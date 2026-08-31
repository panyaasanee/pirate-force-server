"""Who each Bg0003 placement actually IS - Spice Paradise Island's real cast.

LANE-A (WORLD).  ``COO-DECISION 2026-08-30T14:41+07:00`` (pf_bridge
``notes_to_chief/20260830_1441_COO-DECISION-scene4-slave-market-first-door.md``)
approved building the ten still-shut doors surveyed in round ``12lyda`` in
native-placement-count order ("no need to ask again per door").  Scenes 4, 5,
10, 14, 6 and 8 are open; this is the sixth door in the sequence and the
next-highest native placement count among the five still shut (3, 7, 9, 11,
130): scene 3 (Bg0003, "Spice Paradise Island", 72 placements).  This module
is the identity half, the same split every earlier crosswalk used;
``world_population_bg0003`` is the census half.

THE CROSSWALK, RE-DERIVED HERE RATHER THAN TAKEN FROM A CITATION.
``SCENE_NAME[s_MODLE_ID=BG0003].n_CLINE_TYPE`` was read directly off the
bridge clone this round:

    SCENE_NAME[s_MODLE_ID=BG0003].n_ID          = 3
    SCENE_NAME[s_MODLE_ID=BG0003].n_CLINE_TYPE  = 3    (a real value, direct)
    SCENE_NAME[s_MODLE_ID=BG0003].n_SCENE_LV    = 25
    CLINE[(3, <Mob-Set number>)].n_LEADER_BK1   = the real MOBS.n_ID
    MOBS[n_ID].s_OUTFIT                         = the avatar the client loads
    MOBS_TIP[n_ID].s_NAME / s_TITLE             = the label under the actor
    STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX      = max HP (the one derived col)

Same direct-selector shape ``world_bg0004_identity``, ``world_bg0005_identity``,
``world_bg0006_identity``, ``world_bg0008_identity`` and ``world_bg0010_identity``
all ship (one of RE-128's 19 direct CLINE types, not one of its 240 instance
scenes).

WHAT IS ESTABLISHED HERE AND WHAT IS NOT, STATED THE SAME WAY THE OTHER SIX
CROSSWALK MODULES STATE IT.

    ESTABLISHED - THE TABLE.  This scene's cast is drawn from CLINE type 3's
    leader column.  CONTROL 1 below is exact: this scene's placements use
    exactly 51 distinct Mob-Set numbers (1-40, 101-111) and every one of the
    51 has a row in CLINE type 3 - which is CLINE type 3's ENTIRE key range
    (51 rows total, counted directly rather than trusted from the registry's
    own ``native_definition_count`` of 52 - see the discrepancy note below),
    the same 'placement file touches every key its own CLINE type owns'
    shape scenes 5's, 6's and 8's own crosswalks carry (unlike bg0004's
    61-of-62 and bg0010's 40-of-41).

    NOT ESTABLISHED - THE PAIRING.  Which leader belongs to which Mob-Set
    number.  No human has stood in this scene (registry ``status:
    never_sent_to_any_client_by_this_project``), so every name below is a
    table inference, the bottom of the evidence order COO set on
    2026-08-28T21:30, until an attended round looks.

DISCREPANCY, MEASURED AND NOT SILENTLY RECONCILED.  The registry's own
``native_definition_count`` for scene 3 reads 52; this round's own count of
CLINE type 3's rows (grouped by ``n_CREATURE_TYPE``, checked for duplicates -
there are none) is 51, and 51 is also exactly the count of distinct Mob-Set
numbers this scene's own 72 placements use (CONTROL 1).  The two numbers
agreeing with each other and disagreeing with the registry's field is the
same shape as bg0004's 61-of-62, bg0010's 40-of-41 and bg0008's 49-of-48
differences: recorded here rather than "fixed" in the registry, because this
round did not re-derive whatever the registry's own count measured and
cannot say which of the two is wrong without doing that separately.

CONTROL 1 - EXACT SUBSET, MEASURED.  The 72 placements resolve to 51 distinct
Mob-Set numbers; CLINE type 3 has exactly 51 keys (1-40, 101-111); the two
sets are identical (no gap either direction).

CONTROL 2 - NOT REBUILT HERE.  No ``world_bg0015_identity.
SCENE_LEVEL_CONTROL`` row exists for BG0003 (checked: that table only cites
scenes it was built against at the time, and this scene was never one of
them) - the same absence bg0006's and bg0008's own Control 2 recorded, not
silently skipped.

CONTROL 3 - NO SELF-MAPPING, WEAK, SAME CAVEAT AS THE OTHER SIX SCENES.  0
of the 41 resolved rows have ``mobs_n_id == template_id`` (measured, not
assumed): none.  A shape check, not evidence.

TEN OF THE 51 SETS DO NOT RESOLVE (COST 10 PLACEMENTS), TWO FAMILIAR
FAILURE SHAPES, NO THIRD ONE THIS TIME.

* Set [2] -> leader [37].  CLINE type 3's own row for key 2 carries a real,
  non-zero ``n_LEADER_BK1`` (37) but ``CONSTDATA MOBS`` has no row for it -
  the same "MOBS has no row" family bg0005's set 1, bg0006's sets 1/114 and
  bg0008's sets 1/106 needed, five occurrences of the shape across the
  project so far, one here.
* Sets [101, 102, 103, 104, 105, 106, 107, 108, 109] -> leaders [10005,
  10006, 10007, 10008, 10009, 10010, 10011, 10012, 10013].  Every one HAS a
  ``CONSTDATA MOBS`` row but its ``s_OUTFIT`` column is empty - the
  identical 'path-finding helper, not a creature' shape every sibling
  scene's own 101+ block carries (bg0004: 6, bg0005: 4, bg0006: 9, bg0008:
  5, bg0010: 5; this scene: 9).  Unlike every sibling, this scene's own
  101+ block does NOT cover its entire tail: sets 110 and 111 (Loverage
  Nurse, Penguin Searcher) both resolve.
* NO CJK/non-cp874 name this scene needed - unlike bg0006's three
  teleporter drops, every one of this scene's 41 resolved ``MOBS_TIP`` rows
  is plain ASCII, checked directly (not assumed from the absence of a
  failure).

NINE SETS LIST TWO OR MORE AVATAR TEMPLATES SEPARATED BY ';'.  Same rule and
the same open question as bg0004's nine, bg0005's ten, bg0006's ten,
bg0008's ten and bg0010's twelve: ship the FIRST variant, keep the whole
string in ``MULTI_VARIANT_OUTFITS``, and ``_self_check`` refuses at import if
a raw ';' ever reaches the shipped column.  [LANE-A ASSUMPTION - AWAITING
COO/OWNER CONFIRMATION].  Leaders [55, 56, 57, 58, 59, 63, 64, 908, 7042] (9
of the 41 resolved sets), placed unevenly: the nine multi-variant sets
together cover 25 of the 62 shippable placements (measured this round, not
estimated).  ONE OF THE NINE IS NOT A TWO-VARIANT ROW LIKE EVERY OTHER SCENE
HAS SHIPPED SO FAR: leader 908's own ``s_OUTFIT`` lists NINE variants
(``P_MALE_015_000_SINGLE`` through ``SINGLE9``), the widest fan-out any
crosswalk in this lane has recorded; the shipped column still ships only the
first, same rule, wider string.

NO NAME-VS-TEMPLATE DISAGREEMENT, NO EXTRA SPAWN TRIPLE, NO MULTI-TEMPLATE
ROW, NO EXTRACTION-UNRESOLVED SENTINEL.  Checked directly against this
scene's own placement file: no row carries ``extra_triple_count > 0``, no row
lists more than one template id, and no row's ``template_ids`` column reads
the literal ``UNRESOLVED``.  Same clean shape bg0005's, bg0006's and bg0008's
own crosswalks carry on these axes.

NO CREW.  Measured for this scene: 0 of CLINE type 3's 51 rows carry any
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
this scene (n_id 3) records the marker point 405.0 units from the nearest of
this scene's 72 native placements, OUTSIDE the placement extents.  This row
does NOT carry ``table_row_differences.the_two_interiors`` (checked, not
assumed - that flag names only scenes 10 and 11).  Still 'recorded, not
enforced' (a .npc file is not terrain), but a fact worth naming rather than
leaving buried in the registry JSON.

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
    gamedata/scene/Bg0003/bg0003.placements.tsv

THE JOIN, EXACTLY, SO IT CAN BE MECHANISED LATER (done by a throwaway script
against committed TSVs read directly this round, not by hand - the tables
are large enough that hand transcription would itself be an error source;
the script's own output is what appears below, unedited except for
formatting):

    keys   = {r.n_CREATURE_TYPE: r for r in CLINE if r.n_CLINE_TYPE == 3}
    for each Mob-Set number k this scene's placements use (51 of them):
        leader = keys[k].n_LEADER_BK1
        drop k if MOBS has no row for it, or that row's s_OUTFIT is empty,
            or MOBS_TIP.s_NAME/s_TITLE/s_OUTFIT is not cp874-representable
        else row = (k, keys[k].n_ID, leader, s_OUTFIT.split(';')[0],
                    MOBS_TIP.s_NAME or '', MOBS_TIP.s_TITLE or '',
                    MOBS.n_LEVEL_MIN, MOBS.n_RANK,
                    STANDARD_MOB[n_LEVEL_MIN].n_HPMAX, MOBS.n_MOB_USAGE)
    placements = every row of bg0003.placements.tsv as
        (index, template_ids, running instance count per template_ids,
         x, y, z), in file order - no sentinel rows this scene (see above).

WHAT THIS MODULE DOES NOT CLAIM.

* Not that any of these 62 actors has been SEEN.  No human has been in this
  scene in this project's history (registry ``status:
  never_sent_to_any_client_by_this_project``, and ``login_entry_allowed`` is
  still ``false`` as of this module's own construction round).  The
  client-observable layer for this scene is empty until an attended round
  looks.
* Not that this census (built by ``world_population_bg0003``, a sibling
  module, not this one) is what raises these actors on a real server.
* Not leader+crew.  Like every sibling crosswalk this implements
  ``n_LEADER_BK1`` only.  Measured for this scene: 0 of CLINE type 3's 51
  rows carry any ``n_CREW`` value at all, so there is no pet/crew group this
  reading silently drops.
* Not wired at import time in this module - wiring
  (``CENSUS_SOURCES``/``ROSTER_COMPOSERS``/``lane_hooks`` console reader) and
  the door-open (``login_entry_allowed``) are both done by THIS SAME ROUND's
  other files, following the compressed build+wire+open precedent rounds
  ``l03cgh``/``fx0007``/``p4wire`` set for scenes 5, 6 and 8 (the generic
  contract test ``tests/test_lane_a_scene_census.py::ComposerContractTests``
  already assumes every scene this lane composes for is also open at login).
"""
from __future__ import annotations

from dataclasses import dataclass


# Convention marker: shippable, no scenario flag - matching the six sibling
# crosswalk modules' own convention.
production_allowed = True
test_only = False

SCENE_N_ID = 3
SCENE_MODEL_ID = "Bg0003"
SCENE_CLINE_TYPE = 3
# SCENE_NAME.n_SCENE_LV for this scene.
SCENE_DECLARED_LEVEL = 25

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
    "gamedata/scene/Bg0003/bg0003.placements.tsv":
        '5a03747a6cb3c6766fe335863032008c30f82c67dfdc52c701ec44223056ac46',
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  Costs 10 of the 72
# placements (see module docstring for the two distinct failure shapes).
UNRESOLVED = {
    2: (1401, 37, 'MOBS has no row for this leader'),
    101: (1436, 10005, 'MOBS row carries no s_OUTFIT avatar template'),
    102: (1437, 10006, 'MOBS row carries no s_OUTFIT avatar template'),
    103: (1438, 10007, 'MOBS row carries no s_OUTFIT avatar template'),
    104: (1439, 10008, 'MOBS row carries no s_OUTFIT avatar template'),
    105: (1440, 10009, 'MOBS row carries no s_OUTFIT avatar template'),
    106: (1441, 10010, 'MOBS row carries no s_OUTFIT avatar template'),
    107: (1442, 10011, 'MOBS row carries no s_OUTFIT avatar template'),
    108: (1443, 10012, 'MOBS row carries no s_OUTFIT avatar template'),
    109: (1444, 10013, 'MOBS row carries no s_OUTFIT avatar template'),
}

# MOBS rows in this scene that list SEVERAL avatar templates separated by
# ';', as leader n_ID -> the whole string.  The table below ships the FIRST
# variant; ``_self_check`` refuses if a ';' ever reaches the shipped column.
# [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION]
MULTI_VARIANT_OUTFITS = {
    55: 'M006_000_001_SP1;M006_000_001_SP2',
    56: 'M013_000_000_SP1;M013_000_000_SP2',
    57: 'M004_000_000_SP1;M004_000_000_SP2',
    58: 'M028_001_000_SP1;M028_001_000_SP2',
    59: 'M002_000_002_SP1;M002_000_002_SP2',
    63: 'M001_003_000_N;M001_003_000_SP1',
    64: 'M003_001_000_SP1;M003_001_000_SP2',
    908: (
        'P_MALE_015_000_SINGLE;P_MALE_015_000_SINGLE2;'
        'P_MALE_015_000_SINGLE3;P_MALE_015_000_SINGLE4;'
        'P_MALE_015_000_SINGLE5;P_MALE_015_000_SINGLE6;'
        'P_MALE_015_000_SINGLE7;P_MALE_015_000_SINGLE8;'
        'P_MALE_015_000_SINGLE9'
    ),
    7042: 'M024_001_001_SP1;M024_001_001_SP2',
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
# 41 rows: every Mob-Set number this scene's placements use that CLINE type
# 3 resolves to a shippable body (cp874-representable name/title/outfit).
_RESOLVED_ROWS = (
    (1, 1400, 36, 'M055_000_000_N', 'Columbus', 'Marine Transport Station', 35, 0, 7980, 2),
    (3, 1402, 38, 'P_FEMALE_001_001_RENA', 'Reyna', 'Spice Merchant', 35, 0, 7980, 2),
    (4, 1403, 39, 'M015_000_000_SP2', 'Mo Yuzi', 'Naval Communications Bureau', 35, 0, 7980, 2),
    (5, 1404, 40, 'P_MALE_001_001_KARL', 'Carle', 'Nautilus Leader', 35, 0, 7980, 2),
    (6, 1405, 41, 'P_MALE_010_000_MARTIN', 'Martin', 'Commander', 35, 0, 7980, 2),
    (7, 1406, 42, 'P_FEMALE_009_001_N', 'Excited Spice Merchant', '', 35, 0, 7980, 2),
    (8, 1407, 43, 'P_MALE_002_002_EION', 'Iain', 'Novice Adventurer', 35, 0, 7980, 2),
    (9, 1408, 44, 'M055_001_000_N', 'Magellan', 'Maritime Daughter', 35, 0, 7980, 2),
    (10, 1409, 45, 'P_MALE_007_001_OLD_MAGELLAN', 'Magellan Old Man', '', 35, 0, 7980, 7),
    (11, 1410, 46, 'P_FEMALE_012_001_RULALA', 'Lulala', 'Spice Beauty', 35, 0, 7980, 2),
    (12, 1411, 47, 'P_MALE_001_002_JAMES', 'James', 'Gold Shark Leader', 35, 0, 7980, 2),
    (13, 1412, 48, 'P_MALE_009_001_N', 'Avaricious Spice Merchant', '', 35, 0, 7980, 2),
    (14, 1413, 49, 'M004_000_004_N', 'Alien exquisite', '', 35, 0, 7980, 2),
    (15, 1414, 50, 'M015_000_000_SP1', 'Mo Yuzi', 'Naval Communications Bureau', 35, 0, 7980, 2),
    (16, 1415, 51, 'M070_000_001_N', 'Madisen', 'Archaeology Professor', 35, 0, 7980, 2),
    (17, 1416, 52, 'M012_000_000_N', 'Plato', 'Atlantis Prime Minister', 35, 0, 7980, 2),
    (18, 1417, 53, 'M012_000_000_N', 'Plato', 'Wizards', 35, 0, 7980, 2),
    (19, 1418, 54, 'P_FEMALE_018_000_LORA', 'Laura', 'Treasure Hunter', 35, 0, 7980, 2),
    (20, 1419, 55, 'M006_000_001_SP1', 'Sand dragon', '', 31, 1, 5636, 1),
    (21, 1420, 56, 'M013_000_000_SP1', 'lenka', '', 32, 1, 6174, 1),
    (22, 1421, 57, 'M004_000_000_SP1', 'Greenwood Magic Flower', '', 33, 1, 6750, 1),
    (23, 1422, 58, 'M028_001_000_SP1', 'Thorn Hammer Bee', '', 35, 1, 7980, 1),
    (24, 1423, 59, 'M002_000_002_SP1', 'Jungle Tiger', '', 36, 1, 8661, 1),
    (25, 1424, 60, 'M002_000_002_SP3', 'Jungle Big Tiger', '', 37, 1, 9382, 1),
    (26, 1425, 61, 'M004_000_002_SP1', 'Toxic Vine', '', 38, 1, 10149, 1),
    (27, 1426, 62, 'M014_000_000_N', 'Ancient Civilization Alert Weapon', '', 39, 1, 10962, 1),
    (28, 1427, 63, 'M001_003_000_N', 'Green scales pirates', '', 41, 1, 12871, 1),
    (29, 1428, 64, 'M003_001_000_SP1', 'Ward Kingkong', '', 42, 1, 13854, 1),
    (30, 1429, 65, 'M003_001_000_SP3', 'Ward Apes', '', 43, 1, 14910, 1),
    (31, 1430, 232, 'MAP001_000_000', 'Mirage reel', '', 105, 0, 228055, 2),
    (32, 1431, 233, 'MAP001_000_000', 'Mirage reel', '', 105, 0, 228055, 2),
    (33, 1432, 515, 'M015_001_001_SP1', 'Jet cat thieves No.1', '', 39, 1, 10962, 1),
    (34, 1433, 194, 'M015_001_001_SP1', 'Jet cat thieves No.2', '', 44, 1, 16009, 1),
    (35, 1434, 824, 'P_MALE_019_000_SEPHIROTH', 'Sai Feross', 'Treasure Hunters No.1', 40, 0, 11925, 2),
    (36, 1435, 825, 'P_MALE_019_000_SEPHIROTH', 'Sai Feross', 'Treasure Hunters No.2', 40, 0, 11925, 2),
    (37, 1445, 907, 'M000_000_001_SP1', 'Sediment Wolf', '', 32, 1, 6174, 1),
    (38, 1446, 908, 'P_MALE_015_000_SINGLE', 'Jungle Fugitive', '', 33, 1, 6750, 1),
    (39, 1447, 915, 'P_FEMALE_002_000_LAN', 'Isla', 'Nautilus Leader', 20, 0, 1771, 2),
    (40, 1448, 919, 'MAP_OBJ_CRYSTAL', 'Energy Strength Crystal', '', 10, 0, 421, 2),
    (110, 1449, 927, 'M019_001_000_SP1', 'Loverage Nurse', '', 10, 0, 421, 2),
    (111, 1450, 7042, 'M024_001_001_SP1', 'Penguin Searcher', 'Serious and responsible', 99, 0, 192488, 2),
)

IDENTITIES = {row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS}


@dataclass(frozen=True)
class Bg0003Placement:
    """One Bg0003 placement resolved to a real, named, bodied actor."""

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
    (0, 1, 1, -20819.400390625, 16992.1328125, -812.9119262695312),
    (1, 2, 1, -20820.115234375, 15949.2392578125, -729.5115966796875),
    (2, 3, 1, -20346.15625, 15686.0439453125, -671.9505004882812),
    (3, 4, 1, -14033.58203125, 15565.671875, 2282.69384765625),
    (4, 5, 1, -13368.765625, 14321.3505859375, 2318.444091796875),
    (5, 6, 1, -13662.912109375, 13335.5625, 2330.84326171875),
    (6, 7, 1, -7459.3603515625, 6202.85888671875, 3528.978759765625),
    (7, 8, 1, 12033.9619140625, 18428.5859375, 1698.468505859375),
    (8, 9, 1, 5766.20556640625, 11798.4287109375, 1912.92724609375),
    (9, 10, 1, 5845.9775390625, 12044.123046875, 1898.466796875),
    (10, 13, 1, 18403.55859375, 12676.15625, 1663.572509765625),
    (11, 12, 1, 18155.658203125, 14343.4296875, 1613.7208251953125),
    (12, 14, 1, 21499.798828125, 19315.32421875, 1964.63525390625),
    (13, 15, 1, 23590.900390625, 1843.050537109375, 3832.22900390625),
    (14, 16, 1, 16353.51953125, -12510.14453125, 5300.1083984375),
    (15, 17, 1, 18689.20703125, -21105.962890625, 6213.4228515625),
    (16, 18, 1, 6983.2900390625, -13195.974609375, 3676.212646484375),
    (17, 19, 1, -10479.12109375, -21173.927734375, 4601.875),
    (18, 20, 1, -19386.78515625, 15579.6015625, -444.6130065917969),
    (19, 20, 2, -20196.18359375, 9498.1767578125, -227.99009704589844),
    (20, 21, 1, -8610.466796875, 5240.6318359375, 3423.87548828125),
    (21, 21, 2, -9461.51953125, 455.885009765625, 3762.4970703125),
    (22, 22, 1, 3645.974365234375, 11787.09375, 2135.152587890625),
    (23, 22, 2, 3412.60791015625, 9865.408203125, 2442.676513671875),
    (24, 23, 1, 6121.31982421875, 19462.703125, 1896.88720703125),
    (25, 23, 2, 19238.38671875, 19773.380859375, 2108.85498046875),
    (26, 24, 1, 16384.33984375, 17385.7734375, 1647.2923583984375),
    (27, 26, 1, 21344.287109375, -3283.4951171875, 3806.893310546875),
    (28, 26, 2, 22493.90625, 528.2396850585938, 3779.760986328125),
    (29, 27, 1, 6254.3740234375, -18785.84765625, 3989.9228515625),
    (30, 28, 1, -9256.951171875, -22420.830078125, 4859.171875),
    (31, 28, 2, -19386.224609375, -10951.265625, 4194.123046875),
    (32, 29, 1, -15606.49609375, -16462.71484375, 4143.380859375),
    (33, 30, 1, -19654.26953125, -20399.740234375, 4484.51220703125),
    (34, 27, 2, 15594.1728515625, -20767.05078125, 5977.96142578125),
    (35, 25, 1, 16643.705078125, 7747.16455078125, 2645.375732421875),
    (36, 11, 1, 14301.34765625, -5531.60546875, 4089.732421875),
    (37, 31, 1, -14447.5625, 15526.3525390625, 2282.696044921875),
    (38, 32, 1, 23259.140625, 1762.527587890625, 3815.00341796875),
    (39, 34, 1, -19164.9375, -12788.56640625, 4082.4619140625),
    (40, 33, 1, 16968.025390625, -6367.26025390625, 3993.98095703125),
    (41, 27, 3, 12276.7724609375, -7199.38330078125, 3921.6875),
    (42, 27, 4, 16841.40625, -8830.693359375, 4388.2890625),
    (43, 35, 1, 19360.080078125, -20192.009765625, 5978.60791015625),
    (44, 36, 1, 18747.8125, -21632.853515625, 6321.92578125),
    (45, 20, 3, -21466.072265625, 9005.0185546875, -415.5306091308594),
    (46, 20, 4, -20553.7265625, 11076.2890625, -495.20721435546875),
    (47, 20, 5, -20237.484375, 13989.162109375, -418.6200866699219),
    (48, 20, 6, -19214.177734375, 17330.318359375, -487.8811950683594),
    (49, 101, 1, 12897.01953125, 14990.892578125, 1568.6016845703125),
    (50, 102, 1, 22972.3828125, -1324.11328125, 3849.34716796875),
    (51, 103, 1, 14103.03125, 19243.255859375, 1831.11572265625),
    (52, 104, 1, 15145.48828125, -8527.8154296875, 4370.83447265625),
    (53, 105, 1, -5087.908203125, -19319.603515625, 5532.11328125),
    (54, 106, 1, -14194.7900390625, -21113.1015625, 4317.81396484375),
    (55, 107, 1, 21031.46484375, 14973.0166015625, 2267.8994140625),
    (56, 108, 1, 20592.650390625, 19891.6328125, 1914.201904296875),
    (57, 109, 1, -18051.7265625, -11403.03125, 4142.345703125),
    (58, 37, 1, 10138.8359375, 16399.876953125, 1684.7646484375),
    (59, 38, 1, 6226.74658203125, 16404.419921875, 2038.9644775390625),
    (60, 40, 1, 18472.91015625, -14274.5712890625, 7870.68359375),
    (61, 39, 1, 24344.73828125, 2270.2578125, 3787.1875),
    (62, 21, 3, -6792.8564453125, 5370.7880859375, 3563.15234375),
    (63, 21, 4, -7820.90478515625, -1744.419189453125, 3692.958251953125),
    (64, 28, 3, -17851.16796875, -8092.4951171875, 4257.5810546875),
    (65, 29, 2, -18174.408203125, -19453.435546875, 4226.31494140625),
    (66, 28, 4, -9582.1826171875, -19362.123046875, 4849.7421875),
    (67, 24, 2, 21183.7578125, 12163.5556640625, 1860.556884765625),
    (68, 38, 2, 5616.58251953125, 13901.7685546875, 1922.6619873046875),
    (69, 37, 2, 10634.986328125, 13274.2041015625, 2051.42724609375),
    (70, 110, 1, 15156.5595703125, 14237.0927734375, 1618.9381103515625),
    (71, 111, 1, 4464.21875, -13356.6806640625, 6411.94921875),
)

PLACEMENT_COUNT = len(_PLACEMENT_ROWS)


class Bg0003IdentityError(ValueError):
    """A refusal from this module, always with a reason in the message."""


def identity_for(template_id: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    ``None`` is exactly the 10 sets in ``UNRESOLVED`` and nothing else: this
    function never substitutes, and never falls back to the Mob-Set number
    that ``GT-078`` proved wrong on the owner's screen.
    """
    if type(template_id) is not int or type(template_id) is bool:
        raise Bg0003IdentityError("template id must be an int")
    return IDENTITIES.get(template_id)


def shippable_placements() -> tuple[Bg0003Placement, ...]:
    """The 62 placements of the 72 that resolve to a real identity."""
    out = []
    for index, template_id, mm_instance, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(template_id)
        if identity is None:
            continue
        out.append(Bg0003Placement(
            index, template_id, mm_instance, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The 10 that are dropped, each with the id and the reason.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH ones and WHY.
    """
    out = []
    for index, template_id, _mm, x, y, z in _PLACEMENT_ROWS:
        if template_id in IDENTITIES:
            continue
        cline_row_id, leader, reason = UNRESOLVED.get(
            template_id, (0, 0, "set not in CLINE 3"))
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
    if len(_RESOLVED_ROWS) != 41:
        raise Bg0003IdentityError(
            "expected 41 resolved sets, found %d" % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg0003IdentityError("duplicate Mob-Set number in the table")
    if len(UNRESOLVED) != 10:
        raise Bg0003IdentityError(
            "expected 10 unresolved sets, found %d" % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg0003IdentityError("a set is both resolved and unresolved")
    if len(_PLACEMENT_ROWS) != 72:
        raise Bg0003IdentityError(
            "expected 72 placements, found %d" % len(_PLACEMENT_ROWS))
    # Control 1: every Mob-Set number this scene's placements use is either
    # resolved or named as unresolved, and the two sets together are EXACTLY
    # this scene's used keys - a placement keyed by a number this table has
    # never heard of means the placement file and the crosswalk came from
    # different extractions.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if scene_sets != table_sets:
        raise Bg0003IdentityError(
            "placement Mob-Set numbers and this table's keys disagree: %r"
            % sorted(scene_sets ^ table_sets))
    if len(table_sets) != 51:
        raise Bg0003IdentityError(
            "expected 51 distinct Mob-Set numbers, found %d" % len(table_sets))
    if not no_set_number_is_shipped_as_identity():
        raise Bg0003IdentityError(
            "a row ships its own Mob-Set number as an identity")
    for row in _RESOLVED_ROWS:
        (template_id, cline_row_id, n_id, outfit, name, title, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1:
            raise Bg0003IdentityError(
                "set %d carries no CLINE row locator" % template_id)
        if ";" in outfit:
            raise Bg0003IdentityError(
                "set %d ships a multi-variant outfit string" % template_id)
        if not outfit or not outfit.isascii():
            raise Bg0003IdentityError(
                "set %d has an empty or non-ASCII outfit" % template_id)
        if not name.isascii() or not title.isascii():
            raise Bg0003IdentityError(
                "set %d has a non-ASCII name or title" % template_id)
        if not name:
            raise Bg0003IdentityError(
                "set %d has no display name" % template_id)
        if max_hp < 1 or level < 1:
            raise Bg0003IdentityError("set %d has a bad level/HP" % template_id)
    if len(shippable_placements()) != 62:
        raise Bg0003IdentityError("expected 62 shippable placements")
    if len(unshippable_placements()) != 10:
        raise Bg0003IdentityError("expected 10 unshippable placements")
    ids = [p.actor_identity for p in shippable_placements()]
    if len(ids) != len(set(ids)):
        raise Bg0003IdentityError("actor identities collide within this table")


_self_check()
