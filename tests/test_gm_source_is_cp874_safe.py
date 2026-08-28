"""Every source file this lane owns must survive `print()` on the bridge console.

WHY THIS FILE EXISTS (a measured cost, not a style rule)
--------------------------------------------------------
Round `gr2q9j` lost its entire pull request to this. `pirate-force-server#200`
was closed automatically by `.github/workflows/merge-claude-pr.yml` with job
`gate` = failure (Actions run 33168539342, commit `b262be7`), and the single
reason was five `U+1F534` characters sitting in comments: four in
`gm/chat_command_action.py` and one in `lane_hooks/lane_gm_chat_command.py`.
The work itself was sound and every test passed. A whole round's code sat
stranded on a branch until the next round recovered it by hand.

The gate that catches this is `gate-windows.yml`'s cp874 static tripwire, and
it runs ONLY on Windows, ONLY in Actions, and ONLY after the pull request is
already open -- by which time the automatic closer has already fired. Nothing
in the cloud sanity run a lane can execute before pushing said a word about
it. This file is that missing pre-push check, scoped to the files this lane
may write.

WHAT IT ACTUALLY ASSERTS
------------------------
Not "is it ASCII". Thai comments are allowed by the house rules and encode to
cp874 fine, which is the whole point of the bridge console using that code
page. The failure mode is narrower: a character with NO cp874 mapping does
not degrade into `?` inside `print()` -- with `PYTHONIOENCODING=cp874:strict`
it raises `UnicodeEncodeError` and kills the tool mid-report. So the test is
exactly `str.encode("cp874")`, the same operation the console performs, on
the same files the gate scans.

WHY IT READS GIT AND NOT JUST THE WORKING TREE
----------------------------------------------
pf-adversary (round `vvxkft`) broke the first version of this file by pointing
at the branch it was written on. The commit `ac711e1` carried all five
characters; the working tree had them removed but not yet committed; the test
walked the filesystem with `rglob` and reported `3 passed`. Green about an
editor buffer, red about the thing that would be pushed -- which is the exact
question this file exists to answer, since the gate scans the pushed tree.

So it checks BOTH, and fails if either is bad:

* the working tree, which is what CI checks out and what the author is about
  to commit; and
* the content of `HEAD`, read with `git show`, which is what is already
  committed and would go out on the next push.

The file SET comes from `git ls-files`, matching the gate (which walks tracked
files) rather than the filesystem -- so an untracked scratch file under `gm/`
is correctly ignored instead of producing a red the gate would never give.
When git is not available at all the HEAD half is skipped and the working
tree half still runs; a missing git is not a reason to report nothing.
"""
from __future__ import annotations

import pathlib
import subprocess
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

# The lane's own write zone, per its founding order: gm/ is entirely this
# lane's, and lane_hooks/lane_gm_*.py are the hook modules it registers.
# Deliberately not the whole tree -- a file another lane owns going red here
# would be a failure this lane cannot fix and would teach everyone to ignore
# the test. The lane owns no file under tools/, which is where every entry in
# the gate's own ALLOWED pin list lives, so the two sets never overlap.
LANE_PATH_SPECS = (
    "src/pirateforce_foundation/gm",
    "src/pirateforce_foundation/lane_hooks/lane_gm_*.py",
)


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ("git", *args),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
    )


def _tracked_lane_files() -> list[str] | None:
    """Repo-relative paths of the lane's tracked .py files, or None if no git."""
    done = _git("ls-files", "-z", "--", *LANE_PATH_SPECS)
    if done.returncode != 0:
        return None
    found = [p for p in done.stdout.split("\0") if p.endswith(".py")]
    return sorted(found)


def _worktree_lane_files() -> list[pathlib.Path]:
    src = REPO_ROOT / "src" / "pirateforce_foundation"
    found = sorted((src / "gm").rglob("*.py"))
    found += sorted((src / "lane_hooks").glob("lane_gm_*.py"))
    return found


def _first_unmappable(text: str) -> tuple[int, str] | None:
    """(line number, the offending character) for the first cp874 failure."""
    for number, line in enumerate(text.splitlines(), 1):
        try:
            line.encode("cp874")
        except UnicodeEncodeError as error:
            return number, line[error.start:error.end]
    return None


def _complaint(where: str, rel: str, number: int, bad: str) -> str:
    return (
        "%s: %s line %d has a character with no cp874 mapping: %s (%s). It "
        "would raise UnicodeEncodeError inside print() on the bridge console, "
        "and .github/workflows/gate-windows.yml fails the gate for it -- "
        "which closes the pull request automatically. Use an ASCII marker "
        "instead (this lane uses '!!')."
        % (where, rel, number, bad, " ".join(hex(ord(ch)) for ch in bad))
    )


class LaneSourceIsCp874SafeTests(unittest.TestCase):
    def test_the_file_list_is_not_empty(self):
        # Without this, a moved directory turns the suites below into green
        # loops over zero files -- the exact false green pf-adversary flagged
        # elsewhere in this lane.
        worktree = _worktree_lane_files()
        self.assertGreater(len(worktree), 5, worktree)
        names = {p.name for p in worktree}
        self.assertIn("chat_command_action.py", names)
        self.assertIn("lane_gm_chat_command.py", names)

        tracked = _tracked_lane_files()
        if tracked is not None:
            self.assertGreater(len(tracked), 5, tracked)
            self.assertIn(
                "src/pirateforce_foundation/gm/chat_command_action.py", tracked
            )

    def test_every_lane_source_in_the_working_tree_encodes_to_cp874(self):
        for path in _worktree_lane_files():
            rel = str(path.relative_to(REPO_ROOT))
            with self.subTest(path=rel):
                hit = _first_unmappable(path.read_text(encoding="utf-8"))
                if hit is not None:
                    self.fail(_complaint("working tree", rel, *hit))

    def test_every_lane_source_committed_at_head_encodes_to_cp874(self):
        # The half that would have caught this round's own branch: the working
        # tree was already clean while HEAD still carried all five characters.
        tracked = _tracked_lane_files()
        if tracked is None:
            self.skipTest("not a git checkout; the working-tree test still ran")
        for rel in tracked:
            with self.subTest(path=rel):
                done = _git("show", "HEAD:%s" % rel)
                if done.returncode != 0:
                    # A file added but not yet committed has no HEAD blob. The
                    # working-tree test above covers it; nothing to check here.
                    continue
                hit = _first_unmappable(done.stdout)
                if hit is not None:
                    self.fail(_complaint("committed at HEAD", rel, *hit))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
