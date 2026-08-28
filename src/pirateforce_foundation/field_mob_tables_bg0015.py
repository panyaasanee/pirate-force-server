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
    ai_combat            17
    drops_normal         17
    rank                 17
    rank_and_ai_combat   17
    town_target          0
    unambiguous          76
"""

from __future__ import annotations


SCENE = 'Bg0015'
IDENTITY_RULE = 'setnum'
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
    'ai_combat': 17,
    'drops_normal': 17,
    'rank': 17,
    'rank_and_ai_combat': 17,
    'town_target': 0,
    'unambiguous': 76,
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
    30: 31,
    59: 31,
    61: 34,
    62: 34,
    63: 34,
    64: 34,
    65: 31,
    66: 31,
    67: 34,
    68: 34,
    69: 34,
    70: 35,
    71: 34,
    72: 34,
    73: 34,
    74: 34,
    78: 103,
}

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
# Placements whose resolved MOBS row carries BOTH a rank and a combat AI.
HOSTILE_PLACEMENTS = [
    (30, 31, 6036.5810546875, 202.87680053710938, 4542.48388671875, 'M011_000_000_SP3', 'Tornado Eagle', 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (59, 31, 8397.12109375, 3205.90673828125, 4552.0234375, 'M011_000_000_SP3', 'Tornado Eagle', 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (61, 34, -1718.2618408203125, -6423.5595703125, 3756.145263671875, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (62, 34, 995.7576293945312, -7947.04638671875, 4291.10498046875, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (63, 34, -1300.1986083984375, -3309.963623046875, 3282.133544921875, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (64, 34, -2821.444091796875, -9737.005859375, 4235.8583984375, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (65, 31, 3500.207763671875, -1302.6533203125, 4519.55908203125, 'M011_000_000_SP3', 'Tornado Eagle', 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (66, 31, 2197.726806640625, -3225.654296875, 4562.68896484375, 'M011_000_000_SP3', 'Tornado Eagle', 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (67, 34, 5134.92529296875, -12188.62890625, 6195.76025390625, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (68, 34, 7985.09130859375, -15373.0537109375, 6277.93212890625, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (69, 34, 7736.89111328125, -13725.8779296875, 6233.88916015625, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (70, 35, -6298.55322265625, -20541.8125, 6598.4580078125, 'M025_001_000_BOSS', 'Fighting Fish Sergeant', 27, 1, 16, 352, 100, 3857, 2701001, 5400001, 2802264),
    (71, 34, 7127.57568359375, -23162.279296875, 6414.27294921875, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (72, 34, 1032.052978515625, -21807.556640625, 5882.146484375, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (73, 34, 2382.00341796875, -21163.001953125, 5844.23974609375, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (74, 34, -3058.61328125, -20289.9296875, 6767.0615234375, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (78, 103, -10183.431640625, 19154.37109375, 894.6489868164062, 'M023_000_001_SP3', 'Orc Chief', 58, 1, 11, 332, 100, 38728, 2701003, 5400003, 0),
]

# Placements this lane ships as attackable that the hostility predicate does
# NOT select: the named town-target allowlist (a practice dummy is rank 0 and
# has no combat AI, so no predicate over MOBS can pick it out).  Same tuple
# shape as HOSTILE_PLACEMENTS.
TOWN_TARGET_PLACEMENTS = [
]

# Rows the previous
# identity rule selected here that this rule withdraws (they are townspeople,
# see WITHDRAWN_UNDER_THIS_RULE for who each one really is).  They are kept in
# what this lane ships because dropping them in the same round that corrects
# the four town targets would take ~840 pinned assertions with it, and a
# migration that big lands red or lands half-done.  So the round that could
# only do one did the one with a standing COO ruling behind it, and named the
# rest instead of quietly shipping it as if it were resolved.
# NOTHING HERE IS A CLAIM THAT THESE NAMES ARE RIGHT - the module says the
# opposite, per row, in WITHDRAWN_UNDER_THIS_RULE.
LEGACY_SETNUM_PLACEMENTS_PENDING_MIGRATION = [
]

# Which rule produced each shipped row, so no reader has to infer it.
IDENTITY_RULE_PER_PLACEMENT = {
    30: 'setnum',
    59: 'setnum',
    61: 'setnum',
    62: 'setnum',
    63: 'setnum',
    64: 'setnum',
    65: 'setnum',
    66: 'setnum',
    67: 'setnum',
    68: 'setnum',
    69: 'setnum',
    70: 'setnum',
    71: 'setnum',
    72: 'setnum',
    73: 'setnum',
    74: 'setnum',
    78: 'setnum',
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
    (22, 343, 'Glaucoma', 23, 'Seven'),
    (24, 345, 'Phosphor Fascinator', 25, 'Odyssey'),
    (27, 348, 'Crimson Sharp Teeth', 28, 'Drunk wolf pirates [not carried: n_id_28_avatar_is_a_variant_list]'),
    (29, 350, 'Arbiter Bells', 30, 'Desert Eagle [not carried: n_id_30_avatar_is_a_variant_list]'),
    (31, 353, 'Lava shakers', 33, 'Sediment Wolf [not carried: n_id_33_avatar_is_a_variant_list]'),
    (44, 343, 'Glaucoma', 23, 'Seven'),
    (45, 343, 'Glaucoma', 23, 'Seven'),
    (46, 343, 'Glaucoma', 23, 'Seven'),
    (47, 343, 'Glaucoma', 23, 'Seven'),
    (51, 343, 'Glaucoma', 23, 'Seven'),
    (87, 924, 'Carlos', 112, 'Rude pirates'),
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
    (26, 27, 'n_id_27_avatar_is_a_variant_list'),
    (27, 28, 'n_id_28_avatar_is_a_variant_list'),
    (28, 29, 'n_id_29_avatar_is_a_variant_list'),
    (29, 30, 'n_id_30_avatar_is_a_variant_list'),
    (31, 33, 'n_id_33_avatar_is_a_variant_list'),
    (32, 32, 'n_id_32_avatar_is_a_variant_list'),
    (33, 32, 'n_id_32_avatar_is_a_variant_list'),
    (56, 27, 'n_id_27_avatar_is_a_variant_list'),
    (57, 27, 'n_id_27_avatar_is_a_variant_list'),
    (58, 29, 'n_id_29_avatar_is_a_variant_list'),
    (60, 32, 'n_id_32_avatar_is_a_variant_list'),
    (76, 101, 'n_id_101_avatar_is_a_variant_list'),
    (77, 102, 'n_id_102_avatar_is_a_variant_list'),
    (79, 104, 'n_id_104_has_no_MOBS_row'),
]

