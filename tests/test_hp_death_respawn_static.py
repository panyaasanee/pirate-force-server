"""Pin HP-DEATH-001's numbers to the client binary they were read from.

The `combat/hp_death_and_respawn` coverage note said HP was "a static attribute
value only".  This milestone answers, byte-exact and from the client image
alone, the one question that decides what a server would have to send:
**where does the client learn that an actor is dead?**  Because the answer is a
number-heavy one - field offsets, mask bits, vtable slots, call-site censuses -
none of those numbers may be hand-typed into the report.

These tests take the ``HP_DEATH_COUNTS`` fenced block out of

``reports/PF_HP_DEATH001_HP_DEATH_AND_RESPAWN_STATIC_20260819.md``

and compare it, key by key, against a live run of
``tools/pf_hp_death_respawn_static.py``.  If any guard in the verifier drifts,
importing the tool raises ``SystemExit`` and the first test fails; if the guards
hold but a number in the report disagrees with the binary, the comparison tests
fail.  Every number is compared EXACTLY - none of them is a "how big is the
suite today" measurement, they are all facts about one immutable, hash-pinned
image and two read-only source trees.

The tests also restate, independently of the report prose, the load-bearing
conclusions the next round would build on, so that a silent edit to either the
report or the tool cannot quietly change them:

  1. current HP is BasicAttr +0x44 (mask bit 0x0004) and max HP is +0x48
     (bit 0x0008) - the exact pair our server already emits;
  2. the client decides "dead" by comparing that field to ZERO, gated on the
     f32 at +0x58 (bit 0x0080), inside four vtable-only predicates;
  3. ReliveVital has NO inbound handler, so a server echo of it does nothing;
  4. the client picks no respawn position - the marker is used only to render a
     scene name;
  5. our side has zero encoders for all three verbs and never sets bit 0x0080.

Re-pinning when a number legitimately moves (a different client build, a server
edit that changes a call-site count): run
``py -3 tools/pf_hp_death_respawn_static.py --json`` and update the
``HP_DEATH_COUNTS`` block in the report in the same change.

These tests import nothing from ``src/``, open no socket, touch no database and
launch no GameClient.  They read one binary and a handful of text files.
"""
from __future__ import annotations

import importlib.util
import io
import json
import re
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "pf_hp_death_respawn_static.py"
REPORT = (
    ROOT / "reports"
    / "PF_HP_DEATH001_HP_DEATH_AND_RESPAWN_STATIC_20260819.md"
)
MANIFEST = REPORT.with_suffix(".manifest")
CLIENT = ROOT.parent / "GameClient" / "GameClient.local.bin"
CLIENT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
COVERAGE = ROOT / "docs" / "FUNCTIONAL_COVERAGE.json"

COUNTS_BLOCK = re.compile(r"```json HP_DEATH_COUNTS\n(?P<body>.*?)\n```", re.S)

_TOOL_MODULE = None


def load_tool():
    """Execute the verifier once; a drifted guard becomes SystemExit here."""
    global _TOOL_MODULE
    if _TOOL_MODULE is None:
        spec = importlib.util.spec_from_file_location(
            "pf_hp_death_respawn_static", TOOL)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        with redirect_stdout(io.StringIO()):
            spec.loader.exec_module(module)
        _TOOL_MODULE = module
    return _TOOL_MODULE


def report_counts() -> dict:
    match = COUNTS_BLOCK.search(REPORT.read_text(encoding="utf-8"))
    if match is None:
        raise AssertionError("the report has no ```json HP_DEATH_COUNTS block")
    return json.loads(match.group("body"))


class ArtifactsExistTests(unittest.TestCase):
    """The four files of this milestone must ship together."""

    def test_report_manifest_tool_and_client_all_exist(self):
        for path in (REPORT, MANIFEST, TOOL, CLIENT):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), path)

    def test_the_report_carries_a_machine_readable_counts_block(self):
        counts = report_counts()
        self.assertIsInstance(counts, dict)
        self.assertEqual(counts["measured_at_head"], "fc204c7")

    def test_the_manifest_pins_the_client_binary_by_hash(self):
        text = MANIFEST.read_text(encoding="utf-8")
        self.assertIn("GameClient.local.bin", text)
        self.assertIn(CLIENT_SHA, text)

    def test_the_manifest_records_the_one_matrix_row_it_edits_as_unpinned(self):
        text = MANIFEST.read_text(encoding="utf-8")
        self.assertIn("docs/FUNCTIONAL_COVERAGE.json", text)
        self.assertIn("hp_death_and_respawn", text)
        self.assertIn("HYPOTHESIS_LEDGER.json", text)
        self.assertIn("NOT modified", text)


class VerifierRunsCleanTests(unittest.TestCase):
    """Every guard in the verifier must hold against the pinned binary."""

    def test_the_verifier_imports_without_exiting(self):
        tool = load_tool()
        self.assertEqual(tool.FAILS, [], tool.FAILS)

    def test_the_verifier_read_the_pinned_client_image(self):
        self.assertEqual(load_tool().SHA, CLIENT_SHA)

    def test_the_verifier_actually_asserted_something(self):
        tool = load_tool()
        self.assertGreaterEqual(tool.NGUARD, 150)

    def test_the_verifier_is_pure_stdlib(self):
        """The Windows release gate runs `py -3` with no third-party packages."""
        source = TOOL.read_text(encoding="utf-8")
        for banned in ("import capstone", "from capstone"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, source)


class ReportMatchesTheBinaryTests(unittest.TestCase):
    """Every number printed in the report is the number the verifier counted."""

    def test_every_reported_key_exists_in_the_live_counts(self):
        self.assertEqual(sorted(report_counts()), sorted(load_tool().COUNTS))

    def test_every_reported_value_matches_exactly(self):
        reported = report_counts()
        live = load_tool().COUNTS
        for key in sorted(reported):
            with self.subTest(key=key):
                self.assertEqual(reported[key], live[key])

    def test_the_prose_headline_guard_count_matches_the_counts_block(self):
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn("**%d guards, exit 0**" % report_counts()["guards"], text)


class HpFieldIdentityTests(unittest.TestCase):
    """Conclusion 1: which field is current HP and which is max."""

    def test_current_and_max_hp_are_the_pair_the_server_already_emits(self):
        preds = load_tool().RESULT["death_predicates"]
        self.assertIn("BasicAttr+0x44", preds["hp_current_field"])
        self.assertIn("0x0004", preds["hp_current_field"])
        self.assertIn("BasicAttr+0x48", preds["hp_max_field"])
        self.assertIn("0x0008", preds["hp_max_field"])

    def test_the_death_timer_is_a_third_distinct_field(self):
        preds = load_tool().RESULT["death_predicates"]
        self.assertIn("BasicAttr+0x58", preds["death_timer_field"])
        self.assertIn("0x0080", preds["death_timer_field"])

    def test_basicattr_field_count_is_measured_from_the_serializer(self):
        counts = load_tool().COUNTS
        self.assertEqual(counts["basicattr_wire_fields_total"], 12)


class DeathDerivationTests(unittest.TestCase):
    """Conclusion 2: the client derives death from the HP value, not from a frame."""

    def test_all_four_predicates_are_named(self):
        preds = load_tool().RESULT["death_predicates"]
        self.assertEqual(preds["player_isdead"], "0x454AC0")
        self.assertEqual(preds["player_isdead_timer_expired"], "0x454A70")
        self.assertEqual(preds["npc_isdead"], "0x43BDA0")
        self.assertEqual(preds["npc_isdead_timer_expired"], "0x43BD70")

    def test_the_count_of_predicates_matches_the_named_set(self):
        tool = load_tool()
        named = {v for k, v in tool.RESULT["death_predicates"].items()
                 if k.endswith("isdead") or k.endswith("timer_expired")}
        self.assertEqual(len(named), tool.COUNTS["death_predicates_in_client"])

    def test_no_death_notification_verb_exists_for_the_local_player(self):
        """The only three death-token classes are the two Relive verbs and a pet one."""
        matches = load_tool().RESULT["registry_census"]["death_token_matches"]
        self.assertEqual(sorted(matches),
                         ["Pets_NotifySailorDeadVital", "ReliveMarkerVital",
                          "ReliveVital"])


class VerbFamilyTests(unittest.TestCase):
    """Conclusion 3: ReliveVital is request-only."""

    def test_relive_vital_has_no_client_side_decoder(self):
        fam = load_tool().RESULT["family"]
        self.assertFalse(fam["ReliveVital"]["has_client_decoder"])
        self.assertEqual(fam["ReliveVital"]["inbound_handler"], "0x00710440")

    def test_the_other_two_do_have_handlers(self):
        fam = load_tool().RESULT["family"]
        self.assertTrue(fam["ReliveMarkerVital"]["has_client_decoder"])
        self.assertTrue(fam["Pets_NotifySailorDeadVital"]["has_client_decoder"])

    def test_the_ids_are_the_name_hash_of_the_in_image_literals(self):
        tool = load_tool()
        for name, expected in (("ReliveVital", 0x1AD4),
                               ("ReliveMarkerVital", 0x3DD6),
                               ("Pets_NotifySailorDeadVital", 0x8B12)):
            with self.subTest(name=name):
                self.assertEqual(tool.name_id(name), expected)
                self.assertEqual(tool.RESULT["family"][name]["id"],
                                 "0x%04X" % expected)

    def test_the_census_adds_up(self):
        counts = load_tool().COUNTS
        self.assertEqual(
            counts["classes_with_no_inbound_handler"]
            + counts["classes_with_inbound_handler"],
            counts["registered_classes_with_resolved_vtable"])
        self.assertLessEqual(counts["registered_classes_with_resolved_vtable"],
                             counts["registered_protocol_classes"])


class ServerGapTests(unittest.TestCase):
    """Conclusion 5: our side has none of it, and the gap is one mask bit."""

    def test_zero_server_encoders_for_all_three_verbs(self):
        counts = load_tool().COUNTS
        self.assertEqual(counts["server_death_revive_encoders"], 0)
        self.assertEqual(counts["server_death_revive_dispatch"], 0)
        self.assertEqual(counts["client_death_revive_verbs"], 3)

    def test_the_death_timer_bit_is_never_emitted(self):
        counts = load_tool().COUNTS
        self.assertEqual(counts["server_references_to_basicattr_bit_0x0080"], 0)
        self.assertEqual(counts["server_references_to_actorattr_0x1A8_pair"], 0)

    def test_zero_hp_is_never_sent(self):
        self.assertEqual(
            load_tool().COUNTS["server_call_sites_emitting_zero_current_hp"], 0)

    def test_exactly_one_of_the_three_predicate_fields_is_missing(self):
        counts = load_tool().COUNTS
        self.assertEqual(counts["fields_read_by_the_death_predicate"]
                         - counts["fields_read_by_the_death_predicate_emitted_by_us"],
                         1)


class CoverageRowTests(unittest.TestCase):
    """The one matrix edit this milestone is allowed to make, and only that one."""

    def _row(self):
        matrix = json.loads(COVERAGE.read_text(encoding="utf-8"))
        for domain in matrix["domains"]:
            for row in domain["capabilities"]:
                if row["id"] == "hp_death_and_respawn":
                    return domain, row
        raise AssertionError("combat/hp_death_and_respawn row not found")

    def test_the_row_is_in_progress_and_not_runtime_pass(self):
        _domain, row = self._row()
        self.assertEqual(row["status"], "in_progress")

    def test_the_row_points_at_this_report_and_this_test(self):
        _domain, row = self._row()
        self.assertIn(
            "reports/PF_HP_DEATH001_HP_DEATH_AND_RESPAWN_STATIC_20260819.md",
            row["evidence_refs"])
        self.assertIn("tests/test_hp_death_respawn_static.py", row["test_refs"])

    def test_the_note_states_the_derivation_and_keeps_the_negatives(self):
        _domain, row = self._row()
        note = row["notes"]
        self.assertIn("+0x44", note)
        self.assertIn("client-side derivation", note.lower())
        for still_missing in ("static evidence only", "still absent on the server",
                              "no respawn placement", "not runtime-proven"):
            with self.subTest(token=still_missing):
                self.assertIn(still_missing, note.lower())

    def test_the_row_lives_under_the_combat_domain(self):
        domain, _row = self._row()
        self.assertEqual(domain["id"], "combat")


class ReportDisciplineTests(unittest.TestCase):
    """The report must keep the three evidence levels separate and claim nothing more."""

    def test_the_report_separates_byte_proof_inference_and_guess(self):
        text = REPORT.read_text(encoding="utf-8")
        for marker in ("byte-proof", "structural inference", "guess"):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_the_report_makes_no_runtime_or_original_server_claim(self):
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn("Nothing was executed", text)
        self.assertIn("ORIGINAL server", text)
        self.assertIn("`not_started` → `in_progress`", text)
        self.assertIn("`runtime_pass`", text)

    def test_the_report_does_not_call_v141_the_original_server(self):
        text = REPORT.read_text(encoding="utf-8").lower()
        self.assertNotIn("v141, the original server", text)
        self.assertNotIn("original server (v141", text)

    def test_the_report_declares_its_known_debt(self):
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn("known debt", text.lower())
        self.assertIn("NOT traced end to end", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
