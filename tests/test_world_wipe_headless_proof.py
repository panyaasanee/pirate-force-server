"""LANE-B: one hit and one death must not empty the world, ON THE WIRE.

WHAT THIS ADDS TO THE THREE FILES THAT ALREADY TOUCH CORE-REQUEST-008.

``tests/test_mob_combat_dispatch.py`` and ``tests/test_mob_combat_census_
wiring.py`` both assert the dispatcher's output EQUALS what
``mob_death.hostile_census_frames`` returns for the same inputs (the latter
also checks the frame, not just the pc, and pins the skipped/refused
events -- it is the stronger of the two and the one to read first).
``tests/test_world_census_wiring.py`` covers the arrival sequence itself.

What none of them can see is a shortfall that moves BOTH sides of their own
equality at once, because the expected value is recomputed from the same
function the dispatcher just called.  This file asks the question from the
other end: it takes the arrival census THIS SESSION ACTUALLY SENT as the
baseline, and requires every actor named there to still be named in the hit
frame and in both death frames.

MEASURED (round rbuta4, after pf-adversary; each mutation applied to a
clean tree, all three files run, tree restored).  Read "wiring" as
test_mob_combat_census_wiring.py and "dispatch" as
test_mob_combat_dispatch.py.

  (a) STALE FRAME.  runtime.py's two death actions keep the recomposed pc
      but carry death_step's old one-entry frame -- so every kill puts one
      body on the wire.
        dispatch 12 passed | wiring 2 failed | this file 2 failed
      (Before the ``_wire`` fix below, this file passed 7/7 here and the
      whole tree was 19/19 green over a live world wipe.  That is why the
      helper exists.)

  (b) BYSTANDERS ONLY.  The hit/death recompose drops 20 townspeople.
      Every roster body -- hostile, wounded, corpse -- is kept exactly as
      composed, and the target is untouched, so nothing about the fight
      looks wrong.  Arrival is not modified.
        dispatch 12 passed | wiring 7 passed | this file 4 failed
      Both prior-art files are fully green over the wipe.  This is the one
      that matters: it is the world wipe as a player meets it, the monster
      he is hitting behaving perfectly while the town thins out behind him.

  (c) COMPOSER SHRINK.  census_order drops 20 bystanders for EVERY caller,
      so arrival, the baseline identity list and the recompose all move
      together -- the circularity pf-adversary raised against the first
      draft, which passed 4 of 7 then.
        dispatch 12 passed | wiring 7 passed | this file 5 failed
      Caught now by the CENSUS_COUNT pin in ``_baseline``, not by the
      baseline comparison, which genuinely cannot see this on its own.

RE-092 proved the client is replace-by-omission
(``pf_bridge/notes_to_chief/20260826_2223_RE-092-RESULT-REPLACE-BY-
OMISSION-NETWORK-ACTOR-SCOPE.md``, sibling repo -- see NONCLAIM 6), so
"fewer bodies in the frame" IS the wipe, not a step toward it.

THE FIRST DRAFT OF THIS FILE WAS WRONG IN THE WAY THAT MATTERS MOST, AND
THE FIX IS THE POINT OF THE ``_wire`` HELPER BELOW.  It read ``pc``
everywhere.  ``v141:7755`` is ``c.sendall(out_frame)`` -- the pc is never
transmitted, and ``world_population_handoff`` line 358 says so in its own
words.  pf-adversary built a real regression from that: update the death
actions' ``pc`` to the recomposed census while leaving their ``frame``
bound to the old one-entry ``death_step``, and all 7 tests here plus all 12
in test_mob_combat_dispatch.py stayed green while every kill put a one-body
collection on the wire.  Every reading below is now taken from the frame,
and each action's frame is checked against its own pc so the two cannot
drift apart unnoticed.

THE CONSOLE TOKEN IS NOT EVIDENCE OF COUNT, AND THIS FILE DOES NOT MAKE IT
SO.  ``MOB_COMBAT_BAR_CENSUS_RECOMPOSE actor_count=108`` prints
``self.world_census_actor_count``, read from session state BEFORE the frame
is composed.  It is an INPUT.  Two tests here assert the token appears
(proving the recompose branch was TAKEN, which is all the token can
honestly show) and separately count the bodies on the wire.  An attended
tester may use the token to confirm the path ran; the count is the headless
layer's job, not the console's.

NONCLAIMS.

1. Wire layer only.  This says the frames leaving the server name every
   actor arrival named.  It does NOT say a live client draws them -- that is
   ``GT-084``/``RIDER-084-A`` ``OW1``-``OW3``, still attended, still unrun.
   A green run here is not "world wipe closed on screen".
2. It does not prove the BODIES are correct.  It counts how often each
   identity is WRITTEN, so it is blind to any reshape that preserves those
   writes: a frame that teleports all 102 bystanders to the origin passes
   every assertion here.  Body correctness is the equality assertions in the
   two dispatch files.
3. The census size is pinned against ``world_population.CENSUS_COUNT``, the
   committed constant, AND against the arrival frame's own collection
   header -- deliberately not against a literal, and deliberately not
   against the composer alone, because a composer that shrinks for every
   caller would otherwise move the baseline and the frames together.
4. The compose-fallback assertions live in the hit test and the death test
   separately, because a kill never enters the ``MOB_COMBAT_BAR`` branch at
   all; one combined test would leave half its assertion with no executed
   code behind it.
5. The identity counter is sound at HEAD but has a latent hazard named in
   ``_bodies``: ``make_npc_attr`` writes a byte-identical qword tag holding
   ``SCENE_SEQUENCE``, which is 0 today.
6. Two ``notes_to_chief`` citations in this docstring live in the sibling
   ``pf_bridge`` repository and are not reachable from a clone of this one.
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
IDENTITY_TAG = 0x32  # the qword tag every identity write uses


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


# AMENDMENT 2026-08-28 (LANE-A, RE-128 / CLINE identities).  The committed
# census size stopped being ``world_population.CENSUS_COUNT``.  115 is still
# the size of the frozen placement table; 108 is what a flagless boot
# ASSEMBLES, because seven of those placements have a Mob-Set number whose
# CLINE leader has no CONSTDATA MOBS row and therefore no identity that can be
# shipped without reviving the numbering GT-078 disproved.  Pinned as a literal
# here, exactly like the number it replaces, so a composer that shrank for
# every caller still cannot move this file's expectation with it.
SHIPPED_CENSUS_COUNT = 108


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
        # NOTE (pf-adversary D7): this env var is not the only way the
        # diagnostic can switch on -- diag_multi_object_config falls back to
        # a RELATIVE config/diag_multi_object.json, so flaglessness also
        # depends on CWD.  That is why the real guard is
        # _assert_flagless_after_arrival below, which reads session state
        # AFTER the census has run rather than a constructor default.
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

    def _assert_flagless_after_arrival(self, state):
        """Read the diagnostic state AFTER the census, not before it.

        pf-adversary D7: ``runtime.py`` sets ``diag_multi_objects = ()`` in
        ``__init__`` and only assigns the real value from ``activate()``
        during the arrival census.  A guard placed right after construction
        therefore reads a constructor constant and passes even when the
        diagnostic is fully on -- demonstrated: forcing ``activate`` to
        return five objects never tripped the old assertion once.
        """
        self.assertEqual(
            state.diag_multi_objects, (),
            "this file proves the FLAGLESS path; the diagnostic objects are "
            "active, so whatever is green here is green about another path",
        )

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
        """login -> StartGame -> TargetPos, the real client's order."""
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
            label for label, _pc, _f, _d in actions
            if label.startswith("WORLD_CENSUS_INITIAL_")
        ]
        self.assertEqual(
            len(census), 1,
            "arrival must send exactly one initial census to be a baseline",
        )
        self._assert_flagless_after_arrival(state)
        return anchor, self._wire(actions, census[0])

    # ----- the readings ---------------------------------------------------

    def _wire(self, actions, label):
        """The bytes ``c.sendall()`` actually transmits, for one action.

        ``v141:7755`` sends ``out_frame`` and nothing else.  The pc is
        checked against it rather than being trusted, so a frame left
        pointing at a stale collection while its pc was updated -- the exact
        regression pf-adversary built against this file's first draft --
        fails here instead of passing everywhere.
        """
        pc, frame = next(
            (pc, frame) for lbl, pc, frame, _d in actions if lbl == label
        )
        self.assertEqual(
            frame, self.legacy.frame_pc(pc),
            f"{label}: the frame that goes on the wire is not this pc's own "
            f"frame -- one of the two was updated and the other was not, so "
            f"every count taken from the pc is a count of bytes no client "
            f"will ever see",
        )
        return pc, frame

    def _declared_count(self, pc):
        """What the client is TOLD to read, off the collection header.

        Read from the pc, which ``_wire`` has already proven is the exact
        preimage of the transmitted frame.
        """
        return world_population_handoff.wire_count_of(pc)

    def _bodies(self, frame, identities):
        """How often each identity is written in the TRANSMITTED bytes.

        An occurrence count, not a body count, and deliberately so.  A census
        entry writes its identity THREE times -- ``make_npc_attr``
        (``v141:1186``), the entry header (``v141:1259``) and the
        MovementAttr (``v141:1229``) -- all as the same ``0B <u8> 32 <qword>``
        shape, so no scan can separate them without walking the whole
        collection.  Rather than walk it, this compares each identity's count
        against the SAME count in the arrival frame: an actor that vanishes
        goes to zero.

        LATENT HAZARD (pf-adversary D6): ``make_npc_attr`` also writes
        ``qwordtag(0x32, scene_seq)``, a byte-identical shape holding a scene
        sequence rather than an identity.  ``SCENE_SEQUENCE`` is 0 today and
        a structural walk of the arrival collection confirmed zero collisions
        for all 108 identities.  Should that constant ever take a value equal
        to a census identity, the inflation would appear in the baseline and
        the frames alike and this counter would not notice.
        """
        return {
            identity: frame.count(self.legacy.qwordtag(IDENTITY_TAG, identity))
            for identity in identities
        }

    def _baseline(self, state, census_pc, census_frame):
        """Everything later frames are measured against, plus its own pin.

        The identity LIST comes from the composer, but the two numbers that
        decide whether the census is whole do not: the arrival frame's own
        collection header, and ``SHIPPED_CENSUS_COUNT`` (was
        ``world_population.CENSUS_COUNT`` until RE-128 -- see that constant's
        comment).  A composer that shrank for every caller would move the list
        and the frames together (pf-adversary D2) -- these pins are what
        refuse it.
        """
        identities = world_population.build_world_population(
            self.legacy, state.population_refresh_anchor,
            state.world_census_actor_count,
            scene_id=world_population.SCENE_ID,
        ).actor_identities
        self.assertEqual(
            self._declared_count(census_pc), SHIPPED_CENSUS_COUNT,
            "the arrival census on the wire is not the committed census "
            "size; every later comparison in this file would be against a "
            "world that was already short before anything was hit",
        )
        self.assertEqual(len(set(identities)), SHIPPED_CENSUS_COUNT)
        counts = self._bodies(census_frame, identities)
        self.assertEqual(
            sorted(i for i, n in counts.items() if n == 0), [],
            "arrival itself must carry every actor it counts",
        )
        return counts

    def _assert_whole_world_present(self, pc, frame, baseline, what):
        self.assertEqual(
            self._declared_count(pc), SHIPPED_CENSUS_COUNT,
            f"{what}: the collection header tells the client a different "
            f"number of actors than the committed census size",
        )
        counts = self._bodies(frame, baseline)
        missing = sorted(i for i, n in counts.items() if n == 0)
        self.assertEqual(
            missing, [],
            f"{what}: {len(missing)} of {len(baseline)} actors present at "
            f"arrival have no body in this frame -- replace-by-omission "
            f"(RE-092) erases them from the client's registry. "
            f"First few: {['0x%X' % i for i in missing[:5]]}",
        )
        # The 13 roster members are the ones this lane deliberately reshapes
        # (hostile body, wounded HP, corpse), so their identity-write counts
        # are allowed to move.  Every OTHER actor must be written exactly as
        # often as arrival wrote it.  This catches an actor dropped or
        # duplicated; per NONCLAIM 2 it does NOT catch a body whose CONTENTS
        # changed while its identity writes stayed put.
        roster = {mob.actor_identity for mob in self.roster}
        drifted = sorted(
            i for i, n in counts.items()
            if i not in roster and n != baseline[i]
        )
        self.assertEqual(
            drifted, [],
            f"{what}: {['0x%X' % i for i in drifted[:5]]} are bystanders, "
            f"not roster members, yet their identity is written a different "
            f"number of times than arrival wrote it",
        )

    # ----- the proof ----------------------------------------------------

    def test_arrival_on_a_flagless_boot_is_a_whole_census_baseline(self):
        state = self._state()
        _anchor, (census_pc, census_frame) = self._arrive(state)
        self.assertEqual(
            state.world_census_actor_count, SHIPPED_CENSUS_COUNT,
        )
        baseline = self._baseline(state, census_pc, census_frame)
        self._assert_whole_world_present(
            census_pc, census_frame, baseline, "arrival",
        )

    def test_one_hit_leaves_every_arrival_actor_on_the_wire(self):
        state = self._state()
        _anchor, (census_pc, census_frame) = self._arrive(state)
        baseline = self._baseline(state, census_pc, census_frame)
        actions = self._attack(state, SANCTIONED_TARGET)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        bar_pc, bar_frame = self._wire(actions, "MOB_COMBAT_BAR")
        self._assert_whole_world_present(
            bar_pc, bar_frame, baseline, "the bar frame after one hit",
        )
        self.assertFalse(
            [e for e in state.events
             if e.startswith("mob_combat_bar_census_compose_")],
            "a fallback fired: the frame on the wire is the one-entry frame, "
            "which is the world wipe itself",
        )

    def test_one_death_leaves_every_arrival_actor_on_the_wire(self):
        state = self._state()
        _anchor, (census_pc, census_frame) = self._arrive(state)
        baseline = self._baseline(state, census_pc, census_frame)
        self._set_balance(state, SANCTIONED_TARGET, 500)
        actions = self._attack(state, SANCTIONED_TARGET)
        labels = [label for label, _pc, _f, _d in actions]
        self.assertEqual(
            labels[:3],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"],
        )
        for wanted in ("MOB_DEATH_DYING", "MOB_DEATH_DEAD"):
            pc, frame = self._wire(actions, wanted)
            self._assert_whole_world_present(
                pc, frame, baseline, f"{wanted} after one death",
            )
        self.assertFalse(
            [e for e in state.events
             if e.startswith("mob_death_frames_census_compose_")],
            "a fallback fired: the frames on the wire are the one-entry "
            "frames, which is the world wipe itself",
        )

    def test_the_hit_token_marks_a_recompose_that_really_ran(self):
        """The token proves the BRANCH was taken.  The count proves the rest.

        Two separate claims, kept separate: the token cannot be evidence of a
        count, because it is printed from session state before the frame
        exists.
        """
        state = self._state()
        _anchor, (census_pc, census_frame) = self._arrive(state)
        baseline = self._baseline(state, census_pc, census_frame)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = self._attack(state, SANCTIONED_TARGET)
        self.assertIn(
            "MOB_COMBAT_BAR_CENSUS_RECOMPOSE actor_count=%d target=0x%X"
            % (state.world_census_actor_count, SANCTIONED_TARGET),
            buf.getvalue(),
        )
        _bar_pc, bar_frame = self._wire(actions, "MOB_COMBAT_BAR")
        self.assertEqual(
            sum(1 for n in self._bodies(bar_frame, baseline).values() if n),
            state.world_census_actor_count,
            "the console line announces one number and the wire carries "
            "another",
        )

    def test_the_death_token_marks_a_recompose_that_really_ran(self):
        state = self._state()
        _anchor, (census_pc, census_frame) = self._arrive(state)
        baseline = self._baseline(state, census_pc, census_frame)
        self._set_balance(state, SANCTIONED_TARGET, 500)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = self._attack(state, SANCTIONED_TARGET)
        announced = state.world_census_actor_count
        self.assertIn(
            "MOB_DEATH_FRAMES_CENSUS_RECOMPOSE actor_count=%d target=0x%X"
            % (announced, SANCTIONED_TARGET),
            buf.getvalue(),
        )
        for wanted in ("MOB_DEATH_DYING", "MOB_DEATH_DEAD"):
            _pc, frame = self._wire(actions, wanted)
            self.assertEqual(
                sum(1 for n in self._bodies(frame, baseline).values() if n),
                announced,
                f"{wanted} carries fewer bodies than the token announces",
            )


if __name__ == "__main__":
    unittest.main()
