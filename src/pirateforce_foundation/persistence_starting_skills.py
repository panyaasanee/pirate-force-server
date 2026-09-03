"""LANE-DB: which skill ids a character is born with, resolved from
class_id.

WHAT THIS IS.  `PANYA-DECISION 20260904_0328` piece 5 (`COO-ORDER
20260904_0329` item 5): a character's skill window is empty forever today,
including the one skill every class starts with
(`CONSTDATA_TH__SKILL_TEXT.tsv` id 99, "Normal Attack" -- the basic attack).
This module answers exactly one question -- "given a resolved `class_id`,
which skill ids does she start with?" -- and nothing else.

WHERE THE ANSWER COMES FROM, AND WHY THIS MODULE DOES NOT RE-DERIVE IT.
`src/pirateforce_foundation/class_catalog.py` is LANE-CS's own module: it
copies `CONSTDATA_TH__CHARCREATE_CLASS.tsv` byte-for-byte
(sha256-pinned, re-derivable with no `pf_bridge` sibling present) and reads
`s_SKILL_1..4` for the four starting skill ids of each of the five
selectable classes.  This lane does not own skill data -- `COO-ORDER
20260904_0329` item 5 is LANE-DB's to store, not LANE-CS's own catalog to
duplicate -- so this module RESOLVES `class_catalog`'s answer; a second,
independently-typed copy of the same table here would be exactly the drift
`class_catalog.SOURCE_SHA256` exists to prevent, and the two could disagree
about the same class with nothing watching.

WHAT THIS MODULE DOES NOT DO.

* It does not decide which class a character is -- that is
  `persistence_class_id.resolve_class_id`, a separate resolver, upstream of
  this one.  A caller supplies an already-resolved `class_id`.
* It does not write anything.  No database connection, no store, no wire,
  no socket.  `SQLiteStore.grant_starting_skills` (this PR) is the write
  half; wiring the CALL at character creation -- after `class_id` itself is
  known -- is outside this lane's write zone, requested from chief the same
  way piece 1's two hookups were.
* It does not guess.  `class_catalog.starting_skill_ids` raises `KeyError`
  for a `class_id` it does not carry (an unresolved class, a future 6th
  class, a bad caller) and this module turns that into `None` -- a named
  absence, never a guessed skill list (`COO-DECISION 20260901_1059`).
* It does not decide whether skill 99 ("Normal Attack") is special in any
  way a caller should treat differently from the other three starting ids.
  It happens to be `s_SKILL_3` for every one of the five classes -- a fact a
  test below pins against the committed table, not an assumption this
  module's code branches on.
"""
from __future__ import annotations

from .class_catalog import ClassCatalogError, starting_skill_ids


def resolve_starting_skill_ids(class_id: int) -> tuple[int, int, int, int] | None:
    """The four starting-kit skill ids for `class_id`, or `None`.

    `None` for a `class_id` `class_catalog` does not carry -- there is no
    other outcome for an unresolvable class than a named gap, exactly as
    `persistence_class_id.resolve_class_id` returns `None` rather than
    guessing a class.

    Raises `TypeError` for a `class_id` that is not a plain `int` (a `bool`
    included, the same refusal `persistence_typed_attrs.validate` makes for
    the same reason: `True` is an `int` in python and would silently resolve
    class 1's kit).
    """
    if isinstance(class_id, bool) or not isinstance(class_id, int):
        raise TypeError(
            f"class_id must be an int, got {type(class_id).__name__}"
        )
    try:
        return starting_skill_ids(class_id)
    except (KeyError, ClassCatalogError):
        return None
