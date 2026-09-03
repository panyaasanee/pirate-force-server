"""The live value of every named ActorAttr/BasicAttr row, for one character.

COO-DECISION 2026-09-04T00:47+07:00 item 1, restated as an order in
COO-DECISION 2026-09-04T01:45+07:00 item 3 (chief's read point is the one
thing two lanes are standing still for).  This module is the SOURCE; the
point lanes actually call is ``lane_hooks.current_named_attr_values``, which
holds nothing but a registration slot.

WHY IT EXISTS.  ``RE-222`` Q0 (SHA-pinned, static) measured that the
client's ``ActorAttr`` apply is a FULL-OBJECT COPY whose constructor zeroes
HP, MP and cash before decode touches them.  So an ``UpdateAttrVital``
0x309A frame that sets a mask bit for one field and leaves the rest unset
does not say "leave the others alone", it says "make the others zero".  That
is not a hypothetical: ``GT-218`` is the owner watching it happen -- a
``/speed 400`` command carrying the very value login sends every day killed
the client in one frame (HP ``0/1``, cash ``0``).  Condition (b') of the
``attr_wire`` unlock (COO-DECISION 20260904_0046 item 3) is therefore
"EVERY ``known=True`` row carries its REAL value at send time", and a real
value has to be read from somewhere.  Here.

WHAT "REAL" MEANS HERE, AND THE ONE RULE THAT SHAPES EVERY LINE BELOW: a row
this repository has no honest source for is OMITTED, never defaulted, never
zeroed, never guessed (COO-DECISION 20260904_0047 item 1, in those words;
the same "never guess zero" rule as COO-DECISION 20260901_1059).  Omission
is not a soft failure -- ``attr_wire.live_named_values`` turns ONE missing
row into a refusal of the whole send, by design.  A partial dict from here
costs a refused command; a fabricated value costs the player's cash.

WHAT IS AND IS NOT SOURCED TODAY, measured on ``main`` at
``0765f0e1`` (chief, round ``dwvbpm``/R330).  ``named_field_x()`` asks for 26
rows.  This module can answer:

  * x=1 name -- ``store.get_character(cid).name`` (``store.py:632``, the row
    written at ``create_character``; ``characters.name`` is deliberately NOT
    a typed attribute column, ``persistence_typed_attrs.py:117``).
  * x=2 level, x=3 hp_current, x=4 hp_max -- the three columns
    ``create_character`` really writes at birth (``store.py:569``, from the
    birth-values helper in ``persistence_vitals`` -- named in words, not
    spelled, because that module's own test file refuses any file outside
    its one ordered call site whose TEXT contains the name, comments
    included) and that ``migrations/009`` gives a DEFAULT, read back through
    ``store.read_typed_attributes`` (``store.py:1126``) and mapped by
    ``persistence_typed_attrs``' own ``x``/column pairing (``:160``).

TWENTY-ONE ROWS HAVE A COLUMN AND NO VALUE, AND THAT IS NOT THE SAME AS
HAVING A SOURCE.  ``persistence_typed_attrs.TYPED_COLUMNS`` also addresses
x=5, 6, 13, 16, 17, 18-24 and 31-35, so the read below reaches them
structurally -- but every one of those columns is NULL on every character
today: ``migrations/006`` declares them with no DEFAULT, ``migrations/009``
defaults only level/hp/speed_walk, and no writer for any of them exists
anywhere in ``src/`` (measured, chief round ``dwvbpm``, corroborated on a
real newborn by ``GT-215``: ``mp_current=None class_id=None cash=None
stat_str=None``).  ``read_typed_attributes`` OMITS a NULL column rather than
rendering it ``0`` (``store.py:1157``), so this module inherits the "never
guess zero" rule from the layer below instead of re-implementing it: an
unseeded ``cash`` arrives here as a missing key and ends in a refused send,
never a zeroed wallet.  The day LANE-DB seeds one of those columns, this
module starts answering that row with NO CHANGE HERE -- which is the point of
reading through the column map rather than listing rows by hand.

And five rows this module cannot answer at all, with the reason each:

  * x=8 death_timer -- no column, no login emission.  ``player_wire.py``
    composes no dying countdown, and ``persistence_typed_attrs`` addresses
    no x=8.  Omitted.
  * x=11 basic_faction -- ``world_faction_admission.PROVEN_BASIC_FACTION``
    exists, but whether login sends the row AT ALL is a per-SCENE policy
    (``world_faction_admission.admits``, guarded again at
    ``player_wire.py:377-398``).  A ``character_id`` alone cannot answer it,
    and answering it from the constant would be the guess this module exists
    to refuse.  Omitted.
  * x=37 wstr_164_guild -- no guild table exists in this project.  Also
    guarded by name: PANYA-DECISION 20260828_0125 item (3) says the character
    NAME goes in BasicAttr x=1 and never in x=37, so the one string this
    module does hold must not drift into this row.  Omitted.
  * x=52, 53 alt_hp_current/alt_hp_max -- selector-gated rows (used only when
    ``0x430E10(x9)==8``, ``attr_wire.FIELDS`` row note / SELECTOR_NOTE_R301).
    Nothing in this repository resolves that selector.  Omitted.

TWO ROWS LOGIN SENDS AS CONSTANTS ARE STILL OMITTED, AND THIS IS A JUDGMENT
CALL STATED OUT LOUD RATHER THAN MADE QUIETLY.  COO-DECISION 20260904_0047
item 1 names "cash/level/other rows from what login composes for the client
today" as an acceptable source, and login does emit x=13 class
(``player_wire.PLAYER_LOGIN_CLASS_ID = 1``, graded ``[PROPOSED, not
measured]`` at ``player_wire.py:18-22``) and x=24 cash
(``legacy.V116_INITIAL_CASH``).  They are omitted anyway because a constant
is not this character's value: ``GT-215`` measured the DB column NULL while
the composer sent the constant, and the owner's own HUD read "1 gold" against
a composer sending 10000 -- an unreconciled disagreement.  Sending a number
into a full-object copy on the strength of it would be exactly the guess
``GT-218`` priced.  Including them would ALSO change nothing today: 19 other
rows are missing regardless, so the send refuses either way.  Reversing this
costs one line each and belongs to whoever reconciles that disagreement.

So today the read point answers 4 of 26 rows and ``attr_wire`` refuses every
named-field send.  THAT IS THE SHIPPED, CORRECT OUTCOME of this round rather
than a shortfall to pad: what changes is that the refusal stops being
``no_read_point`` ("nobody built the door") and becomes
``missing_named_rows: 5,6,8,...`` ("here is the exact list of values this
server does not know"), which is a work list for LANE-DB and RE-122 instead
of a dead end.

x=7 (movement speed, ``basic_f32_54``) is NOT in this module's output even
though ``speed_walk`` is a typed column, and that is deliberate: x=7 is
``known=False`` in ``attr_wire.FIELDS``, so it is not one of the rows (b')
covers, and ``named_field_x()`` -- the filter below -- excludes it.  A
``known=False`` row that arrived here would set a mask bit for a field whose
meaning nobody has confirmed.

THIS MODULE NEVER SENDS AND NEVER WRITES.  It reads.  Every caller of it is
on a path that composes bytes somewhere else, behind its own gate
(COO-DECISION 20260904_0047 item 1: "do not send bytes from this point").
"""
from typing import Any, Callable


#: The rows ``named_field_x()`` asks for that this server cannot reach AT ALL
#: -- no typed column addresses them, so no amount of seeding makes them
#: appear and each needs its own decision (see the module docstring for the
#: reason per row).  Distinct from the rows that HAVE a column and no value:
#: those arrive here automatically the day one is written, and are therefore
#: deliberately absent from this tuple.  Pinned so a round that lands one
#: sees this constant shrink rather than discovering the change in a console
#: line.
ROWS_WITH_NO_COLUMN_AT_ALL: tuple[int, ...] = (8, 11, 37, 52, 53)


def named_rows_wanted() -> tuple[int, ...]:
    """Exactly ``attr_wire.named_field_x()`` -- the rows (b') covers.

    Imported lazily and by name: ``gm.attr_wire`` resolves ``lane_hooks``
    lazily in the other direction (its own ``live_named_values`` docstring
    says why), and this module is reachable from boot wiring, so neither
    side may close the cycle at module scope.
    """
    from .gm import attr_wire  # noqa: PLC0415 - see docstring

    return attr_wire.named_field_x()


def values_for(store, character_id) -> dict:
    """Every named row this repository really knows for ``character_id``.

    Returns a dict keyed by ``x``.  A row with no honest source is ABSENT --
    never ``0``, never a constant standing in for a column nobody wrote.

    NEVER RAISES, and that is the contract the caller depends on rather than
    a convenience: this runs behind ``lane_hooks.current_named_attr_values``,
    whose consumer (``attr_wire.live_named_values``) converts any exception
    into the opaque ``read_point_raised_<Type>`` refusal.  An unknown
    character, a store that has not migrated, a driver error -- all of them
    are "we know nothing about this character", which is a complete and
    honest answer here and becomes a named per-row refusal one layer up.
    An empty dict is therefore a real answer, not an error signal.

    ``store`` is duck-typed on purpose: the two methods it needs are read-only
    and already public, and the tests hand in a stub rather than a migrated
    SQLite file.
    """
    wanted = set(named_rows_wanted())
    values: dict[int, Any] = {}

    # The typed columns first.  `read_typed_attributes` already omits every
    # NULL column (store.py:1126's own docstring), so nothing here has to
    # decide what an unwritten column means.
    try:
        from . import persistence_typed_attrs as typed_attrs  # noqa: PLC0415

        columns = store.read_typed_attributes(character_id)
    except Exception:  # noqa: BLE001 - see docstring
        columns = {}
    else:
        x_for_column = {
            spec.column: spec.x for spec in typed_attrs.TYPED_COLUMNS.values()
        }
        for column, value in columns.items():
            x = x_for_column.get(column)
            if x is None or x not in wanted:
                continue
            values[x] = value

    # x=1 lives on the character row itself, not in a typed column
    # (persistence_typed_attrs.NOT_A_TYPED_ATTRIBUTE_COLUMN).  A name that is
    # not a `str` -- or a row that cannot be read at all -- is an absent row,
    # never an empty string: an empty name is a value the client would apply.
    if 1 in wanted:
        try:
            name = store.get_character(character_id).name
        except Exception:  # noqa: BLE001 - see docstring
            name = None
        if isinstance(name, str) and name:
            values[1] = name

    return values


def source_for_store(store) -> Callable[[Any], dict]:
    """The callable ``lane_hooks.register_live_attr_values_source`` wants.

    Bound to one store, which in this process is the one the boot opened
    (``app.py``) -- the character id is what selects a character, so a single
    process-wide source serves every connection without any of them being
    able to read another's values by accident: a caller that hands in the
    wrong id gets that id's row, exactly as it would from the store directly.
    """
    def read_live_named_attr_values(character_id) -> dict:
        return values_for(store, character_id)

    return read_live_named_attr_values
