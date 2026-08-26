"""The door out of town - LANE-A build order BUILD-002, second half (M2).

WHAT THIS MODULE IS FOR.  Every scene change this project has ever produced
happened at login: the character's persisted row said where to be, and the boot
put them there.  ``COO-DECISION 20260826_0150`` ruled that waking up in another
map is not travel, and that ``M2`` closes only when a PLAYER makes their own
scene change happen.  This module is that mechanism.  A gate is a place in one
scene; a live player who STOPS in it is sent to another scene, and a player
who walks back to where they landed and stops there is sent home.

    STOPS, NOT WALKS THROUGH, AND THAT WORD IS THE DESIGN.  The first draft of
    this module fired on the first report inside the zone.  The adversary pass
    of round 4fhdxv pointed out where that puts the door: 993 walking units
    from the position an attended run actually found the character on, which
    is the middle of the walk ``GT-078`` asks the owner to take in order to
    count NPCs.  A door that opens because somebody walked past it on another
    errand is a trapdoor, and it would have eaten the M1 acceptance run on the
    evening M1 was due.  So a crossing is not enough: the player has to report
    the SAME position ``dwell_reports`` times running.  In the one authentic
    walk this project holds, every walking report moved, and four stationary
    runs exist - of 3, 6, 2 and 3 identical reports.  The door needs FOUR
    identical reports (the one that arrives, then three that do not move), so
    exactly ONE of those four pauses would have opened it.  That is the right
    way round: an incidental pause usually does not reach the threshold and a
    deliberate stop does, which is the discrimination this rule exists for.
    (Round 4fhdxv pinned "three runs of 3, 6 and 3" and read the threshold as
    three reports; the adversary pass of round e7q6yy recounted both.)  It is
    also the only thing in this design that a player DOES rather than has done
    to them.

    NOTHING HERE IS BEHIND A FLAG.  There is no scenario file to load and no
    argument to pass.  What stands between this module and a player is one call
    site in ``runtime.py``, which is the chief's file - see ``CORE-REQUEST-004``
    in the round's PR body for the exact call.  Until that call exists a player
    walks past Columbus and nothing happens.

    COO RULING 20260826 SUPERSEDES THE PARAGRAPH ABOVE, AND IS THE REASON THE
    PARAGRAPH STAYS RATHER THAN GETS REWRITTEN.  The owner confirmed, verbatim,
    that this walk-in-and-stop mechanic does not exist in the real game - the
    real door out of town is Columbus, a sea map, a dock, and a captain-report
    confirm window - and ruled: pull this gate out of the M2/production
    acceptance criteria immediately; do not delete the file or the code; keep
    it debug-only and OFF by default; never use it as an M2 acceptance
    criterion again.  So as of this ruling "no flag" no longer describes this
    module's DEFAULT reachability, only its mechanism: :func:`lane_reason` is
    the flag now, its default (``debug_enabled=False``) keeps every door shut
    for every session regardless of what else is or is not selected, and a
    caller has to hand ``debug_enabled=True`` - sourced from an explicit
    human opt-in such as a ``--enable-travel-gate-debug`` CLI flag, never from
    a default - to make ``scenario_stand_down`` (below) speak again as the
    secondary guard it always was.  Everything else in this module - the
    gates, the dwell rule, the ping-pong guard, the two-phase crossing - is
    untouched; only the default reachability changed.

THE THREE MEASURED FACTS THIS IS BUILT ON, AND THE ONE THAT NEARLY BROKE IT.

1. ``RE-077`` (result letter ``20260826_0120``) pinned the client's transition
   sequence from the shipped image: a live client in ``StateRunTime`` or
   ``StateNavigation`` that receives a ``TeleportVital`` whose target scene is
   nonzero builds ``cStateSwitchScene``, looks up
   ``SCENE_NAME[n_ID=scene].s_MODLE_ID``, and loads that model.  A row miss
   yields an empty model id, the loader refuses, and the state machine parks at
   status 2.  THERE IS NO FALLBACK, AND THE TICKET FORBIDS ADDING ONE: the
   shipped client fails that lookup deliberately.  This module therefore
   resolves every destination against the pinned registry AT LOAD TIME and
   refuses to build a gate whose destination is not pinned, so the movement
   path can never be the first place a bad scene id is discovered.

2. The server already sees the player walk.  ``TargetPosVital`` reaches
   ``runtime.py:3949`` on the default path - no flag, no scenario - and that
   call site writes the durable position row.  A walk-in trigger needs no new
   packet and no client change; it reads a stream that is already flowing.

3. WHERE A PLAYER LANDS IS NOT KNOWN, AND THE TWO SOURCES DISAGREE.
   ``V112`` disproved at runtime that the LOGIN/bootstrap ``TeleportVital``
   target vec3 positions the local actor - the client kept reporting
   ``(0,0,931)``.  But ``V137``
   (``reports/PF_RE_V137_MARKER1_TeleportVital_Transport_Pass_20260815.md``,
   carried in ``docs/FUNCTIONAL_COVERAGE.json`` as ``teleport_transport``
   ``runtime_pass``) recorded the opposite for a POST-INIT, same-connection
   ``TeleportVital`` v4 - the shape this gate emits - where the client's own
   coordinate UI reported the server's target and its next ``TargetPosVital``
   was byte-exact.  An earlier draft of this docstring cited only V112 and
   generalized it; the adversary pass of round 4fhdxv caught that, and it was
   wrong.

   WHAT IS ACTUALLY UNKNOWN is narrower and still decides the design: neither
   observation crossed a SCENE boundary, and scene 278 carries ``n_MARKER = 0``
   - no authored arrival point at all.  Nobody in this project has measured
   where a player stands after a cross-scene switch.  So the return gate is
   anchored on the first position the client itself reports after the jump,
   because that is the one coordinate in that scene anybody will have
   observed, and because being wrong about it costs a player their way home.

THE PING-PONG THIS WOULD OTHERWISE BE.  Send a player to another scene, write
the row, and the reports keep coming - first with old-scene coordinates while
the client is still loading, then with new ones.  A return gate sitting at the
arrival point sees the arrival report, fires, and sends the player back; the
departure gate then sees them home and fires again.  Two scenes, forever, at
walking speed.  The rule that kills it is uniform and has no exceptions: AFTER
ANY SWITCH, EVERY GATE STARTS DISARMED, and a gate arms only on a report
further than its arm radius from its centre.  A player who lands inside a gate
is standing in a doorway that is not open yet.

WHAT SETTLES A TRANSIT.  While the client is still in the old scene it reports
old-scene coordinates, and the durable row already carries the new scene id, so
the scene id cannot tell the two apart.  What can is the size of the step: the
one authentic walk this project holds - 29 reports, recomputed from
``reports/move_cadence001_smoke/replay_output.txt`` rather than quoted from a
docstring - has a median step of 130.42 units (139.26 is the upper middle of
that even sample, which an earlier revision called the median) and a largest of
538.44, and the move-authority policy already pins 2000 units as the largest
single step an honest client can take.  The first report that jumps further than that is the
arrival.  If none does within the report budget, one ``WORLD_TRAVEL_STRANDED``
line names the row and the way back, and the ordinary rules resume.

THE DAMAGE THIS CAN DO, STATED HERE AND NOT ONLY IN THE PIN.  A departure
rewrites the durable row.  If the destination never loads, that row still says
278 and ``world_scene_entry`` will send the character there again on every
login.  Four recoveries exist and exactly ONE of them works without a human:
a session that opens with the player ALREADY in the destination anchors the
way home on their first report, so a relog turns a walled-in character into
one who can walk out and back and go home.  The other three need somebody:
the ``WORLD_TRAVEL_DEPART`` line prints the exact row to restore,
``world_scene_entry.return_ticket`` exists and is still unwired, and the
attended ticket restores the row at teardown.  THE AUTOMATIC ONE DOES NOT
COVER THE WORST CASE, and saying so is the point of this paragraph: if the
client cannot load the scene at all, the player can relog forever and still
see nothing, because walking out and back needs a scene to walk in.
``CHARTER-02`` rule 2 says a version that takes away what the last one could
do is damage, so a caller that wires this owes the character one of the four.

HOW A CALLER WIRES THIS, AND WHY IT IS THREE PLACES AND NOT ONE.  Round e7q6yy
rebuilt the seam around the three questions ``CORE-REQUEST-004`` left open,
because each of them was a good reason for the chief not to make the call:

    server start   preload()                        a bad pin fails the boot
    in the factory reason = scenario_stand_down(locals())
    each login     TravelGateSet.from_preloaded(    no file read, no raise
                       emit=..., inert_reason=reason)
    each report    departure = gates.observe(row)   nothing committed yet
                   persist(departure.arrival)
                   departure.confirmed_fields()     commits, and prints

``preload`` moves the refusal off the login path, where a broken pin used to
mean nobody could log in rather than nobody could travel.
``scenario_stand_down`` is the opt-in-lane guard written as a rule instead of
a list - THIS LANE IS THE NO-FLAG LANE, so any selected scenario shuts the
doors, including one no version of this file has heard of.  And a crossing is
handed over uncommitted so the console cannot say a player travelled before
the row that says so has been written.

WHAT THIS MODULE DELIBERATELY DOES NOT DO.  It composes no bytes and sends
nothing.  It returns the five arguments ``legacy.make_login_teleport`` takes and
the row to persist, and the caller owns both.  It does not populate the
destination: ``world_scene_travel.population_source`` answers ``None`` anywhere
but home, and ``world_population.build_world_population`` refuses there, so the
bg0001 census cannot follow a player into a football field or a film set.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

from . import world_scene_travel
from .model import Position
from .population import SCENE_SEQUENCE
from .world_scene_travel import (
    HOME_SCENE_ID,
    SceneDestination,
    SceneRegistry,
)


# Convention marker only.  Nothing in this tree branches on it.
production_allowed = True
test_only = False

GATE_REGISTRY_FILENAME = "world_travel_gates_001.json"
GATE_REGISTRY_PATH = (
    Path(__file__).resolve().parents[2] / "scenarios" / GATE_REGISTRY_FILENAME
)

ARRIVAL_DESTINATION_SPAWN = "destination_spawn"
ARRIVAL_REMEMBERED_HOME = "remembered_home_row"
_ARRIVAL_MODES = (ARRIVAL_DESTINATION_SPAWN, ARRIVAL_REMEMBERED_HOME)

ROLE_DEPARTURE = "departure"
ROLE_RETURN = "return"
_ROLES = (ROLE_DEPARTURE, ROLE_RETURN)

# The label the runtime attaches to the queued action.  It carries TELEPORT on
# purpose: runtime.py's move-authority grace window keys on that substring to
# reopen after a SERVER-initiated move, and a scene change is the largest
# server-initiated move this project can make.  Renaming it without renaming
# that check would make the gate's own teleport look like a lying client.
ACTION_LABEL_PREFIX = "WORLD_TRAVEL"

_ROOT_FIELDS = {
    "schema", "id", "lane", "build_order", "test_only", "production_allowed",
    "selection", "not_a_scenario", "written_at", "what_a_gate_is",
    "how_this_is_wired",
    "why_the_trigger_is_a_walk_and_not_a_command",
    "the_measured_facts_the_radii_come_from",
    "the_rule_that_prevents_a_ping_pong", "gates", "settle", "dwell",
    "the_damage_this_can_do_stated_plainly", "capabilities", "nonclaims",
}
_GATE_FIELDS = {
    "name", "role", "from_scene_id", "to_scene_id", "centre",
    "fire_radius_units", "arm_radius_units", "vertical_band_units", "arrival",
}
_GATE_OPTIONAL_FIELDS = {
    "centre_distances_measured_this_round", "centre_source",
    "why_this_centre_cannot_be_pinned", "why_a_vertical_band_here",
    "why_no_vertical_band_here",
}
_CENTRE_FIELDS = {
    "x", "y", "z", "provenance",
    "why_an_authored_placement_and_not_a_bare_coordinate",
}
_SETTLE_FIELDS = {
    "jump_units", "report_budget", "what_settling_means",
    "what_happens_if_it_never_settles",
}
_DWELL_FIELDS = {
    "reports", "still_units", "what_a_dwell_is", "why_a_door_and_not_a_tripwire",
    "measured_backing",
}


class TravelGateRefused(LookupError):
    """A gate that cannot be built, or a departure that must not be sent.

    ``LookupError`` and NOT ``KeyError``, for the same reason
    ``world_scene_entry.SceneEntryRefused`` is: ``runtime.py:3646`` wraps a
    neighbouring call in ``except (KeyError, PermissionError)`` and swallows
    it, and a refusal that is swallowed leaves the client sitting on
    "connecting" with nothing in the log.  A refusal nobody can see is the
    exact failure this lane's console lines exist to prevent, so this one
    cannot be caught by that clause by accident.
    """

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class TravelGate:
    """One door: where it is, what opens it, and where it goes."""

    name: str
    role: str
    from_scene_id: int
    to_scene_id: int
    centre: tuple[float, float, float] | None
    centre_provenance: str | None
    fire_radius: float
    arm_radius: float
    vertical_band: float | None
    arrival_mode: str

    @property
    def centre_is_measured_at_runtime(self) -> bool:
        """True for a gate whose centre only exists once a player has landed.

        See the module docstring: V112 means the server does not know where a
        player lands, so the way back is anchored on the client's own first
        report and not on a coordinate anybody chose.
        """
        return self.centre is None


class _Crossing:
    """The half of a departure that has not happened yet.

    Held by the set AND by the departure it belongs to, so neither can be
    told the crossing went through without the other hearing it.
    """

    __slots__ = ("apply", "discard", "state")

    def __init__(self, apply, discard):
        self.apply = apply
        self.discard = discard
        self.state = "pending"


@dataclass(frozen=True)
class TravelDeparture:
    """Everything one crossing hands back.  Nothing here has been sent.

    TWO PHASES, AND THE SECOND ONE IS THE CALLER'S.  ``observe`` returns this
    object with NOTHING committed: no console line printed, no transit latch
    set, no memory of where the player left from.  The caller persists
    ``arrival`` first, and only then asks for :meth:`confirmed_fields` - which
    is the same tuple ``teleport_fields`` always was, and the act of asking is
    what commits the crossing and prints ``WORLD_TRAVEL_DEPART``.

    ``CORE-REQUEST-004`` section 3 point 3 is why.  The chief pointed out that
    ``foundation.checkpoint`` can throw on a stale lease, and that the old
    order printed the departure line inside ``observe`` before the caller ever
    tried the write: a failed write left a console saying a player had gone to
    scene 278 and a database saying they never left.  In a project whose first
    rule of evidence is that the wire and the row must agree, a log line that
    can outrun the row is not a small thing.

    The caller's patch is the same size it was.  ``departure.teleport_fields``
    became ``departure.confirmed_fields()``; a caller who never asks - because
    the write raised - leaves a crossing that is discarded on the next report
    with ``WORLD_TRAVEL_DEPART_ABANDONED``, and the player stays where they
    are with the log saying exactly that.
    """

    gate: TravelGate
    destination: SceneDestination
    crossed_at: Position
    arrival: Position
    teleport_fields: tuple[int, int, float, float, float]
    action_label: str
    population_source: str | None
    left_from: Position
    console_lines: tuple[str, ...]
    crossing: _Crossing

    @property
    def console_line(self) -> str:
        return self.console_lines[0]

    @property
    def confirmed(self) -> bool:
        return self.crossing.state == "confirmed"

    @property
    def abandoned(self) -> bool:
        return self.crossing.state == "abandoned"

    def confirmed_fields(self) -> tuple[int, int, float, float, float]:
        """Commit the crossing, print it, and hand back the teleport tuple.

        Call this AFTER the arrival row is persisted and not before.  Calling
        it twice is a mistake this refuses rather than double-counts: the
        second call would mean two teleports for one crossing.
        """
        if self.crossing.state == "confirmed":
            raise TravelGateRefused(
                "already_confirmed",
                f"crossing at gate {self.gate.name} was already confirmed",
            )
        if self.crossing.state == "abandoned":
            raise TravelGateRefused(
                "already_abandoned",
                f"crossing at gate {self.gate.name} was abandoned and cannot "
                "be sent",
            )
        self.crossing.apply()
        self.crossing.state = "confirmed"
        return self.teleport_fields

    def abandon(self, reason: str) -> None:
        """Throw the crossing away and say why.  Safe to call twice."""
        if type(reason) is not str or not reason:
            raise ValueError("abandon reason must be a non-empty string")
        if self.crossing.state != "pending":
            return
        self.crossing.state = "abandoned"
        self.crossing.apply = None
        self.crossing.discard(reason)


def _require_text(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise TravelGateRefused("bad_pin", f"{label} must be a non-empty string")
    return value


def _require_int(value: Any, label: str, low: int, high: int) -> int:
    if type(value) is not int or type(value) is bool or not low <= value <= high:
        raise TravelGateRefused(
            "bad_pin", f"{label} must be an integer in [{low}, {high}]")
    return value


def _require_float(value: Any, label: str) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        raise TravelGateRefused("bad_pin", f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise TravelGateRefused("bad_pin", f"{label} must be finite")
    return number


def _horizontal(a: tuple[float, float, float] | Position,
                b: tuple[float, float, float] | Position) -> float:
    ax, ay = (a.x, a.y) if isinstance(a, Position) else (a[0], a[1])
    bx, by = (b.x, b.y) if isinstance(b, Position) else (b[0], b[1])
    return math.hypot(ax - bx, ay - by)


def _finite_position(row: Position) -> bool:
    return all(math.isfinite(value) for value in (row.x, row.y, row.z))


@dataclass(frozen=True)
class TravelGateSettings:
    jump_units: float
    report_budget: int
    dwell_reports: int
    still_units: float


def load_travel_gates(
    path: str | Path = GATE_REGISTRY_PATH,
    registry: SceneRegistry | None = None,
) -> tuple[tuple[TravelGate, ...], TravelGateSettings]:
    """Read the gate pin, and refuse anything a movement path must never meet.

    EVERY check here is a check that would otherwise happen while a player is
    walking.  ``RE-077`` proved the client parks at status 2 on a scene id it
    cannot resolve, with no fallback and no way for the server to know, so a
    gate pointing at an unpinned scene is refused at load and never gets the
    chance to strand somebody.
    """
    scenes = registry or world_scene_travel.load_scene_registry()
    try:
        data = json.loads(Path(path).read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        # Deliberately OUTSIDE the refusal type.  A gate pin that cannot be
        # read is a broken file, and dressing that up as "there is no gate
        # here" is the laundering world_scene_entry was refuted for once.
        raise
    if type(data) is not dict or set(data) != _ROOT_FIELDS:
        raise TravelGateRefused(
            "bad_pin", "travel gate pin root is incomplete or has unknown fields")
    if (
        data["schema"] != 1
        or data["id"] != "world_travel_gates_001"
        or data["test_only"] is not False
        or data["production_allowed"] is not True
    ):
        raise TravelGateRefused("bad_pin", "unsupported travel gate pin")

    settle = data["settle"]
    if type(settle) is not dict or set(settle) != _SETTLE_FIELDS:
        raise TravelGateRefused(
            "bad_pin", "travel gate settle block is incomplete")
    dwell = data["dwell"]
    if type(dwell) is not dict or set(dwell) != _DWELL_FIELDS:
        raise TravelGateRefused("bad_pin", "travel gate dwell block is incomplete")
    settings = TravelGateSettings(
        jump_units=_require_float(settle["jump_units"], "settle jump units"),
        report_budget=_require_int(
            settle["report_budget"], "settle report budget", 1, 10000),
        dwell_reports=_require_int(dwell["reports"], "dwell reports", 2, 1000),
        still_units=_require_float(dwell["still_units"], "dwell still units"),
    )
    if settings.jump_units <= 0.0:
        raise TravelGateRefused("bad_pin", "settle jump units must be positive")
    if settings.still_units < 0.0:
        raise TravelGateRefused("bad_pin", "dwell still units must not be negative")

    rows = data["gates"]
    if type(rows) is not list or not rows:
        raise TravelGateRefused("bad_pin", "travel gate pin has no gates")

    gates: list[TravelGate] = []
    names: set[str] = set()
    origins: set[int] = set()
    for row in rows:
        if (
            type(row) is not dict
            or not _GATE_FIELDS <= set(row)
            or not set(row) <= (_GATE_FIELDS | _GATE_OPTIONAL_FIELDS)
        ):
            raise TravelGateRefused(
                "bad_pin", "travel gate is incomplete or has unknown fields")
        name = _require_text(row["name"], "gate name")
        if name in names:
            raise TravelGateRefused("bad_pin", f"gate {name} is pinned twice")
        names.add(name)
        role = _require_text(row["role"], f"gate {name} role")
        if role not in _ROLES:
            raise TravelGateRefused("bad_pin", f"gate {name} has an unknown role")
        from_scene_id = _require_int(
            row["from_scene_id"], f"gate {name} from scene", 1, 0xFFFF)
        to_scene_id = _require_int(
            row["to_scene_id"], f"gate {name} to scene", 1, 0xFFFF)
        if from_scene_id == to_scene_id:
            raise TravelGateRefused(
                "bad_pin", f"gate {name} leads to the scene it stands in")
        if from_scene_id in origins:
            # One door per scene, for now and on purpose.  Two gates in one
            # scene need a rule for which one wins when a player stands in
            # both, and inventing that rule before anybody has walked through
            # one door is how a lane ships a coin flip.
            raise TravelGateRefused(
                "bad_pin", f"scene {from_scene_id} already has a gate")
        origins.add(from_scene_id)

        # The refusal RE-077 asks for, moved to load time.
        try:
            target = scenes[to_scene_id]
        except KeyError:
            raise TravelGateRefused(
                "destination_not_pinned",
                f"gate {name} points at scene {to_scene_id}, which is not in "
                "the scene registry. RE-077 proved the client parks at status "
                "2 on a model id it cannot resolve and forbids a fallback, so "
                "this gate is refused rather than built.",
            ) from None
        if not target.model_id:
            raise TravelGateRefused(
                "destination_has_no_model",
                f"gate {name} points at scene {to_scene_id}, which has no "
                "model id to load",
            )

        arrival_mode = _require_text(row["arrival"], f"gate {name} arrival")
        if arrival_mode not in _ARRIVAL_MODES:
            raise TravelGateRefused(
                "bad_pin", f"gate {name} has an unknown arrival mode")
        if arrival_mode == ARRIVAL_DESTINATION_SPAWN and target.spawn is None:
            raise TravelGateRefused(
                "destination_has_no_spawn",
                f"gate {name} would land a player in scene {to_scene_id}, "
                "which has no pinned spawn position",
            )

        fire_radius = _require_float(
            row["fire_radius_units"], f"gate {name} fire radius")
        arm_radius = _require_float(
            row["arm_radius_units"], f"gate {name} arm radius")
        if fire_radius <= 0.0:
            raise TravelGateRefused(
                "bad_pin", f"gate {name} fire radius must be positive")
        if arm_radius <= fire_radius:
            # Without hysteresis a player standing on the boundary re-arms and
            # re-fires on alternating reports.
            raise TravelGateRefused(
                "bad_pin",
                f"gate {name} arm radius must be larger than its fire radius",
            )
        band = row["vertical_band_units"]
        vertical_band = None if band is None else _require_float(
            band, f"gate {name} vertical band")
        if vertical_band is not None and vertical_band <= 0.0:
            raise TravelGateRefused(
                "bad_pin", f"gate {name} vertical band must be positive")

        raw_centre = row["centre"]
        if raw_centre is None:
            if role != ROLE_RETURN:
                raise TravelGateRefused(
                    "bad_pin",
                    f"gate {name} has no centre, and only a return gate may "
                    "measure its centre at runtime",
                )
            centre = None
            centre_provenance = None
        else:
            if type(raw_centre) is not dict or not set(raw_centre) <= _CENTRE_FIELDS \
                    or not {"x", "y", "z", "provenance"} <= set(raw_centre):
                raise TravelGateRefused(
                    "bad_pin", f"gate {name} centre is incomplete")
            centre = tuple(
                _require_float(raw_centre[axis], f"gate {name} centre {axis}")
                for axis in "xyz"
            )
            centre_provenance = _require_text(
                raw_centre["provenance"], f"gate {name} centre provenance")

        gates.append(TravelGate(
            name=name,
            role=role,
            from_scene_id=from_scene_id,
            to_scene_id=to_scene_id,
            centre=centre,
            centre_provenance=centre_provenance,
            fire_radius=fire_radius,
            arm_radius=arm_radius,
            vertical_band=vertical_band,
            arrival_mode=arrival_mode,
        ))

    _refuse_unreachable_settles(gates, scenes, settings)
    return tuple(gates), settings


def _refuse_unreachable_settles(
    gates: tuple[TravelGate, ...] | list[TravelGate],
    scenes: SceneRegistry,
    settings: TravelGateSettings,
) -> None:
    """Refuse a pin whose arrival is too close to its own departure point.

    The settle test cannot read a scene id - the durable row already carries
    the new one while the client is still reporting the old scene's
    coordinates - so it reads the size of the jump.  If a destination's pinned
    arrival sits within one jump of the gate a player left from, the arrival
    report is indistinguishable from an ordinary step and the transit never
    settles.  That is a property of the NUMBERS in the pin, so it is checked
    where the numbers are read and not where a player is walking.
    """
    for gate in gates:
        if gate.arrival_mode != ARRIVAL_DESTINATION_SPAWN or gate.centre is None:
            continue
        spawn = scenes[gate.to_scene_id].spawn
        if spawn is None:
            continue
        separation = _horizontal(gate.centre, spawn)
        if separation <= settings.jump_units:
            raise TravelGateRefused(
                "settle_would_never_fire",
                f"gate {gate.name} lands a player {separation:.1f} units from "
                f"the door they left by, and the settle test needs more than "
                f"{settings.jump_units:.1f}. Either the two scenes share a "
                "coordinate space or one of the pins is wrong.",
            )


@dataclass(frozen=True)
class PreloadedGates:
    """One parse of the pin, shared by every session in the process."""

    gates: tuple[TravelGate, ...]
    settings: TravelGateSettings
    registry: SceneRegistry
    source: str


_PRELOADED: PreloadedGates | None = None


def preload(
    path: str | Path = GATE_REGISTRY_PATH,
    registry: SceneRegistry | None = None,
) -> PreloadedGates:
    """Read and validate the pins ONCE, where a bad pin should stop a boot.

    WHY THIS EXISTS, IN THE CHIEF'S OWN WORDS.  ``CORE-REQUEST-004`` section 3
    asked lane A to answer this before the call goes in: a bare
    ``TravelGateSet()`` inside ``PersistentGameSessionState.__init__`` parses
    three JSON files on EVERY LOGIN and raises ``TravelGateRefused`` if any of
    them is wrong - and that constructor sits on the login path of every
    player, so a broken pin does not mean "travel is off", it means NOBODY CAN
    LOG IN.  That is not a hypothetical: the adversary pass of round 4fhdxv
    saw it at 21:56 UTC when the pin was missing for a moment and 53 tests
    went red at once.

    The fix is not a softer loader.  A pin this lane cannot read must still
    stop something, or a typo ships silently.  It stops the RIGHT thing:

        server start   preload()                      -> raises, boot fails,
                                                        one operator, no player
        every login    TravelGateSet.from_preloaded() -> no file I/O, no raise

    Calling this twice re-reads and replaces the cache, so an operator can fix
    a pin and restart the process rather than the machine.  It is deliberately
    NOT called lazily from ``from_preloaded``: a lazy first parse would put the
    raise back on the first player's login, which is the whole thing this
    removes.
    """
    global _PRELOADED
    scenes = registry or world_scene_travel.load_scene_registry()
    gates, settings = load_travel_gates(path, registry=scenes)
    _PRELOADED = PreloadedGates(
        gates=gates, settings=settings, registry=scenes, source=str(path),
    )
    return _PRELOADED


def preloaded() -> PreloadedGates | None:
    """The current parse, or None if nobody has called :func:`preload`."""
    return _PRELOADED


def forget_preload() -> None:
    """Drop the cached parse.  Tests and a reload, nothing else."""
    global _PRELOADED
    _PRELOADED = None


def scenario_stand_down(selected: Any) -> str | None:
    """Name a reason this lane must keep its doors shut, or ``None``.

    ``CORE-REQUEST-004`` section 3 point 2 asked the chief to write a guard
    listing every opt-in lane whose scenarios also run in scene 1, because
    lane A does not know them all: an attended arena, ground-loot or nameprop
    round whose player walks into the gate zone and stops gets carried into
    another scene mid-experiment, and their durable row then says 278 on every
    boot after that until somebody edits the database by hand.

    THE LIST THIS ROUND SAID COULD NOT BE WRITTEN IS ALREADY WRITTEN, and the
    adversary pass of round e7q6yy found it: ``runtime.make_state_class``
    builds ``active_lanes`` at ``runtime.py:334-382`` - a frozenset of the
    names of every lane the boot actually selected, twenty-six of them, at the
    top of the factory, which is where this call goes.  PASS THAT.  It is the
    runtime's own definition of "a lane is selected", so this guard cannot
    drift from it, which is more than a naming rule of mine could promise.

    ACCEPTS, IN ORDER OF PREFERENCE:

        a set/frozenset/list/tuple of names   ``active_lanes``   - any member
                                                                   shuts them
        a mapping                             ``locals()``       - any entry
                                                                   named
                                                                   ``scenario``
                                                                   or ending
                                                                   ``_scenario``
                                                                   whose value
                                                                   is not None
        anything else                                            - refused

    AN OBJECT IS NOT ACCEPTED, AND THAT IS THE POINT.  The first version of
    this function scanned ``vars(owner)``.  The adversary pass measured four
    shapes where that returns ``None`` while a lane IS selected - a class
    attribute, a ``property``, an inherited default, and any object that
    happens to define ``items()`` (whose inventory got scanned instead of its
    attributes).  A guard whose miss opens every door is worse than no guard,
    so the shape that can miss is gone rather than patched.

    ``scenario`` counts as well as ``*_scenario``: the arena lane - the
    chief's own first example, and the one that runs in scene 1 - is passed
    under the bare name, so a suffix-only rule would have let through the
    exact lane this guard was asked for.

    Anything it cannot read returns a reason rather than ``None``: the failure
    mode must be "travel is off", never "every door is open".
    """
    if selected is None:
        return None
    if isinstance(selected, Mapping):
        names = []
        try:
            for name, value in selected.items():
                if not isinstance(name, str):
                    return "scenario_scan_unreadable"
                if (name == "scenario" or name.endswith("_scenario")) and (
                    value is not None
                ):
                    names.append(name)
        except Exception:
            return "scenario_scan_unreadable"
    elif isinstance(selected, (set, frozenset, list, tuple)):
        names = list(selected)
        if any(not isinstance(name, str) for name in names):
            return "scenario_scan_unreadable"
    else:
        # An object, an int, anything with attributes: refused rather than
        # scanned.  See the docstring - the scan is what failed open.
        return "scenario_scan_unreadable"
    if not names:
        return None
    return "scenario_selected_" + ",".join(sorted(names))


# COO ruling 20260826 (verbatim, translated): "Remove world_travel_gates_001
# ('stand in the zone and cross') from M2/production acceptance immediately.
# Do NOT delete the file or the code. Keep it as debug-only, OFF by default.
# It must never again be used as an M2 acceptance criterion." The owner
# separately confirmed, verbatim, that this walk-in-and-stop mechanic does
# not exist in the real game at all - the real door out of town is Columbus,
# a sea map, a dock, and a captain-report confirm window.
DEBUG_LANE_DISABLED_REASON = "walkin_travel_gate_disabled_by_default_owner_20260826"


def lane_reason(selected: Any, *, debug_enabled: bool = False) -> str | None:
    """The reason to hand ``TravelGateSet.from_preloaded`` as ``inert_reason``.

    This is :func:`scenario_stand_down` with the COO's 20260826 ruling laid
    in front of it, and it is meant to REPLACE the bare
    ``scenario_stand_down(active_lanes)`` call at the one call site this
    module has (``runtime.py``, next to ``TravelGateSet.from_preloaded``) -
    see the CORE-REQUEST this ships with for the one-line change and the
    ``make_state_class``/``app.py`` threading it needs, neither of which this
    module may edit itself.

    ``debug_enabled`` DEFAULTS TO ``False``, matching every other opt-in
    boolean this project wires from a CLI flag (``--export-events`` is the
    model: ``action='store_true'``, absent means off).  While it is
    ``False`` this function ALWAYS returns :data:`DEBUG_LANE_DISABLED_REASON`
    - not ``scenario_stand_down(selected)``, not ``None``, regardless of what
    ``selected`` is - because a lane the owner has ruled off does not need to
    consult what else is running to know it is off, and a caller must never
    be able to accidentally arm it by getting ``selected`` right.

    ``debug_enabled=True`` is the explicit, human-chosen opt-in (a CLI flag
    such as ``--enable-travel-gate-debug``, never a default).  Only then does
    :func:`scenario_stand_down` get to speak at all, and it is completely
    unchanged when it does: an opt-in lane sharing scene 1 with this one
    still shuts these doors exactly as it always has.  This function does not
    replace that guard - it decides whether the guard is even consulted.
    """
    if not debug_enabled:
        return DEBUG_LANE_DISABLED_REASON
    return scenario_stand_down(selected)


class TravelGateSet:
    """The live state of one player's doors.  One instance per session.

    Not thread safe and not shared: it holds where this player has been, and
    two players sharing one would open each other's doors.

    THE ONE FACT THIS CLASS DOES NOT HAVE, STATED BEFORE ANYTHING ELSE.
    ``TargetPosVital`` carries no scene identity, and
    ``_checkpoint_exact_target`` stamps the row with the scene the SERVER
    believes the player is in.  So when a report arrives carrying scene 997,
    that is the server's opinion, not the client's.  Nothing in this project
    can currently distinguish "the client is standing in scene 997" from "the
    row says 997 and the client is still in Port Royal".  Every rule below
    that looks paranoid is that missing fact: the module treats a
    DISCONTINUITY - a step no walk can produce - as the only evidence it has
    that the ground under the player changed, and it refuses to arm or fire a
    door on any report it cannot reconcile with the one before it.

    That is a heuristic and it is named as one.  What would replace it is an
    acknowledged transition frame from the client; ``TeleportCheckVital``
    (``0x4477``, decoded schema only, never answered) is the candidate nobody
    has opened.  Until then a distance threshold is what there is.
    """

    @classmethod
    def from_preloaded(
        cls,
        *,
        emit=print,
        inert_reason: str | None = None,
        pins: PreloadedGates | None = None,
    ) -> "TravelGateSet":
        """The login-path constructor: no file I/O, and no raise for a pin.

        This is the one the chief wires into
        ``PersistentGameSessionState.__init__``.  Everything that can refuse
        has already refused inside :func:`preload` at server start, so all
        that is left here is copying references.

        IF NOBODY CALLED ``preload`` THIS RETURNS AN INERT SET, loudly.  The
        alternative - parsing here, or raising here - puts a boot-time failure
        back on a player's login, and a lane whose pin is missing should cost
        the world its doors, not cost the players their game.
        """
        pins = pins if pins is not None else _PRELOADED
        if inert_reason is not None and (
            type(inert_reason) is not str or not inert_reason
        ):
            # THIS IS THE LOGIN PATH.  __init__ refuses a bad reason with a
            # ValueError because a caller building a set by hand should hear
            # about it; here that would put a raise on every player's login
            # for a caller's typo, which is the whole thing preload exists to
            # remove.  A reason nobody can read shuts the doors instead.
            inert_reason = "inert_reason_unreadable"
        if pins is None:
            return cls(
                (), TravelGateSettings(0.0, 0, 0, 0.0),
                registry={}, emit=emit,
                inert_reason="not_preloaded",
            )
        return cls(
            pins.gates, pins.settings, registry=pins.registry, emit=emit,
            inert_reason=inert_reason,
        )

    def __init__(
        self,
        gates: tuple[TravelGate, ...] | None = None,
        settings: TravelGateSettings | None = None,
        *,
        registry: SceneRegistry | None = None,
        emit=print,
        inert_reason: str | None = None,
    ):
        if not callable(emit):
            raise ValueError("emit must be callable")
        if inert_reason is not None and (
            type(inert_reason) is not str or not inert_reason
        ):
            raise ValueError("inert_reason must be a non-empty string or None")
        # ONE registry object, not two.  Validating the gates against one
        # parse and firing them against a second parse of the same file means
        # an edit between the two turns _fire's lookup into a bare KeyError -
        # the exact swallowable type TravelGateRefused exists to avoid.
        #
        # ``is None`` and not a truth test: from_preloaded hands an inert set
        # an EMPTY registry, and an empty dict is falsy, so a truth test here
        # would send the one construction that must never touch the disk
        # straight to the disk.
        if registry is None and inert_reason is None:
            registry = world_scene_travel.load_scene_registry()
        self._registry = {} if registry is None else registry
        self._inert_reason = inert_reason
        if inert_reason is None and not self._registry:
            # world_scene_travel.destination() is ``(registry or
            # load_scene_registry())[...]`` - an EMPTY dict is falsy, so a
            # live set holding one would read the registry off disk from
            # inside observe(), on the walking path, which is the trap this
            # class's own comment argues about two lines up.  Refused at
            # construction, where a refusal costs a boot and not a player.
            raise TravelGateRefused(
                "empty_registry",
                "a live gate set needs a scene registry; an empty one sends "
                "world_scene_travel.destination back to the disk from inside "
                "observe()",
            )
        if inert_reason is not None:
            gates = () if gates is None else gates
            settings = (
                TravelGateSettings(0.0, 0, 0, 0.0) if settings is None
                else settings
            )
        if gates is None or settings is None:
            loaded_gates, loaded_settings = load_travel_gates(
                registry=self._registry)
            gates = gates if gates is not None else loaded_gates
            settings = settings if settings is not None else loaded_settings
        self._gates = tuple(gates)
        self._settings = settings
        self._emit = emit
        self._armed: dict[str, bool] = {gate.name: False for gate in self._gates}
        self._measured_centres: dict[str, tuple[float, float, float]] = {}
        # Keyed by the scene a crossing LEFT, not by "home".  A return gate
        # asks "what row was this player standing on when they left scene 1",
        # and a single slot answered that with the row they left scene 997 on
        # as soon as anybody made the round trip twice.
        self._left_from: dict[int, Position] = {}
        # The row the player was standing on when they crossed - the row an
        # operator restores if the destination never loads.
        self._transit_from: Position | None = None
        # The PREVIOUS report, which is what a step is measured against.
        # Measuring against the crossing row instead makes the test a
        # cumulative-displacement test, and a player who simply keeps walking
        # away from the door passes it while still standing in the old scene.
        self._transit_last: Position | None = None
        self._transit_reports = 0
        self._last_report: Position | None = None
        # Consecutive reports, per gate, on which the player was inside the
        # zone AND had not moved since the report before.  A door you have to
        # stand in is a door; a door that opens because you walked past it is
        # a trapdoor, and the adversary pass of round 4fhdxv pointed out that
        # this one would have been placed 993 walking units from the spawn
        # used by the M1 acceptance walk.
        self._dwell: dict[str, int] = {gate.name: 0 for gate in self._gates}
        self._departures = 0
        # A crossing this set has handed to the caller and has not been told
        # the end of.  At most one exists at a time: a set with a pending
        # crossing has already stopped considering doors.
        self._pending: TravelDeparture | None = None
        # Crossings this set has HANDED OUT, committed or not.  _departures
        # counts the committed ones and is what the console and the reports
        # mean by a departure; this one is what _anchor_on_first_sight has to
        # read, because a crossing the caller never confirmed may still have
        # moved the durable row.  It never goes down.
        self._crossings_offered = 0
        # (gate, reason) pairs already said once.  See _refuse.
        self._refusals_said: set[tuple[str, str]] = set()
        if self._inert_reason is not None:
            try:
                self._emit(_inert_line(self._inert_reason, len(self._gates)))
            except Exception:
                # A console that is gone must not take the login with it.
                # This is the one emit on the login path; every other one is
                # on the walking path, where a raise is the caller's to see.
                pass

    # -- standing down ----------------------------------------------------
    @property
    def is_inert(self) -> bool:
        return self._inert_reason is not None

    @property
    def inert_reason(self) -> str | None:
        return self._inert_reason

    def stand_down(self, reason: str) -> None:
        """Shut every door for the rest of this session.  Cannot be undone.

        For a caller that only learns which lane it is running AFTER the set
        was built.  One way only: a set that resumed would have to decide what
        its half-counted dwells and its transit latch mean, and the honest
        answer is that it cannot know.

        A stand-down inside a transit prints the row to restore, because that
        row is the only copy of where the player was standing when they left
        and this object is about to stop reporting it.
        """
        if type(reason) is not str or not reason:
            raise ValueError("stand down reason must be a non-empty string")
        if self._inert_reason is not None:
            return
        self._inert_reason = reason
        if self._pending is not None:
            # Clearing the slot without abandoning the crossing would leave the
            # caller holding a live one: its staged apply() would still commit
            # and still print, on a set that has already stood down.  A door
            # that opens after the lane was shut is worse than one that never
            # opened.
            self._pending.abandon("stood_down_before_confirm")
        if self._transit_from is not None:
            self._emit(_stranded_line(
                self._transit_last or self._transit_from,
                self._transit_from,
                self._transit_reports,
            ))
        self._clear_transit()
        for name in self._armed:
            self._armed[name] = False
        self._reset_dwell()
        self._emit(_inert_line(reason, len(self._gates)))

    # -- read-only views -------------------------------------------------
    @property
    def gates(self) -> tuple[TravelGate, ...]:
        return self._gates

    @property
    def in_transit(self) -> bool:
        return self._transit_from is not None

    @property
    def departures(self) -> int:
        return self._departures

    def is_armed(self, name: str) -> bool:
        if name not in self._armed:
            raise TravelGateRefused("no_such_gate", f"no gate named {name}")
        return self._armed[name]

    def measured_centre(self, name: str) -> tuple[float, float, float] | None:
        return self._measured_centres.get(name)

    def dwell(self, name: str) -> int:
        """How many consecutive still reports this gate has counted."""
        if name not in self._dwell:
            raise TravelGateRefused("no_such_gate", f"no gate named {name}")
        return self._dwell[name]

    def left_from(self, scene_id: int) -> Position | None:
        """The row this player was standing on when they last left that scene."""
        return self._left_from.get(scene_id)

    # -- the one entry point ---------------------------------------------
    def observe(self, row: Position) -> TravelDeparture | None:
        """Take one durable position row; return a departure or nothing.

        ``row`` is the row AFTER the runtime has checkpointed the client's
        reading, so it carries the scene the server believes the player is in
        together with the position the client just reported.  Reading the row
        rather than the raw wire tuple is deliberate: the scene and the
        coordinates then come from the same object and cannot disagree, which
        is the trap round qumhmf was refuted for.

        NEVER RAISES ON A REPORT.  Every refusal is a named console line and a
        ``None``.  This runs inside ``dispatch``; an exception here does not
        refuse a departure, it kills the connection's frame handling, and
        ``TravelGateRefused`` is a ``LookupError`` precisely so that
        ``runtime.py:3646`` cannot swallow it.  The raising belongs at
        construction, where a broken pin should stop a boot.
        """
        if type(row) is not Position:
            raise ValueError("observe needs a Position row")
        if self._inert_reason is not None:
            # Silent on purpose.  The reason was printed once when this set
            # stood down; printing it again on every report of every session
            # of every opt-in lane would bury the lane that IS running.
            return None
        if self._pending is not None:
            # The caller took a crossing and never came back to confirm it,
            # which means the arrival row was not written - so no teleport
            # went out and the player never moved.  Throw it away before
            # reading this report, or the set carries a crossing that the
            # world has no evidence of.
            self._pending.abandon("not_confirmed_before_next_report")
        if not _finite_position(row):
            self._emit(
                "WORLD_TRAVEL_REFUSED reason=nonfinite_row scene_id={0}"
                .format(row.scene_id)
            )
            return None

        if self._transit_from is not None:
            self._advance_transit(row)
            return None

        step = (
            None if self._last_report is None
            else _horizontal(row, self._last_report)
        )
        if step is not None and step > self._settings.jump_units:
            # A step no walk can produce, outside a transit this set started.
            # It could be a straggler frame from before a switch, a client
            # correcting itself, or a teleport somebody else sent.  What it is
            # NOT is evidence about where this player is standing, so it may
            # not arm a door and it may not open one.
            self._emit(_discontinuity_line(row, self._last_report, step))
            self._reset_dwell()
            self._last_report = row
            return None

        departure = self._consider(row, step)
        self._last_report = row
        return departure

    # -- internals --------------------------------------------------------
    def _consider(
        self, row: Position, step: float | None
    ) -> TravelDeparture | None:
        gate = self._gate_in(row.scene_id)
        if gate is None:
            self._reset_dwell()
            return None
        centre = self._centre_of(gate)
        if centre is None:
            centre = self._anchor_on_first_sight(gate, row)
        if centre is None:
            # A return gate whose landing was never observed IN A SESSION
            # THAT DID THE TRAVELLING.  Nothing this module can do restores
            # it - see the strand paragraph in the module docstring.
            self._reset_dwell()
            return None

        horizontal = _horizontal(row, centre)
        if not self._armed[gate.name]:
            self._reset_dwell()
            if horizontal > gate.arm_radius:
                # Line first, state second, exactly as _fire does it: a
                # console that raises must not leave a gate that the log never
                # said was open.
                self._emit(_armed_line(gate, centre, row, horizontal))
                self._armed[gate.name] = True
            return None

        inside = horizontal <= gate.fire_radius
        if inside and gate.vertical_band is not None:
            inside = abs(row.z - centre[2]) <= gate.vertical_band
        if not inside:
            self._reset_dwell()
            return None

        # INSIDE IS NOT ENOUGH.  The player has to have STOPPED here.  In the
        # one authentic walk this project holds, every walking report moved
        # (runs of identical positions have length 1 while moving) and three
        # stationary runs of 3, 6 and 3 identical reports exist.  So "the same
        # position N times running" separates a player who chose this spot
        # from a player crossing it on the way somewhere else, and it does so
        # on measured behaviour rather than on a number somebody liked.
        if step is None or step > self._settings.still_units:
            self._dwell[gate.name] = 1 if step is None else 0
            return None
        self._dwell[gate.name] += 1
        if self._dwell[gate.name] < self._settings.dwell_reports:
            self._emit(_dwell_line(
                gate, row, horizontal, self._dwell[gate.name],
                self._settings.dwell_reports))
            return None
        return self._fire(gate, centre, row, horizontal)

    def _reset_dwell(self) -> None:
        for name in self._dwell:
            self._dwell[name] = 0

    def _gate_in(self, scene_id: int) -> TravelGate | None:
        for gate in self._gates:
            if gate.from_scene_id == scene_id:
                return gate
        return None

    def _anchor_on_first_sight(
        self, gate: TravelGate, row: Position
    ) -> tuple[float, float, float] | None:
        """Give a relogged player a way home, and nobody else.

        A character whose durable row already says 997 when the session opens
        did their travelling in a process that is gone, so this set has no
        landing to anchor on and the player would be walled into the scene
        with no door.  Anchoring on the first position seen in that scene
        gives them one: walk out, walk back, go home.

        THE CONDITION IS "THIS SET HAS NEVER OFFERED A CROSSING" AND IT IS THE
        WHOLE GUARD.  After a strand inside THIS session the client never
        loaded the destination, so its reports are still the old scene's
        coordinates, and anchoring there would put the way home on a
        coordinate that does not exist in the scene the row names.  A session
        that has already sent somebody somewhere therefore anchors on a
        measured landing or not at all.

        IT COUNTS CROSSINGS OFFERED, NOT DEPARTURES COMMITTED, and the
        difference is a hole the two-phase change opened.  ``_departures``
        only moves inside ``apply()``.  The caller persists the arrival row
        BEFORE it confirms, so there is a real window where the row says 278
        and the confirm never happened - and in that window ``departures``
        was 0, this guard passed, and the way home was anchored on Port Royal
        coordinates while the durable row named another scene.  The adversary
        pass of round e7q6yy reproduced exactly that.  A crossing that was
        handed to a caller is evidence enough that this session did the
        travelling, whether or not the caller came back to say so.
        """
        if not gate.centre_is_measured_at_runtime:
            return None
        if self._crossings_offered != 0 or self.in_transit:
            return None
        centre = (row.x, row.y, row.z)
        # A DIFFERENT EVENT NAME ON PURPOSE.  WORLD_TRAVEL_RETURN_ANCHORED is
        # a landing this session watched arrive; this one is a guess with no
        # evidence under it at all.  One grep must not return both.
        self._emit(_first_sight_line(gate, row))
        self._measured_centres[gate.name] = centre
        return centre

    def _centre_of(self, gate: TravelGate) -> tuple[float, float, float] | None:
        if gate.centre is not None:
            return gate.centre
        return self._measured_centres.get(gate.name)

    def _advance_transit(self, row: Position) -> None:
        assert self._transit_last is not None
        self._transit_reports += 1
        step = _horizontal(row, self._transit_last)
        if step > self._settings.jump_units:
            self._settle(row, step)
            return
        self._transit_last = row
        if self._transit_reports >= self._settings.report_budget:
            self._emit(_stranded_line(
                row, self._transit_from, self._transit_reports))
            self._clear_transit()
            self._last_report = row

    def _settle(self, row: Position, step: float) -> None:
        gate = self._gate_in(row.scene_id)
        anchors = gate is not None and gate.centre_is_measured_at_runtime
        if anchors:
            self._emit(_anchored_line(gate, row, step))
        self._emit(_settled_line(row, step, self._transit_reports))
        # Lines first, state second - see _fire.
        if anchors:
            self._measured_centres[gate.name] = (row.x, row.y, row.z)
        self._clear_transit()
        self._last_report = row

    def _clear_transit(self) -> None:
        self._transit_from = None
        self._transit_last = None
        self._transit_reports = 0

    def _arrival_for(self, gate: TravelGate,
                     target: SceneDestination) -> Position:
        if gate.arrival_mode == ARRIVAL_DESTINATION_SPAWN:
            return world_scene_travel.entry_position(target)
        remembered = self._left_from.get(gate.to_scene_id)
        if remembered is not None and remembered.scene_id == gate.to_scene_id:
            return remembered
        # No memory of where this player left from - a fresh process, or a
        # return that was never preceded by a departure. The pinned home row
        # is the honest answer and the console line says which one was used,
        # because the two are 2294.52 units apart at the gate this lane
        # pinned - well outside the 1200-unit arm radius - and a reader must
        # not have to guess which one they are looking at.
        return world_scene_travel.home_return_position(self._registry)

    def _refuse(
        self, gate: TravelGate, reason: str, row: Position
    ) -> None:
        """Say a refusal ONCE, and make the player earn the next attempt.

        Two things happen here and they answer two different failures.

        THE DWELL RESET stops the gate re-firing on the very next still
        report.  Without it a refusal leaves the dwell counter at or above
        ``dwell_reports``, so the gate fires, refuses and prints again on
        every report for as long as the player stands there.

        THE LATCH stops it printing forever at a slower rate.  The adversary
        pass of round e7q6yy pointed out that the dwell reset alone divides
        the rate by ``dwell_reports`` and calls itself a fix: every one of
        these conditions is a function of a durable row that cannot change
        while the session lives, so "once per three reports, forever" is
        still hundreds of identical lines an idle minute, and the rationale
        this method was written under - that a console repeating a permanent
        refusal is how the one line that mattered gets lost - asked for a
        latch.  So each (gate, reason) says its piece once per session and
        then goes quiet.  A reader who wants to know it is still refusing
        reads the absence of a departure, not a wall of repeats.
        """
        key = (gate.name, reason)
        if key not in self._refusals_said:
            self._refusals_said.add(key)
            self._emit(_refused_line(gate, reason, row))
        self._dwell[gate.name] = 0
        return None

    def _fire(
        self,
        gate: TravelGate,
        centre: tuple[float, float, float],
        row: Position,
        horizontal: float,
    ) -> TravelDeparture | None:
        target = self._registry[gate.to_scene_id]
        arrival = self._arrival_for(gate, target)
        remembered = self._left_from.get(gate.to_scene_id)
        remembered_used = (
            gate.arrival_mode == ARRIVAL_REMEMBERED_HOME
            and remembered is not None
            and remembered.scene_id == gate.to_scene_id
        )
        teleport_fields = (
            arrival.scene_id, arrival.scene_seq, arrival.x, arrival.y, arrival.z,
        )
        # Both of these were raises until the adversary pass of round 4fhdxv
        # pointed out that the second one is reachable from a DATABASE VALUE -
        # store.save_position accepts any scene_seq the column can hold - and
        # that raising here does not refuse a departure, it kills the
        # connection.  They are refusals with names now.
        if teleport_fields[0] <= 0:
            # RE-077: TeleportVital apply 0x5F14B0 rejects target scene 0.
            return self._refuse(gate, "target_scene_zero", row)
        if teleport_fields[1] != SCENE_SEQUENCE:
            return self._refuse(
                gate, "scene_sequence_{0}_not_{1}".format(
                    teleport_fields[1], SCENE_SEQUENCE), row)
        label = "{0}_{1}_TO_SCENE{2}_TELEPORT".format(
            ACTION_LABEL_PREFIX, gate.role.upper(), gate.to_scene_id,
        )
        population = world_scene_travel.population_source(gate.to_scene_id)
        lines = (
            _depart_line(gate, target, row, arrival, population, remembered_used),
        )

        def apply() -> None:
            # Order matters, and tests/test_world_travel_gate.py proves it
            # rather than only saying it. The state is committed only after
            # the lines are out, so a console that raises cannot leave a
            # player mid-transit with nothing in the log saying why.
            for line in lines:
                self._emit(line)
            self._left_from[gate.from_scene_id] = row
            self._transit_from = row
            self._transit_last = row
            self._transit_reports = 0
            self._departures += 1
            for name in self._armed:
                self._armed[name] = False
            self._reset_dwell()
            if gate.role == ROLE_DEPARTURE:
                for other in self._gates:
                    if other.centre_is_measured_at_runtime:
                        self._measured_centres.pop(other.name, None)
            self._pending = None

        def discard(reason: str) -> None:
            # Nothing to undo - the point of staging is that there is
            # nothing to undo - so this only says so and makes the player
            # earn the next attempt, exactly as a refusal does.
            self._emit(_abandoned_line(gate, reason, row, arrival))
            self._dwell[gate.name] = 0
            self._pending = None

        departure = TravelDeparture(
            gate=gate,
            destination=target,
            crossed_at=row,
            arrival=arrival,
            teleport_fields=teleport_fields,
            action_label=label,
            population_source=population,
            left_from=row,
            console_lines=lines,
            crossing=_Crossing(apply, discard),
        )
        self._pending = departure
        self._crossings_offered += 1
        return departure



def _armed_line(
    gate: TravelGate,
    centre: tuple[float, float, float],
    row: Position,
    horizontal: float,
) -> str:
    return (
        "WORLD_TRAVEL_ARMED gate={0} scene_id={1} centre=({2:.3f},{3:.3f},"
        "{4:.3f}) at=({5:.3f},{6:.3f},{7:.3f}) dist={8:.3f} fire_radius={9:.3f}"
        .format(
            gate.name, gate.from_scene_id, centre[0], centre[1], centre[2],
            row.x, row.y, row.z, horizontal, gate.fire_radius,
        )
    )


def _inert_line(reason: str, gate_count: int) -> str:
    return (
        "WORLD_TRAVEL_INERT reason={0} gates={1} "
        "effect=no_door_opens_in_this_session"
        .format(reason, gate_count)
    )


def _abandoned_line(
    gate: TravelGate, reason: str, row: Position, arrival: Position,
) -> str:
    """A crossing this module handed over and was never told the end of.

    ``no_teleport_sent`` IS THE ONLY THING THIS LINE KNOWS.  An earlier
    revision printed ``row_not_written=``, which is a claim about the
    DATABASE, and this module has never been able to see the database.  The
    adversary pass of round e7q6yy reproduced the sequence where it is
    actively false: the caller persists the arrival row FIRST and confirms
    second, so a confirm that dies after a successful write leaves a row that
    says 278 under a console line asserting it was never written.  In a
    project whose first rule of evidence is that the wire and the row must
    agree, a line that guesses at the row is worse than a line that says less.
    ``arrival_row_offered`` is what this module produced; whether anybody
    stored it is the caller's to report.
    """
    return (
        "WORLD_TRAVEL_DEPART_ABANDONED gate={0} reason={1} to_scene={2} "
        "stayed_at=({3:.3f},{4:.3f},{5:.3f}) "
        "arrival_row_offered=({6},{7},{8:.3f},{9:.3f},{10:.3f}) "
        "no_teleport_sent=true whether_the_caller_wrote_that_row=unknown"
        .format(
            gate.name, reason, gate.to_scene_id, row.x, row.y, row.z,
            arrival.scene_id, arrival.scene_seq,
            arrival.x, arrival.y, arrival.z,
        )
    )


def _refused_line(gate: TravelGate, reason: str, row: Position) -> str:
    """A door that will not open, and why, on the walking path.

    THIS FUNCTION DID NOT EXIST UNTIL ROUND e7q6yy AND ITS TWO CALL SITES DID.
    ``_fire`` has called it since round 4fhdxv, so both of the refusals the
    adversary pass asked for - a target scene id of 0, and an arrival row
    whose ``scene_seq`` is not the one the client is on - raised ``NameError``
    inside ``observe`` instead of printing a line and returning ``None``.  The
    module docstring promises ``observe`` never raises on a report because a
    raise there does not refuse a departure, it kills the connection's frame
    handling; that promise was false for every player whose durable row
    carried a ``scene_seq`` other than ``SCENE_SEQUENCE``, which
    ``store.save_position`` accepts and nothing rejects.  ONE of the two is
    reproduced end to end, in
    ``TravelGateRefusalTests.test_a_durable_row_the_database_accepts_used_to_kill_the_connection``:
    the walk out of town succeeded and the door home raised.  The other
    (``target_scene_zero``) has NO reachable public path today - every source
    ``_arrival_for`` can return is already positive - and its test says so and
    drives it through a subclass instead.  An earlier revision of this
    docstring said "the two never_ran tests" reproduced both; no test of that
    name exists and only one branch was ever walked to.

    A guard nobody has ever seen refuse anything is not a guard.
    """
    return (
        "WORLD_TRAVEL_REFUSED gate={0} reason={1} role={2} from_scene={3} "
        "to_scene={4} scene_id={5} at=({6:.3f},{7:.3f},{8:.3f})"
        .format(
            gate.name, reason, gate.role, gate.from_scene_id,
            gate.to_scene_id, row.scene_id, row.x, row.y, row.z,
        )
    )


def _depart_line(
    gate: TravelGate,
    target: SceneDestination,
    row: Position,
    arrival: Position,
    population: str | None,
    remembered_used: bool,
) -> str:
    return (
        "WORLD_TRAVEL_DEPART gate={0} role={1} from_scene={2} to_scene={3} "
        "model={4} crossed_at=({5:.3f},{6:.3f},{7:.3f}) "
        "row_before=({8},{9},{10:.3f},{11:.3f},{12:.3f}) "
        "arrival_row=({13},{14},{15:.3f},{16:.3f},{17:.3f}) "
        "arrival_source={18} population_source={19} "
        "avatar_position_is_not_set_by_this_teleport=V112 "
        "remote_actors_after_switch=unknown_RE077_T5"
        .format(
            gate.name, gate.role, gate.from_scene_id, gate.to_scene_id,
            target.model_id,
            row.x, row.y, row.z,
            row.scene_id, row.scene_seq, row.x, row.y, row.z,
            arrival.scene_id, arrival.scene_seq, arrival.x, arrival.y, arrival.z,
            ("remembered_row" if remembered_used else
             ("pinned_spawn" if gate.arrival_mode == ARRIVAL_DESTINATION_SPAWN
              else "pinned_home_row_no_memory")),
            population,
        )
    )


def _anchored_line(gate: TravelGate, row: Position, jump: float) -> str:
    return (
        "WORLD_TRAVEL_RETURN_ANCHORED gate={0} scene_id={1} "
        "at=({2:.3f},{3:.3f},{4:.3f}) jump={5:.3f} fire_radius={6:.3f} "
        "arm_radius={7:.3f}"
        .format(
            gate.name, row.scene_id, row.x, row.y, row.z, jump,
            gate.fire_radius, gate.arm_radius,
        )
    )


def _first_sight_line(gate: TravelGate, row: Position) -> str:
    return (
        "WORLD_TRAVEL_RETURN_ANCHORED_UNVERIFIED gate={0} scene_id={1} "
        "at=({2:.3f},{3:.3f},{4:.3f}) reason=first_report_of_a_session_that_"
        "did_not_do_the_travelling no_jump_was_observed=true "
        "fire_radius={5:.3f} arm_radius={6:.3f}"
        .format(
            gate.name, row.scene_id, row.x, row.y, row.z,
            gate.fire_radius, gate.arm_radius,
        )
    )


def _dwell_line(
    gate: TravelGate,
    row: Position,
    horizontal: float,
    counted: int,
    needed: int,
) -> str:
    return (
        "WORLD_TRAVEL_DWELL gate={0} scene_id={1} at=({2:.3f},{3:.3f},{4:.3f}) "
        "dist={5:.3f} still_reports={6}/{7}"
        .format(
            gate.name, row.scene_id, row.x, row.y, row.z, horizontal,
            counted, needed,
        )
    )


def _discontinuity_line(row: Position, previous: Position, step: float) -> str:
    return (
        "WORLD_TRAVEL_DISCONTINUITY scene_id={0} at=({1:.3f},{2:.3f},{3:.3f}) "
        "previous=({4:.3f},{5:.3f},{6:.3f}) step={7:.3f} "
        "no_gate_may_arm_or_fire_on_this_report=true"
        .format(
            row.scene_id, row.x, row.y, row.z,
            previous.x, previous.y, previous.z, step,
        )
    )


def _settled_line(row: Position, jump: float, reports: int) -> str:
    return (
        "WORLD_TRAVEL_SETTLED scene_id={0} at=({1:.3f},{2:.3f},{3:.3f}) "
        "jump={4:.3f} reports={5}"
        .format(row.scene_id, row.x, row.y, row.z, jump, reports)
    )


def _stranded_line(
    row: Position, remembered: Position | None, reports: int
) -> str:
    # ``remembered`` is the row the player crossed on, and _advance_transit
    # is the only caller, so it is never None.  There used to be an invented
    # (0,0,0) fallback here; an off-map coordinate presented as a recovery row
    # is worse than no recovery row, and it was unreachable dead code.
    home = remembered
    return (
        "WORLD_TRAVEL_STRANDED scene_id={0} reports={1} "
        "row=({2},{3},{4:.3f},{5:.3f},{6:.3f}) "
        "restore_row=({7},{8},{9:.3f},{10:.3f},{11:.3f}) "
        "restore_row_is_remembered={12}"
        .format(
            row.scene_id, reports,
            row.scene_id, row.scene_seq, row.x, row.y, row.z,
            home.scene_id, home.scene_seq, home.x, home.y, home.z,
            remembered is not None,
        )
    )


def departure_report(departure: TravelDeparture) -> dict:
    """One flat dict for a ticket or a report - no side effects.

    Carries the two nonclaims that a reader of a successful departure is most
    likely to forget: the teleport does not position the avatar, and nobody
    knows what happened to the remote actors.
    """
    if type(departure) is not TravelDeparture:
        raise ValueError("departure report needs a TravelDeparture")
    return {
        "gate": departure.gate.name,
        "role": departure.gate.role,
        "from_scene_id": departure.gate.from_scene_id,
        "to_scene_id": departure.gate.to_scene_id,
        "model_id": departure.destination.model_id,
        "crossed_at": (
            departure.crossed_at.x, departure.crossed_at.y,
            departure.crossed_at.z,
        ),
        "arrival_row": (
            departure.arrival.scene_id, departure.arrival.scene_seq,
            departure.arrival.x, departure.arrival.y, departure.arrival.z,
        ),
        "teleport_fields": departure.teleport_fields,
        # WHICH PHASE THIS CROSSING IS IN.  Without it a report rendered from
        # a staged-and-abandoned crossing is byte-identical to one rendered
        # from a committed departure, which is the exact confusion the two
        # phases exist to prevent - in the one function whose product ends up
        # in tickets and reports.  Found by the adversary pass of round
        # e7q6yy.
        "crossing_state": departure.crossing.state,
        "action_label": departure.action_label,
        "population_source": departure.population_source,
        "left_from_row": (
            departure.left_from.scene_id,
            departure.left_from.scene_seq,
            departure.left_from.x,
            departure.left_from.y,
            departure.left_from.z,
        ),
        "destination_has_authored_entry":
            departure.destination.has_authored_entry,
        "destination_persists_characters":
            departure.destination.persists_characters,
        "destination_sent_before": departure.destination.sent_before,
        "avatar_position_is_not_set_by_this_teleport": True,
        "remote_actors_after_switch": "unknown_RE077_T5",
    }
