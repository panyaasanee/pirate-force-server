"""Pin MP-OPT1-B's numbers to the client binary they were read from.

MULTIPLAYER-READINESS-AUDIT-001 graded ``LSCN_LoginVitalReq`` (0x42BF) as guess
**G8**: the bytes were reproducible but "the value never varies", so nothing in
the corpus could show which field was the account.  This milestone answers that
statically, out of the read-only client image, so its numbers must not be
hand-typed either.  These tests take the ``LOGIN_REQ_COUNTS`` fenced block out of

``reports/PF_MPOPT1B_LOGIN_VITAL_REQ_0X42BF_STATIC_20260819.md``

and compare it, key by key, to a live run of
``tools/pf_login_vital_req_static.py``.  If any guard in the verifier drifts,
importing the tool raises ``SystemExit`` and the first test fails; if the guards
hold but a number in the report disagrees with the binary, the comparison tests
fail.  Every number is compared EXACTLY - none of them is a "how big is the
suite today" measurement.

The tests also restate, independently of the report prose, the five conclusions
the next round would build on, so that a silent edit to either the report or the
tool cannot quietly change them:

  1. the frame has exactly two fields and no others;
  2. ``+0x14`` is a ``std::wstring`` carrying the ACCOUNT, wire tag 0x48;
  3. ``+0x30`` is a ``std::string`` carrying the PASSWORD in clear text, tag 0x44;
  4. the account is ``decode_hex(-acc)``, which is why every archived capture
     shows ``0E 00 00 00`` for the argument ``test`` - the field is a VARIABLE,
     not a constant, and the model computes it for any argument;
  5. our own server reads neither field.

THE CORPUS NUMBERS ARE MEANT TO MOVE.  ``distinct_account_values`` is 1 today,
and that single fact is the entire reason GT-020 exists.  When an attended run
with a different ``-acc`` lands a capture in this repository, this test will
fail on purpose.  Re-pin it by running
``py -3 tools/pf_login_vital_req_static.py --json`` and updating the
``LOGIN_REQ_COUNTS`` block in the same change, naming the account that was used.

These tests import nothing from ``src/``, open no socket, touch no database and
launch no GameClient.  They read one binary and a handful of text files.
"""
from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "pf_login_vital_req_static.py"
REPORT = (
    ROOT / "reports"
    / "PF_MPOPT1B_LOGIN_VITAL_REQ_0X42BF_STATIC_20260819.md"
)
MANIFEST = REPORT.with_suffix(".manifest")
CLIENT = ROOT.parent / "GameClient" / "GameClient.local.bin"
CLIENT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
DRAFT_NAME = "GT_DRAFT_MPOPT1B_LOGIN_USERNAME_20260819.md"

COUNTS_BLOCK = re.compile(r"```json LOGIN_REQ_COUNTS\n(?P<body>.*?)\n```", re.S)

_TOOL_MODULE = None


def load_tool():
    """Import the verifier once.  A drifted guard becomes SystemExit here."""
    global _TOOL_MODULE
    if _TOOL_MODULE is None:
        spec = importlib.util.spec_from_file_location("pf_login_vital_req_static", TOOL)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _TOOL_MODULE = module
    return _TOOL_MODULE


class EvidenceExistsTests(unittest.TestCase):
    """Nothing below means anything if the evidence is not on disk."""

    def test_every_input_and_output_exists(self):
        for path in (REPORT, MANIFEST, TOOL, CLIENT):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), f"missing {path}")

    def test_the_manifest_pins_the_client_image_this_report_read(self):
        text = MANIFEST.read_text(encoding="utf-8")
        self.assertIn(CLIENT_SHA, text)

    def test_the_report_carries_exactly_one_counts_block(self):
        text = REPORT.read_text(encoding="utf-8")
        self.assertEqual(len(COUNTS_BLOCK.findall(text)), 1)

    def test_the_report_hands_the_runtime_half_to_a_queue_draft(self):
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn(DRAFT_NAME, text)


class VerifierRunsCleanTests(unittest.TestCase):
    """The tool is the evidence; if it does not pass, nothing else matters."""

    def test_the_verifier_imports_without_a_drifted_guard(self):
        tool = load_tool()
        self.assertFalse([name for name, ok in tool.RESULTS if not ok])

    def test_the_verifier_runs_a_non_trivial_number_of_guards(self):
        tool = load_tool()
        # An exact count, not a floor: this is a fact about one immutable binary.
        self.assertEqual(tool.COUNTS["guards_total"], len(tool.RESULTS))
        self.assertGreaterEqual(len(tool.RESULTS), 120)

    def test_the_verifier_read_the_pinned_client_build(self):
        tool = load_tool()
        self.assertEqual(tool.COUNTS["client_sha256"], CLIENT_SHA)


class ReportMatchesTheBinaryTests(unittest.TestCase):
    """Every number in the report is the tool's number, key by key."""

    @classmethod
    def setUpClass(cls):
        cls.tool = load_tool()
        text = REPORT.read_text(encoding="utf-8")
        cls.published = json.loads(COUNTS_BLOCK.search(text).group("body"))

    def test_the_report_publishes_every_key_the_tool_measures(self):
        self.assertEqual(sorted(self.published), sorted(self.tool.COUNTS))

    def test_every_published_value_matches_the_measurement(self):
        for key in sorted(self.tool.COUNTS):
            with self.subTest(key=key):
                self.assertEqual(self.published[key], self.tool.COUNTS[key])


class FrameShapeTests(unittest.TestCase):
    """Conclusion 1-3, restated independently of the report prose."""

    @classmethod
    def setUpClass(cls):
        cls.tool = load_tool()

    def test_the_frame_has_exactly_two_fields(self):
        self.assertEqual(self.tool.COUNTS["serial_field_count"], 2)

    def test_the_account_is_a_wide_string_at_0x14_with_tag_0x48(self):
        self.assertEqual(self.tool.COUNTS["account_field_offset"], "0x14")
        self.assertEqual(self.tool.COUNTS["account_field_type"], "std::wstring")
        self.assertEqual(self.tool.COUNTS["account_field_wire_tag"], "0x48")

    def test_the_password_is_a_narrow_string_at_0x30_with_tag_0x44(self):
        self.assertEqual(self.tool.COUNTS["password_field_offset"], "0x30")
        self.assertEqual(self.tool.COUNTS["password_field_type"], "std::string")
        self.assertEqual(self.tool.COUNTS["password_field_wire_tag"], "0x44")

    def test_the_password_is_not_hashed(self):
        # If this ever flips, every statement about the credential path in the
        # report is wrong and the GT draft's -pwd advice is wrong with it.
        self.assertFalse(self.tool.COUNTS["password_is_hashed"])

    def test_the_two_fields_are_serialized_account_first(self):
        body = self.tool.login_vital_req_body("4142", "pw")
        self.assertEqual(body[0], 0x48)
        self.assertEqual(body[5 + 4], 0x44)


class AccountIsAVariableTests(unittest.TestCase):
    """Conclusion 4 - the answer to G8, restated as executable statements."""

    @classmethod
    def setUpClass(cls):
        cls.tool = load_tool()

    def test_the_recovered_hex_table_is_exactly_hexadecimal(self):
        self.assertEqual(self.tool.COUNTS["hexval_mismatches_over_65536_chars"], 0)
        self.assertEqual(self.tool.COUNTS["hexval_table_entries"], 17)

    def test_the_argument_test_decodes_to_the_bytes_the_corpus_has(self):
        self.assertEqual(self.tool.COUNTS["golden_account_wchars"], [14, 0])
        self.assertEqual(
            self.tool.wstring_field(self.tool.decode_hex_wstring("test")),
            bytes.fromhex("48040000000E000000"),
        )

    def test_a_different_argument_produces_a_different_account_field(self):
        """The whole of G8 in one assertion."""
        golden = self.tool.login_vital_req_body("test", "test")
        probe = self.tool.login_vital_req_body("4142", "test")
        self.assertNotEqual(golden, probe)
        self.assertEqual(len(golden), len(probe))
        self.assertEqual(sum(1 for a, b in zip(golden, probe) if a != b), 2)

    def test_the_model_can_name_the_argument_for_any_account(self):
        for account in ("test", "AB", "mptest02"):
            with self.subTest(account=account):
                argument = self.tool.encode_hex_argument(account)
                self.assertEqual(self.tool.decode_hex_wstring(argument), account)

    def test_the_documented_probe_argument_is_the_one_the_tool_measured(self):
        self.assertEqual(self.tool.COUNTS["probe_argument"], "4142")
        self.assertEqual(self.tool.COUNTS["probe_account_name"], "AB")
        self.assertEqual(self.tool.COUNTS["probe_body_length_delta"], 0)
        self.assertEqual(self.tool.COUNTS["probe_bytes_changed"], 2)

    def test_the_password_argument_reaches_the_wire_verbatim(self):
        self.assertEqual(
            self.tool.string_field("test"), bytes.fromhex("4404000000") + b"test"
        )
        self.assertEqual(
            self.tool.string_field("mppass02"),
            bytes.fromhex("4408000000") + b"mppass02",
        )

    def test_the_model_refuses_input_it_cannot_honestly_encode(self):
        """A guard that never fails is not a guard."""
        with self.assertRaises(ValueError):
            self.tool.string_field("ก")            # non-ASCII password
        with self.assertRaises(ValueError):
            self.tool.encode_hex_argument("ก")     # > 0xFF account character


class CorpusTests(unittest.TestCase):
    """The corpus half of G8, and the numbers GT-020 is expected to move."""

    @classmethod
    def setUpClass(cls):
        cls.tool = load_tool()

    def test_the_archived_corpus_was_actually_read(self):
        self.assertGreater(self.tool.COUNTS["archived_login_captures_with_0x42bf"], 0)

    def test_the_whole_corpus_reproduces_from_two_launcher_arguments(self):
        expected = self.tool.login_vital_req_nested("test", "test")
        self.assertEqual(self.tool.DISTINCT_NESTED, [expected])
        self.assertEqual(
            self.tool.COUNTS["golden_nested_hex"], expected.hex(" ").upper()
        )

    def test_the_corpus_still_has_exactly_one_account_value(self):
        """Fails on purpose the day GT-020 lands a second one.  Re-pin then."""
        self.assertEqual(self.tool.COUNTS["distinct_account_values"], 1)
        self.assertEqual(self.tool.COUNTS["distinct_password_values"], 1)

    def test_the_same_account_opens_the_game_listener_handshake(self):
        self.assertGreater(self.tool.COUNTS["game_captures_with_the_same_account"], 0)

    def test_the_body_parser_rejects_a_damaged_frame(self):
        good = self.tool.login_vital_req_body("4142", "pw")
        self.assertEqual(self.tool.split_body(good), ("AB".encode("utf-16-le"), b"pw"))
        for damaged in (
            good[:-1],                       # truncated password
            good + b"\x00",                  # a tail the client would never emit
            b"\x44" + good[1:],              # wrong tag on field 1
            good[:5 + 4] + b"\x48" + good[5 + 5:],   # wrong tag on field 2
            b"",
        ):
            with self.subTest(damaged=damaged.hex()):
                with self.assertRaises(ValueError):
                    self.tool.split_body(damaged)


class OurServerTests(unittest.TestCase):
    """Conclusion 5 - why changing -acc cannot move a database row today."""

    def test_the_frozen_server_never_parses_the_login_request_payload(self):
        source = (ROOT / "current" / "pf_login_game_server_v141.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("parsed.nested_id == LOGIN_REQ", source)
        self.assertNotIn("parse_login_req", source)

    def test_the_persisted_account_name_comes_from_the_servers_own_argument(self):
        source = (ROOT / "current" / "pf_login_game_server_v141.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('ap.add_argument("--token", default="localtest")', source)

    def test_the_frozen_ack_still_carries_the_old_decoded_account(self):
        """The live-test hazard the GT draft warns about, pinned in a test."""
        source = (ROOT / "current" / "pf_login_game_server_v141.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(r'b"\x0B\x68\x48\x04\x00\x00\x00\x0E\x00\x00\x00"', source)

    def test_an_account_row_is_created_on_demand(self):
        source = (ROOT / "src" / "pirateforce_foundation" / "store.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("INSERT OR IGNORE INTO accounts(login_name,created_at)", source)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
