"""Who each Bg0015 placement actually IS - Hell Volcano Island's real cast.

LANE-A (WORLD), M3.  ``COO-DECISION 2026-08-28T22:50+07:00`` ("M2 stays
paused, M3 walks without that door") assigns this lane the server side of
Bg0015's population and forbids one line of boat/travel code with it.  This
module is the identity half; ``world_population_bg0015`` is the census half.

THE CROSSWALK, AND WHY THIS SCENE MAY USE THE DIRECT FORM.  ``RE-128``'s
second result (RE runner, 2026-08-28T23:14+07:00, PASS/DONE) measured that
the client picks a scene's ``n_CLINE_TYPE`` down TWO branches at
``[0x0043AA16,0x0043AAA4)``: a normal scene reads ``SCENE_NAME``; an
instance scene reads ``INSTANCE`` keyed by the active instance id.
Re-derived here rather than quoted: **252** of the 271 scene rows carry the
``0xFFFFFFFF`` sentinel and only **19** have a direct selector.  (The
RE-128 note's "240" is the subset of those 252 that DO have an ``INSTANCE``
row - 7 of the 252 have neither, so "every sentinel scene must go the second
way" is false as well.  Both numbers were quoted from the note in this
module's first draft instead of being recomputed; pf-adversary caught it.)
Bg0015 is one of the 19:

    SCENE_NAME[s_MODLE_ID=Bg0015].n_ID          = 14
    SCENE_NAME[s_MODLE_ID=Bg0015].n_CLINE_TYPE  = 14   (a real value, direct)
    CLINE[(14, <Mob-Set number>)].n_LEADER_BK1  = the real MOBS.n_ID
    MOBS[n_ID].s_OUTFIT                         = the avatar the client loads
    MOBS_TIP[n_ID].s_NAME                       = the label under the actor
    STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX      = max HP (the one derived col)

So this scene takes exactly the shape ``world_port_royal_identity`` already
ships for scene 1, with no instance-id input to guess - which is why this
lane started M3 here rather than at a scene from the 240.

WHAT IS ESTABLISHED HERE AND WHAT IS NOT.  Read this before any number
below.  ``pf-adversary`` (round w0pu2i) broke the first draft of this section
and the honest split it forced is:

    ESTABLISHED - THE TABLE.  That this scene's cast is drawn from CLINE
    type 14's leader column.
    NOT ESTABLISHED - THE PAIRING.  Which leader belongs to which Mob-Set
    number, i.e. every one of the 81 sentences ``actor_lines()`` prints.

Everything in the controls below is invariant under permuting the 51 rows
of the table.  The adversary demonstrated it rather than argued it: a fully
scrambled ``_RESOLVED_ROWS`` (same keys, payloads randomly re-paired)
imports cleanly through ``_self_check`` and still passes every control -
2,000 random permutations put the median level at 105 in 87% of draws and
at or above 100 in 100% of them.  So the guard in ``_self_check`` that
compares the cast median against the declared scene level CANNOT FIRE for
any shuffle of this table.  It is a check that the right BLOCK was picked,
and nothing else.  Do not quote it as evidence for a name over a body.

CONTROL 1 - EXACT SET EQUALITY.  [MEASURED]  The 91 placements use 51
distinct Mob-Set numbers - 1..36 and 101..115 - and CLINE type 14 has
exactly those 51 keys, no more and no fewer.  This is the strongest thing
in this file, and the adversary re-derived it independently: over all 400
CLINE types and all 266 scenes with usable set numbers, restricted to
scenes with 10 or more distinct sets, exact key equality happens in 32 of
19,200 pairings - 0.17%.  Bg0015's key set matches exactly ONE of the 400
types, and it is 14.  SCOPE: this identifies the TABLE.  It is a property
of ``n_CREATURE_TYPE`` alone, so it says nothing about which COLUMN of that
table is the identity (``n_LEADER_BK1`` vs ``BK2`` vs ``n_TACTIC_AI``) and
nothing about the pairing.

CONTROL 2 - THE SCENE-LEVEL COMPARISON.  [PROPOSED, NOT MEASURED EVIDENCE
FOR THE PAIRING]  ``SCENE_NAME.n_SCENE_LV`` here is 100; the CLINE-resolved
cast's median ``n_LEVEL_MIN`` is 105; reading the Mob-Set number straight as
a ``MOBS.n_ID`` - what this tree used to do - gives 20.  Run both readings
over EVERY scene with a direct selector and a nonzero declared level.  There
are FOURTEEN (see ``SCENE_LEVEL_CONTROL``, which carries all fourteen), and
the rows that go against this module are printed first on purpose:

    scene    CLINE type   n_SCENE_LV   CLINE median   set-number median
    BG0003          3         25           35              20
    Bg3002       3002         70            1              20
    Bg3003       3003         92            1              20
    Bg3007       3007         30            1              27
    Bg3008       3008         80            1              20
    BG0004          4         45           52              26
    BG0005          5         60           68              35
    Bg0006          6         70           77.5            20
    Bg0007          7         81           81              20
    Bg0008          8         86           87              20
    Bg0009          9         92           93              20
    Bg0010         10         92           99              20
    Bg0011         11         95           99              20
    Bg0015         14        100          105              20

THREE THINGS THAT KILL THE STRONG READING OF CONTROL 2, all found by
pf-adversary, all reproduced:

  a. It is not a control over 14 scenes and ~1,000 placements.  It is a
     control over 14 numbers.  Take the median leader level of a whole CLINE
     block WITHOUT OPENING ANY PLACEMENT FILE and the column reproduces
     (type 4 -> 50, 7 -> 86, 11 -> 99, 14 -> 105).  Feed Bg0015's own 91
     placements into CLINE type 4 and you get 50; feed BG0004's 116 into
     type 14 and you get 105.  The placement file contributes nothing:
     ``n_CLINE_TYPE`` happens to be monotone in level and equal to the scene
     id, so ANY statistic keyed on the type index "tracks" the level.
  b. BG0003 breaks the band this module first claimed.  It is not a 3000
     scene - it is a plain island (``n_SCENE_TYPE=2``) and it is the only
     OTHER scene in the whole dataset with 51 distinct sets and exact key
     equality, i.e. Bg0015's closest structural twin.  There the CLINE
     reading is off by +10 (outside the 0..8 band the first draft asserted)
     and the set-number reading is closer.  The band was a post-hoc property
     of the rows that survived a selection this module made without saying so.
  c. The 3000 block resolves to SHIPS: type 3002's leaders are Utopia,
     Yamato, Santa Maria, Skull Phantom, with ``s_OUTFIT`` in the ``SP_``
     family (28 of that block's 58 rows) and 37 of 58 at level 1, while the
     land types carry no ``SP_`` outfit at all (0 of 51 in type 14, 0 of 61
     in type 4, 0 of 41 in type 10).  That is a visible family difference,
     not an explanation, and this module does not claim to have explained it.

  The half of control 2 that survives every scene, sea and land: the
  set-number reading gives ~20 on all fourteen, so IT carries no scene
  information either.  That is an argument against the old reading.  It is
  not an argument for this one's pairing.

CONTROL 3 - NO SELF-MAPPING.  [MEASURED, AND WEAK]  0 of the 51 rows have
``n_LEADER_BK1 == n_CREATURE_TYPE``.  The adversary's note is fair: keys are
<= 115 and leaders are >= 321 here, so this control could never have fired
for ANY pairing of this table.  It is a shape check, not evidence.

CONTROL 4 - THE CAST READS AS THIS SCENE'S CAST.  [PROPOSED, AND SHOWN
NON-DISCRIMINATING]  The scene is the Hell Volcano Island and the roster is
Hell Ghoul x11, Glaucoma x6, Blood red eagle x5, Phosphor powder Banshee x5,
Angelina x4, Sea Phantom x4, Earth Flame Dragon x4, Hell King Kong x3,
Red Flame Demon Wolf x3, Hell Dragon Majin x2, plus named level-104..115
figures (Dante "Mad King", Carlos, Val'kyr, Angelina, Siren) and Baroque
"Dragon Blood Lord" at level 105.  The set-number reading gives level 25-27
"Tornado Eagle"/"Fighting Fish soldier" here, the same low-level coastal
cast it gives for every other scene.  BUT: the adversary ran three scrambled
tables through this smell test and all three still "read as a Hell island"
(seed 3 leads with Angelina x18, seed 11 with Hell King Kong x11, seed 42
with Love bathing Banshee x11).  It discriminates between TABLES.  It does
not discriminate between PAIRINGS.

THE ROW THAT FAILS CONTROL 4, named because the adversary had to find it
rather than reading it here.  Set 111 -> ``MOBS.n_ID`` 923, "Big Sword",
``s_OUTFIT`` ``MAP009_000_000``, level 1, ``n_AI_COMBAT`` 0, HP 106.  That
is a map prop, and it ships, at placement 84.  The drop rule below does not
see it because its ``s_OUTFIT`` is not empty - it is a ``MAP*`` basename.
Port Royal ships ``MAP001_000_000`` "Mirage reel" the same way, so this is a
pre-existing pattern rather than a regression, and this module does NOT add
a rule to drop it: a new drop rule with no control under it is exactly what
this round has just been beaten for.  It is recorded, it is in
``MAP_PROP_ROWS``, and ``GT-134`` tells the tester to expect one level-1
"Big Sword" among the level-105 monsters.

A COLUMN THIS ROUND DID NOT OPEN, and the adversary is right that it is
worth more than a median: ``MOBS.n_MOB_USAGE`` splits these 41 rows cleanly
- 16 rows at usage 1 (exactly the level-105 monsters, n_ID 340..355) and 25
at usage 2 (the named 110s, and 923).  It is carried on every row below as
``mob_usage`` so the next round can use it; nothing branches on it today.

SO WHAT WOULD ACTUALLY TEST THE PAIRING?  Named here because the adversary
asked it and this module cannot answer it: a per-row locator that a second
party can re-open (added this round - every row carries its ``CLINE.n_ID``),
the scene's native ``.npc`` digest (not in this clone), an independent table
that ties one set number to one ``MOBS.n_ID`` (a mission or drop table -
not searched yet), or ``GT-134``.  Until one of those lands, the 81 sentences
this module ships are a hypothesis with a strong table under it and nothing
under the assignment.

WHAT THIS MODULE DOES NOT CLAIM.

* Not that any of these 81 actors has been SEEN.  No human has been in THIS
  scene in this project's history.  (Careful with the stronger sentence the
  first draft used - "scene_id has never been anything but 1 on a real boot"
  is false: the owner's attended M1-P boot on 2026-08-28T00:3x+07:00 logged
  ``WORLD_SCENE scene_id=2 model=BG0002``, which is the very evidence
  COO-DECISION 2026-08-28T22:50 used to promote scene 2.  Scene 14 is the
  one nobody has stood in.)  The client-observable layer for this scene is
  empty and
  the ticket that fills it is ``GT-134``.  Until it comes back, every name
  below is a table inference - the bottom of the evidence order COO set on
  2026-08-28T21:30 - however good the four controls above are.
* Not that the census this feeds is what raises these actors.  ``RE-128``'s
  own nonclaim 1 says the map-list consumer it measured is not proof that a
  runtime spawn path builds the same set, and its nonclaim 5 says the roster
  arithmetic this project composes is our design, not the original server's.
* Not leader+crew.  Like scene 1's module this implements ``n_LEADER_BK1``
  only.  Measured for this scene: 0 of the 51 CLINE type-14 rows carry any
  ``n_CREW`` value, so unlike bg0001 (where Mob-Set 88 hides six pets) there
  is nothing here that leader-only silently drops.

TEN SETS DO NOT RESOLVE, AND THEY COST TEN OF THE 91 PLACEMENTS.  Set 1
converts to n_ID 321, which has a ``MOBS_TIP`` name ("Port transportation")
but no ``CONSTDATA MOBS`` row.  It is NOT the same id scene 1 cannot ship -
that one is 155, and 321 appears nowhere in Port Royal's table; the two
share a NAME, not an id (first draft said "the same id"; pf-adversary caught
it).  Sets 101..108 convert to 10063..10070, which have MOBS rows carrying
no ``s_OUTFIT`` at all; those ids have NO ``MOBS_TIP`` row at all, and the
Chinese strings naming path-finding helpers are in ``CONSTDATA MOBS.s_NAME``
- a different table from the one the first draft named.  Set 115 converts to
944, no MOBS row.
[LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION], carried over from
scene 1 unchanged: an entry with no avatar template is DROPPED rather than
sent with some substitute, because ``make_npc_attr`` formats the outfit into
".\\Data\\GC\\V\\%s.avt" and an empty or invented basename names a file that
does not exist.  pf-adversary's counter-argument from last round still
stands and is still unanswered: a dropped actor produces no owner feedback,
and every identity error in this project so far was corrected because the
owner SAW it.  ``UNRESOLVED`` names all ten with the reason, and the census
console line prints the shortfall as 81/91 every boot rather than quietly
retargeting (CHARTER-02).

TEN MORE SETS LIST SEVERAL AVATAR TEMPLATES separated by ';' (all pairs,
e.g. 354 Hell Ghoul = 'M023_001_000_SP1;M023_001_000_SP2').  Same rule and
same open question as scene 1's n_ID 910: ship the FIRST variant, keep the
whole string in ``MULTI_VARIANT_OUTFITS``, and refuse at import if a raw
';' ever reaches the shipped column.  [LANE-A ASSUMPTION - AWAITING
COO/OWNER CONFIRMATION].  This scene makes the question ten times louder
than scene 1 did: 45 of the 81 shipped placements are a multi-variant set,
so if the original server alternated variants per spawn, more than half this
island is wearing one skin where it should wear two.

SIX SETS (109..114) HAVE A THAI ``s_TITLE`` in ``MOBS_TIP``.  This module
carries no title column at all - the wire entry ``world_population_bg0015``
builds sends ``s_NAME`` only - so nothing here is lost by keeping every
literal in this file ASCII, which the bridge console (cp874) requires.

PROVENANCE.  Every row below was generated from the six committed artifacts
digested in ``SOURCE_SHA256`` and nothing else, by this procedure, which is
the whole generator:

    keys   = {r.n_CREATURE_TYPE: r for r in CLINE if r.n_CLINE_TYPE == 14}
    for each key k, leader = keys[k].n_LEADER_BK1
        drop k if leader == 0, or MOBS has no row for it, or that row's
        s_OUTFIT is empty, or STANDARD_MOB has no row for its n_LEVEL_MIN
        else row = (k, leader, s_OUTFIT.split(';')[0], MOBS_TIP.s_NAME,
                    n_LEVEL_MIN, n_RANK, STANDARD_MOB[n_LEVEL_MIN].n_HPMAX)
    placements = every row of Bg0015.placements.tsv as
        (index, template_ids, trailing number of `name`, x, y, z)

Those digests are recorded provenance, NOT a guard: the six files live in
the pf_bridge clone, not in this repository, so nothing here can compare a
digest at import (same limitation ``world_port_royal_identity`` records).
"""
from __future__ import annotations

from dataclasses import dataclass


# Convention marker: shippable, no scenario flag.  Nothing branches on it and
# no chief-owned file imports this module yet -- see the handback in
# ``world_population_bg0015``'s docstring.
production_allowed = True
test_only = False

SCENE_N_ID = 14
SCENE_MODEL_ID = 'Bg0015'
SCENE_CLINE_TYPE = 14
# SCENE_NAME.n_SCENE_LV for this scene.  Control 2 in the module docstring
# compares the resolved cast's median level against this number.
SCENE_DECLARED_LEVEL = 100

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
    'gamedata/scene/Bg0015/Bg0015.placements.tsv':
        '8ef794f9ccbeae1154eb8466c3e43c3d605ca6a620e2e5c936e0af46cb51bb83',
}

# Control 2, executable, and carrying every row - including the five that
# go against this module.  scene model id -> (CLINE type, n_SCENE_LV,
# CLINE-reading median level, set-number-reading median level).  ALL
# FOURTEEN scenes with a direct SCENE_NAME selector and a nonzero declared
# level are here.  The first draft carried eight and called it "every scene
# that has both"; the six it missed lived under differently-cased scene
# directories (scene/Bg0003/bg0003.placements.tsv), and five of the six
# break the claim the first draft made.  Selecting the comparison group on
# the answer is the mistake that killed this lane's dense/sparse rule; it is
# not being made twice, so the disagreeing rows are listed FIRST.
SCENE_LEVEL_CONTROL = {
    # --- against this module ---
    'BG0003': (3, 25, 35.0, 20.0),     # +10, outside any band; set-number wins
    'Bg3002': (3002, 70, 1.0, 20.0),   # ship block
    'Bg3003': (3003, 92, 1.0, 20.0),   # ship block
    'Bg3007': (3007, 30, 1.0, 27.0),   # ship block
    'Bg3008': (3008, 80, 1.0, 20.0),   # ship block
    # --- with this module ---
    'BG0004': (4, 45, 52.0, 26.0),
    'BG0005': (5, 60, 68.0, 35.0),
    'Bg0006': (6, 70, 77.5, 20.0),
    'Bg0007': (7, 81, 81.0, 20.0),
    'Bg0008': (8, 86, 87.0, 20.0),
    'Bg0009': (9, 92, 93.0, 20.0),
    'Bg0010': (10, 92, 99.0, 20.0),
    'Bg0011': (11, 95, 99.0, 20.0),
    'Bg0015': (14, 100, 105.0, 20.0),
}
# The five scenes where the CLINE reading is NOT closer to the declared
# level than the set-number reading.  Kept as data so a test can assert the
# exceptions still exist: if a regeneration ever makes them quietly vanish,
# that is a regeneration to distrust, not a result to celebrate.
SCENE_LEVEL_CONTROL_AGAINST = ('BG0003', 'Bg3002', 'Bg3003', 'Bg3007', 'Bg3008')

# NULL A (pf-adversary, round w0pu2i).  The same column reproduces from the
# CLINE block alone, with no placement file opened at all - so control 2
# measures the block, not this scene's placements.  CLINE type -> median
# leader level over the whole block.
SCENE_LEVEL_CONTROL_NULL_A = {
    3: 35.0, 4: 50.0, 5: 70.0, 6: 80.0, 7: 86.0, 8: 87.0, 9: 98.0,
    10: 99.0, 11: 99.0, 14: 105.0,
    3002: 1.0, 3003: 1.0, 3007: 1.0, 3008: 1.0,
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  These cost ten of the
# 91 placements.  The CLINE row id is here for the same reason it is on the
# resolved rows: so a reader can open the row instead of trusting this file.
UNRESOLVED = {
    1: (3400, 321, 'no CONSTDATA MOBS row for this n_ID'),
    101: (3436, 10063, 'MOBS row carries no s_OUTFIT avatar template'),
    102: (3437, 10064, 'MOBS row carries no s_OUTFIT avatar template'),
    103: (3438, 10065, 'MOBS row carries no s_OUTFIT avatar template'),
    104: (3439, 10066, 'MOBS row carries no s_OUTFIT avatar template'),
    105: (3440, 10067, 'MOBS row carries no s_OUTFIT avatar template'),
    106: (3441, 10068, 'MOBS row carries no s_OUTFIT avatar template'),
    107: (3442, 10069, 'MOBS row carries no s_OUTFIT avatar template'),
    108: (3443, 10070, 'MOBS row carries no s_OUTFIT avatar template'),
    115: (3450, 944, 'no CONSTDATA MOBS row for this n_ID'),
}

# MOBS rows in this scene that list SEVERAL avatar templates separated by
# ';', as leader n_ID -> the whole string.  The table below ships the FIRST
# variant; ``_self_check`` refuses if a ';' ever reaches the shipped column.
# [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION]
MULTI_VARIANT_OUTFITS = {
    340: 'M005_001_000_SP1;M005_001_000_SP2',
    341: 'M011_000_001_SP1;M011_000_001_SP2',
    342: 'M004_000_001_SP1;M004_000_001_SP2',
    344: 'M022_000_001_SP1;M022_000_001_SP2',
    346: 'M005_000_002_SP1;M005_000_002_SP2',
    347: 'M000_001_001_N;M000_001_001_SP1',
    349: 'M017_000_002_SP1;M017_000_002_SP2',
    351: 'M006_001_000_SP1;M006_001_000_SP2',
    352: 'M003_000_003_SP1;M003_000_003_SP2',
    354: 'M023_001_000_SP1;M023_001_000_SP2',
}

# Sets whose MOBS_TIP row carries a Thai s_TITLE.  Recorded as numbers, not
# as text, so every literal in this file stays ASCII (bridge console cp874).
# No title is sent on the wire, so nothing is lost by not carrying them.
THAI_TITLE_SETS = (109, 110, 111, 112, 113, 114)

# Rows whose avatar template is a MAP* basename - a map prop, not a
# creature.  Found by pf-adversary, not by this module's own controls, which
# is the point of recording it here.  These SHIP: the drop rule below keys
# on an EMPTY s_OUTFIT and a MAP* name is not empty.  Port Royal ships
# MAP001_000_000 ("Mirage reel") the same way, so this is a pre-existing
# pattern rather than a regression, and adding a drop rule with no control
# under it is what this round has just been beaten for.
# set number -> (MOBS.n_ID, name, outfit, level, max_hp)
MAP_PROP_ROWS = {
    111: (923, 'Big Sword', 'MAP009_000_000', 1, 106),
}


@dataclass(frozen=True)
class SceneIdentity:
    """One resolved actor: who it is, what it wears, what its label says."""

    template_id: int
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
# 41 rows: every Mob-Set number in CLINE type 14 that resolves.
# ``cline_row_id`` is COO-DECISION 2026-08-28T22:50 condition (a) - "every
# value carries its source line" - in the only form this repository can
# offer: the CLINE row's own n_ID, so a second party can open
# gamedata/tables/CONSTDATA_TH__CLINE.tsv at that row and see the pairing
# this module claims, without re-running the whole scan.  It was missing
# from the first draft (pf-adversary), and the pairing is exactly the part
# that has no other control under it.
_RESOLVED_ROWS = (
    (2, 3401, 322, 'M055_000_000_N', 'Columbus', 110, 0, 260787, 2),
    (3, 3402, 323, 'P_FEMALE_952_000_SIREN', 'Siren', 110, 0, 260787, 2),
    (4, 3403, 324, 'M077_000_000_N', 'Angelina', 110, 0, 260787, 2),
    (5, 3404, 325, 'M023_000_000_SP2', 'Greedy Troll', 110, 0, 260787, 2),
    (6, 3405, 326, 'M008_000_002_N', 'Walking undead', 110, 0, 260787, 2),
    (7, 3406, 327, 'M022_000_000_SP2', 'Love bathing Banshee', 110, 0, 260787, 2),
    (8, 3407, 328, 'M026_000_002_SP2', 'Debt Skeleton', 110, 0, 260787, 2),
    (9, 3408, 329, 'P_FEMALE_000_000_VALKYRE', "Val'kyr", 110, 0, 260787, 2),
    (10, 3409, 330, 'P_FEMALE_028_000_VALKYRE', "Val'kyr", 110, 0, 260787, 2),
    (11, 3410, 331, 'M077_000_000_N', 'Angelina', 110, 0, 260787, 2),
    (12, 3411, 332, 'M023_001_000_SP1', 'Myers', 110, 0, 260787, 2),
    (13, 3412, 333, 'P_MALE_016_000_DANTE', 'Dante', 110, 0, 260787, 2),
    (14, 3413, 334, 'M077_000_000_N', 'Angelina', 110, 0, 260787, 2),
    (15, 3414, 335, 'P_FEMALE_952_000_SIREN', 'Siren', 110, 0, 260787, 2),
    (16, 3415, 336, 'M023_001_002_SP1', 'Kablin', 110, 0, 260787, 2),
    (17, 3416, 337, 'M076_000_000_N', 'Sea Phantom', 110, 0, 260787, 2),
    (18, 3417, 338, 'M076_000_000_N', 'Sea Phantom', 110, 0, 260787, 2),
    (19, 3418, 339, 'M008_000_000_SP1', 'Lonely Soul', 110, 0, 260787, 2),
    (20, 3419, 340, 'M005_001_000_SP1', 'Nightmare Claw beast', 105, 1, 228055, 1),
    (21, 3420, 341, 'M011_000_001_SP1', 'Blood red eagle', 105, 1, 228055, 1),
    (22, 3421, 342, 'M004_000_001_SP1', 'Fire magic', 105, 1, 228055, 1),
    (23, 3422, 343, 'M020_000_000_N', 'Glaucoma', 105, 1, 228055, 1),
    (24, 3423, 344, 'M022_000_001_SP1', 'Phosphor powder Banshee', 105, 1, 228055, 1),
    (25, 3424, 345, 'M022_000_001_SP3', 'Phosphor Fascinator', 105, 1, 228055, 1),
    (26, 3425, 346, 'M005_000_002_SP1', 'Flame Mountains deer', 105, 1, 228055, 1),
    (27, 3426, 347, 'M000_001_001_N', 'Red Flame Demon Wolf', 105, 1, 228055, 1),
    (28, 3427, 348, 'M000_001_001_SP3', 'Crimson Sharp Teeth', 105, 1, 228055, 1),
    (29, 3428, 349, 'M017_000_002_SP1', 'Hell Dragon Majin', 105, 1, 228055, 1),
    (30, 3429, 350, 'M017_000_002_SP3', 'Arbiter Bells', 105, 1, 228055, 1),
    (31, 3430, 351, 'M006_001_000_SP1', 'Earth Flame Dragon', 105, 1, 228055, 1),
    (32, 3431, 352, 'M003_000_003_SP1', 'Hell King Kong', 105, 1, 228055, 1),
    (33, 3432, 353, 'M003_000_003_SP3', 'Lava shakers', 105, 1, 228055, 1),
    (34, 3433, 354, 'M023_001_000_SP1', 'Hell Ghoul', 105, 1, 228055, 1),
    (35, 3434, 355, 'M023_001_000_SP3', 'Horror butcher Lasa', 105, 1, 228055, 1),
    (36, 3435, 465, 'M017_000_002_SP3', 'Baroque', 105, 0, 228055, 2),
    (109, 3444, 921, 'M077_000_000_N', 'Angelina', 98, 0, 186962, 2),
    (110, 3445, 922, 'M076_000_000_N', 'Sea Phantom', 104, 0, 221803, 2),
    (111, 3446, 923, 'MAP009_000_000', 'Big Sword', 1, 0, 106, 2),
    (112, 3447, 924, 'P_MALE_033_000_CARLOS', 'Carlos', 115, 1, 296546, 2),
    (113, 3448, 925, 'M076_000_000_N', 'Sea Phantom', 104, 0, 221803, 2),
    (114, 3449, 926, 'P_FEMALE_028_000_VALKYRE', "Val'kyr", 110, 0, 260787, 2),
)

IDENTITIES = {
    row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS
}


@dataclass(frozen=True)
class Bg0015Placement:
    """One Bg0015 placement resolved to a real, named, bodied actor."""

    placement_index: int
    template_id: int
    mm_instance: int
    x: float
    y: float
    z: float
    identity: SceneIdentity

    @property
    def actor_identity(self) -> int:
        # The same formula bg0001's and bg0002's censuses already use
        # (population.py's SceneActorPlacement.actor_identity).  Never sent
        # in the same generation as another scene's census -- every builder
        # refuses any scene id but its own -- so the identity spaces sharing
        # numbers is a collision in the abstract only.
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


# (placement index, Mob-Set number, MOBSET instance number, x, y, z),
# every row of the scene's own placement file in file order.
_PLACEMENT_ROWS = (
    (0, 1, 1, -18837.380859375, 22084.92578125, 1927.56103515625),
    (1, 2, 1, -19547.025390625, 20988.498046875, 1926.8231201171875),
    (2, 3, 1, -17206.619140625, 19632.37890625, 1952.2628173828125),
    (3, 4, 1, -3997.016845703125, 14049.5673828125, 2179.76123046875),
    (4, 5, 1, -9142.068359375, 21341.736328125, 695.5913696289062),
    (5, 6, 1, -15993.5029296875, 17209.822265625, 2067.378173828125),
    (6, 7, 1, -13610.8896484375, 14690.9892578125, 2155.10107421875),
    (7, 8, 1, -8085.9423828125, 7227.02685546875, 2455.40478515625),
    (8, 9, 1, -7223.39794921875, 3125.231201171875, 2494.580322265625),
    (9, 10, 1, -5564.8388671875, 1405.7564697265625, 2612.73193359375),
    (10, 11, 1, -8306.841796875, -557.5781860351562, 2613.013671875),
    (11, 12, 1, -16310.505859375, -10559.181640625, 1170.952880859375),
    (12, 13, 1, 20129.537109375, 15148.5419921875, 1978.682373046875),
    (13, 14, 1, 11716.0654296875, 21891.123046875, 2643.626708984375),
    (14, 15, 1, 3403.770263671875, -7752.4208984375, 5015.90966796875),
    (15, 16, 1, 6013.41943359375, 4756.150390625, 4660.19775390625),
    (16, 17, 1, 17627.390625, 876.092529296875, 4953.857421875),
    (17, 18, 1, 8816.3955078125, -20302.15234375, 5087.3203125),
    (18, 19, 1, -5590.345703125, -10895.2333984375, 4372.98046875),
    (19, 20, 1, -11130.615234375, 19335.384765625, 961.8015747070312),
    (20, 21, 1, -14941.0947265625, 14209.779296875, 2179.63037109375),
    (21, 22, 1, -9355.736328125, 4568.2919921875, 2430.1884765625),
    (22, 23, 1, -11200.365234375, -598.9420776367188, 2447.830322265625),
    (23, 24, 1, -14204.6455078125, -7533.09228515625, 935.82861328125),
    (24, 25, 1, -12794.1201171875, -19500.970703125, 4982.83740234375),
    (25, 26, 1, 2587.0302734375, 7818.517578125, 2651.933837890625),
    (26, 27, 1, 9530.5546875, 15712.703125, 2646.576416015625),
    (27, 28, 1, 17688.904296875, 14799.4130859375, 2223.9462890625),
    (28, 29, 1, 15693.1865234375, 18930.490234375, 2656.349853515625),
    (29, 30, 1, 12026.26171875, 23254.26171875, 2673.939697265625),
    (30, 31, 1, 6036.5810546875, 202.87680053710938, 4542.48388671875),
    (31, 33, 1, 11665.1416015625, -1562.874755859375, 4365.74462890625),
    (32, 32, 1, 10607.7216796875, 2047.006103515625, 4600.40234375),
    (33, 32, 2, 11962.953125, 2207.499267578125, 4679.72216796875),
    (34, 20, 2, -8583.7177734375, 19452.39453125, 856.416015625),
    (35, 20, 3, -6551.59228515625, 17913.724609375, 1054.2025146484375),
    (36, 20, 4, -4317.15771484375, 14701.7890625, 1991.4840087890625),
    (37, 21, 2, -15754.974609375, 10906.697265625, 2349.8837890625),
    (38, 21, 3, -15313.3359375, 8850.2958984375, 2374.539794921875),
    (39, 21, 4, -13059.0615234375, 7343.07568359375, 2379.736572265625),
    (40, 21, 5, -10816.23046875, 6098.66748046875, 2374.6259765625),
    (41, 22, 2, -7698.7529296875, 284.37890625, 2566.356689453125),
    (42, 22, 3, -1478.806884765625, 194.3948974609375, 2762.9658203125),
    (43, 22, 4, 441.2449951171875, 3974.86767578125, 2656.674072265625),
    (44, 23, 2, -12168.4912109375, -3187.351318359375, 2486.368408203125),
    (45, 23, 3, -10052.9736328125, -7851.99609375, 2401.858154296875),
    (46, 23, 4, -11553.9150390625, -5713.6767578125, 2327.19189453125),
    (47, 23, 5, -8906.2294921875, -10704.669921875, 3154.77587890625),
    (48, 24, 2, -17161.7421875, -11797.16796875, 1176.5955810546875),
    (49, 24, 3, -18427.27734375, -15018.8984375, 1781.6842041015625),
    (50, 24, 4, -17588.576171875, -17492.1796875, 2536.354248046875),
    (51, 23, 6, -13532.3935546875, -13779.04296875, 3239.51806640625),
    (52, 24, 5, -16123.171875, -14752.1298828125, 2804.91650390625),
    (53, 26, 2, 5498.9853515625, 12598.8427734375, 2753.19775390625),
    (54, 26, 3, 3911.6298828125, 10401.345703125, 2643.590576171875),
    (55, 26, 4, 7920.74609375, 13878.4033203125, 2787.249755859375),
    (56, 27, 2, 12761.205078125, 15398.2978515625, 2646.57666015625),
    (57, 27, 3, 15517.1787109375, 16083.822265625, 2628.779296875),
    (58, 29, 2, 13411.642578125, 18700.87890625, 2605.55322265625),
    (59, 31, 2, 8397.12109375, 3205.90673828125, 4552.0234375),
    (60, 32, 3, 14645.087890625, 1440.9427490234375, 4809.2890625),
    (61, 34, 1, -1718.2618408203125, -6423.5595703125, 3756.145263671875),
    (62, 34, 2, 995.7576293945312, -7947.04638671875, 4291.10498046875),
    (63, 34, 3, -1300.1986083984375, -3309.963623046875, 3282.133544921875),
    (64, 34, 4, -2821.444091796875, -9737.005859375, 4235.8583984375),
    (65, 31, 3, 3500.207763671875, -1302.6533203125, 4519.55908203125),
    (66, 31, 4, 2197.726806640625, -3225.654296875, 4562.68896484375),
    (67, 34, 5, 5134.92529296875, -12188.62890625, 6195.76025390625),
    (68, 34, 6, 7985.09130859375, -15373.0537109375, 6277.93212890625),
    (69, 34, 7, 7736.89111328125, -13725.8779296875, 6233.88916015625),
    (70, 35, 1, -6298.55322265625, -20541.8125, 6598.4580078125),
    (71, 34, 8, 7127.57568359375, -23162.279296875, 6414.27294921875),
    (72, 34, 9, 1032.052978515625, -21807.556640625, 5882.146484375),
    (73, 34, 10, 2382.00341796875, -21163.001953125, 5844.23974609375),
    (74, 34, 11, -3058.61328125, -20289.9296875, 6767.0615234375),
    (75, 36, 1, 15764.5576171875, 22718.185546875, 2652.7705078125),
    (76, 101, 1, -2742.84716796875, 15502.26953125, 2087.583740234375),
    (77, 102, 1, -427.4031066894531, 2421.017333984375, 2437.188720703125),
    (78, 103, 1, -10183.431640625, 19154.37109375, 894.6489868164062),
    (79, 104, 1, -18246.482421875, -12254.37109375, 1196.60791015625),
    (80, 105, 1, -5512.15087890625, 3686.0654296875, 2359.6591796875),
    (81, 106, 1, -19006.47265625, 17209.20703125, 1891.3433837890625),
    (82, 107, 1, -13918.7109375, -18170.79296875, 4945.4306640625),
    (83, 108, 1, 5261.59619140625, -12126.3046875, 6187.654296875),
    (84, 111, 1, 20200.5703125, 15051.0341796875, 1946.4705810546875),
    (85, 110, 1, 19917.564453125, 15193.533203125, 1987.82177734375),
    (86, 109, 1, 20765.751953125, 13691.23046875, 1830.7418212890625),
    (87, 112, 1, 10159.2294921875, -39.96989822387695, 4421.5224609375),
    (88, 113, 1, 9593.193359375, -124.72380065917969, 4511.11279296875),
    (89, 114, 1, 9919.1826171875, -594.15478515625, 4441.9248046875),
    (90, 115, 1, -18035.189453125, 21501.71875, 1927.56103515625),
)

PLACEMENT_COUNT = len(_PLACEMENT_ROWS)


class Bg0015IdentityError(ValueError):
    """A refusal from this module, always with a reason in the message."""


def identity_for(template_id: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    ``None`` is the ten sets in ``UNRESOLVED`` and nothing else: this
    function never substitutes, and never falls back to the Mob-Set number
    that ``GT-078`` proved wrong on the owner's screen.
    """
    if type(template_id) is not int or type(template_id) is bool:
        raise Bg0015IdentityError('template id must be an int')
    return IDENTITIES.get(template_id)


def shippable_placements() -> tuple[Bg0015Placement, ...]:
    """The 81 placements of the 91 that resolve to a real identity."""
    out = []
    for index, template_id, mm_instance, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(template_id)
        if identity is None:
            continue
        out.append(Bg0015Placement(
            index, template_id, mm_instance, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The ten that are dropped, each with the id and the reason.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH ten and WHY.
    """
    out = []
    for index, template_id, _mm, x, y, z in _PLACEMENT_ROWS:
        if template_id in IDENTITIES:
            continue
        cline_row_id, leader, reason = UNRESOLVED.get(
            template_id, (0, 0, 'set not in CLINE 14'))
        out.append({
            'placement_index': index,
            'template_id': template_id,
            'cline_row_id': cline_row_id,
            'leader_n_id': leader,
            'reason': reason,
            'xyz': (x, y, z),
        })
    return tuple(out)


# THE OVERLAP WITH LANE B'S MINED HOSTILE ROSTER FOR THIS SAME SCENE, which
# is already committed at HEAD.  It is deliberately not named in this file:
# a guard test forbids ANY mention of that module's name anywhere under
# ``src/`` (COO-DECISION 2026-08-26T12:46 keeps it dormant), and that guard
# is right to fire.  It is named in
# ``tests/test_world_bg0015_identity.py``, which is allowed to.  It was
# generated by a
# rule that reads the Mob-Set number straight as a ``MOBS.n_ID`` -- the
# reading GT-078 had rejected.  It and this module both derive
# ``actor_identity = 0x2000 + placement_index + 1``, both for scene 14, and
# 16 of its 17 placement indices are indices this module also ships:
# placement 61 is "Fighting Fish soldier, lv25, hp3138" there and
# "Hell Ghoul, lv105, hp228055" here, at one identity and one XYZ.  The
# cross-scene collision reporter in this tree cannot see it, because that
# one compares DIFFERENT scene names, and both of these say Bg0015.  Nothing is wired today so nothing
# collides on a wire today; the day lane B's hostile splice for this scene
# lands beside this census, the second collection replaces the first by
# omission (RE-092) and one identity silently wins.
#
# So the overlap is computed and asserted in this module's test file, and
# handed to that module's owner by letter.  Found by pf-adversary, round
# w0pu2i: the first draft of this module never opened the repo's own
# artifact for its own scene.
COLLIDING_PLACEMENTS = (
    30, 59, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74,
)


def no_set_number_is_shipped_as_identity() -> bool:
    """Control 3, executable.  Scope, stated twice because it is weak: this
    checks the 41 SHIPPED rows only -- that no row hands back the Mob-Set
    number it was keyed by -- and pf-adversary's note is correct that in
    THIS scene it could never fire for any pairing, because the keys are all
    <= 115 and the leaders are all >= 321.  It is a shape check, not
    evidence.  It does not and cannot check the ten unresolved sets (they
    ship nothing) or any other scene."""
    return all(row[0] != row[2] for row in _RESOLVED_ROWS)


def _self_check() -> None:
    """Refuse at import if this table has drifted out of the shape the
    module docstring claims.  Fail-closed: a bad table must not reach a
    census builder at all, and an ImportError names the file."""
    if len(_RESOLVED_ROWS) != 41:
        raise Bg0015IdentityError(
            'expected 41 resolved sets, found %d' % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg0015IdentityError('duplicate Mob-Set number in the table')
    if len(UNRESOLVED) != 10:
        raise Bg0015IdentityError(
            'expected 10 unresolved sets, found %d' % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg0015IdentityError('a set is both resolved and unresolved')
    if len(_PLACEMENT_ROWS) != 91:
        raise Bg0015IdentityError(
            'expected 91 placements, found %d' % len(_PLACEMENT_ROWS))
    # Control 1: the scene's Mob-Set numbers and CLINE type 14's keys are
    # the SAME 51 numbers.  A placement keyed by a number this table has
    # never heard of means the placement file and the crosswalk have come
    # from different extractions.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if scene_sets != table_sets:
        raise Bg0015IdentityError(
            'placement Mob-Set numbers and CLINE type 14 keys disagree: %r'
            % sorted(scene_sets ^ table_sets))
    if not no_set_number_is_shipped_as_identity():
        raise Bg0015IdentityError(
            'a row ships its own Mob-Set number as an identity')
    for row in _RESOLVED_ROWS:
        (template_id, cline_row_id, n_id, outfit, name, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1:
            raise Bg0015IdentityError(
                'set %d carries no CLINE row locator' % template_id)
        if ';' in outfit:
            raise Bg0015IdentityError(
                'set %d ships a multi-variant outfit string' % template_id)
        if not outfit or not outfit.isascii():
            raise Bg0015IdentityError(
                'set %d has an empty or non-ASCII outfit' % template_id)
        if not name or not name.isascii():
            raise Bg0015IdentityError(
                'set %d has an empty or non-ASCII display name' % template_id)
        if max_hp < 1 or level < 1:
            raise Bg0015IdentityError('set %d has a bad level/HP' % template_id)
    # Control 2 as a guard, and STATED AT ITS REAL STRENGTH after
    # pf-adversary showed a scrambled table sails through it: a shuffle of
    # this table puts the median at or above 100 in 100% of 2,000 random
    # draws, so this CANNOT detect a wrong pairing.  What it can detect is
    # a regeneration that went back to reading the Mob-Set number as an
    # n_ID, which lands near 20.  That is the only thing it is here for.
    levels = sorted(IDENTITIES[row[1]].level for row in _PLACEMENT_ROWS
                    if row[1] in IDENTITIES)
    median = levels[len(levels) // 2]
    if median < SCENE_DECLARED_LEVEL:
        raise Bg0015IdentityError(
            'resolved cast median level %d is below the declared scene level %d'
            % (median, SCENE_DECLARED_LEVEL))
    if len(shippable_placements()) != 81:
        raise Bg0015IdentityError('expected 81 shippable placements')
    if len(unshippable_placements()) != 10:
        raise Bg0015IdentityError('expected 10 unshippable placements')


_self_check()
