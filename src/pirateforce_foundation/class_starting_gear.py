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

Gate 2 -- the character-select admission predicate ``session.py`` asks
before world entry -- refuses every class but 1 today,
because ``INITIAL_BACKPACK`` is not one thing wearing one hat: it is the
V141 encoder golden AND gate 2's admission golden AND
``inventory.require_known_backpack``'s content allowlist AND
``store.apply_v111_stack_merge``'s exact pre-state.  Three of those four
still spell "carries 2200002" as part of "is a legal bag", so today there is
no such thing anywhere in this server as a valid non-Gladiator bag.  Wiring
the seam without answering that first would let a Paladin be created and
then refuse her at select with no reply frame at all -- the client would sit
on "connecting" forever.  ``tests/test_class_starting_gear.py::
Gate2RefusesEveryClassButOneTodayTests`` pins that refusal through the term
it turns on (``inventory.is_unmoved_baseline``) and through gate 3's own
raise, so it cannot be discovered by a player instead of by a test.  It
does that WITHOUT importing or naming the gate-2 module: that module
carries another lane's pin admitting exactly one caller and a named list of
files that may mention it, and adding this lane to a list is the move
``COO-DECISION 20260907_2050`` forbids outright.

So the ``store.py`` seam (``pf_bridge/notes_to_chief/20260907_2237_LANE-CS-
CORE-REQUEST-the-starting-bag-needs-the-class-she-picked.md``) is filed as
HOLD, and the question of who owns the golden a non-Gladiator bag is
measured against went to COO in ``pf_bridge/notes_to_chief/20260907_2258_
LANE-CS-ASK-COO-there-is-no-legal-non-gladiator-bag-yet.md``.  Until both
are answered no character's bag changes and ``production_allowed`` stays
``False``.

WHO MAY IMPORT THIS MODULE (``COO-DECISION 20260908_1246``).  The pin used
to read "no production module imports this one".  That zero was the thing
blocking LANE-DB from putting the five-bag set behind their own gates
(their letter ``pf_bridge/notes_to_chief/20260908_1155_LANE-DB-TO-COO-five-
bag-set-is-blocked-by-a-no-importer-pin.md``), and COO lifted it to "the
importer is ``inventory``".  The pin is now a NAMED one: ``production_
importers()`` reports dotted names, not a count, so an importer under
another name -- ``lane_hooks.inventory`` included -- is a different string
from the one allowed.

The decision spells the lifted pin ``== 1``.  This module's tests spell it
"at most one, and it is ``inventory``", which is NOT what was ordered, and
the difference is a lane decision, flagged ``[assumption of LANE-CS -
awaiting COO confirmation]``, letter ``pf_bridge/notes_to_chief/20260908_
1345_LANE-CS-ASK-COO-exactly-one-importer-would-leave-main-red-until-db-
wires.md``.  Read the decision before the reasoning: it says
``importer==1 (passes when DB wires it)``, so COO DID foresee that the
strict form is red until LANE-DB's PR lands and accepted that.  The lane's
disagreement is narrower than "COO did not know": ``pytest tests/test_
class_starting_gear.py`` is inside the preflight gate every lane must pass
before pushing anything at all, so the strict form stops seven other lanes
from pushing for as long as the window lasts, and this round could not
have pushed itself.  If COO wants the strict form anyway, the revert is
one line per assertion and the letter says which; the ordering constraint
is that LANE-DB's wiring must land first or with it.

AND THE HONEST LIMIT OF THAT CHOICE (pf-adversary D1 of round ``wz0brc``,
measured): "at most one" does NOT keep this file green through the
wiring.  Wire ``inventory`` for real and
``Gate2RefusesEveryClassButOneTodayTests`` goes red -- 8 failures, 4
subtests each in two tests -- exactly as its own docstring promises ("the
day someone answers what a legal Paladin bag is, they go red and must be
rewritten by the person who answered").  What "at most one" buys is only
the window BETWEEN this PR and that one, and nothing more.  Whoever
answers "what is a legal non-Gladiator bag" owns rewriting those four
subtests in the same PR that wires the set; this lane will not have
rewritten them in advance against a golden nobody has agreed on.

HOW ``inventory`` CAN IMPORT THIS MODULE, PRECISELY (corrected by
pf-adversary D3, measured).  This module reads ``INITIAL_BACKPACK`` from
``inventory`` at import, so an import of it placed ABOVE that name's
definition in ``inventory.py`` -- at the top of the file, next to
``from __future__`` -- is a circular import that dies with "partially
initialized module" before the server has a socket.  An import placed
BELOW it, module level and all, works and yields five bags at import time.
So the rule is ORDER WITHIN THE FILE, not "module level is impossible":
the earlier wording of this docstring said the latter and it is false.
A deferred import inside the function that needs the set works from
anywhere, and the pin counts every one of these shapes, because the walk
parses the tree instead of reading the first lines of the file.

``production_allowed`` is NOT part of that lift and stays ``False``: COO
kept it shut in the same decision, because ``0945`` says a flag comes down
after a client has been seen to show the thing, and no client has yet shown
five different bags at birth.
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


def starting_backpack_states() -> tuple[BackpackState, ...]:
    """Every legal starting bag, one per class, in class-id order.

    This is the SET COO-DECISION 20260907_2342 put in place of the single
    ``INITIAL_BACKPACK`` golden.  LANE-DB owns gates 2/3/4 and changes them
    from ``== INITIAL_BACKPACK`` to ``in starting_backpack_states()``; this
    lane owns what the set contains.  Nothing here reads or writes a
    database, and this module still has no production importer.

    Why a tuple and not a set: ``in`` on a tuple compares with ``==``, which
    is the comparison the gates already make against the one golden today,
    so the gate's meaning does not change when the collection does.  A
    ``frozenset`` would silently swap that for hash-then-equality, and the
    day any field of a bag stops being hashable the gate would start raising
    instead of refusing.  Ordered by ``class_catalog.CLASS_IDS`` so the
    sequence is stable across runs, machines and Python versions.

    Element 0 is the committed ``INITIAL_BACKPACK`` OBJECT itself, not a copy
    of it, so an old character's untouched bag is admitted by the same
    identity it always was.  That is the whole reason COO chose the set over
    a per-class golden: every character alive today carries class 1's bag,
    and a per-class rule would have locked four classes out of the world
    until a migration exists.
    """
    return tuple(
        starting_backpack_state(class_id)
        for class_id in class_catalog.CLASS_IDS
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


def production_importers(root=None) -> tuple[str, ...]:
    """Which shipped modules import this one, by dotted name, at run time.

    Names, not just a number, because ``COO-DECISION 20260908_1246`` moved
    this lane's pin from "nobody imports me" to "at most ONE module imports
    me and it is ``inventory``".  A count alone cannot tell those two apart:
    one importer named ``store`` and one named ``inventory`` are both ``1``.

    DOTTED, not the file's stem (pf-adversary D4 of round ``wz0brc``): a
    stem collapses ``lane_hooks/inventory.py`` -- which is NOT the module
    COO named, and which this package's own ``lane_hooks._discover()``
    imports dynamically -- onto the allowed name ``inventory``.  Measured:
    with a stem, that intruder read as ``('inventory',)``, count 1, and
    every "the pin still bites a second importer" assertion passed.

    THE SAME ROOTS THE TEST WALKS (pf-adversary D5): the package plus
    ``tools`` ``migrations`` ``scenarios`` ``current``.  It used to be the
    package alone, so a real importer under ``tools/`` printed
    ``wired_callers=0 wired_by=NONE`` on the operator's console -- the same
    "a number that can only be what it already is" shape D3 of an earlier
    round was raised to end.

    Sorted and de-duplicated per module, so a module that imports this one
    on two lines is one importer, and the order does not depend on the
    filesystem.
    """
    import ast
    import pathlib
    import warnings

    here = pathlib.Path(__file__).resolve()
    if root is None:
        repo = here.parents[2]
        bases = [here.parent] + [
            repo / name
            for name in ("tools", "migrations", "scenarios", "current")
        ]
    else:
        bases = [pathlib.Path(root)]
    names = set()
    for base in bases:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            # No self-skip.  There used to be one, justified by a staging
            # strategy this file no longer uses, and pf-adversary (D7)
            # measured it as dead code: deleting it, and inverting it,
            # both left every test green.  This module does not import
            # itself, so the walk reaching it changes nothing -- and an
            # untestable line that looks load-bearing is worse than none.
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            try:
                # BYTES, not decoded text (pf-adversary D6): `ast.parse`
                # honours a PEP 263 coding cookie, so a module declaring
                # `latin-1` and carrying one high byte is parsed instead of
                # being dropped by a `UnicodeDecodeError` nothing counts.
                # Measured: such a module imported fine, really called this
                # one, and read as zero importers.
                with warnings.catch_warnings():
                    # Parsing somebody else's file must not report THEIR
                    # deprecated escape sequences as this scan's warnings.
                    warnings.simplefilter("ignore")
                    tree = ast.parse(raw)
            except SyntaxError:
                # Not `except Exception` and not silent-by-design: a file
                # that is not Python at all is not an importer, and every
                # other failure mode should reach the operator rather than
                # be swallowed into a zero.
                continue
            if _imports_this_module(tree):
                names.add(_dotted_name(path, base))
    return tuple(sorted(names))


def _dotted_name(path, base) -> str:
    """`base/lane_hooks/inventory.py` -> `lane_hooks.inventory`.

    Relative to the base it was found under, so the label a staged copy of
    the package produces is the same label the shipped package produces --
    the test and the console token are then comparing the same strings.
    """
    relative = path.relative_to(base).with_suffix("")
    return ".".join(relative.parts)


def _imports_this_module(tree) -> bool:
    """True when the parsed module imports this one, by any spelling."""
    import ast

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name.split(".")[-1] == _MODULE_NAME for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[-1] == _MODULE_NAME or any(
                a.name == _MODULE_NAME for a in node.names
            ):
                return True
        elif isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "attr", getattr(func, "id", ""))
            if name in ("import_module", "__import__"):
                for argument in node.args:
                    if (
                        isinstance(argument, ast.Constant)
                        and isinstance(argument.value, str)
                        and argument.value.split(".")[-1] == _MODULE_NAME
                    ):
                        return True
    return False


def count_production_importers(root=None) -> int:
    """How many shipped modules import this one, counted at run time.

    pf-adversary (D3) dropped a real importer into the package and the
    console token still printed ``wired_callers=0``, because the zero was
    inside the format string: a number that can only ever be the number it
    already is.  This walks the package's parsed modules instead, so the
    operator's console reports what is true of the tree it is running on.
    """
    return len(production_importers(root))


def main() -> int:
    for class_id in class_catalog.CLASS_IDS:
        print(describe(class_id))
    importers = production_importers()
    print(
        "CLASS_STARTING_GEAR_SUMMARY classes=%d wired_callers=%d wired_by=%s "
        "production_allowed=%s gate2_admits_non_class_1=NO"
        % (
            class_catalog.CLASS_COUNT,
            len(importers),
            ",".join(importers) if importers else "NONE",
            production_allowed,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - console entry
    raise SystemExit(main())
