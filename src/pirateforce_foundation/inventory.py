"""Persisted structural Backpack states at the exact V111 boundary.

The initial and merged states are byte-proven.  The third state is the
explicitly tracked HYP-PF-008 composition that keeps the merged quantity and
moves identity 1 to the independently proven free destination slot 2.  It is
not a generalized inventory, item-ownership, collision, or equipment model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


BACKPACK_BASE_MASK = 0xFF
BACKPACK_BASE_IDENTITY = 0
BACKPACK_RANGE_MASK = 1


@dataclass(frozen=True)
class ItemAttrState:
    identity: int
    template_id: int
    quantity: int
    slot: int
    raw_u8_38: int = 0
    raw_u8_39: int = 0xFF
    detail_present: int = 0


@dataclass(frozen=True)
class BackpackState:
    base_mask: int
    base_identity: int
    range_mask: int
    items: tuple[ItemAttrState, ...]


INITIAL_BACKPACK = BackpackState(
    BACKPACK_BASE_MASK,
    BACKPACK_BASE_IDENTITY,
    BACKPACK_RANGE_MASK,
    (
        ItemAttrState(1, 2600001, 1, 0),
        ItemAttrState(2, 2400901, 1, 1),
        ItemAttrState(3, 2600001, 1, 2),
        ItemAttrState(4, 2200002, 1, 3),
    ),
)

MERGED_V111_BACKPACK = BackpackState(
    BACKPACK_BASE_MASK,
    BACKPACK_BASE_IDENTITY,
    BACKPACK_RANGE_MASK,
    (
        ItemAttrState(1, 2600001, 2, 0),
        ItemAttrState(2, 2400901, 1, 1),
        ItemAttrState(4, 2200002, 1, 3),
    ),
)

# PF-HYPOTHESIS-LEDGER: HYP-PF-008 active
HYPOTHESIZED_V111_SLOT2_BACKPACK = BackpackState(
    BACKPACK_BASE_MASK,
    BACKPACK_BASE_IDENTITY,
    BACKPACK_RANGE_MASK,
    (
        # Identity order is retained from the exact merged snapshot.  Its
        # reconnect use after the move is part of HYP-PF-008, not original
        # server evidence.
        ItemAttrState(1, 2600001, 2, 2),
        ItemAttrState(2, 2400901, 1, 1),
        ItemAttrState(4, 2200002, 1, 3),
    ),
)

V111_MERGE_REQUEST_PC = bytes.fromhex(
    "12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 "
    "ED 4B 0B 00 0B 04 14 00 00 00 00 32 03 00 00 00 "
    "00 00 00 00"
)
V111_MERGE_FIELDS = (4, 0, 3)
V111_MERGE_PAYLOAD = V111_MERGE_REQUEST_PC[20:]


def _require_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer in [{minimum},{maximum}]")
    return value


def require_known_backpack(value: Any) -> BackpackState:
    """Reject every state outside the two exact and one tracked snapshots."""
    if type(value) is not BackpackState:
        raise ValueError("backpack must be an exact BackpackState")
    _require_int(value.base_mask, "backpack base mask", 0, 0xFF)
    _require_int(value.base_identity, "backpack base identity", 0, 0xFFFFFFFFFFFFFFFF)
    _require_int(value.range_mask, "backpack range mask", 0, 0xFF)
    if type(value.items) is not tuple:
        raise ValueError("backpack items must be an exact tuple")
    identities: set[int] = set()
    slots: set[int] = set()
    for item in value.items:
        if type(item) is not ItemAttrState:
            raise ValueError("backpack item must be an exact ItemAttrState")
        _require_int(item.identity, "item identity", 0, 0x7FFFFFFFFFFFFFFF)
        _require_int(item.template_id, "item template", 0, 0xFFFFFFFF)
        _require_int(item.quantity, "item quantity", 0, 0xFFFF)
        _require_int(item.slot, "item slot", 0, 0xFFFF)
        _require_int(item.raw_u8_38, "item raw +0x38", 0, 0xFF)
        _require_int(item.raw_u8_39, "item raw +0x39", 0, 0xFF)
        _require_int(item.detail_present, "item detail presence", 0, 1)
        if item.identity in identities or item.slot in slots:
            raise ValueError("backpack identity/slot must be unique")
        identities.add(item.identity)
        slots.add(item.slot)
    if value not in (
        INITIAL_BACKPACK,
        MERGED_V111_BACKPACK,
        HYPOTHESIZED_V111_SLOT2_BACKPACK,
    ):
        raise ValueError("backpack state is outside the governed V111 allowlist")
    return value


def make_backpack_attr(legacy: Any, state: BackpackState) -> bytes:
    """Serialize one governed state using frozen tagged primitives."""
    state = require_known_backpack(state)
    required = {
        "BACKPACK_ATTR": 0x1F81,
        "V103_ITEM_SEQUENCE": 1,
        "V103_ITEM_TEMPLATE": 2600001,
        "V110_CASK_SEQUENCE": 2,
        "V110_CASK_TEMPLATE": 2400901,
        "V111_STACK_SOURCE_SEQUENCE": 3,
        "V123_BLADE_SEQUENCE": 4,
        "V123_BLADE_TEMPLATE": 2200002,
        "V120_BACKPACK_BASE_RANGE_MASK": 1,
    }
    for name, expected in required.items():
        if getattr(legacy, name, None) != expected:
            raise ValueError(f"frozen inventory constant drift: {name}")

    output = bytearray()
    output += legacy.u8tag(0x0B, state.base_mask)
    output += legacy.qwordtag(0x32, state.base_identity)
    output += legacy.u16tag(0x0F, len(state.items))
    for item in state.items:
        output += legacy.qwordtag(0x32, item.identity)
        output += legacy.u32tag(0x14, item.template_id)
        output += legacy.u16tag(0x0F, item.quantity)
        output += legacy.u16tag(0x0F, item.slot)
        output += legacy.u8tag(0x08, item.raw_u8_38)
        output += legacy.u8tag(0x08, item.raw_u8_39)
        output += legacy.u8tag(0x0B, item.detail_present)
    output += legacy.u16tag(0x0F, len(state.items))
    for item in state.items:
        output += legacy.qwordtag(0x32, item.identity)
    output += legacy.u8tag(0x0B, state.range_mask)
    result = bytes(output)
    if state == INITIAL_BACKPACK and result != legacy.make_backpack_attr_four_items():
        raise RuntimeError("typed initial Backpack drifted from frozen V141")
    return result


def parse_merge_candidate(legacy: Any, parsed: Any) -> tuple[int, int, int] | None:
    """Recognize the exact tuple as a candidate, never as authorization.

    A trailing suffix is deliberately still a candidate so a malformed copy of
    the accepted request cannot fall through to the broader frozen handler.
    The separate exact-request predicate rejects that suffix.
    """
    if parsed.nested_id != legacy.ITEM_OPERATE_REQ_VITAL:
        return None
    payload = bytes(parsed.nested_payload)
    if payload.startswith(V111_MERGE_PAYLOAD):
        return V111_MERGE_FIELDS
    try:
        fields = legacy.parse_item_operate_req(parsed)
    except (ValueError, TypeError):
        return None
    return fields if fields == V111_MERGE_FIELDS else None


def is_exact_merge_request(legacy: Any, parsed: Any) -> bool:
    """Require the complete accepted 36-byte request, not just the field tuple."""
    return (
        parse_merge_candidate(legacy, parsed) == V111_MERGE_FIELDS
        and parsed.outer_id == legacy.GSCN_RUNTIME_PROTOCOL_REQ
        and parsed.outer_version == 0
        and parsed.outer_mask == 0x02
        and parsed.vital_count == 1
        and parsed.nested_version == 0
        and parsed.raw_pc == V111_MERGE_REQUEST_PC
    )
