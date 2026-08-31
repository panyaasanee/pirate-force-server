"""Who each Bg4001 placement actually IS - Navy Training Camp's real cast.

LANE-A (WORLD).  ``COO-DECISION 2026-08-30T14:41+07:00`` (pf_bridge
``notes_to_chief/20260830_1441_COO-DECISION-scene4-slave-market-first-door.md``)
approved building the ten still-shut doors surveyed in round ``12lyda`` in
native-placement-count order ("no need to ask again per door").  Scenes 4,
5, 10, 14, 6, 8, 3, 7, 9 and 11 are open; this is the TENTH AND LAST door
in the original sequence: scene 130 (Bg4001, "Navy Training Camp", 42
placements).  This module is the identity half, the same split every
earlier crosswalk used; ``world_population_bg4001`` is the census half.

NOT AN ELEVATED-RISK ROW.  Unlike scenes 10 and 11, this row does NOT carry
``table_row_differences.the_two_interiors`` -- measured, not assumed:
``n_CANGLIDE`` is 1 and ``n_LIMIT_HEIGHT`` is 0 for this scene, not the
(0, 0) pair that flag names.  The registry's own
``table_row_differences.marker_geometry_measured_not_enforced`` block
(already present on this row from round ``ga91m5``) records the marker
point 1018.201 units from the nearest of this scene's 42 native
placements, OUTSIDE the placement extents -- one of the six of the ten
doors that landed outside rather than inside (3, 4, 5, 6, 10, 130), the
same reason this row carries no ``ground`` block (a .npc file is not
terrain -- see that key's own ``why_the_ten_carry_no_ground_block`` prose).

THE CROSSWALK, RE-DERIVED HERE RATHER THAN TAKEN FROM A CITATION.
``SCENE_NAME[s_MODLE_ID=Bg4001].n_CLINE_TYPE`` was read directly off the
bridge clone this round:

    SCENE_NAME[s_MODLE_ID=Bg4001].n_ID          = 130
    SCENE_NAME[s_MODLE_ID=Bg4001].n_CLINE_TYPE  = 4001   (a real value, direct)
    SCENE_NAME[s_MODLE_ID=Bg4001].n_SCENE_LV    = 0
    CLINE[(4001, <Mob-Set number>)].n_LEADER_BK1 = the real MOBS.n_ID
    MOBS[n_ID].s_OUTFIT                          = the avatar the client loads
    MOBS_TIP[n_ID].s_NAME / s_TITLE              = the label under the actor
    STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX       = max HP (the one derived col)

Same direct-selector shape ``world_bg0003_identity`` through
``world_bg0011_identity`` all ship (one of RE-128's 19 direct CLINE types,
not one of its 240 instance scenes).

DECLARED LEVEL IS ZERO, RECORDED RATHER THAN SILENTLY NORMALIZED.  Unlike
every other one of the ten doors (whose ``n_SCENE_LV`` ranged 25-105), this
scene's own ``SCENE_NAME`` row reads ``n_SCENE_LV = 0`` -- the same value
scene 1 (home) carries, even though this is not a home scene and its own
CLINE-resolved cast is real (levels 10 and 150, see below).  This module
does not correct or reinterpret that zero; it is quoted as
``SCENE_DECLARED_LEVEL`` exactly as the source table has it, and CONTROL 2
below explains why no comparison against it is drawn.

WHAT IS ESTABLISHED HERE AND WHAT IS NOT, STATED THE SAME WAY THE OTHER
NINE CROSSWALK MODULES STATE IT.

    ESTABLISHED - THE TABLE.  This scene's cast is drawn from CLINE type
    4001's leader column.  CONTROL 1 below is a SUBSET, not an exact
    match: this scene's placements use exactly 18 distinct Mob-Set numbers
    (1-14, 16, 17, 19, 102), all 18 of them present in CLINE type 4001's
    own 22-row key range (1-19, 101-103) - the same 'placement file
    touches only PART of its own CLINE type' shape bg0004's 55-of-61,
    bg0009's 44-of-48, bg0010's 40-of-41 and bg0011's 31-of-32 crosswalks
    carry.  FOUR keys exist in CLINE type 4001 that no placement in this
    scene uses (15, 18, 101, 103) - checked rather than assumed to be
    empty: 15's own leader (896) is real and non-zero (the SAME leader
    key 14 already resolves to -- two Mob-Set numbers pointing at one
    MOBS row, harmless here because 15 has no placement to reach it
    through); 18's leader (823) is real and non-zero too; 101's leader
    (10001) is real and non-zero; 103's own leader is the literal value
    ``0`` -- the "leader is literally 0" shape bg0007's own set 111
    carried, but here it costs nothing because no placement in this scene
    ever names Mob-Set 103.

    NOT ESTABLISHED - THE PAIRING.  Which leader belongs to which Mob-Set
    number.  No human has stood in this scene (registry ``status:
    never_sent_to_any_client_by_this_project``), so every name below is a
    table inference, the bottom of the evidence order COO set on
    2026-08-28T21:30, until an attended round looks.

DISCREPANCY, MEASURED AND NOT SILENTLY RECONCILED.  The registry's own
``native_definition_count`` for scene 130 reads 20.  This round's own
count of CLINE type 4001's rows (grouped by ``n_CREATURE_TYPE``, checked
for duplicates - there are none) is 22, WIDER than 20 by the two untouched
keys named above whose leaders are real (15 and 18; 101 and 103 are the
other two untouched keys, also real-vs-zero as described above, so all
FOUR of this scene's untouched keys are accounted for, not just two).  18
is also EXACTLY the count of distinct Mob-Set numbers this scene's own 42
placements use (CONTROL 1) - so, like scene 9's and scene 11's own
agreement and unlike bg0003's, bg0004's, bg0007's and bg0008's own
off-by-one pattern, scene 130's registry field and this round's own
placement-side count DISAGREE BY TWO rather than by one or not at all -
the first time this lane has measured a gap wider than one.  What they
still do not agree with is CLINE type 4001's own total row count (22),
which this round did not expect them to.

CONTROL 1 - EXACT SUBSET, MEASURED.  The 42 placements resolve to 18
distinct Mob-Set numbers; CLINE type 4001 has 22 keys (1-19, 101-103);
the 18 the scene uses are exactly {1-14} union {16, 17, 19, 102} - every
one present, none missing - and the four keys the scene never touches
(15, 18, 101, 103) are NOT "no creature" (see the discrepancy paragraph
above): three carry a real, non-zero leader that would have resolved to a
shippable body anyway (15 and 18 both do; 101 does too, unmeasured beyond
"real and non-zero" since no placement ever reaches it), and the fourth
(103) carries a literal-zero leader.

CONTROL 2 - NOT REBUILT HERE.  No ``world_bg0015_identity.
SCENE_LEVEL_CONTROL`` row exists for Bg4001 (checked: that table only
cites scenes it was built against at the time, and this scene was never
one of them) - the same absence bg0003's, bg0006's and bg0008's own
Control 2 recorded, not silently skipped.  Given the declared level itself
reads 0 (see above), this scene would not have been a useful addition to
that table's own median-vs-declared comparison even if a row existed -
noted rather than acted on, since owning that shared table is not this
module's job.

CONTROL 3 - NO SELF-MAPPING, WEAK, SAME CAVEAT AS THE OTHER TEN SCENES.  0
of the 17 resolved rows have ``mobs_n_id == template_id`` (measured, not
assumed): none.  A shape check, not evidence.

ONE OF THE 18 SETS DOES NOT RESOLVE (COST 1 PLACEMENT), THE SAME FAMILIAR
FAILURE SHAPE EVERY SIBLING SCENE'S OWN 101+ BLOCK CARRIES.

* Set 102 -> leader 10080.  HAS a ``CONSTDATA MOBS`` row but its
  ``s_OUTFIT`` column is empty - the identical 'path-finding helper, not a
  creature' shape every sibling scene's own 101+ block carries (bg0003: 9,
  bg0004: 6, bg0005: 4, bg0006: 9, bg0007: 10, bg0008: 5, bg0009: 5,
  bg0010: 5, bg0011: 5; this scene: 1, the narrowest of the eleven).
  MEASURED, NOT JUST THE OUTFIT: leader 10080's own ``MOBS_TIP.s_NAME`` and
  ``s_TITLE`` are ALSO empty, unlike every earlier scene's 101+ drops
  (which at least had a name even without an avatar) - checked rather than
  assumed, since an empty outfit alone was the only thing prior modules'
  ``UNRESOLVED`` reason string named.
* NO "MOBS has no row at all" set this scene needed - unlike bg0009's set
  1, every Mob-Set number this scene's placements use resolves to a real
  ``CONSTDATA MOBS`` row.
* NO "leader is literally 0" set this scene needed AMONG PLACEMENTS USED -
  unlike bg0007's set 111, every Mob-Set number this scene's placements
  use that CLINE type 4001 resolves to a leader resolves to a NON-ZERO one
  (checked, not assumed; the one literal-zero leader in this scene's own
  CLINE type, key 103, has no placement pointing at it - see CONTROL 1).
* NO CJK/non-cp874 name among the 17 SHIPPED rows this scene needed -
  every one of this scene's 17 resolved ``MOBS_TIP`` rows and
  ``MOBS.s_OUTFIT`` values is plain ASCII, checked directly (not assumed
  from the absence of a failure).

TWO SETS LIST THREE VARIANT AVATAR TEMPLATES SEPARATED BY ';', A NARROWER
FAN-OUT THAN bg0003's NINE-VARIANT OUTLIER BUT A WIDER ONE THAN EVERY
OTHER SIBLING'S OWN TWO-VARIANT ROWS.  Same rule and the same open
question as every earlier crosswalk module's own multi-variant sets: ship
the FIRST variant, keep the whole string in ``MULTI_VARIANT_OUTFITS``, and
``_self_check`` refuses at import if a raw ';' ever reaches the shipped
column.  [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION].  Leaders
[894, 898] (Mob-Set numbers 12 and 16, 2 of the 17 resolved sets), both
THREE-variant rows (not the two-variant shape every sibling's own
multi-variant sets carried until now), covering 16 of the 41 shippable
placements (measured this round, not estimated: set 12 places 8, set 16
places 8 - both fully resolved, so every one of their own placements
ships).

NO NAME-VS-TEMPLATE DISAGREEMENT, NO EXTRA SPAWN TRIPLE, NO MULTI-TEMPLATE
ROW, NO EXTRACTION-UNRESOLVED SENTINEL.  Checked directly against this
scene's own placement file: no row carries ``extra_triple_count > 0``, no
row lists more than one template id, and no row's ``template_ids`` column
reads the literal ``UNRESOLVED``.  Same clean shape every sibling scene's
own crosswalk carries on these axes.

NO CREW.  Measured for this scene: 0 of CLINE type 4001's 22 rows carry
any ``n_CREW`` value at all (checked ``n_CREW1`` through ``n_CREW6``), the
same "no pet/crew group silently dropped" shape every sibling scene
carries.

HEADING.  Same measurement every sibling scene's own ``_entry`` made for
its own scene: the extra f32 triple this TSV format carries (columns
``f32_3``/``f32_4``/``f32_5``) is a small round-number set across
unrelated rows here too (2/3/2 distinct values respectively) - the shape
of a radius, not a rotation - so the census half reuses
``world_population.HEADINGS`` on the placement index, same as every other
scene.

LEVEL SPREAD WITHIN ONE SCENE, MEASURED AND NAMED.  Fifteen of the 17
resolved sets carry ``MOBS.n_LEVEL_MIN`` 10 (``STANDARD_MOB`` HP 421); the
remaining two (Mob-Set 11, leader 893, "Lightning Enchanted Generator";
Mob-Set 12, leader 894, "Rookie Recruit") carry level 150 (HP 616267) -
roughly 1,464 times the other fifteen's own HP.  Not reconciled or
softened here: this crosswalk ships exactly what the table says for each
Mob-Set number, and a scene mixing a level-10 trainee roster with two
level-150 bodies is what the source data has, not a transcription choice
this module made.

LANDING GEOMETRY.  ``scenarios/world_scene_registry_001.json``'s own
``table_row_differences.marker_geometry_measured_not_enforced`` block for
this scene (n_id 130) records the marker point 1018.201 units from the
nearest of this scene's 42 native placements, OUTSIDE the placement
extents (unlike bg0011's own inside-extents marker) - cross-checked
directly against this module's own ``_PLACEMENT_ROWS``.  This row does
NOT carry ``table_row_differences.the_two_interiors`` (see the
NOT-AN-ELEVATED-RISK-ROW paragraph above).  This row carries no ``ground``
block, same as five of its nine siblings among the ten doors, and for the
same documented reason (a .npc file is not terrain).

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
    gamedata/scene/Bg4001/Bg4001.placements.tsv

THE JOIN, EXACTLY, SO IT CAN BE MECHANISED LATER (done by a throwaway
script against committed TSVs read directly this round, not by hand - the
tables are large enough that hand transcription would itself be an error
source; the script's own output is what appears below, unedited except
for formatting):

    keys   = {r.n_CREATURE_TYPE: r for r in CLINE if r.n_CLINE_TYPE == 4001}
    for each Mob-Set number k this scene's placements use (18 of them):
        leader = keys[k].n_LEADER_BK1
        drop k if MOBS has no row for it, or that row's s_OUTFIT is empty,
            or MOBS_TIP.s_NAME/s_TITLE/s_OUTFIT is not cp874-representable
        else row = (k, keys[k].n_ID, leader, s_OUTFIT.split(';')[0],
                    MOBS_TIP.s_NAME or '', MOBS_TIP.s_TITLE or '',
                    MOBS.n_LEVEL_MIN, MOBS.n_RANK,
                    STANDARD_MOB[n_LEVEL_MIN].n_HPMAX, MOBS.n_MOB_USAGE)
    placements = every row of Bg4001.placements.tsv as
        (index, template_ids, running instance count per template_ids,
         x, y, z), in file order - no sentinel rows this scene (see above).

WHAT THIS MODULE DOES NOT CLAIM.

* Not that any of these 17 actors has been SEEN.  No human has been in
  this scene in this project's history (registry ``status:
  never_sent_to_any_client_by_this_project``, and ``login_entry_allowed``
  is still ``false`` as of this module's own construction round).  The
  client-observable layer for this scene is empty until an attended round
  looks.
* Not that this census (built by ``world_population_bg4001``, a sibling
  module, not this one) is what raises these actors on a real server.
* Not leader+crew.  Like every sibling crosswalk this implements
  ``n_LEADER_BK1`` only.  Measured for this scene: 0 of CLINE type 4001's
  22 rows carry any ``n_CREW`` value at all, so there is no pet/crew group
  this reading silently drops.
* Not wired at import time in this module - wiring
  (``CENSUS_SOURCES``/``ROSTER_COMPOSERS``/``lane_hooks`` console reader)
  and the door-open (``login_entry_allowed``) are both done by THIS SAME
  ROUND's other files, following the compressed build+wire+open precedent
  rounds ``l03cgh``/``fx0007``/``p4wire``/``p7wm17``/``78zayw``/``ir0lpw``/
  ``68mm02`` set for scenes 5, 6, 8, 3, 7, 9 and 11 (the generic contract
  test ``tests/test_lane_a_scene_census.py::ComposerContractTests``
  already assumes every scene this lane composes for is also open at
  login).
"""
from __future__ import annotations

from dataclasses import dataclass


# Convention marker: shippable, no scenario flag - matching the ten
# sibling crosswalk modules' own convention.
production_allowed = True
test_only = False

SCENE_N_ID = 130
SCENE_MODEL_ID = "Bg4001"
SCENE_CLINE_TYPE = 4001
# SCENE_NAME.n_SCENE_LV for this scene - see module docstring "DECLARED
# LEVEL IS ZERO" for why this is quoted rather than corrected.
SCENE_DECLARED_LEVEL = 0

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
    "gamedata/scene/Bg4001/Bg4001.placements.tsv":
        '4c023ba18fe3940002277e1d88656272222a89a433b731f442ad7f8da9088600',
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  Costs 1 of the 42
# placements (see module docstring - the narrowest of the eleven scenes
# this lane has crosswalked, all sharing the same failure shape).
UNRESOLVED = {
    102: (60370, 10080, 'MOBS row carries no s_OUTFIT avatar template'),
}

# MOBS rows in this scene that list SEVERAL avatar templates separated by
# ';', as leader n_ID -> the whole string.  The table below ships the FIRST
# variant; ``_self_check`` refuses if a ';' ever reaches the shipped
# column.  [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION]
MULTI_VARIANT_OUTFITS = {
    894: 'P_FEMALE_001_000_N;P_FEMALE_002_000_MIX;P_FEMALE_004_000_N',
    898: 'P_MALE_004_000_N;P_MALE_002_000_SP1;P_MALE_001_000_ROLANCE',
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
# 17 rows: every Mob-Set number this scene's placements use that CLINE type
# 4001 resolves to a shippable body (cp874-representable name/title/outfit).
_RESOLVED_ROWS = (
    (1, 60350, 883, 'P_MALE_002_000_ROLE', 'Basil', 'Navy Transport Officer', 10, 0, 421, 2),
    (2, 60351, 884, 'M073_000_000_SP3', 'Hande', 'Support Troops', 10, 0, 421, 2),
    (3, 60352, 885, 'M073_000_000_SP3', 'Hande', 'Support Troops', 10, 0, 421, 2),
    (4, 60353, 886, 'P_MALE_014_000_ARNO', 'Arnaud', 'Devil Trainers', 10, 0, 421, 2),
    (5, 60354, 887, 'M073_000_000_SP3', 'Hande', 'Support Troops', 10, 0, 421, 2),
    (6, 60355, 888, 'M073_000_000_SP3', 'Hande', 'Support Troops', 10, 0, 421, 2),
    (7, 60356, 889, 'P_MALE_002_002_REO', 'Liou', 'Army Medical', 10, 0, 421, 2),
    (8, 60357, 890, 'P_MALE_014_000_ARNO', 'Arnaud', 'Devil Trainers', 10, 0, 421, 2),
    (9, 60358, 891, 'P_MALE_014_000_ARNO', 'Arnaud', 'Devil Trainers', 10, 0, 421, 2),
    (10, 60359, 892, 'P_MALE_014_000_ARNO', 'Arnaud', 'Devil Trainers', 10, 0, 421, 2),
    (11, 60360, 893, 'M014_000_001_N', 'Lightning Enchanted Generator', '', 150, 0, 616267, 7),
    (12, 60361, 894, 'P_FEMALE_001_000_N', 'Rookie Recruit', '', 150, 0, 616267, 7),
    (13, 60362, 895, 'M005_000_004_SP1', 'Deer', '', 10, 0, 421, 2),
    (14, 60363, 896, 'M000_000_000_SP1', 'Alienation Wolf', '', 10, 0, 421, 1),
    (16, 60365, 898, 'P_MALE_004_000_N', 'Passers Soldier', '', 10, 0, 421, 2),
    (17, 60366, 900, 'M005_000_004_SP3', 'Kindly Deer', '', 10, 0, 421, 2),
    (19, 60368, 906, 'M073_000_000_SP3', 'Hande', 'Support Troops', 10, 0, 421, 2),
)

IDENTITIES = {row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS}


@dataclass(frozen=True)
class Bg4001Placement:
    """One Bg4001 placement resolved to a real, named, bodied actor."""

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
    (0, 1, 1, -23803.794921875, 14123.4130859375, -982.019287109375),
    (1, 2, 1, -20764.619140625, 17681.666015625, -885.89501953125),
    (2, 4, 1, -13344.662109375, 11845.86328125, 2241.848388671875),
    (3, 5, 1, -9935.7939453125, 9493.71875, 2837.06396484375),
    (4, 6, 1, -7536.64892578125, 876.5825805664062, 3757.840087890625),
    (5, 7, 1, -19537.208984375, -16160.2998046875, 4341.35009765625),
    (6, 8, 1, -14675.91015625, -18475.712890625, 4423.41357421875),
    (7, 9, 1, -13588.6123046875, -10093.986328125, 7141.330078125),
    (8, 3, 1, -14518.810546875, 6162.79345703125, 1609.58154296875),
    (9, 16, 1, -12982.6142578125, 15306.6513671875, 2310.848388671875),
    (10, 16, 2, -14439.69921875, 14867.0498046875, 2310.848388671875),
    (11, 16, 3, -13137.189453125, 12549.984375, 2310.848388671875),
    (12, 16, 4, -14015.0546875, 13732.369140625, 2310.848388671875),
    (13, 11, 1, -8012.7587890625, 6338.94287109375, 3317.52197265625),
    (14, 11, 2, -6223.8779296875, 5561.10498046875, 3317.52197265625),
    (15, 11, 3, -7274.603515625, 3591.712890625, 3317.52197265625),
    (16, 12, 1, -7053.44580078125, 4646.0283203125, 3402.5390625),
    (17, 12, 2, -7814.056640625, 4672.88232421875, 3406.025146484375),
    (18, 12, 3, -6455.1455078125, 4939.74072265625, 3410.686279296875),
    (19, 12, 4, -6479.4521484375, 4099.5556640625, 3410.490234375),
    (20, 12, 5, -6050.66796875, 6105.42724609375, 3423.612548828125),
    (21, 12, 6, -8144.9970703125, 5721.767578125, 3435.3759765625),
    (22, 12, 7, -6757.697265625, 6129.8916015625, 3408.23828125),
    (23, 12, 8, -7965.46435546875, 6792.71923828125, 3401.27001953125),
    (24, 13, 1, -9418.6123046875, -870.673583984375, 3720.2841796875),
    (25, 13, 2, -9663.7275390625, -2213.500244140625, 3794.6142578125),
    (26, 13, 3, -13078.5234375, -3224.676025390625, 4363.5205078125),
    (27, 13, 4, -12445.484375, -3906.581787109375, 4086.925537109375),
    (28, 13, 5, -13979.6630859375, -5611.267578125, 4139.9013671875),
    (29, 14, 1, -19275.58203125, -12343.111328125, 4155.8544921875),
    (30, 14, 2, -18859.388671875, -15231.244140625, 4120.0810546875),
    (31, 14, 3, -17011.783203125, -16375.1640625, 4357.53564453125),
    (32, 14, 4, -19988.935546875, -16923.826171875, 4384.74072265625),
    (33, 14, 5, -21687.916015625, -15738.7177734375, 4388.8876953125),
    (34, 16, 5, -19890.2265625, 19517.6328125, -797.669921875),
    (35, 16, 6, -21937.4609375, 17929.466796875, -941.7855224609375),
    (36, 16, 7, -20795.810546875, 19463.11328125, -859.4329833984375),
    (37, 16, 8, -19642.140625, 18786.611328125, -794.5410766601562),
    (38, 10, 1, -17546.974609375, -2509.396728515625, 7050.6328125),
    (39, 17, 1, -11289.5908203125, -2301.62841796875, 3928.263916015625),
    (40, 19, 1, -19865.66015625, 17626.849609375, -736.9285888671875),
    (41, 102, 1, -16971.671875, -13856.140625, 4714.0888671875),
)

PLACEMENT_COUNT = len(_PLACEMENT_ROWS)


class Bg4001IdentityError(ValueError):
    """A refusal from this module, always with a reason in the message."""


def identity_for(template_id: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    ``None`` is exactly the 1 set in ``UNRESOLVED`` and nothing else: this
    function never substitutes, and never falls back to the Mob-Set number
    that ``GT-078`` proved wrong on the owner's screen.
    """
    if type(template_id) is not int or type(template_id) is bool:
        raise Bg4001IdentityError("template id must be an int")
    return IDENTITIES.get(template_id)


def shippable_placements() -> tuple[Bg4001Placement, ...]:
    """The 41 placements of the 42 that resolve to a real identity."""
    out = []
    for index, template_id, mm_instance, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(template_id)
        if identity is None:
            continue
        out.append(Bg4001Placement(
            index, template_id, mm_instance, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The 1 that is dropped, with the id and the reason.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH one and WHY.
    """
    out = []
    for index, template_id, _mm, x, y, z in _PLACEMENT_ROWS:
        if template_id in IDENTITIES:
            continue
        cline_row_id, leader, reason = UNRESOLVED.get(
            template_id, (0, 0, "set not in CLINE 4001"))
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
    if len(_RESOLVED_ROWS) != 17:
        raise Bg4001IdentityError(
            "expected 17 resolved sets, found %d" % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg4001IdentityError("duplicate Mob-Set number in the table")
    if len(UNRESOLVED) != 1:
        raise Bg4001IdentityError(
            "expected 1 unresolved set, found %d" % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg4001IdentityError("a set is both resolved and unresolved")
    if len(_PLACEMENT_ROWS) != 42:
        raise Bg4001IdentityError(
            "expected 42 placements, found %d" % len(_PLACEMENT_ROWS))
    # Control 1: every Mob-Set number this scene's placements use is either
    # resolved or named as unresolved, and the two sets together are EXACTLY
    # this scene's used keys - a placement keyed by a number this table has
    # never heard of means the placement file and the crosswalk came from
    # different extractions.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if scene_sets != table_sets:
        raise Bg4001IdentityError(
            "placement Mob-Set numbers and this table's keys disagree: %r"
            % sorted(scene_sets ^ table_sets))
    if len(table_sets) != 18:
        raise Bg4001IdentityError(
            "expected 18 distinct Mob-Set numbers, found %d" % len(table_sets))
    if not no_set_number_is_shipped_as_identity():
        raise Bg4001IdentityError(
            "a row ships its own Mob-Set number as an identity")
    for row in _RESOLVED_ROWS:
        (template_id, cline_row_id, n_id, outfit, name, title, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1:
            raise Bg4001IdentityError(
                "set %d carries no CLINE row locator" % template_id)
        if ";" in outfit:
            raise Bg4001IdentityError(
                "set %d ships a multi-variant outfit string" % template_id)
        if not outfit or not outfit.isascii():
            raise Bg4001IdentityError(
                "set %d has an empty or non-ASCII outfit" % template_id)
        if not name.isascii() or not title.isascii():
            raise Bg4001IdentityError(
                "set %d has a non-ASCII name or title" % template_id)
        if not name:
            raise Bg4001IdentityError(
                "set %d has no display name" % template_id)
        if max_hp < 1 or level < 1:
            raise Bg4001IdentityError("set %d has a bad level/HP" % template_id)
    if len(shippable_placements()) != 41:
        raise Bg4001IdentityError("expected 41 shippable placements")
    if len(unshippable_placements()) != 1:
        raise Bg4001IdentityError("expected 1 unshippable placement")
    ids = [p.actor_identity for p in shippable_placements()]
    if len(ids) != len(set(ids)):
        raise Bg4001IdentityError("actor identities collide within this table")


_self_check()
