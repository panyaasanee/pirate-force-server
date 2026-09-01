"""Bg0002 (Prison Exile Island) census composer - LANE-A M1-P.

PANYA-DECISION 2026-08-27 20:10 (+07:00) pauses M2 and makes M1 "true
identity spawns" priority one, starting at Prison Exile Island rather than
Port Royal.  ``world_population.py`` builds bg0001's census and, on purpose,
refuses anywhere but scene 1 (``build_world_population``'s ``scene_id``
check) - it is not this module's job to loosen that refusal, and this module
does not import or alter it.  This is the SIBLING that refuses anywhere but
scene 2, over ``scene2_prison_exile_tables.py``'s 97 resolved placements
instead of bg0001's 115.

ENCODER REUSE, NOT A NEW PATH.  Every wire call below is the exact same
frozen serializer ``world_population._entry`` already uses
(``legacy.make_npc_attr`` / ``legacy.make_remote_movement_attr`` /
``legacy.make_remote_actor_entry`` / ``legacy.make_runtime_remote_actors``),
and the wire-header constants (``WIRE_HEADER_BYTES``, ``WIRE_COUNT_TAG_OFFSET``,
``COLLECTION_TAG``) and the proven initial+reapply schedule
(``INITIAL_REAPPLY_MS``) are IMPORTED from ``world_population``, not
redefined - they describe the wire format and the accepted schedule, neither
of which is bg0001-specific.

WHAT IS DIFFERENT FROM BG0001'S CENSUS, NAMED RATHER THAN LEFT IMPLICIT.
Every Bg0002 placement this module sends already carries a real name from
``MOBS_TIP`` (``scene2_prison_exile_tables.py`` refuses to load a row with an
empty ``display_name``), so every entry here is named - there is no
named/nameless split the way bg0001's P0/P30/P91 vs. the rest of the census
has.  There is also no faction/hostile bit on ANY entry here: PANYA-DECISION
2026-08-27 20:10 assigns "widen the hostile faction pair (1,6) to bg0002" to
LANE B (item 3 of that letter), explicitly separate from lane A's
"roster_bg0002" item (item 1) - M1-P's own pass criterion is identity and
position, not combat presentation.  A caller that wants monsters 27-35
hostile owes them the same override splice lane B's hostile-monster module and
``mob_death.py`` already use for bg0001, generalized to this scene - not
built here.

WHAT THIS MODULE DOES NOT CLAIM.  ``scene2_prison_exile_tables.py``'s own
docstring is the source of truth for how strong the "NN = MOBS.n_ID"
hypothesis is (2 of 7 owner-named anchors numerically confirmed, 2 more
supportive-not-tight, 3 photographic and unchecked by this lane) - this
module ships the roster that hypothesis predicts because CHARTER-02 and the
M1-P order both call for building around a hole instead of stopping, not
because the hypothesis is settled.  ``census_console_line`` and
``actor_lines`` exist so the required headless-proof gate (PANYA-DECISION
2026-08-27 20:10: proof before the owner is called in to look at a screen)
has real console output to check first.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import scene2_prison_exile_tables as tables
from . import world_census_level
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

SCENE2_N_ID = tables.SCENE_N_ID
SCENE2_SEQUENCE = 0
DEFAULT_ACTOR_COUNT = tables.KNOWN_COUNT

# Carried, not redefined, from world_population -- see module docstring.
WIRE_HEADER_BYTES = world_population.WIRE_HEADER_BYTES
WIRE_COUNT_TAG_OFFSET = world_population.WIRE_COUNT_TAG_OFFSET
COLLECTION_TAG = world_population.COLLECTION_TAG
INITIAL_REAPPLY_MS = world_population.INITIAL_REAPPLY_MS

COUNT_SOURCE_FULL_ROSTER = "bg0002_full_roster"
COUNT_SOURCE_CALLER = "caller_requested"
COUNT_SOURCES = (COUNT_SOURCE_FULL_ROSTER, COUNT_SOURCE_CALLER)


class Bg0002CensusError(ValueError):
    """A refusal from this module, always with a reason in the message."""


@dataclass(frozen=True)
class Bg0002PopulationGeneration:
    """One built Bg0002 collection: its membership, its bytes, nothing sent."""

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
        raise Bg0002CensusError("player XYZ must be an exact three-value tuple")
    import math
    checked = []
    for axis, value in zip("xyz", player_xyz):
        if type(value) not in (int, float) or type(value) is bool:
            raise Bg0002CensusError("player %s must be a finite float32 value" % axis)
        result = float(value)
        if not math.isfinite(result) or abs(result) > 3.4028234663852886e38:
            raise Bg0002CensusError("player %s must be a finite float32 value" % axis)
        checked.append(result)
    return (checked[0], checked[1], checked[2])


def _require_actor_count(actor_count: Any) -> int:
    if type(actor_count) is not int or type(actor_count) is bool or not (
        1 <= actor_count <= tables.KNOWN_COUNT
    ):
        raise Bg0002CensusError(
            "actor count must be an integer in [1,%d]" % tables.KNOWN_COUNT
        )
    return actor_count


def census_order(
    player_xyz: tuple[float, float, float],
) -> tuple[tables.Bg0002Placement, ...]:
    """The 97 resolved placements, nearest the anchor first.

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


def _entry(legacy: Any, placement: tables.Bg0002Placement) -> bytes:
    """One actor entry: the same frozen shape ``world_population._entry`` uses.

    Every field comes from the mined table, never composed: HP is the
    STANDARD_MOB-derived ``max_hp`` (alive, current == max, matching
    ``world_population``'s "no half-dead spawn" convention), the name is the
    real MOBS_TIP display name, and there is no faction bit - see the module
    docstring.

    HEADING (M1-P2 item 2, PANYA-DECISION 2026-08-28 02:00 gap 2: "every
    actor faces the same direction").  The raw placement TSV
    (``gamedata/scene/Bg0002/Bg0002.placements.tsv``) has no per-row heading
    column - ``f32_3``/``f32_4``/``f32_5`` were checked this round (measured
    directly off all 106 rows, not guessed) and are round-number values in
    the 0-5500 range repeated across many unrelated placements, the shape of
    a radius/range triple, not a continuous rotation - so there is no mined
    heading to carry here, unlike x/y/z/name/hp above. Rather than invent one
    or leave every entry pointing the same way, this reuses
    ``world_population.HEADINGS`` - the exact same four-way cycle
    bg0001's own ``_entry`` already sends today via
    ``HEADINGS[placement.placement_index & 3]`` - so Bg0002 stops being a
    special case instead of gaining a second heading policy. If a real
    per-placement heading is later RE'd from the client, replace this call,
    not the encoder.
    """
    # LEVEL (round `7ste68`).  ``placement.level`` is this scene's own mined
    # ``MOBS.n_LEVEL_MIN`` -- the same column every sibling scene sends, and
    # the one RE-173 corrected for placement 63 -- NOT ``level_max``: a row
    # with a range is a range the original server rolls per spawn, and this
    # module has no evidence about that roll, so it sends the mined floor
    # rather than inventing the roll.
    npc_attr = world_census_level.leveled_npc_attr(
        legacy,
        template_n_id=placement.n_id,
        actor_identity=placement.actor_identity,
        scene_id=SCENE2_N_ID,
        scene_sequence=SCENE2_SEQUENCE,
        visual_preset=placement.visual_preset,
        current_hp=placement.max_hp,
        max_hp=placement.max_hp,
        basic_name=placement.display_name,
        level=placement.level,
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


def build_bg0002_population(
    legacy: Any,
    player_xyz: tuple[float, float, float],
    actor_count: int = DEFAULT_ACTOR_COUNT,
    *,
    scene_id: int,
    count_source: str = COUNT_SOURCE_CALLER,
) -> Bg0002PopulationGeneration:
    """Build the Bg0002 roster as ONE RuntimeRes collection.  Sends nothing.

    ``scene_id`` HAS NO DEFAULT ON PURPOSE, same reason as
    ``world_population.build_world_population``: this table encodes every
    actor with scene fixed at 2, and a caller that forgets which scene it is
    in would deliver Prison Exile NPCs into the wrong map.  Refuses anywhere
    but scene 2.
    """
    if type(scene_id) is not int or scene_id != SCENE2_N_ID:
        raise Bg0002CensusError(
            "the Bg0002 roster is only valid in scene %d, not scene %r"
            % (SCENE2_N_ID, scene_id)
        )
    if count_source not in COUNT_SOURCES:
        raise Bg0002CensusError("unknown count source %r" % count_source)
    count = _require_actor_count(actor_count)
    ordered = census_order(player_xyz)[:count]
    entries = [_entry(legacy, placement) for placement in ordered]
    for position, entry in enumerate(entries):
        if type(entry) is not bytes or not entry:
            raise Bg0002CensusError(
                "placement %d (n_id %d) encoded to an empty actor entry"
                % (ordered[position].placement_index, ordered[position].n_id)
            )
    pc, frame = legacy.make_runtime_remote_actors(entries)
    return Bg0002PopulationGeneration(
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


def wire_actor_count(generation: Bg0002PopulationGeneration) -> int:
    """Read the collection count back out of the bytes that will be sent."""
    if type(generation) is not Bg0002PopulationGeneration:
        raise Bg0002CensusError("wire actor count needs a Bg0002PopulationGeneration")
    pc = generation.pc
    if len(pc) < WIRE_HEADER_BYTES or pc[WIRE_COUNT_TAG_OFFSET] != COLLECTION_TAG:
        raise Bg0002CensusError("built frame does not carry the expected collection header")
    return int.from_bytes(pc[WIRE_COUNT_TAG_OFFSET + 1:WIRE_COUNT_TAG_OFFSET + 3], "little")


def dispatch_report(generation: Bg0002PopulationGeneration) -> dict:
    """Count what assembled BEFORE it goes out, cross-checked against the bytes.

    Same three-number shape ``world_population.dispatch_report`` uses (see
    that function's docstring for why all three matter): what was assembled,
    what the wire header says, and whether the body bytes really total that
    many entries.
    """
    if type(generation) is not Bg0002PopulationGeneration:
        raise Bg0002CensusError("dispatch report needs a Bg0002PopulationGeneration")
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


def census_console_line(generation: Bg0002PopulationGeneration) -> str:
    """The ``WORLD_CENSUS`` line PANYA-DECISION 2026-08-27 20:10's headless
    gate requires: ``assembled=N/N``, plus the same wire/body cross-check
    ``world_population.census_console_line`` prints for bg0001.  ASCII only.
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


def actor_lines(generation: Bg0002PopulationGeneration) -> tuple[str, ...]:
    """One ASCII line per actor: ``n_ID name title @x,y,z`` -- PANYA-DECISION
    2026-08-27 20:10's other headless-proof requirement.  Titles are ASCII in
    every row this table carries (checked by the loader's type rules), so no
    escaping beyond a plain format is needed; a future row with a non-ASCII
    title would need one, and this function does not silently invent that
    escaping today.
    """
    if type(generation) is not Bg0002PopulationGeneration:
        raise Bg0002CensusError("actor lines need a Bg0002PopulationGeneration")
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

    This is everything PANYA-DECISION 2026-08-27 20:10's headless-proof gate
    (item 4) asks a boot to print, assembled in one call for a caller (a
    future wiring round, or an attended test harness) that wants it in one
    shot.  Building the ``WORLD_SCENE`` line is NOT this module's own work --
    it reuses ``world_scene_travel.entry_console_line``, which already prints
    the correct line for scene 2 (``scenarios/world_scene_registry_001.json``
    already pins ``model_id=BG0002`` there) -- so this function only adds the
    two lines that module cannot produce.
    """
    from . import world_scene_travel
    destination = world_scene_travel.destination(SCENE2_N_ID)
    scene_line = world_scene_travel.entry_console_line(destination)
    generation = build_bg0002_population(
        legacy, player_xyz, scene_id=SCENE2_N_ID,
        count_source=COUNT_SOURCE_FULL_ROSTER,
    )
    return (scene_line, census_console_line(generation)) + actor_lines(generation)
