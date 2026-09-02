"""LANE-DB: what a newly created character is holding, in a repository where
that answer is about to change under every test in this lane.

WHY THIS FILE EXISTS.  `COO-DECISION 20260902_0444` tells chief to name
`level`, `hp_current` and `hp_max` in the INSERT of
`SQLiteStore.create_character`, taking the three numbers from this lane's
`persistence_vitals.new_character_vitals()`.  Round `cby3pd` simulated that
one line and measured the result: **33 tests go red, and all 33 are pins this
lane wrote itself**, in three files chief may not edit.  Every one of them
says some version of the same sentence -- "a character that was just created
holds no typed value at all" -- which is true today and false the moment the
plug lands.  They are this lane's mines in another lane's corridor, and
removing them is this lane's job, not his.

WHAT THIS MODULE DOES ABOUT IT, AND WHAT IT REFUSES TO DO.  The cheap fix
would be to delete the assertions, or to loosen them into `assertIn`.  Both
would buy chief a green PR by giving up the thing the pins were built to
catch: a birth that writes the WRONG numbers is exactly as invisible to a
loosened test as no birth at all.  So the strictness is not removed, it is
MOVED -- into one function that every affected test calls first:

    `clear_birth_vitals(store, character_id)` refuses any world but the two
    that are allowed.  Either the row holds nothing yet (today), or it holds
    EXACTLY `new_character_vitals()` -- all three columns, those values, and
    no fourth column seeded.  A birth that writes `1/50/50`, that seeds
    `level = 0`, that also seeds `speed_walk`, or that fills only
    `hp_current`, does not reach the test body at all: it dies here, in a
    named assertion, with the row printed.

Only after that check does it return the row to the unseeded state the test
was written against, by NULLing those three columns on THAT ONE ROW.  So the
test bodies keep their absolute `assertEqual(..., {})` spellings, unchanged,
and the two worlds meet in this file alone.

WHAT IT DELIBERATELY DOES NOT COVER, so no reader over-reads it.  It looks at
ONE ROW, so it cannot see a plug whose UPDATE forgot its `WHERE id` and reset
every other character, nor one that seeds only on the retry branch; and it
compares VALUES, so it cannot see a plug that typed `(1, 100, 100)` in by hand
instead of calling the function.  Those are measured on purpose in
`test_persistence_vitals_seed_007.SeedsACohortNotADatabaseTests`, which owns
the multi-row and the source-level doors.  Duplicating them here would spread
one promise over two files without adding a measurement.

And one thing it DOES cover that an earlier draft only claimed to: a birth
that seeds a FOURTH column.  A `pf-adversary` pass installed a plug that also
wrote `speed_walk` and watched it pass this door untouched, because the door
selected only the three columns it was looking for.  It selects the rest now
(`_other_typed_columns_seeded`), which is the difference between a check and
a sentence about a check.

THE SECOND THING THE PLUG BREAKS is not a pin at all.  Two of the 33 do not
fail an assertion, they CRASH: `sqlite3.OperationalError: table characters has
no column named level`.  They build a database at schema 005 -- before
`migrations/006` adds the typed columns -- and then create a character in it,
which is how this lane proves 006 destroys nothing.  With the plug in place
`create_character` cannot run against any database older than 006 at all.
That is a fact about the plug, not about the tests, and it is reported to COO
and chief rather than papered over; `create_character_at_this_schema` below
uses the real door whenever the real door works and writes the row by hand
only when the schema genuinely predates 006, saying so in its return value.
"""
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_vitals as _vitals  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

#: The three columns a birth is allowed to seed, in the order
#: `persistence_vitals` names them.  Not read from `TYPED_COLUMNS`: this tuple
#: is the CLAIM that a birth touches these and nothing else, so it has to be
#: able to disagree with a wider table.
BIRTH_COLUMNS = ("level", "hp_current", "hp_max")


class BirthStateError(AssertionError):
    """A newly created character is in a state no test in this lane accepts.

    Deliberately an `AssertionError`: it is a failed measurement of the
    repository, and it should read like one in a pytest report rather than
    like a broken fixture.
    """


def character_columns(path):
    """The column names of `characters` in the database at `path`.

    An ABSENT table raises rather than answering "no columns".  The two are
    indistinguishable to `PRAGMA table_info`, and the difference is the whole
    safety of this module: "the schema predates 006" is a state it handles,
    while "you handed me a database with no characters table" -- a mistyped
    path, which `sqlite3.connect` happily CREATES, or `:memory:`, which opens
    a fresh empty one every time -- is a caller error that would otherwise
    come back as a green fixture that measured nothing.
    """
    db = sqlite3.connect(str(path))
    try:
        columns = {
            str(row[1]) for row in db.execute("PRAGMA table_info(characters)")
        }
    finally:
        db.close()
    if not columns:
        raise BirthStateError(
            "no `characters` table in %r -- this module was handed a database "
            "it cannot be measuring (a mistyped path, or ':memory:', both of "
            "which produce an empty database rather than an error)" % (str(path),)
        )
    return columns


def _row_vitals(path, character_id):
    """The three birth columns of one row, by RAW SQL, absent when NULL.

    Raw SQL rather than `SQLiteStore.read_typed_attributes`, on purpose: this
    function is what decides whether the store's own reader is telling the
    truth, so it must not be the store's own reader.  (Same lesson as defect
    D13 of round `cby3pd`: a census that grades the database against itself
    measures nothing.)
    """
    present = character_columns(path)
    missing = [c for c in BIRTH_COLUMNS if c not in present]
    if missing:
        return {}, tuple(missing)
    db = sqlite3.connect(str(path))
    try:
        db.row_factory = sqlite3.Row
        row = db.execute(
            "SELECT %s FROM characters WHERE id=?" % ",".join(BIRTH_COLUMNS),
            (character_id,),
        ).fetchone()
    finally:
        db.close()
    if row is None:
        raise BirthStateError("no character row with id %r" % (character_id,))
    return {c: row[c] for c in BIRTH_COLUMNS if row[c] is not None}, ()


def _other_typed_columns_seeded(path, character_id):
    """Any typed column OUTSIDE `BIRTH_COLUMNS` that already holds a value.

    The module's whole claim is that a birth touches three columns and no
    fourth one.  A `pf-adversary` pass measured that the first version of this
    file did not actually look: it selected only the three, so a birth that
    also seeded `speed_walk` -- the number `COO-DECISION 20260901_1447` point
    2 spent a day refusing to let anyone choose -- went straight through the
    door and surfaced eighteen files later as an ordinary assertion failure.
    """
    from pirateforce_foundation import persistence_typed_attrs as _typed

    present = character_columns(path)
    others = [c for c in _typed.TYPED_COLUMNS
              if c not in BIRTH_COLUMNS and c in present]
    if not others:
        return {}
    db = sqlite3.connect(str(path))
    try:
        db.row_factory = sqlite3.Row
        row = db.execute(
            "SELECT %s FROM characters WHERE id=?" % ",".join(others),
            (character_id,),
        ).fetchone()
    finally:
        db.close()
    if row is None:
        return {}
    return {c: row[c] for c in others if row[c] is not None}


def observed_birth_vitals(store, character_id):
    """What the row holds now, refusing every world but the two allowed ones.

    Returns `{}` when the plug of `COO-DECISION 20260902_0444` has not landed
    (or the schema predates 006 and the columns do not exist), and a dict
    equal to `new_character_vitals()` once it has.  Anything else raises.
    """
    held, missing = _row_vitals(store.path, character_id)
    extra = _other_typed_columns_seeded(store.path, character_id)
    if extra:
        raise BirthStateError(
            "a newly created character also holds %r.  A birth may seed the "
            "three vital columns and NOTHING else: `COO-DECISION 20260902_"
            "0443` answered the birth question for those three only, and "
            "every other typed column is a value nobody has adjudicated for "
            "a newborn." % (extra,)
        )
    if missing:
        return {}
    if not held:
        return {}
    expected = _vitals.new_character_vitals()
    if held != expected:
        raise BirthStateError(
            "a newly created character holds %r; this lane accepts only an "
            "unseeded row ({}) or exactly persistence_vitals."
            "new_character_vitals() == %r.  A birth that writes anything "
            "else is the failure these tests exist to catch -- do not widen "
            "this check, fix the birth." % (held, expected)
        )
    return dict(held)


def clear_birth_vitals(store, character_id):
    """Check the birth state, then return THIS ONE ROW to the unseeded state.

    Returns what was cleared, so a caller that cares which world it is in can
    ask, rather than guessing.  Writes by raw SQL and not through
    `write_typed_attributes`, because that API refuses `None` by design -- and
    the point here is to reach the state a pre-plug database is really in, not
    a state the write API can express.
    """
    held = observed_birth_vitals(store, character_id)
    if not held:
        return {}
    db = sqlite3.connect(str(store.path))
    try:
        db.execute(
            "UPDATE characters SET %s WHERE id=?"
            % ",".join("%s=NULL" % c for c in BIRTH_COLUMNS),
            (character_id,),
        )
        db.commit()
    finally:
        db.close()
    left, _ = _row_vitals(store.path, character_id)
    if left:
        raise BirthStateError(
            "clearing the birth vitals of character %r left %r behind"
            % (character_id, left)
        )
    return held


def create_character_at_this_schema(store, account_id, name, name_key,
                                    fingerprint, build_wire, position):
    """`store.create_character`, and a hand-written row when it cannot run.

    Returns `(character_id, used_the_real_door)`.  The real door is tried
    FIRST and always: the fallback is reachable only when the attempt died on
    a birth column the schema does not have, which is checked against
    `PRAGMA table_info` afterwards rather than believed from the message.  A
    database that has the columns therefore cannot take the fallback, whatever
    the store raises.
    """
    try:
        character = store.create_character(
            account_id, name, name_key, fingerprint, build_wire, position
        )
    except sqlite3.OperationalError as error:
        present = character_columns(store.path)
        absent = [c for c in BIRTH_COLUMNS if c not in present]
        # Matched on a WORD, not a substring: `no such column: skill_level`
        # contains "level" and has nothing to do with a birth column, and a
        # fallback taken for an unrelated failure would hide that failure
        # behind a hand-written row that looks fine.
        named = any(
            re.search(r"\b%s\b" % re.escape(column), str(error))
            for column in absent
        )
        if not absent or not named:
            raise
        return _insert_pre_006_character(
            store, account_id, name, name_key, fingerprint, build_wire, position
        ), False
    return character.id, True


def _insert_pre_006_character(store, account_id, name, name_key, fingerprint,
                              build_wire, position):
    """The row `create_character` would have written before the birth plug.

    Only the columns that exist at schema 005 are named, and the position and
    backpack children are written through the store's own helper, so what a
    pre-006 test compares afterwards is the same shape the real door leaves.
    """
    from pirateforce_foundation.store import _now

    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        # The retry branch, in the same place and shape the real door has it.
        # Without it this function is not "what create_character would have
        # written" but something subtly wilder: a second create with the same
        # fingerprint inserts a DUPLICATE and dies on migration 004's partial
        # unique index -- and it dies HERE, in this lane's helper, so a caller
        # meets `IntegrityError` from a test file instead of the store's own
        # idempotent answer.  A `pf-adversary` pass measured exactly that.
        retry = db.execute(
            "SELECT id FROM characters WHERE account_id=? AND "
            "create_fingerprint=? AND deleted_at IS NULL",
            (account_id, fingerprint),
        ).fetchone()
        if retry is not None:
            return int(retry[0])
        used = {
            int(r[0]) for r in db.execute(
                "SELECT selector FROM characters WHERE account_id=? AND "
                "deleted_at IS NULL", (account_id,),
            )
        }
        selector = next((n for n in range(256) if n not in used), None)
        if selector is None:
            # The real door's error, not `StopIteration`: a caller that
            # handles one and not the other is a caller this helper lied to.
            raise ValueError("no selector available")
        wire, avatar_wire, lo, hi = build_wire(selector)
        now = _now()
        cur = db.execute(
            "INSERT INTO characters(account_id,selector,name,name_key,"
            "create_fingerprint,actor_wire,avatar_wire,avatar_typed_json,"
            "identity_lo,identity_hi,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (account_id, selector, name, name_key, fingerprint, wire,
             avatar_wire, None, lo, hi, now, now),
        )
        cid = int(cur.lastrowid)
        db.execute(
            "INSERT INTO character_positions(character_id,scene_id,scene_seq,"
            "x,y,z,updated_at,heading) VALUES (?,?,?,?,?,?,?,?)",
            (cid, position.scene_id, position.scene_seq, position.x,
             position.y, position.z, _now(), position.heading),
        )
        SQLiteStore._insert_initial_backpack(db, cid, now)
    return cid
