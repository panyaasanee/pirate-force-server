"""Who each bg0001 placement actually IS, from the client's own named crosswalk.

LANE-A (WORLD), BUILD-001 / M1.  This module exists because of one measured
fact and one owner verdict:

* ``world_population`` has been shipping ``placement.template_id`` -- the
  scene file's Mob-Set number, 1..113 -- into ``make_npc_attr``'s first
  parameter, which that serializer's own docstring names as "the MOBS/template
  u16 at +0x78".  A Mob-Set number is not a ``MOBS.n_ID``.
* ``GT-078`` put that on the owner's screen and the owner rejected it on
  sight, in one sentence that names both halves: every placement right, every
  NPC wrong.

``RE-128`` (opened by this lane, answered by the RE runner 2026-08-28T19:12,
cross-checked by this lane and beaten on by ``pf-adversary``) found the named
table that converts one into the other, and it was committed in this project
all along:

    SCENE_NAME[s_MODLE_ID=BG0001].n_CLINE_TYPE = 1
    CLINE[(n_CLINE_TYPE=1, n_CREATURE_TYPE=<Mob-Set number>)].n_LEADER_BK1
        = the real MOBS.n_ID
    MOBS[n_ID].s_OUTFIT       = the avatar template the client loads
    MOBS_TIP[n_ID].s_NAME     = the name the client draws under the actor

WHY THIS IS BELIEVED, at the layer the owner's own ruling puts on top
(client-observable > wire/DB > table inference, COO-DECISION 2026-08-28T21:30):

1. ``20260827_1240_PANYA-EVIDENCE-video2-Port-Royal-NPC-tour`` tabulates 32
   ``n_ID`` values the owner saw on screen in Port Royal.  All 32 are in this
   scene's CLINE leader set.  NONE of the 32 is in the Mob-Set number range
   this tree has been shipping (measured: 32/32 present, 0/32 present).
   READ THIS AT ITS REAL WEIGHT (pf-adversary): set membership is invariant
   under EVERY permutation of the 105 identities, so this certifies the
   ROSTER - the image of the crosswalk is Port Royal's cast - and says
   nothing about which placement gets which member.
2. The owner's two placement-level anchors reproduce exactly:
   placement 1 -> 156 Columbus (shipped today as "Sebastian"), placement 65 ->
   802 Loie (shipped today as "Columbus" -- the owner's exact complaint was
   that this one is the slave market's Columbus, not Port Royal's).
3. Positional control, not just set membership: four pairs the owner filmed
   standing side by side (Da Vinci+Chalais, Hields+Sase, Dorothy+Melody,
   Brin+Remad) land on placements 396-1201 units apart, which is the 0.1-1.1
   percentile of all 6,555 pairwise placement distances (median 17,242).
   The two anchors of point 2 cannot rule out an off-by-one mapping
   (pf-adversary raised exactly that last round); this can, and was measured
   as a control: under leader[t+1] only ONE of the four pairs is even
   resolvable, at the 45th percentile; under leader[t-1] two are, at the 19th
   and 51st; under leader[t+2] one, at the 30th.  Only the unshifted mapping
   puts all four pairs in the closest 1.2%.
4. ``pf-adversary`` brute-forced 182 gamedata tables x 49,028 column pairs for
   any pair that sends 2->156 AND 67->802: exactly one survives, this one.
   Re-run this round on the current tables: still exactly one.
5. Cross-scene structural control (pf-adversary, this round): for all 19
   scenes with a real ``SCENE_NAME.n_CLINE_TYPE``, the scene file's Mob-Set
   numbers are a SUBSET of that CLINE block's keys, and 8 of the 19 are exact
   set equality including sparse ones (Bg0002's 45 sets scattered up to 104
   are matched exactly).  A block of literal 1..N keys could not cover 104.

HOW MUCH OF THE TABLE IS ACTUALLY PINNED PER PLACEMENT.  Two rows by the
owner's anchors (Mob-Set 2 and 67) plus eight by the four adjacency pairs
(4, 5, 31, 61, 65, 82, 90, 91) = 10 of 105 rows, 9.5%.  The other 95 rest on
table inference, which the same COO ruling puts at the BOTTOM of the evidence
order.  That is the honest state of this table and it is why ``GT-131`` exists.

THE QUESTION THIS DESIGN HAS NOT ANSWERED (pf-adversary, and it is a good
one).  RE-128's proof is that the CLIENT resolves this scene's NPCs LOCALLY -
``bg0001.npc`` definition id -> ``SCENE_NAME`` -> ``CLINE`` -> ``MOBS`` -
inside its own map-NPC loader, before any server frame arrives; and RE-092
established the remote-actor consumer this census uses is replace-by-omission.
Nobody has shown whether the client's locally-built scene NPCs and this
collection are the same registry.  If they are not, this census may be adding
a second cast rather than naming the first one.  ``GT-131``'s map-window step
is the cheapest observation that bears on it; the question itself belongs to
``RE-128``'s open nonclaims, not to this module.

WHAT THIS MODULE REFUSES TO DO.  Eight of this scene's 113 Mob-Set numbers
convert to a leader id with no ``CONSTDATA MOBS`` row (155, 819, 9107, 937,
942), to 0, or to a MOBS row with no avatar template (10002); seven of the
eight are used by the 115 shipped placements.  What those five ids are missing
is precisely the ``s_OUTFIT`` avatar template - all five DO have a
``MOBS_TIP`` name (155 is "Port transportation", at the dock placement the
owner's 2026-08-27 09:50 letter lists as unconfirmed with "Lisa 177" as its
candidate), and 208 MOBS_TIP ids have no MOBS row, so a missing MOBS row is a
property of the extracted TH tables, not a statement about those actors.
[LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION] that an entry with no
avatar template should be dropped rather than sent with the frozen table's own
preset: RE-128 T2 measured the helper at ``0x0043A120`` as requiring a MOBS row
for MAP-LIST eligibility, and it is this lane, not RE-128, that reads that
across to "cannot be raised as an actor".  pf-adversary argued the other way
and the argument is real: a dropped actor produces no owner feedback, and every
identity error in this project so far was corrected because the owner SAW it.
They are listed in ``UNRESOLVED`` with the id and the reason, and this
module returns ``None`` for them rather than inventing a substitute or falling
back to the Mob-Set number that ``GT-078`` proved wrong.  ``world_population``
drops them from the census and says so on the console line every boot -- the
shipped count therefore reads 108/115, loudly, never silently (CHARTER-02:
a shortfall is reported with the real number and the reason, and the 115 target
is not quietly rewritten to something else).

RELATION TO ``world_scene_numbering``, which refuses every scene.  That guard
says a Mob-Set number may not be shipped as an identity.  This module is not an
exception to it: it is what makes it keepable, because it removes the last
place in this tree where a Mob-Set number was used as one.  ``no_set_number_is
_shipped_as_identity()`` below is the executable form of that claim - measured
over the whole table: 0 of 113 CLINE type-1 rows have leader == creature type.

~~[LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION] The owner's standing
instruction is that a scene's identities are not stated as fact until seven
numeric anchors clear.  This lane reads the 32 video-confirmed ids plus the two
placement anchors plus the four adjacency pairs as clearing that bar for
bg0001, and ships on that reading; ``notes_to_chief/20260828_2240_LANE-A-ASK-
COO-cline-identity-clears-the-anchor-bar.md`` is the letter asking for the
ruling.  If the ruling goes the other way the revert is one commit: this file
and the ``_entry``/``census_order`` change in ``world_population``.~~
ANSWERED, and the assumption label is struck rather than deleted so the
reading can still be told from the ruling that followed it.  The owner
confirmed it directly, in person, at a higher evidence layer than the seven
anchors themselves: ``GT-131`` PASS, owner watching the live client,
"ตำแหน่ง npc ถูก ตัวถูกต้อง ฉันให้เทสนี้ผ่าน" (2026-08-30T00:2x+07:00,
``notes_to_chief/20260830_0030_KA3A-GT131-PASS-owner-confirmed-*``), ratified
in ``notes_to_chief/20260830_1351_COO-DECISION-cline-anchor-bar-cleared-
gt131-pass.md``.  The identity read below is client-observable-confirmed now,
not merely anchor-counted.  If a later finding contradicts it the revert is
still one commit: this file and the ``_entry``/``census_order`` change in
``world_population``.

PROVENANCE.  Every row below was generated from these four committed artifacts
and nothing else; the digests are the files as of 2026-08-28T22:5x+07:00.
"""
from __future__ import annotations

from dataclasses import dataclass


# Convention marker: shippable, no scenario flag.  See the module docstring
# before quoting this as evidence of anything else.
production_allowed = True
test_only = False

SCENE_ID = 1
SCENE_MODEL_ID = "BG0001"
SCENE_CLINE_TYPE = 1

# RECORDED PROVENANCE, NOT A CHECK.  These four tables live in the pf_bridge
# clone, not in this repository, so nothing here can compare a digest against
# them at import - unlike gm/scene_catalog.py, whose table is committed
# beside it.  Kept so a regeneration can be audited by hand; do not read this
# as a guard (pf-adversary, this round).
SOURCE_SHA256 = {
    "gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv":
        "e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b",
    "gamedata/tables/CONSTDATA_TH__CLINE.tsv":
        "aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40",
    "gamedata/tables/CONSTDATA_TH__MOBS.tsv":
        "3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b",
    "gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv":
        "e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f",
}

# The 32 ids the owner saw on screen (PANYA-EVIDENCE 2026-08-27 12:40).  Kept
# here so the check that they are all reachable is executable, not a sentence.
OWNER_VIDEO_CONFIRMED_N_IDS = (
    156, 157, 158, 159, 161, 162, 163, 164, 165, 167, 173, 177, 248, 622, 623,
    624, 634, 717, 740, 796, 797, 798, 800, 801, 802, 833, 899, 903, 904, 905,
    909, 913,
)

# One MOBS row in this scene lists SEVERAL avatar templates separated by ';'
# (n_ID 910, Saben, used by the shipped 115).  make_npc_attr's field is a
# single basename that the client formats into ".\\Data\\GC\\V\\%s.avt", so the
# raw string cannot go on the wire - it would name a file that does not exist
# and the actor would arrive with no body at all.  The table above ships the
# FIRST variant and the full string is kept here, because a variant list is a
# choice the original server made per spawn and we do not know its rule.
# [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION] first-listed variant.
MULTI_VARIANT_OUTFITS = {
    910: 'P_MALE_004_000_N;P_MALE_002_000_SP1;P_MALE_001_000_ROLANCE',
}

# LEADER-ONLY, AND HERE IS WHAT THAT COSTS (pf-adversary, this round).
# RE-128 proved the client's dispatch iterates NINE id fields per CLINE row -
# n_LEADER_BK1..3 and n_CREW1..6 - and its delivered table has 119 rows for
# this scene's 113 Mob-Set numbers.  The extra six are all of Mob-Set 88: the
# crew of 899 Aisha, Herdsman, at placement 88.  This module implements
# n_LEADER_BK1 only, so those six are NOT shipped.  They are recorded here
# rather than left uncounted, because a shortfall nobody names is exactly what
# CHARTER-02 forbids: if the owner walks to Aisha and sees no pets, this is
# the reason, and it is not one of the seven dropped placements.
# Whether one placement raises the leader alone or leader+crew is RE-128's
# still-open nonclaim 2 - not this lane's to decide.
UNSHIPPED_CREW = {
    88: ((8601, 'Sediment Wolf'), (8611, 'Polar ape'), (8617, 'Fire magic'),
         (8626, 'Nightmare Claw beast'), (8629, 'Purple turtle'),
         (8647, 'Air Thief Meteor Mech')),
}

# The two placement-level anchors the owner confirmed by hand, as
# placement index -> MOBS n_ID.  A crosswalk that misses either of these is
# not this crosswalk.
OWNER_PLACEMENT_ANCHORS = {1: 156, 65: 802}
# The same two anchors keyed by Mob-Set number, so ``_self_check`` can hold
# the table to them without needing the frozen placement source.
OWNER_PLACEMENT_ANCHOR_TEMPLATES = {2: 156, 67: 802}


@dataclass(frozen=True)
class SceneIdentity:
    """One resolved actor: who it is, what it wears, what its label says."""

    template_id: int
    mobs_n_id: int
    outfit: str
    name: str
    title: str


# (Mob-Set number, MOBS.n_ID, MOBS.s_OUTFIT, MOBS_TIP.s_NAME, MOBS_TIP.s_TITLE)
# 105 rows: EVERY Mob-Set number in this scene's CLINE block that resolves, not
# only the 81 today's frozen 115-placement source happens to use.  The
# crosswalk is a property of the scene, so widening the placement source later
# does not need this table regenerated.  n_ID 917 (Mob-Set 98 and 103) has a
# MOBS row but no MOBS_TIP row, so its name is empty and the client draws no
# name line for it - recorded, not papered over.
_RESOLVED_ROWS = (
    (2, 156, 'M055_000_000_N', 'Columbus', 'Marine Transport Station'),
    (3, 157, 'M071_000_002_N', 'Love Millie', 'Antique Store'),
    (4, 158, 'M071_000_001_SP2', 'Dorothy', ''),
    (5, 159, 'P_MALE_002_001_FRANK', 'Hields', 'Guild Administrator'),
    (6, 160, 'P_MALE_002_001_FRANK', 'Frank', 'Port Royal Congressman'),
    (7, 161, 'M068_000_002_N', 'Locher', 'Finance Administrator'),
    (8, 162, 'P_MALE_009_002_JOSHUA', 'Joshua', 'Appraisers'),
    (9, 163, 'P_MALE_001_001_MIKEY', 'Mackie', 'Royal Exchange Manager'),
    (10, 164, 'P_MALE_008_002_NAYA', 'Nayar', 'Skill Trainer'),
    (11, 165, 'P_MALE_003_003_TIM', 'Tim', 'Dungeon Keeper'),
    (12, 166, 'M072_000_002_N', 'Grace', 'Beer Promoter Girl'),
    (13, 167, 'P_MALE_010_000_JAMSON', 'Jensen', 'Shipyard Engineer'),
    (14, 168, 'M052_000_000_N', 'Nelson', 'Royal Navy Admiral'),
    (15, 169, 'M056_000_000_N', 'Bismarck', 'Admiral'),
    (16, 170, 'M057_000_000_N', 'Isoroku Yamamoto', 'Admiral'),
    (17, 171, 'M070_000_000_N', 'Drunkard Captain', 'Sea Watchers'),
    (18, 172, 'M015_000_000_SP3', 'Mo Yuzi', 'Naval Communications Bureau'),
    (19, 173, 'P_MALE_007_001_ANDERSON', 'Anderson', 'Antiquities Trader'),
    (20, 174, 'M024_001_000_N', 'Clark', 'Navy Lieutenant Colonel'),
    (21, 175, 'P_MALE_007_000_WILLS', 'Willes', 'Minister Palace'),
    (22, 176, 'M051_000_000_N', 'Rosemary', 'Princess'),
    (23, 177, 'M019_000_001_N', 'Lisa', 'Navy Transport Officer'),
    (24, 178, 'P_MALE_002_000_NEO', 'Neo', 'Treasure Hunters Assistant'),
    (25, 179, 'M071_001_000_SP3', 'Seafood Businesswoman', ''),
    (26, 180, 'P_FEMALE_012_002_DAZZY', 'Daisy', 'Beautiful Wife'),
    (27, 181, 'P_MALE_001_002_FEMANDEZ', 'Fernandez', 'Aristocratic Gentleman'),
    (28, 182, 'P_MALE_005_000_STRANGER', 'Mysterious Stranger', ''),
    (29, 183, 'M055_000_000_N', 'Columbus', 'Dream Voyager'),
    (30, 247, 'P_MALE_002_003_JOSEPH', 'Josef', 'Young Master'),
    (31, 248, 'P_MALE_018_000_DAVINCI', 'Da Vinci', 'World Artist'),
    (32, 356, 'M069_000_000_N', 'Jim', 'Pirates Fan Boy'),
    (33, 357, 'M069_000_001_N', 'Jill', 'Pirates Fan Boy'),
    (34, 358, 'M068_000_000_SP1', 'Babu', 'Strong Sailor'),
    (35, 359, 'P_MALE_004_000_N', 'Deserter Navy', ''),
    (36, 622, 'P_FEMALE_007_001_APPLE', 'Elbow', 'Safe Keeper'),
    (37, 623, 'M070_000_002_N', 'George', 'Redeem Officer'),
    (38, 624, 'M070_000_000_N', 'Toby', 'Heaven Officer'),
    (39, 625, 'M010_000_000_SP2', 'Paul', 'Ocean Navy '),
    (40, 626, 'P_FEMALE_005_001_SECILIA', 'Cecilia', "Maritime King's Daughter"),
    (41, 627, 'P_MALE_017_000_SILVER', 'Silva', 'Heroic Captain'),
    (42, 631, 'P_MALE_004_001_PALACEGUARD', 'Palace Lifeguard', ''),
    (43, 631, 'P_MALE_004_001_PALACEGUARD', 'Palace Lifeguard', ''),
    (44, 631, 'P_MALE_004_001_PALACEGUARD', 'Palace Lifeguard', ''),
    (45, 632, 'P_FEMALE_004_001_PRINCESSGUARD', 'Princess Guard', ''),
    (46, 632, 'P_FEMALE_004_001_PRINCESSGUARD', 'Princess Guard', ''),
    (47, 633, 'P_MALE_004_000_SP1', 'Navy Headquarters Guard', ''),
    (48, 633, 'P_MALE_004_000_SP1', 'Navy Headquarters Guard', ''),
    (49, 635, 'M001_003_001_SP2', 'Leo', 'The Wolf Bounty'),
    (50, 636, 'M019_003_000_N', 'Monica', 'Marksman Huntress'),
    (51, 637, 'INVISIBLE', 'Bermuda Crack', ''),
    (52, 638, 'BULLETIN_BOARD', 'Port Royal Bulletin Board', ''),
    (53, 639, 'P_MALE_001_003_BARBAROSA', 'Barbarossa', 'Maritime Presidency'),
    (54, 717, 'P_FEMALE_007_000_ERIA', 'Jenny', 'Smelter'),
    (55, 151, 'MAP001_000_000', 'Mirage reel', ''),
    (56, 152, 'BULLETIN_BOARD', 'Harbor Bulletin 1', ''),
    (57, 153, 'BULLETIN_BOARD', 'Harbor Bulletin 2', ''),
    (58, 154, 'BULLETIN_BOARD', 'Harbor Bulletin 3', ''),
    (59, 740, 'P_MALE_012_002_FRIEND', 'Romeo', 'Modern Lover'),
    (60, 741, 'P_FEMALE_012_002_FRIEND', 'Juliet', 'Sworn'),
    (61, 796, 'P_MALE_002_001_SARS', 'Sase', 'Guild Assistant'),
    (62, 797, 'P_MALE_003_001_JONATHAN', 'Jonathan', 'Strengthen Master'),
    (63, 798, 'P_FEMALE_002_000_MIX', 'Micks', 'Integration Master'),
    (64, 799, 'P_FEMALE_009_000_KELLY', 'Kailey', 'Smelting Master'),
    (65, 800, 'P_MALE_004_000_RIMERD', 'Remad', 'Refining Master'),
    (66, 801, 'P_MALE_010_001_ADAM', 'Adam', 'Royal Navy Engineer'),
    (67, 802, 'P_MALE_010_001_ROY', 'Loie', 'Royal Navy Engineer'),
    (68, 803, 'P_MALE_004_001_PALACEGUARD', 'Palace Lifeguard', 'Unconscious'),
    (69, 804, 'P_MALE_007_000_WILLS', 'Willes', 'Panic Lord'),
    (70, 805, 'P_MALE_009_000_ROBEN', 'Lupin', 'Strange Pirate'),
    (71, 767, 'P_FEMALE_002_003_NIGHTINGALE', 'Nightingale', 'Nursing'),
    (72, 815, 'M001_000_000_N', 'Bluebeard Barney', 'Unemployed Crew'),
    (73, 816, 'M024_000_001_N', 'Coruno', 'Sergeant Major vanguard'),
    (74, 817, 'M001_002_000_N', 'Jinbada', 'Eastern Wolf'),
    (75, 818, 'M010_001_000_N', 'Bear', 'Gutman'),
    (77, 820, 'M026_001_001_N', 'Caribbean', 'Curse Captain '),
    (78, 821, 'M017_000_003_N', 'Divinity', 'Barbarian'),
    (79, 822, 'M015_001_000_N', 'meow', 'Adventure Cat'),
    (80, 827, 'P_MALE_009_000_ROBEN', 'Lupin', 'Strange Pirate'),
    (81, 828, 'M079_000_000_N', 'Ophelia', 'Death Girl'),
    (82, 833, 'M070_000_002_N', 'Brin', 'Gold Shop'),
    (83, 834, 'M023_000_000_SP1', 'San Marco', 'Sky Dragon Trader'),
    (84, 882, 'M055_001_000_N', 'Magellan', ''),
    (85, 871, 'P_MALE_014_000_COLSON', 'Agent Coulson', ''),
    (88, 899, 'P_FEMALE_002_001_PET_LORD', 'Aisha', 'Herdsman'),
    (89, 902, 'P_MALE_010_000_STRONG', 'Wang Willie', 'Chocolate Factory Owner'),
    (90, 903, 'M071_000_001_SP1', 'Melody', 'Grocer'),
    (91, 904, 'P_MALE_002_002_SALEY', 'Chalais', 'Illustrations Appraisers'),
    (92, 905, 'P_MALE_005_000_BENFRIO', 'Benfolio', '\u0e23\u0e49\u0e32\u0e19\u0e1e\u0e31\u0e19\u0e18\u0e21\u0e34\u0e15\u0e23'),
    (93, 909, 'P_MALE_004_000_SP1', 'Strand', 'PVP Shop'),
    (94, 910, 'P_MALE_004_000_N', 'Saben', 'Onboard Engineer'),
    (95, 911, 'P_FEMALE_002_001_PET_LORD', 'Mysterious Stranger', ''),
    (96, 913, 'P_MALE_012_000_FRAG', 'Fraga', 'Fragment Changer'),
    (97, 916, 'M016_000_000_N', 'Training Iron Man', ''),
    (98, 917, 'INVISIBLE', '', ''),
    (99, 918, 'M071_000_000_SP2', 'Vera', 'Nutrition Jelly Shop'),
    (100, 920, 'M074_000_000_N', 'Hemingway', 'Strange Fishing'),
    (102, 634, 'M024_000_000_N', 'Navy Private', 'Navy Patrol'),
    (103, 917, 'INVISIBLE', '', ''),
    (104, 897, 'P_MALE_010_000_STRONG', 'Alienation Big Wolf', ''),
    (105, 928, 'P_MALE_012_010_DETACTIVE', 'Hired Detective', 'Hard work'),
    (106, 929, 'P_MALE_010_000_JAMSON', 'Jensen', 'Lying on the ground'),
    (107, 930, 'INVISIBLE', 'Suspicious Ship', ''),
    (108, 933, 'M024_000_000_SP1', 'Apple', 'Ultimate Bodyguard'),
    (109, 855, 'M008_000_003_SP3', 'Jack', 'Pumpkin Demon King'),
    (111, 934, 'P_FEMALE_007_002_KLEITA', 'Keleita', '\u0e23\u0e49\u0e32\u0e19\u0e40\u0e2a\u0e37\u0e49\u0e2d\u0e1c\u0e49\u0e32'),
)

# Mob-Set number -> (leader id CLINE gave, why it cannot be shipped).
UNRESOLVED = {
    1: (155, 'CLINE leader 155 has no CONSTDATA MOBS row, so no s_OUTFIT (MOBS_TIP does name it: Port transportation)'),
    76: (819, 'CLINE leader 819 has no CONSTDATA MOBS row, so no s_OUTFIT (MOBS_TIP names it: Tuna)'),
    86: (0, 'CLINE leader is 0 (no creature)'),
    87: (0, 'CLINE leader is 0 (no creature)'),
    101: (10002, 'MOBS row 10002 has no s_OUTFIT avatar template'),
    110: (9107, 'CLINE leader 9107 has no CONSTDATA MOBS row, so no s_OUTFIT (MOBS_TIP names it: Jack)'),
    112: (937, 'CLINE leader 937 has no CONSTDATA MOBS row, so no s_OUTFIT (MOBS_TIP names it: Mengsk)'),
    113: (942, 'CLINE leader 942 has no CONSTDATA MOBS row, so no s_OUTFIT (MOBS_TIP has a name for it)'),
}

# Mob-Set number -> the name the CLIENT'S OWN TEXT TABLE gives that leader,
# verbatim from TEXTDATA_TH__MOBS_TIP.tsv s_NAME (digest in SOURCE_SHA256,
# re-hashed on the bridge tree 2026-08-29T15:2x+07:00 and matched).  The same
# five names are already written into the UNRESOLVED reason strings above as
# prose; this is the machine-readable copy, so a console reader can be told
# WHO the town is missing without a caller parsing an English sentence.
#
# WHAT AN EMPTY STRING MEANS HERE, AND IT IS TWO DIFFERENT FACTS.  Mob-Set 86
# and 87 have no leader at all (CLINE leader 0), so there is nobody to name.
# Mob-Set 101's leader 10002 has a MOBS row and no MOBS_TIP row; its MOBS
# s_NAME is Chinese and reads as a pathfinding-helper prop, not a person, and
# no placement in the frozen bg0001 table uses Mob-Set 101 at all.  The two
# cases are told apart by UNRESOLVED's leader id (0 vs non-zero), never by the
# emptiness of this string.
#
# 113's name is kept in its original characters rather than transliterated.
# The bridge console is cp874 and cannot encode them, which is why every
# console path through this module goes through ``ascii_display_name`` below
# instead of printing this table.
UNRESOLVED_CLIENT_NAMES = {
    1: 'Port transportation',
    76: 'Tuna',
    86: '',
    87: '',
    101: '',
    110: 'Jack',
    112: 'Mengsk',
    113: '\u96f7\u9813',
}

# Every name this table carries has to belong to a refusal recorded above; a
# name for a Mob-Set number that is not refused would be a claim about an
# actor that ships, made in the wrong file.  Raised rather than asserted:
# ``python -O`` strips an assert, and this is a consistency guard, not a
# development aid.
if set(UNRESOLVED_CLIENT_NAMES) != set(UNRESOLVED):
    raise ValueError(
        "unresolved client names and unresolved refusals disagree"
    )

# --------------------------------------------------------------------------
# WHY THE CENSUS STOPS AT 108, ADJUDICATED RATHER THAN STILL OPEN (RE-149).
#
# BUILD-001's order from the owner is 115 placements in one shot, and its one
# red rule is that a census which does not go out whole reports the REAL
# number and the REASON - never a target quietly rewritten to whatever came
# out.  Since round pqx4fj the real number has been on the console (108/115)
# and since round mcxexp the seven missing placements have been named there.
# What was still missing is the last step of that rule: whether 7 of 115 is a
# SERVER shortfall somebody can still go and fix, or a ceiling the client's
# own shipped data sets.  Until it was answered, "108" was a number without a
# verdict, and a number without a verdict is what gets quietly rounded to 115
# by the next round that wants BUILD-001 closed.
#
# RE-149 (opened by this lane last round, answered 2026-08-29T18:14+07:00,
# pf_bridge/notes_to_chief/20260829_1814_RE-149-RESULT-NO-SHIPPED-AVATAR-
# SOURCE.md) is that verdict for the five leaders it covers: DONE /
# BOUNDED-NEGATIVE.  All five have a NAMED crosswalk out of CLINE
# n_LEADER_BK1 into MOBS id space, and none of them has a MOBS row, so there
# is no s_OUTFIT to dress them with; the run enumerated every table carrying
# an s_OUTFIT column, all 616 Lua files, all 289 scene .npc files and all four
# shipped PC tables, and found no other source that gives those ids a body.
#
# THE SCOPE OF THAT WORD "BOUNDED", COPIED FROM THE TICKET RATHER THAN
# SOFTENED.  It is negative AT THE STATIC METHOD CEILING OF THE CURRENT
# CORPUS: the shipped tree whose digests are pinned above.  The ticket
# explicitly does NOT claim that some other build or locale lacks these five,
# and it does NOT claim from a screen that the five cannot be drawn.  What it
# does establish is the only thing this module needs: there is no material in
# WHAT WE SHIP TODAY to build them from.
#
# THAT IS NOT "UNFIXABLE", AND AN EARLIER DRAFT OF THIS COMMENT SAID IT WAS
# (pf-adversary, this round, F5).  It read: "a round that fixed the shortfall
# would have to invent a row - which is the one thing CHARTER-02 forbids
# outright", which collapses three options into one.  The ticket's own
# BUILD_IMPACT names TWO legitimate repairs and neither is invention:
#   (1) open a job to find a new data pack / source, or
#   (2) define a new actor by OWNER decision.
# Only a third route - dressing these five from a number collision or a
# shared display name - is forbidden, and the ticket refuses that one by
# name.  The distinction matters because this comment is what a later round
# reads instead of the ticket: the collapsed version tells that round the
# shortfall is unfixable by rule and to close BUILD-001, when what the ticket
# actually asked for was to OPEN work.  See RE-152 (this lane, round tz2eri)
# for the successor that carries route (1) for placement 0, the harbour.
#
# The two temptations, refused by name: MOBS 8529
# ("Tuna") and MOBS 855 ("Jack") share a DISPLAY NAME with two of the five and
# are not crosswalked to them, and CHANGE_MODEL row 155 is a FIREARM in a
# different id space that merely collides on the number.
#
# THE OTHER TWO OF THE SEVEN ARE NOT RE-149'S, AND ARE NOT AN OPEN QUESTION
# EITHER.  Placements 86 and 87 carry CLINE leader 0.  There is no creature
# there to dress; the table says the slot is empty.  Folding them into
# RE-149's five would overstate what that ticket measured, so they are a
# separate class below and are counted separately on the console.
CEILING_TICKET = "RE-149"
CEILING_TICKET_VERDICT = "BOUNDED-NEGATIVE"
CEILING_TICKET_ANSWERED_AT = "2026-08-29T18:14+07:00"

# The five CLINE leader ids RE-149 actually adjudicated.  Written as the
# ticket's own list rather than derived from UNRESOLVED, so that a later edit
# to UNRESOLVED cannot silently enlarge what this ticket is claimed to cover.
CEILING_ADJUDICATED_LEADERS = (155, 819, 937, 942, 9107)

# WHEN THE PIN ABOVE GOES STALE, AND WHY THAT MUST NOT RAISE.
#
# If a regeneration ever RESOLVES one of the five - exactly what happens if a
# new data pack arrives and someone re-runs the census builder - then this
# pinned list describes a question that is no longer open, and RE-149 has to
# be reopened rather than left asserting a ceiling that moved.
#
# The first draft of this block raised ``ValueError`` at import for that,
# matching the ``UNRESOLVED_CLIENT_NAMES`` guard a few lines below.  That was
# wrong, and the difference is worth stating because the two look alike: that
# guard fires when two tables in THIS FILE contradict each other, which is a
# bug and should stop everything.  This one fires when the WORLD IMPROVED -
# five residents Port Royal could not dress became dressable - and this module
# is imported by ``world_population``, which is imported by ``runtime.py``.
# So the raising version's real behaviour was: the day the town gets five
# people back, every player's server refuses to boot.  Taking a live server
# down because a stale citation needs updating is not fail-closed, it is just
# a bigger failure - the same lesson ``lane_hooks._discover()`` writes up
# about its own import path.
#
# So the staleness is RECORDED and travels to the console instead, where a
# human reads it, and the census keeps working the whole time.  Nothing else
# needs to change for it to be correct: a leader that stops being refused
# stops appearing in ``undressable`` at all, so the count simply rises and
# the classifier is never asked about it.
def stale_adjudicated_leaders(refused_leaders) -> tuple[int, ...]:
    """Which of RE-149's five a given refusal table no longer refuses.

    A FUNCTION, not an inline expression, on a mutation finding this round
    (M11): with the derivation written inline at module level, replacing the
    whole thing with a literal ``()`` - which disables staleness detection
    entirely - left every test green, because the only test covering it
    recomputed the same expression itself instead of exercising the module's
    own arrow.  A test can now hand this function a refusal table where one
    of the five HAS been resolved, which is the state that cannot otherwise
    be reached without editing the file.
    """
    return tuple(sorted(set(CEILING_ADJUDICATED_LEADERS) - set(refused_leaders)))


_REFUSED_LEADERS = {leader for leader, _ in UNRESOLVED.values()}
CEILING_TICKET_STALE_LEADERS = stale_adjudicated_leaders(_REFUSED_LEADERS)

# The three reasons a placement in the frozen bg0001 table can have no body,
# kept apart because they have different evidence under them and a different
# way of ever being repaired.
CEILING_CLASS_NO_AVATAR_SOURCE = "no_avatar_source"
CEILING_CLASS_NO_CREATURE = "no_creature"
CEILING_CLASS_NO_OUTFIT_COLUMN = "no_outfit_column"
# A leader that is none of the three.  This is the bucket that matters most:
# it is what a future table change would land in, and it must be LOUD on the
# console rather than absorbed into RE-149's count.  RE-149's answer is about
# five specific ids, not about "whatever the census could not dress today".
CEILING_CLASS_UNADJUDICATED = "unadjudicated"


# The substring of a refusal reason that means what RE-149 actually measured:
# the leader has NO ``CONSTDATA MOBS`` row at all.  The ticket's finding is
# about that state, not about the id.
CEILING_ADJUDICATED_REASON_MARK = "has no CONSTDATA MOBS row"
# And the older, different finding: a leader that HAS a MOBS row whose
# ``s_OUTFIT`` is empty.  Measured long before RE-149 and not part of it.
CEILING_NO_OUTFIT_REASON_MARK = "no s_OUTFIT avatar template"


def ceiling_class_for_placement(template_id: int, leader: int) -> str:
    """Which named reason applies to one refused placement.

    KEYED ON THE RECORDED REASON, NOT ON THE ID ALONE (pf-adversary, this
    round, F4).  The first draft matched ``leader in
    CEILING_ADJUDICATED_LEADERS`` and stopped, which meant RE-149's verdict
    outlived the fact it measured: give leader 155 a MOBS row with an empty
    ``s_OUTFIT`` - a different, already-named state - and the console went on
    citing "no shipped avatar source" for a row nobody had re-measured, with
    nothing on the line to show the drift.  A ticket's finding is about a
    STATE; when the state changes the citation has to stop, even though the
    id has not moved.

    The same finding closed a latent trap: taking a bare ``leader`` int, this
    answered ``no_avatar_source`` just as readily for ``CHANGE_MODEL`` row
    155 - the FIREARM in a different id space that RE-149 names as the
    number-collision temptation - as for the CLINE leader.  Taking the
    Mob-Set number too means the answer is anchored to a row in the table
    this module owns.

    ``CEILING_CLASS_UNADJUDICATED`` for anything the project has not actually
    adjudicated, INCLUDING an id a future regeneration adds to ``UNRESOLVED``
    and an id whose reason has changed out from under the ticket.
    """
    if type(template_id) is not int or type(leader) is not int:
        raise ValueError("template id and leader must be integers")
    if leader == 0:
        return CEILING_CLASS_NO_CREATURE
    entry = UNRESOLVED.get(template_id)
    reason = "" if entry is None else entry[1]
    if (
        leader in CEILING_ADJUDICATED_LEADERS
        and CEILING_ADJUDICATED_REASON_MARK in reason
    ):
        return CEILING_CLASS_NO_AVATAR_SOURCE
    if CEILING_NO_OUTFIT_REASON_MARK in reason:
        return CEILING_CLASS_NO_OUTFIT_COLUMN
    return CEILING_CLASS_UNADJUDICATED


_BY_TEMPLATE = {row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS}

# The longest name a console token may carry.  Bounded because this string
# reaches a log line that a human reads beside twelve other fields, and an
# unbounded field there is how one row hides the rest of them.
ASCII_NAME_LIMIT = 24


def resolve(template_id: int) -> SceneIdentity | None:
    """The identity for a Mob-Set number, or None when it cannot be shipped.

    None is a refusal with a recorded reason (``UNRESOLVED``), never "not
    found": every Mob-Set number the frozen placement table uses is in exactly
    one of the two mappings.
    """
    if type(template_id) is not int:
        raise ValueError("template id must be an integer")
    return _BY_TEMPLATE.get(template_id)


def unresolved_reason(template_id: int) -> str | None:
    """Why a Mob-Set number has no shippable identity, or None if it has one."""
    if type(template_id) is not int:
        raise ValueError("template id must be an integer")
    entry = UNRESOLVED.get(template_id)
    return None if entry is None else entry[1]


def no_set_number_is_shipped_as_identity() -> bool:
    """No resolved identity is its own Mob-Set number.

    HONEST SCOPE (pf-adversary, this round).  This is NOT "the executable form
    of what ``world_scene_numbering`` refuses", and an earlier draft of this
    docstring said it was.  0 of 113 CLINE type-1 rows have leader ==
    creature type, so any table generated from this block satisfies it by
    construction, and an arbitrary WRONG permutation of the 105 identities
    would satisfy it too.  What it does catch is a future regeneration that
    accidentally falls back to the Mob-Set number - which is the specific
    regression ``GT-078`` was, so it is kept, at its real weight.
    """
    return all(row[0] != row[1] for row in _RESOLVED_ROWS)


def identity_console_token(shipped: int, unresolvable: int | None) -> str:
    """The ASCII token the census line carries.  cp874 console: 7-bit only.

    "composed", not "shipped": this counts what THIS module put in the
    collection.  A later splice on the runtime path can replace entries
    afterwards, and on 2026-08-28 one does - so a token that said "shipped"
    would be asserting something this module cannot see (pf-adversary).

    ``unresolvable`` is None for any rung SMALLER than the whole census: a
    20-actor diagnostic rung is short because someone asked for 20, and
    printing "95 unresolvable" beside it would be a lie in the one place a
    boot log is read for the truth.  The identity source is still named, so a
    grep for ``identity=CLINE`` finds every boot either way.
    """
    if type(shipped) is not int:
        raise ValueError("shipped must be an integer")
    if unresolvable is None:
        return "identity=CLINE:%d composed" % shipped
    if type(unresolvable) is not int:
        raise ValueError("unresolvable must be an integer or None")
    return "identity=CLINE:%d composed,%d unresolvable" % (shipped, unresolvable)


def _self_check() -> None:
    """Refuse to import a table that has drifted out of its own claims."""
    if len(_BY_TEMPLATE) != len(_RESOLVED_ROWS):
        raise ValueError("duplicate Mob-Set number in the resolved table")
    overlap = set(_BY_TEMPLATE) & set(UNRESOLVED)
    if overlap:
        raise ValueError(f"Mob-Set number resolved and refused at once: {overlap}")
    if not no_set_number_is_shipped_as_identity():
        raise ValueError(
            "a resolved identity equals its own Mob-Set number - that is the "
            "rule world_scene_numbering refuses; see this module's docstring"
        )
    for row in _RESOLVED_ROWS:
        if type(row[1]) is not int or not 1 <= row[1] <= 0xFFFF:
            raise ValueError(f"identity out of wire range: {row}")
        if type(row[2]) is not str or not row[2]:
            raise ValueError(f"identity with no avatar template: {row}")
        if ";" in row[2]:
            # A variant list would be sent verbatim as a filename.  See
            # MULTI_VARIANT_OUTFITS.
            raise ValueError(f"avatar template is a variant list: {row}")
    for template_id, expected in OWNER_PLACEMENT_ANCHOR_TEMPLATES.items():
        # This one CAN fire and would catch a regenerated or reordered table:
        # the owner confirmed these two by hand and a crosswalk that misses
        # either is not this crosswalk.
        found = _BY_TEMPLATE.get(template_id)
        if found is None or found.mobs_n_id != expected:
            raise ValueError(
                f"owner anchor broken: Mob-Set {template_id} must resolve to "
                f"{expected}, got {found}"
            )
    reachable = {row[1] for row in _RESOLVED_ROWS}
    missing = [n for n in OWNER_VIDEO_CONFIRMED_N_IDS if n not in reachable]
    if missing:
        # The owner saw these on screen.  A table this scene's placements
        # cannot produce them from is the wrong table, not a smaller one.
        raise ValueError(f"owner-confirmed ids unreachable from this scene: {missing}")


_self_check()
