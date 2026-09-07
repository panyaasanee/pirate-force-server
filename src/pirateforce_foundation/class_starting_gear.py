"""LANE-CS: the backpack a character should be born with, per her own class.

WHY THIS FILE EXISTS.  LANE-DB measured (``pf_bridge/notes_to_chief/
20260907_2032_LANE-DB-TO-COO-four-of-five-classes-start-with-another-class-
weapon.md``) that ``store._insert_initial_backpack`` writes
``inventory.INITIAL_BACKPACK`` for every new character, and that state
carries template ``2200002`` -- which ``CHARCREATE_CLASS`` lists as the
Gladiator's ``n_SLOT_RHAND``.  Four of the five playable classes have a
different right-hand item in that same table, so four of five characters are
born carrying the first class's weapon in the bag.  ``COO-DECISION
20260907_2148`` (answering that letter, file ``20260907_2148_COO-DECISION-
db2032-class-weapon-at-birth-owner-is-cs-LANE-CS.md``) put the class-to-item
map in this lane's zone, chose "fix it at birth" over a migration, and named
the one binding constraint: **class 1 must keep the exact V141
``BackpackAttr`` bytes it has today**.

WHAT IT DOES.  ``starting_backpack_state(class_id)`` returns
``INITIAL_BACKPACK`` with exactly one field different: the ``template_id``
of the single weapon row, read through ``class_catalog.starting_hand_slots``
off the committed table.  Nothing else moves -- identities, slots,
quantities, the two raw bytes, the base/range masks and the row ORDER are
the ones ``inventory.py`` already ships, because the encoder walks the rows
in list order and any reordering here would change the wire bytes for a
reason no table supports.

CLASS 1 IS THE SAME OBJECT, NOT AN EQUAL COPY.  For ``class_id == 1`` this
returns ``INITIAL_BACKPACK`` itself, so ``inventory.make_backpack_attr``'s
inline ``state == INITIAL_BACKPACK`` check -- the one that compares against
the frozen ``legacy.make_backpack_attr_four_items()`` V141 bytes -- still
fires for Gladiators exactly as it does today.  A test pins the identity,
not just equality: an "equal copy" would silently keep that V141 guard
running, but it would also be the shape in which a later field edit could
drift class 1 away without the guard noticing which object it was handed.

WHICH ROW IS THE WEAPON ROW IS DERIVED, NEVER COUNTED.  The row to change is
found by matching class 1's own ``n_SLOT_RHAND`` value against the templates
in ``INITIAL_BACKPACK`` and requiring exactly one hit.  It is not row index
3, not "the last row", and not "the row in slot 3": if either the table's
Gladiator weapon or the starting bag ever moves, this module raises at
import instead of quietly rewriting a potion into a sword.

WHAT IS NOT DECIDED HERE, ON PURPOSE.

* ``n_SLOT_LHAND`` is not represented.  The starting bag has ONE weapon row;
  class 1's two hand slots hold the same id, so today's bag cannot tell us
  whether the left-hand id was ever meant to be in it.  Two classes have a
  ``0`` there.  Inventing a fifth row would change the row count, and with
  it every ``BackpackAttr`` size the project has measured.
* Nothing is equipped.  This is the BAG at birth.  What a character has in
  hand on screen comes from ``AvatarAttr``, which the client itself already
  sends per class (that is how ``persistence_class_id.resolve_class_id``
  recognises the class at all) -- so this module changes what she is
  CARRYING, not what she is wearing.
* Characters that already exist are not touched.  ``COO-DECISION
  20260907_2148`` explicitly left the migration question open for the owner
  ("migration+backup or leave it -- you decide"), and this module has no
  write path of any kind.

NOT WIRED YET, AND THE SEAM ALONE IS NOT ENOUGH -- READ THIS BEFORE WIRING
IT.  ``pf-adversary`` (round ``e8pss9``, finding D1) booted a real store, a
real ``lifecycle`` and ``FoundationSession.select_and_start`` with the bag
this module composes for a Sniper and measured:

    BAG_ADMISSION verdict=refused golden=initial acquired=0
                  reason=golden_item_moved_or_altered
    SELECT_AND_START_RAISED PermissionError

Gate 2 (``bag_admission.may_enter_world``) refuses every class but 1 today,
because ``INITIAL_BACKPACK`` is not one thing wearing one hat: it is the
V141 encoder golden AND gate 2's admission golden AND
``inventory.require_known_backpack``'s content allowlist AND
``store.apply_v111_stack_merge``'s exact pre-state.  Three of those four
still spell "carries 2200002" as part of "is a legal bag", so today there is
no such thing anywhere in this server as a valid non-Gladiator bag.  Wiring
the seam without answering that first would let a Paladin be created and
then refuse her at select with no reply frame at all -- the client would sit
on "connecting" forever.  ``tests/test_class_starting_gear.py::
Gate2RefusesEveryClassButOneTodayTests`` pins that refusal so it cannot be
discovered by a player instead of by a test.

So the ``store.py`` seam (``pf_bridge/notes_to_chief/20260907_2237_LANE-CS-
CORE-REQUEST-the-starting-bag-needs-the-class-she-picked.md``) is filed as
HOLD, and the question of who owns the golden a non-Gladiator bag is
measured against went to COO in ``pf_bridge/notes_to_chief/20260907_2258_
LANE-CS-ASK-COO-there-is-no-legal-non-gladiator-bag-yet.md``.  Until both
are answered no character's bag changes, ``production_allowed`` stays
``False``, and a test measures that no production module imports this one.
"""

from __future__ import annotations

from . import class_catalog
from .inventory import INITIAL_BACKPACK, BackpackState, ItemAttrState

# This module composes a state; it is not reachable from any boot path until
# the CORE-REQUEST seam lands.  See the docstring's "NOT WIRED YET".
production_allowed = False

# The class whose bag the committed INITIAL_BACKPACK already is.  Everything
# below is derived from this one number plus the table; it is not a second
# name for "the first row" or "the default".
V141_BAG_CLASS_ID = 1

_MODULE_NAME = "class_starting_gear"


class ClassStartingGearError(RuntimeError):
    """Raised when the bag and the table no longer agree about the weapon."""


def _weapon_row_index() -> int:
    """The index in INITIAL_BACKPACK.items of the row holding class 1's weapon.

    Raises rather than guessing when the answer is not exactly one row: a
    zero means the committed bag no longer carries the table's Gladiator
    weapon at all, a two means the id is ambiguous and no rule in this
    module could pick between them.
    """
    rhand, _lhand = class_catalog.starting_hand_slots(V141_BAG_CLASS_ID)
    hits = [
        index
        for index, item in enumerate(INITIAL_BACKPACK.items)
        if item.template_id == rhand
    ]
    if len(hits) != 1:
        raise ClassStartingGearError(
            "INITIAL_BACKPACK carries %d rows with class %d's n_SLOT_RHAND "
            "(%d); exactly one is required to know which row is the weapon"
            % (len(hits), V141_BAG_CLASS_ID, rhand)
        )
    index = hits[0]
    row = INITIAL_BACKPACK.items[index]
    # "Exactly one hit" alone cannot tell a weapon row from a cask row:
    # pf-adversary (D2) drifted class 1's n_SLOT_RHAND to the cask template,
    # which also appears exactly once, and got a Sniper born with a rifle in
    # the cask slot and the Gladiator sword still in the weapon slot -- the
    # "potion rewritten into a sword" this module says it cannot do.  The
    # identity and slot of the committed weapon row are therefore part of
    # the match, so a drifted table changes WHICH ROW ONLY IF the whole row
    # moved with it, and otherwise refuses.
    if (row.identity, row.slot) != _V141_WEAPON_ROW_ID_AND_SLOT:
        raise ClassStartingGearError(
            "the row carrying class %d's n_SLOT_RHAND (%d) is identity %d in "
            "slot %d, not the committed weapon row %r -- the table and the "
            "bag no longer agree about which row is the weapon"
            % (V141_BAG_CLASS_ID, rhand, row.identity, row.slot,
               _V141_WEAPON_ROW_ID_AND_SLOT)
        )
    return index


# The committed weapon row's own (identity, slot), read off the bag at import
# rather than spelled as numbers: it is whatever row currently carries class
# 1's table weapon, and _weapon_row_index() then refuses any drift that would
# move the weapon to a DIFFERENT row of the same bag.
_V141_WEAPON_ROW_ID_AND_SLOT = next(
    (item.identity, item.slot)
    for item in INITIAL_BACKPACK.items
    if item.template_id == class_catalog.starting_hand_slots(V141_BAG_CLASS_ID)[0]
)

WEAPON_ROW_INDEX = _weapon_row_index()


def starting_weapon_template(class_id: int) -> int:
    """The template id class_id's starting bag should carry in its weapon row.

    Verbatim ``n_SLOT_RHAND`` from the committed ``CHARCREATE_CLASS`` row.
    Raises ``KeyError`` for an unknown class id -- there is no fallback to
    class 1, because "unknown class silently gets a Gladiator sword" is the
    exact bug this module exists to end.
    """
    rhand, _lhand = class_catalog.starting_hand_slots(class_id)
    if rhand <= 0:
        raise ClassStartingGearError(
            "class_id %r has no right-hand item in the table (n_SLOT_RHAND="
            "%r); the starting bag's weapon row cannot be sourced" % (class_id, rhand)
        )
    return rhand


def starting_backpack_state(class_id: int) -> BackpackState:
    """INITIAL_BACKPACK, with the weapon row carrying class_id's own weapon.

    ``class_id == 1`` returns the committed object itself (see the module
    docstring) so the V141 byte pin inside ``inventory.make_backpack_attr``
    keeps guarding Gladiators unchanged.
    """
    # bool first and on its own: `True` is an int, sqlite binds it as 1, and
    # `isinstance` (not `type() is`) keeps an IntEnum from the seam's own
    # resolver usable.  Written as two terms that can each be the sole reason
    # for the raise -- the earlier `type() is not int or isinstance(bool)`
    # form had a second term nothing could ever reach (pf-adversary D7).
    if isinstance(class_id, bool) or not isinstance(class_id, int):
        raise TypeError("class_id must be int, not %r" % (type(class_id).__name__,))
    template = starting_weapon_template(class_id)
    if class_id == V141_BAG_CLASS_ID:
        return INITIAL_BACKPACK
    rows = list(INITIAL_BACKPACK.items)
    # Re-derived per call, not read off the module global: a global is a
    # literal index the moment anything assigns to it, and the docstring's
    # "not row index 3, not the last row" has to be true of the path that
    # actually ships (pf-adversary D2 killed both mutants through it).
    index = _weapon_row_index()
    weapon = rows[index]
    rows[index] = ItemAttrState(
        weapon.identity,
        template,
        weapon.quantity,
        weapon.slot,
        weapon.raw_u8_38,
        weapon.raw_u8_39,
        weapon.detail_present,
    )
    return BackpackState(
        INITIAL_BACKPACK.base_mask,
        INITIAL_BACKPACK.base_identity,
        INITIAL_BACKPACK.range_mask,
        tuple(rows),
    )


def describe(class_id: int) -> str:
    """One console-safe ASCII token line for one class.

    Printed by ``__main__`` below so an attended run and a headless run can
    be compared word for word.  It reports what THIS module would compose;
    it does not claim anything was written to any database.
    """
    state = starting_backpack_state(class_id)
    templates = ",".join(str(item.template_id) for item in state.items)
    return (
        "CLASS_STARTING_GEAR class_id=%d name=%s rhand=%d bag_templates=(%s) "
        "weapon_row=%d rows=%d same_object_as_v141=%s"
        % (
            class_id,
            class_catalog.class_name(class_id),
            starting_weapon_template(class_id),
            templates,
            WEAPON_ROW_INDEX,
            len(state.items),
            "YES" if state is INITIAL_BACKPACK else "NO",
        )
    )


def count_production_importers(root=None) -> int:
    """How many shipped modules import this one, counted at run time.

    pf-adversary (D3) dropped a real importer into the package and the
    console token still printed ``wired_callers=0``, because the zero was
    inside the format string: a number that can only ever be the number it
    already is.  This walks the package's parsed modules instead, so the
    operator's console reports what is true of the tree it is running on.
    """
    import ast
    import pathlib

    here = pathlib.Path(__file__).resolve()
    base = here.parent if root is None else pathlib.Path(root)
    count = 0
    for path in sorted(base.rglob("*.py")):
        if path == here:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(a.name.split(".")[-1] == _MODULE_NAME for a in node.names):
                    count += 1
                    break
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[-1] == _MODULE_NAME or any(
                    a.name == _MODULE_NAME for a in node.names
                ):
                    count += 1
                    break
    return count


def main() -> int:
    for class_id in class_catalog.CLASS_IDS:
        print(describe(class_id))
    print(
        "CLASS_STARTING_GEAR_SUMMARY classes=%d wired_callers=%d "
        "production_allowed=%s gate2_admits_non_class_1=NO"
        % (
            class_catalog.CLASS_COUNT,
            count_production_importers(),
            production_allowed,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - console entry
    raise SystemExit(main())
