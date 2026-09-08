"""LANE-GM: `/job <class_id>` and `/skill all` -- the GM skill sandbox.

PANYA-ORDER 2026-09-08 ~14:5x (`pf_bridge/notes_to_chief/20260908_1455_KA1A-
PANYA-ORDER-COO-gm-sandbox-skill-all-job-no-level-gate-class-weapons.md`),
routed by `COO-DECISION 20260908_1541`.

THE THREE LAYERS THIS FILE KEEPS APART, because the house rule is that one
may never be used to argue another:

  * THE ARGUMENT.  `JobArgumentTests` / `SkillArgumentTests` ask what the two
    parsers accept, against the COMMITTED tables rather than against literals
    typed here -- the five class ids come from `class_catalog` and the skill
    ids from `class_skill_curriculum`, so a table that moves turns these red
    instead of leaving a stale number in a command that writes rows.
  * THE ROW.  `JobPersistenceTests` / `SkillPersistenceTests` ask whether the
    rows really changed, against a REAL `SQLiteStore` on a temp file, read
    back through a SECOND store opened on the same file -- the closest a
    headless test gets to "the GM logs in again tomorrow".
  * THE REFUSAL.  `RefusalIsRealTests` RUNS the refusal a non-GM account
    gets and then asks the store what it holds.  PANYA-ORDER section 3 item
    2 requires exactly this and forbids the alternative in as many words:
    the test may not grep this lane's own message, it has to measure that no
    row was written.

NONE OF THEM IS A SCREEN.  Nothing in this file has a client in it; the
on-screen half belongs to the attended ticket, and this file's job is to make
sure that ticket is testing something real when it gets there.
"""
from __future__ import annotations

import io
import json
import os
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import class_catalog  # noqa: E402
from pirateforce_foundation import class_skill_curriculum  # noqa: E402
from pirateforce_foundation import persistence_typed_attrs  # noqa: E402
from pirateforce_foundation import session as session_module  # noqa: E402
from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import commands as gm_commands  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import job_command  # noqa: E402
from pirateforce_foundation.gm import say_wire  # noqa: E402
from pirateforce_foundation.gm import skill_all_command  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"

# Deliberately NOT the canonical filename: the run-copy gate stands above
# every write path here, so a default that tripped it would make the whole
# file pass for the wrong reason.
RUN_COPY_DB_PATH = "state/pirateforce_gm_sandbox_20260908_1612.sqlite3"


def make_chat_payload(message: str, speaker: str = "") -> bytes:
    """0xAC52 payload in the GT-006/GT-009 measured shape."""
    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


class FakeSelected:
    def __init__(self, character_id=1):
        self.id = character_id
        self.identity_lo = 1
        self.identity_hi = 0


class FakeStore:
    """`.path` for the run-copy gate plus the two LANE-DB doors used here.

    The signatures are copied from the real `store.SQLiteStore` methods.  The
    persistence classes below run the same commands against a REAL store, so
    this double is never the only thing the wiring is proven against.
    """

    def __init__(self, path=RUN_COPY_DB_PATH):
        self.path = path
        self.writes = []
        self.grants = []
        self.stored = {}
        self.skills = []
        self.raises = None
        self.grant_raises = None
        #: Set to make the read-back DISAGREE with what was asked for -- the
        #: one `/job` refusal that leaves the row's state unknown.
        self.readback_override = None

    def read_typed_attributes(self, character_id):
        """The COLUMN door.  A NULL column is OMITTED, never rendered as 0."""
        return dict(self.stored)

    def write_typed_attributes(self, character_id, values):
        self.writes.append((character_id, dict(values)))
        if self.raises is not None:
            raise self.raises
        self.stored.update(values)
        if self.readback_override is not None:
            return {"class_id": self.readback_override}
        return dict(self.stored)

    def list_character_skills(self, character_id):
        return tuple(self.skills)

    def grant_learned_skill(self, character_id, skill_id):
        self.grants.append((character_id, skill_id))
        if self.grant_raises is not None:
            raise self.grant_raises
        if skill_id not in self.skills:
            self.skills.append(skill_id)
        return tuple(self.skills)


class FakeLifecycle:
    def __init__(self, store):
        self.store = store


class FakeFoundation:
    def __init__(self, selected, store):
        self.selected = selected
        self.lifecycle = None if store is None else FakeLifecycle(store)


_DEFAULT = object()


class FakeSession:
    def __init__(self, token="GM_ONE", selected=_DEFAULT, store=_DEFAULT):
        self.token = token
        self.events = []
        if selected is _DEFAULT:
            selected = FakeSelected()
        if store is _DEFAULT:
            store = FakeStore()
        self.foundation = FakeFoundation(selected, store)


def _build_wire(selector):
    return b"wire", b"avatar", 0x20000001 + selector, 0


class _Case(unittest.TestCase):
    GM_ACCOUNT = "GM_ONE"
    PLAYER_ACCOUNT = "DECKHAND"

    def setUp(self):
        gm_dispatch.reset_rate_limit_state_for_tests()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.config_path = self.tmp / "gm_accounts.json"
        self.config_path.write_text(
            json.dumps({"gm_accounts": [self.GM_ACCOUNT]}), encoding="utf-8"
        )
        self.log_path = self.tmp / "capture" / "gm_command_log.ndjson"
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def act(self, session, text):
        return chat_command_action.make_gm_chat_command_action(
            session,
            make_chat_payload(text),
            self.legacy,
            config_path=str(self.config_path),
            log_path=str(self.log_path),
        )

    def act_capturing_stderr(self, session, text):
        """The same call, with the SERVER CONSOLE captured.

        The console lines are an interface here, not decoration: the owner's
        `HEADLESS_PROOF:` block greps for `GM_JOB` / `GM_SKILL_ALL`, so the
        tests below read what really reached stderr rather than asserting
        that a formatter would have produced it.
        """
        err = io.StringIO()
        with redirect_stderr(err):
            action = self.act(session, text)
        return action, err.getvalue()

    def log_records(self):
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def outcomes(self):
        return [r.get("outcome") for r in self.log_records() if "outcome" in r]

    def store_of(self, session):
        return session.foundation.lifecycle.store


# ---------------------------------------------------------------------------
# THE ARGUMENT
# ---------------------------------------------------------------------------
class JobArgumentTests(_Case):
    """`parse_class_id` -- the second check, deliberately."""

    def test_each_of_the_five_class_ids_parses(self):
        for class_id in class_catalog.CLASS_IDS:
            self.assertEqual(job_command.parse_class_id((str(class_id),)), class_id)

    def test_the_accepted_set_is_the_catalogs_and_not_a_literal(self):
        # The whole point of this test: a class added to (or removed from)
        # the client's own `CHARCREATE_CLASS` table must move this command,
        # not leave it accepting a set nobody else believes in.
        self.assertEqual(job_command.class_ids(), tuple(class_catalog.CLASS_IDS))

    def test_the_grammar_sentence_and_the_module_sentence_agree(self):
        # Two places spell the five values -- `COMMAND_USAGE["job"]`, which a
        # human reads on a parse refusal, and `job_command.usage()`, which a
        # human reads on a catalog refusal.  A drift between them would have
        # the server telling a GM two different things about the same
        # command, which is the failure mode `COMMAND_USAGE`'s own comment
        # was written about.
        self.assertEqual(gm_commands.COMMAND_USAGE["job"], job_command.usage())

    def test_a_bitmask_gap_is_refused_naming_what_is_accepted(self):
        # `3` is the trap the bitmask sets: a human reading `job <class_id>`
        # types 1..5 and 3 is not a class.  It must be refused WITH the five
        # values, never silently, and never guessed to the nearest.
        with self.assertRaises(job_command.JobArgumentError) as caught:
            job_command.parse_class_id(("3",))
        self.assertEqual(
            caught.exception.reason, job_command.REFUSED_NOT_A_CLASS_ID
        )
        for class_id in class_catalog.CLASS_IDS:
            self.assertIn(str(class_id), caught.exception.detail)

    def test_zero_is_not_a_class(self):
        with self.assertRaises(job_command.JobArgumentError) as caught:
            job_command.parse_class_id(("0",))
        self.assertEqual(
            caught.exception.reason, job_command.REFUSED_NOT_A_CLASS_ID
        )

    def test_a_hand_built_args_shape_is_refused_here_too(self):
        # `GmCommand` is a plain dataclass; a caller can hand-build one.  The
        # tuple SUBCLASS is the shape that defeated an `isinstance` allowlist
        # in this lane before (`gm/commands.py::GmCommandArgsError`).
        class Liar(tuple):
            def __len__(self):
                return 1

            def __getitem__(self, index):
                return "1"

        for bad in (None, ["1"], {0: "1"}, ("1", "2"), (1,), Liar()):
            with self.assertRaises(job_command.JobArgumentError) as caught:
                job_command.parse_class_id(bad)
            self.assertEqual(
                caught.exception.reason, job_command.REFUSED_ARGS_SHAPE
            )

    def test_the_column_written_is_the_class_column(self):
        self.assertEqual(job_command.class_column(), "class_id")
        self.assertEqual(
            job_command.class_column(),
            persistence_typed_attrs.column_for(job_command.CLASS_FIELD_X),
        )


class SkillArgumentTests(_Case):
    def test_all_is_the_one_form_and_case_does_not_matter(self):
        self.assertEqual(skill_all_command.parse_subcommand(("all",)), "all")
        self.assertEqual(skill_all_command.parse_subcommand((" ALL ",)), "all")

    def test_any_other_word_is_refused_naming_the_form_that_works(self):
        with self.assertRaises(skill_all_command.SkillArgumentError) as caught:
            skill_all_command.parse_subcommand(("raw",))
        self.assertEqual(
            caught.exception.reason, skill_all_command.REFUSED_UNKNOWN_SUBCOMMAND
        )
        self.assertIn(skill_all_command.usage(), caught.exception.detail)

    def test_the_id_list_is_the_committed_table_and_not_a_literal(self):
        # PANYA-ORDER section 2.1 forbids a hardcoded id list in as many
        # words.  This is the test that makes that enforceable.
        self.assertEqual(
            skill_all_command.all_skill_ids(),
            tuple(class_skill_curriculum.CURRICULUM_SKILL_IDS),
        )
        self.assertEqual(
            len(skill_all_command.all_skill_ids()),
            class_skill_curriculum.SKILL_COUNT,
        )

    def test_the_source_file_contains_no_skill_id_literal(self):
        # The same rule, enforced against the FILE rather than the accessor:
        # a future edit that pastes a list of ids in as a fallback would pass
        # the test above (the accessor still reads the table) and fail here.
        source = Path(skill_all_command.__file__).read_text(encoding="utf-8")
        for skill_id in class_skill_curriculum.CURRICULUM_SKILL_IDS:
            self.assertNotIn(str(skill_id), source)

    def test_the_shared_1024_bucket_is_included_and_named(self):
        # PANYA-ORDER section 2.1: grant it WITH the five and say so out loud.
        # `class_skill_curriculum`'s docstring records that what 1024 MEANS is
        # still not proven -- which is exactly why the console line names the
        # code instead of folding it silently into a class.
        self.assertIn(
            class_skill_curriculum.SHARED_BUCKET_CODE,
            skill_all_command.bucket_codes(),
        )
        for skill_id in class_skill_curriculum.SHARED_BUCKET_SKILL_IDS:
            self.assertIn(skill_id, skill_all_command.all_skill_ids())
        for class_id in class_catalog.CLASS_IDS:
            self.assertIn(class_id, skill_all_command.bucket_codes())


# ---------------------------------------------------------------------------
# THE CONSOLE LINES (an interface: the owner's HEADLESS_PROOF greps them)
# ---------------------------------------------------------------------------
class ConsoleTokenTests(_Case):
    def test_the_job_line_carries_every_field_the_order_names(self):
        session = FakeSession()
        self.store_of(session).stored["class_id"] = 1
        _, err = self.act_capturing_stderr(session, "/job 16")
        line = self._one_line(err, job_command.CONSOLE_TOKEN)
        for field in (
            "cid=1",
            "class_id_from=1",
            "class_id_to=16",
            "relog_required=yes",
        ):
            self.assertIn(field, line)

    def test_a_null_class_column_reads_as_none_and_never_as_zero(self):
        # `migrations/006` adds `class_id` with no default and no backfill, so
        # NULL is the ordinary state of an older row.  `0` is a class id
        # nobody has; printing it would be this lane inventing a previous
        # class for the audit.
        session = FakeSession()
        _, err = self.act_capturing_stderr(session, "/job 2")
        self.assertIn("class_id_from=none", err)

    def test_the_skill_line_carries_every_field_the_order_names(self):
        session = FakeSession()
        _, err = self.act_capturing_stderr(session, "/skill all")
        line = self._one_line(err, skill_all_command.CONSOLE_TOKEN)
        self.assertIn("cid=1", line)
        self.assertIn(
            f"granted={class_skill_curriculum.SKILL_COUNT}", line
        )
        self.assertIn("already=0", line)
        for code in skill_all_command.bucket_codes():
            self.assertIn(str(code), line.split("classes=")[1])

    def test_both_lines_start_with_their_token(self):
        # The owner's `HEADLESS_PROOF:` block greps for a line STARTING with
        # the token.  A prefix ahead of it would leave that grep finding
        # nothing while the line was right there.
        session = FakeSession()
        _, err = self.act_capturing_stderr(session, "/job 32")
        self.assertTrue(
            self._one_line(err, job_command.CONSOLE_TOKEN).startswith(
                job_command.CONSOLE_TOKEN
            )
        )
        gm_dispatch.reset_rate_limit_state_for_tests()
        _, err = self.act_capturing_stderr(session, "/skill all")
        self.assertTrue(
            self._one_line(err, skill_all_command.CONSOLE_TOKEN).startswith(
                skill_all_command.CONSOLE_TOKEN
            )
        )

    def test_neither_line_can_carry_a_byte_the_bridge_console_cannot_print(self):
        # The bridge console is cp874; a byte outside it kills the tool
        # reading the line, not just the line.  A store exception's message
        # is a reachable carrier of foreign text on both refusal paths.
        session = FakeSession()
        self.store_of(session).raises = ValueError("กข broken")
        _, err = self.act_capturing_stderr(session, "/job 1")
        session2 = FakeSession()
        session2.foundation.lifecycle.store.grant_raises = ValueError(
            "กข broken"
        )
        gm_dispatch.reset_rate_limit_state_for_tests()
        _, err2 = self.act_capturing_stderr(session2, "/skill all")
        for text in (err, err2):
            for line in text.splitlines():
                if line.startswith(("GM_JOB", "GM_SKILL_ALL")):
                    self.assertTrue(all(32 <= ord(c) < 127 for c in line), line)

    def _one_line(self, err, token):
        lines = [ln for ln in err.splitlines() if ln.startswith(token)]
        self.assertEqual(len(lines), 1, err)
        return lines[0]


# ---------------------------------------------------------------------------
# THE REFUSAL (PANYA-ORDER section 3 item 2: run it, then ask the store)
# ---------------------------------------------------------------------------
class RefusalIsRealTests(_Case):
    """A non-GM account really types both commands, and nothing is written."""

    def test_a_non_gm_writes_no_class_row(self):
        session = FakeSession(token=self.PLAYER_ACCOUNT)
        self.assertIsNone(self.act(session, "/job 16"))
        self.assertEqual(self.store_of(session).writes, [])
        self.assertEqual(self.store_of(session).stored, {})

    def test_a_non_gm_grants_no_skill_row(self):
        session = FakeSession(token=self.PLAYER_ACCOUNT)
        self.assertIsNone(self.act(session, "/skill all"))
        self.assertEqual(self.store_of(session).grants, [])
        self.assertEqual(self.store_of(session).skills, [])

    def test_the_refusal_is_the_one_shared_allowlist_door(self):
        # PANYA-ORDER section 3 item 1 forbids a second gate.  This asks the
        # SHARED door directly: the reason a non-GM's line stops with is the
        # allowlist's own, and nothing about `/job` or `/skill` appears in it
        # -- the line was never decoded, never parsed, never dispatched.
        for text in ("/job 16", "/skill all"):
            outcome = chat_command.handle_local_talk_chat(
                self.PLAYER_ACCOUNT,
                make_chat_payload(text),
                config_path=str(self.config_path),
                log_path=str(self.log_path),
            )
            self.assertIsNone(outcome.command)
            self.assertEqual(outcome.refusal_reason, chat_command.REFUSAL_NOT_GM)

    def test_a_non_gm_reaches_a_real_store_and_still_writes_nothing(self):
        # The measurement the owner asked for, made against a REAL
        # `SQLiteStore` rather than a double that could simply have no doors:
        # this store CAN write both kinds of row, it is attached to the
        # session, and after both commands the database still holds nothing.
        db_path = self.tmp / "pirateforce_refusal_test.sqlite3"
        store = SQLiteStore(db_path, MIGRATIONS)
        store.migrate()
        account_id = store.ensure_account(self.PLAYER_ACCOUNT)
        character = store.create_character(
            account_id, "Deckhand", "deckhand", "fingerprint-deckhand",
            _build_wire, Position(1, 0, 1.0, 2.0, 3.0, heading=0.0),
        )
        session = FakeSession(
            token=self.PLAYER_ACCOUNT,
            selected=FakeSelected(character_id=character.id),
        )
        session.foundation.lifecycle.store = store
        skills_before = store.list_character_skills(character.id)
        for text in ("/job 16", "/skill all"):
            gm_dispatch.reset_rate_limit_state_for_tests()
            self.assertIsNone(self.act(session, text))
        reopened = SQLiteStore(db_path, MIGRATIONS)
        self.assertNotIn("class_id", reopened.read_typed_attributes(character.id))
        self.assertEqual(
            reopened.list_character_skills(character.id), skills_before
        )

    def test_a_non_gm_line_puts_nothing_on_the_console(self):
        # A MEASURED PROPERTY OF THIS LANE, not an oversight, and it is
        # pinned here so the two new commands cannot be the thing that breaks
        # it: `prompts/LANE-GM.md` sentence 1 says an ordinary player must not
        # be able to tell GM commands exist, and `chat_command.py`'s own
        # refusal tables put `REFUSAL_NOT_GM` in neither printer's set.  So
        # the non-GM refusal is REAL (the three tests above measure it in the
        # database) and SILENT, and the console token an operator greps for a
        # refusal is the one a mistyped command prints -- see
        # `TypoRefusalPrintsTheSharedTokenTests` below.
        session = FakeSession(token=self.PLAYER_ACCOUNT)
        _, err = self.act_capturing_stderr(session, "/job 16")
        self.assertEqual(err, "")

    def test_the_canonical_db_is_refused_for_both_and_nothing_is_written(self):
        for text, outcome in (
            ("/job 16", chat_command_action.OUTCOME_JOB_WITHHELD_CANONICAL_DB),
            (
                "/skill all",
                chat_command_action.OUTCOME_SKILL_WITHHELD_CANONICAL_DB,
            ),
        ):
            gm_dispatch.reset_rate_limit_state_for_tests()
            session = FakeSession(
                store=FakeStore(
                    f"state/{chat_command_action.CANONICAL_DB_FILENAME}"
                )
            )
            self.act(session, text)
            self.assertEqual(self.store_of(session).writes, [])
            self.assertEqual(self.store_of(session).grants, [])
            self.assertIn(outcome, self.outcomes())

    def test_an_unreadable_store_path_counts_as_canonical_for_both(self):
        # Fails CLOSED: "cannot prove this is safe" is treated exactly like
        # "proven canonical".
        for text, outcome in (
            ("/job 16", chat_command_action.OUTCOME_JOB_WITHHELD_CANONICAL_DB),
            (
                "/skill all",
                chat_command_action.OUTCOME_SKILL_WITHHELD_CANONICAL_DB,
            ),
        ):
            gm_dispatch.reset_rate_limit_state_for_tests()
            self.act(FakeSession(store=None), text)
            self.assertIn(outcome, self.outcomes())


class TypoRefusalPrintsTheSharedTokenTests(_Case):
    """A GM who mistypes gets a console line carrying `COMMAND_REFUSED`.

    PANYA-ORDER section 3 item 1 asks for a `COMMAND_REFUSED` console token.
    This is where it comes from for both new commands, and it is the EXISTING
    shared one (`chat_command_action.COMMAND_REFUSED_CONSOLE_TOKEN`) rather
    than a token minted per command -- the same line `/lv` and `/warp` have
    printed since round `9wy444`.
    """

    def test_a_mistyped_job_prints_the_shared_refusal_token(self):
        session = FakeSession()
        _, err = self.act_capturing_stderr(session, "/job banana")
        self.assertIn(chat_command_action.COMMAND_REFUSED_CONSOLE_TOKEN, err)
        self.assertEqual(self.store_of(session).writes, [])

    def test_a_mistyped_skill_prints_the_shared_refusal_token(self):
        session = FakeSession()
        _, err = self.act_capturing_stderr(session, "/skill")
        self.assertIn(chat_command_action.COMMAND_REFUSED_CONSOLE_TOKEN, err)
        self.assertEqual(self.store_of(session).grants, [])

    def test_the_way_out_line_never_echoes_what_was_typed(self):
        # `usage_hint_for`'s founding rule (round `9wy444`, D1): every
        # connection on this listener shares one process-wide token, so a
        # line that echoed the typed text would print a player's words to the
        # operator's console attributed to the operator.
        session = FakeSession()
        _, err = self.act_capturing_stderr(session, "/job kraken")
        self.assertNotIn("kraken", err)


# ---------------------------------------------------------------------------
# THE ROW
# ---------------------------------------------------------------------------
class _RealStoreCase(_Case):
    def setUp(self):
        super().setUp()
        self.addCleanup(self._assert_no_sqlite_handle_survives)
        self.db_path = self.tmp / "pirateforce_gm_sandbox_test.sqlite3"
        self.store = SQLiteStore(self.db_path, MIGRATIONS)
        self.store.migrate()
        account_id = self.store.ensure_account(self.GM_ACCOUNT)
        self.character = self.store.create_character(
            account_id, "SandboxGM", "sandboxgm", "fingerprint-sandbox-gm",
            _build_wire, Position(1, 0, 1.0, 2.0, 3.0, heading=0.0),
        )
        self.session = FakeSession(
            selected=FakeSelected(character_id=self.character.id)
        )
        self.session.foundation.lifecycle.store = self.store

    def _assert_no_sqlite_handle_survives(self):
        # A leaked sqlite handle is what killed PR #495 on the Windows gate
        # (`TemporaryDirectory.cleanup` -> `WinError 32`), a failure Linux
        # never shows.
        fd_dir = "/proc/self/fd"
        if not os.path.isdir(fd_dir):
            return
        root = os.path.realpath(self.tmp)
        held = []
        for fd in os.listdir(fd_dir):
            try:
                target = os.readlink(os.path.join(fd_dir, fd))
            except OSError:
                continue
            if target.startswith(root + os.sep):
                held.append(target)
        self.assertEqual(sorted(held), [])

    def reopened_class_id(self):
        """The row's class read through a SECOND store on the same file."""
        second = SQLiteStore(self.db_path, MIGRATIONS)
        return second.read_typed_attributes(self.character.id).get("class_id")

    def reopened_skills(self):
        second = SQLiteStore(self.db_path, MIGRATIONS)
        return second.list_character_skills(self.character.id)


class JobPersistenceTests(_RealStoreCase):
    def test_the_row_holds_the_new_class_after_the_command(self):
        action = self.act(self.session, "/job 16")
        self.assertEqual(
            action[0], chat_command_action.JOB_SET_NOTICE_ACTION_LABEL
        )
        self.assertEqual(self.reopened_class_id(), 16)
        self.assertIn(
            chat_command_action.OUTCOME_JOB_ROW_WRITTEN, self.outcomes()
        )

    def test_a_second_job_overwrites_the_first(self):
        self.act(self.session, "/job 16")
        gm_dispatch.reset_rate_limit_state_for_tests()
        self.act(self.session, "/job 4")
        self.assertEqual(self.reopened_class_id(), 4)

    def test_a_refused_class_leaves_the_row_exactly_as_it_was(self):
        self.act(self.session, "/job 32")
        before = self.reopened_class_id()
        gm_dispatch.reset_rate_limit_state_for_tests()
        self.act(self.session, "/job 3")
        self.assertEqual(self.reopened_class_id(), before)

    def test_the_next_login_reads_this_exact_column(self):
        # THE ONE QUESTION THE WHOLE DESIGN RESTS ON, asked of the function
        # `session.py` really calls rather than of a copy of its logic: if
        # the login stopped reading this column, `/job` would write a row
        # nobody draws and every attended result taken with it would be
        # measuring the wrong thing.
        self.act(self.session, "/job 2")
        self.assertEqual(
            session_module._class_id_on_the_row(self.store, self.character.id), 2
        )

    def test_login_would_send_agrees_with_the_login_door(self):
        self.act(self.session, "/job 2")
        self.assertTrue(
            job_command.login_would_send(self.store, self.character.id, 2)
        )
        self.assertFalse(
            job_command.login_would_send(self.store, self.character.id, 4)
        )


class SkillPersistenceTests(_RealStoreCase):
    def test_every_curriculum_skill_lands_on_the_row(self):
        action = self.act(self.session, "/skill all")
        self.assertEqual(
            action[0], chat_command_action.SKILL_ALL_NOTICE_ACTION_LABEL
        )
        self.assertEqual(
            set(self.reopened_skills()),
            set(class_skill_curriculum.CURRICULUM_SKILL_IDS),
        )
        self.assertIn(
            chat_command_action.OUTCOME_SKILL_ROWS_WRITTEN, self.outcomes()
        )

    def test_typing_it_twice_writes_nothing_the_second_time(self):
        # PANYA-ORDER section 2.1 requires idempotence in as many words.  The
        # measurement is the ROW SET, not the console line: a second run that
        # duplicated rows would still print a plausible count.
        self.act(self.session, "/skill all")
        first = self.reopened_skills()
        gm_dispatch.reset_rate_limit_state_for_tests()
        _, err = self.act_capturing_stderr(self.session, "/skill all")
        self.assertEqual(self.reopened_skills(), first)
        self.assertEqual(len(first), len(set(first)))
        self.assertIn("granted=0", err)
        self.assertIn(
            f"already={class_skill_curriculum.SKILL_COUNT}", err
        )

    def test_the_skills_a_character_started_with_are_counted_as_already(self):
        # A real character is created holding its starting kit, so the very
        # first `/skill all` on it must report those as `already` rather than
        # claiming to have granted them.
        held = set(self.store.list_character_skills(self.character.id))
        _, err = self.act_capturing_stderr(self.session, "/skill all")
        overlap = held & set(class_skill_curriculum.CURRICULUM_SKILL_IDS)
        self.assertIn(f"already={len(overlap)}", err)
        self.assertIn(
            f"granted={class_skill_curriculum.SKILL_COUNT - len(overlap)}", err
        )

    def test_a_job_change_does_not_take_any_skill_away(self):
        # The sandbox the owner asked for: one character holding EVERY
        # class's skills, moved between classes.  If `/job` dropped rows the
        # sandbox would need a fresh `/skill all` after every change.
        self.act(self.session, "/skill all")
        gm_dispatch.reset_rate_limit_state_for_tests()
        self.act(self.session, "/job 32")
        self.assertEqual(
            set(self.reopened_skills()),
            set(class_skill_curriculum.CURRICULUM_SKILL_IDS),
        )


# ---------------------------------------------------------------------------
# THE DISPATCH CONTRACT
# ---------------------------------------------------------------------------
class DispatchContractTests(_Case):
    def test_neither_command_falls_through_to_the_no_wire_branch(self):
        # The `else` branch of the dispatch chain means "parsed and audited,
        # but this lane has no proven wire".  Both of these DO write, so
        # landing there would audit a command that had an effect as one that
        # did not.
        for text in ("/job 16", "/skill all"):
            gm_dispatch.reset_rate_limit_state_for_tests()
            session = FakeSession()
            self.act(session, text)
            self.assertFalse(
                [
                    event
                    for event in session.events
                    if event.startswith(
                        chat_command_action.EVENT_NO_WIRE_PATH_PREFIX
                    )
                ],
                session.events,
            )

    def test_every_refusal_reason_upstream_has_a_blocker_sentence(self):
        # The lesson `_LV_BLOCKERS`' own comment records: a hand-typed list
        # said five when upstream had ten, and the five that were missing
        # inherited `no blocker recorded` in silence.
        for module, prefix in (
            (job_command, chat_command_action.OUTCOME_JOB_REFUSED_PREFIX),
            (
                skill_all_command,
                chat_command_action.OUTCOME_SKILL_REFUSED_PREFIX,
            ),
        ):
            reasons = [
                value
                for name, value in vars(module).items()
                if name.startswith("REFUSED_") and isinstance(value, str)
            ]
            self.assertTrue(reasons)
            for reason in reasons:
                self.assertIn(
                    f"{prefix}{reason}", chat_command_action.NO_BYTES_BLOCKERS
                )

    def test_every_new_notice_label_has_a_sentence_and_it_is_twelve_ascii(self):
        for label, text in (
            (
                chat_command_action.JOB_SET_NOTICE_ACTION_LABEL,
                say_wire.JOB_SET_NOTICE_TEXT,
            ),
            (
                chat_command_action.JOB_REFUSED_NOTICE_ACTION_LABEL,
                say_wire.JOB_REFUSED_NOTICE_TEXT,
            ),
            (
                chat_command_action.SKILL_ALL_NOTICE_ACTION_LABEL,
                say_wire.SKILL_ALL_NOTICE_TEXT,
            ),
            (
                chat_command_action.SKILL_REFUSED_NOTICE_ACTION_LABEL,
                say_wire.SKILL_REFUSED_NOTICE_TEXT,
            ),
        ):
            self.assertEqual(
                chat_command_action.NOTICE_TEXT_FOR_LABEL[label], text
            )
            self.assertEqual(len(text), say_wire.NOTICE_TEXT_EXACT_LENGTH)
            self.assertTrue(all(32 <= ord(c) < 127 for c in text))
            # `runtime.py`'s `_move_authority_note_server_moves` reopens the
            # move-authority grace window on this exact substring, and
            # neither command moves anybody.
            self.assertNotIn("TELEPORT", label)

    def test_both_outcomes_are_in_the_audit_vocabulary(self):
        self.assertIn(
            gm_commands.OUTCOME_JOB_ROW_WRITTEN, gm_commands.AUDIT_OUTCOMES
        )
        self.assertIn(
            gm_commands.OUTCOME_SKILL_ROWS_WRITTEN, gm_commands.AUDIT_OUTCOMES
        )

    def test_a_store_that_raises_does_not_escape_into_the_listener_thread(self):
        # `runtime.py`'s handler catches only four types and `v141` wraps the
        # connection loop with no `except` at all, so an escaping error parks
        # the client on "connecting".
        session = FakeSession()
        self.store_of(session).raises = RuntimeError("disk went away")
        action = self.act(session, "/job 1")
        self.assertEqual(
            action[0], chat_command_action.JOB_REFUSED_NOTICE_ACTION_LABEL
        )
        gm_dispatch.reset_rate_limit_state_for_tests()
        session2 = FakeSession()
        session2.foundation.lifecycle.store.grant_raises = RuntimeError("gone")
        action2 = self.act(session2, "/skill all")
        self.assertEqual(
            action2[0], chat_command_action.SKILL_REFUSED_NOTICE_ACTION_LABEL
        )

    def test_a_missing_row_stops_the_grant_and_the_counts_still_add_up(self):
        session = FakeSession()
        session.foundation.lifecycle.store.grant_raises = KeyError(1)
        result = skill_all_command.grant_all(self.store_of(session), 1)
        self.assertEqual(result.refusal, skill_all_command.REFUSED_ROW_MISSING)
        self.assertEqual(
            result.granted + result.already + result.failed,
            class_skill_curriculum.SKILL_COUNT,
        )

    def test_a_partial_run_is_a_success_that_says_how_many_failed(self):
        # Some rows landed, so calling it refused would be false; calling it
        # clean would hide the ones that did not.
        class HalfBrokenStore(FakeStore):
            def grant_learned_skill(self, character_id, skill_id):
                if len(self.grants) % 2:
                    self.grants.append((character_id, skill_id))
                    raise ValueError("every other one")
                return super().grant_learned_skill(character_id, skill_id)

        store = HalfBrokenStore()
        result = skill_all_command.grant_all(store, 1)
        self.assertTrue(result.ok)
        self.assertTrue(result.failed)
        self.assertEqual(
            result.granted + result.already + result.failed,
            class_skill_curriculum.SKILL_COUNT,
        )
        self.assertIn("failed=", skill_all_command.console_line(result, 1))


if __name__ == "__main__":
    unittest.main()
