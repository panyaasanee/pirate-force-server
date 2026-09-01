"""LANE-A: a click must repeat the census, not a shorter version of it.

The gait coverage row's accepted rule -- a field present only in the
bootstrap generation is what turned an observed walk into a run in V85 --
applies to every field the census sends, not only to gait.  Round `7ste68`
gave the ordinary census a mined level; it did not notice that two other
composers rebuild the same actors from scratch and had no level parameter at
all, so one click reverted the whole scene on the wire.  pf-adversary found
that in round `2p4n3h` by driving a real ``CHOOSE_NPC`` through the
dispatcher: census frame 108 actors carrying a level, click frame 108
carrying none.

This file is the regression that stops it coming back, and it walks EVERY
actor rather than one, because the failure was per-actor and round
`2p4n3h`'s own first single-actor check had passed straight through it.

What it cannot prove, and does not: that the owner sees a level on screen.
``GT-200`` is that ticket -- and this file is why its photographs can be
trusted, because before it a tester who clicked anyone was photographing a
reverted frame.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_bg0015_identity as bg0015_identity  # noqa: E402
from pirateforce_foundation import world_census_level as level_splice  # noqa: E402
from pirateforce_foundation import world_face_frame  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_port_royal_identity  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


class TheClickFrameRepeatsTheCensus(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_the_face_frames_hp_rule_is_still_the_census_rule(self) -> None:
        """``world_face_frame`` spells the census's HP rule out rather than
        importing it, so the two have to be held together somewhere."""
        self.assertEqual(world_face_frame.FACE_FRAME_MONSTER_INDEX,
                         world_population.SHIPPED_MONSTER_INDEX)
        self.assertEqual(world_face_frame.FACE_FRAME_DEFAULT_HP,
                         world_population.DEFAULT_HP)
        self.assertEqual(world_face_frame.FACE_FRAME_MONSTER_HP,
                         self.legacy.V117_P30_EXACT_HP)

    def _scene_1(self):
        legacy = self.legacy
        anchor = (legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                  legacy.V135_PLAYER_Z)
        placements = {p.placement_index: p
                      for p in world_population.census_order(legacy, anchor)}
        generation = world_population.build_world_population(
            legacy, anchor, len(placements),
            scene_id=world_population.SCENE_ID)
        return anchor, placements, tuple(generation.indices)

    def test_every_scene_1_click_body_is_the_census_body(self) -> None:
        legacy = self.legacy
        anchor, placements, indices = self._scene_1()
        pc, _frame = world_face_frame.build_face_state(
            legacy, indices, indices[0],
            player_x=anchor[0], player_y=anchor[1],
        )
        checked = 0
        for index in indices:
            resolved = world_port_royal_identity.resolve(
                placements[index].template_id)
            self.assertIsNotNone(resolved)
            hp = (
                legacy.V117_P30_EXACT_HP
                if index == world_population.SHIPPED_MONSTER_INDEX
                else world_population.DEFAULT_HP
            )
            body = level_splice.leveled_npc_attr(
                legacy,
                template_n_id=resolved.mobs_n_id,
                actor_identity=0x2000 + index + 1,
                scene_id=1,
                scene_sequence=0,
                visual_preset=resolved.outfit,
                current_hp=hp,
                max_hp=hp,
                basic_name=resolved.name,
                level=resolved.level,
            )
            self.assertIn(
                body, pc,
                "placement %d's click body is not the census body" % index)
            checked += 1
        self.assertEqual(checked, len(indices))
        # Not a vacuous loop: scene 1 assembles 108 of its 115 placements.
        self.assertGreater(checked, 100)

    def test_every_scene_1_click_body_carries_a_level_read_off_the_wire(
            self) -> None:
        """The same thing again from the other side -- read the level OUT of
        the click frame rather than comparing whole bodies, so a future
        change that kept the bytes equal by dropping the field from both
        sides still goes red here."""
        legacy = self.legacy
        anchor, placements, indices = self._scene_1()
        pc, _frame = world_face_frame.build_face_state(
            legacy, indices, indices[0],
            player_x=anchor[0], player_y=anchor[1],
        )
        attr_tag = legacy.u16tag(0x12, world_population.NPC_ATTR_ID)
        seen = set()
        for index in indices:
            resolved = world_port_royal_identity.resolve(
                placements[index].template_id)
            actor_identity = 0x2000 + index + 1
            marker = (
                attr_tag
                + legacy.u8tag(0x0B, 1)
                + legacy.qwordtag(0x32, actor_identity)
            )
            # Uniqueness before value: reading the WRONG actor's body still
            # compares equal wherever the roster shares a level, and most of
            # scene 1 is level 10.
            self.assertEqual(pc.count(marker), 1)
            at = pc.index(marker) + len(attr_tag)
            level = level_splice.read_level(legacy, pc[at:], actor_identity)
            self.assertEqual(level, resolved.level)
            seen.add(level)
        self.assertNotIn(None, seen)
        self.assertGreater(len(seen), 1)


class TheScene14ClickResponderRepeatsItsCensus(unittest.TestCase):
    """The other composer with the same defect, and the one that can run.

    Unlike scene 1's ``lane_a_choose_npc_scene1`` (``production_allowed =
    False``, which the loader announces on import), scene 14's responder is
    production-allowed, so its civilians were being reverted on a real
    click.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_the_responder_is_the_one_that_can_actually_run(self) -> None:
        from pirateforce_foundation.lane_hooks import (
            lane_a_choose_npc_scene14 as responder,
        )
        self.assertTrue(responder.production_allowed)

    def test_every_civilian_click_body_carries_its_mined_level(self) -> None:
        from pirateforce_foundation.lane_hooks import (
            lane_a_choose_npc_scene14 as responder,
        )
        from pirateforce_foundation import world_population_bg0015 as census

        legacy = self.legacy
        placements = list(bg0015_identity.shippable_placements())
        indices = tuple(p.placement_index for p in placements)
        by_index = {p.placement_index: p for p in placements}
        answer = responder.respond(
            legacy=legacy,
            chosen_identities=(by_index[indices[0]].actor_identity,),
            population_indices=indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
            scene_id=census.SCENE_N_ID,
        )
        self.assertIsNotNone(answer)
        attr_tag = legacy.u16tag(0x12, census.NPC_ATTR_ID)
        levels = set()
        for index in indices:
            placement = by_index[index]
            marker = (
                attr_tag
                + legacy.u8tag(0x0B, 1)
                + legacy.qwordtag(0x32, placement.actor_identity)
            )
            if answer.pc.count(marker) != 1:
                continue
            at = answer.pc.index(marker) + len(attr_tag)
            level = level_splice.read_level(
                legacy, answer.pc[at:], placement.actor_identity)
            self.assertEqual(level, placement.identity.level)
            levels.add(level)
        self.assertTrue(levels)
        self.assertNotIn(None, levels)


if __name__ == "__main__":
    unittest.main()
