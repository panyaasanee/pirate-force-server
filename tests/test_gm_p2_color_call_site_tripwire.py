"""Nothing forced new P-2 colour code to CONSULT the refusal.  Inside this
lane's own zone, something does now.

WHAT WAS MISSING.  Round ``wggs0i`` built ``gm/name_color_gate.py`` so that
``RE-195``'s bounded negative became executable rather than prose, and its
tests closed one half of the hole: an ``RE-191`` palette value cannot be
pasted anywhere under ``src/``.  The other half went into that round's own
backlog, unfixed and named as this lane's next job:

    "nothing yet forces newly written colour code to call
     ``p2_color_wiring_verdict()``"

A refusal nobody is obliged to read is a comment.

WHAT THIS FILE DOES.  Every module under ``src/pirateforce_foundation/gm/``
that names a P-2 colour concept IN EXECUTABLE CODE must call
``p2_color_wiring_verdict()`` -- and must reach it through the gate module,
not through a function of its own with the same name.  Naming a token in a
COMMENT or a STRING-EXPRESSION DOCSTRING is free, deliberately: writing down
what a lane must NOT encode is the opposite of the hazard, and
``gm/attr_wire.py`` must keep being allowed to do it.  Import statements are
free for a blunter reason -- the gate module's own NAME contains a banned
token, so a scan that counted imports would punish exactly the modules doing
the right thing.

WHY ONLY ``gm/``, WHEN THE HAZARD IS THE WHOLE TREE.  pf-adversary (round
``qhowwu``) demonstrated the first draft red-lighting other lanes for
correct code -- ``from ...gm import name_color_gate`` in a dispatcher, a
column tuple containing ``"name_color"``, a ``raise`` whose message cites
``RE-195``.  Their only remedy was an allowlist living in THIS file, which
is LANE-GM's exclusive write zone: a lane doing the right thing had no
in-zone way to go green inside its own round.  A guard that deadlocks
another lane is worse than the gap it closes, so the obligation stops at the
boundary this lane actually owns.  The cross-tree half is asked for in
writing instead (``notes_to_chief/20260902_1230_LANE-GM-TO-CHIEF-*``), and
until chief answers it, the gap below stands OPEN and named.

WHAT THIS CANNOT DO -- read this before citing it as cover.  In rough order
of how likely each is to matter:

* PATH.  It scans ``gm/`` only.  ``current/pf_login_game_server_v141.py``
  -- the running game server, the file that actually composes actor rows on
  the wire -- is not scanned, nor is the rest of ``src/``, ``tools/``,
  ``patches/``, or any ``.pyi``.  That is the biggest hole and it is not
  closed here.
* RESULT.  It proves the verdict is CALLED, never that the caller obeyed it.
  ``p2_color_wiring_verdict()`` on its own line, then wiring the colour
  anyway, passes.
* NAME.  It is a name tripwire, not a semantic one: colour code that names
  no token -- composing the field by a bare index -- walks past.
* COMPOSITION.  Literal concatenation is folded and caught, but a runtime
  f-string (``f"{prefix}StyleID"``) is not.

Zone: this file is ``tests/test_gm_*.py``.  It reads modules and edits none.
"""
from __future__ import annotations

import ast
import io
import pathlib
import re
import sys
import tokenize

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import name_color_gate as gate

#: The obligation's boundary: the only tree LANE-GM writes, so a red here is
#: never another lane's round held hostage.
GM_ZONE = ROOT / "src" / "pirateforce_foundation" / "gm"

#: The verdict every P-2 colour call site in that zone owes a call to.
REQUIRED_CALL = "p2_color_wiring_verdict"

#: The module it has to come from.  A local function of the same name does
#: not count (pf-adversary M1).
GATE_MODULE_NAME = "name_color_gate"
GATE_MODULE_PATH = GM_ZONE / "name_color_gate.py"

#: Words a round writes when it is doing P-2 monster-name-colour work.  Each
#: is taken from this repository or from NOW.md P-2; none is invented to pad.
P2_COLOR_TOKENS = (
    "FontStyleID",
    "name_color",
    "name_colour",
    "style61",
    "style_61",
    "style63",
    "style_63",
    "RE-191",
    "RE-195",
)

_TOKEN_RE = re.compile("|".join(re.escape(t) for t in P2_COLOR_TOKENS), re.IGNORECASE)


class UnscannableModule(Exception):
    """Raised with the path, so a bad file names itself instead of dumping a
    SyntaxError from inside the scanner (pf-adversary M3)."""


def _line_starts(source: str) -> list[int]:
    """Offsets of each line, split on ``\\n`` ONLY.

    ``str.splitlines`` also splits on U+2028, U+0085 and friends; ``ast`` and
    ``tokenize`` do not, so using it desynchronised this table from their row
    numbers and blanked the wrong span (pf-adversary M4).
    """
    starts = [0]
    for i, ch in enumerate(source):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _blanked_spans(source: str) -> list[tuple[int, int]]:
    """Comments, docstrings and imports -- the three free forms."""
    starts = _line_starts(source)

    def offset(row: int, col: int) -> int:
        return starts[row - 1] + col

    spans: list[tuple[int, int]] = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type is tokenize.COMMENT:
            spans.append((offset(*tok.start), offset(*tok.end)))
    for node in ast.walk(ast.parse(source)):
        # EVERY bare string statement, not only a first-statement docstring:
        # the attribute-docstring convention (`X = 1` then `"""..."""`) is a
        # docstring to a reader and to Sphinx, and blanking only the first
        # statement made it trip (pf-adversary H2).
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            spans.append(
                (
                    offset(node.value.lineno, node.value.col_offset),
                    offset(node.value.end_lineno, node.value.end_col_offset),
                )
            )
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            spans.append(
                (offset(node.lineno, node.col_offset), offset(node.end_lineno, node.end_col_offset))
            )
    return spans


#: The gate module's own identifier.  Referring to it is the RIGHT thing to
#: do, and it contains a banned token, so it is blanked wherever it appears
#: -- otherwise a dispatcher that registers the gate is punished for it.
_GATE_IDENT_RE = re.compile(r"\b" + GATE_MODULE_NAME + r"\b")


def _executable_text(source: str) -> str:
    """``source`` with those spans blanked, offsets preserved."""
    out = list(source)
    spans = list(_blanked_spans(source))
    spans += [(m.start(), m.end()) for m in _GATE_IDENT_RE.finditer(source)]
    for start, end in spans:
        for i in range(start, min(end, len(out))):
            if out[i] != "\n":
                out[i] = " "
    return "".join(out)


def _folded_strings(source: str) -> list[str]:
    """String constants as the PARSER sees them, plus literal ``+`` joins.

    ``"Font" "StyleID"`` is folded by the parser into one constant, so this
    catches implicit concatenation -- the shape black produces for a long
    string -- which a raw-text scan walks past (pf-adversary M2).

    Docstring statements are skipped here rather than by blanking the source
    first: blanking a class whose whole body is a docstring leaves a body
    that will not parse.
    """
    tree = ast.parse(source)
    docstrings = {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    }
    values: list[str] = []
    for node in ast.walk(tree):
        if id(node) in docstrings:
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.append(node.value)
        elif (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Add)
            and isinstance(node.left, ast.Constant)
            and isinstance(node.right, ast.Constant)
            and isinstance(node.left.value, str)
            and isinstance(node.right.value, str)
        ):
            values.append(node.left.value + node.right.value)
    return values


def _token_hits(source: str) -> list[tuple[int, str]]:
    """(line, token) for every P-2 token in EXECUTABLE code.

    A docstring's own text reaches ``_folded_strings`` too, so the folded
    pass is filtered to constants that survive the blanking -- otherwise the
    free forms above would stop being free.
    """
    text = _executable_text(source)
    hits = [
        (text.count("\n", 0, m.start()) + 1, m.group(0))
        for m in _TOKEN_RE.finditer(text)
    ]
    if hits:
        return hits
    # The folded pass runs on the ORIGINAL source with docstring statements
    # skipped -- comments and imports carry no string constants to fold, so
    # the free forms stay free either way.
    for value in _folded_strings(source):
        found = _TOKEN_RE.search(value)
        if found:
            hits.append((0, found.group(0)))
    return hits


def _imports_the_gate(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and GATE_MODULE_NAME in node.module:
                return True
            if any(GATE_MODULE_NAME == a.name or a.name == REQUIRED_CALL for a in node.names):
                return True
        elif isinstance(node, ast.Import):
            if any(GATE_MODULE_NAME in a.name for a in node.names):
                return True
    return False


def _defines_its_own(tree: ast.AST) -> bool:
    return any(
        isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == REQUIRED_CALL
        for n in ast.walk(tree)
    )


def _consults_the_refusal(source: str) -> bool:
    tree = ast.parse(source)
    called = any(
        isinstance(n, ast.Call)
        and (n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", None))
        == REQUIRED_CALL
        for n in ast.walk(tree)
    )
    return called and _imports_the_gate(tree) and not _defines_its_own(tree)


def _read(path: pathlib.Path) -> str:
    try:
        source = path.read_text(encoding="utf-8")
        ast.parse(source)
        list(tokenize.generate_tokens(io.StringIO(source).readline))
    except Exception as exc:  # noqa: BLE001 -- the path is the point
        try:
            shown = path.relative_to(ROOT).as_posix()
        except ValueError:
            shown = path.as_posix()
        raise UnscannableModule(f"{shown}: {exc!r}") from exc
    return source


def _zone_files() -> list[pathlib.Path]:
    return sorted(p for p in GM_ZONE.rglob("*.py") if p.is_file())


# --------------------------------------------------------------------------
# the tripwire
# --------------------------------------------------------------------------


def test_p2_colour_code_in_the_gm_zone_must_consult_the_refusal():
    """The backlog item of round ``wggs0i``, made mechanical inside the zone
    this lane owns."""
    offenders, unscannable = [], []
    for path in _zone_files():
        if path == GATE_MODULE_PATH:
            continue
        rel = path.relative_to(ROOT).as_posix()
        try:
            source = _read(path)
        except UnscannableModule as exc:
            unscannable.append(str(exc))
            continue
        hits = _token_hits(source)
        if not hits or _consults_the_refusal(source):
            continue
        offenders.append("; ".join(f"{rel}:{line} ({tok})" for line, tok in hits))
    assert not unscannable, (
        "a module under gm/ could not be scanned, so this gate proved nothing "
        "about it: " + " | ".join(unscannable)
    )
    assert not offenders, (
        "P-2 colour tokens appear in executable code under gm/ that never "
        f"reaches {REQUIRED_CALL}() through {GATE_MODULE_NAME}: "
        + " | ".join(offenders)
        + " -- RE-195's bounded negative still stands, so a call site that "
        "touches this field has to read the refusal and say what it does "
        "about it.  Comments, docstrings and imports are free; if the mention "
        "belongs in one of those, move it there."
    )


def test_the_module_that_is_the_refusal_is_exempt_on_purpose():
    """Not an accident of the scan: the gate names every token by design."""
    assert GATE_MODULE_PATH.exists()
    assert _token_hits(GATE_MODULE_PATH.read_text(encoding="utf-8"))


def test_the_obligation_stops_at_this_lanes_zone_and_says_so():
    """Pinned so a later round cannot widen the blast radius by accident --
    widening it is what deadlocked another lane in the first draft."""
    assert GM_ZONE == ROOT / "src" / "pirateforce_foundation" / "gm"
    assert GM_ZONE.is_dir()
    doc = pathlib.Path(__file__).read_text(encoding="utf-8").split('"""')[1]
    assert "pf_login_game_server_v141.py" in doc, (
        "the biggest unscanned path must stay named in the limitations"
    )


# --------------------------------------------------------------------------
# the scanner, watched failing
# --------------------------------------------------------------------------

_VIOLATION = '''"""A docstring may say FontStyleID all it likes."""
# and so may a comment: RE-191, style63

STYLE_SELECTOR = "FontStyleID"


def paint(actor):
    return STYLE_SELECTOR
'''

_COMPLIANT = (
    "from pirateforce_foundation.gm.name_color_gate import p2_color_wiring_verdict\n"
    + _VIOLATION.replace(
        "def paint(actor):\n    return STYLE_SELECTOR\n",
        "def paint(actor):\n"
        "    assert p2_color_wiring_verdict().allowed is False\n"
        "    return STYLE_SELECTOR\n",
    )
)


def test_the_scanner_can_actually_see_a_violation():
    """A guard nobody has watched fail is a guard nobody should trust."""
    hits = _token_hits(_VIOLATION)
    assert [tok for _, tok in hits] == ["FontStyleID"]
    assert not _consults_the_refusal(_VIOLATION)


def test_a_call_site_that_consults_the_refusal_passes():
    assert _token_hits(_COMPLIANT)
    assert _consults_the_refusal(_COMPLIANT)


@pytest.mark.parametrize(
    "source",
    [
        '"""RE-191 and RE-195 and FontStyleID, in a docstring."""\n# style61 too\nX = 1\n',
        'X = 1\n"""X holds the FontStyleID index."""\n',  # attribute docstring
        "from pirateforce_foundation.gm import name_color_gate\nX = 1\n",
        "from pirateforce_foundation.gm.name_color_gate import p2_color_wiring_verdict\nX = 1\n",
        'BANNER = "a b"\n# never hardcode FontStyleID (RE-195).\n',
        "from pirateforce_foundation.gm import name_color_gate\n"
        'HANDLERS = {"p2": name_color_gate}\n',
    ],
    ids=["docstring", "attribute-docstring", "import-module", "import-name", "u2028-comment", "registers-the-gate"],
)
def test_the_free_forms_never_trip_it(source):
    """Each of these red-lighted an innocent module in the first draft."""
    assert _token_hits(source) == []


@pytest.mark.parametrize(
    "literal",
    ['"Font" "StyleID"', '"Font" + "StyleID"'],
    ids=["implicit-concat", "literal-add"],
)
def test_literal_concatenation_does_not_hide_a_token(literal):
    assert _token_hits(f"STYLE = {literal}\n")


@pytest.mark.parametrize(
    "source, expected",
    [
        ("from pirateforce_foundation.gm import name_color_gate\n"
         "x = name_color_gate.p2_color_wiring_verdict()\n", True),
        ("x = p2_color_wiring_verdict()\n", False),                       # no import
        ("def p2_color_wiring_verdict():\n    return 1\n"
         "x = p2_color_wiring_verdict()\n", False),                       # its own
        ("from pirateforce_foundation.gm import name_color_gate\n"
         "x = name_color_gate.p2_color_wiring_verdict\n", False),         # not a call
    ],
    ids=["real", "no-import", "shadowed", "bare-name"],
)
def test_only_a_real_call_through_the_gate_counts(source, expected):
    assert _consults_the_refusal(source) is expected


@pytest.mark.parametrize(
    "bad",
    ["﻿X = 1\n", "def f(:\n", "def f():\n\tx = 1\n        y = 2\n"],
    ids=["utf8-bom", "syntax-error", "taberror"],
)
def test_an_unscannable_file_names_itself(bad, tmp_path):
    path = tmp_path / "broken.py"
    path.write_text(bad, encoding="utf-8")
    with pytest.raises(UnscannableModule):
        _read(path)


def test_the_gate_still_refuses_so_the_obligation_still_bites():
    """If the verdict ever flips, this tripwire is the wrong shape and the
    round that flips it has to come back here."""
    assert gate.p2_color_wiring_verdict().allowed is False
