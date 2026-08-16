from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.verify_hypothesis_ledger import (
    DEFAULT_LEDGER,
    EXPECTED_IDS,
    LedgerError,
    ROOT,
    load_ledger,
    verify_source_annotations,
)


class HypothesisLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = json.loads(DEFAULT_LEDGER.read_text(encoding="utf-8"))

    def verify_mutation(self, mutate) -> None:
        value = copy.deepcopy(self.raw)
        mutate(value)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(LedgerError):
                load_ledger(path, root=ROOT)

    def test_canonical_inventory_and_policy(self) -> None:
        ledger = load_ledger()
        self.assertEqual(tuple(item.id for item in ledger.entries), EXPECTED_IDS)
        one, two = ledger.entries[:2]
        self.assertIsNone(one.extension_approval_ref)
        self.assertIsNone(two.extension_approval_ref)
        self.assertEqual(one.status, "frozen")
        self.assertEqual(two.status, "frozen")
        raw_by_id = {item["id"]: item for item in self.raw["entries"]}
        self.assertIn("mask 0x0400", raw_by_id["HYP-PF-001"]["exact_value_or_transform"])
        self.assertIn("omit trailing TargetPos", raw_by_id["HYP-PF-002"]["exact_value_or_transform"])
        self.assertEqual(raw_by_id["HYP-PF-008"]["status"], "active")
        self.assertIn(
            "destination value32 2",
            raw_by_id["HYP-PF-008"]["exact_value_or_transform"],
        )
        self.assertFalse(raw_by_id["HYP-PF-008"]["production_allowed"])
        self.assertEqual(raw_by_id["HYP-PF-009"]["status"], "active")
        self.assertIn(
            "after the first selected runtime-ready request",
            raw_by_id["HYP-PF-009"]["exact_value_or_transform"],
        )
        self.assertEqual(raw_by_id["HYP-PF-009"]["max_versions"], 3)
        self.assertFalse(raw_by_id["HYP-PF-009"]["production_allowed"])
        self.assertEqual(raw_by_id["RET-PF-001"]["status"], "retired")
        self.assertTrue(all(item["production_allowed"] is False for item in self.raw["entries"]))
        self.assertTrue(all(item["authentic"] is False for item in self.raw["entries"] if item["kind"] == "test_geometry"))
        self.assertTrue(all(item["extension_approval_ref"] is None for item in self.raw["entries"]))
        self.assertTrue(all(
            item["status"] in {"frozen", "expired_pending_decision"}
            for item in self.raw["entries"]
            if len(item["expiry"]["tracked_versions"]) > item["max_versions"]
        ))
        self.assertNotIn("SCENE-013", one.expiry.tracked_versions)
        self.assertNotIn("SCENE-013", two.expiry.tracked_versions)

    def test_rejects_inventory_and_metadata_drift(self) -> None:
        mutations = (
            lambda value: value["entries"].append(copy.deepcopy(value["entries"][0])),
            lambda value: value["entries"][0].update(id="HYP-PF-999"),
            lambda value: value["entries"].__setitem__(slice(0, 2), list(reversed(value["entries"][:2]))),
            lambda value: value["entries"][0].update(kind="diagnostic_value"),
            lambda value: value["entries"][0].update(status="active"),
            lambda value: value["entries"][0].update(unknown=True),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.verify_mutation(mutation)

    def test_rejects_source_and_marker_drift(self) -> None:
        mutations = (
            lambda value: value["entries"][0]["source_refs"][0].update(path="../STATUS.md"),
            lambda value: value["entries"][0]["source_refs"][0]["required_markers"].append("missing ledger marker"),
            lambda value: value["entries"][0]["evidence_refs"].append("missing/report.md"),
            lambda value: value["entries"][0]["source_refs"][0].update(active_claim_marker=False),
            lambda value: value["entries"][10]["source_refs"][0].update(active_claim_marker=True),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.verify_mutation(mutation)

    def test_rejects_production_geometry_and_expiry_drift(self) -> None:
        mutations = (
            lambda value: value["entries"][0].update(production_allowed=True),
            lambda value: value["entries"][11].update(authentic=True),
            lambda value: value["entries"][0].update(extension_approval_ref="GENERIC-APPROVAL"),
            lambda value: value["entries"][0].update(extension_approval_ref={
                "approval_id": "SCOPE-1", "approved_entry_ids": ["HYP-PF-003"],
                "approved_through": "SCENE-012",
            }),
            lambda value: value["entries"][0].update(extension_approval_ref={
                "approval_id": "SCOPE-1", "approved_entry_ids": ["HYP-PF-001"],
            }),
            lambda value: value["entries"][2].update(status="active"),
            lambda value: value["entries"][2]["expiry"]["tracked_versions"].append("V142"),
            lambda value: value["entries"][0]["expiry"]["tracked_versions"].append("SCENE-013"),
            lambda value: value["entries"][0].update(max_versions=4),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.verify_mutation(mutation)

    def test_rejects_schema_and_required_field_drift(self) -> None:
        mutations = (
            lambda value: value.update(schema=True),
            lambda value: value["policy"].update(max_related_versions=True),
            lambda value: value["entries"][0].pop("stop_rule"),
            lambda value: value["entries"][0].update(falsification=""),
            lambda value: value["entries"][0]["expiry"].update(decision=""),
            lambda value: value["entries"][0]["expiry"].update(tracked_versions=[]),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.verify_mutation(mutation)

    def test_rejects_allowed_to_allowed_semantic_text_drift(self) -> None:
        self.verify_mutation(
            lambda value: value["entries"][0].update(
                exact_value_or_transform="Another non-empty but unapproved transform."
            )
        )

    def test_bidirectional_emitter_annotations_fail_closed(self) -> None:
        ledger = load_ledger()
        with self.assertRaises(LedgerError):
            verify_source_annotations(
                ledger.entries, ROOT,
                scan_items=[(
                    "src/pirateforce_foundation/__unregistered.py",
                    "# PF-HYPOTHESIS-LEDGER: HYP-PF-001 frozen\n",
                )],
                require_complete=False,
            )
        with self.assertRaises(LedgerError):
            verify_source_annotations(
                ledger.entries, ROOT,
                scan_items=[(
                    "src/pirateforce_foundation/runtime.py",
                    "# PF-HYPOTHESIS-LEDGER: DIAG-PF-001 active\n",
                )],
                require_complete=False,
            )
        with self.assertRaises(LedgerError):
            verify_source_annotations(ledger.entries, ROOT, scan_items=[], require_complete=True)

    def test_immutable_exception_is_exact_and_unique(self) -> None:
        current_index = 2
        mutations = (
            lambda value: value["entries"][current_index]["source_refs"][0].update(
                sha256="0" * 64
            ),
            lambda value: value["entries"][current_index]["source_refs"][0].update(
                path="src/pirateforce_foundation/runtime.py"
            ),
            lambda value: value["entries"][current_index]["source_refs"][0][
                "immutable_anchors"
            ].append("self.v136_docking_composition_pending=True"),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.verify_mutation(mutation)


if __name__ == "__main__":
    unittest.main()
