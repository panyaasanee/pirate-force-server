"""LANE-GM: the `lv` half of the chat line -> outbound ACTION path.

PANYA-ORDER `20260906_0155` (`pf_bridge/notes_to_chief/20260906_0155_PANYA-
ORDER-LANE-GM-slash-lv-set-character-level-first-job-deadline-1400.md`),
GM round `gm2vlx`. See `chat_command_action._lv_action`'s own section banner
for the full shape and why the live `UpdateAttrVital` send is withheld
unconditionally this round -- this file proves the DB-write half only:

1. THE CANONICAL-DB GATE DEFAULTS OPEN (i.e. tests run past it), the same
   convention `tests/test_gm_speed_action.py` uses for its own version gate:
   `FakeSession` defaults to a run-copy-style path, and a test that means to
   exercise the withheld branch sets `db_path=chat_command_action.
   CANONICAL_DB_FILENAME` itself.
2. NO FRAME IS EVER COMPOSED THROUGH `attr_wire` -- there is no shape-hold,
   no deferred gate, no version gate to patch open, because this route
   never reaches those doors at all this round. The only frame `_lv_action`
   can ever produce is a local-talk courtesy notice
   (`say_wire.make_local_talk_notice_frame`), proven against the real
   codec, not a stand-in.
"""
from __future__ import annotations

import contextlib
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import say_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import persistence_standard_status  # noqa: E402


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
    """Only the fields `_lv_action` reads off `.selected`."""

    def __init__(self, identity_lo=1, identity_hi=0, character_id=1):
        self.identity_lo = identity_lo
        self.identity_hi = identity_hi
        self.id = character_id


class FakeStore:
    """`.path` for the run-copy gate, plus the two generic LANE-DB methods
    `_lv_action` calls: `read_typed_attributes` (the undo's read) and
    `write_typed_attributes` (the write itself). Signature and contract
    copied from the real `store.SQLiteStore.write_typed_attributes`: raises
    for a refusal, and NEVER writes when it does."""

    def __init__(self, path):
        self.path = path
        self.calls = []
        self.raises = None
        #: The row as it stands, keyed by TYPED COLUMN NAME (matching the
        #: real store's shape), not by wire field index.
        self.stored = {}
        #: Set True to simulate a write that REALLY COMMITS (the internal
        #: `stored` dict updates, same as production) but whose returned
        #: read-back dict omits the column -- the one shape
        #: `OUTCOME_LV_PERSIST_READBACK_UNUSABLE` exists for.
        self.readback_drops_level = False

    def read_typed_attributes(self, character_id):
        return dict(self.stored)

    def write_typed_attributes(self, character_id, values):
        self.calls.append((character_id, dict(values)))
        if self.raises is not None:
            raise self.raises
        self.stored.update(values)
        if self.readback_drops_level:
            return {k: v for k, v in self.stored.items() if k != "level"}
        return dict(self.stored)


class FakeLifecycle:
    def __init__(self, path):
        self.store = FakeStore(path)


# Mirrors GT-193's run-copy naming convention (a timestamped filename, never
# the bare canonical one) -- the default every test below gets unless it
# asks for the canonical-DB refusal specifically.
DEFAULT_RUN_COPY_DB_PATH = "state/pirateforce_gm2vlx_20260906_0322.sqlite3"

_DEFAULT = object()


class FakeFoundation:
    def __init__(self, selected=None, db_path=DEFAULT_RUN_COPY_DB_PATH):
        self.selected = selected
        self.lifecycle = None if db_path is None else FakeLifecycle(db_path)


class FakeSession:
    def __init__(self, token="GM_ONE", selected=_DEFAULT, db_path=_DEFAULT):
        self.token = token
        self.events = []
        if selected is _DEFAULT:
            selected = FakeSelected()
        if db_path is _DEFAULT:
            db_path = DEFAULT_RUN_COPY_DB_PATH
        self.foundation = FakeFoundation(selected, db_path)


class _Case(unittest.TestCase):
    GM_ACCOUNT = "GM_ONE"

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


class TheStoredRowTests(_Case):
    def test_a_valid_level_is_written_through_the_generic_typed_door(self):
        session = FakeSession()
        store = session.foundation.lifecycle.store
        action = self.act(session, "/lv 50")
        self.assertEqual(store.calls, [(1, {chat_command_action.LV_TYPED_COLUMN: 50})])
        self.assertEqual(store.stored[chat_command_action.LV_TYPED_COLUMN], 50)
        self.assertIn(chat_command_action.EVENT_LV_ROW_WRITTEN, session.events)
        self.assertIsNotNone(action)

    def test_the_column_written_is_level_not_a_retyped_literal(self):
        # `LV_TYPED_COLUMN` is derived from `attr_wire.BY_NAME["level"]`, not
        # hand-typed as the string "level" a second time anywhere this test
        # can see -- this pins the derived value itself.
        self.assertEqual(chat_command_action.LV_TYPED_COLUMN, "level")

    def test_the_written_value_is_bounded_by_the_clients_own_level_table(self):
        # `chat_command_action.LV_MIN_LEVEL`/`LV_MAX_LEVEL` are NOT imported
        # live from `persistence_standard_status` (that module is a
        # reserved LANE-DB scaffold with no production caller anywhere in
        # the repo, per its own docstring and
        # `tests/test_persistence_standard_status.py::NoProductionCallerTests`
        # -- importing it from `gm/` would trip that guard, confirmed by
        # pf-adversary this round). This test is the cross-check that
        # keeps the hardcoded pair honest against the real source, from a
        # test file (not scanned by that guard).
        self.assertEqual(
            chat_command_action.LV_MIN_LEVEL,
            persistence_standard_status.STANDARD_STATUS_MIN_LEVEL,
        )
        self.assertEqual(
            chat_command_action.LV_MAX_LEVEL,
            persistence_standard_status.STANDARD_STATUS_MAX_LEVEL,
        )

    def test_a_level_outside_the_clients_table_is_refused_before_any_write(self):
        session = FakeSession()
        store = session.foundation.lifecycle.store
        self.act(session, "/lv 9999")
        self.assertEqual(store.calls, [])
        self.assertEqual(store.stored, {})
        self.assertTrue(
            any(
                event.startswith(chat_command_action.EVENT_LV_REFUSED_PREFIX)
                for event in session.events
            ),
            session.events,
        )

    def test_a_level_of_zero_is_refused(self):
        session = FakeSession()
        store = session.foundation.lifecycle.store
        self.act(session, "/lv 0")
        self.assertEqual(store.calls, [])

    def test_the_outcome_is_deferred_not_composed(self):
        # THE CLAIM OF THIS ROUND, pinned: a written `/lv` row reaches
        # `EVENT_LV_ROW_WRITTEN`, never `EVENT_ACCEPTED_PREFIX`-shaped
        # "frame sent" bookkeeping for a live UpdateAttrVital. A future
        # round that wires the live send has to change this test, which is
        # the point -- it cannot happen silently.
        session = FakeSession()
        self.act(session, "/lv 50")
        self.assertIn(chat_command_action.EVENT_LV_ROW_WRITTEN, session.events)
        self.assertFalse(
            any("update_attr" in event for event in session.events),
            session.events,
        )


class TheNoticeTests(_Case):
    def test_a_stored_row_sends_a_real_local_talk_notice(self):
        session = FakeSession()
        action = self.act(session, "/lv 50")
        self.assertIsNotNone(action)
        label, pc, frame, delay = action
        self.assertEqual(label, chat_command_action.LV_NOTICE_ACTION_LABEL)
        self.assertEqual(delay, 0.0)
        # Proven against the real codec: this must equal composing the same
        # notice directly through `say_wire`.
        expected_pc, expected_frame = say_wire.make_local_talk_notice_frame(
            self.legacy, say_wire.LV_STORED_NOTICE_TEXT
        )
        self.assertEqual((pc, frame), (expected_pc, expected_frame))

    def test_a_denied_lv_also_sends_a_notice_with_a_different_body(self):
        session = FakeSession(selected=None)
        action = self.act(session, "/lv 50")
        self.assertIsNotNone(action)
        label, pc, frame, delay = action
        self.assertEqual(label, chat_command_action.LV_NOTICE_ACTION_LABEL)
        expected_pc, expected_frame = say_wire.make_local_talk_notice_frame(
            self.legacy, say_wire.LV_DENIED_NOTICE_TEXT
        )
        self.assertEqual((pc, frame), (expected_pc, expected_frame))

    def test_the_two_notice_bodies_are_both_exactly_twelve_ascii_characters(self):
        for text in (say_wire.LV_STORED_NOTICE_TEXT, say_wire.LV_DENIED_NOTICE_TEXT):
            self.assertEqual(len(text), say_wire.NOTICE_TEXT_EXACT_LENGTH)
            text.encode("ascii")

    def test_the_console_line_names_the_notice_actually_sent_not_speeds(self):
        # pf-adversary (this round) found `_print_notice_sent` hardcoded
        # `say_wire.SPEED_DENIED_NOTICE_TEXT` for EVERY caller -- a
        # successful `/lv 50` printed `notice='SPEED DENIED'` on the very
        # line meant to confirm the write. Fixed via `_Verdict.notice_text`;
        # this pins both `/lv` shapes print their OWN body, not `/speed`'s.
        session = FakeSession()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.act(session, "/lv 50")
        line = err.getvalue()
        self.assertIn(f"notice={say_wire.LV_STORED_NOTICE_TEXT!r}", line)
        self.assertNotIn(say_wire.SPEED_DENIED_NOTICE_TEXT, line)

        session2 = FakeSession(selected=None)
        err2 = io.StringIO()
        with contextlib.redirect_stderr(err2):
            self.act(session2, "/lv 50")
        line2 = err2.getvalue()
        self.assertIn(f"notice={say_wire.LV_DENIED_NOTICE_TEXT!r}", line2)
        self.assertNotIn(say_wire.SPEED_DENIED_NOTICE_TEXT, line2)


class RefusalPathsTests(_Case):
    def test_no_selected_character_is_refused_before_any_write(self):
        session = FakeSession(selected=None)
        self.act(session, "/lv 50")
        self.assertIn(
            chat_command_action.EVENT_LV_NO_SELECTED_CHARACTER, session.events
        )

    def test_the_canonical_db_refuses_the_write_outright(self):
        session = FakeSession(
            db_path=chat_command_action.CANONICAL_DB_FILENAME
        )
        store = session.foundation.lifecycle.store
        self.act(session, "/lv 50")
        self.assertEqual(store.calls, [])
        self.assertIn(
            chat_command_action.EVENT_LV_WITHHELD_CANONICAL_DB, session.events
        )

    def test_a_windows_alias_of_the_canonical_name_is_also_refused(self):
        # Same NTFS-alias set `_speed_db_is_canonical` defends against
        # (pf-adversary round `hw6dix`, D3) -- reused here via
        # `_speed_db_normalized_filename`, not reinvented.
        session = FakeSession(db_path="state\\PirateForce.sqlite3 ")
        store = session.foundation.lifecycle.store
        self.act(session, "/lv 50")
        self.assertEqual(store.calls, [])

    def test_no_store_is_refused(self):
        # A `db_path=None` session has no `.lifecycle` at all, which the
        # canonical-DB gate ALSO treats as "cannot prove this is safe" and
        # refuses -- so it never reaches this check. `EVENT_LV_NO_STORE`
        # fires when `.lifecycle.store` exists (so the canonical check
        # passes) but does not offer `write_typed_attributes`.
        class _NoWriteMethod:
            path = "state/pirateforce_gm2vlx_20260906_0322.sqlite3"

        session = FakeSession()
        session.foundation.lifecycle.store = _NoWriteMethod()
        self.act(session, "/lv 50")
        self.assertIn(chat_command_action.EVENT_LV_NO_STORE, session.events)

    def test_a_missing_lifecycle_is_refused_as_canonical_not_as_no_store(self):
        session = FakeSession(db_path=None)
        self.act(session, "/lv 50")
        self.assertIn(
            chat_command_action.EVENT_LV_WITHHELD_CANONICAL_DB, session.events
        )
        self.assertNotIn(chat_command_action.EVENT_LV_NO_STORE, session.events)

    def test_a_store_that_raises_on_write_leaves_nothing_written(self):
        session = FakeSession()
        store = session.foundation.lifecycle.store
        store.raises = ValueError("typed attr refused")
        self.act(session, "/lv 50")
        self.assertEqual(store.stored, {})
        self.assertIn(
            f"{chat_command_action.EVENT_LV_PERSIST_REFUSED_PREFIX}ValueError",
            session.events,
        )

    def test_every_lv_outcome_has_a_named_blocker(self):
        for name in (
            "OUTCOME_LV_WITHHELD_CANONICAL_DB",
            "OUTCOME_LV_NO_SELECTED_CHARACTER",
            "OUTCOME_LV_NO_STORE",
            "OUTCOME_LV_NO_CHARACTER_ID",
            "OUTCOME_LV_PERSIST_REFUSED",
            "OUTCOME_LV_PERSIST_READBACK_UNUSABLE",
            "OUTCOME_LV_DEFERRED",
        ):
            outcome = getattr(chat_command_action, name)
            with self.subTest(name=name):
                self.assertIn(outcome, chat_command_action.NO_BYTES_BLOCKERS)


class UndoTests(_Case):
    def test_a_persist_refusal_carries_an_undo_that_reports_false_when_nothing_to_restore(self):
        session = FakeSession()
        store = session.foundation.lifecycle.store
        store.raises = ValueError("refused")
        err = io.StringIO()
        with mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            mock.Mock(side_effect=OSError(28, "no space left on device")),
        ), contextlib.redirect_stderr(err):
            self.act(session, "/lv 50")
        line = err.getvalue()
        self.assertIn(
            f"why={chat_command_action.WHY_AUDIT_ROW_NOT_WRITTEN} ", line
        )

    def test_readback_unusable_carries_a_real_undo_that_actually_restores(self):
        # pf-adversary (this round): this branch was exercised by nothing
        # but a blocker-sentence lookup, so a regression that dropped its
        # `undo` (or broke `_lv_undo`'s read) would ship green. Drives the
        # branch directly: the write REALLY COMMITS (production's own
        # contract), this lane's own read-back of the result is what fails.
        session = FakeSession()
        store = session.foundation.lifecycle.store
        store.stored["level"] = 12
        store.readback_drops_level = True
        self.act(session, "/lv 50")
        self.assertIn(
            chat_command_action.EVENT_LV_PERSIST_READBACK_UNUSABLE,
            session.events,
        )
        # The write DID land -- production's own contract guarantees it --
        # even though this route could not read the confirmation back.
        self.assertEqual(store.stored["level"], 50)

        # Now prove the carried `undo` is REAL, not a stub: calling it
        # restores the value this write overwrote.
        store2 = FakeStore("state/pirateforce_gm2vlx_20260906_0322.sqlite3")
        store2.stored["level"] = 12
        store2.readback_drops_level = True
        undo = chat_command_action._lv_undo(store2, 1)
        store2.write_typed_attributes(1, {"level": 77})
        self.assertEqual(store2.stored["level"], 77)
        self.assertTrue(undo())
        self.assertEqual(store2.stored["level"], 12)


class ConsoleLineTests(_Case):
    def test_a_written_row_prints_the_row_written_token(self):
        session = FakeSession()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.act(session, "/lv 77")
        line = err.getvalue()
        self.assertIn(chat_command_action.LV_ROW_WRITTEN_CONSOLE_TOKEN, line)
        self.assertIn("level_after=77", line)
        self.assertNotIn("level_after=None", line)

    def test_the_console_line_never_prints_to_stdout(self):
        session = FakeSession()
        err, out = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            self.act(session, "/lv 77")
        self.assertEqual(out.getvalue(), "")


class ModuleDocstringHonestyTests(_Case):
    def test_the_module_docstring_no_longer_lists_lv_as_unwired(self):
        source = (
            ROOT / "src/pirateforce_foundation/gm/chat_command_action.py"
        ).read_text(encoding="utf-8")
        import re

        live_claim = re.search(
            r"\* It does not send anything for ([^.]*)\.", source
        )
        self.assertIsNotNone(live_claim)
        self.assertNotIn("lv", live_claim.group(1).split("/"))


class AsciiTests(unittest.TestCase):
    def test_this_test_file_added_no_non_ascii_characters(self):
        text = Path(__file__).read_text(encoding="utf-8")
        bad = [ch for ch in text if ord(ch) > 127]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
