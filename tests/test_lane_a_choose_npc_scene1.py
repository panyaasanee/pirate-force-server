"""LANE-A's ChooseNPC responder for scene 1 (Port Royal / bg0001).

Built round `yfbqmg` companion (2026-09-01), answering PANYA-ORDER
``pf_bridge/notes_to_chief/20260901_0955_PANYA-ORDER-login-path-must-ship-
the-census-eagerly-like-the-warp-path-now-does.md``.  ~~``production_allowed``
is ``False`` on ``main`` today (see the module's own docstring, "WHY THE
GATE STAYS CLOSED THIS ROUND")~~ -- AMENDED ROUND ``zqmosn``: still False,
but for the MEASURED reason that docstring now leads with rather than the
second-hand one it carried.  These tests drive ``respond()`` directly, the same
"responder's own logic, independent of the still-widening runtime.py
trigger" split ``test_lane_a_choose_npc_scene14.py`` uses for its own
module.

THE TWO TESTS ROUND ``zqmosn`` ADDED, AND WHY NEITHER REPLACES THE OTHER.
``TheAnswerRepeatsTheCorrectedFrozenFrameTests`` asks whether this
responder's FRAME says the same thing as the path it would take over from
-- the frozen builder's output after
``world_face_frame.rebuild_face_actions`` has corrected it, which is what
runtime.py really sends on a scene-1 click today.  It derives both sides
from live composers and compares bytes.  It passes, and on its own it is
MISLEADING, which is the whole lesson of the round: an answer to a click
is not one action.  ``TheGateStaysClosedForAMeasuredReasonTests`` drives
the REAL dispatcher and counts what else comes back -- the empty
NPCConversation collection that makes an NPC talk, and the shop's
trade-zoom -- neither of which a single ``ChooseNpcResponse`` can carry.
"""
from __future__ import annotations

import dataclasses
import inspect
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import world_census_level  # noqa: E402
from pirateforce_foundation import world_face_frame  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_port_royal_identity as identity  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_choose_npc_scene1 as responder_mod,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
PORT_ROYAL = world_population.SCENE_ID
QUALIFIED_MODULE = (
    "pirateforce_foundation.lane_hooks.lane_a_choose_npc_scene1"
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _shut_registry(work: Path):
    """A loaded registry with scene 1's door shut, temp file only (same
    technique ``test_lane_a_choose_npc_scene14.py``'s own helper uses).
    Scene 1 has ``DEFAULT_LOGIN_ENTRY_ALLOWED = True`` and no explicit row
    in the pin file, so this test proves the shut path by adding one rather
    than flipping an existing row."""
    raw = json.loads(
        world_scene_travel.REGISTRY_PATH.read_text(encoding="ascii"))
    found = False
    for row in raw["destinations"]:
        if row["n_id"] == PORT_ROYAL:
            row["login_entry_allowed"] = False
            found = True
    if not found:
        raw["destinations"].append({
            "n_id": PORT_ROYAL,
            "model_id": "BG0001",
            "login_entry_allowed": False,
        })
    path = work / "registry_scene_1_shut.json"
    path.write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="ascii")
    return world_scene_travel.load_scene_registry(path)


class ResponderRegistryTests(unittest.TestCase):
    """Registration itself, and the gate's withdrawal of it.

    ``production_allowed = False`` on this module means ``_discover()``
    withdraws the claim right after import (``lane_hooks.__init__``'s own
    ``_gate_module``/``_withdraw``), so scene 1's slot in the real,
    process-wide registry is EMPTY today -- unlike scene 14's module, whose
    default is ``True``.  That is the correct, intended state while this
    gate stays closed, and round ``zqmosn`` measured what filling it would
    cost the player (module docstring, "WHAT THE FLIP WOULD COST TODAY");
    asserting the opposite would be pinning the wrong half of the flag.
    """

    def test_the_module_is_withdrawn_from_the_real_registry_while_closed(self):
        self.assertIsNone(lane_hooks.scene_choose_npc_responder(PORT_ROYAL))

    def test_the_decorator_itself_still_names_this_module_and_function(self):
        """The decorator ran and registered before ``_discover()`` withdrew
        it -- proven with a private scene id so this does not collide with
        (or depend on) the real, already-withdrawn scene 1 slot."""
        private_scene = 999_901
        self.addCleanup(
            lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS.pop, private_scene, None,
        )
        registered = lane_hooks.choose_npc_responder(private_scene)(
            responder_mod.respond,
        )
        self.assertIs(registered, responder_mod.respond)
        entry = lane_hooks.scene_choose_npc_responder(private_scene)
        self.assertEqual(entry.module, QUALIFIED_MODULE)
        self.assertIs(entry.respond, responder_mod.respond)


class TheGateStaysClosedTests(unittest.TestCase):
    """The flag itself.  Read the module docstring's "WHAT THE FLIP WOULD
    COST TODAY" for the round ``zqmosn`` measurement that replaced this
    gate's original, second-hand reason; the measurement is driven in
    ``TheGateStaysClosedForAMeasuredReasonTests`` at the bottom of this
    file.  This flag is a convention marker every ``lane_hooks`` module in
    this project uses the same way (``module_production_allowed``); it is
    not a scenario flag and this lane's charter still forbids one --
    flipping it is this lane's own call in a later round, not a
    CORE-REQUEST."""

    def test_the_module_declares_production_allowed_false(self):
        self.assertIs(responder_mod.production_allowed, False)

    def test_the_gate_reports_this_module_closed(self):
        self.assertFalse(
            lane_hooks.module_production_allowed(
                "lane_a_choose_npc_scene1",
            )
        )


class TheResponderAnswersDirectlyTests(unittest.TestCase):
    """``respond()`` driven directly with real ``legacy`` and the real
    Port Royal placement table -- independent of the gate above, and
    independent of the still-missing runtime.py login-trigger widen."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()
        cls.placements = responder_mod._placements_by_index(cls.legacy)
        cls.population_indices = tuple(sorted(cls.placements))

    def test_the_composed_table_matches_world_population_own_filter(self):
        """This responder's placement table must be exactly the set
        ``world_population.census_order`` (and therefore a real
        ``population_indices``) can ever contain -- same identity filter,
        read directly rather than assumed."""
        expected = {
            placement.placement_index
            for placement in world_population.load_port_royal_placements(
                self.legacy)
            if identity.resolve(placement.template_id) is not None
        }
        self.assertEqual(set(self.population_indices), expected)
        self.assertGreater(len(self.population_indices), 0)

    def test_a_click_with_a_known_player_position_faces_the_player(self):
        legacy = self.legacy
        selected_idx = self.population_indices[0]
        actor_identity = 0x2000 + selected_idx + 1
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(actor_identity,),
            population_indices=self.population_indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
        )
        self.assertIsNotNone(answer)
        self.assertEqual(
            answer.label,
            f"LANE_A_CHOOSE_NPC_SCENE{PORT_ROYAL}_FACE_P{selected_idx}",
        )
        self.assertTrue(answer.pc)
        self.assertTrue(answer.frame)
        self.assertEqual(answer.delay, 0.0)
        self.assertEqual(len(answer.console_lines), 1)
        self.assertIn(f"placement={selected_idx}", answer.console_lines[0])
        self.assertIn("anchor=known", answer.console_lines[0])
        # cp874-encodable, same discipline as every other lane console line.
        answer.console_lines[0].encode("cp874")

    def test_a_click_with_no_player_position_is_answered_not_declined(self):
        """THE WHOLE POINT OF THIS MODULE (see "WHY None IS ANSWERED, NOT
        DECLINED" in the module docstring): the everyday state the moment
        an eager login census exists is `last_target_pos is None`, and a
        click in that state must get an honest frame, not silence."""
        legacy = self.legacy
        selected_idx = self.population_indices[0]
        actor_identity = 0x2000 + selected_idx + 1
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(actor_identity,),
            population_indices=self.population_indices,
            last_target_pos=None,
        )
        self.assertIsNotNone(answer)
        self.assertTrue(answer.pc)
        self.assertIn("anchor=none", answer.console_lines[0])

    def test_the_no_position_heading_matches_the_arrival_census_table(self):
        """The fallback heading must be the SAME fixed cardinal heading the
        arrival census itself already assigned this placement
        (``world_population.HEADINGS``), never an invented one."""
        legacy = self.legacy
        selected_idx = self.population_indices[0]
        placement = self.placements[selected_idx]
        expected = world_population.HEADINGS[selected_idx & 3]
        heading = responder_mod._answer_heading(legacy, placement, None)
        self.assertEqual(heading, expected)

    def test_the_monster_placement_keeps_its_measured_hp(self):
        """P30 (``world_population.SHIPPED_MONSTER_INDEX``) carries the
        measured V117 HP override on the arrival census; a click response
        must not silently revert it to the default 100, the same
        discipline ``AClickPreservesTheHostileSpliceTests`` pins for scene
        14's own splice."""
        legacy = self.legacy
        monster_idx = world_population.SHIPPED_MONSTER_INDEX
        # ~~a conditional step-aside when P30 has no shippable identity~~
        # -- STRUCK ROUND ``zqmosn`` and turned into an assertion, for the
        # reason the preflight itself gives: the gate pins skip counts, and
        # a test that can quietly step aside is a test that can quietly
        # stop asserting.  P30 resolving is MEASURED, not hoped for
        # (``RE-128``: Mob-Set 31 -> n_ID 248 "Da Vinci"), so the day it
        # stops resolving this file should go red and say so.
        self.assertIn(monster_idx, self.population_indices)
        actor_identity = 0x2000 + monster_idx + 1
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(actor_identity,),
            population_indices=self.population_indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
        )
        self.assertIsNotNone(answer)
        placement = self.placements[monster_idx]
        resolved = identity.resolve(placement.template_id)
        # ~~``legacy.make_npc_attr(...)`` as the expected body~~ -- STRUCK
        # ROUND ``zqmosn``, and the strike is the POINT of this test now:
        # the bare frozen helper carries no level, the responder composes
        # through the census's own ``world_census_level.leveled_npc_attr``
        # since this round, and an expectation still written against the
        # level-less helper would have gone red for the right reason.  The
        # HP claim this test was written for is unchanged and still
        # asserted -- it now travels inside the levelled body.
        monster_body = world_census_level.leveled_npc_attr(
            legacy,
            template_n_id=resolved.mobs_n_id,
            actor_identity=placement.actor_identity,
            scene_id=PORT_ROYAL,
            scene_sequence=world_population.SCENE_SEQUENCE,
            visual_preset=resolved.outfit,
            current_hp=legacy.V117_P30_EXACT_HP,
            max_hp=legacy.V117_P30_EXACT_HP,
            basic_name=resolved.name,
            level=resolved.level,
        )
        self.assertIn(monster_body, answer.pc)

    def test_declines_for_an_identity_outside_population_indices(self):
        legacy = self.legacy
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + 999_990 + 1,),
            population_indices=(1, 2, 3),
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
        )
        self.assertIsNone(answer)

    def test_declines_when_membership_is_not_armed(self):
        legacy = self.legacy
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + 1 + 1,),
            population_indices=None,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
        )
        self.assertIsNone(answer)

    def test_declines_when_the_scene_is_not_open_to_players(self):
        with tempfile.TemporaryDirectory() as work:
            legacy = self.legacy
            raw_registry = _shut_registry(Path(work))
            answer = responder_mod.respond(
                legacy=legacy,
                chosen_identities=(0x2000 + self.population_indices[0] + 1,),
                population_indices=self.population_indices,
                last_target_pos=(0.0, 0.0, 0.0, 0.0),
                scene_entry_registry=raw_registry,
            )
            self.assertIsNone(answer)

    def test_declines_for_a_scene_other_than_1(self):
        legacy = self.legacy
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + self.population_indices[0] + 1,),
            population_indices=self.population_indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
            scene_id=14,
        )
        self.assertIsNone(answer)

    def test_fails_closed_on_a_placement_this_scenes_own_table_lacks(self):
        """Never invent a row: an index in ``population_indices`` this
        scene's own filtered table does not carry is skipped."""
        legacy = self.legacy
        bogus_idx = 999_999
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + bogus_idx + 1,),
            population_indices=(bogus_idx,),
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
        )
        self.assertIsNone(answer)

    def test_a_multi_select_click_answers_only_the_first_named_identity(self):
        """Same documented gap ``lane_a_choose_npc_scene14.py`` ships with
        (module docstring point (2)): at most one ``ChooseNpcResponse`` per
        call, pinned here rather than fixed, so it cannot silently get
        worse for this scene either."""
        legacy = self.legacy
        first_idx, second_idx = self.population_indices[:2]
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(
                0x2000 + first_idx + 1, 0x2000 + second_idx + 1,
            ),
            population_indices=self.population_indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
        )
        self.assertIsNotNone(answer)
        self.assertEqual(
            answer.label,
            f"LANE_A_CHOOSE_NPC_SCENE{PORT_ROYAL}_FACE_P{first_idx}",
        )


class TheAnswerRepeatsTheCorrectedFrozenFrameTests(unittest.TestCase):
    """THE PARITY PROOF THE GATE WAS WAITING FOR (module docstring, "WHY
    THE GATE IS OPEN FROM ROUND ``zqmosn``", reason 2).

    What this responder replaces is NOT the frozen builder's raw output.
    ``runtime.py:9103-9107`` rewrites every scene-1 face frame through
    ``world_face_frame.rebuild_face_actions`` whenever the census resolved
    its identities -- which the bg0001 census always does -- so the frame a
    Port Royal player really receives on a click today is
    ``world_face_frame.build_face_state``'s.  That is the only honest thing
    to compare against, and comparing against the raw frozen builder would
    have flattered this module by measuring it against a frame no player
    has had for weeks.

    Both sides are composed live, on the real placement table, with the
    real ``legacy``.  Neither side is a copy pasted into this file: a
    change to the census's identity, HP, level or heading rules moves both
    sides at once, and only a change to ONE of the two composers can turn
    this red -- which is exactly the drift worth a test.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()
        cls.placements = responder_mod._placements_by_index(cls.legacy)
        cls.population_indices = tuple(sorted(cls.placements))

    def _lane_answer(self, selected_idx, player_x, player_y):
        return responder_mod.respond(
            legacy=self.legacy,
            chosen_identities=(0x2000 + selected_idx + 1,),
            population_indices=self.population_indices,
            last_target_pos=(player_x, player_y, 0.0, 0.0),
        )

    def test_the_click_answer_is_byte_identical_to_the_corrected_frame(self):
        """On a clean floor -- no ``mob_loot_cell`` passed, which is every
        boot before chief hands one over -- the two frames must be equal
        byte for byte, not merely equal in length or in actor count."""
        for selected_idx in (
            self.population_indices[0],
            self.population_indices[len(self.population_indices) // 2],
            self.population_indices[-1],
        ):
            with self.subTest(placement=selected_idx):
                answer = self._lane_answer(selected_idx, 10.0, 20.0)
                self.assertIsNotNone(answer)
                expected_pc, _expected_frame = world_face_frame.\
                    build_face_state(
                        self.legacy, self.population_indices,
                        selected_idx, 10.0, 20.0,
                    )
                self.assertEqual(bytes(answer.pc), bytes(expected_pc))

    def test_every_actor_carries_its_mined_level(self):
        """The defect this round removed, pinned so it cannot come back:
        the module composed with the bare ``legacy.make_npc_attr``, which
        has no level parameter at all.  A level-less body for ANY actor in
        the answer is the whole regression, so the assertion is over the
        composed answer, not over one hand-picked placement."""
        selected_idx = self.population_indices[0]
        answer = self._lane_answer(selected_idx, 10.0, 20.0)
        self.assertIsNotNone(answer)
        pc = bytes(answer.pc)
        for idx in self.population_indices:
            placement = self.placements[idx]
            resolved = identity.resolve(placement.template_id)
            with self.subTest(placement=idx):
                levelless = self.legacy.make_npc_attr(
                    resolved.mobs_n_id, placement.actor_identity,
                    PORT_ROYAL, world_population.SCENE_SEQUENCE,
                    resolved.outfit,
                    current_hp=(
                        self.legacy.V117_P30_EXACT_HP
                        if idx == world_population.SHIPPED_MONSTER_INDEX
                        else world_population.DEFAULT_HP
                    ),
                    max_hp=(
                        self.legacy.V117_P30_EXACT_HP
                        if idx == world_population.SHIPPED_MONSTER_INDEX
                        else world_population.DEFAULT_HP
                    ),
                    basic_name=resolved.name,
                )
                # The level-less body must NOT be on the wire, and the
                # levelled one must be.  Asserting only the second half
                # would pass on a frame carrying both.
                self.assertNotIn(levelless, pc)
                self.assertIn(
                    world_census_level.leveled_npc_attr(
                        self.legacy,
                        template_n_id=resolved.mobs_n_id,
                        actor_identity=placement.actor_identity,
                        scene_id=PORT_ROYAL,
                        scene_sequence=world_population.SCENE_SEQUENCE,
                        visual_preset=resolved.outfit,
                        current_hp=(
                            self.legacy.V117_P30_EXACT_HP
                            if idx == world_population.SHIPPED_MONSTER_INDEX
                            else world_population.DEFAULT_HP
                        ),
                        max_hp=(
                            self.legacy.V117_P30_EXACT_HP
                            if idx == world_population.SHIPPED_MONSTER_INDEX
                            else world_population.DEFAULT_HP
                        ),
                        basic_name=resolved.name,
                        level=resolved.level,
                    ),
                    pc,
                )

    def test_the_frozen_loop_refuses_the_one_click_this_responder_answers(
            self):
        """The single actor-level difference the flip introduces, measured
        rather than asserted: v141's own loop (v141:4396-4416) skips
        ``V112_MONSTER_INDEX`` at v141:4413 with
        ``v112_choose_p30_usage1_no_npc_response`` and sends nothing, so a click there is silence today.
        ``RE-128`` resolved that placement to a townsman, so answering it
        is a gain -- but it IS a difference, and a reader of this file
        must find it named."""
        monster_idx = world_population.SHIPPED_MONSTER_INDEX
        # Asserted, never skipped, deliberately: the gate pins skip
        # counts, and a test that can quietly step aside is a test that
        # can quietly stop asserting -- the shape that cost #601 a whole
        # round.  (The word for that call is not written here either: the
        # preflight counts the token, not the sentence around it.)  P30
        # resolving is a MEASURED fact of this table, so it is asserted:
        # RE-128 resolves Mob-Set 31 to n_ID 248 "Da Vinci".
        self.assertIn(monster_idx, self.population_indices)
        self.assertEqual(self.legacy.V112_MONSTER_INDEX, monster_idx)
        answer = self._lane_answer(monster_idx, 10.0, 20.0)
        self.assertIsNotNone(answer)
        self.assertEqual(
            answer.label,
            f"LANE_A_CHOOSE_NPC_SCENE{PORT_ROYAL}_FACE_P{monster_idx}",
        )


class TheGateStaysClosedForAMeasuredReasonTests(unittest.TestCase):
    """WHAT THE FLIP WOULD COST, DRIVEN RATHER THAN ARGUED (round
    ``zqmosn``).

    ``TheAnswerRepeatsTheCorrectedFrozenFrameTests`` above proves this
    responder's FRAME is byte-identical to the one runtime.py sends today.
    An earlier draft of that round read the equality as permission to flip
    the gate.  It is not, and this class is why: the frozen loop answers a
    scene-1 click with MORE THAN ONE ACTION, and a ``ChooseNpcResponse``
    carries exactly one ``pc``/``frame`` pair.

    Driven through ``runtime.make_state_class`` itself -- no server
    process, no socket -- with this module withdrawn, which is simply
    ``main``'s own state while the gate is closed.  So these assertions
    describe TODAY's production answer, not a hypothetical: what the
    responder would have to reproduce before it may take the scene over.
    If a future round makes ``ChooseNpcResponse`` a collection and composes
    these actions, this class is the one that tells it when it is done.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()

    def _booted_state(self, token):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = SQLiteStore(Path(tmp.name) / "state.sqlite3",
                            ROOT / "migrations")
        store.migrate()
        legacy = self.legacy
        lifecycle = CharacterLifecycle(
            store,
            Position(PORT_ROYAL, 0, legacy.V135_PLAYER_X,
                     legacy.V135_PLAYER_Y, legacy.V135_PLAYER_Z),
            legacy.extract_avatar_attr_wire_from_actor,
        )
        state_type = make_state_class(
            legacy, lifecycle, LegacyProjector(legacy))
        state = state_type(token)
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc(token)))
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        character = store.list_characters(state.foundation.account_id)[-1]
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_start_game_pc(character.selector)))
        # The first step: what arms the census, and the state every click
        # in this class is measured from.
        state.dispatch(legacy.parse_outer(self._target_pos_pc()))
        return state

    def _target_pos_pc(self, xyz=(10.0, 20.0, 30.0)):
        legacy = self.legacy
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
            + legacy.u8tag(0x0B, 0)
            + b"".join(legacy.f32tag(v) for v in (*xyz, 0.0))
            + legacy.u8tag(0x0B, 0)
            + legacy.u8tag(0x0B, 0)
        )

    def _click_pc(self, actor_identity):
        legacy = self.legacy
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.CHOOSE_NPC)
            + legacy.u8tag(0x0B, 0)
            + legacy.qwordtag(0x32, actor_identity)
        )

    def _labels_for_click(self, token, placement_index):
        state = self._booted_state(token)
        actions = state.dispatch(self.legacy.parse_outer(
            self._click_pc(0x2000 + placement_index + 1)))
        return [action[0] for action in actions]

    def test_todays_answer_to_an_ordinary_click_carries_the_talk_trigger(
            self):
        """The empty NPCConversation collection is the client's authentic
        default-talk trigger (v141's own comment above
        ``make_v98_conversation_face_state``).  Lose it and the NPC stops
        talking -- which is what taking this scene over with a
        single-frame response would do today.

        DRIVES PLACEMENT 3, NOT PLACEMENT 1, AND THE DIFFERENCE IS THE
        WHOLE TEST (pf-adversary ``zqmosn`` B3, measured).  Placement 1 is
        Columbus, the one actor in this scene that carries a SECOND action
        for an unrelated reason (``_dispatch_columbus_quest3021``, additive
        and untouched by the responder branch), so with the gate flipped
        his click still returns two labels and a count assertion on him
        passes while the talk trigger it names is gone.  Placement 3 is an
        ordinary townsman: two labels there are the face frame and the talk
        trigger, and nothing else."""
        labels = self._labels_for_click("tok-scene1-talk", 3)
        self.assertIn("V98_NPC_CONVERSATION_DEFAULT_P3", labels)
        # AND THE FACE LABEL IS THE FROZEN ONE, WHICH IS WHAT MAKES THIS A
        # CONTROL (pf-adversary `yjjtyn` D5, MEASURED): without this line
        # the class passed IDENTICALLY with the responder withdrawn and
        # with it live, so the one test whose job is to describe "TODAY's
        # production answer" could not say which path produced it.  The
        # lane's own answer labels its face frame
        # `LANE_A_CHOOSE_NPC_SCENE1_FACE_P3` and its trigger
        # `..._VIA_LANE_A`, so both assertions below fail the day this
        # class is accidentally driven against the lane path.
        self.assertIn("V98_NPC_FACE_PLAYER_POSITION_HEADING_P3", labels)
        self.assertNotIn("V98_NPC_CONVERSATION_DEFAULT_P3_VIA_LANE_A",
                         labels)
        self.assertEqual(
            len(labels), 2,
            "an answer to an ordinary scene-1 click is exactly the face "
            "frame and the talk trigger; if this ever becomes one action, "
            "re-read the module docstring before flipping the gate",
        )

    def test_todays_answer_at_the_shop_trigger_carries_the_trade_zoom(self):
        shop_index = self.legacy.V112_SHOP_TRIGGER_INDEX
        labels = self._labels_for_click("tok-scene1-shop", shop_index)
        self.assertTrue(
            any(label.startswith("V112_TEST_HARNESS_TRADE_ZOOM")
                for label in labels),
            f"the shop action is gone from {labels}",
        )

    def test_one_response_carries_one_frame_which_is_the_whole_blocker(self):
        """~~The structural half of the reason, read off the response object
        rather than asserted in prose: there is one ``pc`` and one
        ``frame``, so no composition inside ``respond()`` can emit the two
        actions above.~~  AMENDED ROUND ``yjjtyn``, AND THE STRUCK HALF IS
        WHY THIS TEST STAYS: the response still carries exactly one
        ``pc``/``frame`` pair -- which is what this asserts, unchanged --
        but the design change runtime.py's comment asked for landed as
        ``extra_actions`` beside it, so "one pair" is no longer the whole
        blocker.  What is left of the blocker: nothing in ``runtime.py``
        reads that field yet (chief's one line), and the shop's trade-zoom
        is once-per-session state no argument reaches this responder
        carries.  See ``TheTalkTriggerRidesAlongAsAnExtraActionTests`` for
        the half that is paid."""
        legacy = self.legacy
        placements = responder_mod._placements_by_index(legacy)
        indices = tuple(sorted(placements))
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + indices[0] + 1,),
            population_indices=indices,
            last_target_pos=(10.0, 20.0, 0.0, 0.0),
        )
        self.assertIsNotNone(answer)
        self.assertIsInstance(answer.pc, (bytes, bytearray))
        self.assertIsInstance(answer.frame, (bytes, bytearray))
        self.assertFalse(hasattr(answer, "actions"))


class TheTalkTriggerRidesAlongAsAnExtraActionTests(unittest.TestCase):
    """Step 1+2 of the module docstring's flip list, round ``yjjtyn``.

    The class above measures what the flip would COST.  This one measures
    what has been paid back: the empty ``NPCConversation`` collection --
    the client's authentic default-talk trigger -- now travels with the
    answer in ``ChooseNpcResponse.extra_actions``, composed by CALLING the
    frozen builder rather than by copying its bytes.

    NONE OF THIS REACHES A PLAYER YET AND THE TESTS SAY SO BY WHAT THEY DO
    NOT ASSERT: nothing here drives ``runtime.py``, because the one line
    that would queue this field is chief's and is not on ``main``.  What
    is pinned is the composition and every way it honestly composes
    nothing -- including the one pf-adversary `yjjtyn` D3 measured this
    round's first draft missing: the rows LANE B's registry calls hostile
    in this scene are placements 103/105/107/109, not the frozen loop's
    single harness monster at index 30.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()
        cls.placements = responder_mod._placements_by_index(cls.legacy)
        cls.population_indices = tuple(sorted(cls.placements))

    def _ordinary_index(self):
        """A placement that is neither the quest actor, the shop trigger
        nor the monster -- read off the frozen module's own numbers, so
        this test cannot drift from the code it checks."""
        special = {
            self.legacy.V129_QUEST_ACTOR_INDEX,
            self.legacy.V112_SHOP_TRIGGER_INDEX,
            self.legacy.V112_MONSTER_INDEX,
        }
        for idx in self.population_indices:
            if idx not in special:
                return idx
        self.fail("no ordinary placement in Port Royal's own table")

    def test_an_ordinary_click_carries_the_frozen_talk_trigger(self):
        legacy = self.legacy
        selected_idx = self._ordinary_index()
        placement = self.placements[selected_idx]
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + selected_idx + 1,),
            population_indices=self.population_indices,
            last_target_pos=(10.0, 20.0, 0.0, 0.0),
        )
        self.assertIsNotNone(answer)
        self.assertEqual(len(answer.extra_actions), 1)
        label, pc, frame, delay = answer.extra_actions[0]
        # THE LABEL IS THE FROZEN NAME PLUS `_VIA_LANE_A`: the greps in
        # pf_bridge/GAME_TEST_QUEUE.md that read this string match it as a
        # prefix, so the house rule (AGENTS.md - a PR moving a string a
        # ticket greps must keep the grep answering) is satisfied, and the
        # suffix keeps the lane path distinguishable from the frozen one on
        # a capture (pf-adversary `yjjtyn` D5).
        self.assertEqual(
            label,
            f"V98_NPC_CONVERSATION_DEFAULT_P{selected_idx}_VIA_LANE_A")
        expected_pc, expected_frame = legacy.make_npc_conversation_empty(
            placement.actor_identity)
        self.assertEqual(bytes(pc), bytes(expected_pc))
        self.assertEqual(bytes(frame), bytes(expected_frame))
        self.assertEqual(delay, 0.0)
        self.assertIn("extra_composed=1", answer.console_lines[0])
        self.assertIn("extra_reason=conversation_default",
                      answer.console_lines[0])
        answer.console_lines[0].encode("cp874")

    def test_the_trigger_is_derived_from_the_frozen_builder_not_copied(self):
        """A fixture-driven mutant: replace the frozen builder and the
        extra must change with it.  Without this, a hardcoded copy of
        today's 34 bytes would pass every assertion above."""
        legacy = self.legacy
        selected_idx = self._ordinary_index()
        sentinel = (b"PC-SENTINEL", b"FRAME-SENTINEL")
        real = legacy.make_npc_conversation_empty
        legacy.make_npc_conversation_empty = lambda actor_identity: sentinel
        try:
            answer = responder_mod.respond(
                legacy=legacy,
                chosen_identities=(0x2000 + selected_idx + 1,),
                population_indices=self.population_indices,
                last_target_pos=(10.0, 20.0, 0.0, 0.0),
            )
        finally:
            legacy.make_npc_conversation_empty = real
        self.assertEqual(answer.extra_actions[0][1], sentinel[0])
        self.assertEqual(answer.extra_actions[0][2], sentinel[1])

    def test_the_three_latched_or_skipped_placements_get_no_extra(self):
        """Each refusal is its own named reason, because "composed
        nothing" is several different facts on a capture, and a capture
        that cannot tell them apart is the evidence channel this project
        keeps deleting."""
        legacy = self.legacy
        placement = self.placements[self._ordinary_index()]
        for idx, reason in (
            (legacy.V129_QUEST_ACTOR_INDEX,
             "no_extra_quest_actor_needs_session_latch"),
            (legacy.V112_SHOP_TRIGGER_INDEX,
             "no_extra_shop_trigger_needs_session_latch"),
            (legacy.V112_MONSTER_INDEX,
             "no_extra_monster_frozen_path_sends_none"),
        ):
            with self.subTest(placement=idx):
                extras, got, latches = responder_mod._conversation_extra(
                    legacy, placement, idx, PORT_ROYAL)
                self.assertEqual(extras, ())
                self.assertEqual(got, reason)
                # Omitting the latch keywords is what every call site
                # does today, and it must spend nothing.
                self.assertEqual(latches, ())

    def test_a_legacy_without_the_frozen_indices_composes_nothing(self):
        """Fail closed in the direction that composes LESS: with no way to
        tell the shop trigger from a townsman, this must not compose a
        talk trigger for a click the frozen path never sent one for."""
        class _NoConstants:
            @staticmethod
            def make_npc_conversation_empty(actor_identity):
                raise AssertionError("must not be reached")

        extras, reason, latches = responder_mod._conversation_extra(
            _NoConstants(), self.placements[self._ordinary_index()],
            self._ordinary_index(), PORT_ROYAL,
        )
        self.assertEqual(extras, ())
        self.assertEqual(reason, "no_extra_frozen_indices_unreadable")
        self.assertEqual(latches, ())

    def test_a_refusing_builder_costs_the_extra_not_the_answer(self):
        """A responder must never take the listener thread down, and an
        answer that lost its talk trigger is still better than a dropped
        click -- but the console must say which happened."""
        legacy = self.legacy
        selected_idx = self._ordinary_index()
        real = legacy.make_npc_conversation_empty

        def _boom(actor_identity):
            raise RuntimeError("frozen builder refused")

        legacy.make_npc_conversation_empty = _boom
        try:
            answer = responder_mod.respond(
                legacy=legacy,
                chosen_identities=(0x2000 + selected_idx + 1,),
                population_indices=self.population_indices,
                last_target_pos=(10.0, 20.0, 0.0, 0.0),
            )
        finally:
            legacy.make_npc_conversation_empty = real
        self.assertIsNotNone(answer)
        self.assertTrue(answer.pc)
        self.assertEqual(answer.extra_actions, ())
        self.assertIn("extra_composed=0", answer.console_lines[0])
        self.assertIn("extra_reason=no_extra_builder_refused_RuntimeError",
                      answer.console_lines[0])

    def test_every_row_lane_b_calls_hostile_here_gets_no_talk_trigger(self):
        """pf-adversary `yjjtyn` D3, MEASURED: the frozen loop's monster
        INDEX is the harness monster (placement 30), while the rows this
        scene's AI actually ticks are lane B's registry rows.  Handing one
        of those an empty conversation window is `GT-104`'s symptom, and
        this lane must not become its second owner from a new place.

        Derived from lane B's OWN public reader, never a per-scene table
        import and never a copy of the placement numbers -- the same route
        `lane_a_scene_census._field_mob_identities` takes."""
        legacy = self.legacy
        hostiles = [
            mob for mob in field_mobs.roster_for_scene_id(PORT_ROYAL)
            if (mob.actor_identity - 0x2000 - 1) in self.placements
        ]
        if not hostiles:
            self.skipTest(
                "lane B's registry names no hostile row this responder's "
                "own table can answer for scene 1 today"
            )
        for mob in hostiles:
            idx = mob.actor_identity - 0x2000 - 1
            with self.subTest(placement=idx):
                extras, reason, latches = responder_mod._conversation_extra(
                    legacy, self.placements[idx], idx, PORT_ROYAL)
                self.assertEqual(extras, ())
                self.assertEqual(reason, "no_extra_hostile_row_lane_b_registry")
                self.assertEqual(latches, ())

    def test_an_unreadable_hostile_registry_composes_nothing(self):
        """Fail closed in the direction that composes LESS, and say which
        silence this is -- the same distinction the census's own reader
        draws for its failure path."""
        legacy = self.legacy
        selected_idx = self._ordinary_index()
        real = field_mobs.roster_for_scene_id

        def _boom(scene_id):
            raise RuntimeError("registry refused")

        field_mobs.roster_for_scene_id = _boom
        try:
            extras, reason, latches = responder_mod._conversation_extra(
                legacy, self.placements[selected_idx], selected_idx,
                PORT_ROYAL,
            )
        finally:
            field_mobs.roster_for_scene_id = real
        self.assertEqual(extras, ())
        self.assertEqual(
            reason, "no_extra_hostile_registry_unreadable_RuntimeError")
        self.assertEqual(latches, ())

    def test_the_new_field_defaults_to_empty_for_every_other_responder(self):
        """The default is the safety argument for the other four
        responders (scenes 2, 14, the ten roster scenes): a response built
        the way they build it means exactly what it meant before this
        field existed."""
        response = lane_hooks.ChooseNpcResponse(
            label="X", pc=b"p", frame=b"f", delay=0.0, console_lines=(),
        )
        self.assertEqual(response.extra_actions, ())
        # ``latches_spent`` joined the tuple in round ``rlymq1`` with the
        # same additive default, and for the same reason: a responder
        # that never heard of it builds a response that means exactly
        # what it meant before.
        self.assertEqual(response.latches_spent, ())
        self.assertEqual(len(response), 7)


class TheCensusAuthorityIsHonouredTests(unittest.TestCase):
    """STEP 5 OF THE MODULE'S PROMOTION LIST, LANE HALF.

    The responder must decline -- hand the frame back to the frozen loop
    -- on a boot whose census could not resolve identities, because
    pf-adversary ``zqmosn`` MEASURED what answering costs there: a click
    on P0 answered with silence where the frozen path opened a quest
    conversation, and a click on P91 shipped two actors after login had
    announced three.

    The keyword is inert until chief's call site passes it (see
    ``WORLD_CENSUS_IDENTITY_RESOLVED_WIRING``), so the second half of this
    class pins the thing that makes shipping it safe: omitting the keyword
    -- which is every call today -- is byte-for-byte the old behaviour,
    and ``None`` is NOT read as a failure."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()
        cls.placements = responder_mod._placements_by_index(cls.legacy)
        cls.population_indices = tuple(sorted(cls.placements))

    def _click(self, **extra):
        idx = self.population_indices[0]
        return responder_mod.respond(
            legacy=self.legacy,
            chosen_identities=(0x2000 + idx + 1,),
            population_indices=self.population_indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
            **extra,
        )

    def test_declines_when_the_census_says_identities_are_unresolved(self):
        self.assertIsNone(
            self._click(world_census_identity_resolved=False)
        )

    def test_answers_when_the_census_says_identities_resolved(self):
        self.assertIsNotNone(
            self._click(world_census_identity_resolved=True)
        )

    def test_an_omitted_keyword_is_byte_for_byte_the_old_behaviour(self):
        """The mutant this pins: reading the default as a failure (a bare
        ``if not world_census_identity_resolved`` instead of ``is
        False``).  That mutant makes the responder decline on every call
        the real call site makes today, and this assertion goes red."""
        omitted = self._click()
        passed_none = self._click(world_census_identity_resolved=None)
        self.assertIsNotNone(omitted)
        self.assertIsNotNone(passed_none)
        # THE WHOLE TUPLE, NOT A HAND-PICKED FOUR (pf-adversary ``6dvcer``
        # D4): an earlier version of this test compared label/pc/frame/
        # extra_actions and let a mutant through that changed the TEXT of
        # ``console_lines`` while keeping its length -- ``delay`` and
        # ``console_lines`` are both read at the call site.
        self.assertEqual(omitted, passed_none)

    def test_the_decline_is_checked_before_any_frame_is_composed(self):
        """A decline must cost nothing, not compose-then-throw-away: with
        a ``legacy`` whose frame builder would raise, an unresolved census
        still returns ``None`` rather than an exception."""

        class _Exploding:
            def __getattr__(self, name):
                raise AssertionError(
                    f"the decline composed something: touched {name!r}"
                )

        self.assertIsNone(
            responder_mod.respond(
                legacy=_Exploding(),
                chosen_identities=(0x2001,),
                population_indices=(0,),
                last_target_pos=(0.0, 0.0, 0.0, 0.0),
                world_census_identity_resolved=False,
            )
        )

    def test_the_wiring_constant_names_the_call_sites_keyword(self):
        """The ask chief reads is the ask this module actually honours --
        a renamed keyword here must not leave the constant pointing at the
        old name."""
        # THE WHOLE ASSIGNMENT, NOT THE NAME ALONE (pf-adversary ``6dvcer``
        # D3 mutant M2): substituting ``self.world_census_sent`` on the
        # right-hand side left the feature's name in the file and the test
        # green while the ask pointed chief at the one flag the frozen
        # fallback sets to True on exactly the boot this guard exists for.
        self.assertIn(
            "world_census_identity_resolved=self.world_census_identity_resolved",
            responder_mod.WORLD_CENSUS_IDENTITY_RESOLVED_WIRING,
        )
        # And the ask must still carry its second half (D1): the keyword
        # alone turns a census-failed boot silent, because a decline at the
        # call site is ``actions = []`` and not the frozen loop.
        self.assertIn(
            "actions = []",
            responder_mod.WORLD_CENSUS_IDENTITY_RESOLVED_WIRING,
        )
        self.assertIn(
            "world_census_identity_resolved",
            inspect.signature(responder_mod.respond).parameters,
        )


class TheOncePerSessionLatchedActionsTests(unittest.TestCase):
    """Step 2's SECOND half, round ``rlymq1``: the two latched actions.

    The class above pins the action that rides along on EVERY ordinary
    click.  This one pins the two the frozen loop sends ONCE PER SESSION --
    the store-5 trade-zoom at the shop trigger
    (``current/pf_login_game_server_v141.py:4433-4441``) and the q3020
    conversation at the quest actor (``:4453-4461``) -- and the
    three-state keyword that decides which of them this responder composes.

    NONE OF IT REACHES A PLAYER YET, AND THE FIRST TEST IN THIS CLASS IS
    THE ONE THAT SAYS SO: every call site on ``main`` omits both keywords,
    and omitting them must answer exactly as this module answered before
    they existed.  That control is not a formality -- it is the whole
    safety argument for landing this half before chief's call-site lines.

    WHAT IS DELIBERATELY NOT ASSERTED: that the shop opens once rather than
    twice.  This module cannot write a latch back and does not try; it
    NAMES what it spent in ``latches_spent`` and the call site sets it.
    The once-ness is therefore chief's line to prove on a boot, not this
    file's to claim -- see ``SHOP_AND_QUEST_LATCH_WIRING``.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()
        cls.placements = responder_mod._placements_by_index(cls.legacy)
        cls.population_indices = tuple(sorted(cls.placements))

    def _shop_index(self):
        idx = self.legacy.V112_SHOP_TRIGGER_INDEX
        if idx not in self.placements:
            self.fail(
                "the shop trigger is expected to be answerable from this "
                "responder's own table -- the module docstring's cost "
                "table depends on it being reachable"
            )
        return idx

    def _quest_placement(self):
        """The quest actor is NOT a key of the placement table (pf-adversary
        ``yjjtyn`` D4), so its arm is exercised with a placement object
        carrying the frozen P0 identity rather than by clicking it.  Doing
        it this way is the honest shape: the arm is unreachable from
        ``respond()`` today and this test does not pretend otherwise."""
        return types.SimpleNamespace(
            actor_identity=self.legacy.V129_QUEST_ACTOR_ID,
        )

    def test_omitting_both_keywords_is_byte_identical_to_before(self):
        """``None`` means "the call site never told us", which is every
        call site today, and it must not compose a once-per-session action
        on a boot that cannot record it."""
        legacy = self.legacy
        shop_idx = self._shop_index()
        for kwargs in ({}, {"vendor_open_latch_spent": None}):
            with self.subTest(kwargs=kwargs):
                extras, reason, latches = responder_mod._conversation_extra(
                    legacy, self.placements[shop_idx], shop_idx, PORT_ROYAL,
                    **kwargs,
                )
                self.assertEqual(extras, ())
                self.assertEqual(
                    reason, "no_extra_shop_trigger_needs_session_latch")
                self.assertEqual(latches, ())

    def test_an_unspent_shop_latch_composes_the_frozen_trade_zoom(self):
        legacy = self.legacy
        shop_idx = self._shop_index()
        extras, reason, latches = responder_mod._conversation_extra(
            legacy, self.placements[shop_idx], shop_idx, PORT_ROYAL,
            vendor_open_latch_spent=False,
        )
        self.assertEqual(len(extras), 1)
        label, pc, frame, delay = extras[0]
        self.assertEqual(
            label,
            "V112_TEST_HARNESS_TRADE_ZOOM_STORE5_SWORD_SOUL_VIA_LANE_A",
        )
        self.assertEqual(delay, 0.0)
        expected_pc, expected_frame = legacy.make_trade_zoom_store5()
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)
        self.assertEqual(reason, "shop_trigger_trade_zoom_store5")
        self.assertEqual(latches, ("shop_store5_open_sent",))

    def test_the_trade_zoom_is_called_not_copied(self):
        """Same rule the talk trigger follows: compose by CALLING the
        frozen builder, never from a copy of its bytes, so the day the
        frozen body changes this answer changes with it."""
        legacy = self.legacy
        shop_idx = self._shop_index()
        sentinel = (b"sentinel-pc", b"sentinel-frame")
        real = legacy.make_trade_zoom_store5
        legacy.make_trade_zoom_store5 = lambda: sentinel
        try:
            extras, reason, latches = responder_mod._conversation_extra(
                legacy, self.placements[shop_idx], shop_idx, PORT_ROYAL,
                vendor_open_latch_spent=False,
            )
        finally:
            legacy.make_trade_zoom_store5 = real
        self.assertEqual(extras[0][1], sentinel[0])
        self.assertEqual(extras[0][2], sentinel[1])
        self.assertEqual(latches, ("shop_store5_open_sent",))

    def test_a_spent_shop_latch_composes_nothing_under_its_own_reason(self):
        """The frozen loop records
        ``v112_store5_duplicate_open_suppressed`` rather than re-opening
        the store, and a capture must be able to tell that from "never
        told"."""
        legacy = self.legacy
        shop_idx = self._shop_index()
        extras, reason, latches = responder_mod._conversation_extra(
            legacy, self.placements[shop_idx], shop_idx, PORT_ROYAL,
            vendor_open_latch_spent=True,
        )
        self.assertEqual(extras, ())
        self.assertEqual(
            reason, "no_extra_shop_trigger_already_open_this_session")
        self.assertEqual(latches, ())

    def test_a_refusing_trade_zoom_builder_costs_the_extra_not_the_answer(self):
        legacy = self.legacy
        shop_idx = self._shop_index()
        real = legacy.make_trade_zoom_store5

        def _boom():
            raise RuntimeError("frozen builder refused")

        legacy.make_trade_zoom_store5 = _boom
        try:
            extras, reason, latches = responder_mod._conversation_extra(
                legacy, self.placements[shop_idx], shop_idx, PORT_ROYAL,
                vendor_open_latch_spent=False,
            )
        finally:
            legacy.make_trade_zoom_store5 = real
        self.assertEqual(extras, ())
        self.assertEqual(
            reason, "no_extra_shop_builder_refused_RuntimeError")
        # A latch that was never spent must never be reported as spent:
        # the call site would set it and the shop would stay shut for the
        # rest of the session on the strength of an action nobody sent.
        self.assertEqual(latches, ())

    def test_an_unspent_quest_latch_composes_the_frozen_q3020(self):
        legacy = self.legacy
        quest_idx = legacy.V129_QUEST_ACTOR_INDEX
        extras, reason, latches = responder_mod._conversation_extra(
            legacy, self._quest_placement(), quest_idx, PORT_ROYAL,
            mission_dialog_latch_spent=False,
        )
        self.assertEqual(len(extras), 1)
        label, pc, frame, delay = extras[0]
        self.assertEqual(
            label, "V134_P0_Q3020_NPC_CONVERSATION_ONCE_VIA_LANE_A")
        expected_pc, expected_frame = legacy.make_npc_conversation_quest3020(
            legacy.V129_QUEST_ACTOR_ID,
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)
        self.assertEqual(reason, "quest_actor_conversation_q3020")
        self.assertEqual(latches, ("quest3020_conversation_sent",))

    def test_the_quest_builder_refuses_any_identity_but_p0_and_that_is_named(
            self):
        """The frozen builder raises ``ValueError`` for any identity but
        P0's (v141:791-794).  This arm is keyed on the frozen INDEX, so a
        boot whose placement table gives index 0 some other identity
        reaches it -- and must lose the extra, not the answer, and not the
        listener thread."""
        legacy = self.legacy
        wrong = types.SimpleNamespace(
            actor_identity=legacy.V129_QUEST_ACTOR_ID + 1,
        )
        extras, reason, latches = responder_mod._conversation_extra(
            legacy, wrong, legacy.V129_QUEST_ACTOR_INDEX, PORT_ROYAL,
            mission_dialog_latch_spent=False,
        )
        self.assertEqual(extras, ())
        self.assertEqual(reason, "no_extra_quest_builder_refused_ValueError")
        self.assertEqual(latches, ())

    def test_a_spent_quest_latch_composes_nothing_and_never_an_empty_one(self):
        """Composing the EMPTY conversation in place of a spent quest
        conversation would replace a quest window with a blank one, which
        the module docstring calls worse than the gap."""
        legacy = self.legacy
        real = legacy.make_npc_conversation_empty

        def _must_not_run(actor_identity):
            raise AssertionError("the quest arm must never compose the empty "
                                 "conversation")

        legacy.make_npc_conversation_empty = _must_not_run
        try:
            extras, reason, latches = responder_mod._conversation_extra(
                legacy, self._quest_placement(),
                legacy.V129_QUEST_ACTOR_INDEX, PORT_ROYAL,
                mission_dialog_latch_spent=True,
            )
        finally:
            legacy.make_npc_conversation_empty = real
        self.assertEqual(extras, ())
        self.assertEqual(
            reason, "no_extra_quest_actor_already_sent_this_session")
        self.assertEqual(latches, ())

    def test_respond_carries_the_latch_name_and_the_console_says_so(self):
        """End to end through ``respond()``: a click on the shop trigger
        with the session saying "not opened yet" answers with the face
        pair, the trade-zoom in ``extra_actions``, and the latch the call
        site owes in ``latches_spent``."""
        legacy = self.legacy
        shop_idx = self._shop_index()
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + shop_idx + 1,),
            population_indices=self.population_indices,
            last_target_pos=None,
            vendor_open_latch_spent=False,
        )
        self.assertIsNotNone(answer)
        self.assertEqual(answer.latches_spent, ("shop_store5_open_sent",))
        self.assertEqual(len(answer.extra_actions), 1)
        self.assertEqual(
            answer.extra_actions[0][0],
            "V112_TEST_HARNESS_TRADE_ZOOM_STORE5_SWORD_SOUL_VIA_LANE_A",
        )
        self.assertIn("extra_reason=shop_trigger_trade_zoom_store5",
                      answer.console_lines[0])
        self.assertIn("latches=shop_store5_open_sent",
                      answer.console_lines[0])

    def test_respond_without_the_keyword_spends_nothing_and_says_none(self):
        """The control for the test above, and the one that pins what
        ``main``'s call sites get today."""
        legacy = self.legacy
        shop_idx = self._shop_index()
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + shop_idx + 1,),
            population_indices=self.population_indices,
            last_target_pos=None,
        )
        self.assertIsNotNone(answer)
        self.assertEqual(answer.latches_spent, ())
        self.assertEqual(answer.extra_actions, ())
        self.assertIn("extra_reason=no_extra_shop_trigger_needs_session_latch",
                      answer.console_lines[0])
        self.assertIn("latches=none", answer.console_lines[0])

    def test_the_wiring_the_lane_cannot_write_is_spelled_out_verbatim(self):
        """The undone half is chief's, and a named ask is the difference
        between a handoff and a hope.  Both lines must be in the constant,
        and the constant must say why (2) is not optional."""
        wiring = responder_mod.VENDOR_AND_MISSION_LATCH_WIRING
        self.assertIn("vendor_open_latch_spent=self.shop_store5_open_sent",
                      wiring)
        self.assertIn(
            "mission_dialog_latch_spent=self.quest3020_conversation_sent",
            wiring)
        self.assertIn("for _latch in response.latches_spent:", wiring)
        self.assertIn("WITHOUT (2), (1) IS A REGRESSION AND NOT A GAIN.",
                      wiring)

    def test_the_wiring_names_keywords_respond_really_has(self):
        """pf-adversary ``rlymq1`` D2, and the test that finding needed.

        The neighbouring wiring constant pairs a keyword with an attribute
        of the SAME name; this one cannot, because chief's code-name guard
        forbids this lane binding his words.  So the constant is the only
        place the two spellings are joined, ``**_ignored`` cannot refuse a
        wrong one, and a one-character slip in that constant would be a
        silent no-op.  Asserting the constant CONTAINS a string is not
        enough -- the string has to be a parameter this function really
        takes."""
        parameters = inspect.signature(responder_mod.respond).parameters
        wiring = responder_mod.VENDOR_AND_MISSION_LATCH_WIRING
        for keyword in ("vendor_open_latch_spent",
                        "mission_dialog_latch_spent"):
            with self.subTest(keyword=keyword):
                self.assertIn(keyword, parameters)
                self.assertIn(f"{keyword}=self.", wiring)

    def test_the_latch_names_the_lane_reports_are_the_frozen_ones(self):
        """``latches_spent`` is consumed by ``setattr`` on the frozen state
        object, so these two strings are the one thing in this round that
        must NOT be renamed for the guard: a lane word here would set a
        flag v141 does not have, with every test still green."""
        fields = {
            field.name
            for field in dataclasses.fields(self.legacy.GameSessionState)
        }
        for attr in responder_mod._FROZEN_LATCH_ATTRS:
            with self.subTest(attr=attr):
                self.assertIn(attr, fields)

    def test_a_latch_passed_under_the_frozen_spelling_is_shouted_about(self):
        """The failure D2 measured: chief writes the symmetric line, the
        keyword lands in ``**_ignored``, and nothing anywhere differs from
        an unwired boot.  It differs now, on the console line."""
        legacy = self.legacy
        shop_idx = self._shop_index()
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + shop_idx + 1,),
            population_indices=self.population_indices,
            last_target_pos=None,
            **{responder_mod._VENDOR_LATCH_ATTR: False},
        )
        self.assertIsNotNone(answer)
        # The click still answers, and still answers as an unwired boot
        # would -- the point is that the console no longer says so alone.
        self.assertEqual(answer.extra_actions, ())
        self.assertEqual(answer.latches_spent, ())
        self.assertIn(
            f"latch_kwarg_misnamed={responder_mod._VENDOR_LATCH_ATTR}",
            answer.console_lines[0],
        )

    def test_an_ordinary_click_says_nothing_about_misnamed_keywords(self):
        """A field that is always present and almost always empty is a
        field nobody reads by the second boot, so this one appears only
        when there is something to say."""
        legacy = self.legacy
        shop_idx = self._shop_index()
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + shop_idx + 1,),
            population_indices=self.population_indices,
            last_target_pos=None,
            mob_loot_cell=None,
        )
        self.assertNotIn("latch_kwarg_misnamed", answer.console_lines[0])

    def test_other_ignored_keywords_are_left_alone(self):
        """The call site legitimately passes keywords this responder does
        not want; shouting about those would drown the one that matters."""
        legacy = self.legacy
        shop_idx = self._shop_index()
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + shop_idx + 1,),
            population_indices=self.population_indices,
            last_target_pos=None,
            mob_combat_ledger=object(),
            mob_death_register=object(),
        )
        self.assertNotIn("latch_kwarg_misnamed", answer.console_lines[0])


if __name__ == "__main__":
    unittest.main()
