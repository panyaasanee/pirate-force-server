"""LANE-B: how many actors a recomposed census ACTUALLY tells the client to read.

ROUND z096sw.  This module exists because of a sentence this lane wrote
against itself, in ``tests/test_world_wipe_headless_proof.py``:

    THE CONSOLE TOKEN IS NOT EVIDENCE OF COUNT, AND THIS FILE DOES NOT MAKE
    IT SO.  ``MOB_COMBAT_BAR_CENSUS_RECOMPOSE actor_count=108`` prints
    ``self.world_census_actor_count``, read from session state BEFORE the
    frame is composed.  It is an INPUT.

That is exactly right, and it is why the closing criterion this lane was
given for the world-wipe item -- "boot flagless, take one hit and one
death, and the census after the event is still whole, GREPPABLE FROM THE
CONSOLE" -- could not be met by the token that already existed.  Round
wmomy7 refused to declare the item ready for that reason and said so.  This
module is the missing half: it reads the count back off the bytes the
recompose actually produced, so the console line carries a MEASUREMENT
beside the input instead of an input alone.

WHAT IT READS, AND WHY THAT NUMBER AND NOT ANOTHER.
``world_population_handoff.wire_count_of`` reads the collection header --
the number the CLIENT is told to read -- out of a composed ``pc``.  The
headless proof already uses it for exactly this purpose and calls it "what
the client is TOLD to read".  A count taken any other way (the roster, the
session's actor count, the composer's own return value) is a count of what
the server MEANT, and the whole point of the world-wipe item is that those
two numbers came apart without anyone noticing.

THE PAIR CHECK IS NOT OPTIONAL, AND IT IS THE REASON THIS IS A MODULE AND
NOT AN INLINE ``%d``.  ``v141:7755`` sends ``out_frame`` and nothing else,
so a count read off the ``pc`` is a count of bytes no client receives
unless the two are the same collection.  pf-adversary built precisely that
regression against the headless proof's first draft: update the ``pc`` and
leave the ``frame`` bound to a stale one-entry collection, and every
reading stayed green while every kill put one body on the wire.  So this
module refuses to report a number until ``frame == legacy.frame_pc(pc)``,
and when it cannot, it prints a NAMED absence rather than a plausible
number.

FAIL-CLOSED, AND FAIL-CLOSED HERE MEANS "NEVER RAISES AN ``Exception``" --
which is NARROWER than "never raises", and is written the narrow way
because pf-adversary fuzzed this module (9 legacy seams x 9 ``pc`` x 7
``frame`` x 7 count/target pairs) and the broad sentence was false as
stated.  A ``BaseException`` from the legacy seam -- ``KeyboardInterrupt``,
``SystemExit`` -- still escapes, and SHOULD: a console line is not worth
swallowing a shutdown.  Everything the fuzz reached that is not one of
those (``bytearray``, ``memoryview``, ``bytes`` subclasses, truncated
bytes, ``RecursionError``, a ``legacy`` that is ``None``/text/an int, a
seam whose ``frame_pc`` raises, and a seam whose returned frame refuses
``==``) comes back as a named absence.

That distinction matters because every caller of
this module is on ``runtime.py``'s hit/death dispatch path, inside the
branch that composes census frames.  ``v141:7440`` has no ``except``: an
escape from there unwinds out of the listener thread and takes the
player's connection with it.  A console line is never worth that, so every
entry point here catches ``Exception`` and degrades to
``wire_actors=unmeasured reason=<name>``.  The refusal is visible in the
console rather than silent, which is the same convention
``mob_census_hostility.describe_census_hostility`` and
``mob_death.describe_roster_override_coverage`` already follow.

NONCLAIMS.

1. WIRE LAYER ONLY.  A whole collection header says the frame leaving the
   server names N actors.  It does NOT say a client drew N actors, and it
   does not touch ``GT-084``/``RIDER-084-A``'s ``OW1``-``OW3``, which are
   attended and still unrun.
2. THE HEADER CHECK IS WEAK IN A KNOWN WAY, INHERITED NOT INVENTED.
   ``wire_count_of``'s own docstring says ``0x12`` is the generic u16-tag
   byte and not a signature, so it catches a truncated or reshaped header,
   not a forged one.  The pair check against ``frame_pc`` is what actually
   ties the number to the transmitted bytes; this module adds nothing to
   the header check itself and claims nothing it does not do.
3. THIS DOES NOT COUNT BODIES.  It reports the number the collection
   header DECLARES.  A collection that declares 108 and carries 12 is a
   defect this line would not see -- the headless proof's per-identity
   occurrence count is what sees that, and this module does not replace
   it, which is why ``tests/test_world_wipe_headless_proof.py`` keeps
   every reading it already had.
4. IT DOES NOT DECIDE WHAT IS WHOLE.  No expected count is compiled in:
   the line reports what arrival declared alongside what the recompose
   declared where a caller supplies both, and a reader compares them.
   Pinning a literal here would be this lane deciding the census size,
   which belongs to ``world_population`` and moved once already (115 ->
   108, RE-128).
"""

from __future__ import annotations

from typing import Any

from . import world_population_handoff


# Convention markers only; nothing in this tree branches on them.
production_allowed = True
test_only = False

MOB_CENSUS_WIRE_COUNT_LANE = "B_COMBAT"

# Named absences.  Every one of these is a reason a number could not be
# taken, printed in place of the number so a console reader is never handed
# a plausible count that came from bytes nobody sends.
UNMEASURED = "unmeasured"
REASON_PC_NOT_BYTES = "pc_not_bytes"
REASON_FRAME_NOT_BYTES = "frame_not_bytes"
REASON_FRAME_IS_NOT_THIS_PC = "frame_is_not_this_pc"
REASON_HEADER_UNREADABLE = "header_unreadable"
REASON_LEGACY_REFUSED = "legacy_refused"

UNMEASURED_REASONS = (
    REASON_PC_NOT_BYTES,
    REASON_FRAME_NOT_BYTES,
    REASON_FRAME_IS_NOT_THIS_PC,
    REASON_HEADER_UNREADABLE,
    REASON_LEGACY_REFUSED,
)


def wire_actor_count(legacy: Any, pc: Any, frame: Any) -> dict[str, Any]:
    """How many actors the transmitted collection declares, or why not.

    Returns a record, never a bare int, because "could not measure" is an
    answer this caller has to be able to print and must not be able to
    confuse with a count.  ``count`` is an ``int`` when ``measured`` is
    true and ``None`` when it is false; ``reason`` is ``None`` when
    ``measured`` is true and one of :data:`UNMEASURED_REASONS` otherwise.

    NEVER RAISES AN ``Exception`` (a ``BaseException`` from the legacy
    seam is deliberately not swallowed -- see the module docstring).  Every
    caller is inside ``runtime.py``'s dispatch, where an escape kills the
    listener thread.
    """
    if type(pc) is not bytes:
        return _unmeasured(REASON_PC_NOT_BYTES)
    if type(frame) is not bytes:
        return _unmeasured(REASON_FRAME_NOT_BYTES)
    try:
        own_frame = legacy.frame_pc(pc)
        # THE COMPARISON IS INSIDE THE ``try`` ON PURPOSE, and it was
        # outside it in the first draft of this module.  ``frame_pc`` is a
        # seam: a stub, a mock or a drifted legacy may return an object
        # whose ``__eq__`` raises, and a comparison that escapes from here
        # unwinds the listener thread exactly as a raising ``frame_pc``
        # would.  A module whose whole promise is "never raises" cannot
        # leave one operator outside the net because the operator looks
        # harmless.
        same_collection = own_frame == frame
    except Exception:
        # A legacy seam that refuses to frame these bytes, or refuses to
        # compare them, is a real answer about them, and it is not this
        # line's business to interpret which of the two happened.
        return _unmeasured(REASON_LEGACY_REFUSED)
    if not same_collection:
        # THE ONE THAT MATTERS.  The pc and the frame are different
        # collections, so any count off the pc describes bytes the client
        # will never receive -- the exact regression pf-adversary built.
        return _unmeasured(REASON_FRAME_IS_NOT_THIS_PC)
    try:
        count = world_population_handoff.wire_count_of(pc)
    except Exception:
        return _unmeasured(REASON_HEADER_UNREADABLE)
    if type(count) is not int or count < 0:
        return _unmeasured(REASON_HEADER_UNREADABLE)
    return {"measured": True, "count": count, "reason": None}


def _unmeasured(reason: str) -> dict[str, Any]:
    return {"measured": False, "count": None, "reason": reason}


def describe_census_recompose(
    legacy: Any,
    token: str,
    pc: Any,
    frame: Any,
    *,
    target_identity: Any = None,
    input_count: Any = None,
) -> str:
    """One ASCII console line for a recomposed census (G-OBS).

    ``token`` is the caller's own grep token
    (``MOB_COMBAT_BAR_CENSUS_RECOMPOSE`` /
    ``MOB_DEATH_FRAMES_CENSUS_RECOMPOSE``).  It is passed in rather than
    chosen here so the two call sites keep the tokens they already have and
    no existing grep, ticket or runbook line stops matching.

    ``actor_count=`` KEEPS ITS OLD MEANING ON PURPOSE.  It is the session's
    pre-compose input, which is what that field has printed since the
    console gate was added, and ``GAME_TEST_QUEUE.md`` already tells testers
    to grep for it.  Silently redefining a field a tester reads would be a
    worse defect than the one this module fixes.  The measurement is the NEW
    field, ``wire_actors=``, and the two being different numbers is
    information rather than a contradiction: the input is what the composer
    was asked for, the measurement is what the client is told.

    Plain ASCII, single line, no escaping -- the bridge console is cp874.
    NEVER RAISES AN ``Exception``, on the same terms as
    :func:`wire_actor_count`.
    """
    reading = wire_actor_count(legacy, pc, frame)
    if reading["measured"]:
        wire = "%d" % reading["count"]
    else:
        wire = "%s reason=%s" % (UNMEASURED, reading["reason"])
    return "%s actor_count=%s wire_actors=%s target=%s" % (
        _ascii_token(token),
        _plain_int(input_count),
        wire,
        _plain_identity(target_identity),
    )


def _ascii_token(token: Any) -> str:
    if type(token) is not str or not token:
        return "MOB_CENSUS_RECOMPOSE"
    return "".join(c for c in token if 32 <= ord(c) < 127) or (
        "MOB_CENSUS_RECOMPOSE")


def _plain_int(value: Any) -> str:
    # A named absence rather than "0": a caller that has no input count is
    # not a caller whose input count is zero.
    if type(value) is not int or type(value) is bool:
        return "none"
    return "%d" % value


def _plain_identity(value: Any) -> str:
    if type(value) is not int or type(value) is bool or value < 0:
        return "none"
    return "0x%X" % value
