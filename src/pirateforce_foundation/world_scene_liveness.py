"""The character who was left in a scene the client could not open.

LANE-A build order: ``BUILD-002`` / ``M2``, the half of the door out of town
that nobody owns - not the crossing, but what happens to the person on the
other side of it when the crossing worked and the SCENE did not.

WHAT A PLAYER WOULD LIVE THROUGH IF NOBODY OWNED IT.  A departure rewrites the
durable position row to the destination scene; that is how travel works and it
is not negotiable.  ``world_travel_gate`` states the consequence plainly in its
own pin: "if the client never loads that scene, the character's row still says
278, and ``world_scene_entry`` will send them there again on every login."  The
recoveries it lists are (0) a session that opens with the player ALREADY
reporting positions in the destination anchors a way home on its first report,
(1) a console line an operator reads and a row an operator restores by hand,
(2) ``world_scene_entry.return_ticket``, which nothing calls, and (3) the
teardown step of an attended ticket.

    Recovery (0) is the only one that needs no human, and it is exactly the one
    that cannot fire in the case that matters.  ``RE-077`` measured what the
    shipped client does when a scene will not open: ``cStateSwitchScene`` sets
    status ``+0x0C = 2`` and returns, with no fallback and no second
    ``RequestNext``.  ``MOVE-CADENCE-001`` measured a stationary client sending
    ZERO ``TargetPosVital`` in 42 frames.  A client parked at status 2 does not
    report a position, so there is no first report to anchor on, so recovery
    (0) never runs - and neither does the strand detector, which counts
    reports and cannot count a report that never arrives.

    Every remaining recovery needs a person with database access.  That is the
    hole this module closes: after this, a character stranded in a scene the
    client would not open walks home on their NEXT LOGIN, with nobody's help.

WHAT THIS MODULE DECIDES, AND THE ONE FACT IT DECIDES ON.  At login, before
anything is sent, it answers one question about the row a character already
has: HAS A CLIENT IN THIS PROJECT EVER BEEN SEEN ALIVE IN THAT SCENE?

    yes  -> honour the row.  The player is where they left off.
    no   -> use the way home instead, and hand the caller the row to write.

"Seen alive" is deliberately narrow.  It is not "the scene is in the client's
table" (scene 278 is, and no client has ever opened it), and it is not "the
server sent a teleport there" (the server sending is what got the character
stuck in the first place).  It is: A CLIENT REPORTED ITS OWN POSITION IN THAT
SCENE, which is the one event that cannot happen unless the scene opened.  That
event already exists and already has a name - ``WORLD_TRAVEL_SETTLED``, emitted
by ``world_travel_gate`` when a report jumps further than the settle threshold
after a crossing - and this module reads it rather than inventing a second
notion of arrival.

WHERE THE LEDGER STARTS.  Two scenes carry that evidence from before this
process was born, and both are already pinned in this tree as
``world_scene_travel.MEASURED_SCENE_IDS``:

* scene 1, Port Royal - rendered in every boot this project has ever taken.
* scene 2, Prison Exile Island - ``docs/EXPERIMENT_LEDGER.md:31`` records
  SCENE-001 as a runtime pass in which the client loaded and rendered it.

They are seeded as facts whose ``from_this_process`` is False, so a reader can
always tell an inherited fact from one this boot earned.  Nothing else is
seeded.  Scene 278 in particular is NOT seeded, which is the whole point: it is
the scene the door leads to and no client has opened it yet.

WHAT THIS COSTS, WRITTEN BEFORE ANYBODY ELSE FINDS IT.  The ledger lives in
memory for the life of one server process, because this project has nowhere
else to put it that is not the canonical database.  So:

* A player who genuinely reached scene 278, logged out there, and comes back
  after the SERVER restarted is sent home once, and their row is rewritten to
  Port Royal.  They lose their position in the test stage and they keep their
  character.  That is the asymmetry this module is built on: being moved to
  town is an inconvenience that a second walk through the door undoes, and
  being parked at status 2 forever is a character nobody can play.
* The fix for that cost is persistence, and persistence of this fact belongs
  to whoever owns the schema.  ``seed_observed`` exists so that owner can hand
  the facts back at start-up without this module growing a storage opinion.

  DO NOT "FIX" IT BY SEEDING 278 BY HAND.  A hand-seeded fact says a client
  opened a scene that no client has opened; the next stranded character would
  then be honoured straight back into the scene that stranded them, and the
  console line would say the ledger had evidence.  That is worse than no
  module at all, because it looks like a guard.

WHAT THIS MODULE DOES NOT DO.  It does not write: no database, no file, no
socket.  It hands back a decision and the row that decision implies, and the
caller owns the write, exactly as ``world_scene_entry`` and
``world_travel_gate`` do.  It does not move a character who is already live
from one scene to another - that is ``RE-077``, and ``T5`` of it is closed as a
BOUNDED NEGATIVE, meaning the static evidence refuses BOTH readings and nobody
may shorten it to either one.  It does not claim scene 278 loads, renders, or
can be stood in; the first honest answer to that is a tester's eyes, and the
ledger is built so that the answer arrives as a FACT rather than as an opinion:
the day a client settles in 278, the ledger knows, and every login after it in
that process honours the row.

    AND IT DOES NOT SECOND-GUESS A LIVE CLIENT.  If a client is already
    reporting positions in a scene, ``world_travel_gate`` anchors a way home on
    its own; this module is only consulted at login, on a row, before any of
    that.  Two mechanisms with one job would be one of them undoing the other.

THE FRAME-PATH CONTRACT.  ``observe_console_line`` and ``decide`` are total:
they never raise, on any input, except ``KeyboardInterrupt`` and ``SystemExit``
which are allowed through on purpose - a login path that swallows Ctrl-C is a
process that cannot be stopped.  ``observe_alive`` is the structured entry
point and DOES raise on a bad scene id, because its caller passes a value it
already has in hand and a silent no-op there would lose the one fact the ledger
exists to hold.

WHY NOT PARSE-FREE.  ``world_travel_gate`` reports settles by emitting a
console string; it has no structured settle callback and this lane is not
adding one to a module the chief is wiring this morning.  So the frame-path
entry point reads the line the gate already emits, and
``tests/test_world_scene_liveness.py`` drives a real ``TravelGateSet`` through
a real crossing and feeds this parser the real emitted lines.  If the gate's
format changes, that test goes red - the parser is pinned to a producer, not to
a string somebody typed into a docstring.
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
DECISION_SEND_HOME = "send_home"

REASON_HOME_ROW = "home_row"
REASON_OBSERVED_THIS_PROCESS = "observed_live_this_process"
REASON_OBSERVED_BEFORE_THIS_PROCESS = "observed_live_before_this_process"
REASON_NO_EVIDENCE = "no_liveness_evidence"
REASON_UNREADABLE_ROW = "unreadable_row"
REASON_HOME_UNAVAILABLE = "home_row_unavailable"

# The exact prefix world_travel_gate._settled_line() writes.  Pinned against
# the real producer by the tests; never widened to a substring search, because
# WORLD_TRAVEL_SETTLED is not the only line in that file that carries a
# scene_id= field and matching the wrong one would record a scene the client
# never opened.
SETTLED_PREFIX = "WORLD_TRAVEL_SETTLED "

_SEED_EVIDENCE = {
    1: "rendered in every boot of this project (world_scene_travel."
       "MEASURED_SCENE_IDS)",
    2: "SCENE-001 runtime pass, docs/EXPERIMENT_LEDGER.md:31 - the client "
       "loaded and rendered Prison Exile Island",
}


@dataclass(frozen=True)
class LivenessFact:
    """One scene a client has been seen alive in, and how that is known."""

    scene_id: int
    evidence: str
    from_this_process: bool


@dataclass(frozen=True)
class LivenessDecision:
    """What to do with the row a character already has.

    ``position`` is always the row to USE.  When ``sends_home`` is true it is
    also the row to WRITE, and ``stored`` is what the row said before - kept so
    the caller can print both and so an operator can undo this module by hand.
    """

    decision: str
    reason: str
    scene_id: int | None
    stored: Position | None
    position: Position | None
    fact: LivenessFact | None

    @property
    def sends_home(self) -> bool:
        return self.decision == DECISION_SEND_HOME

    @property
    def rewrites_the_row(self) -> bool:
        """True only when the caller owes the database a write.

        Identical to ``sends_home`` today and deliberately a separate name: a
        caller reads this one at the write site, and a future decision that
        moves a character WITHOUT rewriting their row (or the reverse) must
        not silently inherit the wrong meaning from a property named after
        where the player ends up.
        """
        return self.decision == DECISION_SEND_HOME and self.position is not None


class SceneLivenessLedger:
    """Which scenes a client has been observed alive in, this process.

    One per server process, created at start-up and handed to whatever needs
    it - the same shape ``COO-DECISION 20260826_0655`` required of
    ``TravelGateSet``, and for the same reason: a per-login construction turns
    a bad pin into "nobody can log in".  Construction here reads the scene
    registry once, so a broken registry fails the boot in front of one
    operator instead of failing a player.

    This server is strictly serial (``FINDINGS_R18_SERVER_IS_STRICTLY_SERIAL``)
    so the ledger takes no lock.  If that ever stops being true, this class is
    a mutable shared object and is the first thing that needs one.
    """

    __slots__ = ("_facts", "_home")

    def __init__(self, facts: dict[int, LivenessFact], home: Position | None):
        self._facts = dict(facts)
        self._home = home

    @classmethod
    def seeded(
        cls,
        registry: world_scene_travel.SceneRegistry | None = None,
    ) -> "SceneLivenessLedger":
        """The ledger a server starts with: two inherited facts and the way home.

        Raises whatever ``world_scene_travel`` raises for a bad registry.  That
        is the point - this runs at start-up.
        """
        home = world_scene_travel.home_return_position(registry)
        facts = {}
        for scene_id in world_scene_travel.MEASURED_SCENE_IDS:
            facts[scene_id] = LivenessFact(
                scene_id=scene_id,
                evidence=_SEED_EVIDENCE.get(
                    scene_id, "world_scene_travel.MEASURED_SCENE_IDS"),
                from_this_process=False,
            )
        return cls(facts, home)

    @classmethod
    def empty(cls, home: Position | None = None) -> "SceneLivenessLedger":
        """A ledger with no facts at all, for tests and for a caller that wants
        to seed every fact itself.  Never use this on a boot: with no fact for
        scene 1 every character in the game is sent home to a scene the ledger
        does not believe in, which still works but says the wrong thing in
        every console line.
        """
        return cls({}, home)

    @property
    def home(self) -> Position | None:
        return self._home

    @property
    def observed_ids(self) -> tuple[int, ...]:
        return tuple(sorted(self._facts))

    def facts(self) -> tuple[LivenessFact, ...]:
        return tuple(self._facts[key] for key in sorted(self._facts))

    def knows(self, scene_id: Any) -> bool:
        return self.fact(scene_id) is not None

    def fact(self, scene_id: Any) -> LivenessFact | None:
        if type(scene_id) is not int or isinstance(scene_id, bool):
            return None
        return self._facts.get(scene_id)

    def observe_alive(self, scene_id: Any, evidence: Any) -> bool:
        """Record that a client was seen alive in ``scene_id``.

        Returns True if this is the first fact for that scene.  An existing
        fact is NEVER overwritten: the first evidence is the evidence, and a
        later line cannot quietly restate how a scene came to be trusted.

        Raises ``ValueError`` on a bad scene id or empty evidence.  See the
        module docstring: this is the structured entry point and its caller
        holds a value it already validated.
        """
        wanted = _scene_id(scene_id)
        if wanted is None:
            raise ValueError(
                "a liveness observation needs a scene id in 0..65535")
        if type(evidence) is not str or not evidence.strip():
            raise ValueError("a liveness observation needs its evidence")
        if wanted in self._facts:
            return False
        self._facts[wanted] = LivenessFact(
            scene_id=wanted,
            evidence=evidence.strip(),
            from_this_process=True,
        )
        return True

    def seed_observed(self, scene_id: Any, evidence: Any) -> bool:
        """Hand back a fact earned by an EARLIER process.

        Same rules as ``observe_alive`` except that the fact is marked as not
        from this process, so a console line never claims this boot saw
        something it read from storage.  Read the "DO NOT" paragraph in the
        module docstring before calling this with anything a client did not do.
        """
        wanted = _scene_id(scene_id)
        if wanted is None:
            raise ValueError("a seeded fact needs a scene id in 0..65535")
        if type(evidence) is not str or not evidence.strip():
            raise ValueError("a seeded fact needs its evidence")
        if wanted in self._facts:
            return False
        self._facts[wanted] = LivenessFact(
            scene_id=wanted,
            evidence=evidence.strip(),
            from_this_process=False,
        )
        return True

    def observe_console_line(self, line: Any) -> int | None:
        """Read one emitted console line; record a settle if that is what it is.

        THE FRAME-PATH ENTRY POINT.  Total: returns the scene id it recorded,
        or ``None`` for every other line and for anything that is not a line at
        all.  It never raises, and it never records twice for the same scene.
        """
        if type(line) is not str or not line.startswith(SETTLED_PREFIX):
            return None
        scene_id = _scene_id_field(line)
        if scene_id is None:
            return None
        if scene_id in self._facts:
            return scene_id
        self._facts[scene_id] = LivenessFact(
            scene_id=scene_id,
            evidence="client reported its own position in this scene after a "
                     "crossing: " + line.strip(),
            from_this_process=True,
        )
        return scene_id


def _scene_id(value: Any) -> int | None:
    if type(value) is not int or isinstance(value, bool):
        return None
    if not 0 <= value <= 0xFFFF:
        return None
    return value


def _scene_id_field(line: str) -> int | None:
    """The ``scene_id=`` field of a settle line, or None if it is not readable.

    Deliberately strict: the field has to be the first one after the prefix,
    which is where ``_settled_line`` puts it, and it has to be all digits.  A
    lenient reader here would happily learn a scene id out of a line that
    happened to contain the word.
    """
    rest = line[len(SETTLED_PREFIX):].lstrip()
    if not rest.startswith("scene_id="):
        return None
    raw = rest[len("scene_id="):].split(" ", 1)[0]
    if not raw or not raw.isdigit() or not raw.isascii():
        return None
    try:
        return _scene_id(int(raw))
    except ValueError:      # pragma: no cover - isdigit already excludes it
        return None


def decide(
    stored: Any,
    ledger: Any,
    *,
    registry: world_scene_travel.SceneRegistry | None = None,
) -> LivenessDecision:
    """What to do with the row this character already has.  Never raises.

    ``registry`` is only consulted when the ledger was built without a way
    home, which is a test shape rather than a boot shape; a boot resolves home
    once in ``seeded`` so that the login path touches no disk.
    """
    if type(ledger) is not SceneLivenessLedger:
        return LivenessDecision(
            decision=DECISION_HONOUR,
            reason=REASON_UNREADABLE_ROW,
            scene_id=None,
            stored=None,
            position=None,
            fact=None,
        )
    row = stored if type(stored) is Position else None
    scene_id = _scene_id(row.scene_id) if row is not None else None
    if row is None or scene_id is None:
        # Nothing readable to decide about.  HONOUR is the right answer and not
        # a cop-out: this module's only power is to substitute a row, and it
        # has no row to substitute FOR.  The caller's own validation, which ran
        # before this and will run after it, owns a malformed row.
        return LivenessDecision(
            decision=DECISION_HONOUR,
            reason=REASON_UNREADABLE_ROW,
            scene_id=scene_id,
            stored=row,
            position=row,
            fact=None,
        )
    if scene_id == HOME_SCENE_ID:
        return LivenessDecision(
            decision=DECISION_HONOUR,
            reason=REASON_HOME_ROW,
            scene_id=scene_id,
            stored=row,
            position=row,
            fact=ledger.fact(scene_id),
        )
    fact = ledger.fact(scene_id)
    if fact is not None:
        return LivenessDecision(
            decision=DECISION_HONOUR,
            reason=(
                REASON_OBSERVED_THIS_PROCESS if fact.from_this_process
                else REASON_OBSERVED_BEFORE_THIS_PROCESS
            ),
            scene_id=scene_id,
            stored=row,
            position=row,
            fact=fact,
        )
    home = _home_row(ledger, registry)
    if home is None:
        # No way home means no substitution is possible, so the row stands and
        # the reason says why.  This is the one branch that leaves a character
        # where they were stranded, and it must be loud rather than silent -
        # which is what the reason string is for.
        return LivenessDecision(
            decision=DECISION_HONOUR,
            reason=REASON_HOME_UNAVAILABLE,
            scene_id=scene_id,
            stored=row,
            position=row,
            fact=None,
        )
    return LivenessDecision(
        decision=DECISION_SEND_HOME,
        reason=REASON_NO_EVIDENCE,
        scene_id=scene_id,
        stored=row,
        position=home,
        fact=None,
    )


def _home_row(
    ledger: SceneLivenessLedger,
    registry: world_scene_travel.SceneRegistry | None,
) -> Position | None:
    if ledger.home is not None:
        return ledger.home
    try:
        return world_scene_travel.home_return_position(registry)
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException:
        # A login path is not the place to discover a broken registry, and a
        # character who cannot be sent home is better off with the row they
        # have than with an exception in the middle of scene entry.
        return None


def liveness_console_line(decision: Any) -> str:
    """One line per login, printed whichever way the decision went.

    A line only on the interesting branch is a line nobody can use to tell
    "this ran and found nothing wrong" from "this never ran", which is the
    exact confusion that made this lane re-measure its own wiring three rounds
    running.
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
    if decision.sends_home and decision.position is not None:
        home = decision.position
        line += (
            " home_scene={0} home_at=({1:.3f},{2:.3f},{3:.3f})"
            .format(home.scene_id, home.x, home.y, home.z)
        )
    return line


def liveness_report(decision: Any) -> dict:
    """One flat dict for a round note or an attended ticket."""
    if type(decision) is not LivenessDecision:
        raise ValueError("a liveness report needs a LivenessDecision")
    stored = decision.stored
    position = decision.position
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
        "evidence": None if decision.fact is None else decision.fact.evidence,
        "evidence_from_this_process": (
            None if decision.fact is None else decision.fact.from_this_process),
        "console_line": liveness_console_line(decision),
    }
