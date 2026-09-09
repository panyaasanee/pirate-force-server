#!/usr/bin/env python3
"""LANE-CS: full SKILL_CONTEXT census extractor.

WHAT THIS TOOL IS FOR.  ``tools/pf_class_skill_starting_kit_extract.py``
writes the 8-row starting-kit copy ``skill_catalog.py`` loads.  That scope
was right for the kit and is wrong for the learn rules: a player's skill
window offers ids this project's own catalog had never heard of, so
``skill_learn_validator`` answered ``KeyError`` for every id but 8.  This
tool writes the OTHER copy -- every row of the client's own
``CONSTDATA_TH__SKILL_CONTEXT.tsv``, columns and values verbatim -- which
``skill_context_census.py`` loads.

    pf_bridge/gamedata/tables/CONSTDATA_TH__SKILL_CONTEXT.tsv

WHAT IT DOES NOT DO, AND WHY THAT MATTERS HERE.  It does not decide which
class may learn which skill: pf-adversary (round ``iazmrv``) measured that
no committed table answers that, and the starting-kit extractor's docstring
carries the four reasons.  Widening the CENSUS is not widening that claim --
the census says "the client declares 2165 skill rows and here is each row's
own data", and says nothing at all about who may learn one.

It also renames nothing and interprets nothing.  ``n_PASSIVE`` carries six
distinct values in this table (0,1,2,3,4,5), not a boolean, and
``n_TARGET`` five (0,1,2,4,5); neither is given a meaning here, because
nothing committed states one.  The columns land under their own
client-given names so a later round that DOES prove a meaning can add a
named reader without this file having guessed first.

USAGE (from a checkout with the bridge clone beside it):

    python3 tools/pf_skill_context_census_extract.py \\
        --bridge ../pf_bridge --write

Without ``--write`` it prints the sha256 it WOULD write and diffs nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

SOURCE_RELATIVE = "gamedata/tables/CONSTDATA_TH__SKILL_CONTEXT.tsv"
TARGET_RELATIVE = "src/pirateforce_foundation/data/skill_context_all.tsv"


def build(source: Path) -> bytes:
    """The bytes the census copy should hold, read from the bridge table.

    Verbatim: the source's own header line and every data line, in the
    source's own order, LF terminated.  No column is dropped and no value is
    reformatted, so a diff against the bridge table is the whole audit.
    """
    raw = source.read_bytes()
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as error:
        raise SystemExit(
            "%s is not ASCII at byte %d -- the server copy is loaded with "
            "encoding='ascii' on purpose (the bridge console is cp874), so a "
            "non-ASCII row has to be reported, not silently transcoded"
            % (source, error.start)
        )
    lines = text.splitlines()
    if not lines:
        raise SystemExit("%s is empty" % (source,))
    header = lines[0].split("\t")
    if header[0] != "n_ID":
        raise SystemExit(
            "%s does not start with n_ID: %r" % (source, header[:3])
        )
    seen = set()
    for line in lines[1:]:
        skill_id = line.split("\t", 1)[0]
        if skill_id in seen:
            raise SystemExit(
                "%s carries skill id %s twice -- the census keys by id and "
                "cannot choose between two rows" % (source, skill_id)
            )
        seen.add(skill_id)
    return ("\n".join(lines) + "\n").encode("ascii")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bridge", default="../pf_bridge",
        help="path to the pf_bridge clone (default: ../pf_bridge)",
    )
    parser.add_argument(
        "--write", action="store_true",
        help="write the copy; without it, only report the sha256",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="exit non-zero unless the shipped copy is byte-identical to a "
             "fresh mining of the bridge table (drift detection)",
    )
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parents[1]
    source = Path(args.bridge).expanduser() / SOURCE_RELATIVE
    if not source.is_file():
        raise SystemExit("no such table: %s" % (source,))
    payload = build(source)
    digest = hashlib.sha256(payload).hexdigest()
    target = repo / TARGET_RELATIVE

    if args.check:
        if not target.is_file():
            print("missing: %s" % (target,), file=sys.stderr)
            return 1
        shipped = target.read_bytes()
        if shipped != payload:
            print(
                "drift: %s is %d bytes, a fresh mining is %d bytes"
                % (target, len(shipped), len(payload)),
                file=sys.stderr,
            )
            return 1
        print("ok: %s matches a fresh mining (sha256 %s)" % (target, digest))
        return 0

    if args.write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        print("wrote %s (%d bytes)" % (target, len(payload)))
    else:
        print("would write %s (%d bytes)" % (target, len(payload)))
    print("ALL_CONTEXT_SOURCE_SHA256 = %r" % (digest,))
    return 0


if __name__ == "__main__":
    sys.exit(main())
