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
        basic_name=(legacy.V119_P30_TARGET_NAME if is_monster else ""),
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
) -> WorldPopulationGeneration:
    """Build one rung of the census as a single RuntimeRes collection.

    Nothing is sent, scheduled or persisted here.  The caller owns dispatch,
    and owes the frame the reapply the accepted evidence was measured with
    (``INITIAL_REAPPLY_MS``).
    """
    count = _require_actor_count(actor_count)
    ordered = census_order(legacy, player_xyz)[:count]
    entries = [_entry(legacy, placement) for placement in ordered]
    pc, frame = legacy.make_runtime_remote_actors(entries)
    return WorldPopulationGeneration(
        count,
        tuple(item.placement_index for item in ordered),
        tuple(item.actor_identity for item in ordered),
        _require_anchor(player_xyz),
        pc,
        frame,
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
        build_world_population(legacy, player_xyz, count) for count in checked
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
