"""The Pale Silver Sea's cast as ONE census collection - LANE-A, scene 305.

The census half of round ``9zj630``'s pair; ``world_bg3008_identity`` is the
identity half and holds every table row this file sends.  ALL 59 of the
scene's 59 native placements, COUNTED BY PLACEMENT AND NOT BY NAME:

    16 hulls (``SP_*``) with a name plate: 9 Merchant Ship, 3 of the mined
       "Merchant marine" row, and one each of Viking Princess, Santa Maria,
       Skull Phantom and Utopia
    13 level-120 Pirate Ships, the biggest HP numbers this scene sends
    25 invisible weather markers: 19 named ``Tornado`` and 6 placements of
       the two nameless INVISIBLE sets (56, and 57 as the first leg of the
       ``57|58`` pair)
     5 islands-as-actors (``MAP_ISLAND_01``): Ice Island, Turtle Island,
       Dragon Turtle Island, Guawa Island, Snow Island

the cast of an ``n_SCENE_TYPE 8`` OCEAN PANEL, the same scene shape scenes
126 and 304 have, rather than of a town.  NOTHING is dropped here:
``world_bg3008_identity.UNRESOLVED`` is empty, so ``unresolved_lines()``
returns no lines and the console line's ``unresolved=`` reads 0.  That is
this scene's own measured answer, not an unfinished table - the sibling's 16
drops were four CLINE leaders with no ``CONSTDATA_TH__MOBS.tsv`` row, and
this scene's placements never key those sets.

THE SIBLING PATTERN, NOT A FORK.  ``world_population`` builds bg0001's
census and refuses anywhere but scene 1; ``world_population_bg3007`` is the
same shape for scene 304 and is the module this one is copied from, line for
line, with this scene's own numbers.  It refuses anywhere but scene 305.
Every wire call below is the exact frozen serializer the siblings already
use (``legacy.make_npc_attr`` via ``world_census_level`` /
``make_remote_movement_attr`` / ``make_remote_actor_entry`` /
``make_runtime_remote_actors``), and the wire header constants and the
accepted initial+reapply schedule are IMPORTED from ``world_population``
rather than redefined - they describe the wire format, which is not
scene-specific.

WHAT A PLAYER WILL SEE BECAUSE OF THIS FILE, STATED AS NARROWLY AS IT IS
TRUE.  A GM who types ``/warp 305`` today lands in an empty ocean: the scene
has an arrival point (``#843``), an admission arm that already names it
(``lane_a_scene_census.ARM_THREE_ELIGIBLE_SCENE_IDS``, round ``dyi95m``) and
no cast at all.  With this file and its registration in
``world_scene_travel.CENSUS_SOURCES`` / ``lane_hooks/lane_a_scene_census.py``,
the arrival path composes these 59 actors for that session on its first
TargetPosVital.  It is still GM-only - ``accounts.is_gm_account`` gates
``/warp``, ``login_entry_allowed`` for this scene stays ``false``, and this
file opens no door of its own.  NOBODY HAS SEEN IT: no client has ever
received a byte of this scene, and the ticket this round files is what turns
that sentence into a measurement.

WHAT IS DIFFERENT FROM THE SIBLING SCENES, NAMED RATHER THAN LEFT IMPLICIT.
All of these are measured in the identity module's own docstring and are
repeated here only as a pointer:

* THE DOOR IS SHUT AND STAYS SHUT.  ``login_entry_allowed`` for scene 305 is
  ``false`` and this round does not flip it.
* NO FACTION FRAME.  ``n_SAVE`` is 0, so ``world_faction_admission`` refuses
  this scene by its own published rule; nothing here widens that.
* TWO SETS SHIP ``INVISIBLE`` BODIES WITH NO NAME AT ALL (56 and 57), under
  the precedent ``world_bg0004_identity`` set 107 and scene 126's own set 53
  already ship under.
* 780 EXTRA SPAWN POINTS in the placement file are NOT shipped; this
  composer sends one actor per primary placement point, the number the
  registry's ``native_placement_count`` cites.
* HP is real and comes from the table chain, not composed:
  ``STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX``, sent as current == max
  (alive), matching every other composer's "no half-dead spawn" convention.
* There is no faction bit on any entry here, same as every sibling and for
  the same reason: whether any of this scene's placements should be hostile
  is a LANE-B decision, deliberately not made here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import world_bg3008_identity as identity
from . import world_census_level
from . import world_population
from .population import (
    FULL_MOVEMENT_MASK,
    MOVEMENT_ATTR_ID,
    NPC_ATTR_ID,
    NPC_STYLE_ACTOR_TYPE,
)


# Convention marker: matching the ten sibling composer modules' own
# convention.
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

COUNT_SOURCE_FULL_ROSTER = "bg3008_full_roster"
COUNT_SOURCE_CALLER = "caller_requested"
COUNT_SOURCES = (COUNT_SOURCE_FULL_ROSTER, COUNT_SOURCE_CALLER)


class Bg3008CensusError(ValueError):
    """A refusal from this module, always with a reason in the message."""


@dataclass(frozen=True)
class Bg3008PopulationGeneration:
    """One built Bg3008 collection: its membership, its bytes, nothing sent."""

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
        raise Bg3008CensusError("player XYZ must be an exact three-value tuple")
    import math
    checked = []
    for axis, value in zip("xyz", player_xyz):
        if type(value) not in (int, float) or type(value) is bool:
            raise Bg3008CensusError(
                "player %s must be a finite float32 value" % axis)
        result = float(value)
        if not math.isfinite(result) or abs(result) > 3.4028234663852886e38:
            raise Bg3008CensusError(
                "player %s must be a finite float32 value" % axis)
        checked.append(result)
    return (checked[0], checked[1], checked[2])


def _require_actor_count(actor_count: Any) -> int:
    if type(actor_count) is not int or type(actor_count) is bool or not (
        1 <= actor_count <= ROSTER_COUNT
    ):
        raise Bg3008CensusError(
            "actor count must be an integer in [1,%d]" % ROSTER_COUNT)
    return actor_count


def census_order(
    player_xyz: tuple[float, float, float],
) -> tuple[identity.Bg3008Placement, ...]:
    """All 59 placements, nearest the anchor first.

    Nearest-first is the same order every other composer uses, and it is
    what makes a truncated count (a caller asking for fewer than the whole
    roster) show the player the actors around them rather than an arbitrary
    slice of the ocean.  ``shippable_placements`` drops the placements with
    no identity - NONE in this scene, unlike the sibling's 16 - and this
    only orders what it returned.
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


def _entry(legacy: Any, placement: identity.Bg3008Placement) -> bytes:
    """One actor entry: the same frozen shape every other census builds.

    The first ``make_npc_attr`` parameter is the serializer's own
    "MOBS/template u16 at +0x78", and what goes into it is the REAL
    ``MOBS.n_ID`` from the CLINE crosswalk - never the Mob-Set number, which
    is the exact mistake ``GT-078`` put on the owner's screen for bg0001.

    HEADING.  Measured on THIS scene's file (the numbers are in
    ``world_bg3008_identity``'s own HEADING paragraph -- 59 rows, f32_3 flat
    zero, f32_4/f32_5 round thousands): no heading column here either, so
    this reuses ``world_population.HEADINGS`` on the placement index exactly
    as every other scene does.  Which heading each actor gets is pinned in
    the BYTES by ``tests/test_world_population_bg3008.py`` -- shifting the
    table index by one used to leave the whole suite green on the sibling
    scene this file copies.
    """
    # LEVEL (round `7ste68`).  The frozen ``make_npc_attr`` never set
    # BasicAttr bit 0x0002, so every actor this scene sent drew the client's
    # own default and ``GT-192`` read ``LV 1`` off the owner's screen for all
    # of them.  ``world_census_level`` splices in this row's own mined
    # ``MOBS.n_LEVEL_MIN`` at the one position the ascending mask order puts
    # it (``RE-117``: bit 0x0002, u16 tag 0x12, object +0x5E) -- the same
    # splice this project's hostile-monster encoder has shipped since that RE
    # landed (``world_census_level``'s own docstring names that file and its
    # lines; this comment deliberately does not, so the census path does not
    # register as an importer of lane B's combat module), and it REFUSES
    # rather than guesses if the frozen body's layout ever moves.
    npc_attr = world_census_level.leveled_npc_attr(
        legacy,
        template_n_id=placement.n_id,
        actor_identity=placement.actor_identity,
        scene_id=SCENE_N_ID,
        scene_sequence=SCENE_SEQUENCE,
        visual_preset=placement.visual_preset,
        current_hp=placement.max_hp,
        max_hp=placement.max_hp,
        basic_name=placement.display_name,
        level=placement.identity.level,
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


def build_bg3008_population(
    legacy: Any,
    player_xyz: tuple[float, float, float],
    actor_count: int = DEFAULT_ACTOR_COUNT,
    *,
    scene_id: int,
    count_source: str = COUNT_SOURCE_CALLER,
) -> Bg3008PopulationGeneration:
    """Build the Bg3008 roster as ONE RuntimeRes collection.  Sends nothing.

    ``scene_id`` has no default on purpose, the same reason every other
    builder gives: every actor in this table is encoded with scene 305, and
    a caller that forgets which scene it is in would deliver the Pale Silver
    Sea's ships and tornadoes into a different map.  Refuses anywhere but
    scene 305.
    """
    if type(scene_id) is not int or scene_id != SCENE_N_ID:
        raise Bg3008CensusError(
            "the Bg3008 roster is only valid in scene %d, not scene %r"
            % (SCENE_N_ID, scene_id))
    if count_source not in COUNT_SOURCES:
        raise Bg3008CensusError("unknown count source %r" % count_source)
    count = _require_actor_count(actor_count)
    # Same guard every sibling composer carries (pf-adversary, round
    # w0pu2i): without it a caller can build a truncated census, label it
    # "full roster", and the console line would print an unexplained
    # shortfall.
    if count_source == COUNT_SOURCE_FULL_ROSTER and count != ROSTER_COUNT:
        raise Bg3008CensusError(
            "count source %r claims the whole roster but the count is %d, "
            "not %d" % (count_source, count, ROSTER_COUNT))
    ordered = census_order(player_xyz)[:count]
    entries = [_entry(legacy, placement) for placement in ordered]
    for position, entry in enumerate(entries):
        if type(entry) is not bytes or not entry:
            raise Bg3008CensusError(
                "placement %d (n_id %d) encoded to an empty actor entry"
                % (ordered[position].placement_index, ordered[position].n_id))
    pc, frame = legacy.make_runtime_remote_actors(entries)
    return Bg3008PopulationGeneration(
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


def wire_actor_count(generation: Bg3008PopulationGeneration) -> int:
    """Read the collection count back out of the bytes that will be sent."""
    if type(generation) is not Bg3008PopulationGeneration:
        raise Bg3008CensusError(
            "wire actor count needs a Bg3008PopulationGeneration")
    pc = generation.pc
    if len(pc) < WIRE_HEADER_BYTES or pc[WIRE_COUNT_TAG_OFFSET] != COLLECTION_TAG:
        raise Bg3008CensusError(
            "built frame does not carry the expected collection header")
    return int.from_bytes(
        pc[WIRE_COUNT_TAG_OFFSET + 1:WIRE_COUNT_TAG_OFFSET + 3], "little")


def dispatch_report(generation: Bg3008PopulationGeneration) -> dict:
    """Count what assembled BEFORE it goes out, cross-checked against the bytes.

    The same three numbers every other census reports: what was assembled,
    what the wire header says, and whether the body bytes really total that
    many entries.
    """
    if type(generation) is not Bg3008PopulationGeneration:
        raise Bg3008CensusError(
            "dispatch report needs a Bg3008PopulationGeneration")
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


def census_console_line(generation: Bg3008PopulationGeneration) -> str:
    """The one grep-able ``WORLD_CENSUS_BG3008`` line a boot in this scene
    prints.  ``assembled=N/59`` against the scene's REAL placement count,
    which for this scene is also the number that resolves.  ASCII only (the
    bridge console is cp874); no name appears on THIS line at all, see
    ``actor_lines`` for the layer that does print one.
    """
    report = dispatch_report(generation)
    return (
        "WORLD_CENSUS_BG3008 assembled={0}/{1} shippable={2} wire={3} "
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


def actor_lines(generation: Bg3008PopulationGeneration) -> tuple[str, ...]:
    """One ASCII line per actor: ``placement=N n_ID=N name lv%d hp%d @x,y,z``.

    The headless half of the two-layer evidence rule: a grader can read who
    this census says is standing where, without a client.

    THE LINE GOES THROUGH ``identity.evidence_name`` even though every name
    this scene ships is ASCII.  ``COO-DECISION 20260902_2146`` shape 1 split
    the shipped column from the evidence layer, and routing through that
    function is what keeps the split true the day a regeneration brings a
    non-ASCII name into this table: it would print as
    ``name_cp874_hex=<hex>`` rather than as bytes a cp874 console cannot
    show.  ``placement=<n>`` leads every line - the decision's own pairing
    requirement - so a tester reading a hex token can still say which row of
    the scene's 59 it means.
    """
    if type(generation) is not Bg3008PopulationGeneration:
        raise Bg3008CensusError("actor lines need a Bg3008PopulationGeneration")
    placements = {p.placement_index: p
                  for p in identity.shippable_placements()}
    lines = []
    for index in generation.placement_indices:
        placement = placements[index]
        lines.append(
            "placement=%d n_ID=%d %s lv%d hp%d @(%.3f,%.3f,%.3f)"
            % (placement.placement_index, placement.n_id,
               identity.evidence_name(placement.identity),
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
        "BG3008_UNSHIPPED placement=%d set=%d cline_row=%d leader_n_id=%d "
        "reason=%s"
        % (row["placement_index"], row["template_id"], row["cline_row_id"],
           row["leader_n_id"], row["reason"].replace(" ", "_"))
        for row in identity.unshippable_placements()
    )


def census_console_lines(
    legacy: Any, player_xyz: tuple[float, float, float]
) -> tuple[str, ...]:
    """``WORLD_CENSUS_BG3008`` + one line per actor + one per dropped one.

    Everything a headless proof for this scene needs, in one call, built from
    ONE generation.
    """
    generation = build_bg3008_population(
        legacy, player_xyz, scene_id=SCENE_N_ID,
        count_source=COUNT_SOURCE_FULL_ROSTER,
    )
    return (
        (census_console_line(generation),)
        + actor_lines(generation)
        + unresolved_lines()
    )
