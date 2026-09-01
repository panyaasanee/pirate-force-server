"""LANE-A: the walk-speed bit that gates the client's quest-icon board.

The wire/DB half of the two-layer evidence rule for the one input on the
quest-mark skip clause that this server owns.  What this file proves without
a client: the frozen serializer sends no walk speed unless asked, every one
of the thirteen live census sources now asks, the value asked for is the
shipped ``MOBS.n_SPEED_WALK`` for the row the actor already is, the field is
read back byte-identically off each scene's own ``generation.pc``, and the
level splice and the gait field coexist in one body without either moving
the other.

What it cannot prove, and does not claim: that a quest mark appears over
anyone's head.  Three of the four clauses in the skip condition are the
client's (board pointer at ``+0x360``, cached selector at ``+0x364``, the
quest predicates), the whole selector table is ``source=IMAGE`` with no
client-observable row behind it, and Codex's own nonclaim says the on-screen
presentation is a different evidence layer.  ``GT-202`` is that ticket.
"""
from __future__ import annotations

import importlib
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import scene2_prison_exile_tables  # noqa: E402
from pirateforce_foundation import world_bg0006_identity as identity  # noqa: E402
from pirateforce_foundation import world_census_gait as gait  # noqa: E402
from pirateforce_foundation import world_census_level as level_splice  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_population_bg0002  # noqa: E402
from pirateforce_foundation import world_port_royal_identity  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

SCENE_ID = 6
SCENE_SEQUENCE = 0

# The scenes whose composer is the shared ``SceneIdentity`` shape.  bg0001
# and bg0002 are wired too and get their own tests: bg0001 resolves through
# ``world_port_royal_identity`` and takes its HP from a per-placement rule,
# and bg0002 passes its own independently mined ``speed_walk`` column.
WIRED_SCENES = (
    "bg0003", "bg0004", "bg0005", "bg0006", "bg0007", "bg0008",
    "bg0009", "bg0010", "bg0011", "bg0015", "bg4001",
)

# Every live census source keyed by the name ``world_scene_travel
# .CENSUS_SOURCES`` gives it, mapped to the module that composes it -- the
# same two-directional pin ``test_world_census_level`` carries, for the same
# measured reason: a composer that is MISSING looks exactly like one nobody
# has built yet, so a glob over the wired files cannot see a new census
# source that was never wired.
CENSUS_SOURCE_COMPOSERS = {
    "bg0001_census": "world_population",
    "bg0002_roster": "world_population_bg0002",
    "bg0003_roster": "world_population_bg0003",
    "bg0004_roster": "world_population_bg0004",
    "bg0005_roster": "world_population_bg0005",
    "bg0006_roster": "world_population_bg0006",
    "bg0007_roster": "world_population_bg0007",
    "bg0008_roster": "world_population_bg0008",
    "bg0009_roster": "world_population_bg0009",
    "bg0010_roster": "world_population_bg0010",
    "bg0011_roster": "world_population_bg0011",
    "bg0015_roster": "world_population_bg0015",
    "bg4001_roster": "world_population_bg4001",
}


class CensusGaitTable(unittest.TestCase):
    """The mined crosswalk itself, before any byte is composed."""

    def test_the_table_covers_every_id_the_census_ships(self) -> None:
        """A census source shipping an unmined id must go red, not default.

        Walked from the identity tables rather than from the crosswalk, so
        the direction of this check is "does the data we ship resolve", not
        "does the table we wrote resolve".
        """
        missing = []
        for scene in WIRED_SCENES:
            module = importlib.import_module(
                "pirateforce_foundation.world_%s_identity" % scene)
            for row in module._RESOLVED_ROWS:
                n_id = module.SceneIdentity(*row).mobs_n_id
                if n_id not in gait.WALK_SPEED_BY_MOBS_N_ID:
                    missing.append((scene, n_id))
        for row in world_port_royal_identity._RESOLVED_ROWS:
            n_id = world_port_royal_identity.SceneIdentity(*row).mobs_n_id
            if n_id not in gait.WALK_SPEED_BY_MOBS_N_ID:
                missing.append(("bg0001", n_id))
        for placement in scene2_prison_exile_tables.load_known_placements():
            if placement.n_id not in gait.WALK_SPEED_BY_MOBS_N_ID:
                missing.append(("bg0002", placement.n_id))
        self.assertEqual(missing, [])

    def test_scene_2_mined_the_same_column_independently_and_agrees(
            self) -> None:
        """Two tables, mined at different times from the same shipped column.

        ``scene2_prison_exile_tables`` has carried a per-placement
        ``speed_walk`` since long before this crosswalk existed.  Holding
        them to each other is the only cross-check this round has that the
        transcription above is the shipped column and not a column next to
        it; a future disagreement goes red here instead of one table quietly
        winning at the call site.
        """
        checked = 0
        for placement in scene2_prison_exile_tables.load_known_placements():
            self.assertEqual(
                gait.walk_speed_for(placement.n_id), placement.speed_walk,
                "n_ID %d: crosswalk and scene 2's own column disagree"
                % placement.n_id)
            checked += 1
        self.assertEqual(checked, 97)

    def test_it_refuses_an_id_it_never_mined(self) -> None:
        unmined = max(gait.WALK_SPEED_BY_MOBS_N_ID) + 1
        with self.assertRaises(gait.CensusGaitError):
            gait.walk_speed_for(unmined)

    def test_it_refuses_a_non_int_id(self) -> None:
        with self.assertRaises(gait.CensusGaitError):
            gait.walk_speed_for("156")
        with self.assertRaises(gait.CensusGaitError):
            gait.walk_speed_for(True)

    def test_every_mined_value_is_inside_the_declared_domain(self) -> None:
        """The declared domain is the mined one, so it has to hold.

        Stated as a test because ``census_npc_attr`` refuses outside it: a
        transcription that put an HP or a level in this table would ship
        silently otherwise.
        """
        for n_id, speed in gait.WALK_SPEED_BY_MOBS_N_ID.items():
            self.assertIsInstance(speed, int)
            self.assertGreaterEqual(speed, gait.WALK_SPEED_MIN)
            self.assertLessEqual(speed, gait.WALK_SPEED_MAX, "n_ID %d" % n_id)

    def test_the_table_is_not_one_constant(self) -> None:
        """A crosswalk that answered one number for everyone would pass every
        read-back test in this file while carrying no information."""
        self.assertGreater(len(set(gait.WALK_SPEED_BY_MOBS_N_ID.values())), 1)


class CensusGaitBody(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(LEGACY_PATH)
        cls.placement = next(
            p for p in identity.shippable_placements() if p.display_name)

    def _composed(self, **overrides):
        placement = self.placement
        kwargs = dict(
            template_n_id=placement.n_id,
            actor_identity=placement.actor_identity,
            scene_id=SCENE_ID,
            scene_sequence=SCENE_SEQUENCE,
            visual_preset=placement.visual_preset,
            current_hp=placement.max_hp,
            max_hp=placement.max_hp,
            basic_name=placement.display_name,
            level=placement.identity.level,
        )
        kwargs.update(overrides)
        return gait.census_npc_attr(self.legacy, **kwargs)

    def test_the_frozen_body_carries_no_walk_speed_at_all(self) -> None:
        """The gate, stated as a test: this is the shape of every census
        body the owner has ever been sent, and the CNetNPC setter skips the
        quest-icon board for it.

        A tripwire as much as a measurement -- if this ever stops returning
        ``None`` because someone changed the default, the round that did it
        should have deleted this module instead.
        """
        placement = self.placement
        body = self.legacy.make_npc_attr(
            placement.n_id, placement.actor_identity, SCENE_ID,
            SCENE_SEQUENCE, placement.visual_preset,
            current_hp=placement.max_hp, max_hp=placement.max_hp,
            basic_name=placement.display_name)
        self.assertIsNone(gait.read_walk_speed(
            self.legacy, body, placement.actor_identity))
        self.assertFalse(gait.quest_board_gate_is_open(
            self.legacy, body, placement.actor_identity))

    def test_the_composed_body_opens_the_gate(self) -> None:
        body = self._composed()
        self.assertTrue(gait.quest_board_gate_is_open(
            self.legacy, body, self.placement.actor_identity))
        mask_at = level_splice.basic_mask_offset(
            self.legacy, body, self.placement.actor_identity)
        mask = int.from_bytes(body[mask_at:mask_at + 2], "little")
        self.assertTrue(mask & 0x0040)

    def test_the_walk_speed_tag_is_the_one_the_frozen_writer_uses(
            self) -> None:
        """Pinned as a literal and read off the wire against a literal.

        ``read_walk_speed`` alone cannot prove the tag: it reads the same
        constant the writer wrote, so a module that agreed with itself on
        the wrong tag would stay green.  0x2A is pinned here from the frozen
        ``f32tag`` and from ``PF_ATTR_FIELD_SEMANTICS.tsv``'s BasicAttr@0x54
        row, both independent of this module's own constant.
        """
        self.assertEqual(gait.WALK_SPEED_TAG, 0x2A)
        body = self._composed()
        speed = gait.walk_speed_for(self.placement.n_id)
        self.assertIn(b"\x2a" + struct.pack("<f", float(speed)), body)

    def test_the_gait_field_adds_exactly_five_bytes_and_one_mask_bit(
            self) -> None:
        placement = self.placement
        without = level_splice.leveled_npc_attr(
            self.legacy,
            template_n_id=placement.n_id,
            actor_identity=placement.actor_identity,
            scene_id=SCENE_ID,
            scene_sequence=SCENE_SEQUENCE,
            visual_preset=placement.visual_preset,
            current_hp=placement.max_hp,
            max_hp=placement.max_hp,
            basic_name=placement.display_name,
            level=placement.identity.level,
        )
        with_gait = self._composed()
        self.assertEqual(len(with_gait), len(without) + 1 + 4)
        mask_at = level_splice.basic_mask_offset(
            self.legacy, without, placement.actor_identity)
        before = int.from_bytes(without[mask_at:mask_at + 2], "little")
        after = int.from_bytes(with_gait[mask_at:mask_at + 2], "little")
        self.assertEqual(after ^ before, gait.BASIC_BIT_WALK_SPEED)

    def test_the_level_splice_still_reads_back_beside_the_gait_field(
            self) -> None:
        """The two fields sit on opposite sides of the HP pair.  Read both
        out of the same body, so a future change that moved either one is
        caught here rather than in whichever scene ships first."""
        body = self._composed()
        self.assertEqual(
            level_splice.read_level(
                self.legacy, body, self.placement.actor_identity),
            self.placement.identity.level)
        self.assertEqual(
            gait.read_walk_speed(
                self.legacy, body, self.placement.actor_identity),
            float(gait.walk_speed_for(self.placement.n_id)))

    def test_a_nameless_body_reads_back_too(self) -> None:
        """25 of bg0004's 109 shipped placements are nameless, and the name
        field is the one variable-length thing this reader walks past."""
        body = self._composed(basic_name="")
        self.assertEqual(
            gait.read_walk_speed(
                self.legacy, body, self.placement.actor_identity),
            float(gait.walk_speed_for(self.placement.n_id)))

    def test_it_refuses_a_walk_speed_outside_the_mined_domain(self) -> None:
        with self.assertRaises(gait.CensusGaitError):
            self._composed(walk_speed=gait.WALK_SPEED_MAX + 1)
        with self.assertRaises(gait.CensusGaitError):
            self._composed(walk_speed=-1)

    def test_it_refuses_a_walk_speed_that_is_not_a_plain_int(self) -> None:
        """A float slipping through would still serialize, and a caller
        handing this ``placement.max_hp`` by mistake is the failure the
        domain check exists for -- but only if the type check fires first."""
        with self.assertRaises(gait.CensusGaitError):
            self._composed(walk_speed=100.0)
        with self.assertRaises(gait.CensusGaitError):
            self._composed(walk_speed="100")

    def test_the_reader_refuses_a_body_whose_gait_position_moved(self) -> None:
        """Independent of the writer: flip the mask's walk-speed bit on a
        body that has no such field, and the reader must refuse rather than
        return whatever four bytes happen to sit there."""
        placement = self.placement
        body = bytearray(level_splice.leveled_npc_attr(
            self.legacy,
            template_n_id=placement.n_id,
            actor_identity=placement.actor_identity,
            scene_id=SCENE_ID,
            scene_sequence=SCENE_SEQUENCE,
            visual_preset=placement.visual_preset,
            current_hp=placement.max_hp,
            max_hp=placement.max_hp,
            basic_name=placement.display_name,
            level=placement.identity.level,
        ))
        mask_at = level_splice.basic_mask_offset(
            self.legacy, bytes(body), placement.actor_identity)
        mask = int.from_bytes(body[mask_at:mask_at + 2], "little")
        body[mask_at:mask_at + 2] = int(
            mask | gait.BASIC_BIT_WALK_SPEED).to_bytes(2, "little")
        with self.assertRaises(gait.CensusGaitError):
            gait.read_walk_speed(
                self.legacy, bytes(body), placement.actor_identity)


class CensusGaitOnTheWire(unittest.TestCase):
    """Read off each scene's own ``generation.pc``, not off a composer call."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_every_wired_scene_puts_its_mined_gait_on_the_wire(self) -> None:
        for scene in WIRED_SCENES:
            module = importlib.import_module(
                "pirateforce_foundation.world_population_%s" % scene)
            scene_identity = importlib.import_module(
                "pirateforce_foundation.world_%s_identity" % scene)
            build = getattr(module, "build_%s_population" % scene)
            placements = list(scene_identity.shippable_placements())
            first = placements[0]
            generation = build(
                self.legacy, (first.x, first.y, first.z),
                scene_id=module.SCENE_N_ID)
            attr_tag = self.legacy.u16tag(0x12, module.NPC_ATTR_ID)
            by_index = {p.placement_index: p for p in placements}
            with self.subTest(scene=scene):
                seen = set()
                for index in generation.placement_indices:
                    placement = by_index[index]
                    marker = (
                        attr_tag
                        + self.legacy.u8tag(0x0B, 1)
                        + self.legacy.qwordtag(0x32, placement.actor_identity)
                    )
                    # Uniqueness before value, for the same measured reason
                    # the level test carries it: reading the WRONG actor's
                    # body still compares equal wherever a roster shares a
                    # walk speed, and most of these rosters share one.
                    self.assertEqual(generation.pc.count(marker), 1)
                    at = generation.pc.index(marker) + len(attr_tag)
                    speed = gait.read_walk_speed(
                        self.legacy, generation.pc[at:],
                        placement.actor_identity)
                    self.assertEqual(
                        speed, float(gait.walk_speed_for(placement.n_id)))
                    seen.add(speed)
                self.assertNotIn(None, seen)

    def test_bg0001_puts_its_mined_gait_on_the_wire(self) -> None:
        """Port Royal: the scene every login lands in, and the one whose 91
        quest-carrying rows are the reason this round exists."""
        census = world_population
        anchor = (self.legacy.V135_PLAYER_X, self.legacy.V135_PLAYER_Y,
                  self.legacy.V135_PLAYER_Z)
        placements = {p.placement_index: p
                      for p in census.census_order(self.legacy, anchor)}
        generation = census.build_world_population(
            self.legacy, anchor, len(placements), scene_id=census.SCENE_ID)
        attr_tag = self.legacy.u16tag(0x12, census.NPC_ATTR_ID)
        seen = set()
        for index in generation.indices:
            placement = placements[index]
            resolved = world_port_royal_identity.resolve(placement.template_id)
            marker = (
                attr_tag
                + self.legacy.u8tag(0x0B, 1)
                + self.legacy.qwordtag(0x32, placement.actor_identity)
            )
            self.assertEqual(generation.pc.count(marker), 1)
            at = generation.pc.index(marker) + len(attr_tag)
            speed = gait.read_walk_speed(
                self.legacy, generation.pc[at:], placement.actor_identity)
            self.assertEqual(
                speed, float(gait.walk_speed_for(resolved.mobs_n_id)))
            seen.add(speed)
        self.assertNotIn(None, seen)
        self.assertGreater(len(seen), 1)

    def test_bg0002_puts_its_own_mined_gait_on_the_wire(self) -> None:
        """Scene 2 passes its own column rather than the crosswalk, so what
        reaches the wire has to be checked against ITS table."""
        census = world_population_bg0002
        placements = list(census.census_order((0.0, 0.0, 0.0)))
        first = placements[0]
        generation = census.build_bg0002_population(
            self.legacy, (first.x, first.y, first.z),
            scene_id=census.SCENE2_N_ID)
        attr_tag = self.legacy.u16tag(0x12, census.NPC_ATTR_ID)
        by_index = {p.placement_index: p for p in placements}
        seen = set()
        for index in generation.placement_indices:
            placement = by_index[index]
            marker = (
                attr_tag
                + self.legacy.u8tag(0x0B, 1)
                + self.legacy.qwordtag(0x32, placement.actor_identity)
            )
            self.assertEqual(generation.pc.count(marker), 1)
            at = generation.pc.index(marker) + len(attr_tag)
            speed = gait.read_walk_speed(
                self.legacy, generation.pc[at:], placement.actor_identity)
            self.assertEqual(speed, float(placement.speed_walk))
            seen.add(speed)
        self.assertTrue(seen)
        self.assertNotIn(None, seen)


class ClickRecomposeMatchesTheArrivalCensus(unittest.TestCase):
    """The "every generation" rule, as a test rather than as a promise.

    The gait coverage row's accepted rule comes from the V85 regression: a
    walk speed present only in the bootstrap generation turned an observed
    walk into a run.  The two lane_hooks click responders rebuild the WHOLE
    roster whenever a player clicks anyone, and until round `2p4n3h` they
    did it with a plain ``legacy.make_npc_attr`` -- which silently dropped
    BOTH the level and (once the census had it) the gait for every actor on
    screen.  This walks every actor, not one, because the failure was
    per-actor and a single-actor check would have missed it before.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_scene_1_click_answer_repeats_the_census_bodies_byte_for_byte(
            self) -> None:
        from pirateforce_foundation.lane_hooks import (
            lane_a_choose_npc_scene1 as responder,
        )

        legacy = self.legacy
        anchor = (legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                  legacy.V135_PLAYER_Z)
        placements = {p.placement_index: p
                      for p in world_population.census_order(legacy, anchor)}
        generation = world_population.build_world_population(
            legacy, anchor, len(placements),
            scene_id=world_population.SCENE_ID)
        indices = tuple(generation.indices)
        answer = responder.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + indices[0] + 1,),
            population_indices=indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
        )
        self.assertIsNotNone(answer)
        checked = 0
        for index in indices:
            placement = placements[index]
            resolved = world_port_royal_identity.resolve(
                placement.template_id)
            self.assertIsNotNone(resolved)
            hp = (
                legacy.V117_P30_EXACT_HP
                if index == world_population.SHIPPED_MONSTER_INDEX
                else world_population.DEFAULT_HP
            )
            body = gait.census_npc_attr(
                legacy,
                template_n_id=resolved.mobs_n_id,
                actor_identity=placement.actor_identity,
                scene_id=world_population.SCENE_ID,
                scene_sequence=0,
                visual_preset=resolved.outfit,
                current_hp=hp,
                max_hp=hp,
                basic_name=resolved.name,
                level=resolved.level,
            )
            self.assertIn(
                body, answer.pc,
                "placement %d's click body is not the census body" % index)
            checked += 1
        # Not a vacuous loop: the scene assembles 108 of its 115 placements.
        self.assertEqual(checked, len(indices))
        self.assertGreater(checked, 100)


class CensusGaitWiring(unittest.TestCase):
    def test_every_live_census_source_either_sends_a_gait_or_says_why(
            self) -> None:
        live = set(world_scene_travel.CENSUS_SOURCES.values())
        self.assertEqual(
            live - set(CENSUS_SOURCE_COMPOSERS),
            set(),
            "a live census source has no composer named here: add it (and "
            "wire it), or record it in "
            "CENSUS_SOURCES_WITHOUT_A_MINED_WALK_SPEED with a reason")
        for source, module_name in CENSUS_SOURCE_COMPOSERS.items():
            if source not in live:
                continue
            if source in gait.CENSUS_SOURCES_WITHOUT_A_MINED_WALK_SPEED:
                continue
            text = (ROOT / "src" / "pirateforce_foundation"
                    / (module_name + ".py")).read_text(encoding="utf-8")
            self.assertIn(
                "world_census_gait.census_npc_attr(", text,
                "%s composes a live census and neither sends a walk speed "
                "nor says why" % module_name)

    def test_no_source_is_recorded_as_unmined_today(self) -> None:
        """Empty on purpose.  A source that lands here later needs its reason
        written beside it, not merely to be absent from the map above."""
        self.assertEqual(gait.CENSUS_SOURCES_WITHOUT_A_MINED_WALK_SPEED, ())


if __name__ == "__main__":
    unittest.main()
