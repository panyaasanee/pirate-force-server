"""LANE-B: named, hostile monsters built from real MOBS rows.

WHAT THIS MODULE IS FOR.  M3 asks for red-named monsters in a scene that were
not placed one at a time by hand, built from real ``MOBS`` rows rather than
from attributes we composed.  This module is the builder for that.  Every field
of every monster it emits was copied out of a committed game table by
``tools/pf_mine_scene_mob_roster.py`` into :mod:`field_mob_tables`; the only
derived column is HP, and its derivation has a control (below).

    placement index, XYZ  <- the scene's own .npc placement records
    template id           <- that placement's MOBS n_ID
    visual preset         <- MOBS.s_OUTFIT (the .avt basename the client loads)
    display name          <- TEXTDATA_TH__MOBS_TIP.s_NAME for that n_ID
    max HP                <- STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX

WHY THE SELECTION RULE CAN BE TRUSTED.  The generator keeps a placement when
its template resolves in MOBS and that row's outfit is a single unambiguous
basename.  Run over bg0001 that rule reproduces the frozen
``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS`` table in
``current/pf_login_game_server_v141.py`` exactly: 115 rows, zero mismatches on
index, template, x, y, z and outfit.  That table has been on the wire for
months, so the pipeline that feeds this module is checked against something the
project already trusts rather than against its own reasoning.

THE TWO CONTROLS ON THE DERIVED COLUMNS.  bg0001 placement 30 is the monster
the frozen source already names and gives HP to, independently of any table
this module reads: ``V117_P30_EXACT_HP = 3857`` and
``V119_P30_TARGET_NAME = "Tornado Eagle"``.  Placement 30's template is MOBS 31,
whose level is 27; ``STANDARD_MOB`` level 27 has ``n_HPMAX`` 3857, and
``MOBS_TIP`` 31 is named "Tornado Eagle".  Both frozen constants re-derive.
:func:`assert_frozen_controls` re-checks them against the legacy module at
runtime and refuses if either has drifted.

WHAT IS NEW HERE, STATED PLAINLY BECAUSE IT HAS NEVER BEEN ON THE WIRE.  The
body this module builds is a NAMED body and a HOSTILE body at the same time.
Each half is separately proven and the COMBINATION is not:

* named + HP, no faction: what the runtime sends for placement 30 today
  (V119/V117), rendered by a real client.
* faction, no name: the GT-032 ``HOSTILE_SPAWN`` frame (2026-08-21, PASS both
  layers) - the NPC became selectable as an enemy with a red target panel.
  GT-032's own ticket predicted and observed NO red name label, because that
  frame carried no name bit at all.
* named + faction together: THIS module, never sent, never observed.

So this module must not be read as claiming a red NAME.  What decides name
colour is ``RE-067``, which is open and belongs to lane C.
[STALE as of ``pf_bridge/CLIENT_RE_QUEUE.md`` chief R163/R165, 2026-08-25,
round `dvxb6f`] [MEASURED]: ``RE-067`` is CLOSED (PASS/MIXED) - the actor
half closed BOUNDED NEGATIVE (no colour-deciding read of ``actor_type``,
faction, or ``FONT_COLOR`` was found; the driver is unidentified, and the
"renders in PLAYER colour" theory this module never repeated was chief
R163's own retracted draft).  What decides name colour is still unknown,
but the search for it at the static layer is finished, not open; see
``mob_death.py``'s ``full_roster_override`` docstring for the full
citation trail.  What is claimed is
narrower and testable: the body is byte-for-byte the frozen ``make_npc_attr``
body for that monster, with the BasicAttr mask widened by exactly bit 0x0400
and exactly five bytes of tagged faction spliced in at the ascending-mask-order
position - the same splice GT-032 shipped, computed here from the legacy
serializers rather than from a fixed offset, because a name is variable-length
and the GT-032 constant (36) is only correct for a nameless body.

FACTION VALUES ARE OUR DESIGN.  1 for the player and 6 for the monster come
from SCENE-005 and are this project's composition; the original server's
faction semantics are unrecoverable.  Hostility needs BOTH halves: arena-v2
counted 1,023 neutral results for an NPC at faction 6 against a player left at
the constructor default, so a caller that does not put the player at faction 1
gets a monster that is merely present.  This module builds the monster half
only; the player half lives on the StartGame path, which is the chief's file.

WHAT THIS SCENE CANNOT DELIVER, MEASURED BEFORE THIS MODULE WAS COMMITTED.
bg0001 is a town and its monster placements are sparse.  All thirteen exist,
but no monster in this roster has ANOTHER monster within 1,000 units, and the
densest spot in the whole scene - the Mutant Green Eagle line near
(14455, 9357, 2200) - holds three within 2,000 units and four within about
3,900.  The nearest monster to a new character's spawn is 12,095 units away.
So this module delivers "the monsters this scene's own data defines exist and
are hostile", and it does NOT deliver "a field full of red names in one view".
That second thing needs a field scene, which is M2's delivery, and the same
code runs against it the moment the generator is pointed at one.
:func:`neighbour_census` computes those numbers rather than asserting them, so
a denser scene changes the answer loudly instead of leaving this paragraph to
rot.

NOTHING IS INSTALLED, AND THE IDENTITY SPACE IS SHARED.  This module sends
nothing, schedules nothing and persists nothing, and no module in ``src/``
imports it yet.  ``production_allowed`` is True because this is shippable
behaviour rather than a probe - it needs no scenario flag - but the flag is a
convention marker and no code branches on it.

    THE ONE INTEGRATION HAZARD, WRITTEN DOWN RATHER THAN LEFT TO BE FOUND.
    These monsters ARE members of the bg0001 census.  Their actor identities
    are ``0x2000 + placement_index + 1``, the same rule
    :mod:`world_population` uses, so sending this collection AND the lane-A
    census in the same generation would put thirteen identities on the wire
    twice with different bodies.  The correct wiring is the override, not the
    second collection: build the census and swap the hostile body in for the
    members :func:`hostile_placement_indices` names.  :func:`overlapping_
    identities` exists so a caller can assert the intersection instead of
    discovering it on screen.

CORRECTED 2026-08-26 (round `4z0efc`) - two sentences above are now false and are
kept rather than edited, per this project's own rule.  (1) "no module in
``src/`` imports it yet" stopped being true earlier the same day: this
module's ``load_roster()`` is imported by ``mob_combat.py`` (target
resolution) and ``mob_death.py`` (corpse override / repopulation), and
``runtime.py`` imports this module directly as of CORE-REQUEST-005
(commit ``6105d26``, "wire mob_combat+mob_death into runtime.py dispatch
(MOB-COMBAT-001)", 2026-08-26 09:27 UTC / 16:27 +07:00) -- NOT CORE-REQUEST-007
as an earlier draft of this correction said; 007 (round `keen-pasteur-r6hhp6`)
only added the `mob_ai_control` import, and never touched this one.  (2) the
override THE ONE INTEGRATION HAZARD
above calls for now EXISTS AS CODE: ``mob_death.full_roster_override()``
(this round) is exactly that override - it swaps every roster member's body
in for whatever the census would otherwise send, dead ones as corpses, living
ones (touched or not) hostile and named, reusing this module's own
:func:`hostile_actor_entry` under the hood.  What is STILL true, and is the
actual reason this docstring's headline claim ("never sent, never observed")
still holds: nothing in ``runtime.py`` calls ``full_roster_override`` yet -
its one existing census-override call site still calls the narrower
``corpse_override``, which is chief's file and this round's one-line request,
not a wiring line this lane can write itself.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from . import field_mob_tables
from .population import (
    FULL_MOVEMENT_MASK,
    MOVEMENT_ATTR_ID,
    NPC_ATTR_ID,
    NPC_STYLE_ACTOR_TYPE,
    SCENE_ID,
    SCENE_SEQUENCE,
)


# Convention marker only; nothing in this tree branches on it.
production_allowed = True
test_only = False

# The SCENE-005 pairing, carried here so this module does not import a
# scenario-gated probe lane to reach two integers.  Both values are OUR design.
FIELD_MOB_FACTION = 6
PLAYER_PAIR_FACTION = 1

# BasicAttr mask bit and wire tag for faction (u32 at object+0x68), and the
# nameless baseline mask the splice is defined against.
BASIC_BIT_NAME = 0x0001
BASIC_BIT_FACTION = 0x0400
FACTION_TAG = 0x14
FACTION_WIDTH = 4
FACTION_SPLICE_BYTES = 1 + FACTION_WIDTH

# The frozen constants the derived columns are checked against.
CONTROL_PLACEMENT_INDEX = 30
CONTROL_TEMPLATE_ID = 31

# The proven schedule: the identical collection is queued once immediately and
# once after model readiness.  Carried, not re-derived, from world_population.
INITIAL_REAPPLY_MS = 3000

HEADINGS = (0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0)
_FLOAT32_MAX = 3.4028234663852886e38


class FieldMobContractError(ValueError):
    """A refusal from this module, always with a reason in the message."""


@dataclass(frozen=True)
class FieldMob:
    """One monster placement, every field copied from a table but ``max_hp``."""

    placement_index: int
    template_id: int
    x: float
    y: float
    z: float
    visual_preset: str
    display_name: str
    level: int
    rank: int
    ai_wander: int
    ai_combat: int
    speed_walk: int
    max_hp: int
    drops_normal: int
    drops_equipment: int
    drops_specially: int

    @property
    def actor_identity(self) -> int:
        return 0x2000 + self.placement_index + 1


@dataclass(frozen=True)
class FieldMobGeneration:
    """One built collection: who is in it, its bytes, and nothing installed."""

    scene: str
    mob_count: int
    placement_indices: tuple[int, ...]
    actor_identities: tuple[int, ...]
    faction: int
    pc: bytes
    frame: bytes

    @property
    def pc_bytes(self) -> int:
        return len(self.pc)

    @property
    def frame_bytes(self) -> int:
        return len(self.frame)


def _require_float32(value: Any, label: str) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        raise FieldMobContractError("%s must be a finite float32 value" % label)
    result = float(value)
    if not math.isfinite(result) or abs(result) > _FLOAT32_MAX:
        raise FieldMobContractError("%s must be a finite float32 value" % label)
    return result


def _require_anchor(player_xyz: Any) -> tuple[float, float, float]:
    if type(player_xyz) is not tuple or len(player_xyz) != 3:
        raise FieldMobContractError("player XYZ must be an exact three-value tuple")
    x, y, z = (
        _require_float32(value, "player %s" % axis)
        for axis, value in zip("xyz", player_xyz)
    )
    return (x, y, z)


def _require_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or type(value) is bool:
        raise FieldMobContractError("%s must be an integer" % label)
    if not minimum <= value <= maximum:
        raise FieldMobContractError(
            "%s must be an integer in [%d,%d]" % (label, minimum, maximum)
        )
    return value


def load_roster() -> tuple[FieldMob, ...]:
    """Type and check the generated roster.  No file is read at import time.

    The generated module is data, so it is validated here rather than trusted:
    a duplicate placement, a template that cannot fit the u16 the client reads,
    a non-positive HP or an empty visual preset each refuse by name.
    """
    rows = getattr(field_mob_tables, "HOSTILE_PLACEMENTS", None)
    if type(rows) is not list or not rows:
        raise FieldMobContractError("generated roster is missing or empty")
    mobs: list[FieldMob] = []
    seen: set[int] = set()
    for ordinal, row in enumerate(rows):
        if type(row) is not tuple or len(row) != 16:
            raise FieldMobContractError("roster row %d has wrong shape" % ordinal)
        placement_index = _require_int(row[0], "placement index", 0, 0xDFFE)
        if placement_index in seen:
            raise FieldMobContractError("duplicate placement index in roster")
        seen.add(placement_index)
        template_id = _require_int(row[1], "template id", 1, 0xFFFF)
        x = _require_float32(row[2], "placement x")
        y = _require_float32(row[3], "placement y")
        z = _require_float32(row[4], "placement z")
        visual_preset, display_name = row[5], row[6]
        if type(visual_preset) is not str or not visual_preset:
            raise FieldMobContractError("visual preset must be non-empty text")
        if type(display_name) is not str or not display_name:
            raise FieldMobContractError("display name must be non-empty text")
        level = _require_int(row[7], "level", 1, 255)
        rank = _require_int(row[8], "rank", 1, 0xFFFF)
        ai_wander = _require_int(row[9], "ai wander", 0, 0xFFFF)
        ai_combat = _require_int(row[10], "ai combat", 1, 0xFFFF)
        speed_walk = _require_int(row[11], "speed walk", 0, 0xFFFF)
        max_hp = _require_int(row[12], "max hp", 1, 0xFFFFFFFF)
        mobs.append(FieldMob(
            placement_index, template_id, x, y, z, visual_preset, display_name,
            level, rank, ai_wander, ai_combat, speed_walk, max_hp,
            _require_int(row[13], "drops normal", 0, 0x7FFFFFFF),
            _require_int(row[14], "drops equipment", 0, 0x7FFFFFFF),
            _require_int(row[15], "drops specially", 0, 0x7FFFFFFF),
        ))
    return tuple(mobs)


def hostile_placement_indices() -> tuple[int, ...]:
    """The census members whose body must be replaced, for an override wiring."""
    return tuple(mob.placement_index for mob in load_roster())


def overlapping_identities(other_indices: Any) -> tuple[int, ...]:
    """Actor identities this roster shares with another placement selection.

    A non-empty result means the caller is about to send the same identity
    twice in one generation.  It is returned rather than raised because the
    intersection is the normal case for the bg0001 census: these monsters ARE
    census members, and the answer is to override their bodies, not to skip
    them.
    """
    if type(other_indices) not in (tuple, list, set, frozenset):
        raise FieldMobContractError("other indices must be a collection")
    other = set()
    for value in other_indices:
        other.add(_require_int(value, "placement index", 0, 0xDFFE))
    return tuple(
        mob.actor_identity for mob in load_roster()
        if mob.placement_index in other
    )


def assert_frozen_controls(legacy: Any) -> None:
    """Refuse if either independently frozen constant no longer re-derives.

    This is the check that keeps the derived HP column and the mined name
    honest.  It compares against ``v141``'s own constants, which were pinned
    from a different direction (a live run, not a table join).
    """
    roster = {mob.placement_index: mob for mob in load_roster()}
    control = roster.get(CONTROL_PLACEMENT_INDEX)
    if control is None:
        raise FieldMobContractError(
            "roster no longer carries the control placement %d"
            % CONTROL_PLACEMENT_INDEX
        )
    if control.template_id != CONTROL_TEMPLATE_ID:
        raise FieldMobContractError(
            "control placement template drift: %d" % control.template_id
        )
    frozen_hp = getattr(legacy, "V117_P30_EXACT_HP", None)
    if control.max_hp != frozen_hp:
        raise FieldMobContractError(
            "derived HP %r does not match frozen V117_P30_EXACT_HP %r"
            % (control.max_hp, frozen_hp)
        )
    frozen_name = getattr(legacy, "V119_P30_TARGET_NAME", None)
    if control.display_name != frozen_name:
        raise FieldMobContractError(
            "mined name %r does not match frozen V119_P30_TARGET_NAME %r"
            % (control.display_name, frozen_name)
        )
    if getattr(legacy, "V112_MONSTER_INDEX", None) != CONTROL_PLACEMENT_INDEX:
        raise FieldMobContractError("frozen monster index drift")


def _faction_splice_offset(
    legacy: Any,
    baseline: bytes,
    template_id: int,
    visual_preset: str,
) -> int:
    """Where bit 0x0400 lands: right after the BasicAttr block, before NPCAttr's.

    Computed from the legacy serializers rather than written down, because the
    BasicAttr block ends at a variable offset once a name is present.  The
    NPCAttr tail is fixed-shape, so the position is ``len(baseline) - len(tail)``.
    """
    npc_mask = 0x01 | (0x04 if visual_preset else 0)
    tail = (
        bytes(legacy.u8tag(0x0B, npc_mask))
        + bytes(legacy.u16tag(0x12, template_id))
    )
    if visual_preset:
        tail += bytes(legacy.wstr_tag(visual_preset))
    if not baseline.endswith(tail):
        raise FieldMobContractError(
            "frozen make_npc_attr tail drift: the NPCAttr block is no longer "
            "mask + template + preset, so the faction splice position is stale"
        )
    return len(baseline) - len(tail)


def hostile_npc_attr(
    legacy: Any,
    mob: FieldMob,
    *,
    current_hp: int | None = None,
    scene_id: int = SCENE_ID,
    scene_sequence: int = SCENE_SEQUENCE,
    faction: int = FIELD_MOB_FACTION,
    with_name: bool = True,
) -> bytes:
    """The frozen named body plus EXACTLY the five faction bytes.

    The result is refused unless it equals ``legacy.make_npc_attr(...)`` for the
    same monster with the BasicAttr mask widened by exactly bit 0x0400 and the
    tagged faction spliced in at ascending-mask-bit order.  Any other delta
    means the field landed somewhere else and no bytes come back.
    """
    if type(mob) is not FieldMob:
        raise FieldMobContractError("mob must be the typed FieldMob record")
    if type(with_name) is not bool:
        raise FieldMobContractError("with_name must be a bool")
    _require_int(faction, "faction", 0, 0xFFFFFFFF)
    if faction == 0:
        raise FieldMobContractError(
            "faction 0 is the player constructor default: arena-v2 counted "
            "1,023 neutral results for that pairing, so it spawns a monster "
            "that is merely present"
        )
    hp = mob.max_hp if current_hp is None else _require_int(
        current_hp, "current hp", 0, 0xFFFFFFFF,
    )
    if hp == 0:
        raise FieldMobContractError(
            "a spawn at zero HP walks into the death lane's predicates and "
            "answers a different question than this module asks"
        )
    name = mob.display_name if with_name else ""
    baseline = legacy.make_npc_attr(
        mob.template_id,
        mob.actor_identity,
        scene_id,
        scene_sequence,
        mob.visual_preset,
        hp,
        mob.max_hp,
        basic_name=name,
    )
    offset = _faction_splice_offset(
        legacy, baseline, mob.template_id, mob.visual_preset,
    )
    mask_at = _basic_mask_offset(legacy, baseline, mob.actor_identity)
    mask = int.from_bytes(baseline[mask_at:mask_at + 2], "little")
    if bool(mask & BASIC_BIT_NAME) is not bool(name):
        raise FieldMobContractError(
            "frozen make_npc_attr name bit drift: mask 0x%04X does not agree "
            "with a %s body" % (mask, "named" if name else "nameless")
        )
    if mask & BASIC_BIT_FACTION:
        raise FieldMobContractError(
            "frozen make_npc_attr already sets bit 0x0400; the splice below "
            "would double the field"
        )
    composed = (
        baseline[:mask_at]
        + int(mask | BASIC_BIT_FACTION).to_bytes(2, "little")
        + baseline[mask_at + 2:offset]
        + bytes(legacy.u32tag(FACTION_TAG, faction))
        + baseline[offset:]
    )
    if len(composed) != len(baseline) + FACTION_SPLICE_BYTES:
        raise FieldMobContractError("hostile NPCAttr length drift")
    return composed


def _basic_mask_offset(legacy: Any, baseline: bytes, actor_identity: int) -> int:
    """The offset of the BasicAttr u16 mask VALUE inside a frozen body."""
    head = (
        bytes(legacy.u8tag(0x0B, 1))
        + bytes(legacy.qwordtag(0x32, actor_identity))
    )
    if not baseline.startswith(head):
        raise FieldMobContractError(
            "frozen make_npc_attr head drift: the body no longer opens with "
            "the DBAttribute mask and the tagged identity"
        )
    # +1 skips the mask's own tag byte and lands on the little-endian u16.
    return len(head) + 1


def hostile_actor_entry(
    legacy: Any,
    mob: FieldMob,
    *,
    current_hp: int | None = None,
    scene_id: int = SCENE_ID,
    scene_sequence: int = SCENE_SEQUENCE,
    faction: int = FIELD_MOB_FACTION,
    with_name: bool = True,
) -> bytes:
    """One actor entry: hostile named NPCAttr plus the frozen full-mask movement.

    This is the piece an override wiring needs - build the census, then replace
    the entries for :func:`hostile_placement_indices` with these.
    """
    npc_attr = hostile_npc_attr(
        legacy, mob, current_hp=current_hp, scene_id=scene_id,
        scene_sequence=scene_sequence, faction=faction, with_name=with_name,
    )
    movement = legacy.make_remote_movement_attr(
        mob.actor_identity, mob.x, mob.y, mob.z,
        HEADINGS[mob.placement_index & 3],
        mask=FULL_MOVEMENT_MASK,
    )
    return legacy.make_remote_actor_entry(
        NPC_STYLE_ACTOR_TYPE,
        mob.actor_identity,
        [(NPC_ATTR_ID, npc_attr), (MOVEMENT_ATTR_ID, movement)],
    )


def nearest_first(
    player_xyz: tuple[float, float, float],
    roster: tuple[FieldMob, ...] | None = None,
) -> tuple[FieldMob, ...]:
    """Order the roster nearest-first, ties broken by placement index."""
    x, y, z = _require_anchor(player_xyz)
    mobs = load_roster() if roster is None else roster
    ordered = sorted(
        mobs,
        key=lambda mob: (
            (mob.x - x) ** 2 + (mob.y - y) ** 2 + (mob.z - z) ** 2,
            mob.placement_index,
        ),
    )
    return tuple(ordered)


def neighbour_census(radius: float) -> dict:
    """How many monsters share a neighbourhood of ``radius`` with another.

    The measurement behind this module's refusal to promise a crowded view.
    ``best`` is the placement with the most neighbours; ``best_count`` counts
    the neighbours only, not the placement itself.
    """
    limit = _require_float32(radius, "radius")
    if limit <= 0.0:
        raise FieldMobContractError("radius must be positive")
    roster = load_roster()
    limit_squared = limit * limit
    counts = {}
    for mob in roster:
        counts[mob.placement_index] = sum(
            1 for other in roster
            if other is not mob
            and (other.x - mob.x) ** 2
            + (other.y - mob.y) ** 2
            + (other.z - mob.z) ** 2 <= limit_squared
        )
    best = max(sorted(counts), key=lambda index: (counts[index], -index))
    return {
        "radius": limit,
        "mob_count": len(roster),
        "with_a_neighbour": sum(1 for value in counts.values() if value),
        "best": best,
        "best_count": counts[best],
        "counts": counts,
    }


def build_field_mob_population(
    legacy: Any,
    player_xyz: tuple[float, float, float],
    mob_count: int | None = None,
    *,
    faction: int = FIELD_MOB_FACTION,
    with_name: bool = True,
) -> FieldMobGeneration:
    """Build the scene's monsters as ONE RuntimeRes collection, nearest first.

    Nothing is sent, scheduled or persisted.  The caller owns dispatch, owes
    the frame the reapply the accepted evidence was measured with
    (:data:`INITIAL_REAPPLY_MS`), and owes the player half of the pairing
    (faction :data:`PLAYER_PAIR_FACTION` on StartGame) without which these
    monsters are present but neutral.

    Sending this collection alongside the lane-A census duplicates thirteen
    actor identities - see :func:`overlapping_identities`.
    """
    assert_frozen_controls(legacy)
    roster = nearest_first(player_xyz)
    if mob_count is None:
        count = len(roster)
    else:
        count = _require_int(mob_count, "mob count", 1, len(roster))
    selected = roster[:count]
    entries = [
        hostile_actor_entry(
            legacy, mob, faction=faction, with_name=with_name,
        )
        for mob in selected
    ]
    pc, frame = legacy.make_runtime_remote_actors(entries)
    if frame != legacy.frame_pc(pc):
        raise FieldMobContractError("frame drift")
    return FieldMobGeneration(
        field_mob_tables.SCENE,
        count,
        tuple(mob.placement_index for mob in selected),
        tuple(mob.actor_identity for mob in selected),
        faction,
        pc,
        frame,
    )


PIN_ID = "port_royal_field_mobs_hostile_001"
PIN_BUILD_ORDER = "BUILD-004 / FIELD-MOBS-001"
PIN_LANE = "B_COMBAT"


def pin_document(legacy: Any) -> dict:
    """The pin that ships in ``scenarios/`` - a description, not a switch.

    No flag loads this and no loader accepts it.  It exists so an attended
    ticket can state what this lane expects BEFORE the run, in the same shape
    lane A's ``world_population_full_001.json`` uses, and so the expectations
    cannot drift away from the code that produces them: a test compares the
    committed file against this function.
    """
    assert_frozen_controls(legacy)
    anchors = (
        ("v141_V134_PLAYER_XYZ",
         (legacy.V134_PLAYER_X, legacy.V134_PLAYER_Y, legacy.V134_PLAYER_Z)),
        ("v141_V135_PLAYER_XYZ",
         (legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y, legacy.V135_PLAYER_Z)),
    )
    roster = load_roster()
    built = [
        (label, build_field_mob_population(legacy, anchor))
        for label, anchor in anchors
    ]
    close = neighbour_census(1000.0)
    wide = neighbour_census(2000.0)
    return {
        "schema": 1,
        "id": PIN_ID,
        "lane": PIN_LANE,
        "build_order": PIN_BUILD_ORDER,
        "test_only": test_only,
        "production_allowed": production_allowed,
        "selection": "none_default_behaviour_no_scenario_flag",
        "not_a_scenario": (
            "this file is a pin, not a switch - no flag loads it and no "
            "scenario loader accepts it"
        ),
        "scene": field_mob_tables.SCENE,
        "source_digests": dict(field_mob_tables.SOURCE_DIGESTS),
        "predicate_census": dict(field_mob_tables.PREDICATE_CENSUS),
        "hostility": {
            "basic_attr_mask_bit": BASIC_BIT_FACTION,
            "wire_tag": FACTION_TAG,
            "npc_side_value": FIELD_MOB_FACTION,
            "player_side_value": PLAYER_PAIR_FACTION,
            "both_halves_required": True,
            "player_half_owner": "start_game_path_in_the_chiefs_file",
        },
        "population": {
            "trigger": "caller_owned_no_dispatch_in_this_module",
            "order": "nearest_first_by_squared_distance_then_placement_index",
            "initial_reapply_ms": INITIAL_REAPPLY_MS,
            "mob_count": len(roster),
            "distinct_templates": len({mob.template_id for mob in roster}),
            "actor_type": NPC_STYLE_ACTOR_TYPE,
            "shares_identity_space_with": "world_population_bg0001_census",
        },
        "anchors": [
            {
                "label": label,
                "x": generation_anchor[0],
                "y": generation_anchor[1],
                "z": generation_anchor[2],
                "pc_bytes": generation.pc_bytes,
                "frame_bytes": generation.frame_bytes,
                "placement_indices": list(generation.placement_indices),
            }
            for (label, generation_anchor), (_, generation)
            in zip(anchors, built)
        ],
        "roster": [
            {
                "placement_index": mob.placement_index,
                "actor_identity": mob.actor_identity,
                "template_id": mob.template_id,
                "display_name": mob.display_name,
                "visual_preset": mob.visual_preset,
                "level": mob.level,
                "max_hp": mob.max_hp,
                "x": mob.x,
                "y": mob.y,
                "z": mob.z,
                "drops_normal": mob.drops_normal,
                "drops_equipment": mob.drops_equipment,
                "drops_specially": mob.drops_specially,
            }
            for mob in roster
        ],
        "this_scene_cannot_crowd_one_view": {
            "with_a_neighbour_within_1000": close["with_a_neighbour"],
            "densest_placement_within_2000": wide["best"],
            "its_neighbour_count": wide["best_count"],
        },
        "nonclaims": [
            "faction 1 and 6 are OUR design, not the original server's",
            "named AND hostile in one body has never been on the wire: the "
            "named half is V119/V117, the hostile half is GT-032, the "
            "combination is new",
            "no claim about NAME COLOUR - what decides it is RE-067, open, "
            "lane C. [STALE as of pf_bridge/CLIENT_RE_QUEUE.md chief "
            "R163/R165, 2026-08-25, round dvxb6f] [MEASURED]: RE-067 is "
            "CLOSED (PASS/MIXED, actor half BOUNDED NEGATIVE) - still no "
            "claim about name colour, but the static-layer search is "
            "finished, not open; GT-084/RIDER-084-A carries the "
            "client-observable question now",
            "no aggro, no attack, no death, no drop: this lane builds the "
            "monster, not the fight",
            "max_hp is DERIVED from STANDARD_MOB by level; the two frozen "
            "controls it re-derives are placement 30 only",
            "nothing imports this module, so on its own it changes nothing "
            "the player sees",
        ],
    }


def roster_report(legacy: Any, player_xyz: tuple[float, float, float]) -> dict:
    """What a ticket needs to pin expectations before an attended run.

    ASCII-safe by construction: every string in the roster is escaped on the
    way out, because this report is printed on a code page 874 console.
    """
    assert_frozen_controls(legacy)
    generation = build_field_mob_population(legacy, player_xyz)
    x, y, z = _require_anchor(player_xyz)
    rows = []
    for mob in nearest_first(player_xyz):
        distance = math.sqrt(
            (mob.x - x) ** 2 + (mob.y - y) ** 2 + (mob.z - z) ** 2
        )
        rows.append({
            "placement_index": mob.placement_index,
            "actor_identity": mob.actor_identity,
            "template_id": mob.template_id,
            "display_name": ascii(mob.display_name),
            "visual_preset": ascii(mob.visual_preset),
            "level": mob.level,
            "max_hp": mob.max_hp,
            "distance": round(distance, 3),
        })
    return {
        "scene": field_mob_tables.SCENE,
        "anchor": [x, y, z],
        "mob_count": generation.mob_count,
        "distinct_templates": len({mob.template_id for mob in load_roster()}),
        "faction": generation.faction,
        "player_pair_faction": PLAYER_PAIR_FACTION,
        "initial_reapply_ms": INITIAL_REAPPLY_MS,
        "pc_bytes": generation.pc_bytes,
        "frame_bytes": generation.frame_bytes,
        "source_digests": dict(field_mob_tables.SOURCE_DIGESTS),
        "predicate_census": dict(field_mob_tables.PREDICATE_CENSUS),
        "mobs": rows,
    }
