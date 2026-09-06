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
    placements     71011ddc6cc9af824a1c44124022ce5ae04ba41bf8745c55aed6a9274f2187cd
    scene_name     e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b
    standard_mob   4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925

SELECTION CENSUS FOR THIS SCENE (see the generator on why this is printed)
    ai_combat            17
    drops_normal         17
    rank                 17
    rank_and_ai_combat   17
    town_target          0
    unambiguous          35
"""

from __future__ import annotations


SCENE = 'Bg0010'
IDENTITY_RULE = 'cline'
SCENE_CLINE_TYPE = 10
SOURCE_DIGESTS = {
    'cline': 'aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40',
    'mobs': '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    'mobs_tip': 'e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f',
    'placements': '71011ddc6cc9af824a1c44124022ce5ae04ba41bf8745c55aed6a9274f2187cd',
    'scene_name': 'e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b',
    'standard_mob': '4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925',
}
PREDICATE_CENSUS = {
    'ai_combat': 17,
    'drops_normal': 17,
    'rank': 17,
    'rank_and_ai_combat': 17,
    'town_target': 0,
    'unambiguous': 35,
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
    24: 19,
    31: 17,
    32: 18,
    39: 25,
    46: 29,
    47: 27,
    48: 27,
    90: 18,
    91: 18,
    92: 18,
    93: 18,
    94: 18,
    95: 18,
    96: 19,
    97: 19,
    98: 19,
    99: 19,
}

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
# Placements whose resolved MOBS row carries BOTH a rank and a combat AI.
HOSTILE_PLACEMENTS = [
    (24, 662, -646.5667724609375, 10672.0400390625, 507.20849609375, 'M000_001_000_SP3', 'Abyss Demon Wolf', 99, 1, 11, 102, 100, 192488, 2701009, 5400031, 2802204),
    (31, 660, 18040.51171875, -1351.5966796875, 518.0941772460938, 'M026_000_001_SP3', 'Skeleton Commander Lebiya', 99, 1, 11, 362, 100, 192488, 2701009, 5400031, 0),
    (32, 661, 18162.3203125, -390.3909912109375, 517.921875, 'M000_001_000_SP2', 'Exotic Demon Wolf', 99, 1, 16, 100, 100, 192488, 2701009, 5400031, 2802204),
    (39, 668, -16490.47265625, -16926.20703125, -4474.47314453125, 'M018_000_000_N', 'Navy Two Tripods', 99, 1, 16, 280, 100, 192488, 2701009, 5400031, 2802244),
    (46, 673, -15906.484375, -24835.26171875, -4423.37060546875, 'M021_000_000_SP3', 'Seabed Wanderer', 99, 1, 11, 315, 100, 192488, 2701009, 5400031, 2802256),
    (47, 671, -13489.8505859375, -3254.76416015625, -4435.94091796875, 'M020_000_001_SP1', 'Crusty Bone Fish', 99, 1, 16, 301, 100, 192488, 2701009, 5400031, 2802251),
    (48, 671, -17285.3046875, 37.502201080322266, -4256.94091796875, 'M020_000_001_SP1', 'Crusty Bone Fish', 99, 1, 16, 301, 100, 192488, 2701009, 5400031, 2802251),
    (90, 661, 18132.693359375, -2144.323486328125, 536.9204711914062, 'M000_001_000_SP2', 'Exotic Demon Wolf', 99, 1, 16, 100, 100, 192488, 2701009, 5400031, 2802204),
    (91, 661, 17020.2109375, -1360.697509765625, 528.9210815429688, 'M000_001_000_SP2', 'Exotic Demon Wolf', 99, 1, 16, 100, 100, 192488, 2701009, 5400031, 2802204),
    (92, 661, 14737.1171875, -574.6121826171875, 517.92041015625, 'M000_001_000_SP2', 'Exotic Demon Wolf', 99, 1, 16, 100, 100, 192488, 2701009, 5400031, 2802204),
    (93, 661, 13602.69921875, -1800.505126953125, 515.9216918945312, 'M000_001_000_SP2', 'Exotic Demon Wolf', 99, 1, 16, 100, 100, 192488, 2701009, 5400031, 2802204),
    (94, 661, 12802.80859375, -492.20208740234375, 516.9208984375, 'M000_001_000_SP2', 'Exotic Demon Wolf', 99, 1, 16, 100, 100, 192488, 2701009, 5400031, 2802204),
    (95, 661, 15415.568359375, 1949.245849609375, 744.3201293945312, 'M000_001_000_SP2', 'Exotic Demon Wolf', 99, 1, 16, 100, 100, 192488, 2701009, 5400031, 2802204),
    (96, 662, -1746.46630859375, 12049.8876953125, 419.6430969238281, 'M000_001_000_SP3', 'Abyss Demon Wolf', 99, 1, 11, 102, 100, 192488, 2701009, 5400031, 2802204),
    (97, 662, -273.4700927734375, 12937.83203125, 433.6429138183594, 'M000_001_000_SP3', 'Abyss Demon Wolf', 99, 1, 11, 102, 100, 192488, 2701009, 5400031, 2802204),
    (98, 662, -1594.5361328125, 14055.3583984375, 433.6430969238281, 'M000_001_000_SP3', 'Abyss Demon Wolf', 99, 1, 11, 102, 100, 192488, 2701009, 5400031, 2802204),
    (99, 662, -262.4346008300781, 15402.984375, 442.6430969238281, 'M000_001_000_SP3', 'Abyss Demon Wolf', 99, 1, 11, 102, 100, 192488, 2701009, 5400031, 2802204),
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
    24: 'cline',
    31: 'cline',
    32: 'cline',
    39: 'cline',
    46: 'cline',
    47: 'cline',
    48: 'cline',
    90: 'cline',
    91: 'cline',
    92: 'cline',
    93: 'cline',
    94: 'cline',
    95: 'cline',
    96: 'cline',
    97: 'cline',
    98: 'cline',
    99: 'cline',
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
    (57, 31, 'Tornado Eagle', 836, 'Concentration camp prisoner'),
    (62, 34, 'Fighting Fish soldier', 839, 'Coma Guard'),
    (63, 34, 'Fighting Fish soldier', 839, 'Coma Guard'),
    (65, 35, 'Fighting Fish Sergeant', 841, 'Concentration camp prisoner [not carried: n_id_841_avatar_is_a_variant_list]'),
    (68, 103, 'Orc Chief', 10055, '(no MOBS_TIP name) [not carried: n_id_10055_has_no_avatar_template]'),
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
    (12, 14, 'n_id_657_avatar_is_a_variant_list'),
    (13, 14, 'n_id_657_avatar_is_a_variant_list'),
    (14, 14, 'n_id_657_avatar_is_a_variant_list'),
    (15, 14, 'n_id_657_avatar_is_a_variant_list'),
    (16, 15, 'n_id_658_avatar_is_a_variant_list'),
    (17, 15, 'n_id_658_avatar_is_a_variant_list'),
    (18, 15, 'n_id_658_avatar_is_a_variant_list'),
    (19, 15, 'n_id_658_avatar_is_a_variant_list'),
    (20, 15, 'n_id_658_avatar_is_a_variant_list'),
    (21, 16, 'n_id_659_avatar_is_a_variant_list'),
    (22, 14, 'n_id_657_avatar_is_a_variant_list'),
    (23, 14, 'n_id_657_avatar_is_a_variant_list'),
    (25, 20, 'n_id_663_avatar_is_a_variant_list'),
    (26, 20, 'n_id_663_avatar_is_a_variant_list'),
    (27, 20, 'n_id_663_avatar_is_a_variant_list'),
    (28, 20, 'n_id_663_avatar_is_a_variant_list'),
    (29, 20, 'n_id_663_avatar_is_a_variant_list'),
    (30, 15, 'n_id_658_avatar_is_a_variant_list'),
    (33, 15, 'n_id_658_avatar_is_a_variant_list'),
    (34, 22, 'n_id_665_avatar_is_a_variant_list'),
    (35, 22, 'n_id_665_avatar_is_a_variant_list'),
    (36, 22, 'n_id_665_avatar_is_a_variant_list'),
    (37, 22, 'n_id_665_avatar_is_a_variant_list'),
    (38, 23, 'n_id_666_avatar_is_a_variant_list'),
    (40, 22, 'n_id_665_avatar_is_a_variant_list'),
    (41, 22, 'n_id_665_avatar_is_a_variant_list'),
    (42, 22, 'n_id_665_avatar_is_a_variant_list'),
    (43, 22, 'n_id_665_avatar_is_a_variant_list'),
    (44, 26, 'n_id_670_avatar_is_a_variant_list'),
    (45, 26, 'n_id_670_avatar_is_a_variant_list'),
    (49, 28, 'n_id_672_avatar_is_a_variant_list'),
    (50, 0, 'template_id_is_not_a_number_UNRESOLVED'),
    (52, 21, 'n_id_664_avatar_is_a_variant_list'),
    (53, 21, 'n_id_664_avatar_is_a_variant_list'),
    (54, 21, 'n_id_664_avatar_is_a_variant_list'),
    (55, 21, 'n_id_664_avatar_is_a_variant_list'),
    (56, 24, 'n_id_667_avatar_is_a_variant_list'),
    (59, 33, 'n_id_838_avatar_is_a_variant_list'),
    (60, 33, 'n_id_838_avatar_is_a_variant_list'),
    (61, 33, 'n_id_838_avatar_is_a_variant_list'),
    (65, 35, 'n_id_841_avatar_is_a_variant_list'),
    (66, 101, 'n_id_10053_has_no_avatar_template'),
    (67, 102, 'n_id_10054_has_no_avatar_template'),
    (68, 103, 'n_id_10055_has_no_avatar_template'),
    (69, 104, 'n_id_10056_has_no_avatar_template'),
    (70, 105, 'n_id_10057_has_no_avatar_template'),
    (71, 16, 'n_id_659_avatar_is_a_variant_list'),
    (72, 16, 'n_id_659_avatar_is_a_variant_list'),
    (73, 16, 'n_id_659_avatar_is_a_variant_list'),
    (74, 16, 'n_id_659_avatar_is_a_variant_list'),
    (75, 16, 'n_id_659_avatar_is_a_variant_list'),
    (76, 16, 'n_id_659_avatar_is_a_variant_list'),
    (77, 16, 'n_id_659_avatar_is_a_variant_list'),
    (78, 23, 'n_id_666_avatar_is_a_variant_list'),
    (79, 23, 'n_id_666_avatar_is_a_variant_list'),
    (80, 23, 'n_id_666_avatar_is_a_variant_list'),
    (81, 23, 'n_id_666_avatar_is_a_variant_list'),
    (82, 23, 'n_id_666_avatar_is_a_variant_list'),
    (83, 24, 'n_id_667_avatar_is_a_variant_list'),
    (84, 24, 'n_id_667_avatar_is_a_variant_list'),
    (85, 24, 'n_id_667_avatar_is_a_variant_list'),
    (86, 24, 'n_id_667_avatar_is_a_variant_list'),
    (87, 24, 'n_id_667_avatar_is_a_variant_list'),
    (88, 24, 'n_id_667_avatar_is_a_variant_list'),
    (89, 24, 'n_id_667_avatar_is_a_variant_list'),
]

