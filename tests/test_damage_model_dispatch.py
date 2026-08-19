"""DAMAGE-DISPATCH-001 (HYP-PF-024) -- the hit sweep on the real dispatcher.

``tests/test_damage_model_hypothesis.py`` proves the encoder offline.  This file
drives the REAL ``make_state_class`` dispatch path behind the opt-in scenario
``scenarios/damage_model_hypothesis_hit_sweep.json`` and proves the wire layer
end to end, headless -- no server process, no socket, no client:

  * one accepted chat-input frame (the exact 34-byte ascii12 shape the
    HYP-PF-014 lane already classifies, reused because it is the only client
    action an attended tester can trigger on demand) produces exactly FOUR
    actions, in the scenario's order, at delays 0.0 / 6.0 / 6.0 / 6.0;
  * the bytes the dispatcher emits are **identical** to the bytes
    ``build_damage_model_sweep`` composes for the same session actor -- label,
    PC, frame and delay, compared with ``==`` on the bytes themselves.  The
    dispatcher is a forwarder, and if it ever becomes a second composer these
    tests go red;
  * every frame is ``GSCN_RunTimeProtocolRes`` 0x6E9D version 4 with BASE change
    mask 2 (the VitalData collection at ``+0x18``) and DERIVED change mask 0,
    carrying one ``CHitResult`` 0x16F7 version 0 whose single 37-byte hit entry
    names the SESSION's selected character as both performer and target;
  * the four steps carry the pinned pairs -63/0x0001, -379/0x0001, 0/0x0000 and
    -63/0x0009, with the damage read SIGNED off the ``u32`` tag at ``+0x08``;
  * fail-closed and containment: wrong envelope, wrong length, wrong prefix,
    wrong text bytes, no selected character and not-yet-runtime-ready all give
    ``[]`` with an exactly-named no-reply event; the sweep is ONE-SHOT; with no
    scenario nothing at all is composable and the dispatch method itself raises;
    the lane is keyed on the chat-input vital id and answers no other id; it is
    mutually exclusive with every other scenario mode; and no file in the
    throwaway database directory moves one byte.

DISCIPLINE.  Every database in this file is a fresh ``tempfile`` one that is
deleted on exit.  The repository's canonical database is never opened -- it is
only ``stat``-ed, once at import and once at the end, so that a regression that
reached for it would be reported rather than silently tolerated.  That is the
round-41 lesson, kept as a measurement instead of a promise.

NOT proven here, and this is the load-bearing limit: whether a real client draws
anything at all when it receives these bytes.  **No client has ever been shown
one byte of this profile.**  That is the attended lane, not run.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PROBE_REQUEST_PCS,
    CHAT_INPUT_VITAL_ID,
    load_chat_input_hypothesis_scenario,
)
from pirateforce_foundation.channel_message_hypothesis import (  # noqa: E402
    load_channel_message_hypothesis_scenario,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation import damage_model_hypothesis as dmh  # noqa: E402
from pirateforce_foundation import runtimeres_death_hypothesis as rdh  # noqa: E402
from pirateforce_foundation import stats_progression_hypothesis as sp  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "damage_model_hypothesis_hit_sweep.json"
REPLAY_TOOL = ROOT / "tools" / "pf_damage_model_headless_replay.py"
RUNTIME_SOURCE_PATH = ROOT / "src" / "pirateforce_foundation" / "runtime.py"
APP_SOURCE_PATH = ROOT / "src" / "pirateforce_foundation" / "app.py"

# Built by concatenation on purpose: the canonical database's file name must
# never appear as a contiguous literal in this file or in the replay tool, so
# that the "no path points at it" test below can search for it honestly.
CANONICAL_DB = ROOT / "state" / ("pirateforce" + ".sqlite3")

SWEEP_EVENT = "damage_model_hypothesis_hit_sweep_sent"
REPEAT_EVENT = "damage_model_hypothesis_already_sent_no_reply"
NO_SELECTED_EVENT = "damage_model_hypothesis_no_selected_no_reply"
WRONG_SEQUENCE_EVENT = "damage_model_hypothesis_wrong_sequence_no_reply"
EVENT_PREFIX = "damage_model_hypothesis_"

EXPECTED_STEP_ORDER = ("HIT_WEAK", "HIT_STRONG", "MISS", "HIT_REACTION")
EXPECTED_DAMAGE = (-63, -379, 0, -63)
EXPECTED_FLAGS = (0x0001, 0x0001, 0x0000, 0x0009)
EXPECTED_DELAYS = (0.0, 6.0, 6.0, 6.0)
EXPECTED_PC_SIZE = 84
EXPECTED_FRAME_SIZE = 95


def _canonical_stat():
    """Size and mtime of the canonical database, WITHOUT opening it."""
    if not CANONICAL_DB.exists():
        return None
    info = CANONICAL_DB.stat()
    return (info.st_size, info.st_mtime_ns)


_CANONICAL_AT_IMPORT = _canonical_stat()


def tearDownModule():
    """Round 41's lesson, enforced: pytest may not move the canonical file."""
    if _canonical_stat() != _CANONICAL_AT_IMPORT:
        raise AssertionError(
            "this test module changed the canonical database's size or mtime; "
            "every database in this file must be a tempfile one"
        )


class DamageModelDispatchTests(unittest.TestCase):
    # The event the booted profile is expected to name.  The npc subclass
    # overrides this, which is what lets every inherited lane-level test run
    # under BOTH profiles without weakening its assertion.
    SWEEP_EVENT_NAME = SWEEP_EVENT

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp.name)
        self.db_path = self.tmp_dir / "state.sqlite3"
        # Round 41, enforced on every single test: this file's database lives
        # under the system temporary directory and nowhere near the repository.
        self.assertIn(
            Path(tempfile.gettempdir()).resolve(),
            self.db_path.resolve().parents,
        )
        self.assertNotIn(ROOT.resolve(), self.db_path.resolve().parents)
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
        self.scenario = dmh.load_damage_model_hypothesis_scenario(
            SCENARIO_PATH
        )
        self.unlock = dmh.damage_model_wire_unlock(self.scenario)
        self.pinned = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ---------------------------------------------------------

    def _state_type(self, *, sweep=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            damage_model_hypothesis_scenario=(
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

    def _payload(self, probe="probe1"):
        return self._trigger(probe).nested_payload

    def _trigger_pc(self, payload, *, vital_id=CHAT_INPUT_VITAL_ID,
                    outer_version=0, nested_version=0):
        legacy = self.legacy
        return bytes(
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, outer_version)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, vital_id)
            + legacy.u8tag(0x0B, nested_version)
            + payload
        )

    def _session_actor(self, state):
        return dmh.resolve_actor(self.legacy, state.foundation.selected)

    def _expected(self, state):
        """The encoder's composition, built without the dispatcher."""
        return dmh.build_damage_model_sweep(
            self.legacy, self._session_actor(state), self.unlock,
            self.scenario,
        )

    def _db_digest(self):
        """The whole database directory, because the store runs in WAL mode.

        Hashing only the main file would be a weak claim: a committed write can
        land in the ``-wal`` sidecar and leave the main file untouched.
        """
        rows = []
        for name in sorted(os.listdir(self.tmp_dir)):
            path = self.tmp_dir / name
            if path.is_file():
                data = path.read_bytes()
                rows.append((name, len(data), hashlib.sha256(data).hexdigest()))
        return rows

    def _entry(self, pc):
        """The one hit entry of one composed PC, via the module's decoder.

        The replay tool deliberately reads these frames with its own walker;
        this file is allowed the module's decoder because the tool is the
        independent second reader and running both is the point.
        """
        decoded = dmh.decode_chit_result_frame(pc)
        return decoded, decoded["vitals"][0], decoded["vitals"][0]["entries"][0]

    # ----- happy path ------------------------------------------------------

    def test_one_request_sweeps_the_four_steps_in_the_pinned_order(self):
        state = self._state("dmd01")
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), len(EXPECTED_STEP_ORDER))
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            list(dmh.DAMAGE_MODEL_ACTION_LABELS),
        )
        self.assertEqual(
            list(dmh.DAMAGE_MODEL_STEP_ORDER), list(EXPECTED_STEP_ORDER),
        )
        self.assertIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.events.count(SWEEP_EVENT), 1)
        self.assertEqual(state.damage_model_sweep_count, 1)

    def test_the_dispatched_bytes_are_the_encoders_bytes(self):
        """The dispatcher forwards; it does not compose a sweep of its own."""
        state = self._state("dmd02")
        expected = self._expected(state)
        self.assertEqual(state.dispatch(self._trigger()), expected)

    def test_every_dispatched_frame_is_a_chit_result_frame(self):
        state = self._state("dmd03")
        for _label, pc, frame, _delay in state.dispatch(self._trigger()):
            decoded, body, _entry = self._entry(pc)
            self.assertEqual(decoded["envelope_id"], 0x6E9D)
            self.assertEqual(decoded["envelope_version"], 4)
            self.assertEqual(decoded["base_change_mask"], 2)
            self.assertEqual(decoded["derived_change_mask"], 0)
            self.assertEqual(decoded["vital_count"], 1)
            self.assertEqual(body["vital_id"], 0x16F7)
            self.assertEqual(body["vital_version"], 0)
            self.assertEqual(body["header_wire_size"], 22)
            self.assertEqual(body["entry_count"], 1)
            self.assertEqual(body["entries"][0]["wire_size"], 37)
            self.assertEqual(frame, self.legacy.frame_pc(pc))

    def test_the_four_steps_carry_the_pinned_damage_and_flag_pairs(self):
        state = self._state("dmd04")
        actions = state.dispatch(self._trigger())
        damages, flags = [], []
        for _label, pc, _frame, _delay in actions:
            _decoded, _body, entry = self._entry(pc)
            damages.append(entry["damage_wire"])
            flags.append(entry["flags"])
        self.assertEqual(damages, list(EXPECTED_DAMAGE))
        self.assertEqual(flags, list(EXPECTED_FLAGS))

    def test_the_damage_field_is_the_signed_reading_of_the_u32_tag(self):
        """Unsigned would read 4294967233, not -63: the sign is the lane."""
        state = self._state("dmd05")
        for index, (_l, pc, _f, _d) in enumerate(
            state.dispatch(self._trigger())
        ):
            _decoded, _body, entry = self._entry(pc)
            raw = struct.pack("<i", entry["damage_wire"])
            self.assertEqual(struct.unpack("<i", raw)[0], EXPECTED_DAMAGE[index])
            self.assertEqual(
                struct.unpack("<I", raw)[0],
                EXPECTED_DAMAGE[index] & 0xFFFFFFFF,
            )
            self.assertLessEqual(entry["damage_wire"], 0)

    def test_performer_and_target_are_the_sessions_selected_character(self):
        state = self._state("dmd06")
        selected = state.foundation.selected
        identity = (
            ((selected.identity_hi & 0xFFFFFFFF) << 32)
            | (selected.identity_lo & 0xFFFFFFFF)
        )
        seen = set()
        for _l, pc, _f, _d in state.dispatch(self._trigger()):
            _decoded, body, entry = self._entry(pc)
            self.assertEqual(body["performer_identity"], identity)
            self.assertEqual(entry["target_identity"], identity)
            seen.add(entry["target_identity"])
        self.assertEqual(seen, {identity})

    def test_a_sweep_for_another_identity_is_not_the_dispatched_sweep(self):
        """Makes "the frames name the session" falsifiable, not decorative."""
        state = self._state("dmd07")
        actions = state.dispatch(self._trigger())
        other = dmh.DamageModelActor(
            (state.foundation.selected.identity_lo ^ 0x00ABCDEF) & 0xFFFFFFFF,
            0,
            float(self.legacy.V135_PLAYER_X),
            float(self.legacy.V135_PLAYER_Y),
            float(self.legacy.V135_PLAYER_Z),
        )
        other_sweep = dmh.build_damage_model_sweep(
            self.legacy, other, self.unlock, self.scenario,
        )
        self.assertNotEqual(
            [pc for _l, pc, _f, _d in other_sweep],
            [pc for _l, pc, _f, _d in actions],
        )
        # Same widths though: only the identity moved.
        self.assertEqual(
            [len(pc) for _l, pc, _f, _d in other_sweep],
            [len(pc) for _l, pc, _f, _d in actions],
        )

    def test_every_dispatched_frame_reproduces_its_module_and_scenario_pins(self):
        state = self._state("dmd08")
        for index, (_l, pc, frame, _d) in enumerate(
            state.dispatch(self._trigger())
        ):
            step = EXPECTED_STEP_ORDER[index]
            pin = dmh.DAMAGE_MODEL_PINS[step]
            scenario_pin = self.pinned["target"]["per_step"][step]
            pc_digest = hashlib.sha256(pc).hexdigest().upper()
            frame_digest = hashlib.sha256(frame).hexdigest().upper()
            self.assertEqual(len(pc), EXPECTED_PC_SIZE, step)
            self.assertEqual(len(frame), EXPECTED_FRAME_SIZE, step)
            self.assertEqual(pin["pc_size"], EXPECTED_PC_SIZE, step)
            self.assertEqual(pin["frame_size"], EXPECTED_FRAME_SIZE, step)
            self.assertEqual(pc_digest, pin["pc_sha256"], step)
            self.assertEqual(frame_digest, pin["frame_sha256"], step)
            # The module pin and the scenario file pin must be the SAME pin.
            self.assertEqual(scenario_pin["pc_sha256"], pin["pc_sha256"], step)
            self.assertEqual(
                scenario_pin["frame_sha256"], pin["frame_sha256"], step,
            )
            self.assertEqual(
                scenario_pin["damage_wire"], EXPECTED_DAMAGE[index], step,
            )
            self.assertEqual(scenario_pin["flags"], EXPECTED_FLAGS[index], step)

    def test_the_spacing_matches_the_scenario(self):
        state = self._state("dmd09")
        delays = [d for _l, _p, _f, d in state.dispatch(self._trigger())]
        self.assertEqual(delays, list(EXPECTED_DELAYS))
        self.assertEqual(
            self.scenario.first_delay_seconds,
            dmh.DAMAGE_MODEL_FIRST_DELAY_SECONDS,
        )
        self.assertEqual(
            self.scenario.spacing_seconds, dmh.DAMAGE_MODEL_SPACING_SECONDS,
        )

    def test_the_request_payload_is_a_trigger_not_an_input(self):
        """Nothing in the request reaches the answer.

        The sweep is one-shot, so the two probes need two sessions -- and two
        sessions of the SAME store would hold two different characters, whose
        identities the frames legitimately carry.  The second session therefore
        gets its own throwaway store, so the only thing that differs between the
        two runs is the 34 payload bytes.  If any of them were read, the answers
        would diverge.
        """
        first = self._state("dmd10").dispatch(self._trigger("probe1"))
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "state.sqlite3", ROOT / "migrations")
            store.migrate()
            lifecycle = CharacterLifecycle(
                store,
                Position(
                    1, 0, self.legacy.V135_PLAYER_X,
                    self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
                ),
                self.legacy.extract_avatar_attr_wire_from_actor,
            )
            state = make_state_class(
                self.legacy, lifecycle, self.projector,
                damage_model_hypothesis_scenario=self.scenario,
            )("dmd11")
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_client_login_pc()
            ))
            state.dispatch(self.legacy.parse_outer(
                self.legacy._V25_REAL_CREATE_PC
            ))
            characters = store.list_characters(state.foundation.account_id)
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(characters[-1].selector)
            ))
            state.runtime_ack_sent = True
            second = state.dispatch(self._trigger("probe2"))
        self.assertEqual(
            [pc for _l, pc, _f, _d in first],
            [pc for _l, pc, _f, _d in second],
        )
        # And neither probe's payload text appears anywhere in the answer.
        for probe in ("probe1", "probe2"):
            payload = self._payload(probe)
            for _l, pc, _f, _d in first:
                self.assertNotIn(payload, pc)

    def test_the_sweep_writes_nothing_to_the_database(self):
        state = self._state("dmd12")
        before = self._db_digest()
        state.dispatch(self._trigger())
        self.assertEqual(self._db_digest(), before)

    def test_the_sweep_takes_no_socket_action(self):
        state = self._state("dmd13")
        self.assertTrue(
            all(len(action) == 4 for action in state.dispatch(self._trigger()))
        )

    def test_the_sweep_carries_exactly_one_miss_control_frame(self):
        state = self._state("dmd14")
        misses = []
        for index, (_l, pc, _f, _d) in enumerate(
            state.dispatch(self._trigger())
        ):
            _decoded, _body, entry = self._entry(pc)
            if entry["damage_wire"] == 0 and entry["flags"] == 0:
                misses.append(EXPECTED_STEP_ORDER[index])
        self.assertEqual(misses, list(dmh.DAMAGE_MODEL_MISS_STEP_LABELS))

    # ----- the gate --------------------------------------------------------

    def test_the_runtime_branch_is_gated_on_the_scenario_and_the_vital_id(self):
        """The branch must read BOTH conditions, and there must be one of it."""
        source = RUNTIME_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "            if (\n"
            "                damage_model_hypothesis_scenario is not None\n"
            "                and nested_id == CHAT_INPUT_VITAL_ID\n"
            "            ):\n",
            source,
        )
        # The unlock is derived once, behind the same gate, at construction.
        self.assertIn(
            "    if damage_model_hypothesis_scenario is not None:\n", source,
        )
        # Exactly one call site, inside the branch: the dispatcher composes
        # nowhere else and nothing else composes for it.
        self.assertEqual(source.count("build_damage_model_sweep("), 1)
        self.assertEqual(
            source.count("def _dispatch_damage_model_hypothesis("), 1,
        )
        self.assertEqual(
            source.count("self._dispatch_damage_model_hypothesis("), 1,
        )
        # The ledger annotation binds this file and the ledger entry both ways,
        # and verify_hypothesis_ledger.py rejects a duplicate for one file.
        self.assertEqual(
            source.count("PF-HYPOTHESIS-LEDGER: HYP-PF-024 active"), 1,
        )

    def test_the_branch_answers_no_vital_id_other_than_the_chat_input_one(self):
        """A different nested id keeps its frozen baseline answer, untouched."""
        state = self._state("dmd15")
        actions = state.dispatch(self.legacy.parse_outer(
            self._trigger_pc(self._payload(), vital_id=0xBEEF)
        ))
        self.assertFalse([
            label for label, _p, _f, _d in actions
            if label.startswith(dmh.DAMAGE_MODEL_ACTION_LABEL_PREFIX)
        ])
        self.assertFalse(
            [event for event in state.events if event.startswith(EVENT_PREFIX)]
        )
        self.assertEqual(state.damage_model_sweep_count, 0)

    def test_the_app_flag_is_live_and_still_demands_an_existing_database(self):
        source = APP_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertIn("--damage-model-hypothesis-scenario", source)
        self.assertIn(
            "'--damage-model-hypothesis-scenario requires an explicit '",
            source,
        )
        self.assertIn(
            "damage_model_hypothesis_scenario=damage_model_hypothesis", source,
        )
        self.assertEqual(
            source.count("PF-HYPOTHESIS-LEDGER: HYP-PF-024 active"), 1,
        )

    # ----- mutual exclusion ------------------------------------------------

    def test_the_lane_is_mutually_exclusive_with_every_other_mode(self):
        """Five pairs, because all of them key on the same vital id or file."""
        pairs = {
            "hp_death_hypothesis_scenario": sp.load_hp_death_hypothesis_scenario(
                ROOT / "scenarios" / "hp_death_hypothesis_death_sweep.json"
            ),
            "runtimeres_death_hypothesis_scenario": (
                rdh.load_runtimeres_death_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "runtimeres_death_hypothesis_spawn_then_kill.json"
                )
            ),
            "chat_input_hypothesis_scenario": (
                load_chat_input_hypothesis_scenario(
                    ROOT / "scenarios" / "chat_input_hypothesis_echo.json"
                )
            ),
            "channel_message_hypothesis_scenario": (
                load_channel_message_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "channel_message_hypothesis_channel_sweep.json"
                )
            ),
            "stats_progression_hypothesis_scenario": (
                sp.load_stats_progression_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "stats_progression_hypothesis_xp_sweep.json"
                )
            ),
        }
        self.assertGreaterEqual(len(pairs), 3)
        for kwarg, other in pairs.items():
            with self.subTest(other=kwarg):
                with self.assertRaisesRegex(ValueError, "mutually exclusive"):
                    make_state_class(
                        self.legacy, self.lifecycle, self.projector,
                        damage_model_hypothesis_scenario=self.scenario,
                        **{kwarg: other},
                    )

    def test_a_scenario_object_outside_the_allowlist_is_refused(self):
        for candidate in (
            object(),
            dmh.DAMAGE_MODEL_SCENARIO_ID,
            dmh.DamageModelHypothesisScenario(
                dmh.DAMAGE_MODEL_SCENARIO_ID,
                dmh.DAMAGE_MODEL_HYPOTHESIS_ID,
                ("MISS", "HIT_WEAK", "HIT_STRONG", "HIT_REACTION"),
                dmh.DAMAGE_MODEL_SPACING_SECONDS,
                dmh.DAMAGE_MODEL_FIRST_DELAY_SECONDS,
                dmh.DAMAGE_MODEL_ACTION_LABEL_PREFIX,
            ),
        ):
            with self.subTest(candidate=type(candidate).__name__):
                # NOTE, reported upstream rather than "fixed" here: this lane's
                # refusal is a DamageModelValidationError, which derives from
                # RuntimeError -- NOT from ValueError, which is what
                # make_state_class raises for its own mutual-exclusion check and
                # what the HYP-PF-023 lane's construction-time refusal raises.
                # A caller wrapping make_state_class in ``except ValueError``
                # would therefore not catch this one.  The test asserts the
                # behaviour that exists, and names the asymmetry.
                with self.assertRaises(dmh.DamageModelValidationError) as raised:
                    make_state_class(
                        self.legacy, self.lifecycle, self.projector,
                        damage_model_hypothesis_scenario=candidate,
                    )
                self.assertIn(
                    "scenario_object_exceeds_allowlist", str(raised.exception),
                )
                self.assertIsInstance(raised.exception, RuntimeError)
                self.assertNotIsInstance(raised.exception, ValueError)

    # ----- one-shot --------------------------------------------------------

    def test_the_sweep_is_one_shot(self):
        """A second sweep interleaved with the first is noise, not a repeat.

        The value of the two hit numbers is that a tester can predict them
        before they appear; a repeat trigger must therefore emit nothing at all,
        and must say so by name.
        """
        state = self._state("dmd16")
        self.assertEqual(len(state.dispatch(self._trigger())), 4)
        before = self._db_digest()
        self.assertEqual(state.dispatch(self._trigger()), [])
        self.assertEqual(state.dispatch(self._trigger("probe2")), [])
        self.assertEqual(state.damage_model_sweep_count, 1)
        self.assertEqual(state.events.count(self.SWEEP_EVENT_NAME), 1)
        self.assertEqual(state.events.count(REPEAT_EVENT), 2)
        self.assertEqual(self._db_digest(), before)

    # ----- fail closed -----------------------------------------------------

    def _refused(self, state, parsed, event_name):
        before = self._db_digest()
        self.assertEqual(state.dispatch(parsed), [])
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertNotIn(self.SWEEP_EVENT_NAME, state.events)
        self.assertEqual(state.events.count(event_name), 1, state.events)
        self.assertEqual(state.damage_model_sweep_count, 0)
        self.assertEqual(self._db_digest(), before)

    def test_no_selected_character_fails_closed(self):
        self._refused(
            self._state("dmd17", select=False), self._trigger(),
            NO_SELECTED_EVENT,
        )

    def test_not_yet_teleport_and_runtime_ack_fails_closed(self):
        self._refused(
            self._state("dmd18", ready=False), self._trigger(),
            WRONG_SEQUENCE_EVENT,
        )

    def test_wrong_length_fails_closed(self):
        self._refused(
            self._state("dmd19"),
            self.legacy.parse_outer(self._trigger_pc(self._payload()[:-1])),
            EVENT_PREFIX + "wrong_length_no_reply",
        )

    def test_wrong_prefix_fails_closed(self):
        payload = bytearray(self._payload())
        payload[0] ^= 0xFF
        self._refused(
            self._state("dmd20"),
            self.legacy.parse_outer(self._trigger_pc(bytes(payload))),
            EVENT_PREFIX + "wrong_prefix_no_reply",
        )

    def test_wrong_text_bytes_fail_closed(self):
        pc = bytearray(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        pc[-1] ^= 0xFF
        self._refused(
            self._state("dmd21"), self.legacy.parse_outer(bytes(pc)),
            EVENT_PREFIX + "wrong_text_no_reply",
        )

    def test_wrong_envelope_fails_closed(self):
        for index, kwargs in enumerate(
            ({"outer_version": 1}, {"nested_version": 1}),
        ):
            with self.subTest(**kwargs):
                self._refused(
                    self._state("dmd22_%d" % index),
                    self.legacy.parse_outer(
                        self._trigger_pc(self._payload(), **kwargs)
                    ),
                    EVENT_PREFIX + "wrong_envelope_no_reply",
                )

    def test_no_refusal_path_ever_emits_a_hit_frame(self):
        cases = (
            ("dmd23", {"select": False}, self._trigger()),
            ("dmd24", {"ready": False}, self._trigger()),
            ("dmd25", {}, self.legacy.parse_outer(
                self._trigger_pc(self._payload()[:-1])
            )),
            ("dmd26", {}, self.legacy.parse_outer(
                self._trigger_pc(self._payload(), outer_version=1)
            )),
        )
        for login, kwargs, parsed in cases:
            with self.subTest(login=login):
                state = self._state(login, **kwargs)
                self.assertEqual(state.dispatch(parsed), [])
                self.assertEqual(state.damage_model_sweep_count, 0)
                self.assertNotIn(SWEEP_EVENT, state.events)

    # ----- the flag off ----------------------------------------------------

    def test_trap_nothing_is_composable_when_the_lane_is_not_enabled(self):
        """TRAP -- the failure mode: a branch that forgets its scenario gate.

        Two independent locks, because one of them is the kind a careless edit
        removes.  (a) with no scenario the trigger keeps its frozen baseline
        answer: no HYP-PF-024 action, no damage-model event, none of the
        sweep's bytes.  (b) even if a future edit reached the dispatch method
        WITHOUT the gate, it still cannot emit anything: the unlock and the
        scenario profile are closed over as ``None``, so the composer raises
        instead of putting a hit frame on the wire.
        """
        state = self._state("dmd27", sweep=False)
        reference = self._state("dmd28")
        expected_pcs = {pc for _l, pc, _f, _d in self._expected(reference)}

        before = self._db_digest()
        actions = state.dispatch(self._trigger())
        self.assertFalse([
            label for label, _p, _f, _d in actions
            if label.startswith(dmh.DAMAGE_MODEL_ACTION_LABEL_PREFIX)
        ])
        self.assertFalse({pc for _l, pc, _f, _d in actions} & expected_pcs)
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertFalse(
            [event for event in state.events if event.startswith(EVENT_PREFIX)]
        )
        self.assertEqual(state.damage_model_sweep_count, 0)
        self.assertEqual(self._db_digest(), before)

        with self.assertRaises(dmh.DamageModelValidationError):
            state._dispatch_damage_model_hypothesis(self._trigger())
        self.assertEqual(state.damage_model_sweep_count, 0)


class HeadlessReplayToolTests(unittest.TestCase):
    """The tool is run as a real subprocess, which is the only way to prove
    that its exit code and its console encoding are what the Windows attended
    runner will actually see."""

    def _run(self, *args):
        completed = subprocess.run(
            [sys.executable, str(REPLAY_TOOL), *args],
            capture_output=True,
        )
        return completed

    def test_the_replay_tool_runs_clean_against_the_real_dispatcher(self):
        completed = self._run()
        self.assertEqual(
            completed.returncode, 0,
            completed.stdout.decode("utf-8", "replace")
            + completed.stderr.decode("utf-8", "replace"),
        )
        self.assertIn(b"RESULT: PASS", completed.stdout)
        self.assertIn(b"guards PASS", completed.stdout)

    def test_the_replay_tools_output_is_pure_ascii(self):
        """cp874 on a Windows console turns one non-ASCII byte into a crash."""
        for args in ((), ("--json",)):
            with self.subTest(args=args):
                completed = self._run(*args)
                self.assertEqual(completed.returncode, 0)
                self.assertTrue(
                    all(byte < 128 for byte in completed.stdout),
                    "the tool printed a non-ASCII byte",
                )
                completed.stdout.decode("ascii")
                completed.stderr.decode("ascii")

    def test_the_replay_tool_json_mode_reports_a_pass_verdict(self):
        completed = self._run("--json")
        self.assertEqual(completed.returncode, 0)
        verdict = json.loads(completed.stdout.decode("ascii"))
        self.assertEqual(verdict["result"], "PASS")
        self.assertEqual(verdict["failures"], [])
        self.assertGreater(verdict["guards_run"], 0)
        self.assertEqual(verdict["hypothesis_id"], "HYP-PF-024")
        self.assertEqual(len(verdict["frames"]), len(EXPECTED_STEP_ORDER))
        self.assertEqual(
            [row["damage_signed"] for row in verdict["frames"]],
            list(EXPECTED_DAMAGE),
        )
        self.assertEqual(
            [row["flags"] for row in verdict["frames"]], list(EXPECTED_FLAGS),
        )
        self.assertEqual(verdict["dispatch"]["socket_constructor_attempts"], [])

    def test_an_unknown_profile_is_refused_with_its_own_exit_code(self):
        completed = self._run("--profile", "not_a_profile")
        self.assertEqual(completed.returncode, 2)
        self.assertIn(b"unknown profile", completed.stdout)

    def test_the_named_profile_runs_the_same_guards(self):
        completed = self._run("--profile", "hit_sweep")
        self.assertEqual(completed.returncode, 0)
        self.assertIn(b"RESULT: PASS", completed.stdout)

    def test_the_replay_tool_reads_the_frames_with_its_own_walker(self):
        """The tool must not lean on the encoder's decoder to check the encoder."""
        source = REPLAY_TOOL.read_text(encoding="utf-8")
        # The name may appear in prose explaining WHY it is not used; what must
        # never appear is a call to it or an import of it.
        self.assertNotIn("decode_chit_result_frame(", source)
        self.assertNotIn("import decode_chit_result_frame", source)
        self.assertIn("def walk_chit_result_frame(", source)
        self.assertIn("walk_chit_result_frame(pc)", source)

    def test_the_replay_tool_needs_no_third_party_package(self):
        source = REPLAY_TOOL.read_text(encoding="utf-8")
        for banned in ("capstone", "pefile", "numpy", "yaml", "requests",
                       "pytest"):
            self.assertNotIn("import " + banned, source)

    def test_the_replay_tool_source_is_pure_ascii(self):
        self.assertTrue(
            all(byte < 128 for byte in REPLAY_TOOL.read_bytes()),
            "the tool's source carries a non-ASCII byte",
        )


class CanonicalDatabaseContainmentTests(unittest.TestCase):
    """Round 41: pytest once reached the canonical database.  Never again."""

    def test_no_path_in_this_suite_or_the_tool_names_the_canonical_database(self):
        tool_source = REPLAY_TOOL.read_text(encoding="utf-8")
        test_source = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn(CANONICAL_DB.name, tool_source)
        self.assertNotIn(CANONICAL_DB.name, test_source)
        # The tool builds exactly one store, and it builds it inside a
        # TemporaryDirectory block.
        self.assertEqual(tool_source.count("SQLiteStore("), 1)
        self.assertIn("with tempfile.TemporaryDirectory() as tmp:", tool_source)
        self.assertLess(
            tool_source.index("with tempfile.TemporaryDirectory() as tmp:"),
            tool_source.index("SQLiteStore("),
        )
        # Every store this test module builds is handed a path under a
        # TemporaryDirectory; the runtime check below proves it for real.
        self.assertIn("tempfile.TemporaryDirectory()", test_source)

    def test_every_database_this_suite_opens_lives_under_the_temp_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(db_path, ROOT / "migrations")
            store.migrate()
            resolved = Path(store.path).resolve()
            self.assertIn(
                Path(tempfile.gettempdir()).resolve(), resolved.parents,
            )
            self.assertNotIn((ROOT / "state").resolve(), resolved.parents)
            self.assertNotEqual(resolved, CANONICAL_DB.resolve())

    def test_the_canonical_database_has_not_moved_since_this_module_loaded(self):
        self.assertEqual(_canonical_stat(), _CANONICAL_AT_IMPORT)


class NpcTargetProfileDispatchTests(DamageModelDispatchTests):
    """DAMAGE-NPC-TARGET-001 (round 95): the SAME dispatcher, booted with the
    npc_target scenario file instead of hit_sweep.

    Subclassing DamageModelDispatchTests reruns every inherited test under the
    npc profile ON PURPOSE: the refusal ladder, the one-shot rule, the no-write
    guard and the containment tests are all claims about the LANE, so they have
    to hold under both profiles or the second profile is not the same lane.
    The inherited tests that pin hit_sweep-specific values are overridden below
    with their npc equivalents.
    """

    NPC_SCENARIO_PATH = (
        ROOT / "scenarios" / "damage_model_hypothesis_npc_sweep.json"
    )
    NPC_SWEEP_EVENT = "damage_model_hypothesis_npc_sweep_sent"
    NPC_EXPECTED_DELAYS = (0.0, 15.0, 15.0, 15.0)
    SWEEP_EVENT_NAME = NPC_SWEEP_EVENT

    def setUp(self):
        super().setUp()
        self.scenario = dmh.load_damage_model_hypothesis_scenario(
            self.NPC_SCENARIO_PATH
        )
        self.unlock = dmh.damage_model_wire_unlock(self.scenario)
        self.pinned = json.loads(
            self.NPC_SCENARIO_PATH.read_text(encoding="utf-8"))

    # -- overrides of hit_sweep-specific pins --------------------------------

    def test_one_request_sweeps_the_four_steps_in_the_pinned_order(self):
        state = self._state("npc_order")
        actions = state.dispatch(self._trigger())
        self.assertEqual(
            [row[0] for row in actions],
            list(dmh.DAMAGE_MODEL_NPC_ACTION_LABELS),
        )
        self.assertEqual([row[3] for row in actions],
                         list(self.NPC_EXPECTED_DELAYS))
        self.assertEqual(state.events.count(self.NPC_SWEEP_EVENT), 1)
        self.assertNotIn(SWEEP_EVENT, state.events)

    def test_every_dispatched_frame_reproduces_its_module_and_scenario_pins(
        self,
    ):
        state = self._state("npc_pins")
        actions = state.dispatch(self._trigger())
        pins = dmh.pins_for_profile(self.scenario)
        self.assertIs(pins, dmh.DAMAGE_MODEL_PINS_NPC)
        for index, step in enumerate(EXPECTED_STEP_ORDER):
            pin = pins[step]
            file_pin = self.pinned["target"]["per_step"][step]
            _label, pc, frame, _delay = actions[index]
            with self.subTest(step=step):
                self.assertEqual(len(pc), pin["pc_size"])
                self.assertEqual(len(frame), pin["frame_size"])
                self.assertEqual(
                    hashlib.sha256(pc).hexdigest().upper(), pin["pc_sha256"])
                self.assertEqual(
                    hashlib.sha256(frame).hexdigest().upper(),
                    pin["frame_sha256"])
                self.assertEqual(file_pin["pc_sha256"], pin["pc_sha256"])
                self.assertEqual(file_pin["frame_sha256"],
                                 pin["frame_sha256"])
                # and the npc pin is NOT the hit_sweep pin: the target qword
                # is on the wire, so the hashes must differ
                self.assertNotEqual(
                    pin["pc_sha256"],
                    dmh.DAMAGE_MODEL_PINS[step]["pc_sha256"])

    def test_performer_and_target_are_the_sessions_selected_character(self):
        """Overridden: under npc_target the two sides must DIFFER."""
        state = self._state("npc_identities")
        actions = state.dispatch(self._trigger())
        selected = state.foundation.selected
        session_identity = (
            ((selected.identity_hi & 0xFFFFFFFF) << 32)
            | (selected.identity_lo & 0xFFFFFFFF)
        )
        for index, step in enumerate(EXPECTED_STEP_ORDER):
            _decoded, body, entry = self._entry(actions[index][1])
            with self.subTest(step=step):
                self.assertEqual(body["performer_identity"], session_identity)
                self.assertEqual(entry["target_identity"],
                                 dmh.npc_target_identity())
                self.assertEqual(entry["target_identity"], 0x2001)
                self.assertNotEqual(body["performer_identity"],
                                    entry["target_identity"])

    def test_the_spacing_matches_the_scenario(self):
        state = self._state("npc_spacing")
        actions = state.dispatch(self._trigger())
        self.assertEqual([row[3] for row in actions],
                         list(self.NPC_EXPECTED_DELAYS))
        self.assertEqual(
            self.scenario.spacing_seconds,
            dmh.DAMAGE_MODEL_NPC_SPACING_SECONDS,
        )
        self.assertEqual(dmh.DAMAGE_MODEL_NPC_SPACING_SECONDS, 15.0)

    # -- npc-only additions ---------------------------------------------------

    def test_the_npc_target_constant_matches_the_death_lanes_probe(self):
        """0x2001 is COPIED from HYP-PF-023, not imported; drift is a red."""
        self.assertEqual(
            dmh.DAMAGE_NPC_TARGET_IDENTITY_LO,
            rdh.RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY,
        )
        self.assertEqual(dmh.DAMAGE_NPC_TARGET_IDENTITY_HI, 0)

    def test_the_hit_sweep_unlock_opens_no_npc_byte_through_the_dispatcher(
        self,
    ):
        hit_sweep_scenario = dmh.load_damage_model_hypothesis_scenario(
            SCENARIO_PATH
        )
        hit_sweep_unlock = dmh.damage_model_wire_unlock(hit_sweep_scenario)
        state = self._state("npc_cross_key")
        actor = self._session_actor(state)
        with self.assertRaises(dmh.DamageModelValidationError) as raised:
            dmh.build_damage_model_sweep(
                self.legacy, actor, hit_sweep_unlock, self.scenario)
        self.assertIn("wire_unlock_is_for_a_different_profile",
                      str(raised.exception))

    def test_the_replay_tool_passes_under_the_npc_profile(self):
        proc = subprocess.run(
            [sys.executable, str(REPLAY_TOOL), "--profile", "npc_target"],
            cwd=str(ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=600,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, output[-4000:])
        self.assertIn("RESULT: PASS", output)
        self.assertIn("npc_target", output)
        self.assertTrue(output.isascii())


if __name__ == "__main__":
    unittest.main()
