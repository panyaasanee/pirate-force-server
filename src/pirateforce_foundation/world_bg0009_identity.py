"""Who each Bg0009 placement actually IS - Death City Sea's real cast.

LANE-A (WORLD).  ``COO-DECISION 2026-08-30T14:41+07:00`` (pf_bridge
``notes_to_chief/20260830_1441_COO-DECISION-scene4-slave-market-first-door.md``)
approved building the ten still-shut doors surveyed in round ``12lyda`` in
native-placement-count order ("no need to ask again per door").  Scenes 4, 5,
10, 14, 6, 8, 3 and 7 are open; this is the eighth door in the sequence and
the highest native placement count among the two still shut (11, 130): scene
9 (Bg0009, "Death City Sea", 63 placements).  This module is the identity
half, the same split every earlier crosswalk used; ``world_population_bg0009``
is the census half.

THE CROSSWALK, RE-DERIVED HERE RATHER THAN TAKEN FROM A CITATION.
``SCENE_NAME[s_MODLE_ID=Bg0009].n_CLINE_TYPE`` was read directly off the
bridge clone this round:

    SCENE_NAME[s_MODLE_ID=Bg0009].n_ID          = 9
    SCENE_NAME[s_MODLE_ID=Bg0009].n_CLINE_TYPE  = 9    (a real value, direct)
    SCENE_NAME[s_MODLE_ID=Bg0009].n_SCENE_LV    = 92
    CLINE[(9, <Mob-Set number>)].n_LEADER_BK1   = the real MOBS.n_ID
    MOBS[n_ID].s_OUTFIT                         = the avatar the client loads
    MOBS_TIP[n_ID].s_NAME / s_TITLE             = the label under the actor
    STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX      = max HP (the one derived col)

Same direct-selector shape ``world_bg0003_identity``, ``world_bg0004_identity``,
``world_bg0005_identity``, ``world_bg0006_identity``, ``world_bg0007_identity``,
``world_bg0008_identity`` and ``world_bg0010_identity`` all ship (one of
RE-128's 19 direct CLINE types, not one of its 240 instance scenes).

WHAT IS ESTABLISHED HERE AND WHAT IS NOT, STATED THE SAME WAY THE OTHER EIGHT
CROSSWALK MODULES STATE IT.

    ESTABLISHED - THE TABLE.  This scene's cast is drawn from CLINE type 9's
    leader column.  CONTROL 1 below is a SUBSET, not an exact match: this
    scene's placements use exactly 44 distinct Mob-Set numbers (1-37, 41, 44,
    101-105), all 44 of them present in CLINE type 9's own 48-row key range
    (1-41, 44, 101-106) - the same 'placement file touches only PART of its
    own CLINE type' shape bg0004's 55-of-61 and bg0010's 40-of-41 crosswalks
    carry (unlike scenes 5's, 6's, 7's and 8's own EXACT-match crosswalks).
    FOUR keys exist in CLINE type 9 that no placement in this scene uses
    (38, 39, 40, 106) - and UNLIKE bg0004's six untouched keys (all leader 0,
    "no creature"), THREE of these four (38, 39, 40) carry a real, non-zero
    ``n_LEADER_BK1`` (566, 567, 568) that simply has no placement pointing at
    it; only key 106 carries leader 0.  Measured, not assumed, and named
    because "unused CLINE keys always mean no creature" would have been false
    of this scene.

    NOT ESTABLISHED - THE PAIRING.  Which leader belongs to which Mob-Set
    number.  No human has stood in this scene (registry ``status:
    never_sent_to_any_client_by_this_project``), so every name below is a
    table inference, the bottom of the evidence order COO set on
    2026-08-28T21:30, until an attended round looks.

DISCREPANCY, MEASURED AND NOT SILENTLY RECONCILED - AND THE FIRST TIME IN
THIS LANE'S OWN HISTORY THE TWO NUMBERS DO NOT DISAGREE.  The registry's own
``native_definition_count`` for scene 9 reads 44.  This round's own count of
CLINE type 9's rows (grouped by ``n_CREATURE_TYPE``, checked for duplicates -
there are none) is 48, WIDER than 44 by the four untouched keys named above.
But 44 is also EXACTLY the count of distinct Mob-Set numbers this scene's own
63 placements use (CONTROL 1) - so, unlike bg0003's 52-of-51, bg0004's
56-vs-55-used/61-total, bg0007's 57-of-56 and bg0008's 49-of-48 (all of which
disagreed with THIS round's own re-derivation by exactly one), scene 9's
registry field and this round's own placement-side count AGREE.  What they
still do not agree with is CLINE type 9's own total row count (48), which
this round did not expect them to: nothing said ``native_definition_count``
counts CLINE rows rather than used Mob-Set numbers, and this is recorded as a
fact about this one field rather than a rule inferred from a single scene
where it happened to match.

CONTROL 1 - EXACT SUBSET, MEASURED.  The 63 placements resolve to 44 distinct
Mob-Set numbers; CLINE type 9 has 48 keys (1-41, 44, 101-106); the 44 the
scene uses are exactly {1-37} union {41, 44} union {101-105} - every one
present, none missing - and the four keys the scene never touches (38, 39,
40, 106) are NOT all "no creature" (see the discrepancy paragraph above).

CONTROL 2 - NOT REBUILT HERE.  No ``world_bg0015_identity.
SCENE_LEVEL_CONTROL`` row exists for BG0009 (checked: that table only cites
scenes it was built against at the time, and this scene was never one of
them) - the same absence bg0003's, bg0006's and bg0008's own Control 2
recorded, not silently skipped.

CONTROL 3 - NO SELF-MAPPING, WEAK, SAME CAVEAT AS THE OTHER EIGHT SCENES.  0
of the 38 resolved rows have ``mobs_n_id == template_id`` (measured, not
assumed): none.  A shape check, not evidence.

SIX OF THE 44 SETS DO NOT RESOLVE (COST 6 PLACEMENTS), THE SAME TWO FAMILIAR
FAILURE SHAPES AS EVERY SIBLING, NO THIRD ONE THIS TIME.

* Set [1] -> leader [284].  CLINE type 9's own row for key 1 carries a real,
  non-zero ``n_LEADER_BK1`` (284) but ``CONSTDATA MOBS`` has no row for it -
  the same "MOBS has no row" family bg0003's set 2, bg0005's set 1, bg0006's
  sets 1/114, bg0007's sets 1/111 and bg0008's sets 1/106 needed, eight
  occurrences of the shape across the project so far (1+1+2+2+2), one more
  here.
* Sets [101, 102, 103, 104, 105] -> leaders [10048, 10049, 10050, 10051,
  10052].  Every one HAS a ``CONSTDATA MOBS`` row but its ``s_OUTFIT``
  column is empty - the identical 'path-finding helper, not a creature'
  shape every sibling scene's own 101+ block carries (bg0003: 9, bg0004: 6,
  bg0005: 4, bg0006: 9, bg0007: 10, bg0008: 5, bg0010: 5; this scene: 5).
* NO "leader is literally 0" set this scene needed - unlike bg0007's set 111,
  every Mob-Set number this scene's placements use that CLINE type 9 resolves
  to a leader resolves to a NON-ZERO one (checked, not assumed; key 106's
  leader IS zero but no placement in this scene points at Mob-Set 106).
* NO CJK/non-cp874 name this scene needed - unlike bg0006's three teleporter
  drops, every one of this scene's 38 resolved ``MOBS_TIP`` rows is plain
  ASCII, checked directly (not assumed from the absence of a failure).

ELEVEN SETS LIST TWO VARIANT AVATAR TEMPLATES SEPARATED BY ';'.  Same rule and
the same open question as bg0003's nine, bg0004's nine, bg0005's ten,
bg0006's ten, bg0007's eight and bg0008's ten and bg0010's twelve: ship the
FIRST variant, keep the whole string in ``MULTI_VARIANT_OUTFITS``, and
``_self_check`` refuses at import if a raw ';' ever reaches the shipped
column.  [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION].  Leaders
[307, 308, 309, 310, 311, 312, 313, 315, 316, 318, 319] (11 of the 38
resolved sets), all two-variant rows (this scene does not repeat bg0003's
nine-variant outlier), covering 30 of the 57 shippable placements (measured
this round, not estimated).

NO NAME-VS-TEMPLATE DISAGREEMENT, NO EXTRA SPAWN TRIPLE, NO MULTI-TEMPLATE
ROW, NO EXTRACTION-UNRESOLVED SENTINEL.  Checked directly against this
scene's own placement file: no row carries ``extra_triple_count > 0``, no row
lists more than one template id, and no row's ``template_ids`` column reads
the literal ``UNRESOLVED``.  Same clean shape bg0003's, bg0005's, bg0006's,
bg0007's and bg0008's own crosswalks carry on these axes.

NO CREW.  Measured for this scene: 0 of CLINE type 9's 48 rows carry any
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
this scene (n_id 9) records the marker point 2198.81 units from the nearest
of this scene's 63 native placements, INSIDE the placement extents - the
widest marker-to-placement gap any of this lane's own doors has opened on so
far (wider than bg0003's 405.0-units-outside geometry, though still inside
rather than outside).  This row does NOT carry
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
    gamedata/scene/Bg0009/bg0009.placements.tsv

THE JOIN, EXACTLY, SO IT CAN BE MECHANISED LATER (done by a throwaway script
against committed TSVs read directly this round, not by hand - the tables
are large enough that hand transcription would itself be an error source;
the script's own output is what appears below, unedited except for
formatting):

    keys   = {r.n_CREATURE_TYPE: r for r in CLINE if r.n_CLINE_TYPE == 9}
    for each Mob-Set number k this scene's placements use (44 of them):
        leader = keys[k].n_LEADER_BK1
        drop k if MOBS has no row for it, or that row's s_OUTFIT is empty,
            or MOBS_TIP.s_NAME/s_TITLE/s_OUTFIT is not cp874-representable
        else row = (k, keys[k].n_ID, leader, s_OUTFIT.split(';')[0],
                    MOBS_TIP.s_NAME or '', MOBS_TIP.s_TITLE or '',
                    MOBS.n_LEVEL_MIN, MOBS.n_RANK,
                    STANDARD_MOB[n_LEVEL_MIN].n_HPMAX, MOBS.n_MOB_USAGE)
    placements = every row of bg0009.placements.tsv as
        (index, template_ids, running instance count per template_ids,
         x, y, z), in file order - no sentinel rows this scene (see above).

WHAT THIS MODULE DOES NOT CLAIM.

* Not that any of these 38 actors has been SEEN.  No human has been in this
  scene in this project's history (registry ``status:
  never_sent_to_any_client_by_this_project``, and ``login_entry_allowed`` is
  still ``false`` as of this module's own construction round).  The
  client-observable layer for this scene is empty until an attended round
  looks.
* Not that this census (built by ``world_population_bg0009``, a sibling
  module, not this one) is what raises these actors on a real server.
* Not leader+crew.  Like every sibling crosswalk this implements
  ``n_LEADER_BK1`` only.  Measured for this scene: 0 of CLINE type 9's 48
  rows carry any ``n_CREW`` value at all, so there is no pet/crew group this
  reading silently drops.
* Not wired at import time in this module - wiring
  (``CENSUS_SOURCES``/``ROSTER_COMPOSERS``/``lane_hooks`` console reader) and
  the door-open (``login_entry_allowed``) are both done by THIS SAME ROUND's
  other files, following the compressed build+wire+open precedent rounds
  ``l03cgh``/``fx0007``/``p4wire``/``p7wm17``/``78zayw`` set for scenes 5, 6,
  8, 3 and 7 (the generic contract test
  ``tests/test_lane_a_scene_census.py::ComposerContractTests`` already
  assumes every scene this lane composes for is also open at login).
"""
from __future__ import annotations

from dataclasses import dataclass


# Convention marker: shippable, no scenario flag - matching the eight
# sibling crosswalk modules' own convention.
production_allowed = True
test_only = False

SCENE_N_ID = 9
SCENE_MODEL_ID = "Bg0009"
SCENE_CLINE_TYPE = 9
# SCENE_NAME.n_SCENE_LV for this scene.
SCENE_DECLARED_LEVEL = 92

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
    "gamedata/scene/Bg0009/bg0009.placements.tsv":
        'c6b051feb2c1fe027130d95b65abdcfe2d3d937e367b2248e5372042d1e52ea0',
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  Costs 6 of the 63
# placements (see module docstring for the two distinct failure shapes).
UNRESOLVED = {
    1: (2600, 284, 'MOBS has no row for this leader'),
    101: (2642, 10048, 'MOBS row carries no s_OUTFIT avatar template'),
    102: (2643, 10049, 'MOBS row carries no s_OUTFIT avatar template'),
    103: (2644, 10050, 'MOBS row carries no s_OUTFIT avatar template'),
    104: (2645, 10051, 'MOBS row carries no s_OUTFIT avatar template'),
    105: (2646, 10052, 'MOBS row carries no s_OUTFIT avatar template'),
}

# MOBS rows in this scene that list SEVERAL avatar templates separated by
# ';', as leader n_ID -> the whole string.  The table below ships the FIRST
# variant; ``_self_check`` refuses if a ';' ever reaches the shipped column.
# [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION]
MULTI_VARIANT_OUTFITS = {
    307: 'M008_000_000_SP1;M008_000_000_SP2',
    308: 'M002_002_000_SP1;M002_002_000_SP2',
    309: 'M022_000_000_SP1;M022_000_000_SP2',
    310: 'M026_000_000_SP1;M026_000_000_SP2',
    311: 'M000_001_000_N;M000_001_000_SP1',
    312: 'M019_000_002_SP1;M019_000_002_SP2',
    313: 'M010_000_001_SP1;M010_000_001_SP2',
    315: 'M028_001_001_SP1;M028_001_001_SP2',
    316: 'M004_000_003_SP1;M004_000_003_SP2',
    318: 'M008_000_002_SP1;M008_000_002_SP2',
    319: 'M026_000_002_SP1;M026_000_002_SP2',
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
# 9 resolves to a shippable body (cp874-representable name/title/outfit).
_RESOLVED_ROWS = (
    (2, 2601, 285, 'M055_000_000_N', 'Columbus', 'Marine Transport Station', 98, 0, 186962, 2),
    (3, 2602, 286, 'P_FEMALE_952_000_SIREN', 'Siren', 'Poseidon Heir', 98, 0, 186962, 2),
    (4, 2603, 287, 'M077_000_000_N', 'Angelina', 'Witch Skull Bride', 98, 0, 186962, 2),
    (5, 2604, 288, 'M026_001_000_BOSS', 'Dyken', 'Wandering Skipper', 98, 0, 186962, 2),
    (6, 2605, 289, 'P_FEMALE_015_000_BESAN', 'Beeson', 'Beautiful  Slaves', 98, 0, 186962, 2),
    (7, 2606, 290, 'P_MALE_015_000_KENNY', 'Kenny', 'Strong Slaves', 98, 0, 186962, 2),
    (8, 2607, 291, 'P_MALE_015_000_RICK', 'Rick', 'Savvy Slaves', 98, 0, 186962, 2),
    (9, 2608, 292, 'P_MALE_003_000_HAWK', 'Hoeker', 'Familiar Adventurers', 98, 0, 186962, 2),
    (10, 2609, 293, 'M026_000_000_N', 'Skeleton Hoeker', 'Cursed', 98, 0, 186962, 2),
    (11, 2610, 294, 'M010_001_000_SP2', 'Bardgett', 'Navy Remnants', 98, 0, 186962, 2),
    (12, 2611, 295, 'P_FEMALE_952_000_SIREN', 'Siren', 'World Keeper', 98, 0, 186962, 2),
    (13, 2612, 296, 'P_MALE_014_000_COLUMBUS', 'Columbus', 'Voyager into Chaos', 98, 0, 186962, 2),
    (14, 2613, 297, 'P_MALE_009_001_MAGELLAN', 'Magellan', 'Explorers into Chaos', 98, 0, 186962, 2),
    (15, 2614, 298, 'M074_000_000_N', 'Robinson', 'Castaways into Chaos', 98, 0, 186962, 2),
    (16, 2615, 299, 'P_MALE_014_000_COLUMBUS', 'Columbus', 'Ran the Wrong World', 98, 0, 186962, 2),
    (17, 2616, 300, 'P_MALE_009_001_MAGELLAN', 'Magellan', 'Ran the Wrong World', 98, 0, 186962, 2),
    (18, 2617, 301, 'M074_000_000_N', 'Robinson', "Don't need to Back Home", 98, 0, 186962, 2),
    (19, 2618, 302, 'M026_000_002_SP1', 'Skeleton men', '', 98, 0, 186962, 2),
    (20, 2619, 303, 'M026_000_002_SP1', 'Skeleton men', '', 98, 0, 186962, 2),
    (21, 2620, 304, 'P_MALE_002_002_N', 'Dead Survivor', '', 98, 0, 186962, 2),
    (22, 2621, 305, 'M077_000_000_N', 'Angelina', 'Royal Princess', 98, 0, 186962, 2),
    (23, 2622, 306, 'M026_000_001_SP2', 'Skeleton Captain', '', 98, 0, 186962, 2),
    (24, 2623, 307, 'M008_000_000_SP1', 'Blue Ocean soul', '', 93, 1, 160837, 1),
    (25, 2624, 308, 'M002_002_000_SP1', 'Blue Tiger', '', 93, 1, 160837, 1),
    (26, 2625, 309, 'M022_000_000_SP1', 'Harpy', '', 93, 1, 160837, 1),
    (27, 2626, 310, 'M026_000_000_SP1', 'Skeleton Sseaman', '', 93, 1, 160837, 1),
    (28, 2627, 311, 'M000_001_000_N', 'Exotic Demon Wolf', '', 93, 1, 160837, 1),
    (29, 2628, 312, 'M019_000_002_SP1', 'Catwoman pirate', '', 93, 1, 160837, 1),
    (30, 2629, 313, 'M010_000_001_SP1', 'Captain Golem', '', 93, 1, 160837, 1),
    (31, 2630, 314, 'M010_000_001_SP3', 'Captain Golem Rabia', '', 93, 1, 160837, 1),
    (32, 2631, 315, 'M028_001_001_SP1', 'Red blood Bee', '', 93, 1, 160837, 1),
    (33, 2632, 316, 'M004_000_003_SP1', 'End date Flower', '', 93, 1, 160837, 1),
    (34, 2633, 317, 'M004_000_003_SP3', 'Destroy Magic Flower', '', 93, 1, 160837, 1),
    (35, 2634, 318, 'M008_000_002_SP1', 'Dark soul', '', 93, 1, 160837, 1),
    (36, 2635, 319, 'M026_000_002_SP1', 'Skeleton Mate', '', 93, 1, 160837, 1),
    (37, 2636, 320, 'M026_000_002_SP3', 'Skeleton Commander Corella', '', 93, 1, 160837, 1),
    (41, 2640, 546, 'M019_000_000_SP4', 'Black braid Edward', '', 93, 1, 160837, 8),
    (44, 2641, 549, 'M022_000_003_SP2', 'Bermuda Banshee', '', 93, 1, 160837, 8),
)

IDENTITIES = {row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS}


@dataclass(frozen=True)
class Bg0009Placement:
    """One Bg0009 placement resolved to a real, named, bodied actor."""

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
    (0, 1, 1, -1649.3614501953125, 22476.271484375, 202.99220275878906),
    (1, 2, 1, 343.4341125488281, 22189.634765625, 203.00289916992188),
    (2, 3, 1, -2269.171875, 14412.01953125, 898.9771118164062),
    (3, 4, 1, 8756.8037109375, 14297.0400390625, 724.3911743164062),
    (4, 5, 1, 6775.22607421875, 12644.9228515625, 966.7896728515625),
    (5, 6, 1, 8274.0908203125, 2459.46875, 1067.9248046875),
    (6, 7, 1, 15191.9638671875, 780.2459716796875, 1074.2056884765625),
    (7, 8, 1, 14123.5791015625, -6495.99853515625, 817.440185546875),
    (8, 9, 1, 7697.13037109375, -10194.1240234375, 814.736572265625),
    (9, 10, 1, 7682.60107421875, -10158.4775390625, 814.69482421875),
    (10, 11, 1, -719.6953125, -5166.8623046875, 695.360595703125),
    (11, 12, 1, -13991.4853515625, -5770.125, 707.5211791992188),
    (12, 13, 1, -13907.927734375, -162.67430114746094, 653.0106811523438),
    (13, 14, 1, -16508.34765625, 14414.048828125, 573.7255859375),
    (14, 15, 1, -18038.29296875, -6764.7392578125, 703.40478515625),
    (15, 16, 1, -10723.7529296875, -5309.9130859375, 798.1458129882812),
    (16, 17, 1, -15379.1015625, -14412.2890625, 477.2687072753906),
    (17, 18, 1, -23336.822265625, -21821.201171875, 1837.5833740234375),
    (18, 19, 1, 16092.2470703125, -25764.166015625, 2671.437744140625),
    (19, 20, 1, 11269.8466796875, -25263.34765625, 2671.420166015625),
    (20, 21, 1, -11305.3076171875, -22209.271484375, 2304.85546875),
    (21, 22, 1, -1916.1259765625, -23553.572265625, 2699.32763671875),
    (22, 24, 1, 5430.5634765625, 16427.580078125, 563.089111328125),
    (23, 24, 2, 182.9438018798828, 17384.228515625, 815.8140258789062),
    (24, 24, 3, -3555.72705078125, 14870.392578125, 888.99951171875),
    (25, 25, 1, 10208.1953125, 9176.3173828125, 566.5203247070312),
    (26, 25, 2, 6318.87109375, 6598.98583984375, 665.1392822265625),
    (27, 25, 3, 10235.986328125, 2913.44287109375, 1081.121826171875),
    (28, 26, 1, 14596.990234375, -1704.669921875, 1055.474365234375),
    (29, 26, 2, 11328.86328125, -7498.95703125, 819.6270141601562),
    (30, 26, 3, 7448.45654296875, -11636.37890625, 833.11181640625),
    (31, 27, 1, 2918.44287109375, -11638.228515625, 795.064697265625),
    (32, 27, 2, -721.9854125976562, -7971.3330078125, 696.33740234375),
    (33, 27, 3, 3565.32958984375, -2613.22509765625, 179.20509338378906),
    (34, 28, 1, -12471.8955078125, -6816.70166015625, 508.5137023925781),
    (35, 28, 2, -17235.171875, -6418.365234375, 590.8557739257812),
    (36, 28, 3, -7750.37744140625, -8592.8984375, 569.0947875976562),
    (37, 29, 1, -14951.6220703125, 104.36329650878906, 642.9874267578125),
    (38, 29, 2, -13962.1494140625, 2837.025146484375, 685.4301147460938),
    (39, 29, 3, -16163.2099609375, 6382.09326171875, 582.4025268554688),
    (40, 30, 1, -16564.21484375, 10568.1455078125, 577.0587158203125),
    (41, 30, 2, -15422.05078125, 13757.2841796875, 583.0142822265625),
    (42, 31, 1, -17501.869140625, 12612.115234375, 607.1314697265625),
    (43, 30, 3, -11558.041015625, 14265.80859375, 666.61376953125),
    (44, 30, 4, -8228.3310546875, 10672.6494140625, 896.0972290039062),
    (45, 28, 4, -15438.71875, -11081.0400390625, 780.1226196289062),
    (46, 32, 1, -15607.6240234375, -18035.623046875, 778.6655883789062),
    (47, 32, 2, -14139.2021484375, -23479.0234375, 2261.076171875),
    (48, 33, 1, -20881.39453125, -22373.560546875, 1526.56689453125),
    (49, 34, 1, -23619.08984375, -25924.498046875, 2521.283203125),
    (50, 35, 1, -6184.83984375, -22127.34765625, 2690.646240234375),
    (51, 35, 2, 748.4542846679688, -22408.0859375, 2690.621337890625),
    (52, 36, 1, 17521.916015625, -23263.677734375, 2671.41943359375),
    (53, 36, 2, 12749.212890625, -15152.8642578125, 2762.376953125),
    (54, 37, 1, 20391.560546875, -24944.775390625, 2671.420166015625),
    (55, 23, 1, 14246.3740234375, -25420.291015625, 2671.43505859375),
    (56, 41, 1, -17677.73828125, 11541.7734375, 648.3300170898438),
    (57, 44, 1, -14789.716796875, 11079.390625, 588.1323852539062),
    (58, 101, 1, 14061.8095703125, 1257.125, 1061.717041015625),
    (59, 102, 1, 16447.609375, -3611.6201171875, 1022.5355834960938),
    (60, 103, 1, -17437.5390625, -5768.927734375, 560.8355712890625),
    (61, 104, 1, -14326.34765625, -15005.4267578125, 469.7643127441406),
    (62, 105, 1, -183.2071990966797, 17093.224609375, 815.8538208007812),
)

PLACEMENT_COUNT = len(_PLACEMENT_ROWS)


class Bg0009IdentityError(ValueError):
    """A refusal from this module, always with a reason in the message."""


def identity_for(template_id: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    ``None`` is exactly the 6 sets in ``UNRESOLVED`` and nothing else: this
    function never substitutes, and never falls back to the Mob-Set number
    that ``GT-078`` proved wrong on the owner's screen.
    """
    if type(template_id) is not int or type(template_id) is bool:
        raise Bg0009IdentityError("template id must be an int")
    return IDENTITIES.get(template_id)


def shippable_placements() -> tuple[Bg0009Placement, ...]:
    """The 57 placements of the 63 that resolve to a real identity."""
    out = []
    for index, template_id, mm_instance, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(template_id)
        if identity is None:
            continue
        out.append(Bg0009Placement(
            index, template_id, mm_instance, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The 6 that are dropped, each with the id and the reason.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH ones and WHY.
    """
    out = []
    for index, template_id, _mm, x, y, z in _PLACEMENT_ROWS:
        if template_id in IDENTITIES:
            continue
        cline_row_id, leader, reason = UNRESOLVED.get(
            template_id, (0, 0, "set not in CLINE 9"))
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
        raise Bg0009IdentityError(
            "expected 38 resolved sets, found %d" % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg0009IdentityError("duplicate Mob-Set number in the table")
    if len(UNRESOLVED) != 6:
        raise Bg0009IdentityError(
            "expected 6 unresolved sets, found %d" % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg0009IdentityError("a set is both resolved and unresolved")
    if len(_PLACEMENT_ROWS) != 63:
        raise Bg0009IdentityError(
            "expected 63 placements, found %d" % len(_PLACEMENT_ROWS))
    # Control 1: every Mob-Set number this scene's placements use is either
    # resolved or named as unresolved, and the two sets together are EXACTLY
    # this scene's used keys - a placement keyed by a number this table has
    # never heard of means the placement file and the crosswalk came from
    # different extractions.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if scene_sets != table_sets:
        raise Bg0009IdentityError(
            "placement Mob-Set numbers and this table's keys disagree: %r"
            % sorted(scene_sets ^ table_sets))
    if len(table_sets) != 44:
        raise Bg0009IdentityError(
            "expected 44 distinct Mob-Set numbers, found %d" % len(table_sets))
    if not no_set_number_is_shipped_as_identity():
        raise Bg0009IdentityError(
            "a row ships its own Mob-Set number as an identity")
    for row in _RESOLVED_ROWS:
        (template_id, cline_row_id, n_id, outfit, name, title, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1:
            raise Bg0009IdentityError(
                "set %d carries no CLINE row locator" % template_id)
        if ";" in outfit:
            raise Bg0009IdentityError(
                "set %d ships a multi-variant outfit string" % template_id)
        if not outfit or not outfit.isascii():
            raise Bg0009IdentityError(
                "set %d has an empty or non-ASCII outfit" % template_id)
        if not name.isascii() or not title.isascii():
            raise Bg0009IdentityError(
                "set %d has a non-ASCII name or title" % template_id)
        if not name:
            raise Bg0009IdentityError(
                "set %d has no display name" % template_id)
        if max_hp < 1 or level < 1:
            raise Bg0009IdentityError("set %d has a bad level/HP" % template_id)
    if len(shippable_placements()) != 57:
        raise Bg0009IdentityError("expected 57 shippable placements")
    if len(unshippable_placements()) != 6:
        raise Bg0009IdentityError("expected 6 unshippable placements")
    ids = [p.actor_identity for p in shippable_placements()]
    if len(ids) != len(set(ids)):
        raise Bg0009IdentityError("actor identities collide within this table")


_self_check()
