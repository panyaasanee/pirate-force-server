"""Who each Bg0005 placement actually IS - Evil Port's real cast.

LANE-A (WORLD).  ``COO-DECISION 2026-08-30T14:41+07:00`` (pf_bridge
``notes_to_chief/20260830_1441_COO-DECISION-scene4-slave-market-first-door.md``)
approved building the ten still-shut doors surveyed in round ``12lyda`` in
native-placement-count order, and named the sequencing rule "no need to ask
again per door" so long as nothing irreversible is found.  Scene 4 (116
placements) went first, scene 10 (100 placements) second; this is the third,
scene 5 (Bg0005, "Evil Port", 92 placements, the next entry in round
``12lyda``'s own table).  This module is the identity half, the same split
every earlier crosswalk used; ``world_population_bg0005`` is the census half.

THE CROSSWALK, RE-DERIVED HERE RATHER THAN TAKEN FROM A CITATION.
``SCENE_NAME[s_MODLE_ID=BG0005].n_CLINE_TYPE`` was read directly off the
bridge clone this round:

    SCENE_NAME[s_MODLE_ID=BG0005].n_ID          = 5
    SCENE_NAME[s_MODLE_ID=BG0005].n_CLINE_TYPE  = 5    (a real value, direct)
    SCENE_NAME[s_MODLE_ID=BG0005].n_SCENE_LV    = 60
    CLINE[(5, <Mob-Set number>)].n_LEADER_BK1   = the real MOBS.n_ID
    MOBS[n_ID].s_OUTFIT                         = the avatar the client loads
    MOBS_TIP[n_ID].s_NAME / s_TITLE             = the label under the actor
    STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX      = max HP (the one derived col)

Same direct-selector shape ``world_bg0004_identity``, ``world_bg0010_identity``
and ``world_bg0015_identity`` all ship (one of RE-128's 19 direct CLINE
types, not one of its 240 instance scenes).

WHAT IS ESTABLISHED HERE AND WHAT IS NOT, STATED THE SAME WAY THE OTHER THREE
CROSSWALK MODULES STATE IT.

    ESTABLISHED - THE TABLE.  This scene's cast is drawn from CLINE type 5's
    leader column.  CONTROL 1 below is exact: this scene's placements use
    exactly 64 distinct Mob-Set numbers (1-59, 101-105) and every one of the
    64 has a row in CLINE type 5 - which is CLINE type 5's ENTIRE key range
    (64 rows total), unlike bg0004 (61 of CLINE 4's rows) and bg0010 (40 of
    CLINE 10's 41 rows): this scene's placement file touches every key its
    own CLINE type owns.

    NOT ESTABLISHED - THE PAIRING.  Which leader belongs to which Mob-Set
    number.  No human has stood in this scene (registry ``status:
    never_sent_to_any_client_by_this_project``), so every name below is a
    table inference, the bottom of the evidence order COO set on
    2026-08-28T21:30, until an attended round looks.

CONTROL 1 - EXACT SUBSET, MEASURED.  The 92 placements resolve to 64 distinct
Mob-Set numbers; CLINE type 5 has exactly 64 keys (1-59, 101-105); the two
sets are identical (no gap either direction).

CONTROL 2 - NOT REBUILT HERE, CITED, AND IT DOES NOT REPRODUCE EXACTLY THIS
TIME - STATED RATHER THAN SILENCED.  ``world_bg0015_identity.
SCENE_LEVEL_CONTROL['BG0005']`` carries this scene's row: ``(5, 60, 68.0,
35.0)`` - CLINE type 5, declared level 60, CLINE-reading median 68.0,
set-number median 35.0.  Re-measuring BOTH medians this round, over the 87
shippable placements (per-placement, not per-distinct-set, the same counting
bg0004's and bg0010's own modules used): the CLINE-reading median is **70**,
not 68 (a 2-point gap, wider than bg0004's 1-point gap and unlike bg0010's
exact match); the set-number median does NOT agree across the three
countings the way the CLINE-reading median does (checked three ways:
per-distinct-resolved-set and per-CLINE-row-with-a-MOBS-entry both give
**31**, not 35, but per-placement -- the same repeat-weighted counting used
for the CLINE-reading median above -- gives **38** instead; pf-adversary
caught the mismatch, corrected here rather than silently picking the
convenient number). Still read as WEAK evidence for the
PAIRING, same caveat every sibling module's docstring already gives (the
reading is monotone in level across the whole project, so an exact median
match is expected of ANY permutation of the same rows, not specific to this
one) - the gap does not change the evidence tier and is not treated as a
defect in this module's own table; it is recorded because the earlier
citation's own number does not reproduce from this round's independent count,
and a reader comparing the two tables deserves the real numbers rather than a
silently repeated citation.  [LANE-A ASSUMPTION - AWAITING COO CONFIRMATION
IF THIS MATTERS] that this gap is measurement-drift (different counting
convention in the round that first built ``SCENE_LEVEL_CONTROL``) rather than
a table-drift signal; opened to lane C as ``RE-170``.

RE-170 FOLLOW-UP (round ``rdhel6`` 2026-09-01): tried to close RE-170's own
pass criterion 1 ("identify the counting method behind the original 68.0 /
35.0 pair via git blame or a round file") and could NOT - this repo's git
history is not one continuous line back to the round that first wrote
``SCENE_LEVEL_CONTROL``.  ``git blame`` on that line stops at
``73c20fb`` (2026-08-31), and ``git rev-list --max-parents=0 --all`` shows
EIGHT separate root (parentless) commits in this repo, meaning the history
was assembled from disconnected snapshots at least that many times; nothing
before those boundaries is walkable from here.  A citation search of every
``pf_bridge/rounds/A_*`` file that mentions BG0005 or a number matching
35/68 (``uajlve``, ``02k3w5``, ``6p22bu``) found none that document the
counting method either - the ``35.0``/``68.0`` pair predates every round
record this project still has.  So criterion 1 is unanswerable from this
project's own sources, not merely unanswered; criterion 3 of RE-170's own
"ห้าม" section (no git-blame citation -> no edit) therefore still applies
and the numbers above are UNCHANGED by this follow-up.  Recorded rather than
silenced, same as the gap itself.

CONTROL 3 - NO SELF-MAPPING, WEAK, SAME CAVEAT AS THE OTHER THREE SCENES.  0
of the 59 resolved rows have ``mobs_n_id == template_id``: keys are <= 105
and leaders are >= 105 with only one exact adjacency (key 2 -> leader 105,
key 3 -> leader 106, ... - leaders trail their keys by 103 for the first 47
keys, then diverge), so no row ships its own Mob-Set number as its identity.
A shape check, not evidence.

FIVE OF THE 64 SETS DO NOT RESOLVE (COST FIVE PLACEMENTS, ONE EACH), TWO
DIFFERENT REASONS.

* Set 1 -> leader 104.  CLINE type 5's own row for this key carries a real,
  non-zero ``n_LEADER_BK1`` (104), but ``CONSTDATA MOBS`` has NO ROW at all
  for ``n_ID=104`` - a new failure mode neither bg0004 nor bg0010 needed
  (both of their unresolved sets had a MOBS row with an empty ``s_OUTFIT``;
  this one has no MOBS row to check an outfit on).  Dropped rather than
  guessed at, with its own distinct reason string so a reader can tell the
  two failure modes apart.
* Sets 101-104 -> leaders 10020-10023.  Every one HAS a ``CONSTDATA MOBS``
  row but its ``s_OUTFIT`` column is empty - the identical "path-finding
  helper, not a creature" shape bg0004's sets 101-106 (leaders 10014-10019)
  and bg0010's sets 101-105 (leaders 10053-10057) both carry.  Dropped rather
  than sent with an invented preset, same
  [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION] carried over from all
  three sibling crosswalks.  NOTE the asymmetry with bg0010: that scene had
  FIVE such empty-outfit "path-finder" sets (101-105); this scene has FOUR
  (101-104) - set 105 in THIS scene's CLINE table (leader 10024) was never
  examined because this scene's placements never use Mob-Set 105 (checked:
  105 is not in this scene's 64 used keys - the crosswalk only looks at keys
  the placement file actually names).

TEN SETS LIST TWO AVATAR TEMPLATES SEPARATED BY ';'.  Same rule and the same
open question as bg0004's nine, Bg0010's twelve and Bg0015's nine: ship the
FIRST variant, keep the whole string in ``MULTI_VARIANT_OUTFITS``, and
``_self_check`` refuses at import if a raw ';' ever reaches the shipped
column.  [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION].  Leaders 138,
139, 140, 141, 142, 143, 145, 147, 149 and 7044 (10 of the 59 resolved sets),
but UNLIKE bg0010's roughly-even spread, this scene's ten multi-variant sets
are placed VERY UNEVENLY - one of them (set 44, leader 147) alone accounts
for 9 placements, and the ten sets together cover 38 of the 87 shippable
placements (measured this round, not estimated: set instance counts of 3, 3,
2, 4, 2, 4, 6, 9, 4, 1 for sets 35, 36, 37, 38, 39, 40, 42, 44, 46, 105
respectively) - well over a third of the roster, the same "not a corner case"
shape every sibling module's own docstring records, just distributed
differently.

NO NAME-VS-TEMPLATE DISAGREEMENT, NO EXTRA SPAWN TRIPLE, NO MULTI-TEMPLATE
ROW, NO EXTRACTION-UNRESOLVED SENTINEL.  Unlike bg0004 (two mismatches) and
bg0010 (one sentinel row), every one of this scene's 92 placements has a
free-text ``name`` column that agrees with its machine-parsed
``template_ids`` column (``MOBSET_NN`` matches the numeric ``template_ids``
value for all 92 rows, checked), no row carries ``extra_triple_count > 0``,
no row lists more than one template id, and no row's ``template_ids`` column
reads the literal ``UNRESOLVED``.  This scene's placement file is the
cleanest of the three built so far on every axis this project checks.

NO EMPTY-NAME / INVISIBLE-MARKER SHAPE THIS TIME.  Every one of the 59
resolved leaders has a non-empty ``MOBS_TIP.s_NAME`` (bg0004's leader 917
"INVISIBLE, no name" exception does not recur here - checked, not assumed).

HEADING.  Same measurement bg0004's, bg0010's and bg0015's own ``_entry``
each made for their own scene: the extra f32 triple this TSV format carries
(columns ``f32_3``/``f32_4``/``f32_5``) is a round-number range across
unrelated rows here too (twelve distinct combinations, all multiples of 100,
e.g. 0/500/800, 500/1500/2500, 800/2000/3000) - the shape of a radius, not a
rotation - so the census half reuses ``world_population.HEADINGS`` on the
placement index, same as every other scene.

LANDING GEOMETRY.  ``scenarios/world_scene_registry_001.json``'s own
``table_row_differences.marker_geometry_measured_not_enforced`` block for
this scene (n_id 5) records the marker point 564.3 units from the nearest of
this scene's 92 native placements, outside the placement extents - the same
"recorded, not enforced" shape 6 of the 10 doors carry (NOT the elevated
``the_two_interiors`` flag scene 10 alone carries).  This module does not
touch that finding or the registry row - it is recorded here because a
future round that flips ``login_entry_allowed`` for scene 5 must read that
block first, the same ordering principle bg0004's and bg0010's own docstrings
used.  Building this composer is safe regardless (the door stays shut, and
this round does not wire the census into dispatch either - see below);
standing a player on this scene's marker point is a separate, later decision.

PROVENANCE.  Every row below was generated from these five committed
artifacts and nothing else, re-derived rather than copied from a sibling
module's citation of the same four shared tables (identical digests to
``world_bg0004_identity``'s and ``world_bg0010_identity``'s own citations for
the four scene-independent tables, since they are the same committed files;
only the placements file digest is new):

    gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv
    gamedata/tables/CONSTDATA_TH__CLINE.tsv
    gamedata/tables/CONSTDATA_TH__MOBS.tsv
    gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv
    gamedata/tables/CONSTDATA_TH__STANDARD_MOB.tsv
    gamedata/scene/bg0005/bg0005.placements.tsv

THE JOIN, EXACTLY, SO IT CAN BE MECHANISED LATER (this round did it by
script against committed TSVs read directly, not by hand - the tables are
large enough that hand transcription would itself be an error source; the
script's own output is what appears below, unedited except for formatting):

    keys   = {r.n_CREATURE_TYPE: r for r in CLINE if r.n_CLINE_TYPE == 5}
    for each Mob-Set number k this scene's placements use (64 of them):
        leader = keys[k].n_LEADER_BK1
        drop k if leader == 0, or MOBS has no row for it,
            or that row's s_OUTFIT is empty
        else row = (k, keys[k].n_ID, leader, s_OUTFIT.split(';')[0],
                    MOBS_TIP.s_NAME or '', MOBS_TIP.s_TITLE or '',
                    MOBS.n_LEVEL_MIN, MOBS.n_RANK,
                    STANDARD_MOB[n_LEVEL_MIN].n_HPMAX, MOBS.n_MOB_USAGE)
    placements = every row of bg0005.placements.tsv as
        (index, template_ids, running instance count per template_ids,
         x, y, z), in file order - no sentinel rows this scene (see above).

WHAT THIS MODULE DOES NOT CLAIM.

* Not that any of these 87 actors has been SEEN.  No human has been in this
  scene in this project's history (registry ``status:
  never_sent_to_any_client_by_this_project``, and ``login_entry_allowed`` is
  still ``false``).  The client-observable layer for this scene is empty;
  there is no ticket number for it yet because nothing is wired to a login
  path this round.
* Not that this census (built by ``world_population_bg0005``, a sibling
  module, not this one) is what raises these actors on a real server.
* Not leader+crew.  Like every sibling crosswalk this implements
  ``n_LEADER_BK1`` only.  Measured for this scene: 0 of CLINE type 5's 64
  rows carry any ``n_CREW`` value at all, so there is no pet/crew group this
  reading silently drops.
* Not wired.  Registering "bg0005_roster" in
  ``world_scene_travel.CENSUS_SOURCES`` and
  ``world_population_handoff.ROSTER_COMPOSERS`` is deliberately left for a
  later round, matching bg0004's and bg0010's own precedent (identity+census
  land several rounds before wiring, wiring lands several rounds before the
  door opens).  Until wiring lands, a player sees exactly what they saw
  yesterday.
"""
from __future__ import annotations

from dataclasses import dataclass


# Convention marker: shippable, no scenario flag - matching the three sibling
# crosswalk modules' own convention.  Nothing in this tree branches on it and
# no chief-owned file imports this module yet.
production_allowed = True
test_only = False

SCENE_N_ID = 5
SCENE_MODEL_ID = "BG0005"
SCENE_CLINE_TYPE = 5
# SCENE_NAME.n_SCENE_LV for this scene.  world_bg0015_identity's own control 2
# table carries the declared level (60) correctly; see this module's
# docstring for why the two MEDIAN readings do NOT reproduce from this
# module's own count (68->70; 35->31 per-distinct-set/per-CLINE-row but
# 35->38 per-placement -- the two countings disagree, see docstring),
# unlike bg0010's exact match.
SCENE_DECLARED_LEVEL = 60

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
    "gamedata/scene/bg0005/bg0005.placements.tsv":
        "b69ee8f159d5242c393872101326bbddaa67d9f8fb7514f38e039e138308c0c5",
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  Costs five of the 92
# placements (one each - none of these five sets recurs in this scene).
UNRESOLVED = {
    1: (1800, 104, "MOBS has no row for this leader"),
    101: (1858, 10020, "MOBS row carries no s_OUTFIT avatar template"),
    102: (1859, 10021, "MOBS row carries no s_OUTFIT avatar template"),
    103: (1860, 10022, "MOBS row carries no s_OUTFIT avatar template"),
    104: (1861, 10023, "MOBS row carries no s_OUTFIT avatar template"),
}

# MOBS rows in this scene that list SEVERAL avatar templates separated by
# ';', as leader n_ID -> the whole string.  The table below ships the FIRST
# variant; ``_self_check`` refuses if a ';' ever reaches the shipped column.
# [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION]
MULTI_VARIANT_OUTFITS = {
    138: "M000_000_002_SP1;M000_000_002_SP2",
    139: "M005_000_001_SP1;M005_000_001_SP2",
    140: "M024_001_001_SP1;M024_001_001_SP2",
    141: "M002_000_000_SP1;M002_000_000_SP2",
    142: "M019_000_001_SP1;M019_000_001_SP2",
    143: "M011_001_001_SP1;M011_001_001_SP2",
    145: "M001_000_003_N;M001_000_003_SP1",
    147: "M001_000_001_SP2;M001_000_001_SP3",
    149: "M003_000_000_SP1;M003_000_000_SP2",
    7044: "M024_001_001_SP1;M024_001_001_SP2",
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
# 59 rows: every Mob-Set number this scene's placements use that CLINE type
# 5 resolves to a body.
_RESOLVED_ROWS = (
    (2, 1801, 105, "M055_000_000_N", "Columbus", "Marine Transport Station", 70, 0, 71640, 2),
    (3, 1802, 106, "M070_000_000_N", "Old Tom", "Pirate Dad", 70, 0, 71640, 2),
    (4, 1803, 107, "M001_000_000_SP2", "Port Side Pirates", "", 70, 0, 71640, 2),
    (5, 1804, 108, "M015_000_003_SP2", "Sea Devil", "Pirate Radio Station", 70, 0, 71640, 2),
    (6, 1805, 109, "M072_000_000_N", "Jessica", "Beer Promoter Girl", 70, 0, 71640, 2),
    (7, 1806, 110, "P_MALE_012_001_PHILI", "Filet", "Good Man", 70, 0, 71640, 2),
    (8, 1807, 111, "M010_000_001_SP3", "Rob", "Loyalty Soldier", 70, 0, 71640, 2),
    (9, 1808, 112, "P_MALE_003_000_N", "Rude pirates", "", 70, 0, 71640, 2),
    (10, 1809, 113, "M001_002_000_SP2", "Pirates from afar", "", 70, 0, 71640, 2),
    (11, 1810, 114, "P_MALE_009_000_DUWEN", "daul", "Black Market Trader", 70, 0, 71640, 2),
    (12, 1811, 115, "M073_000_001_N", "Digo", "Black Market Trader", 70, 0, 71640, 2),
    (13, 1812, 116, "P_FEMALE_005_000_MONNA", "Mona", "Black Market Trader", 70, 0, 71640, 2),
    (14, 1813, 117, "M019_000_000_SP4", "Edward", "Black Braids", 70, 0, 71640, 2),
    (15, 1814, 118, "M017_000_000_SP4", "Khayredin", "Red Beard", 70, 0, 71640, 2),
    (16, 1815, 119, "P_MALE_006_001_HORKA", "Hokah", "Nomad Maritime", 70, 0, 71640, 2),
    (17, 1816, 120, "P_MALE_009_002_N", "Mystery buyer", "", 70, 0, 71640, 2),
    (18, 1817, 121, "P_MALE_001_000_ROLANCE", "Rollence", "Exiled Colonel ", 70, 0, 71640, 2),
    (19, 1818, 122, "M009_000_000_N", "Odyssey", "Wrath Witch", 70, 0, 71640, 2),
    (20, 1819, 123, "P_MALE_012_001_PHILI", "Filet", "Chef", 70, 0, 71640, 2),
    (21, 1820, 124, "M019_000_000_SP4", "Edward", "Militant Black Braids", 70, 0, 71640, 2),
    (22, 1821, 125, "P_MALE_002_002_HOSE", "Halsey", "Traitor Adjutant", 70, 0, 71640, 2),
    (23, 1822, 126, "M024_001_001_SP2", "Lost pirate", "", 70, 0, 71640, 2),
    (24, 1823, 127, "M001_001_000_SP2", "Lust pirate", "", 70, 0, 71640, 2),
    (25, 1824, 128, "M001_000_003_SP3", "Jonny", "Black Braids Officer", 70, 0, 71640, 2),
    (26, 1825, 129, "M017_000_001_SP3", "Wiliam", "Red Beard Officer", 70, 0, 71640, 2),
    (27, 1826, 130, "P_MALE_003_001_NAVYDUAL3", "Latent bounty hunter", "", 70, 0, 71640, 2),
    (28, 1827, 131, "M001_000_001_SP2", "Governor guard", "", 70, 0, 71640, 2),
    (29, 1828, 132, "M001_000_001_SP1", "Governor guard", "", 70, 0, 71640, 2),
    (30, 1829, 133, "M015_000_003_SP1", "Sea Devil", "Port Authority Communications", 70, 0, 71640, 2),
    (31, 1830, 134, "M017_000_000_SP4", "Khayredin", "Deceit Red Beard", 70, 0, 71640, 2),
    (32, 1831, 135, "P_MALE_005_001_STARK", "Stark", "Port Royale", 70, 0, 71640, 2),
    (33, 1832, 136, "M073_000_001_SP3", "Terry", "Black Market Trader", 70, 0, 71640, 2),
    (34, 1833, 137, "P_FEMALE_003_000_KATE", "Kate", "Cute Girl Pirate", 70, 0, 71640, 2),
    (35, 1834, 138, "M000_000_002_SP1", "Blind Hound", "", 61, 1, 45704, 1),
    (36, 1835, 139, "M005_000_001_SP1", "Sparkler Antelope", "", 62, 1, 48209, 1),
    (37, 1836, 140, "M024_001_001_SP1", "Penguin Staff Sergeant", "", 62, 1, 48209, 1),
    (38, 1837, 141, "M002_000_000_SP1", "Two Horns Tiger", "", 63, 1, 50817, 1),
    (39, 1838, 142, "M019_000_001_SP1", "Golden Cat Navy Group", "", 64, 1, 53557, 1),
    (40, 1839, 143, "M011_001_001_SP1", "Steel blade Eagle", "", 67, 1, 62350, 1),
    (41, 1840, 144, "M011_001_001_SP3", "Hard Blade Eagle", "", 68, 1, 65511, 1),
    (42, 1841, 145, "M001_000_003_N", "Black braids Pirates", "", 64, 1, 53557, 1),
    (43, 1842, 146, "M001_000_003_SP3", "Black Jack", "", 65, 1, 56377, 1),
    (44, 1843, 147, "M001_000_001_SP2", "Red beard Pirate Group", "", 66, 1, 59306, 1),
    (45, 1844, 148, "M010_000_001_SP3", "Red Devil", "", 66, 1, 59306, 1),
    (46, 1845, 149, "M003_000_000_SP1", "Ned King Kong", "", 68, 1, 65511, 1),
    (47, 1846, 150, "M003_000_000_SP3", "Ned apes", "", 69, 1, 68789, 1),
    (48, 1847, 643, "P_FEMALE_006_001_AMINA", "Amina", "Nomad Maritime", 70, 0, 71640, 2),
    (49, 1848, 237, "MAP001_000_000", "Mirage reel", "", 105, 0, 228055, 2),
    (50, 1849, 238, "MAP001_000_000", "Mirage reel", "", 105, 0, 228055, 2),
    (51, 1850, 239, "BULLETIN_BOARD", "Evil Port Bulletin Board 1", "", 105, 0, 228055, 2),
    (52, 1851, 240, "BULLETIN_BOARD", "Evil Port Bulletin Board 2", "", 105, 0, 228055, 2),
    (53, 1852, 241, "BULLETIN_BOARD", "Evil Port Bulletin Board 3", "", 105, 0, 228055, 2),
    (54, 1853, 242, "BULLETIN_BOARD", "Governor Palace Bulletin Board", "", 105, 0, 228055, 2),
    (55, 1854, 243, "BULLETIN_BOARD", "Governor Palace Bulletin Board", "", 105, 0, 228055, 2),
    (56, 1855, 244, "BULLETIN_BOARD", "Governor Palace Bulletin Board", "", 105, 0, 228055, 2),
    (57, 1856, 523, "M015_001_001_N", "Jet cat thieves No.5", "", 62, 1, 48209, 1),
    (58, 1857, 525, "M015_001_001_N", "Jet cat thieves No.6", "", 67, 1, 62350, 1),
    (59, 1862, 854, "M010_001_000_N", "Elephant Oz", "Navy Spy", 75, 0, 87072, 2),
    (105, 1863, 7044, "M024_001_001_SP1", "Penguin Searcher", "Serious and responsible", 99, 0, 192488, 2),
)

IDENTITIES = {row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS}


@dataclass(frozen=True)
class Bg0005Placement:
    """One Bg0005 placement resolved to a real, named, bodied actor."""

    placement_index: int
    template_id: int
    mm_instance: int
    x: float
    y: float
    z: float
    identity: SceneIdentity | None

    @property
    def actor_identity(self) -> int:
        # The same formula bg0004, bg0010 and bg0015 all use.  Never sent in
        # the same generation as another scene's census - every builder
        # refuses any scene id but its own - so sharing the numeric space is
        # a collision in the abstract only.  No lane-B module for this scene
        # exists yet (checked this round: 0 files under src/ mention
        # Bg0005/BG0005 as a census composer outside this pair).
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
    (0, 1, 1, 13025.5107421875, 22814.951171875, -723.1168823242188),
    (1, 2, 1, 13713.9306640625, 23299.134765625, -721.7659301757812),
    (2, 3, 1, 13398.5625, 18166.150390625, -134.64370727539062),
    (3, 4, 1, 13674.74609375, 14206.3076171875, 259.63031005859375),
    (4, 5, 1, 8509.7451171875, 11640.6318359375, 445.15399169921875),
    (5, 6, 1, 7838.57861328125, 9210.04296875, 661.2045288085938),
    (6, 7, 1, 6284.8125, 8807.986328125, 673.8709106445312),
    (7, 10, 1, 7210.814453125, 8244.14453125, 641.9002075195312),
    (8, 8, 1, 8607.525390625, 8730.9248046875, 680.4398803710938),
    (9, 9, 1, 7074.0703125, 9228.033203125, 678.1546020507812),
    (10, 11, 1, 11297.1611328125, 17592.357421875, -137.8721923828125),
    (11, 12, 1, 10777.12109375, 15630.810546875, -155.77059936523438),
    (12, 13, 1, 9082.171875, 15459.6357421875, -204.7761993408203),
    (13, 14, 1, 788.2362060546875, 7297.86328125, 417.5494079589844),
    (14, 15, 1, -1216.4432373046875, 6986.12451171875, 365.64190673828125),
    (15, 16, 1, 19553.55078125, 2279.228515625, 335.7471923828125),
    (16, 17, 1, 24054.26953125, 19109.75390625, -653.2152099609375),
    (17, 18, 1, 24090.8359375, -8686.7353515625, -450.23028564453125),
    (18, 19, 1, 21822.234375, -11349.15625, -404.28240966796875),
    (19, 20, 1, 23003.16796875, -11515.3984375, -409.025390625),
    (20, 24, 1, -2937.280517578125, -7805.58251953125, 1280.741455078125),
    (21, 22, 1, 12382.232421875, -19368.134765625, 2778.150390625),
    (22, 23, 1, 7266.45849609375, -19074.841796875, 4010.521728515625),
    (23, 25, 1, -11794.84765625, -6323.099609375, 1194.275146484375),
    (24, 26, 1, -14613.884765625, -2838.358154296875, 1632.8292236328125),
    (25, 27, 1, -12222.30078125, -24118.9609375, 3791.245361328125),
    (26, 28, 1, -18684.798828125, -8753.9111328125, 900.0797729492188),
    (27, 29, 1, -20597.9375, -7426.64453125, 1219.686279296875),
    (28, 30, 1, -19527.81640625, 3007.899169921875, 2515.219482421875),
    (29, 36, 1, 20798.232421875, -4936.638671875, -363.631103515625),
    (30, 32, 1, -22736.818359375, 2566.93212890625, 2480.736328125),
    (31, 33, 1, -22861.49609375, 3757.7392578125, 2480.736572265625),
    (32, 34, 1, -23215.25390625, 4987.2607421875, 2480.736328125),
    (33, 31, 1, -19928.544921875, 5812.16650390625, 3401.2431640625),
    (34, 36, 2, 18170.0859375, -2679.031494140625, -67.54910278320312),
    (35, 36, 3, 16779.931640625, -72.02649688720703, 321.1326904296875),
    (36, 35, 1, 20029.669921875, 4112.3447265625, 308.2892150878906),
    (37, 35, 2, 23668.69921875, 14995.283203125, -588.9288940429688),
    (38, 35, 3, 25156.513671875, 8411.740234375, -253.09469604492188),
    (39, 37, 1, 21025.353515625, -10186.873046875, -417.7738952636719),
    (40, 37, 2, 23415.076171875, -15860.9296875, 180.18040466308594),
    (41, 39, 1, 10045.92578125, -12512.611328125, 1472.1153564453125),
    (42, 39, 2, 12206.66015625, -18864.158203125, 2720.913818359375),
    (43, 38, 1, 4855.95361328125, -2948.18359375, 1051.396484375),
    (44, 38, 2, 9282.216796875, -2948.183837890625, 730.7421875),
    (45, 38, 3, 13141.130859375, -3423.28173828125, 368.8460998535156),
    (46, 38, 4, 10875.05078125, -8458.046875, 1279.80078125),
    (47, 42, 1, -9193.486328125, 10762.66015625, 1747.550048828125),
    (48, 40, 1, -6125.078125, 4165.0703125, 156.64779663085938),
    (49, 40, 2, -8953.16015625, 2657.495849609375, 171.9824981689453),
    (50, 42, 2, -10904.150390625, -347.5664978027344, 171.75880432128906),
    (51, 42, 3, -10534.13671875, -4745.1865234375, 932.2620849609375),
    (52, 42, 4, -16890.2109375, -10819.494140625, 985.5640258789062),
    (53, 42, 5, -15278.095703125, -15102.326171875, 1338.5859375),
    (54, 42, 6, -20593.74609375, -12035.27734375, 1308.141845703125),
    (55, 44, 1, -5294.36083984375, -8968.349609375, 1369.7139892578125),
    (56, 44, 2, -6459.220703125, -17140.755859375, 1479.4031982421875),
    (57, 44, 3, -10249.015625, -16768.607421875, 1396.6512451171875),
    (58, 44, 4, -6220.5341796875, -12807.46484375, 1506.6683349609375),
    (59, 45, 1, -19755.85546875, -3189.87841796875, 2131.141357421875),
    (60, 44, 5, -19834.935546875, -8736.451171875, 959.165771484375),
    (61, 44, 6, -14313.603515625, -6675.025390625, 1075.041748046875),
    (62, 44, 7, -13792.6796875, -5533.38671875, 1210.43212890625),
    (63, 44, 8, -22209.375, -5147.27099609375, 1378.6141357421875),
    (64, 44, 9, -14671.744140625, -229.08360290527344, 1745.588623046875),
    (65, 46, 1, -18741.36328125, -15715.4453125, 1449.3448486328125),
    (66, 46, 2, -20828.984375, -20068.177734375, 3731.44384765625),
    (67, 46, 3, -18553.70703125, -21889.1640625, 3800.473388671875),
    (68, 46, 4, -14183.904296875, -21729.693359375, 3102.8974609375),
    (69, 47, 1, -11527.8701171875, -24172.7265625, 3907.96923828125),
    (70, 41, 1, -9130.62890625, 11611.884765625, 1747.5501708984375),
    (71, 40, 3, -7589.78271484375, 9326.3359375, 1747.55029296875),
    (72, 40, 4, -10423.08203125, 5432.63037109375, 1778.254638671875),
    (73, 21, 1, 8379.65625, -2693.948974609375, 894.0786743164062),
    (74, 43, 1, -11004.3955078125, -6054.455078125, 1054.8873291015625),
    (75, 48, 1, 19953.283203125, 6933.0078125, 593.5579223632812),
    (76, 49, 1, 8188.1357421875, 11789.5390625, 445.8775939941406),
    (77, 50, 1, -19880.984375, 3033.983642578125, 2515.223388671875),
    (78, 51, 1, 13085.66015625, 19055.01171875, -159.0135955810547),
    (79, 52, 1, 8585.2724609375, 7122.31591796875, 643.3032836914062),
    (80, 53, 1, 9547.22265625, 17424.001953125, -161.3780059814453),
    (81, 54, 1, -24269.408203125, 2043.339111328125, 2481.28271484375),
    (82, 55, 1, -15424.962890625, 6190.8720703125, 2465.40087890625),
    (83, 56, 1, -20538.68359375, 3314.73046875, 2480.736328125),
    (84, 57, 1, 22612.3046875, -17041.068359375, 401.7677917480469),
    (85, 58, 1, -10786.951171875, 14406.4208984375, 1766.5823974609375),
    (86, 101, 1, 24268.1796875, 20712.615234375, -712.81298828125),
    (87, 102, 1, -5376.98046875, 4618.6748046875, 151.97079467773438),
    (88, 103, 1, -7034.72021484375, 8758.2265625, 1747.5498046875),
    (89, 104, 1, -10067.2119140625, -17466.40625, 1576.4007568359375),
    (90, 59, 1, 25066.45703125, 20112.796875, -711.680419921875),
    (91, 105, 1, -25806.158203125, 2762.693359375, 3359.733154296875),
)

PLACEMENT_COUNT = len(_PLACEMENT_ROWS)


class Bg0005IdentityError(ValueError):
    """A refusal from this module, always with a reason in the message."""


def identity_for(template_id: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    ``None`` is exactly the five sets in ``UNRESOLVED`` and nothing else:
    this function never substitutes, and never falls back to the Mob-Set
    number that ``GT-078`` proved wrong on the owner's screen.
    """
    if type(template_id) is not int or type(template_id) is bool:
        raise Bg0005IdentityError("template id must be an int")
    return IDENTITIES.get(template_id)


def shippable_placements() -> tuple[Bg0005Placement, ...]:
    """The 87 placements of the 92 that resolve to a real identity."""
    out = []
    for index, template_id, mm_instance, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(template_id)
        if identity is None:
            continue
        out.append(Bg0005Placement(
            index, template_id, mm_instance, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The five that are dropped, each with the id and the reason.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH five and WHY.
    """
    out = []
    for index, template_id, _mm, x, y, z in _PLACEMENT_ROWS:
        if template_id in IDENTITIES:
            continue
        cline_row_id, leader, reason = UNRESOLVED.get(
            template_id, (0, 0, "set not in CLINE 5"))
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
    census builder at all, and an ImportError names the file."""
    if len(_RESOLVED_ROWS) != 59:
        raise Bg0005IdentityError(
            "expected 59 resolved sets, found %d" % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg0005IdentityError("duplicate Mob-Set number in the table")
    if len(UNRESOLVED) != 5:
        raise Bg0005IdentityError(
            "expected 5 unresolved sets, found %d" % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg0005IdentityError("a set is both resolved and unresolved")
    if len(_PLACEMENT_ROWS) != 92:
        raise Bg0005IdentityError(
            "expected 92 placements, found %d" % len(_PLACEMENT_ROWS))
    # Control 1: every Mob-Set number this scene's placements use is either
    # resolved or named as unresolved, and the two sets together are EXACTLY
    # this scene's 64 used keys - a placement keyed by a number this table
    # has never heard of means the placement file and the crosswalk came
    # from different extractions.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if scene_sets != table_sets:
        raise Bg0005IdentityError(
            "placement Mob-Set numbers and this table's keys disagree: %r"
            % sorted(scene_sets ^ table_sets))
    if len(table_sets) != 64:
        raise Bg0005IdentityError(
            "expected 64 distinct Mob-Set numbers, found %d" % len(table_sets))
    if not no_set_number_is_shipped_as_identity():
        raise Bg0005IdentityError(
            "a row ships its own Mob-Set number as an identity")
    for row in _RESOLVED_ROWS:
        (template_id, cline_row_id, n_id, outfit, name, title, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1:
            raise Bg0005IdentityError(
                "set %d carries no CLINE row locator" % template_id)
        if ";" in outfit:
            raise Bg0005IdentityError(
                "set %d ships a multi-variant outfit string" % template_id)
        if not outfit or not outfit.isascii():
            raise Bg0005IdentityError(
                "set %d has an empty or non-ASCII outfit" % template_id)
        if not name.isascii() or not title.isascii():
            raise Bg0005IdentityError(
                "set %d has a non-ASCII name or title" % template_id)
        if not name:
            raise Bg0005IdentityError(
                "set %d has no display name (no INVISIBLE-marker exception "
                "exists in this scene, unlike bg0004)" % template_id)
        if max_hp < 1 or level < 1:
            raise Bg0005IdentityError("set %d has a bad level/HP" % template_id)
    if len(shippable_placements()) != 87:
        raise Bg0005IdentityError("expected 87 shippable placements")
    if len(unshippable_placements()) != 5:
        raise Bg0005IdentityError("expected 5 unshippable placements")
    ids = [p.actor_identity for p in shippable_placements()]
    if len(ids) != len(set(ids)):
        raise Bg0005IdentityError("actor identities collide within this table")


_self_check()
