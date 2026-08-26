"""Which population generation belongs to the scene a player just arrived in.

LANE-A build order: the seam between ``BUILD-001`` (the bg0001 census, ``M1``)
and ``BUILD-002`` (travel out of town, ``M2``).  Neither build order owns this
seam, and until this module existed nothing in either repository did.

THE TWO THINGS A PLAYER WOULD SEE IF NOBODY OWNED IT.  The census is composed
once, on the login path, and nothing recomposes it in-session.  Travel moves
the player to another scene inside that same session, with no further
collection on the wire.  So:

1.  **The town follows you out of it.**  The client's remote actor collection
    is generation based, and nothing in the crossing replaces it, so the actors
    composed for Port Royal are still the client's actor list while the player
    stands in scene 278, at bg0001 world coordinates.
2.  **You come home to a ghost town.**  The return crossing has no generation
    either, so a player who walks back into Port Royal gets whatever survived
    the round trip - and if anything culled them, an empty city.

    THE PREMISE, AND WHERE IT IS AND IS NOT CHECKABLE.  "Composed once on the
    login path" is checkable at HEAD only for the FROZEN path: ``v141:4292``
    is latched on ``not self.npc_spawn_sent`` and sets it at ``:4308``, and the
    in-session refresh at ``v141:4326-4360`` is gated behind
    ``v138_marker1_population_sent``, which needs an exact
    ``V138_MARKER1_READY_PC`` frame after V137 transport and is False on the
    flagless path.  So the frozen server sends one generation per session.
    The ``WORLD_CENSUS_INITIAL_`` / ``WORLD_CENSUS_REAPPLY_`` labels named in
    this lane's letters are from ``pirate-force-server PR #41``, which is NOT
    merged: ``git grep`` for either label at HEAD returns nothing.  Do not read
    this module as evidence that the census ships.

WHAT THIS MODULE DOES.  One decision, in one place: given the scene the player
has just been confirmed into, it composes the collection that scene's
population is, over the SAME encoder and the SAME frozen table the census
already uses::

    scene 1 (home)      -> the bg0001 census, rebuilt at the arrival anchor
    any other scene     -> the EMPTY generation, 0 entries

It does not invent a population for a scene that has none, and it cannot
deliver dock NPCs into another map: the census path goes through
``world_population.build_world_population``, which refuses any scene but 1, and
the choice between the two branches is ``world_scene_travel.population_source``
rather than a second table this lane would then have to keep in step.

WHAT THE EMPTY GENERATION IS RESTING ON.  [INFERENCE, NOT MEASURED - read this
paragraph before quoting any other one.]  Two comments in the frozen server say
omission despawns::

    v141:1776  "omitting static actors despawns them"   (V92 header)
    v141:1822  "V91 proved omitted members disappear"   (V94 header)

Those are two citations of ONE V91 run, not two findings.  The runtime report
that reproduced that membership sequence is
``reports/PF_OBJECT_POP002_AUTHORITATIVE_SCENE_ACTOR_RUNTIME_PASS_20260816.md``
and it disclaims exactly what this module would like it to say::

    :115   "do not prove that any particular omitted actor visibly despawned"
    :176   evidence ceiling: "does not prove client-visible despawn"

(``reports/PF_MULTIPLAYER_READINESS_AUDIT001_*.md:245`` lists removal-by-
omission as runtime-proven, citing that same report.  The tree contradicts
itself; the report is the source and the report says no.)

What IS measured, in this repository, against the real
``current/pf_login_game_server_v141.py``::

    make_runtime_remote_actors(()) -> pc 17 bytes (header exactly), frame 27,
    pc[14] = 0x12, wire actor count = 0, and frame == frame_pc(pc)

    So: THE EMPTY COLLECTION ENCODES - measured.  THE CLIENT ANSWERS IT BY
    CLEARING ITS ACTOR LIST - inferred from a run whose own report refuses to
    claim it, and never once sent with ZERO entries by this project.  The
    attended answer is free: RIDER-081-A on GT-081 asks a tester who is
    already crossing to write down what they see.  The static half is
    ``RE-077 T5``, open, no result.

WHAT ELSE IS IN THAT COLLECTION - THE BLAST RADIUS.  ``make_runtime_remote_actors``
is the only remote-actor collection in this tree, and fourteen modules compose
one.  If the semantics are "replace", an empty generation removes EVERYTHING
the client holds there - other players, field mobs, corpses on a death timer,
ground loot, scene objects - not only the census.

Measured scope today, and it is the only reason this is shippable: on the
flagless path there is exactly ONE sender.  Every other caller is either
``*_hypothesis`` (scenario-gated, off by default) or a lane-B module
``runtime.py`` does not import at all.  So the clear frame's blast radius today
IS the census.

    THE RULE THAT KEEPS IT THAT WAY, and it is not this module's to enforce:
    anything else that ever shares this collection on the flagless path has to
    be composed INTO the arrival generation, not sent as a second frame after
    it.  Two senders and a replace-semantics collection is one of them wiping
    the other, whichever order they go out in.

    AND THE QUESTION NOBODY IN THIS PROJECT HAS ANSWERED: ``mob_combat.py:923``
    and ``mob_death.py:852`` each send a ONE-entry collection.  Under replace
    semantics every HP-bar frame wipes the other 114 actors.  Either replace is
    wrong - and then this clear frame does nothing - or those modules have been
    shipping world-wipes.  Both cannot be true.  This module is the first thing
    that makes the answer load-bearing, and it does not know it.

WHERE THE CALL GOES, AND IN WHAT ORDER.  After the crossing commits - the row
is written and ``confirmed_fields()`` has been called - and then it depends on
which frame this is, which is why ``dispatch_slot`` is on the object rather
than in prose a caller can read wrong::

    KIND_CLEAR   -> BEFORE the teleport frames
    KIND_CENSUS  -> AFTER the teleport frames

The removal belongs to the scene the client is still in: the only state anyone
has ever observed omission behave in is ``StateRunTime`` in a loaded scene, and
a clear handed to a client in the middle of a scene load may simply be dropped
- after which nothing recomposes in-session and the town follows the player for
the rest of the session.  The addition belongs to the scene the client is going
to: 115 actors tagged scene 1 delivered while the client still renders 278 is
the same mistake pointed the other way.

    THE COST OF THAT CHOICE, SAID PLAINLY RATHER THAN ARGUED AWAY.  If the
    crossing commits and the client then FAILS to load the destination - it
    parks at status 2, or never settles, both of which ``world_travel_gate``
    has named paths for - the player is left in Port Royal with an empty Port
    Royal, for the rest of the session.  That is a real cost and this ordering
    accepts it, because that player is already stranded by the durable row
    (every subsequent login goes to 278 too), and because the alternative
    trades a rare permanent failure for a systematic one.
    ``TravelGateSet._settle()`` is the one place in this project that observes
    the client actually changed scene; it is private, has no callback, and if
    it ever gets one, THAT is where this frame should be composed instead.

WHAT THIS MODULE IS NOT.  It is not a second census, and it does not populate
scene 278: scene 278's nine authored placements are pinned in
``scenarios/world_scene_registry_001.json`` and composing them is a build order
nobody has opened.  Arriving there means arriving alone, on purpose.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .world_population import (
    COLLECTION_TAG,
    COUNT_SOURCE_CALLER,
    INITIAL_REAPPLY_MS,
    WIRE_COUNT_TAG_OFFSET,
    WIRE_HEADER_BYTES,
    WorldPopulationGeneration,
    build_world_population,
    census_count_for_dispatch,
    dispatch_report,
)
from .world_scene_travel import CENSUS_SCENE_ID, population_source

# What the handoff turned out to be.  Recorded, never inferred from the actor
# count afterwards: an empty census and a deliberate clear encode to the same
# bytes and mean opposite things.
KIND_CENSUS = "census"
KIND_CLEAR = "clear"
KIND_UNAVAILABLE = "unavailable"

# Where in the crossing batch this frame goes.  On the object because a caller
# that has to remember a prose rule is a caller that will one day forget it -
# see the ordering paragraph in the module docstring for why the two kinds
# differ.
SLOT_BEFORE_TELEPORT = "before_teleport"
SLOT_AFTER_TELEPORT = "after_teleport"
SLOT_NOT_APPLICABLE = "no_frame"

# The console label prefixes.  The bridge console is cp874, so every string
# this module can put in front of ``print`` is forced through ``_ascii_safe``
# and pinned by a test that feeds it non-ASCII on purpose.
LABEL_CENSUS = "WORLD_POP_HANDOFF_CENSUS_SCENE_{0}"
LABEL_CLEAR = "WORLD_POP_HANDOFF_CLEAR_SCENE_{0}"
LABEL_UNAVAILABLE = "WORLD_POP_HANDOFF_UNAVAILABLE"

# The clear frame carries no reapply.  Not because there is no model to ready -
# that is the census's reason - but because a second copy would only help
# against LOSS of the first, and the ordering above already puts the clear
# where the client is most able to act on it.  If an attended run ever shows a
# clear being dropped, this is the constant that answers it, and it should be
# changed with that evidence attached rather than pre-emptively.
CLEAR_REAPPLY_MS: int | None = None

_ASCII_PRINTABLE = frozenset(range(0x20, 0x7F))


def _ascii_safe(text: Any, limit: int = 120) -> str:
    """Whatever came in, out comes something a cp874 console can print.

    Reasons carry ``str(exception)``, and an exception message can contain any
    character at all - a scene id read out of a TEXT column, a path, a repr
    (which does not escape non-ASCII, PEP 3138).  A refusal that cannot be
    printed is a refusal nobody sees, and a ``\\r`` in one is worse than that:
    on a Windows console it rewrites the line it was supposed to add.
    """
    try:
        raw = str(text)
    except Exception:  # noqa: BLE001 - a __str__ that raises is still an input
        return "unprintable"
    out = []
    for char in raw:
        out.append(char if ord(char) in _ASCII_PRINTABLE else "?")
    cleaned = "".join(out).strip()
    return cleaned[:limit] if cleaned else "none"


@dataclass(frozen=True)
class SceneHandoff:
    """One composed handoff: what it is, why, where it goes, and the bytes.

    ``generation`` is present only for ``KIND_CENSUS``; the clear frame has no
    membership to describe and ``None`` is the honest value rather than an
    empty ``WorldPopulationGeneration`` that would report ``0/115`` as if a
    census had assembled badly.
    """

    scene_id: int
    kind: str
    reason: str
    label: str
    actor_count: int
    pc: bytes
    frame: bytes
    reapply_ms: int | None
    dispatch_slot: str
    generation: WorldPopulationGeneration | None

    @property
    def sends_a_frame(self) -> bool:
        """Whether there is anything to queue.

        Reads the bytes, not the kind: a caller that branched on ``kind`` and
        got a spelling wrong would queue empty bytes as if they were a
        generation, and this is the flag that makes that impossible to write
        by accident.
        """
        return self.kind != KIND_UNAVAILABLE and bool(self.pc) and bool(self.frame)

    @property
    def membership(self) -> tuple[int, ...]:
        """The placement indices this frame puts on the client, if any.

        The caller owns the server-side membership set (``population_indices``
        in the frozen state) and cannot keep it honest without this.  See the
        note on the ChooseNPC path in ``handoff_report``.
        """
        if self.generation is None:
            return ()
        return tuple(self.generation.indices)


def _require_scene_id(scene_id: Any) -> int:
    if type(scene_id) is not int or isinstance(scene_id, bool):
        raise ValueError(f"scene id must be an int, not {scene_id!r}")
    if not 1 <= scene_id <= 0xFFFF:
        raise ValueError(f"scene id {scene_id} is outside the wire's range")
    return scene_id


def _require_anchor(anchor: Any) -> tuple[float, float, float]:
    if type(anchor) is not tuple or len(anchor) != 3:
        raise ValueError("the arrival anchor must be an (x, y, z) tuple")
    out = []
    for value in anchor:
        if type(value) not in (int, float) or isinstance(value, bool):
            raise ValueError(f"anchor component {value!r} is not a number")
        out.append(float(value))
    return (out[0], out[1], out[2])


def wire_count_of(pc: Any) -> int:
    """Read the collection count back out of arbitrary composed bytes.

    ``world_population.wire_actor_count`` answers the same question for a built
    ``WorldPopulationGeneration``; the clear frame is not one.

    The check is deliberately weak in a known way: ``0x12`` is the generic
    u16-tag byte, not a signature, so this accepts any buffer long enough with
    a ``0x12`` at the offset the encoder always writes the count tag to.  It
    catches a truncated or reshaped header, not a forged one, and the pair
    check against ``frame_pc`` is what actually ties these bytes to the frame.
    """
    if type(pc) is not bytes:
        raise ValueError("a composed collection is bytes")
    if len(pc) < WIRE_HEADER_BYTES or pc[WIRE_COUNT_TAG_OFFSET] != COLLECTION_TAG:
        raise ValueError("composed frame does not carry the expected collection header")
    return int.from_bytes(
        pc[WIRE_COUNT_TAG_OFFSET + 1:WIRE_COUNT_TAG_OFFSET + 3], "little"
    )


def _require_pair(legacy: Any, pc: bytes, frame: bytes, what: str) -> None:
    """The frame is what goes on the wire; the pc is what everything checks.

    ``v141:7755`` sends ``out_frame`` and nothing else, so every count and
    length check in this module reads a buffer the client never receives.  Six
    other modules in this tree close that gap the same way - compare the frame
    against ``frame_pc(pc)`` and refuse on drift - and a clear frame that was
    validated as empty while carrying a census payload is the exact failure
    this module exists to prevent, pointed at itself.
    """
    if type(frame) is not bytes or not frame:
        raise ValueError(f"the composed {what} carries no frame")
    rebuilt = legacy.frame_pc(pc)
    if type(rebuilt) is not bytes:
        raise ValueError("frame_pc did not return bytes")
    if frame != rebuilt:
        raise ValueError(
            f"the composed {what} frame does not match its own pc "
            f"({len(frame)}B frame over a {len(pc)}B pc) - encoder drift"
        )


def build_clear_generation(legacy: Any) -> tuple[bytes, bytes]:
    """Compose the empty generation over the frozen encoder, and prove it.

    Nothing here is synthetic: the same ``make_runtime_remote_actors`` the
    census goes out over is asked for a collection with no entries.  The
    checks, in the order a drift would hit them:

    * the return shape is a ``(pc, frame)`` pair of bytes;
    * the frame is the pc's own frame (``_require_pair``) - without this every
      check below reads a buffer that is not what gets sent;
    * the header says zero actors, which is the check that catches a header
      promising bodies that are not in the payload (ErrorData=28317);
    * the pc is header-length exactly, which catches a body behind that zero.
    """
    if legacy is None:
        raise ValueError("composing the clear frame needs the legacy module")
    composed = legacy.make_runtime_remote_actors(())
    if type(composed) is not tuple or len(composed) != 2:
        raise ValueError("make_runtime_remote_actors did not return (pc, frame)")
    pc, frame = composed
    if type(pc) is not bytes:
        raise ValueError("the composed clear frame is not bytes")
    _require_pair(legacy, pc, frame, "clear")
    count = wire_count_of(pc)
    if count != 0:
        raise ValueError(
            f"the clear frame declares {count} actors, so it is not a clear"
        )
    if len(pc) != WIRE_HEADER_BYTES:
        raise ValueError(
            f"the clear frame carries {len(pc) - WIRE_HEADER_BYTES} bytes of "
            "body behind a zero count"
        )
    return (pc, frame)


def handoff_for_arrival(
    legacy: Any,
    scene_id: Any,
    anchor: Any,
    *,
    actor_count: int | None = None,
) -> SceneHandoff:
    """Compose the generation the arrival scene's population is.

    STRICT: this raises on a caller error, and it is NOT the function to call
    from the frame path.  See ``handoff_on_crossing``, which is, and which
    exists because the block this call belongs in has no ``except`` around it -
    a raise there does not refuse the handoff, it ends frame handling for the
    connection.

    ``actor_count`` is for the ceiling rung an attended run may one day pin;
    ``None`` means the count the census itself decides, with its own recorded
    reason, which is the only value that can honestly print ``115``.
    """
    scene = _require_scene_id(scene_id)
    arrival_anchor = _require_anchor(anchor)
    if population_source(scene) is None:
        pc, frame = build_clear_generation(legacy)
        return SceneHandoff(
            scene_id=scene,
            kind=KIND_CLEAR,
            reason=f"scene_{scene}_has_no_population_table",
            label=LABEL_CLEAR.format(scene),
            actor_count=0,
            pc=pc,
            frame=frame,
            reapply_ms=CLEAR_REAPPLY_MS,
            dispatch_slot=SLOT_BEFORE_TELEPORT,
            generation=None,
        )
    # ``population_source`` answers for exactly one scene, and
    # ``build_world_population`` refuses any other, so there is no third branch
    # to write here.  The day the table answers for two scenes, that refusal
    # is what fires, in the module that owns the table.
    if actor_count is None:
        count, count_source = census_count_for_dispatch()
    else:
        if type(actor_count) is not int or isinstance(actor_count, bool):
            raise ValueError(f"actor count must be an int, not {actor_count!r}")
        # A count the caller chose is recorded as the caller's, never as the
        # full census: ``census_shortfall_reason`` reads that field to decide
        # whether a short frame arrives with its reason attached, which is what
        # CHARTER-02 forbids losing.
        count, count_source = (actor_count, COUNT_SOURCE_CALLER)
    generation = build_world_population(
        legacy,
        arrival_anchor,
        count,
        scene_id=CENSUS_SCENE_ID,
        count_source=count_source,
    )
    _require_pair(legacy, generation.pc, generation.frame, "census")
    return SceneHandoff(
        scene_id=scene,
        kind=KIND_CENSUS,
        reason="home_scene_repopulated_after_return",
        label=LABEL_CENSUS.format(scene),
        actor_count=len(generation.indices),
        pc=generation.pc,
        frame=generation.frame,
        reapply_ms=INITIAL_REAPPLY_MS,
        dispatch_slot=SLOT_AFTER_TELEPORT,
        generation=generation,
    )


def handoff_on_crossing(
    legacy: Any,
    scene_id: Any,
    anchor: Any,
    *,
    actor_count: int | None = None,
) -> SceneHandoff:
    """The frame-path entry point.  This does not raise.  Ever.

    The block a crossing commits in (``runtime.py``, the ``scene_load_scenario
    is None`` branch of the position path) has no ``except`` of its own, and
    the one nearby that does catches ``KeyError`` and ``PermissionError`` only.
    Anything else out of a call in there is not a refusal - it kills frame
    handling for that connection, which is the failure this lane already
    shipped once and had refuted.

    A handoff that could not be composed comes back as ``KIND_UNAVAILABLE``
    with the reason attached and NO BYTES, and the consequence is written down
    rather than hidden: the player keeps whatever actor list they already had,
    which is the state this module exists to end, but they keep playing.

    Nothing counts these refusals.  A caller that wants to know whether they
    are rising has to count them itself, and this line is here so that the
    absence is a decision on the record rather than an oversight.

    THE ONE THING IT DOES LET THROUGH, deliberately: ``KeyboardInterrupt`` and
    ``SystemExit``.  Those are not composition failures, and a frame handler
    that swallows them is a process the operator cannot stop at the moment they
    are trying to stop it.  Everything a composition can actually produce -
    including anything raised inside an exception's own ``__str__`` - is
    caught.
    """
    try:
        return handoff_for_arrival(
            legacy, scene_id, anchor, actor_count=actor_count
        )
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as failure:  # noqa: BLE001 - the contract is absolute
        reason = _ascii_safe(type(failure).__name__, 40)
        detail = _ascii_safe(failure)
        try:
            scene = _require_scene_id(scene_id)
        except BaseException:  # noqa: BLE001 - the scene id is what failed
            scene = 0
        return SceneHandoff(
            scene_id=scene,
            kind=KIND_UNAVAILABLE,
            reason=f"handoff_not_composed:{reason}:{detail}",
            label=LABEL_UNAVAILABLE,
            actor_count=0,
            pc=b"",
            frame=b"",
            reapply_ms=None,
            dispatch_slot=SLOT_NOT_APPLICABLE,
            generation=None,
        )


def handoff_report(handoff: SceneHandoff) -> dict:
    """One flat dict for a console line, a ticket, or a test.

    The census branch carries the census's own dispatch report inside it rather
    than re-counting: two modules counting the same frame is two numbers that
    can disagree, and the one that would be wrong is this one.

    ``membership`` is in here for the caller, not for this module.  The frozen
    state keeps its own set (``population_indices``, ``v141:3579``), and
    ``v141:4396-4420`` answers a ChooseNPC for any identity in it, at
    ``last_target_pos``, with no scene check.  A caller that queues a clear and
    leaves that set alone can have the whole town recomposed into the new scene
    by one click; a caller that queues the return census and leaves it alone
    has 112 of 115 townspeople silently unclickable.  Neither is this module's
    to fix - the set belongs to ``runtime.py`` - but neither can be fixed
    without the membership, so it is offered here.
    """
    if type(handoff) is not SceneHandoff:
        raise ValueError("handoff report needs a SceneHandoff")
    report = {
        "scene_id": handoff.scene_id,
        "kind": handoff.kind,
        "reason": handoff.reason,
        "label": handoff.label,
        "actor_count": handoff.actor_count,
        "sends_a_frame": handoff.sends_a_frame,
        "dispatch_slot": handoff.dispatch_slot,
        "pc_bytes": len(handoff.pc),
        "frame_bytes": len(handoff.frame),
        "reapply_ms": handoff.reapply_ms,
        "membership": handoff.membership,
        "wire_actor_count": None,
        "census": None,
    }
    if handoff.pc:
        try:
            report["wire_actor_count"] = wire_count_of(handoff.pc)
        except ValueError:
            report["wire_actor_count"] = "UNREADABLE"
    if handoff.generation is not None:
        report["census"] = dispatch_report(handoff.generation)
    return report


def handoff_console_line(handoff: Any) -> str:
    """The single ASCII line a crossing prints, whichever way it went.

    This does not raise either, and for the same reason as
    ``handoff_on_crossing``: it is what a caller in that same no-``except``
    block calls to print a refusal, so a reporting helper that raises would
    route around the whole contract.

    The number that matters - what the client will be TOLD is in the
    collection - is read back out of the bytes, not out of this module's
    intent.  ``clear`` printing ``wire=0`` is the point of the line: a clear
    that quietly became a census, or a census that quietly became a clear,
    both show up here as a number that does not match the kind.
    """
    try:
        report = handoff_report(handoff)
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as failure:  # noqa: BLE001 - see the docstring
        return (
            "WORLD_POP_HANDOFF unreportable reason=" +
            _ascii_safe(type(failure).__name__, 40)
        )
    wire = report["wire_actor_count"]
    return _ascii_safe(
        "WORLD_POP_HANDOFF scene={0} kind={1} actors={2} wire={3} "
        "pc={4}B frame={5}B reapply_ms={6} slot={7} reason={8}".format(
            report["scene_id"],
            report["kind"],
            report["actor_count"],
            "none" if wire is None else wire,
            report["pc_bytes"],
            report["frame_bytes"],
            "none" if report["reapply_ms"] is None else report["reapply_ms"],
            report["dispatch_slot"],
            report["reason"] or "none",
        ),
        400,
    )
