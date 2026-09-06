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
    placements     c6b051feb2c1fe027130d95b65abdcfe2d3d937e367b2248e5372042d1e52ea0
    scene_name     e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b
    standard_mob   4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925

SELECTION CENSUS FOR THIS SCENE (see the generator on why this is printed)
    ai_combat            5
    drops_normal         3
    rank                 5
    rank_and_ai_combat   5
    town_target          0
    unambiguous          27
"""

from __future__ import annotations


SCENE = 'Bg0009'
IDENTITY_RULE = 'cline'
SCENE_CLINE_TYPE = 9
SOURCE_DIGESTS = {
    'cline': 'aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40',
    'mobs': '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    'mobs_tip': 'e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f',
    'placements': 'c6b051feb2c1fe027130d95b65abdcfe2d3d937e367b2248e5372042d1e52ea0',
    'scene_name': 'e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b',
    'standard_mob': '4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925',
}
PREDICATE_CENSUS = {
    'ai_combat': 5,
    'drops_normal': 3,
    'rank': 5,
    'rank_and_ai_combat': 5,
    'town_target': 0,
    'unambiguous': 27,
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
    42: 31,
    49: 34,
    54: 37,
    56: 41,
    57: 44,
}

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
# Placements whose resolved MOBS row carries BOTH a rank and a combat AI.
HOSTILE_PLACEMENTS = [
    (42, 314, -17501.869140625, 12612.115234375, 607.1314697265625, 'M010_000_001_SP3', 'Captain Golem Rabia', 93, 1, 11, 201, 100, 160837, 2701008, 5400004, 0),
    (49, 317, -23619.08984375, -25924.498046875, 2521.283203125, 'M004_000_003_SP3', 'Destroy Magic Flower', 93, 1, 11, 142, 100, 160837, 2701008, 5400004, 2802220),
    (54, 320, 20391.560546875, -24944.775390625, 2671.420166015625, 'M026_000_002_SP3', 'Skeleton Commander Corella', 93, 1, 11, 360, 100, 160837, 2701008, 5400004, 0),
    (56, 546, -17677.73828125, 11541.7734375, 648.3300170898438, 'M019_000_000_SP4', 'Black braid Edward', 93, 1, 16, 293, 440, 160837, 0, 0, 0),
    (57, 549, -14789.716796875, 11079.390625, 588.1323852539062, 'M022_000_003_SP2', 'Bermuda Banshee', 93, 1, 16, 320, 100, 160837, 0, 0, 0),
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
    42: 'cline',
    49: 'cline',
    54: 'cline',
    56: 'cline',
    57: 'cline',
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
    (50, 35, 'Fighting Fish Sergeant', 318, 'Dark soul [not carried: n_id_318_avatar_is_a_variant_list]'),
    (51, 35, 'Fighting Fish Sergeant', 318, 'Dark soul [not carried: n_id_318_avatar_is_a_variant_list]'),
    (60, 103, 'Orc Chief', 10050, '(no MOBS_TIP name) [not carried: n_id_10050_has_no_avatar_template]'),
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
    (0, 1, 'n_id_284_has_no_MOBS_row'),
    (22, 24, 'n_id_307_avatar_is_a_variant_list'),
    (23, 24, 'n_id_307_avatar_is_a_variant_list'),
    (24, 24, 'n_id_307_avatar_is_a_variant_list'),
    (25, 25, 'n_id_308_avatar_is_a_variant_list'),
    (26, 25, 'n_id_308_avatar_is_a_variant_list'),
    (27, 25, 'n_id_308_avatar_is_a_variant_list'),
    (28, 26, 'n_id_309_avatar_is_a_variant_list'),
    (29, 26, 'n_id_309_avatar_is_a_variant_list'),
    (30, 26, 'n_id_309_avatar_is_a_variant_list'),
    (31, 27, 'n_id_310_avatar_is_a_variant_list'),
    (32, 27, 'n_id_310_avatar_is_a_variant_list'),
    (33, 27, 'n_id_310_avatar_is_a_variant_list'),
    (34, 28, 'n_id_311_avatar_is_a_variant_list'),
    (35, 28, 'n_id_311_avatar_is_a_variant_list'),
    (36, 28, 'n_id_311_avatar_is_a_variant_list'),
    (37, 29, 'n_id_312_avatar_is_a_variant_list'),
    (38, 29, 'n_id_312_avatar_is_a_variant_list'),
    (39, 29, 'n_id_312_avatar_is_a_variant_list'),
    (40, 30, 'n_id_313_avatar_is_a_variant_list'),
    (41, 30, 'n_id_313_avatar_is_a_variant_list'),
    (43, 30, 'n_id_313_avatar_is_a_variant_list'),
    (44, 30, 'n_id_313_avatar_is_a_variant_list'),
    (45, 28, 'n_id_311_avatar_is_a_variant_list'),
    (46, 32, 'n_id_315_avatar_is_a_variant_list'),
    (47, 32, 'n_id_315_avatar_is_a_variant_list'),
    (48, 33, 'n_id_316_avatar_is_a_variant_list'),
    (50, 35, 'n_id_318_avatar_is_a_variant_list'),
    (51, 35, 'n_id_318_avatar_is_a_variant_list'),
    (52, 36, 'n_id_319_avatar_is_a_variant_list'),
    (53, 36, 'n_id_319_avatar_is_a_variant_list'),
    (58, 101, 'n_id_10048_has_no_avatar_template'),
    (59, 102, 'n_id_10049_has_no_avatar_template'),
    (60, 103, 'n_id_10050_has_no_avatar_template'),
    (61, 104, 'n_id_10051_has_no_avatar_template'),
    (62, 105, 'n_id_10052_has_no_avatar_template'),
]

