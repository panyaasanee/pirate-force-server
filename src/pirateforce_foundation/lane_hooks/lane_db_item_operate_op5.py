"""LANE-DB: the equip attempt the client already sends becomes a durable row.

WHAT A PLAYER SEES BECAUSE OF THIS FILE, STATED HONESTLY AND FIRST.
Nothing, today.  Nothing is composed, nothing is sent, no frame reaches a
client -- ``lane_hooks.fire()`` is report-only by construction and this
module stays inside that shape.  What changes is that an equip the player
performs stops being forgotten: today ``op=5`` reaches the seam chief landed
in ``runtime.py:9910`` (PR ``#1054``) and nothing at all happens to it, so
the same character logs back in wearing whatever it was created wearing.
After this file, the equip is a row in ``character_equipment`` that outlives
the session.  The half that puts it back ON THE SCREEN is the login/compose
read and the ``ItemOperateVitalRes`` reply, neither of which is here, and
neither of which this file claims.

WHY THIS IS NOT A PROBE.  It writes real, durable game state through the
canonical door (``store.equip_item``, the write half of
``migrations/015_character_equipment.sql``) on a plain boot with no
scenario flag -- see ``production_allowed`` below.  A probe would record
what went past; this records what the player did.

THE ONE NUMBER THIS FILE REFUSES TO GUESS, AND WHY THAT IS THE WHOLE
DESIGN.  ``RE-280`` (``pf_bridge/notes_to_chief/20260906_2258_RE-280-
RESULT-0x39-IS-A-SHIFT-BIT-INDEX-FF-MEANS-NOT-EQUIPPED.md``) closed what the
CLIENT reads: ``ItemAttr+0x39`` is a SHIFT BIT INDEX ``N`` (the client does
``mask = 1 << N`` at ``0x005833F9``/``0x005833FE`` with no table in
between), and ``0xFF`` is the sentinel for "not worn", which is why only
``N`` in ``0..31`` can ever mean a slot.  It did NOT close what the client
SENDS: the letter's own red warning is that the ``value=8`` seen on the
wire in ``RE-272`` "must not be copied into ``+0x39`` automatically -- if 8
is ``n_EQUIPTYPE`` it becomes bit 8, which may not be the weapon slot", and
static analysis explicitly neither confirmed nor refuted that coincidence.
So ``value32`` is NEVER used as a slot here.  It is printed on the console
line and nowhere else, so the next RE has the number without this server
having acted on it (``PANYA 1059``: an unknown field is never quietly
resolved).

WHAT ``slot_id`` MEANS IN THE ROW THIS FILE WRITES, SAID ONCE, PLAINLY.
It is ``n_EQUIPTYPE`` from ``data/creation_gear_by_class.tsv`` (via
``combat_pose.equip_type_for_class``) -- the game's
own kind-of-gear number -- and it is NOT ``ItemAttr+0x39``'s bit index.
``store.equip_item``'s docstring already calls ``slot_id`` "an opaque
validated byte" precisely because the wire meaning was open when it was
written; this file keeps that column opaque and says which numbering it
used, rather than inventing a translation nobody has measured.  The day the
bit index is known, the translation belongs in the code that COMPOSES the
frame -- the DB does not have to be rewritten for it, because the row
already names a real kind of gear.  The open question is filed as an RE
ticket in the same round this file lands.

WHY IT ONLY WRITES FOR THE CLASS'S OWN RIGHT-HAND WEAPON.  There is no
``item_template_id -> n_EQUIPTYPE`` table anywhere in this repository --
``equip_value_attack_behavior.tsv`` is keyed by the kind, not by the
template, and the character-creation table this lane already reads names exactly one
template per class (``n_SLOT_RHAND``).  So for exactly one item per class the server can
DERIVE the kind instead of guessing it, and for every other item it cannot.
Writing a row for the others would mean filing a hat under the weapon's
kind, so this file refuses them by name and writes nothing
(``REASON_TEMPLATE_IS_NOT_THE_CLASS_RIGHT_HAND``).  That refusal is a
measured limit of the shipped tables, not a flag: it disappears on its own
the day a template->kind table lands, without a line of this file changing
shape.

``production_allowed = True``.  Every write goes through
``store.equip_item``, which validates its own bounds, refuses an unknown or
soft-deleted character with ``KeyError``, and takes the same write lock
every other write door in ``store.py`` takes.  This module adds no new
permission: ``INSERT OR REPLACE`` against ``UNIQUE(character_id, slot_id)``
is the exact behaviour that method documents for an item swap.  It cannot
change what any frame does, because the seam it hangs on has no ``return``
and does not count the frame (chief's letter ``20260907_1718``: "every frame
leaves this block on exactly the path it left it on before").

NOTHING BELOW RAISES INTO THE LISTENER.  ``fire()`` already catches per-hook
exceptions, but relying on that alone would make every refusal look like a
crash on the console and lose the reason, so each step answers with a named
reason instead.  The one place an exception is allowed to be the answer is
the store call itself, whose failure modes are documented and are reported
by name.
"""
from __future__ import annotations

import sys

from . import hook
from ..combat_pose import equip_type_for_class
from ..persistence_class_id import CLASS_PRESETS

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
})

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
        line = "%s %s=%s" % (line, name, fields[name])
    try:
        print(line, file=sys.stderr)
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


@hook(HOOK_POINT)
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
    equip_type = equip_type_for_class(class_id)
    if right_hand is None or equip_type is None:
        _say(REASON_CLASS_NOT_IN_CREATION_GEAR, value32=value32,
             identity=item_identity, cls=class_id)
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
        store.equip_item(
            character_id=character_id,
            slot_id=equip_type,
            item_identity=row.identity,
            item_template_id=template_id,
        )
    except Exception as exc:  # noqa: BLE001 - documented failure modes, reported by name
        _say(REASON_STORE_REFUSED, value32=value32, identity=item_identity,
             cls=class_id, err=type(exc).__name__)
        return

    # slot=<n_EQUIPTYPE>, spelled out so a console reader is never left to
    # assume it is the client's bit index.  value32 is carried for the RE
    # that will decide whether the two numbers are related at all.
    _say(WROTE, character=character_id, slot_equiptype=equip_type,
         identity=row.identity, template=template_id, value32=value32,
         sid=_session_id_of(session))
