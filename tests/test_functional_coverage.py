from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import subprocess
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
        # Any not_started row anywhere in the document will do.  This used to look
        # only in `inventory`, which made the invariant hostage to that one domain's
        # progress: chief round 75 flipped inventory/use_drop_sell to in_progress
        # (USE-DROP-SELL-001), inventory ran out of not_started rows, and the fixture
        # failed to find a subject even though the rule it guards was untouched.
        def mutate(value: dict) -> None:
            for domain in value["domains"]:
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

    # --- ratchet: a graded claim is a watched claim ----------------------

    def test_every_graded_row_carries_at_least_one_test_reference(self) -> None:
        """A row with evidence and no test is a claim nobody watches.

        The verifier only demands a test reference for ``complete``. That left
        eight graded rows with evidence and no test at all until 2026-08-17, so
        this ratchet pins the repaired state: any row that is not
        ``not_started`` must name a test. Adding evidence for a new behavior
        now costs a test in the same change.
        """
        unwatched = [
            (domain["id"], cap["id"], cap["status"])
            for domain in self.raw["domains"]
            for cap in domain["capabilities"]
            if cap["status"] != "not_started" and not cap["test_refs"]
        ]
        self.assertEqual(unwatched, [])

    def test_every_cited_test_path_is_a_module_that_defines_tests(self) -> None:
        """A citation must point at something that can actually fail.

        The verifier only proves the cited path exists inside the repository.
        That is not enough: a golden fixture, a package marker, or a helper
        module would all satisfy it while watching nothing. Every citation
        must be a ``tests/`` module that defines at least one test method.
        """
        offenders = []
        for domain in self.raw["domains"]:
            for cap in domain["capabilities"]:
                for ref in cap["test_refs"]:
                    path = ROOT / ref
                    if (
                        not ref.startswith("tests/")
                        or path.suffix != ".py"
                        or not path.is_file()
                        or "def test_" not in path.read_text(encoding="utf-8")
                    ):
                        offenders.append((domain["id"], cap["id"], ref))
        self.assertEqual(offenders, [])

    def test_not_started_rows_stay_empty_on_both_sides(self) -> None:
        carrying = [
            (domain["id"], cap["id"])
            for domain in self.raw["domains"]
            for cap in domain["capabilities"]
            if cap["status"] == "not_started"
            and (cap["evidence_refs"] or cap["test_refs"])
        ]
        self.assertEqual(carrying, [])


class CoverageEvidenceIsVisibleToVersionControlTests(unittest.TestCase):
    """Every path the coverage matrix cites has to be IN the repository.

    Round 87 wrote this check for the hypothesis ledger after finding a report
    that had been ignored since the day it was written while two active entries
    cited it as evidence.  The check it added lives beside
    verify_hypothesis_ledger.py and reads the ledger only, so the coverage
    matrix -- the other file in this repository that publishes claims backed by
    named documents -- kept its own copy of the same defect.

    Round 93 swept it and found thirty-three of one hundred and twelve cited
    paths excluded by .gitignore, cited by seventeen capability rows across
    eight domains, nine of them graded runtime_pass.  Every one of those files
    existed on the disk that wrote it, so test_declared_refs_all_exist above --
    which asks the filesystem -- was green for all thirty-three.  Existence on
    the author's machine and presence in the repository are different
    properties, and only the second one is what the word evidence means to
    whoever clones this next.  The practical cost was concrete rather than
    theoretical: verify_functional_coverage.py exits 2 on a fresh clone, so the
    gate this project calls green could not be reproduced from git anywhere.

    The remedy when this goes red is to ADD AN ALLOWLIST LINE to .gitignore.
    Do not drop the reference to make it green: the reference is the part that
    is correct, and dropping it deletes the only record of what a claim rests
    on.  That is the same instruction round 87 left on the ledger check, and it
    is repeated here because this is where the next reader will be standing.

    This is a test rather than a guard inside verify_functional_coverage.py on
    purpose.  It is the one question in this area that cannot be answered from
    the working tree alone -- it has to ask git -- and the verifier stays
    runnable with the standard library and no repository.
    """

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "--no-optional-locks", *args],
            cwd=ROOT, capture_output=True, text=True,
        )

    def setUp(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git is not on PATH")
        if self._git("rev-parse", "--is-inside-work-tree").returncode != 0:
            self.skipTest("not a git work tree")

    @staticmethod
    def _cited_paths() -> list[tuple[str, str, str]]:
        """(domain, capability, ref) for every ref the matrix publishes."""
        raw = json.loads(DEFAULT_MATRIX.read_text(encoding="utf-8"))
        cited: list[tuple[str, str, str]] = []
        for domain in raw["domains"]:
            for cap in domain["capabilities"]:
                for ref in list(cap["evidence_refs"]) + list(cap["test_refs"]):
                    cited.append((domain["id"], cap["id"], ref))
        return cited

    @staticmethod
    def _ignored(paths, cwd) -> set[str]:
        """Which of these paths does git exclude?  Batched, and NOT over stdin.

        The first version of this helper passed the paths to check-ignore on
        stdin, and the trap below caught what that costs: subprocess text mode
        translates the separator to CRLF on Windows, git then compares a path
        with a carriage return glued to it, matches nothing, and the sweep
        reports a clean bill of health on the one machine that runs the gate.
        A silent false green is worse than the defect it was written to find,
        so the paths go in argv, where nothing rewrites them, in chunks that
        stay well inside the Windows command line limit.  The trap and the
        sweep call THIS function rather than each keeping their own copy of the
        invocation, because the version that went wrong was the copy the trap
        was not exercising.
        """
        found: set[str] = set()
        paths = list(paths)
        for start in range(0, len(paths), 50):
            chunk = paths[start:start + 50]
            result = subprocess.run(
                ["git", "--no-optional-locks", "check-ignore", "--", *chunk],
                cwd=str(cwd), capture_output=True, text=True,
            )
            if result.returncode not in (0, 1):
                raise AssertionError(
                    f"check-ignore failed to run: {result.returncode} {result.stderr!r}"
                )
            for line in result.stdout.splitlines():
                line = line.strip().replace("\\", "/")
                if line:
                    found.add(line)
        return found

    def test_no_cited_path_is_excluded_by_gitignore(self) -> None:
        cited = self._cited_paths()
        self.assertGreater(
            len(cited), 100, "the sweep found suspiciously few refs to check"
        )
        ignored = self._ignored((ref for _, _, ref in cited), ROOT)
        offenders = sorted(
            (domain, cap, ref)
            for domain, cap, ref in cited
            if ref.replace("\\", "/") in ignored
        )
        self.assertEqual(
            offenders, [],
            "the coverage matrix cites files that version control cannot see, "
            "so a fresh clone would not contain the evidence these rows rest "
            "on and the coverage verifier exits non-zero on one. Add an "
            "allowlist line to .gitignore -- do NOT drop the reference, "
            "because the reference is the part that is correct: "
            + repr(offenders),
        )

    def test_every_cited_path_exists_on_disk_too(self) -> None:
        # Deliberately kept next to the visibility check rather than relying on
        # test_declared_refs_all_exist: the pair of properties is the point,
        # and a reader who deletes one should see the other lose its meaning.
        missing = [
            (domain, cap, ref)
            for domain, cap, ref in self._cited_paths()
            if not (ROOT / ref).is_file()
        ]
        self.assertEqual(missing, [], f"the matrix cites missing paths: {missing!r}")

    def test_the_guard_actually_fires_on_an_ignored_path(self) -> None:
        """A check that has never been seen to fail is not a check."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(
                subprocess.run(
                    ["git", "init", "-q", str(root)], capture_output=True
                ).returncode, 0,
            )
            (root / "ignored.md").write_text("evidence", encoding="utf-8")
            (root / "visible.md").write_text("evidence", encoding="utf-8")
            (root / ".gitignore").write_text("ignored.md\n", encoding="utf-8")
            reported = self._ignored(["ignored.md", "visible.md"], root)
        self.assertIn("ignored.md", reported, "check-ignore missed an ignored file")
        self.assertNotIn("visible.md", reported, "check-ignore over-reported")

    def test_the_thirty_three_files_round_93_added_are_still_visible(self) -> None:
        """The specific debt this check was written for, pinned by name.

        The sweep above would catch these again if somebody removed their
        allowlist lines, but it would report them as three of thirty-three
        anonymous paths.  This test names the failure mode instead: these are
        the Codex-era capture write-ups that back nine runtime_pass rows, and
        they have been dropped from .gitignore by accident once already, in
        round 81, when four lanes edited that file in the same round.
        """
        pinned = [
            "reports/PF_RE_V67_to_V87_Walk_Gait_20260813.md",
            "reports/PF_RE_V92_Runtime_and_V93_Five_Proven_Walkers_20260814.md",
            "reports/PF_RE_V135_Q3020_Conversation_Handshake_Pass_20260815.md",
            "reports/PF_RE_V137_MARKER1_TeleportVital_Transport_Pass_20260815.md",
        ]
        cited = {ref for _, _, ref in self._cited_paths()}
        for ref in pinned:
            with self.subTest(ref=ref):
                self.assertIn(ref, cited, "the matrix stopped citing a pinned report")
                self.assertTrue((ROOT / ref).is_file(), ref)
                self.assertNotEqual(
                    self._git("check-ignore", "-q", ref).returncode, 0,
                    f"{ref} is ignored again -- see the round 93 block in .gitignore",
                )


if __name__ == "__main__":
    unittest.main()
