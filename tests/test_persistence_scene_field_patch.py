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

`RE-248` (`notes_to_chief/20260905_0053_RE-248-RESULT-FIELD-A-IS-SCENE-
FIELD-B-IS-LEVEL.md`) answered the question: `FIELD_A` is the client's
scene-name field, `FIELD_B` is character level.  `SCENE_FIELD` is now
`FIELD_A`.

This file's job is therefore threefold: prove the locate/patch machinery is
correct for BOTH candidate fields (so the constant stays swappable if a
future field is ever misidentified), prove that with `SCENE_FIELD` at
`None` the real call site's output is BYTE-IDENTICAL to the plain
`c.actor_wire` join it replaced (regression coverage for the off state,
even though it no longer ships), and prove that with `SCENE_FIELD` at its
shipped value (`FIELD_A`) the real call site now prints each character's
CURRENT scene, not her frozen birth one.
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

    def test_bool_scene_id_is_rejected_not_silently_accepted_as_zero_or_one(self):
        # `pf-adversary` (this round): bool is an int subclass, so an
        # unguarded range check would happily accept `True`/`False` as 1/0.
        with self.assertRaises(TypeError):
            patch_scene_field(self.wire, FIELD_A, True)
        with self.assertRaises(TypeError):
            patch_scene_field(self.wire, FIELD_A, False)

    def test_non_int_scene_id_raises_type_error_not_struct_error(self):
        # `pf-adversary` (this round): a float or numeric string used to fall
        # straight into `struct.pack_into`, raising `struct.error` instead of
        # a caller-checkable exception type.
        with self.assertRaises(TypeError):
            patch_scene_field(self.wire, FIELD_A, 5.5)
        with self.assertRaises(TypeError):
            patch_scene_field(self.wire, FIELD_A, "5")


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

    def test_shipped_scene_field_is_field_a(self):
        # RE-248 named FIELD_A as the scene field; this is what ships.
        self.assertEqual(scene_field_module.SCENE_FIELD, FIELD_A)

    def test_scene_field_none_is_still_a_pure_pass_through(self):
        # `None` no longer ships, but the machinery must still honor it as a
        # true no-op -- this is what let the scaffold round land inert.
        scene_field_module.SCENE_FIELD = None
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


class CharacterListWireProjectsCurrentSceneTests(unittest.TestCase):
    """The acceptance criterion `COO-DECISION 20260904_1947` named, now that
    `RE-248` has settled which field is which and `SCENE_FIELD` ships as
    `FIELD_A`: the real `legacy_bridge.character_list` frame must print each
    character's CURRENT scene (`character_positions.scene_id`), not the
    BIRTH scene frozen into `actor_wire` at creation -- and every other byte
    of the frame, `FIELD_B` (character level) included, must be untouched."""

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
        self.assertEqual(scene_field_module.SCENE_FIELD, FIELD_A)

    def tearDown(self):
        self.tmp.cleanup()

    def _old_character_list_wire(self, characters):
        """The formula `legacy_bridge.character_list` used before this fix
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

    def test_one_character_at_birth_scene_is_still_byte_identical(self):
        # Birth scene == current scene here (both 1), so patching FIELD_A to
        # the current scene id writes back the same value already there --
        # the fix is inert, not wrong, for a character who never moved.
        character, _ = self.session.create("test01", self.legacy.get_preset_actor_wire())
        actual = self.session.character_list()
        expected = self._old_character_list_wire(self.session.characters)
        self.assertEqual(actual, expected)

    def test_character_moved_to_a_different_scene_now_shows_the_current_one(self):
        # This is the exact case `1947` is about: a character whose CURRENT
        # scene differs from her BIRTH scene.  The old formula would have
        # printed birth scene 1 forever; the fix must print current scene 2.
        character, _ = self.session.create("test01", self.legacy.get_preset_actor_wire())
        self.store.select_character(self.session.session_id, character.selector)
        self.store.save_position(
            self.session.session_id,
            character.id,
            Position(2, 0, 0.0, 0.0, 0.0),
        )
        # `character_list()` / `_old_character_list_wire()` both return
        # `make_runtime_vital`'s `(unframed_payload, framed_bytes)` pair --
        # compare the unframed payload, where the byte offsets `locate_
        # scene_field_candidates` reasons about actually live.
        actual, _ = self.session.character_list()
        stale, _ = self._old_character_list_wire(self.session.characters)
        self.assertNotEqual(actual, stale, "select-screen frame still carries the frozen birth scene")

        moved = self.session.characters[0]
        self.assertEqual(moved.position.scene_id, 2)
        # The underlying `actor_wire` row is untouched (never rewritten in
        # the DB, per the module's own "what this does not do" contract) --
        # still birth scene 1 at both candidate offsets.
        offset_a, offset_b = locate_scene_field_candidates(moved.actor_wire)
        self.assertEqual(struct.unpack_from("<H", moved.actor_wire, offset_a)[0], 1)
        self.assertEqual(struct.unpack_from("<H", moved.actor_wire, offset_b)[0], 1)

        # The frame actually sent on the wire equals the stale formula's
        # output with ONLY FIELD_A's two-byte span patched to the current
        # scene id -- FIELD_B (level) and every other byte is byte-for-byte
        # identical to what the old, unpatched join would have sent.  Locate
        # that span within the FULL frame (envelope + list header +
        # `actor_wire`, not just the wire slice `locate_scene_field_
        # candidates` was proven against) by finding `stale`'s copy of the
        # still-unpatched `actor_wire` -- `stale` was built from the raw
        # `c.actor_wire` join, so it must appear there byte-for-byte -- and
        # offsetting from there, rather than diffing, since a scene id that
        # only changes one octet of the little-endian u16 (1 -> 2) would
        # otherwise make a byte-diff undercount the span.
        wire_start = stale.find(moved.actor_wire)
        self.assertGreaterEqual(wire_start, 0, "stale frame does not contain the unpatched actor_wire")
        offset_a, _ = locate_scene_field_candidates(moved.actor_wire)
        field_offset = wire_start + offset_a

        self.assertEqual(len(actual), len(stale))
        self.assertEqual(
            actual[:field_offset] + actual[field_offset + 2 :],
            stale[:field_offset] + stale[field_offset + 2 :],
            "a byte outside FIELD_A's span changed",
        )
        self.assertEqual(struct.unpack_from("<H", actual, field_offset)[0], 2)
        self.assertEqual(struct.unpack_from("<H", stale, field_offset)[0], 1)

    def _preset(self, name):
        """Same fixture-name-swap helper `tests/test_foundation.py` uses --
        `get_preset_actor_wire()` is a single fixed capture, so a second
        character with a DIFFERENT (and differently-sized) name needs its
        `wstr` name field replaced, which shifts every byte after it."""
        actor = self.legacy.get_preset_actor_wire()
        old = self.legacy.wstr_tag("test01")
        self.assertEqual(actor.count(old), 1)
        return actor.replace(old, self.legacy.wstr_tag(name), 1)

    def test_two_characters_with_different_name_lengths_patch_independently(self):
        # pf-adversary (this round): `project_actor_wire_for_list` is called
        # PER CHARACTER before the frame join (`legacy_bridge.py:35`), so a
        # name-length difference that shifts one character's FIELD_A offset
        # must never affect the other character's patch.  Proven here with a
        # live two-character list rather than argued from the call shape.
        short, _ = self.session.create("ab", self._preset("ab"))
        self.store.select_character(self.session.session_id, short.selector)
        self.store.save_position(
            self.session.session_id, short.id, Position(2, 0, 0.0, 0.0, 0.0)
        )
        long_name = "a-much-longer-character-name-than-the-other-one"
        long, _ = self.session.create(long_name, self._preset(long_name))
        self.store.select_character(self.session.session_id, long.selector)
        self.store.save_position(
            self.session.session_id, long.id, Position(5, 0, 0.0, 0.0, 0.0)
        )

        self.session.characters = self.store.list_characters(self.session.account_id)
        self.assertEqual(len(self.session.characters), 2)
        by_name = {c.name: c for c in self.session.characters}

        actual, _ = self.session.character_list()

        for character, expected_scene in ((by_name["ab"], 2), (by_name[long_name], 5)):
            offset_a, offset_b = locate_scene_field_candidates(character.actor_wire)
            wire_start = actual.find(
                patch_scene_field(character.actor_wire, FIELD_A, expected_scene)[:offset_a]
            )
            self.assertGreaterEqual(
                wire_start, 0,
                f"could not locate {character.name!r}'s patched FIELD_A span in the joined frame",
            )
            field_offset = wire_start + offset_a
            self.assertEqual(
                struct.unpack_from("<H", actual, field_offset)[0], expected_scene,
                f"{character.name!r} did not get its own current scene",
            )
            # FIELD_B (level) for THIS character is untouched -- still birth
            # value 1, not bled over from the other character's scene id.
            level_offset = wire_start + offset_b
            self.assertEqual(struct.unpack_from("<H", actual, level_offset)[0], 1)
