"""Who each Bg0010 placement actually IS - Deep Sea Temple floor 1's real cast.

LANE-A (WORLD).  ``COO-DECISION 2026-08-30T14:41+07:00`` (pf_bridge
``notes_to_chief/20260830_1441_COO-DECISION-scene4-slave-market-first-door.md``)
approved building the ten still-shut doors surveyed in round ``12lyda`` in
native-placement-count order, and named the sequencing rule "no need to ask
again per door" so long as nothing irreversible is found.  Scene 4 (116
placements) went first; this is the second, scene 10 (Bg0010, "Deep Sea
Temple floor 1", 100 placements, the next entry in round ``12lyda``'s own
table).  This module is the identity half, the same split every earlier
crosswalk used; ``world_population_bg0010`` is the census half.

THE CROSSWALK, RE-DERIVED HERE RATHER THAN TAKEN FROM A CITATION.
``SCENE_NAME[s_MODLE_ID=Bg0010].n_CLINE_TYPE`` was read directly off the
bridge clone this round:

    SCENE_NAME[s_MODLE_ID=Bg0010].n_ID          = 10
    SCENE_NAME[s_MODLE_ID=Bg0010].n_CLINE_TYPE  = 10   (a real value, direct)
    SCENE_NAME[s_MODLE_ID=Bg0010].n_SCENE_LV    = 92
    CLINE[(10, <Mob-Set number>)].n_LEADER_BK1  = the real MOBS.n_ID
    MOBS[n_ID].s_OUTFIT                         = the avatar the client loads
    MOBS_TIP[n_ID].s_NAME / s_TITLE             = the label under the actor
    STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX      = max HP (the one derived col)

Same direct-selector shape ``world_bg0004_identity`` and
``world_bg0015_identity`` both ship (one of RE-128's 19 direct CLINE types,
not one of its 240 instance scenes).

WHAT IS ESTABLISHED HERE AND WHAT IS NOT, STATED THE SAME WAY THE OTHER TWO
CROSSWALK MODULES STATE IT.

    ESTABLISHED - THE TABLE.  This scene's cast is drawn from CLINE type 10's
    leader column.  CONTROL 1 below is exact: this scene's placements use
    exactly 40 distinct Mob-Set numbers (1-35, 101-105) and every one of the
    40 has a row in CLINE type 10.

    NOT ESTABLISHED - THE PAIRING.  Which leader belongs to which Mob-Set
    number.  No human has stood in this scene (``status:
    never_sent_to_any_client_by_this_project`` in
    ``scenarios/world_scene_registry_001.json``), so every name below is a
    table inference, the bottom of the evidence order COO set on
    2026-08-28T21:30, until an attended round looks.

CONTROL 1 - EXACT SUBSET, MEASURED.  The 100 placements resolve to 40
distinct Mob-Set numbers (99 of them - see the UNRESOLVED-EXTRACTION
paragraph below for the 100th); CLINE type 10 has 41 keys (1-41); the 40 this
scene uses are all present.  The one key CLINE type 10 carries that this
scene never touches (41) is not examined here (out of scope: nothing in this
scene's placement file names it).

CONTROL 2 - NOT REBUILT HERE, CITED, AND IT REPRODUCES CLEANLY THIS TIME.
``world_bg0015_identity.SCENE_LEVEL_CONTROL['Bg0010']`` carries this scene's
row: ``(10, 92, 99.0, 20.0)`` - CLINE type 10, declared level 92,
CLINE-reading median 99.0.  Re-measuring the CLINE-reading median THIS round,
over the 94 shippable placements (per-placement, not per-distinct-set, the
same counting bg0004's own module used), gives **99.0** - an EXACT match,
unlike bg0004's one-point gap.  Still read as WEAK evidence for the PAIRING,
same caveat that module's docstring already gives (the reading is monotone
in level across the whole project, so an exact median match is expected of
ANY permutation of the same 35 rows, not specific to this one) - recorded
because it is a cleaner number than bg0004's, not because it changes the
evidence tier.

CONTROL 3 - NO SELF-MAPPING, WEAK, SAME CAVEAT AS THE OTHER TWO SCENES.  0 of
the 35 resolved rows have ``mobs_n_id == template_id``: keys are <= 105 and
leaders are >= 644 here, so this control could not fire for any pairing of
this table either.  A shape check, not evidence.

FIVE OF THE 40 SETS DO NOT RESOLVE (COST FIVE PLACEMENTS, ONE EACH), AND A
SIXTH PLACEMENT IS DROPPED FOR A DIFFERENT, NEW REASON.

* Sets 101-105 -> leaders 10053-10057.  Every one HAS a ``CONSTDATA MOBS``
  row but its ``s_OUTFIT`` column is empty - the identical "path-finding
  helper, not a creature" shape bg0004's sets 101-106 (leaders
  10014-10019) and bg0015's 101-108 block (leaders 10063-10070) both carry.
  Dropped rather than sent with an invented preset, same
  [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION] carried over from
  both sibling crosswalks.
* PLACEMENT INDEX 50 (free text "Mob_Set_99 01") IS A NEW SHAPE, NOT SEEN IN
  EITHER SIBLING SCENE: the machine-parsed ``template_ids`` column itself
  reads the literal string ``UNRESOLVED`` for this one row - not a Mob-Set
  number that fails to resolve in CLINE, but a row the extraction step could
  not assign a Mob-Set number to at all.  The free-text ``name``/
  ``set_names`` columns claim ``Mob_Set_99``, but bg0004's own docstring
  already established that this module trusts the machine-parsed column over
  the free-text one when the two disagree (bg0004 placements 82/83), and
  "the machine-parsed column refuses to say" is not the same fact as "the
  free-text column says 99" - inventing set 99 for this row would be
  building a row CHARTER-02 does not license (nothing in this project's
  CLINE type 10 table is confirmed to be Mob-Set 99 for this scene; 99 is
  outside the 1-41 key range CLINE type 10 even carries).  This row is
  DROPPED, its own way, distinct from the five empty-outfit sets, and given
  its own sentinel ``template_id = -1`` in ``_PLACEMENT_ROWS`` so a reader
  can tell the two failure modes apart at a glance.  Grep of every other
  mined scene's placements file this round found exactly one sibling with
  the same literal (``Bg5004``, untouched by this project) - so this is not
  unique to this scene, but it is unique to THIS crosswalk pass.

TWELVE SETS LIST TWO AVATAR TEMPLATES SEPARATED BY ';'.  Same rule and the
same open question as bg0004's nine and Bg0015's nine: ship the FIRST
variant, keep the whole string in ``MULTI_VARIANT_OUTFITS``, and
``_self_check`` refuses at import if a raw ';' ever reaches the shipped
column.  [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION].  Leaders 657,
658, 659, 663, 664, 665, 666, 667, 670, 672, 838 and 841 (12 of the 35
resolved sets, accounting for 59 of the 94 shippable placements - well over
half the roster, the same "not a corner case" shape bg0004's own docstring
records).

NO NAME-VS-TEMPLATE DISAGREEMENT, NO EXTRA SPAWN TRIPLE, NO MULTI-TEMPLATE
ROW.  Unlike bg0004, every placement's free-text ``name`` column agrees with
its machine-parsed ``template_ids`` column (checked for all 99 rows that
carry a real template id), no row carries ``extra_triple_count > 0``, and no
row lists more than one template id.  This scene's placement file is cleaner
than bg0004's on every axis except the one new UNRESOLVED-extraction row
above.

NO EMPTY-NAME / INVISIBLE-MARKER SHAPE THIS TIME.  Every one of the 35
resolved leaders has a non-empty ``MOBS_TIP.s_NAME`` (bg0004's leader 917
"INVISIBLE, no name" exception does not recur here - checked, not assumed).

HEADING.  Same measurement bg0004's own ``_entry`` made for its own scene:
the extra f32 triple this TSV format carries (columns ``f32_3``/``f32_4``/
``f32_5``) is a round-number range across unrelated rows (0-0-0 once,
otherwise combinations of 500/800/1000/1500/2000/3000), the shape of a
radius, not a rotation - so the census half reuses ``world_population.
HEADINGS`` on the placement index, same as every other scene.

LANDING GEOMETRY, A REAL CAUTION FLAG, NOT A BLOCKER FOR THIS ROUND.
``scenarios/world_scene_registry_001.json``'s own
``table_row_differences.the_two_interiors`` block (round ``ga91m5``,
pf-adversary finding D4) names scene 10 as ONE OF THE TWO SCENES an attended
round should check FIRST if a landing goes wrong: its marker point sits
5174.7 units from the nearest of this scene's 100 native placements and is
OUTSIDE the placement extents, with a placement z floor of -4532.9 against a
marker z of 465.  This module does not touch that finding or the registry
row - it is recorded here because a future round that flips
``login_entry_allowed`` for scene 10 must read that block first, the same
"a wrong identity a player can walk up to and read is recoverable" ordering
principle bg0004's own docstring used for its faction question.  Building
this composer is safe regardless (the door stays shut - see below); STANDING
a player on this scene's marker point is a separate, later decision.

PROVENANCE.  Every row below was generated from these five committed
artifacts and nothing else, re-derived rather than copied from a sibling
module's citation of the same four shared tables (identical digests to
``world_bg0004_identity``'s own citation for the four scene-independent
tables, since they are the same committed files; only the placements file
digest is new):

    gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv
    gamedata/tables/CONSTDATA_TH__CLINE.tsv
    gamedata/tables/CONSTDATA_TH__MOBS.tsv
    gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv
    gamedata/tables/CONSTDATA_TH__STANDARD_MOB.tsv
    gamedata/scene/Bg0010/Bg0010.placements.tsv

THE JOIN, EXACTLY, SO IT CAN BE MECHANISED LATER (this round did it by
script against committed TSVs read directly, not by hand - the tables are
large enough that hand transcription would itself be an error source; the
script's own output is what appears below, unedited except for formatting):

    keys   = {r.n_CREATURE_TYPE: r for r in CLINE if r.n_CLINE_TYPE == 10}
    for each Mob-Set number k this scene's placements use (40 of them):
        leader = keys[k].n_LEADER_BK1
        drop k (UNRESOLVED) if leader == 0, or MOBS has no row for it,
            or that row's s_OUTFIT is empty
        else row = (k, keys[k].n_ID, leader, s_OUTFIT.split(';')[0],
                    MOBS_TIP.s_NAME or '', MOBS_TIP.s_TITLE or '',
                    MOBS.n_LEVEL_MIN, MOBS.n_RANK,
                    STANDARD_MOB[n_LEVEL_MIN].n_HPMAX, MOBS.n_MOB_USAGE)
    placements = every row of Bg0010.placements.tsv as
        (index, template_ids, running instance count per template_ids,
         x, y, z) - except index 50, whose template_ids column is itself the
         literal "UNRESOLVED"; that row is emitted with sentinel
         template_id -1 rather than skipped, so PLACEMENT_COUNT still counts
         every native row the scene registry cites (100).

WHAT THIS MODULE DOES NOT CLAIM.

* Not that any of these 94 actors has been SEEN.  No human has been in this
  scene in this project's history (registry ``status:
  never_sent_to_any_client_by_this_project``, and ``login_entry_allowed`` is
  still ``false``).  The client-observable layer for this scene is empty;
  there is no ticket number for it yet because nothing is wired to a login
  path this round.
* Not that this census (built by ``world_population_bg0010``, a sibling
  module, not this one) is what raises these actors on a real server.
* Not leader+crew.  Like both sibling crosswalks this implements
  ``n_LEADER_BK1`` only.  Measured for this scene: 0 of CLINE type 10's 41
  rows carry any ``n_CREW`` value at all, so there is no pet/crew group this
  reading silently drops.
* Not wired.  Registering "bg0010_roster" in
  ``world_scene_travel.CENSUS_SOURCES`` and
  ``world_population_handoff.ROSTER_COMPOSERS`` is deliberately left for a
  later round, matching bg0004's own precedent (identity+census land several
  rounds before wiring, wiring lands several rounds before the door opens).
  Until wiring lands, a player sees exactly what they saw yesterday.
"""
from __future__ import annotations

from dataclasses import dataclass


# Convention marker: shippable, no scenario flag - matching the two sibling
# crosswalk modules' own convention.  Nothing in this tree branches on it and
# no chief-owned file imports this module yet.
production_allowed = True
test_only = False

SCENE_N_ID = 10
SCENE_MODEL_ID = "BG0010"
SCENE_CLINE_TYPE = 10
# SCENE_NAME.n_SCENE_LV for this scene.  world_bg0015_identity's own control 2
# table already carries this exact triple (92, 99.0, 20.0); see this module's
# docstring for why the 99.0 DOES reproduce from THIS module's own count,
# unlike bg0004's one-point gap.
SCENE_DECLARED_LEVEL = 92

SOURCE_SHA256 = {
    "gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv":
        "e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b",
    "gamedata/tables/CONSTDATA_TH__CLINE.tsv":
        "aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40",
    "gamedata/tables/CONSTDATA_TH__MOBS.tsv":
        "3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b",
    "gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv":
        "e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f",
    "gamedata/tables/CONSTDATA_TH__STANDARD_MOB.tsv":
        "4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925",
    "gamedata/scene/Bg0010/Bg0010.placements.tsv":
        "71011ddc6cc9af824a1c44124022ce5ae04ba41bf8745c55aed6a9274f2187cd",
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  Costs five of the 100
# placements (one each - none of these five sets recurs in this scene).
UNRESOLVED = {
    101: (2835, 10053, "MOBS row carries no s_OUTFIT avatar template"),
    102: (2836, 10054, "MOBS row carries no s_OUTFIT avatar template"),
    103: (2837, 10055, "MOBS row carries no s_OUTFIT avatar template"),
    104: (2838, 10056, "MOBS row carries no s_OUTFIT avatar template"),
    105: (2839, 10057, "MOBS row carries no s_OUTFIT avatar template"),
}

# The sentinel reason for placement index 50, which the extraction step
# itself could not assign a Mob-Set number to (template_ids literal
# "UNRESOLVED") - a distinct failure mode from the five above, given its own
# entry so unshippable_placements() can name it precisely rather than fall
# back to a generic message.
EXTRACTION_UNRESOLVED_REASON = (
    "extraction produced no Mob-Set number for this placement (template_ids "
    "column literal UNRESOLVED); free text claims Mob_Set_99 but that is not "
    "authoritative and 99 is outside CLINE type 10's own 1-41 key range, so "
    "it is not shipped as a guess")

# MOBS rows in this scene that list SEVERAL avatar templates separated by
# ';', as leader n_ID -> the whole string.  The table below ships the FIRST
# variant; ``_self_check`` refuses if a ';' ever reaches the shipped column.
# [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION]
MULTI_VARIANT_OUTFITS = {
    657: "M026_000_000_SP1;M026_000_000_SP2",
    658: "M026_000_002_SP1;M026_000_002_SP2",
    659: "M026_000_001_SP1;M026_000_001_SP2",
    663: "M008_000_000_SP1;M008_000_000_SP2",
    664: "M024_000_000_SP1;M024_000_000_SP2",
    665: "M024_000_001_SP1;M024_000_001_SP2",
    666: "M024_001_001_SP1;M024_001_001_SP2",
    667: "M024_001_000_SP1;M024_001_000_SP2",
    670: "M025_000_001_N;M025_000_001_SP1",
    672: "M016_000_000_SP1;M016_000_000_SP2",
    838: "M071_000_003_SP2;M071_000_003_SP1",
    841: "M071_000_003_SP2;M071_000_003_SP1",
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
# 35 rows: every Mob-Set number this scene's placements use that CLINE type
# 10 resolves to a body.
_RESOLVED_ROWS = (
    (1, 2800, 644, "M077_000_000_N", "Angelina", "Flashback", 104, 0, 221803, 2),
    (2, 2801, 645, "M077_000_000_N", "Angelina", "Refugees Savior", 104, 0, 221803, 2),
    (3, 2802, 646, "M026_000_002_SP2", "Concentration Camp Guard", "", 104, 0, 221803, 2),
    (4, 2803, 647, "M026_000_002_SP3", "Concentration Camp Guard", "", 104, 0, 221803, 2),
    (5, 2804, 648, "P_MALE_015_000_SLAVE", "Angry Refugees", "", 104, 0, 221803, 2),
    (6, 2805, 649, "P_MALE_015_000_RICK", "Thirsty Refugees", "", 104, 0, 221803, 2),
    (7, 2806, 650, "M026_000_001_SP3", "Skeleton Corps Officer", "", 104, 0, 221803, 2),
    (8, 2807, 651, "M026_001_000_BOSS", "Dyken", "Lovelorn Captain", 104, 0, 221803, 2),
    (9, 2808, 652, "M076_000_000_N", "Sea Phantom", "Brave Enemies", 104, 0, 221803, 2),
    (10, 2809, 653, "M071_000_003_SP2", "Panic Woman", "", 104, 0, 221803, 2),
    (11, 2810, 654, "M071_000_003_SP1", "Fleeing Woman", "", 104, 0, 221803, 2),
    (12, 2811, 655, "M026_000_000_SP3", "santino", "Skull Deputy chief", 104, 0, 221803, 2),
    (13, 2812, 656, "M019_000_001_SP3", "Seabed Crusader", "Fighting", 104, 0, 221803, 2),
    (14, 2813, 657, "M026_000_000_SP1", "Skeleton Sseaman", "", 99, 1, 192488, 1),
    (15, 2814, 658, "M026_000_002_SP1", "Skeleton Mate", "", 99, 1, 192488, 1),
    (16, 2815, 659, "M026_000_001_SP1", "Skeleton Chiliarch", "", 99, 1, 192488, 1),
    (17, 2816, 660, "M026_000_001_SP3", "Skeleton Commander Lebiya", "", 99, 1, 192488, 1),
    (18, 2817, 661, "M000_001_000_SP2", "Exotic Demon Wolf", "", 99, 1, 192488, 1),
    (19, 2818, 662, "M000_001_000_SP3", "Abyss Demon Wolf", "", 99, 1, 192488, 1),
    (20, 2819, 663, "M008_000_000_SP1", "Shipwreck Souls", "", 99, 1, 192488, 1),
    (21, 2820, 664, "M024_000_000_SP1", "Penguin Corporal", "", 99, 1, 192488, 1),
    (22, 2821, 665, "M024_000_001_SP1", "Penguin Sergeant", "", 99, 1, 192488, 1),
    (23, 2822, 666, "M024_001_001_SP1", "Penguin Staff Sergeant", "", 99, 1, 192488, 1),
    (24, 2823, 667, "M024_001_000_SP1", "Penguin Master Sergeant", "", 99, 1, 192488, 1),
    (25, 2824, 668, "M018_000_000_N", "Navy Two Tripods", "", 99, 1, 192488, 1),
    (26, 2825, 670, "M025_000_001_N", "Deep Sea Slug", "", 99, 1, 192488, 1),
    (27, 2826, 671, "M020_000_001_SP1", "Crusty Bone Fish", "", 99, 1, 192488, 1),
    (28, 2827, 672, "M016_000_000_SP1", "Sewer Iron Man", "", 99, 1, 192488, 1),
    (29, 2828, 673, "M021_000_000_SP3", "Seabed Wanderer", "", 99, 1, 192488, 1),
    (30, 2829, 835, "M055_000_000_N", "Columbus", "Ocean Transport Station", 104, 0, 221803, 2),
    (31, 2830, 836, "P_MALE_015_000_SLAVE", "Concentration camp prisoner", "", 104, 0, 221803, 2),
    (32, 2831, 837, "P_MALE_015_000_RICK", "Concentration camp prisoner", "", 104, 0, 221803, 2),
    (33, 2832, 838, "M071_000_003_SP2", "Concentration camp prisoner", "", 104, 0, 221803, 2),
    (34, 2833, 839, "M026_000_002_SP2", "Coma Guard", "", 104, 0, 221803, 7),
    (35, 2834, 841, "M071_000_003_SP2", "Concentration camp prisoner", "", 104, 0, 221803, 2),
)

IDENTITIES = {row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS}


@dataclass(frozen=True)
class Bg0010Placement:
    """One Bg0010 placement resolved to a real, named, bodied actor - or, for
    the one sentinel row (index 50), not resolved at all."""

    placement_index: int
    template_id: int
    mm_instance: int
    x: float
    y: float
    z: float
    identity: SceneIdentity | None

    @property
    def actor_identity(self) -> int:
        # The same formula bg0004 and bg0015 both use.  Never sent in the
        # same generation as another scene's census - every builder refuses
        # any scene id but its own - so sharing the numeric space is a
        # collision in the abstract only.  No lane-B module for this scene
        # exists yet (checked this round: 0 files under src/ mention
        # Bg0010/BG0010 as a census composer outside this pair).
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
# file in file order.  Index 50 carries sentinel Mob-Set number -1 - see
# EXTRACTION_UNRESOLVED_REASON and the module docstring's own section on it.
_PLACEMENT_ROWS = (
    (0, 1, 1, 7961.14794921875, 20027.435546875, 732.382080078125),
    (1, 2, 1, 20924.8671875, 5482.58203125, 728.382080078125),
    (2, 3, 1, 16087.3154296875, 5019.08984375, 509.92041015625),
    (3, 4, 1, 15203.296875, 9562.748046875, 514.92041015625),
    (4, 5, 1, 9707.630859375, 23375.740234375, 517.9204711914062),
    (5, 6, 1, 5817.39501953125, 23161.873046875, 561.4495239257812),
    (6, 7, 1, 24366.7421875, 17446.68359375, 515.92041015625),
    (7, 8, 1, 7942.2802734375, -8762.44921875, -1672.92578125),
    (8, 9, 1, -17063.203125, -7668.892578125, -4435.88818359375),
    (9, 10, 1, -19239.90234375, 136.97360229492188, -4360.55810546875),
    (10, 11, 1, -14700.9609375, -9712.2734375, -4462.2978515625),
    (11, 12, 1, 1523.779296875, -8517.6171875, -3730.8623046875),
    (12, 14, 1, 14550.7333984375, 16120.9111328125, 416.18359375),
    (13, 14, 2, 17882.58203125, 16692.767578125, 534.125),
    (14, 14, 3, 16932.0625, 13482.8388671875, 416.18359375),
    (15, 14, 4, 14377.6083984375, 13394.912109375, 418.18310546875),
    (16, 15, 1, 15602.8896484375, 14879.7265625, 465.3215026855469),
    (17, 15, 2, 10240.7294921875, 5416.0205078125, 510.1252136230469),
    (18, 15, 3, 10258.4677734375, 9277.4189453125, 530.12548828125),
    (19, 15, 4, 5630.9150390625, 9268.9189453125, 525.1254272460938),
    (20, 15, 5, 5728.021484375, 5434.22265625, 529.1251831054688),
    (21, 16, 1, 7953.8505859375, 6531.642578125, 362.9472961425781),
    (22, 14, 5, 2742.559814453125, 13016.4765625, 431.7737121582031),
    (23, 14, 6, -720.622314453125, 14052.529296875, 405.6430969238281),
    (24, 19, 1, -646.5667724609375, 10672.0400390625, 507.20849609375),
    (25, 20, 1, 8275.9111328125, 15546.6953125, 523.4390258789062),
    (26, 20, 2, 10268.03125, 12841.3466796875, 558.0534057617188),
    (27, 20, 3, 10268.03125, 16788.482421875, 552.0534057617188),
    (28, 20, 4, 5750.70263671875, 16901.759765625, 531.05322265625),
    (29, 20, 5, 5667.21923828125, 12994.3037109375, 555.052978515625),
    (30, 15, 6, 11896.7978515625, 1915.464111328125, 424.9296875),
    (31, 17, 1, 18040.51171875, -1351.5966796875, 518.0941772460938),
    (32, 18, 1, 18162.3203125, -390.3909912109375, 517.921875),
    (33, 15, 7, -2528.582275390625, -12328.7890625, -4440.9443359375),
    (34, 22, 1, -9875.5517578125, -6187.1806640625, -4330.4912109375),
    (35, 22, 2, -9934.0517578125, -10935.7587890625, -4334.49169921875),
    (36, 22, 3, -5617.5537109375, -6185.755859375, -4305.5576171875),
    (37, 22, 4, -5908.32421875, -10796.1240234375, -4328.49169921875),
    (38, 23, 1, -8725.7265625, -7841.02685546875, -4527.87255859375),
    (39, 25, 1, -16490.47265625, -16926.20703125, -4474.47314453125),
    (40, 22, 5, -17591.04296875, -14004.525390625, -4329.4912109375),
    (41, 22, 6, -13245.666015625, -13996.025390625, -4330.4912109375),
    (42, 22, 7, -17649.54296875, -18753.103515625, -4327.49169921875),
    (43, 22, 8, -13623.814453125, -18566.46875, -4337.49169921875),
    (44, 26, 1, -13489.8505859375, -21541.134765625, -4430.94091796875),
    (45, 26, 2, -13178.0625, -24858.8671875, -4417.26953125),
    (46, 29, 1, -15906.484375, -24835.26171875, -4423.37060546875),
    (47, 27, 1, -13489.8505859375, -3254.76416015625, -4435.94091796875),
    (48, 27, 2, -17285.3046875, 37.502201080322266, -4256.94091796875),
    (49, 28, 1, -24085.01953125, -16175.65625, -4327.71337890625),
    (50, -1, 1, 15645.7294921875, 18058.12109375, 1953.42138671875),
    (51, 13, 1, -20795.9375, -15970.025390625, -4126.1669921875),
    (52, 21, 1, -5644.22802734375, -18627.6328125, -4323.54833984375),
    (53, 21, 2, -5530.17529296875, -13917.7578125, -4304.4912109375),
    (54, 21, 3, -9934.0517578125, -18674.8359375, -4293.49169921875),
    (55, 21, 4, -9875.5517578125, -13926.2578125, -4309.4912109375),
    (56, 24, 1, -8832.4833984375, -15466.091796875, -4511.87158203125),
    (57, 31, 1, 15082.0888671875, 8210.5009765625, 358.6061096191406),
    (58, 32, 1, 16376.5625, 7213.14111328125, 344.6059875488281),
    (59, 33, 1, 15330.560546875, 7207.00634765625, 342.6059875488281),
    (60, 33, 2, 15524.2490234375, 6495.572265625, 341.6059875488281),
    (61, 33, 3, 15026.1201171875, 6174.107421875, 343.6059875488281),
    (62, 34, 1, 16380.5146484375, 6221.923828125, 331.6059875488281),
    (63, 34, 2, 16475.333984375, 8056.11669921875, 343.6059875488281),
    (64, 30, 1, 16030.8662109375, 20302.4296875, 752.3197021484375),
    (65, 35, 1, 7910.4150390625, 23677.025390625, 519.9210815429688),
    (66, 101, 1, 13435.72265625, 6239.2109375, 518.9210815429688),
    (67, 102, 1, 8798.0537109375, 15959.3173828125, 340.8764953613281),
    (68, 103, 1, -19560.853515625, 76.51290130615234, -4363.5576171875),
    (69, 104, 1, -12821.970703125, -5991.14453125, -4358.55810546875),
    (70, 105, 1, -10486.048828125, -13468.08203125, -4343.5576171875),
    (71, 16, 2, 8044.5615234375, 4865.66845703125, 523.9207763671875),
    (72, 16, 3, 10304.6044921875, 5422.2255859375, 527.9204711914062),
    (73, 16, 4, 10342.916015625, 9472.8740234375, 539.9210815429688),
    (74, 16, 5, 10276.2607421875, 7198.0576171875, 543.9204711914062),
    (75, 16, 6, 5472.5263671875, 9175.609375, 517.9210815429688),
    (76, 16, 7, 5733.9013671875, 7122.73193359375, 548.9204711914062),
    (77, 16, 8, 5650.6142578125, 4974.7041015625, 530.9204711914062),
    (78, 23, 2, -8798.65234375, -9322.2646484375, -4527.87255859375),
    (79, 23, 3, -6981.89453125, -7779.48974609375, -4506.87255859375),
    (80, 23, 4, -7048.8330078125, -9354.0751953125, -4529.87255859375),
    (81, 23, 5, -7821.82470703125, -10655.9599609375, -4330.55712890625),
    (82, 23, 6, -7776.2626953125, -6400.486328125, -4335.5576171875),
    (83, 24, 2, -8720.4267578125, -16975.53515625, -4520.87255859375),
    (84, 24, 3, -7015.24267578125, -15666.9609375, -4532.8720703125),
    (85, 24, 4, -7346.48193359375, -16823.279296875, -4300.0),
    (86, 24, 5, -7888.31884765625, -14062.919921875, -4337.5576171875),
    (87, 24, 6, -10207.59375, -16436.646484375, -4345.55712890625),
    (88, 24, 7, -7890.82080078125, -18581.55078125, -4344.55810546875),
    (89, 24, 8, -5597.80078125, -16357.5224609375, -4328.5576171875),
    (90, 18, 2, 18132.693359375, -2144.323486328125, 536.9204711914062),
    (91, 18, 3, 17020.2109375, -1360.697509765625, 528.9210815429688),
    (92, 18, 4, 14737.1171875, -574.6121826171875, 517.92041015625),
    (93, 18, 5, 13602.69921875, -1800.505126953125, 515.9216918945312),
    (94, 18, 6, 12802.80859375, -492.20208740234375, 516.9208984375),
    (95, 18, 7, 15415.568359375, 1949.245849609375, 744.3201293945312),
    (96, 19, 2, -1746.46630859375, 12049.8876953125, 419.6430969238281),
    (97, 19, 3, -273.4700927734375, 12937.83203125, 433.6429138183594),
    (98, 19, 4, -1594.5361328125, 14055.3583984375, 433.6430969238281),
    (99, 19, 5, -262.4346008300781, 15402.984375, 442.6430969238281),
)

PLACEMENT_COUNT = len(_PLACEMENT_ROWS)


class Bg0010IdentityError(ValueError):
    """A refusal from this module, always with a reason in the message."""


def identity_for(template_id: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    ``None`` is the five sets in ``UNRESOLVED``, the sentinel ``-1`` (the
    extraction-unresolved placement), and nothing else: this function never
    substitutes, and never falls back to the Mob-Set number that ``GT-078``
    proved wrong on the owner's screen.
    """
    if type(template_id) is not int or type(template_id) is bool:
        raise Bg0010IdentityError("template id must be an int")
    return IDENTITIES.get(template_id)


def shippable_placements() -> tuple[Bg0010Placement, ...]:
    """The 94 placements of the 100 that resolve to a real identity."""
    out = []
    for index, template_id, mm_instance, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(template_id)
        if identity is None:
            continue
        out.append(Bg0010Placement(
            index, template_id, mm_instance, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The six that are dropped, each with the id and the reason.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH six and WHY - and, for this scene,
    to see the two different reasons told apart (five empty-outfit sets, one
    extraction-unresolved row).
    """
    out = []
    for index, template_id, _mm, x, y, z in _PLACEMENT_ROWS:
        if template_id in IDENTITIES:
            continue
        if template_id == -1:
            cline_row_id, leader, reason = 0, 0, EXTRACTION_UNRESOLVED_REASON
        else:
            cline_row_id, leader, reason = UNRESOLVED.get(
                template_id, (0, 0, "set not in CLINE 10"))
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
    this scene's keys are all <= 105 and its resolved leaders are all >= 644,
    so this could not fail for any pairing of this table - it only catches a
    future regeneration that falls back to the Mob-Set number itself, which
    is the specific regression GT-078 was."""
    return all(row[0] != row[2] for row in _RESOLVED_ROWS)


def _self_check() -> None:
    """Refuse at import if this table has drifted out of the shape the
    module docstring claims.  Fail-closed: a bad table must not reach a
    census builder at all, and an ImportError names the file."""
    if len(_RESOLVED_ROWS) != 35:
        raise Bg0010IdentityError(
            "expected 35 resolved sets, found %d" % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg0010IdentityError("duplicate Mob-Set number in the table")
    if len(UNRESOLVED) != 5:
        raise Bg0010IdentityError(
            "expected 5 unresolved sets, found %d" % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg0010IdentityError("a set is both resolved and unresolved")
    if len(_PLACEMENT_ROWS) != 100:
        raise Bg0010IdentityError(
            "expected 100 placements, found %d" % len(_PLACEMENT_ROWS))
    # Control 1: every Mob-Set number this scene's placements use (other than
    # the sentinel -1) is either resolved or named as unresolved - a
    # placement keyed by a number this table has never heard of means the
    # placement file and the crosswalk came from different extractions.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS if row[1] != -1}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if scene_sets != table_sets:
        raise Bg0010IdentityError(
            "placement Mob-Set numbers and this table's keys disagree: %r"
            % sorted(scene_sets ^ table_sets))
    sentinel_rows = [row for row in _PLACEMENT_ROWS if row[1] == -1]
    if len(sentinel_rows) != 1 or sentinel_rows[0][0] != 50:
        raise Bg0010IdentityError(
            "expected exactly one sentinel row, at placement index 50")
    if not no_set_number_is_shipped_as_identity():
        raise Bg0010IdentityError(
            "a row ships its own Mob-Set number as an identity")
    for row in _RESOLVED_ROWS:
        (template_id, cline_row_id, n_id, outfit, name, title, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1:
            raise Bg0010IdentityError(
                "set %d carries no CLINE row locator" % template_id)
        if ";" in outfit:
            raise Bg0010IdentityError(
                "set %d ships a multi-variant outfit string" % template_id)
        if not outfit or not outfit.isascii():
            raise Bg0010IdentityError(
                "set %d has an empty or non-ASCII outfit" % template_id)
        if not name.isascii() or not title.isascii():
            raise Bg0010IdentityError(
                "set %d has a non-ASCII name or title" % template_id)
        if not name:
            raise Bg0010IdentityError(
                "set %d has no display name (no INVISIBLE-marker exception "
                "exists in this scene, unlike bg0004)" % template_id)
        if max_hp < 1 or level < 1:
            raise Bg0010IdentityError("set %d has a bad level/HP" % template_id)
    if len(shippable_placements()) != 94:
        raise Bg0010IdentityError("expected 94 shippable placements")
    if len(unshippable_placements()) != 6:
        raise Bg0010IdentityError("expected 6 unshippable placements")
    ids = [p.actor_identity for p in shippable_placements()]
    if len(ids) != len(set(ids)):
        raise Bg0010IdentityError("actor identities collide within this table")


_self_check()
