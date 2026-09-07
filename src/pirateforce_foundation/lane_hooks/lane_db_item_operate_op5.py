"""LANE-DB: the equip attempt the client already sends becomes a durable row.

WHAT A PLAYER SEES BECAUSE OF THIS FILE, STATED HONESTLY AND FIRST.
Nothing, today.  Nothing is composed, nothing is sent, no frame reaches a
client -- ``lane_hooks.fire()`` is report-only by construction and this
module stays inside that shape.  What changes is that an equip the player
performs stops being forgotten: today ``op=5`` reaches the seam chief landed
in ``runtime.py:9910`` (PR ``#1054``) and nothing at all happens to it.
After this file, the equip is a row in ``character_equipment``.

WHAT "DURABLE" DOES AND DOES NOT MEAN HERE -- the correction a
``pf-adversary`` pass on ``#1064`` earned (finding ``D5``), kept at the top
because the earlier wording of this very docstring was the thing it caught.
The row outlives the session.  It does NOT put the item back on the
character at the next login, and this file does not claim it does:

* the login frame's worn byte is ``ItemAttrState.raw_u8_39`` in
  ``character_backpack_items``, already persisted and already on the wire in
  the StartGame ``BackpackAttr`` (``inventory.py:508``).  This file does not
  write it -- see the next paragraph for why that would be an invented
  fact, not a fix;
* ``reports/PF_RE_V130_Equipped_Blade_Negative_Boundary_20260815.md`` proves
  the client's equipment UI does not read ``BackpackAttr`` at all: refresh
  routine ``0x583290`` asks for a SEPARATE ``CollectionBagAttr`` (``0x3CD0``)
  collection, and only an item present in BOTH that collection and live
  inventory can appear worn.  This server sends no ``CollectionBagAttr``;
* that same report proves live equipment slots are the reserved range
  ``200..229`` and says, in as many words, that the absolute slot inside it
  is unrecovered and must not be chosen ("Do not choose 200, 203, or any
  other member until allocation evidence is recovered").

So the screen half of this feature is blocked on two named, filed RE
questions, not on this lane's effort, and the honest sentence is "the equip
is no longer forgotten", never "the equip comes back".

WHAT READS THE ROW TODAY, SINCE A ROW NOTHING READS IS NOT A FEATURE.  One
designed consumer exists: LANE-Q's ``lua_api/player.py`` builds
``PlayerContext.equipped_template_ids`` out of ``store.list_equipped_items``
and answers ``Player.CheckEquipItem`` from it (``lua_api/player.py:58-79``).
That consumer is SLOT-AGNOSTIC -- it reduces the rows by dropping
``slot_id`` -- which is exactly why this file can write a row today whose
slot number is provenance-backed but not yet client-proven: no reader is
relying on the number, and the swap semantics it keys do not depend on
which absolute number it is (see below).

WHAT ``slot_id`` HOLDS, AND WHY IT IS NO LONGER ``n_EQUIPTYPE``.  It holds
the client's own ``ItemAttr+0x39`` EQUIPMENT-MASK INDEX -- the ``N`` in the
``mask = 1 << N`` the client computes at ``0x005833F9``/``0x005833FE``
(``RE-280``), where ``0xFF`` means "not worn" and only ``0..31`` can ever
mean a slot.  That is the namespace
``migrations/015_character_equipment.sql`` sized the column for in its own
docstring ("bounded only to a byte ... ``ItemAttr``'s ``+0x39`` field is one
byte").

The earlier version of this file wrote ``n_EQUIPTYPE`` there, and
``pf-adversary`` finding ``D1`` proved that cannot be right, arithmetically,
from a committed table:
``pf_bridge/gamedata/tables/CONSTDATA_TH__EQUIPMENT_BASE.tsv`` has 974
equipment rows of which 650 carry ``n_EQUIPTYPE > 255``, so for two thirds
of the game's equipment the number does not fit the column at all; and
three different ``n_EQUIPTYPE`` values (8, 16, 64) share one physical
``n_EQUIPSLOT`` (24), so keying the swap on the kind would let one physical
slot accumulate rows instead of replacing them.

An index cannot break either way: it is ``0..31`` by construction, and it
IS the client's physical slot (one bit of one mask per worn item), so
``UNIQUE(character_id, slot_id)`` is exactly one item per slot and
``INSERT OR REPLACE`` is exactly the swap ``015`` was built for.

WHERE THE NUMBER COMES FROM, AND WHAT HAPPENS IF IT IS EVER WRONG.  It is
not typed in here: ``_right_hand_equipment_index()`` reads it out of the
committed sentence in
``reports/PF_RE_V130_Equipped_Blade_Negative_Boundary_20260815.md`` at
import, so the report is the single source and a test dies if that sentence
changes.  If the sentence cannot be read, the constant is ``None`` and this
hook REFUSES BY NAME (``REASON_EQUIP_INDEX_UNPROVEN``) rather than falling
back to a number -- ``PANYA 1059``: an unknown field is never quietly
resolved.  And if RE later proves a different index for the right hand, one
constant moves and one migration rewrites one column: nothing about the
behaviour (which item, which character, one row per physical slot) depends
on the absolute value.

``value32`` IS STILL NEVER USED AS A SLOT.  ``RE-280`` closed what the
client READS and explicitly did not close what it SENDS -- its own red
warning is that the ``value=8`` seen in ``RE-272`` "must not be copied into
``+0x39`` automatically".  It is printed on the console line so the next RE
has the number, and it reaches no column.

WHY IT ONLY WRITES FOR THE CLASS'S OWN RIGHT-HAND WEAPON -- the reason is
now the INDEX, not a missing table.  The correction ``D2`` earned: this
file used to claim "there is no ``item_template_id -> n_EQUIPTYPE`` table
anywhere in this repository", and that was false --
``tools/pf_equip_attack_behavior_extract.py`` implements exactly that
crosswalk for the ``2200xxx`` weapon family (``WEAPON_SLOT_KEY_BASE =
2200000``; row id = template - 2200000, and that row carries
``n_EQUIPTYPE``).  The claim is withdrawn.  It is also no longer load
bearing: this file does not want a kind at all now.  What it wants is an
``+0x39`` index, and the ONLY index with committed provenance is the
right-hand-one slot.  So every other item is refused by name
(``REASON_TEMPLATE_IS_NOT_THE_CLASS_RIGHT_HAND``) and nothing is written,
because filing a hat under the right hand's bit would be an invented fact.
That refusal is a measured limit of the recovered evidence, not a flag.

WHY THIS IS NOT A PROBE.  It writes real, durable game state through the
canonical door on a plain boot with no scenario flag -- see
``production_allowed`` below.  A probe would record what went past; this
records what the player did.

``production_allowed = True``.  Every write goes through
``store.equip_item_nowait``, which validates its own bounds through the same
``_check_equip_arguments`` the canonical ``equip_item`` uses, refuses an
unknown or soft-deleted character with ``KeyError``, and takes the same
write lock every other write door in ``store.py`` takes -- on a 250 ms
budget instead of 5,000 ms, because this hook stands on the player's own
dispatch thread.  That budget is finding ``D6``, measured: the previous
version of this file could stall one player's connection for 5.01 s under
lock contention while insisting it was "report-only", which is true of
``fire()``'s return contract and false about time.  This module adds no new
permission, and it cannot change what any frame does: the seam it hangs on
has no ``return`` and does not count the frame (chief's letter
``20260907_1718``: "every frame leaves this block on exactly the path it
left it on before").

NOTHING BELOW RAISES INTO THE LISTENER.  ``fire()`` already catches per-hook
exceptions, but relying on that alone would make every refusal look like a
crash on the console and lose the reason, so each step answers with a named
reason instead.  The one place an exception is allowed to be the answer is
the store call itself, whose failure modes are documented and are reported
by name -- and a lock refusal is reported SEPARATELY from every other store
refusal, because "somebody else was writing" and "this write was illegal"
are not the same event for anyone reading the console.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from . import console_safe, hook
from ..persistence_class_id import CLASS_PRESETS
from ..store import WriteLockTimeout

production_allowed = True

HOOK_POINT = "vital_inbound_item_operate_op5"
CONSOLE_PREFIX = "LANE_DB_EQUIP"

#: Written, and why the row is the one it is.
WROTE = "wrote"

#: Refusals.  Each names the step that could not be taken, never a value
#: this module invented to get past it.
REASON_NO_CHARACTER = "no_selected_character"
REASON_NO_BAG = "no_backpack_loaded"
REASON_BAG_UNREADABLE = "backpack_unreadable"
REASON_IDENTITY_NOT_IN_BAG = "identity_not_in_bag"
REASON_NO_CLASS_ID = "character_has_no_class_id"
REASON_CLASS_NOT_IN_CREATION_GEAR = "class_not_in_creation_gear"
REASON_TEMPLATE_IS_NOT_THE_CLASS_RIGHT_HAND = (
    "template_is_not_the_class_right_hand")
REASON_NO_STORE = "no_store_reachable"
REASON_STORE_REFUSED = "store_refused"

#: The lock was held by somebody else and this door does not wait for it.
#: Kept SEPARATE from `REASON_STORE_REFUSED` on purpose: a refusal means
#: this write was illegal, a busy means it was legal and lost a race, and
#: a console reader who cannot tell them apart cannot tell a bug from load.
REASON_STORE_BUSY = "store_busy"

#: The one number this file will not invent.  Fires when the committed
#: provenance sentence cannot be read back (see
#: `_right_hand_equipment_index`): the hook writes NOTHING rather than
#: falling back to a default slot.
REASON_EQUIP_INDEX_UNPROVEN = "equip_index_unproven"

REASONS = frozenset({
    WROTE,
    REASON_NO_CHARACTER,
    REASON_NO_BAG,
    REASON_BAG_UNREADABLE,
    REASON_IDENTITY_NOT_IN_BAG,
    REASON_NO_CLASS_ID,
    REASON_CLASS_NOT_IN_CREATION_GEAR,
    REASON_TEMPLATE_IS_NOT_THE_CLASS_RIGHT_HAND,
    REASON_NO_STORE,
    REASON_STORE_REFUSED,
    REASON_STORE_BUSY,
    REASON_EQUIP_INDEX_UNPROVEN,
})

#: The committed report this module reads its one client number out of.
#: A path built from `__file__` and joined with `/`-free segments, never a
#: `str(...relative_to(...))` (LANE-DB round `5vzis0`: that shape is what
#: puts a Windows separator into a value a test then compares).
EQUIP_INDEX_REPORT = (
    Path(__file__).resolve().parents[3]
    / "reports"
    / "PF_RE_V130_Equipped_Blade_Negative_Boundary_20260815.md"
)

#: The exact sentence that carries it.  Deliberately long: a looser pattern
#: would happily match some other "index 3" that a future edit of the
#: report drops in for an unrelated reason.
#: `\s+` between the words, not a space: the sentence is wrapped in the
#: report and a literal space silently matches nothing across the newline.
EQUIP_INDEX_SENTENCE = re.compile(
    r"statically\s+mapped\s+right-hand-one\s+equipment\s+index\s+(\d+)")


def _right_hand_equipment_index():
    """The `ItemAttr+0x39` mask index of the right-hand-one slot, read back
    out of `EQUIP_INDEX_REPORT`, or `None` when it cannot be read.

    WHY A FILE READ AT IMPORT AND NOT A LITERAL.  A literal would be this
    lane asserting a client fact on its own authority; the fact belongs to
    the V130 audit, which recovered it statically from the client and is
    committed in this repository.  Reading it back means the report is the
    single source: edit the report, and
    `test_the_equipment_index_is_the_number_the_report_states` says so
    instead of the two quietly disagreeing.  This is the same posture
    `persistence_class_id.CLASS_PRESETS` already takes toward
    `charcreate_class.tsv`.

    WHY `None` INSTEAD OF AN EXCEPTION.  An import that raises takes down
    every hook in the package, including lanes with nothing to do with
    equipment.  `None` fails this hook closed, by name, on its own console
    line, and leaves the rest of the boot alone.

    RANGE.  `RE-280` proves only `0..31` can be a mask index (`1 << N` into
    a 32-bit mask), so a number outside that is treated as unreadable
    rather than trusted -- a report that says 47 is a report that changed
    meaning, not a slot.
    """
    try:
        text = EQUIP_INDEX_REPORT.read_text(encoding="utf-8")
    except OSError:
        return None
    found = EQUIP_INDEX_SENTENCE.findall(text)
    if len(found) != 1:
        # Zero: the sentence is gone.  Two or more: the report now states
        # it more than once and this module must not pick one.
        return None
    index = int(found[0])
    if not 0 <= index <= 31:
        return None
    return index


#: The `+0x39` mask index this file writes into `character_equipment.
#: slot_id`, or `None` when the report cannot be read.
EQUIP_INDEX_RIGHT_HAND_ONE = _right_hand_equipment_index()


def _right_hand_template_by_class_id() -> dict:
    """``class_id -> n_SLOT_RHAND`` (the template id of that class's
    starting right hand), derived from ``persistence_class_id.CLASS_PRESETS``.

    NO SECOND READ OF ANY TABLE, DELIBERATELY.  This lane already builds
    that column once, in ``persistence_class_id._slot_rhand_by_class_id``,
    off ``charcreate_class.tsv`` under ``class_catalog.SOURCE_SHA256``.  An
    earlier draft of this file re-read ``creation_gear_by_class.tsv`` under
    ``combat_pose``'s own pin instead, which would have been a second
    crosswalk for one column -- the exact "a duplicated predicate is a
    predicate that will drift" shape pf-adversary has already charged this
    lane for once (``D7``, round ``5vzis0``).  The two tables DO agree
    today, and that agreement is pinned as a test rather than relied on
    here, so the day they stop agreeing a test says so instead of this
    module silently preferring one.

    ``CLASS_PRESETS`` carries three rows per class (one per creation
    "look") and ``n_SLOT_RHAND`` has no per-look variant, so the three
    agree by construction; ``dict`` assignment collapses them.
    """
    return {row[0]: row[3] for row in CLASS_PRESETS}


#: ``class_id -> template id of that class's starting right hand``.
RIGHT_HAND_TEMPLATE_BY_CLASS_ID = _right_hand_template_by_class_id()


def _say(reason: str, **fields: object) -> None:
    """One console line per fired hook, always, refusal or write.

    stderr, for the reason ``lane_hooks/__init__.py`` gives at length: the
    headless replay tools' ``--json`` mode owns stdout.  The print is
    guarded because writing to stderr is itself I/O that can fail, and this
    module's announcement must never become the failure.
    """
    line = "%s %s" % (CONSOLE_PREFIX, reason)
    for name in sorted(fields):
        try:
            rendered = "%s" % (fields[name],)
        except Exception:  # noqa: BLE001 - a value whose __str__ raises is still a line
            rendered = "<unprintable>"
        line = "%s %s=%s" % (line, name, rendered)
    try:
        print(console_safe(line), file=sys.stderr)
    except Exception:  # noqa: BLE001 - the announcement must never be the failure
        pass


def _character_of(session):
    try:
        return session.foundation.selected
    except Exception:  # noqa: BLE001 - an unreachable attribute is its own answer
        return None


def _store_of(session):
    try:
        return session.foundation.lifecycle.store
    except Exception:  # noqa: BLE001 - see _character_of
        return None


def _session_id_of(session):
    try:
        return session.foundation.session_id
    except Exception:  # noqa: BLE001 - see _character_of
        return None


def _bag_row_for(session, item_identity):
    """The one bag row wearing ``item_identity``, or a reason.

    Returns ``(row, None)`` or ``(None, reason)``.  ``BackpackState``
    already guarantees identities are unique within a bag
    (``inventory.py:133``), so a second match would mean the value object
    was built by something that skipped that gate -- treated as unreadable
    rather than resolved by picking one.
    """
    try:
        bag = session.foundation.backpack
    except Exception:  # noqa: BLE001 - see _character_of
        return None, REASON_BAG_UNREADABLE
    if bag is None:
        return None, REASON_NO_BAG
    try:
        matches = [row for row in bag.items if row.identity == item_identity]
    except Exception:  # noqa: BLE001 - a bag whose rows do not read is unreadable
        return None, REASON_BAG_UNREADABLE
    if len(matches) != 1:
        return None, (
            REASON_IDENTITY_NOT_IN_BAG if not matches
            else REASON_BAG_UNREADABLE)
    return matches[0], None


def _class_id_of(character):
    try:
        class_id = character.class_id
    except Exception:  # noqa: BLE001 - see _character_of
        return None
    if not isinstance(class_id, int) or isinstance(class_id, bool):
        # bool is an int subclass and True == 1, so a True here would look
        # up class 1 and write a Gladiator's row -- combat_pose carries the
        # same exclusion for the same measured reason.
        return None
    return class_id


# The point name is spelled as a LITERAL here, not as ``HOOK_POINT``, and
# that is not a style choice: ``gm/lane_gate_name_audit.py``'s dead-hook-point
# audit grades every registration from source, and a name it cannot read as a
# string literal makes it refuse to grade ANY hook point in the tree
# (``hook_point_audit_undecidable_dynamic_name``) -- one lane's constant would
# blind the audit for every lane.  Measured, not assumed: this file registered
# with ``@hook(HOOK_POINT)`` first and turned
# ``test_the_repository_registers_no_hook_point_that_nothing_fires`` red.
# ``test_the_decorator_literal_and_the_constant_cannot_drift_apart`` below
# reads this decorator back with AST so the two spellings stay one fact.
@hook("vital_inbound_item_operate_op5")
def remember_the_equip(session=None, value32=None, item_identity=None) -> None:
    """Persist an ``op=5`` equip for the one item whose kind is derivable.

    Every argument is keyword-defaulted because ``fire()`` calls hooks with
    ``**kwargs`` and a future call site that stops passing one of them must
    produce a named refusal here, not a ``TypeError`` swallowed by
    ``fire()``.
    """
    character = _character_of(session)
    if character is None:
        _say(REASON_NO_CHARACTER, value32=value32, identity=item_identity)
        return

    row, reason = _bag_row_for(session, item_identity)
    if row is None:
        _say(reason, value32=value32, identity=item_identity)
        return

    class_id = _class_id_of(character)
    if class_id is None:
        _say(REASON_NO_CLASS_ID, value32=value32, identity=item_identity)
        return

    right_hand = RIGHT_HAND_TEMPLATE_BY_CLASS_ID.get(class_id)
    if right_hand is None:
        _say(REASON_CLASS_NOT_IN_CREATION_GEAR, value32=value32,
             identity=item_identity, cls=class_id)
        return

    if EQUIP_INDEX_RIGHT_HAND_ONE is None:
        # The committed sentence could not be read.  Writing anyway would
        # mean this lane naming a client slot on its own authority.
        _say(REASON_EQUIP_INDEX_UNPROVEN, value32=value32,
             identity=item_identity, cls=class_id,
             report=EQUIP_INDEX_REPORT.name)
        return

    try:
        template_id = row.template_id
    except Exception:  # noqa: BLE001 - see _bag_row_for
        _say(REASON_BAG_UNREADABLE, value32=value32, identity=item_identity)
        return

    if template_id != right_hand:
        # The refusal RE has to close, not a bug: no table in this
        # repository maps this template to a kind of gear, and filing it
        # under the right hand's kind would be an invented fact.
        _say(REASON_TEMPLATE_IS_NOT_THE_CLASS_RIGHT_HAND, value32=value32,
             identity=item_identity, cls=class_id, template=template_id,
             right_hand=right_hand)
        return

    store = _store_of(session)
    character_id = getattr(character, "id", None)
    if store is None or not isinstance(character_id, int) or isinstance(
            character_id, bool):
        _say(REASON_NO_STORE, value32=value32, identity=item_identity,
             cls=class_id)
        return

    try:
        rowid = store.equip_item_nowait(
            character_id=character_id,
            slot_id=EQUIP_INDEX_RIGHT_HAND_ONE,
            item_identity=row.identity,
            item_template_id=template_id,
        )
    except WriteLockTimeout as exc:
        # Somebody else held the write lock and this door does not wait for
        # it on a player's dispatch thread.  A legal write that lost a race
        # is not a refusal, and the console must not read like one.
        _say(REASON_STORE_BUSY, value32=value32, identity=item_identity,
             cls=class_id, err=type(exc).__name__)
        return
    except Exception as exc:  # noqa: BLE001 - documented failure modes, reported by name
        _say(REASON_STORE_REFUSED, value32=value32, identity=item_identity,
             cls=class_id, err=type(exc).__name__)
        return

    # `slot_equip_index=` names the numbering out loud, so a console reader
    # is never left to guess whether it is the client's mask index, a kind
    # of gear, or the wire's own value32 -- all three are different numbers
    # and only the first one is in the column.  `row=` is the id read back
    # inside the writing transaction, so this line means "the row is
    # there", not "the call returned".
    _say(WROTE, character=character_id,
         slot_equip_index=EQUIP_INDEX_RIGHT_HAND_ONE, row=rowid,
         identity=row.identity, template=template_id, value32=value32,
         sid=_session_id_of(session))
