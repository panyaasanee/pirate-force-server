"""GROUND-LOOT-NAMEPROP-001 (HYP-PF-039) -- the selector lane.

This file proves three things and refuses to claim a fourth.

1. The scenario file is a permission token, not a source of values: the
   loader's named refusals, the identity gate, and cross-lane isolation in
   both directions against HYP-PF-032's own file.
2. The composition, rebuilt INDEPENDENTLY here with ``struct`` from the
   re-derived 0x5F85B0 wire table and never through the module's own element
   helper -- including the thing the whole experiment rests on: the CONTROL
   element (mask 0x12, no selector fields) and the TREATMENT element (mask
   0x3A, gate at +0x1B and index 6 at +0x1A) carry a byte-identical payload
   dword and byte-identical coordinates and differ by exactly the four
   selector bytes.
3. The real dispatcher, on a throwaway sqlite, appends both exactly once,
   commits nothing, and never moves HYP-PF-032's latch.

And it drives the headless replay tool as a subprocess, so that tool's guard
count is a number something actually executes rather than a number in a
docstring.

NOT proven here, and not provable on any machine without a person at a
screen: whether the client accepts element mask 0x3A at all, and whether the
name-property gate and index reach the floating label.  That is GT-069,
attended, queued, not run.  Nothing here claims to know what UI text
property 0x34 or 0x5D..0x62 MEAN, and none of them is known to be a colour.
The 1.50 carried on the treatment frame is a SCHEDULER DEADLINE OFFSET and
not a measured wire gap -- nothing in this repository measures the realized
gap.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    ground_loot_nameprop_hypothesis as glnp,
)
from pirateforce_foundation import ground_loot_hypothesis as glh  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "ground_loot_nameprop_probe.json"
RENDER_SCENARIO_PATH = (
    ROOT / "scenarios" / "ground_loot_hypothesis_bit08_render.json"
)
REPLAY_TOOL = ROOT / "tools" / "pf_ground_loot_nameprop_headless_replay.py"

PAIR_EVENT = "hyp_pf_039_ground_loot_nameprop_pair_committed"
COMPOSE_REFUSED_EVENT = "ground_loot_nameprop_compose_refused_no_reply"
SIBLING_EVENT = "hyp_pf_032_ground_loot_bit08_pair_committed"
CONTROL_LABEL = "GROUND_LOOT_NAMEPROP_CONTROL_ONCE"
TREATMENT_LABEL = "GROUND_LOOT_NAMEPROP_IDX6_ONCE"
LANE_LABELS = (CONTROL_LABEL, TREATMENT_LABEL)

# Independent restatement of everything the module pins.  If the module and
# this table ever disagree the tests below go red, which is the point.
CONTROL_MASK = 0x12
TREATMENT_MASK = 0x3A
EXPECTED_DERIVED_BIT = 0x08
FRAME_COORD_SHIFT = 10
# key, dword, mask, gate, index, x_offset, delay
EXPECTED_ELEMENTS = (
    (3, 2200423, CONTROL_MASK, None, None, 30.0, 0.0),
    (4, 2200423, TREATMENT_MASK, 1, 6, 30.0, 1.50),
)
# pc_size, frame_size, coord_spans, pc_template, frame_template
EXPECTED_GEOMETRY = (
    (44, 54, ((30, 34), (35, 39), (40, 44)),
     "8657614E33073F5C1969AA6CB1FEAA441E0A1ED011F38AD13B22270183B8E26D",
     "FB419334817234FFEA7A2A8A498E2C24DF7D223915783D5CBFBB87B2866BAD9D"),
    (48, 58, ((32, 36), (37, 41), (42, 46)),
     "34E4D5B285258FD8BE929704195F2C704B6B25A03ECDDC9F41C2D8E42C115FF2",
     "A91392DDC1F092DDFE7F5897E2A38CAB9C7C93646BB06BA5248F5161578E1D07"),
)

# A real spawn the attended round of 2026-08-23 actually measured, used so
# the coordinate arithmetic is exercised on a number nobody chose to be
# convenient.
TRIGGER = (-8553.947265625, -2579.68896484375, 186.0)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest().upper()


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def independent_pc(msg_id: int, key: int, dword: int, mask: int,
                   gate, index, x: float, y: float, z: float) -> bytes:
    """Rebuild one pc with struct only -- no module code on this path.

    Field order is the codec's, ascending by mask bit: dword (0x02), gate
    (0x08), position (0x10), index (0x20).
    """
    out = b""
    out += b"\x12" + struct.pack("<H", msg_id)
    out += b"\x14" + struct.pack("<I", 0)
    out += b"\x08" + bytes([4])
    out += b"\x0b" + bytes([0])
    out += b"\x0b" + bytes([EXPECTED_DERIVED_BIT])
    out += b"\x12" + struct.pack("<H", 1)
    out += b"\x14" + struct.pack("<I", key)
    out += b"\x0b" + bytes([mask])
    out += b"\x14" + struct.pack("<I", dword)
    if mask & 0x08:
        out += b"\x05" + bytes([gate])
    out += b"\x2a" + struct.pack("<f", x)
    out += b"\x2a" + struct.pack("<f", y)
    out += b"\x2a" + struct.pack("<f", z)
    if mask & 0x20:
        out += b"\x08" + bytes([index])
    return out


class NamePropScenarioTests(unittest.TestCase):
    """The scenario file is a permission token, never a source of values."""

    def setUp(self):
        self.body = SCENARIO_PATH.read_text(encoding="utf-8")
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _written(self, text: str) -> Path:
        path = Path(self.tmp.name) / "probe.json"
        path.write_text(text, encoding="utf-8")
        return path

    def test_the_shipped_file_loads_and_yields_the_frozen_profile(self):
        loaded = glnp.load_ground_loot_nameprop_scenario(SCENARIO_PATH)
        self.assertIs(loaded, glnp._PROFILES[loaded.scenario_id])
        self.assertEqual(loaded.hypothesis_id, "HYP-PF-039")
        self.assertEqual(loaded.scenario_id, "ground_loot_nameprop_probe")
        self.assertEqual(len(loaded.elements), 2)

    def test_the_shipped_file_declares_the_control_and_the_treatment(self):
        for needle in (
            '"role": "control"',
            '"role": "treatment"',
            '"element_mask_hex": "0x12"',
            '"element_mask_hex": "0x3A"',
            '"control_pc_size": 44',
            '"control_frame_size": 54',
            '"treatment_pc_size": 48',
            '"treatment_frame_size": 58',
            '"property_index": 6',
            '"scheduler_delay": 1.5',
        ):
            self.assertIn(needle, self.body)

    def test_the_shipped_file_names_the_two_coordinate_span_sets(self):
        """The masks differ, so the spans differ; both must be pinned."""
        self.assertIn('"control_coordinate_bytes_masked": '
                      '"pc[30:34]+pc[35:39]+pc[40:44]"', self.body)
        self.assertIn('"treatment_coordinate_bytes_masked": '
                      '"pc[32:36]+pc[37:41]+pc[42:46]"', self.body)

    def test_the_shipped_file_is_declared_test_only(self):
        self.assertIn('"test_only": true', self.body)
        self.assertIn('"production_allowed": false', self.body)
        self.assertFalse(glnp.production_allowed)

    def test_the_file_carries_the_nonclaim_that_this_is_not_a_colour(self):
        self.assertIn("ui_text_property_is_a_colour", self.body)
        self.assertIn("static_create_path_is_the_widget_the_observer_sees",
                      self.body)
        self.assertIn("scheduler_delay_is_a_wire_gap", self.body)

    def test_a_tampered_index_is_refused_rather_than_obeyed(self):
        path = self._written(
            self.body.replace('"property_index": 6', '"property_index": 5')
        )
        with self.assertRaises(ValueError) as caught:
            glnp.load_ground_loot_nameprop_scenario(path)
        self.assertIn("exceeds_allowlist", str(caught.exception))

    def test_a_tampered_control_mask_is_refused_rather_than_obeyed(self):
        path = self._written(
            self.body.replace('"element_mask_hex": "0x12"',
                              '"element_mask_hex": "0x3A"')
        )
        with self.assertRaises(ValueError) as caught:
            glnp.load_ground_loot_nameprop_scenario(path)
        self.assertIn("exceeds_allowlist", str(caught.exception))

    def test_an_int_where_a_float_is_expected_is_refused(self):
        path = self._written(self.body.replace('"x_offset": 30.0',
                                               '"x_offset": 30'))
        with self.assertRaises(ValueError) as caught:
            glnp.load_ground_loot_nameprop_scenario(path)
        self.assertIn("exceeds_allowlist", str(caught.exception))

    def test_an_extra_key_is_refused(self):
        path = self._written(self.body.replace(
            '"schema": 1,', '"schema": 1,\n  "extra": true,'))
        with self.assertRaises(ValueError) as caught:
            glnp.load_ground_loot_nameprop_scenario(path)
        self.assertIn("exceeds_allowlist", str(caught.exception))

    def test_a_missing_key_is_refused(self):
        path = self._written(self.body.replace('  "schema": 1,\n', ''))
        with self.assertRaises(ValueError) as caught:
            glnp.load_ground_loot_nameprop_scenario(path)
        self.assertIn("exceeds_allowlist", str(caught.exception))

    def test_a_non_json_file_is_refused_by_name(self):
        path = self._written("not json at all")
        with self.assertRaises(ValueError) as caught:
            glnp.load_ground_loot_nameprop_scenario(path)
        self.assertIn("unreadable", str(caught.exception))

    def test_an_absent_file_is_refused_by_name(self):
        with self.assertRaises(ValueError) as caught:
            glnp.load_ground_loot_nameprop_scenario(
                Path(self.tmp.name) / "nope.json")
        self.assertIn("unreadable", str(caught.exception))

    def test_an_unknown_id_is_refused_by_name(self):
        path = self._written(self.body.replace(
            '"ground_loot_nameprop_probe"', '"something_else"', 1))
        with self.assertRaises(ValueError) as caught:
            glnp.load_ground_loot_nameprop_scenario(path)
        self.assertIn("unknown_id", str(caught.exception))

    def test_the_other_lanes_file_never_opens_this_gate(self):
        """Cross-lane loader isolation, both directions."""
        with self.assertRaises(ValueError):
            glnp.load_ground_loot_nameprop_scenario(RENDER_SCENARIO_PATH)
        with self.assertRaises(ValueError):
            glh.load_ground_loot_hypothesis_scenario(SCENARIO_PATH)

    def test_a_value_equal_lookalike_profile_is_refused(self):
        real = glnp.load_ground_loot_nameprop_scenario(SCENARIO_PATH)
        lookalike = glnp.NamePropScenario(
            real.scenario_id, real.hypothesis_id, real.elements,
        )
        self.assertEqual(lookalike, real)
        with self.assertRaises(ValueError) as caught:
            glnp.require_ground_loot_nameprop_scenario(lookalike)
        self.assertIn("not_allowlisted", str(caught.exception))
        self.assertIs(
            glnp.require_ground_loot_nameprop_scenario(real), real)


class NamePropCompositionTests(unittest.TestCase):
    def setUp(self):
        self.legacy = _legacy()
        self.scenario = glnp.load_ground_loot_nameprop_scenario(SCENARIO_PATH)

    def test_the_modules_constants_match_this_files_independent_copies(self):
        self.assertEqual(glnp.GROUND_LOOT_NAMEPROP_CONTROL_MASK, CONTROL_MASK)
        self.assertEqual(glnp.GROUND_LOOT_NAMEPROP_TREATMENT_MASK,
                         TREATMENT_MASK)
        self.assertEqual(glnp.GROUND_LOOT_NAMEPROP_DERIVED_BIT,
                         EXPECTED_DERIVED_BIT)
        self.assertEqual(glnp.GROUND_LOOT_NAMEPROP_FRAME_COORD_SHIFT,
                         FRAME_COORD_SHIFT)
        self.assertEqual(glnp.GROUND_LOOT_NAMEPROP_LABELS, LANE_LABELS)
        self.assertEqual(
            tuple(
                (g.pc_size, g.frame_size, g.coord_spans,
                 g.pc_template_sha256, g.frame_template_sha256)
                for g in glnp.GROUND_LOOT_NAMEPROP_GEOMETRY
            ),
            EXPECTED_GEOMETRY,
        )
        self.assertEqual(
            tuple(
                (e.element_key, e.payload_dword, e.element_mask,
                 e.property_gate, e.property_index, e.x_offset, e.delay)
                for e in self.scenario.elements
            ),
            EXPECTED_ELEMENTS,
        )

    def test_the_masks_are_not_magic_numbers(self):
        self.assertEqual(CONTROL_MASK, 0x02 | 0x10)
        self.assertEqual(TREATMENT_MASK, 0x02 | 0x08 | 0x10 | 0x20)
        self.assertFalse(CONTROL_MASK & 0x08)
        self.assertFalse(CONTROL_MASK & 0x20)
        self.assertFalse(TREATMENT_MASK & 0x04)

    def test_the_experiment_holds_everything_but_the_selector(self):
        """If this fails the round measures something other than the fields."""
        control, treatment = self.scenario.elements
        self.assertEqual(control.payload_dword, treatment.payload_dword)
        self.assertEqual(control.x_offset, treatment.x_offset)
        self.assertIsNone(control.property_gate)
        self.assertIsNone(control.property_index)
        self.assertNotEqual(treatment.property_gate, 0)
        self.assertIsNotNone(treatment.property_index)

    def test_the_treatment_index_is_not_the_ctor_default(self):
        """+0x1A defaults to 1, so index 1 would prove nothing."""
        self.assertNotEqual(self.scenario.elements[1].property_index, 1)
        self.assertLessEqual(self.scenario.elements[1].property_index,
                             glnp.GROUND_LOOT_NAMEPROP_INDEX_MAX)
        self.assertGreaterEqual(self.scenario.elements[1].property_index,
                                glnp.GROUND_LOOT_NAMEPROP_INDEX_MIN)

    def test_the_composed_pcs_equal_the_independent_struct_rebuild(self):
        frames = glnp.make_ground_loot_nameprop_frames(
            self.legacy, self.scenario, TRIGGER)
        self.assertEqual(len(frames), 2)
        for (pc, frame), spec in zip(frames, EXPECTED_ELEMENTS):
            key, dword, mask, gate, index, offset, _delay = spec
            expected = independent_pc(
                0x6E9D, key, dword, mask, gate, index,
                _f32(TRIGGER[0] + offset), _f32(TRIGGER[1]), _f32(TRIGGER[2]),
            )
            self.assertEqual(pc, expected)
            self.assertEqual(frame, self.legacy.frame_pc(pc))

    def test_the_masked_template_pins_hold_at_their_own_spans(self):
        frames = glnp.make_ground_loot_nameprop_frames(
            self.legacy, self.scenario, TRIGGER)
        for (pc, frame), geo in zip(frames, EXPECTED_GEOMETRY):
            pc_size, frame_size, spans, pc_pin, frame_pin = geo
            self.assertEqual(len(pc), pc_size)
            self.assertEqual(len(frame), frame_size)
            masked = bytearray(pc)
            for start, end in spans:
                masked[start:end] = b"\x00" * (end - start)
            self.assertEqual(_sha(bytes(masked)), pc_pin)
            masked_frame = bytearray(frame)
            for start, end in spans:
                masked_frame[start + FRAME_COORD_SHIFT:
                             end + FRAME_COORD_SHIFT] = (
                    b"\x00" * (end - start))
            self.assertEqual(_sha(bytes(masked_frame)), frame_pin)

    def test_the_template_pins_are_trigger_independent(self):
        """The masked pin must hold at ANY trigger, or it pins nothing."""
        for trigger in (TRIGGER, (0.0, 0.0, 0.0), (1234.5, -99.25, 7.5)):
            frames = glnp.make_ground_loot_nameprop_frames(
                self.legacy, self.scenario, trigger)
            for (pc, _frame), geo in zip(frames, EXPECTED_GEOMETRY):
                _pc_size, _frame_size, spans, pc_pin, _frame_pin = geo
                masked = bytearray(pc)
                for start, end in spans:
                    masked[start:end] = b"\x00" * (end - start)
                self.assertEqual(_sha(bytes(masked)), pc_pin)

    def test_the_two_frames_differ_by_exactly_the_selector_bytes(self):
        """The single-variable claim, checked on the bytes themselves."""
        (control_pc, _cf), (treatment_pc, _tf) = (
            glnp.make_ground_loot_nameprop_frames(
                self.legacy, self.scenario, TRIGGER))
        # envelope through the element key tag is the same in both
        self.assertEqual(control_pc[:17], treatment_pc[:17])
        # mask byte differs, and only in the expected direction
        self.assertEqual(control_pc[23], CONTROL_MASK)
        self.assertEqual(treatment_pc[23], TREATMENT_MASK)
        # payload dword bytes identical -> same label text
        self.assertEqual(control_pc[24:29], treatment_pc[24:29])
        # coordinates identical -> same pixels
        self.assertEqual(
            b"".join(control_pc[s:e] for s, e in EXPECTED_GEOMETRY[0][2]),
            b"".join(treatment_pc[s:e] for s, e in EXPECTED_GEOMETRY[1][2]),
        )
        # exactly four extra bytes: the gate tag pair and the index tag pair
        self.assertEqual(len(treatment_pc) - len(control_pc), 4)
        self.assertEqual(treatment_pc[29:31], b"\x05\x01")
        self.assertEqual(treatment_pc[46:48], b"\x08\x06")

    def test_the_coordinates_follow_the_trigger_not_any_constant(self):
        for trigger in ((100.0, 200.0, 300.0), (-9000.5, -1.25, 42.0)):
            frames = glnp.make_ground_loot_nameprop_frames(
                self.legacy, self.scenario, trigger)
            for (pc, _frame), spec, geo in zip(
                    frames, EXPECTED_ELEMENTS, EXPECTED_GEOMETRY):
                offset = spec[5]
                spans = geo[2]
                coords = b"".join(pc[s:e] for s, e in spans)
                self.assertEqual(
                    coords,
                    struct.pack(
                        "<fff",
                        _f32(trigger[0] + offset),
                        _f32(trigger[1]),
                        _f32(trigger[2]),
                    ),
                )

    def test_a_non_finite_trigger_refuses_to_compose_by_name(self):
        for bad in ((float("nan"), 0.0, 0.0), (0.0, float("inf"), 0.0)):
            with self.assertRaises(RuntimeError) as caught:
                glnp.make_ground_loot_nameprop_frames(
                    self.legacy, self.scenario, bad)
            self.assertIn("not_finite", str(caught.exception))

    def test_a_malformed_trigger_refuses_to_compose_by_name(self):
        for bad in (("x", 0.0, 0.0), (0.0, 0.0), None):
            with self.assertRaises(RuntimeError) as caught:
                glnp.make_ground_loot_nameprop_frames(
                    self.legacy, self.scenario, bad)
            self.assertIn("trigger_malformed", str(caught.exception))

    def test_an_f32_overflowing_offset_refuses_to_compose_by_name(self):
        with self.assertRaises(RuntimeError) as caught:
            glnp.make_ground_loot_nameprop_frames(
                self.legacy, self.scenario, (3.5e38, 0.0, 0.0))
        self.assertIn("offset_overflow", str(caught.exception))

    def test_the_composer_refuses_a_lookalike_before_composing(self):
        lookalike = glnp.NamePropScenario(
            self.scenario.scenario_id, self.scenario.hypothesis_id,
            self.scenario.elements,
        )
        with self.assertRaises(ValueError) as caught:
            glnp.make_ground_loot_nameprop_frames(
                self.legacy, lookalike, TRIGGER)
        self.assertIn("not_allowlisted", str(caught.exception))

    # ----- the element guards, every one driven ---------------------------

    def _wire(self, **kwargs):
        base = dict(element_key=3, payload_dword=2200423,
                    element_mask=TREATMENT_MASK, property_gate=1,
                    property_index=6, x_offset=30.0, delay=0.0)
        base.update(kwargs)
        return glnp._element_wire(
            self.legacy, glnp.NamePropElement(**base), 1.0, 2.0, 3.0)

    def test_a_zero_gate_element_refuses_by_name(self):
        with self.assertRaises(RuntimeError) as caught:
            self._wire(property_gate=0)
        self.assertIn("gate_is_zero", str(caught.exception))

    def test_an_out_of_range_index_refuses_by_name(self):
        for index in (0, 7, -1, 255):
            with self.assertRaises(RuntimeError) as caught:
                self._wire(property_index=index)
            self.assertIn("index_out_of_range", str(caught.exception))

    def test_a_mask_that_does_not_name_its_gate_refuses_by_name(self):
        with self.assertRaises(RuntimeError) as caught:
            self._wire(element_mask=CONTROL_MASK | 0x20)
        self.assertIn("gate_mask_disagrees", str(caught.exception))

    def test_a_gate_the_mask_does_not_name_refuses_by_name(self):
        with self.assertRaises(RuntimeError) as caught:
            self._wire(element_mask=CONTROL_MASK, property_index=None)
        self.assertIn("gate_mask_disagrees", str(caught.exception))

    def test_a_mask_that_does_not_name_its_index_refuses_by_name(self):
        with self.assertRaises(RuntimeError) as caught:
            self._wire(element_mask=CONTROL_MASK | 0x08)
        self.assertIn("index_mask_disagrees", str(caught.exception))

    def test_the_unsupported_0x04_field_refuses_by_name(self):
        with self.assertRaises(RuntimeError) as caught:
            self._wire(element_mask=TREATMENT_MASK | 0x04)
        self.assertIn("mask_unsupported", str(caught.exception))

    def test_a_mask_missing_dword_or_position_refuses_by_name(self):
        for mask in (0x08 | 0x10 | 0x20, 0x02 | 0x08 | 0x20):
            with self.assertRaises(RuntimeError) as caught:
                self._wire(element_mask=mask)
            self.assertIn("mask_incomplete", str(caught.exception))

    def test_the_control_shape_composes_with_no_selector_bytes(self):
        wire = self._wire(element_mask=CONTROL_MASK, property_gate=None,
                          property_index=None)
        self.assertNotIn(b"\x05", wire[:8])
        self.assertEqual(len(wire), 27)

    def test_a_pin_count_mismatch_refuses_rather_than_truncating(self):
        short = glnp.NamePropScenario(
            self.scenario.scenario_id, self.scenario.hypothesis_id,
            self.scenario.elements[:1],
        )
        glnp._PROFILES["__short__"] = short
        try:
            with self.assertRaises(RuntimeError) as caught:
                glnp.make_ground_loot_nameprop_frames(
                    self.legacy, short, TRIGGER)
            self.assertIn("pin_count_mismatch", str(caught.exception))
        finally:
            del glnp._PROFILES["__short__"]


class NamePropDispatchTests(unittest.TestCase):
    """The real dispatcher, on a throwaway database."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
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
        self.scenario = glnp.load_ground_loot_nameprop_scenario(SCENARIO_PATH)

    def tearDown(self):
        self.tmp.cleanup()

    def _state_type(self, *, lane=True, world_census_actor_count=None):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            ground_loot_nameprop_scenario=(self.scenario if lane else None),
            world_census_actor_count=world_census_actor_count,
        )

    def _state(self, login, *, lane=True, ready=True, select=True,
               world_census_actor_count=None):
        state = self._state_type(
            lane=lane, world_census_actor_count=world_census_actor_count,
        )(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(login)
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

    def _target_pos_pc(self, x, y, z, heading=0.0, moving=1, derived=0):
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.f32tag(x) + self.legacy.f32tag(y)
            + self.legacy.f32tag(z) + self.legacy.f32tag(heading)
            + self.legacy.u8tag(0x0B, moving)
            + self.legacy.u8tag(0x0B, derived)
        )

    def _trigger(self, state, *, derived=0):
        position = state.foundation.selected.position
        return self.legacy.parse_outer(self._target_pos_pc(
            position.x, position.y, position.z, derived=derived,
        ))

    def _trigger_xyz(self, state):
        position = state.foundation.selected.position
        return tuple(
            _f32(value) for value in (position.x, position.y, position.z)
        )

    def _lane_actions(self, actions):
        return [a for a in actions if a[0] in LANE_LABELS]

    def _lane_events(self, state):
        return [e for e in state.events if "nameprop" in e]

    def _table_counts(self):
        db = sqlite3.connect(str(self.db_path))
        try:
            names = [row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            return {
                name: db.execute(
                    'SELECT COUNT(*) FROM "%s"' % name).fetchone()[0]
                for name in names
            }
        finally:
            db.close()

    def test_the_dispatcher_forwards_the_composers_bytes_exactly(self):
        state = self._state("nameprop_exact")
        expected = glnp.make_ground_loot_nameprop_frames(
            self.legacy, self.scenario, self._trigger_xyz(state))
        actions = state.dispatch(self._trigger(state))
        lane = self._lane_actions(actions)
        self.assertEqual([a[0] for a in lane], list(LANE_LABELS))
        for action, (pc, frame) in zip(lane, expected):
            self.assertEqual(action[1], pc)
            self.assertEqual(action[2], frame)
        self.assertEqual([a[3] for a in lane], [0.0, 1.50])
        self.assertEqual(self._lane_events(state).count(PAIR_EVENT), 1)
        self.assertTrue(state.ground_loot_nameprop_sent)

    def test_the_dispatched_lengths_are_the_two_different_shapes(self):
        """54 bytes on BOTH would mean the selector never left the server."""
        state = self._state("nameprop_len")
        lane = self._lane_actions(state.dispatch(self._trigger(state)))
        self.assertEqual(
            [(len(a[1]), len(a[2])) for a in lane], [(44, 54), (48, 58)])

    def test_the_treatment_is_scheduled_clear_of_the_controls_label(self):
        """The offset must clear the measured 0.2-0.4 s label lifetime.

        This asserts the DISPATCHED offset, which is all this layer can see:
        the realized wire gap is that offset minus the control frame's send
        lateness, and nothing in this repository measures it.
        """
        state = self._state("nameprop_gap")
        lane = self._lane_actions(state.dispatch(self._trigger(state)))
        self.assertEqual(lane[0][3], 0.0)
        self.assertGreaterEqual(lane[1][3] - lane[0][3], 1.0)

    def test_the_pair_is_appended_after_the_inherited_actions(self):
        state = self._state("nameprop_tail")
        actions = state.dispatch(self._trigger(state))
        self.assertEqual([a[0] for a in actions[-2:]], list(LANE_LABELS))
        # Containment, asserted here and not only in the census lane's own
        # file: this boot opted into a hypothesis, so it must still receive
        # the frozen three-actor population it was measured against.
        self.assertEqual(
            [a[0] for a in actions if a[0].startswith("WORLD_CENSUS_")], [],
        )
        self.assertIn(
            "V134_P0_P30_P91_ISOLATED_INITIAL_READY",
            [a[0] for a in actions],
        )
        # WORLD-CENSUS-001 moved the control.  A boot with NO lane is no
        # longer the inherited three-actor boot -- it sends the whole bg0001
        # census -- so the control is taken at census rung 3, which is pinned
        # to be the exact frozen P0/P30/P91 collection this lane rides
        # alongside.  The LABEL differs by design and is asserted separately;
        # what this test is here to prove is that the lane displaces nothing
        # on the wire, and that is a statement about bytes.
        control = self._state(
            "nameprop_tail_ctl", lane=False, world_census_actor_count=3,
        )
        control_actions = control.dispatch(self._trigger(control))
        self.assertEqual(
            [a[0] for a in control_actions[-2:]],
            ["WORLD_CENSUS_INITIAL_3", "WORLD_CENSUS_REAPPLY_3"],
        )
        self.assertEqual(
            [(a[1], a[2]) for a in actions[:-2]],
            [(a[1], a[2]) for a in control_actions],
        )

    def test_the_pair_is_one_shot(self):
        state = self._state("nameprop_once")
        state.dispatch(self._trigger(state))
        again = state.dispatch(self._trigger(state))
        self.assertEqual(self._lane_actions(again), [])
        self.assertEqual(self._lane_events(state).count(PAIR_EVENT), 1)

    def test_the_pair_writes_no_database_row(self):
        state = self._state("nameprop_nodb")
        before = self._table_counts()
        state.dispatch(self._trigger(state))
        self.assertEqual(self._table_counts(), before)

    def test_no_socket_action_rides_any_action(self):
        state = self._state("nameprop_nosock")
        for action in state.dispatch(self._trigger(state)):
            self.assertEqual(len(action), 4)

    def test_no_selected_character_fails_closed(self):
        state = self._state("nameprop_nosel", select=False)
        self.assertEqual(
            self._lane_actions(state.dispatch(self.legacy.parse_outer(
                self._target_pos_pc(1.0, 2.0, 3.0)))), [])
        self.assertFalse(state.ground_loot_nameprop_sent)
        self.assertEqual(self._lane_events(state), [])

    def test_not_yet_runtime_ready_fails_closed(self):
        state = self._state("nameprop_notready", ready=False)
        self.assertEqual(self._lane_actions(state.dispatch(
            self._trigger(state))), [])
        self.assertFalse(state.ground_loot_nameprop_sent)
        state.runtime_ack_sent = True
        self.assertEqual(
            [a[0] for a in self._lane_actions(state.dispatch(
                self._trigger(state)))],
            list(LANE_LABELS),
        )

    def test_a_malformed_target_pos_fails_closed(self):
        state = self._state("nameprop_malformed")
        self.assertEqual(self._lane_actions(state.dispatch(
            self._trigger(state, derived=1))), [])
        self.assertFalse(state.ground_loot_nameprop_sent)
        self.assertEqual(
            [a[0] for a in self._lane_actions(state.dispatch(
                self._trigger(state)))],
            list(LANE_LABELS),
        )

    def test_a_drifted_composition_latches_by_name_and_emits_nothing(self):
        original = glnp.GROUND_LOOT_NAMEPROP_GEOMETRY
        broken = glnp.NamePropGeometry(
            original[0].pc_size, original[0].frame_size,
            original[0].coord_spans, "00" * 32,
            original[0].frame_template_sha256,
        )
        glnp.GROUND_LOOT_NAMEPROP_GEOMETRY = (broken, original[1])
        try:
            state = self._state("nameprop_drift")
            actions = state.dispatch(self._trigger(state))
            self.assertEqual(self._lane_actions(actions), [])
            events = self._lane_events(state)
            self.assertEqual(events.count(COMPOSE_REFUSED_EVENT), 1)
            self.assertEqual(events.count(PAIR_EVENT), 0)
            self.assertTrue(state.ground_loot_nameprop_sent)
        finally:
            glnp.GROUND_LOOT_NAMEPROP_GEOMETRY = original
        # the refusal latched: restoring the pin must not let it retry
        self.assertEqual(self._lane_actions(state.dispatch(
            self._trigger(state))), [])

    def test_with_the_scenario_absent_nothing_composes(self):
        state = self._state("nameprop_absent", lane=False)
        actions = state.dispatch(self._trigger(state))
        self.assertEqual(self._lane_actions(actions), [])
        self.assertFalse(state.ground_loot_nameprop_sent)
        self.assertEqual(self._lane_events(state), [])

    def test_the_lane_never_shares_a_boot_with_ground_loot_001(self):
        """The two lanes are the same client parser: never both at once."""
        render = glh.load_ground_loot_hypothesis_scenario(
            RENDER_SCENARIO_PATH)
        with self.assertRaises(ValueError) as caught:
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                ground_loot_hypothesis_scenario=render,
                ground_loot_nameprop_scenario=self.scenario,
            )
        self.assertIn("mutually exclusive", str(caught.exception))

    def test_the_lane_is_refused_alongside_the_allow_listed_pair(self):
        render = glh.load_ground_loot_hypothesis_scenario(
            RENDER_SCENARIO_PATH)
        with self.assertRaises(ValueError) as caught:
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                ground_loot_hypothesis_scenario=render,
                pickup_listener_hypothesis_scenario=object(),
                ground_loot_nameprop_scenario=self.scenario,
            )
        self.assertIn("mutually exclusive", str(caught.exception))

    def test_a_lookalike_profile_cannot_reach_the_dispatcher(self):
        lookalike = glnp.NamePropScenario(
            self.scenario.scenario_id, self.scenario.hypothesis_id,
            self.scenario.elements,
        )
        with self.assertRaises(ValueError) as caught:
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                ground_loot_nameprop_scenario=lookalike,
            )
        self.assertIn("not_allowlisted", str(caught.exception))

    def test_the_ground_loot_001_latch_never_moves(self):
        """HYP-PF-032 must be untouched by this lane, including its latch."""
        state = self._state("nameprop_sibling")
        state.dispatch(self._trigger(state))
        self.assertFalse(state.ground_loot_pair_sent)
        self.assertEqual(
            [e for e in state.events if e == SIBLING_EVENT], [])


class NamePropReplayToolTests(unittest.TestCase):
    """Drive the headless replay tool, so its guard count is executed.

    A proof tool nothing runs is a docstring.  This is the pattern
    tests/test_hostile_hp_link_hypothesis.py already uses for its own lane.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "seed.sqlite3"
        SQLiteStore(self.db_path, ROOT / "migrations").migrate()

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_headless_replay_passes_every_guard(self):
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        completed = subprocess.run(
            [sys.executable, str(REPLAY_TOOL), "--json",
             "--db", str(self.db_path)],
            capture_output=True, text=True, cwd=str(ROOT), env=env,
        )
        self.assertEqual(
            completed.returncode, 0,
            "%s\n%s" % (completed.stdout[-4000:], completed.stderr[-4000:]),
        )
        report = json.loads(completed.stdout)
        self.assertEqual(report["failures"], [])
        # EXACT, not a floor: a floor of 30 lets 17 guards stop running while this
        # test, the ledger entry and the coverage row all keep saying 48.  Sibling
        # lanes pin the count the same way (test_runtimeres_actor_entry_static.py).
        # If a guard is deliberately added or removed, move this number in the same
        # commit and say why.
        self.assertEqual(report["guards"], 48)
        result = report["results"][0]
        self.assertEqual(result["action_labels"], list(LANE_LABELS))
        self.assertEqual(result["scheduler_delays"], [0.0, 1.50])
        self.assertEqual(result["pc_lengths"], [44, 48])
        self.assertEqual(result["frame_lengths"], [54, 58])
        control, treatment = result["walked_frames"]
        self.assertIsNone(control["gate"])
        self.assertIsNone(control["index"])
        self.assertEqual(treatment["gate"], 1)
        self.assertEqual(treatment["index"], 6)
        self.assertEqual(control["dword"], treatment["dword"])
        self.assertEqual(control["position"], treatment["position"])

    def test_the_replay_tool_reports_a_missing_database_rather_than_dying(
            self):
        completed = subprocess.run(
            [sys.executable, str(REPLAY_TOOL),
             "--db", str(Path(self.tmp.name) / "nope.sqlite3")],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        self.assertEqual(completed.returncode, 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
