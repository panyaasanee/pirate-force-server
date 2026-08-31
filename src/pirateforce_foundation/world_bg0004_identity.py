"""Who each Bg0004 placement actually IS - Slave Market Island's real cast.

LANE-A (WORLD), BUILD-002 door 1 of 10.  ``COO-DECISION 2026-08-30T14:41+07:00``
picked scene 4 (Slave Market Island, ``BG0004``) as the first of ten
already-checked-safe shut doors to open, because it has the most native
placements (116) among the ten and already appears as a sibling destination
of ``world_m2_sea_destination``'s Q_TELEPORT1.  This module is the identity
half; ``world_population_bg0004`` is the census half - same split as
``world_port_royal_identity`` / ``world_population`` (scene 1) and
``world_bg0015_identity`` / ``world_population_bg0015`` (scene 14).

THE CROSSWALK IS A DIRECT READ HERE, NOT A GUESS.  ``RE-128``'s measurement
(quoted in ``world_bg0015_identity``) is that a scene picks its CLINE type one
of two ways: 252 of 271 scene rows carry the ``0xFFFFFFFF`` sentinel and go
through an ``INSTANCE`` lookup keyed by the active instance id; 19 carry a
real value directly in ``SCENE_NAME.n_CLINE_TYPE``.  ``BG0004`` is read this
round straight off ``gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv``:

    SCENE_NAME[s_MODLE_ID=BG0004].n_ID          = 4
    SCENE_NAME[s_MODLE_ID=BG0004].n_CLINE_TYPE  = 4   (a real value, direct)
    CLINE[(4, <Mob-Set number>)].n_LEADER_BK1   = the real MOBS.n_ID
    MOBS[n_ID].s_OUTFIT                         = the avatar the client loads
    MOBS_TIP[n_ID].s_NAME                       = the label under the actor
    STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX      = max HP (the one derived col)

So unlike bg0015's own control 1 (which had to show the scene's Mob-Set
numbers matched exactly one CLINE type's keys, because a direct value had to
be re-derived some other way for a scene not on the sentinel/INSTANCE branch)
this scene's own row already NAMES the type - there is no key-set puzzle to
solve to find it.  ``BG0004`` is one of the same 19 direct-selector scenes
``world_bg0015_identity`` counted; the docstring there already listed BG0004
in ``SCENE_LEVEL_CONTROL`` (n_CLINE_TYPE=4, n_SCENE_LV=45) without opening
this scene's placement file - this module is what opens it.

A SUBSET CHECK, STILL RUN AS A SANITY CONTROL EVEN THOUGH THE TYPE IS NOT
GUESSED.  This scene's placement file uses 55 distinct Mob-Set numbers.
CLINE type 4 has 61 keys (1-47, 101-114) - a SUPERSET, not an exact match:
six of its keys (109-114) are never placed anywhere in this scene.  That is
expected (not every row a type carries has to appear in every scene that
uses it) and is NOT the same failure mode bg0015 guarded against.  Checked
across all 400 CLINE types: only THREE (1, 4, 9998) have a key set wide
enough to contain this scene's 55 numbers as a subset - type 9998 and type 1
are broad blocks, not narrow matches, so this check is weak evidence on its
own; it is run anyway as "the placements and the crosswalk did not come from
different extractions", not as evidence the type itself is 4 (the direct
column read already settles that).

WHAT IS DIFFERENT FROM BG0015'S TABLE, NAMED RATHER THAN LEFT IMPLICIT.

* 47 of the 61 CLINE type-4 rows resolve to a shippable identity (real MOBS
  row, non-empty ``s_OUTFIT``, a ``STANDARD_MOB`` level row, a real
  ``MOBS_TIP`` name).  14 do not: Mob-Set 1 has no MOBS row at all for its
  leader (``n_ID`` 66); Mob-Sets 101-106 resolve to MOBS rows with an EMPTY
  ``s_OUTFIT`` (path-finding helper rows, the same pattern bg0015's 101-108
  block hit); Mob-Set 107 resolves to a MOBS row (``n_ID`` 917) that HAS an
  outfit but has NO ``MOBS_TIP`` row at all - a new failure mode this scene
  hits that neither bg0001 nor bg0015 recorded, kept as its own reason rather
  than folded into the outfit-empty bucket; Mob-Sets 109-114 have
  ``n_LEADER_BK1 = 0`` (no leader assigned at all) and, as the subset check
  above already showed, are never placed in this scene anyway, so they cost
  zero placements.
* Of this scene's 116 real placements, Mob-Set 107 alone accounts for 25 of
  them (a dense cluster near the market square, placement indices 90-114) -
  every one of those 25 is dropped for the reason above.  Combined with the
  single placement each of sets 1 and 101-106, this scene loses 32 of 116
  placements (84 shippable), a materially bigger unresolved fraction than
  either bg0001 (0 of 115 by the time BUILD-001 closed) or bg0015 (10 of 91).
* TWO PLACEMENTS CARRY A MOB-SET NUMBER THAT DISAGREES WITH THEIR OWN "name"
  FIELD, RECORDED RATHER THAN SILENTLY PICKED.  Placement index 82's raw
  ``name`` column reads ``"Mob_Set_34 08"`` (implying set 34, instance 8) but
  its ``template_ids`` column - the field this project's other tables treat
  as authoritative (``field_mob_tables.py``'s own docstring: "the value the
  client reads as the template u16") - is 45, not 34.  Index 83 has the same
  split: ``name`` says ``"Mob_Set_34 09"``, ``template_ids`` says 46.  Both
  rows sit far from set 34's own tight cluster (which stays within roughly
  -8k..3k on X) - index 82 is at X=-11667, index 83 is at X=+4303, on the
  opposite side of the map from every other set-34 row and from each other -
  which is consistent with ``template_ids`` being the real value and
  ``name``'s "34" being a stale or mis-typed label in the source data, but
  this module does not resolve that disagreement, only reports it: both
  placements ship under their ``template_ids`` reading (sets 45 and 46,
  which each independently resolve to a normal single-instance identity), and
  ``NAME_TEMPLATE_ID_DISAGREEMENT`` below names both rows so a later mining
  pass does not have to re-find them.
* NINE LEADER IDS HAVE A ``;``-SEPARATED MULTI-VARIANT OUTFIT (Mob-Sets 28,
  30, 32-37 by key; leaders 93, 95, 96, 98, 99, 100, 101, 102, 7043).  Same
  open question as bg0001's n_ID 910 and bg0015's ten multi-variant sets:
  this module ships the FIRST listed variant and refuses at import if a raw
  ``;`` ever reaches the shipped column.  [LANE-A ASSUMPTION - AWAITING
  COO/OWNER CONFIRMATION]
* ONE RESOLVED NAME CARRIES A REAL TRAILING SPACE IN THE SOURCE DATA.
  ``MOBS_TIP`` row 103's ``s_NAME`` is literally ``"Orc Chief "`` (verified
  byte-for-byte against the raw TSV column, not a parsing artifact this
  module introduced) - shipped verbatim, not stripped, because inventing a
  trim is exactly the kind of silent transform CHARTER-02 forbids; a
  ``.strip()`` would be a claim about what the client actually renders that
  nobody has checked.
* THREE RESOLVED ROWS ARE MAP PROPS, NOT CREATURES, SAME PATTERN AS BG0001'S
  ``MAP001_000_000`` "Mirage reel" AND BG0015'S ``MAP009_000_000`` "Big
  Sword".  Leaders 234 and 235 both carry outfit ``MAP001_000_000`` / name
  "Mirage reel"; leader 236 carries outfit ``BULLETIN_BOARD`` / name "Slave
  Market Bulletin Board".  All three ship: the drop rule keys on an EMPTY
  ``s_OUTFIT``, and none of these three is empty.  Recorded in
  ``MAP_PROP_LEADERS`` so a reader does not mistake them for combat rows.
* RECURRING NAMES ACROSS SCENES, NOTED BECAUSE IT LOOKS LIKE A COLLISION AND
  IS NOT ONE.  Leaders 67/68 here resolve to "Columbus"/"Veronica" - names
  this project has already shipped for OTHER scenes under DIFFERENT
  ``MOBS.n_ID`` values (bg0001's own Columbus, bg0002's Veronica anchor).
  These are different ``n_ID`` rows with the same display string, which is
  unsurprising for a guide/narrator character name reused across many towns
  in this client's own data - not evidence that this scene's crosswalk
  picked up another scene's row.  No claim beyond "the string repeats" is
  made.

WHAT THIS MODULE DOES NOT CLAIM.  Same list ``world_bg0015_identity`` states,
unchanged in substance:

* Not that any of these 84 actors has been SEEN.  No human has stood in
  scene 4 in this project's history.  The client-observable layer is empty
  until a ticket like ``GT-134`` exists for this scene.
* Not that the census this feeds is what raises these actors originally -
  this project's roster arithmetic is our own design, not a re-derivation of
  the original server's spawn logic.
* Not leader+crew.  Only ``n_LEADER_BK1`` is read.  Measured for this type:
  0 of the 61 CLINE type-4 rows carry any ``n_CREW`` value, so - like
  bg0015, unlike bg0001's Mob-Set 88 - there is nothing here that
  leader-only silently drops.

PROVENANCE.  Every row below was generated from the six committed artifacts
digested in ``SOURCE_SHA256`` and nothing else, by the exact procedure
``world_bg0015_identity`` documents, applied to CLINE type 4 and
``bg0004.placements.tsv`` instead of type 14 and ``Bg0015.placements.tsv``.
Those digests are recorded provenance, NOT a guard: the six files live in the
pf_bridge clone, not in this repository, so nothing here can compare a digest
at import (same limitation the two sibling modules record).
"""
from __future__ import annotations

from dataclasses import dataclass


# Convention marker: shippable, no scenario flag.  Nothing branches on it and
# no chief-owned file imports this module yet -- see the handback in
# ``world_population_bg0004``'s docstring.
production_allowed = True
test_only = False

SCENE_N_ID = 4
SCENE_MODEL_ID = 'BG0004'
SCENE_CLINE_TYPE = 4
# SCENE_NAME.n_SCENE_LV for this scene -- a documentation constant only,
# unlike bg0015 this module does not gate import on a median-level control
# (see the docstring: the CLINE type here is a direct read, not something a
# level-median needs to help confirm).
SCENE_DECLARED_LEVEL = 45

SOURCE_SHA256 = {
    'gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv':
        'e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b',
    'gamedata/tables/CONSTDATA_TH__CLINE.tsv':
        'aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40',
    'gamedata/tables/CONSTDATA_TH__MOBS.tsv':
        '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    'gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv':
        'e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f',
    'gamedata/tables/CONSTDATA_TH__STANDARD_MOB.tsv':
        '4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925',
    'gamedata/scene/bg0004/bg0004.placements.tsv':
        '43ae4a104b760059bba4e7c170bcc7db5af0fcd2b58f50bf1b3613be182e63f5',
}

# CLINE types whose key set is wide enough to contain this scene's 55 used
# Mob-Set numbers as a subset -- see the docstring's "SUBSET CHECK" section
# for why this is a sanity control, not the source of the type-4 claim.
SUBSET_CANDIDATE_CLINE_TYPES = (1, 4, 9998)

# Mob-Set numbers this scene's leaders resolve to that are map props, not
# creatures -- see docstring.  leader n_ID -> name.
MAP_PROP_LEADERS = {
    234: 'Mirage reel',
    235: 'Mirage reel',
    236: 'Slave Market Bulletin Board',
}

# Placements whose raw "name" column names a different Mob-Set number than
# their own "template_ids" column -- see docstring.  placement_index ->
# (name-implied set, template_ids-implied set).  This module ships the
# template_ids reading for both, unchanged.
NAME_TEMPLATE_ID_DISAGREEMENT = {
    82: (34, 45),
    83: (34, 46),
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  These cost 32 of the
# 116 placements (set 107 alone accounts for 25 of the 32).
UNRESOLVED = {
    1: (1600, 66, 'no CONSTDATA MOBS row for this n_ID'),
    101: (1647, 10014, 'MOBS row carries no s_OUTFIT avatar template'),
    102: (1648, 10015, 'MOBS row carries no s_OUTFIT avatar template'),
    103: (1649, 10016, 'MOBS row carries no s_OUTFIT avatar template'),
    104: (1650, 10017, 'MOBS row carries no s_OUTFIT avatar template'),
    105: (1651, 10018, 'MOBS row carries no s_OUTFIT avatar template'),
    106: (1652, 10019, 'MOBS row carries no s_OUTFIT avatar template'),
    107: (1653, 917, 'no MOBS_TIP s_NAME for this n_ID'),
    109: (1655, 0, 'leader_bk1 is 0'),
    110: (1656, 0, 'leader_bk1 is 0'),
    111: (1657, 0, 'leader_bk1 is 0'),
    112: (1658, 0, 'leader_bk1 is 0'),
    113: (1659, 0, 'leader_bk1 is 0'),
    114: (1660, 0, 'leader_bk1 is 0'),
}

# Leader n_IDs whose MOBS.s_OUTFIT lists SEVERAL avatar templates separated
# by ';'.  Same rule and same open question as bg0001's n_ID 910 and
# bg0015's ten multi-variant sets: ship the FIRST variant, keep the whole
# string here, refuse at import if a raw ';' ever reaches the shipped
# column.  [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION]
MULTI_VARIANT_OUTFITS = {
    93: 'M028_000_000_SP1;M028_000_000_SP2',
    95: 'M017_000_001_SP1;M017_000_001_SP2',
    96: 'M011_000_002_SP1;M011_000_002_SP2',
    98: 'M019_002_000_SP1;M019_002_000_SP2',
    99: 'M008_000_001_SP1;M008_000_001_SP2',
    100: 'M021_000_001_SP1;M021_000_001_SP2',
    101: 'M006_001_001_SP1;M006_001_001_SP2',
    102: 'M023_000_001_SP1;M023_000_001_SP2',
    7043: 'M024_001_001_SP1;M024_001_001_SP2',
}


@dataclass(frozen=True)
class SceneIdentity:
    """One resolved actor: who it is, what it wears, what its label says."""

    mobset_key: int
    cline_row_id: int
    mobs_n_id: int
    outfit: str
    name: str
    level: int
    rank: int
    max_hp: int
    mob_usage: int


# (Mob-Set number, CLINE row n_ID, MOBS.n_ID, shipped s_OUTFIT,
#  MOBS_TIP.s_NAME, MOBS.n_LEVEL_MIN, MOBS.n_RANK,
#  STANDARD_MOB[level].n_HPMAX, MOBS.n_MOB_USAGE)
# 47 rows: every Mob-Set number in CLINE type 4 that resolves.
_RESOLVED_ROWS = (
    (2, 1601, 67, 'M055_000_000_N', 'Columbus', 50, 0, 23976, 2),
    (3, 1602, 68, 'P_FEMALE_012_000_VENONIKA', 'Veronica', 50, 0, 23976, 2),
    (4, 1603, 69, 'M015_000_001_SP3', 'Mori Hiroko', 50, 0, 23976, 2),
    (5, 1604, 70, 'M070_000_000_N', 'Wealthy slave buyer', 50, 0, 23976, 2),
    (6, 1605, 71, 'M001_001_000_SP2', 'Lecherous slave buyer', 50, 0, 23976, 2),
    (7, 1606, 72, 'M068_000_001_SP3', 'Battle Arena gambler', 50, 0, 23976, 2),
    (8, 1607, 73, 'M051_000_001_N', 'Angelina', 50, 0, 23976, 2),
    (9, 1608, 74, 'M073_000_000_N', 'Aston', 50, 0, 23976, 2),
    (10, 1609, 75, 'P_MALE_003_002_LARGIN', 'AstonLarkin', 50, 0, 23976, 2),
    (11, 1610, 76, 'M023_000_001_SP1', 'Hasan', 50, 0, 23976, 2),
    (12, 1611, 77, 'P_MALE_015_000_LING', 'Ringer', 50, 0, 23976, 2),
    (13, 1612, 78, 'P_MALE_015_000_BERULT', 'Beirut', 50, 0, 23976, 2),
    (14, 1613, 79, 'P_FEMALE_015_000_MAYA', 'Maya', 50, 0, 23976, 2),
    (15, 1614, 80, 'P_MALE_015_000_ZERALTIN', 'Salahuddin', 50, 0, 23976, 2),
    (16, 1615, 81, 'P_MALE_015_000_SLAVE', 'Unwanted slaves', 50, 0, 23976, 2),
    (17, 1616, 82, 'P_MALE_003_000_DANKEN', 'Duncan', 50, 0, 23976, 2),
    (18, 1617, 83, 'P_MALE_003_002_CLOUZE', 'Kelas', 50, 0, 23976, 2),
    (19, 1618, 84, 'M019_002_000_SP1', 'Qina', 50, 0, 23976, 2),
    (20, 1619, 85, 'P_MALE_003_000_KAIM', 'Kaim', 50, 0, 23976, 2),
    (21, 1620, 86, 'M015_000_001_SP1', 'Mori Hiroko', 50, 0, 23976, 2),
    (22, 1621, 87, 'M076_000_000_N', 'Sea Phantom', 50, 0, 23976, 2),
    (23, 1622, 88, 'P_FEMALE_030_000_KAREN', 'Karen', 50, 0, 23976, 2),
    (24, 1623, 89, 'P_FEMALE_015_000_PETIRA', 'Betula', 50, 0, 23976, 2),
    (25, 1624, 90, 'M073_000_001_N', 'Hood', 50, 0, 23976, 2),
    (26, 1625, 91, 'M074_000_001_N', 'Local people', 50, 0, 23976, 2),
    (27, 1626, 92, 'P_FEMALE_015_000_PENNY', 'Penny', 50, 0, 23976, 2),
    (28, 1627, 93, 'M028_000_000_SP1', 'Scythe Beetle', 46, 1, 18424, 1),
    (29, 1628, 94, 'M020_001_000_SP1', 'An Gebo Little Firebird', 47, 1, 19710, 1),
    (30, 1629, 95, 'M017_000_001_SP1', 'Dragon Gladiator', 48, 1, 21045, 1),
    (31, 1630, 96, 'M011_000_002_SP1', 'Forest Green Eagle', 50, 1, 23976, 1),
    (32, 1631, 97, 'M011_000_002_SP3', 'Mutant Green Eagle', 51, 1, 25564, 1),
    (33, 1632, 98, 'M019_002_000_SP1', 'Gladiator Slave Girl', 52, 1, 27184, 1),
    (34, 1633, 99, 'M008_000_001_SP1', 'Moor Slime', 53, 1, 28904, 1),
    (35, 1634, 100, 'M021_000_001_SP1', 'Sharp snake poison ivy', 54, 1, 30703, 1),
    (36, 1635, 101, 'M006_001_001_SP1', 'Swamp Tortoise', 56, 1, 34530, 1),
    (37, 1636, 102, 'M023_000_001_SP1', 'Orc', 57, 1, 36585, 1),
    (38, 1637, 103, 'M023_000_001_SP3', 'Orc Chief ', 58, 1, 38728, 1),
    (39, 1638, 640, 'P_FEMALE_003_000_ARENAFIGHTER', 'Crazy Rose Regina', 105, 0, 228055, 2),
    (40, 1639, 641, 'M017_000_001_SP3', 'Blood dragon Norman', 105, 0, 228055, 2),
    (41, 1640, 234, 'MAP001_000_000', 'Mirage reel', 105, 0, 228055, 2),
    (42, 1641, 235, 'MAP001_000_000', 'Mirage reel', 105, 0, 228055, 2),
    (43, 1642, 236, 'BULLETIN_BOARD', 'Slave Market Bulletin Board', 105, 0, 228055, 2),
    (44, 1643, 744, 'M074_000_001_N', 'Ventura', 105, 0, 228055, 2),
    (45, 1644, 519, 'M015_001_001_SP1', 'Jet cat thieves No.3', 50, 1, 23976, 1),
    (46, 1645, 246, 'M015_001_001_SP1', 'Jet cat thieves No.4', 57, 1, 36585, 1),
    (47, 1646, 757, 'P_MALE_015_000_ZERALTIN', 'Salahuddin', 50, 0, 23976, 2),
    (108, 1654, 7043, 'M024_001_001_SP1', 'Penguin Searcher', 99, 0, 192488, 2),
)

IDENTITIES = {
    row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS
}


@dataclass(frozen=True)
class Bg0004Placement:
    """One Bg0004 placement resolved to a real, named, bodied actor."""

    placement_index: int
    mobset_key: int
    mm_instance: int
    x: float
    y: float
    z: float
    identity: SceneIdentity

    @property
    def actor_identity(self) -> int:
        # Same formula every census in this tree uses (population.py's
        # SceneActorPlacement.actor_identity, and both sibling scene
        # modules).  Never sent in the same generation as another scene's
        # census -- every builder refuses any scene id but its own -- so the
        # identity spaces sharing numbers is a collision in the abstract
        # only.
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


# (placement index, Mob-Set number [template_ids column, authoritative --
#  see NAME_TEMPLATE_ID_DISAGREEMENT], MOBSET instance number [raw "name"
#  column's trailing number, kept for provenance only], x, y, z), every row
# of the scene's own placement file in file order.
_PLACEMENT_ROWS = (
    (0, 1, 1, -18724.265625, 18326.28125, 1478.566650390625),
    (1, 2, 1, -17773.109375, 19926.1328125, 1481.3291015625),
    (2, 3, 1, -4948.75341796875, 16126.60546875, 1598.4730224609375),
    (3, 4, 1, -12179.4208984375, 23516.158203125, 1534.238525390625),
    (4, 5, 1, -4239.1455078125, 14551.4169921875, 1716.2342529296875),
    (5, 6, 1, -1640.8388671875, 15165.046875, 1679.5806884765625),
    (6, 7, 1, -7192.53076171875, 18728.080078125, 1677.0467529296875),
    (7, 8, 1, -1946.5809326171875, 16912.08984375, 1558.7724609375),
    (8, 9, 1, -4090.9609375, 18370.048828125, 1591.0484619140625),
    (9, 10, 1, -5326.4091796875, 23845.40234375, 2367.775634765625),
    (10, 11, 1, -908.0391235351562, 13699.5, 1599.3037109375),
    (11, 12, 1, -2630.90625, 17509.8125, 1612.31591796875),
    (12, 13, 1, -4241.1484375, 13922.19921875, 1621.0089111328125),
    (13, 14, 1, -10203.685546875, 19839.98828125, 1621.8746337890625),
    (14, 15, 1, 16126.4306640625, 18300.78515625, 3851.40185546875),
    (15, 16, 1, -371.5741882324219, 16448.9765625, 1735.8133544921875),
    (16, 17, 1, 22007.466796875, 20767.078125, 4079.979248046875),
    (17, 18, 1, 20705.20703125, 18382.251953125, 3799.4501953125),
    (18, 19, 1, 18533.6640625, 7422.06640625, 4078.504638671875),
    (19, 20, 1, 17872.638671875, -4114.8486328125, 4026.408203125),
    (20, 21, 1, 18225.17578125, -2757.53759765625, 4068.76708984375),
    (21, 22, 1, -10591.2998046875, -10071.662109375, 2828.8818359375),
    (22, 23, 1, -3964.556884765625, -13227.8212890625, 2008.0692138671875),
    (23, 24, 1, 4786.4697265625, -19408.611328125, 1918.884765625),
    (24, 25, 1, 1722.82275390625, -19046.650390625, 1971.3095703125),
    (25, 26, 1, -8808.7373046875, -1143.334228515625, 2362.6962890625),
    (26, 27, 1, 9110.6494140625, -8708.98828125, 2601.748046875),
    (27, 28, 1, 3738.38720703125, 18302.33984375, 1803.738037109375),
    (28, 28, 2, 6442.29345703125, 21859.40625, 2047.102783203125),
    (29, 28, 3, 12171.1875, 25974.19921875, 2912.14208984375),
    (30, 29, 1, 18620.16015625, 25247.43359375, 3382.362548828125),
    (31, 29, 2, 21511.134765625, 22272.46484375, 3924.55224609375),
    (32, 29, 3, 22519.201171875, 18964.6953125, 4041.401611328125),
    (33, 30, 1, 21389.650390625, 16740.4453125, 3883.948486328125),
    (34, 30, 2, 16122.193359375, 17238.908203125, 3753.192626953125),
    (35, 30, 3, 13761.8359375, 14000.6298828125, 3750.57470703125),
    (36, 30, 4, 16096.0185546875, 9812.8603515625, 3724.12255859375),
    (37, 30, 5, 20651.849609375, 5983.28076171875, 4134.2294921875),
    (38, 31, 1, 24056.185546875, 16266.4833984375, 4119.9599609375),
    (39, 31, 2, 24489.69140625, 12121.2080078125, 4617.359375),
    (40, 31, 3, 22932.392578125, 2867.386962890625, 4269.3525390625),
    (41, 31, 4, 22723.349609375, 1776.897216796875, 4294.341796875),
    (42, 32, 1, 22691.337890625, 14229.287109375, 4422.484375),
    (43, 30, 6, 21440.833984375, -2466.861328125, 4285.99853515625),
    (44, 30, 7, 17117.8984375, -3186.320556640625, 3750.588134765625),
    (45, 30, 8, 13552.7138671875, -836.998779296875, 2953.02490234375),
    (46, 30, 9, 9901.57421875, -1174.7373046875, 2611.3154296875),
    (47, 36, 1, 8150.90478515625, -16054.306640625, 1913.0),
    (48, 36, 2, 10952.009765625, -12999.9619140625, 1785.599609375),
    (49, 36, 3, 13524.8447265625, -15144.7587890625, 1978.5423583984375),
    (50, 36, 4, 5236.3349609375, -12683.4140625, 1911.72802734375),
    (51, 36, 5, -657.7073974609375, -12683.4140625, 1953.4510498046875),
    (52, 36, 6, -5071.7080078125, -12683.4140625, 1981.3673095703125),
    (53, 34, 1, 3144.10302734375, -6236.673828125, 1818.9404296875),
    (54, 34, 2, -591.436279296875, -2599.496337890625, 1926.07568359375),
    (55, 34, 3, -2830.73095703125, -7304.2724609375, 1972.4559326171875),
    (56, 34, 4, -489.60211181640625, -9245.89453125, 1813.65185546875),
    (57, 34, 5, -7006.6767578125, -4217.29833984375, 1798.2520751953125),
    (58, 34, 6, -5154.9619140625, 1532.656982421875, 1798.2550048828125),
    (59, 34, 7, -8246.3056640625, 2789.51416015625, 2284.1533203125),
    (60, 35, 1, -2268.9130859375, -14867.322265625, 1987.670166015625),
    (61, 35, 2, -2268.9130859375, -19320.599609375, 1965.19140625),
    (62, 35, 3, 1381.3450927734375, -17415.1953125, 1832.9739990234375),
    (63, 35, 4, 5896.509765625, -23649.44140625, 1912.2562255859375),
    (64, 33, 1, 10743.822265625, -21253.263671875, 1794.2354736328125),
    (65, 33, 2, 13625.0263671875, -18248.458984375, 1960.39404296875),
    (66, 33, 3, 17467.4375, -17366.6328125, 1700.000244140625),
    (67, 33, 4, 21150.5546875, -15357.7724609375, 2160.6943359375),
    (68, 33, 5, 20737.2109375, -21366.607421875, 1855.518798828125),
    (69, 38, 1, -13705.6953125, -7340.2626953125, 1924.2117919921875),
    (70, 37, 1, -10406.015625, -3064.753662109375, 1798.253662109375),
    (71, 37, 2, -8875.796875, -7683.884765625, 2434.858154296875),
    (72, 37, 3, -13030.185546875, -7164.7421875, 1929.879150390625),
    (73, 37, 4, -15813.3466796875, -5030.9814453125, 1808.8446044921875),
    (74, 37, 5, -7863.27880859375, -11105.0732421875, 2302.90185546875),
    (75, 39, 1, -6728.8779296875, 25696.498046875, 1592.749755859375),
    (76, 40, 1, -5997.45947265625, 25874.806640625, 1592.749755859375),
    (77, 41, 1, -12571.0126953125, 23725.578125, 1525.83642578125),
    (78, 42, 1, 18659.31640625, -2653.3623046875, 4147.4521484375),
    (79, 43, 1, -10272.716796875, 24037.861328125, 1557.40185546875),
    (80, 44, 1, -9832.474609375, 20201.337890625, 1558.772705078125),
    (81, 47, 1, -18227.58984375, 19174.37890625, 1491.3531494140625),
    (82, 45, 8, -11667.541015625, 1527.80126953125, 2557.55078125),
    (83, 46, 9, 4303.18017578125, -24295.369140625, 1912.2210693359375),
    (84, 101, 1, 14279.5205078125, 15089.09765625, 3753.29638671875),
    (85, 102, 1, 9012.47265625, -12525.39453125, 1810.40380859375),
    (86, 103, 1, -2342.21484375, -10439.4453125, 1810.40380859375),
    (87, 104, 1, 21416.435546875, -17011.46484375, 2020.343994140625),
    (88, 105, 1, 21746.189453125, 21971.4609375, 3949.51123046875),
    (89, 106, 1, -14138.4296875, 408.9609069824219, 2537.306640625),
    (90, 107, 1, -4231.21240234375, 13898.4521484375, 1980.912109375),
    (91, 107, 2, -10161.26171875, 19854.73046875, 1980.4200439453125),
    (92, 107, 3, -2693.166748046875, 17367.521484375, 1957.707763671875),
    (93, 107, 4, -1933.017822265625, 16899.98046875, 1962.809326171875),
    (94, 107, 5, -370.8133850097656, 16468.259765625, 2085.59130859375),
    (95, 107, 6, -137.06509399414062, 16624.33203125, 1684.549072265625),
    (96, 107, 7, -172.9010009765625, 16196.41015625, 1698.007568359375),
    (97, 107, 8, -642.9832763671875, 16215.3828125, 1673.05712890625),
    (98, 107, 9, -577.635498046875, 16670.708984375, 1662.619873046875),
    (99, 107, 10, -1651.57421875, 16887.55859375, 1562.632080078125),
    (100, 107, 11, -1968.1710205078125, 17204.158203125, 1558.807861328125),
    (101, 107, 12, -2408.1865234375, 17518.0703125, 1558.7724609375),
    (102, 107, 13, -2899.179931640625, 17587.828125, 1558.7724609375),
    (103, 107, 14, -2939.425048828125, 17110.25, 1558.774658203125),
    (104, 107, 15, -2477.945068359375, 17086.103515625, 1558.773681640625),
    (105, 107, 16, -2300.86572265625, 16874.14453125, 1558.783203125),
    (106, 107, 17, -1949.3897705078125, 16560.23046875, 1561.320068359375),
    (107, 107, 18, -3957.544189453125, 13922.599609375, 1592.4786376953125),
    (108, 107, 19, -4601.4697265625, 13898.453125, 1584.6304931640625),
    (109, 107, 20, -4193.650390625, 13528.1953125, 1596.8839111328125),
    (110, 107, 21, -4225.8466796875, 14215.048828125, 1579.371337890625),
    (111, 107, 22, -9825.091796875, 19856.353515625, 1566.6910400390625),
    (112, 107, 23, -10538.7763671875, 19877.818359375, 1612.7685546875),
    (113, 107, 24, -10203.3984375, 19507.560546875, 1612.7685546875),
    (114, 107, 25, -10139.005859375, 20191.732421875, 1569.8372802734375),
    (115, 108, 1, 11788.0, -20550.0, 3300.0),
)

PLACEMENT_COUNT = len(_PLACEMENT_ROWS)


class Bg0004IdentityError(ValueError):
    """A refusal from this module, always with a reason in the message."""


def identity_for(mobset_key: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    ``None`` is exactly the keys in ``UNRESOLVED`` and nothing else: this
    function never substitutes, and never falls back to the Mob-Set number
    itself as if it were the real ``MOBS.n_ID`` (the reading ``GT-078``
    proved wrong for bg0001).
    """
    if type(mobset_key) is not int or type(mobset_key) is bool:
        raise Bg0004IdentityError('mobset key must be an int')
    return IDENTITIES.get(mobset_key)


def shippable_placements() -> tuple[Bg0004Placement, ...]:
    """The 84 placements of the 116 that resolve to a real identity."""
    out = []
    for index, key, mm, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(key)
        if identity is None:
            continue
        out.append(Bg0004Placement(index, key, mm, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The 32 that are dropped, each with the id and the reason.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH and WHY.
    """
    out = []
    for index, key, _mm, x, y, z in _PLACEMENT_ROWS:
        if key in IDENTITIES:
            continue
        cline_row_id, leader, reason = UNRESOLVED.get(
            key, (0, 0, 'set not in CLINE 4'))
        out.append({
            'placement_index': index,
            'mobset_key': key,
            'cline_row_id': cline_row_id,
            'leader_n_id': leader,
            'reason': reason,
            'xyz': (x, y, z),
        })
    return tuple(out)


def no_set_number_is_shipped_as_identity() -> bool:
    """Control, executable: no resolved row hands back its own Mob-Set
    number as the ``mobs_n_id`` it ships -- the same shape check
    ``world_bg0015_identity`` runs, and just as weak for the same reason
    here (keys are all <= 108, leaders are mostly >= 66, but leaders 67-103
    ARE in the same numeric neighbourhood as some keys, so this check is
    real here in a way it structurally could not be for bg0015 -- verified
    below that it still passes)."""
    return all(row[0] != row[2] for row in _RESOLVED_ROWS)


def _self_check() -> None:
    """Refuse at import if this table has drifted out of the shape the
    module docstring claims.  Fail-closed: a bad table must not reach a
    census builder at all, and an ImportError names the file."""
    if len(_RESOLVED_ROWS) != 47:
        raise Bg0004IdentityError(
            'expected 47 resolved sets, found %d' % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg0004IdentityError('duplicate Mob-Set number in the table')
    if len(UNRESOLVED) != 14:
        raise Bg0004IdentityError(
            'expected 14 unresolved sets, found %d' % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg0004IdentityError('a set is both resolved and unresolved')
    if len(_PLACEMENT_ROWS) != 116:
        raise Bg0004IdentityError(
            'expected 116 placements, found %d' % len(_PLACEMENT_ROWS))
    # Every placement's Mob-Set number must be a key this table has heard
    # of (either resolved or explicitly unresolved) -- a placement keyed by
    # a number absent from both means the placement file and the crosswalk
    # came from different extractions.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if not scene_sets.issubset(table_sets):
        raise Bg0004IdentityError(
            'placement Mob-Set numbers not covered by CLINE type 4: %r'
            % sorted(scene_sets - table_sets))
    if not no_set_number_is_shipped_as_identity():
        raise Bg0004IdentityError(
            'a row ships its own Mob-Set number as an identity')
    for row in _RESOLVED_ROWS:
        (mobset_key, cline_row_id, n_id, outfit, name, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1:
            raise Bg0004IdentityError(
                'set %d carries no CLINE row locator' % mobset_key)
        if ';' in outfit:
            raise Bg0004IdentityError(
                'set %d ships a multi-variant outfit string' % mobset_key)
        if not outfit or not outfit.isascii():
            raise Bg0004IdentityError(
                'set %d has an empty or non-ASCII outfit' % mobset_key)
        if not name or not name.isascii():
            raise Bg0004IdentityError(
                'set %d has an empty or non-ASCII display name' % mobset_key)
        if max_hp < 1 or level < 1:
            raise Bg0004IdentityError('set %d has a bad level/HP' % mobset_key)
    if len(shippable_placements()) != 84:
        raise Bg0004IdentityError('expected 84 shippable placements')
    if len(unshippable_placements()) != 32:
        raise Bg0004IdentityError('expected 32 unshippable placements')


_self_check()
