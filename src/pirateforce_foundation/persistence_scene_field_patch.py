"""LANE-DB / PLAYER-CHARACTER: locate, but do not yet choose between, the two
ambiguous `u16 tag 0x12` fields inside `characters.actor_wire`, so that
fixing the character-select scene name (`PANYA-DECISION 20260904_1857`) is a
one-constant-line change once the field is confirmed, not a new patch site.

WHY THIS FILE EXISTS.  `legacy_bridge.character_list` sends each character's
`actor_wire` -- the `CreateActorDataEx` blob frozen at creation time -- into
the character-select frame verbatim.  `COO-DECISION 20260904_1947` measured
that this is why the select screen prints the character's BIRTH scene
(always Port Royal) instead of her CURRENT one (`character.position.scene_id`,
already correct in the DB): nothing ever overwrites the scene field in that
frozen blob before it goes out.

WHY THIS IS A SCAFFOLD, NOT THE FIX.  Walking the wire (the same structural
position `extract_avatar_attr_wire_from_actor` in `current/pf_login_game_
server_v141.py` walks past on its way to the embedded AvatarAttr) finds TWO
`u16 tag 0x12` fields back to back, both value `1`, in the one capture this
repo has (`legacy.get_preset_actor_wire()`, a character created at Port
Royal -- `scene_id` there is always `1`, so nothing distinguishes "the scene
field" from "some other field that happens to also read 1 for this one
character").  `COO-DECISION 20260901_1059` (the owner's own rule) forbids
writing an unconfirmed field: an overwrite of the wrong one of these two
would inject silent garbage into every player's character-list frame,
forever, with no test able to catch it (the wrong field would still read
`1` in the one fixture this repo has).  `LANE-DB-TO-COO 20260904_2058` raised
exactly this before writing any patch code; `COO-DECISION 20260904_2152`
item 4 ordered this scaffold while a narrow static RE ticket (drafted the
same round, see `pf_bridge/notes_to_chief/`) settles which field is which.

WHAT THIS MODULE DOES.  `locate_scene_field_candidates` finds the byte
OFFSETS of both fields' u16 values without deciding which is which.
`patch_scene_field` overwrites ONE named field (`FIELD_A`/`FIELD_B`) with a
given scene id, or returns the input UNCHANGED when `field` is `None`.
`SCENE_FIELD` below is the one constant that decides what the real call
site (`legacy_bridge.character_list`, via `project_actor_wire_for_list`)
actually does.  IT IS `None` TODAY -- a deliberate no-op, proved
byte-identical by `tests/test_persistence_scene_field_patch.py` -- because
the RE ticket has not answered yet.  When it answers, the fix is ONE LINE:
change `SCENE_FIELD` to whichever of `FIELD_A`/`FIELD_B` the client reads for
the map name, in this file, under the same round code.  No other file needs
to change again.

WHAT THIS MODULE DOES NOT DO.  It does not guess.  It does not touch
`characters.actor_wire` in the database (no migration, no backfill --
`COO-DECISION 20260901_1947` item 4 forbids both).  It does not import or
modify `current/pf_login_game_server_v141.py`.
"""
from __future__ import annotations

import struct

# The two names a future reader (and `SCENE_FIELD` below) chooses between.
# Which one is the client's scene-name field is NOT known yet -- see the
# module docstring and the narrow RE ticket this round's letters reference.
FIELD_A = "A"
FIELD_B = "B"

# The one line this whole scaffold exists to make a one-line change.  `None`
# means "patch nothing" -- `project_actor_wire_for_list` below then returns
# `character.actor_wire` byte-for-byte, which is what `main` does today.
# Flip this to `FIELD_A` or `FIELD_B` ONLY once the narrow RE ticket names
# which field the client actually reads for the character-select map name.
SCENE_FIELD: str | None = None


def locate_scene_field_candidates(actor_wire: bytes) -> tuple[int, int]:
    """Return the byte offsets of the two-byte VALUE (not the tag byte) of
    the two `u16 tag 0x12` fields that sit back to back in
    `CreateActorDataEx`, immediately after the `u32 tag 0x19` field
    (`COO-DECISION 20260903_1943` item 3: an unconfirmed `class_id`
    hypothesis, not read here) and before the trailing `astr`/`wstr` pair.

    This walks the exact same structural position `extract_avatar_attr_wire_
    from_actor` (`current/pf_login_game_server_v141.py`) walks past on its
    way to the embedded AvatarAttr -- re-derived here, not imported, so this
    module has no dependency on that frozen file.  Raises `ValueError` if any
    expected tag byte along the way does not match, rather than silently
    reading past a wire shape this was never proven against.
    """
    if len(actor_wire) < 12 or actor_wire[0] != 0x32:
        raise ValueError("unsupported actor wire prefix (expected 0x32 identity tag)")
    try:
        # raw8(0x32): 1 tag byte + 8 data bytes (identity_lo, identity_hi).
        pos = 9
        if actor_wire[pos] != 0x0B:
            raise ValueError("selector tag (0x0B) missing at expected offset")
        pos += 2  # tag byte + 1-byte selector value
        pos = _skip_wstr(actor_wire, pos)  # name
        for _ in range(2):  # appearance byte, create-context byte: u8(0x0B) x2
            if actor_wire[pos] != 0x0B:
                raise ValueError("appearance/create u8(0x0B) tag missing")
            pos += 2
        if actor_wire[pos] != 0x19:
            raise ValueError("u32(0x19) class-id-hypothesis tag missing")
        pos += 5  # tag byte + 4-byte value
        if actor_wire[pos] != 0x12:
            raise ValueError("field A: u16(0x12) tag missing")
        field_a_value_offset = pos + 1
        pos += 3  # tag byte + 2-byte value
        if actor_wire[pos] != 0x12:
            raise ValueError("field B: u16(0x12) tag missing")
        field_b_value_offset = pos + 1
    except IndexError as exc:
        raise ValueError("truncated actor wire: ran past its end while "
                          "walking to the scene field candidates") from exc
    return field_a_value_offset, field_b_value_offset


def _skip_wstr(data: bytes, pos: int) -> int:
    """Advance past one `wstr` field (`tag 0x48 + u32 byte_len + utf16le`)."""
    if data[pos] != 0x48:
        raise ValueError("wstr tag (0x48) missing at expected offset")
    if len(data) < pos + 1 + 4:
        raise ValueError("truncated wstr length field")
    (byte_len,) = struct.unpack_from("<I", data, pos + 1)
    end = pos + 1 + 4 + byte_len
    if len(data) < end:
        raise ValueError("truncated wstr payload")
    return end


def patch_scene_field(actor_wire: bytes, field: str | None, scene_id: int) -> bytes:
    """Overwrite ONE of the two ambiguous `u16 tag 0x12` fields with
    `scene_id`, or return `actor_wire` UNCHANGED when `field` is `None`.

    `field` must be `None`, `FIELD_A` or `FIELD_B` -- anything else raises
    `ValueError` rather than silently doing nothing or guessing.  `scene_id`
    must fit the wire's u16 (raises `ValueError` otherwise); this function
    never truncates or wraps a value that does not fit.
    """
    if field is None:
        return actor_wire
    if field not in (FIELD_A, FIELD_B):
        raise ValueError(f"unknown scene field selector: {field!r}")
    if not 0 <= scene_id <= 0xFFFF:
        raise ValueError("scene_id must fit the wire's u16 field")
    offset_a, offset_b = locate_scene_field_candidates(actor_wire)
    offset = offset_a if field == FIELD_A else offset_b
    result = bytearray(actor_wire)
    struct.pack_into("<H", result, offset, scene_id)
    return bytes(result)


def project_actor_wire_for_list(character) -> bytes:
    """What `legacy_bridge.character_list` sends for one character's
    `actor_wire` slot: `character.actor_wire` with the scene field named by
    `SCENE_FIELD` patched to `character.position.scene_id` -- or, while
    `SCENE_FIELD` is `None`, `character.actor_wire` completely unchanged.
    """
    return patch_scene_field(
        character.actor_wire, SCENE_FIELD, character.position.scene_id
    )
