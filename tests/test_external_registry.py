"""EXTERNAL-RE-READER-001 - prove the deliverable reader reads and refuses.

tools/pf_external_registry.py is the first code in this repository that reads
the Codex RE deliverable tables in ../pf_bridge/external/ (Panya order
2026-08-23 18:22 item 5 made the gap a visible work item; her ruling the same
evening, 20:39, put the tables on the remote).  These tests hold it to the two
promises its docstring makes:

  1. When the tables are the pinned snapshot, every cross-table invariant
     holds and the documented golden example (TriggerCastSkillVital, the one
     00_SEARCH_HERE_FIRST.md prints in full) comes back byte-identical.
  2. When the tables are ABSENT, WRONG or MUTATED, the reader refuses loudly:
     no partial answers, no best-effort rows, exit codes that say why.

The mutation tests copy the real tables into a temp directory and break ONE
thing at a time, running with check_sha off - so they prove the structural
checks catch what the file hash would otherwise mask.  They need the real
tables as raw material, so they sit behind the same precondition as the happy
path.  The refusal-when-absent test needs nothing and runs everywhere - the
machine the skip pin protects is exactly the machine where absence is real
(the single-repo gate checkout).

These tests import nothing from src/, open no socket, touch no database and
launch no game process.  They read five committed TSV files and a temp copy.
The words "Game" + "Client" never appear joined anywhere in this file, on
purpose: the Windows gate builds its pytest exclusion list by grepping test
files for that token (gate-windows.yml, exclusion step), and this module must
NOT be excluded there - the gate runner is exactly the machine where the
tables are absent and the refusal tests plus the 10 pinned skips are real.
ASCII only, on purpose: the bridge console is code page 874.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from pf_preconditions import EXTERNAL_RE_TABLES  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "pf_external_registry", ROOT / "tools" / "pf_external_registry.py")
reader = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(reader)


def _run_cli(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = reader.main(argv)
    return code, out.getvalue()


class RefusalWithoutTablesTests(unittest.TestCase):
    """Run everywhere: absence is answered with REFUSED, exit 3, no traceback."""

    def test_cli_refuses_an_empty_base_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = _run_cli(["--stats", "--base", tmp])
        self.assertEqual(code, 3)
        self.assertIn("REFUSED", out)

    def test_verify_spans_refuses_when_nothing_is_present(self):
        # Tables absent AND image absent: the tables refusal fires first
        # (external_dir_present is checked before any mode dispatch), so the
        # message names the tables.  Asserted exactly - the adversary pass
        # caught the first draft claiming the opposite order in a comment
        # while asserting so little that either order would have passed.
        with tempfile.TemporaryDirectory() as tmp:
            code, out = _run_cli([
                "--verify-spans", str(Path(tmp) / "no_image_here.bin"),
                "--base", tmp])
        self.assertEqual(code, 3)
        self.assertIn("REFUSED: the deliverable tables are not present", out)

    def test_verify_spans_refuses_an_empty_image_path(self):
        # An unset %VAR% in a bridge batch file arrives here as "".  The
        # first draft fell through to --stats and exited 0 with zero spans
        # hashed (adversary, R131); now it must refuse.
        # Empty placeholder files are enough: the presence probe only asks
        # whether the five names exist, and the empty-path refusal fires
        # before any table is opened - so this runs on table-less machines.
        with tempfile.TemporaryDirectory() as tmp:
            for name in reader.PINS:
                (Path(tmp) / name).touch()
            code, out = _run_cli(["--verify-spans", "", "--base", tmp])
        self.assertEqual(code, 3)
        self.assertIn("REFUSED: --verify-spans got an empty image path", out)

    def test_pins_are_internally_consistent(self):
        self.assertEqual(sorted(reader.PINS), [
            "PF_FIELD_VALIDATION.tsv", "PF_INPUT_INVENTORY.tsv",
            "PF_PROTOCOL_REGISTRY.tsv", "PF_RUNTIME_CLASSMAP.tsv",
            "PF_SERIALIZER_FIELDS.tsv"])
        for name, pin in reader.PINS.items():
            self.assertEqual(len(pin["sha256"]), 64, name)
            self.assertGreater(pin["rows"], 0, name)
            self.assertEqual(len(pin["header"]), len(set(pin["header"])), name)


@EXTERNAL_RE_TABLES.skip_unless_present()
class DeliverableSnapshotTests(unittest.TestCase):
    """The pinned snapshot: shas, counts, invariants, the golden example."""

    def test_cross_check_holds_and_summary_matches_the_letter(self):
        summary = reader.cross_check()
        # The 2026-08-23 20:39 letter counted these same numbers by hand on
        # the bridge; the reader must reproduce them from the committed bytes.
        self.assertEqual(summary["messages"], 519)
        self.assertEqual(summary["field_rows"], 6931)
        self.assertEqual(summary["field_groups"], 1038)
        self.assertEqual(summary["directions"], {"W": 3464, "R": 3467})
        self.assertEqual(summary["unknown_serializer_messages"], 16)
        self.assertEqual(summary["spanless_field_rows"], 32)
        self.assertEqual(summary["empty_tag_rows"], 202)

    def test_golden_trigger_cast_skill_vital(self):
        # The exact example 00_SEARCH_HERE_FIRST.md prints, byte for byte.
        row = reader.protocol_registry()["TriggerCastSkillVital"]
        self.assertEqual(row["serializer_va"], "0x00600A60")
        self.assertEqual(row["handler_va"], "0x00601810")
        self.assertEqual(row["vtable_va"], "0x00F3175C")
        fields = reader.fields_for("TriggerCastSkillVital", "W")
        self.assertEqual(
            [(f["order"], f["tag"], f["field_offset"], f["len"]) for f in fields],
            [("1", "0x0F", "+0x14", "2"),
             ("2", "0x08", "+0x16", "1"),
             ("3", "0x14", "+0x18", "4")])
        self.assertEqual(
            set(f["span_sha256"] for f in fields),
            {"396200629ab4082b8eef730dda809124f5df8eca6f0ced5419d7a2ac7e3500ec"})
        self.assertEqual(set(f["span_start"] for f in fields), {"0x00600A60"})
        self.assertEqual(set(f["span_end"] for f in fields), {"0x00600AD7"})

    def test_cli_stats_and_message_exit_zero(self):
        code, out = _run_cli(["--stats"])
        self.assertEqual(code, 0)
        self.assertIn("cross-check: OK", out)
        code, out = _run_cli(["--message", "TriggerCastSkillVital"])
        self.assertEqual(code, 0)
        self.assertIn("0x00600A60", out)
        code, out = _run_cli(["--message", "NoSuchMessageEver"])
        self.assertEqual(code, 1)
        self.assertIn("NOT FOUND", out)
        for text in (out,):
            text.encode("ascii")  # cp874 tripwire: CLI output stays ASCII


@EXTERNAL_RE_TABLES.skip_unless_present()
class MutationRefusalTests(unittest.TestCase):
    """Copy the real tables, break one thing, and demand a loud failure.

    check_sha is off in every test here ON PURPOSE: with the hash pin active
    any mutation trivially fails at the hash, and the structural checks -
    the ones that must survive a legitimate re-pin - would never be
    exercised at all.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        for name in reader.PINS:
            shutil.copy(reader.EXTERNAL_DIR / name, self.base / name)

    def tearDown(self):
        self._tmp.cleanup()

    def _rewrite(self, name, old, new, count=1):
        path = self.base / name
        raw = path.read_bytes()
        self.assertIn(old, raw)
        path.write_bytes(raw.replace(old, new, count))

    def test_unmutated_copy_still_passes_without_sha(self):
        # The control: everything below must fail BECAUSE of its mutation,
        # not because the copy or the no-sha path is broken to begin with.
        summary = reader.cross_check(self.base, check_sha=False)
        self.assertEqual(summary["messages"], 519)

    def test_sha_pin_catches_any_edit_when_active(self):
        self._rewrite("PF_PROTOCOL_REGISTRY.tsv", b"IMAGE\n", b"IMAGe\n")
        with self.assertRaisesRegex(reader.ExternalRegistryError, "sha256"):
            reader.load_table("PF_PROTOCOL_REGISTRY.tsv", self.base)

    def test_dropped_row_fails_the_row_pin(self):
        path = self.base / "PF_PROTOCOL_REGISTRY.tsv"
        lines = path.read_bytes().splitlines(keepends=True)
        path.write_bytes(b"".join(lines[:-1]))
        with self.assertRaisesRegex(reader.ExternalRegistryError, "data rows"):
            reader.load_table("PF_PROTOCOL_REGISTRY.tsv", self.base,
                              check_sha=False)

    def test_renamed_header_column_is_refused(self):
        self._rewrite("PF_SERIALIZER_FIELDS.tsv", b"gate_condition",
                      b"gate_conditioN")
        with self.assertRaisesRegex(reader.ExternalRegistryError, "header"):
            reader.load_table("PF_SERIALIZER_FIELDS.tsv", self.base,
                              check_sha=False)

    def test_non_ascii_byte_is_refused(self):
        self._rewrite("PF_INPUT_INVENTORY.tsv", b"IMAGE-0001", b"IMAGE-000\xe9")
        with self.assertRaisesRegex(reader.ExternalRegistryError, "non-ASCII"):
            reader.load_table("PF_INPUT_INVENTORY.tsv", self.base,
                              check_sha=False)

    def test_claim_moved_outside_its_span_is_refused(self):
        # TriggerCastSkillVital field #1 claim 0x001FFE79 maps inside
        # [0x00600A60, 0x00600AD7).  0x00300000 maps to 0x00700C00 - far out.
        self._rewrite("PF_SERIALIZER_FIELDS.tsv", b"0x001FFE79",
                      b"0x00300000")
        with self.assertRaisesRegex(reader.ExternalRegistryError,
                                    "outside span"):
            reader.cross_check(self.base, check_sha=False)

    def test_garbage_hex_in_an_undelta_column_is_refused(self):
        # serializer_va is delta-checked by nothing, so before R131's
        # adversary pass a mutation here sailed through --no-sha untouched.
        # The registry-wide format gate must catch it now.
        self._rewrite("PF_PROTOCOL_REGISTRY.tsv", b"\t0x00600A60\t",
                      b"\t0xZZ600A60\t")
        with self.assertRaisesRegex(reader.ExternalRegistryError,
                                    "neither UNKNOWN nor a hex number"):
            reader.cross_check(self.base, check_sha=False)

    def test_non_integer_order_is_a_refusal_not_a_traceback(self):
        # The first draft let int() raise a raw ValueError here, which broke
        # the tool's own refusal contract (adversary, R131).
        self._rewrite("PF_SERIALIZER_FIELDS.tsv",
                      b"TriggerCastSkillVital\tW\t1\t",
                      b"TriggerCastSkillVital\tW\tx\t")
        with self.assertRaisesRegex(reader.ExternalRegistryError,
                                    "not a decimal integer"):
            reader.cross_check(self.base, check_sha=False)

    def test_broken_name_join_is_refused(self):
        # Rename one message in the registry only: both directions of the
        # join break at once, and the reader must say so, not guess.
        self._rewrite("PF_PROTOCOL_REGISTRY.tsv",
                      b"TriggerCastSkillVital\t", b"TriggerCastSkillVitaX\t")
        with self.assertRaisesRegex(reader.ExternalRegistryError,
                                    "name join broken"):
            reader.cross_check(self.base, check_sha=False)


if __name__ == "__main__":
    unittest.main()
