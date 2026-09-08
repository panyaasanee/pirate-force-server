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


# -- the SCHEMA half ------------------------------------------------------
#
# Adversary finding D1 on round `fw2hs6` asked the question the three
# builders above cannot answer: they prove the ROWS crossed the rebuild
# unchanged, and a rebuild exists precisely to change the SCHEMA, so they
# deliberately do not look at it -- with the result that a one-token mutant
# deleting `REFERENCES characters(id)` from `018` passed the whole suite,
# and the test named `test_foreign_key_integrity_holds_after_the_rebuild`
# passed BECAUSE the foreign key was gone (`pragma_foreign_key_check` sees
# nothing to check on a table that has no constraints).
#
# These two builders are that missing half.  They are a SEPARATE, OPT-IN
# pair rather than more rows inside `verify_sql`, for two reasons that are
# not style: (1) `migrations/018` is applied and its text is pinned by
# checksum, so widening `verify_sql` would change the pin and make every
# database that already ran `018` refuse to boot; (2) a rebuild whose whole
# purpose IS to add or drop a constraint must be able to say so, and a
# guard that cannot be opted out of would simply be deleted by the first
# migration that needed to.  A migration that does not intend to change its
# constraints carries this pair and says so in one line; one that does
# intend to leaves it out, and the reader can see which from the file.


def schema_snapshot_sql(table: str, tag: str) -> str:
    """The statement that records a table's CONSTRAINTS on the way in.

    Two more scaffold tables beside `snapshot_sql`'s data copy: the
    table's foreign keys and its indexes, read out of SQLite's own
    catalogue rather than out of the migration's prose.  Like the data
    snapshot it must run before the rebuild's first `CREATE`/`DROP`, and
    `drop_sql` (widened below) removes both again inside the same
    transaction.

    `pragma_index_list` is filtered to `origin='c'` -- indexes the schema
    CREATEd by name.  The `u`/`pk` rows are the implicit indexes SQLite
    mints for `UNIQUE`/`PRIMARY KEY` and it names them
    `sqlite_autoindex_<table>_<n>`, which changes with the table's name and
    the ordinal of the constraint; those constraints are visible to the
    data guard's own `UNIQUE` failures and to `pragma_foreign_key_list`,
    and pinning their generated names would make an honest rename red.
    """
    table = _identifier(table, "table")
    tag = _identifier(tag, "tag")
    return "\n".join(
        (
            f"CREATE TABLE {tag}_fk_before AS SELECT"
            ' "table","from","to",on_update,on_delete,"match"'
            f" FROM pragma_foreign_key_list('{table}');",
            f"CREATE TABLE {tag}_ix_before AS SELECT"
            ' name,"unique",partial'
            f" FROM pragma_index_list('{table}') WHERE origin='c';",
        )
    )


def schema_verify_sql(table: str, tag: str) -> str:
    """The guard rows that refuse a rebuild which quietly changed the
    table's constraints.

    Four more rows on the SAME `<tag>_guard` table `verify_sql` creates
    (so this pair must follow it, not replace it), asking the two questions
    in both directions: no foreign key gained, none lost, no created index
    gained, none lost.  `EXCEPT` both ways for the same reason the data
    guard uses it -- a set difference that is empty in one direction only
    is a change, not a match.

    A rebuild that INTENDS to change a constraint must not carry these
    rows; see the comment above this section for why that is a deliberate
    opt-in rather than something a migration can be forced into.
    """
    table = _identifier(table, "table")
    tag = _identifier(tag, "tag")
    fk = '"table","from","to",on_update,on_delete,"match"'
    ix = 'name,"unique",partial'
    live_fk = f"SELECT {fk} FROM pragma_foreign_key_list('{table}')"
    live_ix = (
        f"SELECT {ix} FROM pragma_index_list('{table}') WHERE origin='c'"
    )
    return "\n".join(
        (
            f"INSERT INTO {tag}_guard(ok) SELECT CASE WHEN NOT EXISTS("
            f"{live_fk} EXCEPT SELECT {fk} FROM {tag}_fk_before)"
            " THEN 1 ELSE 0 END;",
            f"INSERT INTO {tag}_guard(ok) SELECT CASE WHEN NOT EXISTS("
            f"SELECT {fk} FROM {tag}_fk_before EXCEPT {live_fk})"
            " THEN 1 ELSE 0 END;",
            f"INSERT INTO {tag}_guard(ok) SELECT CASE WHEN NOT EXISTS("
            f"{live_ix} EXCEPT SELECT {ix} FROM {tag}_ix_before)"
            " THEN 1 ELSE 0 END;",
            f"INSERT INTO {tag}_guard(ok) SELECT CASE WHEN NOT EXISTS("
            f"SELECT {ix} FROM {tag}_ix_before EXCEPT {live_ix})"
            " THEN 1 ELSE 0 END;",
        )
    )


def schema_drop_sql(tag: str) -> str:
    """The cleanup for `schema_snapshot_sql`'s two scaffold tables.

    Separate from `drop_sql` for the same reason the snapshot is separate:
    `migrations/018` is frozen and carries `drop_sql`'s exact text, so
    widening that one would break its checksum pin.
    """
    tag = _identifier(tag, "tag")
    return "\n".join(
        (f"DROP TABLE {tag}_ix_before;", f"DROP TABLE {tag}_fk_before;")
    )


# -- the WINDOW check -----------------------------------------------------
#
# Adversary finding D2 on round `fw2hs6`: the corruption the guard was
# built to stop moved UP one line and passed green --
#
#     BEGIN IMMEDIATE;
#     UPDATE character_skills SET skill_id=skill_id+1000;   <- here
#     CREATE TABLE _pf_mig018_before AS SELECT * FROM character_skills;
#
# because the window the guard protects STARTS at the snapshot, and nothing
# proved the snapshot was the first thing in the transaction.  No SQL the
# guard can emit closes that: the guard runs inside the window it is trying
# to bound.  What can close it is a check on the FILE, run by the tests
# that pin the migration, which is what this is.  It is a linter, not a
# guard, and it is named that way on purpose.


def _statements(text: str) -> "list[str]":
    """The migration's executable statements, comments stripped.

    Line comments only (`--`), which is every comment style the migrations
    in this repository use; a `/* */` block would need a real tokenizer and
    none exists in the corpus to justify one.
    """
    code = "\n".join(
        line for line in text.splitlines()
        if not line.strip().startswith("--")
    )
    return [s.strip() for s in code.split(";") if s.strip()]


def _mentions(statement: str, table: str) -> bool:
    """Is ``table`` named as a WHOLE identifier anywhere in ``statement``?

    Written by hand rather than with `re` on purpose: the test beside this
    module pins that this file imports nothing but `__future__`, which is
    what proves a helper whose whole job is to RETURN SQL never runs any.
    A regular expression would be the first import, and the next reader
    would have a weaker pin to argue with.

    Whole-identifier, so ``character_skills`` does not match
    ``character_skills_rebuild`` -- the scaffold `018` creates and drops
    entirely inside the guard's own window, which a substring test would
    report as a violation on every honest rebuild in the repository.
    Case-insensitive because SQLite is.
    """
    target = table.lower()
    token: list[str] = []
    for character in statement.lower() + " ":
        if character.isalnum() or character == "_":
            token.append(character)
            continue
        if token and "".join(token) == target:
            return True
        token = []
    return False


def window_violations(text: str, table: str, tag: str) -> "tuple[str, ...]":
    """Everything wrong with WHERE the guard sits in a migration's file.

    Returns a tuple of human-readable problems -- empty means the file's
    guard window really does cover every statement that can touch
    ``table``:

      1. the snapshot exists at all;
      2. no statement before the snapshot mentions ``table`` (the D2
         corruption, which is invisible to the guard by construction);
      3. no statement after the LAST guard row mentions ``table`` (the
         mirror image: a corruption appended after the guard has already
         voted);
      4. the scaffold is dropped, so nothing ``_pf_`` survives.

    Case-insensitive on the table name because SQLite is; a statement is
    counted as "mentioning" the table when the name appears as a whole word
    in it, which over-reports rather than under-reports -- a linter that
    guesses wrong should send its author to look, not wave them through.
    """
    table = _identifier(table, "table")
    tag = _identifier(tag, "tag")
    statements = _statements(text)
    snapshot = snapshot_sql(table, tag).rstrip(";")
    problems: list[str] = []
    try:
        first = next(
            i for i, s in enumerate(statements) if s == snapshot
        )
    except StopIteration:
        return (
            f"the snapshot statement for {table} is not in this file "
            f"(expected {snapshot!r})",
        )
    guard_rows = [
        i for i, s in enumerate(statements)
        if s.startswith(f"INSERT INTO {tag}_guard(ok)")
    ]
    if not guard_rows:
        problems.append(f"no {tag}_guard rows in this file")
    for i in range(first):
        if _mentions(statements[i], table):
            problems.append(
                "statement %d touches %s before the snapshot: %s"
                % (i + 1, table, statements[i].splitlines()[0])
            )
    if guard_rows:
        for i in range(guard_rows[-1] + 1, len(statements)):
            if _mentions(statements[i], table):
                problems.append(
                    "statement %d touches %s after the last guard row: %s"
                    % (i + 1, table, statements[i].splitlines()[0])
                )
    for scaffold in (f"{tag}_before", f"{tag}_guard"):
        if any(s == f"CREATE TABLE {scaffold}" or
               s.startswith(f"CREATE TABLE {scaffold} ") or
               s.startswith(f"CREATE TABLE {scaffold}(")
               for s in statements):
            if not any(s == f"DROP TABLE {scaffold}" for s in statements):
                problems.append(f"{scaffold} is created but never dropped")
    return tuple(problems)
