"""Who each Bg3001 placement actually IS - Atlantis, the ocean panel's cast.

LANE-A (WORLD), round ``4uztfj``.  The eleventh crosswalk this lane has
built and the FIRST one outside the ten island doors ``COO-DECISION
2026-08-30T14:41+07:00`` approved: scene 126 (``Bg3001``, "Atlantis", 38
placements) is an ``n_SCENE_TYPE 8`` OCEAN PANEL, not an island, and its
cast is ships, islands-as-actors, sea monsters and weather markers rather
than townspeople.  This module is the identity half; ``world_population_
bg3001`` is the census half.

WHY THIS SCENE AND WHY NOW.  ``world_m2_sea_destination`` measured this
scene's census feasibility on 2026-08-29 (round ``02k3w5``) and left it as
a note: "if a later round ever needs its cast, the crosswalk resolves".
That round is this one.  A player CAN stand here today - not through the
ordinary login door, which is shut, but through the GM single-use grant
``CORE-REQUEST-GM-038`` landed for exactly this scene (``gm/
login_scene_admission.SANCTIONED_BARRED_SCENES`` names 126 and cites
``CHIEF-DECISION 20260829_1603`` item 2) - and what that player sees today
is an empty ocean.

THE DOOR IS NOT TOUCHED BY THIS ROUND.  ``login_entry_allowed`` for scene
126 stays ``false``.  ``COO-DECISION 20260829_1444`` requires an attended
var2 test before any flip, and this round does not flip it, ask for it, or
route around it: the ordinary login path still refuses this scene with
``REFUSED_NOT_ALLOWED_AT_LOGIN``, exactly as it did before this file
existed.  What changes is only what a session ALREADY STANDING in the
scene is sent.

THE CROSSWALK, RE-DERIVED HERE RATHER THAN TAKEN FROM A CITATION.
``SCENE_NAME[s_MODLE_ID=Bg3001]`` was read directly off the bridge clone
this round:

    SCENE_NAME[s_MODLE_ID=Bg3001].n_ID          = 126
    SCENE_NAME[s_MODLE_ID=Bg3001].n_CLINE_TYPE  = 3001  (a real value, direct)
    SCENE_NAME[s_MODLE_ID=Bg3001].n_SCENE_LV    = 0
    SCENE_NAME[s_MODLE_ID=Bg3001].n_SAVE        = 0     (see THE FACTION GAP)
    CLINE[(3001, <Mob-Set number>)].n_LEADER_BK1 = the real MOBS.n_ID
    MOBS[n_ID].s_OUTFIT                         = the avatar the client loads
    MOBS_TIP[n_ID].s_NAME / s_TITLE             = the label under the actor
    STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX      = max HP (the one derived col)

Same direct-selector shape the ten island crosswalks ship (one of RE-128's
19 direct CLINE types, not one of its 240 instance scenes).

WHAT IS ESTABLISHED HERE AND WHAT IS NOT.

    ESTABLISHED - THE TABLE.  This scene's cast is drawn from CLINE type
    3001's leader column.  CONTROL 1 is a SUBSET: the 38 placements use 25
    distinct first-leg Mob-Set numbers, all 25 present in CLINE type
    3001's own 56-row key range (1..56, no gaps, no duplicates - counted
    this round).  The registry's own ``native_definition_count`` for this
    scene reads 56 and CLINE type 3001 holds exactly 56 rows: an AGREEMENT,
    unlike bg0003's, bg0004's, bg0007's and bg0008's own off-by-one
    disagreements, and the same independent corroboration
    ``world_m2_sea_destination`` recorded for this block in August.

    NOT ESTABLISHED - THE PAIRING.  Which leader belongs to which Mob-Set
    number.  No human has stood in this scene (registry ``status:
    never_sent_to_any_client_by_this_project``), so every name below is a
    table inference until an attended round looks - the bottom of the
    evidence order COO set on 2026-08-28T21:30.

SIX PLACEMENTS NAME TWO MOB-SETS IN ONE FIELD, AND THAT SHAPE IS NEW HERE.
Placements 30-35 carry ``set_names = "Mob_Set_53|Mob_Set_54"`` and
``template_ids = "53|54"``.  Both legs resolve: 53 -> CLINE 60452 ->
MOBS 8167, 54 -> CLINE 60453 -> MOBS 8171, both ``s_OUTFIT INVISIBLE``,
both level 110, both with NO ``MOBS_TIP`` row at all (the two sea-weather
markers ``world_m2_sea_destination`` named in August, thunderstorm / dead
calm).  THE RULE THIS ROUND TAKES: ship the FIRST leg, keep the whole
string in ``MULTI_SET_PLACEMENTS``, and never let a raw ``|`` reach the
shipped column (``_self_check`` refuses at import if one does).  ~~[LANE-A ASSUMPTION -
AWAITING COO/OWNER CONFIRMATION.]~~  **CONFIRMED, ``COO-DECISION
20260902_2146`` shape 2**, and with a gate attached, because the ruling
turns on the REASON and not on the rule: what makes the first leg safe
here is that BOTH legs are invisible, unnamed and identical on every
column this module ships except the MOBS id - NOT that "the first leg
wins".  This shape has 98 placements across 16 scenes; left as a bare rule
it would one day swallow a visible monster in silence.

So ``MULTI_SET_GATE`` (executable, run by ``_self_check``, refuses at
import) rejects a multi-set placement when EITHER:

1. the legs disagree on any column this module ships except the MOBS id,
   or a leg's identity is not in this table at all - unknown is not equal;
   or
2. any leg is not ``INVISIBLE``, or any leg HAS a ``MOBS_TIP`` row (a body
   that can be seen, or a name plate that can be read).

A rejected placement must NOT quietly ship its first leg: it goes to
``UNRESOLVED`` and the COO gets a letter.  Measured for this scene:
53 -> CLINE 60452 -> MOBS 8167 and 54 -> CLINE 60453 -> MOBS 8171 are both
``INVISIBLE``, level 110, rank 0, usage 7, HP 260787, with NO ``MOBS_TIP``
row on either - so all six placements pass the gate rather than being
exempt from it.  ``COO-DECISION 20260902_2146`` also bars applying the
first-leg rule to the other 16 scenes until this gate is on ``main``.

Set 54 is therefore a key CLINE HAS that no shipped row uses, recorded in
``SECOND_LEG_ONLY`` rather than left to look like an omission - the same
shape bg0011's untouched key 106 carries, and now carrying the second
leg's full shipped columns so the gate can COMPARE rather than assert.

~~TWO SETS DO NOT RESOLVE (COST 2 PLACEMENTS), TWO DIFFERENT SHAPES.~~
ONE SET DOES NOT RESOLVE (COSTS 1 PLACEMENT) SINCE ROUND ``gx7xtp``.  The
second shape is kept below, struck, because it is the shape a future
non-ASCII name will be read against.

* Set 16 -> CLINE row 60415, whose ``n_LEADER_BK1`` is literally ``0`` -
  the only zero-leader row in the block (measured, and the same row
  ``world_m2_sea_destination`` flagged in August).  Costs placement 28.
  Same "leader is literally 0" shape bg0007's set 111 carries.
* ~~Set 56 -> CLINE row 60455 -> MOBS 8180, a real bodied row
  (``M081_000_000_N``, level 60) whose ``MOBS_TIP.s_NAME`` is THAI, not
  ASCII.  A NEW failure shape for this lane: every earlier drop of this
  kind was CJK, which ``cp874`` cannot encode at all, while Thai is
  precisely what cp874 CAN encode.  This round still drops it, for the
  narrower reason that this lane's evidence layer - ``actor_lines``, the
  census console line, the ticket a tester copies - is ASCII by contract,
  and shipping a name the headless proof cannot print is how a shortfall
  becomes invisible.  Costs placement 37.~~  **STRUCK, round ``gx7xtp``:
  ``COO-DECISION 20260902_2146`` shape 1 OVERRULED this drop.**  Set 56
  SHIPS.  The ruling and its reason: this is a Thai game, the table
  encodes, the client draws - the only layer that could not print the name
  was OUR console, and cutting a real actor out of a real scene because
  the evidence layer cannot print it is the tool commanding the game.  The
  ASCII contract is not loosened, it is SPLIT (see THE TWO NAME LAYERS).
  Costs placement 37 nothing; this scene now ships 37 of 38.

THE TWO NAME LAYERS, SPLIT BY ``COO-DECISION 20260902_2146`` SHAPE 1.
One name, two contracts, and neither is weakened:

* THE SHIPPED COLUMN carries the real ``MOBS_TIP.s_NAME``, Thai included.
  What actually reaches the client is measured, not assumed: the frozen
  serializer's ``wstr_tag`` puts a display name on the wire as
  **UTF-16LE**, not as cp874 bytes - so the wire never had a cp874 problem
  to begin with.  ~~the shipped column is cp874 bytes~~ is the one premise
  of that decision this round had to correct; it changes no row, because
  cp874 still decides MEMBERSHIP (below), just not the transport.  The
  correction went to the COO in this round's letter.
* THE EVIDENCE LAYER - ``actor_lines``, the census console line, the
  ticket a tester copies - stays ASCII, and ``isascii()`` is NOT loosened
  anywhere it already stood.  A non-ASCII name prints as
  ``name_cp874_hex=<hex>`` beside ``placement=<n>``, so a tester can still
  copy the whole ticket out of a cp874 console AND still say which row is
  meant.  ``evidence_name`` is the one function that does this.

THE MEMBERSHIP GATE THAT COMES WITH SHIPPING A NAME.  A display name may
ship only if it round-trips through **cp874**, and the source of this
module stays pure ASCII (house rule), so a non-ASCII name is pinned as its
cp874 bytes in ``NAME_CP874_HEX`` and decoded at import by ``_cp874``.
That single mechanism enforces the decision's own exception: bg0006's CJK
names cannot be expressed at all this way, so they still land in
``UNRESOLVED``, exactly as the decision requires.  A name that IS ASCII
must be written as the literal - the hex form is for names that need it.

NO EMPTY-``s_OUTFIT`` FAMILY HERE, which is worth naming because every
island scene had one: this scene's placements never touch a 101+ block, so
the "path-finding helper, not a creature" drop that cost bg0003 nine rows
and bg0011 five costs this scene nothing.

FIVE SETS SHIP ``INVISIBLE``, NOT DROPPED, AND THE PRECEDENT IS EXPLICIT.
Sets 31, 32, 34 and 40 are four separate ``Tornado`` rows and set 53 is the
weather marker above.  ``INVISIBLE`` is a real, non-empty ``s_OUTFIT``
string, so the refusal rule every crosswalk in this project keys on (an
EMPTY outfit column) does not fire - the same reading ``world_bg0004_
identity`` set 107 and ``world_port_royal_identity``'s own leader 917 ship
under today.  Set 53's rows additionally have no name, which bg0004's set
107 also has and ships.  Nobody has seen what a client draws for an
invisible actor with a name plate that says ``Tornado``; this module ships
them because CHARTER-02 calls for building the known shape around the hole.

814 EXTRA SPAWN POINTS EXIST AND NONE OF THEM IS SHIPPED.  22 of the 38
placement rows carry ``extra_triple_count > 0`` (11 to 85 each, 814 in
total) - by far the biggest such block this lane has met, where bg0004's
single extra triple was the only one before it.  This module ships ONLY
the 38 primary points, the number the registry's own ``native_placement_
count`` cites, and records the per-row counts in ``EXTRA_TRIPLES_NOT_
SHIPPED``.  Whether those triples are a patrol path or 814 more actors is
NOT established (``world_density`` carries the same open question by name,
``are_the_extra_triples_spawn_points_or_paths``), and inventing 814 actors
on an unmeasured reading would move this round's own target by a factor of
twenty.

THE FACTION GAP, NAMED RATHER THAN HIDDEN.  ``SCENE_NAME.n_SAVE`` is 0 for
this scene, and ``world_faction_admission.admits`` requires
``login_entry_allowed AND n_SAVE == 1``.  So a login into scene 126 emits
NO ``PLAYER_FACTION`` frame, exactly as scene 14's own D3 debt describes.
This module does not widen that guard (shipping an unmeasured wire shape is
the decision ``COO-DECISION 20260828_2345`` requires an ask for).  What it
costs here is smaller than it was for scene 14: every row this file ships
is ``n_MOB_USAGE`` 2 or 7 (NPC/prop shapes) except the Jellyfish King, and
no LANE-B combat roster names this scene at all.

NO CREW, AND ONE THING THAT IS NOT CREW AND IS STILL DROPPED.  Measured:
0 of CLINE type 3001's 56 rows carry any ``n_CREW`` value (``n_CREW1``..
``n_CREW6`` all read 0), so there is no pet/crew group this leader-only
reading silently drops.  BUT ``n_LEADER_BK2``/``n_LEADER_BK3`` are a
different column family and this scene DOES use them: CLINE row 60410
(Mob-Set 11, the scene's densest set -- 9 of the ~~36~~ 37 shipped rows)
carries back-up leaders 8165 and 8166, both real ``MOBS`` rows wearing the
same ``SP_001_000_000_N`` hull at level 1.  Like every crosswalk in this
project this module implements ``n_LEADER_BK1`` ONLY, so those two are
dropped -- written here because a paragraph headed NO CREW is where the
next reader stops (pf-adversary, round ``4uztfj``).

NO NAME-VS-TEMPLATE DISAGREEMENT, NO MULTI-VARIANT OUTFIT, NO EXTRACTION
SENTINEL, NO EMPTY ``set_names``.  Checked directly against this scene's
own placement file: no shipped ``s_OUTFIT`` contains ``;`` (this scene does
not repeat the ten islands' two-variant families at all), no row's
``template_ids`` column reads the literal ``UNRESOLVED``, and every row
carries a ``set_names`` value whose numeric tail matches its
``template_ids`` column.

HEADING, MEASURED ON THIS SCENE'S OWN FILE.  ``f32_3`` is ``0.0`` on all
38 rows; ``f32_4`` takes 11 values (500, 1000, 1500, 5000, 6000, 7000,
8000, 9000, 11000, 12000, 25000) and ``f32_5`` 11 values (800, 1200, 3000,
6000, 7000, 8000, 9000, 10000, 12000, 13000, 26000).  ~~a small
round-number set - 0/300 and 500 and 800/1200/3500~~ -- STRUCK,
pf-adversary, round ``4uztfj``: 300 and 3500 appear NOWHERE in this
scene's file.  That was a sibling scene's set, quoted in the one module
whose framing is "re-derived here rather than taken from a citation" --
the exact failure this file exists to avoid.  The conclusion is unchanged
and now rests on this scene's own numbers: round thousands that scale with
the placement rather than with any facing, the shape of a radius and not a
rotation, so the census half reuses ``world_population.HEADINGS`` on the
placement index.

PROVENANCE.  Every row below was generated from these six committed
artifacts and nothing else, by a throwaway script run against the bridge
clone this round (the tables are large enough that hand transcription
would itself be an error source); the script's output is what appears
below, unedited except for formatting:

    gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv
    gamedata/tables/CONSTDATA_TH__CLINE.tsv
    gamedata/tables/CONSTDATA_TH__MOBS.tsv
    gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv
    gamedata/tables/CONSTDATA_TH__STANDARD_MOB.tsv
    gamedata/scene/Bg3001/Bg3001.placements.tsv

THE JOIN, EXACTLY, SO IT CAN BE MECHANISED LATER:

    keys   = {r.n_CREATURE_TYPE: r for r in CLINE if r.n_CLINE_TYPE == 3001}
    for each FIRST-LEG Mob-Set number k this scene's placements use (25):
        leader = keys[k].n_LEADER_BK1
        drop k if leader is 0 or MOBS has no row for it, or that row's
            s_OUTFIT is empty, or MOBS_TIP.s_NAME/s_TITLE is not ASCII
        else row = (k, keys[k].n_ID, leader, s_OUTFIT,
                    MOBS_TIP.s_NAME or '', MOBS_TIP.s_TITLE or '',
                    MOBS.n_LEVEL_MIN, MOBS.n_RANK,
                    STANDARD_MOB[n_LEVEL_MIN].n_HPMAX, MOBS.n_MOB_USAGE)
    placements = every row of Bg3001.placements.tsv as
        (index, first-leg template id, running instance count, x, y, z)

WHAT THIS MODULE DOES NOT CLAIM.

* Not that any of these ~~36~~ 37 actors has been SEEN.  No human has been in
  this scene in this project's history.
* Not that this scene is where a Columbus crossing lands a player.  It is
  not: ``world_m2_sea_destination`` settled that in August - the Columbus
  row's ``n_VARI_2`` is 17, and 126 is the OCEAN PANEL NAME that option
  advertises.  This module makes no route claim at all, and the word for
  what Columbus offers is deliberately not written here: see
  ``world_m2_sea_destination`` for it, and ``tests/
  test_npc_interaction_wire.py``'s own guard for why a foundation module
  does not carry that vocabulary.
* Not that ``MAP_ISLAND_01`` actors ("Mad Sand Island", "Pirate Lair",
  "Blood Blade Island", "Lonely Island") render as islands rather than as
  ordinary actor bodies.  They are rows in the same table with the same
  serializer; what the client does with that avatar name is unmeasured.
* Not leader+crew: like every sibling crosswalk this implements
  ``n_LEADER_BK1`` only, and this scene has no crew columns set at all.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass


# Convention marker: shippable, no scenario flag - matching the ten sibling
# crosswalk modules' own convention.
production_allowed = True
test_only = False

SCENE_N_ID = 126
SCENE_MODEL_ID = "Bg3001"
SCENE_CLINE_TYPE = 3001
# SCENE_NAME.n_SCENE_LV for this scene.  Zero, unlike every island door
# this lane has opened (25..95) - an ocean panel carries no level band.
SCENE_DECLARED_LEVEL = 0
# SCENE_NAME.n_SAVE for this scene.  Kept as a named constant because
# ``world_faction_admission`` refuses on it - see THE FACTION GAP above.
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
    "gamedata/scene/Bg3001/Bg3001.placements.tsv":
        '63a61fcfa6f48d548f2dede28a41a79dbdb2f81c6cb824cb5246c5e31fd1c0e1',
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  Costs 1 of the 38
# placements (index 28).  Set 56 used to be the second entry here and is
# now SHIPPED - ``COO-DECISION 20260902_2146`` shape 1, round ``gx7xtp``;
# the struck paragraph in the module docstring keeps why it was dropped.
UNRESOLVED = {
    16: (60415, 0, 'CLINE row carries leader 0, no CONSTDATA MOBS row'),
}

# Placements whose ``template_ids`` column names TWO Mob-Set numbers, as
# placement index -> the whole raw string.  The table below ships the FIRST
# leg; ``_self_check`` refuses if a raw '|' ever reaches a shipped column,
# and ``MULTI_SET_GATE`` (below) refuses if the legs are not the
# interchangeable pair that makes shipping the first one safe.
# Confirmed by ``COO-DECISION 20260902_2146`` shape 2, with that gate.
MULTI_SET_PLACEMENTS = {
    30: '53|54',
    31: '53|54',
    32: '53|54',
    33: '53|54',
    34: '53|54',
    35: '53|54',
}

# The second legs of the rows above: real CLINE keys, resolvable, never
# shipped under the first-leg rule.  Recorded so the key looks like a
# decision rather than an omission - and carried in the SAME ten-column
# row shape as ``_RESOLVED_ROWS`` so ``MULTI_SET_GATE`` can compare the
# legs column by column instead of asserting they match.  Re-derived off
# the tables this round (``gx7xtp``), not copied from the first-leg row.
_SECOND_LEG_ROWS = (
    (54, 60453, 8171, 'INVISIBLE', '', '', 110, 0, 260787, 7),
)

# Whether each leg of a multi-set placement has a ``TEXTDATA_TH__MOBS_TIP``
# row at all - measured, because "no name" and "no name plate" are
# different facts and the gate turns on the second one.  Both legs of this
# scene's only multi-set pair have NO tip row (checked this round against
# ``TEXTDATA_TH__MOBS_TIP.tsv`` by MOBS.n_ID: 8167 absent, 8171 absent).
MULTI_SET_LEG_HAS_TIP_ROW = {
    53: False,
    54: False,
}

# Display names this table ships that are not ASCII, as Mob-Set number ->
# the ``MOBS_TIP.s_NAME`` bytes in cp874, hex.  The bytes rather than the
# characters because every committed file in this lane is ASCII (the
# bridge console is cp874 and a source file has to survive being opened
# there); ``_cp874`` decodes and round-trips them at import.  cp874 is
# also the MEMBERSHIP test ``COO-DECISION 20260902_2146`` set: a name that
# cannot be expressed here - bg0006's CJK - cannot ship.
#   56: MOBS_TIP[8180].s_NAME, 5 bytes, Thai.
NAME_CP874_HEX = {
    56: 'a1c3d0b7a7',
}

# Placement index -> how many EXTRA xyz triples that row carries beyond its
# primary point.  None of them is shipped (see the module docstring); 814
# points in total across 22 of the 38 rows.
EXTRA_TRIPLES_NOT_SHIPPED = {
    5: 16,
    6: 17,
    7: 16,
    8: 18,
    9: 29,
    10: 11,
    11: 18,
    12: 22,
    13: 38,
    14: 60,
    15: 59,
    16: 42,
    17: 40,
    28: 40,
    29: 55,
    30: 33,
    31: 35,
    32: 48,
    33: 36,
    34: 43,
    35: 53,
    37: 85,
}


class Bg3001IdentityError(ValueError):
    """A refusal from this module, always with a reason in the message."""


# The one encoding that decides whether a display name may ship at all.
# Not the transport - the wire carries a name as UTF-16LE (`wstr_tag`) -
# but the client's own locale, which is what makes a Thai name renderable
# and a CJK one not.  See THE MEMBERSHIP GATE in the module docstring.
NAME_ENCODING = "cp874"


def _cp874(hex_bytes: str) -> str:
    """Decode a pinned non-ASCII display name, refusing at import if the
    pin is not what it claims to be.

    Three refusals, all fail-closed, all at import time:

    * bytes that are not valid ``cp874`` - the membership gate itself;
    * bytes that do not round-trip (``cp874`` maps several undefined
      positions lossily, and a name that comes back different is a name
      the client would not draw);
    * a pin whose text is ASCII after all - that row must carry the
      literal, so the table stays readable to the next person.
    """
    if type(hex_bytes) is not str:
        raise Bg3001IdentityError("a pinned name must be a hex str")
    try:
        raw = bytes.fromhex(hex_bytes)
    except ValueError as exc:
        raise Bg3001IdentityError(
            "pinned name %r is not hex: %s" % (hex_bytes, exc)) from exc
    if not raw:
        raise Bg3001IdentityError("pinned name %r is empty" % hex_bytes)
    try:
        text = raw.decode(NAME_ENCODING)
    except UnicodeDecodeError as exc:
        raise Bg3001IdentityError(
            "pinned name %r is not %s: %s" % (hex_bytes, NAME_ENCODING, exc)
        ) from exc
    if text.encode(NAME_ENCODING, "strict") != raw:
        raise Bg3001IdentityError(
            "pinned name %r does not round-trip through %s"
            % (hex_bytes, NAME_ENCODING))
    if text.isascii():
        raise Bg3001IdentityError(
            "pinned name %r is ASCII - write it as the literal" % hex_bytes)
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
# 24 rows: every first-leg Mob-Set number this scene's placements use that
# CLINE type 3001 resolves to a shippable body.
_RESOLVED_ROWS = (
    (2, 60401, 8001, 'SP_001_000_000_N', 'Intrepid', '', 1, 0, 106, 7),
    (7, 60406, 8006, 'SP_003_000_000_N', 'Santa Maria', '', 1, 0, 106, 7),
    (8, 60407, 8007, 'SP_008_000_000_N', 'Skull Phantom', '', 1, 0, 106, 7),
    (9, 60408, 8018, 'MAP_ISLAND_01', 'Mad Sand Island', '', 1, 0, 106, 2),
    (10, 60409, 8019, 'MAP_ISLAND_01', 'Pirate Lair', '', 1, 0, 106, 2),
    (11, 60410, 8024, 'SP_000_000_000_N', 'Merchant Ship', '', 1, 0, 106, 7),
    (12, 60411, 8025, 'SP_001_000_000_N', 'Merchant marine Trade Ship', '',
     1, 0, 106, 2),
    (13, 60412, 8026, 'SP_001_000_000_N', 'Merchant marine Trade Ship', '',
     1, 0, 106, 2),
    (14, 60413, 8027, 'SP_001_000_000_N', 'Merchant marine Trade Ship', '',
     1, 0, 106, 2),
    (15, 60414, 8028, 'M020_000_001_PET', 'Sea Monster Fish', '', 5, 0, 191, 2),
    (17, 60416, 8041, 'M031_000_000_SP1', 'Jellyfish King', '', 60, 64,
     43275, 1),
    (18, 60417, 8042, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0,
     335459, 7),
    (19, 60418, 8043, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0,
     335459, 7),
    (20, 60419, 8044, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0,
     335459, 7),
    (23, 60422, 8047, 'SP_005_000_000_N', 'Pirate Ship', '', 120, 0,
     335459, 7),
    (31, 60430, 8055, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (32, 60431, 8056, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (34, 60433, 8058, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (40, 60439, 8064, 'INVISIBLE', 'Tornado', '', 1, 0, 106, 7),
    (50, 60449, 3220, 'MAP_ISLAND_01', 'Blood Blade Island', '', 1, 0, 106, 2),
    (51, 60450, 3222, 'MAP_ISLAND_01', 'Lonely Island', '', 1, 0, 106, 2),
    (53, 60452, 8167, 'INVISIBLE', '', '', 110, 0, 260787, 7),
    (55, 60454, 8173, 'SP_001_000_000_N', 'Repair ship', '', 1, 0, 106, 7),
    # The Thai name COO-DECISION 20260902_2146 shape 1 put back on the
    # wire.  MOBS 8180 is a real bodied row - it was never the body that
    # was in doubt, only whether our console could print the label.
    (56, 60455, 8180, 'M081_000_000_N', _cp874(NAME_CP874_HEX[56]), '',
     60, 1, 43275, 1),
)

IDENTITIES = {row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS}

# The second legs, in the same object shape as ``IDENTITIES`` so the gate
# compares like with like.  Never merged into ``IDENTITIES``: these keys
# are deliberately not shippable.
SECOND_LEG_IDENTITIES = {
    row[0]: SceneIdentity(*row) for row in _SECOND_LEG_ROWS
}

# Backwards-compatible view of the same rows: set -> (CLINE row, leader).
SECOND_LEG_ONLY = {row[0]: (row[1], row[2]) for row in _SECOND_LEG_ROWS}

# The fields of ``SceneIdentity`` that are LOCATORS rather than shipped
# columns, plus the one column the decision allows the legs to differ on.
# Named here so the derivation below can be read as "everything else".
_LEG_COMPARISON_EXEMPT = ("template_id", "cline_row_id", "mobs_n_id")

# The columns this module SHIPS, minus the MOBS id.  ``COO-DECISION
# 20260902_2146`` shape 2 names exactly this set: the legs of a multi-set
# placement may differ on the MOBS number and on nothing else.  The CLINE
# row id and the Mob-Set number are locators, not shipped columns - two
# legs are two CLINE rows by definition, so comparing them would refuse
# every pair that exists.
#
# DERIVED, NOT TYPED (pf-adversary, round ``gx7xtp``, D5).  Written by hand
# this was a tuple nothing checked for completeness: deleting ``"rank"``
# from it left the whole suite green, and the next multi-set pair with a
# rank-64 leg beside a rank-0 leg would have been called interchangeable
# and shipped a boss as a mook.  Now a column added to ``SceneIdentity``
# joins the comparison by existing.
SHIPPED_COLUMNS_EXCEPT_MOBS_ID = tuple(
    field.name for field in dataclasses.fields(SceneIdentity)
    if field.name not in _LEG_COMPARISON_EXEMPT
)

# The one set this scene ships with an empty display name, and the outfit
# that makes it legal.  Named rather than left to a bare ``or ''``: an
# empty name anywhere else in this table is a mining fault, and
# ``_self_check`` treats it as one.
NAMELESS_INVISIBLE_SETS = frozenset({53})
INVISIBLE_OUTFIT = "INVISIBLE"


@dataclass(frozen=True)
class Bg3001Placement:
    """One Bg3001 placement resolved to a real, bodied actor."""

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
    (0, 2, 1, 182.6383056640625, 1140.40087890625, 123.57350158691406),
    (1, 7, 1, -67.45040130615234, -2806.41796875, 123.57389831542969),
    (2, 8, 1, 3707.42041015625, -5245.1943359375, 123.57420349121094),
    (3, 9, 1, -5593.45361328125, -5943.873046875, 123.57250213623047),
    (4, 10, 1, 2607.32275390625, 6200.05078125, 123.57240295410156),
    (5, 11, 1, -461.872314453125, -1850.048095703125, 123.57279968261719),
    (6, 11, 2, -915.6986083984375, -6053.642578125, 123.5708999633789),
    (7, 11, 3, 4477.466796875, -3009.5625, 116.22250366210938),
    (8, 11, 4, -4827.9208984375, 4394.46484375, 123.57420349121094),
    (9, 11, 5, 9379.3310546875, -206.23660278320312, 123.57469940185547),
    (10, 11, 6, 6367.4453125, 4072.68603515625, 94.61930084228516),
    (11, 11, 7, 9627.546875, -28.993200302124023, 123.57559967041016),
    (12, 11, 8, 5888.0234375, 3902.27880859375, 99.64630126953125),
    (13, 11, 9, -2863.192138671875, -1302.895263671875, 123.57099914550781),
    (14, 12, 1, -7277.27294921875, 8772.23828125, 123.57610321044922),
    (15, 13, 1, 7609.75048828125, 8881.412109375, 123.57450103759766),
    (16, 14, 1, -7395.55712890625, -7573.240234375, 123.57340240478516),
    (17, 15, 1, -4227.5166015625, -2268.31884765625, 184.22799682617188),
    (18, 18, 1, -1567.8546142578125, 2474.15380859375, 146.65789794921875),
    (19, 19, 1, -4725.8662109375, 360.4023132324219, 146.6531982421875),
    (20, 20, 1, 4241.19482421875, 6495.86572265625, 146.65310668945312),
    (21, 23, 1, 6846.83544921875, 1603.3616943359375, 146.64830017089844),
    (22, 31, 1, -3096.632568359375, 7156.4970703125, 146.6575927734375),
    (23, 32, 1, 551.6575927734375, -4892.7802734375, 146.65829467773438),
    (24, 34, 1, 6303.2939453125, -5587.1669921875, 146.65330505371094),
    (25, 40, 1, -4547.0244140625, -5540.56396484375, 146.65310668945312),
    (26, 50, 1, 6493.8173828125, 200.44869995117188, 123.61100006103516),
    (27, 51, 1, 552.6392211914062, 3892.43310546875, 123.6406021118164),
    (28, 16, 1, 2870.8173828125, -2860.9248046875, 184.22799682617188),
    (29, 17, 1, 578.215087890625, 6094.5546875, 184.22799682617188),
    (30, 53, 1, 6103.5439453125, -4567.28369140625, 86.0011978149414),
    (31, 53, 2, -3801.2705078125, -5383.482421875, 86.0011978149414),
    (32, 53, 3, -1901.68212890625, 5900.359375, 86.0),
    (33, 53, 4, 6990.89501953125, 4800.96875, 86.0011978149414),
    (34, 53, 5, 1914.54541015625, -6740.798828125, 86.0011978149414),
    (35, 53, 6, -5825.27099609375, 786.07177734375, 86.0),
    (36, 55, 1, 299.22100830078125, -3071.845947265625, 86.0),
    (37, 56, 1, 6591.837890625, -2885.15283203125, 393.6686096191406),
)

PLACEMENT_COUNT = len(_PLACEMENT_ROWS)


def identity_for(template_id: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    ``None`` is exactly the ~~2~~ 1 set in ``UNRESOLVED`` and nothing else: this
    function never substitutes, and never falls back to the Mob-Set number
    that ``GT-078`` proved wrong on the owner's screen.
    """
    if type(template_id) is not int or type(template_id) is bool:
        raise Bg3001IdentityError("template id must be an int")
    return IDENTITIES.get(template_id)


def shippable_placements() -> tuple[Bg3001Placement, ...]:
    """The ~~36~~ 37 placements of the 38 that resolve to an identity."""
    out = []
    for index, template_id, mm_instance, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(template_id)
        if identity is None:
            continue
        out.append(Bg3001Placement(
            index, template_id, mm_instance, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The ~~2~~ 1 that is dropped, with the id and the reason.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH ones and WHY.
    """
    out = []
    for index, template_id, _mm, x, y, z in _PLACEMENT_ROWS:
        if template_id in IDENTITIES:
            continue
        cline_row_id, leader, reason = UNRESOLVED.get(
            template_id, (0, 0, "set not in CLINE 3001"))
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

    ``COO-DECISION 20260902_2146`` shape 1 split one name into two
    contracts, and this is the second one.  An ASCII name prints as
    itself, so every grep, ticket and console line that worked before this
    round still works.  A name that is not ASCII prints as
    ``name_cp874_hex=<hex>`` - the bytes, in a form a cp874 console can
    show and a tester can copy - and callers pair it with ``placement=<n>``
    so the row is still identifiable.

    Never raises on a shipped row: every name in this table either is
    ASCII or is pinned in ``NAME_CP874_HEX``, and ``_self_check`` refuses
    at import if that stops being true.
    """
    if type(identity) is not SceneIdentity:
        raise Bg3001IdentityError("evidence_name needs a SceneIdentity")
    if identity.name.isascii():
        return identity.name
    return "name_cp874_hex=%s" % (
        identity.name.encode(NAME_ENCODING, "strict").hex(),)


def multi_set_placement_refusals() -> tuple[dict, ...]:
    """``MULTI_SET_GATE``, executable.  Empty tuple means every multi-set
    placement is the interchangeable pair that makes shipping the first leg
    safe; anything in it must NOT ship.

    The two conditions are ``COO-DECISION 20260902_2146`` shape 2, in
    order: (1) the legs disagree on a shipped column other than the MOBS
    id, or a leg is not in this module's tables at all - unknown is not
    equal, and (2) a leg is visible or carries a name plate.  A refusal
    carries the placement, the legs and which condition fired, because the
    decision requires the case to reach the COO as a letter rather than to
    ship quietly.
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
                # that drops what it cannot parse is a gate that passes
                # the case it was written for.
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
    if len(_RESOLVED_ROWS) != 24:
        raise Bg3001IdentityError(
            "expected 24 resolved sets, found %d" % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg3001IdentityError("duplicate Mob-Set number in the table")
    if len(UNRESOLVED) != 1:
        raise Bg3001IdentityError(
            "expected 1 unresolved set, found %d" % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg3001IdentityError("a set is both resolved and unresolved")
    if set(IDENTITIES) & set(SECOND_LEG_ONLY):
        raise Bg3001IdentityError(
            "a second-leg-only key is also shipped as a first leg")
    if len(_PLACEMENT_ROWS) != 38:
        raise Bg3001IdentityError(
            "expected 38 placements, found %d" % len(_PLACEMENT_ROWS))
    # Control 1: every first-leg Mob-Set number this scene's placements use
    # is either resolved or named as unresolved, and the two sets together
    # are EXACTLY this scene's used keys - a placement keyed by a number
    # this table has never heard of means the placement file and the
    # crosswalk came from different extractions.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if scene_sets != table_sets:
        raise Bg3001IdentityError(
            "placement Mob-Set numbers and this table's keys disagree: %r"
            % sorted(scene_sets ^ table_sets))
    if len(table_sets) != 25:
        raise Bg3001IdentityError(
            "expected 25 distinct Mob-Set numbers, found %d" % len(table_sets))
    # Every multi-set placement must BE one of this table's rows, keyed by
    # the first leg of its own raw string - the one check that makes the
    # first-leg rule readable from the data rather than from the docstring.
    indices = {row[0]: row[1] for row in _PLACEMENT_ROWS}
    for index, raw in MULTI_SET_PLACEMENTS.items():
        if index not in indices:
            raise Bg3001IdentityError(
                "multi-set placement %d is not in the placement table" % index)
        legs = raw.split("|")
        if len(legs) < 2 or not all(leg.isdigit() for leg in legs):
            raise Bg3001IdentityError(
                "multi-set placement %d has a malformed raw column %r"
                % (index, raw))
        if indices[index] != int(legs[0]):
            raise Bg3001IdentityError(
                "multi-set placement %d does not ship its first leg" % index)
        for leg in legs[1:]:
            if int(leg) in IDENTITIES:
                raise Bg3001IdentityError(
                    "second leg %s of placement %d is shipped as well"
                    % (leg, index))
    for index in EXTRA_TRIPLES_NOT_SHIPPED:
        if index not in indices:
            raise Bg3001IdentityError(
                "extra-triple row %d is not in the placement table" % index)
    if not no_set_number_is_shipped_as_identity():
        raise Bg3001IdentityError(
            "a row ships its own Mob-Set number as an identity")
    for row in _RESOLVED_ROWS:
        (template_id, cline_row_id, n_id, outfit, name, title, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1 or n_id < 1:
            raise Bg3001IdentityError(
                "set %d carries no CLINE row or leader locator" % template_id)
        if ";" in outfit or "|" in outfit:
            raise Bg3001IdentityError(
                "set %d ships a multi-variant outfit string" % template_id)
        if not outfit or not outfit.isascii():
            raise Bg3001IdentityError(
                "set %d has an empty or non-ASCII outfit" % template_id)
        # NAMES.  ``COO-DECISION 20260902_2146`` shape 1 replaced the flat
        # "names are ASCII" rule with a membership test plus a declaration:
        # a non-ASCII name must round-trip through cp874 AND be pinned as
        # bytes in ``NAME_CP874_HEX``, so a name can never arrive here by
        # some other route.  TITLES are untouched and still ASCII - no
        # decision has been taken on a non-ASCII title, and this table
        # ships none.
        if not title.isascii():
            raise Bg3001IdentityError(
                "set %d has a non-ASCII title" % template_id)
        if not name.isascii():
            pinned = NAME_CP874_HEX.get(template_id)
            if pinned is None:
                raise Bg3001IdentityError(
                    "set %d has a non-ASCII name that is not pinned in "
                    "NAME_CP874_HEX" % template_id)
            if _cp874(pinned) != name:
                raise Bg3001IdentityError(
                    "set %d ships a name that is not its own pin"
                    % template_id)
        elif template_id in NAME_CP874_HEX:
            raise Bg3001IdentityError(
                "set %d is pinned in NAME_CP874_HEX but ships an ASCII name"
                % template_id)
        if not name and not (
            template_id in NAMELESS_INVISIBLE_SETS
            and outfit == INVISIBLE_OUTFIT
        ):
            # The bg0004 set-107 exception, narrowed to the one set that
            # earns it: a nameless row with a real body is a mining fault.
            raise Bg3001IdentityError(
                "set %d has no display name and is not the known nameless "
                "INVISIBLE set" % template_id)
        if max_hp < 1 or level < 1:
            raise Bg3001IdentityError("set %d has a bad level/HP" % template_id)
    # MULTI_SET_GATE.  Fail-closed and BEFORE the counts below, so a pair
    # that stops being interchangeable cannot reach a census builder even
    # if the row count still looks right.
    # ORDER MATTERS HERE (pf-adversary, round ``gx7xtp``, D6).  The gate's
    # own fail-closed default - an unmeasured leg counts as having a name
    # plate - was survivable as a mutant only because THIS loop happened to
    # run after it and raise for a different reason.  Accidental ordering
    # is not a guard, so the inputs are checked BEFORE the gate reads them.
    for index, raw in MULTI_SET_PLACEMENTS.items():
        for leg in raw.split("|"):
            if not leg.isdigit() or int(leg) not in MULTI_SET_LEG_HAS_TIP_ROW:
                raise Bg3001IdentityError(
                    "leg %s of placement %d has no measured MOBS_TIP answer"
                    % (leg, index))
    if set(SECOND_LEG_IDENTITIES) != set(SECOND_LEG_ONLY):
        raise Bg3001IdentityError("the second-leg views disagree")
    if not SHIPPED_COLUMNS_EXCEPT_MOBS_ID:
        raise Bg3001IdentityError("the leg comparison compares nothing")
    refusals = multi_set_placement_refusals()
    if refusals:
        raise Bg3001IdentityError(
            "multi-set placements refused by the gate (COO-DECISION "
            "20260902_2146 shape 2): %s"
            % "; ".join(
                "placement %d: %s" % (row["placement_index"], row["reason"])
                for row in refusals))
    if len(shippable_placements()) != 37:
        raise Bg3001IdentityError("expected 37 shippable placements")
    if len(unshippable_placements()) != 1:
        raise Bg3001IdentityError("expected 1 unshippable placement")
    ids = [p.actor_identity for p in shippable_placements()]
    if len(ids) != len(set(ids)):
        raise Bg3001IdentityError("actor identities collide within this table")


_self_check()
