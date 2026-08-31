"""Who each Bg0006 placement actually IS - Ocean Walled City's real cast.

LANE-A (WORLD).  ``COO-DECISION 2026-08-30T14:41+07:00`` (pf_bridge
``notes_to_chief/20260830_1441_COO-DECISION-scene4-slave-market-first-door.md``)
approved building the ten still-shut doors surveyed in round ``12lyda`` in
native-placement-count order ("no need to ask again per door").  Scenes 4, 5,
10 and 14 are open; this is the fifth door in the sequence and the next-highest
native placement count among the seven still shut (3, 6, 7, 8, 9, 11, 130):
scene 6 (Bg0006, "Ocean Walled City", 80 placements).  This module is the
identity half, the same split every earlier crosswalk used;
``world_population_bg0006`` is the census half.

THE CROSSWALK, RE-DERIVED HERE RATHER THAN TAKEN FROM A CITATION.
``SCENE_NAME[s_MODLE_ID=Bg0006].n_CLINE_TYPE`` was read directly off the
bridge clone this round:

    SCENE_NAME[s_MODLE_ID=Bg0006].n_ID          = 6
    SCENE_NAME[s_MODLE_ID=Bg0006].n_CLINE_TYPE  = 6    (a real value, direct)
    SCENE_NAME[s_MODLE_ID=Bg0006].n_SCENE_LV    = 70
    CLINE[(6, <Mob-Set number>)].n_LEADER_BK1   = the real MOBS.n_ID
    MOBS[n_ID].s_OUTFIT                         = the avatar the client loads
    MOBS_TIP[n_ID].s_NAME / s_TITLE             = the label under the actor
    STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX      = max HP (the one derived col)

Same direct-selector shape ``world_bg0004_identity``, ``world_bg0005_identity``,
``world_bg0010_identity`` and ``world_bg0015_identity`` all ship (one of
RE-128's 19 direct CLINE types, not one of its 240 instance scenes).

WHAT IS ESTABLISHED HERE AND WHAT IS NOT, STATED THE SAME WAY THE OTHER FOUR
CROSSWALK MODULES STATE IT.

    ESTABLISHED - THE TABLE.  This scene's cast is drawn from CLINE type 6's
    leader column.  CONTROL 1 below is exact: this scene's placements use
    exactly 52 distinct Mob-Set numbers (1-38, 101-114) and every one of the 52 has a
    row in CLINE type 6 - which is CLINE type 6's ENTIRE key range (52 rows
    total), the same 'placement file touches every key its own CLINE type
    owns' shape scene 5's own crosswalk carries (unlike bg0004's 61-of-62 and
    bg0010's 40-of-41).

    NOT ESTABLISHED - THE PAIRING.  Which leader belongs to which Mob-Set
    number.  No human has stood in this scene (registry ``status:
    never_sent_to_any_client_by_this_project``), so every name below is a
    table inference, the bottom of the evidence order COO set on
    2026-08-28T21:30, until an attended round looks.

CONTROL 1 - EXACT SUBSET, MEASURED.  The 80 placements resolve to 52 distinct
Mob-Set numbers; CLINE type 6 has exactly 52 keys (1-38, 101-114); the two
sets are identical (no gap either direction).

CONTROL 2 - NOT REBUILT HERE.  No ``world_bg0015_identity.
SCENE_LEVEL_CONTROL`` row exists for BG0006 (checked: that table only cites
scenes it was built against at the time, and this scene was never one of
them) - so, unlike bg0005's Control 2 gap, there is no earlier citation to
compare this round's own reading against.  Recorded as an absence rather than
silently skipped: a future round wiring a sixth door should not assume a
Control 2 citation exists just because bg0004's, bg0005's and bg0010's own
modules each carry one.

CONTROL 3 - NO SELF-MAPPING, WEAK, SAME CAVEAT AS THE OTHER FOUR SCENES.  0
of the 38 resolved rows have ``mobs_n_id == template_id`` (measured, not
assumed): none.  A shape check, not evidence.

14 OF THE 52 SETS DO NOT RESOLVE (COST 14 PLACEMENTS), THREE DIFFERENT REASONS -
ONE OF THEM NEW TO THIS PROJECT.

* Sets [1, 114] -> leaders [195, 943].  CLINE type 6's own row for these keys carries a
  real, non-zero ``n_LEADER_BK1``, but ``CONSTDATA MOBS`` has NO ROW at all
  for either leader - the same failure mode bg0005's set 1 needed (two
  occurrences here, not one).
* Sets [101, 102, 103, 104, 105, 106, 107, 108, 109] -> leaders [10024, 10025, 10026, 10027, 10028, 10029, 10030, 10031, 10032].  Every one HAS a
  ``CONSTDATA MOBS`` row but its ``s_OUTFIT`` column is empty - the identical
  'path-finding helper, not a creature' shape every sibling scene's own
  101+ block carries (bg0004: 6, bg0005: 4, bg0010: 5; this scene: 10, the
  most of any scene built so far).
* Sets [111, 112, 113] -> leaders [939, 940, 941].  NEW FAILURE MODE, NOT NEEDED BY ANY SIBLING
  SCENE SO FAR.  These three DO resolve to a real ``CONSTDATA MOBS`` row with
  a real ``s_OUTFIT``, but ``MOBS_TIP.s_NAME`` for all three reads
  ``\u6d77\u7687\u57ce\u5be8\u50b3\u9001\u54e1`` (CJK script - a teleporter NPC label at this scene's own
  gate, going by the outfit/model).  ``cp874`` (the bridge console's own
  codepage, Thai) cannot encode CJK, and CHARTER-02's rule is that nothing
  under ``src/`` may carry a character cp874 cannot map - so these three are
  DROPPED rather than shipped with a mis-decoded or truncated name, the same
  fail-closed choice this project makes for an empty ``s_OUTFIT``.  Not a
  guess at a transliteration either: no invented ASCII name is substituted.
  Opened to lane C for a from-source re-check (does a non-CJK label exist in
  a sibling text table this round did not read); see handback letter.

TEN SETS LIST TWO AVATAR TEMPLATES SEPARATED BY ';'.  Same rule and the same
open question as bg0004's nine, bg0005's ten, bg0010's twelve and bg0015's
nine: ship the FIRST variant, keep the whole string in
``MULTI_VARIANT_OUTFITS``, and ``_self_check`` refuses at import if a raw ';'
ever reaches the shipped column.  [LANE-A ASSUMPTION - AWAITING COO/OWNER
CONFIRMATION].  Leaders [219, 220, 221, 223, 224, 225, 227, 228, 229, 7045] (10 of the 38 resolved sets), placed unevenly:
the ten multi-variant sets together cover 36 of the 66 shippable placements
(measured this round, not estimated).

NO NAME-VS-TEMPLATE DISAGREEMENT, NO EXTRA SPAWN TRIPLE, NO MULTI-TEMPLATE
ROW, NO EXTRACTION-UNRESOLVED SENTINEL.  Checked directly against this
scene's own placement file: no name-vs-template disagreement anywhere in the 80 rows, no row carries ``extra_triple_count > 0``, no row lists more than one
template id, and no row's ``template_ids`` column reads the literal
``UNRESOLVED``.  Same clean shape bg0005's own crosswalk carries on these
four axes.

HEADING.  Same measurement every sibling scene's own ``_entry`` made for its
own scene: the extra f32 triple this TSV format carries (columns
``f32_3``/``f32_4``/``f32_5``) is a round-number range across unrelated rows
here too (11 distinct combinations, all multiples of 100) - the shape of a
radius, not a rotation - so the census half reuses ``world_population.
HEADINGS`` on the placement index, same as every other scene.

LANDING GEOMETRY.  ``scenarios/world_scene_registry_001.json``'s own
``table_row_differences.marker_geometry_measured_not_enforced`` block for
this scene (n_id 6) records the marker point 772.0 units from the nearest of
this scene's 80 native placements, outside the placement extents - the same
'recorded, not enforced' shape most of the ten doors carry (NOT the elevated
``the_two_interiors`` flag scene 10 alone carries).  This module does not
touch that finding or the registry row - it is recorded here because a
future round that flips ``login_entry_allowed`` for scene 6 must read that
block first, the same ordering principle the sibling modules use.

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
    gamedata/scene/bg0006/bg0006.placements.tsv

THE JOIN, EXACTLY, SO IT CAN BE MECHANISED LATER (done by a throwaway script
against committed TSVs read directly this round, not by hand - the tables
are large enough that hand transcription would itself be an error source;
the script's own output is what appears below, unedited except for
formatting):

    keys   = {r.n_CREATURE_TYPE: r for r in CLINE if r.n_CLINE_TYPE == 6}
    for each Mob-Set number k this scene's placements use (52 of them):
        leader = keys[k].n_LEADER_BK1
        drop k if MOBS has no row for it, or that row's s_OUTFIT is empty,
            or MOBS_TIP.s_NAME/s_TITLE/s_OUTFIT is not cp874-representable
        else row = (k, keys[k].n_ID, leader, s_OUTFIT.split(';')[0],
                    MOBS_TIP.s_NAME or '', MOBS_TIP.s_TITLE or '',
                    MOBS.n_LEVEL_MIN, MOBS.n_RANK,
                    STANDARD_MOB[n_LEVEL_MIN].n_HPMAX, MOBS.n_MOB_USAGE)
    placements = every row of bg0006.placements.tsv as
        (index, template_ids, running instance count per template_ids,
         x, y, z), in file order - no sentinel rows this scene (see above).

WHAT THIS MODULE DOES NOT CLAIM.

* Not that any of these 66 actors has been SEEN.  No human has been in this
  scene in this project's history (registry ``status:
  never_sent_to_any_client_by_this_project``, and ``login_entry_allowed`` is
  still ``false`` as of this module's own construction round).  The
  client-observable layer for this scene is empty until an attended round
  looks.
* Not that this census (built by ``world_population_bg0006``, a sibling
  module, not this one) is what raises these actors on a real server.
* Not leader+crew.  Like every sibling crosswalk this implements
  ``n_LEADER_BK1`` only.  Measured for this scene: 0 of CLINE type 6's 52
  rows carry any ``n_CREW`` value at all, so there is no pet/crew group this
  reading silently drops.
* Not wired at import time in this module - wiring
  (``CENSUS_SOURCES``/``ROSTER_COMPOSERS``/``lane_hooks`` console reader) and
  the door-open (``login_entry_allowed``) are both done by THIS SAME ROUND's
  other files, following the compressed build+wire+open precedent round
  ``l03cgh`` set for scene 5 (the generic contract test
  ``tests/test_lane_a_scene_census.py::ComposerContractTests`` already
  assumes every scene this lane composes for is also open at login).
"""
from __future__ import annotations

from dataclasses import dataclass


# Convention marker: shippable, no scenario flag - matching the four sibling
# crosswalk modules' own convention.
production_allowed = True
test_only = False

SCENE_N_ID = 6
SCENE_MODEL_ID = "Bg0006"
SCENE_CLINE_TYPE = 6
# SCENE_NAME.n_SCENE_LV for this scene.
SCENE_DECLARED_LEVEL = 70

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
    "gamedata/scene/bg0006/bg0006.placements.tsv":
        '4493f6e0596a869fa333ef970b7c6963d1861d4ca88490c6179635c3b23563ce',
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  Costs 14 of the 80
# placements (see module docstring for the three distinct failure shapes).
UNRESOLVED = {
    1: (2000, 195, 'MOBS has no row for this leader'),
    101: (2038, 10024, 'MOBS row carries no s_OUTFIT avatar template'),
    102: (2039, 10025, 'MOBS row carries no s_OUTFIT avatar template'),
    103: (2040, 10026, 'MOBS row carries no s_OUTFIT avatar template'),
    104: (2041, 10027, 'MOBS row carries no s_OUTFIT avatar template'),
    105: (2042, 10028, 'MOBS row carries no s_OUTFIT avatar template'),
    106: (2043, 10029, 'MOBS row carries no s_OUTFIT avatar template'),
    107: (2044, 10030, 'MOBS row carries no s_OUTFIT avatar template'),
    108: (2045, 10031, 'MOBS row carries no s_OUTFIT avatar template'),
    109: (2046, 10032, 'MOBS row carries no s_OUTFIT avatar template'),
    111: (2048, 939, 'MOBS_TIP name/title is non-ASCII, cp874 cannot ship it'),
    112: (2049, 940, 'MOBS_TIP name/title is non-ASCII, cp874 cannot ship it'),
    113: (2050, 941, 'MOBS_TIP name/title is non-ASCII, cp874 cannot ship it'),
    114: (2051, 943, 'MOBS has no row for this leader'),
}

# MOBS rows in this scene that list SEVERAL avatar templates separated by
# ';', as leader n_ID -> the whole string.  The table below ships the FIRST
# variant; ``_self_check`` refuses if a ';' ever reaches the shipped column.
# [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION]
MULTI_VARIANT_OUTFITS = {
    219: 'M001_003_001_N;M001_003_001_SP1',
    220: 'M022_000_003_SP1;M022_000_003_SP2',
    221: 'M001_001_000_N;M001_001_000_SP1',
    223: 'M017_000_003_SP1;M017_000_003_SP2',
    224: 'M004_000_004_SP1;M004_000_004_SP2',
    225: 'M002_000_001_SP1;M002_000_001_SP2',
    227: 'M025_000_000_SP1;M025_000_000_SP2',
    228: 'M021_001_000_SP1;M021_001_000_SP2',
    229: 'M015_000_002_SP1;M015_000_002_SP2',
    7045: 'M024_001_001_SP1;M024_001_001_SP2',
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
# 38 rows: every Mob-Set number this scene's placements use that CLINE type
# 6 resolves to a shippable body (cp874-representable name/title/outfit).
_RESOLVED_ROWS = (
    (2, 2001, 196, 'M055_000_000_N', 'Columbus', 'Marine Transport Station', 80, 0, 104603, 2),
    (3, 2002, 197, 'M001_000_000_SP2', 'Pirate port', '', 80, 0, 104603, 2),
    (4, 2003, 198, 'M009_000_000_N', 'Odyssey', 'Consideration', 80, 0, 104603, 2),
    (5, 2004, 199, 'M068_000_001_SP1', 'Sailor pirate ship', '', 80, 0, 104603, 2),
    (6, 2005, 200, 'M015_000_003_SP3', 'Sea Devil', 'Pirate Radio Station', 80, 0, 104603, 2),
    (7, 2006, 201, 'M073_000_000_SP3', 'Nicholas', 'Miner Foreman', 80, 0, 104603, 2),
    (8, 2007, 202, 'M001_000_001_SP3', 'Underground palace guard', '', 80, 0, 104603, 2),
    (9, 2008, 203, 'M010_000_001_SP3', 'Rob', 'Poseidon Loyalty Soldier', 80, 0, 104603, 2),
    (10, 2009, 204, 'M053_000_000_N', 'Jason', 'Pirate King', 80, 0, 104603, 2),
    (11, 2010, 205, 'P_MALE_012_000_ROBERS', 'Robert', 'Baron The Pirate', 80, 0, 104603, 2),
    (12, 2011, 206, 'M001_000_001_SP3', 'Eavesdrop Pirates', '', 80, 0, 104603, 2),
    (13, 2012, 207, 'M001_000_001_SP1', 'Pirates informer', '', 75, 0, 87072, 4),
    (14, 2013, 208, 'M009_000_000_N', 'Odyssey', 'Navy Stalker', 80, 0, 104603, 2),
    (15, 2014, 209, 'M017_000_003_BOSS', 'Urouge', 'Chief Dragon Warrior', 80, 0, 104603, 2),
    (16, 2015, 210, 'P_FEMALE_017_000_MORGEN', 'morgan', 'Pirate Knight', 80, 0, 104603, 2),
    (17, 2016, 211, 'P_FEMALE_007_002_GISEL', 'Giselle', 'Cage feed', 80, 0, 104603, 2),
    (18, 2017, 212, 'P_FEMALE_003_000_N', 'Underground palace  Female guard', '', 80, 0, 104603, 2),
    (19, 2018, 213, 'M030_000_000_N', 'Medea', 'The Siren', 80, 0, 104603, 2),
    (20, 2019, 214, 'M051_000_001_N', 'Angelina', 'Cute Slave', 80, 0, 104603, 2),
    (21, 2020, 215, 'M009_000_000_N', 'Odyssey', 'Wrath Witch', 80, 0, 104603, 2),
    (22, 2021, 216, 'M051_000_001_N', 'Angelina', 'Rescued Princess', 80, 0, 104603, 2),
    (23, 2022, 217, 'P_FEMALE_012_000_VENONIKA', 'Veronica', 'Witch Apprentice', 80, 0, 104603, 2),
    (24, 2023, 218, 'P_MALE_015_000_SLAVE', 'Tired Worker', '', 80, 0, 104603, 2),
    (25, 2024, 219, 'M001_003_001_N', 'Golden Axe pirates', '', 71, 1, 74566, 1),
    (26, 2025, 220, 'M022_000_003_SP1', 'Bat Banshee', '', 72, 1, 77577, 1),
    (27, 2026, 221, 'M001_001_000_N', 'Red Horn Pirates Group', '', 73, 1, 80671, 1),
    (28, 2027, 222, 'M001_001_000_SP3', 'Crull Two Horns', '', 73, 1, 80671, 1),
    (29, 2028, 223, 'M017_000_003_SP1', 'Sea Dragon Warrior', '', 74, 1, 83844, 1),
    (30, 2029, 224, 'M004_000_004_SP1', 'Charm Felvine', '', 75, 1, 87072, 1),
    (31, 2030, 225, 'M002_000_001_SP1', 'Purple Flame Lion', '', 76, 1, 90417, 1),
    (32, 2031, 226, 'M002_000_001_SP3', 'Anger Lion', '', 77, 1, 93814, 1),
    (33, 2032, 227, 'M025_000_000_SP1', 'Snail', '', 77, 1, 93814, 1),
    (34, 2033, 228, 'M021_001_000_SP1', 'Phantom Demon Snake', '', 78, 1, 97367, 1),
    (35, 2034, 229, 'M015_000_002_SP1', 'Jade magician', '', 79, 1, 100907, 1),
    (36, 2035, 245, 'MAP001_000_000', 'Mirage reel', '', 105, 0, 228055, 2),
    (37, 2036, 753, 'P_FEMALE_007_002_GISEL', 'Giselle', 'Sea Princess Successor', 87, 0, 132902, 2),
    (38, 2037, 826, 'M009_000_000_N', 'Odyssey', 'Wrath Witch', 105, 0, 228055, 2),
    (110, 2047, 7045, 'M024_001_001_SP1', 'Penguin Searcher', 'Serious and responsible', 99, 0, 192488, 2),
)

IDENTITIES = {row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS}


@dataclass(frozen=True)
class Bg0006Placement:
    """One Bg0006 placement resolved to a real, named, bodied actor."""

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
    (0, 1, 1, -9363.6103515625, 23549.841796875, 374.3804016113281),
    (1, 2, 1, -6914.181640625, 22385.59375, 373.505615234375),
    (2, 3, 1, -4255.13525390625, 21188.26953125, 371.1995849609375),
    (3, 5, 1, -9908.9697265625, 14043.5849609375, 348.2760925292969),
    (4, 4, 1, -9342.0224609375, 7780.0615234375, 371.58099365234375),
    (5, 6, 1, -4288.51220703125, 22458.703125, 338.5544128417969),
    (6, 7, 1, -795.6318969726562, 8869.80078125, 376.0531921386719),
    (7, 8, 1, -19162.71875, -2852.893798828125, 2335.9150390625),
    (8, 9, 1, -16216.8583984375, -6491.6240234375, 2520.87841796875),
    (9, 10, 1, -15643.9609375, -6718.57421875, 2520.11767578125),
    (10, 11, 1, -15175.939453125, -6241.2880859375, 2502.69091796875),
    (11, 12, 1, 2299.45947265625, -24849.115234375, 5836.64990234375),
    (12, 13, 1, -13311.357421875, -12392.0966796875, 1817.6962890625),
    (13, 14, 1, 415.69140625, -24489.314453125, 5615.69140625),
    (14, 15, 1, 4826.97021484375, -15079.6630859375, 8678.3828125),
    (15, 16, 1, 11596.7109375, -2174.660400390625, 4964.3212890625),
    (16, 17, 1, 1280.020751953125, -2251.399658203125, 4521.76611328125),
    (17, 18, 1, 15198.8447265625, 13755.93359375, 2560.34765625),
    (18, 19, 1, 13377.095703125, 12427.0712890625, 3056.665283203125),
    (19, 20, 1, 12781.6630859375, 13201.572265625, 2845.5390625),
    (20, 22, 1, 1183.598876953125, 11385.0712890625, 1470.2904052734375),
    (21, 21, 1, 855.7470703125, 12542.171875, 1453.5076904296875),
    (22, 23, 1, 12732.4638671875, 15931.724609375, 2021.912109375),
    (23, 24, 1, -14503.541015625, 16570.533203125, 300.9919128417969),
    (24, 25, 1, -2736.477294921875, 10485.7587890625, 473.412109375),
    (25, 25, 2, -6057.4111328125, 5662.93505859375, 371.5810852050781),
    (26, 25, 3, -7341.6328125, 11830.5986328125, 348.2358093261719),
    (27, 25, 4, -9748.8203125, 14860.0791015625, 342.13189697265625),
    (28, 26, 1, -14413.173828125, 5469.49560546875, 372.906005859375),
    (29, 26, 2, -17958.97265625, 7619.3115234375, 371.5820007324219),
    (30, 26, 3, -14676.052734375, 13090.462890625, 348.2392883300781),
    (31, 26, 4, -15384.228515625, 17661.634765625, 826.3505859375),
    (32, 27, 1, -13303.4501953125, 2088.64501953125, 891.0037231445312),
    (33, 27, 2, -17496.96875, 789.4520263671875, 1661.7125244140625),
    (34, 27, 3, -19263.482421875, -1438.26708984375, 2142.05859375),
    (35, 27, 4, -18926.255859375, -5084.21826171875, 2261.5185546875),
    (36, 27, 5, -15432.166015625, -8883.8408203125, 2261.519287109375),
    (37, 27, 6, -12807.1162109375, -10894.93359375, 1792.431640625),
    (38, 28, 1, -10661.697265625, -7704.74609375, 1686.622314453125),
    (39, 36, 1, -4537.306640625, 22912.416015625, 327.7651062011719),
    (40, 8, 2, -20128.26171875, -3547.2041015625, 2315.06787109375),
    (41, 18, 2, 15838.2119140625, 12727.6396484375, 2561.15625),
    (42, 37, 1, 1778.588623046875, -1779.033935546875, 4542.53515625),
    (43, 29, 1, -11876.7890625, -14847.0703125, 2334.201171875),
    (44, 29, 2, -225.22720336914062, -24093.767578125, 5490.31005859375),
    (45, 29, 3, 2039.2467041015625, -24345.818359375, 5814.9677734375),
    (46, 29, 4, 4181.33251953125, -21038.947265625, 7041.47216796875),
    (47, 29, 5, 3330.3955078125, -19036.978515625, 7655.4521484375),
    (48, 30, 1, 6268.5341796875, -12649.046875, 8616.66796875),
    (49, 30, 2, 6641.72998046875, -9394.072265625, 7671.12548828125),
    (50, 30, 3, 10324.4306640625, -9152.4580078125, 7492.2587890625),
    (51, 31, 1, 4287.5947265625, -2556.848876953125, 4521.6796875),
    (52, 32, 1, 2029.6630859375, -5314.63037109375, 4524.6962890625),
    (53, 33, 1, 8278.6982421875, -1727.6163330078125, 4525.71484375),
    (54, 34, 1, 10828.634765625, -6134.79296875, 7149.30859375),
    (55, 34, 2, 14553.669921875, -2824.295166015625, 6348.6455078125),
    (56, 34, 3, 12383.958984375, -1946.891845703125, 4940.39453125),
    (57, 34, 4, 14413.181640625, -811.1937866210938, 4764.2109375),
    (58, 35, 1, 14483.18359375, 4853.1328125, 2650.517578125),
    (59, 35, 2, 13377.8857421875, 8638.244140625, 2555.162109375),
    (60, 35, 3, 15214.5791015625, 9066.9716796875, 2555.162109375),
    (61, 35, 4, 16491.375, 11369.501953125, 2555.162109375),
    (62, 35, 5, 15219.5029296875, 14247.142578125, 2555.162109375),
    (63, 35, 6, 12870.185546875, 16599.541015625, 1964.5498046875),
    (64, 35, 7, 7300.11962890625, 15766.6513671875, 2056.51513671875),
    (65, 38, 1, 892.2647705078125, 11787.2626953125, 1453.5074462890625),
    (66, 101, 1, -9513.1259765625, 10421.8330078125, 292.38720703125),
    (67, 102, 1, -539.2822265625, 9678.6826171875, 321.4837951660156),
    (68, 103, 1, -9362.9228515625, 15007.1484375, 297.8450012207031),
    (69, 104, 1, -10321.3330078125, 15412.7412109375, 297.8442077636719),
    (70, 105, 1, -15644.494140625, -12271.869140625, 1639.9981689453125),
    (71, 106, 1, 5384.75927734375, -11893.255859375, 8610.9404296875),
    (72, 107, 1, 9162.14453125, -255.789794921875, 4536.9130859375),
    (73, 108, 1, 11609.8095703125, 12668.6494140625, 2988.691650390625),
    (74, 109, 1, -872.013671875, 14057.2822265625, 982.0811157226562),
    (75, 110, 1, 17327.083984375, 13169.62109375, 2686.56689453125),
    (76, 111, 1, -14294.9521484375, -6423.45068359375, 2489.3642578125),
    (77, 112, 1, -8972.720703125, 13907.900390625, 304.898193359375),
    (78, 113, 1, 10024.14453125, -6835.64599609375, 7149.30810546875),
    (79, 114, 1, -10691.8740234375, 15491.515625, 348.2760925292969),
)

PLACEMENT_COUNT = len(_PLACEMENT_ROWS)


class Bg0006IdentityError(ValueError):
    """A refusal from this module, always with a reason in the message."""


def identity_for(template_id: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    ``None`` is exactly the 14 sets in ``UNRESOLVED`` and nothing else: this
    function never substitutes, and never falls back to the Mob-Set number
    that ``GT-078`` proved wrong on the owner's screen.
    """
    if type(template_id) is not int or type(template_id) is bool:
        raise Bg0006IdentityError("template id must be an int")
    return IDENTITIES.get(template_id)


def shippable_placements() -> tuple[Bg0006Placement, ...]:
    """The 66 placements of the 80 that resolve to a real identity."""
    out = []
    for index, template_id, mm_instance, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(template_id)
        if identity is None:
            continue
        out.append(Bg0006Placement(
            index, template_id, mm_instance, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The 14 that are dropped, each with the id and the reason.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH ones and WHY.
    """
    out = []
    for index, template_id, _mm, x, y, z in _PLACEMENT_ROWS:
        if template_id in IDENTITIES:
            continue
        cline_row_id, leader, reason = UNRESOLVED.get(
            template_id, (0, 0, "set not in CLINE 6"))
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
    if len(_RESOLVED_ROWS) != 38:
        raise Bg0006IdentityError(
            "expected 38 resolved sets, found %d" % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg0006IdentityError("duplicate Mob-Set number in the table")
    if len(UNRESOLVED) != 14:
        raise Bg0006IdentityError(
            "expected 14 unresolved sets, found %d" % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg0006IdentityError("a set is both resolved and unresolved")
    if len(_PLACEMENT_ROWS) != 80:
        raise Bg0006IdentityError(
            "expected 80 placements, found %d" % len(_PLACEMENT_ROWS))
    # Control 1: every Mob-Set number this scene's placements use is either
    # resolved or named as unresolved, and the two sets together are EXACTLY
    # this scene's used keys - a placement keyed by a number this table has
    # never heard of means the placement file and the crosswalk came from
    # different extractions.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if scene_sets != table_sets:
        raise Bg0006IdentityError(
            "placement Mob-Set numbers and this table's keys disagree: %r"
            % sorted(scene_sets ^ table_sets))
    if len(table_sets) != 52:
        raise Bg0006IdentityError(
            "expected 52 distinct Mob-Set numbers, found %d" % len(table_sets))
    if not no_set_number_is_shipped_as_identity():
        raise Bg0006IdentityError(
            "a row ships its own Mob-Set number as an identity")
    for row in _RESOLVED_ROWS:
        (template_id, cline_row_id, n_id, outfit, name, title, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1:
            raise Bg0006IdentityError(
                "set %d carries no CLINE row locator" % template_id)
        if ";" in outfit:
            raise Bg0006IdentityError(
                "set %d ships a multi-variant outfit string" % template_id)
        if not outfit or not outfit.isascii():
            raise Bg0006IdentityError(
                "set %d has an empty or non-ASCII outfit" % template_id)
        if not name.isascii() or not title.isascii():
            raise Bg0006IdentityError(
                "set %d has a non-ASCII name or title" % template_id)
        if not name:
            raise Bg0006IdentityError(
                "set %d has no display name" % template_id)
        if max_hp < 1 or level < 1:
            raise Bg0006IdentityError("set %d has a bad level/HP" % template_id)
    if len(shippable_placements()) != 66:
        raise Bg0006IdentityError("expected 66 shippable placements")
    if len(unshippable_placements()) != 14:
        raise Bg0006IdentityError("expected 14 unshippable placements")
    ids = [p.actor_identity for p in shippable_placements()]
    if len(ids) != len(set(ids)):
        raise Bg0006IdentityError("actor identities collide within this table")


_self_check()
