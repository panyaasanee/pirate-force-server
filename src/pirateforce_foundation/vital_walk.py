"""LANE-E / VITAL-WALK-001: read EVERY nested vital in one inbound frame.

WHY THIS FILE EXISTS.  ``current/pf_login_game_server_v141.py:parse_outer``
reads the FIRST nested vital of a frame and hands the whole remaining tail
over as that vital's body::

    if outer_mask & 0x02:
        vital_count = c.u16(0x12)
        if vital_count:
            # All client packets seen so far contain one nested vital. With
            # more than one, boundaries require each vital's serializer
            # schema.
            nested_offset = c.p
            nested_id = c.u16(0x12)
            nested_version = c.u8(0x0B)
            nested_payload = pc[c.p:]

The comment is honest about its own limit and the limit turned out to be
false against the real client.  Attended round R303 measured ``vital_count``
of 5 on live inbound traffic (ka1-A, pf_bridge letter 20260902_1800, owner
at the keyboard and agreeing with the diagnosis), which cost two things the
owner watched fail with her own eyes:

  * 42 of 46 pickup clicks were thrown away before the body was decoded;
  * ``last_target_pos`` froze, so the server refused a player standing 173
    units from a drop on the grounds that she was 9250 units away -- the
    last position it had been allowed to learn.

WHAT THIS MODULE DOES, AND THE ONE THING IT REFUSES TO DO.  ``v141`` never
threw the tail away: ``raw_pc`` holds every byte of the frame.  What was
missing was the WALK, not the data.  This module walks it, and it walks it
only where the geometry is CLOSED -- one declared body length per vital id,
derived from committed artifacts and cross-checked against a captured byte
dump.  An id with no length in the table STOPS THE WALK.  It does not guess,
it does not scan for the next 0x12 byte, and it does not fall back to a
partial answer, because a guessed boundary means handing a lane the bytes
that belong to the vital next door.  (Read NONCLAIM 5: that is the guarantee
for an UNKNOWN id.  A declared-but-wrong length is a different failure and
this module does not detect it.)

``v141`` IS NOT TOUCHED.  Nothing here edits, monkey-patches or re-implements
the frozen snapshot; the walk reads ``parsed.raw_pc`` and hands each vital
back as an ordinary ``legacy.ParsedOuter`` so the EXISTING v141 decoders read
it unchanged.  That shape is not invented here either -- ``action_ack.py``
(``parse_scene006_ea7d``, lines 24-52) has walked a 2- and a 6-vital frame
this way on main for days, and ``damage_model_hypothesis.py:982`` walks
``range(vital_count)`` as well.  This module is those two lifted into one
place with a length table and a name.

HOW THE LENGTH TABLE WAS ESTABLISHED (G1: two independent sources each).

  ``ON_LAND_VITAL`` 0x1EB4, body 23 bytes
      (a) ``action_ack.py:38-40`` walks it as 4 x f32(tag 0x2A) + u16(tag
          0x0F) = 4*5 + 3 = 23.
      (b) The R303 capture of frame #714 (156 bytes, ka1-A's letter) shows
          ``12 B4 1E 0B 00 <4 floats> 0F 01 00`` four times.

  ``TARGET_POS_VITAL`` 0x2A90, body 24 bytes
      THIS ROW HAS ONE SOURCE, NOT TWO, AND SAYING OTHERWISE WOULD BE A
      FALSE G1 CLAIM.  An earlier draft of this docstring listed
      ``action_ack.py:41-43`` (4 x f32 + u8 + u8) and the R303 frame #714
      dump as independent.  They are not: BOTH put TargetPos LAST in the
      frame, and in a last-position vital "24-byte body" and "22-byte body
      plus a 2-byte per-envelope trailer" are indistinguishable.  v141 reads
      the tail two ways itself -- ``parse_target_pos_vital`` (v141:2991)
      takes ``moving`` and stops, while ``parse_v141_refresh_target_pos``
      (v141:3010) takes ``moving`` and then a value it NAMES
      ``derived_mask`` and requires to be 0 -- and
      ``damage_model_hypothesis`` reads a derived change mask AFTER its
      vital loop, i.e. as an envelope trailer.  The 156-byte arithmetic
      below does not break the tie either: it is invariant under moving two
      bytes out of the last body into a trailer, so it is the same check,
      not a third one.  [pf-adversary D6, round mvtiw5.]

      WHAT THIS PROJECT DOES ABOUT IT, since it cannot be settled from
      committed artifacts: 24 is used, and the consequence of being wrong is
      made LOUD instead of being argued.  If the trailer reading is right,
      every frame where TargetPos is not last misparses -- and misparsing
      lands in ``unknown_vital_id``/``truncated_vital``, which this module
      now reports by name to the console and the events trail rather than
      swallowing.  An attended round therefore reads the answer off the
      console instead of trusting this comment.

  ``ACTION_VITAL`` 0x1AEA, body 64 bytes
      (a) ``action_ack.py:44-47`` slices exactly 64 bytes and refuses a short
          one.
      (b) ``legacy.parse_action_vital`` reports ``consumed_bytes == 64`` for
          the audited shape (asserted in ``action_ack.parse_scene006_ea7d``).

  ``PICKUP_REQUEST_VITAL_ID`` 0x4543, body 7 bytes
      (a) ``mob_pickup_request`` declares the codec as tag 0x14 + u32 then
          tag 0x08 + u8 = 5 + 2 = 7, from four byte-symmetric
          ``PF_SERIALIZER_FIELDS.tsv`` rows over serializer span
          [0x005E5E30, 0x005E5E83).
      (b) ``mob_pickup_request._decode_by_tag_walk`` refuses any body with a
          byte left over after those two records, and R303 decoded 4 of these
          bodies off the live wire.

  THE ARITHMETIC CHECKS ITSELF.  Frame #714 is 156 bytes.  Outer header
  3 + 5 + 2 + 2 + 3 = 15, each vital header 3 + 2 = 5, so
  15 + 4*(5+23) + (5+24) = 15 + 112 + 29 = 156.  The table reproduces a
  measured frame length exactly; that is why this file ships with four rows
  and not with a scan.

NONCLAIMS -- read before using one symbol from here.

  1. THE TABLE IS FOUR IDS LONG AND THE CLIENT HAS MORE -- 46 of the 49 ids
     in ``legacy.NAMES`` stop the walk, and one of them,
     ``UPDATE_SERVER_SETTING_VITAL`` 0x0F01, is in v141's own
     ``CAPTURE_NOISE_IDS`` (v141:3128), i.e. an id v141 itself classes as one
     the client sends continuously.  A frame carrying an untabled id is
     refused as a whole and keeps TODAY'S behaviour exactly: v141 reads the
     first vital and the tail stays invisible, which is what happens now.
     THE MODULE cannot therefore make a frame worse than main.  THAT IS A
     CLAIM ABOUT THE MODULE AND NOT ABOUT ITS CALL SITES, and the difference
     was measured, not reasoned: a first draft of the runtime wiring did make
     one frame shape worse than main (a leading TargetPos batched with a
     pickup click lost its position entirely, because the pickup branch
     claims the frame and returns above ``super().dispatch``).  A call site
     that consumes a walk has to check what it is taking the frame AWAY from.
     [pf-adversary D1/D3, round mvtiw5.]
  2. THIS MODULE GRANTS NOTHING.  It classifies bytes.  Whether an isolated
     vital may take an object, move a player or write a row is decided by
     the lane that consumes it, with its own guards, unchanged.
  3. THE ISOLATED PARSE IS NOT THE FRAME.  ``raw_pc`` on an isolated vital
     is that vital's own bytes, NOT the whole packet, and ``vital_count`` is
     1 by construction.  A consumer that compares ``raw_pc`` against a
     whole-frame constant (v141 does this for the v139 login marker) will
     correctly not match.  Do not use an isolated parse to answer a question
     about the frame it came from.
  4. WHICH POSITION THE PICKUP VITAL ARRIVES IN IS UNRESOLVED.  ka1-A's
     prose says the request "usually arrives as vital 2..5"; the refusal
     token actually counted 42 times, ``vital_count_not_one``, can only be
     produced when the pickup vital is FIRST (the runtime branch keys on
     ``parsed.nested_id``).  The two readings disagree and this module does
     not settle it -- it handles both, because ``isolate_vital`` searches
     every position including the first.  "Handles both" is now driven by a
     test per reading at the dispatcher, not asserted here: the claim was
     made once before it was true.
  5. A WRONG LENGTH IS NOT AN UNKNOWN ID, AND ONLY THE SECOND IS CAUGHT.
     Fail-closed here means "an id whose length is not declared stops the
     walk".  A row that is DECLARED but WRONG produces a clean, accepted
     walk whose boundaries are in the wrong places -- the bytes one vital
     hands a lane would then come from its neighbour.  Nothing in this
     module detects that; the byte-reconstruction test and the 156-byte
     arithmetic constrain the rows but cannot prove one.  See the
     TARGET_POS_VITAL row above for the one row where this is a live
     question.  And the reach is bounded: ``raw_pc`` is one frame from one
     connection, so the worst case is one player's own frame misread, never
     another connection's bytes.
"""
from dataclasses import dataclass
from typing import Any

WALKED = "walked"

# Bounds the work one unauthenticated frame can ask for.  The largest count
# ever observed is 5 (R303).  A frame over the cap is refused, which means
# today's behaviour, not a crash.
MAX_VITALS_PER_FRAME = 64

VITAL_WALK_PROMOTED_TOKEN = "VITAL_WALK_PROMOTED"
VITAL_WALK_REFUSED_TOKEN = "VITAL_WALK_REFUSED"

# Every refusal means: this frame is not walked, and the caller keeps the
# unwalked ``parsed`` it already had.  Registered so a reason can never be
# invented at a call site.
VITAL_WALK_REFUSAL_REASONS = (
    "parse_object_missing_fields",
    "parse_object_refused_to_answer",
    "legacy_module_missing_fields",
    "raw_pc_not_bytes",
    "not_a_runtime_protocol_req",
    "not_a_vital_collection",
    "vital_count_not_positive",
    "vital_count_too_large",
    "envelope_reread_disagrees",
    "unknown_vital_id",
    "truncated_vital",
    "trailing_bytes_after_last_vital",
)

_ENVELOPE_FIELDS = (
    "outer_id", "outer_version", "outer_mask", "vital_count",
    "nested_id", "nested_version", "nested_payload", "raw_pc",
)

# Vital ids are read off the legacy module by NAME rather than hard-coded,
# so a frozen-snapshot change cannot leave this table silently disagreeing
# with the decoders it feeds.  The pickup id is the one exception and it is
# imported from the lane that owns it, below.
_LENGTHS_BY_LEGACY_NAME = {
    "ON_LAND_VITAL": 23,
    "TARGET_POS_VITAL": 24,
    "ACTION_VITAL": 64,
}


def _pickup_vital_id():
    """The pickup id, from the lane that owns it -- never hand-typed here."""
    from .mob_pickup_request import PICKUP_REQUEST_VITAL_ID
    return PICKUP_REQUEST_VITAL_ID


def body_length_table(legacy: Any) -> dict:
    """id -> declared body length, built fresh from the modules that own it.

    Raises nothing the caller has to catch for wire reasons: a legacy module
    missing one of the names simply contributes no row, and a missing row
    stops the walk by name later.
    """
    table = {}
    for name, length in _LENGTHS_BY_LEGACY_NAME.items():
        vital_id = getattr(legacy, name, None)
        if type(vital_id) is int:
            table[vital_id] = length
    table[_pickup_vital_id()] = 7
    return table


@dataclass(frozen=True)
class VitalWalk:
    """One frame, walked or refused.  ``vitals`` is empty unless walked."""

    walked: bool
    reason: str
    vitals: tuple


def _isolated(legacy: Any, parsed: Any, vital_id: int, version: int,
              body: bytes, vital_bytes: bytes):
    """One nested vital, wearing the ordinary ParsedOuter the decoders take.

    The outer fields are copied from the frame it came out of so a decoder
    that checks the envelope (``parse_v141_refresh_target_pos`` does) sees
    the truth about the packet, with ONE deliberate exception: vital_count
    is 1, because this object carries exactly one vital and saying 5 would
    be a lie the pickup lane's own gate is right to refuse.

    ``raw_pc``/``nested_offset`` KEEP v141's OWN INVARIANT rather than a
    prettier one: v141 sets ``nested_offset`` to the offset of the nested
    HEADER (id + version, five bytes) and ``nested_payload`` to everything
    after it, so ``nested_payload == raw_pc[nested_offset + 5:]`` holds on a
    frame v141 parsed.  ``raw_pc`` here is this vital's own five header
    bytes plus its body and ``nested_offset`` is 0, so the same equation
    holds on an isolated parse.  A copy that carried the whole frame's
    offset with only the body's bytes would break it silently.
    """
    return legacy.ParsedOuter(
        outer_id=parsed.outer_id,
        outer_version=parsed.outer_version,
        outer_mask=parsed.outer_mask,
        vital_count=1,
        nested_id=vital_id,
        nested_version=version,
        nested_payload=body,
        nested_offset=0,
        raw_pc=vital_bytes,
    )


def walk_nested_vitals(legacy: Any, parsed: Any) -> VitalWalk:
    """Walk every nested vital of one frame, or refuse the whole frame.

    Never raises for wire reasons.  A refusal is always a registered name and
    always means "the caller keeps what it had", never "the frame is gone":
    this function is additive by construction and removes no behaviour from
    any path that calls it.
    """
    try:
        if not hasattr(legacy, "GSCN_RUNTIME_PROTOCOL_REQ"):
            return VitalWalk(False, "legacy_module_missing_fields", ())
        if not hasattr(legacy, "Cursor") or not hasattr(legacy, "ParsedOuter"):
            return VitalWalk(False, "legacy_module_missing_fields", ())
        for name in _ENVELOPE_FIELDS:
            # hasattr swallows only AttributeError; a property raising
            # anything else has to be caught by the outer guard, which is
            # why the whole read sits inside it (the shape mob_pickup_request
            # arrived at under an adversarial pass, same reasoning).
            if not hasattr(parsed, name):
                return VitalWalk(False, "parse_object_missing_fields", ())
        return _walk_fields(legacy, parsed)
    except Exception:
        return VitalWalk(False, "parse_object_refused_to_answer", ())


def _walk_fields(legacy: Any, parsed: Any) -> VitalWalk:
    raw = parsed.raw_pc
    if type(raw) is not bytes and type(raw) is not bytearray:
        return VitalWalk(False, "raw_pc_not_bytes", ())
    if parsed.outer_id != legacy.GSCN_RUNTIME_PROTOCOL_REQ:
        return VitalWalk(False, "not_a_runtime_protocol_req", ())
    if not (parsed.outer_mask & 0x02):
        return VitalWalk(False, "not_a_vital_collection", ())
    if type(parsed.vital_count) is not int or parsed.vital_count < 1:
        return VitalWalk(False, "vital_count_not_positive", ())
    if parsed.vital_count > MAX_VITALS_PER_FRAME:
        return VitalWalk(False, "vital_count_too_large", ())

    table = body_length_table(legacy)
    cursor = legacy.Cursor(bytes(raw))
    try:
        # THE SECOND, INDEPENDENT READ OF THE ENVELOPE.  The walk cannot
        # trust the offsets in ``parsed`` -- it has to re-derive where the
        # vital collection starts -- so it re-reads the header off the raw
        # bytes and then requires the two readings to agree.  A frame where
        # they disagree is not walked at all rather than walked from a
        # position one of the two readers did not mean.
        outer_id = cursor.u16(0x12)
        cursor.u32(0x14)
        outer_version = cursor.u8(0x08)
        outer_mask = cursor.u8(0x0B)
        vital_count = cursor.u16(0x12)
    except Exception:
        return VitalWalk(False, "truncated_vital", ())
    if (outer_id != parsed.outer_id
            or outer_version != parsed.outer_version
            or outer_mask != parsed.outer_mask
            or vital_count != parsed.vital_count):
        return VitalWalk(False, "envelope_reread_disagrees", ())

    vitals = []
    for _index in range(vital_count):
        header_start = cursor.p
        try:
            vital_id = cursor.u16(0x12)
            version = cursor.u8(0x0B)
        except Exception:
            return VitalWalk(False, "truncated_vital", ())
        length = table.get(vital_id)
        if length is None:
            # THE FAIL-CLOSED LINE THIS WHOLE FILE IS BUILT AROUND.  No
            # guess, no scan, no partial answer: an id whose body length is
            # not declared ends the walk and the frame keeps main's
            # behaviour.  Returning the vitals gathered so far would hand a
            # lane a body whose end was never established.
            return VitalWalk(False, "unknown_vital_id", ())
        start = cursor.p
        if cursor.remain() < length:
            return VitalWalk(False, "truncated_vital", ())
        body = bytes(raw[start:start + length])
        if len(body) != length:
            return VitalWalk(False, "truncated_vital", ())
        cursor.p += length
        vitals.append(_isolated(
            legacy, parsed, vital_id, version, body,
            bytes(raw[header_start:start + length]),
        ))
    if cursor.remain() != 0:
        # Bytes left over mean the table disagrees with the frame somewhere
        # in the middle, so no vital in it is trustworthy -- including the
        # ones that looked right.
        return VitalWalk(False, "trailing_bytes_after_last_vital", ())
    return VitalWalk(True, WALKED, tuple(vitals))


def isolate_last_vital(legacy: Any, parsed: Any, vital_id: int):
    """Return the LAST vital of ``vital_id`` in this frame, or None.

    WHICH END MATTERS, AND IT IS NOT THE SAME ANSWER FOR EVERY CALLER.  A
    position is a report of where the player IS, so when one frame carries
    two of them the later one is the true one; taking the first records the
    older position and then range-checks against it, which is the R303
    freeze in miniature (pf-adversary, D8, measured:
    ``[TargetPos(1,1,1), OnLand, TargetPos(9999,9999,9999)]`` promoted
    (1,1,1)).  A pickup click is a discrete request rather than a report, so
    ``isolate_vital`` keeps taking the first.
    """
    walk = walk_nested_vitals(legacy, parsed)
    if not walk.walked:
        return None
    found = None
    for vital in walk.vitals:
        if vital.nested_id == vital_id:
            found = vital
    return found


def isolate_vital(legacy: Any, parsed: Any, vital_id: int):
    """Return the FIRST vital of ``vital_id`` in this frame, or None.

    THE CONTRACT CALL SITES DEPEND ON, stated once here so no branch has to
    restate it: this returns something a lane can read only when the whole
    frame walked cleanly.  It never returns a half-read frame, and a None
    means "no change from main", never "the frame was consumed".

    The single-vital fast path returns the caller's own ``parsed`` object
    unchanged rather than a rebuilt copy, so a frame that works on main
    today goes down exactly the path it goes down today, byte for byte.
    """
    try:
        if parsed.vital_count == 1 and parsed.nested_id == vital_id:
            return parsed
    except Exception:
        return None
    walk = walk_nested_vitals(legacy, parsed)
    if not walk.walked:
        return None
    for vital in walk.vitals:
        if vital.nested_id == vital_id:
            return vital
    return None


def walk_refused_console_line(walk: VitalWalk, vital_count: Any) -> str:
    """One ASCII line for a frame this module would not walk."""
    return "%s reason=%s vital_count=%s" % (
        VITAL_WALK_REFUSED_TOKEN, walk.reason, vital_count)


def walk_promoted_console_line(vital_id: int, vital_count: Any) -> str:
    """One ASCII line for a vital a lane could not have read on main.

    Printed by the CALL SITE, not by the walk: the walk runs on every inbound
    frame a moving player sends and a line per frame would bury the console
    the owner reads.  A line here means a lane actually consumed a vital that
    main's parser would have left invisible.
    """
    return "%s vital=0x%04X vital_count=%s" % (
        VITAL_WALK_PROMOTED_TOKEN, vital_id, vital_count)
