"""CORE-REQUEST-014: ``columbus_quest_dispatch`` proved OFFLINE.

Companion to ``tests/test_columbus_quest_dispatch_wiring.py``, which drives
the real ``make_state_class`` dispatcher end to end.  This file proves the
module's own functions in isolation, the same split
``tests/test_world_scene_liveness.py`` / ``..._wiring.py`` already uses.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import columbus_quest_dispatch, population
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.world_scene_entry import SceneEntryRefused

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class ColumbusActorIdentityTests(unittest.TestCase):
    def test_matches_the_same_formula_the_census_itself_uses(self):
        legacy = _legacy()
        identity = columbus_quest_dispatch.columbus_actor_identity(legacy)
        # 0x2000 + placement_index(1) + 1, same formula as
        # population.SceneActorPlacement.actor_identity.
        self.assertEqual(identity, 0x2002)
        placements = population.load_port_royal_placements(legacy)
        by_index = {p.placement_index: p for p in placements}
        self.assertEqual(
            identity, by_index[columbus_quest_dispatch.COLUMBUS_PLACEMENT_INDEX]
            .actor_identity,
        )

    def test_raises_a_named_error_when_the_census_ships_no_such_index(self):
        with mock.patch.object(
            columbus_quest_dispatch.population,
            "load_port_royal_placements",
            return_value=(),
        ):
            with self.assertRaises(columbus_quest_dispatch.ColumbusActorNotFound):
                columbus_quest_dispatch.columbus_actor_identity(_legacy())


class MakeColumbusConversationTests(unittest.TestCase):
    def test_matches_the_general_wire_shape_re094_pinned(self):
        legacy = _legacy()
        pc, frame = columbus_quest_dispatch.make_columbus_conversation(
            legacy, 0x2002,
        )
        expected_payload = (
            legacy.qwordtag(0x32, 0x2002)
            + legacy.u16tag(0x0F, 1)
            + legacy.u16tag(0x12, 3021)
            + legacy.u8tag(0x08, 0)
        )
        expected_pc, expected_frame = legacy.make_runtime_vitals(
            [(legacy.NPC_CONVERSATION, 0, expected_payload)]
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)
        self.assertEqual(frame, legacy.frame_pc(pc))

    def test_refuses_a_non_positive_actor_identity(self):
        with self.assertRaises(ValueError):
            columbus_quest_dispatch.make_columbus_conversation(_legacy(), 0)

    def test_carries_3021_not_3023_the_earlier_status_letter_mistake(self):
        """Regression pin for the exact mix-up
        notes_to_chief/20260827_1052_LANE-A-CORRECTION-... corrected."""
        legacy = _legacy()
        pc, _frame = columbus_quest_dispatch.make_columbus_conversation(
            legacy, 0x2002,
        )
        self.assertIn(legacy.u16tag(0x12, 3021), pc)
        self.assertNotIn(legacy.u16tag(0x12, 3023), pc)


class MatchesColumbusDispatchTests(unittest.TestCase):
    def _fields(self, **overrides):
        base = {
            "quest_id": 3021,
            "field_u8_16": 1,
            "field_u8_17": 0,
            "field_u32_18": 0,
            "field_qword_20": 0,
            "field_u8_28": 0,
        }
        base.update(overrides)
        return base

    def test_matches_op1_quest_3021(self):
        self.assertTrue(
            columbus_quest_dispatch.matches_columbus_dispatch(self._fields())
        )

    def test_ignores_a_different_quest_id(self):
        self.assertFalse(columbus_quest_dispatch.matches_columbus_dispatch(
            self._fields(quest_id=3020)
        ))

    def test_ignores_a_different_operation(self):
        self.assertFalse(columbus_quest_dispatch.matches_columbus_dispatch(
            self._fields(field_u8_16=2)
        ))

    def test_does_not_gate_on_the_fields_re094_could_only_call_opaque(self):
        """RE-094's own result criticised the existing 3020 lane's exact-
        tuple match for leaving "no room for another NPC/quest" -- this
        proves the Columbus match does not repeat that over-narrowing onto
        fields RE-094 never proved the meaning of."""
        self.assertTrue(columbus_quest_dispatch.matches_columbus_dispatch(
            self._fields(field_u32_18=999, field_qword_20=12345, field_u8_28=7)
        ))

    def test_rejects_a_non_dict(self):
        self.assertFalse(columbus_quest_dispatch.matches_columbus_dispatch(None))


class ResolveColumbusArrivalTests(unittest.TestCase):
    def test_refuses_today_because_scene_17_has_no_pinned_spawn(self):
        """The exact, currently-open gap this module's docstring names:
        scenarios/world_scene_registry_001.json's scene-17 entry carries
        spawn=null (Bg1001.placements.tsv has no player-arrival marker)."""
        with self.assertRaises(SceneEntryRefused) as ctx:
            columbus_quest_dispatch.resolve_columbus_arrival(emit=lambda line: None)
        self.assertEqual(ctx.exception.reason, "scene_has_no_pinned_spawn")


class DispatchColumbusQuest3021Tests(unittest.TestCase):
    def test_always_refuses_today_with_both_named_reasons(self):
        with self.assertRaises(
            columbus_quest_dispatch.ColumbusDispatchRefused
        ) as ctx:
            columbus_quest_dispatch.dispatch_columbus_quest3021(
                emit=lambda line: None,
            )
        self.assertEqual(
            ctx.exception.reasons,
            (
                "scene17_teleport_refused_scene_has_no_pinned_spawn",
                columbus_quest_dispatch.VEHICLE_BIND_REFUSED_NO_VEHICLE_ROW,
            ),
        )

    def test_never_partially_applies(self):
        """No side effect this module could observe (no frame composed, no
        registry mutated) survives the refusal -- there is nothing here to
        assert BESIDES the raise, which is itself the assertion: a compound
        action that partially applied would have something else to check."""
        try:
            columbus_quest_dispatch.dispatch_columbus_quest3021(
                emit=lambda line: None,
            )
        except columbus_quest_dispatch.ColumbusDispatchRefused:
            pass
        else:
            self.fail("dispatch_columbus_quest3021 must refuse today")


if __name__ == "__main__":
    unittest.main()
