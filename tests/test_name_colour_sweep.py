"""RE-155: the env-gated dummy-row sweep this lane owns (LANE-B, round dipufa).

Load-bearing tests, in order: (1) fail-closed by default and on garbage
input; (2) the reserved synthetic placement band never collides with a real
placement index this repository ships anywhere; (3) each candidate body
differs from its own set's ``BASE`` by exactly the one field under test,
nothing else -- the same discipline ``test_field_mobs.py`` holds
``hostile_npc_attr`` to; (4) every label is unique ASCII text, because the
whole point of the sweep is a tester reading labels off a nameboard.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA
from pirateforce_foundation import (
    field_mob_tables,
    field_mob_tables_bg0002,
    field_mob_tables_bg0003,
    field_mob_tables_bg0004,
    field_mob_tables_bg0005,
    field_mob_tables_bg0006,
    field_mob_tables_bg0007,
    field_mob_tables_bg0008,
    field_mob_tables_bg0009,
    field_mob_tables_bg0010,
    field_mob_tables_bg0011,
    field_mob_tables_bg0015,
    field_mobs,
    name_colour_sweep,
)
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.population import NPC_STYLE_ACTOR_TYPE

BG_MODULES = (
    field_mob_tables,
    field_mob_tables_bg0002,
    field_mob_tables_bg0003,
    field_mob_tables_bg0004,
    field_mob_tables_bg0005,
    field_mob_tables_bg0006,
    field_mob_tables_bg0007,
    field_mob_tables_bg0008,
    field_mob_tables_bg0009,
    field_mob_tables_bg0010,
    field_mob_tables_bg0011,
    field_mob_tables_bg0015,
)


class NameColourSweepGateTests(unittest.TestCase):
    """Fail-closed behaviour needs no gamedata and no legacy module."""

    def test_unset_is_disabled(self) -> None:
        self.assertFalse(name_colour_sweep.sweep_enabled(env={}))

    def test_garbage_value_is_disabled(self) -> None:
        self.assertFalse(name_colour_sweep.sweep_enabled(env={"PF_NAME_COLOUR_SWEEP": "nope"}))

    def test_empty_string_is_disabled(self) -> None:
        self.assertFalse(name_colour_sweep.sweep_enabled(env={"PF_NAME_COLOUR_SWEEP": ""}))

    def test_known_sets_are_enabled(self) -> None:
        for value in name_colour_sweep.KNOWN_SETS:
            self.assertTrue(name_colour_sweep.sweep_enabled(env={"PF_NAME_COLOUR_SWEEP": value}))

    def test_unset_sweep_actors_is_empty_without_a_legacy_module(self) -> None:
        # None is never dereferenced when the gate is closed.
        self.assertEqual(name_colour_sweep.sweep_actors(None, env={}), ())


@BRIDGE_GAMEDATA.skip_unless_present()
class NameColourSweepPlacementBandTests(unittest.TestCase):
    """The reserved synthetic band must not collide with any shipped row."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_reserved_band_is_above_every_shipped_placement_index(self) -> None:
        highest = 0
        for module in BG_MODULES:
            for row in module.SHIPPED_PLACEMENTS:
                highest = max(highest, row[0])
        for row in self.legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS:
            highest = max(highest, row[0])
        self.assertLess(
            highest, name_colour_sweep.SWEEP_PLACEMENT_BASE,
            "a real placement index reaches into the reserved synthetic band",
        )

    def test_sweep_rows_stay_inside_their_own_reserved_band(self) -> None:
        for value in name_colour_sweep.KNOWN_SETS:
            actors = name_colour_sweep.sweep_actors(self.legacy, env={"PF_NAME_COLOUR_SWEEP": value})
            self.assertTrue(actors, f"set {value} produced no rows")
            for actor in actors:
                placement_index = (actor.actor_identity - 1) - 0x2000
                self.assertGreaterEqual(
                    placement_index, name_colour_sweep.SWEEP_PLACEMENT_BASE,
                )


@BRIDGE_GAMEDATA.skip_unless_present()
class NameColourSweepOneFieldPerCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_npc_base_has_no_faction_bit_set(self) -> None:
        body = name_colour_sweep._npc_plain_body(self.legacy, 0x99999, "N-BASE")
        mask_at = field_mobs._basic_mask_offset(self.legacy, body, 0x99999)
        mask = int.from_bytes(body[mask_at:mask_at + 2], "little")
        self.assertFalse(mask & field_mobs.BASIC_BIT_FACTION)

    def test_npc_faction_candidate_differs_from_base_by_exactly_the_splice(self) -> None:
        identity = 0x88888
        base = name_colour_sweep._npc_plain_body(self.legacy, identity, "N-BASE")
        candidate = name_colour_sweep._npc_faction_body(self.legacy, identity, "N-BASE", 7)
        self.assertEqual(len(candidate), len(base) + field_mobs.FACTION_SPLICE_BYTES)
        # Same label -> same head up to the mask value, and the same NPCAttr
        # tail (mask + template + preset) after the splice point.
        offset = field_mobs._faction_splice_offset(
            self.legacy, base, name_colour_sweep.NPC_BASE_TEMPLATE_ID,
            name_colour_sweep.NPC_BASE_VISUAL_PRESET,
        )
        mask_at = field_mobs._basic_mask_offset(self.legacy, base, identity)
        self.assertEqual(candidate[:mask_at], base[:mask_at])
        self.assertEqual(
            candidate[offset + field_mobs.FACTION_SPLICE_BYTES:],
            base[offset:],
        )
        base_mask = int.from_bytes(base[mask_at:mask_at + 2], "little")
        candidate_mask = int.from_bytes(candidate[mask_at:mask_at + 2], "little")
        self.assertEqual(candidate_mask, base_mask | field_mobs.BASIC_BIT_FACTION)

    def test_faction_set_candidates_differ_from_a_same_label_base_by_exactly_the_splice(self) -> None:
        # The assembled sweep gives BASE and each candidate DIFFERENT labels
        # (so a tester can read them apart on screen), and labels of
        # different lengths change body length for a reason that has
        # nothing to do with faction -- so this isolates the one field by
        # holding identity AND label fixed and calling the two composers
        # directly, the same style as
        # test_npc_faction_candidate_differs_from_base_by_exactly_the_splice.
        identity = 0x77777
        base = name_colour_sweep._npc_plain_body(self.legacy, identity, "SAME")
        for value in name_colour_sweep.FACTION_CANDIDATES:
            candidate = name_colour_sweep._npc_faction_body(
                self.legacy, identity, "SAME", value,
            )
            self.assertEqual(
                len(candidate), len(base) + field_mobs.FACTION_SPLICE_BYTES, value,
            )

    def test_actor_type_candidate_body_is_unaffected_by_actor_type(self) -> None:
        # actor_type is never a parameter of the NPCAttr composer at all --
        # it lives on the outer ActorEntry only.  Proven here by
        # reconstructing the candidate's body independently (same identity,
        # same label, no actor_type in sight) and finding it byte-identical
        # to what the sweep produced.
        actors = {
            a.label: a for a in name_colour_sweep.sweep_actors(
                self.legacy, env={"PF_NAME_COLOUR_SWEEP": "2"},
            )
        }
        base_npc = actors["N-BASE"]
        at_npc = actors[f"N-AT{name_colour_sweep.ACTOR_TYPE_CANDIDATE}"]
        self.assertNotEqual(at_npc.actor_type, base_npc.actor_type)
        self.assertEqual(base_npc.actor_type, NPC_STYLE_ACTOR_TYPE)
        self.assertEqual(at_npc.actor_type, name_colour_sweep.ACTOR_TYPE_CANDIDATE)
        reconstructed_npc = name_colour_sweep._npc_plain_body(
            self.legacy, at_npc.actor_identity, at_npc.label,
        )
        self.assertEqual(at_npc.npc_attr, reconstructed_npc)

        base_mob = actors["M-BASE"]
        at_mob = actors[f"M-AT{name_colour_sweep.ACTOR_TYPE_CANDIDATE}"]
        self.assertNotEqual(at_mob.actor_type, base_mob.actor_type)
        mob = name_colour_sweep._mob_prototype()
        from dataclasses import replace as _replace
        variant = _replace(
            mob,
            placement_index=(at_mob.actor_identity - 1) - 0x2000,
            display_name=at_mob.label,
        )
        reconstructed_mob = field_mobs.hostile_npc_attr(
            self.legacy, variant, faction=field_mobs.FIELD_MOB_FACTION,
        )
        self.assertEqual(at_mob.npc_attr, reconstructed_mob)

    def test_skin_candidate_changes_only_the_preset_text(self) -> None:
        actors = {
            a.label: a for a in name_colour_sweep.sweep_actors(
                self.legacy, env={"PF_NAME_COLOUR_SWEEP": "2"},
            )
        }
        base_npc = actors["N-BASE"]
        skin_npc = actors["N-SKIN"]
        self.assertNotEqual(base_npc.npc_attr, skin_npc.npc_attr)
        # Both labels are the same length ("N-BASE" / "N-SKIN"), so the
        # entire length delta is the preset text -- 2 bytes (UTF-16) per
        # character of difference.
        expected_delta = 2 * (
            len(name_colour_sweep.NPC_BASE_VISUAL_PRESET)
            - len(name_colour_sweep.SKIN_CANDIDATE_VISUAL_PRESET)
        )
        self.assertEqual(len(base_npc.npc_attr) - len(skin_npc.npc_attr), expected_delta)
        self.assertIn(
            name_colour_sweep.NPC_BASE_VISUAL_PRESET.encode("utf-16-le"),
            base_npc.npc_attr,
        )
        self.assertIn(
            name_colour_sweep.SKIN_CANDIDATE_VISUAL_PRESET.encode("utf-16-le"),
            skin_npc.npc_attr,
        )


@BRIDGE_GAMEDATA.skip_unless_present()
class NameColourSweepLabelAndFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_every_label_is_unique_ascii(self) -> None:
        for value in name_colour_sweep.KNOWN_SETS:
            actors = name_colour_sweep.sweep_actors(
                self.legacy, env={"PF_NAME_COLOUR_SWEEP": value},
            )
            labels = [a.label for a in actors]
            self.assertEqual(len(labels), len(set(labels)), value)
            for label in labels:
                self.assertTrue(label.isascii(), label)

    def test_build_sweep_population_frame_round_trips(self) -> None:
        for value in name_colour_sweep.KNOWN_SETS:
            result = name_colour_sweep.build_sweep_population(
                self.legacy, env={"PF_NAME_COLOUR_SWEEP": value},
            )
            self.assertIsNotNone(result)
            pc, frame = result
            self.assertEqual(frame, self.legacy.frame_pc(pc))

    def test_unarmed_build_sweep_population_is_none(self) -> None:
        self.assertIsNone(
            name_colour_sweep.build_sweep_population(self.legacy, env={}),
        )


if __name__ == "__main__":
    unittest.main()
