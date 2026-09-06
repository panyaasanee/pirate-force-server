"""Who is really in the Pale Silver Sea - LANE-A, scene 305, model ``Bg3008``.

THE IDENTITY HALF of round ``9zj630``'s pair; ``world_population_bg3008`` is
the census half and ships every row this table resolves.  Scene 305 is the
SECOND of the two seas ``COO-DECISION 20260905_1748`` named as the
destinations of a crossing at scene 126's own map edge (the southern edge,
where 304 is the western one); round ``n4vqxc`` (``#843``) pinned its arrival
point and its registry row, round ``yob0a2`` built 304's cast and left 305
with NO CAST at all, and round ``dyi95m`` put 305 into
``lane_a_scene_census.ARM_THREE_ELIGIBLE_SCENE_IDS`` with the comment "no
composer or named seam constant yet (that is the cast this lane still owes
it)".  This module is the table that pays that.

WHAT IT RESOLVES, COUNTED BY PLACEMENT AND NOT BY NAME (the count a ticket
quotes is the placement count; an earlier lane round shipped a ticket that
counted names and sent a tester looking for the wrong number):

    ALL 59 of the scene's 59 native placements ship, over all 47 first-leg
    Mob-Set numbers those placements use.  The four lines below add up to
    59:

    25 invisible bodies (``INVISIBLE``): 19 named ``Tornado``, plus 6
       placements of the two NAMELESS sets (2 of set 56 and 4 of set 57,
       the first leg of the ``57|58`` pair - see below)
    16 hulls (``SP_*``) with a name plate: 9 Merchant Ship, 3 of the mined
       "Merchant marine" row, and one each of Viking Princess, Santa Maria,
       Skull Phantom and Utopia
    13 level-120 Pirate Ships (sets 17, 18, 20-22, 24-26, 34-38), the only
       rows in this scene that carry a real HP number besides the two
       level-110 nameless sets
     5 islands-as-actors (``MAP_ISLAND_01``): Ice Island, Turtle Island,
       Dragon Turtle Island, Guawa Island, Snow Island

    NOTHING IS DROPPED, and that is the one number this scene does not
    share with its sibling.  ``UNRESOLVED`` is EMPTY: every one of the 47
    first-leg sets resolves through CLINE type 3008 to a MOBS row with a
    real ``s_OUTFIT``.  Scene 304 lost 16 of its 66 placements to four
    CLINE leaders (8176-8179) that ``CONSTDATA_TH__MOBS.tsv`` has no row
    for; this scene's placements never key those four sets.  The
    ``UNRESOLVED`` mechanism is kept rather than deleted - it is what a
    future regeneration would put a new drop in, and ``unshippable_
    placements`` still answers with an empty tuple rather than with nothing.

THE SIBLING PATTERN, NOT A FORK.  ``world_bg3007_identity`` is scene 304's
crosswalk and this is the same join against the same five tables, keyed on
this scene's own ``n_CLINE_TYPE`` (3008 rather than 3007), refusing anywhere
but scene 305.  Every rule this module enforces is that module's rule; where
this scene's numbers differ, they were measured here rather than carried
over, and the differences are listed below rather than left for a reader to
find by diffing.

THE JOIN, EXACTLY, AS ``world_bg3007_identity`` states it:

    keys   = {r.n_CREATURE_TYPE: r for r in CLINE if r.n_CLINE_TYPE == 3008}
    for each FIRST-LEG Mob-Set number k this scene's placements use (47):
        leader = keys[k].n_LEADER_BK1
        drop k if leader is 0 or MOBS has no row for it, or that row's
            s_OUTFIT is empty, or MOBS_TIP.s_NAME/s_TITLE is not ASCII
        else row = (k, keys[k].n_ID, leader, s_OUTFIT,
                    MOBS_TIP.s_NAME or '', MOBS_TIP.s_TITLE or '',
                    MOBS.n_LEVEL_MIN, MOBS.n_RANK,
                    STANDARD_MOB[n_LEVEL_MIN].n_HPMAX, MOBS.n_MOB_USAGE)
    placements = every row of Bg3008.placements.tsv as
        (index, first-leg template id, running instance count, x, y, z)

WHERE 3008 IS NOT 3007, MEASURED ON THIS SCENE'S OWN FILES rather than
assumed from the sibling:

* ``n_CLINE_TYPE`` IS READ, NOT ASSUMED.  ``CONSTDATA_TH__SCENE_NAME.tsv``
  row 305 carries ``s_MODLE_ID = Bg3008`` and ``n_CLINE_TYPE = 3008``; the
  fact that the two numbers rhyme is the table's doing, not this module's
  assumption, and ``SCENE_CLINE_TYPE`` below is that column's value.
* ``n_SCENE_LV`` IS 80, not 304's 30 and not 126's 0.  Recorded as
  ``SCENE_DECLARED_LEVEL`` and used by nothing - the level each ACTOR ships
  is its own ``MOBS.n_LEVEL_MIN``, never the scene's band.
* THE PAIR IS ``57|58``, not 304's ``53|54``, and it is 4 placements rather
  than 6.  Both legs are checked by ``MULTI_SET_GATE`` below rather than
  assumed safe: leg 57 is CLINE 61656 -> MOBS 8167 and leg 58 is CLINE
  61657 -> MOBS 8171 - the SAME two MOBS rows scene 304's ``53|54`` pair
  resolves to, reached through this scene's own CLINE rows.  They agree on
  every column THIS MODULE SHIPS (``INVISIBLE``, no name, no title, level
  110, rank 0, HP 260787, usage 7), and NEITHER has a
  ``TEXTDATA_TH__MOBS_TIP`` row - so neither can draw a name plate that
  would tell a player which leg they are looking at.
  ~~and differ only on the MOBS id~~ -- STRUCK, pf-adversary (this round,
  D2), MEASURED FALSE in ``CONSTDATA_TH__MOBS.tsv`` itself: the two rows
  differ on FOUR columns besides ``n_ID``, and the sibling scene's own
  docstring makes the same claim about the same two rows, so it is wrong
  there too (corrected in that file this round).  8167 is
  the row whose ``s_NAME`` is utf-8
  ``e6b5b7e4b88ae5a4a9e5809928e99bb7e99bbbe9a2a8e69ab429`` (a THUNDERSTORM,
  per the mined label) with
  ``s_PROPERTIES = 8209;8211;8212;8213;8214;8215;8216;8196`` and speeds
  600/600; 8171 is the row whose ``s_NAME`` is utf-8
  ``e6b5b7e4b88ae5a4a9e5809928e9a2a8e5b9b3e6b5aae99d9c29`` (a DEAD CALM) with
  ``s_PROPERTIES = 8190`` and speeds 200/200.  So the honest sentence is:
  the legs are interchangeable IN WHAT THIS CENSUS PUTS ON THE WIRE, and
  are two different weather events in the table.  Nothing this module
  sends carries a property list or a speed, so shipping the first leg is
  still correct TODAY - but ``multi_set_placement_refusals`` compares the
  fields of ``SceneIdentity`` and structurally CANNOT see those four
  columns, so the day any round adds ``s_PROPERTIES`` or a speed to what a
  census ships, this pair stops being interchangeable and the gate will
  not notice.  Asked as a design question in this round's
  ``LANE-A-ASK-COO`` letter rather than answered here.
* TWO NAMELESS SETS, not one.  Sets 56 (MOBS 8170) and 57 (MOBS 8167) both
  ship ``INVISIBLE`` with no ``MOBS_TIP`` row at all.
  ``NAMELESS_INVISIBLE_SETS`` names both; a nameless row with a visible
  body is still a mining fault and still refused.  Set 56 is the ICEBERG
  (utf-8 ``e6b5b7e4b88ae5a4a9e5809928e586b0e5b1b129``,
  properties ``8222;8223``, speed 450) and it ships
  SOLO on 2 placements - unlike 304, where the one nameless set was
  reachable only through the pair, so a blind mirror of that scene's
  ``NAMELESS_INVISIBLE_SETS = {53}`` would have raised at import here.
* THE THREE NAMELESS BODIES CANNOT BE NAMED IN cp874 AT ALL, said here
  because the obvious next step for a reader is to give them one
  (pf-adversary, this round, D6).  Their ``MOBS.s_NAME`` values above are
  Traditional Chinese; ``str.encode("cp874")`` RAISES for all three, so
  there is no ``NAME_CP874_HEX`` pin that could carry them - the pin
  mechanism is cp874-shaped because the bridge console is, and these names
  are outside it.  What ships is the ``MOBS_TIP`` name, which for these
  three does not exist; ``MOBS.s_NAME`` is a mining label this project has
  never put on a wire.
* 780 EXTRA SPAWN POINTS in 19 of the 59 placement rows are NOT shipped
  (304 carries 656 in 18 rows).  This composer sends one actor per primary
  placement point, the number the registry's ``native_placement_count``
  cites.  Whether those triples are a patrol path or 780 more actors is NOT
  established (the same open question ``world_density`` carries by name).

WHAT THIS SCENE SHARES WITH 304 AND 126, re-measured here rather than
inherited:

* THE DOOR IS SHUT.  ``login_entry_allowed`` for scene 305 is ``false`` and
  this round does not flip it.  The one way a session stands here today is
  a GM ``/warp 305``, which ``#843`` opened as a declared side effect of
  pinning the scene's arrival marker (``accounts.is_gm_account`` still
  gates ``/warp`` itself).  This module opens no door of its own: a census
  is composed FOR a session that is already there.
* FACTION FRAME: SHIPS NOW.  ``SCENE_NAME.n_SAVE`` is 0; ``world_faction_
  admission`` used to refuse this scene (exactly as it refused 126 and
  304), but LANE-A round q02brx (COO-DECISION 20260906_1347) widened it to
  every login scene.  Nothing in THIS module changed to make that true.
* NO CREW.  Measured: 0 of CLINE type 3008's 58 rows carry any ``n_CREW``
  value.  BUT ``n_LEADER_BK2``/``n_LEADER_BK3`` are a different column
  family and this scene uses them on exactly one row - CLINE 61610
  (Mob-Set 11, this scene's densest set, 9 of the 59 placements) carries
  back-up leaders 8165 and 8166, both absent from the tip table.  The same
  shape scene 304's CLINE 61410 and scene 126's CLINE 60410 carry, on the
  same Mob-Set number, and like every crosswalk in this project this module
  implements ``n_LEADER_BK1`` ONLY, so those two are dropped.
* NO NAME-VS-TEMPLATE DISAGREEMENT, NO MULTI-VARIANT OUTFIT, NO EXTRACTION
  SENTINEL.  Checked directly against this scene's own placement file: no
  shipped ``s_OUTFIT`` contains ``;``, no row's ``template_ids`` column
  reads the literal ``UNRESOLVED``, and every row's ``set_names`` numeric
  tail matches its ``template_ids`` column (the four ``57|58`` rows carry
  ``MobSet_57|MobSet_58``, which agrees leg for leg).  ~~``Mob_Set_57|
  Mob_Set_58``~~ -- STRUCK before the first push, pf-adversary (this round,
  D4): that is the SIBLING's spelling.  This scene's file writes the column
  without the second underscore and zero-pads the low numbers
  (``MobSet_03``), which is the kind of detail a sentence carried over from
  a sibling gets wrong while the claim around it stays true.  The claim was
  re-measured on all 59 rows and holds; the token did not.
* NO NON-ASCII NAME.  Every name this table ships is ASCII, so
  ``NAME_CP874_HEX`` is empty here.  The mechanism is kept, not deleted:
  it is the MEMBERSHIP GATE ``COO-DECISION 20260902_2146`` set for this
  lane, and ``_self_check`` refuses any future regeneration that brings a
  non-ASCII name in without a pin.
* HEADING, MEASURED ON THIS SCENE'S OWN FILE.  ``f32_3`` is ``0.0`` on all
  59 rows; ``f32_4`` takes 9 values (500, 1000, 3000, 4000, 5000, 6000,
  7000, 12000, 22000) and ``f32_5`` 9 values (800, 2500, 4000, 5000, 6000,
  7000, 8000, 13000, 23000) - round thousands that scale with the placement
  rather than with any facing, the shape of a radius and not a rotation, so
  the census half reuses ``world_population.HEADINGS`` on the placement
  index exactly as every sibling scene does.

PROVENANCE.  Every row below was generated from these six committed
artifacts and nothing else, by a throwaway script run against the bridge
clone this round; the script's output is what appears below, unedited except
for line wrapping:

    gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv
    gamedata/tables/CONSTDATA_TH__CLINE.tsv
    gamedata/tables/CONSTDATA_TH__MOBS.tsv
    gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv
    gamedata/tables/CONSTDATA_TH__STANDARD_MOB.tsv
    gamedata/scene/Bg3008/Bg3008.placements.tsv

WHAT THIS MODULE DOES NOT CLAIM.

* Not that any of these 59 actors has been SEEN.  No human has been in this
  scene in this project's history, and no client has ever received a byte
  of it.
* Not that ``MAP_ISLAND_01`` actors render as islands rather than as
  ordinary actor bodies.  Same rows, same serializer; what the client does
  with that avatar name is unmeasured.  This scene has five of them and
  none of the five names appears in scene 126's or 304's tables, so the
  "two seas may be drawing the same island twice" question those two raise
  does not arise here.
* Not that a crossing at scene 126's southern map edge lands a player here.
  That responder is not wired (``world_sea_edge_crossing`` composes
  nothing); what reaches this scene today is a GM ``/warp``.
* Not leader+crew: this implements ``n_LEADER_BK1`` only.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass


# Convention marker: shippable, no scenario flag - matching the sibling
# crosswalk modules' own convention.
production_allowed = True
test_only = False

SCENE_N_ID = 305
SCENE_MODEL_ID = "Bg3008"
SCENE_CLINE_TYPE = 3008
# SCENE_NAME.n_SCENE_LV for this scene.  80, unlike scene 304's 30 and
# scene 126's 0.  Read by nothing: an actor ships its own level.
SCENE_DECLARED_LEVEL = 80
# SCENE_NAME.n_SAVE for this scene.  Kept as a named constant because
# ``world_faction_admission`` used to refuse on it - see the module
# docstring for why that no longer holds (LANE-A round q02brx).
SCENE_SAVE_FLAG = 0

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
    "gamedata/scene/Bg3008/Bg3008.placements.tsv":
        'b0855920e52fbd49ae6b59031201dbff6662d70b0a1b78b7dfbb6a3c791db7d9',
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  EMPTY FOR THIS SCENE:
# all 47 first-leg sets resolve, so all 59 placements ship.  The mechanism
# is kept for the same reason ``NAME_CP874_HEX`` is: a regeneration that
# brings a drop in must name it here, and ``_self_check`` counts what is in
# it rather than trusting a comment.
UNRESOLVED: dict[int, tuple[int, int, str]] = {}

# Placements whose ``template_ids`` column names TWO Mob-Set numbers, as
# placement index -> the whole raw string.  The table below ships the FIRST
# leg; ``_self_check`` refuses if a raw '|' ever reaches a shipped column,
# and ``multi_set_placement_refusals`` (the executable ``MULTI_SET_GATE``)
# refuses if the legs are not the interchangeable pair that makes shipping
# the first one safe.  ``COO-DECISION 20260902_2146`` shape 2.
MULTI_SET_PLACEMENTS = {
    55: '57|58',
    56: '57|58',
    57: '57|58',
    58: '57|58',
}

# The second legs of the rows above: real CLINE keys, resolvable, never
# shipped under the first-leg rule.  Recorded so the key looks like a
# decision rather than an omission - and carried in the SAME ten-column row
# shape as ``_RESOLVED_ROWS`` so the gate can compare the legs column by
# column instead of asserting they match.  Derived off this scene's own
# tables, not copied from scene 304's identical-looking pair.
_SECOND_LEG_ROWS = (
    (58, 61657, 8171, 'INVISIBLE', '', '', 110, 0, 260787, 7),
)

# Whether each leg of a multi-set placement has a ``TEXTDATA_TH__MOBS_TIP``
# row at all - measured, because "no name" and "no name plate" are
# different facts and the gate turns on the second one.  Checked this round
# against ``TEXTDATA_TH__MOBS_TIP.tsv`` by MOBS.n_ID: 8167 absent, 8171
# absent.
MULTI_SET_LEG_HAS_TIP_ROW = {
    57: False,
    58: False,
}

# Display names this table ships that are not ASCII, as Mob-Set number ->
# the ``MOBS_TIP.s_NAME`` bytes in cp874, hex.  EMPTY FOR THIS SCENE: every
# one of its 47 resolved sets carries an ASCII name (or, for sets 56 and
# 57, none).  The mechanism stays because it is the membership gate
# ``COO-DECISION 20260902_2146`` set - a future regeneration that brings in
# a Thai name must pin it here or ``_self_check`` refuses at import.
NAME_CP874_HEX: dict[int, str] = {}

# Placement index -> how many EXTRA xyz triples that row carries beyond its
# primary point.  None of them is shipped (see the module docstring); 780
# points in total across 19 of the 59 rows.
EXTRA_TRIPLES_NOT_SHIPPED = {
    8: 8,
    9: 38,
    10: 25,
    11: 19,
    12: 14,
    13: 21,
    14: 20,
    15: 24,
    16: 29,
    17: 51,
    18: 36,
    19: 47,
    35: 1,
    53: 100,
    54: 103,
    55: 35,
    56: 58,
    57: 70,
    58: 81,
}


class Bg3008IdentityError(ValueError):
    """A refusal from this module, always with a reason in the message."""


# The one encoding that decides whether a display name may ship at all.
# Not the transport - the wire carries a name as UTF-16LE (``wstr_tag``) -
# but the client's own locale.  See the module docstring.
NAME_ENCODING = "cp874"


def _cp874(hex_bytes: str) -> str:
    """Decode a pinned non-ASCII display name, refusing if the pin is not
    what it claims to be.

    NO ROW IN THIS SCENE NEEDS IT TODAY (``NAME_CP874_HEX`` is empty), and
    it is here rather than deleted because ``_self_check`` calls it for any
    future non-ASCII name: without it, a regeneration that pulled in a Thai
    row would ship a name nothing had checked.  Exercised directly by this
    scene's own test file so it is not code nothing runs.

    Three refusals, all fail-closed:

    * bytes that are not valid ``cp874`` - the membership gate itself;
    * bytes that do not round-trip;
    * a pin whose text is ASCII after all - that row must carry the
      literal, so the table stays readable to the next person.
    """
    if type(hex_bytes) is not str:
        raise Bg3008IdentityError("a pinned name must be a hex str")
    try:
        raw = bytes.fromhex(hex_bytes)
    except ValueError as failure:
        raise Bg3008IdentityError(
            "a pinned name must be hex bytes: %s" % (failure,)) from failure
    try:
        text = raw.decode(NAME_ENCODING, "strict")
    except UnicodeDecodeError as failure:
        raise Bg3008IdentityError(
            "a pinned name must decode as %s" % NAME_ENCODING) from failure
    if text.encode(NAME_ENCODING, "strict") != raw:
        raise Bg3008IdentityError("a pinned name must round-trip through %s"
                                  % NAME_ENCODING)
    if text.isascii():
        raise Bg3008IdentityError(
            "an ASCII name must be written as the literal, not as a pin")
    return text


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
# 47 rows: every first-leg Mob-Set number this scene's placements use, all
# of which CLINE type 3008 resolves to a shippable body.
_RESOLVED_ROWS = (
    (3, 61602, 8010, 'SP_005_000_000_N', 'Viking Princess', '', 1, 0, 106, 7),
    (4, 61603, 8011, 'SP_003_000_000_N', 'Santa Maria', '', 1, 0, 106, 7),
    (5, 61604, 8012, 'SP_008_000_000_N', 'Skull Phantom', '', 1, 0, 106, 7),
    (6, 61605, 8013, 'SP_001_000_000_N', 'Utopia', '', 1, 0, 106, 7),
    (7, 61606, 8020, 'MAP_ISLAND_01', 'Ice Island', '', 1, 0, 106, 2),
    (8, 61607, 8021, 'MAP_ISLAND_01', 'Turtle Island', '', 1, 0, 106, 2),
    (9, 61608, 8022, 'MAP_ISLAND_01', 'Dragon Turtle Island', '', 1, 0, 106,
     2),
    (10, 61609, 8023, 'MAP_ISLAND_01', 'Guawa Island', '', 1, 0, 106, 2),
    (11, 61610, 8024, 'SP_000_000_000_N', 'Merchant Ship', '', 1, 0, 106, 7),
    (12, 61611, 8029, 'SP_001_000_000_N', 'Merchant marine Trade Ship', '', 1,
     0, 106, 2),
    (13, 61612, 8030, 'SP_001_000_000_N', 'Merchant marine Trade Ship', '', 1,
     0, 106, 2),
    (14, 61613, 8031, 'SP_001_000_000_N', 'Merchant marine Trade Ship', '', 1,
     0, 106, 2),
    (17, 61616, 8075, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0, 335459,
     7),
    (18, 61617, 8076, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0, 335459,
     7),
    (20, 61619, 8078, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0, 335459,
     7),
    (21, 61620, 8079, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0, 335459,
     7),
    (22, 61621, 8080, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0, 335459,
     7),
    (24, 61623, 8082, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0, 335459,
     7),
    (25, 61624, 8083, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0, 335459,
     7),
    (26, 61625, 8084, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0, 335459,
     7),
    (29, 61628, 8087, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (30, 61629, 8088, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (31, 61630, 8089, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (32, 61631, 3204, 'MAP_ISLAND_01', 'Snow Island', '', 1, 0, 106, 2),
    (34, 61633, 8090, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0, 335459,
     7),
    (35, 61634, 8091, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0, 335459,
     7),
    (36, 61635, 8092, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0, 335459,
     7),
    (37, 61636, 8093, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0, 335459,
     7),
    (38, 61637, 8094, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0, 335459,
     7),
    (39, 61638, 8095, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (40, 61639, 8096, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (41, 61640, 8097, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (42, 61641, 8098, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (43, 61642, 8099, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (44, 61643, 8100, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (45, 61644, 8101, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (46, 61645, 8102, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (47, 61646, 8103, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (48, 61647, 8104, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (49, 61648, 8105, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (50, 61649, 8106, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (51, 61650, 8107, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (52, 61651, 8108, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (53, 61652, 8109, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (54, 61653, 8110, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (56, 61655, 8170, 'INVISIBLE', '', '', 110, 0, 260787, 7),
    (57, 61656, 8167, 'INVISIBLE', '', '', 110, 0, 260787, 7),
)

IDENTITIES = {row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS}

# The second legs, in the same object shape as ``IDENTITIES`` so the gate
# compares like with like.  Never merged into ``IDENTITIES``: these keys are
# deliberately not shippable.
SECOND_LEG_IDENTITIES = {
    row[0]: SceneIdentity(*row) for row in _SECOND_LEG_ROWS
}

# Backwards-compatible view of the same rows: set -> (CLINE row, leader).
SECOND_LEG_ONLY = {row[0]: (row[1], row[2]) for row in _SECOND_LEG_ROWS}

# The fields of ``SceneIdentity`` that are LOCATORS rather than shipped
# columns.  Named here so the derivation below reads as "everything else".
_LEG_COMPARISON_EXEMPT = ("template_id", "cline_row_id", "mobs_n_id")

# The columns this module SHIPS, minus the MOBS id.  ``COO-DECISION
# 20260902_2146`` shape 2 names exactly this set: the legs of a multi-set
# placement may differ on the MOBS number and on nothing else.  DERIVED, not
# typed - a column added to ``SceneIdentity`` joins the comparison by
# existing (the regression pf-adversary measured on scene 126, round
# ``gx7xtp``, D5: a hand-typed tuple that had lost ``rank`` left the whole
# suite green and would have called a boss interchangeable with a mook).
SHIPPED_COLUMNS_EXCEPT_MOBS_ID = tuple(
    field.name for field in dataclasses.fields(SceneIdentity)
    if field.name not in _LEG_COMPARISON_EXEMPT
)

# The two sets this scene ships with an empty display name, and the outfit
# that makes them legal.  Named rather than left to a bare ``or ''``: an
# empty name anywhere else in this table is a mining fault.
NAMELESS_INVISIBLE_SETS = frozenset({56, 57})
INVISIBLE_OUTFIT = "INVISIBLE"


@dataclass(frozen=True)
class Bg3008Placement:
    """One Bg3008 placement resolved to a real, bodied actor."""

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
        # scene id but its own - so sharing the numeric space is a collision
        # in the abstract only.
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


# (placement index, FIRST-LEG Mob-Set number, running instance count of that
#  Mob-Set number within this file, x, y, z), every row of the scene's own
#  placement file in file order.  The four rows whose raw column named two
#  sets are in ``MULTI_SET_PLACEMENTS``; no sentinel rows this scene.
_PLACEMENT_ROWS = (
    (0, 3, 1, -469.4219970703125, -3925.510498046875, 109.86859893798828),
    (1, 4, 1, 340.36669921875, -3677.46533203125, 109.30699920654297),
    (2, 5, 1, 3792.731201171875, -5868.5673828125, 109.30670166015625),
    (3, 6, 1, 1648.14892578125, 897.7979125976562, 109.30719757080078),
    (4, 7, 1, -1922.4677734375, -6779.44287109375, 109.30670166015625),
    (5, 8, 1, -4924.22412109375, -5278.515625, 109.30650329589844),
    (6, 9, 1, -1181.3896484375, -1330.763916015625, 109.30660247802734),
    (7, 10, 1, -4360.10546875, -325.0658874511719, 109.30709838867188),
    (8, 11, 1, -6211.20947265625, 967.0042724609375, 109.30470275878906),
    (9, 11, 2, -5191.00244140625, 1752.2103271484375, 109.30680084228516),
    (10, 11, 3, -5504.3828125, 942.8408813476562, 109.30619812011719),
    (11, 11, 4, -3360.64599609375, -1693.376220703125, 109.30819702148438),
    (12, 11, 5, -3832.548828125, -1924.846435546875, 109.30699920654297),
    (13, 11, 6, -3991.79736328125, -2404.02197265625, 100.20909881591797),
    (14, 11, 7, -3995.5390625, -2801.58642578125, 109.3062973022461),
    (15, 11, 8, 1397.625, -3856.60205078125, 109.30509948730469),
    (16, 11, 9, 2812.630615234375, -3820.525634765625, 109.30680084228516),
    (17, 12, 1, -4849.400390625, 4466.30322265625, 109.30560302734375),
    (18, 13, 1, 5331.92431640625, 4412.98828125, 109.3062973022461),
    (19, 14, 1, -5477.17431640625, -7201.08203125, 109.3062973022461),
    (20, 17, 1, -5342.29150390625, -1994.641845703125, 109.30590057373047),
    (21, 18, 1, -1818.1044921875, -680.5382080078125, 109.30670166015625),
    (22, 20, 1, -3356.203125, -6190.8125, 109.30680084228516),
    (23, 21, 1, 2154.546875, -7743.376953125, 109.30549621582031),
    (24, 22, 1, 4075.33935546875, -2997.720458984375, 109.3053970336914),
    (25, 24, 1, -4574.43994140625, 1590.328857421875, 109.30549621582031),
    (26, 25, 1, 102.9811019897461, 4706.4814453125, 109.3053970336914),
    (27, 26, 1, -2671.96875, 3336.07666015625, 109.30549621582031),
    (28, 29, 1, 3942.466064453125, -4591.3974609375, 109.30549621582031),
    (29, 30, 1, 4721.5615234375, -6989.08642578125, 109.30549621582031),
    (30, 31, 1, 870.8303833007812, -6263.0830078125, 109.3053970336914),
    (31, 34, 1, -5229.70703125, -7538.2646484375, 109.30549621582031),
    (32, 35, 1, -513.1561279296875, -5577.8369140625, 109.3053970336914),
    (33, 36, 1, 4170.373046875, 404.4424133300781, 109.30549621582031),
    (34, 37, 1, 1908.599365234375, 1677.878173828125, 109.30549621582031),
    (35, 38, 1, -1015.9196166992188, 4619.78515625, 109.30670166015625),
    (36, 39, 1, -6514.2119140625, -452.06689453125, 109.30780029296875),
    (37, 40, 1, -6463.67041015625, -5539.8837890625, 109.30870056152344),
    (38, 41, 1, -2234.347412109375, 476.0869140625, 109.31069946289062),
    (39, 42, 1, -2052.7744140625, 2382.6015625, 109.31050109863281),
    (40, 43, 1, 2886.5283203125, 5279.552734375, 109.31009674072266),
    (41, 44, 1, 3022.31787109375, 4153.57470703125, 109.31050109863281),
    (42, 45, 1, 6858.9970703125, 1150.95849609375, 109.31050109863281),
    (43, 46, 1, 2608.9853515625, -1688.0537109375, 109.31009674072266),
    (44, 47, 1, 6537.07861328125, -3440.629150390625, 109.30899810791016),
    (45, 48, 1, 6565.9072265625, -5616.8525390625, 109.30819702148438),
    (46, 49, 1, -3467.138671875, -4491.759765625, 109.30660247802734),
    (47, 50, 1, -5653.287109375, -3490.333984375, 109.30709838867188),
    (48, 51, 1, -4830.38134765625, 4966.1337890625, 109.30829620361328),
    (49, 52, 1, 1525.5517578125, 4694.65380859375, 109.30829620361328),
    (50, 53, 1, 515.747314453125, -1136.06103515625, 109.30889892578125),
    (51, 54, 1, 4935.57666015625, 2550.27734375, 109.3104019165039),
    (52, 32, 1, 5204.939453125, -7336.494140625, 109.3051986694336),
    (53, 56, 1, 6129.33740234375, -6323.65869140625, 66.78299713134766),
    (54, 56, 2, -1396.6474609375, 3344.08740234375, 66.78299713134766),
    (55, 57, 1, -3182.499755859375, -1313.61083984375, 66.78299713134766),
    (56, 57, 2, -2040.15771484375, -4963.4580078125, 66.78250122070312),
    (57, 57, 3, 4863.26123046875, 1134.43798828125, 66.78250122070312),
    (58, 57, 4, 23.762699127197266, -7275.13525390625, 66.78299713134766),
)

PLACEMENT_COUNT = len(_PLACEMENT_ROWS)


def identity_for(template_id: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    WHAT ``None`` REALLY MEANS HERE, corrected before the first push
    (pf-adversary, this round, D9, on a first draft that said "``None`` is
    exactly the sets in ``UNRESOLVED``, which for this scene is none of
    them" - read literally, that claimed this function never returns
    ``None`` at all).  It returns ``None`` for two different populations:
    the sets in ``UNRESOLVED`` (empty for this scene) AND every Mob-Set
    number CLINE type 3008 defines that this scene never PLACES - 11 of the
    58, namely 1, 2, 15, 16, 19, 23, 27, 28, 33, 55 and 58.  Set 58 is the
    pair's second leg, deliberately unshipped.  SET 55 IS WORTH A READER'S
    ATTENTION and is written down rather than left to be found: CLINE 61654
    -> MOBS 8163 is ``Pirate Flagship``, ``SP_008_000_000_BOSS``, level 80,
    rank 64, HP 104603 - the ONLY ``n_RANK != 0`` row in the whole CLINE
    type, defined for this sea and placed at none of its 59 points.  This
    module ships what the placement file places; a boss the scene's own
    author did not place is not this crosswalk's to invent.

    What this function still never does: substitute, or fall back to the
    Mob-Set number itself, which is the specific regression ``GT-078`` was.
    """
    if type(template_id) is not int or type(template_id) is bool:
        raise Bg3008IdentityError("template id must be an int")
    return IDENTITIES.get(template_id)


def shippable_placements() -> tuple[Bg3008Placement, ...]:
    """All 59 placements: every one of them resolves to an identity."""
    out = []
    for index, template_id, mm_instance, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(template_id)
        if identity is None:
            continue
        out.append(Bg3008Placement(
            index, template_id, mm_instance, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The dropped placements, with the id and the reason.  EMPTY HERE.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH ones and WHY.  An empty tuple is
    this scene's real answer, not a stub: the loop below is the sibling's
    loop, and it would report a drop the day a regeneration made one.
    """
    out = []
    for index, template_id, _mm, x, y, z in _PLACEMENT_ROWS:
        if template_id in IDENTITIES:
            continue
        cline_row_id, leader, reason = UNRESOLVED.get(
            template_id, (0, 0, "set not in CLINE 3008"))
        out.append({
            "placement_index": index,
            "template_id": template_id,
            "cline_row_id": cline_row_id,
            "leader_n_id": leader,
            "reason": reason,
            "xyz": (x, y, z),
        })
    return tuple(out)


def evidence_name(identity: SceneIdentity) -> str:
    """The ASCII token the evidence layer prints for this actor's name.

    Every name this scene ships is ASCII today, so this returns the name
    itself for every row in the table; the hex branch is the contract
    ``COO-DECISION 20260902_2146`` shape 1 set for the day a regeneration
    brings a Thai name in, and this scene's test file exercises it directly
    rather than leaving it unrun.
    """
    if type(identity) is not SceneIdentity:
        raise Bg3008IdentityError("evidence_name needs a SceneIdentity")
    if identity.name.isascii():
        return identity.name
    return "name_cp874_hex=%s" % (
        identity.name.encode(NAME_ENCODING, "strict").hex(),)


def multi_set_placement_refusals() -> tuple[dict, ...]:
    """``MULTI_SET_GATE``, executable.  Empty tuple means every multi-set
    placement is the interchangeable pair that makes shipping the first leg
    safe; anything in it must NOT ship.

    The two conditions are ``COO-DECISION 20260902_2146`` shape 2, in order:
    (1) the legs disagree on a shipped column other than the MOBS id, or a
    leg is not in this module's tables at all - unknown is not equal, and
    (2) a leg is visible or carries a name plate.  A refusal carries the
    placement, the legs and which condition fired, because the decision
    requires the case to reach the COO as a letter rather than to ship
    quietly.
    """
    out = []
    for index in sorted(MULTI_SET_PLACEMENTS):
        raw = MULTI_SET_PLACEMENTS[index]
        legs = []
        malformed = False
        for text in raw.split("|"):
            if not text.isdigit():
                # NOT skipped.  ``_self_check`` refuses a malformed raw
                # column before it ever reaches here, but this function is
                # also called on its own (by tests, and by anything that
                # wants the refusals without the ImportError), and a gate
                # that drops what it cannot parse is a gate that passes the
                # case it was written for.
                out.append({
                    "placement_index": index, "raw": raw, "leg": text,
                    "condition": 1,
                    "reason": "leg %r is not a Mob-Set number" % text,
                })
                malformed = True
                continue
            legs.append(int(text))
        if malformed:
            continue
        known = []
        for leg in legs:
            found = IDENTITIES.get(leg) or SECOND_LEG_IDENTITIES.get(leg)
            if found is None:
                out.append({
                    "placement_index": index, "raw": raw, "leg": leg,
                    "condition": 1,
                    "reason": "leg %d has no identity in this table" % leg,
                })
            else:
                known.append((leg, found))
        if len(known) != len(legs):
            continue
        first_leg, first = known[0]
        for leg, other in known[1:]:
            for column in SHIPPED_COLUMNS_EXCEPT_MOBS_ID:
                mine = getattr(first, column)
                theirs = getattr(other, column)
                if mine != theirs:
                    out.append({
                        "placement_index": index, "raw": raw, "leg": leg,
                        "condition": 1,
                        "reason": "legs %d and %d disagree on %s"
                                  % (first_leg, leg, column),
                    })
        for leg, found in known:
            if found.outfit != INVISIBLE_OUTFIT:
                out.append({
                    "placement_index": index, "raw": raw, "leg": leg,
                    "condition": 2,
                    "reason": "leg %d is visible (outfit %s)"
                              % (leg, found.outfit),
                })
            if MULTI_SET_LEG_HAS_TIP_ROW.get(leg, True):
                out.append({
                    "placement_index": index, "raw": raw, "leg": leg,
                    "condition": 2,
                    "reason": "leg %d has a MOBS_TIP row (a name plate), or "
                              "this table does not know whether it does"
                              % leg,
                })
    return tuple(out)


def no_set_number_is_shipped_as_identity() -> bool:
    """Control 3, executable.  No resolved row ships its own Mob-Set number
    as its identity - it catches a future regeneration that falls back to
    the Mob-Set number itself, which is the specific regression GT-078 was.
    """
    return all(row[0] != row[2] for row in _RESOLVED_ROWS)


def _self_check() -> None:
    """Refuse at import if this table has drifted out of the shape the
    module docstring claims.  Fail-closed: a bad table must not reach a
    census builder at all, and an ImportError names the file.
    """
    if len(_RESOLVED_ROWS) != 47:
        raise Bg3008IdentityError(
            "expected 47 resolved sets, found %d" % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg3008IdentityError("duplicate Mob-Set number in the table")
    if UNRESOLVED:
        # Not "expected N unresolved sets": this scene's answer is zero, and
        # a regeneration that produced a drop must land as a code change
        # with its own count rather than pass a loose check.
        raise Bg3008IdentityError(
            "this scene resolves every set; %d unresolved appeared"
            % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg3008IdentityError("a set is both resolved and unresolved")
    if set(IDENTITIES) & set(SECOND_LEG_ONLY):
        raise Bg3008IdentityError(
            "a second-leg-only key is also shipped as a first leg")
    if len(_PLACEMENT_ROWS) != 59:
        raise Bg3008IdentityError(
            "expected 59 placements, found %d" % len(_PLACEMENT_ROWS))
    # Control 1: every first-leg Mob-Set number this scene's placements use
    # is either resolved or named as unresolved, and the two sets together
    # are EXACTLY this scene's used keys - a placement keyed by a number
    # this table has never heard of means the placement file and the
    # crosswalk came from different extractions.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if scene_sets != table_sets:
        raise Bg3008IdentityError(
            "placement Mob-Set numbers and this table's keys disagree: %r"
            % sorted(scene_sets ^ table_sets))
    if len(table_sets) != 47:
        raise Bg3008IdentityError(
            "expected 47 distinct Mob-Set numbers, found %d" % len(table_sets))
    # Control 2: the placement file's own running instance counts.  A row
    # whose count restarts or skips means the rows were reordered after the
    # table was generated, which would silently re-key every actor.
    seen: dict[int, int] = {}
    for index, template_id, mm_instance, _x, _y, _z in _PLACEMENT_ROWS:
        seen[template_id] = seen.get(template_id, 0) + 1
        if mm_instance != seen[template_id]:
            raise Bg3008IdentityError(
                "placement %d claims instance %d of set %d, expected %d"
                % (index, mm_instance, template_id, seen[template_id]))
    # Every multi-set placement must BE one of this table's rows, keyed by
    # the first leg of its own raw string.
    indices = {row[0]: row[1] for row in _PLACEMENT_ROWS}
    for index, raw in MULTI_SET_PLACEMENTS.items():
        if index not in indices:
            raise Bg3008IdentityError(
                "multi-set placement %d is not in the placement table" % index)
        legs = raw.split("|")
        if len(legs) < 2 or not all(leg.isdigit() for leg in legs):
            raise Bg3008IdentityError(
                "multi-set placement %d has a malformed raw column %r"
                % (index, raw))
        if indices[index] != int(legs[0]):
            raise Bg3008IdentityError(
                "multi-set placement %d does not ship its first leg" % index)
        for leg in legs[1:]:
            if int(leg) in IDENTITIES:
                raise Bg3008IdentityError(
                    "second leg %s of placement %d is shipped as well"
                    % (leg, index))
    for index in EXTRA_TRIPLES_NOT_SHIPPED:
        if index not in indices:
            raise Bg3008IdentityError(
                "extra-triple row %d is not in the placement table" % index)
    if not no_set_number_is_shipped_as_identity():
        raise Bg3008IdentityError(
            "a row ships its own Mob-Set number as an identity")
    for row in _RESOLVED_ROWS:
        (template_id, cline_row_id, n_id, outfit, name, title, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1 or n_id < 1:
            raise Bg3008IdentityError(
                "set %d carries no CLINE row or leader locator" % template_id)
        if ";" in outfit or "|" in outfit:
            raise Bg3008IdentityError(
                "set %d ships a multi-variant outfit string" % template_id)
        if not outfit or not outfit.isascii():
            raise Bg3008IdentityError(
                "set %d has an empty or non-ASCII outfit" % template_id)
        # NAMES.  ``COO-DECISION 20260902_2146`` shape 1: a non-ASCII name
        # must round-trip through cp874 AND be pinned as bytes in
        # ``NAME_CP874_HEX``, so a name can never arrive here by some other
        # route.  TITLES are untouched and still ASCII.
        if not title.isascii():
            raise Bg3008IdentityError(
                "set %d has a non-ASCII title" % template_id)
        if not name.isascii():
            pinned = NAME_CP874_HEX.get(template_id)
            if pinned is None:
                raise Bg3008IdentityError(
                    "set %d has a non-ASCII name that is not pinned in "
                    "NAME_CP874_HEX" % template_id)
            if _cp874(pinned) != name:
                raise Bg3008IdentityError(
                    "set %d ships a name that is not its own pin"
                    % template_id)
        elif template_id in NAME_CP874_HEX:
            raise Bg3008IdentityError(
                "set %d is pinned in NAME_CP874_HEX but ships an ASCII name"
                % template_id)
        if not name and not (
            template_id in NAMELESS_INVISIBLE_SETS
            and outfit == INVISIBLE_OUTFIT
        ):
            # The bg0004 set-107 exception, narrowed to the two sets that
            # earn it: a nameless row with a real body is a mining fault.
            raise Bg3008IdentityError(
                "set %d has no display name and is not a known nameless "
                "INVISIBLE set" % template_id)
        if max_hp < 1 or level < 1:
            raise Bg3008IdentityError("set %d has a bad level/HP" % template_id)
    # Every set NAMED as nameless must really be in this table and really be
    # nameless: without this, deleting a row from ``_RESOLVED_ROWS`` leaves
    # a stale exemption behind that would bless the next nameless row to
    # take that number.
    for template_id in NAMELESS_INVISIBLE_SETS:
        found = IDENTITIES.get(template_id)
        if found is None:
            raise Bg3008IdentityError(
                "set %d is exempted as nameless but is not in this table"
                % template_id)
        if found.name:
            raise Bg3008IdentityError(
                "set %d is exempted as nameless but ships the name %r"
                % (template_id, found.name))
    # MULTI_SET_GATE.  Fail-closed and BEFORE the counts below, so a pair
    # that stops being interchangeable cannot reach a census builder even if
    # the row count still looks right.  ORDER MATTERS (pf-adversary, scene
    # 126, round ``gx7xtp``, D6): the gate's own fail-closed default - an
    # unmeasured leg counts as having a name plate - must not depend on a
    # later loop happening to raise first, so the inputs are checked BEFORE
    # the gate reads them.
    for index, raw in MULTI_SET_PLACEMENTS.items():
        for leg in raw.split("|"):
            if not leg.isdigit() or int(leg) not in MULTI_SET_LEG_HAS_TIP_ROW:
                raise Bg3008IdentityError(
                    "leg %s of placement %d has no measured MOBS_TIP answer"
                    % (leg, index))
    if set(SECOND_LEG_IDENTITIES) != set(SECOND_LEG_ONLY):
        raise Bg3008IdentityError("the second-leg views disagree")
    if not SHIPPED_COLUMNS_EXCEPT_MOBS_ID:
        raise Bg3008IdentityError("the leg comparison compares nothing")
    refusals = multi_set_placement_refusals()
    if refusals:
        raise Bg3008IdentityError(
            "multi-set placements refused by the gate (COO-DECISION "
            "20260902_2146 shape 2): %s"
            % "; ".join(
                "placement %d: %s" % (row["placement_index"], row["reason"])
                for row in refusals))
    if len(shippable_placements()) != 59:
        raise Bg3008IdentityError("expected 59 shippable placements")
    if len(unshippable_placements()) != 0:
        raise Bg3008IdentityError("expected no unshippable placements")
    ids = [p.actor_identity for p in shippable_placements()]
    if len(ids) != len(set(ids)):
        raise Bg3008IdentityError("actor identities collide within this table")


_self_check()
