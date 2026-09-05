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

  * an unset or malformed ``PF_POSE_TRIAL`` sends the exact same two frames
    (``MOB_COMBAT_ANNOUNCE``, ``MOB_COMBAT_BAR``) an unarmed boot already
    sends today, with nothing extra;
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


class MobCombatPoseTrialWiringTests(unittest.TestCase):
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

    def _clear_class_id(self, state):
        """Force the selected Character's `class_id` back to None.

        CORE-REQUEST 20260905_2242: runtime.py now passes the real
        `class_id` into this call site, so `_V25_REAL_CREATE_PC` (this
        harness's synthetic creation packet) resolving to a real class
        (Gladiator, class_id=1 -- see CHARACTER_CLASS_ID in these tests'
        own stdout) makes the PRODUCTION pose composer answer with a real,
        screen-confirmed behavior on every accepted hit, unarmed or not.
        The three tests below are about the ``PF_POSE_TRIAL`` env-var gate
        specifically (this file's own module docstring: "NOT proven here:
        whether a real client plays an attack animation... this file
        proves the wire only"), not about the production path -- that is
        ``test_action_ack.py``/``test_combat_pose.py``'s job, and
        ``test_production_class_id_reaches_the_composer`` below, which
        proves runtime.py's wiring end-to-end.  So they clear class_id to
        keep testing exactly what they always tested: "unarmed sends
        nothing extra" when there is nothing (yet) for the composer to
        answer with.
        """
        state.foundation.selected = replace(
            state.foundation.selected, class_id=None,
        )

    def _hit(self, state, target_identity=CONTROL_TARGET):
        """One accepted, survived hit: attack, then heal back to full so
        the next call is not a killing blow, and advance the injected
        clock past the cadence window."""
        actions, out = self._attack(state, target_identity)
        self._set_balance(state, target_identity, self.control_mob.max_hp)
        self.clock_ms += mob_combat.ATTACK_CADENCE_MS_PROVISIONAL + 1
        return actions, out

    # ----- unarmed: byte-for-byte what main already sends ----------------

    def test_unset_sends_no_pose_trial_frame(self):
        os.environ.pop(POSE_TRIAL_ENV, None)
        state = self._state("mc_pose_unset")
        self._clear_class_id(state)
        actions, out = self._hit(state)
        self.assertEqual(
            [label for label, *_ in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        self.assertNotIn("POSE_TRIAL", out)

    def test_malformed_sends_no_frame_but_says_so(self):
        os.environ[POSE_TRIAL_ENV] = "not-a-number"
        state = self._state("mc_pose_malformed")
        self._clear_class_id(state)
        actions, out = self._hit(state)
        self.assertEqual(
            [label for label, *_ in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        self.assertIn("POSE_TRIAL_REFUSED malformed hit=1", out)

    def test_a_bare_empty_or_whitespace_value_is_unset_not_armed(self):
        for raw in ("", "   "):
            with self.subTest(raw=repr(raw)):
                os.environ[POSE_TRIAL_ENV] = raw
                state = self._state("mc_pose_blank_%d" % len(raw))
                self._clear_class_id(state)
                actions, out = self._hit(state)
                self.assertEqual(
                    [label for label, *_ in actions],
                    ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
                )
                self.assertNotIn("POSE_TRIAL", out)

    # ----- unarmed, real class: the production path CORE-REQUEST 2242 asked
    # for -- proves runtime.py actually passes class_id through, not just
    # that the composer can accept one (test_action_ack.py's job).
    # ------------------------------------------------------------------

    def test_production_class_id_reaches_the_composer(self):
        os.environ.pop(POSE_TRIAL_ENV, None)
        state = self._state("mc_pose_production_class")
        # _V25_REAL_CREATE_PC resolves to class_id=1 (Gladiator) today --
        # CHARACTER_CLASS_ID cid=1 written class_id=1 on stdout of every
        # test in this file that does not call _clear_class_id.  Assert it
        # rather than assume it, so a future change to the synthetic
        # creation packet fails this test loudly instead of this test
        # quietly proving nothing.
        self.assertEqual(state.foundation.selected.class_id, 1)
        actions, out = self._hit(state)
        self.assertEqual(
            [label for label, *_ in actions],
            ["MOB_COMBAT_POSE_TRIAL", "MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        # combat_pose.production_behavior_for_class(1) -> BEHAVIOR 280, the
        # sword swing GT-247/R315 watched a Gladiator play on the real
        # screen (SCREEN_CONFIRMED_BEHAVIOR_IDS) -- this is the unit fact
        # tests/test_combat_pose.py pins; this test only proves runtime.py
        # hands the composer the class that produces it.
        self.assertIn("POSE_PRODUCTION class=1", out)
        _label, pc, frame, delay = actions[0]
        self.assertEqual(delay, 0.0)
        fields = self.legacy.parse_action_vital(self.legacy.parse_outer(
            self._action_vital_pc(CONTROL_TARGET)
        ))
        performer = (
            ((state.foundation.selected.identity_hi & 0xFFFFFFFF) << 32)
            | (state.foundation.selected.identity_lo & 0xFFFFFFFF)
        )
        expected_pc, expected_frame = build_action_vital_echo(
            self.legacy, fields, performer, 280,
        )
        self.assertEqual((pc, frame), (expected_pc, expected_frame))

    def test_no_equip_provenance_prints_once_per_connection_not_per_hit(self):
        """CORE-REQUEST 20260905_2242 item 2, COO-DECISION 20260906_0346."""
        os.environ.pop(POSE_TRIAL_ENV, None)
        state = self._state("mc_pose_provenance_throttle")
        self._clear_class_id(state)
        self.assertEqual(
            state.pose_no_equip_provenance_reported, [False],
        )
        _actions1, out1 = self._hit(state)
        self.assertIn("POSE_NO_EQUIP_PROVENANCE", out1)
        self.assertEqual(
            state.pose_no_equip_provenance_reported, [True],
        )
        # Second hit, same connection: the refusal is the same fact as the
        # first hit's -- still no class_id -- so it does not print again.
        _actions2, out2 = self._hit(state)
        self.assertNotIn("POSE_NO_EQUIP_PROVENANCE", out2)
        self.assertEqual(
            state.pose_no_equip_provenance_reported, [True],
        )
        # A different connection (a fresh session object) starts with its
        # own slot at False -- the flag is per-connection, not global.
        other = self._state("mc_pose_provenance_throttle_other")
        self._clear_class_id(other)
        self.assertEqual(other.pose_no_equip_provenance_reported, [False])
        _actions3, out3 = self._hit(other)
        self.assertIn("POSE_NO_EQUIP_PROVENANCE", out3)

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
