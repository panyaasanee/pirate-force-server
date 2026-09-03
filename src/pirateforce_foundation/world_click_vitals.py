"""LANE-A (WORLD): the two click vitals, given a declared length at last.

WHAT A PLAYER SEES BECAUSE OF THIS FILE, STATED HONESTLY AND FIRST.
Nothing today, and this module says so rather than implying otherwise: it
has no production caller, because the only branch that decides whether a
click reaches this lane is ``runtime.py``'s (chief's file).  What this file
IS, is the half that measurement said was missing, plus the two declared
lengths ``vital_walk`` needs before anybody -- this lane, LANE-B's pickup
rescue, LANE-GM's chat tail -- can read a frame that carries a click.
``CORE-REQUEST 20260903_1641`` is the two lines that make it live.

THE MEASUREMENT THIS FILE EXISTS FOR (round ``0zoxir``, driven through
``runtime.make_state_class`` itself, the real dispatcher, one logged-in
session in scene 1, clicking an identity the arrival census armed):

    frame shape                              replies   console
    -------------------------------------    -------   -------------------
    [TargetVital, ChooseNPC]                 3         REFUSED count=2
    [TargetVital, ChooseNPC, TargetPos]      3         REFUSED count=3
                                             and the position is LOST
    [TargetPos, TargetVital, ChooseNPC]      0         REFUSED count=3
    [TargetPos, ChooseNPC]                   0         REFUSED count=2

where "console" is one line, on every one of the four::

    VITAL_WALK_REFUSED reason=unknown_vital_id vital_count=<n>

    THE REPLY COUNTS ARE THIS SESSION'S, NOT A CONSTANT.  pf-adversary
    measured the same leading-click frame answering 3, then 2, then 2 on
    repeat clicks, and answering 0 for an identity the census never armed.
    What the rows above establish is the DIFFERENCE between the shapes on
    one session, not a number a later round may assert.

because ``vital_walk.body_length_table`` declares a body length for four
vital ids (``ON_LAND_VITAL`` 23, ``TARGET_POS_VITAL`` 24, ``ACTION_VITAL``
64, pickup 7) and NEITHER of the two the client sends when a player clicks
an actor.  An id with no declared length stops the walk by design
(``vital_walk._walk_fields``: "no guess, no scan, no partial answer"), so
today a frame that carries a click is not walked AT ALL -- not for this
lane's click, not for LANE-B's pickup, not for the position promotion that
R303 measured frozen.  The refusal is correct.  The missing row is this
lane's to supply: ``TARGET_VITAL``/``CHOOSE_NPC`` are the ids this lane's
thirteen ChooseNPC responders answer.

WHY THE SILENCE IS NOT THIS LANE'S TO CLOSE ALONE.  ``runtime.py``'s guard
reads ``parsed.nested_id`` -- the FIRST vital of the frame, which is all
``v141.parse_outer`` ever fills in -- so a click that is not first never
reaches ``lane_hooks.scene_choose_npc_responder`` and never reaches v141's
own frozen loop either (``v141:4396`` tests the same field).  Two lines in
files this lane does not own close it, and they are named in the letter.

    NOT MEASURED, AND SAID PLAINLY: whether the live client puts a click
    vital anywhere but first.  What IS measured is that the client batches
    (R303, ``vital_count = 5`` on real inbound traffic, pf_bridge letter
    ``20260902_1800`` -- that frame is four ``OnLand`` and one
    ``TargetPos``, it carries NO click id, and this file does not pretend
    otherwise), and that ``v141``'s own composer builds a click frame with
    a TRAILING ``TargetPosVital`` (``v141:6300-6315``).  "The click is
    second" is not measured, no claim in this file or its tests rests on
    it, and the row that matters -- the position thrown away -- does not
    need it.

WHERE THE TWO LENGTHS COME FROM -- READ THIS BEFORE CHANGING A NUMBER
====================================================================

HALF DERIVED, HALF TRANSCRIBED, AND THE HALVES ARE NAMED SEPARATELY -- a
first draft of this section said "derived, not typed" flatly and
pf-adversary refuted it with a runnable mutant: give ``v141``'s TargetVital
body a third field in BOTH its parser and its builder, and this module
still answers 11, with every test green.  What is DERIVED is each field's
width, from the frozen module's own tag helpers.  What is TRANSCRIBED is
WHICH tags, HOW MANY, and in WHAT ORDER -- and a schema change in ``v141``
would leave that transcription a fossil.  The transcription's sources:

  * ``TARGET_VITAL`` (0x1ADD): ``parse_target_vital`` reads ``raw8(0x32)``
    then ``u8(0x08)`` (``v141:3021-3028``), and ``v141``'s own frame builder
    writes exactly ``qwordtag(0x32, target_id) + u8tag(0x08, target_kind)``
    (``v141:6304-6307``).  Composed: 11 bytes.
  * ``CHOOSE_NPC`` (0x0FB6): ``parse_choose_npc`` reads one ``raw8(0x32)``
    -- its docstring names the serializer, "0x6C0180 writes exactly tag
    0x32 plus qword actor identity", V74/V90/V96 captures agreeing -- and
    the builder writes ``qwordtag(0x32, actor_id)`` (``v141:6309-6312``).
    Composed: 9 bytes.

THE COMPOSITION IS CHECKED AGAINST ROWS SOMEBODY ELSE DECLARED -- and that
control is narrower than it looks, so read what it does and does not say.
Composing ``ON_LAND_VITAL``'s and ``TARGET_POS_VITAL``'s bodies the same
way reproduces 23 and 24, the numbers ``vital_walk._LENGTHS_BY_LEGACY_NAME``
carries.  That establishes the tag helpers have the widths this file
assumes.  It does NOT check this file's field list: those two bodies are
composed of different tags (``f32tag``/``u16tag``) from the click bodies
(``qwordtag``/``u8tag``).  And ``vital_walk``'s own docstring (``:57-82``)
says in capitals that 24 has ONE source, not two -- the R303 capture cannot
separate a 24-byte body from a 22-byte body plus a two-byte envelope
trailer -- so the control reproduces a number its own owner has flagged as
live.  It is a sanity check, not a proof, and nothing here calls it one.

    A THIRD CLICK ID, LEFT UNDECLARED ON PURPOSE:
    ``CHOOSE_NPC_BY_TABLE_ID`` (0x3BFB), which ``v141`` names
    (``v141:402``) and never parses or builds.  A first draft said no
    artifact in either repository establishes its body; pf-adversary
    refuted that by opening the file this module's own letter cites --
    ``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv:1567`` carries one
    ``ALWAYS`` W row, tag ``0x14``, four bytes, which would make the body
    5.  So the honest statement is narrower: v141 neither reads nor writes
    it, no capture in either repository contains one, and declaring a row
    from the image layer ALONE would break this file's own two-layer rule.
    It stays undeclared, a frame carrying one still refuses by name, and
    the row is named here so the next round can ask for it deliberately.

WHAT THIS MODULE WALKS, AND WHY IT DOES NOT RE-IMPLEMENT THE WALKER
===================================================================

``read_click()`` borrows ``vital_walk``'s own declared table, adds the two
rows above, and walks the frame HERE -- see ``_walk_with_click_lengths``
for why it does not reach into that module to do it.  The two rows are
declared here rather than typed into LANE-E's file by this lane: when
``CORE-REQUEST 20260903_1641`` lands, ``body_length_table`` will hold them
for every caller and this module's own copy becomes a no-op it keeps only
so the file is readable on a deploy older than that request.  (LANE-B's
pickup id already reaches that table this way -- ``vital_walk``'s own
``_pickup_vital_id()`` imports it "from the lane that owns it, never
hand-typed here" -- so this is the established shape, applied to the two
ids this lane owns.)

Every answer is fail-closed and named.  An empty result NEVER means "the
frame was consumed"; it means "no change from main", exactly the contract
``vital_walk.isolate_vital`` states for ``None``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import vital_walk

# NO ``production_allowed`` FLAG HERE, AND THAT IS DELIBERATE.  A first
# draft carried ``production_allowed = True``; pf-adversary measured that
# NOTHING reads it (``lane_hooks.module_production_allowed`` resolves names
# under ``lane_hooks.`` only, and this module is not a hook), and flipping
# it to False left all 28 tests green.  LANE-B's aggro lane retired a bool
# of exactly that shape this same day (round ``1tz15e``, pirate-force-server
# ``#658``), on COO's rule that "a bool that RESTATES a fact is not a guard
# on it".  The fact it would have restated is in the sentence above: this
# module has no caller.
#
# THE MODULE THAT RULING CAME FROM IS NOT NAMED IN THIS FILE ON PURPOSE:
# its own lane pins an exact list of every file under ``src/`` that mentions
# it, and a citation from here moved that list -- measured, this round, as a
# red in another lane's suite.  The round and the PR number above locate it
# without standing in that census.
WALKED = "walked"

#: Printed once per connection the first time a click is recovered from a
#: frame ``main`` could not read.  A distinct token, not v141's: an attended
#: round has to be able to tell a click the frozen path answered from one
#: this walk rescued (the same reason ``vital_walk`` refused to borrow
#: v141's ``target_pos_`` event name).
CONSOLE_TOKEN = "LANE_A_CLICK_VITAL_RESCUED"

#: Printed when a frame that carries a click cannot be walked closed.
REFUSAL_TOKEN = "LANE_A_CLICK_VITAL_REFUSED"

#: Why a frame was not walked.  Every name here is ``vital_walk``'s own for
#: the same condition, except ``nested_offset_not_a_position`` and
#: ``envelope_payload_disagrees``, which name checks that module does not
#: need (it re-reads the envelope instead of trusting the parse object).
REFUSAL_NAMES = (
    "parse_object_refused_to_answer",
    "raw_pc_not_bytes",
    "not_a_runtime_protocol_req",
    "not_a_vital_collection",
    "vital_count_not_positive",
    "vital_count_too_large",
    "nested_offset_not_a_position",
    "envelope_payload_disagrees",
    "unknown_vital_id",
    "truncated_vital",
    "trailing_bytes_after_last_vital",
)

#: Every name a read of a frame can carry -- one of them is the success.
#: Registered here so a reason can never be invented at a call site
#: (``vital_walk.VITAL_WALK_REFUSAL_REASONS``' own convention).
READ_NAMES = (
    "read",
    "legacy_module_missing_click_ids",
    "no_click_vital_in_this_frame",
    "leading_click_is_mains_branch",
) + REFUSAL_NAMES


@dataclass(frozen=True)
class ClickRead:
    """One frame, read or refused.  ``identities`` is empty unless read.

    ONE OBJECT RATHER THAN TWO CALLS, and the reason is measured rather
    than stylistic: a first draft of this module had a separate
    ``refusal_reason()`` that walked the frame a SECOND time, and on a
    frame that DID name identities it answered
    ``no_click_vital_in_this_frame`` -- a reason that reads as a refusal
    for a frame that was read.  A caller logging that pair would have
    written a line contradicting its own answer.
    """

    identities: tuple
    reason: str


def _click_ids(legacy: Any) -> tuple[int, ...]:
    """The two ids this lane answers, read off the frozen module by NAME.

    Never hard-coded: a frozen-snapshot change that renumbered either id
    would otherwise leave this file silently disagreeing with the dispatcher
    it exists to feed.  An id the module does not declare as an ``int``
    contributes nothing, which is how a partially-loaded legacy module ends
    up refused by name rather than raising.
    """
    ids = []
    for name in ("TARGET_VITAL", "CHOOSE_NPC"):
        vital_id = getattr(legacy, name, None)
        if type(vital_id) is int:
            ids.append(vital_id)
    return tuple(ids)


def body_lengths(legacy: Any) -> dict:
    """id -> declared body length, COMPOSED from the frozen codec.

    Composed rather than typed, out of the same helpers ``v141``'s own frame
    builder uses and in the same field order its own parsers read back, so a
    change to the tag convention moves this table with it instead of leaving
    a fossil number behind.  A legacy module missing a helper or an id
    contributes no row, and a missing row stops the walk later -- refusal,
    never a guess.
    """
    lengths: dict = {}
    try:
        target_vital = getattr(legacy, "TARGET_VITAL", None)
        choose_npc = getattr(legacy, "CHOOSE_NPC", None)
        if type(target_vital) is int:
            # v141:3021-3028 reads raw8(0x32) then u8(0x08); v141:6304-6307
            # writes exactly those two fields, in that order.
            lengths[target_vital] = len(
                legacy.qwordtag(0x32, 0) + legacy.u8tag(0x08, 0))
        if type(choose_npc) is int:
            # v141:3031-3041 reads one raw8(0x32); v141:6309-6312 writes it.
            lengths[choose_npc] = len(legacy.qwordtag(0x32, 0))
    except Exception:
        # Same shape as ``vital_walk.walk_nested_vitals``' outer guard: a
        # legacy module whose helper raises contributes no rows at all
        # rather than half a table.
        return {}
    return lengths


def declared_lengths_for_the_walk(legacy: Any) -> dict:
    """``vital_walk``'s table plus the two rows this lane owns.

    The borrowed rows are never re-typed here: what LANE-E declares is what
    this returns, with two ids added.  When ``CORE-REQUEST 20260903_1641``
    lands, ``vital_walk`` holds them itself and this function returns a
    table identical to the one it borrowed -- deliberately still correct,
    not dead, so the file reads the same on both sides of that landing.
    """
    table = dict(vital_walk.body_length_table(legacy))
    table.update(body_lengths(legacy))
    return table


def leading_click_is_mains_branch(legacy: Any, parsed: Any) -> bool:
    """True when the frame LEADS with a click id, so main's branch SEES it.

    "SEES", not "answers", and the distinction is measured rather than
    pedantic.  ``runtime.py:8856`` and ``v141:4396`` both test
    ``parsed.nested_id``, so a leading click reaches their branches -- and
    both then apply conditions this module cannot evaluate: a
    ``production_allowed`` responder for the scene, an armed
    ``population_indices``, a marker latch.  pf-adversary drove a leading
    click naming an identity the census never armed and measured ZERO
    replies (round ``0zoxir``), so an earlier draft of this docstring, which
    said a leading click "is answered today", was false.

    What the True means for this module is only this: the frame is on
    main's path, so reading it here would make a second author for one
    frame -- the defect ``_vital_walk_promote_target_pos`` stands down to
    avoid.  Whether main then answers is main's business, and a caller that
    logs this reason must not report it as "answered".
    """
    try:
        return parsed.nested_id in _click_ids(legacy)
    except Exception:
        return False


def read_click(legacy: Any, parsed: Any) -> ClickRead:
    """Every ChooseNPC identity in the frame, in wire order, or a reason.

    Empty identities mean "no change from main" on every path -- a frame
    with no click in it, a frame main reads itself, a frame that would not
    walk closed.  It never means "the frame was consumed".

    WHY THIS GATHERS RATHER THAN ISOLATES.  ``vital_walk.isolate_vital``
    hands back ONE vital wearing a ``vital_count = 1`` envelope, and
    ``v141.extract_choose_npc_identities`` walks the tail of the vital it is
    given: handed an isolated ``TARGET_VITAL`` it returns ``[]``, because
    that vital's own body carries no identity (measured, round ``0zoxir``).
    A click frame names its actors across SEVERAL vitals, so the answer has
    to be gathered from the walk, one identity per ``CHOOSE_NPC`` vital, in
    the order the client sent them -- the order v141's own multi-select loop
    preserves (``v141:3043-3068``).
    """
    ids = _click_ids(legacy)
    if len(ids) != 2:
        return ClickRead((), "legacy_module_missing_click_ids")
    if leading_click_is_mains_branch(legacy, parsed):
        return ClickRead((), "leading_click_is_mains_branch")
    choose_npc = getattr(legacy, "CHOOSE_NPC", None)
    walk = _walk_with_click_lengths(legacy, parsed)
    if not walk.walked:
        return ClickRead((), walk.reason)
    found = []
    for vital in walk.vitals:
        if vital.nested_id != choose_npc:
            continue
        identity = _identity_of(legacy, vital)
        if identity is None:
            # A body that will not decode is dropped by name, and the rest
            # of the frame is still read: the "drop and say so" discipline
            # this lane's responders already use for an unresolvable
            # placement, rather than throwing the whole click away.
            continue
        found.append(identity)
    if not found:
        return ClickRead((), "no_click_vital_in_this_frame")
    return ClickRead(tuple(found), "read")


def rescued_console_line(identities: Any, vital_count: Any) -> str:
    """One ASCII line for a click ``main`` could not see.

    ASCII only and no field the caller has to escape: the bridge console is
    ``cp874`` and every other console line in this lane is held to the same
    rule.
    """
    return "%s identities=%s vital_count=%s" % (
        CONSOLE_TOKEN,
        ",".join("0x%X" % (identity,) for identity in tuple(identities))
        or "none",
        vital_count,
    )


def refused_console_line(reason: Any, vital_count: Any) -> str:
    """One ASCII line for a click frame this module would not read."""
    return "%s reason=%s vital_count=%s" % (
        REFUSAL_TOKEN, reason, vital_count)


def _identity_of(legacy: Any, vital: Any):
    """The actor identity out of ONE isolated ``CHOOSE_NPC`` vital.

    Read through the frozen parser rather than by unpacking bytes here, so
    the schema has exactly one reader in this repository and a change to it
    cannot leave this module reading a shape nothing else agrees with.
    """
    try:
        identity = legacy.parse_choose_npc(vital)
    except Exception:
        return None
    return identity if type(identity) is int else None


def _walk_with_click_lengths(legacy: Any, parsed: Any):
    """This frame's vitals, walked CLOSED, or a refusal by name.

    WHY THE WALK IS HERE AND NOT A CALL INTO ``vital_walk``.  That module
    reads its lengths from a table this lane may not edit
    (``_LENGTHS_BY_LEGACY_NAME``, LANE-E's file), and the two rows a click
    frame needs are not in it -- so on every frame this module cares about,
    ``walk_nested_vitals`` refuses by name and hands back nothing to read.
    Reaching in to patch that module's table for the duration of a call was
    the first draft and it is not shipped: the table is a module global and
    ``lane_hooks``' own docstring is explicit that a hook runs on "the
    listener thread for every other player", so a patch-and-restore around
    one frame is a window where another connection's walk reads this lane's
    table.  Rather than mutate another lane's module, this walks the frame
    here -- the shape LANE-GM's ``gm/chat_frame_tail.py`` already ships for
    the same reason, and its rule is kept: BORROW the declared lengths,
    never retype them.

    CLOSED MEANS CLOSED.  Five header bytes plus a DECLARED body length per
    vital, ``vital_count`` of them, landing exactly on the last byte of the
    frame.  An id with no declared length, a body that runs off the end, or
    one byte left over refuses the WHOLE frame -- no guess at a boundary, no
    partial answer, nothing handed back from a frame whose middle this table
    disagreed with.
    """
    try:
        raw = parsed.raw_pc
        if type(raw) is not bytes and type(raw) is not bytearray:
            return _refused("raw_pc_not_bytes")
        raw = bytes(raw)
        if parsed.outer_id != legacy.GSCN_RUNTIME_PROTOCOL_REQ:
            return _refused("not_a_runtime_protocol_req")
        if not (parsed.outer_mask & 0x02):
            return _refused("not_a_vital_collection")
        count = parsed.vital_count
        if type(count) is not int or count < 1:
            return _refused("vital_count_not_positive")
        if count > vital_walk.MAX_VITALS_PER_FRAME:
            return _refused("vital_count_too_large")
        start = parsed.nested_offset
        if type(start) is not int or not (0 <= start <= len(raw)):
            return _refused("nested_offset_not_a_position")
        # v141's OWN INVARIANT, checked rather than assumed: ``parse_outer``
        # sets ``nested_offset`` to the offset of the first nested HEADER
        # (id + version = five bytes) and ``nested_payload`` to everything
        # after it (``vital_walk._isolated`` states the same equation).  A
        # frame where the two disagree is not walked from a position its own
        # parser did not mean.
        #
        # AND IT DOES REAL WORK, on ONE input shape and only that one --
        # measured twice this round, both results recorded because the first
        # one was misleading.  Mutant "delete these two lines", frame with a
        # LYING OFFSET: all tests stayed green, because a lying offset walks
        # off the end and the closure check below refuses it anyway.  Mutant
        # "delete these two lines", frame with an HONEST offset and a
        # REPLACED payload (pf-adversary's input, round ``0zoxir``): the
        # walk RETURNED AN IDENTITY, and the unmutated module refuses it.
        # So this check is what stops a rebuilt ``ParsedOuter`` whose two
        # halves describe different frames, and the closed walk below is
        # what stops a bad offset.  Neither covers for the other.
        if bytes(parsed.nested_payload) != raw[start + 5:]:
            return _refused("envelope_payload_disagrees")
        table = declared_lengths_for_the_walk(legacy)
    except Exception:
        return _refused("parse_object_refused_to_answer")

    vitals = []
    cursor = start
    for _index in range(count):
        header_end = cursor + 5
        if header_end > len(raw):
            return _refused("truncated_vital")
        try:
            head = legacy.Cursor(raw[cursor:])
            vital_id = head.u16(0x12)
            version = head.u8(0x0B)
        except Exception:
            return _refused("truncated_vital")
        length = table.get(vital_id)
        if length is None:
            return _refused("unknown_vital_id")
        body_end = header_end + length
        if body_end > len(raw):
            return _refused("truncated_vital")
        vitals.append(_isolated_like_v141(
            legacy, parsed, vital_id, version,
            raw[header_end:body_end], raw[cursor:body_end]))
        cursor = body_end
    if cursor != len(raw):
        return _refused("trailing_bytes_after_last_vital")
    return vital_walk.VitalWalk(True, WALKED, tuple(vitals))


def _refused(reason: str):
    """One refusal, by a name from ``REFUSAL_NAMES`` and never invented.

    NINE CAUSES USED TO SHARE ONE NAME (``frame_not_walked``), and
    pf-adversary named the cost: the CORE-REQUEST this module exists to
    support rests on ``unknown_vital_id`` being DISTINGUISHABLE from a
    truncated body, and the first draft's reader could not tell them apart.
    The names here are ``vital_walk``'s own wherever the same condition
    exists there, so two walkers do not grow two vocabularies for one wire.
    """
    if reason not in REFUSAL_NAMES:  # pragma: no cover - a typo guard
        raise AssertionError("unregistered refusal name: %r" % (reason,))
    return vital_walk.VitalWalk(False, reason, ())


def _isolated_like_v141(legacy: Any, parsed: Any, vital_id: int,
                        version: int, body: bytes, vital_bytes: bytes):
    """One nested vital wearing the ordinary ``ParsedOuter`` decoders take.

    The field-for-field shape ``vital_walk._isolated`` documents, kept
    identical on purpose so an isolated vital from this module and one from
    that module are the same object to every decoder: outer fields copied
    from the frame it came out of, ``vital_count`` 1 because this object
    carries exactly one vital, ``nested_offset`` 0 and ``raw_pc`` this
    vital's own header plus body, so v141's ``nested_payload ==
    raw_pc[nested_offset + 5:]`` still holds on the copy.
    """
    return legacy.ParsedOuter(
        outer_id=parsed.outer_id,
        outer_version=parsed.outer_version,
        outer_mask=parsed.outer_mask,
        vital_count=1,
        nested_id=vital_id,
        nested_version=version,
        nested_payload=bytes(body),
        nested_offset=0,
        raw_pc=bytes(vital_bytes),
    )
