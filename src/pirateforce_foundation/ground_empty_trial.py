"""LANE-B: the attended-only arm for "the floor emptied and nothing said so".

WHAT IS BROKEN, MEASURED ON A REAL SCREEN.  ``GT-242``/R316, 2026-09-05
(``pf_bridge/notes_to_chief/20260905_1102_KA1A-R316-RESULTS-...md`` finding
(d)): ground items stayed drawn on the client past 120 seconds while this
server had already expired them -- the console printed ``EXPIRY_HELD
expired=2`` and every click on one of those labels came back
``drop_already_taken``.  The world on the screen and the world on the server
disagreed, and nothing in the pipe was ever going to fix it.

WHY THE ORDINARY FIX DOES NOT REACH THIS CASE.
``DropLedgerCell.frames_after_rows_expired`` publishes the scene's REMAINING
rows when a sweep retires one -- the expired row is removed by being absent
from a generation that still carries something.  When the sweep empties the
floor there is nothing left to carry: that method returns ``(owed, 0, ())``
and holds the debt for ever, which its own docstring has said in capitals
since the round that wrote it.  ``COO-DECISION 20260903_1942`` item 3 offered
the empty-pool branch, this lane declined it, and ``COO-DECISION
20260905_1247`` item 1 has now ruled that the condition the refusal rested on
-- "somebody must measure it on a screen first" -- is satisfied by R316.

WHAT THIS MODULE IS, THEN.  The arm for that measurement, and nothing more.
It composes ONE zero-element ground generation -- the same envelope, the same
mask, the same ``0x12`` count record every generation this lane has ever put
on a real client's wire carries, with the count set to ``0`` and no elements
after it -- and it is reachable only from a process an owner armed by hand.

WHAT IT IS TESTING, IN ONE SENTENCE, because the ticket has to be able to
read a negative correctly: ``RE-130`` T3 says the consumer reads ``count``
off the list object at ``+0x2C`` and that every NONEMPTY generation erases
the keys it omits -- but it read a zero count as falling through to the
epilogue, i.e. a no-op, and that reading has never been confirmed against a
screen.  If the labels vanish, the empty generation is the delete frame this
lane needs and ``rows_left == 0`` stops being a dead end.  If nothing
happens, RE-130's reading is confirmed on the screen, this arm is a measured
negative, and the next suspect is the OTHER half of the narrow RE ticket
(which part of a successful ``MOB_PICKUP`` removes the label, as distinct
from the part that fills the bag).

FAIL-CLOSED, AND WHAT "UNARMED" GUARANTEES.  With ``PF_GROUND_EMPTY_TRIAL``
unset -- every ordinary boot -- ``arm()`` is ``False``, no byte is composed,
no console line is printed, and ``frames_after_rows_expired`` returns exactly
what it returns on ``main`` today.  ``COO-DECISION 20260905_1247`` item 4 is
explicit that the ``rows_left = 0`` branch keeps its current behaviour until
the screen answers, so production is unchanged BY DESIGN here, not by
oversight.  The gate is an environment variable for the same reason
``PF_POSE_TRIAL`` and ``PF_SPEED_TRIAL`` are: ``app.py``'s argument parsing
is chief's file and this lane may not edit it, and the attended bridge
already arms trials this way.

NEVER RAISES ON A REQUEST PATH.  The gate read and the compose both run
inside ``state.dispatch()`` under the frozen ``game_listener``, which has no
except handlers (interlock X07): an exception here would kill the accept loop
for every session over one empty floor.  ``frames_for_empty_floor`` therefore
returns ``()`` on anything it cannot compose, and says so on the console.
"""
import os

# The variable an owner sets before the boot.  ``set``, not ``setx``: ``setx``
# writes the registry and would arm every future boot invisibly -- the same
# warning ``pose_trial`` carries, for the same operator.
GROUND_EMPTY_TRIAL_ENV = "PF_GROUND_EMPTY_TRIAL"

# Console tokens.  ASCII, greppable off a cp874 console.
GROUND_EMPTY_TRIAL_SENT = "GROUND_EMPTY_TRIAL_SENT"
GROUND_EMPTY_TRIAL_REFUSED = "GROUND_EMPTY_TRIAL_REFUSED"


def _say(line):
    """Print one trial line, and never raise into ``state.dispatch()``.

    ``print`` to a closed stdout raises ``ValueError`` and to a broken pipe
    ``BrokenPipeError``; the frozen ``game_listener`` above this call has no
    except handlers (interlock X07), so either one would kill the thread over
    a log line.  Same wrapper, same reason, as ``action_ack._say``.
    """
    if line is None:
        return
    try:
        print(line)
    except Exception:  # noqa: BLE001 - a log line never kills the listener
        pass


def armed(environ=None):
    """True only when an owner set the variable to ``1`` in THIS process.

    Anything else -- unset, empty, ``0``, ``true``, a typo -- is unarmed.  A
    trial that guesses what an operator meant is a trial whose negative
    result nobody can trust.  Never raises: the whole read is inside the
    ``try`` for the interlock X07 reason in the module header.
    """
    try:
        source = os.environ if environ is None else environ
        raw = source.get(GROUND_EMPTY_TRIAL_ENV)
        return isinstance(raw, str) and raw.strip() == "1"
    except Exception:  # noqa: BLE001 - see the module docstring
        return False


def empty_generation_pc(legacy):
    """The zero-element ground generation's ``pc`` bytes.

    Composed through the SAME envelope tags ``mob_loot.drop_collection_pc``
    composes, in the same order, rather than a second literal: the ONLY thing
    this frame must differ from a real generation in is its count, and a
    hand-written envelope could differ in a byte nobody noticed and turn a
    negative result into a wrong conclusion.  The envelope is then compared
    against that module's own pin before it is returned.

    Raises ``MobLootContractError`` if the composed bytes are not the pinned
    envelope with a zero count and nothing after it -- this function is not on
    a request path; ``frames_for_empty_floor`` is, and it is what catches.
    """
    from . import mob_loot

    pc = bytearray()
    pc += legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_RES)
    pc += legacy.u32tag(0x14, 0)
    pc += legacy.u8tag(0x08, mob_loot.ENVELOPE_VERSION)
    pc += legacy.u8tag(0x0B, 0)
    pc += legacy.u8tag(0x0B, mob_loot.RUNTIME_DERIVED_BIT_GROUND_LIST)
    pc += legacy.u16tag(mob_loot.ELEMENT_LIST_COUNT_TAG, 0)
    pc = bytes(pc)
    if len(pc) != mob_loot.DROP_ENVELOPE_SIZE:
        raise mob_loot.MobLootContractError(
            mob_loot.REFUSE_COMPOSED_BYTES_OFF_PIN,
            "a zero-element ground pc is %d bytes, composed %d"
            % (mob_loot.DROP_ENVELOPE_SIZE, len(pc)))
    constant = mob_loot.DROP_ENVELOPE_CONSTANT_SIZE
    if pc[:constant] != mob_loot.DROP_ENVELOPE_CONSTANT_PIN:
        raise mob_loot.MobLootContractError(
            mob_loot.REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the composed envelope is not the pinned envelope; the legacy "
            "serializer moved under this lane and it refuses to emit")
    if pc[constant] != mob_loot.ELEMENT_LIST_COUNT_TAG:
        raise mob_loot.MobLootContractError(
            mob_loot.REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the count record does not start with the pinned 0x12 tag")
    if pc[constant + 1:] != b"\x00\x00":
        raise mob_loot.MobLootContractError(
            mob_loot.REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the generation does not declare zero elements")
    return pc


def frames_for_empty_floor(legacy, environ=None):
    """``(frames, console_line_or_None)`` for a floor a sweep just emptied.

    ``((), None)`` -- compose and send NOTHING, print NOTHING -- whenever the
    trial is unarmed, which is every ordinary boot.  That is the production
    contract ``COO-DECISION 20260905_1247`` item 4 requires, and it is the
    first branch here so that no code below it can run on an unarmed server.

    Armed, it returns one framed zero-element generation and the console line
    the attended ticket greps.  It never raises: a serializer that will not
    compose the envelope costs the trial its frame and says which refusal it
    was, and the accept loop keeps running (interlock X07).

    THE LINE IS PRINTED HERE, not by the caller, and it is returned as well so
    a test can read it without capturing stdout.  The caller
    (``mob_loot.DropLedgerCell.frames_after_rows_expired``) is a pure composer
    that prints nothing anywhere else, and this arm must not be the thing that
    gives it a console voice on a path an unarmed boot also walks.
    """
    if not armed(environ):
        return ((), None)
    try:
        pc = empty_generation_pc(legacy)
        frame = legacy.frame_pc(pc)
    except Exception as exc:  # noqa: BLE001 - see the module docstring
        # TYPE NAME ONLY, never the message: an exception message can carry a
        # byte the cp874 console cannot encode, and the encode error would
        # land inside this very handler.  Three other modules in this package
        # learned that by measurement.
        line = "%s %s" % (GROUND_EMPTY_TRIAL_REFUSED, type(exc).__name__)
        _say(line)
        return ((), line)
    line = "%s elements=0 bytes=%d" % (GROUND_EMPTY_TRIAL_SENT, len(pc))
    _say(line)
    return (((pc, frame),), line)
