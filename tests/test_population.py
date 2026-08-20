import copy
import hashlib
import json
import math
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

# The v94 provenance test below reads two capture files under backups/, a tree
# that only exists on the bridge.  Actions run #3 (2026-08-20) found it with a
# FileNotFoundError on a fresh clone.  See tests/pf_preconditions.py.
from pf_preconditions import BACKUPS_TREE  # noqa: E402

from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.population import (
    AUTHORITATIVE_COUNT,
    MOVEMENT_ATTR_ID,
    NPC_ATTR_ID,
    PORT_ROYAL_SOURCE_COUNT,
    PORT_ROYAL_SOURCE_SHA256,
    build_port_royal_initial_population,
    build_port_royal_membership_transition,
    load_port_royal_placements,
)


class PopulationTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.golden = json.loads(
            (ROOT / "tests/golden/object_pop_001.json").read_text(encoding="utf-8")
        )
        provenance = cls.golden["provenance"]
        cls.initial_xyz = tuple(
            struct.unpack("<f", bytes.fromhex(raw))[0]
            for raw in provenance["initial_xyz_f32le"]
        )
        cls.refresh_xyz = tuple(
            struct.unpack("<f", bytes.fromhex(raw))[0]
            for raw in provenance["refresh_xyz_f32le"]
        )

    def _digest(self, value):
        return hashlib.sha256(value).hexdigest().upper()

    def _assert_generation_shape(self, transition):
        self.assertEqual(len(transition.current_indices), AUTHORITATIVE_COUNT)
        self.assertEqual(
            transition.pc.count(self.legacy.u16tag(0x12, NPC_ATTR_ID)), 20,
        )
        self.assertEqual(
            transition.pc.count(self.legacy.u16tag(0x12, MOVEMENT_ATTR_ID)),
            len(transition.entrant_indices),
        )
        self.assertEqual(
            set(transition.retained_indices) | set(transition.entrant_indices),
            set(transition.current_indices),
        )
        self.assertFalse(set(transition.omitted_indices) & set(transition.current_indices))
        first_offsets = [
            transition.pc.index(self.legacy.qwordtag(0x32, identity))
            for identity in transition.current_actor_identities
        ]
        self.assertEqual(first_offsets, sorted(first_offsets))
        for identity in transition.retained_actor_identities:
            self.assertEqual(transition.pc.count(self.legacy.qwordtag(0x32, identity)), 2)
        for identity in transition.entrant_actor_identities:
            self.assertEqual(transition.pc.count(self.legacy.qwordtag(0x32, identity)), 3)
        for identity in transition.omitted_actor_identities:
            self.assertNotIn(self.legacy.qwordtag(0x32, identity), transition.pc)

    def test_exact_source_forward_and_reverse_match_frozen_v94(self):
        placements = load_port_royal_placements(self.legacy)
        self.assertEqual(len(placements), PORT_ROYAL_SOURCE_COUNT)
        self.assertEqual(self.golden["source_count"], PORT_ROYAL_SOURCE_COUNT)
        self.assertEqual(self.golden["source_sha256"], PORT_ROYAL_SOURCE_SHA256)

        initial = tuple(
            row[0] for row in self.legacy._v94_nearest_population(*self.initial_xyz)
        )
        self.assertEqual(initial, tuple(self.golden["initial_indices"]))
        forward = build_port_royal_membership_transition(
            self.legacy, initial, self.refresh_xyz,
        )
        legacy_pc, legacy_frame, legacy_rows = self.legacy.make_v94_population_state(
            *self.refresh_xyz, set(initial),
        )
        self.assertEqual(forward.pc, legacy_pc)
        self.assertEqual(forward.frame, legacy_frame)
        self.assertEqual(
            forward.current_indices, tuple(row[0] for row in legacy_rows),
        )
        self.assertEqual(forward.current_indices, tuple(self.golden["refresh_indices"]))
        self.assertEqual(forward.retained_indices, tuple(self.golden["forward"]["retained"]))
        self.assertEqual(forward.entrant_indices, tuple(self.golden["forward"]["entrants"]))
        self.assertEqual(forward.omitted_indices, tuple(self.golden["forward"]["omitted"]))
        self.assertEqual(len(forward.pc), self.golden["forward"]["pc_length"])
        self.assertEqual(self._digest(forward.pc), self.golden["forward"]["pc_sha256"])
        self.assertEqual(len(forward.frame), self.golden["forward"]["frame_length"])
        self.assertEqual(self._digest(forward.frame), self.golden["forward"]["frame_sha256"])
        self._assert_generation_shape(forward)

        reverse = build_port_royal_membership_transition(
            self.legacy, forward.current_indices, self.initial_xyz,
        )
        legacy_pc, legacy_frame, legacy_rows = self.legacy.make_v94_population_state(
            *self.initial_xyz, set(forward.current_indices),
        )
        self.assertEqual(reverse.pc, legacy_pc)
        self.assertEqual(reverse.frame, legacy_frame)
        self.assertEqual(reverse.current_indices, tuple(row[0] for row in legacy_rows))
        self.assertEqual(reverse.current_indices, initial)
        self.assertEqual(reverse.retained_indices, tuple(self.golden["reverse"]["retained"]))
        self.assertEqual(reverse.entrant_indices, tuple(self.golden["reverse"]["entrants"]))
        self.assertEqual(reverse.omitted_indices, tuple(self.golden["reverse"]["omitted"]))
        self.assertEqual(len(reverse.pc), self.golden["reverse"]["pc_length"])
        self.assertEqual(self._digest(reverse.pc), self.golden["reverse"]["pc_sha256"])
        self.assertEqual(len(reverse.frame), self.golden["reverse"]["frame_length"])
        self.assertEqual(self._digest(reverse.frame), self.golden["reverse"]["frame_sha256"])
        self._assert_generation_shape(reverse)

        reentered = set(reverse.entrant_actor_identities)
        for index in reverse.entrant_indices:
            identity = 0x2000 + index + 1
            self.assertIn(identity, reentered)
            placement = next(item for item in placements if item.placement_index == index)
            exact_movement = self.legacy.make_remote_movement_attr(
                identity, placement.x, placement.y, placement.z,
                (0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0)[index & 3],
                mask=0xFF,
            )
            self.assertEqual(reverse.pc.count(exact_movement), 1)

    def test_initial_population_is_byte_exact_frozen_v94_all_entrants(self):
        initial = build_port_royal_initial_population(self.legacy, self.initial_xyz)
        legacy_pc, legacy_frame, legacy_rows = self.legacy.make_v94_population_state(
            *self.initial_xyz, None,
        )
        expected = self.golden["initial"]
        self.assertEqual(initial.pc, legacy_pc)
        self.assertEqual(initial.frame, legacy_frame)
        self.assertEqual(
            initial.current_indices, tuple(row[0] for row in legacy_rows),
        )
        self.assertEqual(initial.previous_indices, ())
        self.assertEqual(initial.retained_indices, ())
        self.assertEqual(initial.entrant_indices, tuple(expected["entrants"]))
        self.assertEqual(initial.omitted_indices, ())
        self.assertEqual(len(initial.pc), expected["pc_length"])
        self.assertEqual(self._digest(initial.pc), expected["pc_sha256"])
        self.assertEqual(len(initial.frame), expected["frame_length"])
        self.assertEqual(self._digest(initial.frame), expected["frame_sha256"])
        self.assertEqual(
            initial.pc.count(self.legacy.u16tag(0x12, MOVEMENT_ATTR_ID)),
            AUTHORITATIVE_COUNT,
        )
        self.assertEqual(
            initial.pc.count(self.legacy.u16tag(0x12, NPC_ATTR_ID)),
            AUTHORITATIVE_COUNT,
        )
        self._assert_generation_shape(initial)

    def test_previous_membership_and_position_are_strict(self):
        initial = tuple(self.golden["initial_indices"])
        invalid_previous = (
            list(initial), initial[:-1], initial + (60,),
            initial[:-1] + (initial[0],), initial[:-1] + (-1,),
            initial[:-1] + (0xDFFF,), initial[:-1] + (True,),
        )
        for value in invalid_previous:
            with self.subTest(previous=value):
                with self.assertRaises(ValueError):
                    build_port_royal_membership_transition(
                        self.legacy, value, self.refresh_xyz,
                    )
        invalid_xyz = (
            [0.0, 0.0, 931.0], (0.0, 0.0), (0.0, 0.0, 931.0, 0.0),
            (True, 0.0, 931.0), (float("nan"), 0.0, 931.0),
            (float("inf"), 0.0, 931.0), (3.5e38, 0.0, 931.0),
        )
        for value in invalid_xyz:
            with self.subTest(xyz=value):
                with self.assertRaises(ValueError):
                    build_port_royal_membership_transition(
                        self.legacy, initial, value,
                    )

    def test_the_v94_provenance_paths_are_declared_machine_local(self):
        """Always runs, on every machine, clone or bridge.

        The exact-content test below can only run where backups/ exists.  This
        one keeps a real assertion on the same golden data everywhere: the two
        provenance paths must still be the ones the precondition registry says
        are machine-local, so that nobody can move the evidence into the
        repository - or out of it - without this test noticing.
        """
        provenance = self.golden["provenance"]
        for key in ("raw_path", "live_path"):
            with self.subTest(key=key):
                declared = provenance[key]
                self.assertTrue(
                    declared.startswith("backups/"),
                    "%s no longer points into the machine-local tree: %s"
                    % (key, declared),
                )
                self.assertEqual(
                    (ROOT / declared).parents[2], BACKUPS_TREE.paths[0],
                )

    @BACKUPS_TREE.skip_unless_present()
    def test_natural_v94_provenance_is_exact_and_read_only(self):
        provenance = self.golden["provenance"]
        raw = ROOT / provenance["raw_path"]
        live = ROOT / provenance["live_path"]
        self.assertEqual(raw.stat().st_size, provenance["raw_size"])
        self.assertEqual(live.stat().st_size, provenance["live_size"])
        self.assertEqual(self._digest(raw.read_bytes()), provenance["raw_sha256"])
        self.assertEqual(self._digest(live.read_bytes()), provenance["live_sha256"])
        self.assertEqual(self.initial_xyz, tuple(provenance["initial_xyz"]))
        self.assertEqual(self.refresh_xyz, tuple(provenance["refresh_xyz"]))
        raw_text = raw.read_text(encoding="utf-8")
        self.assertIn(provenance["initial_hexdump_anchor"], raw_text)
        self.assertIn(provenance["initial_label"], raw_text)
        self.assertIn(provenance["refresh_hexdump_anchor"], raw_text)
        self.assertIn(provenance["accepted_label"], raw_text)
        self.assertIn(
            provenance["accepted_label"],
            live.read_text(encoding="utf-8"),
        )

    def test_source_constants_shape_order_and_allowed_value_drift_fail(self):
        original = self.legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
        mutations = []
        changed = copy.deepcopy(original)
        changed[0] = changed[0][:2] + (changed[0][2] + 1.0,) + changed[0][3:]
        mutations.append(changed)
        reordered = copy.deepcopy(original)
        reordered[0], reordered[1] = reordered[1], reordered[0]
        mutations.append(reordered)
        duplicate = copy.deepcopy(original)
        duplicate[1] = (duplicate[0][0],) + duplicate[1][1:]
        mutations.append(duplicate)
        malformed = copy.deepcopy(original)
        malformed[0] = malformed[0][:-1]
        mutations.append(malformed)
        nonfinite = copy.deepcopy(original)
        nonfinite[0] = nonfinite[0][:2] + (float("nan"),) + nonfinite[0][3:]
        mutations.append(nonfinite)
        try:
            for rows in mutations:
                with self.subTest(first=rows[0]):
                    self.legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS = rows
                    with self.assertRaises(ValueError):
                        load_port_royal_placements(self.legacy)
        finally:
            self.legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS = original

        for name, value in (
            ("NPC_ATTR", 0x0AD4),
            ("MOVEMENT_ATTR", 0x2066),
            ("GSCN_RUNTIME_PROTOCOL_RES", 0x6E9C),
            ("V94_LOCAL_LIMIT", 19),
            ("V94_REFRESH_DISTANCE", 999.0),
        ):
            original_value = getattr(self.legacy, name)
            try:
                setattr(self.legacy, name, value)
                with self.assertRaises(ValueError):
                    load_port_royal_placements(self.legacy)
            finally:
                setattr(self.legacy, name, original_value)

    def test_runtime_wiring_is_explicitly_opt_in(self):
        runtime_source = (ROOT / "src/pirateforce_foundation/runtime.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("build_port_royal_membership_transition", runtime_source)
        self.assertIn("population_scenario is not None", runtime_source)
        self.assertIn("self.npc_spawn_sent = True", runtime_source)


if __name__ == "__main__":
    unittest.main()
