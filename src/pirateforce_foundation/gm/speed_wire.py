"""LANE-GM: `/speed <value>` -> a SPARSE `UpdateAttrVital` (0x309A) frame,
field x=7 ONLY.

WHY THIS MODULE EXISTS AND WHY IT IS NOT `gm/attr_wire.build_named_field_update`
---------------------------------------------------------------------------
COO-ORDER 2026-09-01T16:41+07:00 (`pf_bridge/notes_to_chief/
20260901_1641_COO-ORDER-speed-sparse-x7-lane-gm-wire-chat-command.md`),
citing Panya's live session override of 2026-09-01T16:39+07:00 ("ส่งให้พอ
ใช้งานได้ก่อน อย่ารอ RE") and its paired order to LANE-DB
(`20260901_1640_COO-ORDER-speed-sparse-x7-approved-panya-live-override-of-
1447.md`), approves exactly ONE narrow door: an `UpdateAttrVital` send that
sets ONLY the BasicAttr mask bit for field x=7 (offset +0x54, f32) -- never
any of the other 54 fields `attr_wire.FIELDS` describes -- and only against
the RUN-COPY DB of an attended GT test round, never canonical.

`attr_wire.build_named_field_update` is the WRONG function for this door,
on purpose, not by oversight. It requires:
  (a) `known=True` for the field. x=7 is not (`attr_wire.py:173`, still
      `False` -- confirmed from source, not hearsay, by LANE-DB's reply
      `notes_to_chief/20260901_1201_LANE-DB-REPLY-lane-gm-x7-known-gate-and-
      seed-source-plan.md`).
  (b) a per-connection `RawBlockCache` already seeded via
      `capture_initial()`, which MERGES the new field into the FULL current
      block before composing.
Both requirements exist to protect the FULL-BLOCK, every-named-field door
`attr_wire.py` is building toward (its own module docstring has the COO-
DECISION chain) -- neither is what a SPARSE, single-field, test-scoped send
needs. Routing this through that function would mean either (a) flipping
`known` for x=7, which COO-ORDER 1641 does NOT ask for and would silently
open x=7 to `attr_wire`'s general-purpose named-field API for every future
caller, not just this one -- or (b) inventing a captured baseline this lane
has no proven source for yet (`attr_wire.py`'s own "open part": question 2,
still unanswered per LANE-DB's `1201` reply).

So this module composes the ONE frame COO-ORDER 1641 actually asked for,
directly on top of `attr_wire.encode_block`/`make_update_attr_frame` --
which do NOT gate on `known` themselves, only `build_named_field_update`
does -- with no `values` dict ever reaching a caller: the one public entry
point below takes exactly one float and cannot be asked to touch any field
but x=7. `attr_wire.FIELDS` row 7 is NOT edited by this module; its `known`
stays `False`, and `attr_wire.build_named_field_update` keeps refusing x=7
exactly as before. This is a second, narrower door beside the first one,
not a widening of it.

WHAT x=7 IS, AND HOW SURE THIS LANE IS
-----------------------------------------
`attr_wire.FIELDS[6]` (x=7): BasicAttr, mask bit `0x0040`, offset `+0x54`,
tag `0x2A` (f32), name placeholder `basic_f32_54`, `known=False`, note
"unknown f32". LANE-DB's `1201` reply cross-references the client-side
codex table independently: `reference_codex_attr/
PF_ATTR_FIELD_SEMANTICS.tsv:53` names the SAME bit/offset/tag/kind row
`semantic_name=FightAttr_run_speed_formula_input`,
`structural_status=PROVEN_EXACT`, `semantic_status=PROVEN_EXACT`,
`default_value=400.0`. Two independently-derived sources (this lane's own
probe-measured `FIELDS` table, and the client-side codex disassembly) agree
on every comparable column, which is why COO approved naming this door
"speed" instead of leaving it `basic_f32_54` -- but NEITHER source is a
client-observable measurement of a send changing anything on a real
screen, and this module never claims one.
[สมมติของสาย GM - รอ RE-193 / GT ผลจริง]

WHAT THIS MODULE DOES NOT DO
-------------------------------
1. It does not send. `UpdateAttrVital` (0x309A)'s own vital_version byte has
   never been measured against a real client -- sparse or full -- and
   `attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED` is `None` for exactly
   that reason (see that module's own docstring; GT-101 already showed what
   an unproven version byte does to a real client: modal error, connection
   halted, socket closed). COO-ORDER 1641 approves WHICH FIELDS the sparse
   door may touch; it does not and cannot supply a byte nobody has measured
   -- that is a SEPARATE, still-open blocker. This module reads
   `attr_wire`'s constant at call time rather than defining a second number
   that could drift from it: the sparse send and the full-block send share
   one wire mechanism (0x309A) and therefore must share one version byte,
   whatever it turns out to be. See `shared_vital_version_confirmed()`.
2. It does not touch `runtime.py`. Composing bytes and putting them on a
   real socket are different lanes' work by this house's standing rule
   (chief's zone) -- see this round's CORE-REQUEST-GM letter for the call
   site chief is asked to add, once the version byte is proven and an
   identity source (`identity_lo`/`identity_hi` for the connected
   character) is available at that call site.
3. It does not read or write `attr_wire.RawBlockCache`. A sparse send is
   defined as "this one field, nothing merged from any prior state" --
   touching the cache here would silently turn it into a full-block send
   the moment a connection had one captured, which is exactly the door
   COO-ORDER 1641 did NOT open.
4. It does not accept a `values` dict, a field index, or any parameter that
   could route a caller to a field other than x=7. The scope is enforced by
   the function's SIGNATURE, not by a runtime check a future edit could
   loosen without anyone noticing.

CHAT COMMAND GRAMMAR
-----------------------
`gm/commands.py`'s `speed <value>` entry parses and audits through the
EXISTING generic `gm/chat_command.py` pipeline -- no change was needed
there. A GM typing `/speed 5.0` is authorized (GM-account gate first, same
as every other command), decoded, parsed and logged exactly like `/lv 10`
is today, entirely before this module is ever imported. `value` is required
finite by the grammar itself (`commands._require_number`, the same check
`/warp`'s x/y already use) -- a NaN/Inf never reaches this module's own
`parse_speed_value` at all, which re-applies the same rule for callers that
hold a `GmCommand` built some other way (the "regardless of source" posture
this lane's other wire modules already take).
"""
from __future__ import annotations

import math

from . import attr_wire

# The one field this whole module exists to touch. Not exported as a
# parameter anywhere below -- see module docstring point 4.
SPEED_FIELD_X = 7

# `attr_wire.BY_X[7][6]` today: "basic_f32_54". Read through the table
# rather than hardcoded, so a future round that renames the placeholder (or
# flips `known` for it) cannot leave this string silently stale.
SPEED_FIELD_NAME = attr_wire.BY_X[SPEED_FIELD_X][6]


class SpeedWireError(ValueError):
    """A `/speed` value cannot be turned into a sparse frame."""


def shared_vital_version_confirmed() -> int | None:
    """The vital_version byte this door must wait on -- see module docstring
    point 1. Read live from `attr_wire`, never copied, so proving the byte
    there (a future RE result) does not also require an edit here."""
    return attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED


def parse_speed_value(text: str) -> float:
    """Parse chat-typed text into the f32 this field's `kind` requires.

    Mirrors `commands._require_number` (finite float, no NaN/Inf) rather
    than importing that private helper: same rule, this module's own error
    type, so a caller holding a `GmCommand` from any source never has to
    catch `GmCommandParseError` to get a `SpeedWireError` reason instead.
    `commands.parse_gm_command` already applies the identical check at parse
    time; this function re-applies it for the "regardless of source" reason
    every wire module in this lane states for its own inputs.
    """
    if not isinstance(text, str):
        raise SpeedWireError(f"speed value must be a str, got {text!r}")
    try:
        value = float(text)
    except ValueError as error:
        raise SpeedWireError(
            f"speed value must be a number, got {text!r}"
        ) from error
    if not math.isfinite(value):
        raise SpeedWireError(f"speed value must be finite, got {text!r}")
    return value


def compose_sparse_speed_update(
    legacy, identity_lo: int, identity_hi: int, value: float,
) -> tuple[bytes, bytes]:
    """The ONE frame COO-ORDER 1641 approved: x=7 alone, no merge, no cache.

    Raises `SpeedWireError` for a non-finite or non-numeric `value`.
    Everything else -- `identity_lo`/`identity_hi` types, the f32 encode
    itself -- is `attr_wire.encode_block`'s own contract; this function does
    not re-validate what that one already guards, the same separation
    `attr_wire.make_update_attr_frame` keeps from its own caller.

    NOT gated on `shared_vital_version_confirmed()` here -- same posture as
    `attr_wire.make_update_attr_frame` itself and `teleport_wire`/
    `say_wire`'s pure builders: this is a byte composer, exercised freely by
    this module's own tests regardless of whether a real send is allowed
    today. The gate belongs at the one call site allowed to reach a real
    socket, which does not exist yet (module docstring point 2) -- a future
    caller in that position checks `shared_vital_version_confirmed()` is not
    `None` BEFORE calling this function, the same way `_say_action` checks
    `say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED` before
    `make_say_broadcast_frame`.

    `bool` is explicitly refused even though it is an `int` subclass in
    Python: `True`/`False` reaching a speed value would silently encode as
    `1.0`/`0.0`, which is never what a GM typing `/speed true` (a grammar
    error `commands.py` already refuses, but this function is called
    "regardless of source") could have meant.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SpeedWireError(f"speed value must be a number, got {value!r}")
    fvalue = float(value)
    if not math.isfinite(fvalue):
        raise SpeedWireError(f"speed value must be finite, got {value!r}")
    return attr_wire.make_update_attr_frame(
        legacy, identity_lo, identity_hi, {SPEED_FIELD_X: fvalue}
    )


# ---------------------------------------------------------------------------
# GT-193 [FAIL]: THE SHAPE THIS DOOR ACTUALLY SHIPPED TO A REAL CLIENT
# ---------------------------------------------------------------------------
# Attended round R303 (2026-09-02 16:10 -> 17:49 +07:00, owner at the keyboard,
# results letter `pf_bridge/notes_to_chief/20260902_1755_KA1A-R303-RESULTS-
# gt205-pass-gt193-fail-gt204-full-chain-pass-and-the-pickup-path-measured-end-
# to-end.md`) typed `/speed 300` on a real client for the first time.  What was
# measured, quoting the tester's own wire tally rather than paraphrasing it:
#
#   * `LANE_GM_CHAT_ACTION speed route=action` then `[G>]
#     LANE_GM_CHAT_SPEED_UPDATE_ATTR_VITAL (74 bytes)` -- this door's frame,
#     composed and sent;
#   * "the frame carried `00 00 96 43` = 300.0 followed by trailing zero
#     fields";
#   * the character immediately showed HP 0, money 0 AND DIED;
#   * after that frame: 426 inbound frames, ZERO of them non-heartbeat.  The
#     revive buttons produced no server traffic at all -- the client locked
#     ITSELF out, and the attended round lost the client until a re-login;
#   * the run DB was healthy afterwards (`characters.speed_walk = 300.0`,
#     hp 100/100): the damage was never persisted, so this is a CLIENT-SIDE
#     reaction to bytes this lane put on the wire, not a server state bug.
#
# WHAT THE TESTER DID NOT PROVE, IN HER OWN WORDS: "I did NOT prove the client
# death is caused by the trailing zero fields.  I proved the frame carries them
# and that the client died on receiving it."  So the constant below is NOT a
# root-cause claim and this module must never be read as making one.
#
# THE "TRAILING ZERO FIELDS", NAMED EXACTLY, FROM THIS CLONE'S OWN COMPOSER:
# `encode_block` always emits BOTH sections of the DBAttribute body -- a
# BasicAttr u16 mask followed by its set fields, then an ActorAttr u64 mask, a
# group-flag tag, and its set fields.  A door that sets one BasicAttr field and
# nothing else therefore announces an ActorAttr section that is EMPTY.
# Measured on this clone for `/speed 300.0`, with each object named -- the
# first draft called the 74 "the body" and pf-adversary measured that it is not
# (round `et2ux4`, D7): the DBAttribute BODY is 30 bytes, the composer's first
# return value (`pc`) is 63, and the FRAME the dispatcher counts, which the
# tester logged as `(74 bytes)`, is the second.  `pc` ends
# `... 12 40 00 2a 00 00 96 43 32 00 00 00 00 00 00 00 00 05 01 0b 00`, where
# the `32` tag plus eight zero bytes IS the ActorAttr mask, `05 01` is the
# group flag, and `0b 00` belongs to the outer envelope; `cash`
# (offset 0x0A8, mask 1<<11) is one of the fields that section carries.  Money
# went to 0 on the screen.  That correlation is why the hold below is keyed on
# the empty section rather than on the command name.
#
# WHY A HOLD AND NOT A FIX.  The safe shape is unknown and this lane may not
# guess it: whether the client treats a zero ActorAttr mask as "change nothing"
# or as "zero everything", and whether a body with the section OMITTED is even
# parseable, are questions about the client's deserializer -- LANE-RE's work,
# asked for in this round's letter to chief.  The one shape this lane could
# ship instead (both sections carrying the character's real current values)
# needs a captured baseline `attr_wire.RawBlockCache` still has no seed source
# for (that module's own open question 2).  Until one of those answers lands,
# the fail-closed reading of GT-193 is: do not put this shape in front of a
# tester again.  A refused `/speed` costs her one chat line; this shape cost
# her a dead character, a locked client and a re-login.
# [ASSUMPTION OF LANE-GM, AWAITING COO] -- this round's letter
# `20260902_1841_LANE-GM-ASK-COO-hold-the-speed-shape-that-locked-a-client.md`.
SPARSE_SHAPE_MEASURED_BY = "GT-193 attended round R303 2026-09-02"

SECTION_BASIC_ATTR = "basic_attr"
SECTION_ACTOR_ATTR = "actor_attr"

# THE CLEARANCE IS A SET OF SHAPES, NOT A BOOLEAN, and pf-adversary is the
# reason (round `et2ux4`, D6).  The first draft of this hold opened itself for
# ANY shape with both sections filled: `declared_empty_sections() == ()` was an
# independent opening path that never consulted the clearance at all.  His
# question is the one this module could not answer: GT-193 proved a frame with
# an empty ActorAttr section was sent and the client then died, and the tester
# wrote in the same letter that she did NOT prove the two are connected -- so
# "the section became non-empty" is not evidence about anything.  A lane that
# filled the section would have shipped a NEW, never-measured, ~90-byte shape
# to an attended tester while this file still said, a few lines up, that the
# safe shape is unknown and this lane may not guess it.
#
# So: every send needs a clearance, and the shape's own signature -- the tuple
# `declared_empty_sections` returns -- is the KEY.  An empty set means nothing
# has ever been cleared, which is where GT-193 leaves us.  A future round adds
# ONE entry with the measurement that earned it named in the comment above:
#   * `("actor_attr",)` if an attended round finds today's shape is fine after
#     all (the client death having been something else);
#   * `()` if a both-sections-filled shape is measured accepted.
# Adding an entry is a deliberate edit that names its evidence.  Filling the
# section is no longer a way around that.
SHAPES_CLEARED_BY_A_REAL_CLIENT: frozenset = frozenset()


def shape_cleared(sections) -> bool:
    """Has a real client been measured accepting THIS shape?

    Read through a function, never by importing the set into a caller's own
    namespace, for the same reason `shared_vital_version_confirmed()` exists:
    a future round that clears a shape edits ONE line here and every gate
    re-reads it live.  `None` -- a shape that could not be measured at all --
    is never cleared, whatever the set contains.
    """
    if sections is None:
        return False
    return tuple(sections) in SHAPES_CLEARED_BY_A_REAL_CLIENT


def declared_empty_sections(
    legacy, identity_lo: int, identity_hi: int, value: float,
) -> tuple[str, ...]:
    """Which DBAttribute sections this door ANNOUNCES WITH NOTHING IN THEM.

    This tuple is the SIGNATURE the clearance set above is keyed on.  Today a
    `/speed` send always returns `("actor_attr",)`, because `SPEED_FIELD_X` is
    a BasicAttr field and this door sets no other field; a door that carried an
    ActorAttr value as well would return `()`.  Neither is cleared today.

    WHAT IT MEASURES, SAID EXACTLY, BECAUSE THE FIRST DRAFT OVERSTATED IT
    (pf-adversary, round `et2ux4`, D5).  It composes through `encode_block` and
    reads the masks off the composer's own return value -- so it measures the
    SHAPE this door builds, not the individual frame one particular call will
    send.  The shape does not depend on the identity or on the value, and that
    is pinned by `tests/test_gm_speed_shape_hold.py::
    TheShapeDoesNotDependOnIdentityOrValueTests`.  That pin is what makes it
    legitimate for `_speed_action` to check the shape BEFORE the store
    read-back its shipped frame is actually composed from.  A future round that
    adds a field whose presence depends on the value turns that pin red, and
    the check has to move below the read-back.
    """
    # The value is passed THROUGH, not coerced: a caller whose value the
    # encoder would refuse must see that refusal here rather than have it
    # papered over by a `float()` this function invented.
    _body, basic_mask, actor_mask = attr_wire.encode_block(
        legacy, identity_lo, identity_hi, {SPEED_FIELD_X: value}
    )
    empty = []
    if not basic_mask:
        empty.append(SECTION_BASIC_ATTR)
    if not actor_mask:
        empty.append(SECTION_ACTOR_ATTR)
    return tuple(empty)
