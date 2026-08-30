"""BT_GM click experiment fork -- RE-164 (pf_bridge/CLIENT_RE_QUEUE.md).

# Why this module exists

`RE-126` (CLOSED PASS/DONE, pf_bridge notes_to_chief
20260828_1809_RE-126-RESULT-BT-GM-SAME-CONTROL.md) proved the `BT_GM` button
and its click dispatcher are the SAME object -- the "wrong-object binding"
hypothesis is dead. `GT-103` A/B (NO-RESULT, pf_bridge notes_to_chief
20260828_1140_GT103AB-RESULT-...) then falsified `RE-118`'s practical
conclusion ("current-UI key must be non-empty") across four UI states, all
silent. Static RE alone has now given one answer that a later click test
disproved (`RE-118`). Per the owner's 2026-08-31T01:52+07:00 standing order
(pf_bridge notes_to_chief
20260831_0152_PANYA-ORDER-LANE-GM-make-the-BT_GM-button-and-GMUI_BASIC-
window-actually-work.md), this round builds an experimental FORK instead of
reading more disassembly: construct labelled variants an attended tester can
fire one at a time, watching whether `GMUI_BASIC` opens, modelled on the
`PF_ADHOC_ATTR_PROBE` lane pattern (one variable flipped per attempt, human
eyes on the result, no guessed semantics shipped as fact).

Four suspects remain, named by RE-126 itself, none of them guessed at here:

1. connection context on the click handler
2. the query-`0x25` gate at `GMModule_Client+0x19` -- true at click-time, or
   only at draw-time?
3. the real current-UI object-key condition (RE-118's "must be non-empty"
   guess is falsified, the true condition is unknown)
4. whether factory `0x007280D0` (constructs `GMUI_BASIC`) is even reached

This module builds concrete, byte-verifiable WIRE variants for suspect area
2 (`iter_state_vital_bit_variants` / `build_variant_frame`, reusing
`gm.state_wire`'s proven frame layout unchanged -- no new tag/offset is
invented here). Suspects 1, 3 and 4 are NOT things a server-sent vital
payload can vary directly (they are client-side connection/UI-stack/call
state, or in runtime.py's wiring which is outside this lane's `gm/` write
zone) -- those three are recorded as labelled, parameterized hypothesis
STUBS (`SUSPECT_STUBS`) instead of guessed at.

NONCLAIM (read before citing this module anywhere): nothing here has been
sent to a live client. No function in this file proves, or claims to prove,
that any variant opens `GMUI_BASIC`. Whether the window opens is a
client-observable fact only an attended click test can produce -- see
pf_bridge GAME_TEST_QUEUE.md's paired GT entry and RE-164 itself. This
module's job is to make that click test cheap to run and its inputs
byte-auditable, nothing more.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from .state_wire import (
    GM_UPDATE_GM_STATE_VITAL_ID,
    GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED,
    make_gm_update_state_frame,
    make_gm_update_state_payload,
)

HYPOTHESIS_LABEL = "[สมมติของสาย GM - รอ RE]"


# ---------------------------------------------------------------------------
# Suspect area 2: GM_UpdateGMStateVital field variants (wire-constructible)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateVitalBitVariant:
    """One field-combination of the pinned `GM_UpdateGMStateVital` payload.

    ``field_0x0b_first`` / ``field_0x0b_second`` are the two proven u8 tag-0x0B
    fields, ``field_0x14`` is the proven u32 tag-0x14 field -- see
    ``gm.state_wire`` for the byte-level provenance (span_sha256 pinned
    against `pf_bridge/external/PF_SERIALIZER_FIELDS.tsv`). This dataclass
    adds no new field and no new meaning: it only names combinations of the
    three ALREADY-PROVEN fields so an attended tester can fire them one at a
    time and a wire/DB log can cite ``variant_id`` instead of raw integers.
    """

    variant_id: str
    field_0x0b_first: int
    field_0x0b_second: int
    field_0x14: int
    note: str


def iter_state_vital_bit_variants() -> Iterator[StateVitalBitVariant]:
    """Yield one-field-at-a-time variants of the state-vital payload.

    Scope, stated explicitly rather than silently bounded: this covers the
    two u8 fields fully (each is normalized to exactly 1-or-0 per RE-089's
    traced compare at `0x00727B09-0x00727B0D` -- "only exact value 1
    survives; 2..255 collapse to 0" once copied into
    `GMModule_Client+0x18/+0x19`) and the u32 field's low 8 bits plus the
    all-ones boundary. RE-089 traced the u32 field too, but found the
    OPPOSITE shape from the two bytes: it is copied verbatim through two
    hops (`GMModule_Client+0x1C`, then the type-0x25 argument's `+0x18`)
    "without compare/switch/arithmetic in either traced span" (RE-089's own
    words) -- i.e. no collapse/normalization was found for it at all, not
    "unmeasured". That is exactly why a full 0-31 bit sweep is not
    self-evidently redundant here the way it would be for the two u8 fields
    -- RE-089 simply never traced the value past those two copy hops into
    whatever reads the type-0x25 argument, so this generator's 8-bit + max
    coverage is a deliberately bounded first slice, not a claim that higher
    bits are known to matter or known not to. Bits 8-31 of ``field_0x14``
    are NOT covered by this generator; that gap is named as open follow-up
    work in RE-164 and docs/GM_LANE.md, not hidden.

    Every value combination here is UNTESTED against a live client. This
    generator does not claim, and must never be cited as claiming, that any
    listed value is the "correct" GM-level/flag/gate value -- see the module
    docstring's nonclaim.
    """
    yield StateVitalBitVariant(
        "baseline-all-zero", 0, 0, 0,
        "control: every field zero, same shape every pre-order boot already sent silently",
    )
    yield StateVitalBitVariant(
        "first-byte-1", 1, 0, 0,
        "toggle field_0x0b_first only (RE-089's normalized-to-1 value)",
    )
    yield StateVitalBitVariant(
        "second-byte-1", 0, 1, 0,
        "toggle field_0x0b_second only (RE-089's normalized-to-1 value)",
    )
    yield StateVitalBitVariant(
        "both-bytes-1", 1, 1, 0,
        "both u8 fields at their only non-collapsing value simultaneously",
    )
    for bit in range(8):
        value = 1 << bit
        yield StateVitalBitVariant(
            f"u32-bit{bit}",
            0,
            0,
            value,
            f"field_0x14 = 1<<{bit} (0x{value:02X}) with both u8 fields at baseline zero",
        )
    yield StateVitalBitVariant(
        "u32-max", 0, 0, 0xFFFFFFFF,
        "field_0x14 boundary value -- rules out a simple magnitude/level-cap gate",
    )
    yield StateVitalBitVariant(
        "all-fields-1", 1, 1, 1,
        "every field at its smallest non-zero value simultaneously",
    )


def build_variant_frame(
    legacy,
    variant: StateVitalBitVariant,
    vital_version: int = GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED,
):
    """Build the full runtime-vital envelope for one variant.

    Thin pass-through to ``gm.state_wire.make_gm_update_state_frame`` --
    this function invents no new wire logic, it only lets a caller iterate
    ``StateVitalBitVariant`` records instead of unpacking each one by hand.
    ``vital_version`` defaults to the one value RE-105 proved survives the
    generic VitalData version check (0); it is still a parameter, not a
    hardcoded constant, so a caller investigating suspect 2 differently is
    not blocked from passing another value.
    """
    return make_gm_update_state_frame(
        legacy,
        vital_version,
        variant.field_0x0b_first,
        variant.field_0x0b_second,
        variant.field_0x14,
    )


def build_variant_payload(legacy, variant: StateVitalBitVariant) -> bytes:
    """Build just the 9-byte tagged field body (no envelope) for one variant."""
    return make_gm_update_state_payload(
        legacy,
        variant.field_0x0b_first,
        variant.field_0x0b_second,
        variant.field_0x14,
    )


# ---------------------------------------------------------------------------
# Suspects 1, 3, 4: NOT wire-constructible -- labelled hypothesis stubs only
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SuspectHypothesisStub:
    """A named, unanswered suspect from RE-126's own closing paragraph.

    This is deliberately NOT executable. It carries no frame, no field
    values, no guessed semantics -- only the question, why no code-level
    probe variant exists for it this round, and what would have to happen
    (RE static work, or a runtime.py CORE-REQUEST outside this lane's write
    zone) before it could gain one. Every instance is tagged with
    ``HYPOTHESIS_LABEL`` so a reader searching for that marker across the
    `gm/` tree finds this file's real scope, not an invented meaning.
    """

    suspect_id: str
    question: str
    why_not_wired_this_round: str
    label: str = HYPOTHESIS_LABEL


CONNECTION_CONTEXT_SUSPECT = SuspectHypothesisStub(
    suspect_id="connection-context",
    question=(
        "Does the click handler (0x0053B9B0, RE-126-confirmed same object as "
        "the BT_GM binder) see a connection context that actually matches the "
        "session the state vital was sent on -- or can the two disagree?"
    ),
    why_not_wired_this_round=(
        "connection/session wiring lives in runtime.py's server-side dispatch, "
        "outside this lane's gm/ write zone (see AGENTS.md); this lane cannot "
        "vary it via a vital payload. Needs either static RE of the handler's "
        "context read, or a CORE-REQUEST-GM-<nnn> letter to chief if a wiring "
        "change turns out to be required."
    ),
)

QUERY_GATE_VALUE_AT_CLICK_TIME_SUSPECT = SuspectHypothesisStub(
    suspect_id="query-0x25-gate-value-at-click-time",
    question=(
        "Query type 0x25 (adapter 0x00726D30, reads GMModule_Client+0x19) is "
        "known to gate whether BT_GM is drawn/enabled (RE-104). Does it still "
        "return true at the moment of the click, or only at draw/paint time -- "
        "i.e. can the button be visible but the gate have already flipped "
        "false by the time the click dispatches?"
    ),
    why_not_wired_this_round=(
        "this is a timing question about when the client re-reads the gate, "
        "not a value this lane's frame can set differently -- the frame "
        "variants above (iter_state_vital_bit_variants) exercise WHAT is "
        "written to GMModule_Client+0x18/+0x19/+0x1C, not WHEN the client "
        "re-checks it relative to a click. Answering this needs either a "
        "timed pair of sends (state vital immediately before vs. well before "
        "the click, both attended-observed) or static RE of 0x0053B9B0's own "
        "call to the query-0x25 adapter."
    ),
)

CURRENT_UI_OBJECT_KEY_SUSPECT = SuspectHypothesisStub(
    suspect_id="current-ui-object-key-condition",
    question=(
        "RE-118 guessed the current-UI object-key vfunc must return non-empty; "
        "GT-103 A/B measured four UI states (empty HUD / map open / bag open / "
        "bag closed-then-reclicked) and got silence in all four, falsifying "
        "that specific guess. What IS the real key condition, if any?"
    ),
    why_not_wired_this_round=(
        "GT-103 already exhausted the practical states this lane could name "
        "without new RE; a fifth guessed condition here would repeat exactly "
        "the mistake RE-118 made (naming a condition without disassembly "
        "backing). The order's own text is explicit that RE-118's failure "
        "mode must not be repeated -- so this suspect stays a labelled "
        "question for static RE-164, not a guessed frame variant."
    ),
)

SUSPECT_STUBS: tuple[SuspectHypothesisStub, ...] = (
    CONNECTION_CONTEXT_SUSPECT,
    QUERY_GATE_VALUE_AT_CLICK_TIME_SUSPECT,
    CURRENT_UI_OBJECT_KEY_SUSPECT,
)


__all__ = [
    "HYPOTHESIS_LABEL",
    "StateVitalBitVariant",
    "iter_state_vital_bit_variants",
    "build_variant_frame",
    "build_variant_payload",
    "SuspectHypothesisStub",
    "CONNECTION_CONTEXT_SUSPECT",
    "QUERY_GATE_VALUE_AT_CLICK_TIME_SUSPECT",
    "CURRENT_UI_OBJECT_KEY_SUSPECT",
    "SUSPECT_STUBS",
    "GM_UPDATE_GM_STATE_VITAL_ID",
]
