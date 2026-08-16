"""Offline guard for coverage row chat/server_system_message.

The row is graded ``runtime_pass`` on two evidence reports and its own note says
the vital "has no offline test, so it is one observation rather than an owned
feature". These tests supply the offline half: the exact wire shape, the
one-shot emission discipline through the real dispatch path, and a fail-closed
guard that no Foundation module has quietly taken ownership of the vital.

Nothing here upgrades the claim. It only makes the claim watched.
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

WELCOME_TEXT = "Pirate Force local server online"
WELCOME_LABEL = "V99_SHOW_MESSAGE_LOCAL_SERVER_ONLINE"
WELCOME_EVENT = "v99_show_message_local_server_online"


class ShowMessageWireTests(unittest.TestCase):
    """The builder emits exactly one wide string and nothing else."""

    @classmethod
    def setUpClass(cls):
        cls.v = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_vital_id_and_version_are_the_decoded_pair(self):
        self.assertEqual(self.v.SHOW_MESSAGE_VITAL, 0x36D2)
        self.assertEqual(self.v.NAMES[self.v.SHOW_MESSAGE_VITAL], "ShowMessageVital")

    def test_payload_is_one_wide_string_tag_and_no_other_field(self):
        pc, frame = self.v.make_show_message(WELCOME_TEXT)
        head = (
            self.v.u16tag(0x12, self.v.GSCN_RUNTIME_PROTOCOL_RES)
            + self.v.u32tag(0x14, 0)
            + self.v.u8tag(0x08, 4)
            + self.v.u8tag(0x0B, 2)
            + self.v.u16tag(0x12, 1)
            + self.v.u16tag(0x12, self.v.SHOW_MESSAGE_VITAL)
            + self.v.u8tag(0x0B, 0)
        )
        self.assertTrue(pc.startswith(head))
        body = pc[len(head):]
        # RuntimeRes v4 keeps its derived-class change mask after the collection.
        self.assertTrue(body.endswith(self.v.u8tag(0x0B, 0)))
        payload = body[: -len(self.v.u8tag(0x0B, 0))]
        # Decode the wide string by hand rather than trusting wstr_tag both ways.
        self.assertEqual(payload[0], 0x48)
        declared = struct.unpack("<I", payload[1:5])[0]
        self.assertEqual(declared, len(WELCOME_TEXT.encode("utf-16le")))
        self.assertEqual(payload[5:].decode("utf-16le"), WELCOME_TEXT)
        self.assertEqual(len(payload), 5 + declared)
        self.assertEqual(frame, self.v.frame_pc(pc))

    def test_non_ascii_text_survives_the_wide_encoding(self):
        text = "ทดสอบ"  # Thai, two bytes per code unit
        pc, _ = self.v.make_show_message(text)
        self.assertIn(text.encode("utf-16le"), pc)
        self.assertEqual(pc.count(text.encode("utf-16le")), 1)

    def test_empty_text_is_rejected_because_the_client_drops_it(self):
        with self.assertRaises(ValueError):
            self.v.make_show_message("")

    def test_exactly_one_vital_is_carried(self):
        pc, _ = self.v.make_show_message(WELCOME_TEXT)
        self.assertEqual(pc.count(self.v.u16tag(0x12, self.v.SHOW_MESSAGE_VITAL)), 1)


class ShowMessageEmissionTests(unittest.TestCase):
    """The welcome message is emitted once per connection, on the first RuntimeReq."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db = Path(self.tmp.name) / "system_message.sqlite3"
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
        seed = FoundationSession(self.lifecycle, self.projector, "msg-user")
        actor = self.v.get_preset_actor_wire().replace(
            self.v.wstr_tag("test01"), self.v.wstr_tag("Arena01"), 1
        )
        self.character, _ = seed.create("Arena01", actor)
        self.scenario = load_scene_load_scenario(
            ROOT / "scenarios/scene2_fighting_fish_soldier.json"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def entered_state(self):
        factory = lambda token: ReadOnlyFoundationSession(
            self.store, self.projector, token, self.scenario
        )
        state = make_state_class(
            self.v,
            self.lifecycle,
            self.projector,
            scene_load_scenario=self.scenario,
            session_factory=factory,
        )("msg-user")
        state.dispatch(self.v.parse_outer(self.v._synthetic_client_login_pc()))
        state.dispatch(
            self.v.parse_outer(
                self.v._synthetic_start_game_pc(self.character.selector)
            )
        )
        return state

    def runtime_req(self):
        return self.v.parse_outer(self.v.V136_EMPTY_RUNTIME_REQ_PC)

    def test_first_runtime_req_emits_the_exact_builder_output_once(self):
        state = self.entered_state()
        actions = state.dispatch(self.runtime_req())
        labels = [action[0] for action in actions]
        self.assertEqual(labels.count(WELCOME_LABEL), 1)
        message = actions[labels.index(WELCOME_LABEL)]
        self.assertEqual(
            (message[1], message[2]), self.v.make_show_message(WELCOME_TEXT)
        )
        self.assertEqual(state.events.count(WELCOME_EVENT), 1)

    def test_repeat_runtime_req_never_sends_a_second_message(self):
        state = self.entered_state()
        state.dispatch(self.runtime_req())
        for _ in range(3):
            self.assertEqual(state.dispatch(self.runtime_req()), [])
        self.assertEqual(state.events.count(WELCOME_EVENT), 1)
        self.assertTrue(state.welcome_message_sent)

    def test_message_follows_the_runtime_ack_and_never_precedes_it(self):
        state = self.entered_state()
        labels = [action[0] for action in state.dispatch(self.runtime_req())]
        self.assertIn("RUNTIME_RES_ACK_FIRST_REQ", labels)
        self.assertLess(
            labels.index("RUNTIME_RES_ACK_FIRST_REQ"), labels.index(WELCOME_LABEL)
        )

    def test_a_connection_that_never_requests_runtime_gets_no_message(self):
        state = self.entered_state()
        self.assertFalse(state.welcome_message_sent)
        self.assertNotIn(WELCOME_EVENT, state.events)


class ShowMessageOwnershipGuardTests(unittest.TestCase):
    """Fail closed if a Foundation module starts owning the vital.

    The coverage note claims the vital is emitted by the frozen legacy seam and
    that no Foundation module owns it. If that ever stops being true, the note
    is stale and the row must be re-graded, so this guard breaks on purpose.
    """

    def test_no_foundation_module_constructs_a_show_message_vital(self):
        offenders = []
        for path in sorted((ROOT / "src/pirateforce_foundation").glob("*.py")):
            text = path.read_text(encoding="utf-8")
            if "SHOW_MESSAGE" in text or "0x36D2" in text.upper():
                offenders.append(path.name)
        self.assertEqual(
            offenders,
            [],
            "Foundation now references ShowMessageVital; re-grade "
            "chat/server_system_message instead of loosening this guard",
        )


if __name__ == "__main__":
    unittest.main()
