"""Regenerate lua_api/quest_var_{rows,signedness}.tsv from the game's data.

LANE-Q, COO-DECISION ``20260908_0042`` item 5 (option "kho").  Two vendored
files, one command, the same shape and the same reasons as
``tools/pf_regen_lua_quest_criteria.py``:

  * ``quest_var_rows.tsv``       <- ``QUESTDATA_TH__QUEST.tsv``
    1544 quests x the 20 ``n_VARI_k`` cells, copied VERBATIM as the
    unsigned 32-bit decimals the table stores.  No interpretation.

  * ``quest_var_signedness.tsv`` <- the SAME table, cross-read against the
    Lua corpus in ``pf_bridge/gamedata/lua/``.  Which (script, column)
    pairs hold a signed quantity, and the ``file:line`` that proves it.

HOW THE SECOND FILE IS DERIVED, in full, because a table nobody can
re-derive is a guess with a header:

  1. every cell at or above ``2**31`` is a candidate -- the table has no
     signed type, so a designer's ``-15000`` is stored as ``4294952296``;
  2. candidates are grouped by (``s_LUASCRIPT``, ``k``), because the
     column's MEANING belongs to the script that reads it, not to the row;
  3. for each group the corpus file the script names is opened and the
     line reading ``Quest.Var<k>`` is located -- that line, verbatim, is
     the provenance;
  4. the ``kind`` comes from the API this lane already implements at that
     line: ``Player.AddCash`` -> ``signed_money``, ``Player.CastSkillXYZ``
     -> ``signed_coordinate``.

Step 4 is the ONLY step with a lane-authored mapping in it, it is four
lines long (:data:`KIND_BY_API`), and a call site whose API is not in it
STOPS THE TOOL rather than being filed under a default.  A new signed
column has to be looked at by a person; that is the whole point.

THE CORPUS IS READ AS BYTES, NEVER DECODED.  ``q_kill_skxyz.lua`` carries
Big5 comment bytes on lines 11-13, right above the call site this tool has
to find, and ``str`` decoding them would raise ``UnicodeDecodeError`` on
exactly the file the signedness table most needs (pf-adversary D12, round
``yfeauz``).  Matching is done on ``bytes`` patterns and only the ASCII
subset of a matched line is ever rendered into the output.

    python3 tools/pf_regen_lua_quest_vars.py            # rewrite both
    python3 tools/pf_regen_lua_quest_vars.py --check    # drift only
    python3 tools/pf_regen_lua_quest_vars.py --explain  # show the scan

``--check`` exits 0 when both copies match the source, 1 when one has
drifted, and 2 -- INCONCLUSIVE, not a drift report -- when there is no
``pf_bridge`` checkout beside this repository, which is the case on the
Windows gate.  The digest header is what the gate CAN check, and does, in
``tests/test_script_lua_quest_vars.py``.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.lua_api.quest_criteria import (  # noqa: E402
    BODY_DIGEST_PREFIX, body_digest,
)
from pirateforce_foundation.lua_api.quest_vars import (  # noqa: E402
    KIND_COORDINATE, KIND_MONEY, ROW_COLUMNS, SIGNEDNESS_COLUMNS, VAR_COUNT,
    WRAPPED_SCAN_THRESHOLD,
)

BRIDGE = ROOT.parent / "pf_bridge"
SOURCE_RELPATH = "gamedata/tables/QUESTDATA_TH__QUEST.tsv"
CORPUS_RELPATH = "gamedata/lua"

LUA_API = ROOT / "src" / "pirateforce_foundation" / "lua_api"
ROWS_TARGET = LUA_API / "quest_var_rows.tsv"
SIGNEDNESS_TARGET = LUA_API / "quest_var_signedness.tsv"

#: The only lane-authored step in the derivation: what KIND of signed
#: quantity each API that consumes a signed VarN takes.  Both entries are
#: read off the call site itself, not assumed -- ``AddCash`` is this lane's
#: own money door (``lua_api.player``), ``CastSkillXYZ``'s three trailing
#: arguments are named X/Y/Z by the script's own comment lines.  An
#: unlisted API is a HARD STOP, see :func:`kind_for_api`.
KIND_BY_API = {
    # api -> {0-based argument position: kind}.  POSITION, not just the
    # api name: `q_kill_skxyz.lua:85` is
    #     Player.CastSkillXYZ(Quest.Var9, Quest.Var10, Quest.Var11, Quest.Var12)
    # where Var9 is a SKILL ID sharing the line with three coordinates.
    # Matching on "the api name appears somewhere in this line" would file
    # a wrapped id as a signed coordinate and hand the game a negative id,
    # which is precisely the `n_VARI_13 = mob id` case ASK-COO `0015`
    # raised as the reason a table has to exist at all (pf-adversary D3,
    # round `joa0u6`).
    "Player.AddCash": {0: KIND_MONEY},
    "Player.CastSkillXYZ": {1: KIND_COORDINATE, 2: KIND_COORDINATE,
                            3: KIND_COORDINATE},
}


class SourceMissing(Exception):
    """No bridge checkout beside this repo.  Distinct from "drifted"."""


class UnclassifiedColumn(Exception):
    """A wrapped column whose call site uses an API nobody has classified."""


def read_rows(path: Path):
    """``[(quest_id, script, (var1..var20))]`` in table order."""
    rows = []
    with path.open(encoding="utf-8", newline="", errors="strict") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            cells = tuple(int(row["n_VARI_%d" % index])
                          for index in range(1, VAR_COUNT + 1))
            rows.append((int(row["n_ID"]), row["s_LUASCRIPT"].strip(), cells))
    return rows


def corpus_file_for(corpus: Path, script: str):
    """The one ``.lua`` file a ``s_LUASCRIPT`` name dispatches, or ``None``.

    Case-insensitive by basename over the whole corpus rather than a
    lowercase path guess: the shipped tree mixes ``Quest/q_class.lua`` with
    ``t_*.lua`` at other depths, and a name that matches two files is
    returned as ``None`` -- ambiguous, so a person looks -- instead of
    whichever one the walk happened to reach first.
    """
    wanted = "%s.lua" % script.strip().lower()
    hits = [path for path in sorted(corpus.rglob("*.lua"))
            if path.name.lower() == wanted]
    return hits[0] if len(hits) == 1 else None


def _arguments_at(line: bytes, api: bytes, start: int):
    """The argument list of the ``api(...)`` that starts at ``start``.

    ``None`` when the parentheses do not close on this line.  Splitting at
    depth 0 means a nested call counts as ONE argument, which is what an
    argument POSITION has to mean.
    """
    index = start + len(api) + 1
    depth = 1
    current = bytearray()
    args = []
    while index < len(line):
        byte = line[index:index + 1]
        if byte == b"(":
            depth += 1
        elif byte == b")":
            depth -= 1
            if depth == 0:
                args.append(bytes(current))
                return args
        if depth == 1 and byte == b",":
            args.append(bytes(current))
            current = bytearray()
        else:
            current += byte
        index += 1
    return None


def argument_lists_of(line: bytes, api: bytes):
    """EVERY ``api(...)`` on ``line``, as a list of argument lists.

    WHY THIS EXISTS, AND WHY :func:`arguments_of` IS NOW A WRAPPER ROUND
    IT (pf-adversary D3, round ``yzdgx1``).  The one-call form used
    ``line.find`` once, so a second call to the same API on the same line
    WAS INVISIBLE -- and invisible in the direction that costs a player
    money: two ``Player.AddCash(...)`` calls on one line would have had
    the second charge read by nothing, the scan still green and
    ``--check`` still clean.  MEASURED over all 616 corpus files today: no
    line holds two calls to any API either scanner reads (``AddCash`` has
    6 call sites, one per line), so this closes a hole rather than
    changing a mirror -- which is the point at which to close it.

    A call whose parentheses run off the end of the line is skipped rather
    than ending the scan: the next call on the same line is still real.
    """
    found = []
    start = line.find(api + b"(")
    while start >= 0:
        args = _arguments_at(line, api, start)
        if args is not None:
            found.append(args)
        start = line.find(api + b"(", start + len(api) + 1)
    return found


def arguments_of(line: bytes, api: bytes):
    """The argument list of the FIRST ``api(...)`` on ``line``, or ``None``.

    Kept for the callers that genuinely want one call; anything that scans
    for call SITES wants :func:`argument_lists_of` instead.
    """
    lists = argument_lists_of(line, api)
    return lists[0] if lists else None


#: A ``VarN`` whose value the SCRIPT itself negates before handing it over.
#: `q_boat_health.lua:21` is ``Player.AddCash(Quest.Var2 * -1)`` and
#: `q_ship.lua:50` is ``Player.AddCash(-Quest.Var3)``: the sign lives in
#: the EXPRESSION, so decoding the cell as signed too would flip it twice
#: and pay the player for repairing their own boat (pf-adversary D4, round
#: `joa0u6`).  Any argument that is not the bare read is refused -- an
#: allow-list of one shape, not a blocklist of the two seen today.
_BARE_READ = re.compile(rb"^\s*Quest\.Var%d\s*$")


def call_site_for(path: Path, var_index: int):
    """``(line_number, api_name, ascii_text)`` for the line reading VarN.

    Bytes in, bytes matched, ASCII out.  ``Quest.Var1`` must not match
    ``Quest.Var10``, so the pattern refuses a trailing digit.
    """
    pattern = re.compile(rb"Quest\.Var%d(?![0-9])" % var_index)
    bare = re.compile(_BARE_READ.pattern % var_index)
    data = path.read_bytes()
    first = None
    for number, line in enumerate(data.split(b"\n"), start=1):
        if not pattern.search(line):
            continue
        text = line.decode("ascii", "replace").rstrip("\r").strip()
        if first is None:
            first = (number, None, text)
        for api in sorted(KIND_BY_API):
            for args in argument_lists_of(line, api.encode("ascii")):
                # EVERY call on the line, not just the first (pf-adversary
                # D3, round `yzdgx1`): the second call to the same API on
                # one line used to be invisible to this scan.
                for position, argument in enumerate(args):
                    if not bare.match(argument):
                        continue
                    # ALWAYS position-qualified, valid position or not, so
                    # `kind_for_api` resolves the kind by POSITION and a
                    # bad position refuses by name instead of the scan
                    # moving on to another api and guessing.
                    return number, "%s@arg%d" % (api, position), text
    # No line passes the name to a classified API as a bare read.  Report
    # the FIRST read anyway, with no API, so the caller raises a failure
    # that names the line a person has to go and look at.
    #
    # THE FIRST READ IS OFTEN NOT THE CALL.  `q_kill_skxyz.lua` opens with
    # a designer's key -- `Quest.Var10=<X coordinate>` in Big5 bytes on
    # line 11 -- three lines before anything executes, and the executable
    # read is line 85.  Preferring the classified line over the first one
    # is what makes the provenance column point at code instead of at a
    # comment; the comment is real evidence too, but it is evidence a
    # PERSON reads, not a file:line this tool should pin.
    return first


def kind_for_api(script: str, var_index: int, api):
    """The kind, or a HARD STOP naming what a person has to go and read."""
    positions = None
    if api is not None and "@arg" in api:
        name, _, position = api.partition("@arg")
        positions = KIND_BY_API.get(name)
        if positions is not None and int(position) in positions:
            return positions[int(position)]
    raise UnclassifiedColumn(
        "%s n_VARI_%d holds a wrapped (negative) value but its call site is "
        "%s: not a bare `Quest.Var%d` at a signed argument position of an "
        "API in KIND_BY_API. That covers three different things a person has "
        "to tell apart -- an unlisted API, an argument position that API "
        "does not treat as signed (an id beside a coordinate), and a read "
        "the SCRIPT already negates itself (`Quest.Var2 * -1`), which would "
        "flip the sign twice. This tool will not guess between them."
        % (script, var_index, api or "no classified API", var_index))


def scan_signedness(rows, corpus: Path):
    """``[(script, var_index, kind, api, call_site, ids, raws)]`` ascending."""
    groups = {}
    for quest_id, script, cells in rows:
        for index in range(1, VAR_COUNT + 1):
            raw = cells[index - 1]
            if raw < WRAPPED_SCAN_THRESHOLD:
                continue
            groups.setdefault((script, index), []).append((quest_id, raw))

    derived = []
    for (script, index), evidence in sorted(groups.items()):
        path = corpus_file_for(corpus, script)
        if path is None:
            raise UnclassifiedColumn(
                "%s n_VARI_%d is wrapped but no single corpus file matches "
                "the script name" % (script, index))
        found = call_site_for(path, index)
        if found is None:
            raise UnclassifiedColumn(
                "%s n_VARI_%d is wrapped but %s never reads Quest.Var%d"
                % (script, index, path.name, index))
        line_number, api, _text = found
        kind = kind_for_api(script, index, api)
        # The mirror records the API NAME; the position is how the kind was
        # decided, not a fact about the column, and a reader who wants it
        # opens call_site.
        api = api.partition("@arg")[0]
        relative = path.relative_to(corpus).as_posix()
        derived.append((
            script, index, kind, api, "%s:%d" % (relative, line_number),
            tuple(quest_id for quest_id, _raw in evidence),
            tuple(raw for _quest_id, raw in evidence),
        ))
    return derived


def _header(regenerate: str, source_note: str, source_sha256: str,
            count: int, pulled: str, rendered_body: str, note: str) -> str:
    lines = [
        "# VENDORED MIRROR -- do not hand-edit.",
        "# regenerate: python3 tools/%s" % regenerate,
        "# source: %s" % source_note,
        "# source_sha256: %s" % source_sha256,
        "# source_rows: %d" % count,
        "# pulled: %s" % pulled,
        "%s%s" % (BODY_DIGEST_PREFIX, body_digest(rendered_body)),
        "# %s" % note,
    ]
    return "\n".join(lines) + "\n"


TOOL = Path(__file__).name


def render_rows(rows, digest: str, pulled: str) -> str:
    body = ["\t".join(ROW_COLUMNS)]
    for quest_id, _script, cells in rows:
        body.append("%d\t%s" % (quest_id,
                                "\t".join("%d" % cell for cell in cells)))
    rendered = "\n".join(body) + "\n"
    return _header(
        TOOL, "pf_bridge/%s" % SOURCE_RELPATH, digest, len(rows), pulled,
        rendered,
        "n_VARI_1..n_VARI_20 verbatim, as the unsigned 32-bit decimals the "
        "source stores; a value at or above 2147483648 is a negative held "
        "in two's complement and is decoded ONLY for the columns "
        "quest_var_signedness.tsv names.") + rendered


def render_signedness(derived, digest: str, pulled: str) -> str:
    body = ["\t".join(SIGNEDNESS_COLUMNS)]
    for script, index, kind, api, call_site, ids, raws in derived:
        body.append("%s\t%d\t%s\t%s\t%s\t%s\t%s"
                    % (script, index, kind, api, call_site,
                       ",".join("%d" % value for value in ids),
                       ",".join("%d" % value for value in raws)))
    rendered = "\n".join(body) + "\n"
    return _header(
        TOOL,
        "pf_bridge/%s cross-read against pf_bridge/%s"
        % (SOURCE_RELPATH, CORPUS_RELPATH),
        digest, len(derived), pulled, rendered,
        "one row per (script, n_VARI_k) that holds a signed quantity; "
        "call_site is the corpus line that proves it, evidence_quest_ids/"
        "evidence_raw are the source rows exhibiting the wrapped value.") \
        + rendered


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(pulled_rows: str, pulled_signedness: str):
    source = BRIDGE / SOURCE_RELPATH
    corpus = BRIDGE / CORPUS_RELPATH
    missing = [str(p) for p in (source, corpus) if not p.exists()]
    if missing:
        raise SourceMissing(
            "source not found: %s (this script needs a pf_bridge checkout "
            "beside this repository)" % ", ".join(missing))
    rows = read_rows(source)
    digest = _digest(source)
    return (render_rows(rows, digest, pulled_rows),
            render_signedness(scan_signedness(rows, corpus), digest,
                              pulled_signedness))


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


def explain() -> int:
    """Print the scan, so a reader can check the derivation by eye."""
    source = BRIDGE / SOURCE_RELPATH
    corpus = BRIDGE / CORPUS_RELPATH
    if not source.exists() or not corpus.exists():
        print("INCONCLUSIVE: no pf_bridge checkout beside this repository")
        return 2
    rows = read_rows(source)
    cells = [cell for _q, _s, group in rows for cell in group]
    ordinary = [cell for cell in cells if cell < WRAPPED_SCAN_THRESHOLD]
    wrapped = [cell for cell in cells if cell >= WRAPPED_SCAN_THRESHOLD]
    print("cells=%d rows=%d ordinary_max=%d wrapped_min=%d wrapped=%d"
          % (len(cells), len(rows), max(ordinary), min(wrapped), len(wrapped)))
    for script, index, kind, api, call_site, ids, raws in scan_signedness(
            rows, corpus):
        print("%-16s n_VARI_%-2d %-18s %-22s %s ids=%s signed=%s"
              % (script, index, kind, api, call_site,
                 ",".join("%d" % value for value in ids),
                 ",".join("%d" % (value - (1 << 32)) for value in raws)))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero if a vendored copy has drifted")
    parser.add_argument("--explain", action="store_true",
                        help="print the scan behind quest_var_signedness.tsv")
    parser.add_argument("--pulled", default=None,
                        help="date stamp for the headers (default: today)")
    args = parser.parse_args(argv)

    if args.explain:
        try:
            return explain()
        except UnclassifiedColumn as exc:
            print("STOP: %s" % exc)
            return 3

    today = date.today().isoformat()
    if args.pulled is not None:
        pulled_rows = pulled_signedness = args.pulled
    elif args.check:
        pulled_rows = _pulled_of(ROWS_TARGET, today)
        pulled_signedness = _pulled_of(SIGNEDNESS_TARGET, today)
    else:
        pulled_rows = pulled_signedness = today

    try:
        rows_text, signedness_text = build(pulled_rows, pulled_signedness)
    except SourceMissing as exc:
        print("INCONCLUSIVE: %s" % exc)
        print("         Nothing was compared.  This is not a drift report.")
        return 2
    except UnclassifiedColumn as exc:
        print("STOP: %s" % exc)
        return 3

    pairs = ((ROWS_TARGET, rows_text), (SIGNEDNESS_TARGET, signedness_text))
    if args.check:
        drifted = False
        for target, rendered in pairs:
            current = (target.read_text(encoding="ascii")
                       if target.exists() else "")
            if rendered == current:
                print("OK: %s matches %s" % (target.name, SOURCE_RELPATH))
            else:
                print("%s: %s" % (target.name,
                                  _first_difference(rendered, current)))
                drifted = True
        return 1 if drifted else 0

    for target, rendered in pairs:
        target.write_text(rendered, encoding="ascii", newline="\n")
        body = [line for line in rendered.splitlines()
                if not line.startswith("#")]
        print("wrote %s (%d rows)" % (target, len(body) - 1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
