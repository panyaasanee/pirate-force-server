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
``level = 0``, or that adds a FIFTH column, turns every file that imports this
one red at its fixture.

WHAT CHANGED ON 2026-09-02 AT 16:07, and why the list grew to three.  This
module used to refuse a birth carrying ``speed_walk = 400.0`` outright, citing
``COO-DECISION 20260901_1447`` point 2, which reserved that number for a
migration and forbade it at birth.  That decision was overtaken twice: `0742`
lifted the ban on the number once `RE-194` closed which of the two candidates
the player object uses, and ``COO-DECISION 20260902_1607`` -- the owner
overruling her own COO in session -- had this lane install all four as column
DEFAULTS in ``migrations/009_character_birth_defaults.sql``.  So the third
accepted state is not a loosening of the guard, it is the guard following the
decision that created it: a birth on a database at 009 is exactly those four
values, and anything else is still refused.

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

from pirateforce_foundation import persistence_typed_attrs as _typed  # noqa: E402
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402

#: The column `009` gives a default alongside the three vitals.  Looked up by
#: its WIRE field (x=7, BasicAttr+0x54) through `persistence_typed_attrs`
#: rather than written here as a string, because the column NAME still encodes
#: an unproven identification ("speed_walk", [assumption of LANE-DB - awaiting
#: RE], see the naming note in `migrations/006`) while the field it is bound to
#: does not.  A rename of the column therefore moves this constant with it; a
#: column that stops existing is an error here rather than a silently absent
#: key in an expectation.
SPEED_COLUMN = _typed.COLUMN_FOR_X[7]

#: The state a character was born into before `migrations/009_character_birth
#: _defaults.sql`: no typed column holds anything.  Still reachable, and still
#: accepted, because a database BELOW 009 really is in it -- the boot tests
#: build databases that stop at 006, 007 and 008 on purpose, and
#: :func:`clear_vitals_to_pre_seed` constructs it deliberately so the
#: fail-closed doors stay measured instead of unreachable.
UNSEEDED_BIRTH: dict[str, int | float] = {}

#: The four columns `migrations/009_character_birth_defaults.sql` gives a
#: DEFAULT, in the order the migration lists them.
BIRTH_COLUMNS: tuple[str, ...] = tuple(vitals.VITAL_COLUMNS) + (SPEED_COLUMN,)


def seeded_birth() -> dict[str, int]:
    """The state a character is born into once the insertion point lands.

    Derived from ``new_character_vitals()`` on every call rather than written
    out again here, so this file cannot drift away from the module that owns
    the numbers -- which itself derives them from ``migrations/007``.
    """
    return vitals.new_character_vitals()


def default_birth() -> dict[str, int | float]:
    """The state a character is born into on a database that has applied
    ``migrations/009_character_birth_defaults.sql``.

    THE FOURTH COLUMN IS NOT A DRIFT.  Until `009` this module refused a birth
    carrying ``speed_walk``, on `COO-DECISION 20260901_1447` point 2 -- which
    forbade seeding that column while 400.0 and the 150.0 proven on the wire
    for NPCs were two candidates.  `RE-194` closed that question,
    `COO-DECISION 20260902_0742` lifted the ban and approved
    ``008_character_speed_walk_seed.sql``, and `COO-DECISION 20260902_1607`
    -- the owner overruling two refusals of her own COO in session on
    2026-09-02 -- put the same number on the column as a DEFAULT so that
    characters born after `008` get it too.  So the refusal below did not
    weaken: it moved with the decision that created it, and a birth carrying
    a FIFTH column, or any of these four with a different number, is still a
    defect this module raises on.

    Both halves are derived rather than retyped: the three vitals from
    ``persistence_vitals.new_character_vitals()`` and the speed from
    ``persistence_attr_compose.CLIENT_CONSTRUCTION_DEFAULTS[7]``, the
    client's own construction default at ``0x00464AF2``.  A migration whose
    DEFAULT drifts from either module is red at every fixture that imports
    this file, which is the whole reason this state is spelled here once.
    """
    from pirateforce_foundation import persistence_attr_compose as compose

    state: dict[str, int | float] = dict(seeded_birth())
    state[SPEED_COLUMN] = float(compose.CLIENT_CONSTRUCTION_DEFAULTS[7].value)
    return state


def accepted_birth_states() -> tuple[dict, ...]:
    """The only states this lane accepts from ``create_character``.

    Three, in the order a database reaches them: no seeding at all (below
    `009`, and what `clear_vitals_to_pre_seed` builds), the three vitals
    `COO-DECISION 20260902_0444` has chief write at the insertion point, and
    the four `009` installs as column defaults.  A database that has applied
    `009` AND carries chief's plug lands on the third of them as well -- the
    plug writes the same three numbers the defaults would have supplied, which
    is measured, not assumed (LANE-DB letter `20260902_1452`).
    """
    return dict(UNSEEDED_BIRTH), seeded_birth(), default_birth()


def measure_birth_typed_state(store, character_id: int) -> dict[str, int | float]:
    """The typed state a just-created character holds, refusing any third one.

    Call it on a character nothing has written to yet.  The return value is
    what every expectation in that test should be phrased against; the
    refusal is what keeps that phrasing from being a rubber stamp.
    """
    state = dict(store.read_typed_attributes(character_id))
    accepted = accepted_birth_states()
    if state in accepted:
        return state
    unseeded, seeded, defaulted = accepted
    raise AssertionError(
        "a newly created character holds a typed state this lane does not "
        "accept: %r.  The three accepted states are %r (no seeding -- a "
        "database below migrations/009, or one built by "
        "clear_vitals_to_pre_seed), %r (create_character calling "
        "persistence_vitals.new_character_vitals(), COO-DECISION "
        "20260902_0444) and %r (the column defaults of "
        "migrations/009_character_birth_defaults.sql, COO-DECISION "
        "20260902_1607).  Anything else -- a fifth column, a level of zero, "
        "one of these four with a different number -- is a defect in the "
        "insertion point or in the migration, not in the test that just "
        "refused it."
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


def clear_birth_defaults_to_pre_009(db_path, character_ids=None) -> int:
    """Put character rows into the state a pre-`009` database really held:
    none of the FOUR birth columns holds anything.

    :func:`clear_vitals_to_pre_seed` clears the three vital columns and is the
    right call for a test about `007`'s narrowness or about the fail-closed
    doors of `persistence_vitals`.  This one also clears ``speed_walk``, which
    `migrations/009_character_birth_defaults.sql` gives a DEFAULT: a test whose
    subject is "writing this column CLOSES a gap" needs a row where the gap is
    open, and after 009 a newborn no longer has one.  Same raw-SQL,
    temporary-file-only rule as its neighbour -- the owner's canonical database
    is reachable exactly one way, through a migration file (`COO-DECISION
    20260901_1112` point 2).
    """
    return _clear_columns(db_path, list(BIRTH_COLUMNS), character_ids)


def clear_vitals_to_pre_seed(db_path, character_ids=None) -> int:
    """Put character rows into the state a pre-007 database really held.

    Returns the number of rows that still hold a vital afterwards, which is
    always zero -- it raises rather than returning nonzero -- so a caller can
    assert on the call itself.  Raw SQL on a temporary test database only:
    the owner's canonical file is reachable exactly one way, through a
    migration file (``COO-DECISION 20260901_1112`` point 2), and nothing here
    runs anywhere near it.
    """
    return _clear_columns(db_path, list(vitals.VITAL_COLUMNS), character_ids)


def _clear_columns(db_path, columns, character_ids) -> int:
    """The shared body of the two functions above.

    Returns the number of rows that still hold one of ``columns`` afterwards,
    which is always zero -- it raises rather than returning nonzero.
    """
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
