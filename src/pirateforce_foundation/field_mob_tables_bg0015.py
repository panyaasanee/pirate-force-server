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
    placements     8ef794f9ccbeae1154eb8466c3e43c3d605ca6a620e2e5c936e0af46cb51bb83
    scene_name     e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b
    standard_mob   4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925

SELECTION CENSUS FOR THIS SCENE (see the generator on why this is printed)
    ai_combat            12
    drops_normal         11
    rank                 12
    rank_and_ai_combat   12
    town_target          0
    unambiguous          36
"""

from __future__ import annotations


SCENE = 'Bg0015'
IDENTITY_RULE = 'cline'
SCENE_CLINE_TYPE = 14
SOURCE_DIGESTS = {
    'cline': 'aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40',
    'mobs': '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    'mobs_tip': 'e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f',
    'placements': '8ef794f9ccbeae1154eb8466c3e43c3d605ca6a620e2e5c936e0af46cb51bb83',
    'scene_name': 'e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b',
    'standard_mob': '4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925',
}
PREDICATE_CENSUS = {
    'ai_combat': 12,
    'drops_normal': 11,
    'rank': 12,
    'rank_and_ai_combat': 12,
    'town_target': 0,
    'unambiguous': 36,
}
# What the crosswalk controls found at mining time.  Recorded, not a check:
# nothing here can re-read CLINE, which lives on the bridge clone.  The
# executable control on this data is the roster loader's own
# assert_frozen_controls, which
# holds these rows against world_port_royal_identity's independently mined
# crosswalk table inside this repository.
CONTROL_FINDINGS = {
    'prison_exile_identity': '35/35',
    'town_target_916_hp': '198125',
}

# The scene file's own Mob-Set number per placement, so a reader can redo the
# resolution by hand: SET_NUMBER_FOR_PLACEMENT[i] -> CLINE -> template_id.
SET_NUMBER_FOR_PLACEMENT = {
    22: 23,
    24: 25,
    27: 28,
    29: 30,
    31: 33,
    44: 23,
    45: 23,
    46: 23,
    47: 23,
    51: 23,
    70: 35,
    87: 112,
}

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
# Placements whose resolved MOBS row carries BOTH a rank and a combat AI.
HOSTILE_PLACEMENTS = [
    (22, 343, -11200.365234375, -598.9420776367188, 2447.830322265625, 'M020_000_000_N', 'Glaucoma', 105, 1, 16, 301, 100, 228055, 2701010, 5400004, 2802250),
    (24, 345, -12794.1201171875, -19500.970703125, 4982.83740234375, 'M022_000_001_SP3', 'Phosphor Fascinator', 105, 1, 11, 323, 100, 228055, 2701010, 5400004, 0),
    (27, 348, 17688.904296875, 14799.4130859375, 2223.9462890625, 'M000_001_001_SP3', 'Crimson Sharp Teeth', 105, 1, 11, 102, 100, 228055, 2701010, 5400004, 2802205),
    (29, 350, 12026.26171875, 23254.26171875, 2673.939697265625, 'M017_000_002_SP3', 'Arbiter Bells', 105, 1, 11, 273, 100, 228055, 2701010, 5400004, 0),
    (31, 353, 11665.1416015625, -1562.874755859375, 4365.74462890625, 'M003_000_003_SP3', 'Lava shakers', 105, 1, 11, 134, 100, 228055, 2701010, 5400004, 2802214),
    (44, 343, -12168.4912109375, -3187.351318359375, 2486.368408203125, 'M020_000_000_N', 'Glaucoma', 105, 1, 16, 301, 100, 228055, 2701010, 5400004, 2802250),
    (45, 343, -10052.9736328125, -7851.99609375, 2401.858154296875, 'M020_000_000_N', 'Glaucoma', 105, 1, 16, 301, 100, 228055, 2701010, 5400004, 2802250),
    (46, 343, -11553.9150390625, -5713.6767578125, 2327.19189453125, 'M020_000_000_N', 'Glaucoma', 105, 1, 16, 301, 100, 228055, 2701010, 5400004, 2802250),
    (47, 343, -8906.2294921875, -10704.669921875, 3154.77587890625, 'M020_000_000_N', 'Glaucoma', 105, 1, 16, 301, 100, 228055, 2701010, 5400004, 2802250),
    (51, 343, -13532.3935546875, -13779.04296875, 3239.51806640625, 'M020_000_000_N', 'Glaucoma', 105, 1, 16, 301, 100, 228055, 2701010, 5400004, 2802250),
    (70, 355, -6298.55322265625, -20541.8125, 6598.4580078125, 'M023_001_000_SP3', 'Horror butcher Lasa', 105, 1, 11, 333, 100, 228055, 2701010, 5400004, 0),
    (87, 924, 10159.2294921875, -39.96989822387695, 4421.5224609375, 'P_MALE_033_000_CARLOS', 'Carlos', 115, 1, 22, 472, 150, 296546, 0, 0, 0),
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
    22: 'cline',
    24: 'cline',
    27: 'cline',
    29: 'cline',
    31: 'cline',
    44: 'cline',
    45: 'cline',
    46: 'cline',
    47: 'cline',
    51: 'cline',
    70: 'cline',
    87: 'cline',
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
    (30, 31, 'Tornado Eagle', 351, 'Earth Flame Dragon [not carried: n_id_351_avatar_is_a_variant_list]'),
    (59, 31, 'Tornado Eagle', 351, 'Earth Flame Dragon [not carried: n_id_351_avatar_is_a_variant_list]'),
    (61, 34, 'Fighting Fish soldier', 354, 'Hell Ghoul [not carried: n_id_354_avatar_is_a_variant_list]'),
    (62, 34, 'Fighting Fish soldier', 354, 'Hell Ghoul [not carried: n_id_354_avatar_is_a_variant_list]'),
    (63, 34, 'Fighting Fish soldier', 354, 'Hell Ghoul [not carried: n_id_354_avatar_is_a_variant_list]'),
    (64, 34, 'Fighting Fish soldier', 354, 'Hell Ghoul [not carried: n_id_354_avatar_is_a_variant_list]'),
    (65, 31, 'Tornado Eagle', 351, 'Earth Flame Dragon [not carried: n_id_351_avatar_is_a_variant_list]'),
    (66, 31, 'Tornado Eagle', 351, 'Earth Flame Dragon [not carried: n_id_351_avatar_is_a_variant_list]'),
    (67, 34, 'Fighting Fish soldier', 354, 'Hell Ghoul [not carried: n_id_354_avatar_is_a_variant_list]'),
    (68, 34, 'Fighting Fish soldier', 354, 'Hell Ghoul [not carried: n_id_354_avatar_is_a_variant_list]'),
    (69, 34, 'Fighting Fish soldier', 354, 'Hell Ghoul [not carried: n_id_354_avatar_is_a_variant_list]'),
    (71, 34, 'Fighting Fish soldier', 354, 'Hell Ghoul [not carried: n_id_354_avatar_is_a_variant_list]'),
    (72, 34, 'Fighting Fish soldier', 354, 'Hell Ghoul [not carried: n_id_354_avatar_is_a_variant_list]'),
    (73, 34, 'Fighting Fish soldier', 354, 'Hell Ghoul [not carried: n_id_354_avatar_is_a_variant_list]'),
    (74, 34, 'Fighting Fish soldier', 354, 'Hell Ghoul [not carried: n_id_354_avatar_is_a_variant_list]'),
    (78, 103, 'Orc Chief', 10065, '(no MOBS_TIP name) [not carried: n_id_10065_has_no_avatar_template]'),
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
    (0, 1, 'n_id_321_has_no_MOBS_row'),
    (19, 20, 'n_id_340_avatar_is_a_variant_list'),
    (20, 21, 'n_id_341_avatar_is_a_variant_list'),
    (21, 22, 'n_id_342_avatar_is_a_variant_list'),
    (23, 24, 'n_id_344_avatar_is_a_variant_list'),
    (25, 26, 'n_id_346_avatar_is_a_variant_list'),
    (26, 27, 'n_id_347_avatar_is_a_variant_list'),
    (28, 29, 'n_id_349_avatar_is_a_variant_list'),
    (30, 31, 'n_id_351_avatar_is_a_variant_list'),
    (32, 32, 'n_id_352_avatar_is_a_variant_list'),
    (33, 32, 'n_id_352_avatar_is_a_variant_list'),
    (34, 20, 'n_id_340_avatar_is_a_variant_list'),
    (35, 20, 'n_id_340_avatar_is_a_variant_list'),
    (36, 20, 'n_id_340_avatar_is_a_variant_list'),
    (37, 21, 'n_id_341_avatar_is_a_variant_list'),
    (38, 21, 'n_id_341_avatar_is_a_variant_list'),
    (39, 21, 'n_id_341_avatar_is_a_variant_list'),
    (40, 21, 'n_id_341_avatar_is_a_variant_list'),
    (41, 22, 'n_id_342_avatar_is_a_variant_list'),
    (42, 22, 'n_id_342_avatar_is_a_variant_list'),
    (43, 22, 'n_id_342_avatar_is_a_variant_list'),
    (48, 24, 'n_id_344_avatar_is_a_variant_list'),
    (49, 24, 'n_id_344_avatar_is_a_variant_list'),
    (50, 24, 'n_id_344_avatar_is_a_variant_list'),
    (52, 24, 'n_id_344_avatar_is_a_variant_list'),
    (53, 26, 'n_id_346_avatar_is_a_variant_list'),
    (54, 26, 'n_id_346_avatar_is_a_variant_list'),
    (55, 26, 'n_id_346_avatar_is_a_variant_list'),
    (56, 27, 'n_id_347_avatar_is_a_variant_list'),
    (57, 27, 'n_id_347_avatar_is_a_variant_list'),
    (58, 29, 'n_id_349_avatar_is_a_variant_list'),
    (59, 31, 'n_id_351_avatar_is_a_variant_list'),
    (60, 32, 'n_id_352_avatar_is_a_variant_list'),
    (61, 34, 'n_id_354_avatar_is_a_variant_list'),
    (62, 34, 'n_id_354_avatar_is_a_variant_list'),
    (63, 34, 'n_id_354_avatar_is_a_variant_list'),
    (64, 34, 'n_id_354_avatar_is_a_variant_list'),
    (65, 31, 'n_id_351_avatar_is_a_variant_list'),
    (66, 31, 'n_id_351_avatar_is_a_variant_list'),
    (67, 34, 'n_id_354_avatar_is_a_variant_list'),
    (68, 34, 'n_id_354_avatar_is_a_variant_list'),
    (69, 34, 'n_id_354_avatar_is_a_variant_list'),
    (71, 34, 'n_id_354_avatar_is_a_variant_list'),
    (72, 34, 'n_id_354_avatar_is_a_variant_list'),
    (73, 34, 'n_id_354_avatar_is_a_variant_list'),
    (74, 34, 'n_id_354_avatar_is_a_variant_list'),
    (76, 101, 'n_id_10063_has_no_avatar_template'),
    (77, 102, 'n_id_10064_has_no_avatar_template'),
    (78, 103, 'n_id_10065_has_no_avatar_template'),
    (79, 104, 'n_id_10066_has_no_avatar_template'),
    (80, 105, 'n_id_10067_has_no_avatar_template'),
    (81, 106, 'n_id_10068_has_no_avatar_template'),
    (82, 107, 'n_id_10069_has_no_avatar_template'),
    (83, 108, 'n_id_10070_has_no_avatar_template'),
    (90, 115, 'n_id_944_has_no_MOBS_row'),
]

