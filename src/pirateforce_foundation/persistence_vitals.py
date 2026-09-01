"""LANE-DB / M4: the three columns a character has to REMEMBER to be hit and
to die -- ``level``, ``hp_current``, ``hp_max`` -- and the only arithmetic
allowed to move them.

WHY THIS FILE EXISTS.  ``COO-DECISION 20260901_1100`` set this lane's queue
after ``/speed`` as "HP/เลเวล" and named what it unlocks in the same
sentence: *M4 (ตีได้ตายได้) -- ตอนนี้ schema ไม่มีที่เก็บ HP แม้แต่คอลัมน์เดียว*.
``migrations/006_character_typed_attribute_columns.sql`` built the columns;
``COO-DECISION 20260901_1447`` point 1 acknowledged that and said to walk the
HP/level queue next.  This module is the next step of that queue: the DECISION
layer over those three columns: the one place that says what a stored HP
value means and what a hit does to it.

[PROPOSED - LANE-DB] "one answer instead of one per call site" is the
DESTINATION, not what this round achieves, and a ``pf-adversary`` pass was
right to make the difference explicit.  This round adds an answer that
nothing calls yet and removes none of the existing ones: today
``docs/FUNCTIONAL_COVERAGE.json:551`` still grades ``hp_death_and_respawn``
``runtime_pass`` on other code, and ``hostile_hp_link_hypothesis.py:1960``
still contains a literal ``rows[-1].get("hp_current", 0)`` -- a guessed zero
on this very field, in shipped code, that this module does not touch and has
no authority over.

## WHAT IT REFUSES, AND WHY EACH REFUSAL IS THE OWNER'S RULE

The owner's standing rule, relayed verbatim in ``COO-DECISION 20260901_1059``:
a block in which an unknown field is GUESSED TO BE ZERO must never be sent.
An HP field is where that rule bites hardest, because on this wire zero is not
a missing value -- it is DEAD.  A character whose ``hp_current`` column has
never been written is not a corpse; it is a character this server does not yet
know the HP of.  So:

* an absent column is a NAMED GAP here, never a zero.  ``resolve()`` reports
  it, ``VitalsResolution.require()`` raises with the column named, and
  ``SQLiteStore.apply_hp_damage`` refuses to run at all.  There is no
  ``.get(column, 0)`` in this file and a test parses the source to prove it,
  the same way ``persistence_typed_attrs`` is proved.
* ``hp_max = 0`` is refused as a stored state.  The column's own SQL CHECK
  allows it (the CHECK carries the wire kind's range, ``u32``, and 0 is in
  it), but a character whose maximum is zero can never be alive and cannot be
  revived by any arithmetic this server can do.  It is also EXACTLY the shape
  a guessed-zero seed would leave behind, which is the second and larger
  reason to refuse it: the refusal is a net under a seeding mistake that no
  per-column CHECK can catch.  [สมมติของสาย DB] this rule is about PLAYER
  characters, which are the only rows in ``characters``; nothing here claims a
  mob or an NPC may not have a zero maximum somewhere else in this repository.
* ``hp_current > hp_max`` is refused.  Two per-column CHECKs cannot express a
  relation between two columns, so SQLite cannot catch this and something has
  to.
* a half-written pair (``hp_current`` set, ``hp_max`` not, or the reverse) is
  refused as INCOMPLETE rather than half-used, because every use of one needs
  the other: a bar needs both ends and damage needs a floor and a ceiling.

## WHAT IT DOES NOT DO

* **It does not seed.**  Nothing in this file writes a value into a column
  that had none.  Whether anything ELSE has seeded them is not asserted here
  and is not knowable from this file: it is a question about a database, and
  ``census_sql`` / ``SQLiteStore.vitals_seeding_census`` ask it there.
  Seeding is a write on live rows and therefore a migration, and what the
  migration is waiting for is a VALUE that this lane may not pick on its own:
  ``COO-DECISION 20260901_1447`` point 2 is the standing shape of that rule
  for ``speed_walk``, and the same question for ``level``/``hp`` is put to COO
  in the OTHER repository -- ``pf_bridge/notes_to_chief/20260901_2322_LANE-DB-
  ASK-COO-hp-level-seed-value-adjudication.md``.  Named with its repository
  because a reviewer of THIS repository cannot open it: a ``pf-adversary``
  pass searched for it here, found nothing, and was right to call the citation
  unopenable.  Nothing in this module depends on that letter's contents; it is
  where the question went, not evidence for anything here.
  What is measured and is in that letter: the shipped login frame already
  sends level ``1`` and hp ``100/100`` for every character
  (``src/pirateforce_foundation/player_wire.py:203-205``, with
  ``PLAYER_LOGIN_LEVEL = 1`` at ``:22`` and the two ``100``\\ s written inline),
  so seeding those three numbers would be a TRANSCRIPTION of what this server
  already puts on the wire rather than a new number -- but "one number instead
  of two candidates" is a better position to ask from, not a licence to
  answer, so this module ships unseeded and fail-closed.
* **It sends nothing and is wired to nothing.**  No frame, no encoder, no
  socket, no call site.  Composing an attribute block from these values is
  still ``persistence_attr_compose``'s decision and still refuses today.
* **It does not decide combat.**  ``apply_damage`` is arithmetic over two
  numbers: what a hit is worth, whether a hit lands, what happens when a
  character reaches zero, and whether a corpse may be hit again are LANE-B's
  and the owner's to rule.  This module reports ``was_already_zero`` and
  ``died`` and refuses nothing on that basis, so that a caller cannot mistake
  this file's silence for a rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .gm.attr_wire import BY_X
from . import persistence_typed_attrs as typed_attrs

#: The wire fields these three columns serve, in mask-bit order.  Named by ``x``
#: rather than by column name so that a rename in ``persistence_attr_compose``
#: cannot silently point this module at a different field: ``_verify_binding``
#: below re-derives the column name from ``x`` at import time.
#:
#: All three are ``known=True`` in ``gm/attr_wire.FIELDS`` -- x=2 ``level``
#: (BasicAttr+0x5E, "GetLv"), x=3 ``hp_current`` (+0x044, "HP bar"), x=4
#: ``hp_max`` (+0x048).  That is a different evidential position from x=7
#: (``basic_f32_54``, ``known=False``), and it is why this module does not
#: carry x=7's [สมมติของสาย DB - รอ RE] caveat: these three names are the
#: repository's own proven ones, not this lane's proposal.
LEVEL_X = 2
HP_CURRENT_X = 3
HP_MAX_X = 4
VITAL_X: tuple[int, ...] = (LEVEL_X, HP_CURRENT_X, HP_MAX_X)


class VitalsError(ValueError):
    """A vitals state, or a change to one, that this server may not hold."""


def _column(x: int) -> str:
    return typed_attrs.column_for(x)


LEVEL_COLUMN = _column(LEVEL_X)
HP_CURRENT_COLUMN = _column(HP_CURRENT_X)
HP_MAX_COLUMN = _column(HP_MAX_X)

#: The three column names, in the same order as ``VITAL_X``.
VITAL_COLUMNS: tuple[str, ...] = (
    LEVEL_COLUMN, HP_CURRENT_COLUMN, HP_MAX_COLUMN,
)

#: Reason codes.  Strings rather than an enum to match the reason codes
#: ``persistence_attr_compose`` already reports, so a caller that logs both
#: does not have to special-case one of them.
REASON_NOT_SEEDED = "vital_column_not_seeded"
REASON_HP_PAIR_INCOMPLETE = "hp_pair_incomplete"
REASON_HP_ABOVE_MAX = "hp_current_above_hp_max"
REASON_HP_MAX_ZERO = "hp_max_zero_is_never_alive"


def _verify_binding() -> None:
    """Fail at import if these three columns are not the fields named here.

    WHAT IT CATCHES: drift in this repository's PYTHON tables -- a rename or a
    kind change in ``gm/attr_wire.FIELDS``, or a field that stops being a
    proven name (``known=False``).

    WHAT IT DOES NOT CATCH, said plainly because the first draft of this
    docstring claimed the opposite: a rename that happens only in SQL.  A
    ``pf-adversary`` pass ran ``ALTER TABLE characters RENAME COLUMN
    hp_current TO hp_cur`` against a real migrated database; this function
    passed without complaint and the failure arrived as a raw
    ``sqlite3.OperationalError`` at the first SELECT -- exactly the place the
    old wording promised it would not.  Nothing here reads a database, and
    nothing here can: this function runs at import, before any store exists.
    ``verify_schema`` below is the half that needs a connection, and the store
    methods call it so that the drift arrives NAMED rather than raw.
    """
    expected = {
        LEVEL_X: ("level", "u16"),
        HP_CURRENT_X: ("hp_current", "u32"),
        HP_MAX_X: ("hp_max", "u32"),
    }
    for x, (wire_name, wire_kind) in expected.items():
        row = BY_X[x]
        if row[6] != wire_name or row[5] != wire_kind:
            raise VitalsError(
                f"x={x} is {row[6]!r}/{row[5]} in gm/attr_wire.FIELDS, not "
                f"{wire_name!r}/{wire_kind}: this module's binding is stale"
            )
        if not row[7]:
            raise VitalsError(
                f"x={x} ({wire_name}) is marked known=False in "
                "gm/attr_wire.FIELDS; this module claims all three of its "
                "fields are proven names and that claim is now false"
            )
        typed_attrs.TYPED_COLUMNS[_column(x)]


_verify_binding()


class SchemaDriftError(VitalsError):
    """This database cannot serve the reads these store methods make."""


def required_columns() -> tuple[str, ...]:
    """Every ``characters`` column the vitals store methods actually name.

    DERIVED, not listed.  The first version of ``verify_schema`` checked the
    three vital columns and nothing else, and a ``pf-adversary`` pass showed
    what that misses: the two store methods ``SELECT`` ALL of
    ``typed_attrs.TYPED_COLUMNS`` and also touch ``id``, ``deleted_at`` and
    ``updated_at``.  Renaming ``speed_walk`` -- the ONE rename
    ``migrations/006...sql`` explicitly pre-announces, because that column's
    name still encodes an unproven identification -- left the guard green and
    produced a raw ``sqlite3.OperationalError`` out of both methods.  Renaming
    ``updated_at`` was worse: every gate passed and the error arrived from the
    ``UPDATE``, inside the open transaction.

    So the guard now asks the question the CALLER asks, built from the same
    list the SELECT is built from.  A column added to ``TYPED_COLUMNS`` by a
    later migration joins this set automatically.
    """
    return tuple(typed_attrs.TYPED_COLUMNS) + ("id", "deleted_at", "updated_at")


def verify_schema(db) -> None:
    """Raise ``SchemaDriftError`` unless ``characters`` can serve these reads.

    ``_verify_binding`` above checks this repository's python tables against
    each other and cannot see the database at all.  This is the other half,
    and it needs a connection.  Two questions, because a ``pf-adversary`` pass
    got a raw ``sqlite3.OperationalError`` past a version that asked only the
    second:

    1. is ``characters`` a TABLE?  ``PRAGMA table_info`` answers identically
       for a view, and the adversary renamed the table away and left a view of
       the same name behind: the guard passed, the read returned three
       plausible numbers, and the write raised
       ``cannot modify characters because it is a view``.
    2. does it carry every column ``required_columns()`` names?

    Without this the first symptom is ``sqlite3.OperationalError: no such
    column: ...`` raised out of a store method whose documented exceptions are
    ``KeyError`` and ``VitalsError`` -- which a caller following that contract
    does not catch.
    """
    kind = db.execute(
        "SELECT type FROM sqlite_master WHERE name='characters'"
    ).fetchone()
    if kind is None:
        raise SchemaDriftError(
            "this database has no `characters` object at all: it is not a "
            "Pirate Force database, and no vitals can be read from it"
        )
    if kind[0] != "table":
        raise SchemaDriftError(
            "`characters` is a %s in this database, not a table: a read may "
            "succeed and the write cannot" % (kind[0],)
        )
    have = {row[1] for row in db.execute("PRAGMA table_info(characters)")}
    missing = [column for column in required_columns() if column not in have]
    if missing:
        raise SchemaDriftError(
            "characters is missing %s: this database's schema and "
            "persistence_vitals disagree, and no vitals can be read from it"
            % (", ".join(missing),)
        )


@dataclass(frozen=True)
class VitalGap:
    """One named reason the vitals of a character cannot be used as they are.

    ``column`` is the column the reason is about; ``detail`` says it in words
    for a log line.  A gap is never a value and carries no substitute.
    """

    column: str
    reason: str
    detail: str


@dataclass(frozen=True)
class Vitals:
    """A COMPLETE, consistent vitals state.  Only ``VitalsResolution.require``
    builds one, so holding an instance of this is itself the proof that every
    column was present and every cross-column rule passed."""

    level: int
    hp_current: int
    hp_max: int

    @property
    def alive(self) -> bool:
        """``hp_current > 0``.  Named so that a caller does not write the
        comparison itself and get the ``>= 0`` version of it."""
        return self.hp_current > 0


@dataclass(frozen=True)
class VitalsResolution:
    """What the database knows about one character's vitals, and what it does
    not.  ``present`` holds only columns that really have a value; ``gaps``
    names every reason the state is unusable."""

    present: Mapping[str, int]
    gaps: tuple[VitalGap, ...]

    @property
    def complete(self) -> bool:
        return not self.gaps

    def require(self) -> Vitals:
        """The ``Vitals``, or ``VitalsError`` naming every gap.

        This is the fail-closed door: a caller that wants numbers has to come
        through here, and there is no path through it that invents one.
        """
        if self.gaps:
            raise VitalsError(
                "character vitals are not usable: "
                + "; ".join(
                    f"{gap.column} [{gap.reason}] {gap.detail}"
                    for gap in self.gaps
                )
            )
        # This dataclass is public and can be built by hand with an empty
        # `present` and no gaps at all.  A `pf-adversary` pass did exactly
        # that and got `KeyError('level')` out of a contract written entirely
        # in `VitalsError` -- and a KeyError from a store-level caller reads
        # as "no such character", which is a different and much worse lie
        # than "these numbers are missing".
        missing = [c for c in VITAL_COLUMNS if c not in self.present]
        if missing:
            raise VitalsError(
                "this resolution has no gaps but is missing %s; it was not "
                "built by resolve()" % (", ".join(missing),)
            )
        return Vitals(
            level=int(self.present[LEVEL_COLUMN]),
            hp_current=int(self.present[HP_CURRENT_COLUMN]),
            hp_max=int(self.present[HP_MAX_COLUMN]),
        )


def _as_stored_int(column: str, value: object) -> int:
    """``value`` re-validated against the column it claims to come from.

    A ``SELECT`` on a database another writer reached with raw SQL can hand
    back anything the CHECK allowed -- and for a column added by ``006`` the
    CHECK is per column, so a relation this module depends on was never
    checked at all.  Re-validating here means every number below has passed
    ``persistence_typed_attrs.validate`` at least once inside this process.

    ``TypedAttrError`` is re-raised as ``VitalsError`` on the way out.  Both
    are ``ValueError`` subclasses, so a caller catching the wrong one still
    catches it -- but this module's whole contract is written in terms of
    ``VitalsError``, and a caller that follows that contract exactly would
    otherwise miss a refusal that came from one layer down.
    """
    try:
        checked = typed_attrs.validate(column, value)
    except typed_attrs.TypedAttrError as error:
        raise VitalsError(str(error)) from error
    if not isinstance(checked, int):
        raise VitalsError(
            f"{column}: {value!r} is not an integer vital"
        )
    return checked


def _consistency_gaps(present: Mapping[str, int]) -> tuple[VitalGap, ...]:
    """Every cross-column rule broken by ``present``, in a fixed order.

    Only rules that a per-column SQL CHECK cannot express live here.  The
    per-column ranges are already enforced twice (``validate`` and the CHECK
    written by ``006``) and are not repeated.

    PRIVATE ON PURPOSE.  It was public in the first draft and a
    ``pf-adversary`` pass showed why that is a trap: it answers ``()`` for an
    EMPTY mapping and for ``{"level": 1}``, because the pair rules can only
    fire when at least one of the pair is present.  A caller who wrote
    ``if not consistency_gaps(store.read_typed_attributes(cid)): proceed``
    would get a green light on a completely unseeded character -- a gate that
    passes on emptiness, which is the exact shape of the failure this module
    exists to prevent.  ``resolve()`` is the only entry point, and it adds the
    not-seeded gaps before these run.
    """
    gaps: list[VitalGap] = []
    hp_current = present.get(HP_CURRENT_COLUMN)
    hp_max = present.get(HP_MAX_COLUMN)
    if (hp_current is None) != (hp_max is None):
        missing = HP_MAX_COLUMN if hp_max is None else HP_CURRENT_COLUMN
        gaps.append(VitalGap(
            missing, REASON_HP_PAIR_INCOMPLETE,
            f"{HP_CURRENT_COLUMN} and {HP_MAX_COLUMN} are only usable as a "
            f"pair; {missing} has no value",
        ))
        return tuple(gaps)
    if hp_max is not None and hp_max == 0:
        gaps.append(VitalGap(
            HP_MAX_COLUMN, REASON_HP_MAX_ZERO,
            "a character whose maximum HP is 0 is never alive and cannot be "
            "revived; a zero here is what a guessed seed leaves behind",
        ))
    if hp_current is not None and hp_max is not None and hp_current > hp_max:
        gaps.append(VitalGap(
            HP_CURRENT_COLUMN, REASON_HP_ABOVE_MAX,
            f"{hp_current} is above the maximum {hp_max}",
        ))
    return tuple(gaps)


def resolve(stored: Mapping[str, object]) -> VitalsResolution:
    """Read one character's vitals out of a typed-attribute read.

    ``stored`` is what ``SQLiteStore.read_typed_attributes`` returns: only
    columns that HAVE a value, NULLs already dropped.  A column that is not in
    it is reported as ``REASON_NOT_SEEDED`` and never as a zero.  Columns
    outside these three are ignored rather than refused -- a character's
    ``cash`` is not this module's business, and refusing the whole read
    because of it would make this function unusable on a fully seeded row.
    """
    present: dict[str, int] = {}
    gaps: list[VitalGap] = []
    for column in VITAL_COLUMNS:
        if column not in stored:
            gaps.append(VitalGap(
                column, REASON_NOT_SEEDED,
                "no value in this server's database; absence is not zero "
                "(COO-DECISION 20260901_1059)",
            ))
            continue
        present[column] = _as_stored_int(column, stored[column])
    gaps.extend(_consistency_gaps(present))
    return VitalsResolution(present=dict(present), gaps=tuple(gaps))


@dataclass(frozen=True)
class DamageOutcome:
    """What one application of damage did to a character's HP.

    ``requested`` is what the caller asked for and ``applied`` is what the HP
    bar could actually absorb; they differ on an overkill.  Both are reported
    because throwing the difference away is how an overkill silently becomes a
    normal hit in a log.
    """

    hp_before: int
    hp_after: int
    hp_max: int
    requested: int
    applied: int
    died: bool
    was_already_zero: bool


def apply_damage(hp_current: int, hp_max: int, amount: int) -> DamageOutcome:
    """Subtract ``amount`` from ``hp_current``, with a floor of zero.

    Pure arithmetic over three validated integers -- no database, no clock, no
    randomness -- so it can be tested exhaustively at the edges and reused by
    whatever call site eventually lands.

    Refused, each because the alternative is a silent wrong number:

    * a ``bool`` amount (``True`` is ``1`` in python and would land as a hit
      for one point with no complaint);
    * a negative amount, which would be a HEAL wearing damage's name and could
      push ``hp_current`` above ``hp_max`` where nothing checks it again;
    * an inconsistent input pair (``hp_current`` above ``hp_max``, or a zero
      maximum) -- ``consistency_gaps`` is applied to the INPUT, not just to
      what is read from the database, so this function cannot be used to
      launder a state the read path would have refused.

    ``amount = 0`` is allowed: a blocked or fully mitigated hit is a real
    event, and it produces an outcome with ``applied = 0`` rather than an
    error.  Hitting a character who is already at zero is likewise allowed and
    reported (``was_already_zero``) rather than refused -- whether a corpse may
    be hit is LANE-B's rule, not this file's.
    """
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise VitalsError(
            f"damage amount must be an int, got {type(amount).__name__}"
        )
    if amount < 0:
        raise VitalsError(
            f"damage amount {amount} is negative; healing is not damage with "
            "a minus sign and does not go through this function"
        )
    if amount > typed_attrs.KIND_STORAGE["u32"][2]:
        # `applied` is clamped, so nothing wrong could ever be STORED -- but
        # `requested` is handed back to a caller as a damage figure, and a
        # number wider than the HP field itself is not a damage figure.  A
        # `pf-adversary` pass got `requested == 2**70` out of this function.
        raise VitalsError(
            f"damage amount {amount} is wider than the u32 the HP columns "
            "hold; it is not a quantity of damage this wire can describe"
        )
    before = _as_stored_int(HP_CURRENT_COLUMN, hp_current)
    maximum = _as_stored_int(HP_MAX_COLUMN, hp_max)
    gaps = _consistency_gaps({
        HP_CURRENT_COLUMN: before, HP_MAX_COLUMN: maximum,
    })
    if gaps:
        raise VitalsError(
            "cannot apply damage to an inconsistent state: "
            + "; ".join(f"{g.column} [{g.reason}] {g.detail}" for g in gaps)
        )
    applied = min(amount, before)
    after = before - applied
    return DamageOutcome(
        hp_before=before,
        hp_after=after,
        hp_max=maximum,
        requested=amount,
        applied=applied,
        died=after == 0 and before > 0,
        was_already_zero=before == 0,
    )


def census_sql() -> str:
    """The one query that answers "is anything seeded", against the DATABASE.

    THIS REPLACES A TEXT PARSER, and the replacement is the point.  The first
    draft of this module answered the same question by parsing
    ``migrations/*.sql`` for ``UPDATE``/``INSERT`` statements naming these
    columns.  A ``pf-adversary`` pass took it apart with seven seeding shapes
    that parser reported as "nothing seeds" -- ``ADD COLUMN ... DEFAULT 100``
    (the shape ``006``'s own header invites, since it says a later rename is
    cheap), a UTF-8 BOM before the statement, a CTE, ``REPLACE INTO``, a
    ``CREATE TRIGGER`` whose body updates, ``INSERT INTO ... SELECT``, and a
    ``/* */`` comment -- and then built a real migrated database on which
    every row held ``hp_current = 100`` while the report still said
    ``seeded_by_any_migration: False``.  It also returned "nothing seeds" for
    a directory that did not exist, and read the REPOSITORY's migrations
    directory rather than the one the live ``SQLiteStore`` was built with.

    EVERY ROW IS COUNTED, INCLUDING SOFT-DELETED ONES, and that is the second
    correction rather than a detail.  The first version of this query carried
    ``WHERE deleted_at IS NULL``, matching every other read in this lane, and
    a second ``pf-adversary`` pass showed what that costs a REPORT (as opposed
    to a read): seed a character, soft-delete it, add a fresh one, and the
    census said ``characters: 1`` with every ``*_seeded`` at ``0`` over a
    database holding ``level=9, hp_current=50`` on disk.  ``004_character_
    soft_delete_reuse.sql`` keeps those rows forever, so that was a permanent
    wrong answer in the reassuring direction -- the same direction, and the
    same lie, as the text parser it replaced.  A read must ignore deleted
    rows; a report that exists to say "nothing has been seeded" must not.

    So both are reported side by side: ``*_seeded_live`` for the rows a read
    would see, ``*_seeded_any`` for every row on disk.  They differ exactly
    when a seeded character has been deleted, and a reader who quotes only
    one of them can at least see the other next to it.
    """
    parts = ["COUNT(*) AS characters_any",
             "SUM(deleted_at IS NULL) AS characters_live"]
    for column in VITAL_COLUMNS:
        parts.append(f"SUM({column} IS NOT NULL) AS {column}_seeded_any")
        parts.append(
            f"SUM({column} IS NOT NULL AND deleted_at IS NULL) "
            f"AS {column}_seeded_live"
        )
    return "SELECT " + ",".join(parts) + " FROM characters"
