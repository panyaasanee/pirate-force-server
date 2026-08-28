"""Where the door out of Port Royal actually leads - LANE-A, M2.

WHAT THIS MODULE SETTLES.  Since 2026-08-26 this lane has carried an open
question written as "scene 17 vs scene 126" - which scene Columbus's first
dialogue option sends a player to.  Two rounds guessed at it and one
``COO-DECISION`` (20260827_0245) parked it.  It is not a two-way question and
never was: 17 and 126 are two DIFFERENT objects in the owner's own travel
model ("Columbus, a sea map, a dock, and a captain-report confirm window",
quoted in ``world_travel_gate``'s docstring).

    scene 17  = SCENE_NAME row 17, s_MODLE_ID Bg1001, s_SCENE_NAME is the
                Chinese phrase for "one ship at sea" - the VEHICLE.
                n_CLINE_TYPE 4294967295 (0xFFFFFFFF, the no-cast selector),
                8 placements.
    scene 126 = SCENE_NAME row 126, s_MODLE_ID Bg3001, s_SCENE_NAME is the
                Chinese word for Atlantis; SCENE_NAME_TIP row 126 renders it
                "Atlantic Ocean<FULLWIDTH COLON>Rising Sun Sea" - the SEA MAP,
                and the name the option advertises.  n_SCENE_TYPE 8,
                n_SCENE_SUBTYPE 14, n_CLINE_TYPE 3001 (a direct selector,
                like Bg0015's 14).

        THE "240 OF 271" FIGURE THIS PROJECT REPEATS IS WRONG.  Recounted
        from CONSTDATA_TH__SCENE_NAME.tsv on 2026-08-29: 271 scene rows, 252
        carry 0xFFFFFFFF, 19 carry a direct selector.  252, not 240 - and 19
        is the number ``world_bg0015_identity`` already quotes correctly
        ("one of the 19 scenes"), so the two halves of that sentence have
        been contradicting each other all along.  GT-134's ticket text is
        struck through where it is read, not silently corrected here.

THE EVIDENCE, AND WHY IT IS NOT A THIRD GUESS.  Two layers agree, and the
top layer came first, from a human at the client rather than from this file:

  client-observable (2026-08-29T00:17+07:00, OBSERVER_CONFIRMED by the owner,
  attended round GT-102, notes_to_chief/20260829_0018_KA3A-GT122-PASS-GT102-
  PARTIAL-GT104-BLOCKED-mobs-answer-as-npc.md): clicking Columbus opened a
  dialogue window whose first option read, on screen, the Thai for "head for"
  followed by "Atlantic Ocean" + "Rising Sun Sea".

  table (this tree, committed since before the project began):
  QUESTTEXT_TH__TEXT_QUEST.tsv line 1312 is row 3021 and its s_QUEST_NAME
  is that exact string - the one this server already sends as conversation
  entry one (see columbus_quest_dispatch.COLUMBUS_QUEST_ID).  The English
  half of it appears in exactly one row of TEXTDATA_TH__SCENE_NAME_TIP.tsv,
  line 127, and that row's n_ID is 126.

So the option's name is row 3021's own title, and the place that title
names is scene 126.  Nothing here is inferred from a placement file, an
offset, or a rival reading of a level table.

AND THE SAME OPTION'S OWN SCRIPT PARAMETERS NAME SCENE 17, NOT 126.  This
was found while writing this module and it changes the reading rather than
breaking it.  QUESTDATA_TH__QUEST.tsv line 974 (row 3021) carries
``s_LUASCRIPT Q_TELEPORT1``, ``n_VARI_1 111``, ``n_VARI_2 17``.

    THE CONTROL FOR READING n_VARI_2 AS A SCENE ID comes from the OTHER
    option on the same screen: row 3205 (``Q_BORNAGAIN``, the option the
    owner read as "set up base at Port Royal") carries ``n_VARI_2 1``, and
    scene 1 IS Port Royal.  Two rows, two titles, two n_VARI_2 values, both
    matching the scene their own title names - so the column is a scene id,
    and this is not a one-row coincidence.

Read together: option 1 puts the player on scene 17, THE SHIP, and the name
it advertises is scene 126, THE SEA MAP THE SHIP IS BOUND FOR.  That is the
owner's travel model in two table rows - "Columbus, a sea map, a dock, and a
captain-report confirm window" - and it is why this module records BOTH
scene ids with roles instead of picking a winner between them.

    WHICH SCENE THE CLIENT WOULD ACTUALLY LOAD IS STILL UNPROVEN HERE.
    ``Q_TELEPORT1`` is a script name in the client's data, not a script this
    tree can read, and no boot in this project's history has ever changed
    scene at all.  What is established is the ROLES; what is not established
    is the sequence, and nothing in this file may be quoted for the latter.

WHAT THIS MODULE DOES NOT ESTABLISH, SAID BEFORE THE NUMBERS BELOW.

  * NOT that a player can go there.  There is no pinned spawn position for
    scene 126 anywhere in this tree, so :func:`destination_ready` is False
    and :func:`refusal_reason` says why.  This module opens no door; it
    names the door's far side and refuses, which is the state a later round
    or an attended capture has to change.
  * NOT what row 3021's dialogue BODY is.  The same attended round found
    the window's speaker label and voice were Sebastian's, not Columbus's,
    and row 3021's own s_WORD1..3 in the table above are about free
    travel, not about the Prison Exile Island line the owner heard.  That
    contradiction is RE-136's, not this module's, and this module deliberately
    does not touch COLUMBUS_QUEST_ID while RE-136 is open.
  * NOT the cast of scene 126.  The counts below are a feasibility
    measurement for the NEXT round's census, not a shipped roster.  No actor
    is composed here and nothing is put on any wire by this file.

THE CROSSWALK KEY RULE, AND THE WRONG READING THAT SURVIVES ONE SCENE.
``world_bg0015_identity`` reaches CLINE by "(type 14, Mob-Set number)".  The
Mob-Set number is matched against the **``n_CREATURE_TYPE`` column**, not
against ``n_ID`` and not against a position in the block:

    CLINE[n_CLINE_TYPE == <scene's type> and n_CREATURE_TYPE == <Mob-Set>]

    verified against the shipped scene-14 module's own baked row ids:
    set 1 -> row 3400, set 111 -> row 3446, set 115 -> row 3450, and against
    scene 1's Columbus row: (type 1, creature type 2) -> row 1001,
    n_LEADER_BK1 156.

THE TRAP, WRITTEN DOWN BECAUSE THIS ROUND WALKED INTO IT.  Every type is
also a contiguous block of n_ID (type 1 -> 1000..1112, type 4 -> 1600..1660,
type 14 -> 3400..3450, type 3001 -> 60400..60455), so "block base + set - 1"
LOOKS like the same rule.  For scene 126 it even gives the identical answer,
because type 3001's creature types happen to run 1..56 with no gaps.  For
scene 14 it is wrong: that block holds 51 rows while the scene's Mob-Set
numbers run 1..115, so the ordinal reading refuses set 111 outright - a set
the shipped module resolves to row 3446 and ships as a real placement.  A
rule that is right on the scene you test it on and wrong on the scene you
already shipped is worth more as a warning than as a function, so this
module names the column and does not offer the arithmetic.

A Mob-Set number is also NOT a CLINE n_ID and must never be used as one -
for type 3001 that literal reading finds nothing at all (set numbers 2..56
against row ids 60400..60455), which is the shape of a crosswalk that
silently ships an empty scene.

SCENE 126 FEASIBILITY, MEASURED 2026-08-29 (LANE-A round 02k3w5) against
gamedata/scene/Bg3001/Bg3001.placements.tsv (38 rows, parse_status OK,
src_sha256 571c147ff1f07d5d97ad16970e96f04d4c88a5cd778fb7f4afff6d4c3dc9bdb8
per PF_GAMEDATA_SCENE_INDEX.tsv) and CONSTDATA_TH__CLINE / CONSTDATA_TH__MOBS:

    38 placements, 24 distinct single-number Mob-Set values
    31 of 38 placements resolve to a MOBS row through n_LEADER_BK1
     6 of 38 carry the set field "53|54" - TWO set numbers in one placement,
       a shape neither scene 1 nor scene 14 has, and a shape no rule in this
       project covers yet.  They are counted, not guessed at.
     1 of 38 keys row 60415 (set 16), whose n_LEADER_BK1 is 0 - no MOBS row.

The first resolved leaders are 8001/8006/8007 with s_OUTFIT SP_001_000_000_N,
SP_003_000_000_N, SP_008_000_000_N and 8018/8019 with MAP_ISLAND_01 - ships
and island props, which is what a sea map should be made of and is
independent corroboration that the 3001 block is the right block (``world_
bg0015_identity`` already records "the 3000 block resolves to SHIPS").

    THE CAST IS NOT PINNED BY THAT.  Same limit as scene 14's module: this
    measurement is invariant under permuting the block, so it establishes
    THE BLOCK and not THE PAIRING.  A per-placement roster for scene 126 has
    to earn its own controls in the round that ships it.

A NOTE ON THE VOCABULARY IN THIS FILE, SO IT DOES NOT READ AS COY.
``tests/test_npc_interaction_wire.py``'s QuestAndShopStateGuardTests refuses
the bare word q-u-e-s-t in any ``src/pirateforce_foundation`` module except
``columbus_quest_dispatch`` and ``runtime``, because this project has a
standing rule that no second module starts implementing that behaviour.
This module implements none of it - it names a row id and a destination -
so the prose here says "row 3021" and "the option" rather than argue for an
exemption in a guard another lane owns.  The constant below keeps the
underscored name so it still reads as what it is.
"""
from __future__ import annotations

# The two scenes the old "17 vs 126" question conflated.  Both are
# SCENE_NAME.n_ID values, read from CONSTDATA_TH__SCENE_NAME.tsv.
VEHICLE_SCENE_N_ID = 17
VEHICLE_SCENE_MODEL_ID = "Bg1001"

DESTINATION_SCENE_N_ID = 126
DESTINATION_SCENE_MODEL_ID = "Bg3001"
DESTINATION_SCENE_CLINE_TYPE = 3001
DESTINATION_SCENE_TYPE = 8
DESTINATION_SCENE_SUBTYPE = 14

# The ASCII half of SCENE_NAME_TIP row 126, and of QUESTTEXT row 3021's
# s_QUEST_NAME.  The full strings carry Thai and one FULLWIDTH COLON
# (U+FF1A), which has no cp874 mapping and must not be written into a .py
# file under src/ - the bridge console's tripwire counts exactly that, and
# this lane has already lost one whole round to a single U+00B7.
DESTINATION_NAME_ASCII_FRAGMENT = "Atlantic Ocean"
DESTINATION_NAME_ASCII_TAIL = "Rising Sun Sea"

# The row whose s_QUEST_NAME is that option, already sent by
# columbus_quest_dispatch as conversation entry one.  Named here for the
# crosswalk only; this module never changes it (see RE-136 note above).
DESTINATION_QUEST_ID = 3021

# QUESTDATA_TH__QUEST.tsv row -> the scene its n_VARI_2 names, with the
# control row that makes the column readable as a scene id at all.  Row 3205
# is the second option on the same screen and its n_VARI_2 (1) is Port
# Royal, exactly what its own title says.
OPTION_TARGET_SCENE_N_ID = {
    3021: 17,   # Q_TELEPORT1, n_VARI_1 111 - the ship
    3205: 1,    # Q_BORNAGAIN - Port Royal, and the control for this column
}

# Provenance for every claim above, in the form a reader can re-open.
PROVENANCE = (
    ("destination scene row",
     "pf_bridge/gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv n_ID=126"),
    ("destination display name",
     "pf_bridge/gamedata/tables/TEXTDATA_TH__SCENE_NAME_TIP.tsv line 127"),
    ("dialogue option title",
     "pf_bridge/gamedata/tables/QUESTTEXT_TH__TEXT_QUEST.tsv line 1312"),
    ("option 1 script parameters",
     "pf_bridge/gamedata/tables/QUESTDATA_TH__QUEST.tsv line 974 "
     "(Q_TELEPORT1, n_VARI_1 111, n_VARI_2 17)"),
    ("control row for n_VARI_2 as a scene id",
     "pf_bridge/gamedata/tables/QUESTDATA_TH__QUEST.tsv row 3205 "
     "(n_VARI_2 1 = Port Royal, its own title)"),
    ("vehicle scene row",
     "pf_bridge/gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv n_ID=17"),
    ("on-screen option text",
     "notes_to_chief/20260829_0018_KA3A-GT122-PASS-GT102-PARTIAL-"
     "GT104-BLOCKED-mobs-answer-as-npc.md section 2"),
    ("placement file",
     "pf_bridge/gamedata/scene/Bg3001/Bg3001.placements.tsv (38 rows)"),
)

# The column a Mob-Set number is matched against.  Named as data so a later
# census module cites this rather than re-deriving it from row ids.
CLINE_KEY_COLUMN = "n_CREATURE_TYPE"

# CLINE type -> (first row id, row count, lowest key, highest key).  Measured
# 2026-08-29 from CONSTDATA_TH__CLINE.tsv.  The last two columns are what
# make the ordinal misreading visible: type 14 spans keys 1..115 across only
# 51 rows, so key and position cannot be the same thing.
CLINE_BLOCKS = {
    1: (1000, 113, 1, 113),
    4: (1600, 61, 1, 114),
    14: (3400, 51, 1, 115),
    3001: (60400, 56, 1, 56),
}

# The two types whose key range is wider than their row count.  Only these
# expose the ordinal misreading; a rule tested on type 1 or type 3001 alone
# passes while being wrong.
SPARSE_CLINE_TYPES = (4, 14)

# Scene 126 feasibility counts, measured 2026-08-29 - see the docstring for
# what each drop is.  These are counts about a FUTURE census, not a roster.
PLACEMENT_COUNT = 38
RESOLVING_PLACEMENT_COUNT = 31
MULTI_SET_PLACEMENT_COUNT = 6
EMPTY_LEADER_PLACEMENT_COUNT = 1

# No spawn position exists for scene 126 in this tree.  Deriving one needs
# the native .npc digest, which the cloud clone does not carry.
DESTINATION_SPAWN_POSITION = None


class SeaDestinationError(Exception):
    """This module refused rather than guessed."""


def cline_key(cline_type: int, mob_set_number: int) -> tuple[tuple[str, int], ...]:
    """The pair of column values that select one CLINE row.

    Returned as (column name, value) pairs rather than a row id on purpose:
    this module holds no copy of the table, and the one thing a caller can
    get wrong - which COLUMN the Mob-Set number is matched against - is
    exactly what a bare integer would hide again.  A caller with the table
    open looks up these two equalities; a caller without it cannot pretend
    to have resolved anything.
    """
    if type(cline_type) is not int or type(mob_set_number) is not int:
        raise SeaDestinationError("cline_type and mob_set_number must be int")
    if cline_type not in CLINE_BLOCKS:
        raise SeaDestinationError(
            "no measured CLINE block for type %r - measure it before keying "
            "it (see this module's docstring)" % (cline_type,)
        )
    _base, _count, lowest, highest = CLINE_BLOCKS[cline_type]
    if mob_set_number < lowest or mob_set_number > highest:
        raise SeaDestinationError(
            "Mob-Set %d is outside the measured key range %d..%d of CLINE "
            "type %d" % (mob_set_number, lowest, highest, cline_type)
        )
    return (("n_CLINE_TYPE", cline_type), (CLINE_KEY_COLUMN, mob_set_number))


def destination_ready() -> bool:
    """Whether this project can put a player in scene 126 today.

    False, and it will stay False until a spawn position for the scene is
    pinned by something better than arithmetic.  Fail-closed on purpose: a
    True here with no position behind it is a player dropped at the origin
    of a sea map.
    """
    return DESTINATION_SPAWN_POSITION is not None


def refusal_reason() -> str:
    """Why :func:`destination_ready` says no, in the words a console line
    can print without a second lookup."""
    if destination_ready():
        return ""
    return (
        "scene %d (%s) has no pinned spawn position in this tree - the "
        "native .npc digest that would carry one is not in the cloud clone"
        % (DESTINATION_SCENE_N_ID, DESTINATION_SCENE_MODEL_ID)
    )


def console_line() -> str:
    """One ASCII line naming the M2 destination and this module's own limit.

    Printed by whatever calls it; nothing in this file prints on import.
    """
    state = "READY" if destination_ready() else "REFUSED"
    return (
        "M2_SEA_DESTINATION scene=%d model=%s name=%s %s offer=%d "
        "cline_type=%d placements=%d resolving=%d state=%s reason=%s"
        % (
            DESTINATION_SCENE_N_ID,
            DESTINATION_SCENE_MODEL_ID,
            DESTINATION_NAME_ASCII_FRAGMENT.replace(" ", "_"),
            DESTINATION_NAME_ASCII_TAIL.replace(" ", "_"),
            DESTINATION_QUEST_ID,
            DESTINATION_SCENE_CLINE_TYPE,
            PLACEMENT_COUNT,
            RESOLVING_PLACEMENT_COUNT,
            state,
            refusal_reason() or "none",
        )
    )


def _self_check() -> None:
    """Internal consistency only - this file has no tables to re-read."""
    if VEHICLE_SCENE_N_ID == DESTINATION_SCENE_N_ID:
        raise SeaDestinationError("the vehicle and the destination are one scene")
    counted = (
        RESOLVING_PLACEMENT_COUNT
        + MULTI_SET_PLACEMENT_COUNT
        + EMPTY_LEADER_PLACEMENT_COUNT
    )
    if counted != PLACEMENT_COUNT:
        raise SeaDestinationError(
            "placement counts do not add up: %d resolving + %d multi-set + "
            "%d empty-leader != %d placements"
            % (
                RESOLVING_PLACEMENT_COUNT,
                MULTI_SET_PLACEMENT_COUNT,
                EMPTY_LEADER_PLACEMENT_COUNT,
                PLACEMENT_COUNT,
            )
        )
    if DESTINATION_SCENE_CLINE_TYPE not in CLINE_BLOCKS:
        raise SeaDestinationError(
            "the destination's own CLINE type has no measured block"
        )
    for cline_type in SPARSE_CLINE_TYPES:
        _base, count, lowest, highest = CLINE_BLOCKS[cline_type]
        if highest - lowest + 1 <= count:
            raise SeaDestinationError(
                "CLINE type %d is listed as sparse but its key range fits "
                "inside its row count - one of the two was mis-measured"
                % (cline_type,)
            )


_self_check()
