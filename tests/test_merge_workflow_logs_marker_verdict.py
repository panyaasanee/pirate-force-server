"""Every marker gate that can merge, finish or reap a pull request has to say
in its own log what the body looked like WHEN IT READ IT.

Why this file exists.  ``pirate-force-server#922`` was merged at
2026-09-06T09:23:54Z by ``github-actions[bot]``.  Its body today carries no
automerge marker.  Two explanations fit that equally well - (a) the body was
edited AFTER the merge, (b) the run read a body that did have the marker - and
REST cannot separate them, because a merged pull request reports
``updated_at == merged_at``.  Reading the source settled that all three merge
paths read the body live per pull request and are fail-closed
(chief round ``lafdux``/R385), but it could not settle what #922's body said at
09:23.

The answer was only ever recoverable from the run log, and the log was silent
on the case that mattered: the ``*"$PF_MARKER"*)`` arm printed NOTHING when the
marker WAS found, and the reaper printed nothing on either arm.  A gate that
logs only its refusals leaves no record of its acceptances.

COO-DECISION 20260907_1041 (``chief0922``) ordered the fence instead of the
answer: all three paths print the verdict either way, so the next case like
#922 is one minute of reading instead of a round of inference.

MUTATION-PROOF ON PURPOSE.  Delete the ``echo`` from any one of the three
main-path positive arms and ``test_every_main_path_arm_announces_the_marker``
goes red naming that arm.  Delete a negative arm's message and
``test_every_main_path_arm_announces_a_refusal`` goes red.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "merge-claude-pr.yml"

# The one arm that is silent ON PURPOSE.  It is inside the `case "$HEAD_REF"`
# sub-branch for a head that is NOT `claude/*`: such a head is invisible to
# decide, finish and the reaper whatever its body says, so "no marker" there
# means "nobody asked for anything" and the workflow stays quiet, as it has
# since COO-DECISION 20260905_0847 item 4.  It is exempt by position, not by
# name, so moving it out of that sub-branch makes this file red.
QUIET_ARM_MARKER = "Stay quiet, as before."

ARM = re.compile(r'\*"\$PF_MARKER"\*\)(.*?);;', re.S)
NEGATIVE_ARM = re.compile(r'\*"\$PF_MARKER"\*\).*?;;\s*\*\)(.*?);;', re.S)


def _text():
    return WORKFLOW.read_text(encoding="utf-8")


def _arms():
    """Return (offset, arm_body) for every `*"$PF_MARKER"*)` case arm."""
    return [(m.start(), m.group(1)) for m in ARM.finditer(_text())]


def _is_quiet_arm(text, offset):
    """True for the documented non-claude/ sub-branch arm only.

    Identified by the comment that sits immediately above it, within the 400
    characters before the arm.  Nothing else in the file carries that sentence.
    """
    return QUIET_ARM_MARKER in text[max(0, offset - 400):offset]


class MergeWorkflowLogsItsMarkerVerdict(unittest.TestCase):
    def test_the_workflow_is_where_this_file_thinks_it_is(self):
        self.assertTrue(
            WORKFLOW.is_file(),
            "%s is missing; this pin is about that file and cannot run without it"
            % WORKFLOW,
        )

    def test_there_are_exactly_four_marker_arms_three_of_them_main_path(self):
        """Guards against a fourth merge path being added without a verdict line.

        If someone adds a new `case "$BODY" in *"$PF_MARKER"*)` gate, this count
        changes and they are forced to come here and say whether the new arm is
        a main path (must log) or another documented quiet one.
        """
        text = _text()
        arms = _arms()
        self.assertEqual(
            4, len(arms),
            "expected 4 `*\"$PF_MARKER\"*)` arms (decide, finish, reaper "
            "non-claude sub-branch, reaper main path); found %d. A new merge "
            "path must either log its verdict or be documented as quiet."
            % len(arms),
        )
        quiet = [off for off, _ in arms if _is_quiet_arm(text, off)]
        self.assertEqual(
            1, len(quiet),
            "expected exactly 1 documented quiet arm (the non-claude/ head "
            "sub-branch); found %d" % len(quiet),
        )

    def test_every_main_path_arm_announces_the_marker(self):
        """The positive arm must PRINT. `: ;` is what made #922 unanswerable."""
        text = _text()
        for offset, body in _arms():
            if _is_quiet_arm(text, offset):
                continue
            line = text.count("\n", 0, offset) + 1
            with self.subTest(line=line):
                self.assertIn(
                    "echo", body,
                    "the marker-found arm at line %d prints nothing, so a run "
                    "that merges on the strength of this marker leaves no "
                    "record that the marker was there. That is the #922 hole."
                    % line,
                )
                self.assertIn(
                    "HAS marker", body,
                    "the marker-found arm at line %d prints something, but not "
                    "a verdict about the marker; the log has to be readable "
                    "without the workflow source next to it" % line,
                )

    def test_every_main_path_arm_announces_a_refusal(self):
        """The negative arm must print too - the reaper used to `continue` mute."""
        text = _text()
        for m in NEGATIVE_ARM.finditer(text):
            if _is_quiet_arm(text, m.start()):
                continue
            line = text.count("\n", 0, m.start()) + 1
            with self.subTest(line=line):
                self.assertIn(
                    "echo", m.group(1),
                    "the no-marker arm at line %d skips silently; a pull "
                    "request left alone for hours with no line in any log is "
                    "exactly pirate-force-server#794" % line,
                )

    def test_the_verdict_lines_are_ascii(self):
        """The bridge console is cp874; a non-ASCII byte here kills the tool."""
        text = _text()
        for offset, body in _arms():
            if _is_quiet_arm(text, offset):
                continue
            line = text.count("\n", 0, offset) + 1
            with self.subTest(line=line):
                body.encode("ascii")


if __name__ == "__main__":
    unittest.main()
