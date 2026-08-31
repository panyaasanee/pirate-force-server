"""Who each Bg0004 placement actually IS - Slave Market Island's real cast.

LANE-A (WORLD).  ``COO-DECISION 2026-08-30T14:41+07:00`` (pf_bridge
``notes_to_chief/20260830_1441_COO-DECISION-scene4-slave-market-first-door.md``)
approved this lane's own recommendation: start the CLINE->MOBS crosswalk for
scene 4 next, of the ten still-shut doors surveyed in round ``12lyda``, because
it has the highest native placement count (116) and already appears as
``world_m2_sea_destination``'s Q_TELEPORT1 second stop.  This module is the
identity half, the same split ``world_bg0015_identity`` /
``world_population_bg0015`` used for Bg0015; ``world_population_bg0004`` is
the census half.

THE CROSSWALK, RE-DERIVED HERE RATHER THAN TAKEN FROM A CITATION.
``SCENE_NAME[s_MODLE_ID=BG0004].n_CLINE_TYPE`` was read directly off the
bridge clone this round (not copied from ``world_bg0015_identity``'s own
cross-scene table, which cites the same number for a different purpose):

    SCENE_NAME[s_MODLE_ID=BG0004].n_ID          = 4
    SCENE_NAME[s_MODLE_ID=BG0004].n_CLINE_TYPE  = 4   (a real value, direct)
    SCENE_NAME[s_MODLE_ID=BG0004].n_SCENE_LV    = 45
    CLINE[(4, <Mob-Set number>)].n_LEADER_BK1   = the real MOBS.n_ID
    MOBS[n_ID].s_OUTFIT                         = the avatar the client loads
    MOBS_TIP[n_ID].s_NAME / s_TITLE             = the label under the actor
    STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX      = max HP (the one derived col)

So this scene takes the exact shape ``world_port_royal_identity`` ships for
scene 1 and ``world_bg0015_identity`` ships for scene 14, with a DIRECT
``n_CLINE_TYPE`` selector (one of RE-128's 19, not one of its 240 instance
scenes) - the same reason M3 could start at Bg0015 without an instance id to
guess.

WHAT IS ESTABLISHED HERE AND WHAT IS NOT, STATED THE SAME WAY THE OTHER TWO
CROSSWALK MODULES STATE IT.

    ESTABLISHED - THE TABLE.  That this scene's cast is drawn from CLINE
    type 4's leader column.  CONTROL 1 below is exact: this scene's
    placements use exactly 55 distinct Mob-Set numbers (1..47 and
    101..108), and every one of the 55 has a row in CLINE type 4.  Six MORE
    keys exist in that block (109..114, all leader 0) that no placement in
    this scene uses - a strictly WIDER block than the scene needs, not an
    exact-key-equality control the way Bg0015's 51-for-51 match was.

    NOT ESTABLISHED - THE PAIRING.  Which leader belongs to which Mob-Set
    number.  No human has stood in this scene (``status:
    never_sent_to_any_client_by_this_project`` in
    ``scenarios/world_scene_registry_001.json``), so unlike Bg0001 there is
    no owner video and no HUD anchor to check a placement against.  Every
    name below is a table inference, the bottom of the evidence order COO
    set on 2026-08-28T21:30, until an attended round looks.

CONTROL 1 - EXACT SUBSET, MEASURED.  The 116 placements resolve to 55
distinct Mob-Set numbers; CLINE type 4 has 61 keys (1..47, 101..114); the
55 the scene uses are exactly {1..47} union {101..108} - every one present,
none missing, and the six keys the scene never touches (109..114) all carry
``n_LEADER_BK1 == 0`` ("no creature"), the same "unused slots have no
creature" shape ``world_port_royal_identity`` and ``world_bg0015_identity``
both use for their own scene's dead placements.

CONTROL 2 - NOT REBUILT HERE, CITED WITH ITS OWN CAVEAT.
``world_bg0015_identity.SCENE_LEVEL_CONTROL['BG0004']`` already carries this
scene's row: ``(4, 45, 52.0, 26.0)`` - CLINE type 4, declared level 45,
CLINE-reading median 52.0, set-number-reading median 26.0.  Re-measuring the
CLINE-reading median THIS round, over the 109 shippable placements (not the
48 distinct sets - the two give different numbers because some sets recur up
to 25 times), gives **53**, not 52.  The one-point gap is not reconciled this
round: that module's own docstring already rates control 2 as WEAK evidence
for the PAIRING (a scrambled table of the same 48 rows reproduces a median
"near" the declared level for ANY permutation, because ``n_CLINE_TYPE``
happens to be monotone in level and equal to the scene id across the whole
project) - so a one-point disagreement between two independent countings is
not read as evidence for or against this table, only recorded so nobody
quotes "52" as this module's own number.

CONTROL 3 - NO SELF-MAPPING, WEAK, SAME CAVEAT AS THE OTHER TWO SCENES.
0 of the 48 resolved rows have ``mobs_n_id == template_id``: keys are
<= 108 and leaders are >= 67 here (with the sole exception of the one
Port-transportation prop, key 1 -> leader 66, which is UNRESOLVED and never
ships), so this control could not fire for any pairing of this table.  It is
a shape check, not evidence, exactly as ``world_bg0015_identity``'s own
docstring says of its own version.

SEVEN OF THE 55 SETS DO NOT RESOLVE, AND THEY COST SEVEN OF THE 116
PLACEMENTS (109 shippable).  Two different reasons, told apart rather than
merged into one count:

* Set 1 -> leader 66, "Port transportation".  MOBS_TIP names it but
  ``CONSTDATA_TH__MOBS`` carries no row for id 66 at all - the identical
  shape Port Royal's set 1 (leader 155, "Port transportation") and Bg0015's
  set 1 (leader 321, same MOBS_TIP name again) both hit.  A boat/dock prop
  that recurs across at least three scenes under the same English name and
  never has a body in this table.
* Sets 101..106 -> leaders 10014..10019.  Every one HAS a ``CONSTDATA MOBS``
  row (so, unlike set 1, this is not "no row at all") but its
  ``s_OUTFIT`` column is empty and it has no ``MOBS_TIP`` row either - the
  same "path-finding helper, not a creature" shape Bg0015's 101..108 block
  (leaders 10063..10070) already carries.  ``make_npc_attr`` formats the
  outfit into ``.\\Data\\GC\\V\\%s.avt``, and an empty basename names a file
  that does not exist, so these seven placements are DROPPED rather than
  sent with an invented preset - [LANE-A ASSUMPTION - AWAITING COO/OWNER
  CONFIRMATION], carried over unchanged from both sibling crosswalks.

ONE SET SHIPS WITH NO NAME, AND IT IS THE SAME SHAPE PORT ROYAL ALREADY
SHIPS.  Set 107 -> leader 917, outfit ``INVISIBLE`` (a real, non-empty
string - this is not the "no s_OUTFIT" refusal above), but MOBS_TIP has no
row for 917 at all, so ``name`` and ``title`` are both empty.
``world_port_royal_identity`` ships the SAME leader id (917, at its own
Mob-Set 98 and 103) the same way - outfit ``INVISIBLE``, empty name, empty
title, shipped rather than refused - because the refusal rule in every one
of this project's crosswalk modules keys on the OUTFIT column, not the name
column.  This scene makes it a bigger fact than Port Royal's two rows: set
107 alone accounts for TWENTY-FIVE of Bg0004's 116 placements (indices
90..114, "Mob_Set_107" instances 01..25), so more than a fifth of this
island is this one invisible, nameless marker repeated - clustered around
two points roughly 6,000-8,000 units apart (one cluster near the scene's own
CLIENT_MARKER_TABLE spawn at -19076/17634, one near +/-2000,17000).  Nobody
has looked at what a real client renders for 25 repeats of an invisible
level-100 rank-0 actor with no name plate; this module ships them because
CHARTER-02 calls for building the known shape around the hole, not for
guessing what 25 invisible markers are for.

NINE SETS LIST TWO AVATAR TEMPLATES SEPARATED BY ';'.  Same rule and the
same open question as scene 1's n_ID 910 and nine of Bg0015's forty-one: ship
the FIRST variant, keep the whole string in ``MULTI_VARIANT_OUTFITS``, and
``_self_check`` refuses at import if a raw ';' ever reaches the shipped
column.  [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION].  Sets 28, 30,
31, 33, 34, 35, 36, 37 and 108 (nine of the 48 resolved sets, accounting for
44 of the 109 shippable placements - set 30 alone recurs nine times, so this
is nearly 40% of the shipped roster, not a corner case).

TWO PLACEMENT ROWS DISAGREE WITH THEMSELVES, NAMED RATHER THAN SILENTLY
PICKED.  The raw placements TSV carries the resolved Mob-Set number TWICE per
row - once inside the free-text ``name`` column (e.g. ``"Mob_Set_34 08"``)
and once in the machine-parsed ``template_ids`` column (``45``) - and
``scene2_prison_exile_tables``'s own docstring records that for Bg0002 the
two always agree (checked for all 106 rows there).  For Bg0004 they do NOT
always agree: placement 82's ``name`` reads ``"Mob_Set_34 08"`` while its
``template_ids``/``set_names`` columns read ``45``/``"Mob_Set_45"``, and
placement 83 the same way (``"Mob_Set_34 09"`` vs. ``46``/``"Mob_Set_46"``).
This module follows ``template_ids`` - the machine-parsed column, not the
free-text label that a level editor's copy-paste could stale without anyone
re-typing it - which is also the column ``field_mob_tables_bg0002.py`` (LANE
B, same source format) already treats as authoritative for its own scene.
Both rows resolve cleanly under 45/46 (leaders 519/246, "Jet cat thieves
No.3"/"No.4"), so the anomaly costs nothing today; it is recorded because a
future re-mine that trusts the ``name`` column instead would silently ship
two placements as "Jet cat thieves" repeats of set 34 ("Sediment Wolf") that
this table never claims.

ONE PLACEMENT CARRIES A SECOND, UNBUILT SPAWN POINT, NAMED AND NOT SHIPPED.
Placement 83's raw row also carries ``extra_triple_count=1`` and a second
XYZ triple (4644.32, -24141.15, 1912.22, about 341 units from its own
primary point) that no other row in this scene carries.  This module ships
ONLY the 116 primary points - the number the owner's own survey and the
scene registry's ``native_placement_count`` both cite - and does not turn
the one extra triple into a 117th actor: whether it means "this Mob-Set has
a second instance the placements TSV's own row count does not reflect" or
something else entirely is not established, and inventing a 117th placement
this round would silently move the round's own stated target.  Recorded in
``EXTRA_TRIPLE_NOT_SHIPPED`` so a later round that wants it has the exact
number rather than a re-scan.

PROVENANCE.  Every row below was generated from these five committed
artifacts and nothing else; the digests are the files as read this round
(2026-08-30, round after ``12lyda``), re-derived rather than copied from a
sibling module's citation of the same four shared tables:

    gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv
    gamedata/tables/CONSTDATA_TH__CLINE.tsv
    gamedata/tables/CONSTDATA_TH__MOBS.tsv
    gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv
    gamedata/tables/CONSTDATA_TH__STANDARD_MOB.tsv
    gamedata/scene/bg0004/bg0004.placements.tsv

THE JOIN, EXACTLY, SO IT CAN BE MECHANISED LATER (this round did it by hand
against committed TSVs read directly, the same discipline
``scene2_prison_exile_tables`` used before a generator existed for it):

    keys   = {r.n_CREATURE_TYPE: r for r in CLINE if r.n_CLINE_TYPE == 4}
    for each Mob-Set number k this scene's placements use (55 of them):
        leader = keys[k].n_LEADER_BK1
        drop k (UNRESOLVED) if leader == 0, or MOBS has no row for it,
            or that row's s_OUTFIT is empty
        else row = (k, keys[k].n_ID, leader, s_OUTFIT.split(';')[0],
                    MOBS_TIP.s_NAME or '', MOBS_TIP.s_TITLE or '',
                    MOBS.n_LEVEL_MIN, MOBS.n_RANK,
                    STANDARD_MOB[n_LEVEL_MIN].n_HPMAX, MOBS.n_MOB_USAGE)
    placements = every row of bg0004.placements.tsv as
        (index, template_ids, running instance count per template_ids,
         x, y, z)

WHAT THIS MODULE DOES NOT CLAIM.

* Not that any of these 109 actors has been SEEN.  No human has been in this
  scene in this project's history (registry ``status:
  never_sent_to_any_client_by_this_project``, and ``login_entry_allowed`` is
  still ``false`` - COO-DECISION 2026-08-30T14:41's own instruction: do not
  flip it until the population component is actually ready).  The
  client-observable layer for this scene is empty; there is no ticket number
  for it yet because nothing is wired to a login path this round.
* Not that this census (built by ``world_population_bg0004``, a sibling
  module, not this one) is what raises these actors on a real server.
  ``RE-128``'s own nonclaim 5 says the roster arithmetic this project
  composes is our design, not the original server's.
* Not leader+crew.  Like both sibling crosswalks this implements
  ``n_LEADER_BK1`` only.  Measured for this scene: 0 of CLINE type 4's 61
  rows carry any ``n_CREW`` value at all, so - like Bg0015 and unlike
  Bg0001's Mob-Set 88 - there is no pet/crew group this reading silently
  drops.
* Not wired.  Registering "bg0004_roster" in
  ``world_scene_travel.CENSUS_SOURCES`` and
  ``world_population_handoff.ROSTER_COMPOSERS`` is deliberately left for a
  later round: this is a multi-round order (COO-DECISION 2026-08-30T14:41),
  and Bg0015's own history shows the identity+census pair landing several
  rounds before its own wiring did.  Until that wiring lands, a player sees
  exactly what they saw yesterday - see the sibling module's handback for
  the exact shape of that wall.
"""
from __future__ import annotations

from dataclasses import dataclass


# Convention marker: shippable, no scenario flag - matching
# world_bg0015_identity's own convention (see that module's comment).
# Nothing in this tree branches on it and no chief-owned file imports this
# module yet.
production_allowed = True
test_only = False

SCENE_N_ID = 4
SCENE_MODEL_ID = "BG0004"
SCENE_CLINE_TYPE = 4
# SCENE_NAME.n_SCENE_LV for this scene.  world_bg0015_identity's own control 2
# table already carries this exact triple (45, 52.0, 26.0); see this module's
# docstring for why the 52.0 does not reproduce from THIS module's own count.
SCENE_DECLARED_LEVEL = 45

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
    "gamedata/scene/bg0004/bg0004.placements.tsv":
        "43ae4a104b760059bba4e7c170bcc7db5af0fcd2b58f50bf1b3613be182e63f5",
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  Costs seven of the 116
# placements.
UNRESOLVED = {
    1: (1600, 66, "no CONSTDATA MOBS row for this n_ID (MOBS_TIP names it: "
        "Port transportation)"),
    101: (1647, 10014, "MOBS row carries no s_OUTFIT avatar template"),
    102: (1648, 10015, "MOBS row carries no s_OUTFIT avatar template"),
    103: (1649, 10016, "MOBS row carries no s_OUTFIT avatar template"),
    104: (1650, 10017, "MOBS row carries no s_OUTFIT avatar template"),
    105: (1651, 10018, "MOBS row carries no s_OUTFIT avatar template"),
    106: (1652, 10019, "MOBS row carries no s_OUTFIT avatar template"),
}

# MOBS rows in this scene that list SEVERAL avatar templates separated by
# ';', as leader n_ID -> the whole string.  The table below ships the FIRST
# variant; ``_self_check`` refuses if a ';' ever reaches the shipped column.
# [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION]
MULTI_VARIANT_OUTFITS = {
    93: "M028_000_000_SP1;M028_000_000_SP2",
    95: "M017_000_001_SP1;M017_000_001_SP2",
    96: "M011_000_002_SP1;M011_000_002_SP2",
    98: "M019_002_000_SP1;M019_002_000_SP2",
    99: "M008_000_001_SP1;M008_000_001_SP2",
    100: "M021_000_001_SP1;M021_000_001_SP2",
    101: "M006_001_001_SP1;M006_001_001_SP2",
    102: "M023_000_001_SP1;M023_000_001_SP2",
    7043: "M024_001_001_SP1;M024_001_001_SP2",
}

# The one placement whose raw row carries a second, unbuilt spawn point.  See
# the module docstring's own section on it.  (placement_index, template_id,
# extra_x, extra_y, extra_z, distance_from_primary_units)
EXTRA_TRIPLE_NOT_SHIPPED = (
    83, 46, 4644.32177734375, -24141.146484375, 1912.2210693359375, 341.0,
)


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
# 48 rows: every Mob-Set number this scene's placements use that CLINE type 4
# resolves to a body.
_RESOLVED_ROWS = (
    (2, 1601, 67, "M055_000_000_N", "Columbus", "Marine Transport Station", 50, 0, 23976, 2),
    (3, 1602, 68, "P_FEMALE_012_000_VENONIKA", "Veronica", "Apprentice Witch", 50, 0, 23976, 2),
    (4, 1603, 69, "M015_000_001_SP3", "Mori Hiroko", "Vagabond Messenger", 50, 0, 23976, 2),
    (5, 1604, 70, "M070_000_000_N", "Wealthy slave buyer", "", 50, 0, 23976, 2),
    (6, 1605, 71, "M001_001_000_SP2", "Lecherous slave buyer", "", 50, 0, 23976, 2),
    (7, 1606, 72, "M068_000_001_SP3", "Battle Arena gambler", "", 50, 0, 23976, 2),
    (8, 1607, 73, "M051_000_001_N", "Angelina", "Princess Slave", 50, 0, 23976, 2),
    (9, 1608, 74, "M073_000_000_N", "Aston", "Slave Traders ", 50, 0, 23976, 2),
    (10, 1609, 75, "P_MALE_003_002_LARGIN", "AstonLarkin", "Fighter Club Chairman", 50, 0, 23976, 2),
    (11, 1610, 76, "M023_000_001_SP1", "Hasan", "Vendor", 50, 0, 23976, 2),
    (12, 1611, 77, "P_MALE_015_000_LING", "Ringer", "Escaped Slave", 50, 0, 23976, 2),
    (13, 1612, 78, "P_MALE_015_000_BERULT", "Beirut", "Passionate Slave", 50, 0, 23976, 2),
    (14, 1613, 79, "P_FEMALE_015_000_MAYA", "Maya", "Beautiful Slave", 50, 0, 23976, 2),
    (15, 1614, 80, "P_MALE_015_000_ZERALTIN", "Salahuddin", "Prince Slaves", 50, 0, 23976, 2),
    (16, 1615, 81, "P_MALE_015_000_SLAVE", "Unwanted slaves", "", 50, 0, 23976, 2),
    (17, 1616, 82, "P_MALE_003_000_DANKEN", "Duncan", "Wounded Fighter", 50, 0, 23976, 2),
    (18, 1617, 83, "P_MALE_003_002_CLOUZE", "Kelas", "Trainer", 50, 0, 23976, 2),
    (19, 1618, 84, "M019_002_000_SP1", "Qina", "Fighter Apprentice ", 50, 0, 23976, 2),
    (20, 1619, 85, "P_MALE_003_000_KAIM", "Kaim", "Novice Fighter ", 50, 0, 23976, 2),
    (21, 1620, 86, "M015_000_001_SP1", "Mori Hiroko", "Vagabond Messenger", 50, 0, 23976, 2),
    (22, 1621, 87, "M076_000_000_N", "Sea Phantom", "Dark Captain", 50, 0, 23976, 2),
    (23, 1622, 88, "P_FEMALE_030_000_KAREN", "Karen", "Female Fighter", 50, 0, 23976, 2),
    (24, 1623, 89, "P_FEMALE_015_000_PETIRA", "Betula", "Panic Slave", 50, 0, 23976, 2),
    (25, 1624, 90, "M073_000_001_N", "Hood", "Shameless Slave Traders ", 50, 0, 23976, 2),
    (26, 1625, 91, "M074_000_001_N", "Local people", "", 50, 0, 23976, 2),
    (27, 1626, 92, "P_FEMALE_015_000_PENNY", "Penny", "Cute Girl Slave", 50, 0, 23976, 2),
    (28, 1627, 93, "M028_000_000_SP1", "Scythe Beetle", "", 46, 1, 18424, 1),
    (29, 1628, 94, "M020_001_000_SP1", "An Gebo Little Firebird", "", 47, 1, 19710, 1),
    (30, 1629, 95, "M017_000_001_SP1", "Dragon Gladiator", "", 48, 1, 21045, 1),
    (31, 1630, 96, "M011_000_002_SP1", "Forest Green Eagle", "", 50, 1, 23976, 1),
    (32, 1631, 97, "M011_000_002_SP3", "Mutant Green Eagle", "", 51, 1, 25564, 1),
    (33, 1632, 98, "M019_002_000_SP1", "Gladiator Slave Girl", "", 52, 1, 27184, 1),
    (34, 1633, 99, "M008_000_001_SP1", "Moor Slime", "", 53, 1, 28904, 1),
    (35, 1634, 100, "M021_000_001_SP1", "Sharp snake poison ivy", "", 54, 1, 30703, 1),
    (36, 1635, 101, "M006_001_001_SP1", "Swamp Tortoise", "", 56, 1, 34530, 1),
    (37, 1636, 102, "M023_000_001_SP1", "Orc", "", 57, 1, 36585, 1),
    (38, 1637, 103, "M023_000_001_SP3", "Orc Chief", "", 58, 1, 38728, 1),
    (39, 1638, 640, "P_FEMALE_003_000_ARENAFIGHTER", "Crazy Rose Regina", "", 105, 0, 228055, 2),
    (40, 1639, 641, "M017_000_001_SP3", "Blood dragon Norman", "", 105, 0, 228055, 2),
    (41, 1640, 234, "MAP001_000_000", "Mirage reel", "", 105, 0, 228055, 2),
    (42, 1641, 235, "MAP001_000_000", "Mirage reel", "", 105, 0, 228055, 2),
    (43, 1642, 236, "BULLETIN_BOARD", "Slave Market Bulletin Board", "", 105, 0, 228055, 2),
    (44, 1643, 744, "M074_000_001_N", "Ventura", "Nomad Maritime", 105, 0, 228055, 2),
    (45, 1644, 519, "M015_001_001_SP1", "Jet cat thieves No.3", "", 50, 1, 23976, 1),
    (46, 1645, 246, "M015_001_001_SP1", "Jet cat thieves No.4", "", 57, 1, 36585, 1),
    (47, 1646, 757, "P_MALE_015_000_ZERALTIN", "Salahuddin", "Liberate", 50, 0, 23976, 2),
    (107, 1653, 917, "INVISIBLE", "", "", 100, 0, 198125, 7),
    (108, 1654, 7043, "M024_001_001_SP1", "Penguin Searcher", "Serious and responsible", 99, 0, 192488, 2),
)

IDENTITIES = {row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS}


@dataclass(frozen=True)
class Bg0004Placement:
    """One Bg0004 placement resolved to a real, named-or-marked, bodied actor."""

    placement_index: int
    template_id: int
    mm_instance: int
    x: float
    y: float
    z: float
    identity: SceneIdentity

    @property
    def actor_identity(self) -> int:
        # The same formula every other scene's census already uses
        # (population.py's SceneActorPlacement.actor_identity).  Never sent
        # in the same generation as another scene's census -- every builder
        # refuses any scene id but its own -- so sharing the numeric space is
        # a collision in the abstract only.  No lane-B module for this scene
        # exists yet (checked this round: 0 files under src/ mention
        # Bg0004/BG0004 outside this pair), so unlike Bg0015 there is no
        # committed sibling table to cross-check for a live collision.
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
# file in file order.  The instance count is computed per Mob-Set number as
# this table is read, NOT copied from the raw TSV's own free-text instance
# suffix -- see the module docstring's "TWO PLACEMENT ROWS DISAGREE WITH
# THEMSELVES" section for why the two are not always the same number.
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
    (82, 45, 1, -11667.541015625, 1527.80126953125, 2557.55078125),
    (83, 46, 1, 4303.18017578125, -24295.369140625, 1912.2210693359375),
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


def identity_for(template_id: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    ``None`` is the seven sets in ``UNRESOLVED`` and nothing else: this
    function never substitutes, and never falls back to the Mob-Set number
    that ``GT-078`` proved wrong on the owner's screen.
    """
    if type(template_id) is not int or type(template_id) is bool:
        raise Bg0004IdentityError("template id must be an int")
    return IDENTITIES.get(template_id)


def shippable_placements() -> tuple[Bg0004Placement, ...]:
    """The 109 placements of the 116 that resolve to a real identity."""
    out = []
    for index, template_id, mm_instance, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(template_id)
        if identity is None:
            continue
        out.append(Bg0004Placement(
            index, template_id, mm_instance, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The seven that are dropped, each with the id and the reason.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH seven and WHY.
    """
    out = []
    for index, template_id, _mm, x, y, z in _PLACEMENT_ROWS:
        if template_id in IDENTITIES:
            continue
        cline_row_id, leader, reason = UNRESOLVED.get(
            template_id, (0, 0, "set not in CLINE 4"))
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
    this scene's keys are all <= 108 and its resolved leaders are all >= 67,
    so this could not fail for any pairing of this table -- it only catches a
    future regeneration that falls back to the Mob-Set number itself, which
    is the specific regression GT-078 was."""
    return all(row[0] != row[2] for row in _RESOLVED_ROWS)


def _self_check() -> None:
    """Refuse at import if this table has drifted out of the shape the
    module docstring claims.  Fail-closed: a bad table must not reach a
    census builder at all, and an ImportError names the file."""
    if len(_RESOLVED_ROWS) != 48:
        raise Bg0004IdentityError(
            "expected 48 resolved sets, found %d" % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg0004IdentityError("duplicate Mob-Set number in the table")
    if len(UNRESOLVED) != 7:
        raise Bg0004IdentityError(
            "expected 7 unresolved sets, found %d" % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg0004IdentityError("a set is both resolved and unresolved")
    if len(_PLACEMENT_ROWS) != 116:
        raise Bg0004IdentityError(
            "expected 116 placements, found %d" % len(_PLACEMENT_ROWS))
    # Control 1: every Mob-Set number this scene's placements use is either
    # resolved or named as unresolved -- a placement keyed by a number this
    # table has never heard of means the placement file and the crosswalk
    # came from different extractions.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if scene_sets != table_sets:
        raise Bg0004IdentityError(
            "placement Mob-Set numbers and this table's keys disagree: %r"
            % sorted(scene_sets ^ table_sets))
    if not no_set_number_is_shipped_as_identity():
        raise Bg0004IdentityError(
            "a row ships its own Mob-Set number as an identity")
    for row in _RESOLVED_ROWS:
        (template_id, cline_row_id, n_id, outfit, name, title, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1:
            raise Bg0004IdentityError(
                "set %d carries no CLINE row locator" % template_id)
        if ";" in outfit:
            raise Bg0004IdentityError(
                "set %d ships a multi-variant outfit string" % template_id)
        if not outfit or not outfit.isascii():
            raise Bg0004IdentityError(
                "set %d has an empty or non-ASCII outfit" % template_id)
        # Name/title MAY be empty (set 107, leader 917, "INVISIBLE" -- the
        # exact shape world_port_royal_identity ships for the same leader id
        # at its own Mob-Set 98/103) but must be ASCII when present -- the
        # bridge console is cp874.
        if not name.isascii() or not title.isascii():
            raise Bg0004IdentityError(
                "set %d has a non-ASCII name or title" % template_id)
        if template_id != 107 and not name:
            raise Bg0004IdentityError(
                "set %d has no display name and is not the known INVISIBLE "
                "exception" % template_id)
        if max_hp < 1 or level < 1:
            raise Bg0004IdentityError("set %d has a bad level/HP" % template_id)
    if len(shippable_placements()) != 109:
        raise Bg0004IdentityError("expected 109 shippable placements")
    if len(unshippable_placements()) != 7:
        raise Bg0004IdentityError("expected 7 unshippable placements")
    ids = [p.actor_identity for p in shippable_placements()]
    if len(ids) != len(set(ids)):
        raise Bg0004IdentityError("actor identities collide within this table")


_self_check()
