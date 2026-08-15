import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = str(ROOT / "tools")
sys.path.insert(0, TOOLS)
SPEC = importlib.util.spec_from_file_location(
    "pf_relation_matrix_probe", ROOT / "tools" / "pf_relation_matrix_probe.py"
)
MATRIX = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MATRIX
SPEC.loader.exec_module(MATRIX)


class RelationMatrixProbeTests(unittest.TestCase):
    def test_guarded_read_only_thiscall_source(self):
        config = MATRIX.load_config(ROOT / "tools/pf_relation_probe_config.json")
        source = MATRIX.make_agent_source(config, 6, 31)
        self.assertEqual(MATRIX.LOOKUP_VA, 0x4A1D50)
        self.assertEqual(MATRIX.ACCESSOR_VA, 0x40B560)
        self.assertIn("'thiscall'", source)
        self.assertIn("runtime relation function guard mismatch", source)
        self.assertNotIn("Memory.write", source)
        self.assertNotIn("writeU", source)

    def test_matrix_event_schema_and_rows_are_strict(self):
        rows = [
            {"candidate": value, "candidate_then_target": value & 1,
             "target_then_candidate": value & 1}
            for value in range(4)
        ]
        event = {"schema": 1, "event": "matrix", "timestamp": "now",
                 "relation_system": "0x1000", "target": 1, "rows": rows}
        self.assertIs(MATRIX.validate_event(event, 3), event)
        with self.assertRaises(ValueError):
            MATRIX.validate_event(dict(event, semantic="enemy"), 3)
        bad_rows = [dict(row) for row in rows]
        bad_rows[2]["candidate"] = 3
        with self.assertRaises(ValueError):
            MATRIX.validate_event(dict(event, rows=bad_rows), 3)

    def test_observed_lookup_rejects_non_boolean_result(self):
        event = {"schema": 1, "event": "observed_lookup", "timestamp": "now",
                 "first": 0, "second": 6, "result_u8": 1}
        self.assertIs(MATRIX.validate_event(event, 31), event)
        with self.assertRaises(ValueError):
            MATRIX.validate_event(dict(event, result_u8=2), 31)


if __name__ == "__main__":
    unittest.main()
