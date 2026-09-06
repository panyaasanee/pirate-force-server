"""``Community_*`` -- pure encode/decode, wire shape only, for sixteen
classes in this catalog group whose ``PF_SERIALIZER_FIELDS.tsv`` rows are
FULLY TAGGED (every field row has a real tag byte, no
``CALL_UNCLASSIFIED``/``PE_IMPORT_*``/``SUBCALL:``/``DYNAMIC_INTERLOCKED_*``/
``ATOMIC_*`` entries) and are not yet owned by any other module in this
lane's ``CORE-REQUEST 1120`` batch (``ui_friend_wire.py``/``ui_mail_wire.py``
already cover ``RequestBeFriendVital``/``RemoveFriendVital``/
``SendMailVital``/``GetMailContentVital``/``DeleteMailVital``, the other
five ``Community_`` classes in that batch):

    Community_ChangeActorCommentVital              0xE1AB   3 fields
    Community_ChangeActorPenNameVital              0xDCCD   3 fields
    Community_ChangeActorPersonalDataVital         0x26D5   5 fields
    Community_CommunityCommandNotAllowVital        0x3C4D   1 field
    Community_CommunityPropertyChangedVital        0x3E50   5 fields
    Community_OpenLetterInABottleVital             0xEBF8   7 fields
    Community_OpenPenpalLetterVital                0xC8D5   6 fields
    Community_RemoveBlackListVital                 0xBA6D   3 fields
    Community_ReplyLetterInABottleVital            0xFAF1   3 fields
    Community_RequestorConfirmSoulMateMatchVital   0x8E24   4 fields
    Community_SetReceiveActiveChangeVital          0x1666   4 fields
    Community_TargetConfirmSoulMateMatchVital      0x57BC   3 fields
    Community_ThrowLetterInABottleVital            0xFB51   3 fields
    Community_ThrowPenpalLetterVital               0xD72C   5 fields
    Community_UseBlankPenpalLetterVital            0xFD4B   3 fields
    Community_WriteBlankPenpalLetterVital          0x1B3C   4 fields

Eight other classes in the same registry group are deliberately NOT
implemented here (checked this round, same exclusion policy as every
sibling module in this batch): ``Community_AddBlackListVital`` (10/18 rows
unresolved), ``Community_AddFriendVital`` (10/18), ``Community_
GetActorVowLockListVital`` (12/18), ``Community_InitalizeActorCommunity
Vital`` (22/54), ``Community_ReceiveNewMailVital`` (8/34), ``Community_
ReplyPenpalLetterVital`` (10/24), ``Community_RequestSoulMateMatchVital``
(10/16), and ``Community_UpdateActorVowLockVital`` (8/14) -- each mixes
real tags with ``CALL_UNCLASSIFIED``/``PE_IMPORT_*`` rows (row counts from
``awk -F'\\t'`` over ``PF_SERIALIZER_FIELDS.tsv`` this round). A further
nine registry rows in this group (``Community_GSRequestChangeFriendship
ValueVital``, ``Community_GetActorCommunityDataFromDBVital``, ``Community_
QuerySoulMateCandidateVital``, ``Community_SSRequestLetterInABottleData
Vital``, ``Community_SSRequestPenpalLetterDataVital``, ``Community_
SendSystemMailVital``, ``Community_UpdateActorCommunityDataToDBVital``,
``Community_UpdateLetterInABottleDataToDBVital``, ``Community_
UpdatePenpalLetterDataToDBVital``) have zero rows in
``PF_SERIALIZER_FIELDS.tsv`` at all -- no wire layout known, needs static
RE from scratch, not a field-completeness call.

Field shapes are copied field-for-field from
``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv`` (searched via
``awk -F'\\t' '$1 ~ /^Community_/'``; each of the sixteen classes'
row ranges: ``ChangeActorCommentVital`` 2171-2176, ``ChangeActorPenName
Vital`` 2273-2278, ``ChangeActorPersonalDataVital`` 2279-2288, ``Community
CommandNotAllowVital`` 1985-1986, ``CommunityPropertyChangedVital``
2041-2050, ``OpenLetterInABottleVital`` 2221-2234, ``OpenPenpalLetter
Vital`` 2313-2324, ``RemoveBlackListVital`` 2099-2104, ``ReplyLetterInA
BottleVital`` 2235-2240, ``RequestorConfirmSoulMateMatchVital`` 2201-2208,
``SetReceiveActiveChangeVital`` 2177-2184, ``TargetConfirmSoulMateMatch
Vital`` 2209-2214, ``ThrowLetterInABottleVital`` 2215-2220, ``ThrowPenpal
LetterVital`` 2303-2312, ``UseBlankPenpalLetterVital`` 2289-2294,
``WriteBlankPenpalLetterVital`` 2295-2302); W and R rows are identical
shape for every class implemented here. The sixteen ``*_VITAL_ID`` hex
constants below come from
``pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`` (grep
``Community_``) -- that file, not ``PF_SERIALIZER_FIELDS.tsv`` (which has
no id column), is this project's id-on-the-wire source per
``docs/UI_LANE.md`` item 1.

Grepped first, per ``AGENTS.md`` section 7's mandatory search: no hit for
any of the sixteen class names above in ``CLIENT_RE_QUEUE.md``,
``GAME_TEST_QUEUE.md``, ``archive/``, or ``notes_to_chief/consumed/`` --
no open RE/GT ticket or closed capture references any of them. The only
hits are the static census tables (``external/PF_FIELD_VALIDATION.tsv``,
``external/PF_PROTOCOL_PRIORITY.tsv``), which is expected background
coverage confirming ``status=NOT_OBSERVED``/``observed_frames=0`` for all
sixteen (both directions), not a ticket.

Several classes share an identical field shape (``ChangeActorCommentVital``/
``ChangeActorPenNameVital``/``RemoveBlackListVital``/``TargetConfirmSoulMate
MatchVital``/``ThrowLetterInABottleVital`` are all u64+wstring+u8;
``ReplyLetterInABottleVital``/``UseBlankPenpalLetterVital`` are both
u64+u64+u8) -- same pattern as ``ui_express_wire.py``'s shared-serializer
classes: separate dataclasses and vital ids are kept for each, the shared
shape is not treated as proof they are the same action.

See ``ui_social_wire.py``'s module docstring for the shared tag legend,
the "why no wire offsets" explanation, and ``ui_party_wire.py``'s
docstring for why fields are named positionally rather than by guessed
meaning (nobody has traced caller/verb semantics for any field of any of
these sixteen classes -- naming a field "friend_id" or "letter_text" with
no evidence is exactly what ``RE_STATIC_SEARCH_RULES.md``'s "ห้ามเดา"
discipline forbids). Tag ``0x08`` (used by ``ChangeActorPersonalDataVital``'s
last field only, distinct from the ``0x0B`` u8 flavour every other field
in this module uses) is already documented in that legend
(``FINDINGS_R38_0x1B40_DECODED_LOGOUTVITAL.md``).

WSTRING TAG MIGRATION COMPLETE (round `d1b231`). Every wstring field in
every class here now encodes/decodes through ``ui_social_wire.wstring_tag``/
``read_wstring_tag`` (tag byte ``0x48``), never the proven-wrong
``encode_untagged_wstring``/``read_untagged_wstring`` pair -- see that pair's
docstring for the measurement that proved it wrong. Rounds `on8hbb` (3
classes) and `d1b231` (the remaining 10: ``ChangeActorPersonalData``,
``CommunityPropertyChanged``, ``OpenLetterInABottle``, ``OpenPenpalLetter``,
``RequestorConfirmSoulMateMatch``, ``SetReceiveActiveChange``,
``TargetConfirmSoulMateMatch``, ``ThrowLetterInABottle``,
``ThrowPenpalLetter``, ``WriteBlankPenpalLetter``) did the work. Each of the
16 W/R field pairs migrated in round `d1b231` was checked individually
against ``pf_bridge/notes_to_chief/reference_codex_attr/
PF_A2_STRING_WIRE_TAG_DELTA.tsv`` first: every one carries a
``corrected_tag=0x48`` row for BOTH directions (grepped by class name; no
field was migrated on pattern-similarity alone). Note that
``external/PF_SERIALIZER_FIELDS.tsv`` still spells these rows
``UNTAGGED_WSTRING16LE_LEN32LE`` -- the delta table above is the correction
to that table, not a contradiction of it. This module was the LAST of the
six affected modules still calling the untagged pair; with it migrated, no
module under ``src/pirateforce_foundation/`` calls that pair any more (the
functions themselves are kept in ``ui_social_wire.py`` only as the
documented record of the bug).

Same scope line as every sibling module in this batch (``CORE-REQUEST
1120``'s own words): "รับเฟรม (decode) + ตอบ ack/error frame ที่วางเปล่า ...
ไม่ใช่การทำ business logic เต็ม". Not wired into ``runtime.py`` or
``vital_walk.py``; wiring any of these is a separate ``CORE-REQUEST``.

wstring tag-0x48 migration (LANE-UI round `on8hbb`, see ``ui_friend_wire.
py``'s docstring for the bug and ``pf_bridge/notes_to_chief/
20260906_1622_LANE-UI-TO-COO-wstring-tag-0x48-bug-affects-six-shipped-
modules.md``): of the thirteen classes above with at least one wstring
field, three are migrated onto ``wstring_tag``/``read_wstring_tag`` so
far -- ``ChangeActorCommentFields``, ``ChangeActorPenNameFields``,
``RemoveBlackListFields`` (each says so in its own class docstring). The
other ten (``ChangeActorPersonalDataFields``,
``CommunityPropertyChangedFields``, ``OpenLetterInABottleFields``,
``OpenPenpalLetterFields``, ``RequestorConfirmSoulMateMatchFields``,
``SetReceiveActiveChangeFields``, ``TargetConfirmSoulMateMatchFields``,
``ThrowLetterInABottleFields``, ``ThrowPenpalLetterFields``,
``WriteBlankPenpalLetterFields``) still call the untagged pair --
``tests/test_ui_express_community_social_migration_guard.py``'s
``_GUARDED_MODULES`` keeps this whole module listed until all thirteen
are done (partial migration does not trip that guard, since it only
checks whether the module still calls the untagged pair *at all*).
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

COMMUNITY_CHANGE_ACTOR_COMMENT_VITAL_ID = 0xE1AB
COMMUNITY_CHANGE_ACTOR_PEN_NAME_VITAL_ID = 0xDCCD
COMMUNITY_CHANGE_ACTOR_PERSONAL_DATA_VITAL_ID = 0x26D5
COMMUNITY_COMMUNITY_COMMAND_NOT_ALLOW_VITAL_ID = 0x3C4D
COMMUNITY_COMMUNITY_PROPERTY_CHANGED_VITAL_ID = 0x3E50
COMMUNITY_OPEN_LETTER_IN_A_BOTTLE_VITAL_ID = 0xEBF8
COMMUNITY_OPEN_PENPAL_LETTER_VITAL_ID = 0xC8D5
COMMUNITY_REMOVE_BLACK_LIST_VITAL_ID = 0xBA6D
COMMUNITY_REPLY_LETTER_IN_A_BOTTLE_VITAL_ID = 0xFAF1
COMMUNITY_REQUESTOR_CONFIRM_SOUL_MATE_MATCH_VITAL_ID = 0x8E24
COMMUNITY_SET_RECEIVE_ACTIVE_CHANGE_VITAL_ID = 0x1666
COMMUNITY_TARGET_CONFIRM_SOUL_MATE_MATCH_VITAL_ID = 0x57BC
COMMUNITY_THROW_LETTER_IN_A_BOTTLE_VITAL_ID = 0xFB51
COMMUNITY_THROW_PENPAL_LETTER_VITAL_ID = 0xD72C
COMMUNITY_USE_BLANK_PENPAL_LETTER_VITAL_ID = 0xFD4B
COMMUNITY_WRITE_BLANK_PENPAL_LETTER_VITAL_ID = 0x1B3C

# Unproven default (see ui_party_wire.py's version-byte note).
COMMUNITY_CHANGE_ACTOR_COMMENT_VITAL_VERSION = 0
COMMUNITY_CHANGE_ACTOR_PEN_NAME_VITAL_VERSION = 0
COMMUNITY_CHANGE_ACTOR_PERSONAL_DATA_VITAL_VERSION = 0
COMMUNITY_COMMUNITY_COMMAND_NOT_ALLOW_VITAL_VERSION = 0
COMMUNITY_COMMUNITY_PROPERTY_CHANGED_VITAL_VERSION = 0
COMMUNITY_OPEN_LETTER_IN_A_BOTTLE_VITAL_VERSION = 0
COMMUNITY_OPEN_PENPAL_LETTER_VITAL_VERSION = 0
COMMUNITY_REMOVE_BLACK_LIST_VITAL_VERSION = 0
COMMUNITY_REPLY_LETTER_IN_A_BOTTLE_VITAL_VERSION = 0
COMMUNITY_REQUESTOR_CONFIRM_SOUL_MATE_MATCH_VITAL_VERSION = 0
COMMUNITY_SET_RECEIVE_ACTIVE_CHANGE_VITAL_VERSION = 0
COMMUNITY_TARGET_CONFIRM_SOUL_MATE_MATCH_VITAL_VERSION = 0
COMMUNITY_THROW_LETTER_IN_A_BOTTLE_VITAL_VERSION = 0
COMMUNITY_THROW_PENPAL_LETTER_VITAL_VERSION = 0
COMMUNITY_USE_BLANK_PENPAL_LETTER_VITAL_VERSION = 0
COMMUNITY_WRITE_BLANK_PENPAL_LETTER_VITAL_VERSION = 0

_TAG_U64 = 0x32
_TAG_U8 = 0x0B
_TAG_U8_ALT = 0x08
_TAG_U32 = 0x14


@dataclass(frozen=True)
class ChangeActorCommentFields:
    """Wire order: u64, tagged wstring (tag 0x48), u8 -- identical shape
    for W and R. Migrated off ``encode_untagged_wstring``/
    ``read_untagged_wstring`` onto ``wstring_tag``/``read_wstring_tag``
    in LANE-UI round `on8hbb` (same fix as ``ui_friend_wire.py``/
    ``ui_mail_wire.py``/``ui_party_wire.py``/``ui_trade_wire.py``/
    ``ui_express_wire.py`` -- see ``ui_friend_wire.py``'s docstring for
    the bug this proves wrong). Not wired into ``runtime.py`` -- this is
    a shape correction ahead of wiring, not a live-bug fix like
    ``ui_friend_wire.py``'s was."""

    field1_u64: int
    field2_wstring: str
    field3_u8: int


@dataclass(frozen=True)
class ChangeActorPenNameFields:
    """Wire order: u64, tagged wstring (tag 0x48), u8 -- identical shape
    for W and R (same shape as ``ChangeActorCommentFields`` -- see module
    docstring's shared-shape note; kept as a distinct class/id). Migrated
    off the untagged pair in LANE-UI round `on8hbb`, same as
    ``ChangeActorCommentFields`` above."""

    field1_u64: int
    field2_wstring: str
    field3_u8: int


@dataclass(frozen=True)
class ChangeActorPersonalDataFields:
    """Wire order: u64, wstring, wstring, wstring, u8(tag 0x08) --
    identical shape for W and R. The last field uses the alternate u8 tag
    (``0x08``), not ``0x0B`` like every other field in this module.

    Every ``wstring`` below is a TAGGED wstring (tag ``0x48``): this class was
    migrated off ``encode_untagged_wstring``/``read_untagged_wstring`` in LANE-UI
    round `d1b231` (see the module docstring's migration note)."""

    field1_u64: int
    field2_wstring: str
    field3_wstring: str
    field4_wstring: str
    field5_u8: int


@dataclass(frozen=True)
class CommunityCommandNotAllowFields:
    """Wire order: u64 -- the group's only single-field class, identical
    shape for W and R."""

    field1_u64: int


@dataclass(frozen=True)
class CommunityPropertyChangedFields:
    """Wire order: u64, u64, u8, u32, wstring -- identical shape for W
    and R.

    Every ``wstring`` below is a TAGGED wstring (tag ``0x48``): this class was
    migrated off ``encode_untagged_wstring``/``read_untagged_wstring`` in LANE-UI
    round `d1b231` (see the module docstring's migration note)."""

    field1_u64: int
    field2_u64: int
    field3_u8: int
    field4_u32: int
    field5_wstring: str


@dataclass(frozen=True)
class OpenLetterInABottleFields:
    """Wire order: u64, u64, u8, wstring, wstring, u8, u32 -- identical
    shape for W and R.

    Every ``wstring`` below is a TAGGED wstring (tag ``0x48``): this class was
    migrated off ``encode_untagged_wstring``/``read_untagged_wstring`` in LANE-UI
    round `d1b231` (see the module docstring's migration note)."""

    field1_u64: int
    field2_u64: int
    field3_u8: int
    field4_wstring: str
    field5_wstring: str
    field6_u8: int
    field7_u32: int


@dataclass(frozen=True)
class OpenPenpalLetterFields:
    """Wire order: u64, u64, u8, wstring, wstring, u32 -- identical shape
    for W and R.

    Every ``wstring`` below is a TAGGED wstring (tag ``0x48``): this class was
    migrated off ``encode_untagged_wstring``/``read_untagged_wstring`` in LANE-UI
    round `d1b231` (see the module docstring's migration note)."""

    field1_u64: int
    field2_u64: int
    field3_u8: int
    field4_wstring: str
    field5_wstring: str
    field6_u32: int


@dataclass(frozen=True)
class RemoveBlackListFields:
    """Wire order: u64, tagged wstring (tag 0x48), u8 -- identical shape
    for W and R (same shape as ``ChangeActorCommentFields`` -- see module
    docstring's shared-shape note; kept as a distinct class/id). Migrated
    off the untagged pair in LANE-UI round `on8hbb`, same as
    ``ChangeActorCommentFields`` above."""

    field1_u64: int
    field2_wstring: str
    field3_u8: int


@dataclass(frozen=True)
class ReplyLetterInABottleFields:
    """Wire order: u64, u64, u8 -- identical shape for W and R."""

    field1_u64: int
    field2_u64: int
    field3_u8: int


@dataclass(frozen=True)
class RequestorConfirmSoulMateMatchFields:
    """Wire order: u64, wstring, u8, u8 -- identical shape for W and R.

    Every ``wstring`` below is a TAGGED wstring (tag ``0x48``): this class was
    migrated off ``encode_untagged_wstring``/``read_untagged_wstring`` in LANE-UI
    round `d1b231` (see the module docstring's migration note)."""

    field1_u64: int
    field2_wstring: str
    field3_u8: int
    field4_u8: int


@dataclass(frozen=True)
class SetReceiveActiveChangeFields:
    """Wire order: u64, wstring, u8, u8 -- identical shape for W and R
    (same shape as ``RequestorConfirmSoulMateMatchFields`` -- see module
    docstring's shared-shape note; kept as a distinct class/id).

    Every ``wstring`` below is a TAGGED wstring (tag ``0x48``): this class was
    migrated off ``encode_untagged_wstring``/``read_untagged_wstring`` in LANE-UI
    round `d1b231` (see the module docstring's migration note)."""

    field1_u64: int
    field2_wstring: str
    field3_u8: int
    field4_u8: int


@dataclass(frozen=True)
class TargetConfirmSoulMateMatchFields:
    """Wire order: u64, wstring, u8 -- identical shape for W and R (same
    shape as ``ChangeActorCommentFields`` -- see module docstring's
    shared-shape note; kept as a distinct class/id).

    Every ``wstring`` below is a TAGGED wstring (tag ``0x48``): this class was
    migrated off ``encode_untagged_wstring``/``read_untagged_wstring`` in LANE-UI
    round `d1b231` (see the module docstring's migration note)."""

    field1_u64: int
    field2_wstring: str
    field3_u8: int


@dataclass(frozen=True)
class ThrowLetterInABottleFields:
    """Wire order: u64, wstring, u8 -- identical shape for W and R (same
    shape as ``ChangeActorCommentFields`` -- see module docstring's
    shared-shape note; kept as a distinct class/id).

    Every ``wstring`` below is a TAGGED wstring (tag ``0x48``): this class was
    migrated off ``encode_untagged_wstring``/``read_untagged_wstring`` in LANE-UI
    round `d1b231` (see the module docstring's migration note)."""

    field1_u64: int
    field2_wstring: str
    field3_u8: int


@dataclass(frozen=True)
class ThrowPenpalLetterFields:
    """Wire order: u64, u64, wstring, wstring, u8 -- identical shape for
    W and R.

    Every ``wstring`` below is a TAGGED wstring (tag ``0x48``): this class was
    migrated off ``encode_untagged_wstring``/``read_untagged_wstring`` in LANE-UI
    round `d1b231` (see the module docstring's migration note)."""

    field1_u64: int
    field2_u64: int
    field3_wstring: str
    field4_wstring: str
    field5_u8: int


@dataclass(frozen=True)
class UseBlankPenpalLetterFields:
    """Wire order: u64, u64, u8 -- identical shape for W and R (same
    shape as ``ReplyLetterInABottleFields`` -- see module docstring's
    shared-shape note; kept as a distinct class/id)."""

    field1_u64: int
    field2_u64: int
    field3_u8: int


@dataclass(frozen=True)
class WriteBlankPenpalLetterFields:
    """Wire order: u64, u64, wstring, u8 -- identical shape for W and
    R.

    Every ``wstring`` below is a TAGGED wstring (tag ``0x48``): this class was
    migrated off ``encode_untagged_wstring``/``read_untagged_wstring`` in LANE-UI
    round `d1b231` (see the module docstring's migration note)."""

    field1_u64: int
    field2_u64: int
    field3_wstring: str
    field4_u8: int


def encode_change_actor_comment_payload(
    fields: ChangeActorCommentFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.wstring_tag(fields.field2_wstring)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_change_actor_comment_payload(
    payload: bytes,
) -> ChangeActorCommentFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_wstring_tag(payload, offset)
        f3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ChangeActorCommentFields(f1, f2, f3)


def encode_change_actor_pen_name_payload(
    fields: ChangeActorPenNameFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.wstring_tag(fields.field2_wstring)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_change_actor_pen_name_payload(
    payload: bytes,
) -> ChangeActorPenNameFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_wstring_tag(payload, offset)
        f3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ChangeActorPenNameFields(f1, f2, f3)


def encode_change_actor_personal_data_payload(
    fields: ChangeActorPersonalDataFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.wstring_tag(fields.field2_wstring)
    out += wire.wstring_tag(fields.field3_wstring)
    out += wire.wstring_tag(fields.field4_wstring)
    out += bytes([_TAG_U8_ALT, fields.field5_u8 & 0xFF])
    return bytes(out)


def decode_change_actor_personal_data_payload(
    payload: bytes,
) -> ChangeActorPersonalDataFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_wstring_tag(payload, offset)
        f3, offset = wire.read_wstring_tag(payload, offset)
        f4, offset = wire.read_wstring_tag(payload, offset)
        f5, offset = wire.read_u8tag(payload, offset, _TAG_U8_ALT)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ChangeActorPersonalDataFields(f1, f2, f3, f4, f5)


def encode_community_command_not_allow_payload(
    fields: CommunityCommandNotAllowFields,
) -> bytes:
    return wire.u64tag(_TAG_U64, fields.field1_u64)


def decode_community_command_not_allow_payload(
    payload: bytes,
) -> CommunityCommandNotAllowFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return CommunityCommandNotAllowFields(f1)


def encode_community_property_changed_payload(
    fields: CommunityPropertyChangedFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    out += wire.u32tag(_TAG_U32, fields.field4_u32)
    out += wire.wstring_tag(fields.field5_wstring)
    return bytes(out)


def decode_community_property_changed_payload(
    payload: bytes,
) -> CommunityPropertyChangedFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        f3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        f4, offset = wire.read_u32tag(payload, offset, _TAG_U32)
        f5, offset = wire.read_wstring_tag(payload, offset)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return CommunityPropertyChangedFields(f1, f2, f3, f4, f5)


def encode_open_letter_in_a_bottle_payload(
    fields: OpenLetterInABottleFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    out += wire.wstring_tag(fields.field4_wstring)
    out += wire.wstring_tag(fields.field5_wstring)
    out += bytes([_TAG_U8, fields.field6_u8 & 0xFF])
    out += wire.u32tag(_TAG_U32, fields.field7_u32)
    return bytes(out)


def decode_open_letter_in_a_bottle_payload(
    payload: bytes,
) -> OpenLetterInABottleFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        f3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        f4, offset = wire.read_wstring_tag(payload, offset)
        f5, offset = wire.read_wstring_tag(payload, offset)
        f6, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        f7, offset = wire.read_u32tag(payload, offset, _TAG_U32)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return OpenLetterInABottleFields(f1, f2, f3, f4, f5, f6, f7)


def encode_open_penpal_letter_payload(
    fields: OpenPenpalLetterFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    out += wire.wstring_tag(fields.field4_wstring)
    out += wire.wstring_tag(fields.field5_wstring)
    out += wire.u32tag(_TAG_U32, fields.field6_u32)
    return bytes(out)


def decode_open_penpal_letter_payload(
    payload: bytes,
) -> OpenPenpalLetterFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        f3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        f4, offset = wire.read_wstring_tag(payload, offset)
        f5, offset = wire.read_wstring_tag(payload, offset)
        f6, offset = wire.read_u32tag(payload, offset, _TAG_U32)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return OpenPenpalLetterFields(f1, f2, f3, f4, f5, f6)


def encode_remove_black_list_payload(
    fields: RemoveBlackListFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.wstring_tag(fields.field2_wstring)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_remove_black_list_payload(
    payload: bytes,
) -> RemoveBlackListFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_wstring_tag(payload, offset)
        f3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return RemoveBlackListFields(f1, f2, f3)


def encode_reply_letter_in_a_bottle_payload(
    fields: ReplyLetterInABottleFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_reply_letter_in_a_bottle_payload(
    payload: bytes,
) -> ReplyLetterInABottleFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        f3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ReplyLetterInABottleFields(f1, f2, f3)


def encode_requestor_confirm_soul_mate_match_payload(
    fields: RequestorConfirmSoulMateMatchFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.wstring_tag(fields.field2_wstring)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field4_u8 & 0xFF])
    return bytes(out)


def decode_requestor_confirm_soul_mate_match_payload(
    payload: bytes,
) -> RequestorConfirmSoulMateMatchFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_wstring_tag(payload, offset)
        f3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        f4, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return RequestorConfirmSoulMateMatchFields(f1, f2, f3, f4)


def encode_set_receive_active_change_payload(
    fields: SetReceiveActiveChangeFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.wstring_tag(fields.field2_wstring)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field4_u8 & 0xFF])
    return bytes(out)


def decode_set_receive_active_change_payload(
    payload: bytes,
) -> SetReceiveActiveChangeFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_wstring_tag(payload, offset)
        f3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        f4, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return SetReceiveActiveChangeFields(f1, f2, f3, f4)


def encode_target_confirm_soul_mate_match_payload(
    fields: TargetConfirmSoulMateMatchFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.wstring_tag(fields.field2_wstring)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_target_confirm_soul_mate_match_payload(
    payload: bytes,
) -> TargetConfirmSoulMateMatchFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_wstring_tag(payload, offset)
        f3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return TargetConfirmSoulMateMatchFields(f1, f2, f3)


def encode_throw_letter_in_a_bottle_payload(
    fields: ThrowLetterInABottleFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.wstring_tag(fields.field2_wstring)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_throw_letter_in_a_bottle_payload(
    payload: bytes,
) -> ThrowLetterInABottleFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_wstring_tag(payload, offset)
        f3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ThrowLetterInABottleFields(f1, f2, f3)


def encode_throw_penpal_letter_payload(
    fields: ThrowPenpalLetterFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += wire.wstring_tag(fields.field3_wstring)
    out += wire.wstring_tag(fields.field4_wstring)
    out += bytes([_TAG_U8, fields.field5_u8 & 0xFF])
    return bytes(out)


def decode_throw_penpal_letter_payload(
    payload: bytes,
) -> ThrowPenpalLetterFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        f3, offset = wire.read_wstring_tag(payload, offset)
        f4, offset = wire.read_wstring_tag(payload, offset)
        f5, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ThrowPenpalLetterFields(f1, f2, f3, f4, f5)


def encode_use_blank_penpal_letter_payload(
    fields: UseBlankPenpalLetterFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_use_blank_penpal_letter_payload(
    payload: bytes,
) -> UseBlankPenpalLetterFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        f3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return UseBlankPenpalLetterFields(f1, f2, f3)


def encode_write_blank_penpal_letter_payload(
    fields: WriteBlankPenpalLetterFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += wire.wstring_tag(fields.field3_wstring)
    out += bytes([_TAG_U8, fields.field4_u8 & 0xFF])
    return bytes(out)


def decode_write_blank_penpal_letter_payload(
    payload: bytes,
) -> WriteBlankPenpalLetterFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        f3, offset = wire.read_wstring_tag(payload, offset)
        f4, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return WriteBlankPenpalLetterFields(f1, f2, f3, f4)
