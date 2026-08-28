"""GROUND-LOOT-NAMEPROP-001: does the name-property selector reach the label?

WHY THIS MODULE EXISTS
----------------------
GROUND-LOOT-001 (HYP-PF-032) asked whether the client draws anything at all
for RuntimeRes derived change-mask bit 0x08.  That question is ANSWERED: the
attended run of 2026-08-25 (job 1135) measured a floating item name label --
the exact string "Red leaves Hammer" -- appearing on the ground at the
coordinate that lane sent, and living on screen for 0.2 to 0.4 s.

This module asks the NEXT question: the client picks that label's UI TEXT
PROPERTY from two element fields our shipped lane has never put on the wire.

  [STATIC, RE-067, closed 2026-08-25, verifier 54/54 on client image sha256
   9627211412ac60d50ad189ce5a629443ce928ec23a9f8d219dfb2b157028b623]
    * CREATE selects the text property at [0x005F47FE,0x005F4822) and UPDATE
      at [0x005F4D04,0x005F4D5D); both hand the chosen value to the setter
      0x005BACF0, whose only direct callers are those two sites.
    * The selection reads element +0x1B as a GATE: "cmp byte [element+0x1B],0"
      and, when it is zero, pushes the DEFAULT property 0x34.
    * When the gate is non-zero the selection reads element +0x1A as a signed
      INDEX, accepts only 1..6, and looks it up in dword [index*4+0x00F30EC4],
      which maps 1..6 -> 0x5D..0x62.  Out of range falls back to 0x34.
    * The element ctor at [0x005F82C0,0x005F83F9) leaves +0x1B = 0 and
      +0x1A = 1.  INDEX 1 IS THEREFORE THE CTOR DEFAULT, which is why this
      lane does not send it: gate=1,index=1 would be indistinguishable at the
      client from gate=1 with no index at all.
    * In the list codec [0x005F85B0,0x005F8869) sha256 ce0a58f7.. the dirty
      mask carries +0x1B under bit 0x08 and +0x1A under bit 0x20.

  [CORROBORATED INDEPENDENTLY] The field order and tags above are not taken
  on the letter's word: pf_bridge/external/PF_SERIALIZER_FIELDS.tsv pins the
  same write path in emission order -- mask (tag 0x0B) at +0x28, tag 0x14 at
  +0x14, tag 0x0F at +0x18, tag 0x05 at +0x1B, the position subcall with its
  three tag 0x2A f32, then tag 0x08 at +0x1A.  Gate BEFORE position, index
  AFTER it.

  [MEASURED, from the shipped lane's own constants] HYP-PF-032 sends element
  mask 0x12 = 0x10|0x02 -- position and the payload dword and nothing else.
  Neither 0x08 nor 0x20 has ever been on the wire, so every label this
  project has drawn was drawn with the DEFAULT property 0x34, and the colour
  an attended observer recorded is not one we chose.

  [PROPOSED -- this is the hypothesis] That setting the gate and the index
  changes the label's appearance on screen.

THE EXPERIMENT: A CONTROL AND A TREATMENT, NOT TWO TREATMENTS
-------------------------------------------------------------
The first draft of this lane sent two treatment frames carrying indices 1 and
6 at different coordinates, and an adversarial review killed it: THREE of its
four possible outcomes were unreadable.  Two labels the same colour could
mean the selector is ignored, or that two properties look alike, or that the
client dropped the wider element; no labels could mean the mask was rejected
or the points were off camera; one label could mean either.  There was no
control inside the round, and one attended session is all we get.

What this lane sends instead is ONE CONTROL and ONE TREATMENT at the SAME
coordinate:

    frame A  element mask 0x12  -- the already-proven shape, no selector
                                  fields at all, so the client falls to the
                                  default property 0x34
    frame B  element mask 0x3A  -- the same element plus the gate and the
                                  index, index 6 -> property 0x62

Everything else is held: the same payload dword (so the label TEXT is the
same string), the same x/y/z (so the same pixels, background and lighting),
the same trigger, the same session, the same camera.  The ONLY variable is
whether the two selector fields are present.  That makes every outcome
readable:

    both labels drawn, different appearance -> the selector reaches the label
    both labels drawn, same appearance      -> it does not, and the control
                                               proves the pipe was alive
    A drawn, B not drawn                    -> the client does not draw the
                                               wider element (~~"REJECTS ...
                                               the V43 question, answered for
                                               free"~~ STRUCK round kfs01z:
                                               V43 was about record COUNT on
                                               the mask-0x02 actor list, not
                                               element WIDTH here, and
                                               ErrorData=28317 named no cause
                                               at all -- see mob_loot.py:100)
    neither drawn                           -> the session or the geometry
                                               failed; discard, and NOT a
                                               negative about the selector

TIMING [OUR DESIGN, and it is a scheduler offset, not a wire guarantee]
-----------------------------------------------------------------------
The two frames carry delays 0.0 and 1.50.  READ THAT AS A DEADLINE OFFSET,
NOT AS "1.50 s apart on the wire".  The frozen sender walks the action list
accumulating an absolute deadline (v141 send loop): a zero-delay action does
not advance the deadline, so however LATE frame A is actually sent, that
lateness is subtracted from the gap frame B waits out.

  realized_gap ~= 1.50 - lateness(A)

There is a measured control for this in the project's own capture: on
2026-08-25 the sibling lane's pair carried delays 0.0 and 0.10 and landed
42 ms apart, because frame A was sent about 85 ms after its deadline.  At
that lateness this lane's realized gap is about 1.41-1.44 s.  NOTHING IN
THIS TREE MEASURES THE REALIZED GAP -- it is I/O time in the sender's loop,
and only the attended capture can measure it.  What the offset buys is
margin: the label's measured lifetime is 0.2-0.4 s with +/-0.1 s of edge
error, so even at three times the observed lateness the two labels cannot
overlap, and a video timestamp alone attributes each one.

That margin is the whole reason the offset is not 0.10.  The 2026-08-25
round's realized 42 ms left the observer unable to say which element the one
label she saw belonged to, and the gap also rules out a second confound: if
the client reads a count=1 collection as "here is the complete list", a
frame arriving 42 ms later could have DELETED the first element.

GEOMETRY [OUR DESIGN]
---------------------
Both elements sit at trigger + 30 on X, the trigger's own Y and Z.  Not two
offsets: the labels never coexist (0.4 s lifetime, ~1.4 s gap), so separate
positions would buy nothing and would cost the comparison its shared
background -- and +30 is the ONLY offset this project has ever seen a label
at.  Trigger-relative because absolute pins died once already, when the
character's persisted position drifted away from the V135 boot placement.

  [NOT MEASURED] That the label seen at +30 in job 1135 belonged to the +30
  element is an inference from its TEXT, which assumes the payload dword is
  the lookup key -- HYP-PF-032's standing nonclaim, supported at the static
  layer by RE-066 and not at the wire layer.  Nobody has measured where the
  camera frustum ends, either.

FAIL-CLOSED, AND NEVER SILENTLY
-------------------------------
The scenario file is a PERMISSION TOKEN, never a source of values.  The
composer re-asserts, per element, the pc and frame lengths and a sha256 over
the composed pc with its twelve coordinate payload bytes zeroed -- the
coordinates are the one legitimately per-run input, every other byte is
pinned -- and re-asserts the coordinate bytes against an f32 round-trip of
trigger+offset.  The two elements carry DIFFERENT masks and therefore
different lengths and different coordinate spans, so every one of those pins
is per-element.  It refuses, by name and before composing, an element whose
declared mask and written fields disagree, a gate of zero, an index outside
the client's 1..6 window, and an element count that does not match the
pinned templates.

NONCLAIMS
---------
* This is a TEXT PROPERTY, not a colour.  RE-067 pinned property ids, not a
  palette: 0x34 and 0x5D..0x62 could select font, size, style, alignment or
  a whole preset.  Nothing here may be joined to
  CONSTDATA_TH__FONT_COLOR.n_ID 1..57 -- RE-067 forbids that join by name,
  because the numbers merely look similar.  The lane is called NAMEPROP and
  not NAMECOLOR for exactly this reason.
* The join between the STATIC CREATE path and the CLIENT-OBSERVABLE floating
  label has never been made.  Two layers agreeing is consistency, not proof.
  If the label an observer sees is a different widget, this lane returns a
  negative for the wrong reason.
* The client has NEVER been shown element mask 0x3A.  A stream error or a
  dropped frame is a real outcome and a RESULT, not a failure.
* Bit 0x08 = "ground loot" is still UNPROVEN and the payload dword is still
  NOT claimed to be an item template id.  Both inherited whole from
  HYP-PF-032; nothing here weakens them.
* An appearance matching an old screenshot of the original server is NOT
  evidence the original server sent these bytes.  That server is closed and
  unrecoverable, and the reference images may be a different build or region.
* Nothing here touches the ACTOR name label.  RE-067's actor half closed
  bounded-negative and RE-068 is the open ticket; an item-side positive says
  nothing about it.
  [STALE as of pf_bridge/CLIENT_RE_QUEUE.md chief R167, 2026-08-25 ~19:0x
  +07:00, round dvxb6f] [MEASURED]: RE-068 is CLOSED (PASS-MIXED, actor half
  hit the same static ceiling as RE-067) - not open. See mob_death.py's
  full_roster_override docstring for the full RE-067/RE-068 citation
  trail. An item-side positive still says nothing about the actor label
  either way.
* The CREATE-selector half of this module's foundation is SINGLE-SOURCE and
  not checkable at HEAD: RE-067's verifier is not in version control, so no
  layer in this repository can re-derive 0x005F47FE, the gate compare, the
  1..6 range check, the 0x00F30EC4 table or the 0x005BACF0 setter.  Only the
  codec order and tags are independently corroborated, by
  pf_bridge/external/PF_SERIALIZER_FIELDS.tsv.
* production_baseline_behavior is untouched: with the scenario absent this
  module is never imported by the dispatch path and no branch consults it.

WHY THIS IS NOT A FOURTH VERSION OF HYP-PF-032 -- AND WHY THAT IS NOT
THE AUTHOR'S CALL
---------------------------------------------------------------------
HYP-PF-032 stands at 3 of 3 tracked versions with extension_approval_ref
null, and its stop_rule names "other element masks (0x04/0x08/0x20 fields
stay unsent)" as exactly the widening that would need a new version.  This
module therefore does not touch that lane by a byte.

  IT DOES NOT FOLLOW THAT A NEW ENTRY IS ALLOWED.  HYP-PF-029's expiry
  decision says a further widening needs "a new entry OR a scoped approval",
  which is what authorised HYP-PF-038.  HYP-PF-032's says "ANY FURTHER WIRE
  CHANGE TO THIS LANE NEEDS AN EXTENSION DECISION FROM THE OWNER FIRST" and
  contains no new-entry clause at all.  A separate lane on the SAME derived
  bit, through the SAME client parser 0x5F85B0, on the very element fields
  that stop_rule freezes, is a dependent version by every test available.
  So this lane MUST NOT be merged on the standing gameplay pre-approval.
  It is built, proven at the wire layer and pushed for review; the owner
  rules on whether it becomes a fourth tracked version of HYP-PF-032 with a
  scoped extension_approval_ref, stays a separate entry, or is retired.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any, Tuple


# PF-HYPOTHESIS-LEDGER: HYP-PF-039 active
GROUND_LOOT_NAMEPROP_CHECKPOINT = "GROUND-LOOT-NAMEPROP-001"
GROUND_LOOT_NAMEPROP_HYPOTHESIS_ID = "HYP-PF-039"
production_allowed = False

# The derived change-mask bit is the one HYP-PF-032 already exercises -- that
# is where the label lives.  What is new is the ELEMENT mask of the TREATMENT
# element: 0x02 dword | 0x08 gate(+0x1B) | 0x10 position | 0x20 index(+0x1A).
GROUND_LOOT_NAMEPROP_DERIVED_BIT = 0x08
GROUND_LOOT_NAMEPROP_CONTROL_MASK = 0x12    # the already-proven shape
GROUND_LOOT_NAMEPROP_TREATMENT_MASK = 0x3A  # control + gate + index

# The client accepts the index only in this range; outside it the selection
# falls back to the default property.  The lane refuses to compose an index
# the client would throw away, so a negative can never be explained by our
# own out-of-range value.
GROUND_LOOT_NAMEPROP_INDEX_MIN = 1
GROUND_LOOT_NAMEPROP_INDEX_MAX = 6

# The UI text property the client falls back to when the gate is zero.  The
# control element sends no gate, so this is what it is expected to select --
# recorded here as the thing the treatment is compared AGAINST, not as a
# claim about what the value means.
GROUND_LOOT_NAMEPROP_DEFAULT_PROPERTY = 0x34

# The scheduler DEADLINE OFFSET carried on the treatment frame.  Not a wire
# guarantee: see TIMING in the module docstring.  realized_gap is roughly
# this minus however late the control frame was actually sent, and nothing in
# this tree measures it.
GROUND_LOOT_NAMEPROP_TREATMENT_DELAY = 1.50
# The lateness measured on the sibling lane's 2026-08-25 pair, kept so the
# realized-gap estimate in the docstring can be re-derived rather than
# believed.
GROUND_LOOT_NAMEPROP_MEASURED_LATENESS = 0.085


@dataclass(frozen=True)
class NamePropElement:
    """One 0x5F85B0 element this lane may emit.

    ``property_gate`` and ``property_index`` are None on the control element
    and set on the treatment element; the mask must agree with that, and the
    composer refuses rather than trusts.
    """

    element_key: int          # +0x10, always on the wire (tag 0x14 u32)
    payload_dword: int        # +0x14, mask bit 0x02 (tag 0x14 u32)
    element_mask: int         # +0x28, the per-element dirty mask
    property_gate: Any        # +0x1B, mask bit 0x08 (tag 0x05 u8), or None
    property_index: Any       # +0x1A, mask bit 0x20 (tag 0x08 u8), or None
    x_offset: float           # added to the triggering TargetPos x
    delay: float              # scheduler deadline offset, NOT a wire gap


@dataclass(frozen=True)
class NamePropGeometry:
    """The pins that differ per element because the masks differ."""

    pc_size: int
    frame_size: int
    coord_spans: Tuple[Tuple[int, int], ...]
    pc_template_sha256: str
    frame_template_sha256: str


@dataclass(frozen=True)
class NamePropScenario:
    scenario_id: str
    hypothesis_id: str
    elements: Tuple[NamePropElement, ...]


# The control carries the shape HYP-PF-032 has already put on a screen; the
# treatment adds the two selector fields and NOTHING else.  Same dword, same
# offset, same trigger: the presence of the selector is the only variable.
_CONTROL = NamePropElement(
    element_key=3,
    payload_dword=2200423,
    element_mask=GROUND_LOOT_NAMEPROP_CONTROL_MASK,
    property_gate=None,
    property_index=None,
    x_offset=30.0,
    delay=0.0,
)
_TREATMENT = NamePropElement(
    element_key=4,
    payload_dword=2200423,
    element_mask=GROUND_LOOT_NAMEPROP_TREATMENT_MASK,
    property_gate=1,
    # Index 6 and not 1: 1 is the element ctor's own default for +0x1A, so
    # sending it would be indistinguishable at the client from sending no
    # index at all.  6 is the far end of the accepted window, which is the
    # most contrast the client's own table can give us against the default.
    property_index=6,
    x_offset=30.0,
    delay=GROUND_LOOT_NAMEPROP_TREATMENT_DELAY,
)

_NAMEPROP_PROBE = NamePropScenario(
    "ground_loot_nameprop_probe",
    GROUND_LOOT_NAMEPROP_HYPOTHESIS_ID,
    (_CONTROL, _TREATMENT),
)

# Masked-template pins, one per element, count=1 each.  The two elements
# carry different masks, so the sizes and the coordinate spans differ too --
# the control is the 44-byte shape HYP-PF-032 ships, the treatment is 48
# bytes because the gate and the index add two tagged bytes each.  The
# template sha256 is taken over the composed pc with its twelve coordinate
# payload bytes zeroed; the frame carries its own pin over the same spans
# shifted by the 10-byte snappy-literal header.
GROUND_LOOT_NAMEPROP_FRAME_COORD_SHIFT = 10
GROUND_LOOT_NAMEPROP_CONTROL_GEOMETRY = NamePropGeometry(
    pc_size=44,
    frame_size=54,
    coord_spans=((30, 34), (35, 39), (40, 44)),
    pc_template_sha256=(
        "8657614E33073F5C1969AA6CB1FEAA441E0A1ED011F38AD13B22270183B8E26D"
    ),
    frame_template_sha256=(
        "FB419334817234FFEA7A2A8A498E2C24DF7D223915783D5CBFBB87B2866BAD9D"
    ),
)
GROUND_LOOT_NAMEPROP_TREATMENT_GEOMETRY = NamePropGeometry(
    pc_size=48,
    frame_size=58,
    coord_spans=((32, 36), (37, 41), (42, 46)),
    pc_template_sha256=(
        "34E4D5B285258FD8BE929704195F2C704B6B25A03ECDDC9F41C2D8E42C115FF2"
    ),
    frame_template_sha256=(
        "A91392DDC1F092DDFE7F5897E2A38CAB9C7C93646BB06BA5248F5161578E1D07"
    ),
)
GROUND_LOOT_NAMEPROP_GEOMETRY = (
    GROUND_LOOT_NAMEPROP_CONTROL_GEOMETRY,
    GROUND_LOOT_NAMEPROP_TREATMENT_GEOMETRY,
)

GROUND_LOOT_NAMEPROP_LABELS = (
    "GROUND_LOOT_NAMEPROP_CONTROL_ONCE",
    "GROUND_LOOT_NAMEPROP_IDX6_ONCE",
)

_EXPECTED = {
    "schema": 1,
    "id": _NAMEPROP_PROBE.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _NAMEPROP_PROBE.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_only",
        "trigger": "first_target_pos_after_runtime_ack",
        "emission": (
            "one_control_and_one_treatment_single_element_bit08_frame"
            "_v43_shape_same_position_same_dword"
        ),
    },
    "elements": [
        {
            "role": "control",
            "element_key": _CONTROL.element_key,
            "payload_dword": _CONTROL.payload_dword,
            # Written as text on purpose: JSON has no hex literal and a
            # reader must be able to see 0x12 rather than 18.
            "element_mask_hex": "0x12",
            "property_gate": None,
            "property_index": None,
            "x_offset": _CONTROL.x_offset,
            "scheduler_delay": _CONTROL.delay,
            "coordinate_provenance": (
                "triggering_target_pos_plus_30x_same_y_same_z"
            ),
        },
        {
            "role": "treatment",
            "element_key": _TREATMENT.element_key,
            "payload_dword": _TREATMENT.payload_dword,
            "element_mask_hex": "0x3A",
            "property_gate": _TREATMENT.property_gate,
            "property_index": _TREATMENT.property_index,
            "x_offset": _TREATMENT.x_offset,
            "scheduler_delay": _TREATMENT.delay,
            "coordinate_provenance": (
                "triggering_target_pos_plus_30x_same_y_same_z"
            ),
        },
    ],
    "frame_pins": {
        "control_pc_size": GROUND_LOOT_NAMEPROP_CONTROL_GEOMETRY.pc_size,
        "control_frame_size": (
            GROUND_LOOT_NAMEPROP_CONTROL_GEOMETRY.frame_size
        ),
        "control_coordinate_bytes_masked": (
            "pc[30:34]+pc[35:39]+pc[40:44]"
        ),
        "control_pc_template_sha256": (
            GROUND_LOOT_NAMEPROP_CONTROL_GEOMETRY.pc_template_sha256
        ),
        "control_frame_template_sha256": (
            GROUND_LOOT_NAMEPROP_CONTROL_GEOMETRY.frame_template_sha256
        ),
        "treatment_pc_size": (
            GROUND_LOOT_NAMEPROP_TREATMENT_GEOMETRY.pc_size
        ),
        "treatment_frame_size": (
            GROUND_LOOT_NAMEPROP_TREATMENT_GEOMETRY.frame_size
        ),
        "treatment_coordinate_bytes_masked": (
            "pc[32:36]+pc[37:41]+pc[42:46]"
        ),
        "treatment_pc_template_sha256": (
            GROUND_LOOT_NAMEPROP_TREATMENT_GEOMETRY.pc_template_sha256
        ),
        "treatment_frame_template_sha256": (
            GROUND_LOOT_NAMEPROP_TREATMENT_GEOMETRY.frame_template_sha256
        ),
    },
    "capabilities": [
        "emit_one_control_and_one_treatment_bit08_frame_at_scene_load",
    ],
    "nonclaims": [
        "ui_text_property_is_a_colour",
        "meaning_of_ui_text_property_0x34_or_0x5D_to_0x62",
        "static_create_path_is_the_widget_the_observer_sees",
        "bit08_list_is_ground_loot",
        "payload_dword_is_an_item_template_id",
        "client_accepts_element_mask_0x3A",
        "scheduler_delay_is_a_wire_gap",
        "appearance_match_with_an_old_screenshot_is_original_server_evidence",
        "actor_name_label_appearance",
        "original_server_ever_sent_bit08",
        "production_baseline_behavior",
    ],
}

_PROFILES = {_NAMEPROP_PROBE.scenario_id: _NAMEPROP_PROBE}


def _exact_equal(actual: Any, expected: Any) -> bool:
    """Type-strict recursive equality.

    Plain ``==`` would accept ``True`` where ``1`` is expected and ``2``
    where ``2.0`` is expected.  A permission token that accepts near misses
    is not a permission token, so every node is compared by type first.
    """
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        if set(actual) != set(expected):
            return False
        return all(_exact_equal(actual[key], expected[key]) for key in expected)
    if type(expected) is list:
        if len(actual) != len(expected):
            return False
        return all(
            _exact_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def require_ground_loot_nameprop_scenario(value: Any) -> NamePropScenario:
    """Refuse anything that is not the module's own frozen profile.

    Compared by identity, so a value-equal lookalike dataclass built outside
    this module opens nothing.
    """
    if not any(value is profile for profile in _PROFILES.values()):
        raise ValueError(
            "ground_loot_nameprop_scenario_not_allowlisted: HYP-PF-039 "
            "refuses to emit a selector frame for a profile this module did "
            "not issue"
        )
    return value


def load_ground_loot_nameprop_scenario(path) -> NamePropScenario:
    """Load the one allowlisted opt-in scenario file, or refuse by name."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "ground_loot_nameprop_scenario_unreadable: HYP-PF-039 refuses "
            "an unreadable or malformed opt-in file"
        ) from exc
    if type(data) is not dict or data.get("id") not in _PROFILES:
        raise ValueError(
            "ground_loot_nameprop_scenario_unknown_id: HYP-PF-039 refuses a "
            "file that does not name the one allowlisted profile"
        )
    if not _exact_equal(data, _EXPECTED):
        raise ValueError(
            "ground_loot_nameprop_scenario_exceeds_allowlist: HYP-PF-039 "
            "refuses a scenario body that drifted from the allowlisted one"
        )
    return require_ground_loot_nameprop_scenario(_PROFILES[data["id"]])


def _f32(value: float) -> float:
    """Quantize to the exact f32 the wire will carry."""
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def _element_wire(legacy, element: NamePropElement,
                  x: float, y: float, z: float) -> bytes:
    """One 0x5F85B0 element, in the re-derived field order.

    The mask is asserted against the fields actually written rather than
    trusted.  These guards are live, not decorative: this lane emits TWO
    DIFFERENT masks, so an element whose mask and fields disagreed would
    produce bytes the client walks differently from the way we describe
    them -- and a wire claim nobody can read back is worse than no frame.
    """
    mask = element.element_mask
    if mask & 0x04:
        raise RuntimeError(
            "ground_loot_nameprop_mask_unsupported: HYP-PF-039 composes no "
            "field for element mask bit 0x04"
        )
    if not (mask & 0x02 and mask & 0x10):
        raise RuntimeError(
            "ground_loot_nameprop_mask_incomplete: HYP-PF-039 refuses a mask "
            "that does not name both the payload dword and the position"
        )
    gate_named = bool(mask & 0x08)
    index_named = bool(mask & 0x20)
    if gate_named != (element.property_gate is not None):
        raise RuntimeError(
            "ground_loot_nameprop_gate_mask_disagrees: HYP-PF-039 refuses an "
            "element whose mask and gate field do not agree"
        )
    if index_named != (element.property_index is not None):
        raise RuntimeError(
            "ground_loot_nameprop_index_mask_disagrees: HYP-PF-039 refuses "
            "an element whose mask and index field do not agree"
        )
    if gate_named and element.property_gate == 0:
        raise RuntimeError(
            "ground_loot_nameprop_gate_is_zero: HYP-PF-039 refuses to send "
            "a gate the client reads as 'use the default property'"
        )
    if index_named and not (
            GROUND_LOOT_NAMEPROP_INDEX_MIN
            <= element.property_index
            <= GROUND_LOOT_NAMEPROP_INDEX_MAX):
        raise RuntimeError(
            "ground_loot_nameprop_index_out_of_range: HYP-PF-039 refuses an "
            "index the client would discard for the default property"
        )
    out = (
        legacy.u32tag(0x14, element.element_key)            # +0x10 key
        + legacy.u8tag(0x0B, mask)                          # +0x28 dirty mask
        + legacy.u32tag(0x14, element.payload_dword)        # +0x14 (bit 0x02)
    )
    if gate_named:
        out += legacy.u8tag(0x05, element.property_gate)    # +0x1B (bit 0x08)
    out += (
        legacy.f32tag(x)                                    # +0x1C (bit 0x10)
        + legacy.f32tag(y)                                  # +0x20
        + legacy.f32tag(z)                                  # +0x24
    )
    if index_named:
        out += legacy.u8tag(0x08, element.property_index)   # +0x1A (bit 0x20)
    return out


def make_ground_loot_nameprop_frames(
    legacy, scenario, trigger_xyz,
) -> Tuple[Tuple[bytes, bytes], ...]:
    """Compose the control and treatment frames from the trigger position.

    ``trigger_xyz`` is the (x, y, z) of the exact TargetPos frame that fires
    the emission -- already f32-exact because it was parsed from wire f32.
    Both elements sit at trigger + 30 on X, same Y/Z, so the geometry claim
    travels with the frame that proves where the player is.
    """
    scenario = require_ground_loot_nameprop_scenario(scenario)
    try:
        tx, ty, tz = (float(v) for v in trigger_xyz)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "ground_loot_nameprop_trigger_malformed: HYP-PF-039 refuses to "
            "compose without the triggering TargetPos coordinates"
        ) from exc
    if not all(math.isfinite(v) for v in (tx, ty, tz)):
        raise RuntimeError(
            "ground_loot_nameprop_trigger_not_finite: HYP-PF-039 refuses to "
            "place elements relative to a non-finite trigger position"
        )
    if len(scenario.elements) != len(GROUND_LOOT_NAMEPROP_GEOMETRY):
        # zip() would silently truncate to the shorter side and emit an
        # unpinned element; refuse instead.
        raise RuntimeError(
            "ground_loot_nameprop_pin_count_mismatch: HYP-PF-039 refuses a "
            "profile whose element count does not match the pinned templates"
        )
    out = []
    for element, geometry in zip(
            scenario.elements, GROUND_LOOT_NAMEPROP_GEOMETRY):
        try:
            x, y, z = _f32(tx + element.x_offset), _f32(ty), _f32(tz)
        except OverflowError:
            x = y = z = float("inf")
        if not all(math.isfinite(v) for v in (x, y, z)):
            raise RuntimeError(
                "ground_loot_nameprop_offset_overflow: HYP-PF-039 refuses "
                "an offset position that does not survive the f32 round-trip"
            )
        pc = bytearray()
        pc += legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_RES)
        pc += legacy.u32tag(0x14, 0)
        pc += legacy.u8tag(0x08, 4)
        pc += legacy.u8tag(0x0B, 0)                          # inherited: none
        pc += legacy.u8tag(0x0B, GROUND_LOOT_NAMEPROP_DERIVED_BIT)
        pc += legacy.u16tag(0x12, 1)                         # ONE element
        pc += _element_wire(legacy, element, x, y, z)
        pc = bytes(pc)
        masked = bytearray(pc)
        for start, end in geometry.coord_spans:
            masked[start:end] = b"\x00" * (end - start)
        # NOTE: this coordinate-byte comparison shares its inputs with the
        # element wire above, so it only catches f32tag/encoding drift; the
        # trigger+offset DERIVATION is enforced by construction and by the
        # dispatch tests and the headless replay, not by this line.
        coord_bytes = struct.pack("<fff", x, y, z)
        actual_coords = b"".join(
            pc[start:end] for start, end in geometry.coord_spans
        )
        frame = legacy.frame_pc(pc)
        masked_frame = bytearray(frame)
        for start, end in geometry.coord_spans:
            shift = GROUND_LOOT_NAMEPROP_FRAME_COORD_SHIFT
            masked_frame[start + shift:end + shift] = (
                b"\x00" * (end - start)
            )
        if (
            len(pc) != geometry.pc_size
            or hashlib.sha256(bytes(masked)).hexdigest().upper()
            != geometry.pc_template_sha256
            or actual_coords != coord_bytes
            or len(frame) != geometry.frame_size
            or hashlib.sha256(bytes(masked_frame)).hexdigest().upper()
            != geometry.frame_template_sha256
        ):
            raise RuntimeError(
                "ground_loot_nameprop_frame_drift: HYP-PF-039 refuses to "
                "emit bytes that do not match the pinned composition"
            )
        out.append((pc, frame))
    return tuple(out)
