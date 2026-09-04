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
    placements     5a03747a6cb3c6766fe335863032008c30f82c67dfdc52c701ec44223056ac46
    scene_name     e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b
    standard_mob   4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925

SELECTION CENSUS FOR THIS SCENE (see the generator on why this is printed)
    ai_combat            12
    drops_normal         12
    rank                 12
    rank_and_ai_combat   12
    town_target          0
    unambiguous          37
"""

from __future__ import annotations


SCENE = 'Bg0003'
IDENTITY_RULE = 'cline'
SCENE_CLINE_TYPE = 3
SOURCE_DIGESTS = {
    'cline': 'aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40',
    'mobs': '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    'mobs_tip': 'e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f',
    'placements': '5a03747a6cb3c6766fe335863032008c30f82c67dfdc52c701ec44223056ac46',
    'scene_name': 'e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b',
    'standard_mob': '4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925',
}
PREDICATE_CENSUS = {
    'ai_combat': 12,
    'drops_normal': 12,
    'rank': 12,
    'rank_and_ai_combat': 12,
    'town_target': 0,
    'unambiguous': 37,
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
    27: 26,
    28: 26,
    29: 27,
    33: 30,
    34: 27,
    35: 25,
    39: 34,
    40: 33,
    41: 27,
    42: 27,
    58: 37,
    69: 37,
}

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
# Placements whose resolved MOBS row carries BOTH a rank and a combat AI.
HOSTILE_PLACEMENTS = [
    (27, 61, 21344.287109375, -3283.4951171875, 3806.893310546875, 'M004_000_002_SP1', 'Toxic Vine', 38, 1, 16, 140, 100, 10149, 2701002, 5400002, 2802219),
    (28, 61, 22493.90625, 528.2396850585938, 3779.760986328125, 'M004_000_002_SP1', 'Toxic Vine', 38, 1, 16, 140, 100, 10149, 2701002, 5400002, 2802219),
    (29, 62, 6254.3740234375, -18785.84765625, 3989.9228515625, 'M014_000_000_N', 'Ancient Civilization Alert Weapon', 39, 1, 16, 240, 100, 10962, 2701002, 5400002, 0),
    (33, 65, -19654.26953125, -20399.740234375, 4484.51220703125, 'M003_001_000_SP3', 'Ward Apes', 43, 1, 11, 133, 100, 14910, 2701002, 5400002, 2802215),
    (34, 62, 15594.1728515625, -20767.05078125, 5977.96142578125, 'M014_000_000_N', 'Ancient Civilization Alert Weapon', 39, 1, 16, 240, 100, 10962, 2701002, 5400002, 0),
    (35, 60, 16643.705078125, 7747.16455078125, 2645.375732421875, 'M002_000_002_SP3', 'Jungle Big Tiger', 37, 1, 11, 123, 100, 9382, 2701002, 5400002, 2802208),
    (39, 194, -19164.9375, -12788.56640625, 4082.4619140625, 'M015_001_001_SP1', 'Jet cat thieves No.2', 44, 1, 16, 250, 100, 16009, 2701002, 5400002, 0),
    (40, 515, 16968.025390625, -6367.26025390625, 3993.98095703125, 'M015_001_001_SP1', 'Jet cat thieves No.1', 39, 1, 16, 250, 100, 10962, 2701002, 5400002, 0),
    (41, 62, 12276.7724609375, -7199.38330078125, 3921.6875, 'M014_000_000_N', 'Ancient Civilization Alert Weapon', 39, 1, 16, 240, 100, 10962, 2701002, 5400002, 0),
    (42, 62, 16841.40625, -8830.693359375, 4388.2890625, 'M014_000_000_N', 'Ancient Civilization Alert Weapon', 39, 1, 16, 240, 100, 10962, 2701002, 5400002, 0),
    (58, 907, 10138.8359375, 16399.876953125, 1684.7646484375, 'M000_000_001_SP1', 'Sediment Wolf', 32, 1, 16, 100, 100, 6174, 2701002, 5400002, 0),
    (69, 907, 10634.986328125, 13274.2041015625, 2051.42724609375, 'M000_000_001_SP1', 'Sediment Wolf', 32, 1, 16, 100, 100, 6174, 2701002, 5400002, 0),
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
    27: 'cline',
    28: 'cline',
    29: 'cline',
    33: 'cline',
    34: 'cline',
    35: 'cline',
    39: 'cline',
    40: 'cline',
    41: 'cline',
    42: 'cline',
    58: 'cline',
    69: 'cline',
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
    (37, 31, 'Tornado Eagle', 232, 'Mirage reel'),
    (43, 35, 'Fighting Fish Sergeant', 824, 'Sai Feross'),
    (51, 103, 'Orc Chief', 10007, '(no MOBS_TIP name) [not carried: n_id_10007_has_no_avatar_template]'),
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
    (1, 2, 'n_id_37_has_no_MOBS_row'),
    (18, 20, 'n_id_55_avatar_is_a_variant_list'),
    (19, 20, 'n_id_55_avatar_is_a_variant_list'),
    (20, 21, 'n_id_56_avatar_is_a_variant_list'),
    (21, 21, 'n_id_56_avatar_is_a_variant_list'),
    (22, 22, 'n_id_57_avatar_is_a_variant_list'),
    (23, 22, 'n_id_57_avatar_is_a_variant_list'),
    (24, 23, 'n_id_58_avatar_is_a_variant_list'),
    (25, 23, 'n_id_58_avatar_is_a_variant_list'),
    (26, 24, 'n_id_59_avatar_is_a_variant_list'),
    (30, 28, 'n_id_63_avatar_is_a_variant_list'),
    (31, 28, 'n_id_63_avatar_is_a_variant_list'),
    (32, 29, 'n_id_64_avatar_is_a_variant_list'),
    (45, 20, 'n_id_55_avatar_is_a_variant_list'),
    (46, 20, 'n_id_55_avatar_is_a_variant_list'),
    (47, 20, 'n_id_55_avatar_is_a_variant_list'),
    (48, 20, 'n_id_55_avatar_is_a_variant_list'),
    (49, 101, 'n_id_10005_has_no_avatar_template'),
    (50, 102, 'n_id_10006_has_no_avatar_template'),
    (51, 103, 'n_id_10007_has_no_avatar_template'),
    (52, 104, 'n_id_10008_has_no_avatar_template'),
    (53, 105, 'n_id_10009_has_no_avatar_template'),
    (54, 106, 'n_id_10010_has_no_avatar_template'),
    (55, 107, 'n_id_10011_has_no_avatar_template'),
    (56, 108, 'n_id_10012_has_no_avatar_template'),
    (57, 109, 'n_id_10013_has_no_avatar_template'),
    (59, 38, 'n_id_908_avatar_is_a_variant_list'),
    (62, 21, 'n_id_56_avatar_is_a_variant_list'),
    (63, 21, 'n_id_56_avatar_is_a_variant_list'),
    (64, 28, 'n_id_63_avatar_is_a_variant_list'),
    (65, 29, 'n_id_64_avatar_is_a_variant_list'),
    (66, 28, 'n_id_63_avatar_is_a_variant_list'),
    (67, 24, 'n_id_59_avatar_is_a_variant_list'),
    (68, 38, 'n_id_908_avatar_is_a_variant_list'),
    (71, 111, 'n_id_7042_avatar_is_a_variant_list'),
]

