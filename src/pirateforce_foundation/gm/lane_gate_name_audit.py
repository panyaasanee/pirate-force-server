"""Make a lane_hooks name that two files must agree on FAIL LOUDLY.

The defect class, measured on ``origin/main`` on 2026-09-03, not reasoned
about
---------------------------------------------------------------------------
``lane_hooks`` couples a call site to a lane module through a bare string
that nothing checks.  ``lane_hooks/__init__.py`` says so itself at its
``hook()`` decorator: the point name is something "the call site and the
module agree on out of band".  Two such strings exist, and both fail the
same way -- SILENTLY, in the direction that looks like "the feature is
switched off":

1. ``module_production_allowed("<name>")``.  Its own docstring records the
   shape on purpose: "the closed answer is indistinguishable from the typo".
   Correct as a fail-closed rule, and expensive as an operating condition.
2. ``@hook("<point>")`` versus ``fire("<point>")``.  A hook registered for a
   point no ``fire()`` names is imported, gated, reported as REGISTERED on
   the console, and never runs.

WHAT IT COST.  LANE-B measured (``pf_bridge notes_to_chief/20260903_1450``,
and this lane re-measured it independently before writing a line of this
file) that ``runtime.py:5887`` asks::

    lane_hooks.module_production_allowed("lane_hooks.lane_b_mob_ai_tick")

``module_production_allowed`` prefixes any name that is not already fully
qualified, so that literal resolves to
``pirateforce_foundation.lane_hooks.lane_hooks.lane_b_mob_ai_tick`` -- a key
no module ever registers.  The answer is ``False`` on every frame, for
every player, since the branch landed.  The mob AI tick behind it has never
run once in production.  Re-measured by this lane on ``origin/main``
``9a14083``::

    module_production_allowed("lane_hooks.lane_b_mob_ai_tick")  -> False
    module_production_allowed("lane_b_mob_ai_tick")             -> True

WHAT ALREADY EXISTED, SAID BEFORE ANY CLAIM OF NOVELTY.  LANE-B landed
``test_the_tick_gate_is_reported_not_assumed`` -- grep that name; the file
it lives in is deliberately NOT written out here, because LANE-B's own
containment census counts every file under ``src/`` that so much as MENTIONS
its module's name, in prose as readily as in code, and the first draft of
this file put itself on that list and turned that lane's test red with a
docstring citation (measured this round).  The card pins THAT call site's
two answers and is written to go red the day chief corrects it.  This
module does not repeat it and does not replace it.
Three differences are the whole reason it is worth its lines: it is not
tied to one call site, so the NEXT lane to write this spelling is caught
without anyone thinking to add a card; it audits the hook-point half as
well, which no test in this repository did; and it does not have to be
edited when a call site is repaired.

AND ONE CORRECTION THIS FILE'S FIRST DRAFT NEEDED (pf-adversary, round
`lx4yib`, D6).  That draft claimed that requalifying LANE-GM's own
``runtime.py:6911`` literal the way ``:5887`` is spelled would "red no
test".  MEASURED, with the requalification actually applied: **24 tests
fail**, 23 of them pre-existing in ``test_gm_chat_command_dispatch_wiring.py``
and ``test_gm_chat_command_action.py``.  The claim was prose asserted
without opening the tests it described, and it was the sentence that
justified this module's placement.  The honest version: LANE-GM's chat
route is already well guarded against this specific spelling; the LANE-B
tick was not guarded at all; and what neither lane had is a check that
holds for a call site NOBODY has written yet.  That is what this is.

What this module does NOT claim
-------------------------------
* It does not decide whether a gate SHOULD be open.  A module whose
  ``production_allowed`` is genuinely ``False`` (``lane_a_choose_npc_scene1``
  today) is not a finding here.
* It does not re-implement ``module_production_allowed``'s qualification
  rule.  Copying those four lines here would be a second, unguarded copy of
  the very thing under audit, and it would agree with the bug rather than
  catch it.
* It does not read a private registry.
* It says nothing about GM status, and grants none.  Nothing here sends a
  byte, and nothing here prints.

Why the walkers parse instead of grepping, stated because this lane got it
wrong first
---------------------------------------------------------------------------
Drafting this module, this lane grepped ``fire\\(\\s*"[a-z_]+"`` across
``src/`` and concluded that ``vital_inbound_gm_run_command`` was a dead hook
-- a false alarm that would have gone into a letter.  The real call is
``runtime.py:7613``, where ``lane_hooks.fire(`` and its point name are on
DIFFERENT LINES.  A line-oriented search cannot answer this question.

AND PARSING ALONE IS NOT ENOUGH EITHER, which is the second thing this
lane got wrong.  The first draft matched ``fire(...)`` by BARE NAME
anywhere in the package.  pf-adversary (D2) measured both halves of what
that costs on a pirate-ship server, where ``fire`` is a more ordinary word
than ``hook``: an unrelated ``cannon.fire("vital_inbound_gm_run_command")``
made a genuinely dead LANE-GM hook report clean, and an unrelated
``cannon.fire()`` with no arguments disarmed the entire hook half and
turned another lane's file red with a message about hook points.  So every
call below is matched by RESOLUTION, not by name: the callee has to reach
the real ``lane_hooks`` package through the imports of the file it appears
in -- see :func:`_lane_hooks_bindings`.

Which answers the question pf-adversary closed that review with: what makes
this module's own coupling any better than the two it audits?  Nothing, as
long as it matched strings.  Now it matches through the same import graph
Python does, and the three attribute names it does depend on
(:data:`GATE_FUNCTION_NAME`, :data:`HOOK_DECORATOR_NAME`,
:data:`FIRE_FUNCTION_NAME`) are checked against the live package by
``tests/test_gm_lane_gate_name_audit.py``, so a rename in ``lane_hooks``
reds this audit instead of quietly leaving it auditing nothing.
"""
from __future__ import annotations

import ast
import subprocess
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from .. import lane_hooks

#: The tree the no-argument finding functions audit: the whole repository.
#:
#: The first draft scanned ``src/pirateforce_foundation`` only and called
#: that "repository-wide" (pf-adversary D9).  ``tools/`` holds a hundred
#: scripts and nothing stops a headless replay tool from reading the gate,
#: so the root is the repository and the exclusion below is explicit.
AUDIT_ROOT = Path(__file__).resolve().parents[3]

#: Top-level directories the audit does not read.  ``tests/`` is excluded
#: because a test that exercises a deliberately-wrong name is doing its job,
#: and reporting it would train a reader to ignore this module -- including
#: every synthetic defect in this module's own test file.
EXCLUDED_TOP_LEVEL = ("tests",)

#: The package directory a gate name has to reach.
LANE_HOOKS_PACKAGE = "lane_hooks"
LANE_HOOKS_DIR = Path(lane_hooks.__file__).resolve().parent

#: Every lane module is ``lane_<x>_*``; this lane's are ``lane_gm_*``.
LANE_MODULE_PREFIX = "lane_"
LANE_GM_MODULE_PREFIX = "lane_gm_"

#: The three ``lane_hooks`` attributes this audit follows, and the keyword
#: each accepts for the string in question.  Both spellings are read: the
#: real ``fire()`` already passes ``session=``/``payload=`` by keyword, so
#: ``fire(point="...")`` is an ordinary thing for a call site to write, and
#: the first draft reported that plain literal as "not a string literal"
#: (pf-adversary D3).
GATE_FUNCTION_NAME = "module_production_allowed"
GATE_KEYWORD = "module_name"
HOOK_DECORATOR_NAME = "hook"
FIRE_FUNCTION_NAME = "fire"
POINT_KEYWORD = "point"

#: The module-level flag ``lane_hooks`` reads to decide whether a lane's
#: hooks survive discovery.
PRODUCTION_FLAG_NAME = "production_allowed"

#: A gate literal whose last dotted segment names no module in
#: ``lane_hooks/``.  Nothing can ever open this gate.
FINDING_NAMES_NO_MODULE = "gate_literal_names_no_lane_module"

#: A gate literal whose module is cleared under its bare stem and shut
#: under the literal as written.  The ``runtime.py:5887`` shape: the owner
#: switched the lane on and the call site cannot see it.
FINDING_SPELLING_UNREACHABLE = "gate_literal_spelling_reaches_no_registry_key"

#: The module's source declares ``production_allowed`` truthy and the
#: resolver still refuses it under BOTH spellings -- so the module never
#: reached the registry at all (an import failure, which ``_discover()``
#: reports on the console and then forgets).  Added after pf-adversary (D7)
#: measured that the first draft reported this state as NOTHING, which is
#: exactly the silence this module exists to break.
FINDING_DECLARED_ALLOWED_BUT_UNREGISTERED = (
    "lane_module_declares_production_allowed_but_the_registry_refuses_it"
)

#: A point a lane module registers a hook for that no ``fire()`` names.
FINDING_HOOK_POINT_NEVER_FIRED = "hook_point_no_fire_call_names"

#: A module declared a point as deliberately never fired, and the tree
#: disagrees: either something now fires it, or THAT SAME MODULE no longer
#: registers it.  The inverse guard, and the reason the declaration is a
#: declaration rather than a mute button.
FINDING_STALE_NEVER_FIRED_DECLARATION = "declared_never_fired_point_is_stale"

#: A ``registered_but_not_fired`` assignment this audit cannot read.  Not
#: silence: an unreadable declaration silences nothing, and says so.
FINDING_UNREADABLE_DECLARATION = "registered_but_not_fired_is_not_a_literal_tuple"

#: Returned ALONGSIDE any other finding when the scan met a ``fire()`` or
#: ``hook()`` whose point argument is not a string literal.  A dynamic point
#: name makes "no ``fire()`` names this point" unanswerable by reading the
#: source, and answering it anyway would put a lane's live hook on a dead
#: list.
FINDING_UNDECIDABLE_DYNAMIC_POINT = "hook_point_audit_undecidable_dynamic_name"

#: The module-level name a lane module uses to declare that it registers a
#: hook for a point NOTHING fires, on purpose.
#:
#: SCOPED TO THE DECLARING FILE.  A declaration silences a registration in
#: its own module and nowhere else, and the stale guard looks for the
#: registration in that same module.  The first draft keyed on the point
#: name alone, and pf-adversary (D4) measured all three consequences: one
#: lane could silence another lane's dead hook, a cross-lane registration of
#: an already-declared point went unreported, and the promised "reds when
#: the module stops registering it" guard stayed asleep as long as any other
#: module registered the point.
DECLARATION_NAME = "registered_but_not_fired"


@dataclass(frozen=True)
class SourceSite:
    """One thing the walker found, located for a human, not for a machine."""

    path: str
    line: int
    #: ``None`` when the value is not a plain string literal.  Kept as a
    #: site rather than dropped: an unreadable argument is a fact about the
    #: audit's reach, and the finding functions act on it.
    literal: str | None

    def where(self) -> str:
        return f"{self.path}:{self.line}"


@dataclass(frozen=True)
class Finding:
    kind: str
    site: SourceSite
    detail: str

    def line(self) -> str:
        return f"{self.kind} {self.site.where()} {self.detail}"


@dataclass(frozen=True)
class Scan:
    """Everything ONE pass over a source tree learned.

    One object, and the public functions below share a single pass through
    :func:`audit_report`, because the first draft walked the tree three
    times while its own docstring claimed otherwise (pf-adversary D9).
    """

    gate_calls: tuple[SourceSite, ...]
    hook_registrations: tuple[SourceSite, ...]
    fire_calls: tuple[SourceSite, ...]
    #: ``registered_but_not_fired`` entries, one site per declared point.
    #: A site whose ``literal`` is ``None`` is an assignment this audit
    #: could not read.
    never_fired_declarations: tuple[SourceSite, ...]


# ---------------------------------------------------------------------------
# Resolving a call to the real package, rather than matching its name.
# ---------------------------------------------------------------------------


def _parse(source: str) -> ast.Module:
    """``ast.parse`` without re-emitting other files' compile warnings.

    Several modules in this repository carry regex strings with invalid
    escapes; Python already warns about those when it compiles them, and an
    audit that re-parses the whole tree would repeat every one of those
    warnings on every scan (measured: 24 in one test file).  Nothing is
    hidden -- a SyntaxError still propagates to the caller, which decides.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse(source)


def _dotted(node: ast.expr) -> str | None:
    """``a.b.c`` for a Name/Attribute chain, else ``None``."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def _lane_hooks_bindings(
    tree: ast.Module, inside_package: bool
) -> tuple[set[str], dict[str, str]]:
    """What names in THIS file reach the ``lane_hooks`` package.

    Returns ``(module_names, attribute_names)``:

    * ``module_names`` -- local names that refer to the package itself, so
      ``<name>.fire(...)`` is a real call.  ``import x.lane_hooks``,
      ``import x.lane_hooks as lh``, ``from x import lane_hooks`` and the
      relative forms all land here.
    * ``attribute_names`` -- ``{local name: package attribute}`` for
      ``from ...lane_hooks import fire``, and -- only when the file is
      itself inside the package -- for ``from . import hook``, which is how
      every ``lane_<x>_*.py`` in this repository gets its decorator.

    A file that binds nothing contributes nothing, which is the whole point:
    ``cannon.fire(...)`` in a module that has never imported lane_hooks is
    not a hook point, and the first draft could not tell.
    """
    module_names: set[str] = set()
    attribute_names: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[-1] != LANE_HOOKS_PACKAGE:
                    continue
                # `import a.b.lane_hooks` binds `a`, and the call is written
                # `a.b.lane_hooks.fire(...)`; the dotted match below looks at
                # the LAST segment, so the package name itself is what has to
                # be known here.  `import a.b.lane_hooks as lh` binds `lh`.
                module_names.add(alias.asname or LANE_HOOKS_PACKAGE)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            tail = module.split(".")[-1] if module else ""
            for alias in node.names:
                if alias.name == LANE_HOOKS_PACKAGE:
                    # `from pirateforce_foundation import lane_hooks`, and
                    # the relative `from . import lane_hooks`.
                    module_names.add(alias.asname or alias.name)
                elif tail == LANE_HOOKS_PACKAGE:
                    # `from ...lane_hooks import fire, hook`.
                    attribute_names[alias.asname or alias.name] = alias.name
                elif not module and inside_package:
                    # `from . import hook`, which is how every lane module in
                    # this repository gets its decorator.
                    attribute_names[alias.asname or alias.name] = alias.name
    return module_names, attribute_names


def _resolves_to(
    node: ast.Call,
    attribute: str,
    module_names: set[str],
    attribute_names: dict[str, str],
) -> bool:
    """Is this call the package's ``attribute``, as this file imports it?"""
    func = node.func
    if isinstance(func, ast.Attribute):
        if func.attr != attribute:
            return False
        dotted = _dotted(func.value)
        return dotted is not None and dotted.rsplit(".", 1)[-1] in module_names
    if isinstance(func, ast.Name):
        return attribute_names.get(func.id) == attribute
    return False


def _string_argument(node: ast.Call, keyword: str) -> str | None:
    """The first positional argument, or the named keyword, as a literal."""
    candidate: ast.expr | None = None
    if node.args:
        candidate = node.args[0]
    else:
        for entry in node.keywords:
            if entry.arg == keyword:
                candidate = entry.value
                break
    if isinstance(candidate, ast.Constant) and isinstance(candidate.value, str):
        return candidate.value
    return None


# ---------------------------------------------------------------------------
# Walking the tree.
# ---------------------------------------------------------------------------


def _tracked_python_sources(root: Path) -> Iterator[Path]:
    """Every ``.py`` git would ship from ``root``, or every ``.py`` on disk.

    ``git ls-files`` FIRST, and this is not a preference.  pf-adversary
    (D9) changed this audit's verdict in both directions with an untracked
    scratch file, which is the failure
    ``tests/test_gm_source_is_cp874_safe.py`` already records for this
    repository: "green about an editor buffer, red about the thing that
    would be pushed".  A tree that is not a git checkout -- every synthetic
    tree in the tests, and any exported tarball -- falls back to walking
    the disk, which is the only answer available there.

    THE PRICE, SAID PLAINLY: a file its author has not staged is invisible
    to this audit locally, and visible on the gate, where every file is
    tracked.  That is the right way round -- the gate grades what would be
    pushed -- but a lane writing a new gate call sees this audit's verdict
    only after ``git add``.  Measured on this module's own round: before
    staging, the report listed four unauditable sites; after, six.
    """
    listed: list[str] | None = None
    try:
        top = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Only trust the listing when `root` IS the checkout root; a temp
        # directory that happens to sit inside somebody's repository would
        # otherwise be answered with that repository's file list.
        if top.returncode == 0 and Path(top.stdout.strip()) == root:
            result = subprocess.run(
                ["git", "-C", str(root), "ls-files", "--", "*.py"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                listed = result.stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        listed = None
    if listed is None:
        candidates: Iterable[Path] = sorted(root.rglob("*.py"))
    else:
        candidates = (root / entry for entry in sorted(listed))
    for path in candidates:
        if "__pycache__" in path.parts:
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:  # pragma: no cover - both branches are rooted
            continue
        if relative.parts and relative.parts[0] in EXCLUDED_TOP_LEVEL:
            continue
        if path.is_file():
            yield path


def _declaration_sites(tree: ast.Module, where: str) -> list[SourceSite]:
    """Read a module-level ``registered_but_not_fired`` assignment.

    MODULE LEVEL ONLY.  A declaration nested inside a function or a class
    would be invisible to any reader looking for the lane's switches at the
    top of the file, and this audit refuses to honour a silencer that is
    hard to find.

    An assignment whose value is not a non-empty tuple/list of plain string
    literals yields ONE site with ``literal=None``, which becomes
    :data:`FINDING_UNREADABLE_DECLARATION`.  It never yields nothing: a
    declaration this audit cannot read must not silence anything, and must
    not be mistaken for an absent declaration either.
    """
    sites: list[SourceSite] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets: list[ast.expr] = list(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        else:
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == DECLARATION_NAME
            for target in targets
        ):
            continue
        if not isinstance(value, (ast.Tuple, ast.List)) or not value.elts:
            sites.append(SourceSite(where, node.lineno, None))
            continue
        points = [
            element.value
            for element in value.elts
            if isinstance(element, ast.Constant)
            and isinstance(element.value, str)
        ]
        if len(points) != len(value.elts):
            sites.append(SourceSite(where, node.lineno, None))
            continue
        sites.extend(SourceSite(where, node.lineno, point) for point in points)
    return sites


def _declares_production_allowed(source: str) -> bool:
    """Does this module's SOURCE set ``production_allowed`` truthy?

    Read from source rather than by importing, because the state this
    answers a question about -- a module that fails to import -- is exactly
    the state where importing it is not available.
    """
    try:
        tree = _parse(source)
    except SyntaxError:
        return False
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets: list[ast.expr] = list(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        else:
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == PRODUCTION_FLAG_NAME
            for target in targets
        ):
            continue
        if isinstance(value, ast.Constant):
            return bool(value.value)
        return False
    return False


def scan_sources(root: Path) -> Scan:
    """Parse every shipped ``.py`` under ``root`` and collect four shapes.

    ``root`` is required, with no default, on purpose: the no-argument
    finding functions below bind :data:`AUDIT_ROOT` themselves, so a mutant
    that points that constant somewhere empty reds the non-vacuity tests
    instead of quietly auditing nothing.

    A file that does not parse is skipped rather than raising.  A repository
    that cannot be imported has louder problems than this audit, and a
    SyntaxError here would take the whole suite down with a message about
    the wrong thing.
    """
    gate_calls: list[SourceSite] = []
    hook_registrations: list[SourceSite] = []
    fire_calls: list[SourceSite] = []
    declarations: list[SourceSite] = []
    root = root.resolve()
    for path in _tracked_python_sources(root):
        try:
            tree = _parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        where = str(path.relative_to(root)).replace("\\", "/")
        inside_package = path.parent.name == LANE_HOOKS_PACKAGE
        if inside_package:
            declarations.extend(_declaration_sites(tree, where))
        module_names, attribute_names = _lane_hooks_bindings(
            tree, inside_package
        )
        if not module_names and not attribute_names:
            # AN OPTIMISATION, NOT THE GUARD, and saying so matters: deleting
            # this line changes no verdict, because `_resolves_to` still
            # refuses every call in a file that binds nothing.  A mutant on
            # it therefore survives on purpose.  The guard that a mutant
            # DOES kill is the dotted check inside `_resolves_to` -- see
            # `test_an_unrelated_fire_in_a_file_that_DOES_import_lane_hooks`.
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for attribute, keyword, sink in (
                (GATE_FUNCTION_NAME, GATE_KEYWORD, gate_calls),
                (FIRE_FUNCTION_NAME, POINT_KEYWORD, fire_calls),
                (HOOK_DECORATOR_NAME, POINT_KEYWORD, hook_registrations),
            ):
                if _resolves_to(node, attribute, module_names, attribute_names):
                    sink.append(
                        SourceSite(
                            where,
                            node.lineno,
                            _string_argument(node, keyword),
                        )
                    )
                    break
    return Scan(
        tuple(gate_calls),
        tuple(hook_registrations),
        tuple(fire_calls),
        tuple(declarations),
    )


# ---------------------------------------------------------------------------
# The gate half.
# ---------------------------------------------------------------------------


def _classify_gate_literal(
    *,
    resolver_answers_for_literal: bool,
    resolver_answers_for_stem: bool,
    module_file_exists: bool,
    module_declares_allowed: bool,
) -> str | None:
    """Which finding these four facts mean, or ``None`` for no finding.

    A pure function of facts, so every combination is testable without a
    repository in a particular state.  The facts themselves are gathered by
    :func:`gate_name_findings` from the REAL resolver and the REAL directory
    -- this function never learns a name and never qualifies one.

    THE RESOLVER IS ASKED FIRST, AND THAT ORDER IS THE FIX FOR THIS
    FUNCTION'S FIRST DRAFT.  That draft consulted the filesystem before
    either probe, so one ``is_file()`` overrode both.  pf-adversary (D1)
    measured the cost: ``lane_hooks`` discovers with ``pkgutil.iter_modules``,
    which yields PACKAGES too, so a lane whose next feature is a directory
    (``lane_hooks/lane_gm_big_feature/__init__.py``) got a working gate
    reported as ``names_no_lane_module`` -- and it was this lane's own
    asserted test that went red over a call site that worked.  A literal the
    resolver opens is never a finding now, whatever the disk says.

    Deliberately NOT a finding: everything false while the file exists and
    declares nothing.  That is a module whose ``production_allowed`` is off,
    which is a decision.
    """
    if resolver_answers_for_literal:
        return None
    if resolver_answers_for_stem:
        return FINDING_SPELLING_UNREACHABLE
    if not module_file_exists:
        return FINDING_NAMES_NO_MODULE
    if module_declares_allowed:
        return FINDING_DECLARED_ALLOWED_BUT_UNREGISTERED
    return None


def _stem(literal: str) -> str:
    return literal.rsplit(".", 1)[-1]


def _module_source(stem: str) -> str | None:
    """The source of the lane module ``stem``, module or package, or None."""
    for candidate in (
        LANE_HOOKS_DIR / f"{stem}.py",
        LANE_HOOKS_DIR / stem / "__init__.py",
    ):
        if candidate.is_file():
            try:
                return candidate.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return ""
    return None


def _gate_findings(scan: Scan) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for site in scan.gate_calls:
        if site.literal is None:
            continue
        stem = _stem(site.literal)
        source = _module_source(stem)
        kind = _classify_gate_literal(
            resolver_answers_for_literal=lane_hooks.module_production_allowed(
                site.literal
            ),
            resolver_answers_for_stem=lane_hooks.module_production_allowed(
                stem
            ),
            module_file_exists=source is not None,
            module_declares_allowed=(
                source is not None and _declares_production_allowed(source)
            ),
        )
        if kind is None:
            continue
        findings.append(
            Finding(kind, site, f"{site.literal!r} (lane module {stem!r})")
        )
    return tuple(findings)


def gate_name_findings() -> tuple[Finding, ...]:
    """Every ``module_production_allowed`` literal that reaches nothing.

    Repository-wide, and REPORTING ONLY -- no test asserts this is empty
    today, because it is not: ``runtime.py:5887`` is chief's file and
    chief's fix is in flight (``pf_bridge notes_to_chief/20260903_1648``).
    Pinning it here would go red the moment that fix lands, which would
    punish the repair.  The asserted subset is
    :func:`gate_findings_in_lane_gm_scope`.

    Call sites whose argument is not a string literal are not findings and
    not silence either: they are reported by
    :func:`unauditable_gate_call_sites`.
    """
    return _gate_findings(scan_sources(AUDIT_ROOT))


def unauditable_gate_call_sites() -> tuple[SourceSite, ...]:
    """Gate calls whose argument this audit cannot read from source.

    Two kinds on ``main`` today, and neither is a defect:

    * ``runtime.py``, ``gm/warp_chain_preflight.py`` and
      ``lane_hooks/lane_a_scene_census.py`` pass a ``.module`` attribute the
      lane_hooks tables filled in.  That is the SAFE shape -- the name came
      from the registry rather than from a human typing it.
    * This module's own two probes in :func:`_gate_findings`, which pass
      whatever literal they are auditing.  Listing them rather than
      excluding this file is deliberate: an audit that carves itself out of
      its own scan has one file nobody checks, and it would be this one.

    Named here so "no findings" is never mistaken for "every call site was
    checked" -- and see
    :func:`lane_gm_gate_literals` for the non-vacuity this does NOT provide.
    """
    return tuple(
        site
        for site in scan_sources(AUDIT_ROOT).gate_calls
        if site.literal is None
    )


def _owned_by_another_lane(stem: str) -> bool:
    """Is ``stem`` an existing lane module that is not this lane's?"""
    return (
        _module_source(stem) is not None
        and stem.startswith(LANE_MODULE_PREFIX)
        and not stem.startswith(LANE_GM_MODULE_PREFIX)
    )


def gate_findings_in_lane_gm_scope() -> tuple[Finding, ...]:
    """The findings this lane asserts on, and the scoping rule is the point.

    A repository-wide assertion inherits every other lane's current state:
    it can only be added at a moment when every lane happens to be clean,
    and it reds someone who did not write the line.  So this lane asserts on
    the complement instead -- every finding EXCEPT one attributable to
    another lane's existing module.

    NOT ``stem.startswith("lane_gm_")``, which is what the first draft used.
    pf-adversary (D8) measured that ``lanegm_chat_command``,
    ``lane_gmchat_command``, ``Lane_GM_chat_command`` and
    ``lane_gm_chat_command.py`` all fall outside that prefix -- so the
    assertion protected the spelling that was already right and let through
    the misspellings this module exists for.  Under the rule below every one
    of those is in scope, because none of them names an existing lane
    module at all; ``lane_hooks.lane_b_mob_ai_tick`` is out of scope because
    its stem names a real LANE-B module.
    """
    return tuple(
        finding
        for finding in gate_name_findings()
        if not _owned_by_another_lane(_stem(finding.site.literal or ""))
    )


def lane_gm_gate_literals() -> tuple[str, ...]:
    """The lane_gm gate literals the scan actually read.

    Exists so the assertion above cannot pass by having nothing to say.
    pf-adversary (D5) measured the hole: hoist ``runtime.py:6911``'s literal
    into a module constant and the chat gate goes dead, the scan sees only a
    ``Name`` node, the asserted subset empties, and every test in this
    lane's file still passes.  A test pins this non-empty, so that move reds
    something and a human has to look.
    """
    return tuple(
        site.literal
        for site in scan_sources(AUDIT_ROOT).gate_calls
        if site.literal is not None
        and _stem(site.literal).startswith(LANE_GM_MODULE_PREFIX)
    )


# ---------------------------------------------------------------------------
# The hook-point half.
# ---------------------------------------------------------------------------


def _dead_hook_findings(scan: Scan) -> tuple[Finding, ...]:
    # An unreadable declaration is reported in EVERY case, including the
    # refusal below.  A declaration nobody can read is a defect in the file
    # that wrote it, and it does not stop being one because some other file
    # made the dead-point question unanswerable.
    findings = [
        Finding(
            FINDING_UNREADABLE_DECLARATION,
            site,
            f"{DECLARATION_NAME} is not a non-empty tuple of string literals, "
            "so it silences nothing",
        )
        for site in scan.never_fired_declarations
        if site.literal is None
    ]
    undecidable = [
        site
        for site in scan.fire_calls + scan.hook_registrations
        if site.literal is None
    ]
    if undecidable:
        return tuple(findings) + tuple(
            Finding(
                FINDING_UNDECIDABLE_DYNAMIC_POINT,
                site,
                "point name is not a string literal, so no hook point in "
                "this tree can be graded from source",
            )
            for site in undecidable
        )
    fired = {site.literal for site in scan.fire_calls}
    # BOTH keyed by (file, point).  A declaration reaches its own module and
    # no other, and the stale guard looks for the registration in that same
    # module -- see DECLARATION_NAME for the three things the first draft's
    # global sets let through.
    registered = {
        (site.path, site.literal) for site in scan.hook_registrations
    }
    declared = {
        (site.path, site.literal)
        for site in scan.never_fired_declarations
        if site.literal is not None
    }
    findings.extend(
        Finding(
            FINDING_HOOK_POINT_NEVER_FIRED,
            site,
            f"{site.literal!r} is registered and no fire() call names it",
        )
        for site in scan.hook_registrations
        if site.literal not in fired
        and (site.path, site.literal) not in declared
    )
    # THE INVERSE.  A declaration whose premise has changed is worse than no
    # declaration: it is a silencer over a question nobody is asking any
    # more, and the next reader takes it for a live fact.
    findings.extend(
        Finding(
            FINDING_STALE_NEVER_FIRED_DECLARATION,
            site,
            f"{site.literal!r} is declared never-fired but is "
            + (
                "fired in this tree"
                if site.literal in fired
                else "registered by no hook in the declaring module"
            ),
        )
        for site in scan.never_fired_declarations
        if site.literal is not None
        and (
            site.literal in fired
            or (site.path, site.literal) not in registered
        )
    )
    return tuple(findings)


def dead_hook_point_findings() -> tuple[Finding, ...]:
    """Points a lane registers a hook for that no ``fire()`` call names.

    Refuses rather than guesses when any ``fire()`` or ``@hook()`` that
    resolves to the real package takes a non-literal point name: with one
    dynamic name in play, "no call names this point" stops being a
    source-readable fact, and a wrong entry on this list would send a lane
    hunting for a hook that fires perfectly well.  The refusal is itself a
    finding rather than an empty tuple, so it cannot be read as a clean
    bill, and an unreadable declaration is reported alongside it rather
    than swallowed by it.
    """
    return _dead_hook_findings(scan_sources(AUDIT_ROOT))


def audit_report() -> tuple[str, ...]:
    """One line per finding, for a letter or a console.  Never printed here.

    Nothing in this module prints.  A module that printed would need a
    consumer for its token (``COO 0846``), and this audit's consumer is a
    test, not a screen.  ONE scan feeds both halves.
    """
    scan = scan_sources(AUDIT_ROOT)
    return tuple(
        finding.line()
        for finding in _gate_findings(scan) + _dead_hook_findings(scan)
    )
