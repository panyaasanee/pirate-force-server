"""CORE-REQUEST (LANE-B, 20260828_0337) on the REAL dispatcher.

``tests/test_mob_combat.py`` proves ``mob_combat.check_attack_cadence`` /
``describe_cadence_rejection`` offline, against synthetic ledgers and
caller-supplied integer millisecond readings.  It does not prove that
``runtime.py``'s ``_dispatch_mob_combat`` actually calls either function --
before this round's wiring, nothing did, so a real spam-click reached
``attack_from_observed_action`` on every single dispatch, exactly the
"runaway damage" gap GT-084-R2 saw and PANYA-REFERENCE 2026-08-27 16:35
ordered closed first.  This file drives ``make_state_class`` headless (no
socket, no client) the same way ``tests/test_mob_combat_dispatch.py`` does,
injecting a fake ``monotonic_clock`` so cadence timing is exact and
reproducible instead of wall-clock flaky, and checks:

* a fresh session's first attack is accepted (nobody has an accepted-attack
  row yet, so the gate's own "no prior timestamp" branch treats it as if a
  full window had already elapsed);
* a second attack from the SAME performer at the SAME clock reading (i.e.
  well inside ``ATTACK_CADENCE_MS_PROVISIONAL``) is rejected: no frames
  reach the wire, the combat ledger is not touched (target HP unchanged),
  and the ASCII console line ``describe_cadence_rejection`` composes is
  printed exactly once;
* an attack at exactly the window boundary is accepted, and the ledger
  commits normally from there (second hit lands, HP drops further);
* a burst of three rejects does not slide the performer's own deadline --
  the fourth attempt, timed from the ORIGINAL accepted timestamp rather
  than from any of the rejected attempts, is accepted at the same boundary
  the single-reject case above uses.

NOT proven here: the real client's own attack-input period (RE-110, still
open) -- ``ATTACK_CADENCE_MS_PROVISIONAL`` remains a labelled guess, and
this file's job is only that the gate SOME wiring installed actually runs
on the production dispatch path, not that its number is the right one.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
CADENCE_MS = mob_combat.ATTACK_CADENCE_MS_PROVISIONAL


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class MobCombatCadenceWiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
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
        self.roster = field_mobs.load_roster()
        self.target = self.roster[0].actor_identity
        roster_identities = {m.actor_identity for m in self.roster}
        self.non_mob_target = 0x999999
        while self.non_mob_target in roster_identities:
            self.non_mob_target += 1
        self.clock_ms = 0

    def _clock(self):
        return self.clock_ms / 1000.0

    def _state(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            monotonic_clock=self._clock,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        return state

    def _action_vital_pc(self, target_identity):
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
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.ACTION_VITAL)
            + legacy.u8tag(0x0B, 0)
            + body
        )

    def _attack(self, state, target=None):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            actions = state.dispatch(self.legacy.parse_outer(
                self._action_vital_pc(
                    self.target if target is None else target
                )
            ))
        return actions, buffer.getvalue()

    def _current_hp(self, state):
        return state.mob_combat_ledger.balance_of(self.target).current_hp

    # ----- construction ---------------------------------------------------

    def test_a_default_boot_opens_an_empty_cadence_ledger(self):
        state = self._state("cadence_init")
        self.assertEqual(state.mob_combat_cadence.records, ())

    # ----- first attack always lands ---------------------------------------

    def test_first_attack_from_a_fresh_session_is_accepted(self):
        state = self._state("cadence_first")
        starting_hp = self._current_hp(state)
        actions, printed = self._attack(state)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        self.assertEqual(state.mob_combat_hit_count, 1)
        self.assertLess(self._current_hp(state), starting_hp)
        self.assertNotIn("REJECTED", printed)
        self.assertEqual(state.mob_combat_cadence.identities(), (
            (
                (state.foundation.selected.identity_hi & 0xFFFFFFFF) << 32
            ) | (state.foundation.selected.identity_lo & 0xFFFFFFFF),
        ))

    # ----- spam-click within the window is silently refused ----------------

    def test_second_click_at_the_same_instant_is_rejected_and_silent(self):
        state = self._state("cadence_spam")
        self._attack(state)  # accepted, sets the deadline at t=0
        hp_after_first = self._current_hp(state)
        hit_count_after_first = state.mob_combat_hit_count

        actions, printed = self._attack(state)  # still t=0, same performer

        self.assertEqual(actions, [])
        self.assertEqual(state.mob_combat_hit_count, hit_count_after_first)
        self.assertEqual(self._current_hp(state), hp_after_first)
        self.assertIn("MOB-COMBAT-001 attack cadence REJECTED", printed)
        self.assertIn("%d ms too soon" % CADENCE_MS, printed)
        self.assertEqual(printed.count("REJECTED"), 1)
        self.assertIn(
            "mob_combat_cadence_rejected_no_reply", state.events,
        )

    def test_repeated_spam_clicks_do_not_slide_the_deadline(self):
        state = self._state("cadence_spam_burst")
        self._attack(state)  # accepted at t=0
        hp_after_first = self._current_hp(state)

        for step_ms in (100, 200, 300):
            self.clock_ms = step_ms
            actions, printed = self._attack(state)
            self.assertEqual(actions, [])
            self.assertIn(
                "%d ms too soon" % (CADENCE_MS - step_ms), printed,
            )
        self.assertEqual(self._current_hp(state), hp_after_first)

        # The window is measured from the ORIGINAL accept (t=0), not from
        # any of the three rejects above, so this must land at exactly the
        # same boundary the single-reject case does: CADENCE_MS.
        self.clock_ms = CADENCE_MS
        actions, printed = self._attack(state)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        self.assertNotIn("REJECTED", printed)
        self.assertLess(self._current_hp(state), hp_after_first)

    # ----- pf-adversary regression: a miss-click must not tax the window ---

    def test_a_click_on_a_non_monster_does_not_consume_the_cadence_window(
        self,
    ):
        """pf-adversary (round confident-ride-d9704m): before the fix, the
        gate ran on every ActionVital with a plausible target field, so an
        ActionVital aimed at something that is NOT a field mob (a
        townsperson, another player, anything outside ``roster``) silently
        spent the performer's cadence window before ``attack_from_observed_
        action`` ever got a chance to say "not a field mob".  A genuine
        first attack on a real monster shortly after was then rejected as
        "too soon", though no damage-bearing attack had ever landed.  This
        reproduces that exact sequence and proves it no longer happens.
        """
        state = self._state("cadence_missclick")

        actions, printed = self._attack(state, target=self.non_mob_target)
        self.assertEqual(actions, [])
        self.assertNotIn("REJECTED", printed)
        self.assertEqual(state.mob_combat_cadence.records, ())
        self.assertIn(
            "mob_combat_target_not_a_field_mob_no_reply", state.events,
        )

        self.clock_ms = 200  # well inside CADENCE_MS (600) of the miss-click
        starting_hp = self._current_hp(state)
        actions, printed = self._attack(state)  # a REAL first attack

        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        self.assertNotIn("REJECTED", printed)
        self.assertEqual(state.mob_combat_hit_count, 1)
        self.assertLess(self._current_hp(state), starting_hp)

    # ----- waiting out the window lands the next hit ------------------------

    def test_attack_after_the_full_window_elapses_is_accepted(self):
        state = self._state("cadence_wait")
        self._attack(state)  # accepted at t=0
        hp_after_first = self._current_hp(state)

        self.clock_ms = CADENCE_MS
        actions, printed = self._attack(state)

        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        self.assertNotIn("REJECTED", printed)
        self.assertEqual(state.mob_combat_hit_count, 2)
        self.assertLess(self._current_hp(state), hp_after_first)


if __name__ == "__main__":
    unittest.main()
