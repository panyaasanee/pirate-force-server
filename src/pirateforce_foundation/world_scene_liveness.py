"""The character who was left in a scene the client may never have opened.

LANE-A build order: ``BUILD-002`` / ``M2``, the half of the door out of town
that nobody owns - not the crossing, but what happens to the person on the
other side of it when the crossing worked and the SCENE did not.

    THIS MODULE WAS BUILT TO REWRITE THAT PERSON'S ROW AT LOGIN, AND THE
    ADVERSARIAL PASS OF THE SAME ROUND PROVED IT MUST NOT.  The retraction is
    the first thing in this file because it is the most important thing in it,
    and because a reader who skims and wires the obvious call would otherwise
    ship the harm.  Read "WHY THIS DOES NOT REWRITE ANYTHING" before using
    anything below it.

WHAT A PLAYER WOULD LIVE THROUGH IF NOBODY OWNED IT.  A departure rewrites the
durable position row to the destination scene; that is how travel works and it
is not negotiable.  ``world_travel_gate`` states the consequence plainly in its
own pin: "if the client never loads that scene, the character's row still says
278, and ``world_scene_entry`` will send them there again on every login."

    AND ONE CORRECTION TO THAT SURVEY, FOUND BY THE ADVERSARY: the login path
    the pin describes is not the login path that runs today.  Nothing imports
    ``world_scene_entry``, and ``runtime.py:3675`` sends
    ``legacy.make_login_teleport(1, 0)`` on the flagless path - scene 1,
    hardcoded, every login, no scenario.  Whether that rescues a row that says
    278, strands it, or does something else has never been measured.  So the
    premise "they are sent back there on every login" is UNMEASURED at HEAD,
    not established, and this module does not rest on it.

WHY THIS DOES NOT REWRITE ANYTHING.  The only fact this module could learn is
the ``WORLD_TRAVEL_SETTLED`` line, and that line's scene id does not come from
the client.  ``world_travel_gate.observe`` says so itself::

    "row is the row AFTER the runtime has checkpointed the client's reading,
     so it carries the scene the server believes the player is in together
     with the position the client just reported"

The client contributes a coordinate delta.  The server contributes the scene
id.  So a settle line is A COORDINATE DISCONTINUITY THE SERVER LABELLED WITH A
SCENE ID - not a client saying where it is.  Two things follow, and the
adversary ran both against the real gate rather than arguing them:

1.  FALSE LEARN.  A client that never loads the destination and is still
    standing in Port Royal produces a settle the moment any one report moves
    more than ``jump_units``.  ``world_travel_gate.py:1034-1037`` lists the
    causes itself - "a straggler frame from before a switch, a client
    correcting itself, or a teleport somebody else sent" - and the gate pin's
    nonclaim 11 says an attended round on another lane can cross this gate.
    The ledger would then trust 278 on Port Royal coordinates, and every
    stranded character afterwards would be honoured straight back into the
    scene that stranded them, with a console line saying there was evidence.

2.  STARVED LEDGER.  ``_depart_line`` carries
    ``avatar_position_is_not_set_by_this_teleport=V112``.  If that holds
    across a scene boundary, a client that DOES load the destination keeps its
    coordinates and reports ordinary walking steps, so nothing ever exceeds
    ``jump_units``, nothing settles, and the crossing strands.  A rewriting
    guard would then yank a player who genuinely arrived back to Port Royal at
    every login, destroying their row each time, while the console printed
    "no evidence" - which reads exactly like the guard working.

    The gate pin says outright: "Nobody in this project has measured where a
    player stands after a CROSS-SCENE switch."  V112 and V137 disagree and
    neither crossed a scene boundary.  So branch 2 is not a corner case; it is
    one of two unmeasured branches, and it is the one where an automatic
    rewrite takes away exactly what ``M2`` is about to add.

THEREFORE, BY DEFAULT, THIS MODULE ONLY REPORTS.  ``decide`` returns a
decision whose ``rewrites_the_row`` is False, and the row it hands back is the
row that came in.  The substitution exists behind ``rewrite=True`` and must
stay off until somebody measures whether an arrival produces a coordinate
jump.  ``RIDER-081-B`` on ``GT-081`` asks a tester who is already crossing to
write down the HUD coordinates on both sides, which answers it.

WHAT IT DOES DO, AND WHY THAT IS STILL WORTH WIRING.  One line per login,
printed on every branch, naming what the row says, whether any arrival was
ever recorded for that scene in this process, and what the way home would be.
Today nobody can tell "the guard ran and found nothing wrong" from "the guard
never ran", and nobody can tell a stranded row from a healthy one without
opening the database.  A line costs nothing and turns both into something a
tester can paste.

THE CROSS-CHECK THAT KEEPS THE FALSE LEARN OUT.  A settle line is only
recorded when its coordinates are plausible for the scene it names, measured
against the pinned spawn the registry already carries.  The Port Royal settle
in branch 1 above is tens of thousands of units from anything in scene 278 and
is refused on arithmetic.  This does NOT make the fact mean "the scene opened"
- nothing available to this server means that - it only removes the cheapest
way of being wrong.  A scene the registry pins no spawn for is recorded with
``cross_checked=False`` so a reader can tell the two apart.

WHERE THE LEDGER STARTS.  Two scene ids are pinned in this tree as
``world_scene_travel.MEASURED_SCENE_IDS``, whose own documentation calls them
"scene ids a live client in this project has accepted":

* scene 1, Port Royal.
* scene 2, Prison Exile Island - ``docs/EXPERIMENT_LEDGER.md`` records
  SCENE-001 as a runtime pass in which the client loaded and rendered it.

They are seeded with ``from_this_process=False`` so an inherited fact is never
read as something this boot saw.  Scene 278 is not seeded, and hand-seeding it
is forbidden: a fact saying a client opened a scene no client has opened would
make the report claim evidence that does not exist.

WHAT THIS MODULE DOES NOT DO.  It does not write: no database, no file, no
socket.  It does not move a character who is already live from one scene to
another - that is ``RE-077``.  ``T5`` of that ticket is closed as a BOUNDED
NEGATIVE about whether the client keeps or drops REMOTE ACTORS across a
switch, and it refuses both readings; it is not about moving a character and
must not be cited as if it were.  It does not claim scene 278 loads, renders,
or can be stood in.  And it does not second-guess a live client: with the
rewrite off it cannot, and with the rewrite on it would - see
``world_travel_gate._anchor_on_first_sight``, which is also a login-time
on-a-row recovery and which a rewritten row would silently disable.

WHAT THE TWO CITATIONS THAT USED TO BE HERE ACTUALLY SAY.  Both were quoted
one step stronger than their sources and the adversary caught both.  They are
kept, corrected, because the correction is the useful part:

* ``RE-077`` measured status ``+0x0C = 2`` with no fallback for a scene id
  with NO ROW in ``SCENE_NAME``.  That is the table-miss branch.  Scene 278
  HAS a row and a model id, so RE-077 does not describe what happens when its
  load fails, and no claim here rests on it.  It is also a static
  disassembly result, which is not the client-observable layer.
* ``MOVE-CADENCE-001`` recorded a stationary client sending zero
  ``TargetPosVital`` in 42 frames in one capture - and, in the SAME report, a
  stationary client re-sending its position, 24 of 29 frames carrying
  ``moving=0``.  So "a stuck client goes quiet" is one of two recorded
  behaviours, not a rule.  [PROPOSED, NOT MEASURED.]

THE FRAME-PATH CONTRACT.  ``observe_console_line`` and ``decide`` are total:
they never raise, on any input, except ``KeyboardInterrupt`` and ``SystemExit``
which are allowed through on purpose - a login path that swallows Ctrl-C is a
process that cannot be stopped.  ``observe_arrival`` is the structured entry
point and DOES raise on a bad scene id, because its caller passes a value it
already has in hand.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import world_scene_travel
from .model import Position

# This module ships on the flagless path.  Neither flag is read by any code;
# they are the convention markers this lane's files carry, and nothing about
# them makes anything run - runtime.py is the chief's file and calls none of
# this yet.
test_only = False
production_allowed = True

HOME_SCENE_ID = world_scene_travel.HOME_SCENE_ID

DECISION_HONOUR = "honour"
DECISION_FLAG = "flag_no_arrival_recorded"
DECISION_SEND_HOME = "send_home"

REASON_HOME_ROW = "home_row"
REASON_RECORDED_THIS_PROCESS = "arrival_recorded_this_process"
REASON_RECORDED_BEFORE_THIS_PROCESS = "accepted_before_this_process"
REASON_NO_RECORD = "no_arrival_recorded"
REASON_UNREADABLE_ROW = "unreadable_row"
REASON_UNREADABLE_LEDGER = "unreadable_ledger"
REASON_HOME_UNAVAILABLE = "home_row_unavailable"
REASON_STOOD_DOWN = "stood_down"

# The exact prefix world_travel_gate._settled_line() writes.  Pinned against
# the real producer by the tests, and never widened to a substring search:
# eight other lines in that module carry a scene_id= field, and one of them is
# WORLD_TRAVEL_STRANDED, emitted in exactly the case this module cares about.
SETTLED_PREFIX = "WORLD_TRAVEL_SETTLED "

# How far from a scene's pinned spawn a settle may land and still be recorded
# for that scene.  A margin, not a boundary: the registry pins one spawn per
# scene and no scene's walkable area, so this only has to be wide enough never
# to refuse a real arrival and narrow enough to refuse a settle emitted while
# the client is still standing in the scene it departed from.  The two pinned
# spawns that matter here are 25705 units apart, and the test re-derives that
# separation from the registry so this number cannot drift past it in silence.
CROSS_CHECK_RADIUS_UNITS = 12000.0


@dataclass(frozen=True)
class ArrivalFact:
    """One recorded arrival, and exactly how much it is worth.

    NOT "a client was seen alive in this scene".  It is: a coordinate
    discontinuity, labelled with this scene id by the SERVER, whose
    coordinates were plausible for the scene when the registry pinned enough
    to check.  Read the module docstring before treating it as more.
    """

    scene_id: int
    evidence: str
    from_this_process: bool
    cross_checked: bool


@dataclass(frozen=True)
class LivenessDecision:
    """What is known about the row a character already has.

    ``position`` is always a usable row, on every branch, and it is the row
    that came in unless ``rewrites_the_row`` is True.  ``home_if_asked`` is
    what a rewrite WOULD have used - present on the flag branch so the console
    line and an operator can both see it without the module acting on it.
    """

    decision: str
    reason: str
    scene_id: int | None
    stored: Position | None
    position: Position | None
    home_if_asked: Position | None
    fact: ArrivalFact | None

    @property
    def sends_home(self) -> bool:
        return self.decision == DECISION_SEND_HOME

    @property
    def rewrites_the_row(self) -> bool:
        """True only when the caller owes the database a write.

        A separate name from ``sends_home`` on purpose: a caller reads this one
        at the write site, and a future decision that moves a character
        WITHOUT rewriting their row (or the reverse) must not inherit the
        wrong meaning from a property named after where the player ends up.
        """
        return self.decision == DECISION_SEND_HOME


class SceneLivenessLedger:
    """Which scenes an arrival has been recorded for, in this process.

    One per server process, created at start-up with ``preload`` and handed on
    with ``from_preloaded`` - the same shape ``COO-DECISION 20260826_0655``
    required of ``TravelGateSet``, and for the same reason: a per-login
    construction turns a bad pin into "nobody can log in".  ``preload`` reads
    the scene registry once, so a broken registry fails the boot in front of
    one operator rather than failing a player.

    IT COUNTS WHAT IT WAS SHOWN.  ``lines_seen`` and ``settle_lines_seen``
    exist so that a half-wiring is visible in the console instead of looking
    exactly like an honest empty ledger: a ledger consulted at login but never
    fed from the emit hook reports zero lines seen, forever, and says so.

    This server is strictly serial (``FINDINGS_R18_SERVER_IS_STRICTLY_SERIAL``)
    so the ledger takes no lock.  ``observe_console_line`` is read-modify-write,
    so if that ever stops being true, "the first evidence is the evidence"
    becomes last-writer-wins and this class is the first thing needing a lock.
    """

    __slots__ = (
        "_facts", "_home", "_registry", "_stood_down",
        "_lines_seen", "_settle_lines_seen", "_refused_by_cross_check",
    )

    _preloaded: "SceneLivenessLedger | None" = None

    def __init__(
        self,
        facts: dict[int, ArrivalFact],
        home: Position | None,
        registry: Any = None,
    ):
        self._facts = dict(facts)
        self._home = home
        self._registry = registry
        self._stood_down = None
        self._lines_seen = 0
        self._settle_lines_seen = 0
        self._refused_by_cross_check = 0

    # -- construction ------------------------------------------------------

    @classmethod
    def seeded(cls, registry: Any = None) -> "SceneLivenessLedger":
        """The ledger a server starts with: the inherited ids and the way home.

        Raises whatever ``world_scene_travel`` raises for a bad registry.  That
        is the point - this runs at start-up.
        """
        resolved = (
            registry if registry is not None
            else world_scene_travel.load_scene_registry()
        )
        home = world_scene_travel.home_return_position(resolved)
        facts = {}
        for scene_id in world_scene_travel.MEASURED_SCENE_IDS:
            facts[scene_id] = ArrivalFact(
                scene_id=scene_id,
                evidence=_seed_evidence(scene_id),
                from_this_process=False,
                cross_checked=False,
            )
        return cls(facts, home, resolved)

    @classmethod
    def preload(cls, registry: Any = None) -> "SceneLivenessLedger":
        """Build the one ledger this process uses, at server start.

        Kept separate from ``seeded`` so the login path has a call that cannot
        read a file: ``from_preloaded`` never touches disk and never raises.
        """
        cls._preloaded = cls.seeded(registry)
        return cls._preloaded

    @classmethod
    def forget_preloaded(cls) -> None:
        """Drop the process ledger.  For tests, and for a shutdown that means it."""
        cls._preloaded = None

    @classmethod
    def from_preloaded(cls) -> "SceneLivenessLedger":
        """The preloaded ledger, or an inert one that says so.

        Never raises and never reads a file.  If ``preload`` was not called,
        the session gets a ledger that stands down: every login is honoured and
        one console line names the reason.  The failure mode of finding nothing
        must be "do nothing", not "act on an empty ledger" - an empty ledger
        would flag every character in the game.
        """
        if cls._preloaded is not None:
            return cls._preloaded
        inert = cls({}, None, None)
        inert.stand_down("preload_was_never_called")
        return inert

    @classmethod
    def empty(cls, home: Position | None = None) -> "SceneLivenessLedger":
        """A ledger with no facts at all, for tests and for a caller that seeds
        every fact itself.  Never use this on a boot: with no fact for scene 1
        every character in the game is flagged, which is noise rather than harm
        today only because nothing rewrites a row.
        """
        return cls({}, home, None)

    # -- state -------------------------------------------------------------

    @property
    def home(self) -> Position | None:
        return self._home

    @property
    def registry(self) -> Any:
        return self._registry

    @property
    def stood_down(self) -> str | None:
        return self._stood_down

    @property
    def lines_seen(self) -> int:
        return self._lines_seen

    @property
    def settle_lines_seen(self) -> int:
        return self._settle_lines_seen

    @property
    def refused_by_cross_check(self) -> int:
        return self._refused_by_cross_check

    @property
    def observed_ids(self) -> tuple[int, ...]:
        return tuple(sorted(self._facts))

    def facts(self) -> tuple[ArrivalFact, ...]:
        return tuple(self._facts[key] for key in sorted(self._facts))

    def stand_down(self, reason: Any) -> str:
        """Turn this ledger into something that never changes an answer.

        Default-closed, in the spirit of ``COO-DECISION 20260826_0655``
        condition two: a caller that cannot satisfy this module's assumptions -
        an opt-in scenario lane, a boot with no preload - switches it off in
        one call rather than being asked to remember a list of lanes.
        """
        self._stood_down = _ascii_reason(reason)
        return self._stood_down

    def knows(self, scene_id: Any) -> bool:
        return self.fact(scene_id) is not None

    def fact(self, scene_id: Any) -> ArrivalFact | None:
        wanted = _scene_id(scene_id)
        if wanted is None:
            return None
        return self._facts.get(wanted)

    # -- learning ----------------------------------------------------------

    def observe_arrival(
        self, scene_id: Any, evidence: Any, *, cross_checked: bool = False
    ) -> bool:
        """Record an arrival for ``scene_id``.  The structured entry point.

        Returns True if this is the first fact for that scene.  An existing
        fact is NEVER overwritten: the first evidence is the evidence.

        Raises ``ValueError`` on a bad scene id or empty evidence.
        """
        wanted = _scene_id(scene_id)
        if wanted is None:
            raise ValueError("an arrival needs a scene id in 0..65535")
        if type(evidence) is not str or not evidence.strip():
            raise ValueError("an arrival needs its evidence")
        if wanted in self._facts:
            return False
        self._facts[wanted] = ArrivalFact(
            scene_id=wanted,
            evidence=evidence.strip(),
            from_this_process=True,
            cross_checked=bool(cross_checked),
        )
        return True

    def seed_observed(self, scene_id: Any, evidence: Any) -> bool:
        """Hand back a fact earned by an EARLIER process.

        Same rules as ``observe_arrival`` except the fact is marked as not from
        this process.  Read the "hand-seeding is forbidden" sentence in the
        module docstring before calling this with anything a client did not do.
        """
        wanted = _scene_id(scene_id)
        if wanted is None:
            raise ValueError("a seeded fact needs a scene id in 0..65535")
        if type(evidence) is not str or not evidence.strip():
            raise ValueError("a seeded fact needs its evidence")
        if wanted in self._facts:
            return False
        self._facts[wanted] = ArrivalFact(
            scene_id=wanted,
            evidence=evidence.strip(),
            from_this_process=False,
            cross_checked=False,
        )
        return True

    def observe_console_line(self, line: Any) -> int | None:
        """Read one emitted console line; record a settle if that is what it is.

        THE FRAME-PATH ENTRY POINT.  Total: returns the scene id it recorded,
        or ``None`` for every other line and for anything that is not a line at
        all.  It never raises, and it never records twice for the same scene.

        Accepts any ``str`` including subclasses, because the line arrives
        through whatever the caller's emit hook is and a logging wrapper is a
        ``str`` subclass.  It does NOT accept a line with anything in front of
        the prefix: a timestamped log line is a different producer and this
        parser is pinned to one.
        """
        if not isinstance(line, str):
            return None
        self._lines_seen += 1
        if not line.startswith(SETTLED_PREFIX):
            return None
        self._settle_lines_seen += 1
        scene_id = _scene_id_field(line)
        if scene_id is None:
            return None
        if scene_id in self._facts:
            return scene_id
        checked = _cross_check(self._registry, scene_id, _settled_at(line))
        if checked is False:
            self._refused_by_cross_check += 1
            return None
        self._facts[scene_id] = ArrivalFact(
            scene_id=scene_id,
            evidence="coordinate discontinuity labelled with this scene id by "
                     "the server: " + line.strip(),
            from_this_process=True,
            cross_checked=checked is True,
        )
        return scene_id


def _seed_evidence(scene_id: int) -> str:
    if scene_id == 1:
        return ("world_scene_travel.MEASURED_SCENE_IDS - a scene id a live "
                "client in this project has accepted")
    if scene_id == 2:
        return ("docs/EXPERIMENT_LEDGER.md SCENE-001 runtime load pass - the "
                "client loaded and rendered Prison Exile Island")
    return "world_scene_travel.MEASURED_SCENE_IDS"


def _ascii_reason(value: Any, limit: int = 80) -> str:
    """Whatever came in, out comes something a cp874 console can print.

    A reason can carry ``str(exception)``, and an exception message can hold
    any character at all.  A reason that cannot be printed is a reason nobody
    sees, and a carriage return in one rewrites the line it should have added.
    """
    try:
        raw = str(value)
    except BaseException:       # noqa: BLE001 - a __str__ that raises is input
        return "unprintable"
    out = "".join(
        char if 0x20 <= ord(char) < 0x7F else "?" for char in raw
    ).strip()
    return (out[:limit] or "none").replace(" ", "_")


def _scene_id(value: Any) -> int | None:
    # bool is an int subclass, so the exact-type test is what excludes True
    # from being read as scene 1.  It is not redundant with the range test.
    if type(value) is not int:
        return None
    if not 0 <= value <= 0xFFFF:
        return None
    return value


def _scene_id_field(line: str) -> int | None:
    """The ``scene_id=`` field of a settle line, or None if it is not readable.

    Deliberately strict: the field has to be the first one after the prefix,
    which is where ``_settled_line`` puts it, and it has to be ASCII digits.
    A lenient reader would learn a scene id out of a line that happened to
    contain the word.
    """
    rest = line[len(SETTLED_PREFIX):]
    if not rest.startswith("scene_id="):
        return None
    raw = rest[len("scene_id="):].split(" ", 1)[0]
    if not raw or not raw.isascii() or not raw.isdigit():
        return None
    try:
        return _scene_id(int(raw))
    except ValueError:
        # Reachable, and an earlier version of this file claimed it was not:
        # CPython 3.11 refuses int() on a string of more than 4300 digits.
        return None


def _settled_at(line: str) -> tuple[float, float, float] | None:
    """The ``at=(x,y,z)`` field of a settle line, or None if unreadable."""
    head = line.find(" at=(")
    if head < 0:
        return None
    tail = line.find(")", head)
    if tail < 0:
        return None
    parts = line[head + len(" at=("):tail].split(",")
    if len(parts) != 3:
        return None
    out = []
    for part in parts:
        try:
            value = float(part)
        except ValueError:
            return None
        if value != value or value in (float("inf"), float("-inf")):
            return None
        out.append(value)
    return (out[0], out[1], out[2])


def _cross_check(
    registry: Any, scene_id: int, where: tuple[float, float, float] | None
) -> bool | None:
    """True: plausible.  False: refuse it.  None: nothing to check against.

    Never raises: a registry that cannot answer is "nothing to check against",
    which records the fact and marks it unchecked, rather than losing a real
    arrival to a bad lookup.
    """
    if registry is None or where is None:
        return None
    try:
        spawn = registry[scene_id].spawn
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException:
        return None
    if spawn is None:
        return None
    try:
        dx = float(where[0]) - float(spawn[0])
        dy = float(where[1]) - float(spawn[1])
        distance = (dx * dx + dy * dy) ** 0.5
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException:
        return None
    if distance != distance:
        return None
    return distance <= CROSS_CHECK_RADIUS_UNITS


def decide(
    stored: Any,
    ledger: Any,
    *,
    rewrite: bool = False,
) -> LivenessDecision:
    """What is known about the row this character already has.  Never raises.

    ``rewrite`` DEFAULTS TO FALSE AND MUST STAY FALSE until somebody measures
    whether arriving in another scene produces a coordinate jump.  Read "WHY
    THIS DOES NOT REWRITE ANYTHING" in the module docstring; with it on, the
    branch where an arrival is quiet yanks a player who arrived safely back to
    town at every login and destroys their row each time.
    """
    row = stored if isinstance(stored, Position) else None
    scene_id = _scene_id(row.scene_id) if row is not None else None
    if not isinstance(ledger, SceneLivenessLedger):
        # The ledger is what is broken, not the row, and the reason has to say
        # so: an operator reading "unreadable row" would go looking in the
        # database for a fault that is in the wiring.
        return LivenessDecision(
            decision=DECISION_HONOUR,
            reason=REASON_UNREADABLE_LEDGER,
            scene_id=scene_id,
            stored=row,
            position=row,
            home_if_asked=None,
            fact=None,
        )
    if ledger.stood_down is not None:
        return LivenessDecision(
            decision=DECISION_HONOUR,
            reason=REASON_STOOD_DOWN,
            scene_id=scene_id,
            stored=row,
            position=row,
            home_if_asked=None,
            fact=None,
        )
    if row is None or scene_id is None:
        # Nothing readable to decide about.  HONOUR is the right answer and not
        # a cop-out: this module's only power is to substitute a row, and it
        # has no row to substitute FOR.
        return LivenessDecision(
            decision=DECISION_HONOUR,
            reason=REASON_UNREADABLE_ROW,
            scene_id=scene_id,
            stored=row,
            position=row,
            home_if_asked=None,
            fact=None,
        )
    if scene_id == HOME_SCENE_ID:
        return LivenessDecision(
            decision=DECISION_HONOUR,
            reason=REASON_HOME_ROW,
            scene_id=scene_id,
            stored=row,
            position=row,
            home_if_asked=None,
            fact=ledger.fact(scene_id),
        )
    fact = ledger.fact(scene_id)
    if fact is not None:
        return LivenessDecision(
            decision=DECISION_HONOUR,
            reason=(
                REASON_RECORDED_THIS_PROCESS if fact.from_this_process
                else REASON_RECORDED_BEFORE_THIS_PROCESS
            ),
            scene_id=scene_id,
            stored=row,
            position=row,
            home_if_asked=None,
            fact=fact,
        )
    home = ledger.home
    if home is None:
        return LivenessDecision(
            decision=DECISION_HONOUR,
            reason=REASON_HOME_UNAVAILABLE,
            scene_id=scene_id,
            stored=row,
            position=row,
            home_if_asked=None,
            fact=None,
        )
    if not rewrite:
        return LivenessDecision(
            decision=DECISION_FLAG,
            reason=REASON_NO_RECORD,
            scene_id=scene_id,
            stored=row,
            position=row,
            home_if_asked=home,
            fact=None,
        )
    return LivenessDecision(
        decision=DECISION_SEND_HOME,
        reason=REASON_NO_RECORD,
        scene_id=scene_id,
        stored=row,
        position=home,
        home_if_asked=home,
        fact=None,
    )


def liveness_console_line(decision: Any, ledger: Any = None) -> str:
    """One line per login, printed whichever way the decision went.

    A line only on the interesting branch is a line nobody can use to tell
    "this ran and found nothing wrong" from "this never ran", which is the
    exact confusion that made this lane re-measure its own wiring three rounds
    running.  Passing the ledger adds the counters, which are what tell an
    honest empty ledger from one nobody ever fed.
    """
    if type(decision) is not LivenessDecision:
        raise ValueError("a liveness console line needs a LivenessDecision")
    stored = decision.stored
    where = (
        "({0:.3f},{1:.3f},{2:.3f})".format(stored.x, stored.y, stored.z)
        if stored is not None else "unreadable"
    )
    fact = decision.fact
    evidence = "none"
    if fact is not None:
        evidence = "this_process" if fact.from_this_process else "inherited"
        if fact.from_this_process and not fact.cross_checked:
            evidence += "_unchecked"
    line = (
        "WORLD_SCENE_LIVENESS decision={0} reason={1} stored_scene={2} "
        "stored_at={3} evidence={4}"
        .format(
            decision.decision,
            decision.reason,
            "none" if decision.scene_id is None else decision.scene_id,
            where,
            evidence,
        )
    )
    home = decision.position if decision.sends_home else decision.home_if_asked
    if home is not None:
        label = "home" if decision.sends_home else "home_if_asked"
        line += (
            " {0}_scene={1} {0}_at=({2:.3f},{3:.3f},{4:.3f})"
            .format(label, home.scene_id, home.x, home.y, home.z)
        )
    if isinstance(ledger, SceneLivenessLedger):
        line += (
            " lines_seen={0} settles={1} refused={2} recorded={3}"
            .format(
                ledger.lines_seen, ledger.settle_lines_seen,
                ledger.refused_by_cross_check,
                "+".join(str(item) for item in ledger.observed_ids) or "none",
            )
        )
        if ledger.stood_down is not None:
            line += " stood_down=" + ledger.stood_down
    return line


def liveness_report(decision: Any, ledger: Any = None) -> dict:
    """One flat dict for a round note or an attended ticket."""
    if type(decision) is not LivenessDecision:
        raise ValueError("a liveness report needs a LivenessDecision")
    stored = decision.stored
    position = decision.position
    home = decision.home_if_asked
    return {
        "decision": decision.decision,
        "reason": decision.reason,
        "sends_home": decision.sends_home,
        "rewrites_the_row": decision.rewrites_the_row,
        "stored_scene_id": None if stored is None else stored.scene_id,
        "stored_position": (
            None if stored is None else [stored.x, stored.y, stored.z]),
        "used_scene_id": None if position is None else position.scene_id,
        "used_position": (
            None if position is None else [position.x, position.y, position.z]),
        "home_if_asked": None if home is None else [home.x, home.y, home.z],
        "evidence": None if decision.fact is None else decision.fact.evidence,
        "evidence_from_this_process": (
            None if decision.fact is None else decision.fact.from_this_process),
        "evidence_cross_checked": (
            None if decision.fact is None else decision.fact.cross_checked),
        "console_line": liveness_console_line(decision, ledger),
    }
