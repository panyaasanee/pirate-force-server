"""Who is really in the Dark Fog Sea - LANE-A, scene 304, model ``Bg3007``.

THE IDENTITY HALF of round ``yob0a2``'s pair; ``world_population_bg3007`` is
the census half and ships every row this table resolves.  Scene 304 is the
first of the two seas ``COO-DECISION 20260905_1748`` named as the
destinations of a crossing at scene 126's own map edge; round ``n4vqxc``
(``#843``) pinned its arrival point and its registry row, and left the scene
with NO CAST - a GM who warps there today is sent an empty ocean.  This
module is the table that ends that.

WHAT IT RESOLVES, COUNTED BY PLACEMENT AND NOT BY NAME (the count a ticket
quotes is the placement count; an earlier lane round shipped a ticket that
counted names and sent a tester looking for the wrong number):

    50 of the scene's 66 native placements ship, over 37 of the 41
    first-leg Mob-Set numbers those placements use.  The four lines below
    add up to 50 placements, and they were re-added after pf-queue-author
    caught an earlier draft of this paragraph adding up to 49:

    20 invisible bodies (``INVISIBLE``): 14 named ``Tornado``, one
       placement each from sets 33, 35-39 and 41-48, plus 6 placements of
       the ONE nameless set 53 (the ``53|54`` pair - see below)
    19 hulls (``SP_*``) with a name plate: 9 Merchant Ship, 3 of the mined
       "Merchant marine" row, and one each of Ulysses, Bismarck, Yamato,
       Black beard, Red beard, Smuggling Ship and a set-52 Pirate Ship
     9 level-120 Pirate Ships (sets 21, 22, 24-30), the only rows in this
       scene that carry a real HP number rather than the level-1 floor
     2 islands-as-actors (``MAP_ISLAND_01``): Mad Sand Island, Pirate Lair

    ~~44~~ 50, corrected before the first commit: the round's own opening
    measurement counted the six ``53|54`` placements as unresolvable, which
    is not what the first-leg rule this project already uses says.  Set 53
    resolves; the pair is checked by ``MULTI_SET_GATE`` below rather than
    assumed safe.

    16 placements do NOT ship, all for ONE reason (see ``UNRESOLVED``):
    sets 55, 56, 57 and 58 name CLINE leaders 8176, 8178, 8177 and 8179,
    and ``CONSTDATA_TH__MOBS.tsv`` HAS NO ROW for any of the four.  They
    are not nameless - ``TEXTDATA_TH__MOBS_TIP.tsv`` names them Ulysses,
    Pirate Follow Ship, Yamato and Navy Follow Ship - but a tip row is a
    label, not a body: there is no ``s_OUTFIT``, no level and no HP to
    send, and inventing one would put a made-up actor on a client.  This
    is a NEW drop shape for this lane, and it is the majority of what this
    scene loses: every earlier scene's drops were leader-0 rows or empty
    outfits.

THE SIBLING PATTERN, NOT A FORK.  ``world_bg3001_identity`` is scene 126's
crosswalk and this is the same join against the same five tables, keyed on
this scene's own ``n_CLINE_TYPE`` (3007 rather than 3001), refusing anywhere
but scene 304.  Every rule this module enforces is that module's rule; where
this scene's numbers differ, they were measured here rather than carried
over.

THE JOIN, EXACTLY, AS ``world_bg3001_identity`` states it:

    keys   = {r.n_CREATURE_TYPE: r for r in CLINE if r.n_CLINE_TYPE == 3007}
    for each FIRST-LEG Mob-Set number k this scene's placements use (41):
        leader = keys[k].n_LEADER_BK1
        drop k if leader is 0 or MOBS has no row for it, or that row's
            s_OUTFIT is empty, or MOBS_TIP.s_NAME/s_TITLE is not ASCII
        else row = (k, keys[k].n_ID, leader, s_OUTFIT,
                    MOBS_TIP.s_NAME or '', MOBS_TIP.s_TITLE or '',
                    MOBS.n_LEVEL_MIN, MOBS.n_RANK,
                    STANDARD_MOB[n_LEVEL_MIN].n_HPMAX, MOBS.n_MOB_USAGE)
    placements = every row of Bg3007.placements.tsv as
        (index, first-leg template id, running instance count, x, y, z)

WHAT THIS SCENE DOES AND DOES NOT SHARE WITH SCENE 126, MEASURED ON ITS OWN
FILES rather than assumed from the sibling:

* THE DOOR IS SHUT.  ``login_entry_allowed`` for scene 304 is ``false`` and
  this round does not flip it.  The one way a session stands here today is
  a GM ``/warp 304``, which ``#843`` opened as a declared side effect of
  pinning the scene's arrival marker (``accounts.is_gm_account`` still
  gates ``/warp`` itself).  This module opens no door of its own: a census
  is composed FOR a session that is already there.
* NO FACTION FRAME.  ``SCENE_NAME.n_SAVE`` is 0, so
  ``world_faction_admission`` refuses this scene by its own published rule,
  exactly as it refuses 126.  Nothing here widens that.
* ``n_SCENE_LV`` IS 30, NOT 0.  Scene 126's ocean panel declares level 0;
  this one declares 30.  Recorded as ``SCENE_DECLARED_LEVEL`` and used by
  nothing - the level each ACTOR ships is its own ``MOBS.n_LEVEL_MIN``,
  never the scene's band.
* 15 SETS SHIP ``INVISIBLE`` BODIES, one of them (set 53) with no name at
  all, both under the precedent ``world_bg0004_identity`` set 107 and
  scene 126's own set 53 already ship under.
* 656 EXTRA SPAWN POINTS in 18 of the 66 placement rows are NOT shipped.
  This composer sends one actor per primary placement point, the number
  the registry's ``native_placement_count`` cites.  Whether those triples
  are a patrol path or 656 more actors is NOT established (the same open
  question ``world_density`` carries by name).
* NO CREW.  Measured: 0 of CLINE type 3007's 58 rows carry any ``n_CREW``
  value.  BUT ``n_LEADER_BK2``/``n_LEADER_BK3`` are a different column
  family and this scene uses them on exactly one row - CLINE 61410
  (Mob-Set 11, this scene's densest set, 9 of the 50 shipped placements)
  carries back-up leaders 8165 and 8166, both nameless in the tip table.
  Like every crosswalk in this project this module implements
  ``n_LEADER_BK1`` ONLY, so those two are dropped.  The same shape scene
  126's own CLINE row 60410 carries, and named here for the same reason:
  a paragraph headed NO CREW is where the next reader stops.
* NO NAME-VS-TEMPLATE DISAGREEMENT, NO MULTI-VARIANT OUTFIT, NO EXTRACTION
  SENTINEL.  Checked directly against this scene's own placement file: no
  shipped ``s_OUTFIT`` contains ``;``, no row's ``template_ids`` column
  reads the literal ``UNRESOLVED``, and every row's ``set_names`` numeric
  tail matches its ``template_ids`` column (the six ``53|54`` rows carry
  ``Mob_Set_53|Mob_Set_54``, which agrees leg for leg).
* NO NON-ASCII NAME.  Every name this table ships is ASCII, so
  ``NAME_CP874_HEX`` is empty here.  The mechanism is kept, not deleted:
  it is the MEMBERSHIP GATE ``COO-DECISION 20260902_2146`` set for this
  lane, and ``_self_check`` refuses any future regeneration that brings a
  non-ASCII name in without a pin.
* HEADING, MEASURED ON THIS SCENE'S OWN FILE.  ``f32_3`` is ``0.0`` on all
  66 rows; ``f32_4`` takes 9 values (500, 1500, 5000, 7000, 8000, 9000,
  11000, 12000, 25000) and ``f32_5`` 9 values (800, 3000, 6000, 8000,
  9000, 10000, 12000, 13000, 26000) - round thousands that scale with the
  placement rather than with any facing, the shape of a radius and not a
  rotation, so the census half reuses ``world_population.HEADINGS`` on the
  placement index exactly as every sibling scene does.

THE ``53|54`` PAIR, AND WHY SHIPPING THE FIRST LEG IS CHECKED RATHER THAN
ASSUMED.  Six placements (44-49) name two Mob-Set numbers in one column.
``COO-DECISION 20260902_2146`` shape 2 allows the first leg to ship when the
legs are interchangeable, and ``multi_set_placement_refusals`` is that rule
executable.  Measured for this scene: leg 53 is CLINE 61452 -> MOBS 8167 and
leg 54 is CLINE 61453 -> MOBS 8171; the two rows agree on every column THIS
MODULE SHIPS (``INVISIBLE``, no name, no title, level 110, rank 0, HP
260787, usage 7), and NEITHER has a ``TEXTDATA_TH__MOBS_TIP`` row.
~~and differ only on the MOBS id~~ -- STRUCK 2026-09-06 (LANE-A round
``9zj630``; pf-adversary measured it there while checking scene 305, whose
own ``57|58`` pair resolves to these SAME two MOBS rows and whose docstring
had inherited this sentence).  In ``CONSTDATA_TH__MOBS.tsv`` the two rows
differ on FOUR columns besides ``n_ID``: ``s_NAME`` (8167 is a thunderstorm,
8171 a dead calm - both Traditional Chinese, neither encodable in cp874, so
neither can be quoted in this file), ``s_PROPERTIES`` (eight entries against
one) and both speed columns (600/600 against 200/200).  Shipping the first
leg is still correct today because nothing this census sends carries any of
those four - but ``multi_set_placement_refusals`` compares the fields of
``SceneIdentity`` and structurally cannot see them, so "interchangeable"
here means interchangeable ON THE WIRE, not in the table - so neither can draw a name plate that would
tell a player which leg they are looking at.  That is the same pair shape
scene 126 ships under, re-measured here on this scene's own rows.

PROVENANCE.  Every row below was generated from these six committed
artifacts and nothing else, by a throwaway script run against the bridge
clone this round; the script's output is what appears below, unedited except
for formatting:

    gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv
    gamedata/tables/CONSTDATA_TH__CLINE.tsv
    gamedata/tables/CONSTDATA_TH__MOBS.tsv
    gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv
    gamedata/tables/CONSTDATA_TH__STANDARD_MOB.tsv
    gamedata/scene/Bg3007/Bg3007.placements.tsv

WHAT THIS MODULE DOES NOT CLAIM.

* Not that any of these 50 actors has been SEEN.  No human has been in this
  scene in this project's history, and no client has ever received a byte
  of it.
* Not that ``MAP_ISLAND_01`` actors ("Mad Sand Island", "Pirate Lair")
  render as islands rather than as ordinary actor bodies.  Same rows, same
  serializer; what the client does with that avatar name is unmeasured.
  Note that BOTH names also appear in scene 126's own table: whether the
  client draws two instances of one island in two seas, or these are two
  different props sharing a label, is not established here.
* Not that a crossing at scene 126's map edge lands a player here.  That
  responder is not wired (``world_sea_edge_crossing`` composes nothing);
  what reaches this scene today is a GM ``/warp``.
* Not leader+crew: this implements ``n_LEADER_BK1`` only.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass


# Convention marker: shippable, no scenario flag - matching the sibling
# crosswalk modules' own convention.
production_allowed = True
test_only = False

SCENE_N_ID = 304
SCENE_MODEL_ID = "Bg3007"
SCENE_CLINE_TYPE = 3007
# SCENE_NAME.n_SCENE_LV for this scene.  30, unlike scene 126's ocean panel
# which declares 0.  Read by nothing: an actor ships its own level.
SCENE_DECLARED_LEVEL = 30
# SCENE_NAME.n_SAVE for this scene.  Kept as a named constant because
# ``world_faction_admission`` refuses on it - see the module docstring.
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
    "gamedata/scene/Bg3007/Bg3007.placements.tsv":
        'aeb9b37ab684e95b20dd7b60dfb76c741651b9e978b5027f697aa3b426f69701',
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  Costs 16 of the 66
# placements.  ONE shape for all four, and it is not the leader-0 shape
# every earlier scene met: the CLINE row names a real leader number, the
# tip table even names it, and ``CONSTDATA_TH__MOBS.tsv`` has no row for
# it at all - no outfit, no level, no HP, nothing to send.
UNRESOLVED = {
    55: (61454, 8176,
         'CLINE leader has no CONSTDATA MOBS row (MOBS_TIP names it Ulysses)'),
    56: (61455, 8178,
         'CLINE leader has no CONSTDATA MOBS row (MOBS_TIP names it Pirate '
         'Follow Ship)'),
    57: (61456, 8177,
         'CLINE leader has no CONSTDATA MOBS row (MOBS_TIP names it Yamato)'),
    58: (61457, 8179,
         'CLINE leader has no CONSTDATA MOBS row (MOBS_TIP names it Navy '
         'Follow Ship)'),
}

# Placements whose ``template_ids`` column names TWO Mob-Set numbers, as
# placement index -> the whole raw string.  The table below ships the FIRST
# leg; ``_self_check`` refuses if a raw '|' ever reaches a shipped column,
# and ``multi_set_placement_refusals`` (the executable ``MULTI_SET_GATE``)
# refuses if the legs are not the interchangeable pair that makes shipping
# the first one safe.  ``COO-DECISION 20260902_2146`` shape 2.
MULTI_SET_PLACEMENTS = {
    44: '53|54',
    45: '53|54',
    46: '53|54',
    47: '53|54',
    48: '53|54',
    49: '53|54',
}

# The second legs of the rows above: real CLINE keys, resolvable, never
# shipped under the first-leg rule.  Recorded so the key looks like a
# decision rather than an omission - and carried in the SAME ten-column row
# shape as ``_RESOLVED_ROWS`` so the gate can compare the legs column by
# column instead of asserting they match.  Derived off this scene's own
# tables, not copied from scene 126's identical-looking pair.
_SECOND_LEG_ROWS = (
    (54, 61453, 8171, 'INVISIBLE', '', '', 110, 0, 260787, 7),
)

# Whether each leg of a multi-set placement has a ``TEXTDATA_TH__MOBS_TIP``
# row at all - measured, because "no name" and "no name plate" are
# different facts and the gate turns on the second one.  Checked this round
# against ``TEXTDATA_TH__MOBS_TIP.tsv`` by MOBS.n_ID: 8167 absent, 8171
# absent.
MULTI_SET_LEG_HAS_TIP_ROW = {
    53: False,
    54: False,
}

# Display names this table ships that are not ASCII, as Mob-Set number ->
# the ``MOBS_TIP.s_NAME`` bytes in cp874, hex.  EMPTY FOR THIS SCENE: every
# one of its 37 resolved sets carries an ASCII name (or, for set 53, none).
# The mechanism stays because it is the membership gate ``COO-DECISION
# 20260902_2146`` set - a future regeneration that brings in a Thai name
# must pin it here or ``_self_check`` refuses at import.
NAME_CP874_HEX: dict[int, str] = {}

# Placement index -> how many EXTRA xyz triples that row carries beyond its
# primary point.  None of them is shipped (see the module docstring); 656
# points in total across 18 of the 66 rows.
EXTRA_TRIPLES_NOT_SHIPPED = {
    5: 16,
    6: 17,
    7: 16,
    8: 18,
    9: 17,
    10: 11,
    11: 18,
    12: 22,
    13: 38,
    14: 60,
    15: 59,
    16: 42,
    44: 77,
    45: 56,
    46: 37,
    47: 54,
    48: 52,
    49: 46,
}


class Bg3007IdentityError(ValueError):
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
        raise Bg3007IdentityError("a pinned name must be a hex str")
    try:
        raw = bytes.fromhex(hex_bytes)
    except ValueError as failure:
        raise Bg3007IdentityError(
            "a pinned name must be hex bytes: %s" % (failure,)) from failure
    try:
        text = raw.decode(NAME_ENCODING, "strict")
    except UnicodeDecodeError as failure:
        raise Bg3007IdentityError(
            "a pinned name must decode as %s" % NAME_ENCODING) from failure
    if text.encode(NAME_ENCODING, "strict") != raw:
        raise Bg3007IdentityError("a pinned name must round-trip through %s"
                                  % NAME_ENCODING)
    if text.isascii():
        raise Bg3007IdentityError(
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
# 37 rows: every first-leg Mob-Set number this scene's placements use that
# CLINE type 3007 resolves to a shippable body.
_RESOLVED_ROWS = (
    (1, 61400, 8000, 'SP_007_000_000_SP1', 'Ulysses', '', 1, 0, 106, 7),
    (3, 61402, 8002, 'SP_003_000_000_N', 'Bismarck', '', 1, 0, 106, 7),
    (4, 61403, 8003, 'SP_011_000_000_SP1', 'Yamato', '', 1, 0, 106, 7),
    (5, 61404, 8004, 'SP_006_000_000_N', 'Black beard', '', 1, 0, 106, 7),
    (6, 61405, 8005, 'SP_006_000_000_N', 'Red beard', '', 1, 0, 106, 7),
    (9, 61408, 8018, 'MAP_ISLAND_01', 'Mad Sand Island', '', 1, 0, 106, 2),
    (10, 61409, 8019, 'MAP_ISLAND_01', 'Pirate Lair', '', 1, 0, 106, 2),
    (11, 61410, 8024, 'SP_000_000_000_N', 'Merchant Ship', '', 1, 0, 106, 7),
    (12, 61411, 8025, 'SP_001_000_000_N', 'Merchant marine Trade Ship', '',
     1, 0, 106, 2),
    (13, 61412, 8026, 'SP_001_000_000_N', 'Merchant marine Trade Ship', '',
     1, 0, 106, 2),
    (14, 61413, 8027, 'SP_001_000_000_N', 'Merchant marine Trade Ship', '',
     1, 0, 106, 2),
    (21, 61420, 8045, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0,
     335459, 7),
    (22, 61421, 8046, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0,
     335459, 7),
    (24, 61423, 8048, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0,
     335459, 7),
    (25, 61424, 8049, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0,
     335459, 7),
    (26, 61425, 8050, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0,
     335459, 7),
    (27, 61426, 8051, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0,
     335459, 7),
    (28, 61427, 8052, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0,
     335459, 7),
    (29, 61428, 8053, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0,
     335459, 7),
    (30, 61429, 8054, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0,
     335459, 7),
    (33, 61432, 8057, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (35, 61434, 8059, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (36, 61435, 8060, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (37, 61436, 8061, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (38, 61437, 8062, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (39, 61438, 8063, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (41, 61440, 8065, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (42, 61441, 8066, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (43, 61442, 8067, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (44, 61443, 8068, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (45, 61444, 8069, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (46, 61445, 8070, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (47, 61446, 8071, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (48, 61447, 8072, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (49, 61448, 3219, 'SP_000_000_000_N', 'Smuggling Ship', '', 1, 0, 106, 2),
    (52, 61451, 3224, 'SP_000_000_000_N', 'Pirate Ship', '', 1, 0, 106, 2),
    (53, 61452, 8167, 'INVISIBLE', '', '', 110, 0, 260787, 7),
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

# The one set this scene ships with an empty display name, and the outfit
# that makes it legal.  Named rather than left to a bare ``or ''``: an empty
# name anywhere else in this table is a mining fault.
NAMELESS_INVISIBLE_SETS = frozenset({53})
INVISIBLE_OUTFIT = "INVISIBLE"


@dataclass(frozen=True)
class Bg3007Placement:
    """One Bg3007 placement resolved to a real, bodied actor."""

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
#  placement file in file order.  The six rows whose raw column named two
#  sets are in ``MULTI_SET_PLACEMENTS``; no sentinel rows this scene.
_PLACEMENT_ROWS = (
    (0, 1, 1, -311.3564147949219, -861.8358764648438, 652.036376953125),
    (1, 3, 1, -4497.509765625, 608.23828125, 130.6864013671875),
    (2, 4, 1, -1934.8253173828125, 456.7029113769531, 123.57420349121094),
    (3, 5, 1, 1776.2794189453125, 2926.828125, 123.57420349121094),
    (4, 6, 1, 3669.3916015625, 1766.3955078125, 123.57420349121094),
    (5, 11, 1, -1632.479736328125, -1051.109130859375, 123.57279968261719),
    (6, 11, 2, -915.69873046875, -6053.6435546875, 123.5708999633789),
    (7, 11, 3, 4477.466796875, -3009.5625, 40.85639953613281),
    (8, 11, 4, -4827.9208984375, 4394.46484375, 107.43280029296875),
    (9, 11, 5, -1230.8751220703125, -807.36572265625, 123.57469940185547),
    (10, 11, 6, 6367.4453125, 4072.68603515625, 88.63200378417969),
    (11, 11, 7, 9627.546875, -28.993200302124023, 123.57559967041016),
    (12, 11, 8, 5888.0234375, 3902.27880859375, 93.29229736328125),
    (13, 11, 9, -3495.899658203125, 432.6836853027344, 227.66639709472656),
    (14, 12, 1, -8901.912109375, 8772.23828125, 123.57610321044922),
    (15, 13, 1, 7609.751953125, 5781.330078125, 123.57450103759766),
    (16, 14, 1, -9018.0576171875, -6831.6826171875, 123.57340240478516),
    (17, 21, 1, 4267.4208984375, 2857.47021484375, 253.685302734375),
    (18, 22, 1, 4413.212890625, -90.30570220947266, 506.3276062011719),
    (19, 24, 1, 3821.05029296875, -3711.4287109375, 265.2544860839844),
    (20, 25, 1, -2331.830078125, -6050.01318359375, 146.65780639648438),
    (21, 26, 1, -3116.25048828125, -3554.098876953125, 146.64840698242188),
    (22, 27, 1, 6181.923828125, 2540.0966796875, 307.7533874511719),
    (23, 28, 1, 6891.52392578125, 5206.0302734375, 320.99749755859375),
    (24, 29, 1, 6263.80224609375, -5303.13134765625, 237.57080078125),
    (25, 30, 1, 4112.240234375, 5049.19384765625, 146.648193359375),
    (26, 33, 1, 6916.0419921875, 255.63510131835938, 390.6131896972656),
    (27, 35, 1, 444.57958984375, 3094.766357421875, 199.5240936279297),
    (28, 36, 1, -2182.877197265625, 3837.794189453125, 553.24658203125),
    (29, 37, 1, -515.1071166992188, -164.68850708007812, 447.4715881347656),
    (30, 38, 1, -6857.3603515625, -5537.8623046875, 146.65310668945312),
    (31, 39, 1, 350.5541076660156, -4272.47900390625, 744.230712890625),
    (32, 41, 1, -7142.22705078125, 4568.212890625, 146.65310668945312),
    (33, 42, 1, 1480.4150390625, -1831.6409912109375, 458.1278991699219),
    (34, 43, 1, 5960.52685546875, -782.6343994140625, 617.8073120117188),
    (35, 44, 1, 3813.913818359375, -1455.36328125, 530.6533813476562),
    (36, 45, 1, 1836.23779296875, 6332.08642578125, 146.65780639648438),
    (37, 46, 1, 6759.48291015625, -2901.60546875, 471.3782958984375),
    (38, 47, 1, 2069.51513671875, -5711.68310546875, 393.5315856933594),
    (39, 48, 1, -4947.28515625, 2552.5498046875, 399.9930114746094),
    (40, 49, 1, 1479.5537109375, -4756.62744140625, 420.2355041503906),
    (41, 52, 1, -1511.81591796875, 4851.31201171875, 123.64689636230469),
    (42, 9, 1, 5029.70654296875, -4590.55419921875, 123.57420349121094),
    (43, 10, 1, -2122.693115234375, -3974.025634765625, 123.57420349121094),
    (44, 53, 1, -5041.68359375, -5876.31494140625, 85.99939727783203),
    (45, 53, 2, 2825.9296875, -5705.52587890625, 86.0),
    (46, 53, 3, -1250.78125, 1583.89111328125, 86.0),
    (47, 53, 4, 6464.142578125, 1437.324951171875, 86.0),
    (48, 53, 5, -6839.71875, 3727.962158203125, 86.0),
    (49, 53, 6, 5673.39453125, -3044.771240234375, 85.9988021850586),
    (50, 55, 1, -6331.75537109375, 1310.9356689453125, 86.00468444824219),
    (51, 56, 1, -6141.376953125, 1124.2457275390625, 85.99971008300781),
    (52, 57, 1, -7066.48486328125, 809.62158203125, 86.0),
    (53, 58, 1, -6888.77001953125, 615.992431640625, 86.0),
    (54, 56, 2, -6504.16357421875, 1491.30224609375, 86.0023422241211),
    (55, 56, 3, -6687.1826171875, 1682.2791748046875, 86.0023422241211),
    (56, 56, 4, -5931.23486328125, 934.2880249023438, 86.0023422241211),
    (57, 56, 5, -5846.35595703125, 1273.80126953125, 86.0023422241211),
    (58, 56, 6, -6045.28857421875, 1531.08935546875, 86.0023422241211),
    (59, 56, 7, -6323.796875, 1711.4559326171875, 86.0023422241211),
    (60, 58, 2, -6705.75048828125, 382.57684326171875, 86.0),
    (61, 58, 3, -7294.59521484375, 992.6412353515625, 86.0),
    (62, 58, 4, -7490.87744140625, 1199.5328369140625, 86.0),
    (63, 58, 5, -7596.974609375, 923.6775512695312, 86.0),
    (64, 58, 6, -7395.38818359375, 642.5172119140625, 86.0),
    (65, 58, 7, -7177.88720703125, 409.10137939453125, 86.0),
)

PLACEMENT_COUNT = len(_PLACEMENT_ROWS)


def identity_for(template_id: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    ``None`` is exactly the 4 sets in ``UNRESOLVED`` and nothing else: this
    function never substitutes, and never falls back to the Mob-Set number
    itself, which is the specific regression ``GT-078`` was.
    """
    if type(template_id) is not int or type(template_id) is bool:
        raise Bg3007IdentityError("template id must be an int")
    return IDENTITIES.get(template_id)


def shippable_placements() -> tuple[Bg3007Placement, ...]:
    """The 50 placements of the 66 that resolve to an identity."""
    out = []
    for index, template_id, mm_instance, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(template_id)
        if identity is None:
            continue
        out.append(Bg3007Placement(
            index, template_id, mm_instance, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The 16 that are dropped, with the id and the reason.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH ones and WHY.
    """
    out = []
    for index, template_id, _mm, x, y, z in _PLACEMENT_ROWS:
        if template_id in IDENTITIES:
            continue
        cline_row_id, leader, reason = UNRESOLVED.get(
            template_id, (0, 0, "set not in CLINE 3007"))
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
        raise Bg3007IdentityError("evidence_name needs a SceneIdentity")
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
    if len(_RESOLVED_ROWS) != 37:
        raise Bg3007IdentityError(
            "expected 37 resolved sets, found %d" % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg3007IdentityError("duplicate Mob-Set number in the table")
    if len(UNRESOLVED) != 4:
        raise Bg3007IdentityError(
            "expected 4 unresolved sets, found %d" % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg3007IdentityError("a set is both resolved and unresolved")
    if set(IDENTITIES) & set(SECOND_LEG_ONLY):
        raise Bg3007IdentityError(
            "a second-leg-only key is also shipped as a first leg")
    if len(_PLACEMENT_ROWS) != 66:
        raise Bg3007IdentityError(
            "expected 66 placements, found %d" % len(_PLACEMENT_ROWS))
    # Control 1: every first-leg Mob-Set number this scene's placements use
    # is either resolved or named as unresolved, and the two sets together
    # are EXACTLY this scene's used keys - a placement keyed by a number
    # this table has never heard of means the placement file and the
    # crosswalk came from different extractions.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if scene_sets != table_sets:
        raise Bg3007IdentityError(
            "placement Mob-Set numbers and this table's keys disagree: %r"
            % sorted(scene_sets ^ table_sets))
    if len(table_sets) != 41:
        raise Bg3007IdentityError(
            "expected 41 distinct Mob-Set numbers, found %d" % len(table_sets))
    # Control 2: the placement file's own running instance counts.  A row
    # whose count restarts or skips means the rows were reordered after the
    # table was generated, which would silently re-key every actor.
    seen: dict[int, int] = {}
    for index, template_id, mm_instance, _x, _y, _z in _PLACEMENT_ROWS:
        seen[template_id] = seen.get(template_id, 0) + 1
        if mm_instance != seen[template_id]:
            raise Bg3007IdentityError(
                "placement %d claims instance %d of set %d, expected %d"
                % (index, mm_instance, template_id, seen[template_id]))
    # Every multi-set placement must BE one of this table's rows, keyed by
    # the first leg of its own raw string.
    indices = {row[0]: row[1] for row in _PLACEMENT_ROWS}
    for index, raw in MULTI_SET_PLACEMENTS.items():
        if index not in indices:
            raise Bg3007IdentityError(
                "multi-set placement %d is not in the placement table" % index)
        legs = raw.split("|")
        if len(legs) < 2 or not all(leg.isdigit() for leg in legs):
            raise Bg3007IdentityError(
                "multi-set placement %d has a malformed raw column %r"
                % (index, raw))
        if indices[index] != int(legs[0]):
            raise Bg3007IdentityError(
                "multi-set placement %d does not ship its first leg" % index)
        for leg in legs[1:]:
            if int(leg) in IDENTITIES:
                raise Bg3007IdentityError(
                    "second leg %s of placement %d is shipped as well"
                    % (leg, index))
    for index in EXTRA_TRIPLES_NOT_SHIPPED:
        if index not in indices:
            raise Bg3007IdentityError(
                "extra-triple row %d is not in the placement table" % index)
    if not no_set_number_is_shipped_as_identity():
        raise Bg3007IdentityError(
            "a row ships its own Mob-Set number as an identity")
    for row in _RESOLVED_ROWS:
        (template_id, cline_row_id, n_id, outfit, name, title, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1 or n_id < 1:
            raise Bg3007IdentityError(
                "set %d carries no CLINE row or leader locator" % template_id)
        if ";" in outfit or "|" in outfit:
            raise Bg3007IdentityError(
                "set %d ships a multi-variant outfit string" % template_id)
        if not outfit or not outfit.isascii():
            raise Bg3007IdentityError(
                "set %d has an empty or non-ASCII outfit" % template_id)
        # NAMES.  ``COO-DECISION 20260902_2146`` shape 1: a non-ASCII name
        # must round-trip through cp874 AND be pinned as bytes in
        # ``NAME_CP874_HEX``, so a name can never arrive here by some other
        # route.  TITLES are untouched and still ASCII.
        if not title.isascii():
            raise Bg3007IdentityError(
                "set %d has a non-ASCII title" % template_id)
        if not name.isascii():
            pinned = NAME_CP874_HEX.get(template_id)
            if pinned is None:
                raise Bg3007IdentityError(
                    "set %d has a non-ASCII name that is not pinned in "
                    "NAME_CP874_HEX" % template_id)
            if _cp874(pinned) != name:
                raise Bg3007IdentityError(
                    "set %d ships a name that is not its own pin"
                    % template_id)
        elif template_id in NAME_CP874_HEX:
            raise Bg3007IdentityError(
                "set %d is pinned in NAME_CP874_HEX but ships an ASCII name"
                % template_id)
        if not name and not (
            template_id in NAMELESS_INVISIBLE_SETS
            and outfit == INVISIBLE_OUTFIT
        ):
            # The bg0004 set-107 exception, narrowed to the one set that
            # earns it: a nameless row with a real body is a mining fault.
            raise Bg3007IdentityError(
                "set %d has no display name and is not the known nameless "
                "INVISIBLE set" % template_id)
        if max_hp < 1 or level < 1:
            raise Bg3007IdentityError("set %d has a bad level/HP" % template_id)
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
                raise Bg3007IdentityError(
                    "leg %s of placement %d has no measured MOBS_TIP answer"
                    % (leg, index))
    if set(SECOND_LEG_IDENTITIES) != set(SECOND_LEG_ONLY):
        raise Bg3007IdentityError("the second-leg views disagree")
    if not SHIPPED_COLUMNS_EXCEPT_MOBS_ID:
        raise Bg3007IdentityError("the leg comparison compares nothing")
    refusals = multi_set_placement_refusals()
    if refusals:
        raise Bg3007IdentityError(
            "multi-set placements refused by the gate (COO-DECISION "
            "20260902_2146 shape 2): %s"
            % "; ".join(
                "placement %d: %s" % (row["placement_index"], row["reason"])
                for row in refusals))
    if len(shippable_placements()) != 50:
        raise Bg3007IdentityError("expected 50 shippable placements")
    if len(unshippable_placements()) != 16:
        raise Bg3007IdentityError("expected 16 unshippable placements")
    ids = [p.actor_identity for p in shippable_placements()]
    if len(ids) != len(set(ids)):
        raise Bg3007IdentityError("actor identities collide within this table")


_self_check()
