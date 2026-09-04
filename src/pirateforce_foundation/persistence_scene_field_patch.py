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

WHY THIS WAS A SCAFFOLD.  Walking the wire (the same structural position
`extract_avatar_attr_wire_from_actor` in `current/pf_login_game_
server_v141.py` walks past on its way to the embedded AvatarAttr) finds TWO
`u16 tag 0x12` fields back to back, both value `1`, in the one capture this
repo has (`legacy.get_preset_actor_wire()`, a character created at Port
Royal -- `scene_id` there is always `1`, so nothing distinguished "the scene
field" from "some other field that happens to also read 1 for this one
character").  `COO-DECISION 20260901_1059` (the owner's own rule) forbids
writing an unconfirmed field: an overwrite of the wrong one of these two
would have injected silent garbage into every player's character-list
frame, forever, with no test able to catch it.  `LANE-DB-TO-COO 20260904_2058`
raised exactly this before writing any patch code; `COO-DECISION 20260904_2152`
item 4 ordered this scaffold while a narrow static RE ticket settled which
field is which.

FLIPPED, NOT YET CLOSED.  `notes_to_chief/20260905_0053_RE-248-RESULT-
FIELD-A-IS-SCENE-FIELD-B-IS-LEVEL.md` (static IMAGE trace, six pinned proof
slices from codec write-order through the named UI widget bindings
`LABEL_SCENE` / `NUMLABEL_CHARLV`) names `FIELD_A` (`+0x20`) as the field
the character-select screen reads for the map name; `FIELD_B` (`+0x22`) is
character level, a different field this module does not touch.  Its own
`BUILD_IMPACT` line authorized exactly one change: flip `SCENE_FIELD` from
`None` to `FIELD_A` below -- which this round does.  RE-248 is IMAGE-layer
evidence only; it says so itself (`nonclaims` item 3: "ไม่อ้างว่า IMAGE
trace คือ client-observable").  The client-observable proof is `GT-245`
(`pf_bridge/GAME_TEST_QUEUE.md`), an attended ticket that has not run yet
as of this diff.  Until it does, treat this flip as AUTHORIZED and SHIPPED,
not as CONFIRMED CORRECT on a real screen.

WHAT THIS MODULE DOES.  `locate_scene_field_candidates` finds the byte
OFFSETS of both fields' u16 values without deciding which is which.
`patch_scene_field` overwrites ONE named field (`FIELD_A`/`FIELD_B`) with a
given scene id, or returns the input UNCHANGED when `field` is `None`.
`SCENE_FIELD` below is the one constant that decides what the real call
site (`legacy_bridge.character_list`, via `project_actor_wire_for_list`)
actually does -- now `FIELD_A`, so every character-select frame patches in
`character.position.scene_id` (the already-correct CURRENT scene) over the
frozen BIRTH scene `actor_wire` carried since creation.  `FIELD_B` (level)
is never written by this module; nothing here decides or changes character
level.

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

# The one line the scaffold above existed to make a one-line change.  `None`
# would mean "patch nothing" -- `project_actor_wire_for_list` below would
# then return `character.actor_wire` byte-for-byte.  RE-248 (`notes_to_chief/
# 20260905_0053_RE-248-RESULT-FIELD-A-IS-SCENE-FIELD-B-IS-LEVEL.md`) named
# `FIELD_A` as the client's scene-name field; `BUILD_IMPACT` on that ticket
# authorized this exact flip and nothing else.
SCENE_FIELD: str | None = FIELD_A


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

    Independently cross-checked (not merely re-derived) against
    `pf_bridge/external/PF_SERIALIZER_FIELDS.tsv` rows for serializer VA
    `0x005DFF60`: order 16 (`tag 0x19`, `+0x1C`) followed immediately by
    order 17/18 (`tag 0x12`, `+0x20`/`+0x22`), a static disassembly trace
    from a different tool entirely, agreeing on this exact structural shape.
    That table does not name which field is the scene id (no data-flow to
    the write's source value, only to the object pointer) -- see the narrow
    RE ticket this round's letters reference for that open question.
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
    must be a plain `int` (a `pf-adversary` pass, this round, found `bool`
    silently accepted as 0/1 and `float`/`str` raising the wrong exception
    type by falling straight into `struct.pack_into` -- both raise
    `TypeError` here instead) that fits the wire's u16, or `ValueError` if it
    does not fit; this function never truncates or wraps a value that does
    not fit.
    """
    if field is None:
        return actor_wire
    if field not in (FIELD_A, FIELD_B):
        raise ValueError(f"unknown scene field selector: {field!r}")
    if isinstance(scene_id, bool) or not isinstance(scene_id, int):
        raise TypeError("scene_id must be a plain int, not bool/float/str")
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
