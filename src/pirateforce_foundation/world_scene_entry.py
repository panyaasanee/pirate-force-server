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

    ~~NOTHING IN THIS FILE REACHES A PLAYER UNTIL SOMETHING CALLS IT, AND
    NOTHING CALLS IT YET.~~  STRUCK, MEASURED FALSE AT HEAD (LANE-A, round
    this-round, 2026-09-01, re-derived from the tree rather than trusted from
    this paragraph).  ``runtime.py``'s production login path calls
    ``resolve_entry`` twice today - once, silenced (``emit=lambda _line:
    None``), as the probe that decides whether a GM login-scene override may
    be applied at all, and once for real, for whichever row (the character's
    own, or the override) survives that probe - at the two call sites a
    reader can find by name: ``world_scene_entry.resolve_entry(`` appears
    twice in ``runtime.py``, both inside the login handler, both reachable
    on the flagless default boot for any account whose stored or
    GM-overridden scene id resolves through this module.  Tests exercise the
    wiring directly rather than asking this docstring to be believed:
    ``tests/test_gm_login_scene_override_wiring.py`` and
    ``tests/test_gm_login_scene_registry_wiring_in_runtime.py`` both drive
    ``runtime.py`` itself, not a mock of it.  The struck sentence was true
    when this module's first two rounds shipped it (hence "two rounds of
    this lane have already shipped capabilities nobody called" below, which
    stays - it is a true sentence about the PAST, not a claim about HEAD);
    it stopped being true once a later round (not this lane's - ``runtime.py``
    is the chief's file) wired the call in.  ``runtime.py``, ``app.py`` and
    ``session.py`` remain the chief's files and this lane still does not
    edit them - that half of the paragraph was never the part that went
    stale.

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
   who logged out beside the tavern comes back beside the tavern (and since
   round ``ioz8fd`` so does one who logged out at sea - see
   ``_ground_refutes_stored_row``; before it, only home kept a row), exactly as
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
arrive at, and says nothing whatever about a way back out.  ~~``RE-077`` is
open for scene 2 exactly as it is for scene 278~~ -- STRUCK, MEASURED FALSE
(LANE-A, round ``f6e5kd``, 2026-09-03): ``RE-077`` was answered 2026-08-26 and
archived 2026-08-27, T0-T4 pinned and T5 a bounded negative.  The half of the
sentence that survives is the load-bearing half and it needs no ticket to hold
it up: NO MEASUREMENT IN THIS TREE NAMES A WAY OUT OF EITHER SCENE, because
what ``RE-077`` pinned is the order the CLIENT requires for a switch, not an
authored route home from a row whose ``n_MARKER`` is 0.  See
``world_scene_travel``'s docstring for the citation and the full
correction.  So ``SceneEntry.return_ticket_required`` is true
for every non-home destination, and it will differ from the pinned line for
scene 2 on purpose: the line reports the client's column, the field reports
whether THIS project knows a way home.

WHAT THIS MODULE DOES NOT DO.  It does not move a character who is already
live from one scene to another - that is ``RE-077`` (~~open~~ CLOSED
2026-08-26; what is missing is not the answer but a server that has ever sent
it), and guessing the sequence is how a lane ships something that works until
it silently does not.
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
import math

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
# ADDED round 1v5i3h (LANE-A), pf-adversary D2 of this round's own branch,
# MEASURED: with the third gate open, a stored row of (14, inf, inf, 0) was
# kept verbatim, and `teleport_fields` -> `make_login_teleport` -> f32tag
# packs that as 0000807f onto the wire, on every login, forever - because no
# login rewrites the row any more.  SQLite REAL round-trips +/-Inf, and
# `runtime.py::_checkpoint_exact_target` unpacks the client's TargetPos with
# no finite check, so the value gets in.  This project had already decided
# such a check is required in two other places (`world_m2_return_leg.
# remember_departure` refuses a non-finite row by name, `gm/warp_executor.
# _require_finite_float` refuses NaN/Inf); the login path was the one that
# did not have it, which is the path that matters most.
RELOCATED_ROW_NOT_FINITE = "stored_xy_not_a_finite_number"
RELOCATION_REASONS = (
    RELOCATED_NO_GROUND_EVIDENCE,
    RELOCATED_OUTSIDE_GROUND,
    RELOCATED_ROW_NOT_FINITE,
)

# Why a stored position WAS the one used, for the same reader at 2am.  Both
# of these are "kept"; they are not the same fact and an attended tester
# reading the console must not have to guess which one held.
KEPT_ROW_WITHIN_GROUND = "stored_xy_inside_pinned_ground_extent"
# ~~KEPT_ROW_NOT_REFUTED = "login_row_not_refuted_by_measured_ground"~~ --
# WITHDRAWN round 1v5i3h (LANE-A), pf-adversary D2 of round ioz8fd, which is
# the sharpest kind of finding this project gets: the string was not merely
# vague, it was FALSE on the one scene it was printed for.  Scene 17 carries
# a measured placement box in the same JSON object, a stored row of
# (999999, 999999) is outside it on any reading, and the console still said
# no measured ground refuted the row -- because the decree veto in
# ``_ground_evidence`` returned before the box was ever consulted.  One
# token cannot carry "there is no measurement" and "there is one and the row
# is inside it"; they are the two facts an attended tester most needs to
# tell apart, so they are two tokens now and the login path actually
# consults the box (see ``_measured_envelope_refutes``).
KEPT_ROW_NO_MEASUREMENT = "login_row_no_measured_ground_exists_for_this_scene"
KEPT_ROW_INSIDE_ENVELOPE = "login_row_inside_measured_placement_envelope"
KEPT_ROW_BASES = (
    KEPT_ROW_WITHIN_GROUND,
    KEPT_ROW_NO_MEASUREMENT,
    KEPT_ROW_INSIDE_ENVELOPE,
)

# Why an arrival was refused outright.  One exception type, several reasons,
# so the wiring catches one thing and still gets to say which one happened.
REFUSED_SCENE_NOT_PINNED = "scene_not_pinned"
REFUSED_SCENE_ID_OUT_OF_RANGE = "scene_id_out_of_range"
REFUSED_NO_PINNED_SPAWN = "scene_has_no_pinned_spawn"
# Round 0z3kjx, pf-adversary-flagged.  A destination whose pin sets
# login_entry_allowed=False may only be resolved with via_login=False (a
# caller that is NOT reading a character's persisted row) - see resolve_entry
# and world_scene_travel's login_entry_allowed comment for the full story.
REFUSED_NOT_ALLOWED_AT_LOGIN = "scene_not_allowed_at_login"
REFUSAL_REASONS = (
    REFUSED_SCENE_NOT_PINNED,
    REFUSED_SCENE_ID_OUT_OF_RANGE,
    REFUSED_NO_PINNED_SPAWN,
    REFUSED_NOT_ALLOWED_AT_LOGIN,
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


def _ground_evidence(target: SceneDestination, x: float, y: float) -> bool | None:
    """The ground-evidence verdict for one XY against one destination's pin.

    ``None`` MEANS "THIS SCENE HAS NO GROUND EVIDENCE AT ALL", NOT "OUTSIDE".
    Collapsing those two into the same ``False`` is exactly what
    ``_within_ground`` has always done for its own caller (which never
    needed the distinction - a kept-row test only cares "yes or no, treat as
    outside"), but a caller with nothing else to go on, such as a GM warp
    target that has never resolved a ``SceneEntry``, needs to be able to
    tell "definitely outside ground" apart from "we don't know" - see
    ``is_position_within_scene_ground``.

    Z is deliberately not tested.  The only z evidence any scene here has is
    the placement z of its own mobs, which says where a developer put an NPC
    and not how far above or below it the ground goes; a z test would refuse
    positions for a reason the data cannot support.

    A PROVISIONAL-OWNER-DECREE spawn never counts as ground evidence here
    (pf-adversary, round e0daaa, found this the hard way after scene 17
    gained BOTH a decree and a real ground block the same round): this
    radius test is centred on ``target.spawn`` and is safe to be generous
    around ONLY because a normal spawn is itself a measured point already
    inside the real ground. A decreed spawn carries no such guarantee -- it
    was never derived from the ground data at all, so a position merely
    numerically close to it is not evidence of anything. Refusing here
    forces every arrival at such a destination through the pinned-spawn
    branch instead, so it always lands on exactly the decreed point rather
    than on some nearby row nobody measured either.  Note this scene MAY
    still carry real ground_extent evidence (scene 17 does, both at once) -
    the decree only disqualifies the radius test centred on ITS spawn, so
    the answer here is ``False`` (evidence exists, this point is not shown
    to be inside it), not ``None`` (no evidence at all).
    """
    extent = target.ground_extent
    if extent is None:
        return None
    if (
        target.spawn_provenance is not None
        and target.spawn_provenance.startswith("PROVISIONAL-OWNER-DECREE")
    ):
        return False
    spawn_x, spawn_y, _spawn_z = target.spawn
    extent_x, extent_y = extent
    return (
        abs(x - spawn_x) <= extent_x
        and abs(y - spawn_y) <= extent_y
    )


def _ground_refutes_stored_row(
    target: SceneDestination, stored: Position
) -> bool:
    """Whether MEASURED ground evidence says this XY is not in this scene.

    THE THIRD GATE OF PANYA-DECISION 20260908_1218, NAMED.  Rounds 9lv3fa
    and 3a11a0 opened the two gates everybody could see -
    ``login_entry_allowed`` (may this row be read at all) and
    ``persist_position_allowed`` (may this row be written at all) - and a
    character that logged out at sea still arrived on the pinned spawn
    rather than on its own coordinates, because ``_within_ground`` answered
    "no" and ``resolve_entry`` threw the row away.  pf-adversary D1 of round
    3a11a0 measured it: scene 17 stored (-149.0, -1250.3, 745.0) landed on
    (0, 0, 0), scene 14 stored (-17000, 18500, 1890) landed on the marker.
    That is the owner's rule failing on its own headline case.

    WHY THE ANSWER IS THIS AND NOT A MEASUREMENT.  The other way to close
    the gate is to give 14, 126, 304 and 305 a real ``ground`` block, and
    NOW.md offers both - but with ``ground_extent`` forbidden to be made up,
    and no placement file to derive one from, there is nothing honest to
    write for those four.  So the rule moves instead: at login the stored
    row is kept unless something MEASURED refutes it.  A stored row is not a
    guess; it is where the client last said the character stood, written by
    the persist path on a real ``TargetPos``.  An NPC-placement bounding box
    is weaker evidence than that, and this registry's own ``ground`` blocks
    say so in their ``limit`` field ("a .npc file carries NPC placements,
    not ground").

    WHAT STILL RELOCATES, so this is a narrowing and not a removal:
    a ``False`` from ``_ground_evidence`` that came from a radius centred on
    a MEASURED spawn - scene 278 is the only such row in the shipped
    registry today.  A ``False`` that came from the PROVISIONAL-OWNER-DECREE
    veto is not a measurement of anything (see ``_ground_evidence``: the
    veto exists precisely because a radius around an unmeasured point proves
    nothing), so it does not refute the row either, and ``None`` - no ground
    block at all - never did.

    NOT CLAIMED: that a kept row is inside the playable map.  Nothing in
    this tree can decide that for a scene with no ground block, and this
    function does not pretend otherwise; it decides whose word is better in
    the absence of evidence, and 1218 says it is the player's.
    """
    if _ground_evidence(target, stored.x, stored.y) is not False:
        return False
    provenance = target.spawn_provenance
    if (
        provenance is not None
        and provenance.startswith("PROVISIONAL-OWNER-DECREE")
    ):
        # The radius test proved nothing here (that is what the veto means),
        # but "the test I ran proved nothing" is not "there is nothing to
        # measure against" -- see ``_measured_envelope_refutes``, which is
        # the same generosity re-centred on a point that WAS measured.
        return _measured_envelope_refutes(target, stored.x, stored.y) is True
    return True


def _row_is_finite(row: Position) -> bool:
    """Is every coordinate of this stored row an actual number?

    ``heading`` is deliberately not tested here: a bad heading points a
    character the wrong way, which the next client report corrects, while a
    bad coordinate is a place that does not exist and now survives every
    login.  ``z`` IS tested even though no rule below reads it, because it
    goes on the wire in the teleport frame exactly as stored.
    """
    return (
        math.isfinite(row.x)
        and math.isfinite(row.y)
        and math.isfinite(row.z)
    )


def _measured_envelope_refutes(
    target: SceneDestination, x: float, y: float
) -> bool | None:
    """Does the MEASURED placement box say this XY is not in this scene?

    ``True`` outside, ``False`` inside, ``None`` when the scene has no
    ground block to ask.

    WHY THIS EXISTS (pf-adversary D2, round ioz8fd).  ``_ground_evidence``
    centres ``ground_extent`` on ``target.spawn``, and refuses to do so when
    that spawn is a PROVISIONAL-OWNER-DECREE, for the reason its own
    docstring gives: a radius around an unmeasured point proves nothing.
    That refusal is right.  What was wrong was what the login path then did
    with it -- it reported that no measured ground existed, for a scene
    whose ``ground`` block carries four measured numbers.  A BOX does not
    need a spawn to be centred on, so a decreed spawn does not disqualify
    it.

    THE CENTRE AND THE SPANS ARE MEASURED.  THE SHAPE THEY MAKE IS
    ``[PROPOSED]`` -- pf-adversary corrected an earlier draft of this
    paragraph that said "nothing here is invented", and it was wrong twice
    in one sentence:

    1.  ``extent_x`` is the FULL width of the box, used here as a RADIUS, so
        the accepted region is 2x the box on each axis and **4x its area**.
        For scene 17 the box is x in [-971.3, 844.6] and the envelope is
        x in [-1879.3, 1752.6].  The doubling is a choice, not a
        measurement, and it is load-bearing: the row 1218 is about
        (-149, -1250.3) sits 381 units OUTSIDE the measured box and is kept
        only because of it.  A mutant that tightens the envelope to the real
        box turns two cases red, which is the suite pinning the choice
        rather than hiding it.
    2.  It is not "what every measured scene already gets".  Scene 278's
        test is centred on its SPAWN, this one on the box MIDPOINT, and for
        278 those are 1816 units apart in x.  The two measured scenes get
        two geometrically different tests, for the honest reason that one
        has a measured spawn to centre on and the other does not.

    WHY THE LOOSE SHAPE IS STILL THE RIGHT DIRECTION.  This function may
    only ever REFUTE a stored row, never admit one, so a too-generous
    envelope errs toward keeping the player where the client said it was --
    the direction PANYA-DECISION 20260908_1218 rules in -- and a too-tight
    one would relocate the very row 1218 is about.  What it buys is the case
    it was built for: a row three orders of magnitude away is refuted by
    measured data instead of being reported as unrefutable.

    WHAT IT DOES AND DOES NOT SETTLE.  Scene 17's headline row
    (-149.0, -1250.3) sits 381 units below ``y_min`` and is INSIDE this
    envelope, so the row that 1218 is about is still kept -- this is not a
    re-closing of the third gate.  A row of (999999, 999999) is outside it
    by three orders of magnitude and is refuted, which is the case D2 found
    the console lying about.  NOT CLAIMED: that a row inside the envelope is
    on walkable ground.  A ``.npc`` file carries NPC placements, not
    terrain (every ``ground`` block says so in its own ``limit`` field), so
    this can catch a row that is provably nowhere near the scene and can
    never certify one that is.
    """
    box = target.ground_box
    extent = target.ground_extent
    if box is None or extent is None:
        return None
    x_min, x_max, y_min, y_max = box
    extent_x, extent_y = extent
    return not (
        abs(x - (x_min + x_max) / 2.0) <= extent_x
        and abs(y - (y_min + y_max) / 2.0) <= extent_y
    )


def _within_ground(target: SceneDestination, stored: Position) -> bool:
    """Whether this scene has ground evidence that reaches the stored XY.

    Delegates to ``_ground_evidence`` - the shared core - and collapses its
    three-valued answer back to two, because this caller (the kept-row
    branch of ``resolve_entry``) has only ever needed "keep the row" or
    "don't"; "we have no evidence either way" and "we checked and it's
    outside" both mean "don't" here.  See ``_ground_evidence`` for the rules
    (PROVISIONAL-OWNER-DECREE, z not tested) and
    ``is_position_within_scene_ground`` for the public wrapper that keeps
    the third value instead of discarding it.
    """
    return _ground_evidence(target, stored.x, stored.y) is True


def is_position_within_scene_ground(
    scene_id: int,
    x: float,
    y: float,
    *,
    registry: SceneRegistry | None = None,
) -> bool | None:
    """Public ground check for one XY inside one scene - no resolved row
    required.

    Built for a caller that has a scene id and a candidate XY but no
    ``SceneEntry`` to resolve first - e.g. a GM ``/warp`` target that has not
    landed anywhere yet (LANE-GM's request, round egee8l: `/warp` composes
    real teleport frames for an off-ground point today because nothing it
    calls exposes this check publicly - see
    ``notes_to_chief/20260901_2028_LANE-GM-TO-LANE-A-warp-coordinate-bound-needs-a-public-ground-check.md``).
    ~~Wraps the exact same rule ``resolve_entry`` uses to decide whether a
    stored row survives a login (``_ground_evidence``, shared with
    ``_within_ground``) rather than a second, looser radius test~~ --
    STRUCK ROUND 1v5i3h, pf-adversary D5 of that round: since the login path
    also consults ``_measured_envelope_refutes``, this wrapper IS the looser
    reading's opposite number, and the two now DISAGREE on a real row::

        is_position_within_scene_ground(17, -149.0, -1250.3)  -> False
        resolve_entry(same row, via_login=True)               -> KEPT

    A caller importing this still gets the PROVISIONAL-OWNER-DECREE
    carve-out for free, and that is what it is for.  What it must NOT be
    read as any more is a preview of what a login will do with the same XY.

    THE LIVE BITE, NAMED SO THE NEXT ROUND CAN FIX IT RATHER THAN
    REDISCOVER IT: ``gm/warp_executor._refuse_if_outside_ground`` early-
    returns for a decree scene, so ``/warp 17 1800 0`` composes a frame and
    ``warp_scene_persist`` writes the row -- and the next login now
    RELOCATES that character to the decreed point.  That module's headline
    contract ("a destination the next login would refuse is not persisted")
    was written when the login had no coordinate-level refusal to see, and
    it needs this function's third answer wired into it.  It is LANE-GM's
    file; this lane owns the check it must call.

    THREE ANSWERS, NOT TWO.  ``True`` - this XY is inside the ground this
    scene has evidence for.  ``False`` - this scene HAS ground evidence and
    this XY is outside it (or the only spawn evidence it has is a
    PROVISIONAL-OWNER-DECREE, which never counts).  ``None`` - this scene
    has no ground evidence at all (including: the scene id is not pinned in
    the registry, or is not a value the scene field can carry) - a caller
    that treats ``None`` as "assume False" gets today's ``_within_ground``
    behaviour back; a caller that wants to tell "definitely outside" apart
    from "we don't know" can now do that instead.

    ``registry`` follows ``resolve_entry``'s own convention: pass one loaded
    once at startup, or leave it ``None`` to load and fully re-validate the
    pin file on every call.
    """
    if type(scene_id) is not int:
        raise ValueError("scene_id must be an int")
    if type(x) not in (int, float) or type(y) not in (int, float):
        raise ValueError("x and y must be numbers")
    try:
        target = world_scene_travel.destination(scene_id, registry)
    except (KeyError, ValueError):
        # Not pinned, or not a value the scene field can carry - either way
        # this tree has no ground evidence to check against.
        return None
    return _ground_evidence(target, float(x), float(y))


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
    via_login: bool = True,
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

    ``via_login`` DEFAULTS TO THE SAFE ANSWER ON PURPOSE.  This is the same
    call ``runtime.py``'s login path makes with whatever ``scene_id`` is
    sitting in a character's persisted row, so the default has to be the one
    that keeps that path fail-closed without ``runtime.py`` ever having to say
    so explicitly - it is the chief's file and this lane does not add a kwarg
    to its call site.  A destination pinned with ``login_entry_allowed=False``
    (~~today: scene 17 only~~ ~~the set is 17, 126, 304 and 305~~ -- BOTH
    STRUCK, LANE-A round ``9lv3fa``, 2026-09-08: the set is **EMPTY**, and
    PANYA-DECISION 20260908_1218 is why it must stay empty.  The owner's
    permanent rule is that logging in returns a character to the exact point
    it logged out from IN EVERY SCENE, sea and island included, so a pinned
    ``False`` on a destination a character can stand in is a player who
    cannot get back into their own character.  The four that carried it were
    this project's own belt-and-braces pins (COO + this lane), not a fact
    about the original game, and every one of them has a spawn today.
    Do not believe this sentence either - derive it:
    ``tests/test_world_scene_registry_login_door.py`` walks the registry and
    fails if ANY pinned destination that has a spawn is shut at login.
    AND READ THE NEXT SENTENCE BEFORE QUOTING THE ONE ABOVE.  Opening this
    door delivers the SCENE, not the POINT: rounds ``9lv3fa`` and ``3a11a0``
    both wrote the owner's full promise here while ``resolve_entry`` was
    still throwing the stored x/y away, and pf-adversary D1 measured the
    gap.  The point half is delivered by the third branch below and by
    ``_ground_refutes_stored_row``; without that branch this paragraph is
    an overclaim, which is exactly what it was for two rounds.
    THE MECHANISM BELOW IS NOT REMOVED and is not dead code: a destination
    added later without a measured spawn is exactly what it is for, and 1218
    forbids the pin only for the CURRENT registry, not forever)
    raises ``REFUSED_NOT_ALLOWED_AT_LOGIN`` here UNLESS the caller explicitly
    passes ``via_login=False``, meaning "this call is not reading a
    character's own persisted position row" - which is exactly what
    ``columbus_quest_dispatch.resolve_columbus_arrival``'s synthetic call is,
    and the only caller in this tree that passes it today.  Passing
    ``via_login=False`` does not weaken the check for any other destination:
    every pre-existing pin (1, 2, 278, 997) has no ``login_entry_allowed``
    field at all and defaults True, so this changes nothing for them either
    way.

    Refusals: a row this tree cannot compose an arrival for raises
    ``SceneEntryRefused`` - read that class before deciding what to do with
    it, because the existing handler in ``runtime.py`` would have swallowed the
    obvious choice.  Faults in the registry FILE are deliberately not caught
    and surface as themselves.
    """
    row = _require_position(stored, "stored position")
    if not callable(emit):
        raise ValueError("emit must be callable")
    if type(via_login) is not bool:
        raise ValueError("via_login must be a bool")

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

    if via_login and not target.login_entry_allowed:
        raise SceneEntryRefused(
            REFUSED_NOT_ALLOWED_AT_LOGIN,
            f"scene {target.n_id} is pinned but not allowed as a login "
            "destination for a persisted row - only a non-login caller "
            "that passes via_login=False may resolve it",
        )

    if target.n_id != HOME_SCENE_ID and target.spawn is None:
        raise SceneEntryRefused(
            REFUSED_NO_PINNED_SPAWN,
            f"scene {target.n_id} is pinned but has no spawn position - "
            "measure one before sending a player there",
        )

    lines = [world_scene_travel.entry_console_line(target)]
    scene_id, scene_seq = world_scene_travel.entry_fields(target)

    kept_basis = None
    if target.n_id == HOME_SCENE_ID:
        position = row
        reason = None
    elif not _row_is_finite(row):
        # Asked BEFORE any ground question, because every question below
        # compares the row against a measurement and NaN loses every
        # comparison silently: `abs(nan - centre) <= extent` is False, which
        # reads as "outside" by luck rather than by decision, and +/-Inf is
        # inside nothing but was kept by the login branch because nothing
        # measured could refute it.  A row that is not a number is not a
        # place, whoever is asking, so this arm is not gated on via_login.
        position = world_scene_travel.entry_position(target, row.heading)
        reason = RELOCATED_ROW_NOT_FINITE
    elif _within_ground(target, row):
        # The row is inside the only ground this scene has evidence for, so it
        # is a position this scene can account for.  Keep it, but keep it in
        # this scene's own frame: scene_seq is whatever entry_fields says for
        # this destination, never whatever the row happened to carry.
        position = Position(
            scene_id, scene_seq, row.x, row.y, row.z, row.heading,
        )
        reason = None
        kept_basis = KEPT_ROW_WITHIN_GROUND
    elif via_login and not _ground_refutes_stored_row(target, row):
        # PANYA-DECISION 20260908_1218: logging in puts a character back on
        # the point it logged out from, in EVERY scene.  Nothing measured
        # says this row is wrong (see ``_ground_refutes_stored_row``), and a
        # row the client wrote beats a spawn nobody stood on, so the row
        # wins.  Same frame discipline as the branch above.
        position = Position(
            scene_id, scene_seq, row.x, row.y, row.z, row.heading,
        )
        reason = None
        kept_basis = (
            KEPT_ROW_NO_MEASUREMENT if target.ground_extent is None
            else KEPT_ROW_INSIDE_ENVELOPE
        )
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
        # ``or kept_basis is not None`` ADDED round 1v5i3h, pf-adversary D8
        # of round ioz8fd: the three conditions above all ask "is the arrival
        # different from the pin", and a row that a RULE decided to keep and
        # that happens to sit exactly on the pin answers no to all three.  So
        # the one line that says which rule kept the row was missing in the
        # case it was written for, and the console for a kept (17, 0,0,0) was
        # byte-identical to an arrival where the row had been thrown away
        # (that is D1, from the other side).  A rule ran; it gets a line.
        or kept_basis is not None
    ):
        lines.append(
            _relocated_line(target, row, position, reason) if moved
            else _kept_row_line(target, row, position, kept_basis)
        )

    # PANYA-DECISION 2026-08-27T14:45+07:00 item 2: a spawn this project did
    # not measure or model, and used only because the owner decreed it for
    # this exact scene/value, must print a distinct grep-able token the
    # moment it is actually used -- not merely pinned in the registry --
    # so WIRED v2 and an attended tester can tell a decreed landing from a
    # measured one.  Detected from the pin's own provenance text rather than
    # a hardcoded scene id, so this is not scene-17-specific code: whichever
    # scene's spawn provenance is tagged this way gets the token when the
    # position actually used for this arrival equals that decreed spawn.
    #
    # DELIBERATELY NOT KEYED ON WHICH BRANCH ABOVE PRODUCED ``position``
    # (pf-adversary-shaped bug found this round, before it shipped): once a
    # scene has BOTH a decreed spawn AND ground evidence -- exactly what
    # happened to scene 17 this same round, independently, in
    # world_scene_registry_001.json -- a row that already sits inside that
    # ground (the ``_within_ground`` branch, e.g. a synthetic row built at
    # the decreed value itself) takes the "kept row" path, never touching
    # ``target.spawn`` at all.  Gating the token on "did we take the
    # pinned-spawn branch" would then silently stop firing for the exact
    # arrival it exists to mark, while the arrival still lands on the
    # decreed coordinate.  Comparing the FINAL position against the pin
    # instead catches both branches.
    if (
        target.n_id != HOME_SCENE_ID
        and target.spawn is not None
        and (position.x, position.y, position.z) == target.spawn
        and target.spawn_provenance is not None
        and target.spawn_provenance.startswith("PROVISIONAL-OWNER-DECREE")
    ):
        decree_tag = target.spawn_provenance.split(" ", 1)[0]
        # ``from=`` ADDED round 1v5i3h (LANE-A), pf-adversary D1 of round
        # ioz8fd.  The token above fires on the FINAL position matching the
        # decreed pin, which is right (see the paragraph before it), but two
        # very different arrivals produce that same match and, until this
        # field, the same bytes on the console:
        #
        #   pinned_spawn  the incoming row was thrown away and the arrival
        #                 is the decree -- what the token was written for
        #   caller_row    a via_login=False caller (Columbus) handed in a row
        #                 that already IS the decreed point.  Not a
        #                 character's persisted row and must not read as one
        #                 -- the first draft of this field called it
        #                 stored_row and made the sanctioned synthetic
        #                 arrival look like a durable one.
        #   stored_row    the character's OWN persisted row is being used and
        #                 happens to equal the decreed point.  A durable row
        #                 of (17, 0,0,0) does this: it is kept, it moves
        #                 nothing, so the second line above is (correctly)
        #                 not printed, and an attended tester reading the
        #                 console saw a decreed arrival that never happened.
        #                 A zero row is exactly what an uninitialised or
        #                 half-written character row looks like, so this is
        #                 the case a tester most needs to catch.
        #
        # It reads the same ``moved`` the two lines above read, so a change
        # to one cannot silently disagree with the other.
        lines.append(
            "SCENE_ENTRY scene={0} xyz={1:.3f},{2:.3f},{3:.3f} source={4} "
            "from={5}"
            .format(
                target.n_id, position.x, position.y, position.z, decree_tag,
                "pinned_spawn" if moved
                else ("stored_row" if via_login else "caller_row"),
            )
        )

    for line in lines:
        emit(line)

    return SceneEntry(
        stored=row,
        position=position,
        destination=target,
        teleport_fields=_teleport_from(target, position),
        population_source=world_scene_travel.population_source(target.n_id),
        # Not from n_MARKER - see the module docstring.  ~~RE-077 is open
        # for every non-home scene~~ (STRUCK: closed 2026-08-26) - this
        # project knows a way home from none of them, which is a fact about
        # this tree's own measurements and never depended on the ticket.
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
    basis: str | None = None,
) -> str:
    """The console line for an arrival that used the character's own row.

    ``basis`` says WHICH rule kept it - measured ground reached the point,
    the scene has no measurement to refute it, or a measured envelope
    contains it - because on the console those look identical and only some
    of them mean this project has evidence for the coordinate.  The values
    are ``KEPT_ROW_BASES``, and ``test_every_kept_row_basis_is_one_this_
    module_declares`` walks the registry to keep that tuple honest (it had
    no reader at all until round 1v5i3h; pf-adversary D8).

    ~~``None`` renders as ``basis=unstated`` rather than being dropped, so a
    caller that forgets is visible instead of silent.~~ -- CORRECTED round
    1v5i3h, same finding: ``None`` never came from a forgetful caller.  It
    came from the RELOCATION branch, whose only caller is ``_relocated_line``
    one line above this function in ``resolve_entry`` -- so ``unstated`` was
    unreachable through this function and the sentence described a
    protection that did not exist.  It renders as ``unstated`` anyway,
    because the day a fourth branch is added the line should say it does not
    know rather than silently pick one.
    """
    return (
        "WORLD_SCENE_KEPT_ROW scene_id={0} used=({1:.3f},{2:.3f},{3:.3f}) "
        "pinned_spawn=({4:.3f},{5:.3f},{6:.3f}) stored_seq={7} used_seq={8} "
        "basis={9}"
        .format(
            target.n_id, position.x, position.y, position.z,
            *target.spawn,
            stored.scene_seq, position.scene_seq,
            basis if basis is not None else "unstated",
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
    scene 278 carries ``n_MARKER = 0`` and ``n_SAVE = 0`` and ~~``RE-077`` is
    open~~ (STRUCK, LANE-A round ``f6e5kd`` 2026-09-03: closed 2026-08-26 -
    see the module docstring; the ticket was never what made this true) no
    measurement in this tree names a way back out,
    so a character left there has no in-game way back.  A ticket is owed
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
