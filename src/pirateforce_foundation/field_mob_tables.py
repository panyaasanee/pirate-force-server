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
    placements     2e5b4115169160d609289d0e638e953d7da16a0000e267c12c118c7c1a4cfc5f
    scene_name     e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b
    standard_mob   4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925

SELECTION CENSUS FOR THIS SCENE (see the generator on why this is printed)
    ai_combat            9
    drops_normal         0
    rank                 0
    rank_and_ai_combat   0
    town_target          4
    unambiguous          140
"""

from __future__ import annotations


SCENE = 'bg0001'
IDENTITY_RULE = 'cline'
SCENE_CLINE_TYPE = 1
SOURCE_DIGESTS = {
    'cline': 'aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40',
    'mobs': '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    'mobs_tip': 'e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f',
    'placements': '2e5b4115169160d609289d0e638e953d7da16a0000e267c12c118c7c1a4cfc5f',
    'scene_name': 'e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b',
    'standard_mob': '4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925',
}
PREDICATE_CENSUS = {
    'ai_combat': 9,
    'drops_normal': 0,
    'rank': 0,
    'rank_and_ai_combat': 0,
    'town_target': 4,
    'unambiguous': 140,
}
# What the crosswalk controls found at mining time.  Recorded, not a check:
# nothing here can re-read CLINE, which lives on the bridge clone.  The
# executable control on this data is the roster loader's own
# assert_frozen_controls, which
# holds these rows against world_port_royal_identity's independently mined
# crosswalk table inside this repository.
CONTROL_FINDINGS = {
    'owner_anchors': '2/2',
    'prison_exile_identity': '35/35',
    'town_target_916_hp': '198125',
}

# The scene file's own Mob-Set number per placement, so a reader can redo the
# resolution by hand: SET_NUMBER_FOR_PLACEMENT[i] -> CLINE -> template_id.
SET_NUMBER_FOR_PLACEMENT = {
    12: 35,
    30: 31,
    33: 34,
    58: 60,
    59: 61,
    60: 62,
    63: 65,
    95: 94,
    103: 97,
    105: 97,
    107: 97,
    109: 97,
    132: 103,
}

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
# Placements whose resolved MOBS row carries BOTH a rank and a combat AI.
HOSTILE_PLACEMENTS = [
]

# Placements this lane ships as attackable that the hostility predicate does
# NOT select: the named town-target allowlist (a practice dummy is rank 0 and
# has no combat AI, so no predicate over MOBS can pick it out).  Same tuple
# shape as HOSTILE_PLACEMENTS.
TOWN_TARGET_PLACEMENTS = [
    (103, 916, 14455.2685546875, 9356.755859375, 2200.45849609375, 'M016_000_000_N', 'Training Iron Man', 100, 0, 21, 0, 150, 198125, 0, 0, 0),
    (105, 916, 13236.265625, 9364.3427734375, 2200.4599609375, 'M016_000_000_N', 'Training Iron Man', 100, 0, 21, 0, 150, 198125, 0, 0, 0),
    (107, 916, 15649.916015625, 9317.12109375, 2200.456298828125, 'M016_000_000_N', 'Training Iron Man', 100, 0, 21, 0, 150, 198125, 0, 0, 0),
    (109, 916, 11789.4384765625, 9318.8798828125, 2200.461181640625, 'M016_000_000_N', 'Training Iron Man', 100, 0, 21, 0, 150, 198125, 0, 0, 0),
]

# !! STILL THE OLD READING, ON PURPOSE, FOR ONE MORE ROUND.
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
    (12, 35, 17961.1796875, 25208.271484375, 452.3008117675781, 'M025_001_000_BOSS', 'Fighting Fish Sergeant', 27, 1, 16, 352, 100, 3857, 2701001, 5400001, 2802264),
    (30, 31, 1747.5244140625, -7837.69775390625, 931.0413208007812, 'M011_000_000_SP3', 'Tornado Eagle', 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (33, 34, -216.15969848632812, 11168.337890625, 575.0142822265625, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (58, 60, -5893.7265625, 15161.7578125, 314.1536865234375, 'M002_000_002_SP3', 'Jungle Big Tiger', 37, 1, 11, 123, 100, 9382, 2701002, 5400002, 2802208),
    (59, 61, 10755.4521484375, 7250.541015625, 2200.4453125, 'M004_000_002_SP1', 'Toxic Vine', 38, 1, 16, 140, 100, 10149, 2701002, 5400002, 2802219),
    (60, 62, 7663.41748046875, 1862.685546875, 2037.39404296875, 'M014_000_000_N', 'Ancient Civilization Alert Weapon', 39, 1, 16, 240, 100, 10962, 2701002, 5400002, 0),
    (63, 65, 9647.2890625, -4765.767578125, 1985.731201171875, 'M003_001_000_SP3', 'Ward Apes', 43, 1, 11, 133, 100, 14910, 2701002, 5400002, 2802215),
    (95, 94, -4945.591796875, 14081.251953125, 314.1182861328125, 'M020_001_000_SP1', 'An Gebo Little Firebird', 47, 1, 16, 300, 100, 19710, 2701003, 5400002, 2802253),
    (132, 103, 3722.39990234375, 21294.939453125, 84.98320007324219, 'M023_000_001_SP3', 'Orc Chief', 58, 1, 11, 332, 100, 38728, 2701003, 5400003, 0),
]

# Which rule produced each shipped row, so no reader has to infer it.
IDENTITY_RULE_PER_PLACEMENT = {
    103: 'cline',
    105: 'cline',
    107: 'cline',
    109: 'cline',
    12: 'setnum',
    30: 'setnum',
    33: 'setnum',
    58: 'setnum',
    59: 'setnum',
    60: 'setnum',
    63: 'setnum',
    95: 'setnum',
    132: 'setnum',
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
    (12, 35, 'Fighting Fish Sergeant', 359, 'Deserter Navy'),
    (30, 31, 'Tornado Eagle', 248, 'Da Vinci'),
    (33, 34, 'Fighting Fish soldier', 358, 'Babu'),
    (58, 60, 'Jungle Big Tiger', 741, 'Juliet'),
    (59, 61, 'Toxic Vine', 796, 'Sase'),
    (60, 62, 'Ancient Civilization Alert Weapon', 797, 'Jonathan'),
    (63, 65, 'Ward Apes', 800, 'Remad'),
    (95, 94, 'An Gebo Little Firebird', 910, 'Saben [not carried: n_id_910_avatar_is_a_variant_list]'),
    (132, 103, 'Orc Chief', 917, '(no MOBS_TIP name)'),
]

# (placement_index, template_id, display_name, ai_combat) - placements whose
# resolved MOBS row HAS a combat AI but no rank, so the hostility predicate
# does not select them and this lane does not ship them.  Recorded because
# "the town has no monsters" and "nothing in the town has combat AI" are
# different sentences, and only the first one is true.
COMBAT_AI_AT_RANK_ZERO = [
    (2, 157, 'Love Millie', 13),
    (96, 918, 'Vera', 14),
    (131, 634, 'Navy Private', 12),
    (133, 634, 'Navy Private', 12),
    (134, 634, 'Navy Private', 12),
    (135, 634, 'Navy Private', 12),
    (136, 634, 'Navy Private', 12),
    (137, 634, 'Navy Private', 12),
    (138, 634, 'Navy Private', 12),
]

# (placement_index, set_number, reason) - placements this scene HAS that this
# identity rule could not read at all.  Carried because "no placement in this
# scene is hostile" is a claim about the rows the rule resolves, and a reader
# is entitled to see the denominator and the skipped rows by name instead of
# a count.  PREDICATE_CENSUS['unambiguous'] plus len(this list) is the scene's
# whole placement count.
UNRESOLVED_PLACEMENTS = [
    (0, 1, 'n_id_155_has_no_MOBS_row'),
    (75, 76, 'n_id_819_has_no_MOBS_row'),
    (83, 101, 'n_id_10002_has_no_avatar_template'),
    (86, 86, 'cline_leader_is_zero_or_absent'),
    (87, 87, 'cline_leader_is_zero_or_absent'),
    (95, 94, 'n_id_910_avatar_is_a_variant_list'),
    (145, 110, 'n_id_9107_has_no_MOBS_row'),
    (147, 112, 'n_id_937_has_no_MOBS_row'),
    (148, 113, 'n_id_942_has_no_MOBS_row'),
]


# ~~The two constants this table used to be checked against.~~  Kept as the
# record of the reading RE-128 replaced: under ``setnum`` this scene's
# placement 30 read as MOBS 31 "Tornado Eagle", level 27, HP 3857 -- the
# values ``v141`` froze as V119_P30_TARGET_NAME / V117_P30_EXACT_HP.  Under
# ``cline`` that placement is Mob-Set 31 -> n_ID 248 "Da Vinci".
LEGACY_SETNUM_READING_OF_PLACEMENT_30 = {
    'template_id': 31, 'display_name': 'Tornado Eagle', 'level': 27,
    'max_hp': 3857,
}
