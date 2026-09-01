"""Bg0004 (Slave Market Island) census composer - LANE-A door-priority build.

COO-DECISION 2026-08-30T14:41 approved building this scene's composer next,
the same CLINE->MOBS crosswalk BUILD-001 (bg0001) used, per LANE-A's own
`R236` gate-scope recommendation. ``world_population.py`` builds bg0001's
census and refuses anywhere but scene 1; ``world_population_bg0002.py`` is
the sibling that refuses anywhere but scene 2.  This is the SAME shape again,
refusing anywhere but scene 4, over ``scene4_slave_market_tables.py``'s 84
resolved placements.

ENCODER REUSE, NOT A NEW PATH.  Every wire call below is the exact same
frozen serializer ``world_population._entry`` already uses
(``legacy.make_npc_attr`` / ``legacy.make_remote_movement_attr`` /
``legacy.make_remote_actor_entry`` / ``legacy.make_runtime_remote_actors``),
and the wire-header constants and the proven initial+reapply schedule are
IMPORTED from ``world_population``, not redefined - exactly the reuse
``world_population_bg0002.py`` already established as this tree's pattern
for a second scene, now a third.

WHAT IS DIFFERENT FROM BG0002's CENSUS.  This scene's placements resolve
through the CLINE crosswalk (RE-128), not a direct Mob-Set-number-equals-
MOBS-n_ID join - see ``scene4_slave_market_tables.py``'s own docstring for
the full mechanism and its two open caveats (2 name/template_ids
disagreements resolved in template_ids' favor; 32 of 116 placements
UNRESOLVED, mostly the reused "Training Iron Man" n_id 917 also seen in
bg0001 and, separately, 6 pathfinding-helper markers with no player name).

WHY THIS DOOR STAYS SHUT (login_entry_allowed unchanged this round).  The
same COO letter that approved this build explicitly said not to flip scene
4's login door until the composer is genuinely ready - opening it today
would put a player in an empty scene, since nothing calls this module yet.
``production_allowed = True`` is this tree's usual convention marker only:
nothing branches on it and nothing imports this module from ``runtime.py``
(the chief's file) yet.  Until that wiring exists AND a queue ticket
confirms these identities client-side (the way ``GT-131`` did for bg0001),
a player walking into Slave Market Island sees exactly what they saw
yesterday - nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import scene4_slave_market_tables as tables
from . import world_population
from .population import (
    FULL_MOVEMENT_MASK,
    MOVEMENT_ATTR_ID,
    NPC_ATTR_ID,
    NPC_STYLE_ACTOR_TYPE,
)


# Convention marker only, per this tree's own rule: nothing branches on it
# and nothing imports this module yet.  Until runtime.py - the chief's file,
# not this lane's - calls into it, the player sees exactly what they saw
# yesterday.
production_allowed = True
test_only = False

SCENE4_N_ID = tables.SCENE_N_ID
SCENE4_SEQUENCE = 0
DEFAULT_ACTOR_COUNT = tables.KNOWN_COUNT

# Carried, not redefined, from world_population -- see module docstring.
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
            raise Bg0004CensusError("player %s must be a finite float32 value" % axis)
        result = float(value)
        if not math.isfinite(result) or abs(result) > 3.4028234663852886e38:
            raise Bg0004CensusError("player %s must be a finite float32 value" % axis)
        checked.append(result)
    return (checked[0], checked[1], checked[2])


def _require_actor_count(actor_count: Any) -> int:
    if type(actor_count) is not int or type(actor_count) is bool or not (
        1 <= actor_count <= tables.KNOWN_COUNT
    ):
        raise Bg0004CensusError(
            "actor count must be an integer in [1,%d]" % tables.KNOWN_COUNT
        )
    return actor_count


def census_order(
    player_xyz: tuple[float, float, float],
) -> tuple[tables.Bg0004Placement, ...]:
    """The 84 resolved placements, nearest the anchor first.

    ``load_known_placements`` has already refused a shape or count drift, so
    this only orders what it returned; it does not re-validate the table.
    """
    placements = tables.load_known_placements()
    x, y, z = _require_anchor(player_xyz)
    ordered = sorted(
        placements,
        key=lambda p: (
            (p.x - x) ** 2 + (p.y - y) ** 2 + (p.z - z) ** 2,
            p.placement_index,
        ),
    )
    return tuple(ordered)


def _entry(legacy: Any, placement: tables.Bg0004Placement) -> bytes:
    """One actor entry: the same frozen shape ``world_population._entry`` uses.

    Every field comes from the mined/crosswalked table, never composed: HP
    is the STANDARD_MOB-derived ``max_hp`` (alive, current == max, matching
    ``world_population``'s "no half-dead spawn" convention), the name is the
    real MOBS_TIP display name, ambiguous outfits ship the first listed
    variant (same default ``world_port_royal_identity.py`` and
    ``scene2_prison_exile_tables.py`` both already use).

    HEADING.  The raw placement TSV (``gamedata/scene/bg0004/
    bg0004.placements.tsv``) has no per-row heading column - ``f32_3``/
    ``f32_4``/``f32_5`` were checked this round (measured directly, not
    guessed) and are round-number values forming a radius/range triple, the
    SAME shape bg0002's own placement file has, not a continuous rotation -
    so there is no mined heading to carry here.  This reuses
    ``world_population.HEADINGS`` via ``HEADINGS[placement.placement_index
    & 3]``, the same four-way cycle bg0001's and bg0002's own ``_entry``
    already send, so Bg0004 gains no second heading policy.  If a real
    per-placement heading is later RE'd from the client, replace this call,
    not the encoder.
    """
    npc_attr = legacy.make_npc_attr(
        placement.n_id,
        placement.actor_identity,
        SCENE4_N_ID,
        SCENE4_SEQUENCE,
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

    ``scene_id`` HAS NO DEFAULT ON PURPOSE, same reason as
    ``world_population.build_world_population``: this table encodes every
    actor with scene fixed at 4, and a caller that forgets which scene it is
    in would deliver Slave Market NPCs into the wrong map.  Refuses anywhere
    but scene 4.
    """
    if type(scene_id) is not int or scene_id != SCENE4_N_ID:
        raise Bg0004CensusError(
            "the Bg0004 roster is only valid in scene %d, not scene %r"
            % (SCENE4_N_ID, scene_id)
        )
    if count_source not in COUNT_SOURCES:
        raise Bg0004CensusError("unknown count source %r" % count_source)
    count = _require_actor_count(actor_count)
    ordered = census_order(player_xyz)[:count]
    entries = [_entry(legacy, placement) for placement in ordered]
    for position, entry in enumerate(entries):
        if type(entry) is not bytes or not entry:
            raise Bg0004CensusError(
                "placement %d (n_id %d) encoded to an empty actor entry"
                % (ordered[position].placement_index, ordered[position].n_id)
            )
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
        raise Bg0004CensusError("wire actor count needs a Bg0004PopulationGeneration")
    pc = generation.pc
    if len(pc) < WIRE_HEADER_BYTES or pc[WIRE_COUNT_TAG_OFFSET] != COLLECTION_TAG:
        raise Bg0004CensusError("built frame does not carry the expected collection header")
    return int.from_bytes(pc[WIRE_COUNT_TAG_OFFSET + 1:WIRE_COUNT_TAG_OFFSET + 3], "little")


def dispatch_report(generation: Bg0004PopulationGeneration) -> dict:
    """Count what assembled BEFORE it goes out, cross-checked against the bytes.

    Same three-number shape ``world_population.dispatch_report`` /
    ``world_population_bg0002.dispatch_report`` use: what was assembled,
    what the wire header says, and whether the body bytes really total that
    many entries.  Per CHARTER-02: never silently reduce a number the order
    specified - a shortfall always carries a reason.
    """
    if type(generation) is not Bg0004PopulationGeneration:
        raise Bg0004CensusError("dispatch report needs a Bg0004PopulationGeneration")
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
    if assembled != tables.KNOWN_COUNT:
        shortfall_reason = "%s=%d" % (generation.count_source, assembled)
    return {
        "assembled_count": assembled,
        "wire_actor_count": declared,
        "roster_count": tables.KNOWN_COUNT,
        "unresolved_count": tables.UNRESOLVED_COUNT,
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
    """The ``WORLD_CENSUS`` line, same shape
    ``world_population_bg0002.census_console_line`` prints for bg0002.  ASCII
    only.
    """
    report = dispatch_report(generation)
    return (
        "WORLD_CENSUS assembled={0}/{1} wire={2} bodies={3} pc={4}B frame={5}B "
        "anchor=({6:.3f},{7:.3f},{8:.3f}) reapply_ms={9} source={10} "
        "shortfall={11} unresolved={12}".format(
            report["assembled_count"], report["roster_count"],
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
    """One ASCII line per actor: ``n_ID name title @x,y,z``, same headless-
    proof shape bg0002's own ``actor_lines`` prints.
    """
    if type(generation) is not Bg0004PopulationGeneration:
        raise Bg0004CensusError("actor lines need a Bg0004PopulationGeneration")
    placements = {p.placement_index: p for p in tables.load_known_placements()}
    lines = []
    for index in generation.placement_indices:
        placement = placements[index]
        title = (" (%s)" % placement.title) if placement.title else ""
        lines.append(
            "n_ID=%d %s%s @(%.3f,%.3f,%.3f)"
            % (placement.n_id, placement.display_name, title,
               placement.x, placement.y, placement.z)
        )
    return tuple(lines)


def scene_and_census_console_lines(
    legacy: Any, player_xyz: tuple[float, float, float]
) -> tuple[str, ...]:
    """``WORLD_SCENE`` + ``WORLD_CENSUS`` + one line per actor, in that order.

    This is the headless-proof-before-owner-look output this lane's own
    convention asks for (PANYA-DECISION 2026-08-27 20:10, applied to bg0002
    and reused here) so a queue ticket has real console output to check
    before anyone is asked to look at a screen.  ``WORLD_SCENE`` reuses
    ``world_scene_travel.entry_console_line`` - not this module's own work.
    """
    from . import world_scene_travel
    destination = world_scene_travel.destination(SCENE4_N_ID)
    scene_line = world_scene_travel.entry_console_line(destination)
    generation = build_bg0004_population(
        legacy, player_xyz, scene_id=SCENE4_N_ID,
        count_source=COUNT_SOURCE_FULL_ROSTER,
    )
    return (scene_line, census_console_line(generation)) + actor_lines(generation)
