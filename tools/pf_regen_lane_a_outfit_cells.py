#!/usr/bin/env python3
"""Rewrite the shipped ``s_OUTFIT`` column of LANE-A's crosswalk modules to
the RAW cell the client itself reads.

WHY THIS TOOL EXISTS.  Every ``world_bg*_identity`` module was mined under a
reading in which a MOBS row listing several avatar templates
(``'M006_000_001_SP1;M006_000_001_SP2'``) shipped only its FIRST token, and
each module's ``_self_check`` refused a ';' in the shipped column.  That
reading was tagged in the modules themselves as
``[LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION]``.  The confirmation
came back the other way:

    PANYA 1313 (owner):  s_OUTFIT does not decide who is an enemy.
    RE-296:              the client tokenises the cell ITSELF and keeps every
                         token, so the raw cell is what the client sees.
    COO-DECISION 2026-09-08 13:41 +07:00 (pf_bridge notes_to_chief/
    20260908_1341_COO-DECISION-b-regenerates-the-lane-a-outfit-table-under-
    1313-LANE-B.md): LANE-B regenerates these tables, LANE-A reviews.

WHAT IT CHANGES AND WHAT IT REFUSES TO CHANGE.  Exactly one column of one
tuple per row: the shipped outfit string.  Identity, name, title, level,
rank, HP, usage, the placement table, the UNRESOLVED map and every count in
``_self_check`` are left byte-for-byte alone, so a reviewer diffs one column.

THE CONTROL, RUN PER ROW BEFORE ANYTHING IS WRITTEN.  For every row the tool
touches, the value already committed must equal the FIRST token of the raw
MOBS cell.  That is the whole claim being made -- "the old table is the new
table truncated" -- and a row where it does not hold is a row the old miner
got wrong for some OTHER reason, which this tool must not paper over: it
refuses the whole file and names the row.  The MOBS table itself is checked
against the sha256 the module already pins in ``SOURCE_SHA256``, so a module
mined from a different extraction is refused rather than silently re-mined.

USAGE (the line that produced the committed diff):

    python3 tools/pf_regen_lane_a_outfit_cells.py \
        --bridge ../pf_bridge --outfit-rule any --all --write

``--outfit-rule unambiguous`` is accepted and does nothing but report, so
the old reading stays runnable and named rather than deleted.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import pathlib
import re
import sys


MOBS_TSV = "gamedata/tables/CONSTDATA_TH__MOBS.tsv"

def load_mobs_outfits(bridge: pathlib.Path) -> tuple[dict[int, str], str]:
    """Return ``{MOBS.n_ID: raw s_OUTFIT cell}`` and the file's sha256."""
    path = bridge / MOBS_TSV
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8-sig", errors="strict")
    lines = text.splitlines()
    header = lines[0].split("\t")
    n_id_col = header.index("n_ID")
    outfit_col = header.index("s_OUTFIT")
    outfits: dict[int, str] = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) <= max(n_id_col, outfit_col):
            continue
        try:
            n_id = int(cells[n_id_col])
        except ValueError:
            continue
        outfits[n_id] = cells[outfit_col].strip()
    return outfits, digest


def pinned_mobs_sha(text: str) -> str | None:
    match = re.search(
        r"""['"]gamedata/tables/CONSTDATA_TH__MOBS\.tsv['"]:\s*\n?\s*"""
        r"""['"]([0-9a-f]{64})['"]""",
        text,
    )
    return match.group(1) if match else None


class Refusal(RuntimeError):
    """The tool will not write this file, and says which row stopped it."""


class Opaque:
    """A column this tool cannot read as a value, and does not need to.

    The instance-scene modules build a display name as
    ``_cp874(NAME_CP874_HEX[56])``: a real string at import, no string
    literal on the line.  Only the outfit column has to be readable, so
    every other column is allowed to be one of these.
    """

    def __repr__(self) -> str:
        return "<opaque column>"


def row_value(node: ast.AST):
    """One column of a row, as a value, or ``Opaque`` when it is not one."""
    if isinstance(node, ast.Constant):
        return node.value
    return Opaque()


def parse_row(chunk: str):
    """Parse one row chunk into (values, element nodes), or None."""
    try:
        expr = ast.parse(chunk.strip().rstrip().rstrip(","), mode="eval").body
    except SyntaxError:
        return None
    if not isinstance(expr, ast.Tuple):
        return None
    return tuple(row_value(e) for e in expr.elts), expr.elts


def literal_span(chunk: str, node: ast.Constant) -> tuple[int, int]:
    """Byte span of a string literal inside the chunk it was parsed from.

    ``ast`` positions are relative to the text handed to ``ast.parse``,
    which is ``chunk`` stripped of its leading whitespace; the offset of
    that strip is added back here.  Using the parser's own positions is
    what keeps this tool from having to GUESS which quoted run on the line
    is the outfit -- the failure mode that would silently rewrite a display
    name instead.
    """
    lead = len(chunk) - len(chunk.lstrip())
    body = chunk[lead:]
    lines = body.splitlines(keepends=True)
    starts = []
    running = 0
    for line in lines:
        starts.append(running)
        running += len(line)
    begin = starts[node.lineno - 1] + node.col_offset
    finish = starts[node.end_lineno - 1] + node.end_col_offset
    return lead + begin, lead + finish


def row_field_names(text: str) -> list[str]:
    """Field order of the dataclass each row is splatted into.

    The modules all build their rows with ``SceneIdentity(*row)``, so the
    dataclass's field ORDER is the row's column order.  Reading it here is
    what lets one tool serve four different row shapes without a per-scene
    table of column numbers to get wrong.
    """
    tree = ast.parse(text)
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(
                (isinstance(d, ast.Name) and d.id == "dataclass")
                or (isinstance(d, ast.Call) and isinstance(d.func, ast.Name)
                    and d.func.id == "dataclass")
                for d in node.decorator_list):
            continue
        fields = [b.target.id for b in node.body
                  if isinstance(b, ast.AnnAssign)
                  and isinstance(b.target, ast.Name)]
        if "outfit" in fields:
            return fields
    raise Refusal("no dataclass with an 'outfit' field")


def rewrite_module(path: pathlib.Path, outfits: dict[int, str],
                   mobs_sha: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Return the new text and the rows whose outfit cell changed."""
    text = path.read_text(encoding="utf-8")
    pinned = pinned_mobs_sha(text)
    if pinned is None:
        raise Refusal("%s pins no MOBS sha256" % path.name)
    if pinned != mobs_sha:
        raise Refusal(
            "%s was mined from a different MOBS extraction (pins %s, bridge "
            "has %s)" % (path.name, pinned[:12], mobs_sha[:12]))

    fields = row_field_names(text)
    outfit_at = fields.index("outfit")
    if "mobs_n_id" not in fields:
        raise Refusal("%s rows carry no mobs_n_id column" % path.name)
    n_id_at = fields.index("mobs_n_id")

    start = text.index("_RESOLVED_ROWS = (")
    end = text.index("\n)\n", start) + len("\n)\n")
    block = text[start:end]

    changed: list[tuple[int, str, str]] = []
    seen_rows = 0
    out_chunks: list[str] = []
    lines = block.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip().startswith("("):
            out_chunks.append(line)
            index += 1
            continue
        # A row may WRAP (bg1001 puts the numeric tail on a second line), so
        # take lines until the tuple parses.  A row that never parses is a
        # refusal, not a row to skip quietly.
        chunk = ""
        row = None
        for take in range(index, min(index + 6, len(lines))):
            chunk += lines[take]
            parsed = parse_row(chunk)
            if parsed is None:
                continue
            row, row_nodes = parsed
            index = take + 1
            break
        if row is None:
            raise Refusal(
                "%s: a row of _RESOLVED_ROWS starting %r does not parse"
                % (path.name, line.strip()[:40]))
        if len(row) != len(fields):
            raise Refusal(
                "%s has a row of %d values where the dataclass declares %d: "
                "%r" % (path.name, len(row) if isinstance(row, tuple) else -1,
                        len(fields), row))
        seen_rows += 1
        n_id = row[n_id_at]
        shipped = row[outfit_at]
        raw = outfits.get(n_id)
        if raw is None:
            raise Refusal(
                "%s row MOBS n_ID %r has no row in MOBS at all"
                % (path.name, n_id))
        if raw == shipped:
            out_chunks.append(chunk)
            continue
        if raw.split(";")[0] != shipped:
            raise Refusal(
                "%s row MOBS n_ID %d ships %r, which is NOT the first token "
                "of the raw cell %r -- the old table differs from the new one "
                "by something other than truncation, so this tool refuses the "
                "whole file" % (path.name, n_id, shipped, raw))
        if "'" in raw or '"' in raw or not raw.isascii():
            raise Refusal(
                "%s row MOBS n_ID %d has a raw cell that cannot be written as "
                "an ASCII single-quoted literal: %r" % (path.name, n_id, raw))
        node = row_nodes[outfit_at]
        if not isinstance(node, ast.Constant) or not isinstance(
                node.value, str):
            raise Refusal(
                "%s row MOBS n_ID %d does not carry its outfit as a string "
                "literal" % (path.name, n_id))
        begin, finish = literal_span(chunk, node)
        old_literal = chunk[begin:finish]
        if old_literal[1:-1] != shipped:
            raise Refusal(
                "%s row MOBS n_ID %d: the outfit literal is not where the "
                "parser says it is (found %s)"
                % (path.name, n_id, old_literal))
        quote = old_literal[0]
        out_chunks.append(
            chunk[:begin] + quote + raw + quote + chunk[finish:])
        changed.append((n_id, shipped, raw))

    if seen_rows == 0:
        raise Refusal(
            "%s: no row of _RESOLVED_ROWS was recognised, so 'nothing to "
            "change' would be a lie" % path.name)

    return text[:start] + "".join(out_chunks) + text[end:], changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge", required=True,
                        help="path to the pf_bridge clone")
    parser.add_argument("--outfit-rule", choices=("any", "unambiguous"),
                        default="any")
    parser.add_argument("--module", action="append", default=[],
                        help="one identity module path (repeatable)")
    parser.add_argument("--all", action="store_true",
                        help="every world_*_identity module in the package")
    parser.add_argument("--write", action="store_true",
                        help="write the files; default is a dry run")
    args = parser.parse_args(argv)

    bridge = pathlib.Path(args.bridge)
    package = pathlib.Path(__file__).resolve().parent.parent / (
        "src/pirateforce_foundation")
    modules = [pathlib.Path(m) for m in args.module]
    if args.all:
        modules.extend(sorted(package.glob("world_*_identity.py")))
    if not modules:
        parser.error("nothing to do: pass --module or --all")

    outfits, mobs_sha = load_mobs_outfits(bridge)
    print("MOBS %s rows=%d sha256=%s" % (MOBS_TSV, len(outfits), mobs_sha))
    print("outfit rule: %s" % args.outfit_rule)
    if args.outfit_rule == "unambiguous":
        print("nothing to do: 'unambiguous' IS what the tree already ships")
        return 0

    total = 0
    refused: list[str] = []
    for path in modules:
        try:
            new_text, changed = rewrite_module(path, outfits, mobs_sha)
        except Refusal as exc:
            refused.append(str(exc))
            print("REFUSED %s" % exc)
            continue
        total += len(changed)
        print("%-44s rows rewritten: %d" % (path.name, len(changed)))
        for n_id, old, new in changed:
            print("    MOBS %-6d %s -> %s" % (n_id, old, new))
        if args.write and changed:
            path.write_text(new_text, encoding="utf-8")

    print("total rows rewritten: %d%s"
          % (total, "" if args.write else " (dry run, nothing written)"))
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
