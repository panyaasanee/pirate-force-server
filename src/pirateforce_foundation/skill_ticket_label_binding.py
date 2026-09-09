"""Bind the action label an attended ticket names to the label the server
actually returns.

WHY THIS FILE EXISTS
--------------------
The frozen sender writes the action label of every queued action to the
operator's console as ``[G>] <label> (N bytes)``
(``current/pf_login_game_server_v141.py:7762``).  An attended ticket that
tells the operator to look for ``[G>] X`` is therefore making a claim ABOUT
THIS TREE: that some code path can return an action whose label is ``X``.

When that claim is wrong the ticket does not fail softly.  It fails the
whole run at the console step, on a working feature, on the owner's own
machine -- the most expensive place in the project to discover a typo.
``GT-307`` is the measured case: its step 4 tells the operator to look for
``[G>] LEARN_SKILL_RESULT_LOGIN``, and no path in ``runtime.py`` has ever
returned that label.  The label the login skill list really carries is
``SKILL_LIST_AT_LOGIN`` (``runtime.py:4110``).

COO-DECISION ``20260908_1943`` (to LANE-CS) ordered the binding measured by
a test rather than by eye, and ordered the TICKET fixed by its owner (K),
not the label in ``runtime.py`` changed back.  This module is the measuring
half of that order.

WHAT "BOUND" MEANS, AND WHY IT IS NOT STRING EQUALITY
-----------------------------------------------------
Some labels are composed at send time from a literal prefix and a runtime
number -- ``runtime.py:14063`` builds ``WORLD_CENSUS_INITIAL_<n><suffix>``
inside an f-string -- so a ticket that quotes a whole composed label
(``WORLD_CENSUS_INITIAL_108_SWEEP_8``) is quoting something no literal in
the file spells.  Equality would call that a defect and it is not one.
A claim is bound when the file holds a label-shaped literal that is the
claim, extends the claim, or is extended by it.  Both directions carry a
minimum length so that a short literal cannot vouch for an unrelated claim.

WHAT THIS MODULE DELIBERATELY DOES NOT DO
-----------------------------------------
It does not read a ticket to decide whether the ticket is right about
anything else, it does not edit a ticket (tickets belong to LANE-K), and it
does not resolve a label through a variable: a label that reaches the send
queue only through a name defined in another module is NOT in
``action_label_literals`` and a ticket quoting it would be reported unbound.
That is a false positive this module can produce, it has never produced one
on the shipped tickets (measured: 13 distinct claims, 11 bound), and the
fix when it does is to name the literal in ``runtime.py``, not to widen the
rule until it stops answering.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path


#: The label the login skill list carries.  One literal, quoted here so a
#: test can pin it without re-spelling it, and so a ticket writer has one
#: place to copy from.  Kept in step with ``runtime.py:4110`` by
#: ``tests/test_skill_ticket_label_binding.py``, which reads that file.
SKILL_LIST_AT_LOGIN_ACTION_LABEL = "SKILL_LIST_AT_LOGIN"

#: The name ``GT-307`` step 4 quotes instead.  It is not a label; it is the
#: defect, kept as data so the test that measures it does not have to spell
#: it in an assertion message.
GT307_UNBOUND_CONSOLE_CLAIM = "LEARN_SKILL_RESULT_LOGIN"

#: Screaming snake case, whole string.  A label-shaped literal.
_LABEL_SHAPE = re.compile(r"\A[A-Z][A-Z0-9]*(?:_[A-Z0-9]*)*\Z")

#: ``[G>] LABEL`` as an attended ticket writes it: optionally backticked,
#: optionally followed by a placeholder (``<RUNG>``, ``...``) that the regex
#: stops before rather than swallows.
_CONSOLE_CLAIM = re.compile(r"\[G>\]\s*`?([A-Z][A-Z0-9_]*)")

#: Below this many characters a prefix relation is not evidence of
#: composition, only of a shared word.
_MIN_PREFIX = 12


def runtime_source_path() -> Path:
    """The file whose action labels a ticket is making claims about."""
    return Path(__file__).resolve().parent / "runtime.py"


def _docstring_nodes(tree: ast.AST) -> set:
    """Every string constant that is a docstring, by identity.

    Prose is not code.  A label named in a docstring -- including this
    module's own docstring, which names the defect twice -- must not vouch
    for a ticket that quotes it.
    """
    found = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                   ast.ClassDef)
        ):
            continue
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            found.add(id(body[0].value))
    return found


def action_label_literals(source: str) -> frozenset:
    """Every label-shaped string literal the source can put in a label.

    Both plain constants and the literal parts of f-strings, because the
    composed labels are built the second way.  Docstrings are excluded, and
    so is anything shorter than eight characters or without an underscore:
    a bare ``SENT`` or ``OK`` is not a label and would vouch for anything
    that starts with it.
    """
    tree = ast.parse(source)
    skip = _docstring_nodes(tree)
    literals = set()

    def offer(value: str) -> None:
        if len(value) >= 8 and "_" in value and _LABEL_SHAPE.match(value):
            literals.add(value)

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in skip:
                offer(node.value)
        elif isinstance(node, ast.JoinedStr):
            for part in node.values:
                if (isinstance(part, ast.Constant)
                        and isinstance(part.value, str)):
                    offer(part.value)
    return frozenset(literals)


def console_label_claims(text: str) -> tuple:
    """The labels a ticket tells an operator to look for, in order, once each.

    Comments in this repository quote the console form too (``[G>] <label>``
    appears in ``runtime.py`` and in three lane modules), which is why the
    placeholder ``<label>`` is not matched: the pattern requires the first
    character to be an upper-case letter.
    """
    seen = []
    for match in _CONSOLE_CLAIM.finditer(text):
        claim = match.group(1)
        if claim not in seen:
            seen.append(claim)
    return tuple(seen)


def claim_is_bound(claim: str, literals) -> bool:
    """True when some literal can be the label the claim names.

    Three ways, and the two prefix directions are not symmetric in what
    they mean:

    * equal -- the ticket quotes the literal.
    * the claim extends a literal -- the label is composed at send time
      (``WORLD_CENSUS_INITIAL_`` + a count).
    * a literal extends the claim -- the ticket truncated the label, which
      attended tickets do when the tail is a number they cannot know.  This
      direction requires the break to land on an underscore so that
      ``MOB_COMBAT`` cannot vouch for itself against ``MOB_COMBAT_BAR``
      while naming no line the operator will ever see.
    """
    if claim in literals:
        return True
    for literal in literals:
        if len(literal) >= _MIN_PREFIX and claim.startswith(literal):
            return True
        if (len(claim) >= _MIN_PREFIX and literal.startswith(claim)
                and (claim.endswith("_") or literal[len(claim)] == "_")):
            return True
    return False


def unbound_claims(text: str, literals) -> tuple:
    """The claims in one ticket that no literal in the source can produce."""
    return tuple(
        claim for claim in console_label_claims(text)
        if not claim_is_bound(claim, literals)
    )


def audit_ticket_dir(directory, literals) -> dict:
    """``{ticket file name: unbound claims}`` for every ticket that has one.

    An absent directory answers ``{}`` rather than raising: the gate runs
    this repository with no ``pf_bridge`` beside it, and "there are no
    tickets here" is a real answer, not an error.  Tickets with no unbound
    claim are left out so the mapping reads as a defect list.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return {}
    report = {}
    for path in sorted(directory.glob("GT-*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        unbound = unbound_claims(text, literals)
        if unbound:
            report[path.name] = unbound
    return report
