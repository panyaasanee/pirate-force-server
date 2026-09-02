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
:func:`measure_birth_typed_state` is the single place the accepted states are
named, and it refuses everything else -- so an insertion point that seeds
``level = 0``, or writes a fifth column, turns every file that imports this one
red at its fixture.

THE THIRD ACCEPTED STATE, AND WHY IT WAS ADDED RATHER THAN ARGUED WITH.  Until
``migrations/009_character_birth_defaults.sql`` there were two.  ``009`` gives
``level``/``hp_current``/``hp_max``/``speed_walk`` a column DEFAULT, so on any
database carrying it a newborn holds all FOUR -- including ``speed_walk =
400.0``, the exact value ``COO-DECISION 20260901_1447`` point 2 had reserved
for a migration and forbidden at birth.  That point was overruled by the
project owner in person (relayed as ``COO-DECISION 20260902_1607``, which fixes
all four numbers and forbids changing them), and the pin file that predicted
this collision said in advance what the fix would be: amend this module, do not
argue with it from a test.  So :func:`defaulted_birth` is that state, derived
-- like :func:`seeded_birth` -- from the modules that own the numbers rather
than written out again here, and a database WITHOUT ``009`` still measures as
one of the older two.

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


def defaulted_birth() -> dict[str, int | float]:
    """The state a character is born into on a database carrying ``009``.

    ``migrations/009_character_birth_defaults.sql`` installs a column DEFAULT
    for the three vitals and for ``speed_walk``, so this is
    :func:`seeded_birth` plus the walk speed.  Both halves are DERIVED from
    the modules that own the numbers -- ``persistence_vitals`` for the vitals
    and ``persistence_attr_compose.CLIENT_CONSTRUCTION_DEFAULTS`` for the
    client's measured ``BasicAttr@0x54`` construction default, reached through
    ``persistence_typed_attrs.column_for`` so even the COLUMN NAME is not
    spelled here -- because a copy of ``400.0`` in a test file is a second
    place the owner's fixed number could drift from ``009``.
    """
    from pirateforce_foundation import persistence_attr_compose as compose
    from pirateforce_foundation import persistence_typed_attrs as typed

    speed_x = 7
    birth: dict[str, int | float] = dict(seeded_birth())
    birth[typed.column_for(speed_x)] = (
        compose.CLIENT_CONSTRUCTION_DEFAULTS[speed_x].value)
    return birth


def accepted_birth_states() -> tuple[dict, dict, dict]:
    """The only three states this lane accepts from ``create_character``."""
    return dict(UNSEEDED_BIRTH), seeded_birth(), defaulted_birth()


def columns_no_birth_carries() -> tuple[str, ...]:
    """Typed columns that NO accepted birth state holds, in column order.

    A test whose subject is "an unwritten column arrives absent, never as
    zero" needs a column it can be sure a newborn does not already carry.
    Naming one by hand is how such a test rots: ``speed_walk`` was that
    column until ``migrations/009_character_birth_defaults.sql`` gave it a
    DEFAULT, and every test that had named it went red at once.  This derives
    the answer from :func:`accepted_birth_states` instead, so the day a
    further migration seeds another column the probes move with it -- and if
    a migration ever seeded ALL of them, this returns empty and the tests
    that depend on it say so rather than passing vacuously.

    The seventeen it returns today are the ones ``COO-DECISION 20260902_1607``
    keeps NULL on purpose: the owner's ban on guessing an unknown field as
    zero (``COO-DECISION 20260901_1059``) is exactly why they have no DEFAULT.
    """
    from pirateforce_foundation import persistence_typed_attrs as typed

    carried: set[str] = set()
    for state in accepted_birth_states():
        carried |= set(state)
    return tuple(c for c in typed.TYPED_COLUMNS if c not in carried)


def a_column_no_birth_carries() -> str:
    """One column from :func:`columns_no_birth_carries`, or a refusal."""
    columns = columns_no_birth_carries()
    if not columns:
        raise AssertionError(
            "every typed column is now carried by some accepted birth state, "
            "so there is no column left with which to probe 'absent, not "
            "zero'.  The test that asked for one needs rewriting, not this "
            "helper."
        )
    return columns[0]


def measure_birth_typed_state(store, character_id: int) -> dict[str, int | float]:
    """The typed state a just-created character holds, refusing any third one.

    Call it on a character nothing has written to yet.  The return value is
    what every expectation in that test should be phrased against; the
    refusal is what keeps that phrasing from being a rubber stamp.
    """
    state = dict(store.read_typed_attributes(character_id))
    unseeded, seeded, defaulted = accepted_birth_states()
    if state in (unseeded, seeded, defaulted):
        return state
    raise AssertionError(
        "a newly created character holds a typed state this lane does not "
        "accept: %r.  The three accepted states are %r (no seeding, the world "
        "as of round cby3pd), %r (create_character calling "
        "persistence_vitals.new_character_vitals(), COO-DECISION "
        "20260902_0444) and %r (the column DEFAULTs of "
        "migrations/009_character_birth_defaults.sql, COO-DECISION "
        "20260902_1607).  Anything else -- a fifth column, a level of zero, "
        "a number that is not the one the owner fixed -- is a defect in the "
        "insertion point, not in the test that just refused it."
        % (state, unseeded, seeded, defaulted)
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
