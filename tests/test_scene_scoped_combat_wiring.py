"""COO-DECISION 2026-08-29T08:48+07:00 item 3 -- the chief's half, proven.

LANE-B letter 20260829_0744 measured the wall: ``runtime.py`` loaded ONE
scene's roster (bg0001's) no matter where the selected character stood, and
opened the combat ledger and the AI register on that same default -- so a
Bg0002 mob was refused as ``target_not_in_ledger`` before any gate was even
asked.  LANE-A shipped the one public reader
(``world_scene_folder.scene_folder_for_scene_id``, PR #255); this file proves
the chief's wiring of it:

  * the combat roster, the combat ledger and the AI register follow the
    SELECTED CHARACTER's scene, resolved through that reader and never
    through the registry's ``model_id`` spelling;
  * an attack in Bg0002 on a Bg0002 roster identity now lands, and a killing
    blow there finishes under Bg0002's own owner letter
    (``widened=mob_death.ruling_for(mob)``), not bg0001's hardcoded one;
  * a scene the registry does not address ships NO roster and says so by
    name BEFORE any other verdict -- never the default roster;
  * an ADDRESSED scene with no mined mob table answers with the existing
    not-a-field-mob silence over a truthfully empty roster;
  * a scene 1 session's mid-scene ledger state is never wiped by a re-open
    (the sync only re-opens when the folder actually changes);
  * the boot census prints ``mob_death.describe_widening_coverage()`` so an
    uncovered scene is seen at boot, not in front of a tester.

NOT proven here, unchanged from test_mob_combat_dispatch.py's own limit:
whether a real attack input produces this exact ActionVital shape, and
whether a real client draws anything for these frames.  Scene arrival is
synthesized two ways below -- a stored scene-2 row (the same
``store.save_position`` route test_bg0002_census_wiring.py uses) and direct
``dataclasses.replace`` surgery on ``foundation.selected`` for scene ids no
login path stores today -- because what this file pins is the DISPATCH's
answer to "where does the character stand", not any travel lane.
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import itertools
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import world_scene_folder  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation import world_population_bg0002  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENE2_N_ID = world_population_bg0002.SCENE2_N_ID
CONTROL_TARGET = 0x2000 + field_mobs.CONTROL_PLACEMENT_INDEX + 1
# An addressed scene the registry names but no mined mob table serves --
# resolved through the reader itself at import time so this file cannot pin
# a hand-typed folder spelling (the exact drift the reader exists to end).
TABLELESS_SCENE_ID = 5
# No registry row addresses this id; world_scene_folder answers None.
UNADDRESSED_SCENE_ID = 9999


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class SceneScopedCombatWiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.bg0002_roster = field_mobs.load_roster(field_mobs.BG0002_SCENE)
        self.bg0002_mob = self.bg0002_roster[0]

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness -----------------------------------------------------

    def _login_and_create(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        return state, character

    def _start_game(self, state, character):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)
            ))
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        return buf.getvalue()

    def _state(self, token):
        state, character = self._login_and_create(token)
        self._start_game(state, character)
        return state

    def _state_at_scene2(self, token):
        """A real stored character row whose scene_id is 2 -- the same
        ``store.save_position`` route test_bg0002_census_wiring.py uses,
        because nothing in this tree seeds a scene-2 row on a real boot.
        """
        state, character = self._login_and_create(token)
        destination = world_scene_travel.destination(SCENE2_N_ID)
        spawn = world_scene_travel.spawn_position(destination)
        self.store.select_character(
            state.foundation.session_id, character.selector,
        )
        self.store.save_position(
            state.foundation.session_id, character.id,
            Position(SCENE2_N_ID, 0, spawn[0], spawn[1], spawn[2], 0.0),
        )
        self._start_game(state, character)
        return state

    def _move_to_scene(self, state, scene_id):
        """Direct surgery on the selected record's frozen Position, for
        scene ids no login path stores today (the tableless and unaddressed
        cases).  What is under test is the dispatch's reading of
        ``selected.position.scene_id``, not how the character got there.
        """
        selected = state.foundation.selected
        state.foundation.selected = dataclasses.replace(
            selected,
            position=dataclasses.replace(
                selected.position, scene_id=scene_id,
            ),
        )

    def _arrive(self, state):
        """The real arrival TargetPos, production order (login -> StartGame
        -> TargetPos -> census) -- sets population_refresh_anchor/
        world_census_actor_count so the census-recompose lane the round-trip
        test exercises actually runs (same shape as
        test_mob_combat_dispatch.py's own _arrive)."""
        anchor = (
            state.foundation.selected.position.x,
            state.foundation.selected.position.y,
            state.foundation.selected.position.z,
        )
        legacy = self.legacy
        pc = (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
            + legacy.u8tag(0x0B, 0)
            + b"".join(legacy.f32tag(v) for v in (*anchor, 0.0))
            + legacy.u8tag(0x0B, 0)
            + legacy.u8tag(0x0B, 0)
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self._last_arrival_actions = state.dispatch(
                legacy.parse_outer(pc)
            )
        return anchor

    def _action_vital_pc(self, target_identity, outer_id=None):
        """``outer_id`` other than the default RuntimeProtocolReq builds
        the wound-before-census frame pf-adversary (round nbulzb, D1)
        measured: combat dispatch is NESTED-id gated while the census
        guard is OUTER-id gated, and ``parse_outer`` extracts a nested
        vital under any outer id with mask bit 0x02 -- so this frame
        wounds without composing the arrival census."""
        legacy = self.legacy
        if outer_id is None:
            outer_id = legacy.GSCN_RUNTIME_PROTOCOL_REQ
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
        return (
            legacy.u16tag(0x12, outer_id)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.ACTION_VITAL)
            + legacy.u8tag(0x0B, 0)
            + body
        )

    def _attack(self, state, target_identity):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = state.dispatch(self.legacy.parse_outer(
                self._action_vital_pc(target_identity)
            ))
        return actions

    def _combat_labels(self, actions):
        """Combat/death/loot labels only: a first attack in a scene can
        also flush that scene's one-shot census lane into the same dispatch
        (WORLD_CENSUS_*), which is that lane's contract, not this one's."""
        return [
            label for label, _pc, _f, _d in actions
            if not label.startswith("WORLD_CENSUS_")
        ]

    def _set_balance(self, state, identity, current_hp):
        row = state.mob_combat_ledger.balance_of(identity)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            mob_combat.MobBalance(identity, row.max_hp, current_hp)
        )

    # ----- scene 1: unchanged, and never wiped mid-scene -----------------

    def test_scene1_boot_records_the_folder_its_ledger_was_opened_on(self):
        state = self._state("ssc_boot")
        self.assertEqual(
            state.mob_combat_scene_folder,
            world_scene_folder.scene_folder_for_scene_id(1),
        )
        self.assertEqual(
            state.mob_combat_ledger.identities(),
            tuple(sorted(
                m.actor_identity for m in field_mobs.load_roster()
            )),
        )

    def test_scene1_dispatch_does_not_reopen_the_ledger_mid_scene(self):
        """The sync re-opens ONLY on a folder change.  A mutant that
        re-opens unconditionally resets this pre-wounded balance to its
        ceiling and the killing blow below never lands."""
        state = self._state("ssc_no_reopen")
        self._set_balance(state, CONTROL_TARGET, 500)
        actions = self._attack(state, CONTROL_TARGET)
        labels = self._combat_labels(actions)
        self.assertEqual(
            labels[:3],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"],
        )
        self.assertTrue(state.mob_death_register.is_dead(CONTROL_TARGET))

    # ----- scene 2: the wall LANE-B measured, down ------------------------

    def test_scene2_attack_on_a_bg0002_identity_now_lands(self):
        state = self._state_at_scene2("ssc_scene2_hit")
        target = self.bg0002_mob.actor_identity
        actions = self._attack(state, target)
        self.assertEqual(
            self._combat_labels(actions),
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        self.assertEqual(state.mob_combat_scene_folder, "Bg0002")
        balance = state.mob_combat_ledger.balance_of(target)
        self.assertLess(balance.current_hp, self.bg0002_mob.max_hp)
        self.assertGreater(balance.current_hp, 0)
        self.assertTrue(state.mob_ai_register.is_tracked(target))
        self.assertEqual(state.mob_combat_hit_count, 1)

    def test_scene2_ledger_and_register_hold_bg0002_rows_not_bg0001s(self):
        state = self._state_at_scene2("ssc_scene2_rows")
        self._attack(state, self.bg0002_mob.actor_identity)
        self.assertEqual(
            state.mob_combat_ledger.identities(),
            tuple(sorted(
                m.actor_identity for m in self.bg0002_roster
            )),
        )
        self.assertNotIn(
            CONTROL_TARGET, state.mob_combat_ledger.identities(),
        )
        self.assertFalse(state.mob_ai_register.is_tracked(CONTROL_TARGET))

    def test_scene2_killing_blow_finishes_under_bg0002s_own_letter(self):
        """A mutant that keeps the hardcoded bg0001 ruling string refuses
        this kill (wrong letter for every Bg0002 template) and the death
        frames below never compose."""
        state = self._state_at_scene2("ssc_scene2_kill")
        target = self.bg0002_mob.actor_identity
        # Arm the ledger AFTER the first dispatch has synced it to Bg0002:
        # a fresh scene-2 session's ledger opens on the first attack.
        self._attack(state, target)
        self._set_balance(state, target, 1)
        # Two attacks in one test run faster than the real attack cadence
        # allows; reset the per-session cadence ledger so the SECOND swing
        # is judged on the death path, not the timing gate (which
        # test_mob_combat_cadence_wiring.py owns).
        state.mob_combat_cadence = mob_combat.open_cadence_ledger()
        actions = self._attack(state, target)
        labels = self._combat_labels(actions)
        self.assertEqual(
            labels[:3],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"],
        )
        # The register keys deaths by (identity, scene) -- and the scene it
        # recorded is the mob's own tag from the Bg0002 table, which is the
        # point of this whole wiring.
        self.assertTrue(
            state.mob_death_register.is_dead(target, self.bg0002_mob.scene)
        )
        self.assertFalse(any(
            event.startswith("mob_death_refused_")
            for event in state.events
        ))
        # And the letter it travelled under is Bg0002's own, the one
        # ruling_for derives -- pinned against the module, not retyped.
        self.assertIn(
            "widen-death-scope-bg0002",
            mob_death.ruling_for(self.bg0002_mob),
        )

    # ----- unaddressed scene: no roster, said by name, said FIRST --------

    def test_an_unaddressed_scene_ships_no_roster_and_says_so_first(self):
        state = self._state("ssc_unaddressed")
        folder_before = state.mob_combat_scene_folder
        ledger_before = state.mob_combat_ledger.identities()
        self._move_to_scene(state, UNADDRESSED_SCENE_ID)
        self.assertIsNone(
            world_scene_folder.scene_folder_for_scene_id(
                UNADDRESSED_SCENE_ID,
            )
        )
        actions = self._attack(state, CONTROL_TARGET)
        self.assertEqual(self._combat_labels(actions), [])
        self.assertIn(
            f"mob_combat_scene_{UNADDRESSED_SCENE_ID}"
            "_unaddressed_no_roster_no_reply",
            state.events,
        )
        # Refused BEFORE any verdict: the default roster did not answer,
        # no hit was counted, and no scene swap was committed either --
        # a refusal is not an arrival.
        self.assertEqual(state.mob_combat_hit_count, 0)
        self.assertEqual(state.mob_combat_scene_folder, folder_before)
        self.assertEqual(
            state.mob_combat_ledger.identities(), ledger_before,
        )

    # ----- addressed scene, no mined table: truthfully empty -------------

    def test_an_addressed_tableless_scene_answers_over_an_empty_roster(self):
        state = self._state("ssc_tableless")
        self._move_to_scene(state, TABLELESS_SCENE_ID)
        folder = world_scene_folder.scene_folder_for_scene_id(
            TABLELESS_SCENE_ID,
        )
        self.assertIsNotNone(folder)
        self.assertNotIn(folder, field_mobs.live_scenes())
        actions = self._attack(state, CONTROL_TARGET)
        self.assertEqual(self._combat_labels(actions), [])
        self.assertIn(
            "mob_combat_target_not_a_field_mob_no_reply", state.events,
        )
        self.assertEqual(state.mob_combat_scene_folder, folder)
        self.assertEqual(state.mob_combat_ledger.identities(), ())
        # LANE-B CORE-REQUEST 20260829_1955 item (3), COO 20:41: an empty
        # roster has no rows for open_ledger to derive the scene tag from,
        # so before scene= was declared at the call site this ledger said
        # scene=None while mob_combat_scene_folder said the folder -- two
        # fields answering the same question differently the moment a
        # player walked into a tableless scene.  scene= is a checked
        # declaration (open_ledger joins it against the rows), not a
        # forced label.
        self.assertEqual(state.mob_combat_ledger.scene, folder)

    # ----- scene change re-opens at the new scene -------------------------

    def test_a_scene_change_reopens_ledger_and_register_at_the_new_scene(
        self,
    ):
        state = self._state("ssc_change")
        self._attack(state, CONTROL_TARGET)  # wound it in scene 1
        self.assertEqual(state.mob_combat_hit_count, 1)
        self._move_to_scene(state, SCENE2_N_ID)
        target = self.bg0002_mob.actor_identity
        # Same cadence reset as the killing-blow test above: the timing
        # gate is per performer, not per scene, and is not what this test
        # measures.
        state.mob_combat_cadence = mob_combat.open_cadence_ledger()
        actions = self._attack(state, target)
        self.assertIn("MOB_COMBAT_ANNOUNCE", self._combat_labels(actions))
        self.assertEqual(state.mob_combat_scene_folder, "Bg0002")
        self.assertNotIn(
            CONTROL_TARGET, state.mob_combat_ledger.identities(),
        )
        self.assertTrue(state.mob_ai_register.is_tracked(target))
        self.assertFalse(state.mob_ai_register.is_tracked(CONTROL_TARGET))

    # ----- a round trip keeps the dead dead (pf-adversary D1) -------------

    def test_a_scene_round_trip_rehydrates_deaths_into_the_fresh_ledger(
        self,
    ):
        """pf-adversary (this round, D1, measured): the first version of
        _sync_combat_scene_state re-opened the ledger at full HP on a
        return trip while mob_death_register still held the corpse --
        repopulation_entries refused BY DESIGN on every later hit
        (REFUSE_LEDGER_DISAGREES_WITH_REGISTER), every bar/death frame
        degraded to the one-entry replace-by-omission shape, and the corpse
        answered hits with live damage numbers.  This drives the same
        kill -> leave -> return -> hit sequence through the real dispatcher
        (with the arrival census armed, so the recompose lane actually
        runs) and pins the fix: the re-opened ledger holds the registered
        death at 0 HP, the recompose never refuses, and the corpse stays
        silent."""
        state, character = self._login_and_create("ssc_round_trip")
        self._start_game(state, character)
        self._arrive(state)
        # Kill the control mob in scene 1.
        self._set_balance(state, CONTROL_TARGET, 1)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = state.dispatch(self.legacy.parse_outer(
                self._action_vital_pc(CONTROL_TARGET)
            ))
        self.assertIn(
            "MOB_DEATH_DEAD", [label for label, *_r in actions],
        )
        # Leave: one attack in Bg0002 swaps the per-scene state there.
        self._move_to_scene(state, SCENE2_N_ID)
        state.mob_combat_cadence = mob_combat.open_cadence_ledger()
        self._attack(state, self.bg0002_mob.actor_identity)
        # Return to scene 1 and hit a DIFFERENT, living mob.
        self._move_to_scene(state, 1)
        state.mob_combat_cadence = mob_combat.open_cadence_ledger()
        living = next(
            m.actor_identity for m in field_mobs.load_roster()
            if m.actor_identity != CONTROL_TARGET
        )
        actions = self._attack(state, living)
        self.assertIn(
            "MOB_COMBAT_ANNOUNCE", self._combat_labels(actions),
        )
        # The fix, pinned three ways: no recompose refusal anywhere in the
        # session, the corpse re-opened dead rather than at its ceiling,
        # and a further hit on it stays silent (no_room), never a live
        # damage number.
        self.assertFalse(any(
            "census_compose_refused" in event for event in state.events
        ))
        self.assertEqual(
            state.mob_combat_ledger.balance_of(CONTROL_TARGET).current_hp,
            0,
        )
        self.assertTrue(state.mob_death_register.is_dead(CONTROL_TARGET))
        state.mob_combat_cadence = mob_combat.open_cadence_ledger()
        corpse_actions = self._attack(state, CONTROL_TARGET)
        self.assertEqual(self._combat_labels(corpse_actions), [])

    # ----- ledger and AI register open on ONE roster (pf-adversary D3) ----

    def test_boot_opens_ledger_and_ai_register_on_the_same_roster(self):
        """pf-adversary (this round, D3): no test pinned the COO invariant
        that the boot ledger and AI register hold the same scene's rows --
        a mutant calling field_mobs.load_roster() twice stayed green
        because both calls return the same value today.  Feed load_roster
        DIFFERENT rosters on successive calls: code that shares one
        _boot_roster stays self-consistent, code that loads twice opens
        the two structures on different scenes' rows and goes red here."""
        rosters = itertools.cycle([
            field_mobs.load_roster(),
            self.bg0002_roster,
        ])
        with mock.patch.object(
            field_mobs, "load_roster",
            side_effect=lambda *a, **k: next(rosters),
        ):
            state_type = make_state_class(
                self.legacy, self.lifecycle, self.projector,
            )
            state = state_type("ssc_one_boot_roster")
        ledger_identities = set(state.mob_combat_ledger.identities())
        for identity in (
            {m.actor_identity for m in field_mobs.load_roster()}
            | {m.actor_identity for m in self.bg0002_roster}
        ):
            self.assertEqual(
                identity in ledger_identities,
                state.mob_ai_register.is_tracked(identity),
                "boot ledger and AI register disagree on identity "
                f"0x{identity:X}: they were not opened on one roster",
            )

    # ----- the boot census says what the letters cover --------------------

    def test_the_home_census_prints_widening_coverage_at_boot(self):
        """LANE-B letter 20260829_0744 point 3: the day a scene ships that
        no owner letter covers, someone sees it AT BOOT.  Driven through
        the real arrival census, printed next to the roster-override
        coverage gate; content pinned against the module's own lines so
        this cannot drift into asserting a retyped copy."""
        state, character = self._login_and_create("ssc_coverage")
        self._start_game(state, character)
        anchor = (
            state.foundation.selected.position.x,
            state.foundation.selected.position.y,
            state.foundation.selected.position.z,
        )
        legacy = self.legacy
        pc = (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
            + legacy.u8tag(0x0B, 0)
            + b"".join(legacy.f32tag(v) for v in (*anchor, 0.0))
            + legacy.u8tag(0x0B, 0)
            + legacy.u8tag(0x0B, 0)
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            state.dispatch(legacy.parse_outer(pc))
        out = buf.getvalue()
        self.assertTrue(state.world_census_sent)
        for line in mob_death.describe_widening_coverage():
            self.assertIn(line, out)

    # ----- the census override composes from ONE scene id -----------------

    def test_census_override_recomposes_ledger_from_the_scene_it_composes_for(
        self,
    ):
        """CORE-REQUEST (LANE-B 20260829_1445), the half R227 left open:
        the home-census ``full_roster_override`` used to pair a fresh
        ``field_mobs.load_roster()`` (always bg0001) with whatever ledger
        the session happened to hold -- and the ledger is re-opened lazily
        at ATTACK time, so after a scene round trip with no attack since
        returning it still holds the other scene's rows.  That pairing
        raises ``ledger_disagrees_with_register`` OUTSIDE the compose
        catch-all and unwinds the listener thread (v141:7440 has no
        except).

        This drives the exact state through the real dispatcher: kill the
        control mob at home (register holds the corpse), swap the per-scene
        combat state with one real Bg0002 attack, return home WITHOUT
        attacking, and recompose the arrival census.  ``world_census_sent``
        is un-latched by hand -- today no login path re-runs the home
        arrival census after travel, but BUILD-002's own comment in
        runtime.py names the boot that will, and the invariant must hold
        before that boot exists, not after it crashes.

        The away-scene leg is a KILL, not a wound (pf-adversary, this
        round, D1, measured): the death register is per-(identity, scene)
        and survives the trip BY DESIGN, so a Bg0002 corpse rides along
        into the home recompose -- and before this round's
        mob_death.repopulation_entries scene filter, that one foreign-scene
        record refused the whole compose
        (``register_row_disagrees_with_roster``) on the same uncaught line,
        with the ledger correctly synced.  A wound here would have dodged
        exactly that defect.

        MUTATION-PROOF: revert the runtime.py override site to
        ``field_mobs.load_roster()`` + the un-synced ledger and this test
        errors with MobDeathContractError out of dispatch; revert the
        mob_death scene filter alone and it errors the same way on the
        foreign-scene corpse; drop the rehydration instead and the
        corpse-at-0 assertion fails.
        """
        state = self._state("ssc_census_override_sync")
        self._arrive(state)
        self._set_balance(state, CONTROL_TARGET, 1)
        actions = state.dispatch(self.legacy.parse_outer(
            self._action_vital_pc(CONTROL_TARGET)
        ))
        self.assertIn(
            "MOB_DEATH_DEAD", [label for label, *_rest in actions],
        )
        self._move_to_scene(state, SCENE2_N_ID)
        state.mob_combat_cadence = mob_combat.open_cadence_ledger()
        away_target = self.bg0002_mob.actor_identity
        self._attack(state, away_target)
        self.assertEqual(state.mob_combat_scene_folder, "Bg0002")
        self._set_balance(state, away_target, 1)
        state.mob_combat_cadence = mob_combat.open_cadence_ledger()
        away_actions = self._attack(state, away_target)
        self.assertIn(
            "MOB_DEATH_DEAD",
            [label for label, *_rest in away_actions],
        )
        self.assertTrue(
            state.mob_death_register.is_dead(away_target, "Bg0002"),
        )
        self._move_to_scene(state, 1)
        state.world_census_sent = False
        committed_before = sum(
            1 for event in state.events
            if event.startswith("world_census_committed_actors_")
        )
        self._arrive(state)
        home_folder = world_scene_folder.scene_folder_for_scene_id(1)
        self.assertEqual(state.mob_combat_scene_folder, home_folder)
        self.assertTrue(state.world_census_sent)
        self.assertEqual(
            sum(
                1 for event in state.events
                if event.startswith("world_census_committed_actors_")
            ),
            committed_before + 1,
            state.events,
        )
        self.assertFalse(any(
            "census_compose_refused" in event for event in state.events
        ))
        self.assertEqual(
            state.mob_combat_ledger.balance_of(CONTROL_TARGET).current_hp,
            0,
        )


    def test_the_bg0002_arrival_census_syncs_combat_state_to_the_scene(self):
        """COO-DECISION 20260829_1842 item 3, the chief's call-site half:
        the Bg0002 arrival census takes the same symmetric route the
        bg0001 branch already takes -- sync ledger+roster+AI register to
        the scene it composes for, then pass that synced ledger to the
        hostility override, never omitting it again.

        What this makes observable: on a scene-2 boot the combat state
        holds Bg0002's rows from the ARRIVAL census on, not from the first
        attack on (the lazy attack-time sync was the only opener before) --
        so anything that reads the ledger between arrival and the first
        swing sees the right scene, and the mismatched
        ledger-against-roster pair that made R230 omit the ledger can no
        longer be composed.

        What this deliberately does NOT claim: that the census bytes of a
        WELL-ORDERED session change.  On an untouched arrival a fresh sync
        holds every mob at its ceiling with deaths rehydrated from the
        register -- the same facts the register-only compose carried --
        and in the one frame that both wounds and composes, dispatch order
        puts the compose FIRST (measured: census labels precede
        MOB_COMBAT_* in the same dispatch).  The case where the bytes DO
        change -- a wound landed in an EARLIER frame, reachable through a
        foreign-outer ActionVital -- is pinned by
        ``test_a_wound_landed_before_the_census_reaches_the_census_bytes``
        below, which is what makes the ledger kwarg itself falsifiable
        (pf-adversary this round, D1: without it, dropping ``ledger=``
        alone kept the entire tree green).

        MUTATION-PROOF (measured): revert the call site to the unsynced
        no-ledger shape and the folder assertion goes red (boot folder is
        bg0001 until the first attack).
        """
        state = self._state_at_scene2("ssc_bg0002_arrival_sync")
        self.assertNotEqual(state.mob_combat_scene_folder, "Bg0002")
        self._arrive(state)
        self.assertTrue(state.world_census_sent)
        self.assertEqual(state.mob_combat_scene_folder, "Bg0002")
        self.assertIn(
            self.bg0002_mob.actor_identity,
            state.mob_combat_ledger.identities(),
        )
        self.assertFalse(any(
            "census" in event and "refused" in event
            for event in state.events
        ), state.events)
        # And the first swing still lands, exactly as before the change.
        actions = self._attack(state, self.bg0002_mob.actor_identity)
        self.assertIn(
            "MOB_COMBAT_ANNOUNCE",
            [label for label, *_rest in actions],
        )

    def test_a_wound_landed_before_the_census_reaches_the_census_bytes(self):
        """The ledger kwarg's own mutation kill (pf-adversary D1, measured).

        A wound CAN precede the arrival census: combat dispatch is gated
        on the NESTED vital id while the census guard is gated on the
        OUTER id, and ``parse_outer`` extracts a nested vital under any
        outer id carrying mask bit 0x02 -- so an ActionVital under a
        foreign outer id wounds the mob (the attack-time sync opens the
        Bg0002 ledger) while ``world_census_sent`` stays False.  The
        arrival census that follows must ship that mob at its wounded HP:
        this is the exact full-HP window COO-DECISION 20260829_1842
        exists to close, and before this test, deleting ``ledger=`` alone
        from the call site kept the entire suite green.

        MUTATION-PROOF (measured): drop ``ledger=self.mob_combat_ledger``
        from the Bg0002 override call and the wounded-entry assertion
        goes red (the census ships the ceiling again).
        """
        state = self._state_at_scene2("ssc_bg0002_wound_before_census")
        target = self.bg0002_mob.actor_identity
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = state.dispatch(self.legacy.parse_outer(
                self._action_vital_pc(target, outer_id=0x1234)
            ))
        self.assertIn(
            "MOB_COMBAT_ANNOUNCE",
            [label for label, *_rest in actions],
        )
        self.assertFalse(
            state.world_census_sent,
            "fixture failure: the foreign-outer frame composed the census "
            "after all, so no wound-before-census state exists",
        )
        wounded_hp = state.mob_combat_ledger.balance_of(target).current_hp
        self.assertLess(wounded_hp, self.bg0002_mob.max_hp)
        self.assertGreater(
            wounded_hp, 0,
            "fixture failure: the strike killed outright -- deaths were "
            "already covered by the register, this pins the wounded-alive "
            "case",
        )
        self._arrive(state)
        self.assertTrue(state.world_census_sent)
        census_pc = next(
            pc for label, pc, *_rest in self._last_arrival_actions
            if label.startswith("WORLD_CENSUS_BG0002_INITIAL_")
        )
        wounded_entry = field_mobs.hostile_actor_entry(
            self.legacy, self.bg0002_mob, current_hp=wounded_hp,
        )
        full_entry = field_mobs.hostile_actor_entry(
            self.legacy, self.bg0002_mob,
            current_hp=self.bg0002_mob.max_hp,
        )
        self.assertIn(wounded_entry, census_pc)
        self.assertNotIn(full_entry, census_pc)
        self.assertFalse(any(
            "census" in event and "refused" in event
            for event in state.events
        ), state.events)


if __name__ == "__main__":
    unittest.main()
