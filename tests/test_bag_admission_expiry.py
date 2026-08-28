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


def test_the_expiry_condition_is_still_unmet_so_the_shape_rule_is_entitled() -> None:
    """Half one: the pickup path still only LOGS the row it would write.

    ``mob_pickup``'s token is ``MOB_PICKUP_ROW_WOULD_INSERT`` -- WOULD, and
    that word is the whole content of this assertion.  The day it becomes a
    real INSERT this test fails, and the failure is the reminder, not a bug.
    """
    pickup = _source("mob_pickup")
    assert "MOB_PICKUP_ROW_WOULD_INSERT" in pickup, (
        "the token this expiry is keyed to has been renamed; re-derive the "
        "expiry rather than deleting this test"
    )
    assert "MOB_PICKUP_ROW_DID_INSERT" not in pickup, (
        "the pickup path appears to INSERT for real now.  Half one of "
        "bag_admission's nonclaim 8 expiry is MET: the superseding round "
        "must delete _classify_against, not keep it as a fallback."
    )


def test_nothing_advances_the_identity_counter_yet() -> None:
    """Half two: no write path moves ``next_item_identity``.

    Measured over ``store.py``'s source rather than its behaviour because
    the honest question is "does any statement mention this column in a
    write?", and a behavioural test could only prove that the paths it
    happened to call do not.  A mention in a SELECT or in prose does not
    count as advancing it, so the check is for the column beside an UPDATE
    or an INSERT in the same statement text.
    """
    store = _source("store")
    writes = [
        line for line in store.splitlines()
        if "next_item_identity" in line
        and ("UPDATE" in line.upper() or "INSERT" in line.upper())
    ]
    assert not writes, (
        "store.py now writes character_backpacks.next_item_identity:\n  "
        + "\n  ".join(writes)
        + "\nHalf two of bag_admission's nonclaim 8 expiry is MET.  The "
          "counter can be the admission criterion now, and COO-DECISION "
          "20260829_0441 item 2 requires _classify_against to be DELETED "
          "rather than kept beside it."
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
