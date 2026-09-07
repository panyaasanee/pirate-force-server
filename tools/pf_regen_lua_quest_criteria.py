"""Regenerate lua_api/quest_criteria_{curve,rows}.tsv from the game's tables.

LANE-Q.  Two vendored mirrors, one command, same shape and same reasons as
``tools/pf_regen_lua_message_catalog.py`` (COO-DECISION 2026-09-07T04:05):

  * ``quest_criteria_curve.tsv``  <- ``CONSTDATA_TH__STANDARD_QUEST.tsv``
    (255 levels x cash/exp/skill-point: the standard per-level quest reward
    curve the six ``Quest.Add*Criteria*`` names read their base amount from)
  * ``quest_criteria_rows.tsv``   <- ``QUESTDATA_TH__QUEST.tsv``
    (1544 quests x criteria level + the three float multipliers)

WHY MIRROR THE SECOND ONE AT ALL, when the first is the amount table.  The
amount is ``curve[level] * multiplier`` and BOTH halves live in different
files: vendoring one and telling the reader to go find the other in a
sibling checkout is the drift the message-catalog decision already ruled
against.  Only the reward-relevant columns are copied -- five of the quest
table's 62 -- because the other 57 belong to other lanes' seams and copying
them here would make this file the place people edit instead of the source.

BOTH MIRRORS ARE PURE ASCII on disk (the bridge console is cp874) and carry
a ``# body_sha256:`` of their own body, so ``--check`` is meaningful in two
different ways on two different machines:

    python3 tools/pf_regen_lua_quest_criteria.py --check

exits 0 when both copies match the source tables, 1 when one has drifted,
and 2 -- INCONCLUSIVE, not a drift report -- when there is no ``pf_bridge``
checkout beside this repository, which is the case on the Windows gate.
The digest header is what the gate CAN check, and does, in
``tests/test_script_lua_api_quest_criteria.py``.
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

from pirateforce_foundation.lua_api.quest_criteria import (  # noqa: E402
    BODY_DIGEST_PREFIX, CURVE_COLUMNS, ROW_COLUMNS, body_digest,
)

BRIDGE = ROOT.parent / "pf_bridge"
CURVE_SOURCE_RELPATH = "gamedata/tables/CONSTDATA_TH__STANDARD_QUEST.tsv"
ROWS_SOURCE_RELPATH = "gamedata/tables/QUESTDATA_TH__QUEST.tsv"

LUA_API = ROOT / "src" / "pirateforce_foundation" / "lua_api"
CURVE_TARGET = LUA_API / "quest_criteria_curve.tsv"
ROWS_TARGET = LUA_API / "quest_criteria_rows.tsv"


class SourceMissing(Exception):
    """No bridge checkout beside this repo.  Distinct from "drifted"."""


def read_curve(path: Path):
    rows = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            rows.append((int(row["n_ID"]), int(row["n_QUEST_CASH"]),
                         int(row["n_QUEST_EXP"]), int(row["n_QUEST_SP"])))
    return rows


def read_rows(path: Path):
    """Multipliers are copied AS WRITTEN, not reformatted.

    The source stores them float32-widened (``0.1`` is on disk as
    ``0.10000000149011612``).  Rewriting those as ``0.1`` would be this
    repository deciding what the designer meant; round-tripping the literal
    keeps ``--check`` honest and keeps the decision where it belongs.
    """
    rows = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            rows.append((int(row["n_ID"]), int(row["n_LEVEL_EXP"]),
                         row["f_CASH"].strip(), row["f_EXP"].strip(),
                         row["f_SP"].strip()))
    return rows


def _header(target_name: str, source_relpath: str, source_sha256: str,
            count: int, pulled: str, rendered_body: str, note: str) -> str:
    lines = [
        "# VENDORED MIRROR -- do not hand-edit.",
        "# regenerate: python3 tools/pf_regen_lua_quest_criteria.py",
        "# source: pf_bridge/%s" % source_relpath,
        "# source_sha256: %s" % source_sha256,
        "# source_rows: %d" % count,
        "# pulled: %s" % pulled,
        "%s%s" % (BODY_DIGEST_PREFIX, body_digest(rendered_body)),
        "# %s" % note,
    ]
    return "\n".join(lines) + "\n"


def render_curve(rows, digest: str, pulled: str) -> str:
    body = ["\t".join(CURVE_COLUMNS)]
    for level, cash, exp, skill_point in rows:
        body.append("%d\t%d\t%d\t%d" % (level, cash, exp, skill_point))
    rendered = "\n".join(body) + "\n"
    return _header(
        CURVE_TARGET.name, CURVE_SOURCE_RELPATH, digest, len(rows), pulled,
        rendered,
        "base reward per level; the amount is this times the quest row's "
        "multiplier.") + rendered


def render_rows(rows, digest: str, pulled: str) -> str:
    body = ["\t".join(ROW_COLUMNS)]
    for quest_id, level, cash, exp, sp in rows:
        body.append("%d\t%d\t%s\t%s\t%s" % (quest_id, level, cash, exp, sp))
    rendered = "\n".join(body) + "\n"
    return _header(
        ROWS_TARGET.name, ROWS_SOURCE_RELPATH, digest, len(rows), pulled,
        rendered,
        "criteria_level is QUESTDATA n_LEVEL_EXP; multipliers are f_CASH/"
        "f_EXP/f_SP copied verbatim (float32-widened in the source).") + rendered


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(pulled_curve: str, pulled_rows: str):
    curve_source = BRIDGE / CURVE_SOURCE_RELPATH
    rows_source = BRIDGE / ROWS_SOURCE_RELPATH
    missing = [str(p) for p in (curve_source, rows_source) if not p.exists()]
    if missing:
        raise SourceMissing(
            "source table(s) not found: %s (this script needs a pf_bridge "
            "checkout beside this repository)" % ", ".join(missing))
    return (
        render_curve(read_curve(curve_source), _digest(curve_source),
                     pulled_curve),
        render_rows(read_rows(rows_source), _digest(rows_source), pulled_rows),
    )


def _pulled_of(path: Path, fallback: str) -> str:
    if not path.exists():
        return fallback
    for line in path.read_text(encoding="ascii").splitlines():
        if line.startswith("# pulled: "):
            return line[len("# pulled: "):]
    return fallback


def _first_difference(want: str, have: str) -> str:
    want_lines, have_lines = want.splitlines(), have.splitlines()
    for index in range(max(len(want_lines), len(have_lines))):
        left = want_lines[index] if index < len(want_lines) else "<missing>"
        right = have_lines[index] if index < len(have_lines) else "<missing>"
        if left != right:
            return ("DRIFT at line %d\n  source: %s\n  vendored: %s"
                    % (index + 1, left, right))
    return "DRIFT with no differing line (should be unreachable)"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero if a vendored copy has drifted")
    parser.add_argument("--pulled", default=None,
                        help="date stamp for the headers (default: today)")
    args = parser.parse_args(argv)

    today = date.today().isoformat()
    if args.pulled is not None:
        pulled_curve = pulled_rows = args.pulled
    elif args.check:
        # Reuse each file's own stamp so --check compares CONTENT, not dates.
        pulled_curve = _pulled_of(CURVE_TARGET, today)
        pulled_rows = _pulled_of(ROWS_TARGET, today)
    else:
        pulled_curve = pulled_rows = today

    try:
        curve_text, rows_text = build(pulled_curve, pulled_rows)
    except SourceMissing as exc:
        print("INCONCLUSIVE: %s" % exc)
        print("         Nothing was compared.  This is not a drift report.")
        return 2

    pairs = ((CURVE_TARGET, curve_text, CURVE_SOURCE_RELPATH),
             (ROWS_TARGET, rows_text, ROWS_SOURCE_RELPATH))
    if args.check:
        drifted = False
        for target, rendered, source_relpath in pairs:
            current = (target.read_text(encoding="ascii")
                       if target.exists() else "")
            if rendered == current:
                print("OK: %s matches %s" % (target.name, source_relpath))
            else:
                print("%s: %s" % (target.name, _first_difference(rendered, current)))
                drifted = True
        return 1 if drifted else 0

    for target, rendered, _source_relpath in pairs:
        target.write_text(rendered, encoding="ascii", newline="\n")
        body = [line for line in rendered.splitlines()
                if not line.startswith("#")]
        print("wrote %s (%d rows)" % (target, len(body) - 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
