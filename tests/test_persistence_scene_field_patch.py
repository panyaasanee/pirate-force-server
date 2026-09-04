"""Grades `src/pirateforce_foundation/persistence_scene_field_patch.py`.

The character-select screen prints a character's BIRTH scene (`actor_wire`
is frozen at creation) instead of her CURRENT one (`character_positions.
scene_id`, already correct) -- `COO-DECISION 20260904_1947`.  The fix is
blocked on which of two identical-looking `u16 tag 0x12` fields in
`actor_wire` is the client's scene field: the one capture this repo has
(`legacy.get_preset_actor_wire()`) was created at Port Royal, so both fields
read `1` and nothing tells them apart (`LANE-DB-TO-COO 20260904_2058`).

`COO-DECISION 20260904_2152` item 4 ordered a SCAFFOLD while a narrow RE
ticket answers that question: locate both fields' offsets (never guess which
is which), wire a patch function into the real call site
(`legacy_bridge.character_list`, via `project_actor_wire_for_list`), and gate
the whole thing behind one constant, `SCENE_FIELD`, that is `None` today.

This file's job is therefore twofold: prove the locate/patch machinery is
correct for BOTH candidate fields (so flipping the one constant later is
safe), and prove that with `SCENE_FIELD` at its current value (`None`) the
real call site's output is BYTE-IDENTICAL to what `main` sends today -- the
scaffold must not, itself, change anything a player can observe.
"""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pirateforce_foundation.persistence_scene_field_patch as scene_field_module
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.persistence_scene_field_patch import (
    FIELD_A,
    FIELD_B,
    locate_scene_field_candidates,
    patch_scene_field,
    project_actor_wire_for_list,
)
from pirateforce_foundation.session import FoundationSession
from pirateforce_foundation.store import SQLiteStore


class LocateCandidatesTests(unittest.TestCase):
    """`locate_scene_field_candidates` must find both `u16 tag 0x12` fields
    at the structural position `extract_avatar_attr_wire_from_actor` walks
    past, without deciding which one is the scene field."""

    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.wire = self.legacy.get_preset_actor_wire()

    def test_both_offsets_point_at_the_tag_0x12_value_bytes(self):
        offset_a, offset_b = locate_scene_field_candidates(self.wire)
        # The byte immediately BEFORE each returned offset is the 0x12 tag
        # this function claims to have found -- proving the offsets are the
        # VALUE bytes, not the tag bytes themselves.
        self.assertEqual(self.wire[offset_a - 1], 0x12)
        self.assertEqual(self.wire[offset_b - 1], 0x12)
        # Field B immediately follows field A's 2-byte value with no gap.
        self.assertEqual(offset_b, offset_a + 3)

    def test_both_candidates_currently_read_one_in_the_only_capture_we_have(self):
        # This is EXACTLY the ambiguity `LANE-DB-TO-COO 20260904_2058` raised:
        # both fields read 1 in the only character-creation capture this repo
        # has, because it was made at Port Royal (scene_id 1).  This test
        # documents that fact -- it does not resolve it.
        offset_a, offset_b = locate_scene_field_candidates(self.wire)
        self.assertEqual(struct.unpack_from("<H", self.wire, offset_a)[0], 1)
        self.assertEqual(struct.unpack_from("<H", self.wire, offset_b)[0], 1)

    def test_truncated_wire_raises_rather_than_guessing(self):
        with self.assertRaises(ValueError):
            locate_scene_field_candidates(self.wire[:15])

    def test_wrong_prefix_raises(self):
        mutated = bytearray(self.wire)
        mutated[0] = 0xFF
        with self.assertRaises(ValueError):
            locate_scene_field_candidates(bytes(mutated))


class PatchSceneFieldTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.wire = self.legacy.get_preset_actor_wire()
        self.offset_a, self.offset_b = locate_scene_field_candidates(self.wire)

    def test_field_none_is_byte_identical(self):
        patched = patch_scene_field(self.wire, None, 2)
        self.assertEqual(patched, self.wire)
        self.assertIs(patched, self.wire)  # not even a defensive copy

    def test_field_a_overwrites_only_field_as_two_bytes(self):
        patched = patch_scene_field(self.wire, FIELD_A, 2)
        self.assertEqual(struct.unpack_from("<H", patched, self.offset_a)[0], 2)
        # Field B and everything else is untouched.
        self.assertEqual(
            patched[: self.offset_a] + patched[self.offset_a + 2 :],
            self.wire[: self.offset_a] + self.wire[self.offset_a + 2 :],
        )

    def test_field_b_overwrites_only_field_bs_two_bytes(self):
        patched = patch_scene_field(self.wire, FIELD_B, 3)
        self.assertEqual(struct.unpack_from("<H", patched, self.offset_b)[0], 3)
        self.assertEqual(
            patched[: self.offset_b] + patched[self.offset_b + 2 :],
            self.wire[: self.offset_b] + self.wire[self.offset_b + 2 :],
        )

    def test_unknown_field_selector_raises(self):
        with self.assertRaises(ValueError):
            patch_scene_field(self.wire, "C", 2)

    def test_scene_id_out_of_u16_range_raises(self):
        with self.assertRaises(ValueError):
            patch_scene_field(self.wire, FIELD_A, 0x10000)
        with self.assertRaises(ValueError):
            patch_scene_field(self.wire, FIELD_A, -1)

    def test_max_u16_scene_id_round_trips(self):
        patched = patch_scene_field(self.wire, FIELD_B, 0xFFFF)
        self.assertEqual(struct.unpack_from("<H", patched, self.offset_b)[0], 0xFFFF)


class FakeCharacter:
    """The two attributes `project_actor_wire_for_list` reads off a real
    `model.Character` -- kept minimal so these tests do not depend on
    constructing a full `Character`/`Position` pair for every case."""

    def __init__(self, actor_wire: bytes, scene_id: int):
        self.actor_wire = actor_wire
        self.position = Position(scene_id, 0, 0.0, 0.0, 0.0)


class ProjectActorWireForListTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.wire = self.legacy.get_preset_actor_wire()
        self.offset_a, self.offset_b = locate_scene_field_candidates(self.wire)
        self._orig_scene_field = scene_field_module.SCENE_FIELD

    def tearDown(self):
        scene_field_module.SCENE_FIELD = self._orig_scene_field

    def test_default_scene_field_none_is_a_pure_pass_through(self):
        self.assertIsNone(scene_field_module.SCENE_FIELD)
        character = FakeCharacter(self.wire, scene_id=2)
        self.assertEqual(project_actor_wire_for_list(character), self.wire)

    def test_scene_field_a_reads_from_character_position(self):
        scene_field_module.SCENE_FIELD = FIELD_A
        character = FakeCharacter(self.wire, scene_id=2)
        projected = project_actor_wire_for_list(character)
        self.assertEqual(struct.unpack_from("<H", projected, self.offset_a)[0], 2)

    def test_scene_field_b_reads_from_character_position(self):
        scene_field_module.SCENE_FIELD = FIELD_B
        character = FakeCharacter(self.wire, scene_id=3)
        projected = project_actor_wire_for_list(character)
        self.assertEqual(struct.unpack_from("<H", projected, self.offset_b)[0], 3)


class CharacterListWireIsUnchangedWhileScaffoldIsOffTests(unittest.TestCase):
    """The acceptance criterion `COO-DECISION 20260904_2152` item 4 names:
    with `SCENE_FIELD` at its shipped value (`None`), the real
    `legacy_bridge.character_list` frame must be byte-identical to what the
    plain `c.actor_wire` join it replaced would have produced -- this
    scaffold changes no player-visible byte until the constant is flipped."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations"
        )
        self.store.migrate()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(1, 0, 0.0, 0.0, 931.0),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.session = FoundationSession(
            self.lifecycle, self.projector, "scene-field-scaffold-test"
        )
        self.assertIsNone(scene_field_module.SCENE_FIELD)

    def tearDown(self):
        self.tmp.cleanup()

    def _old_character_list_wire(self, characters):
        """The formula `legacy_bridge.character_list` used before this round
        -- `c.actor_wire` joined verbatim, no projection -- reproduced here
        so this test does not depend on the very code path it is grading."""
        v = self.legacy
        payload = (
            v.u8tag(0x0B, 0)
            + v.u32tag(0x14, 0)
            + v.u32tag(0x14, 0)
            + v.u32tag(0x1F, 0)
            + v.u8tag(0x0B, 0)
            + v.u8tag(0x0B, len(characters))
            + b"".join(c.actor_wire for c in characters)
            + v.u8tag(0x0B, 0)
            + v.u8tag(0x0B, 0)
        )
        return v.make_runtime_vital(v.SELECT_ACTOR_VITAL, 10, payload)

    def test_one_character_at_birth_scene(self):
        character, _ = self.session.create("test01", self.legacy.get_preset_actor_wire())
        actual = self.session.character_list()
        expected = self._old_character_list_wire(self.session.characters)
        self.assertEqual(actual, expected)

    def test_character_moved_to_a_different_scene_is_still_byte_identical(self):
        # This is the exact case `1947` is about: a character whose CURRENT
        # scene differs from her BIRTH scene.  Proving byte-identity here
        # too is what shows this round's wiring is truly inert, not merely
        # inert for a character who never left scene 1.
        character, _ = self.session.create("test01", self.legacy.get_preset_actor_wire())
        self.store.select_character(self.session.session_id, character.selector)
        self.store.save_position(
            self.session.session_id,
            character.id,
            Position(2, 0, 0.0, 0.0, 0.0),
        )
        actual = self.session.character_list()
        expected = self._old_character_list_wire(self.session.characters)
        self.assertEqual(actual, expected)
        # And the DB-side fact this whole fix exists to eventually surface is
        # really there, waiting on the constant flip: the frozen wire still
        # says scene 1 while the position row says scene 2.
        moved = self.session.characters[0]
        self.assertEqual(moved.position.scene_id, 2)
        offset_a, offset_b = locate_scene_field_candidates(moved.actor_wire)
        self.assertEqual(struct.unpack_from("<H", moved.actor_wire, offset_a)[0], 1)
        self.assertEqual(struct.unpack_from("<H", moved.actor_wire, offset_b)[0], 1)
