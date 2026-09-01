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

CALL SITE (CORE-REQUEST-GM-043, chief CHIEF-REPLY 2026-08-31T03:57+07:00,
option A): `gm/chat_command_action.py`'s `_gmprobe_action` is now the mid-
session way to fire any one of these variants -- `/gmprobe <variant_id>`,
looked up via `VARIANTS_BY_ID`/`variant_by_id` below. This does not change
the nonclaim above one bit: composing and sending a frame through a chat
command is still not evidence that anything renders; it only removes the
"only one hardcoded value, only once at login" limit `GT-164` was BLOCKED
on (pf_bridge notes_to_chief 20260831_0321).

GT-164 RESULT LANDED (2026-08-31, pf_bridge notes_to_chief
20260831_0901_GT164-RESULT-bounded-negative-on-suspect-2-plus-field-0x0b-
second-is-the-button-visibility-switch.md): attended click sweep across all
14 variants above -- NONE opened `GMUI_BASIC` (the nonclaim above still
holds in full: this module has still never been shown, by itself, to open
that window). Incidentally, the sweep gave the first ATTENDED confirmation
that `field_0x0b_second` (already known from static RE, RE-089/RE-104,
CORE-REQUEST-020) gates `BT_GM` VISIBILITY specifically, mid-session, via
`/gmprobe` and not only the one hardcoded login frame -- 14/14, no
exception, client re-draws with no relog. See `observed_button_visible` /
`guaranteed_visible_variant_ids` / `guaranteed_hidden_variant_ids` below.
Visibility is still not click-success: do not read those helpers as
answering any of the four suspects.

CODEX EVIDENCE ADDED (2026-09-01, pf_bridge notes_to_chief
20260901_0344_CODEX-CORRECTION-GM-EVIDENCE-BOUNDARY.md, the authoritative
version replacing its own two earlier drafts 0254/0321 -- this module reads
only the 0344 text, since those two are explicitly withdrawn by it): a fifth
question, not wire-constructible either, has surfaced from Codex's static RE
of the client's `GameMaster.dll` loader path -- see
`GM_PLUGIN_MODEL_KEY_SUSPECT` below. This is NOT a resolution of any of the
four suspects above and does not change `SUSPECT_STUBS`' "three input
suspects, one outcome suspect" shape claim -- it is a fifth, separate
question about which on-disk `.model` resource the click's downstream
factory would even find, sitting upstream of all four. Read that stub's own
`why_not_wired_this_round` before citing it anywhere: Codex's own letter
hedges this as a "PROPOSED compatible binding", explicitly NOT a proven
original-DLL return value.
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
# variant_id lookup -- the seam CORE-REQUEST-GM-043's `/gmprobe <variant_id>`
# chat command (gm/chat_command_action.py::_gmprobe_action) reads.
# ---------------------------------------------------------------------------

# Built once, at import time, from the same generator every other reader of
# this module uses -- so this table and `iter_state_vital_bit_variants` can
# never drift apart into two different lists of "the variants that exist".
VARIANTS_BY_ID: dict[str, StateVitalBitVariant] = {
    variant.variant_id: variant for variant in iter_state_vital_bit_variants()
}


def known_variant_ids() -> tuple[str, ...]:
    """The `variant_id` values `/gmprobe` accepts, in generator order."""
    return tuple(VARIANTS_BY_ID)


def observed_button_visible(variant: StateVitalBitVariant) -> bool:
    """Does GT-164's attended evidence say `BT_GM` is drawn for this variant?

    `field_0x0b_second` was already known, pre-`RE-164`, to gate `BT_GM`
    VISIBILITY at login time -- RE-089/RE-104 traced wire `+0x15==1` to that
    effect, and `CORE-REQUEST-020` flipped the one hardcoded login send to
    `field_0x0b_second=1` on that basis (`GT-107-R3`,
    `notes_to_chief/20260827_2014_CHIEF-REPLY-CORE-REQUEST-020-bt-gm-field-
    wired.md`). What `GT-164` (`pf_bridge/notes_to_chief/
    20260831_0901_GT164-RESULT-bounded-negative-on-suspect-2-plus-field-0x0b-
    second-is-the-button-visibility-switch.md`) adds is NOT a new field --
    it is the first ATTENDED, client-observable confirmation of the same
    rule, fired mid-session through `/gmprobe` (not only the one hardcoded
    login frame), across all 14 named variants, with the button re-drawing
    live with no relog: `field_0x0b_second == 1` -> button shown, 14/14, no
    exception; `field_0x0b_first` and `field_0x14` (bits 0-7, and the
    all-ones boundary) had zero observed effect on visibility either way.

    NONCLAIM (read before calling this anywhere): "visible" is not "click
    works". GT-164's OWN headline result is that none of these 14 variants
    made a click open `GMUI_BASIC` -- see the module docstring's four
    suspects and `SUSPECT_STUBS`. This predicate exists so an attended
    tester chasing suspects 1/3 (connection-context, current-UI object-key)
    can pick a variant that GUARANTEES the button is on-screen first,
    instead of re-deriving that from scratch or tripping over it hidden by
    accident -- it says nothing about what happens after the click.
    """
    return variant.field_0x0b_second == 1


def guaranteed_visible_variant_ids() -> tuple[str, ...]:
    """`variant_id`s that GT-164 attended-confirmed draw `BT_GM` visibly.

    Generator order, per `observed_button_visible` above. Use this to pick a
    known-visible variant before an attended suspect-1/3 capture, rather
    than guessing or repeating GT-164's own sweep.
    """
    return tuple(
        v.variant_id for v in iter_state_vital_bit_variants() if observed_button_visible(v)
    )


def guaranteed_hidden_variant_ids() -> tuple[str, ...]:
    """`variant_id`s that GT-164 attended-confirmed hide `BT_GM`.

    The complement of `guaranteed_visible_variant_ids`, useful for setting up
    a "button starts hidden" precondition (e.g. to re-observe the live
    re-render GT-164 reported, without relogging) the same explicit way.
    """
    return tuple(
        v.variant_id for v in iter_state_vital_bit_variants() if not observed_button_visible(v)
    )


def variant_by_id(variant_id: str) -> StateVitalBitVariant | None:
    """The named variant, or None if `variant_id` matches none of them.

    Wired for CORE-REQUEST-GM-043's `/gmprobe <variant_id>` (chief
    CHIEF-REPLY 2026-08-31T03:57+07:00, option A): this is the one place
    that turns operator-typed text into one of
    `iter_state_vital_bit_variants`'s named combinations, so the chat action
    and any future caller cannot disagree about which string maps to which
    fields.

    Returns `None` rather than raising -- an unknown id is the GM's typo,
    not this module's error, and the caller decides how to report it
    (`_gmprobe_action` refuses by name, never guesses the closest match).
    `variant_id` is accepted "regardless of source" the same way
    `gm/commands.py`'s `GmCommand.args` is (see `GmCommandArgsError`'s
    docstring): a non-`str` key cannot be in this dict (every key is a
    literal from `iter_state_vital_bit_variants`), but `dict.get` on an
    unhashable value raises `TypeError` instead of returning `None`, so the
    type is checked first rather than trusted.
    """
    if not isinstance(variant_id, str):
        return None
    return VARIANTS_BY_ID.get(variant_id)


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

GM_PLUGIN_MODEL_KEY_SUSPECT = SuspectHypothesisStub(
    suspect_id="gm-plugin-model-key",
    question=(
        "Codex's static RE of the `GameMaster.dll` / `CreateGameMaster` loader "
        "path (pf_bridge notes_to_chief 20260901_0344) found direct-call slot "
        "+0x04 consumed as a GUI model basename composing "
        "`.\\Data\\GUI\\Model\\<key>.model`, and that the client's 534-file "
        ".model corpus has NO `GMUI_BASIC.model` under any case variant -- but "
        "`GMUI.project` declares a `GMUI_1` entry whose own `.model` has root "
        "`GMUI_1` with child `GMUI_BASIC`. Is `L\"GMUI_1\"` the key this slot "
        "actually resolves to at runtime (making `GMUI_BASIC` reachable only "
        "as a child/tab of that panel), or is the true original-DLL return "
        "value something this corpus scan has not found at all?"
    ),
    why_not_wired_this_round=(
        "this is a client-side resource-name resolution question inside a "
        "DLL loader this lane's server code never runs or calls -- no vital "
        "payload this module can compose varies which .model basename the "
        "client resolves, so there is no frame variant to add. Codex's own "
        "letter is explicit that `GMUI_1` is a 'PROPOSED compatible binding', "
        "reconstructed from which .model file exists on disk, not a proven "
        "original DLL return value -- and that the three artifact files "
        "backing this claim (`external/pf_rederive_gm_plugin_gate.py`, "
        "`PF_GM_PLUGIN_GATE.tsv`, `PF_GM_PLUGIN_GATE.md`) are local-only, "
        "git-ignored on the machine Codex ran on, and not yet packaged for "
        "other clones (this session's clone included) to read directly -- "
        "so this stub is deliberately bounded to what the letter's own prose "
        "states, nothing pulled from the unavailable artifacts themselves. "
        "Runtime acceptance (does opening a `GMUI_1` panel actually reach a "
        "`GMUI_BASIC` tab, does it shut down clean) is explicitly still owed "
        "and is an attended, client-observable question for RE-164/a future "
        "GT entry -- not something this stub or any code in this file proves. "
        "UPDATE 2026-09-01 (pf_bridge notes_to_chief "
        "20260901_0934_CODEX-CHECKPOINT-GM-COLOR-DROP-SECOND.md, consumed by "
        "chief round 632iyt, no action mandated -- read here only to keep "
        "this stub's own facts current): the same checkpoint adds an "
        "implementation-contract detail for `CreateGameMaster` itself -- "
        "exact undecorated export name, x86 vtable slot `+0x00` (not only "
        "`+0x04`), calling convention/stack cleanup, and MSVCR90 "
        "scalar-delete allocator compatibility -- and warns that getting "
        "the export decoration, `+0x00` slot, or allocator wrong 'may "
        "crash'. That is a DIFFERENT question from the `.model` basename "
        "question this stub asks (it is about the DLL's own export/vtable "
        "contract, not which GUI resource its result names), it is native "
        "`GameMaster.dll` authoring which this Python server repo neither "
        "builds nor loads, and it does not change this stub's own "
        "conclusion: still no vital-payload frame variant to add here. "
        "Recorded so a future native-side attempt does not have to "
        "re-derive it, not because this lane is acting on it now."
    ),
)

SUSPECT_STUBS: tuple[SuspectHypothesisStub, ...] = (
    CONNECTION_CONTEXT_SUSPECT,
    QUERY_GATE_VALUE_AT_CLICK_TIME_SUSPECT,
    CURRENT_UI_OBJECT_KEY_SUSPECT,
    GM_PLUGIN_MODEL_KEY_SUSPECT,
)


__all__ = [
    "HYPOTHESIS_LABEL",
    "StateVitalBitVariant",
    "iter_state_vital_bit_variants",
    "build_variant_frame",
    "build_variant_payload",
    "observed_button_visible",
    "guaranteed_visible_variant_ids",
    "guaranteed_hidden_variant_ids",
    "SuspectHypothesisStub",
    "CONNECTION_CONTEXT_SUSPECT",
    "QUERY_GATE_VALUE_AT_CLICK_TIME_SUSPECT",
    "CURRENT_UI_OBJECT_KEY_SUSPECT",
    "GM_PLUGIN_MODEL_KEY_SUSPECT",
    "SUSPECT_STUBS",
    "GM_UPDATE_GM_STATE_VITAL_ID",
    "VARIANTS_BY_ID",
    "known_variant_ids",
    "variant_by_id",
]
