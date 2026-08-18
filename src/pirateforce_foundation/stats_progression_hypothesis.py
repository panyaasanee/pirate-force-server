"""STATS-PROG-002 -- server-side encoder for the mask-gated progression fields
carried by the ``UpdateAttrVital`` 0x309A delta pipe (HYP-PF-020).

Where the project stops without this module
-------------------------------------------
``player_wire.py`` projects exactly six ``BasicAttr`` fields and two
``ActorAttr`` fields, and the frozen v141 snapshot's only ``ActorAttr`` delta
encoder writes the 64-bit mask as the literal ``struct.pack("<II", 0x800, 0)``
-- one field, cash.  Level, experience and the five ability values have never
been emitted by anything in this repository, which is why
``character_management/stats_and_progression`` is graded ``in_progress`` on
static evidence alone and why GT-017 (does the XP bar / level number / ability
row on screen move when the server says so?) had nothing to run against.

What STATS-PROG-001 proved (round 76, do not re-prove, do not contradict)
-------------------------------------------------------------------------
``reports/PF_STATS_PROG001_CHARACTER_STATS_AND_PROGRESSION_STATIC_20260818.md``
(99 tool guards + 25 tests, byte-exact against the read-only client image
SHA-256 ``9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623``)
established, and this module implements verbatim:

  * ``UpdateAttrVital`` 0x309A is the delta transport (report table s1); its
    serializer 0x5E42C0 re-bases ``this+0x14`` and tail-jumps to the shared
    Attr-collection codec 0x463DE0, and the inbound handler is 0x5F2400.
  * The wire follows the class chain base first (report s2):
    ``DBAttribute::Serialize`` 0x467790 -> ``BasicAttr::Serialize`` 0x4656F0
    -> ``ActorAttr::Serialize`` 0x466230.
  * Every block is dirty-mask gated (report s2/s4/s5): ``DBAttribute`` u8 mask
    at +0x20, ``BasicAttr`` u16 mask at +0x70 with 12 gated fields,
    ``ActorAttr`` 64-bit mask staged from +0x1B4/+0x1B8 and emitted as one
    qword, followed by the u8 extra-group flag at +0x1BC.
  * Field-by-field, with a gate pin each (report s4 and s5 tables):
    level ``BasicAttr`` u16 +0x5E bit 0x0002 (gate 0x465736, script binding
    ``GetLv`` handler 0x460050); HP cur/max +0x44/+0x48 bits 0x0004/0x0008;
    MP cur/max +0x4C/+0x50 bits 0x0010/0x0020; scene id +0x5C bit 0x0100;
    scene sequence +0x60 bit 0x0200; class ``ActorAttr`` u32 +0x8C bit
    0x00000001; skill points u32 +0x7C bit 0x00000008; unspent allocation
    points u16 +0x80 bit 0x00000010; STR/CON/DEX/INT/PER u16
    +0x82/+0x84/+0x86/+0x88/+0x8A bits 0x20/0x40/0x80/0x100/0x200; their five
    bonus counterparts u16 +0x182..+0x18A bits 0x00040000..0x00400000; and
    experience qword +0xA0 bit 0x00000400 (gate 0x4663A8, XP bar 0x519299
    dividing it by ``STANDARD_STATUS[level+1].n_EXP_CURRENTLV`` times 100).
  * Cash is the qword immediately after experience, +0xA8 bit 0x00000800,
    told apart from it by its consumer (``GetCash`` 0x4600AC), not by
    position.

Field ORDER is not assumed here, it is read off the report
----------------------------------------------------------
The report's s4 and s5 tables list, for every gated field, the address of the
mask test that gates it.  Those addresses ascend strictly with the mask bit
value in both tables (BasicAttr 0x465727 < 0x465736 < 0x46574A < ... <
0x465825 for bits 0x0001 < 0x0002 < 0x0004 < ... < 0x0800; ActorAttr
0x466299 < 0x4662EC < ... < 0x466508 for bits 0x1 < 0x8 < ... < 0x400000).
A linear serializer emits in code order, so ascending code address IS
ascending emission order, and ascending mask bit therefore IS the wire order.
That is what ``_ordered`` enforces, and ``_require_ascending_gate_pins``
re-checks the pins themselves so the argument cannot silently invert.

The independent cross-check that keeps this honest
--------------------------------------------------
This encoder is generic and mask-driven; ``player_wire.make_actor_attr_with_name``
is hand-written, field-by-field, and has been on the wire in front of a real
client since NAME-002.  For the baseline field set the two must agree BYTE FOR
BYTE, and ``_require_player_wire_crosscheck`` asserts exactly that on every
composition.  A wrong tag, a wrong width, a wrong mask bit, a wrong block
boundary or an inverted field order cannot survive it.  Every composed payload
is additionally re-decoded by ``decode_actor_attr`` and compared with the
requested ``(identity, fields)`` before the bytes are returned.

Fail-closed contract
--------------------
Refused with ``ValueError`` and no bytes: an unknown field name, a value of the
wrong type (``bool`` included), a value outside the field's width, a name that
is not two bytes per UTF-16 code unit, a missing identity, a mask bit outside
the implemented table, any mask bit in the high half of the 64-bit ActorAttr
mask (the u8 flag at +0x1BC gates that half and this lane never sets it to
anything but the v141-proven 1), and a step label outside the pinned plan.
No database call exists on any path in this file.

Deliberately NOT implemented
----------------------------
The five progression VERBS of STATS-PROG-001 s7 have no encoder, no decoder
and no dispatch here -- this milestone moves the delta pipe only, so the
static milestone's "0 encoders, 0 dispatch" statement about those verbs stays
literally true and its guards stay green.  ``BasicAttr`` bits 0x0001, 0x0040,
0x0080, 0x0400 and 0x0800 and the 24 unnamed ``ActorAttr`` fields are not
implemented either; ``NOT_IMPLEMENTED_*`` below says so explicitly rather than
leaving the omission silent.

Opt-in, test-only
-----------------
``production_allowed`` is False in the module and in the scenario file, the
scenario loads through an exact allowlist, and with no scenario handed in the
dispatch branch does not exist: nothing in default mode composes one byte of
this.  ``database_write`` is ``none`` -- progression has no table, and this
lane deliberately does not open one.

NOT CLAIMED here: that any client has ever rendered any of it (that is
GT-017, attended, not run); that this project has ever seen a progression
field on a wire in either direction; anything about the ORIGINAL server's
progression rules, XP curve, allocation validation or reset cost (the curve
numbers are not even in the client executable -- STATS-PROG-001 s8.4); that a
sparse delta which omits a field leaves that field alone on the client (v141's
own note on apply 0x464F30 says the opposite, which is why every frame here
carries the full baseline field set); and any meaning for the u8 extra-group
flag beyond reproducing the value v141 has always sent.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .player_wire import make_actor_attr_with_name


# ---------------------------------------------------------------- static pins
# Client-binary VAs proven in STATS-PROG-001; carried as documentation-grade
# constants and never dereferenced.
UPDATE_ATTR_VITAL_SERIALIZER_VA = 0x5E42C0     # UpdateAttrVital Serialize
ATTR_COLLECTION_CODEC_VA = 0x463DE0            # shared Attr-collection codec
UPDATE_ATTR_VITAL_HANDLER_VA = 0x5F2400        # inbound apply handler
DB_ATTRIBUTE_SERIALIZER_VA = 0x467790
BASIC_ATTR_SERIALIZER_VA = 0x4656F0
ACTOR_ATTR_SERIALIZER_VA = 0x466230
ACTOR_ATTR_APPLY_VA = 0x464F30

# The three ids v141 already carries as committed constants.  They are
# re-declared here for documentation and drift-checked against the frozen
# module at composition time; they are never used in place of it.
UPDATE_ATTR_VITAL_ID = 0x309A
ACTOR_ATTR_ID = 0x12AD
UPDATE_ATTR_VITAL_VERSION = 0

# Block masks.  DBAttribute u8 at +0x20, BasicAttr u16 at +0x70, ActorAttr
# 64-bit staged from +0x1B4/+0x1B8 and emitted as one qword, then the u8
# extra-group flag at +0x1BC.
DB_ATTRIBUTE_MASK_TAG = 0x0B
DB_ATTRIBUTE_MASK_OFFSET = 0x20
DB_ATTRIBUTE_IDENTITY_BIT = 0x01
DB_ATTRIBUTE_IDENTITY_OFFSET = 0x18
DB_ATTRIBUTE_IDENTITY_TAG = 0x32
BASIC_ATTR_MASK_TAG = 0x12
BASIC_ATTR_MASK_OFFSET = 0x70
ACTOR_ATTR_MASK_TAG = 0x32
ACTOR_ATTR_MASK_LOW_OFFSET = 0x1B4
ACTOR_ATTR_MASK_HIGH_OFFSET = 0x1B8
ACTOR_ATTR_EXTRA_GROUP_TAG = 0x05
ACTOR_ATTR_EXTRA_GROUP_OFFSET = 0x1BC
# v141 has always sent 1 here (make_actor_attr_minimal), with the high mask
# dword zero.  This lane reproduces that byte and refuses every high-half bit
# rather than guessing what the flag would mean with one set.
ACTOR_ATTR_EXTRA_GROUP_VALUE = 1
ACTOR_ATTR_MASK_LOW_HALF_LIMIT = 1 << 32

# Field widths as emitted by the scalar codec 0x89A600 (stdcall tag/ptr/width)
# and the wstring codec 0x89A810 (tag 0x48 + u32 byte length + UTF-16LE).
FIELD_KIND_WIDTH = {"u16": 2, "u32": 4, "qword": 8}
WSTRING_TAG = 0x48
WSTRING_HEADER_SIZE = 5


@dataclass(frozen=True)
class AttrField:
    """One mask-gated field: block, bit, object offset, wire tag, width."""

    name: str
    block: str
    mask_bit: int
    offset: int
    tag: int
    kind: str
    evidence: str


def _ordered(fields: tuple[AttrField, ...]) -> tuple[AttrField, ...]:
    """Emission order IS ascending mask-bit order (see the module docstring)."""
    return tuple(sorted(fields, key=lambda field: field.mask_bit))


# BasicAttr, mask +0x70.  Report s4; bits 0x0001 / 0x0040 / 0x0080 / 0x0400 /
# 0x0800 are deliberately absent -- see NOT_IMPLEMENTED_BASIC_ATTR_BITS.
BASIC_ATTR_FIELDS = _ordered((
    AttrField("level", "basic", 0x0002, 0x5E, 0x12, "u16",
              "STATS-PROG-001 s4 gate 0x465736; GetLv handler 0x460050"),
    AttrField("hp_current", "basic", 0x0004, 0x44, 0x14, "u32",
              "STATS-PROG-001 s4 gate 0x46574A"),
    AttrField("hp_max", "basic", 0x0008, 0x48, 0x14, "u32",
              "STATS-PROG-001 s4 gate 0x46575E"),
    AttrField("mp_current", "basic", 0x0010, 0x4C, 0x14, "u32",
              "STATS-PROG-001 s4 gate 0x465772; PROGRESSBAR_MP 0x53F1AD"),
    AttrField("mp_max", "basic", 0x0020, 0x50, 0x14, "u32",
              "STATS-PROG-001 s4 gate 0x465786; schema column n_STAMINAMAX"),
    AttrField("scene_id", "basic", 0x0100, 0x5C, 0x12, "u16",
              "STATS-PROG-001 s4 gate 0x4657C2"),
    AttrField("scene_sequence", "basic", 0x0200, 0x60, 0x32, "qword",
              "STATS-PROG-001 s4 gate 0x4657E3"),
))

# ActorAttr, 64-bit mask.  Report s5; the 24 unnamed fields are absent -- see
# NOT_IMPLEMENTED_ACTOR_ATTR_NOTE.
ACTOR_ATTR_FIELDS = _ordered((
    AttrField("class_id", "actor", 0x00000001, 0x8C, 0x19, "u32",
              "STATS-PROG-001 s5 gate 0x466299; GetClass 0x460160"),
    AttrField("skill_points", "actor", 0x00000008, 0x7C, 0x19, "u32",
              "STATS-PROG-001 s5 gate 0x4662EC; NUMBERLABEL_SPNOW 0x75C613"),
    AttrField("unspent_ability_points", "actor", 0x00000010, 0x80, 0x12, "u16",
              "STATS-PROG-001 s5 gate 0x466304; spinner cap 0x57DD7A"),
    AttrField("ability_str", "actor", 0x00000020, 0x82, 0x12, "u16",
              "STATS-PROG-001 s5 gate 0x46631F; getter 0x467A60 -> LABEL_STR"),
    AttrField("ability_con", "actor", 0x00000040, 0x84, 0x12, "u16",
              "STATS-PROG-001 s5 gate 0x46633A; getter 0x467AF0 -> LABEL_CON"),
    AttrField("ability_dex", "actor", 0x00000080, 0x86, 0x12, "u16",
              "STATS-PROG-001 s5 gate 0x466355; getter 0x467B80 -> LABEL_DEX"),
    AttrField("ability_int", "actor", 0x00000100, 0x88, 0x12, "u16",
              "STATS-PROG-001 s5 gate 0x466370; getter 0x467CA0 -> LABEL_INT"),
    AttrField("ability_per", "actor", 0x00000200, 0x8A, 0x12, "u16",
              "STATS-PROG-001 s5 gate 0x46638A; getter 0x467C10 -> LABEL_PER"),
    AttrField("experience", "actor", 0x00000400, 0xA0, 0x32, "qword",
              "STATS-PROG-001 s5 gate 0x4663A8; XP bar 0x519299/0x5192C6"),
    AttrField("cash", "actor", 0x00000800, 0xA8, 0x32, "qword",
              "STATS-PROG-001 s5 gate 0x4663C6; GetCash 0x4600AC"),
    AttrField("ability_bonus_str", "actor", 0x00040000, 0x182, 0x12, "u16",
              "STATS-PROG-001 s5 gate 0x466490"),
    AttrField("ability_bonus_con", "actor", 0x00080000, 0x184, 0x12, "u16",
              "STATS-PROG-001 s5 gate 0x4664AE"),
    AttrField("ability_bonus_dex", "actor", 0x00100000, 0x186, 0x12, "u16",
              "STATS-PROG-001 s5 gate 0x4664CC"),
    AttrField("ability_bonus_int", "actor", 0x00200000, 0x188, 0x12, "u16",
              "STATS-PROG-001 s5 gate 0x4664EA"),
    AttrField("ability_bonus_per", "actor", 0x00400000, 0x18A, 0x12, "u16",
              "STATS-PROG-001 s5 gate 0x466508"),
    # The one bit in this table that STATS-PROG-001 does NOT pin directly.
    # The report names +0x164 as the persisted player-name wstring but gives no
    # gate address for it; the bit is DERIVED from the mask v141/player_wire
    # have had on the wire since NAME-002, 0x01000800, whose only two bits are
    # cash 0x00000800 (report-pinned) and this one, emitted in that order after
    # the cash qword.  Recorded as a derivation, not as a report pin.
    AttrField("character_name", "actor", 0x01000000, 0x164, WSTRING_TAG,
              "wstring",
              "derived: player_wire mask 0x01000800 minus report-pinned cash"),
))

# Named in STATS-PROG-001 but deliberately outside this encoder.
NOT_IMPLEMENTED_BASIC_ATTR_BITS = (0x0001, 0x0040, 0x0080, 0x0400, 0x0800)
NOT_IMPLEMENTED_ACTOR_ATTR_NOTE = (
    "the 24 ActorAttr fields STATS-PROG-001 s5 decodes but deliberately "
    "does not name are not implemented, and neither is any of the five "
    "progression verbs of s7"
)

PROGRESSION_FIELDS = {
    field.name: field for field in (*BASIC_ATTR_FIELDS, *ACTOR_ATTR_FIELDS)
}

# Rejection reasons; every one of them means "no bytes, no reply, no write".
STATS_PROGRESSION_REJECTIONS = (
    "unknown_field",
    "value_type_not_integer",
    "value_outside_field_width",
    "identity_outside_qword",
    "character_name_not_two_bytes_per_code_unit",
    "empty_character_name",
    "mask_bit_in_unimplemented_high_half",
    "unknown_step_label",
)

# One-vital GSCN_RunTimeProtocolRes v4 collection geometry (v141
# make_runtime_vitals), identical to the geometry the chat lanes pin.
STATS_PC_PAYLOAD_OFFSET = 20
STATS_PC_OVERHEAD = 22
# u16tag count (3) + u16tag attr id (3) + u32tag body length (5).
STATS_ATTR_COLLECTION_HEADER_SIZE = 11
STATS_PC_ATTR_BODY_OFFSET = STATS_PC_PAYLOAD_OFFSET + STATS_ATTR_COLLECTION_HEADER_SIZE
STATS_ATTR_COLLECTION_COUNT = 1


@dataclass(frozen=True)
class StatsProgressionActor:
    """The per-session inputs a composed frame needs, and nothing else."""

    identity_lo: int
    identity_hi: int
    scene_id: int
    scene_sequence: int
    character_name: str


# ------------------------------------------------------------ the sweep plan
STATS_PROGRESSION_SCENARIO_ID = "stats_progression_hypothesis_xp_sweep"
STATS_PROGRESSION_HYPOTHESIS_ID = "HYP-PF-020"

# The baseline every frame carries.  It is NOT a design choice about what a
# progression delta "should" contain: it is the exact field set
# player_wire.make_actor_attr_with_name already puts on the wire at start-game,
# reproduced by this encoder and byte-compared against it on every call.  v141's
# own note on ActorAttr apply 0x464F30 says the client copies the complete
# object, so a field left out of a delta does not keep its live value -- which
# is why nothing here ships a bare two-field delta.
STATS_BASELINE_HP_CURRENT = 100
STATS_BASELINE_HP_MAX = 100

# GT-017 reads these on screen, one change per frame, cumulative so that no
# earlier change is undone by a later frame.
STATS_PROGRESSION_EXPERIENCE_1 = 1234
STATS_PROGRESSION_EXPERIENCE_2 = 987654
STATS_PROGRESSION_LEVEL = 7
# Distinct multiples of eleven: if LABEL_STR shows 22 instead of 11 the
# offset-to-label binding is off by one and the tester can see it at a glance.
STATS_PROGRESSION_ABILITY_STR = 11
STATS_PROGRESSION_ABILITY_CON = 22
STATS_PROGRESSION_ABILITY_DEX = 33
STATS_PROGRESSION_ABILITY_INT = 44
STATS_PROGRESSION_ABILITY_PER = 55

STATS_PROGRESSION_STEPS = (
    ("BASELINE", {}),
    ("EXPERIENCE_1", {"experience": STATS_PROGRESSION_EXPERIENCE_1}),
    ("EXPERIENCE_2", {"experience": STATS_PROGRESSION_EXPERIENCE_2}),
    ("LEVEL", {"level": STATS_PROGRESSION_LEVEL}),
    ("ABILITY_STR", {"ability_str": STATS_PROGRESSION_ABILITY_STR}),
    ("ABILITY_CON", {"ability_con": STATS_PROGRESSION_ABILITY_CON}),
    ("ABILITY_DEX", {"ability_dex": STATS_PROGRESSION_ABILITY_DEX}),
    ("ABILITY_INT", {"ability_int": STATS_PROGRESSION_ABILITY_INT}),
    ("ABILITY_PER", {"ability_per": STATS_PROGRESSION_ABILITY_PER}),
)
STATS_PROGRESSION_STEP_ORDER = tuple(
    label for label, _fields in STATS_PROGRESSION_STEPS
)
STATS_PROGRESSION_STEP_FIELDS = {
    label: dict(fields) for label, fields in STATS_PROGRESSION_STEPS
}

# Seconds between consecutive sends.  The frozen V141 sender treats the fourth
# action-tuple field as a gap on a cumulative deadline (send_deadline += delay,
# then sleep to it), so the first frame carries 0.0 and each later frame the
# full spacing.  Three seconds is what an attended reader needs to attribute
# one on-screen change to one frame.
STATS_PROGRESSION_SPACING_SECONDS = 3.0
STATS_PROGRESSION_FIRST_DELAY_SECONDS = 0.0
STATS_PROGRESSION_ACTION_LABEL_PREFIX = "HYP_PF_020_STATS_PROG_"


@dataclass(frozen=True)
class StatsProgressionHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    step_order: tuple[str, ...]
    spacing_seconds: float


# --------------------------------------------------------------- probe pins
# The composition is per-character (identity, scene, name), so the pins below
# are for ONE explicit probe actor: the first character of the first account of
# a fresh store (lifecycle identity_lo = 0x10000000 + account_id * 0x10000 +
# selector + 1 with account_id 1 and selector 0), at the default spawn scene,
# under the canonical smoke name the pinned V25 create wire commits.
STATS_PROBE_IDENTITY_LO = 0x10010001
STATS_PROBE_IDENTITY_HI = 0
STATS_PROBE_SCENE_ID = 1
STATS_PROBE_SCENE_SEQUENCE = 0
STATS_PROBE_CHARACTER_NAME = "test01"
# Drift-checked against legacy.V116_INITIAL_CASH on every composition; the
# baseline must not move the client's cash by one coin.
STATS_PROBE_CASH = 10000
STATS_PROBE_ACTOR = StatsProgressionActor(
    STATS_PROBE_IDENTITY_LO, STATS_PROBE_IDENTITY_HI, STATS_PROBE_SCENE_ID,
    STATS_PROBE_SCENE_SEQUENCE, STATS_PROBE_CHARACTER_NAME,
)

# Computed live by tools/verify_stats_progression_encoder.py; every value below
# is a sha256 of bytes this encoder produced, never a value copied in.
STATS_PROBE_ATTR_BODY_SHA256 = {
    "BASELINE": (
        "479ED77DFA554F89AAB02E884608EC53BAEC9E213F85548AF9CCD291BCC896C4"
    ),
    "EXPERIENCE_1": (
        "53D7B4EF98604159C7ED07270BD474660C99512BC4736B5B26C9E3C4D848B661"
    ),
    "EXPERIENCE_2": (
        "F1C14654F06D805A4A3A642D6DD41A32EAA316DC089138158727E256EB93B437"
    ),
    "LEVEL": (
        "A0743D9BE338E470344914F5CC91B095B76254268DF180DEE721888470C0DB24"
    ),
    "ABILITY_STR": (
        "AEB122CEA1B4256E151B9661153085AE81B838071288CB10F0868585B1D96620"
    ),
    "ABILITY_CON": (
        "B421BAC35F08DB6A9E377C87F772A5F04B02AC33B90DB29B5EE4A885E1DB5D39"
    ),
    "ABILITY_DEX": (
        "D2CF02DF7FA574311B2383E1FD5E21D809D7659632CC4D988BAD33E6523C8342"
    ),
    "ABILITY_INT": (
        "B20CD7AC63A9F9EB4FCB8236F3791AA77D5A2B028F026C9BA7BC99FC4AFB42D4"
    ),
    "ABILITY_PER": (
        "4EE5B05F3773A3171BE8284ED69DC9E878520B870E319900F129E884993ABA1E"
    ),
}
STATS_PROBE_PC_SHA256 = {
    "BASELINE": (
        "DB3CE0B5D14196181EF9EA26A0D435E0489212634334CB562F840E368B5F0049"
    ),
    "EXPERIENCE_1": (
        "EAF977654412771F20008C02739DE3CECBEB5C7F53A163E5FE2C4E65A74912DF"
    ),
    "EXPERIENCE_2": (
        "4C87E2924B8FBC0D0EB82870F57D273E7DB7F6FB3F8E3C8DEDA6E0F210E1F421"
    ),
    "LEVEL": (
        "3C6AF0B21B6A92491375830EA33EBEF293AD223B46C68CA7C866EE696F07E59E"
    ),
    "ABILITY_STR": (
        "4C85605FCB38AC7C47CA825A849EC86B847182A5B21F32CC2B92D732CDF5DAD6"
    ),
    "ABILITY_CON": (
        "1BB3225F1CBA9F5B414E8A27A9B499432DECDB454DF8895BF10C79CFA4312881"
    ),
    "ABILITY_DEX": (
        "A256C9A69572ACCB6FE8FCA07C7E8783790FB68B1DFD6C076336EAF52A797022"
    ),
    "ABILITY_INT": (
        "77AB9EE8E29B396A18A98F4A3DDC75A1B9851D1FCF60393148574926D638AA0E"
    ),
    "ABILITY_PER": (
        "0B57D332114568AC644E3B65D37E6BC28C3053EB595941C1E2059F60328796D5"
    ),
}
STATS_PROBE_FRAME_SHA256 = {
    "BASELINE": (
        "04E2B40152B633A48C84713B1C24A2910B7AB84E178E268094C0D10B179D9FBC"
    ),
    "EXPERIENCE_1": (
        "0174F88CF2171AFF6AA34D7278F5F488CDF77132F73035526CE20C7EBE2325B1"
    ),
    "EXPERIENCE_2": (
        "4FC30B642D619E4CBBD6DFDDB13A643A67D3DECC8BDADAF3D45AA6682F3D2E2D"
    ),
    "LEVEL": (
        "4D016B5F775E5355909AA2CB795BA1F598F7538BF5FD0202605D3891F8AE3158"
    ),
    "ABILITY_STR": (
        "408D9E1A1A662EF39A85D81EC9C45A9732C7D64323F812AA2FCD7D43D339FF70"
    ),
    "ABILITY_CON": (
        "425B740EB4DABA91A38FBA46A1EBD8F8A35130227C16BB44FCEA1008662F1BCF"
    ),
    "ABILITY_DEX": (
        "857891B014383215DE540F2A6C47FEE3A9E4D42BB13817C99651241F834AFD21"
    ),
    "ABILITY_INT": (
        "165990411FC64348A69389F1DA5F67F9A3E5E6A2F096FD6D79511C6BD05A5F16"
    ),
    "ABILITY_PER": (
        "50AC4927BBEAD772EFAB459B07D35404F457F3E190F53EF538C378BD7B186625"
    ),
}
STATS_PROBE_ATTR_BODY_SIZE = {
    "BASELINE": 73,
    "EXPERIENCE_1": 82,
    "EXPERIENCE_2": 82,
    "LEVEL": 85,
    "ABILITY_STR": 88,
    "ABILITY_CON": 91,
    "ABILITY_DEX": 94,
    "ABILITY_INT": 97,
    "ABILITY_PER": 100,
}
STATS_PROBE_PC_SIZE = {
    "BASELINE": 106,
    "EXPERIENCE_1": 115,
    "EXPERIENCE_2": 115,
    "LEVEL": 118,
    "ABILITY_STR": 121,
    "ABILITY_CON": 124,
    "ABILITY_DEX": 127,
    "ABILITY_INT": 130,
    "ABILITY_PER": 133,
}
STATS_PROBE_FRAME_SIZE = {
    "BASELINE": 117,
    "EXPERIENCE_1": 126,
    "EXPERIENCE_2": 126,
    "LEVEL": 129,
    "ABILITY_STR": 132,
    "ABILITY_CON": 135,
    "ABILITY_DEX": 138,
    "ABILITY_INT": 142,
    "ABILITY_PER": 145,
}


# ---------------------------------------------------------------- self-guards
# The gate-pin addresses STATS-PROG-001 s4/s5 record for every field this
# encoder implements.  They exist here for one reason: the whole field-order
# argument rests on "ascending gate address == ascending emission order", so
# the pins have to ascend with the mask bits or the argument is unsound.
BASIC_ATTR_GATE_PINS = {
    0x0002: 0x465736, 0x0004: 0x46574A, 0x0008: 0x46575E, 0x0010: 0x465772,
    0x0020: 0x465786, 0x0100: 0x4657C2, 0x0200: 0x4657E3,
}
ACTOR_ATTR_GATE_PINS = {
    0x00000001: 0x466299, 0x00000008: 0x4662EC, 0x00000010: 0x466304,
    0x00000020: 0x46631F, 0x00000040: 0x46633A, 0x00000080: 0x466355,
    0x00000100: 0x466370, 0x00000200: 0x46638A, 0x00000400: 0x4663A8,
    0x00000800: 0x4663C6, 0x00040000: 0x466490, 0x00080000: 0x4664AE,
    0x00100000: 0x4664CC, 0x00200000: 0x4664EA, 0x00400000: 0x466508,
}


def _require_ascending_gate_pins() -> None:
    """Ascending mask bit must mean ascending gate address, in both blocks."""
    for fields, pins in (
        (BASIC_ATTR_FIELDS, BASIC_ATTR_GATE_PINS),
        (ACTOR_ATTR_FIELDS, ACTOR_ATTR_GATE_PINS),
    ):
        addresses = [
            pins[field.mask_bit] for field in fields if field.mask_bit in pins
        ]
        if addresses != sorted(addresses):
            raise RuntimeError("HYP-PF-020 gate pin order contradicts mask order")
        if len(set(addresses)) != len(addresses):
            raise RuntimeError("HYP-PF-020 duplicate gate pin")


def _require_field_table() -> None:
    """No duplicate name, bit or offset inside a block; no unsupported kind."""
    if set(PROGRESSION_FIELDS) != {
        field.name for field in (*BASIC_ATTR_FIELDS, *ACTOR_ATTR_FIELDS)
    }:
        raise RuntimeError("HYP-PF-020 field name collision across blocks")
    for fields in (BASIC_ATTR_FIELDS, ACTOR_ATTR_FIELDS):
        if len({field.mask_bit for field in fields}) != len(fields):
            raise RuntimeError("HYP-PF-020 duplicate mask bit")
        if len({field.offset for field in fields}) != len(fields):
            raise RuntimeError("HYP-PF-020 duplicate field offset")
        for field in fields:
            if field.mask_bit & (field.mask_bit - 1):
                raise RuntimeError("HYP-PF-020 mask bit is not a single bit")
            if field.kind != "wstring" and field.kind not in FIELD_KIND_WIDTH:
                raise RuntimeError("HYP-PF-020 unsupported field width")
    for bit in NOT_IMPLEMENTED_BASIC_ATTR_BITS:
        if bit in {field.mask_bit for field in BASIC_ATTR_FIELDS}:
            raise RuntimeError("HYP-PF-020 not-implemented bit is implemented")
    for field in ACTOR_ATTR_FIELDS:
        if field.mask_bit >= ACTOR_ATTR_MASK_LOW_HALF_LIMIT:
            raise RuntimeError(
                "HYP-PF-020 mask bit in unimplemented high half"
            )


def _require_step_plan() -> None:
    """One new change per frame, cumulative, no label reused, no field reused."""
    if STATS_PROGRESSION_STEP_ORDER[0] != "BASELINE":
        raise RuntimeError("HYP-PF-020 sweep must open with the baseline")
    if STATS_PROGRESSION_STEP_FIELDS["BASELINE"]:
        raise RuntimeError("HYP-PF-020 baseline must add no progression field")
    if len(set(STATS_PROGRESSION_STEP_ORDER)) != len(
        STATS_PROGRESSION_STEP_ORDER
    ):
        raise RuntimeError("HYP-PF-020 duplicate step label")
    seen: dict[str, Any] = {}
    for label in STATS_PROGRESSION_STEP_ORDER[1:]:
        added = STATS_PROGRESSION_STEP_FIELDS[label]
        if len(added) != 1:
            raise RuntimeError("HYP-PF-020 a step must change exactly one field")
        for name, value in added.items():
            if name not in PROGRESSION_FIELDS:
                raise RuntimeError("HYP-PF-020 step names an unknown field")
            if seen.get(name) == value:
                raise RuntimeError("HYP-PF-020 step repeats an unchanged value")
            seen[name] = value
    if STATS_PROGRESSION_EXPERIENCE_1 == STATS_PROGRESSION_EXPERIENCE_2:
        raise RuntimeError("HYP-PF-020 the two experience values must differ")


# ---------------------------------------------------------------- encoder
def _encode_scalar(legacy: Any, field: AttrField, value: Any) -> bytes:
    if type(value) is not int or type(value) is bool:
        raise ValueError(
            "stats progression field rejected: value_type_not_integer"
        )
    width = FIELD_KIND_WIDTH[field.kind]
    if value < 0 or value >= (1 << (8 * width)):
        raise ValueError(
            "stats progression field rejected: value_outside_field_width"
        )
    if field.kind == "u16":
        return legacy.u16tag(field.tag, value)
    if field.kind == "u32":
        return legacy.u32tag(field.tag, value)
    return legacy.qwordtag(field.tag, value)


def _encode_wstring(legacy: Any, value: Any) -> bytes:
    if type(value) is not str:
        raise ValueError(
            "stats progression field rejected: "
            "character_name_not_two_bytes_per_code_unit"
        )
    if not value:
        raise ValueError("stats progression field rejected: empty_character_name")
    try:
        raw = value.encode("utf-16le")
    except UnicodeEncodeError as exc:
        raise ValueError(
            "stats progression field rejected: "
            "character_name_not_two_bytes_per_code_unit"
        ) from exc
    if len(raw) != 2 * len(value):
        raise ValueError(
            "stats progression field rejected: "
            "character_name_not_two_bytes_per_code_unit"
        )
    return legacy.wstr_tag(value)


def _encode_block(
    legacy: Any, fields: tuple[AttrField, ...], values: dict[str, Any],
) -> tuple[int, bytes]:
    """Return ``(mask, body)`` for one block, fields in ascending bit order."""
    mask = 0
    body = b""
    for field in fields:
        if field.name not in values:
            continue
        mask |= field.mask_bit
        if field.kind == "wstring":
            body += _encode_wstring(legacy, values[field.name])
        else:
            body += _encode_scalar(legacy, field, values[field.name])
    return mask, body


# PF-HYPOTHESIS-LEDGER: HYP-PF-020 active
def encode_actor_attr(
    legacy: Any, identity_lo: int, identity_hi: int, fields: dict[str, Any],
) -> bytes:
    """Compose one sparse mask-gated ``ActorAttr`` body from named fields.

    The wire is the class chain base first: ``DBAttribute`` u8 mask + identity
    qword, then the ``BasicAttr`` u16 mask and its set fields, then the
    ``ActorAttr`` 64-bit mask, the u8 extra-group flag and its set fields.
    Within a block the fields go out in ascending mask-bit order, which is the
    serializer's emission order (module docstring).  Unknown names, wrong
    types, out-of-range values and unencodable names all raise ``ValueError``
    with the reason and produce no bytes.
    """
    _require_field_table()
    _require_ascending_gate_pins()
    if type(fields) is not dict:
        raise ValueError("stats progression field rejected: unknown_field")
    unknown = sorted(set(fields) - set(PROGRESSION_FIELDS))
    if unknown:
        raise ValueError(
            "stats progression field rejected: unknown_field " + unknown[0]
        )
    for value in (identity_lo, identity_hi):
        if type(value) is not int or type(value) is bool:
            raise ValueError(
                "stats progression field rejected: value_type_not_integer"
            )
        if value < 0 or value > 0xFFFFFFFF:
            raise ValueError(
                "stats progression field rejected: identity_outside_qword"
            )
    basic_mask, basic_body = _encode_block(legacy, BASIC_ATTR_FIELDS, fields)
    actor_mask, actor_body = _encode_block(legacy, ACTOR_ATTR_FIELDS, fields)
    if actor_mask >= ACTOR_ATTR_MASK_LOW_HALF_LIMIT:
        raise ValueError(
            "stats progression field rejected: "
            "mask_bit_in_unimplemented_high_half"
        )
    body = (
        legacy.u8tag(DB_ATTRIBUTE_MASK_TAG, DB_ATTRIBUTE_IDENTITY_BIT)
        + legacy.qwordtag(
            DB_ATTRIBUTE_IDENTITY_TAG,
            (identity_hi << 32) | identity_lo,
        )
        + legacy.u16tag(BASIC_ATTR_MASK_TAG, basic_mask)
        + basic_body
        + legacy.qwordtag(ACTOR_ATTR_MASK_TAG, actor_mask)
        + legacy.u8tag(ACTOR_ATTR_EXTRA_GROUP_TAG, ACTOR_ATTR_EXTRA_GROUP_VALUE)
        + actor_body
    )
    if decode_actor_attr(body) != (identity_lo, identity_hi, dict(fields)):
        raise RuntimeError("HYP-PF-020 encoder is not decoder-inverse")
    return body


# ---------------------------------------------------------------- decoder
def _read_scalar(body: bytes, cursor: int, field: AttrField) -> tuple[int, int]:
    width = FIELD_KIND_WIDTH[field.kind]
    if len(body) - cursor < 1 + width:
        raise ValueError("stats progression body rejected: truncated_field")
    if body[cursor] != field.tag:
        raise ValueError("stats progression body rejected: wrong_field_tag")
    cursor += 1
    value = int.from_bytes(body[cursor:cursor + width], "little")
    return value, cursor + width


def _read_wstring(body: bytes, cursor: int) -> tuple[str, int]:
    if len(body) - cursor < WSTRING_HEADER_SIZE:
        raise ValueError("stats progression body rejected: truncated_field")
    if body[cursor] != WSTRING_TAG:
        raise ValueError("stats progression body rejected: wrong_field_tag")
    byte_length = int.from_bytes(body[cursor + 1:cursor + 5], "little")
    cursor += WSTRING_HEADER_SIZE
    if byte_length % 2 or byte_length > len(body) - cursor:
        raise ValueError("stats progression body rejected: bad_wstring_length")
    raw = body[cursor:cursor + byte_length]
    cursor += byte_length
    try:
        text = raw.decode("utf-16-le")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "stats progression body rejected: "
            "character_name_not_two_bytes_per_code_unit"
        ) from exc
    if len(text) * 2 != byte_length:
        raise ValueError(
            "stats progression body rejected: "
            "character_name_not_two_bytes_per_code_unit"
        )
    return text, cursor


def _read_block(
    body: bytes, cursor: int, fields: tuple[AttrField, ...], mask: int,
    values: dict[str, Any],
) -> int:
    for field in fields:
        if not mask & field.mask_bit:
            continue
        if field.kind == "wstring":
            values[field.name], cursor = _read_wstring(body, cursor)
        else:
            values[field.name], cursor = _read_scalar(body, cursor, field)
        mask &= ~field.mask_bit
    if mask:
        raise ValueError("stats progression body rejected: unimplemented_mask_bit")
    return cursor


def decode_actor_attr(body: bytes) -> tuple[int, int, dict[str, Any]]:
    """Read one sparse ``ActorAttr`` body back into ``(lo, hi, fields)``.

    This is the inverse the encoder checks itself against; it accepts only the
    masks this lane implements, so a body carrying an unimplemented bit is a
    refusal rather than a partial parse.
    """
    if type(body) is not bytes and type(body) is not bytearray:
        raise ValueError("stats progression body rejected: truncated_field")
    body = bytes(body)
    if len(body) < 2 or body[0] != DB_ATTRIBUTE_MASK_TAG:
        raise ValueError("stats progression body rejected: wrong_field_tag")
    if body[1] != DB_ATTRIBUTE_IDENTITY_BIT:
        raise ValueError("stats progression body rejected: unimplemented_mask_bit")
    if len(body) < 11 or body[2] != DB_ATTRIBUTE_IDENTITY_TAG:
        raise ValueError("stats progression body rejected: wrong_field_tag")
    identity = int.from_bytes(body[3:11], "little")
    cursor = 11
    if len(body) - cursor < 3 or body[cursor] != BASIC_ATTR_MASK_TAG:
        raise ValueError("stats progression body rejected: wrong_field_tag")
    basic_mask = int.from_bytes(body[cursor + 1:cursor + 3], "little")
    cursor += 3
    values: dict[str, Any] = {}
    cursor = _read_block(body, cursor, BASIC_ATTR_FIELDS, basic_mask, values)
    if len(body) - cursor < 9 or body[cursor] != ACTOR_ATTR_MASK_TAG:
        raise ValueError("stats progression body rejected: wrong_field_tag")
    actor_mask = int.from_bytes(body[cursor + 1:cursor + 9], "little")
    cursor += 9
    if len(body) - cursor < 2 or body[cursor] != ACTOR_ATTR_EXTRA_GROUP_TAG:
        raise ValueError("stats progression body rejected: wrong_field_tag")
    if body[cursor + 1] != ACTOR_ATTR_EXTRA_GROUP_VALUE:
        raise ValueError("stats progression body rejected: unimplemented_mask_bit")
    cursor += 2
    cursor = _read_block(body, cursor, ACTOR_ATTR_FIELDS, actor_mask, values)
    if cursor != len(body):
        raise ValueError("stats progression body rejected: trailing_bytes")
    return identity & 0xFFFFFFFF, (identity >> 32) & 0xFFFFFFFF, values


# ---------------------------------------------------------------- composition
def stats_progression_baseline_fields(
    legacy: Any, actor: StatsProgressionActor,
) -> dict[str, Any]:
    """The field set player_wire already puts on the wire at start-game."""
    if type(actor) is not StatsProgressionActor:
        raise ValueError("stats progression actor is unavailable")
    return {
        "hp_current": STATS_BASELINE_HP_CURRENT,
        "hp_max": STATS_BASELINE_HP_MAX,
        "scene_id": actor.scene_id,
        "scene_sequence": actor.scene_sequence,
        "cash": legacy.V116_INITIAL_CASH,
        "character_name": actor.character_name,
    }


def stats_progression_step_fields(
    legacy: Any, actor: StatsProgressionActor, step_index: int,
) -> dict[str, Any]:
    """Baseline plus every progression change up to and including this step.

    Cumulative on purpose: the client's ActorAttr apply (v141's note on
    0x464F30) copies the complete object, so a field dropped from a later frame
    would be undone on screen rather than left alone.
    """
    if type(step_index) is not int or type(step_index) is bool:
        raise ValueError("stats progression step rejected: unknown_step_label")
    if step_index < 0 or step_index >= len(STATS_PROGRESSION_STEP_ORDER):
        raise ValueError("stats progression step rejected: unknown_step_label")
    fields = stats_progression_baseline_fields(legacy, actor)
    for label in STATS_PROGRESSION_STEP_ORDER[:step_index + 1]:
        fields.update(STATS_PROGRESSION_STEP_FIELDS[label])
    return fields


def _require_player_wire_crosscheck(
    legacy: Any, actor: StatsProgressionActor,
) -> None:
    """This generic encoder must reproduce the hand-written proven projection.

    ``player_wire.make_actor_attr_with_name`` has been in front of a real
    client since NAME-002 and is written field by field; this module is written
    mask by mask.  For the baseline field set they must be the same bytes.
    """
    if type(actor) is not StatsProgressionActor:
        raise ValueError("stats progression actor is unavailable")
    if legacy.V116_INITIAL_CASH != STATS_PROBE_CASH:
        raise RuntimeError("HYP-PF-020 baseline cash constant drift")
    composed = encode_actor_attr(
        legacy, actor.identity_lo, actor.identity_hi,
        stats_progression_baseline_fields(legacy, actor),
    )
    proven = make_actor_attr_with_name(
        legacy, actor.identity_lo, actor.identity_hi, actor.scene_id,
        actor.scene_sequence, actor.character_name,
    )
    if composed != proven:
        raise RuntimeError(
            "HYP-PF-020 encoder disagrees with the proven player_wire "
            "ActorAttr projection"
        )


def make_stats_progression_attr_payload(legacy: Any, body: bytes) -> bytes:
    """Wrap one ActrAttr body in the shared Attr-collection payload.

    Layout is the one v141's own UpdateAttrVital encoder uses: tag12/u16 count,
    tag12/u16 Attr id, tag14/u32 body length, then the body.
    """
    if legacy.ACTOR_ATTR != ACTOR_ATTR_ID:
        raise RuntimeError("HYP-PF-020 ActorAttr id drift against the frozen module")
    return (
        legacy.u16tag(0x12, STATS_ATTR_COLLECTION_COUNT)
        + legacy.u16tag(0x12, legacy.ACTOR_ATTR)
        + legacy.u32tag(0x14, len(body))
        + body
    )


# Ledger annotation for this lane is carried once, on encode_actor_attr above:
# the ledger verifier allows exactly one emitter annotation per (file, id).
def make_stats_progression_response(
    legacy: Any, actor: StatsProgressionActor, fields: dict[str, Any],
) -> tuple[bytes, bytes]:
    """Compose ``(pc, frame)`` for one UpdateAttrVital progression delta.

    The envelope is NOT rebuilt here: this reuses the frozen v141
    ``make_runtime_vitals`` one-vital GSCN_RunTimeProtocolRes v4 collection
    helper, the same envelope the already client-accepted lanes use, so the
    only new thing on the wire is the ActorAttr body.  Everything composed is
    re-checked structurally (ids, sizes, body at the fixed offset, body
    re-decodes to the requested fields) and cross-checked against the proven
    player_wire projection before a byte is returned.
    """
    if legacy.UPDATE_ATTR_VITAL != UPDATE_ATTR_VITAL_ID:
        raise RuntimeError(
            "HYP-PF-020 UpdateAttrVital id drift against the frozen module"
        )
    _require_step_plan()
    _require_player_wire_crosscheck(legacy, actor)
    body = encode_actor_attr(
        legacy, actor.identity_lo, actor.identity_hi, fields,
    )
    payload = make_stats_progression_attr_payload(legacy, body)
    pc, frame = legacy.make_runtime_vitals([
        (legacy.UPDATE_ATTR_VITAL, UPDATE_ATTR_VITAL_VERSION, payload),
    ])
    if len(pc) != len(payload) + STATS_PC_OVERHEAD:
        raise RuntimeError("HYP-PF-020 composed PC size drift")
    if pc[STATS_PC_PAYLOAD_OFFSET:STATS_PC_PAYLOAD_OFFSET + len(payload)] != payload:
        raise RuntimeError("HYP-PF-020 composed PC is not the encoded payload")
    if pc[STATS_PC_ATTR_BODY_OFFSET:STATS_PC_ATTR_BODY_OFFSET + len(body)] != body:
        raise RuntimeError("HYP-PF-020 composed PC is not the encoded Attr body")
    if decode_actor_attr(
        pc[STATS_PC_ATTR_BODY_OFFSET:STATS_PC_ATTR_BODY_OFFSET + len(body)]
    ) != (actor.identity_lo, actor.identity_hi, dict(fields)):
        raise RuntimeError("HYP-PF-020 composed PC does not re-decode")
    return pc, frame


def make_stats_progression_step_response(
    legacy: Any, actor: StatsProgressionActor, step_index: int,
) -> tuple[bytes, bytes]:
    """Compose one numbered frame of the pinned sweep, then drift-check pins."""
    fields = stats_progression_step_fields(legacy, actor, step_index)
    pc, frame = make_stats_progression_response(legacy, actor, fields)
    _require_pinned_composition(
        actor, STATS_PROGRESSION_STEP_ORDER[step_index], pc, frame,
    )
    return pc, frame


def _require_pinned_composition(
    actor: StatsProgressionActor, label: str, pc: bytes, frame: bytes,
) -> None:
    """Drift-check the one actor whose composition this lane pins."""
    if actor != STATS_PROBE_ACTOR:
        return
    if not STATS_PROBE_PC_SHA256:
        return
    if hashlib.sha256(pc).hexdigest().upper() != STATS_PROBE_PC_SHA256[label]:
        raise RuntimeError("HYP-PF-020 composed PC drift")
    if hashlib.sha256(frame).hexdigest().upper() != STATS_PROBE_FRAME_SHA256[label]:
        raise RuntimeError("HYP-PF-020 composed frame drift")
    if len(pc) != STATS_PROBE_PC_SIZE[label]:
        raise RuntimeError("HYP-PF-020 composed PC size pin drift")
    if len(frame) != STATS_PROBE_FRAME_SIZE[label]:
        raise RuntimeError("HYP-PF-020 composed frame size pin drift")


# ---------------------------------------------------------------- scenario gate
_PROFILE_XP_SWEEP = StatsProgressionHypothesisScenario(
    STATS_PROGRESSION_SCENARIO_ID,
    STATS_PROGRESSION_HYPOTHESIS_ID,
    STATS_PROGRESSION_STEP_ORDER,
    STATS_PROGRESSION_SPACING_SECONDS,
)


def _field_schema(fields: tuple[AttrField, ...]) -> dict[str, Any]:
    return {
        field.name: {
            "mask_bit": field.mask_bit,
            "object_offset": field.offset,
            "wire_tag": field.tag,
            "width": field.kind,
            "evidence": field.evidence,
        }
        for field in fields
    }


def _expected_sweep() -> dict[str, Any]:
    return {
        "schema": 1,
        "id": STATS_PROGRESSION_SCENARIO_ID,
        "test_only": True,
        "production_allowed": False,
        "hypothesis_id": STATS_PROGRESSION_HYPOTHESIS_ID,
        "entry": {
            "flow": "full_writable_character",
            "required_sequence": "selected_and_runtime_ready",
            "response_policy": (
                "compose_cumulative_update_attr_vital_progression_deltas_"
                "no_write_no_close"
            ),
        },
        "dispatch": {
            "trigger": "accepted_chat_input_frame_exact_ascii12_shape",
            "trigger_classifier": "classify_chat_input_attempt",
            "frames_per_accepted_request": len(STATS_PROGRESSION_STEP_ORDER),
            "step_order": list(STATS_PROGRESSION_STEP_ORDER),
            "step_fields": {
                label: dict(STATS_PROGRESSION_STEP_FIELDS[label])
                for label in STATS_PROGRESSION_STEP_ORDER
            },
            "cumulative": True,
            "spacing_seconds": STATS_PROGRESSION_SPACING_SECONDS,
            "first_frame_delay_seconds": STATS_PROGRESSION_FIRST_DELAY_SECONDS,
            "delay_semantics": "gap_before_each_send_on_a_cumulative_deadline",
            "action_label_prefix": STATS_PROGRESSION_ACTION_LABEL_PREFIX,
            "action_labels": [
                STATS_PROGRESSION_ACTION_LABEL_PREFIX + label
                for label in STATS_PROGRESSION_STEP_ORDER
            ],
            "one_shot": False,
            "socket_action": "none",
        },
        "wire": {
            "vital_id": UPDATE_ATTR_VITAL_ID,
            "vital_version": UPDATE_ATTR_VITAL_VERSION,
            "envelope": (
                "gscn_runtime_protocol_res_v4_one_vital_collection"
            ),
            "attr_id": ACTOR_ATTR_ID,
            "attr_collection": (
                "tag12_u16_count_tag12_u16_attr_id_tag14_u32_length_then_body"
            ),
            "block_order": [
                "dbattribute_mask_u8_then_identity_qword",
                "basicattr_mask_u16_then_gated_fields",
                "actorattr_mask_qword_then_extra_group_u8_then_gated_fields",
            ],
            "field_order_rule": "ascending_mask_bit_within_each_block",
            "extra_group_flag_value": ACTOR_ATTR_EXTRA_GROUP_VALUE,
            "basic_attr_fields": _field_schema(BASIC_ATTR_FIELDS),
            "actor_attr_fields": _field_schema(ACTOR_ATTR_FIELDS),
            "not_implemented_basic_attr_bits": list(
                NOT_IMPLEMENTED_BASIC_ATTR_BITS
            ),
            "not_implemented_note": NOT_IMPLEMENTED_ACTOR_ATTR_NOTE,
        },
        "probe": {
            "identity_lo": STATS_PROBE_IDENTITY_LO,
            "identity_hi": STATS_PROBE_IDENTITY_HI,
            "scene_id": STATS_PROBE_SCENE_ID,
            "scene_sequence": STATS_PROBE_SCENE_SEQUENCE,
            "character_name": STATS_PROBE_CHARACTER_NAME,
            "cash": STATS_PROBE_CASH,
            "hp_current": STATS_BASELINE_HP_CURRENT,
            "hp_max": STATS_BASELINE_HP_MAX,
            "baseline_crosscheck": (
                "encode_actor_attr_reproduces_player_wire_"
                "make_actor_attr_with_name_byte_for_byte"
            ),
            "per_step": {
                label: {
                    "attr_body_size": STATS_PROBE_ATTR_BODY_SIZE[label],
                    "attr_body_sha256": STATS_PROBE_ATTR_BODY_SHA256[label],
                    "pc_size": STATS_PROBE_PC_SIZE[label],
                    "pc_sha256": STATS_PROBE_PC_SHA256[label],
                    "frame_size": STATS_PROBE_FRAME_SIZE[label],
                    "frame_sha256": STATS_PROBE_FRAME_SHA256[label],
                }
                for label in STATS_PROGRESSION_STEP_ORDER
            },
        },
        "persisted_post_state": {
            "database_write": "none",
        },
        "capabilities": [
            "compose_sparse_mask_gated_actor_attr_bodies_from_named_fields",
            "emit_level_experience_and_five_ability_fields_through_0x309A",
            "reproduce_the_proven_player_wire_baseline_projection_byte_exactly",
            "decode_every_composed_body_back_to_the_requested_fields",
            "repeatable_sweep_per_session_no_state_change",
        ],
        "nonclaims": [
            "client_rendering_of_any_progression_field_pending_gt017",
            "any_wire_observation_of_a_progression_field_in_either_direction",
            "original_server_progression_rules_xp_curve_or_allocation_policy",
            "the_per_level_numbers_which_live_in_external_static_data",
            "sparse_delta_semantics_for_fields_a_frame_omits",
            "any_meaning_for_the_extra_group_flag_beyond_the_v141_value",
            "the_five_progression_verbs_which_have_no_encoder_here",
            "progression_persistence_or_database_write",
            "production_dispatch_wiring",
            "production_baseline_behavior",
        ],
    }


def _exact_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(
            _exact_equal(actual[key], value) for key, value in expected.items()
        )
    if type(expected) is list:
        return len(actual) == len(expected) and all(
            _exact_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def load_stats_progression_hypothesis_scenario(
    path: str | Path,
) -> StatsProgressionHypothesisScenario:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid stats progression hypothesis scenario") from exc
    if type(data) is not dict or data.get("id") != STATS_PROGRESSION_SCENARIO_ID:
        raise ValueError(
            "stats progression hypothesis scenario exceeds the exact allowlist"
        )
    if not _exact_equal(data, _expected_sweep()):
        raise ValueError(
            "stats progression hypothesis scenario exceeds the exact allowlist"
        )
    return require_stats_progression_hypothesis_scenario(_PROFILE_XP_SWEEP)


def require_stats_progression_hypothesis_scenario(
    value: Any,
) -> StatsProgressionHypothesisScenario:
    if (
        type(value) is not StatsProgressionHypothesisScenario
        or value != _PROFILE_XP_SWEEP
    ):
        raise ValueError(
            "stats progression hypothesis scenario object exceeds the allowlist"
        )
    _require_field_table()
    _require_ascending_gate_pins()
    _require_step_plan()
    return value
