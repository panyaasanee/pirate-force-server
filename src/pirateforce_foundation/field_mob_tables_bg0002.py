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
    ai_combat            17
    drops_normal         17
    rank                 17
    rank_and_ai_combat   17
    town_target          0
    unambiguous          49
"""

from __future__ import annotations


SCENE = 'Bg0002'
IDENTITY_RULE = 'setnum'
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
    'ai_combat': 17,
    'drops_normal': 17,
    'rank': 17,
    'rank_and_ai_combat': 17,
    'town_target': 0,
    'unambiguous': 49,
}
# What the crosswalk controls found at mining time.  Recorded, not a check:
# nothing here can re-read CLINE, which lives on the bridge clone.  The
# executable control on this data is the roster loader's own
# assert_frozen_controls, which
# holds these rows against world_port_royal_identity's independently mined
# crosswalk table inside this repository.
CONTROL_FINDINGS = {
    'legacy_setnum_controls': 're-derived',
}

# The scene file's own Mob-Set number per placement, so a reader can redo the
# resolution by hand: SET_NUMBER_FOR_PLACEMENT[i] -> CLINE -> template_id.
SET_NUMBER_FOR_PLACEMENT = {
    50: 31,
    58: 34,
    59: 34,
    60: 34,
    61: 35,
    77: 31,
    78: 31,
    79: 35,
    80: 35,
    86: 34,
    87: 34,
    88: 34,
    92: 103,
    93: 103,
    94: 103,
    95: 103,
    96: 103,
}

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
# Placements whose resolved MOBS row carries BOTH a rank and a combat AI.
HOSTILE_PLACEMENTS = [
    (50, 31, -13085.171875, -19977.615234375, 2012.8807373046875, 'M011_000_000_SP3', 'Tornado Eagle', 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (58, 34, 18879.498046875, 1349.995361328125, 742.139404296875, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (59, 34, 18530.75390625, 6839.6767578125, 966.080322265625, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (60, 34, 21421.005859375, 9277.1123046875, 590.6787719726562, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (61, 35, 19111.2265625, -1607.8365478515625, 716.8709716796875, 'M025_001_000_BOSS', 'Fighting Fish Sergeant', 27, 1, 16, 352, 100, 3857, 2701001, 5400001, 2802264),
    (77, 31, -10755.2109375, -19645.896484375, 2102.639892578125, 'M011_000_000_SP3', 'Tornado Eagle', 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (78, 31, -15819.3173828125, -19490.04296875, 2092.069580078125, 'M011_000_000_SP3', 'Tornado Eagle', 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (79, 35, 18347.130859375, 6794.07177734375, 985.388671875, 'M025_001_000_BOSS', 'Fighting Fish Sergeant', 27, 1, 16, 352, 100, 3857, 2701001, 5400001, 2802264),
    (80, 35, 19162.310546875, 1337.4029541015625, 708.5288696289062, 'M025_001_000_BOSS', 'Fighting Fish Sergeant', 27, 1, 16, 352, 100, 3857, 2701001, 5400001, 2802264),
    (86, 34, 20485.072265625, 8018.71337890625, 623.4412231445312, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (87, 34, 18747.009765625, 5091.45166015625, 963.4185180664062, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (88, 34, 19234.421875, 2805.1865234375, 849.1326293945312, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (92, 103, 17870.701171875, 6142.2685546875, 946.0828857421875, 'M023_000_001_SP3', 'Orc Chief', 58, 1, 11, 332, 100, 38728, 2701003, 5400003, 0),
    (93, 103, 17646.60546875, 5751.74072265625, 1472.725830078125, 'M023_000_001_SP3', 'Orc Chief', 58, 1, 11, 332, 100, 38728, 2701003, 5400003, 0),
    (94, 103, 17927.32421875, 5449.716796875, 920.7349853515625, 'M023_000_001_SP3', 'Orc Chief', 58, 1, 11, 332, 100, 38728, 2701003, 5400003, 0),
    (95, 103, 17194.107421875, 6104.9345703125, 1016.1411743164062, 'M023_000_001_SP3', 'Orc Chief', 58, 1, 11, 332, 100, 38728, 2701003, 5400003, 0),
    (96, 103, 17243.01171875, 5434.12158203125, 979.5286254882812, 'M023_000_001_SP3', 'Orc Chief', 58, 1, 11, 332, 100, 38728, 2701003, 5400003, 0),
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
    50: 'setnum',
    58: 'setnum',
    59: 'setnum',
    60: 'setnum',
    61: 'setnum',
    77: 'setnum',
    78: 'setnum',
    79: 'setnum',
    80: 'setnum',
    86: 'setnum',
    87: 'setnum',
    88: 'setnum',
    92: 'setnum',
    93: 'setnum',
    94: 'setnum',
    95: 'setnum',
    96: 'setnum',
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
    (2, 3, 'n_id_3_avatar_is_a_variant_list'),
    (3, 3, 'n_id_3_avatar_is_a_variant_list'),
    (4, 3, 'n_id_3_avatar_is_a_variant_list'),
    (5, 3, 'n_id_3_avatar_is_a_variant_list'),
    (31, 28, 'n_id_28_avatar_is_a_variant_list'),
    (32, 28, 'n_id_28_avatar_is_a_variant_list'),
    (33, 28, 'n_id_28_avatar_is_a_variant_list'),
    (34, 28, 'n_id_28_avatar_is_a_variant_list'),
    (35, 28, 'n_id_28_avatar_is_a_variant_list'),
    (36, 27, 'n_id_27_avatar_is_a_variant_list'),
    (37, 27, 'n_id_27_avatar_is_a_variant_list'),
    (38, 27, 'n_id_27_avatar_is_a_variant_list'),
    (39, 27, 'n_id_27_avatar_is_a_variant_list'),
    (40, 29, 'n_id_29_avatar_is_a_variant_list'),
    (41, 29, 'n_id_29_avatar_is_a_variant_list'),
    (42, 29, 'n_id_29_avatar_is_a_variant_list'),
    (43, 30, 'n_id_30_avatar_is_a_variant_list'),
    (44, 33, 'n_id_33_avatar_is_a_variant_list'),
    (45, 33, 'n_id_33_avatar_is_a_variant_list'),
    (46, 30, 'n_id_30_avatar_is_a_variant_list'),
    (47, 30, 'n_id_30_avatar_is_a_variant_list'),
    (48, 30, 'n_id_30_avatar_is_a_variant_list'),
    (49, 30, 'n_id_30_avatar_is_a_variant_list'),
    (51, 33, 'n_id_33_avatar_is_a_variant_list'),
    (52, 33, 'n_id_33_avatar_is_a_variant_list'),
    (53, 32, 'n_id_32_avatar_is_a_variant_list'),
    (54, 33, 'n_id_33_avatar_is_a_variant_list'),
    (55, 30, 'n_id_30_avatar_is_a_variant_list'),
    (56, 30, 'n_id_30_avatar_is_a_variant_list'),
    (57, 30, 'n_id_30_avatar_is_a_variant_list'),
    (62, 32, 'n_id_32_avatar_is_a_variant_list'),
    (65, 37, 'n_id_37_has_no_MOBS_row'),
    (66, 3, 'n_id_3_avatar_is_a_variant_list'),
    (69, 33, 'n_id_33_avatar_is_a_variant_list'),
    (70, 29, 'n_id_29_avatar_is_a_variant_list'),
    (71, 29, 'n_id_29_avatar_is_a_variant_list'),
    (72, 30, 'n_id_30_avatar_is_a_variant_list'),
    (73, 30, 'n_id_30_avatar_is_a_variant_list'),
    (74, 30, 'n_id_30_avatar_is_a_variant_list'),
    (75, 33, 'n_id_33_avatar_is_a_variant_list'),
    (76, 33, 'n_id_33_avatar_is_a_variant_list'),
    (81, 29, 'n_id_29_avatar_is_a_variant_list'),
    (82, 33, 'n_id_33_avatar_is_a_variant_list'),
    (83, 28, 'n_id_28_avatar_is_a_variant_list'),
    (84, 29, 'n_id_29_avatar_is_a_variant_list'),
    (85, 32, 'n_id_32_avatar_is_a_variant_list'),
    (89, 102, 'n_id_102_avatar_is_a_variant_list'),
    (90, 101, 'n_id_101_avatar_is_a_variant_list'),
    (97, 104, 'n_id_104_has_no_MOBS_row'),
    (98, 3, 'n_id_3_avatar_is_a_variant_list'),
    (99, 3, 'n_id_3_avatar_is_a_variant_list'),
    (100, 3, 'n_id_3_avatar_is_a_variant_list'),
    (101, 3, 'n_id_3_avatar_is_a_variant_list'),
    (102, 3, 'n_id_3_avatar_is_a_variant_list'),
    (103, 3, 'n_id_3_avatar_is_a_variant_list'),
    (104, 3, 'n_id_3_avatar_is_a_variant_list'),
    (105, 3, 'n_id_3_avatar_is_a_variant_list'),
]

