"""`gm/gmui_log_type_join.py` -- the caption/log-type joins, and their refusal.

P-3's next lead after round `dl1etn` was: sixteen GMUI rows now have a real
caption, and the client's GMTOOL log-type table is the closest thing to an
enumeration of GM operations any committed artifact holds -- so join them
and see which rows are worth wiring first.  These cards pin the answer this
lane found across BOTH searches the module runs (whole-string, and rare
substring overlap): neither promotes anything, and both fail loudly if the
underlying tables, or the search itself, change enough to make that answer
wrong.  Several cards here exist specifically because `pf-adversary` (this
round) found the first draft's coverage tests would not have caught a
narrowed search, and its domain claim overstated what the tables share.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import gmui_catalog, gmui_log_type_join
from pirateforce_foundation.gm.gmui_log_type_join import (
    CANDIDATES,
    NOTABLE_OVERLAPS,
    ACTION_ROWS_WITH_NO_LOG_MATCH,
    JoinCandidate,
    _is_mutual_substring,
    _longest_common_substring,
    _searched_block_ids,
    backed_matches,
    rare_overlaps,
)


class WholeStringSearchCoverageTests(unittest.TestCase):
    def test_the_search_visits_every_row_of_the_copied_block(self):
        # Stronger than "hits are a subset of the role dict": this compares
        # against the set of ids the search LOOP actually completed for
        # (tracked as a side effect of the same loop, see
        # _run_whole_string_search), so a mutation that skips an id
        # partway through -- without shrinking the declared role dict --
        # is caught here.  pf-adversary (this round) showed a subset-only
        # check does not catch that class of mutation.
        self.assertEqual(
            _searched_block_ids(), frozenset(gmui_catalog.GMUI_LABEL_BLOCK_ROLES)
        )

    def test_the_search_is_recomputed_not_hand_written(self):
        # CANDIDATES is a module-level constant computed at import time from
        # the two pinned tables.  This card exists so a later round that
        # turns it into a hand-typed tuple (to "simplify" the module) sees a
        # test name explaining why that would be a regression: a hand-typed
        # list would not re-run this round's question against new data.
        recomputed_candidates, recomputed_ids = (
            gmui_log_type_join._run_whole_string_search()
        )
        self.assertEqual(CANDIDATES, recomputed_candidates)
        self.assertEqual(_searched_block_ids(), recomputed_ids)

    def test_todays_pinned_data_produces_exactly_three_hits(self):
        # Pinned to the exact count so a change in either source table shows
        # up here rather than silently changing what the module concludes.
        # If this test starts failing after an edit to gmui_label_block.tsv
        # or gm_tool_log_types.tsv, that is the search finding something
        # NEW -- read the new hit before touching this number.
        self.assertEqual(len(CANDIDATES), 3)

    def test_exactly_one_of_todays_hits_is_the_tab_three_title(self):
        tab_title_hits = [c for c in CANDIDATES if c.is_a_tab_title]
        self.assertEqual(len(tab_title_hits), 1)
        self.assertEqual(tab_title_hits[0].block_id, 1891)

    def test_the_other_two_hits_are_both_the_recovery_event_row(self):
        # The remaining two survivors share their GMUI side: block row 1896,
        # the page-3 row-5 caption -- named by id here rather than by
        # quoting the client's own words on an added .py line (see the
        # module docstring for why).  It hits twice because its caption is
        # a two-word compound and each half separately matches a different
        # log message.
        non_title_hits = [c for c in CANDIDATES if not c.is_a_tab_title]
        self.assertEqual(len(non_title_hits), 2)
        self.assertTrue(all(c.block_id == 1896 for c in non_title_hits))
        self.assertEqual(sorted(c.log_id for c in non_title_hits), [4, 12])

    def test_every_action_row_has_zero_whole_string_hits(self):
        # THE CORRECTED CLAIM (pf-adversary caught the prior wording
        # overstating this as "no shared vocabulary at all"): every GMUI
        # row that names a distinct world/player-administration action has
        # zero whole-caption matches in the log-type table.  Read from
        # ACTION_ROWS_WITH_NO_LOG_MATCH rather than repeating the list, so
        # the two files cannot drift apart.
        candidate_block_ids = {c.block_id for c in CANDIDATES}
        for block_id, gloss in ACTION_ROWS_WITH_NO_LOG_MATCH:
            self.assertNotIn(
                block_id,
                candidate_block_ids,
                f"block {block_id} ({gloss}) unexpectedly has a whole-string "
                "log-type hit",
            )

    def test_action_rows_list_is_not_accidentally_empty(self):
        # A guard against the list above silently losing its entries (which
        # would make the previous card vacuously true).
        self.assertEqual(len(ACTION_ROWS_WITH_NO_LOG_MATCH), 12)


class MutualSubstringPredicateTests(unittest.TestCase):
    """Pins BOTH directions of the whole-string search using synthetic
    ASCII strings, independent of the real Thai tables.

    pf-adversary (this round) removed the "left in right" half of the
    predicate and the full suite stayed green, because every real hit on
    today's pinned data happens to fire through the other direction only.
    These cards do not depend on that being true of today's data.
    """

    def test_left_contained_in_right(self):
        self.assertTrue(_is_mutual_substring("cat", "concatenate"))

    def test_right_contained_in_left(self):
        self.assertTrue(_is_mutual_substring("concatenate", "cat"))

    def test_neither_contained_is_false(self):
        self.assertFalse(_is_mutual_substring("cat", "dog"))

    def test_equal_strings_are_mutual_substrings(self):
        self.assertTrue(_is_mutual_substring("same", "same"))


class LongestCommonSubstringTests(unittest.TestCase):
    def test_finds_the_shared_run(self):
        self.assertEqual(
            _longest_common_substring("abcdef", "xxbcdeyy"), "bcde"
        )

    def test_no_overlap_is_empty(self):
        self.assertEqual(_longest_common_substring("abc", "xyz"), "")

    def test_is_symmetric(self):
        left, right = "warehouse", "mousetrap"
        self.assertEqual(
            _longest_common_substring(left, right),
            _longest_common_substring(right, left),
        )


class NotableOverlapTests(unittest.TestCase):
    def test_todays_pinned_data_produces_exactly_seven_notable_substrings(self):
        # A substring here means: at least six characters long, shared
        # between some GMUI block string and some log message.  Pinned by
        # count so a table edit that changes this shows up here.
        self.assertEqual(len(NOTABLE_OVERLAPS), 7)

    def test_every_notable_substrings_log_id_set_is_independently_correct(self):
        # NOTABLE_OVERLAPS reports, per substring, EVERY log message that
        # contains it -- not only the one pair the substring was first
        # found on.  Recompute that count directly against log_types() for
        # each substring, rather than trusting the module's own bookkeeping.
        for substring, log_ids in NOTABLE_OVERLAPS.items():
            expected = frozenset(
                log_id
                for log_id, _log_type, log_text in gmui_catalog.log_types()
                if substring in gmui_log_type_join._normalize(log_text)
            )
            self.assertEqual(log_ids, expected, substring)

    def test_rare_overlaps_is_a_strict_subset_of_notable_overlaps(self):
        rare = rare_overlaps()
        self.assertTrue(set(rare) <= set(NOTABLE_OVERLAPS))
        self.assertLess(len(rare), len(NOTABLE_OVERLAPS))

    def test_todays_pinned_data_produces_exactly_four_rare_overlaps(self):
        self.assertEqual(len(rare_overlaps()), 4)

    def test_no_rare_overlap_recurs_in_more_than_one_log_message(self):
        # THE FILTER ITSELF, pinned: rare_overlaps()'s bar is
        # "at most one independent log message", not "small count".  A
        # future round that loosens this without reading the wider set it
        # admits should see this card name what changed.
        for substring, log_ids in rare_overlaps().items():
            self.assertLessEqual(len(log_ids), 1, substring)

    def test_the_common_overlaps_are_excluded_from_rare(self):
        # The two substrings this module's docstring names as clearly
        # common ("player"-ish and "change"-ish vocabulary, recurring
        # across many log messages) must NOT appear in the rare set --
        # otherwise the filter is not doing anything.
        rare = rare_overlaps()
        common = {
            substring: log_ids
            for substring, log_ids in NOTABLE_OVERLAPS.items()
            if len(log_ids) > 1
        }
        self.assertEqual(len(common), 3)
        for substring in common:
            self.assertNotIn(substring, rare)


class BackedMatchesTests(unittest.TestCase):
    def test_backed_matches_is_empty_today(self):
        # THE CLAIM OF THIS ROUND, pinned in code: no caption/log-type join
        # -- whole-string or rare-overlap -- clears the evidence bar today.
        # A round that later confirms one (by attended observation, per the
        # function's own docstring) has to edit _ATTENDED_CONFIRMED_JOINS to
        # make this test fail, which is the point -- the failure is the
        # signal that a real join arrived.
        self.assertEqual(backed_matches(), ())

    def test_a_tab_title_can_never_be_a_backed_match(self):
        for candidate in CANDIDATES:
            if candidate.is_a_tab_title:
                self.assertNotIn(candidate, backed_matches())


class NamedConstantTests(unittest.TestCase):
    def test_no_join_survives_because_names_the_refusal_reason(self):
        reason = gmui_log_type_join.NO_JOIN_SURVIVES_BECAUSE
        self.assertIn("coincidence", reason)
        self.assertIn("LOG_TYPE_TABLE_IS_ITEM_ECONOMY_BOOKKEEPING", reason)

    def test_domain_note_points_at_the_action_row_list_not_a_bare_denial(self):
        # Replaces a prior, tautological card that only checked the note's
        # own English words against itself (pf-adversary, this round: that
        # card would pass unchanged even if the note's claim were false).
        # This checks the note POINTS somewhere a reader can verify the
        # claim, and the pointed-at list is independently checked above in
        # WholeStringSearchCoverageTests.
        note = gmui_log_type_join.LOG_TYPE_TABLE_IS_ITEM_ECONOMY_BOOKKEEPING
        self.assertIn("ACTION_ROWS_WITH_NO_LOG_MATCH", note)


class JoinCandidateShapeTests(unittest.TestCase):
    def test_is_a_tab_title_reads_the_role_suffix(self):
        title_candidate = JoinCandidate(
            block_id=1891,
            block_role="page3.tab_title",
            block_text="x",
            log_id=1,
            log_type=1,
            log_text="x",
        )
        row_candidate = JoinCandidate(
            block_id=1896,
            block_role="page3.row5.label",
            block_text="x",
            log_id=1,
            log_type=1,
            log_text="x",
        )
        self.assertTrue(title_candidate.is_a_tab_title)
        self.assertFalse(row_candidate.is_a_tab_title)


if __name__ == "__main__":
    unittest.main()
