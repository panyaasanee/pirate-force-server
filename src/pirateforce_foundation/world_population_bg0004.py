"""Bg0004 (Slave Market Island) census composer - LANE-A.

``COO-DECISION 2026-08-30T14:41+07:00`` approved this lane's own
recommendation to build scene 4's CLINE->MOBS crosswalk next, of the ten
still-shut doors surveyed in round ``12lyda``.  This is the census half; the
identity half is ``world_bg0004_identity``.

THE SIBLING PATTERN, NOT A FORK.  ``world_population`` builds bg0001's
census and refuses anywhere but scene 1; ``world_population_bg0002`` and
``world_population_bg0015`` are the same shape for scenes 2 and 14.  This is
the fourth: it refuses anywhere but scene 4, over
``world_bg0004_identity``'s 109 shippable placements of 116.  Every wire call
below is the exact frozen serializer the other three already use
(``legacy.make_npc_attr`` / ``make_remote_movement_attr`` /
``make_remote_actor_entry`` / ``make_runtime_remote_actors``), and the wire
header constants and the accepted initial+reapply schedule are IMPORTED from
``world_population`` rather than redefined - they describe the wire format,
which is not scene-specific.

WHAT IS DIFFERENT FROM THE OTHER THREE, NAMED RATHER THAN LEFT IMPLICIT.

* Unlike Bg0002 (every placement named) and like Bg0001/Bg0015, this scene
  has ONE placement family that ships with an EMPTY name: Mob-Set 107
  (leader 917, outfit ``INVISIBLE``), which alone accounts for 25 of the 109
  shippable placements - see ``world_bg0004_identity``'s own docstring for
  why that is the same shape Port Royal already ships (leader 917 there
  too, at its own Mob-Set 98/103) rather than a new refusal rule.
* HP is real and comes from the table chain, not composed:
  ``STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX``, sent as current == max
  (alive), matching every other composer's "no half-dead spawn" convention.
* There is no faction bit on any entry here.  Whether any of this scene's
  monster-shaped placements (Scythe Beetle, Dragon Gladiator, Orc Chief and
  so on - the level 46-58 sets that carry a nonzero MOBS.n_RANK) should be
  hostile is a LANE-B decision (the same split PANYA-DECISION 2026-08-27
  20:10 drew for Bg0002's "widen the hostile faction pair" item), deliberately
  not made here - a wrong identity a player can walk up to and read is
  recoverable, a wrong identity that attacks on sight is not.
* NOT WIRED.  This module is not registered in
  ``world_scene_travel.CENSUS_SOURCES`` or
  ``world_population_handoff.ROSTER_COMPOSERS`` this round, and scene 4's
  ``login_entry_allowed`` stays ``false`` (COO-DECISION 2026-08-30T14:41's own
  instruction: do not open the door until the population component is ready).
  A player sees exactly what they saw yesterday because of this file.  Wiring
  it is the same two-table change ``world_population_bg0015`` needed
  (``lane_hooks/lane_a_scene_census.py`` round ga91m5-r2 did the wiring for
  scene 14, several rounds after that module first shipped) - left for a
  later round of this same multi-round order, deliberately, so this round's
  diff is the identity+census pair alone and can be verified on its own.
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
# imports this module yet.  See the module docstring's "NOT WIRED" paragraph
# before reading this as "live today".
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
    """The 109 shippable placements, nearest the anchor first.

    Nearest-first is the same order every other composer uses, and it is
    what makes a truncated count (a caller asking for fewer than the whole
    roster) show the player the actors around them rather than an arbitrary
    slice of the island.  ``shippable_placements`` has already dropped the
    seven with no identity; this only orders what it returned.
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
    """One actor entry: the same frozen shape every other census builds.

    The first ``make_npc_attr`` parameter is the serializer's own
    "MOBS/template u16 at +0x78", and what goes into it is the REAL
    ``MOBS.n_ID`` from the CLINE crosswalk - never the Mob-Set number, which
    is the exact mistake ``GT-078`` put on the owner's screen for bg0001.

    HEADING.  This scene's placement rows carry no heading column either
    (measured the same way ``world_population_bg0002``'s ``_entry`` measured
    it for its own scene: the extra f32 triple this TSV format carries is a
    round-number 0-6000 range repeated across unrelated rows, the shape of a
    radius/range, not a rotation), so this reuses ``world_population.
    HEADINGS`` on the placement index exactly as every other scene does
    rather than inventing a second heading policy.
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

    ``scene_id`` has no default on purpose, the same reason every other
    builder gives: every actor in this table is encoded with scene 4, and a
    caller that forgets which scene it is in would deliver slave-market NPCs
    into a different map.  Refuses anywhere but scene 4.
    """
    if type(scene_id) is not int or scene_id != SCENE_N_ID:
        raise Bg0004CensusError(
            "the Bg0004 roster is only valid in scene %d, not scene %r"
            % (SCENE_N_ID, scene_id))
    if count_source not in COUNT_SOURCES:
        raise Bg0004CensusError("unknown count source %r" % count_source)
    count = _require_actor_count(actor_count)
    # Same guard bg0015's composer carries (pf-adversary, round w0pu2i):
    # without it a caller can build a 5-actor census, label it "full roster",
    # and the console line would print an unexplained shortfall.
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
    """Count what assembled BEFORE it goes out, cross-checked against the bytes.

    The same three numbers every other census reports: what was assembled,
    what the wire header says, and whether the body bytes really total that
    many entries.
    """
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
    """The one grep-able ``WORLD_CENSUS_BG0004`` line a boot in this scene
    prints.  ``assembled=N/116`` against the scene's REAL placement count,
    not against the 109 that happen to resolve.  ASCII only (bridge console
    is cp874).
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
    """One ASCII line per actor: ``n_ID name lv%d hp%d @x,y,z``.

    The headless half of the two-layer evidence rule: a grader can read who
    this census says is standing where, without a client.  Every name in the
    shipped table is ASCII by ``world_bg0004_identity._self_check`` (empty
    for set 107's INVISIBLE marker, which prints as an empty name rather than
    a fabricated one).
    """
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
    """One ASCII line per DROPPED placement, with the reason.

    CHARTER-02's rule in executable form: a shortfall is reported with the
    real number and the real reason, in the same console output as the
    census, rather than left for someone to notice as a missing actor.
    """
    return tuple(
        "BG0004_UNSHIPPED placement=%d set=%d cline_row=%d leader_n_id=%d "
        "reason=%s"
        % (row["placement_index"], row["template_id"], row["cline_row_id"],
           row["leader_n_id"], row["reason"].replace(" ", "_"))
        for row in identity.unshippable_placements()
    )


def census_console_lines(
    legacy: Any, player_xyz: tuple[float, float, float]
) -> tuple[str, ...]:
    """``WORLD_CENSUS_BG0004`` + one line per actor + one per dropped one.

    Everything a headless proof for this scene needs, in one call, built from
    ONE generation.  Deliberately does NOT print a ``WORLD_SCENE`` line the
    way ``world_population_bg0002``'s helper does: this scene's registry
    entry already has a pinned ``spawn`` (the CLIENT_MARKER_TABLE point), so
    a caller that wants that line can get it from
    ``world_scene_travel.entry_console_line`` directly - reproducing it here
    would print scene-registry evidence a second way for no reason this
    module owns.
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
