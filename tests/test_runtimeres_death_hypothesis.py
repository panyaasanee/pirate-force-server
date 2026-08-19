"""RUNTIMERES-ENCODER-001: pin the spawn-then-kill sweep to its exact bytes.

The lane's claim is that three composed ``GSCN_RunTimeProtocolRes`` frames can
drive a KNOWN actor through the client's real engine death chain.  Every part
of that is a statement about bytes, so these tests assert bytes: the complete
hex of all three PCs, the derived change mask, the repeated identity, and the
two sides of the timer polarity.

They also carry SIX TRAP TESTS.  A validator that cannot be made to fail is not
a validator, it is a printout.  Each trap builds a deliberately malformed sweep
and requires ``validate_runtimeres_death_sweep`` to reject it:

  1. the derived change mask bit 0x02 cleared -- the shape that makes the
     client over-read and raise ``ErrorData=28317`` (round 82/85 lesson) AND
     the shape whose +0x1C object is never read, so ``0x446F30`` is never
     reached at all;
  2. a death timer that never reaches ``<= 0`` -- the polarity trap.  A sweep
     that stays positive satisfies ``vt+0x40`` (0x43BDA0, the dying latch) and
     NEVER satisfies ``vt+0x3C`` (0x43BD70), so ``0x443990`` never opens,
     ``CActorTask_Dead`` is never constructed and ``_F_DIE_000`` never plays;
  3. an actor born dead -- an unknown identity takes the spawn 0x446990 ->
     vtable +0x10, which is not a caller of 0x4437C0;
  4. a kill frame re-targeted at a different identity -- that is a second
     spawn, not the vtable +0x20 update the chain needs;
  5. a spawn with no visual preset -- ``[actor+0x70] & 0x40`` at 0x47289E
     never opens, so the actor would latch, get a task, and never animate;
  6. a sweep that re-arms the timer AFTER opening the task gate.

Traps 1 and 2 are the two the task asked for by name.

No socket, no server, no GameClient, no canonical database.  The verifier test
reads the real client image; everything else is pure composition.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import runtimeres_death_hypothesis as rdh  # noqa: E402

SCENARIO = ROOT / "scenarios" / "runtimeres_death_hypothesis_spawn_then_kill.json"
TOOL = ROOT / "tools" / "pf_runtimeres_death_encoder_static.py"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# The complete PC of every frame, byte for byte.  If any of these three strings
# has to change, the change is a wire change and belongs in a report.
EXPECT_PC_HEX = {
    "SPAWN": (
        "129d6e140000000008040b000b021201000b043201200000000000000b02"
        "12d50a0b01320120000000000000120c0314640000001464000000120100"
        "3200000000000000000b05120100482400000050005f004d0041004c0045"
        "005f003000300032005f003000300030005f005300500031001267200b01"
        "3201200000000000000bff2ad4cf0ec62ab9c02dc52ac74a5f432a000000"
        "000b0026000000002a000000002a000000002a00000000"
    ),
    "DYING_LATCH": (
        "129d6e140000000008040b000b021201000b043201200000000000000b01"
        "12d50a0b01320120000000000000128c03140000000014640000002a0000"
        "a0411201003200000000000000000b05120100482400000050005f004d00"
        "41004c0045005f003000300032005f003000300030005f00530050003100"
    ),
    "DEATH_TASK": (
        "129d6e140000000008040b000b021201000b043201200000000000000b01"
        "12d50a0b01320120000000000000128c03140000000014640000002a0000"
        "00001201003200000000000000000b05120100482400000050005f004d00"
        "41004c0045005f003000300032005f003000300030005f00530050003100"
    ),
}

_LEGACY = None
_SWEEP = None


def legacy():
    global _LEGACY
    if _LEGACY is None:
        _LEGACY = load_legacy(LEGACY_PATH)
    return _LEGACY


def sweep():
    """Compose the real sweep once."""
    global _SWEEP
    if _SWEEP is None:
        scenario = rdh.load_runtimeres_death_hypothesis_scenario(SCENARIO)
        unlock = rdh.runtimeres_death_lethal_unlock(scenario)
        probe = rdh.resolve_probe(legacy())
        _SWEEP = (
            scenario, unlock, probe,
            rdh.build_runtimeres_death_sweep(legacy(), probe, unlock, scenario),
        )
    return _SWEEP


def mutated(mutate):
    """A copy of the real sweep with one deliberate defect."""
    _scenario, _unlock, _probe, actions = sweep()
    rows = [list(a) for a in actions]
    mutate(rows)
    return [tuple(r) for r in rows]


class ScenarioAllowlistTests(unittest.TestCase):
    def test_the_shipped_scenario_loads(self):
        scenario = rdh.load_runtimeres_death_hypothesis_scenario(SCENARIO)
        self.assertEqual(scenario.scenario_id, rdh.RUNTIMERES_DEATH_SCENARIO_ID)
        self.assertEqual(scenario.step_order,
                         ("SPAWN", "DYING_LATCH", "DEATH_TASK"))

    def test_the_scenario_file_is_exactly_the_expected_tree(self):
        on_disk = json.loads(SCENARIO.read_text(encoding="utf-8"))
        self.assertEqual(on_disk, json.loads(json.dumps(rdh._expected_scenario())))

    def test_the_lane_is_test_only_and_never_production(self):
        on_disk = json.loads(SCENARIO.read_text(encoding="utf-8"))
        self.assertIs(on_disk["production_allowed"], False)
        self.assertIs(on_disk["test_only"], True)
        self.assertIs(on_disk["lethal"], True)
        self.assertIs(rdh.production_allowed, False)

    def test_the_scenario_agrees_with_the_ledger_about_registration(self):
        # Round 86: the HYP-PF-023 append landed, so the flag flipped to True.
        # It must stay honest in BOTH directions -- the file may not claim an
        # id the ledger does not carry, and may not deny one it does.
        on_disk = json.loads(SCENARIO.read_text(encoding="utf-8"))
        self.assertIs(on_disk["hypothesis_id_is_registered_in_the_ledger"], True)
        ledger = json.loads(
            (ROOT / "docs" / "HYPOTHESIS_LEDGER.json").read_text(encoding="utf-8")
        )
        self.assertIn(
            rdh.RUNTIMERES_DEATH_HYPOTHESIS_ID,
            {entry["id"] for entry in ledger["entries"]},
        )

    def test_the_loader_rejects_every_single_key_edit(self, ):
        base = rdh._expected_scenario()
        variants = {
            "extra key": lambda d: d.update(extra=1),
            "missing key": lambda d: d.pop("lethal"),
            "production allowed": lambda d: d.update(production_allowed=True),
            "not test only": lambda d: d.update(test_only=False),
            "renamed id": lambda d: d.update(id="something_else"),
            "wrong hypothesis id": lambda d: d.update(hypothesis_id="HYP-PF-001"),
            "nested extra key": lambda d: d["wire"].update(sneaky=1),
            "nested value": lambda d: d["wire"].update(derived_change_mask=0),
            "polarity flipped": lambda d: d["wire"]["polarity"].update(
                death_task_value_seconds=99.0),
            "pin edited": lambda d: d["probe"]["per_step"]["DEATH_TASK"].update(
                pc_size=1),
        }
        for label, mutate in variants.items():
            with self.subTest(variant=label):
                data = json.loads(json.dumps(base))
                mutate(data)
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "s.json"
                    path.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        rdh.load_runtimeres_death_hypothesis_scenario(path)

    def test_the_loader_rejects_a_file_that_is_not_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            path.write_text("not json at all", encoding="utf-8")
            with self.assertRaises(ValueError):
                rdh.load_runtimeres_death_hypothesis_scenario(path)

    def test_the_scenario_object_allowlist_refuses_a_lookalike(self):
        fake = rdh.RuntimeResDeathHypothesisScenario(
            rdh.RUNTIMERES_DEATH_SCENARIO_ID,
            rdh.RUNTIMERES_DEATH_HYPOTHESIS_ID,
            ("SPAWN", "DEATH_TASK"), 6.0, 0.0,
            rdh.RUNTIMERES_DEATH_ACTION_LABEL_PREFIX,
        )
        with self.assertRaises(ValueError):
            rdh.require_runtimeres_death_hypothesis_scenario(fake)
        with self.assertRaises(ValueError):
            rdh.require_runtimeres_death_hypothesis_scenario(object())


class FailClosedTests(unittest.TestCase):
    def test_the_encoder_refuses_bit_0x0080_without_the_lethal_unlock(self):
        _scenario, _unlock, probe, _actions = sweep()
        with self.assertRaises(ValueError):
            rdh.encode_death_capable_npc_attr(
                legacy(), probe, current_hp=0, death_timer=0.0,
            )
        for impostor in (None, object(), "unlock", rdh.RuntimeResDeathLethalUnlock(
                rdh.RUNTIMERES_DEATH_SCENARIO_ID,
                rdh.RUNTIMERES_DEATH_HYPOTHESIS_ID)):
            with self.subTest(impostor=type(impostor).__name__):
                with self.assertRaises(ValueError):
                    rdh.encode_death_capable_npc_attr(
                        legacy(), probe, current_hp=0, death_timer=0.0,
                        lethal=impostor,
                    )

    def test_the_unlock_cannot_be_derived_from_anything_but_the_scenario(self):
        with self.assertRaises(ValueError):
            rdh.runtimeres_death_lethal_unlock(object())
        with self.assertRaises(ValueError):
            rdh.runtimeres_death_lethal_unlock(None)

    def test_the_timerless_body_reproduces_the_frozen_projection(self):
        _scenario, _unlock, probe, _actions = sweep()
        widened = rdh.encode_death_capable_npc_attr(
            legacy(), probe, current_hp=rdh.RUNTIMERES_DEATH_HP_ALIVE,
        )
        frozen = legacy().make_npc_attr(
            probe.template_id, probe.actor_identity, probe.scene_id,
            probe.scene_sequence, probe.visual_preset,
            rdh.RUNTIMERES_DEATH_HP_ALIVE, rdh.RUNTIMERES_DEATH_HP_MAX,
        )
        self.assertEqual(widened, frozen)

    def test_the_lethal_body_is_the_frozen_body_plus_exactly_five_bytes(self):
        _scenario, unlock, probe, _actions = sweep()
        frozen = legacy().make_npc_attr(
            probe.template_id, probe.actor_identity, probe.scene_id,
            probe.scene_sequence, probe.visual_preset, 0,
            rdh.RUNTIMERES_DEATH_HP_MAX,
        )
        lethal = rdh.encode_death_capable_npc_attr(
            legacy(), probe, current_hp=0, death_timer=0.0, lethal=unlock,
        )
        self.assertEqual(len(lethal), len(frozen) + 5)
        self.assertIn(bytes([rdh.DEATH_TIMER_TAG]) + struct.pack("<f", 0.0),
                      lethal)

    def test_the_probe_comes_from_the_frozen_placement_source(self):
        _scenario, _unlock, probe, _actions = sweep()
        self.assertEqual(probe.placement_index,
                         rdh.RUNTIMERES_DEATH_PROBE_PLACEMENT_INDEX)
        self.assertEqual(probe.actor_identity,
                         rdh.RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY)
        self.assertEqual(probe.visual_preset,
                         rdh.RUNTIMERES_DEATH_PROBE_VISUAL_PRESET)
        self.assertTrue(probe.visual_preset)


class WireShapeTests(unittest.TestCase):
    """The bytes themselves.  This is the headless wire proof."""

    def test_the_sweep_is_three_labelled_frames_in_the_pinned_order(self):
        scenario, _unlock, _probe, actions = sweep()
        self.assertEqual([a[0] for a in actions],
                         list(rdh.RUNTIMERES_DEATH_ACTION_LABELS))
        self.assertEqual([a[3] for a in actions], [0.0, 6.0, 6.0])
        self.assertEqual(scenario.step_order, rdh.RUNTIMERES_DEATH_STEP_ORDER)

    def test_every_frame_is_byte_for_byte_the_expected_pc(self):
        _scenario, _unlock, _probe, actions = sweep()
        for index, label in enumerate(rdh.RUNTIMERES_DEATH_STEP_ORDER):
            with self.subTest(step=label):
                self.assertEqual(actions[index][1].hex(),
                                 EXPECT_PC_HEX[label])

    def test_every_frame_matches_its_pinned_hashes(self):
        _scenario, scen_unlock, _probe, actions = sweep()
        for index, label in enumerate(rdh.RUNTIMERES_DEATH_STEP_ORDER):
            pin = rdh.RUNTIMERES_DEATH_PINS[label]
            with self.subTest(step=label):
                self.assertEqual(len(actions[index][1]), pin["pc_size"])
                self.assertEqual(len(actions[index][2]), pin["frame_size"])

    def test_requirement_1_id_0x6e9d_derived_mask_0x02_object_0x1c(self):
        _scenario, _unlock, _probe, actions = sweep()
        for label, pc, _frame, _delay in actions:
            with self.subTest(step=label):
                self.assertEqual(pc[0], 0x12)
                self.assertEqual(int.from_bytes(pc[1:3], "little"), 0x6E9D)
                self.assertEqual(pc[9], rdh.RUNTIME_PROTOCOL_RES_VERSION)
                # the INHERITED (VitalData, +0x18) collection is absent...
                self.assertEqual(pc[rdh.INHERITED_CHANGE_MASK_OFFSET],
                                 rdh.INHERITED_CHANGE_MASK_ABSENT)
                # ...and the DERIVED mask selects the +0x1C actor entries.
                self.assertEqual(pc[rdh.DERIVED_CHANGE_MASK_OFFSET],
                                 rdh.DERIVED_CHANGE_MASK_ACTOR_ENTRIES)
                self.assertEqual(rdh.DERIVED_CHANGE_MASK_OBJECT_OFFSET, 0x1C)

    def test_requirement_2_spawn_first_kill_second_same_identity(self):
        _scenario, _unlock, probe, actions = sweep()
        read = [rdh.decode_runtimeres_actor_entry_frame(a[1]) for a in actions]
        self.assertEqual({r["identity"] for r in read}, {probe.actor_identity})
        self.assertEqual(read[0]["attrs"][rdh.NPC_ATTR_ID]["fields"][0x0004],
                         rdh.RUNTIMERES_DEATH_HP_ALIVE)
        self.assertNotIn(0x0080, read[0]["attrs"][rdh.NPC_ATTR_ID]["fields"])
        self.assertIn(rdh.MOVEMENT_ATTR_ID, read[0]["attrs"])
        for row in read[1:]:
            self.assertEqual(row["attrs"][rdh.NPC_ATTR_ID]["fields"][0x0004], 0)
            self.assertNotIn(rdh.MOVEMENT_ATTR_ID, row["attrs"])

    def test_requirement_3_the_polarity_and_that_the_sweep_reaches_le_zero(self):
        scenario, _unlock, _probe, actions = sweep()
        rows = rdh.validate_runtimeres_death_sweep(list(actions), scenario)
        # vtable +0x40 (0x43BDA0): HP == 0 AND timer > 0  -> the DYING latch
        self.assertTrue(rows[1]["dying_latch_predicate_vt40"])
        self.assertFalse(rows[1]["death_task_predicate_vt3c"])
        self.assertEqual(rows[1]["death_timer_bit_0x0080"],
                         rdh.DYING_LATCH_TIMER_SECONDS)
        self.assertGreater(rows[1]["death_timer_bit_0x0080"], 0.0)
        # vtable +0x3C (0x43BD70): HP == 0 AND timer <= 0 -> CActorTask_Dead
        self.assertTrue(rows[2]["death_task_predicate_vt3c"])
        self.assertFalse(rows[2]["dying_latch_predicate_vt40"])
        self.assertLessEqual(rows[2]["death_timer_bit_0x0080"],
                             rdh.DEATH_TASK_TIMER_CEILING)
        # and the constants say which slot each side gates
        self.assertEqual(rdh.DYING_LATCH_PREDICATE_VA, 0x43BDA0)
        self.assertEqual(rdh.DEATH_TASK_PREDICATE_VA, 0x43BD70)

    def test_the_actor_type_is_the_cnetnpc_jump_table_case(self):
        _scenario, _unlock, _probe, actions = sweep()
        for _label, pc, _frame, _delay in actions:
            read = rdh.decode_runtimeres_actor_entry_frame(pc)
            self.assertEqual(read["actor_type"], 4)
            self.assertEqual(read["actor_type"], rdh.NPC_STYLE_ACTOR_TYPE)

    def test_every_frame_is_frame_pc_of_its_own_pc(self):
        _scenario, _unlock, _probe, actions = sweep()
        for label, pc, frame, _delay in actions:
            with self.subTest(step=label):
                self.assertEqual(frame, legacy().frame_pc(pc))


class TrapTests(unittest.TestCase):
    """A validator that cannot be made to fail is not a validator."""

    def _reject(self, mutate, because):
        """Reject, AND reject for the stated reason.

        A trap that passes because the validator tripped over something else
        is not testing the guard it claims to test, so every trap here pins the
        message it expects.
        """
        scenario, _unlock, _probe, _actions = sweep()
        bad = mutated(mutate)
        with self.assertRaises(rdh.RuntimeResDeathValidationError) as ctx:
            rdh.validate_runtimeres_death_sweep(bad, scenario)
        self.assertIn(because, str(ctx.exception))

    def test_positive_control_the_untouched_sweep_validates(self):
        scenario, _unlock, _probe, actions = sweep()
        rows = rdh.validate_runtimeres_death_sweep(list(actions), scenario)
        self.assertEqual(len(rows), 3)

    # ---- TRAP 1: the missing 0x02 derived change mask ---------------------
    def test_trap_missing_the_0x02_derived_change_mask(self):
        def mutate(rows):
            pc = bytearray(rows[2][1])
            pc[rdh.DERIVED_CHANGE_MASK_OFFSET] = 0x00
            rows[2][1] = bytes(pc)
        self._reject(mutate, "missing bit 0x02")

    def test_trap_the_derived_mask_set_to_a_neighbouring_bit(self):
        """0x04 selects +0x24, a completely different sub-object."""
        def mutate(rows):
            pc = bytearray(rows[2][1])
            pc[rdh.DERIVED_CHANGE_MASK_OFFSET] = 0x04
            rows[2][1] = bytes(pc)
        self._reject(mutate, "missing bit 0x02")

    # ---- TRAP 2: a timer that never reaches <= 0 --------------------------
    def test_trap_a_timer_that_never_reaches_le_zero(self):
        def mutate(rows):
            pc = bytearray(rows[2][1])
            off = pc.find(bytes([0x2A]) + struct.pack("<f", 0.0))
            assert off > 0
            pc[off + 1:off + 5] = struct.pack("<f", 5.0)
            rows[2][1] = bytes(pc)
        self._reject(mutate, "never reaches <= 0")

    def test_trap_a_sweep_that_re_arms_the_timer_after_the_task_gate(self):
        """Frames swapped: <= 0 first, then positive again."""
        def mutate(rows):
            rows[1][1], rows[2][1] = rows[2][1], rows[1][1]
        self._reject(mutate, "re-arms the timer after opening the task gate")

    # ---- TRAP 3: an actor born dead ---------------------------------------
    def test_trap_an_actor_born_dead(self):
        def mutate(rows):
            rows[0][1] = rows[2][1]
        self._reject(mutate, "an actor cannot be born dead")

    # ---- TRAP 4: the kill frame aimed at a different identity -------------
    def test_trap_a_kill_frame_aimed_at_a_different_identity(self):
        """Both identities in the frame are moved, so the validator has to
        reject on 'this is not the spawned actor', not on an internal
        inconsistency it would have caught anyway."""
        old = struct.pack("<Q", rdh.RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY)
        new = struct.pack("<Q", rdh.RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY + 1)

        def mutate(rows):
            pc = rows[2][1]
            self.assertEqual(pc.count(old), 2)
            rows[2][1] = pc.replace(old, new)
        self._reject(mutate, "that is a second spawn")

    def test_trap_the_entry_and_attr_identities_disagreeing(self):
        old = struct.pack("<Q", rdh.RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY)
        new = struct.pack("<Q", rdh.RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY + 1)

        def mutate(rows):
            pc = bytearray(rows[2][1])
            pc[20:28] = new
            self.assertEqual(bytes(pc).count(old), 1)
            rows[2][1] = bytes(pc)
        self._reject(mutate, "would target different actors")

    # ---- TRAP 5: no visual preset -----------------------------------------
    def test_trap_a_frame_with_no_visual_preset(self):
        """No preset -> [actor+0x70] & 0x40 never opens -> no animation."""
        _scenario, _unlock, probe, _actions = sweep()
        naked = rdh.RuntimeResDeathProbe(
            probe.placement_index, probe.template_id, probe.actor_identity,
            probe.x, probe.y, probe.z, "", probe.source_name,
            probe.scene_id, probe.scene_sequence,
        )
        body = rdh.encode_death_capable_npc_attr(
            legacy(), naked, current_hp=rdh.RUNTIMERES_DEATH_HP_ALIVE,
        )
        movement = legacy().make_remote_movement_attr(
            naked.actor_identity, naked.x, naked.y, naked.z, 0.0,
            mask=rdh.FULL_MOVEMENT_MASK,
        )
        entry = legacy().make_remote_actor_entry(
            4, naked.actor_identity,
            [(rdh.NPC_ATTR_ID, body), (rdh.MOVEMENT_ATTR_ID, movement)],
        )
        pc, _frame = legacy().make_runtime_remote_actors([entry])

        def mutate(rows):
            rows[0][1] = pc
        self._reject(mutate, "carries no visual preset")

    # ---- structural traps -------------------------------------------------
    def test_trap_a_truncated_frame(self):
        def mutate(rows):
            rows[2][1] = rows[2][1][:-4]
        self._reject(mutate, "truncated")

    def test_trap_the_wrong_number_of_frames(self):
        scenario, _unlock, _probe, actions = sweep()
        with self.assertRaises(rdh.RuntimeResDeathValidationError) as ctx:
            rdh.validate_runtimeres_death_sweep(list(actions[:2]), scenario)
        self.assertIn("exactly 3 frames", str(ctx.exception))

    def test_trap_a_relabelled_step(self):
        def mutate(rows):
            rows[2][0] = "HYP_PF_023_RUNTIMERES_DEATH_SOMETHING_ELSE"
        self._reject(mutate, "expected")

    def test_trap_the_wrong_envelope_id(self):
        def mutate(rows):
            pc = bytearray(rows[1][1])
            pc[1:3] = (0x309A).to_bytes(2, "little")   # UpdateAttrVital
            rows[1][1] = bytes(pc)
        self._reject(mutate, "does not open with GSCN_RunTimeProtocolRes")

    def test_trap_the_wrong_actor_type(self):
        def mutate(rows):
            pc = bytearray(rows[2][1])
            pc[18] = 9   # outside the 2..6 jump table
            rows[2][1] = bytes(pc)
        self._reject(mutate, "outside the 2..6 jump table")

    def test_trap_the_kill_frame_dropping_the_death_timer(self):
        _scenario, _unlock, probe, _actions = sweep()
        body = rdh.encode_death_capable_npc_attr(legacy(), probe, current_hp=0)
        entry = legacy().make_remote_actor_entry(
            4, probe.actor_identity, [(rdh.NPC_ATTR_ID, body)],
        )
        pc, _frame = legacy().make_runtime_remote_actors([entry])

        def mutate(rows):
            rows[2][1] = pc
        self._reject(mutate, "omits the death timer")


class AppWiringTests(unittest.TestCase):
    def test_the_flag_exists_and_refuses_to_boot_while_unwired(self):
        """app.py must not start a server that would answer nothing."""
        from pirateforce_foundation import app
        from pirateforce_foundation.runtime import make_state_class
        import inspect

        wired = rdh.RUNTIMERES_DEATH_DISPATCH_KWARG in (
            inspect.signature(make_state_class).parameters
        )
        saved = sys.argv[:]
        try:
            sys.argv = [
                "app.py",
                "--db", str(ROOT / "state" / "does_not_exist_for_this_test.sqlite3"),
                "--runtimeres-death-hypothesis-scenario", str(SCENARIO),
            ]
            if wired:
                self.skipTest("runtime.py now carries the dispatcher branch")
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                with self.assertRaises(SystemExit) as ctx:
                    app.main()
            self.assertEqual(ctx.exception.code, 2)
            self.assertIn("no frame would ever be dispatched", buf.getvalue())
        finally:
            sys.argv = saved

    def test_the_flag_is_mutually_exclusive_with_the_hp_death_lane(self):
        from pirateforce_foundation import app
        saved = sys.argv[:]
        try:
            sys.argv = [
                "app.py", "--db", "x",
                "--runtimeres-death-hypothesis-scenario", str(SCENARIO),
                "--hp-death-hypothesis-scenario",
                str(ROOT / "scenarios" / "hp_death_hypothesis_death_sweep.json"),
            ]
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                with self.assertRaises(SystemExit):
                    app.main()
            self.assertIn("mutually exclusive", buf.getvalue())
        finally:
            sys.argv = saved


class VerifierTests(unittest.TestCase):
    """Run the real verifier against the real image."""

    def test_the_verifier_runs_clean_and_opens_its_regression_gate(self):
        if not _client_image_present():
            self.skipTest("GameClient.local.bin is not available here")
        spec = importlib.util.spec_from_file_location(
            "pf_runtimeres_death_encoder_static", TOOL)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(module)   # SystemExit here == a red guard
        self.assertEqual(module.FAILS, [])
        self.assertEqual(module.REGRESSION_FAILS, [])
        self.assertGreaterEqual(module.REGRESSION_GUARDS, 20)
        self.assertGreater(module.NGUARD, module.REGRESSION_GUARDS)

    def test_the_verifier_needs_no_third_party_package(self):
        source = TOOL.read_text(encoding="utf-8")
        for banned in ("capstone", "pefile", "numpy", "yaml", "requests"):
            self.assertNotIn("import " + banned, source)


LATCH_ONLY_SCENARIO = (
    ROOT / "scenarios" / "runtimeres_death_hypothesis_dying_latch_only.json"
)


class DyingLatchOnlyProfileTests(unittest.TestCase):
    """RUNTIMERES-LATCHONLY-001 (round 91): the two-frame tie-breaker.

    GT-022 put a real corpse on a real client -- the probe NPC went from
    standing to lying flat and stayed there -- and could NOT say which frame
    did it.  DYING_LATCH lands at t+6 and DEATH_TASK at t+12; the photographs
    that caught the pose sit about one second from that boundary and capture
    latency was never instrumented, so attributing the pose to either frame is
    an argument about an unmeasured clock.

    A sweep that STOPS after DYING_LATCH removes the clock from the question
    entirely.  If the pose still appears, it belongs to the latch.  If it does
    not, it belongs to the death task.  That only works if the two frames it
    does send are the SAME BYTES the three-frame profile sends, which is what
    most of the tests below are about: the experiment is decisive only while
    the absent third frame is the only difference between the two runs.

    Nothing here has been shown to a client.  This is the test, not the answer.
    """

    def latch_only(self):
        profile = rdh.load_runtimeres_death_hypothesis_scenario(
            LATCH_ONLY_SCENARIO,
        )
        unlock = rdh.runtimeres_death_lethal_unlock(profile)
        probe = rdh.resolve_probe(legacy())
        actions = rdh.build_runtimeres_death_sweep(
            legacy(), probe, unlock, profile,
        )
        return profile, unlock, probe, actions

    def test_the_shipped_two_frame_scenario_loads_as_its_own_profile(self):
        profile, _unlock, _probe, _actions = self.latch_only()
        self.assertEqual(profile.scenario_id,
                         rdh.RUNTIMERES_DEATH_LATCH_ONLY_SCENARIO_ID)
        self.assertEqual(profile.profile_name,
                         rdh.RUNTIMERES_DEATH_PROFILE_DYING_LATCH_ONLY)
        self.assertEqual(profile.step_order, ("SPAWN", "DYING_LATCH"))
        self.assertEqual(profile.lethal_step_labels, ("DYING_LATCH",))
        self.assertIs(profile.ends_on_death_task, False)

    def test_the_two_frame_file_is_exactly_the_expected_tree(self):
        on_disk = json.loads(LATCH_ONLY_SCENARIO.read_text(encoding="utf-8"))
        self.assertEqual(on_disk, json.loads(json.dumps(
            rdh._expected_scenario(rdh._PROFILE_LATCH_ONLY))))
        self.assertIs(on_disk["production_allowed"], False)
        self.assertIs(on_disk["test_only"], True)
        self.assertIs(on_disk["lethal"], True)
        self.assertIs(on_disk["dispatch"]["ends_on_death_task"], False)
        self.assertEqual(on_disk["dispatch"]["frames_per_accepted_request"], 2)

    def test_the_two_frames_are_the_three_frame_sweeps_first_two(self):
        """THE load-bearing test of this profile.

        Byte identity, compared on the bytes objects themselves rather than on
        a hash summary.  If these two frames were merely similar, a difference
        seen on a screen would prove nothing about which frame causes what.
        """
        _scenario, _unlock, _probe, three = sweep()
        _p, _u, _pr, two = self.latch_only()
        self.assertEqual(len(two), 2)
        self.assertEqual(list(two), list(three[:2]))
        for index in range(2):
            label_a, pc_a, frame_a, delay_a = three[index]
            label_b, pc_b, frame_b, delay_b = two[index]
            with self.subTest(step=label_a):
                self.assertEqual(label_a, label_b)
                self.assertEqual(pc_a, pc_b)
                self.assertEqual(frame_a, frame_b)
                self.assertEqual(delay_a, delay_b)

    def test_the_two_profiles_share_the_very_same_step_rows(self):
        """Structural, not incidental: a slice cannot be edited on one side."""
        self.assertIs(rdh.RUNTIMERES_DEATH_LATCH_ONLY_STEPS[0],
                      rdh.RUNTIMERES_DEATH_STEPS[0])
        self.assertIs(rdh.RUNTIMERES_DEATH_LATCH_ONLY_STEPS[1],
                      rdh.RUNTIMERES_DEATH_STEPS[1])
        self.assertEqual(len(rdh.RUNTIMERES_DEATH_LATCH_ONLY_STEPS), 2)

    def test_no_frame_of_it_opens_the_death_task_gate(self):
        profile, _unlock, _probe, actions = self.latch_only()
        rows = rdh.validate_runtimeres_death_sweep(actions, profile)
        self.assertEqual([row["death_task_predicate_vt3c"] for row in rows],
                         [False, False])
        self.assertIs(rows[-1]["dying_latch_predicate_vt40"], True)
        self.assertEqual(rows[1]["death_timer_bit_0x0080"], 20.0)
        self.assertIsNone(rows[0]["death_timer_bit_0x0080"])

    def test_an_unlock_issued_for_one_profile_does_not_open_the_other(self):
        three_unlock = rdh.runtimeres_death_lethal_unlock(
            rdh.load_runtimeres_death_hypothesis_scenario(SCENARIO))
        two_unlock = rdh.runtimeres_death_lethal_unlock(
            rdh.load_runtimeres_death_hypothesis_scenario(LATCH_ONLY_SCENARIO))
        self.assertIsNot(three_unlock, two_unlock)
        probe = rdh.resolve_probe(legacy())
        for unlock, profile, name in (
            (three_unlock, rdh._PROFILE_LATCH_ONLY, "three key, two lane"),
            (two_unlock, rdh._PROFILE, "two key, three lane"),
        ):
            with self.subTest(case=name):
                with self.assertRaises(ValueError):
                    rdh.build_runtimeres_death_sweep(
                        legacy(), probe, unlock, profile,
                    )

    def test_a_value_equal_forged_unlock_still_opens_nothing(self):
        forged = rdh.RuntimeResDeathLethalUnlock(
            rdh.RUNTIMERES_DEATH_LATCH_ONLY_SCENARIO_ID,
            rdh.RUNTIMERES_DEATH_HYPOTHESIS_ID,
        )
        self.assertEqual(forged, rdh._UNLOCK_LATCH_ONLY)   # equal by value
        self.assertIsNot(forged, rdh._UNLOCK_LATCH_ONLY)   # not by identity
        with self.assertRaises(ValueError):
            rdh.build_runtimeres_death_sweep(
                legacy(), rdh.resolve_probe(legacy()), forged,
                rdh._PROFILE_LATCH_ONLY,
            )

    def test_a_file_that_names_one_profile_and_carries_the_other_is_refused(
        self,
    ):
        """The id picks which tree to compare against; it decides nothing."""
        body = rdh._expected_scenario(rdh._PROFILE)
        body["id"] = rdh.RUNTIMERES_DEATH_LATCH_ONLY_SCENARIO_ID
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            path.write_text(json.dumps(body), encoding="utf-8")
            with self.assertRaises(ValueError):
                rdh.load_runtimeres_death_hypothesis_scenario(path)

    def test_the_loader_rejects_every_single_key_edit_here_too(self):
        base = rdh._expected_scenario(rdh._PROFILE_LATCH_ONLY)
        variants = {
            "ends on death task flipped": lambda d: d["dispatch"].update(
                ends_on_death_task=True),
            "third step smuggled in": lambda d: d["dispatch"]["step_order"]
            .append("DEATH_TASK"),
            "frame count widened": lambda d: d["dispatch"].update(
                frames_per_accepted_request=3),
            "timer taken to zero": lambda d: d["wire"]["polarity"].update(
                dying_latch_value_seconds=0.0),
            "profile renamed": lambda d: d.update(profile="spawn_then_kill"),
        }
        for label, mutate in variants.items():
            with self.subTest(variant=label):
                data = json.loads(json.dumps(base))
                mutate(data)
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "s.json"
                    path.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        rdh.load_runtimeres_death_hypothesis_scenario(path)

    def test_trap_a_profile_that_ends_on_the_latch_but_reaches_the_gate(self):
        """A rule nobody can reach through a shipped file is still a rule.

        The shipped two-frame profile CANNOT open the task gate, so the
        validator branch that refuses one is unreachable from the scenarios
        directory.  It is reached here by registering a forged profile on the
        allowlist for the duration of the assertion and restoring it in a
        finally, because a branch that has never been seen to fire is not a
        guard.  The restore is asserted, by identity, at the end.
        """
        forged = rdh.RuntimeResDeathHypothesisScenario(
            "runtimeres_death_hypothesis_forged_latch_only",
            rdh.RUNTIMERES_DEATH_HYPOTHESIS_ID,
            ("SPAWN", "DYING_LATCH", "DEATH_TASK"),
            rdh.RUNTIMERES_DEATH_SPACING_SECONDS,
            rdh.RUNTIMERES_DEATH_FIRST_DELAY_SECONDS,
            rdh.RUNTIMERES_DEATH_ACTION_LABEL_PREFIX,
            "forged_latch_only",
            ("DYING_LATCH", "DEATH_TASK"),
            False,                      # claims it never reaches the gate
        )
        saved_profiles = rdh._ALLOWED_PROFILES
        saved_unlocks = dict(rdh._UNLOCKS)
        try:
            rdh._ALLOWED_PROFILES = saved_profiles + (forged,)
            rdh._UNLOCKS[forged.scenario_id] = rdh.RuntimeResDeathLethalUnlock(
                forged.scenario_id, forged.hypothesis_id,
            )
            with self.assertRaises(rdh.RuntimeResDeathValidationError):
                rdh.build_runtimeres_death_sweep(
                    legacy(), rdh.resolve_probe(legacy()),
                    rdh._UNLOCKS[forged.scenario_id], forged,
                )
        finally:
            rdh._ALLOWED_PROFILES = saved_profiles
            rdh._UNLOCKS.clear()
            rdh._UNLOCKS.update(saved_unlocks)
        self.assertEqual(len(rdh._ALLOWED_PROFILES), 2)
        self.assertIs(rdh._ALLOWED_PROFILES[0], rdh._PROFILE)
        self.assertIs(rdh._ALLOWED_PROFILES[1], rdh._PROFILE_LATCH_ONLY)
        self.assertEqual(set(rdh._UNLOCKS), {
            rdh.RUNTIMERES_DEATH_SCENARIO_ID,
            rdh.RUNTIMERES_DEATH_LATCH_ONLY_SCENARIO_ID,
        })
        # And the real thing still composes after the allowlist was handled.
        self.assertEqual(len(self.latch_only()[3]), 2)


def _client_image_present() -> bool:
    for cand in (
        ROOT.parent / "GameClient" / "GameClient.local.bin",
        ROOT / "GameClient" / "GameClient.local.bin",
        ROOT / "packages" / ".v134_staging_20260815_0355"
        / "GameClient.local.bin",
    ):
        if cand.is_file():
            return True
    return False


if __name__ == "__main__":
    unittest.main()
