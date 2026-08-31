"""Who each Bg0008 placement actually IS - Silver Harbour's real cast.

LANE-A (WORLD).  ``COO-DECISION 2026-08-30T14:41+07:00`` (pf_bridge
``notes_to_chief/20260830_1441_COO-DECISION-scene4-slave-market-first-door.md``)
approved building the ten still-shut doors surveyed in round ``12lyda`` in
native-placement-count order ("no need to ask again per door").  Scenes 4, 5,
10, 14 and 6 are open; this is the sixth door in the sequence and the
next-highest native placement count among the six still shut (3, 7, 8, 9, 11,
130): scene 8 (Bg0008, "Silver Harbour", 76 placements).  This module is the
identity half, the same split every earlier crosswalk used;
``world_population_bg0008`` is the census half.

THE CROSSWALK, RE-DERIVED HERE RATHER THAN TAKEN FROM A CITATION.
``SCENE_NAME[s_MODLE_ID=Bg0008].n_CLINE_TYPE`` was read directly off the
bridge clone this round:

    SCENE_NAME[s_MODLE_ID=Bg0008].n_ID          = 8
    SCENE_NAME[s_MODLE_ID=Bg0008].n_CLINE_TYPE  = 8    (a real value, direct)
    SCENE_NAME[s_MODLE_ID=Bg0008].n_SCENE_LV    = 86
    CLINE[(8, <Mob-Set number>)].n_LEADER_BK1   = the real MOBS.n_ID
    MOBS[n_ID].s_OUTFIT                         = the avatar the client loads
    MOBS_TIP[n_ID].s_NAME / s_TITLE             = the label under the actor
    STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX      = max HP (the one derived col)

Same direct-selector shape ``world_bg0004_identity``, ``world_bg0005_identity``,
``world_bg0006_identity`` and ``world_bg0010_identity`` all ship (one of
RE-128's 19 direct CLINE types, not one of its 240 instance scenes).

WHAT IS ESTABLISHED HERE AND WHAT IS NOT, STATED THE SAME WAY THE OTHER FIVE
CROSSWALK MODULES STATE IT.

    ESTABLISHED - THE TABLE.  This scene's cast is drawn from CLINE type 8's
    leader column.  CONTROL 1 below is exact: this scene's placements use
    exactly 48 distinct Mob-Set numbers (1-42, 101-106) and every one of the
    48 has a row in CLINE type 8 - which is CLINE type 8's ENTIRE key range
    (48 rows total, counted directly rather than trusted from the registry's
    own ``native_definition_count`` of 49 - see the discrepancy note below),
    the same 'placement file touches every key its own CLINE type owns'
    shape scenes 5's and 6's own crosswalks carry (unlike bg0004's 61-of-62
    and bg0010's 40-of-41).

    NOT ESTABLISHED - THE PAIRING.  Which leader belongs to which Mob-Set
    number.  No human has stood in this scene (registry ``status:
    never_sent_to_any_client_by_this_project``), so every name below is a
    table inference, the bottom of the evidence order COO set on
    2026-08-28T21:30, until an attended round looks.

DISCREPANCY, MEASURED AND NOT SILENTLY RECONCILED.  The registry's own
``native_definition_count`` for scene 8 reads 49; this round's own count of
CLINE type 8's rows (grouped by ``n_CREATURE_TYPE``, checked for duplicates -
there are none) is 48, and 48 is also exactly the count of distinct Mob-Set
numbers this scene's own 76 placements use (CONTROL 1).  The two numbers
agreeing with each other and disagreeing with the registry's field is the
same shape as bg0004's 61-of-62 and bg0010's 40-of-41 differences: recorded
here rather than "fixed" in the registry, because this round did not
re-derive whatever the registry's own count measured and cannot say which of
the two is wrong without doing that separately.

CONTROL 1 - EXACT SUBSET, MEASURED.  The 76 placements resolve to 48 distinct
Mob-Set numbers; CLINE type 8 has exactly 48 keys (1-42, 101-106); the two
sets are identical (no gap either direction).

CONTROL 2 - NOT REBUILT HERE.  No ``world_bg0015_identity.
SCENE_LEVEL_CONTROL`` row exists for BG0008 (checked: that table only cites
scenes it was built against at the time, and this scene was never one of
them) - the same absence bg0006's own Control 2 recorded, not silently
skipped.

CONTROL 3 - NO SELF-MAPPING, WEAK, SAME CAVEAT AS THE OTHER FIVE SCENES.  0
of the 41 resolved rows have ``mobs_n_id == template_id`` (measured, not
assumed): none.  A shape check, not evidence.

SEVEN OF THE 48 SETS DO NOT RESOLVE (COST 7 PLACEMENTS), TWO FAMILIAR
FAILURE SHAPES, NO THIRD ONE THIS TIME.

* Sets [1, 106] -> leaders [249, 0].  CLINE type 8's own row for key 1 carries a
  real, non-zero ``n_LEADER_BK1`` (249) but ``CONSTDATA MOBS`` has no row for
  it; key 106's own row carries ``n_LEADER_BK1 = 0``, which resolves to no
  leader at all - the same "MOBS has no row" family bg0005's set 1 and
  bg0006's sets 1/114 needed, three occurrences of the shape across the
  project so far, two here.
* Sets [101, 102, 103, 104, 105] -> leaders [10043, 10044, 10045, 10046,
  10047].  Every one HAS a ``CONSTDATA MOBS`` row but its ``s_OUTFIT`` column
  is empty - the identical 'path-finding helper, not a creature' shape every
  sibling scene's own 101+ block carries (bg0004: 6, bg0005: 4, bg0006: 9,
  bg0010: 5; this scene: 5).
* NO CJK/non-cp874 name this scene needed - unlike bg0006's three teleporter
  drops, every one of this scene's 41 resolved ``MOBS_TIP`` rows is plain
  ASCII, checked directly (not assumed from the absence of a failure).

TEN SETS LIST TWO AVATAR TEMPLATES SEPARATED BY ';'.  Same rule and the same
open question as bg0004's nine, bg0005's ten, bg0006's ten and bg0010's
twelve: ship the FIRST variant, keep the whole string in
``MULTI_VARIANT_OUTFITS``, and ``_self_check`` refuses at import if a raw ';'
ever reaches the shipped column.  [LANE-A ASSUMPTION - AWAITING COO/OWNER
CONFIRMATION].  Leaders [270, 271, 272, 273, 275, 276, 278, 279, 282, 283]
(10 of the 41 resolved sets), placed unevenly: the ten multi-variant sets
together cover 36 of the 69 shippable placements (measured this round, not
estimated).

NO NAME-VS-TEMPLATE DISAGREEMENT, NO EXTRA SPAWN TRIPLE, NO MULTI-TEMPLATE
ROW, NO EXTRACTION-UNRESOLVED SENTINEL.  Checked directly against this
scene's own placement file: no row carries ``extra_triple_count > 0``, no row
lists more than one template id, and no row's ``template_ids`` column reads
the literal ``UNRESOLVED``.  Same clean shape bg0005's and bg0006's own
crosswalks carry on these axes.

NO CREW.  Measured for this scene: 0 of CLINE type 8's 48 rows carry any
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
this scene (n_id 8) records the marker point 8.8 units from the nearest of
this scene's 76 native placements, INSIDE the placement extents - unlike
scene 6's 772.0-unit gap, this is the tightest marker-to-placement distance
of any door this lane has opened so far.  Still 'recorded, not enforced' (a
.npc file is not terrain), but a fact worth naming rather than leaving
buried in the registry JSON: a future round that flips
``login_entry_allowed`` for scene 8 should read that block, and this scene's
own number is favourable rather than merely present.

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
    gamedata/scene/Bg0008/Bg0008.placements.tsv

THE JOIN, EXACTLY, SO IT CAN BE MECHANISED LATER (done by a throwaway script
against committed TSVs read directly this round, not by hand - the tables
are large enough that hand transcription would itself be an error source;
the script's own output is what appears below, unedited except for
formatting):

    keys   = {r.n_CREATURE_TYPE: r for r in CLINE if r.n_CLINE_TYPE == 8}
    for each Mob-Set number k this scene's placements use (48 of them):
        leader = keys[k].n_LEADER_BK1
        drop k if MOBS has no row for it, or that row's s_OUTFIT is empty,
            or MOBS_TIP.s_NAME/s_TITLE/s_OUTFIT is not cp874-representable
        else row = (k, keys[k].n_ID, leader, s_OUTFIT.split(';')[0],
                    MOBS_TIP.s_NAME or '', MOBS_TIP.s_TITLE or '',
                    MOBS.n_LEVEL_MIN, MOBS.n_RANK,
                    STANDARD_MOB[n_LEVEL_MIN].n_HPMAX, MOBS.n_MOB_USAGE)
    placements = every row of Bg0008.placements.tsv as
        (index, template_ids, running instance count per template_ids,
         x, y, z), in file order - no sentinel rows this scene (see above).

WHAT THIS MODULE DOES NOT CLAIM.

* Not that any of these 69 actors has been SEEN.  No human has been in this
  scene in this project's history (registry ``status:
  never_sent_to_any_client_by_this_project``, and ``login_entry_allowed`` is
  still ``false`` as of this module's own construction round).  The
  client-observable layer for this scene is empty until an attended round
  looks.
* Not that this census (built by ``world_population_bg0008``, a sibling
  module, not this one) is what raises these actors on a real server.
* Not leader+crew.  Like every sibling crosswalk this implements
  ``n_LEADER_BK1`` only.  Measured for this scene: 0 of CLINE type 8's 48
  rows carry any ``n_CREW`` value at all, so there is no pet/crew group this
  reading silently drops.
* Not wired at import time in this module - wiring
  (``CENSUS_SOURCES``/``ROSTER_COMPOSERS``/``lane_hooks`` console reader) and
  the door-open (``login_entry_allowed``) are both done by THIS SAME ROUND's
  other files, following the compressed build+wire+open precedent rounds
  ``l03cgh``/``fx0007`` set for scenes 5 and 6 (the generic contract test
  ``tests/test_lane_a_scene_census.py::ComposerContractTests`` already
  assumes every scene this lane composes for is also open at login).
"""
from __future__ import annotations

from dataclasses import dataclass


# Convention marker: shippable, no scenario flag - matching the five sibling
# crosswalk modules' own convention.
production_allowed = True
test_only = False

SCENE_N_ID = 8
SCENE_MODEL_ID = "Bg0008"
SCENE_CLINE_TYPE = 8
# SCENE_NAME.n_SCENE_LV for this scene.
SCENE_DECLARED_LEVEL = 86

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
    "gamedata/scene/Bg0008/Bg0008.placements.tsv":
        '7143642442abd810ccaed1f1692d82b99ee7729061c30429e54d01d1e42fdb86',
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  Costs 7 of the 76
# placements (see module docstring for the two distinct failure shapes).
UNRESOLVED = {
    1: (2400, 249, 'MOBS has no row for this leader'),
    101: (2442, 10043, 'MOBS row carries no s_OUTFIT avatar template'),
    102: (2443, 10044, 'MOBS row carries no s_OUTFIT avatar template'),
    103: (2444, 10045, 'MOBS row carries no s_OUTFIT avatar template'),
    104: (2445, 10046, 'MOBS row carries no s_OUTFIT avatar template'),
    105: (2446, 10047, 'MOBS row carries no s_OUTFIT avatar template'),
    106: (2447, 0, 'MOBS has no row for this leader'),
}

# MOBS rows in this scene that list SEVERAL avatar templates separated by
# ';', as leader n_ID -> the whole string.  The table below ships the FIRST
# variant; ``_self_check`` refuses if a ';' ever reaches the shipped column.
# [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION]
MULTI_VARIANT_OUTFITS = {
    270: 'M024_000_000_SP1;M024_000_000_SP2',
    271: 'M005_000_003_SP1;M005_000_003_SP2',
    272: 'M025_000_002_SP1;M025_000_002_SP2',
    273: 'M003_000_001_SP1;M003_000_001_SP2',
    275: 'M013_001_001_SP1;M013_001_001_SP2',
    276: 'M006_001_002_SP1;M006_001_002_SP2',
    278: 'M021_000_000_SP1;M021_000_000_SP2',
    279: 'M024_001_002_SP1;M024_001_002_SP2',
    282: 'M025_000_001_SP1;M025_000_001_SP2',
    283: 'M000_000_002_SP1;M000_000_002_SP2',
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
# 8 resolves to a shippable body (cp874-representable name/title/outfit).
_RESOLVED_ROWS = (
    (2, 2401, 250, 'M055_000_000_N', 'Columbus', 'Marine Transport Station', 87, 0, 132902, 2),
    (3, 2402, 251, 'M068_000_000_SP2', 'Chamber sailor', '', 87, 0, 132902, 2),
    (4, 2403, 252, 'M015_000_001_SP1', 'Mori Hiroko', 'Vagabond Messenger', 87, 0, 132902, 2),
    (5, 2404, 253, 'P_MALE_019_000_SEPHIROTH', 'Sai Feross', 'Bounty Hunter King', 87, 0, 132902, 2),
    (6, 2405, 254, 'P_FEMALE_018_000_LORA', 'Laura', 'Treasure Hunter', 87, 0, 132902, 2),
    (7, 2406, 255, 'P_MALE_003_002_N', 'Seasoned bounty hunter', '', 87, 0, 132902, 2),
    (8, 2407, 256, 'M019_002_000_SP1', 'Young sea monster hunter', '', 87, 0, 132902, 2),
    (9, 2408, 257, 'M009_000_000_N', 'Odyssey', 'Pride', 87, 0, 132902, 2),
    (10, 2409, 258, 'P_FEMALE_009_001_YSERA', 'Ysera', 'Beutyfull', 87, 0, 132902, 2),
    (11, 2410, 259, 'P_FEMALE_019_000_FIONA', 'Fiona', 'Beautiful Girl of Iceberg', 87, 0, 132902, 2),
    (12, 2411, 260, 'M001_003_000_SP2', 'Tony', 'Monster Hunter', 87, 0, 132902, 2),
    (13, 2412, 261, 'P_FEMALE_018_000_LORA', 'Laura', 'Lair Finder', 87, 0, 132902, 2),
    (14, 2413, 262, 'P_FEMALE_012_000_VENONIKA', 'Veronica', 'Witch Apprentice', 87, 0, 132902, 2),
    (15, 2414, 263, 'M010_000_000_SP1', 'Gugh', 'Monster Hunter', 87, 0, 132902, 2),
    (16, 2415, 264, 'P_MALE_014_000_MULLER', 'Moorer', 'Captain', 87, 0, 132902, 2),
    (17, 2416, 265, 'M015_000_000_SP2', 'Mo Yuzi', 'Naval Communications Bureau', 87, 0, 132902, 2),
    (18, 2417, 266, 'M076_000_000_N', 'Sea Phantom', 'Greedy', 87, 0, 132902, 2),
    (19, 2418, 267, 'P_FEMALE_003_002_N', 'Wounded bounty hunter', '', 87, 0, 132902, 2),
    (20, 2419, 268, 'M077_000_000_N', 'Angelina', 'Chasing Love Pirate Princess', 87, 0, 132902, 2),
    (21, 2420, 269, 'M068_000_002_N', 'Local fisherman', '', 87, 0, 132902, 2),
    (22, 2421, 270, 'M024_000_000_SP1', 'Penguin Corporal', '', 87, 1, 132902, 1),
    (23, 2422, 271, 'M005_000_003_SP1', 'Polar deer', '', 87, 1, 132902, 1),
    (24, 2423, 272, 'M025_000_002_SP1', 'Flash Snail', '', 87, 1, 132902, 1),
    (25, 2424, 273, 'M003_000_001_SP1', 'Polar ape', '', 87, 1, 132902, 1),
    (26, 2425, 274, 'M003_000_001_SP3', 'Polar head', '', 87, 1, 132902, 1),
    (27, 2426, 275, 'M013_001_001_SP1', 'Crystal Bibi', '', 87, 1, 132902, 1),
    (28, 2427, 276, 'M006_001_002_SP1', 'Iceberg Turtle', '', 87, 1, 132902, 1),
    (29, 2428, 277, 'M006_001_002_SP3', 'Polar Giant Turtle', '', 87, 1, 132902, 1),
    (30, 2429, 278, 'M021_000_000_SP1', 'Blue Sea Snake', '', 87, 1, 132902, 1),
    (31, 2430, 279, 'M024_001_002_SP1', 'Penguin Koro', '', 87, 1, 132902, 1),
    (32, 2431, 280, 'M010_000_000_SP1', 'Walrus general', '', 87, 1, 132902, 1),
    (33, 2432, 281, 'M010_000_000_SP3', 'Ice Carle Commander', '', 87, 1, 132902, 1),
    (34, 2433, 282, 'M025_000_001_SP1', 'Deep Sea Snail', '', 87, 1, 132902, 1),
    (35, 2434, 283, 'M000_000_002_SP1', 'Blind Hound', '', 87, 1, 132902, 1),
    (36, 2435, 720, 'MAP001_000_000', 'Mirage reel', '', 105, 0, 228055, 2),
    (37, 2436, 721, 'MAP001_000_000', 'Mirage reel', '', 105, 0, 228055, 2),
    (38, 2437, 722, 'BULLETIN_BOARD', 'Task Board', '', 105, 0, 228055, 2),
    (39, 2438, 544, 'M015_001_001_SP2', 'Jet cat thieves No.9', '', 87, 1, 132902, 1),
    (40, 2439, 527, 'M015_001_001_SP2', 'Jet cat thieves No.10', '', 87, 1, 132902, 1),
    (41, 2440, 528, 'P_MALE_003_002_REME', 'Remy', 'Bounty Hunter', 90, 1, 146413, 2),
    (42, 2441, 529, 'P_FEMALE_003_002_NENA', 'Nina', 'Bounty Hunter', 90, 1, 146413, 2),
)

IDENTITIES = {row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS}


@dataclass(frozen=True)
class Bg0008Placement:
    """One Bg0008 placement resolved to a real, named, bodied actor."""

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
    (0, 1, 1, 19440.59765625, 23997.322265625, 551.20849609375),
    (1, 2, 1, 21456.15234375, 22088.701171875, 587.1802978515625),
    (2, 3, 1, 19695.328125, 21958.072265625, 566.971923828125),
    (3, 4, 1, 18633.234375, 14118.9658203125, 2483.098876953125),
    (4, 5, 1, 17753.51171875, 12207.125, 2507.056640625),
    (5, 6, 1, 19510.365234375, 11408.763671875, 2523.2001953125),
    (6, 7, 1, 19690.8203125, 13632.763671875, 2530.050537109375),
    (7, 8, 1, 8510.8984375, 11684.0498046875, 2544.90185546875),
    (8, 9, 1, 3668.62939453125, 153.3907928466797, 1173.3199462890625),
    (9, 10, 1, 22086.38671875, -6699.76318359375, 981.2412719726562),
    (10, 11, 1, 18710.162109375, -14739.99609375, 524.6201171875),
    (11, 12, 1, 18907.1171875, -11758.9677734375, 479.7381896972656),
    (12, 13, 1, 23723.392578125, -17333.142578125, 469.8992919921875),
    (13, 14, 1, 10022.2900390625, -22131.220703125, 889.905517578125),
    (14, 15, 1, 4398.40869140625, -17378.1953125, 905.8773803710938),
    (15, 16, 1, -12038.1162109375, -18309.4140625, 2075.978515625),
    (16, 17, 1, -10409.970703125, -19968.02734375, 2026.426025390625),
    (17, 18, 1, -8894.2802734375, -4214.9794921875, 5620.31982421875),
    (18, 19, 1, -1688.830078125, -7669.970703125, 4692.0556640625),
    (19, 23, 1, 20191.478515625, -2191.19482421875, 1879.85791015625),
    (20, 27, 1, 13067.9072265625, -11557.5048828125, 2634.74072265625),
    (21, 26, 1, 21857.80859375, -16751.83984375, 572.4290161132812),
    (22, 27, 2, 14650.98828125, -20279.0234375, 884.1774291992188),
    (23, 29, 1, -11584.1142578125, -25424.4765625, 620.8662109375),
    (24, 30, 1, 34.468299865722656, -12920.2958984375, 1901.5548095703125),
    (25, 31, 1, -18210.40625, -18225.291015625, 2474.906982421875),
    (26, 32, 1, -8425.880859375, 1696.989013671875, 3849.341552734375),
    (27, 33, 1, -8827.2705078125, -5276.39599609375, 5660.751953125),
    (28, 24, 1, 6692.35302734375, 5229.802734375, 1946.8729248046875),
    (29, 24, 2, 4754.955078125, 2966.983154296875, 1551.977294921875),
    (30, 34, 1, -16002.2001953125, 5899.98095703125, 3837.584228515625),
    (31, 28, 1, 1757.5321044921875, -19079.33203125, 544.2794799804688),
    (32, 28, 2, -2859.40234375, -22475.88671875, 474.5541076660156),
    (33, 28, 3, -4715.259765625, -23919.7109375, 554.0147705078125),
    (34, 28, 4, -3742.887939453125, -25225.01953125, 687.2000122070312),
    (35, 28, 5, -9908.189453125, -25762.529296875, 642.3214721679688),
    (36, 35, 1, 1607.39306640625, 10736.9091796875, 2572.0556640625),
    (37, 23, 2, 20881.759765625, -5696.6064453125, 1160.212158203125),
    (38, 23, 3, 22230.876953125, -9586.5, 669.1160888671875),
    (39, 25, 1, 19450.46875, -12168.8681640625, 531.1129150390625),
    (40, 25, 2, 19715.587890625, -15617.7470703125, 562.90478515625),
    (41, 25, 3, 17858.96875, -16920.23828125, 492.30731201171875),
    (42, 27, 3, 9472.9189453125, -21927.515625, 951.4337768554688),
    (43, 27, 4, 5597.8916015625, -17903.884765625, 968.3228149414062),
    (44, 27, 5, 11606.810546875, -11773.2216796875, 2671.1142578125),
    (45, 30, 2, -4256.138671875, -14119.427734375, 2919.9990234375),
    (46, 30, 3, -10702.75, -18512.224609375, 2095.940673828125),
    (47, 31, 2, -15860.828125, -14958.1416015625, 3549.052490234375),
    (48, 31, 3, -13663.8330078125, -11208.548828125, 4242.4794921875),
    (49, 31, 4, -2340.703125, -5320.96923828125, 4720.24951171875),
    (50, 31, 5, -3329.4287109375, -2965.453125, 4391.5791015625),
    (51, 32, 2, -13039.6025390625, -2826.213623046875, 5144.4638671875),
    (52, 32, 3, -11621.6376953125, -4845.341796875, 5410.49755859375),
    (53, 34, 2, -14176.6572265625, 9340.7265625, 3177.29345703125),
    (54, 34, 3, -9216.681640625, 11078.193359375, 1812.4935302734375),
    (55, 35, 2, 3857.92578125, 11506.423828125, 2571.02734375),
    (56, 35, 3, -914.5753784179688, 10749.4736328125, 2578.2734375),
    (57, 35, 4, -3274.461669921875, 12289.0498046875, 2026.4437255859375),
    (58, 22, 1, 16772.705078125, 982.774169921875, 2119.40234375),
    (59, 22, 2, 11847.619140625, 4782.125, 2180.0712890625),
    (60, 22, 3, 9371.0048828125, 7765.31982421875, 2314.79931640625),
    (61, 20, 1, -9145.76171875, 14845.93359375, 762.2020874023438),
    (62, 21, 1, -6679.79345703125, 14050.0224609375, 857.7910766601562),
    (63, 36, 1, 16849.37890625, 12191.5703125, 2483.58203125),
    (64, 38, 1, 20758.9296875, 13817.8056640625, 2858.449462890625),
    (65, 37, 1, -9267.1455078125, -15971.9453125, 2698.59716796875),
    (66, 39, 1, 13263.310546875, -11137.9619140625, 2628.9375),
    (67, 40, 1, -10696.365234375, -26105.734375, 620.875),
    (68, 41, 1, 3773.245849609375, -2862.899658203125, 518.7052001953125),
    (69, 42, 1, -9298.9326171875, -2653.55224609375, 5668.18115234375),
    (70, 101, 1, 18944.9140625, 19211.146484375, 1978.3228759765625),
    (71, 102, 1, -7496.0390625, 1442.095703125, 3716.301025390625),
    (72, 103, 1, 14512.515625, -11092.6181640625, 2637.767578125),
    (73, 104, 1, -9438.6728515625, 14363.8681640625, 810.7307739257812),
    (74, 105, 1, 18465.130859375, 13345.1826171875, 2356.237060546875),
    (75, 106, 1, 9439.5966796875, -3760.4560546875, 3263.875),
)

PLACEMENT_COUNT = len(_PLACEMENT_ROWS)


class Bg0008IdentityError(ValueError):
    """A refusal from this module, always with a reason in the message."""


def identity_for(template_id: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    ``None`` is exactly the 7 sets in ``UNRESOLVED`` and nothing else: this
    function never substitutes, and never falls back to the Mob-Set number
    that ``GT-078`` proved wrong on the owner's screen.
    """
    if type(template_id) is not int or type(template_id) is bool:
        raise Bg0008IdentityError("template id must be an int")
    return IDENTITIES.get(template_id)


def shippable_placements() -> tuple[Bg0008Placement, ...]:
    """The 69 placements of the 76 that resolve to a real identity."""
    out = []
    for index, template_id, mm_instance, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(template_id)
        if identity is None:
            continue
        out.append(Bg0008Placement(
            index, template_id, mm_instance, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The 7 that are dropped, each with the id and the reason.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH ones and WHY.
    """
    out = []
    for index, template_id, _mm, x, y, z in _PLACEMENT_ROWS:
        if template_id in IDENTITIES:
            continue
        cline_row_id, leader, reason = UNRESOLVED.get(
            template_id, (0, 0, "set not in CLINE 8"))
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
        raise Bg0008IdentityError(
            "expected 41 resolved sets, found %d" % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg0008IdentityError("duplicate Mob-Set number in the table")
    if len(UNRESOLVED) != 7:
        raise Bg0008IdentityError(
            "expected 7 unresolved sets, found %d" % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg0008IdentityError("a set is both resolved and unresolved")
    if len(_PLACEMENT_ROWS) != 76:
        raise Bg0008IdentityError(
            "expected 76 placements, found %d" % len(_PLACEMENT_ROWS))
    # Control 1: every Mob-Set number this scene's placements use is either
    # resolved or named as unresolved, and the two sets together are EXACTLY
    # this scene's used keys - a placement keyed by a number this table has
    # never heard of means the placement file and the crosswalk came from
    # different extractions.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if scene_sets != table_sets:
        raise Bg0008IdentityError(
            "placement Mob-Set numbers and this table's keys disagree: %r"
            % sorted(scene_sets ^ table_sets))
    if len(table_sets) != 48:
        raise Bg0008IdentityError(
            "expected 48 distinct Mob-Set numbers, found %d" % len(table_sets))
    if not no_set_number_is_shipped_as_identity():
        raise Bg0008IdentityError(
            "a row ships its own Mob-Set number as an identity")
    for row in _RESOLVED_ROWS:
        (template_id, cline_row_id, n_id, outfit, name, title, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1:
            raise Bg0008IdentityError(
                "set %d carries no CLINE row locator" % template_id)
        if ";" in outfit:
            raise Bg0008IdentityError(
                "set %d ships a multi-variant outfit string" % template_id)
        if not outfit or not outfit.isascii():
            raise Bg0008IdentityError(
                "set %d has an empty or non-ASCII outfit" % template_id)
        if not name.isascii() or not title.isascii():
            raise Bg0008IdentityError(
                "set %d has a non-ASCII name or title" % template_id)
        if not name:
            raise Bg0008IdentityError(
                "set %d has no display name" % template_id)
        if max_hp < 1 or level < 1:
            raise Bg0008IdentityError("set %d has a bad level/HP" % template_id)
    if len(shippable_placements()) != 69:
        raise Bg0008IdentityError("expected 69 shippable placements")
    if len(unshippable_placements()) != 7:
        raise Bg0008IdentityError("expected 7 unshippable placements")
    ids = [p.actor_identity for p in shippable_placements()]
    if len(ids) != len(set(ids)):
        raise Bg0008IdentityError("actor identities collide within this table")


_self_check()
