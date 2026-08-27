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
    def test_succeeds_on_the_owner_decreed_provisional_spawn(self):
        """UPDATED PANYA-DECISION 2026-08-27T14:45+07:00: the owner decreed a
        PROVISIONAL scene-17 spawn (0,0,0), tagged PROVISIONAL-OWNER-DECREE-
        20260827-1445, in scenarios/world_scene_registry_001.json. This used
        to always raise SceneEntryRefused(scene_has_no_pinned_spawn); it now
        succeeds and world_scene_entry.resolve_entry prints the decree token,
        which this test also proves is not silently dropped."""
        lines = []
        entry = columbus_quest_dispatch.resolve_columbus_arrival(
            emit=lines.append,
        )
        self.assertEqual(
            (entry.position.x, entry.position.y, entry.position.z),
            (0.0, 0.0, 0.0),
        )
        self.assertIn(
            "SCENE_ENTRY scene=17 xyz=0.000,0.000,0.000 "
            "source=PROVISIONAL-OWNER-DECREE-20260827-1445",
            lines,
        )


class DispatchColumbusQuest3021Tests(unittest.TestCase):
    def test_succeeds_today_without_a_vehicle_bind(self):
        """UPDATED PANYA-DECISION 2026-08-27T15:25+07:00
        (M2-accept-scene17-entry-without-vehicle-fix-later): the owner
        accepted "arrive at scene 17 as an ordinary character" as M2's bar
        for today, tagged M2-NO-VEHICLE-OWNER-20260827-1525. The vehicle
        bind (RE-096's still-open gap) is no longer attempted at all, so
        this now succeeds and returns the SceneEntry instead of always
        raising ColumbusDispatchRefused."""
        lines = []
        entry = columbus_quest_dispatch.dispatch_columbus_quest3021(
            emit=lines.append,
        )
        self.assertEqual(
            (entry.position.x, entry.position.y, entry.position.z),
            (0.0, 0.0, 0.0),
        )
        self.assertIn(
            "COLUMBUS_QUEST3021_NO_VEHICLE_DISPATCH scene=17 source="
            + columbus_quest_dispatch.M2_NO_VEHICLE_TAG,
            lines,
        )

    def test_still_refuses_if_the_scene17_arrival_itself_refuses(self):
        # The one remaining failure mode: a registry with no scene-17 pin
        # (or no spawn) at all -- proven with a synthetic registry rather
        # than mutating the real shipped one.
        import json
        import tempfile
        from pathlib import Path
        from pirateforce_foundation import world_scene_travel

        data = json.loads(
            world_scene_travel.REGISTRY_PATH.read_text(encoding="ascii")
        )
        data["destinations"] = [
            row for row in data["destinations"] if row["n_id"] != 17
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "registry.json"
            path.write_text(json.dumps(data), encoding="ascii")
            registry = world_scene_travel.load_scene_registry(path)
        with self.assertRaises(
            columbus_quest_dispatch.ColumbusDispatchRefused
        ) as ctx:
            columbus_quest_dispatch.dispatch_columbus_quest3021(
                registry=registry, emit=lambda line: None,
            )
        self.assertEqual(
            ctx.exception.reasons,
            ("scene17_teleport_refused_scene_not_pinned",),
        )


if __name__ == "__main__":
    unittest.main()
