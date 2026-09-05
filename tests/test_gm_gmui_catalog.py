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

    def test_every_caption_now_comes_from_the_table(self):
        # Round `dl1etn` replaced UNREAD/LATIN_PARTIAL: the captions were
        # never a squinting problem, they were text in a committed table.
        # It then shipped ONE row as "absent from every committed table"
        # and pf-adversary found that caption at n_ID 1671 -- outside the
        # run, which is the only place this lane had looked.  So the count
        # is 17/17 and the status that was wrong keeps its guards.
        no_table_row = [
            entry for entry in ROW_CENSUS if entry.label_has_no_table_row
        ]
        from_table = list(gmui_catalog.rows_with_a_read_label())
        self.assertEqual(gmui_catalog.labels_are_read(), (17, 17))
        self.assertEqual(len(from_table), 17)
        self.assertEqual(no_table_row, [])
        for entry in from_table:
            row = next(row for row in BUTTONS if row.button == entry.slug)
            self.assertIn(gmui_catalog.FUNCTION_LABEL_FROM_TABLE, row.function)
            self.assertIn(str(entry.label_row_id), row.function)

    def test_a_read_label_never_leaks_the_words_into_a_function_string(self):
        # A `function` string that carried the Thai would let a round file
        # quote a caption without ever joining it to a row id -- which is
        # the whole evidence chain this round bought.
        for entry in gmui_catalog.rows_with_a_read_label():
            row = next(row for row in BUTTONS if row.button == entry.slug)
            self.assertNotIn(
                gmui_catalog.label_text(entry.label_row_id), row.function
            )

    def test_an_unknown_label_status_is_refused(self):
        with self.assertRaises(GmuiCatalogError) as caught:
            gmui_catalog._parse_census_line(
                "1\t1\tp1r1_row_selector\t0\t0\t0\t365\tREAD\t1386\tinvented"
            )
        self.assertIn("label_status", str(caught.exception))

    def test_a_row_naming_a_page_that_does_not_exist_is_refused(self):
        with self.assertRaises(GmuiCatalogError) as caught:
            gmui_catalog._parse_census_line(
                "4\t1\tp4r1_row_selector\t0\t0\t0\t365\t"
                "SCREENSHOT_ONLY\t0\tinvented"
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


class LabelBlockTests(unittest.TestCase):
    """The captions, and the guards that stop a plausible id becoming one.

    The claim these cards hold up is NOT "adjacent ids in a text table are
    this window's labels" -- that on its own is worth nothing.  It is that
    the run's shape and the panel's shape agree row by row, which is a thing
    a test can actually check.
    """

    def test_the_copy_matches_its_pinned_sha(self):
        raw = (
            ROOT
            / "src/pirateforce_foundation/gm/data/gmui_label_block.tsv"
        ).read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(), gmui_catalog.LABEL_BLOCK_SHA256
        )

    def test_the_block_is_two_runs_plus_four_strays_not_one_run(self):
        # pf-adversary (D4) was right that "one contiguous run" is false and
        # this card used to hide it behind its own name.  Stated properly:
        # two runs, three tab titles 26 and 451 ids away, and one row
        # caption (1671) 258 ids away.  The panel is NOT one block, and
        # anything that reasons from adjacency alone is reasoning from a
        # premise this card refutes.
        rows = sorted(gmui_catalog.LABEL_BLOCK)
        page_1_2 = [n for n in rows if 1386 <= n <= 1413]
        page_3 = [n for n in rows if 1892 <= n <= 1896]
        self.assertEqual(page_1_2, list(range(1386, 1414)))
        self.assertEqual(page_3, list(range(1892, 1897)))
        strays = sorted(set(rows) - set(page_1_2) - set(page_3))
        self.assertEqual(strays, [1439, 1440, 1671, 1891])
        self.assertEqual(
            sorted(gmui_catalog.PAGE_TITLE_ROW_IDS), [1439, 1440, 1891]
        )

    def test_every_censused_row_points_at_its_own_caption(self):
        for entry in gmui_catalog.rows_with_a_read_label():
            with self.subTest(slug=entry.slug):
                self.assertEqual(
                    gmui_catalog.GMUI_LABEL_BLOCK_ROLES[entry.label_row_id],
                    f"page{entry.page}.row{entry.row}.label",
                )

    def test_every_shape_number_is_pinned_not_just_the_four_the_run_joins(
        self,
    ):
        # pf-adversary (D3) mutated p3r4's radio count 2->9, p3r1's numeric
        # count 2->42 and p2r3's text count 1->0, re-pinned the sha, and the
        # whole suite stayed green: only 4 of the 51 shape numbers were
        # joined to anything.  The join CANNOT cover the rest (page 3 row 4
        # draws radios the run has no option strings for), so the remaining
        # 47 are pinned here instead -- read off the GT-207 shots, and a
        # later re-read has to edit this table in the same commit.
        expected = {
            "p1r1_row_selector": (2, 0, 0),
            "p1r2_row_selector": (0, 1, 3),
            "p1r3_row_selector": (0, 1, 0),
            "p1r4_row_selector": (0, 1, 0),
            "p1r5_row_selector": (0, 1, 0),
            "p1r6_row_selector": (0, 1, 0),
            "p1r7_row_selector": (0, 1, 0),
            "p2r1_row_selector": (0, 1, 0),
            "p2r2_row_selector": (0, 1, 0),
            "p2r3_row_selector": (2, 1, 1),
            "p2r4_row_selector": (2, 2, 1),
            "p2r5_row_selector": (0, 1, 0),
            "p3r1_row_selector": (0, 0, 2),
            "p3r2_row_selector": (0, 0, 1),
            "p3r3_row_selector": (0, 0, 1),
            "p3r4_row_selector": (2, 0, 0),
            "p3r5_row_selector": (0, 0, 2),
        }
        actual = {
            entry.slug: (
                entry.option_radios,
                entry.text_inputs,
                entry.numeric_inputs,
            )
            for entry in ROW_CENSUS
        }
        self.assertEqual(actual, expected)

    def test_seven_rows_share_a_shape_so_shape_cannot_order_them(self):
        # The defect that killed "cannot be joined any other way" (D2), kept
        # as a card so nobody restores that sentence: these seven rows are
        # indistinguishable by shape, and only ROW_ORDER_PREMISE separates
        # them.  If a later round ever makes them distinguishable, this card
        # goes red and the premise can be weakened honestly.
        shapes = {}
        for entry in ROW_CENSUS:
            key = (entry.option_radios, entry.text_inputs, entry.numeric_inputs)
            shapes.setdefault(key, []).append(entry.slug)
        # EIGHT rows, not the seven pf-adversary counted -- p1r3 has the
        # same shape and was missed on both sides.  It is the one of the
        # eight that IS anchored independently (its caption starts with the
        # latin token NPC and 1393 is the only NPC-prefixed row in the run),
        # which leaves seven genuinely unordered by anything but the premise.
        self.assertEqual(
            sorted(shapes[(0, 1, 0)]),
            [
                "p1r3_row_selector",
                "p1r4_row_selector",
                "p1r5_row_selector",
                "p1r6_row_selector",
                "p1r7_row_selector",
                "p2r1_row_selector",
                "p2r2_row_selector",
                "p2r5_row_selector",
            ],
        )
        self.assertIn("NOT MEASURED", gmui_catalog.ROW_ORDER_PREMISE)

    def test_the_ordering_premise_admits_the_rows_that_break_it(self):
        # 1404 and 1405 are each consumed by two rows.  A strict draw-order
        # sequence would not do that, and the premise has to say so where a
        # reader meets it rather than in a round file nobody re-reads.
        reused = [
            row_id
            for row_id, role in gmui_catalog.GMUI_LABEL_BLOCK_ROLES.items()
            if "+" in role
        ]
        self.assertEqual(sorted(reused), [1404, 1405])
        for row_id in reused:
            self.assertIn(str(row_id), gmui_catalog.ROW_ORDER_PREMISE)

    def test_one_caption_comes_from_outside_the_run(self):
        # p3r3's caption (1671) is 258 ids away.  It is the standing
        # counter-example to "the panel is one contiguous run", and the
        # reason FUNCTION_LABEL_SCREENSHOT_ONLY now says "not found YET".
        entry = next(
            row for row in ROW_CENSUS if row.slug == "p3r3_row_selector"
        )
        self.assertEqual(entry.label_row_id, 1671)
        self.assertNotIn(1671, range(1386, 1414))
        self.assertNotIn(1671, range(1892, 1897))
        self.assertIn("not found", gmui_catalog.FUNCTION_LABEL_SCREENSHOT_ONLY)

    def test_the_shapes_agree_where_the_run_says_they_must(self):
        # This is the corroboration the whole mapping rests on: a row the
        # run gives option strings to is a row the photograph shows radios
        # on, and a row it gives none to is a row with none.
        by_slug = {entry.slug: entry for entry in ROW_CENSUS}
        option_rows: dict[str, int] = {}
        for row_id, role in gmui_catalog.GMUI_LABEL_BLOCK_ROLES.items():
            del row_id
            for part in role.split("+"):
                head, _, tail = part.rpartition(".")
                if tail.startswith("option_"):
                    option_rows[head] = option_rows.get(head, 0) + 1
        for anchor, count in option_rows.items():
            page, row = anchor.split(".")
            slug = f"p{page[-1]}r{row[-1]}_row_selector"
            with self.subTest(anchor=anchor):
                self.assertEqual(by_slug[slug].option_radios, count)
        # Page 1 row 2 is the strongest single agreement in the set: three
        # axis captions in the run, three numeric boxes on the shot.
        axes = [
            role
            for role in gmui_catalog.GMUI_LABEL_BLOCK_ROLES.values()
            if role.startswith("page1.row2.axis_")
        ]
        self.assertEqual(len(axes), 3)
        self.assertEqual(by_slug["p1r2_row_selector"].numeric_inputs, 3)

    def test_the_undrawn_rows_are_named_and_the_gap_stays_a_candidate(self):
        self.assertEqual(gmui_catalog.UNDRAWN_BLOCK_ROWS, (1396, 1403))
        self.assertIn(
            gmui_catalog.PAGE_1_GAP_CANDIDATE, gmui_catalog.UNDRAWN_BLOCK_ROWS
        )
        # The candidate must not be allowed to turn into a measurement by
        # accident: page 2 has an undrawn string and no gap, so an undrawn
        # string does not reserve space, and the count stays unconfirmed.
        self.assertFalse(gmui_catalog.total_is_confirmed_on_screen())
        for row_id in gmui_catalog.UNDRAWN_BLOCK_ROWS:
            self.assertEqual(
                gmui_catalog.GMUI_LABEL_BLOCK_ROLES[row_id], "undrawn"
            )
            self.assertNotIn(
                row_id, [entry.label_row_id for entry in ROW_CENSUS]
            )

    def test_a_census_row_may_not_point_at_a_non_caption(self):
        # 1387 is an option text, not a caption.  Pointing a row at it is
        # exactly how a mapping quietly becomes wrong by one.
        with self.assertRaises(GmuiCatalogError) as caught:
            gmui_catalog._parse_census_line(
                "1\t1\tp1r1_row_selector\t2\t0\t0\t365\t"
                "TABLE_EXACT\t1387\tinvented"
            )
        self.assertIn("1387", str(caught.exception))

    def test_a_census_row_may_not_point_at_another_rows_caption(self):
        with self.assertRaises(GmuiCatalogError) as caught:
            gmui_catalog._parse_census_line(
                "1\t1\tp1r1_row_selector\t2\t0\t0\t365\t"
                "TABLE_EXACT\t1389\tinvented"
            )
        self.assertIn("page1.row1.label", str(caught.exception))

    def test_a_screenshot_only_row_may_not_carry_a_row_id(self):
        with self.assertRaises(GmuiCatalogError) as caught:
            gmui_catalog._parse_census_line(
                "3\t3\tp3r3_row_selector\t0\t0\t1\t448\t"
                "SCREENSHOT_ONLY\t1671\tinvented"
            )
        self.assertIn("1671", str(caught.exception))

    def test_label_text_refuses_an_id_the_block_does_not_carry(self):
        with self.assertRaises(GmuiCatalogError):
            gmui_catalog.label_text(1)

    def test_reading_a_label_is_not_answering_a_button(self):
        # The one number P-3 is graded on must not move because captions
        # were read.  16 of 17 labels, 0 of 17 handlers.
        self.assertEqual(gmui_catalog.labels_are_read(), (17, 17))
        self.assertEqual(progress(), (0, 17))

    def test_the_page_2_caption_is_flagged_as_not_describing_page_2(self):
        titles = gmui_catalog.page_titles()
        self.assertEqual(
            [row_id for row_id, _ in titles],
            list(gmui_catalog.PAGE_TITLE_ROW_IDS),
        )
        self.assertIn("1440", gmui_catalog.PAGE_2_TITLE_DOES_NOT_MATCH_ITS_CONTENT)
        self.assertIn(
            "never the tab title",
            gmui_catalog.PAGE_2_TITLE_DOES_NOT_MATCH_ITS_CONTENT,
        )

    def test_a_tab_title_is_not_a_model_name(self):
        # `PAGES` are model names (one known, two placeholders) and the
        # titles are what a human reads on the strip.  Collapsing the two
        # would let a round claim the other two models are named now.
        for _, words in gmui_catalog.page_titles():
            self.assertNotIn(words, PAGES)
        self.assertEqual(PAGES[1], gmui_catalog.PAGE_UNNAMED_2)
        self.assertEqual(PAGES[2], gmui_catalog.PAGE_UNNAMED_3)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
