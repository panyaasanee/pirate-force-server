"""Who each Bg0007 placement actually IS - Voodoo Island's real cast.

LANE-A (WORLD).  ``COO-DECISION 2026-08-30T14:41+07:00`` (pf_bridge
``notes_to_chief/20260830_1441_COO-DECISION-scene4-slave-market-first-door.md``)
approved building the ten still-shut doors surveyed in round ``12lyda`` in
native-placement-count order ("no need to ask again per door").  Scenes 4, 5,
10, 14, 6, 8 and 3 are open; this is the seventh door in the sequence and the
next-highest native placement count among the four still shut (7, 9, 11,
130): scene 7 (Bg0007, "Voodoo Island", 68 placements).  This module is the
identity half, the same split every earlier crosswalk used;
``world_population_bg0007`` is the census half.

THE CROSSWALK, RE-DERIVED HERE RATHER THAN TAKEN FROM A CITATION.
``SCENE_NAME[s_MODLE_ID=BG0007].n_CLINE_TYPE`` was read directly off the
bridge clone this round:

    SCENE_NAME[s_MODLE_ID=BG0007].n_ID          = 7
    SCENE_NAME[s_MODLE_ID=BG0007].n_CLINE_TYPE  = 7    (a real value, direct)
    SCENE_NAME[s_MODLE_ID=BG0007].n_SCENE_LV    = 81
    CLINE[(7, <Mob-Set number>)].n_LEADER_BK1   = the real MOBS.n_ID
    MOBS[n_ID].s_OUTFIT                         = the avatar the client loads
    MOBS_TIP[n_ID].s_NAME / s_TITLE             = the label under the actor
    STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX      = max HP (the one derived col)

Same direct-selector shape ``world_bg0003_identity``, ``world_bg0004_identity``,
``world_bg0005_identity``, ``world_bg0006_identity``, ``world_bg0008_identity``
and ``world_bg0010_identity`` all ship (one of RE-128's 19 direct CLINE
types, not one of its 240 instance scenes).

WHAT IS ESTABLISHED HERE AND WHAT IS NOT, STATED THE SAME WAY THE OTHER SEVEN
CROSSWALK MODULES STATE IT.

    ESTABLISHED - THE TABLE.  This scene's cast is drawn from CLINE type 7's
    leader column.  CONTROL 1 below is exact: this scene's placements use
    exactly 56 distinct Mob-Set numbers (1-45, 101-111) and every one of the
    56 has a row in CLINE type 7 - which is CLINE type 7's ENTIRE key range
    (56 rows total, counted directly rather than trusted from the registry's
    own ``native_definition_count`` of 57 - see the discrepancy note below),
    the same 'placement file touches every key its own CLINE type owns'
    shape scenes 3's, 5's, 6's and 8's own crosswalks carry (unlike bg0004's
    61-of-62 and bg0010's 40-of-41).

    NOT ESTABLISHED - THE PAIRING.  Which leader belongs to which Mob-Set
    number.  No human has stood in this scene (registry ``status:
    never_sent_to_any_client_by_this_project``), so every name below is a
    table inference, the bottom of the evidence order COO set on
    2026-08-28T21:30, until an attended round looks.

DISCREPANCY, MEASURED AND NOT SILENTLY RECONCILED.  The registry's own
``native_definition_count`` for scene 7 reads 57; this round's own count of
CLINE type 7's rows (grouped by ``n_CREATURE_TYPE``, checked for duplicates -
there are none) is 56, and 56 is also exactly the count of distinct Mob-Set
numbers this scene's own 68 placements use (CONTROL 1).  The two numbers
agreeing with each other and disagreeing with the registry's field is the
same shape as bg0003's 52-of-51, bg0004's 61-of-62, bg0010's 40-of-41 and
bg0008's 49-of-48 differences: recorded here rather than "fixed" in the
registry, because this round did not re-derive whatever the registry's own
count measured and cannot say which of the two is wrong without doing that
separately.

CONTROL 1 - EXACT SUBSET, MEASURED.  The 68 placements resolve to 56 distinct
Mob-Set numbers; CLINE type 7 has exactly 56 keys (1-45, 101-111); the two
sets are identical (no gap either direction).

CONTROL 2 - NOT REBUILT HERE.  No ``world_bg0015_identity.
SCENE_LEVEL_CONTROL`` row exists for BG0007 (checked: that table only cites
scenes it was built against at the time, and this scene was never one of
them) - the same absence bg0003's, bg0006's and bg0008's own Control 2
recorded, not silently skipped.

CONTROL 3 - NO SELF-MAPPING, WEAK, SAME CAVEAT AS THE OTHER SEVEN SCENES.  0
of the 44 resolved rows have ``mobs_n_id == template_id`` (measured, not
assumed): none.  A shape check, not evidence.

TWELVE OF THE 56 SETS DO NOT RESOLVE (COST 12 PLACEMENTS), TWO FAMILIAR
FAILURE SHAPES, NO THIRD ONE THIS TIME.

* Set [1] -> leader [361].  CLINE type 7's own row for key 1 carries a real,
  non-zero ``n_LEADER_BK1`` (361) but ``CONSTDATA MOBS`` has no row for it -
  the same "MOBS has no row" family bg0003's set 2, bg0005's set 1, bg0006's
  sets 1/114 and bg0008's sets 1/106 needed, six occurrences of the shape
  across the project so far, one here.
* Sets [101, 102, 103, 104, 105, 106, 107, 108, 109, 110] -> leaders [10033,
  10034, 10035, 10036, 10037, 10038, 10039, 10040, 10041, 10042].  Every one
  HAS a ``CONSTDATA MOBS`` row but its ``s_OUTFIT`` column is empty - the
  identical 'path-finding helper, not a creature' shape every sibling
  scene's own 101+ block carries (bg0003: 9, bg0004: 6, bg0005: 4, bg0006:
  9, bg0008: 5, bg0010: 5; this scene: 10).
* Set [111] -> leader [0].  CLINE type 7's own row for key 111 carries
  ``n_LEADER_BK1`` = 0, which is not a MOBS row this table treats as
  resolvable (the same "no leader at all" shape as a "MOBS has no row"
  refusal, folded into that family here rather than invented as a third
  reason).
* NO CJK/non-cp874 name this scene needed - unlike bg0006's three
  teleporter drops, every one of this scene's 44 resolved ``MOBS_TIP`` rows
  is plain ASCII, checked directly (not assumed from the absence of a
  failure).

EIGHT SETS LIST TWO VARIANT AVATAR TEMPLATES SEPARATED BY ';'.  Same rule and
the same open question as bg0003's nine, bg0004's nine, bg0005's ten,
bg0006's ten, bg0008's ten and bg0010's twelve: ship the FIRST variant, keep
the whole string in ``MULTI_VARIANT_OUTFITS``, and ``_self_check`` refuses at
import if a raw ';' ever reaches the shipped column.  [LANE-A ASSUMPTION -
AWAITING COO/OWNER CONFIRMATION].  Leaders [385, 386, 387, 389, 391, 392,
394, 396] (8 of the 44 resolved sets), all two-variant rows (this scene does
not repeat bg0003's nine-variant outlier), covering 18 of the 56 shippable
placements (measured this round, not estimated).

NO NAME-VS-TEMPLATE DISAGREEMENT, NO EXTRA SPAWN TRIPLE, NO MULTI-TEMPLATE
ROW, NO EXTRACTION-UNRESOLVED SENTINEL.  Checked directly against this
scene's own placement file: no row carries ``extra_triple_count > 0``, no row
lists more than one template id, and no row's ``template_ids`` column reads
the literal ``UNRESOLVED``.  Same clean shape bg0003's, bg0005's, bg0006's
and bg0008's own crosswalks carry on these axes.

NO CREW.  Measured for this scene: 0 of CLINE type 7's 56 rows carry any
``n_CREW`` value at all (checked ``n_CREW1`` through ``n_CREW6``), the same
"no pet/crew group silently dropped" shape every sibling scene carries.

HEADING.  Same measurement every sibling scene's own ``_entry`` made for its
own scene: the extra f32 triple this TSV format carries (columns
``f32_3``/``f32_4``/``f32_5``) is a round-number range across unrelated rows
here too - the shape of a radius, not a rotation - so the census half reuses
``world_population.HEADINGS`` on the placement index, same as every other
scene.

LANDING GEOMETRY.  ``scenarios/world_scene_registry_001.json``'s own
``table_row_differences.marker_geometry_measured_not_enforced`` block for
this scene (n_id 7) records the marker point 10.793 units from the nearest
of this scene's 68 native placements, INSIDE the placement extents - unlike
bg0003's 405.0-units-outside geometry, this door's own arrival point sits
among its own cast.  This row does NOT carry
``table_row_differences.the_two_interiors`` (checked, not assumed - that
flag names only scenes 10 and 11).  Still 'recorded, not enforced' (a .npc
file is not terrain), but a fact worth naming rather than leaving buried in
the registry JSON.

PROVENANCE.  Every row below was generated from these six committed
artifacts and nothing else, re-derived rather than copied from a sibling
module's citation of the same four shared tables (identical digests to the
other crosswalk modules' own citations, since they are the same committed
files; only the placements file digest is new):

    gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv
    gamedata/tables/CONSTDATA_TH__CLINE.tsv
    gamedata/tables/CONSTDATA_TH__MOBS.tsv
    gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv
    gamedata/tables/CONSTDATA_TH__STANDARD_MOB.tsv
    gamedata/scene/Bg0007/Bg0007.placements.tsv

THE JOIN, EXACTLY, SO IT CAN BE MECHANISED LATER (done by a throwaway script
against committed TSVs read directly this round, not by hand - the tables
are large enough that hand transcription would itself be an error source;
the script's own output is what appears below, unedited except for
formatting):

    keys   = {r.n_CREATURE_TYPE: r for r in CLINE if r.n_CLINE_TYPE == 7}
    for each Mob-Set number k this scene's placements use (56 of them):
        leader = keys[k].n_LEADER_BK1
        drop k if MOBS has no row for it, or that row's s_OUTFIT is empty,
            or MOBS_TIP.s_NAME/s_TITLE/s_OUTFIT is not cp874-representable
        else row = (k, keys[k].n_ID, leader, s_OUTFIT.split(';')[0],
                    MOBS_TIP.s_NAME or '', MOBS_TIP.s_TITLE or '',
                    MOBS.n_LEVEL_MIN, MOBS.n_RANK,
                    STANDARD_MOB[n_LEVEL_MIN].n_HPMAX, MOBS.n_MOB_USAGE)
    placements = every row of Bg0007.placements.tsv as
        (index, template_ids, running instance count per template_ids,
         x, y, z), in file order - no sentinel rows this scene (see above).

WHAT THIS MODULE DOES NOT CLAIM.

* Not that any of these 56 actors has been SEEN.  No human has been in this
  scene in this project's history (registry ``status:
  never_sent_to_any_client_by_this_project``, and ``login_entry_allowed`` is
  still ``false`` as of this module's own construction round).  The
  client-observable layer for this scene is empty until an attended round
  looks.
* Not that this census (built by ``world_population_bg0007``, a sibling
  module, not this one) is what raises these actors on a real server.
* Not leader+crew.  Like every sibling crosswalk this implements
  ``n_LEADER_BK1`` only.  Measured for this scene: 0 of CLINE type 7's 56
  rows carry any ``n_CREW`` value at all, so there is no pet/crew group this
  reading silently drops.
* Not wired at import time in this module - wiring
  (``CENSUS_SOURCES``/``ROSTER_COMPOSERS``/``lane_hooks`` console reader) and
  the door-open (``login_entry_allowed``) are both done by THIS SAME ROUND's
  other files, following the compressed build+wire+open precedent rounds
  ``l03cgh``/``fx0007``/``p4wire``/``p7wm17`` set for scenes 5, 6, 8 and 3
  (the generic contract test
  ``tests/test_lane_a_scene_census.py::ComposerContractTests`` already
  assumes every scene this lane composes for is also open at login).
"""
from __future__ import annotations

from dataclasses import dataclass


# Convention marker: shippable, no scenario flag - matching the seven
# sibling crosswalk modules' own convention.
production_allowed = True
test_only = False

SCENE_N_ID = 7
SCENE_MODEL_ID = "Bg0007"
SCENE_CLINE_TYPE = 7
# SCENE_NAME.n_SCENE_LV for this scene.
SCENE_DECLARED_LEVEL = 81

SOURCE_SHA256 = {
    "gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv":
        'e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b',
    "gamedata/tables/CONSTDATA_TH__CLINE.tsv":
        'aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40',
    "gamedata/tables/CONSTDATA_TH__MOBS.tsv":
        '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    "gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv":
        'e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f',
    "gamedata/tables/CONSTDATA_TH__STANDARD_MOB.tsv":
        '4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925',
    "gamedata/scene/Bg0007/Bg0007.placements.tsv":
        '3a0e8d9a11a24f1f0825a6ecc83d1f6fb43e51c0a5b8338fd30a8abf15ccc15d',
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  Costs 12 of the 68
# placements (see module docstring for the two distinct failure shapes).
UNRESOLVED = {
    1: (2200, 361, 'MOBS has no row for this leader'),
    101: (2245, 10033, 'MOBS row carries no s_OUTFIT avatar template'),
    102: (2246, 10034, 'MOBS row carries no s_OUTFIT avatar template'),
    103: (2247, 10035, 'MOBS row carries no s_OUTFIT avatar template'),
    104: (2248, 10036, 'MOBS row carries no s_OUTFIT avatar template'),
    105: (2249, 10037, 'MOBS row carries no s_OUTFIT avatar template'),
    106: (2250, 10038, 'MOBS row carries no s_OUTFIT avatar template'),
    107: (2251, 10039, 'MOBS row carries no s_OUTFIT avatar template'),
    108: (2252, 10040, 'MOBS row carries no s_OUTFIT avatar template'),
    109: (2253, 10041, 'MOBS row carries no s_OUTFIT avatar template'),
    110: (2254, 10042, 'MOBS row carries no s_OUTFIT avatar template'),
    111: (2255, 0, 'MOBS has no row for this leader'),
}

# MOBS rows in this scene that list SEVERAL avatar templates separated by
# ';', as leader n_ID -> the whole string.  The table below ships the FIRST
# variant; ``_self_check`` refuses if a ';' ever reaches the shipped column.
# [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION]
MULTI_VARIANT_OUTFITS = {
    385: 'M003_000_002_SP1;M003_000_002_SP2',
    386: 'M006_000_002_SP1;M006_000_002_SP2',
    387: 'M005_000_004_SP1;M005_000_004_SP2',
    389: 'M002_001_000_SP1;M002_001_000_SP2',
    391: 'M022_000_002_SP1;M022_000_002_SP2',
    392: 'M023_000_000_SP1;M023_000_000_SP2',
    394: 'M003_001_001_SP1;M003_001_001_SP2',
    396: 'M023_001_002_SP1;M023_001_002_SP2',
}


@dataclass(frozen=True)
class SceneIdentity:
    """One resolved actor: who it is, what it wears, what its label says."""

    template_id: int
    cline_row_id: int
    mobs_n_id: int
    outfit: str
    name: str
    title: str
    level: int
    rank: int
    max_hp: int
    mob_usage: int


# (Mob-Set number, CLINE row n_ID, MOBS.n_ID, shipped s_OUTFIT,
#  MOBS_TIP.s_NAME, MOBS_TIP.s_TITLE, MOBS.n_LEVEL_MIN, MOBS.n_RANK,
#  STANDARD_MOB[level].n_HPMAX, MOBS.n_MOB_USAGE)
# 44 rows: every Mob-Set number this scene's placements use that CLINE type
# 7 resolves to a shippable body (cp874-representable name/title/outfit).
_RESOLVED_ROWS = (
    (2, 2201, 362, 'M055_000_000_N', 'Columbus', 'Marine Transport Station', 86, 0, 128549, 2),
    (3, 2202, 363, 'M012_000_000_N', 'Plato', 'Finding Treasure', 86, 0, 128549, 2),
    (4, 2203, 364, 'P_MALE_008_000_OSERO', 'Ousailuo', 'Vice Admiral', 86, 0, 128549, 2),
    (5, 2204, 365, 'M015_000_000_SP3', 'Mo Yuzi', '', 86, 0, 128549, 2),
    (6, 2205, 366, 'P_FEMALE_007_000_ERIA', 'Aaliyah', 'Army Medical', 86, 0, 128549, 2),
    (7, 2206, 367, 'P_MALE_006_001_N', 'Suspicious Voodoo Tribe', '', 86, 0, 128549, 2),
    (8, 2207, 368, 'M070_000_001_N', 'Madisen', 'Archaeology Professor', 86, 0, 128549, 2),
    (9, 2208, 369, 'P_FEMALE_011_000_PAKANA', 'Pacana', 'Voodoo Princess', 86, 0, 128549, 2),
    (10, 2209, 370, 'P_FEMALE_011_000_PAKANA', 'Pacana', 'Heathen Wives', 86, 0, 128549, 2),
    (11, 2210, 371, 'M012_000_000_N', 'Plato', 'Colonial Spiritual Mentor', 86, 0, 128549, 2),
    (12, 2211, 372, 'P_MALE_011_000_BALUM', 'Barum', 'Voodoo Chieftain', 86, 0, 128549, 2),
    (13, 2212, 373, 'M015_000_001_SP2', 'Mori Hiroko', 'Vagabond Messenger', 86, 0, 128549, 2),
    (14, 2213, 374, 'P_MALE_006_001_N', 'Voodoo', '', 86, 0, 128549, 2),
    (15, 2214, 375, 'P_FEMALE_006_000_KANYA', 'Kanya', 'Voodoo Beauty', 86, 0, 128549, 2),
    (16, 2215, 376, 'P_MALE_006_002_AMAL', 'Ammaroo', 'Stunner Wizards', 86, 0, 128549, 2),
    (17, 2216, 377, 'P_FEMALE_011_001_MARELPH', 'Mare Love', 'Everlasting Witch', 86, 0, 128549, 2),
    (18, 2217, 378, 'P_FEMALE_011_000_PAKANA', 'Pacana', 'Back-Pedal Bride', 86, 0, 128549, 2),
    (19, 2218, 379, 'P_MALE_006_000_INCA', 'Inca', 'Voodo Hero No.1', 86, 0, 128549, 2),
    (20, 2219, 380, 'P_MALE_006_001_N', 'Voodoo', 'Infected', 86, 0, 128549, 2),
    (21, 2220, 381, 'P_FEMALE_011_000_PAKANA', 'Pacana', 'Zombie Wife', 86, 0, 128549, 2),
    (22, 2221, 382, 'M023_000_000_SP1', 'wugawuga', 'Cannibalistic Baby', 86, 0, 128549, 2),
    (23, 2222, 383, 'M012_000_000_N', 'Plato', 'Delicious', 86, 0, 128549, 2),
    (24, 2223, 384, 'M023_000_002_SP3', 'Vuvuzela', 'Demon Fierce', 86, 0, 128549, 2),
    (25, 2224, 385, 'M003_000_002_SP1', 'Wild ape', '', 81, 1, 108391, 1),
    (26, 2225, 386, 'M006_000_002_SP1', 'Purple turtle', '', 81, 1, 108391, 1),
    (27, 2226, 387, 'M005_000_004_SP1', 'Prairie deer', '', 81, 1, 108391, 1),
    (28, 2227, 388, 'M020_001_001_SP1', 'Ominous Bird', '', 81, 1, 108391, 1),
    (29, 2228, 389, 'M002_001_000_SP1', 'Dark Roast Lion', '', 81, 1, 108391, 1),
    (30, 2229, 390, 'M002_001_000_SP3', 'Dark roar', '', 81, 1, 108391, 1),
    (31, 2230, 391, 'M022_000_002_SP1', 'Curse Harpy', '', 81, 1, 108391, 1),
    (32, 2231, 392, 'M023_000_000_SP1', 'Voodoo Troll', '', 81, 1, 108391, 1),
    (33, 2232, 393, 'M023_000_000_SP3', 'Avarice Lerch', '', 81, 1, 108391, 1),
    (34, 2233, 394, 'M003_001_001_SP1', 'Zombie baboon', '', 81, 1, 108391, 1),
    (35, 2234, 395, 'M014_000_001_N', 'Remain Alert Weapon', '', 81, 1, 108391, 1),
    (36, 2235, 396, 'M023_001_002_SP1', 'Voodoo butcher', '', 81, 1, 108391, 1),
    (37, 2236, 397, 'M023_001_002_SP3', 'Green Eye Minced', '', 81, 1, 108391, 1),
    (38, 2237, 718, 'MAP001_000_000', 'Mirage reel', '', 105, 0, 228055, 2),
    (39, 2238, 719, 'MAP001_000_000', 'Mirage reel', '', 105, 0, 228055, 2),
    (40, 2239, 745, 'BULLETIN_BOARD', 'Task Board', '', 105, 0, 228055, 2),
    (41, 2240, 746, 'P_MALE_004_000_N', 'Navy soldier', '', 105, 0, 228055, 2),
    (42, 2241, 747, 'P_MALE_004_000_N', 'Navy soldier', '', 105, 0, 228055, 2),
    (43, 2242, 748, 'P_MALE_004_000_N', 'Navy soldier', '', 105, 0, 228055, 2),
    (44, 2243, 536, 'M015_001_001_SP2', 'Jet cat thieves No.7', '', 81, 1, 108391, 1),
    (45, 2244, 526, 'M015_001_001_SP2', 'Jet cat thieves No.8', '', 81, 1, 108391, 1),
)

IDENTITIES = {row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS}


@dataclass(frozen=True)
class Bg0007Placement:
    """One Bg0007 placement resolved to a real, named, bodied actor."""

    placement_index: int
    template_id: int
    mm_instance: int
    x: float
    y: float
    z: float
    identity: SceneIdentity | None

    @property
    def actor_identity(self) -> int:
        # The same formula every sibling scene uses.  Never sent in the same
        # generation as another scene's census - every builder refuses any
        # scene id but its own - so sharing the numeric space is a
        # collision in the abstract only.
        return 0x2000 + self.placement_index + 1

    @property
    def n_id(self) -> int:
        return self.identity.mobs_n_id

    @property
    def visual_preset(self) -> str:
        return self.identity.outfit

    @property
    def display_name(self) -> str:
        return self.identity.name

    @property
    def max_hp(self) -> int:
        return self.identity.max_hp


# (placement index, Mob-Set number, running instance count of that Mob-Set
# number within this file, x, y, z), every row of the scene's own placement
# file in file order.  No sentinel rows this scene (see module docstring).
_PLACEMENT_ROWS = (
    (0, 1, 1, -23276.765625, 7709.75927734375, 5220.09033203125),
    (1, 2, 1, -22594.728515625, 9188.69921875, 5220.07421875),
    (2, 3, 1, -20899.046875, 9427.349609375, 5220.07421875),
    (3, 4, 1, -16366.658203125, 9803.0478515625, 5184.06396484375),
    (4, 5, 1, -21026.462890625, 7748.07958984375, 5208.548828125),
    (5, 6, 1, -19862.05078125, 9033.7607421875, 5211.93603515625),
    (6, 7, 1, -14422.2724609375, 17125.140625, 6953.39990234375),
    (7, 8, 1, -18736.15625, 16124.07421875, 5959.95263671875),
    (8, 9, 1, -2631.908447265625, 6450.46923828125, 9312.212890625),
    (9, 10, 1, -14573.6982421875, 6167.0986328125, 5403.10791015625),
    (10, 11, 1, 9008.9541015625, 5155.525390625, 10470.060546875),
    (11, 12, 1, 9943.2978515625, 7633.9541015625, 10572.802734375),
    (12, 13, 1, 7167.69287109375, 6757.7470703125, 10570.2705078125),
    (13, 14, 1, 10943.8623046875, 6177.46142578125, 10570.2705078125),
    (14, 15, 1, 8062.2763671875, 8995.986328125, 10570.2705078125),
    (15, 16, 1, 4897.80810546875, -3094.338134765625, 10476.0302734375),
    (16, 17, 1, 17244.234375, 16225.5009765625, 11670.3896484375),
    (17, 18, 1, 8074.455078125, 16330.876953125, 10524.630859375),
    (18, 19, 1, 17354.58984375, 2350.8603515625, 10339.1123046875),
    (19, 20, 1, 17114.349609375, -6436.875, 10838.2724609375),
    (20, 21, 1, 7511.1875, -12109.2548828125, 11816.6845703125),
    (21, 22, 1, 12418.0537109375, -19377.771484375, 12188.98046875),
    (22, 23, 1, -1888.01806640625, -17729.986328125, 12017.810546875),
    (23, 24, 1, -6454.58544921875, -19052.86328125, 11863.7646484375),
    (24, 25, 1, -12269.7509765625, 9855.525390625, 6208.853515625),
    (25, 27, 1, -19106.384765625, 16047.994140625, 6035.8193359375),
    (26, 27, 2, -14518.828125, 17643.880859375, 7140.0234375),
    (27, 26, 1, -10339.4580078125, -4161.84912109375, 5261.509765625),
    (28, 28, 1, -10082.4375, 16337.6259765625, 7506.95556640625),
    (29, 28, 2, -6656.8134765625, 8682.6064453125, 7637.74951171875),
    (30, 29, 1, 738.4974975585938, 3341.0205078125, 10158.7236328125),
    (31, 29, 2, 3875.502685546875, -1856.577880859375, 10507.31640625),
    (32, 29, 3, 9728.013671875, -99.1886978149414, 10366.279296875),
    (33, 29, 4, 17132.1875, 4598.46337890625, 10507.6337890625),
    (34, 29, 5, 14190.5654296875, -342.5386047363281, 10338.3828125),
    (35, 30, 1, 1177.8848876953125, -5377.81787109375, 10404.1572265625),
    (36, 31, 1, 7300.35498046875, 14869.0712890625, 10526.1923828125),
    (37, 31, 2, 10785.28515625, 16237.4658203125, 10652.931640625),
    (38, 32, 1, 15969.7880859375, 9244.548828125, 10481.6787109375),
    (39, 32, 2, 15763.466796875, 13405.15625, 10970.6513671875),
    (40, 33, 1, 16700.453125, 15398.3828125, 11538.787109375),
    (41, 34, 1, 15172.5576171875, -7267.57080078125, 11017.220703125),
    (42, 34, 2, 11321.5791015625, -12213.005859375, 10946.9697265625),
    (43, 35, 1, 12862.5927734375, -18777.833984375, 12415.1875),
    (44, 35, 2, 7798.28857421875, -16908.482421875, 12034.6396484375),
    (45, 36, 1, 4082.7783203125, -19120.73046875, 12306.849609375),
    (46, 36, 2, 2815.865478515625, -14871.14453125, 11965.013671875),
    (47, 36, 3, -3026.287109375, -18356.8203125, 11829.7314453125),
    (48, 37, 1, -8197.6513671875, -19397.052734375, 11892.1669921875),
    (49, 38, 1, -21058.986328125, 6229.41357421875, 5253.787109375),
    (50, 39, 1, 7814.9853515625, 5497.771484375, 10458.7900390625),
    (51, 40, 1, -21767.69140625, 8373.947265625, 5156.98583984375),
    (52, 41, 1, -20483.267578125, 5109.814453125, 5208.93017578125),
    (53, 42, 1, -14374.9423828125, 5499.3427734375, 5371.52392578125),
    (54, 43, 1, -14859.83203125, 11568.8115234375, 5815.61083984375),
    (55, 44, 1, 11958.9775390625, 16993.32421875, 10483.7509765625),
    (56, 45, 1, 15880.2958984375, -13514.4677734375, 12391.2353515625),
    (57, 101, 1, -12984.1806640625, -2617.23095703125, 5279.76904296875),
    (58, 102, 1, 8680.5673828125, 5681.56494140625, 10411.453125),
    (59, 103, 1, 6286.40283203125, 16299.15234375, 10564.55078125),
    (60, 104, 1, -6578.64453125, 14919.171875, 7986.78125),
    (61, 105, 1, -21182.001953125, 9094.9716796875, 5157.60302734375),
    (62, 106, 1, -14882.859375, 16319.57421875, 6738.4453125),
    (63, 107, 1, -15357.326171875, 3558.4130859375, 4798.19384765625),
    (64, 108, 1, 2007.896484375, -5185.7294921875, 10435.8046875),
    (65, 109, 1, 17055.26953125, 15031.3779296875, 11456.849609375),
    (66, 110, 1, 14359.1533203125, -15919.021484375, 12367.70703125),
    (67, 111, 1, -4304.54052734375, -8717.5615234375, 7853.4453125),
)

PLACEMENT_COUNT = len(_PLACEMENT_ROWS)


class Bg0007IdentityError(ValueError):
    """A refusal from this module, always with a reason in the message."""


def identity_for(template_id: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    ``None`` is exactly the 12 sets in ``UNRESOLVED`` and nothing else: this
    function never substitutes, and never falls back to the Mob-Set number
    that ``GT-078`` proved wrong on the owner's screen.
    """
    if type(template_id) is not int or type(template_id) is bool:
        raise Bg0007IdentityError("template id must be an int")
    return IDENTITIES.get(template_id)


def shippable_placements() -> tuple[Bg0007Placement, ...]:
    """The 56 placements of the 68 that resolve to a real identity."""
    out = []
    for index, template_id, mm_instance, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(template_id)
        if identity is None:
            continue
        out.append(Bg0007Placement(
            index, template_id, mm_instance, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The 12 that are dropped, each with the id and the reason.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH ones and WHY.
    """
    out = []
    for index, template_id, _mm, x, y, z in _PLACEMENT_ROWS:
        if template_id in IDENTITIES:
            continue
        cline_row_id, leader, reason = UNRESOLVED.get(
            template_id, (0, 0, "set not in CLINE 7"))
        out.append({
            "placement_index": index,
            "template_id": template_id,
            "cline_row_id": cline_row_id,
            "leader_n_id": leader,
            "reason": reason,
            "xyz": (x, y, z),
        })
    return tuple(out)


def no_set_number_is_shipped_as_identity() -> bool:
    """Control 3, executable.  See the module docstring for its real weight:
    no resolved row ships its own Mob-Set number as its identity - it only
    catches a future regeneration that falls back to the Mob-Set number
    itself, which is the specific regression GT-078 was."""
    return all(row[0] != row[2] for row in _RESOLVED_ROWS)


def _self_check() -> None:
    """Refuse at import if this table has drifted out of the shape the
    module docstring claims.  Fail-closed: a bad table must not reach a
    census builder at all, and an ImportError names the file.
    """
    if len(_RESOLVED_ROWS) != 44:
        raise Bg0007IdentityError(
            "expected 44 resolved sets, found %d" % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg0007IdentityError("duplicate Mob-Set number in the table")
    if len(UNRESOLVED) != 12:
        raise Bg0007IdentityError(
            "expected 12 unresolved sets, found %d" % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg0007IdentityError("a set is both resolved and unresolved")
    if len(_PLACEMENT_ROWS) != 68:
        raise Bg0007IdentityError(
            "expected 68 placements, found %d" % len(_PLACEMENT_ROWS))
    # Control 1: every Mob-Set number this scene's placements use is either
    # resolved or named as unresolved, and the two sets together are EXACTLY
    # this scene's used keys - a placement keyed by a number this table has
    # never heard of means the placement file and the crosswalk came from
    # different extractions.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if scene_sets != table_sets:
        raise Bg0007IdentityError(
            "placement Mob-Set numbers and this table's keys disagree: %r"
            % sorted(scene_sets ^ table_sets))
    if len(table_sets) != 56:
        raise Bg0007IdentityError(
            "expected 56 distinct Mob-Set numbers, found %d" % len(table_sets))
    if not no_set_number_is_shipped_as_identity():
        raise Bg0007IdentityError(
            "a row ships its own Mob-Set number as an identity")
    for row in _RESOLVED_ROWS:
        (template_id, cline_row_id, n_id, outfit, name, title, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1:
            raise Bg0007IdentityError(
                "set %d carries no CLINE row locator" % template_id)
        if ";" in outfit:
            raise Bg0007IdentityError(
                "set %d ships a multi-variant outfit string" % template_id)
        if not outfit or not outfit.isascii():
            raise Bg0007IdentityError(
                "set %d has an empty or non-ASCII outfit" % template_id)
        if not name.isascii() or not title.isascii():
            raise Bg0007IdentityError(
                "set %d has a non-ASCII name or title" % template_id)
        if not name:
            raise Bg0007IdentityError(
                "set %d has no display name" % template_id)
        if max_hp < 1 or level < 1:
            raise Bg0007IdentityError("set %d has a bad level/HP" % template_id)
    if len(shippable_placements()) != 56:
        raise Bg0007IdentityError("expected 56 shippable placements")
    if len(unshippable_placements()) != 12:
        raise Bg0007IdentityError("expected 12 unshippable placements")
    ids = [p.actor_identity for p in shippable_placements()]
    if len(ids) != len(set(ids)):
        raise Bg0007IdentityError("actor identities collide within this table")


_self_check()
