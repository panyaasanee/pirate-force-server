"""`gm/gmui_catalog.py` -- the P-3 catalogue and, mostly, its refusals.

`COO-DECISION 20260904_0245` item 1 asked for a page/button/opcode table.
This clone has no client image, so the table cannot be filled here -- and the
cards below are about the two things that ARE testable: that the parts built
from committed artifacts really come from them, and that the empty part
cannot be filled with a claim nothing backs.
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import gmui_catalog
from pirateforce_foundation.gm.gmui_catalog import (
    BUTTONS,
    GM_VITALS,
    GmuiCatalogError,
    PAGES,
    PAGE_KNOWN,
    SOURCE_SHA256,
    ButtonRow,
    assert_backed,
    log_types,
    progress,
    total_is_unknown,
    vitals_without_a_codec,
)


class LogTypeTableTests(unittest.TestCase):
    def test_the_copy_matches_its_pinned_sha(self):
        # The module checks this at import time; this card names the property
        # so a reader does not have to find the import-time check to know the
        # table is pinned rather than trusted.
        path = (
            ROOT
            / "src"
            / "pirateforce_foundation"
            / "gm"
            / "data"
            / "gm_tool_log_types.tsv"
        )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(digest, SOURCE_SHA256)

    def test_it_holds_the_ninety_seven_rows_the_client_table_holds(self):
        self.assertEqual(len(log_types()), 97)

    def test_every_log_type_id_is_distinct(self):
        # If the client ever shipped two rows on one `n_LogType`, a future
        # button row keyed on it would be ambiguous -- pin that it does not.
        types = [log_type for _n_id, log_type, _msg in log_types()]
        self.assertEqual(len(types), len(set(types)))

    def test_a_drifted_copy_refuses_loudly_rather_than_loading(self):
        original = gmui_catalog.SOURCE_SHA256
        gmui_catalog.SOURCE_SHA256 = "0" * 64
        try:
            with self.assertRaises(GmuiCatalogError) as caught:
                gmui_catalog._load_log_types()
        finally:
            gmui_catalog.SOURCE_SHA256 = original
        self.assertIn("drifted", str(caught.exception))


class VitalRowTests(unittest.TestCase):
    def test_the_seven_gm_surface_vitals_are_all_here(self):
        self.assertEqual(
            {row.vital_id for row in GM_VITALS},
            {0x51E9, 0x8C77, 0x5A19, 0x8D30, 0x9F2C, 0x162E, 0x6CEC},
        )

    def test_no_gm_surface_vital_lacks_a_codec_anymore(self):
        # Round sexjmq closed the last two (gm/forbid_to_talk_wire.py,
        # gm/activity_cheat_code_wire.py) -- the backlog item
        # rounds/GM_20260904_1316_zjbjys_*.md named as buildable straight
        # from the registry + PF_SERIALIZER_FIELDS.tsv without any RE
        # answer.  A codec existing is NOT "the button works" (see
        # test_a_codec_is_not_the_same_claim_as_a_working_button below) --
        # this only says every vital on the surface can now be read or
        # written by this repo.
        self.assertEqual(vitals_without_a_codec(), ())

    def test_every_named_handler_module_actually_exists(self):
        # The "answers today" column is a claim about THIS repo, so it is
        # re-derived here rather than trusted: a module that gets renamed or
        # deleted must turn this card red, not leave a catalogue row lying.
        import importlib

        for row in GM_VITALS:
            if row.handler_module is None:
                continue
            with self.subTest(vital=row.name):
                module = importlib.import_module(
                    f"pirateforce_foundation.{row.handler_module}"
                )
                self.assertTrue(module)

    def test_a_codec_is_not_the_same_claim_as_a_working_button(self):
        # The distinction the module docstring insists on, pinned: nothing in
        # this table may be read as "the button works".
        for row in GM_VITALS:
            self.assertNotIn("button works", row.note)
        self.assertTrue(
            any(row.server_has_a_codec for row in GM_VITALS)
            and total_is_unknown()
        )


class PagesTests(unittest.TestCase):
    def test_only_one_page_name_is_committed_evidence(self):
        # `GMUI_1.model`'s child tab is the only page name any committed
        # artifact carries; the other two are placeholders naming the gap.
        self.assertEqual(PAGE_KNOWN, "GMUI_BASIC")
        self.assertEqual(len(PAGES), 3)
        self.assertEqual(
            sum(1 for page in PAGES if page.startswith("UNNAMED_PAGE")), 2
        )


class EmptyButtonTableTests(unittest.TestCase):
    """The half of P-3 this clone cannot build, and the guard on it."""

    def test_the_button_table_is_empty_and_the_count_says_so(self):
        self.assertEqual(BUTTONS, ())
        self.assertTrue(total_is_unknown())
        self.assertEqual(progress(), (0, 0))

    def test_zero_of_zero_is_not_reported_as_completion(self):
        # `progress()` alone reads as "0/0 done".  `total_is_unknown()` is
        # what stops a future round from writing that, so pin that the two
        # travel together while the table is empty.
        closed, total = progress()
        self.assertEqual((closed, total), (0, 0))
        self.assertTrue(total_is_unknown())

    def test_a_row_claiming_a_handler_that_does_not_exist_is_refused(self):
        # The whole reason this module is code and not a table in a letter.
        row = ButtonRow(
            page=PAGE_KNOWN,
            button="BT_SOMETHING",
            function="invented for this test",
            client_frame=0x51E9,
            handler_symbol="dispatch.no_such_function_exists",
            owner="LANE-GM",
        )
        with self.assertRaises(GmuiCatalogError) as caught:
            assert_backed(row)
        self.assertIn("no_such_function_exists", str(caught.exception))

    def test_a_row_naming_an_unimportable_module_is_refused(self):
        row = ButtonRow(
            page=PAGE_KNOWN,
            button="BT_SOMETHING",
            function="invented for this test",
            client_frame=0x51E9,
            handler_symbol="no_such_module.anything",
            owner="LANE-GM",
        )
        with self.assertRaises(GmuiCatalogError) as caught:
            assert_backed(row)
        self.assertIn("unimportable", str(caught.exception))

    def test_a_malformed_handler_symbol_is_refused_rather_than_ignored(self):
        row = ButtonRow(
            page=PAGE_KNOWN,
            button="BT_SOMETHING",
            function="invented for this test",
            client_frame=0x51E9,
            handler_symbol="dispatch",  # no attribute half
            owner="LANE-GM",
        )
        with self.assertRaises(GmuiCatalogError):
            assert_backed(row)

    def test_a_row_with_a_real_handler_is_accepted(self):
        # The guard must not be a blanket refusal -- a row that names
        # something real has to pass, or the next round cannot use it.
        row = ButtonRow(
            page=PAGE_KNOWN,
            button="BT_SOMETHING",
            function="invented for this test",
            client_frame=0x51E9,
            handler_symbol="gmui_catalog.progress",
            owner="LANE-GM",
        )
        assert_backed(row)

    def test_an_unanswered_row_needs_no_handler(self):
        # A catalogued button the server does NOT answer is the normal state
        # for P-3 and must be recordable without inventing a symbol.
        row = ButtonRow(
            page=PAGE_KNOWN,
            button="BT_SOMETHING",
            function="invented for this test",
            client_frame=None,
            handler_symbol=None,
            owner="LANE-GM",
        )
        assert_backed(row)
        self.assertFalse(row.server_answers_today)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
