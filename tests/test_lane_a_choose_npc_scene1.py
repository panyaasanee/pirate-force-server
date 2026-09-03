"""LANE-A's ChooseNPC responder for scene 1 (Port Royal / bg0001).

Built round `yfbqmg` companion (2026-09-01), answering PANYA-ORDER
``pf_bridge/notes_to_chief/20260901_0955_PANYA-ORDER-login-path-must-ship-
the-census-eagerly-like-the-warp-path-now-does.md``.  ~~``production_allowed``
is ``False`` on ``main`` today (see the module's own docstring, "WHY THE
GATE STAYS CLOSED THIS ROUND")~~ -- AMENDED ROUND ``zqmosn``: still False,
but for the MEASURED reason that docstring now leads with rather than the
circular one it carried.  These tests drive ``respond()`` directly, the same
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

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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
    gate's original, circular reason; the measurement is driven in
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
        rather than asserted: v141's own loop skips
        ``V112_MONSTER_INDEX`` with ``v112_choose_p30_usage1_no_npc_
        response`` and sends nothing, so a click there is silence today.
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
        single-frame response would do today."""
        labels = self._labels_for_click("tok-scene1-talk", 1)
        self.assertIn("V98_NPC_CONVERSATION_DEFAULT_P1", labels)
        self.assertGreater(
            len(labels), 1,
            "an answer to a scene-1 click is not one action; if this ever "
            "becomes one, re-read the module docstring before flipping the "
            "gate",
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
        """The structural half of the reason, read off the response object
        rather than asserted in prose: there is one ``pc`` and one
        ``frame``, so no composition inside ``respond()`` can emit the two
        actions above.  runtime.py's own call-site comment names the fix
        and its owner -- "needs ``ChooseNpcResponse`` to become a
        collection ... a ``lane_hooks``/lane_a design change"."""
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


if __name__ == "__main__":
    unittest.main()
