"""List the test files that only run when the pf_bridge checkout is present.

WHY THIS EXISTS (COO work order `0445` item 3, from LANE-UI's D1 `0335`).
``.github/workflows/gate-windows.yml`` checks out THIS repository and nothing
else, so every test guarded by a precondition whose paths live in the sibling
``pf_bridge`` working directory skips on the gate - on every commit, forever,
with a reason that reads like a healthy skip.  Nobody was evaluating them.
The report-only job in ``.github/workflows/bridge-guarded-tests.yml`` clones
the bridge beside the workspace and runs exactly the files this tool names.

WHY THE LIST IS DERIVED AND NOT WRITTEN DOWN.  A hard-coded list is right on
the day it is written and wrong the first time a lane adds a guarded test -
and it would be wrong SILENTLY, because a missing file looks the same as a
file with no failures.  So the set is recomputed from two facts that cannot
drift from the tests themselves: the precondition registry in
``tests/pf_preconditions.py`` (which preconditions resolve inside the bridge
checkout) and the test sources (which files name those preconditions).

The dependency walk is recursive on purpose: ``AllOfThese`` holds ``parts``
that are themselves preconditions, and ``tests/test_script_lua_corpus.py``
reaches the bridge's Lua corpus only through one of those.

Exit codes: 0 with at least one file named, 2 when the derivation produced
nothing.  2 is not a formality - a caller that pipes an empty list into
pytest runs zero tests and reports success, which is the exact failure this
whole job exists to end.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"

#: The sibling directory whose absence is the whole point.  Kept as a name
#: rather than a literal so this file says WHAT it means, not just where.
BRIDGE_DIRNAME = "pf_bridge"


def _paths_of(obj, seen=None):
    """Every filesystem path a precondition (or a composite) requires."""
    if seen is None:
        seen = set()
    if id(obj) in seen:
        return []
    seen.add(id(obj))
    found = []
    for path in getattr(obj, "paths", ()) or ():
        found.append(Path(path))
    for part in getattr(obj, "parts", ()) or ():
        found.extend(_paths_of(part, seen))
    return found


def bridge_precondition_names(module) -> list:
    """Module-level names in pf_preconditions that need the bridge checkout.

    ANY path under the bridge is enough: a precondition with one bridge path
    and one in-repo path still skips on a machine without the bridge.
    """
    names = []
    for name, value in sorted(vars(module).items()):
        if not name.isupper():
            continue
        paths = _paths_of(value)
        if not paths:
            continue
        for path in paths:
            if BRIDGE_DIRNAME in path.parts:
                names.append(name)
                break
    return names


def guarded_test_files(names, tests_dir: Path = TESTS) -> list:
    """Test files that name at least one of ``names``.

    Word-bounded so ``BRIDGE_SIBLING`` does not also match a longer name that
    merely starts with it, and so a name inside a longer identifier is not a
    hit.  Comments and docstrings DO count: a file that only discusses a
    precondition it does not use costs one cheap extra test file in the job,
    while a missed file costs a test nobody evaluates - the asymmetry the
    whole tool is about.
    """
    if not names:
        return []
    pattern = re.compile(r"\b(?:%s)\b" % "|".join(re.escape(n) for n in names))
    hits = []
    for path in sorted(tests_dir.glob("test_*.py")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if pattern.search(text):
            hits.append(path)
    return hits


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--names", action="store_true",
        help="print the precondition names instead of the test files")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(TESTS))
    import pf_preconditions

    names = bridge_precondition_names(pf_preconditions)
    if args.names:
        for name in names:
            print(name)
        return 0 if names else 2

    files = guarded_test_files(names)
    for path in files:
        print(path.relative_to(ROOT).as_posix())
    if not files:
        sys.stderr.write(
            "FATAL: no bridge-guarded test file derived from %d precondition "
            "name(s) -- the registry or the tests moved and this tool went "
            "blind; a caller must NOT treat an empty list as 'nothing to "
            "run'\n" % (len(names),))
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
