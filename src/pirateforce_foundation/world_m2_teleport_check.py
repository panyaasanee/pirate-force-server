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
wire (RE-303 BUILD_IMPACT 5).  This module keeps ONE pending marker per
session and lets a later :func:`open_check` overwrite it -- that is the whole
cancel story: the next prompt replaces the abandoned one.  It deliberately
does NOT invent an expiry clock, because a clock here would be a number no
letter measured.

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

from typing import Any, NamedTuple

from . import world_marker_copy

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

#: ``MARKER`` is 390 rows, ids 1..390 (RE-303 section 4; the same count is
#: independently pinned in ``world_scene_marker.MARKER_ROW_COUNT``).
MARKER_ID_MIN = 1
MARKER_ID_MAX = 390

#: A u16 field cannot carry more than this, and the range check below reports
#: the two failures separately: an id outside the TABLE is a caller mistake,
#: an id outside the FIELD is a frame that could not be built at all.
_U16_MAX = 0xFFFF

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

CHECK_REFUSED_MARKER_ID_NOT_AN_INT = "CHECK_REFUSED_MARKER_ID_NOT_AN_INT"
CHECK_REFUSED_MARKER_ID_OUT_OF_TABLE = "CHECK_REFUSED_MARKER_ID_OUT_OF_TABLE"
CHECK_REFUSED_MARKER_ROW_NOT_PINNED = "CHECK_REFUSED_MARKER_ROW_NOT_PINNED"
ECHO_REFUSED_NOTHING_PENDING = "ECHO_REFUSED_NOTHING_PENDING"
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

    ``world_marker_copy.verbatim_marker_row``'s docstring is emphatic about
    that direction and this type keeps the emphasis: indexing ``MARKER`` BY A
    SCENE lies for 257 scenes, so nothing here ever goes back the other way.
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


def marker_destination(marker_id: Any) -> MarkerDestination:
    """The row ``marker_id`` names, or raise :class:`TeleportCheckError`.

    Reads the committed crosswalk (``world_marker_copy``), which carries 18 of
    the client's 390 rows verbatim.  "Absent here" therefore means NOT PINNED,
    never "not in the client's table" -- the refusal says so by name, because
    the two have completely different fixes (regenerate the copy on the bridge
    vs. the caller named a row that does not exist).
    """
    coerced = _coerce_marker_id(marker_id)
    if coerced is None:
        raise TeleportCheckError(
            "%s marker_id=%r" % (CHECK_REFUSED_MARKER_ID_NOT_AN_INT, marker_id))
    if not (MARKER_ID_MIN <= coerced <= MARKER_ID_MAX) or coerced > _U16_MAX:
        raise TeleportCheckError(
            "%s marker_id=%d range=%d..%d"
            % (CHECK_REFUSED_MARKER_ID_OUT_OF_TABLE, coerced,
               MARKER_ID_MIN, MARKER_ID_MAX))
    row = world_marker_copy.verbatim_marker_row(coerced)
    if row is None:
        raise TeleportCheckError(
            "%s marker_id=%d (the committed copy keeps 18 rows verbatim; "
            "regenerate it on the bridge, do not type the numbers here)"
            % (CHECK_REFUSED_MARKER_ROW_NOT_PINNED, coerced))
    scene_id, x, y, z, direction = row
    return MarkerDestination(coerced, scene_id, x, y, z, direction)


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

    ``legacy`` is the v141 module, injected the same way
    ``world_m2_provisioning_trial.encode_trial_records`` takes it: this
    package does not import ``current/`` and does not own the envelope.

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


def prompt_console_line(pending: PendingCheck) -> str:
    """ASCII only (the bridge console is cp874): what was sent, and what the
    client is expected to draw for it."""
    d = pending.destination
    return (
        "%s PROMPT marker=%d scene=%d xyz=%d,%d,%d dir=%d"
        " confirm_predicted=%d window_expected=%d"
        % (TOKEN, pending.marker_id, d.scene_id, d.x, d.y, d.z, d.direction,
           pending.confirm_id, int(pending.window_expected)))


def echo_console_line(pending: PendingCheck | None, echoed_marker_id: Any,
                      refusal: str | None) -> str:
    """The line for an inbound echo, accepted or refused, always the same shape."""
    expected = "none" if pending is None else str(pending.marker_id)
    shown = echoed_marker_id if type(echoed_marker_id) is int else "?"
    return (
        "%s ECHO expected=%s got=%s verdict=%s"
        % (TOKEN, expected, shown, "OK" if refusal is None else refusal))


def transport_console_line(pending: PendingCheck, frame_bytes: int) -> str:
    """The line for the transport this server sends back for a good echo."""
    d = pending.destination
    return (
        "%s TRANSPORT marker=%d scene=%d xyz=%d,%d,%d bytes_out=%d"
        % (TOKEN, pending.marker_id, d.scene_id, d.x, d.y, d.z, frame_bytes))


class TeleportCheckOrder(NamedTuple):
    """One recorded "ask this player to confirm travel to marker N".

    Recorded, not sent: ``lua_api`` builds no frames (``lua_api/message.py``'s
    own docstring states the same rule for ``ShowMessage``), so the closure
    that a quest script calls records here and the dispatch branch that owns
    the socket reads it.  Keeping the two apart is what lets the Lua half be
    always-on today while the wire half is still one chief edit away.
    """

    character_id: int
    pending: PendingCheck


#: A recorder that has to forget: a script loop that calls
#: ``Player.TeleportCheck`` in a tight cycle must not grow this list without
#: bound in a long-lived session.  The number is this module's own choice and
#: is stated as such -- no letter measured a cap -- and the refusal is
#: counted, never silent.
ORDER_CAP = 64
ORDER_REFUSED_AT_CAP = "ORDER_REFUSED_AT_CAP"


class InMemoryTeleportCheckSink:
    """The default recorder, fresh and private per namespace.

    Same posture ``lua_api.player.build_namespace`` already takes for its
    ``InMemoryPlayerMobAppearStore`` and ``InMemoryMessageSink``: a default
    that is inert and unshared, never a process singleton two unrelated tests
    can collide inside.
    """

    __slots__ = ("orders", "refusals")

    def __init__(self) -> None:
        self.orders: list[TeleportCheckOrder] = []
        self.refusals: list[str] = []

    def record(self, character_id: int, pending: PendingCheck) -> int:
        """``1`` when the order was stored, ``0`` when the cap refused it."""
        if len(self.orders) >= ORDER_CAP:
            self.refusals.append(ORDER_REFUSED_AT_CAP)
            return 0
        self.orders.append(TeleportCheckOrder(character_id, pending))
        return 1

    def record_refusal(self, reason: str) -> None:
        self.refusals.append(reason)
