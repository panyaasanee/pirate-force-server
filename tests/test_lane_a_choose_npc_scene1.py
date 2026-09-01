"""LANE-A's ChooseNPC responder for scene 1 (Port Royal / bg0001).

Built round `yfbqmg` companion (2026-09-01), answering PANYA-ORDER
``pf_bridge/notes_to_chief/20260901_0955_PANYA-ORDER-login-path-must-ship-
the-census-eagerly-like-the-warp-path-now-does.md``.  ``production_allowed``
is ``False`` on ``main`` today (see the module's own docstring, "WHY THE
GATE STAYS CLOSED THIS ROUND") -- these tests drive ``respond()`` directly,
the same "responder's own logic, independent of the still-widening runtime.py
trigger" split ``test_lane_a_choose_npc_scene14.py`` uses for its own module.
A real-dispatcher, end-to-end test (mirroring that file's
``TheGuardAnsweredTheClickInsteadOfCrashingTests``) is deferred to the round
that flips this module's gate, once the login trigger widen has landed --
see this round's own ``rounds/`` entry and the CORE-REQUEST letter for why
the two steps are kept apart.
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
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_port_royal_identity as identity  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_choose_npc_scene1 as responder_mod,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

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
    ``_gate_module``/``_withdraw`` -- "A module that does not set
    ``production_allowed = True`` has every hook it registered withdrawn
    again right after import"), so scene 1's slot in the real, process-wide
    registry is EMPTY today -- unlike scene 14's module, whose default is
    ``True``.  That is the correct, intended state while this gate stays
    closed (module docstring, "WHY THE GATE STAYS CLOSED THIS ROUND");
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
    """See the module docstring's "WHY THE GATE STAYS CLOSED THIS ROUND":
    two independent reasons, either sufficient alone.  This flag is a
    convention marker every ``lane_hooks`` module in this project uses the
    same way (``module_production_allowed``); it is not a scenario flag and
    this lane's charter still forbids one -- flipping it is this lane's own
    call in a later round, not a CORE-REQUEST."""

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
        if monster_idx not in self.population_indices:
            self.skipTest("P30 has no shippable identity in this table")
        actor_identity = 0x2000 + monster_idx + 1
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(actor_identity,),
            population_indices=self.population_indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
        )
        self.assertIsNotNone(answer)
        placement = self.placements[monster_idx]
        monster_body = legacy.make_npc_attr(
            identity.resolve(placement.template_id).mobs_n_id,
            placement.actor_identity, PORT_ROYAL, 0,
            identity.resolve(placement.template_id).outfit,
            current_hp=legacy.V117_P30_EXACT_HP,
            max_hp=legacy.V117_P30_EXACT_HP,
            basic_name=identity.resolve(placement.template_id).name,
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


if __name__ == "__main__":
    unittest.main()
