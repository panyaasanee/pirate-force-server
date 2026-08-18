"""Pin UI-REFRESH-001's numbers to the client binary they were read from.

Two attended rounds (GT-011 delete-ack, GT-013 worldinfo-first logout) ended the
same way: the client parsed our frame without complaint and then did not change
UI state.  UI-REFRESH-001 answers that statically, from the read-only client
image, so its numbers must not be hand-typed either.  These tests take the
``UI_REFRESH_COUNTS`` fenced block out of

``reports/PF_UI_REFRESH001_CHARACTER_SELECT_STATE_MACHINE_STATIC_20260819.md``

and compare it, key by key, to a live run of
``tools/pf_ui_state_refresh_static.py``.  If any guard in the verifier drifts,
importing the tool records it in ``GUARDS_FAILED`` and the first test fails; if
the guards hold but a number in the report disagrees with the binary, the
comparison tests fail.  Every number is compared EXACTLY - none of them is a
"how big is the suite today" measurement, they are all facts about one
immutable, hash-pinned binary.

The tests also restate, independently of the report prose, the load-bearing
conclusions the next round would build on, so a silent edit to either the report
or the tool cannot quietly change them:

  1. the character list lives in ONE buffer, [0x1081A90]+0x180, and the image
     contains no path at all that erases a single record from it;
  2. the only frame that can rebuild that buffer is SelectActorVital 0x36EF,
     and the only frame that can append to it is CreateActorVital 0x36CF;
  3. the DeleteActorVital 0x36DB acknowledgement repaints the screen and never
     touches the buffer, the state machine or the page variable;
  4. LogoutVital 0x1B40 drives a confirm dialog and never requests a state
     transition;
  5. of the eighteen state transitions in the image, only three are reachable
     from an inbound vital, and the character-select -> world transition is not
     one of them.

Re-pinning when a number legitimately moves (a different client build, a server
edit that changes a cross-check): run
``py -3 tools/pf_ui_state_refresh_static.py --json`` and update the
``UI_REFRESH_COUNTS`` block in the report in the same change.

These tests import nothing from ``src/``, open no socket, touch no database and
launch no GameClient.  They read one binary and three text files.
"""
from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "pf_ui_state_refresh_static.py"
REPORT = (
    ROOT / "reports"
    / "PF_UI_REFRESH001_CHARACTER_SELECT_STATE_MACHINE_STATIC_20260819.md"
)
MANIFEST = REPORT.with_suffix(".manifest")
CLIENT = ROOT.parent / "GameClient" / "GameClient.local.bin"
CLIENT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

COUNTS_BLOCK = re.compile(r"```json UI_REFRESH_COUNTS\n(?P<body>.*?)\n```", re.S)

_TOOL_MODULE = None


def load_tool():
    """Execute the verifier once; a drifted guard shows up in GUARDS_FAILED."""
    global _TOOL_MODULE
    if _TOOL_MODULE is None:
        spec = importlib.util.spec_from_file_location("pf_ui_state_refresh_static", TOOL)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        _TOOL_MODULE = module
    return _TOOL_MODULE


def report_counts() -> dict:
    match = COUNTS_BLOCK.search(REPORT.read_text(encoding="utf-8"))
    if match is None:
        raise AssertionError("the report has no ```json UI_REFRESH_COUNTS block")
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
        self.assertEqual(counts["measured_at_head"], "08fb65b")

    def test_the_manifest_pins_the_client_binary_by_hash(self):
        text = MANIFEST.read_text(encoding="utf-8")
        self.assertIn("GameClient.local.bin", text)
        self.assertIn(CLIENT_SHA, text)

    def test_the_verifier_is_pure_stdlib(self):
        """The release gate runs py -3 on Windows with no third-party packages."""
        source = TOOL.read_text(encoding="utf-8")
        imports = set(re.findall(r"^import (\w+)$", source, re.M))
        self.assertEqual(imports, {"hashlib", "json", "os", "struct", "sys"}, imports)
        self.assertNotIn("capstone", source.replace("capstone was used", ""))


class VerifierRunsCleanTests(unittest.TestCase):
    """Every guard in the verifier must hold against the pinned binary."""

    def test_the_verifier_imports_without_a_failed_guard(self):
        tool = load_tool()
        self.assertEqual(tool.GUARDS_FAILED, [], tool.GUARDS_FAILED)

    def test_the_verifier_read_the_pinned_client_image(self):
        self.assertEqual(load_tool().sha, CLIENT_SHA)

    def test_the_verifier_actually_asserted_something(self):
        tool = load_tool()
        self.assertGreaterEqual(tool.GUARDS_TOTAL, 250)
        self.assertEqual(tool.GUARDS_TOTAL, len(tool.RESULTS))

    def test_the_server_cross_check_ran(self):
        self.assertTrue(load_tool().COUNTS["v141_cross_check_ran"])


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
        self.assertIn("%d guards" % report_counts()["guards_total"], text)


class CharacterListBufferTests(unittest.TestCase):
    """Conclusion 1+2: one buffer, three mutators, zero erase paths."""

    def test_the_list_lives_in_one_singleton_field(self):
        counts = load_tool().COUNTS
        self.assertEqual(counts["character_list_singleton_global"], "0x01081A90")
        self.assertEqual(counts["character_list_collection_offset"], "+0x180")

    def test_the_bulk_fill_has_exactly_one_caller(self):
        tool = load_tool()
        self.assertEqual(tool.calls_to(tool.LIST_FILL), [0x5EFCAC])

    def test_that_caller_is_inside_the_selectactorvital_apply(self):
        tool = load_tool()
        apply_va = tool.VITALS["SelectActorVital"][5]
        self.assertEqual(apply_va, 0x5EFC40)
        self.assertTrue(apply_va <= 0x5EFCAC < apply_va + 0x110)

    def test_the_append_has_exactly_one_caller_and_it_is_createactorvital(self):
        tool = load_tool()
        self.assertEqual(tool.calls_to(tool.LIST_ADD_ONE), [0x5EFD76])
        self.assertEqual(tool.VITALS["CreateActorVital"][5], 0x5EFD50)

    def test_there_is_no_erase_by_key_path(self):
        self.assertEqual(load_tool().COUNTS["character_list_erase_by_key_paths"], 0)

    def test_only_thirty_two_instructions_in_text_form_that_offset(self):
        self.assertEqual(load_tool().COUNTS["plus_0x180_instructions_in_text"], 32)


class DeleteAckTests(unittest.TestCase):
    """Conclusion 3: the delete acknowledgement repaints and nothing else."""

    def test_the_delete_ack_id_and_handler_are_the_ones_reported(self):
        tool = load_tool()
        self.assertEqual(tool.VITALS["DeleteActorVital"][0], 0x36DB)
        self.assertEqual(tool.VITALS["DeleteActorVital"][5], 0x5EFDC0)
        self.assertEqual(tool.calls_to(0x4BAEB0), [0x5EFE03])

    def test_only_field_values_three_and_four_reach_the_list(self):
        counts = load_tool().COUNTS
        self.assertEqual(counts["delete_ack_ops_that_touch_the_list"], [3, 4])
        self.assertNotIn(counts["delete_ack_op_our_server_sends"],
                         counts["delete_ack_ops_that_touch_the_list"])

    def test_the_handler_calls_no_list_mutator_and_no_transition(self):
        tool = load_tool()
        reached = tool.calls_in(0x4BAEB0, 0x4BB618)
        for forbidden in (tool.LIST_FILL, tool.LIST_ADD_ONE, tool.LIST_CLEAR,
                          tool.LIST_CLEAR_DTOR, 0x4C7320, tool.APP_RESET):
            with self.subTest(target=hex(forbidden)):
                self.assertNotIn(forbidden, reached)

    def test_the_handler_never_writes_the_page_variable(self):
        tool = load_tool()
        lo, hi = tool.va2off(0x4BAEB0), tool.va2off(0x4BB618)
        self.assertEqual(tool.refs32(0x107A2C0, lo, hi), [])


class LogoutTests(unittest.TestCase):
    """Conclusion 4: LogoutVital is a dialog controller."""

    def test_logout_apply_is_the_reported_one(self):
        tool = load_tool()
        self.assertEqual(tool.VITALS["LogoutVital"][0], 0x1B40)
        self.assertEqual(tool.VITALS["LogoutVital"][5], 0x5EF930)

    def test_logout_never_requests_a_state_transition(self):
        tool = load_tool()
        self.assertNotIn(0x4C7320, tool.calls_in(0x5DC660, 0x5DC79A))
        self.assertNotIn(0x4C7320, tool.calls_in(0x5EF930, 0x5EF94D))

    def test_the_only_window_it_drives_is_the_logout_confirm(self):
        self.assertEqual(load_tool().wstr(0xF2FDAC), "SystemSetting_LogoutConfirm")


class TransitionGraphTests(unittest.TestCase):
    """Conclusion 5: eighteen transitions, three of them network-reachable."""

    def test_exactly_eighteen_transition_sites(self):
        tool = load_tool()
        self.assertEqual(len(tool.calls_to(0x4C7320)), 18)
        self.assertEqual(tool.COUNTS["state_transition_sites"], 18)

    def test_only_three_live_inside_a_vital_apply(self):
        self.assertEqual(
            load_tool().COUNTS["state_transition_sites_inside_a_vital_apply"], 3)

    def test_the_character_select_screen_is_cstatecreateactor(self):
        counts = load_tool().COUNTS
        self.assertEqual(counts["character_select_state"], "cStateCreateActor")
        self.assertEqual(counts["character_select_state_token"], "0x0107A38C")

    def test_the_five_character_select_gated_vitals(self):
        self.assertEqual(
            load_tool().COUNTS["vitals_gated_on_character_select_ids"],
            ["0x36CF", "0x36DB", "0x42E3", "0x4323", "0x709E"])

    def test_six_of_the_enumerated_vitals_do_nothing_when_sent_inbound(self):
        tool = load_tool()
        self.assertEqual(tool.COUNTS["vitals_with_noop_inbound_apply"], 6)
        for name in tool.CLIENT_TO_SERVER_ONLY:
            with self.subTest(vital=name):
                self.assertEqual(tool.VITALS[name][5], tool.NOOP_APPLY)


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
        self.assertIn("No claim about the ORIGINAL server", text)

    def test_the_report_does_not_call_v141_the_original_server(self):
        text = REPORT.read_text(encoding="utf-8").lower()
        self.assertNotIn("v141, the original server", text)
        self.assertNotIn("original server (v141", text)

    def test_the_report_leaves_the_decision_to_the_chief(self):
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn("proposal", text)
        self.assertIn("no ledger entry", text.lower())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
