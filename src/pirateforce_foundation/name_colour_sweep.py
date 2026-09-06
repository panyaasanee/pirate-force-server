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

from . import field_mobs
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
KNOWN_SETS = (SET_FACTION, SET_ACTOR_TYPE_AND_SKIN)

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
# NONCLAIM, and it is the open question of this candidate: report line 53
# names 5 CAvatarNPC, line 105 places it as a CHILD of CNetNPC (4, what we
# emit today), lines 168/170 show 4 and 5 sharing the +0x74/+0x78 name
# GETTERS off actor+0x358, and line 62 shows both gated the same way by the
# factory flag [this+0x6D] -- so 5 is a real flip of the envelope's class
# under a controlled comparison.  But the name BOARD is built by vtable
# +0x7C (report section 4, lines 175-177) and the report pins +0x7C for
# CNetActor (0x456580) and CNetNPC (0x45C560) ONLY.  CAvatarNPC has its own
# vtable (0xF0DFF8) and NOTHING committed in either repository carries its
# +0x7C.  Report line 292 says so itself: whether CAvatarNPC is reachable
# from a server-side stream "was not traced".  So: 5 is strictly better than
# 3 (3 is proven to build no object; 5 is not proven to draw no board) and
# it is NOT proven to draw one.  RE ticket body for the one dword that
# settles it -- [0xF0DFF8 + 0x7C] vs 0x45C560 -- went to LANE-K in round
# b08g3z; until it comes back, an AT5 row showing no nameplate is a known
# possible outcome of set 2 and must not be recorded as a colour FAIL.
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


def _npc_plain_body(
    legacy: Any,
    actor_identity: int,
    label: str,
    *,
    visual_preset: str = NPC_BASE_VISUAL_PRESET,
) -> bytes:
    """``legacy.make_npc_attr`` with no splice at all -- the GT-131 shape."""
    return legacy.make_npc_attr(
        NPC_BASE_TEMPLATE_ID,
        actor_identity,
        SCENE_ID,
        SCENE_SEQUENCE,
        visual_preset,
        NPC_BASE_HP,
        NPC_BASE_HP,
        movement_speed=0.0,
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


def sweep_actors(legacy: Any, env: dict | None = None) -> tuple[SweepActor, ...]:
    """The labelled dummy row for the armed set, or ``()`` if unarmed.

    Nothing is sent, scheduled or persisted -- the caller owns dispatch, the
    same contract ``field_mobs.build_field_mob_population`` documents.
    """
    value = (os.environ if env is None else env).get(SWEEP_ENV, "")
    if value == SET_FACTION:
        return _faction_set(legacy)
    if value == SET_ACTOR_TYPE_AND_SKIN:
        return _actor_type_and_skin_set(legacy)
    return ()


def build_sweep_population(legacy: Any, env: dict | None = None) -> tuple[bytes, bytes] | None:
    """``(pc, frame)`` for the armed set's actors, or ``None`` if unarmed."""
    actors = sweep_actors(legacy, env)
    if not actors:
        return None
    entries = []
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
    pc, frame = legacy.make_runtime_remote_actors(entries)
    if frame != legacy.frame_pc(pc):
        raise NameColourSweepError("sweep frame drift")
    return pc, frame
