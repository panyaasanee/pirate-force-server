"""LANE-A: Prison Exile Island's 97 people answer a click.

WHAT THIS FILE MEASURES, and at which layer.

  * THE MEMBERSHIP IS NOT THIS FILE'S OPINION.  ``lane_a_choose_npc_scene2``
    derives the set it re-sends from ``scene2_prison_exile_tables`` because
    scene 2 never arms ``population_indices`` (``runtime.py``'s bg0002 arm
    says so in its own words).  ``TheMembershipIsTheCensusThatShippedTests``
    drives the REAL arrival builder and asserts the two sets are identical,
    so the day the census composes a different set this file goes red
    instead of the responder quietly re-sending a roster nobody was sent.

  * THE ANSWER IS READ OUT OF THE COMPOSED FRAME, never compared against
    the constant that composed it.  Round `gwwpmr`'s most expensive lesson
    (three module mutants survived 7,549 tests because no assertion read
    the frame) is the reason every body assertion below is a
    ``assertIn(<bytes>, frame)`` against bytes built by a DIFFERENT encoder
    call than the one under test, plus two variation tests -- click another
    actor, move the player -- that no frozen-heading or wrong-actor mutant
    can pass.

  * THE CLAIM ON THE VITAL FAMILY IS RE-CHECKED, because ``runtime.py``'s
    guard tells a lane to: "a future scene whose players use melee/skill
    targeting on the SAME connection a responder claims must re-check this
    before flipping its flag."  Scene 2 is where LANE-B's monsters live.
    ``OnTheRealDispatcherTests`` drives a real TARGET_VITAL on scene 2 and
    pins that v141's ``p30_action_target_armed`` could not have armed there
    anyway (``population_indices`` is ``None`` on this scene, which the
    same test asserts rather than assumes).

WHAT THIS FILE DOES NOT MEASURE.  Nobody has seen any of this on a screen.
``GT-214`` is the attended ticket and no assertion here stands in for it.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import (  # noqa: E402
    scene2_prison_exile_tables as tables,
)
from pirateforce_foundation import world_census_level  # noqa: E402
from pirateforce_foundation import world_population_bg0002  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_choose_npc_scene2 as responder_mod,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
PRISON_EXILE = 2
ROSTER_COUNT = 97
HOSTILE_COUNT = 12
QUALIFIED_MODULE = (
    "pirateforce_foundation.lane_hooks.lane_a_choose_npc_scene2"
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _target_pos_pc(legacy, xyz, heading=0.0, moving=0, derived=0):
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
        + legacy.u8tag(0x0B, 0)
        + b"".join(legacy.f32tag(value) for value in (*xyz, heading))
        + legacy.u8tag(0x0B, moving)
        + legacy.u8tag(0x0B, derived)
    )


def _target_vital_pc(legacy, actor_id, kind=0):
    """One bare TARGET_VITAL frame: no ChooseNPC record attached, so the
    only thing at stake is v141's own arming side effect."""
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, legacy.TARGET_VITAL)
        + legacy.u8tag(0x0B, 0)
        + legacy.qwordtag(0x32, actor_id)
        + legacy.u8tag(0x08, kind)
    )


def _choose_npc_pc(legacy, *actor_ids):
    body = b"".join(
        legacy.u16tag(0x12, legacy.CHOOSE_NPC)
        + legacy.u8tag(0x0B, 0)
        + legacy.qwordtag(0x32, actor_id)
        for actor_id in actor_ids
    )
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, len(actor_ids))
        + body
    )


def _shut_registry(work: Path):
    """A loaded registry with scene 2's door shut, temp file only."""
    raw = json.loads(
        world_scene_travel.REGISTRY_PATH.read_text(encoding="ascii"))
    for row in raw["destinations"]:
        if row["n_id"] == PRISON_EXILE:
            row["login_entry_allowed"] = False
    path = work / "registry_scene_2_shut.json"
    path.write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="ascii")
    return world_scene_travel.load_scene_registry(path)


def _hostile_by_index():
    return {
        mob.placement_index: mob
        for mob in field_mobs.roster_for_scene_id(PRISON_EXILE)
    }


class TheModuleGateIsOpenTests(unittest.TestCase):

    def test_the_module_declares_production_allowed_true(self):
        self.assertIs(responder_mod.production_allowed, True)

    def test_the_responder_is_registered_for_scene_2_at_discovery(self):
        registered = lane_hooks.scene_choose_npc_responder(PRISON_EXILE)
        self.assertIsNotNone(
            registered, "scene 2 has no ChooseNPC responder at all")
        self.assertEqual(registered.module, QUALIFIED_MODULE)
        self.assertTrue(
            lane_hooks.module_production_allowed(registered.module))


class TheMembershipIsTheCensusThatShippedTests(unittest.TestCase):
    """The responder re-sends the set the ARRIVAL census sent, measured
    against the real builder rather than against this file's own copy.

    Mutate ``_placements_by_index`` to drop or add a row and this class is
    the one that catches it, because it never reads that helper: it reads
    ``world_population_bg0002.build_bg0002_population`` -- the function
    ``runtime.py``'s bg0002 arm calls -- with the same
    ``COUNT_SOURCE_FULL_ROSTER`` that arm passes.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()

    def test_the_arrival_census_ships_the_whole_known_table(self):
        spawn = world_scene_travel.spawn_position(
            world_scene_travel.destination(PRISON_EXILE))
        generation = world_population_bg0002.build_bg0002_population(
            self.legacy, spawn, scene_id=PRISON_EXILE,
            count_source=world_population_bg0002.COUNT_SOURCE_FULL_ROSTER,
        )
        self.assertEqual(generation.actor_count, ROSTER_COUNT)
        self.assertEqual(
            set(generation.actor_identities),
            {p.actor_identity for p in tables.load_known_placements()},
            "the arrival census and this responder disagree about who is "
            "standing on scene 2",
        )

    def test_the_responder_answers_for_exactly_that_set(self):
        legacy = self.legacy
        answer = _answer(legacy, clicked_index=0)
        self.assertIn(f"visible={ROSTER_COUNT}", answer.console_lines[0])

    def test_every_hostile_row_is_one_of_the_ninety_seven(self):
        known = {p.placement_index for p in tables.load_known_placements()}
        hostile = set(_hostile_by_index())
        self.assertEqual(len(hostile), HOSTILE_COUNT)
        self.assertTrue(
            hostile <= known,
            "a monster stands on scene 2 at a placement the civilian table "
            "does not hold: %r" % (sorted(hostile - known),),
        )


def _placements_by_index():
    return {p.placement_index: p for p in tables.load_known_placements()}


def _placement(index):
    return _placements_by_index()[index]


def _answer(legacy, clicked_index, player_xy=(100.0, 200.0), ledger=None):
    placement = _placement(clicked_index)
    with contextlib.redirect_stderr(io.StringIO()):
        response = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(placement.actor_identity,),
            population_indices=None,
            last_target_pos=(player_xy[0], player_xy[1], 0.0, 0.0),
            scene_id=PRISON_EXILE,
            mob_combat_ledger=ledger,
        )
    return response


class TheAnswerCarriesTheWholeIslandTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()
        cls.civilian_index = next(
            index for index in sorted(
                p.placement_index for p in tables.load_known_placements())
            if index not in _hostile_by_index()
        )

    def test_a_click_is_answered_with_a_named_label_and_real_bytes(self):
        response = _answer(self.legacy, self.civilian_index)
        self.assertIsNotNone(response)
        self.assertEqual(
            response.label,
            f"LANE_A_CHOOSE_NPC_SCENE{PRISON_EXILE}_FACE_P"
            f"{self.civilian_index}",
        )
        self.assertTrue(response.pc)
        self.assertTrue(response.frame)
        self.assertEqual(response.delay, 0.0)

    def test_the_console_line_names_the_count_the_hostiles_and_the_hp_source(
        self,
    ):
        response = _answer(self.legacy, self.civilian_index)
        line = response.console_lines[0]
        self.assertIn(f"placement={self.civilian_index}", line)
        self.assertIn(f"visible={ROSTER_COUNT}", line)
        self.assertIn(f"hostile={HOSTILE_COUNT}", line)
        # The gap this lane owes the tester in writing: with no ledger the
        # 12 hostile bodies carry their table ceiling.
        self.assertIn("hp=ceiling", line)

    def test_the_turn_to_face_is_in_the_frame_and_not_only_in_the_label(self):
        """Reads the COMPOSED frame, three ways, so no mutant of the face
        branch survives: deleting the movement attr, sending it for the
        wrong actor, and freezing the heading each fail one of these.
        """
        legacy = self.legacy
        placement = _placement(self.civilian_index)
        response = _answer(legacy, self.civilian_index)
        heading = legacy._heading_to_player(
            placement.x, placement.y, 100.0, 200.0)
        expected = legacy.make_remote_movement_attr(
            placement.actor_identity, placement.x, placement.y, placement.z,
            heading, mask=0x03,
        )
        self.assertIn(
            expected, response.frame,
            "the clicked actor's turn-to-face is not in the frame",
        )

        # A DIFFERENT actor clicked composes a DIFFERENT frame -- so the
        # attr really follows the click rather than riding a fixed row.
        other_index = next(
            index for index in sorted(
                p.placement_index for p in tables.load_known_placements())
            if index != self.civilian_index
            and index not in _hostile_by_index()
        )
        other = _answer(legacy, other_index)
        self.assertNotEqual(response.frame, other.frame)

        # AND THE HEADING IS COMPUTED FROM THE PLAYER: the same click from
        # a different standing position composes different bytes.  A frozen
        # heading passes both assertions above and fails this one.
        moved = _answer(
            legacy, self.civilian_index, player_xy=(-9000.0, 9000.0))
        self.assertNotEqual(response.frame, moved.frame)

    def test_a_click_leaves_the_hostile_splice_alone(self):
        """The scene-14 defect (round R274) in this scene's numbers: every
        one of the 12 hostile bodies must be in the answer as HOSTILE, and
        the civilian body for those same placements must not be.

        THE AUTHORITY IS THE ARRIVAL SPLICE ITSELF, not a second call with
        this test's own arguments.  ``mob_death.full_roster_override`` is
        the function ``runtime.py``'s bg0002 arm applies to the census, so
        the body it produces is literally what the client is holding.  An
        earlier draft of this test built the expected body with
        ``scene_id=2`` -- and passed, against a responder that also used 2,
        while the census had sent 1.  That is the constant-pinned-against-
        itself shape round `gwwpmr` paid for; asking the real override
        cannot agree with the responder by construction.
        """
        legacy = self.legacy
        response = _answer(legacy, self.civilian_index)
        override = mob_death.full_roster_override(
            legacy, field_mobs.roster_for_scene_id(PRISON_EXILE),
            mob_death.DeathRegister(), ledger=None,
        )
        self.assertEqual(len(override), HOSTILE_COUNT)
        for index, mob in sorted(_hostile_by_index().items()):
            with self.subTest(placement=index):
                arrival_entry = override[mob.actor_identity]
                hostile_body = field_mobs.hostile_npc_attr(
                    legacy, mob, current_hp=mob.max_hp,
                    scene_id=field_mobs.SCENE_ID,
                    scene_sequence=field_mobs.SCENE_SEQUENCE,
                )
                self.assertIn(
                    hostile_body, arrival_entry,
                    "this test's idea of a hostile body is not the one the "
                    "arrival splice ships for placement %d" % index,
                )
                self.assertIn(
                    hostile_body, response.frame,
                    "placement %d went out civilian -- the click reverted "
                    "the arrival census's hostile splice" % index,
                )
                placement = _placement(index)
                civilian_body = world_census_level.leveled_npc_attr(
                    legacy,
                    template_n_id=placement.n_id,
                    actor_identity=placement.actor_identity,
                    scene_id=PRISON_EXILE,
                    scene_sequence=0,
                    visual_preset=placement.visual_preset,
                    current_hp=placement.max_hp,
                    max_hp=placement.max_hp,
                    basic_name=placement.display_name,
                    level=placement.level,
                )
                self.assertNotIn(civilian_body, response.frame)

    def test_every_entry_is_addressed_to_its_own_actor(self):
        """pf-adversary D1, the mutant that survived the whole suite.

        Every other body assertion in this file reads a PAYLOAD out of the
        frame -- and a payload carries its own identity inside itself, so
        addressing all 97 entries to the clicked actor left 7,626 tests
        green while 96 bodies rode under one identity (and, under this
        module's own RE-092 reading, vanished from the screen).  This test
        reads the ENTRY, header included: actor type, identity, and the
        attribute tag the body is carried under -- the three fields
        ``make_remote_actor_entry`` writes and nothing else checked.
        """
        legacy = self.legacy
        response = _answer(legacy, self.civilian_index)
        hostile_by_idx = _hostile_by_index()
        checked = 0
        for index, placement in sorted(_placements_by_index().items()):
            if index == self.civilian_index:
                continue        # the clicked entry carries a second attr
            mob = hostile_by_idx.get(index)
            if mob is not None:
                body = field_mobs.hostile_npc_attr(
                    legacy, mob, current_hp=mob.max_hp,
                    scene_id=field_mobs.SCENE_ID,
                    scene_sequence=field_mobs.SCENE_SEQUENCE,
                )
            else:
                body = world_census_level.leveled_npc_attr(
                    legacy,
                    template_n_id=placement.n_id,
                    actor_identity=placement.actor_identity,
                    scene_id=PRISON_EXILE,
                    scene_sequence=0,
                    visual_preset=placement.visual_preset,
                    current_hp=placement.max_hp,
                    max_hp=placement.max_hp,
                    basic_name=placement.display_name,
                    level=placement.level,
                )
            entry = legacy.make_remote_actor_entry(
                4, placement.actor_identity, [(legacy.NPC_ATTR, body)],
            )
            self.assertIn(
                entry, response.frame,
                "placement %d's entry is not addressed to placement %d, or "
                "not an NPCAttr, or not the NPC actor type" % (index, index),
            )
            checked += 1
        self.assertEqual(
            checked, ROSTER_COUNT - 1,
            "the loop checked %d entries, not the 96 unclicked ones"
            % checked,
        )

    def test_the_clicked_entry_is_the_only_one_carrying_a_movement_attr(self):
        """The other half of D1/D4: the clicked actor's entry is a real
        entry too, header and both attrs, and exactly one exists."""
        legacy = self.legacy
        placement = _placement(self.civilian_index)
        response = _answer(legacy, self.civilian_index)
        body = world_census_level.leveled_npc_attr(
            legacy,
            template_n_id=placement.n_id,
            actor_identity=placement.actor_identity,
            scene_id=PRISON_EXILE,
            scene_sequence=0,
            visual_preset=placement.visual_preset,
            current_hp=placement.max_hp,
            max_hp=placement.max_hp,
            basic_name=placement.display_name,
            level=placement.level,
        )
        heading = legacy._heading_to_player(
            placement.x, placement.y, 100.0, 200.0)
        movement = legacy.make_remote_movement_attr(
            placement.actor_identity, placement.x, placement.y, placement.z,
            heading, mask=0x03,
        )
        entry = legacy.make_remote_actor_entry(
            4, placement.actor_identity,
            [(legacy.NPC_ATTR, body), (legacy.MOVEMENT_ATTR, movement)],
        )
        self.assertIn(entry, response.frame)
        # And no other actor got one: every movement attr in the frame is
        # this one's bytes.
        self.assertEqual(
            response.frame.count(movement), 1,
            "the clicked actor's movement attr appears more than once",
        )

    def test_the_entries_are_in_placement_index_order(self):
        """pf-adversary D5, pinned rather than left to drift.

        The ARRIVAL census orders its 97 nearest-first from the anchor;
        this answer orders them by placement index.  The sets are equal
        (asserted elsewhere); the ORDER is a third thing this responder
        does differently, and no evidence says the client cares.  Pinned so
        the difference is a decision on the record instead of an accident:
        a round that finds out order matters will fail here and read this.
        """
        legacy = self.legacy
        response = _answer(legacy, self.civilian_index)
        positions = []
        for index, placement in sorted(_placements_by_index().items()):
            mob = _hostile_by_index().get(index)
            if mob is not None:
                body = field_mobs.hostile_npc_attr(
                    legacy, mob, current_hp=mob.max_hp,
                    scene_id=field_mobs.SCENE_ID,
                    scene_sequence=field_mobs.SCENE_SEQUENCE,
                )
            else:
                body = world_census_level.leveled_npc_attr(
                    legacy,
                    template_n_id=placement.n_id,
                    actor_identity=placement.actor_identity,
                    scene_id=PRISON_EXILE,
                    scene_sequence=0,
                    visual_preset=placement.visual_preset,
                    current_hp=placement.max_hp,
                    max_hp=placement.max_hp,
                    basic_name=placement.display_name,
                    level=placement.level,
                )
            positions.append(response.frame.index(body))
        self.assertEqual(
            positions, sorted(positions),
            "the entries are no longer in placement-index order",
        )

    def test_the_clickable_totals_this_lane_reports(self):
        """pf-adversary D12: 692 was pinned, 81 and 870 were not."""
        from pirateforce_foundation import world_bg0015_identity
        from pirateforce_foundation.lane_hooks import (
            lane_a_choose_npc_roster_scenes as roster,
        )
        roster_total = sum(
            len(roster._IDENTITY_OF_SCENE[scene].shippable_placements())
            for scene in roster.scenes_this_lane_answers_for()
        )
        volcano = len(world_bg0015_identity.shippable_placements())
        # 692 IS THE ISLANDS, and round `4uztfj` added a scene that is not
        # one (126, the ocean panel, 36 actors) -- so the islands are
        # counted on their own here and the panel is named beside them,
        # rather than letting a new scene quietly move a number three
        # letters and a round file quote.
        island_total = sum(
            len(roster._IDENTITY_OF_SCENE[scene].shippable_placements())
            for scene in roster.scenes_this_lane_answers_for()
            if scene != 126
        )
        ocean_panel = len(
            roster._IDENTITY_OF_SCENE[126].shippable_placements())
        self.assertEqual((island_total, volcano, ROSTER_COUNT, ocean_panel),
                         (692, 81, 97, 36))
        self.assertEqual(island_total + volcano + ROSTER_COUNT, 870)
        self.assertEqual(roster_total, island_total + ocean_panel)

    def test_a_duplicate_identity_in_one_frame_is_answered_once(self):
        """pf-adversary D10: a double-click is the input v141's own frozen
        loop comments say a client really produces."""
        legacy = self.legacy
        placement = _placement(self.civilian_index)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            response = responder_mod.respond(
                legacy=legacy,
                chosen_identities=(
                    placement.actor_identity, placement.actor_identity),
                population_indices=None,
                last_target_pos=(100.0, 200.0, 0.0, 0.0),
                scene_id=PRISON_EXILE,
            )
        self.assertIsNotNone(response)
        self.assertEqual(
            err.getvalue().count("_ANSWERED"), 0,
            "respond() printed the answer line itself; the call site does",
        )
        self.assertEqual(
            response.frame, _answer(legacy, self.civilian_index).frame,
            "a repeated identity changed the answer",
        )

    def test_the_civilians_go_out_leveled_and_named(self):
        """Round `7ste68`'s level, read back out of the frame.  A bare
        ``legacy.make_npc_attr`` body in the responder passes every other
        test in this file and fails this one.
        """
        legacy = self.legacy
        response = _answer(legacy, self.civilian_index)
        placement = _placement(self.civilian_index)
        leveled = world_census_level.leveled_npc_attr(
            legacy,
            template_n_id=placement.n_id,
            actor_identity=placement.actor_identity,
            scene_id=PRISON_EXILE,
            scene_sequence=0,
            visual_preset=placement.visual_preset,
            current_hp=placement.max_hp,
            max_hp=placement.max_hp,
            basic_name=placement.display_name,
            level=placement.level,
        )
        self.assertIn(leveled, response.frame)
        bare = legacy.make_npc_attr(
            placement.n_id, placement.actor_identity, 1, 0,
            placement.visual_preset,
        )
        self.assertNotIn(
            bare, response.frame,
            "a civilian went out with the bare body -- the level round "
            "`7ste68` shipped is reverted on the wire by every click",
        )


class TheLedgerPathTests(unittest.TestCase):
    """The keyword ``runtime.py`` does not pass yet, driven end to end.

    The CORE-REQUEST (20260902_1735) asks chief for one argument on the
    ChooseNPC call site.  These tests are what make that request cheap to
    accept: the responder side is already built and measured, so the day
    the keyword arrives nothing in this lane has to change.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()
        cls.mob_index, cls.mob = sorted(_hostile_by_index().items())[0]
        cls.civilian_index = next(
            index for index in sorted(
                p.placement_index for p in tables.load_known_placements())
            if index not in _hostile_by_index()
        )

    def _ledger_with(self, current_hp):
        roster = field_mobs.roster_for_scene_id(PRISON_EXILE)
        ledger = mob_combat.open_ledger(roster)
        return ledger.with_balance(
            mob_combat.MobBalance(
                self.mob.actor_identity, self.mob.max_hp, current_hp)
        )

    def test_a_wounded_monster_stays_wounded_when_a_ledger_is_passed(self):
        legacy = self.legacy
        wounded_hp = max(1, self.mob.max_hp // 2)
        response = _answer(
            legacy, self.civilian_index, ledger=self._ledger_with(wounded_hp))
        self.assertIsNotNone(response)
        self.assertIn("hp=ledger", response.console_lines[0])
        self.assertIn(
            field_mobs.hostile_npc_attr(
                legacy, self.mob, current_hp=wounded_hp,
                scene_id=field_mobs.SCENE_ID,
                scene_sequence=field_mobs.SCENE_SEQUENCE,
            ),
            response.frame,
        )
        self.assertNotIn(
            field_mobs.hostile_npc_attr(
                legacy, self.mob, current_hp=self.mob.max_hp,
                scene_id=field_mobs.SCENE_ID,
                scene_sequence=field_mobs.SCENE_SEQUENCE,
            ),
            response.frame,
            "the click healed a wounded monster back to its ceiling",
        )

    def test_a_ledger_row_this_module_cannot_read_answers_the_ceiling(self):
        """pf-adversary D10: the ``current < 0`` guard was unpinned.

        A real ``MobBalance`` refuses a negative HP at construction, so the
        input has to come from something that is not one -- which is the
        case the guard exists for.  A negative must never reach
        ``hostile_npc_attr`` as an alive body's HP, and must not be counted
        as a ledger read.
        """
        legacy = self.legacy

        class _Row:
            current_hp = -5

        class _StrangeLedger:
            def balance_of(self, _identity):
                return _Row()

        response = _answer(
            legacy, self.civilian_index, ledger=_StrangeLedger())
        self.assertIsNotNone(response)
        self.assertIn("hp=ceiling", response.console_lines[0])
        self.assertIn("from_ledger=0", response.console_lines[0])
        self.assertIn(
            field_mobs.hostile_npc_attr(
                legacy, self.mob, current_hp=self.mob.max_hp,
                scene_id=field_mobs.SCENE_ID,
                scene_sequence=field_mobs.SCENE_SEQUENCE,
            ),
            response.frame,
        )

    def test_a_dead_monster_does_not_silence_a_click_on_anyone_else(self):
        """~~test_a_dead_monster_refuses_the_whole_click_by_name~~ REWRITTEN,
        round `4uztfj`, and the old name is kept here because the test that
        bore it PINNED A DEFECT AS DESIRED BEHAVIOUR.  It clicked a
        CIVILIAN, with one monster elsewhere in the scene dead, and asserted
        the whole click was refused -- which is what the responder did, and
        which chief then measured on the real dispatcher: one kill silenced
        every click in scene 2 until the player reconnected, because
        ``_sync_combat_scene_state`` pulls the death back out of
        ``mob_death_register`` on every re-entry (letter 20260902_1918).
        ``COO-DECISION 20260902_1945``: the dead guard judges the CLICKED
        body only.  Same input as the old test; the opposite assertion."""
        legacy = self.legacy
        with contextlib.redirect_stderr(io.StringIO()) as err:
            response = responder_mod.respond(
                legacy=legacy,
                chosen_identities=(
                    _placement(self.civilian_index).actor_identity,),
                population_indices=None,
                last_target_pos=(1.0, 2.0, 0.0, 0.0),
                scene_id=PRISON_EXILE,
                mob_combat_ledger=self._ledger_with(0),
            )
        self.assertIsNotNone(
            response,
            "a kill somewhere else in the scene silenced a click on a "
            "civilian",
        )
        self.assertEqual(response.label, f"LANE_A_CHOOSE_NPC_SCENE2_FACE_P"
                         f"{self.civilian_index}")
        # The whole island is still in the frame -- the dead body included,
        # at its ceiling, because omitting it would delete the actor.
        self.assertIn(f"visible={ROSTER_COUNT}", response.console_lines[0])
        self.assertIn("dead_at_ceiling=1", response.console_lines[0])
        self.assertIn(
            f"_DEAD_BODY_AT_CEILING placement={self.mob_index} ",
            err.getvalue())

    def test_a_packet_naming_a_corpse_AND_a_civilian_is_still_answered(self):
        """ONE PACKET CAN NAME SEVERAL ACTORS, and that is what the guard's
        per-identity ``continue`` is for.  ``v141`` documents "TargetVital
        followed by one or more ChooseNPC records" and
        ``extract_choose_npc_identities`` returns a LIST.  pf-adversary
        measured that turning either responder's ``continue`` back into a
        ``return`` left the whole lane suite green, because no test drove a
        multi-identity packet: this is that test, and it is what pins the
        narrowing this round exists for."""
        legacy = self.legacy
        corpse = _placement(self.mob_index).actor_identity
        civilian = _placement(self.civilian_index).actor_identity
        with contextlib.redirect_stderr(io.StringIO()) as err:
            response = responder_mod.respond(
                legacy=legacy,
                chosen_identities=(corpse, civilian),
                population_indices=None,
                last_target_pos=(1.0, 2.0, 0.0, 0.0),
                scene_id=PRISON_EXILE,
                mob_combat_ledger=self._ledger_with(0),
            )
        printed = err.getvalue()
        self.assertIsNotNone(
            response,
            "a packet naming a corpse first was refused outright",
        )
        self.assertEqual(
            response.label,
            f"LANE_A_CHOOSE_NPC_SCENE2_FACE_P{self.civilian_index}")
        # AND THE CONSOLE MUST NOT SAY THE CLICK WAS REFUSED (pf-adversary
        # D3): the packet was answered, so the only refusal token allowed
        # here is the identity-scoped one.
        self.assertNotIn("_DECLINED", printed)
        self.assertIn("_IDENTITY_REFUSED", printed)

    def test_a_corpse_in_the_frame_is_not_counted_as_a_wound_or_a_read(self):
        """The two numbers a ticket may quote, pinned against the mutants
        that survived pf-adversary: a dead body sent at its ceiling is
        neither ``wounded`` nor a ledger read, because neither describes
        what went on the wire for it."""
        legacy = self.legacy
        response = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(
                _placement(self.civilian_index).actor_identity,),
            population_indices=None,
            last_target_pos=(1.0, 2.0, 0.0, 0.0),
            scene_id=PRISON_EXILE,
            mob_combat_ledger=self._ledger_with(0),
        )
        line = response.console_lines[0]
        self.assertIn("wounded=0", line)
        self.assertIn("dead_at_ceiling=1", line)
        self.assertIn("from_ledger=11", line)

    def test_the_dead_body_line_names_the_identity_in_hex(self):
        """Every identity in this tree is written ``0x2033``; a decimal one
        is a line a tester's grep cannot find (pf-adversary D6)."""
        legacy = self.legacy
        with contextlib.redirect_stderr(io.StringIO()) as err:
            responder_mod.respond(
                legacy=legacy,
                chosen_identities=(
                    _placement(self.civilian_index).actor_identity,),
                population_indices=None,
                last_target_pos=(1.0, 2.0, 0.0, 0.0),
                scene_id=PRISON_EXILE,
                mob_combat_ledger=self._ledger_with(0),
            )
        self.assertIn(
            f"_DEAD_BODY_AT_CEILING placement={self.mob_index} "
            f"identity=0x{self.mob.actor_identity:04X}",
            err.getvalue(),
        )

    def test_a_ledger_from_the_other_scene_is_refused_by_name(self):
        """pf-adversary D4, MEASURED AT HEAD: scene 2 and scene 14 share
        identity 0x2058 (placement 87 in both).  Before this round a
        scene-14 ledger carrying that row at 0 HP made a click on scene 2's
        LIVING placement 87 refuse itself -- a click dropped by a kill in
        another scene.  The ledger is now admitted for this scene before it
        is read."""
        from pirateforce_foundation import field_mob_hostile_bg0015
        legacy = self.legacy
        scene14_roster = tuple(
            field_mob_hostile_bg0015.scene14_hostile_roster())
        shared = {mob.actor_identity for mob in scene14_roster} & {
            mob.actor_identity for mob in _hostile_by_index().values()}
        self.assertTrue(shared, "the collision this test is about is gone")
        identity = sorted(shared)[0]
        foreign = mob_combat.open_ledger(scene14_roster)
        row = foreign.balance_of(identity)
        foreign = foreign.with_balance(
            mob_combat.MobBalance(identity, row.max_hp, 0))
        clicked = next(
            index for index, mob in _hostile_by_index().items()
            if mob.actor_identity == identity
        )
        with contextlib.redirect_stderr(io.StringIO()) as err:
            response = responder_mod.respond(
                legacy=legacy,
                chosen_identities=(_placement(clicked).actor_identity,),
                population_indices=None,
                last_target_pos=(1.0, 2.0, 0.0, 0.0),
                scene_id=PRISON_EXILE,
                mob_combat_ledger=foreign,
            )
        self.assertIsNotNone(
            response,
            "a kill in ANOTHER scene dropped a click in this one",
        )
        self.assertIn("hp=ceiling", response.console_lines[0])
        self.assertIn("dead_at_ceiling=0", response.console_lines[0])
        self.assertIn("_LEDGER_NOT_ADMITTED", err.getvalue())

    def test_a_ledger_that_raises_or_overflows_still_answers(self):
        """pf-adversary D5: the ``current_hp`` READ is inside the try now,
        and an HP above the table ceiling answers the ceiling instead of
        crashing inside the wire encoder's u32 contract."""
        legacy = self.legacy

        class _Exploding:
            scene = "Bg0002"

            def balance_of(self, _identity):
                class _Row:
                    @property
                    def current_hp(self):
                        raise RuntimeError("ledger on fire")
                return _Row()

        class _Overflowing:
            scene = "Bg0002"

            def balance_of(self, _identity):
                return type("_Row", (), {"current_hp": 2 ** 40})()

        for ledger in (_Exploding(), _Overflowing()):
            with self.subTest(ledger=type(ledger).__name__):
                response = _answer(
                    legacy, self.civilian_index, ledger=ledger)
                self.assertIsNotNone(response)
                self.assertIn("hp=ceiling", response.console_lines[0])

    def test_a_click_on_the_dead_body_itself_is_refused_by_its_own_name(self):
        """The other half of the same ruling: the corpse is not answered,
        and the reason names THE CLICKED placement rather than the first
        dead hostile in table order (chief's item 4.1: a click on placement
        0 printed ``placement_50``)."""
        legacy = self.legacy
        with contextlib.redirect_stderr(io.StringIO()) as err:
            response = responder_mod.respond(
                legacy=legacy,
                chosen_identities=(
                    _placement(self.mob_index).actor_identity,),
                population_indices=None,
                last_target_pos=(1.0, 2.0, 0.0, 0.0),
                scene_id=PRISON_EXILE,
                mob_combat_ledger=self._ledger_with(0),
            )
        self.assertIsNone(response)
        # An IDENTITY token, not a packet one: one ChooseNPC packet can
        # name several actors, so "this identity was refused" and "the
        # packet got no frame" are different lines now (pf-adversary D3).
        self.assertIn(
            "_IDENTITY_REFUSED reason=clicked_body_is_dead_needs_a_mob_"
            f"death_body placement={self.mob_index} identity=0x",
            err.getvalue())
        self.assertIn("every_named_identity_refused count=1", err.getvalue())

    def test_a_wounded_monster_is_counted_by_a_number_not_by_a_word(self):
        """``hp=ledger`` proves only that a ledger was readable -- an empty
        one prints it with all twelve bodies at their ceiling (chief's item
        4.3).  ``wounded=`` is the number that may be quoted."""
        legacy = self.legacy
        wounded = self._ledger_with(max(1, self.mob.max_hp - 1))
        response = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(
                _placement(self.civilian_index).actor_identity,),
            population_indices=None,
            last_target_pos=(1.0, 2.0, 0.0, 0.0),
            scene_id=PRISON_EXILE,
            mob_combat_ledger=wounded,
        )
        self.assertIsNotNone(response)
        self.assertIn("wounded=1", response.console_lines[0])
        self.assertIn("dead_at_ceiling=0", response.console_lines[0])
        self.assertIn(
            field_mobs.hostile_npc_attr(
                legacy, self.mob, current_hp=self.mob.max_hp - 1,
                scene_id=field_mobs.SCENE_ID,
                scene_sequence=field_mobs.SCENE_SEQUENCE,
            ),
            response.frame,
        )

    def test_a_foreign_ledger_answers_the_ceiling_and_says_so(self):
        """Fail-SAFE, and measured: a ledger with no row for this scene's
        monsters must not turn a click into a dropped frame -- AND the
        console line must not claim it read one (pf-adversary D8).  The
        first version of that line printed ``hp=ledger`` whenever a ledger
        argument arrived, so this exact input, where every one of the 12
        bodies carries its ceiling, was reported as if the wounds had been
        honoured.
        """
        legacy = self.legacy
        empty = mob_combat.open_ledger(())
        response = _answer(legacy, self.civilian_index, ledger=empty)
        self.assertIsNotNone(response)
        self.assertIn("hp=ceiling", response.console_lines[0])
        self.assertIn("from_ledger=0", response.console_lines[0])
        self.assertIn(
            field_mobs.hostile_npc_attr(
                legacy, self.mob, current_hp=self.mob.max_hp,
                scene_id=field_mobs.SCENE_ID,
                scene_sequence=field_mobs.SCENE_SEQUENCE,
            ),
            response.frame,
        )


class EveryRefusalIsNamedTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()

    def _refused(self, **kwargs):
        base = dict(
            legacy=self.legacy,
            chosen_identities=(0x2001,),
            population_indices=None,
            last_target_pos=(1.0, 2.0, 0.0, 0.0),
            scene_id=PRISON_EXILE,
        )
        base.update(kwargs)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            response = responder_mod.respond(**base)
        self.assertIsNone(response)
        return err.getvalue()

    def test_a_scene_other_than_two_is_refused_by_name(self):
        self.assertIn(
            "wrong_scene_this_responder_is_2", self._refused(scene_id=7))

    def test_a_shut_registry_door_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as work:
            registry = _shut_registry(Path(work))
            self.assertIn(
                "registry_door_shut",
                self._refused(scene_entry_registry=registry),
            )

    def test_the_pre_movement_click_is_refused_by_name(self):
        self.assertIn(
            "no_player_position_walk_one_step",
            self._refused(last_target_pos=None),
        )

    def test_an_identity_this_scenes_table_lacks_is_refused_by_name(self):
        # 0x2000 + 900 + 1: no placement index anywhere near this table.
        # TWO LINES SINCE ROUND `4uztfj`: the identity is refused by its own
        # token, and the PACKET's own refusal says how many identities went
        # that way rather than claiming none was answerable.
        printed = self._refused(chosen_identities=(0x2000 + 901,))
        self.assertIn(
            "_IDENTITY_REFUSED reason=placement_not_in_this_scenes_table "
            "placement=900 identity=0x2385",
            printed,
        )
        self.assertIn("every_named_identity_refused count=1", printed)

    def test_a_second_named_identity_is_tried_before_giving_up(self):
        legacy = self.legacy
        good = _placement(0).actor_identity
        with contextlib.redirect_stderr(io.StringIO()):
            response = responder_mod.respond(
                legacy=legacy,
                chosen_identities=(0x2000 + 901, good),
                population_indices=None,
                last_target_pos=(1.0, 2.0, 0.0, 0.0),
                scene_id=PRISON_EXILE,
            )
        self.assertIsNotNone(response)
        self.assertEqual(
            response.label, f"LANE_A_CHOOSE_NPC_SCENE{PRISON_EXILE}_FACE_P0")


class OnTheRealDispatcherTests(unittest.TestCase):
    """The click through ``state.dispatch``, and the re-check
    ``runtime.py``'s guard asks a claiming lane to make.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()

    def _state_on_scene_2(self, token):
        legacy = self.legacy
        lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                legacy.V135_PLAYER_Z,
            ),
            legacy.extract_avatar_attr_wire_from_actor,
        )
        state_type = make_state_class(
            legacy, lifecycle, LegacyProjector(legacy))
        state = state_type(token)
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc(token)))
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(state.foundation.account_id)[-1]
        spawn = world_scene_travel.spawn_position(
            world_scene_travel.destination(PRISON_EXILE))
        self.store.select_character(
            state.foundation.session_id, character.selector)
        self.store.save_position(
            state.foundation.session_id, character.id,
            Position(PRISON_EXILE, 0, spawn[0], spawn[1], spawn[2], 0.0),
        )
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_start_game_pc(character.selector)))
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            state.dispatch(legacy.parse_outer(_target_pos_pc(legacy, spawn)))
        self.assertEqual(
            state.foundation.selected.position.scene_id, PRISON_EXILE)
        return state

    def test_a_real_click_on_prison_exile_is_answered(self):
        legacy = self.legacy
        state = self._state_on_scene_2("scene2-click")
        placement = _placement(0)
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            actions = state.dispatch(legacy.parse_outer(
                _choose_npc_pc(legacy, placement.actor_identity)))
        self.assertEqual(len(actions), 1, actions)
        self.assertEqual(
            actions[0][0],
            f"LANE_A_CHOOSE_NPC_SCENE{PRISON_EXILE}_FACE_P0",
        )
        self.assertTrue(actions[0][1])
        self.assertTrue(actions[0][2])
        self.assertIn("LANE_HOOK_FIRED", err.getvalue())
        self.assertIn(
            f"LANE_A_CHOOSE_NPC_SCENE{PRISON_EXILE}_ANSWERED", err.getvalue())

    def test_claiming_this_scene_costs_an_arming_that_could_never_arm(self):
        """The re-check ``runtime.py``'s guard demands, both halves.

        (a) scene 2 arms no ``population_indices`` -- asserted here rather
        than quoted from the comment that says so; (b) v141's
        ``exact_p30_target`` requires exactly that field, so the arming a
        claimed scene skips could not have armed on scene 2 with or
        without this responder.
        """
        legacy = self.legacy
        state = self._state_on_scene_2("scene2-arming")
        self.assertIsNone(
            state.population_indices,
            "scene 2 armed population_indices -- the responder's membership "
            "reasoning and this claim both have to be re-derived",
        )
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            state.dispatch(legacy.parse_outer(
                _target_vital_pc(legacy, _placement(0).actor_identity)))
        self.assertFalse(state.p30_action_target_armed)

    def test_a_pre_movement_click_sends_no_bytes_and_is_named(self):
        """The first click after arrival, before the player has moved: no
        frame, and a console line a tester can grep instead of silence.
        """
        legacy = self.legacy
        state = self._state_on_scene_2("scene2-premovement")
        state.last_target_pos = None
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            actions = state.dispatch(legacy.parse_outer(
                _choose_npc_pc(legacy, _placement(0).actor_identity)))
        self.assertEqual(actions, [])
        self.assertIn("no_player_position_walk_one_step", err.getvalue())
        self.assertIn("scene_choose_npc_responder_declined", state.events)


if __name__ == "__main__":       # pragma: no cover
    unittest.main()
