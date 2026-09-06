#!/usr/bin/env python3
"""UI wire-name coverage census - PANYA `2032` job 2 / COO-DECISION
`pf_bridge/notes_to_chief/20260906_2047_COO-DECISION-panya2032-job2-ui-wire-coverage-bar-after-captain-frame-LANE-UI.md`.

WHAT QUESTION THIS ANSWERS
--------------------------
"Of the 327 Vital wire names in
``pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv``, how many does
this server already touch in real code, how many are known by name only (in
one of the project's own registries/docs) and how many has nobody looked at
yet?" -- the "n/327" number PANYA asked for on the encyclopedia page, grouped
by family and split out `...Req` client-request names.

WHAT "SOURCE" MEANS HERE, AND WHAT IT DOES NOT MEAN
----------------------------------------------------
A name is tier ``SOURCE`` when its exact identifier appears on a non-comment
line of a Python file under ``src/pirateforce_foundation/`` (any lane's, not
just UI's -- the official n/327 is a whole-project number, not a per-lane
one, per the COO-DECISION above quoting ka1-A's own 69/327 as "not the
official count"). This is presence-in-code, found the same mechanical way
`AGENTS.md` section 7 requires before writing the word "wired": a name in
this tier is NOT thereby claimed WIRED (`COO-DECISION 20260905_0947`) --
that word needs a mutation test, a single-writer guard and an observed round
trip, none of which this census runs. Read ``docs/UI_WIRE_COVERAGE.md`` for
the tier definitions this tool prints; do not read "SOURCE" as "done".

Skipping full-line comments removes the one false positive found by
pf-adversary on round `9dezrf`'s first draft (`VitalData` was SOURCE only
because of a comment in `app.py` reusing the name as generic prose for an
unrelated memory-layout concept, with no real reference anywhere else in the
tree) -- it does NOT catch a name mentioned only inside a trailing inline
comment or a docstring body; those remain a known, disclosed gap.

TIERS
-----
  SOURCE     the identifier appears in a `.py` file under
             `src/pirateforce_foundation/` -- evidence = `path:line` of the
             first hit.
  NAME-ONLY  not in SOURCE, but the identifier appears in at least one of the
             project's three function-map files (`prompts/COMMON_LANE_ROUND.md`
             section "แผนที่โปรโตคอลของเกม"): `docs/PF_VITAL_NAMES.json`
             (admitted names table, this repo), `pf_bridge/external/
             PF_PROTOCOL_REGISTRY.tsv` (serializer/handler VA table) or
             `pf_bridge/external/PF_SERIALIZER_FIELDS.tsv` (proven wire
             layouts), or in this repo's own `docs/UI_LANE.md` function
             table -- evidence names which source(s).
  UNTOUCHED  neither -- the only place the name exists is the master catalog
             row itself.

Usage:
    python3 tools/pf_ui_wire_name_census.py [--emit] [--tsv PATH]
      (no flag)   re-derive the census and compare it against the committed
                  artifact (reports/PF_UI_WIRE_NAME_CENSUS_20260906.tsv);
                  nonzero exit + a diff-shaped message on any drift.
      --emit      (re)write the artifact, then run the same comparison
                  (always equal right after --emit; kept for symmetry with
                  the project's other census tools).
      --summary   print the family/tier counts table to stdout and exit 0
                  (does not touch the artifact).

Pure stdlib. No side effects on import.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT.parent / "pf_bridge"
DEFAULT_TSV = BRIDGE / "VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv"
PROTOCOL_REGISTRY = BRIDGE / "external" / "PF_PROTOCOL_REGISTRY.tsv"
SERIALIZER_FIELDS = BRIDGE / "external" / "PF_SERIALIZER_FIELDS.tsv"
VITAL_NAMES_JSON = ROOT / "docs" / "PF_VITAL_NAMES.json"
UI_LANE_DOC = ROOT / "docs" / "UI_LANE.md"
SRC_DIR = ROOT / "src" / "pirateforce_foundation"
DEFAULT_ARTIFACT = ROOT / "reports" / "PF_UI_WIRE_NAME_CENSUS_20260906.tsv"

ARTIFACT_HEADER = "id\tname\tfamily\tis_client_req\ttier\tevidence"


class CensusError(Exception):
    """Raised when an input file is missing or malformed."""


def load_names(tsv_path: Path = DEFAULT_TSV):
    """Return the ``[(id_hex, name)]`` rows of the master catalog, in file order."""
    if not tsv_path.exists():
        raise CensusError(
            f"{tsv_path} not found -- this tool needs a sibling pf_bridge "
            "checkout next to the server repo (see tools/pf_vital_names.py "
            "DEFAULT_TSV for the same layout assumption)"
        )
    rows = []
    for line in tsv_path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        wid, name = parts[0].strip(), parts[1].strip()
        if wid and name:
            rows.append((wid, name))
    return rows


def family_of(name: str) -> str:
    if "_" in name:
        return name.split("_", 1)[0] + "_"
    return "(unprefixed)"


def _iter_py_files(base: Path):
    if not base.exists():
        return []
    return sorted(p for p in base.rglob("*.py") if p.is_file())


_PASCAL_TOKEN = re.compile(r"[A-Z][a-z0-9]*|[A-Z]+(?![a-z])|[a-z0-9]+")


def is_client_req(name: str) -> bool:
    """True when ``name`` contains ``Req`` as its own PascalCase word --
    matches both wire-naming conventions the master catalog actually uses
    (`...VitalReq` and `...ReqVital[_REGION]`, e.g. `CTracePathReqVital`,
    confirmed client-inbound by this repo's own trace_path.py comment) --
    without also matching an unrelated English word that merely starts the
    same way (`Community_RequestBeFriendVital` tokenizes to `Request`, not
    `Req`, so it is correctly NOT flagged)."""
    return "Req" in _PASCAL_TOKEN.findall(name)


def _build_source_hits(names, py_files):
    """One pass over every file in ``py_files`` (sorted, so deterministic):
    for every identifier token on a non-comment line, record the FIRST
    ``"relpath:line"`` it is seen at, for every name in ``names`` that is
    still unresolved. Full-line comments (``line.lstrip().startswith("#")``)
    are skipped so a name used only as this codebase's own descriptive
    prose (e.g. a comment reusing a wire name as a generic term) is not
    counted as a code reference; this does not catch a name mentioned only
    in a trailing inline comment or inside a docstring body -- see
    docs/UI_WIRE_COVERAGE.md's non-claims."""
    remaining = set(names)
    hits: dict = {}
    for path in py_files:
        if not remaining:
            break
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        relpath = path.relative_to(ROOT)
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not remaining:
                break
            if line.lstrip().startswith("#"):
                continue
            for token in _IDENT_TOKEN.findall(line):
                if token in remaining:
                    hits[token] = f"{relpath}:{lineno}"
                    remaining.discard(token)
    return hits


def _load_admitted_names(path: Path = VITAL_NAMES_JSON):
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {entry.get("name") for entry in data.get("entries", []) if entry.get("name")}


def _load_plain_name_set(path: Path, pattern: "re.Pattern[str]"):
    if not path.exists():
        return set()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    return set(pattern.findall(text))


_IDENT_TOKEN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


def _load_name_only_sources():
    """Return ``{name: [source_label, ...]}`` for every identifier-shaped
    token found in the project's three function-map files plus this repo's
    UI function table -- the "known by name" evidence pool."""
    hits: dict = {}

    def add(names, label):
        for n in names:
            hits.setdefault(n, []).append(label)

    add(_load_admitted_names(), "docs/PF_VITAL_NAMES.json")
    add(
        _load_plain_name_set(PROTOCOL_REGISTRY, _IDENT_TOKEN),
        "pf_bridge/external/PF_PROTOCOL_REGISTRY.tsv",
    )
    add(
        _load_plain_name_set(SERIALIZER_FIELDS, _IDENT_TOKEN),
        "pf_bridge/external/PF_SERIALIZER_FIELDS.tsv",
    )
    add(_load_plain_name_set(UI_LANE_DOC, _IDENT_TOKEN), "docs/UI_LANE.md")
    return hits


_CENSUS_INPUT_CACHE: dict = {}


def _census_inputs(tsv_path: Path):
    """Compute (once per ``tsv_path``, cached for the life of the process --
    every input here is a file this tool itself does not write, so nothing
    inside one run of this process can invalidate it) the two expensive,
    call-independent pieces build_rows() needs: the per-name SOURCE hit
    index and the NAME-ONLY registry pool. Re-derive_rows below still runs
    the tier decision fresh from these every call, so this cache changes
    speed, not what gets computed."""
    cache_key = str(tsv_path)
    cached = _CENSUS_INPUT_CACHE.get(cache_key)
    if cached is None:
        names = load_names(tsv_path)
        py_files = _iter_py_files(SRC_DIR)
        source_hits = _build_source_hits({n for _, n in names}, py_files)
        name_only_sources = _load_name_only_sources()
        cached = (names, source_hits, name_only_sources)
        _CENSUS_INPUT_CACHE[cache_key] = cached
    return cached


def build_rows(tsv_path: Path = DEFAULT_TSV):
    names, source_hits, name_only_sources = _census_inputs(tsv_path)
    rows = []
    for wid, name in names:
        hit = source_hits.get(name)
        if hit:
            tier, evidence = "SOURCE", hit
        else:
            sources = name_only_sources.get(name)
            if sources:
                tier, evidence = "NAME-ONLY", "+".join(sources)
            else:
                tier, evidence = "UNTOUCHED", "-"
        rows.append(
            {
                "id": wid,
                "name": name,
                "family": family_of(name),
                "is_client_req": "1" if is_client_req(name) else "0",
                "tier": tier,
                "evidence": evidence,
            }
        )
    return rows


def render_tsv(rows) -> str:
    lines = [ARTIFACT_HEADER]
    for row in rows:
        lines.append(
            "\t".join(
                (
                    row["id"],
                    row["name"],
                    row["family"],
                    row["is_client_req"],
                    row["tier"],
                    row["evidence"],
                )
            )
        )
    return "\n".join(lines) + "\n"


def parse_tsv(text: str):
    lines = text.splitlines()
    if not lines or lines[0] != ARTIFACT_HEADER:
        raise CensusError(f"artifact header mismatch: {lines[0] if lines else '(empty)'}")
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        wid, name, family, is_req, tier, evidence = line.split("\t", 5)
        rows.append(
            {
                "id": wid,
                "name": name,
                "family": family,
                "is_client_req": is_req,
                "tier": tier,
                "evidence": evidence,
            }
        )
    return rows


def summarize(rows):
    total = len(rows)
    by_tier = {"SOURCE": 0, "NAME-ONLY": 0, "UNTOUCHED": 0}
    by_family: dict = {}
    for row in rows:
        by_tier[row["tier"]] += 1
        fam = by_family.setdefault(row["family"], {"SOURCE": 0, "NAME-ONLY": 0, "UNTOUCHED": 0})
        fam[row["tier"]] += 1
    return total, by_tier, by_family


def _print_summary(rows) -> None:
    total, by_tier, by_family = summarize(rows)
    print(f"n/327 known (SOURCE) = {by_tier['SOURCE']}/{total}")
    print(f"  NAME-ONLY = {by_tier['NAME-ONLY']}  UNTOUCHED = {by_tier['UNTOUCHED']}")
    for fam in sorted(by_family):
        counts = by_family[fam]
        fam_total = sum(counts.values())
        print(
            f"  {fam:<24} {counts['SOURCE']:>3} SOURCE  "
            f"{counts['NAME-ONLY']:>3} NAME-ONLY  "
            f"{counts['UNTOUCHED']:>3} UNTOUCHED  (of {fam_total})"
        )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tsv", type=Path, default=DEFAULT_TSV)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--emit", action="store_true")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)

    try:
        rows = build_rows(args.tsv)
    except CensusError as exc:
        print(f"CENSUS ERROR: {exc}", file=sys.stderr)
        return 2

    if args.summary:
        _print_summary(rows)
        return 0

    rendered = render_tsv(rows)
    if args.emit:
        args.artifact.write_text(rendered, encoding="utf-8")

    if not args.artifact.exists():
        print(f"CENSUS DRIFT: artifact {args.artifact} does not exist (run with --emit)", file=sys.stderr)
        return 1

    committed = args.artifact.read_text(encoding="utf-8")
    if committed != rendered:
        print(
            f"CENSUS DRIFT: {args.artifact} does not match a fresh re-derive "
            "-- rerun with --emit and commit the new artifact",
            file=sys.stderr,
        )
        return 1

    _print_summary(rows)
    print("PASS -- committed artifact matches a fresh re-derive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
