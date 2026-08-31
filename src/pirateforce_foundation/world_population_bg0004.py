"""Bg0004 (Slave Market Island) census composer - LANE-A BUILD-002 door 1.

``COO-DECISION 2026-08-30T14:41+07:00`` picked scene 4 as the first of ten
already-checked-safe shut doors to build a composer for.  This is the fourth
sibling of the same pattern ``world_population`` (scene 1), ``_bg0002``
(scene 2) and ``_bg0015`` (scene 14) already ship: it refuses anywhere but
scene 4, over ``world_bg0004_identity``'s 84 shippable placements of 116.
Every wire call below is the exact frozen serializer the other three already
use (``legacy.make_npc_attr`` / ``make_remote_movement_attr`` /
``make_remote_actor_entry`` / ``make_runtime_remote_actors``), and the wire
header constants and the accepted initial+reapply schedule are IMPORTED from
``world_population`` rather than redefined - they describe the wire format,
which is not scene-specific.

WHAT IS DIFFERENT FROM THE OTHER THREE, NAMED RATHER THAN LEFT IMPLICIT.

* This scene has the biggest unresolved fraction of the four: 32 of 116
  placements (28%) are dropped, dominated by one dense 25-placement cluster
  (Mob-Set 107) whose leader has no ``MOBS_TIP`` name at all.  See
  ``world_bg0004_identity``'s docstring for the full breakdown.  The console
  line prints ``assembled=N/116`` every boot, never quietly against the 84
  that happen to resolve.
* No faction/hostile bit on ANY entry here, same convention as the other
  three: this module ships identity and position, not combat presentation.
  A caller that wants the 11 ranked Mob-Set rows (28, 29, 30, 31 .. 38, 45,
  46, 108 - the resolved rows with ``rank != 0`` in
  ``world_bg0004_identity._RESOLVED_ROWS``) hostile owes them the same
  override splice lane B's hostile-monster module and ``mob_death.py`` use
  for the other scenes, generalized here - not built in this module.
* HP is real and comes from the table chain, not composed:
  ``STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX``.  Sent as current == max
  (alive), matching every other census in this tree.

THE HANDBACK, STATED PLAINLY BECAUSE IT IS THIS ROUND'S REAL LIMIT.  Nothing
in this repository calls this module yet.  ``runtime.py``'s census dispatch
is chief's file, not this lane's, and this round does not touch it or ask
for scene 4's login door to open (``COO-DECISION 2026-08-30T14:41+07:00``
says explicitly: "ยังไม่แก้ login_entry_allowed ของฉาก 4 จนกว่าตัวประกอบจะ
พร้อมจริง" - do not open the door until the composer is ready, and a single
round's composer with no attended eyes on it yet is not "ready" in the sense
that decision means).  The one-line request for the next wiring step is in
this round's PR body.

WHAT THIS MODULE DOES NOT CLAIM.  Everything
``world_bg0004_identity``'s "WHAT THIS MODULE DOES NOT CLAIM" says,
unchanged, and: no human has ever seen this scene in this project, so there
is no client-observable layer under any of it yet.  Until a ticket exists
for this scene, ``census_console_lines`` is wire/DB-layer evidence and
nothing above that.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import world_bg0004_identity as identity
from . import world_population
from .population import (
    FULL_MOVEMENT_MASK,
    MOVEMENT_ATTR_ID,
    NPC_ATTR_ID,
    NPC_STYLE_ACTOR_TYPE,
)


# Convention marker only: nothing branches on it and no chief-owned file
# imports this module yet.  See the handback above before reading this as
# "live today".
production_allowed = True
test_only = False

SCENE_N_ID = identity.SCENE_N_ID
SCENE_SEQUENCE = 0
ROSTER_COUNT = len(identity.shippable_placements())
PLACEMENT_COUNT = identity.PLACEMENT_COUNT
UNRESOLVED_COUNT = PLACEMENT_COUNT - ROSTER_COUNT
DEFAULT_ACTOR_COUNT = ROSTER_COUNT

WIRE_HEADER_BYTES = world_population.WIRE_HEADER_BYTES
WIRE_COUNT_TAG_OFFSET = world_population.WIRE_COUNT_TAG_OFFSET
COLLECTION_TAG = world_population.COLLECTION_TAG
INITIAL_REAPPLY_MS = world_population.INITIAL_REAPPLY_MS

COUNT_SOURCE_FULL_ROSTER = "bg0004_full_roster"
COUNT_SOURCE_CALLER = "caller_requested"
COUNT_SOURCES = (COUNT_SOURCE_FULL_ROSTER, COUNT_SOURCE_CALLER)


class Bg0004CensusError(ValueError):
    """A refusal from this module, always with a reason in the message."""


@dataclass(frozen=True)
class Bg0004PopulationGeneration:
    """One built Bg0004 collection: its membership, its bytes, nothing sent."""

    actor_count: int
    placement_indices: tuple[int, ...]
    actor_identities: tuple[int, ...]
    n_ids: tuple[int, ...]
    display_names: tuple[str, ...]
    anchor: tuple[float, float, float]
    pc: bytes
    frame: bytes
    entry_bytes: tuple[int, ...] = ()
    count_source: str = COUNT_SOURCE_CALLER

    @property
    def pc_bytes(self) -> int:
        return len(self.pc)

    @property
    def frame_bytes(self) -> int:
        return len(self.frame)


def _require_anchor(player_xyz: Any) -> tuple[float, float, float]:
    if type(player_xyz) is not tuple or len(player_xyz) != 3:
        raise Bg0004CensusError("player XYZ must be an exact three-value tuple")
    import math
    checked = []
    for axis, value in zip("xyz", player_xyz):
        if type(value) not in (int, float) or type(value) is bool:
            raise Bg0004CensusError(
                "player %s must be a finite float32 value" % axis)
        result = float(value)
        if not math.isfinite(result) or abs(result) > 3.4028234663852886e38:
            raise Bg0004CensusError(
                "player %s must be a finite float32 value" % axis)
        checked.append(result)
    return (checked[0], checked[1], checked[2])


def _require_actor_count(actor_count: Any) -> int:
    if type(actor_count) is not int or type(actor_count) is bool or not (
        1 <= actor_count <= ROSTER_COUNT
    ):
        raise Bg0004CensusError(
            "actor count must be an integer in [1,%d]" % ROSTER_COUNT)
    return actor_count


def census_order(
    player_xyz: tuple[float, float, float],
) -> tuple[identity.Bg0004Placement, ...]:
    """The 84 shippable placements, nearest the anchor first.

    Nearest-first is the same order the other three censuses use.
    ``shippable_placements`` has already dropped the 32 with no identity;
    this only orders what it returned.
    """
    x, y, z = _require_anchor(player_xyz)
    ordered = sorted(
        identity.shippable_placements(),
        key=lambda p: (
            (p.x - x) ** 2 + (p.y - y) ** 2 + (p.z - z) ** 2,
            p.placement_index,
        ),
    )
    return tuple(ordered)


def _entry(legacy: Any, placement: identity.Bg0004Placement) -> bytes:
    """One actor entry: the same frozen shape the other three censuses build.

    The first ``make_npc_attr`` parameter is the real ``MOBS.n_ID`` from the
    CLINE crosswalk, never the Mob-Set number, matching bg0001's and
    bg0015's identity modules.

    HEADING.  This scene's placement rows carry no heading column either
    (same shape ``world_population_bg0002``'s ``_entry`` measured), so this
    reuses ``world_population.HEADINGS`` on the placement index exactly as
    the other three scenes do.
    """
    npc_attr = legacy.make_npc_attr(
        placement.n_id,
        placement.actor_identity,
        SCENE_N_ID,
        SCENE_SEQUENCE,
        placement.visual_preset,
        current_hp=placement.max_hp,
        max_hp=placement.max_hp,
        basic_name=placement.display_name,
    )
    movement_attr = legacy.make_remote_movement_attr(
        placement.actor_identity,
        placement.x, placement.y, placement.z,
        world_population.HEADINGS[placement.placement_index & 3],
        mask=FULL_MOVEMENT_MASK,
    )
    return legacy.make_remote_actor_entry(
        NPC_STYLE_ACTOR_TYPE,
        placement.actor_identity,
        [(NPC_ATTR_ID, npc_attr), (MOVEMENT_ATTR_ID, movement_attr)],
    )


def build_bg0004_population(
    legacy: Any,
    player_xyz: tuple[float, float, float],
    actor_count: int = DEFAULT_ACTOR_COUNT,
    *,
    scene_id: int,
    count_source: str = COUNT_SOURCE_CALLER,
) -> Bg0004PopulationGeneration:
    """Build the Bg0004 roster as ONE RuntimeRes collection.  Sends nothing.

    ``scene_id`` has no default on purpose, the same reason the other three
    builders give: every actor in this table is encoded with scene 4, and a
    caller that forgets which scene it is in would deliver slave-market
    NPCs into the wrong map.  Refuses anywhere but scene 4.
    """
    if type(scene_id) is not int or scene_id != SCENE_N_ID:
        raise Bg0004CensusError(
            "the Bg0004 roster is only valid in scene %d, not scene %r"
            % (SCENE_N_ID, scene_id))
    if count_source not in COUNT_SOURCES:
        raise Bg0004CensusError("unknown count source %r" % count_source)
    count = _require_actor_count(actor_count)
    if count_source == COUNT_SOURCE_FULL_ROSTER and count != ROSTER_COUNT:
        raise Bg0004CensusError(
            "count source %r claims the whole roster but the count is %d, "
            "not %d" % (count_source, count, ROSTER_COUNT))
    ordered = census_order(player_xyz)[:count]
    entries = [_entry(legacy, placement) for placement in ordered]
    for position, entry in enumerate(entries):
        if type(entry) is not bytes or not entry:
            raise Bg0004CensusError(
                "placement %d (n_id %d) encoded to an empty actor entry"
                % (ordered[position].placement_index, ordered[position].n_id))
    pc, frame = legacy.make_runtime_remote_actors(entries)
    return Bg0004PopulationGeneration(
        count,
        tuple(p.placement_index for p in ordered),
        tuple(p.actor_identity for p in ordered),
        tuple(p.n_id for p in ordered),
        tuple(p.display_name for p in ordered),
        _require_anchor(player_xyz),
        pc,
        frame,
        tuple(len(entry) for entry in entries),
        count_source,
    )


def wire_actor_count(generation: Bg0004PopulationGeneration) -> int:
    """Read the collection count back out of the bytes that will be sent."""
    if type(generation) is not Bg0004PopulationGeneration:
        raise Bg0004CensusError(
            "wire actor count needs a Bg0004PopulationGeneration")
    pc = generation.pc
    if len(pc) < WIRE_HEADER_BYTES or pc[WIRE_COUNT_TAG_OFFSET] != COLLECTION_TAG:
        raise Bg0004CensusError(
            "built frame does not carry the expected collection header")
    return int.from_bytes(
        pc[WIRE_COUNT_TAG_OFFSET + 1:WIRE_COUNT_TAG_OFFSET + 3], "little")


def dispatch_report(generation: Bg0004PopulationGeneration) -> dict:
    """Count what assembled BEFORE it goes out, cross-checked against the
    bytes -- the same three numbers every census in this tree reports."""
    if type(generation) is not Bg0004PopulationGeneration:
        raise Bg0004CensusError(
            "dispatch report needs a Bg0004PopulationGeneration")
    assembled = len(generation.placement_indices)
    declared = wire_actor_count(generation)
    body_bytes = generation.pc_bytes - WIRE_HEADER_BYTES
    entry_bytes_total = sum(generation.entry_bytes)
    bodies_intact = (
        bool(generation.entry_bytes)
        and len(generation.entry_bytes) == assembled
        and body_bytes == entry_bytes_total
        and all(generation.entry_bytes)
    )
    shortfall_reason = None
    if assembled != ROSTER_COUNT:
        shortfall_reason = "%s=%d" % (generation.count_source, assembled)
    elif assembled != PLACEMENT_COUNT:
        shortfall_reason = "identity_unresolved=%d" % UNRESOLVED_COUNT
    return {
        "assembled_count": assembled,
        "wire_actor_count": declared,
        "roster_count": ROSTER_COUNT,
        "placement_count": PLACEMENT_COUNT,
        "unresolved_count": UNRESOLVED_COUNT,
        "count_source": generation.count_source,
        "shortfall_reason": shortfall_reason,
        "counts_agree": declared == assembled,
        "bodies_intact": bodies_intact,
        "body_bytes": body_bytes,
        "entry_bytes_total": entry_bytes_total,
        "pc_bytes": generation.pc_bytes,
        "frame_bytes": generation.frame_bytes,
        "anchor": list(generation.anchor),
        "initial_reapply_ms": INITIAL_REAPPLY_MS,
    }


def census_console_line(generation: Bg0004PopulationGeneration) -> str:
    """The one grep-able ``WORLD_CENSUS`` line a boot in this scene prints.

    ``assembled=N/116`` against the scene's REAL placement count, not
    against the 84 that happen to resolve.  ASCII only (bridge console is
    cp874).
    """
    report = dispatch_report(generation)
    return (
        "WORLD_CENSUS_BG0004 assembled={0}/{1} shippable={2} wire={3} "
        "bodies={4} pc={5}B frame={6}B anchor=({7:.3f},{8:.3f},{9:.3f}) "
        "reapply_ms={10} source={11} shortfall={12} unresolved={13}".format(
            report["assembled_count"], report["placement_count"],
            report["roster_count"],
            report["wire_actor_count"] if report["counts_agree"]
            else "MISMATCH:%d" % report["wire_actor_count"],
            "ok" if report["bodies_intact"] else "SHORT",
            report["pc_bytes"], report["frame_bytes"],
            report["anchor"][0], report["anchor"][1], report["anchor"][2],
            report["initial_reapply_ms"], report["count_source"],
            report["shortfall_reason"] or "none",
            report["unresolved_count"],
        )
    )


def actor_lines(generation: Bg0004PopulationGeneration) -> tuple[str, ...]:
    """One ASCII line per actor: ``n_ID name level @x,y,z``."""
    if type(generation) is not Bg0004PopulationGeneration:
        raise Bg0004CensusError("actor lines need a Bg0004PopulationGeneration")
    placements = {p.placement_index: p
                  for p in identity.shippable_placements()}
    lines = []
    for index in generation.placement_indices:
        placement = placements[index]
        lines.append(
            "n_ID=%d %s lv%d hp%d @(%.3f,%.3f,%.3f)"
            % (placement.n_id, placement.display_name,
               placement.identity.level, placement.max_hp,
               placement.x, placement.y, placement.z))
    return tuple(lines)


def unresolved_lines() -> tuple[str, ...]:
    """One ASCII line per DROPPED placement, with the reason."""
    return tuple(
        "BG0004_UNSHIPPED placement=%d set=%d cline_row=%d leader_n_id=%d "
        "reason=%s"
        % (row["placement_index"], row["mobset_key"], row["cline_row_id"],
           row["leader_n_id"], row["reason"].replace(" ", "_"))
        for row in identity.unshippable_placements()
    )


def census_console_lines(
    legacy: Any, player_xyz: tuple[float, float, float]
) -> tuple[str, ...]:
    """``WORLD_CENSUS_BG0004`` + one line per actor + one per dropped one.

    Built from ONE generation, never composing the roster twice.
    """
    generation = build_bg0004_population(
        legacy, player_xyz, scene_id=SCENE_N_ID,
        count_source=COUNT_SOURCE_FULL_ROSTER,
    )
    return (
        (census_console_line(generation),)
        + actor_lines(generation)
        + unresolved_lines()
    )
