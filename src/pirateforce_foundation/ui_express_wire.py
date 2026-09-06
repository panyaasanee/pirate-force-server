"""``Express_*`` -- pure encode/decode, wire shape only, for the four classes
in this catalog group whose ``PF_SERIALIZER_FIELDS.tsv`` rows are FULLY
TAGGED (every field row has a real tag byte or a resolved untagged-string
shape, no ``CALL_UNCLASSIFIED``/``PE_IMPORT_*``/``JUMP_UNCLASSIFIED``/
``ATOMIC_*``/``DYNAMIC_INTERLOCKED_*`` entries):

    Express_ClientRemoveExpressVital       0xD82D  3 fields
    Express_ClientSendExpressResultVital   0x1091  3 fields
    Express_ClientcClaimExpressVital       0xD5A8  3 fields
    Express_ResetExpressCountVital         0xBECD  2 fields

Eight classes in the same registry group (12 total, per
``pf_bridge/prompts/LANE-UI.md``'s catalog: "Express 12") are deliberately
NOT implemented here:
    - ``Express_InitalizeActorExpressVital`` (0xF375, 40 rows) -- mixes
      real tags with ``CALL_UNCLASSIFIED``/``PE_IMPORT_*`` entries (20 of
      40 rows).
    - ``Express_ClientGetExpressItemAttrsVital`` (0x2C5D, 22 rows) -- same
      mix (12 of 22 rows).
    - ``Express_ClientReceiveNewExpressVital`` (0x0E0C, 26 rows) -- same
      mix (6 of 26 rows).
    - ``Express_ClientSendExpressVital`` (0xBD0D, 28 rows) -- same mix
      (12 of 28 rows).
    - ``Express_GetActorExpressDataFromDBVital`` (0x1F14),
      ``Express_GSConfirmActorExpressDataVital`` (0x278C),
      ``Express_GSAddNewExpressVital`` (0xA1E1), and
      ``Express_GSSendSystemExpressVital`` (0xD6F1) -- present in
      ``pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`` (the
      id-on-the-wire source, per ``docs/UI_LANE.md`` item 1) but absent
      from ``external/PF_SERIALIZER_FIELDS.tsv`` entirely (grep
      ``^Express_`` there returns no row for any of these four names) --
      no wire layout is known for them at all, so they cannot be scoped
      as either "included" or "excluded-for-unresolved-rows"; they need
      static RE from scratch, not a field-completeness judgment call.

Field shapes are copied field-for-field from
``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv`` (searched via
``awk -F'\\t' '$1 ~ /^Express_/'``, 138 rows total across the eight classes
that do have rows there); W and R rows are identical shape for every class
implemented here (same span/sha256 per class, both directions). The four
``*_VITAL_ID`` hex constants below come from
``pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`` (grep
``^0x....\\tExpress_``) -- that file, not ``PF_SERIALIZER_FIELDS.tsv``
(which has no id column), is this project's id-on-the-wire source per
``docs/UI_LANE.md`` item 1.

``Express_ClientRemoveExpressVital`` and ``Express_ClientcClaimExpressVital``
share an identical field table (same three-field shape, same span_start
``0x006E7B20``, same span_sha256) -- two distinct vital ids compiled to one
shared serializer function, the same pattern already documented in
``ui_channel_wire.py``'s module docstring for its five shared-serializer
classes. This module still gives each its own dataclass and its own
encode/decode pair (matching each vital id to its own named type), it just
notes the two happen to be wire-identical; nothing here claims the two
actions are the same action.

``Express_ClientSendExpressResultVital``'s third field is
``UNTAGGED_WSTRING16LE_LEN32LE`` per ``PF_SERIALIZER_FIELDS.tsv``'s own
label, but that label is not the real wire shape (see
``ui_social_wire.encode_untagged_wstring``'s docstring): the actual codec
always writes a tag byte ``0x48`` before the u32 LE length + UTF-16LE
payload, proven byte-exact against disassembly in
``reports/PF_CHAT_CHANNEL001_CHANNEL_FAMILY_AND_ROUTING_STATIC_20260818.md``
and confirmed live for four other wstring fields that shipped without it
(``ui_friend_wire.py``/``ui_mail_wire.py``/``ui_party_wire.py``/
``ui_trade_wire.py``). This module's own field originally reused
``ui_social_wire``'s untagged pair too (same live-misdecoding bug those
four had) and was migrated onto ``wire.wstring_tag``/``wire.read_wstring_tag``
below in the same round that recovered
``tests/test_ui_express_community_social_migration_guard.py`` (round
`me7s4u`) -- see that commit's message for the migration itself; this
docstring only records the resulting shape, not a separate history
document the way the four sibling modules each carry in their own
docstrings.

Grepped first, per ``AGENTS.md`` section 7's mandatory search: no hit for
any of the four class names above in ``CLIENT_RE_QUEUE.md`` or
``GAME_TEST_QUEUE.md`` (grep on the bridge repo, including ``archive/``) --
no open or closed RE/GT ticket references any of them. The only hits are
the static census tables (``notes_to_chief/reference_codex_attr/
PF_PROTOCOL_REGISTRY.tsv``, ``PF_FIELD_VALIDATION.tsv``,
``PF_PROTOCOL_PRIORITY.tsv``), which is expected background coverage, not
a ticket. This catalog group has no prior wire module in ``src/``.

See ``ui_social_wire.py``'s module docstring for the shared tag legend, the
"why no wire offsets" explanation, and the fail-closed-on-decode
convention. Tag ``0x32`` = u64/qword and ``0x0B`` = u8 are documented there
directly.

Same scope line as every sibling module in this batch (``CORE-REQUEST
1120``'s own words): "receive frame (decode) + compose the same shape back
(encode), no business logic". Nothing here claims what any field MEANS
(express/parcel id, sender/recipient id, result code, etc.) -- the
registry's ``proven_semantics`` column is ``UNKNOWN`` for every row of all
four classes. Not wired into ``runtime.py`` or ``vital_walk.py``; wiring
any of these is a separate ``CORE-REQUEST``.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

EXPRESS_CLIENT_REMOVE_EXPRESS_VITAL_ID = 0xD82D
EXPRESS_CLIENT_SEND_EXPRESS_RESULT_VITAL_ID = 0x1091
EXPRESS_CLIENT_CLAIM_EXPRESS_VITAL_ID = 0xD5A8
EXPRESS_RESET_EXPRESS_COUNT_VITAL_ID = 0xBECD

# Unproven default (see ui_party_wire.py's version-byte note).
EXPRESS_CLIENT_REMOVE_EXPRESS_VITAL_VERSION = 0
EXPRESS_CLIENT_SEND_EXPRESS_RESULT_VITAL_VERSION = 0
EXPRESS_CLIENT_CLAIM_EXPRESS_VITAL_VERSION = 0
EXPRESS_RESET_EXPRESS_COUNT_VITAL_VERSION = 0

_TAG_U8 = 0x0B
_TAG_U64 = 0x32


@dataclass(frozen=True)
class ClientRemoveExpressFields:
    """Wire order: u64, u64, u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv`` ``Express_ClientRemoveExpressVital``
    rows)."""

    field1_u64: int
    field2_u64: int
    field3_u8: int


@dataclass(frozen=True)
class ClientSendExpressResultFields:
    """Wire order: u64, u8, wstring -- identical shape for W and R."""

    field1_u64: int
    field2_u8: int
    field3_wstring: str


@dataclass(frozen=True)
class ClientClaimExpressFields:
    """Wire order: u64, u64, u8 -- identical shape for W and R. Same field
    table as ``ClientRemoveExpressFields`` above (shared serializer, see
    module docstring) -- kept as its own type because the two vital ids
    are distinct actions."""

    field1_u64: int
    field2_u64: int
    field3_u8: int


@dataclass(frozen=True)
class ResetExpressCountFields:
    """Wire order: u64, u8 -- identical shape for W and R."""

    field1_u64: int
    field2_u8: int


def encode_client_remove_express_payload(fields: ClientRemoveExpressFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_client_remove_express_payload(
    payload: bytes,
) -> ClientRemoveExpressFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ClientRemoveExpressFields(field1, field2, field3)


def encode_client_send_express_result_payload(
    fields: ClientSendExpressResultFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    out += wire.wstring_tag(fields.field3_wstring)
    return bytes(out)


def decode_client_send_express_result_payload(
    payload: bytes,
) -> ClientSendExpressResultFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field3, offset = wire.read_wstring_tag(payload, offset)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ClientSendExpressResultFields(field1, field2, field3)


def encode_client_claim_express_payload(fields: ClientClaimExpressFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_client_claim_express_payload(
    payload: bytes,
) -> ClientClaimExpressFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ClientClaimExpressFields(field1, field2, field3)


def encode_reset_express_count_payload(fields: ResetExpressCountFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    return bytes(out)


def decode_reset_express_count_payload(
    payload: bytes,
) -> ResetExpressCountFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ResetExpressCountFields(field1, field2)
