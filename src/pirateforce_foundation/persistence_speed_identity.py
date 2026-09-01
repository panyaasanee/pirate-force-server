"""LANE-DB: everything `/speed` needs to become a REMEMBERED speed, except
the SQL.

WHY THIS MODULE EXISTS.  `COO-DECISION 20260902_0147` ruled the `/speed`
ordering `(1) DB-first, wire-second`: `store.write_speed_by_identity` returns
`None` and NO frame is composed.  `LANE-GM`'s request letter
(`pf_bridge/notes_to_chief/20260902_0017_LANE-GM-TO-LANE-DB-request-speed-
persistence-method.md`) fixed the signature: the caller holds
`identity_lo`/`identity_hi` off `session.foundation.selected` and no
`character_id` at all, so the identity -> row translation belongs on this
side of the wall.

The SQL for that lives in `SQLiteStore.write_speed_by_identity`, because a
lookup, an update and a read-back have to be one transaction and only the
store owns a connection.  Everything ELSE -- which field, which column, which
refusals exist, what a refusal is CALLED -- is here, where it can be tested
without a database and imported by `gm/` without importing the store.

THE REFUSAL NAMES ARE THE POINT, not decoration.  `COO-DECISION 20260902_0147`
makes a silent refusal a banned outcome, not merely an unwanted one:

    every db refusal must answer the GM in chat immediately (for
    example `speed refused: db <reason>`) with one server-side log line
    carrying the identity and the cause; "silent" is a BANNED outcome,
    not merely an unwanted one -- a tester must be able to tell "typo"
    from "the db said no" from "the frame went out", from the screen.

(translated from the Thai; the decision letter is the original)

A bare `None` cannot satisfy that -- there is no `<reason>` in it.  So the
store exposes the requested `dict | None` method EXACTLY as LANE-GM specified
it, and a second method that returns the same answer plus one of the tokens
below.  The tokens are fixed strings and never embed the GM's typed text: the
same rule `gm/chat_command_action` already applies to its own refusals (type
name only), for the same reason -- a refusal message is echoed to a chat
window.

WHAT THIS MODULE DOES NOT DECIDE.  Which database file the store points at.
`COO-ORDER 20260901_1641` allows the `/speed` write path against an attended
round's run-copy and forbids the canonical database, and `gm/
chat_command_action._speed_db_is_canonical` is where that is enforced.
Nothing here can see a path, so no green test here means that gate was
honoured.
"""
from __future__ import annotations

from typing import Mapping

#: Wire field index for the speed this lane persists (BasicAttr+0x54, f32).
#:
#: Pinned as a literal rather than read out of
#: `persistence_attr_compose.SPARSE_APPROVED_FIELDS`: that set is a PERMISSION
#: and COO may widen it (the module says so itself), and the day it grows to
#: `{7, 12}` a `next(iter(...))` here would silently start writing a different
#: column.  `column_for` below turns this number into a column name through
#: the one table that maps them, so a rename of the column cannot desync from
#: it either.
SPEED_FIELD_X: int = 7

#: The write landed; the block is the row read back.
REASON_OK = "ok"
#: No LIVE character carries this `(identity_lo, identity_hi)`.  A
#: soft-deleted one that carries it is deliberately the same answer: the row
#: exists on disk but there is nobody to move.
REASON_NO_SUCH_CHARACTER = "no_such_character"
#: The identity itself is not a pair of `int`s.  `gm/` reads these off
#: `model.Character` where they are always `int`, so this is a caller bug
#: rather than a player's mistake -- but it is answered rather than raised
#: because it must not be able to reach SQLite: SQLite compares `7.0` equal to
#: `7`, so a float identity would MATCH A ROW and write to it.
REASON_IDENTITY_NOT_AN_INT = "identity_not_an_int"
#: The value cannot be stored or cannot survive the wire encoder --
#: `persistence_typed_attrs.validate` said so (out of range, NaN, a bool, a
#: string, a float that underflows to an exact 0.0 on the wire), or the
#: sparse compose gate refused the field.
REASON_VALUE_REFUSED = "value_refused"
#: The column's own SQL CHECK refused the write.  Reachable only if this
#: module's range table and `migrations/006_character_typed_attribute_
#: columns.sql` ever disagree, which a test pins -- kept because "the second
#: line of defence fired" must be visible rather than fatal.
REASON_SCHEMA_REFUSED = "schema_refused"
#: The row read back inside the write's own transaction does not hold what was
#: written.  Nothing rolls this into `REASON_OK`: the transaction is rolled
#: back and the caller is told, because a caller that shows the player a speed
#: this method could not verify is the exact lie `COO-DECISION 20260902_0147`
#: forbids.
REASON_READBACK_DISAGREES = "readback_disagrees"

#: Every token the two store methods may return, so a caller can assert it
#: handled all of them rather than discovering a new one in a chat window.
REASONS: frozenset[str] = frozenset({
    REASON_OK,
    REASON_NO_SUCH_CHARACTER,
    REASON_IDENTITY_NOT_AN_INT,
    REASON_VALUE_REFUSED,
    REASON_SCHEMA_REFUSED,
    REASON_READBACK_DISAGREES,
})

#: The subset that means "nothing was written and nothing is different".
#: `REASON_READBACK_DISAGREES` is in here because the write is rolled back;
#: `REASON_OK` is the only token that is not.
REFUSALS: frozenset[str] = REASONS - {REASON_OK}


def speed_column() -> str:
    """The `characters` column holding `SPEED_FIELD_X`, via the one map.

    Deferred import: `persistence_typed_attrs` imports
    `persistence_attr_compose` at its top and this module is imported by
    `store`, so keeping the import inside the call leaves this module free of
    import-order coupling to either.
    """
    from .persistence_typed_attrs import column_for

    return column_for(SPEED_FIELD_X)


def identity_is_usable(identity_lo: object, identity_hi: object) -> bool:
    """Both halves are real `int`s -- `bool` excluded.

    `type(...) is not int` rather than `isinstance`: `type(True) is bool`, so
    this rejects `True` for free and matches
    `gm/chat_command_action._selected_speed_identity` character for
    character, which is where these two values come from.
    """
    return type(identity_lo) is int and type(identity_hi) is int


def gate_value(speed: object) -> float | None:
    """The float32 to store, or `None` if nothing may be stored at all.

    This is the WHOLE refusal gate and it runs BEFORE any transaction opens,
    which is the property that keeps the store method honest: a value this
    function rejects never reaches SQLite, so `None` for a refused value can
    never mean "committed, then reported as refused".

    It refuses by composing the very block the caller would get back.  That
    is deliberate rather than convenient: `compose_sparse_block` runs
    `persistence_typed_attrs.validate` (range, type, the f32 underflow rule)
    AND the `SPARSE_APPROVED_FIELDS` permission, so a value that survives here
    is one both the column and the sparse send path already accepted.  The
    number returned is the ROUNDED float32 -- the same number the client would
    be sent -- so the column and the wire cannot disagree about one character.

    NOTE what this does not do: it does not compose the block the caller
    RECEIVES.  That one is built from the row read back inside the write's
    transaction (`SQLiteStore.write_speed_by_identity`).  This is a gate, and
    its output is thrown away except for the number.
    """
    from .persistence_attr_compose import AttrComposeError, compose_sparse_block
    from .persistence_typed_attrs import TypedAttrError

    try:
        composed = compose_sparse_block({SPEED_FIELD_X: speed})
    except (AttrComposeError, TypedAttrError):
        return None
    value = composed[SPEED_FIELD_X]
    if not isinstance(value, float):  # pragma: no cover - f32 always floats
        return None
    return value


def block_from_stored(stored: Mapping[str, object]) -> dict[int, object] | None:
    """`{7: value}` from a row read back, or `None` if the row has no speed.

    `stored` is what `SQLiteStore.read_typed_attributes` returns -- a mapping
    with the NULL columns already OMITTED -- so "the column is unset" arrives
    here as a missing key and leaves as `None`.  It is never rendered as
    `0.0`; a zero on this wire is a value rather than an absence
    (`tests/test_npc_gait_wire.py`), and inventing one is the owner's banned
    guessed zero (`COO-DECISION 20260901_1059`).
    """
    from .persistence_attr_compose import AttrComposeError
    from .persistence_typed_attrs import TypedAttrError, typed_values_for_compose
    from .persistence_attr_compose import compose_sparse_block

    column = speed_column()
    if column not in stored:
        return None
    try:
        return compose_sparse_block(
            typed_values_for_compose({column: stored[column]})
        )
    except (AttrComposeError, TypedAttrError):  # pragma: no cover - gated above
        return None
