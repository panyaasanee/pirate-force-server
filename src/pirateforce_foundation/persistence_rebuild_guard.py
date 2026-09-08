"""The rebuild guard: SQL that proves a table-rebuild migration copied
every row's CONTENT, not merely the right NUMBER of rows.

WHY THIS MODULE EXISTS -- IT IS A DEBT THIS LANE DECLARED AGAINST ITSELF.
``pf_bridge/rounds/DB_20260908_1316_nivlwg_round.md`` records pf-adversary
finding D2 against migration ``017`` in this lane's own words: the seven
guards that migration carries "never look at a child table's row CONTENT --
``UPDATE character_positions SET scene_id=99`` before the ``DROP`` passes
green (every character moves to scene 99 and the migration reports
success)".  ``017`` is applied and frozen, so it cannot be repaired; the
same round's "next round" list therefore names the repair shape exactly:
"a helper every rebuild can borrow ... the next ``018`` must pass it".
This module is that helper, and ``migrations/
018_character_skills_gm_grant_source.sql`` is the first migration to carry
it.

WHAT A COUNT GUARD CANNOT SEE, AND WHAT THIS ONE CAN.  A rebuild's copy
step is one ``INSERT INTO new SELECT ... FROM old``.  Every way that step
can go wrong while still moving the right number of rows is invisible to
``COUNT(*)``: a column dropped from the SELECT list and filled by the new
table's DEFAULT, two columns swapped, a ``COALESCE`` that turns a NULL into
a zero, an expression that rewrites a value, or -- the shape D2 actually
demonstrated -- an unrelated ``UPDATE`` slipped in before the ``DROP``.
Comparing the two row SETS in BOTH directions sees all of them: a row that
exists after but not before, and a row that existed before but not after,
are each an error, and each is reported by its own guard row.

WHY ``EXCEPT`` AND NOT A JOIN.  SQLite's compound set operators compare
rows with the same NULL-sensitive equality ``DISTINCT`` uses: two NULLs in
the same column count as EQUAL, so a table with NULLs compares correctly
and without a single ``IS`` special case.  ``a=b`` in a join's ``ON``
clause is NULL for that same pair, which would silently report every
NULL-carrying row as changed (or, with the comparison inverted, silently
pass over one).  Every table this lane rebuilds has nullable columns
(``characters.deleted_at``, ``ground_drops.taken_at``), so this is the
difference between a guard and a decoration.

WHY THE COUNT GUARD IS STILL EMITTED.  ``EXCEPT`` is set-based: it folds
duplicate rows together, so a rebuild that wrote one row twice would leave
both directions empty.  Every table this lane rebuilds has ``id INTEGER
PRIMARY KEY``, which makes a byte-identical duplicate impossible -- but
that is a property of today's schemas, not of this helper, and a count
comparison costs one statement.  The two guards answer different questions
and this module emits both rather than reasoning about which is redundant.

WHY SQL AND NOT PYTHON.  The runner (``SQLiteStore.migrate``) wraps a
migration file in one transaction and hands it to ``executescript``; there
is no point in that path where Python sees the rows.  A guard that lives
anywhere but inside the migration's own transaction cannot abort the
migration, and one that cannot abort it is a report, not a guard.  The
abort itself is the ``CHECK(ok=1)`` on the guard table: inserting a ``0``
raises, ``executescript`` propagates, and ``migrate`` rolls the whole file
back -- the mechanism ``004``/``009``/``014``/``017`` already use for their
count guards, reused here rather than replaced.

WHAT THIS MODULE DOES NOT DO.  It does not run anything: every function
here returns SQL TEXT for a migration author to paste into a file, which
keeps the migration a self-contained artifact whose sha256 the ledger can
pin (a helper that generated SQL at apply time would put a Python function
inside the checksum's blind spot).  It does not choose a table's column
list -- the caller names the columns, and
``tests/test_persistence_rebuild_guard.py`` is what proves the list a
migration passed is the complete one, derived from the pre-migration
schema rather than typed twice.  It does not verify anything about the new
table's SCHEMA (a rebuild's whole purpose is to change that); it verifies
only that the DATA crossed unchanged.
"""

from __future__ import annotations

#: Identifier characters this module will emit.  A migration author names
#: its own tables and columns, and every name that reaches this module is a
#: literal typed in a migration file in this repository -- but the guard
#: builds SQL by string concatenation (a table name cannot be a bound
#: parameter in SQLite), so a name that is not a plain identifier is
#: refused here rather than concatenated into a statement.
_SAFE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


class RebuildGuardError(ValueError):
    """This module refused to build SQL rather than emit a broken guard."""


def _identifier(name: str, what: str) -> str:
    if not isinstance(name, str):
        raise RebuildGuardError(f"{what} must be a str")
    if not name:
        raise RebuildGuardError(f"{what} must not be empty")
    if set(name) - _SAFE:
        raise RebuildGuardError(
            f"{what} {name!r} is not a plain SQL identifier"
        )
    if name[0].isdigit():
        raise RebuildGuardError(f"{what} {name!r} starts with a digit")
    return name


def _columns(columns) -> tuple[str, ...]:
    if isinstance(columns, (str, bytes)) or not isinstance(
        columns, (list, tuple)
    ):
        raise RebuildGuardError("columns must be a list or tuple of str")
    if not columns:
        raise RebuildGuardError("columns must name at least one column")
    checked = tuple(_identifier(name, "column") for name in columns)
    if len(set(checked)) != len(checked):
        raise RebuildGuardError("columns names a column twice")
    return checked


def snapshot_sql(table: str, tag: str) -> str:
    """The statement a rebuild runs BEFORE it touches anything.

    One ``CREATE TABLE <tag>_before AS SELECT * FROM <table>`` -- a plain
    data copy, deliberately without the source's constraints, indexes or
    types, because its only job is to be compared against.  It must run
    before the rebuild's own ``CREATE``/``INSERT``/``DROP`` so that it
    captures the rows as they were on the way in, and the migration must
    drop it again at the end (`drop_sql` below) so no ``_pf_`` scaffold
    survives into the shipped schema.
    """
    table = _identifier(table, "table")
    tag = _identifier(tag, "tag")
    return f"CREATE TABLE {tag}_before AS SELECT * FROM {table};"


def verify_sql(table: str, columns, tag: str) -> str:
    """The statements a rebuild runs AFTER the copy, DROP and RENAME.

    Three guard rows against one ``CHECK(ok=1)`` table, so a failure names
    which question failed rather than only that something did:

      1. the row COUNT is the one the snapshot carried;
      2. no row exists in the rebuilt table that was not in the snapshot;
      3. no row existed in the snapshot that is not in the rebuilt table.

    ``columns`` is the complete pre-migration column list, in any order --
    a column left out of it is a column this guard cannot see, which is
    why the test beside this module derives the list from the schema
    instead of trusting the migration's own typing.
    """
    table = _identifier(table, "table")
    tag = _identifier(tag, "tag")
    names = ",".join(_columns(columns))
    return "\n".join(
        (
            f"CREATE TABLE {tag}_guard(ok INTEGER NOT NULL CHECK(ok=1));",
            f"INSERT INTO {tag}_guard(ok) SELECT CASE WHEN"
            f" (SELECT COUNT(*) FROM {table})"
            f"=(SELECT COUNT(*) FROM {tag}_before) THEN 1 ELSE 0 END;",
            f"INSERT INTO {tag}_guard(ok) SELECT CASE WHEN NOT EXISTS("
            f"SELECT {names} FROM {table}"
            f" EXCEPT SELECT {names} FROM {tag}_before) THEN 1 ELSE 0 END;",
            f"INSERT INTO {tag}_guard(ok) SELECT CASE WHEN NOT EXISTS("
            f"SELECT {names} FROM {tag}_before"
            f" EXCEPT SELECT {names} FROM {table}) THEN 1 ELSE 0 END;",
            f"INSERT INTO {tag}_guard(ok) SELECT CASE WHEN"
            " (SELECT COUNT(*) FROM pragma_foreign_key_check())=0"
            " THEN 1 ELSE 0 END;",
        )
    )


def drop_sql(tag: str) -> str:
    """The cleanup a rebuild runs last: both scaffold tables go away inside
    the same transaction that created them, so a database that finishes the
    migration carries no ``_pf_`` leftovers and a database that fails it
    carries none either (the whole file rolls back)."""
    tag = _identifier(tag, "tag")
    return "\n".join(
        (f"DROP TABLE {tag}_guard;", f"DROP TABLE {tag}_before;")
    )
