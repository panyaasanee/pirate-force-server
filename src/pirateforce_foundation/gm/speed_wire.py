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
