"""LANE-DB: the typed attribute columns, and the only validated way in and out.

WHAT THIS IS.  ``migrations/006_character_typed_attribute_columns.sql`` adds
twenty-one nullable columns to ``characters`` -- level, hp, mp, walk speed,
class, points, the five stats, the five bonuses, experience and cash.  This
module is the single description of that column set in python: which wire
field each column serves, what values it may hold, and what a value that
cannot survive the encoder looks like.  ``SQLiteStore.read_typed_attributes``
and ``SQLiteStore.write_typed_attributes`` are the two store methods built on
it; nothing else in this repository should build a column name for these
fields by hand.

THE ONE PROPERTY IT DEFENDS.  A column with no value stays NULL and is
*omitted* from what a read returns -- it is never rendered as ``0``.  That is
the schema half of the owner's rule (relayed verbatim in
``COO-DECISION 20260901_1059``): a block whose unknown field was guessed to be
zero must never be sent.  ``persistence_attr_compose`` refuses to compose a
block for a field it was handed no value for, so a NULL column arrives there
as ABSENT and the refusal happens by itself.  If a read had defaulted NULL to
zero, that refusal would have been silently defeated one layer earlier -- so
there is no ``dict.get(column, 0)`` here either, and a test parses this file
to prove it.

WHAT IT DOES NOT DO.

* It does not seed.  No value is written into any of these columns by this
  module, at creation or at migration time; a caller supplies every value.
  Seeding walk speed from the client's proven construction default (400.0,
  written at ``0x00464AF2``, see ``persistence_attr_compose.
  CLIENT_CONSTRUCTION_DEFAULTS``) is a real and wanted step, and it is a data
  write on live rows.  The snapshot that a live write needs now exists on the
  boot path (``app.py:784``/``:787`` call ``SQLiteStore.migrate_with_backup``;
  ``CORE-REQUEST-DB-001`` answered on main by LANE-E round liq4ri), so what
  seeding waits on is no longer a mechanism but a NUMBER: ``COO-DECISION
  20260901_1447`` point 2 forbids seeding ``speed_walk`` with either candidate
  until an RE says which one a player object uses.
* It does not know whether ``speed_walk`` really is the PLAYER's walk speed.
  The column serves BasicAttr+0x54 (x=7).  ``gm/attr_wire.py:173`` calls it
  ``basic_f32_54``, ``known=False``, and the Codex corpus scopes its row to
  ``CNetNPC`` -- but ``docs/FUNCTIONAL_COVERAGE.json`` grades
  ``npc_locomotion_presentation`` ``runtime_pass`` on the same bit (0x0040)
  and ``tests/test_npc_gait_wire.py:59`` pins ``PROVEN_WALK_SPEED = 150.0``
  there.  Identified for NPCs at the wire+visual layer, untested for a player,
  and carrying two different numbers between layers (150.0 proven on the wire,
  400.0 as the client's construction default).  [สมมติของสาย DB - รอ RE]
* It sends nothing.  No frame, no encoder, no socket.
"""
from __future__ import annotations

import math
import re
import struct
from dataclasses import dataclass
from typing import Mapping

from .gm.attr_wire import BY_X
from .persistence_attr_compose import SERVER_OWNED_FIELDS

#: The migration that builds every column named here.  Pinned so a test can
#: parse that file and prove the two agree, rather than trusting this list.
MIGRATION_FILE = "006_character_typed_attribute_columns.sql"

#: Largest finite float32, as a double.  The wire kind for x=7 is ``f32``; the
#: column is an 8-byte REAL, so this is the real bound, checked here and again
#: by the column's own SQL CHECK.
F32_MAX = 3.4028234663852886e38


def as_f32(value: float) -> float:
    """``value`` after the round trip through the wire's own float32.

    ``gm/attr_wire.py`` emits an ``f32`` field as ``struct.pack("<f", value)``.
    A REAL column is eight bytes, so without this the database could hold a
    number the client can never be sent -- ``400.1`` is stored, the client
    receives ``400.1000061035156``, and the two disagree forever with nothing
    watching.  Storing the rounded value instead makes "what the database
    says" and "what the wire carries" the same number by construction.
    """
    return struct.unpack("<f", struct.pack("<f", value))[0]


class TypedAttrError(ValueError):
    """A value or a column name that these typed columns may not hold."""


@dataclass(frozen=True)
class TypedColumn:
    """One column, bound to the wire field it exists to serve."""

    x: int
    column: str
    kind: str
    sql_type: str
    minimum: int | float
    maximum: int | float


# wire kind -> (SQL type, minimum, maximum).  u64 is capped at 2**63-1 rather
# than 2**64-1 because SQLite's INTEGER is signed 64-bit and simply has no
# room for the top half; the migration's comment says the same thing where the
# CHECK is written.  This narrowing is a property of the storage engine, not a
# decision, and it is asserted in the tests so it cannot drift into a silent
# truncation later.
KIND_STORAGE: dict[str, tuple[str, int | float, int | float]] = {
    "u16": ("INTEGER", 0, 65535),
    "u32": ("INTEGER", 0, 4294967295),
    "u64": ("INTEGER", 0, 2**63 - 1),
    "f32": ("REAL", -F32_MAX, F32_MAX),
}

# x=1 (`characters.name`) is server-owned too, and it is deliberately NOT a
# typed attribute column here.  It is a `wstr`, it already exists since
# 001_initial.sql, and it is written by `create_character` together with
# `name_key` and the create fingerprint -- a rename is a whole operation with
# uniqueness rules, not a field poke.  Letting it through this API would give
# a caller a way to change a character's name without any of that.
NOT_A_TYPED_ATTRIBUTE_COLUMN: frozenset[int] = frozenset({1})

_COLUMN_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def _build() -> dict[str, TypedColumn]:
    built: dict[str, TypedColumn] = {}
    for x, owned in sorted(SERVER_OWNED_FIELDS.items()):
        if x in NOT_A_TYPED_ATTRIBUTE_COLUMN:
            continue
        kind = BY_X[x][5]
        if kind not in KIND_STORAGE:
            raise TypedAttrError(
                f"field x={x} ({owned.column}) has wire kind {kind!r}, which "
                "these typed columns have no storage rule for"
            )
        sql_type, minimum, maximum = KIND_STORAGE[kind]
        if not _COLUMN_NAME.match(owned.column):
            raise TypedAttrError(f"unsafe column name {owned.column!r}")
        if owned.column in built:
            raise TypedAttrError(f"duplicate column name {owned.column!r}")
        built[owned.column] = TypedColumn(
            x=x,
            column=owned.column,
            kind=kind,
            sql_type=sql_type,
            minimum=minimum,
            maximum=maximum,
        )
    return built


#: column name -> TypedColumn.  Ordered by ``x``, which is the order the
#: migration writes them in.
TYPED_COLUMNS: dict[str, TypedColumn] = _build()

#: x -> column name, for the compose gate's ``{x: value}`` shape.
COLUMN_FOR_X: dict[int, str] = {c.x: c.column for c in TYPED_COLUMNS.values()}


def column_for(x: int) -> str:
    """The typed column serving wire field ``x``, or ``TypedAttrError``."""
    if x not in COLUMN_FOR_X:
        raise TypedAttrError(
            f"wire field x={x!r} has no typed attribute column "
            f"(built: {sorted(COLUMN_FOR_X)})"
        )
    return COLUMN_FOR_X[x]


def validate(column: str, value: object) -> int | float:
    """The value as it will be stored, or ``TypedAttrError`` saying why not.

    Every refusal below is a value that would either be silently altered on
    the way into SQLite or be unencodable on the way out to the client:

    * an unknown column name -- nothing may be poked into ``characters`` by
      name through this API that is not one of these columns;
    * ``None`` -- clearing a typed column back to "no value" is not a field
      write and is not offered here (it would look exactly like a write in a
      caller's code, which is how a cleared column becomes a guessed zero one
      layer up);
    * ``bool`` -- ``True`` is an ``int`` in python and would store as ``1``
      with no complaint at all;
    * a float for an integer field, a string for anything, ``NaN``/``inf``;
    * anything outside the wire kind's range;
    * a nonzero ``f32`` value that underflows to exactly ``0.0`` on the wire.

    An ``f32`` value that survives is returned ROUNDED to float32
    (``as_f32``), so the number the database stores is the number the client
    is sent.  A caller that hands in ``400.1`` gets ``400.1000061035156``
    back and stores that; the alternative is a database and a client that
    quietly disagree about the same character with nothing measuring it.
    """
    if column not in TYPED_COLUMNS:
        raise TypedAttrError(
            f"{column!r} is not a typed attribute column "
            f"(built: {sorted(TYPED_COLUMNS)})"
        )
    spec = TYPED_COLUMNS[column]
    if value is None:
        raise TypedAttrError(
            f"{column}: None is not a value; this API does not clear a typed "
            "column back to NULL"
        )
    if isinstance(value, bool):
        raise TypedAttrError(
            f"{column}: bool is not a value for a {spec.kind} field "
            f"(python would store {value!r} as {int(value)})"
        )
    if spec.sql_type == "INTEGER":
        if not isinstance(value, int):
            raise TypedAttrError(
                f"{column}: {spec.kind} needs an int, got {type(value).__name__}"
            )
        stored: int | float = value
    else:
        if not isinstance(value, (int, float)):
            raise TypedAttrError(
                f"{column}: {spec.kind} needs a number, got {type(value).__name__}"
            )
        stored = float(value)
        if not math.isfinite(stored):
            raise TypedAttrError(f"{column}: {value!r} is not a finite number")
        if stored < spec.minimum or stored > spec.maximum:
            # checked BEFORE rounding: `struct.pack("<f", ...)` raises
            # OverflowError rather than returning anything for a double
            # outside the float32 range, and an OverflowError here would read
            # as a bug in this module rather than as a refused value
            raise TypedAttrError(
                f"{column}: {value!r} is outside the {spec.kind} range "
                f"[{spec.minimum}, {spec.maximum}]"
            )
        rounded = as_f32(stored)
        if stored != 0.0 and rounded == 0.0:
            # An adversary pass measured this: 1e-300 validates, stores, reads
            # back as 1e-300, and reaches the client as an EXACT 0.0 -- and on
            # this wire 0.0 is a value, not an absence
            # (tests/test_npc_gait_wire.py:
            # test_zero_speed_is_still_serialized_because_only_none_means_absent).
            # That is the owner's banned guessed zero arriving by arithmetic
            # instead of by a `.get(x, 0)`, so it is refused here.
            raise TypedAttrError(
                f"{column}: {value!r} underflows to exactly 0.0 as a float32, "
                "and a zero on this wire is a value rather than an absence"
            )
        stored = rounded
    if stored < spec.minimum or stored > spec.maximum:
        raise TypedAttrError(
            f"{column}: {value!r} is outside the {spec.kind} range "
            f"[{spec.minimum}, {spec.maximum}]"
        )
    return stored


def validate_all(values: Mapping[str, object]) -> dict[str, int | float]:
    """``validate`` over a whole write, refusing an empty one.

    An empty mapping is refused rather than treated as a no-op: a caller that
    computed nothing to write has a bug, and a silent success there is how a
    write that never happened gets reported as a write that did.
    """
    if not values:
        raise TypedAttrError("no typed attribute values to write")
    return {column: validate(column, value) for column, value in values.items()}


def typed_values_for_compose(stored: Mapping[str, object]) -> dict[int, int | float]:
    """``{x: value}`` for ``persistence_attr_compose``, re-validated on the way.

    ``block_gaps`` keys on PRESENCE -- ``if x in typed_values`` -- so a caller
    that builds that dict straight off a ``SELECT`` puts a ``None`` for an
    unset column past the gate and into the encoder, where it becomes a
    ``TypeError`` at emit time on a live client.  An adversary pass measured
    exactly that.  ``SQLiteStore.read_typed_attributes`` already drops NULLs,
    but nothing forces a future caller to go through it, so this is the
    conversion that does: every value is validated again here, and a ``None``
    or an out-of-range value raises rather than being handed on.
    """
    checked = {column: validate(column, value) for column, value in stored.items()}
    return {TYPED_COLUMNS[column].x: value for column, value in checked.items()}
