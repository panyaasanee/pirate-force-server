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
    placements     712fb2d88ebe385615d43bd5233437329ebcdda31d196521dcd0ba69ac469c0d
    scene_name     e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b
    standard_mob   4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925

SELECTION CENSUS FOR THIS SCENE (see the generator on why this is printed)
    ai_combat            10
    drops_normal         10
    rank                 10
    rank_and_ai_combat   10
    town_target          0
    unambiguous          24
"""

from __future__ import annotations


SCENE = 'Bg0011'
IDENTITY_RULE = 'cline'
SCENE_CLINE_TYPE = 11
SOURCE_DIGESTS = {
    'cline': 'aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40',
    'mobs': '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    'mobs_tip': 'e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f',
    'placements': '712fb2d88ebe385615d43bd5233437329ebcdda31d196521dcd0ba69ac469c0d',
    'scene_name': 'e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b',
    'standard_mob': '4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925',
}
PREDICATE_CENSUS = {
    'ai_combat': 10,
    'drops_normal': 10,
    'rank': 10,
    'rank_and_ai_combat': 10,
    'town_target': 0,
    'unambiguous': 24,
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
    20: 19,
    25: 24,
    38: 22,
    42: 19,
    43: 19,
    44: 19,
    45: 23,
    46: 19,
    49: 19,
    50: 26,
}

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
# Placements whose resolved MOBS row carries BOTH a rank and a combat AI.
HOSTILE_PLACEMENTS = [
    (20, 693, 10738.6474609375, 4526.6455078125, 424.9296875, 'M018_000_000_N', 'Navy Two Tripods', 99, 1, 16, 280, 100, 192488, 2701009, 5400031, 2802244),
    (25, 669, -23315.921875, -15531.681640625, -4412.55810546875, 'M016_000_001_SP3', 'Steam Iron Giant', 99, 1, 11, 261, 100, 192488, 2701009, 5400031, 0),
    (38, 696, -16860.6171875, -15836.875, -4412.56298828125, 'M018_000_002_N', 'Navy Tiger Mech', 99, 1, 16, 280, 100, 192488, 2701009, 5400031, 2802246),
    (42, 693, -12879.826171875, -4423.88330078125, -4422.3056640625, 'M018_000_000_N', 'Navy Two Tripods', 99, 1, 16, 280, 100, 192488, 2701009, 5400031, 2802244),
    (43, 693, -12977.75390625, -7480.7568359375, -4469.3466796875, 'M018_000_000_N', 'Navy Two Tripods', 99, 1, 16, 280, 100, 192488, 2701009, 5400031, 2802244),
    (44, 693, -16417.3828125, -7453.4580078125, -4391.92333984375, 'M018_000_000_N', 'Navy Two Tripods', 99, 1, 16, 280, 100, 192488, 2701009, 5400031, 2802244),
    (45, 697, -16663.072265625, -4109.37255859375, -4412.5537109375, 'M026_001_001_BOSS', 'Undead Besso', 99, 1, 11, 362, 100, 192488, 2701009, 5400031, 0),
    (46, 693, -14951.0078125, -6018.94287109375, -4510.29541015625, 'M018_000_000_N', 'Navy Two Tripods', 99, 1, 16, 280, 100, 192488, 2701009, 5400031, 2802244),
    (49, 693, 14429.572265625, 4526.6455078125, 424.9296875, 'M018_000_000_N', 'Navy Two Tripods', 99, 1, 16, 280, 100, 192488, 2701009, 5400031, 2802244),
    (50, 674, 25118.537109375, 20715.20703125, 474.93231201171875, 'M008_000_002_SP3', 'Guard Soul', 104, 1, 16, 182, 100, 221803, 2701009, 5400031, 2802201),
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
    20: 'cline',
    25: 'cline',
    38: 'cline',
    42: 'cline',
    43: 'cline',
    44: 'cline',
    45: 'cline',
    46: 'cline',
    49: 'cline',
    50: 'cline',
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
    (51, 103, 'Orc Chief', 10060, '(no MOBS_TIP name) [not carried: n_id_10060_has_no_avatar_template]'),
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
    (12, 14, 'n_id_688_avatar_is_a_variant_list'),
    (13, 14, 'n_id_688_avatar_is_a_variant_list'),
    (14, 14, 'n_id_688_avatar_is_a_variant_list'),
    (15, 15, 'n_id_689_avatar_is_a_variant_list'),
    (16, 15, 'n_id_689_avatar_is_a_variant_list'),
    (17, 16, 'n_id_690_avatar_is_a_variant_list'),
    (18, 15, 'n_id_689_avatar_is_a_variant_list'),
    (19, 18, 'n_id_692_avatar_is_a_variant_list'),
    (21, 20, 'n_id_694_avatar_is_a_variant_list'),
    (22, 20, 'n_id_694_avatar_is_a_variant_list'),
    (23, 21, 'n_id_695_avatar_is_a_variant_list'),
    (24, 21, 'n_id_695_avatar_is_a_variant_list'),
    (26, 14, 'n_id_688_avatar_is_a_variant_list'),
    (28, 18, 'n_id_692_avatar_is_a_variant_list'),
    (29, 18, 'n_id_692_avatar_is_a_variant_list'),
    (30, 16, 'n_id_690_avatar_is_a_variant_list'),
    (31, 18, 'n_id_692_avatar_is_a_variant_list'),
    (32, 16, 'n_id_690_avatar_is_a_variant_list'),
    (33, 17, 'n_id_691_avatar_is_a_variant_list'),
    (34, 17, 'n_id_691_avatar_is_a_variant_list'),
    (35, 16, 'n_id_690_avatar_is_a_variant_list'),
    (36, 16, 'n_id_690_avatar_is_a_variant_list'),
    (37, 16, 'n_id_690_avatar_is_a_variant_list'),
    (39, 16, 'n_id_690_avatar_is_a_variant_list'),
    (40, 16, 'n_id_690_avatar_is_a_variant_list'),
    (41, 17, 'n_id_691_avatar_is_a_variant_list'),
    (47, 20, 'n_id_694_avatar_is_a_variant_list'),
    (51, 103, 'n_id_10060_has_no_avatar_template'),
    (52, 101, 'n_id_10058_has_no_avatar_template'),
    (53, 102, 'n_id_10059_has_no_avatar_template'),
    (54, 104, 'n_id_10061_has_no_avatar_template'),
    (55, 105, 'n_id_10062_has_no_avatar_template'),
]

