"""RE-155: the env-gated, single-boot "dummy row" sweep for name colour.

WHAT THIS IS FOR.  PANYA-ORDER 2026-09-06T21:3x+07:00 (relayed by ka1-A,
``pf_bridge/notes_to_chief/20260906_2142_...`` + addendum ``20260906_2150_
...``) and COO-DECISION 2026-09-06T22:41+07:00 (``pf_bridge/notes_to_chief/
20260906_2241_COO-DECISION-panya2142-re155-owner-b-two-rounds-dummy-row-
LANE-B.md``) order this lane to build an opt-in spawner that places two
prototypes -- a plain NPC and the Training Iron Man practice dummy
(``template_id`` 916) -- side by side, each candidate differing from its own
``BASE`` by EXACTLY ONE field, labelled on the nameboard so an attended
tester reads the answer off the screen instead of a hexdump.  This module
does not decide a colour, does not hardcode a ``FontStyleID``, and sends
nothing by itself: it is called from an attended/dev boot path, gated
fail-closed by one environment variable, the same shape as
``pose_trial.PF_POSE_TRIAL`` and ``gm/speed_wire.PF_SPEED_TRIAL``.

WHY AN ENVIRONMENT VARIABLE.  Same reason as ``pose_trial``: argument parsing
lives in ``app.py`` (chief's file), this lane may not edit it, and the
attended bridge already arms trials via the process environment.

FAIL-CLOSED.  ``PF_NAME_COLOUR_SWEEP`` unset, empty or not one of the known
set names below means :func:`sweep_actors` returns an empty tuple and
:func:`sweep_enabled` is False -- production spawns nothing extra.

THE TWO PROTOTYPES, AND WHY THESE EXACT ROWS.
* NPC: ``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS[0]`` in
  ``current/pf_login_game_server_v141.py`` -- ``template_id`` 1, visual
  preset ``P_MALE_002_000_SP1``, source name "Navy Transfer".  This is a
  real, committed, currently-shipping town placement, composed with
  ``legacy.make_npc_attr`` and NO faction splice at all -- byte-for-byte the
  shape GT-131 (2026-08-30) captured showing every NPC green.  That is
  ``BASE`` for the NPC row.
* Mob: the Training Iron Man row LANE-B already mines and ships today
  (``field_mob_tables.PLACEMENTS`` placement 103, ``template_id`` 916,
  preset ``M016_000_000_N``), fetched through ``field_mobs.load_roster()``
  and composed through ``field_mobs.hostile_npc_attr`` exactly as production
  does (level splice + faction splice, faction 6).  That is ``BASE`` for the
  mob row -- what a real client already renders today, still not proven
  red (RE-195/RE-263).

ONE FIELD PER CANDIDATE, MEASURED NOT ASSUMED.  Every candidate function
below is checked by ``tests/test_name_colour_sweep.py`` to differ from its
own ``BASE`` body by exactly the bytes the one field under test needs --
mirroring the discipline ``field_mobs.hostile_npc_attr`` already holds
itself to (see that function's own load-bearing test).  The NPC faction
splice reuses ``field_mobs._faction_splice_offset``/``_basic_mask_offset``
directly rather than re-deriving the insertion point, because those two
helpers are what the frozen-body-plus-exactly-N-bytes test already trusts.

SYNTHETIC IDENTITIES, NOT THE REAL ONES.  Every row in this sweep gets a
placement index from :data:`SWEEP_PLACEMENT_BASE` upward -- never the
prototype's own real placement index (0 or 103) -- because a live boot may
ALSO carry the real Port Royal population and the real field-mob roster in
the same session, and ``actor_identity`` is ``0x2000 + placement_index + 1``
with no other collision guard anywhere in this codebase.
``tests/test_name_colour_sweep.py`` asserts the reserved band is disjoint
from every placement-index table this round found by name (``population``'s
115-row source, every ``field_mob_tables_bg*.SHIPPED_PLACEMENTS``, and
``scene2_prison_exile_tables``/``world_bg1001_identity``/
``world_bg3001_identity``/``world_bg3007_identity``/``world_bg3008_identity``/
``world_bg4001_identity``'s own placement rows), not just eyeballed once
here.  pf-adversary (round dipufa, finding 2): this is an ENUMERATED list,
not a discovery scan -- a future module with its own placement-index table
that nobody adds here would not be checked.  No live collision exists today
(every table above tops out in the low hundreds), and the fix, if the
enumerated-list risk becomes real, is either a discovery-based rewrite of
this check or raising :data:`SWEEP_PLACEMENT_BASE` further.

CANDIDATES THIS ROUND SHIPS, AND WHY EACH ONE IS SAFE TO COMPOSE.
* ``faction`` (sets 1): three real ``n_ID`` rows from
  ``gamedata/tables/CONSTDATA_TH__FACTION.tsv`` (38 data rows) outside the
  1-6 range this project already uses -- 7, 12, 999 (low, mid, and the
  table's own sentinel-shaped high value).  Reuses the exact splice
  ``hostile_npc_attr`` already ships for the mob row; a new local splice for
  the NPC row (which has no faction bit set in its own ``BASE``, unlike the
  mob row) built from the same two frozen helpers.
* ``actor_type`` (set 2): value 5 (``CAvatarNPC``; was 3 until round b08g3z
  -- see :data:`NPC_ATTR_BINDING_ACTOR_TYPES` for the byte-proof that 3
  binds no ``NPCAttr`` and so shows no nameplate at all), applied to the
  OUTER ``ActorEntry``, not
  the ``NPCAttr`` body -- ``legacy.make_remote_actor_entry``'s first
  argument, already a real, already-sent field
  (``population.NPC_STYLE_ACTOR_TYPE`` is 4).  The ``NPCAttr``/movement
  bytes are byte-identical to ``BASE``; only the envelope's own type tag
  changes.
* ``visual_preset`` ("skin", set 2): swapped to a second real, committed
  preset (``M010_001_000_N``, "Sebastian", row 1 of the same frozen table)
  for the SAME ``template_id`` -- deliberately a combination no placement
  ships today, because the sweep's whole point is isolating one field.

CANDIDATES THIS ROUND DOES **NOT** SHIP, AND WHY -- do not re-derive these
as a TODO, read the reason first.
* ``relation +0x98`` -- ``gm/name_color_gate.py`` and ``mob_viewer_link.py``
  both warn, independently, that TWO different fields share the "+0x98"
  name in two different classes: ``ActorAttr+0x98`` (u8, tag 0x0B, presence
  ``+0x1B4 & 0x04000000`` -- the relation byte
  ``gm/attr_wire.py`` FIELDS row ``x=39`` already models) and
  ``NPCAttr+0x98`` (u64, tag 0x32, presence ``+0xBC & 0x08`` -- the viewer
  identity ``mob_viewer_link.py`` implements, a DIFFERENT hypothesis).
  Neither citation says ``NPCAttr`` -- the class this module's bodies are --
  carries an EQUIVALENT relation byte anywhere in its own tail.  Splicing an
  ``ActorAttr`` field into an ``NPCAttr`` body on the strength of a shared
  hex offset between two admittedly-different classes is exactly the kind
  of guess ``NOW.md`` P-2 forbids (no guessing a byte position) and the
  letter this module ships with says so in as many words, as a real,
  useful negative result for RE-155's candidate list -- not a placeholder.
* ``rank`` -- ``field_mobs.FieldMob.rank`` (MOBS ``n_RANK``, mined and real)
  is used ONLY for the M3 roster-eligibility predicate; nothing in
  ``field_mobs.py`` or ``gm/attr_wire.py`` wires it to any BasicAttr/ActorAttr
  bit or tag.  There is no known byte to flip.  Same refusal as above,
  same reason: inventing an offset is not measurement.

pf-adversary: this module is new this round and has not yet had adversary
review; see the round file for ``ADVERSARY_PENDING``/``ADVERSARY_UNAVAILABLE``.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import os
from typing import Any

from . import field_mob_tables
from . import field_mobs
from . import mob_viewer_link
from .gm import name_color_gate
from .population import (
    FULL_MOVEMENT_MASK,
    MOVEMENT_ATTR_ID,
    NPC_ATTR_ID,
    SCENE_ID,
    SCENE_SEQUENCE,
)

# The one environment variable that arms this module.  Unset/empty/unknown
# means every function below behaves as if the sweep does not exist.
SWEEP_ENV = "PF_NAME_COLOUR_SWEEP"

SET_FACTION = "1"
SET_ACTOR_TYPE_AND_SKIN = "2"
#: Set 3 (COO-ORDER 2026-09-07T20:50+07:00, after GT-288 set 2 eliminated
#: actor_type and the skin): one row per field in which the NPC prototype's
#: body and the monster prototype's body actually differ, each row carrying
#: the MONSTER's value of exactly ONE of them on an otherwise untouched NPC.
#: The field list is not hand-written here -- it is what
#: ``npc_attr_body_diff.diff(N-BASE, M-BASE)`` returns, and
#: ``tests/test_name_colour_sweep_set3.py`` re-derives it from the two bodies
#: rather than trusting this comment.
SET_DIFF_FIELDS = "3"
#: ALL (PANYA-ORDER 2026-09-07T23:25+07:00, relayed by COO-ORDER 23:42): every
#: candidate in one boot on the Iron Man square instead of one question per
#: attended trip.  ALL-NOID is the same row with the identity families left
#: out, for a client that refuses to draw an actor whose identity is 0 or
#: negative -- so a boot that dies on ALL still returns an answer.
SET_ALL = "ALL"
SET_ALL_NOID = "ALL-NOID"
KNOWN_SETS = (
    SET_FACTION, SET_ACTOR_TYPE_AND_SKIN, SET_DIFF_FIELDS, SET_ALL,
    SET_ALL_NOID,
)

# Reserved placement-index band for this experiment ONLY.  Never a real
# placement index (see module docstring "SYNTHETIC IDENTITIES").
SWEEP_PLACEMENT_BASE = 20000
SWEEP_PLACEMENT_STRIDE = 10

# The NPC prototype: PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS[0] in
# current/pf_login_game_server_v141.py, transcribed by value (that table
# belongs to chief and this lane does not import row 0 by index from a
# 115-row list it may not edit).
NPC_BASE_TEMPLATE_ID = 1
NPC_BASE_VISUAL_PRESET = "P_MALE_002_000_SP1"
NPC_BASE_SOURCE_NAME = "Navy Transfer"
NPC_BASE_SOURCE_PLACEMENT_INDEX = 0

# RE-071 precedent (LANE-B.md "known already" section): a bare actor with
# name + HP 100/100 is a body this project has already sent successfully.
# Chosen because color is what is under test here, not HP.
NPC_BASE_HP = 100

# A second real, committed preset (row 1, "Sebastian") used ONLY as the
# "skin" candidate's alternate value -- see module docstring.
SKIN_CANDIDATE_VISUAL_PRESET = "M010_001_000_N"

MOB_TEMPLATE_ID = 916
MOB_SOURCE_PLACEMENT_INDEX = 103

# CONSTDATA_TH__FACTION.tsv n_ID values outside the 1-6 range this project's
# own faction pairing (field_mobs.FIELD_MOB_FACTION / PLAYER_PAIR_FACTION)
# uses.  All three are real rows of that 38-row table.
FACTION_CANDIDATES = (7, 12, 999)

# The actor_type values whose class still binds an ``NPCAttr`` at all.  A
# candidate outside this set produces an actor with NO nameplate rather than
# a nameplate of a different colour, and the tester then writes down FAIL for
# a colour that was never drawn.  Provenance, in this repo since 2026-08-18:
# reports/PF_MPAUDIT_FOLLOWUP001_ACTOR_TYPE_DISPATCH_STATIC_20260818.md line
# 129 -- the NPCAttr (0x0AD5) vtable +0x38 thunk 0x4697B0 is-a-checks
# CNetNPC and silently no-ops otherwise, "(so 4, 5)".  The set is NOT
# hand-copied from that sentence: tests/test_name_colour_sweep.py parses the
# report's own row and fails if this literal drifts from it, the same
# discipline tests/test_actor_type_dispatch_static.py already holds the
# DISPATCH_COUNTS block to.
#
# Why 3 is out, corrected by pf-adversary in round b08g3z: the first draft of
# this comment said an actor_type 3 row would survive RE-092's collection
# wipe (which exempts CMyActor) and so read as a false PASS.  That cannot
# fire, and the real fact is stronger -- report line 61: actor_type 3 is
# refused outright unless the local-player global 0x1032EC4 is zero, so with
# a local player already built the factory returns NULL and there is no
# object in the manager at all, nothing to exempt and nothing to survive.
#
# WHY 5 IS IN, and the nonclaim that used to stand here is WITHDRAWN --
# RE-290 RESULT, 2026-09-07T10:27+07:00 (pf_bridge notes_to_chief/
# 20260907_1027_RE-290-RESULT-cavatarnpc-builds-the-same-nameboardnpc-as-
# cnetnpc.md), the ticket this lane opened in round b08g3z.  Report line 53
# names 5 CAvatarNPC, line 105 places it as a CHILD of CNetNPC (4, what we
# emit today), lines 168/170 show 4 and 5 sharing the +0x74/+0x78 name
# GETTERS off actor+0x358, and line 62 shows both gated the same way by the
# factory flag [this+0x6D].  What was missing was the name BOARD: the board
# is built by vtable +0x7C and the report pinned +0x7C for CNetActor
# (0x456580) and CNetNPC (0x45C560) ONLY, so an AT5 row showing no nameplate
# had to be allowed as a possible outcome of set 2.  RE-290 read the dword:
#
#     [0xF0DFF8 + 0x7C] = 0x0045C560
#
# -- byte for byte the CNetNPC creator, cross-checked at the target's own
# prologue (push 0xC0 = sizeof NameBoardNPC, against push 0x78 =
# NameBoardPlayer at CNetActor's 0x456580).  CAvatarNPC therefore builds the
# SAME NameBoardNPC.  An AT5 row has a nameplate to colour, so an AT5 row
# showing no nameplate is a FAIL of this experiment, not an expected
# outcome, and the escape clause the old text handed the attended tester is
# gone.
#
# THE NARROW GREP RE-290 ASKED THIS LANE TO RUN BEFORE CONSUMING IT (its
# "limitations" section: the runner hit the round's minute line before it
# could tell which of six files matched which word).  Run in round mhr9y6
# over the six named files under pf_bridge notes_to_chief/
# reference_codex_attr/ (PF_MONSTER_PRESENTATION.tsv does not exist in
# either repository; the other five do): every case-insensitive hit on
# "cavatarnpc" and "f0dff8" is ZERO, and every hit on "45c560" outside the
# span_sha256 column is the SAME single row, PF_MONSTER_COLOR_GATE.tsv
# MCG-IMG-044 NAMEBOARD_CONTROLLER_BIND, whose span_start_va is 0x0045C560
# for CNetNPC.  So the house had this value already, for the OTHER class,
# and RE-290's read agrees with it -- which is the "same value, treat as
# re-confirmation" branch the letter itself named.  The bulk case-insensitive
# hits on "45c560" in all five files are substrings of sha256 digests, not
# addresses.
NPC_ATTR_BINDING_ACTOR_TYPES = frozenset({4, 5})

#: The committed artifact :data:`NPC_ATTR_BINDING_ACTOR_TYPES` is derived
#: from, and the row inside it that carries the answer.
ACTOR_TYPE_REPORT = (
    "reports/PF_MPAUDIT_FOLLOWUP001_ACTOR_TYPE_DISPATCH_STATIC_20260818.md"
)

#: Minimum distance, in world units, between any sweep row and any real
#: Port Royal placement.  Not a guess: one row's spacing (150) plus enough
#: margin that a tester reading label text off a nameboard cannot pick up the
#: neighbouring real NPC's board instead.  The shipped layout clears it with
#: 255.0; see :func:`_row_xyz`.
ROW_CLEARANCE_FROM_REAL_NPCS = 200.0

# Was 3 (CMyActor) until round b08g3z.  chief's letter 2026-09-07T03:41+07:00
# carried pf-adversary's measurement that 3 is not in the set above; the
# report line it cites is the one quoted there, read directly, not taken on
# trust.  5 is the only remaining flip that keeps a nameplate.
ACTOR_TYPE_CANDIDATE = 5


class NameColourSweepError(ValueError):
    """Shape or contract error building a sweep row."""


@dataclass(frozen=True)
class SweepActor:
    """One labelled dummy: bytes ready for ``make_runtime_remote_actors``."""

    label: str
    actor_type: int
    actor_identity: int
    x: float
    y: float
    z: float
    npc_attr: bytes


def standing_colour_wiring_refusal() -> name_color_gate.P2ColorWiringVerdict:
    """This module's own reminder that it MEASURES, it does not DECIDE.

    Returns the gate's standing refusal (``tests/test_gm_name_color_gate.py``
    owns what it means) so a static scan
    (``tests/test_gm_p2_color_call_site_tripwire.py``) can tell a P-2 colour
    module that only builds candidates for an attended human to grade apart
    from one that would wire a colour decision in code without consulting
    the refusal first.  Nothing here reads ``.allowed`` and branches on it --
    there is no colour decision in this module to gate.
    """
    return name_color_gate.p2_color_wiring_verdict()


def sweep_enabled(env: dict | None = None) -> bool:
    value = (os.environ if env is None else env).get(SWEEP_ENV, "")
    return value in KNOWN_SETS


def _spawn_anchor(legacy: Any) -> tuple[float, float, float]:
    return (
        float(legacy.V135_PLAYER_X),
        float(legacy.V135_PLAYER_Y),
        float(legacy.V135_PLAYER_Z),
    )


def _row_xyz(anchor: tuple[float, float, float], ordinal: int) -> tuple[float, float, float]:
    x, y, z = anchor
    # Lined up 150 units apart -- close enough to read every nameboard from
    # one spot, far enough apart that boxes do not overlap.  Two things about
    # this line are load-bearing and both were measured, in this repo, from
    # ``legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS`` (115 rows) against
    # ``_spawn_anchor``; :data:`ROW_CLEARANCE_FROM_REAL_NPCS` is the test that
    # keeps them true.
    #
    # 1. NO ROW STANDS ON THE ANCHOR.  The anchor is the player's own spawn
    #    point, so an ordinal-0 row would be inside the camera at the exact
    #    moment the tester is asked to read its nameplate.  Hence ordinal + 1.
    # 2. THE LINE RUNS -X, AWAY FROM TOWN.  Port Royal's real NPCs are all in
    #    the +X direction from the spawn: "Navy Transfer" at 111.8 units and
    #    "Sebastian" at 1227.5.  A +X line walks the dummies straight into
    #    them -- worst case a dummy 56.6 units from the real "Sebastian",
    #    38% of one row's spacing, and the SKIN candidate wears Sebastian's
    #    own preset.  Running -X instead, the closest any dummy comes to any
    #    real NPC is 255.0 units.  (chief's 2026-09-07T03:41 letter said the
    #    nearest real NPC was Sebastian at 1,227 units and that nothing was
    #    within 1,000; re-derived here, that skips placement 0 "Navy
    #    Transfer" at 111.8 -- which is this module's own NPC prototype.  The
    #    letter's conclusion, "get off the spawn point", stands; its distance
    #    premise does not, and -X is what the real numbers ask for.)
    return (x - 150.0 * (ordinal + 1), y, z)


def _mob_prototype() -> field_mobs.FieldMob:
    for mob in field_mobs.load_roster():
        if (
            mob.template_id == MOB_TEMPLATE_ID
            and mob.placement_index == MOB_SOURCE_PLACEMENT_INDEX
        ):
            return mob
    raise NameColourSweepError(
        f"Training Iron Man (template {MOB_TEMPLATE_ID}, placement "
        f"{MOB_SOURCE_PLACEMENT_INDEX}) is not in field_mobs.load_roster() "
        "any more -- this module's mob prototype needs re-deriving"
    )


def _identity_template_mob_prototype() -> field_mobs.FieldMob:
    """The real field monster the identity x template row is built from.

    Read out of the shipped Bg0002 roster (Tornado Eagle, template 31,
    ``M011_000_000_SP3``) rather than typed, so this row moves with the table
    instead of drifting away from it.  This READS bg0002; it does not touch
    it.
    """
    for mob in field_mobs.load_roster(scene=IDENTITY_TEMPLATE_MOB_SCENE):
        if mob.template_id == IDENTITY_TEMPLATE_MOB_TEMPLATE_ID:
            return mob
    raise NameColourSweepError(
        f"template {IDENTITY_TEMPLATE_MOB_TEMPLATE_ID} is not in "
        f"field_mobs.load_roster(scene={IDENTITY_TEMPLATE_MOB_SCENE!r}) any "
        "more -- the identity x template row needs re-deriving"
    )


def _npc_plain_body(
    legacy: Any,
    actor_identity: int,
    label: str,
    *,
    visual_preset: str = NPC_BASE_VISUAL_PRESET,
    template_id: int = NPC_BASE_TEMPLATE_ID,
    current_hp: int = NPC_BASE_HP,
    max_hp: int = NPC_BASE_HP,
    movement_speed: float = 0.0,
) -> bytes:
    """``legacy.make_npc_attr`` with no splice at all -- the GT-131 shape.

    Every keyword defaults to the prototype's own committed value, so a
    caller that passes none gets ``N-BASE`` byte for byte (pinned by
    ``tests/test_name_colour_sweep_set3.py``).  The keywords exist for set 3,
    where each row moves EXACTLY ONE of them to the monster prototype's
    value; they are all already parameters of the frozen ``make_npc_attr``,
    so no row here splices anything the town does not send today.
    """
    return legacy.make_npc_attr(
        template_id,
        actor_identity,
        SCENE_ID,
        SCENE_SEQUENCE,
        visual_preset,
        current_hp,
        max_hp,
        movement_speed=movement_speed,
        basic_name=label,
    )


def _npc_faction_body(legacy: Any, actor_identity: int, label: str, faction: int) -> bytes:
    """The NPC plain body plus EXACTLY the faction splice, nothing else.

    Reuses ``field_mobs``' own frozen splice-position helpers rather than
    re-deriving them -- see module docstring.  Validates ``faction`` the
    same way ``field_mobs.hostile_npc_attr`` does (pf-adversary, round
    dipufa, finding 7: the first draft trusted its only caller instead).
    """
    field_mobs._require_int(faction, "faction", 0, 0xFFFFFFFF)
    if faction == 0:
        raise NameColourSweepError(
            "faction 0 is the player constructor default -- see "
            "field_mobs.hostile_npc_attr's own refusal for the same value"
        )
    baseline = _npc_plain_body(legacy, actor_identity, label)
    offset = field_mobs._faction_splice_offset(
        legacy, baseline, NPC_BASE_TEMPLATE_ID, NPC_BASE_VISUAL_PRESET,
    )
    mask_at = field_mobs._basic_mask_offset(legacy, baseline, actor_identity)
    mask = int.from_bytes(baseline[mask_at:mask_at + 2], "little")
    if mask & field_mobs.BASIC_BIT_FACTION:
        raise NameColourSweepError(
            "NPC plain body already sets the faction bit; the splice below "
            "would double the field"
        )
    composed = (
        baseline[:mask_at]
        + int(mask | field_mobs.BASIC_BIT_FACTION).to_bytes(2, "little")
        + baseline[mask_at + 2:offset]
        + bytes(legacy.u32tag(field_mobs.FACTION_TAG, faction))
        + baseline[offset:]
    )
    if len(composed) != len(baseline) + field_mobs.FACTION_SPLICE_BYTES:
        raise NameColourSweepError("NPC faction splice length drift")
    return composed


def _entry(
    legacy: Any,
    *,
    label: str,
    actor_type: int,
    actor_identity: int,
    npc_attr: bytes,
    x: float,
    y: float,
    z: float,
) -> SweepActor:
    return SweepActor(label, actor_type, actor_identity, x, y, z, npc_attr)


def _faction_set(legacy: Any) -> tuple[SweepActor, ...]:
    anchor = _spawn_anchor(legacy)
    mob = _mob_prototype()
    rows: list[SweepActor] = []
    ordinal = 0

    npc_identity = SWEEP_PLACEMENT_BASE  # actor_identity computed below
    for label, faction in (("N-BASE", None),) + tuple(
        (f"N-F{value:02d}", value) for value in FACTION_CANDIDATES
    ):
        placement_index = SWEEP_PLACEMENT_BASE + ordinal * SWEEP_PLACEMENT_STRIDE
        identity = 0x2000 + placement_index + 1
        x, y, z = _row_xyz(anchor, ordinal)
        body = (
            _npc_plain_body(legacy, identity, label)
            if faction is None
            else _npc_faction_body(legacy, identity, label, faction)
        )
        rows.append(_entry(
            legacy, label=label, actor_type=field_mobs.NPC_STYLE_ACTOR_TYPE,
            actor_identity=identity, npc_attr=body, x=x, y=y, z=z,
        ))
        ordinal += 1

    for label, faction in (("M-BASE", field_mobs.FIELD_MOB_FACTION),) + tuple(
        (f"M-F{value:02d}", value) for value in FACTION_CANDIDATES
    ):
        placement_index = SWEEP_PLACEMENT_BASE + ordinal * SWEEP_PLACEMENT_STRIDE
        variant = replace(mob, placement_index=placement_index, display_name=label)
        x, y, z = _row_xyz(anchor, ordinal)
        body = field_mobs.hostile_npc_attr(legacy, variant, faction=faction)
        rows.append(_entry(
            legacy, label=label, actor_type=field_mobs.NPC_STYLE_ACTOR_TYPE,
            actor_identity=variant.actor_identity, npc_attr=body, x=x, y=y, z=z,
        ))
        ordinal += 1

    return tuple(rows)


def _actor_type_and_skin_set(legacy: Any) -> tuple[SweepActor, ...]:
    anchor = _spawn_anchor(legacy)
    mob = _mob_prototype()
    rows: list[SweepActor] = []
    ordinal = 0

    def add_npc(label: str, *, actor_type: int, visual_preset: str) -> None:
        nonlocal ordinal
        placement_index = SWEEP_PLACEMENT_BASE + ordinal * SWEEP_PLACEMENT_STRIDE
        identity = 0x2000 + placement_index + 1
        x, y, z = _row_xyz(anchor, ordinal)
        body = _npc_plain_body(legacy, identity, label, visual_preset=visual_preset)
        rows.append(_entry(
            legacy, label=label, actor_type=actor_type, actor_identity=identity,
            npc_attr=body, x=x, y=y, z=z,
        ))
        ordinal += 1

    def add_mob(label: str, *, actor_type: int, visual_preset: str | None) -> None:
        nonlocal ordinal
        placement_index = SWEEP_PLACEMENT_BASE + ordinal * SWEEP_PLACEMENT_STRIDE
        variant = replace(mob, placement_index=placement_index, display_name=label)
        if visual_preset is not None:
            variant = replace(variant, visual_preset=visual_preset)
        x, y, z = _row_xyz(anchor, ordinal)
        body = field_mobs.hostile_npc_attr(
            legacy, variant, faction=field_mobs.FIELD_MOB_FACTION,
        )
        rows.append(_entry(
            legacy, label=label, actor_type=actor_type,
            actor_identity=variant.actor_identity, npc_attr=body, x=x, y=y, z=z,
        ))
        ordinal += 1

    add_npc("N-BASE", actor_type=field_mobs.NPC_STYLE_ACTOR_TYPE, visual_preset=NPC_BASE_VISUAL_PRESET)
    add_npc(f"N-AT{ACTOR_TYPE_CANDIDATE}", actor_type=ACTOR_TYPE_CANDIDATE, visual_preset=NPC_BASE_VISUAL_PRESET)
    add_npc("N-SKIN", actor_type=field_mobs.NPC_STYLE_ACTOR_TYPE, visual_preset=SKIN_CANDIDATE_VISUAL_PRESET)

    add_mob("M-BASE", actor_type=field_mobs.NPC_STYLE_ACTOR_TYPE, visual_preset=None)
    add_mob(f"M-AT{ACTOR_TYPE_CANDIDATE}", actor_type=ACTOR_TYPE_CANDIDATE, visual_preset=None)
    add_mob("M-SKIN", actor_type=field_mobs.NPC_STYLE_ACTOR_TYPE, visual_preset=SKIN_CANDIDATE_VISUAL_PRESET)

    return tuple(rows)


def _npc_level_body(legacy: Any, actor_identity: int, label: str, level: int) -> bytes:
    """The NPC plain body plus EXACTLY the level splice, nothing else.

    Bit 0x0002, tag ``field_mobs.LEVEL_TAG``, spliced at its own
    ascending-mask-bit position -- right after the mask and the name, before
    the HP pair -- which is where ``field_mobs.hostile_npc_attr`` puts it in
    the monster body this row is being compared against.  Everything
    load-bearing here (the bit, the tag, the splice arithmetic) is that
    function's, reused rather than re-derived, the same way
    :func:`_npc_faction_body` reuses the faction splice.
    """
    field_mobs._require_int(level, "level", 1, 0xFFFF)
    baseline = _npc_plain_body(legacy, actor_identity, label)
    mask_at = field_mobs._basic_mask_offset(legacy, baseline, actor_identity)
    mask = int.from_bytes(baseline[mask_at:mask_at + 2], "little")
    if mask & field_mobs.BASIC_BIT_LEVEL:
        raise NameColourSweepError(
            "NPC plain body already sets the level bit; the splice below "
            "would double the field"
        )
    if not mask & field_mobs.BASIC_BIT_NAME:
        raise NameColourSweepError(
            "the level splice point is measured from the name field; a "
            "nameless body would put it somewhere else"
        )
    name_bytes = bytes(legacy.wstr_tag(label))
    level_at = mask_at + 2 + len(name_bytes)
    if baseline[mask_at + 2:level_at] != name_bytes:
        raise NameColourSweepError("frozen make_npc_attr name position drift")
    composed = (
        baseline[:mask_at]
        + int(mask | field_mobs.BASIC_BIT_LEVEL).to_bytes(2, "little")
        + baseline[mask_at + 2:level_at]
        + bytes(legacy.u16tag(field_mobs.LEVEL_TAG, level))
        + baseline[level_at:]
    )
    if len(composed) != len(baseline) + field_mobs.LEVEL_SPLICE_BYTES:
        raise NameColourSweepError("NPC level splice length drift")
    return composed


def _diff_field_set(legacy: Any) -> tuple[SweepActor, ...]:
    """One NPC row per field the two prototypes' bodies disagree about.

    WHAT THE TESTER READS OFF THE SCREEN.  Seven nameboards in a line.  The
    two ends are the controls GT-288 set 2 already drew and the owner already
    graded -- ``N-BASE`` green, ``M-BASE`` pink.  The five between them are
    the NPC prototype with EXACTLY ONE of the monster's field values on it.
    Whichever of those five is pink names the field the client's name-colour
    selector reads; if all five stay green, the answer is not a field in this
    diff and the letter says which candidate is next.

    WHY THESE FIVE AND NOT THE OTHER FIVE ROWS OF THE DIFF.
    ``npc_attr_body_diff.diff`` returns ten fields for these two bodies.
    Excluded, each for a reason that is not "it seemed unlikely":

    * ``actor_identity`` and ``basic_name`` differ only because the sweep
      gives every row its own synthetic identity and its own label.  They are
      artefacts of the instrument, not of the prototypes.
    * ``basic_field_mask`` is not an independent field: it is the presence
      mask, and it differs precisely BECAUSE ``level`` and ``faction``
      differ.  Each row below moves it by exactly the bit its own field owns.
    * ``faction`` is set 1's whole question (``N-F07``/``N-F12``/``N-F999``),
      already composed, already ticketed, and COO-ORDER 2026-09-07T20:50 puts
      set 1 on the bus BEFORE this set.  Repeating it here would spend a boot
      re-asking a question already queued.

    ``current_hp`` and ``max_hp`` move together in ONE row: they are one
    concept (the monster's HP), the client reads them as a pair
    (``make_npc_attr``'s own V64 note), and an NPC with 198,125 current HP and
    100 max HP is a body no production path composes.  That is a deliberate
    departure from one-field-per-row, and it is here rather than hidden.
    """
    anchor = _spawn_anchor(legacy)
    mob = _mob_prototype()
    rows: list[SweepActor] = []
    ordinal = 0

    def npc_row(label: str, body_for) -> None:
        nonlocal ordinal
        placement_index = SWEEP_PLACEMENT_BASE + ordinal * SWEEP_PLACEMENT_STRIDE
        identity = 0x2000 + placement_index + 1
        x, y, z = _row_xyz(anchor, ordinal)
        rows.append(_entry(
            legacy, label=label, actor_type=field_mobs.NPC_STYLE_ACTOR_TYPE,
            actor_identity=identity, npc_attr=body_for(identity, label),
            x=x, y=y, z=z,
        ))
        ordinal += 1

    npc_row("N-BASE", lambda identity, label: _npc_plain_body(legacy, identity, label))
    npc_row("N-LVL", lambda identity, label: _npc_level_body(
        legacy, identity, label, mob.level,
    ))
    npc_row("N-HP", lambda identity, label: _npc_plain_body(
        legacy, identity, label, current_hp=mob.max_hp, max_hp=mob.max_hp,
    ))
    npc_row("N-SPD", lambda identity, label: _npc_plain_body(
        legacy, identity, label, movement_speed=float(mob.speed_walk),
    ))
    npc_row("N-TPL", lambda identity, label: _npc_plain_body(
        legacy, identity, label, template_id=mob.template_id,
    ))
    npc_row("N-PRE", lambda identity, label: _npc_plain_body(
        legacy, identity, label, visual_preset=mob.visual_preset,
    ))

    placement_index = SWEEP_PLACEMENT_BASE + ordinal * SWEEP_PLACEMENT_STRIDE
    variant = replace(mob, placement_index=placement_index, display_name="M-BASE")
    x, y, z = _row_xyz(anchor, ordinal)
    rows.append(_entry(
        legacy, label="M-BASE", actor_type=field_mobs.NPC_STYLE_ACTOR_TYPE,
        actor_identity=variant.actor_identity,
        npc_attr=field_mobs.hostile_npc_attr(
            legacy, variant, faction=field_mobs.FIELD_MOB_FACTION,
        ),
        x=x, y=y, z=z,
    ))
    return tuple(rows)


# ---------------------------------------------------------------------------
# ALL / ALL-NOID -- one boot, every candidate this lane can compose.
# PANYA-ORDER 2026-09-07T23:25+07:00 + addendum 23:50, relayed word for word by
# COO-ORDER 2026-09-07T23:42+07:00 (pf_bridge notes_to_chief/20260907_2342_
# COO-ORDER-panya2325-sweep-all-26-rows-iron-man-square-first-job-LANE-B.md).
# The owner asked for every possibility in ONE attended boot instead of one
# question per bus trip: twenty-six labelled nameboards on the Training Iron
# Man square, ALL-NOID being the same row with the identity families left out
# for a client that refuses the identity shapes.
# ---------------------------------------------------------------------------

#: The Iron Man practice square in bg0001 (PANYA 2350 item 1).  X starts here
#: and steps one row at a time; Y is the owner's number; Z is READ from the
#: shipped dummy row (:data:`ALL_ROW_Z_SOURCE_PLACEMENT_INDEX`) rather than
#: typed here, so an edit to that table moves the sweep with it instead of
#: leaving the row floating over or under the ground the dummies stand on.
ALL_ROW_X0 = 11800.0
ALL_ROW_DX = 150.0
ALL_ROW_Y = 9340.0
#: Two lines, 300 units apart -- the owner allowed the split so twenty-six
#: boards do not run off one screen (PANYA 2350 item 1).
ALL_ROW_Y_SPLIT = 300.0
ALL_ROWS_PER_LINE = 13
ALL_ROW_Z_SOURCE_PLACEMENT_INDEX = 103

#: ``n_ENEMY``: BasicAttr mask bit 0x0800, offset +0x6C, tag 0x14, four bytes,
#: uint32, direction W, PROVEN_EXACT -- pf_bridge notes_to_chief/
#: reference_codex_attr/PF_A2_ATTR_FIELD_DELTA.tsv, semantic_name
#: ``CNetNPC.template.n_ENEMY``.  The tag byte is the same 0x14 the faction
#: field uses because the tag names the WIRE TYPE (u32), not the field: fields
#: are told apart by their mask bit, in ascending bit order, which is the rule
#: this module's bodies are already composed and walked under.  0x0800 is the
#: next bit after faction's 0x0400 and the last BasicAttr bit before the
#: NPCAttr block, so the splice lands at the same boundary the faction splice
#: uses -- after faction when faction is present, which ascending order
#: requires.
BASIC_BIT_ENEMY = 0x0800
ENEMY_TAG = 0x14
ENEMY_WIDTH = 4
ENEMY_SPLICE_BYTES = 1 + ENEMY_WIDTH

#: The owner's seven ``n_ENEMY`` rows (COO-ORDER 2342 item 2 group D): six on
#: the NPC prototype plus one on the monster.  No table in either repository
#: states this field's real domain -- grepped: ``n_ENEMY`` appears in the codex
#: TSV above (the wire layout) and nowhere in ``gamedata/tables``' MOBS
#: columns this lane mines -- so these are the owner's own values, and the
#: order asked for real ones only "if a table naming the domain turns up".
ENEMY_CANDIDATES = (0, 1, 2, 6, 12, 0xFF)

#: Labels whose row this lane can NOT compose, and the refusal that stops it.
#: Named here rather than dropped silently, because the order says a row that
#: cannot be built must come back with its reason (COO-ORDER 2342 item 2).
#: Neither refusal is this module's own: both belong to the module that owns
#: the shape, and weakening either to fill a nameboard would be trading a
#: standing guard for one attended row.
ALL_SET_UNCOMPOSABLE = (
    (
        "N-LNKS",
        "mob_viewer_link.REFUSE_VIEWER_IS_THE_MONSTER -- linking a body to "
        "its own identity is the one shape RE-195 row 61(a) calls certainly "
        "wrong, and mob_viewer_link refuses it at the door",
    ),
    (
        "M-DEAD",
        "field_mobs.hostile_npc_attr refuses a zero current HP: 'a spawn at zero "
        "HP walks into the death lane's predicates and answers a different "
        "question'.  N-HP0 asks the same question on the NPC prototype, "
        "where no death predicate is watching",
    ),
    (
        "M-IDNEG-DEAD",
        "same refusal as M-DEAD -- the death half of the mix cannot be "
        "composed, so the mix cannot either",
    ),
    (
        "N-ID0-LNKP",
        "the zero identity class holds exactly one value (hi == lo == 0), and "
        "N-ID0 carries it in this boot.  A second zero row would have to share "
        "that identity, and two rows sharing an identity overwrite each other "
        "on the client (pf-adversary round ixdda8 finding D3), so this mix is "
        "a separate boot rather than a second nameboard here",
    ),
)

#: Labels that need the WATCHING SESSION's identity, which this module cannot
#: know: ``sweep_entries`` is called from the arrival census with the legacy
#: module and nothing else.  Pass ``viewer_identity=`` and they compose; leave
#: it None -- every caller on main today -- and they are left out rather than
#: filled with a made-up number.  CORE-REQUEST to chief (round ixdda8) asks
#: for the one keyword at the call site.
ALL_SET_NEEDS_VIEWER_IDENTITY = ("N-LNKP", "N-IDNEG-LNKP")

#: The identity families (COO-ORDER 2342 item 2 groups B and F) that
#: ``ALL-NOID`` leaves out.
ALL_IDENTITY_GROUPS = ("identity", "mixed")

#: The identities the identity rows carry.  Zero and negative are the only
#: two sides of the one split PANYA 2350 item 4 says exists: every positive
#: value is the same question, so the sweep asks about <= 0 and no other.
#: The N-HP0 row's zero, as a NAMED constant rather than a literal.  Not
#: cosmetic and not a scanner dodge: ``tools/pf_runtimeres_actor_entry_static
#: .py`` counts server call sites that write a bare zero-HP literal and
#: pins that count at zero across the whole repository, because a PRODUCTION
#: spawn at zero HP walks into the death lane -- the same hazard
#: ``field_mobs.hostile_npc_attr`` refuses outright (see M-DEAD above).  This
#: env-gated attended row is not that, and the repo already has an idiom for
#: reaching zero without moving another lane's counter: the named-constant
#: path the same verifier tracks separately as
#: ``src_modules_passing_zero_hp_by_named_constant``
#: (``RUNTIMERES_DEATH_HP_ZERO`` is the precedent, reports/
#: PF_RUNTIMERES_ENCODER001_SPAWN_THEN_KILL_20260819.md line 214).  The fact
#: itself is not hidden: ``tests/test_name_colour_sweep_all.py`` asserts the
#: N-HP0 body really carries zero on the wire.
SWEEP_HP_ZERO = 0

IDENTITY_ZERO = 0
IDENTITY_NEGATIVE = -1

#: EVERY NAMEBOARD NEEDS ITS OWN ACTOR IDENTITY.  pf-adversary round ixdda8
#: finding D3 measured six rows sharing two identities (-1 across N-IDNEG,
#: M-IDNEG and N-IDNEG-ENM1, 0 across the two zero rows): the client keys an
#: actor by its identity, so two rows carrying the same one overwrite each
#: other and the board that survives names one question while the body drawn
#: may answer another -- a result that cannot be told from a wrong one.
#:
#: The gate this family exists to cross does not care WHICH non-positive
#: value it is.  RE 0x0045C160 / RE-222 (relayed in ka1-A's addendum 2,
#: pf_bridge notes_to_chief/20260908_0057_KA1A-TO-COO-B-sweep-all-addendum2-
#: *.md) puts the exit from the player formula at "the 64-bit identity is not
#: strictly positive", i.e. ``hi < 0`` OR ``hi == lo == 0``.  Every value in
#: this pool sign-extends to ``hi == -1``, so they are all the same side of
#: that split and stay distinct on the wire.
NEGATIVE_IDENTITY_STRIDE = -1


def negative_identity(slot: int) -> int:
    """The ``slot``-th distinct negative identity: -1, -2, -3, ...

    Same side of the RE-222 split for every slot (``hi == -1`` after sign
    extension), distinct so two boards cannot overwrite each other.
    """
    if slot < 0:
        raise NameColourSweepError(
            f"negative identity slot {slot} is not a slot number"
        )
    return IDENTITY_NEGATIVE + slot * NEGATIVE_IDENTITY_STRIDE


def placement_index_for_identity(identity: int) -> int:
    """The placement index a ``FieldMob`` needs to CARRY ``identity``.

    ``FieldMob.actor_identity`` is ``0x2000 + placement_index + 1``, so a
    monster row reaches a non-positive identity through its placement index,
    never by overwriting the derived value.
    """
    return identity - 0x2000 - 1


#: THE ZERO CLASS HAS EXACTLY ONE VALUE.  ``hi == lo == 0`` is one identity,
#: not a family, so exactly one board in a boot can ask the zero question.
#: This is the label that carries it; any other zero row is refused with that
#: reason rather than quietly handed a second copy of 0 (finding D3).
ALL_ZERO_IDENTITY_LABEL = "N-ID0"

#: One declared slot per negative row, so a label's identity does not move
#: when another row joins or leaves the boot (ALL vs ALL-NOID, viewer
#: identity known or not).  Order is the slot number, nothing else.
NEGATIVE_IDENTITY_SLOTS = (
    "N-IDNEG",
    "M-IDNEG",
    "N-IDNEG-LNKP",
    "N-IDNEG-ENM1",
    "M-IDNEG-T31",
    "N-IDNEG-T916",
)


def negative_identity_for(label: str) -> int:
    """The one negative identity declared for ``label``."""
    try:
        slot = NEGATIVE_IDENTITY_SLOTS.index(label)
    except ValueError:
        raise NameColourSweepError(
            f"{label!r} has no declared negative identity slot -- add it to "
            "NEGATIVE_IDENTITY_SLOTS rather than reusing another row's"
        ) from None
    return negative_identity(slot)


#: EVERY label this set can name, in declaration order.  The slot a label has
#: here is what its POSITIVE identity and placement index are derived from, so
#: an identity belongs to a LABEL and not to the order the boot happened to
#: draw in.  Without it the rows are numbered by composition ordinal, and
#: supplying a viewer identity (or dropping the identity families for
#: ALL-NOID) silently renumbers every later board -- so the attended sheet
#: written for one boot describes a different actor in the next.  Measured:
#: N-ENM0 moved from 28313 to 28323 between the two boots before this existed.
#: ~~Screen POSITION is still packed by drawn ordinal, so an absent row leaves
#: no hole in the line; only the identity is pinned to the label.~~
#: [STRUCK, round p9x1mh, 2026-09-08: that was the other half of the same
#: defect and pf-adversary round ``ubmvj1`` D7 named it.  Position is a
#: function of the label now too -- see :func:`all_row_standing_slot` -- and an
#: absent row DOES leave a hole in the line, on purpose.]
ALL_ROW_ORDER = (
    "N-BASE", "M-BASE",
    "N-LVL", "N-HP", "N-SPD", "N-TPL", "N-PRE",
    "N-ID0", "N-IDNEG", "M-IDNEG", "M-IDNEG-T31", "N-IDNEG-T916",
    "N-LNKP", "N-LNKS",
    "N-ENM0", "N-ENM1", "N-ENM2", "N-ENM6", "N-ENM12", "N-ENMFF", "M-ENM1",
    "N-HP0", "M-DEAD",
    "N-IDNEG-LNKP", "N-IDNEG-ENM1", "N-ID0-LNKP", "M-IDNEG-DEAD",
    "M-T001",
)


def all_row_placement_index(label: str) -> int:
    """The reserved-band placement index declared for ``label``."""
    try:
        slot = ALL_ROW_ORDER.index(label)
    except ValueError:
        raise NameColourSweepError(
            f"{label!r} is not in ALL_ROW_ORDER -- a row with no declared slot "
            "would be numbered by draw order and move between boots"
        ) from None
    return SWEEP_PLACEMENT_BASE + slot * SWEEP_PLACEMENT_STRIDE


#: The labels that keep a ground spot, in the order they stand in on the map.
#: ``ALL_ROW_ORDER`` minus the four rows :data:`ALL_SET_UNCOMPOSABLE` says this
#: lane cannot build at all: those four can never stand anywhere, so reserving
#: ground for them would only push the boards that DO compose onto a third
#: line, and the owner approved two (PANYA 2350 item 1).  Everything that can
#: compose in ANY boot keeps its spot in EVERY boot -- including the two rows
#: that need a viewer identity, which is the whole point.
ALL_ROW_STANDING_ORDER = tuple(
    label for label in ALL_ROW_ORDER
    if label not in {label for label, _ in ALL_SET_UNCOMPOSABLE}
)


def all_row_standing_slot(label: str) -> int:
    """The 0-based ground spot ``label`` stands in, in every boot of this set.

    Raises rather than falling back to a draw counter: a row with no reserved
    spot is exactly the shape that moved the boards, and a silent fallback
    would put it back.
    """
    try:
        return ALL_ROW_STANDING_ORDER.index(label)
    except ValueError:
        raise NameColourSweepError(
            f"{label!r} has no reserved ground spot -- it is either absent "
            "from ALL_ROW_ORDER or listed in ALL_SET_UNCOMPOSABLE, and a row "
            "positioned by draw order moves between boots"
        ) from None


#: THE NAME CHIEF LEFT FOR THIS LANE TO TAKE BACK (chief R396 letter
#: ``20260908_0204``, "the words ALL / ALL-NOID are your lane's").  His file
#: reads this tuple FIRST and falls back to its own
#: ``runtime.NAME_COLOUR_SWEEP_EMPTY_WORLD_SETS`` only while this one does not
#: exist, so declaring it here is what moves the vocabulary home -- no round of
#: his in between.  These are the two sets whose question is unanswerable in a
#: populated town: :func:`rows_inside_the_readability_floor` measures boards
#: standing inside :data:`ROW_CLEARANCE_FROM_REAL_NPCS` of a real Port Royal
#: NPC, and a tester cannot tell a sweep board's nameplate from a townsman's
#: when they overlap.
#:
#: Sets 1 and 2 are deliberately NOT here: they ride in the ordinary town and
#: chief's letter pins that they still do, byte for byte.
SWEEP_SETS_WANTING_AN_EMPTY_WORLD = ("ALL", "ALL-NOID")


#: The identity x template rows ka1-A's addendum 2 (2026-09-08T00:57+07:00)
#: added after the Codex runner answered ``0x0045C160``: ``IsOffensive()``
#: reads no wire field at all, it reads ``AI_WANDER[key].n_OFFESIVE`` out of
#: the client's own CONSTDATA through the template.  So once a body is on the
#: NPC branch, the colour comes from the TEMPLATE, and identity alone cannot
#: answer the question -- the two have to be crossed.
#:
#: ``M-IDNEG-T31`` is the row that answers P-2 most directly: a real field
#: monster (Tornado Eagle, ``n_AI_WANDER`` 16 -> ``n_OFFESIVE`` 0), faction 6,
#: at a non-positive identity.  ``N-IDNEG-T916`` is the same crossing on the
#: NPC prototype with the Training Iron Man template (wander 21 ->
#: ``n_OFFESIVE`` 1).  Both templates are READ from the shipped rosters, never
#: typed here.
IDENTITY_TEMPLATE_MOB_SCENE = "Bg0002"
IDENTITY_TEMPLATE_MOB_TEMPLATE_ID = 31


#: WHAT EACH BOARD IS EXPECTED TO SAY IF THE RE IS RIGHT.  ka1-A's addendum 2
#: (2026-09-08T00:57+07:00) asks for a prediction per row, so the attended boot
#: GRADES a hypothesis instead of only recording colours: a board that matches
#: is a confirmation, a board that does not is a gate the RE cannot see, and
#: both are results.  The predictions are ka1-A's, drafted from two findings:
#:
#:   * ``0x0045C160`` (``IsOffensive``) reads no wire field.  It reads
#:     ``AI_WANDER[key].n_OFFESIVE`` out of the client's own CONSTDATA via the
#:     template -- 1 for 47 of the 73 rows, 0 for 26.  Measured against our
#:     tables: template 1/156 (town NPC) wander 2 -> 0; template 916 (Training
#:     Iron Man) wander 21 -> 1; field monsters 27-35 wander 16 -> 0.
#:   * ``0x0043C380`` cuts in FIRST and reads the faction relationship
#:     (``+0x98``, ``+0x1A0``, ``+0x68``, ``+0x248 -> +0xA8``), so "non-positive
#:     identity AND hostile" and "non-positive identity AND not hostile" are
#:     two different questions and get two different boards.
#:
#: A prediction is a sentence, not a pass mark: nothing in this repository can
#: check a colour on a screen, and no test here asserts one is right.
ALL_ROW_PREDICTIONS = {
    "N-BASE": "green -- positive identity, no faction: the player formula, "
              "friendly side.  Already graded green by the owner",
    "M-BASE": "pink -- positive identity, faction 6: the player formula, "
              "hostile side.  Already graded pink by the owner",
    "N-LVL": "green -- positive identity keeps the player formula; a board "
             "that is not green means level reaches the selector",
    "N-HP": "green -- as N-LVL, for current/max HP",
    "N-SPD": "green -- as N-LVL, for movement speed",
    "N-TPL": "green -- as N-LVL, for template_id.  Read together with M-T001, "
             "which asks the same field from the other direction",
    "N-PRE": "green -- as N-LVL, for the visual preset",
    "N-ID0": "yellow -- identity 0/0 leaves the player formula, and template 1 "
             "has n_AI_WANDER 2 -> n_OFFESIVE 0, the NPC formula's quiet side",
    "N-IDNEG": "yellow -- same as N-ID0 through the hi<0 half of the split",
    "M-IDNEG": "orange or red IF the faction gate 0x0043C380 answers first "
               "(template 916, faction 6, hostile on the NPC branch); the "
               "0x3D style if it does not.  This row is the gate-order probe",
    "M-IDNEG-T31": "orange -- a real field monster (Tornado Eagle, template "
                   "31, wander 16 -> n_OFFESIVE 0) that is hostile and not yet "
                   "aggroed, which is the owner's colour table for a field mob. "
                   "The row that answers P-2 most directly",
    "N-IDNEG-T916": "the 0x3D style -- template 916 is wander 21 -> "
                    "n_OFFESIVE 1, the loud side of the NPC formula.  Record "
                    "whatever colour that is; it is not predicted here",
    "N-ENM0": "green -- positive identity, so n_ENEMY should not be reached",
    "N-ENM1": "green -- as N-ENM0; a board that is not green puts n_ENEMY on "
              "the selector path even under the player formula",
    "N-ENM2": "green -- as N-ENM0",
    "N-ENM6": "green -- as N-ENM0",
    "N-ENM12": "green -- as N-ENM0",
    "N-ENMFF": "green -- as N-ENM0",
    "M-ENM1": "pink -- the monster control plus n_ENEMY 1 and nothing else, so "
              "a difference from M-BASE is n_ENEMY and only n_ENEMY",
    "N-HP0": "green -- positive identity; zero current HP asks whether the "
             "death predicate is read before the colour is chosen",
    "N-IDNEG-ENM1": "yellow -- the same board as N-IDNEG unless n_ENEMY is on "
                    "the NPC branch's path.  Read as a diff against N-IDNEG, "
                    "not on its own",
    "N-LNKP": "green -- positive identity.  Gate 4 (linked = the viewer) is "
              "what this row probes; a non-green board is the finding",
    "N-IDNEG-LNKP": "not predicted -- gate 4 crossed with the non-positive "
                    "identity split.  Record the colour",
    "M-T001": "pink -- the monster carrying the NPC template_id.  Read with "
              "N-TPL: the two live hypotheses predict opposite results here",
}


def all_row_predictions() -> dict[str, str]:
    """What each board is expected to say if the RE is right (a copy)."""
    return dict(ALL_ROW_PREDICTIONS)


def prediction_for(label: str) -> str:
    """The prediction declared for ``label``."""
    try:
        return ALL_ROW_PREDICTIONS[label]
    except KeyError:
        raise NameColourSweepError(
            f"{label!r} has no prediction -- a board with no prediction is a "
            "colour written down, not a hypothesis graded (ka1-A addendum 2)"
        ) from None


def rows_inside_the_readability_floor(
    legacy: Any, *, viewer_identity: int | None = None,
) -> tuple[tuple[str, float, str], ...]:
    """``(label, distance, real NPC)`` for every ALL board a live town hides.

    pf-adversary round ubmvj1, D3.  The overlap was known -- the owner placed
    the row by absolute coordinate on a square inside Port Royal -- but it was
    stated as one number for one row, and the attended ticket then told the
    tester to drop "the first four rows".  Measured, the rows inside the floor
    are NOT the first four: two of them are ``M-IDNEG`` and ``M-IDNEG-T31``,
    the gate-order probe and the row that answers P-2 most directly, and the
    real actor next to them is a hostile field mob whose nameboard is the same
    colour ``M-IDNEG-T31`` is predicted to be.  A tester grading that cluster
    can read the real mob's colour as a confirmation.

    So the ticket takes this list rather than a sentence: which boards a
    populated town makes unreadable is a measurement, and it moves whenever a
    row moves.
    """
    real = [
        (float(row[2]), float(row[3]), row[6])
        for row in legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
    ]
    hidden: list[tuple[str, float, str]] = []
    for actor in _all_set(
        legacy, include_identity_rows=True, viewer_identity=viewer_identity,
    ):
        distance, name = min(
            ((((actor.x - x) ** 2 + (actor.y - y) ** 2) ** 0.5), name)
            for x, y, name in real
        )
        if distance < ROW_CLEARANCE_FROM_REAL_NPCS:
            hidden.append((actor.label, distance, name))
    return tuple(hidden)


def all_set_uncomposable_rows() -> tuple[tuple[str, str], ...]:
    """(label, reason) for every ALL row this lane cannot build."""
    return ALL_SET_UNCOMPOSABLE


def all_set_rows_needing_viewer_identity() -> tuple[str, ...]:
    """Labels that appear only when a viewer identity is supplied."""
    return ALL_SET_NEEDS_VIEWER_IDENTITY


def _all_row_z() -> float:
    """The ground the shipped Iron Man dummies stand on, read not typed."""
    for row in field_mob_tables.TOWN_TARGET_PLACEMENTS:
        if row[0] == ALL_ROW_Z_SOURCE_PLACEMENT_INDEX:
            return float(row[4])
    raise NameColourSweepError(
        "placement "
        f"{ALL_ROW_Z_SOURCE_PLACEMENT_INDEX} is not in "
        "field_mob_tables.TOWN_TARGET_PLACEMENTS any more -- the ALL sweep's "
        "ground height has no source"
    )


def _all_row_xyz(label: str, z: float) -> tuple[float, float, float]:
    """The ground spot reserved for ``label``, and for no other row.

    pf-adversary round ``ubmvj1`` D7: this used to take the DRAW ORDINAL -- a
    counter bumped once per row that actually composed -- so the boards moved
    whenever the composed set changed.  Two boots of the same sweep already
    differ that way on ``main``: ``viewer_identity=`` (chief's
    ``pirate-force-server#1099``) makes ``N-LNKP`` compose at slot 12 and
    pushes every one of the eleven boards after it one spot along, and
    ``ALL-NOID`` drops the identity groups and pulls them all back again.  The
    attended tester reads a printed label sheet against boards on a screen; a
    sheet made on a headless dry run of one of those boots names the wrong
    board in the other, and a board that answers a different question than its
    label says is indistinguishable from a wrong ANSWER.

    So the spot is a function of the LABEL alone, over the standing order
    below.  A row that does not compose leaves its spot EMPTY rather than
    closing the gap -- which is itself readable: the tester sees the sheet's
    slot with nothing standing in it and reports "not composed", the same
    thing :func:`all_set_uncomposable_rows` says on the console.
    """
    line, column = divmod(all_row_standing_slot(label), ALL_ROWS_PER_LINE)
    return (
        ALL_ROW_X0 + ALL_ROW_DX * column,
        ALL_ROW_Y + ALL_ROW_Y_SPLIT * line,
        z,
    )


def _splice_enemy(
    legacy: Any,
    body: bytes,
    *,
    actor_identity: int,
    template_id: int,
    visual_preset: str,
    enemy: int,
) -> bytes:
    """``body`` plus EXACTLY the ``n_ENEMY`` field, nothing else.

    Built out of the same two frozen helpers the faction and level splices
    use, at the same BasicAttr/NPCAttr boundary, so a body whose layout moved
    comes back as a named refusal instead of bytes that would reach a client.
    """
    field_mobs._require_int(enemy, "enemy", 0, 0xFFFFFFFF)
    mask_at = field_mobs._basic_mask_offset(legacy, body, actor_identity)
    mask = int.from_bytes(body[mask_at:mask_at + 2], "little")
    if mask & BASIC_BIT_ENEMY:
        raise NameColourSweepError(
            "body already sets the n_ENEMY bit; the splice below would "
            "double the field"
        )
    offset = field_mobs._faction_splice_offset(
        legacy, body, template_id, visual_preset,
    )
    composed = (
        body[:mask_at]
        + int(mask | BASIC_BIT_ENEMY).to_bytes(2, "little")
        + body[mask_at + 2:offset]
        + bytes(legacy.u32tag(ENEMY_TAG, enemy))
        + body[offset:]
    )
    if len(composed) != len(body) + ENEMY_SPLICE_BYTES:
        raise NameColourSweepError("n_ENEMY splice length drift")
    return composed


def _npc_enemy_body(
    legacy: Any,
    actor_identity: int,
    label: str,
    enemy: int,
    *,
    body: bytes | None = None,
) -> bytes:
    baseline = (
        _npc_plain_body(legacy, actor_identity, label) if body is None else body
    )
    return _splice_enemy(
        legacy, baseline,
        actor_identity=actor_identity,
        template_id=NPC_BASE_TEMPLATE_ID,
        visual_preset=NPC_BASE_VISUAL_PRESET,
        enemy=enemy,
    )


def _npc_linked_body(
    legacy: Any,
    actor_identity: int,
    label: str,
    viewer_identity: int,
    *,
    body: bytes | None = None,
) -> bytes:
    baseline = (
        _npc_plain_body(legacy, actor_identity, label) if body is None else body
    )
    return mob_viewer_link.link_viewer_to_npc_attr(
        legacy, baseline,
        viewer_identity=viewer_identity,
        monster_identity=actor_identity,
        template_id=NPC_BASE_TEMPLATE_ID,
        visual_preset=NPC_BASE_VISUAL_PRESET,
    )


def _all_set(
    legacy: Any,
    *,
    include_identity_rows: bool,
    viewer_identity: int | None,
) -> tuple[SweepActor, ...]:
    """Every candidate the owner listed, minus the ones with a written reason.

    WHAT THE TESTER READS OFF THE SCREEN.  Two lines of nameboards on the
    Iron Man square, each carrying its own question in its own label.  The two
    controls are the ends of the diff this lane already measured -- N-BASE
    green and M-BASE pink, both already graded by the owner -- and every other
    board is the NPC prototype carrying exactly one monster-shaped value, or
    the monster prototype carrying exactly one NPC-shaped one.  A board that
    is not green names a field the client's name-colour selector reads; every
    board green means the answer is in none of them, which is a result too.

    ALL-NOID is the same row with the identity families (B and F) left out,
    so a client that will not draw an actor whose identity is 0 or negative
    still returns an answer for the other fields instead of a failed boot.
    """
    mob = _mob_prototype()
    z = _all_row_z()
    rows: list[SweepActor] = []
    skipped = {label for label, _ in ALL_SET_UNCOMPOSABLE}
    if viewer_identity is None:
        skipped.update(ALL_SET_NEEDS_VIEWER_IDENTITY)

    def npc(label: str, group: str, body_for) -> None:
        if label in skipped or (
            not include_identity_rows and group in ALL_IDENTITY_GROUPS
        ):
            return
        placement_index = all_row_placement_index(label)
        identity = 0x2000 + placement_index + 1
        rows.append(_entry(
            legacy, label=label, actor_type=field_mobs.NPC_STYLE_ACTOR_TYPE,
            actor_identity=identity, npc_attr=body_for(identity, label),
            **dict(zip(("x", "y", "z"), _all_row_xyz(label, z))),
        ))

    def npc_fixed_identity(label: str, group: str, identity: int, body_for) -> None:
        """A row whose whole question IS its identity, so it keeps that one."""
        if label in skipped or (
            not include_identity_rows and group in ALL_IDENTITY_GROUPS
        ):
            return
        rows.append(_entry(
            legacy, label=label, actor_type=field_mobs.NPC_STYLE_ACTOR_TYPE,
            actor_identity=identity, npc_attr=body_for(identity, label),
            **dict(zip(("x", "y", "z"), _all_row_xyz(label, z))),
        ))

    def mob_row(
        label: str,
        group: str,
        *,
        placement_index: int | None = None,
        body_for=None,
        prototype=None,
        **overrides: Any,
    ) -> None:
        if label in skipped or (
            not include_identity_rows and group in ALL_IDENTITY_GROUPS
        ):
            return
        index = (
            all_row_placement_index(label)
            if placement_index is None else placement_index
        )
        # pf-adversary round ubmvj1, D6: the prototype is a CALLABLE, resolved
        # only after the group check above.  Passing the FieldMob itself
        # evaluated _identity_template_mob_prototype() as an argument, so a
        # Bg0002 roster regeneration that renumbers template 31 killed
        # ALL-NOID -- the identity-free fallback boot, which draws no Bg0002
        # row at all.
        variant = replace(
            mob if prototype is None else prototype(),
            placement_index=index, display_name=label, **overrides
        )
        body = (
            field_mobs.hostile_npc_attr(
                legacy, variant, faction=field_mobs.FIELD_MOB_FACTION,
            )
            if body_for is None else body_for(variant)
        )
        rows.append(_entry(
            legacy, label=label, actor_type=field_mobs.NPC_STYLE_ACTOR_TYPE,
            actor_identity=variant.actor_identity, npc_attr=body,
            **dict(zip(("x", "y", "z"), _all_row_xyz(label, z))),
        ))

    # Controls (COO-ORDER 2342 item 2).
    npc("N-BASE", "control", lambda i, l: _npc_plain_body(legacy, i, l))
    mob_row("M-BASE", "control")

    # A -- the five body fields the two prototypes actually differ in
    # (npc_attr_body_diff, set 3, already on this branch).
    npc("N-LVL", "body", lambda i, l: _npc_level_body(legacy, i, l, mob.level))
    npc("N-HP", "body", lambda i, l: _npc_plain_body(
        legacy, i, l, current_hp=mob.max_hp, max_hp=mob.max_hp))
    npc("N-SPD", "body", lambda i, l: _npc_plain_body(
        legacy, i, l, movement_speed=float(mob.speed_walk)))
    npc("N-TPL", "body", lambda i, l: _npc_plain_body(
        legacy, i, l, template_id=mob.template_id))
    npc("N-PRE", "body", lambda i, l: _npc_plain_body(
        legacy, i, l, visual_preset=mob.visual_preset))

    # B -- identity.  PANYA 2350 item 4: every positive identity is the same
    # question, so the only split worth a nameboard is <= 0.
    npc_fixed_identity("N-ID0", "identity", IDENTITY_ZERO,
                       lambda i, l: _npc_plain_body(legacy, i, l))
    npc_fixed_identity("N-IDNEG", "identity", negative_identity_for("N-IDNEG"),
                       lambda i, l: _npc_plain_body(legacy, i, l))
    mob_row("M-IDNEG", "identity", placement_index=placement_index_for_identity(
        negative_identity_for("M-IDNEG")))

    # B2 -- identity x template (ka1-A addendum 2, 2026-09-08T00:57+07:00).
    # IsOffensive() reads the template's AI_WANDER row out of client CONSTDATA,
    # so identity alone cannot answer the question once a body is on the NPC
    # branch: the crossing has to be drawn.
    mob_row("M-IDNEG-T31", "identity",
            placement_index=placement_index_for_identity(
                negative_identity_for("M-IDNEG-T31")),
            prototype=_identity_template_mob_prototype)
    npc_fixed_identity(
        "N-IDNEG-T916", "identity", negative_identity_for("N-IDNEG-T916"),
        lambda i, l: _npc_plain_body(
            legacy, i, l, template_id=mob.template_id,
            visual_preset=mob.visual_preset),
    )

    # C -- linked identity (NPCAttr+0x98, mob_viewer_link's own field).
    if viewer_identity is not None:
        npc("N-LNKP", "linked", lambda i, l: _npc_linked_body(
            legacy, i, l, viewer_identity))

    # D -- n_ENEMY.
    for value in ENEMY_CANDIDATES:
        label = "N-ENM%s" % ("FF" if value == 0xFF else value)
        npc(label, "enemy", lambda i, l, v=value: _npc_enemy_body(legacy, i, l, v))
    mob_row("M-ENM1", "enemy", body_for=lambda variant: _splice_enemy(
        legacy,
        field_mobs.hostile_npc_attr(
            legacy, variant, faction=field_mobs.FIELD_MOB_FACTION),
        actor_identity=variant.actor_identity,
        template_id=variant.template_id,
        visual_preset=variant.visual_preset,
        enemy=1,
    ))

    # E -- death.  M-DEAD has a written reason above; N-HP0 asks the same
    # question where no death predicate is watching.
    npc("N-HP0", "death", lambda i, l: _npc_plain_body(
        legacy, i, l, current_hp=SWEEP_HP_ZERO))

    # F -- the mixes the owner asked for.
    if viewer_identity is not None:
        npc_fixed_identity("N-IDNEG-LNKP", "mixed",
                           negative_identity_for("N-IDNEG-LNKP"),
                           lambda i, l: _npc_linked_body(
                               legacy, i, l, viewer_identity))
    npc_fixed_identity("N-IDNEG-ENM1", "mixed",
                       negative_identity_for("N-IDNEG-ENM1"),
                       lambda i, l: _npc_enemy_body(legacy, i, l, 1))

    # The twenty-sixth row (COO-DECISION 2026-09-07T23:42, answering this
    # lane's letter 2245): the monster prototype carrying the NPC's
    # template_id and nothing else.  template_id is the ONE field in the diff
    # where the two live hypotheses predict opposite results, so this row and
    # N-TPL are read together.
    mob_row("M-T001", "reverse", template_id=NPC_BASE_TEMPLATE_ID)

    return tuple(rows)


def all_set_labels(
    legacy: Any,
    *,
    include_identity_rows: bool = True,
    viewer_identity: int | None = None,
) -> tuple[str, ...]:
    """The labels the armed ALL/ALL-NOID boot would draw, in order."""
    return tuple(
        actor.label for actor in _all_set(
            legacy,
            include_identity_rows=include_identity_rows,
            viewer_identity=viewer_identity,
        )
    )


def sweep_actors(
    legacy: Any,
    env: dict | None = None,
    *,
    viewer_identity: int | None = None,
) -> tuple[SweepActor, ...]:
    """The labelled dummy row for the armed set, or ``()`` if unarmed.

    Nothing is sent, scheduled or persisted -- the caller owns dispatch, the
    same contract ``field_mobs.build_field_mob_population`` documents.
    """
    value = (os.environ if env is None else env).get(SWEEP_ENV, "")
    if value == SET_FACTION:
        return _faction_set(legacy)
    if value == SET_ACTOR_TYPE_AND_SKIN:
        return _actor_type_and_skin_set(legacy)
    if value == SET_DIFF_FIELDS:
        return _diff_field_set(legacy)
    if value in (SET_ALL, SET_ALL_NOID):
        return _all_set(
            legacy,
            include_identity_rows=value == SET_ALL,
            viewer_identity=viewer_identity,
        )
    return ()


def unrecognised_env_value(env: dict | None = None) -> str | None:
    """The raw value of ``PF_NAME_COLOUR_SWEEP`` when it is set but unknown.

    ``None`` when the variable is absent, empty, or names a real set -- so a
    caller that prints on a non-``None`` return stays silent on every ordinary
    boot and on both armed boots.

    WHY (chief, round ``ky8m6j``, pf-adversary finding D7).  ``sweep_actors``
    answers an unknown value with ``()``, which is the right REFUSAL but was
    indistinguishable, byte for byte and line for line, from a build that has
    no sweep in it at all: an attended tester who typed
    ``PF_NAME_COLOUR_SWEEP=true`` got a silent ordinary town and no way to tell
    a typo from a stale binary.  The caller prints the value back so the
    console says which of the two happened.
    """
    value = (os.environ if env is None else env).get(SWEEP_ENV, "")
    if not value or value in KNOWN_SETS:
        return None
    return value


def sweep_entries(
    legacy: Any,
    env: dict | None = None,
    *,
    viewer_identity: int | None = None,
) -> tuple[bytes, ...]:
    """Per-actor entry bytes for the armed set, or ``()`` if unarmed.

    CHIEF EXTRACTION (round ``ky8m6j``), NOT A NEW SELECTOR: this is the loop
    that was inside :func:`build_sweep_population`, lifted out unchanged so a
    caller can put these bodies inside SOMEBODY ELSE'S collection instead of
    encoding a second one.  ``build_sweep_population`` now calls it and its
    output is byte-identical to before the extraction.

    WHY A CALLER WANTS THE ENTRIES AND NOT THE FRAME.  ``RE-092`` measured the
    client's remote-actor consumer as replace-by-omission at COLLECTION scope,
    so sending this row as its own ``make_runtime_remote_actors`` frame does
    not add eight dummies to the town -- it replaces the town WITH the eight
    dummies, and the ``N-BASE`` control has no real NPC left to be read
    against.  ``runtime.py`` therefore appends these entries to the arrival
    census (``world_population.append_census_entries``) and sends one
    collection.  ``build_sweep_population`` is kept for tests and for any
    caller that genuinely wants a standalone collection; it is not the way to
    put this row on a live screen.
    """
    actors = sweep_actors(legacy, env, viewer_identity=viewer_identity)
    entries: list[bytes] = []
    for actor in actors:
        movement = legacy.make_remote_movement_attr(
            actor.actor_identity, actor.x, actor.y, actor.z, 0.0,
            mask=FULL_MOVEMENT_MASK,
        )
        entries.append(legacy.make_remote_actor_entry(
            actor.actor_type,
            actor.actor_identity,
            [(NPC_ATTR_ID, actor.npc_attr), (MOVEMENT_ATTR_ID, movement)],
        ))
    return tuple(entries)


def build_sweep_population(legacy: Any, env: dict | None = None) -> tuple[bytes, bytes] | None:
    """``(pc, frame)`` for the armed set's actors ALONE, or ``None`` if unarmed.

    NOT THE LIVE PATH ANY MORE (chief, round ``ky8m6j``).  A collection that
    carries only this row erases every other actor on the client -- see
    :func:`sweep_entries` and RE-092.  Kept because it is a standalone,
    testable encoding of the same bytes and because callers outside a live
    scene census (harnesses, byte comparisons) still want it.
    """
    entries = sweep_entries(legacy, env)
    if not entries:
        return None
    pc, frame = legacy.make_runtime_remote_actors(list(entries))
    if frame != legacy.frame_pc(pc):
        raise NameColourSweepError("sweep frame drift")
    return pc, frame
