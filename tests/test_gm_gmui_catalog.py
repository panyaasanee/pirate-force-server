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
    ROW_CENSUS,
    ROW_CENSUS_SHA256,
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
        # Until round `y1evqj` the second half of this card was
        # `total_is_unknown()`, which stopped meaning "no button is claimed
        # to work" the moment the census gave the table a denominator.  The
        # claim it was always making is this one: seven codecs exist and
        # NOT ONE censused row says the server answers it.
        self.assertTrue(any(row.server_has_a_codec for row in GM_VITALS))
        self.assertEqual([row for row in BUTTONS if row.server_answers_today], [])


class PagesTests(unittest.TestCase):
    def test_only_one_page_name_is_committed_evidence(self):
        # `GMUI_1.model`'s child tab is the only page name any committed
        # artifact carries; the other two are placeholders naming the gap.
        self.assertEqual(PAGE_KNOWN, "GMUI_BASIC")
        self.assertEqual(len(PAGES), 3)
        self.assertEqual(
            sum(1 for page in PAGES if page.startswith("UNNAMED_PAGE")), 2
        )


class RowCensusTests(unittest.TestCase):
    """The half of P-3 the GT-207 screenshots turned out to already answer.

    These cards are about the COUNT and the SHAPE.  Not one of them asserts
    a label or an opcode, because the census does not carry either.
    """

    def test_the_census_matches_its_pin(self):
        # Same guard as the log-type table's: a silent edit to the tsv --
        # a row added, a slug renamed, a shape changed -- must fail loudly
        # rather than quietly restate the count P-3 is graded on.
        raw = (
            ROOT
            / "src"
            / "pirateforce_foundation"
            / "gm"
            / "data"
            / "gmui_widget_census.tsv"
        ).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ROW_CENSUS_SHA256)

    def test_a_drifted_census_refuses_loudly_rather_than_loading(self):
        original = gmui_catalog.ROW_CENSUS_SHA256
        try:
            gmui_catalog.ROW_CENSUS_SHA256 = "0" * 64
            with self.assertRaises(GmuiCatalogError) as caught:
                gmui_catalog._load_row_census()
        finally:
            gmui_catalog.ROW_CENSUS_SHA256 = original
        self.assertIn("drifted", str(caught.exception))

    def test_seventeen_rows_across_the_three_pages(self):
        # The number P-3 has been missing since `COO-DECISION 20260904_0245`
        # asked for it: 7 + 5 + 5.
        self.assertEqual(len(ROW_CENSUS), 17)
        per_page = {}
        for entry in ROW_CENSUS:
            per_page[entry.page] = per_page.get(entry.page, 0) + 1
        self.assertEqual(per_page, {1: 7, 2: 5, 3: 5})

    def test_every_row_is_on_a_page_the_module_names(self):
        for entry in ROW_CENSUS:
            self.assertIn(PAGES[entry.page - 1], PAGES)

    def test_row_numbers_are_dense_and_unique_within_each_page(self):
        # A missing row number would mean the census silently dropped a row
        # it had counted, which is the one arithmetic error that would
        # corrupt the denominator without changing the file's shape.
        seen = {}
        for entry in ROW_CENSUS:
            seen.setdefault(entry.page, []).append(entry.row)
        for page, rows in seen.items():
            self.assertEqual(
                sorted(rows), list(range(1, len(rows) + 1)), f"page {page}"
            )

    def test_every_slug_is_distinct_and_ascii(self):
        slugs = [entry.slug for entry in ROW_CENSUS]
        self.assertEqual(len(set(slugs)), len(slugs))
        for slug in slugs:
            self.assertTrue(slug.isascii(), slug)

    def test_no_censused_row_claims_an_opcode_or_a_handler(self):
        # THE POINT OF THE WHOLE CENSUS BEING A PHOTOGRAPH.  A screenshot
        # cannot say what a widget sends, so no row built from one may say
        # it either -- and a future round that fills `client_frame` from
        # anything but the image has to delete this card to do it.
        for row in BUTTONS:
            self.assertIsNone(row.client_frame, row.button)
            self.assertIsNone(row.handler_symbol, row.button)
            self.assertFalse(row.server_answers_today, row.button)

    def test_fifteen_labels_are_unread_and_the_other_two_are_only_partial(self):
        unread = [entry for entry in ROW_CENSUS if entry.label_is_unread]
        partial = [
            entry
            for entry in ROW_CENSUS
            if entry.label_status == gmui_catalog.LABEL_STATUS_LATIN_PARTIAL
        ]
        self.assertEqual(len(unread), 15)
        self.assertEqual(len(partial), 2)
        # And a partial row must SAY it is partial where a human reads it,
        # not quietly borrow the unread wording.
        for entry in partial:
            row = next(row for row in BUTTONS if row.button == entry.slug)
            self.assertIn(gmui_catalog.FUNCTION_LABEL_PARTIAL, row.function)

    def test_an_unknown_label_status_is_refused(self):
        with self.assertRaises(GmuiCatalogError) as caught:
            gmui_catalog._parse_census_line(
                "1\t1\tp1r1_row_selector\t0\t0\t0\t365\tREAD\tinvented"
            )
        self.assertIn("label_status", str(caught.exception))

    def test_a_row_naming_a_page_that_does_not_exist_is_refused(self):
        with self.assertRaises(GmuiCatalogError) as caught:
            gmui_catalog._parse_census_line(
                "4\t1\tp4r1_row_selector\t0\t0\t0\t365\tUNREAD\tinvented"
            )
        self.assertIn("page 4", str(caught.exception))

    def test_a_short_row_is_refused_rather_than_padded(self):
        with self.assertRaises(GmuiCatalogError) as caught:
            gmui_catalog._parse_census_line("1\t1\tp1r1_row_selector\t0")
        self.assertIn("columns", str(caught.exception))


class CountHonestyTests(unittest.TestCase):
    """The count exists now; the two predicates that bound it must too."""

    def test_the_count_is_known_and_is_zero_of_seventeen(self):
        self.assertFalse(total_is_unknown())
        self.assertEqual(progress(), (0, 17))

    def test_a_known_count_is_still_not_a_confirmed_one(self):
        # `total_is_unknown()` going False is exactly the moment a round
        # could start writing "17 buttons" as if the number were settled.
        # `PAGE_1_UNEXPLAINED_GAP` is why it is not, and this card is what
        # makes deleting that doubt a visible edit.
        self.assertFalse(gmui_catalog.total_is_confirmed_on_screen())
        # The doubt has to name the two rows it sits between, or a later
        # reader cannot check it against the screenshots.
        self.assertIn("row 5", gmui_catalog.PAGE_1_UNEXPLAINED_GAP)
        self.assertIn("row 6", gmui_catalog.PAGE_1_UNEXPLAINED_GAP)

    def test_every_screenshot_the_census_cites_is_pinned_by_content(self):
        # Four PNGs, each with a sha256 -- "the screenshots" must not be
        # able to become different screenshots without a visible diff.
        self.assertEqual(len(gmui_catalog.ROW_CENSUS_SCREENSHOTS), 4)
        for path, digest in gmui_catalog.ROW_CENSUS_SCREENSHOTS:
            self.assertTrue(path.startswith("evidence_screens/"), path)
            self.assertEqual(len(digest), 64, path)
            self.assertTrue(all(c in "0123456789abcdef" for c in digest), path)


class ButtonGuardTests(unittest.TestCase):
    """The guard on a row that claims more than a photograph can carry."""

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
