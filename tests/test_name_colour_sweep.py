"""RE-155: the env-gated dummy-row sweep this lane owns (LANE-B, round dipufa).

Load-bearing tests, in order: (1) fail-closed by default and on garbage
input; (2) the reserved synthetic placement band never collides with a real
placement index this repository ships anywhere; (3) each candidate body
differs from its own set's ``BASE`` by exactly the one field under test,
nothing else -- the same discipline ``test_field_mobs.py`` holds
``hostile_npc_attr`` to; (4) every label is unique ASCII text, because the
whole point of the sweep is a tester reading labels off a nameboard.
"""
import math
import re
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
    scene2_prison_exile_tables,
    world_bg1001_identity,
    world_bg3001_identity,
    world_bg3007_identity,
    world_bg3008_identity,
    world_bg4001_identity,
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

# pf-adversary (round dipufa, finding 2): the check below used to walk only
# BG_MODULES + the v141 town table, and never looked at these five modules'
# own placement tables (each row's element 0 is a placement index, same
# shape as every table in BG_MODULES) -- no live collision today (their
# indices top out in the low tens), but the module docstring's claim of
# "disjoint from every placement-index table this repository ships" was not
# what the test actually checked.  Listed here BY NAME because these five
# modules do not share one common table attribute name
# (KNOWN_PLACEMENTS/UNRESOLVED_PLACEMENTS vs _PLACEMENT_ROWS), so a
# discovery loop would have to special-case them anyway; a later round that
# adds a sixth such module and forgets to list it here is exactly the risk
# pf-adversary named, and remains open.
_EXTRA_PLACEMENT_ROW_SOURCES = (
    (scene2_prison_exile_tables, "KNOWN_PLACEMENTS"),
    (scene2_prison_exile_tables, "UNRESOLVED_PLACEMENTS"),
    (world_bg1001_identity, "_PLACEMENT_ROWS"),
    (world_bg3001_identity, "_PLACEMENT_ROWS"),
    (world_bg3007_identity, "_PLACEMENT_ROWS"),
    (world_bg3008_identity, "_PLACEMENT_ROWS"),
    (world_bg4001_identity, "_PLACEMENT_ROWS"),
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
        for module, attr in _EXTRA_PLACEMENT_ROW_SOURCES:
            for row in getattr(module, attr):
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


class CandidateIsAnExperimentThatCanBeReadTests(unittest.TestCase):
    """Round b08g3z: the two ways a sweep row can be unreadable on screen.

    Both were measured by pf-adversary through chief's letter
    2026-09-07T03:41+07:00 and both are properties of the CANDIDATE CHOICE,
    which is this lane's own, so both get a test that goes red on the
    revert rather than a paragraph that does not.
    """

    @classmethod
    def setUpClass(cls) -> None:
        BRIDGE_GAMEDATA.require(cls)
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_the_actor_type_candidate_still_binds_an_npc_attr(self) -> None:
        """3 (``CMyActor``) produces NO nameplate, not a differently-coloured
        one: reports/PF_MPAUDIT_FOLLOWUP001_ACTOR_TYPE_DISPATCH_STATIC_
        20260818.md line 129 -- ``NPCAttr``'s vtable ``+0x38`` thunk is-a
        checks ``CNetNPC`` ("so 4, 5") and silently no-ops for anything
        else.  A row with no nameplate is worse than no row: the tester
        writes down FAIL for a colour that was never drawn.
        """
        self.assertIn(
            name_colour_sweep.ACTOR_TYPE_CANDIDATE,
            name_colour_sweep.NPC_ATTR_BINDING_ACTOR_TYPES,
        )
        # ...and it is still a FLIP, not a second copy of N-BASE.
        self.assertNotEqual(
            name_colour_sweep.ACTOR_TYPE_CANDIDATE,
            field_mobs.NPC_STYLE_ACTOR_TYPE,
        )

    def test_the_binding_set_is_read_out_of_the_report_not_typed(self) -> None:
        """pf-adversary D-8: a hand-typed pin and a hand-typed candidate,
        edited in the same commit, prove each other and nothing else -- the
        mutant that sets BOTH to include 6 (``Pet``, which is not a
        ``CNetNPC`` descendant) was green.  So re-derive the set from the
        artifact itself, the way
        ``tests/test_actor_type_dispatch_static.py`` re-derives that same
        report's DISPATCH_COUNTS block.
        """
        report = (ROOT / name_colour_sweep.ACTOR_TYPE_REPORT).read_text(
            encoding="utf-8",
        )
        rows = [
            line for line in report.splitlines()
            if line.startswith("|") and "`NPCAttr`" in line
            and "0x0AD5" in line and "0x4697B0" in line
        ]
        self.assertEqual(
            len(rows), 1,
            "the report's NPCAttr dispatch row is not exactly one line any "
            "more -- re-read it before trusting this test",
        )
        accepted = re.search(r"\(so ([0-9,\s]+)\)", rows[0])
        self.assertIsNotNone(
            accepted,
            "the NPCAttr row no longer spells which actor_types it accepts: "
            + rows[0],
        )
        from_report = frozenset(
            int(part) for part in accepted.group(1).replace(" ", "").split(",")
            if part
        )
        self.assertEqual(
            from_report, name_colour_sweep.NPC_ATTR_BINDING_ACTOR_TYPES,
        )

    def test_every_row_is_somewhere_a_tester_can_actually_read_it(self) -> None:
        """Three ways a row is unreadable, all measured against the same
        two frozen tables the module itself composes from.

        1. ON THE SPAWN POINT.  The anchor IS the spawn point
           (``_spawn_anchor`` reads V135_PLAYER_X/Y/Z), so an ordinal-0 row
           is inside the camera at the moment the tester is asked to read
           its nameplate.
        2. ON TOP OF A REAL NPC.  Port Royal's own placements carry real
           nameboards; a dummy standing next to one is a nameplate the
           tester can read the wrong way round, and RE-155's entire output
           is one colour per label -- a mis-read is indistinguishable from
           a result.  Measured against every row of
           ``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS``, not against the one
           placement somebody eyeballed.
        3. OFF THE PLAYER'S OWN PLANE.  A row displaced in Y or Z is
           "not on the anchor" and still unreadable -- pf-adversary's D-11
           mutant put every row 100,000 units in the air and the first
           draft of this test stayed green.
        """
        anchor = name_colour_sweep._spawn_anchor(self.legacy)
        real = [
            (float(p[2]), float(p[3]), float(p[4]), p[6])
            for p in self.legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
        ]
        self.assertTrue(real)
        floor = name_colour_sweep.ROW_CLEARANCE_FROM_REAL_NPCS
        for value in name_colour_sweep.KNOWN_SETS:
            rows = name_colour_sweep.sweep_actors(
                self.legacy, env={"PF_NAME_COLOUR_SWEEP": value},
            )
            self.assertTrue(rows, value)
            for row in rows:
                with self.subTest(set=value, label=row.label):
                    # (1) and (3): same plane as the player, not on top of
                    # the player.
                    self.assertNotEqual((row.x, row.y, row.z), anchor)
                    self.assertAlmostEqual(row.y, anchor[1])
                    self.assertAlmostEqual(row.z, anchor[2])
                    # (2): clear of every real nameboard in the scene.
                    for x, y, z, name in real:
                        gap = math.dist((row.x, row.y, row.z), (x, y, z))
                        self.assertGreaterEqual(
                            gap, floor,
                            "%s is %.1f units from the real %r -- closer "
                            "than the %.1f-unit clearance this sweep needs "
                            "to be readable" % (row.label, gap, name, floor),
                        )
            # The spacing the readability argument rests on is unchanged:
            # consecutive rows are still one step apart, and the nearest row
            # is one step off the anchor.
            xs = sorted(abs(row.x - anchor[0]) for row in rows)
            self.assertAlmostEqual(xs[0], 150.0)
            for near, far in zip(xs, xs[1:]):
                self.assertAlmostEqual(far - near, 150.0)


if __name__ == "__main__":
    unittest.main()
