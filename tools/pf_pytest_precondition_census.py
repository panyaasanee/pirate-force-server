"""Count, name and pin every skip this test suite is allowed to produce.

WHY.  On 2026-08-20 the suite ran on a second machine for the first time
(GitHub Actions run #3, a fresh clone on windows-latest) and four tests went
red reaching for evidence a clone cannot have.  Panya's ruling was to fix that
at the test, with a declared skip, and then:

    "A skipped check is not a passed check.  Every skip must be counted, named
    and given a reason, and the count must be PINNED so that it goes red when
    it moves - in either direction.  Otherwise a real test drifts into the skip
    pile one day and nobody notices."

This tool is the second half of that.  It reads what pytest actually reported,
groups the skips, and compares them against docs/PYTEST_SKIP_PINS.json.

WHAT IT REFUSES (each of these is exit 1):
  * a skip whose reason carries no [precondition:<key>] token and is not in the
    design_skips pin - i.e. a skip nobody declared;
  * a [precondition:<key>] token for a key that is not in the registry;
  * a precondition skip on a machine where the artifact IS present;
  * a count that differs from its pin in either direction;
  * a pinned skip that did not happen when the rule says it should have.

WHAT IT IS NOT.  It does not run the test suite and it never decides whether a
test passed.  It reads a transcript.  Give it one of:

    py -3 tools/pf_pytest_precondition_census.py --report pytest_output.txt
    py -3 -m pytest tests -q -rs | py -3 tools/pf_pytest_precondition_census.py -
    py -3 tools/pf_pytest_precondition_census.py --run          (runs pytest itself)

and, when the caller narrowed the selection, the list of modules it left out:

    --excluded excluded_modules.txt

Without --excluded the tool assumes every module ran, which is what the bridge
gate does.  The exclusion list matters because a pinned skip inside an excluded
module must NOT happen - and the tool has to know the difference between "it
did not happen because the module was left out" and "it did not happen because
somebody deleted the test".

Pure standard library, ASCII only: the bridge console is code page 874 and
round 142 proved what one unmappable character does there.

Exit 0 = the census matches its pins exactly.  Exit 1 = drift.  Exit 2 = the
tool could not do its job (no transcript, unreadable pin file).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(_HERE, ".."))
PINS = os.path.join(ROOT, "docs", "PYTEST_SKIP_PINS.json")

sys.path.insert(0, os.path.join(ROOT, "tests"))
from pf_preconditions import REGISTRY, key_of  # noqa: E402

# pytest -rs prints:  SKIPPED [1] tests/test_x.py:123: the reason text
# and for a module-level skip:  SKIPPED [4] tests/test_x.py: the reason text
SKIP_LINE = re.compile(
    r"^SKIPPED\s+\[(?P<count>\d+)\]\s+(?P<module>[^\s:]+?\.py)"
    r"(?::(?P<line>\d+))?:\s*(?P<reason>.*)$"
)


def normalise(module):
    """tests\\test_x.py and ./tests/test_x.py are the same module."""
    return module.replace("\\", "/").lstrip("./")


def parse(text):
    """Return [(module, count, reason)] for every SKIPPED line in a transcript."""
    found = []
    for raw in text.splitlines():
        match = SKIP_LINE.match(raw.strip())
        if match is None:
            continue
        found.append((
            normalise(match.group("module")),
            int(match.group("count")),
            match.group("reason").strip(),
        ))
    return found


def same_reason(observed, pinned):
    """Is this the pinned reason, allowing for pytest truncating the line?

    pytest cuts its short-summary lines to the console width, so a long reason
    arrives shortened and sometimes with a trailing ellipsis.  Precondition
    skips survive that by construction - their key is the FIRST thing in the
    string - but a design skip is matched on its whole text, so the comparison
    has to be tolerant in exactly one direction: what was seen may be a PREFIX
    of what was pinned, never the other way round.  (If it were tolerant both
    ways, a pin of one word would match everything.)
    """
    observed = observed.rstrip()
    if observed.endswith("..."):
        observed = observed[:-3].rstrip()
    if not observed:
        return False
    return observed == pinned or pinned.startswith(observed)


def load_pins(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def run_pytest(extra):
    argv = [sys.executable, "-m", "pytest", "tests", "-q", "-rs",
            "-p", "no:cacheprovider"] + list(extra)
    completed = subprocess.run(argv, cwd=ROOT, capture_output=True)
    return (completed.stdout.decode("utf-8", "replace")
            + completed.stderr.decode("utf-8", "replace"))


def artifacts_here():
    """What this machine actually has, asked fresh, never cached."""
    return {key: REGISTRY[key].present for key in REGISTRY}


def census(text, excluded, pins, present=None):
    """Return (problems, observed_preconditions, observed_design_skips).

    ``present`` is the artifact map; it is a parameter and not a global lookup
    so that the tool's own tests can drive both machines - bridge and fresh
    clone - from one place, instead of only ever proving the machine they
    happen to run on.
    """
    problems = []
    if present is None:
        present = artifacts_here()
    excluded = set(normalise(m) for m in excluded)

    # ---- what actually happened -----------------------------------------
    # Fold a truncated design reason back onto the pin it belongs to, so that a
    # narrow console cannot turn one pinned skip into an unknown one.
    pinned_design = [(e["reason"], normalise(e["module"]))
                     for e in pins.get("design_skips", [])]

    def canonical_design(reason, module):
        for pinned_reason, pinned_module in pinned_design:
            if module == pinned_module and same_reason(reason, pinned_reason):
                return pinned_reason
        return reason

    observed_pre = {}     # (key, module) -> count
    observed_design = {}  # (reason, module) -> count
    for module, count, reason in parse(text):
        key = key_of(reason)
        if key is None:
            pair = (canonical_design(reason, module), module)
            observed_design[pair] = observed_design.get(pair, 0) + count
            continue
        if key not in REGISTRY:
            problems.append(
                "unknown precondition key %r reported by %s - it is not in "
                "tests/pf_preconditions.py REGISTRY" % (key, module))
            continue
        observed_pre[(key, module)] = observed_pre.get((key, module), 0) + count

    # ---- what the pins say should have happened --------------------------
    expected_pre = {}
    for entry in pins.get("preconditions", []):
        key = entry["key"]
        module = normalise(entry["module"])
        if key not in REGISTRY:
            problems.append(
                "pin names precondition key %r, which is not in the registry"
                % key)
            continue
        if module in excluded:
            expected_pre[(key, module)] = 0
        elif present.get(key, False):
            expected_pre[(key, module)] = 0
        else:
            expected_pre[(key, module)] = int(entry["count"])

    expected_design = {}
    for entry in pins.get("design_skips", []):
        module = normalise(entry["module"])
        pair = (entry["reason"], module)
        expected_design[pair] = 0 if module in excluded else int(entry["count"])

    # ---- compare, both directions ---------------------------------------
    for pair in sorted(set(observed_pre) | set(expected_pre)):
        key, module = pair
        got = observed_pre.get(pair, 0)
        want = expected_pre.get(pair)
        if want is None:
            problems.append(
                "UNPINNED: %s skipped %d test(s) on precondition '%s'.  Add it "
                "to docs/PYTEST_SKIP_PINS.json in the same commit."
                % (module, got, key))
        elif got != want:
            why = "present" if present.get(key, False) else "absent"
            problems.append(
                "PIN DRIFT: %s / precondition '%s' (artifact %s%s): pinned %d, "
                "observed %d" % (module, key, why,
                                 ", module excluded" if module in excluded
                                 else "", want, got))

    for pair in sorted(set(observed_design) | set(expected_design)):
        reason, module = pair
        got = observed_design.get(pair, 0)
        want = expected_design.get(pair)
        if want is None:
            problems.append(
                "UNDECLARED SKIP: %s skipped %d test(s) with the reason %r.  "
                "Either guard it with a precondition from "
                "tests/pf_preconditions.py, or pin it under design_skips in "
                "docs/PYTEST_SKIP_PINS.json." % (module, got, reason))
        elif got != want:
            problems.append(
                "PIN DRIFT: %s / design skip %r%s: pinned %d, observed %d"
                % (module, reason,
                   " (module excluded)" if module in excluded else "",
                   want, got))

    return problems, observed_pre, observed_design


def main():
    argv = sys.argv[1:]
    want_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]

    excluded = []
    if "--excluded" in argv:
        at = argv.index("--excluded")
        path = argv[at + 1] if at + 1 < len(argv) else None
        if path is None or not os.path.isfile(path):
            print("CENSUS ABORT: --excluded needs a readable file")
            return 2
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            excluded = [ln.strip() for ln in handle if ln.strip()]
        del argv[at:at + 2]

    if "--run" in argv:
        argv.remove("--run")
        text = run_pytest(argv)
        argv = []
    elif "--report" in argv:
        at = argv.index("--report")
        path = argv[at + 1] if at + 1 < len(argv) else None
        if path is None or not os.path.isfile(path):
            print("CENSUS ABORT: --report needs a readable file")
            return 2
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    elif argv and argv[0] == "-":
        text = sys.stdin.read()
    else:
        print(__doc__.strip().splitlines()[0])
        print("CENSUS ABORT: give me --report FILE, --run, or - for stdin")
        return 2

    try:
        pins = load_pins(PINS)
    except (OSError, ValueError) as exc:
        print("CENSUS ABORT: cannot read %s: %s" % (PINS, exc))
        return 2

    problems, observed_pre, observed_design = census(text, excluded, pins)

    total = sum(observed_pre.values()) + sum(observed_design.values())
    lines = []
    lines.append("PYTEST SKIP CENSUS - %d skip(s) on this machine" % total)
    lines.append("  modules excluded from the selection: %d" % len(excluded))
    # Width from the longest key rather than a constant: round 118 added
    # original_schema_history (23 characters) and the hand-picked 18 turned the
    # table the gate pastes into GITHUB_STEP_SUMMARY into a ragged list.
    width = max([len(key) for key in REGISTRY] + [18])
    lines.append("  artifacts this machine has:")
    for key in sorted(REGISTRY):
        lines.append("    %-*s %s" % (
            width, key, "present" if REGISTRY[key].present else "ABSENT"))
    if observed_pre:
        lines.append("  skipped for a declared precondition:")
        for (key, module), count in sorted(observed_pre.items()):
            lines.append("    %-*s %-52s x%d" % (width, key, module, count))
    if observed_design:
        lines.append("  skipped by design (not a missing artifact):")
        for (reason, module), count in sorted(observed_design.items()):
            lines.append("    %-52s x%d  %s" % (module, count, reason))
    if not observed_pre and not observed_design:
        lines.append("  nothing was skipped.")

    if want_json:
        payload = {
            "total": total,
            "excluded_modules": len(excluded),
            "artifacts": {k: REGISTRY[k].present for k in sorted(REGISTRY)},
            "preconditions": {"%s|%s" % k: v
                              for k, v in sorted(observed_pre.items())},
            "design_skips": {"%s|%s" % (m, r): v
                             for (r, m), v in sorted(observed_design.items())},
            "problems": problems,
            "result": "PASS" if not problems else "FAIL",
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if problems else 0

    for line in lines:
        print(line)
    if problems:
        print("")
        print("CENSUS FAILURES (%d):" % len(problems))
        for problem in problems:
            print("  - %s" % problem)
        print("")
        print("RESULT: FAIL")
        return 1
    print("")
    print("every skip is declared, named and pinned")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
