"""SKILL-LIST-AT-LOGIN-001 -- the character's persisted skill rows on the wire.

Pure offline pytest: a throwaway temp database with the real migrations, the
real ``SQLiteStore``, and the frozen v141 module for the envelope.  No network, no game
client, no UI.  (The client class name is deliberately not spelled here: the
Windows gate excludes any test module that contains it, which would hide this
file from the gate entirely.)

What these tests prove
----------------------
  * the ids come from ``character_skills`` and from nowhere else -- proved by
    changing the ROWS and watching the frame change, and by deleting a row and
    watching the frame shrink, neither of which the class table could do;
  * every refusal is a NAMED refusal of this module's own exception class, so
    a login-path caller has one ``except`` and never a bare ``KeyError``;
  * a character with no rows gets a refusal, never a count-0 frame;
  * the composed bytes are the GT-050-proven body and the frozen envelope,
    asserted by decoding them back with the owning module's own decoder;
  * ``callers_in_src`` is MEASURED here by grepping every sibling module, so
    the token cannot go on saying a number once it is false.  It said 0 for
    three rounds and says 1 since round `ixbs2f` wired the seam;
  * and, since `ixbs2f`, that a REAL ``StartGameReq`` through the REAL
    dispatcher comes back carrying the frame -- see the last class in this
    file, which is the only kind of test that could have caught three rounds
    of a green module nothing called.

NOT tested here, because it is not claimed: that any client renders any of
this (GT-249 says 3 of 4 ids rendered from a TRIGGER, never from a login);
that a login is the right moment to send it; or that the movement regression
GT-249 recorded is absent.  ``GT-307`` is the attended ticket for all three,
and `production_allowed` being True is not an answer to any of them -- it is
a kill switch that an operator can put back, which is a different thing.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import io
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import skill_list_at_login  # noqa: E402
from pirateforce_foundation.class_catalog import (  # noqa: E402
    starting_skill_ids,
)
from pirateforce_foundation.learn_skill_result_hypothesis import (  # noqa: E402
    LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET,
    LEARN_SKILL_RESULT_PROBE_FRAME_SHA256,
    LEARN_SKILL_RESULT_PROBE_PC_SHA256,
    LEARN_SKILL_RESULT_RECORD_WIRE_SIZE,
    LEARN_SKILL_RESULT_PAYLOAD_BASE_SIZE,
    LEARN_SKILL_RESULT_VITAL_ID,
    LearnSkillResultRecord,
    decode_learn_skill_result_payload,
)
from pirateforce_foundation.learn_skill_result_frame import (  # noqa: E402
    make_learn_skill_result_response,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.skill_list_at_login import (  # noqa: E402
    SkillListAtLoginError,
)
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SRC = ROOT / "src" / "pirateforce_foundation"

_HOME = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
_next_identity = iter(range(0x30000001, 0x30001000))


@contextlib.contextmanager
def _sqlite(path):
    """`sqlite3.connect`, but the handle is CLOSED when the block ends.

    THIS IS THE ONE DEFECT THAT TURNED THE WINDOWS GATE RED FOR `#1103`
    (run 34156908531, `pytest_subset exit=1`, every other check GREEN).
    `sqlite3.Connection.__exit__` commits or rolls back the transaction and
    deliberately leaves the connection OPEN, so the four call sites below
    still held `state.sqlite3` when `TemporaryDirectory` cleanup ran, and
    Windows answered `PermissionError: [WinError 32] The process cannot
    access the file because it is being used by another process`.  POSIX
    unlinks an open file without a word, which is why the same four lines are
    green on this clone and red on windows-latest -- the second platform
    difference this module has produced after the path separators of #1091.

    The failure lands in `tearDown`, not in the test body, so pytest reports
    it as an ERROR: with the gate's `-rs` (which REPLACES the default
    reportchars) no `FAILED` line is printed at all, and the gate's
    tail-readable summary said `none`.  The cause was in the log, 1000 lines
    above that summary.
    """
    connection = sqlite3.connect(path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _build_wire(selector):
    return b"wire", b"avatar", next(_next_identity), 0


class _Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()

    def _character(self, login="acct01", name="Test01"):
        account_id = self.store.ensure_account(login)
        self.store.open_session(account_id)
        return self.store.create_character(
            account_id, name, name.casefold(), "fp-" + login,
            _build_wire, _HOME,
        )

    def _with_skills(self, skill_ids, login="acct01", name="Test01"):
        character = self._character(login=login, name=name)
        self.store.grant_starting_skills(character.id, tuple(skill_ids))
        return character


class TheIdsComeFromTheRowsNotFromTheClassTableTests(_Fixture):
    """The whole point of the order, proved by moving the rows."""

    def test_the_frame_carries_exactly_the_rows_that_are_in_the_table(self):
        wanted = (111, 40000, 99, 110)
        character = self._with_skills(wanted)
        self.assertEqual(
            wanted,
            skill_list_at_login.read_character_skill_ids(
                self.store, character.id
            ),
        )

    def test_ids_that_no_class_starts_with_still_reach_the_wire(self):
        # A class table could never answer this: 7/8/9 are not any class's
        # starting kit.  If this module were secretly resolving the class, the
        # frame would come back with the kit instead of these three.
        invented = (7, 8, 9)
        for class_id in (1, 2, 4, 16, 32):
            self.assertNotEqual(invented, starting_skill_ids(class_id)[:3])
        character = self._with_skills(invented)
        pc, _frame = skill_list_at_login.login_skill_list_response(
            self.legacy, self.store, character.id
        )
        records, trailing = self._decode(pc, 3)
        self.assertEqual(
            [7, 8, 9], [record.record_u32_0 for record in records]
        )
        self.assertEqual(skill_list_at_login.SKILL_LIST_TRAILING_BYTE, trailing)

    def test_a_second_grant_makes_the_frame_grow(self):
        character = self._with_skills((99,))
        before, _ = skill_list_at_login.login_skill_list_response(
            self.legacy, self.store, character.id
        )
        self.store.grant_starting_skills(character.id, (110,))
        after, _ = skill_list_at_login.login_skill_list_response(
            self.legacy, self.store, character.id
        )
        self.assertEqual(
            len(before) + LEARN_SKILL_RESULT_RECORD_WIRE_SIZE, len(after)
        )
        records, _ = self._decode(after, 2)
        self.assertEqual([99, 110], [r.record_u32_0 for r in records])

    def test_two_characters_get_two_different_frames(self):
        one = self._with_skills((99,), login="acct01", name="Test01")
        two = self._with_skills((110, 111), login="acct02", name="Test02")
        pc_one, _ = skill_list_at_login.login_skill_list_response(
            self.legacy, self.store, one.id
        )
        pc_two, _ = skill_list_at_login.login_skill_list_response(
            self.legacy, self.store, two.id
        )
        self.assertNotEqual(pc_one, pc_two)
        self.assertEqual(
            [99], [r.record_u32_0 for r in self._decode(pc_one, 1)[0]]
        )
        self.assertEqual(
            [110, 111], [r.record_u32_0 for r in self._decode(pc_two, 2)[0]]
        )

    def _decode(self, pc, count):
        size = (
            LEARN_SKILL_RESULT_PAYLOAD_BASE_SIZE
            + LEARN_SKILL_RESULT_RECORD_WIRE_SIZE * count
        )
        offset = LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET
        return decode_learn_skill_result_payload(pc[offset:offset + size])


class RowsThatCannotAnswerAreRefusedByNameTests(_Fixture):

    def test_a_character_with_no_skill_rows_is_refused_not_sent_count_zero(self):
        character = self._character()
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.login_skill_list_response(
                self.legacy, self.store, character.id
            )
        self.assertEqual(
            skill_list_at_login.REFUSE_NO_SKILL_ROWS, caught.exception.reason
        )

    def test_a_missing_character_is_a_named_refusal_not_a_key_error(self):
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.read_character_skill_ids(self.store, 999999)
        self.assertEqual(
            skill_list_at_login.REFUSE_CHARACTER_ROW_MISSING,
            caught.exception.reason,
        )

    def test_a_bool_character_id_is_refused_before_the_store_sees_it(self):
        # `True == 1` and character 1 is a real row in a fresh database, so a
        # coercing check would read someone else's skills.
        self._with_skills((99,))
        for bad in (True, False):
            with self.subTest(character_id=bad):
                with self.assertRaises(SkillListAtLoginError) as caught:
                    skill_list_at_login.read_character_skill_ids(
                        self.store, bad
                    )
                self.assertEqual(
                    skill_list_at_login.REFUSE_CHARACTER_ID_NOT_AN_INT,
                    caught.exception.reason,
                )

    def test_a_bool_never_reaches_the_store_at_all(self):
        """The bool guard is a branch nobody walks unless a test walks it.

        Round `b2cnxe` mutant M3 (delete the `isinstance(..., bool)` half)
        stayed GREEN against the first version of this file: `True` is an
        `int` in python, so it sailed past the type check, and
        `list_character_skills` then raised its OWN `TypeError`, which
        `read_character_skill_ids` translates into the SAME reason string.
        Every assertion still passed while the guard was gone -- the exact
        defect class round `hhmvit` was caught by (its M4/M6).  So this test
        checks the thing the reason string cannot: that the store is never
        asked.  It matters beyond tidiness -- `sqlite3` binds `True` as `1`,
        so a store that is reached would answer with CHARACTER 1's skills.
        """
        class _StoreThatMustNotBeAsked:
            def list_character_skills(self, character_id):
                raise AssertionError(
                    "the store was consulted for %r" % (character_id,)
                )

        for bad in (True, False):
            with self.subTest(character_id=bad):
                with self.assertRaises(SkillListAtLoginError) as caught:
                    skill_list_at_login.read_character_skill_ids(
                        _StoreThatMustNotBeAsked(), bad
                    )
                self.assertEqual(
                    skill_list_at_login.REFUSE_CHARACTER_ID_NOT_AN_INT,
                    caught.exception.reason,
                )

    def test_a_string_character_id_is_refused_by_name(self):
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.read_character_skill_ids(self.store, "1")
        self.assertEqual(
            skill_list_at_login.REFUSE_CHARACTER_ID_NOT_AN_INT,
            caught.exception.reason,
        )


class TheRecordListRefusesByNameTests(unittest.TestCase):

    def test_a_bool_skill_id_is_not_a_skill_id(self):
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.skill_list_records((True,))
        self.assertEqual(
            skill_list_at_login.REFUSE_SKILL_ID_NOT_AN_INT,
            caught.exception.reason,
        )

    def test_an_id_outside_u32_is_refused(self):
        for bad in (-1, 0x100000000):
            with self.subTest(skill_id=bad):
                with self.assertRaises(SkillListAtLoginError) as caught:
                    skill_list_at_login.skill_list_records((bad,))
                self.assertEqual(
                    skill_list_at_login.REFUSE_SKILL_ID_OUTSIDE_U32,
                    caught.exception.reason,
                )

    def test_a_duplicate_id_is_refused(self):
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.skill_list_records((99, 99))
        self.assertEqual(
            skill_list_at_login.REFUSE_DUPLICATE_SKILL_ID,
            caught.exception.reason,
        )

    def test_a_string_is_not_a_list_of_ids(self):
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.skill_list_records("99")
        self.assertEqual(
            skill_list_at_login.REFUSE_SKILL_ID_NOT_AN_INT,
            caught.exception.reason,
        )

    def test_more_records_than_anyone_has_measured_is_refused_by_name(self):
        cap = skill_list_at_login.OBSERVED_ACCEPTED_RECORD_COUNT
        self.assertEqual(cap, len(skill_list_at_login.skill_list_records(
            tuple(range(1, cap + 1))
        )))
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.skill_list_records(tuple(range(1, cap + 2)))
        self.assertEqual(
            skill_list_at_login.REFUSE_TOO_MANY_UNMEASURED,
            caught.exception.reason,
        )

    def test_the_unmeasured_cap_is_below_the_wire_cap(self):
        # The two constants say different things: one is the u16 field width
        # (a fact about the serializer), the other is the largest count a
        # client was watched accepting (a fact about GT-249).  If they ever
        # collapse into one number this test says so.
        self.assertLess(
            skill_list_at_login.OBSERVED_ACCEPTED_RECORD_COUNT,
            skill_list_at_login.WIRE_MAX_RECORDS,
        )

    def test_the_id_lands_in_all_three_wire_positions(self):
        records = skill_list_at_login.skill_list_records((111, 99))
        self.assertEqual(
            (
                LearnSkillResultRecord(111, 111, 111),
                LearnSkillResultRecord(99, 99, 99),
            ),
            records,
        )


class TheComposedBytesAreTheProvenShapeTests(_Fixture):

    def test_the_vital_id_is_the_one_gt050_proved(self):
        character = self._with_skills((99, 110))
        pc, frame = skill_list_at_login.login_skill_list_response(
            self.legacy, self.store, character.id
        )
        self.assertIn(
            LEARN_SKILL_RESULT_VITAL_ID.to_bytes(2, "little"), pc
        )
        self.assertTrue(frame)

    def test_the_frame_is_byte_identical_to_the_one_gt249_already_rendered(
        self,
    ):
        """The strongest thing this module can honestly claim today.

        GT-249 (2026-09-05, real client, owner watching) sent step 6 of the
        pinned sweep -- class 1's four starting ids, trailing 0 -- and three
        of the four appeared in the skill window with correct name and icon.
        This module reaches the SAME 79-byte PC and 90-byte frame from a
        different direction entirely: four rows read out of
        `character_skills`, no scenario file, no flag, no pinned step index.

        That equality is the ticket's whole argument and its whole honesty at
        once.  It means an attended run of this module is not asking a client
        to accept anything new -- these exact bytes were already accepted and
        rendered.  It ALSO means the "from the database, not from a fixed
        table" difference is not visible in the bytes for any character alive
        today, because `lifecycle.py` wrote those rows from the same class
        table.  Both halves are true and this test pins both.
        """
        character = self._with_skills(starting_skill_ids(1))
        pc, frame = skill_list_at_login.login_skill_list_response(
            self.legacy, self.store, character.id
        )
        step = "COUNT4_REAL_SKILL_IDS_CLASS1_TRAIL0"
        self.assertEqual(
            LEARN_SKILL_RESULT_PROBE_PC_SHA256[step].lower(),
            hashlib.sha256(pc).hexdigest(),
        )
        self.assertEqual(
            LEARN_SKILL_RESULT_PROBE_FRAME_SHA256[step].lower(),
            hashlib.sha256(frame).hexdigest(),
        )

    def test_an_id_above_u16_is_refused_by_this_module_not_by_a_value_error(
        self,
    ):
        # `record_u16_4` is the narrow position: 70000 fits both u32 slots and
        # not the middle one, so the encoder refuses with `ValueError` and the
        # login path would see an exception class it does not catch.
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.make_skill_list_response(
                self.legacy, (70000,)
            )
        self.assertEqual(
            skill_list_at_login.REFUSE_SKILL_ID_OUTSIDE_U32,
            caught.exception.reason,
        )


class TheLaneIsWiredAndSaysSoTests(unittest.TestCase):
    """Was `TheLaneIsNotWiredAndSaysSo...` until round `ixbs2f` wired it.

    The three tests in here were written to go red on the day the seam
    landed, and they did (all three, first run).  They are REWRITTEN, not
    removed: each one still pins a fact, and the fact it pins is the one that
    replaced the fact it used to pin.  A pin whose subject has changed and
    that gets deleted instead of re-aimed is how a lane ends up with no pin
    at all on the thing it just changed.
    """

    def test_production_allowed_is_true_and_the_flag_names_what_paid_for_it(
        self,
    ):
        # GT-249 recorded a client that stopped emitting movement frames
        # after this vital's sweep; while the cause was unisolated this
        # asserted False, because flipping the flag before a measurement was
        # the loud failure.  GT-276 (PASS, R323C) isolated it to the trailing
        # u8, so the flag is True -- and the assertion moves to the thing
        # that can now go wrong instead: True with nothing written down.
        self.assertTrue(skill_list_at_login.production_allowed)
        source = Path(
            skill_list_at_login.__file__
        ).read_text(encoding="utf-8")
        head = source.split("production_allowed = True")[0]
        # The comment BLOCK ABOVE the flag, not the file at large: a ticket
        # id anywhere in a 900-line module would pass a whole-file search
        # while the flag itself sat there unexplained.
        self.assertIn("GT-276", head[-800:])
        self.assertIn("R323C", head[-800:])

    def test_the_callers_in_src_token_matches_the_tree(self):
        summary = [
            line for line in
            skill_list_at_login.describe_skill_list((99, 110))
            if line.startswith("SKILL_LIST_AT_LOGIN_SUMMARY")
        ]
        self.assertEqual(1, len(summary))
        here = Path(skill_list_at_login.__file__).resolve()
        callers = sorted(
            path.name
            for path in SRC.rglob("*.py")
            if path.resolve() != here
            and "skill_list_at_login" in path.read_text(encoding="utf-8")
        )
        # Whole token, not a substring: pf-adversary showed on the sibling
        # module (round `hhmvit` D2) that `assertIn("callers_in_src=1", ...)`
        # passes against `callers_in_src=12`.
        self.assertIn(
            "callers_in_src=%d" % len(callers), summary[0].split(),
        )
        # WAS `assertEqual([], callers)`.  The list is spelled out rather
        # than counted so that a SECOND caller appearing -- a lane wiring
        # this frame somewhere else without saying so -- goes red instead of
        # quietly riding the count.
        self.assertEqual(["runtime.py"], callers)

    def test_every_console_line_survives_the_bridge_console(self):
        for line in skill_list_at_login.describe_skill_list((111, 40000)):
            with self.subTest(line=line):
                line.encode("ascii")
                line.encode("cp874")


class TheHeadlessTokenIsMeasuredNotSpelledTests(_Fixture):
    """GT-307's ``HEADLESS_PROOF:`` command, pinned against its own database.

    The ticket names one line and says in as many words that it "must read
    from the real database, not from the class table".  Every test here
    grants ids that no class in ``CHARCREATE_CLASS`` starts with, so a
    version of this command that quietly fell back on the class table would
    print different ids and go red rather than look right.
    """

    def _run(self, argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = skill_list_at_login.main(argv)
        return code, buffer.getvalue().strip()

    def test_the_token_carries_the_rows_that_are_in_the_database(self):
        character = self._with_skills((7, 8, 9))
        code, line = self._run(
            ["--character", str(character.id), "--db", str(self.path)]
        )
        self.assertEqual(0, code)
        fields = dict(
            token.split("=", 1) for token in line.split() if "=" in token
        )
        self.assertTrue(line.startswith("SKILL_LIST_AT_LOGIN "))
        self.assertEqual(str(character.id), fields["cid"])
        self.assertEqual("3", fields["rows"])
        self.assertEqual("(7,8,9)", fields["ids"])
        self.assertEqual("0", fields["trailing_u8"])
        self.assertEqual(
            str(skill_list_at_login.SKILL_LIST_TRAILING_BYTE),
            fields["trailing_u8"],
        )

    def test_the_byte_count_is_the_frame_the_proven_encoder_composed(self):
        character = self._with_skills((7, 8, 9))
        _pc, frame = skill_list_at_login.make_skill_list_response(
            self.legacy, (7, 8, 9)
        )
        _code, line = self._run(
            ["--character", str(character.id), "--db", str(self.path)]
        )
        self.assertIn("frame_bytes=%d" % len(frame), line.split())

    def test_deleting_one_row_shortens_the_token_and_the_frame(self):
        """GT-307 step (c), measured here so the attended run is a re-check.

        pf-adversary (D8) refuted this test's first rationale, which called
        it "the one step that tells rows from the class table": the fixture
        grants 7/8/9, and no class starts with those, so the IDS already
        separate the two hypotheses and the count is a second, independent
        witness rather than the only one.  It still earns its place -- on the
        attended run the character carries her real class ids, where the ids
        alone prove nothing and only the count moves.
        """
        character = self._with_skills((7, 8, 9))
        _code, before = self._run(
            ["--character", str(character.id), "--db", str(self.path)]
        )
        with _sqlite(self.path) as connection:
            connection.execute(
                "DELETE FROM character_skills WHERE character_id=? "
                "AND skill_id=?",
                (character.id, 9),
            )
        _code, after = self._run(
            ["--character", str(character.id), "--db", str(self.path)]
        )
        self.assertIn("rows=3", before.split())
        self.assertIn("rows=2", after.split())
        self.assertIn("ids=(7,8)", after.split())
        self.assertLess(
            int(dict(t.split("=", 1) for t in after.split() if "=" in t)
                ["frame_bytes"]),
            int(dict(t.split("=", 1) for t in before.split() if "=" in t)
                ["frame_bytes"]),
        )

    def test_main_reports_sent_by_from_the_runtime_it_is_pointed_at(self):
        """pf-adversary D3: nothing pinned that ``main`` calls seam_carrier.

        The spelled-literal mutant -- ``headless_token(..., "runtime")`` --
        was green against every other test in this file, so the one line an
        operator pastes as HEADLESS_PROOF could end ``sent_by=runtime`` with
        nothing behind it.  Two runtimes, two answers, through ``main``.
        """
        character = self._with_skills((7, 8, 9))
        calls = Path(self.tmp.name) / "calls_runtime.py"
        calls.write_text(
            "def start_game(legacy, store, cid):\n"
            "    return %s(legacy, store, cid)\n"
            % skill_list_at_login.LOGIN_SEAM_SYMBOL,
            encoding="utf-8",
        )
        silent = Path(self.tmp.name) / "silent_runtime.py"
        silent.write_text("class GameState:\n    pass\n", encoding="utf-8")
        _code, wired = self._run([
            "--character", str(character.id), "--db", str(self.path),
            "--runtime", str(calls),
        ])
        _code, bare = self._run([
            "--character", str(character.id), "--db", str(self.path),
            "--runtime", str(silent),
        ])
        self.assertIn("sent_by=runtime", wired.split())
        self.assertIn("sent_by=module_only", bare.split())

    def test_a_character_with_no_rows_prints_one_refusal_line_and_exits_1(self):
        character = self._character()
        code, line = self._run(
            ["--character", str(character.id), "--db", str(self.path)]
        )
        self.assertEqual(1, code)
        self.assertTrue(line.startswith("SKILL_LIST_AT_LOGIN_REFUSED "))
        self.assertIn(
            "reason=%s" % skill_list_at_login.REFUSE_NO_SKILL_ROWS,
            line.split(),
        )
        self.assertEqual(1, len(line.splitlines()))

    def test_a_missing_database_is_refused_and_never_created(self):
        """A proof command that can write to the canonical database is not one.

        ``SQLiteStore`` would happily create the file, and an attended run
        that mistypes the path would then get a green-looking empty database
        instead of a refusal.
        """
        missing = Path(self.tmp.name) / "not_here.sqlite3"
        code, line = self._run(["--character", "1", "--db", str(missing)])
        self.assertEqual(1, code)
        self.assertTrue(line.startswith("SKILL_LIST_AT_LOGIN_REFUSED "))
        self.assertFalse(missing.exists())

    def test_opening_a_delete_journal_database_flips_it_to_wal(self):
        """The one side effect, measured instead of denied.

        ``SQLiteStore.connect()`` runs ``PRAGMA journal_mode=WAL`` on every
        open, so this command is not read-only against a database that is
        not already in WAL.  Every canonical database is (the next test
        sha256s that case), but a claim that rots silently is worse than a
        side effect that is written down.
        """
        character = self._with_skills((7, 8, 9))
        with _sqlite(self.path) as connection:
            connection.execute("PRAGMA journal_mode=DELETE")
        with _sqlite(self.path) as connection:
            self.assertEqual(
                "delete",
                connection.execute("PRAGMA journal_mode").fetchone()[0],
            )
        self._run(["--character", str(character.id), "--db", str(self.path)])
        with _sqlite(self.path) as connection:
            self.assertEqual(
                "wal",
                connection.execute("PRAGMA journal_mode").fetchone()[0],
            )

    def test_a_zero_byte_file_is_refused_and_stays_zero_bytes(self):
        """pf-adversary D5: is_file() is True of a stub, and sqlite fills it.

        A truncated copy or an operator's placeholder used to become a fresh
        database on disk, followed by a traceback -- while the refusal string
        one line above promised this command never creates one.
        """
        stub = Path(self.tmp.name) / "stub.sqlite3"
        stub.write_bytes(b"")
        code, line = self._run(["--character", "1", "--db", str(stub)])
        self.assertEqual(1, code)
        self.assertIn(
            "reason=%s" % skill_list_at_login.REFUSE_NOT_A_DATABASE,
            line.split(),
        )
        self.assertEqual(b"", stub.read_bytes())

    def test_a_text_file_is_refused_by_name_and_not_by_traceback(self):
        text = Path(self.tmp.name) / "notes.txt"
        text.write_text("this is not a database\n", encoding="utf-8")
        code, line = self._run(["--character", "1", "--db", str(text)])
        self.assertEqual(1, code)
        self.assertTrue(line.startswith("SKILL_LIST_AT_LOGIN_REFUSED "))
        self.assertEqual(1, len(line.splitlines()))

    def test_a_character_id_too_large_for_sqlite_is_a_named_refusal(self):
        character = self._with_skills((7, 8, 9))
        del character
        code, line = self._run(
            ["--character", "9" * 26, "--db", str(self.path)]
        )
        self.assertEqual(1, code)
        self.assertIn(
            "reason=%s" % skill_list_at_login.REFUSE_CHARACTER_ID_NOT_AN_INT,
            line.split(),
        )

    def test_a_path_outside_cp874_does_not_kill_the_report(self):
        """pf-adversary D6: the refusal line interpolates the operator's path.

        A --db under a directory with a character cp874 cannot carry used to
        raise UnicodeEncodeError inside print() -- the tool dying while
        explaining why it could not run.
        """
        missing = Path(self.tmp.name) / "sch\u00f6n" / "missing.sqlite3"
        code, line = self._run(["--character", "1", "--db", str(missing)])
        self.assertEqual(1, code)
        line.encode("ascii")
        line.encode("cp874")
        self.assertTrue(line.startswith("SKILL_LIST_AT_LOGIN_REFUSED "))

    def test_the_command_does_not_write_to_the_database_it_reads(self):
        """Against a database already in WAL -- i.e. every canonical one."""
        character = self._with_skills((7, 8, 9))
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self._run(["--character", str(character.id), "--db", str(self.path)])
        self.assertEqual(
            before, hashlib.sha256(self.path.read_bytes()).hexdigest()
        )


class SentByIsReadOffTheTreeTests(unittest.TestCase):
    """``sent_by=`` is a measurement of ``runtime.py``, not a spelling.

    pf-adversary killed the sibling module's ``callers_in_src=0`` for being a
    zero inside a format string.  The same trap is one word away here: GT-307
    asks for a line ending ``sent_by=runtime``, and printing that word
    unconditionally would make the ticket's own proof unfalsifiable.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_a_runtime_that_calls_the_entry_point_reads_as_runtime(self):
        path = self.dir / "runtime.py"
        path.write_text(
            "frame = %s(legacy, store, cid)\n"
            % skill_list_at_login.LOGIN_SEAM_SYMBOL,
            encoding="utf-8",
        )
        self.assertEqual("runtime", skill_list_at_login.seam_carrier(path))

    def test_a_comment_mentioning_the_entry_point_is_not_a_seam(self):
        """pf-adversary D4, run as its own input.

        The substring version of seam_carrier turned on for this one line.
        """
        path = self.dir / "runtime.py"
        path.write_text(
            "# TODO(next round): call %s from the login path\n"
            % skill_list_at_login.LOGIN_SEAM_SYMBOL,
            encoding="utf-8",
        )
        self.assertEqual("module_only", skill_list_at_login.seam_carrier(path))

    def test_importing_it_without_calling_it_is_not_a_seam(self):
        path = self.dir / "runtime.py"
        path.write_text(
            "from .skill_list_at_login import %s\n"
            % skill_list_at_login.LOGIN_SEAM_SYMBOL,
            encoding="utf-8",
        )
        self.assertEqual("module_only", skill_list_at_login.seam_carrier(path))

    def test_a_runtime_that_does_not_parse_reads_as_unknown(self):
        path = self.dir / "runtime.py"
        path.write_text("def broken(:\n", encoding="utf-8")
        self.assertEqual("unknown", skill_list_at_login.seam_carrier(path))

    def test_a_runtime_without_the_entry_point_reads_as_module_only(self):
        path = self.dir / "runtime.py"
        path.write_text("class GameState:\n    pass\n", encoding="utf-8")
        self.assertEqual("module_only", skill_list_at_login.seam_carrier(path))

    def test_no_runtime_at_all_reads_as_unknown_not_as_runtime(self):
        self.assertEqual(
            "unknown", skill_list_at_login.seam_carrier(self.dir / "gone.py")
        )

    def test_the_shipped_tree_is_never_reported_as_wired_while_it_is_not(self):
        """One direction only, and that is deliberate.

        pf-adversary (D4) showed the first version of this test recomputed
        the implementation's own substring search on both sides -- a
        tautology that could only ever pass.  The honest half is the half
        that can fail: if runtime.py does not mention the symbol AT ALL,
        then no reading of it can honestly say ``runtime``.  The other
        direction is left unasserted on purpose, so the round that lands the
        seam does not have to come back and edit this lane's test to go
        green.
        """
        text = (SRC / "runtime.py").read_text(encoding="utf-8")
        mentions = skill_list_at_login.LOGIN_SEAM_SYMBOL in text
        # One assertion, no skip and no branch: a file that never mentions
        # the symbol cannot honestly be read as `runtime`, and the AST check
        # under test is strictly narrower than the substring on the left, so
        # this is not the same computation twice.
        self.assertTrue(
            mentions or skill_list_at_login.seam_carrier() == "module_only",
            "runtime.py does not mention %s, yet seam_carrier() said %r"
            % (skill_list_at_login.LOGIN_SEAM_SYMBOL,
               skill_list_at_login.seam_carrier()),
        )

    def test_the_token_line_survives_the_bridge_console(self):
        # The pc is COMPOSED, not faked: `headless_token` measures the row
        # count off it (round `jty60h`, pf-adversary D3), so a byte string
        # standing in for a frame can no longer produce a token at all.
        legacy = load_legacy(LEGACY_PATH)
        pc, frame = skill_list_at_login.make_skill_list_response(
            legacy, (111, 40000),
        )
        line = skill_list_at_login.headless_token(1, (111, 40000), frame,
                                                  "module_only", 0, pc=pc)
        line.encode("ascii")
        line.encode("cp874")


class TheDatabaseLayerIsReachedOnlyByTheTwoFunctionsThatNeedItTests(
    unittest.TestCase
):
    """``store`` and ``legacy_bridge`` are imported inside the functions.

    WHY THIS IS AN AST PIN AND NOT A ``sys.modules`` PIN.  The obvious
    stronger test -- boot a clean interpreter, import this module, assert
    ``pirateforce_foundation.store`` is not in ``sys.modules`` -- CANNOT
    pass and would not mean what it says if it did: the package's own
    ``__init__.py`` imports ``SQLiteStore`` on line 3, so importing ANY
    module in this package imports the store before this module's first
    line runs.  Measured, not assumed: the assertion below re-reads that
    ``__init__`` and fails if it ever stops being true, at which point the
    ``sys.modules`` pin becomes the right one to write.

    What is left to measure is this module's own top-level import list, and
    it is worth measuring: the login seam imports this module to compose a
    frame, and the two database names belong to the two functions that read
    a database, not to everybody who wants bytes.
    """

    _DATABASE_NAMES = ("store", "legacy_bridge")

    def _module_level_imports(self):
        tree = ast.parse(
            Path(skill_list_at_login.__file__).read_text(encoding="utf-8")
        )
        names = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                names.extend(alias.name.split(".")[-1] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.append((node.module or "").split(".")[-1])
        return names

    def test_the_package_init_still_imports_the_store(self):
        text = (SRC / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("from .store import", text)

    def test_no_database_name_is_imported_at_module_level(self):
        names = self._module_level_imports()
        for forbidden in self._DATABASE_NAMES:
            with self.subTest(name=forbidden):
                self.assertNotIn(forbidden, names)

    def test_the_pin_can_see_a_module_level_import_when_there_is_one(self):
        """The mutant, run here rather than trusted.

        Without this, a rewrite that made ``_module_level_imports`` return
        ``[]`` would keep the test above green forever.
        """
        tree = ast.parse("from .store import SQLiteStore\n")
        node = tree.body[0]
        self.assertEqual("store", (node.module or "").split(".")[-1])
        self.assertIn(
            "learn_skill_result_frame", self._module_level_imports()
        )


class NoSqliteHandleOutlivesItsBlockTests(unittest.TestCase):
    """The Windows-only leak of `#1103`, pinned where this clone can see it.

    Neither test here needs Windows.  The first one measures the property
    Windows punished -- the handle is shut, not merely committed -- and the
    second one stops the shape from coming back, because the leak is invisible
    on this platform and costs a whole gate round on the other one.
    """

    def test_the_helper_shuts_the_connection_and_not_only_the_transaction(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.sqlite3"
            with _sqlite(path) as connection:
                connection.execute("CREATE TABLE t (a INTEGER)")
                connection.execute("INSERT INTO t VALUES (1)")
            # committed ...
            with _sqlite(path) as reopened:
                self.assertEqual([(1,)], reopened.execute("SELECT a FROM t").fetchall())
            # ... and shut.  `sqlite3.connect(...)`'s own context manager
            # passes the line above and fails this one.
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT a FROM t")

    def test_no_sqlite_connect_in_this_module_is_used_as_a_with_item(self):
        """`with sqlite3.connect(...)` anywhere in this file = the same red.

        An AST walk, not a grep: a name comparison would miss
        `sqlite3 . connect` and would fire on the sentence in `_sqlite`'s own
        docstring that explains why this rule exists.
        """
        source = Path(__file__).read_text(encoding="utf-8")
        offenders = []
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, (ast.With, ast.AsyncWith)):
                continue
            for item in node.items:
                call = item.context_expr
                if not isinstance(call, ast.Call):
                    continue
                func = call.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "connect"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "sqlite3"
                ):
                    offenders.append(node.lineno)
        self.assertEqual(
            offenders,
            [],
            "line(s) %s open a database in a `with` that does not close it; "
            "use the module's `_sqlite` helper" % (offenders,),
        )


class AHookCanWireThisWithoutRuntimeChangingTests(unittest.TestCase):
    """pf-adversary D2 of round `jqeid1`, paid and then pinned.

    `runtime.py` does `from . import lane_hooks`, and that package imports
    every `lane_*.py` module beside it at process start.  So the sentence
    "`runtime.py` does not call it" and the sentence "nothing sends this
    frame" were never the same sentence, and `sent_by=module_only` was the
    second one printed off a measurement of the first.  These tests build the
    tree that separates them.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.runtime = self.dir / "runtime.py"
        self.runtime.write_text(
            "from . import lane_hooks\n", encoding="utf-8"
        )
        self.hooks = self.dir / "lane_hooks"
        self.hooks.mkdir()

    def _hook(self, name, body):
        (self.hooks / name).write_text(body, encoding="utf-8")

    def test_a_hook_that_calls_the_entry_point_is_named_not_hidden(self):
        self._hook(
            "lane_cs_skill_list.py",
            "def on_login(legacy, store, cid):\n"
            "    return %s(legacy, store, cid)\n"
            % skill_list_at_login.LOGIN_SEAM_SYMBOL,
        )
        self.assertEqual(
            "hook:lane_cs_skill_list",
            skill_list_at_login.seam_carrier(self.runtime, self.hooks),
        )

    def test_before_this_round_the_same_tree_read_module_only(self):
        """The defect itself, run as a test: runtime alone cannot see it."""
        self._hook(
            "lane_cs_skill_list.py",
            "x = %s(1, 2, 3)\n" % skill_list_at_login.LOGIN_SEAM_SYMBOL,
        )
        runtime_only = skill_list_at_login.seam_carrier(
            self.runtime, self.dir / "no_such_hooks"
        )
        self.assertEqual("module_only", runtime_only)
        self.assertNotEqual(
            runtime_only,
            skill_list_at_login.seam_carrier(self.runtime, self.hooks),
        )

    def test_a_file_the_package_never_imports_is_not_a_carrier(self):
        """`_discover()` skips every name that is not `lane_*`."""
        self._hook(
            "helper_skill_list.py",
            "x = %s(1, 2, 3)\n" % skill_list_at_login.LOGIN_SEAM_SYMBOL,
        )
        self.assertEqual(
            "module_only",
            skill_list_at_login.seam_carrier(self.runtime, self.hooks),
        )

    def test_a_comment_in_a_hook_is_not_a_carrier_either(self):
        self._hook(
            "lane_cs_skill_list.py",
            "# TODO: call %s here\n" % skill_list_at_login.LOGIN_SEAM_SYMBOL,
        )
        self.assertEqual(
            "module_only",
            skill_list_at_login.seam_carrier(self.runtime, self.hooks),
        )

    def test_runtime_wins_when_both_call_it(self):
        self.runtime.write_text(
            "from . import lane_hooks\n"
            "frame = %s(legacy, store, cid)\n"
            % skill_list_at_login.LOGIN_SEAM_SYMBOL,
            encoding="utf-8",
        )
        self._hook(
            "lane_cs_skill_list.py",
            "x = %s(1, 2, 3)\n" % skill_list_at_login.LOGIN_SEAM_SYMBOL,
        )
        self.assertEqual(
            "runtime",
            skill_list_at_login.seam_carrier(self.runtime, self.hooks),
        )

    def test_the_named_hook_is_the_first_in_filename_sort_order(self):
        """The package promises that order and nothing else; so does this."""
        for name in ("lane_zz_last.py", "lane_aa_first.py"):
            self._hook(
                name, "x = %s(1, 2, 3)\n" % skill_list_at_login.LOGIN_SEAM_SYMBOL
            )
        self.assertEqual(
            "hook:lane_aa_first",
            skill_list_at_login.seam_carrier(self.runtime, self.hooks),
        )

    def test_a_hook_that_does_not_parse_is_stepped_over_not_fatal(self):
        """`_discover()` prints IMPORT_FAILED and keeps going; so does this."""
        self._hook("lane_aa_broken.py", "def (\n")
        self._hook(
            "lane_bb_real.py",
            "x = %s(1, 2, 3)\n" % skill_list_at_login.LOGIN_SEAM_SYMBOL,
        )
        self.assertEqual(
            "hook:lane_bb_real",
            skill_list_at_login.seam_carrier(self.runtime, self.hooks),
        )

    def test_the_live_tree_answers_runtime_and_the_call_is_really_there(self):
        """Measured, not assumed: `runtime.py` CALLS the seam symbol today.

        This asserted `module_only` until round `ixbs2f` wired the seam, and
        went red on the first run after it -- which is the whole point of
        reading the tree instead of a constant.  Re-aimed rather than
        deleted, and with the second assertion added because `runtime` is a
        three-state answer: `unknown` also comes back when the file cannot be
        read or parsed, and this test would have passed on `unknown` if it
        only asked "not module_only".
        """
        self.assertEqual("runtime", skill_list_at_login.seam_carrier())
        runtime_source = (SRC / "runtime.py").read_text(encoding="utf-8")
        tree = ast.parse(runtime_source)
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and getattr(
                node.func, "attr", getattr(node.func, "id", ""),
            ) == skill_list_at_login.LOGIN_SEAM_SYMBOL
        ]
        # Exactly one: a second call site would mean two skill frames on one
        # login, which is a thing no attended run has ever measured.
        self.assertEqual(1, len(calls), "call sites: %d" % len(calls))


class TheTokenReportsTheByteTheFrameCarriesTests(_Fixture):
    """pf-adversary D3: the `HEADLESS_PROOF:` line used to print
    `SKILL_LIST_TRAILING_BYTE` straight out of the format string, so it read
    `trailing_u8=0` about a frame whose trailing byte was 0x01 -- an operator
    pasting it into a ticket would have certified the walk-locking frame as
    walkable.  These drive the byte and the constant APART and require the
    line to follow the bytes."""

    def test_the_token_follows_the_payload_not_the_constant(self):
        # Composed by the owner module directly, so the constant is 0 while
        # the frame carries 1 -- the state the old format string could not
        # tell apart from a walkable frame.
        records = skill_list_at_login.skill_list_records((99,))
        pc, frame = make_learn_skill_result_response(self.legacy, records, 1)
        self.assertEqual(0, skill_list_at_login.SKILL_LIST_TRAILING_BYTE)
        line = skill_list_at_login.headless_token(
            1, (99,), frame, "module_only",
            skill_list_at_login.measured_trailing_byte(pc, 1), pc=pc,
        )
        self.assertIn("trailing_u8=1", line)

    def test_the_measurement_answers_zero_for_the_frame_this_module_composes(
        self,
    ):
        pc, _frame = skill_list_at_login.make_skill_list_response(
            self.legacy, (111, 40000, 99, 110),
        )
        self.assertEqual(
            0, skill_list_at_login.measured_trailing_byte(pc, 4)
        )

    def test_an_unreadable_payload_is_its_own_reason_not_the_walk_lock_one(
        self,
    ):
        # pf-adversary D5: two facts, two reasons.  A slice that cannot be
        # decoded says so; it does not claim the walk-lock byte was set.
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.measured_trailing_byte(b"\x00" * 8, 1)
        self.assertEqual(
            skill_list_at_login.REFUSE_PAYLOAD_UNREADABLE,
            caught.exception.reason,
        )
        self.assertNotEqual(
            skill_list_at_login.REFUSE_TRAILING_BYTE_LOCKS_WALKING,
            caught.exception.reason,
        )


class TheRouteRefusesAFrameThatWouldLockWalkingTests(_Fixture):
    """R323C's byte, checked on the bytes rather than on the constant.

    The pins this module already had compared
    ``SKILL_LIST_TRAILING_BYTE`` with the value decoded back out of a frame
    composed FROM that same constant -- both sides move together, so editing
    the constant to 1 left every one of them green while the route composed
    the frame R323C measured as locking the player's movement for the whole
    session.  These tests drive the constant to the locking value and require
    the ROUTE to refuse, which is a property of ``src/``, not of a test file.
    """

    def test_the_ordinary_route_carries_the_walkable_trailing_zero(self):
        # Decoded, not indexed: the frame's LAST byte is an outer `00` that is
        # zero whatever the walk-lock byte says, so `frame[-1] == 0` would
        # pass on a locking frame.  That is the exact reading mistake this
        # class exists to stop, so its own happy-path test may not make it.
        pc, _frame = skill_list_at_login.make_skill_list_response(
            self.legacy, (111, 40000, 99, 110),
        )
        size = (
            LEARN_SKILL_RESULT_PAYLOAD_BASE_SIZE
            + LEARN_SKILL_RESULT_RECORD_WIRE_SIZE * 4
        )
        start = LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET
        _records, trailing = decode_learn_skill_result_payload(
            pc[start:start + size]
        )
        self.assertEqual(0, trailing)

    def test_a_locking_trailing_byte_is_refused_by_name_not_composed(self):
        # The mutant this file could not previously kill: one integer.
        with mock.patch.object(
            skill_list_at_login, "SKILL_LIST_TRAILING_BYTE", 1,
        ):
            with self.assertRaises(SkillListAtLoginError) as caught:
                skill_list_at_login.make_skill_list_response(
                    self.legacy, (111, 40000, 99, 110),
                )
        self.assertEqual(
            skill_list_at_login.REFUSE_TRAILING_BYTE_LOCKS_WALKING,
            caught.exception.reason,
        )

    def test_the_login_entry_point_refuses_it_too_not_only_the_composer(self):
        # `login_skill_list_response` is the one function the CORE-REQUEST
        # asks runtime.py to call, so the guard has to hold on THAT path.
        character = self._with_skills((111, 40000, 99, 110))
        with mock.patch.object(
            skill_list_at_login, "SKILL_LIST_TRAILING_BYTE", 1,
        ):
            with self.assertRaises(SkillListAtLoginError) as caught:
                skill_list_at_login.login_skill_list_response(
                    self.legacy, self.store, character.id,
                )
        self.assertEqual(
            skill_list_at_login.REFUSE_TRAILING_BYTE_LOCKS_WALKING,
            caught.exception.reason,
        )

    def test_the_refusal_reason_names_the_byte_it_saw(self):
        with mock.patch.object(
            skill_list_at_login, "SKILL_LIST_TRAILING_BYTE", 1,
        ):
            with self.assertRaises(SkillListAtLoginError) as caught:
                skill_list_at_login.make_skill_list_response(
                    self.legacy, (99,),
                )
        self.assertIn("0x01", str(caught.exception))

class TheLoginPathActuallySendsItTests(unittest.TestCase):
    """Round `ixbs2f`: the seam, driven through the REAL dispatcher.

    Everything above this class tests the module in isolation, and the module
    was already green for three rounds while both skill tabs stayed empty on a
    real client -- because nothing called it.  These tests dispatch a genuine
    ``StartGameReq`` and ask what came back, which is the only question that
    could have caught that.

    Shape borrowed, deliberately, from `tests/test_gm_login_state_guard.py`'s
    `_login_and_start`: the GM frame beside this one is wired at the same
    site, by the same rule, and two different harnesses for one code path is
    how two lanes come to disagree about what a login does.

    WHAT THESE CANNOT DO, stated rather than implied: no client is in the
    room.  They prove the server composes the frame from the rows and hands
    it to the dispatcher in a known position.  Whether the skill WINDOW fills
    and whether the player can still walk afterwards is `GT-307`, attended,
    and no assertion here is a substitute for it.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def setUp(self):
        from pirateforce_foundation import field_mobs
        from pirateforce_foundation.legacy_bridge import LegacyProjector
        from pirateforce_foundation.lifecycle import CharacterLifecycle
        from pirateforce_foundation.runtime import make_state_class

        self._make_state_class = make_state_class
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", MIGRATIONS,
        )
        self.store.migrate()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        field_mobs.load_roster()

    def _login(self, token="skilluser"):
        """Everything up to, but NOT including, the StartGameReq.

        Split from the start so a test can change the world between the two
        -- `CharacterLifecycle.login` needs the store it is being asked to
        survive losing, so "no store" can only be staged after login.
        """
        state_type = self._make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        return state, character

    def _start(self, state, character):
        return state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))

    def _login_and_start(self, token="skilluser"):
        state, character = self._login(token)
        return state, self._start(state, character), character

    def test_a_normal_login_carries_the_skill_frame(self):
        state, actions, character = self._login_and_start()
        by_label = {action[0]: action for action in actions}
        self.assertIn("SKILL_LIST_AT_LOGIN", by_label)
        _, pc, frame, delay = by_label["SKILL_LIST_AT_LOGIN"]
        self.assertEqual(0.0, delay)
        # The bytes are the composer's, byte for byte, off the SAME rows --
        # not a second route built for the test.
        rows = self.store.list_character_skills(character.id)
        expected_pc, expected_frame = (
            skill_list_at_login.make_skill_list_response(self.legacy, rows)
        )
        self.assertEqual(expected_pc, pc)
        self.assertEqual(expected_frame, frame)
        # A FIXED event name, not one with the byte count baked into it:
        # pf-adversary D8 pointed out that the same commit arguing for
        # `.reason` over `args[0]` (because other lanes match this list by
        # equality) then put a varying number in the name.  The count is on
        # the console line instead, where a varying number belongs.
        self.assertIn("skill_list_at_login_sent", state.events)

    def test_the_byte_that_locks_walking_is_zero_on_what_the_login_sent(self):
        """R323C: trailing u8 == 1 locks walking, == 0 walks.

        Measured off the pc the DISPATCHER handed out, decoded through the
        module's own `measured_trailing_byte`.  Reading the constant here
        instead would test that a constant equals itself.
        """
        _state, actions, character = self._login_and_start()
        by_label = {action[0]: action for action in actions}
        pc = by_label["SKILL_LIST_AT_LOGIN"][1]
        rows = self.store.list_character_skills(character.id)
        self.assertEqual(
            0, skill_list_at_login.measured_trailing_byte(pc, len(rows)),
        )

    def test_it_rides_behind_start_game_and_the_teleport_never_in_front(self):
        _state, actions, _character = self._login_and_start()
        labels = [action[0] for action in actions]
        self.assertEqual("SKILL_LIST_AT_LOGIN", labels[-1])
        # Named, not just "last": the two frames whose bytes and order this
        # seam promised not to disturb have to still BE there, in front.
        start_game = [
            index for index, label in enumerate(labels)
            if "START_GAME" in label
        ]
        teleport = [
            index for index, label in enumerate(labels) if "TELEPORT" in label
        ]
        self.assertTrue(start_game, "no START_GAME action at all: %r" % labels)
        self.assertTrue(teleport, "no teleport action at all: %r" % labels)
        self.assertLess(max(start_game), len(labels) - 1)
        self.assertLess(max(teleport), len(labels) - 1)

    def test_the_frame_follows_the_rows_and_not_the_class_table(self):
        """Move the ROWS; the login frame has to move with them.

        This is the assertion the whole order rests on (COO-DECISION
        `20260908_1541`, and the module's own header): the ids on the wire
        are THIS CHARACTER's persisted rows, so a grant or a revoke shows up
        at the next login.  The substituted ids are deliberately ones the
        class table does not contain -- a seam that read
        `class_catalog.starting_skill_ids` would pass every other test in
        this class and fail this one, and would fail it with the CLASS ids
        in the frame rather than with a length mismatch that could be
        anything.
        """
        state, character = self._login()
        rows = self.store.list_character_skills(character.id)
        self.assertEqual((111, 40000, 99, 110), rows)
        substitute = (777, 778)
        self.assertFalse(
            set(substitute) & set(starting_skill_ids(1)),
            "the substitute ids have to be absent from the class table",
        )
        with mock.patch.object(
            SQLiteStore, "list_character_skills",
            lambda self, cid: substitute,
        ):
            actions = self._start(state, character)
        frame = {a[0]: a for a in actions}["SKILL_LIST_AT_LOGIN"][2]
        expected_pc, expected_frame = (
            skill_list_at_login.make_skill_list_response(
                self.legacy, substitute,
            )
        )
        self.assertEqual(expected_frame, frame)
        # And not the class ids, said as its own assertion rather than
        # inferred from the equality above.
        class_pc, class_frame = skill_list_at_login.make_skill_list_response(
            self.legacy, rows,
        )
        self.assertNotEqual(class_frame, frame)

    def test_a_character_with_no_rows_gets_no_frame_and_a_named_event(self):
        """The refusal path, driven through the dispatcher.

        `read_character_skill_ids` refuses an empty result BY NAME rather
        than composing a count-0 frame (its docstring says why).  What this
        adds is that the refusal reaches the login as a missing action and a
        NAMED event -- not as an exception out of the listener thread, which
        is what an uncaught one would be for every player on every login.

        The event's exact spelling is asserted, and that caught a real one:
        the seam appended `error.args[0]`, which is the human sentence, so
        the event read `skill_list_at_login_refused_character 1 has no rows
        in character_skills; sending a count-0 frame would assert an empty
        skill list...` -- a paragraph, with spaces, in a list other lanes
        match against by equality.
        """
        state, character = self._login()
        with mock.patch.object(
            SQLiteStore, "list_character_skills", lambda self, cid: (),
        ):
            actions = self._start(state, character)
        self.assertNotIn(
            "SKILL_LIST_AT_LOGIN", [action[0] for action in actions],
        )
        self.assertIn(
            "skill_list_at_login_refused_%s"
            % skill_list_at_login.REFUSE_NO_SKILL_ROWS,
            state.events,
        )

    def test_the_flag_is_a_real_kill_switch_not_a_decoration(self):
        """pf-adversary D1, paid in round `ixbs2f`.

        The first draft flipped `production_allowed` to True and then never
        read it: the seam called the module unconditionally, and the ONLY
        consumer of that flag in the whole tree was a test asserting it was
        True.  So an operator who watched players stop walking and set it
        back to False would have changed nothing, and backing the frame out
        would have meant editing `runtime.py` and redeploying.

        That is not hypothetical for this frame in particular: the only
        escape GT-249 ever recorded from its walk-lock was a relog, and a
        relog is what re-sends this.  A feature whose failure mode is
        "nobody can move" needs a switch that is not a code change.
        """
        state, character = self._login()
        with mock.patch.object(
            skill_list_at_login, "production_allowed", False,
        ):
            actions = self._start(state, character)
        self.assertNotIn(
            "SKILL_LIST_AT_LOGIN", [action[0] for action in actions],
        )
        self.assertIn(
            "skill_list_at_login_withheld_not_production_allowed",
            state.events,
        )
        # ...and the rest of the login is untouched: the switch withholds one
        # frame, it does not break the login it rides on.
        labels = [action[0] for action in actions]
        self.assertTrue([x for x in labels if "START_GAME" in x], labels)
        self.assertTrue([x for x in labels if "TELEPORT" in x], labels)

    def test_a_store_error_costs_the_skill_frame_and_nothing_else(self):
        """pf-adversary D4, paid in round `ixbs2f`, with adversary's own input.

        The seam caught `SkillListAtLoginError` alone, on the module's
        contract that it raises nothing else.  That contract covers what the
        MODULE decides, not what the store does underneath it: adversary made
        `list_character_skills` raise `sqlite3.OperationalError("database is
        locked")` and watched it leave `dispatch()` entirely.  v141 wraps the
        per-connection loop in try/finally with no except, so the thread
        unwinds and the client parks on "connecting" -- and because the seam
        runs BEFORE the action list is built, a locked database in the SKILL
        LIST cost the player their START_GAME_RES and their teleport too.

        The assertion that matters is the last two: the login SURVIVES.
        """
        state, character = self._login()

        def locked(self, cid):
            raise sqlite3.OperationalError("database is locked")

        with mock.patch.object(SQLiteStore, "list_character_skills", locked):
            actions = self._start(state, character)
        self.assertNotIn(
            "SKILL_LIST_AT_LOGIN", [action[0] for action in actions],
        )
        # Named by CLASS, so the operator gets a bug report and not an empty
        # window with no explanation.
        self.assertIn(
            "skill_list_at_login_failed_OperationalError", state.events,
        )
        labels = [action[0] for action in actions]
        self.assertTrue([x for x in labels if "START_GAME" in x], labels)
        self.assertTrue([x for x in labels if "TELEPORT" in x], labels)

    def test_every_branch_says_something_on_a_flagless_console(self):
        """pf-adversary D3: events reach the console only under
        `--export-events`, and this seam is on for the boot that does not
        pass it.  A refusal used to be visible only as the ABSENCE of a line
        the operator had to know to look for, while the write half printed
        `CHARACTER_STARTING_SKILLS ... written` right next to it.

        All three branches are driven, and each has to print.
        """
        cases = []
        state, character = self._login("printuser1")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self._start(state, character)
        cases.append(("sent", out.getvalue()))

        state, character = self._login("printuser2")
        with mock.patch.object(
            SQLiteStore, "list_character_skills", lambda self, cid: (),
        ), contextlib.redirect_stdout(io.StringIO()) as out:
            self._start(state, character)
        cases.append(("refused", out.getvalue()))

        state, character = self._login("printuser3")
        with mock.patch.object(
            skill_list_at_login, "production_allowed", False,
        ), contextlib.redirect_stdout(io.StringIO()) as out:
            self._start(state, character)
        cases.append(("withheld", out.getvalue()))

        for name, printed in cases:
            with self.subTest(branch=name):
                lines = [
                    line for line in printed.splitlines()
                    if line.startswith("SKILL_LIST_AT_LOGIN ")
                ]
                self.assertEqual(1, len(lines), printed)
                # cp874: the bridge console cannot carry anything else.
                lines[0].encode("cp874")

    def test_a_lifecycle_without_a_store_never_reaches_the_seam_at_all(self):
        """Why the seam does NOT guard `lifecycle.store`, measured.

        The seam first carried a `getattr(..., None)` and a named refusal for
        a store-less lifecycle, copying session.py's defensive shape.  This
        test was written to drive that refusal and could not: the login dies
        two frames earlier, in `select_and_start` -> `lifecycle.select` ->
        `store.select_character`, before the seam is reached.  So the guard
        was removed, and this stayed -- pointing at the call that makes it
        unnecessary.  If some future round moves the seam ABOVE
        `select_and_start`, this goes green in a new way (no AttributeError,
        or one raised from the seam's own line) and the guard has to come
        back with it.
        """
        state, character = self._login()
        del self.lifecycle.store
        # Caught by hand, not with assertRaises: that context manager strips
        # the traceback off the exception it hands back (to break reference
        # cycles), and the traceback is the whole evidence here.
        frames = []
        try:
            self._start(state, character)
        except AttributeError as error:
            self.assertIn("store", str(error))
            traceback = error.__traceback__
            while traceback is not None:
                frames.append(traceback.tb_frame.f_code.co_name)
                traceback = traceback.tb_next
        else:                                # pragma: no cover - see below
            self.fail(
                "a store-less lifecycle now survives to the seam; the guard "
                "removed in round `ixbs2f` has to come back"
            )
        self.assertIn("select_and_start", frames)
        self.assertNotIn(
            "login_skill_list_response", frames,
            "the seam was reached after all: %r" % (frames,),
        )


class TheTokenMeasuresTheWireAndTheCapIsPinnedTests(unittest.TestCase):
    """pf-adversary round `jty60h`, findings D3 and D4, paid here.

    Both findings are about the same failure shape: a number that an
    operator pastes into a ticket, or that a COO decision rests its whole
    weight on, with nothing in the repository that turns red when it stops
    being true.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_the_token_refuses_when_the_wire_and_the_row_disagree(self):
        """D3: the mutant that composes a shorter frame than it reports.

        The store's list and the composed pc are two separate answers to
        "how many skills does this character have"; before this round the
        token printed the first one and never looked at the second, so a
        seam that composed four records and appended nothing, or composed a
        one-record frame off a stale list, produced a healthy-looking
        ``rows=4`` line.  There is no assertion here that ``rows`` equals a
        constant -- that would be the same defect one layer up.
        """
        pc, frame = skill_list_at_login.make_skill_list_response(
            self.legacy, (111,),
        )
        with self.assertRaises(skill_list_at_login.SkillListAtLoginError) as caught:
            skill_list_at_login.headless_token(
                1, (111, 40000, 99, 110), frame, "runtime", 0, pc=pc,
            )
        self.assertEqual(
            skill_list_at_login.REFUSE_PAYLOAD_UNREADABLE,
            caught.exception.reason,
        )
        self.assertIn("1 records", str(caught.exception))
        self.assertIn("4 skill ids", str(caught.exception))

    def test_the_row_count_in_the_token_is_read_out_of_the_composed_bytes(self):
        """D3: and it really is the wire that answers, not the argument.

        The pc is mutated in place at the count field's own offset, so the
        list handed in stays four ids long while the bytes say three.  A
        token built from ``len(skill_ids)`` cannot notice.
        """
        pc, frame = skill_list_at_login.make_skill_list_response(
            self.legacy, (111, 40000, 99, 110),
        )
        self.assertEqual(4, skill_list_at_login.measured_record_count(pc))
        start = skill_list_at_login.LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET
        shortened = bytearray(pc)
        shortened[start + 1:start + 3] = (3).to_bytes(2, "little")
        with self.assertRaises(skill_list_at_login.SkillListAtLoginError):
            skill_list_at_login.headless_token(
                1, (111, 40000, 99, 110), frame, "runtime", 0,
                pc=bytes(shortened),
            )

    def test_a_byte_string_that_never_was_a_frame_cannot_answer(self):
        """D3: the count field is decoded, not merely read."""
        for pretender in (b"", b"x" * 50, bytes(64)):
            with self.assertRaises(skill_list_at_login.SkillListAtLoginError):
                skill_list_at_login.measured_record_count(pretender)

    def test_the_observed_cap_of_four_is_pinned_to_what_was_observed(self):
        """D4: ``OBSERVED_ACCEPTED_RECORD_COUNT`` had no pin at all.

        ``COO-DECISION 20260908_1742`` ("the cap of four stands") rests its
        whole ruling on this constant, and pf-adversary raised it to 255
        with the suite still green.  The pin is not a taste: four is
        ``GT-249``'s ``COUNT4_REAL_SKILL_IDS_CLASS1_TRAIL0``, the largest
        count a real client has ever been measured accepting, and raising it
        is an attended result's job.  The behaviour is pinned beside the
        value, so deleting the equality alone does not free the cap.
        """
        self.assertEqual(4, skill_list_at_login.OBSERVED_ACCEPTED_RECORD_COUNT)
        rows = (111, 40000, 99, 110)
        pc, _frame = skill_list_at_login.make_skill_list_response(
            self.legacy, rows,
        )
        self.assertEqual(4, skill_list_at_login.measured_record_count(pc))
        with self.assertRaises(skill_list_at_login.SkillListAtLoginError) as caught:
            skill_list_at_login.make_skill_list_response(
                self.legacy, rows + (112,),
            )
        self.assertEqual(
            skill_list_at_login.REFUSE_TOO_MANY_UNMEASURED,
            caught.exception.reason,
        )

    def test_the_cap_is_below_the_wire_field_it_lives_in(self):
        """D4: and it is a policy floor, not the u16 the serializer allows.

        A round that raises the cap to the wire maximum has not measured
        anything; this keeps the two numbers from quietly becoming one.
        """
        self.assertLess(
            skill_list_at_login.OBSERVED_ACCEPTED_RECORD_COUNT,
            skill_list_at_login.WIRE_MAX_RECORDS,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
