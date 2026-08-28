"""LANE-B: the expiry COO attached to the gate-2 shape rule is executable.

``COO-DECISION 20260829_0441`` approved ``bag_admission``'s shape rule for
gate 2 as an INTERIM and ordered its expiry written into the module (item 2).
Prose expires badly: a nonclaim that says "this is temporary" reads exactly
the same on the day it stopped being true.  These tests turn the two halves
of that expiry into things a run can fail on.

WHAT THIS FILE IS AND IS NOT.  It does not test the admission rule -- that is
``tests/test_bag_admission.py``, which enumerates the governed family.  It
tests that the RULE'S OWN SUNSET is still correctly described:

  1. the expiry condition is stated in the module, in both places a reader
     looks (the nonclaim tuple and a constant), and
  2. the condition is still UNMET, which is the only thing that entitles the
     shape rule to be on the production path at all.

If test 2 starts failing, nothing is broken -- it means ``store.py`` grew the
real INSERT and the counter advance, and the round that did it now owes the
replacement COO specified: delete ``_classify_against``, do not keep it as a
fallback.  Read the failure message, not just the red.

DELIBERATELY A SOURCE-TEXT TEST.  ``bag_admission`` must not import ``store``
(it sits on the character-select path and pulling the store in to read a
boolean would be a worse defect than the one this guards).  So the second
half is measured the only honest way available from here: over the source of
``mob_pickup`` and ``store``, naming the tokens it looks for so a reader can
grep the same thing by hand.
"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import bag_admission


_SRC = Path(bag_admission.__file__).resolve().parent


def _source(module_name: str) -> str:
    return (_SRC / (module_name + ".py")).read_text(encoding="utf-8")


def test_nonclaim_8_states_the_expiry_and_names_the_replacement() -> None:
    """The tuple a console reader sees carries the sunset, not just the rule.

    Pinned by content and not by index: a later round is free to renumber,
    but it may not quietly drop the sentence that says this rule dies.
    """
    joined = "\n".join(bag_admission.BAG_ADMISSION_NONCLAIMS)
    assert "COO-DECISION 20260829_0441" in joined, (
        "the ruling that made this rule interim is not cited in the "
        "nonclaims a reader actually sees"
    )
    assert "next_item_identity" in joined, (
        "the expiry is keyed to the identity counter; the nonclaims do not "
        "name it"
    )
    assert "_classify_against" in joined, (
        "COO ordered replace-not-extend: the nonclaims must name the "
        "function the superseding round deletes"
    )


def test_the_expiry_condition_is_two_named_facts_not_a_date() -> None:
    """A date cannot be evaluated by a test; these two facts can.

    Both are about ``store.py`` doing something it does not do yet.  The
    order is meaningful -- the INSERT is what makes the counter advance
    possible -- and it is asserted so the constant cannot be reshuffled into
    a weaker pair.
    """
    condition = bag_admission.BAG_ADMISSION_EXPIRY_CONDITION
    assert len(condition) == 2
    assert "INSERT" in condition[0] and "store.py" in condition[0]
    assert "next_item_identity" in condition[1]
    assert all(text.isascii() for text in condition), (
        "this constant can reach the bridge console, which is cp874"
    )


def _executed_sql(module_name: str):
    """(enclosing function, sql text) for every string handed to a DB call.

    Two failures shaped this helper, both found by pf-adversary.

    A LINE SCANNER IS NOT ENOUGH.  ``store.py`` writes SQL split across
    adjacent string literals and, elsewhere in this codebase, hoisted into a
    module constant.  Both look like nothing to a per-line grep.  ``ast``
    folds implicit concatenation into one Constant, and module-level
    constants are resolved by name below, so both shapes are seen.

    PROSE IS NOT A STATEMENT.  Matching SQL text anywhere in a file finds
    ``mob_pickup``'s docstrings, which discuss at length the exact INSERT
    ``store.py`` must one day make, and its console token
    ``MOB_PICKUP_ROW_WOULD_INSERT table=character_backpack_items``.  A
    module that DESCRIBES a write is the opposite of a module that performs
    one -- that description is the whole reason the expiry is not met yet.
    So only strings that reach ``execute``/``executemany``/``executescript``
    count.
    """
    tree = ast.parse(_source(module_name))
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        constants[target.id] = node.value.value
    owner = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                owner[id(child)] = node.name
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        if name not in ("execute", "executemany", "executescript"):
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            text = first.value
        elif isinstance(first, ast.Name) and first.id in constants:
            text = constants[first.id]
        else:
            continue
        out.append((owner.get(id(node), "<module>"), " ".join(text.split())))
    return out


def _writes_naming(module_name: str, column: str):
    """Executed statements that both name ``column`` and are a write.

    ``\bUPDATE\b`` and not ``"UPDATE" in text``: every write in
    ``store.py`` also sets ``updated_at``, and a substring test counts a
    pure SELECT of that column as a write.  The first version of this check
    did exactly that -- red on a read, green on the write it exists to
    catch.
    """
    hits = []
    for func, text in _executed_sql(module_name):
        if column not in text:
            continue
        upper = text.upper()
        if re.search(r"\bUPDATE\b", upper) or re.search(r"\bINSERT\b", upper):
            hits.append((func, text))
    return hits


def test_nothing_writes_the_identity_counter_yet() -> None:
    """Half two of the expiry: no statement advances ``next_item_identity``.

    Goes red the day chief's STORE-INSERT-001 lands, however that statement
    is formatted, because the check is over parsed string constants rather
    than over source lines.
    """
    writes = _writes_naming("store", "next_item_identity")
    assert not writes, (
        "store.py now writes character_backpacks.next_item_identity:\n  "
        + "\n  ".join("%s(): %s" % hit for hit in writes)
        + "\nHalf two of bag_admission's nonclaim 8 expiry is MET.  The "
          "counter can be the admission criterion now, and COO-DECISION "
          "20260829_0441 item 2 requires _classify_against to be DELETED "
          "rather than kept beside it."
    )


def test_the_only_backpack_row_insert_is_the_one_that_makes_a_character() -> None:
    """Half one: nothing INSERTs a bag row that a pickup produced.

    ~~Asserted by the absence of a token nobody writes
    (``MOB_PICKUP_ROW_DID_INSERT``).~~  pf-adversary showed that was a
    strawman: appending a real ``persist_pickup_row`` with a genuine INSERT,
    and leaving ``mob_pickup``'s WOULD token in place as stale prose, kept
    it green.  The honest question is not "is a token absent" but "which
    functions can put a row in the bag table", so that is what is asserted.

    ``_insert_initial_backpack`` is character creation.  Any second name in
    this set is a pickup path, and the expiry's first half is met.
    """
    statement = re.compile(r"INSERT\s+INTO\s+character_backpack_items",
                           re.IGNORECASE)
    inserters = {
        func for module in ("store", "mob_pickup")
        for func, text in _executed_sql(module)
        if statement.search(text)
    }
    assert inserters == {"_insert_initial_backpack"}, (
        "the set of functions that INSERT a backpack row is %s, not just "
        "character creation.  Half one of bag_admission's nonclaim 8 expiry "
        "is MET: a real pickup row can reach the database, so the "
        "superseding round must delete _classify_against rather than keep "
        "it as a fallback." % (sorted(inserters),)
    )


def test_the_pickup_path_still_only_logs_the_row_it_would_write() -> None:
    """The token, kept as a SECOND signal rather than the only one.

    Weaker than the test above and labelled as such: it catches a rename,
    not a behaviour change.  It stays because the token is what a person
    greps the console for, and a silent rename would strand that habit.
    """
    assert "MOB_PICKUP_ROW_WOULD_INSERT" in _source("mob_pickup"), (
        "the console token this expiry is written around has been renamed; "
        "re-derive the expiry rather than deleting this test"
    )


def test_the_wire_this_nonclaim_describes_is_actually_there() -> None:
    """Nonclaim 3 says gate 2 calls this module.  Check it, do not report it.

    pf-adversary's finding: nonclaim 3 first said the wire was "in flight"
    when it had already merged, then told the reader to go and verify at
    their own head.  Both are reports.  This is the check, and it fails in
    both directions -- if the wire is reverted, nonclaim 3 becomes false
    and this goes red.
    """
    session = _source("session")
    assert "bag_admission.may_enter_world(" in session, (
        "session.select_and_start no longer calls "
        "bag_admission.may_enter_world.  Gate 2 is byte-identical again and "
        "nonclaim 3 in bag_admission.py -- which states the opposite in "
        "capitals -- must be struck through in the same commit as the "
        "revert."
    )


def test_classify_against_still_exists_so_the_expiry_has_a_subject() -> None:
    """The function the sunset names must be findable by that name.

    Guards the failure mode where a refactor renames ``_classify_against``
    and nonclaim 8's "DELETE this" instruction silently loses its referent,
    leaving a rule with an expiry nobody can carry out.
    """
    tree = ast.parse(_source("bag_admission"))
    names = {
        node.name for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    assert "_classify_against" in names, (
        "nonclaim 8 tells a later round to delete _classify_against, but no "
        "function by that name exists; update the nonclaim in the same "
        "commit as the rename"
    )
