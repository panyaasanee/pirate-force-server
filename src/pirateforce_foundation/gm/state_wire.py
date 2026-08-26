"""Wire builder for GM_UpdateGMStateVital (server->client, vital id 0x5A19).

Layout is PROVEN at the byte level and pinned against the bridge repository:
    pf_bridge/external/PF_SERIALIZER_FIELDS.tsv
    span_sha256 = 03b186737b43884c61c7e82dc9805f7ee161cce3ae3436f2c5d0a5db8033c661
    rows: GM_UpdateGMStateVital  W/R  tag 0x0B @+0x14 len 1
          GM_UpdateGMStateVital  W/R  tag 0x0B @+0x15 len 1
          GM_UpdateGMStateVital  W/R  tag 0x14 @+0x18 len 4

[สมมติของสาย GM - รอ RE] What is PROVEN stops at "three fields, these tags,
this order".  What each field MEANS -- is the first byte an is_gm flag, is
the second a talk/mute bit, is the u32 a GM level -- is NOT proven.  RE
request filed (notes_to_chief CORE-REQUEST-GM-001) to resolve it against
client handler 0x00729F00 and the ``bm_gm.tga`` chat-balloon icon.  Until
that comes back, callers pass the three fields as opaque integers, not named
booleans -- do not rename these parameters to "is_gm" or similar without a
citation to the RE answer.
"""
from __future__ import annotations

GM_UPDATE_GM_STATE_VITAL_ID = 0x5A19

SERIALIZER_FIELDS_SPAN_SHA256 = (
    "03b186737b43884c61c7e82dc9805f7ee161cce3ae3436f2c5d0a5db8033c661"
)


def make_gm_update_state_payload(
    legacy, field_0x0b_first: int, field_0x0b_second: int, field_0x14: int
) -> bytes:
    """Build the 8-byte tagged field body: u8tag(0x0B) + u8tag(0x0B) + u32tag(0x14).

    ``legacy`` is the loaded ``pf_login_game_server_v141`` module (see
    ``pirateforce_foundation.legacy_bridge.load_legacy``) -- this module does
    not import the frozen legacy serializer directly, the same seam
    ``npc_wire.make_npc_attr_with_basic_faction`` uses, so the wiring caller
    (owned by chief, in runtime.py) supplies it.
    """
    if not (0 <= field_0x0b_first <= 0xFF):
        raise ValueError("field_0x0b_first must fit one byte (0-255)")
    if not (0 <= field_0x0b_second <= 0xFF):
        raise ValueError("field_0x0b_second must fit one byte (0-255)")
    if not (0 <= field_0x14 <= 0xFFFFFFFF):
        raise ValueError("field_0x14 must fit a u32 (0-4294967295)")
    return (
        legacy.u8tag(0x0B, field_0x0b_first)
        + legacy.u8tag(0x0B, field_0x0b_second)
        + legacy.u32tag(0x14, field_0x14)
    )


def make_gm_update_state_frame(
    legacy,
    vital_version: int,
    field_0x0b_first: int,
    field_0x0b_second: int,
    field_0x14: int,
) -> tuple[bytes, bytes]:
    """Wrap the payload in the standard runtime-vital envelope.

    ``vital_version`` is NOT proven for this message (every other vital in
    this codebase carries its own, separately-observed version number, see
    ``LegacyProjector.character_list`` using 10 for SELECT_ACTOR_VITAL) -- it
    is a required parameter rather than a guessed default so a caller cannot
    silently ship an unverified constant.
    """
    payload = make_gm_update_state_payload(
        legacy, field_0x0b_first, field_0x0b_second, field_0x14
    )
    return legacy.make_runtime_vital(GM_UPDATE_GM_STATE_VITAL_ID, vital_version, payload)
