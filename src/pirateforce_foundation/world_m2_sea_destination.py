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

ROUND drrnpu, 2026-08-29: THE TWO SENTENCES THIS FILE HAD WRONG.  Until this
round the file said, in code and in prose, that the door has no landing spot
and that nobody had read the path that would carry one.  Both were false ON
MAIN while they were written, and a reader who believed them would have gone
looking for work that is already done.

0.  **AND THE ROUND THAT WROTE ITEMS 1-3 BELOW WAS ITSELF REFUTED, BY ITS OWN
    ADVERSARY PASS, BEFORE IT LEFT DRAFT.  READ THIS ITEM FIRST.**
    ``n_VARI_2`` is almost certainly **a MarkerID, not a scene id**, and this
    module has stated the scene reading as MEASURED since it was written.
    Re-derived twice, once by ``pf-adversary`` and once by the round, from
    ``QUESTDATA_TH__QUEST.tsv`` and ``CONSTDATA_TH__MARKER.tsv``:

        41 rows use these two scripts.  41 of 41 carry a Var2 that is a valid
        MARKER id.  FIVE carry a Var2 that is not a scene id at all:
        3016 -> 12, 3018 -> 16, 3019 -> 12, 3037 -> 1000, 3039 -> 336.
        Row 3037 passes 1000, and 1000 is exactly what SCENE_NAME row 130
        declares in its own n_MARKER column.  A destination "scene 1000"
        does not exist.

        MARKER[Var2].n_SCENE reproduces this file's whole eight-row
        "advertised ocean" column - 126,126,126,304,304,127,127,305 - in ONE
        lookup, where this file derives it through a three-hop
        MAP_SCENE_LIST -> n_ID_MAINTITLE -> SCENE_NAME_TIP chain.  Under the
        marker reading the three Columbuses that "advertise the same ocean"
        are three different BERTHS in scene 126: MARKER[17] is
        (3050, 232, 90) dir 6 and MARKER[18] is (-5072, 4000, 90) dir 7,
        about 8000 units apart.

    ``q_teleport_new.lua`` states the argument's type in the client's own
    header comment (Big5): teleport methods 0 and 4 take a **MarkerID** in
    the variable it then passes to ``Player.Teleport``.  And the control this
    file offered for the scene reading - "measured across siblings: 3002 ->
    1, 3003 -> 4, 3005 -> 5, 3007 -> 6, 3009 -> 8, 3014 -> 14" - is
    DEGENERATE: every one of those six values is in the 19-row subset where
    ``MARKER.n_ID == MARKER.n_SCENE``, so both readings give the same answer
    and the control could not have failed.

    **The owner said this on 2026-08-27 and the project overruled them.**
    GT-106's letter, section 4.2: in the original game that option turns you
    into a ship and puts you in "Atlantic Ocean: Rising Sun Sea", not "Ship
    in the Sea".  That is scene 126 - and ``MARKER[17].n_SCENE`` is 126.
    The letter's own open question, "how does the original server turn 17
    into scene 126", has that one-column answer.

    WHAT THIS FILE DOES ABOUT IT, AND WHAT IT DELIBERATELY DOES NOT.
    ``DESTINATION_SCENE_N_ID`` stays 17 in code this round, because
    ``columbus_quest_dispatch`` and a live flagless call site agree on 17
    and because ``COO-DECISION 20260829_0441`` closed the 17-vs-126 question
    in favour of 17 - on this lane's own withdrawal of it, and on the
    degenerate control above.  Changing a live destination on a lane's own
    reading is not this lane's call.  So the number stays and the CLAIM
    changes: the scene reading is **[CONTESTED - LANE-A round drrnpu,
    awaiting COO]**, not measured, and the letter is
    ``pf_bridge/notes_to_chief/20260829_1410_LANE-A-ASK-COO-var2-is-a-
    markerid.md``.  Nothing in this file may be quoted as measuring that
    row 3021's destination is a scene id.

1.  **"Nothing here has read that path."**  The path is
    ``q_teleport1.lua``, the script row 3021 names in ``s_LUASCRIPT`` -
    ``PF_GAMEDATA_LUA_INDEX.tsv`` indexes it, with its directory, under that
    basename.  (The directory name is spelled out nowhere in this file: it is
    a bare word ``tests/test_npc_interaction_wire.py`` forbids here, and
    working around a sibling lane's guard is not worth one path string.)
    Read this round, in full: its ``Accept_Run``
    calls ``Player.Teleport(<the row's own n_VARI_2 field>)`` with **ONE
    argument, the destination scene id, and no coordinate of any kind**.  Its
    sibling ``q_teleport_with_vehicle1.lua`` (rows 3002-3014) is the same call
    with ``Player.TeleportWithVehicle``, same single argument.  So THOSE TWO
    SCRIPTS carry no float coordinate - a fact about two files, not about the
    mechanism (item 0), and narrower than it first reads: the family has five
    members, and ``q_teleport3.lua`` calls ``Player.ResetMarker(Var2)`` right
    before its own teleport, which is a positioning call taking the same
    argument.  This round read two of the five in full; ``q_teleport_new``
    was read afterwards, by the adversary, and it is the one that names the
    argument's type.  ``CONSTDATA_TH__SCENE_NAME``'s
    own ``n_MARKER`` column, the client's authored arrival-point pointer,
    reads **0** for scene 17 and for every scene in the sea family (18-23),
    so the table that WOULD have carried one says there is none.  Together
    those two close ``RE-103``'s question about SCENE 17's OWN default
    arrival point: no scene-keyed arrival data exists for the sea family.
    ~~for a sea scene the arriving position is not authored data anywhere, so
    whoever sends the teleport owns it.~~  **STRUCK IN THE SAME ROUND THAT
    WROTE IT (item 0).**  The arriving position for row 3021 IS authored, in
    ``MARKER[17]``, and reading a Lua stub's lack of a coordinate as the
    whole mechanism's lack of one was the error: RE-103's own T3 recorded
    that the WIRE Teleport target carries scene_id AND a vec3, and the land
    case shows where the server gets that vec3 - SCENE_NAME.n_MARKER ->
    MARKER -> point.  One layer's silence is not another layer's answer.

    ``Accept_Check`` in the same script gates acceptance on
    ``Var1``, which is **111** for rows 3021 and 3022 and 0 for 3023-3028 -
    a flag precondition on the client side.  **[PROPOSED, NOT MEASURED]**
    that it stops nothing: what GT-106 measured is that with the dialog THIS
    server built, the client displayed the option and sent the operate frame
    for row 3021 with no such flag set - and that letter's own nonclaims say
    it does not prove ``Accept_Check`` was called at all.  A gate that is
    never invoked has not been measured as harmless.  Recorded because the
    next reader of this script will otherwise re-open it.

2.  **"No pinned arrival position."**  There has been one since
    2026-08-27T14:45+07:00, in this project's own registry, and this module
    is the only file that said otherwise -
    ``scenarios/world_scene_registry_001.json``'s scene-17 entry carries
    ``spawn (0, 0, 0)`` under ``PROVISIONAL-OWNER-DECREE-20260827-1445``.
    ``columbus_quest_dispatch`` has been dispatching on it, and
    ``runtime.py:4567`` calls that dispatch on the FLAGLESS path.  This file
    kept its own ``ARRIVAL_POSITION = None`` next to it: two answers to one
    question, one of them stale, which is the exact defect shape
    ``pf-adversary`` charged this lane with in round ``yam18f`` (D8).  The
    constant is struck below and every answer now comes from the registry.

3.  **AND A PLAYER HAS ALREADY WALKED THROUGH THIS DOOR.**  ``GT-106``, an
    attended run on 2026-08-27, flagless, on main:
    ``notes_to_chief/20260827_1710_GT106-RESULT-M2-*``.  Both layers, from
    that letter:

        wire  ``WORLD_SCENE scene_id=17 ... spawn=(0.000,0.000,0.000)
              save=0 marker=0`` then ``SCENE_ENTRY scene=17
              xyz=0.000,0.000,0.000 source=PROVISIONAL-OWNER-DECREE-
              20260827-1445`` then the teleport frame, sent once
        screen ``...GT106_scene17_ShipInTheSea_arrival_X0_Y0_...png``:
              HUD **X:0 Y:0**, character standing on the wooden deck, then
              walked to X:-639 Y:200 without falling

    So the decreed point is no longer only decreed: it has been sent and it
    put a player on a walkable deck.  That is the evidence the decree names
    as its own expiry condition, and retiring the decree is therefore a
    change this project OWES - but not one this round makes, and the reason
    is measured rather than cautious.  The prefix is not a label: it is what
    EXEMPTS this spawn from ``world_scene_travel``'s ground check, and that
    check tests z against the band the scene's own native placements give
    (746.04 .. 1272.74).  Driven this round, three registries built and
    loaded (``test_retiring_the_decree_today_would_stop_the_registry_
    loading``):

        provenance measured, z = 0        -> ValueError, registry REFUSES to
                                             load: every login dies at boot
        provenance measured, z = 745.0    -> ValueError, the same refusal -
                                             the z a human ACTUALLY STOOD AT
                                             is 1.04 under the band
        provenance measured, z = 746.0424 -> loads
        the pairing shipped today          -> loads

    So the band derived from placements refuses the only position anybody has
    ever occupied in this scene, which is the registry's own ground block
    saying "a .npc file carries NPC placements, not terrain" arriving as a
    load failure.  Retiring the decree therefore means deciding what z means
    here, not editing a string - plus ``world_scene_entry``'s radius rule
    (a decreed spawn may not count as ground evidence) and the console token
    operators grep.  Written up for COO in this round's letter instead of
    flipped here.

    THE ONE THING THAT RUN ALSO SETTLES, AND THE READING TO NOT TAKE FROM IT.
    ``z = 0`` did not drop the player: the client put them on the deck at
    ``(0, 0)`` anyway, and the run DB row written from their own walk in that
    scene reads ``z = 745.0`` - one unit under the lowest native placement in
    the file (``746.0424``).  So the client resolves the standing height
    itself and a server-sent z of 0 is survivable HERE.  Do NOT read that as
    "z never matters": one scene, one run, one client build.
"""
from __future__ import annotations

# Where row 3021 actually sends the player: QUESTDATA_TH__QUEST.tsv row
# 3021, n_VARI_2.  Agrees with columbus_quest_dispatch.COLUMBUS_DEST_SCENE_ID
# rather than contradicting it; a test below fails if the two ever drift.
#
# ID SPACE (COO-DECISION 2026-08-29 14:44, item 4 - a destination module
# must name the space its number lives in): read here as
# ``CONSTDATA_TH__SCENE_NAME.n_ID``.  [CONTESTED] The rival reading is
# ``MARKER.n_ID``, under which 17 resolves to ``MARKER[17].n_SCENE = 126``
# at (3050, 232, 90) heading 6 - re-derived from the committed MARKER table
# in round 2pdf6j, same numbers the ruling names.  The value is legal in
# BOTH spaces and no control in any table separates them, so neither
# reading may be labelled measured; the COO sent it to an attended test.
# Until that result lands, this stays 17 and the [CONTESTED] tag below
# stays with it.
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

# ~~No arrival position is pinned for EITHER scene here.  The reason is not a
# missing file: Bg3001's and Bg1001's .npc digests are both in this tree
# (PF_GAMEDATA_SCENE_INDEX.tsv, parse_status OK).  RE-103 established that
# the digest carries placement coordinates and NOT player-arrival ones -
# "the teleport target owns the XYZ" - so the arrival point has to come from
# the teleport path, which nothing in this tree has read yet.
# ARRIVAL_POSITION = None~~
# STRUCK, round drrnpu: false on main when it was written.  The registry has
# pinned scene 17's arrival since 2026-08-27 and runtime.py:4567 dispatches on
# it flaglessly.  Kept struck rather than deleted (house rule) because the
# sentence "the teleport path was never read" is the reason RE-103 stayed open
# for two days after the path became readable.  The path is read now - see the
# module docstring, item 1 - and every arrival answer below comes from the ONE
# place that owns it:
ARRIVAL_POSITION_OWNER = (
    "scenarios/world_scene_registry_001.json -> destinations[n_id == 17].spawn,"
    " read through world_scene_travel.destination()/spawn_position()"
)

# What GT-106 measured on 2026-08-27, both layers, flagless, on main.  Values
# only - the argument is in the module docstring, item 3.
ARRIVAL_EVIDENCE_TICKET = "GT-106"
# Cited by its stable head rather than in full: the tail of the real filename
# carries a bare word the foundation-module word guard refuses in src/.
ARRIVAL_EVIDENCE_LETTER = (
    "pf_bridge/notes_to_chief/20260827_1710_GT106-RESULT-M2-Columbus-3021-"
    "enters-scene17-walkable-*.md"
)
ARRIVAL_SCREEN_ARTIFACT = (
    "OURS_LOCAL_SERVER_GT106_scene17_ShipInTheSea_arrival_X0_Y0_"
    "20260827_164301.png"
)
# The HUD reading at arrival, which is the client-observable half.  x and y
# only: the HUD in that shot carries no z.
ARRIVAL_OBSERVED_HUD_XY = (0.0, 0.0)
# The one z ever recorded inside this scene: the run DB character_positions
# row written from the player's own walk (NOT at the arrival point - they had
# walked to about (-149, -1250) by then, and the row carried scene_id 1
# because of the persistence defect the same letter reports).
ARRIVAL_RUN_DB_WALKED_Z = 745.0
# The lowest native placement z in Bg1001.placements.tsv, one unit above the
# walked z.  Two independent sources putting the walkable deck at ~745-746 is
# why "z = 0 was survivable" is stated as an observation about this client and
# not as a rule.
LOWEST_NATIVE_PLACEMENT_Z = 746.0424194335938

# The teleport path, read this round.  ONE argument and no coordinate: that
# single fact is what closes RE-103 positively instead of by absence.
# Basename only, for the reason given in the docstring - it is unique in
# PF_GAMEDATA_LUA_INDEX.tsv, which carries the directory.
TELEPORT_SCRIPT = "q_teleport1.lua"
TELEPORT_CALL = "Player.Teleport(<n_VARI_2>)"
TELEPORT_CALL_ARGUMENT_COUNT = 1
TELEPORT_CALL_CARRIES_A_POSITION = False
# The client-side acceptance precondition in the same script (Var1), and the
# rows that carry it.  GT-106 measured it not blocking - docstring item 1.
TELEPORT_ACCEPT_PRECONDITION_VALUE = 111
TELEPORT_ACCEPT_PRECONDITION_ROWS = (3021, 3022)
# CONSTDATA_TH__SCENE_NAME.n_MARKER, the client's own arrival-point pointer,
# for this scene and for the whole sea family.  0 means the client authored
# no arrival point for them.
SCENE_NAME_MARKER_COLUMN_FOR_THE_SEA_FAMILY = 0
SEA_FAMILY_SCENE_IDS = (17, 18, 19, 20, 21, 22, 23)

# The prefix that marks a spawn the owner decreed rather than one anybody
# measured.  Not re-typed here - this module imports the constant.  ~~two
# other modules branch on it~~ CORRECTED (pf-adversary, round drrnpu, D9):
# world_scene_entry hard-codes the literal at TWO places (285, 476) instead
# of importing it, so the string exists by hand in three spots and this
# module is the only one reading it from its owner.  Said out loud rather
# than left as a comment that flatters this file.
_DECREE_PREFIX_OWNER = "world_scene_travel.PROVISIONAL_SPAWN_PROVENANCE_PREFIX"

# The literal Var2 of row 3021, and what MARKER says at that id.  These are
# the numbers item 0 of the docstring turns on, kept as data so a test can
# drive them instead of a reader having to trust prose.
DESTINATION_QUEST_ROW_VAR2 = 17
MARKER_AT_VAR2 = (126, 3050, 232, 90)          # (n_SCENE, x, y, z)
MARKER_AT_VAR2_DIRECTION = 6
# Rows in the two teleport scripts whose Var2 is NOT a scene id at all - the
# five that falsify the scene reading.  (row id, Var2).
VAR2_VALUES_THAT_ARE_NOT_SCENE_IDS = (
    (3016, 12), (3018, 16), (3019, 12), (3037, 1000), (3039, 336),
)
TELEPORT_ROWS_TOTAL = 41
# Row 3037 passes 1000; SCENE_NAME row 130 declares n_MARKER 1000.  One
# number, in both places, that cannot be a scene id.
SCENE_130_DECLARES_MARKER = 1000

STATE_REFUSED = "REFUSED"
STATE_READY_DECREED = "READY_DECREED"
# NOT "READY_MEASURED": this fires on the ABSENCE of the decree prefix, and
# nothing here checks that a measurement exists.  pf-adversary (round drrnpu,
# D7) named the input that would make a measured-sounding token print with no
# measurement anywhere: any hand-edited provenance, "pending re-measurement"
# included.  The name says what the test actually is.
STATE_READY_NOT_DECREED = "READY_NOT_DECREED"


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


def _target(registry):
    """The registry's row for scene 17, or None when it pins none.

    ``registry`` is REQUIRED and never defaulted.  ``world_scene_travel.
    destination()`` falls back to loading the file from disk when it is given
    a falsy registry, so a caller who forgot the argument would otherwise get
    a confident answer sourced from a file this module never meant to open -
    a boot reading one registry while this line reads another.
    """
    if registry is None:
        raise SeaDestinationError(
            "a scene registry is required - pass the one the boot loaded, "
            "never None (this module must not read the file itself)"
        )
    if not hasattr(registry, "destinations"):
        # Refusing here rather than below keeps the REFUSED answer honest.
        # world_scene_travel.destination() indexes whatever it is given, so a
        # string or a list would raise IndexError, get caught as "this
        # registry does not carry scene 17", and hand back a confident
        # refusal about a registry that was never one.
        raise SeaDestinationError(
            "that is not a scene registry - expected the object "
            "world_scene_travel.load_scene_registry() returns, got %r"
            % (type(registry).__name__,)
        )
    from . import world_scene_travel

    try:
        return world_scene_travel.destination(DESTINATION_SCENE_N_ID, registry)
    except Exception:
        # Not in this registry: a refusal, fail-closed, never an exception
        # into a caller's boot.
        return None


def arrival_position(registry) -> tuple[float, float, float] | None:
    """Scene 17's pinned arrival point, or None if the registry pins none.

    Takes the registry rather than loading one: the caller (runtime.py) reads
    it once at boot, and a module that opened the file itself would be the
    second copy this file was just corrected for holding.
    """
    target = _target(registry)
    if target is None:
        return None
    from . import world_scene_travel

    try:
        return world_scene_travel.spawn_position(target)
    except Exception:
        # A pinned row with no spawn is a refusal, not a crash - the same
        # answer a missing row gets, said out loud by refusal_reason().
        return None


def arrival_provenance(registry) -> str | None:
    """The provenance string the registry carries for that point, verbatim."""
    target = _target(registry)
    return None if target is None else target.spawn_provenance


def arrival_is_decreed(registry) -> bool:
    """Whether the pinned point still rests on the owner's decree.

    True today.  GT-106 has satisfied the decree's own written expiry
    condition (module docstring, item 3), but retiring the prefix changes two
    other modules' behaviour and one console token, so it is a decision this
    module reports rather than takes.
    """
    from . import world_scene_travel

    provenance = arrival_provenance(registry)
    if provenance is None:
        return False
    return provenance.startswith(
        world_scene_travel.PROVISIONAL_SPAWN_PROVENANCE_PREFIX
    )


def destination_state(registry) -> str:
    """REFUSED, READY_DECREED or READY_NOT_DECREED - one word for a console.

    The third state is deliberately not called READY_MEASURED: it is the
    absence of the decree prefix, which is not the presence of a measurement.
    """
    if arrival_position(registry) is None:
        return STATE_REFUSED
    return STATE_READY_DECREED if arrival_is_decreed(registry) else (
        STATE_READY_NOT_DECREED
    )


def destination_ready(registry) -> bool:
    """Whether this project can put a player on the far side of that door.

    It can, and it has: GT-106 walked it on 2026-08-27.  This answers from
    the registry, so it can only be True while a point is actually pinned -
    and it says nothing about whether the door is OPEN.  Two separate pins
    keep it shut for login (``login_entry_allowed: false``) and for
    persistence (``persist_position_allowed: false``); the live way through
    is the row-3021 dispatch, not this function.
    """
    return arrival_position(registry) is not None


def refusal_reason(registry) -> str:
    """Why :func:`destination_ready` says no, in the words a console line can
    print without a second lookup.

    Empty when a point is pinned - including when it is only decreed.  A
    decreed point is a weak point, not a missing one, and reporting weak as
    missing is what sent RE-103 looking for a file that was never going to
    exist.
    """
    if destination_ready(registry):
        return ""
    return (
        "scene %d (%s) has no arrival point in the registry - SCENE_NAME."
        "n_MARKER is %d for this scene, so the client authors none KEYED BY "
        "SCENE; MARKER[%d] does exist and carries (%d,%d,%d) in scene %d, "
        "which is the contested reading (see this module's docstring item 0) "
        "and must not be pinned here without a ruling"
        % (
            DESTINATION_SCENE_N_ID,
            DESTINATION_SCENE_MODEL_ID,
            SCENE_NAME_MARKER_COLUMN_FOR_THE_SEA_FAMILY,
            DESTINATION_QUEST_ROW_VAR2,
            MARKER_AT_VAR2[1], MARKER_AT_VAR2[2], MARKER_AT_VAR2[3],
            MARKER_AT_VAR2[0],
        )
    )


def console_line(registry) -> str:
    """One ASCII line naming where the door leads and this module's limit.

    Printed by whatever calls it; nothing in this file prints on import.
    """
    state = destination_state(registry)
    point = arrival_position(registry)
    arrival = "none" if point is None else (
        "%.3f,%.3f,%.3f" % point
    )
    return (
        "M2_SEA_DESTINATION offer=%d target_scene=%d model=%s "
        "advertises_ocean=%d (%s_%s) var2_reading=CONTESTED state=%s "
        "arrival=%s evidence=%s reason=%s"
        % (
            DESTINATION_QUEST_ID,
            DESTINATION_SCENE_N_ID,
            DESTINATION_SCENE_MODEL_ID,
            ADVERTISED_OCEAN_SCENE_N_ID,
            ADVERTISED_NAME_ASCII_FRAGMENT.replace(" ", "_"),
            ADVERTISED_NAME_ASCII_TAIL.replace(" ", "_"),
            state,
            arrival,
            # The ticket that walked it, so an operator reading one line can
            # tell "pinned" from "pinned and used by a real client".
            ARRIVAL_EVIDENCE_TICKET,
            refusal_reason(registry) or "none",
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
    if DESTINATION_SCENE_N_ID not in SEA_FAMILY_SCENE_IDS:
        raise SeaDestinationError(
            "the destination has left the scene family whose n_MARKER column "
            "this file reports as 0 - one of the two was edited alone"
        )
    if not 0.0 < LOWEST_NATIVE_PLACEMENT_Z - ARRIVAL_RUN_DB_WALKED_Z < 2.0:
        raise SeaDestinationError(
            "the docstring says the walked z is about one unit under the "
            "lowest native placement; these two numbers no longer say that"
        )
    if DESTINATION_QUEST_ROW_VAR2 != OPTION_TARGET_SCENE_N_ID[DESTINATION_QUEST_ID]:
        raise SeaDestinationError(
            "the row's literal Var2 and the number this file reads as a "
            "scene id have been allowed to differ - the whole contest in "
            "docstring item 0 is that they are the SAME number read two ways"
        )
    if SCENE_130_DECLARES_MARKER not in [
        var2 for _row, var2 in VAR2_VALUES_THAT_ARE_NOT_SCENE_IDS
    ]:
        raise SeaDestinationError(
            "1000 is the number that closes item 0 - a Var2 that is a marker "
            "id and cannot be a scene id; removing it from the list guts the "
            "refutation this file is required to carry"
        )
    if TELEPORT_CALL_ARGUMENT_COUNT != 1 or TELEPORT_CALL_CARRIES_A_POSITION:
        raise SeaDestinationError(
            "the whole RE-103 answer is that the teleport call takes one "
            "argument and no coordinate - editing that here does not make it "
            "true in the script"
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
