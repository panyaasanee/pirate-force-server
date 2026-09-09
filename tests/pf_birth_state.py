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

WHAT CHANGED ON 2026-09-08 AT 12:18, AND WHY THE LIST OF STATES IS GONE.
This module used to name THREE accepted birth states as literal dicts and
FOUR birth columns, citing `COO-DECISION 20260902_1607` -- the owner naming
four columns in session.  She reopened that herself on 2026-09-08
(`PANYA-DECISION 20260908_1218` point 3, her words: "do not hold to what I
once said, that a newly born character's defaults are only four columns;
there are more than that as the discoveries keep coming.  Make it correct
logic"), because the literal list had become a veto: `migrations/016` was cut
down from a rebuild to a backfill precisely because a fifth and sixth birth
column turned 39 tests red at this module's fixture, and a character born
after it still could not be paid by a quest.

SO THE BIRTH STATE IS NOW MEASURED, NOT LISTED.  What a newborn may hold is
computed from the database in front of the test: every typed column that
carries a DEFAULT in `PRAGMA table_info('characters')`, overlaid with the
columns `store.create_character` writes by name.  A migration that adds a
seventh birth column is then not an event in this file at all, and no other
lane's fixture goes red for it -- which is the half the owner ordered.

WHAT DID NOT LOOSEN, WHICH IS THE HALF THAT MATTERS.  Deriving the
expectation from the schema would be a rubber stamp if that were all it did,
so it is not all it does.  Two separate questions are asked:

1. DOES THE ROW MATCH THE SCHEMA?  The newborn's typed state must equal the
   computed state EXACTLY -- not a superset, not a subset, and column for
   column by value.  An insertion point that writes `level = 0`, or that
   writes a number the schema does not declare, or that seeds character one
   correctly and character two wrongly, is red here exactly as before.  This
   is not circular: it compares a ROW against a SCHEMA, and they are written
   by different files.

2. DOES THE SCHEMA MATCH THE MODULE THAT OWNS THE NUMBER?  For every column
   some module in `src/` owns an adjudicated value for -- the three vitals
   from `persistence_vitals.new_character_vitals()`, `speed_walk` from
   `persistence_attr_compose.CLIENT_CONSTRUCTION_DEFAULTS[7]`, the client's
   own construction default at `0x00464AF2` -- the schema's DEFAULT must
   equal it.  A migration that quietly changes `level`'s default to 0 is red
   here, and this check is NOT derived from the schema, so it cannot be
   satisfied by agreeing with the thing it grades.
   `experience` is in that list too: `migrations/017` calls its 0 MEASURED
   and names the module it is measured from -- the shipped, sha-pinned
   `standard_status.tsv`, whose `n_EXP_CURRENTLV` is 0 at level 1 -- so this
   file reads it through `persistence_experience` rather than leaving it
   ungraded.  `skill_points` is still ungraded here -- no module has
   published a number for it yet -- but its ASSUMPTION no longer belongs
   to this lane.  Through round `s5d4kz` an unstated "0" was this lane's
   own guess; `COO-DECISION 20260908_1441` named the number's owner as
   LANE-CS (`skill_point_curve.py`'s birth constant, to be published with a
   `MEASURED`/`ASSUMPTION` provenance tag) instead, so the live status is
   `[assumption of the project - number owner = LANE-CS per COO-DECISION
   20260908_1441]`, not this lane's own assumption to carry.  Question 2
   starts grading it the day `skill_point_curve` publishes that constant
   and this file is wired to read it -- not done this round, so the gap
   below still applies to it in practice.  For a column no module owns a
   number for -- whatever the next discovery adds -- question 2 has nothing
   to say and says nothing.  That is the deliberate gap the owner ordered: a
   new birth column needs no permission from this file.  What stops that gap
   from becoming permanent is not here but in
   `tests/test_migration_017_*.py::ItStaysTrueOnTheDIRECTORYNotOnlyOnThisVersionTests`,
   which reads the shipped `migrations/` directory and is red the day a later
   migration takes either default away or changes its number.

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
#: does not.
SPEED_COLUMN = _typed.COLUMN_FOR_X[7]

#: The state a character was born into before any migration gave a column a
#: DEFAULT: no typed column holds anything.  Still reachable and still
#: meaningful -- the boot tests build databases that stop at 006, 007 and 008
#: on purpose, and :func:`clear_vitals_to_pre_seed` constructs it deliberately
#: so the fail-closed doors stay measured instead of unreachable.
UNSEEDED_BIRTH: dict[str, int | float] = {}

MIGRATIONS = ROOT / "migrations"


def _adjudicated_birth_values() -> dict[str, int | float]:
    """The birth columns some module in ``src/`` owns the NUMBER for.

    This is the half of the pin that is not derived from the schema, so it
    cannot be satisfied by agreeing with the thing it grades.  It is also
    deliberately incomplete: a column no module owns a number for is absent
    here, and absence means "this file has nothing to say about the value",
    not "the value is wrong".  ``experience`` and ``skill_points`` are absent
    on purpose -- `migrations/017` gives them a DEFAULT of 0 on
    `PANYA-DECISION 20260908_1218`, and no module publishes those numbers
    YET.  ``skill_points`` is `[assumption of the project - number owner =
    LANE-CS per COO-DECISION 20260908_1441]` -- CS's job, not a re-open of
    this lane's own resolved ``016``/``017`` labels (`COO-DECISION
    20260908_2055`: an applied migration is frozen, so `016`'s own comment
    keeps its retired wording forever and this status lives here instead).
    """
    from pirateforce_foundation import persistence_attr_compose as compose

    values: dict[str, int | float] = dict(vitals.new_character_vitals())
    values[SPEED_COLUMN] = float(compose.CLIENT_CONSTRUCTION_DEFAULTS[7].value)
    # `experience` DOES have an owner, which this function did not ask on its
    # first draft (`pf-adversary`, round `nivlwg`, D5): `migrations/017`'s own
    # header calls this number MEASURED and names the module --
    # `src/pirateforce_foundation/data/standard_status.tsv`, the committed,
    # sha-pinned table `persistence_experience` already reads, whose
    # `n_EXP_CURRENTLV` is 0 at level 1.  Read through the reader rather than
    # typed here, so a table whose first row stops being 0 moves this with it.
    from pirateforce_foundation.persistence_standard_status import (
        standard_status_row,
    )
    values["experience"] = int(standard_status_row(1).exp_currentlv)
    return values


def _coerce(column: str, literal: str) -> int | float:
    """A `PRAGMA table_info` default literal, in the column's own Python type.

    The type comes from `persistence_typed_attrs`, which owns what each
    column is, rather than from guessing at the shape of the text.
    """
    spec = _typed.TYPED_COLUMNS[column]
    text = literal.strip()
    if text[:1] == "'" and text[-1:] == "'":
        text = text[1:-1]
    try:
        if (getattr(spec, "sql_type", "").upper() == "REAL"
                or "." in text or "e" in text.lower()):
            return float(text)
        return int(text)
    except ValueError:
        # SQLite accepts `DEFAULT (0)`, `DEFAULT 0x10` and
        # `DEFAULT CURRENT_TIMESTAMP`, and a bare `int()` on any of them
        # crashed every fixture importing this module with an opaque
        # traceback (`pf-adversary`, round `nivlwg`, D10).  The refusal says
        # what to do instead.
        raise AssertionError(
            "the birth DEFAULT this database declares for %r is %r, which "
            "this module cannot read as a number.  A migration that writes a "
            "default in a form other than a plain literal has to teach this "
            "function how to read it, in the same pull request -- a birth "
            "value nothing can read is a birth value nothing can grade."
            % (column, literal)
        )


def _defaults_from_columns(columns) -> dict[str, int | float]:
    """``{column: value}`` for every TYPED column carrying a DEFAULT.

    ``columns`` is a sequence of ``(name, dflt_value)`` pairs, whatever their
    source: a live `PRAGMA table_info`, or the declaration parsed out of the
    migration that last rebuilt the table.  Non-typed columns (`identity_hi`,
    `name_key`, `create_fingerprint`) carry defaults too and are not birth
    state -- they never appear in `read_typed_attributes`, so a fixture that
    expected them would be red against every store.
    """
    return {
        name: _coerce(name, default)
        for name, default in columns
        if default is not None and name in _typed.TYPED_COLUMNS
    }


def _declared_defaults_from_migrations() -> dict[str, int | float]:
    """The birth defaults the migration DIRECTORY declares, for the callers
    that have no store to ask.

    Parsed from the newest migration that rebuilds `characters`, because that
    is the file that owns the table's declaration; SQLite has no other way to
    attach a DEFAULT to an existing column, so a rebuild is where every one of
    them is written.  A file that adds a birth column therefore moves this
    function by itself, which is the point -- nothing here is a list.
    """
    import re

    rebuilds = sorted(
        path
        for path in MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")
        if "CREATE TABLE characters_rebuild" in path.read_text(encoding="utf-8")
    )
    if not rebuilds:
        raise AssertionError(
            "no migration in %s rebuilds `characters`, so the declared birth "
            "defaults cannot be read; this module's derivation is broken, not "
            "the caller's test" % MIGRATIONS
        )
    text = rebuilds[-1].read_text(encoding="utf-8")
    body = text.split("CREATE TABLE characters_rebuild", 1)[1]
    body = body.split("\n);", 1)[0]
    pairs = []
    for name in _typed.TYPED_COLUMNS:
        found = re.search(
            r"^\s*%s\s+\w+\s+DEFAULT\s+([^\s,]+)" % re.escape(name),
            body,
            re.MULTILINE,
        )
        pairs.append((name, found.group(1) if found else None))
    return _defaults_from_columns(pairs)


def _schema_defaults(store) -> dict[str, int | float]:
    """The birth defaults the database IN FRONT OF THE TEST declares.

    Falls back to the migration directory only when the store cannot be asked
    (a fake, or a store built over a table that does not exist yet), because a
    test running against a database stopped at 006 must be graded on THAT
    database and not on what `migrations/` holds today.
    """
    try:
        with store.connect() as db:
            rows = [
                (row[1], row[4])
                for row in db.execute("PRAGMA table_info('characters')")
            ]
    except Exception:
        return _declared_defaults_from_migrations()
    if not rows:
        return _declared_defaults_from_migrations()
    return _defaults_from_columns(rows)


def seeded_birth() -> dict[str, int]:
    """The columns ``store.create_character`` writes by name, with the numbers
    the module it reads them from returns.

    Derived from ``new_character_vitals()`` on every call rather than written
    out again here, so this file cannot drift away from the module that owns
    the numbers -- which itself derives them from ``migrations/007``.
    """
    return vitals.new_character_vitals()


def default_birth() -> dict[str, int | float]:
    """The state a character is born into on a database at the newest
    migration this repository ships.

    Derived twice over: the columns and their numbers come from the migration
    that declares them, and the columns `create_character` writes come from
    `persistence_vitals`.  Nothing is retyped here, so a migration that adds a
    birth column moves this function without anyone editing it -- which is
    what `PANYA-DECISION 20260908_1218` point 3 ordered.
    """
    state = _declared_defaults_from_migrations()
    state.update(seeded_birth())
    return state


def expected_birth_state(store) -> dict[str, int | float]:
    """What a character created against ``store`` must hold, and nothing else.

    The schema's own DEFAULTs, overlaid with the columns
    `store.create_character` writes by name.  The overlay order is the one
    SQLite itself uses: a named column in the INSERT beats the DEFAULT, so a
    plug that writes a number DISAGREEING with the schema is visible as the
    row disagreeing with this expectation.
    """
    state = _schema_defaults(store)
    # `_writes_vitals_at_birth()` FIRST, and not behind `state or ...`: with
    # the short-circuit the source read never ran on any database at 009 or
    # later, which is every database that matters, so the module could not
    # actually follow the insertion point being withdrawn -- measured at zero
    # calls over three characters on a 017 database (`pf-adversary`, round
    # `nivlwg`, D8).
    if _writes_vitals_at_birth():
        state.update(seeded_birth())
    return state


def _writes_vitals_at_birth() -> bool:
    """Whether `store.create_character` still names the vitals in its INSERT.

    Read from the shipped source rather than assumed, so the day the
    insertion point is withdrawn this module follows it instead of demanding
    a state nothing produces.
    """
    import inspect

    from pirateforce_foundation import store as store_module

    source = inspect.getsource(store_module.SQLiteStore.create_character)
    insert = [line for line in source.splitlines() if "INSERT INTO characters(" in line]
    if not insert:
        return False
    named = insert[0].split("INSERT INTO characters(", 1)[1].split(")", 1)[0]
    return all(column in named.split(",") for column in vitals.VITAL_COLUMNS)


def accepted_birth_states() -> tuple[dict, ...]:
    """Kept for callers that still ask for the list.

    It is no longer the authority -- :func:`measure_birth_typed_state` grades
    against the database in front of it -- but the two states a test can still
    legitimately name are here: nothing seeded at all (a database below the
    first rebuild, and what `clear_vitals_to_pre_seed` builds) and the state
    the newest migration declares.
    """
    return dict(UNSEEDED_BIRTH), seeded_birth(), default_birth()


#: The typed columns the newest migration gives a DEFAULT, plus the ones
#: `create_character` writes.  Derived, so it grows by itself.
def birth_columns() -> tuple[str, ...]:
    return tuple(default_birth())


#: Backwards-compatible name.  A tuple built once at import, from the same
#: derivation, for the callers that read it as a constant.
BIRTH_COLUMNS: tuple[str, ...] = tuple(default_birth())


def _check_schema_against_the_modules(state: dict) -> None:
    """Question 2: the schema's numbers against the modules that own them.

    Only for columns some module owns a value for.  A column nobody owns a
    number for is skipped in silence -- that is the gap
    `PANYA-DECISION 20260908_1218` point 3 opened on purpose.
    """
    adjudicated = _adjudicated_birth_values()
    wrong = {
        column: (state[column], adjudicated[column])
        for column in state
        if column in adjudicated and state[column] != adjudicated[column]
    }
    if wrong:
        raise AssertionError(
            "the birth value of a column whose number is owned by a module in "
            "src/ disagrees with that module: %r (column: (found, owed)).  "
            "`level`, `hp_current` and `hp_max` are owned by "
            "`persistence_vitals.new_character_vitals()` and `%s` by "
            "`persistence_attr_compose.CLIENT_CONSTRUCTION_DEFAULTS[7]`.  A "
            "migration or an insertion point moved one of them; this is not a "
            "defect in the test that refused it."
            % (wrong, SPEED_COLUMN)
        )


def measure_birth_typed_state(store, character_id: int) -> dict[str, int | float]:
    """The typed state a just-created character holds, refusing any other.

    Call it on a character nothing has written to yet.  The return value is
    what every expectation in that test should be phrased against; the two
    refusals are what keep that phrasing from being a rubber stamp -- see this
    module's docstring for which question each one asks.
    """
    state = dict(store.read_typed_attributes(character_id))
    expected = expected_birth_state(store)
    # THE RAW SCHEMA DEFAULTS, not `expected`.  `expected` has already been
    # overlaid with `seeded_birth()`, which IS `new_character_vitals()` -- so
    # feeding it here compared three of the four adjudicated columns against
    # themselves, and `pf-adversary` (round `nivlwg`, D4) drove `level = 0`,
    # `hp_max = 1` and both through it green.  Only `speed_walk` was ever
    # reachable, because it is the one column the overlay does not touch.
    _check_schema_against_the_modules(_schema_defaults(store))
    if state == expected:
        return state
    missing = {c: v for c, v in expected.items() if c not in state}
    extra = {c: v for c, v in state.items() if c not in expected}
    differing = {
        c: (state[c], expected[c])
        for c in state
        if c in expected and state[c] != expected[c]
    }
    raise AssertionError(
        "a newly created character does not hold the birth state this "
        "database declares.  Held: %r.  Declared by the schema and by "
        "`create_character`: %r.  Columns the row is missing: %r.  Columns "
        "the row holds that nothing declares: %r.  Columns holding a "
        "different value (found, declared): %r.  The birth state is MEASURED "
        "from `PRAGMA table_info('characters')` and from the INSERT in "
        "`store.create_character` (PANYA-DECISION 20260908_1218 point 3), so "
        "a mismatch here is a defect in the insertion point or in the "
        "migration, not in the test that refused it -- adding a birth column "
        "to a migration is NOT a change this file has to be told about."
        % (state, expected, missing, extra, differing)
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


def clear_columns_to_null(db_path, columns, character_ids=None) -> int:
    """Put named columns back to NULL on a temporary test database.

    The state a fail-closed door refuses ("nobody ever measured this column")
    stopped being reachable by accident the day a migration gave the column a
    birth DEFAULT, and a door whose refusal is unreachable is a door that can
    be deleted with the suite still green.  So the state is CONSTRUCTED, and
    the test says so -- the same rule, and the same raw-SQL-on-a-temporary-
    file-only limit, as its two neighbours: the owner's canonical database is
    reachable exactly one way, through a migration file (`COO-DECISION
    20260901_1112` point 2).
    """
    return _clear_columns(db_path, list(columns), character_ids)


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
