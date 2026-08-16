from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.verify_functional_coverage import (
    COMPLETE,
    DEFAULT_MATRIX,
    ROOT,
    STATUSES,
    CoverageError,
    load_coverage,
)


class FunctionalCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = json.loads(DEFAULT_MATRIX.read_text(encoding="utf-8"))

    def reject(self, mutate) -> CoverageError:
        value = copy.deepcopy(self.raw)
        mutate(value)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "coverage.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(CoverageError) as caught:
                load_coverage(path, root=ROOT)
        return caught.exception

    @staticmethod
    def domain(value: dict, ident: str) -> dict:
        for item in value["domains"]:
            if item["id"] == ident:
                return item
        raise AssertionError(f"missing domain {ident}")

    # --- canonical state -------------------------------------------------

    def test_canonical_matrix_loads_and_no_domain_is_complete(self) -> None:
        coverage = load_coverage()
        self.assertEqual(coverage.schema, 1)
        self.assertGreaterEqual(len(coverage.domains), 2)
        ids = {domain.id for domain in coverage.domains}
        self.assertIn("inventory", ids)
        self.assertIn("session_lifecycle", ids)
        for domain in coverage.domains:
            self.assertFalse(
                domain.domain_complete,
                f"{domain.id} must not claim completion without required rows green",
            )
            self.assertTrue(domain.status_banner.endswith(": INCOMPLETE"))

    def test_every_user_requested_inventory_row_is_present_and_required(self) -> None:
        coverage = load_coverage()
        inventory = next(d for d in coverage.domains if d.id == "inventory")
        expected = {
            "backpack_open_display",
            "persisted_projection_reconnect",
            "move_known_item_any_free_slot",
            "same_slot_noop",
            "move_negative_paths",
            "occupied_destination_policy",
            "stack_merge_and_limit",
            "split_stack",
            "equip_unequip",
            "use_drop_sell",
        }
        present = {cap.id for cap in inventory.capabilities}
        self.assertEqual(expected, present)
        for cap in inventory.capabilities:
            self.assertTrue(cap.required, f"{cap.id} must stay required")

    def test_playable_game_domains_are_present_and_every_row_stays_required(self) -> None:
        """The matrix must keep spanning the whole playable surface.

        The stated project goal is a game that is actually playable through the
        real client.  A domain may only be removed from this set by an explicit
        decision, never as a side effect of making the report look greener.
        """
        coverage = load_coverage()
        expected = {
            "inventory",
            "session_lifecycle",
            "movement",
            "combat",
            "character_management",
            "chat",
            "npc_interaction",
        }
        present = {domain.id for domain in coverage.domains}
        self.assertEqual(expected, expected & present, sorted(expected - present))
        for domain in coverage.domains:
            for cap in domain.capabilities:
                self.assertTrue(
                    cap.required,
                    f"{domain.id}.{cap.id} must stay required",
                )

    def test_no_open_domain_hides_behind_runtime_pass_alone(self) -> None:
        """runtime_pass rows must never be mistaken for finished behavior."""
        for domain in load_coverage().domains:
            if domain.domain_complete:
                continue
            statuses = {cap.status for cap in domain.capabilities if cap.required}
            self.assertNotEqual(
                statuses,
                {"complete"},
                f"{domain.id} is open yet every required row reads complete",
            )

    def test_status_file_publishes_every_banner_exactly_once(self) -> None:
        contents = (ROOT / "STATUS.md").read_text(encoding="utf-8")
        for domain in load_coverage().domains:
            self.assertEqual(contents.count(domain.status_banner), 1)

    def test_declared_refs_all_exist(self) -> None:
        for domain in load_coverage().domains:
            for cap in domain.capabilities:
                for ref in cap.evidence_refs + cap.test_refs:
                    self.assertTrue((ROOT / ref).is_file(), ref)

    # --- the core gate ---------------------------------------------------

    def test_domain_complete_is_rejected_while_required_rows_are_open(self) -> None:
        def mutate(value: dict) -> None:
            domain = self.domain(value, "inventory")
            domain["domain_complete"] = True
            domain["status_banner"] = "Inventory: COMPLETE"
            domain["next_missing_behavior"] = "none"

        error = self.reject(mutate)
        self.assertIn("domain_complete=true", str(error))

    def test_runtime_pass_alone_never_closes_a_domain(self) -> None:
        def mutate(value: dict) -> None:
            domain = self.domain(value, "session_lifecycle")
            for cap in domain["capabilities"]:
                if cap["status"] == "not_started":
                    cap["status"] = "runtime_pass"
                    cap["evidence_refs"] = [
                        "reports/PF_CONSOLE001_VISIBLE_CONSOLE_RUNTIME_PASS_20260817.md"
                    ]
            domain["domain_complete"] = True
            domain["status_banner"] = "Session lifecycle: COMPLETE"
            domain["next_missing_behavior"] = "none"

        error = self.reject(mutate)
        self.assertIn("not complete", str(error))

    def test_all_required_complete_is_accepted_and_demands_none(self) -> None:
        value = copy.deepcopy(self.raw)
        domain = self.domain(value, "session_lifecycle")
        for cap in domain["capabilities"]:
            cap["status"] = COMPLETE
            cap["evidence_refs"] = [
                "reports/PF_CONSOLE001_VISIBLE_CONSOLE_RUNTIME_PASS_20260817.md"
            ]
            cap["test_refs"] = ["tests/test_functional_coverage.py"]
        domain["domain_complete"] = True
        domain["status_banner"] = "Session lifecycle: COMPLETE"
        domain["next_missing_behavior"] = "none"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "coverage.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            # STATUS.md still carries the INCOMPLETE banner, so the publication
            # gate must fail even though the completion gate now passes.
            with self.assertRaises(CoverageError) as caught:
                load_coverage(path, root=ROOT)
        self.assertIn("STATUS.md", str(caught.exception))

    # --- banner and pointer discipline -----------------------------------

    def test_banner_must_match_completion_state(self) -> None:
        error = self.reject(
            lambda value: self.domain(value, "inventory").__setitem__(
                "status_banner", "Inventory: COMPLETE"
            )
        )
        self.assertIn("status_banner", str(error))

    def test_banner_must_be_published_in_status(self) -> None:
        def mutate(value: dict) -> None:
            domain = self.domain(value, "inventory")
            domain["title"] = "Inventory subsystem"
            domain["status_banner"] = "Inventory subsystem: INCOMPLETE"

        error = self.reject(mutate)
        self.assertIn("STATUS.md", str(error))

    def test_next_missing_behavior_must_name_an_open_required_row(self) -> None:
        self.reject(
            lambda value: self.domain(value, "inventory").__setitem__(
                "next_missing_behavior", "not_a_capability"
            )
        )

        def point_at_closed(value: dict) -> None:
            domain = self.domain(value, "inventory")
            cap = domain["capabilities"][0]
            cap["status"] = COMPLETE
            cap["test_refs"] = ["tests/test_functional_coverage.py"]
            domain["next_missing_behavior"] = cap["id"]

        error = self.reject(point_at_closed)
        self.assertIn("not an open required capability", str(error))

    def test_open_domain_may_not_say_none(self) -> None:
        self.reject(
            lambda value: self.domain(value, "inventory").__setitem__(
                "next_missing_behavior", "none"
            )
        )

    # --- evidence discipline ---------------------------------------------

    def test_runtime_pass_requires_evidence(self) -> None:
        def mutate(value: dict) -> None:
            domain = self.domain(value, "inventory")
            for cap in domain["capabilities"]:
                if cap["status"] == "runtime_pass":
                    cap["evidence_refs"] = []
                    return
            raise AssertionError("no runtime_pass row to mutate")

        error = self.reject(mutate)
        self.assertIn("evidence ref", str(error))

    def test_not_started_must_not_carry_evidence(self) -> None:
        def mutate(value: dict) -> None:
            domain = self.domain(value, "inventory")
            for cap in domain["capabilities"]:
                if cap["status"] == "not_started":
                    cap["evidence_refs"] = [
                        "reports/PF_CONSOLE001_VISIBLE_CONSOLE_RUNTIME_PASS_20260817.md"
                    ]
                    return
            raise AssertionError("no not_started row to mutate")

        error = self.reject(mutate)
        self.assertIn("must not carry evidence", str(error))

    def test_missing_reference_is_rejected(self) -> None:
        self.reject(
            lambda value: self.domain(value, "inventory")["capabilities"][0]
            .__setitem__("evidence_refs", ["reports/does_not_exist.md"])
        )

    def test_reference_escape_is_rejected(self) -> None:
        for bad in ("../secret.md", "/etc/passwd", "reports\\windows.md"):
            with self.subTest(bad=bad):
                self.reject(
                    lambda value, bad=bad: self.domain(value, "inventory")["capabilities"][0]
                    .__setitem__("evidence_refs", [bad])
                )

    def test_duplicate_reference_is_rejected(self) -> None:
        ref = "reports/PF_CONSOLE001_VISIBLE_CONSOLE_RUNTIME_PASS_20260817.md"
        self.reject(
            lambda value: self.domain(value, "session_lifecycle")["capabilities"][0]
            .__setitem__("evidence_refs", [ref, ref])
        )

    # --- schema discipline -----------------------------------------------

    def test_unknown_status_is_rejected(self) -> None:
        self.reject(
            lambda value: self.domain(value, "inventory")["capabilities"][0]
            .__setitem__("status", "mostly_done")
        )

    def test_status_vocabulary_cannot_drift(self) -> None:
        self.assertEqual(
            STATUSES,
            ("not_started", "in_progress", "blocked", "runtime_pass", "complete"),
        )
        self.reject(
            lambda value: value["policy"].__setitem__(
                "statuses", ["not_started", "complete"]
            )
        )

    def test_extra_and_missing_fields_are_rejected(self) -> None:
        self.reject(
            lambda value: self.domain(value, "inventory").__setitem__("extra", 1)
        )
        self.reject(lambda value: self.domain(value, "inventory").pop("capabilities"))
        self.reject(
            lambda value: self.domain(value, "inventory")["capabilities"][0].pop("notes")
        )

    def test_schema_and_shape_guards(self) -> None:
        self.reject(lambda value: value.__setitem__("schema", 2))
        self.reject(lambda value: value.__setitem__("schema", True))
        self.reject(lambda value: value.__setitem__("domains", []))
        self.reject(
            lambda value: self.domain(value, "inventory").__setitem__("capabilities", [])
        )

    def test_duplicate_ids_are_rejected(self) -> None:
        def duplicate_capability(value: dict) -> None:
            domain = self.domain(value, "inventory")
            domain["capabilities"].append(copy.deepcopy(domain["capabilities"][0]))

        self.reject(duplicate_capability)
        self.reject(
            lambda value: value["domains"].append(copy.deepcopy(value["domains"][0]))
        )

    def test_identifiers_must_be_snake_case(self) -> None:
        self.reject(
            lambda value: self.domain(value, "inventory").__setitem__("id", "Inventory")
        )
        self.reject(
            lambda value: self.domain(value, "inventory")["capabilities"][0]
            .__setitem__("id", "Backpack Display")
        )

    def test_booleans_must_be_real_booleans(self) -> None:
        self.reject(
            lambda value: self.domain(value, "inventory").__setitem__("domain_complete", 0)
        )
        self.reject(
            lambda value: self.domain(value, "inventory")["capabilities"][0]
            .__setitem__("required", 1)
        )

    def test_domain_needs_at_least_one_required_capability(self) -> None:
        def mutate(value: dict) -> None:
            for cap in self.domain(value, "inventory")["capabilities"]:
                cap["required"] = False

        self.reject(mutate)

    def test_complete_row_needs_a_test_reference(self) -> None:
        def mutate(value: dict) -> None:
            cap = self.domain(value, "inventory")["capabilities"][0]
            cap["status"] = COMPLETE
            cap["test_refs"] = []

        error = self.reject(mutate)
        self.assertIn("test ref", str(error))


if __name__ == "__main__":
    unittest.main()
