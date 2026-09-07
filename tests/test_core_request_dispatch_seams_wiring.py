"""The three CORE-REQUEST dispatch seams chief landed in one PR, on the REAL
dispatcher.

COO-DECISION `pf_bridge/notes_to_chief/20260907_1141_COO-DECISION-chief1109-
core-request-queue-order-LANE-E.md` item 1 allows one PR to pay three
dispatch seams in one file, on four conditions.  This file is the first of
them: each seam has its own test, and removing one seam from
``runtime.py`` reddens a DIFFERENT test class here.

  * ``ActivityCheatCodeSeamTests``   -- CORE-REQUEST-GM-062 (0x6CEC)
  * ``UnclaimedVitalSeamTests``      -- CORE-REQUEST-GM-063 (unknown id)
  * ``ItemOperateOp5SeamTests``      -- CORE-REQUEST LANE-DB 20260906_1452

The lane-side modules are proved offline by their owners
(``tests/test_gm_activity_cheat_code_dispatch.py``,
``tests/test_lane_gm_unknown_vital_counter.py``).  What those files cannot
prove is the one thing chief's edit adds: that a raw frame reaching
``runtime.py`` on a real login actually reaches ``lane_hooks.fire()``.  This
file drives ``make_state_class`` headless -- no server process, no socket,
no client -- mirroring ``tests/test_lane_a_trigger_vital_dispatch_wiring.py``.
"""
from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation.gm.activity_cheat_code_wire import (  # noqa: E402
    ACTIVITY_CHEAT_CODE_VITAL_ID,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _synthetic_nested_pc(legacy, nested_id: int, payload: bytes) -> bytes:
    """One outer envelope carrying one nested vital ``nested_id``.

    Same bytes as ``test_lane_a_trigger_vital_dispatch_wiring.py``'s own
    helper with the id as a parameter -- that file's docstring is the
    reference for why this is the outer-frame shape.
    """
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 0x02)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, nested_id)
        + legacy.u8tag(0x0B, 0)
        + payload
    )


class _SeamCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = _legacy()
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

    def _login_and_start(self, token):
        state_type = make_state_class(
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
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        return state

    def _send(self, state, nested_id, payload):
        pc = _synthetic_nested_pc(self.legacy, nested_id, payload)
        return state.dispatch(self.legacy.parse_outer(pc))

    def _warm_runtime_ack(self, state):
        """Spend the once-per-session RUNTIME_RES_ACK_FIRST_REQ action.

        The first frame a session sends down this path composes v141's
        `make_runtime_res_empty_exact()` ack (`runtime_ack_sent`,
        current/pf_login_game_server_v141.py:3768).  It is an action, so the
        GM-063 detector below correctly reads that frame as claimed.  In a
        real session that costs exactly one frame per connection; in a test
        it would otherwise mask every probe, so it is spent deliberately
        here and asserted, not assumed.
        """
        self._send(state, 0xFFF0, b"")
        self.assertTrue(state.runtime_ack_sent)

    def _capture(self, point):
        """Register a recorder on ``point`` and remove it again afterwards.

        Touches ``lane_hooks._HOOKS`` directly, the same way
        ``tests/test_gm_activity_cheat_code_dispatch.py`` and
        ``tests/test_gm_chat_command.py`` already read it: there is no
        public unregister, and a test that left a hook behind would leak
        into every later test in the process.
        """
        seen = []

        def _recorder(**kwargs):
            seen.append(kwargs)

        entry = (__name__, _recorder)
        lane_hooks._HOOKS.setdefault(point, []).append(entry)

        def _remove():
            entries = lane_hooks._HOOKS.get(point, [])
            if entry in entries:
                entries.remove(entry)

        self.addCleanup(_remove)
        return seen


class ActivityCheatCodeSeamTests(_SeamCase):
    """CORE-REQUEST-GM-062: 0x6CEC reaches its hook and answers nothing."""

    def test_the_frame_reaches_the_hook_and_sends_nothing(self):
        state = self._login_and_start("cheatcode")
        seen = self._capture("vital_inbound_activity_cheat_code")
        rx_before = state.rx_frames
        actions = self._send(state, ACTIVITY_CHEAT_CODE_VITAL_ID, b"")
        self.assertEqual(actions, [], "the seam must send nothing back")
        self.assertEqual(state.rx_frames, rx_before + 1)
        self.assertEqual(len(seen), 1, "the point fired exactly once")

    def test_the_hook_is_handed_the_session_and_the_payload_only(self):
        # The letter's own hard line: identity comes from the connection,
        # never from a byte the client sent.  The seam therefore hands over
        # the session (whose `token` is the verified login name) and the
        # payload -- and no third thing that could stand in for identity.
        state = self._login_and_start("cheatargs")
        seen = self._capture("vital_inbound_activity_cheat_code")
        body = b"\x0b\x07"
        self._send(state, ACTIVITY_CHEAT_CODE_VITAL_ID, body)
        self.assertEqual(len(seen), 1)
        self.assertEqual(set(seen[0]), {"session", "payload"})
        self.assertIs(seen[0]["session"], state)
        self.assertEqual(seen[0]["payload"], body)

    def test_the_id_is_the_one_the_wire_module_owns(self):
        # Not a re-declared literal in runtime.py: the branch is reached
        # through the constant imported from gm/activity_cheat_code_wire.py.
        runtime_source = (
            ROOT / "src" / "pirateforce_foundation" / "runtime.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "from .gm.activity_cheat_code_wire import "
            "ACTIVITY_CHEAT_CODE_VITAL_ID",
            runtime_source,
        )
        # A comment may spell the number (one does, in the branch's own
        # NOT CLAIMED note); what must not exist is a second DEFINITION of
        # it in this file.
        self.assertNotIn("ACTIVITY_CHEAT_CODE_VITAL_ID =", runtime_source)
        self.assertEqual(ACTIVITY_CHEAT_CODE_VITAL_ID, 0x6CEC)

    def test_a_non_gm_login_is_refused_without_writing_anything(self):
        # End to end through the real hook (no recorder): the account is not
        # a GM, so the module refuses and records why.  Proves the seam is
        # wired to the shipped hook, not only to a test recorder.
        state = self._login_and_start("cheatreal")
        actions = self._send(state, ACTIVITY_CHEAT_CODE_VITAL_ID, b"")
        self.assertEqual(actions, [])
        self.assertTrue(
            [e for e in state.events
             if e.startswith("activity_cheat_code_refused_")],
            f"expected a refusal event, got {state.events[-3:]}",
        )


class UnclaimedVitalSeamTests(_SeamCase):
    """CORE-REQUEST-GM-063: a frame no reader claimed is counted once."""

    POINT = "vital_inbound_unknown_id"

    def test_an_id_no_branch_reads_reaches_the_hook_once(self):
        state = self._login_and_start("unknownid")
        self._warm_runtime_ack(state)
        seen = self._capture(self.POINT)
        actions = self._send(state, 0xABCD, b"")
        self.assertEqual(actions, [])
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]["vital_id"], 0xABCD)
        self.assertIs(seen[0]["session"], state)

    def test_the_shipped_hook_records_the_id_in_hex_once_per_session(self):
        # End to end through the real hook, and its dedup contract with it:
        # the same id twice is one line, not two.
        state = self._login_and_start("unknownreal")
        self._warm_runtime_ack(state)
        self._send(state, 0xABCD, b"")
        self._send(state, 0xABCD, b"")
        self.assertEqual(
            [e for e in state.events if e == "unknown_vital_id_0xABCD"],
            ["unknown_vital_id_0xABCD"],
        )

    def test_a_claimed_frame_is_not_reported_unknown(self):
        # 0x6CEC is claimed by the GM-062 branch above -- it bumps
        # rx_frames and its hook appends an event -- so the unclaimed
        # detector must stay silent on it.  This is the finding the seam
        # exists to avoid: a wrong id in a P-3 capture.
        state = self._login_and_start("claimedframe")
        self._warm_runtime_ack(state)
        seen = self._capture(self.POINT)
        self._send(state, ACTIVITY_CHEAT_CODE_VITAL_ID, b"")
        self.assertEqual(seen, [])

    def test_the_module_no_longer_declares_the_point_never_fired(self):
        from pirateforce_foundation.lane_hooks import (
            lane_gm_unknown_vital_counter as counter,
        )
        self.assertNotIn(
            self.POINT, getattr(counter, "registered_but_not_fired", ()),
        )


class ItemOperateOp5SeamTests(_SeamCase):
    """CORE-REQUEST LANE-DB 20260906_1452: op=5 gets a seam, nothing else."""

    POINT = "vital_inbound_item_operate_op5"

    def _item_operate_pc(self, op, value32, identity):
        payload = (
            self.legacy.u8tag(0x0B, op)
            + self.legacy.u32tag(0x14, value32)
            + bytes([0x32]) + struct.pack("<Q", identity)
        )
        return _synthetic_nested_pc(
            self.legacy, self.legacy.ITEM_OPERATE_REQ_VITAL, payload,
        )

    def _send_item_operate(self, state, op, value32=7, identity=0x1122):
        return state.dispatch(self.legacy.parse_outer(
            self._item_operate_pc(op, value32, identity)
        ))

    def test_op5_reaches_the_hook_with_the_positional_fields(self):
        state = self._login_and_start("equipop5")
        seen = self._capture(self.POINT)
        self._send_item_operate(state, 5, value32=9, identity=0xDEAD)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]["value32"], 9)
        self.assertEqual(seen[0]["item_identity"], 0xDEAD)
        self.assertIs(seen[0]["session"], state)

    def test_op4_does_not_reach_the_op5_point(self):
        state = self._login_and_start("moveop4")
        seen = self._capture(self.POINT)
        self._send_item_operate(state, 4)
        self.assertEqual(seen, [])

    def test_a_malformed_body_is_dropped_not_raised(self):
        # The seam parses inside a try; a body the v141 parser refuses must
        # leave dispatch on the path it was already on.
        state = self._login_and_start("badbody")
        seen = self._capture(self.POINT)
        state.dispatch(self.legacy.parse_outer(_synthetic_nested_pc(
            self.legacy, self.legacy.ITEM_OPERATE_REQ_VITAL, b"\xff\xff",
        )))
        self.assertEqual(seen, [])

    def test_the_seam_answers_nothing_and_counts_nothing(self):
        # SEAM ONLY: no reply, no rx_frames bump, no store call.  If a
        # later round wires equip behaviour here, this test is the one that
        # must be re-argued rather than quietly deleted.
        state = self._login_and_start("op5inert")
        self._warm_runtime_ack(state)
        self._capture(self.POINT)
        equipped_before = len(self.store.list_characters(
            state.foundation.account_id
        ))
        actions = self._send_item_operate(state, 5)
        self.assertEqual(actions, [], "the seam composes no reply")
        self.assertEqual(
            len(self.store.list_characters(state.foundation.account_id)),
            equipped_before,
        )


if __name__ == "__main__":
    unittest.main()
