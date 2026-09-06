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
    placements     b69ee8f159d5242c393872101326bbddaa67d9f8fb7514f38e039e138308c0c5
    scene_name     e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b
    standard_mob   4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925

SELECTION CENSUS FOR THIS SCENE (see the generator on why this is printed)
    ai_combat            6
    drops_normal         6
    rank                 6
    rank_and_ai_combat   6
    town_target          0
    unambiguous          49
"""

from __future__ import annotations


SCENE = 'bg0005'
IDENTITY_RULE = 'cline'
# Which column reading selected the rows below.  'rank_and_ai_combat' is the
# town reading every module before round mf71tm shipped under; 'rank' is the
# ocean-panel reading, where the combat-AI column marks ships and weather
# markers instead of monsters.  The generator's own HOSTILITY_RULES block
# carries the per-scene measurement behind that split.
HOSTILITY_RULE = 'rank_and_ai_combat'
SCENE_CLINE_TYPE = 5
SOURCE_DIGESTS = {
    'cline': 'aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40',
    'mobs': '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    'mobs_tip': 'e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f',
    'placements': 'b69ee8f159d5242c393872101326bbddaa67d9f8fb7514f38e039e138308c0c5',
    'scene_name': 'e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b',
    'standard_mob': '4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925',
}
PREDICATE_CENSUS = {
    'ai_combat': 6,
    'drops_normal': 6,
    'rank': 6,
    'rank_and_ai_combat': 6,
    'town_target': 0,
    'unambiguous': 49,
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
    59: 45,
    69: 47,
    70: 41,
    74: 43,
    84: 57,
    85: 58,
}

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
# Placements whose resolved MOBS row carries BOTH a rank and a combat AI.
HOSTILE_PLACEMENTS = [
    (59, 148, -19755.85546875, -3189.87841796875, 2131.141357421875, 'M010_000_001_SP3', 'Red Devil', 66, 1, 11, 201, 100, 59306, 2701004, 5400003, 0),
    (69, 150, -11527.8701171875, -24172.7265625, 3907.96923828125, 'M003_000_000_SP3', 'Ned apes', 69, 1, 11, 134, 100, 68789, 2701004, 5400003, 2802211),
    (70, 144, -9130.62890625, 11611.884765625, 1747.5501708984375, 'M011_001_001_SP3', 'Hard Blade Eagle', 68, 1, 11, 214, 100, 65511, 2701004, 5400003, 2802235),
    (74, 146, -11004.3955078125, -6054.455078125, 1054.8873291015625, 'M001_000_003_SP3', 'Black Jack', 65, 1, 11, 111, 100, 56377, 2701004, 5400003, 0),
    (84, 523, 22612.3046875, -17041.068359375, 401.7677917480469, 'M015_001_001_N', 'Jet cat thieves No.5', 62, 1, 16, 250, 100, 48209, 2701004, 5400003, 0),
    (85, 525, -10786.951171875, 14406.4208984375, 1766.5823974609375, 'M015_001_001_N', 'Jet cat thieves No.6', 67, 1, 16, 250, 100, 62350, 2701004, 5400003, 0),
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
    59: 'cline',
    69: 'cline',
    70: 'cline',
    74: 'cline',
    84: 'cline',
    85: 'cline',
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
    (32, 34, 'Fighting Fish soldier', 137, 'Kate'),
    (33, 31, 'Tornado Eagle', 134, 'Khayredin'),
    (36, 35, 'Fighting Fish Sergeant', 138, 'Blind Hound [not carried: n_id_138_avatar_is_a_variant_list]'),
    (37, 35, 'Fighting Fish Sergeant', 138, 'Blind Hound [not carried: n_id_138_avatar_is_a_variant_list]'),
    (38, 35, 'Fighting Fish Sergeant', 138, 'Blind Hound [not carried: n_id_138_avatar_is_a_variant_list]'),
    (88, 103, 'Orc Chief', 10022, '(no MOBS_TIP name) [not carried: n_id_10022_has_no_avatar_template]'),
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
    (0, 1, 'n_id_104_has_no_MOBS_row'),
    (29, 36, 'n_id_139_avatar_is_a_variant_list'),
    (34, 36, 'n_id_139_avatar_is_a_variant_list'),
    (35, 36, 'n_id_139_avatar_is_a_variant_list'),
    (36, 35, 'n_id_138_avatar_is_a_variant_list'),
    (37, 35, 'n_id_138_avatar_is_a_variant_list'),
    (38, 35, 'n_id_138_avatar_is_a_variant_list'),
    (39, 37, 'n_id_140_avatar_is_a_variant_list'),
    (40, 37, 'n_id_140_avatar_is_a_variant_list'),
    (41, 39, 'n_id_142_avatar_is_a_variant_list'),
    (42, 39, 'n_id_142_avatar_is_a_variant_list'),
    (43, 38, 'n_id_141_avatar_is_a_variant_list'),
    (44, 38, 'n_id_141_avatar_is_a_variant_list'),
    (45, 38, 'n_id_141_avatar_is_a_variant_list'),
    (46, 38, 'n_id_141_avatar_is_a_variant_list'),
    (47, 42, 'n_id_145_avatar_is_a_variant_list'),
    (48, 40, 'n_id_143_avatar_is_a_variant_list'),
    (49, 40, 'n_id_143_avatar_is_a_variant_list'),
    (50, 42, 'n_id_145_avatar_is_a_variant_list'),
    (51, 42, 'n_id_145_avatar_is_a_variant_list'),
    (52, 42, 'n_id_145_avatar_is_a_variant_list'),
    (53, 42, 'n_id_145_avatar_is_a_variant_list'),
    (54, 42, 'n_id_145_avatar_is_a_variant_list'),
    (55, 44, 'n_id_147_avatar_is_a_variant_list'),
    (56, 44, 'n_id_147_avatar_is_a_variant_list'),
    (57, 44, 'n_id_147_avatar_is_a_variant_list'),
    (58, 44, 'n_id_147_avatar_is_a_variant_list'),
    (60, 44, 'n_id_147_avatar_is_a_variant_list'),
    (61, 44, 'n_id_147_avatar_is_a_variant_list'),
    (62, 44, 'n_id_147_avatar_is_a_variant_list'),
    (63, 44, 'n_id_147_avatar_is_a_variant_list'),
    (64, 44, 'n_id_147_avatar_is_a_variant_list'),
    (65, 46, 'n_id_149_avatar_is_a_variant_list'),
    (66, 46, 'n_id_149_avatar_is_a_variant_list'),
    (67, 46, 'n_id_149_avatar_is_a_variant_list'),
    (68, 46, 'n_id_149_avatar_is_a_variant_list'),
    (71, 40, 'n_id_143_avatar_is_a_variant_list'),
    (72, 40, 'n_id_143_avatar_is_a_variant_list'),
    (86, 101, 'n_id_10020_has_no_avatar_template'),
    (87, 102, 'n_id_10021_has_no_avatar_template'),
    (88, 103, 'n_id_10022_has_no_avatar_template'),
    (89, 104, 'n_id_10023_has_no_avatar_template'),
    (91, 105, 'n_id_7044_avatar_is_a_variant_list'),
]

