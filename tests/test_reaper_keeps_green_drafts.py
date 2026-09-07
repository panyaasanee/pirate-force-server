"""A pull request whose gate is GREEN and whose merge was refused only for
being a DRAFT must be left open by the reaper.

Why this file exists.  ``.github/workflows/merge-claude-pr.yml`` has exactly
one path that closes a pull request whose gate job came back green: the reap
job tries the merge itself, and closes what will not merge.  The API refuses
to merge a draft, so that refusal was guaranteed for every pull request opened
as a draft -- and house rule 1849 requires exactly that of every seam that runs
on every frame: open as a draft until ``pf-adversary`` reports.  The reaper was
therefore closing pull requests for obeying a rule.  The close comment itself
said so ("If this pull request was still a draft, that refusal is expected --
the API will not merge a draft") and closed anyway.

PANYA-DECISION 20260908_0010+07:00 (via ka1-A), item 3 remedy (b), measured on
server #1077, #1084 and #1076: "a pull request whose CI is GREEN while its
adversary result has not come back is ALIVE - the reaper may not close it",
and the gate verdict is read as a first-class marker, equal in standing to the
marker line in the body.

WHAT THIS FILE DOES NOT CLAIM.  It does not claim the guard has ever run on
GitHub - no reap tick has been observed since it landed.  It reads the shipped
workflow text, the same method as
``tests/test_merge_workflow_logs_marker_verdict.py``, and pins the ORDER of
the three statements that decide a green draft's fate.  It says nothing about
red gates: a red verdict still closes, in ``decide``, untouched by this round.

MUTATION-PROOF ON PURPOSE.  Delete the guard, drop its ``continue``, move it
below the close, or widen it to close nothing green at all, and a named test
here goes red.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "merge-claude-pr.yml"

# The reaper's own merge attempt.  Everything this file pins sits between this
# line and the close it used to fall into.
REAPER_MERGE = 'gh pr merge "$PR" --repo "$REPO" --merge --match-head-commit "$HEAD_SHA"'

# The first line of the comment the reaper posts before closing a green pull
# request.  This is the close the guard has to come BEFORE.
GREEN_CLOSE_HEADLINE = "but this pull request could not be merged - closing it"

# The reap job's own green branch opener, used to bound the region searched so
# that an identically shaped guard somewhere else in the file cannot satisfy
# these tests by accident.
GREEN_BRANCH = 'if [ "$GREEN" = "yes" ]; then'

DRAFT_GUARD = re.compile(
    r'if \[ "\$DRAFT" = "true" \]; then(?P<body>.*?)\n\s*fi\n',
    re.S,
)


def _text():
    return WORKFLOW.read_text(encoding="utf-8")


def _green_region(text):
    """The reap job's green branch: from its `if` to the close it guards.

    Bounded on purpose.  `decide` has its own green handling and its own
    `mergeable != true` close; a guard that drifted into THAT job would be a
    different (and wrong) change, and would not be found here.
    """
    start = text.rindex(GREEN_BRANCH)
    end = text.index(GREEN_CLOSE_HEADLINE, start)
    return text[start:end]


class ReaperKeepsGreenDrafts(unittest.TestCase):
    def test_workflow_is_where_this_file_thinks_it_is(self):
        self.assertTrue(WORKFLOW.is_file(), f"{WORKFLOW} is missing")

    def test_the_green_close_still_exists(self):
        """The guard must not have been implemented by deleting the close.

        A reaper that never closes an unmergeable green pull request leaves
        the lane lock stuck forever, which is the failure the whole file was
        written to prevent.
        """
        self.assertIn(GREEN_CLOSE_HEADLINE, _text())

    def test_a_draft_guard_stands_between_the_merge_attempt_and_the_close(self):
        region = _green_region(_text())
        self.assertIn(REAPER_MERGE, region, "the reaper's merge attempt moved")
        guard = DRAFT_GUARD.search(region, region.index(REAPER_MERGE))
        self.assertIsNotNone(
            guard,
            "no `if [ \"$DRAFT\" = \"true\" ]` guard between the reaper's merge "
            "attempt and the close of a GREEN pull request - a green draft "
            "waiting for pf-adversary would be closed again "
            "(PANYA-DECISION 20260908_0010)",
        )

    def test_the_guard_leaves_the_pull_request_open(self):
        """`continue` and nothing else: no comment, no close, no un-draft."""
        region = _green_region(_text())
        guard = DRAFT_GUARD.search(region, region.index(REAPER_MERGE))
        assert guard is not None, "covered by the test above"
        body = guard.group("body")
        self.assertIn(
            "continue",
            body,
            "the draft guard does not `continue` - execution falls into the close",
        )
        for forbidden in ("gh pr close", "gh pr comment", "gh pr ready"):
            self.assertNotIn(
                forbidden,
                body,
                f"the draft guard runs `{forbidden}` - it must only leave the "
                "pull request alone",
            )

    def test_the_guard_says_why_in_the_run_log(self):
        """A silent skip is how a reaper decision becomes unauditable.

        server #794 sat green, unmerged and unclosed for 2.5 hours with
        nothing anywhere saying why; the fix then was to say it once in the
        log, and the same applies to a pull request this guard keeps alive.
        """
        region = _green_region(_text())
        guard = DRAFT_GUARD.search(region, region.index(REAPER_MERGE))
        assert guard is not None, "covered by the test above"
        body = guard.group("body")
        self.assertIn("::warning::", body, "the guard skips without logging")
        self.assertIn(
            "20260908_0010",
            body,
            "the guard's log line does not name the decision that ordered it",
        )
        self.assertIn("DRAFT", body, "the log line does not say what was skipped")

    def test_a_non_draft_green_pull_request_can_still_be_closed(self):
        """The guard is conditioned on the draft flag, not on green alone.

        Widen it to `if true` (or drop the `$DRAFT` test) and a green pull
        request that genuinely cannot merge - a conflict, a 403 - would sit
        open forever holding nothing but confusion.
        """
        region = _green_region(_text())
        guard = DRAFT_GUARD.search(region, region.index(REAPER_MERGE))
        assert guard is not None, "covered by the test above"
        after_guard = region[guard.end():]
        self.assertNotIn(
            "continue",
            after_guard,
            "something else `continue`s after the draft guard - the close is "
            "unreachable for non-drafts",
        )

    def test_the_red_verdict_still_closes(self):
        """This round widened nothing: `decide` closes on red exactly as before."""
        text = _text()
        self.assertIn('if [ "$VERDICT" = "red" ]; then', text)
        self.assertIn("Gate RED (job", text)


if __name__ == "__main__":
    unittest.main()
