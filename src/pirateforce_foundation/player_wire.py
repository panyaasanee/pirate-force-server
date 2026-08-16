"""Typed player ActorAttr projections outside the immutable V141 source."""
import struct


def _encode_character_name(legacy, character_name: str) -> bytes:
    """Encode the persisted name with the exact ActorAttr+0x164 wstring codec."""
    if not isinstance(character_name, str):
        raise TypeError("character name must be str")
    if not character_name:
        raise ValueError("empty character name")
    try:
        encoded = character_name.encode("utf-16le")
    except UnicodeEncodeError as exc:
        raise ValueError("character name is not valid UTF-16") from exc
    if len(encoded) > 0xFFFFFFFF:
        raise ValueError("character name exceeds the PcBinary wstring length field")
    return legacy.wstr_tag(character_name)


def _make_actor_attr_with_name(
    legacy, identity_lo: int, identity_hi: int, scene_id: int, scene_seq: int,
    character_name: str, *, basic_faction: int | None,
) -> bytes:
    """Project the exact ActorAttr name field and optional frozen faction field."""
    name_wire = _encode_character_name(legacy, character_name)
    basic_mask = 0x000C | 0x0100 | 0x0200
    faction_wire = b""
    if basic_faction is not None:
        basic_mask |= 0x0400
        faction_wire = legacy.u32tag(0x14, basic_faction)
    return (
        legacy.u8tag(0x0B, 1)
        + bytes([0x32])
        + struct.pack("<II", identity_lo & 0xFFFFFFFF, identity_hi & 0xFFFFFFFF)
        + legacy.u16tag(0x12, basic_mask)
        + legacy.u32tag(0x14, 100)
        + legacy.u32tag(0x14, 100)
        + legacy.u16tag(0x12, scene_id)
        + bytes([0x32]) + struct.pack("<Q", scene_seq)
        + faction_wire
        + bytes([0x32]) + struct.pack("<II", 0x01000800, 0)
        + legacy.u8tag(0x05, 1)
        + bytes([0x32]) + struct.pack("<Q", legacy.V116_INITIAL_CASH)
        + name_wire
    )


def make_actor_attr_with_name(
    legacy, identity_lo: int, identity_hi: int, scene_id: int, scene_seq: int,
    character_name: str,
) -> bytes:
    """Build the normal player ActorAttr with its persisted player name."""
    return _make_actor_attr_with_name(
        legacy, identity_lo, identity_hi, scene_id, scene_seq, character_name,
        basic_faction=None,
    )


# PF-HYPOTHESIS-LEDGER: HYP-PF-001 frozen
def make_actor_attr_with_basic_faction(
    legacy, identity_lo: int, identity_hi: int, scene_id: int, scene_seq: int,
    character_name: str, basic_faction: int,
) -> bytes:
    """Add the frozen faction value to the named player ActorAttr projection."""
    if basic_faction != 1 or scene_seq != 0 or scene_id not in (1, 2):
        raise ValueError(
            "only the exact Scene2 or SCENE-007 Port Royal faction-1 probe is allowed"
        )
    return _make_actor_attr_with_name(
        legacy, identity_lo, identity_hi, scene_id, scene_seq, character_name,
        basic_faction=basic_faction,
    )
