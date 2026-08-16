"""Offline guard for coverage row movement/teleport_transport.

The row is graded ``runtime_pass`` on V137 (one standalone TeleportVital v4 to a
decoded MARKER row transported the client) and V131 (the TeleportCheck
challenge/echo path is only captured). Its note is careful that a
server-validated transport with its own acceptance rule does not exist.

These tests pin exactly that much and no more:
  * the transport probe carries the decoded MARKER1 target and constructor
    defaults everywhere else,
  * the only difference from the proven bootstrap teleport is carrier and XYZ,
  * the probe is emitted once, only after the exact V136 confirm, and never
    from a near-miss packet or an unprompted echo.
"""

from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.scene_load import load_scene_load_scenario
from pirateforce_foundation.session import FoundationSession, ReadOnlyFoundationSession
from pirateforce_foundation.store import SQLiteStore

TRANSPORT_LABEL = (
    "V137_ISOLATED_COMPOSITIONAL_MARKER1_TELEPORTVITAL_TRANSPORT_PROBE_ONCE"
)


class TeleportTargetWireTests(unittest.TestCase):
    """The transport probe is the decoded MARKER1 row and constructor defaults."""

    @classmethod
    def setUpClass(cls):
        cls.v = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_marker1_constants_are_the_decoded_row(self):
        self.assertEqual(self.v.V137_MARKER_ID, 1)
        self.assertEqual(
            (
                self.v.V137_MARKER_SCENE_ID,
                self.v.V137_MARKER_SCENE_SEQ,
                self.v.V137_MARKER_X,
                self.v.V137_MARKER_Y,
                self.v.V137_MARKER_Z,
            ),
            (1, 0, -10322.0, -755.0, 671.0),
        )

    def test_target_object_layout_is_scene_seq_two_flags_and_vec3(self):
        target = self.v.make_teleport_target(1, 0, -10322.0, -755.0, 671.0)
        expected = (
            self.v.u16tag(0x12, 1)
            + b"\x32"
            + struct.pack("<Q", 0)
            + self.v.u8tag(0x0B, 0)
            + self.v.u8tag(0x0B, 0)
            + self.v.f32tag(-10322.0)
            + self.v.f32tag(-755.0)
            + self.v.f32tag(671.0)
        )
        self.assertEqual(target, expected)

    def test_probe_is_one_teleport_vital_version4_on_the_runtime_carrier(self):
        pc, frame = self.v.make_v137_marker1_transport_probe()
        head = (
            self.v.u16tag(0x12, self.v.GSCN_RUNTIME_PROTOCOL_RES)
            + self.v.u32tag(0x14, 0)
            + self.v.u8tag(0x08, 4)
            + self.v.u8tag(0x0B, 2)
            + self.v.u16tag(0x12, 1)
            + self.v.u16tag(0x12, self.v.TELEPORT_VITAL)
            + self.v.u8tag(0x0B, 4)
        )
        self.assertTrue(pc.startswith(head))
        self.assertEqual(pc.count(self.v.u16tag(0x12, self.v.TELEPORT_VITAL)), 1)
        self.assertEqual(self.v.TELEPORT_VITAL, 0x25A2)
        self.assertEqual(frame, self.v.frame_pc(pc))

    def test_probe_differs_from_the_bootstrap_teleport_only_by_carrier_and_xyz(self):
        probe_pc, _ = self.v.make_v137_marker1_transport_probe()
        zero_login_pc, _ = self.v.make_login_teleport(1, 0, 0.0, 0.0, 0.0)
        marker_login_pc, _ = self.v.make_login_teleport(
            self.v.V137_MARKER_SCENE_ID,
            self.v.V137_MARKER_SCENE_SEQ,
            self.v.V137_MARKER_X,
            self.v.V137_MARKER_Y,
            self.v.V137_MARKER_Z,
        )
        # Same vital body under two different outer carriers.
        vital = self.v.u16tag(0x12, self.v.TELEPORT_VITAL) + self.v.u8tag(0x0B, 4)
        probe_body = probe_pc[probe_pc.index(vital) + len(vital):]
        marker_body = marker_login_pc[marker_login_pc.index(vital) + len(vital):]
        self.assertTrue(probe_body.startswith(marker_body))
        # The RuntimeRes carrier adds exactly the trailing derived change mask.
        self.assertEqual(probe_body[len(marker_body):], self.v.u8tag(0x0B, 0))
        # And the only body difference from the stable zero-target bootstrap is
        # the three floats, so no other field was quietly repurposed.
        zero_body = zero_login_pc[zero_login_pc.index(vital) + len(vital):]
        self.assertEqual(len(zero_body), len(marker_body))
        diff = [i for i in range(len(zero_body)) if zero_body[i] != marker_body[i]]
        floats = b"".join(
            self.v.f32tag(value)
            for value in (
                self.v.V137_MARKER_X,
                self.v.V137_MARKER_Y,
                self.v.V137_MARKER_Z,
            )
        )
        start = marker_body.index(floats)
        self.assertTrue(all(start <= i < start + len(floats) for i in diff))

    def test_challenge_is_the_bounded_scene1_value_and_carries_no_target(self):
        pc, _ = self.v.make_teleport_check_scene1_challenge()
        self.assertEqual(self.v.TELEPORT_CHECK_VITAL, 0x4477)
        self.assertEqual(self.v.V131_TELEPORT_CHECK_VALUE, 1)
        self.assertEqual(pc.count(self.v.u16tag(0x12, self.v.TELEPORT_CHECK_VITAL)), 1)
        self.assertNotIn(self.v.u16tag(0x12, self.v.TELEPORT_VITAL), pc)


class TeleportTransportEmissionTests(unittest.TestCase):
    """Only the exact confirm packet, once, after the prompt, produces a probe."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db = Path(self.tmp.name) / "teleport.sqlite3"
        self.store = SQLiteStore(db, ROOT / "migrations")
        self.store.migrate()
        self.v = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.projector = LegacyProjector(self.v)
        default = Position(
            1, 0, self.v.V135_PLAYER_X, self.v.V135_PLAYER_Y, self.v.V135_PLAYER_Z
        )
        self.lifecycle = CharacterLifecycle(
            self.store, default, self.v.extract_avatar_attr_wire_from_actor
        )
        seed = FoundationSession(self.lifecycle, self.projector, "tp-user")
        actor = self.v.get_preset_actor_wire().replace(
            self.v.wstr_tag("test01"), self.v.wstr_tag("Arena01"), 1
        )
        self.character, _ = seed.create("Arena01", actor)
        self.scenario = load_scene_load_scenario(
            ROOT / "scenarios/scene2_fighting_fish_soldier.json"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def armed_state(self, *, prompt_sent=True):
        factory = lambda token: ReadOnlyFoundationSession(
            self.store, self.projector, token, self.scenario
        )
        state = make_state_class(
            self.v,
            self.lifecycle,
            self.projector,
            scene_load_scenario=self.scenario,
            session_factory=factory,
        )("tp-user")
        state.dispatch(self.v.parse_outer(self.v._synthetic_client_login_pc()))
        state.dispatch(
            self.v.parse_outer(
                self.v._synthetic_start_game_pc(self.character.selector)
            )
        )
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        state.v136_marker1_prompt_sent = prompt_sent
        return state

    def confirm(self):
        return self.v.parse_outer(self.v.V136_MARKER1_CONFIRM_PC)

    def test_exact_confirm_emits_one_probe_equal_to_the_builder(self):
        state = self.armed_state()
        actions = state.dispatch(self.confirm())
        labels = [action[0] for action in actions]
        self.assertEqual(labels.count(TRANSPORT_LABEL), 1)
        probe = actions[labels.index(TRANSPORT_LABEL)]
        self.assertEqual(
            (probe[1], probe[2]), self.v.make_v137_marker1_transport_probe()
        )
        self.assertEqual(state.v137_marker1_transport_send_count, 1)

    def test_replayed_confirm_never_emits_a_second_probe(self):
        state = self.armed_state()
        state.dispatch(self.confirm())
        for _ in range(3):
            labels = [action[0] for action in state.dispatch(self.confirm())]
            self.assertNotIn(TRANSPORT_LABEL, labels)
        self.assertEqual(state.v137_marker1_transport_send_count, 1)

    def test_confirm_without_the_prompt_is_refused(self):
        state = self.armed_state(prompt_sent=False)
        labels = [action[0] for action in state.dispatch(self.confirm())]
        self.assertNotIn(TRANSPORT_LABEL, labels)
        self.assertEqual(state.v137_marker1_transport_send_count, 0)
        self.assertFalse(state.v137_marker1_transport_sent)

    def test_near_miss_packets_are_refused_byte_for_byte(self):
        base = self.v.V136_MARKER1_CONFIRM_PC
        for index in range(len(base)):
            mutated = bytearray(base)
            mutated[index] ^= 0x01
            state = self.armed_state()
            try:
                parsed = self.v.parse_outer(bytes(mutated))
            except Exception:
                continue  # A packet that will not parse cannot transport either.
            try:
                labels = [action[0] for action in state.dispatch(parsed)]
            except Exception:
                continue
            self.assertNotIn(
                TRANSPORT_LABEL,
                labels,
                f"byte {index} flipped still transported",
            )

    def test_plain_scene1_echo_alone_does_not_transport(self):
        state = self.armed_state(prompt_sent=False)
        state.teleport_check_challenge_sent = True
        echo_pc = (
            self.v.u16tag(0x12, self.v.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.v.u32tag(0x14, 0)
            + self.v.u8tag(0x08, 0)
            + self.v.u8tag(0x0B, 2)
            + self.v.u16tag(0x12, 1)
            + self.v.u16tag(0x12, self.v.TELEPORT_CHECK_VITAL)
            + self.v.u8tag(0x0B, 0)
            + self.v.u16tag(0x0F, self.v.V131_TELEPORT_CHECK_VALUE)
        )
        labels = [action[0] for action in state.dispatch(self.v.parse_outer(echo_pc))]
        self.assertNotIn(TRANSPORT_LABEL, labels)
        self.assertEqual(state.teleport_check_echo_capture_count, 1)
        self.assertEqual(
            state.teleport_check_echo_last_value, self.v.V131_TELEPORT_CHECK_VALUE
        )


if __name__ == "__main__":
    unittest.main()
