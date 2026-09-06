"""Regenerate lua_api/message_catalog.tsv from the game's own message table.

LANE-Q.  The vendored file is a COMPLETE, ASCII-SAFE MIRROR of
``../pf_bridge/gamedata/tables/TEXTDATA_TH__MESSAGE.tsv``: all four of its
columns, with the localized ``s_MESSAGE`` text escaped ``\\uXXXX`` so the
file itself stays pure ASCII.  The Windows gate has burned two rounds on
encoding already (#961, #967) and the bridge console is cp874, so "pure
ASCII on disk" is a hard property here, not a preference.

WHY A MIRROR AND NOT "THE COLUMNS WE USE" (COO-DECISION 2026-09-07T04:05,
answering LANE-Q's 2026-09-07T03:22 letter, option (a)).  The previous
shape vendored only the two integer columns and told whoever finally emits
the frame to go read the bridge table themselves.  That means every lane
that wires a frame needs a sibling checkout or a second copy of its own --
drift, guaranteed.  Keeping the whole row where it is used costs one
regenerate command to undo.

WHY THIS SCRIPT EXISTS.  A vendored file with no way to re-derive it is a
belief.  With this script the claim "the copy still matches the source" is
a command:

    python3 tools/pf_regen_lua_message_catalog.py --check

which exits non-zero and prints the first difference if the copy has
drifted, and

    python3 tools/pf_regen_lua_message_catalog.py

which rewrites it.  The test that ties the two together lives in
``tests/test_script_lua_api_message.py`` (guarded by BRIDGE_GAMEDATA -- it
needs the bridge's tables directory and nothing else, notably not lupa).

The encoder is imported from ``lua_api.message`` rather than copied, so
this writer and the loader that reads it cannot drift apart.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.lua_api.message import (  # noqa: E402
    BODY_DIGEST_PREFIX, CATALOG_COLUMNS, body_digest, escape_message_text,
)

SOURCE_RELPATH = "gamedata/tables/TEXTDATA_TH__MESSAGE.tsv"
SOURCE = ROOT.parent / "pf_bridge" / SOURCE_RELPATH
TARGET = ROOT / "src" / "pirateforce_foundation" / "lua_api" / "message_catalog.tsv"


def read_source(path: Path):
    """``[(id, type, notify_type, text), ...]`` in the source's own order."""
    rows = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            rows.append((
                int(row["n_ID"]), int(row["n_TYPE"]),
                int(row["n_NOTIFY_TYPE"]), row["s_MESSAGE"],
            ))
    return rows


def render(rows, source_relpath: str, source_sha256: str, pulled: str) -> str:
    """The exact bytes of the vendored file, header included.

    The header is data, not decoration: the row count and the source digest
    are what a reader checks the body against without needing the source
    itself (``tests/test_script_lua_api_message.py`` does exactly that), so
    a hand-edit that adds or drops a row is caught even in a clone with no
    bridge beside it.
    """
    body = ["\t".join(CATALOG_COLUMNS)]
    for message_id, message_type, notify, text in rows:
        body.append("%d\t%d\t%d\t%s" % (
            message_id, message_type, notify, escape_message_text(text)))
    rendered_body = "\n".join(body) + "\n"
    header = [
        "# VENDORED MIRROR -- do not hand-edit.",
        "# regenerate: python3 tools/pf_regen_lua_message_catalog.py",
        "# source: pf_bridge/%s" % source_relpath,
        "# source_sha256: %s" % source_sha256,
        "# source_rows: %d" % len(rows),
        "# pulled: %s" % pulled,
        # A digest of the BODY BELOW, not of the source: this one is
        # checkable on a machine with no bridge checkout, which is the
        # machine the gate runs on (pf-adversary D1/D3/D4/D5, round 7kxfe9).
        "%s%s" % (BODY_DIGEST_PREFIX, body_digest(rendered_body)),
        "# message_text is \\uXXXX-escaped so this file stays pure ASCII;",
        "# decode with lua_api.message.unescape_message_text().",
    ]
    return "\n".join(header) + "\n" + rendered_body


class SourceMissing(Exception):
    """The bridge checkout this script reads from is not beside this repo.

    A DISTINCT outcome from "the copy has drifted" -- pf-adversary D8,
    round 7kxfe9: collapsing the two into one non-zero exit gives anyone who
    wires --check into CI a false RED on every gate run, because the gate
    has no bridge checkout.  The house convention for exactly this is
    pf_gate_preflight.py's own three states (pass / red / inconclusive), so
    --check exits 0, 1 and 2 respectively.
    """


def build(pulled: str) -> str:
    if not SOURCE.exists():
        raise SourceMissing(
            "source table not found: %s (this script needs a pf_bridge "
            "checkout beside this repository)" % SOURCE)
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    return render(read_source(SOURCE), SOURCE_RELPATH, digest, pulled)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true",
        help="exit non-zero if the vendored copy differs from the source")
    parser.add_argument(
        "--pulled", default=None,
        help="date stamp for the header (default: today, UTC-naive local)")
    args = parser.parse_args(argv)

    current = TARGET.read_text(encoding="ascii") if TARGET.exists() else ""
    # A --check must not report drift merely because today is a different
    # day: reuse the pulled stamp already in the file so the comparison is
    # about CONTENT.  A rewrite (no --check) stamps today unless told.
    pulled = args.pulled
    if pulled is None:
        stamped = [line for line in current.splitlines()
                   if line.startswith("# pulled: ")]
        pulled = (stamped[0][len("# pulled: "):] if stamped and args.check
                  else date.today().isoformat())

    try:
        rendered = build(pulled)
    except SourceMissing as exc:
        print("INCONCLUSIVE: %s" % exc)
        print("         Nothing was compared.  This is not a drift report.")
        return 2
    if args.check:
        if rendered == current:
            print("OK: %s matches %s" % (TARGET.name, SOURCE_RELPATH))
            return 0
        want = rendered.splitlines()
        have = current.splitlines()
        for index in range(max(len(want), len(have))):
            left = want[index] if index < len(want) else "<missing>"
            right = have[index] if index < len(have) else "<missing>"
            if left != right:
                print("DRIFT at line %d\n  source: %s\n  vendored: %s"
                      % (index + 1, left, right))
                break
        return 1
    TARGET.write_text(rendered, encoding="ascii", newline="\n")
    print("wrote %s (%d rows)" % (TARGET, len(read_source(SOURCE))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
