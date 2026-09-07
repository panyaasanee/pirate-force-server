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
tree). Round `mg3nr4` added the second exclusion, docstring bodies, by AST
(COO-DECISION `pf_bridge/notes_to_chief/20260907_0546_COO-DECISION-q0454-
census-tool-skips-docstrings-LANE-UI.md`): a lane writing the honest note
"this module does NOT build `XxxVital`" used to push n/327 UP by one with
nothing wired. A name mentioned only inside a TRAILING INLINE comment is
still counted; that remains a known, disclosed gap.

TIERS
-----
  SOURCE     the identifier appears in a `.py` file under
             `src/pirateforce_foundation/` -- evidence = the `path` of the
             file holding the first hit. Deliberately NOT `path:line`: see
             `_build_source_hits` for the measurement that removed the line
             number, and `--where <name>` below to recover it. NOT grep --
             the same refuted recovery this file already warns about 27
             lines further down (pf-adversary D9 on `#1017` found this
             sixth copy of it after D-E on `#1013` had swept five).
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
    python3 tools/pf_ui_wire_name_census.py [--emit] [--tsv IN] [--artifact OUT]

    --tsv is the INPUT catalog (pf_bridge's 327-name registry, read only).
    --artifact is the OUTPUT artifact (this tool's own census file, which
    --emit OVERWRITES).  They are not interchangeable, and passing either
    file to the other flag is refused by name rather than half-obeyed --
    two lanes lost a round each to that swap on 2026-09-07.

      (no flag)   re-derive the census and compare it against the committed
                  artifact (reports/PF_UI_WIRE_NAME_CENSUS_20260906.tsv);
                  nonzero exit + a diff-shaped message on any drift.
      --emit      (re)write the artifact, printing `CENSUS EMIT: rows
                  changed` or `CENSUS EMIT: no change` FIRST -- the
                  comparison that follows a write is trivially equal and
                  is not evidence of anything.
      --summary   print the family/tier counts table to stdout and exit 0
                  (does not touch the artifact).
      --where N   print `relpath:line` of the exact occurrence this census
                  counts as name N's SOURCE evidence, and exit 0; exit 1 when
                  N has no counted occurrence. Exactly one line on stdout,
                  nothing else. This is the supported way to recover the line
                  number the artifact stopped carrying in round `o50gly` --
                  `grep -n` is NOT, because grep also reports docstring and
                  full-line-comment hits, which this census deliberately does
                  not count (round `jx6r5p`, pf-adversary D2 on `#1005`:
                  measured, `grep -n`'s first hit disagrees with the counted
                  hit on 18 of the 30 SOURCE rows, including both rows that
                  motivated dropping the line).
                  Needs no `pf_bridge` sibling: it reads only this repo -- so
                  N is NOT checked against the master catalog. Any identifier
                  token that appears in counted code gets located, catalog row
                  or not; this mode answers "where is this spelled", not "is
                  this a vital" (pf-adversary D-D on `#1013`).
                  When the name is counted in more than one file, a
                  `+N more files, use --where-all` line goes to STDERR --
                  stdout stays exactly one line, so `LINE=$(... --where X)`
                  is byte-for-byte what it was (COO-DECISION `20260907_1141`
                  item (c), which approved this as an ADDITION: no existing
                  consumer changes).
                  Does not touch the artifact.
      --where-all N
                  print EVERY occurrence this census counts for N, one
                  `relpath:line` per line on stdout, in census file order --
                  the first of them is exactly what `--where` prints. Exit 0,
                  or exit 1 with the same stderr message as `--where` when N
                  has no counted occurrence. 11 of the 327 catalog names are
                  counted in more than one file; the artifact can only ever
                  name one, because it is one row per name. [MEASURED this
                  round, re-derived here, not quoted:
                    python3 -c 'import sys; sys.path.insert(0, "tools");
                    import pf_ui_wire_name_census as c;
                    print(len(c.multi_file_counted_names(
                        [n for _w, n in c.load_names()])))'
                  -> 11, in about a second.  Needs the sibling catalog only
                  for the count, not for the mode.]
                  Does not touch the artifact.

Pure stdlib. No side effects on import.
"""
from __future__ import annotations

import argparse
import ast
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


def first_uncommented_line(text: str) -> str:
    """First line of TEXT that is neither blank nor a `#` comment.

    This is the ONE test that tells this tool's own emitted artifact apart
    from the master catalog, and it has to be exact.  Measured 2026-09-07
    (round `uw3bxb`, pf-adversary D3/D5 of round `8y18nc`): the catalog has
    FOUR leading `#` lines, not two, and the fourth of them reads
    `# id<TAB>name` -- so a check that looks at the first PARSED row pair
    ("id", "name") accuses the real catalog the moment those two comment
    characters are gone, and a check that looks at any two-column header
    accuses it as well.  `ARTIFACT_HEADER` has SIX columns and the catalog
    has no six-column header row in any spelling, commented or not.
    """
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        return line
    return ""


def _artifact_where_catalog_belongs(path) -> str:
    return (
        f"{path} looks like this tool's own emitted artifact (its first "
        f"uncommented line is the artifact header `{ARTIFACT_HEADER}`), not "
        "the master catalog. --tsv READS the catalog "
        "(pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv); "
        "--artifact READS AND, with --emit, OVERWRITES the census artifact "
        "(reports/PF_UI_WIRE_NAME_CENSUS_20260906.tsv); plain "
        "`python3 tools/pf_ui_wire_name_census.py` already uses the right "
        "default for both"
    )


def _catalog_where_artifact_belongs(path) -> str:
    return (
        f"CENSUS ERROR: refusing to write the census over {path}: that file "
        "is not this tool's artifact (its first uncommented line is not "
        f"`{ARTIFACT_HEADER}`). --artifact is the OUTPUT path and --emit "
        "overwrites it; the catalog goes to --tsv, which is read only"
    )


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
    text = tsv_path.read_text(encoding="utf-8")
    if first_uncommented_line(text) == ARTIFACT_HEADER:
        raise CensusError(_artifact_where_catalog_belongs(tsv_path))
    rows = []
    for line in text.splitlines():
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
    """Every ``.py`` file under ``base``, in an order that does not depend on
    the OS this runs on.

    Two OS-dependent behaviours had to be removed here (pf-adversary, round
    `d1b231`, both measured), because ``_build_source_hits`` records the FIRST
    hit per name and 11 of the catalog names are COUNTED in more than one file
    -- so this order decides those rows' ``evidence`` values, and a different
    order on Windows is a Windows-only `CENSUS DRIFT`, exactly PR #961's shape.

    The number used to read 46, which was wrong under every definition this
    file has (pf-adversary D6 on `#1017`; 46 > 30 = ``EXPECT_SOURCE`` in the
    same test file, so the sentence refuted itself without a measurement) and
    it is the number LANE-UI's ASK-COO of `1101` priced its whole question on.
    11 is re-derived, not quoted -- ``--where-all`` in the usage block above
    carries the command, and ``TheMultiFileCountIsRederived`` re-runs it in
    the test suite so this docstring cannot go stale silently again. An
    absolute SOURCE total is still deliberately not repeated here: it moves
    whenever any lane lands a wire module, and a number frozen in a docstring
    is exactly how this file went stale before.

    The failure shape this ordering prevents:

    1. ``sorted(<Path objects>)`` compares ``PurePath._str_normcase``, which on
       Windows is ``str(path).lower()`` -- backslash separators AND case-folded.
       Two proven divergences: ``["src/pf/Ui_shim.py", "src/pf/bootstrap.py"]``
       orders ``[Ui_shim, bootstrap]`` on Linux and ``[bootstrap, Ui_shim]`` on
       Windows; and against the existing ``gm/`` package a sibling ``gm2_*.py``
       orders ``[gm/..., gm2_...]`` on Linux (``/`` 0x2F < ``2`` 0x32) but
       ``[gm2_..., gm/...]`` on Windows (``2`` 0x32 < ``\\`` 0x5C). Sorting on
       ``as_posix()`` is byte-order on both.
    2. ``rglob("*.py")`` is case-INSENSITIVE on Windows, so a file named
       ``X.PY`` would be scanned there and ignored here. The explicit
       ``suffix == ".py"`` check makes both platforms agree with Linux.

    Latent, not live, when it was found: no tracked ``.py`` has an uppercase
    basename and the one live ``gm``/``gm_*`` prefix pair happens to order the
    same on both platforms. It was one ordinary new filename away from firing.
    Pinned by ``SourceHitPathSafetyTests``, which needs no sibling checkout and
    therefore runs on the Windows gate."""

    if not base.exists():
        return []
    files = [
        p for p in base.rglob("*.py") if p.is_file() and p.suffix == ".py"
    ]
    return sort_py_files(files)


def sort_py_files(files):
    """Order paths by the byte order of their POSIX spelling.

    Split out of ``_iter_py_files`` so the ordering policy can be tested with
    ``PureWindowsPath`` inputs, which reproduce Windows comparison semantics on
    any host -- a test that only fed real ``Path`` objects would pass on Linux
    for both the correct key and the broken ``sorted(files)`` it replaced, and
    so could not catch a revert anywhere this project actually runs pytest."""

    return sorted(files, key=lambda p: p.as_posix())


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


def _parse(text):
    """``ast.parse`` with the two encodings this project actually receives.

    A leading UTF-8 BOM makes ``ast.parse`` raise, and this repo is synced
    from a Windows/PowerShell bridge whose default output encoding writes
    one. Round `mg3nr4`, pf-adversary D7: without the strip, one BOM'd file
    would silently fall back to the no-exclusion path, its docstrings would
    start counting again, and the only symptom would be a pin going red with
    nothing naming the cause. Returns ``None`` when the text does not parse
    at all, so callers can both fall back AND count the fallback."""
    try:
        return ast.parse(text.lstrip("\ufeff"))
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None


def prose_string_line_numbers(text):
    """Line numbers (1-based) of every BARE STRING STATEMENT in ``text``.

    A bare string statement is an ``ast.Expr`` whose value is a string
    constant: it evaluates the string and throws it away. Python assigns no
    meaning to one beyond the first-statement case it calls a docstring, so
    every one of them is prose about the code, never a reference from it.
    Every physical line the literal spans is returned.

    WHY NOT JUST DOCSTRINGS (round `mg3nr4`, pf-adversary D1). The first
    version of this matched Python's own docstring definition -- the first
    statement of a module, class, function or async function, i.e. what
    ``ast.get_docstring`` returns. Measured on that version: prepending one
    extra one-line docstring above each ``ui_*_wire.py`` module docstring
    demotes the original prose block to a SECOND bare string,
    which is then not a docstring, and n/327 jumps 30 -> 149 with no wire
    code touched. A lint rule asking for a one-line summary, or anyone
    splitting a long docstring, would have done it by accident and the
    movement log would have read it as 119 rows of progress. Counting every
    bare string statement has no such spelling to slip through.

    Deliberately NOT excluded, because they are code, not prose: a string
    bound to a name (``WIRE_NAME = "ShowMessageVital"``), a string passed as
    an argument, a string in a collection, an f-string, and any trailing
    inline comment.
    """
    tree = _parse(text)
    if tree is None:
        return frozenset()
    lines = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr):
            continue
        value = node.value
        if not (isinstance(value, ast.Constant) and isinstance(value.value, str)):
            continue
        end = getattr(value, "end_lineno", None) or value.lineno
        lines.update(range(value.lineno, end + 1))
    return frozenset(lines)


def unparseable_py_files(py_files):
    """The subset of ``py_files`` whose text does not parse.

    Exists so the fallback in ``prose_string_line_numbers`` cannot be a
    silent skip (round `mg3nr4`, pf-adversary D7): a file in here has its
    prose counted as code, which moves the census with nothing to point at.
    Pinned empty over the real tree by the test file."""
    bad = []
    for path in py_files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if _parse(text) is None:
            bad.append(path)
    return bad


def code_token_lines(text):
    """Yield ``(lineno, [identifier tokens])`` for every line of ``text`` this
    census counts as CODE -- i.e. every line that is neither a full-line
    comment nor part of a bare string statement.

    Split out of ``_build_source_hits`` in round `jx6r5p` so that
    ``source_hit_location`` (which backs ``--where``) applies the SAME two
    exclusions rather than a second, hand-kept copy of them. A recovery
    command that disagrees with the census about which lines count is worse
    than no recovery command at all: that is exactly what ``grep -n`` was,
    and it shipped in FIVE places before it was measured. Round `jx6r5p`
    counted "three" (the commit message, this file's own comment,
    docs/UI_WIRE_COVERAGE.md); pf-adversary D-E on `#1013` found the two that
    count most, both in `pf_bridge`: the ASK-COO note of `0758` that COO read
    when approving COO-DECISION `0845` (still unconsumed at the time), and
    this lane's own round file for `o50gly`.

    ``split("\n")``, not ``splitlines()``: ``splitlines()`` also breaks on FF,
    VT, FS, GS, RS, NEL, U+2028 and U+2029, which ``ast`` does NOT count as
    line breaks. One form feed inside a docstring shifts every later line
    number and the exclusion inverts -- real code skipped, docstring prose
    counted (round `mg3nr4`, pf-adversary D6; latent today, 0 such characters
    in the tree). ``read_text`` already normalises ``\r\n`` and ``\r``."""

    prose_lines = prose_string_line_numbers(text)
    for lineno, line in enumerate(text.split("\n"), start=1):
        if line.lstrip().startswith("#"):
            continue
        if lineno in prose_lines:
            continue
        yield lineno, _IDENT_TOKEN.findall(line)


def census_file_texts(py_files):
    """Yield ``(relpath, text)`` for ``py_files``, in the order given, with the
    ONE spelling of the path and the ONE reading policy this census has.

    Extracted round `8btjto` (pf-adversary D-A on `#1013`, measured). Before
    it, ``_build_source_hits`` and ``source_hit_location`` each carried their
    own copy of these five lines, and nothing compared the copies: three
    one-line mutants in the copy inside ``source_hit_location`` sent
    ``--where`` to a DIFFERENT file from the one the artifact names while
    tests/test_ui_wire_name_census.py stayed green -- including
    ``str(path.relative_to(ROOT))``, which is PR #961's Windows backslash bug
    reappearing verbatim in the newer function, three lines away from the
    comment that explains why it must not.

    ``.as_posix()``, not ``str()``: on Windows ``str()`` renders backslashes
    (``src\\pirateforce_foundation\\x.py``), which never matches the
    forward-slash evidence baked into the committed artifact (generated on
    Linux) -- the actual cause of gate-windows's ``pytest_subset`` 9 failed on
    PR #961 (LANE-UI round `on8hbb`, per COO-DECISION 20260907_0148 item 2).

    ``errors="replace"`` and the ``OSError`` skip: a file this process cannot
    read must not take the whole census down, and one undecodable byte must
    not hide every name in that file. Both are exercised by
    ``CensusFileTextsTests`` -- before round `8btjto` neither had ever run
    (pf-adversary D-H: deleting both kept the suite green)."""

    for path in py_files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        yield path.relative_to(ROOT).as_posix(), text


def source_hit_location(name, py_files=None):
    """Return ``(relpath, lineno)`` of the FIRST occurrence of ``name`` that
    this census counts, or ``None`` when it counts none.

    This is the artifact's missing column, on demand. The committed artifact
    stopped carrying the line number in round `o50gly` because any lane adding
    lines above a cited hit rewrote this lane's file and reddened main; the
    line itself still has readers (a human opening the handler).

    It walks ``census_file_texts(py_files)`` -- the SAME generator
    ``_build_source_hits`` walks, so file order and path spelling are one
    piece of code, not two that happen to agree today. Round `jx6r5p` claimed
    that agreement while the two functions each held their own copy of those
    lines; pf-adversary D-A broke it with three one-line mutants that left the
    whole test file green. What is still genuinely separate is the membership
    test (one name here, a shrinking set there), and
    ``WhereAndCensusCannotDisagreeTests`` pins that across a fixture with many
    files, a subpackage, many names and names that are substrings of each
    other."""

    return next(iter_source_hits(name, py_files), None)


def iter_source_hits(name, py_files=None):
    """Yield ``(relpath, lineno)`` for the FIRST counted occurrence of ``name``
    in EACH file, in census file order.

    One generator so that ``--where`` (which takes the first) and
    ``--where-all`` (which takes all) cannot disagree about which files, in
    what order, with paths spelled how -- the same reason ``census_file_texts``
    exists (pf-adversary D-A on `#1013`: two copies of those five lines, and
    three one-line mutants of the second copy sent ``--where`` to a different
    file from the artifact with the whole test file green).

    Lazy on purpose: ``source_hit_location`` takes only the first element, so
    it still stops at the first hit and stays cheap for the callers that run
    it once per catalog name. Only ``--where-all`` (and the round's own
    re-derive of the multi-file count) pays for the whole walk.

    One line per file, not every line in a file: the artifact's evidence is a
    file, and this mode exists to name the files the artifact cannot -- the
    question COO-DECISION `20260907_1141` item (c) approved answering."""

    if py_files is None:
        py_files = _iter_py_files(SRC_DIR)
    for relpath, text in census_file_texts(py_files):
        for lineno, tokens in code_token_lines(text):
            if name in tokens:
                yield relpath, lineno
                break


def source_hit_locations(name, py_files=None):
    """``list(iter_source_hits(...))`` -- every file this census counts ``name``
    in, with the line of its first counted occurrence in each."""

    return list(iter_source_hits(name, py_files))


def multi_file_counted_names(names, py_files=None):
    """The subset of ``names`` this census counts in MORE THAN ONE file, in the
    order given. ONE pass over the tree, so it is cheap enough for a docstring
    to hand a reader as a command they will actually run.

    Deliberately a SECOND implementation of what
    ``[n for n in names if len(source_hit_locations(n)) > 1]`` computes, not a
    wrapper around it: the number this answers (11, round `cpgueb`) sits in
    two docstrings, and the previous number in that position (46) was wrong
    under every definition this file has and survived a round because nothing
    re-ran it (pf-adversary D6 on `#1017`). ``MultiFileCountIsRederivedTests``
    asserts the two implementations agree, so a mutant has to break both the
    same way, and neither can be a circular restatement of the other -- the
    shape pf-adversary D10 on `#1017` faulted in the one-pass equivalence test
    round `8btjto` shipped."""

    if py_files is None:
        py_files = _iter_py_files(SRC_DIR)
    wanted = set(names)
    seen_in = {}
    for _relpath, text in census_file_texts(py_files):
        here = set()
        for _lineno, tokens in code_token_lines(text):
            here.update(t for t in tokens if t in wanted)
        for name in here:
            seen_in[name] = seen_in.get(name, 0) + 1
    return [n for n in names if seen_in.get(n, 0) > 1]


def _build_source_hits(names, py_files):
    """One pass over every file in ``py_files`` (sorted, so deterministic):
    for every identifier token on a line that is neither a full-line comment
    nor part of a docstring, record the ``"relpath"`` of the FIRST line it is
    seen at, for every name in ``names`` that is still unresolved.

    The FILE, not ``"relpath:line"`` -- this sentence still said `:line` for a
    round after the value stopped carrying it (round `jx6r5p`). Use
    ``source_hit_location()`` / ``--where`` when the line itself is wanted.

    TWO kinds of line are skipped, for the same reason -- both are this
    codebase's own prose about the game, not references to it:

    * full-line comments (``line.lstrip().startswith("#")``), which removed
      the one false positive pf-adversary found on round `9dezrf` (a comment
      in `app.py` reusing `VitalData` as a generic memory-layout term);
    * bare string statements (``prose_string_line_numbers``, AST-based),
      added round `mg3nr4` per COO-DECISION `20260907_0546` on LANE-Q's
      `0454` alert -- docstrings and every other string that is evaluated
      and discarded.
      Without this, a lane writing the honest note "this module does NOT
      build `XxxVital`" pushed n/327 UP by one with nothing wired: the
      metric moved opposite to what it measures, and an inflated value gets
      read as progress. AST, not a three-quote regex, because the regex
      would have to reimplement raw/f-prefixes, nesting and escapes.

    STILL not caught, and still disclosed in docs/UI_WIRE_COVERAGE.md's
    non-claims: a name that appears ONLY in a trailing inline comment
    (``x = 1  # see FooVital``) counts as SOURCE, because that line does
    carry code and this tool does not tokenize sub-line spans."""
    remaining = set(names)
    hits: dict = {}
    for relpath, text in census_file_texts(py_files):
        if not remaining:
            break
        for _lineno, tokens in code_token_lines(text):
            if not remaining:
                break
            for token in tokens:
                if token in remaining:
                    # The FILE, not `file:line` (round `o50gly`). The line
                    # number was in the committed artifact until this round,
                    # and it made the artifact drift -- so
                    # `test_committed_artifact_matches_a_fresh_rederive` went
                    # red on main -- whenever ANY lane added lines above a hit
                    # in a file this census cites, with nothing about the
                    # census changing. Measured on `6b5b6b8`: LANE-GM grew
                    # `gm/command_capture.py` by 50 lines, and main went red
                    # with exactly two rows moved, `0x51E9` 750 -> 800 and
                    # `0x6CEC` 803 -> 853, both still SOURCE, both still in
                    # the same file. The hot files here (`runtime.py`, 9 rows;
                    # `gm/` catalogs; `delete_actor.py`) belong to other
                    # lanes, so that red is unbounded and only this lane can
                    # clear it. The line number is also the one part of the
                    # row nothing else needs: `--where <name>` re-derives it
                    # in one command, and the tier -- which is what n/327
                    # counts -- does not depend on it.
                    #
                    # NOT `grep -n` (round `jx6r5p`, pf-adversary D2 on
                    # `#1005`). grep reports docstring bodies and full-line
                    # comments, which this function skips, so its first hit
                    # is a DIFFERENT line on 18 of the 30 SOURCE rows --
                    # including the two rows whose drift caused this change
                    # (`gm/command_capture.py` spells both names in its
                    # module docstring). `--where` shares `code_token_lines`
                    # and this file order with the loop above, so it agrees
                    # with the census by construction rather than by hand.
                    hits[token] = relpath
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
    parser.add_argument(
        "--tsv", type=Path, default=DEFAULT_TSV,
        help="INPUT: the master catalog of vital names in pf_bridge "
             "(read only; never written). Default: %(default)s",
    )
    parser.add_argument(
        "--artifact", type=Path, default=DEFAULT_ARTIFACT,
        help="OUTPUT: the committed census artifact this tool emits and "
             "compares against (OVERWRITTEN by --emit). Default: %(default)s",
    )
    parser.add_argument(
        "--emit", action="store_true",
        help="rewrite the --artifact file from a fresh re-derive instead of "
             "comparing against it",
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="print the per-family tier counts only; do not compare or write",
    )
    parser.add_argument(
        "--where", metavar="NAME", default=None,
        help="print the first source file that mentions NAME, then exit",
    )
    parser.add_argument(
        "--where-all", metavar="NAME", default=None,
        help="print every source file that mentions NAME, then exit",
    )
    args = parser.parse_args(argv)

    if args.where is not None and args.where_all is not None:
        # Two answers to "which file", one stdout. Refuse rather than pick.
        print(
            "CENSUS ERROR: --where and --where-all are two spellings of the "
            "same question; pass one",
            file=sys.stderr,
        )
        return 2

    if args.where is not None or args.where_all is not None:
        # `is not None`, not truthiness: `--where ""` used to fall through to
        # the full census and exit 2 with `CENSUS ERROR ... needs a sibling
        # pf_bridge`, which is the one thing this mode promises never to need
        # (pf-adversary D-F on `#1013`). The empty string is simply a name
        # with no counted occurrence, and says so.
        #
        # Answered before build_rows() on purpose: this branch reads only
        # this repo's own `src/` tree, so it works on a checkout with no
        # `pf_bridge` sibling -- which is where a reader who just found a
        # bare path in the artifact usually is.
        wanted = args.where if args.where is not None else args.where_all
        # ONE walk for both modes: --where prints locations[0] and counts the
        # rest onto stderr, --where-all prints them all. Nothing here can make
        # the two disagree about file order or path spelling.
        locations = source_hit_locations(wanted)
        if not locations:
            # State what was measured -- no occurrence this census counts --
            # and offer the two reasons as possibilities, not as a finding.
            # This used to assert the docstring rule as THE cause, which is
            # false for the commonest case of all, a misspelled name: no
            # token matched anywhere and no exclusion ever fired
            # (pf-adversary D-D on `#1013`).
            print(
                f"NOT A SOURCE ROW: {wanted} has no occurrence that this "
                f"census counts under {SRC_DIR.relative_to(ROOT).as_posix()} "
                "-- either the name is spelled nowhere in that tree (check "
                "the spelling against the master catalog), or every "
                "occurrence is in a docstring or a full-line comment, which "
                "are not counted by rule (COO-DECISION 20260907_0546). This "
                "tool does not read the master catalog, so it cannot tell "
                "you which.",
                file=sys.stderr,
            )
            return 1
        if args.where_all is not None:
            for relpath, lineno in locations:
                print(f"{relpath}:{lineno}")
            return 0
        relpath, lineno = locations[0]
        # STDOUT stays exactly one line -- COO-DECISION `20260907_1141` item
        # (c) approved the extra line only on STDERR, so that the pinned
        # `LINE=$(... --where X)` contract (pf-adversary D-G on `#1013`) is
        # byte-for-byte what it was.
        print(f"{relpath}:{lineno}")
        if len(locations) > 1:
            print(
                f"+{len(locations) - 1} more files, use --where-all "
                f"{wanted}",
                file=sys.stderr,
            )
        return 0

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
        # D2 (pf-adversary, round `8y18nc`): `--emit --artifact <catalog>`
        # used to overwrite the 327-name master catalog with a 328-line
        # census and then print `PASS`, because nothing here looked at what
        # was about to be destroyed.  Measured on a copy: md5 173f662e ->
        # 9f211939, exit 0.  An absent file is still fine (that is a first
        # emit); a file that exists and is not this tool's artifact is not.
        if args.artifact.exists():
            existing = args.artifact.read_text(encoding="utf-8")
            if first_uncommented_line(existing) != ARTIFACT_HEADER:
                print(
                    _catalog_where_artifact_belongs(args.artifact),
                    file=sys.stderr,
                )
                return 2
            # D4: --emit writes before the comparison below, so that
            # comparison is guaranteed to pass and says nothing.  Say the
            # useful thing instead, out loud, before the write.
            print(
                "CENSUS EMIT: %s"
                % ("rows changed" if existing != rendered else "no change")
            )
        # newline="" -- write exactly the "\n" this module already joins
        # with, not whatever this OS's default text-mode translation would
        # do (Windows would otherwise write "\r\n", which read_text's own
        # universal-newline translation on read masks in this comparison
        # but which other tools reading this artifact byte-for-byte would
        # not).
        args.artifact.write_text(rendered, encoding="utf-8", newline="")

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
