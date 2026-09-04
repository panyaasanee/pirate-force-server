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
import os

from . import attr_wire
from .. import persistence_typed_attrs

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
    """~~The ONE frame COO-ORDER 1641 approved: x=7 alone, no merge, no
    cache.~~  THIS FUNCTION NO LONGER PRODUCES A FRAME.  It refuses, by
    name, every call -- `COO-DECISION 20260904_0345` item 2, answering this
    lane's own alarm `20260904_0309`.

    ~~STILL A LIVE COMPOSER AFTER `COO-DECISION 20260904_0215`~~ -- struck,
    not deleted (house rule: strike history, never erase it).  That reading
    was true for one round and is now withdrawn at the source: COO chose
    option (kh) of the alarm -- `PF_SPEED_TRIAL` goes UNDER (b''), it is not
    a scoped risk held outside it -- and withdrew his own 2026-09-03 06:46
    approval of the escape hatch, because that approval predates `RE-222`
    (2026-09-03 21:49).

    WHY THERE IS NO "SAFE VALUE" LEFT TO SEND.  `RE-222` Q0 (SHA-pinned)
    says the client applies `0x309A` as a full-object copy whose constructor
    zeroes every field before decode.  The damage therefore does NOT depend
    on the number in x=7 at all -- it is the 54 rows this frame did not
    carry.  `GT-218` measured it on a real client in one frame: HP `0/1`,
    cash `0`.  Picking a "safe" speed on a half block is picking which
    number rides along with the zeroing, so this door closes rather than
    narrows.

    WHAT REPLACES IT.  Nothing, yet, and that is deliberate: the full door
    (`attr_wire.build_named_field_update`, seeded through
    `attr_wire.live_full_block_values`) is the only shape allowed to carry
    a speed change now, and it refuses today because chief's two read points
    (`COO-DECISION 20260904_0216`) are not both on main.  So an owner who
    arms `PF_SPEED_TRIAL` today gets a REFUSAL, never silent -- but said
    PRECISELY rather than the way an earlier draft of this paragraph and of
    `pirate-force-server#700`'s own PR body first put it (pf-adversary,
    round `tof9cw`, measured; correction recorded in `pf_bridge#1067`):
    no `0x309A` byte ever leaves (that half held), but
    `chat_command_action._speed_denied` composes and sends one LocalTalk
    "SPEED DENIED" notice frame -- which IS bytes, just never the attr
    frame -- and the console prints TWO lines for that route, not one:
    `GM_CHAT_NOTICE_SENT` (the notice going out) followed by
    `GM_CHAT_NO_BYTES_SENT ... why=speed_persist_compose_refused_
    SpeedWireError` (the attr frame that did not).  `GT-218` is not delayed
    BY this: it was already waiting on chief's read points (see `NOW.md`).

    DEFENCE IN DEPTH, NOT THE WALL.  The wall is
    `attr_wire.make_update_attr_frame`, which refuses any block that is not
    login-shaped (`COO-DECISION 20260904_0345` item 1 put the wall there;
    `COO-DECISION 20260904_0545` item 1/2 changed the SET it enforces from
    all 55 rows to the rows production login itself sets bits for) -- this
    function's `{7: value}` would raise there either way: one row is not the
    login shape any more than it was the full table.  The raise here is the earlier, better-named half of the same
    answer; a reader who deletes one still hits the other.

    Raises `SpeedWireError` unconditionally.  The value checks below still
    run FIRST and keep their own words, so a caller passing rubbish is told
    it passed rubbish rather than being told the door is shut -- the two
    facts send an operator to two different places, the same split
    `attr_wire.live_named_values` keeps between `absent` and `unsendable`.
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
    raise SpeedWireError(
        "sparse /speed frames are closed: a one-row 0x309A block zeroes every "
        "other row on the client (RE-222 Q0; GT-218 measured HP 0/1 and cash 0 "
        "in one frame), so no value is safe on this shape -- COO-DECISION "
        "20260904_0345 item 2. A speed change now goes through "
        "gm/login_mask.build_login_shaped_frame on a login-shaped block "
        "(COO-DECISION 20260904_0545 item 1/2), which needs chief's read "
        "points first"
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

# ---------------------------------------------------------------------------
# RE-222 (2026-09-03, `pf_bridge/notes_to_chief/20260903_2149_RE-222-RESULT-
# PARTIAL-updateattr-and-name-color-gates.md`, static-only, SHA-pinned):
# THE "LANE-RE'S WORK" ASKED FOR ABOVE HAS A PARTIAL ANSWER NOW.
# ---------------------------------------------------------------------------
# Two of the three open questions the "WHY A HOLD AND NOT A FIX" comment
# above named are answered, from the client image directly rather than from
# a client's reaction:
#
#   * The container is NOT malformed.  RE-222 Q0 decodes the exact 30-byte
#     nested `ActorAttr` body this door's GT-218 send carried (a DIFFERENT
#     attended send than GT-193's, `/speed 400` not `/speed 300`, same
#     shape) byte-for-byte against the disassembled generic reader at
#     `[0x00463DE0,0x00463FA2)`: tag/length framing is structurally valid,
#     `0x12AD` is the `checksum("ActorAttr") & 0xFFFF` crosswalk (not a
#     tag-order error), and the `0x0040` bit this module sets is a BasicAttr
#     presence-mask bit, exactly where `attr_wire.FIELDS[6]` says it is.  So
#     "whether a body with the section omitted is even parseable" is
#     answered: it parses; that was never the failure.
#   * "Whether the client treats a zero ActorAttr mask as change-nothing or
#     zero-everything" is answered too, and the answer is neither reading:
#     the apply path at `ActorAttr::full copy [0x00464F30,0x004652AC)`
#     overwrites the WHOLE resident object -- inherited BasicAttr AND every
#     ActorAttr member -- from a freshly constructed incoming object,
#     unconditionally, regardless of which presence-mask bits that incoming
#     object set. The fresh object's own constructors
#     (`[0x00464A80,0x00464B3D)` for BasicAttr, `[0x00464BE0,0x00464E39)`
#     for ActorAttr) zero HP/MP and cash BEFORE the wire decode ever touches
#     them, so any field this door's send does not carry is not "left
#     unchanged" and not "zeroed by the client's parser" either -- it is
#     copied from a constructor default that was already zero.  This is the
#     SAME full-copy-not-merge mechanism `attr_wire.py`'s own module
#     docstring has cited since R281 as "a read of the v141 client apply
#     routine at 0x464F30" -- RE-222 is that citation upgraded from an
#     unverified note to an independently-derived, SHA-pinned static result
#     naming the exact same address.
#
# WHAT IS STILL NOT ANSWERED, AND WHY THIS DOES NOT REOPEN ANYTHING.  RE-222
# is static-only (its own nonclaims section says so): no game/server boot,
# no client-observable measurement, no byte sent.  It cannot and does not
# clear a shape -- `SHAPES_CLEARED_BY_A_REAL_CLIENT` above is the only thing
# that can, and only an attended round can add to it.  It also does not
# supply the "both sections carrying the character's real current values"
# baseline this comment block already named as the missing piece: RE-222
# decoded what one sparse send looked like, it did not answer where a
# COMPLETE current BasicAttr/ActorAttr snapshot -- HP/MP current+max, cash,
# and every other `known=True` row `attr_wire.FIELDS` lists -- would come
# from at the point a chat command dispatches.  `attr_wire.py`'s own
# CORE-REQUEST-GM-044 already answered NEGATIVE on the one candidate source
# this lane had found (`characters.actor_wire` is a `CreateActorDataEx`
# BLOB, i.e. `AvatarAttr`, not this DBAttribute collection --
# `pf_bridge/notes_to_chief/consumed/20260831_1810_CHIEF-REPLY-GM-044-
# actor-wire-blob-is-AvatarAttr-not-ActorAttr-BasicAttr-does-not-match.md`),
# so a safe full-object `/speed` send still needs a live runtime-side
# reader for the character's current named-field values.  ~~a
# CORE-REQUEST-shaped ask this lane has not filed yet, because nothing has
# asked this lane to build that door~~ -- struck 2026-09-04 round `tof9cw`
# (`CHIEF-TO-LANE-GM 20260904_0305` calls this the fourth false sentence):
# the ask WAS filed and answered.  `COO-DECISION 20260904_0047` item 1
# ordered it, chief landed `lane_hooks.current_named_attr_values` in
# `server#695` covering 4 of 26 rows, and `COO-DECISION 20260904_0216`
# ordered the second (login-byte) point, which does not exist yet.  So the
# blocker is no longer "nobody asked" -- it is 22 named rows and 29 login
# bytes, counted in `attr_wire.live_named_values`' own refusal string.
# Both locks below (`SPEED_LOGIN_READ_LANDED`, `SHAPES_CLEARED_BY_A_REAL_
# CLIENT`) are UNCHANGED by this section -- nothing here is a green light.
RE_222_STATIC_CONFIRMATION = (
    "pf_bridge/notes_to_chief/consumed/20260903_2149_RE-222-RESULT-PARTIAL-"
    "updateattr-and-name-color-gates.md"
)

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


# THE SECOND LOCK, AND IT IS OUTSIDE THE SHAPE QUESTION ENTIRELY --
# COO-DECISION 2026-09-02T18:47+07:00 (`pf_bridge/notes_to_chief/
# 20260902_1847_COO-DECISION-lane-gm-stop-sending-speed-as-an-attr-frame-
# now.md`): "`/speed <value>` must not put `LANE_GM_CHAT_SPEED_UPDATE_ATTR_
# VITAL` on the wire again UNTIL THE LOGIN-READ OF `speed_walk` IS ON
# `main`", and the route answers with a printed `SPEED DEFERRED` instead.
#
# WHY IT IS A SECOND LOCK RATHER THAN A WIDER SHAPE HOLD.  The two gates
# answer different questions and neither implies the other:
#
#   * `SHAPES_CLEARED_BY_A_REAL_CLIENT` above asks "has a real client been
#     measured accepting THIS shape?"  It is about the bytes.
#   * this one asks "does the number the client would paint survive the next
#     login?"  It is about the DATABASE, and it is the half `GT-193` measured
#     from the other side: `persistence_attr_compose.py:289` composes a
#     hardcoded `400.0` at login because ~~`speed_walk` has no login read
#     yet~~ (LANE-DB owns the fix -- COO-DECISION `20260902_1846`, NOT this
#     lane).  STRUCK, NOT DELETED, by LANE-GM round `gj77z5`: LANE-DB LANDED
#     IT (PR #605, `session.py:192` -> `login_speed.resolve_for_character` ->
#     `player_wire.py:266`).  So this gate's stated rationale -- "does the
#     number the client would paint survive the next login?" -- now answers
#     YES, and the flip condition spelled out below ("one line, here, by the
#     round that can point at the login read ON `main`") is met on the
#     evidence.  IT IS STILL NOT FLIPPED HERE, and deliberately: COO `2147`
#     point 3 forbids opening either lock "until the attended round that
#     deliberately tries a safe `/speed` value has happened and has a result",
#     and `GT-218` -- that round's own ticket, in `pf_bridge/
#     GAME_TEST_QUEUE.md` -- will not boot until both locks are already open.
#     The two rules close a loop that only the COO can cut, and round
#     `gj77z5` asked for that cut rather than guessing at it (letter
#     `20260903_0529`).  A lane flipping this on its own reading is exactly
#     what the "name your evidence in the comment" rule below exists to stop.
#     A door that painted a number the next login silently discards is a door
#     that lies to a tester even on a shape a client accepts.
#
# So a round that measures a safe shape STILL does not reopen the wire, and
# the round that lands the login read STILL does not either.  Both edits are
# required, they are owned by two different lanes, and that is on purpose:
# whichever lane moves first cannot cost an attended round by moving alone.
#
# HOW IT IS FLIPPED, said plainly so nobody flips it by accident: one line,
# here, by the round that can point at the login read ON `main` -- the same
# "name your evidence in the comment" rule the clearance set above states.
# It is deliberately NOT auto-detected from LANE-DB's module: a heuristic
# that guesses "the login read looks landed" and guesses wrong reopens the
# exact door that locked a real client out of an attended round, and this
# lane does not guess (`COO-DECISION 1847`: "do not guess which field killed
# the client and then fix your guess").
SPEED_LOGIN_READ_LANDED: bool = False


def send_deferred() -> bool:
    """Is every `/speed` frame held, whatever its shape? -- COO `1847`.

    Read through a function for the reason `shape_cleared()` and
    `shared_vital_version_confirmed()` are: the gate re-reads the module
    attribute live, so the round that flips the constant above edits one line
    and no call site.

    FAIL-CLOSED BY CONSTRUCTION: the deferral is the DEFAULT and the landing
    is what has to be proven, so a module half-edited by a later round holds
    the frame rather than sends it.
    """
    return not SPEED_LOGIN_READ_LANDED


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


# ---------------------------------------------------------------------------
# THE RUNTIME TRIAL GATE -- COO-DECISION 2026-09-03T06:46+07:00, ITEM 2
# ---------------------------------------------------------------------------
# `pf_bridge/notes_to_chief/20260903_0646_COO-DECISION-lane-gm-the-row-keeps-
# being-written-and-the-trial-opens-at-runtime-not-on-main.md`, answering this
# lane's letter `20260903_0529`, cuts a loop the two locks above had closed on
# themselves: `GT-218` -- the attended round whose whole purpose is to try ONE
# deliberately-safe `/speed` value -- cannot boot until both locks are open,
# and `COO 2147` point 3 forbids opening either lock until that round has
# happened and has a result.  Neither side can move first.
#
# THE CUT, IN THE COO'S OWN WORDS: "ไม่มีล็อกไหนถูกเปิดบน `main` ทั้งสองคงค่าเดิม
# -- ทางเปิดคือ **เกต runtime** รูปเดียวกับ `PFGM_FORCE=1`".  So:
#
#   * `SPEED_LOGIN_READ_LANDED` stays `False` and
#     `SHAPES_CLEARED_BY_A_REAL_CLIENT` stays empty.  NOTHING in this section
#     edits either.  A checkout of `main` with no environment variable set
#     behaves EXACTLY as it did before this section existed -- that is the
#     property `tests/test_gm_speed_trial_gate.py` pins first, because it is
#     the one `COO 2147` point 3 is actually about ("ประตูห้ามเปิดตอนเจ้าของไม่อยู่",
#     not "there may be no way to open it").
#   * `PF_SPEED_TRIAL=<one value>` in the PROCESS environment admits `/speed
#     <that one value>` and nothing else.  Every other value stays held by
#     both locks.  The person who opens the door is therefore the owner, in
#     her own session, in the minute she is watching, and the door closes by
#     itself when the process dies.
#
# FAIL-CLOSED IN THE SAME SHAPE `PFGM_FORCE` USES, and the shape matters more
# than the mechanism: `PFGM_FORCE` accepts the single string `1` and treats
# every other spelling -- unset, empty, `true`, `yes`, `01` -- as "not
# forced".  Here the accepted spelling is a NUMBER rather than a fixed word,
# so "one value" has to mean one f32, not one string: see `trial_opening`.
SPEED_TRIAL_ENV = "PF_SPEED_TRIAL"

# The three states the environment can be in, spelled as constants because an
# attended tester greps them off a cp874 console and a test names the same
# strings.  ASCII, no spaces, for the reason every console token in this lane
# is (`chat_command_action.SPEED_DEFERRED_CONSOLE_TOKEN`'s own comment).
TRIAL_UNSET = "unset"
TRIAL_MALFORMED = "malformed"
TRIAL_ARMED = "armed"


def _as_f32_or_none(value: object) -> float | None:
    """`value` as the f32 the wire would carry, or `None` if it is not one.

    Read through `persistence_typed_attrs.as_f32` rather than re-spelling the
    `struct.pack("<f", ...)` round trip here: the number this gate compares
    against is the number the DB row holds, and that module is what rounds it
    on the way in.  A second copy of the round trip is how a gate and a row
    start disagreeing about whether `400.1` is `400.1` -- the exact drift
    that function's own docstring exists to stop.

    `bool` is refused even though it is an `int` subclass, the same rule
    `compose_sparse_speed_update` states above: `PF_SPEED_TRIAL=True` is not a
    speed and must not silently become `1.0`.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        if not math.isfinite(float(value)):
            return None
        return persistence_typed_attrs.as_f32(float(value))
    except Exception:  # noqa: BLE001 - a gate never raises into dispatch
        # `OverflowError` for a double past F32_MAX is the measured case; the
        # bare catch is the posture, not a guess about which one it will be.
        return None


def trial_opening(environ=None) -> tuple[str, float | None]:
    """Which ONE value the runtime trial gate opens the door for, if any.

    Returns `(TRIAL_UNSET, None)`, `(TRIAL_MALFORMED, None)` or
    `(TRIAL_ARMED, <the f32 it admits>)`.  Never raises: a hostile or exotic
    mapping is a malformed environment, not an exception on the dispatch path
    -- the same posture `shape_cleared` and `send_deferred` take, and the
    reason both of those are functions rather than imported constants.

    THE VALUE IS NORMALISED THROUGH `_as_f32_or_none` BEFORE IT IS RETURNED,
    which is what makes "one value" well defined.  `PF_SPEED_TRIAL=450`,
    `=450.0` and `=4.5e2` all arm the SAME f32 and therefore admit the same
    `/speed`; `=400.1` arms `400.1000061035156`, which is what the row will
    hold after `persistence_typed_attrs.validate` rounds it, so the gate and
    the row agree by construction rather than by luck.

    MALFORMED IS NOT ARMED, and that is the fail-closed half: an owner who
    typed `PF_SPEED_TRIAL=fast` gets today's behaviour (every frame held) and
    a console field that says `malformed`, never an open door for some value
    she did not choose.
    """
    try:
        source = os.environ if environ is None else environ
        raw = source.get(SPEED_TRIAL_ENV)
    except Exception:  # noqa: BLE001 - see the docstring
        return (TRIAL_MALFORMED, None)
    if raw is None:
        return (TRIAL_UNSET, None)
    if not isinstance(raw, str):
        return (TRIAL_MALFORMED, None)
    if raw.strip() == "":
        # An empty or whitespace-only variable is the shell's own way of
        # saying "not set" (`set PF_SPEED_TRIAL=` on the bridge's cmd.exe
        # leaves an empty string, not an absent key), so it reads as UNSET
        # rather than MALFORMED -- the operator who cleared it did the right
        # thing and must not see a word that says she made a mistake.
        return (TRIAL_UNSET, None)
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        return (TRIAL_MALFORMED, None)
    admitted = _as_f32_or_none(parsed)
    if admitted is None:
        return (TRIAL_MALFORMED, None)
    return (TRIAL_ARMED, admitted)


def trial_admits(value: object, environ=None) -> bool:
    """Does the trial gate admit THIS `/speed` value?  Default: no.

    `False` for every value while the variable is unset or malformed, and for
    every value but the armed one while it is armed.  Never raises, for the
    reason `trial_opening` does not.

    COMPARED AS `repr()` OF TWO f32s, NOT WITH `==`, and the difference is one
    measured case rather than a style choice: `-0.0 == 0.0` is `True` in
    Python, so an `==` here would let `PF_SPEED_TRIAL=0` admit `/speed -0`.
    LANE-DB's round `vitdca` met that exact value from the other side (its PR
    title names the `-0.0` that refuted its own claim).  Two spellings of a
    number this lane never measured on a client are two values, and the
    stricter reading is the one that cannot cost an attended round.
    """
    reason, admitted = trial_opening(environ)
    if reason != TRIAL_ARMED or admitted is None:
        return False
    offered = _as_f32_or_none(value)
    if offered is None:
        return False
    return repr(offered) == repr(admitted)


def trial_console_field(environ=None) -> str:
    """What the console must say the trial gate is doing, in one ASCII word.

    `unset`, `malformed`, or `repr()` of the one f32 it admits.  COO `0646`
    item 2's fourth bullet: "บรรทัดคอนโซลต้องบอกว่าประตูเปิดให้ค่าไหน ผู้คุมจอต้อง
    อ่านออกโดยไม่ต้องเปิดซอร์ส" -- the operator must be able to tell an armed
    gate from an unarmed one, and an armed-for-450 gate from an armed-for-300
    one, WITHOUT opening a source file.

    NOTHING TYPED BY A CLIENT REACHES THIS STRING, which is why it is safe on
    the line: the two words are this lane's own constants and the third is
    `repr()` of a finite float, which cannot carry a space, a quote, an `=`,
    a newline or a non-ASCII byte.  The environment variable's RAW text is
    never echoed -- an owner who set `PF_SPEED_TRIAL=<something odd>` sees
    `malformed`, not her own string coming back at her through a console this
    lane promised to keep pure ASCII.
    """
    reason, admitted = trial_opening(environ)
    if reason == TRIAL_ARMED and admitted is not None:
        return repr(admitted)
    return reason
