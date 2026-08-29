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

import copy
import dataclasses

from pirateforce_foundation import (
    columbus_quest_dispatch,
    population,
    world_population,
    world_scene_travel,
)
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


class MakeColumbusConversationTwoOptionsTests(unittest.TestCase):
    """Option 2 (quest 3205, Q_BORNAGAIN), added 2026-08-27 per
    COO-DECISION-M2-not-closed and GT-106 (4).1 -- purely additive: proves
    the two-option descriptor carries BOTH quests, and that the pre-existing
    single-option encoder is untouched byte-for-byte alongside it."""

    def test_carries_both_quest_ids_with_entry_count_two(self):
        legacy = _legacy()
        pc, frame = columbus_quest_dispatch.make_columbus_conversation_two_options(
            legacy, 0x2002,
        )
        expected_payload = (
            legacy.qwordtag(0x32, 0x2002)
            + legacy.u16tag(0x0F, 2)
            + legacy.u16tag(0x12, 3021)
            + legacy.u8tag(0x08, 0)
            + legacy.u16tag(0x12, 3205)
            + legacy.u8tag(0x08, 0)
        )
        expected_pc, expected_frame = legacy.make_runtime_vitals(
            [(legacy.NPC_CONVERSATION, 0, expected_payload)]
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)
        self.assertEqual(frame, legacy.frame_pc(pc))

    def test_entry_count_byte_is_two_not_one(self):
        legacy = _legacy()
        pc, _frame = columbus_quest_dispatch.make_columbus_conversation_two_options(
            legacy, 0x2002,
        )
        self.assertIn(legacy.u16tag(0x0F, 2), pc)
        self.assertNotIn(legacy.u16tag(0x0F, 1), pc)

    def test_refuses_a_non_positive_actor_identity(self):
        with self.assertRaises(ValueError):
            columbus_quest_dispatch.make_columbus_conversation_two_options(
                _legacy(), 0,
            )

    def test_single_option_encoder_is_still_byte_for_byte_unchanged(self):
        """The regression this whole file exists to prevent: adding option 2
        must not alter what ``make_columbus_conversation`` (the pre-existing
        single-option encoder) emits for the exact same call it always
        answered."""
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

    def test_still_matches_quest_3021_with_the_new_optional_quest_id_param(self):
        """The generalisation that added a ``quest_id`` parameter (for option
        2's reuse below) must not change the default-argument behaviour any
        pre-existing 1-argument call site relies on."""
        self.assertTrue(columbus_quest_dispatch.matches_columbus_dispatch(
            self._fields(quest_id=3021),
        ))
        self.assertFalse(columbus_quest_dispatch.matches_columbus_dispatch(
            self._fields(quest_id=3205),
        ))


class MatchesColumbusBornagainDispatchTests(unittest.TestCase):
    """Option 2 / quest 3205 (Q_BORNAGAIN) dispatch-acceptance gate, added
    2026-08-27 -- the "dispatch acceptance for quest_id 3205" proof: this
    class proves the gate ACCEPTS a decoded op1/3205 frame and rejects
    everything that op1/3021's own gate would also reject."""

    def _fields(self, **overrides):
        base = {
            "quest_id": 3205,
            "field_u8_16": 1,
            "field_u8_17": 0,
            "field_u32_18": 0,
            "field_qword_20": 0,
            "field_u8_28": 0,
        }
        base.update(overrides)
        return base

    def test_accepts_op1_quest_3205(self):
        self.assertTrue(
            columbus_quest_dispatch.matches_columbus_bornagain_dispatch(
                self._fields(),
            )
        )

    def test_ignores_quest_3021_the_other_option(self):
        self.assertFalse(
            columbus_quest_dispatch.matches_columbus_bornagain_dispatch(
                self._fields(quest_id=3021),
            )
        )

    def test_ignores_a_different_operation(self):
        self.assertFalse(
            columbus_quest_dispatch.matches_columbus_bornagain_dispatch(
                self._fields(field_u8_16=2),
            )
        )

    def test_rejects_a_non_dict(self):
        self.assertFalse(
            columbus_quest_dispatch.matches_columbus_bornagain_dispatch(None)
        )


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


class LoginPathStaysRefusedTests(unittest.TestCase):
    """Round 0z3kjx, pf-adversary-flagged regression, proven from THIS
    module's own vantage point rather than only world_scene_entry's: the
    decree that lets ``resolve_columbus_arrival`` succeed above must not
    also let a character's own persisted row walk into scene 17 through the
    exact same login call runtime.py makes.
    """

    def test_a_persisted_scene_17_row_is_refused_at_the_plain_login_call(self):
        from pirateforce_foundation import world_scene_entry
        from pirateforce_foundation.model import Position

        persisted_row = Position(17, 0, 1.0, 2.0, 3.0, 0.5)
        with self.assertRaises(world_scene_entry.SceneEntryRefused) as caught:
            # No via_login keyword - exactly runtime.py's login call shape.
            world_scene_entry.resolve_entry(persisted_row, emit=lambda line: None)
        self.assertEqual(
            caught.exception.reason,
            world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN,
        )

    def test_resolve_columbus_arrival_still_succeeds_despite_that_refusal(self):
        # The two facts side by side: the same scene, the same registry, one
        # call refuses and the other succeeds, because only one of them is
        # reading a character's persisted row.
        from pirateforce_foundation import world_scene_entry
        from pirateforce_foundation.model import Position

        with self.assertRaises(world_scene_entry.SceneEntryRefused):
            world_scene_entry.resolve_entry(
                Position(17, 0, 1.0, 2.0, 3.0, 0.5), emit=lambda line: None,
            )
        entry = columbus_quest_dispatch.resolve_columbus_arrival(
            emit=lambda line: None,
        )
        self.assertEqual(entry.destination.n_id, 17)


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

    def test_quest_3021_dispatch_is_unaffected_by_the_option_2_addition(self):
        """Regression pin the round handoff promises: option 2 (quest 3205)
        is purely additive, so quest 3021's OWN dispatch outcome -- success,
        the returned SceneEntry's XYZ, and the exact tokens it emits -- must
        be provably unchanged from before this round's addition."""
        lines = []
        entry = columbus_quest_dispatch.dispatch_columbus_quest3021(
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
        # ROUND 2pdf6j MOVED THIS ASSERTION BY ONE AND KEPT IT EXACT.  The
        # dispatch's own decision line is unchanged, byte for byte, and is
        # still the LAST decision this function prints; what follows it now
        # is one report line about who the client is still holding at the
        # landing point (see ``_emit_arrival_stowaways``).  Weakening this
        # to ``assertIn`` would have hidden a future line inserted BETWEEN
        # the decision and the report, so the position is still pinned -
        # against the report, which the next assertion pins too.
        self.assertEqual(
            lines[-2],
            "COLUMBUS_QUEST3021_NO_VEHICLE_DISPATCH scene=17 source="
            + columbus_quest_dispatch.M2_NO_VEHICLE_TAG,
        )
        self.assertTrue(lines[-1].startswith("WORLD_POP_STOWAWAYS "), lines)
        self.assertEqual(len(lines), 4, lines)


class DispatchColumbusQuest3205Tests(unittest.TestCase):
    """Option 2 (quest 3205, Q_BORNAGAIN) dispatch, added 2026-08-27.  Unlike
    quest 3021, this refuses every time TODAY -- see the function's own
    docstring for the two evidence gaps (no persisted marker/respawn column,
    no captured wire ack) neither of which a static tree can close."""

    def test_refuses_with_the_named_no_persistence_reason(self):
        lines = []
        with self.assertRaises(
            columbus_quest_dispatch.ColumbusDispatchRefused
        ) as ctx:
            columbus_quest_dispatch.dispatch_columbus_quest3205(
                emit=lines.append,
            )
        self.assertEqual(
            ctx.exception.reasons,
            (
                columbus_quest_dispatch
                .BORNAGAIN_MARKER_RESET_REFUSED_NO_PERSISTENCE_ROW,
            ),
        )
        self.assertIn(
            "COLUMBUS_QUEST3205_BORNAGAIN_REFUSED reason="
            + columbus_quest_dispatch
            .BORNAGAIN_MARKER_RESET_REFUSED_NO_PERSISTENCE_ROW,
            lines,
        )

    def test_does_not_raise_the_quest_3021_exception_type_by_accident(self):
        """Both quests share the SAME ColumbusDispatchRefused type on
        purpose (see the function's own docstring) -- this proves that
        sharing is deliberate reuse, not one dispatch accidentally catching
        the other's error."""
        with self.assertRaises(columbus_quest_dispatch.ColumbusDispatchRefused):
            columbus_quest_dispatch.dispatch_columbus_quest3205(
                emit=lambda line: None,
            )


class ArrivalStowawayReportTests(unittest.TestCase):
    """The one line round 2pdf6j added to this live, flagless dispatch.

    It is a REPORT.  Every test here checks that it says something true and
    that it cannot reach the return value or the caller - never that it
    changes what goes on the wire, because it does not.
    """

    def _dispatch(self, **kwargs):
        lines = []
        entry = columbus_quest_dispatch.dispatch_columbus_quest3021(
            emit=lines.append, **kwargs)
        return entry, lines

    def _stowaway_line(self, lines):
        found = [line for line in lines if line.startswith("WORLD_POP_STOWAWAYS")]
        self.assertEqual(len(found), 1, lines)
        return found[0]

    def test_the_call_site_as_it_stands_today_says_so_out_loud(self):
        entry, lines = self._dispatch()
        line = self._stowaway_line(lines)
        self.assertIn("unmeasured", line)
        self.assertIn("reason=call_site_passed_no_legacy", line)
        # The anchor is real even when the membership is not, so the line is
        # still evidence of WHERE the boat lands.
        self.assertIn("anchor=(0.000,0.000,0.000)", line)
        self.assertIsNotNone(entry)

    def _census_membership(self):
        """What ``self.world_census_indices`` actually holds at the call site.

        The first draft of this test built the membership from the frozen
        TABLE (115 rows) and pinned ``held=115`` - a line the requested
        one-token change can never print, because the census ships 108 of
        those rows (pf-adversary, round 2pdf6j, D3).  Built the way the
        login path builds it now, so this test proves the change it is
        named for.
        """
        return tuple(
            world_population.build_world_population(
                _legacy(), (0.0, 0.0, 0.0), scene_id=1,
            ).indices
        )

    def test_with_the_one_token_change_it_names_them(self):
        legacy = _legacy()
        membership = self._census_membership()
        self.assertEqual(len(membership), 108)
        entry, lines = self._dispatch(legacy=legacy, held_indices=membership)
        line = self._stowaway_line(lines)
        self.assertIn("held=108", line)
        self.assertIn("within=4", line)
        self.assertIn("radius=2000.0", line)
        self.assertIn("nearest=Legend_Jack@1226.6", line)
        self.assertIsNotNone(entry)

    def test_the_line_reports_where_the_boat_actually_lands(self):
        """The anchor comes from the entry, and moving the entry moves it.

        pf-adversary (round 2pdf6j, D5) mutated the anchor read to a
        hardcoded ``(0, 0, 0)`` and every test still passed, because the
        only destination this dispatch produces today IS the origin.  This
        drives the dispatch with a registry whose scene-17 spawn is
        somewhere else, so the plumbing is pinned rather than assumed - the
        exact case that arrives the day the owner's provisional decree is
        replaced by a measured spawn.
        """
        legacy = _legacy()
        registry = world_scene_travel.load_scene_registry()
        moved = copy.deepcopy(registry)
        rows = [
            dataclasses.replace(row, spawn=(111.0, 222.0, 333.0))
            if row.n_id == 17 else row
            for row in moved.destinations
        ]
        moved = dataclasses.replace(moved, destinations=tuple(rows))
        entry, lines = self._dispatch(
            registry=moved, legacy=legacy,
            held_indices=self._census_membership(),
        )
        line = self._stowaway_line(lines)
        self.assertIn("anchor=(111.000,222.000,333.000)", line)
        self.assertNotIn("anchor=(0.000,0.000,0.000)", line)
        # and the crowd it names changes with the landing point
        self.assertNotIn("nearest=Legend_Jack@1226.6", line)

    def test_the_report_cannot_change_what_the_dispatch_returns(self):
        legacy = _legacy()
        plain, _ = self._dispatch()
        reported, _ = self._dispatch(legacy=legacy, held_indices=(0, 1))
        self.assertEqual(plain.teleport_fields, reported.teleport_fields)

    def test_a_broken_membership_is_reported_not_raised(self):
        legacy = _legacy()
        entry, lines = self._dispatch(legacy=legacy, held_indices="115")
        self.assertIn("unmeasured", self._stowaway_line(lines))
        self.assertIsNotNone(entry)

    def test_an_emit_that_is_asked_for_junk_still_gets_one_line(self):
        """The anchor half can fail too, and it fails to a printed line."""
        lines = []
        columbus_quest_dispatch._emit_arrival_stowaways(
            object(), legacy=None, held_indices=None, emit=lines.append)
        self.assertEqual(len(lines), 1)
        self.assertIn("reason=no_arrival_anchor:", lines[0])

    def test_every_line_this_dispatch_prints_survives_the_bridge_console(self):
        legacy = _legacy()
        membership = tuple(
            placement.placement_index
            for placement in population.load_port_royal_placements(legacy)
        )
        for kwargs in ({}, {"legacy": legacy, "held_indices": membership}):
            _, lines = self._dispatch(**kwargs)
            for line in lines:
                line.encode("ascii")
                line.encode("cp874")


if __name__ == "__main__":
    unittest.main()
