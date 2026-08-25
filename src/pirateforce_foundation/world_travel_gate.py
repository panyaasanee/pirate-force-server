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
    walk this project holds, every walking report moved and three stationary
    runs of 3, 6 and 3 identical reports exist - so standing still is
    measurably distinguishable from passing through, and it is also the only
    thing in this design that a player DOES rather than has done to them.

    NOTHING HERE IS BEHIND A FLAG.  There is no scenario file to load and no
    argument to pass.  What stands between this module and a player is one call
    site in ``runtime.py``, which is the chief's file - see ``CORE-REQUEST-004``
    in the round's PR body for the exact call.  Until that call exists a player
    walks past Columbus and nothing happens.

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
``reports/move_cadence001_smoke/replay_output.txt`` in this round rather than
quoted from a docstring - has a median step of 139.26 units and a largest of
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

WHAT THIS MODULE DELIBERATELY DOES NOT DO.  It composes no bytes and sends
nothing.  It returns the five arguments ``legacy.make_login_teleport`` takes and
the row to persist, and the caller owns both.  It does not populate the
destination: ``world_scene_travel.population_source`` answers ``None`` anywhere
but home, and ``world_population.build_world_population`` refuses there, so the
bg0001 census cannot follow a player into a football field or a film set.
"""

from __future__ import annotations

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


@dataclass(frozen=True)
class TravelDeparture:
    """Everything one crossing hands back.  Nothing here has been sent."""

    gate: TravelGate
    destination: SceneDestination
    crossed_at: Position
    arrival: Position
    teleport_fields: tuple[int, int, float, float, float]
    action_label: str
    population_source: str | None
    left_from: Position
    console_lines: tuple[str, ...]

    @property
    def console_line(self) -> str:
        return self.console_lines[0]


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

    def __init__(
        self,
        gates: tuple[TravelGate, ...] | None = None,
        settings: TravelGateSettings | None = None,
        *,
        registry: SceneRegistry | None = None,
        emit=print,
    ):
        if not callable(emit):
            raise ValueError("emit must be callable")
        # ONE registry object, not two.  Validating the gates against one
        # parse and firing them against a second parse of the same file means
        # an edit between the two turns _fire's lookup into a bare KeyError -
        # the exact swallowable type TravelGateRefused exists to avoid.
        self._registry = registry or world_scene_travel.load_scene_registry()
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

        THE CONDITION IS ``departures == 0`` AND IT IS THE WHOLE GUARD.  After
        a strand inside THIS session the client never loaded the destination,
        so its reports are still the old scene's coordinates, and anchoring
        there would put the way home on a coordinate that does not exist in
        the scene the row names.  A session that has already sent somebody
        somewhere therefore anchors on a measured landing or not at all.
        """
        if not gate.centre_is_measured_at_runtime:
            return None
        if self._departures != 0 or self.in_transit:
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
            self._emit(_refused_line(gate, "target_scene_zero", row))
            return None
        if teleport_fields[1] != SCENE_SEQUENCE:
            self._emit(_refused_line(
                gate, "scene_sequence_{0}_not_{1}".format(
                    teleport_fields[1], SCENE_SEQUENCE), row))
            return None
        label = "{0}_{1}_TO_SCENE{2}_TELEPORT".format(
            ACTION_LABEL_PREFIX, gate.role.upper(), gate.to_scene_id,
        )
        population = world_scene_travel.population_source(gate.to_scene_id)
        lines = (
            _depart_line(gate, target, row, arrival, population, remembered_used),
        )
        for line in lines:
            self._emit(line)

        # Order matters, and tests/test_world_travel_gate.py proves it rather
        # than only saying it. The state is committed only after the lines are
        # out, so a console that raises cannot leave a player mid-transit with
        # nothing in the log saying why.
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

        return TravelDeparture(
            gate=gate,
            destination=target,
            crossed_at=row,
            arrival=arrival,
            teleport_fields=teleport_fields,
            action_label=label,
            population_source=population,
            left_from=row,
            console_lines=lines,
        )



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
