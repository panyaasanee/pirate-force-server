"""RE-157 Job 2, the REAL dispatcher.  ``tests/test_mob_combat_membership.py``
pins ``mob_combat_membership.admits()``'s fail-closed contract offline, with
no ``runtime.py`` call site involved.  This file proves the wiring itself:
``runtime.py``'s ``_dispatch_mob_combat`` now calls ``admits()`` right after
``target_is_field_mob`` is computed and before cadence is spent or the
ledger is touched, so a target that the STATIC scene roster would accept but
this session's own client was never told about (via a committed census)
cannot spend cadence or mutate combat state.

Same headless harness shape as ``tests/test_mob_combat_dispatch.py`` and
``tests/test_mob_combat_cadence_wiring.py`` (``make_state_class`` driven
directly, no socket, no client), but this file drives ``state.dispatch()``
with NO membership seeded by a shared ``_attack`` helper -- every test here
sets ``state.mob_combat_announced_membership`` (and, where it matters,
``state.mob_combat_announced_membership_generation``) by hand, explicitly,
so the exact case each test proves is visible at the call site rather than
hidden inside a harness default.

NOT proven here, same load-bearing limit every sibling combat-dispatch file
already states: whether a real attack input produces this exact ActionVital
shape, and whether a real client's own census sequencing matches what this
file constructs directly. RE-157 nonclaim 1: this guard defends a
forged/desync risk, not one proven reachable by a normal client.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_combat_membership  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
# The roster's own control row -- the practice dummy COO-RULING-20260827-1350
# approved as the thing a player can hit, same identity every sibling
# combat-dispatch file in this tree uses.
CONTROL_TARGET = 0x2000 + field_mobs.CONTROL_PLACEMENT_INDEX + 1


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class MobCombatMembershipWiringTests(unittest.TestCase):
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
        self.control_mob = next(
            m for m in self.roster if m.actor_identity == CONTROL_TARGET
        )

    # ----- harness -----------------------------------------------------

    def _state(self, token):
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
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        # Bootstrap frames pre-armed, same as the sibling dispatch files:
        # this file is about the membership guard, not login sequencing.
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

    def _attack(self, state, target_identity=CONTROL_TARGET):
        return state.dispatch(self.legacy.parse_outer(
            self._action_vital_pc(target_identity)
        ))

    def _scene_id(self, state):
        return state.foundation.selected.position.scene_id

    # ----- (a) announced target: no regression -------------------------

    def test_a_target_in_the_announced_membership_still_lands_a_hit(self):
        """A target the STATIC roster already accepts, and that THIS
        session's own client was actually told about (current scene,
        current generation), spends cadence and mutates the ledger exactly
        as it did before the guard existed.
        """
        state = self._state("membership_admits")
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                self._scene_id(state), (CONTROL_TARGET,),
                state.mob_combat_announced_membership_generation,
            )
        )
        starting_hp = state.mob_combat_ledger.balance_of(
            CONTROL_TARGET
        ).current_hp
        actions = self._attack(state)
        self.assertEqual(
            [label for label, *_rest in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        self.assertEqual(state.mob_combat_hit_count, 1)
        self.assertLess(
            state.mob_combat_ledger.balance_of(CONTROL_TARGET).current_hp,
            starting_hp,
        )
        self.assertNotIn(
            "mob_combat_target_not_announced_no_reply", state.events,
        )

    # ----- (b) static roster member, never announced: refused ----------

    def test_a_roster_member_never_announced_is_refused(self):
        """The gap RE-157 job 2 closes: a target the STATIC scene roster
        would accept, but no committed census this session ever put on
        the wire (``mob_combat_announced_membership`` still ``None``,
        the boot default), cannot spend cadence or mutate the ledger.
        """
        state = self._state("membership_none")
        self.assertIsNone(state.mob_combat_announced_membership)
        starting_hp = state.mob_combat_ledger.balance_of(
            CONTROL_TARGET
        ).current_hp
        actions = self._attack(state)
        self.assertEqual(actions, [])
        self.assertIn(
            "mob_combat_target_not_announced_no_reply", state.events,
        )
        self.assertEqual(state.mob_combat_hit_count, 0)
        self.assertEqual(
            state.mob_combat_ledger.balance_of(CONTROL_TARGET).current_hp,
            starting_hp,
        )
        self.assertEqual(state.mob_combat_ledger.generation, 0)

    def test_a_roster_member_announced_for_a_different_actor_is_refused(
        self,
    ):
        """A non-empty, current-scene, current-generation membership that
        simply does not name THIS target still refuses it -- not merely
        "any census this session" but "this exact actor, this census".
        """
        state = self._state("membership_other_actor")
        other = next(
            m for m in self.roster if m.actor_identity != CONTROL_TARGET
        )
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                self._scene_id(state), (other.actor_identity,),
                state.mob_combat_announced_membership_generation,
            )
        )
        actions = self._attack(state)
        self.assertEqual(actions, [])
        self.assertIn(
            "mob_combat_target_not_announced_no_reply", state.events,
        )
        self.assertEqual(state.mob_combat_hit_count, 0)

    # ----- (c) stale/mismatched generation: refused ---------------------

    def test_a_stale_generation_refuses_even_a_once_announced_target(self):
        """The exact same scene and the exact same actor identity, stamped
        under an OLDER generation than the session's current counter, must
        not be trusted -- a re-census (or a scene round trip back to the
        same scene id) must not let a stale announcement stand in for a
        fresh one.
        """
        state = self._state("membership_stale_generation")
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                self._scene_id(state), (CONTROL_TARGET,),
                state.mob_combat_announced_membership_generation,
            )
        )
        # A later commit bumps the counter (exactly what every real census
        # commit site in runtime.py does) without this membership record
        # being replaced -- simulating a stale record surviving past its
        # own generation.
        state.mob_combat_announced_membership_generation += 1
        actions = self._attack(state)
        self.assertEqual(actions, [])
        self.assertIn(
            "mob_combat_target_not_announced_no_reply", state.events,
        )
        self.assertEqual(state.mob_combat_hit_count, 0)

    # ----- (d) scene mismatch: refused -----------------------------------

    def test_a_scene_mismatch_refuses_even_a_once_announced_target(self):
        """The exact same actor identity and the exact same generation,
        stamped for a DIFFERENT scene than the one the character currently
        stands in, must not be trusted -- the departure scene's own
        announcement can never authorize a hit in the scene arrived at.
        """
        state = self._state("membership_scene_mismatch")
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                self._scene_id(state) + 1, (CONTROL_TARGET,),
                state.mob_combat_announced_membership_generation,
            )
        )
        actions = self._attack(state)
        self.assertEqual(actions, [])
        self.assertIn(
            "mob_combat_target_not_announced_no_reply", state.events,
        )
        self.assertEqual(state.mob_combat_hit_count, 0)

    # ----- a miss-click (not a field mob at all) is unaffected -----------

    def test_a_non_field_mob_target_is_still_refused_by_the_older_gate(
        self,
    ):
        """The membership guard only ever fires once ``target_is_field_mob``
        is already ``True`` -- a target outside the STATIC roster entirely
        is refused by the existing, older gate and names itself with that
        gate's own event, not the membership one, whether or not a
        membership record happens to be set.
        """
        state = self._state("membership_not_a_mob")
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                self._scene_id(state), (CONTROL_TARGET,),
                state.mob_combat_announced_membership_generation,
            )
        )
        selected = state.foundation.selected
        performer = (
            ((selected.identity_hi & 0xFFFFFFFF) << 32)
            | (selected.identity_lo & 0xFFFFFFFF)
        )
        outsider = performer + 1
        actions = self._attack(state, outsider)
        self.assertEqual(actions, [])
        self.assertIn(
            "mob_combat_target_not_a_field_mob_no_reply", state.events,
        )
        self.assertNotIn(
            "mob_combat_target_not_announced_no_reply", state.events,
        )


if __name__ == "__main__":
    unittest.main()
