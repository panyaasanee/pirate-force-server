"""LANE-DB: the birth path may name the three vitals and must not write the
fourth column -- graded on the STATEMENTS and on what SQLite is authorized to
touch, never on the value in the row.

WHY THIS FILE EXISTS, STATED CORRECTLY.  `COO-DECISION 20260901_1447` point 2
forbids the birth path from writing the fourth typed column (the one bound to
wire field x=7, `BasicAttr+0x54`, carried in this schema under the still-
unproven name `speed_walk`); `migrations/009_character_birth_defaults.sql` is
where that column's birth value comes from, as a column DEFAULT, and the
insertion point in `SQLiteStore.create_character` writes only the three vitals
`COO-DECISION 20260902_0444` ordered.

!! THE PREMISE THIS FILE WAS COMMISSIONED WITH IS FALSE, AND SAYING SO IS PART
OF THE FILE.  `COO-DECISION 20260902_2243` point 3 says appending the column to
the birth INSERT fails "zero tests".  That was measured on `f5b3fd1`; chief
landed the same-shaped guard one minute earlier in `3e0d8b97`
(`tests/test_birth_vitals_plug_is_pinned.py::TheFourthBirthValueTests`), and a
`pf-adversary` pass this round re-measured the mutation against the whole
suite at `6ff7eb09`: **16 tests fail**, chief's shape (a) among them.  So this
file is NOT the only sensor for that shape and must not be read as one.  What
it adds over chief's file is measured and listed below; what it still cannot
see is listed with it.

WHAT IT REFUSES.  No write reachable from character creation may reach the
fourth column -- whether it names it in a statement, reaches it positionally,
or reaches it from inside a trigger.

THE FOUR LAYERS, AND WHAT EACH ONE ALONE MISSES.

* STATIC (:class:`NoBirthStatementNamesTheFourthColumnTests`) parses
  `store.py`, walks `create_character` and, transitively, the methods it calls
  on ``self``, and reads the first argument of every
  `execute`/`executemany`/`executescript`.  It sees a forbidden write on a
  branch no fixture walks.  It is blind to anything not authored as a literal
  in that closure -- which is why an unreadable statement is a RED here (see
  below) and why the other three layers exist.
* EXECUTED STATEMENTS (:class:`TheExecutedBirthNamesOnlyTheThreeTests`)
  installs `sqlite3.Connection.set_trace_callback` and creates real characters
  against the real migration directory.  It sees writes issued from anywhere
  the CALLER issues them -- another module, SQL assembled at run time -- but
  only along the paths the fixtures walk, and never a trigger body: measured,
  the tracer repeats the top-level statement once per trigger invocation and
  never shows the trigger's own SQL.
* AUTHORIZED COLUMNS (same class) installs `set_authorizer`, which reports
  `SQLITE_UPDATE` with the TABLE AND COLUMN for every update SQLite compiles
  -- including the ones inside trigger bodies, which it attributes to the
  trigger by name.  This is the layer that does not care how the statement is
  spelled, and it is why a comment, a `WITH` prefix or a rename of the
  statement's shape cannot get an UPDATE past this file.
* SHAPE OF THE INSERT (same class).  `SQLITE_INSERT` carries no column, so an
  insert that reaches the column POSITIONALLY (`REPLACE INTO characters SELECT
  ...`) is invisible to every layer above.  It is caught by counting instead:
  a birth performs EXACTLY ONE insert into `characters`, and that one is
  required to be the column-listed INSERT the static layer already read.  A
  second one is refused whatever it contains.
* THE SCHEMA ITSELF (same class) reads every trigger on `characters` from
  `sqlite_master`, because a trigger's text lives in a migration rather than
  in `store.py` and the static layer cannot see it.

FAIL-CLOSED ON A STATEMENT IT CANNOT READ.  A birth-path `execute` whose first
argument is not a plain string literal is a RED, not a skip: a scanner that
silently skips what it cannot parse is the dead sensor this file replaces.
The cost is real and is stated rather than hidden -- rewriting even a pure
SELECT in this closure as an f-string turns this file red, and the fail
message says so and says which statement.

WHAT IT STILL CANNOT SEE, NAMED RATHER THAN LEFT FOR THE NEXT ADVERSARY PASS.
A write placed on a branch no fixture walks (a helper called only for the
fourth character, say) is covered by the static layer only when it is authored
inside the `self.` closure; a module-level function called from
`create_character` under such a branch is seen by NEITHER the static walk nor
the dynamic layers.  The fixtures walk three births and a retry, which is
where that residual is smallest, not zero.

WHAT IT DELIBERATELY DOES NOT DO.

* It never asserts the column is `NULL` or holds any particular number.
  `COO-DECISION 20260902_2243` point 3 forbids that spelling by name, and
  after `009` the column is NOT NULL on a newborn row, so a NULL-shaped
  assertion would be red on a correct database.
* It does not grade `migrations/009`; that is
  `tests/test_persistence_birth_defaults_009.py`.
* It does not name the column as a string.  The name comes from
  `persistence_typed_attrs.COLUMN_FOR_X[7]`, by the WIRE FIELD, for the reason
  `tests/pf_birth_state.py` gives at its own `SPEED_COLUMN`.  A rename moves
  this guard with it.
"""
from __future__ import annotations

import ast
import contextlib
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pirateforce_foundation import persistence_typed_attrs as typed  # noqa: E402
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation import store as store_module  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from test_persistence_typed_attr_columns import (  # noqa: E402
    NoHandleOutlivesItsTempDirMixin,
    _is_sqlite_connect,
    bare_with_connect_sites,
    unclosed_connect_sites,
)

MIGRATIONS = ROOT / "migrations"

#: Read through a module global rather than inline so the mutation pass can
#: point the SHIPPED assertions at a doctored copy and require them to fail.
STORE_SOURCE = ROOT / "src" / "pirateforce_foundation" / "store.py"

#: The forbidden column, by its wire field rather than by its name.  x=7 is
#: `BasicAttr+0x54`, `float32`, client default 400.0 (reference_codex_attr).
FOURTH_COLUMN = typed.COLUMN_FOR_X[7]

#: The columns the birth INSERT is REQUIRED to name -- from the module that
#: owns them, so a rename there is red here instead of silently unmeasured.
THE_THREE = tuple(vitals.VITAL_COLUMNS)

#: Text that WRITES, matched anywhere rather than at the start of the string.
#:
#: !! ANCHORING THIS WAS A MEASURED DEFECT, NOT A STYLE CHOICE.  The first
#: draft used `^\s*(INSERT|REPLACE|UPDATE)` with `.match()`; a `pf-adversary`
#: pass got three real forbidden writes past it with nothing but a prefix --
#: a leading `-- comment`, a leading `/* comment */`, and a `WITH t(v) AS
#: (...) UPDATE ...` -- each landing 777.0 on the newborn row with this file
#: reporting all green.  A trigger body (`CREATE TRIGGER ... BEGIN UPDATE
#: ...`) is a fourth.  Unanchored costs nothing here because a hit also has
#: to NAME the forbidden column: `SELECT speed_walk FROM ...` is not a match,
#: and that is asserted rather than asserted-about.
_WRITES = re.compile(r"\b(INSERT\s+INTO|REPLACE\s+INTO|UPDATE)\b", re.IGNORECASE)

_EXECUTORS = ("execute", "executemany", "executescript")

#: `set_authorizer` action codes used here.  Named through the module so a
#: build with different numbering cannot silently make this layer inert.
_SQLITE_UPDATE = sqlite3.SQLITE_UPDATE
_SQLITE_INSERT = sqlite3.SQLITE_INSERT


def _names(text: str, column: str) -> bool:
    """Does ``text`` mention ``column`` as a word?

    Word-bounded so a future `speed_walk_updated_at` is not a false hit.  No
    `;`-splitting anywhere in this file: CPython's trace callback hands over
    EXPANDED sql, so a `;` inside a character name would have truncated the
    graded text and dropped the offence that followed it (measured on
    `UPDATE characters SET name='Bo;b', speed_walk=777.0`).
    """
    return re.search(r"\b%s\b" % re.escape(column), text,
                     re.IGNORECASE) is not None


def offending_writes(text: str) -> list[str]:
    """The write fragments in ``text`` that name the forbidden column."""
    if not text:
        return []
    if _WRITES.search(text) and _names(text, FOURTH_COLUMN):
        return [" ".join(text.split())]
    return []


class BirthStatement:
    """One statement the birth path issues, and where it was written."""

    def __init__(self, method: str, lineno: int, sql: str | None,
                 unparsed: str):
        self.method = method
        self.lineno = lineno
        #: ``None`` when the call site did not hand over a readable literal.
        self.sql = sql
        self.unparsed = unparsed

    @property
    def where(self) -> str:
        return "SQLiteStore.%s (store.py:%d)" % (self.method, self.lineno)

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        body = self.sql if self.sql is not None else self.unparsed
        return "<%s: %s>" % (self.where, " ".join(body.split())[:160])


def scan_birth_path(source: str) -> tuple[list[BirthStatement], list[str]]:
    """Every statement reachable from ``SQLiteStore.create_character``.

    The walk follows calls on ``self`` into other methods of the same class,
    because the birth path really does reach the database through them
    (`_insert_initial_backpack`, `get_character`): a scan that stopped at
    `create_character`'s own body is defeated by moving one line into a
    helper, which is measured -- that shape is green in the sibling guard and
    red here.

    An absent class or method is an :class:`AssertionError` rather than an
    empty result, so a rename cannot turn this file into a test that passes
    by measuring nothing.
    """
    tree = ast.parse(source)
    classes = [node for node in ast.walk(tree)
               if isinstance(node, ast.ClassDef) and node.name == "SQLiteStore"]
    if not classes:
        raise AssertionError(
            "store.py no longer defines a class named SQLiteStore, so the "
            "birth path cannot be located; this scanner must be pointed at "
            "the new insertion point rather than left to pass on nothing")
    methods = {node.name: node for node in ast.walk(classes[0])
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if "create_character" not in methods:
        raise AssertionError(
            "SQLiteStore no longer defines create_character; the birth path "
            "has moved and this guard is measuring nothing until it is "
            "pointed at the new one (methods seen: %r)" % (sorted(methods),))

    statements: list[BirthStatement] = []
    walked: list[str] = []
    queue = ["create_character"]
    seen: set[str] = set()
    while queue:
        name = queue.pop(0)
        if name in seen or name not in methods:
            continue
        seen.add(name)
        walked.append(name)
        for node in ast.walk(methods[name]):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if (isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "self"):
                queue.append(node.func.attr)
            if node.func.attr not in _EXECUTORS:
                continue
            argument = node.args[0] if node.args else None
            unparsed = ast.unparse(argument) if argument is not None else ""
            sql = None
            if (isinstance(argument, ast.Constant)
                    and isinstance(argument.value, str)):
                sql = argument.value
            statements.append(
                BirthStatement(name, node.lineno, sql, unparsed))
    return statements, walked


def static_offences(source: str) -> tuple[list[tuple[str, str]],
                                          list[BirthStatement]]:
    """``(writes, unreadable)`` for one `store.py` source.

    ONE implementation, called by the shipped assertions AND by the mutation
    pass, because a mutation pass that re-implements the check grades a
    private copy: a `pf-adversary` pass emptied both shipped assertions and
    the file still reported all green.  The mutation pass now RUNS the
    shipped assertions (see :class:`TheShippedGuardsReallyFireTests`); this
    function is what they share.
    """
    statements, _walked = scan_birth_path(source)
    writes = []
    unreadable = []
    for statement in statements:
        if statement.sql is None:
            unreadable.append(statement)
            continue
        for fragment in offending_writes(statement.sql):
            writes.append((statement.where, fragment))
    return writes, unreadable


class BirthRecorder:
    """What SQLite was asked to run, and what it was authorized to touch."""

    def __init__(self):
        self.statements: list[str] = []
        self.column_updates: list[tuple[str, str, str | None]] = []
        self.inserts: list[str] = []

    def authorize(self, action, arg1, arg2, dbname, source):
        if action == _SQLITE_UPDATE and arg1 == "characters":
            self.column_updates.append((arg1, arg2, source))
        elif action == _SQLITE_INSERT and arg1 == "characters":
            self.inserts.append(source or "<top level>")
        return sqlite3.SQLITE_OK

    @property
    def writes(self) -> list[str]:
        return [" ".join(text.split()) for text in self.statements
                if _WRITES.search(text)]

    def offences(self) -> list[str]:
        found = [fragment for text in self.statements
                 for fragment in offending_writes(text)]
        found += ["authorized UPDATE of %s.%s (from %s)"
                  % (table, column, source or "the statement itself")
                  for table, column, source in self.column_updates
                  if column == FOURTH_COLUMN]
        return found


@contextlib.contextmanager
def traced_sql():
    """Record statements and authorized columns for the duration of the block.

    !! THIS PATCH IS GLOBAL AND THE FIRST DRAFT'S DOCSTRING CLAIMED IT WAS
    NARROW.  `store_module.sqlite3 is sqlite3` -- measured True -- so every
    `sqlite3.connect` in the process is wrapped while the block runs.  That is
    acceptable here and it is written down rather than dressed up: the gate
    runs pytest serially (`.github/workflows/gate-windows.yml`), the block
    spans one store call, and a connection that outlived the block would
    produce spurious REDS, never a false green.  It would record nothing at
    all if `store.py` switched to `from sqlite3 import connect`, and that is
    caught by the positive control below rather than left to chance.
    """
    recorder = BirthRecorder()
    real_connect = store_module.sqlite3.connect

    def connect(*args, **kwargs):
        db = real_connect(*args, **kwargs)
        db.set_trace_callback(recorder.statements.append)
        db.set_authorizer(recorder.authorize)
        return db

    with mock.patch.object(store_module.sqlite3, "connect", connect):
        yield recorder


def _build_wire(selector):
    return b"wire-%d" % selector, b"avatar", 0x30000001 + selector, 0


class TheBirthPathIsReadableTests(unittest.TestCase):
    """The static layer's own preconditions.  Each of these failing means the
    LAYER is broken, not the code it grades, and the messages say so."""

    def setUp(self):
        self.statements, self.walked = scan_birth_path(
            STORE_SOURCE.read_text(encoding="utf-8"))

    def test_the_walk_reaches_the_helpers_the_birth_path_writes_through(self):
        """Named, not counted.  A count would pass while the walk quietly
        stopped following `self` calls -- which is how a forbidden write is
        hidden from the static layer (measured: that shape is green in the
        sibling guard)."""
        for method in ("create_character", "_insert_initial_backpack"):
            self.assertIn(
                method, self.walked,
                "the birth-path walk no longer reaches %s, so a write placed "
                "there would not be graded by this file (walked: %r)"
                % (method, self.walked))

    def test_every_birth_statement_is_a_literal_this_file_can_read(self):
        unreadable = [s for s in self.statements if s.sql is None]
        self.assertEqual(
            [], unreadable,
            "the birth path issues SQL this guard cannot read, and an "
            "unreadable statement is a RED here rather than a skip: %s.  "
            "This fires on a READ rewritten as an f-string too -- that is the "
            "price of the rule, not a bug in it.  Either write the statement "
            "as a literal, or amend this file (and say so to COO) so that "
            "allowing assembled SQL on the birth path is a decision somebody "
            "takes rather than a hole nobody sees."
            % ", ".join("%s -> %s" % (s.where, s.unparsed)
                        for s in unreadable))

    def test_the_scan_really_found_the_writes_it_claims_to_grade(self):
        """The anti-vacuity line.  A scanner returning zero write statements
        would pass the next class while measuring nothing.  The pin is four
        write STATEMENTS -- `characters`, `character_positions`,
        `character_backpacks` and one `INSERT` for the starting items; the
        item insert is one statement per item, so this number is a floor and
        not a headcount of rows."""
        writes = [s for s in self.statements
                  if s.sql is not None and _WRITES.search(s.sql)]
        self.assertGreaterEqual(
            len(writes), 4,
            "the birth-path scan found %d write statements, which is fewer "
            "than the ones known to be there; the walk is broken"
            % len(writes))


class NoBirthStatementNamesTheFourthColumnTests(unittest.TestCase):
    """Layer one: the text `store.py` authors."""

    def test_no_write_on_the_birth_path_names_the_fourth_column(self):
        writes, _unreadable = static_offences(
            STORE_SOURCE.read_text(encoding="utf-8"))
        self.assertEqual(
            [], writes,
            "the birth path writes the column COO-DECISION 20260901_1447 "
            "point 2 forbids it to write (%r, the typed column for wire "
            "field x=7).  The statement seen was:\n%s\n"
            "Refused at the STATEMENT and not at the value on purpose: since "
            "migrations/009 gives that column the same default this write "
            "would supply, no expectation about the row can tell the two "
            "apart.  The birth value comes from the column DEFAULT; the "
            "insertion point names %r and nothing else."
            % (FOURTH_COLUMN,
               "\n".join("  %s: %s" % pair for pair in writes),
               list(THE_THREE)))

    def test_the_birth_insert_still_names_the_three_it_must(self):
        """The other half of the file's name.  A birth INSERT that stopped
        naming the three vitals would satisfy the refusal above and reopen the
        hole `COO-DECISION 20260902_0444` closed, so the positive is asserted
        beside the negative."""
        statements, _walked = scan_birth_path(
            STORE_SOURCE.read_text(encoding="utf-8"))
        inserts = [s.sql for s in statements
                   if s.sql is not None
                   and "INSERT" in s.sql.upper()
                   and _names(s.sql, "characters")]
        named = [sql for sql in inserts
                 if all(_names(sql, column) for column in THE_THREE)]
        self.assertEqual(
            1, len(named),
            "exactly one birth INSERT into `characters` must name all three "
            "vitals %r; found %d among %d candidate INSERT statements.  Zero "
            "means the birth plug was reverted (COO-DECISION 20260902_0444); "
            "more than one means there are two insertion points and only one "
            "of them is graded."
            % (list(THE_THREE), len(named), len(inserts)))


class TheExecutedBirthNamesOnlyTheThreeTests(
        NoHandleOutlivesItsTempDirMixin, unittest.TestCase):
    """Layers two, three, four and five: what SQLite was really asked to run,
    what it was authorized to touch, how many inserts a birth performs, and
    what the schema itself would run behind all of that.

    !! THE RUNTIME HANDLE GUARD IS THE ONE THAT MATTERS HERE.  This is the
    class that opens raw handles through `_raw`, and the AST pins at the
    bottom of this file grade the SOURCE.  The mixin asks the operating
    system instead, after every test, whether a descriptor under the temp
    directory survived -- which is the question the Windows gate asks by
    refusing the unlink, and the one that closed `#495` and `#610`.
    Registered after the directory's own cleanup so LIFO runs it first.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.guard_the_temp_dir(self.tmp)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.account_id = self.store.ensure_account("birth-statements")
        self.home = Position(1, 0, 1.0, 2.0, 3.0, heading=0.0)

    def _create(self, name, tag, store=None, account_id=None):
        store = store or self.store
        with traced_sql() as recorder:
            character = store.create_character(
                account_id or self.account_id, name, tag, "fingerprint-" + tag,
                _build_wire, self.home)
        return character, recorder

    @contextlib.contextmanager
    def _raw(self, path=None):
        """A raw handle that this helper -- not its caller -- is responsible
        for closing.

        !! IT USED TO RETURN THE HANDLE AND LEAVE CLOSING TO THE CALLER, and
        that shape is the one `NoUnclosedSqliteHandleInThisFileTests` at the
        bottom of this file cannot grade: the function that opens a handle
        and hands it out contains no `.close()` of its own, so the pin either
        reports it forever or is weakened into blindness.  Every call site
        below did close it in a `finally`; a future round adding a fourth one
        had nothing making it.  Now the ownership sits in one place and the
        pin reads it correctly.
        """
        db = sqlite3.connect(str(path or self.path))
        try:
            yield db
        finally:
            db.close()

    # ---- positive and negative controls for the recorders --------------

    def test_the_recorder_sees_the_birth_insert_itself(self):
        """Every refusal in this class is worthless if the callbacks record
        nothing -- and a callback that is never installed looks exactly like a
        birth that writes nothing forbidden."""
        _character, recorder = self._create("Traced", "traced")
        self.assertTrue(
            any(w.upper().startswith("INSERT INTO CHARACTERS")
                for w in recorder.writes),
            "the SQL recorder saw no INSERT INTO characters during character "
            "creation, so it is not recording and this class is measuring "
            "nothing (saw %d write statements)" % len(recorder.writes))
        self.assertEqual(
            1, len(recorder.inserts),
            "the authorizer recorded %d inserts into `characters` for one "
            "birth; it is not installed, or a birth is no longer one insert"
            % len(recorder.inserts))

    def test_the_detector_would_report_a_write_handed_to_it_directly(self):
        with traced_sql() as recorder:
            with self.store.connect() as db:
                db.execute(
                    "UPDATE characters SET %s=? WHERE id=?"
                    % FOURTH_COLUMN, (401.0, -1))
        self.assertTrue(
            recorder.offences(),
            "the detector did not report a write it was handed directly; it "
            "cannot be trusted to report one issued by the birth path "
            "(statements seen: %r)" % (recorder.writes,))

    def test_the_authorizer_reports_a_column_a_comment_hides_from_the_text(
            self):
        """The prefix evasions that beat the first draft (`-- comment`,
        `/* comment */`, `WITH ... UPDATE`) reach the column through an
        UPDATE, and an UPDATE always names its columns to the authorizer --
        so this layer does not depend on the statement's spelling at all."""
        with traced_sql() as recorder:
            with self.store.connect() as db:
                db.execute(
                    "-- birth speed\nWITH t(v) AS (SELECT 401.0) "
                    "UPDATE characters SET %s=(SELECT v FROM t) WHERE id=?"
                    % FOURTH_COLUMN, (-1,))
        self.assertTrue(
            [c for c in recorder.column_updates if c[1] == FOURTH_COLUMN],
            "the authorizer did not report the column of an UPDATE it "
            "compiled; this layer is inert (updates seen: %r)"
            % (recorder.column_updates,))
        self.assertTrue(recorder.offences())

    # ---- the refusals --------------------------------------------------

    def test_creating_a_character_reaches_the_fourth_column_no_way_at_all(
            self):
        _character, recorder = self._create("Firstborn", "firstborn")
        self.assertEqual(
            [], recorder.offences(),
            "creating a character reached %r.  The birth value of that column "
            "comes from the DEFAULT installed by migrations/009; the "
            "insertion point is forbidden to write it (COO-DECISION "
            "20260901_1447 point 2)." % (FOURTH_COLUMN,))

    def test_a_birth_performs_exactly_one_insert_into_characters(self):
        """`SQLITE_INSERT` carries no column name, so an insert that reaches
        the fourth column POSITIONALLY -- `REPLACE INTO characters SELECT
        <35 columns> FROM ...` -- names nothing and is invisible to every
        text-based layer here (measured: green in both this file's first draft
        and the sibling guard, with 400.0 landing on the row).  Counting is
        what closes it: a birth inserts into `characters` once."""
        for name, tag in (("Firstborn", "firstborn"),
                          ("Secondborn", "secondborn"),
                          ("Thirdborn", "thirdborn")):
            _character, recorder = self._create(name, tag)
            self.assertEqual(
                1, len(recorder.inserts),
                "creating %s performed %d inserts into `characters` (%r).  A "
                "birth is ONE insert; a second one can reach the fourth "
                "column positionally without naming it anywhere."
                % (name, len(recorder.inserts), recorder.inserts))

    def test_the_second_and_third_characters_are_measured_too(self):
        """The regression shape the sibling helpers exist for: a plug that
        behaves for an account's first character and misbehaves for every one
        after it was green across the whole suite once already.  Three births
        rather than two because a `pf-adversary` pass reached the column under
        `if selector >= 2`."""
        self._create("Firstborn", "firstborn")
        for name, tag in (("Secondborn", "secondborn"),
                          ("Thirdborn", "thirdborn")):
            _character, recorder = self._create(name, tag)
            self.assertEqual(
                [], recorder.offences(),
                "character %s reached %r during its birth: %r"
                % (name, FOURTH_COLUMN, recorder.offences()))

    def test_a_retried_creation_reaches_nothing_either(self):
        """The idempotent-retry branch returns the existing row; it is a
        distinct path through the method and it is walked rather than assumed
        harmless."""
        first, _ = self._create("Retried", "retried")
        with traced_sql() as recorder:
            again = self.store.create_character(
                self.account_id, "Retried", "retried", "fingerprint-retried",
                _build_wire, self.home)
        self.assertEqual(first.id, again.id)
        self.assertEqual([], recorder.offences())
        self.assertEqual(
            [], recorder.inserts,
            "the retry branch inserted into `characters` (%r); it is supposed "
            "to return the existing row" % (recorder.inserts,))

    def test_no_trigger_writes_the_fourth_column_behind_the_recorders(self):
        """The evasion the statement layers cannot see, closed at the schema.

        Measured, not feared: `set_trace_callback` reports the statement the
        CALLER issued and never the trigger body SQLite runs underneath it,
        and a trigger's text lives in a migration rather than in `store.py`.
        The authorizer DOES see a trigger's UPDATE, which is why this check
        and that one are both here -- this one catches a trigger that exists
        even on a path no fixture walks.
        """
        with self._raw() as db:
            triggers = db.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='trigger' "
                "AND tbl_name='characters'").fetchall()
        offenders = [(name, fragment) for name, sql in triggers
                     for fragment in offending_writes(sql or "")]
        self.assertEqual(
            [], offenders,
            "a trigger on `characters` writes %r: %r.  A migration that "
            "installs one puts the fourth birth value on every newborn row "
            "with no statement in store.py to show for it."
            % (FOURTH_COLUMN, offenders))

    def test_the_trigger_layers_really_fire_on_a_migration_that_adds_one(self):
        """The mutation for the two trigger checks, run for real: a scratch
        migration directory with one extra file that installs exactly the
        forbidden trigger.  Both the schema read and the authorizer must
        report it -- otherwise those checks pass because the query is wrong
        rather than because the schema is clean (today `characters` carries
        zero triggers, so the two are indistinguishable without this).

        THE EXTRA FILE'S VERSION IS DERIVED, NOT A LITERAL `010`.  It was a
        literal until round `5d02mu`, when `010_ground_drops.sql` landed for
        real and this probe's own hard-coded `010` collided with it
        (`RuntimeError: duplicate migration version`) -- the same class of
        failure `BootSnapshotProtects008Tests.test_a_snapshot_is_due_while_
        008_is_the_pending_file` hit for the same reason.  One free slot
        past whatever this tree's own newest real migration is stays free
        forever, unlike a number typed here.
        """
        scratch = Path(self.tmp.name) / "migrations"
        shutil.copytree(MIGRATIONS, scratch)
        newest = max(
            int(path.name[:3])
            for path in scratch.glob("[0-9][0-9][0-9]_*.sql")
        )
        (scratch / ("%03d_probe_speed_trigger.sql" % (newest + 1))).write_text(
            "CREATE TRIGGER pf_probe_speed AFTER INSERT ON characters\n"
            "BEGIN UPDATE characters SET %s=777.0 WHERE id=NEW.id; END;\n"
            % FOURTH_COLUMN, encoding="utf-8")
        path = Path(self.tmp.name) / "planted.sqlite3"
        store = SQLiteStore(path, scratch)
        store.migrate()
        account = store.ensure_account("planted")
        _character, recorder = self._create(
            "Planted", "planted", store=store, account_id=account)

        with self._raw(path) as db:
            triggers = db.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='trigger' "
                "AND tbl_name='characters'").fetchall()
        self.assertTrue(
            [f for _name, sql in triggers for f in offending_writes(sql or "")],
            "the schema read did not report a trigger written to be reported")
        self.assertTrue(
            recorder.offences(),
            "the authorizer did not report the trigger's UPDATE; it reports "
            "trigger subprograms by name on this build, so an empty result "
            "means this layer is inert (updates seen: %r)"
            % (recorder.column_updates,))

    def test_the_column_still_holds_its_default_after_all_of_this(self):
        """Not a value assertion standing in for the guard -- the guards are
        above.  This is the sanity line saying the refusals are made in a
        world where the column EXISTS and the MIGRATION populates it, which is
        the only world in which refusing the write is the right answer.  Red
        here means 009 is the thing to look at."""
        character, _ = self._create("Defaulted", "defaulted")
        with self._raw() as db:
            row = db.execute(
                "SELECT %s FROM characters WHERE id=?" % FOURTH_COLUMN,
                (character.id,)).fetchone()
        self.assertIsNotNone(row)
        self.assertIsNotNone(
            row[0],
            "the fourth column is empty on a newborn row, so the DEFAULT from "
            "migrations/009 is not doing the job the birth path is forbidden "
            "to do for it")


class TheShippedGuardsReallyFireTests(unittest.TestCase):
    """The mutation pass, pointed at the SHIPPED assertions.

    !! THE FIRST DRAFT GRADED A PRIVATE COPY.  It re-implemented the check in
    a helper and asserted on that; a `pf-adversary` pass replaced the bodies
    of BOTH shipped static assertions with `return` and the file still
    reported all green -- a mutation pass proving that its own helper fires
    and nothing about the tests that ship.  Every mutation below writes a
    doctored `store.py` to a temporary file, points the module's
    `STORE_SOURCE` at it, RUNS the real test method, and requires a real
    failure.
    """

    def _doctored(self, needle: str, replacement: str) -> str:
        source = STORE_SOURCE.read_text(encoding="utf-8")
        self.assertIn(needle, source,
                      "the anchor this mutation edits is gone from store.py; "
                      "the mutation is no longer the shape it claims to test")
        return source.replace(needle, replacement, 1)

    def _failures(self, source: str, method: str,
                  klass=NoBirthStatementNamesTheFourthColumnTests):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "store.py"
            path.write_text(source, encoding="utf-8")
            with mock.patch.object(sys.modules[__name__], "STORE_SOURCE",
                                   path):
                case = klass(method)
                result = case.defaultTestResult()
                case.run(result)
                return result.failures + result.errors

    def _refused(self, source, method="test_no_write_on_the_birth_path_"
                                     "names_the_fourth_column", klass=None):
        klass = klass or NoBirthStatementNamesTheFourthColumnTests
        failures = self._failures(source, method, klass)
        self.assertEqual(
            1, len(failures),
            "the SHIPPED assertion %s.%s did not fail on a doctored source "
            "it must refuse" % (klass.__name__, method))
        return failures[0][1]

    def test_the_shipped_assertions_pass_on_the_real_source(self):
        """The baseline every mutation below is measured against.  Without it
        a mutation that 'fails' could be failing for a reason that has nothing
        to do with the shape it planted."""
        source = STORE_SOURCE.read_text(encoding="utf-8")
        for method in ("test_no_write_on_the_birth_path_names_the_fourth_"
                       "column",
                       "test_the_birth_insert_still_names_the_three_it_must"):
            self.assertEqual([], self._failures(source, method))
        self.assertEqual(
            [], self._failures(
                source, "test_every_birth_statement_is_a_literal_this_file_"
                        "can_read", TheBirthPathIsReadableTests))

    def test_it_catches_the_fourth_column_appended_to_the_birth_insert(self):
        """The shape `COO-DECISION 20260902_2243` point 3 is about -- the
        column appended with the SAME value 009 defaults it to."""
        message = self._refused(self._doctored(
            "created_at,updated_at,level,hp_current,hp_max)",
            "created_at,updated_at,level,hp_current,hp_max,%s)"
            % FOURTH_COLUMN))
        self.assertIn(FOURTH_COLUMN, message)

    def test_it_catches_an_update_after_the_insert(self):
        self._refused(self._doctored(
            "            cid = int(cur.lastrowid)",
            "            cid = int(cur.lastrowid)\n"
            "            db.execute(\"UPDATE characters SET %s=400.0 "
            "WHERE id=?\", (cid,))" % FOURTH_COLUMN))

    def test_it_catches_a_write_a_leading_comment_hides(self):
        """The measured escape from the first draft's anchored pattern."""
        for prefix in ("-- birth speed\\n", "/* birth */ ",
                       "WITH t(v) AS (SELECT 400.0) "):
            with self.subTest(prefix=prefix):
                self._refused(self._doctored(
                    "            cid = int(cur.lastrowid)",
                    "            cid = int(cur.lastrowid)\n"
                    "            db.execute(\"%sUPDATE characters SET "
                    "%s=400.0 WHERE id=?\", (cid,))"
                    % (prefix, FOURTH_COLUMN)))

    def test_it_catches_the_write_hidden_one_helper_deep(self):
        """Moved into `_insert_initial_backpack`, which the birth path calls:
        a scanner reading only `create_character`'s body is green (measured
        on the sibling guard, which lists its methods by hand)."""
        self._refused(self._doctored(
            '            "INSERT INTO character_backpacks(',
            '            "UPDATE characters SET %s=400.0 WHERE id=?",\n'
            '            (character_id,),\n'
            '        )\n'
            '        db.execute(\n'
            '            "INSERT INTO character_backpacks(' % FOURTH_COLUMN))

    def test_it_refuses_a_statement_it_cannot_read_instead_of_skipping_it(self):
        message = self._refused(
            self._doctored(
                '            cid = int(cur.lastrowid)',
                '            cid = int(cur.lastrowid)\n'
                '            db.execute(f"UPDATE characters SET {_col}=400.0 '
                'WHERE id={cid}")'),
            method="test_every_birth_statement_is_a_literal_this_file_can_read",
            klass=TheBirthPathIsReadableTests)
        self.assertIn("cannot read", message)

    def test_it_reads_past_the_first_statement_of_a_script(self):
        self._refused(self._doctored(
            '            cid = int(cur.lastrowid)',
            '            cid = int(cur.lastrowid)\n'
            '            db.executescript("SELECT 1; UPDATE characters SET '
            '%s=400.0;")' % FOURTH_COLUMN))

    def test_it_catches_the_plug_being_reverted(self):
        """The shape chief's letter `20260902_1925` measured going green
        across the whole suite: the birth INSERT back to twelve columns."""
        source = self._doctored(
            "created_at,updated_at,level,hp_current,hp_max) VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            "created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)")
        self._refused(
            source,
            method="test_the_birth_insert_still_names_the_three_it_must")

    def test_a_read_of_the_column_is_not_an_offence(self):
        """The refusal is about WRITES.  A SELECT naming the column is how
        every other test in the tree reads it, and a guard that reddened on
        one would be removed within a round."""
        source = self._doctored(
            '            cid = int(cur.lastrowid)',
            '            cid = int(cur.lastrowid)\n'
            '            db.execute("SELECT %s FROM characters WHERE id=?", '
            '(cid,))' % FOURTH_COLUMN)
        self.assertEqual([], self._failures(
            source, "test_no_write_on_the_birth_path_names_the_fourth_column"))

    def test_a_missing_insertion_point_is_an_error_not_an_empty_result(self):
        source = STORE_SOURCE.read_text(encoding="utf-8").replace(
            "    def create_character(", "    def create_character_renamed(", 1)
        with self.assertRaises(AssertionError) as caught:
            scan_birth_path(source)
        self.assertIn("create_character", str(caught.exception))


class NoUnclosedSqliteHandleInThisFileTests(unittest.TestCase):
    """The house pin against the leak that has now closed three pull requests.

    `with sqlite3.connect(path) as db:` commits on exit and does NOT close.
    On Linux the surviving handle is silent -- the test body prints the right
    answer and passes.  On the Windows gate `TemporaryDirectory.cleanup`
    raises `PermissionError [WinError 32]` at TEARDOWN, after the assertions
    have already gone green.  It killed `#495`, then `#610` a month later
    four metres outside the one fence that existed, and `CHIEF-TO-ALL
    20260903_0154` asks every lane to carry this class into any file of its
    own that opens sqlite.  This file opens one raw handle -- `_raw`, the
    only `sqlite3.connect(...)` node in it -- so it carries it.

    !! IT DOES NOT CARRY THE COPY THE LETTER POINTED AT, AND THE THIRD DRAFT
    OF THIS CLASS IS WHY.  Draft one copied the two AST tests out of
    `tests/test_login_speed.py` verbatim.  A `pf-adversary` pass measured
    that copy against `unclosed_connect_sites` / `bare_with_connect_sites`,
    the predicate THIS LANE ALREADY OWNS in
    `tests/test_persistence_typed_attr_columns.py`, and the copy lost five
    ways: it walked `FunctionDef`s only (module-scope leak invisible), it
    accepted ANY `X.close()` in the function rather than a close bound to the
    opened name, and it reported `contextlib.closing(sqlite3.connect(...))`
    -- correct code its own sibling blesses by name -- as RED.  So draft two
    imported the lane's predicate instead of re-deriving it.

    !! DRAFT TWO THEN LOST THE ONE MUTANT THE VERBATIM COPY CAUGHT, and that
    is the lesson this class exists to carry.  `unclosed_connect_sites`
    treats `return db` as HANDING THE HANDLE ON, which is right in the file
    it was written for and wrong here: `_raw` stripped of its
    `@contextlib.contextmanager` and put back to `return sqlite3.connect(...)`
    was reported by the copy and is INVISIBLE to the import.  Measured, with
    the lane's own runtime helper rather than by argument:
    `open_handles_under(tmp)` after `with _raw(path) as db: ...` and a
    `gc.collect()` returned the live `state.sqlite3` descriptor -- the exact
    thing `TemporaryDirectory.cleanup` refuses to unlink on Windows -- while
    the file read `29 passed`.  A reviewer would have seen three call sites
    spelled `with self._raw() as db:` and no reason to doubt them.

    So draft three stops enumerating spellings and pins the PROPERTY the file
    actually depends on: **`_raw` is this file's only door to a sqlite
    handle, and it closes what it opens.**  That one rule kills the returning
    `_raw`, and it also kills three spellings draft two was measured green
    on: `store_module.sqlite3.connect(...)`, `sqlite3.dbapi2.connect(...)`
    (where the function really lives -- `sqlite3.connect is
    sqlite3.dbapi2.connect`), and `from sqlite3 import connect as _open`.
    Enumerating spellings would have needed a new test per spelling and
    missed the next one.

    The two imported checks stay, and they are not redundant: they grade what
    happens INSIDE `_raw` (a `_raw` that stops closing) and they carry the
    module-scope and bound-name coverage this file would otherwise have to
    re-derive.  One shape is red in both and is a house-wide property rather
    than a defect here: `db = sqlite3.connect(...)` with
    `self.addCleanup(db.close)`, because `db.close` there is an
    `ast.Attribute` and never an `ast.Call`.  It is written down so the next
    lane to hit it knows it is not alone.

    MEASURED on the commit this class ships with, by mutating this file in
    place and running it.  Each line reports the state WITH this class:
      * the shipped form -- `29 passed`.
      * `_raw` put back to `return sqlite3.connect(...)`, callers unchanged
        -- RED on `test_raw_is_the_only_door_and_it_closes_what_it_opens`.
        Draft two: fully green.
      * the same mutant with one call site given an explicit
        `try/finally: db.close()` -- RED on the same test.  Draft two: fully
        green.  (This is the exact mutant whose result draft two's docstring
        stated backwards; it is restated here from a re-run, not carried.)
      * a fixture rewritten as `with sqlite3.connect(str(self.path)) as db:`
        -- RED on the bare-`with` test and on the only-door test.  (Draft two
        claimed two tests here as well, but the second was the imported
        closed-handle check, which keys on `ast.Assign` and never fires on a
        `with` item.  One false number in a docstring is a defect, so it is
        named rather than quietly corrected.)
      * a fixture that opens a handle, reads, commits and never closes -- RED
        on the imported closed-handle test and on the only-door test.
      * a leaking fixture spelled `store_module.sqlite3.connect(...)`, or
        `sqlite3.dbapi2.connect(...)`, or through
        `from sqlite3 import connect as _open` -- each RED on the only-door
        test.  All three were GREEN in draft two.
      * `_raw` kept as a contextmanager but stripped of its `finally:
        db.close()` -- `4 failed`: the imported closed-handle test, plus the
        three tests that use `_raw`, through `NoHandleOutlivesItsTempDirMixin`
        asking the operating system whether a descriptor survived.  This is
        the half the only-door test does NOT cover, it is why both AST checks
        stay, and it is the one place where the guard on the class above
        answers the question the Windows gate really asks instead of a
        question about how the source is spelled.
      * this class deleted in ANY of those states -- fully green, which is
        exactly the blindness `#610` was written in.

    An AST pin rather than a text search: `grep` cannot tell a real call from
    the same characters inside this docstring, and exempting the docstring
    would put a hole in the pin for the sake of the pin.
    """

    #: The one call this file is allowed to make outside `_raw`.  It is the
    #: store's own `@contextmanager`, which closes in `finally`
    #: (`src/pirateforce_foundation/store.py`), so it is a door that shuts.
    STORE_DOOR = "self.store.connect"

    #: The function that owns every raw handle in this file.
    DOOR = "_raw"

    def _source(self):
        return Path(__file__).read_text(encoding="utf-8")

    @staticmethod
    def _dotted(node):
        """`sqlite3.dbapi2.connect` for the AST of that expression, or None."""
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
            return ".".join(reversed(parts))
        return None

    @classmethod
    def _sqlite3_import_aliases(cls, tree):
        """Names bound by `from sqlite3 import connect [as x]`.

        Without this, `from sqlite3 import connect as _open` opens a handle
        through a bare `ast.Name` that no `Attribute` rule can see -- measured
        green against all of draft two.
        """
        return {
            alias.asname or alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == "sqlite3"
            for alias in node.names
        }

    @classmethod
    def _handle_opening_calls(cls, tree):
        """Every call here that could hand back a live sqlite handle.

        Deliberately over-broad -- ANY `....connect(...)`, plus any name
        imported out of `sqlite3` -- because the failure mode being pinned is
        a spelling nobody thought of.  Over-breadth costs a named exemption
        (`STORE_DOOR`); under-breadth costs a silent green.
        """
        aliases = cls._sqlite3_import_aliases(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute) and node.func.attr == "connect":
                yield node, cls._dotted(node.func) or "<expr>.connect"
            elif isinstance(node.func, ast.Name) and node.func.id in aliases:
                yield node, node.func.id

    def test_the_pin_is_looking_at_something(self):
        """The positive control.  Every test in this class passes trivially
        on a file that opens no connection at all, so a refactor moving the
        last handle out of this file would leave them green while grading
        nothing -- the same false comfort as `#610`."""
        tree = ast.parse(self._source())
        raw = [node for node in ast.walk(tree) if _is_sqlite_connect(node)]
        self.assertTrue(
            raw,
            "this file no longer opens a sqlite connection in any spelling "
            "this class can see, so the checks below are green because there "
            "is nothing to grade.  Either the handles moved to a helper -- "
            "carry this class there -- or this class should go with them.")

    def test_raw_is_the_only_door_and_it_closes_what_it_opens(self):
        """The property, not a list of spellings.

        Two halves, and both are needed: every handle-opening call in this
        file is inside `_raw` (or is the store's own closing door), AND `_raw`
        hands its handle out through a `contextmanager` rather than by
        returning it.  See this class's docstring for the four spellings that
        were measured green before this test existed.
        """
        tree = ast.parse(self._source())
        door = next(
            (node for node in ast.walk(tree)
             if isinstance(node, ast.FunctionDef) and node.name == self.DOOR),
            None)
        self.assertIsNotNone(
            door, "`%s`, the function this file routes every raw handle "
                  "through, is gone; this class no longer describes the file"
                  % self.DOOR)

        inside_the_door = {id(node) for node in ast.walk(door)}
        strays = sorted(
            (node.lineno, spelling)
            for node, spelling in self._handle_opening_calls(tree)
            if id(node) not in inside_the_door
            and spelling != self.STORE_DOOR)
        self.assertEqual(
            strays, [],
            "a sqlite handle is opened outside `%s`, so nothing in this file "
            "owns closing it and no pin here grades it.  On the Windows gate "
            "a handle nobody closes makes TemporaryDirectory.cleanup raise "
            "PermissionError [WinError 32] at teardown, long after the "
            "assertions went green.  Take it from `%s`, which closes what it "
            "opens.  Offender(s): %r"
            % (self.DOOR, self.DOOR, strays))

        decorators = {self._dotted(d) or getattr(d, "id", None)
                      for d in door.decorator_list}
        self.assertIn(
            "contextlib.contextmanager", decorators,
            "`%s` no longer hands its handle out through a context manager, "
            "so it is returning a live connection for its callers to close. "
            "The lane's `unclosed_connect_sites` reads `return db` as handing "
            "the handle on and stays SILENT on this -- measured, with "
            "`open_handles_under` reporting the live descriptor while the "
            "file read green.  Decorators seen: %r" % (self.DOOR, decorators))

    def test_this_file_never_writes_the_leaking_with_form(self):
        """`with sqlite3.connect(...) as db:` -- the exact line that died."""
        leaking = bare_with_connect_sites(self._source())
        self.assertEqual(
            leaking, [],
            "`with sqlite3.connect(...)` commits but does NOT close.  On "
            "Linux the surviving handle is silent; on the Windows gate "
            "TemporaryDirectory.cleanup raises PermissionError [WinError 32] "
            "at TEARDOWN, after the test body has printed its correct "
            "result.  Take the handle from `_raw`, which closes what it "
            "opens, or write `contextlib.closing(...)`.  "
            "Offending line(s): %r" % (leaking,))

    def test_every_connection_this_file_opens_is_closed(self):
        """Opened, used, and then never closed -- graded inside `_raw` too.

        Uses the lane's own predicate, which reads module scope and binds the
        close to the opened name.  This is the check that catches a `_raw`
        that keeps its decorator and loses its `finally: db.close()`, which
        the only-door test above cannot see.
        """
        unclosed = unclosed_connect_sites(self._source())
        self.assertEqual(
            unclosed, [],
            "a sqlite connection is opened here and nothing closes it or "
            "hands it on.  On the Windows gate that handle makes "
            "TemporaryDirectory.cleanup raise PermissionError [WinError 32] "
            "at teardown, long after the assertions went green.  "
            "Offending line(s): %r" % (unclosed,))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
