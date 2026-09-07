"""The captain-report handshake, as a marker-driven mechanism (LANE-A, M2).

WHAT THIS IS, IN ONE SENTENCE
The server sends ``TeleportCheckVital`` carrying one ``MARKER.n_ID``; the
client opens "raayngaan kapatan ..." by itself, echoes the SAME id back when
the player confirms, and this module turns that echo into the outbound
transport to that marker's own scene and point.

WHY IT CAN BE WRITTEN AT ALL NOW (RE-303 PASS, 2026-09-07T21:50+07:00,
``pf_bridge/notes_to_chief/20260907_2150_RE-303-RESULT-teleportcheck-0x4477-
opens-confirm-22-ok-echoes-marker.md``).  Everything below is that letter's
measurement, not this lane's guess:

* ``TeleportCheckVital`` (``0x4477``) is the frame whose HANDLER opens the
  confirm window -- handler ``0x005F2190``, confirm open at ``0x005F232F``.
* The frame has ONE field: ``u16``, tag ``0x0F``, at ``+0x14``, gate ALWAYS,
  and the SAME layout in both directions (``PF_SERIALIZER_FIELDS.tsv``).
* That u16 IS ``MARKER.n_ID``: the handler indexes ``MARKER`` with it at
  ``0x005F2290`` and reads ``n_SCENE`` out of the row.
* OK echoes the same class, the same id, the same value, unmodified
  (``0x0044BFA0``: ``mov word ptr [eax+0x14], cx``).  Cancel sends NOTHING
  (the only other path out of that callback is ``ret``).
* The client picks the WORDING itself from
  ``SCENE_NAME[MARKER[u16].n_SCENE].n_SCENE_TYPE``: ``== 8`` -> confirm 21
  ("moving ahead"), anything else -> confirm 22 ("docking").  The server
  cannot choose the text and must not try to send one.

WHY THE ECHO MUST NOT REQUIRE A WINDOW (RE-303 section 6.1, and the addendum
``20260907_2158_RE-303-ADDENDUM-the-auto-ack-gate-that-skips-the-window.md``).
Before the handler reaches the window-opening path it has an early gate: when
the client's own state matches ``0x33`` and the marker id equals the one it
remembered, it answers IMMEDIATELY from the same pool, with no window at all.
So a server that only accepts an echo it can pair with "a window we believe is
open" would teleport sometimes and hang sometimes, for reasons no log would
name.  :func:`accept_echo` therefore keys on the PENDING MARKER ID and nothing
else, and :func:`accept_echo` has a test that runs it with the window-shown
fact set both ways and pins the two results identical.

WHY THERE IS NO TIMEOUT HERE, AND WHAT CANCEL COSTS.  Cancel sends nothing, so
"the player refused" and "the player walked away" are the same silence on the
wire (RE-303 BUILD_IMPACT 5).  This module holds NO session state of its own:
:func:`open_check` returns a :class:`PendingCheck` and keeps nothing, and a
recorder (the sink) is what holds up to :data:`ORDER_CAP` live orders at once,
replacing none of them.  An earlier draft of this paragraph said the module
"keeps ONE pending marker per session and lets a later open_check overwrite
it", and that was the stated reason there is no expiry clock -- a reason
resting on a mechanism this file never had (pf-adversary, round `w4cp5c`).

The real answer to an abandoned prompt is :func:`resolve_echo`, which says in
code which recorded order an inbound echo consumes and pins that it is
consumed ONCE.  An order nobody echoes is simply never taken; it costs one
list slot until the cap refuses new ones out loud.  There is still deliberately
no expiry clock, because a clock here would be a number no letter measured.

WHAT THIS MODULE DOES NOT DO
It builds and reads bytes and decides what the answer should be.  It does not
own a socket, does not read one, and registers no hook: the dispatch branch
that hands it an inbound ``0x4477`` and puts its frames on the wire is
``runtime.py``'s, i.e. chief's, and this round's PR body carries the one-line
request for it.  Nothing in this file is gated by a scenario flag or a
``production_allowed`` switch -- it is ordinary always-on server code, which
is the whole point of the M2 order (COO round `2241`).

NOT CLAIMED
1. That any particular ``MARKER.n_ID`` is any particular island.  RE-303
   nonclaim 1 refuses the destination crosswalk and so does this file: the
   marker id is whatever the caller names, and the row it resolves to is read
   out of the committed copy, never guessed from a number's neighbourhood.
2. That the client will show a window for every id.  Section 6.1's early gate
   can answer without one, and 6.2 records that only confirm 22 fires the
   extra ``0x51`` state.  This module predicts the wording (see
   :func:`predicted_confirm_id`) and says out loud that the prediction is a
   READING of the client's rule, not an observation of a screen.
3. That ``0x4477`` was measured from the image this round.  RE-303 nonclaim 6
   is explicit: the id is bound at runtime and the number is cited from
   ``gm/teleport_wire.py`` and the vital registry.  This module cites the same
   two sources and pins the value against ``legacy`` at import-free test time
   rather than re-deriving it.
"""
from __future__ import annotations

import threading
import weakref
from typing import Any, NamedTuple

from . import world_scene_marker

#: ``TeleportCheckVital``'s wire id.  Cited, not measured -- see NOT CLAIMED 3.
#: ``tests`` pin this against ``current/pf_login_game_server_v141.py``'s own
#: ``TELEPORT_CHECK_VITAL`` so the two can never drift apart silently.
TELEPORT_CHECK_VITAL_ID = 0x4477

#: The vital VERSION byte for this class.  ``0``, and this is measured, not a
#: default: ``pf_login_game_server_v141.parse_teleport_check_vital`` refuses
#: any other version, and ``make_teleport_check_scene1_challenge`` -- the
#: frame the V136 route has actually put on the wire -- sends 0.
TELEPORT_CHECK_VITAL_VERSION = 0

#: The tag of the single u16 field (``PF_SERIALIZER_FIELDS.tsv``, both rows).
TELEPORT_CHECK_FIELD_TAG = 0x0F

#: The client's ``MARKER`` table is 390 rows (RE-303 section 4, and
#: ``world_scene_marker.MARKER_ROW_COUNT`` pins the same number).  THE IDS ARE
#: NOT 1..390 THOUGH, and this module learned that from its own data rather
#: than from a letter: ``world_scene_marker``'s transcribed rows include
#: marker id 1000 for scene 130.  So the only bound that can be asserted here
#: is the one the WIRE imposes -- the field is a u16 -- and everything else is
#: "the table knows this id or it does not".  An earlier draft of this file
#: range-checked 1..390 and would have refused a row the repository already
#: carries.
#:
#: THE LOWER BOUND IS NOT THE FIELD'S, IT IS THE TABLE'S SENTINEL.  A u16
#: carries 0 perfectly well, so ``0`` is inside the wire's range and outside
#: this door on purpose: ``0`` is how the client's own ``SCENE_NAME`` rows
#: spell "this scene names no marker" -- it is the value ``world_scene_marker``
#: counts to get its ``MARKER_LESS_SCENES`` -- so a caller that reaches here
#: holding 0 is holding an absent lookup, not a destination.  Refusing it by
#: name is the only way that mistake is ever visible (pf-adversary, round
#: `w4cp5c`: the bound was left over from the refuted 1..390 claim and
#: relabelled as a field bound it is not).
MARKER_ID_MIN = 1
MARKER_ID_MAX = 0xFFFF
#: The value the comment above is about, named so the two refusals can be
#: told apart in code as well as in prose.  ``MARKER_ID_MIN`` stays 1
#: because 1 is still the lowest id this door will resolve; what changed
#: in round `ew9416` is that reaching it with 0 is no longer reported as
#: an id the FIELD could not carry.
MARKER_ID_ABSENT_SENTINEL = 0

#: ``n_SCENE_TYPE == 8`` -- open sea.  RE-303 counted the type-8 rows in
#: ``CONSTDATA_TH__SCENE_NAME.tsv`` and got exactly {126, 127, 128, 304, 305},
#: which is the same set RE-238 had already pinned from the other direction.
#: Two independent letters, one set: that is why it is written down here as
#: data rather than re-read from a table this repository does not carry.
SEA_SCENE_IDS: tuple[int, ...] = (126, 127, 128, 304, 305)
SEA_SCENE_SOURCE = "RE-303 s.4 SCENE_NAME n_SCENE_TYPE==8; cross-checked RE-238"

#: The two confirm rows the client picks between (``CONSTDATA_TH.UI_CONFIRM``).
CONFIRM_ID_MOVING_AHEAD = 21   # UI_MESSAGE 1132, scene type 8
CONFIRM_ID_DOCKING = 22        # UI_MESSAGE 1133, every other scene type

CHECK_REFUSED_BAD_ARITY = "CHECK_REFUSED_BAD_ARITY"
CHECK_REFUSED_MARKER_ID_NOT_AN_INT = "CHECK_REFUSED_MARKER_ID_NOT_AN_INT"
CHECK_REFUSED_MARKER_ID_OUT_OF_FIELD = "CHECK_REFUSED_MARKER_ID_OUT_OF_FIELD"
#: ``0`` is INSIDE the u16 the wire carries and outside this door, so it
#: gets a name of its own rather than borrowing the field refusal.  The
#: same mistake D6 fixed for arity was still live here: a reader of a run
#: tally saw "an id the wire could not carry" for the client's own "this
#: scene names no marker" sentinel, whose fix is in the CALLER that looked
#: a marker up and got nothing, not in the number it passed
#: (pf-adversary, round `ew9416`, D-A2).  The only script in the shipped
#: corpus that calls this name (``t_telchk_lv.lua``) passes an unbound
#: ``Trigger.Var1``, which is exactly this case.
CHECK_REFUSED_MARKER_ID_IS_ABSENT_SENTINEL = (
    "CHECK_REFUSED_MARKER_ID_IS_ABSENT_SENTINEL")
#: An order recorded against a character the CONNECTION never proved can
#: never be consumed: the dispatch branch takes with the id the socket
#: proved (``foundation.selected.id``), so an order filed under the script
#: context default 0 opens a window and then refuses its own echo -- the
#: "window that goes nowhere" of R307, produced by this chain itself
#: (chief letter `20260908_0432`, D6).  Refused BY NAME here so the
#: misconfiguration is a counted refusal instead of a dead window.
CHECK_REFUSED_NO_CHARACTER_BOUND = "CHECK_REFUSED_NO_CHARACTER_BOUND"
CHECK_REFUSED_MARKER_ROW_NOT_PINNED = "CHECK_REFUSED_MARKER_ROW_NOT_PINNED"
ECHO_REFUSED_NOTHING_PENDING = "ECHO_REFUSED_NOTHING_PENDING"
ECHO_REFUSED_NO_ORDER_FOR_THIS_PLAYER = "ECHO_REFUSED_NO_ORDER_FOR_THIS_PLAYER"
ECHO_REFUSED_MARKER_ID_MISMATCH = "ECHO_REFUSED_MARKER_ID_MISMATCH"
ECHO_REFUSED_UNDECODABLE = "ECHO_REFUSED_UNDECODABLE"

TOKEN = "LANE_A_M2_TELEPORT_CHECK"


class TeleportCheckError(ValueError):
    """Raised by :func:`marker_destination` when an id has no usable row.

    Named rather than bare so a caller can tell "this lane refused" apart from
    a ``struct`` or ``Cursor`` failure underneath it.
    """


class MarkerDestination(NamedTuple):
    """One ``MARKER`` row, read in the marker -> scene direction only.

    ``world_scene_marker.forbidden_direct_index_scenes`` exists because
    indexing ``MARKER`` BY A SCENE lies for 257 scenes.  This type is built
    from a marker id something else already named, and it carries that row's
    OWN back-pointer scene (``MarkerArrival.marker_row_scene``), never the
    scene the row was found under -- so nothing here can go back the other
    way by accident.
    """

    marker_id: int
    scene_id: int
    x: int
    y: int
    z: int
    direction: int


class PendingCheck(NamedTuple):
    """The one outstanding prompt for one session.

    ``window_expected`` is a PREDICTION and is never read by
    :func:`accept_echo` -- see the module docstring's auto-ACK paragraph.  It
    exists so the console line can say what the tester should expect to see,
    and so an attended round can report "the window did not appear" as a
    finding instead of as a silence.
    """

    marker_id: int
    destination: MarkerDestination
    window_expected: bool
    confirm_id: int


def _coerce_marker_id(marker_id: Any) -> int | None:
    """``marker_id`` as an int, or ``None``.

    ``bool`` is rejected with the ints because ``True`` is a valid Python int
    and a catastrophic marker id: it would resolve row 1 and teleport a player
    to scene 1 because a caller passed a flag into the wrong argument.
    """
    if type(marker_id) is not int:
        return None
    return marker_id


def coerce_wire_marker_id(value: Any) -> int | None:
    """A Lua-side argument as an int, WITHOUT applying this door's bound.

    The bound belongs to :func:`marker_destination`, which refuses it BY NAME
    (``CHECK_REFUSED_MARKER_ID_OUT_OF_FIELD``).  A caller that range-checks
    first collapses both refusals into "not an int" and that name then names
    nothing that can happen: measured by pf-adversary in round `ebh143` (D6)
    at the only live door there is, where ``Player.TeleportCheck(70000)`` and
    ``Player.TeleportCheck(-1)`` were counted as NOT_AN_INT.  THE NARROWER
    SENTENCE IS THE TRUE ONE (pf-adversary, round `ew9416`, D-A2, re-measured
    against `origin/main` before it was accepted): ``_coerce_int``'s floor is
    0, so ``Player.TeleportCheck(0)`` -- the client's own "this scene names no
    marker" sentinel -- always did reach a named refusal.  It reached the
    FIELD refusal, which was the wrong name for it; it now reaches
    ``CHECK_REFUSED_MARKER_ID_IS_ABSENT_SENTINEL``.  What was unreachable from
    a live call was the field refusal for ids ABOVE the ceiling and for
    NEGATIVE ids, and that is what this function fixed.

    ``bool`` is rejected with the ints (``True`` is an int and would resolve
    row 1), a float is accepted only when it carries an exact integer because
    that is how lupa hands every Lua number across, and NOTHING here is
    clamped: this returns the number the caller meant or ``None`` for a value
    that is not a number at all.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        as_int = int(value)
        if float(as_int) != value:
            return None
        return as_int
    if isinstance(value, int):
        return int(value)
    return None


def _by_marker_id() -> "dict[int, Any]":
    """Marker id -> ``world_scene_marker.MarkerArrival``, built from that
    module's PUBLIC accessors only.

    WHY NOT ``world_marker_copy``, WHICH KEEPS 20 ROWS VERBATIM.  That
    module reads a JSON file the release archive deliberately does not ship,
    and ``tests/test_world_marker_copy.py`` pins that NO module in this
    package may import it: a release-side caller would get ``MarkerCopyError``
    instead of a row.  A travel mechanism that works in the repository and
    raises in the release is worse than one with five fewer rows, so this
    reads the transcribed table that does ship.  (Measured, not reasoned: the
    first draft of this module imported the copy reader and turned that pin
    red.)

    THE DECREED ROWS ARE PART OF THE INDEX, AND WITHOUT THEM M2 HAS NO SEA.
    ``scenes_with_an_arrival_point()`` answers only for scenes whose
    ``SCENE_NAME`` row names its own marker; scenes 126, 304 and 305 -- the
    open-sea scenes this milestone exists to reach -- carry ``n_MARKER == 0``,
    so their arrival points live in ``world_scene_marker.
    DECREED_ARRIVAL_ROWS`` instead (COO-DECISION 20260905_1748).  Leaving them
    out is what made :func:`predicted_confirm_id` unable to return
    ``CONFIRM_ID_MOVING_AHEAD`` for anything this server can build a prompt
    for -- the sea half of RE-303's rule was unreachable code, and no test
    noticed (pf-adversary, round ``w4cp5c``).  They come from the same
    always-shipped module through its own public accessor, which takes BOTH
    ids precisely so no caller can turn a marker id into a scene id by
    accident.
    """
    rows = {}
    for scene_n_id in world_scene_marker.scenes_with_an_arrival_point():
        arrival = world_scene_marker.arrival_point(scene_n_id)
        if arrival is not None:
            rows[arrival.marker_n_id] = arrival
    for marker_n_id, scene_n_id, _x, _y, _z, _dir in (
            world_scene_marker.DECREED_ARRIVAL_ROWS):
        point = world_scene_marker.decreed_arrival_row(scene_n_id, marker_n_id)
        if point is None:                       # covered by a patched test
            raise TeleportCheckError(
                "%s marker_id=%d scene=%d (DECREED_ARRIVAL_ROWS and "
                "decreed_arrival_row disagree in world_scene_marker)"
                % (CHECK_REFUSED_MARKER_ROW_NOT_PINNED, marker_n_id,
                   scene_n_id))
        x, y, z, direction = point
        if marker_n_id in rows:                 # covered by a patched test
            raise TeleportCheckError(
                "%s marker_id=%d is both a named and a decreed arrival row"
                % (CHECK_REFUSED_MARKER_ROW_NOT_PINNED, marker_n_id))
        rows[marker_n_id] = world_scene_marker.MarkerArrival(
            scene_n_id, marker_n_id, scene_n_id, x, y, z, direction)
    return rows


def marker_destination(marker_id: Any) -> MarkerDestination:
    """The row ``marker_id`` names, or raise :class:`TeleportCheckError`.

    Two refusals, kept apart because their fixes are different: an id the WIRE
    could not carry (the field is one u16) is a caller bug, and an id the
    TRANSCRIBED TABLE does not know is a row this repository has not written
    down yet -- fixed by transcribing it in ``world_scene_marker``, never by
    typing coordinates here.
    """
    coerced = _coerce_marker_id(marker_id)
    if coerced is None:
        raise TeleportCheckError(
            "%s marker_id=%r" % (CHECK_REFUSED_MARKER_ID_NOT_AN_INT, marker_id))
    if coerced == MARKER_ID_ABSENT_SENTINEL:
        raise TeleportCheckError(
            "%s marker_id=0 (the SCENE_NAME sentinel for \"this scene names no "
            "marker\"; the wire carries 0 perfectly well, so fix the lookup "
            "that produced it, not the field)"
            % CHECK_REFUSED_MARKER_ID_IS_ABSENT_SENTINEL)
    if not (0 <= coerced <= MARKER_ID_MAX):
        raise TeleportCheckError(
            "%s marker_id=%d field=u16 range=%d..%d"
            % (CHECK_REFUSED_MARKER_ID_OUT_OF_FIELD, coerced,
               0, MARKER_ID_MAX))
    arrival = _by_marker_id().get(coerced)
    if arrival is None:
        raise TeleportCheckError(
            "%s marker_id=%d (world_scene_marker transcribes %d of the "
            "client's %d rows; transcribe the row there, do not type "
            "coordinates here)"
            % (CHECK_REFUSED_MARKER_ROW_NOT_PINNED, coerced,
               world_scene_marker.SCENES_WITH_A_MARKER,
               world_scene_marker.MARKER_ROW_COUNT))
    return MarkerDestination(
        coerced, arrival.marker_row_scene,
        arrival.x, arrival.y, arrival.z, arrival.direction)


def predicted_confirm_id(scene_id: int) -> int:
    """Which ``UI_CONFIRM`` row the CLIENT will pick for this destination.

    A reading of the client's own rule (RE-303 s.4), not an observation of a
    screen -- NOT CLAIMED 2.  The server cannot influence this and must not
    send any text; the value is here so a console line and an attended ticket
    can name the wording the tester should see.
    """
    return (CONFIRM_ID_MOVING_AHEAD if scene_id in SEA_SCENE_IDS
            else CONFIRM_ID_DOCKING)


def encode_prompt(legacy: Any, marker_id: Any) -> tuple[bytes, bytes]:
    """``(pc, frame)`` for the outbound ``TeleportCheckVital(marker_id)``.

    ``legacy`` is the v141 module, injected the same way this package's other
    M2 provisioning encoder takes it (the module whose own guard forbids the
    rest of the tree from even naming it -- which is why this docstring does
    not): this package does not import ``current/`` and does not own the
    envelope.

    The bytes are the exact shape ``make_teleport_check_scene1_challenge``
    already puts on the wire -- ``make_runtime_vitals`` with one vital, version
    0, body ``u16tag(0x0F, value)`` -- with the hard-coded ``1`` replaced by
    the caller's marker id.  That helper's own docstring explains why the
    RuntimeRes v4 carrier and its trailing derived mask are not optional here.
    """
    destination = marker_destination(marker_id)
    return legacy.make_runtime_vitals([(
        TELEPORT_CHECK_VITAL_ID,
        TELEPORT_CHECK_VITAL_VERSION,
        legacy.u16tag(TELEPORT_CHECK_FIELD_TAG, destination.marker_id),
    )])


def decode_echo(legacy: Any, parsed: Any) -> int | None:
    """The marker id inside an inbound ``TeleportCheckVital``, or ``None``.

    ``None`` -- never an exception -- for anything that is not a decodable
    frame of this class, because this is called from a dispatch branch where a
    raise costs a session and a ``None`` costs a log line.  The refusal is the
    caller's to print (:func:`echo_refusal_line`); returning the reason as a
    string instead would make the success path and the failure path the same
    type, which is how a marker id of 0 gets treated as a message.

    WHICH CHECKS THIS ACTUALLY MAKES, and which it only inherits (pf-adversary,
    round `ebh143`, D7 -- the claim was made in prose and pinned by nothing).
    This function itself checks exactly one thing: that the decoded field is an
    ``int``.  Vital class, nested version and the collection boundary are the
    v141 parser's, raised out of it and swallowed here; the RuntimeRes v4
    carrier and its trailing derived mask are ``parse_outer``'s, upstream of
    the ``parsed`` this is handed -- and RE-292 forbids this lane from putting
    a decoder of its own in that path, so inheriting them is the only correct
    posture, not a shortcut.  What that adds up to is measured rather than
    asserted in ``TheInboundDecoderRefusesEverythingButAnEcho``: an outbound
    prompt frame and another vital class both come back ``None``, a real client
    echo comes back as its marker id.
    """
    try:
        decoded = legacy.parse_teleport_check_vital(parsed)
    except Exception:  # noqa: BLE001 - see docstring: a raise here costs a session
        return None
    value = decoded.get("field_u16_14")
    return value if type(value) is int else None


def open_check(marker_id: Any) -> PendingCheck:
    """The pending record for a prompt this server is about to send.

    Raises :class:`TeleportCheckError` for an id it cannot resolve, BEFORE any
    frame is composed: a prompt for a row nobody pinned would open a window
    the confirm could not be answered, which is worse than not opening one.
    """
    destination = marker_destination(marker_id)
    confirm_id = predicted_confirm_id(destination.scene_id)
    return PendingCheck(
        marker_id=destination.marker_id,
        destination=destination,
        window_expected=True,
        confirm_id=confirm_id,
    )


def accept_echo(pending: PendingCheck | None, echoed_marker_id: Any) -> str | None:
    """``None`` when the echo answers ``pending``; the refusal name otherwise.

    THIS IS THE ANSWERING RULE, NOT THE CONSUMING ONE, AND A CALLER THAT USES
    ONLY THIS DOOR HAS BUILT A REPLAY.  ``accept_echo`` says whether an echo
    answers ONE pending order; it removes nothing, so calling it five times
    with the same id returns ``None`` five times and ``encode_transport``
    re-emits the same journey each time -- an unlimited free teleport to the
    player's last confirmed marker (pf-adversary, round `ebh143`, D8).  The
    door a dispatch branch wants is :meth:`InMemoryTeleportCheckSink.take`
    (or :func:`resolve_echo` plus a removal of its own): it checks the
    character, pops the order, and names the refusal on a replay.  Use this
    one only when the order in hand was already taken.

    THE ONE FACT THIS READS IS THE MARKER ID.  It does not read
    ``window_expected``, does not ask whether a window was shown, and has no
    other state -- because the client can answer without a window at all
    (module docstring, RE-303 s.6.1).  A version of this that also required
    "we think a window is open" would produce the exact symptom the addendum
    warns about: teleports that work on some approaches and hang on others.
    """
    if pending is None:
        return ECHO_REFUSED_NOTHING_PENDING
    if echoed_marker_id is None:
        return ECHO_REFUSED_UNDECODABLE
    if type(echoed_marker_id) is not int:
        return ECHO_REFUSED_UNDECODABLE
    if echoed_marker_id != pending.marker_id:
        return ECHO_REFUSED_MARKER_ID_MISMATCH
    return None


def resolve_echo(orders: "Any", character_id: Any,
                 echoed_marker_id: Any) -> int | None:
    """Index of the recorded order this echo consumes, or ``None``.

    THE RULE, WRITTEN DOWN BECAUSE THE DISPATCH BRANCH CANNOT INVENT IT.  A
    recorder holds several live orders at once (up to :data:`ORDER_CAP`), the
    client echoes back a marker id and nothing else, and every frame arrives on
    one player's socket.  So the order an echo may consume is:

    1. recorded for THIS character -- the socket already proved which one, and
       an echo must never move somebody else's ship;
    2. carrying THIS marker id -- the only fact the echo carries
       (:func:`accept_echo` reads that and nothing else, for the reason its own
       docstring gives);
    3. the NEWEST such order, when a player has been prompted for the same
       marker more than once -- the older prompts are the abandoned ones, and
       Cancel is silent so nothing else can tell them apart.

    THE INDEX IS VALID ONLY UNTIL THE LIST CHANGES.  Resolve, then remove,
    then resolve again -- never resolve twice and pop twice, because the
    second index was computed against the longer list and now names a
    different row (pf-adversary, round `ebh143`, D10).
    :meth:`InMemoryTeleportCheckSink.take` does resolve-and-pop inside one
    call for exactly this reason, and is what a caller should reach for.

    CONSUMED ONCE.  This returns an INDEX rather than the order itself
    precisely so the caller must remove it (``sink.take`` does), which is what
    keeps one echo from driving two transports: a client that echoes twice --
    or an attacker who replays the frame -- gets
    ``ECHO_REFUSED_NO_ORDER_FOR_THIS_PLAYER`` the second time instead of a
    second free journey.  A pure function over a list, so any recorder shape
    can use it and a test can drive it without a namespace.
    """
    if type(character_id) is not int or isinstance(character_id, bool):
        return None
    if type(echoed_marker_id) is not int or isinstance(echoed_marker_id, bool):
        return None
    for index in range(len(orders) - 1, -1, -1):
        order = orders[index]
        if (order.character_id == character_id
                and order.pending.marker_id == echoed_marker_id):
            return index
    return None


def encode_transport(legacy: Any, pending: PendingCheck) -> tuple[bytes, bytes]:
    """``(pc, frame)`` for the outbound transport that answers a good echo.

    Same body ``make_v137_marker1_transport_probe`` sends -- a RuntimeRes
    ``TeleportVital`` v4 whose ``TeleportTarget`` carries the destination
    scene and XYZ -- with V137's five hard-coded MARKER-row-1 constants
    replaced by the row this pending check resolved.

    Two values stay at constructor zero on purpose, exactly as that helper
    documents: the scene SEQUENCE and the trailing u16.  In particular
    ``MARKER.n_DIRTECTION`` is carried on :class:`MarkerDestination` and is
    NOT written into any of them -- V137's docstring refuses that assignment
    and no letter since has made it, so this module carries the number and
    declines to place it, rather than quietly inventing a field for it.
    """
    destination = pending.destination
    payload = (
        legacy.u8tag(0x0B, 2)
        + legacy.u8tag(0x0B, 1)
        + legacy.make_teleport_target(
            destination.scene_id,
            legacy.V137_MARKER_SCENE_SEQ,
            float(destination.x), float(destination.y), float(destination.z),
        )
        + legacy.u8tag(0x0B, 0)
        + legacy.u8tag(0x0B, 0)
        + legacy.u16tag(0x0F, 0)
    )
    return legacy.make_runtime_vitals([(legacy.TELEPORT_VITAL, 4, payload)])


class TransportRelocation(NamedTuple):
    """What a caller must do to the SESSION when it sends the transport.

    LANE-A's answer to chief's G1 (letter `20260908_0545_FROM_CHIEF_R398b`),
    which asked a WORLD question and so is answered here rather than at the
    call site: does the M2 transport move the client, or not?

    IT MOVES THE CLIENT.  :func:`encode_transport` builds the same
    ``TeleportVital`` v4 body with a ``TeleportTarget`` that
    ``make_v137_marker1_transport_probe`` sends and that ``gm/teleport_wire``
    composes for the GM warp -- the one cross-scene mover this server already
    had.  A server that hands that frame to a socket and then keeps calling
    the player's scene by the departure scene's number is lying to its own
    next frame: chief MEASURED the cost of that lie on a real store -- the
    destination's coordinates written into the durable row under
    ``scene_id=1``, and the next login putting the character in Port Royal at
    a point that belongs to the open sea.

    AND MOVING THE CLIENT IS NOT A LICENCE TO WRITE THE ROW.  COO-DECISION
    2026-08-28T21:30 (position ownership after a GM warp) already ruled the
    other half and this lane does not reopen it: the owner of a position is
    the position the CLIENT confirmed, a frame that left the server is a
    REQUEST and never evidence that anything moved, and the durable write
    happens on the first ``TargetPos`` after the frame, not before it.  So
    the two halves of this record are deliberately asymmetric:
    ``scene_id`` is relabelled IN MEMORY at send time, and
    ``durable_write_allowed`` is False -- exactly the shape
    ``_gm_warp_resync_selected_scene`` already has for the other mover,
    including leaving x/y/z alone so the first real report still reads as a
    change.

    ``scene_label_is_server_guess`` is True for the same reason it is there
    at all: until the client reports from the destination, the new scene
    number is this server's guess about where a frame it sent will land, and
    a guess must not advance ``client_confirmed_scene``.
    """

    scene_id: int
    x: int
    y: int
    z: int
    scene_label_is_server_guess: bool
    durable_write_allowed: bool


#: What the relocation record always says about a durable write, named so a
#: reader does not have to trust a bare ``False`` in a tuple: the ruling above
#: is COO's, not this module's, and a caller that wants to write at send time
#: is arguing with that decision rather than with this file.
TRANSPORT_DURABLE_WRITE_ALLOWED = False


def transport_relocation(pending: PendingCheck) -> TransportRelocation:
    """The in-memory relabel the caller owes the session for this transport.

    Call it WHERE THE FRAME IS QUEUED, with the pending check the echo
    resolved, and apply ``scene_id`` to the session's own position row (and
    nothing else -- see :class:`TransportRelocation`).  This module holds no
    session state and reaches no store, so it cannot apply anything itself;
    what it can do is say, in one place, what the answer is, so the call site
    is one line rather than a second derivation of the marker row.
    """
    d = pending.destination
    return TransportRelocation(
        scene_id=d.scene_id, x=d.x, y=d.y, z=d.z,
        scene_label_is_server_guess=True,
        durable_write_allowed=TRANSPORT_DURABLE_WRITE_ALLOWED)


def transport_resync_console_line(pending: PendingCheck) -> str:
    """The line a caller prints when it applies :func:`transport_relocation`.

    ``durable=0`` is the field an attended round reads next to the DB row it
    is about to look at: the row is EXPECTED to still carry the departure
    scene until the player takes one step, and a ticket that does not know
    that will report the correct behaviour as a defect.
    """
    r = transport_relocation(pending)
    return (
        "%s TRANSPORT_RESYNC marker=%d scene=%d xyz=%d,%d,%d guess=%d durable=%d"
        % (TOKEN, pending.marker_id, r.scene_id, r.x, r.y, r.z,
           int(r.scene_label_is_server_guess), int(r.durable_write_allowed)))


def prompt_console_line(pending: PendingCheck, sink: Any = None) -> str:
    """ASCII only (the bridge console is cp874): what this server RECORDED.

    IT IS NOT A SEND RECEIPT, AND IT NO LONGER READS LIKE ONE.  This line is
    printed by the Lua-layer door the moment ``Player.TeleportCheck`` files an
    order; ``encode_prompt`` is not called on this path and no byte reaches a
    socket from it.  The previous wording (``PROMPT`` + "what was sent") was
    byte-for-byte the line ``GT-309`` named as the proof that the server SENT
    ``0x4477``, so an attended ticket could have boarded the capture bus on a
    token that proves only that a script asked (pf-adversary, round `ew9416`,
    D-A1).  The verb now says which half fired, and ``sent=0`` says the other
    half did not: what a send looks like is :func:`prompt_sent_console_line`,
    which only the code path holding the bytes may print.

    ``sink`` IS THE OTHER HALF OF THE SAME HONESTY.  An order recorded into a
    recorder nobody drains is R307's window that goes nowhere, and until now
    this line read the same either way.  Pass the recorder the order went into
    and the line names it (:func:`sink_fingerprint`) and says whether anyone
    claimed to drain it (:func:`sink_drain_claim`); omit it and the line says
    ``sink=unnamed drain=unknown`` rather than pretending
    (pf-adversary, round `nilasm`, H4).
    """
    d = pending.destination
    return (
        "%s ORDER_RECORDED marker=%d scene=%d xyz=%d,%d,%d dir=%d"
        " confirm_predicted=%d window_expected=%d sent=0 %s"
        % (TOKEN, pending.marker_id, d.scene_id, d.x, d.y, d.z, d.direction,
           pending.confirm_id, int(pending.window_expected),
           sink_console_fields(sink)))


def prompt_sent_console_line(pending: PendingCheck, frame_bytes: int,
                             sink: Any = None) -> str:
    """The line for a ``TeleportCheckVital`` this server HANDED TO A SEND PATH.

    ONLY THE CALLER THAT HOLDS THE BYTES MAY PRINT THIS.  ``frame_bytes`` is
    the length of the frame :func:`encode_prompt` built and the caller queued;
    printing it from anywhere else re-creates exactly the confusion D-A1 found.
    It still is not proof that a window was DRAWN -- nothing comes back from a
    client on this path, and only a screen can say that -- but it is the honest
    server-side half of ``GT-309``'s first proof line.  IT HAS NO CALLER AT
    ALL TODAY, and that is written in the present tense on purpose: the drain
    at the end of ``dispatch()`` (chief, letter `20260908_0432`) is the caller
    it is FOR, on a branch this repository does not carry.  Saying "is the one
    caller" of something that does not exist is the mistake D-A1 punished
    (pf-adversary, round `nilasm`, M2).  ``frame_bytes`` is counted by the
    caller and verified by nothing here: a drain that builds the bytes and
    then dies before the socket can still print this line.

    PASS THE SINK YOU DRAINED.  Then this line and the ``ORDER_RECORDED`` line
    of the same order carry the same ``sink=`` word when -- and only when --
    the recorder that took the order is the recorder these bytes came out of.
    That comparison is what a reader can do with their eyes and what this
    module cannot do for them: nothing here can see the drain, so the check is
    "the two halves name one object", never "the drain ran"
    (pf-adversary, round `nilasm`, H4).
    """
    d = pending.destination
    return (
        "%s PROMPT_SENT marker=%d scene=%d xyz=%d,%d,%d dir=%d"
        " confirm_predicted=%d window_expected=%d bytes_out=%d %s"
        % (TOKEN, pending.marker_id, d.scene_id, d.x, d.y, d.z, d.direction,
           pending.confirm_id, int(pending.window_expected), frame_bytes,
           sink_console_fields(sink)))


def echo_console_line(pending: PendingCheck | None, echoed_marker_id: Any,
                      refusal: str | None) -> str:
    """The line for an inbound echo, accepted or refused, always the same shape."""
    expected = "none" if pending is None else str(pending.marker_id)
    shown = echoed_marker_id if type(echoed_marker_id) is int else "?"
    return (
        "%s ECHO expected=%s got=%s verdict=%s"
        % (TOKEN, expected, shown, "OK" if refusal is None else refusal))


def transport_console_line(pending: PendingCheck, frame_bytes: int) -> str:
    """The line for the transport this server sends back for a good echo.

    IT PRINTS THE INTENT THIS SERVER ACTED ON, NEVER WHAT THE CLIENT DID WITH
    IT (pf-adversary, round `ebh143`, D9).  ``bytes_out`` counts bytes handed
    to a send path; no byte of it comes back from the client, so this line is
    not evidence that a player arrived anywhere.  The only thing that can say
    that is a screen -- the attended ticket is what this lane opened for it.
    """
    d = pending.destination
    return (
        "%s TRANSPORT marker=%d scene=%d xyz=%d,%d,%d bytes_out=%d"
        % (TOKEN, pending.marker_id, d.scene_id, d.x, d.y, d.z, frame_bytes))


class TeleportCheckOrder(NamedTuple):
    """One recorded "ask this player to confirm travel to marker N".

    Recorded, not sent: ``lua_api`` builds no frames (``lua_api/message.py``'s
    own docstring states the same rule for the legacy system-message name,
    which the seam guard forbids any top-level module here from spelling), so
    the closure that a quest script calls records here and the dispatch branch
    that owns the socket reads it.  Keeping the two apart is what lets the Lua half be
    always-on today while the wire half is still one chief edit away.
    """

    character_id: int
    pending: PendingCheck


#: A recorder that refuses rather than grows: a script loop that calls
#: ``Player.TeleportCheck`` in a tight cycle must not grow this list without
#: bound in a long-lived session.  The number is this module's own choice and
#: is stated as such -- no letter measured a cap -- and the refusal is
#: counted, never silent.
ORDER_CAP = 64
ORDER_REFUSED_AT_CAP = "ORDER_REFUSED_AT_CAP"


#: What the console prints for the drain half when the sink was never claimed.
#: NOT an error and NOT a refusal: the order really was recorded, and this word
#: is the token saying out loud that it cannot tell whether anyone will ever
#: take it off the sink (pf-adversary, round `nilasm`, H4).
DRAIN_CLAIM_UNCLAIMED = "unclaimed"

#: What the console prints when the caller did not even say WHICH recorder took
#: the order.  Told apart from ``unclaimed`` on purpose: "nobody claimed this
#: sink" and "this line does not know its sink" are two different holes and a
#: reader who cannot tell them apart will chase the wrong one.
DRAIN_CLAIM_UNKNOWN = "unknown"
SINK_FINGERPRINT_UNNAMED = "unnamed"

#: A sink this process cannot hold a weak reference to cannot be told apart
#: from the next object that lands on its address, so it gets a fingerprint
#: that says exactly that instead of a sequence number that would be a lie.
SINK_FINGERPRINT_UNPINNED_SUFFIX = "unpinned"

#: A claim is printed on a space-delimited console line, in cp874, next to a
#: token an attended ticket greps for.  So it is one printable-ASCII word,
#: bounded, and refused at CLAIM time rather than sanitised at print time: the
#: caller who wrote the bad claim is the one who can fix it, and they are
#: standing right there when this raises.
DRAIN_CLAIM_MAX_LEN = 40

CLAIM_REFUSED_NOT_A_STRING = "CLAIM_REFUSED_NOT_A_STRING"
CLAIM_REFUSED_EMPTY = "CLAIM_REFUSED_EMPTY"
CLAIM_REFUSED_TOO_LONG = "CLAIM_REFUSED_TOO_LONG"
CLAIM_REFUSED_NOT_PRINTABLE_ASCII = "CLAIM_REFUSED_NOT_PRINTABLE_ASCII"
CLAIM_REFUSED_SINK_NOT_WEAK_REFERENCEABLE = (
    "CLAIM_REFUSED_SINK_NOT_WEAK_REFERENCEABLE")


class SinkClaimError(ValueError):
    """Raised by :func:`claim_sink_for_drain` when a claim cannot be trusted.

    Named like :class:`TeleportCheckError` and for the same reason: the drain
    that mis-claims must be able to tell "this lane refused my claim" apart
    from a ``TypeError`` out of its own plumbing.
    """


class _SinkEntry:
    """What this module remembers about one recorder object.

    ``ref`` is what makes the memory safe.  The dict is keyed by ``id(sink)``
    because a recorder is allowed to define ``__eq__`` (which would make two
    DIFFERENT recorders one key in any dict keyed by the object itself) and
    allowed to be unhashable, and neither may cost a lane its identity check.
    An address, though, is reused the moment the object at it dies -- so every
    lookup re-checks ``ref() is sink`` and a dead entry answers for nobody.
    """

    __slots__ = ("ref", "sequence", "claim")

    def __init__(self, ref, sequence: int) -> None:
        self.ref = ref
        self.sequence = sequence
        self.claim: str | None = None


_SINK_REGISTRY_LOCK = threading.RLock()
_SINK_REGISTRY: "dict[int, _SinkEntry]" = {}
_SINK_SEQUENCE = 0


def _forget_sink(key: int, dead_ref) -> None:
    """Drop a dead recorder's entry, and ONLY if it is still that entry.

    A weakref callback runs after the object is gone, which is exactly when a
    new object may already have been allocated at the same address and
    registered under the same key.  Deleting by key alone would then throw away
    a LIVE recorder's identity, and the next console line would say a different
    fingerprint for a sink that never moved.
    """
    with _SINK_REGISTRY_LOCK:
        entry = _SINK_REGISTRY.get(key)
        if entry is not None and entry.ref is dead_ref:
            del _SINK_REGISTRY[key]


def _entry_for(sink: Any, create: bool) -> "_SinkEntry | None":
    """This recorder's entry, minting one when asked and when possible."""
    global _SINK_SEQUENCE
    key = id(sink)
    with _SINK_REGISTRY_LOCK:
        entry = _SINK_REGISTRY.get(key)
        if entry is not None:
            if entry.ref() is sink:
                return entry
            # The address was reused.  The old entry belongs to an object that
            # is already gone; its claim must not be inherited by whoever
            # landed here next.
            del _SINK_REGISTRY[key]
        if not create:
            return None
        try:
            ref = weakref.ref(sink, lambda dead, key=key: _forget_sink(key, dead))
        except TypeError:
            return None
        _SINK_SEQUENCE += 1
        entry = _SinkEntry(ref, _SINK_SEQUENCE)
        _SINK_REGISTRY[key] = entry
        return entry


def _sink_type_name(sink: Any) -> str:
    """The recorder's class name, ASCII and printable, never a crash.

    Class names may hold non-ASCII (Python allows it) and a ``__class__`` may
    be a property that raises; either one reaching a cp874 console kills the
    line that was reporting on somebody else's mistake -- the same failure
    ``ascii()`` was introduced for one round ago.
    """
    try:
        name = type(sink).__name__
    except Exception:
        return "sink"
    cleaned = "".join(ch for ch in name if 33 <= ord(ch) <= 126)
    return cleaned[:40] or "sink"


def sink_fingerprint(sink: Any) -> str:
    """A per-object name for a recorder that two console lines can compare.

    THIS IS THE HALF OF H4 THAT IS NOT A PROMISE.  ``ORDER_RECORDED`` prints
    the fingerprint of the sink the order went INTO and ``PROMPT_SENT`` prints
    the fingerprint of the sink the bytes came OUT of, so a reader of one log
    can see with their own eyes whether the two halves are talking about the
    same object -- which is the failure R307 named ("a window that goes
    nowhere") and which nothing in this file could previously show.

    The sequence number is per process and never reused; the address is not
    printed, because an address IS reused and a reader comparing two lines
    minutes apart would have no way to know it.  A recorder that cannot be
    weak-referenced gets ``@unpinned`` instead of a number, because for that
    object this module genuinely cannot tell one incarnation from the next.
    """
    entry = _entry_for(sink, create=True)
    if entry is None:
        return "%s@%s" % (_sink_type_name(sink),
                          SINK_FINGERPRINT_UNPINNED_SUFFIX)
    return "%s@%d" % (_sink_type_name(sink), entry.sequence)


def claim_sink_for_drain(sink: Any, claim: Any) -> str:
    """Record that ``claim`` is the code that will DRAIN this recorder.

    WHAT THIS PROVES, EXACTLY: that some caller, holding this very object,
    said so.  It is not a promise that the drain will run, and this module
    cannot make one -- the drain lives in ``runtime.py``'s dispatch, which is
    chief's file and not this lane's to inspect.  What it buys is that the
    two ways of getting this wrong stop looking identical on the console: a
    sink NOBODY claimed now prints ``drain=unclaimed``, and a sink claimed by
    a drain that then drains a DIFFERENT object prints a fingerprint the
    ``PROMPT_SENT`` line does not repeat.  Before this, both cases printed
    ``stored=1`` and read like success (pf-adversary, round `nilasm`, H4).

    Refuses loudly rather than sanitising: a claim is printed unescaped next to
    the token an attended ticket greps for, so a claim carrying a space, a
    newline or a byte the bridge's cp874 console cannot render would corrupt
    the very line it was meant to make readable.  A recorder that cannot be
    weak-referenced is refused too, with the one-line fix in the message --
    without a weak reference this module cannot notice the object dying and
    would hand its claim to whatever is allocated at that address next.
    """
    if type(claim) is not str:
        raise SinkClaimError(
            "%s claim=%s: a drain claim is a short printable-ASCII word"
            % (CLAIM_REFUSED_NOT_A_STRING, ascii(claim)))
    if not claim:
        raise SinkClaimError(
            "%s: a drain claim names the code that will drain this sink"
            % CLAIM_REFUSED_EMPTY)
    if len(claim) > DRAIN_CLAIM_MAX_LEN:
        raise SinkClaimError(
            "%s claim=%s len=%d max=%d"
            % (CLAIM_REFUSED_TOO_LONG, ascii(claim), len(claim),
               DRAIN_CLAIM_MAX_LEN))
    if any(not (33 <= ord(ch) <= 126) for ch in claim):
        raise SinkClaimError(
            "%s claim=%s: no spaces, no control bytes, no cp874 gambles"
            % (CLAIM_REFUSED_NOT_PRINTABLE_ASCII, ascii(claim)))
    entry = _entry_for(sink, create=True)
    if entry is None:
        raise SinkClaimError(
            "%s sink=%s: give the recorder a weak reference slot "
            "(add \"__weakref__\" to its __slots__) so a claim cannot "
            "outlive the object that carries it"
            % (CLAIM_REFUSED_SINK_NOT_WEAK_REFERENCEABLE,
               _sink_type_name(sink)))
    with _SINK_REGISTRY_LOCK:
        entry.claim = claim
    return claim


def sink_drain_claim(sink: Any) -> str | None:
    """The claim on this recorder, or ``None`` when nobody claimed it.

    Never mints an entry: asking who will drain a sink must not be the reason
    this module starts remembering it.
    """
    entry = _entry_for(sink, create=False)
    if entry is None:
        return None
    with _SINK_REGISTRY_LOCK:
        return entry.claim


def sink_console_fields(sink: Any) -> str:
    """The ``sink=... drain=...`` half of a console line, one shape always.

    ``sink is None`` means the caller did not say which recorder it used, and
    that reads ``sink=unnamed drain=unknown`` -- not ``unclaimed``, which is a
    measured fact about a named object.
    """
    if sink is None:
        return ("sink=%s drain=%s"
                % (SINK_FINGERPRINT_UNNAMED, DRAIN_CLAIM_UNKNOWN))
    claim = sink_drain_claim(sink)
    return ("sink=%s drain=%s"
            % (sink_fingerprint(sink),
               DRAIN_CLAIM_UNCLAIMED if claim is None else claim))


def sink_stored_count(returned: Any) -> int | None:
    """What a recorder's ``record()`` answered, or ``None`` for "it did not".

    ``InMemoryTeleportCheckSink.record`` returns ``1``/``0``, and this module
    made that return value LOAD-BEARING when the live door started printing a
    console line only for an order the sink actually holds.  The shape check in
    ``lua_api.player`` can see that ``record`` is callable and cannot see what
    it returns, so the most obvious recorder anyone would write -- a method
    with no ``return`` -- came back ``None`` and killed the door with
    ``TypeError: %d format: a real number is required`` AFTER the order was
    already recorded: an exception out of a Lua closure, for a window that had
    in fact been opened (pf-adversary, round `ew9416`, D-A5).

    So the contract is stated here and enforced nowhere else: a recorder that
    answers with anything but an ``int`` is treated as HAVING RECORDED but not
    having counted -- ``None`` -- which the caller reports as ``stored=unknown``
    rather than crashing or silently swallowing the order.  ``bool`` is not an
    ``int`` for this purpose: ``True`` would print as ``stored=1`` and hide a
    recorder that answers with a flag.
    """
    if isinstance(returned, bool):
        return None
    if type(returned) is not int:
        return None
    return returned


class InMemoryTeleportCheckSink:
    """The default recorder, fresh and private per namespace.

    Same posture ``lua_api.player.build_namespace`` already takes for its
    ``InMemoryPlayerMobAppearStore`` and ``InMemoryMessageSink``: a default
    that is inert and unshared, never a process singleton two unrelated tests
    can collide inside.
    """

    #: ``__weakref__`` is load-bearing, not boilerplate: without a weak
    #: reference slot this recorder cannot be claimed for draining at all
    #: (:func:`claim_sink_for_drain` refuses it by name), because this
    #: module would have no way to notice the object dying and would hand
    #: its claim to whatever is allocated at that address next.
    __slots__ = ("orders", "refusals", "__weakref__")

    def __init__(self) -> None:
        self.orders: list[TeleportCheckOrder] = []
        self.refusals: list[str] = []

    def record(self, character_id: int, pending: PendingCheck) -> int:
        """``1`` when the order was stored, ``0`` when the cap refused it.

        THE RETURN VALUE IS PART OF THE SHAPE, not a convenience: the live door
        prints its console line only for a stored order, so a recorder that
        answers nothing is answering "I did not count", which
        :func:`sink_stored_count` turns into ``stored=unknown`` (D-A5).
        """
        if len(self.orders) >= ORDER_CAP:
            self.refusals.append(ORDER_REFUSED_AT_CAP)
            return 0
        self.orders.append(TeleportCheckOrder(character_id, pending))
        return 1

    def record_refusal(self, reason: str) -> None:
        self.refusals.append(reason)

    def take(self, character_id: int, echoed_marker_id: int):
        """Remove and return the order this echo consumes, or ``None``.

        The removal is the point -- see :func:`resolve_echo`.  A refusal is
        counted by name so a run can say how many echoes answered nothing
        without grepping its own log.
        """
        index = resolve_echo(self.orders, character_id, echoed_marker_id)
        if index is None:
            self.refusals.append(ECHO_REFUSED_NO_ORDER_FOR_THIS_PLAYER)
            return None
        return self.orders.pop(index)
