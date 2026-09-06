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
    placements     7143642442abd810ccaed1f1692d82b99ee7729061c30429e54d01d1e42fdb86
    scene_name     e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b
    standard_mob   4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925

SELECTION CENSUS FOR THIS SCENE (see the generator on why this is printed)
    ai_combat            9
    drops_normal         8
    rank                 10
    rank_and_ai_combat   9
    town_target          0
    unambiguous          33
"""

from __future__ import annotations


SCENE = 'Bg0008'
IDENTITY_RULE = 'cline'
SCENE_CLINE_TYPE = 8
SOURCE_DIGESTS = {
    'cline': 'aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40',
    'mobs': '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    'mobs_tip': 'e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f',
    'placements': '7143642442abd810ccaed1f1692d82b99ee7729061c30429e54d01d1e42fdb86',
    'scene_name': 'e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b',
    'standard_mob': '4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925',
}
PREDICATE_CENSUS = {
    'ai_combat': 9,
    'drops_normal': 8,
    'rank': 10,
    'rank_and_ai_combat': 9,
    'town_target': 0,
    'unambiguous': 33,
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
    21: 26,
    23: 29,
    26: 32,
    27: 33,
    51: 32,
    52: 32,
    66: 39,
    67: 40,
    69: 42,
}

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
# Placements whose resolved MOBS row carries BOTH a rank and a combat AI.
HOSTILE_PLACEMENTS = [
    (21, 274, 21857.80859375, -16751.83984375, 572.4290161132812, 'M003_000_001_SP3', 'Polar head', 87, 1, 11, 134, 150, 132902, 2701007, 5400004, 2802212),
    (23, 277, -11584.1142578125, -25424.4765625, 620.8662109375, 'M006_001_002_SP3', 'Polar Giant Turtle', 87, 1, 16, 162, 150, 132902, 2701007, 5400004, 2802233),
    (26, 280, -8425.880859375, 1696.989013671875, 3849.341552734375, 'M010_000_000_SP1', 'Walrus general', 87, 1, 16, 200, 150, 132902, 2701007, 5400004, 0),
    (27, 281, -8827.2705078125, -5276.39599609375, 5660.751953125, 'M010_000_000_SP3', 'Ice Carle Commander', 87, 1, 11, 201, 150, 132902, 2701007, 5400004, 0),
    (51, 280, -13039.6025390625, -2826.213623046875, 5144.4638671875, 'M010_000_000_SP1', 'Walrus general', 87, 1, 16, 200, 150, 132902, 2701007, 5400004, 0),
    (52, 280, -11621.6376953125, -4845.341796875, 5410.49755859375, 'M010_000_000_SP1', 'Walrus general', 87, 1, 16, 200, 150, 132902, 2701007, 5400004, 0),
    (66, 544, 13263.310546875, -11137.9619140625, 2628.9375, 'M015_001_001_SP2', 'Jet cat thieves No.9', 87, 1, 16, 250, 100, 132902, 2701007, 5400004, 0),
    (67, 527, -10696.365234375, -26105.734375, 620.875, 'M015_001_001_SP2', 'Jet cat thieves No.10', 87, 1, 16, 250, 100, 132902, 2701007, 5400004, 0),
    (69, 529, -9298.9326171875, -2653.55224609375, 5668.18115234375, 'P_FEMALE_003_002_NENA', 'Nina', 90, 1, 2, 471, 150, 146413, 0, 0, 0),
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
    21: 'cline',
    23: 'cline',
    26: 'cline',
    27: 'cline',
    51: 'cline',
    52: 'cline',
    66: 'cline',
    67: 'cline',
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
    (25, 31, 'Tornado Eagle', 279, 'Penguin Koro [not carried: n_id_279_avatar_is_a_variant_list]'),
    (30, 34, 'Fighting Fish soldier', 282, 'Deep Sea Snail [not carried: n_id_282_avatar_is_a_variant_list]'),
    (36, 35, 'Fighting Fish Sergeant', 283, 'Blind Hound [not carried: n_id_283_avatar_is_a_variant_list]'),
    (47, 31, 'Tornado Eagle', 279, 'Penguin Koro [not carried: n_id_279_avatar_is_a_variant_list]'),
    (48, 31, 'Tornado Eagle', 279, 'Penguin Koro [not carried: n_id_279_avatar_is_a_variant_list]'),
    (49, 31, 'Tornado Eagle', 279, 'Penguin Koro [not carried: n_id_279_avatar_is_a_variant_list]'),
    (50, 31, 'Tornado Eagle', 279, 'Penguin Koro [not carried: n_id_279_avatar_is_a_variant_list]'),
    (53, 34, 'Fighting Fish soldier', 282, 'Deep Sea Snail [not carried: n_id_282_avatar_is_a_variant_list]'),
    (54, 34, 'Fighting Fish soldier', 282, 'Deep Sea Snail [not carried: n_id_282_avatar_is_a_variant_list]'),
    (55, 35, 'Fighting Fish Sergeant', 283, 'Blind Hound [not carried: n_id_283_avatar_is_a_variant_list]'),
    (56, 35, 'Fighting Fish Sergeant', 283, 'Blind Hound [not carried: n_id_283_avatar_is_a_variant_list]'),
    (57, 35, 'Fighting Fish Sergeant', 283, 'Blind Hound [not carried: n_id_283_avatar_is_a_variant_list]'),
    (72, 103, 'Orc Chief', 10045, '(no MOBS_TIP name) [not carried: n_id_10045_has_no_avatar_template]'),
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
    (0, 1, 'n_id_249_has_no_MOBS_row'),
    (19, 23, 'n_id_271_avatar_is_a_variant_list'),
    (20, 27, 'n_id_275_avatar_is_a_variant_list'),
    (22, 27, 'n_id_275_avatar_is_a_variant_list'),
    (24, 30, 'n_id_278_avatar_is_a_variant_list'),
    (25, 31, 'n_id_279_avatar_is_a_variant_list'),
    (28, 24, 'n_id_272_avatar_is_a_variant_list'),
    (29, 24, 'n_id_272_avatar_is_a_variant_list'),
    (30, 34, 'n_id_282_avatar_is_a_variant_list'),
    (31, 28, 'n_id_276_avatar_is_a_variant_list'),
    (32, 28, 'n_id_276_avatar_is_a_variant_list'),
    (33, 28, 'n_id_276_avatar_is_a_variant_list'),
    (34, 28, 'n_id_276_avatar_is_a_variant_list'),
    (35, 28, 'n_id_276_avatar_is_a_variant_list'),
    (36, 35, 'n_id_283_avatar_is_a_variant_list'),
    (37, 23, 'n_id_271_avatar_is_a_variant_list'),
    (38, 23, 'n_id_271_avatar_is_a_variant_list'),
    (39, 25, 'n_id_273_avatar_is_a_variant_list'),
    (40, 25, 'n_id_273_avatar_is_a_variant_list'),
    (41, 25, 'n_id_273_avatar_is_a_variant_list'),
    (42, 27, 'n_id_275_avatar_is_a_variant_list'),
    (43, 27, 'n_id_275_avatar_is_a_variant_list'),
    (44, 27, 'n_id_275_avatar_is_a_variant_list'),
    (45, 30, 'n_id_278_avatar_is_a_variant_list'),
    (46, 30, 'n_id_278_avatar_is_a_variant_list'),
    (47, 31, 'n_id_279_avatar_is_a_variant_list'),
    (48, 31, 'n_id_279_avatar_is_a_variant_list'),
    (49, 31, 'n_id_279_avatar_is_a_variant_list'),
    (50, 31, 'n_id_279_avatar_is_a_variant_list'),
    (53, 34, 'n_id_282_avatar_is_a_variant_list'),
    (54, 34, 'n_id_282_avatar_is_a_variant_list'),
    (55, 35, 'n_id_283_avatar_is_a_variant_list'),
    (56, 35, 'n_id_283_avatar_is_a_variant_list'),
    (57, 35, 'n_id_283_avatar_is_a_variant_list'),
    (58, 22, 'n_id_270_avatar_is_a_variant_list'),
    (59, 22, 'n_id_270_avatar_is_a_variant_list'),
    (60, 22, 'n_id_270_avatar_is_a_variant_list'),
    (70, 101, 'n_id_10043_has_no_avatar_template'),
    (71, 102, 'n_id_10044_has_no_avatar_template'),
    (72, 103, 'n_id_10045_has_no_avatar_template'),
    (73, 104, 'n_id_10046_has_no_avatar_template'),
    (74, 105, 'n_id_10047_has_no_avatar_template'),
    (75, 106, 'cline_leader_is_zero_or_absent'),
]

