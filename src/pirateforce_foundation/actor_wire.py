"""Known-safe edits to the otherwise opaque CreateActorDataEx wire."""
import struct

def read_identity(actor_wire: bytes) -> tuple[int, int]:
    if len(actor_wire) < 12 or actor_wire[0] != 0x32 or actor_wire[9] != 0x0B:
        raise ValueError("unsupported actor wire prefix")
    return struct.unpack_from("<II", actor_wire, 1)

def read_selector(actor_wire: bytes) -> int:
    read_identity(actor_wire)
    return actor_wire[10]

def bind_identity_and_selector(actor_wire: bytes, identity_lo: int, identity_hi: int, selector: int) -> bytes:
    read_identity(actor_wire)
    if not 0 <= selector <= 255:
        raise ValueError("selector must fit one byte")
    result = bytearray(actor_wire)
    struct.pack_into("<II", result, 1, identity_lo & 0xFFFFFFFF, identity_hi & 0xFFFFFFFF)
    result[10] = selector
    return bytes(result)

def bind_common_attr_identity(attr_wire: bytes, identity_lo: int, identity_hi: int) -> bytes:
    """Rewrite the proven common-Attr identity without interpreting opaque fields."""
    if len(attr_wire) < 11 or attr_wire[0] != 0x0B or not (attr_wire[1] & 0x01) or attr_wire[2] != 0x32:
        raise ValueError("common Attr identity is absent or malformed")
    result = bytearray(attr_wire)
    struct.pack_into("<II", result, 3, identity_lo & 0xFFFFFFFF, identity_hi & 0xFFFFFFFF)
    return bytes(result)

def bind_actor_and_avatar_identity(
    actor_wire: bytes,
    identity_lo: int,
    identity_hi: int,
    selector: int,
    avatar_extractor,
) -> tuple[bytes, bytes]:
    """Bind the actor and its embedded AvatarAttr to one server identity.

    CreateActorDataEx and its embedded AvatarAttr both serialize an identity.
    The rest of the AvatarAttr remains opaque and byte-preserved.
    """
    rebound_actor = bind_identity_and_selector(
        actor_wire, identity_lo, identity_hi, selector
    )
    old_avatar = avatar_extractor(rebound_actor)
    new_avatar = bind_common_attr_identity(old_avatar, identity_lo, identity_hi)
    offset = rebound_actor.find(old_avatar)
    if offset < 0 or rebound_actor.find(old_avatar, offset + 1) >= 0:
        raise ValueError("embedded AvatarAttr boundary is not unique")
    rebound_actor = (
        rebound_actor[:offset]
        + new_avatar
        + rebound_actor[offset + len(old_avatar):]
    )
    return rebound_actor, new_avatar
