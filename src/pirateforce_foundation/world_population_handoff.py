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
    already crossing to write down what they see.

    THE SENTENCE THAT USED TO END THIS PARAGRAPH WAS WRONG, AND THIS LANE
    WROTE IT.  It said: "The static half is ``RE-077 T5``, open, no result."
    ``RE-077``'s result letter (``pf_bridge/notes_to_chief/20260826_0120_
    RE-077-RESULT-SCENE-TRANSITION-SEQUENCE-PINNED.md``) closed T5 as a
    BOUNDED NEGATIVE at 01:20 on the same day, with the switch-scene cleanup
    slot ``0x004C7160`` and its helper ``0x004C6920`` walked as a complete
    recursive CFG.  The mistake came from reading the ticket header in
    ``CLIENT_RE_QUEUE.md``, which still says OPEN, instead of the letter.

    WHAT THE BOUNDED NEGATIVE ACTUALLY SAYS, AND WHY IT CHANGES NOTHING HERE.
    Those functions do clear world/app collections, but indirect calls remain
    unresolved and there is no identity-membership crosswalk, so the letter
    refuses BOTH readings in its own words: the static evidence "is not enough
    to claim either side; do not shorten this to remote actors being preserved
    or dropped".  So the static half is CLOSED and it is closed on "nobody
    knows".  This module's empty generation is still resting on inference, the
    attended eye is still the first answer, and no reader may cite T5 for
    either direction.

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
from .world_scene_travel import CENSUS_SCENE_ID, CENSUS_SOURCE, population_source

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

# THE BAND A CROSSING IS JUDGED IN.  2000 units is not chosen here: it is the
# band ``world_density`` already reports the login view in ("census members
# within 2000 units of the login anchor ... 2"), and reusing it means the
# number this module prints for a crossing can be compared with the number
# that module prints for a login without a conversion nobody wrote down.  It
# is a REPORTING band and nothing else - no frame, no cull, no render radius
# is derived from it, and this project has never measured what the client's
# render distance actually is.
STOWAWAY_REPORT_RADIUS = 2000.0

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
class MembershipReset:
    """The two frozen-state fields a crossing has to rewrite, together.

    ``v141:3579`` holds ``population_indices`` and ``v141:4326-4360`` reads a
    refresh anchor beside it.  They describe ONE scene between them; written
    apart, they can describe two.
    """

    population_indices: tuple[int, ...] | None
    population_refresh_anchor: tuple[float, float, float] | None

    @property
    def clears_everything(self) -> bool:
        return (self.population_indices is None
                and self.population_refresh_anchor is None)


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

        PREFER ``membership_reset``.  This property is half of a pair and
        nothing here stops a caller taking only the half they remembered.
        """
        if self.generation is None:
            return ()
        return tuple(self.generation.indices)

    @property
    def membership_reset(self) -> "MembershipReset":
        """BOTH server-side fields, as one object that cannot be half-taken.

        The round that built this module wrote down the hazard it was leaving
        open: a caller who sets ``population_indices`` from ``membership`` and
        forgets ``population_refresh_anchor`` leaves the frozen state holding
        the OLD scene's anchor, and this module has no test that can see it.
        The fix is not another sentence in a letter - it is handing the caller
        one value with both fields in it, so the two cannot disagree.

            crossing INTO the census scene -> the census's own membership and
            the anchor it was actually built at, which is the arrival
            position rather than anything the caller has to remember.

            every other crossing, and every unavailable handoff -> None and
            None.  Clearing on UNAVAILABLE is deliberate: no frame goes out,
            so the client keeps the old scene's actors, and the frozen state's
            ``last_target_pos`` is already in the new scene - which is exactly
            the state where one ChooseNPC recomposes the old town into the new
            map.  A membership nobody can answer for is a membership to drop.
        """
        if self.kind != KIND_CENSUS or self.generation is None:
            return MembershipReset(None, None)
        return MembershipReset(
            tuple(self.generation.indices), tuple(self.generation.anchor))


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
    # GENERALIZED 2026-08-27 (PANYA-DECISION 20:10, M1-P) BROKE THE OLD GUARD
    # HERE, AND THIS IS THE FIX.  ``population_source`` used to answer for
    # exactly one scene (1), so "not None" and "== bg0001's census" were the
    # same test.  M1-P gave scene 2 its own named source
    # ("bg0002_roster", ``world_population_bg0002.py``) so they no longer
    # are: the branch below UNCONDITIONALLY calls ``build_world_population``
    # with ``scene_id=CENSUS_SCENE_ID`` (1) hardcoded, so a bare "is not
    # None" test here would have handed scene 2's arrival the BG0001 CENSUS -
    # dock NPCs delivered into Prison Exile Island, the exact cross-build-
    # order defect this module's own docstring says it exists to prevent.
    # This module still only builds the CENSUS branch for the source it has
    # always built it for; a scene with any OTHER named source (today: just
    # "bg0002_roster") still gets the CLEAR branch below, UNCHANGED from
    # before this round - wiring a live in-session CROSSING handoff for
    # Bg0002 is M2-shaped work (paused, PANYA-DECISION 2026-08-27 20:10) and
    # is deliberately NOT done here.  M1-P's own Bg0002 population is built
    # by ``world_population_bg0002.build_bg0002_population`` on the LOGIN
    # path, which this module does not touch.
    if population_source(scene) != CENSUS_SOURCE:
        pc, frame = build_clear_generation(legacy)
        source = population_source(scene)
        reason = (
            f"scene_{scene}_has_no_population_table" if source is None
            else f"scene_{scene}_source_{source}_has_no_crossing_handoff_yet"
        )
        return SceneHandoff(
            scene_id=scene,
            kind=KIND_CLEAR,
            reason=reason,
            label=LABEL_CLEAR.format(scene),
            actor_count=0,
            pc=pc,
            frame=frame,
            reapply_ms=CLEAR_REAPPLY_MS,
            dispatch_slot=SLOT_BEFORE_TELEPORT,
            generation=None,
        )
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
        "membership_reset_indices": handoff.membership_reset.population_indices,
        "membership_reset_anchor": (
            handoff.membership_reset.population_refresh_anchor),
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


# --------------------------------------------------------------------------
# WHO IS STILL ON THE CLIENT WHEN THE PLAYER LANDS SOMEWHERE ELSE
# --------------------------------------------------------------------------
#
# ROUND 2pdf6j (LANE-A, M2).  Everything above composes the frame that ENDS
# the state this section MEASURES.  Until that frame has a caller, the
# client keeps the collection it was sent at login, and nothing reported who
# that leaves standing next to a player who crossed - BY NAME.
#
#     THE FIRST DRAFT OF THAT SENTENCE SAID "this project has never once
#     written down who", AND IT WAS TOO WIDE (pf-adversary, round 2pdf6j,
#     D11).  ``world_density.m1_console_line(legacy, (0, 0, 0))`` already
#     prints ``census_within_500u=0 1000u=0 2000u=4 5000u=11`` at HEAD - the
#     same bands, the same table.  What is new here is WHICH ACTORS (names,
#     identities, per-member distances) and, more load-bearing, that the
#     answer is filtered through the membership the client was ACTUALLY
#     SENT rather than the whole frozen table.  That difference is not
#     cosmetic: see the count note below.
#
# THE COUNT NOTE, AND IT CORRECTS THIS SECTION'S OWN FIRST DRAFT.  The frozen
# table carries 115 placements; ``build_world_population`` ships 108 of them
# (7 rows - 0 "Navy Transfer", 75, 86, 87, 145 "Filet", 147, 148 - never
# reach the client).  Distances are identical either way inside 2000u of the
# decreed sea anchor, but at 5000u the table says 11 and the census says 10:
# placement 145 at 2530.1u is a table row the client was never sent.  A
# reader who takes 115, or takes ``world_density``'s 11, as "actors the
# player can see" is reading the data-table layer as the wire layer
# (pf-adversary, round 2pdf6j, D2).  This is why ``held_indices`` is
# required and why passing the whole table is a caller error, not a default.
#
# AND THE ANCHOR THE HEADLINE NUMBER BELONGS TO.  4-within-2000 is a fact
# about the point the server sends today, ``(0, 0, 0)``, which is an OWNER
# DECREE and not a measured spawn - the registry's own scene-17 entry
# records that the decreed z sits OUTSIDE the ground band its placements
# measure ([746.04, 1272.74]).  Move the landing anywhere inside that band
# and the answer is 5, not 4 (Kaim joins at ~819u), and the vertical
# separation between player and crowd collapses from ~930 units to 0-200
# (pf-adversary, round 2pdf6j, D1).  So: [MEASURED from the frozen table, AT
# A DECREED ANCHOR].  Both halves of that label are load-bearing.
#
# THE PREMISE, AND IT IS THE SAME [INFERENCE] THE MODULE DOCSTRING ALREADY
# CARRIES, NOT A NEW ONE: that the client KEEPS remote actors across a
# TeleportVital.  Nothing in this project has measured it.  If the client
# clears them itself, every number these functions produce is an upper
# bound of zero and the module docstring's whole premise retires with it -
# which is why the attended ticket this round opens (GT-147) is written to
# be informative BOTH ways rather than to confirm this one.
#
# WHAT IS NOT INFERRED: the placements, their names, their coordinates, and
# the distance arithmetic.  Those come from the same frozen table the census
# ships over, through the same loader, with the same hash guard.


@dataclass(frozen=True)
class StowawayMember:
    """One census actor, and how far it is from where the player lands."""

    placement_index: int
    actor_identity: int
    source_name: str
    distance: float
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class StowawayView:
    """What the client is still holding, measured against an arrival point.

    ``reason`` is ``None`` on a computed view and carries a named refusal on
    one that could not be computed.  ``held`` is the membership that was
    ACTUALLY sent - never a default, never the whole table assumed - which is
    why a caller with no record of it gets a refusal instead of a number.
    """

    anchor: tuple[float, float, float]
    radius: float
    held: int
    within_radius: tuple[StowawayMember, ...]
    nearest: StowawayMember | None
    reason: str | None = None

    @property
    def computed(self) -> bool:
        return self.reason is None


def _require_held_indices(held_indices: Any) -> tuple[int, ...]:
    """The membership the client was sent, or a raise naming what came in.

    Deliberately strict about ``None``: "the caller does not know what it
    sent" and "the caller sent nothing" are different facts, and a default
    of the whole census here would turn the first into the second silently -
    the exact shape of error this lane's own modules have been caught in
    twice (see the module docstring's [INFERENCE] paragraph).
    """
    if held_indices is None:
        raise ValueError("no recorded census membership to measure")
    if type(held_indices) not in (tuple, list):
        # The message names both accepted shapes, because the check does.
        # (pf-adversary, round 2pdf6j, D11: the first draft said "must be a
        # tuple, not list" while accepting lists - a refusal message that
        # contradicts its own check teaches the next reader the wrong rule.)
        raise ValueError(
            "census membership must be a tuple or list, not "
            f"{type(held_indices).__name__}"
        )
    out = []
    for value in held_indices:
        # ``type(value) is not int`` already rejects ``True``/``False``,
        # since ``type(True) is bool``.  An ``isinstance(value, bool)``
        # conjunct here would be a line that can never run (pf-adversary,
        # round 2pdf6j, D6 - it was in the first draft and is deliberately
        # not here now).
        if type(value) is not int:
            raise ValueError("census membership must be placement indices")
        out.append(value)
    # A repeated index is drift, not a bigger crowd: it would report
    # ``held=3`` and print one actor's name three times.  Refused by name
    # rather than silently de-duplicated, so the caller learns its
    # membership is wrong instead of getting a tidied answer (pf-adversary,
    # round 2pdf6j, D6).
    if len(set(out)) != len(out):
        raise ValueError("census membership repeats a placement index")
    return tuple(out)


def _require_report_radius(radius: Any) -> float:
    """The report band, as a float that is safe to format and compare.

    ``float()`` is where this has to happen and it has to happen ONCE:
    ``10 ** 400`` is an ``int``, is non-negative, and equals itself, so a
    shape check alone passes it straight through to an ``OverflowError``
    deeper in - including inside the fail-closed handler that exists to
    catch it, which is how the first draft of this section broke its own
    "does not raise, ever" contract (pf-adversary, round 2pdf6j, D4).
    """
    if type(radius) not in (int, float):
        raise ValueError(
            f"the report radius must be a finite distance, not {radius!r}"
        )
    try:
        value = float(radius)
    except (OverflowError, ValueError) as error:
        raise ValueError(
            "the report radius is outside the range of a float"
        ) from error
    if value != value or value in (float("inf"), float("-inf")) or value < 0:
        raise ValueError(
            f"the report radius must be a finite distance, not {radius!r}"
        )
    return value


def stowaways_near(
    legacy: Any,
    held_indices: Any,
    arrival_anchor: Any,
    *,
    radius: float = STOWAWAY_REPORT_RADIUS,
) -> StowawayView:
    """STRICT.  Which of the actors the client holds are near ``arrival_anchor``.

    ``held_indices`` is the census membership the client was actually sent
    (``runtime.py`` keeps it as ``world_census_indices``); a placement index
    in it that the frozen table does not carry is a refusal, not a skip,
    because a membership and a table that disagree is drift and this is the
    only place that would see it.

    Distance is the plain 3-space distance between the placement's own
    coordinate and the arrival point.  BOTH ARE READ IN THE CLIENT'S ONE
    COORDINATE SPACE, WHICH IS THE ASSUMPTION WORTH NAMING: the scene
    changes, the numbers on the wire do not get remapped by anything this
    project has found, so an actor at bg0001's (-507, -616, 931) is 1,227
    units from a player standing at the sea scene's (0, 0, 0) unless the
    client re-bases coordinates per scene - which nobody has measured
    either way.

    Not for the frame path.  See :func:`stowaways_on_crossing`.
    """
    anchor = _require_anchor(arrival_anchor)
    band = _require_report_radius(radius)
    membership = _require_held_indices(held_indices)
    from .population import load_port_royal_placements

    by_index = {
        placement.placement_index: placement
        for placement in load_port_royal_placements(legacy)
    }
    members = []
    for index in membership:
        placement = by_index.get(index)
        if placement is None:
            raise ValueError(
                f"census membership names placement {index}, which the frozen "
                "table does not carry"
            )
        distance = (
            (placement.x - anchor[0]) ** 2
            + (placement.y - anchor[1]) ** 2
            + (placement.z - anchor[2]) ** 2
        ) ** 0.5
        members.append(StowawayMember(
            placement_index=placement.placement_index,
            actor_identity=placement.actor_identity,
            source_name=str(placement.source_name),
            distance=distance,
            x=placement.x,
            y=placement.y,
            z=placement.z,
        ))
    members.sort(key=lambda member: (member.distance, member.placement_index))
    near = tuple(member for member in members if member.distance <= band)
    return StowawayView(
        anchor=anchor,
        radius=band,
        held=len(members),
        within_radius=near,
        nearest=members[0] if members else None,
    )


def stowaways_on_crossing(
    legacy: Any,
    held_indices: Any,
    arrival_anchor: Any,
    *,
    radius: float = STOWAWAY_REPORT_RADIUS,
) -> StowawayView:
    """The frame-path entry point.  It raises nothing a composition can produce.

    Same contract, and for the same reason, as :func:`handoff_on_crossing`:
    the block a crossing is reported from has no ``except`` of its own, and a
    REPORT that kills frame handling would be a worse bug than the state it
    was reporting on.  A view that could not be computed comes back with
    ``reason`` set and no members.

    THE TWO IT STILL LETS THROUGH, deliberately and identically to
    ``handoff_on_crossing``: ``KeyboardInterrupt`` and ``SystemExit``.  The
    first draft of this docstring said "does not raise, ever", which was
    false twice over (pf-adversary, round 2pdf6j, D4): those two, and -
    genuinely a defect, now fixed - an ``OverflowError`` from ``float()``
    on a huge int radius, raised INSIDE this handler while building the
    refusal.  Every field this handler touches is now built defensively.
    """
    try:
        return stowaways_near(
            legacy, held_indices, arrival_anchor, radius=radius
        )
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as failure:  # noqa: BLE001 - the contract is absolute
        try:
            anchor = _require_anchor(arrival_anchor)
        except BaseException:  # noqa: BLE001 - the anchor is what failed
            anchor = (0.0, 0.0, 0.0)
        try:
            band = _require_report_radius(radius)
        except BaseException:  # noqa: BLE001 - the radius is what failed
            band = 0.0
        return StowawayView(
            anchor=anchor,
            radius=band,
            held=0,
            within_radius=(),
            nearest=None,
            reason="stowaways_not_measured:{0}:{1}".format(
                _ascii_safe(type(failure).__name__, 40), _ascii_safe(failure)
            ),
        )


def stowaway_console_line(view: Any) -> str:
    """One ASCII line naming who is near the landing point, or why nobody knows.

    The names are placement source names from the frozen table, so they are
    what a tester reads off a nameplate; they go through ``_ascii_safe`` and
    have their spaces replaced, because a console line a grep cannot field-
    split is a line the WIRED-v2 style checks in this project cannot use.
    """
    try:
        if not isinstance(view, StowawayView):
            raise TypeError(f"not a StowawayView: {type(view).__name__}")
        if view.reason is not None:
            return _ascii_safe(
                "WORLD_POP_STOWAWAYS unmeasured reason=" + view.reason, 400
            )
        listed = ",".join(
            "{0}@{1:.1f}".format(
                _ascii_safe(member.source_name, 40).replace(" ", "_") or "unnamed",
                member.distance,
            )
            for member in view.within_radius[:4]
        )
        return _ascii_safe(
            "WORLD_POP_STOWAWAYS anchor=({0:.3f},{1:.3f},{2:.3f}) held={3} "
            "radius={4:.1f} within={5} nearest={6} names={7}".format(
                view.anchor[0], view.anchor[1], view.anchor[2],
                view.held, view.radius, len(view.within_radius),
                "none" if view.nearest is None
                else "{0}@{1:.1f}".format(
                    _ascii_safe(view.nearest.source_name, 40).replace(" ", "_"),
                    view.nearest.distance,
                ),
                listed or "none",
            ),
            400,
        )
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as failure:  # noqa: BLE001 - see the docstring
        return (
            "WORLD_POP_STOWAWAYS unreportable reason="
            + _ascii_safe(type(failure).__name__, 40)
        )
