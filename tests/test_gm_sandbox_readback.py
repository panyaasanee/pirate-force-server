"""The `sandbox` readback: what the row holds, in twelve characters.

TWO LAYERS, KEPT APART ON PURPOSE.  The DB layer runs against a real
`SQLiteStore` on a temp file and reads back through a SECOND store that
opens the same file, so "the readback answered 137" is measured against
rows on disk rather than against the object that wrote them.  The
wire/screen layer composes the real local-talk notice frame through
`say_wire.make_local_talk_notice_frame`, which is the function that refuses
any body that is not exactly `NOTICE_TEXT_EXACT_LENGTH` printable ASCII --
so a sentence this module could not put on a screen fails here rather than
at an attended boot.

NEITHER LAYER IS EVIDENCE FOR THE OTHER, and no case in this file claims a
client drew anything: nothing sends the skill list yet (LANE-CS owns that
seam).  What is proven here is that the sentence says what the row holds.
"""

import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import class_skill_curriculum  # noqa: E402
from pirateforce_foundation import session as session_module  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import commands as gm_commands  # noqa: E402
from pirateforce_foundation.gm import sandbox_readback  # noqa: E402
from pirateforce_foundation.gm import say_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"
LEGACY = ROOT / "current/pf_login_game_server_v141.py"
TOTAL = class_skill_curriculum.SKILL_COUNT


def _build_wire(selector):
    return b"wire", b"avatar", 0x20000001 + selector, 0


class _RaisingStore:
    def read_typed_attributes(self, character_id):
        raise RuntimeError("the typed map is unavailable")

    def list_character_skills(self, character_id):
        raise RuntimeError("the skill table is unavailable")


class _DoorlessStore:
    """A store object with neither door, which other lanes' fakes really are."""


class _TypedOnlyStore:
    def __init__(self, class_id):
        self._class_id = class_id

    def read_typed_attributes(self, character_id):
        return {} if self._class_id is None else {"class_id": self._class_id}


class _SkillsStore(_TypedOnlyStore):
    def __init__(self, class_id, skill_ids):
        super().__init__(class_id)
        self._skill_ids = tuple(skill_ids)

    def list_character_skills(self, character_id):
        return self._skill_ids


# ---------------------------------------------------------------------------
# THE SENTENCE
# ---------------------------------------------------------------------------
class TheBodyIsAlwaysOneTheWireWillTakeTests(unittest.TestCase):
    """Every branch, at the pinned length, through the real composer."""

    def setUp(self):
        self.legacy = load_legacy(LEGACY)

    def _bodies(self):
        state = sandbox_readback.SandboxState
        return {
            "job_and_skills": state(16, TOTAL, TOTAL, TOTAL),
            "smallest_class": state(1, 0, 0, TOTAL),
            "largest_class": state(999, 999, 999, TOTAL),
            "no_job": state(None, TOTAL, TOTAL, TOTAL),
            "skills_unknown": state(32, None, None, TOTAL),
            "nothing_readable": state(None, None, None, TOTAL),
            "class_too_big": state(1000, 1, 1, TOTAL),
            "class_negative": state(-1, 1, 1, TOTAL),
            "skills_too_big": state(1, 1000, 1000, TOTAL),
        }

    def test_every_branch_is_exactly_the_pinned_length_of_printable_ascii(self):
        for name, state in self._bodies().items():
            with self.subTest(branch=name):
                body = sandbox_readback.notice_body(state)
                self.assertEqual(len(body), say_wire.NOTICE_TEXT_EXACT_LENGTH)
                self.assertTrue(body.isascii())
                self.assertTrue(body.isprintable())

    def test_every_branch_composes_a_real_notice_frame(self):
        # The composer refuses any body it will not put on a screen, so this
        # is the branch coverage that matters: a sentence found by hand
        # inside twelve characters is worth nothing until this call takes it.
        for name, state in self._bodies().items():
            with self.subTest(branch=name):
                pc, frame = say_wire.make_local_talk_notice_frame(
                    self.legacy, sandbox_readback.notice_body(state)
                )
                self.assertTrue(frame)

    def test_a_number_that_does_not_fit_says_so_instead_of_lying(self):
        # `%03d` of 1000 is "1000", which would ship a 13-character body the
        # wire refuses; `%03d` of -1 is "-01", which reads as a class this
        # game does not have.  Both answer the same refusal sentence.
        for value in (1000, -1, 10 ** 9):
            with self.subTest(class_id=value):
                self.assertEqual(
                    sandbox_readback.notice_body(
                        sandbox_readback.SandboxState(value, 1, 1, TOTAL)
                    ),
                    sandbox_readback.NOTICE_TOO_BIG,
                )

    def test_zero_skills_is_not_the_same_sentence_as_unknown_skills(self):
        counted = sandbox_readback.notice_body(
            sandbox_readback.SandboxState(1, 0, 0, TOTAL)
        )
        unknown = sandbox_readback.notice_body(
            sandbox_readback.SandboxState(1, None, None, TOTAL)
        )
        self.assertNotEqual(counted, unknown)
        self.assertIn("000", counted)
        self.assertIn("???", unknown)


# ---------------------------------------------------------------------------
# THE DOORS
# ---------------------------------------------------------------------------
class TheDoorsAreTheLoginsOwnTests(unittest.TestCase):
    """The class answer is the login's answer, not a copy of its logic."""

    def test_the_class_matches_the_function_the_login_itself_calls(self):
        # `session._class_id_on_the_row` is what `legacy_bridge.start_game`
        # asks.  If this readback ever grows its own lookup, one of these
        # rows will disagree and this case says which.
        cases = [
            _TypedOnlyStore(16),
            _TypedOnlyStore(None),
            _TypedOnlyStore("16"),
            _RaisingStore(),
            _DoorlessStore(),
            None,
        ]
        for store in cases:
            with self.subTest(store=type(store).__name__):
                login = session_module._class_id_on_the_row(store, 7)
                if type(login) is not int or isinstance(login, bool):
                    login = None
                self.assertEqual(
                    sandbox_readback.read_sandbox_state(store, 7).class_id, login
                )

    def test_a_store_whose_doors_raise_answers_unknown_and_never_raises(self):
        state = sandbox_readback.read_sandbox_state(_RaisingStore(), 7)
        self.assertIsNone(state.class_id)
        self.assertIsNone(state.curriculum_held)
        self.assertIsNone(state.rows_held)
        self.assertEqual(
            sandbox_readback.notice_body(state), "NO JOB SK???"
        )

    def test_no_selected_character_is_not_a_row_that_reads_back_empty(self):
        store = _SkillsStore(16, class_skill_curriculum.CURRICULUM_SKILL_IDS)
        for character_id in (None, 0, -1, True, "7", 7.0):
            with self.subTest(character_id=character_id):
                state = sandbox_readback.read_sandbox_state(store, character_id)
                self.assertIsNone(state.class_id)
                self.assertIsNone(state.curriculum_held)

    def test_the_count_is_of_curriculum_ids_and_the_row_total_is_separate(self):
        # A character can hold skills this lane never granted; `SK<n>` may not
        # count them or "the sandbox is stocked" becomes unanswerable.
        stranger = max(class_skill_curriculum.CURRICULUM_SKILL_IDS) + 1000
        store = _SkillsStore(
            1, list(class_skill_curriculum.CURRICULUM_SKILL_IDS[:3]) + [stranger]
        )
        state = sandbox_readback.read_sandbox_state(store, 7)
        self.assertEqual(state.curriculum_held, 3)
        self.assertEqual(state.rows_held, 4)
        self.assertIn("skills=3/%d" % TOTAL, sandbox_readback.console_line(7, state))
        self.assertIn("rows=4", sandbox_readback.console_line(7, state))

    def test_the_console_line_names_what_it_could_not_read(self):
        state = sandbox_readback.read_sandbox_state(_RaisingStore(), 7)
        line = sandbox_readback.console_line(7, state)
        self.assertTrue(line.startswith(sandbox_readback.CONSOLE_TOKEN))
        self.assertIn("class_id=none", line)
        self.assertIn("rows=unknown", line)


# ---------------------------------------------------------------------------
# THE ROW
# ---------------------------------------------------------------------------
class TheAnswerIsMeasuredOnDiskTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.db_path = self.tmp / "pirateforce_sandbox_readback_test.sqlite3"
        self.store = SQLiteStore(self.db_path, MIGRATIONS)
        self.store.migrate()
        account_id = self.store.ensure_account("sandbox-gm")
        self.character = self.store.create_character(
            account_id, "ReadbackGM", "readbackgm", "fingerprint-readback-gm",
            _build_wire, Position(1, 0, 1.0, 2.0, 3.0, heading=0.0),
        )

    def _state_through_a_second_store(self):
        second = SQLiteStore(self.db_path, MIGRATIONS)
        return sandbox_readback.read_sandbox_state(second, self.character.id)

    def test_a_fresh_character_reads_back_as_no_job_and_a_real_zero(self):
        state = self._state_through_a_second_store()
        self.assertIsNone(state.class_id)
        self.assertEqual(state.curriculum_held, 0)
        self.assertEqual(sandbox_readback.notice_body(state), "NO JOB SK000")

    def test_what_the_two_sandbox_commands_write_is_what_this_reads_back(self):
        # Written through the same doors `/job` and `/skill all` write
        # through, read back through a store that never saw the writes.
        self.store.write_typed_attributes(self.character.id, {"class_id": 16})
        for skill_id in class_skill_curriculum.CURRICULUM_SKILL_IDS:
            self.store.grant_learned_skill(self.character.id, skill_id)
        state = self._state_through_a_second_store()
        self.assertEqual(state.class_id, 16)
        self.assertEqual(state.curriculum_held, TOTAL)
        self.assertEqual(
            sandbox_readback.notice_body(state), "JOB016 SK%03d" % TOTAL
        )

    def test_a_partly_stocked_row_reads_back_partly_stocked(self):
        self.store.write_typed_attributes(self.character.id, {"class_id": 32})
        for skill_id in class_skill_curriculum.CURRICULUM_SKILL_IDS[:5]:
            self.store.grant_learned_skill(self.character.id, skill_id)
        state = self._state_through_a_second_store()
        self.assertEqual(sandbox_readback.notice_body(state), "JOB032 SK005")


# ---------------------------------------------------------------------------
# THE COMMAND
# ---------------------------------------------------------------------------
class _FakeSelected:
    def __init__(self, character_id):
        # `.id`, because `_selected_speed_character_id` reads
        # `session.foundation.selected.id` -- the same chain `/job` and
        # `/skill all` read, so this double cannot pass a character the two
        # writers would not have touched.
        self.id = character_id


class _FakeLifecycle:
    def __init__(self, store):
        self.store = store


class _FakeFoundation:
    def __init__(self, store, character_id):
        self.lifecycle = _FakeLifecycle(store)
        self.selected = _FakeSelected(character_id)


class _FakeSession:
    def __init__(self, store, character_id):
        self.foundation = _FakeFoundation(store, character_id)
        self.events = []
        self.token = "sandbox-gm"


class TheGrammarAndTheDispatchTests(unittest.TestCase):
    def test_sandbox_takes_no_arguments_and_says_so_when_given_one(self):
        self.assertEqual(
            gm_commands.parse_gm_command("sandbox"),
            gm_commands.GmCommand("sandbox", (), "sandbox"),
        )
        # Trailing spaces are the same command; an argument is a refusal
        # carrying the table's own sentence, never an argument ignored.
        self.assertEqual(gm_commands.parse_gm_command("sandbox   ").args, ())
        with self.assertRaises(gm_commands.GmCommandParseError) as caught:
            gm_commands.parse_gm_command("sandbox 3")
        self.assertEqual(
            str(caught.exception), gm_commands.COMMAND_USAGE["sandbox"]
        )

    def test_the_command_is_in_the_audited_vocabulary(self):
        self.assertIn("sandbox", gm_commands.COMMAND_NAMES)
        self.assertTrue(
            gm_commands.is_known_outcome(
                gm_commands.OUTCOME_SANDBOX_READBACK_ANSWERED
            )
        )

    def test_the_action_label_carries_no_teleport_substring(self):
        # `runtime.py`'s `_move_authority_note_server_teleport` reads the
        # label as a substring and would open a move-authority grace window
        # for a sentence that moves nobody.
        self.assertNotIn(
            "TELEPORT",
            chat_command_action.SANDBOX_READBACK_NOTICE_ACTION_LABEL,
        )

    def test_one_sandbox_answers_on_screen_and_on_the_console(self):
        store = _SkillsStore(16, class_skill_curriculum.CURRICULUM_SKILL_IDS)
        session = _FakeSession(store, 7)
        stderr = StringIO()
        with redirect_stderr(stderr):
            verdict = chat_command_action._sandbox_action(
                session,
                gm_commands.parse_gm_command("sandbox"),
                load_legacy(LEGACY),
                token="sandbox-gm",
            )
        self.assertEqual(
            verdict.audit_outcome,
            gm_commands.OUTCOME_SANDBOX_READBACK_ANSWERED,
        )
        self.assertEqual(
            verdict.action[0],
            chat_command_action.SANDBOX_READBACK_NOTICE_ACTION_LABEL,
        )
        self.assertTrue(verdict.is_notice)
        printed = stderr.getvalue()
        self.assertIn("GM_SANDBOX cid=7 class_id=16", printed)
        self.assertIn("JOB016 SK%03d" % TOTAL, printed)
        self.assertIn("job_and_skills", " ".join(session.events))

    def test_the_readback_writes_nothing_at_all(self):
        # The one property that makes a canonical-DB gate unnecessary in
        # front of this command: there is no writer to reach.  A store that
        # RAISES on every write door answers the same sentence as one that
        # has them, because neither is ever called.
        class _WriteTrap(_SkillsStore):
            def write_typed_attributes(self, *args, **kwargs):
                raise AssertionError("the readback wrote a typed attribute")

            def grant_learned_skill(self, *args, **kwargs):
                raise AssertionError("the readback granted a skill")

        store = _WriteTrap(16, class_skill_curriculum.CURRICULUM_SKILL_IDS)
        session = _FakeSession(store, 7)
        with redirect_stderr(StringIO()):
            verdict = chat_command_action._sandbox_action(
                session,
                gm_commands.parse_gm_command("sandbox"),
                load_legacy(LEGACY),
                token="sandbox-gm",
            )
        self.assertIsNone(verdict.undo)

    def test_a_sandbox_on_a_connection_with_no_character_still_answers(self):
        session = _FakeSession(_DoorlessStore(), None)
        stderr = StringIO()
        with redirect_stderr(stderr):
            verdict = chat_command_action._sandbox_action(
                session,
                gm_commands.parse_gm_command("sandbox"),
                load_legacy(LEGACY),
                token="sandbox-gm",
            )
        self.assertEqual(
            verdict.audit_outcome,
            gm_commands.OUTCOME_SANDBOX_READBACK_ANSWERED,
        )
        self.assertIn("NO JOB SK???", stderr.getvalue())

    def test_a_notice_that_will_not_compose_is_a_refusal_not_a_success(self):
        # This command's whole product IS the sentence, so a compose failure
        # leaves nothing at all -- and may not be audited as an answer.
        class _BrokenLegacy:
            def __getattr__(self, name):
                raise RuntimeError("no legacy wire in this process")

        session = _FakeSession(_DoorlessStore(), 7)
        stderr = StringIO()
        with redirect_stderr(stderr):
            verdict = chat_command_action._sandbox_action(
                session,
                gm_commands.parse_gm_command("sandbox"),
                _BrokenLegacy(),
                token="sandbox-gm",
            )
        self.assertTrue(
            verdict.audit_outcome.startswith(
                gm_commands.OUTCOME_REFUSED_PREFIX
            )
        )
        self.assertIsNone(verdict.action)
        self.assertIn("notice=none", stderr.getvalue())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
