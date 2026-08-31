"""LANE-B: tests for src/pirateforce_foundation/mob_combat_bg0015_gates.py.

What each test is for, and what it deliberately does NOT claim:

``test_registering_bg0015_unwinds_the_first_swing`` is the headline: it
registers Bg0015 in-process and drives one real ActionVital in scene 14,
and the dispatch RAISES. That is a dropped connection, not a refusal.

``test_the_backing_check_reports_exactly_the_identities_it_is_not_given``
exercises the production cross-check with a set that is missing eleven of
the twelve identities, so the function must name those eleven. ACCEPTANCE
CRITERION recorded on purpose: stubbing ``splice_identities_missing_from``
to ``return ()`` must turn this test RED. An earlier draft's fabrication
test recomputed membership inline and never called the function at all --
stubbing it left 12 of 13 tests green.

``test_the_hand_typed_twelve_are_what_catches_a_small_shift`` records
honestly which check does the real work: the backing check cannot catch a
``+1`` placement shift (lane A ships 81 of 91 placements, so a shifted
identity usually lands on another real actor); the literal pin can.

``test_a_real_swing_in_scene_14_answers_not_a_field_mob`` pins what it
actually pins -- that scene 14 resolves to folder Bg0015 over an EMPTY
roster -- and the sibling assertion shows an arbitrary integer produces the
identical answer, so nobody reads it as identity-specific.
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from pirateforce_foundation import field_mob_hostile_bg0015 as hostile_bg0015
from pirateforce_foundation import field_mobs
from pirateforce_foundation import mob_ai_control
from pirateforce_foundation import mob_combat
from pirateforce_foundation import mob_combat_bg0015_gates as gates
from pirateforce_foundation import mob_death
from pirateforce_foundation import mob_scene_recompose
from pirateforce_foundation import world_population_bg0015
from pirateforce_foundation import world_scene_folder
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.store import SQLiteStore

MODULE_PATH = SRC / "pirateforce_foundation" / "mob_combat_bg0015_gates.py"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# The twelve identities Bg0015's own table produces under
# 0x2000 + placement + 1. LANE-A's letter 20260831_2007 CONFIRMED these
# against its own census -- it did not derive them independently (its own
# words: "12 placement index ที่สาย B ระบุ"), so this is a shared-formula
# cross-check, not two independent derivations. What IS independent is the
# two runtime paths: world_bg0015_identity._PLACEMENT_ROWS (lane A) and
# Bg0015's HOSTILE_PLACEMENTS (lane B) never import each other.
TWELVE_IDENTITIES = (
    0x2017, 0x2019, 0x201C, 0x201E, 0x2020, 0x202D,
    0x202E, 0x202F, 0x2030, 0x2034, 0x2047, 0x2058,
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _lane_a_census(legacy):
    return world_population_bg0015.build_bg0015_population(
        legacy, (0.0, 0.0, 0.0), world_population_bg0015.ROSTER_COUNT,
        scene_id=14,
        count_source=world_population_bg0015.COUNT_SOURCE_FULL_ROSTER,
    )


class Bg0015MeasurementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.legacy = _legacy()

    # ---- the cause of the unwind ------------------------------------

    def test_open_register_refuses_every_bg0015_row(self) -> None:
        self.assertEqual(
            gates.open_register_refusal_for_scene14(), "ai_row_missing")
        with self.assertRaises(mob_ai_control.MobAiControlError):
            mob_ai_control.open_register(
                hostile_bg0015.scene14_hostile_roster())

    def test_the_missing_ai_rows_are_named_not_summarised(self) -> None:
        report = gates.ai_rows_missing_for_scene14()
        self.assertEqual(report["mined_combat"], (214, 332, 350, 352))
        self.assertEqual(
            report["missing_combat"], (102, 134, 273, 301, 323, 333, 472))
        self.assertEqual(report["mined_wander"], (11, 16, 21))
        self.assertEqual(report["missing_wander"], (22,))

    # ---- the other measured preconditions ---------------------------

    def test_no_roster_and_no_death_ruling_today(self) -> None:
        self.assertFalse(gates.roster_gate_open())
        self.assertEqual(gates.scene14_roster_size_today(), 0)
        self.assertEqual(
            gates.templates_without_a_death_ruling(),
            (343, 345, 348, 350, 353, 355, 924))
        for mob in hostile_bg0015.scene14_hostile_roster():
            with self.assertRaises(mob_death.MobDeathContractError) as ctx:
                mob_death.ruling_for(mob)
            self.assertEqual(
                ctx.exception.reason, "target_outside_the_sanctioned_scope")

    def test_recompose_reports_both_halves_not_just_the_composer_table(
            self) -> None:
        status = gates.recompose_status()
        self.assertEqual(status["composer_scene_ids"], (1, 2))
        self.assertFalse(status["has_composer"])
        # The half an earlier draft missed: the hole is acknowledged in
        # writing, and that acknowledgement says the composer lands in the
        # same round the first roster row does -- downstream of
        # registration, not a separate choice someone can make first.
        self.assertTrue(status["acknowledged_without_composer"])
        self.assertTrue(status["accounted_for"])
        self.assertIn(
            14, mob_scene_recompose.ACKNOWLEDGED_WITHOUT_COMPOSER)

    # ---- the visual splice, measured here rather than inherited ------

    def test_the_splice_preserves_every_census_identity(self) -> None:
        # Lane A's letter asserts this and disclaims having tested it
        # ("ยังไม่มีเทสที่ขับฟังก์ชันนี้กับ generation ของ bg0015 เลย").
        # Run it here instead of repeating it on authority.
        generation = _lane_a_census(self.legacy)
        override = hostile_bg0015.scene14_hostile_overrides(self.legacy)
        spliced = mob_scene_recompose.splice_identity_override(
            self.legacy, generation, override)
        self.assertEqual(generation.actor_count, 81)
        self.assertEqual(spliced.actor_count, 81)
        self.assertEqual(
            tuple(spliced.actor_identities), tuple(generation.actor_identities))
        changed = [
            i for i, (a, b) in enumerate(
                zip(generation.entry_bytes, spliced.entry_bytes)) if a != b
        ]
        self.assertEqual(len(changed), 12)
        self.assertEqual(len(generation.frame), 14879)
        self.assertEqual(len(spliced.frame), 15035)

    # ---- the cross-check, and what it cannot do ----------------------

    def test_splice_identities_come_from_the_visual_path(self) -> None:
        self.assertEqual(gates.splice_identities(self.legacy),
                         TWELVE_IDENTITIES)

    def test_the_backing_check_reports_exactly_the_identities_it_is_not_given(
            self) -> None:
        # ACCEPTANCE CRITERION: stub splice_identities_missing_from to
        # `return ()` and this test must go red. It calls the production
        # function with a set that is deliberately missing eleven of the
        # twelve, so a stub that always answers () cannot pass.
        census = set(_lane_a_census(self.legacy).actor_identities)
        withheld = set(TWELVE_IDENTITIES[1:])
        reported = gates.splice_identities_missing_from(
            census - withheld, self.legacy)
        self.assertEqual(set(reported), withheld)
        self.assertEqual(len(reported), 11)
        # And with the full census nothing is missing -- the real state.
        self.assertEqual(
            gates.splice_identities_missing_from(census, self.legacy), ())

    def test_the_hand_typed_twelve_are_what_catches_a_small_shift(
            self) -> None:
        # Honest limit, recorded as a test rather than as a comment: a +1
        # placement shift stays "backed", because lane A ships 81 of 91
        # placements so the shifted identity is usually another real actor.
        census = set(_lane_a_census(self.legacy).actor_identities)
        shifted_by_one = {i + 1 for i in TWELVE_IDENTITIES}
        still_backed = shifted_by_one & census
        self.assertGreaterEqual(
            len(still_backed), 10,
            "a +1 shift is NOT caught by the census cross-check")
        # The literal pin is what notices it.
        self.assertNotEqual(tuple(sorted(shifted_by_one)), TWELVE_IDENTITIES)

    def test_an_empty_external_set_is_refused_rather_than_reported(
            self) -> None:
        with self.assertRaises(gates.MobCombatBg0015GateError):
            gates.splice_identities_missing_from((), self.legacy)

    # ---- collisions (unchanged, reviewed sound) ----------------------

    def test_there_are_no_live_cross_scene_collisions_today(self) -> None:
        self.assertEqual(gates.live_cross_scene_collisions_today(), ())

    def test_the_one_collision_registration_would_create(self) -> None:
        self.assertEqual(gates.bg0002_bg0015_identity_collisions(), (0x2058,))
        bg0015_row = next(
            m for m in hostile_bg0015.scene14_hostile_roster()
            if m.actor_identity == 0x2058)
        bg0002_row = next(
            m for m in field_mobs.roster_for_scene_id(gates.BG0002_SCENE_ID)
            if m.actor_identity == 0x2058)
        self.assertEqual(
            (bg0015_row.placement_index, bg0002_row.placement_index), (87, 87))
        self.assertEqual(
            (bg0002_row.template_id, bg0015_row.template_id), (34, 924))

    def test_the_owner_refusal_divergence_is_named_not_assumed(self) -> None:
        self.assertEqual(gates.owner_refused_placements_for_scene14(), ())
        self.assertEqual(
            field_mobs.OWNER_REFUSED_PLACEMENTS.get("Bg0002"),
            (89, 90, 92, 93, 94, 95, 96, 97))

    # ---- the pin the rename orphaned, restored -----------------------

    def test_the_two_scene_tag_readers_disagree_and_that_is_pinned(
            self) -> None:
        # Restored from the file the rename deleted: world_scene_folder
        # addresses scene 14, field_mobs does not ship it, so the two
        # readers answer differently and the ledgers they build are unequal
        # while both stay empty.
        self.assertEqual(
            world_scene_folder.scene_folder_for_scene_id(14), "Bg0015")
        self.assertIsNone(field_mobs.scene_for_scene_id(14))
        via_sync_shape = mob_combat.open_ledger((), scene="Bg0015")
        via_helper = mob_combat.open_ledger_for_scene_id(14)
        self.assertNotEqual(via_sync_shape, via_helper)
        self.assertEqual(
            via_sync_shape.identities(), via_helper.identities())

    def test_this_module_does_not_import_the_raw_table_module(self) -> None:
        self.assertNotIn(
            "field_mob_tables_bg0015",
            MODULE_PATH.read_text(encoding="utf-8"))

    def test_importing_this_module_registers_nothing(self) -> None:
        before = field_mobs.live_scenes()
        import importlib
        importlib.reload(gates)
        self.assertEqual(field_mobs.live_scenes(), before)
        self.assertEqual(set(before), {"bg0001", "Bg0002"})


class Bg0015WiredPathTests(unittest.TestCase):
    """Drives the REAL dispatch. Same harness shape as
    tests/test_scene_scoped_combat_wiring.py."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations")
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(1, 0, self.legacy.V135_PLAYER_X,
                     self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def _state_in_scene_14(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector)
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(state.foundation.account_id)[-1]
        with contextlib.redirect_stdout(io.StringIO()):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)))
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        selected = state.foundation.selected
        state.foundation.selected = dataclasses.replace(
            selected,
            position=dataclasses.replace(selected.position, scene_id=14))
        return state

    def _attack(self, state, target_identity):
        legacy = self.legacy
        body = (
            legacy.qwordtag(0x32, 0)
            + legacy.qwordtag(0x32, target_identity)
            + legacy.qwordtag(0x32, 0)
            + legacy.u32tag(0x14, 0)
            + legacy.u32tag(0x19, 0)
            + legacy.f32tag(0.0) + legacy.f32tag(0.0)
            + legacy.f32tag(0.0) + legacy.f32tag(0.0)
            + legacy.u8tag(0x0B, 0)
            + legacy.u16tag(0x12, 0)
            + legacy.u8tag(0x0B, 0)
        )
        pc = (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.ACTION_VITAL)
            + legacy.u8tag(0x0B, 0)
            + body
        )
        with contextlib.redirect_stdout(io.StringIO()):
            return state.dispatch(legacy.parse_outer(pc))

    def test_a_real_swing_in_scene_14_answers_not_a_field_mob(self) -> None:
        state = self._state_in_scene_14("bg0015_gates_wired")
        for identity in gates.splice_identities(self.legacy):
            self._attack(state, identity)
        answers = [e for e in state.events if e.startswith("mob_combat_")]
        self.assertEqual(
            answers.count(gates.WIRED_ANSWER_FOR_A_TABLELESS_SCENE), 12)
        for event in state.events:
            self.assertNotIn(mob_combat.REFUSE_TARGET_NOT_IN_LEDGER, event)
        self.assertEqual(state.mob_combat_scene_folder, gates.BG0015_FOLDER)
        self.assertEqual(state.mob_combat_ledger.identities(), ())
        # WHAT THIS DOES NOT PIN, shown rather than claimed: the answer is
        # about the EMPTY ROSTER, not about these twelve identities.
        for arbitrary in (0xDEADBEEF, 0x1, 0xFFFF):
            self._attack(state, arbitrary)
        self.assertEqual(
            [e for e in state.events if e.startswith("mob_combat_")].count(
                gates.WIRED_ANSWER_FOR_A_TABLELESS_SCENE), 15)

    def test_registering_bg0015_unwinds_the_first_swing(self) -> None:
        """THE HEADLINE. Registration alone does not give unkillable
        monsters -- it drops the connection on the first swing."""
        # Imported plainly by name: the approved-importer guard sweeps
        # src/**/*.py only, and tests/test_field_mob_hostile_bg0015.py
        # already imports this table the same way. No string-splitting
        # tricks -- a test that had to evade a guard would be a test
        # nobody should trust.
        from pirateforce_foundation import field_mob_tables_bg0015 as module
        registry = field_mobs._SCENE_TABLE_MODULES
        self.assertNotIn(module.SCENE, registry)
        registry[module.SCENE] = module
        self.addCleanup(registry.pop, module.SCENE, None)

        state = self._state_in_scene_14("bg0015_gates_unwind")
        with self.assertRaises(mob_ai_control.MobAiControlError) as ctx:
            self._attack(state, 0x2017)
        self.assertEqual(ctx.exception.reason, "ai_row_missing")
        self.assertIn("AI_COMBAT 301", str(ctx.exception))
        # Nothing on the dispatch path catches it: this is an unwind out of
        # dispatch(), i.e. a dropped connection, not an appended event.
        self.assertNotIn(
            gates.WIRED_ANSWER_FOR_A_TABLELESS_SCENE, state.events[-1:])


if __name__ == "__main__":
    unittest.main()
