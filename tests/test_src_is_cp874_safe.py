"""No file under ``src/`` may carry a character the bridge console cannot print.

WHY THIS FILE EXISTS, AND WHY IT IS NOT A DUPLICATE OF THE GM ONE.
``tests/test_gm_source_is_cp874_safe.py`` exists because round ``gr2q9j``
lost an entire pull request to five ``U+1F534`` characters: the Windows gate's
cp874 static tripwire went red, ``merge-claude-pr.yml`` closed the PR
automatically, and a sound round sat stranded on a branch until the next one
recovered it by hand.  That test was scoped to ``src/gm/``, which is the lane
that got burned.

The gate is not scoped that way.  Its tripwire scans ``tools/``, ``src/`` and
``current/``, and it goes red on ONE new unmappable character anywhere in
them.  So every lane that writes under ``src/`` carries the same risk, and
until this file only one of them had a pre-push check for it.

MEASURED, round ua236k: this lane's own first draft of
``scene_identity_rule.py`` quoted a COO ruling verbatim and brought
``U+21D2`` (RIGHTWARDS DOUBLE ARROW) in with the quote.  Thai encodes to
cp874 fine -- that is the whole point of the console using that code page --
but the arrow does not, and nothing a lane can run in the cloud would have
said so before the push.  It was caught by hand.  The next one would not be.

WHAT IT ASSERTS.  Not "is it ASCII".  Exactly ``str.encode("cp874")``, the
same operation ``print()`` performs under the gate's
``PYTHONIOENCODING=cp874:strict``, on the same tree the gate scans.  Thai
comments stay legal.

SCOPE, AND THE PART THAT IS NOT THIS LANE'S TO DECIDE.  ``src/`` measures
clean today, so the assertion is a flat zero rather than a pinned debt table.
``tools/`` is NOT covered here: it carries four pre-existing unmappable
characters that the gate pins by filename and count, and re-implementing that
pin table in a second place is how two pins drift apart.  Widening this to
``tools/`` and ``current/``, or folding the gm file into it, is chief's call
-- see this round's PR body.
"""

from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCANNED = ROOT / "src"


def _unmappable(text: str) -> list[str]:
    """Every distinct character in ``text`` with no cp874 mapping.

    Character by character rather than encoding the whole string: the whole
    string tells you THAT it fails, and a lane that has to find one arrow in
    a nine-hundred-line docstring needs to know WHICH.
    """
    bad = []
    for char in dict.fromkeys(text):
        try:
            char.encode("cp874")
        except UnicodeEncodeError:
            bad.append(char)
    return bad


class SrcIsCp874Safe(unittest.TestCase):

    def test_every_python_file_under_src_encodes_to_cp874(self) -> None:
        offenders = {}
        for path in sorted(SCANNED.rglob("*.py")):
            bad = _unmappable(path.read_text(encoding="utf-8"))
            if bad:
                offenders[path.relative_to(ROOT).as_posix()] = bad
        self.assertEqual(
            offenders, {},
            "these characters have no cp874 mapping, and the Windows gate's "
            "static tripwire goes red on them -- which closes the pull "
            "request automatically (round gr2q9j lost a whole round this "
            "way).  Replace them with ASCII: '=>' for an arrow, '--' for a "
            "dash, a word for an emoji.  Thai is fine and does not need "
            "changing:\n  "
            + "\n  ".join(
                "%s: %s" % (name, " ".join("U+%04X %s" % (ord(c), c)
                                           for c in chars))
                for name, chars in sorted(offenders.items())
            )
        )

    def test_the_scan_finds_files_at_all(self) -> None:
        """A guard that walks an empty tree passes and proves nothing.

        The gm file's own history is the reason this is here: its first
        version was green about an editor buffer rather than about the tree
        that would be pushed, and pf-adversary caught it.  A wrong ROOT would
        fail the same way, silently.
        """
        found = list(SCANNED.rglob("*.py"))
        self.assertGreater(len(found), 50, "src/ scan found almost nothing")

    def test_the_check_would_actually_fail_on_a_bad_character(self) -> None:
        """The tripwire's own self-check, in miniature.

        The gate proves its tripwire is armed by printing U+1F534 and
        requiring a crash.  Same idea: if ``_unmappable`` ever returns empty
        for a character cp874 genuinely cannot hold, the test above is a
        green that means nothing.
        """
        self.assertEqual(_unmappable("\U0001F534"), ["\U0001F534"])
        self.assertEqual(_unmappable("⇒"), ["⇒"])
        self.assertEqual(_unmappable("a => b"), [])
        # Thai must NOT be flagged; the console's code page is cp874 for
        # exactly this reason.
        self.assertEqual(_unmappable("กฎที่"), [])


if __name__ == "__main__":
    unittest.main()
