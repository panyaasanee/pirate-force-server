"""The class-weapon door: which weapon template a character's bag SHOULD
carry, derived from the shipped client table rather than typed here.

WHOSE ORDER THIS IS.  ``pf_bridge/notes_to_chief/20260908_0025_KA1A-PANYA-
TICK-*.md`` item 4, ticked by the owner in the words "(a) write a migration
and back the DB up": the five classes are born holding their own weapon
(LANE-CS, at the character-creation site), and the characters that ALREADY
exist in the canonical database get their weapon row corrected by this lane.
Three conditions came with the tick and all three are load-bearing here:

  1. run on a COPY first, print before/after per character, and NEVER delete
     an item -- a wrong-class weapon is MOVED into the bag, not dropped;
  2. the canonical database is touched only while ka1-A holds ``LOCK_GAME``
     in an attended session, snapshot taken and sha256 announced first;
  3. every character the run touched must log in once afterwards and reach
     the map -- one that cannot means restoring the whole snapshot.

WHY THE NUMBERS ARE NOT TYPED IN THIS FILE.  ``COO-DECISION 20260901_1059``
forbids a guessed field, and LANE-CS's row-provenance letter
(``notes_to_chief/20260908_0151_LANE-CS-TO-DB-class-to-weapon-mapping-with-
row-provenance-for-migration.md``) says explicitly: do not copy the ids,
read the column.  So the mapping below is parsed out of
``data/charcreate_class.tsv`` column ``n_SLOT_RHAND`` at import, and
``class_catalog`` is imported FIRST so that its sha256 pin on that same file
has already run: if the table drifts from the pinned client source, this
module never loads instead of quietly answering with stale ids.

WHY ``n_SLOT_LHAND`` IS NOT READ.  LANE-CS's letter measured it: two classes
carry ``0`` there and Gladiator repeats its right hand, so no rule in the
table says whether a left hand belongs in the bag at all.  The committed
starting bag has exactly one weapon row; inventing a second would change
every ``BackpackAttr`` size this project has measured.  Reading a column we
cannot interpret would be the guess ``1059`` forbids, so this door reads one
column and says so.
"""

from __future__ import annotations

import csv
from dataclasses import replace

from . import class_catalog
from .inventory import (
    INITIAL_BACKPACK as INITIAL_BACKPACK_FOR_PROBE,
    BackpackState,
    ItemAttrState,
)


class ClassWeaponError(RuntimeError):
    """This module refused rather than answer with a guess."""


#: The column LANE-CS's letter proved is the class's weapon, and the only
#: one this module reads.
RHAND_COLUMN = "n_SLOT_RHAND"

#: The letter this mapping's provenance comes from, quoted where a reader
#: would otherwise have to take the numbers on trust.
PROVENANCE_LETTER = (
    "notes_to_chief/20260908_0151_LANE-CS-TO-DB-class-to-weapon-mapping-"
    "with-row-provenance-for-migration.md"
)


def _load_weapon_templates() -> dict[int, int]:
    # class_catalog has already read and sha256-checked this exact file at
    # its own import (above), so a mismatch has raised before we get here.
    path = class_catalog._DATA_PATH
    with path.open("r", encoding="ascii", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    mapping: dict[int, int] = {}
    for row in rows:
        template = int(row[RHAND_COLUMN])
        if template <= 0:
            # Not reachable for the right hand in the shipped table, and if
            # it ever is, "no weapon" is a thing this door must not invent a
            # zero-template row for.
            raise ClassWeaponError(
                "class %s has no %s in %s"
                % (row["n_ID"], RHAND_COLUMN, path.name))
        mapping[int(row["n_ID"])] = template
    return mapping


#: ``class_id -> the template id of that class's right-hand weapon``.
CLASS_ID_TO_WEAPON_TEMPLATE: dict[int, int] = _load_weapon_templates()


def class_weapon_template_id(class_id: int) -> int:
    """The weapon template this class is born holding.

    Raises for a class id the shipped table does not have a row for, rather
    than falling back to the Gladiator blade every character carries today:
    a character whose class the table cannot name is exactly the row a
    migration must leave alone and report, not repair.
    """
    try:
        return CLASS_ID_TO_WEAPON_TEMPLATE[int(class_id)]
    except (KeyError, TypeError, ValueError):
        raise ClassWeaponError(
            "no %s row for class_id %r" % (RHAND_COLUMN, class_id)) from None



def _slot_ceiling() -> int:
    """The highest slot ``inventory.require_backpack_shape`` accepts, found
    by asking it rather than by typing 39 here.

    A hand-typed ceiling is a fourth copy of a bound this repository already
    holds, and pf-adversary's `D7` was exactly that mistake in the other
    direction: the first draft used 65535, so its "no free slot" refusal was
    a line that could never run and a full bag came back `malformed`.
    """
    from .inventory import require_backpack_shape

    ceiling = 0
    probe = replace(
        INITIAL_BACKPACK_FOR_PROBE,
        items=(replace(INITIAL_BACKPACK_FOR_PROBE.items[0], slot=0),),
    )
    for slot in range(0, 0x10000):
        try:
            require_backpack_shape(replace(
                probe, items=(replace(probe.items[0], slot=slot),)))
        except Exception:
            break
        ceiling = slot
    return ceiling


def weapon_row(bag: BackpackState) -> ItemAttrState:
    """The single row in ``bag`` that holds a class weapon.

    DERIVED, NOT ADDRESSED BY NUMBER.  ``migrations/003`` seeds the weapon at
    identity 4 / slot 3, and every character alive today matches that -- but
    a migration that hunts for "identity 4" would happily rewrite a potion
    the day a bag is seeded differently.  What makes a row the weapon row is
    that its template is one of the five the class table calls a weapon, so
    that is what is asked.  Raises unless exactly one row qualifies: zero
    means this bag has no weapon to correct, and two means the assumption
    the owner's order rests on ("the bag holds one weapon row") is false for
    this character and a human has to look.
    """
    templates = set(CLASS_ID_TO_WEAPON_TEMPLATE.values())
    weapons = tuple(item for item in bag.items if item.template_id in templates)
    if len(weapons) == 1:
        return weapons[0]
    if not weapons:
        raise ClassWeaponError("expected exactly one weapon row, found 0")
    # MORE THAN ONE, AND THAT IS NOT A CORRUPT BAG.  pf-adversary measured it:
    # `mob_loot.IDS_ON_THE_WIRE_GT045_V3` has 2200003 -- the Paladin's class
    # weapon -- as a template this project has watched drop on the ground four
    # separate rounds.  A character who picked one up holds two rows this rule
    # calls weapons, and refusing there would silently skip exactly the
    # players who have been playing (a skip nobody sees, `D5`).  The row the
    # owner's order is about is the one the character was BORN with, so the
    # anchor is the born bag's own weapon row -- its identity AND its slot,
    # both, since either alone is reachable by a pickup.
    from .inventory import INITIAL_BACKPACK

    born = next(
        item for item in INITIAL_BACKPACK.items if item.template_id in templates
    )
    anchored = tuple(
        item for item in weapons
        if item.identity == born.identity and item.slot == born.slot
    )
    if len(anchored) != 1:
        raise ClassWeaponError(
            "found %d weapon rows and %d of them sit where the bag was born "
            "holding one" % (len(weapons), len(anchored)))
    return anchored[0]


def retarget_weapon_row(bag: BackpackState, class_id: int) -> BackpackState:
    """``bag`` with its weapon row's template changed to this class's.

    This is the end state LANE-CS's ``starting_backpack_states()`` describes
    -- four rows, the weapon one swapped -- and it is NOT the end state the
    owner's condition 1 asks for, because it drops the old template.  It is
    here because it is the shape the golden set is being widened to, and the
    migration's own end state has to be compared against it.
    """
    target = class_weapon_template_id(class_id)
    current = weapon_row(bag)
    return replace(bag, items=tuple(
        replace(item, template_id=target) if item.identity == current.identity
        else item
        for item in bag.items
    ))


def carry_old_weapon_forward(
    bag: BackpackState, class_id: int, issued_through: int,
) -> tuple[BackpackState, int]:
    """The owner's condition 1, as a value: the class weapon takes the weapon
    row, and the template that was there is kept as a NEW bag row.

    Returns ``(post_state, new_issued_through)``.  The old weapon is given
    the next identity the character has never been issued -- not a recycled
    one -- because the identity counter is what
    the gate-2 admission module reads to tell an item the server handed over
    from one a client invented.

    Refuses when the class weapon is already in place (nothing to carry
    forward, and a second identical row is not what "do not delete" means)
    and when the bag has no free slot below the shape gate's ceiling.
    """
    target = class_weapon_template_id(class_id)
    current = weapon_row(bag)
    if current.template_id == target:
        raise ClassWeaponError(
            "class %d already holds template %d" % (int(class_id), target))
    used = {item.slot for item in bag.items}
    # The ceiling is the shape gate's, read from the shape gate, not a 65535
    # that no loadable bag can reach: pf-adversary measured the old bound
    # handing out slot 40 for a full bag, which `require_backpack_shape`
    # refuses -- a full bag came back "malformed" instead of "no free slot",
    # and the named refusal below was a line that could never run.
    free = next(
        (slot for slot in range(0, _slot_ceiling() + 1) if slot not in used),
        None)
    if free is None:
        raise ClassWeaponError("no free slot to carry the old weapon into")
    carried = ItemAttrState(
        identity=issued_through + 1,
        template_id=current.template_id,
        quantity=current.quantity,
        slot=free,
        raw_u8_38=current.raw_u8_38,
        raw_u8_39=current.raw_u8_39,
        detail_present=current.detail_present,
    )
    swapped = retarget_weapon_row(bag, class_id)
    return replace(swapped, items=swapped.items + (carried,)), issued_through + 1


def admission_blockers(
    bag: BackpackState, class_id: int, issued_through: int,
) -> tuple[str, ...]:
    """Every reason, measured against the code as it stands right now, why a
    character whose bag became the owner's post-state would be worse off --
    empty tuple when there is none.

    TWO THINGS THIS FUNCTION IS NOT, BOTH OF THEM MEASURED THIS ROUND.

    It is not a reading of ``runtime.py``.  The first draft blamed that
    module's committed-merge comparison, and pf-adversary showed the
    comparison CANNOT FIRE for any bag this migration produces, because
    ``store.apply_v111_stack_merge`` refuses a bag outside the starting set
    one step earlier and the caller swallows that refusal.  The door below is
    that one, asked by asking it.

    It does not consult the gate-2 admission module.  It did, and the full
    suite caught it: that module's wiring test pins the set of modules
    in this package that may import that module AT ALL to ``session.py``
    alone, and NOW.md ``2050`` gives a caller that trips a cross-lane pin one
    move -- withdraw and let the pin's owner decide.  So the gate-2 finding
    of this round (a retargeted bag classifies ``refused``, measured with the
    shipped classifier) lives in the round file and in
    ``notes_to_chief/20260908_0602_LANE-DB-ASK-PIN-OWNERS-*``, and this
    function reports only what it can ask without saying that module's name.
    Membership in the starting set is a NECESSARY condition for the golden
    verdict either way, so an empty tuple here is not yet a green light: it
    is "the door this lane owns no longer refuses".
    """
    from . import inventory

    post, _new_issued = carry_old_weapon_forward(bag, class_id, issued_through)
    blockers: list[str] = []
    if inventory.starting_core_of(post) is None:
        # store.apply_v111_stack_merge's pre-state door.  It no longer asks
        # ``post in STARTING_BACKPACKS`` -- the extra row this migration adds
        # would have failed that forever, which was the blocker this function
        # reported until COO-DECISION 20260908_0542 section 4 -- it asks
        # whether the bag still CARRIES a starting bag's own rows.  The
        # carried-forward bag does not, because retargeting the weapon row is
        # exactly the change the core check refuses, and the class's own bag
        # is not in the set: ``STARTING_BACKPACKS`` still holds one member.
        # So the blocker stands, with a different sentence and a different
        # remedy -- widen the SET, not the door.  It clears itself the day
        # ``inventory.STARTING_BACKPACKS`` holds LANE-CS's five, with no edit
        # here, which is why the condition is asked rather than spelled.
        blockers.append(
            "store.apply_v111_stack_merge refuses a post-state bag whose "
            "core is outside inventory.STARTING_BACKPACKS (%d member(s) "
            "today): the character loses the V111 stack merge with no reply "
            "to the client" % len(inventory.STARTING_BACKPACKS))
    return tuple(blockers)


def newly_created_character_merge_warning() -> str | None:
    """The ``runtime.py`` hazard, stated about the population it can actually
    reach -- which is NOT this migration's.

    Once LANE-CS's ``#1091`` widens the starting set, a character BORN in a
    class other than the first merges successfully, commits, and only then
    meets ``runtime.py``'s comparison against the single imported constant,
    which raises after the write.  That is CORE-REQUEST ``20260908_0206``, it
    is real, and it is urgent for new characters; it is not what blocks the
    owner's item 4.  Returns ``None`` when no starting bag can reach it.
    """
    from . import inventory

    for starting in inventory.STARTING_BACKPACKS:
        if not inventory.can_merge_v111(starting):
            continue
        if inventory.merged_v111_state(starting) != inventory.MERGED_V111_BACKPACK:
            return (
                "runtime.py compares the committed V111 merge state against "
                "the single MERGED_V111_BACKPACK it imported and raises AFTER "
                "the commit; a character born in this class reaches that "
                "(CORE-REQUEST 20260908_0206)")
    return None


# ---------------------------------------------------------------------------
# The READ-ONLY census (COO-DECISION 20260908_0542 section 4).
#
# PANYA's item 4 (letter 20260908_0025) says an attended run under LOCK_GAME
# corrects the weapon row of every character that already exists.  Nobody can
# size that job from a cloud clone: the canonical database is on the owner's
# machine and this repository has never held a copy.  These two functions are
# the half that can be answered without the machine and without writing
# anything -- how many characters exist, in which classes, and how many of
# them hold a weapon their class would not be given.  The connection is
# opened ``mode=ro`` through a file: URI, so the process CANNOT write even if
# a later edit here asked it to; that is the whole reason the census is a
# separate entry point from the migration.
# ---------------------------------------------------------------------------

#: The identity the born bag puts the weapon on, DERIVED from the committed
#: bag rather than typed as 4, for the reason ``weapon_row`` states at length.
def _born_weapon_identity() -> int:
    return weapon_row(INITIAL_BACKPACK_FOR_PROBE).identity


def census_rows(db) -> tuple[tuple[int, int, int, int, int], ...]:
    """``(class_id, characters, weapon_ok, weapon_wrong, weapon_missing)`` per class.

    ``db`` is any DB-API connection; the caller owns opening it read-only.
    A class with no entry in the weapon table counts every one of its
    characters as ``weapon_missing`` rather than raising, because a census
    that dies on the first surprising row tells an operator nothing about the
    other nine hundred.
    """
    identity = _born_weapon_identity()
    counts: dict[int, list[int]] = {}
    rows = db.execute(
        "SELECT c.class_id, i.template_id FROM characters AS c "
        "LEFT JOIN character_backpack_items AS i "
        "ON i.character_id = c.id AND i.item_identity = ? "
        "ORDER BY c.class_id, c.id",
        (identity,),
    ).fetchall()
    for class_id, template_id in rows:
        class_id = -1 if class_id is None else int(class_id)
        bucket = counts.setdefault(class_id, [0, 0, 0, 0])
        bucket[0] += 1
        expected = CLASS_ID_TO_WEAPON_TEMPLATE.get(class_id)
        if template_id is None or expected is None:
            bucket[3] += 1
        elif int(template_id) == expected:
            bucket[1] += 1
        else:
            bucket[2] += 1
    return tuple(
        (class_id, *counts[class_id]) for class_id in sorted(counts)
    )


def census_lines(db) -> list[str]:
    """The console tokens, ASCII only, one per class plus one summary."""
    rows = census_rows(db)
    lines = [
        "CLASS_WEAPON_CENSUS_CLASS class_id=%d name=%s characters=%d "
        "weapon_ok=%d weapon_wrong=%d weapon_missing=%d"
        % (
            class_id,
            class_catalog.class_name(class_id)
            if class_id in class_catalog.CLASS_IDS else "UNKNOWN",
            characters, ok, wrong, missing,
        )
        for class_id, characters, ok, wrong, missing in rows
    ]
    lines.append(
        "CLASS_WEAPON_CENSUS_SUMMARY classes=%d characters=%d "
        "rows_to_change=%d writes_performed=0 read_only=YES"
        % (
            len(rows),
            sum(row[1] for row in rows),
            sum(row[3] for row in rows),
        )
    )
    return lines


def census_main(argv=None) -> int:  # pragma: no cover - console entry
    import sqlite3
    import sys

    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 1:
        print("CLASS_WEAPON_CENSUS_ERROR usage=<state.sqlite3>")
        return 2
    uri = "file:%s?mode=ro" % args[0].replace("?", "%3f").replace("#", "%23")
    with sqlite3.connect(uri, uri=True) as db:
        for line in census_lines(db):
            print(line)
    return 0


if __name__ == "__main__":  # pragma: no cover - console entry
    raise SystemExit(census_main())
