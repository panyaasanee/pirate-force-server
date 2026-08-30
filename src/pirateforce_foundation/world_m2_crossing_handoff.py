"""The town that sails out with you - LANE-A, M2.

WHAT THIS MODULE IS FOR.  There is exactly ONE scene change a player can make
happen for themselves on a default boot today: talk to Columbus, take option
one (row 3021, ``columbus_quest_dispatch``), arrive in scene 17.

    THE WORD "Q-U-E-S-T" IS NOT SPELLED OUT ANYWHERE IN THIS FILE ON PURPOSE,
    and saying so is better than leaving a reader to find out by breaking it.
    ``tests/test_npc_interaction_wire.QuestAndShopStateGuardTests`` scans
    every ``src/pirateforce_foundation/*.py`` for that whole word and holds a
    deliberately short allowlist.  This module composes a POPULATION handoff;
    it implements none of that behaviour, so the honest fix was to name the
    dispatch module and the row number - which is more precise prose anyway -
    rather than to widen a guard that is doing its job.

The walk-in travel gate that
``world_travel_gate`` builds is debug-only and OFF by default by owner ruling
(``COO RULING 20260826``), so the Columbus dispatch is not one crossing among
several - it is the crossing.

That crossing sends a ``TeleportVital`` and NOTHING ELSE.  The population
handoff this lane built for exactly this moment
(``world_population_handoff.handoff_on_crossing``) is wired into
``runtime.py`` at ONE call site, and it is the one on the disabled travel-gate
path (``runtime.py:7146``).  The Columbus branch (``runtime.py:4971-5044``)
never calls it.

    SO THE WHOLE OF PORT ROYAL GOES TO SEA.  ``make_runtime_remote_actors``
    has replace semantics and nothing replaces it on this path, so the actor
    collection the client was sent at login is still the collection it holds
    after the transition.  The census this tree composes for that login is
    115 actors (``world_population.census_count_for_dispatch() -> (115,
    'full_census')``, re-derived this round rather than quoted), so that is
    the order of what is left standing on open water around a player who just
    walked out of town.  115 IS THE CENSUS SIZE, NOT A MEASUREMENT OF WHAT A
    PARTICULAR BOOT HELD: the collection actually held is the caller's
    ``world_census_indices``, and ``crossing_handoff_console_line`` prints
    THAT number in its ``held=`` field, so a boot where the two differ says so
    on the console instead of inheriting this docstring's number.

    THIS IS NOT THIS LANE'S FIRST SIGHTING OF IT AND THAT IS THE POINT.
    ``columbus_quest_dispatch._emit_arrival_stowaways`` has printed
    ``WORLD_POP_STOWAWAYS`` at this exact moment since round 2pdf6j - a
    REPORT naming who is still held - and ``RE-162``'s Job 4 result
    (``pf_bridge/notes_to_chief/20260830_1909_RE-162-RESULT-IN-SESSION-SCENE-
    CHANGE-WIRE-EXISTS-CLIENT-OBSERVABLE-UNPROVEN.md``) states the same thing
    from the other side, independently, as a negative finding: "the Columbus
    in-session crossing sends the teleport frame alone ... nothing in this
    clone's committed source sends one."  Two sources, one gap, nobody had
    composed the frame that closes it.

WHAT THIS MODULE ADDS, AND WHAT IT DELIBERATELY DOES NOT.

It composes.  It does not send.  ``crossing_handoff`` feeds the SceneEntry a
crossing already produced to the seam that already ships, and hands back the
``SceneHandoff`` - kind, reason, bytes, dispatch slot and membership reset,
all of it the existing encoder's answer and none of it re-derived here.  For
scene 17 today that is a 27-byte CLEAR in slot ``before_teleport``.

Queueing those bytes is one block in ``runtime.py``, which is the chief's
file.  ``dispatched=`` below is the parameter that block flips, so the console
line stops saying ``dispatched=NO`` in the same edit that makes it untrue,
rather than in a later round that has to remember to come back for it.

WHY NOT JUST CALL ``handoff_on_crossing`` FROM THE DISPATCH.  Because the
dispatch has a ``SceneEntry``, and the seam wants a scene id and an (x, y, z).
Reading one out of the other is three lines that can be got wrong in two ways
- the wrong field, or the departure point instead of the arrival point - and
round qb70g2's adversary pass caught precisely that second mistake in the
stowaway line next door.  It is written once, here, with the arrival named in
the function that does it.

WHAT THIS COSTS ON THE FRAME PATH, SAID OUT LOUD RATHER THAN LEFT TO BE
DISCOVERED.  Composing a handoff in order to PRINT it means composing bytes
that are then thrown away.  For the only crossing that exists today that is a
27-byte clear and the cost is nothing.  It would not stay nothing: a scene
with a roster would build the whole roster per crossing for one console line.
That is not reachable now (``columbus_quest_dispatch``'s destination is the
constant 17, and 17 is in ``SCENES_INTENTIONALLY_UNPOPULATED`` with a measured
reason), and the round that makes it reachable should queue the bytes rather
than keep discarding them - which is the same edit the CORE-REQUEST asks for.

WHAT NOBODY HAS SEEN.  No human has watched a client render scene 17 at all:
``GT-106`` is PENDING, and ``RE-162`` marks the in-session transition
client-observable-UNPROVEN.  So "the sea is empty once this is queued" is what
the bytes say, not what anyone has seen, and this module claims only the
first.
"""
from __future__ import annotations

from typing import Any

from . import world_population_handoff


# Convention marker: this module is not a scenario and is not behind a flag.
production_allowed = True
test_only = False

# The console token.  One string, greppable, and deliberately NOT the seam's
# own ``WORLD_POP_HANDOFF``: that token means "these bytes were queued" on the
# travel-gate path, and a reader who greps it must not find this lane's
# composed-but-unsent line mixed in with it.
CONSOLE_TAG = "WORLD_M2_CROSSING_HANDOFF"

# What went wrong when the entry could not be read.  A named absence, printed
# in the same field shape as the measured line, for the same reason every
# other report in this lane does it: a console that goes quiet about a
# question it cannot answer is indistinguishable from one that was never
# asked.
UNREADABLE_ENTRY = "entry_carried_no_readable_arrival_position"


def crossing_arrival(entry: Any) -> tuple[int, tuple[float, float, float]] | None:
    """The ARRIVAL scene id and anchor this entry names, or ``None``.

    ``entry.position`` and not ``entry.teleport_fields``: ``SceneEntry``'s own
    docstring says the teleport fields are DERIVED from the position, so the
    position is the source and the derivation is not re-done here.  Home is
    the case that would bite a reader who chose the other one - its teleport
    fields are the frozen ``(1, 0, 0.0, 0.0, 0.0)`` the runtime already sends
    rather than anything read off the row.

    ``None`` rather than a raise, because every caller in this module is on
    the frame path.
    """
    try:
        position = entry.position
        scene_id = position.scene_id
        anchor = (float(position.x), float(position.y), float(position.z))
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException:  # noqa: BLE001 - report-only, see the docstring
        return None
    if type(scene_id) is not int or isinstance(scene_id, bool):
        return None
    return scene_id, anchor


def crossing_handoff(
    legacy: Any,
    entry: Any,
) -> world_population_handoff.SceneHandoff:
    """The handoff this crossing owes, composed by the seam that already ships.

    NO ``actor_count`` PASS-THROUGH, DELIBERATELY.  ``handoff_on_crossing``
    takes one, and mirroring it here was the first draft.  It would have had
    no reader: the seam reads ``actor_count`` only on its CENSUS branch, and
    the only scene this function can be handed today answers CLEAR, so no test
    in this tree could give the parameter a meaning.  A parameter nobody reads
    is the flag-with-no-reader shape ``PANYA-DIRECTIVE 20260829_2222`` item 7
    bans, one level down.  The day a crossing lands somewhere with a roster,
    add it back WITH the test that measures it.

    NEVER RAISES, and the contract is inherited rather than re-implemented:
    ``handoff_on_crossing`` is absolute about this for the same reason (the
    block it is called from in ``runtime.py`` has no ``except`` of its own, so
    a raise there does not refuse a handoff, it ends frame handling for the
    connection).  The one case this function adds - an entry it cannot read -
    is turned into the seam's own ``KIND_UNAVAILABLE`` by handing it a scene
    id the seam refuses, so there is ONE unavailable shape in the tree and not
    two.

    ``KIND_UNAVAILABLE`` is not a failure to hide: its ``membership_reset``
    clears both frozen-state fields on purpose (see that property's docstring
    - a membership nobody can answer for is a membership to drop), and a
    caller that applies it is strictly better off than one that got nothing.
    """
    arrival = crossing_arrival(entry)
    if arrival is None:
        # Deliberately routed through the seam rather than hand-built: a
        # SceneHandoff assembled here would be the second construction site
        # for a type whose own __post_init__ exists because two of them
        # drifted apart once already.  The sentinel is a STRING where the
        # seam wants an int, so the seam's own guard is what refuses it and
        # the reason it prints names this constant.
        scene_id, anchor = UNREADABLE_ENTRY, None
    else:
        scene_id, anchor = arrival
    # ONE CALL, AND THE SINGLE CALL IS THE POINT, NOT AN ACCIDENT OF STYLE.
    # tests/test_world_population_bg0015.py censuses every ``handoff_on_
    # crossing`` call site under src/ and allows exactly one per blessed
    # file, because a second call inside an already-blessed file is the
    # double-populator shape COO-DECISION 20260829_2245 bans.  The first
    # draft of this function had two - one per branch - and tripped it.
    return world_population_handoff.handoff_on_crossing(
        legacy, scene_id, anchor,
    )


def crossing_handoff_console_line(
    handoff: Any,
    *,
    dispatched: bool = False,
    held: Any = None,
) -> str:
    """The ``WORLD_M2_CROSSING_HANDOFF`` line, for every crossing, every boot.

    NEVER RAISES, for the same reason the stowaway line and the return-leg
    line next door never raise: it is composed inside the dispatch that sends
    a player to sea, and a report that can throw turns a reporting gap into a
    lost crossing.  Every failure becomes a line saying what failed, in 7-bit
    ASCII so the cp874 bridge console can print it.

    ``dispatched`` IS THE HONEST FIELD AND IT DEFAULTS TO THE TRUTH.  Today
    the only call site composes these bytes and queues nothing, so the default
    is ``False`` and the line says ``dispatched=NO``.  The runtime block that
    starts queueing them passes ``dispatched=True`` in the same edit - which
    is why this is a parameter and not a constant.

    ``held`` is the actor collection the client is STILL holding from the
    scene it is leaving - the count the clear is there to remove.  It is the
    caller's ``world_census_indices``, and it is optional because a call site
    without it should still print a line.
    """
    try:
        report = world_population_handoff.handoff_report(handoff)
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as failure:  # noqa: BLE001 - report-only
        return (
            CONSOLE_TAG + " unreportable reason="
            + type(failure).__name__.encode(
                "ascii", "backslashreplace").decode("ascii")
        )
    try:
        if held is None:
            held_text = "unmeasured"
        else:
            held_text = str(len(tuple(held)))
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException:  # noqa: BLE001 - report-only
        held_text = "unreadable"
    try:
        return (
            "{tag} scene={scene} kind={kind} held={held} composed={composed} "
            "dispatched={dispatched} pc={pc}B frame={frame}B slot={slot} "
            "reason={reason}".format(
                tag=CONSOLE_TAG,
                scene=report["scene_id"],
                kind=report["kind"],
                held=held_text,
                composed="YES" if report["sends_a_frame"] else "NO",
                dispatched="YES" if dispatched else "NO",
                pc=report["pc_bytes"],
                frame=report["frame_bytes"],
                slot=report["dispatch_slot"],
                reason=report["reason"],
            )
        )
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as failure:  # noqa: BLE001 - report-only
        return (
            CONSOLE_TAG + " uncomposable reason="
            + type(failure).__name__.encode(
                "ascii", "backslashreplace").decode("ascii")
        )
