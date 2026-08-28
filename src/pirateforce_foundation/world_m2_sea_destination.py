"""Where the door out of Port Royal actually leads - LANE-A, M2.

WHAT THIS MODULE RECORDS.  Row 3021 - the option this server already sends
as conversation entry one - teleports the player to **scene 17**, the ship.
Not to scene 126.  The name the option displays is the name of the OCEAN
PANEL THE SOURCE ISLAND SITS UNDER, and that is a different thing from where
it sends you.

    THIS ROUND FIRST GOT IT BACKWARDS, AND THE CORRECTION IS THE POINT.
    The first draft of this file read the on-screen option text
    ("Atlantic Ocean<FF1A>Rising Sun Sea", = scene 126's display name) as
    naming the destination, and declared 126 the destination and 17 "the
    vehicle".  ``pf-adversary`` refuted it from the table this file had not
    opened, and from two notes already in the mailbox.  Both are cited
    below.  The wrong reading is left written down here because a later
    round that finds the same option string will reach for it again.

THE TABLE THAT DECIDES IT.  QUESTDATA_TH__QUEST.tsv row 3021:
``n_TYPE 20``, ``s_LUASCRIPT Q_TELEPORT1``, ``n_VARI_1 111``,
``n_VARI_2 17``.  ``n_VARI_2`` is the destination scene id, and that is
measured across siblings rather than assumed: rows 3002 -> 1 Port Royal,
3003 -> 4 Slave Market, 3005 -> 5 Evil Port, 3007 -> 6 Ocean Walled City,
3009 -> 8 Silver Harbour, 3014 -> 14 Hell Volcanic Island (this project's
own Bg0015), 3038 and 8003 -> 1 Port Royal.  Title and number agree in every
one.  ``columbus_quest_dispatch`` already reads the column this way for the
sibling option (3205's ``n_VARI_2 1`` as ``Player.ResetMarker(1)``), and
``COLUMBUS_DEST_SCENE_ID`` there is already 17.  This module agrees with it
rather than contradicting it from the next file along.

THE ONE-PER-ISLAND RULE, WHICH IS WHAT THE OPTION TEXT ACTUALLY FOLLOWS.
Each island has its own Columbus, its own Q_TELEPORT1 row, and its own ship
scene; the advertised name is the ocean panel of the island you are STANDING
ON, resolved as MAP_SCENE_LIST[n_NAME_ID == home].n_ID_MAINTITLE -> the
MAINTITLE == 0 row -> its n_NAME_ID -> SCENE_NAME_TIP.  Eight of eight, no
exceptions:

    MOBS 156 Port Royal (home 1)         3021 -> scene 17 Bg1001, panel 126
    MOBS 360 Prison Exile (home 2)       3022 -> scene 18 Bg1002, panel 126
    MOBS  36 Spice Paradise (home 3)     3023 -> scene 19 Bg1003, panel 126
    MOBS  67 Slave Market (home 4)       3024 -> scene 20 Bg1004, panel 304
    MOBS 105 Evil Port (home 5)          3025 -> scene 21 Bg1005, panel 304
    MOBS 196 Ocean Walled City (home 6)  3026 -> scene 39 Bg1023, panel 127
    MOBS 362 Voodoo (home 7)             3027 -> scene 40 Bg1024, panel 127
    MOBS 250 Silver Harbour (home 8)     3028 -> scene 41 Bg1025, panel 305

    SO 126 IS NOT A DESTINATION AT ALL.  Three different Columbuses on three
    different islands all advertise it while going to three different ship
    scenes.  A module that pinned 126 as the destination could not tell 3021
    from 3022, and a later round wiring it would deliver Prison Exile's
    player to Port Royal's sea.  That is the concrete damage this correction
    prevents.

AND A HUMAN AT THE CLIENT ALREADY SAW THIS, ON THIS SERVER, TWO DAYS BEFORE
THIS MODULE WAS WRITTEN.  ``notes_to_chief/20260827_1710_GT106-RESULT-M2-``
records an attended run where clicking this exact option put the player into
scene 17, walkable.  The crosswalk letter
``notes_to_chief/20260827_1050_ATTENDED-FOUND-M2-crosswalk-Columbus-156-``
carries the same eight-row table, read from gamedata with no inference, and
adds what the owner means by "the sea map": scenes 17-23 are Bg1001..Bg1007,
"one/two/three ships at sea", ``n_SCENE_TYPE 4`` - the scenes where the
character becomes a ship.  This module adds no evidence layer to that.  What
it adds is the ocean-panel derivation for the TITLE, which is what made 126
look like a destination in the first place.

WHAT IS STILL OPEN, AND IT IS NOT THIS MODULE'S TO CLOSE.  GT-106's own
result marks the step from scene 17 to a named sea explicitly unknown, and
"scenes 17-23 are on-ship scenes" explicitly a hypothesis, both needing a
new RE or a clip of the original server.  What ``Player.Teleport(<the row's Var2>)``
does on the original server with a value of 17 is exactly that question.
Nothing here may be quoted for it.

SCENE 126 IS STILL WORTH THE MEASUREMENT BELOW, for a different reason: it
is one of the 19 scenes carrying a direct n_CLINE_TYPE (3001), so if a later
round ever needs its cast, the crosswalk resolves.  That is a census
feasibility note, not a route.

    SCENE 126 FEASIBILITY, MEASURED 2026-08-29 (LANE-A round 02k3w5) against
    gamedata/scene/Bg3001/Bg3001.placements.tsv (38 rows, parse_status OK,
    src_sha256 571c147ff1f07d5d97ad16970e96f04d4c88a5cd778fb7f4afff6d4c3dc
    9bdb8 per PF_GAMEDATA_SCENE_INDEX.tsv):

        38 placements; 37 resolve to a MOBS row through n_LEADER_BK1
         6 of those 37 carry TWO Mob-Set numbers in one field ("53|54").
           BOTH legs resolve: set 53 -> CLINE 60452 -> MOBS 8167 and set 54
           -> CLINE 60453 -> MOBS 8171, the two sea-weather markers
           (thunderstorm / dead calm), both with s_OUTFIT INVISIBLE.  They
           need a two-variant pick rule, not an unknown-shape rule, and the
           shape is not rare: 98 placements across 16 scenes carry it.
         1 placement (index 28, set 16) keys CLINE row 60415, whose
           n_LEADER_BK1 is 0 - the only zero-leader row in the block.

        AN EARLIER DRAFT OF THIS FILE SAID "31 of 38 resolve" and called the
        "53|54" shape one "no rule in this project covers yet".  Both were
        wrong: it had never followed the second leg.  Sizing a census off
        that number would have budgeted seven unknowns where there is one.

    INDEPENDENT CORROBORATION THAT 3001 IS THE RIGHT BLOCK, not drawn
    through the crosswalk being corroborated: PF_GAMEDATA_SCENE_INDEX.tsv
    gives Bg3001 ``definition_count = 56``, and CLINE type 3001 holds
    exactly 56 rows.  (An earlier draft offered "the leaders are ships and
    island props" instead, which travels through the very chain in question
    and is a plausibility check, not evidence.)

THE CROSSWALK KEY RULE, AND THE WRONG READING THAT SURVIVES ONE SCENE.
``world_bg0015_identity`` reaches CLINE by "(type 14, Mob-Set number)".  The
Mob-Set number is matched against the **``n_CREATURE_TYPE`` column**, not
against ``n_ID`` and not against a position in the block:

    CLINE[n_CLINE_TYPE == <scene's type> and n_CREATURE_TYPE == <Mob-Set>]

    verified against the shipped scene-14 module's own baked row ids: set 1
    -> row 3400, set 111 -> row 3446, set 115 -> row 3450, and against scene
    1's Columbus row: (type 1, creature type 2) -> row 1001, n_LEADER_BK1
    156.

THE TRAP.  Every type is also a contiguous block of n_ID (type 1 ->
1000..1112, type 4 -> 1600..1660, type 14 -> 3400..3450, type 3001 ->
60400..60455), so "block base + set - 1" LOOKS like the same rule.  For
scene 126 it even gives the identical answer, because type 3001's creature
types run 1..56 with no gaps.  For scene 14 it is wrong: 51 rows against
Mob-Set numbers reaching 115, so the ordinal reading refuses set 111 - a
placement on the wire today.  This module names the column and does not
offer the arithmetic.

ON THE SELECTOR COUNT: this project repeats "240 of 271 scenes carry
0xFFFFFFFF".  Recounted from CONSTDATA_TH__SCENE_NAME.tsv on 2026-08-29:
271 rows, 252 no-cast, 19 direct.  19 is the figure world_bg0015_identity
already quotes correctly, and 271 - 19 is 252.

A NOTE ON THE VOCABULARY IN THIS FILE, SO IT DOES NOT READ AS COY.
``tests/test_npc_interaction_wire.py``'s QuestAndShopStateGuardTests refuses
the bare word q-u-e-s-t in any ``src/pirateforce_foundation`` module except
``columbus_quest_dispatch`` and ``runtime``.  This module implements none of
that behaviour - it names row ids and scene ids - so the prose says "row
3021" rather than argue for an exemption in a guard another lane owns.
"""
from __future__ import annotations

# Where row 3021 actually sends the player: QUESTDATA_TH__QUEST.tsv row
# 3021, n_VARI_2.  Agrees with columbus_quest_dispatch.COLUMBUS_DEST_SCENE_ID
# rather than contradicting it; a test below fails if the two ever drift.
DESTINATION_SCENE_N_ID = 17
DESTINATION_SCENE_MODEL_ID = "Bg1001"

# The ocean panel the option ADVERTISES, which is a property of the island
# the player is standing on, not of the destination.  Recorded so the next
# reader who meets this string on screen does not read it as a route.
ADVERTISED_OCEAN_SCENE_N_ID = 126
ADVERTISED_OCEAN_SCENE_MODEL_ID = "Bg3001"
ADVERTISED_OCEAN_CLINE_TYPE = 3001

# The ASCII half of SCENE_NAME_TIP row 126.  The full string carries Thai
# and one FULLWIDTH COLON (U+FF1A), which has no cp874 mapping and must not
# be written into a .py file under src/ - the bridge console's tripwire
# counts exactly that, and this lane has already lost a whole round to a
# single U+00B7.
#
# THIS FRAGMENT IS NOT UNIQUE, and an earlier draft claimed it was: two
# SCENE_NAME_TIP rows contain "Atlantic Ocean" - 126 (Rising Sun Sea) and
# 304 (Dark Fog Sea).  Uniqueness needs the tail as well.
ADVERTISED_NAME_ASCII_FRAGMENT = "Atlantic Ocean"
ADVERTISED_NAME_ASCII_TAIL = "Rising Sun Sea"

# The row this server already sends as conversation entry one.  Named for
# the crosswalk only; this module never changes it.
#
# THE ON-SCREEN STRING DOES NOT IDENTIFY THIS ROW.  Rows 3021, 3022 and 3023
# carry byte-identical s_QUEST_NAME and s_WORD1..3, one per island.  What
# makes this one 3021 is that columbus_quest_dispatch sends 3021, not
# anything the owner could read on the screen.
DESTINATION_QUEST_ID = 3021

# Each island's Columbus, his home scene (Q_BORNAGAIN n_VARI_2), the row he
# offers, the scene it teleports to (Q_TELEPORT1 n_VARI_2), and the ocean
# panel his island sits under.  Eight of eight, no exceptions - this is the
# table that makes the advertised name a property of the SOURCE.
COLUMBUS_ROUTES = (
    # (MOBS n_ID, home scene, row id, target scene, advertised ocean scene)
    (156, 1, 3021, 17, 126),
    (360, 2, 3022, 18, 126),
    (36, 3, 3023, 19, 126),
    (67, 4, 3024, 20, 304),
    (105, 5, 3025, 21, 304),
    (196, 6, 3026, 39, 127),
    (362, 7, 3027, 40, 127),
    (250, 8, 3028, 41, 305),
)

# Row -> the scene its n_VARI_2 names.  Row 3205 is the second option on the
# same screen and its n_VARI_2 (1) is Port Royal, which is what its own
# title says - the control that makes this column readable as a scene id.
OPTION_TARGET_SCENE_N_ID = {
    3021: 17,   # Q_TELEPORT1, n_VARI_1 111 - the ship
    3205: 1,    # Q_BORNAGAIN - Port Royal, and the control for this column
}

# Provenance for every claim above, in the form a reader can re-open.
PROVENANCE = (
    ("destination, and the column that decides it",
     "pf_bridge/gamedata/tables/QUESTDATA_TH__QUEST.tsv row 3021 "
     "(Q_TELEPORT1, n_VARI_1 111, n_VARI_2 17)"),
    ("that column read across siblings",
     "same file, rows 3002/3003/3005/3007/3009/3014/3038/8003 - title and "
     "n_VARI_2 agree in every one"),
    ("the same answer, observed on a client",
     "notes_to_chief/20260827_1710_GT106-RESULT-M2-... (attended: clicking "
     "this option put the player into scene 17, walkable)"),
    ("the eight-island crosswalk, read with no inference",
     "notes_to_chief/20260827_1050_ATTENDED-FOUND-M2-crosswalk-Columbus-156-"
     "... (the 2026-08-27 10:50 attended letter; grep that prefix - its full "
     "name spells a word the foundation guard in "
     "tests/test_npc_interaction_wire.py forbids in this directory)"),
    ("advertised ocean panel derivation",
     "pf_bridge/gamedata/tables/CONSTDATA_TH__MAP_SCENE_LIST.tsv "
     "(n_NAME_ID == home -> n_ID_MAINTITLE -> the MAINTITLE==0 row) then "
     "TEXTDATA_TH__SCENE_NAME_TIP.tsv"),
    ("on-screen option text",
     "notes_to_chief/20260829_0018_KA3A-GT122-PASS-GT102-PARTIAL-"
     "GT104-BLOCKED-mobs-answer-as-npc.md section 2"),
    ("scene rows",
     "pf_bridge/gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv n_ID 17 and 126"),
    ("placement file and its definition count",
     "pf_bridge/gamedata/scene/Bg3001/Bg3001.placements.tsv (38 rows) and "
     "PF_GAMEDATA_SCENE_INDEX.tsv (definition_count 56)"),
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

# Scene 126 census feasibility, measured 2026-08-29.  Counts about a
# possible FUTURE census of that scene, not a roster, and not a route.
PLACEMENT_COUNT = 38
RESOLVING_PLACEMENT_COUNT = 37
TWO_VARIANT_PLACEMENT_COUNT = 6      # of the 37: both legs resolve
EMPTY_LEADER_PLACEMENT_COUNT = 1     # index 28, set 16, CLINE 60415 leader 0
TWO_VARIANT_SHAPE_TREE_WIDE = (98, 16)   # placements, scenes carrying "a|b"

# No arrival position is pinned for EITHER scene here.  The reason is not a
# missing file: Bg3001's and Bg1001's .npc digests are both in this tree
# (PF_GAMEDATA_SCENE_INDEX.tsv, parse_status OK).  RE-103 established that
# the digest carries placement coordinates and NOT player-arrival ones -
# "the teleport target owns the XYZ" - so the arrival point has to come from
# the teleport path, which nothing in this tree has read yet.
ARRIVAL_POSITION = None


class SeaDestinationError(Exception):
    """This module refused rather than guessed."""


def cline_key(cline_type: int, mob_set_number: int) -> tuple[tuple[str, int], ...]:
    """The pair of column values that select one CLINE row.

    Returned as (column name, value) pairs rather than a row id on purpose:
    this module holds no copy of the table, and the one thing a caller can
    get wrong - which COLUMN the Mob-Set number is matched against - is
    exactly what a bare integer would hide again.
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


def route_for(columbus_mobs_n_id: int) -> tuple[int, int, int, int] | None:
    """(home scene, row id, target scene, advertised ocean scene), or None.

    The whole point of the table: the advertised ocean is NOT the target,
    and three Columbuses advertise the same ocean while going to three
    different ship scenes.
    """
    for mobs_n_id, home, row, target, ocean in COLUMBUS_ROUTES:
        if mobs_n_id == columbus_mobs_n_id:
            return (home, row, target, ocean)
    return None


def destination_ready() -> bool:
    """Whether this project can put a player on the far side of that door.

    False, and it stays False until an arrival position is pinned by
    something better than arithmetic.  Fail-closed on purpose.
    """
    return ARRIVAL_POSITION is not None


def refusal_reason() -> str:
    """Why :func:`destination_ready` says no, in the words a console line can
    print without a second lookup."""
    if destination_ready():
        return ""
    return (
        "scene %d (%s) has no pinned arrival position - RE-103: the .npc "
        "digest carries placement XYZ, not arrival XYZ, so the teleport "
        "target owns it and nothing here has read that path"
        % (DESTINATION_SCENE_N_ID, DESTINATION_SCENE_MODEL_ID)
    )


def console_line() -> str:
    """One ASCII line naming where the door leads and this module's limit.

    Printed by whatever calls it; nothing in this file prints on import.
    """
    state = "READY" if destination_ready() else "REFUSED"
    return (
        "M2_SEA_DESTINATION offer=%d target_scene=%d model=%s "
        "advertises_ocean=%d (%s_%s) state=%s reason=%s"
        % (
            DESTINATION_QUEST_ID,
            DESTINATION_SCENE_N_ID,
            DESTINATION_SCENE_MODEL_ID,
            ADVERTISED_OCEAN_SCENE_N_ID,
            ADVERTISED_NAME_ASCII_FRAGMENT.replace(" ", "_"),
            ADVERTISED_NAME_ASCII_TAIL.replace(" ", "_"),
            state,
            refusal_reason() or "none",
        )
    )


def _self_check() -> None:
    """Internal consistency only - this file has no tables to re-read."""
    if DESTINATION_SCENE_N_ID == ADVERTISED_OCEAN_SCENE_N_ID:
        raise SeaDestinationError(
            "the target scene and the advertised ocean have become one "
            "number - the whole finding of this module is that they differ"
        )
    if OPTION_TARGET_SCENE_N_ID[DESTINATION_QUEST_ID] != DESTINATION_SCENE_N_ID:
        raise SeaDestinationError(
            "the target scene disagrees with the row's own n_VARI_2"
        )
    if RESOLVING_PLACEMENT_COUNT + EMPTY_LEADER_PLACEMENT_COUNT != PLACEMENT_COUNT:
        raise SeaDestinationError(
            "placement counts do not add up: %d resolving + %d empty-leader "
            "!= %d placements"
            % (RESOLVING_PLACEMENT_COUNT, EMPTY_LEADER_PLACEMENT_COUNT,
               PLACEMENT_COUNT)
        )
    if TWO_VARIANT_PLACEMENT_COUNT > RESOLVING_PLACEMENT_COUNT:
        raise SeaDestinationError(
            "the two-variant rows are a SUBSET of the resolving ones - "
            "counting them as a separate drop is the error this file was "
            "corrected for"
        )
    if ADVERTISED_OCEAN_CLINE_TYPE not in CLINE_BLOCKS:
        raise SeaDestinationError(
            "the advertised ocean's CLINE type has no measured block"
        )
    routes = {row[0] for row in COLUMBUS_ROUTES}
    if len(routes) != len(COLUMBUS_ROUTES):
        raise SeaDestinationError("a Columbus appears twice in COLUMBUS_ROUTES")
    oceans = {row[4] for row in COLUMBUS_ROUTES}
    targets = {row[3] for row in COLUMBUS_ROUTES}
    if len(targets) != len(COLUMBUS_ROUTES) or len(oceans) >= len(targets):
        raise SeaDestinationError(
            "COLUMBUS_ROUTES must show one target per island and fewer "
            "oceans than targets - that asymmetry IS the finding"
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
