"""`GT-269` came back from the screen, and the screen disagreed.

WHAT ARRIVED.  `GT-269` (GMUI three-tab row census) ran attended in `KA1A`
round `R321` on 2026-09-06.  Two things came back.  The count held: a human
counted 7 / 5 / 5 rows off three photographs, the census's own numbers, and
reported the page 1 gap as empty.  The captions did not: eight of the
seventeen readings are not the string the census points that row at, and
five of those eight are on page 1.

WHY THIS FILE EXISTS RATHER THAN AN EDIT TO THE CENSUS.  The cheap move was
available and is the one this lane refuses: quietly repoint the eight rows,
or quietly reclassify them `SCREENSHOT_ONLY`, and let the suite go green on
a census nothing contradicts any more.  Both would destroy the finding.  A
transcription off a photograph does not outrank a committed text table and a
committed text table does not outrank somebody's eyes -- so the disagreement
is recorded as a disagreement, in its own pinned file, and
`labels_are_confirmed_on_screen()` stays False until an attended pass reads
page 1 character by character.

WHAT THE CARDS BELOW ACTUALLY GUARD.  Mostly they guard against this record
being made convenient later: that the observation file stays total over the
census (so an inconvenient row cannot simply be deleted), that the eight
disagreements stay eight (so one cannot be reclassified into agreement
without a test naming it), that the two predicates keep meaning different
things (the COUNT is confirmed, the CAPTIONS are not), and that no refusal
in the loader prints a Thai string into a cp874 console.
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
    AGREEMENTS,
    AGREEMENT_AGREES,
    AGREEMENT_DISAGREES,
    AGREEMENT_UNCERTAIN,
    GmuiCatalogError,
    OBSERVED_LABELS,
    OBSERVED_LABELS_SHA256,
    PAGE_1_GAP_ANSWERED,
    PAGE_1_GAP_CANDIDATE,
    ROW_CENSUS,
    label_disagreements,
    labels_are_confirmed_on_screen,
    observed_label,
    total_is_confirmed_on_screen,
)

OBSERVED_PATH = (
    ROOT / "src" / "pirateforce_foundation" / "gm" / "data"
    / "gmui_observed_labels.tsv"
)

#: The eight rows the screen and the table disagree about, as `R321` read
#: them.  Pinned as a SET, not a count: a count would let a later round trade
#: one disagreement for another and stay green, which is precisely the kind
#: of drift the whole census is built to refuse.
DISAGREEING_ROWS = {
    (1, 2),
    (1, 3),
    (1, 4),
    (1, 5),
    (1, 6),
    (2, 3),
    (2, 4),
    (3, 3),
}


class ObservedLabelFileTests(unittest.TestCase):
    def test_the_copy_on_disk_is_the_one_the_module_pinned(self):
        """The pin is the record, and this file is the only copy of it.

        Same guard the census and the label block already carry, for a
        sharper reason: those two are derived from committed artifacts and
        can be re-derived if the copy rots.  This one is a transcription of
        somebody's eyes and cannot be re-derived from anything in this
        repository at all.
        """
        digest = hashlib.sha256(OBSERVED_PATH.read_bytes()).hexdigest()
        self.assertEqual(
            digest,
            OBSERVED_LABELS_SHA256,
            "gmui_observed_labels.tsv changed without its pin changing -- "
            "the pin is the only thing standing between this record and a "
            "silent edit",
        )

    def test_every_censused_row_has_a_reading(self):
        """Totality, so a row cannot be dropped instead of answered."""
        self.assertEqual(
            {(entry.page, entry.row) for entry in OBSERVED_LABELS},
            {(entry.page, entry.row) for entry in ROW_CENSUS},
            "the observation file and the census must cover exactly the "
            "same rows",
        )
        self.assertEqual(len(OBSERVED_LABELS), 17)

    def test_every_reading_carries_a_verdict_from_the_closed_set(self):
        for entry in OBSERVED_LABELS:
            with self.subTest(page=entry.page, row=entry.row):
                self.assertIn(entry.agreement, AGREEMENTS)

    def test_the_disagreements_are_the_eight_r321_actually_found(self):
        """A set, not a number.  See `DISAGREEING_ROWS`.

        This is the card that makes the finding survive a later round: to
        move any of these eight into agreement, that round has to edit this
        constant, and editing it is a statement about evidence rather than a
        tidy-up of a red test.
        """
        self.assertEqual(
            {(entry.page, entry.row) for entry in label_disagreements()},
            DISAGREEING_ROWS,
        )

    def test_five_of_the_eight_are_on_page_one(self):
        """The clustering is the part worth keeping in front of a reader.

        Five of page 1's seven rows disagree.  That is either transcription
        noise landing in a suspicious place, or the census pointing page 1 at
        the wrong id run -- and `PAGE_1_GAP_CANDIDATE` is a member of that
        same run, so the second reading would take the gap story with it.
        Neither this file nor any file in this repository can choose between
        them; the point of the card is that nobody can quietly stop asking.
        """
        page_1 = {row for page, row in DISAGREEING_ROWS if page == 1}
        self.assertEqual(page_1, {2, 3, 4, 5, 6})
        self.assertEqual(PAGE_1_GAP_CANDIDATE, 1396)

    def test_the_one_unclear_reading_is_recorded_as_unclear(self):
        """`UNCERTAIN` is not a synonym for either verdict.

        Page 2 row 2 is the row the observer themself called unreadable on
        the photograph.  Recording it as `AGREES` would manufacture a
        confirmation and recording it as `DISAGREES` would manufacture a
        finding.
        """
        entry = observed_label(2, 2)
        self.assertEqual(entry.agreement, AGREEMENT_UNCERTAIN)
        self.assertFalse(entry.contradicts_the_table)
        self.assertEqual(
            [e for e in OBSERVED_LABELS if e.agreement == AGREEMENT_UNCERTAIN],
            [entry],
        )

    def test_the_two_predicates_do_not_mean_the_same_thing(self):
        """The count is confirmed; the captions are not.

        `GT-269` answered one of the two questions it was written to ask,
        and a round that reads the green half as the whole ticket is the
        failure this pair of predicates exists to prevent.
        """
        self.assertTrue(total_is_confirmed_on_screen())
        self.assertFalse(labels_are_confirmed_on_screen())

    def test_the_caption_predicate_is_computed_from_the_record(self):
        """Not a hardcoded False that somebody has to remember to flip.

        `total_is_confirmed_on_screen()` is hardcoded on purpose -- no table
        knows whether a human looked.  This one is different: the record
        below it answers it, so it is derived, and it goes True on the round
        that resolves the last disagreement without anybody editing it.
        """
        self.assertEqual(
            labels_are_confirmed_on_screen(), not label_disagreements()
        )


class ObservedLabelRefusalTests(unittest.TestCase):
    """The loader's own refusals, reached without writing the pinned file.

    Same posture as the census's refusal tests: a bad row written into the
    real file would be caught by the pin first, and the refusal under test
    would never run.
    """

    def test_a_row_with_the_wrong_column_count_is_refused(self):
        with self.assertRaises(GmuiCatalogError) as caught:
            gmui_catalog._parse_observed_line("1\t1\tAGREES\tx")
        self.assertIn("expected 5", str(caught.exception))

    def test_a_verdict_outside_the_closed_set_is_refused(self):
        with self.assertRaises(GmuiCatalogError) as caught:
            gmui_catalog._parse_observed_line("1\t1\tCLOSE_ENOUGH\tx\tnote")
        self.assertIn("expected one of", str(caught.exception))

    def test_a_reading_with_no_text_is_refused(self):
        with self.assertRaises(GmuiCatalogError) as caught:
            gmui_catalog._parse_observed_line("1\t1\tAGREES\t   \tnote")
        self.assertIn("not an observation", str(caught.exception))

    def test_a_verdict_with_no_comparison_behind_it_is_refused(self):
        """The note is where the reading is held against the table row.

        A verdict with an empty note is a claim, and this file's whole value
        is that it is not one.
        """
        with self.assertRaises(GmuiCatalogError) as caught:
            gmui_catalog._parse_observed_line("1\t1\tDISAGREES\tx\t  ")
        self.assertIn("is a claim", str(caught.exception))

    def test_no_refusal_prints_the_observed_string(self):
        """The house console is cp874; these readings are Thai.

        A refusal that dies inside the error handler while reporting a bad
        row is worse than the bad row, so every message identifies a line by
        page and row and never by its text.  Exercised against the real
        strings, not a fixture: an ascii fixture would pass this card even
        if the message did interpolate the text.
        """
        for entry in OBSERVED_LABELS:
            line = "\t".join(
                [
                    str(entry.page),
                    str(entry.row),
                    "CLOSE_ENOUGH",
                    entry.observed_text,
                    entry.note,
                ]
            )
            with self.subTest(page=entry.page, row=entry.row):
                with self.assertRaises(GmuiCatalogError) as caught:
                    gmui_catalog._parse_observed_line(line)
                message = str(caught.exception)
                self.assertNotIn(entry.observed_text, message)
                message.encode("cp874")


class ObservedLabelsDoNotEditTheCensusTests(unittest.TestCase):
    """A disagreement is a question, not a licence to rewrite the answer."""

    def test_the_disagreeing_rows_still_point_at_their_table_rows(self):
        """No row was repointed or downgraded to make the red go away.

        Every one of the eight still carries `TABLE_EXACT` and the same
        `label_row_id` it carried before `GT-269` ran.  Nothing observed on
        a screen is evidence about which row of a text table a caption is;
        it is only evidence about what the caption says.
        """
        by_key = {(e.page, e.row): e for e in ROW_CENSUS}
        expected = {
            (1, 2): 1389,
            (1, 3): 1393,
            (1, 4): 1394,
            (1, 5): 1395,
            (1, 6): 1397,
            (2, 3): 1401,
            (2, 4): 1407,
            (3, 3): 1671,
        }
        for key, row_id in expected.items():
            with self.subTest(page=key[0], row=key[1]):
                self.assertEqual(by_key[key].label_status, "TABLE_EXACT")
                self.assertEqual(by_key[key].label_row_id, row_id)

    def test_the_gap_answer_keeps_the_half_that_is_still_open(self):
        """`PAGE_1_GAP_ANSWERED` may not read as a closed question.

        A human confirmed nothing is DRAWN in the gap.  Nobody can confirm
        by looking that nothing is THERE, and the constant has to keep
        saying so, or the next round to grep it will bank the wrong half.
        """
        self.assertIn("NO VISIBLE WIDGET", PAGE_1_GAP_ANSWERED)
        self.assertIn("undrawn", PAGE_1_GAP_ANSWERED)
        self.assertIn("looking cannot settle it", PAGE_1_GAP_ANSWERED)

    def test_the_progress_number_did_not_move(self):
        """Reading a label is not making a button work.

        `GT-269`'s own ticket says it in as many words -- the result may not
        be read as evidence that any button functions -- and `progress()` is
        where that would show up if a round ever confused the two.
        """
        self.assertEqual(gmui_catalog.progress(), (0, 17))


class AgreementVocabularyTests(unittest.TestCase):
    def test_there_is_no_fourth_verdict_meaning_close_enough(self):
        """Three values, and the missing fourth is the point.

        Six of the eight disagreements differ from the table in a single
        token.  A `NEARLY` bucket would collect exactly those six and retire
        the question, which is the outcome this lane is trying not to buy.
        """
        self.assertEqual(
            AGREEMENTS,
            (AGREEMENT_AGREES, AGREEMENT_DISAGREES, AGREEMENT_UNCERTAIN),
        )
        self.assertEqual(len(set(AGREEMENTS)), 3)


if __name__ == "__main__":
    unittest.main()
