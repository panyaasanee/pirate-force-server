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
writing instead -- in the bridge repository, which this one does not
contain (``pf_bridge/notes_to_chief/20260902_1230_LANE-GM-TO-CHIEF-*``,
and again in ``..._1335_...``) -- and
until chief answers it, the gap below stands OPEN and named.

WHAT CHANGED (COO-DECISION ``20260906_0255``).  LANE-B shipped a second
per-mob NPCAttr composer the same week as the first (``mob_viewer_link.py``,
``pirate-force-server#876``), and ``field_mobs.py`` being a fixed name meant
this scan could not see it.  The order was explicit: widen the scan to that
file AND to every module that assembles NPCAttr bytes for a mob, and do not
bind the widening to a single filename.  ``field_mobs.py`` therefore stopped
being its own special case; both it and ``mob_viewer_link.py`` are two of
what one discovery function finds by naming ``NPCAttr`` in a module's
source (:func:`_npc_attr_composer_files`), the same way the P-2 token scan
itself is name-based rather than semantic -- run today, it finds several
MORE files than just these two, and nobody has read the rest one by one to
judge whether each genuinely composes NPCAttr bytes rather than merely
discussing the class chain in prose (see the honesty note next to
:data:`NPC_ATTR_COMPOSER_ROOT`).  Exactly like the ``gm/`` zone scan, this
wider net has never fired against a real file either, today -- a test
below keeps this sentence honest.  Turning that discovery on also surfaced
a real bug in THIS file: the folded-string fallback below matched
"name_color" inside
``mob_viewer_link.py``'s own cross-reference to ``gm/name_color_gate.py``
-- a citation, not a violation -- because that fallback pass, unlike the
primary one, never scrubbed the gate identifier first.  Fixed in the same
round it was found, not left as a red for LANE-B to be blamed for (see the
comment inside :func:`_token_hits`).

WHAT THIS CANNOT DO -- read this before citing it as cover.  In rough order
of how likely each is to matter:

* PATH.  It scans ``gm/`` plus every top-level module under
  ``src/pirateforce_foundation/`` that names ``NPCAttr`` in its source
  (discovered, not listed -- see :func:`_npc_attr_composer_files`;
  ``field_mobs.py`` was the first of these, added round ``y1evqj``'s
  pf-adversary D10, read-only -- see :data:`FIELD_MOBS_PATH`).
  ``current/pf_login_game_server_v141.py`` -- the running game server, the
  file that actually composes actor rows on the wire -- is still not
  scanned: the discovery root is the package directory, not the repository,
  so ``current/``, ``tools/``, ``patches/``, and any ``.pyi`` stay outside
  it.  That is still the biggest hole and it is not closed here.
* RESULT.  NARROWED by round ``9sqec6``: a verdict call whose value nothing
  downstream can act on no longer counts as consulting anything, and NO call
  in a module may be discarded (``all``, not ``any`` -- otherwise one
  throwaway binding at module scope launders the discard at the site that
  matters).  The rule reads the STATEMENT, not the call: a bare expression
  statement throws away everything inside it, so ``verdict(),`` (one comma),
  ``[verdict()]``, ``verdict().allowed``, ``not verdict()``,
  ``f"{verdict()}"``, ``lambda: verdict()`` and a comprehension over it are
  all discards.  The first version of this rule asked only whether the call
  was the statement's DIRECT value, and pf-adversary defeated the whole
  round with a single trailing comma.  Handing the value to another function
  (``_require_p2(verdict())``) is the one thing that rescues a bare
  statement, because the callee received the answer.
  Its premise, stated because it is load-bearing: the gate RETURNS its
  refusal.  ``try: verdict() / except NameColorGateError:`` reads as a
  discard here, and would be a real consultation against a gate that raised.
  What is still NOT proved, each pinned by a test that asserts the shape
  PASSES rather than by prose: a tautological ``if p2_color_wiring_verdict():``
  (the dataclass is truthy, so the body always runs); a consult sitting in
  dead code; an unreachable consult; a ``match`` whose ``case _`` ignores the
  subject; and a branch that consults and then paints anyway -- OBEDIENCE is
  not provable here at all.  An ``assert``-only consult passes too, and in a
  scanned module ``python -O`` would compile that assert away entirely; that
  last point is argued rather than tested, because this file reads source
  text and never executes the module it judges.
  Finally, and least visible: no module under ``gm/`` other than the gate
  names a P-2 token in executable code today: this rule has
  never run against a real module.  Every green in the zone scan below comes
  from a ``continue``.  It is prospective, and a test below keeps this sentence
  honest.
* NAME.  It is a name tripwire, not a semantic one: colour code that names
  no token -- composing the field by a bare index -- walks past.
* COMPOSITION.  Literal concatenation is folded and caught, but a runtime
  f-string (``f"{prefix}StyleID"``) is not.

Zone: this file is ``tests/test_gm_*.py``.  It reads modules and edits none.
"""
from __future__ import annotations

import ast
import inspect
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

#: D10 (pf-adversary, round ``y1evqj``): this file's own limitations section
#: named ``pf_login_game_server_v141.py`` as the biggest unscanned path, but
#: said nothing about ``field_mobs.py`` -- the module that actually composes
#: every actor row this refusal is about (``FieldMob.actor_identity``,
#: ``hostile_actor_entry``), and the file COO-DECISION ``20260905_2348``
#: names as the eventual per-viewer compose point's neighbour.  It is where
#: a real P-2 colour splice is most likely to land first, and this tripwire
#: could not see it.
#:
#: This constant is READ-ONLY: the test below opens ``field_mobs.py`` to
#: scan its text, exactly as it already does for every file under
#: ``GM_ZONE``, and never writes to it.  ``field_mobs.py`` is outside this
#: lane's write zone (``prompts/LANE-GM.md``'s "do not touch lane A/B's
#: zone" rule), so a red here is an escalation letter to chief/LANE-B, never
#: a same-round self-fix the way a ``GM_ZONE`` offender is.
FIELD_MOBS_PATH = ROOT / "src" / "pirateforce_foundation" / "field_mobs.py"

#: COO-DECISION ``20260906_0255`` item 2: ``field_mobs.py`` was a fixed name,
#: and LANE-B shipped a SECOND module the same shape the same week
#: (``mob_viewer_link.py``, ``pirate-force-server#876``) that this scan could
#: not see either.  The order was explicit -- "extend the scan set to cover
#: this file, and every module that assembles NPCAttr bytes for a mob; do
#: not bind this to a single filename" -- so this is a NAME-based discovery,
#: not a second hardcoded path next to ``FIELD_MOBS_PATH``: any top-level
#: module in the package that so much as spells the wire class this whole
#: file is about (``NPCAttr``) is a candidate.
#:
#: HONESTLY, NOT "TWO COMPOSERS".  pf-adversary (round ``xfeizd``) ran this
#: discovery against the real tree and got well over a dozen files today,
#: not the two named above -- several are hypothesis/analysis modules that
#: only discuss ``NPCAttr`` in prose, not code that composes it.  The exact
#: count is deliberately not pinned here: it will drift as the tree grows,
#: and a stale number would be worse than none (``test_npc_attr_composer_
#: discovery_finds_the_known_composers`` pins only that the two NAMED
#: composers stay found, never the total).  This function does not,
#: and by design cannot, tell "assembles bytes" apart from "writes about the
#: class chain": it is a name tripwire exactly like the P-2 token scan it
#: feeds, and the same NAME limitation applies (see the file docstring).
#: Nobody has read all sixteen to decide which genuinely belong; this round
#: chose the wider, unaudited net over a curated list that would need a
#: human to keep current, because a red on any of the sixteen still costs
#: nothing worse than a letter to the lane that owns the file -- the same
#: price ``field_mobs.py`` already pays -- and an unaudited net that scans
#: too much is a smaller risk than a curated list that quietly drifts out
#: of date.
#:
#: Root and boundary, matching ``FIELD_MOBS_PATH``'s own scope exactly:
#: top-level files only (``glob``, not ``rglob``), so ``GM_ZONE`` -- already
#: scanned in full -- is never double-counted, and a subpackage some other
#: lane adds later is not silently swept in without its own round noticing.
NPC_ATTR_COMPOSER_ROOT = ROOT / "src" / "pirateforce_foundation"

#: The identifier this discovery keys on.  A name tripwire, like the P-2
#: token scan itself (see the file docstring's own NAME limitation) --
#: composing the field by a bare index with no identifier in sight walks
#: past this exactly as it would walk past the P-2 tokens.
NPC_ATTR_IDENT_RE = re.compile(r"\bNPCAttr\b")


def _npc_attr_composer_files() -> list[pathlib.Path]:
    """Top-level modules whose source names ``NPCAttr`` -- discovered, not
    listed.

    READ-ONLY, exactly like ``FIELD_MOBS_PATH`` above: every path returned
    here is opened with ``.read_text()`` for scanning, by this function and
    by the test that consumes it, and never for writing.  Every path this
    returns is outside ``GM_ZONE`` by construction (this lane's own files
    live one directory down, under ``gm/``, and ``glob`` here is
    non-recursive), so a red from one of them is the same escalation
    ``field_mobs.py`` already gets: a letter to the lane that owns the file,
    never a same-round edit to it from here.

    ``current/pf_login_game_server_v141.py`` and everything under ``tools/``
    also name ``NPCAttr`` and are still NOT covered -- this discovery's root
    is the package directory, not the repository, so the biggest unscanned
    path the file docstring already names stays unscanned by design, not by
    oversight.

    A file this cannot even DECODE is skipped, not raised: pf-adversary
    (round ``xfeizd``) found that an earlier version of this function called
    ``.read_text()`` with no guard at all, unlike ``_read()`` above, so one
    bad-encoding file anywhere among the (currently 200+) top-level modules
    under this root -- whether or not it has anything to do with NPCAttr --
    would abort collection of every test in this file with a raw
    ``UnicodeDecodeError`` naming no path.  A file that cannot be decoded
    cannot be confirmed to name ``NPCAttr`` either, so silently leaving it
    out of discovery is the same posture ``_read()`` takes for a module that
    fails to scan for a different reason: name the failure at the actual
    scan step, not here, where there is nothing yet to report about it.
    """
    found = []
    for path in NPC_ATTR_COMPOSER_ROOT.glob("*.py"):
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if NPC_ATTR_IDENT_RE.search(source):
            found.append(path)
    return sorted(found)


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
#: IGNORECASE to match ``_TOKEN_RE``'s own case-insensitivity: without it, a
#: citation spelled ``NAME_COLOR_GATE`` was not scrubbed and produced a
#: false positive of its own (pf-adversary, round ``xfeizd``).
_GATE_IDENT_RE = re.compile(r"\b" + GATE_MODULE_NAME + r"\b", re.IGNORECASE)


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
    # the free forms stay free either way.  The gate identifier is NOT free
    # here by accident: this pass reads assigned/keyword string constants,
    # not just docstrings, and a constant that cites "gm/name_color_gate.py"
    # as a cross-reference (the RIGHT thing to write) contains the substring
    # "name_color" too.  ``_executable_text`` above already scrubs every
    # occurrence of the gate identifier for exactly this reason; this pass
    # read the ORIGINAL, unscrubbed source and had no equivalent, so a real
    # module (``mob_viewer_link.py``, added to this scan the same round this
    # comment was written) tripped it for the exact opposite of a violation.
    for value in _folded_strings(source):
        found = _TOKEN_RE.search(_GATE_IDENT_RE.sub(" ", value))
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
    if not _verdict_calls(tree):
        return False
    if not _imports_the_gate(tree) or _defines_its_own(tree):
        return False
    # RESULT tier: a call whose answer is thrown away consulted nothing.  What
    # this proves is that no verdict call in the module is discarded -- never
    # that the value was read, believed, or obeyed (see the file docstring and
    # the witness tests at the end).
    return _every_verdict_is_kept(tree)


def _verdict_calls(tree: ast.AST) -> list[ast.Call]:
    return [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and (n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", None))
        == REQUIRED_CALL
    ]


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    table: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            table[child] = node
    return table


def _call_operands(call: ast.Call) -> list[ast.AST]:
    """The nodes a call RECEIVES -- positional and keyword arguments.

    Not ``func``: ``p2_color_wiring_verdict().reason()`` receives nothing; it
    reads the verdict and drops the string.
    """
    return list(call.args) + [kw.value for kw in call.keywords]


def _is_discarded(call: ast.Call, parents: dict[ast.AST, ast.AST]) -> bool:
    """True iff nothing downstream can act on this call's value.

    Walks outward to the STATEMENT the call sits in.  Any statement other
    than a bare expression statement keeps the value -- it is bound,
    returned, raised, tested, iterated, entered, matched or decorated with.
    A bare expression statement throws the whole expression away, and so
    throws the verdict away with it, no matter how much syntax sits in
    between: ``p2_color_wiring_verdict(),`` (one comma), ``[...()]``,
    ``...().allowed``, ``not ...()``, ``f"{...()}"``, ``lambda: ...()`` and
    a comprehension over it are all discards, and the first version of this
    rule -- which asked only whether the call was the Expr's DIRECT value --
    graded every one of them as a consultation (pf-adversary, second pass,
    D1: one trailing comma defeated the whole round).

    The one thing that rescues a bare expression statement is HANDING THE
    VALUE TO ANOTHER FUNCTION (``_require_p2(verdict())``, ``log.info(
    verdict().reason())``): the callee received the answer and may act on
    it.  That exception is what keeps this zone's own guard idiom -- a bare
    ``_require_x(value)`` statement, ``gm/commands.py:321``,
    ``gm/teleport_wire.py:346`` -- legal, and a rule that red-lights the
    zone's own idiom is how the FIRST design of this round died (D1 of the
    first pass).

    Premise, written down because it is load-bearing and unstated elsewhere:
    the gate RETURNS its refusal.  A future gate that RAISED instead would
    make ``try: verdict() / except NameColorGateError:`` a real consultation
    through a channel this rule reads as a discard, and this function would
    have to be revisited with it (pf-adversary, second pass, D9).
    """
    node: ast.AST = call
    parent = parents.get(node)
    while parent is not None:
        if isinstance(parent, ast.Call) and any(node is a for a in _call_operands(parent)):
            return False
        if isinstance(parent, ast.Expr):
            return True
        node, parent = parent, parents.get(parent)
    # Fell off the top without meeting a bare expression statement.  No
    # explicit "any other statement keeps it" clause: a statement's parent is
    # only ever another statement or the module, so once the walk passes a
    # non-Expr statement it can never meet an Expr, and such a clause would be
    # unkillable by any test (pf-adversary, second pass, D4).
    return False


def _every_verdict_is_kept(tree: ast.AST) -> bool:
    """No verdict call in the module may be discarded.

    ``all``, not ``any``: with ``any`` a single throwaway binding at module
    scope (``_BOOT = p2_color_wiring_verdict()``) launders every discarded
    call in the file, and no test could tell the two rules apart because no
    fixture had two calls (pf-adversary, second pass, D4/D5).  A discarded
    call is never useful, so requiring all of them costs nothing correct.
    """
    parents = _parents(tree)
    calls = _verdict_calls(tree)
    return bool(calls) and all(not _is_discarded(call, parents) for call in calls)


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
        f"reaches {REQUIRED_CALL}() through {GATE_MODULE_NAME}, or calls it "
        "and throws the answer away: "
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


def test_field_mobs_is_scanned_for_p2_colour_tokens_read_only():
    """D10: widen the SCAN, not the write zone.

    Same rule as ``test_p2_colour_code_in_the_gm_zone_must_consult_the_
    refusal`` above, applied to exactly one file outside ``GM_ZONE``:
    ``field_mobs.py``, named by COO-DECISION ``20260905_2348`` as the
    neighbour of the eventual per-viewer compose point. This test only
    calls ``.read_text()`` on it -- the same read-only access every other
    assertion in this file already has to every module it scans -- and
    asserts nothing else about the file.

    A red here is NOT something this lane can fix in the same round: it
    would mean a P-2 colour token reached executable code in another
    lane's zone without consulting the gate, and the fix is a letter to
    chief/LANE-B, not an edit to ``field_mobs.py`` from here.
    """
    assert FIELD_MOBS_PATH.exists(), (
        "field_mobs.py moved or was renamed -- update FIELD_MOBS_PATH "
        "(and tell LANE-A/LANE-B, since this lane does not own that file)"
    )
    source = _read(FIELD_MOBS_PATH)
    hits = _token_hits(source)
    if not hits:
        return
    assert _consults_the_refusal(source), (
        "P-2 colour tokens appear in field_mobs.py's executable code that "
        f"never reach {REQUIRED_CALL}() through {GATE_MODULE_NAME}, or call "
        "it and throw the answer away: "
        + "; ".join(f"line {line} ({tok})" for line, tok in hits)
        + " -- this is outside LANE-GM's write zone, so the fix is a letter "
        "to chief/LANE-B (this tripwire only widened the SCAN, per COO-"
        "DECISION 20260905_2051 item 3's rm-rf lesson applied the other way: "
        "read another lane's file freely, never edit it)"
    )


def test_field_mobs_scan_is_read_only_by_construction():
    """Pinned so a later round cannot quietly turn the D10 widening into a
    write.  The whole file's zone declaration already says "reads modules
    and edits none"; this asserts the one call this test makes against
    ``FIELD_MOBS_PATH`` is exactly the read-only helper every other file in
    the scan already goes through, not a bespoke open() this test invented
    for itself."""
    tree = ast.parse(
        inspect.getsource(test_field_mobs_is_scanned_for_p2_colour_tokens_read_only)
    )
    calls_on_path = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "FIELD_MOBS_PATH"
    ]
    assert calls_on_path == ["exists"], (
        f"expected FIELD_MOBS_PATH.exists() as the only direct call on the "
        f"path; found {calls_on_path} -- a write method here would defeat "
        "the read-only guarantee this test exists to pin"
    )


def test_npc_attr_composer_discovery_finds_the_known_composers():
    """Pinned so silent discovery breakage (a rename, a moved directory, the
    identifier disappearing from a docstring) is caught here rather than by
    a future round wondering why a composer stopped being scanned.

    Both files are named explicitly ONLY in this assertion -- the scan
    itself (below) never hardcodes either path, per COO-DECISION
    ``20260906_0255`` item 2."""
    found = _npc_attr_composer_files()
    assert found, "the NPCAttr discovery found nothing -- it is broken"
    assert FIELD_MOBS_PATH in found
    assert (NPC_ATTR_COMPOSER_ROOT / "mob_viewer_link.py") in found
    assert GM_ZONE not in {p.parent for p in found}, (
        "GM_ZONE is already scanned in full by the zone test above -- a "
        "non-recursive glob() double-counting it would just be noise"
    )


def test_npc_attr_composer_files_are_scanned_for_p2_colour_tokens_read_only():
    """The generalised D10: every module this round's discovery names, not
    only ``field_mobs.py``, owes the same obligation ``field_mobs.py`` does.

    Same shape as ``test_field_mobs_is_scanned_for_p2_colour_tokens_read_
    only`` above, run over the whole discovered set so a red names every
    offending file at once rather than one lane finding out about a second
    offender from a later round.  A red here is, exactly like a
    ``field_mobs.py`` red, an escalation letter to whichever lane owns the
    file -- never a same-round edit to it from here.
    """
    offenders, unscannable = [], []
    for path in _npc_attr_composer_files():
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
        "a discovered NPCAttr composer could not be scanned, so this gate "
        "proved nothing about it: " + " | ".join(unscannable)
    )
    assert not offenders, (
        "P-2 colour tokens appear in executable code in a module that "
        f"composes NPCAttr bytes, never reaching {REQUIRED_CALL}() through "
        f"{GATE_MODULE_NAME}, or calling it and throwing the answer away: "
        + " | ".join(offenders)
        + " -- this is outside LANE-GM's write zone for every file this "
        "scan can find, so the fix is a letter to whichever lane owns the "
        "file, never an edit to it from here."
    )


def test_the_composer_scan_has_never_fired_against_a_real_module():
    """Same shape as ``test_the_scan_visits_real_files_and_says_it_has_
    never_fired`` for ``GM_ZONE``, applied to the wider, unaudited net
    :func:`_npc_attr_composer_files` casts (pf-adversary, round ``xfeizd``,
    finding 3): every discovered file returns zero P-2 token hits today, so
    the ``offenders.append(...)`` branch in the test above has never run
    against real code, and the header has to keep saying so."""
    files = _npc_attr_composer_files()
    assert files, "the composer discovery found nothing -- it is broken"
    hit = [
        p.relative_to(ROOT).as_posix()
        for p in files
        if _token_hits(_read(p))
    ]
    doc = pathlib.Path(__file__).read_text(encoding="utf-8").split('"""')[1]
    if not hit:
        assert "never fired against a real file either, today" in doc, (
            "while nothing the composer scan finds trips it, the header "
            "must keep saying so"
        )


def test_npc_attr_composer_discovery_is_read_only_by_construction():
    """Mirrors ``test_field_mobs_scan_is_read_only_by_construction``, and
    inherits its exact blind spot: this only sees calls of the shape
    ``x.method(...)``.  A bare-name call reached through
    ``from os import remove; remove(path)`` or through indirection
    (``getattr(path, "write_bytes")(...)``) would not appear in ``calls``
    at all (pf-adversary, round ``xfeizd``, reproduced this against a
    hand-built variant) -- so this pins "no attribute-call write appears in
    the source as written today", not "this function cannot write"."""
    tree = ast.parse(inspect.getsource(_npc_attr_composer_files))
    calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert set(calls) <= {"glob", "read_text", "search", "append"}, (
        f"expected only glob()/read_text()/search()/list.append() inside "
        f"the discovery function; found {calls} -- an attribute-call write "
        "here would defeat the read-only guarantee this test exists to pin "
        "(see this test's own docstring for what it does not catch)"
    )


def test_the_folded_pass_does_not_mistake_a_gate_citation_for_a_violation():
    """Regression: this exact shape (an assigned string constant that cites
    ``gm/name_color_gate.py`` by name, the right thing for a caller to do)
    tripped the folded-string fallback before this round scrubbed the gate
    identifier from it too, because ``mob_viewer_link.py`` -- newly in scope
    via ``_npc_attr_composer_files`` -- contains exactly this pattern
    (``OTHER_ACTORATTR_LINK_AT_0X98``) and nothing else that names a P-2
    token in executable code."""
    source = (
        _IMPORT
        + 'CROSS_REF = (\n    "see gm/name_color_gate.py for the other +0x98"\n)\n'
    )
    assert _token_hits(source) == [], (
        "a string that merely cites the gate module's filename must not "
        "read as a P-2 colour token -- the folded-string fallback must "
        "scrub the gate identifier exactly as the primary pass does"
    )


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


_IMPORT = "from pirateforce_foundation.gm import name_color_gate\n"
_VERDICT = "name_color_gate.p2_color_wiring_verdict()"


@pytest.mark.parametrize(
    "source, expected",
    [
        (_IMPORT + f"if {_VERDICT}.allowed:\n    paint()\n", True),
        (f"if {_VERDICT}.allowed:\n    paint()\n", False),               # no import
        (_IMPORT + "def p2_color_wiring_verdict():\n    return 1\n"
         "if p2_color_wiring_verdict().allowed:\n    paint()\n", False),  # its own
        (_IMPORT + "x = name_color_gate.p2_color_wiring_verdict\n", False),  # not a call
    ],
    ids=["real", "no-import", "shadowed", "bare-name"],
)
def test_only_a_real_call_through_the_gate_counts(source, expected):
    assert _consults_the_refusal(source) is expected


# --------------------------------------------------------------------------
# the RESULT tier: a value that is thrown away consulted nothing
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body, expected",
    [
        (f"{_VERDICT}\n", False),                                        # bare statement
        (f"({_VERDICT})\n", False),                                      # parenthesised
        (f"{_VERDICT},\n", False),                                       # ONE trailing comma
        (f"[{_VERDICT}]\n", False),                                      # wrapped in a list
        (f"{_VERDICT}.allowed\n", False),                                # read, then dropped
        (f"{_VERDICT}.reason()\n", False),                               # method, dropped
        (f"not {_VERDICT}\n", False),                                    # negated, dropped
        (f'f"{{{_VERDICT}}}"\n', False),                                 # f-string, dropped
        (f"lambda: {_VERDICT}\n", False),                                # never even runs
        (f"[x for x in [{_VERDICT}]]\n", False),                         # comprehension
        (f"async def f():\n    await {_VERDICT}\n", False),              # awaited, dropped
        (f"async def f():\n    (await {_VERDICT}),\n", False),           # awaited, comma'
        (f"assert {_VERDICT}.allowed is False\n", True),
        (f"if {_VERDICT}.allowed:\n    paint()\n", True),
        (f"raise RuntimeError({_VERDICT}.reason())\n", True),
        (f"def f():\n    return {_VERDICT}\n", True),
        (f"v = {_VERDICT}\nif v.allowed:\n    paint()\n", True),
        (f"_require_p2({_VERDICT})\n", True),                            # zone house idiom
        (f"self._verdict = {_VERDICT}\n", True),                         # attribute target
        (f"allowed, blockers, evidence = {_VERDICT}\n", True),           # tuple unpack
        (f"with {_VERDICT} as v:\n    pass\n", True),                    # with-item
        (f"for b in {_VERDICT}.blockers:\n    pass\n", True),            # for iterable
        (f"@guard({_VERDICT})\ndef paint():\n    pass\n", True),         # decorator
        (f"log.info({_VERDICT}.reason())\n", True),                      # kept, then logged
    ],
    ids=[
        "bare-statement",
        "parenthesised-bare-statement",
        "trailing-comma",
        "wrapped-in-a-list",
        "attribute-then-dropped",
        "method-then-dropped",
        "negated",
        "f-string",
        "lambda-body",
        "comprehension",
        "awaited-bare-statement",
        "awaited-then-comma",
        "assert",
        "if-test",
        "raise",
        "return",
        "assigned",
        "require-helper",
        "attribute-target",
        "tuple-unpack",
        "with-item",
        "for-iterable",
        "decorator",
        "logged",
    ],
)
def test_a_discarded_verdict_is_not_a_consultation(body, expected):
    """A value thrown away fails, however much syntax hides the throw.

    The rule reads the STATEMENT: a bare expression statement discards
    everything inside it, so a trailing comma, a list, an attribute read, an
    f-string or a lambda body cannot rescue a call.  The first version of
    this rule looked only at the Expr's direct value, and pf-adversary
    defeated the whole round with one comma (second pass, D1).

    The rescue that stays is handing the value to another function: the
    ``require-helper`` and ``logged`` rows are this zone's own idioms
    (``gm/commands.py:321``, ``gm/teleport_wire.py:346``), and red-lighting
    them is how the FIRST design of this round died (first pass, D1).
    """
    assert _consults_the_refusal(_IMPORT + body) is expected


def test_one_kept_call_does_not_launder_the_discarded_ones():
    """``all``, not ``any``.  A throwaway binding at module scope must not buy
    a discarded call at the site that matters (pf-adversary, second pass,
    D5)."""
    laundered = _IMPORT + (
        f"_BOOT = {_VERDICT}\n"
        "def paint(actor):\n"
        f"    {_VERDICT}\n"
        "    actor.style = 1\n"
    )
    assert not _consults_the_refusal(laundered)
    kept = laundered.replace(f"    {_VERDICT}\n", f"    if {_VERDICT}.allowed:\n        return\n")
    assert _consults_the_refusal(kept)


@pytest.mark.parametrize(
    "source, expected",
    [
        (_IMPORT + f"match {_VERDICT}:\n    case _:\n        pass\n", True),
        (_IMPORT + f"try:\n    {_VERDICT}\n"
         "except name_color_gate.NameColorGateError:\n    pass\n", False),
        (_IMPORT + "async def p2_color_wiring_verdict():\n    return 1\n"
         f"async def f():\n    v = await p2_color_wiring_verdict()\n    return v\n", False),
    ],
    ids=["match-subject-is-kept", "try-except-reads-as-a-discard", "async-shadow"],
)
def test_the_judgement_calls_are_pinned_where_a_reader_can_see_them(source, expected):
    """Three answers this rule OWES a reader, fixed here rather than left to
    be rediscovered:

    * a ``match`` subject keeps the value -- ``case _`` then ignoring it is
      the same class as consulting and disobeying, which this file never
      claimed to catch;
    * ``try: verdict() / except ...`` reads as a DISCARD.  It is a real
      consultation only if the gate RAISES, and today it returns.  If that
      ever changes, ``_is_discarded`` changes with it;
    * an ``async def`` of the same name shadows the gate exactly as a ``def``
      does -- the half of the shadowing guard nothing exercised before.
    """
    assert _consults_the_refusal(source) is expected


def test_the_scan_visits_real_files_and_says_it_has_never_fired():
    """Two things nothing else notices.

    A zone scan that silently returned nothing would make every green above
    meaningless, so the file list is asserted non-empty.  And today NO module
    under ``gm/`` other than the gate names a P-2 token in executable code,
    so the whole rule has never run against a real file -- the header has to
    keep saying so (pf-adversary, second pass, D3).
    """
    files = _zone_files()
    assert len(files) > 5, "the zone scan found almost nothing -- it is broken"
    assert GATE_MODULE_PATH in files
    hit = [
        p.relative_to(ROOT).as_posix()
        for p in files
        if p != GATE_MODULE_PATH and _token_hits(_read(p))
    ]
    doc = pathlib.Path(__file__).read_text(encoding="utf-8").split('"""')[1]
    if not hit:
        assert "never run against a real module" in doc, (
            "while nothing in the zone trips it, the header must keep saying "
            "the rule is prospective"
        )


@pytest.mark.parametrize(
    "body",
    [
        f"if {_VERDICT}:\n    paint()\n",                     # truthy: body always runs
        f"def _never_called():\n    return {_VERDICT}\n",     # dead code
        f"if False:\n    assert {_VERDICT}.allowed\n",        # unreachable consult
        f"if {_VERDICT}.allowed:\n    pass\npaint()\n",      # consults, then disobeys
    ],
    ids=["tautology", "dead-code", "unreachable", "disobedient"],
)
def test_the_holes_this_rule_does_not_close_are_witnessed_not_asserted(body):
    """Each of these PASSES the tripwire, and each is named in the header.

    A guard whose limits live only in prose gets cited for more than it
    proves.  ``P2ColorWiringVerdict`` defines no ``__bool__``, so
    ``if p2_color_wiring_verdict():`` is a tautology whose body always runs
    -- this file grades it green, on purpose, rather than pretend otherwise.
    """
    assert _consults_the_refusal(_IMPORT + body)
    assert gate.p2_color_wiring_verdict(), "the tautology row depends on this"
    doc = pathlib.Path(__file__).read_text(encoding="utf-8").split('"""')[1]
    for word in ("tautological", "OBEDIENCE", "dead code"):
        assert word in doc, f"the header stopped naming the hole: {word}"


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
