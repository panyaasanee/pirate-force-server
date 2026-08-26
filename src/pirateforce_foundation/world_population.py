"""Full bg0001 world census population - LANE-A build order BUILD-001.

WHAT THIS MODULE IS FOR.  The normal runtime path sends three actors out of the
115 decoded bg0001 placements on every boot, and has done so since the V112 ->
V129 -> V134 variable isolation became the permanent default.  This module
builds the SAME frame the same encoder already builds, from the SAME frozen
placement table, over the SAME serializers - the only thing it changes is HOW
MANY placements go into it.

WHAT IT DOES *NOT* DO, MEASURED BEFORE THIS MODULE WAS COMMITTED.  It does not
fill the area around the player.  The frozen table is not a town roster; it
spans roughly 39,000 units end to end, and it is thin almost everywhere::

    anchor              <500u   <1000u   <2000u   20th     60th    115th
    V134 (P0 minus100X)     1        1        2   12,998  26,696  39,394
    V135 (new spawn)        1        1        2   13,012  26,719  39,425
    V112 (dock probe)       2        2        3    9,224  19,509  37,063

    densest placement in the whole table: P67, with 8 neighbours within 1000u

So "send 115 and the city fills up" is FALSE, and this module must not be read
as claiming it.  What changes for the player is different and still worth
building: today three actors exist anywhere in bg0001 at all, so every part of
the map except one dock corner is provably empty; with the census every
placement the original data defines is present, so walking anywhere in bg0001
can put the player next to the NPCs that belong there.  Crowding a single view
is a different problem - it needs either a dense scene or spawns this table
does not contain - and it belongs to its own build order.

WHY IT IS NOT BEHIND A SCENARIO FLAG.  Every population capability in this tree
so far is opt-in and off by default (``--population-scenario``), which is why
the project owns dozens of scenarios and, before this file, no module that
declared itself shippable.  This module declares ``production_allowed = True``
and its default actor count is the entire census.

    That flag is a CONVENTION MARKER AND NOTHING ELSE.  No code in this tree
    branches on it, and nothing imports this module yet.  Until ``runtime.py``
    - which is the chief's file, not this lane's - calls into it, the player
    sees exactly what they saw yesterday.  Do not read the flag, or this
    module's existence, as evidence that population shipped.

THE MEASUREMENT THIS MODULE EXISTS TO MAKE POSSIBLE.  No document in either
repository records how many actors this client accepts in one RuntimeRes
collection.  The highest count with a RECORDED result is 20 (V94 authoritative
nearest-set).

Read that as "unrecorded", not as "never attempted".  The frozen source still
carries ``make_v62_port_royal_population_snapshot()`` (v141:1441), which emits
ALL 115 placements in one snapshot under the label
``V73_PORT_ROYAL_GOLDEN_POPULATION_115`` and whose own docstring calls V62 "the
golden runtime-state baseline".  Today that function has no caller in v141, no
test exercises it, and no surviving report in ``reports/`` or in either
repository's markdown says what the client did with it - the V62/V73 narrative
lives in ``handoff.txt`` and in commit ``5c200e2``, neither of which is
reachable from this clone.  So the census is delivered as a STAIRCASE of rungs::

    3 -> 20 -> 60 -> 115

AMENDMENT 2026-08-26 00:2x (+07:00) - THE STAIRCASE IS CANCELLED AS THE
SHIPPING PLAN.  The paragraph above stays because it is the reasoning that was
true when it was written, and this project does not delete its own history.
What changed is an owner ruling carried by CHARTER-02 (2026-08-25 23:45): send
all 115 in one shot, do not climb.  The owner's stated reason is evidence this
lane did not have - an earlier assistant had already climbed this ladder and
115 gave no trouble, and the reduction to three was an experiment-isolation
choice, not a client limit.  That is ``[owner, from direct experience]`` and
not ``[measured this round]``, and it agrees with the one thing this lane can
check for itself: ``:4292`` sends three actors through the SAME encoder that
``make_v62_port_royal_population_snapshot()`` uses for all 115.

What the staircase was guarding is now guarded more cheaply, per the same
ruling: COUNT THE ACTORS THAT ACTUALLY ASSEMBLED, BEFORE SENDING, AND PRINT
THAT NUMBER.  If the client truncates or refuses, one boot shows the number
directly instead of three boots bracketing it.  See ``dispatch_report()`` and
``census_console_line()``, and note the hard part of the ruling: the count that
goes out must never quietly become something other than 115 - a shortfall has
to arrive with its reason attached.

``build_staircase()`` and ``nesting_break()`` stay in this module.  They are no
longer the plan; they are the diagnostic to reach for if one shot comes back
dead and somebody has to bracket the failure after all.

WHAT THE STAIRCASE CAN AND CANNOT SEPARATE.  Within one anchor each rung is a
strict prefix of the next, so the membership of a lower rung survives into
every higher one.  That is the most this construction gives, and it is less
than "the count is the only variable":

* Climbing a rung also adds new ``template_id`` values and new visual presets,
  each of which is an avatar-template basename the client must resolve
  (``.\\Data\\GC\\V\\%s.avt``, see ``make_npc_attr``).  One unloadable template
  among the new members fails a rung for reasons that have nothing to do with
  count.
* Climbing a rung grows the frame.  Count and bytes are not proportional -
  per-actor size varies with preset length, and P30 carries a name - so a rung
  failure is a joint statement about both until a follow-up separates them.
  Server-side compression is NOT a confound: ``frame_pc`` wraps the payload as
  a snappy raw LITERAL (v141:560), so framed size tracks payload size directly.
* Rungs are nested only AT ONE ANCHOR.  The runtime trigger is the player's
  first TargetPos after runtime ack, so two boots taken from different
  positions produce different rung memberships and are not comparable.  Use
  ``nesting_break()`` on the generations actually built for an attended run
  rather than assuming it.

WHAT A REFUSAL LOOKS LIKE, AND WHY IT IS NOT SELF-INTERPRETING.  The one known
refusal signal is ``ErrorData=28317``.  ``reports/PF_DELETE_SOFT002_NATURAL_
0x36DB_DECODE_20260818.md`` resolves that number: 28317 = 0x6E9D =
GSCN_RunTimeProtocolRes, i.e. the client echoing the class id of whichever
envelope failed to deserialize, and every live reproduction listed there is a
RuntimeRes stream-tail/misalignment fault.  It is a parse-failure echo, not a
count report, and the client closed both connections after it.  The oldest note
in v141 (V43, six actors, same number; V42, one actor, parse-safe) is therefore
not a datum about six being too many.  A rung that dies gives an interval, not
a cause.

RUNG 3 IS THE CONTROL.  The first three members are pinned to the exact
``V112_TEST_INDICES`` (P0, P30, P91) in their exact frozen order, so rung 3 is
byte-identical to what ``make_v112_monster_shop_population_state()`` sends
today - the v141 self-test independently pins that frame at 504/517 bytes
(v141:6104-6107).  Being anchor-invariant, it controls for the encoder and the
harness; it cannot control for anything that varies with position.

WHAT THIS MODULE DOES NOT CLAIM.  It does not give any actor a name, HP,
faction, hostility, AI, locomotion or loot beyond what the frozen V134 encoder
already gives it: P30 keeps its measured HP (V117) and its measured BasicAttr
name (V119); every other member is HP 100 and nameless, exactly as today.  It
claims nothing about rendering, visibility, distance culling or actor-slot
displacement (``GT-072``, open, PARTIAL) - the four things that decide whether
a delivered actor becomes a model on screen.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .population import (
    FULL_MOVEMENT_MASK,
    MOVEMENT_ATTR_ID,
    NPC_ATTR_ID,
    NPC_STYLE_ACTOR_TYPE,
    PORT_ROYAL_SOURCE_COUNT,
    SCENE_ID,
    SCENE_SEQUENCE,
    SceneActorPlacement,
    load_port_royal_placements,
)


# Convention marker only.  Nothing in this tree branches on it; see the module
# docstring before quoting it as evidence of shipped behaviour.
production_allowed = True
test_only = False

CENSUS_COUNT = PORT_ROYAL_SOURCE_COUNT
STAIRCASE_RUNGS = (3, 20, 60, CENSUS_COUNT)
SHIPPED_ISOLATED_INDICES = (0, 30, 91)
SHIPPED_MONSTER_INDEX = 30
DEFAULT_ACTOR_COUNT = CENSUS_COUNT

# The proven schedule the shipped branch uses: the identical collection is
# queued once immediately and once again after model readiness.  The V138
# nearest-20 runtime pass was an initial-plus-reapply pass, not a single frame,
# so a caller that sends one frame is not reproducing what was accepted.
INITIAL_REAPPLY_MS = 3000

# Set this to the highest rung the client was OBSERVED to accept, once an
# attended run answers it.  ``None`` means unmeasured, and unmeasured means the
# default stays the full census rather than a number somebody guessed.
# ``effective_actor_count()`` reads this at CALL time, so editing it here is
# enough - do not also pass it as an argument.
MEASURED_CLIENT_ACTOR_CEILING: int | None = None

# The collection count the client reads sits in a fixed-width header that
# ``make_runtime_remote_actors`` writes the same way every time (v141:1278-1284):
# u16tag class id (3) + u32tag 0 (5) + u8tag 4 (2) + u8tag 0 (2) + u8tag 2 (2),
# then the u16tag actor count (3).  Reading the count back out of the bytes is
# the only way to compare what the wire SAYS against what was assembled.
WIRE_COUNT_TAG_OFFSET = 14
WIRE_HEADER_BYTES = 17
COLLECTION_TAG = 0x12

COUNT_SOURCE_FULL_CENSUS = "full_census"
COUNT_SOURCE_MEASURED_CEILING = "measured_client_ceiling"
COUNT_SOURCE_CALLER = "caller_requested"
COUNT_SOURCES = (
    COUNT_SOURCE_FULL_CENSUS,
    COUNT_SOURCE_MEASURED_CEILING,
    COUNT_SOURCE_CALLER,
)

DEFAULT_HP = 100
HEADINGS = (0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0)
_FLOAT32_MAX = 3.4028234663852886e38
_UNSET = object()


@dataclass(frozen=True)
class WorldPopulationGeneration:
    """One built rung: its membership, its bytes, and nothing installed."""

    actor_count: int
    indices: tuple[int, ...]
    actor_identities: tuple[int, ...]
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
        raise ValueError("player XYZ must be an exact three-value tuple")
    checked = []
    for axis, value in zip("xyz", player_xyz):
        if type(value) not in (int, float):
            raise ValueError(f"player {axis} must be a finite float32 value")
        result = float(value)
        if not math.isfinite(result) or abs(result) > _FLOAT32_MAX:
            raise ValueError(f"player {axis} must be a finite float32 value")
        checked.append(result)
    return (checked[0], checked[1], checked[2])


def _require_actor_count(actor_count: Any) -> int:
    # The census is 115 and the collection count field is a u16, so the census
    # bound is the binding one; there is no separate wire-width check to make.
    if type(actor_count) is not int or not 1 <= actor_count <= CENSUS_COUNT:
        raise ValueError(
            f"actor count must be an integer in [1,{CENSUS_COUNT}]"
        )
    return actor_count


def _pinned_indices(legacy: Any) -> tuple[int, ...]:
    """Read the shipped isolated set from the frozen source, never a literal.

    If the frozen default ever stops being P0/P30/P91 the control rung is no
    longer a control, so this refuses rather than silently measuring something
    else.
    """
    pinned = getattr(legacy, "V112_TEST_INDICES", None)
    if pinned != SHIPPED_ISOLATED_INDICES:
        raise ValueError("frozen isolated population set drift")
    if getattr(legacy, "V112_MONSTER_INDEX", None) != SHIPPED_MONSTER_INDEX:
        raise ValueError("frozen isolated monster index drift")
    return pinned


def census_order(
    legacy: Any,
    player_xyz: tuple[float, float, float],
) -> tuple[SceneActorPlacement, ...]:
    """Order the whole census once: pinned control set first, then nearest-first.

    The ordering is computed for the whole census and every rung is a prefix of
    it, so rung membership is monotone within one anchor.  ``load_port_royal_
    placements`` has already refused duplicate or missing rows and checked the
    table against its sha256, so this does not re-check the table's shape.
    """
    placements = load_port_royal_placements(legacy)
    pinned = _pinned_indices(legacy)
    x, y, z = _require_anchor(player_xyz)

    # No "is the pinned index present" guard: _pinned_indices has already
    # refused anything but (0,30,91) and load_port_royal_placements has already
    # checked the table against its sha256, so their presence is not in doubt.
    # A guard that cannot fire is decoration, and decoration reads as coverage.
    by_index = {item.placement_index: item for item in placements}
    rest = []
    for placement in placements:
        if placement.placement_index in pinned:
            continue
        distance2 = (
            (placement.x - x) ** 2
            + (placement.y - y) ** 2
            + (placement.z - z) ** 2
        )
        rest.append((distance2, placement.placement_index, placement))
    rest.sort(key=lambda item: (item[0], item[1]))

    ordered = [by_index[index] for index in pinned]
    ordered.extend(item[2] for item in rest)
    return tuple(ordered)


def _entry(legacy: Any, placement: SceneActorPlacement) -> bytes:
    """Exactly the frozen V134 per-actor shape, for every member of the census."""
    actor_identity = placement.actor_identity
    is_monster = placement.placement_index == SHIPPED_MONSTER_INDEX
    hp = legacy.V117_P30_EXACT_HP if is_monster else DEFAULT_HP
    npc_attr = legacy.make_npc_attr(
        placement.template_id,
        actor_identity,
        SCENE_ID,
        SCENE_SEQUENCE,
        placement.visual_preset,
        current_hp=hp,
        max_hp=hp,
        # AMENDMENT 2026-08-26 (LANE-A, post-GT-078 OWNER-REJECTED / identity).
        # The frozen PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS row already carries a
        # per-placement source_name (it always has - see the 7-tuple shape in
        # population.py), and this call was discarding it for every entry
        # except the P30 diagnostic override. The client only draws the
        # yellow NPC-name line when BasicAttr bit 0x0001 is set (make_npc_attr
        # docstring, 0x51F920), so a dropped source_name is not a cosmetic
        # gap: it is why GT-078's addendum photo shows a lone blue title line
        # with no name line under it anywhere in town. This does not touch
        # WHICH template_id/visual_preset is sent (that is a placement-
        # identity question RE-077's follow-up owns), only whether the name
        # this table already has for that placement reaches the wire.
        basic_name=(
            legacy.V119_P30_TARGET_NAME if is_monster
            else placement.source_name
        ),
    )
    movement_attr = legacy.make_remote_movement_attr(
        actor_identity,
        placement.x,
        placement.y,
        placement.z,
        HEADINGS[placement.placement_index & 3],
        mask=FULL_MOVEMENT_MASK,
    )
    return legacy.make_remote_actor_entry(
        NPC_STYLE_ACTOR_TYPE,
        actor_identity,
        [(NPC_ATTR_ID, npc_attr), (MOVEMENT_ATTR_ID, movement_attr)],
    )


def build_world_population(
    legacy: Any,
    player_xyz: tuple[float, float, float],
    actor_count: int = DEFAULT_ACTOR_COUNT,
    *,
    scene_id: int,
    count_source: str = COUNT_SOURCE_CALLER,
) -> WorldPopulationGeneration:
    """Build one rung of the census as a single RuntimeRes collection.

    Nothing is sent, scheduled or persisted here.  The caller owns dispatch,
    and owes the frame the reapply the accepted evidence was measured with
    (``INITIAL_REAPPLY_MS``).

    ``scene_id`` HAS NO DEFAULT ON PURPOSE.  This table is bg0001's, built with
    ``SCENE_ID`` fixed at 1 in every actor it encodes.  Once a player can be in
    another scene, a caller that forgets which scene it is in would deliver
    dock NPCs into that other map, and a module that merely REPORTS that hazard
    (``world_scene_travel.population_source``) does not prevent it - the
    refusal has to live where the frame is built.  So every caller states the
    scene it is populating and this refuses anywhere but home.

    ``count_source`` says WHY this count was chosen; it is recorded rather than
    inferred, because the same number can be a measured ceiling in one boot and
    a deliberate experiment in the next.
    """
    if type(scene_id) is not int or scene_id != SCENE_ID:
        raise ValueError(
            f"the bg0001 census is only valid in scene {SCENE_ID}, "
            f"not scene {scene_id!r}"
        )
    if count_source not in COUNT_SOURCES:
        raise ValueError(f"unknown count source {count_source!r}")
    count = _require_actor_count(actor_count)
    ordered = census_order(legacy, player_xyz)[:count]
    entries = [_entry(legacy, placement) for placement in ordered]
    for position, entry in enumerate(entries):
        # An entry that encodes to nothing still counts in the collection's
        # count field, so the client would be told N actors follow and given
        # N-1 bodies - a stream-tail misalignment, which is the one refusal
        # this client is documented to answer with (ErrorData=28317).
        if type(entry) is not bytes or not entry:
            raise ValueError(
                f"placement {ordered[position].placement_index} encoded to an "
                "empty actor entry"
            )
    pc, frame = legacy.make_runtime_remote_actors(entries)
    return WorldPopulationGeneration(
        count,
        tuple(item.placement_index for item in ordered),
        tuple(item.actor_identity for item in ordered),
        _require_anchor(player_xyz),
        pc,
        frame,
        tuple(len(entry) for entry in entries),
        count_source,
    )


def build_staircase(
    legacy: Any,
    player_xyz: tuple[float, float, float],
    rungs: tuple[int, ...] = STAIRCASE_RUNGS,
) -> tuple[WorldPopulationGeneration, ...]:
    """Build every rung against ONE anchor, cheapest first.

    Rungs must be strictly increasing so that the built memberships are nested;
    an unsorted or repeating rung list is a caller error, not something to
    quietly sort, because the run order is what the attended tester follows.

    Nesting is guaranteed here only because every rung is a prefix of one
    ``census_order()`` call.  The threat this cannot address is an attended run
    whose boots have different anchors - check those with ``nesting_break()``.
    """
    if type(rungs) is not tuple or not rungs:
        raise ValueError("rungs must be a non-empty tuple")
    checked = tuple(_require_actor_count(count) for count in rungs)
    for previous, current in zip(checked, checked[1:]):
        if current <= previous:
            raise ValueError("rungs must be strictly increasing")
    return tuple(
        build_world_population(legacy, player_xyz, count, scene_id=SCENE_ID)
        for count in checked
    )


def nesting_break(
    generations: tuple[WorldPopulationGeneration, ...],
) -> tuple[int, ...] | None:
    """Return the first membership a higher rung dropped, or None if nested.

    This is the check that matters for a real attended run, where each rung is
    a separate boot and therefore a separate anchor.  If a boot was taken from
    a different position, its rung is not a superset of the rung below and the
    two boots cannot be read as steps of one staircase.
    """
    if type(generations) is not tuple or not generations:
        raise ValueError("generations must be a non-empty tuple")
    for lower, higher in zip(generations, generations[1:]):
        if higher.actor_count <= lower.actor_count:
            raise ValueError("generations must be given in increasing size")
        dropped = tuple(
            index for index in lower.indices if index not in set(higher.indices)
        )
        if dropped:
            return dropped
    return None


def effective_actor_count(ceiling: Any = _UNSET) -> int:
    """The count the runtime should send: the census, capped by MEASURED fact.

    Called with no argument it reads ``MEASURED_CLIENT_ACTOR_CEILING`` at call
    time, so recording a measured ceiling in this module actually changes what
    callers send.  Before anything is measured this returns the whole census on
    purpose: a guessed cap would look like caution and would in fact be the
    same mistake that left three actors in bg0001 for months.
    """
    if ceiling is _UNSET:
        ceiling = MEASURED_CLIENT_ACTOR_CEILING
    if ceiling is None:
        return DEFAULT_ACTOR_COUNT
    if type(ceiling) is not int or not 1 <= ceiling <= CENSUS_COUNT:
        raise ValueError(f"ceiling must be an integer in [1,{CENSUS_COUNT}]")
    return min(DEFAULT_ACTOR_COUNT, ceiling)


def census_count_for_dispatch() -> tuple[int, str]:
    """The count a flagless boot should send, and WHY that number.

    One call, two values, so the caller never has to reconstruct the reason
    from the number - which is exactly the inference that would misreport a
    deliberate 20-actor rung as a client ceiling on a day when a ceiling of 20
    happens to be recorded.
    """
    ceiling = MEASURED_CLIENT_ACTOR_CEILING
    count = effective_actor_count()
    if ceiling is not None and count < CENSUS_COUNT:
        return (count, COUNT_SOURCE_MEASURED_CEILING)
    return (count, COUNT_SOURCE_FULL_CENSUS)


def wire_actor_count(generation: WorldPopulationGeneration) -> int:
    """Read the collection count back out of the bytes that will be sent.

    Everything else in this module counts what was ASSEMBLED.  This counts what
    the client will be TOLD, which is the number that decides how many actor
    bodies it tries to read.  The two are the same only if the encoder put
    every entry in, and nothing else in this tree checks that.
    """
    if type(generation) is not WorldPopulationGeneration:
        raise ValueError("wire actor count needs a WorldPopulationGeneration")
    pc = generation.pc
    if len(pc) < WIRE_HEADER_BYTES or pc[WIRE_COUNT_TAG_OFFSET] != COLLECTION_TAG:
        raise ValueError("built frame does not carry the expected collection header")
    return int.from_bytes(
        pc[WIRE_COUNT_TAG_OFFSET + 1:WIRE_COUNT_TAG_OFFSET + 3], "little"
    )


def census_shortfall_reason(
    assembled_count: int,
    count_source: str = COUNT_SOURCE_CALLER,
) -> str | None:
    """Why fewer than the whole census went out, or None when none is missing.

    CHARTER-02 forbids the shipped count from becoming something other than 115
    without saying so.  The reason is taken from what the CALLER recorded when
    it chose the count, not inferred from the number afterwards: the same 60
    can be a measured client ceiling on one boot and a deliberate diagnostic
    rung on the next, and a report that guesses between them is worse than one
    that asks.
    """
    assembled = _require_actor_count(assembled_count)
    if count_source not in COUNT_SOURCES:
        raise ValueError(f"unknown count source {count_source!r}")
    if assembled == CENSUS_COUNT:
        return None
    if count_source == COUNT_SOURCE_MEASURED_CEILING:
        return f"{COUNT_SOURCE_MEASURED_CEILING}={assembled}"
    return f"{COUNT_SOURCE_CALLER}={assembled}"


def dispatch_report(generation: WorldPopulationGeneration) -> dict:
    """Count what assembled BEFORE it goes out, and cross-check it against the
    bytes.

    This is the pre-send count CHARTER-02 requires in place of the staircase.
    Three numbers have to agree, and each one can move without the others:

    * ``assembled_count`` - how many placements this module put in the list.
    * ``wire_actor_count`` - what the collection header will tell the client.
    * ``body_bytes`` vs the sum of the per-entry lengths - whether that many
      actor bodies are really in the payload.

    The third is the one that catches a silently dropped body, which produces
    exactly the stream-tail misalignment this client answers with
    ``ErrorData=28317``.  A report that only counted its own input would print
    ``115/115`` for that frame.
    """
    if type(generation) is not WorldPopulationGeneration:
        raise ValueError("dispatch report needs a WorldPopulationGeneration")
    assembled = len(generation.indices)
    declared = wire_actor_count(generation)
    body_bytes = generation.pc_bytes - WIRE_HEADER_BYTES
    entry_bytes_total = sum(generation.entry_bytes)
    bodies_intact = (
        bool(generation.entry_bytes)
        and len(generation.entry_bytes) == assembled
        and body_bytes == entry_bytes_total
        and all(generation.entry_bytes)
    )
    return {
        "assembled_count": assembled,
        "wire_actor_count": declared,
        "census_count": CENSUS_COUNT,
        "count_source": generation.count_source,
        "shortfall_reason": census_shortfall_reason(
            assembled, generation.count_source),
        "counts_agree": declared == assembled,
        "bodies_intact": bodies_intact,
        "body_bytes": body_bytes,
        "entry_bytes_total": entry_bytes_total,
        "pc_bytes": generation.pc_bytes,
        "frame_bytes": generation.frame_bytes,
        "anchor": list(generation.anchor),
        "initial_reapply_ms": INITIAL_REAPPLY_MS,
    }


def census_console_line(generation: WorldPopulationGeneration) -> str:
    """The single ASCII line a boot prints before the census goes on the wire.

    Without this line four boots of the same build are indistinguishable in a
    log, which is the state BUILD-001 was written to end.  It carries the wire
    count and the body check beside the assembled count, because those are the
    two ways ``115`` can be printed over a frame that is not 115 actors.  The
    bridge console is cp874, so this stays inside 7-bit ASCII deliberately.
    """
    report = dispatch_report(generation)
    return (
        "WORLD_CENSUS assembled={0}/{1} wire={2} bodies={3} pc={4}B frame={5}B "
        "anchor=({6:.3f},{7:.3f},{8:.3f}) reapply_ms={9} source={10} "
        "shortfall={11}".format(
            report["assembled_count"], report["census_count"],
            report["wire_actor_count"] if report["counts_agree"]
            else "MISMATCH:%d" % report["wire_actor_count"],
            "ok" if report["bodies_intact"] else "SHORT",
            report["pc_bytes"], report["frame_bytes"],
            report["anchor"][0], report["anchor"][1], report["anchor"][2],
            report["initial_reapply_ms"], report["count_source"],
            report["shortfall_reason"] or "none",
        )
    )


def staircase_report(
    legacy: Any,
    player_xyz: tuple[float, float, float],
    rungs: tuple[int, ...] = STAIRCASE_RUNGS,
) -> dict:
    """Rung sizes, membership and byte counts, so a ticket can pin expectations.

    Membership is included on purpose: the byte counts alone cannot tell an
    analyst which placements a rung contained, and at any anchor other than the
    pinned one the byte counts are the part that changes.
    """
    built = build_staircase(legacy, player_xyz, rungs)
    return {
        "anchor": _require_anchor(player_xyz),
        "census_count": CENSUS_COUNT,
        "control_rung_indices": list(SHIPPED_ISOLATED_INDICES),
        "initial_reapply_ms": INITIAL_REAPPLY_MS,
        "rungs": [
            {
                "actor_count": generation.actor_count,
                "pc_bytes": generation.pc_bytes,
                "frame_bytes": generation.frame_bytes,
                "indices": list(generation.indices),
            }
            for generation in built
        ],
    }
