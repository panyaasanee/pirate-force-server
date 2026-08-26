"""One resolved arrival - LANE-A build order BUILD-002, slice 1 (v2).

WHY THIS MODULE EXISTS, IN ONE SENTENCE.  ``world_scene_travel`` answers
"which scene, and where in it"; this module answers the question a boot
actually has to answer, which is "given the row this character carries, what
exactly do I send, and what do I print before I send it".

THE TWO THINGS ``GT-079`` SAYS THE WIRING STILL OWES IT.  The attended ticket
``GT-079 SCENE-278-ENTRY-AND-STAGE-EYECHECK-001`` lists three deliverables and
names the state of the tree that satisfies each.  One is already written: a
flagless path that picks the destination from the character's position row.
The other two are what this module is FOR - and read the next paragraph before
believing it delivers them.

    NOTHING IN THIS FILE REACHES A PLAYER UNTIL SOMETHING CALLS IT, AND
    NOTHING CALLS IT YET.  ``runtime.py``, ``app.py`` and ``session.py`` are
    the chief's files and this lane does not edit them.  Two rounds of this
    lane have already shipped capabilities nobody called; saying so at the top
    of the third is the least this file can do.  What is here is a call the
    wiring can make in one line, and a written request for it - not a
    delivered deliverable.

* **The console line, printed BEFORE the character is placed.**  The ticket's
  words are "no line = do not boot", so a run without it is not a run.
  ``resolve_entry`` writes it through its ``emit`` sink before it returns
  anything, so a caller that resolves a destination has already emitted the
  line by the time it holds one.

      TWO LIMITS OF THAT, SAID PLAINLY RATHER THAN LEFT TO BE FOUND.
      (1) This module cannot tell a console from a list's ``append``.  ``emit``
      is checked for being callable and nothing else, so "the line was
      emitted" is a claim at THIS layer only; whether it reached the cp874
      console the ticket's step 4 reads is decided by the caller that chose
      the sink.  (2) The line is emitted when a destination is DECIDED, not
      when a character is placed.  "No line = do not boot" is therefore
      one-directional: the line's absence is decisive, its presence is not a
      claim that the login went on to succeed.

* **A row that is coherent with its own scene.**  The ticket calls this its
  "biggest trap" and gives the stop condition in coordinates: a character
  entering scene 278 must arrive near ``(-13270, 22794)``, and a HUD reading of
  ``(-9239, -2830)`` is a stopped boot.  That is not hypothetical.  A character
  row is one row: it carries a scene id and an XYZ, and today the only XYZ any
  row in this project has ever carried is a Port Royal one.  Point that row's
  scene id at the test stage and the login frames disagree with each other -
  the teleport carries one point while the ActorAttr and the MovementAttr
  built from the same row carry another.  Which one the client believes is
  unmeasured, and a boot whose answer depends on that is a boot that cannot be
  graded.  So ``resolve_entry`` returns ONE position, and the teleport fields
  it returns are BUILT FROM THAT POSITION rather than from the pin - the two
  can no longer disagree with each other, whichever branch produced the
  position.

WHAT DECIDES WHETHER A STORED POSITION IS KEPT OR REPLACED.  Two rules, and
the first one is the important one:

1. **Home is never touched.**  Scene 1 is the only scene a character in this
   project has ever stood in, walked around and been persisted in.  A player
   who logged out beside the tavern comes back beside the tavern, exactly as
   today, and the teleport arguments stay ``(1, 0, 0.0, 0.0, 0.0)`` -
   argument for argument what the runtime sends now.  That zero target is the
   shape every default boot here has been observed to survive, so home's
   teleport is the one place the position is deliberately NOT used.
   CHARTER-02's cumulative rule says a version that takes away what the last
   one could do is damage, and this is that rule at its smallest scale.

2. **Away from home, the row is kept only if it is inside the destination's
   own ground evidence.**  The test is the pinned ground extent measured from
   the scene's own placement file: a stored XY within ``extent_x``/``extent_y``
   of the pinned spawn is a position that scene has evidence for, and is kept
   so that a character who walks around the stage and logs back in does not get
   yanked to the middle of it.  Anything further out - a Port Royal row, most
   of all - takes the pinned spawn instead, and the replacement is EMITTED,
   not merely made available: the ticket's stop rule is a person reading the
   console, and a silent rewrite is exactly what would stop that rule firing.

   ``relocated`` MEANS THE POSITION MOVED, NOT THAT THE RULE FIRED.  Those are
   different, and reporting the second as the first would cry wolf forever: a
   character standing exactly on a spawn-only scene's pinned spawn takes the
   pinned-spawn branch on every login while nothing about it moves.  The flag
   and the second console line are driven by the comparison, not the branch.

   THE EXTENT IS A SPAN, NOT A BOUNDING BOX, AND THIS USES IT AS A RADIUS ON
   PURPOSE.  ``ground_extent`` is the x and y span of the nine placements, so
   accepting +/- that span around the spawn accepts an area up to four times
   the measured one.  That looseness is deliberate and it points the safe way:
   the failure this guard exists to stop is a row 25,624 units out, and being
   generous at the edge costs a character a few hundred units of walking while
   being strict there could refuse a position that is genuinely on the stage.

   WHY THIS KEYS ON GROUND EVIDENCE AND NOT ON ``n_SAVE``, WHICH IS THE
   OBVIOUS OBJECTION.  Scene 2 carries ``n_SAVE = 1`` - the client's own table
   marks it a scene characters persist in - and it has no pinned ground, so
   rule 2 sends every scene-2 row that is not already there to the measured
   SCENE-001 entry point.  That is right TODAY for a checkable reason: no
   scene-2 row exists yet, because the only path that has ever put a character
   in scene 2 is the scene-load scenario, whose session class refuses to
   checkpoint at all.

       AND THAT REASON EXPIRES THE MOMENT THIS MODULE HAS A CALLER.  The
       PRODUCTION session's ``checkpoint`` refuses nothing and
       ``store.save_position`` accepts any scene id in ``0..0xFFFF``, so the
       instant a wiring writes ``entry.position`` into a row, non-home rows
       start meaning "where I was" and rule 2 is measuring the wrong thing.
       This is a dated rule, not a durable one.  ``n_SAVE`` is the right
       signal for that day and is already exposed as
       ``SceneDestination.persists_characters``; it is not the right signal
       today, because today it would authorise keeping a Port Royal XY inside
       scene 2 on the strength of a column with no evidence behind it.

A RETURN TICKET IS OWED FOR EVERY DESTINATION BUT HOME, AND ``n_MARKER`` DOES
NOT GET A VOTE.  ``world_scene_travel``'s pinned console line reports
``return_ticket=not_needed`` for a scene whose ``n_MARKER`` is non-zero, and
that line is quoted verbatim by ``GT-079`` so it is not changed here.  But
``n_MARKER`` is an ARRIVAL marker: it says the developers authored a point to
arrive at, and says nothing whatever about a way back out.  ``RE-077`` closed
2026-08-26 (T0-T4 pinned, T5 bounded negative) with the client's own
scene-transition sequence, but no measurement in this tree names a way out of
scene 2 or scene 278.  So ``SceneEntry.return_ticket_required`` is true for
every non-home destination, and it will differ from the pinned line for
scene 2 on purpose: the line reports the client's column, the field reports
whether THIS project knows a way home.

WHAT THIS MODULE DOES NOT DO.  It does not move a character who is already
live from one scene to another.  ``RE-077`` pinned the client's sequence for
that; nothing in this tree drives it yet, and guessing ahead of a driver is
how a lane ships something that works until it silently does not.
It does not write anything: no database, no file, no socket.  It does not
decide who gets sent to the stage; it answers what to do with the row a
character already has.  And it does not claim scene 278 loads, renders, has
ground, or can be stood on - ``GT-079`` decides that with somebody's eyes.

THE HAZARD THIS MODULE CANNOT MAKE BINDING, NAMED SO THE NEXT ROUND CAN.
``world_population.build_world_population`` was made to REFUSE the census away
from home rather than merely report on it.  The persistence hazard has no such
guard anywhere: nothing forbids writing a character row into a scene with no
known exit, and this module can only hand back a ticket and ask.  Making that
binding means touching the persistence path, which is the chief's file and not
this lane's; it is written down here so that it is a known gap rather than an
assumption.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import Position
from . import world_scene_travel
from .world_scene_travel import (
    HOME_SCENE_ID,
    SceneDestination,
    SceneRegistry,
)


# Convention marker.  This module is not a scenario and is not behind a flag:
# once the runtime calls it, it runs on the default boot for every character.
production_allowed = True
test_only = False

# Why a stored position was not the one used.  Reported rather than inferred:
# the person explaining a boot at 2am should not have to work out which rule
# fired from the numbers afterwards.
RELOCATED_NO_GROUND_EVIDENCE = "no_pinned_ground_for_scene"
RELOCATED_OUTSIDE_GROUND = "stored_xy_outside_pinned_ground_extent"
RELOCATION_REASONS = (
    RELOCATED_NO_GROUND_EVIDENCE,
    RELOCATED_OUTSIDE_GROUND,
)

# Why an arrival was refused outright.  One exception type, several reasons,
# so the wiring catches one thing and still gets to say which one happened.
REFUSED_SCENE_NOT_PINNED = "scene_not_pinned"
REFUSED_SCENE_ID_OUT_OF_RANGE = "scene_id_out_of_range"
REFUSED_NO_PINNED_SPAWN = "scene_has_no_pinned_spawn"
REFUSAL_REASONS = (
    REFUSED_SCENE_NOT_PINNED,
    REFUSED_SCENE_ID_OUT_OF_RANGE,
    REFUSED_NO_PINNED_SPAWN,
)


class SceneEntryRefused(LookupError):
    """This row names an arrival this tree cannot compose, and why.

    ONE TYPE ON PURPOSE, AND DELIBERATELY NOT A ``KeyError``.  ``GT-079``
    describes the intended behaviour as "a scene not in the pin = a loud
    KeyError at boot", and an earlier draft of this module obliged.  That was
    wrong for a measured reason: ``runtime.py`` wraps the production
    ``select_and_start`` in ``except (KeyError, PermissionError)`` and answers
    it by appending an event and returning no frames.  A refusal raised as a
    ``KeyError`` there produces no console line, no traceback and no reply -
    a client stuck at "connecting" and a bridge console with nothing on it to
    read, which is precisely the silence "no line = do not boot" exists to
    prevent.  ``LookupError`` is the nearest base that the existing handler
    does not swallow, so the refusal stays loud until somebody handles it ON
    PURPOSE.

    Whoever wires this owes that deliberate handler: catch
    ``SceneEntryRefused``, print its message, and refuse the login by name.
    Letting it escape unwinds the connection's listener thread instead.

    Faults in the registry FILE - missing, unreadable, malformed, non-ASCII -
    are not this type and are not caught here.  They are not facts about the
    character's row and reporting them as "your scene is not pinned" would
    send the reader hunting for a destination that is present.
    """

    def __init__(self, reason: str, message: str):
        if reason not in REFUSAL_REASONS:
            raise ValueError(f"unknown refusal reason {reason!r}")
        super().__init__(f"[{reason}] {message}")
        self.reason = reason


@dataclass(frozen=True)
class SceneEntry:
    """Everything one login needs about where this character is arriving.

    ``stored`` and ``position`` are both here, always, even when they are the
    same object.  A report that carried only the position it chose could not
    tell a reader whether it chose it or was given it.

    ``teleport_fields`` is derived from ``position`` for every destination
    except home, where it is the frozen ``(1, 0, 0.0, 0.0, 0.0)`` the runtime
    already sends.  Nothing here reads the pin a second time, so the teleport
    and the position cannot drift apart.
    """

    stored: Position
    position: Position
    destination: SceneDestination
    teleport_fields: tuple[int, int, float, float, float]
    population_source: str | None
    return_ticket_required: bool
    relocated: bool
    relocation_reason: str | None
    console_lines: tuple[str, ...]

    @property
    def is_home(self) -> bool:
        return self.destination.n_id == HOME_SCENE_ID

    @property
    def console_line(self) -> str:
        """The ``WORLD_SCENE`` line - the one ``GT-079`` pins by name."""
        return self.console_lines[0]


def _require_position(value: object, label: str) -> Position:
    if type(value) is not Position:
        raise ValueError(f"{label} must be a Position")
    return value


def _within_ground(target: SceneDestination, stored: Position) -> bool:
    """Whether this scene has ground evidence that reaches the stored XY.

    Z is deliberately not tested.  The only z evidence any scene here has is
    the placement z of its own mobs, which says where a developer put an NPC
    and not how far above or below it the ground goes; a z test would refuse
    positions for a reason the data cannot support.
    """
    extent = target.ground_extent
    if extent is None:
        return False
    spawn_x, spawn_y, _spawn_z = target.spawn
    extent_x, extent_y = extent
    return (
        abs(stored.x - spawn_x) <= extent_x
        and abs(stored.y - spawn_y) <= extent_y
    )


def _teleport_from(target: SceneDestination, position: Position) -> tuple[
    int, int, float, float, float
]:
    """The five ``make_login_teleport`` arguments, from the position in hand.

    Home keeps the frozen zero target rather than the character's XYZ, because
    that zero target is what every surviving default boot in this project has
    sent; using the position there would be a change to the one path that is
    known to work.  The carve-out is on the scene id and nothing else - not on
    ``n_SAVE``, not on whether the scene has ground - because "home" is the
    only property that makes it true.  Everywhere else the teleport carries the
    position that the rest of the login frames will carry, which is the point.
    """
    scene_id, scene_seq = world_scene_travel.entry_fields(target)
    if target.n_id == HOME_SCENE_ID:
        return (scene_id, scene_seq, 0.0, 0.0, 0.0)
    return (scene_id, scene_seq, position.x, position.y, position.z)


def resolve_entry(
    stored: Position,
    *,
    registry: SceneRegistry | None = None,
    emit=print,
) -> SceneEntry:
    """Resolve one character's stored row into the arrival the boot will send.

    THE EMIT IS NOT DECORATION.  ``GT-079`` requires the destination line on
    the console before the character is placed, and this is where the
    destination becomes known, so this is where the line goes out - along with
    a second line whenever the row and the position used are not the same
    arrival.  A silent rewrite would disable the ticket's own stop rule, which
    is a person reading coordinates off the console.  ``emit`` exists for
    tests and for a caller with its own log sink; see the module docstring for
    what this module can and cannot promise about where those lines land.

    PASS ``registry`` FROM A LOAD DONE ONCE AT STARTUP.  Left as ``None`` the
    pin file is read and fully re-validated on every call, which on a wired
    runtime is every login.  Loading it once at boot also moves a malformed
    pin to the moment the server starts, where somebody is watching, instead
    of the moment a player logs in.

    Refusals: a row this tree cannot compose an arrival for raises
    ``SceneEntryRefused`` - read that class before deciding what to do with
    it, because the existing handler in ``runtime.py`` would have swallowed the
    obvious choice.  Faults in the registry FILE are deliberately not caught
    and surface as themselves.
    """
    row = _require_position(stored, "stored position")
    if not callable(emit):
        raise ValueError("emit must be callable")

    if registry is None:
        # Outside the try below on purpose: a missing, unreadable or malformed
        # pin file is not a fact about this character's row.
        registry = world_scene_travel.load_scene_registry()

    try:
        target = world_scene_travel.destination(row.scene_id, registry)
    except KeyError as error:
        raise SceneEntryRefused(
            REFUSED_SCENE_NOT_PINNED,
            f"stored row names scene {row.scene_id!r}, which is not pinned "
            f"in the scene registry ({error})",
        ) from error
    except ValueError as error:
        raise SceneEntryRefused(
            REFUSED_SCENE_ID_OUT_OF_RANGE,
            f"stored row names scene {row.scene_id!r}, which is not a value "
            f"the scene field can carry ({error})",
        ) from error

    if target.n_id != HOME_SCENE_ID and target.spawn is None:
        raise SceneEntryRefused(
            REFUSED_NO_PINNED_SPAWN,
            f"scene {target.n_id} is pinned but has no spawn position - "
            "measure one before sending a player there",
        )

    lines = [world_scene_travel.entry_console_line(target)]
    scene_id, scene_seq = world_scene_travel.entry_fields(target)

    if target.n_id == HOME_SCENE_ID:
        position = row
        reason = None
    elif _within_ground(target, row):
        # The row is inside the only ground this scene has evidence for, so it
        # is a position this scene can account for.  Keep it, but keep it in
        # this scene's own frame: scene_seq is whatever entry_fields says for
        # this destination, never whatever the row happened to carry.
        position = Position(
            scene_id, scene_seq, row.x, row.y, row.z, row.heading,
        )
        reason = None
    else:
        position = world_scene_travel.entry_position(target, row.heading)
        reason = (
            RELOCATED_NO_GROUND_EVIDENCE if target.ground_extent is None
            else RELOCATED_OUTSIDE_GROUND
        )

    moved = (
        (position.x, position.y, position.z) != (row.x, row.y, row.z)
    )
    if not moved:
        # The rule chose the pinned spawn and the character was already on it.
        # Nothing was overridden, so nothing is reported as overridden.
        reason = None

    # The second line, when the row and the arrival are not the same thing.
    # Home never gets one: there the row IS the position, byte for byte, and
    # an extra line on every normal boot would be noise around the one line
    # the ticket pins.
    if target.n_id != HOME_SCENE_ID and (
        moved
        or (position.x, position.y, position.z) != target.spawn
        or position.scene_seq != row.scene_seq
    ):
        lines.append(
            _relocated_line(target, row, position, reason) if moved
            else _kept_row_line(target, row, position)
        )

    for line in lines:
        emit(line)

    return SceneEntry(
        stored=row,
        position=position,
        destination=target,
        teleport_fields=_teleport_from(target, position),
        population_source=world_scene_travel.population_source(target.n_id),
        # Not from n_MARKER - see the module docstring.  RE-077 is open for
        # every non-home scene, so this project knows a way home from none of
        # them.
        return_ticket_required=target.n_id != HOME_SCENE_ID,
        relocated=moved,
        relocation_reason=reason,
        console_lines=tuple(lines),
    )


def _relocated_line(
    target: SceneDestination,
    stored: Position,
    position: Position,
    reason: str,
) -> str:
    return (
        "WORLD_SCENE_RELOCATED scene_id={0} reason={1} "
        "stored=({2:.3f},{3:.3f},{4:.3f}) used=({5:.3f},{6:.3f},{7:.3f}) "
        "stored_seq={8} used_seq={9}"
        .format(
            target.n_id, reason,
            stored.x, stored.y, stored.z,
            position.x, position.y, position.z,
            stored.scene_seq, position.scene_seq,
        )
    )


def _kept_row_line(
    target: SceneDestination,
    stored: Position,
    position: Position,
) -> str:
    return (
        "WORLD_SCENE_KEPT_ROW scene_id={0} used=({1:.3f},{2:.3f},{3:.3f}) "
        "pinned_spawn=({4:.3f},{5:.3f},{6:.3f}) stored_seq={7} used_seq={8}"
        .format(
            target.n_id, position.x, position.y, position.z,
            *target.spawn,
            stored.scene_seq, position.scene_seq,
        )
    )


def relocation_console_line(entry: SceneEntry) -> str:
    """The relocation line for an entry that had one, for a report or a test.

    ``resolve_entry`` has already emitted this; recomposing it here is for
    callers that want the string rather than the side effect.  Refuses on an
    entry whose position was not overridden, so a caller cannot print a
    relocation that did not happen.
    """
    if type(entry) is not SceneEntry:
        raise ValueError("relocation console line needs a SceneEntry")
    if not entry.relocated:
        raise ValueError("no relocation happened - there is nothing to report")
    return _relocated_line(
        entry.destination, entry.stored, entry.position,
        entry.relocation_reason,
    )


def return_ticket(
    entry: SceneEntry,
    *,
    remembered: Position | None = None,
    registry: SceneRegistry | None = None,
) -> Position | None:
    """The row that walks this character home, or ``None`` if none is owed.

    ``GT-079`` makes restoring this row a mandatory teardown step, because
    scene 278 carries ``n_MARKER = 0`` and ``n_SAVE = 0`` and ``RE-077`` is
    open, so a character left there has no in-game way back.  A ticket is owed
    for every non-home destination and not only that one: ``n_MARKER`` is an
    arrival marker and this project has measured no way out of any scene.

    PASS ``remembered`` IF YOU HAVE IT, AND CAPTURE IT BEFORE THE TRIP.  With
    no argument this returns the pinned Port Royal entry point, which is where
    a NEW character starts and not where this one was standing - a character
    that departed from the attended GT-045 spawn comes back 731 units away with
    its heading reset.  That is the best this module can do from a row that
    already says 278; the row it departed from is gone by then.  Whoever writes
    ``entry.position`` into the character row owns keeping a copy of what was
    there before and handing it back here.

    Both extra arguments are keyword-only, because ``remembered`` was added
    after ``registry`` existed and a positional call would otherwise have
    silently changed meaning.
    """
    if type(entry) is not SceneEntry:
        raise ValueError("return ticket needs a SceneEntry")
    # Validated even when no ticket is owed, so a caller that passes a bad row
    # hears about it on the boot where it passed one.
    if remembered is not None:
        home = _require_position(remembered, "remembered position")
        if home.scene_id != HOME_SCENE_ID:
            raise ValueError(
                f"a remembered home row must be scene {HOME_SCENE_ID}, "
                f"not {home.scene_id}"
            )
    if not entry.return_ticket_required:
        return None
    if remembered is None:
        return world_scene_travel.home_return_position(registry)
    return remembered


def entry_report(entry: SceneEntry) -> dict:
    """One flat dict for a round note or an attended ticket.

    This wraps ``world_scene_travel.entry_report`` rather than restating it, so
    a column added there cannot go missing here, and adds only what this module
    knows that that one cannot: what the row said, what was used instead, and
    why.  A name collision between the two is refused rather than merged: the
    wrapped report is the one that would lose, and losing a column silently is
    the failure this wrapper exists to prevent.
    """
    if type(entry) is not SceneEntry:
        raise ValueError("entry report needs a SceneEntry")
    report = world_scene_travel.entry_report(entry.destination)
    mine = {
        "stored_scene_id": entry.stored.scene_id,
        "stored_scene_seq": entry.stored.scene_seq,
        "stored_position": [entry.stored.x, entry.stored.y, entry.stored.z],
        "stored_heading": entry.stored.heading,
        "used_position": [
            entry.position.x, entry.position.y, entry.position.z,
        ],
        "used_scene_seq": entry.position.scene_seq,
        "used_heading": entry.position.heading,
        "relocated": entry.relocated,
        "relocation_reason": entry.relocation_reason,
        "return_ticket_required": entry.return_ticket_required,
        "teleport_fields": list(entry.teleport_fields),
        "console_lines": list(entry.console_lines),
    }
    collisions = sorted(set(report) & set(mine))
    if collisions:
        raise ValueError(
            "scene entry report would overwrite travel columns: "
            + ", ".join(collisions)
        )
    report.update(mine)
    return report
