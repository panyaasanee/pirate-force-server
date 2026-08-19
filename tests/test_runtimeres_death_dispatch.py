"""RUNTIMERES-DISPATCH-001 (proposed HYP-PF-023) -- the sweep on the dispatcher.

``tests/test_runtimeres_death_hypothesis.py`` proves the encoder offline.  This
file drives the REAL ``make_state_class`` dispatch path behind the opt-in
``scenarios/runtimeres_death_hypothesis_spawn_then_kill.json`` and proves the
wire layer end to end, headless -- no server process, no socket, no client:

  * one accepted chat-input frame (the exact 34-byte ascii12 shape the
    HYP-PF-014 lane already classifies, reused because it is the only client
    action an attended tester can trigger on demand) produces exactly THREE
    actions, in the scenario's order, spaced by ``spacing_seconds``;
  * the bytes the dispatcher emits are **identical** to the bytes
    ``build_runtimeres_death_sweep`` composes -- label, PC, frame and delay,
    compared with ``==`` on the bytes themselves.  The dispatcher is a
    forwarder, and if it ever becomes a second composer these tests go red;
  * every frame is ``GSCN_RunTimeProtocolRes`` 0x6E9D with the inherited change
    mask ``0x00`` and the derived change mask bit ``0x02`` (the actor-entry
    collection at ``+0x1C``), one ``actor_type 4`` entry, one identity across
    all three;
  * the polarity is on the wire in the proven order: frame 2 satisfies
    ``vt+0x40`` (HP == 0 AND timer > 0, the dying latch) and frame 3 satisfies
    ``vt+0x3C`` (HP == 0 AND timer <= 0, the gate on ``CActorTask_Dead``);
  * fail-closed and containment: wrong length, wrong text bytes, no selected
    character and not-yet-runtime-ready all give ``[]`` with a named no-reply
    event; the sweep is ONE-SHOT; with no scenario the same trigger keeps its
    frozen baseline answer and composes no death frame at all; the database
    file does not move one byte; and the lane is mutually exclusive with every
    other scenario mode.

NOT proven here, and this is the load-bearing limit: whether a real client does
anything at all when it receives these bytes.  **No client has ever been shown
one byte of this profile.**  That is GT-022, attended, not run.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PROBE_REQUEST_PCS,
    CHAT_INPUT_VITAL_ID,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation import runtimeres_death_hypothesis as rdh  # noqa: E402
from pirateforce_foundation import stats_progression_hypothesis as sp  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = (
    ROOT / "scenarios" / "runtimeres_death_hypothesis_spawn_then_kill.json"
)
HP_DEATH_SCENARIO_PATH = (
    ROOT / "scenarios" / "hp_death_hypothesis_death_sweep.json"
)
REPLAY_TOOL = ROOT / "tools" / "pf_runtimeres_death_headless_replay.py"
SWEEP_EVENT = "runtimeres_death_hypothesis_spawn_then_kill_sent"
REPEAT_EVENT = "runtimeres_death_hypothesis_already_sent_no_reply"
EVENT_PREFIX = "runtimeres_death_hypothesis_"


class RuntimeResDeathRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.scenario = rdh.load_runtimeres_death_hypothesis_scenario(
            SCENARIO_PATH
        )
        self.unlock = rdh.runtimeres_death_lethal_unlock(self.scenario)
        self.probe = rdh.resolve_probe(self.legacy)
        self.pinned = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ---------------------------------------------------------

    def _state_type(self, *, sweep=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            runtimeres_death_hypothesis_scenario=(
                self.scenario if sweep else None
            ),
        )

    def _state(self, login, *, sweep=True, ready=True, select=True):
        state = self._state_type(sweep=sweep)(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        if select:
            characters = self.store.list_characters(state.foundation.account_id)
            actions = state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(characters[-1].selector)
            ))
            self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = ready
        return state

    def _trigger(self, probe="probe1"):
        return self.legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS[probe])

    def _trigger_pc(self, payload, *, outer_version=0, nested_version=0):
        legacy = self.legacy
        return bytes(
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, outer_version)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, CHAT_INPUT_VITAL_ID)
            + legacy.u8tag(0x0B, nested_version)
            + payload
        )

    def _expected(self):
        """The encoder's composition, built without the dispatcher."""
        return rdh.build_runtimeres_death_sweep(
            self.legacy, self.probe, self.unlock, self.scenario,
        )

    def _db_digest(self):
        return hashlib.sha256(self.db_path.read_bytes()).hexdigest()

    # ----- happy path ------------------------------------------------------

    def test_one_request_sweeps_the_three_steps_in_the_pinned_order(self):
        state = self._state("rrd01")
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), len(rdh.RUNTIMERES_DEATH_STEP_ORDER))
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            list(rdh.RUNTIMERES_DEATH_ACTION_LABELS),
        )
        self.assertEqual(
            list(rdh.RUNTIMERES_DEATH_STEP_ORDER),
            ["SPAWN", "DYING_LATCH", "DEATH_TASK"],
        )
        self.assertIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.runtimeres_death_sweep_count, 1)

    def test_the_dispatched_bytes_are_the_encoders_bytes(self):
        """The dispatcher forwards; it does not compose a sweep of its own."""
        state = self._state("rrd02")
        self.assertEqual(state.dispatch(self._trigger()), self._expected())

    def test_every_dispatched_frame_is_a_0x6e9d_actor_entry_frame(self):
        state = self._state("rrd03")
        for _label, pc, frame, _delay in state.dispatch(self._trigger()):
            read = rdh.decode_runtimeres_actor_entry_frame(pc)
            self.assertEqual(
                pc[0:3],
                self.legacy.u16tag(0x12, rdh.RUNTIME_PROTOCOL_RES_ID),
            )
            self.assertEqual(
                pc[rdh.INHERITED_CHANGE_MASK_OFFSET],
                rdh.INHERITED_CHANGE_MASK_ABSENT,
            )
            self.assertTrue(
                read["derived_mask"] & rdh.DERIVED_CHANGE_MASK_ACTOR_ENTRIES
            )
            self.assertEqual(frame, self.legacy.frame_pc(pc))

    def test_all_three_frames_name_the_one_pinned_identity(self):
        state = self._state("rrd04")
        identities = {
            rdh.decode_runtimeres_actor_entry_frame(pc)["identity"]
            for _l, pc, _f, _d in state.dispatch(self._trigger())
        }
        self.assertEqual(
            identities, {rdh.RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY},
        )

    def test_the_polarity_is_on_the_wire_in_the_proven_order(self):
        """Frame 2 is vt+0x40 (timer > 0); frame 3 is vt+0x3C (timer <= 0)."""
        state = self._state("rrd05")
        rows = rdh.validate_runtimeres_death_sweep(
            state.dispatch(self._trigger()), self.scenario,
        )
        self.assertEqual(rows[0]["hp_current_bit_0x0004"],
                         rdh.RUNTIMERES_DEATH_HP_ALIVE)
        self.assertIsNone(rows[0]["death_timer_bit_0x0080"])
        self.assertTrue(rows[1]["dying_latch_predicate_vt40"])
        self.assertFalse(rows[1]["death_task_predicate_vt3c"])
        self.assertEqual(rows[1]["death_timer_bit_0x0080"],
                         rdh.DYING_LATCH_TIMER_SECONDS)
        self.assertTrue(rows[2]["death_task_predicate_vt3c"])
        self.assertFalse(rows[2]["dying_latch_predicate_vt40"])
        self.assertEqual(rows[2]["death_timer_bit_0x0080"],
                         rdh.DEATH_TASK_TIMER_SECONDS)

    def test_every_dispatched_frame_reproduces_its_pins(self):
        state = self._state("rrd06")
        for index, (_l, pc, frame, _d) in enumerate(
            state.dispatch(self._trigger())
        ):
            step = rdh.RUNTIMERES_DEATH_STEP_ORDER[index]
            pin = rdh.RUNTIMERES_DEATH_PINS[step]
            self.assertEqual(len(pc), pin["pc_size"], step)
            self.assertEqual(len(frame), pin["frame_size"], step)
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(), pin["pc_sha256"], step,
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                pin["frame_sha256"], step,
            )
            self.assertEqual(
                self.pinned["probe"]["per_step"][step]["pc_sha256"],
                pin["pc_sha256"], step,
            )

    def test_the_spacing_matches_the_scenario(self):
        state = self._state("rrd07")
        delays = [d for _l, _p, _f, d in state.dispatch(self._trigger())]
        self.assertEqual(delays[0], rdh.RUNTIMERES_DEATH_FIRST_DELAY_SECONDS)
        self.assertTrue(
            all(d == self.scenario.spacing_seconds for d in delays[1:])
        )
        self.assertEqual(
            self.scenario.spacing_seconds, rdh.RUNTIMERES_DEATH_SPACING_SECONDS,
        )

    def test_the_request_payload_is_a_trigger_not_an_input(self):
        # Two fresh sessions, because the sweep is one-shot: the only thing
        # that differs between them is the request payload, and it must not
        # change one byte of the answer.
        first = self._state("rrd08").dispatch(self._trigger("probe1"))
        second = self._state("rrd09").dispatch(self._trigger("probe2"))
        self.assertEqual(
            [pc for _l, pc, _f, _d in first],
            [pc for _l, pc, _f, _d in second],
        )

    def test_the_sweep_writes_nothing_to_the_database(self):
        state = self._state("rrd10")
        before = self._db_digest()
        state.dispatch(self._trigger())
        self.assertEqual(self._db_digest(), before)

    def test_the_sweep_takes_no_socket_action(self):
        state = self._state("rrd11")
        self.assertTrue(
            all(len(action) == 4 for action in state.dispatch(self._trigger()))
        )

    # ----- traps -----------------------------------------------------------

    def test_trap_the_dispatcher_cannot_fire_when_the_lane_is_not_enabled(self):
        """TRAP 1 -- the failure mode: a branch that forgets its scenario gate.

        Two independent locks are checked, because one of them is the kind a
        careless edit removes.  (a) with no scenario the trigger keeps its
        frozen baseline answer and no HYP-PF-023 action, no sweep event and no
        byte of the sweep appears.  (b) even if a future edit reached the
        dispatch method WITHOUT the gate, it still cannot emit anything: the
        lethal unlock and the scenario profile are closed over as ``None``, so
        the composer raises instead of putting a death frame on the wire.
        """
        state = self._state("rrd12", sweep=False)
        expected_pcs = {pc for _l, pc, _f, _d in self._expected()}
        actions = state.dispatch(self._trigger())
        self.assertFalse([
            label for label, _p, _f, _d in actions
            if label.startswith(rdh.RUNTIMERES_DEATH_ACTION_LABEL_PREFIX)
        ])
        self.assertFalse(
            {pc for _l, pc, _f, _d in actions} & expected_pcs
        )
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.runtimeres_death_sweep_count, 0)
        with self.assertRaises(ValueError):
            state._dispatch_runtimeres_death_hypothesis(self._trigger())
        self.assertEqual(state.runtimeres_death_sweep_count, 0)

    def test_trap_a_kill_before_the_spawn_is_rejected(self):
        """TRAP 2 -- the failure mode: the frames arriving in the wrong order.

        An actor cannot be born dead.  An identity the client does not know
        takes 0x446990 -> vtable +0x10, which never touches the dead-state sync
        0x4437C0, so a sweep whose FIRST frame is a kill produces a stuck live
        NPC and nothing else.  Take the frames this dispatcher really emitted,
        put the kill first while leaving the labels in the pinned order, and
        require the validator to refuse it by that name.  The unswapped list
        from the same dispatch is asserted to pass, so the trap cannot be
        passing because the validator refuses everything.
        """
        state = self._state("rrd13")
        actions = state.dispatch(self._trigger())
        self.assertEqual(
            len(rdh.validate_runtimeres_death_sweep(actions, self.scenario)), 3,
        )
        labels = list(rdh.RUNTIMERES_DEATH_ACTION_LABELS)
        swapped = [
            (labels[0], actions[1][1], actions[1][2], actions[0][3]),
            (labels[1], actions[0][1], actions[0][2], actions[1][3]),
            actions[2],
        ]
        with self.assertRaises(
            rdh.RuntimeResDeathValidationError
        ) as raised:
            rdh.validate_runtimeres_death_sweep(swapped, self.scenario)
        self.assertIn("an actor cannot be born dead", str(raised.exception))

    def test_trap_the_sweep_is_one_shot(self):
        """TRAP 3 -- the failure mode: a second sweep resurrecting the probe.

        The second SPAWN would name an identity the client now knows, so it
        would take the vtable +0x20 UPDATE path with HP back at 100 -- undoing
        the kill instead of repeating it.  A repeat trigger must therefore emit
        nothing at all, and must say so.
        """
        state = self._state("rrd14")
        self.assertEqual(len(state.dispatch(self._trigger())), 3)
        before = self._db_digest()
        self.assertEqual(state.dispatch(self._trigger()), [])
        self.assertEqual(state.dispatch(self._trigger("probe2")), [])
        self.assertEqual(state.runtimeres_death_sweep_count, 1)
        self.assertEqual(state.events.count(SWEEP_EVENT), 1)
        self.assertEqual(state.events.count(REPEAT_EVENT), 2)
        self.assertEqual(self._db_digest(), before)

    # ----- fail closed -----------------------------------------------------

    def _refused(self, state, parsed, event_fragment):
        before = self._db_digest()
        self.assertEqual(state.dispatch(parsed), [])
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertTrue(
            any(event_fragment in event for event in state.events),
            state.events,
        )
        self.assertEqual(state.runtimeres_death_sweep_count, 0)
        self.assertEqual(self._db_digest(), before)

    def test_wrong_length_fails_closed(self):
        state = self._state("rrd15")
        payload = bytes(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])[-33:]
        self._refused(
            state, self.legacy.parse_outer(self._trigger_pc(payload)),
            EVENT_PREFIX,
        )

    def test_wrong_text_bytes_fail_closed(self):
        state = self._state("rrd16")
        pc = bytearray(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        pc[-1] ^= 0xFF
        self._refused(
            state, self.legacy.parse_outer(bytes(pc)), EVENT_PREFIX,
        )

    def test_not_yet_runtime_ready_fails_closed(self):
        state = self._state("rrd17", ready=False)
        self._refused(
            state, self._trigger(),
            EVENT_PREFIX + "wrong_sequence_no_reply",
        )

    def test_no_selected_character_fails_closed(self):
        state = self._state("rrd18", select=False)
        self._refused(
            state, self._trigger(), EVENT_PREFIX + "no_selected_no_reply",
        )

    def test_no_refusal_path_ever_emits_a_lethal_frame(self):
        for login, kwargs in (
            ("rrd19", {"ready": False}), ("rrd20", {"select": False}),
        ):
            state = self._state(login, **kwargs)
            self.assertEqual(state.dispatch(self._trigger()), [])
            self.assertEqual(state.runtimeres_death_sweep_count, 0)

    # ----- containment -----------------------------------------------------

    def test_the_lane_is_mutually_exclusive_with_every_other_mode(self):
        hp_death = sp.load_hp_death_hypothesis_scenario(HP_DEATH_SCENARIO_PATH)
        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                runtimeres_death_hypothesis_scenario=self.scenario,
                hp_death_hypothesis_scenario=hp_death,
            )

    def test_a_scenario_object_outside_the_allowlist_is_refused(self):
        for candidate in (
            object(),
            rdh.RUNTIMERES_DEATH_SCENARIO_ID,
            rdh.RuntimeResDeathHypothesisScenario(
                rdh.RUNTIMERES_DEATH_SCENARIO_ID,
                rdh.RUNTIMERES_DEATH_HYPOTHESIS_ID,
                ("DEATH_TASK", "DYING_LATCH", "SPAWN"),
                rdh.RUNTIMERES_DEATH_SPACING_SECONDS,
                rdh.RUNTIMERES_DEATH_FIRST_DELAY_SECONDS,
                rdh.RUNTIMERES_DEATH_ACTION_LABEL_PREFIX,
            ),
        ):
            with self.assertRaises(ValueError):
                make_state_class(
                    self.legacy, self.lifecycle, self.projector,
                    runtimeres_death_hypothesis_scenario=candidate,
                )

    def test_the_runtime_lane_sits_behind_the_scenario_gate(self):
        source = (
            ROOT / "src" / "pirateforce_foundation" / "runtime.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "if runtimeres_death_hypothesis_scenario is not None:", source,
        )
        # Exactly one call site, inside the branch: the dispatcher composes
        # nowhere else and nothing else composes for it.
        self.assertEqual(source.count("build_runtimeres_death_sweep("), 1)
        self.assertEqual(
            source.count("def _dispatch_runtimeres_death_hypothesis("), 1,
        )
        # Round 86: the id IS in docs/HYPOTHESIS_LEDGER.json now, and
        # tools/verify_hypothesis_ledger.py binds the entry and the annotation
        # both ways -- and rejects a DUPLICATE annotation for the same file.
        # So there must be exactly one, here, on the dispatch method.
        self.assertEqual(source.count("PF-HYPOTHESIS-LEDGER: HYP-PF-023 active"), 1)

    def test_the_app_flag_is_live_and_still_demands_an_existing_database(self):
        source = (
            ROOT / "src" / "pirateforce_foundation" / "app.py"
        ).read_text(encoding="utf-8")
        self.assertIn("--runtimeres-death-hypothesis-scenario", source)
        self.assertIn(
            "'--runtimeres-death-hypothesis-scenario requires an explicit '",
            source,
        )
        self.assertIn(
            "runtimeres_death_hypothesis_scenario=runtimeres_death_hypothesis",
            source,
        )
        # The refuse-to-boot stub RUNTIMERES-ENCODER-001 left behind is gone,
        # because there is now something behind the flag.
        self.assertNotIn("no frame would ever be dispatched", source)
        # Exactly one, for the same reason as the runtime.py assertion above.
        self.assertEqual(source.count("PF-HYPOTHESIS-LEDGER: HYP-PF-023 active"), 1)


class HeadlessReplayToolTests(unittest.TestCase):
    def test_the_replay_tool_runs_clean_against_the_real_dispatcher(self):
        spec = importlib.util.spec_from_file_location(
            "pf_runtimeres_death_headless_replay", REPLAY_TOOL,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        saved = sys.argv[:]
        try:
            sys.argv = [str(REPLAY_TOOL)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(), 0)
        finally:
            sys.argv = saved

    def _run_replay(self, argv):
        spec = importlib.util.spec_from_file_location(
            "pf_runtimeres_death_headless_replay", REPLAY_TOOL,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        saved = sys.argv[:]
        try:
            sys.argv = [str(REPLAY_TOOL)] + argv
            with contextlib.redirect_stdout(io.StringIO()):
                return module.main()
        finally:
            sys.argv = saved

    def test_the_replay_tool_runs_clean_for_the_two_frame_profile(self):
        """RUNTIMERES-LATCHONLY-001.

        Without this, the two-frame profile's replay guards exist and are run
        by nothing: the gate job calls the tool with no arguments, which is the
        three-frame profile, so the whole latch-only section would have been
        dead code that only a human remembering to pass a flag ever executed.
        """
        self.assertEqual(self._run_replay(["--profile", "dying_latch_only"]), 0)

    def test_the_replay_tool_refuses_a_profile_it_does_not_ship(self):
        self.assertEqual(self._run_replay(["--profile", "no_such_profile"]), 2)

    def test_the_replay_tool_needs_no_third_party_package(self):
        source = REPLAY_TOOL.read_text(encoding="utf-8")
        for banned in ("capstone", "pefile", "numpy", "yaml", "requests"):
            self.assertNotIn("import " + banned, source)

    def test_the_replay_tool_reads_the_frames_with_its_own_walker(self):
        """The tool must not lean on the encoder's decoder to check the encoder."""
        source = REPLAY_TOOL.read_text(encoding="utf-8")
        self.assertNotIn("decode_runtimeres_actor_entry_frame(", source)
        self.assertIn("def walk_actor_entry_frame(", source)


if __name__ == "__main__":
    unittest.main()
