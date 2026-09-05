"""ATTACK-POSE-ONE-FIELD-AB-001 on the production ``_dispatch_mob_combat``
path (COO-DECISION 20260905_0248), NOT the SCENE-007 scenario gate
``tests/test_pose_trial.py`` and ``tests/test_action_ack.py`` already cover.

``GT-247``'s own R314 result measured the scenario route dead twice over: the
``vital_count == 1`` gate never admits a real client's ActionVital (which
always carries TargetPos alongside it), and separately the head of ``main``
cannot even boot ``--scene-load-scenario`` right now (COO-DECISION
20260905_0250).  This file drives the ORDINARY, unflagged dispatcher --
``make_state_class`` with no scenario of any kind, the same harness
``tests/test_mob_combat_dispatch.py`` uses for MOB-COMBAT-001/MOB-DEATH-001 --
and proves:

  * ~~an unset or malformed ``PF_POSE_TRIAL`` sends the exact same two
    frames (``MOB_COMBAT_ANNOUNCE``, ``MOB_COMBAT_BAR``) an unarmed boot
    already sends today, with nothing extra~~ -- STRUCK for the UNSET half
    only, and struck by design rather than by regression: since chief wired
    ``class_id=selected.class_id`` at the call site (``LANE-B CORRECTION
    20260905_1600``) an unarmed hit composes the swing the performer's
    CLASS implies.  A MALFORMED value still sends nothing extra, and a
    character whose ``class_id`` column is NULL still sends nothing extra;
    both are pinned separately below;
  * an unarmed hit by a class whose BEHAVIOR id is screen-confirmed echoes
    ONE extra ActionVital frame carrying that id, with no flag, no
    scenario, and no environment variable anywhere in the path;
  * an armed comma-separated list echoes ONE extra ActionVital frame per
    accepted hit, cycling one selector off the list per hit and wrapping
    around, with performer/target carried through from the real request and
    ``+0x30`` set to the armed value;
  * the console prints ``POSE_TRIAL sent=<id> hit=<n>`` for that hit and
    nothing when unarmed.

NOT proven here: whether a real client plays an attack animation for any of
the six ids (``GT-247``, on a screen).  This file proves the wire only.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_combat_membership  # noqa: E402
from pirateforce_foundation.action_ack import build_action_vital_echo  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
CONTROL_TARGET = 0x2000 + field_mobs.CONTROL_PLACEMENT_INDEX + 1
POSE_TRIAL_ENV = "PF_POSE_TRIAL"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class PoseWiringHarness(unittest.TestCase):
    """setUp/teardown and the request helpers, shared by the two suites
    below.  Carries no ``test_`` method of its own on purpose: it is a
    harness, and a harness that runs as a suite would run every test in
    both subclasses twice."""

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
        self.control_mob = next(
            m for m in self.roster if m.actor_identity == CONTROL_TARGET
        )
        # Injected clock: MOB_COMBAT_CADENCE_WIRING gates two hits from the
        # same performer 600 ms apart (ATTACK_CADENCE_MS_PROVISIONAL) and a
        # cycling test needs several hits without sleeping.  Production
        # passes the real monotonic clock through this same argument
        # (test_mob_combat_dispatch_bg0002_kill.py's own harness note).
        self.clock_ms = 0
        # A saved copy of PF_POSE_TRIAL, restored in tearDown: this suite
        # arms and clears the real process environment (not a mapping
        # override) because the production call site
        # (runtime.py's _dispatch_mob_combat) reads os.environ directly,
        # exactly like an attended boot's `set PF_POSE_TRIAL=...`.
        self._saved_env = os.environ.get(POSE_TRIAL_ENV)

    def tearDown(self):
        self.tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop(POSE_TRIAL_ENV, None)
        else:
            os.environ[POSE_TRIAL_ENV] = self._saved_env

    # ----- harness (mirrors tests/test_mob_combat_dispatch.py) -----------

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

    def _action_vital_pc(
        self, target_identity, *, action_code=0,
        heading=0.0, x=0.0, y=0.0, z=0.0,
    ):
        legacy = self.legacy
        body = (
            legacy.qwordtag(0x32, 0)
            + legacy.qwordtag(0x32, target_identity)
            + legacy.qwordtag(0x32, 0)
            + legacy.u32tag(0x14, action_code)
            + legacy.u32tag(0x19, 0)
            + legacy.f32tag(heading) + legacy.f32tag(x)
            + legacy.f32tag(y) + legacy.f32tag(z)
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

    def _attack(self, state, target_identity, **kwargs):
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                state.foundation.selected.position.scene_id,
                (target_identity,),
                state.mob_combat_announced_membership_generation,
            )
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            actions = state.dispatch(self.legacy.parse_outer(
                self._action_vital_pc(target_identity, **kwargs)
            ))
        return actions, out.getvalue()

    def _set_balance(self, state, identity, current_hp):
        row = state.mob_combat_ledger.balance_of(identity)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            mob_combat.MobBalance(identity, row.max_hp, current_hp)
        )

    def _hit(self, state, target_identity=CONTROL_TARGET):
        """One accepted, survived hit: attack, then heal back to full so
        the next call is not a killing blow, and advance the injected
        clock past the cadence window."""
        actions, out = self._attack(state, target_identity)
        self._set_balance(state, target_identity, self.control_mob.max_hp)
        self.clock_ms += mob_combat.ATTACK_CADENCE_MS_PROVISIONAL + 1
        return actions, out


class MobCombatPoseTrialWiringTests(PoseWiringHarness):
    # ----- unarmed ~~byte-for-byte what main already sends~~ --------------
    #
    # THE HEADING IS STRUCK, and so is the claim it made.  It was true for
    # exactly as long as `runtime.py` called the composer without a
    # `class_id`: with nothing to resolve, an unarmed hit took the
    # `class_id is None` refusal and shipped nothing extra.  Under `LANE-B
    # CORRECTION 20260905_1600` chief passes `selected.class_id`, and the
    # harness's own `_V25_REAL_CREATE_PC` character carries `class_id=1`
    # from creation (`CHARACTER_CLASS_ID cid=1 written class_id=1` on this
    # suite's own stderr), so an unarmed hit now composes class 1's swing.
    # That is the entire point of the wiring, so the pin below is rewritten
    # to the corrected value rather than deleted or loosened to an
    # either-way check.  What survives unchanged is the narrower and still
    # load-bearing fact: an unarmed boot prints no `POSE_TRIAL` line -- the
    # trial instrument stays silent unless somebody armed it.

    def test_unset_sends_the_class_pose_not_a_trial_frame(self):
        os.environ.pop(POSE_TRIAL_ENV, None)
        state = self._state("mc_pose_unset")
        self.assertEqual(state.foundation.selected.class_id, 1)
        actions, out = self._hit(state)
        self.assertEqual(
            [label for label, *_ in actions],
            ["MOB_COMBAT_POSE_TRIAL", "MOB_COMBAT_ANNOUNCE",
             "MOB_COMBAT_BAR"],
        )
        self.assertNotIn("POSE_TRIAL", out)
        self.assertIn("POSE_PRODUCTION class=1", out)
        self.assertIn("behavior=280", out)

    def test_unset_with_a_null_class_column_sends_nothing_extra(self):
        # The half of the struck claim that IS still true, kept as its own
        # pin: a character whose column is NULL still gets main's frames.
        os.environ.pop(POSE_TRIAL_ENV, None)
        state = self._state("mc_pose_unset_null")
        state.foundation.selected = replace(
            state.foundation.selected, class_id=None,
        )
        actions, out = self._hit(state)
        self.assertEqual(
            [label for label, *_ in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        self.assertNotIn("POSE_TRIAL", out)
        self.assertIn("POSE_NO_EQUIP_PROVENANCE", out)

    def test_malformed_sends_no_frame_but_says_so(self):
        os.environ[POSE_TRIAL_ENV] = "not-a-number"
        state = self._state("mc_pose_malformed")
        actions, out = self._hit(state)
        self.assertEqual(
            [label for label, *_ in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        self.assertIn("POSE_TRIAL_REFUSED malformed hit=1", out)

    def test_a_bare_empty_or_whitespace_value_is_unset_not_armed(self):
        # "Unset, not armed" is what this test measures, and it still does:
        # a blank value must reach the SAME place a missing variable does.
        # Since the class wiring landed that place composes the class's
        # swing, so the frame list is the unset list -- compared against
        # `test_unset_sends_the_class_pose_not_a_trial_frame` above, not
        # against a hardcoded "nothing extra" this file no longer means.
        for raw in ("", "   "):
            with self.subTest(raw=repr(raw)):
                os.environ[POSE_TRIAL_ENV] = raw
                state = self._state("mc_pose_blank_%d" % len(raw))
                actions, out = self._hit(state)
                self.assertEqual(
                    [label for label, *_ in actions],
                    ["MOB_COMBAT_POSE_TRIAL", "MOB_COMBAT_ANNOUNCE",
                     "MOB_COMBAT_BAR"],
                )
                self.assertNotIn("POSE_TRIAL", out)
                self.assertIn("POSE_PRODUCTION class=1", out)

    # ----- armed: one extra frame per hit, cycling the list ---------------

    def test_an_armed_list_echoes_one_frame_per_hit_and_wraps(self):
        os.environ[POSE_TRIAL_ENV] = "280,284,288"
        state = self._state("mc_pose_armed")
        expected_ids = [280, 284, 288, 280, 284]
        for hit_number, want_id in enumerate(expected_ids, start=1):
            actions, out = self._hit(state)
            labels = [label for label, *_ in actions]
            self.assertEqual(
                labels, ["MOB_COMBAT_POSE_TRIAL", "MOB_COMBAT_ANNOUNCE",
                         "MOB_COMBAT_BAR"],
            )
            self.assertIn(
                "POSE_TRIAL sent=%d hit=%d" % (want_id, hit_number), out,
            )
            _label, pc, frame, delay = actions[0]
            self.assertEqual(delay, 0.0)
            self.assertEqual(frame, self.legacy.frame_pc(pc))
            # Re-derive the same request fields _dispatch_mob_combat itself
            # parsed (identical call, same target, defaults for everything
            # else) and check the composed frame against the shared encoder
            # directly -- the unit-level test for that encoder already lives
            # in tests/test_action_ack.py; this only proves the WIRING
            # carries the real performer/target through to it.
            fields = self.legacy.parse_action_vital(self.legacy.parse_outer(
                self._action_vital_pc(CONTROL_TARGET)
            ))
            performer = (
                ((state.foundation.selected.identity_hi & 0xFFFFFFFF) << 32)
                | (state.foundation.selected.identity_lo & 0xFFFFFFFF)
            )
            expected_pc, expected_frame = build_action_vital_echo(
                self.legacy, fields, performer, want_id,
            )
            self.assertEqual((pc, frame), (expected_pc, expected_frame))
        self.assertEqual(state.mob_combat_hit_count, len(expected_ids))

    def test_a_single_element_list_sends_the_same_id_every_hit(self):
        os.environ[POSE_TRIAL_ENV] = "60029"
        state = self._state("mc_pose_single")
        for hit_number in (1, 2, 3):
            actions, out = self._hit(state)
            self.assertEqual(actions[0][0], "MOB_COMBAT_POSE_TRIAL")
            self.assertIn(
                "POSE_TRIAL sent=60029 hit=%d" % hit_number, out,
            )


class ProductionClassPoseWiringTests(PoseWiringHarness):
    """The performer's class reaches the pose composer through the REAL
    dispatcher (`LANE-B CORRECTION 20260905_1600`, correcting CORE-REQUEST
    `20260905_1352`).

    Before the keyword existed, `runtime.py` called
    `make_production_hit_pose_echo` without one, so every ordinary hit took
    the `class_id is None` refusal and the client got the inherited v141
    echo of the request's own `+0x30` -- which `GT-247` R315 measured on the
    screen as "the monster's blood drops and the character stands still".

    These tests drive the same unflagged `_dispatch_mob_combat` the parent
    class does, with `PF_POSE_TRIAL` unset, and assert the frame the class
    implies -- not the frame a flag was armed with.

    NOT proven here: that a client plays the animation.  That is `GT-247`'s
    already-passed R315 measurement for these five ids, on a screen; this
    file proves the wire carries the id the class implies.
    """

    def _state_with_class(self, token, class_id):
        state = self._state(token)
        selected = state.foundation.selected
        state.foundation.selected = replace(selected, class_id=class_id)
        return state

    def test_each_screen_confirmed_class_swings_its_own_weapon(self):
        os.environ.pop(POSE_TRIAL_ENV, None)
        for class_id, behavior_id in (
            (1, 280), (2, 284), (4, 282), (16, 288),
        ):
            with self.subTest(class_id=class_id):
                state = self._state_with_class(
                    "mc_pose_cls_%d" % class_id, class_id,
                )
                actions, out = self._hit(state)
                self.assertEqual(actions[0][0], "MOB_COMBAT_POSE_TRIAL")
                self.assertIn(
                    "POSE_PRODUCTION class=%d" % class_id, out,
                )
                self.assertIn("behavior=%d" % behavior_id, out)
                # The frame is the one build_action_vital_echo composes for
                # that behavior id, not merely "some extra frame".
                _, pc, frame, _ = actions[0]
                fields = self.legacy.parse_action_vital(
                    self.legacy.parse_outer(
                        self._action_vital_pc(CONTROL_TARGET)
                    )
                )
                performer = (
                    ((state.foundation.selected.identity_hi & 0xFFFFFFFF) << 32)
                    | (state.foundation.selected.identity_lo & 0xFFFFFFFF)
                )
                expected_pc, expected_frame = build_action_vital_echo(
                    self.legacy, fields, performer, behavior_id,
                )
                self.assertEqual((pc, frame), (expected_pc, expected_frame))

    def test_a_null_class_column_still_sends_nothing_extra(self):
        os.environ.pop(POSE_TRIAL_ENV, None)
        state = self._state_with_class("mc_pose_cls_null", None)
        actions, out = self._hit(state)
        self.assertNotIn(
            "MOB_COMBAT_POSE_TRIAL", [a[0] for a in actions],
        )
        self.assertIn("POSE_NO_EQUIP_PROVENANCE", out)

    def test_a_class_whose_behavior_is_not_screen_confirmed_is_refused(self):
        # class 32 (Sorcerer) resolves BEHAVIOR 286, measured on the same
        # R315 screen to play NOTHING.  It must be refused here, not sent.
        os.environ.pop(POSE_TRIAL_ENV, None)
        state = self._state_with_class("mc_pose_cls_32", 32)
        actions, out = self._hit(state)
        self.assertNotIn(
            "MOB_COMBAT_POSE_TRIAL", [a[0] for a in actions],
        )
        self.assertIn("POSE_REFUSED", out)
        self.assertIn("behavior=286", out)

    def test_an_armed_trial_list_still_wins_over_the_class(self):
        # COO-DECISION 20260905_1045 item 3: an owner running a sweep gets
        # the id she armed.  Wiring the class must not change that.
        os.environ[POSE_TRIAL_ENV] = "60029"
        state = self._state_with_class("mc_pose_cls_armed", 1)
        actions, out = self._hit(state)
        self.assertEqual(actions[0][0], "MOB_COMBAT_POSE_TRIAL")
        self.assertIn("POSE_TRIAL sent=60029 hit=1", out)
        self.assertNotIn("POSE_PRODUCTION", out)

    def test_a_selected_without_the_attribute_costs_the_hit_nothing(self):
        # foundation.selected is a stub in several other lanes' dispatch
        # tests.  An AttributeError raised at the call site would leave
        # _dispatch_mob_combat entirely and cost the hit its ANNOUNCE and
        # BAR frames, not just the pose.
        os.environ.pop(POSE_TRIAL_ENV, None)
        state = self._state("mc_pose_cls_stub")

        class _NoClassId:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                if name == "class_id":
                    raise AttributeError(name)
                return getattr(self._real, name)

        state.foundation.selected = _NoClassId(state.foundation.selected)
        actions, out = self._hit(state)
        names = [a[0] for a in actions]
        self.assertIn("MOB_COMBAT_ANNOUNCE", names)
        self.assertNotIn("MOB_COMBAT_POSE_TRIAL", names)
        self.assertIn("POSE_NO_EQUIP_PROVENANCE", out)
