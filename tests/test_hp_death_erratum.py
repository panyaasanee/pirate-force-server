"""HP-DEATH-ERRATA-001 (round 85) - the correction has to be where the reader is.

WHY THIS FILE EXISTS
--------------------
`reports/PF_HP_DEATH001_HP_DEATH_AND_RESPAWN_STATIC_20260819.md` says, in its
one-paragraph answer, that a single ``UpdateAttrVital`` is *"the whole trigger"*
for death and that mask bit ``0x0080`` should carry *"a positive float"*.
Round 85 lane B (`reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md`,
150 guards) refuted both byte-exact: the ``UpdateAttrVital`` handler span
``0x5F2400..0x5F261A`` holds **zero** ``+0x20`` dispatch shapes, so it cannot
reach the dead-state sync at all; and the two timer predicates have OPPOSITE
polarity, so a positive ``+0x58`` buys the dying latch and **no animation**.

The project's convention (set round 82, reused round 84) is that a wrong
sentence is corrected by APPENDING an erratum, never by quietly rewriting the
sentence - otherwise everyone who already quoted it has no way to learn they
were quoting a mistake.  The failure mode of that convention is equally real:
an erratum at the foot of a 400-line report is invisible to the next reader,
who stops at the one-paragraph answer.  Three notes already quote this report's
§2 sentence.

So these tests assert the thing the convention does not give for free:

  1. the warning block EXISTS and sits **before** the one-paragraph answer -
     compared by character offset, not by "is it in the file somewhere";
  2. it names both refuted claims and points at the refuting report;
  3. the erratum section exists at the foot, with its reproduce command;
  4. **the original sentences are still there, verbatim** - a "fix" that
     silently rewrites §2 must fail this file just as loudly as no fix at all.

Pure stdlib.  Reads two report files and nothing else: no binary, no capstone,
no network, no database, no GameClient.

Run just this file:
    python3 -m pytest tests/test_hp_death_erratum.py -q
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (
    ROOT / "reports"
    / "PF_HP_DEATH001_HP_DEATH_AND_RESPAWN_STATIC_20260819.md"
)
SOURCE_REPORT = (
    ROOT / "reports"
    / "PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md"
)

TEXT = REPORT.read_text(encoding="utf-8")

#: the marker that opens the warning block above the answer
WARNING_MARKER = "READ THIS BEFORE THE ANSWER"
#: the first words of the paragraph the warning must precede
ANSWER_MARKER = "**One-paragraph answer.**"
#: the appended section at the foot
ERRATUM_HEADING = "## ⚠ ERRATUM 2026-08-19 (รอบ 85, HP-DEATH-ERRATA-001)"

#: the two sentences that were wrong. They must SURVIVE, unedited.
ORIGINAL_CARRIER_SENTENCE = (
    "**So: to make a character die, a server sends one `UpdateAttrVital` "
    "carrying a `BasicAttr` with mask bit `0x0004` = 0 and mask bit `0x0080` "
    "set to a positive float. That is the whole trigger.**"
)
ORIGINAL_CONSEQUENCE_SENTENCE = (
    "to make a character die on this client, a server has to deliver a "
    "`BasicAttr` in which mask bit `0x0004` carries `0` **and** mask bit "
    "`0x0080` carries a positive float"
)


class WarningIsAboveTheAnswerTests(unittest.TestCase):
    """An erratum nobody reaches is an erratum nobody has."""

    def test_both_markers_exist_exactly_once(self):
        self.assertEqual(TEXT.count(WARNING_MARKER), 1,
                         "exactly one warning block, or ordering is ambiguous")
        self.assertEqual(TEXT.count(ANSWER_MARKER), 1)

    def test_the_warning_block_precedes_the_one_paragraph_answer(self):
        warning_at = TEXT.index(WARNING_MARKER)
        answer_at = TEXT.index(ANSWER_MARKER)
        self.assertLess(
            warning_at, answer_at,
            "the correction must sit ABOVE the one-paragraph answer. Three "
            "downstream notes quote that paragraph; a warning that lives only "
            "at the foot of a 400-line report does not reach them.")

    def test_the_warning_is_close_enough_to_be_read_as_part_of_the_answer(self):
        warning_at = TEXT.index(WARNING_MARKER)
        answer_at = TEXT.index(ANSWER_MARKER)
        between = TEXT[warning_at:answer_at]
        self.assertLessEqual(
            between.count("\n\n"), 2,
            "the warning must be adjacent to the answer paragraph, not parked "
            "several sections above it")

    def test_the_warning_is_a_blockquote_so_it_renders_as_a_callout(self):
        line_start = TEXT.rfind("\n", 0, TEXT.index(WARNING_MARKER)) + 1
        self.assertTrue(TEXT[line_start:].startswith(">"),
                        "the warning block must be a markdown blockquote")


class WarningSaysWhatIsWrongTests(unittest.TestCase):
    """A pointer with no content just moves the reader's confusion around."""

    def setUp(self):
        self.head = TEXT[:TEXT.index(ANSWER_MARKER)]

    def test_the_warning_names_the_refuting_report(self):
        self.assertIn(SOURCE_REPORT.name, self.head)
        self.assertTrue(SOURCE_REPORT.is_file(),
                        f"{SOURCE_REPORT.name} must exist to be cited")

    def test_the_warning_names_the_carrier_claim_it_refutes(self):
        self.assertIn("whole trigger", self.head)
        self.assertIn("0x5F2400", self.head,
                      "cite the handler span the negative was measured over")

    def test_the_warning_names_the_polarity_claim_it_refutes(self):
        self.assertIn("polarity", self.head.lower())
        for marker in ("0x0080", "+0x40", "+0x3C"):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.head)

    def test_the_warning_says_the_published_numbers_still_hold(self):
        self.assertIn("still reproduce", self.head.lower(),
                      "readers must not conclude the whole report is void")


class ErratumAtTheFootTests(unittest.TestCase):
    """The append-only convention itself."""

    def setUp(self):
        self.erratum_at = TEXT.index(ERRATUM_HEADING)

    def test_the_erratum_section_exists_and_is_last(self):
        self.assertGreater(self.erratum_at, TEXT.index("## 9. How to reproduce"),
                           "the erratum is APPENDED, never spliced into §9 or earlier")

    def test_the_erratum_cites_a_reproducible_verifier(self):
        tail = TEXT[self.erratum_at:]
        self.assertIn("pf_runtimeres_actor_entry_static.py", tail)
        self.assertIn("150 guards", tail)

    def test_the_erratum_covers_all_three_corrections(self):
        tail = TEXT[self.erratum_at:]
        for needle in ("0x5F2400", "0x6E9D", "0x446F30", "+0x58", "0x443990"):
            with self.subTest(needle=needle):
                self.assertIn(needle, tail)

    def test_the_erratum_claims_nothing_about_the_original_server(self):
        tail = TEXT[self.erratum_at:]
        self.assertIn("ORIGINAL server", tail)
        self.assertIn("runtime pass", tail.lower(),
                      "the erratum must say the corpse is still unobserved")


class OriginalSentencesSurviveTests(unittest.TestCase):
    """Round 82's rule: correct by appending. Never sand the sentence smooth."""

    def test_the_carrier_sentence_is_still_present_verbatim(self):
        self.assertIn(ORIGINAL_CARRIER_SENTENCE, TEXT,
                      "the wrong sentence must stay so that anyone who quoted it "
                      "can find it and see the erratum attached to it")

    def test_the_consequence_sentence_is_still_present_verbatim(self):
        self.assertIn(ORIGINAL_CONSEQUENCE_SENTENCE, TEXT)

    def test_the_original_open_debt_line_is_still_present(self):
        self.assertIn("NOT traced end to end", TEXT,
                      "§7's debt line stays; the erratum answers it, it does not "
                      "delete it")

    def test_the_report_still_carries_its_machine_readable_counts_block(self):
        self.assertTrue(re.search(r"```json HP_DEATH_COUNTS\n.*?\n```", TEXT, re.S),
                        "appending an erratum must not disturb the counts block "
                        "tests/test_hp_death_respawn_static.py parses")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
