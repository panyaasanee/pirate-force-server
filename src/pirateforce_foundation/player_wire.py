"""Narrow experimental player ActorAttr projection for relation testing."""
import struct


def make_actor_attr_with_basic_faction(
    legacy, identity_lo: int, identity_hi: int, scene_id: int, scene_seq: int,
    basic_faction: int,
) -> bytes:
    """Add only the statically proven BasicAttr 0x0400 field in wire order."""
    if basic_faction != 1 or scene_id != 2 or scene_seq != 0:
        raise ValueError("only the Scene2 player-faction-1 relation probe is allowed")
    basic_mask = 0x000C | 0x0100 | 0x0200 | 0x0400
    return (
        legacy.u8tag(0x0B, 1)
        + bytes([0x32])
        + struct.pack("<II", identity_lo & 0xFFFFFFFF, identity_hi & 0xFFFFFFFF)
        + legacy.u16tag(0x12, basic_mask)
        + legacy.u32tag(0x14, 100)
        + legacy.u32tag(0x14, 100)
        + legacy.u16tag(0x12, scene_id)
        + bytes([0x32]) + struct.pack("<Q", scene_seq)
        + legacy.u32tag(0x14, basic_faction)
        + bytes([0x32]) + struct.pack("<II", 0x800, 0)
        + legacy.u8tag(0x05, 1)
        + bytes([0x32]) + struct.pack("<Q", legacy.V116_INITIAL_CASH)
    )
