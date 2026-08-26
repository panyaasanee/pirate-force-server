#!/usr/bin/env python3
"""LANE-B: write scenarios/combat_aggro_001.json from the code that owns it.

WHY THIS TOOL EXISTS.  ``scenarios/combat_aggro_001.json`` is not a hand-typed
document and must never become one: it stores this lane's four INVENTED numbers
-- leash radius, home radius, attack range, cadence -- once per monster, so
thirteen times over.  An adversarial review of the round that added it found the
lane telling the COO that rolling one of those numbers back was "one constant
and one test line", while the pin quietly held every one of them and nothing in
``tools/`` could rewrite it.  This tool is that missing half.

WHAT IT PROVES AND WHAT IT DOES NOT.  Nothing.  The pin is the code's own output
compared against itself, so ``test_the_committed_pin_is_what_the_code_computes``
can only ever catch a STALE file, never a wrong number.  That is worth having --
a changed constant that nobody re-pinned goes red -- and it is not evidence, and
the pin says so in its own ``not_a_scenario`` marker.

ASCII ONLY, ON PURPOSE -- lesson 86, the bridge console is code page 874.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path,
                        help="write the pin here (default: stdout)")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))
    from pirateforce_foundation import field_mobs, mob_ai_control

    document = mob_ai_control.pin_document(field_mobs.load_roster())
    body = json.dumps(document, indent=2, ensure_ascii=True) + "\n"
    if not body.isascii():
        sys.stderr.write("REFUSED: the pin is not pure ASCII\n")
        return 2
    if args.out is None:
        sys.stdout.write(body)
    else:
        args.out.write_text(body, encoding="ascii", newline="\n")
        sys.stderr.write("wrote %s: %d monsters\n"
                         % (args.out, document["mob_count"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
