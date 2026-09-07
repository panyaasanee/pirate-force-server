"""LANE-B: a death refusal must leave the player looking at a monster that
will not die, NEVER at a world that went silent.

WHY THIS FILE EXISTS.  COO-DECISION 2026-09-07T15:41+07:00 (pf_bridge
``notes_to_chief/20260907_1541_COO-DECISION-b1520-hold-the-flip-measure-
the-raise-LANE-B.md``, item 5) closes a "[NOT MEASURED]" this lane wrote
into its own round file the round before: ``mob_death`` refuses a kill on a
monster no registered ruling covers by RAISING, and

    ``current/pf_login_game_server_v141.py`` wraps ``state.dispatch`` in NO
    except handler

(the sentence is ``src/pirateforce_foundation/gm/login_scene_consume.py``'s,
not this file's).  An exception that leaves ``dispatch`` therefore leaves the
game listener, and the session stops answering: the player's world goes
quiet, which reads on a screen exactly like "the server lost my character"
and nothing like "this monster cannot be killed yet".  The refusal itself is
a deliberate, named, owner-facing decision; carrying it out of the listener
would not be.

WHAT IS MEASURED HERE, end to end on the real dispatcher, in a real scene,
on a flagless boot with no scenario of any kind:

  * ``test_an_uncovered_kill_does_not_leave_dispatch`` -- a killing blow on a
    Bg0002 roster row NO ruling covers returns from ``state.dispatch()``
    normally.  The burst it composes is the announce and nothing after it:
    no ``MOB_DEATH_DYING``, no ``MOB_DEATH_DEAD``, no ``MOB_LOOT_DROP``.
  * ``test_the_refusal_is_named_on_the_session`` -- the session records
    ``mob_death_refused_target_outside_the_sanctioned_scope_no_death_frames``
    so an operator reading the event list is told WHICH refusal happened,
    not merely that frames are missing.
  * ``test_the_second_blow_also_does_not_leave_dispatch`` -- a player does not
    stop at one swing.  The second blow returns too, and composes no combat
    frame at all (``mob_combat``'s own no-room path for a 0 HP body).
  * ``test_the_control_kill_still_dies`` -- the SAME harness, with the
    registry untouched, composes the full four-action burst ending in a real
    ``MOB_LOOT_DROP``.  Without this the three tests above would pass just as
    well against a dispatcher that had stopped killing anything at all.

HOW THE UNCOVERED MONSTER IS MADE, and why it is not a stub of the thing
under test.  Nothing in the combat path is replaced: the roster, the ledger,
the census, the AI register, ``mob_combat.strike``, ``mob_death`` and the
dispatcher are all the shipped ones.  What is removed, for the duration of
one test, is the PERMIT -- the entries of ``mob_death.WIDENING_RULINGS``
that cover a Bg0002 row -- which is precisely the condition the decision
asks about: "a monster nobody authorised killing".  ``ruling_for`` is
asserted to raise before the blow is thrown, so a test that stopped
injecting anything would fail loudly instead of passing on a kill that was
never refused.

THE MUTANT THIS FILE IS FOR.  Delete the ``except mob_death.
MobDeathContractError`` around the roster kill site in ``runtime.py`` (the
``else`` branch that calls ``mob_death.kill``) and
``test_an_uncovered_kill_does_not_leave_dispatch`` fails with the refusal
coming out of ``dispatch``, which is the whole point: today's guard is not
pinned by anything else in the repository.

WHAT THIS FILE DOES NOT MEASURE, and no line of it may be read as:

  * NOBODY HAS SEEN THIS ON A SCREEN.  That a client draws a monster stuck
    at 0 HP as "alive and unkillable" rather than as something stranger is
    unmeasured; this file measures what the server composes.
  * ONE DOOR, NOT ALL OF THEM.  This drives the roster kill site.  The
    diagnostic branch (``diag_multi_object_wiring.death_dispatch``),
    ``mob_respawn``, ``mob_death_persistence`` and ``scene_door_walk`` each
    reach a kill by their own path and each carry their own handler; none of
    them is driven here.
  * THE SIBLING RAISE IS NOT COVERED AND IS NOT SAFE.  In the same block,
    a commit refusal whose reason is not ``REFUSE_REGISTER_STALE`` is
    re-raised bare.  Round jkrcej MEASURED that one to leave ``dispatch``
    (forced with a stubbed ``commit_death_and_prepare_hook``, reason
    ``already_dead``).  Whether a live path can produce such a reason is
    NOT established in either direction -- ``runtime.py``'s own comment says
    "unreachable today", and this lane has not confirmed it.  ``runtime.py``
    belongs to chief, so that half is a CORE-REQUEST
    (pf_bridge ``notes_to_chief/20260907_*_LANE-B-CORE-REQUEST-dispatch-
    edge-swallows-only-half-the-death-refusals.md``), not an edit here, and
    no test in this file pretends to cover it.
"""
from __future__ import annotations

import contextlib
import io
import random
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs                      # noqa: E402
from pirateforce_foundation import mob_combat                      # noqa: E402
from pirateforce_foundation import mob_combat_membership           # noqa: E402
from pirateforce_foundation import mob_death                       # noqa: E402
from pirateforce_foundation import world_scene_travel              # noqa: E402
from pirateforce_foundation.gm.chat_command_action import (        # noqa: E402
    WARP_ACTION_LABEL,
)
from pirateforce_foundation.gm.warp_executor import WarpTarget     # noqa: E402
from pirateforce_foundation.gm.warp_target_record import (         # noqa: E402
    current_character_id, record_warp_target,
)
from pirateforce_foundation.legacy_bridge import (                 # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle    # noqa: E402
from pirateforce_foundation.model import Position                  # noqa: E402
from pirateforce_foundation.runtime import make_state_class        # noqa: E402
from pirateforce_foundation.store import SQLiteStore               # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

#: The scene whose roster can be killed AND can drop, so the control kill
#: below is a full burst rather than a three-action one.  Same scene, same
#: seed and same reasons as tests/test_mob_combat_dispatch_bg0002_kill.py.
DESTINATION_SCENE_ID = 2
DESTINATION_FOLDER = "Bg0002"
DROP_SEED = 1

#: The event runtime.py appends when the roster kill site catches a refusal.
REFUSED_EVENT = (
    "mob_death_refused_target_outside_the_sanctioned_scope_no_death_frames"
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _rulings_without_bg0002_cover():
    """``WIDENING_RULINGS`` minus every letter that covers a Bg0002 row.

    Derived from the shipped roster rather than hand-listed, so a letter
    added tomorrow that covers this scene is dropped here too and the
    injection does not quietly stop injecting.
    """
    roster = field_mobs.load_roster(DESTINATION_FOLDER)
    keep = {}
    for name, templates in mob_death.WIDENING_RULINGS.items():
        scene = mob_death.WIDENING_RULING_SCENES.get(name)
        covers = any(
            mob.template_id in templates
            and (scene is None or mob.scene == scene)
            for mob in roster
        )
        if not covers:
            keep[name] = templates
    return keep


class UncoveredKillDispatchTests(unittest.TestCase):

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
        self.roster = field_mobs.load_roster(DESTINATION_FOLDER)
        self.target = self.roster[0].actor_identity
        # Injected for the same reason as the sibling kill harness: two
        # blows in one test are a cadence apart and a test must not sleep.
        self.clock_ms = 0

    # ----- harness -------------------------------------------------------

    def _clock(self):
        return self.clock_ms / 1000.0

    def _dispatch(self, state, pc):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            return state.dispatch(self.legacy.parse_outer(pc))

    def _state(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            monotonic_clock=self._clock,
        )
        state = state_type(token)
        self._dispatch(state, self.legacy._synthetic_client_login_pc(token))
        self._dispatch(state, self.legacy._V25_REAL_CREATE_PC)
        character = self.store.list_characters(state.foundation.account_id)[-1]
        self._dispatch(
            state, self.legacy._synthetic_start_game_pc(character.selector),
        )
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        state.mob_loot_rng = random.Random(DROP_SEED)
        return state

    def _warp(self, state, scene_id):
        spawn = world_scene_travel.spawn_position(
            world_scene_travel.destination(scene_id)
        )
        target = WarpTarget(scene_id, spawn[0], spawn[1], spawn[2])
        self.assertTrue(
            record_warp_target(state, target, current_character_id(state))
        )
        real = state._dispatch_with_lanes

        def _one_warp_action(parsed):
            state._dispatch_with_lanes = real
            return [(WARP_ACTION_LABEL, b"", b"", 0.0)]

        state._dispatch_with_lanes = _one_warp_action
        self._dispatch(
            state, self.legacy._synthetic_client_login_pc(state.token),
        )
        self.assertEqual(
            state.foundation.selected.position.scene_id, scene_id,
            "the warp did not move the session's scene",
        )
        self.clock_ms += 1000

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

    def _armed_session(self):
        """A booted session standing in Bg0002 with ``self.target`` on 1 HP."""
        state = self._state("uncovered-kill")
        self._warp(state, DESTINATION_SCENE_ID)
        state._sync_combat_scene_state()
        row = state.mob_combat_ledger.balance_of(self.target)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            mob_combat.MobBalance(self.target, row.max_hp, 1)
        )
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                state.foundation.selected.position.scene_id,
                (self.target,),
                state.mob_combat_announced_membership_generation,
            )
        )
        return state

    @contextlib.contextmanager
    def _no_letter_covers_the_target(self):
        keep = _rulings_without_bg0002_cover()
        with unittest.mock.patch.object(
                mob_death, "WIDENING_RULINGS", keep):
            with self.assertRaises(mob_death.MobDeathContractError) as caught:
                mob_death.ruling_for(self.roster[0])
            self.assertEqual(
                caught.exception.reason,
                mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE,
                "the injection stopped injecting: this target is still "
                "covered, so the tests below would measure an ordinary kill",
            )
            yield

    @staticmethod
    def _labels(actions):
        return [label for label, *_rest in actions]

    # ----- the measurement -----------------------------------------------

    def test_an_uncovered_kill_does_not_leave_dispatch(self):
        """[MEASURED] the refusal is answered inside dispatch, not thrown
        through it.  A raise here would reach v141's game_listener, which
        has no handler, and the player's session would go quiet."""
        state = self._armed_session()
        with self._no_letter_covers_the_target():
            try:
                actions = self._dispatch(
                    state, self._action_vital_pc(self.target),
                )
            except mob_death.MobDeathContractError as error:
                self.fail(
                    "the refusal %r left state.dispatch(); v141 wraps that "
                    "call in no except handler, so this is the listener "
                    "thread dying and the player's world going silent"
                    % error.reason
                )
        labels = self._labels(actions)
        self.assertIn(
            "MOB_COMBAT_ANNOUNCE", labels,
            "the blow itself must still land -- the player has to see the "
            "monster get hit, or 'unkillable' is indistinguishable from "
            "'not targetable'",
        )
        for absent in ("MOB_DEATH_DYING", "MOB_DEATH_DEAD", "MOB_LOOT_DROP"):
            self.assertNotIn(
                absent, labels,
                "%s was composed for a monster no ruling authorises killing"
                % absent,
            )

    def test_the_refusal_is_named_on_the_session(self):
        """A missing frame is not a diagnosis.  The session says which
        refusal happened, by name, on the event list."""
        state = self._armed_session()
        with self._no_letter_covers_the_target():
            self._dispatch(state, self._action_vital_pc(self.target))
        self.assertIn(REFUSED_EVENT, state.events)

    def test_the_second_blow_also_does_not_leave_dispatch(self):
        """A player swings again.  The second blow returns as well, and
        composes no combat frame at all -- mob_combat's no-room path for a
        body already at 0 HP."""
        state = self._armed_session()
        with self._no_letter_covers_the_target():
            self._dispatch(state, self._action_vital_pc(self.target))
            self.clock_ms += 1000
            try:
                again = self._dispatch(
                    state, self._action_vital_pc(self.target),
                )
            except mob_death.MobDeathContractError as error:
                self.fail(
                    "the SECOND blow's refusal %r left state.dispatch()"
                    % error.reason
                )
        self.assertNotIn("MOB_COMBAT_ANNOUNCE", self._labels(again))
        self.assertNotIn("MOB_DEATH_DEAD", self._labels(again))

    def test_the_body_is_left_at_zero_hp_and_this_is_what_the_player_sees(
            self):
        """[MEASURED] the ledger keeps the row at 0 HP with no corpse behind
        it.  Recorded because it is the honest description of the state this
        refusal ships, and it is NOT a good state -- it is only a better one
        than a dead session.  Nobody has seen it on a screen."""
        state = self._armed_session()
        with self._no_letter_covers_the_target():
            self._dispatch(state, self._action_vital_pc(self.target))
        balance = state.mob_combat_ledger.balance_of(self.target)
        self.assertEqual(balance.current_hp, 0)
        self.assertFalse(
            state.mob_death_register.is_dead(self.target),
            "a refused kill must not leave a death record behind it",
        )

    def test_the_control_kill_still_dies(self):
        """The same harness with the registry untouched.  Without this, every
        test above would pass against a dispatcher that had stopped killing
        anything at all, for any reason."""
        state = self._armed_session()
        labels = self._labels(
            self._dispatch(state, self._action_vital_pc(self.target))
        )
        for expected in (
                "MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"):
            self.assertIn(expected, labels)
        self.assertNotIn(REFUSED_EVENT, state.events)


if __name__ == "__main__":
    unittest.main()
