"""ATTACK-POSE-ONE-FIELD-AB-001: the trial gate over ActionVital +0x30.

The first test in this file is the one COO-DECISION 20260904_2141 point 2 is
about -- with no environment armed, the composed frame is byte-identical to
the frame main composes today and the console says nothing -- and the second
is the one that makes the first mean something, by mutating this lane's own
gate and watching the pin go red.
"""
import contextlib
import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import pose_trial
from pirateforce_foundation.action_ack import make_scene007_action_ack
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.scene_load import load_scene_load_scenario
from pirateforce_foundation.session import (
    FoundationSession, ReadOnlyFoundationSession,
)
from pirateforce_foundation.store import SQLiteStore

ECHO = 0xEA7D  # 60029, the selector every captured request has carried.


class GateReadingTests(unittest.TestCase):
    """What the environment says, and what the gate makes of it."""

    def test_an_unset_or_cleared_variable_is_not_an_error(self):
        for environ in ({}, {"PF_POSE_TRIAL": ""}, {"PF_POSE_TRIAL": "   "}):
            with self.subTest(environ=environ):
                self.assertEqual(
                    pose_trial.trial_opening(environ),
                    (pose_trial.TRIAL_UNSET, None),
                )

    def test_every_id_the_ticket_sweeps_arms_the_gate(self):
        for value in pose_trial.TICKET_SWEEP_ORDER + (ECHO, 0, 0xFFFFFFFF):
            with self.subTest(value=value):
                self.assertEqual(
                    pose_trial.trial_opening({"PF_POSE_TRIAL": str(value)}),
                    (pose_trial.TRIAL_ARMED, value),
                )

    def test_hex_is_the_same_selector_as_its_decimal(self):
        for text in ("0x118", "0X118"):
            with self.subTest(text=text):
                self.assertEqual(
                    pose_trial.trial_opening({"PF_POSE_TRIAL": text}),
                    (pose_trial.TRIAL_ARMED, 280),
                )

    def test_anything_the_owner_did_not_mean_to_type_is_malformed(self):
        # `1_0`, `0b1` and `0o7` are here because `int(text, 0)` would have
        # accepted all three: a selector nobody chose is exactly what costs
        # an attended round.  The unicode digit is here because `str.isdigit`
        # alone says yes to it and `int()` would then return 2.
        for text in ("fast", "-1", "280.0", "1e2", "1_0", "0b1", "0o7", "0x",
                     "0xzz", "4294967296", "٢", "280 290", "auto2"):
            with self.subTest(text=text):
                self.assertEqual(
                    pose_trial.trial_opening({"PF_POSE_TRIAL": text}),
                    (pose_trial.TRIAL_MALFORMED, None),
                )

    def test_auto_is_refused_while_no_equip_type_has_a_provenance(self):
        # RE-110 nonclaim 5 and COO 2141 point 2: `auto` may not guess.
        self.assertIsNone(pose_trial.equip_type_of_performer())
        for text in ("auto", "AUTO", " Auto "):
            with self.subTest(text=text):
                self.assertEqual(
                    pose_trial.trial_opening({"PF_POSE_TRIAL": text}),
                    (pose_trial.TRIAL_NO_PROVENANCE, None),
                )

    def test_auto_resolves_through_the_re110_crosswalk_the_day_it_can(self):
        # The gate is not merely refusing today because it has no code path:
        # give the provenance a value and the RE-110 row is what comes back.
        original = pose_trial.equip_type_of_performer
        try:
            for equip_type, behavior in sorted(
                    pose_trial.ATTACK_BEHAVIOR_BY_EQUIP_TYPE.items()):
                pose_trial.equip_type_of_performer = (
                    lambda state=None, _t=equip_type: _t
                )
                with self.subTest(equip_type=equip_type):
                    self.assertEqual(
                        pose_trial.trial_opening({"PF_POSE_TRIAL": "auto"}),
                        (pose_trial.TRIAL_ARMED, behavior),
                    )
            pose_trial.equip_type_of_performer = lambda state=None: 3
            self.assertEqual(
                pose_trial.trial_opening({"PF_POSE_TRIAL": "auto"}),
                (pose_trial.TRIAL_NO_PROVENANCE, None),
            )
        finally:
            pose_trial.equip_type_of_performer = original

    def test_a_hostile_environment_is_malformed_and_never_an_exception(self):
        # action_ack is called from inside state.dispatch(); the frozen
        # game_listener has no except handlers (interlock X07), so a gate
        # that raises kills the thread.
        class Hostile:
            def get(self, key):
                raise RuntimeError("no")

        self.assertEqual(
            pose_trial.trial_opening(Hostile()),
            (pose_trial.TRIAL_MALFORMED, None),
        )
        for raw in (object(), 280, None):
            with self.subTest(raw=raw):
                state, value = pose_trial.trial_opening({"PF_POSE_TRIAL": raw})
                self.assertIsNone(value)
                self.assertIn(
                    state, (pose_trial.TRIAL_MALFORMED, pose_trial.TRIAL_UNSET),
                )

    def test_the_console_token_names_the_arm_by_what_was_actually_sent(self):
        self.assertEqual(
            pose_trial.console_token(ECHO, ECHO, pose_trial.TRIAL_ARMED),
            "POSE_TRIAL sent=+0x30=60029 control",
        )
        self.assertEqual(
            pose_trial.console_token(280, ECHO, pose_trial.TRIAL_ARMED),
            "POSE_TRIAL sent=+0x30=280 mutant",
        )
        self.assertEqual(
            pose_trial.console_token(ECHO, ECHO, pose_trial.TRIAL_MALFORMED),
            "POSE_TRIAL_REFUSED malformed sent=+0x30=60029 control",
        )
        self.assertEqual(
            pose_trial.console_token(
                ECHO, ECHO, pose_trial.TRIAL_NO_PROVENANCE),
            "POSE_TRIAL_REFUSED auto_no_equip_type_provenance "
            "sent=+0x30=60029 control",
        )

    def test_a_refused_arming_ships_the_requests_own_selector(self):
        for text in ("fast", "auto"):
            with self.subTest(text=text):
                sent, line = pose_trial.selector_for_reply(
                    ECHO, {"PF_POSE_TRIAL": text})
                self.assertEqual(sent, ECHO)
                self.assertTrue(line.startswith("POSE_TRIAL_REFUSED "))

    def test_unset_returns_the_echo_and_no_console_line_at_all(self):
        self.assertEqual(
            pose_trial.selector_for_reply(ECHO, {}), (ECHO, None),
        )

    def test_every_console_line_is_ascii(self):
        # The bridge console is cp874; a non-ASCII byte here raises
        # UnicodeEncodeError inside the dispatch path.
        for state in (pose_trial.TRIAL_ARMED, pose_trial.TRIAL_MALFORMED,
                      pose_trial.TRIAL_NO_PROVENANCE):
            line = pose_trial.console_token(280, ECHO, state)
            with self.subTest(state=state):
                self.assertTrue(line.isascii())
                line.encode("cp874")


class ComposedFrameTests(unittest.TestCase):
    """What the real composer puts on the wire, byte for byte."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def fields(self):
        return {
            "field_qword_20": 0x203D,
            "field_qword_28": 0,
            "action_u32_30": ECHO,
            "field_u32_34": 0,
            "heading_f32_38": 1.25,
            "x_f32_3c": 2.5,
            "y_f32_40": 3.5,
            "z_f32_44": 4.5,
            "field_u8_48": 0,
            "field_u16_4a": 1,
            "field_u8_4c": 0,
        }

    def compose(self, environ):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            pc, frame = make_scene007_action_ack(
                self.legacy, self.fields(), 0x1234, environ=environ,
            )
        return pc, frame, out.getvalue()

    def test_an_unarmed_boot_is_byte_and_line_identical_to_production(self):
        pc, frame, printed = self.compose({})
        control_pc, control_frame, control_printed = self.compose(
            {"PF_POSE_TRIAL": str(ECHO)})
        self.assertEqual(printed, "")
        self.assertEqual(control_pc, pc)
        self.assertEqual(control_frame, frame)
        self.assertEqual(
            control_printed, "POSE_TRIAL sent=+0x30=60029 control\n")

    def test_a_refused_arming_composes_the_unarmed_bytes(self):
        baseline, _, _ = self.compose({})
        for text in ("fast", "auto", ""):
            with self.subTest(text=text):
                pc, _, printed = self.compose({"PF_POSE_TRIAL": text})
                self.assertEqual(pc, baseline)
                if text:
                    self.assertIn("POSE_TRIAL_REFUSED", printed)
                else:
                    self.assertEqual(printed, "")

    def test_a_mutant_moves_exactly_the_four_bytes_of_that_one_field(self):
        baseline, _, _ = self.compose({})
        for value in pose_trial.TICKET_SWEEP_ORDER:
            with self.subTest(value=value):
                pc, _, printed = self.compose({"PF_POSE_TRIAL": str(value)})
                self.assertEqual(len(pc), len(baseline))
                differing = [
                    i for i, (a, b) in enumerate(zip(pc, baseline)) if a != b
                ]
                # Two of the four bytes are 0x00 in both selectors (280 is
                # 0x00000118, 60029 is 0x0000EA7D), so the claim is "inside
                # one 4-byte window", not "four bytes changed value".
                self.assertTrue(differing)
                self.assertLessEqual(max(differing) - min(differing), 3,
                                     differing)
                # And the four bytes are the u32 the tag carries, in the one
                # place the request's own selector used to sit.
                self.assertEqual(
                    pc.replace(
                        self.legacy.u32tag(0x14, value),
                        self.legacy.u32tag(0x14, ECHO), 1),
                    baseline,
                )
                self.assertEqual(
                    printed, "POSE_TRIAL sent=+0x30=%d mutant\n" % value)

    def test_the_byte_identity_pin_can_actually_fail(self):
        """Mutate this lane's own gate; the pin above must go red.

        Without this, `test_an_unarmed_boot_is_byte_and_line_identical` would
        also pass on a build where the gate was accidentally unreachable --
        it would be pinning nothing.
        """
        baseline, _, _ = self.compose({})
        original = pose_trial.trial_opening
        try:
            pose_trial.trial_opening = (
                lambda environ=None: (pose_trial.TRIAL_ARMED, 280)
            )
            pc, _, printed = self.compose({})
            self.assertNotEqual(pc, baseline)
            self.assertEqual(printed, "POSE_TRIAL sent=+0x30=280 mutant\n")
        finally:
            pose_trial.trial_opening = original
        self.assertEqual(self.compose({})[0], baseline)


class DispatchTests(unittest.TestCase):
    """The same claim one layer out: through the real ActionVital dispatch."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "a.sqlite3"
        self.store = SQLiteStore(self.db, ROOT / "migrations")
        self.store.migrate()
        self.v = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.projector = LegacyProjector(self.v)
        default = Position(
            1, 0, self.v.V135_PLAYER_X, self.v.V135_PLAYER_Y,
            self.v.V135_PLAYER_Z,
        )
        self.lifecycle = CharacterLifecycle(
            self.store, default, self.v.extract_avatar_attr_wire_from_actor,
        )
        seed = FoundationSession(self.lifecycle, self.projector, "pose-user")
        actor = self.v.get_preset_actor_wire().replace(
            self.v.wstr_tag("test01"), self.v.wstr_tag("Arena01"), 1)
        self.character, _ = seed.create("Arena01", actor)
        self.scenario = load_scene_load_scenario(
            ROOT / "scenarios/port_royal_fighting_fish_soldier_hp3857_"
                   "player_faction1_ea7d_ack.json")

    def tearDown(self):
        self.tmp.cleanup()

    def request(self):
        v = self.v
        body = (
            v.qwordtag(0x32, 0) + v.qwordtag(0x32, 0x203D)
            + v.qwordtag(0x32, 0) + v.u32tag(0x14, ECHO) + v.u32tag(0x19, 0)
            + b"".join(v.f32tag(f) for f in (1.25, 2.5, 3.5, 4.5))
            + v.u8tag(0x0B, 0) + v.u16tag(0x12, 1) + v.u8tag(0x0B, 0)
        )
        targetpos = (
            v.u16tag(0x12, v.TARGET_POS_VITAL) + v.u8tag(0x0B, 0)
            + b"".join(v.f32tag(f) for f in (2.5, 3.5, 4.5, 1.25))
            + v.u8tag(0x0B, 0) + v.u8tag(0x0B, 0)
        )
        pc = (
            v.u16tag(0x12, v.GSCN_RUNTIME_PROTOCOL_REQ) + v.u32tag(0x14, 0)
            + v.u8tag(0x08, 0) + v.u8tag(0x0B, 2) + v.u16tag(0x12, 2)
            + v.u16tag(0x12, v.ACTION_VITAL) + v.u8tag(0x0B, 0) + body
            + targetpos
        )
        return v.parse_outer(pc)

    def state(self):
        factory = lambda token: ReadOnlyFoundationSession(  # noqa: E731
            self.store, self.projector, token, self.scenario)
        cls = make_state_class(
            self.v, self.lifecycle, self.projector,
            scene_load_scenario=self.scenario, session_factory=factory)
        state = cls("pose-user")
        state.foundation.selected = self.character
        state.runtime_ack_sent = True
        state.teleport_sent = True
        state.scene_remote_spawned = True
        state.scene_remote_target_captured = True
        state.scene_hostile_target_captured = True
        return state

    def dispatch(self, environ):
        # Touch ONLY this lane's key: `os.environ.clear()` would unset every
        # other variable in the process for the duration of a dispatch, and
        # this suite shares that process with everything else pytest runs.
        missing = object()
        saved = pose_trial.os.environ.get(
            pose_trial.POSE_TRIAL_ENV, missing)
        out = io.StringIO()
        try:
            pose_trial.os.environ.pop(pose_trial.POSE_TRIAL_ENV, None)
            pose_trial.os.environ.update(environ)
            with contextlib.redirect_stdout(out):
                actions = self.state().dispatch(self.request())
        finally:
            pose_trial.os.environ.pop(pose_trial.POSE_TRIAL_ENV, None)
            if saved is not missing:
                pose_trial.os.environ[pose_trial.POSE_TRIAL_ENV] = saved
        self.assertEqual([action[0] for action in actions],
                         ["SCENE007_EA7D_ACTION_ACK_ONCE"])
        return actions[0][1], out.getvalue()

    def test_the_real_dispatch_path_reads_the_process_environment(self):
        # The runtime call site passes no `environ`, so this is the only
        # test that proves an attended boot -- which sets the variable in
        # the process, not in a keyword argument -- moves the field at all.
        baseline, printed = self.dispatch({})
        self.assertNotIn("POSE_TRIAL", printed)
        mutant, mutant_printed = self.dispatch({"PF_POSE_TRIAL": "280"})
        self.assertNotEqual(mutant, baseline)
        self.assertEqual(len(mutant), len(baseline))
        self.assertIn("POSE_TRIAL sent=+0x30=280 mutant", mutant_printed)
        self.assertEqual(
            hashlib.sha256(self.dispatch({})[0]).hexdigest(),
            hashlib.sha256(baseline).hexdigest(),
        )
        control, control_printed = self.dispatch(
            {"PF_POSE_TRIAL": str(ECHO)})
        self.assertEqual(control, baseline)
        self.assertIn("POSE_TRIAL sent=+0x30=60029 control", control_printed)


if __name__ == "__main__":
    unittest.main()
