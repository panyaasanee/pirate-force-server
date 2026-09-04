"""COO-DECISION 20260904_0746 item 3 -- the NavigationEx_EnterInstanceVital
(0xC723) inbound call site, on the REAL dispatcher.

Mirrors tests/test_lane_a_trigger_vital_dispatch_wiring.py, which does the
same job for the sibling `vital_inbound_trigger_vital` point sitting next to
this one in runtime.py.  The difference is that this point has NO hook module
yet: LANE-A's is due a round later, so there is nothing here to assert a
`LANE_A_*` console line against.  That is the interesting half.  COO-DECISION
0746 item 3 allows the call site to land early only on the condition that the
point fires safely with no subscriber, so this file proves exactly that pair:

  1. a raw 0xC723 frame reaching a real logged-in session dispatches into the
     branch, counts, and returns no actions -- with the hook table EMPTY for
     the point (this is the "landed early" state, and it must not raise, warn,
     or answer the client);
  2. the same frame delivers `payload` verbatim to a hook once one registers
     -- so LANE-A's module, when it arrives, is wired by the act of
     subscribing and needs no second runtime.py edit.

It also pins the id itself.  0xC723 is a literal in runtime.py because the
frozen v141 snapshot has no constant for this vital, so the usual protection
(a rename breaks the reader) is absent: a typo in four hex digits would be a
branch that silently never matches, which is the failure this project has
already paid for once.  `test_the_vital_id_is_the_registry_hash_of_the_wire_
name` recomputes the v141 protocol_name_id hash over the wire name and
asserts it equals the constant.

NOT PROVEN HERE: that a real client has ever sent this frame to this server.
It has not.  We have never provisioned the NavigationEx_AddSurveyDataVtial
record that makes the captain-report window pop, so nothing on the wire
reaches this branch yet (RE-227 nonclaim 6; COO-DECISION 20260904_0747 (b)
forbids sending that record until GT-228 measures real island XYZ).
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import (  # noqa: E402
    NAVIGATIONEX_ENTER_INSTANCE_VITAL_ID,
    NAVIGATIONEX_ENTER_INSTANCE_VITAL_NAME,
    make_state_class,
)
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

POINT = "vital_inbound_navigationex_enter_instance_vital"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _synthetic_enter_instance_pc(legacy, payload: bytes) -> bytes:
    """A minimal outer envelope carrying one NavigationEx_EnterInstanceVital
    nested vital, `payload` used verbatim as its body.

    Identical in shape to `_synthetic_trigger_vital_pc` in the sibling
    dispatch-wiring test (see that file for why this is the outer-frame
    shape), with the nested id swapped.
    """
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 0x02)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, NAVIGATIONEX_ENTER_INSTANCE_VITAL_ID)
        + legacy.u8tag(0x0B, 0)
        + payload
    )


def _confirm_body(legacy, opaque: int) -> bytes:
    """The body RE-227 pinned statically for the confirm frame:
    `12 <opaque-u16 LE> 0B 06`.

    The u16 is copied unchanged by the client from the survey record's
    `+0x12`; RE-227 nonclaim 3 forbids calling it an island id, a scene id or
    a Trigger-TIP id, so this test treats it as opaque -- it asserts the bytes
    arrive, never what they mean.  The trailing `0B 06` is the allocator's
    fixed byte 6 at record `+0x16`.
    """
    return legacy.u16tag(0x12, opaque) + legacy.u8tag(0x0B, 6)


class NavigationExEnterInstanceDispatchWiringTests(unittest.TestCase):
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

    def _send(self, state, payload):
        pc = _synthetic_enter_instance_pc(self.legacy, payload)
        return state.dispatch(self.legacy.parse_outer(pc))

    def test_the_vital_id_is_the_registry_hash_of_the_wire_name(self):
        # pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv header:
        # protocol_name_id = sum((i+1)*ord(c) for i,c in enumerate(name))
        # & 0xFFFF.  Recomputed here rather than trusted, and the frozen
        # snapshot's own TriggerVital = 0x1FB2 is the control that the
        # formula is the right one -- so this test fails if the four hex
        # digits are wrong AND if the hash rule was misread.
        def protocol_name_id(name):
            return sum((i + 1) * ord(c) for i, c in enumerate(name)) & 0xFFFF

        self.assertEqual(
            protocol_name_id("TriggerVital"), self.legacy.TRIGGER_VITAL,
            "control: the hash rule must reproduce a v141 id we already have",
        )
        self.assertEqual(
            protocol_name_id(NAVIGATIONEX_ENTER_INSTANCE_VITAL_NAME),
            NAVIGATIONEX_ENTER_INSTANCE_VITAL_ID,
        )

    def test_the_point_has_no_subscriber_yet(self):
        # The precondition the two tests below are interesting under, asserted
        # rather than assumed: LANE-A's hook module does not exist yet.  When
        # it lands this test is the one that has to change, deliberately, in
        # the same PR -- it must never be "fixed" by deleting it.
        self.assertEqual(
            lane_hooks.registered_points().get(POINT, 0), 0,
            "a subscriber appeared for %s: update this file's docstring and "
            "the sibling assertions in the same PR" % POINT,
        )

    def test_an_unsubscribed_frame_dispatches_counts_and_answers_nothing(self):
        state = self._login_and_start("navent1")
        rx_before = state.rx_frames
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            actions = self._send(state, _confirm_body(self.legacy, 0x1234))
        self.assertEqual(actions, [], "this call site must send nothing back")
        self.assertEqual(
            state.rx_frames, rx_before + 1,
            "the frame must be counted, not dropped as unmatched",
        )
        # An unsubscribed point is a no-op, so nothing fires and nothing errs.
        console = stderr.getvalue()
        self.assertNotIn("LANE_HOOK_FIRED", console)
        self.assertNotIn("ERR", console)

    def test_the_payload_reaches_a_hook_verbatim_once_one_registers(self):
        body = _confirm_body(self.legacy, 0xBEEF)
        seen = []

        @lane_hooks.hook(POINT)
        def _probe(session=None, payload=None):
            seen.append((session, payload))

        self.addCleanup(lane_hooks._withdraw, _probe.__module__)

        state = self._login_and_start("navent2")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            actions = self._send(state, body)

        self.assertEqual(actions, [], "a subscriber must not make it answer")
        self.assertEqual(len(seen), 1, "the point fired exactly once")
        session, payload = seen[0]
        self.assertIs(session, state)
        self.assertEqual(
            payload, body,
            "the nested payload must arrive byte-for-byte -- LANE-A's module "
            "decodes `12 <opaque-u16> 0B 06` out of exactly these bytes",
        )
        self.assertIsInstance(payload, bytes)
        self.assertIn("LANE_HOOK_FIRED", stderr.getvalue())

    def test_a_raising_hook_neither_kills_the_session_nor_leaks_an_answer(self):
        # lane_hooks.fire() is fail-closed by construction; proven again HERE
        # because this branch is the one that runs before a hook module for it
        # exists, so the first version of that module is the likeliest thing
        # in the tree to raise on its first real frame.
        @lane_hooks.hook(POINT)
        def _boom(session=None, payload=None):
            raise ValueError("deliberate")

        self.addCleanup(lane_hooks._withdraw, _boom.__module__)

        state = self._login_and_start("navent3")
        rx_before = state.rx_frames
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            actions = self._send(state, _confirm_body(self.legacy, 1))
        self.assertEqual(actions, [])
        self.assertEqual(state.rx_frames, rx_before + 1)
        console = stderr.getvalue()
        self.assertIn("ERR", console)
        self.assertIn("deliberate", console)
        # and the session is still usable afterwards
        self.assertEqual(self._send(state, _confirm_body(self.legacy, 2)), [])

    def test_console_output_is_ascii(self):
        # The bridge console is cp874; a non-ASCII byte kills a tool
        # mid-report.  Same guard the sibling wiring test carries.
        @lane_hooks.hook(POINT)
        def _quiet(session=None, payload=None):
            pass

        self.addCleanup(lane_hooks._withdraw, _quiet.__module__)

        state = self._login_and_start("navent4")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self._send(state, _confirm_body(self.legacy, 3))
        stderr.getvalue().encode("ascii")


if __name__ == "__main__":
    unittest.main()
