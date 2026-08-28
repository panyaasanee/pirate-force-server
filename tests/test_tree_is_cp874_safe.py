"""The gate's cp874 static tripwire, runnable on Linux BEFORE a push.

WHY THIS FILE EXISTS (measured, not a style rule)
-------------------------------------------------
`pirate-force-server#200` (round `gr2q9j`) was closed automatically by
`.github/workflows/merge-claude-pr.yml` with job `gate` = failure (Actions run
33168539342, commit `b262be7`). The single cause was five `U+1F534` characters
in comments. Every test passed; the work was sound; the whole round's code sat
stranded on a branch until round `vvxkft` recovered it by hand. Round 142 lost
a report the same way, on the bridge console rather than in Actions.

The check that catches this lives in `.github/workflows/gate-windows.yml`
("cp874 static tripwire (tools/, src/, current/)"). It runs ONLY on Windows,
ONLY in Actions, and ONLY once the pull request is already open -- by which
time the automatic closer fires the moment the gate goes red. Nothing a lane
can run in the cloud before pushing said a word about it.

`tests/test_gm_source_is_cp874_safe.py` (round `vvxkft`) closed that hole for
ONE lane's write zone, by design: a file another lane owns going red in a
lane's own suite is a red that lane cannot fix. This file closes it for the
whole scanned tree, and it is safe to do that here because it does not invent
a standard -- it reproduces the gate's, pins included. It is green today for
exactly the tree the gate is green on, and it goes red exactly when the gate
would.

WHAT IT ASSERTS
---------------
Not "is it ASCII". Thai text encodes to cp874 fine and the house rules allow
it in prose. The failure mode is narrower: a character with NO cp874 mapping
does not degrade into `?` inside `print()` -- under the gate's
`PYTHONIOENCODING=cp874:strict` it raises `UnicodeEncodeError` and kills the
tool mid-report. So the operation checked is exactly `str.encode("cp874")`, on
exactly the file set the gate walks (tracked `.py` under `tools/`, `src/`,
`current/`), compared against exactly the gate's own pin table.

WHY THE PINS ARE READ OUT OF THE WORKFLOW AND NOT COPIED
-------------------------------------------------------
A copied pin table is a second source of truth that drifts silently, and the
drift is invisible until a pull request dies. This file parses the `ALLOWED`
dict out of `gate-windows.yml` itself. If the workflow's table changes, this
test changes with it in the same commit or it fails loudly; it can never be
green about a rule the gate no longer enforces.

The pinned counts are two-directional in the gate -- debt going DOWN
unannounced is red too -- and they are reproduced that way here. Removing one
of the pinned characters means lowering its pin in the same commit.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "gate-windows.yml"

# The gate's own scope line: tracked .py under these prefixes only. tests/ is
# excluded there because several modules carry non-ASCII test DATA on purpose
# (fullwidth latin in test_player_name.py, CJK in test_delete_actor.py), and
# docs/ and reports/ because a markdown file is never printed to a console.
SCANNED_PREFIXES = ("tools/", "src/", "current/")

_ALLOWED_ROW = re.compile(r'^\s*"([^"]+)":\s*(\d+),\s*$')


def _allowed_from_workflow() -> dict[str, int]:
    """The gate's ALLOWED table, parsed out of gate-windows.yml."""
    text = WORKFLOW.read_text(encoding="utf-8")
    start = text.find("ALLOWED = {")
    if start == -1:
        raise AssertionError(
            "no `ALLOWED = {` block in %s -- the gate's cp874 tripwire was "
            "renamed, moved or removed. This test cannot mirror a table it "
            "cannot find; fix the parse or delete both together."
            % WORKFLOW.relative_to(REPO_ROOT)
        )
    end = text.find("}", start)
    if end == -1:
        raise AssertionError("unterminated ALLOWED block in gate-windows.yml")
    pins: dict[str, int] = {}
    for line in text[start:end].splitlines()[1:]:
        hit = _ALLOWED_ROW.match(line)
        if hit is not None:
            pins[hit.group(1)] = int(hit.group(2))
    if not pins:
        raise AssertionError(
            "the ALLOWED block in gate-windows.yml parsed to zero rows -- a "
            "green loop over nothing is the false green this file exists to "
            "prevent"
        )
    return pins


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ("git", *args),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
    )


def _tracked_scanned_files() -> list[str] | None:
    """Repo-relative tracked .py paths the gate scans, or None if no git."""
    done = _git("ls-files")
    if done.returncode != 0:
        return None
    found = [
        rel.strip()
        for rel in done.stdout.split("\n")
        if rel.strip().endswith(".py")
        and rel.strip().startswith(SCANNED_PREFIXES)
    ]
    return sorted(found)


def _count_unmappable(text: str) -> tuple[int, list[tuple[int, str]]]:
    """(how many characters have no cp874 mapping, first 20 as (line, hex))."""
    total, detail = 0, []
    for number, line in enumerate(text.splitlines(), 1):
        for ch in line:
            try:
                ch.encode("cp874")
            except UnicodeEncodeError:
                total += 1
                if len(detail) < 20:
                    detail.append((number, hex(ord(ch))))
    return total, detail


def _complaint(where: str, rel: str, got: int, want: int, detail) -> str:
    lines = ", ".join("line %d %s" % (n, cp) for n, cp in detail) or "none"
    if got > want:
        why = (
            "This is the failure that closed pirate-force-server#200: the gate "
            "goes red and merge-claude-pr.yml closes the pull request. Use an "
            "ASCII marker instead."
        )
    else:
        why = (
            "The gate pins these counts in BOTH directions -- debt going down "
            "unannounced is red too. Lower the pin in "
            ".github/workflows/gate-windows.yml in the same commit and say why."
        )
    return (
        "%s: %s has %d character(s) with no cp874 mapping, the gate pins %d "
        "(%s). %s" % (where, rel, got, want, lines, why)
    )


class TreeIsCp874SafeTests(unittest.TestCase):
    def test_the_scanned_file_list_is_not_empty(self):
        # Without this, a moved directory or a git-less checkout turns the
        # suites below into green loops over zero files.
        tracked = _tracked_scanned_files()
        if tracked is None:
            self.skipTest("not a git checkout; nothing to mirror the gate on")
        self.assertGreater(len(tracked), 50, tracked)
        self.assertIn("src/pirateforce_foundation/runtime.py", tracked)

    def test_the_pin_table_matches_the_gate(self):
        pins = _allowed_from_workflow()
        # Every pinned path must still be a file the gate actually scans --
        # otherwise the pin is dead weight and hides nothing.
        for rel in pins:
            with self.subTest(pin=rel):
                self.assertTrue(
                    rel.startswith(SCANNED_PREFIXES),
                    "%s is pinned but outside the gate's scan scope" % rel,
                )

    def test_every_scanned_source_in_the_working_tree_matches_its_pin(self):
        pins = _allowed_from_workflow()
        tracked = _tracked_scanned_files()
        if tracked is None:
            self.skipTest("not a git checkout; the gate walks tracked files")
        for rel in tracked:
            path = REPO_ROOT / rel
            if not path.is_file():
                continue
            with self.subTest(path=rel):
                got, detail = _count_unmappable(path.read_text(encoding="utf-8"))
                want = pins.get(rel, 0)
                if got != want:
                    self.fail(_complaint("working tree", rel, got, want, detail))

    def test_every_pinned_file_still_exists(self):
        # A pinned file that was deleted or renamed leaves the gate comparing
        # got=0 against want=N -- red, and confusingly so. Catch it here first.
        pins = _allowed_from_workflow()
        tracked = _tracked_scanned_files()
        if tracked is None:
            self.skipTest("not a git checkout")
        for rel, want in pins.items():
            if want == 0:
                # Deliberately kept rows: the gate documents that a cleaned
                # file stays in the table at 0 as the record that it once
                # carried the trap. It may legitimately be gone.
                continue
            with self.subTest(pin=rel):
                self.assertIn(rel, tracked)

    def test_every_scanned_source_committed_at_head_matches_its_pin(self):
        # The half that catches a clean editor buffer over a dirty commit: the
        # gate scans the pushed tree, not the working tree.
        pins = _allowed_from_workflow()
        tracked = _tracked_scanned_files()
        if tracked is None:
            self.skipTest("not a git checkout; the working-tree test still ran")
        for rel in tracked:
            with self.subTest(path=rel):
                done = _git("show", "HEAD:%s" % rel)
                if done.returncode != 0:
                    # Added but not yet committed: no HEAD blob. The
                    # working-tree test above covers it.
                    continue
                got, detail = _count_unmappable(done.stdout)
                want = pins.get(rel, 0)
                if got != want:
                    self.fail(
                        _complaint("committed at HEAD", rel, got, want, detail)
                    )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
