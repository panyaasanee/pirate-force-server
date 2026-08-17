"""Pin the Foundation/legacy seam and the evidence manifests that back the matrix.

M13 established three facts that nothing in the suite was watching:

  1. The Foundation server is not an alternative to the frozen V141 scenario
     runner.  ``app.py`` loads ``current/pf_login_game_server_v141.py`` and
     ``runtime.make_state_class`` returns a subclass of ``legacy.GameSessionState``
     that calls ``super().dispatch()`` for everything it does not override.  A
     ``runtime_pass`` produced by a Foundation process therefore does not imply
     that Foundation code produced the behavior.
  2. The five opt-in scenario modes are mutually exclusive, so no single server
     run can exhibit every green row, and the launcher used by the playbook
     enables none of them.
  3. Every ``reports/*.manifest`` line still hashes to its recorded sha256, but
     four ``runtime_pass`` rows cite no manifest-backed report at all.

These tests freeze that state.  They are deliberately structural: they assert
what the seam *is*, not that any particular capability works.  A change that
re-points the legacy module, flattens the subclass, makes the modes composable,
or grows the manifest-debt list has to say so in the same commit.
"""

import ast
import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
REPORTS = ROOT / "reports"
COVERAGE = ROOT / "docs" / "FUNCTIONAL_COVERAGE.json"
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.runtime import make_state_class  # noqa: E402

# The frozen module the Foundation server is built on.  Changing this pin means
# the whole evidence base moves to a different legacy baseline.
PINNED_LEGACY_MODULE = "current/pf_login_game_server_v141.py"

# The five strictly opt-in scenario parameters of make_state_class.  At most one
# may be active in a run; see test_scenario_modes_are_mutually_exclusive.
SCENARIO_MODES = (
    "scenario",
    "scene_load_scenario",
    "population_scenario",
    "item_move_capture_scenario",
    "item_move_hypothesis_scenario",
)

# Rows graded runtime_pass whose evidence has no .manifest, i.e. whose runtime
# claim rests on report prose rather than on hash-pinned artifacts.  This is
# recorded debt, not an accepted practice: the set may shrink, and shrinking it
# is expected to update this list in the same commit.
MANIFEST_DEBT_RUNTIME_PASS = {
    "movement/npc_locomotion_presentation",
    "movement/teleport_transport",
    "npc_interaction/npc_conversation_handshake",
    "npc_interaction/conversation_operation_sequence",
}

# sha256 over every graded field of every row -- id, status, required, evidence
# refs, test refs, next_missing_behavior, domain_complete -- and nothing else.
# `notes` is excluded on purpose so prose corrections stay cheap while any grade
# movement has to be deliberate.
GRADE_SUBSET_SHA256 = (
    # This pin covers one deliberate movement: inventory/
    # move_known_item_any_free_slot moved blocked -> in_progress because the
    # blocker it recorded (hypothesis-ledger review) was resolved by the owner:
    # HYP-PF-010 landed as M3 (commit abf3696) and the owner-approved M4
    # runtime hookup wired the generalized free-slot move into the runtime
    # ItemOperate lane behind the existing opt-in scenario, with occupied/
    # unknown/out-of-range/same-slot targets failing closed.  The row gains
    # tests/test_item_move_generalized.py per the same-day test-ref ratchet.
    # Not runtime_pass yet: the first real-client acceptance run is GT-002.
    # Previous pin 0EC17CBB..33A1 covered the chat/client_chat_input first
    # evidence and the opening of the eighth domain `presentation`; see the
    # eb6fef0 re-pin note in git history for the pin before that.
    "B00AE3FBE64E29AD994FB6C55F2725B85C7487A0B880059E95304E257B61B63B"
)


# Two manifest formats exist in reports/.  PIPE is the house format used by 21 of
# the 22 manifests; COLUMNS is a single earlier file whose paths are relative to
# its capture root rather than to the repository.  Both are accepted, but the
# COLUMNS set is pinned so a new report cannot quietly reintroduce the old shape.
MANIFEST_PIPE = re.compile(r"^(?P<path>[^|]+)\|(?P<size>\d+)\|(?P<sha>[0-9A-F]{64})$")
MANIFEST_COLUMNS = re.compile(r"^(?P<sha>[0-9A-F]{64})\s+(?P<size>\d+)\s+(?P<path>\S.*)$")

LEGACY_FORMAT_MANIFESTS = {
    "PF_RELATION_COMPARATOR_RUNTIME_TRACE_20260815.manifest",
}


def grade_subset(document):
    """Every field the matrix grades on, in file order, excluding prose."""
    return [
        (
            domain["id"],
            domain.get("domain_complete"),
            [
                (
                    row["id"],
                    row["status"],
                    row["required"],
                    tuple(row["evidence_refs"]),
                    tuple(row["test_refs"]),
                    row.get("next_missing_behavior"),
                )
                for row in domain["capabilities"]
            ],
        )
        for domain in document["domains"]
    ]


def grade_digest(document):
    payload = json.dumps(grade_subset(document), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def parse_manifest(text, pattern=MANIFEST_PIPE):
    """Return parsed rows, or raise ValueError naming the first bad line."""
    rows = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = pattern.match(line)
        if match is None:
            raise ValueError(f"line {number} does not match the manifest format: {line!r}")
        rows.append((match["path"], int(match["size"]), match["sha"]))
    return rows


def parse_any_manifest(path):
    pattern = MANIFEST_COLUMNS if path.name in LEGACY_FORMAT_MANIFESTS else MANIFEST_PIPE
    return parse_manifest(path.read_text(encoding="utf-8"), pattern)


def modules_mentioning(root, pattern):
    found = []
    for path in sorted(Path(root).glob("*.py")):
        if re.search(pattern, path.read_text(encoding="utf-8")):
            found.append(path.name)
    return found


class FoundationLegacySeamTests(unittest.TestCase):
    """The architectural facts behind every runtime_pass grade."""

    def test_app_pins_exactly_one_frozen_legacy_module(self):
        source = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
        pins = re.findall(r"current/pf_login_game_server_v\d+\.py", source)
        self.assertEqual(pins, [PINNED_LEGACY_MODULE])
        self.assertTrue((ROOT / PINNED_LEGACY_MODULE).is_file())

    def test_app_loads_the_legacy_module_rather_than_importing_a_package(self):
        source = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("load_legacy(", source)
        # A plain import would make the frozen script a build-time dependency and
        # silently change which copy runs.
        self.assertNotIn("import pf_login_game_server", source)

    def test_the_foundation_state_class_subclasses_frozen_v141(self):
        source = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        classes = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == "PersistentGameSessionState"
        ]
        self.assertEqual(len(classes), 1)
        bases = [ast.unparse(base) for base in classes[0].bases]
        self.assertEqual(bases, ["legacy.GameSessionState"])

    def test_dispatch_still_falls_through_to_the_frozen_implementation(self):
        source = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
        # If this ever drops to zero, Foundation stopped relaying legacy actions
        # and every passthrough row in the coverage matrix needs re-grading.
        self.assertGreater(source.count("super().dispatch(parsed)"), 0)

    def test_scenario_modes_are_mutually_exclusive(self):
        for first in range(len(SCENARIO_MODES)):
            for second in range(first + 1, len(SCENARIO_MODES)):
                kwargs = {
                    SCENARIO_MODES[first]: object(),
                    SCENARIO_MODES[second]: object(),
                }
                with self.subTest(modes=(SCENARIO_MODES[first], SCENARIO_MODES[second])):
                    with self.assertRaises(ValueError) as raised:
                        make_state_class(None, None, None, **kwargs)
                    self.assertIn("mutually exclusive", str(raised.exception))

    def test_a_single_mode_is_never_refused_for_being_exclusive(self):
        """The exclusion must reject pairs, not reject scenarios generally.

        Three of the five modes run their own allowlist validator that also
        raises ValueError, so the discriminating signal is the message, not the
        exception type.
        """
        for mode in SCENARIO_MODES:
            with self.subTest(mode=mode):
                try:
                    make_state_class(None, None, None, **{mode: object()})
                except Exception as error:  # noqa: BLE001 - any failure is fine here
                    self.assertNotIn("mutually exclusive", str(error))
                else:
                    self.fail("a bare object cannot produce a usable state class")

    def test_the_visible_launcher_enables_no_scenario_mode(self):
        launcher = (ROOT / "tools" / "run_foundation_visible.ps1").read_text(encoding="utf-8")
        for flag in (
            "--scenario", "--scene-load-scenario", "--population-scenario",
            "--item-move-capture-scenario", "--item-move-hypothesis-scenario",
        ):
            self.assertNotIn(flag, launcher)


class EvidenceManifestTests(unittest.TestCase):
    """Manifests are the only re-checkable link between a claim and bytes."""

    def setUp(self):
        self.manifests = sorted(REPORTS.glob("*.manifest"))

    def test_reports_carry_manifests_at_all(self):
        self.assertGreaterEqual(len(self.manifests), 22)

    def test_every_manifest_line_is_well_formed(self):
        for manifest in self.manifests:
            with self.subTest(manifest=manifest.name):
                rows = parse_any_manifest(manifest)
                self.assertTrue(rows, "an empty manifest pins nothing")
                for path, size, _sha in rows:
                    # Zero is legitimate and load-bearing: an empty stderr file is
                    # itself the evidence for several clean-shutdown claims.
                    self.assertGreaterEqual(size, 0)
                    self.assertNotIn("..", path)

    def test_only_the_recorded_manifests_use_the_older_column_format(self):
        odd = set()
        for manifest in self.manifests:
            try:
                parse_manifest(manifest.read_text(encoding="utf-8"), MANIFEST_PIPE)
            except ValueError:
                odd.add(manifest.name)
        self.assertEqual(odd, LEGACY_FORMAT_MANIFESTS)

    def test_no_manifest_pins_the_same_path_twice(self):
        for manifest in self.manifests:
            with self.subTest(manifest=manifest.name):
                paths = [row[0] for row in parse_any_manifest(manifest)]
                self.assertEqual(len(paths), len(set(paths)))

    def test_every_manifest_belongs_to_a_report_that_exists(self):
        for manifest in self.manifests:
            with self.subTest(manifest=manifest.name):
                self.assertTrue(manifest.with_suffix(".md").is_file())

    def test_the_parser_rejects_a_damaged_manifest(self):
        """A guard that never fails is not a guard."""
        good = "GameClient/capture_x/server.out.txt|12|" + "A" * 64
        self.assertEqual(len(parse_manifest(good)), 1)
        for damaged in (
            "GameClient/capture_x/server.out.txt|12",                      # no sha
            "GameClient/capture_x/server.out.txt|12|" + "A" * 63,          # short sha
            "GameClient/capture_x/server.out.txt|12|" + "a" * 64,          # lowercase
            "GameClient/capture_x/server.out.txt|-1|" + "A" * 64,          # negative
            "GameClient/capture_x/server.out.txt|12|" + "G" * 64,          # non-hex
            "A" * 64 + "  12  server.out.txt",                             # wrong format
        ):
            with self.subTest(damaged=damaged):
                with self.assertRaises(ValueError):
                    parse_manifest(damaged)

    def test_the_column_parser_rejects_a_pipe_line(self):
        good = "A" * 64 + "  12  server.out.txt"
        self.assertEqual(len(parse_manifest(good, MANIFEST_COLUMNS)), 1)
        with self.assertRaises(ValueError):
            parse_manifest(
                "GameClient/capture_x/server.out.txt|12|" + "A" * 64,
                MANIFEST_COLUMNS,
            )


class CoverageProvenanceTests(unittest.TestCase):
    """Ratchets that keep the M13 findings from being reopened quietly."""

    def setUp(self):
        self.document = json.loads(COVERAGE.read_text(encoding="utf-8"))
        self.rows = {
            f"{domain['id']}/{row['id']}": row
            for domain in self.document["domains"]
            for row in domain["capabilities"]
        }

    def test_grade_fields_match_the_pinned_digest(self):
        self.assertEqual(grade_digest(self.document), GRADE_SUBSET_SHA256)

    def test_the_digest_would_notice_a_single_status_change(self):
        mutated = json.loads(COVERAGE.read_text(encoding="utf-8"))
        row = mutated["domains"][0]["capabilities"][0]
        row["status"] = "complete" if row["status"] != "complete" else "blocked"
        self.assertNotEqual(grade_digest(mutated), GRADE_SUBSET_SHA256)

    def test_the_digest_ignores_prose_only_edits(self):
        mutated = json.loads(COVERAGE.read_text(encoding="utf-8"))
        mutated["domains"][0]["capabilities"][0]["notes"] += " (edited)"
        self.assertEqual(grade_digest(mutated), GRADE_SUBSET_SHA256)

    def _manifest_debt(self):
        debt = set()
        for key, row in self.rows.items():
            if row["status"] != "runtime_pass":
                continue
            backed = any(
                (ROOT / ref).with_suffix(".manifest").is_file()
                for ref in row["evidence_refs"]
            )
            if not backed:
                debt.add(key)
        return debt

    def test_manifest_debt_matches_the_recorded_list(self):
        self.assertEqual(self._manifest_debt(), MANIFEST_DEBT_RUNTIME_PASS)

    def test_every_recorded_debt_row_still_exists_and_is_runtime_pass(self):
        for key in MANIFEST_DEBT_RUNTIME_PASS:
            with self.subTest(row=key):
                self.assertIn(key, self.rows)
                self.assertEqual(self.rows[key]["status"], "runtime_pass")

    def test_the_system_message_row_records_its_legacy_ownership(self):
        notes = self.rows["chat/server_system_message"]["notes"]
        self.assertIn("no Foundation module owns it", notes)
        self.assertNotIn("has no offline test", notes)
        self.assertTrue(self.rows["chat/server_system_message"]["test_refs"])

    def test_no_foundation_module_emits_the_legacy_system_message(self):
        self.assertEqual(modules_mentioning(SRC_ROOT, r"ShowMessage"), [])
        legacy = (ROOT / PINNED_LEGACY_MODULE).read_text(encoding="utf-8")
        self.assertIn("V99_SHOW_MESSAGE_LOCAL_SERVER_ONLINE", legacy)

    def test_the_source_scanner_would_notice_a_module_that_emitted_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "clean.py").write_text("nothing to see\n", encoding="utf-8")
            self.assertEqual(modules_mentioning(root, r"ShowMessage"), [])
            (root / "chat.py").write_text("SHOW = legacy.ShowMessage\n", encoding="utf-8")
            self.assertEqual(modules_mentioning(root, r"ShowMessage"), ["chat.py"])


if __name__ == "__main__":
    unittest.main()
