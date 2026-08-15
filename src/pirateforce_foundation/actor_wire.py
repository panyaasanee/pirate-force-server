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
