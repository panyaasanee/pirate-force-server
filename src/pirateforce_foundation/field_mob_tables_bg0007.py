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
    placements     3a0e8d9a11a24f1f0825a6ecc83d1f6fb43e51c0a5b8338fd30a8abf15ccc15d
    scene_name     e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b
    standard_mob   4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925

SELECTION CENSUS FOR THIS SCENE (see the generator on why this is printed)
    ai_combat            9
    drops_normal         9
    rank                 9
    rank_and_ai_combat   9
    town_target          0
    unambiguous          38
"""

from __future__ import annotations


SCENE = 'Bg0007'
IDENTITY_RULE = 'cline'
# Which column reading selected the rows below.  'rank_and_ai_combat' is the
# town reading every module before round mf71tm shipped under; 'rank' is the
# ocean-panel reading, where the combat-AI column marks ships and weather
# markers instead of monsters.  The generator's own HOSTILITY_RULES block
# carries the per-scene measurement behind that split.
HOSTILITY_RULE = 'rank_and_ai_combat'
SCENE_CLINE_TYPE = 7
SOURCE_DIGESTS = {
    'cline': 'aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40',
    'mobs': '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    'mobs_tip': 'e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f',
    'placements': '3a0e8d9a11a24f1f0825a6ecc83d1f6fb43e51c0a5b8338fd30a8abf15ccc15d',
    'scene_name': 'e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b',
    'standard_mob': '4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925',
}
PREDICATE_CENSUS = {
    'ai_combat': 9,
    'drops_normal': 9,
    'rank': 9,
    'rank_and_ai_combat': 9,
    'town_target': 0,
    'unambiguous': 38,
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
    28: 28,
    29: 28,
    35: 30,
    40: 33,
    43: 35,
    44: 35,
    48: 37,
    55: 44,
    56: 45,
}

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
# Placements whose resolved MOBS row carries BOTH a rank and a combat AI.
HOSTILE_PLACEMENTS = [
    (28, 388, -10082.4375, 16337.6259765625, 7506.95556640625, 'M020_001_001_SP1', 'Ominous Bird', 81, 1, 10, 300, 150, 108391, 2701006, 5400004, 2802254),
    (29, 388, -6656.8134765625, 8682.6064453125, 7637.74951171875, 'M020_001_001_SP1', 'Ominous Bird', 81, 1, 10, 300, 150, 108391, 2701006, 5400004, 2802254),
    (35, 390, 1177.8848876953125, -5377.81787109375, 10404.1572265625, 'M002_001_000_SP3', 'Dark roar', 81, 1, 11, 125, 150, 108391, 2701006, 5400004, 2802209),
    (40, 393, 16700.453125, 15398.3828125, 11538.787109375, 'M023_000_000_SP3', 'Avarice Lerch', 81, 1, 16, 333, 150, 108391, 2701006, 5400004, 0),
    (43, 395, 12862.5927734375, -18777.833984375, 12415.1875, 'M014_000_001_N', 'Remain Alert Weapon', 81, 1, 16, 240, 150, 108391, 2701006, 5400004, 0),
    (44, 395, 7798.28857421875, -16908.482421875, 12034.6396484375, 'M014_000_001_N', 'Remain Alert Weapon', 81, 1, 16, 240, 150, 108391, 2701006, 5400004, 0),
    (48, 397, -8197.6513671875, -19397.052734375, 11892.1669921875, 'M023_001_002_SP3', 'Green Eye Minced', 81, 1, 11, 333, 150, 108391, 2701006, 5400004, 0),
    (55, 536, 11958.9775390625, 16993.32421875, 10483.7509765625, 'M015_001_001_SP2', 'Jet cat thieves No.7', 81, 1, 16, 250, 100, 108391, 2701006, 5400004, 0),
    (56, 526, 15880.2958984375, -13514.4677734375, 12391.2353515625, 'M015_001_001_SP2', 'Jet cat thieves No.8', 81, 1, 16, 250, 100, 108391, 2701006, 5400004, 0),
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
    28: 'cline',
    29: 'cline',
    35: 'cline',
    40: 'cline',
    43: 'cline',
    44: 'cline',
    48: 'cline',
    55: 'cline',
    56: 'cline',
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
    (36, 31, 'Tornado Eagle', 391, 'Curse Harpy [not carried: n_id_391_avatar_is_a_variant_list]'),
    (37, 31, 'Tornado Eagle', 391, 'Curse Harpy [not carried: n_id_391_avatar_is_a_variant_list]'),
    (41, 34, 'Fighting Fish soldier', 394, 'Zombie baboon [not carried: n_id_394_avatar_is_a_variant_list]'),
    (42, 34, 'Fighting Fish soldier', 394, 'Zombie baboon [not carried: n_id_394_avatar_is_a_variant_list]'),
    (59, 103, 'Orc Chief', 10035, '(no MOBS_TIP name) [not carried: n_id_10035_has_no_avatar_template]'),
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
    (0, 1, 'n_id_361_has_no_MOBS_row'),
    (24, 25, 'n_id_385_avatar_is_a_variant_list'),
    (25, 27, 'n_id_387_avatar_is_a_variant_list'),
    (26, 27, 'n_id_387_avatar_is_a_variant_list'),
    (27, 26, 'n_id_386_avatar_is_a_variant_list'),
    (30, 29, 'n_id_389_avatar_is_a_variant_list'),
    (31, 29, 'n_id_389_avatar_is_a_variant_list'),
    (32, 29, 'n_id_389_avatar_is_a_variant_list'),
    (33, 29, 'n_id_389_avatar_is_a_variant_list'),
    (34, 29, 'n_id_389_avatar_is_a_variant_list'),
    (36, 31, 'n_id_391_avatar_is_a_variant_list'),
    (37, 31, 'n_id_391_avatar_is_a_variant_list'),
    (38, 32, 'n_id_392_avatar_is_a_variant_list'),
    (39, 32, 'n_id_392_avatar_is_a_variant_list'),
    (41, 34, 'n_id_394_avatar_is_a_variant_list'),
    (42, 34, 'n_id_394_avatar_is_a_variant_list'),
    (45, 36, 'n_id_396_avatar_is_a_variant_list'),
    (46, 36, 'n_id_396_avatar_is_a_variant_list'),
    (47, 36, 'n_id_396_avatar_is_a_variant_list'),
    (57, 101, 'n_id_10033_has_no_avatar_template'),
    (58, 102, 'n_id_10034_has_no_avatar_template'),
    (59, 103, 'n_id_10035_has_no_avatar_template'),
    (60, 104, 'n_id_10036_has_no_avatar_template'),
    (61, 105, 'n_id_10037_has_no_avatar_template'),
    (62, 106, 'n_id_10038_has_no_avatar_template'),
    (63, 107, 'n_id_10039_has_no_avatar_template'),
    (64, 108, 'n_id_10040_has_no_avatar_template'),
    (65, 109, 'n_id_10041_has_no_avatar_template'),
    (66, 110, 'n_id_10042_has_no_avatar_template'),
    (67, 111, 'cline_leader_is_zero_or_absent'),
]

