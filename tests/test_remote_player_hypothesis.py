"""REMOTE-PLAYER-ENCODER-001 (HYP-PF-025): pin the visibility sweep to its bytes.

The lane's claim is that five composed ``GSCN_RunTimeProtocolRes`` frames can
put ``actor_type 2`` (``CNetActor``, the remote-player branch of the client's
actor factory) in front of a real client for the first time in this project's
history.  Every part of that is a statement about bytes, so these tests assert
bytes: the pinned sizes and hashes of the four fully-pinned frames, the
SPAWN_AVATAR skeleton pin, the shared BasicAttr prefix against the frozen
``make_npc_attr`` oracle, and the exact-allowlist scenario file.

They also carry TRAP TESTS.  A validator that cannot be made to fail is not a
validator, it is a printout: every refusal in the encoder's ladder is entered
by name, the independent walker is fed hand-mutated frames (a second actor
entry, a flipped version byte, a set inherited mask, a wrong derived mask, a
truncated and a padded frame, a smuggled CMyActor-only skill attr, an avatar
tail that is not last), the sweep validator is fed off-plan sweeps, and the
byte pins are monkeypatched to prove the composer refuses its own drift.

Nothing here claims a client renders anything.  That is the attended test's
question; this file only proves the bytes are exactly the designed experiment.

No socket, no server, no GameClient, no canonical database.  Pure composition.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.actor_wire import (  # noqa: E402
    bind_common_attr_identity,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.population import (  # noqa: E402
    load_port_royal_placements,
)
from pirateforce_foundation import remote_player_hypothesis as rph  # noqa: E402

SCENARIO = ROOT / "scenarios" / "remote_player_hypothesis_visibility_probe.json"
MODULE = ROOT / "src" / "pirateforce_foundation" / "remote_player_hypothesis.py"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# Two SYNTHETIC avatar tails.  Both satisfy the proven common-Attr prefix the
# encoder checks (0x0B, identity bit 0x01, identity tag 0x32, >= 11 bytes);
# past the identity they are deliberately different bytes of different
# lengths, because the skeleton pin's whole claim is that the composed part
# of SPAWN_AVATAR does not depend on the opaque tail.
AVATAR_TAIL_ONE = (
    bytes([0x0B, 0x01, 0x32]) + (0x1111).to_bytes(8, "little")
    + bytes([0x05, 0x01, 0x14, 0x2A, 0x00, 0x00, 0x00])
)
AVATAR_TAIL_TWO = (
    bytes([0x0B, 0x01, 0x32]) + (0x2222).to_bytes(8, "little")
    + bytes([0x05, 0x01, 0x14, 0x2A, 0x00, 0x00, 0x00, 0x0B, 0x07])
)
# A plausible selected-character identity (the character space starts at
# 0x10000000) that collides with none of the three probes.
SELECTED_IDENTITY = 0x10000001

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
        scenario = rph.load_remote_player_hypothesis_scenario(SCENARIO)
        unlock = rph.remote_player_wire_unlock(scenario)
        probes = rph.resolve_probes(legacy())
        actions = rph.build_remote_player_sweep(
            legacy(), probes, unlock, scenario,
            avatar_wire=AVATAR_TAIL_ONE, selected_identity=SELECTED_IDENTITY,
        )
        _SWEEP = (scenario, unlock, probes, actions)
    return _SWEEP


def mutated(mutate):
    """A copy of the real sweep with one deliberate defect."""
    _scenario, _unlock, _probes, actions = sweep()
    rows = [list(a) for a in actions]
    mutate(rows)
    return [tuple(r) for r in rows]


def by_role(probes):
    return {probe.role: probe for probe in probes}


class ScenarioAllowlistTests(unittest.TestCase):
    def test_the_shipped_scenario_loads(self):
        scenario = rph.load_remote_player_hypothesis_scenario(SCENARIO)
        self.assertEqual(scenario.scenario_id, rph.REMOTE_PLAYER_SCENARIO_ID)
        self.assertEqual(scenario.hypothesis_id, "HYP-PF-025")
        self.assertEqual(scenario.step_order, (
            "SPAWN_BARE", "SPAWN_AVATAR", "MOVE_A_1", "MOVE_A_2",
            "NEGATIVE_CONTROL",
        ))
        self.assertEqual(scenario.spacing_seconds, 15.0)
        self.assertEqual(scenario.first_delay_seconds, 0.0)

    def test_the_scenario_file_is_exactly_the_expected_tree(self):
        on_disk = json.loads(SCENARIO.read_text(encoding="utf-8"))
        self.assertEqual(
            on_disk, json.loads(json.dumps(rph._expected_scenario()))
        )

    def test_the_lane_is_test_only_and_never_production(self):
        on_disk = json.loads(SCENARIO.read_text(encoding="utf-8"))
        self.assertIs(on_disk["production_allowed"], False)
        self.assertIs(on_disk["test_only"], True)
        self.assertIs(rph.production_allowed, False)

    def test_the_module_source_carries_the_ledger_marker_line(self):
        source = MODULE.read_text(encoding="utf-8")
        self.assertEqual(
            source.count("PF-HYPOTHESIS-LEDGER: HYP-PF-025 active"), 1,
        )
        self.assertEqual(rph.REMOTE_PLAYER_HYPOTHESIS_ID, "HYP-PF-025")

    def test_the_loader_rejects_every_single_key_edit(self):
        base = rph._expected_scenario()
        variants = {
            "extra key": lambda d: d.update(extra=1),
            "missing key": lambda d: d.pop("persisted_post_state"),
            "production allowed": lambda d: d.update(production_allowed=True),
            "not test only": lambda d: d.update(test_only=False),
            "renamed id": lambda d: d.update(id="something_else"),
            "wrong hypothesis id": lambda d: d.update(
                hypothesis_id="HYP-PF-023"),
            "nested extra key": lambda d: d["wire"].update(sneaky=1),
            "actor type widened": lambda d: d["wire"].update(actor_type=4),
            "movement mask widened": lambda d: d["wire"]["movement_masks"]
            .append(7),
            "value type changed": lambda d: d["dispatch"].update(
                spacing_seconds="15.0"),
            "int turned bool": lambda d: d["probe"].update(hp_alive=True),
            "step order flipped": lambda d: d["dispatch"]["step_order"]
            .reverse(),
            "pin edited": lambda d: d["probe"]["per_step"]["MOVE_A_1"].update(
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
                        rph.load_remote_player_hypothesis_scenario(path)

    def test_the_loader_rejects_a_file_that_is_not_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            path.write_text("not json at all", encoding="utf-8")
            with self.assertRaises(ValueError):
                rph.load_remote_player_hypothesis_scenario(path)

    def test_the_scenario_object_allowlist_refuses_a_lookalike(self):
        lookalike = rph.RemotePlayerHypothesisScenario(
            rph.REMOTE_PLAYER_SCENARIO_ID,
            rph.REMOTE_PLAYER_HYPOTHESIS_ID,
            ("SPAWN_BARE", "SPAWN_AVATAR"), 6.0, 0.0,
            rph.REMOTE_PLAYER_ACTION_LABEL_PREFIX,
        )
        for candidate in (lookalike, object(), None,
                          rph.REMOTE_PLAYER_SCENARIO_ID):
            with self.subTest(candidate=type(candidate).__name__):
                with self.assertRaises(ValueError):
                    rph.require_remote_player_hypothesis_scenario(candidate)


class WireUnlockTests(unittest.TestCase):
    def test_the_unlock_cannot_be_derived_from_anything_but_the_scenario(self):
        for candidate in (object(), None, rph.REMOTE_PLAYER_SCENARIO_ID):
            with self.subTest(candidate=type(candidate).__name__):
                with self.assertRaises(ValueError):
                    rph.remote_player_wire_unlock(candidate)

    def test_the_unlock_derived_from_the_scenario_is_the_one_token(self):
        scenario, unlock, _probes, _actions = sweep()
        self.assertIs(unlock, rph.remote_player_wire_unlock(scenario))
        self.assertIs(unlock, rph.require_remote_player_wire_unlock(unlock))

    def test_a_value_equal_forged_wire_unlock_opens_nothing(self):
        """The unlock is compared by identity, so equality is not enough."""
        scenario, real, probes, _actions = sweep()
        forged = rph.RemotePlayerWireUnlock(
            rph.REMOTE_PLAYER_SCENARIO_ID, rph.REMOTE_PLAYER_HYPOTHESIS_ID,
        )
        self.assertEqual(forged, real)      # equal by value
        self.assertIsNot(forged, real)      # not by identity
        outcome = None
        with self.assertRaises(ValueError) as ctx:
            outcome = rph.encode_remote_player_actor_attr(
                legacy(), probes[0], forged,
            )
        self.assertIn("missing_or_forged_wire_unlock", str(ctx.exception))
        self.assertIsNone(outcome)
        outcome = None
        with self.assertRaises(ValueError):
            outcome = rph.build_remote_player_sweep(
                legacy(), probes, forged, scenario,
                avatar_wire=AVATAR_TAIL_ONE,
                selected_identity=SELECTED_IDENTITY,
            )
        self.assertIsNone(outcome)

    def test_nothing_composes_without_a_wire_unlock_at_all(self):
        _scenario, _unlock, probes, _actions = sweep()
        for impostor in (None, object(), "unlock", 1):
            with self.subTest(impostor=type(impostor).__name__):
                outcome = None
                with self.assertRaises(ValueError) as ctx:
                    outcome = rph.encode_remote_player_entry(
                        legacy(), "SPAWN_BARE", probes[0], impostor,
                    )
                self.assertIn(
                    "missing_or_forged_wire_unlock", str(ctx.exception),
                )
                self.assertIsNone(outcome)


class ResolveProbesTests(unittest.TestCase):
    def test_resolve_probes_returns_the_three_pinned_roles(self):
        _scenario, _unlock, probes, _actions = sweep()
        self.assertEqual(len(probes), 3)
        roles = by_role(probes)
        self.assertEqual(sorted(roles), ["A", "B", "C"])
        self.assertEqual(roles["A"].identity, rph.PROBE_IDENTITY_A)
        self.assertEqual(roles["B"].identity, rph.PROBE_IDENTITY_B)
        self.assertEqual(roles["C"].identity, rph.PROBE_IDENTITY_C)
        self.assertEqual(roles["A"].name, "ProbePlayer01")
        self.assertEqual(roles["B"].name, "ProbePlayer02")
        self.assertEqual(roles["C"].name, "ProbeControl03")

    def test_the_probes_anchor_at_the_pinned_placement_zero(self):
        _scenario, _unlock, probes, _actions = sweep()
        roles = by_role(probes)
        placements = load_port_royal_placements(legacy())
        anchor = next(
            p for p in placements
            if p.placement_index == rph.REMOTE_PLAYER_ANCHOR_PLACEMENT_INDEX
        )
        self.assertEqual(anchor.placement_index, 0)
        self.assertEqual(anchor.template_id, 1)
        self.assertEqual(anchor.visual_preset, "P_MALE_002_000_SP1")
        self.assertEqual(anchor.source_name, "Navy Transfer")
        self.assertEqual(
            anchor.source_name, rph.REMOTE_PLAYER_ANCHOR_SOURCE_NAME,
        )
        for probe in probes:
            with self.subTest(role=probe.role):
                self.assertEqual(probe.anchor_placement_index, 0)
                self.assertEqual(probe.anchor_template_id, 1)
                self.assertEqual(
                    probe.anchor_visual_preset, "P_MALE_002_000_SP1",
                )
                self.assertEqual(probe.y, anchor.y)
                self.assertEqual(probe.z, anchor.z)
        self.assertEqual(roles["A"].x, anchor.x)

    def test_the_x_offsets_are_plus_and_minus_150_from_the_anchor(self):
        _scenario, _unlock, probes, _actions = sweep()
        roles = by_role(probes)
        self.assertEqual(roles["B"].x, roles["A"].x + 150.0)
        self.assertEqual(roles["C"].x, roles["A"].x - 150.0)
        self.assertEqual(rph.PROBE_B_X_OFFSET, 150.0)
        self.assertEqual(rph.PROBE_C_X_OFFSET, -150.0)
        for probe in probes:
            with self.subTest(role=probe.role):
                self.assertEqual(probe.scene_id, 1)
                self.assertEqual(probe.scene_sequence, 0)


class WireShapeTests(unittest.TestCase):
    """The bytes themselves.  This is the headless wire proof."""

    def test_the_sweep_is_five_labelled_frames_in_the_pinned_order(self):
        _scenario, _unlock, _probes, actions = sweep()
        self.assertEqual(len(actions), 5)
        self.assertEqual(
            [a[0] for a in actions], list(rph.REMOTE_PLAYER_ACTION_LABELS),
        )
        self.assertEqual(
            [a[3] for a in actions], [0.0, 15.0, 15.0, 15.0, 15.0],
        )
        self.assertEqual(rph.REMOTE_PLAYER_STEP_ORDER, (
            "SPAWN_BARE", "SPAWN_AVATAR", "MOVE_A_1", "MOVE_A_2",
            "NEGATIVE_CONTROL",
        ))

    def test_every_pc_re_reads_through_the_independent_walker(self):
        _scenario, _unlock, probes, actions = sweep()
        roles = by_role(probes)
        expected_role = {
            "SPAWN_BARE": "A", "SPAWN_AVATAR": "B", "MOVE_A_1": "A",
            "MOVE_A_2": "A", "NEGATIVE_CONTROL": "C",
        }
        for index, step in enumerate(rph.REMOTE_PLAYER_STEP_ORDER):
            with self.subTest(step=step):
                read = rph.decode_remote_player_actor_entry_frame(
                    actions[index][1]
                )
                self.assertEqual(read["actor_type"], 2)
                self.assertEqual(
                    read["actor_type"], rph.REMOTE_PLAYER_ACTOR_TYPE,
                )
                self.assertEqual(
                    read["identity"], roles[expected_role[step]].identity,
                )

    def test_every_fully_pinned_frame_matches_its_pinned_hashes(self):
        _scenario, _unlock, _probes, actions = sweep()
        for index, step in enumerate(rph.REMOTE_PLAYER_STEP_ORDER):
            if step == "SPAWN_AVATAR":
                continue
            pin = rph.REMOTE_PLAYER_PINS[step]
            _label, pc, frame, _delay = actions[index]
            with self.subTest(step=step):
                self.assertEqual(len(pc), pin["pc_size"])
                self.assertEqual(len(frame), pin["frame_size"])
                self.assertEqual(
                    hashlib.sha256(pc).hexdigest().upper(), pin["pc_sha256"],
                )
                self.assertEqual(
                    hashlib.sha256(frame).hexdigest().upper(),
                    pin["frame_sha256"],
                )

    def test_the_pins_equal_the_scenario_files_per_step_exactly(self):
        on_disk = json.loads(SCENARIO.read_text(encoding="utf-8"))
        per_step = on_disk["probe"]["per_step"]
        self.assertEqual(set(per_step), set(rph.REMOTE_PLAYER_PINS))
        for step, pin in rph.REMOTE_PLAYER_PINS.items():
            with self.subTest(step=step):
                self.assertEqual(per_step[step], pin)

    def test_every_frame_is_frame_pc_of_its_own_pc(self):
        _scenario, _unlock, _probes, actions = sweep()
        for label, pc, frame, _delay in actions:
            with self.subTest(step=label):
                self.assertEqual(frame, legacy().frame_pc(pc))

    def test_the_envelope_is_0x6e9d_v4_with_the_pinned_masks(self):
        _scenario, _unlock, _probes, actions = sweep()
        for label, pc, _frame, _delay in actions:
            with self.subTest(step=label):
                self.assertEqual(pc[0], 0x12)
                self.assertEqual(int.from_bytes(pc[1:3], "little"), 0x6E9D)
                self.assertEqual(pc[9], rph.RUNTIME_PROTOCOL_RES_VERSION)
                self.assertEqual(
                    pc[rph.INHERITED_CHANGE_MASK_OFFSET],
                    rph.INHERITED_CHANGE_MASK_ABSENT,
                )
                self.assertEqual(
                    pc[rph.DERIVED_CHANGE_MASK_OFFSET],
                    rph.DERIVED_CHANGE_MASK_ACTOR_ENTRIES,
                )
                self.assertEqual(int.from_bytes(
                    pc[rph.ACTOR_ENTRY_COUNT_OFFSET:
                       rph.ACTOR_ENTRY_COUNT_OFFSET + 2], "little",
                ), 1)

    def test_the_masks_on_the_wire_are_the_pinned_ones(self):
        _scenario, _unlock, _probes, actions = sweep()
        expected_movement = {
            "SPAWN_BARE": 0xFF, "SPAWN_AVATAR": 0xFF, "MOVE_A_1": 0x01,
            "MOVE_A_2": 0x03, "NEGATIVE_CONTROL": 0xFF,
        }
        for index, step in enumerate(rph.REMOTE_PLAYER_STEP_ORDER):
            read = rph.decode_remote_player_actor_entry_frame(
                actions[index][1]
            )
            with self.subTest(step=step):
                movement = read["attrs"][rph.MOVEMENT_ATTR_ID]
                self.assertEqual(movement["mask"], expected_movement[step])
                if step in ("SPAWN_BARE", "SPAWN_AVATAR"):
                    actor = read["attrs"][rph.ACTOR_ATTR_ID]
                    self.assertEqual(actor["basic_mask"], 0x030D)
                    self.assertEqual(actor["actor_mask"], 0)
                    self.assertEqual(actor["extra_group"], 1)

    def test_the_move_frames_carry_exactly_one_movement_attr(self):
        _scenario, _unlock, _probes, actions = sweep()
        for index in (2, 3):
            read = rph.decode_remote_player_actor_entry_frame(
                actions[index][1]
            )
            with self.subTest(step=rph.REMOTE_PLAYER_STEP_ORDER[index]):
                self.assertEqual(
                    read["attr_order"], (rph.MOVEMENT_ATTR_ID,),
                )

    def test_the_negative_control_ships_the_frozen_npc_body(self):
        _scenario, _unlock, probes, actions = sweep()
        control = by_role(probes)["C"]
        read = rph.decode_remote_player_actor_entry_frame(actions[4][1])
        npc = read["attrs"][rph.NPC_ATTR_ID]
        self.assertEqual(npc["identity"], control.identity)
        self.assertEqual(npc["template_id"], 1)
        self.assertEqual(npc["visual_preset"], "P_MALE_002_000_SP1")
        self.assertEqual(npc["fields"][rph.BASIC_BIT_NAME], control.name)
        # And it is a straight call into the frozen serializer.
        self.assertEqual(actions[4][1].count(legacy().make_npc_attr(
            control.anchor_template_id, control.identity, control.scene_id,
            control.scene_sequence, control.anchor_visual_preset,
            rph.REMOTE_PLAYER_HP_ALIVE, rph.REMOTE_PLAYER_HP_MAX,
            None, control.name,
        )), 1)

    def test_the_validator_rows_reproduce_every_pin(self):
        scenario, _unlock, probes, actions = sweep()
        rows = rph.validate_remote_player_sweep(
            list(actions), scenario, probes,
        )
        self.assertEqual(len(rows), 5)
        for index, step in enumerate(rph.REMOTE_PLAYER_STEP_ORDER):
            pin = rph.REMOTE_PLAYER_PINS[step]
            with self.subTest(step=step):
                for key, expected in pin.items():
                    self.assertEqual(rows[index].get(key), expected, key)


class OracleTests(unittest.TestCase):
    """BasicAttr::Serial 0x4656F0 runs first on BOTH attr classes, so the
    frozen, client-proven make_npc_attr body is a free oracle for the new
    ActorAttr prefix."""

    def test_the_basic_prefix_reproduces_make_npc_attr_byte_for_byte(self):
        _scenario, unlock, probes, _actions = sweep()
        roles = by_role(probes)
        for role in ("A", "B"):
            probe = roles[role]
            with self.subTest(probe=role):
                body = rph.encode_remote_player_actor_attr(
                    legacy(), probe, unlock,
                )
                # The ActorAttr suffix is the 9-byte 64-bit mask tag plus the
                # 2-byte extra-group tag; everything before it is BasicAttr.
                self.assertEqual(body[-11:-2], legacy().qwordtag(0x32, 0))
                self.assertEqual(body[-2:], legacy().u8tag(0x05, 1))
                prefix = body[:-11]
                self.assertGreater(len(prefix), 40)
                baseline = legacy().make_npc_attr(
                    probe.anchor_template_id, probe.identity, probe.scene_id,
                    probe.scene_sequence, "", rph.REMOTE_PLAYER_HP_ALIVE,
                    rph.REMOTE_PLAYER_HP_MAX, None, probe.name,
                )
                self.assertEqual(bytes(baseline[:len(prefix)]), prefix)

    def test_the_oracle_guard_itself_refuses_a_drifted_prefix(self):
        _scenario, unlock, probes, _actions = sweep()
        probe = probes[0]
        body = rph.encode_remote_player_actor_attr(legacy(), probe, unlock)
        drifted = bytearray(body[:-11])
        drifted[12] ^= 0xFF
        with self.assertRaises(ValueError) as ctx:
            rph._require_basic_prefix_matches_make_npc_attr(
                legacy(), bytes(drifted), probe,
                rph.REMOTE_PLAYER_HP_ALIVE, rph.REMOTE_PLAYER_HP_MAX,
            )
        self.assertIn(
            "basic_prefix_does_not_reproduce_make_npc_attr",
            str(ctx.exception),
        )


class SkeletonPinTests(unittest.TestCase):
    """SPAWN_AVATAR's tail is opaque per-character database bytes, so its pin
    covers the frame SKELETON only -- and that must be provably tail-blind."""

    def _spawn_avatar_pc(self, tail):
        scenario, unlock, probes, _actions = sweep()
        pc, frame = rph.make_remote_player_step_response(
            legacy(), probes, 1, unlock, scenario, avatar_wire=tail,
        )
        self.assertEqual(frame, legacy().frame_pc(pc))
        return pc

    def test_two_different_avatar_tails_share_one_pinned_skeleton(self):
        pin = rph.REMOTE_PLAYER_PINS["SPAWN_AVATAR"]
        self.assertIs(pin["avatar_tail_excluded_from_pin"], True)
        self.assertNotIn("pc_sha256", pin)
        self.assertNotIn("frame_sha256", pin)
        pc_one = self._spawn_avatar_pc(AVATAR_TAIL_ONE)
        pc_two = self._spawn_avatar_pc(AVATAR_TAIL_TWO)
        self.assertNotEqual(pc_one, pc_two)
        skeleton_one = pc_one[:len(pc_one) - len(AVATAR_TAIL_ONE)]
        skeleton_two = pc_two[:len(pc_two) - len(AVATAR_TAIL_TWO)]
        self.assertEqual(skeleton_one, skeleton_two)
        self.assertEqual(len(skeleton_one), pin["pc_skeleton_size"])
        self.assertEqual(
            hashlib.sha256(skeleton_one).hexdigest().upper(),
            pin["pc_skeleton_sha256"],
        )

    def test_the_avatar_tail_is_the_last_attr_with_identity_b(self):
        for tail in (AVATAR_TAIL_ONE, AVATAR_TAIL_TWO):
            with self.subTest(tail_size=len(tail)):
                pc = self._spawn_avatar_pc(tail)
                read = rph.decode_remote_player_actor_entry_frame(pc)
                self.assertEqual(read["attr_order"][-1], rph.AVATAR_ATTR_ID)
                avatar = read["attrs"][rph.AVATAR_ATTR_ID]
                self.assertEqual(avatar["identity"], rph.PROBE_IDENTITY_B)
                self.assertEqual(avatar["body_size"], len(tail))
                # The tail on the wire is the input tail with ONLY the
                # identity rebound; everything opaque is byte-preserved.
                self.assertEqual(
                    pc[-len(tail):],
                    bind_common_attr_identity(
                        tail, rph.PROBE_IDENTITY_B & 0xFFFFFFFF,
                        rph.PROBE_IDENTITY_B >> 32,
                    ),
                )


class RefusalLadderTests(unittest.TestCase):
    """One test per named refusal.  Nothing may be returned on any of them."""

    def _refuses(self, reason, fn, *args, **kwargs):
        outcome = None
        with self.assertRaises(ValueError) as ctx:
            outcome = fn(*args, **kwargs)
        self.assertIn(reason, str(ctx.exception))
        self.assertIsNone(outcome)

    def test_refusal_actor_type_not_the_remote_player_branch(self):
        _scenario, unlock, probes, _actions = sweep()
        roles = by_role(probes)
        for actor_type, label, role in (
            (4, "MOVE_A_1", "A"), (5, "SPAWN_BARE", "A"),
            (6, "MOVE_A_2", "A"), (5, "NEGATIVE_CONTROL", "C"),
        ):
            with self.subTest(actor_type=actor_type, step=label):
                self._refuses(
                    "actor_type_not_the_remote_player_branch",
                    rph.encode_remote_player_entry,
                    legacy(), label, roles[role], unlock,
                    actor_type=actor_type,
                )

    def test_refusal_actor_type_outside_client_jump_table(self):
        _scenario, unlock, probes, _actions = sweep()
        for actor_type in (0, 1, 7, True):
            with self.subTest(actor_type=repr(actor_type)):
                self._refuses(
                    "actor_type_outside_client_jump_table",
                    rph.encode_remote_player_entry,
                    legacy(), "SPAWN_BARE", probes[0], unlock,
                    actor_type=actor_type,
                )

    def test_refusal_actor_type_3_would_claim_the_local_player_slot(self):
        _scenario, unlock, probes, _actions = sweep()
        self._refuses(
            "actor_type_3_would_claim_the_local_player_slot",
            rph.encode_remote_player_entry,
            legacy(), "SPAWN_BARE", probes[0], unlock, actor_type=3,
        )

    def test_refusal_actor_attr_inside_actor_type_4_entry(self):
        _scenario, unlock, probes, _actions = sweep()
        roles = by_role(probes)
        for label, role in (("SPAWN_BARE", "A"), ("SPAWN_AVATAR", "B")):
            with self.subTest(step=label):
                self._refuses(
                    "actor_attr_inside_actor_type_4_entry",
                    rph.encode_remote_player_entry,
                    legacy(), label, roles[role], unlock, actor_type=4,
                    avatar_wire=AVATAR_TAIL_ONE,
                )

    def test_refusal_hp_zero_would_cross_into_the_death_chain(self):
        _scenario, unlock, probes, _actions = sweep()
        for current_hp in (0, -1, -100, "100"):
            with self.subTest(current_hp=repr(current_hp)):
                self._refuses(
                    "hp_zero_would_cross_into_the_death_chain",
                    rph.encode_remote_player_actor_attr,
                    legacy(), probes[0], unlock, current_hp=current_hp,
                )

    def test_refusal_death_timer_bit_is_not_this_lanes_field(self):
        _scenario, unlock, probes, _actions = sweep()
        for basic_mask in (rph.BASIC_MASK_PROBE | 0x0080, 0x0080):
            with self.subTest(basic_mask=hex(basic_mask)):
                self._refuses(
                    "death_timer_bit_is_not_this_lanes_field",
                    rph.encode_remote_player_actor_attr,
                    legacy(), probes[0], unlock, basic_mask=basic_mask,
                )

    def test_refusal_basic_mask_is_not_the_pinned_probe_mask(self):
        _scenario, unlock, probes, _actions = sweep()
        for basic_mask in (0x030C, 0x0305, 0x0001, "mask", True):
            with self.subTest(basic_mask=repr(basic_mask)):
                self._refuses(
                    "basic_mask_is_not_the_pinned_probe_mask",
                    rph.encode_remote_player_actor_attr,
                    legacy(), probes[0], unlock, basic_mask=basic_mask,
                )

    def test_refusal_actor_attr_mask_high_half_not_implemented(self):
        _scenario, unlock, probes, _actions = sweep()
        for actor_mask in (1 << 32, 1 << 63):
            with self.subTest(actor_mask=hex(actor_mask)):
                self._refuses(
                    "actor_attr_mask_high_half_not_implemented",
                    rph.encode_remote_player_actor_attr,
                    legacy(), probes[0], unlock, actor_mask=actor_mask,
                )

    def test_refusal_actor_attr_mask_is_not_the_pinned_probe_mask(self):
        _scenario, unlock, probes, _actions = sweep()
        for actor_mask in (1, 2, (1 << 32) - 1):
            with self.subTest(actor_mask=hex(actor_mask)):
                self._refuses(
                    "actor_attr_mask_is_not_the_pinned_probe_mask",
                    rph.encode_remote_player_actor_attr,
                    legacy(), probes[0], unlock, actor_mask=actor_mask,
                )

    def test_refusal_actor_attr_extra_group_flag_not_one(self):
        _scenario, unlock, probes, _actions = sweep()
        for value in (0, 2):
            with self.subTest(value=value):
                self._refuses(
                    "actor_attr_extra_group_flag_not_one",
                    rph.encode_remote_player_actor_attr,
                    legacy(), probes[0], unlock, extra_group_value=value,
                )

    def test_refusal_character_name_not_encodable_as_utf16le(self):
        _scenario, unlock, probes, _actions = sweep()
        for name in ("", "\ud800", b"bytes"):
            with self.subTest(name=repr(name)):
                broken = dataclasses.replace(probes[0], name=name)
                self._refuses(
                    "character_name_not_encodable_as_utf16le",
                    rph.encode_remote_player_actor_attr,
                    legacy(), broken, unlock,
                )

    def test_refusal_movement_position_not_finite_float32(self):
        _scenario, unlock, probes, _actions = sweep()
        for field, value in (
            ("x", float("nan")), ("y", float("inf")),
            ("z", float("-inf")), ("x", 3.5e38),
        ):
            with self.subTest(field=field, value=repr(value)):
                broken = dataclasses.replace(probes[0], **{field: value})
                self._refuses(
                    "movement_position_not_finite_float32",
                    rph.encode_remote_player_entry,
                    legacy(), "SPAWN_BARE", broken, unlock,
                )

    def test_refusal_movement_mask_outside_the_pinned_set(self):
        _scenario, _unlock, probes, _actions = sweep()
        probe = probes[0]
        for mask in (0x00, 0x02, 0x07, True):
            with self.subTest(mask=repr(mask)):
                self._refuses(
                    "movement_mask_outside_the_pinned_set",
                    rph._make_movement_attr,
                    legacy(), probe, mask, probe.x, probe.y, probe.z, 0.0,
                )

    def test_refusal_avatar_wire_absent_or_not_a_common_attr_body(self):
        _scenario, unlock, probes, _actions = sweep()
        probe_b = by_role(probes)["B"]
        for wire in (
            None,
            b"",
            b"\x0c" + AVATAR_TAIL_ONE[1:],            # wrong first byte
            bytes([0x0B, 0x02]) + AVATAR_TAIL_ONE[2:],  # identity bit clear
            AVATAR_TAIL_ONE[:10],                     # shorter than 11
        ):
            with self.subTest(wire=repr(wire)[:32]):
                self._refuses(
                    "avatar_wire_absent_or_not_a_common_attr_body",
                    rph.encode_remote_player_entry,
                    legacy(), "SPAWN_AVATAR", probe_b, unlock,
                    avatar_wire=wire,
                )

    def test_refusal_probe_identity_collides_with_the_selected_character(self):
        scenario, unlock, probes, _actions = sweep()
        for selected in (
            rph.PROBE_IDENTITY_A, rph.PROBE_IDENTITY_B,
            rph.PROBE_IDENTITY_C, None, True,
        ):
            with self.subTest(selected=repr(selected)):
                self._refuses(
                    "probe_identity_collides_with_the_selected_character",
                    rph.build_remote_player_sweep,
                    legacy(), probes, unlock, scenario,
                    avatar_wire=AVATAR_TAIL_ONE, selected_identity=selected,
                )

    def test_refusal_unknown_step_label(self):
        _scenario, unlock, probes, _actions = sweep()
        for label in ("SPAWN", 99, -1, True, 1.0):
            with self.subTest(label=repr(label)):
                self._refuses(
                    "unknown_step_label",
                    rph.encode_remote_player_entry,
                    legacy(), label, probes[0], unlock,
                )

    def test_refusal_unknown_step_index(self):
        scenario, unlock, probes, _actions = sweep()
        for index in (99, -1, True, 1.0):
            with self.subTest(index=repr(index)):
                self._refuses(
                    "unknown_step_label",
                    rph.make_remote_player_step_response,
                    legacy(), probes, index, unlock, scenario,
                )

    def test_refusal_probe_object_is_not_the_typed_probe(self):
        scenario, unlock, probes, _actions = sweep()
        real = probes[0]
        lookalike = (
            real.role, real.identity, real.name, real.x, real.y, real.z,
            real.scene_id, real.scene_sequence, real.anchor_placement_index,
            real.anchor_template_id, real.anchor_visual_preset,
        )
        for impostor in (lookalike, None):
            with self.subTest(impostor=type(impostor).__name__):
                self._refuses(
                    "probe_object_is_not_the_typed_probe",
                    rph.encode_remote_player_entry,
                    legacy(), "SPAWN_BARE", impostor, unlock,
                )
        # And the sweep composer refuses the same drift inside its list.
        self._refuses(
            "probe_object_is_not_the_typed_probe",
            rph.build_remote_player_sweep,
            legacy(), (lookalike, probes[1], probes[2]), unlock, scenario,
            avatar_wire=AVATAR_TAIL_ONE, selected_identity=SELECTED_IDENTITY,
        )


class WalkerTrapTests(unittest.TestCase):
    """Hand-mutated frames against the independent tag walker."""

    def _walker_rejects(self, pc, because):
        with self.assertRaises(rph.RemotePlayerValidationError) as ctx:
            rph.decode_remote_player_actor_entry_frame(pc)
        self.assertIn(because, str(ctx.exception))

    def test_trap_the_actor_entry_count_flipped_to_two(self):
        _scenario, _unlock, _probes, actions = sweep()
        pc = bytearray(actions[0][1])
        self.assertEqual(pc[rph.ACTOR_ENTRY_COUNT_OFFSET], 1)
        pc[rph.ACTOR_ENTRY_COUNT_OFFSET] = 2
        self._walker_rejects(bytes(pc), "actor_entry_count_not_one")

    def test_trap_the_version_byte_flipped(self):
        _scenario, _unlock, _probes, actions = sweep()
        pc = bytearray(actions[3][1])
        self.assertEqual(pc[9], rph.RUNTIME_PROTOCOL_RES_VERSION)
        pc[9] = 5
        self._walker_rejects(bytes(pc), "envelope_id_or_version_not_pinned")

    def test_trap_the_envelope_id_flipped(self):
        _scenario, _unlock, _probes, actions = sweep()
        pc = bytearray(actions[0][1])
        pc[1:3] = (0x309A).to_bytes(2, "little")   # UpdateAttrVital
        self._walker_rejects(bytes(pc), "envelope_id_or_version_not_pinned")

    def test_trap_the_inherited_change_mask_set(self):
        _scenario, _unlock, _probes, actions = sweep()
        pc = bytearray(actions[0][1])
        self.assertEqual(pc[rph.INHERITED_CHANGE_MASK_OFFSET], 0x00)
        pc[rph.INHERITED_CHANGE_MASK_OFFSET] = 0x01
        self._walker_rejects(bytes(pc), "inherited_change_mask_not_zero")

    def test_trap_the_derived_change_mask_off_the_actor_entry_bit(self):
        _scenario, _unlock, _probes, actions = sweep()
        for wrong in (0x00, 0x04):
            with self.subTest(mask=hex(wrong)):
                pc = bytearray(actions[0][1])
                self.assertEqual(pc[rph.DERIVED_CHANGE_MASK_OFFSET], 0x02)
                pc[rph.DERIVED_CHANGE_MASK_OFFSET] = wrong
                self._walker_rejects(
                    bytes(pc), "derived_change_mask_not_the_actor_entry_bit",
                )

    def test_trap_a_truncated_frame(self):
        """Cut the control frame inside its trailing preset wstring (and drop
        its second attr from the count) so the walker's cursor runs past the
        end -- the one shape that reaches the truncation message rather than
        a field-level tag error."""
        _scenario, _unlock, _probes, actions = sweep()
        pc = bytearray(actions[4][1])
        preset = rph.REMOTE_PLAYER_ANCHOR_VISUAL_PRESET.encode("utf-16le")
        offset = bytes(pc).find(preset)
        self.assertGreater(offset, 0)
        self.assertEqual(bytes(pc).count(preset), 1)
        self.assertEqual(pc[28], 0x0B)   # per-entry attr count tag
        self.assertEqual(pc[29], 2)      # NPCAttr + MovementAttr
        pc[29] = 1
        truncated = bytes(pc[:offset + len(preset) - 6])
        self._walker_rejects(truncated, "truncated")

    def test_trap_a_frame_with_trailing_bytes(self):
        _scenario, _unlock, _probes, actions = sweep()
        padded = actions[2][1] + b"\x00\x00\x00\x00"
        self._walker_rejects(padded, "trailing bytes")

    def test_trap_a_smuggled_my_actor_only_skill_attr(self):
        """Attr id 0x1661 binds through 0x4698B0, which gates on CMyActor."""
        _scenario, _unlock, _probes, actions = sweep()
        pc = bytearray(actions[2][1])
        self.assertEqual(pc[30], 0x12)
        self.assertEqual(
            pc[31:33], rph.MOVEMENT_ATTR_ID.to_bytes(2, "little"),
        )
        pc[31:33] = rph.SKILL_ATTR_ID.to_bytes(2, "little")
        self._walker_rejects(bytes(pc), "skill_attr_is_my_actor_only")

    def test_trap_an_avatar_tail_that_is_not_the_last_attr(self):
        """Hand-build an entry with the avatar id tag BEFORE MovementAttr:
        an opaque body anywhere but the tail has no findable boundary."""
        _scenario, unlock, probes, _actions = sweep()
        probe_b = by_role(probes)["B"]
        actor_body = rph.encode_remote_player_actor_attr(
            legacy(), probe_b, unlock,
        )
        movement = legacy().make_remote_movement_attr(
            probe_b.identity, probe_b.x, probe_b.y, probe_b.z, 0.0, mask=0xFF,
        )
        avatar = bind_common_attr_identity(
            AVATAR_TAIL_ONE, probe_b.identity & 0xFFFFFFFF,
            probe_b.identity >> 32,
        )
        entry = legacy().make_remote_actor_entry(
            rph.REMOTE_PLAYER_ACTOR_TYPE, probe_b.identity,
            [
                (rph.ACTOR_ATTR_ID, actor_body),
                (rph.AVATAR_ATTR_ID, avatar),
                (rph.MOVEMENT_ATTR_ID, movement),
            ],
        )
        pc, _frame = legacy().make_runtime_remote_actors([entry])
        self._walker_rejects(pc, "LAST attr")


class ValidatorTrapTests(unittest.TestCase):
    """A validator that cannot be made to fail is not a validator."""

    def _reject(self, mutate, because):
        scenario, _unlock, probes, _actions = sweep()
        bad = mutated(mutate)
        with self.assertRaises(rph.RemotePlayerValidationError) as ctx:
            rph.validate_remote_player_sweep(bad, scenario, probes)
        self.assertIn(because, str(ctx.exception))

    def test_positive_control_the_untouched_sweep_validates(self):
        scenario, _unlock, probes, actions = sweep()
        rows = rph.validate_remote_player_sweep(
            list(actions), scenario, probes,
        )
        self.assertEqual(len(rows), 5)

    def test_trap_a_wrong_delay(self):
        def mutate(rows):
            rows[1][3] = 6.0
        self._reject(mutate, "step_order_or_delay_not_pinned")

    def test_trap_an_integer_delay_lookalike(self):
        """15 is not 15.0: the delay is typed, not coerced."""
        def mutate(rows):
            rows[2][3] = 15
        self._reject(mutate, "step_order_or_delay_not_pinned")

    def test_trap_a_relabelled_step(self):
        def mutate(rows):
            rows[2][0] = rph.REMOTE_PLAYER_ACTION_LABEL_PREFIX + "SOMETHING"
        self._reject(mutate, "step_order_or_delay_not_pinned")

    def test_trap_a_sweep_that_is_too_short(self):
        scenario, _unlock, probes, actions = sweep()
        with self.assertRaises(rph.RemotePlayerValidationError) as ctx:
            rph.validate_remote_player_sweep(
                list(actions[:4]), scenario, probes,
            )
        self.assertIn("exactly 5 frames", str(ctx.exception))

    def test_trap_the_negative_control_swapped_for_a_spawn_bare_copy(self):
        """A sweep without its wrong-class control cannot falsify anything,
        so a control frame that is really SPAWN_BARE again must refuse."""
        def mutate(rows):
            rows[4][1] = rows[0][1]
            rows[4][2] = rows[0][2]
        self._reject(mutate, "is not probe C's")

    def test_trap_a_move_frame_that_carries_two_attrs(self):
        _scenario, _unlock, probes, _actions = sweep()
        probe_a = by_role(probes)["A"]
        move = legacy().make_remote_movement_attr(
            probe_a.identity, probe_a.x + rph.MOVE_X_OFFSET, probe_a.y,
            probe_a.z, 0.0, mask=rph.MOVEMENT_MASK_POSITION,
        )
        entry = legacy().make_remote_actor_entry(
            rph.REMOTE_PLAYER_ACTOR_TYPE, probe_a.identity,
            [(rph.MOVEMENT_ATTR_ID, move), (rph.MOVEMENT_ATTR_ID, move)],
        )
        pc, frame = legacy().make_runtime_remote_actors([entry])

        def mutate(rows):
            rows[2][1] = pc
            rows[2][2] = frame
        self._reject(mutate, "EXACTLY one MovementAttr")


def test_pin_drift_trap_composed_bytes_do_not_match_the_pin(monkeypatch):
    """Poison one pinned hash and the composer must refuse its own output.

    The pin table is the contract between the encoder, the verifier and the
    scenario file; a composer that keeps emitting when the table disagrees
    with its bytes would let the three readers drift apart in silence.  The
    monkeypatch is undone before the final assertion, which proves the
    refusal came from the poisoned pin and nothing else.
    """
    scenario, unlock, probes, _actions = sweep()
    monkeypatch.setitem(
        rph.REMOTE_PLAYER_PINS[rph.MOVE_A_1_STEP_LABEL],
        "pc_sha256", "00" * 32,
    )
    with pytest.raises(rph.RemotePlayerValidationError) as ctx:
        rph.build_remote_player_sweep(
            legacy(), probes, unlock, scenario,
            avatar_wire=AVATAR_TAIL_ONE, selected_identity=SELECTED_IDENTITY,
        )
    assert "composed_bytes_do_not_match_the_pin" in str(ctx.value)
    monkeypatch.undo()
    assert rph.REMOTE_PLAYER_PINS[rph.MOVE_A_1_STEP_LABEL]["pc_sha256"] != (
        "00" * 32
    )
    actions = rph.build_remote_player_sweep(
        legacy(), probes, unlock, scenario,
        avatar_wire=AVATAR_TAIL_ONE, selected_identity=SELECTED_IDENTITY,
    )
    assert len(actions) == 5


if __name__ == "__main__":
    unittest.main()
