"""GENERATED - do not hand-edit.  LANE-B scene mob roster.

Written by ``tools/pf_mine_scene_mob_roster.py`` from the committed game data
on the bridge clone.  Regenerate rather than patch; the generator carries the
selection rule, the controls it refuses on, and the reasoning behind both.

The rows below are the placements of one scene whose MOBS row has a rank and a
combat AI.  Every value is copied from a table; nothing here was composed.
``max_hp`` is the one derived column: ``STANDARD_MOB[n_LEVEL_MIN].n_HPMAX``.

WHO EACH PLACEMENT IS, AND UNDER WHICH RULE.  ``IDENTITY_RULE`` below names
it.  ``cline`` = the RE-128 crosswalk: the scene's own ``SCENE_NAME
.n_CLINE_TYPE``, then ``CLINE[(type, Mob-Set number)].n_LEADER_BK1`` is the
real ``MOBS.n_ID``.  ``setnum`` = the older reading in which a Mob-Set number
was taken to BE the ``n_ID``; that reading is what the owner rejected on sight
for Port Royal in ``GT-078``.  ``template_id`` in every row below is the
resolved ``MOBS.n_ID`` - the value the client reads as the template u16 -
and ``SET_NUMBER_FOR_PLACEMENT`` keeps the scene file's own number beside it.

SOURCES AND THEIR DIGESTS AT MINING TIME
    cline          aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40
    mobs           3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b
    mobs_tip       e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f
    placements     e57841a7018b46ff50d31972e5ba0846612548288446fe8514d819a99be92f8f
    scene_name     e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b
    standard_mob   4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925

SELECTION CENSUS FOR THIS SCENE (see the generator on why this is printed)
    ai_combat            52
    drops_normal         52
    rank                 52
    rank_and_ai_combat   52
    town_target          0
    unambiguous          104
"""

from __future__ import annotations


SCENE = 'Bg0002'
IDENTITY_RULE = 'cline'
# s_OUTFIT DOES NOT DECIDE WHO IS AN ENEMY IN THIS SCENE.  Owner
# ruling 2026-09-07 (PANYA 1313 / COO-DECISION 20260907_1346):
# an enemy is n_RANK plus n_AI_COMBAT and nothing else.  A row
# whose s_OUTFIT is a variant list is carried here; a module with
# no OUTFIT_RULE line was mined under the older rule that
# refused those rows.  visual_preset below is the RAW cell,
# separators included: RE-296 (2026-09-07T14:50) measured that
# the client tokenises it on ';', TAB and SPACE and keeps EVERY
# token, and left open who picks one.  Do not read this column
# as 'the avatar'.
OUTFIT_RULE = 'any'
SCENE_CLINE_TYPE = 2
SOURCE_DIGESTS = {
    'cline': 'aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40',
    'mobs': '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    'mobs_tip': 'e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f',
    'placements': 'e57841a7018b46ff50d31972e5ba0846612548288446fe8514d819a99be92f8f',
    'scene_name': 'e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b',
    'standard_mob': '4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925',
}
PREDICATE_CENSUS = {
    'ai_combat': 52,
    'drops_normal': 52,
    'rank': 52,
    'rank_and_ai_combat': 52,
    'town_target': 0,
    'unambiguous': 104,
}
# What the crosswalk controls found at mining time.  Recorded, not a check:
# nothing here can re-read CLINE, which lives on the bridge clone.
#
# --- PROVENANCE BLOCK BEGIN (pinned verbatim against the generator) -------
# WHICH CONTROL RE-READS THIS TABLE.  Corrected under D14 of pf-adversary's
# pass on round r6isy5b: this generator stamped one sentence about controls
# onto every scene it emits, and the sentence was true of one of them.
#
# ~~The executable control on this data is the roster loader's own
# assert_frozen_controls, which holds these rows against
# world_port_royal_identity's independently mined crosswalk table inside this
# repository.~~ STRUCK, not deleted, because it is TRUE FOR bg0001 AND FALSE
# FOR EVERY OTHER SCENE, and a reader has to be able to see which sentence
# was over-generalised: that function calls load_roster() with no argument
# and reads the bg0001 table module by name, so it has never read one row of
# a sibling scene's table.  MEASURED, not read off the source: give any
# sibling scene's first shipped row template id 65535 and a name no table
# contains and that control still passes; the same mutation on bg0001 raises
# (`placement 103 ships n_ID 65535, the crosswalk says 916`).
#
# The loader module is named by its FUNCTION and not by its module name
# throughout this block, deliberately: a name-based tripwire lists every file
# under src/ that mentions that module as one of its importers, and a
# generated data table that imports nothing must not join that list on the
# strength of a comment.
#
# WHAT DOES RE-CHECK THESE ROWS, per scene, each one opened and read rather
# than assumed from a filename (the first draft of this correction guessed a
# filename for two scenes and was wrong about both -- pf-adversary, D1):
#
#   * EVERY scene, including this one: a byte-for-byte regenerate test that
#     re-runs this generator against the bridge clone's tables and compares
#     the whole module.  It is the upstream drift control, and it is gated on
#     the bridge clone being present, so it does NOT run on the Windows merge
#     gate.  Nothing else re-derives these values from the client's tables.
#   * bg0001: the struck function above -- for this one scene it was, and
#     still is, the row-level identity control.
#   * Bg0003, bg0004, bg0005: a row-by-row cross-check against LANE-A's
#     independently mined identity table, in that scene's own test module.
#   * Bg0015: the same cross-check, but it lives in the test module of
#     LANE-A's identity table, not in this scene's own.
#   * Bg0002: NONE.  Its Mob-Set numbers ARE its n_ID by the owner's
#     2026-08-27 ruling, so there is no second table to cross-check against
#     and no row-level control on or off the bridge.  Named here rather than
#     left for a reader to discover, and open: who closes it is not this
#     generator's call.
# --- PROVENANCE BLOCK END -------------------------------------------------
CONTROL_FINDINGS = {
    'prison_exile_identity': '35/35',
    'town_target_916_hp': '198125',
}

# The scene file's own Mob-Set number per placement, so a reader can redo the
# resolution by hand: SET_NUMBER_FOR_PLACEMENT[i] -> CLINE -> template_id.
SET_NUMBER_FOR_PLACEMENT = {
    31: 28,
    32: 28,
    33: 28,
    34: 28,
    35: 28,
    36: 27,
    37: 27,
    38: 27,
    39: 27,
    40: 29,
    41: 29,
    42: 29,
    43: 30,
    44: 33,
    45: 33,
    46: 30,
    47: 30,
    48: 30,
    49: 30,
    50: 31,
    51: 33,
    52: 33,
    53: 32,
    54: 33,
    55: 30,
    56: 30,
    57: 30,
    58: 34,
    59: 34,
    60: 34,
    61: 35,
    62: 32,
    69: 33,
    70: 29,
    71: 29,
    72: 30,
    73: 30,
    74: 30,
    75: 33,
    76: 33,
    77: 31,
    78: 31,
    79: 35,
    80: 35,
    81: 29,
    82: 33,
    83: 28,
    84: 29,
    85: 32,
    86: 34,
    87: 34,
    88: 34,
}

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
# Placements whose resolved MOBS row carries BOTH a rank and a combat AI.
HOSTILE_PLACEMENTS = [
    (31, 28, 6924.79833984375, 11621.9033203125, 2491.86376953125, 'M001_000_000_N;M001_000_000_SP1', 'Drunk wolf pirates', 16, 1, 16, 110, 100, 1054, 2701001, 5400001, 0),
    (32, 28, 7540.783203125, 9423.3486328125, 2339.728515625, 'M001_000_000_N;M001_000_000_SP1', 'Drunk wolf pirates', 16, 1, 16, 110, 100, 1054, 2701001, 5400001, 0),
    (33, 28, 7904.90673828125, 7103.75732421875, 2399.0791015625, 'M001_000_000_N;M001_000_000_SP1', 'Drunk wolf pirates', 16, 1, 16, 110, 100, 1054, 2701001, 5400001, 0),
    (34, 28, 7402.69091796875, 4605.966796875, 2431.791015625, 'M001_000_000_N;M001_000_000_SP1', 'Drunk wolf pirates', 16, 1, 16, 110, 100, 1054, 2701001, 5400001, 0),
    (35, 28, 4553.7744140625, 2544.940673828125, 2383.078125, 'M001_000_000_N;M001_000_000_SP1', 'Drunk wolf pirates', 16, 1, 16, 110, 100, 1054, 2701001, 5400001, 0),
    (36, 27, 3124.040283203125, 378.0357971191406, 2299.1484375, 'M005_000_000_SP1;M005_000_000_SP2', 'Mountain Deer', 17, 1, 16, 150, 100, 1201, 2701001, 5400001, 2802222),
    (37, 27, 682.3438720703125, 1555.4178466796875, 2927.33740234375, 'M005_000_000_SP1;M005_000_000_SP2', 'Mountain Deer', 17, 1, 16, 150, 100, 1201, 2701001, 5400001, 2802222),
    (38, 27, -5054.56982421875, 13031.8916015625, 1343.759765625, 'M005_000_000_SP1;M005_000_000_SP2', 'Mountain Deer', 17, 1, 16, 150, 100, 1201, 2701001, 5400001, 2802222),
    (39, 27, -8637.4619140625, 13720.3984375, 867.1171875, 'M005_000_000_SP1;M005_000_000_SP2', 'Mountain Deer', 17, 1, 16, 150, 100, 1201, 2701001, 5400001, 2802222),
    (40, 29, -5655.052734375, 1122.0823974609375, 3414.732421875, 'M001_000_001_SP1;M001_000_001_SP2', 'Lion pirates', 19, 1, 16, 110, 100, 1569, 2701001, 5400001, 0),
    (41, 29, -7929.8720703125, 2489.582763671875, 3621.234130859375, 'M001_000_001_SP1;M001_000_001_SP2', 'Lion pirates', 19, 1, 16, 110, 100, 1569, 2701001, 5400001, 0),
    (42, 29, -3454.65234375, -2209.150390625, 4429.8564453125, 'M001_000_001_SP1;M001_000_001_SP2', 'Lion pirates', 19, 1, 16, 110, 100, 1569, 2701001, 5400001, 0),
    (43, 30, 20340.9921875, -11901.7119140625, 511.68829345703125, 'M011_000_000_SP1;M011_000_000_SP2', 'Desert Eagle', 25, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (44, 33, -5033.64111328125, -12530.1669921875, 4164.88330078125, 'M000_000_001_SP1;M000_000_001_SP2', 'Sediment Wolf', 19, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (45, 33, -8911.7939453125, -14937.2421875, 3571.885009765625, 'M000_000_001_SP1;M000_000_001_SP2', 'Sediment Wolf', 19, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (46, 30, -10866.1005859375, -18732.95703125, 2222.3076171875, 'M011_000_000_SP1;M011_000_000_SP2', 'Desert Eagle', 25, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (47, 30, -14330.3974609375, -19398.423828125, 2082.44189453125, 'M011_000_000_SP1;M011_000_000_SP2', 'Desert Eagle', 25, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (48, 30, 20598.708984375, -8844.66796875, 497.8904113769531, 'M011_000_000_SP1;M011_000_000_SP2', 'Desert Eagle', 25, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (49, 30, 19908.462890625, -4308.9296875, 510.07379150390625, 'M011_000_000_SP1;M011_000_000_SP2', 'Desert Eagle', 25, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (50, 31, -13085.171875, -19977.615234375, 2012.8807373046875, 'M011_000_000_SP3', 'Tornado Eagle', 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (51, 33, 9501.0439453125, -6198.6337890625, 1224.273681640625, 'M000_000_001_SP1;M000_000_001_SP2', 'Sediment Wolf', 19, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (52, 33, 8349.6513671875, -11477.1435546875, 1509.3643798828125, 'M000_000_001_SP1;M000_000_001_SP2', 'Sediment Wolf', 19, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (53, 32, 4840.14208984375, -16955.1328125, 924.340576171875, 'M006_000_000_SP1;M006_000_000_SP2', 'Rock turtle', 23, 1, 16, 164, 100, 2525, 2701001, 5400001, 2802228),
    (54, 33, -249.96929931640625, -11861.9306640625, 3094.955078125, 'M000_000_001_SP1;M000_000_001_SP2', 'Sediment Wolf', 19, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (55, 30, 9124.7275390625, -21878.76953125, 995.5101928710938, 'M011_000_000_SP1;M011_000_000_SP2', 'Desert Eagle', 25, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (56, 30, 13341.11328125, -21878.73046875, 659.9921264648438, 'M011_000_000_SP1;M011_000_000_SP2', 'Desert Eagle', 25, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (57, 30, 17032.955078125, -18020.771484375, 565.7628784179688, 'M011_000_000_SP1;M011_000_000_SP2', 'Desert Eagle', 25, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (58, 34, 18879.498046875, 1349.995361328125, 742.139404296875, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (59, 34, 18530.75390625, 6839.6767578125, 966.080322265625, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (60, 34, 21421.005859375, 9277.1123046875, 590.6787719726562, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (61, 35, 19111.2265625, -1607.8365478515625, 716.8709716796875, 'M025_001_000_BOSS', 'Fighting Fish Sergeant', 27, 1, 16, 352, 100, 3857, 2701001, 5400001, 2802264),
    (62, 32, -1726.652587890625, -19164.966796875, 564.5496826171875, 'M006_000_000_SP1;M006_000_000_SP2', 'Rock turtle', 23, 1, 16, 164, 100, 2525, 2701001, 5400001, 2802228),
    (69, 33, 8191.88232421875, -4096.4951171875, 1863.89111328125, 'M000_000_001_SP1;M000_000_001_SP2', 'Sediment Wolf', 19, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (70, 29, -8426.798828125, 426.71600341796875, 4405.99853515625, 'M001_000_001_SP1;M001_000_001_SP2', 'Lion pirates', 19, 1, 16, 110, 100, 1569, 2701001, 5400001, 0),
    (71, 29, -9559.884765625, 2990.335205078125, 3840.907470703125, 'M001_000_001_SP1;M001_000_001_SP2', 'Lion pirates', 19, 1, 16, 110, 100, 1569, 2701001, 5400001, 0),
    (72, 30, 20015.45703125, -6608.15185546875, 579.5313110351562, 'M011_000_000_SP1;M011_000_000_SP2', 'Desert Eagle', 25, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (73, 30, 15271.048828125, -20091.658203125, 598.2581787109375, 'M011_000_000_SP1;M011_000_000_SP2', 'Desert Eagle', 25, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (74, 30, 11696.0439453125, -21716.974609375, 896.9006958007812, 'M011_000_000_SP1;M011_000_000_SP2', 'Desert Eagle', 25, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (75, 33, 4724.2880859375, -1465.498291015625, 2178.907958984375, 'M000_000_001_SP1;M000_000_001_SP2', 'Sediment Wolf', 19, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (76, 33, 2360.637451171875, 1690.940673828125, 2691.794921875, 'M000_000_001_SP1;M000_000_001_SP2', 'Sediment Wolf', 19, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (77, 31, -10755.2109375, -19645.896484375, 2102.639892578125, 'M011_000_000_SP3', 'Tornado Eagle', 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (78, 31, -15819.3173828125, -19490.04296875, 2092.069580078125, 'M011_000_000_SP3', 'Tornado Eagle', 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (79, 35, 18347.130859375, 6794.07177734375, 985.388671875, 'M025_001_000_BOSS', 'Fighting Fish Sergeant', 27, 1, 16, 352, 100, 3857, 2701001, 5400001, 2802264),
    (80, 35, 19162.310546875, 1337.4029541015625, 708.5288696289062, 'M025_001_000_BOSS', 'Fighting Fish Sergeant', 27, 1, 16, 352, 100, 3857, 2701001, 5400001, 2802264),
    (81, 29, -9434.8642578125, 796.3521728515625, 4436.84423828125, 'M001_000_001_SP1;M001_000_001_SP2', 'Lion pirates', 19, 1, 16, 110, 100, 1569, 2701001, 5400001, 0),
    (82, 33, 6788.8017578125, -3051.13525390625, 2117.647705078125, 'M000_000_001_SP1;M000_000_001_SP2', 'Sediment Wolf', 19, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (83, 28, 5726.9091796875, 3208.04736328125, 2385.8447265625, 'M001_000_000_N;M001_000_000_SP1', 'Drunk wolf pirates', 16, 1, 16, 110, 100, 1054, 2701001, 5400001, 0),
    (84, 29, -11636.51171875, 1761.240478515625, 4462.7490234375, 'M001_000_001_SP1;M001_000_001_SP2', 'Lion pirates', 19, 1, 16, 110, 100, 1569, 2701001, 5400001, 0),
    (85, 32, 1206.410400390625, -19004.802734375, 529.0416259765625, 'M006_000_000_SP1;M006_000_000_SP2', 'Rock turtle', 23, 1, 16, 164, 100, 2525, 2701001, 5400001, 2802228),
    (86, 34, 20485.072265625, 8018.71337890625, 623.4412231445312, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (87, 34, 18747.009765625, 5091.45166015625, 963.4185180664062, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (88, 34, 19234.421875, 2805.1865234375, 849.1326293945312, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
]

# Placements this lane ships as attackable that the hostility predicate does
# NOT select: the named town-target allowlist (a practice dummy is rank 0 and
# has no combat AI, so no predicate over MOBS can pick it out).  Same tuple
# shape as HOSTILE_PLACEMENTS.
TOWN_TARGET_PLACEMENTS = [
]

# EMPTY.  This scene never shipped rows under the older set-number reading
# pending a migration; the list exists so every generated module has the same
# shape.  See bg0001's own module for the scene that did.
LEGACY_SETNUM_PLACEMENTS_PENDING_MIGRATION = [
]

# Which rule produced each shipped row, so no reader has to infer it.
IDENTITY_RULE_PER_PLACEMENT = {
    31: 'cline',
    32: 'cline',
    33: 'cline',
    34: 'cline',
    35: 'cline',
    36: 'cline',
    37: 'cline',
    38: 'cline',
    39: 'cline',
    40: 'cline',
    41: 'cline',
    42: 'cline',
    43: 'cline',
    44: 'cline',
    45: 'cline',
    46: 'cline',
    47: 'cline',
    48: 'cline',
    49: 'cline',
    50: 'cline',
    51: 'cline',
    52: 'cline',
    53: 'cline',
    54: 'cline',
    55: 'cline',
    56: 'cline',
    57: 'cline',
    58: 'cline',
    59: 'cline',
    60: 'cline',
    61: 'cline',
    62: 'cline',
    69: 'cline',
    70: 'cline',
    71: 'cline',
    72: 'cline',
    73: 'cline',
    74: 'cline',
    75: 'cline',
    76: 'cline',
    77: 'cline',
    78: 'cline',
    79: 'cline',
    80: 'cline',
    81: 'cline',
    82: 'cline',
    83: 'cline',
    84: 'cline',
    85: 'cline',
    86: 'cline',
    87: 'cline',
    88: 'cline',
}

# What this lane ships for this scene.  This is the list the roster loader
# reads; the lists above say WHY each row is in it and under which rule.
# Sorted by placement index, because callers downstream build ledgers keyed on
# ``0x2000 + placement_index + 1`` and refuse rows out of ascending order.
SHIPPED_PLACEMENTS = sorted(
    HOSTILE_PLACEMENTS + TOWN_TARGET_PLACEMENTS
    + LEGACY_SETNUM_PLACEMENTS_PENDING_MIGRATION
)

# (placement_index, was_template_id, was_display_name, now_template_id,
#  now_display_name) - placements the OTHER identity rule called hostile here
# and this one does not ship, with who they actually are.  Kept so the cost of
# the rule change is readable per placement instead of as a count.
WITHDRAWN_UNDER_THIS_RULE = [
    (89, 102, 'Orc', 10004, '(no MOBS_TIP name) [not carried: n_id_10004_has_no_avatar_template]'),
    (90, 101, 'Swamp Tortoise', 10003, '(no MOBS_TIP name) [not carried: n_id_10003_has_no_avatar_template]'),
    (92, 103, 'Orc Chief', 917, '(no MOBS_TIP name)'),
    (93, 103, 'Orc Chief', 917, '(no MOBS_TIP name)'),
    (94, 103, 'Orc Chief', 917, '(no MOBS_TIP name)'),
    (95, 103, 'Orc Chief', 917, '(no MOBS_TIP name)'),
    (96, 103, 'Orc Chief', 917, '(no MOBS_TIP name)'),
]

# (placement_index, template_id, display_name, ai_combat) - placements whose
# resolved MOBS row HAS a combat AI but no rank, so the hostility predicate
# does not select them and this lane does not ship them.  Recorded because
# "the town has no monsters" and "nothing in the town has combat AI" are
# different sentences, and only the first one is true.
COMBAT_AI_AT_RANK_ZERO = [
]

# (placement_index, set_number, reason) - placements this scene HAS that this
# identity rule could not read at all.  Carried because "no placement in this
# scene is hostile" is a claim about the rows the rule resolves, and a reader
# is entitled to see the denominator and the skipped rows by name instead of
# a count.  PREDICATE_CENSUS['unambiguous'] plus len(this list) is the scene's
# whole placement count.
UNRESOLVED_PLACEMENTS = [
    (89, 102, 'n_id_10004_has_no_avatar_template'),
    (90, 101, 'n_id_10003_has_no_avatar_template'),
]

