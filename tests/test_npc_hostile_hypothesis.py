"""NPC-HOSTILE-001 (HYP-PF-027) -- the hostile-presentation encoder, offline.

What this file proves, and where the proof stops:

  * the one designed frame recomputes to its pins, three copies agreeing --
    the module dict, the scenario file, and the composed bytes;
  * CROSS-LANE BYTE EQUALITY: the frame IS the parent lane's SPAWN (composed
    through the parent's own module and profile) plus exactly the five-byte
    faction splice and exactly one mask bit.  Tests may import both lanes;
    the src modules never import each other;
  * every named refusal fires: the unlock (missing and forged), the pinned
    faction values, zero HP, the exact-allowlist scenario loader against a
    tampered tree, the lookalike dataclass, and the validator against
    hand-built wrong sweeps -- including a mask that silently LOST the
    faction bit and a mask that silently GAINED any other bit;
  * containment: only app.py and runtime.py mention the module; the module
    opens no database and no socket; the module never names the death lane's
    timer bit at all (its strict mask equality subsumes forbidding it).

NOT proven here: anything about a client.  No client has ever been shown one
byte of this profile; whether NPC 0x2001 presents as hostile is GT-032,
attended, not run.  The faction values (player 1, NPC 6) are OUR composition
-- the pair SCENE-005 proved on a real screen -- and the original server's
faction assignment is unknown and unrecoverable.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import npc_hostile_hypothesis as nhm  # noqa: E402
from pirateforce_foundation import runtimeres_death_hypothesis as parent  # noqa: E402
from pirateforce_foundation.player_wire import (  # noqa: E402
    make_actor_attr_with_basic_faction,
    make_actor_attr_with_name,
)

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "npc_hostile_hypothesis_faction_pairing.json"
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
MODULE_SOURCE_PATH = SRC_ROOT / "npc_hostile_hypothesis.py"

STEP_LABEL = "HOSTILE_SPAWN"
ACTION_LABEL = "HYP_PF_027_NPC_HOSTILE_HOSTILE_SPAWN"
ATTR_START = 17 + 2 + 9 + 2 + 3
MASK_AT = ATTR_START + 12
SPLICE_AT = ATTR_START + 36


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class NpcHostileEncoderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()
        cls.scenario = nhm.load_npc_hostile_hypothesis_scenario(SCENARIO_PATH)
        cls.wire = nhm.npc_hostile_wire_unlock(cls.scenario)
        cls.probe = nhm.resolve_probe(cls.legacy)
        cls.pinned = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        cls.actions = nhm.build_npc_hostile_sweep(
            cls.legacy, cls.probe, cls.wire, cls.scenario,
        )

    # ----- the pins, three copies agreeing --------------------------------

    def test_the_sweep_is_exactly_one_pinned_action(self):
        self.assertEqual(len(self.actions), 1)
        label, pc, frame, delay = self.actions[0]
        self.assertEqual(label, ACTION_LABEL)
        self.assertEqual(delay, 0.0)
        self.assertEqual(frame, self.legacy.frame_pc(pc))

    def test_the_pins_recompute_and_all_three_copies_agree(self):
        _label, pc, frame, _delay = self.actions[0]
        pin = nhm.NPC_HOSTILE_PINS[STEP_LABEL]
        scen = self.pinned["probe"]["per_step"][STEP_LABEL]
        computed = {
            "basic_mask": 0x070C,
            "faction_value": 6,
            "pc_size": len(pc),
            "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
            "frame_size": len(frame),
            "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
        }
        self.assertEqual(computed, pin)
        self.assertEqual(computed, scen)

    def test_the_mask_algebra_is_exactly_one_bit_wide(self):
        self.assertEqual(nhm.HYP23_SPAWN_BASIC_MASK, 0x030C)
        self.assertEqual(nhm.BASIC_BIT_FACTION, 0x0400)
        self.assertEqual(nhm.NPC_HOSTILE_BASIC_MASK, 0x070C)
        self.assertEqual(
            nhm.HYP23_SPAWN_BASIC_MASK & nhm.BASIC_BIT_FACTION, 0,
        )

    def test_the_walker_reads_back_the_designed_frame(self):
        _label, pc, _frame, _delay = self.actions[0]
        read = nhm.decode_npc_hostile_actor_entry_frame(pc)
        self.assertEqual(read["actor_type"], 4)
        self.assertEqual(read["identity"], 0x2001)
        npc = read["attrs"][nhm.NPC_ATTR_ID]
        self.assertEqual(npc["basic_mask"], 0x070C)
        self.assertEqual(npc["fields"][nhm.BASIC_BIT_FACTION], 6)
        self.assertEqual(npc["fields"][nhm.BASIC_BIT_CURRENT_HP], 100)
        self.assertEqual(npc["template_id"], 1)
        self.assertEqual(npc["visual_preset"], "P_MALE_002_000_SP1")
        self.assertIn(nhm.MOVEMENT_ATTR_ID, read["attrs"])

    # ----- cross-lane byte equality ----------------------------------------

    def test_the_frame_is_the_parents_spawn_plus_exactly_the_splice(self):
        parent_probe = parent.resolve_probe(self.legacy)
        parent_pc, _parent_frame = parent.make_runtimeres_death_step_response(
            self.legacy, parent_probe, 0, None, parent._PROFILE,
        )
        _label, pc, _frame, _delay = self.actions[0]
        faction_wire = bytes(self.legacy.u32tag(0x14, 6))
        expected = (
            parent_pc[:MASK_AT]
            + (0x070C).to_bytes(2, "little")
            + parent_pc[MASK_AT + 2:SPLICE_AT]
            + faction_wire
            + parent_pc[SPLICE_AT:]
        )
        self.assertEqual(pc, expected)
        self.assertEqual(len(pc), len(parent_pc) + 5)
        self.assertEqual(pc[:MASK_AT], parent_pc[:MASK_AT])
        self.assertEqual(pc[SPLICE_AT + 5:], parent_pc[SPLICE_AT:])
        self.assertEqual(pc[SPLICE_AT:SPLICE_AT + 5], faction_wire)

    def test_both_lanes_resolve_the_same_frozen_probe(self):
        parent_probe = parent.resolve_probe(self.legacy)
        self.assertEqual(
            (parent_probe.placement_index, parent_probe.template_id,
             parent_probe.actor_identity, parent_probe.visual_preset,
             parent_probe.x, parent_probe.y, parent_probe.z),
            (self.probe.placement_index, self.probe.template_id,
             self.probe.actor_identity, self.probe.visual_preset,
             self.probe.x, self.probe.y, self.probe.z),
        )

    def test_the_copied_parent_mask_constant_is_honest(self):
        self.assertEqual(
            parent.RUNTIMERES_DEATH_PINS["SPAWN"]["basic_mask"],
            nhm.HYP23_SPAWN_BASIC_MASK,
        )

    # ----- the unlock -------------------------------------------------------

    def test_no_unlock_refuses_by_name(self):
        with self.assertRaisesRegex(ValueError, "missing_or_forged"):
            nhm.encode_hostile_npc_attr(self.legacy, self.probe, wire=None)

    def test_a_value_equal_forged_unlock_is_refused(self):
        forged = nhm.NpcHostileWireUnlock(
            nhm.NPC_HOSTILE_SCENARIO_ID, nhm.NPC_HOSTILE_HYPOTHESIS_ID,
        )
        self.assertEqual(forged, nhm._UNLOCK)
        with self.assertRaisesRegex(ValueError, "missing_or_forged"):
            nhm.encode_hostile_npc_attr(self.legacy, self.probe, wire=forged)
        with self.assertRaisesRegex(ValueError, "missing_or_forged"):
            nhm.build_npc_hostile_sweep(
                self.legacy, self.probe, forged, self.scenario,
            )

    # ----- the pinned values ------------------------------------------------

    def test_only_the_scene005_npc_faction_is_composable(self):
        for value in (0, 1, 2, 3, 5, 7, 18, 0xFFFFFFFF):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    ValueError, "faction_value_not_pinned",
                ):
                    nhm.encode_hostile_npc_attr(
                        self.legacy, self.probe, faction=value,
                        wire=self.wire,
                    )

    def test_zero_hp_refuses_by_name(self):
        with self.assertRaisesRegex(ValueError, "refuses_zero_hp"):
            nhm.encode_hostile_npc_attr(
                self.legacy, self.probe, current_hp=0, wire=self.wire,
            )

    def test_a_bare_tuple_is_not_a_probe(self):
        with self.assertRaisesRegex(ValueError, "typed probe object"):
            nhm.encode_hostile_npc_attr(
                self.legacy, (0, 1, 0x2001), wire=self.wire,
            )

    def test_the_probe_resolves_to_the_pinned_placement(self):
        self.assertEqual(self.probe.actor_identity, 0x2001)
        self.assertEqual(self.probe.template_id, 1)
        self.assertEqual(self.probe.placement_index, 0)
        self.assertEqual(self.probe.visual_preset, "P_MALE_002_000_SP1")
        self.assertEqual(self.probe.source_name, "Navy Transfer")

    # ----- the scenario allowlist -------------------------------------------

    def _mutant_path(self, mutate):
        data = copy.deepcopy(self.pinned)
        mutate(data)
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8",
        )
        json.dump(data, handle)
        handle.close()
        self.addCleanup(Path(handle.name).unlink)
        return handle.name

    def test_tampered_scenario_trees_are_refused(self):
        mutations = {
            "production_allowed_true":
                lambda d: d.update(production_allowed=True),
            "test_only_false": lambda d: d.update(test_only=False),
            "lethal_true": lambda d: d.update(lethal=True),
            "extra_key_at_root": lambda d: d.update(extra=1),
            "extra_key_in_wire": lambda d: d["wire"].update(extra=1),
            "npc_faction_1":
                lambda d: d["wire"]["relation"].update(npc_side_value=1),
            "player_faction_6":
                lambda d: d["entry"]["player_start_game"].update(
                    basic_faction=6),
            "pairing_requirement_dropped":
                lambda d: d["dispatch"].pop(
                    "requires_player_faction_start_game"),
            "one_shot_false": lambda d: d["dispatch"].update(one_shot=False),
            "tampered_pin":
                lambda d: d["probe"]["per_step"][STEP_LABEL].update(
                    pc_sha256="00" * 32),
            "second_step":
                lambda d: d["dispatch"].update(
                    step_order=[STEP_LABEL, STEP_LABEL]),
            "database_write":
                lambda d: d["persisted_post_state"].update(
                    database_write="checkpoint"),
        }
        for name, mutate in mutations.items():
            with self.subTest(mutation=name):
                with self.assertRaisesRegex(
                    ValueError, "exceeds the exact allowlist",
                ):
                    nhm.load_npc_hostile_hypothesis_scenario(
                        self._mutant_path(mutate),
                    )

    def test_a_non_json_file_is_refused(self):
        with self.assertRaisesRegex(ValueError, "invalid npc hostile"):
            nhm.load_npc_hostile_hypothesis_scenario(LEGACY_PATH)

    def test_a_lookalike_dataclass_is_refused(self):
        look = nhm.NpcHostileHypothesisScenario(
            nhm.NPC_HOSTILE_SCENARIO_ID, nhm.NPC_HOSTILE_HYPOTHESIS_ID,
            nhm.NPC_HOSTILE_STEP_ORDER, 15.0, 0.0,
            nhm.NPC_HOSTILE_ACTION_LABEL_PREFIX, 7, 1,
        )
        with self.assertRaisesRegex(ValueError, "exceeds the allowlist"):
            nhm.require_npc_hostile_hypothesis_scenario(look)

    # ----- validator traps: hand-built wrong sweeps -------------------------

    def _validate(self, actions):
        return nhm.validate_npc_hostile_sweep(actions, self.scenario)

    def test_the_validator_refuses_the_wrong_shapes(self):
        _label, pc, frame, _delay = self.actions[0]
        with self.assertRaisesRegex(
            nhm.NpcHostileValidationError, "exactly 1 frame",
        ):
            self._validate([])
        with self.assertRaisesRegex(
            nhm.NpcHostileValidationError, "exactly 1 frame",
        ):
            self._validate([self.actions[0], self.actions[0]])
        with self.assertRaisesRegex(
            nhm.NpcHostileValidationError, "labelled",
        ):
            self._validate([("HYP_PF_027_NPC_HOSTILE_WRONG", pc, frame, 0.0)])

    def test_a_mask_that_lost_the_faction_bit_is_refused(self):
        _label, pc, _frame, _delay = self.actions[0]
        bad = (
            pc[:MASK_AT] + (0x030C).to_bytes(2, "little") + pc[MASK_AT + 2:]
        )
        with self.assertRaisesRegex(
            nhm.NpcHostileValidationError,
            "not exactly the HYP-PF-023 spawn mask",
        ):
            self._validate([(ACTION_LABEL, bad,
                             self.legacy.frame_pc(bad), 0.0)])

    def test_a_mask_that_gained_any_other_bit_is_refused(self):
        _label, pc, _frame, _delay = self.actions[0]
        for extra in (0x0001, 0x0002, 0x0040, 0x0800):
            with self.subTest(extra_bit=hex(extra)):
                bad = (
                    pc[:MASK_AT]
                    + (0x070C | extra).to_bytes(2, "little")
                    + pc[MASK_AT + 2:]
                )
                with self.assertRaisesRegex(
                    nhm.NpcHostileValidationError,
                    "not exactly the HYP-PF-023 spawn mask",
                ):
                    self._validate([(ACTION_LABEL, bad,
                                     self.legacy.frame_pc(bad), 0.0)])

    def test_a_wire_faction_other_than_6_is_refused(self):
        _label, pc, _frame, _delay = self.actions[0]
        patched = bytearray(pc)
        patched[SPLICE_AT + 1:SPLICE_AT + 5] = (1).to_bytes(4, "little")
        with self.assertRaisesRegex(
            nhm.NpcHostileValidationError, "not the pinned 6",
        ):
            self._validate([(ACTION_LABEL, bytes(patched),
                             self.legacy.frame_pc(bytes(patched)), 0.0)])

    def test_trailing_bytes_are_refused(self):
        _label, pc, _frame, _delay = self.actions[0]
        bad = pc + b"\x00"
        with self.assertRaisesRegex(
            nhm.NpcHostileValidationError, "trailing",
        ):
            nhm.decode_npc_hostile_actor_entry_frame(bad)

    # ----- the entry half ---------------------------------------------------

    def test_the_player_pairing_constants_and_delta(self):
        legacy = self.legacy
        plain = make_actor_attr_with_name(
            legacy, 0x10010001, 0, 1, 0, "SmokeName",
        )
        paired = make_actor_attr_with_basic_faction(
            legacy, 0x10010001, 0, 1, 0, "SmokeName", 1,
        )
        self.assertEqual(
            len(paired) - len(plain),
            nhm.NPC_HOSTILE_PLAYER_FACTION_WIRE_DELTA,
        )
        self.assertIn(bytes([0x14, 1, 0, 0, 0]), bytes(paired))
        self.assertNotIn(bytes([0x14, 1, 0, 0, 0]), bytes(plain))
        self.assertEqual(nhm.NPC_HOSTILE_PLAYER_IDENTITY_LO, 0x10010001)
        self.assertEqual(nhm.NPC_HOSTILE_PLAYER_IDENTITY_HI, 0)
        self.assertEqual(nhm.NPC_HOSTILE_PLAYER_PAIR_FACTION, 1)
        self.assertEqual(nhm.NPC_HOSTILE_NPC_FACTION_VALUE, 6)

    def test_the_frozen_player_serializer_refuses_everything_else(self):
        legacy = self.legacy
        with self.assertRaises(ValueError):
            make_actor_attr_with_basic_faction(
                legacy, 0x10010001, 0, 1, 0, "X", 6,
            )
        with self.assertRaises(ValueError):
            make_actor_attr_with_basic_faction(
                legacy, 0x10010001, 0, 3, 0, "X", 1,
            )
        with self.assertRaises(ValueError):
            make_actor_attr_with_basic_faction(
                legacy, 0x10010001, 0, 1, 9, "X", 1,
            )

    # ----- containment and hygiene ------------------------------------------

    def test_exactly_two_foundation_modules_mention_the_lane(self):
        module = "npc_hostile_hypothesis"
        importers = sorted(
            path.name for path in SRC_ROOT.glob("*.py")
            if module in path.read_text(encoding="utf-8")
            and path.name != f"{module}.py"
        )
        self.assertEqual(importers, ["app.py", "runtime.py"])
        for name in ("connection.py", "scenario.py", "session.py",
                     "store.py"):
            self.assertNotIn(
                module, (SRC_ROOT / name).read_text(encoding="utf-8"), name)

    def test_the_module_opens_no_database_and_no_socket(self):
        source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        for banned in ("sqlite3", "SQLiteStore", "INSERT ", "DELETE FROM",
                       "import socket", "socket.socket", "connect("):
            self.assertNotIn(banned, source)

    def test_the_module_never_names_the_death_lanes_timer_bit(self):
        source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("0x0080", source)

    def test_the_module_carries_exactly_one_ledger_marker(self):
        source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertEqual(
            source.count("# PF-HYPOTHESIS-LEDGER: HYP-PF-027 active"), 1,
        )

    def test_production_is_disallowed_everywhere(self):
        self.assertIs(nhm.production_allowed, False)
        self.assertIs(self.pinned["production_allowed"], False)
        self.assertIs(self.pinned["test_only"], True)
        self.assertIs(self.pinned["lethal"], False)
        self.assertEqual(
            self.pinned["persisted_post_state"]["database_write"], "none",
        )

    def test_the_nonclaims_name_the_composition_and_the_client_gap(self):
        for needle in (
            "no_client_has_ever_been_shown_one_byte_of_this_profile",
            "faction_values_1_and_6_are_our_composition_not_the_original_"
            "servers_which_is_unrecoverable",
            "no_aggro_no_threat_table_no_chase_no_attack_door_b_stays_closed",
        ):
            self.assertIn(needle, self.pinned["nonclaims"])
            self.assertIn(needle, nhm.NPC_HOSTILE_NONCLAIMS)


if __name__ == "__main__":
    unittest.main()
