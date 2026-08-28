"""LANE-B, addendum-G closing proof: one hit and one death do NOT empty the world.

WHY THIS FILE EXISTS, GIVEN THAT tests/test_mob_combat_dispatch.py ALREADY
HAS TWO ``*_recomposes_*_over_115`` TESTS.

Those two tests prove the dispatcher's frame EQUALS what
``mob_death.hostile_census_frames`` returns for the same inputs.  That pins
the runtime.py call site against the encoder, which is exactly what
CORE-REQUEST-008 needed at the time, and it is genuinely strong: mutating
the encoder to compose only the target's own roster row turns both of them
red.  What it cannot see is a shortfall that moves BOTH sides of its own
equality at once, because the expected value is recomputed from the same
function the dispatcher just called.

MEASURED, not argued (round rbuta4, both mutations run against the tree):

  * encoder composes roster[:1] / actor_count=1
      -> test_mob_combat_dispatch.py  2 failed, 10 passed   (caught)
      -> this file                    5 failed,  2 passed   (caught)
  * encoder composes actor_count-20, every roster member and the target
    still present -- i.e. twenty TOWNSPEOPLE silently dropped from every
    hit and death frame
      -> test_mob_combat_dispatch.py  12 passed             (BLIND)
      -> this file                     4 failed, 3 passed   (caught)

The second mutation is the world wipe as a player would meet it: the monster
he is hitting behaves perfectly while the town thins out behind him.  The
client is confirmed replace-by-omission
(``pf_bridge/notes_to_chief/20260826_2223_RE-092-RESULT-REPLACE-BY-OMISSION-
NETWORK-ACTOR-SCOPE.md``), so "fewer bodies in the frame" IS the wipe, not a
step toward it.  This file closes that hole by measuring every frame against
the ARRIVAL census the same session actually sent, which no mutation of the
composer can move.

The same hole exists in the console token an attended round is told to grep.
``MOB_COMBAT_BAR_CENSUS_RECOMPOSE actor_count=115`` prints
``self.world_census_actor_count`` -- the number read off session state BEFORE
composing -- so the line says 115 whether the frame that follows carries 115
bodies or three.  A tester who greps it is reading an INPUT, not a result.
Observed directly under the first mutation above: the console printed
``MOB_DEATH_FRAMES_CENSUS_RECOMPOSE actor_count=115`` over a frame carrying
one body.  Two tests here pin the token against the bodies actually sent, so
the attended instruction in GAME_TEST_QUEUE.md is safe to follow.

So this file asks the omission question directly, against the bytes:

* it counts the actor bodies actually present in each pc, by the identity
  tag the entry serializer itself writes (``qwordtag(0x32, identity)`` at
  ``v141:1259``), not by asking the encoder what it thinks it wrote;
* it takes the arrival census as the BASELINE -- the set of actors the player
  can see standing in Port Royal before anything is attacked -- and requires
  the hit frame and both death frames to carry that SAME set;
* it runs on the flagless production path: ``make_state_class`` with no
  kwargs, no ``PF_DIAG_MULTI_OBJECT_CONFIG`` in the environment, no scenario.
  ``production_allowed`` is the whole point -- a proof that only holds under
  a diagnostic flag proves nothing about what a player gets.

NONCLAIMS.

1. This is a wire-layer proof.  It says the frames leaving the server name
   every actor arrival named.  It does NOT say a live client draws them --
   that is ``GT-084``/``RIDER-084-A`` ``OW1``-``OW3``, still attended, still
   unrun.  Nobody may read a green run of this file as "world wipe closed on
   screen".
2. It does not prove the BODIES are correct.  For a bystander it proves the
   identity is written exactly as often as arrival wrote it; for the 13
   roster members, whose bodies this lane reshapes on purpose, it proves
   only that the identity is still there at all.  Whether a given actor's
   body carries the right name/HP/hostility after the splice is
   ``test_mob_combat_dispatch.py``'s equality assertions, which this file
   deliberately does not duplicate.
3. 115 here is bg0001's committed census count, read off the running state,
   not a constant this file chooses.
"""
from __future__ import annotations

import contextlib
import io
import os
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
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_population_handoff  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SANCTIONED_TARGET = mob_death.SANCTIONED_FIRST_TARGET_IDENTITY  # 0x201F, P30
IDENTITY_TAG = 0x32  # v141:1259, make_remote_actor_entry's qwordtag


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class WorldWipeHeadlessProofTests(unittest.TestCase):
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
        self.roster = field_mobs.load_roster()
        # The flagless path is the claim of this file, so the diagnostic
        # allowlist is removed for the duration rather than merely left
        # unset: a developer running the suite with it exported in their
        # shell would otherwise silently prove the WRONG path green.
        patcher = mock.patch.dict(os.environ, {}, clear=False)
        patcher.start()
        os.environ.pop("PF_DIAG_MULTI_OBJECT_CONFIG", None)
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness (same shape as tests/test_mob_combat_dispatch.py) -----

    def _state(self):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        token = "wipe_%d" % id(self)
        state = state_type(token)
        self.assertEqual(
            state.diag_multi_objects, (),
            "the flagless boot this file exists to prove must carry no "
            "diagnostic objects",
        )
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

    def _performer(self, state):
        selected = state.foundation.selected
        return (
            ((selected.identity_hi & 0xFFFFFFFF) << 32)
            | (selected.identity_lo & 0xFFFFFFFF)
        )

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

    def _attack(self, state, target_identity):
        return state.dispatch(self.legacy.parse_outer(
            self._action_vital_pc(target_identity)
        ))

    def _set_balance(self, state, identity, current_hp):
        row = state.mob_combat_ledger.balance_of(identity)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            mob_combat.MobBalance(identity, row.max_hp, current_hp)
        )

    def _arrive(self, state):
        """login -> StartGame -> TargetPos, the real client's order.

        Returns the arrival census pc: the baseline set of actors the player
        is standing in front of before anything is hit.
        """
        anchor = (
            state.foundation.selected.position.x,
            state.foundation.selected.position.y,
            state.foundation.selected.position.z,
        )
        pc = (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + b"".join(self.legacy.f32tag(v) for v in (*anchor, 0.0))
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.u8tag(0x0B, 0)
        )
        actions = state.dispatch(self.legacy.parse_outer(pc))
        census = [
            action for action in actions
            if action[0].startswith("WORLD_CENSUS_INITIAL_")
        ]
        self.assertEqual(
            len(census), 1,
            "arrival must send exactly one initial census to be a baseline",
        )
        return anchor, census[0][1]

    # ----- the two readings this file is about --------------------------

    def _census_identities(self, state):
        """The membership arrival is supposed to have sent, built from the
        same table arrival builds from, at the anchor/count the running
        session actually recorded.  Used as the LIST of identities to look
        for; whether each one made it onto the wire is what the byte counts
        below decide.
        """
        return world_population.build_world_population(
            self.legacy, state.population_refresh_anchor,
            state.world_census_actor_count,
            scene_id=world_population.SCENE_ID,
        ).actor_identities

    def _declared_count(self, pc):
        """What the client is TOLD to read, off the collection header."""
        return world_population_handoff.wire_count_of(pc)

    def _bodies(self, pc, identities):
        """What the client is GIVEN: how often each identity is written.

        Counted by the identity tag the serializers themselves write
        (``qwordtag(0x32, identity)``), so an entry dropped by ANY
        composition step disappears here no matter which step dropped it.

        This is an occurrence count, not a body count, and deliberately so.
        An actor entry writes its identity in the entry header
        (``v141:1259``) AND again inside its MovementAttr (``v141:1229``),
        and the two are byte-identical shapes (``0B <u8> 32 <qword>`` both
        times), so no scan can tell them apart without parsing the whole
        collection.  Rather than parse, this compares each identity's count
        against the SAME count in the arrival frame: an actor that vanishes
        goes to zero, and one whose body was reshaped moves off its baseline.
        Both are reported, and only the first is the world wipe.
        """
        return {
            identity: pc.count(self.legacy.qwordtag(IDENTITY_TAG, identity))
            for identity in identities
        }

    def _assert_whole_world_present(self, pc, baseline, what):
        """``baseline`` is ``_bodies`` read off the arrival census frame."""
        self.assertEqual(
            self._declared_count(pc), len(baseline),
            f"{what}: the collection header tells the client a different "
            f"number of actors than arrival did",
        )
        counts = self._bodies(pc, baseline)
        missing = sorted(i for i, n in counts.items() if n == 0)
        self.assertEqual(
            missing, [],
            f"{what}: {len(missing)} of {len(baseline)} actors present at "
            f"arrival have no body in this frame -- replace-by-omission "
            f"(RE-092) erases them from the client's registry. "
            f"First few: {['0x%X' % i for i in missing[:5]]}",
        )
        # The 13 roster members are the ones this lane deliberately reshapes
        # (hostile body, wounded HP, corpse), so their occurrence counts are
        # allowed to move.  Every OTHER actor -- the townspeople a player
        # watches while fighting -- must come through a hit or a death
        # byte-count-identical to how arrival sent them.
        roster = {mob.actor_identity for mob in self.roster}
        drifted = sorted(
            i for i, n in counts.items()
            if i not in roster and n != baseline[i]
        )
        self.assertEqual(
            drifted, [],
            f"{what}: {['0x%X' % i for i in drifted[:5]]} are bystanders, "
            f"not roster members, yet their bodies changed shape between "
            f"arrival and this frame",
        )

    # ----- the proof ----------------------------------------------------

    def test_arrival_on_a_flagless_boot_is_a_115_body_baseline(self):
        state = self._state()
        _anchor, census_pc = self._arrive(state)
        self.assertEqual(state.world_census_actor_count, 115)
        identities = self._census_identities(state)
        self.assertEqual(len(set(identities)), 115)
        baseline = self._bodies(census_pc, identities)
        self.assertEqual(
            sorted(i for i, n in baseline.items() if n == 0), [],
            "arrival itself must carry every actor it counts",
        )
        self._assert_whole_world_present(census_pc, baseline, "arrival")

    def test_one_hit_leaves_every_arrival_actor_in_the_bar_frame(self):
        state = self._state()
        _anchor, census_pc = self._arrive(state)
        baseline = self._bodies(census_pc, self._census_identities(state))
        actions = self._attack(state, SANCTIONED_TARGET)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        bar_pc = next(
            pc for label, pc, _f, _d in actions if label == "MOB_COMBAT_BAR"
        )
        self._assert_whole_world_present(
            bar_pc, baseline, "the bar frame after one hit",
        )

    def test_one_death_leaves_every_arrival_actor_in_both_death_frames(self):
        state = self._state()
        _anchor, census_pc = self._arrive(state)
        baseline = self._bodies(census_pc, self._census_identities(state))
        self._set_balance(state, SANCTIONED_TARGET, 500)
        actions = self._attack(state, SANCTIONED_TARGET)
        labels = [label for label, _pc, _f, _d in actions]
        self.assertEqual(
            labels[:3],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"],
        )
        for wanted in ("MOB_DEATH_DYING", "MOB_DEATH_DEAD"):
            pc = next(
                pc for label, pc, _f, _d in actions if label == wanted
            )
            self._assert_whole_world_present(
                pc, baseline, f"{wanted} after one death",
            )

    def test_the_dead_mob_is_still_a_body_in_the_frame_not_a_deletion(self):
        """A corpse must be REPLACED, never removed.

        The lane's own fix would look green to the omission counters above if
        death removed the dead actor and nothing else -- 114 of 115 present
        reads as one missing actor, which is what the assertion says, but it
        is worth pinning the intent separately: GT-030 proved actor_type 2
        renders a corpse that stays on screen ~0.7s, so the dead mob's own
        identity has to keep a body in the frame that announces its death.
        """
        state = self._state()
        self._arrive(state)
        self._set_balance(state, SANCTIONED_TARGET, 500)
        actions = self._attack(state, SANCTIONED_TARGET)
        dead_pc = next(
            pc for label, pc, _f, _d in actions if label == "MOB_DEATH_DEAD"
        )
        self.assertGreaterEqual(
            dead_pc.count(
                self.legacy.qwordtag(IDENTITY_TAG, SANCTIONED_TARGET)
            ),
            1,
        )
        self.assertIn(
            mob_death.death_actor_entry(
                self.legacy,
                next(
                    m for m in self.roster
                    if m.actor_identity == SANCTIONED_TARGET
                ),
                death_timer=mob_death.DEAD_TIMER_SECONDS,
            ),
            dead_pc,
        )

    def test_the_console_token_reports_the_bodies_actually_sent(self):
        """The grep token an attended round is told to trust must not lie.

        ``MOB_COMBAT_BAR_CENSUS_RECOMPOSE actor_count=N`` is printed from
        session state before the frame is composed, so N is an INPUT.  This
        test is what makes it safe to grep: it pins that the number in the
        line equals the number of bodies that actually left, on this path,
        for both the hit and the death token.  If a future change makes the
        composed frame smaller than the announced count, this fails and the
        attended instruction in GAME_TEST_QUEUE.md stops being true -- which
        is the point, because the console line alone could not tell.
        """
        state = self._state()
        self._arrive(state)
        identities = self._census_identities(state)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = self._attack(state, SANCTIONED_TARGET)
        printed = buf.getvalue()
        token = (
            "MOB_COMBAT_BAR_CENSUS_RECOMPOSE actor_count=%d target=0x%X"
            % (state.world_census_actor_count, SANCTIONED_TARGET)
        )
        self.assertIn(token, printed)
        bar_pc = next(
            pc for label, pc, _f, _d in actions if label == "MOB_COMBAT_BAR"
        )
        announced = state.world_census_actor_count
        self.assertEqual(self._declared_count(bar_pc), announced)
        self.assertEqual(
            sum(1 for n in self._bodies(bar_pc, identities).values() if n),
            announced,
            "the console line announces one number and the frame carries "
            "another -- an attended tester grepping the token would record a "
            "PASS over a world wipe",
        )

    def test_a_kill_console_token_reports_the_bodies_actually_sent(self):
        state = self._state()
        self._arrive(state)
        identities = self._census_identities(state)
        self._set_balance(state, SANCTIONED_TARGET, 500)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = self._attack(state, SANCTIONED_TARGET)
        printed = buf.getvalue()
        announced = state.world_census_actor_count
        self.assertIn(
            "MOB_DEATH_FRAMES_CENSUS_RECOMPOSE actor_count=%d target=0x%X"
            % (announced, SANCTIONED_TARGET),
            printed,
        )
        for wanted in ("MOB_DEATH_DYING", "MOB_DEATH_DEAD"):
            pc = next(
                pc for label, pc, _f, _d in actions if label == wanted
            )
            self.assertEqual(self._declared_count(pc), announced)
            self.assertEqual(
                sum(1 for n in self._bodies(pc, identities).values() if n),
                announced,
                f"{wanted} carries fewer bodies than the token announces",
            )

    def test_no_compose_refusal_or_skip_fired_on_the_flagless_path(self):
        """The fail-closed fallbacks are one-entry frames -- the wipe itself.

        ``runtime.py`` degrades to ``death_step.dying_frame`` /
        ``bar_frames``' one-entry collection when the anchor/count are
        missing or the scene does not match.  That is the right thing to do
        rather than raising, but it means a green ``*_recompose_*`` test and
        a silently skipped recompose look the same from outside.  On the
        ordinary path proven here, neither may fire.
        """
        state = self._state()
        self._arrive(state)
        self._set_balance(state, SANCTIONED_TARGET, 500)
        self._attack(state, SANCTIONED_TARGET)
        offenders = [
            event for event in state.events
            if event.startswith("mob_combat_bar_census_compose_")
            or event.startswith("mob_death_frames_census_compose_")
        ]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
