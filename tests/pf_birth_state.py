"""LANE-DB: what a newly created character may legitimately hold, and the one
place this lane's tests turn that into a row state they can reason about.

WHY THIS FILE EXISTS.  ``COO-DECISION 20260902_0444`` tells chief to write
``level``, ``hp_current``, ``hp_max`` into ``SQLiteStore.create_character``
from ``persistence_vitals.new_character_vitals()``.  Round ``cby3pd``
simulated that insertion point and measured **33 red tests, every one of them
in this lane's own files** -- not one of them a defect in chief's line.  Each
had quietly taken "a character this test just made holds no vital" as a fact
about the world, when it is only a fact about TODAY.  They were mines this
lane had laid in another lane's corridor, and clearing them is this lane's
work, not his: he may not edit these files at all under the write zones.

THE TWO WAYS A TEST GETS OFF THAT DEPENDENCY, and which to reach for:

1. The test's subject is something else (a ``speed_walk`` round trip, a sparse
   block, a census count) and the vitals are only noise in the assertion.
   Then MEASURE the birth state with :func:`measure_birth_typed_state` and
   phrase the expectation as ``birth + what this test wrote``
   (:func:`with_birth`).  The assertion stays exact -- an insertion point that
   writes a fourth column, or the wrong numbers, is still red.
2. The test's subject IS a row in a particular vitals state (migration 007's
   narrowness, the fail-closed refusals the vitals store methods make over a
   row that holds none of the three).  Then CONSTRUCT that state with
   :func:`clear_vitals_to_pre_seed`, and say so.  Inheriting it from whatever
   ``create_character`` happens to leave behind was always the weaker
   spelling; once birth seeding lands it is the ONLY way to reach an unseeded
   row at all, so the fail-closed doors stay measured instead of unreachable.

WHAT IS DELIBERATELY *NOT* HERE.  No branch of the form "if the insertion
point is in, expect A, else expect B" written per test.  That shape is how a
stamp gets written: a ``pf-adversary`` pass (round ``cby3pd``, defect D2)
took a draft in that shape and drove four different WRONG insertion points
through it green, the worst of which reset an existing ``level 9, hp 480/500``
character to ``1, 100/100``.  The refusal in
:func:`measure_birth_typed_state` is the single place the two accepted states
are named, and it refuses everything else -- so an insertion point that seeds
``level = 0``, or that adds ``speed_walk = 400.0`` (a number
``COO-DECISION 20260901_1447`` point 2 reserves for a migration and forbids at
birth), turns every file that imports this one red at its fixture.

WHAT IT DOES NOT CLAIM.  It does not check that other TABLES (positions,
backpacks) or non-vital columns of other rows survived the creation of this
one -- a `pf-adversary` pass showed plugs that stamp another character's
backpack, blank another character's ``avatar_typed_json``, or undelete a
soft-deleted row, all green against this lane's files.  Those are real and
they are reported to COO rather than papered over here.  It also does not
check that OTHER characters' VITALS survived the creation of this one.  That is a different property and it is
measured where it belongs, against real second and third rows, by
``SeedsACohortNotADatabaseTests`` in ``tests/test_persistence_vitals.py``.
Nothing here is a substitute for it.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402

#: The state a character is born into TODAY: no typed column holds anything.
UNSEEDED_BIRTH: dict[str, int | float] = {}


def seeded_birth() -> dict[str, int]:
    """The state a character is born into once the insertion point lands.

    Derived from ``new_character_vitals()`` on every call rather than written
    out again here, so this file cannot drift away from the module that owns
    the numbers -- which itself derives them from ``migrations/007``.
    """
    return vitals.new_character_vitals()


def accepted_birth_states() -> tuple[dict, dict]:
    """The only two states this lane accepts from ``create_character``."""
    return dict(UNSEEDED_BIRTH), seeded_birth()


def measure_birth_typed_state(store, character_id: int) -> dict[str, int | float]:
    """The typed state a just-created character holds, refusing any third one.

    Call it on a character nothing has written to yet.  The return value is
    what every expectation in that test should be phrased against; the
    refusal is what keeps that phrasing from being a rubber stamp.
    """
    state = dict(store.read_typed_attributes(character_id))
    unseeded, seeded = accepted_birth_states()
    if state in (unseeded, seeded):
        return state
    raise AssertionError(
        "a newly created character holds a typed state this lane does not "
        "accept: %r.  The two accepted states are %r (no seeding, the world "
        "as of round cby3pd) and %r (create_character calling "
        "persistence_vitals.new_character_vitals(), COO-DECISION "
        "20260902_0444).  Anything else -- a fourth column, a level of zero, "
        "a speed_walk seeded at birth -- is a defect in the insertion point, "
        "not in the test that just refused it."
        % (state, unseeded, seeded)
    )


def measure_every_birth(store, character_ids) -> list[dict]:
    """:func:`measure_birth_typed_state` over EVERY id, and the reason it must
    be every one.

    A `pf-adversary` pass measured what checking only the first costs: a plug
    that seeds correctly for an account's first character and then, for every
    character after it, writes ``level = 0`` (the state
    ``persistence_vitals`` refuses by name) was GREEN across the whole
    7000-test suite -- as was one that gave characters 2..N ``speed_walk =
    400.0``, the column ``COO-DECISION 20260901_1447`` point 2 forbids at
    birth, and one that gave them ``hp_current > hp_max``.  The fixtures that
    used this module measured character one, then cleared all of them, and the
    clearing removed the evidence for every row it had never looked at.

    Call it BEFORE anything writes to these characters.  Returns one state per
    id, in the order given.
    """
    return [measure_birth_typed_state(store, character_id)
            for character_id in character_ids]


def with_birth(birth: dict, **written) -> dict[str, int | float]:
    """``birth`` overlaid with what the test wrote -- the exact expectation.

    Written keys win, so a test that writes ``level=12`` over a birth level of
    1 expects 12 and would still catch a write that failed to land.
    """
    expected = dict(birth)
    expected.update(written)
    return expected


def birth_by_x(birth: dict) -> dict[int, int | float]:
    """``birth`` in the gate's ``{x: value}`` shape."""
    from pirateforce_foundation import persistence_typed_attrs as typed

    return {typed.TYPED_COLUMNS[column].x: value
            for column, value in birth.items()}


def clear_vitals_to_pre_seed(db_path, character_ids=None) -> int:
    """Put character rows into the state a pre-007 database really held.

    Returns the number of rows that still hold a vital afterwards, which is
    always zero -- it raises rather than returning nonzero -- so a caller can
    assert on the call itself.  Raw SQL on a temporary test database only:
    the owner's canonical file is reachable exactly one way, through a
    migration file (``COO-DECISION 20260901_1112`` point 2), and nothing here
    runs anywhere near it.
    """
    columns = list(vitals.VITAL_COLUMNS)
    assignments = ", ".join("%s=NULL" % column for column in columns)
    db = sqlite3.connect(str(db_path))
    try:
        if character_ids is None:
            db.execute("UPDATE characters SET %s" % assignments)
        else:
            ids = list(character_ids)
            db.executemany(
                "UPDATE characters SET %s WHERE id=?" % assignments,
                [(int(cid),) for cid in ids],
            )
        db.commit()
        predicate = " OR ".join("%s IS NOT NULL" % c for c in columns)
        sql = "SELECT COUNT(*) FROM characters WHERE (%s)" % predicate
        params: tuple = ()
        if character_ids is not None:
            ids = [int(cid) for cid in character_ids]
            sql += " AND id IN (%s)" % ",".join("?" * len(ids))
            params = tuple(ids)
        left = int(db.execute(sql, params).fetchone()[0])
    finally:
        db.close()
    if left:
        raise AssertionError(
            "clear_vitals_to_pre_seed left %d row(s) holding a vital; the "
            "pre-seed state this test is about was never actually built"
            % left
        )
    return left
