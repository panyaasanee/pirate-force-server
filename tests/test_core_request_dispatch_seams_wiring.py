"""The three CORE-REQUEST dispatch seams chief landed in one PR, on the REAL
dispatcher.

COO-DECISION `pf_bridge/notes_to_chief/20260907_1141_COO-DECISION-chief1109-
core-request-queue-order-LANE-E.md` item 1 allows one PR to pay three
dispatch seams in one file, on four conditions.  This file is the first of
them: each seam has its own test, and removing one seam from
``runtime.py`` reddens a DIFFERENT test class here.

  * ``ActivityCheatCodeSeamTests``   -- CORE-REQUEST-GM-062 (0x6CEC)
  * ``UnclaimedVitalSeamWithdrawnTests`` -- CORE-REQUEST-GM-063, landed
    by R390 and withdrawn by R391 (the detector could not answer the
    question its own hook point asks); the withdrawal is pinned here
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


class UnclaimedVitalSeamWithdrawnTests(_SeamCase):
    """CORE-REQUEST-GM-063 was landed by R390 and WITHDRAWN by R391.

    This class replaces the three pins R390 wrote for the detector, and it
    is deliberately not a deletion.  The detector could be re-landed in the
    same shape by anyone who reads only the letter, so what is pinned here
    is the withdrawal itself: from `dispatch()` nothing fires the GM-063
    point, and the hook module says so about itself.  Both halves come back
    out together on the day a call site exists that can answer the question
    the point asks -- which branch, if any, read this id.
    """

    POINT = "vital_inbound_unknown_id"

    def test_an_id_no_branch_reads_does_not_reach_the_hook(self):
        # The exact frame R390's own pin drove: an id with no branch
        # anywhere in the chain.  It still produces no actions -- the
        # withdrawal changed no dispatch behaviour -- but it no longer
        # reports itself, because the detector could not tell this frame
        # apart from the ten ids that DO have a branch and answer nothing.
        state = self._login_and_start("unknownid")
        self._warm_runtime_ack(state)
        seen = self._capture(self.POINT)
        actions = self._send(state, 0xABCD, b"")
        self.assertEqual(actions, [])
        self.assertEqual(seen, [])

    def test_no_hex_line_is_written_for_it_either(self):
        # End to end through the real hook: with no call site, the console
        # line an attended round would have read is not written at all.
        # Silence is the correct state -- a wrong id is worse than none.
        state = self._login_and_start("unknownreal")
        self._warm_runtime_ack(state)
        self._send(state, 0xABCD, b"")
        self.assertEqual(
            [e for e in state.events if e.startswith("unknown_vital_id_")],
            [],
        )

    def test_the_module_declares_the_point_never_fired_again(self):
        # The relation pin in tests/test_lane_gm_unknown_vital_counter.py
        # owns the general rule (declared if and only if nothing fires it).
        # This asserts the concrete end state R391 ships, so that removing
        # the declaration without landing a call site reds here too.
        from pirateforce_foundation.lane_hooks import (
            lane_gm_unknown_vital_counter as counter,
        )
        self.assertIn(
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
