"""LANE-GM: the `speed` half of the chat line -> outbound ACTION path.

CORE-REQUEST-GM-049 (`pf_bridge/notes_to_chief/20260901_1728_LANE-GM-CORE-
REQUEST-GM-049-speed-sparse-x7-runtime-send-point.md`), wired behind a
SCOPED, temporary exception to `attr_wire.UPDATE_ATTR_VITAL_VERSION_
CONFIRMED` (`COO-DECISION 2026-09-01T18:47+07:00`, `pf_bridge/notes_to_
chief/20260901_1847_COO-DECISION-gm049-vital-version-gate-scoped-
exception-c.md`).  This file proves the `speed` half, mirroring
`tests/test_gm_say_action.py`'s shape (single-socket send, no DB write, no
move-authority interaction) with the differences that shape actually has:

1. THE GATE DEFAULTS OPEN, UNLIKE `say`'s.  `UPDATE_ATTR_VITAL_VERSION_
   CONFIRMED` is `0` today (the scoped exception), not `None` -- so a test
   that means to exercise the withheld branch must force the gate SHUT
   itself (`close_the_version_gate`), the same discipline
   `test_gm_chat_command_action.py`'s `VersionGateTests` already uses for
   `teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED` since RE-129 shipped.
2. IDENTITY, NOT POSITION.  `_speed_action` reads `identity_lo`/
   `identity_hi` off `session.foundation.selected` -- a field `say` never
   touches and `warp` reads `.position` from instead.  A connection with no
   selected character (or one missing the fields) is a named refusal.
3. THE LABEL MUST NOT SAY TELEPORT, same reason as `say`'s: `runtime.py`'s
   `_move_authority_note_server_moves` reopens the move-authority grace
   window on that exact substring, and `/speed` moves nobody.
"""
from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import attr_wire  # noqa: E402
from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import speed_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


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
    """Only the two fields `_speed_action` reads off `.selected`.

    `id`/`position` are deliberately absent -- `speed` reads neither, and a
    future edit that starts reaching for one fails here instead of quietly
    working on a real session.
    """

    def __init__(self, identity_lo=1, identity_hi=0):
        self.identity_lo = identity_lo
        self.identity_hi = identity_hi


class FakeStore:
    """Only the one field `_speed_db_filename` reads off `.lifecycle.store`."""

    def __init__(self, path):
        self.path = path


class FakeLifecycle:
    def __init__(self, path):
        self.store = FakeStore(path)


# The default run-copy-style path every test below gets unless it asks for
# something else -- deliberately NOT the canonical filename, so the whole
# suite exercises `_speed_action` past the run-copy-DB gate by default the
# same way it already defaults past the identity read and version gate.
# Mirrors `pf_bridge/GAME_TEST_QUEUE.md`'s GT-193 run-copy naming: a
# timestamped filename, never the bare canonical one.
DEFAULT_RUN_COPY_DB_PATH = "state/pirateforce_gt193_20260901_1200.sqlite3"


class FakeFoundation:
    def __init__(self, selected=None, db_path=DEFAULT_RUN_COPY_DB_PATH):
        self.selected = selected
        # `None` means "no `.lifecycle` at all" -- the same shape
        # `_speed_db_filename` must treat as unreadable, not as canonical
        # for the wrong reason and not as safe.
        self.lifecycle = None if db_path is None else FakeLifecycle(db_path)


_DEFAULT = object()


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

    def close_the_version_gate(self):
        """Force the scoped exception shut, to walk the withheld branch.

        `UPDATE_ATTR_VITAL_VERSION_CONFIRMED` is `0` by default (the scoped
        exception this round flipped it to) -- a test proving the withheld
        path exists must patch the gate back to `None` itself, the same
        discipline `test_gm_chat_command_action.py::VersionGateTests` uses
        for `teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED` since RE-129
        shipped.
        """
        return mock.patch.object(
            attr_wire, "UPDATE_ATTR_VITAL_VERSION_CONFIRMED", None
        )


class SpeedVersionGateTests(_Case):
    def test_the_shipped_constant_is_zero_by_the_scoped_exception(self):
        # See attr_wire.py's own comment on the constant for the full
        # reasoning (COO-DECISION 20260901_1847, a convergence across
        # RE-105/RE-129, not a byte lifted from either).
        self.assertEqual(attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED, 0)

    def test_a_valid_gm_speed_composes_with_the_gate_open_by_default(self):
        # Unlike `say`'s gate (still None today), this one does not need a
        # test to open it -- proving that IS what this test pins.
        session = FakeSession()
        action = self.act(session, "/speed 5.0")
        self.assertIsNotNone(action)

    def test_a_valid_gm_speed_withholds_when_the_gate_is_forced_shut(self):
        session = FakeSession()
        with self.close_the_version_gate():
            action = self.act(session, "/speed 5.0")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_NO_VERSION, session.events
        )

    def test_the_line_is_still_authorized_and_audited_while_withheld(self):
        session = FakeSession()
        with self.close_the_version_gate():
            self.act(session, "/speed 5.0")
        records = self.log_records()
        # Issued row + the outcome row that names the shut gate
        # (CORE-REQUEST-GM-032).
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["command"], "speed")
        self.assertFalse(records[0]["executed"])
        self.assertEqual(
            records[1]["outcome"],
            chat_command_action.OUTCOME_SPEED_WITHHELD_NO_VERSION,
        )
        self.assertIn(
            f"{chat_command_action.EVENT_ACCEPTED_PREFIX}speed", session.events
        )


class SpeedActionTests(_Case):
    def test_a_speed_command_becomes_a_real_update_attr_vital_action(self):
        session = FakeSession()
        action = self.act(session, "/speed 5.0")
        self.assertIsNotNone(action)
        label, pc, frame, delay = action
        self.assertEqual(label, chat_command_action.SPEED_ACTION_LABEL)
        self.assertEqual(delay, 0.0)
        self.assertIsInstance(pc, (bytes, bytearray))
        self.assertIsInstance(frame, (bytes, bytearray))

    def test_the_bytes_are_the_imported_composers_bytes_not_new_ones(self):
        # This module must never become a second place that knows how to
        # build an UpdateAttrVital frame.
        session = FakeSession(selected=FakeSelected(identity_lo=7, identity_hi=3))
        _label, pc, frame, _delay = self.act(session, "/speed 12.5")
        expected_pc, expected_frame = speed_wire.compose_sparse_speed_update(
            self.legacy, 7, 3, 12.5
        )
        self.assertEqual(bytes(pc), bytes(expected_pc))
        self.assertEqual(bytes(frame), bytes(expected_frame))

    def test_the_identity_reaches_the_frame_from_the_selected_character(self):
        session = FakeSession(
            selected=FakeSelected(identity_lo=0xAABBCCDD, identity_hi=0x11223344)
        )
        _label, _pc, frame, _delay = self.act(session, "/speed 1.0")
        self.assertIn(
            struct.pack("<II", 0xAABBCCDD, 0x11223344), bytes(frame)
        )

    def test_a_composer_rejection_surfaces_as_a_named_speed_refusal(self):
        session = FakeSession()
        with mock.patch.object(
            speed_wire,
            "compose_sparse_speed_update",
            side_effect=speed_wire.SpeedWireError("nope"),
        ):
            action = self.act(session, "/speed 5.0")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_SPEED_REFUSED_PREFIX}SpeedWireError",
            session.events,
        )

    def test_the_refusal_outcome_names_the_command_and_the_exception_type(self):
        session = FakeSession()
        with mock.patch.object(
            speed_wire,
            "compose_sparse_speed_update",
            side_effect=speed_wire.SpeedWireError("nope"),
        ):
            self.act(session, "/speed 5.0")
        records = self.log_records()
        self.assertEqual(
            records[-1]["outcome"], "refused_speed_SpeedWireError"
        )


class SpeedIdentityTests(_Case):
    def test_no_selected_character_is_a_named_refusal_not_a_crash(self):
        session = FakeSession(selected=None)
        action = self.act(session, "/speed 5.0")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_NO_SELECTED_CHARACTER,
            session.events,
        )

    def test_a_selected_character_missing_identity_is_the_same_named_refusal(self):
        class BareSelected:
            pass

        session = FakeSession(selected=BareSelected())
        action = self.act(session, "/speed 5.0")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_NO_SELECTED_CHARACTER,
            session.events,
        )

    def test_the_outcome_row_names_the_missing_character_case(self):
        session = FakeSession(selected=None)
        self.act(session, "/speed 5.0")
        records = self.log_records()
        self.assertEqual(
            records[-1]["outcome"],
            chat_command_action.OUTCOME_SPEED_NO_SELECTED_CHARACTER,
        )


class SpeedRunCopyDbGateTests(_Case):
    """CORE-REQUEST-GM-049's run-copy-DB requirement, enforced this round.

    pf-adversary found that the prior docstring's "no existing code-level
    mechanism" claim was false and the gap it excused was live-reachable:
    `session.foundation.lifecycle.store.path` was already the live DB path
    string this process booted against.  This class proves the filename
    heuristic `_speed_db_is_canonical` reads off it -- see that function's
    own docstring, and `_speed_action`'s, for the honest statement of what a
    FILENAME HEURISTIC does and does not guarantee.
    """

    def test_the_canonical_filename_exact_match_withholds(self):
        session = FakeSession(db_path="state/pirateforce.sqlite3")
        action = self.act(session, "/speed 5.0")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
            session.events,
        )

    def test_the_bare_canonical_filename_with_no_directory_also_withholds(self):
        session = FakeSession(db_path="pirateforce.sqlite3")
        action = self.act(session, "/speed 5.0")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
            session.events,
        )

    def test_an_explicit_run_copy_filename_proceeds_past_this_gate(self):
        # A GT-193-style timestamped filename is exactly what a run-copy
        # boot passes to --db -- this must NOT be refused by this gate.
        session = FakeSession(
            db_path="state/pirateforce_gt193_20260901.sqlite3"
        )
        action = self.act(session, "/speed 5.0")
        self.assertIsNotNone(action)
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
            session.events,
        )

    def test_a_windows_backslash_path_to_the_canonical_file_is_still_caught(self):
        # `os.path.basename` alone would leave this whole string uncut on a
        # Linux process -- this is what proves the explicit `/`-and-`\`
        # split actually does its job rather than trusting the platform's
        # own separator.
        session = FakeSession(db_path="state\\pirateforce.sqlite3")
        action = self.act(session, "/speed 5.0")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
            session.events,
        )

    def test_an_unreadable_path_withholds_rather_than_proceeding(self):
        # `db_path=None` means `FakeFoundation` carries no `.lifecycle` at
        # all -- a test double / unusual session shape this function cannot
        # read.  "Cannot prove this is safe" must refuse, never proceed as
        # if it were proven safe.
        session = FakeSession(db_path=None)
        action = self.act(session, "/speed 5.0")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
            session.events,
        )

    def test_this_gate_runs_before_the_identity_read(self):
        # Point 4 of the fix: a wrong-DB refusal must not depend on a
        # character having been selected first.  No character is selected
        # here, and the refusal must still be the DB one, not the identity
        # one.
        session = FakeSession(selected=None, db_path="state/pirateforce.sqlite3")
        action = self.act(session, "/speed 5.0")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
            session.events,
        )
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_NO_SELECTED_CHARACTER,
            session.events,
        )

    def test_the_outcome_row_names_the_canonical_db_case(self):
        session = FakeSession(db_path="state/pirateforce.sqlite3")
        self.act(session, "/speed 5.0")
        records = self.log_records()
        self.assertEqual(
            records[-1]["outcome"],
            chat_command_action.OUTCOME_SPEED_WITHHELD_CANONICAL_DB,
        )

    def test_the_path_string_itself_never_reaches_an_event_name(self):
        # Defense in depth, same rule this whole module states for every
        # other refusal: the event/outcome names are fixed literals, never
        # built from anything read off the session, so a run-copy filename
        # cannot leak through this gate's refusal either.
        session = FakeSession(
            db_path="state/pirateforce_SECRET_TOKEN_1234.sqlite3"
        )
        self.act(session, "/speed 5.0")
        self.assertFalse(
            any("SECRET_TOKEN" in event for event in session.events),
            session.events,
        )


class SpeedLabelTests(_Case):
    """The label is not decoration; runtime.py reads it."""

    def test_the_speed_label_does_not_contain_teleport(self):
        self.assertNotIn("TELEPORT", chat_command_action.SPEED_ACTION_LABEL)

    def test_the_label_is_ascii(self):
        chat_command_action.SPEED_ACTION_LABEL.encode("ascii")

    def test_the_speed_label_is_distinct_from_the_others(self):
        self.assertNotEqual(
            chat_command_action.SPEED_ACTION_LABEL,
            chat_command_action.SAY_ACTION_LABEL,
        )
        self.assertNotEqual(
            chat_command_action.SPEED_ACTION_LABEL,
            chat_command_action.WARP_ACTION_LABEL,
        )
        self.assertNotEqual(
            chat_command_action.SPEED_ACTION_LABEL,
            chat_command_action.GMPROBE_ACTION_LABEL,
        )


class SpeedPermissionTests(_Case):
    def test_a_non_gm_typing_the_same_line_gets_nothing(self):
        session = FakeSession(token=self.PLAYER_ACCOUNT)
        action = self.act(session, "/speed 5.0")
        self.assertIsNone(action)
        self.assertEqual(self.log_records(), [])
        self.assertFalse(
            any(
                event.startswith(chat_command_action.EVENT_ACCEPTED_PREFIX)
                for event in session.events
            ),
            session.events,
        )


class SpeedCoverageHonestyTests(_Case):
    """The "not wired yet" list has to shrink when a wire is built."""

    def test_speed_is_no_longer_reported_as_having_no_wire_path(self):
        session = FakeSession()
        self.act(session, "/speed 5.0")
        self.assertNotIn(
            f"{chat_command_action.EVENT_NO_WIRE_PATH_PREFIX}speed",
            session.events,
        )


if __name__ == "__main__":
    unittest.main()
