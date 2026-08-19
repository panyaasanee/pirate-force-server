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

One tenant, two ledger entries
------------------------------
This file also hosts HP-DEATH-002 / HYP-PF-022 -- the LETHAL lane, at the very
bottom, behind its own scenario file, its own step plan and an unlock token.
It is the same encoder because the death predicate reads the same BasicAttr
block, but it is NOT the same claim and it is NOT the same bound: HYP-PF-020's
stop rule allows exactly the 23 fields listed above and nothing else, so bit
0x0080 stays in ``NOT_IMPLEMENTED_BASIC_ATTR_BITS`` and stays out of
``BASIC_ATTR_FIELDS`` / ``PROGRESSION_FIELDS`` forever.  With ``lethal=None`` --
which is every progression call site and the default everywhere -- the field
table is byte-for-byte the one described above and ``hp_death_timer`` is an
unknown field name like any other.  Read the block comment at the bottom of
this file before touching any of it.

One hypothesis, two death profiles (DYING-HOLD-001)
---------------------------------------------------
HYP-PF-022 ships TWO named step-plan profiles, not one, and the difference
between them is the point rather than an accident of configuration:

  * ``death_sweep`` is a DIAGNOSTIC.  It arms the timer, zeroes current HP and
    then puts the HP value back in the same sweep, so an attended tester is
    never left staring at a dead character and never has to restart the client.
    Its timer is 60.0 s, picked back when the deployed value of the client's
    ``DURATION_DYING`` was unknown and a wide margin was the only safe guess.
    Its pins, hashes and tests are load-bearing and are frozen: nothing in this
    file may move one byte of them.
  * ``dying_hold`` asks the question the diagnostic cannot ask -- "what does the
    client do when the dying countdown actually runs out?"  It arms the timer at
    20.0 s, zeroes current HP, and then STOPS.  There is no restoring frame, on
    purpose: the frame that restores HP is exactly the frame that would stop the
    answer from ever being observable.

20.0 is not a guess and not a margin.  It is the value compiled into the client
image for ``DURATION_DYING``: the int global at ``0x102249C``, bound by name at
``0x483476`` to the literal L"DURATION_DYING" at ``0xF118FC``, with exactly one
reader in the whole image, ``0x44A572``, which opens L"Main_Dead"
(``0xF0D738``) iff ``DURATION_DYING - 0.5 <= timer``.  A timer of 20.0
therefore clears that gate exactly, with nothing to spare and nothing invented.
The two predicates the countdown moves between are ``0x454AC0`` (HP == 0 and
timer > 0 -- the "dying" state; this module has always called its pin
``IS_DEAD_PLAYER_VA`` and that name is kept so no test moves) and ``0x454A70``
(HP == 0 and timer <= 0 -- the "timer elapsed" state).  The screen that offers
to put the character back on its feet is a DIFFERENT window, L"Common_Death"
(``0xF0D860``), opened out of ``CMyActor``'s own per-frame update once the
elapsed predicate is true.  Whether any of that appears on a real screen is
unobserved: no client in this project has ever been shown either window, and
this module implements, names and composes none of the client-side verbs that
window is wired to.

The step plan and the timer are therefore properties of a NAMED PROFILE, not of
this module.  Every symbol that used to be a module-level plan constant
(``HP_DEATH_TIMER_SECONDS``, ``HP_DEATH_STEPS``, ``HP_DEATH_STEP_ORDER``,
``HP_DEATH_STEP_FIELDS``, ``HP_DEATH_LETHAL_STEP_LABELS``,
``HP_DEATH_SCENARIO_ID``) still exists and still names the ``death_sweep``
profile byte for byte, so every existing caller and every existing test is
untouched.  ``_require_hp_death_step_plan`` now validates ONE profile at a time
and got STRICTER, not looser: a profile must declare ``ends_dead`` explicitly,
and the two branches are separately enforced -- ``ends_dead=False`` must end on
a restoring frame with hp > 0, ``ends_dead=True`` must end on the hp-zero frame,
must not contain a restoring frame at all, and must carry a timer that clears
``DURATION_DYING - 0.5``.

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
import struct
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
# ``f32`` is used by the HP-DEATH-002 lethal lane only (tag 0x2A, width 4); it
# is NOT reachable from the progression field tables above.
FIELD_KIND_WIDTH = {"u16": 2, "u32": 4, "qword": 8, "f32": 4}
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
    if field.kind == "f32":
        return _encode_death_timer(legacy, field, value)
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
    lethal: Any = None,
) -> bytes:
    """Compose one sparse mask-gated ``ActorAttr`` body from named fields.

    The wire is the class chain base first: ``DBAttribute`` u8 mask + identity
    qword, then the ``BasicAttr`` u16 mask and its set fields, then the
    ``ActorAttr`` 64-bit mask, the u8 extra-group flag and its set fields.
    Within a block the fields go out in ascending mask-bit order, which is the
    serializer's emission order (module docstring).  Unknown names, wrong
    types, out-of-range values and unencodable names all raise ``ValueError``
    with the reason and produce no bytes.

    ``lethal`` is the HP-DEATH-002 unlock token and is ``None`` on every
    progression path.  With ``None`` the field table is exactly the 23
    progression fields and the death-timer bit 0x0080 is an ``unknown_field``
    like any other unimplemented name; only the unlock token widens the table.
    """
    _require_field_table()
    _require_ascending_gate_pins()
    basic_fields, field_index = _resolve_field_tables(lethal)
    if type(fields) is not dict:
        raise ValueError("stats progression field rejected: unknown_field")
    unknown = sorted(set(fields) - set(field_index))
    if unknown:
        raise ValueError(
            "stats progression field rejected: unknown_field " + unknown[0]
        )
    if HP_DEATH_TIMER_NAME in fields and "hp_current" not in fields:
        raise ValueError(
            "hp death field rejected: death_timer_without_hp_current"
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
    basic_mask, basic_body = _encode_block(legacy, basic_fields, fields)
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
    if decode_actor_attr(body, lethal) != (
        identity_lo, identity_hi, dict(fields),
    ):
        raise RuntimeError("HYP-PF-020 encoder is not decoder-inverse")
    return body


# ---------------------------------------------------------------- decoder
def _read_scalar(body: bytes, cursor: int, field: AttrField) -> tuple[Any, int]:
    width = FIELD_KIND_WIDTH[field.kind]
    if len(body) - cursor < 1 + width:
        raise ValueError("stats progression body rejected: truncated_field")
    if body[cursor] != field.tag:
        raise ValueError("stats progression body rejected: wrong_field_tag")
    cursor += 1
    raw = body[cursor:cursor + width]
    if field.kind == "f32":
        return struct.unpack("<f", raw)[0], cursor + width
    value = int.from_bytes(raw, "little")
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


def decode_actor_attr(
    body: bytes, lethal: Any = None,
) -> tuple[int, int, dict[str, Any]]:
    """Read one sparse ``ActorAttr`` body back into ``(lo, hi, fields)``.

    This is the inverse the encoder checks itself against; it accepts only the
    masks this lane implements, so a body carrying an unimplemented bit is a
    refusal rather than a partial parse.  Without the HP-DEATH-002 unlock token
    the death-timer bit 0x0080 stays an ``unimplemented_mask_bit``, so a lethal
    body cannot even be read back on a progression path.
    """
    basic_fields, _field_index = _resolve_field_tables(lethal)
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
    cursor = _read_block(body, cursor, basic_fields, basic_mask, values)
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


# ============================================================================
# HP-DEATH-002 (HYP-PF-022) -- the lethal lane.
#
# READ THIS BEFORE TOUCHING ANYTHING BELOW.  Everything above composes numbers
# a player would like to see go up.  Everything below composes the two values
# that make the client decide the character is DEAD.  It is a separate ledger
# entry, a separate opt-in scenario file, a separate field table and a separate
# unlock token on purpose: HYP-PF-020's stop rule says "compose only the 23
# implemented fields, only behind the existing opt-in scenario file", and this
# lane is outside that bound in both directions.
#
# What HP-DEATH-001 proved byte-exactly (reports/PF_HP_DEATH001_*.md), and what
# this lane implements verbatim:
#
#   * There is NO death frame.  Every actor class derives death itself, in
#     ``IsDead`` at vtable +0x40 (``0x454AC0`` for CNetActor/CMyActor,
#     ``0x43BDA0`` for the NPC family): the f32 at ``attr+0x58`` must be
#     GREATER than the 0.0f constant at ``0xF0989C``, and then the u32 at
#     ``attr+0x44`` must be ZERO.
#   * ``+0x44`` is BasicAttr mask bit 0x0004 -- the field this module has always
#     emitted as ``hp_current``.  ``+0x58`` is BasicAttr mask bit 0x0080, f32,
#     wire tag 0x2A, gate pin 0x4657AE -- the one bit in the whole death
#     predicate that nothing in this repository has ever emitted.  It is listed
#     in ``NOT_IMPLEMENTED_BASIC_ATTR_BITS`` above and STAYS listed there: it is
#     not in ``BASIC_ATTR_FIELDS`` and it is not in ``PROGRESSION_FIELDS``.
#     Only ``LETHAL_BASIC_ATTR_FIELDS`` / ``LETHAL_FIELDS`` carry it, and they
#     are only reachable with the unlock token this file hands out exactly once,
#     from the hp-death scenario loader.
#
# What THIS lane added on top, from the same read-only client image, and which
# is why the timer value below is not a round number picked out of the air
# (all of it re-asserted as byte guards by tools/verify_hp_death_encoder.py):
#
#   * The local player's death window is a pure per-frame function of the two
#     values: ``CMyActor`` vtable +0x18 = 0x44E4E0 calls 0x44A540, which calls
#     ``IsDead`` and, if true, opens L"Main_Dead" (0xF0D738) -- but only behind
#     one more comparison at 0x44A572:
#         cvtsi2sd xmm1, dword [0x102249C]     ; the int the by-name binder at
#                                              ; 0x483476 binds to L"DURATION_DYING"
#         subsd    xmm1, [0xF092D0]            ; the double constant 0.5
#         cvtps2pd xmm0, xmm0                  ; the f32 at attr+0x58
#         comisd   xmm1, xmm0 ; ja  -> do NOT open
#     so the window opens iff ``DURATION_DYING - 0.5 <= timer``.  The value
#     compiled into the image at 0x102249C is 20.  A timer of "any positive
#     float" satisfies ``IsDead`` but can silently fail to open the window, so
#     this lane pins the timer ABOVE the in-image default with margin.
#   * The incoming attribute really does land on the object the death predicate
#     reads.  ``UpdateAttrVital``'s inbound handler 0x5F2400 takes each Attr in
#     the collection, asks it for its class id (vtable +0x10 = 0x464E40 =
#     ``mov ax,[0x10334A0]``, the once-init ActorAttr id), looks that class up
#     in ``[0x1032EC4]+0x130`` -- the local player's own attr collection -- and
#     calls the INCOMING attr's vtable +0x24, which for ActorAttr (vtable base
#     0xF0E7A0) is 0x464F30.  0x464F30 chains the BasicAttr copy 0x464B40,
#     which copies the whole block UNCONDITIONALLY -- ``8b 57 44 / 89 56 44``
#     for current HP and ``d9 47 58 / d9 5e 58`` for the death timer -- with no
#     mask consulted.  The actor caches that same pointer at ``+0x348`` and
#     registers it into ``+0x130`` in one breath at 0x4573CA, and ``+0x348`` is
#     exactly what ``GetAttr`` (0x44C630) returns to ``IsDead``.
#
# The one correction this lane makes to HP-DEATH-001's open debt B1: the chain
# is NOT ``UpdateAttrVital -> 0x4446F0``.  ``0x4446F0`` (attr apply + the
# dead-state sync 0x4437C0 that latches [actor+0x70] |= 0x200, spawns
# CActorTask_Dead and plays L"_F_DIE_000") has a full census of ONE direct
# call in the whole image (0x4566A7, the actor-entry update path) PLUS FOUR
# vtable +0x20 slots (the shared actor base and CNetNPC/CAvatarNPC/Pet -- see
# reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md sec 2). The
# conclusion survives the fuller count unchanged: ``UpdateAttrVital``'s own
# inbound handler (0x5F2400) contains zero +0x20 dispatch shapes across its
# whole extent, so it cannot reach any of those five entry points -- not this
# one.
# CONSEQUENCE, stated so nobody claims more than we have: a frame from this
# lane is expected to move the local player's HUD and open L"Main_Dead", and is
# NOT expected to play the death animation or push L"TargetIsDead".
#
# NOT CLAIMED: that any client has rendered any of it (that is GT-019, attended,
# not run); anything about coming back the other way -- HP-DEATH-001 enumerated
# the three verbs that carry a death token out of 519 registered classes, found
# that the player-facing one has no inbound handler at all (its slot is the
# shared no-op 0x710440, so a server echo of it changes nothing), and this lane
# implements NONE of them, has no encoder or decoder for any of them, and names
# none of them anywhere in src/; any death penalty, corpse or damage rule;
# anything about the ORIGINAL server; and any persistence -- HP has no write
# path in this project and this lane opens none.
# ============================================================================

HP_DEATH_TIMER_NAME = "hp_death_timer"
HP_DEATH_TIMER_MASK_BIT = 0x0080
HP_DEATH_TIMER_OFFSET = 0x58
HP_DEATH_TIMER_TAG = 0x2A
HP_DEATH_TIMER_WIDTH = 4
HP_DEATH_TIMER_GATE_PIN = 0x4657AE

# Client-binary VAs proven in HP-DEATH-001 and in this lane's own static pass;
# documentation-grade constants, never dereferenced.
IS_DEAD_PLAYER_VA = 0x454AC0            # CNetActor/CMyActor vtable +0x40
IS_DEAD_PLAYER_TIMER_ELAPSED_VA = 0x454A70   # ... vtable +0x3C
IS_DEAD_NPC_VA = 0x43BDA0               # CNetNPC/CAvatarNPC/Pet vtable +0x40
ZERO_FLOAT_CONSTANT_VA = 0xF0989C       # the 0.0f IsDead compares the timer to
MY_ACTOR_UPDATE_VA = 0x44E4E0           # CMyActor vtable +0x18
MAIN_DEAD_GATE_VA = 0x44A540            # the per-frame death-window gate
MAIN_DEAD_LITERAL_VA = 0xF0D738         # L"Main_Dead"
DURATION_DYING_GLOBAL_VA = 0x102249C    # the int bound to L"DURATION_DYING"
DURATION_DYING_NAME_VA = 0xF118FC       # that name literal
DURATION_DYING_HALF_SECOND_VA = 0xF092D0  # the 0.5 subtracted from it
UPDATE_ATTR_VITAL_ATTR_CLASS_LOOKUP_VA = 0x5F8C30  # the by-class-id lookup
ACTOR_ATTR_CLASS_ID_GETTER_VA = 0x464E40   # ActorAttr vtable +0x10
ACTOR_ATTR_VTABLE_VA = 0xF0E7A0
ACTOR_ATTR_COPY_VA = 0x464F30              # ActorAttr vtable +0x24
BASIC_ATTR_COPY_VA = 0x464B40              # BasicAttr vtable +0x24, unconditional
LOCAL_PLAYER_POINTER_VA = 0x1032EC4
LOCAL_PLAYER_ATTR_COLLECTION_OFFSET = 0x130
ACTOR_BOUND_ATTR_OFFSET = 0x348
ACTOR_ATTR_BIND_SITE_VA = 0x4573CA
DEAD_STATE_SYNC_VA = 0x4437C0
ATTR_APPLY_AND_DEAD_SYNC_VA = 0x4446F0
ATTR_APPLY_AND_DEAD_SYNC_ONLY_CALLER_VA = 0x4566A7

# DYING-HOLD-001 added these three, from the same read-only image and by the
# same method.  The first two are ALIASES for pins this module already carries:
# round 83's static pass established that 0x454AC0 is the "still dying" half of
# the predicate pair (HP == 0 and timer > 0) and 0x454A70 the "timer elapsed"
# half (HP == 0 and timer <= 0).  The original names are kept above so no pin,
# no test and no report reference moves; the aliases exist so a cold reader can
# tell the two states apart by name.
IS_DYING_PLAYER_VA = IS_DEAD_PLAYER_VA               # 0x454AC0
IS_DEAD_ELAPSED_PLAYER_VA = IS_DEAD_PLAYER_TIMER_ELAPSED_VA   # 0x454A70
# The window that follows the countdown is NOT L"Main_Dead".  It is a second,
# separate window opened from CMyActor's own per-frame update after the elapsed
# predicate turns true, and nothing in this project has ever seen it.
COMMON_DEATH_LITERAL_VA = 0xF0D860

# The value compiled into the image for DURATION_DYING, and the gate the death
# window is behind.  See the block comment above.
DURATION_DYING_IMAGE_DEFAULT = 20
DURATION_DYING_WINDOW_MARGIN = 0.5

HP_DEATH_TIMER_FIELD = AttrField(
    HP_DEATH_TIMER_NAME, "basic", HP_DEATH_TIMER_MASK_BIT, HP_DEATH_TIMER_OFFSET,
    HP_DEATH_TIMER_TAG, "f32",
    "STATS-PROG-001 s4 / HP-DEATH-001 s1 gate 0x4657AE "
    "`f6 03 80 74 0f 6a 04 8d 4e 58 51 6a 2a`; read by IsDead 0x454AC0",
)

# The lethal tables.  These are the ONLY tables that know the field exists.
LETHAL_BASIC_ATTR_FIELDS = _ordered(BASIC_ATTR_FIELDS + (HP_DEATH_TIMER_FIELD,))
LETHAL_FIELDS = {
    **PROGRESSION_FIELDS, HP_DEATH_TIMER_NAME: HP_DEATH_TIMER_FIELD,
}
LETHAL_BASIC_ATTR_GATE_PINS = {
    **BASIC_ATTR_GATE_PINS, HP_DEATH_TIMER_MASK_BIT: HP_DEATH_TIMER_GATE_PIN,
}

HP_DEATH_REJECTIONS = (
    "lethal_lane_locked",
    "death_timer_not_float",
    "death_timer_not_finite",
    "death_timer_not_positive",
    "death_timer_not_exactly_representable",
    "death_timer_below_the_death_window_gate",
    "death_timer_without_hp_current",
    "unknown_step_label",
    "unknown_step_profile",
)


@dataclass(frozen=True)
class HpDeathLethalUnlock:
    """The only key that widens the field table to include bit 0x0080.

    An instance is compared by IDENTITY, not by value: constructing an equal
    dataclass elsewhere does not unlock the lane.
    """

    scenario_id: str
    hypothesis_id: str


HP_DEATH_SCENARIO_ID = "hp_death_hypothesis_death_sweep"
HP_DEATH_HYPOTHESIS_ID = "HYP-PF-022"
# DYING-HOLD-001's second profile.  Same hypothesis, same ledger entry, same
# unlock token -- a different STEP PLAN, nothing more.
HP_DEATH_DYING_HOLD_SCENARIO_ID = "hp_death_hypothesis_dying_hold"
HP_DEATH_PROFILE_DEATH_SWEEP_NAME = "death_sweep"
HP_DEATH_PROFILE_DYING_HOLD_NAME = "dying_hold"
# There is exactly ONE token for the whole lane, and it is the death_sweep one
# by construction: adding a profile must not add a key.
_HP_DEATH_UNLOCK = HpDeathLethalUnlock(HP_DEATH_SCENARIO_ID, HP_DEATH_HYPOTHESIS_ID)


def require_hp_death_lethal_unlock(value: Any) -> HpDeathLethalUnlock:
    """Fail closed unless this is the one token the scenario loader hands out."""
    if value is not _HP_DEATH_UNLOCK:
        raise ValueError("hp death field rejected: lethal_lane_locked")
    return value


def _resolve_field_tables(lethal: Any) -> tuple[tuple[AttrField, ...], dict]:
    """``None`` means the 23 progression fields; the token means 24."""
    if lethal is None:
        return BASIC_ATTR_FIELDS, PROGRESSION_FIELDS
    require_hp_death_lethal_unlock(lethal)
    _require_lethal_field_table()
    return LETHAL_BASIC_ATTR_FIELDS, LETHAL_FIELDS


def _require_lethal_field_table() -> None:
    """The lethal table must be the progression table plus exactly one bit."""
    if HP_DEATH_TIMER_NAME in PROGRESSION_FIELDS:
        raise RuntimeError("HYP-PF-022 the death timer leaked into the base table")
    if HP_DEATH_TIMER_MASK_BIT in {field.mask_bit for field in BASIC_ATTR_FIELDS}:
        raise RuntimeError("HYP-PF-022 the death bit leaked into the base table")
    if HP_DEATH_TIMER_MASK_BIT not in NOT_IMPLEMENTED_BASIC_ATTR_BITS:
        raise RuntimeError(
            "HYP-PF-022 bit 0x0080 must stay declared not-implemented for "
            "HYP-PF-020"
        )
    if len(LETHAL_BASIC_ATTR_FIELDS) != len(BASIC_ATTR_FIELDS) + 1:
        raise RuntimeError("HYP-PF-022 lethal table is not base plus one field")
    if set(LETHAL_FIELDS) != set(PROGRESSION_FIELDS) | {HP_DEATH_TIMER_NAME}:
        raise RuntimeError("HYP-PF-022 lethal name table drift")
    if HP_DEATH_TIMER_FIELD.kind != "f32" or HP_DEATH_TIMER_FIELD.tag != 0x2A:
        raise RuntimeError("HYP-PF-022 the death timer is not the f32 tag 0x2A")
    # The whole emission-order argument again, on the widened table.
    addresses = [
        LETHAL_BASIC_ATTR_GATE_PINS[field.mask_bit]
        for field in LETHAL_BASIC_ATTR_FIELDS
        if field.mask_bit in LETHAL_BASIC_ATTR_GATE_PINS
    ]
    if addresses != sorted(addresses) or len(set(addresses)) != len(addresses):
        raise RuntimeError("HYP-PF-022 gate pin order contradicts mask order")


def _encode_death_timer(legacy: Any, field: AttrField, value: Any) -> bytes:
    """Encode the one float this project is allowed to put at BasicAttr +0x58.

    Every rejection here produces no bytes.  The value must be a real ``float``
    (``int`` and ``bool`` are refused so "1" can never become a timer by
    accident), finite, strictly greater than the 0.0f ``IsDead`` compares
    against, exactly representable in 32 bits so the wire value is the pinned
    value, and at least the death-window gate ``DURATION_DYING - 0.5`` computed
    from the value compiled into the client image.
    """
    if type(value) is not float:
        raise ValueError("hp death field rejected: death_timer_not_float")
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("hp death field rejected: death_timer_not_finite")
    if not value > 0.0:
        raise ValueError("hp death field rejected: death_timer_not_positive")
    encoded = legacy.f32tag(value)
    if (
        len(encoded) != 1 + HP_DEATH_TIMER_WIDTH
        or encoded[0] != field.tag
        or field.tag != HP_DEATH_TIMER_TAG
    ):
        raise RuntimeError("HYP-PF-022 f32 tag drift against the frozen module")
    if struct.unpack("<f", encoded[1:])[0] != value:
        raise ValueError(
            "hp death field rejected: death_timer_not_exactly_representable"
        )
    if value < DURATION_DYING_IMAGE_DEFAULT - DURATION_DYING_WINDOW_MARGIN:
        raise ValueError(
            "hp death field rejected: death_timer_below_the_death_window_gate"
        )
    return encoded


# ----------------------------------------------------------- the death plans
# TWO PROFILES, ONE HYPOTHESIS.  Read the "One hypothesis, two death profiles"
# section of the module docstring before touching either plan.  In one sentence:
# ``death_sweep`` is the diagnostic that ends ALIVE and whose 60.0 s timer is a
# margin taken when the deployed DURATION_DYING was unknown, and ``dying_hold``
# is the question that ends DEAD on purpose, with the 20.0 s the client image
# actually carries, because the thing it asks about only happens after the
# countdown has run all the way out.
#
# The timer this lane sends.  IsDead needs only "> 0.0f", but the local player's
# L"Main_Dead" window is behind `DURATION_DYING - 0.5 <= timer` and the value
# compiled into the image is 20.  60.0 clears that gate with a wide margin --
# it stays a plausible "seconds of dying remaining" while surviving a deployed
# configuration that raises DURATION_DYING -- and it is exactly representable in
# 32 bits, so the wire value is this value.  The margin is a DESIGN CHOICE on
# top of a byte-proven inequality, and is recorded as such in the ledger.
HP_DEATH_TIMER_SECONDS = 60.0
# The pair that makes IsDead true.  Zero is not a magic number here: it is the
# literal `cmp [attr+0x44], 0` at 0x454AFA.
HP_DEATH_HP_CURRENT = 0
# Recovery is one more frame with a non-zero current HP -- NOT a protocol verb:
# 0x44A540 closes the window as soon as IsDead is false, so restoring the HP
# value is the whole undo and the tester never has to restart the client.  It is
# the same 100 the baseline projection already carries.
HP_DEATH_HP_RESTORED = STATS_BASELINE_HP_CURRENT

HP_DEATH_STEPS = (
    # Byte-identical to the projection a real client has accepted since
    # NAME-002.  Nothing lethal, no new bit, no new tag.
    ("BASELINE", {}),
    # The new bit and the new tag WITHOUT the kill: HP is still full, so IsDead
    # is false and nothing should happen on screen.  This step exists to tell
    # "the client cannot parse a BasicAttr carrying bit 0x0080" apart from "the
    # client will not die" -- if the session survives this frame the wire shape
    # is accepted, whatever the next frame does.
    ("TIMER_ARMED", {HP_DEATH_TIMER_NAME: HP_DEATH_TIMER_SECONDS}),
    # The kill.  Cumulative, so this frame carries both halves of the predicate.
    ("HP_ZERO", {"hp_current": HP_DEATH_HP_CURRENT}),
    # Undo it in the same sweep, by restoring the attribute and nothing else.
    # Leaving a tester staring at a dead character is not an acceptable end
    # state for a diagnostic.
    ("HP_RESTORED", {"hp_current": HP_DEATH_HP_RESTORED}),
)
HP_DEATH_STEP_ORDER = tuple(label for label, _fields in HP_DEATH_STEPS)
HP_DEATH_STEP_FIELDS = {label: dict(fields) for label, fields in HP_DEATH_STEPS}
HP_DEATH_LETHAL_STEP_LABELS = ("HP_ZERO",)
# Wider than the progression sweep on purpose: an attended tester has to see
# the window open, read it, and still be looking when it closes again.
HP_DEATH_SPACING_SECONDS = 6.0
HP_DEATH_FIRST_DELAY_SECONDS = 0.0
HP_DEATH_ACTION_LABEL_PREFIX = "HYP_PF_022_HP_DEATH_"
HP_DEATH_RESPONSE_POLICY = (
    "compose_cumulative_update_attr_vital_death_deltas_no_write_no_close"
)
HP_DEATH_CAPABILITIES = (
    "emit_basicattr_mask_bit_0x0080_as_an_f32_death_timer",
    "compose_the_exact_pair_the_client_isdead_predicate_reads",
    "arm_the_timer_before_the_kill_and_restore_hp_in_the_same_sweep",
    "reproduce_the_proven_player_wire_baseline_projection_byte_exactly",
    "decode_every_composed_body_back_to_the_requested_fields",
)
HP_DEATH_NONCLAIMS = (
    "client_rendering_of_death_pending_gt019",
    "any_wire_observation_of_bit_0x0080_in_either_direction",
    "the_death_animation_or_target_panel_which_this_transport_"
    "cannot_reach",
    "any_spawn_point_or_marker_behavior",
    "any_death_penalty_corpse_or_damage_rule",
    "original_server_death_rules",
    "hp_persistence_or_database_write",
    "the_deployed_value_of_duration_dying",
    "production_dispatch_wiring",
    "production_baseline_behavior",
)

# ---------------------------------------------------- DYING-HOLD-001, profile 2
# 20.0, not 60.0, and not because 20 is rounder.  It is the int compiled into
# the image at DURATION_DYING_GLOBAL_VA (0x102249C), bound by name at 0x483476
# to the literal at 0xF118FC, with a single reader at 0x44A572 that opens
# L"Main_Dead" iff `DURATION_DYING - 0.5 <= timer`.  20.0 clears that gate
# exactly -- 20.0 >= 19.5 -- so this profile sends the client's own number back
# to it and nothing else.  It is exactly representable in 32 bits, so the wire
# value is this value.
HP_DEATH_DYING_HOLD_TIMER_SECONDS = 20.0

HP_DEATH_DYING_HOLD_STEPS = (
    # Byte-identical to the death_sweep baseline, and therefore to the
    # player_wire projection a real client has accepted since NAME-002.  The
    # tests assert that identity rather than assuming it.
    ("BASELINE", {}),
    # The same armed frame as death_sweep except for the four f32 bytes of the
    # timer itself -- also asserted, not assumed.
    ("TIMER_ARMED", {HP_DEATH_TIMER_NAME: HP_DEATH_DYING_HOLD_TIMER_SECONDS}),
    # The kill, and the LAST frame.  There is deliberately no restoring step:
    # the whole question this profile asks is what the client does once the
    # countdown reaches zero, and a restoring frame is precisely the thing that
    # would stop that from ever being observable.
    ("HP_ZERO", {"hp_current": HP_DEATH_HP_CURRENT}),
)
HP_DEATH_DYING_HOLD_STEP_ORDER = tuple(
    label for label, _fields in HP_DEATH_DYING_HOLD_STEPS
)
HP_DEATH_DYING_HOLD_STEP_FIELDS = {
    label: dict(fields) for label, fields in HP_DEATH_DYING_HOLD_STEPS
}
HP_DEATH_DYING_HOLD_LETHAL_STEP_LABELS = ("HP_ZERO",)
HP_DEATH_DYING_HOLD_SPACING_SECONDS = 6.0
HP_DEATH_DYING_HOLD_FIRST_DELAY_SECONDS = 0.0
HP_DEATH_DYING_HOLD_ACTION_LABEL_PREFIX = "HYP_PF_022_DYING_HOLD_"
HP_DEATH_DYING_HOLD_RESPONSE_POLICY = (
    "compose_cumulative_update_attr_vital_dying_hold_deltas_no_write_no_close"
)
HP_DEATH_DYING_HOLD_CAPABILITIES = (
    "emit_basicattr_mask_bit_0x0080_as_an_f32_death_timer",
    "compose_the_exact_pair_the_client_isdead_predicate_reads",
    "arm_the_timer_at_the_duration_dying_value_compiled_into_the_image",
    "hold_the_character_dead_so_the_countdown_can_run_to_zero",
    "reproduce_the_proven_player_wire_baseline_projection_byte_exactly",
    "decode_every_composed_body_back_to_the_requested_fields",
)
HP_DEATH_DYING_HOLD_NONCLAIMS = (
    # The four this profile is REQUIRED to state, first and in plain words.
    "no_client_has_ever_been_shown_one_byte_of_this_profile",
    "the_common_death_window_has_never_been_observed_by_this_project",
    "no_persistence_hp_has_no_write_path_and_this_lane_opens_none",
    "not_a_rule_of_the_original_server_which_this_project_cannot_read",
    # And the ones death_sweep already carries, which stay true here.
    "client_rendering_of_death_pending_gt019",
    "any_wire_observation_of_bit_0x0080_in_either_direction",
    "the_death_animation_or_target_panel_which_this_transport_"
    "cannot_reach",
    "any_spawn_point_or_marker_behavior",
    "any_death_penalty_corpse_or_damage_rule",
    "the_deployed_value_of_duration_dying",
    "what_the_client_does_when_the_countdown_reaches_zero",
    "any_recovery_path_out_of_the_state_this_profile_leaves_behind",
    "production_dispatch_wiring",
    "production_baseline_behavior",
)


@dataclass(frozen=True)
class HpDeathHypothesisScenario:
    """One allowlisted hp-death scenario object.

    ``ends_dead`` and ``profile_name`` carry defaults so the five-positional
    construction every existing caller and test uses keeps working and keeps
    meaning the ``death_sweep`` profile.  Neither default is a fallback the
    loader relies on: the two real objects below name both explicitly.
    """

    scenario_id: str
    hypothesis_id: str
    step_order: tuple[str, ...]
    spacing_seconds: float
    death_timer_seconds: float
    ends_dead: bool = False
    profile_name: str = HP_DEATH_PROFILE_DEATH_SWEEP_NAME


def _require_hp_death_step_plan(profile: Any = None) -> None:
    """Validate ONE named step plan.  Stricter than the single-plan version.

    Every rule the original module-level validator enforced is still enforced,
    and none of them was relaxed to make room for the second profile:

      * open with a BASELINE that adds no field;
      * no duplicate label, and every later step changes exactly one field
        that the lethal table knows;
      * arm the timer BEFORE the kill -- a frame that zeroes HP while the timer
        is still absent leaves the client in a state neither half of the
        predicate pair covers, and this lane refuses to be what produced it;
      * exactly one lethal step, and it is the one that zeroes current HP;
      * the armed step carries the profile's own declared timer, as a float.

    What is NEW is that the end state is no longer assumed.  A profile has to
    say which of the two it is, in ``ends_dead``, and each answer is then
    enforced separately:

      * ``ends_dead=False`` -- the diagnostic contract, unchanged: the plan must
        contain a restoring step, it must come after the kill, it must set a
        positive current HP, and it must be the LAST step.
      * ``ends_dead=True`` -- the dying-hold contract: the plan must NOT contain
        a restoring step at all, the last step must be the kill, and the timer
        must clear the client's own death-window gate
        ``DURATION_DYING - 0.5``, because a countdown the window never opens
        for cannot be watched running out.
    """
    if profile is None:
        profile = HP_DEATH_PROFILE_DEATH_SWEEP
    if type(profile) is not HpDeathStepProfile:
        raise RuntimeError("HYP-PF-022 step plan is not a named profile")
    if type(profile.ends_dead) is not bool:
        raise RuntimeError("HYP-PF-022 a profile must declare ends_dead")
    order = profile.step_order
    plan = profile.step_fields
    if not order or order[0] != "BASELINE":
        raise RuntimeError("HYP-PF-022 the sweep must open with the baseline")
    if plan["BASELINE"]:
        raise RuntimeError("HYP-PF-022 the baseline must add no lethal field")
    if len(set(order)) != len(order):
        raise RuntimeError("HYP-PF-022 duplicate step label")
    for label in order[1:]:
        added = plan[label]
        if len(added) != 1:
            raise RuntimeError("HYP-PF-022 a step must change exactly one field")
        for name in added:
            if name not in LETHAL_FIELDS:
                raise RuntimeError("HYP-PF-022 step names an unknown field")
    if "TIMER_ARMED" not in order or "HP_ZERO" not in order:
        raise RuntimeError("HYP-PF-022 the sweep order is not arm/kill/restore")
    armed = order.index("TIMER_ARMED")
    killed = order.index("HP_ZERO")
    if not armed < killed:
        raise RuntimeError("HYP-PF-022 the sweep order is not arm/kill/restore")
    if plan["HP_ZERO"].get("hp_current") != 0:
        raise RuntimeError("HYP-PF-022 the lethal step does not zero current HP")
    if profile.lethal_step_labels != ("HP_ZERO",):
        raise RuntimeError("HYP-PF-022 exactly one step may be lethal")
    timer = plan["TIMER_ARMED"].get(HP_DEATH_TIMER_NAME)
    if type(timer) is not float or timer != profile.timer_seconds:
        raise RuntimeError("HYP-PF-022 the armed step is not the profile timer")
    if profile.ends_dead:
        if "HP_RESTORED" in order:
            raise RuntimeError(
                "HYP-PF-022 a profile that ends dead must carry no restore step"
            )
        if order[-1] != "HP_ZERO":
            raise RuntimeError(
                "HYP-PF-022 a profile that ends dead must end on the kill frame"
            )
        if timer < DURATION_DYING_IMAGE_DEFAULT - DURATION_DYING_WINDOW_MARGIN:
            raise RuntimeError(
                "HYP-PF-022 a profile that ends dead must clear the "
                "death-window gate"
            )
        return
    if "HP_RESTORED" not in order:
        raise RuntimeError("HYP-PF-022 the sweep does not end alive")
    restored = order.index("HP_RESTORED")
    if not killed < restored:
        raise RuntimeError("HYP-PF-022 the sweep order is not arm/kill/restore")
    if plan["HP_RESTORED"].get("hp_current", 0) <= 0:
        raise RuntimeError("HYP-PF-022 the sweep does not end alive")
    if order[-1] != "HP_RESTORED":
        raise RuntimeError("HYP-PF-022 the sweep must end on the hp-restored frame")


def hp_death_step_fields(
    legacy: Any, actor: StatsProgressionActor, step_index: int,
    profile: Any = None,
) -> dict[str, Any]:
    """Baseline plus every death change up to and including this step.

    Cumulative for the same reason the progression sweep is, and here the
    reason is byte-proven twice over: BasicAttr's copy 0x464B40 copies the whole
    block with no mask consulted, so a field dropped from a later frame is not
    left alone -- it is overwritten with whatever the incoming object holds.

    ``profile`` defaults to ``death_sweep``, so every existing caller keeps the
    plan it has always had.
    """
    profile = _resolve_hp_death_profile(profile)
    order = profile.step_order
    plan = profile.step_fields
    if type(step_index) is not int or type(step_index) is bool:
        raise ValueError("hp death step rejected: unknown_step_label")
    if step_index < 0 or step_index >= len(order):
        raise ValueError("hp death step rejected: unknown_step_label")
    fields = stats_progression_baseline_fields(legacy, actor)
    for label in order[:step_index + 1]:
        fields.update(plan[label])
    return fields


def hp_death_step_is_lethal(step_index: int, profile: Any = None) -> bool:
    """True only for the frame on which the client should derive death."""
    profile = _resolve_hp_death_profile(profile)
    plan = profile.step_fields
    fields = {}
    for label in profile.step_order[:step_index + 1]:
        fields.update(plan[label])
    return (
        fields.get("hp_current") == 0
        and float(fields.get(HP_DEATH_TIMER_NAME, 0.0)) > 0.0
    )


# ---------------------------------------------------------------- death pins
# Same probe actor as the progression sweep, on purpose: the BASELINE frame of
# this sweep is then byte-identical to HYP-PF-020's BASELINE frame and to the
# player_wire projection a real client has been accepting since NAME-002, which
# is what makes the DIFFERENCE between the frames the only thing under test.
# Every value below is a sha256 of bytes this encoder produced, recomputed live
# by tools/verify_hp_death_encoder.py, never a value copied in.
HP_DEATH_PROBE_ACTOR = STATS_PROBE_ACTOR
HP_DEATH_PROBE_ATTR_BODY_SHA256 = {
    "BASELINE": (
        "479ED77DFA554F89AAB02E884608EC53BAEC9E213F85548AF9CCD291BCC896C4"
    ),
    "TIMER_ARMED": (
        "903F2D45EAB009DD2D1AD9C14A00D0027F428BB98076560E5C5F22534B53A8FA"
    ),
    "HP_ZERO": (
        "C718DFC077AEC9C93432F26C81A6AA08D2BD8616F5C4424D1DC2DAC668576469"
    ),
    "HP_RESTORED": (
        "903F2D45EAB009DD2D1AD9C14A00D0027F428BB98076560E5C5F22534B53A8FA"
    ),
}
HP_DEATH_PROBE_PC_SHA256 = {
    "BASELINE": (
        "DB3CE0B5D14196181EF9EA26A0D435E0489212634334CB562F840E368B5F0049"
    ),
    "TIMER_ARMED": (
        "B7BE99B81FDBBC88D08599C6504328B99E55F40B3877856FC6D7BA0F7047E97F"
    ),
    "HP_ZERO": (
        "A1990A937B4A1A8FFAB2D1D8F29004489C260A7829051F14CADDB0D619A16717"
    ),
    "HP_RESTORED": (
        "B7BE99B81FDBBC88D08599C6504328B99E55F40B3877856FC6D7BA0F7047E97F"
    ),
}
HP_DEATH_PROBE_FRAME_SHA256 = {
    "BASELINE": (
        "04E2B40152B633A48C84713B1C24A2910B7AB84E178E268094C0D10B179D9FBC"
    ),
    "TIMER_ARMED": (
        "FF43A6FC590A88CCC9B548AE694FA9EDAFE25051FB3AB9E61041BA4142276B04"
    ),
    "HP_ZERO": (
        "F6DB8ACA8C80DBFCED2FBF12BC8532C0A0865818D88D7AF4B4CAD06931C58A35"
    ),
    "HP_RESTORED": (
        "FF43A6FC590A88CCC9B548AE694FA9EDAFE25051FB3AB9E61041BA4142276B04"
    ),
}
HP_DEATH_PROBE_ATTR_BODY_SIZE = {
    "BASELINE": 73, "TIMER_ARMED": 78, "HP_ZERO": 78, "HP_RESTORED": 78,
}
HP_DEATH_PROBE_PC_SIZE = {
    "BASELINE": 106, "TIMER_ARMED": 111, "HP_ZERO": 111, "HP_RESTORED": 111,
}
HP_DEATH_PROBE_FRAME_SIZE = {
    "BASELINE": 117, "TIMER_ARMED": 122, "HP_ZERO": 122, "HP_RESTORED": 122,
}
# The masks the four frames carry, so a reader never has to trust prose about
# which bits went out.  0x030C is the baseline (hp cur/max, scene id, scene
# sequence) and 0x038C is that plus the death bit 0x0080.
HP_DEATH_PROBE_BASIC_MASK = {
    "BASELINE": 0x030C, "TIMER_ARMED": 0x038C,
    "HP_ZERO": 0x038C, "HP_RESTORED": 0x038C,
}
# The exact five bytes bit 0x0080 puts on the wire: tag 0x2A + 60.0f LE.
HP_DEATH_TIMER_WIRE_BYTES = bytes.fromhex("2a00007042")

# ------------------------------------------------- DYING-HOLD-001 death pins
# Same probe actor again.  BASELINE is byte-identical to death_sweep's BASELINE
# (and therefore to the player_wire projection), TIMER_ARMED differs from
# death_sweep's TIMER_ARMED in exactly the four f32 bytes of the timer, and
# HP_ZERO is the last frame this profile sends.  Both statements are asserted by
# tests, not left as prose.  Every value below was recomputed from bytes the
# encoder produced; none of it was copied from the death_sweep table.
HP_DEATH_DYING_HOLD_PROBE_ATTR_BODY_SHA256 = {
    "BASELINE": (
        "479ED77DFA554F89AAB02E884608EC53BAEC9E213F85548AF9CCD291BCC896C4"
    ),
    "TIMER_ARMED": (
        "877A7E0AB45E8BC144AD509D78D38A25C25E1524F4AE795336211700B29725EB"
    ),
    "HP_ZERO": (
        "857AC3F2D1CFBCB717FAC62B27DE78617344D4E2A7D74BB00DE6FD2F8E488873"
    ),
}
HP_DEATH_DYING_HOLD_PROBE_PC_SHA256 = {
    "BASELINE": (
        "DB3CE0B5D14196181EF9EA26A0D435E0489212634334CB562F840E368B5F0049"
    ),
    "TIMER_ARMED": (
        "F08E53D3D89DC8ABA169277BA5D9230A539D221F78F7881CB7D69C6E80917932"
    ),
    "HP_ZERO": (
        "1099931C80FAA0394BE1DADCA587ED890A04ED7C72118F1888D6708CF9967E44"
    ),
}
HP_DEATH_DYING_HOLD_PROBE_FRAME_SHA256 = {
    "BASELINE": (
        "04E2B40152B633A48C84713B1C24A2910B7AB84E178E268094C0D10B179D9FBC"
    ),
    "TIMER_ARMED": (
        "01E1B9E638BAD578D5E2865BEC2F14F05FF8645A679B48AF968B6ECFF82F611F"
    ),
    "HP_ZERO": (
        "77E98AD69434C112FD4D7B6F29B04DCCE306B42187E92B3BDB91383F0C1B200D"
    ),
}
HP_DEATH_DYING_HOLD_PROBE_ATTR_BODY_SIZE = {
    "BASELINE": 73, "TIMER_ARMED": 78, "HP_ZERO": 78,
}
HP_DEATH_DYING_HOLD_PROBE_PC_SIZE = {
    "BASELINE": 106, "TIMER_ARMED": 111, "HP_ZERO": 111,
}
HP_DEATH_DYING_HOLD_PROBE_FRAME_SIZE = {
    "BASELINE": 117, "TIMER_ARMED": 122, "HP_ZERO": 122,
}
HP_DEATH_DYING_HOLD_PROBE_BASIC_MASK = {
    "BASELINE": 0x030C, "TIMER_ARMED": 0x038C, "HP_ZERO": 0x038C,
}
# Tag 0x2A + 20.0f little-endian.  The four value bytes are the ONLY difference
# between this profile's armed frame and death_sweep's.
HP_DEATH_DYING_HOLD_TIMER_WIRE_BYTES = bytes.fromhex("2a0000a041")


# ------------------------------------------------------------ named profiles
@dataclass(frozen=True)
class HpDeathStepProfile:
    """One named hp-death step plan, with its own pins and its own end state.

    A profile is the unit HYP-PF-022 varies.  Everything that used to be a
    module-level plan constant lives here now, including ``ends_dead``, which a
    profile must state OUT LOUD -- the validator refuses to infer it from the
    step list, because inferring it is exactly how a plan that silently stopped
    restoring HP would get past a reviewer.
    """

    name: str
    scenario_id: str
    timer_seconds: float
    steps: tuple[tuple[str, dict[str, Any]], ...]
    lethal_step_labels: tuple[str, ...]
    ends_dead: bool
    spacing_seconds: float
    first_delay_seconds: float
    action_label_prefix: str
    response_policy: str
    capabilities: tuple[str, ...]
    nonclaims: tuple[str, ...]
    probe_attr_body_sha256: dict
    probe_pc_sha256: dict
    probe_frame_sha256: dict
    probe_attr_body_size: dict
    probe_pc_size: dict
    probe_frame_size: dict
    probe_basic_mask: dict
    timer_wire_bytes: bytes

    @property
    def step_order(self) -> tuple[str, ...]:
        return tuple(label for label, _fields in self.steps)

    @property
    def step_fields(self) -> dict:
        return {label: dict(fields) for label, fields in self.steps}


HP_DEATH_PROFILE_DEATH_SWEEP = HpDeathStepProfile(
    HP_DEATH_PROFILE_DEATH_SWEEP_NAME,
    HP_DEATH_SCENARIO_ID,
    HP_DEATH_TIMER_SECONDS,
    HP_DEATH_STEPS,
    HP_DEATH_LETHAL_STEP_LABELS,
    False,
    HP_DEATH_SPACING_SECONDS,
    HP_DEATH_FIRST_DELAY_SECONDS,
    HP_DEATH_ACTION_LABEL_PREFIX,
    HP_DEATH_RESPONSE_POLICY,
    HP_DEATH_CAPABILITIES,
    HP_DEATH_NONCLAIMS,
    HP_DEATH_PROBE_ATTR_BODY_SHA256,
    HP_DEATH_PROBE_PC_SHA256,
    HP_DEATH_PROBE_FRAME_SHA256,
    HP_DEATH_PROBE_ATTR_BODY_SIZE,
    HP_DEATH_PROBE_PC_SIZE,
    HP_DEATH_PROBE_FRAME_SIZE,
    HP_DEATH_PROBE_BASIC_MASK,
    HP_DEATH_TIMER_WIRE_BYTES,
)
HP_DEATH_PROFILE_DYING_HOLD = HpDeathStepProfile(
    HP_DEATH_PROFILE_DYING_HOLD_NAME,
    HP_DEATH_DYING_HOLD_SCENARIO_ID,
    HP_DEATH_DYING_HOLD_TIMER_SECONDS,
    HP_DEATH_DYING_HOLD_STEPS,
    HP_DEATH_DYING_HOLD_LETHAL_STEP_LABELS,
    True,
    HP_DEATH_DYING_HOLD_SPACING_SECONDS,
    HP_DEATH_DYING_HOLD_FIRST_DELAY_SECONDS,
    HP_DEATH_DYING_HOLD_ACTION_LABEL_PREFIX,
    HP_DEATH_DYING_HOLD_RESPONSE_POLICY,
    HP_DEATH_DYING_HOLD_CAPABILITIES,
    HP_DEATH_DYING_HOLD_NONCLAIMS,
    HP_DEATH_DYING_HOLD_PROBE_ATTR_BODY_SHA256,
    HP_DEATH_DYING_HOLD_PROBE_PC_SHA256,
    HP_DEATH_DYING_HOLD_PROBE_FRAME_SHA256,
    HP_DEATH_DYING_HOLD_PROBE_ATTR_BODY_SIZE,
    HP_DEATH_DYING_HOLD_PROBE_PC_SIZE,
    HP_DEATH_DYING_HOLD_PROBE_FRAME_SIZE,
    HP_DEATH_DYING_HOLD_PROBE_BASIC_MASK,
    HP_DEATH_DYING_HOLD_TIMER_WIRE_BYTES,
)
HP_DEATH_PROFILES = {
    HP_DEATH_PROFILE_DEATH_SWEEP_NAME: HP_DEATH_PROFILE_DEATH_SWEEP,
    HP_DEATH_PROFILE_DYING_HOLD_NAME: HP_DEATH_PROFILE_DYING_HOLD,
}


def _resolve_hp_death_profile(profile: Any) -> HpDeathStepProfile:
    """``None`` means ``death_sweep``; anything unregistered is refused.

    Identity, not equality: a profile assembled elsewhere that happens to
    compare equal is still not one of the two this module ships, and composing
    against it would compose bytes nobody reviewed.
    """
    if profile is None:
        return HP_DEATH_PROFILE_DEATH_SWEEP
    for candidate in HP_DEATH_PROFILES.values():
        if profile is candidate:
            return candidate
    raise ValueError("hp death step rejected: unknown_step_profile")


def _require_pinned_death_composition(
    actor: StatsProgressionActor, label: str, body: bytes, pc: bytes,
    frame: bytes, profile: Any = None,
) -> None:
    profile = _resolve_hp_death_profile(profile)
    if actor != HP_DEATH_PROBE_ACTOR or not profile.probe_pc_sha256:
        return
    if (
        hashlib.sha256(body).hexdigest().upper()
        != profile.probe_attr_body_sha256[label]
    ):
        raise RuntimeError("HYP-PF-022 composed Attr body drift")
    if hashlib.sha256(pc).hexdigest().upper() != profile.probe_pc_sha256[label]:
        raise RuntimeError("HYP-PF-022 composed PC drift")
    if (
        hashlib.sha256(frame).hexdigest().upper()
        != profile.probe_frame_sha256[label]
    ):
        raise RuntimeError("HYP-PF-022 composed frame drift")
    if (
        len(body) != profile.probe_attr_body_size[label]
        or len(pc) != profile.probe_pc_size[label]
        or len(frame) != profile.probe_frame_size[label]
    ):
        raise RuntimeError("HYP-PF-022 composed size pin drift")


# PF-HYPOTHESIS-LEDGER: HYP-PF-022 active
def make_hp_death_response(
    legacy: Any, actor: StatsProgressionActor, fields: dict[str, Any],
    lethal: Any, profile: Any = None,
) -> tuple[bytes, bytes]:
    """Compose ``(pc, frame)`` for one UpdateAttrVital frame of the death sweep.

    Same envelope, same Attr collection and same encoder as the progression
    lane -- the only new thing on the wire is one f32 field at BasicAttr +0x58,
    and it is only reachable with the unlock token.  Before any byte is
    returned this re-runs the whole HYP-PF-020 chain of self-checks (the frozen
    module's ids, the ascending gate pins, the byte-for-byte player_wire
    cross-check on the baseline projection) plus the lethal table and step-plan
    guards, and re-decodes the composed PC back to the requested field set.

    ``profile`` selects the step plan whose contract is enforced; it defaults to
    ``death_sweep``, and the unlock token is the same one for every profile --
    a second plan must not mean a second key.
    """
    require_hp_death_lethal_unlock(lethal)
    profile = _resolve_hp_death_profile(profile)
    if legacy.UPDATE_ATTR_VITAL != UPDATE_ATTR_VITAL_ID:
        raise RuntimeError(
            "HYP-PF-022 UpdateAttrVital id drift against the frozen module"
        )
    _require_lethal_field_table()
    _require_hp_death_step_plan(profile)
    _require_player_wire_crosscheck(legacy, actor)
    body = encode_actor_attr(
        legacy, actor.identity_lo, actor.identity_hi, fields, lethal,
    )
    payload = make_stats_progression_attr_payload(legacy, body)
    pc, frame = legacy.make_runtime_vitals([
        (legacy.UPDATE_ATTR_VITAL, UPDATE_ATTR_VITAL_VERSION, payload),
    ])
    if len(pc) != len(payload) + STATS_PC_OVERHEAD:
        raise RuntimeError("HYP-PF-022 composed PC size drift")
    if pc[STATS_PC_PAYLOAD_OFFSET:STATS_PC_PAYLOAD_OFFSET + len(payload)] != payload:
        raise RuntimeError("HYP-PF-022 composed PC is not the encoded payload")
    if pc[STATS_PC_ATTR_BODY_OFFSET:STATS_PC_ATTR_BODY_OFFSET + len(body)] != body:
        raise RuntimeError("HYP-PF-022 composed PC is not the encoded Attr body")
    if decode_actor_attr(
        pc[STATS_PC_ATTR_BODY_OFFSET:STATS_PC_ATTR_BODY_OFFSET + len(body)],
        lethal,
    ) != (actor.identity_lo, actor.identity_hi, dict(fields)):
        raise RuntimeError("HYP-PF-022 composed PC does not re-decode")
    return pc, frame


def make_hp_death_step_response(
    legacy: Any, actor: StatsProgressionActor, step_index: int, lethal: Any,
    profile: Any = None,
) -> tuple[bytes, bytes]:
    """Compose one numbered frame of the pinned death sweep, then drift-check."""
    require_hp_death_lethal_unlock(lethal)
    profile = _resolve_hp_death_profile(profile)
    fields = hp_death_step_fields(legacy, actor, step_index, profile)
    pc, frame = make_hp_death_response(legacy, actor, fields, lethal, profile)
    label = profile.step_order[step_index]
    _require_pinned_death_composition(
        actor, label, hp_death_attr_body(pc), pc, frame, profile,
    )
    return pc, frame


def hp_death_attr_body(pc: bytes) -> bytes:
    """Slice the ``ActorAttr`` body out of a composed PC by its own length tag.

    The Attr collection carries ``tag14/u32 body length`` immediately before the
    body, so the body is read out of the frame rather than assumed: a caller
    that slices to the end of the PC picks up the envelope's own tail bytes and
    every hash it computes is wrong.
    """
    length_tag_offset = STATS_PC_PAYLOAD_OFFSET + 6
    if len(pc) < length_tag_offset + 5 or pc[length_tag_offset] != 0x14:
        raise ValueError("hp death body rejected: wrong_field_tag")
    length = int.from_bytes(
        pc[length_tag_offset + 1:length_tag_offset + 5], "little",
    )
    end = STATS_PC_ATTR_BODY_OFFSET + length
    if length <= 0 or end > len(pc):
        raise ValueError("hp death body rejected: truncated_field")
    return pc[STATS_PC_ATTR_BODY_OFFSET:end]


# --------------------------------------------------------- death scenario gate
_PROFILE_DEATH_SWEEP = HpDeathHypothesisScenario(
    HP_DEATH_SCENARIO_ID,
    HP_DEATH_HYPOTHESIS_ID,
    HP_DEATH_STEP_ORDER,
    HP_DEATH_SPACING_SECONDS,
    HP_DEATH_TIMER_SECONDS,
    False,
    HP_DEATH_PROFILE_DEATH_SWEEP_NAME,
)
_PROFILE_DYING_HOLD = HpDeathHypothesisScenario(
    HP_DEATH_DYING_HOLD_SCENARIO_ID,
    HP_DEATH_HYPOTHESIS_ID,
    HP_DEATH_DYING_HOLD_STEP_ORDER,
    HP_DEATH_DYING_HOLD_SPACING_SECONDS,
    HP_DEATH_DYING_HOLD_TIMER_SECONDS,
    True,
    HP_DEATH_PROFILE_DYING_HOLD_NAME,
)
# Both scenario objects are singletons and are compared by IDENTITY everywhere.
_HP_DEATH_SCENARIOS = {
    HP_DEATH_SCENARIO_ID: _PROFILE_DEATH_SWEEP,
    HP_DEATH_DYING_HOLD_SCENARIO_ID: _PROFILE_DYING_HOLD,
}


def _expected_death_scenario(profile: Any) -> dict[str, Any]:
    """The one shape a scenario file for ``profile`` is allowed to have.

    Both profiles share this structure key for key; only the values a profile
    owns differ.  The loader compares a file against it with ``_exact_equal``,
    so an extra key, a missing key or a changed type is a refusal.
    """
    profile = _resolve_hp_death_profile(profile)
    step_order = profile.step_order
    step_fields = profile.step_fields
    return {
        "schema": 1,
        "id": profile.scenario_id,
        "test_only": True,
        "production_allowed": False,
        "hypothesis_id": HP_DEATH_HYPOTHESIS_ID,
        "lethal": True,
        "entry": {
            "flow": "full_writable_character",
            "required_sequence": "selected_and_runtime_ready",
            "response_policy": profile.response_policy,
        },
        "dispatch": {
            "trigger": "accepted_chat_input_frame_exact_ascii12_shape",
            "trigger_classifier": "classify_chat_input_attempt",
            "frames_per_accepted_request": len(step_order),
            "step_order": list(step_order),
            "step_fields": {
                label: dict(step_fields[label]) for label in step_order
            },
            "lethal_steps": list(profile.lethal_step_labels),
            "cumulative": True,
            "spacing_seconds": profile.spacing_seconds,
            "first_frame_delay_seconds": profile.first_delay_seconds,
            "delay_semantics": "gap_before_each_send_on_a_cumulative_deadline",
            "action_label_prefix": profile.action_label_prefix,
            "action_labels": [
                profile.action_label_prefix + label for label in step_order
            ],
            "one_shot": False,
            "socket_action": "none",
        },
        "wire": {
            "vital_id": UPDATE_ATTR_VITAL_ID,
            "vital_version": UPDATE_ATTR_VITAL_VERSION,
            "envelope": "gscn_runtime_protocol_res_v4_one_vital_collection",
            "attr_id": ACTOR_ATTR_ID,
            "attr_collection": (
                "tag12_u16_count_tag12_u16_attr_id_tag14_u32_length_then_body"
            ),
            "field_order_rule": "ascending_mask_bit_within_each_block",
            "death_field": {
                "name": HP_DEATH_TIMER_NAME,
                "block": "basic",
                "mask_bit": HP_DEATH_TIMER_MASK_BIT,
                "object_offset": HP_DEATH_TIMER_OFFSET,
                "wire_tag": HP_DEATH_TIMER_TAG,
                "width": "f32",
                "gate_pin": HP_DEATH_TIMER_GATE_PIN,
                "value_seconds": profile.timer_seconds,
            },
            "death_predicate": {
                "is_dead_player": IS_DEAD_PLAYER_VA,
                "is_dead_npc": IS_DEAD_NPC_VA,
                "zero_float_constant": ZERO_FLOAT_CONSTANT_VA,
                "current_hp_mask_bit": PROGRESSION_FIELDS["hp_current"].mask_bit,
                "current_hp_offset": PROGRESSION_FIELDS["hp_current"].offset,
                "rule": "current_hp_zero_and_death_timer_greater_than_zero",
            },
            "death_window_gate": {
                "per_frame_gate": MAIN_DEAD_GATE_VA,
                "window_literal": MAIN_DEAD_LITERAL_VA,
                "duration_dying_global": DURATION_DYING_GLOBAL_VA,
                "duration_dying_image_default": DURATION_DYING_IMAGE_DEFAULT,
                "rule": "duration_dying_minus_half_second_at_most_the_timer",
            },
            "apply_chain": {
                "inbound_handler": UPDATE_ATTR_VITAL_HANDLER_VA,
                "attr_class_id_getter": ACTOR_ATTR_CLASS_ID_GETTER_VA,
                "attr_lookup": UPDATE_ATTR_VITAL_ATTR_CLASS_LOOKUP_VA,
                "actor_attr_copy": ACTOR_ATTR_COPY_VA,
                "basic_attr_copy": BASIC_ATTR_COPY_VA,
                "copy_is_mask_gated": False,
                "reaches_dead_state_sync": False,
                "dead_state_sync": DEAD_STATE_SYNC_VA,
                "dead_state_sync_only_reachable_from": (
                    ATTR_APPLY_AND_DEAD_SYNC_ONLY_CALLER_VA
                ),
            },
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
                    "lethal": label in profile.lethal_step_labels,
                    "attr_body_size": profile.probe_attr_body_size[label],
                    "attr_body_sha256": profile.probe_attr_body_sha256[label],
                    "pc_size": profile.probe_pc_size[label],
                    "pc_sha256": profile.probe_pc_sha256[label],
                    "frame_size": profile.probe_frame_size[label],
                    "frame_sha256": profile.probe_frame_sha256[label],
                }
                for label in step_order
            },
        },
        "persisted_post_state": {
            "database_write": "none",
        },
        "capabilities": list(profile.capabilities),
        "nonclaims": list(profile.nonclaims),
    }


def _expected_death_sweep() -> dict[str, Any]:
    """The death_sweep shape, kept under its original name for old callers."""
    return _expected_death_scenario(HP_DEATH_PROFILE_DEATH_SWEEP)


def hp_death_profile_for_scenario(value: Any) -> HpDeathStepProfile:
    """Map an allowlisted scenario object to the step profile it selects."""
    require_hp_death_hypothesis_scenario(value)
    return HP_DEATH_PROFILES[value.profile_name]


def load_hp_death_hypothesis_scenario(
    path: str | Path,
) -> HpDeathHypothesisScenario:
    """Load ONE of the two allowlisted scenario files, by exact match.

    The allowlist is still exact and still by id: a file whose id is not one of
    the two names this module ships is refused before anything else is read,
    and the whole document must then equal the shape the matching profile
    declares, key for key and type for type.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid hp death hypothesis scenario") from exc
    if type(data) is not dict or type(data.get("id")) is not str:
        raise ValueError("hp death hypothesis scenario exceeds the exact allowlist")
    scenario = _HP_DEATH_SCENARIOS.get(data["id"])
    if scenario is None:
        raise ValueError("hp death hypothesis scenario exceeds the exact allowlist")
    profile = HP_DEATH_PROFILES[scenario.profile_name]
    if not _exact_equal(data, _expected_death_scenario(profile)):
        raise ValueError("hp death hypothesis scenario exceeds the exact allowlist")
    return require_hp_death_hypothesis_scenario(scenario)


def require_hp_death_hypothesis_scenario(
    value: Any,
) -> HpDeathHypothesisScenario:
    if type(value) is not HpDeathHypothesisScenario or not any(
        value is candidate for candidate in _HP_DEATH_SCENARIOS.values()
    ):
        raise ValueError(
            "hp death hypothesis scenario object exceeds the allowlist"
        )
    profile = HP_DEATH_PROFILES[value.profile_name]
    if (
        profile.scenario_id != value.scenario_id
        or profile.ends_dead is not value.ends_dead
        or profile.timer_seconds != value.death_timer_seconds
        or profile.step_order != value.step_order
        or profile.spacing_seconds != value.spacing_seconds
    ):
        raise ValueError(
            "hp death hypothesis scenario object exceeds the allowlist"
        )
    _require_field_table()
    _require_ascending_gate_pins()
    _require_lethal_field_table()
    _require_hp_death_step_plan(profile)
    return value


def hp_death_lethal_unlock(
    scenario: HpDeathHypothesisScenario,
) -> HpDeathLethalUnlock:
    """Hand out the unlock token, and only against the allowlisted scenario.

    This is the ONLY public way to obtain it.  Everything lethal in this module
    is behind an identity comparison against the object it returns.
    """
    require_hp_death_hypothesis_scenario(scenario)
    return _HP_DEATH_UNLOCK
