"""Who each Bg1001 placement actually IS - the ship at sea, scene 17's cast.

LANE-A (WORLD), round ``vwekfq``.  COO-DECISION ``pf_bridge/notes_to_chief/
20260905_0848_COO-DECISION-sea-scene-17-roster-approved-as-main-task-gt159-
kept-LANE-A.md`` approved this as the round's main task, on the milestone-M3
ladder ("the field has monsters"), with four binding conditions.  This module
is the identity half of that pair; ``world_population_bg1001`` is the census
half - the same split ``world_bg3001_identity`` / ``world_population_bg3001``
already ship for scene 126.

WHY THIS SCENE.  ``world_m2_sea_scene_cast`` (round nmn123) already measured,
against ``CONSTDATA_TH__INSTANCE.tsv``, that scene 17 (``Bg1001``, "one ship
at sea") resolves 7 of its 8 native placements through CLINE - the first
scene outside the ten island doors and Atlantis where this lane's own
enumerated search (``CREATURE_LINE_SOURCES``) answers something.  This round
turns that measurement into a shippable identity table, condition (c) of the
COO decision: **actor/census only**.  Nothing here is hostile, nothing here
carries a faction bit, and nothing here opens a GT ticket for hitting these
actors - that is LANE-B's own door, through its own admission.

THE THREE CANDIDATE CLINE TYPES, AND WHY THIS FILE PICKS 801 (CONDITION (b)).
``CONSTDATA_TH__INSTANCE.tsv`` carries THREE rows keyed by ``n_SCENE_ID ==
17``, each naming a different creature-line type and a different level tier:

    INSTANCE row  n_CLINE_TYPE  n_MIN_LEVEL  n_MAX_LEVEL  resolves (of 8)
    109           801           25           999          7
    122           814           70           999          7
    124           816           70           999          7

All three TIE at 7/8 resolved - measured below, and independently true of
each type because all three hold exactly the same 5 creature-type keys
(1..5) against this scene's own placement file, so whichever type wins, set
6 (the one placement with no CLINE row in any of the three) is the one that
does not resolve.  With the count tied, the tie-break the prior round's
adversary pass flagged as D8 matters: **a max-across-types reading would
pick 814 or 816 (n_MIN_LEVEL 70), which is wrong for a level-1 arrival** -
those two tiers gate a player who cannot possibly be admitted to them yet.
Condition (b) is explicit about the correction: the level block is the
**lowest** ``n_MIN_LEVEL`` among the resolving rows, which is row 109's 25.
This file therefore keys on **CLINE type 801**, ``SCENE_CLINE_TYPE`` below,
and ``SCENE_LEVEL_GATE_MIN_LEVEL`` is 25, not 70 - the opposite choice from
D8, made for the same reason D8 was wrong to skip.

    [PROPOSED], NOT MEASURED, THAT 801 IS THE RIGHT TYPE RATHER THAN AN
    ARBITRARY TIE-BREAK.  Unlike ``world_bg3001_identity``'s CONTROL 1 (the
    registry's own ``native_definition_count`` 56 agreeing with CLINE type
    3001's 56 rows), NO SUCH AGREEMENT EXISTS HERE: this scene's registry
    row gives ``native_definition_count`` 6 (six DISTINCT ``Mob_set_N``
    free-text labels appear in the placement file's ``name``/``set_names``
    columns - see the placement-disagreement paragraph below for why that
    is a label count and not a resolved-key count), while CLINE type 801
    (and 814, and 816) holds exactly 5 creature-type keys.  6 != 5, so
    there is no control that would let this file say "measured" the way
    scene 126's crosswalk could.  Every reading below - the type choice,
    the level-gate choice, and the eventual roster this scene sends - is
    tagged ``[PROPOSED]`` in this module, in ``world_m2_sea_destination``'s
    widened ``CLINE_BLOCKS`` (see that module's own docstring), and in the
    console line this pair of modules prints.  It stays PROPOSED until a
    control appears or an attended round confirms it on screen.

ONE PLACEMENT ROW DISAGREES WITH ITSELF, AND THIS FILE FOLLOWS THE MACHINE
COLUMN, NOT THE LABEL - the same anomaly and the same resolution
``world_bg0004_identity`` already recorded for its own scene.  Placement
index 1's free-text columns read ``name="Mob_set_3 01"`` and
``set_names="Mob_set_3"``, but its machine-parsed ``template_ids`` column
reads ``2`` - a plain copy-paste stale label, not a second placement of set
3.  This file follows ``template_ids``, the column
``field_mob_tables_bg0002.py`` (LANE B, same source format) already treats
as authoritative for its own scene and ``world_bg0004_identity`` followed
for the same reason: it is machine-parsed, not free-text a level editor's
copy-paste could leave stale.  Under that reading index 1 is a SECOND
instance of set 2 (Fighting Fish soldier's neighbour, Penguin Sergeant),
not a first instance of set 3 - and set 3 (leader 2882, "Penguin Staff
Sergeant") is consequently NOT among this scene's placements at all, even
though its own CLINE row resolves cleanly.  Named here so a future re-mine
that trusts the label column instead does not silently ship a placement
this table never claims - the exact caution bg0004's own paragraph raised
for its own scene.  This is also why the registry's own
``native_definition_count`` (6, counting the free-text labels 1..6) does not
match this table's 5 distinct RESOLVED-OR-NAMED-UNRESOLVED keys (1,2,4,5,6)
- 6 labels appear on screen^H^H^Hin the file, 5 numbers are real.

THE CROSSWALK, RE-DERIVED FROM THE COMMITTED TABLES.
``CLINE[(n_CLINE_TYPE=801, n_CREATURE_TYPE=<Mob-Set number>)].n_LEADER_BK1
-> CONSTDATA_TH__MOBS.n_ID -> s_OUTFIT / n_LEVEL_MIN / n_RANK /
n_MOB_USAGE``, and the display name/title from
``TEXTDATA_TH__MOBS_TIP.s_NAME`` / ``s_TITLE`` (not ``MOBS.s_NAME``, which is
CJK for every one of these five rows - this project's own crosswalk
convention, matching every sibling module).  HP from
``CONSTDATA_TH__STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX``, the same derived
column every sibling crosswalk uses.

    n_CREATURE_TYPE  CLINE n_ID  leader   MOBS_TIP.s_NAME          level
    1                26660       2880     Fighting Fish soldier    30
    2                26661       2881     Penguin Sergeant         32
    3                26662       2882     Penguin Staff Sergeant   33  (unused - see above)
    4                26663       2883     Golden Cat Navy Group    34
    5                26664       2884     Lion pirates             35

FOUR SETS SHIP ``s_OUTFIT`` STRINGS SEPARATED BY ';', AND ONE DOES NOT - the
same shape ``world_bg0004_identity`` names for nine of its own sets.  Ship
the FIRST variant, keep the whole raw string in ``MULTI_VARIANT_OUTFITS``
(keyed by leader ``n_ID``, this scene's own convention as well as bg0004's),
and ``_self_check`` refuses at import if a raw ';' ever reaches the shipped
column.  [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION], same
standing assumption bg0004's own docstring carries for the identical shape:

    leader 2880  M025_001_000_N                              (single, no ';')
    leader 2881  M024_000_001_SP1;M024_000_001_SP2            (first variant ships)
    leader 2883  M019_000_001_N;M019_000_001_SP1              (first variant ships)
    leader 2884  M001_000_001_SP1;M001_000_001_SP2            (first variant ships)

ONE SET HAS NO CLINE ROW AT ALL, IN ANY OF THE THREE CANDIDATE TYPES.  Set 6
(placement index 7) keys ``n_CREATURE_TYPE 6``, and none of CLINE type 801,
814 or 816 carries a row for that key - all three run keys 1..5 only, 5 rows
each.  So this placement is unresolved regardless of which of the three tied
types this file had picked, and the choice made under condition (b) costs
nothing extra.  Costs placement 7 (1 of 8).

CREW COLUMNS EXIST HERE AND ARE NOT SHIPPED - NAMED RATHER THAN LEFT FOR THE
NEXT READER TO DISCOVER (the same discipline ``world_bg3001_identity``'s own
"NO CREW" paragraph set, but the finding is the opposite: this scene DOES
carry crew).  Measured: every one of the 5 CLINE type 801 rows carries a
nonzero ``n_CREW1`` (creature-type 1's row even names ITSELF, 2880, as its
own crew1; creature-type 5's row names TWO crew slots, 2882 and 2880), while
``n_LEADER_BK2``/``n_LEADER_BK3`` are 0 on every row - the opposite mix from
Atlantis's densest set, which carried backup leaders and no crew at all.
Like every crosswalk in this project this module implements ``n_LEADER_BK1``
ONLY; the crew family is a pet/escort group this reading drops, recorded so
the next reader does not have to re-derive whether it exists.

NO EMPTY-``s_OUTFIT`` FAMILY, NO EXTRA SPAWN TRIPLES, NO CJK NAME.  Checked
directly against this scene's own 8-row placement file: every
``extra_triple_count`` reads 0 (no second spawn point silently dropped, the
"814 extra points" shape Atlantis carries has no analogue here), and every
``MOBS_TIP.s_NAME`` this table ships is plain ASCII - no ``NAME_CP874_HEX``
membership gate is needed for this scene.

HEADING.  This scene's placement file carries no heading column either (the
same absence every sibling scene has), so the census half reuses
``world_population.HEADINGS`` on the placement index, exactly as every other
composer in this project does.

PROVENANCE.  Every row below was read directly from these six committed
artifacts (the same six ``world_bg3001_identity`` cites, this scene's own
rows within them), by hand this round rather than by a throwaway script -
the block is 5 rows, not 56, so hand transcription is not the error source
it would be at Atlantis's scale, and every number is cross-checked against
the placement file's own template_ids column in ``_self_check`` below:

    gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv     (scene row, n_ID=17)
    gamedata/tables/CONSTDATA_TH__INSTANCE.tsv       (n_SCENE_ID=17, 3 rows)
    gamedata/tables/CONSTDATA_TH__CLINE.tsv          (n_CLINE_TYPE=801, 5 rows)
    gamedata/tables/CONSTDATA_TH__MOBS.tsv           (5 leader rows)
    gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv        (5 leader rows)
    gamedata/tables/CONSTDATA_TH__STANDARD_MOB.tsv   (levels 30/32/33/34/35)
    gamedata/scene/Bg1001/Bg1001.placements.tsv      (8 rows)

WHAT THIS MODULE DOES NOT CLAIM.

* Not that any of these 7 actors has been SEEN on a client screen.  GT-106
  (2026-08-27, attended) walked a player onto this scene's deck, but that
  run predates this crosswalk and reports no cast - "an empty ocean" is
  literally what condition (d)'s charter text calls today's state.
* Not that this scene is composed or sent on any path today.  This module
  and its census sibling build the table; whether the admission gate in
  ``lane_hooks/lane_a_scene_census.py`` admits a call for scene 17 is a
  separate, unedited decision - see that module's own registration comment
  and this round's report for exactly what remains closed and why.
* Not that CLINE type 801 is THE type rather than A tied type - see the
  [PROPOSED] paragraph above.
* Not leader+crew: like every sibling crosswalk this implements
  ``n_LEADER_BK1`` only.
"""
from __future__ import annotations

from dataclasses import dataclass


# Convention marker: shippable, no scenario flag - matching every sibling
# crosswalk module's own convention.  This lane's charter forbids a
# flag-gated lane; whether a CALLER admits scene 17 today is a separate,
# data-driven gate (the registry's own ``login_entry_allowed``), not a
# scenario flag on this file.
production_allowed = True
test_only = False

SCENE_N_ID = 17
SCENE_MODEL_ID = "Bg1001"
# [PROPOSED], not measured against a control - see the module docstring's
# own paragraph on why no 56==56-style agreement exists for this scene.
SCENE_CLINE_TYPE = 801
# SCENE_NAME.n_SCENE_LV for this scene - zero, matching the ocean panel
# (126) and unlike every island door this lane has opened (25..95).
SCENE_DECLARED_LEVEL = 0
# SCENE_NAME.n_SAVE for this scene.  Zero, the same faction gap
# ``world_bg3001_identity`` names for Atlantis: a login into this scene
# (were one ever to happen) emits no PLAYER_FACTION frame.  Kept as a named
# constant rather than inlined, matching that module's own convention.
SCENE_SAVE_FLAG = 0

# The three INSTANCE rows naming this scene, and why 801 (not 814 or 816)
# is this file's pick - condition (b) of the COO decision, see the module
# docstring.  (INSTANCE n_ID, n_CLINE_TYPE, n_MIN_LEVEL, n_MAX_LEVEL,
# resolved-of-8 placements).
INSTANCE_CANDIDATE_ROWS = (
    (109, 801, 25, 999, 7),
    (122, 814, 70, 999, 7),
    (124, 816, 70, 999, 7),
)
# The row this file follows, and the level a level-1 player's arrival is
# gated by under condition (b)'s rule: the LOWEST n_MIN_LEVEL among the
# resolving rows, not the highest across types (the D8 defect this
# condition exists to avoid).
SCENE_LEVEL_GATE_INSTANCE_ROW = 109
SCENE_LEVEL_GATE_MIN_LEVEL = 25

SOURCE_SHA256 = {
    "gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv":
        'e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b',
    "gamedata/tables/CONSTDATA_TH__INSTANCE.tsv":
        'e3b54a192b886284f30cdf94922d3ee2f5907f4db6c8ab24a6850318d21558f4',
    "gamedata/tables/CONSTDATA_TH__CLINE.tsv":
        'aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40',
    "gamedata/tables/CONSTDATA_TH__MOBS.tsv":
        '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    "gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv":
        'e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f',
    "gamedata/tables/CONSTDATA_TH__STANDARD_MOB.tsv":
        '4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925',
    "gamedata/scene/Bg1001/Bg1001.placements.tsv":
        '5e4de48707a87061d9a95471a1c3c25c56f0469fe2ece7ef0709a9c79f40fec7',
}

# Mob-Set numbers whose CLINE leader has no shippable identity, as
# set number -> (CLINE row n_ID, leader n_ID, why).  Unlike Atlantis's set
# 16 (a CLINE row that exists with leader 0), this scene's set 6 has NO
# CLINE row at all in type 801 (or in 814 or 816 - see the module
# docstring): 0/0 rather than a real row id with a zero leader.
UNRESOLVED = {
    6: (0, 0, 'no CLINE row for creature type 6 in any of types 801 814 816'),
}

# The four sets whose MOBS.s_OUTFIT names TWO avatar templates separated by
# ';', as leader n_ID -> the whole raw string.  The table below ships the
# FIRST variant; ``_self_check`` refuses if a raw ';' ever reaches the
# shipped column.  [LANE-A ASSUMPTION - AWAITING COO/OWNER CONFIRMATION],
# same standing assumption ``world_bg0004_identity`` carries for the
# identical shape.
MULTI_VARIANT_OUTFITS = {
    2881: "M024_000_001_SP1;M024_000_001_SP2",
    2883: "M019_000_001_N;M019_000_001_SP1",
    2884: "M001_000_001_SP1;M001_000_001_SP2",
}


class Bg1001IdentityError(ValueError):
    """A refusal from this module, always with a reason in the message."""


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
#  STANDARD_MOB[n_LEVEL_MIN].n_HPMAX, MOBS.n_MOB_USAGE)
# 4 rows: every Mob-Set number this scene's placements use (per
# ``template_ids``, not the stale free-text label - see the module
# docstring) that CLINE type 801 resolves to a shippable body.
_RESOLVED_ROWS = (
    (1, 26660, 2880, 'M025_001_000_N', 'Fighting Fish soldier', '',
     30, 1, 5143, 1),
    (2, 26661, 2881, 'M024_000_001_SP1', 'Penguin Sergeant', '',
     32, 1, 6174, 1),
    (4, 26663, 2883, 'M019_000_001_N', 'Golden Cat Navy Group', '',
     34, 1, 7339, 1),
    (5, 26664, 2884, 'M001_000_001_SP1', 'Lion pirates', '',
     35, 1, 7980, 1),
)

IDENTITIES = {row[0]: SceneIdentity(*row) for row in _RESOLVED_ROWS}


@dataclass(frozen=True)
class Bg1001Placement:
    """One Bg1001 placement resolved to a real, bodied actor."""

    placement_index: int
    template_id: int
    instance_count: int
    x: float
    y: float
    z: float
    identity: SceneIdentity | None

    @property
    def actor_identity(self) -> int:
        # The same formula every sibling scene uses (0x2000 + index + 1).
        # Never sent in the same generation as another scene's census -
        # every builder refuses any scene but its own - so sharing the
        # numeric space is a collision in the abstract only.
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


# (placement index, Mob-Set number FROM template_ids - the machine column,
#  NOT the free-text name/set_names label (index 1 disagrees, see the
#  module docstring), running instance count of that number within this
#  file, x, y, z), every row of the scene's own placement file in file
# order.  No row carries a raw '|' two-Mob-Set shape (unlike Atlantis) and
# no row carries extra spawn triples.
_PLACEMENT_ROWS = (
    (0, 2, 1, 844.638427734375, 1209.7308349609375, 1249.6798095703125),
    (1, 2, 2, 499.60089111328125, 199.53160095214844, 1215.7275390625),
    (2, 4, 1, -830.794921875, 60.902801513671875, 1091.7183837890625),
    (3, 5, 1, 296.9585876464844, -869.072998046875, 1272.73876953125),
    (4, 1, 1, -971.2965087890625, -690.400390625, 1112.424072265625),
    (5, 1, 2, -912.0040893554688, 1526.1767578125, 1112.424072265625),
    (6, 1, 3, 614.47607421875, 82.13349914550781, 1114.1845703125),
    (7, 6, 1, -741.5615844726562, 512.5458984375, 746.0424194335938),
)

PLACEMENT_COUNT = len(_PLACEMENT_ROWS)


def identity_for(template_id: int) -> SceneIdentity | None:
    """The identity of a Mob-Set number, or ``None`` if it cannot be shipped.

    ``None`` is exactly the 1 set in ``UNRESOLVED`` and nothing else: this
    function never substitutes.
    """
    if type(template_id) is not int or type(template_id) is bool:
        raise Bg1001IdentityError("template id must be an int")
    return IDENTITIES.get(template_id)


def shippable_placements() -> tuple[Bg1001Placement, ...]:
    """The 7 placements of the 8 that resolve to an identity."""
    out = []
    for index, template_id, instance_count, x, y, z in _PLACEMENT_ROWS:
        identity = IDENTITIES.get(template_id)
        if identity is None:
            continue
        out.append(Bg1001Placement(
            index, template_id, instance_count, x, y, z, identity))
    return tuple(out)


def unshippable_placements() -> tuple[dict, ...]:
    """The 1 placement that is dropped, with the id and the reason.

    The census console line quotes the COUNT of these every boot; this is
    where a reader goes to find out WHICH ones and WHY.
    """
    out = []
    for index, template_id, _count, x, y, z in _PLACEMENT_ROWS:
        if template_id in IDENTITIES:
            continue
        cline_row_id, leader, reason = UNRESOLVED.get(
            template_id,
            (0, 0, "set not in CLINE type %d" % SCENE_CLINE_TYPE))
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

    Every name this scene ships is already ASCII (unlike Atlantis's Thai
    row), so this always returns the name literally.  Kept as its own
    function, matching ``world_bg3001_identity.evidence_name``'s own
    signature, so a census module can call one convention across scenes
    without checking which one needs the cp874 fallback.
    """
    if type(identity) is not SceneIdentity:
        raise Bg1001IdentityError("evidence_name needs a SceneIdentity")
    if not identity.name.isascii():
        raise Bg1001IdentityError(
            "this scene ships no non-ASCII name - if one appears here, "
            "add the cp874 membership gate world_bg3001_identity carries "
            "rather than silently printing raw bytes")
    return identity.name


def no_set_number_is_shipped_as_identity() -> bool:
    """Control, executable.  No resolved row ships its own Mob-Set number
    as its identity - the same regression guard ``world_bg3001_identity``
    carries for GT-078's failure shape.
    """
    return all(row[0] != row[2] for row in _RESOLVED_ROWS)


def _self_check() -> None:
    """Refuse at import if this table has drifted out of the shape the
    module docstring claims.  Fail-closed: a bad table must not reach a
    census builder at all, and an ImportError names the file.
    """
    if len(_RESOLVED_ROWS) != 4:
        raise Bg1001IdentityError(
            "expected 4 resolved sets, found %d" % len(_RESOLVED_ROWS))
    if len(IDENTITIES) != len(_RESOLVED_ROWS):
        raise Bg1001IdentityError("duplicate Mob-Set number in the table")
    if len(UNRESOLVED) != 1:
        raise Bg1001IdentityError(
            "expected 1 unresolved set, found %d" % len(UNRESOLVED))
    if set(IDENTITIES) & set(UNRESOLVED):
        raise Bg1001IdentityError("a set is both resolved and unresolved")
    if len(_PLACEMENT_ROWS) != 8:
        raise Bg1001IdentityError(
            "expected 8 placements, found %d" % len(_PLACEMENT_ROWS))
    # Every Mob-Set number this scene's placements use (per template_ids)
    # is either resolved or named as unresolved, and the two sets together
    # are EXACTLY this scene's used keys.
    scene_sets = {row[1] for row in _PLACEMENT_ROWS}
    table_sets = set(IDENTITIES) | set(UNRESOLVED)
    if scene_sets != table_sets:
        raise Bg1001IdentityError(
            "placement Mob-Set numbers and this table's keys disagree: %r"
            % sorted(scene_sets ^ table_sets))
    if table_sets != {1, 2, 4, 5, 6}:
        raise Bg1001IdentityError(
            "expected keys {1,2,4,5,6} (set 3 is the mislabeled placement, "
            "see the module docstring), found %r" % sorted(table_sets))
    if not no_set_number_is_shipped_as_identity():
        raise Bg1001IdentityError(
            "a row ships its own Mob-Set number as an identity")
    for row in _RESOLVED_ROWS:
        (template_id, cline_row_id, n_id, outfit, name, title, level, rank,
         max_hp, _usage) = row
        if cline_row_id < 1 or n_id < 1:
            raise Bg1001IdentityError(
                "set %d carries no CLINE row or leader locator" % template_id)
        if ";" in outfit or "|" in outfit:
            raise Bg1001IdentityError(
                "set %d ships a multi-variant outfit string" % template_id)
        if not outfit or not outfit.isascii():
            raise Bg1001IdentityError(
                "set %d has an empty or non-ASCII outfit" % template_id)
        if not name or not name.isascii():
            raise Bg1001IdentityError(
                "set %d has an empty or non-ASCII name - this scene ships "
                "no non-ASCII names, unlike Atlantis" % template_id)
        if not title.isascii():
            raise Bg1001IdentityError(
                "set %d has a non-ASCII title" % template_id)
        if max_hp < 1 or level < 1:
            raise Bg1001IdentityError("set %d has a bad level/HP" % template_id)
        if level < SCENE_LEVEL_GATE_MIN_LEVEL:
            raise Bg1001IdentityError(
                "set %d is below this scene's own chosen level gate (%d) - "
                "the gate is measured FROM these rows, so this can only "
                "mean the gate or a row drifted" % (
                    template_id, SCENE_LEVEL_GATE_MIN_LEVEL))
    # MULTI_VARIANT_OUTFITS must name exactly the leaders whose outfit is a
    # ';'-joined string, and every one of them must ship the FIRST variant.
    multi_variant_leaders = set()
    for row in _RESOLVED_ROWS:
        template_id, _cline, n_id, outfit, *_rest = row
        raw = MULTI_VARIANT_OUTFITS.get(n_id)
        if raw is None:
            continue
        multi_variant_leaders.add(n_id)
        variants = raw.split(";")
        if len(variants) < 2:
            raise Bg1001IdentityError(
                "leader %d is in MULTI_VARIANT_OUTFITS but its raw string "
                "has no ';'" % n_id)
        if outfit != variants[0]:
            raise Bg1001IdentityError(
                "leader %d does not ship the first outfit variant" % n_id)
    if multi_variant_leaders != set(MULTI_VARIANT_OUTFITS):
        raise Bg1001IdentityError(
            "MULTI_VARIANT_OUTFITS names a leader this table does not ship, "
            "or misses one that needs it")
    if len(shippable_placements()) != 7:
        raise Bg1001IdentityError("expected 7 shippable placements")
    if len(unshippable_placements()) != 1:
        raise Bg1001IdentityError("expected 1 unshippable placement")
    ids = [p.actor_identity for p in shippable_placements()]
    if len(ids) != len(set(ids)):
        raise Bg1001IdentityError("actor identities collide within this table")
    # Condition (b): the level gate must be the LOWEST n_MIN_LEVEL among the
    # resolving INSTANCE rows, never the highest - the D8 defect this file
    # exists to avoid re-introducing.
    resolving_min_levels = [row[2] for row in INSTANCE_CANDIDATE_ROWS]
    if SCENE_LEVEL_GATE_MIN_LEVEL != min(resolving_min_levels):
        raise Bg1001IdentityError(
            "the level gate must be the LOWEST n_MIN_LEVEL among the "
            "resolving INSTANCE rows (%r), not %d"
            % (resolving_min_levels, SCENE_LEVEL_GATE_MIN_LEVEL))
    if SCENE_CLINE_TYPE not in {row[1] for row in INSTANCE_CANDIDATE_ROWS}:
        raise Bg1001IdentityError(
            "SCENE_CLINE_TYPE must be one of the scene's own candidate "
            "INSTANCE rows")


_self_check()
