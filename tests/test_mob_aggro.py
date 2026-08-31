"""MOB-AGGRO-001 -- the server-side threat table and decision tick, pure logic.

What this file proves, and where the proof stops:

  * DETERMINISM: no randomness exists in the module; the same profile + state
    + observation produce the identical TickResult on repeated calls, and a
    scripted four-tick fight renders one pinned list of ASCII lines;
  * every REFUSAL fires by name and nothing is silently clamped or coerced --
    non-numeric values (string radius, bool range, string position), non-
    finite values, non-positive radii, a leash smaller than the aggro radius,
    a home radius outside the leash, an attack range outside the aggro
    radius, a cadence below one, a non-positive identity, a damage outside
    signed 32-bit range, a non-int hp, a non-bool alive, a duplicate player
    identity, and a rehydrated state with an unknown phase or a malformed
    threat table;
  * the declared no-ops: a NON-NEGATIVE damage (meaning unknown, MISS
    included) adds no threat, and RETURN/DEAD phases absorb no threat;
  * the DISTANCE boundaries are inclusive and 3D: a player exactly ON the
    aggro radius is inside, one epsilon beyond is outside;
  * the THREAT rules: abs() of a signed damage, saturation at i32 max, MISS
    (damage 0) adds nothing, the proximity floor is 1 and never accumulates;
  * the SELECTION rules: highest threat wins, ties break to the LOWEST
    identity, selection is re-evaluated every tick, and an acquired attacker
    is kept even outside the aggro radius until leash or forgiveness;
  * the CADENCE: attacks fire only inside attack range, every N ticks, and an
    approach tick still advances the counter so arrival can attack at once;
  * the LEASH: breaking it clears all threat and yields RETURN intents until
    the mob is back inside the home radius, which yields IDLE that tick;
  * DEATH is absorbing and clears the table; damage folded into a dead mob's
    state is a no-op;
  * PURITY: frozen inputs are never mutated;
  * CONTAINMENT: the module imports only stdlib, has no import-time side
    effects, is imported by no other module in ``src/``, is pure ASCII and
    cp874-safe, and declares production_allowed False, dispatch-reachable
    False and attack-intent deliverable False.

NOT proven here: anything about a client, a wire, or a database.  The rules
are OUR design (the original server is unrecoverable forever); the attack
decision is named UNDELIVERABLE because Door B (round-98 draft) has no proven
server->client transport, and no emitter for any intent exists anywhere.
"""
from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_aggro as ma  # noqa: E402

MODULE_SOURCE_PATH = ROOT / "src" / "pirateforce_foundation" / "mob_aggro.py"
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"

ORIGIN = (0.0, 0.0, 0.0)


def profile(**overrides):
    values = dict(
        aggro_radius=10.0,
        leash_radius=30.0,
        home_radius=2.0,
        attack_range=3.0,
        attack_cadence_ticks=2,
        # Every test written before 2026-08-26 assumed a monster that charges,
        # because that was the only monster the profile could express.  The
        # default keeps those tests saying what they were written to say; the
        # tests that the mined n_OFFESIVE column added pass offensive=False.
        offensive=True,
    )
    values.update(overrides)
    return ma.MobAiProfile(**values)


def player(identity, position, alive=True):
    return ma.PlayerObservation(identity=identity, position=position,
                                alive=alive)


def observe(mob_position=ORIGIN, hp=100, players=()):
    return ma.MobObservation(position=mob_position, hp=hp,
                             players=tuple(players))


class ProfileContractTests(unittest.TestCase):
    def test_a_coherent_profile_builds_and_freezes_floats(self):
        built = profile()
        self.assertEqual(built.aggro_radius, 10.0)
        self.assertIsInstance(built.aggro_radius, float)

    def test_every_profile_refusal_fires_by_name(self):
        cases = [
            (dict(aggro_radius=float("nan")),
             ma.REFUSE_PROFILE_VALUE_NOT_FINITE),
            (dict(leash_radius=float("inf")),
             ma.REFUSE_PROFILE_VALUE_NOT_FINITE),
            # A ZERO AGGRO RADIUS USED TO BE REFUSED HERE.  It is a real row:
            # ~~ten~~ six of the thirteen bg0001 rows have n_AGGRO = 0 as of
            # round szdkgs (the four dummies carry 3000).  The case
            # is kept, inverted, rather than deleted.
            (dict(aggro_radius=-1.0), ma.REFUSE_PROFILE_RADIUS_NOT_POSITIVE),
            (dict(home_radius=0.0), ma.REFUSE_PROFILE_RADIUS_NOT_POSITIVE),
            (dict(attack_range=-1.0), ma.REFUSE_PROFILE_RADIUS_NOT_POSITIVE),
            (dict(offensive=1), ma.REFUSE_OFFENSIVE_NOT_BOOL),
            (dict(offensive=None), ma.REFUSE_OFFENSIVE_NOT_BOOL),
            (dict(leash_radius=5.0),
             ma.REFUSE_PROFILE_LEASH_SMALLER_THAN_AGGRO),
            (dict(home_radius=31.0), ma.REFUSE_PROFILE_HOME_OUTSIDE_LEASH),
            # THE BOUND MOVED from the aggro radius to the leash, so 11.0 -
            # outside the 10.0 aggro radius, inside the 30.0 leash - is now
            # ACCEPTED, and only a range outside the LEASH is refused.  A
            # monster you hit must be able to hit back, and a non-offensive
            # monster (aggro radius 0) is not an unarmed one.
            (dict(attack_range=31.0),
             ma.REFUSE_PROFILE_ATTACK_RANGE_OUTSIDE_LEASH),
            (dict(attack_cadence_ticks=0),
             ma.REFUSE_PROFILE_CADENCE_NOT_POSITIVE),
            (dict(attack_cadence_ticks=True),
             ma.REFUSE_PROFILE_CADENCE_NOT_POSITIVE),
            (dict(attack_cadence_ticks=2.0),
             ma.REFUSE_PROFILE_CADENCE_NOT_POSITIVE),
            (dict(aggro_radius="10"), ma.REFUSE_VALUE_NOT_NUMERIC),
            (dict(attack_range=True), ma.REFUSE_VALUE_NOT_NUMERIC),
        ]
        for overrides, reason in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ma.MobAiContractError) as caught:
                    profile(**overrides)
                self.assertEqual(caught.exception.reason, reason)

    def test_every_refusal_reason_is_registered(self):
        for overrides in (dict(aggro_radius=-1.0), dict(leash_radius=5.0)):
            with self.assertRaises(ma.MobAiContractError) as caught:
                profile(**overrides)
            self.assertIn(caught.exception.reason,
                          ma.MOB_AGGRO_REFUSAL_REASONS)


class ObservationContractTests(unittest.TestCase):
    def test_player_identity_must_be_a_positive_int(self):
        for bad in (0, -1, True, "7"):
            with self.subTest(bad=bad):
                with self.assertRaises(ma.MobAiContractError) as caught:
                    player(bad, (1.0, 0.0, 0.0))
                self.assertEqual(caught.exception.reason,
                                 ma.REFUSE_IDENTITY_NOT_POSITIVE)

    def test_positions_must_be_finite_triples(self):
        with self.assertRaises(ma.MobAiContractError) as caught:
            player(7, (float("nan"), 0.0, 0.0))
        self.assertEqual(caught.exception.reason,
                         ma.REFUSE_POSITION_NOT_FINITE)
        with self.assertRaises(ma.MobAiContractError):
            observe(mob_position=(0.0, float("inf"), 0.0))
        with self.assertRaises(ma.MobAiContractError):
            ma.initial_state((0.0, 0.0))

    def test_a_string_position_component_is_refused_by_name_not_coerced(self):
        with self.assertRaises(ma.MobAiContractError) as caught:
            player(7, ("1.0", 0.0, 0.0))
        self.assertEqual(caught.exception.reason,
                         ma.REFUSE_VALUE_NOT_NUMERIC)

    def test_alive_must_be_an_actual_bool(self):
        with self.assertRaises(ma.MobAiContractError) as caught:
            player(7, (1.0, 0.0, 0.0), alive="false")
        self.assertEqual(caught.exception.reason, ma.REFUSE_ALIVE_NOT_BOOL)

    def test_hp_must_be_an_int_so_nan_hp_cannot_slip_through(self):
        for bad in ("0", 0.0, float("nan"), True):
            with self.subTest(bad=bad):
                with self.assertRaises(ma.MobAiContractError) as caught:
                    observe(hp=bad)
                self.assertEqual(caught.exception.reason,
                                 ma.REFUSE_HP_NOT_INT)

    def test_duplicate_player_identities_are_refused_by_name(self):
        with self.assertRaises(ma.MobAiContractError) as caught:
            observe(players=[player(7, (2.0, 0.0, 0.0)),
                             player(7, (9000.0, 0.0, 0.0))])
        self.assertEqual(caught.exception.reason,
                         ma.REFUSE_DUPLICATE_PLAYER_IDENTITY)


class StateContractTests(unittest.TestCase):
    def test_a_rehydrated_state_is_validated_like_everything_else(self):
        cases = [
            (dict(phase="combat"), ma.REFUSE_PHASE_UNKNOWN),
            (dict(leash_origin=(float("nan"), 0.0, 0.0)),
             ma.REFUSE_POSITION_NOT_FINITE),
            (dict(threat=((7, 0),)), ma.REFUSE_STATE_MALFORMED),
            (dict(threat=((7, ma.THREAT_MAX + 1),)),
             ma.REFUSE_STATE_MALFORMED),
            (dict(threat=((9, 1), (7, 1))), ma.REFUSE_STATE_MALFORMED),
            (dict(threat=((7, 1), (7, 2))), ma.REFUSE_STATE_MALFORMED),
            (dict(target_identity=0), ma.REFUSE_STATE_MALFORMED),
            (dict(ticks_since_attack=-1), ma.REFUSE_STATE_MALFORMED),
        ]
        base = dict(phase=ma.PHASE_IDLE, leash_origin=ORIGIN, threat=(),
                    target_identity=None, ticks_since_attack=0)
        for overrides, reason in cases:
            with self.subTest(overrides=overrides):
                values = dict(base)
                values.update(overrides)
                with self.assertRaises(ma.MobAiContractError) as caught:
                    ma.MobAiState(**values)
                self.assertEqual(caught.exception.reason, reason)

    def test_a_well_formed_hand_built_state_constructs_and_describes_ascii(self):
        state = ma.MobAiState(phase=ma.PHASE_AGGRO, leash_origin=ORIGIN,
                              threat=((7, 63),), target_identity=7,
                              ticks_since_attack=1)
        result = ma.TickResult(state, ma.MobAiIntent(ma.INTENT_NONE, None))
        for line in ma.describe_mob_ai(result):
            line.encode("ascii")
            line.encode("cp874")


class ThreatTests(unittest.TestCase):
    def setUp(self):
        self.state = ma.initial_state(ORIGIN)

    def test_a_negative_damage_model_hit_adds_its_absolute_value(self):
        folded = ma.apply_damage_threat(self.state, 7, -63)
        self.assertEqual(folded.threat, ((7, 63),))

    def test_threat_accumulates_across_hits(self):
        folded = ma.apply_damage_threat(self.state, 7, -63)
        folded = ma.apply_damage_threat(folded, 7, -379)
        self.assertEqual(folded.threat, ((7, 442),))

    def test_threat_saturates_at_i32_max(self):
        folded = ma.apply_damage_threat(self.state, 7, -ma.DAMAGE_I32_MAX)
        folded = ma.apply_damage_threat(folded, 7, -ma.DAMAGE_I32_MAX)
        self.assertEqual(folded.threat, ((7, ma.THREAT_MAX),))

    def test_a_miss_adds_no_threat_and_is_not_an_error(self):
        folded = ma.apply_damage_threat(self.state, 7, 0)
        self.assertEqual(folded.threat, ())

    def test_a_positive_value_adds_no_threat_its_meaning_is_unknown(self):
        folded = ma.apply_damage_threat(self.state, 7, 500)
        self.assertEqual(folded.threat, ())

    def test_a_returning_mob_absorbs_no_damage_threat(self):
        returning = ma.tick(profile(), self.state,
                            observe(mob_position=(31.0, 0.0, 0.0))).state
        self.assertEqual(returning.phase, ma.PHASE_RETURN)
        folded = ma.apply_damage_threat(returning, 7, -5000)
        self.assertEqual(folded.threat, ())
        self.assertEqual(folded.phase, ma.PHASE_RETURN)

    def test_damage_outside_i32_is_refused_by_name(self):
        for bad in (ma.DAMAGE_I32_MAX + 1, ma.DAMAGE_I32_MIN - 1, 1.5, False):
            with self.subTest(bad=bad):
                with self.assertRaises(ma.MobAiContractError) as caught:
                    ma.apply_damage_threat(self.state, 7, bad)
                self.assertEqual(caught.exception.reason,
                                 ma.REFUSE_DAMAGE_OUTSIDE_I32)

    def test_attacker_identity_is_validated(self):
        with self.assertRaises(ma.MobAiContractError) as caught:
            ma.apply_damage_threat(self.state, 0, -63)
        self.assertEqual(caught.exception.reason,
                         ma.REFUSE_IDENTITY_NOT_POSITIVE)

    def test_the_input_state_is_never_mutated(self):
        before = self.state.threat
        ma.apply_damage_threat(self.state, 7, -63)
        self.assertEqual(self.state.threat, before)


class AcquisitionTests(unittest.TestCase):
    def test_a_player_exactly_on_the_aggro_radius_is_acquired(self):
        result = ma.tick(profile(), ma.initial_state(ORIGIN),
                         observe(players=[player(7, (10.0, 0.0, 0.0))]))
        self.assertEqual(result.state.phase, ma.PHASE_AGGRO)
        self.assertEqual(result.state.target_identity, 7)
        self.assertEqual(result.state.threat, ((7, ma.PROXIMITY_THREAT),))

    def test_a_player_just_beyond_the_aggro_radius_is_not_acquired(self):
        result = ma.tick(profile(), ma.initial_state(ORIGIN),
                         observe(players=[player(7, (10.000001, 0.0, 0.0))]))
        self.assertEqual(result.state.phase, ma.PHASE_IDLE)
        self.assertIsNone(result.state.target_identity)
        self.assertEqual(result.intent.kind, ma.INTENT_NONE)

    def test_the_distance_is_3d(self):
        result = ma.tick(profile(), ma.initial_state(ORIGIN),
                         observe(players=[player(7, (6.0, 6.0, 6.0))]))
        self.assertEqual(result.state.phase, ma.PHASE_IDLE)

    def test_a_dead_player_inside_the_radius_is_not_acquired(self):
        result = ma.tick(profile(), ma.initial_state(ORIGIN),
                         observe(players=[player(7, (5.0, 0.0, 0.0),
                                                 alive=False)]))
        self.assertEqual(result.state.phase, ma.PHASE_IDLE)

    def test_a_non_offensive_mob_acquires_nobody_at_any_distance(self):
        # THE FLAG AND THE RADIUS ARE DELIBERATELY DECORRELATED HERE.  In every
        # profile the roster can build they agree, so an adversarial mutation
        # that replaced `if profile.offensive:` with `if aggro_radius > 0` left
        # the WHOLE SUITE green - the field was behaviourally indistinguishable
        # from the thing it was added to be distinguishable from.  These two
        # cases are the only place in the repo that can tell them apart.
        passive = profile(offensive=False, aggro_radius=10.0)
        for offset in (0.0, 1.0, 5.0, 10.0):
            with self.subTest(offset=offset):
                result = ma.tick(passive, ma.initial_state(ORIGIN), observe(
                    players=[player(7, (offset, 0.0, 0.0))]))
                self.assertEqual(result.state.phase, ma.PHASE_IDLE)
                self.assertEqual(result.state.threat, ())
                self.assertIsNone(result.state.target_identity)

    def test_an_offensive_mob_with_a_zero_radius_acquires_nobody_either(self):
        # The other half of the same decorrelation: a zero radius must not
        # admit a player standing exactly on the monster.  It does not, and
        # this is the case that proves _within's inclusive boundary is not the
        # thing keeping the passive monsters passive.
        charging_but_blind = profile(offensive=True, aggro_radius=0.0)
        result = ma.tick(charging_but_blind, ma.initial_state(ORIGIN), observe(
            players=[player(7, ORIGIN)]))
        self.assertEqual(result.state.phase, ma.PHASE_AGGRO)
        # ...and with the flag off, the identical observation acquires nobody.
        blind_and_passive = profile(offensive=False, aggro_radius=0.0)
        result = ma.tick(blind_and_passive, ma.initial_state(ORIGIN), observe(
            players=[player(7, ORIGIN)]))
        self.assertEqual(result.state.phase, ma.PHASE_IDLE)

    def test_a_non_offensive_mob_that_is_hit_still_fights_back(self):
        passive = profile(offensive=False, aggro_radius=0.0)
        pulled = ma.apply_damage_threat(ma.initial_state(ORIGIN), 7, -50)
        result = ma.tick(passive, pulled, observe(
            players=[player(7, (1.0, 0.0, 0.0))]))
        self.assertEqual(result.state.phase, ma.PHASE_AGGRO)
        self.assertEqual(result.state.target_identity, 7)

    def test_a_saturating_fold_returns_the_very_same_state_object(self):
        # Two threat-reporting predicates exist in this project, one comparing
        # by identity (mob_combat.threat_was_recorded) and one by value
        # (mob_ai_control's step).  A hit on a row already at THREAT_MAX used
        # to build a NEW state EQUAL to the old, so the two answered
        # oppositely about the same fold and the console line named three
        # causes, none of which applied.
        saturated = ma.apply_damage_threat(
            ma.initial_state(ORIGIN), 7, -ma.THREAT_MAX)
        self.assertEqual(saturated.threat, ((7, ma.THREAT_MAX),))
        again = ma.apply_damage_threat(saturated, 7, -1)
        self.assertIs(again, saturated)
        self.assertEqual(again, saturated)

    def test_the_proximity_floor_never_accumulates(self):
        state = ma.initial_state(ORIGIN)
        snapshot = observe(players=[player(7, (5.0, 0.0, 0.0))])
        for _ in range(3):
            state = ma.tick(profile(), state, snapshot).state
        self.assertEqual(state.threat, ((7, ma.PROXIMITY_THREAT),))


class SelectionTests(unittest.TestCase):
    def test_higher_damage_pulls_aggro(self):
        state = ma.initial_state(ORIGIN)
        state = ma.apply_damage_threat(state, 7, -63)
        state = ma.apply_damage_threat(state, 9, -379)
        snapshot = observe(players=[player(7, (5.0, 0.0, 0.0)),
                                    player(9, (6.0, 0.0, 0.0))])
        result = ma.tick(profile(), state, snapshot)
        self.assertEqual(result.state.target_identity, 9)

    def test_ties_break_to_the_lowest_identity(self):
        snapshot = observe(players=[player(9, (5.0, 0.0, 0.0)),
                                    player(7, (6.0, 0.0, 0.0))])
        result = ma.tick(profile(), ma.initial_state(ORIGIN), snapshot)
        self.assertEqual(result.state.target_identity, 7)

    def test_an_acquired_attacker_is_kept_outside_the_aggro_radius(self):
        state = ma.apply_damage_threat(ma.initial_state(ORIGIN), 7, -63)
        snapshot = observe(players=[player(7, (20.0, 0.0, 0.0))])
        result = ma.tick(profile(), state, snapshot)
        self.assertEqual(result.state.phase, ma.PHASE_AGGRO)
        self.assertEqual(result.state.target_identity, 7)
        self.assertEqual(result.intent.kind, ma.INTENT_FACE_AND_APPROACH)

    def test_an_absent_target_is_forgiven_and_the_next_takes_over(self):
        state = ma.initial_state(ORIGIN)
        state = ma.apply_damage_threat(state, 7, -379)
        state = ma.apply_damage_threat(state, 9, -63)
        snapshot = observe(players=[player(9, (5.0, 0.0, 0.0))])
        result = ma.tick(profile(), state, snapshot)
        self.assertEqual(result.state.target_identity, 9)
        self.assertEqual(result.state.threat, ((9, 63),))

    def test_everyone_gone_returns_the_mob_to_idle(self):
        state = ma.apply_damage_threat(ma.initial_state(ORIGIN), 7, -63)
        result = ma.tick(profile(), state, observe(players=[]))
        self.assertEqual(result.state.phase, ma.PHASE_IDLE)
        self.assertEqual(result.state.threat, ())
        self.assertEqual(result.state.ticks_since_attack, 0)


class CadenceTests(unittest.TestCase):
    def test_the_attack_fires_every_n_ticks_inside_attack_range(self):
        state = ma.initial_state(ORIGIN)
        snapshot = observe(players=[player(7, (2.0, 0.0, 0.0))])
        kinds = []
        for _ in range(5):
            result = ma.tick(profile(attack_cadence_ticks=2), state, snapshot)
            state = result.state
            kinds.append(result.intent.kind)
        self.assertEqual(kinds, [
            ma.INTENT_NONE,
            ma.INTENT_ATTACK_UNDELIVERABLE,
            ma.INTENT_NONE,
            ma.INTENT_ATTACK_UNDELIVERABLE,
            ma.INTENT_NONE,
        ])

    def test_cadence_one_attacks_every_tick(self):
        state = ma.initial_state(ORIGIN)
        snapshot = observe(players=[player(7, (2.0, 0.0, 0.0))])
        for _ in range(3):
            result = ma.tick(profile(attack_cadence_ticks=1), state, snapshot)
            state = result.state
            self.assertEqual(result.intent.kind,
                             ma.INTENT_ATTACK_UNDELIVERABLE)

    def test_an_approach_tick_advances_the_counter_so_arrival_attacks(self):
        state = ma.initial_state(ORIGIN)
        far = observe(players=[player(7, (8.0, 0.0, 0.0))])
        near = observe(players=[player(7, (2.0, 0.0, 0.0))])
        first = ma.tick(profile(attack_cadence_ticks=2), state, far)
        self.assertEqual(first.intent.kind, ma.INTENT_FACE_AND_APPROACH)
        second = ma.tick(profile(attack_cadence_ticks=2), first.state, near)
        self.assertEqual(second.intent.kind, ma.INTENT_ATTACK_UNDELIVERABLE)

    def test_the_counter_is_clamped_at_the_cadence(self):
        state = ma.initial_state(ORIGIN)
        far = observe(players=[player(7, (8.0, 0.0, 0.0))])
        for _ in range(10):
            state = ma.tick(profile(attack_cadence_ticks=3), state, far).state
        self.assertEqual(state.ticks_since_attack, 3)

    def test_the_attack_target_rides_the_intent(self):
        state = ma.initial_state(ORIGIN)
        snapshot = observe(players=[player(7, (2.0, 0.0, 0.0))])
        result = ma.tick(profile(attack_cadence_ticks=1), state, snapshot)
        self.assertEqual(result.intent.target_identity, 7)


class LeashTests(unittest.TestCase):
    def test_breaking_the_leash_clears_threat_and_returns(self):
        state = ma.apply_damage_threat(ma.initial_state(ORIGIN), 7, -379)
        snapshot = observe(mob_position=(31.0, 0.0, 0.0),
                           players=[player(7, (30.0, 0.0, 0.0))])
        result = ma.tick(profile(), state, snapshot)
        self.assertEqual(result.state.phase, ma.PHASE_RETURN)
        self.assertEqual(result.state.threat, ())
        self.assertEqual(result.intent.kind, ma.INTENT_RETURN_TO_LEASH)

    def test_the_mob_exactly_on_the_leash_radius_holds_its_ground(self):
        state = ma.apply_damage_threat(ma.initial_state(ORIGIN), 7, -63)
        snapshot = observe(mob_position=(30.0, 0.0, 0.0),
                           players=[player(7, (29.0, 0.0, 0.0))])
        result = ma.tick(profile(), state, snapshot)
        self.assertEqual(result.state.phase, ma.PHASE_AGGRO)

    def test_no_acquisition_while_returning(self):
        returning = ma.tick(
            profile(), ma.initial_state(ORIGIN),
            observe(mob_position=(31.0, 0.0, 0.0))).state
        snapshot = observe(mob_position=(15.0, 0.0, 0.0),
                           players=[player(7, (15.0, 1.0, 0.0))])
        result = ma.tick(profile(), returning, snapshot)
        self.assertEqual(result.state.phase, ma.PHASE_RETURN)
        self.assertEqual(result.state.threat, ())
        self.assertEqual(result.intent.kind, ma.INTENT_RETURN_TO_LEASH)

    def test_the_return_completes_inside_the_home_radius(self):
        returning = ma.tick(
            profile(), ma.initial_state(ORIGIN),
            observe(mob_position=(31.0, 0.0, 0.0))).state
        result = ma.tick(profile(), returning,
                         observe(mob_position=(2.0, 0.0, 0.0)))
        self.assertEqual(result.state.phase, ma.PHASE_IDLE)
        self.assertEqual(result.intent.kind, ma.INTENT_NONE)

    def test_after_coming_home_the_mob_can_acquire_again(self):
        state = ma.tick(
            profile(), ma.initial_state(ORIGIN),
            observe(mob_position=(31.0, 0.0, 0.0))).state
        state = ma.tick(profile(), state,
                        observe(mob_position=(1.0, 0.0, 0.0))).state
        result = ma.tick(profile(), state,
                         observe(players=[player(7, (5.0, 0.0, 0.0))]))
        self.assertEqual(result.state.phase, ma.PHASE_AGGRO)


class DeathTests(unittest.TestCase):
    def test_hp_zero_kills_and_clears(self):
        state = ma.apply_damage_threat(ma.initial_state(ORIGIN), 7, -63)
        result = ma.tick(profile(), state,
                         observe(hp=0, players=[player(7, (2.0, 0.0, 0.0))]))
        self.assertEqual(result.state.phase, ma.PHASE_DEAD)
        self.assertEqual(result.state.threat, ())
        self.assertEqual(result.intent.kind, ma.INTENT_NONE)

    def test_dead_is_absorbing_even_if_hp_returns(self):
        dead = ma.tick(profile(), ma.initial_state(ORIGIN),
                       observe(hp=0)).state
        result = ma.tick(profile(), dead,
                         observe(hp=100, players=[player(7, (2.0, 0.0, 0.0))]))
        self.assertEqual(result.state.phase, ma.PHASE_DEAD)
        self.assertEqual(result.intent.kind, ma.INTENT_NONE)

    def test_damage_folded_into_a_dead_mob_is_a_no_op(self):
        dead = ma.tick(profile(), ma.initial_state(ORIGIN),
                       observe(hp=0)).state
        folded = ma.apply_damage_threat(dead, 7, -63)
        self.assertEqual(folded.threat, ())


PINNED_FIGHT = (
    "mob_aggro|MOB-AGGRO-001|phase=aggro|target=7|cadence=1"
    "|intent=face_and_approach|intent_target=7",
    "threat|identity=7|value=63",
    "mob_aggro|MOB-AGGRO-001|phase=aggro|target=7|cadence=0"
    "|intent=attack_undeliverable|intent_target=7",
    "threat|identity=7|value=63",
    "mob_aggro|MOB-AGGRO-001|phase=aggro|target=7|cadence=1"
    "|intent=none|intent_target=7",
    "threat|identity=7|value=63",
    "mob_aggro|MOB-AGGRO-001|phase=idle|target=-|cadence=0"
    "|intent=none|intent_target=-",
)


def scripted_fight():
    built = profile()
    state = ma.apply_damage_threat(ma.initial_state(ORIGIN), 7, -63)
    lines = []
    for snapshot in (
        observe(players=[player(7, (5.0, 0.0, 0.0))]),
        observe(players=[player(7, (2.0, 0.0, 0.0))]),
        observe(players=[player(7, (2.0, 0.0, 0.0))]),
        observe(players=[player(7, (2.0, 0.0, 0.0), alive=False)]),
    ):
        result = ma.tick(built, state, snapshot)
        state = result.state
        lines.extend(ma.describe_mob_ai(result))
    return tuple(lines)


class DeterminismTests(unittest.TestCase):
    def test_the_scripted_fight_renders_the_pinned_lines(self):
        self.assertEqual(scripted_fight(), PINNED_FIGHT)

    def test_the_scripted_fight_is_identical_on_a_second_run(self):
        self.assertEqual(scripted_fight(), scripted_fight())

    def test_the_rendering_is_ascii(self):
        for line in scripted_fight():
            line.encode("ascii")

    def test_the_threat_table_representation_is_sorted_and_unique(self):
        state = ma.initial_state(ORIGIN)
        state = ma.apply_damage_threat(state, 9, -1)
        state = ma.apply_damage_threat(state, 7, -1)
        self.assertEqual(state.threat, ((7, 1), (9, 1)))


class VocabularyTests(unittest.TestCase):
    def test_the_attack_intent_says_undeliverable_in_its_name(self):
        self.assertIn("undeliverable", ma.INTENT_ATTACK_UNDELIVERABLE)
        self.assertIs(ma.ATTACK_INTENT_DELIVERABLE, False)

    def test_the_vocabularies_are_complete(self):
        self.assertEqual(ma.MOB_AGGRO_PHASES,
                         ("idle", "aggro", "return", "dead"))
        self.assertEqual(len(ma.MOB_AGGRO_INTENTS), 4)
        self.assertEqual(len(set(ma.MOB_AGGRO_REFUSAL_REASONS)),
                         len(ma.MOB_AGGRO_REFUSAL_REASONS))


class ContainmentTests(unittest.TestCase):
    """Pure server logic: no wire, no database, no dispatch, no scenario."""

    def setUp(self):
        self.source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def test_the_module_is_ascii_and_cp874_safe(self):
        self.source.encode("ascii")
        self.source.encode("cp874")

    def test_the_module_imports_only_stdlib_and_nothing_cross_layer(self):
        imported = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        self.assertEqual(imported, {"__future__", "dataclasses", "math",
                                    "typing"})

    def test_the_module_has_no_import_time_side_effects(self):
        allowed = (
            ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign,
            ast.ClassDef, ast.FunctionDef,
        )
        for node in self.tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value,
                                                         ast.Constant):
                continue  # the module docstring
            self.assertIsInstance(node, allowed)

    def test_the_module_never_imports_a_clock_or_randomness(self):
        imported = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        for banned in ("random", "time", "datetime", "secrets"):
            self.assertNotIn(banned, imported)

    def test_the_lane_is_not_reachable_from_production_dispatch(self):
        # RETIRED 2026-08-26 and INVERTED IN PLACE, kept under its old name so
        # that a reader who greps it in an older round note lands here and
        # reads why it says the opposite of what it used to.
        #
        # It used to assert production_allowed is False and that NOTHING in
        # src/ imports this module.  COO-DECISION 2026-08-26T04:02+07:00,
        # section 2, ruled that arrangement the hole rather than the safeguard:
        # the damage driver reached this lane through a HANDLE ARGUMENT, and no
        # scan of src/ can see an argument, so "nothing imports it" was a true
        # sentence that protected nothing.  The order was to promote the module
        # where the scan CAN see it.
        #
        # So the assertion is inverted, and what it now defends is the shape of
        # the promotion: exactly ONE importer, the controller, and the damage
        # driver's wiring line STILL does not name this module - because if it
        # did, the argument-shaped edge would be back.
        #
        # WIDENED round 256rvs: mob_ai_scheduler.py is a SECOND importer, and
        # it is not a second controller -- it owns no AI_STATE mutation, it
        # only calls mob_ai_control.tick_step/commit_step (the one controller
        # this comment already names) and imports mob_aggro solely to build
        # the MobObservation/PlayerObservation inputs those calls need.  The
        # invariant this test defends ("one controller") still holds; what
        # changed is that a controller can now have more than one CALLER, the
        # same relationship mob_ai_control already has with runtime.py.
        self.assertIs(ma.production_allowed, True)
        self.assertIs(ma.MOB_AGGRO_IMPORTED_BY_A_PRODUCTION_MODULE, True)
        # Dispatch reachability is still False and that is still honest: the
        # last unbuilt step is one call in runtime.py, which is the chief's.
        self.assertIs(ma.MOB_AGGRO_DISPATCH_REACHABLE, False)
        importers = []
        mentions = []
        for path in sorted(SRC_ROOT.glob("*.py")):
            if path.name == "mob_aggro.py":
                continue
            source = path.read_text(encoding="utf-8")
            if "mob_aggro" not in source:
                continue
            mentions.append(path.name)
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""] + [
                        alias.name for alias in node.names]
                else:
                    continue
                if any("mob_aggro" in name for name in names):
                    importers.append(path.name)
        self.assertEqual(
            sorted(importers),
            sorted([ma.MOB_AGGRO_IMPORTER + ".py", "mob_ai_scheduler.py"]))
        self.assertEqual(
            sorted(mentions),
            ["mob_ai_control.py", "mob_ai_scheduler.py", "mob_combat.py"])
        # The edge that must NOT come back: the damage driver's wiring line
        # still passes None, so threat never arrives through an argument the
        # scan above cannot see.  It arrives through the importer named on the
        # line above, after the combat commit.
        from pirateforce_foundation import mob_combat, mob_ai_control
        self.assertIs(mob_combat.MOB_COMBAT_THREAT_HANDLE_IS_OPTIONAL, True)
        self.assertNotIn("mob_aggro", mob_combat.MOB_COMBAT_WIRING)
        self.assertEqual(mob_combat.MOB_COMBAT_THREAT_FOLD_OWNER,
                         "mob_ai_control.damage_step")
        self.assertIs(mob_ai_control.production_allowed, True)

    def test_the_module_declares_which_rules_are_ours(self):
        self.assertIn("[OUR DESIGN]", self.source)
        self.assertIn("NONCLAIMS", self.source)
        for reading in (
            "threat_is_abs_damage_saturating_at_i32_max",
            "nonnegative_damage_including_miss_adds_no_threat_meaning_unknown",
            "return_and_dead_phases_absorb_no_damage_threat",
            "ties_broken_by_lowest_identity",
            "phase_dead_is_absorbing_revival_not_modeled",
        ):
            self.assertIn(reading, ma.MOB_AGGRO_CHOSEN_READINGS)


if __name__ == "__main__":
    unittest.main()
