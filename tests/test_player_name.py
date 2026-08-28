import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.actor_wire import read_name
from pirateforce_foundation.player_wire import (
    make_actor_attr_with_basic_faction,
    make_actor_attr_with_name,
    make_actor_attr_with_name_and_class,
)
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.session import FoundationSession
from pirateforce_foundation.store import SQLiteStore


class PlayerNameProjectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.store = SQLiteStore(Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations")
        self.store.migrate()
        self.projector = LegacyProjector(self.legacy)
        lifecycle = CharacterLifecycle(
            self.store, Position(1, 0, 0.0, 0.0, 931.0),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.lifecycle = lifecycle
        self.session = FoundationSession(lifecycle, self.projector, "name-test")

    def tearDown(self):
        self.tmp.cleanup()

    def create(self, name="กัปตัน01"):
        template = self.legacy.get_preset_actor_wire()
        old = self.legacy.wstr_tag("test01")
        self.assertEqual(template.count(old), 1)
        template = template.replace(old, self.legacy.wstr_tag(name), 1)
        return self.session.create(name, template)[0]

    def test_persisted_name_is_one_ordered_actor_attr_wstring(self):
        character = self.create()
        list_pc, _ = self.session.character_list()
        selected, (start_pc, _) = self.session.select_and_start(character.selector)
        self.assertEqual(selected.name, character.name)
        self.assertIn(character.actor_wire, list_pc)
        self.assertEqual(character.actor_wire.count(self.legacy.wstr_tag(character.name)), 1)

        name_wire = self.legacy.wstr_tag(character.name)
        # CORE-REQUEST-023: the real login path (select_and_start) now goes
        # through make_actor_attr_with_name_and_class, which adds level
        # (BasicAttr +0x5E, bit 0x0002), movement speed (+0x54, bit 0x0040)
        # and class_id (ActorAttr +0x8C, bit 0x00000001) on top of the
        # proven name/HP/scene/cash baseline (CORE-REQUEST-023 probe-base-1
        # widening; see player_wire.py's own module docstring). MP current/
        # max and STR/CON/DEX/INT/PER are deliberately NOT emitted -- no
        # committed source names a value for them (same docstring).
        actor = make_actor_attr_with_name_and_class(
            self.legacy, character.identity_lo, character.identity_hi,
            character.position.scene_id, character.position.scene_seq,
            character.name,
        )
        identity = bytes([0x32]) + character.identity_lo.to_bytes(4, "little") + character.identity_hi.to_bytes(4, "little")
        expected_prefix = (
            self.legacy.u8tag(0x0B, 1)
            + identity
            + self.legacy.u16tag(0x12, 0x034E)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u32tag(0x14, 100)
            + self.legacy.u32tag(0x14, 100)
            + self.legacy.f32tag(400.0)
            + self.legacy.u16tag(0x12, character.position.scene_id)
            + bytes([0x32]) + character.position.scene_seq.to_bytes(8, "little")
            + bytes([0x32]) + (0x01000801).to_bytes(4, "little") + bytes(4)
            + self.legacy.u8tag(0x05, 1)
            + self.legacy.u32tag(0x19, 1)
            + bytes([0x32]) + self.legacy.V116_INITIAL_CASH.to_bytes(8, "little")
            + name_wire
        )
        self.assertEqual(actor, expected_prefix)
        self.assertEqual(actor.count(name_wire), 1)
        self.assertEqual(start_pc.count(name_wire), 1)
        self.assertIn(actor, start_pc)

    def test_faction_projection_preserves_name_and_only_adds_frozen_value(self):
        character = self.create("Arena01")
        normal = make_actor_attr_with_name(
            self.legacy, character.identity_lo, character.identity_hi, 2, 0,
            character.name,
        )
        faction = make_actor_attr_with_basic_faction(
            self.legacy, character.identity_lo, character.identity_hi, 2, 0,
            character.name, 1,
        )
        name_wire = self.legacy.wstr_tag(character.name)
        faction_at = 14 + 10 + 3 + 9
        expected = (
            normal[:11]
            + self.legacy.u16tag(0x12, 0x070C)
            + normal[14:faction_at]
            + self.legacy.u32tag(0x14, 1)
            + normal[faction_at:]
        )
        self.assertEqual(faction, expected)
        self.assertEqual(faction.count(name_wire), 1)
        self.assertTrue(faction.endswith(name_wire))

    def test_rejects_empty_non_string_and_unencodable_name(self):
        args = (self.legacy, 1, 0, 1, 0)
        with self.assertRaisesRegex(ValueError, "empty"):
            make_actor_attr_with_name(*args, "")
        with self.assertRaisesRegex(TypeError, "str"):
            make_actor_attr_with_name(*args, b"name")
        with self.assertRaisesRegex(ValueError, "UTF-16"):
            make_actor_attr_with_name(*args, "\ud800")

    def test_actor_name_prefix_parser_is_strict_and_bounded_by_input(self):
        actor = self.legacy.get_preset_actor_wire()
        self.assertEqual(read_name(actor), "test01")
        for malformed in (
            actor[:11] + b"\x44" + actor[12:],
            actor[:12] + (13).to_bytes(4, "little") + actor[16:],
            actor[:12] + (0xFFFFFFFE).to_bytes(4, "little") + actor[16:],
            actor[:16] + b"\x00\xD8" + actor[18:],
        ):
            with self.subTest(prefix=malformed[:20].hex()):
                with self.assertRaises(ValueError):
                    read_name(malformed)

    def test_create_rejects_noncanonical_name_without_reply_or_row(self):
        original = self.legacy._V25_REAL_CREATE_PC
        old = self.legacy.wstr_tag("test01")
        self.assertEqual(original.count(old), 1)
        for index, raw_name in enumerate((" test01 ", "ｔｅｓｔ０１")):
            with self.subTest(raw_name=raw_name):
                state = make_state_class(
                    self.legacy, self.lifecycle, self.projector,
                )(f"noncanonical-{index}")
                request = original.replace(old, self.legacy.wstr_tag(raw_name), 1)
                actions = state.dispatch(self.legacy.parse_outer(request))
                self.assertEqual(actions, [])
                self.assertIn("foundation_create_rejected_no_reply", state.events)
                self.assertEqual(
                    self.store.list_characters(state.foundation.account_id), []
                )

    def test_foundation_seam_rejects_canonical_name_wire_mismatch(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.session.create("test02", self.legacy.get_preset_actor_wire())
        self.assertEqual(
            self.store.list_characters(self.session.account_id), []
        )


if __name__ == "__main__":
    unittest.main()
