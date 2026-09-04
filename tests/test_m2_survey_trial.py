"""LANE-E / M2: the attended-only trial gate, its two trial numbers, and the
one runtime.py call site they admit.

The interesting tests here are the last class: a guard that used to say
"nobody may call world_m2_provisioning_trial" now says "exactly one caller,
and only inside the branch the flag opens".  If that structural claim ever
stops being true, this file goes red rather than the wiring going quiet.
"""
from __future__ import annotations

import ast
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import m2_survey_trial  # noqa: E402


class TrialOpeningTests(unittest.TestCase):
    def test_unset_is_shut(self):
        self.assertEqual(
            m2_survey_trial.trial_opening(environ={}),
            m2_survey_trial.TRIAL_UNSET,
        )

    def test_exactly_one_opens_it(self):
        self.assertEqual(
            m2_survey_trial.trial_opening(
                environ={m2_survey_trial.SURVEY_TRIAL_ENV: "1"},
            ),
            m2_survey_trial.TRIAL_OPEN,
        )

    def test_every_other_value_is_malformed_and_shut(self):
        for raw in ("", "0", "true", "True", " 1", "1 ", "01", "2", "yes"):
            with self.subTest(raw=raw):
                self.assertEqual(
                    m2_survey_trial.trial_opening(
                        environ={m2_survey_trial.SURVEY_TRIAL_ENV: raw},
                    ),
                    m2_survey_trial.TRIAL_MALFORMED,
                )

    def test_a_broken_environ_is_shut_and_never_raises(self):
        class Exploding:
            def get(self, _name):
                raise RuntimeError("no environment here")

        self.assertEqual(
            m2_survey_trial.trial_opening(environ=Exploding()),
            m2_survey_trial.TRIAL_MALFORMED,
        )

    def test_malformed_is_not_the_same_token_as_unset(self):
        # An operator who armed the flag and typo'd the value must be able
        # to tell that from having forgotten it.
        self.assertNotEqual(
            m2_survey_trial.TRIAL_UNSET, m2_survey_trial.TRIAL_MALFORMED,
        )


class TrialNumbersTests(unittest.TestCase):
    def test_the_trial_msg_id_is_the_hash_of_the_client_s_own_typo(self):
        # The whole provenance of this number in one line: it is the v141
        # protocol_name_id hash of the name as the client misspells it.
        self.assertEqual(
            m2_survey_trial.protocol_name_id(
                m2_survey_trial.NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_NAME,
            ),
            m2_survey_trial.NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_ID_TRIAL,
        )

    def test_the_typo_is_load_bearing(self):
        # Spelled correctly, the same hash gives a DIFFERENT id -- so a
        # future tidy-up of the constant's spelling is a red test, not a
        # frame the client silently ignores.
        self.assertNotEqual(
            m2_survey_trial.protocol_name_id(
                "NavigationEx_AddSurveyDataVital",
            ),
            m2_survey_trial.NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_ID_TRIAL,
        )

    def test_the_hash_reproduces_the_two_proven_navigationex_ids(self):
        # Controls, from pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_
        # 20260817.tsv (the only two NavigationEx rows it carries) plus the
        # id runtime.py already pins for the confirm frame.
        for name, wire_id in (
            ("NavigationEx_EnterInstanceVital", 0xC723),
            ("NavigationEx_UseAddingMoraleItemResultVital", 0x7A94),
            ("TriggerVital", 0x1FB2),
        ):
            with self.subTest(name=name):
                self.assertEqual(
                    m2_survey_trial.protocol_name_id(name), wire_id,
                )

    def test_the_sea_scene_is_the_one_gt228_measured(self):
        self.assertEqual(m2_survey_trial.M2_SEA_SCENE_ID, 126)


class ConsoleLineTests(unittest.TestCase):
    def test_every_line_is_ascii(self):
        # The bridge console is cp874; a non-ascii byte kills the tool
        # mid-report (rounds 86 and 142).
        lines = [
            m2_survey_trial.console_line(m2_survey_trial.TRIAL_OPEN, 126, 2),
            m2_survey_trial.console_line(m2_survey_trial.TRIAL_UNSET, 126),
            m2_survey_trial.console_line(
                m2_survey_trial.TRIAL_MALFORMED, 126,
            ),
            m2_survey_trial.refusal_line(126, "ValueError"),
        ]
        for line in lines:
            with self.subTest(line=line):
                line.encode("ascii")

    def test_the_armed_line_names_both_trial_numbers(self):
        line = m2_survey_trial.console_line(
            m2_survey_trial.TRIAL_OPEN, 126, 2,
        )
        self.assertIn("M2_SURVEY_TRIAL_SENT", line)
        self.assertIn("scene=126", line)
        self.assertIn("records=2", line)
        self.assertIn("msg_id=0xC4AF", line)
        self.assertIn("version=0", line)

    def test_a_shut_boot_and_a_broken_trial_carry_different_tokens(self):
        shut = m2_survey_trial.console_line(m2_survey_trial.TRIAL_UNSET, 126)
        broken = m2_survey_trial.refusal_line(126, "no_records")
        self.assertIn("M2_SURVEY_TRIAL_NOT_THIS_BOOT", shut)
        self.assertIn("M2_SURVEY_TRIAL_REFUSED", broken)
        self.assertNotIn("M2_SURVEY_TRIAL_REFUSED", shut)
        self.assertNotIn("M2_SURVEY_TRIAL_NOT_THIS_BOOT", broken)


class RuntimeCallSiteTests(unittest.TestCase):
    """The structural half of the guard that `tests/test_world_m2_
    provisioning_trial.py` widened for this call site.

    That guard can only say "runtime.py is allowed to name the module".
    These say what it is allowed to do with it.
    """

    RUNTIME = ROOT / "src" / "pirateforce_foundation" / "runtime.py"

    def _tree(self):
        return ast.parse(self.RUNTIME.read_text(encoding="utf-8"))

    @staticmethod
    def _calls_named(tree, dotted: str):
        found = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            target = node.func
            if not isinstance(target, ast.Attribute):
                continue
            if not isinstance(target.value, ast.Name):
                continue
            if f"{target.value.id}.{target.attr}" == dotted:
                found.append(node)
        return found

    def test_exactly_one_call_to_the_composer(self):
        calls = self._calls_named(
            self._tree(), "world_m2_provisioning_trial.encode_trial_records",
        )
        self.assertEqual(
            len(calls), 1,
            "the M2 provisioning trial has exactly one call site in "
            f"runtime.py; found {len(calls)}",
        )

    def test_the_composer_is_called_inside_the_function_that_opens_the_flag(
        self,
    ):
        tree = self._tree()
        composer = self._calls_named(
            tree, "world_m2_provisioning_trial.encode_trial_records",
        )[0]
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if composer not in set(ast.walk(node)):
                continue
            openings = self._calls_named(
                node, "m2_survey_trial.trial_opening",
            )
            if openings:
                return
        self.fail(
            "runtime.py calls encode_trial_records outside every function "
            "that calls m2_survey_trial.trial_opening() -- the attended-only "
            "flag no longer admits the trial",
        )

    def test_both_trial_numbers_reach_the_composer_from_the_gate_module(self):
        # No hand-typed 0xC4AF / 0 at the call site: the numbers must come
        # from the module that carries their evidence note.
        composer = self._calls_named(
            self._tree(),
            "world_m2_provisioning_trial.encode_trial_records",
        )[0]
        passed = {kw.arg: kw.value for kw in composer.keywords}
        self.assertEqual(set(passed), {"msg_id", "vital_version"})
        for arg, value in passed.items():
            with self.subTest(arg=arg):
                self.assertIsInstance(value, ast.Attribute)
                self.assertIsInstance(value.value, ast.Name)
                self.assertEqual(value.value.id, "m2_survey_trial")

    def test_the_server_never_composes_the_client_s_confirm_frame(self):
        """COO-DECISION 20260904_1845 item 4: the server must not send
        `NavigationEx_EnterInstanceVital` itself -- that is the CLIENT's
        confirm frame, and a server that sends it answers its own question.

        Asserted on the SHAPE, not on a substring.  The first draft checked
        `"make_enter_instance" not in source`, a string that names no
        function anywhere in this repository and therefore could never fail
        (pf-adversary D9); the way this ban would actually be broken is a
        `legacy.make_runtime_vital(s)` call carrying
        `NAVIGATIONEX_ENTER_INSTANCE_VITAL_ID`, which is what this looks
        for.  runtime.py may still NAME that constant -- it dispatches the
        inbound frame -- so only its use as a composer argument is banned.
        """
        composers = {"make_runtime_vital", "make_runtime_vitals"}
        tree = self._tree()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute)
                    and func.attr in composers):
                continue
            names = {
                child.id for child in ast.walk(node)
                if isinstance(child, ast.Name)
            }
            self.assertNotIn(
                "NAVIGATIONEX_ENTER_INSTANCE_VITAL_ID", names,
                "runtime.py composes the client's own confirm frame; "
                "COO-DECISION 20260904_1845 item 4 forbids it",
            )



class DispatchWiringTests(unittest.TestCase):
    """The behavioural half: `make_state_class` driven headless (no server
    process, no socket, no client), proving that a runtime poll taken while
    the session is in the sea scene really does put the two survey frames on
    the returned action list -- and really does not, on a flagless boot.

    Same harness shape as `tests/test_lane_a_trigger_vital_dispatch_wiring.py`
    (chief's previous call site for this same lane); the structural tests
    above cannot prove this half and this half cannot prove theirs.
    """

    def setUp(self):
        import tempfile

        from pirateforce_foundation import field_mobs
        from pirateforce_foundation.legacy_bridge import (
            LegacyProjector, load_legacy,
        )
        from pirateforce_foundation.lifecycle import CharacterLifecycle
        from pirateforce_foundation.model import Position
        from pirateforce_foundation.store import SQLiteStore

        self.Position = Position
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            pathlib.Path(self.tmp.name) / "state.sqlite3",
            ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = load_legacy(ROOT / "current"
                                 / "pf_login_game_server_v141.py")
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        field_mobs.load_roster()

    def _poll_pc(self):
        """An empty runtime-protocol poll -- the same boundary the arrival
        census uses, and the one the call site keys on.
        """
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 0)
        )

    def _session_in_scene(self, token, scene_id):
        import contextlib
        import dataclasses
        import io

        from pirateforce_foundation.runtime import make_state_class

        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)
            ))
        state.runtime_ack_sent = True
        # Relabel the IN-MEMORY row only, exactly as the GM cross-scene warp
        # resync does (runtime.py, `_gm_warp_resync_selected_scene`).  Scene
        # 126 is login-barred, so a stored row cannot carry the session
        # there; the attended round gets there by warp, and this is that
        # arrival's shape without a GM account or a chat frame.
        selected = state.foundation.selected
        state.foundation.selected = dataclasses.replace(
            selected,
            position=dataclasses.replace(
                selected.position, scene_id=scene_id,
            ),
        )
        return state

    def _poll(self, state):
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = state.dispatch(
                self.legacy.parse_outer(self._poll_pc())
            )
        trial = [a for a in actions if a[0].startswith("M2_SURVEY_TRIAL")]
        return trial, buf.getvalue()

    def _arm(self):
        import os

        os.environ[m2_survey_trial.SURVEY_TRIAL_ENV] = "1"
        self.addCleanup(
            os.environ.pop, m2_survey_trial.SURVEY_TRIAL_ENV, None,
        )

    def test_a_flagless_boot_sends_nothing_and_says_so_once(self):
        state = self._session_in_scene(
            "m2shut", m2_survey_trial.M2_SEA_SCENE_ID,
        )
        trial, console = self._poll(state)
        self.assertEqual(trial, [])
        self.assertIn("M2_SURVEY_TRIAL_NOT_THIS_BOOT", console)
        self.assertIn("reason=unset", console)
        # ...once per arrival, not once per poll.
        trial_again, console_again = self._poll(state)
        self.assertEqual(trial_again, [])
        self.assertNotIn("M2_SURVEY_TRIAL", console_again)

    def test_an_armed_boot_sends_both_records_twice_in_the_sea_scene(self):
        from pirateforce_foundation import world_population

        self._arm()
        state = self._session_in_scene(
            "m2armed", m2_survey_trial.M2_SEA_SCENE_ID,
        )
        trial, console = self._poll(state)
        # Two records, each queued INITIAL and REAPPLY -- the schedule
        # world_population.py:184-188 records as the one that was accepted
        # ("a caller that sends one frame is not reproducing what was
        # accepted"), pf-adversary D4.
        self.assertEqual(len(trial), 4, trial)
        labels = sorted(action[0] for action in trial)
        self.assertEqual(labels, [
            "M2_SURVEY_TRIAL_SURVEY2_DOCK153_INITIAL",
            "M2_SURVEY_TRIAL_SURVEY2_DOCK153_REAPPLY",
            "M2_SURVEY_TRIAL_SURVEY3_DOCK154_INITIAL",
            "M2_SURVEY_TRIAL_SURVEY3_DOCK154_REAPPLY",
        ])
        # The label leads with the value that is ON THE WIRE (survey_id
        # 2/3), not the dock-table id, because the label is what an
        # attended capture gets matched against and 153/154 never appear on
        # the wire (LANE-A's warning, pf-adversary D3).
        for label, pc, frame, delay in trial:
            self.assertIsInstance(pc, bytes)
            self.assertIsInstance(frame, bytes)
            self.assertTrue(frame)
            self.assertEqual(
                delay,
                0.0 if label.endswith("_INITIAL")
                else world_population.INITIAL_REAPPLY_MS / 1000.0,
            )
            # The trial msg id, the record kind byte, and the trailing
            # derived-class mask GT-010 died without (pf-adversary D1).
            self.assertIn(bytes.fromhex("12afc4"), pc)
            self.assertIn(bytes.fromhex("0b01"), pc)
            self.assertTrue(pc.endswith(bytes.fromhex("0b00")))
        self.assertIn("M2_SURVEY_TRIAL_SENT", console)
        self.assertIn("records=2", console)
        self.assertIn("msg_id=0xC4AF", console)
        # The label is a claim about a scene the client has not confirmed;
        # the line says so rather than implying otherwise (D2).
        self.assertIn("confirmed=none", console)

    def test_an_armed_boot_sends_nothing_anywhere_but_the_sea_scene(self):
        self._arm()
        for scene_id in (1, 2, 17, 125, 127, 130):
            with self.subTest(scene_id=scene_id):
                state = self._session_in_scene(f"m2s{scene_id}", scene_id)
                trial, console = self._poll(state)
                self.assertEqual(trial, [])
                self.assertNotIn("M2_SURVEY_TRIAL", console)

    def test_leaving_and_re_entering_the_sea_arms_it_exactly_once_more(self):
        import dataclasses

        self._arm()
        state = self._session_in_scene(
            "m2return", m2_survey_trial.M2_SEA_SCENE_ID,
        )
        first, _ = self._poll(state)
        self.assertEqual(len(first), 4)
        self.assertEqual(self._poll(state)[0], [])

        def relabel(scene_id):
            selected = state.foundation.selected
            state.foundation.selected = dataclasses.replace(
                selected,
                position=dataclasses.replace(
                    selected.position, scene_id=scene_id,
                ),
            )

        relabel(1)
        self.assertEqual(self._poll(state)[0], [])
        relabel(m2_survey_trial.M2_SEA_SCENE_ID)
        again, _ = self._poll(state)
        self.assertEqual(len(again), 4)
        self.assertEqual(self._poll(state)[0], [])
    def _trial_frames(self):
        """The exact frames the trial numbers compose, built here so a
        flagless boot can be checked for the BYTES rather than for a label.

        pf-adversary D8 wrote a runtime.py mutant that shipped these frames
        on a flagless boot under a different label and passed every test in
        this file: both behavioural tests filtered on the `M2_SURVEY_TRIAL`
        prefix, so renaming the label made the send invisible to them. The
        bytes cannot be renamed.
        """
        from pirateforce_foundation import world_m2_provisioning_trial

        return {
            frame for _dock, _pc, frame in
            world_m2_provisioning_trial.encode_trial_records(
                self.legacy,
                msg_id=m2_survey_trial
                .NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_ID_TRIAL,
                vital_version=m2_survey_trial
                .NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_VERSION_TRIAL,
            )
        }

    def test_a_flagless_boot_puts_none_of_the_trial_bytes_on_the_wire(self):
        state = self._session_in_scene(
            "m2bytes", m2_survey_trial.M2_SEA_SCENE_ID,
        )
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = state.dispatch(
                self.legacy.parse_outer(self._poll_pc())
            )
        forbidden = self._trial_frames()
        self.assertTrue(forbidden)
        for label, _pc, frame, _delay in actions:
            with self.subTest(label=label):
                self.assertNotIn(
                    frame, forbidden,
                    f"action {label!r} carries the trial's own frame bytes "
                    "on a boot where PF_M2_SURVEY_TRIAL is unset",
                )

    def test_a_send_made_before_the_client_confirmed_is_made_again_after(
        self,
    ):
        """pf-adversary D2: `/warp 126` relabels the row at queue time and
        the client may ignore it, so the first send can land while the
        player is still elsewhere.  The trial re-arms exactly once when the
        client does confirm the scene -- and then stops.
        """
        self._arm()
        state = self._session_in_scene(
            "m2confirm", m2_survey_trial.M2_SEA_SCENE_ID,
        )
        first, first_console = self._poll(state)
        self.assertEqual(len(first), 4)
        self.assertIn("confirmed=none", first_console)
        self.assertEqual(self._poll(state)[0], [])

        state.client_confirmed_scene = m2_survey_trial.M2_SEA_SCENE_ID
        again, again_console = self._poll(state)
        self.assertEqual(len(again), 4)
        self.assertIn(
            f"confirmed={m2_survey_trial.M2_SEA_SCENE_ID}", again_console,
        )
        # ...and only once more.
        self.assertEqual(self._poll(state)[0], [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
