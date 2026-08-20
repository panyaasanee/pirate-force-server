"""DAMAGE-HP-LINK-001 (HYP-PF-026) -- the link sweep on the real dispatcher.

``tests/test_damage_hp_link_hypothesis.py`` proves the encoder offline.  This
file drives the REAL ``make_state_class`` dispatch path behind the opt-in
scenario ``scenarios/damage_hp_link_hypothesis_link_sweep.json`` and proves
the wire layer end to end, headless -- no server process, no socket, no
client:

  * one accepted chat-input frame (the exact 34-byte ascii12 shape the
    HYP-PF-014 lane already classifies, reused because it is the only client
    action an attended tester can trigger on demand) produces exactly EIGHT
    actions, in the scenario's order, at delays 0.0 then 15.0 x 7;
  * the bytes the dispatcher emits are **identical** to the bytes
    ``build_damage_hp_link_sweep`` composes for the same session identity --
    label, PC, frame and delay, compared with ``==`` on the bytes themselves.
    The dispatcher is a forwarder, and if it ever becomes a second composer
    these tests go red;
  * IDENTITY IS PINNED, and that is this lane's own refusal rung: the
    dispatcher fires only if the selected actor IS the canonical smoke
    identity 0x10010001/0 the pins were computed for.  Any other identity
    gets ``damage_hp_link_hypothesis_identity_not_pinned_no_reply``, zero
    actions, an unmoved counter and an unburned one-shot;
  * fail-closed and containment: wrong classification, no selected character
    and not-yet-runtime-ready all give ``[]`` with an exactly-named no-reply
    event; the sweep is ONE-SHOT; with no scenario nothing at all is
    composable and the dispatch method itself raises; the lane is keyed on
    the chat-input vital id and answers no other id; it is mutually exclusive
    with every other scenario mode; no foreign lane's counter moves and no
    foreign-prefix event appears; and no file in the throwaway database
    directory moves one byte -- there is no HP column in any table and this
    lane does not add one.

DISCIPLINE.  Every database in this file is a fresh ``tempfile`` one that is
deleted on exit.  The repository's canonical database is never opened -- it
is only ``stat``-ed, once at import and once at the end, so that a regression
that reached for it would be reported rather than silently tolerated.  That
is the round-41 lesson, kept as a measurement instead of a promise.

NOT proven here, and this is the load-bearing limit: whether a real client
draws the number, moves the bar, or opens L"Common_Death" when it receives
these bytes.  **No client has ever been shown one byte of this profile.**
That is the attended lane, not run.
"""
from __future__ import annotations

import dataclasses
import hashlib
import inspect
import json
import os
from pathlib import Path
import sqlite3
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
from pirateforce_foundation import damage_hp_link_hypothesis as hpl  # noqa: E402
from pirateforce_foundation import damage_model_hypothesis as dmh  # noqa: E402
from pirateforce_foundation import remote_player_hypothesis as rph  # noqa: E402
from pirateforce_foundation import runtimeres_death_hypothesis as rdh  # noqa: E402
from pirateforce_foundation import stats_progression_hypothesis as sp  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "damage_hp_link_hypothesis_link_sweep.json"
REPLAY_TOOL = ROOT / "tools" / "pf_damage_hp_link_headless_replay.py"
RUNTIME_SOURCE_PATH = ROOT / "src" / "pirateforce_foundation" / "runtime.py"
APP_SOURCE_PATH = ROOT / "src" / "pirateforce_foundation" / "app.py"

# Built by concatenation on purpose: the canonical database's file name must
# never appear as a contiguous literal in this file or in the replay tool, so
# that the "no path points at it" test below can search for it honestly.
CANONICAL_DB = ROOT / "state" / ("pirateforce" + ".sqlite3")

SWEEP_EVENT = "damage_hp_link_hypothesis_link_sweep_sent"
REPEAT_EVENT = "damage_hp_link_hypothesis_already_sent_no_reply"
NO_SELECTED_EVENT = "damage_hp_link_hypothesis_no_selected_no_reply"
WRONG_SEQUENCE_EVENT = "damage_hp_link_hypothesis_wrong_sequence_no_reply"
IDENTITY_EVENT = "damage_hp_link_hypothesis_identity_not_pinned_no_reply"
EVENT_PREFIX = "damage_hp_link_hypothesis_"

EXPECTED_STEP_ORDER = (
    "HP_BASELINE", "HIT_WEAK", "HP_AFTER_WEAK", "MISS",
    "HP_AFTER_MISS", "HIT_STRONG", "HP_ZERO_DYING", "DYING_ELAPSED",
)
EXPECTED_KINDS = ("hp", "hit", "hp", "hit", "hp", "hit", "hp", "hp")
EXPECTED_DAMAGE = {"HIT_WEAK": -63, "MISS": 0, "HIT_STRONG": -379}
EXPECTED_FLAGS = {"HIT_WEAK": 0x0001, "MISS": 0x0000, "HIT_STRONG": 0x0001}
EXPECTED_LADDER = (100, 100, 37, 37, 37, 37, 0, 0)
EXPECTED_TIMERS = {"HP_ZERO_DYING": 20.0, "DYING_ELAPSED": 0.0}
EXPECTED_DELAYS = tuple([0.0] + [15.0] * 7)
PINNED_IDENTITY_LO = 0x10010001
PINNED_IDENTITY_HI = 0

# The other chat-keyed and scenario-keyed lanes: their counters must never
# move and their event prefixes must never appear while this lane runs.  The
# list is the remote-player dispatch suite's foreign list PLUS the damage
# model and remote player lanes themselves.
FOREIGN_COUNTERS = (
    "chat_input_echo_count", "channel_message_sweep_count",
    "stats_progression_sweep_count", "hp_death_sweep_count",
    "runtimeres_death_sweep_count", "damage_model_sweep_count",
    "remote_player_sweep_count",
)
FOREIGN_PREFIXES = (
    "chat_input_hypothesis_", "channel_message_hypothesis_",
    "stats_progression_hypothesis_", "hp_death_hypothesis_",
    "runtimeres_death_hypothesis_", "damage_model_hypothesis_",
    "remote_player_hypothesis_",
)


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


class DamageHpLinkDispatchTests(unittest.TestCase):
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
        self.scenario = hpl.load_damage_hp_link_hypothesis_scenario(
            SCENARIO_PATH
        )
        self.unlock = hpl.damage_hp_link_wire_unlock(self.scenario)
        self.pinned = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ---------------------------------------------------------

    def _state_type(self, *, sweep=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            damage_hp_link_hypothesis_scenario=(
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

    def _expected(self, state):
        """The encoder's composition, built without the dispatcher."""
        selected = state.foundation.selected
        self.assertIsNotNone(selected)
        return hpl.build_damage_hp_link_sweep(
            self.legacy, selected.identity_lo, selected.identity_hi,
            self.unlock, self.scenario,
        )

    def _unpin_identity(self, state, *, lo=None, hi=None):
        """Swap the selected character for one whose identity is NOT the
        pinned probe.  The harness cannot create a second character (the V25
        create wire always commits the same canonical smoke character), so
        the frozen Character record is re-stamped instead -- the dispatcher
        reads only identity_lo/identity_hi off it."""
        selected = state.foundation.selected
        self.assertIsNotNone(selected)
        replaced = dataclasses.replace(
            selected,
            identity_lo=selected.identity_lo if lo is None else lo,
            identity_hi=selected.identity_hi if hi is None else hi,
        )
        state.foundation.selected = replaced
        return selected, replaced

    def _db_digest(self):
        """The whole database directory, because the store runs in WAL mode.

        Hashing only the main file would be a weak claim: a committed write
        can land in the ``-wal`` sidecar and leave the main file untouched.
        """
        rows = []
        for name in sorted(os.listdir(self.tmp_dir)):
            path = self.tmp_dir / name
            if path.is_file():
                data = path.read_bytes()
                rows.append((name, len(data), hashlib.sha256(data).hexdigest()))
        return rows

    def _table_row_counts(self):
        connection = sqlite3.connect(str(self.db_path))
        try:
            tables = [
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "ORDER BY name"
                )
            ]
            return {
                table: connection.execute(
                    'SELECT COUNT(*) FROM "%s"' % table
                ).fetchone()[0]
                for table in tables
            }
        finally:
            connection.close()

    def _decoded(self, pc):
        return hpl.decode_damage_hp_link_frame(pc)

    # ----- wiring ----------------------------------------------------------

    def test_make_state_class_accepts_the_link_kwarg(self):
        parameters = inspect.signature(make_state_class).parameters
        self.assertEqual(
            hpl.DAMAGE_HP_LINK_DISPATCH_KWARG,
            "damage_hp_link_hypothesis_scenario",
        )
        self.assertIn(hpl.DAMAGE_HP_LINK_DISPATCH_KWARG, parameters)
        self.assertIsNone(
            parameters[hpl.DAMAGE_HP_LINK_DISPATCH_KWARG].default,
        )

    # ----- happy path ------------------------------------------------------

    def test_one_request_sweeps_the_eight_steps_in_the_pinned_order(self):
        state = self._state("hpl01")
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), len(EXPECTED_STEP_ORDER))
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            list(hpl.DAMAGE_HP_LINK_ACTION_LABELS),
        )
        self.assertEqual(
            list(hpl.DAMAGE_HP_LINK_STEP_ORDER), list(EXPECTED_STEP_ORDER),
        )
        self.assertIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.events.count(SWEEP_EVENT), 1)
        self.assertEqual(state.damage_hp_link_sweep_count, 1)

    def test_the_dispatched_bytes_are_the_encoders_bytes(self):
        """The dispatcher forwards; it does not compose a sweep of its own."""
        state = self._state("hpl02")
        expected = self._expected(state)
        self.assertEqual(state.dispatch(self._trigger()), expected)

    def test_every_dispatched_frame_is_one_of_the_two_pinned_carriers(self):
        state = self._state("hpl03")
        actions = state.dispatch(self._trigger())
        for index, (label, pc, frame, _delay) in enumerate(actions):
            decoded = self._decoded(pc)
            with self.subTest(step=EXPECTED_STEP_ORDER[index]):
                self.assertEqual(decoded["envelope_id"], 0x6E9D)
                self.assertEqual(decoded["envelope_version"], 4)
                self.assertEqual(decoded["base_change_mask"], 2)
                self.assertEqual(decoded["derived_change_mask"], 0)
                self.assertEqual(decoded["kind"], EXPECTED_KINDS[index])
                self.assertEqual(
                    decoded["vital_id"],
                    0x16F7 if EXPECTED_KINDS[index] == "hit" else 0x309A,
                )
                self.assertEqual(decoded["vital_version"], 0)
                self.assertEqual(frame, self.legacy.frame_pc(pc))

    def test_the_hit_frames_carry_the_pinned_damage_and_flag_pairs(self):
        state = self._state("hpl04")
        actions = state.dispatch(self._trigger())
        for index, step in enumerate(EXPECTED_STEP_ORDER):
            if EXPECTED_KINDS[index] != "hit":
                continue
            decoded = self._decoded(actions[index][1])
            with self.subTest(step=step):
                self.assertEqual(decoded["damage_wire"], EXPECTED_DAMAGE[step])
                self.assertEqual(decoded["flags"], EXPECTED_FLAGS[step])

    def test_the_hp_frames_carry_the_server_held_ladder(self):
        """The whole point of the lane: the bar shows what the hits cost."""
        state = self._state("hpl05")
        actions = state.dispatch(self._trigger())
        for index, step in enumerate(EXPECTED_STEP_ORDER):
            if EXPECTED_KINDS[index] != "hp":
                continue
            fields = self._decoded(actions[index][1])["fields"]
            with self.subTest(step=step):
                self.assertEqual(fields["hp_current"], EXPECTED_LADDER[index])
                self.assertEqual(fields["hp_max"], 100)
                self.assertEqual(
                    fields.get(hpl.HP_LINK_DEATH_TIMER_NAME),
                    EXPECTED_TIMERS.get(step),
                )

    def test_the_damage_field_is_the_signed_reading_of_the_u32_tag(self):
        """Unsigned would read 4294967233, not -63: the sign is the lane."""
        state = self._state("hpl06")
        actions = state.dispatch(self._trigger())
        for index, step in enumerate(EXPECTED_STEP_ORDER):
            if EXPECTED_KINDS[index] != "hit":
                continue
            decoded = self._decoded(actions[index][1])
            raw = struct.pack("<i", decoded["damage_wire"])
            with self.subTest(step=step):
                self.assertEqual(struct.unpack("<i", raw)[0],
                                 EXPECTED_DAMAGE[step])
                self.assertEqual(struct.unpack("<I", raw)[0],
                                 EXPECTED_DAMAGE[step] & 0xFFFFFFFF)
                self.assertLessEqual(decoded["damage_wire"], 0)

    def test_every_frame_names_the_sessions_selected_character(self):
        state = self._state("hpl07")
        selected = state.foundation.selected
        identity = (
            ((selected.identity_hi & 0xFFFFFFFF) << 32)
            | (selected.identity_lo & 0xFFFFFFFF)
        )
        # ... which on this lane is ALSO the pinned probe identity, by
        # construction of the fresh store: first account, first character.
        self.assertEqual(identity, PINNED_IDENTITY_LO)
        seen = set()
        for _label, pc, _frame, _delay in state.dispatch(self._trigger()):
            decoded = self._decoded(pc)
            seen.add(decoded["performer_identity"])
            if decoded["kind"] == "hit":
                self.assertEqual(decoded["target_identity"], identity)
        self.assertEqual(seen, {identity})

    def test_every_dispatched_frame_reproduces_its_module_and_scenario_pins(self):
        state = self._state("hpl08")
        for index, (_l, pc, frame, _d) in enumerate(
            state.dispatch(self._trigger())
        ):
            step = EXPECTED_STEP_ORDER[index]
            pin = hpl.DAMAGE_HP_LINK_PINS[step]
            scenario_pin = self.pinned["probe"]["per_step"][step]
            pc_digest = hashlib.sha256(pc).hexdigest().upper()
            frame_digest = hashlib.sha256(frame).hexdigest().upper()
            self.assertEqual(len(pc), pin["pc_size"], step)
            self.assertEqual(len(frame), pin["frame_size"], step)
            self.assertEqual(pc_digest, pin["pc_sha256"], step)
            self.assertEqual(frame_digest, pin["frame_sha256"], step)
            # The module pin and the scenario file pin must be the SAME pin.
            self.assertEqual(scenario_pin["pc_sha256"], pin["pc_sha256"], step)
            self.assertEqual(
                scenario_pin["frame_sha256"], pin["frame_sha256"], step,
            )

    def test_the_spacing_matches_the_scenario(self):
        state = self._state("hpl09")
        delays = [d for _l, _p, _f, d in state.dispatch(self._trigger())]
        self.assertEqual(delays, list(EXPECTED_DELAYS))
        self.assertEqual(
            self.scenario.first_delay_seconds,
            hpl.DAMAGE_HP_LINK_FIRST_DELAY_SECONDS,
        )
        self.assertEqual(
            self.scenario.spacing_seconds, hpl.DAMAGE_HP_LINK_SPACING_SECONDS,
        )
        self.assertEqual(hpl.DAMAGE_HP_LINK_SPACING_SECONDS, 15.0)

    def test_the_request_payload_is_a_trigger_not_an_input(self):
        """Nothing in the request reaches the answer.

        The sweep is one-shot, so the two probes need two sessions -- and on
        this lane the second session's own throwaway store recreates the SAME
        pinned identity (first account, first character), so the two answers
        must be byte-identical.  If any of the 34 payload bytes were read,
        they would diverge.
        """
        first = self._state("hpl10").dispatch(self._trigger("probe1"))
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
                damage_hp_link_hypothesis_scenario=self.scenario,
            )("hpl11")
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
        state = self._state("hpl12")
        before = self._db_digest()
        state.dispatch(self._trigger())
        self.assertEqual(self._db_digest(), before)

    def test_the_sweep_writes_no_row_to_any_table(self):
        """There is no HP column in any table and this lane adds none."""
        state = self._state("hpl13")
        counts_before = self._table_row_counts()
        # The comparison must have teeth: the session harness has already
        # written an account, a session and a character.
        self.assertTrue(any(count > 0 for count in counts_before.values()))
        self.assertEqual(len(state.dispatch(self._trigger())), 8)
        self.assertEqual(self._table_row_counts(), counts_before)

    def test_the_sweep_takes_no_socket_action(self):
        state = self._state("hpl14")
        self.assertTrue(
            all(len(action) == 4 for action in state.dispatch(self._trigger()))
        )

    def test_the_sweep_carries_exactly_one_miss_control_frame(self):
        state = self._state("hpl15")
        misses = []
        for index, (_l, pc, _f, _d) in enumerate(
            state.dispatch(self._trigger())
        ):
            decoded = self._decoded(pc)
            if decoded["kind"] == "hit" and decoded["damage_wire"] == 0 and (
                decoded["flags"] == 0
            ):
                misses.append(EXPECTED_STEP_ORDER[index])
        self.assertEqual(misses, list(hpl.DAMAGE_HP_LINK_MISS_STEP_LABELS))
        self.assertEqual(misses, ["MISS"])

    def test_the_two_post_miss_hp_frames_are_byte_identical(self):
        state = self._state("hpl16")
        actions = state.dispatch(self._trigger())
        after_weak = EXPECTED_STEP_ORDER.index("HP_AFTER_WEAK")
        after_miss = EXPECTED_STEP_ORDER.index("HP_AFTER_MISS")
        self.assertEqual(actions[after_weak][1], actions[after_miss][1])
        self.assertEqual(actions[after_weak][2], actions[after_miss][2])

    # ----- the gate --------------------------------------------------------

    def test_the_runtime_branch_is_gated_on_the_scenario_and_the_vital_id(self):
        """The branch must read BOTH conditions, and there must be one of it."""
        source = RUNTIME_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "            if (\n"
            "                damage_hp_link_hypothesis_scenario is not None\n"
            "                and nested_id == CHAT_INPUT_VITAL_ID\n"
            "            ):\n",
            source,
        )
        # The unlock is derived once, behind the same gate, at construction.
        self.assertIn(
            "    if damage_hp_link_hypothesis_scenario is not None:\n", source,
        )
        # Exactly one call site, inside the branch: the dispatcher composes
        # nowhere else and nothing else composes for it.
        self.assertEqual(source.count("build_damage_hp_link_sweep("), 1)
        self.assertEqual(
            source.count("def _dispatch_damage_hp_link_hypothesis("), 1,
        )
        self.assertEqual(
            source.count("self._dispatch_damage_hp_link_hypothesis("), 1,
        )
        # The ledger annotation binds this file and the ledger entry both
        # ways, and verify_hypothesis_ledger.py rejects a duplicate per file.
        self.assertEqual(
            source.count("PF-HYPOTHESIS-LEDGER: HYP-PF-026 active"), 1,
        )

    def test_the_branch_answers_no_vital_id_other_than_the_chat_input_one(self):
        """A different nested id keeps its frozen baseline answer, untouched."""
        state = self._state("hpl17")
        actions = state.dispatch(self.legacy.parse_outer(
            self._trigger_pc(self._payload(), vital_id=0xBEEF)
        ))
        self.assertFalse([
            label for label, _p, _f, _d in actions
            if label.startswith(hpl.DAMAGE_HP_LINK_ACTION_LABEL_PREFIX)
        ])
        self.assertFalse(
            [event for event in state.events if event.startswith(EVENT_PREFIX)]
        )
        self.assertEqual(state.damage_hp_link_sweep_count, 0)

    def test_the_app_flag_is_live_and_still_demands_an_existing_database(self):
        source = APP_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertIn("--damage-hp-link-hypothesis-scenario", source)
        self.assertIn(
            "'--damage-hp-link-hypothesis-scenario requires an explicit '",
            source,
        )
        self.assertIn(
            "damage_hp_link_hypothesis_scenario=damage_hp_link_hypothesis,",
            source,
        )
        self.assertEqual(
            source.count("PF-HYPOTHESIS-LEDGER: HYP-PF-026 active"), 1,
        )

    # ----- mutual exclusion ------------------------------------------------

    def test_the_lane_is_mutually_exclusive_with_every_other_mode(self):
        """Seven pairs, because all of them key on the same vital id or on
        the shared scenario machinery."""
        pairs = {
            "damage_model_hypothesis_scenario": (
                dmh.load_damage_model_hypothesis_scenario(
                    ROOT / "scenarios" / "damage_model_hypothesis_hit_sweep.json"
                )
            ),
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
            "remote_player_hypothesis_scenario": (
                rph.load_remote_player_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "remote_player_hypothesis_visibility_probe.json"
                )
            ),
        }
        self.assertGreaterEqual(len(pairs), 3)
        self.assertIn("damage_model_hypothesis_scenario", pairs)
        self.assertIn("hp_death_hypothesis_scenario", pairs)
        for kwarg, other in pairs.items():
            with self.subTest(other=kwarg):
                with self.assertRaisesRegex(ValueError, "mutually exclusive"):
                    make_state_class(
                        self.legacy, self.lifecycle, self.projector,
                        damage_hp_link_hypothesis_scenario=self.scenario,
                        **{kwarg: other},
                    )

    def test_a_scenario_object_outside_the_allowlist_is_refused(self):
        for candidate in (
            object(),
            hpl.DAMAGE_HP_LINK_SCENARIO_ID,
            hpl.DamageHpLinkHypothesisScenario(
                hpl.DAMAGE_HP_LINK_SCENARIO_ID,
                hpl.DAMAGE_HP_LINK_HYPOTHESIS_ID,
                tuple(reversed(hpl.DAMAGE_HP_LINK_STEP_ORDER)),
                hpl.DAMAGE_HP_LINK_SPACING_SECONDS,
                hpl.DAMAGE_HP_LINK_FIRST_DELAY_SECONDS,
                hpl.DAMAGE_HP_LINK_ACTION_LABEL_PREFIX,
            ),
        ):
            with self.subTest(candidate=type(candidate).__name__):
                # Unlike the HYP-PF-024 lane (whose validation error derives
                # from RuntimeError, an asymmetry its own dispatch tests name),
                # this lane's DamageHpLinkValidationError derives from
                # ValueError, so a caller wrapping make_state_class in
                # ``except ValueError`` catches both this refusal and the
                # mutual-exclusion refusal.  Asserted, not assumed.
                with self.assertRaises(hpl.DamageHpLinkValidationError) as raised:
                    make_state_class(
                        self.legacy, self.lifecycle, self.projector,
                        damage_hp_link_hypothesis_scenario=candidate,
                    )
                self.assertIn(
                    "scenario_object_exceeds_allowlist", str(raised.exception),
                )
                self.assertIsInstance(raised.exception, ValueError)

    # ----- one-shot --------------------------------------------------------

    def test_the_sweep_is_one_shot(self):
        """The ladder's value is that a tester can predict every number
        before it appears; a repeat trigger must therefore emit nothing at
        all, and must say so by name."""
        state = self._state("hpl18")
        self.assertEqual(len(state.dispatch(self._trigger())), 8)
        before = self._db_digest()
        self.assertEqual(state.dispatch(self._trigger()), [])
        self.assertEqual(state.dispatch(self._trigger("probe2")), [])
        self.assertEqual(state.damage_hp_link_sweep_count, 1)
        self.assertEqual(state.events.count(SWEEP_EVENT), 1)
        self.assertEqual(state.events.count(REPEAT_EVENT), 2)
        self.assertEqual(self._db_digest(), before)

    # ----- fail closed -----------------------------------------------------

    def _refused(self, state, parsed, event_name):
        before = self._db_digest()
        counts_before = self._table_row_counts()
        self.assertEqual(state.dispatch(parsed), [])
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.events.count(event_name), 1, state.events)
        self.assertEqual(state.damage_hp_link_sweep_count, 0)
        self.assertEqual(self._db_digest(), before)
        self.assertEqual(self._table_row_counts(), counts_before)

    def test_no_selected_character_fails_closed(self):
        self._refused(
            self._state("hpl19", select=False), self._trigger(),
            NO_SELECTED_EVENT,
        )

    def test_not_yet_teleport_and_runtime_ack_fails_closed(self):
        self._refused(
            self._state("hpl20", ready=False), self._trigger(),
            WRONG_SEQUENCE_EVENT,
        )

    def test_wrong_length_fails_closed(self):
        self._refused(
            self._state("hpl21"),
            self.legacy.parse_outer(self._trigger_pc(self._payload()[:-1])),
            EVENT_PREFIX + "wrong_length_no_reply",
        )

    def test_wrong_prefix_fails_closed(self):
        payload = bytearray(self._payload())
        payload[0] ^= 0xFF
        self._refused(
            self._state("hpl22"),
            self.legacy.parse_outer(self._trigger_pc(bytes(payload))),
            EVENT_PREFIX + "wrong_prefix_no_reply",
        )

    def test_wrong_text_bytes_fail_closed(self):
        pc = bytearray(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        pc[-1] ^= 0xFF
        self._refused(
            self._state("hpl23"), self.legacy.parse_outer(bytes(pc)),
            EVENT_PREFIX + "wrong_text_no_reply",
        )

    def test_wrong_envelope_fails_closed(self):
        for index, kwargs in enumerate(
            ({"outer_version": 1}, {"nested_version": 1}),
        ):
            with self.subTest(**kwargs):
                self._refused(
                    self._state("hpl24_%d" % index),
                    self.legacy.parse_outer(
                        self._trigger_pc(self._payload(), **kwargs)
                    ),
                    EVENT_PREFIX + "wrong_envelope_no_reply",
                )

    # ----- THE NEW RUNG: identity is pinned --------------------------------

    def test_a_selected_identity_that_is_not_the_pinned_probe_fails_closed(self):
        """The lane composes the pinned bytes or nothing: a session whose
        selected actor is not 0x10010001/0 gets the named refusal, zero
        actions, and an untouched database."""
        state = self._state("hpl25")
        _original, replaced = self._unpin_identity(
            state, lo=PINNED_IDENTITY_LO + 1,
        )
        self.assertNotEqual(replaced.identity_lo, PINNED_IDENTITY_LO)
        self._refused(state, self._trigger(), IDENTITY_EVENT)

    def test_a_nonzero_identity_hi_is_not_the_pinned_probe_either(self):
        """Both halves of the qword are pinned, not just the low word."""
        state = self._state("hpl26")
        self._unpin_identity(state, hi=1)
        self._refused(state, self._trigger(), IDENTITY_EVENT)

    def test_the_identity_refusal_emits_no_frame_and_no_sweep_event(self):
        state = self._state("hpl27")
        self._unpin_identity(state, lo=0x10010002)
        actions = state.dispatch(self._trigger())
        self.assertEqual(actions, [])
        self.assertEqual(state.events.count(IDENTITY_EVENT), 1)
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.damage_hp_link_sweep_count, 0)

    def test_the_identity_refusal_does_not_burn_the_one_shot(self):
        """A refusal is not a send: once the pinned identity is back, the
        sweep still fires exactly once."""
        state = self._state("hpl28")
        original, _replaced = self._unpin_identity(
            state, lo=PINNED_IDENTITY_LO ^ 0x00ABCDEF,
        )
        self.assertEqual(state.dispatch(self._trigger()), [])
        self.assertEqual(state.events.count(IDENTITY_EVENT), 1)
        self.assertEqual(state.damage_hp_link_sweep_count, 0)
        state.foundation.selected = original
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 8)
        self.assertEqual(state.damage_hp_link_sweep_count, 1)
        self.assertEqual(state.events.count(SWEEP_EVENT), 1)

    def test_the_dispatcher_source_reads_both_identity_halves(self):
        source = RUNTIME_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "identity_lo != HP_LINK_PROBE_IDENTITY_LO", source,
        )
        self.assertIn(
            "identity_hi != HP_LINK_PROBE_IDENTITY_HI", source,
        )
        self.assertEqual(
            source.count(
                "damage_hp_link_hypothesis_identity_not_pinned_no_reply"
            ),
            1,
        )

    def test_no_refusal_path_ever_emits_a_frame(self):
        cases = (
            ("hpl29", {"select": False}, None, self._trigger()),
            ("hpl30", {"ready": False}, None, self._trigger()),
            ("hpl31", {}, 0x10010002, self._trigger()),
            ("hpl32", {}, None, self.legacy.parse_outer(
                self._trigger_pc(self._payload()[:-1])
            )),
            ("hpl33", {}, None, self.legacy.parse_outer(
                self._trigger_pc(self._payload(), outer_version=1)
            )),
        )
        for login, kwargs, unpin_lo, parsed in cases:
            with self.subTest(login=login):
                state = self._state(login, **kwargs)
                if unpin_lo is not None:
                    self._unpin_identity(state, lo=unpin_lo)
                self.assertEqual(state.dispatch(parsed), [])
                self.assertEqual(state.damage_hp_link_sweep_count, 0)
                self.assertNotIn(SWEEP_EVENT, state.events)

    # ----- containment against the other lanes ------------------------------

    def test_no_other_chat_keyed_lane_is_reachable_while_this_one_runs(self):
        """The other lanes keyed on vital 0xAC52 are refused at construction
        (mutual exclusion), so while this lane is active the accepted frame
        reaches ONLY the link dispatcher."""
        state = self._state("hpl34")
        actions = state.dispatch(self._trigger())
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            list(hpl.DAMAGE_HP_LINK_ACTION_LABELS),
        )
        for counter in FOREIGN_COUNTERS:
            with self.subTest(counter=counter):
                self.assertEqual(getattr(state, counter), 0)
        for event in state.events:
            self.assertFalse(event.startswith(FOREIGN_PREFIXES), event)

    def test_the_foreign_counters_stay_zero_across_every_refusal_too(self):
        state = self._state("hpl35")
        self._unpin_identity(state, lo=0x10010002)
        self.assertEqual(state.dispatch(self._trigger()), [])
        for counter in FOREIGN_COUNTERS:
            with self.subTest(counter=counter):
                self.assertEqual(getattr(state, counter), 0)
        for event in state.events:
            self.assertFalse(event.startswith(FOREIGN_PREFIXES), event)

    # ----- the flag off ----------------------------------------------------

    def test_trap_nothing_is_composable_when_the_lane_is_not_enabled(self):
        """TRAP -- the failure mode: a branch that forgets its scenario gate.

        Two independent locks, because one of them is the kind a careless
        edit removes.  (a) with no scenario the trigger keeps its frozen
        baseline answer: no HYP-PF-026 action, no link event, none of the
        sweep's bytes.  (b) even if a future edit reached the dispatch method
        WITHOUT the gate, it still cannot emit anything: the unlock and the
        scenario profile are closed over as ``None``, so the composer raises
        instead of putting a frame on the wire.
        """
        state = self._state("hpl36", sweep=False)
        reference = self._state("hpl37")
        expected_pcs = {pc for _l, pc, _f, _d in self._expected(reference)}

        before = self._db_digest()
        actions = state.dispatch(self._trigger())
        self.assertFalse([
            label for label, _p, _f, _d in actions
            if label.startswith(hpl.DAMAGE_HP_LINK_ACTION_LABEL_PREFIX)
        ])
        self.assertFalse({pc for _l, pc, _f, _d in actions} & expected_pcs)
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertFalse(
            [event for event in state.events if event.startswith(EVENT_PREFIX)]
        )
        self.assertEqual(state.damage_hp_link_sweep_count, 0)
        self.assertEqual(self._db_digest(), before)

        with self.assertRaises(hpl.DamageHpLinkValidationError):
            state._dispatch_damage_hp_link_hypothesis(self._trigger())
        self.assertEqual(state.damage_hp_link_sweep_count, 0)
        self.assertNotIn(SWEEP_EVENT, state.events)


class HeadlessReplayToolTests(unittest.TestCase):
    """The tool is run as a real subprocess, which is the only way to prove
    that its exit code and its console encoding are what the Windows attended
    runner will actually see.  The tests skip themselves until the tool is
    written, exactly as the encoder suite's VerifierTests do."""

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(REPLAY_TOOL), *args],
            capture_output=True,
        )

    @unittest.skipUnless(
        REPLAY_TOOL.exists(),
        "tools/pf_damage_hp_link_headless_replay.py is not written yet")
    def test_the_replay_tool_runs_clean_against_the_real_dispatcher(self):
        completed = self._run()
        self.assertEqual(
            completed.returncode, 0,
            completed.stdout.decode("utf-8", "replace")
            + completed.stderr.decode("utf-8", "replace"),
        )
        self.assertIn(b"RESULT: PASS", completed.stdout)

    @unittest.skipUnless(
        REPLAY_TOOL.exists(),
        "tools/pf_damage_hp_link_headless_replay.py is not written yet")
    def test_the_replay_tools_output_is_pure_ascii(self):
        """cp874 on a Windows console turns one non-ASCII byte into a crash."""
        completed = self._run()
        self.assertEqual(completed.returncode, 0)
        self.assertTrue(
            all(byte < 128 for byte in completed.stdout),
            "the tool printed a non-ASCII byte",
        )
        completed.stdout.decode("ascii")
        completed.stderr.decode("ascii")

    @unittest.skipUnless(
        REPLAY_TOOL.exists(),
        "tools/pf_damage_hp_link_headless_replay.py is not written yet")
    def test_the_replay_tool_needs_no_third_party_package(self):
        source = REPLAY_TOOL.read_text(encoding="utf-8")
        for banned in ("capstone", "pefile", "numpy", "yaml", "requests",
                       "pytest"):
            self.assertNotIn("import " + banned, source)

    @unittest.skipUnless(
        REPLAY_TOOL.exists(),
        "tools/pf_damage_hp_link_headless_replay.py is not written yet")
    def test_the_replay_tool_source_is_pure_ascii(self):
        self.assertTrue(
            all(byte < 128 for byte in REPLAY_TOOL.read_bytes()),
            "the tool's source carries a non-ASCII byte",
        )


class CanonicalDatabaseContainmentTests(unittest.TestCase):
    """Round 41: pytest once reached the canonical database.  Never again."""

    def test_no_path_in_this_suite_names_the_canonical_database(self):
        test_source = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn(CANONICAL_DB.name, test_source)
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


if __name__ == "__main__":
    unittest.main()
