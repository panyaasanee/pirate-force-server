"""LANE-GM: `/lv <n>` -- the argument, the row write, and the login link.

PANYA-ORDER 2026-09-06 01:55 (`pf_bridge/notes_to_chief/20260906_0155_PANYA-
ORDER-LANE-GM-slash-lv-set-character-level-first-job-deadline-1400.md`).

THE TWO LAYERS THIS FILE KEEPS APART, because the house rule is that one may
never be used to argue the other:

  * THE ROW.  `LevelCommandTests` and `PersistenceIntegrationTests` ask
    whether `characters.level` really changed -- the second class against a
    REAL `SQLiteStore` on a temp file, read back through a SECOND store
    opened on the same file, which is the closest a headless test gets to
    "the GM logs in again tomorrow".
  * THE LOGIN.  `NextLoginReadsTheRowTests` asks the ONE question the whole
    design rests on: does the login path read that column back?  It asks it
    of `persistence_login_vitals.resolve_for_character`, the function
    `session.py` calls, not of a copy of its logic.

NEITHER IS A SCREEN.  Nothing in this file has a client in it; the on-screen
half is the attended ticket's, and this file's job is to make sure that
ticket is testing something real when it gets there.
"""
from __future__ import annotations

import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_login_vitals  # noqa: E402
from pirateforce_foundation import persistence_standard_status  # noqa: E402
from pirateforce_foundation import persistence_typed_attrs  # noqa: E402
from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import commands as gm_commands  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import level_command  # noqa: E402
from pirateforce_foundation.gm import say_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"

# Deliberately NOT the canonical filename: the run-copy gate stands above
# every write path here, so a default that tripped it would make the whole
# file pass for the wrong reason.  Mirrors GT-193's run-copy naming.
RUN_COPY_DB_PATH = "state/pirateforce_lv_20260906_0412.sqlite3"


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
        # `/lv` never reads these; they are here because a real `.selected`
        # carries them, and a double that is thinner than the real object is
        # how a test proves a read that production would fail.
        self.identity_lo = 1
        self.identity_hi = 0


class FakeStore:
    """`.path` for the run-copy gate plus LANE-DB's typed-attribute door.

    The signature is copied from the real `store.SQLiteStore.write_typed_
    attributes(character_id, values)` -> the row's typed columns AFTER the
    write.  `PersistenceIntegrationTests` runs the same command against a
    REAL store, so this double is never the only thing the wiring is proven
    against.
    """

    def __init__(self, path=RUN_COPY_DB_PATH):
        self.path = path
        self.writes = []
        self.stored = {}
        self.raises = None
        #: Set to a value to make the read-back DISAGREE with what was asked
        #: for -- the one refusal that leaves the row's state unknown.
        self.readback_override = None
        #: False = this row's login vitals do not resolve (a bad HP pair), so
        #: `store.read_character_vitals_or_none` answers `None` even though
        #: the level column holds a value.  That is the D1 state: the row
        #: moves and the login still sends the composer's constant.
        self.login_resolves = True

    def read_typed_attributes(self, character_id):
        """The COLUMN door.  A NULL column is OMITTED, never rendered as 0 --
        the real method's own contract, and what makes `_previous_level`'s
        `KeyError` branch the never-written case."""
        return dict(self.stored)

    def read_character_vitals_or_none(self, character_id):
        """The LOGIN's door: `None` for any incomplete resolution, which is
        not the same question as "does the column hold a value"."""
        level = self.stored.get("level")
        if level is None or not self.login_resolves:
            return None
        return mock.Mock(level=level)

    def write_typed_attributes(self, character_id, values):
        self.writes.append((character_id, dict(values)))
        if self.raises is not None:
            raise self.raises
        self.stored.update(values)
        if self.readback_override is not None:
            return {"level": self.readback_override}
        return dict(self.stored)


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


class ArgumentTests(_Case):
    """`parse_level` -- the second check, deliberately (see its docstring)."""

    def test_a_plain_level_parses(self):
        self.assertEqual(level_command.parse_level(("30",)), 30)

    def test_whitespace_around_the_number_is_tolerated(self):
        self.assertEqual(level_command.parse_level((" 30 ",)), 30)

    def test_zero_is_refused_because_the_vitals_gate_refuses_that_row(self):
        # Not a style rule: `store.read_character_vitals` returns a
        # `level_zero_is_not_an_adjudicated_level` gap for such a row, so a
        # `/lv 0` would leave a row the LOGIN falls back away from -- the
        # command would look like it did nothing and the tester would be
        # reading the screen correctly.
        with self.assertRaises(level_command.LevelArgumentError) as caught:
            level_command.parse_level(("0",))
        self.assertEqual(caught.exception.reason, level_command.REFUSED_OUT_OF_RANGE)

    def test_above_the_column_ceiling_is_refused(self):
        ceiling = level_command.max_level()
        self.assertEqual(level_command.parse_level((str(ceiling),)), ceiling)
        with self.assertRaises(level_command.LevelArgumentError) as caught:
            level_command.parse_level((str(ceiling + 1),))
        self.assertEqual(caught.exception.reason, level_command.REFUSED_OUT_OF_RANGE)

    def test_the_ceiling_is_the_clients_table_not_the_columns_width(self):
        # pf-adversary (round `l86bt4`, D5): the first draft used the u16
        # storage maximum, 65535.  The client's own committed table stops at
        # 255 and its XP bar reads the `level + 1` row, so the last row is
        # left alone as well.
        self.assertEqual(
            level_command.max_level(),
            persistence_standard_status.STANDARD_STATUS_MAX_LEVEL - 1,
        )
        self.assertLess(
            level_command.max_level(),
            int(persistence_typed_attrs.TYPED_COLUMNS["level"].maximum),
        )

    def test_the_level_above_the_tables_last_row_is_refused(self):
        top = persistence_standard_status.STANDARD_STATUS_MAX_LEVEL
        with self.assertRaises(level_command.LevelArgumentError) as caught:
            level_command.parse_level((str(top),))
        self.assertEqual(caught.exception.reason, level_command.REFUSED_OUT_OF_RANGE)
        # And every level the table DOES carry below it is writable.
        self.assertEqual(level_command.parse_level((str(top - 1),)), top - 1)

    def test_a_negative_level_is_refused(self):
        with self.assertRaises(level_command.LevelArgumentError) as caught:
            level_command.parse_level(("-5",))
        self.assertEqual(caught.exception.reason, level_command.REFUSED_OUT_OF_RANGE)

    def test_a_non_number_is_refused_as_a_non_number(self):
        with self.assertRaises(level_command.LevelArgumentError) as caught:
            level_command.parse_level(("thirty",))
        self.assertEqual(caught.exception.reason, level_command.REFUSED_NOT_AN_INTEGER)

    def test_a_tuple_subclass_that_lies_is_refused_on_shape(self):
        # The defeat this module's docstring names: `isinstance` would pass
        # this, `type(...) is not tuple` does not.
        class Liar(tuple):
            def __len__(self):
                return 1

            def __getitem__(self, index):
                return "30"

        with self.assertRaises(level_command.LevelArgumentError) as caught:
            level_command.parse_level(Liar())
        self.assertEqual(caught.exception.reason, level_command.REFUSED_ARGS_SHAPE)

    def test_an_integer_keyed_dict_is_refused_on_shape(self):
        with self.assertRaises(level_command.LevelArgumentError) as caught:
            level_command.parse_level({0: "30"})
        self.assertEqual(caught.exception.reason, level_command.REFUSED_ARGS_SHAPE)

    def test_the_usage_sentence_names_both_ends_of_the_range(self):
        sentence = level_command.usage()
        self.assertIn(str(level_command.MIN_LEVEL), sentence)
        self.assertIn(str(level_command.max_level()), sentence)


class WriteTests(_Case):
    """`write_level` -- never raises, always names its refusal."""

    def test_a_write_reports_the_stores_read_back_not_the_typed_number(self):
        store = FakeStore()
        store.readback_override = 31
        result = level_command.write_level(store, 1, 30)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal, level_command.REFUSED_READBACK_MISMATCH)

    def test_a_clean_write_is_ok_and_carries_the_previous_level(self):
        store = FakeStore()
        store.stored["level"] = 7
        result = level_command.write_level(store, 1, 30)
        self.assertTrue(result.ok)
        self.assertEqual(result.written, 30)
        self.assertEqual(result.previous, 7)

    def test_a_missing_row_is_named_rather_than_raised(self):
        store = FakeStore()
        store.raises = KeyError(1)
        result = level_command.write_level(store, 1, 30)
        self.assertEqual(result.refusal, level_command.REFUSED_ROW_MISSING)

    def test_any_other_store_failure_is_named_rather_than_raised(self):
        # The property that matters on the listener thread: `runtime.py`
        # catches four exception types and `v141` wraps the connection loop
        # with no `except` at all, so an escaping error parks the client on
        # "connecting".
        store = FakeStore()
        store.raises = RuntimeError("disk on fire")
        result = level_command.write_level(store, 1, 30)
        self.assertEqual(result.refusal, level_command.REFUSED_WRITE_FAILED)
        self.assertIn("RuntimeError", result.detail)

    def test_no_character_id_is_a_named_refusal_and_writes_nothing(self):
        store = FakeStore()
        for bad in (None, 0, -1, True, "1"):
            with self.subTest(character_id=bad):
                result = level_command.write_level(store, bad, 30)
                self.assertEqual(result.refusal, level_command.REFUSED_NO_CHARACTER)
        self.assertEqual(store.writes, [])

    def test_a_store_without_the_door_is_a_named_refusal(self):
        result = level_command.write_level(object(), 1, 30)
        self.assertEqual(result.refusal, level_command.REFUSED_NO_STORE)

    def test_the_undo_puts_the_previous_level_back(self):
        store = FakeStore()
        store.stored["level"] = 7
        result = level_command.write_level(store, 1, 30)
        undo = level_command.undo(store, 1, result.previous)
        self.assertTrue(undo())
        self.assertEqual(store.stored["level"], 7)

    def test_a_row_the_login_would_not_send_is_refused_and_put_back(self):
        # pf-adversary D1, MEASURED on a real DB: the login's vitals gate is
        # ALL THREE OR NONE, so a row with a bad HP pair resolves
        # `row_refused_by_vitals_gate` with EMPTY wire kwargs and the login
        # sends `PLAYER_LOGIN_LEVEL` (1).  The row said 50 and the screen
        # said 1, with the only trace on the server console one login later.
        store = FakeStore()
        store.stored["level"] = 7
        store.login_resolves = False
        result = level_command.write_level(store, 1, 50)
        self.assertFalse(result.ok)
        self.assertTrue(
            result.refusal.startswith(level_command.REFUSED_LOGIN_WOULD_NOT_SEND)
        )
        self.assertEqual(store.stored["level"], 7)
        self.assertTrue(result.refusal.endswith(level_command.REPAIRED_SUFFIX))

    def test_a_readback_mismatch_puts_the_row_back_without_waiting_for_an_undo(self):
        # pf-adversary D6: the dispatch runs a verdict's undo ONLY when the
        # audit row could not be written, so an undo attached to this branch
        # never ran on the ordinary path.  The repair happens here instead.
        store = FakeStore()
        store.stored["level"] = 7
        store.readback_override = 31
        result = level_command.write_level(store, 1, 30)
        self.assertTrue(
            result.refusal.startswith(level_command.REFUSED_READBACK_MISMATCH)
        )
        self.assertEqual(store.stored["level"], 7)

    def test_the_previous_level_is_read_from_the_column_not_the_vitals_gate(self):
        # pf-adversary D7: reading it through the login's door returned
        # `None` for a row with a bad HP pair -- exactly the rows most likely
        # to need putting back -- and the repair then had nothing to restore.
        store = FakeStore()
        store.stored["level"] = 7
        store.login_resolves = False
        self.assertEqual(level_command._previous_level(store, 1), 7)

    def test_login_would_send_answers_no_when_it_cannot_ask(self):
        # It gates a CLAIM about a screen; "cannot tell" may not be reported
        # as "yes".
        self.assertFalse(level_command.login_would_send(object(), 1, 30))

    def test_the_console_line_is_filtered_to_ascii(self):
        # pf-adversary D11: the docstring claimed this and the code did not
        # do it.  A store exception's message is a reachable carrier.
        store = FakeStore()
        store.raises = RuntimeError("ไม่ได้")
        result = level_command.write_level(store, 1, 30)
        line = level_command.console_line(result, 1)
        self.assertTrue(line.isascii(), line)

    def test_there_is_no_undo_when_there_is_nothing_to_undo_to(self):
        # `None` is not "the undo ran and failed"; the dispatch's audit tells
        # those two apart and this is the first of them.
        self.assertIsNone(level_command.undo(FakeStore(), 1, None))


class DispatchTests(_Case):
    """The chat line -> `_lv_action` -> row + notice route."""

    def test_a_gms_lv_writes_the_row_and_sends_the_relog_sentence(self):
        session = FakeSession()
        action = self.act(session, "/lv 30")
        self.assertIsNotNone(action)
        self.assertEqual(action[0], chat_command_action.LV_SET_NOTICE_ACTION_LABEL)
        self.assertEqual(self.store_of(session).writes, [(1, {"level": 30})])
        self.assertIn(gm_commands.OUTCOME_LV_ROW_WRITTEN, self.outcomes())

    def test_the_sentence_says_relog_because_no_level_frame_is_sent(self):
        # The wording is the whole courtesy: a GM staring at an unchanged
        # level bar after a bare "LV SET" would call the command broken.
        self.assertIn("RELOG", say_wire.LV_SET_NOTICE_TEXT)

    def test_a_non_gm_cannot_reach_the_write(self):
        session = FakeSession(token=self.PLAYER_ACCOUNT)
        self.assertIsNone(self.act(session, "/lv 30"))
        self.assertEqual(self.store_of(session).writes, [])

    def test_the_canonical_db_is_refused_and_nothing_is_written(self):
        # `AGENTS.md` section 7: `ห้ามแตะ canonical DB ตัวจริง`.  This is the only
        # thing standing between a row write and that rule.
        session = FakeSession(
            store=FakeStore(f"state/{chat_command_action.CANONICAL_DB_FILENAME}")
        )
        action = self.act(session, "/lv 30")
        self.assertEqual(self.store_of(session).writes, [])
        self.assertEqual(
            action[0], chat_command_action.LV_REFUSED_NOTICE_ACTION_LABEL
        )
        self.assertIn(
            chat_command_action.OUTCOME_LV_WITHHELD_CANONICAL_DB, self.outcomes()
        )

    def test_an_unreadable_store_path_counts_as_canonical_and_refuses(self):
        # Fails CLOSED: "cannot prove this is safe" is treated exactly like
        # "proven canonical".
        session = FakeSession(store=None)
        self.act(session, "/lv 30")
        self.assertIn(
            chat_command_action.OUTCOME_LV_WITHHELD_CANONICAL_DB, self.outcomes()
        )

    def test_an_out_of_range_level_writes_nothing_and_says_so(self):
        session = FakeSession()
        action = self.act(session, "/lv 0")
        self.assertEqual(self.store_of(session).writes, [])
        self.assertEqual(
            action[0], chat_command_action.LV_REFUSED_NOTICE_ACTION_LABEL
        )
        self.assertIn(
            f"{chat_command_action.OUTCOME_LV_REFUSED_PREFIX}"
            f"{level_command.REFUSED_OUT_OF_RANGE}",
            self.outcomes(),
        )

    def test_no_selected_character_is_refused_after_the_gate(self):
        session = FakeSession(selected=None)
        self.act(session, "/lv 30")
        self.assertIn(
            f"{chat_command_action.OUTCOME_LV_REFUSED_PREFIX}"
            f"{level_command.REFUSED_NO_CHARACTER}",
            self.outcomes(),
        )

    def test_every_lv_refusal_word_has_a_console_blocker_sentence(self):
        # Derived from `level_command`'s own constants rather than hand-typed,
        # for the reason `test_gm_chat_no_bytes_line.py` records: a hand-typed
        # list said five when upstream had ten and the missing five inherited
        # `no blocker recorded` in silence.
        for name in dir(level_command):
            if not name.startswith("REFUSED_"):
                continue
            reason = getattr(level_command, name)
            if reason == level_command.REFUSED_CANONICAL_DB:
                # Carried by the withheld word, which has its own entry.
                continue
            with self.subTest(reason=reason):
                self.assertIn(
                    f"{chat_command_action.OUTCOME_LV_REFUSED_PREFIX}{reason}",
                    chat_command_action.NO_BYTES_BLOCKERS,
                )
        self.assertIn(
            chat_command_action.OUTCOME_LV_WITHHELD_CANONICAL_DB,
            chat_command_action.NO_BYTES_BLOCKERS,
        )

    def test_the_success_word_is_in_the_audit_vocabulary(self):
        # The writer refuses any word outside `AUDIT_OUTCOMES`, so a success
        # word that was never added would have made every `/lv` fail to
        # record -- and `_make_action` undoes an unrecorded effect.
        self.assertIn(gm_commands.OUTCOME_LV_ROW_WRITTEN, gm_commands.AUDIT_OUTCOMES)

    def test_neither_label_contains_teleport(self):
        # `runtime.py`'s `_move_authority_note_server_moves` reopens the
        # move-authority grace window on that exact substring, and `/lv`
        # moves nobody.
        for label in (
            chat_command_action.LV_SET_NOTICE_ACTION_LABEL,
            chat_command_action.LV_REFUSED_NOTICE_ACTION_LABEL,
        ):
            with self.subTest(label=label):
                self.assertNotIn("TELEPORT", label)

    def test_lv_no_longer_falls_into_the_no_wire_path_branch(self):
        session = FakeSession()
        self.act(session, "/lv 30")
        self.assertNotIn(
            chat_command_action.OUTCOME_NO_WIRE_PATH, self.outcomes()
        )

    def test_the_console_line_never_repeats_what_the_gm_typed(self):
        session = FakeSession()
        import contextlib
        import io

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.act(session, "/lv 30")
        printed = stderr.getvalue()
        self.assertIn(chat_command_action.LV_CONSOLE_TOKEN, printed)
        self.assertNotIn("/lv 30", printed)


class PersistenceIntegrationTests(_Case):
    """The same command against a REAL `SQLiteStore` on a real temp file."""

    def setUp(self):
        super().setUp()
        self.addCleanup(self._assert_no_sqlite_handle_survives)
        self.db_path = self.tmp / "pirateforce_lv_test.sqlite3"
        self.store = SQLiteStore(self.db_path, MIGRATIONS)
        self.store.migrate()
        account_id = self.store.ensure_account(self.GM_ACCOUNT)
        self.character = self.store.create_character(
            account_id, "LevelGM", "levelgm", "fingerprint-level-gm",
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

    def reopened_level(self):
        """The row's level read through a SECOND store on the same file."""
        second = SQLiteStore(self.db_path, MIGRATIONS)
        return second.read_character_vitals_or_none(self.character.id).level

    def test_the_row_holds_the_new_level_after_the_command(self):
        action = self.act(self.session, "/lv 42")
        self.assertEqual(
            action[0], chat_command_action.LV_SET_NOTICE_ACTION_LABEL
        )
        self.assertEqual(self.reopened_level(), 42)

    def test_a_second_lv_overwrites_the_first(self):
        self.act(self.session, "/lv 42")
        gm_dispatch.reset_rate_limit_state_for_tests()
        self.act(self.session, "/lv 7")
        self.assertEqual(self.reopened_level(), 7)

    def test_a_refused_level_leaves_the_row_exactly_as_it_was(self):
        before = self.reopened_level()
        self.act(self.session, "/lv 99999")
        self.assertEqual(self.reopened_level(), before)


class NextLoginReadsTheRowTests(PersistenceIntegrationTests):
    """The one question the whole design rests on, asked of the login's own
    function rather than of a copy of its logic.

    `session.py` resolves a login's three vitals through
    `persistence_login_vitals.resolve_for_character`, and `legacy_bridge.
    start_game` puts the level it returns on the wire.  If that function does
    not carry the row this command wrote, `/lv` is a row nobody reads.

    STILL NOT A SCREEN: no client is involved here, and this file never
    claims one saw anything.  The attended ticket owns that half.
    """

    def resolved(self):
        return persistence_login_vitals.resolve_for_character(
            self.store,
            self.character.id,
            fallback_level=1,
            fallback_hp_current=100,
            fallback_hp_max=100,
        )

    def test_the_login_resolution_carries_the_level_lv_wrote(self):
        self.act(self.session, "/lv 42")
        resolved = self.resolved()
        self.assertEqual(resolved.level, 42)

    def test_the_login_resolution_is_complete_so_the_row_is_what_ships(self):
        # "ALL THREE OR NONE" (`PANYA-DECISION 20260901_1059`): `start_game`
        # sends the row's numbers only when level AND both HP ends resolve.
        # A `/lv` that left the resolution incomplete would write a row the
        # login then ignores -- the exact silent failure this test exists for.
        self.act(self.session, "/lv 42")
        resolved = self.resolved()
        for field in persistence_login_vitals.CHARACTER_FIELDS:
            with self.subTest(field=field):
                self.assertIsNotNone(getattr(resolved, field))

    def test_a_row_whose_hp_pair_is_broken_is_refused_on_a_real_database(self):
        # The D1 state, built on the real schema rather than on a double:
        # `hp_max IS NULL` makes the login's vitals gate refuse the WHOLE row,
        # so the level would never reach the wire.  `/lv` must not claim it.
        import sqlite3

        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute(
                "UPDATE characters SET hp_max=NULL WHERE id=?",
                (self.character.id,),
            )
            connection.commit()
        finally:
            connection.close()
        before = self.resolved().level
        action = self.act(self.session, "/lv 42")
        self.assertEqual(
            action[0], chat_command_action.LV_REFUSED_NOTICE_ACTION_LABEL
        )
        self.assertEqual(self.resolved().level, before)
        self.assertTrue(
            any(
                o.startswith(
                    f"{chat_command_action.OUTCOME_LV_REFUSED_PREFIX}"
                    f"{level_command.REFUSED_LOGIN_WOULD_NOT_SEND}"
                )
                for o in self.outcomes()
            ),
            self.outcomes(),
        )

    def test_the_character_object_a_login_composes_carries_the_new_level(self):
        # The seam's own half: `session.py` hands the resolution to
        # `apply_to_character`, and the value RIDES the character into
        # `legacy_bridge.start_game`.
        self.act(self.session, "/lv 42")
        character = persistence_login_vitals.apply_to_character(
            self.character, self.resolved()
        )
        self.assertEqual(character.level, 42)


if __name__ == "__main__":
    unittest.main()
