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

import collections
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
            "PF_DATA_EVIDENCE.tsv", "PF_FIELD_VALIDATION.tsv",
            "PF_INPUT_INVENTORY.tsv", "PF_PROTOCOL_PRIORITY.tsv",
            "PF_PROTOCOL_REGISTRY.tsv", "PF_RUNTIME_CLASSMAP.tsv",
            "PF_SERIALIZER_FIELDS.tsv", "PF_TAG_CENSUS.tsv"])
        for name, pin in reader.PINS.items():
            self.assertEqual(len(pin["sha256"]), 64, name)
            self.assertGreater(pin["rows"], 0, name)
            self.assertEqual(len(pin["header"]), len(set(pin["header"])), name)

    def test_the_three_late_tables_sum_to_the_820_rows_the_letter_pinned(self):
        # The bridge letter of 2026-08-23 20:39 named these three by hand and
        # counted 820 data rows across them before Panya ruled they could go
        # on the remote.  If a re-pin ever moves one of them, this says so in
        # the terms the ruling was made in, not just as three loose numbers.
        late = ("PF_PROTOCOL_PRIORITY.tsv", "PF_DATA_EVIDENCE.tsv",
                "PF_TAG_CENSUS.tsv")
        self.assertEqual(sum(reader.PINS[n]["rows"] for n in late), 820)

    def test_only_two_tags_are_allowed_a_proven_semantic(self):
        # A width is not a type.  Nine of the eleven census tags say UNKNOWN,
        # and this repository must keep it that way until evidence says
        # otherwise - the same rule GT-052 closed on when no legend for
        # n_TARGET could be found.
        self.assertEqual(reader.CENSUS_PROVEN_SEMANTICS,
                         {"0x12": "uint16", "0x2A": "float32"})


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

    def test_the_late_tables_are_internally_consistent(self):
        # R145: the checks that only became runnable when the last three
        # tables reached the remote.  These are INTERNAL-CONSISTENCY checks -
        # two of the three tables are projections of PF_SERIALIZER_FIELDS, so
        # they assert a projection matches its source, not that two
        # independent passes agreed (R145 adversary, defects 1/2/4).
        summary = reader.cross_check()
        self.assertEqual(summary["census_tags"], 11)
        self.assertEqual(summary["census_covered_field_rows"], 2783)
        self.assertEqual(summary["field_offset_classes"], 8)
        self.assertEqual(summary["priority_serializer_closed"], 338)
        self.assertEqual(summary["priority_serializer_open"], 181)
        self.assertEqual(summary["static_open_set_symmetric_difference"], 0)
        self.assertEqual(summary["evidence_rows"], 290)
        self.assertEqual(summary["evidence_joined_to_inventory"], 290)
        self.assertEqual(summary["evidence_parse_pass"], 287)

    def test_the_priority_open_set_is_a_projection_of_field_offset(self):
        # The priority table's serializer_status is a projection of the
        # serializer table's field_offset column (serializer_blockers is the
        # deduped set of its UNKNOWN(...) reasons; status is OPEN iff blockers
        # exist).  So this equality asserts the projection has not been
        # hand-edited out of sync - NOT an independent agreement.  It is the
        # same 181-message static-open set the GT-047 guard pins by digest,
        # but both come from field_offset, so it is one witness, not two.
        priority = reader.protocol_priority()
        by_status = set(name for name, row in priority.items()
                        if row["serializer_status"] == "OPEN")
        by_offset = set(row["message"] for row in reader.serializer_fields()
                        if "UNKNOWN(" in row["field_offset"])
        self.assertEqual(len(by_status), 181)
        self.assertEqual(by_status, by_offset)

    def test_census_widths_match_every_row_that_carries_the_tag(self):
        census = reader.tag_census()
        self.assertEqual(sorted(census), [
            "0x05", "0x08", "0x0B", "0x0F", "0x12", "0x14", "0x19", "0x1F",
            "0x26", "0x2A", "0x32"])
        widths = {tag: int(row["len"]) for tag, row in census.items()}
        self.assertEqual(widths["0x0B"], 1)
        self.assertEqual(widths["0x12"], 2)
        self.assertEqual(widths["0x2A"], 4)
        self.assertEqual(widths["0x32"], 8)
        counted = collections.Counter(
            row["tag"] for row in reader.serializer_fields()
            if row["tag"] in census)
        for tag, row in census.items():
            self.assertEqual(counted[tag], int(row["frequency_in_A2"]), tag)

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

    def test_census_width_disagreeing_with_a_field_row_is_refused(self):
        # Widen tag 0x0B in the census from 1 to 3: 555 serializer rows now
        # contradict it, and the reader must name the first one rather than
        # average the two passes into a number nobody measured.
        self._rewrite("PF_TAG_CENSUS.tsv", b"0x0B\t1\tFIXED", b"0x0B\t3\tFIXED")
        with self.assertRaisesRegex(reader.ExternalRegistryError,
                                    "census pins"):
            reader.cross_check(self.base, check_sha=False)

    def test_census_frequency_drifting_from_the_row_count_is_refused(self):
        self._rewrite("PF_TAG_CENSUS.tsv", b"\t555\tUNKNOWN", b"\t554\tUNKNOWN")
        with self.assertRaisesRegex(reader.ExternalRegistryError,
                                    "frequency_in_A2"):
            reader.cross_check(self.base, check_sha=False)

    def test_a_new_semantic_claim_in_the_census_is_refused(self):
        # The dangerous direction: a regenerated table quietly upgrading
        # UNKNOWN to a type name.  Absorbing that silently would let a guess
        # made elsewhere become this repository's belief.
        self._rewrite("PF_TAG_CENSUS.tsv", b"0x32\t8\tFIXED\t541\tUNKNOWN",
                      b"0x32\t8\tFIXED\t541\tuint64")
        with self.assertRaisesRegex(reader.ExternalRegistryError,
                                    "proven_semantics"):
            reader.cross_check(self.base, check_sha=False)

    def test_a_membership_swap_in_the_priority_open_set_is_refused(self):
        # Count-preserving attack, the one the R144 adversary pass found
        # against the GT-047 guard: flip one message OPEN->CLOSED and another
        # CLOSED->OPEN.  338/181 still holds; the set equality does not.
        # Attribute is CLOSED, GSCN_RunTimeProtocolReq is OPEN (measured).
        self._rewrite("PF_PROTOCOL_PRIORITY.tsv",
                      b"Attribute\t3\tremaining\tN/A\tN/A\tKNOWN\tN/A\tCLOSED",
                      b"Attribute\t3\tremaining\tN/A\tN/A\tKNOWN\tN/A\tOPEN")
        raw = (self.base / "PF_PROTOCOL_PRIORITY.tsv").read_bytes()
        head, sep, tail = raw.partition(b"\nGSCN_RunTimeProtocolReq\t")
        self.assertTrue(sep)
        line, nl, rest = tail.partition(b"\n")
        self.assertIn(b"\tOPEN\t", line)
        (self.base / "PF_PROTOCOL_PRIORITY.tsv").write_bytes(
            head + sep + line.replace(b"\tOPEN\t", b"\tCLOSED\t", 1) + nl + rest)
        # Either self-consistency check may fire first: Attribute flipped to
        # OPEN now carries no blockers, and GSCN flipped to CLOSED still does.
        with self.assertRaisesRegex(
                reader.ExternalRegistryError,
                "OPEN must carry blockers|CLOSED must not|static-open sets disagree"):
            reader.cross_check(self.base, check_sha=False)

    def test_a_garbage_field_offset_is_refused(self):
        # field_offset was previously read only for the substring "UNKNOWN(",
        # so a cell could become anything.  The grammar gate now refuses it
        # (R145 adversary, defect 3 / attack A3).
        self._rewrite("PF_SERIALIZER_FIELDS.tsv",
                      b"TriggerCastSkillVital\tW\t1\t0x0F\t+0x14",
                      b"TriggerCastSkillVital\tW\t1\t0x0F\t@@@NOPE@@@")
        with self.assertRaisesRegex(reader.ExternalRegistryError,
                                    "matches no known class"):
            reader.cross_check(self.base, check_sha=False)

    def test_changing_an_unknown_reason_desyncs_priority_and_is_refused(self):
        # Attack A1 variant that preserves the field_offset grammar counts
        # (UNKNOWN stays UNKNOWN) but changes a reason string, so the priority
        # table's serializer_blockers no longer matches the field_offset
        # reasons for that message.  Isolates the blocker-desync check from
        # the grammar gate.  All 5 rows carrying this reason are edited so the
        # priority table (which keeps the old reason) goes out of sync.
        self._rewrite(
            "PF_SERIALIZER_FIELDS.tsv",
            b"UNKNOWN(invalid_parameter_import_call_wire_effect_unproved)",
            b"UNKNOWN(invalid_parameter_import_call_wire_effect_RENAMED)",
            count=999)
        with self.assertRaisesRegex(reader.ExternalRegistryError,
                                    "serializer_blockers"):
            reader.cross_check(self.base, check_sha=False)

    def test_an_open_row_with_no_blocker_is_refused(self):
        # Attack C2: a single-row self-contradiction - serializer_status OPEN
        # while serializer_blockers is N/A.  Previously invisible because the
        # blockers column was never read.
        self._rewrite(
            "PF_PROTOCOL_PRIORITY.tsv",
            b"ItemOperateVitalRes\t",
            b"ItemOperateVitalRes\t", count=1)  # anchor exists; edit blockers below
        raw = (self.base / "PF_PROTOCOL_PRIORITY.tsv").read_bytes()
        head, sep, tail = raw.partition(b"\nItemOperateVitalRes\t")
        line, nl, rest = tail.partition(b"\n")
        self.assertIn(b"\tOPEN\t", line)
        # blank the blockers field: replace its non-N/A content with N/A
        import re as _re
        newline = _re.sub(rb"\tOPEN\t[^\t]+\t", b"\tOPEN\tN/A\t", line, count=1)
        self.assertNotEqual(newline, line)
        (self.base / "PF_PROTOCOL_PRIORITY.tsv").write_bytes(
            head + sep + newline + nl + rest)
        with self.assertRaisesRegex(reader.ExternalRegistryError,
                                    "OPEN must carry blockers"):
            reader.cross_check(self.base, check_sha=False)

    def test_evidence_digest_not_matching_inventory_is_refused(self):
        # Attack D2: swap an evidence sha256 for another valid upper-hex 64.
        # The shape gate passes; the join to PF_INPUT_INVENTORY does not.
        self._rewrite(
            "PF_DATA_EVIDENCE.tsv",
            b"674B1CFC5254AA94B52F8ACB8F5236B331AF49E0E58D7474E94E42AF2DADB508",
            b"2FB6CF1C74475BE424FE73F194D8FA1FF2EDCCAD25B4A566912AB9DF88A84192")
        with self.assertRaisesRegex(reader.ExternalRegistryError,
                                    "does not match inventory"):
            reader.cross_check(self.base, check_sha=False)

    def test_a_relabelled_nonstandard_grammar_row_is_refused(self):
        # Attack D1: the docstring pins 287 PASS / 3 NONSTANDARD_GRAMMAR; the
        # three non-PASS rows must not quietly become PASS or anything else.
        self._rewrite("PF_DATA_EVIDENCE.tsv",
                      b"\tNONSTANDARD_GRAMMAR\t", b"\tTOTALLY_FINE\t", count=1)
        with self.assertRaisesRegex(reader.ExternalRegistryError,
                                    "parse_status split"):
            reader.cross_check(self.base, check_sha=False)

    def test_a_duplicate_evidence_id_is_refused(self):
        self._rewrite("PF_DATA_EVIDENCE.tsv", b"DATA-1778", b"DATA-1777")
        with self.assertRaisesRegex(reader.ExternalRegistryError,
                                    "duplicate evidence_id"):
            reader.cross_check(self.base, check_sha=False)

    def test_a_lower_cased_evidence_digest_is_refused(self):
        # The two tables really do use different cases.  Normalising here
        # would let a table change its own convention with nothing saying so.
        self._rewrite(
            "PF_DATA_EVIDENCE.tsv",
            b"674B1CFC5254AA94B52F8ACB8F5236B331AF49E0E58D7474E94E42AF2DADB508",
            b"674b1cfc5254aa94b52f8acb8f5236b331af49e0e58d7474e94e42af2dadb508")
        with self.assertRaisesRegex(reader.ExternalRegistryError,
                                    "upper-case hex"):
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
