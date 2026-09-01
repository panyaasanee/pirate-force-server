"""LANE-B: tests for src/pirateforce_foundation/mob_combat_bg0015_gates.py.

What each test is for, and what it deliberately does NOT claim:

~~``test_registering_bg0015_unwinds_the_first_swing`` is the headline: it
registers Bg0015 in-process and drives one real ActionVital in scene 14,
and the dispatch RAISES. That is a dropped connection, not a refusal.~~
WITHDRAWN as of round n8kq4r: ``tools/pf_mine_mob_ai_rows.py`` now mines
Bg0015 into the union it writes ``field_mob_ai_tables.py`` from (the AI
table it was reading from was simply never asked for these rows -- nothing
about the raise was inherent). ``open_register`` no longer refuses any
Bg0015 row, so this call no longer raises. The test below is renamed
``test_registering_bg0015_clears_the_ai_table_gate_but_the_swing_is_still_
inert`` and pins what is ACTUALLY measured now: no raise, the roster syncs,
and the one real packet this file already used to probe with (action code
0, historically called a "wield" capture in the v141 event vocabulary)
still produces no combat reply -- because it was never a strike packet,
only ever the thing this file already had lying around that reached
``_sync_combat_scene_state``. This test does NOT claim a real hit or a
real kill has been driven; it does not have a strike packet to drive one
with, and inventing one is exactly what this lane's charter forbids.

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

    # ---- the AI-table gate, closed round n8kq4r ----------------------

    def test_open_register_no_longer_refuses_any_bg0015_row(self) -> None:
        # ~~open_register_refusal_for_scene14() == "ai_row_missing"~~
        # WITHDRAWN round n8kq4r: ``tools/pf_mine_mob_ai_rows.py`` now mines
        # ``field_mob_tables_bg0015`` into the union, so every AI_COMBAT/
        # AI_WANDER id Bg0015's rows cite resolves. The refusal this test
        # used to pin is gone; it does not claim anything past that.
        self.assertIsNone(gates.open_register_refusal_for_scene14())
        mob_ai_control.open_register(hostile_bg0015.scene14_hostile_roster())

    def test_the_missing_ai_rows_are_named_not_summarised(self) -> None:
        # ~~missing_combat/missing_wander name seven and one ids~~
        # WITHDRAWN round n8kq4r: both are now empty -- see the test above.
        # ``mined_combat``/``mined_wander`` are asserted as SUPERSETS of
        # what Bg0015 wants rather than pinned to an exact tuple, so a
        # later scene's mining widening this same union does not make this
        # test lie about what Bg0015 specifically needs.
        report = gates.ai_rows_missing_for_scene14()
        self.assertEqual(report["missing_combat"], ())
        self.assertEqual(report["missing_wander"], ())
        self.assertEqual(
            report["wanted_combat"],
            (102, 134, 273, 301, 323, 333, 472))
        self.assertEqual(report["wanted_wander"], (11, 16, 22))
        self.assertTrue(
            set(report["wanted_combat"]).issubset(set(report["mined_combat"])))
        self.assertTrue(
            set(report["wanted_wander"]).issubset(set(report["mined_wander"])))

    # ---- the other measured preconditions ---------------------------

    def test_no_roster_and_carlos_alone_lacks_a_death_ruling_today(
            self) -> None:
        # ~~no death ruling for any of the seven~~ WITHDRAWN round
        # n3wqrt-successor: COO-RULING-20260901-1046 covers six of the
        # seven now (mob_death.py). Only Carlos (924) is still refused --
        # this test's own name used to claim more than that.
        self.assertFalse(gates.roster_gate_open())
        self.assertEqual(gates.scene14_roster_size_today(), 0)
        self.assertEqual(
            gates.templates_without_a_death_ruling(), (924,))
        ruled, refused = [], []
        for mob in hostile_bg0015.scene14_hostile_roster():
            if mob.template_id == 924:
                refused.append(mob)
                continue
            ruled.append(mob)
        self.assertTrue(ruled, "expected six ruled rows, got none")
        for mob in ruled:
            self.assertEqual(
                mob_death.ruling_for(mob), "COO-RULING-20260901-1046")
        for mob in refused:
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

    def test_registering_bg0015_clears_the_ai_table_gate_but_the_swing_is_still_inert(
            self) -> None:
        """~~Registration alone does not give unkillable monsters -- it
        drops the connection on the first swing.~~ WITHDRAWN round n8kq4r:
        the AI-table gap that raise came from is mined now (see
        ``tools/pf_mine_mob_ai_rows.py``'s Bg0015 union). Registering no
        longer raises. What is measured below and NOTHING MORE: no raise,
        the roster syncs and the ledger fills with Bg0015's twelve real
        identities, and the one packet this file already had on hand
        (action code 0) still comes back as a no-reply "wield" capture, not
        a strike -- so this test still cannot and does not claim a hit or a
        kill was driven. Other gates this lane has already measured and not
        touched stay exactly where they were:
        :func:`templates_without_a_death_ruling` is non-empty (owner-only)
        and :func:`recompose_status` still reports no scene-14 composer
        (``has_composer`` is ``False`` -- re-verified live this round).

        ~~the recompose reply is
        ``mob_combat_bar_census_compose_skipped_no_population_anchor``~~ IS
        STRUCK, round n8kq4r addendum (post-merge, unrelated to this lane's
        own edits): chief's already-merged R278 work widened the eager NPC
        census disjunct from bg0002-only to every scene but home
        (``runtime.py``, commit ``b69071f6``), so scene 14 now gets an
        arrival-census anchor (``last_target_pos``-equivalent) WITHOUT this
        test's helper ever sending a ``TargetPosVital`` -- a real improvement,
        not a regression.  The "attack before any anchor exists" branch this
        test used to land in (``runtime.py``'s ``else`` arm,
        ``no_population_anchor``) is therefore no longer reached; the swing
        now reaches the recompose call itself, which still refuses because
        scene 14 has no registered composer (``has_composer=False``, same
        gate :func:`recompose_status` already named) -- so the event this
        test now measures is ``no_composer_for_scene``, one gate further
        along than before, and this file did not move that gate.

        RE-157 job 2 ADDENDUM (MOB-COMBAT-001 announced-actor guard): STRUCK
        again.  ``runtime.py``'s scene-14 census commit (the lane-composer
        branch the paragraph above names) now runs before this file's
        helper ever attacks -- but ``lane_hooks.SceneCensusResult`` carries
        no per-actor identity list, only opaque wire bytes, so that commit
        cannot name what it announced and stamps an EMPTY announced-actor
        membership for scene 14 rather than a fabricated or stale one (see
        the ``JUDGMENT CALL`` comment at that commit site in ``runtime.py``).
        0x2017 is therefore a real roster/ledger member that was never
        ANNOUNCED, which is exactly the gap RE-157 job 2 closes: the new
        guard now refuses the swing one gate EARLIER than the recompose
        call this docstring's previous paragraph measured, before the
        recompose path is ever reached at all.
        """
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

        state = self._state_in_scene_14("bg0015_gates_cleared")
        # No raise: the earlier ``assertRaises(MobAiControlError)`` this
        # test used is gone on purpose. If it starts raising again this
        # assertion turns red, which is exactly the coverage this file
        # wants -- a silent regression back to the mining gap.
        self._attack(state, 0x2017)
        self.assertEqual(state.mob_combat_scene_folder, gates.BG0015_FOLDER)
        self.assertEqual(
            state.mob_combat_ledger.identities(),
            tuple(sorted(gates.splice_identities(self.legacy))))
        # The one reply this specific (non-strike) packet produces today,
        # measured rather than assumed.  RE-157 job 2 ADDENDUM: this used to
        # be "..._skipped_no_composer_for_scene" (the recompose path's own
        # refusal) -- see the docstring's RE-157 paragraph for why the
        # MOB-COMBAT-001 announced-actor guard now refuses one gate
        # earlier, before the recompose call is ever reached.
        self.assertIn(
            "mob_combat_target_not_announced_no_reply",
            state.events)
        self.assertFalse(gates.recompose_status()["has_composer"])


if __name__ == "__main__":
    unittest.main()
