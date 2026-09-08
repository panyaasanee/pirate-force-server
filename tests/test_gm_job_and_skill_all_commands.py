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
import sqlite3
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest import mock
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
    """`.path` for the run-copy gate plus the LANE-DB doors used here.

    The signatures are copied from the real `store.SQLiteStore` methods.  The
    persistence classes below run the same commands against a REAL store, so
    this double is never the only thing the wiring is proven against.
    """

    def __init__(self, path=RUN_COPY_DB_PATH):
        self.path = path
        self.writes = []
        self.grants = []
        self.learned_grants = []
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

    def grant_gm_skills(self, character_id, skill_ids):
        """The BULK door `/skill all` calls, signature copied from the real one.

        Idempotent the way the real one is (`INSERT OR IGNORE`), and it
        records the WHOLE call as ONE entry rather than one per id, so a
        case can tell "one transaction" from "a loop over the ids" by
        counting `self.grants` -- which is the property `COO-DECISION
        20260908_1943` bought and the thing a future refactor could quietly
        take away.
        """
        self.grants.append((character_id, tuple(skill_ids)))
        if self.grant_raises is not None:
            raise self.grant_raises
        for skill_id in skill_ids:
            if skill_id not in self.skills:
                self.skills.append(skill_id)
        return tuple(self.skills)

    def grant_learned_skill(self, character_id, skill_id):
        """The PER-ID door, present ONLY so a case can prove it is unused.

        `/skill all` called this until `COO-DECISION 20260908_1943`; it
        writes `source='learned'`, which is a false sentence about a row an
        operator was handed.  Any call lands in `self.learned_grants` and
        `SkillProvenanceTests` asserts that list stays empty.
        """
        self.learned_grants.append((character_id, skill_id))
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

    def _sources(self):
        """`{skill_id: source}` straight out of the table, reopened.

        CLOSED IN A `finally`, not with a context manager: `sqlite3`'s
        `with` block commits the transaction and leaves the HANDLE open,
        and `_assert_no_sqlite_handle_survives` (the guard PR #495 died
        without, on the Windows gate) counts open handles under the temp
        directory rather than transactions.
        """
        db = sqlite3.connect(self.db_path)
        try:
            rows = db.execute(
                "SELECT skill_id,source FROM character_skills "
                "WHERE character_id=?",
                (self.character.id,),
            ).fetchall()
        finally:
            db.close()
        return {int(r[0]): str(r[1]) for r in rows}

    def test_the_rows_this_command_writes_say_a_gm_granted_them(self):
        # THE POINT OF THE WHOLE SWAP (`COO-DECISION 20260908_1943`, choice
        # 2), asked of the COLUMN rather than of the module: a row an
        # operator was handed must not claim the character learned it.
        # Before the swap every one of these read `'learned'`.
        started_with = set(self.store.list_character_skills(self.character.id))
        self.act(self.session, "/skill all")
        sources = self._sources()
        granted_now = set(sources) - started_with
        self.assertEqual(
            granted_now, set(class_skill_curriculum.CURRICULUM_SKILL_IDS)
        )
        self.assertEqual(
            {sources[skill_id] for skill_id in granted_now}, {"gm_grant"}
        )
        self.assertNotIn("learned", set(sources.values()))

    def test_a_skill_the_character_already_owned_keeps_its_own_provenance(self):
        # `INSERT OR IGNORE`, deliberately not `OR REPLACE`: a skill the
        # character really did learn must not start saying a GM handed it
        # over, or the column stops being able to answer the question it
        # exists for -- and the swap would have traded one false sentence
        # for another.  The row is planted through LANE-DB's OWN learn door,
        # so this measures the two doors against each other rather than
        # against a hand-written INSERT.
        learned_id = class_skill_curriculum.CURRICULUM_SKILL_IDS[0]
        self.store.grant_learned_skill(self.character.id, learned_id)
        before = self._sources()
        self.assertEqual(before.get(learned_id), "learned", before)
        self.act(self.session, "/skill all")
        after = self._sources()
        self.assertEqual(after[learned_id], "learned")
        for skill_id, source in before.items():
            with self.subTest(skill_id=skill_id):
                self.assertEqual(after[skill_id], source)

    def test_the_printed_count_is_the_number_of_rows_that_appeared(self):
        # `COO-DECISION 20260908_1943` makes the counter a condition of the
        # swap, because the owner's `HEADLESS_PROOF:` block greps this
        # number.  Measured against the TABLE, not against the module's own
        # bookkeeping: `granted=` must equal how many rows the file grew by.
        before = len(self._sources())
        _, err = self.act_capturing_stderr(self.session, "/skill all")
        appeared = len(self._sources()) - before
        self.assertTrue(appeared)
        self.assertIn(f"granted={appeared}", err)
        self.assertNotIn("granted_from=", err)

    def test_the_whole_grant_is_one_transaction_over_one_connection(self):
        # The second thing the new door buys, and the one no console line
        # shows: `/skill all` is hundreds of ids and used to be hundreds of
        # `BEGIN IMMEDIATE` transactions, each re-reading the character's
        # whole skill row.  Counted through the store's own `connect`, so a
        # refactor back to a loop turns this red.
        opened = []
        real_connect = self.store.connect

        def counting_connect(*args, **kwargs):
            opened.append(1)
            return real_connect(*args, **kwargs)

        with mock.patch.object(self.store, "connect", counting_connect):
            self.act(self.session, "/skill all")
        # One read of the row, one write transaction, and the audit/readback
        # the dispatcher does around it -- a per-id loop would be at least
        # `SKILL_COUNT` of them.
        self.assertLess(len(opened), class_skill_curriculum.SKILL_COUNT, opened)
        self.assertEqual(
            set(self.reopened_skills()) >= set(
                class_skill_curriculum.CURRICULUM_SKILL_IDS
            ),
            True,
        )

    def test_a_database_without_migration_018_refuses_instead_of_lying(self):
        # THE ONE REGRESSION THIS SWAP COULD CAUSE, measured rather than
        # argued: the old door wrote a value legal since migration 014, the
        # new one writes a value legal only since 018.  On a file stopped at
        # 017 the CHECK rejects every row and `INSERT OR IGNORE` swallows it
        # in silence -- so the door rolls back and this command must REFUSE,
        # not print a clean count over an empty table.  (A normal boot
        # cannot be in this state: `app.py` runs `migrate_with_backup()`
        # before it serves.  A hand-made `--db` copy can.)
        old_db = self.tmp / "stopped_at_017.sqlite3"
        stunted = self.tmp / "migrations_through_017"
        stunted.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if int(path.name[:3]) <= 17:
                (stunted / path.name).write_bytes(path.read_bytes())
        store = SQLiteStore(old_db, stunted)
        store.migrate()
        account_id = store.ensure_account(self.GM_ACCOUNT)
        character = store.create_character(
            account_id, "OldSchema", "oldschema", "fingerprint-old-schema",
            _build_wire, Position(1, 0, 1.0, 2.0, 3.0, heading=0.0),
        )
        held_before = store.list_character_skills(character.id)
        result = skill_all_command.grant_all(store, character.id)
        self.assertEqual(
            result.refusal, skill_all_command.REFUSED_GRANT_ROLLED_BACK
        )
        self.assertEqual(result.granted, 0)
        # AND THE ROW IS UNTOUCHED, which is the half a refusal alone would
        # not prove.
        self.assertEqual(store.list_character_skills(character.id), held_before)

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

    def test_a_missing_row_refuses_with_its_counts_and_writes_nothing(self):
        # pf-adversary (round `wv0fpe`, D4) made this branch print its
        # numbers, because back then it could leave 40 rows on disk while
        # the console read `REFUSED [row_not_found]` with no count anywhere.
        # SINCE THE BULK DOOR the partial write is gone -- `grant_gm_skills`
        # looks the character up as the first statement inside its own
        # transaction, before any INSERT -- so the numbers stay (the row
        # really does hold three) and `granted=0` is now a fact rather than
        # a floor.
        session = FakeSession()
        store = self.store_of(session)
        held = list(class_skill_curriculum.CURRICULUM_SKILL_IDS)[:3]
        store.skills.extend(held)
        store.grant_raises = KeyError(1)
        result = skill_all_command.grant_all(store, 1)
        self.assertEqual(result.refusal, skill_all_command.REFUSED_ROW_MISSING)
        self.assertEqual(result.already, 3)
        self.assertEqual(result.granted, 0)
        self.assertEqual(
            result.failed, class_skill_curriculum.SKILL_COUNT - 3
        )
        self.assertEqual(store.skills, held)
        line = skill_all_command.console_line(result, 1)
        self.assertIn("granted=0", line)
        self.assertIn("already=3", line)

    def test_granted_counts_rows_the_door_really_inserted(self):
        # pf-adversary (round `wv0fpe`, D3), MEASURED: the first draft
        # counted a call as a grant whenever it came back, so a run that
        # inserted nothing printed the full count -- the number the owner's
        # HEADLESS_PROOF block greps.  The door returns its own post-insert
        # id set, read inside its transaction, so a set that did not grow is
        # the door saying INSERT OR IGNORE ignored.
        every = tuple(class_skill_curriculum.CURRICULUM_SKILL_IDS)

        class SomebodyElseGotThereFirstStore(FakeStore):
            """Empty when asked, already full when the grant lands.

            The concurrent case: a second writer put every row in between
            this command's read and its call, so the door inserted NOTHING
            and returned the full set anyway.  Only a count derived from
            the door's own answer can tell, and here it cannot tell either
            -- which is the honest limit `SkillGrant` records rather than
            hides.
            """

            def grant_gm_skills(self, character_id, skill_ids):
                self.grants.append((character_id, tuple(skill_ids)))
                self.skills = list(every)
                return every

        store = SomebodyElseGotThereFirstStore()
        result = skill_all_command.grant_all(store, 1)
        self.assertTrue(result.ok)
        # ONE call, not one per id: the whole grant is one transaction now.
        self.assertEqual(len(store.grants), 1)
        self.assertEqual(store.grants[0][1], every)
        self.assertEqual(result.granted, len(every))
        self.assertTrue(result.counts_are_complete)

        # THE CASE THE COUNT REALLY GUARDS, and the one the wv0fpe defect
        # got wrong: the row is ALREADY full when this command reads it, so
        # the door inserts nothing and returns the same set it was handed.
        # A count read off the door's answer says 0; a count of "the call
        # returned, so they all landed" would say all of them, on the very
        # line the owner's HEADLESS_PROOF block greps.
        settled = FakeStore()
        settled.skills = list(every)
        after = skill_all_command.grant_all(settled, 1)
        self.assertEqual(after.granted, 0)
        self.assertEqual(after.already, len(every))
        self.assertTrue(after.counts_are_complete)

    def test_a_row_another_writer_added_is_not_counted_as_this_grant(self):
        # The door hands back the WHOLE row, not just what it was asked for,
        # so a skill some other writer put there between this command's read
        # and its call would be counted as one `/skill all` granted -- on
        # the line the owner greps.  The count is scoped to the curriculum
        # for that reason.
        every = tuple(class_skill_curriculum.CURRICULUM_SKILL_IDS)
        intruder = max(every) + 9999
        self.assertNotIn(intruder, every)

        class BusyTableStore(FakeStore):
            def grant_gm_skills(self, character_id, skill_ids):
                got = super().grant_gm_skills(character_id, skill_ids)
                return got + (intruder,)

        result = skill_all_command.grant_all(BusyTableStore(), 1)
        self.assertTrue(result.ok)
        self.assertEqual(result.granted, len(every))

    def test_a_door_whose_answer_cannot_be_measured_says_where_the_number_came_from(self):
        # "derived" may not be reported as "measured".  A door that hands
        # back something this module cannot count still made a promise by
        # returning at all -- `grant_gm_skills` rolls back rather than
        # return when an id did not land -- so the number comes from that
        # CONTRACT, and the line says so instead of passing it off as a
        # reading of the row.
        class SilentDoorStore(FakeStore):
            def grant_gm_skills(self, character_id, skill_ids):
                self.grants.append((character_id, tuple(skill_ids)))
                return None

        result = skill_all_command.grant_all(SilentDoorStore(), 1)
        self.assertTrue(result.ok)
        self.assertFalse(result.counts_are_complete)
        self.assertEqual(result.granted, class_skill_curriculum.SKILL_COUNT)
        line = skill_all_command.console_line(result, 1)
        self.assertIn("granted_from=door_contract", line)
        # And the ordinary line does NOT carry it, or the field would be
        # noise rather than a warning.
        clean = skill_all_command.grant_all(FakeStore(), 1)
        self.assertNotIn(
            "granted_from=", skill_all_command.console_line(clean, 1)
        )

    def test_an_unreadable_row_is_refused_rather_than_counted_blind(self):
        # The posture change D3 forced: every number this command prints is
        # derived from reading the row first, so a store that cannot be read
        # gets a named refusal instead of a countable-looking guess -- and
        # NOTHING is written on that branch.
        class UnreadableStore(FakeStore):
            def list_character_skills(self, character_id):
                raise RuntimeError("database is locked")

        store = UnreadableStore()
        result = skill_all_command.grant_all(store, 1)
        self.assertEqual(
            result.refusal,
            skill_all_command.REFUSED_CANNOT_READ_CURRENT_SKILLS,
        )
        self.assertEqual(store.grants, [])

    def test_both_undos_report_the_effect_was_kept_rather_than_vanishing(self):
        # pf-adversary (round `wv0fpe`, D2): `_make_action` runs the undo
        # only when the audit row could not be written, and it tells "the
        # effect was KEPT" from "anything it had in hand was dropped with
        # it" by whether a callable exists at all.  A `/job` on a row whose
        # class was NULL, and every `/skill all`, had no callable -- so the
        # console said the rows were dropped while they sat on disk.
        store = FakeStore()
        kept = job_command.undo(store, 1, None)
        self.assertIsNotNone(kept)
        self.assertIs(kept(), False)
        self.assertIs(skill_all_command.undo(store, 1)(), False)
        # And the real undo still restores when there IS something to put
        # back, so the honest `False` did not cost the working case.
        store.stored["class_id"] = 4
        self.assertIs(job_command.undo(store, 1, 2)(), True)
        self.assertEqual(store.stored["class_id"], 2)

    def test_write_class_id_never_raises_even_if_the_column_map_moves(self):
        # pf-adversary (round `wv0fpe`, D7): `column = class_column()` sat
        # outside every `try`, so the drift `CLASS_FIELD_X`'s own comment
        # guards against escaped as a `TypedAttrError` -- caught one frame
        # up, but leaving an `issued` audit row with no `outcome` row.
        with mock.patch.object(
            job_command, "class_column", side_effect=RuntimeError("x=13 gone")
        ):
            result = job_command.write_class_id(FakeStore(), 1, 16)
        self.assertEqual(result.refusal, job_command.REFUSED_NO_COLUMN)

    def test_a_row_the_login_would_not_read_back_is_refused_and_put_back(self):
        # pf-adversary (round `wv0fpe`, D8): `login_would_send` shipped
        # defined, tested and NEVER CALLED, so the module docstring claimed
        # a gate that did not exist.  It is called now, and it asks the door
        # `session.py` really reads.
        class WriteOnlyStore(FakeStore):
            """The write projects the value; the login's door does not."""

            def read_typed_attributes(self, character_id):
                return dict(self.login_view)

            def __init__(self):
                super().__init__()
                self.login_view = {"class_id": 1}

            def write_typed_attributes(self, character_id, values):
                self.writes.append((character_id, dict(values)))
                self.stored.update(values)
                return dict(self.stored)

        store = WriteOnlyStore()
        result = job_command.write_class_id(store, 1, 16)
        self.assertTrue(
            result.refusal.startswith(job_command.REFUSED_LOGIN_WOULD_NOT_SEND)
        )
        # The row was put back to what the login's door reported.
        self.assertEqual(store.writes[-1][1], {"class_id": 1})

    def test_there_is_no_partial_run_left_for_the_operator_to_read(self):
        # ~~"a partial run is a success that says how many failed"~~ --
        # STRUCK by `COO-DECISION 20260908_1943`.  The per-id loop could
        # write half the curriculum and report the rest as `failed=`; the
        # bulk door is one transaction, so a run either lands whole or
        # leaves the row exactly as it was.  This case pins the SECOND
        # half: the refusal still carries the numbers, and `failed=` now
        # means "ids the row still does not hold" rather than "calls that
        # raised".
        class RolledBackStore(FakeStore):
            def grant_gm_skills(self, character_id, skill_ids):
                self.grants.append((character_id, tuple(skill_ids)))
                raise RuntimeError(
                    "grant_gm_skills: 137 of 137 id(s) for character 1 did "
                    "not reach character_skills (first missing: 7)"
                )

        store = RolledBackStore()
        before = list(store.skills)
        result = skill_all_command.grant_all(store, 1)
        self.assertFalse(result.ok)
        self.assertEqual(
            result.refusal, skill_all_command.REFUSED_GRANT_ROLLED_BACK
        )
        self.assertEqual(result.granted, 0)
        self.assertEqual(result.failed, class_skill_curriculum.SKILL_COUNT)
        self.assertEqual(store.skills, before)
        line = skill_all_command.console_line(result, 1)
        self.assertIn("failed=", line)
        self.assertIn("granted=0", line)
        # The operator is told which door threw the transaction away, and
        # the sentence the dispatcher prints names the remedy.
        self.assertIn(
            "018",
            chat_command_action.NO_BYTES_BLOCKERS[
                chat_command_action.OUTCOME_SKILL_REFUSED_PREFIX
                + skill_all_command.REFUSED_GRANT_ROLLED_BACK
            ],
        )

    def test_every_refusal_this_command_can_name_has_an_operator_sentence(self):
        # DERIVED, not hand-listed, for the reason `test_gm_chat_no_bytes_
        # line.py` gives about the stage faults: a reason added to
        # `skill_all_command` and forgotten in the dispatcher's map prints
        # `no blocker recorded` to the person holding the console.  This
        # round added one (`REFUSED_GRANT_ROLLED_BACK`) and would have
        # forgotten it.
        reasons = [
            value
            for name, value in sorted(vars(skill_all_command).items())
            if name.startswith("REFUSED_") and isinstance(value, str)
        ]
        self.assertGreaterEqual(len(reasons), 8, reasons)
        for reason in reasons:
            with self.subTest(reason=reason):
                self.assertIn(
                    chat_command_action.OUTCOME_SKILL_REFUSED_PREFIX + reason,
                    chat_command_action.NO_BYTES_BLOCKERS,
                )


class TheFixesOfRoundNkb608Tests(_Case):
    """One case per pf-adversary finding round `nkb608` measured live.

    Every one of these ran GREEN against the defect it names before the fix,
    which is why they exist: the round that shipped the defects had 49 cases
    over these two modules and none of them called the functions the way an
    operator can.
    """

    def test_every_exit_of_grant_all_builds_a_whole_record(self):
        # D-A (CRITICAL): two exits passed FIVE positional arguments into a
        # six-field record, so both raised `TypeError` on the listener thread
        # -- the escape this lane forbids -- and neither line had ever run,
        # because no case called `grant_all` with anything but a valid id and
        # a store that has the door.
        class _Bare:
            pass

        for store, character_id, expected in (
            (FakeStore(), 0, skill_all_command.REFUSED_NO_CHARACTER),
            (FakeStore(), None, skill_all_command.REFUSED_NO_CHARACTER),
            (FakeStore(), True, skill_all_command.REFUSED_NO_CHARACTER),
            (_Bare(), 1, skill_all_command.REFUSED_NO_STORE),
        ):
            with self.subTest(refusal=expected):
                result = skill_all_command.grant_all(store, character_id)
                self.assertEqual(result.refusal, expected)
                self.assertTrue(result.counts_are_complete)
                self.assertEqual(
                    (result.granted, result.already, result.failed), (0, 0, 0)
                )

    def test_a_character_with_no_row_is_named_as_such_not_as_a_dead_store(self):
        # D-K: `KeyError` from the real store's reader means "no such
        # character", and folding it into "the store cannot be read" sent the
        # operator to look at the wrong thing.
        class _NoRowStore(FakeStore):
            def list_character_skills(self, character_id):
                raise KeyError(character_id)

        result = skill_all_command.grant_all(_NoRowStore(), 1)
        self.assertEqual(result.refusal, skill_all_command.REFUSED_ROW_MISSING)

        class _DeadReaderStore(FakeStore):
            def list_character_skills(self, character_id):
                raise RuntimeError("the table is locked")

        self.assertEqual(
            skill_all_command.grant_all(_DeadReaderStore(), 1).refusal,
            skill_all_command.REFUSED_CANNOT_READ_CURRENT_SKILLS,
        )

    def test_a_restore_that_did_not_take_is_not_reported_as_put_back(self):
        # D-D: `write_typed_attributes` returning without raising is not the
        # same fact as the column holding the value again, and the suffix is
        # read by a human deciding whether the row is safe to walk away from.
        class _SilentNoOpStore(FakeStore):
            """Takes the write, raises nothing, and changes no column."""

            def write_typed_attributes(self, character_id, values):
                self.writes.append((character_id, dict(values)))
                return dict(self.stored)

        # The row is carrying the class the GM asked for; the restore is
        # asked to put 2 back and the store quietly declines.
        store = _SilentNoOpStore()
        store.stored["class_id"] = 16
        self.assertEqual(
            job_command._repair(store, 1, 2), job_command.REPAIR_FAILED_SUFFIX
        )
        self.assertEqual(store.stored["class_id"], 16)
        # The control: a store that really does take it answers `put back`,
        # so the case above is measuring the read-back and not the store.
        working = FakeStore()
        working.stored["class_id"] = 16
        self.assertEqual(
            job_command._repair(working, 1, 2), job_command.REPAIRED_SUFFIX
        )

    def test_a_row_that_had_no_class_says_it_is_still_carrying_the_new_one(self):
        # D-C: the common case -- a row whose `class_id` is NULL -- had
        # nothing to put back, and the empty suffix reported the most
        # dangerous of the three states as though nothing had happened.
        self.assertEqual(
            job_command._repair(FakeStore(), 1, None),
            job_command.NO_PREVIOUS_SUFFIX,
        )
        self.assertNotEqual(job_command.NO_PREVIOUS_SUFFIX, "")
        # And the operator gets a sentence for it rather than the bare
        # reason's silence about durability.
        reason = (
            job_command.REFUSED_LOGIN_WOULD_NOT_SEND
            + job_command.NO_PREVIOUS_SUFFIX
        )
        sentence = chat_command_action._JOB_BLOCKERS[reason]
        self.assertIn("no class to put back", sentence)
        self.assertIn("still carries the new one", sentence)
        # And it fits the console cap, which the first wording of this
        # sentence did not (254 > 240, caught by
        # `tests/test_gm_chat_no_bytes_line.py`).
        self.assertLessEqual(
            len(sentence), chat_command_action.MAX_CONSOLE_HINT_LENGTH
        )

    def test_a_refusal_that_left_rows_behind_offers_an_undo_that_says_kept(self):
        # D-B: `_make_action` reads a MISSING undo as "the effect was dropped
        # with the audit row", so a refusal holding rows on disk printed a
        # count and then denied it one line later.
        kept = job_command.REFUSED_READBACK_MISMATCH + job_command.REPAIR_FAILED_SUFFIX
        gone = job_command.REFUSED_READBACK_MISMATCH + job_command.REPAIRED_SUFFIX
        nothing = job_command.REFUSED_NOT_A_CLASS_ID

        class _R:
            def __init__(self, refusal):
                self.refusal = refusal

        self.assertIsNotNone(chat_command_action._job_refusal_undo(_R(kept)))
        self.assertIs(
            chat_command_action._job_refusal_undo(_R(kept))(), False
        )
        self.assertIsNotNone(
            chat_command_action._job_refusal_undo(
                _R(
                    job_command.REFUSED_LOGIN_WOULD_NOT_SEND
                    + job_command.NO_PREVIOUS_SUFFIX
                )
            )
        )
        # A refusal that put the old value back, and one that never wrote,
        # keep NO undo: for those two "dropped with the audit row" is true.
        self.assertIsNone(chat_command_action._job_refusal_undo(_R(gone)))
        self.assertIsNone(chat_command_action._job_refusal_undo(_R(nothing)))

    def test_the_test_files_the_docstrings_cite_are_files_that_exist(self):
        # D-G: three docstrings named `tests/test_gm_job_command.py` and
        # `tests/test_gm_skill_all_command.py`, neither of which has ever
        # existed -- and one of them is the named guarantee that the usage
        # literal cannot drift from `class_catalog.CLASS_IDS`.
        import re

        sources = [
            ROOT / "src/pirateforce_foundation/gm/job_command.py",
            ROOT / "src/pirateforce_foundation/gm/skill_all_command.py",
            ROOT / "src/pirateforce_foundation/gm/commands.py",
            ROOT / "src/pirateforce_foundation/gm/sandbox_readback.py",
        ]
        for source in sources:
            text = source.read_text(encoding="utf-8")
            for cited in set(re.findall(r"tests/test_[a-z0-9_]+\.py", text)):
                with self.subTest(source=source.name, cited=cited):
                    self.assertTrue(
                        (ROOT / cited).is_file(),
                        f"{source.name} cites {cited}, which does not exist",
                    )


if __name__ == "__main__":
    unittest.main()
