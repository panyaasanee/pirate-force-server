"""The way back from the sea, captured at the moment of departure - LANE-A, M2.

WHAT THIS MODULE IS FOR.  ``world_scene_entry.return_ticket`` has been able to
name the row that walks a character home since round ``qumhmf``, and its own
docstring states the condition nobody has met since:

    PASS ``remembered`` IF YOU HAVE IT, AND CAPTURE IT BEFORE THE TRIP.  With
    no argument this returns the pinned Port Royal entry point, which is where
    a NEW character starts and not where this one was standing.

Nothing in this tree captures it.  The one crossing a player can actually make
today - Columbus's option 1, into scene 17 - calls
``columbus_quest_dispatch.dispatch_columbus_quest3021`` with a registry and an
emit function and nothing else, so the only ticket that can be minted for that
trip is the fallback: the spawn a NEW character gets.  This module is the
missing half.  It captures the departed-from row, reports what the ticket for
this crossing actually is, and MEASURES THE DIFFERENCE between the two, so the
cost of not having the row is a number on the console instead of a sentence in
a docstring.

WHAT IT DOES NOT CLAIM, AND THIS IS THE HALF A READER WILL WANT.

1. IT DOES NOT SEND ANYTHING.  No frame, no write, no scheduling.  It composes
   a ``Position`` and a console line.  Sending a live character back across a
   scene boundary needs the transition sequence ``RE-077`` still has open,
   which is the same wall ``world_m2_sea_destination`` stops at.
2. IT DOES NOT CLAIM THE SEA IS A TRAP TODAY.  It is not: scene 17 carries
   ``persist_position_allowed = false`` in the registry (round ``jafskv``,
   from GT-106's own finding), so the durable row keeps saying Port Royal for
   the whole trip and a relog already puts the character back on land.  What
   this module is about is WHERE - a relog restores whatever the row last
   held, and the fallback ticket does not.
3. IT DOES NOT DECIDE WHO WRITES THE ROW BACK.  That is the runtime's, which
   is the chief's file.  This makes the row available and says so out loud.

THE ONE NUMBER THIS ADDS.  ``drift`` is the distance between the row the
character departed from and the pinned home entry the fallback would hand
back.  For a character standing on the V135 spawn it is 0.0 - the fallback is
correct for them, which is exactly why this gap has stayed invisible, and it
is measured here rather than asserted (the pinned test drives it).
``return_ticket``'s own docstring names 731 units for a character that
departed from the attended GT-045 spawn; that number is QUOTED, not re-derived
by this round, and this module holds no GT-045 row to check it with.  A
console reader can therefore tell "the fallback is fine for
this character" from "the fallback would move this character" without knowing
either coordinate.
"""
from __future__ import annotations

import math

from . import world_scene_entry
from . import world_scene_travel
from .model import Position
from .world_scene_travel import HOME_SCENE_ID


# Convention marker: this module is not a scenario and is not behind a flag.
production_allowed = True
test_only = False

# What the console prints when the crossing was dispatched without the row the
# character departed from.  It is a NAMED absence, not a silent fallback: the
# ticket still exists (the pinned home entry), and the reader is told that the
# ticket is the generic one rather than this character's.
NO_DEPARTURE_ROW = "call_site_passed_no_departure_row"

# Where the ticket came from.  Three values, and they are three different
# facts about the same trip.
SOURCE_DEPARTED_ROW = "departed_row"
SOURCE_PINNED_HOME_ENTRY = "pinned_home_entry"
SOURCE_NONE_OWED = "none_owed"


class DepartureRowRefused(ValueError):
    """A row offered as "where this character departed from" was not one."""


def remember_departure(position: object) -> Position:
    """Validate and return the row a character is leaving home from.

    RAISES.  This is the strict half, for a caller that has a row and wants to
    know if it is usable.  The crossing path does not call this directly; it
    goes through :func:`return_leg_console_line`, which never raises, because
    a console line composed on the frame path must not be able to end a boot.

    A departure row must be in the home scene.  A row already naming another
    scene is not a departure from home, and accepting one would let a caller
    hand back a ticket that walks the character into the scene they are trying
    to leave - which is the one failure this module exists to prevent.
    """
    if type(position) is not Position:
        raise DepartureRowRefused("a departure row must be a Position")
    if position.scene_id != HOME_SCENE_ID:
        raise DepartureRowRefused(
            f"a departure row must be scene {HOME_SCENE_ID}, "
            f"not scene {position.scene_id}"
        )
    for axis in (position.x, position.y, position.z):
        if type(axis) not in (int, float) or not math.isfinite(float(axis)):
            raise DepartureRowRefused(
                "a departure row must carry finite coordinates")
    return position


def drift_from_pinned_home(
    departed: Position,
    *,
    registry=None,
) -> float:
    """How far the fallback ticket would move this character, in units.

    Three dimensions, not two: the fallback resets nothing else about the row
    but it does move z, and a character put back 900 units above where they
    left is not "back".
    """
    remembered = remember_departure(departed)
    home = world_scene_travel.home_return_position(registry)
    return math.sqrt(
        (remembered.x - home.x) ** 2
        + (remembered.y - home.y) ** 2
        + (remembered.z - home.z) ** 2
    )


def return_leg(
    entry,
    *,
    departed: Position | None = None,
    registry=None,
) -> dict:
    """One flat report of the way home this crossing owes.

    ``owed`` is ``world_scene_entry``'s answer, not this module's: a ticket is
    owed for every non-home destination.  ``source`` says which row the ticket
    is, and ``drift`` is present only when both rows exist to compare - it is
    ``None`` rather than 0.0 when there is nothing to compare, because 0.0 is
    a real and meaningful answer here (the character departed from the pinned
    entry) and must not be reachable by a caller that measured nothing.
    """
    ticket = world_scene_entry.return_ticket(
        entry, remembered=departed, registry=registry)
    if ticket is None:
        return {
            "owed": False,
            "source": SOURCE_NONE_OWED,
            "reason": None,
            "position": None,
            "drift": None,
        }
    if departed is None:
        return {
            "owed": True,
            "source": SOURCE_PINNED_HOME_ENTRY,
            "reason": NO_DEPARTURE_ROW,
            "position": ticket,
            "drift": None,
        }
    return {
        "owed": True,
        "source": SOURCE_DEPARTED_ROW,
        "reason": None,
        "position": ticket,
        "drift": drift_from_pinned_home(departed, registry=registry),
    }


def return_leg_console_line(
    entry,
    *,
    departed: Position | None = None,
    registry=None,
) -> str:
    """The ``WORLD_M2_RETURN_LEG`` line, for every crossing, every boot.

    NEVER RAISES, FOR THE SAME REASON THE STOWAWAY LINE NEVER RAISES.  This is
    composed inside the dispatch that sends a player to sea; a report that can
    throw would turn a reporting gap into a lost crossing.  Every failure
    becomes a line saying what failed, and the line is 7-bit ASCII so the
    cp874 bridge console can print it.
    """
    try:
        report = return_leg(entry, departed=departed, registry=registry)
    except Exception as error:  # a report must not be able to end a boot
        return (
            "WORLD_M2_RETURN_LEG unmeasured reason=refused:"
            + type(error).__name__
        )
    try:
        if not report["owed"]:
            return "WORLD_M2_RETURN_LEG owed=NO source=" + SOURCE_NONE_OWED
        home = report["position"]
        drift = report["drift"]
        return (
            "WORLD_M2_RETURN_LEG owed=YES source={0} scene={1} "
            "xyz=({2:.3f},{3:.3f},{4:.3f}) heading={5:.3f} drift={6}".format(
                report["source"], home.scene_id, home.x, home.y, home.z,
                home.heading,
                "{0:.1f}".format(drift) if drift is not None
                else "unmeasured:" + str(report["reason"]),
            )
        )
    except Exception as error:
        return (
            "WORLD_M2_RETURN_LEG unmeasured reason=uncomposable:"
            + type(error).__name__
        )
