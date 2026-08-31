"""Who each Bg0011 placement actually IS - Deep Sea Temple floor 2's real cast.

LANE-A (WORLD).  ``COO-DECISION 2026-08-30T14:41+07:00`` (pf_bridge
``notes_to_chief/20260830_1441_COO-DECISION-scene4-slave-market-first-door.md``)
approved building the ten still-shut doors surveyed in round ``12lyda`` in
native-placement-count order ("no need to ask again per door").  Scenes 4,
5, 10, 14, 6, 8, 3, 7 and 9 are open; this is the ninth door in the
sequence and the highest native placement count of the one still shut
(130): scene 11 (Bg0011, "Deep Sea Temple floor 2", 56 placements).  This
module is the identity half, the same split every earlier crosswalk used;
``world_population_bg0011`` is the census half.

ELEVATED-RISK ROW, NAMED RATHER THAN HIDDEN.  Registry
``table_row_differences.the_two_interiors`` names this row and scene 10's
as the two an attended round should look at first if a landing goes wrong
(``n_CANGLIDE`` 0, ``n_LIMIT_HEIGHT`` 0 - a no-glide, no-height-limit
interior rather than an open island).  ``COO-DECISION
20260831T10:42+07:00`` already confirmed opening scene 10 on this basis
without waiting for an attended round first; this round applies the same
ruling to scene 11 rather than asking again.

THE CROSSWALK, RE-DERIVED HERE RATHER THAN TAKEN FROM A CITATION.
``SCENE_NAME[s_MODLE_ID=Bg0011].n_CLINE_TYPE`` was read directly off the
bridge clone this round:

    SCENE_NAME[s_MODLE_ID=Bg0011].n_ID          = 11
    SCENE_NAME[s_MODLE_ID=Bg0011].n_CLINE_TYPE  = 11   (a real value, direct)
    SCENE_NAME[s_MODLE_ID=Bg0011].n_SCENE_LV    = 95
    CLINE[(11, <Mob-Set number>)].n_LEADER_BK1  = the real MOBS.n_ID
    MOBS[n_ID].s_OUTFIT                         = the avatar the client loads
    MOBS_TIP[n_ID].s_NAME / s_TITLE             = the label under the actor
    STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX      = max HP (the one derived col)

Same direct-selector shape ``world_bg0003_identity``, ``world_bg0004_identity``,
``world_bg0005_identity``, ``world_bg0006_identity``, ``world_bg0007_identity``,
``world_bg0008_identity``, ``world_bg0009_identity`` and ``world_bg0010_identity``
all ship (one of RE-128's 19 direct CLINE types, not one of its 240 instance
scenes).

WHAT IS ESTABLISHED HERE AND WHAT IS NOT, STATED THE SAME WAY THE OTHER
NINE CROSSWALK MODULES STATE IT.

    ESTABLISHED - THE TABLE.  This scene's cast is drawn from CLINE type
    11's leader column.  CONTROL 1 below is a SUBSET, not an exact match:
    this scene's placements use exactly 31 distinct Mob-Set numbers (1-26,
    101-105), all 31 of them present in CLINE type 11's own 32-row key
    range (1-26, 101-106) - the same 'placement file touches only PART of
    its own CLINE type' shape bg0004's 55-of-61, bg0010's 40-of-41 and
    bg0009's 44-of-48 crosswalks carry (unlike scenes 5's, 6's, 7's and 8's
    own EXACT-match crosswalks).  ONE key exists in CLINE type 11 that no
    placement in this scene uses (106) - and its own ``n_LEADER_BK1`` (9061)
    is real and non-zero, but leads nowhere shippable anyway: ``CONSTDATA
    MOBS`` row 9061 carries an empty ``s_OUTFIT`` AND a non-cp874 (CJK,
    four Han characters, not reproduced here - this file and every file
    under src/ must stay cp874-encodable) ``s_NAME`` - checked, not
    assumed, even though no placement here ever points at it.

    NOT ESTABLISHED - THE PAIRING.  Which leader belongs to which Mob-Set
    number.  No human has stood in this scene (registry ``status:
    never_sent_to_any_client_by_this_project``), so every name below is a
    table inference, the bottom of the evidence order COO set on
    2026-08-28T21:30, until an attended round looks.

DISCREPANCY, MEASURED AND NOT SILENTLY RECONCILED.  The registry's own
``native_definition_count`` for scene 11 reads 31.  This round's own count
of CLINE type 11's rows (grouped by ``n_CREATURE_TYPE``, checked for
duplicates - there are none) is 32, WIDER than 31 by the one untouched key
named above.  But 31 is also EXACTLY the count of distinct Mob-Set numbers
this scene's own 56 placements use (CONTROL 1) - so, like scene 9's own
44-of-44 agreement and unlike bg0003's 52-of-51, bg0004's 56-vs-55-used/
61-total, bg0007's 57-of-56 and bg0008's 49-of-48 (all of which disagreed
with THIS round's own re-derivation by exactly one), scene 11's registry
field and this round's own placement-side count AGREE, the second time
this lane has measured that agreement rather than the earlier off-by-one
pattern.  What they still do not agree with is CLINE type 11's own total
row count (32), which this round did not expect them to.

CONTROL 1 - EXACT SUBSET, MEASURED.  The 56 placements resolve to 31
distinct Mob-Set numbers; CLINE type 11 has 32 keys (1-26, 101-106); the 31
the scene uses are exactly {1-26} union {101-105} - every one present, none
missing - and the one key the scene never touches (106) is NOT "no
creature" (see the discrepancy paragraph above), it is a real leader whose
own MOBS row would have failed to resolve anyway (see ELEVATED-RISK/
established-here paragraph above).

CONTROL 2 - PRESENT, WITH THIS MODULE, VERIFIED RATHER THAN ASSUMED TO BE
ABSENT.  Unlike bg0003's, bg0006's and bg0008's own Control 2 (no row for
those scenes), ``world_bg0015_identity.SCENE_LEVEL_CONTROL`` DOES carry a
row for this scene already: ``'Bg0011': (11, 95, 99.0, 20.0)`` - the
CLINE-reading median level (99.0) is closer to the declared level (95)
than the set-number-reading median (20.0), placing this scene WITH that
module rather than against it, the same side bg0004's, bg0005's, bg0006's,
bg0007's, bg0008's, bg0009's and bg0010's own rows are on.  Grepped this
round rather than trusted from a sibling's citation - see this module's
own worked example for why that check matters (bg0009's own docstring
claimed this table had no row for it, which this round found to be no
longer true of the shared table it cites).

CONTROL 3 - NO SELF-MAPPING, WEAK, SAME CAVEAT AS THE OTHER NINE SCENES.  0
of the 26 resolved rows have ``mobs_n_id == template_id`` (measured, not
assumed): none.  A shape check, not evidence.

FIVE OF THE 31 SETS DO NOT RESOLVE (COST 5 PLACEMENTS), ONE FAMILIAR
FAILURE SHAPE, NOT TWO.

* Sets [101, 102, 103, 104, 105] -> leaders [10058, 10059, 10060, 10061,
  10062].  Every one HAS a ``CONSTDATA MOBS`` row but its ``s_OUTFIT``
  column is empty - the identical 'path-finding helper, not a creature'
  shape every sibling scene's own 101+ block carries (bg0003: 9, bg0004: 6,
  bg0005: 4, bg0006: 9, bg0007: 10, bg0008: 5, bg0009: 5, bg0010: 5; this
  scene: 5).
* NO "MOBS has no row at all" set this scene needed - unlike bg0009's set
  1, every Mob-Set number 1-26 this scene's placements use resolves to a
  real ``CONSTDATA MOBS`` row.
* NO "leader is literally 0" set this scene needed - unlike bg0007's set
  111, every Mob-Set number this scene's placements use that CLINE type 11
  resolves to a leader resolves to a NON-ZERO one (checked, not assumed;
  key 106's leader is real too, see above - it simply has no placement
  pointing at it and would have failed on ``s_OUTFIT`` anyway).
* NO CJK/non-cp874 name among the 26 SHIPPED rows this scene needed -
  unlike bg0006's three teleporter drops, every one of this scene's 26
  resolved ``MOBS_TIP`` rows is plain ASCII, checked directly (not assumed
  from the absence of a failure).  The one CJK name this round DID find
  (MOBS row 9061, a four-Han-character ``s_NAME`` not reproduced here to
  keep this file cp874-encodable) belongs to the untouched key 106 above,
  and never reaches a placement.

SEVEN SETS LIST TWO VARIANT AVATAR TEMPLATES SEPARATED BY ';'.  Same rule
and the same open question as bg0003's nine, bg0004's nine, bg0005's ten,
bg0006's ten, bg0007's eight, bg0008's ten, bg0009's eleven and bg0010's
twelve: ship the FIRST variant, keep the whole string in
``MULTI_VARIANT_OUTFITS``, and ``_self_check`` refuses at import if a raw
';' ever reaches the shipped column.  [LANE-A ASSUMPTION - AWAITING
COO/OWNER CONFIRMATION].  Leaders [688, 689, 690, 691, 692, 694, 695] (7 of
the 26 resolved sets), all two-variant rows (this scene does not repeat
bg0003's nine-variant outlier), covering 27 of the 51 shippable placements
(measured this round, not estimated).

NO NAME-VS-TEMPLATE DISAGREEMENT, NO EXTRA SPAWN TRIPLE, NO MULTI-TEMPLATE
ROW, NO EXTRACTION-UNRESOLVED SENTINEL.  Checked directly against this
scene's own placement file: no row carries ``extra_triple_count > 0``, no
row lists more than one template id, and no row's ``template_ids`` column
reads the literal ``UNRESOLVED``.  Same clean shape every sibling scene's
own crosswalk carries on these axes.

NO CREW.  Measured for this scene: 0 of CLINE type 11's 32 rows carry any
``n_CREW`` value at all (checked ``n_CREW1`` through ``n_CREW6``), the same
"no pet/crew group silently dropped" shape every sibling scene carries.

HEADING.  Same measurement every sibling scene's own ``_entry`` made for
its own scene: the extra f32 triple this TSV format carries (columns
``f32_3``/``f32_4``/``f32_5``) is a small round-number set across unrelated
rows here too (5/8/4 distinct values respectively) - the shape of a
radius, not a rotation - so the census half reuses
``world_population.HEADINGS`` on the placement index, same as every other
scene.

LANDING GEOMETRY.  ``scenarios/world_scene_registry_001.json``'s own
``table_row_differences.marker_geometry_measured_not_enforced`` block for
this scene (n_id 11) records the marker point 1107.764 units from the
nearest of this scene's 56 native placements, INSIDE the placement extents
(cross-checked directly against this module's own ``_PLACEMENT_ROWS``:
placement index 0, Mob-Set 1, is the nearest placement to the registry's
own spawn point, and IS the 1107.764-unit distance the registry names).
This row DOES carry ``table_row_differences.the_two_interiors`` (checked,
not assumed - see the ELEVATED-RISK paragraph above), the same flag scene
10's row carries and no other scene in this lane's own door sequence
carries.  Still 'recorded, not enforced' (a .npc file is not terrain), but
the fact this lane's own elevated-risk row is now open at login is worth
naming rather than leaving buried in the registry JSON.

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
    gamedata/scene/Bg0011/Bg0011.placements.tsv

THE JOIN, EXACTLY, SO IT CAN BE MECHANISED LATER (done by a throwaway
script against committed TSVs read directly this round, not by hand - the
tables are large enough that hand transcription would itself be an error
source; the script's own output is what appears below, unedited except for
formatting):

    keys   = {r.n_CREATURE_TYPE: r for r in CLINE if r.n_CLINE_TYPE == 11}
    for each Mob-Set number k this scene's placements use (31 of them):
        leader = keys[k].n_LEADER_BK1
        drop k if MOBS has no row for it, or that row's s_OUTFIT is empty,
            or MOBS_TIP.s_NAME/s_TITLE/s_OUTFIT is not cp874-representable
        else row = (k, keys[k].n_ID, leader, s_OUTFIT.split(';')[0],
                    MOBS_TIP.s_NAME or '', MOBS_TIP.s_TITLE or '',
                    MOBS.n_LEVEL_MIN, MOBS.n_RANK,
                    STANDARD_MOB[n_LEVEL_MIN].n_HPMAX, MOBS.n_MOB_USAGE)
    placements = every row of Bg0011.placements.tsv as
        (index, template_ids, running instance count per template_ids,
         x, y, z), in file order - no sentinel rows this scene (see above).

WHAT THIS MODULE DOES NOT CLAIM.

* Not that any of these 26 actors has been SEEN.  No human has been in
  this scene in this project's history (registry ``status:
  never_sent_to_any_client_by_this_project``, and ``login_entry_allowed``
  is still ``false`` as of this module's own construction round).  The
  client-observable layer for this scene is empty until an attended round
  looks - and this is the scene most likely to need that look, per the
  elevated-risk flag above.
* Not that this census (built by ``world_population_bg0011``, a sibling
  module, not this one) is what raises these actors on a real server.
* Not leader+crew.  Like every sibling crosswalk this implements
  ``n_LEADER_BK1`` only.  Measured for this scene: 0 of CLINE type 11's 32
  rows carry any ``n_CREW`` value at all, so there is no pet/crew group
  this reading silently drops.
* Not wired at import time in this module - wiring
  (``CENSUS_SOURCES``/``ROSTER_COMPOSERS``/``lane_hooks`` console reader)
  and the door-open (``login_entry_allowed``) are both done by THIS SAME
  ROUND's other files, following the compressed build+wire+open precedent
  rounds ``l03cgh``/``fx0007``/``p4wire``/``p7wm17``/``78zayw``/``ir0lpw``
  set for scenes 5, 6, 8, 3, 7 and 9 (the generic contract test
  ``tests/test_lane_a_scene_census.py::ComposerContractTests`` already
  assumes every scene this lane composes for is also open at login).
"""
from __future__ import annotations

from dataclasses import dataclass


# Convention marker: shippable, no scenario flag - matching the nine
# sibling crosswalk modules' own convention.
production_allowed = True
test_only = False

SCENE_N_ID = 11
SCENE_MODEL_ID = "Bg0011"
SCENE_CLINE_TYPE = 11
# SCENE_NAME.n_SCENE_LV for this scene.
SCENE_DECLARED_LEVEL = 95

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
    "gamedata/scene/Bg0011/Bg0011.placements.tsv":
        '712fb2d88ebe385615d43bd5233437329ebcdda31d196521dcd0ba69ac469c0d',
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  Costs 5 of the 56
# placements (see module docstring - one failure shape this scene, unlike
# most siblings' two).
UNRESOLVED = {
    101: (3026, 10058, 'MOBS row carries no s_OUTFIT avatar template'),
    102: (3027, 10059, 'MOBS row carries no s_OUTFIT avatar template'),
    103: (3028, 10060, 'MOBS row carries no s_OUTFIT avatar template'),
    104: (3029, 10061, 'MOBS row carries no s_OUTFIT avatar template'),
    105: (3030, 10062, 'MOBS row carries no s_OUTFIT avatar template'),
}

# MOBS rows in this scene that list SEVERAL avatar templates separated by
# ';', as leader n_ID -> the whole string.  The table below ships the FIRST
# variant; ``_self_check`` refuses if a ';' ever reaches the shipped
# column.  [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION]
MULTI_VARIANT_OUTFITS = {
    688: 'M025_002_000_SP1;M025_002_000_SP2',
    689: 'M024_001_000_SP1;M024_001_000_SP2',
    690: 'M019_000_001_SP1;M019_000_001_SP2',
    691: 'M026_000_001_SP1;M026_000_001_SP2',
    692: 'M016_000_000_SP1;M016_000_000_SP2',
    694: 'M026_001_001_SP1;M026_001_001_SP2',
    695: 'M016_000_001_N;M016_000_001_SP1',
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
# 26 rows: every Mob-Set number this scene's placements use that CLINE type
# 11 resolves to a shippable body (cp874-representable name/title/outfit).
_RESOLVED_ROWS = (
    (1, 3000, 675, 'M026_001_001_SP3', 'Balas', 'Skull Chief', 104, 0, 221803, 2),
    (2, 3001, 676, 'M019_000_001_SP3', 'Fisher', 'Crusader Chief', 104, 0, 221803, 2),
    (3, 3002, 677, 'M077_000_000_N', 'Angelina', 'Royalty Generations', 104, 0, 221803, 2),
    (4, 3003, 678, 'M074_000_001_N', 'Horror Refugees', '', 104, 0, 221803, 2),
    (5, 3004, 679, 'M071_000_003_SP3', 'Beauty Refugees', '', 104, 0, 221803, 2),
    (6, 3005, 680, 'P_FEMALE_007_002_N', 'Brave Refugees', '', 104, 0, 221803, 2),
    (7, 3006, 681, 'P_FEMALE_007_002_SANDER', 'Sinda', '', 104, 0, 221803, 2),
    (8, 3007, 682, 'M026_001_000_BOSS', 'Dyken', 'Lovestruck', 104, 0, 221803, 2),
    (9, 3008, 683, 'M077_000_000_N', 'Angelina', 'Savior of Mankind', 104, 0, 221803, 2),
    (10, 3009, 684, 'M076_000_000_N', 'Sea Phantom', 'Brave Enemies', 104, 0, 221803, 2),
    (11, 3010, 685, 'P_FEMALE_012_000_MELPOMENE', 'Melpomen', 'Holy Temple Priest', 104, 0, 221803, 2),
    (12, 3011, 686, 'P_MALE_012_000_N', 'Subjugation Magician', '', 104, 0, 221803, 2),
    (13, 3012, 687, 'P_FEMALE_952_000_SIREN', 'Siren', 'Creator', 104, 0, 221803, 2),
    (14, 3013, 688, 'M025_002_000_SP1', 'Gentry Platypus', '', 99, 1, 192488, 1),
    (15, 3014, 689, 'M024_001_000_SP1', 'Penguin Master Sergeant', '', 99, 1, 192488, 1),
    (16, 3015, 690, 'M019_000_001_SP1', 'Seabed Crusader', '', 99, 1, 192488, 1),
    (17, 3016, 691, 'M026_000_001_SP1', 'Skeleton Chiliarch', '', 99, 1, 192488, 1),
    (18, 3017, 692, 'M016_000_000_SP1', 'Sewer Iron Man', '', 99, 1, 192488, 1),
    (19, 3018, 693, 'M018_000_000_N', 'Navy Two Tripods', '', 99, 1, 192488, 1),
    (20, 3019, 694, 'M026_001_001_SP1', 'Skeleton Captain', '', 99, 1, 192488, 1),
    (21, 3020, 695, 'M016_000_001_N', 'Steam Iron Man', '', 99, 1, 192488, 1),
    (22, 3021, 696, 'M018_000_002_N', 'Navy Tiger Mech', '', 99, 1, 192488, 1),
    (23, 3022, 697, 'M026_001_001_BOSS', 'Undead Besso', '', 99, 1, 192488, 1),
    (24, 3023, 669, 'M016_000_001_SP3', 'Steam Iron Giant', '', 99, 1, 192488, 1),
    (25, 3024, 750, 'M074_000_000_N', 'Collect Scrap Vendor', '', 105, 0, 228055, 2),
    (26, 3025, 674, 'M008_000_002_SP3', 'Guard Soul', '', 104, 1, 221803, 1),
)

IDENTITIES = {row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS}


@dataclass(frozen=True)
class Bg0011Placement:
    """One Bg0011 placement resolved to a real, named, bodied actor."""

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
# file in file order.  No sentinel rows this scene (see above).
_PLACEMENT_ROWS = (
    (0, 1, 1, 14149.349609375, 23215.52734375, 371.77398681640625),
    (1, 2, 1, 16368.7646484375, 16040.8837890625, 358.1767883300781),
    (2, 3, 1, 10114.2490234375, 12236.7822265625, 455.9205017089844),
    (3, 4, 1, 11023.091796875, 9379.65625, 455.9252014160156),
    (4, 5, 1, 8101.041015625, 9032.7216796875, 275.601806640625),
    (5, 6, 1, 9443.3056640625, 7578.599609375, 455.9205017089844),
    (6, 7, 1, 15690.6552734375, 963.780517578125, 455.9252014160156),
    (7, 8, 1, 17744.44140625, 1710.612060546875, 455.9252014160156),
    (8, 9, 1, -2230.484375, -5905.62060546875, -4184.1611328125),
    (9, 10, 1, -1432.01513671875, -13604.4765625, -4184.1611328125),
    (10, 11, 1, -14263.958984375, 2237.61865234375, -4412.56298828125),
    (11, 13, 1, -12217.0439453125, -21853.974609375, -4498.79833984375),
    (12, 14, 1, 21743.38671875, 15896.326171875, 371.77911376953125),
    (13, 14, 2, 3625.647216796875, 15544.4765625, 410.0400085449219),
    (14, 14, 3, 108.77339935302734, 15531.9453125, 410.0351867675781),
    (15, 15, 1, 11138.3349609375, 19692.5703125, 455.9299011230469),
    (16, 15, 2, 11138.4248046875, 15452.5283203125, 506.7755126953125),
    (17, 16, 1, 6458.30224609375, 15352.9443359375, 492.1217956542969),
    (18, 15, 3, 6621.09619140625, 19512.94140625, 493.08209228515625),
    (19, 18, 1, 14249.37109375, 12069.1552734375, 455.92230224609375),
    (20, 19, 1, 10738.6474609375, 4526.6455078125, 424.9296875),
    (21, 20, 1, -9111.408203125, -15844.326171875, -4412.56494140625),
    (22, 20, 2, -9071.5087890625, -11396.6279296875, -4412.55322265625),
    (23, 21, 1, -4879.14208984375, -11372.3916015625, -4412.56103515625),
    (24, 21, 2, -4836.4833984375, -15889.3251953125, -4412.55322265625),
    (25, 24, 1, -23315.921875, -15531.681640625, -4412.55810546875),
    (26, 14, 4, 21795.50390625, 11553.1640625, 371.773193359375),
    (27, 12, 1, -20082.76171875, -9963.923828125, -4496.69970703125),
    (28, 18, 2, 18754.560546875, 12119.662109375, 455.9252014160156),
    (29, 18, 3, 18728.5546875, 7545.03369140625, 455.9158020019531),
    (30, 16, 2, 16553.015625, 9642.173828125, 275.60650634765625),
    (31, 18, 4, 14455.875, 7603.8310546875, 455.9205017089844),
    (32, 16, 3, -4747.55126953125, -3678.241455078125, -4412.556640625),
    (33, 17, 1, -4815.45263671875, -8172.107421875, -4412.5478515625),
    (34, 17, 2, -9188.0419921875, -8165.97265625, -4412.55810546875),
    (35, 16, 4, -9175.0478515625, -3602.760009765625, -4412.55078125),
    (36, 16, 5, -12474.443359375, -11417.4853515625, -4412.55810546875),
    (37, 16, 6, -12581.818359375, -15900.4189453125, -4412.5546875),
    (38, 22, 1, -16860.6171875, -15836.875, -4412.56298828125),
    (39, 16, 7, -16730.900390625, -11375.8671875, -4412.55322265625),
    (40, 16, 8, -23222.41796875, -12518.08984375, -4412.55810546875),
    (41, 17, 3, -6992.0107421875, -5988.9677734375, -4592.8720703125),
    (42, 19, 2, -12879.826171875, -4423.88330078125, -4422.3056640625),
    (43, 19, 3, -12977.75390625, -7480.7568359375, -4469.3466796875),
    (44, 19, 4, -16417.3828125, -7453.4580078125, -4391.92333984375),
    (45, 23, 1, -16663.072265625, -4109.37255859375, -4412.5537109375),
    (46, 19, 5, -14951.0078125, -6018.94287109375, -4510.29541015625),
    (47, 20, 3, -7075.8359375, -13716.59765625, -4592.8720703125),
    (48, 25, 1, 7843.92822265625, 10938.0771484375, 275.6112976074219),
    (49, 19, 6, 14429.572265625, 4526.6455078125, 424.9296875),
    (50, 26, 1, 25118.537109375, 20715.20703125, 474.93231201171875),
    (51, 103, 1, 24341.73046875, 16966.89453125, 455.9211120605469),
    (52, 101, 1, 11203.68359375, 26801.767578125, 455.9211120605469),
    (53, 102, 1, 158.2012939453125, 13301.3505859375, 366.6429138183594),
    (54, 104, 1, -17003.572265625, 1999.0487060546875, -4412.5576171875),
    (55, 105, 1, -22435.470703125, -10945.1220703125, -4412.5576171875),
)

PLACEMENT_COUNT = len(_PLACEMENT_ROWS)


class Bg0011IdentityError(ValueError):
    """A refusal from this module, always with a reason in the message."""


def identity_for(template_id: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    ``None`` is exactly the 5 sets in ``UNRESOLVED`` and nothing else: this
    function never substitutes, and never falls back to the Mob-Set number
    that ``GT-078`` proved wrong on the owner's screen.
    """
    if type(template_id) is not int or type(template_id) is bool:
        raise Bg0011IdentityError("template id must be an int")
    return IDENTITIES.get(template_id)


def shippable_placements() -> tuple[Bg0011Placement, ...]:
    """The 51 placements of the 56 that resolve to a real identity."""
    out = []
    for index, template_id, mm_instance, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(template_id)
        if identity is None:
            continue
        out.append(Bg0011Placement(
            index, template_id, mm_instance, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The 5 that are dropped, each with the id and the reason.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH ones and WHY.
    """
    out = []
    for index, template_id, _mm, x, y, z in _PLACEMENT_ROWS:
        if template_id in IDENTITIES:
            continue
        cline_row_id, leader, reason = UNRESOLVED.get(
            template_id, (0, 0, "set not in CLINE 11"))
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
    if len(_RESOLVED_ROWS) != 26:
        raise Bg0011IdentityError(
            "expected 26 resolved sets, found %d" % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg0011IdentityError("duplicate Mob-Set number in the table")
    if len(UNRESOLVED) != 5:
        raise Bg0011IdentityError(
            "expected 5 unresolved sets, found %d" % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg0011IdentityError("a set is both resolved and unresolved")
    if len(_PLACEMENT_ROWS) != 56:
        raise Bg0011IdentityError(
            "expected 56 placements, found %d" % len(_PLACEMENT_ROWS))
    # Control 1: every Mob-Set number this scene's placements use is either
    # resolved or named as unresolved, and the two sets together are EXACTLY
    # this scene's used keys - a placement keyed by a number this table has
    # never heard of means the placement file and the crosswalk came from
    # different extractions.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if scene_sets != table_sets:
        raise Bg0011IdentityError(
            "placement Mob-Set numbers and this table's keys disagree: %r"
            % sorted(scene_sets ^ table_sets))
    if len(table_sets) != 31:
        raise Bg0011IdentityError(
            "expected 31 distinct Mob-Set numbers, found %d" % len(table_sets))
    if not no_set_number_is_shipped_as_identity():
        raise Bg0011IdentityError(
            "a row ships its own Mob-Set number as an identity")
    for row in _RESOLVED_ROWS:
        (template_id, cline_row_id, n_id, outfit, name, title, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1:
            raise Bg0011IdentityError(
                "set %d carries no CLINE row locator" % template_id)
        if ";" in outfit:
            raise Bg0011IdentityError(
                "set %d ships a multi-variant outfit string" % template_id)
        if not outfit or not outfit.isascii():
            raise Bg0011IdentityError(
                "set %d has an empty or non-ASCII outfit" % template_id)
        if not name.isascii() or not title.isascii():
            raise Bg0011IdentityError(
                "set %d has a non-ASCII name or title" % template_id)
        if not name:
            raise Bg0011IdentityError(
                "set %d has no display name" % template_id)
        if max_hp < 1 or level < 1:
            raise Bg0011IdentityError("set %d has a bad level/HP" % template_id)
    if len(shippable_placements()) != 51:
        raise Bg0011IdentityError("expected 51 shippable placements")
    if len(unshippable_placements()) != 5:
        raise Bg0011IdentityError("expected 5 unshippable placements")
    ids = [p.actor_identity for p in shippable_placements()]
    if len(ids) != len(set(ids)):
        raise Bg0011IdentityError("actor identities collide within this table")


_self_check()
