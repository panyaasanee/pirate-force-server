"""Wire builder for GM_UpdateGMStateVital (server->client, vital id 0x5A19).

Layout is PROVEN at the byte level and pinned against the bridge repository:
    pf_bridge/external/PF_SERIALIZER_FIELDS.tsv
    span_sha256 = 03b186737b43884c61c7e82dc9805f7ee161cce3ae3436f2c5d0a5db8033c661
    rows: GM_UpdateGMStateVital  W/R  tag 0x0B @+0x14 len 1
          GM_UpdateGMStateVital  W/R  tag 0x0B @+0x15 len 1
          GM_UpdateGMStateVital  W/R  tag 0x14 @+0x18 len 4

[สมมติของสาย GM - รอ RE] What is PROVEN stops at "three fields, these tags,
this order".  What each field MEANS -- is the first byte an is_gm flag, is
the second a talk/mute bit, is the u32 a GM level -- is NOT proven, and
RE-089 (DONE/BOUNDED-NEGATIVE,
notes_to_chief/20260827_0016_RE-089-RESULT-STATE-PROPAGATION-PINNED-BMGM-FALSE-LEAD.md)
answered CORE-REQUEST-GM-001 without resolving it: it pins that the wire
bytes get normalized (only exact value 1 survives; 2..255 collapse to 0) and
copied into ``GMModule_Client+0x18/+0x19/+0x1C``, then projected once more
into an opaque type-0x25 record -- but finds no render/widget/texture call
anywhere in that chain.  RE-089 also DISPROVES the ``bm_gm.tga`` lead this
docstring used to cite: byte-level census shows that asset is the
``FxNumberCache`` "green minus" damage-number glyph (`0x29`, alongside
`bm_gp.tga`/`bm_bp.tga`/`bm_bm.tga` as plus/minus x green/blue glyphs), not
a GM chat-balloon icon, and has no crosswalk to this vital at all -- do not
cite it as a GM indicator again. Until a capture/attended matrix (RE-089's
own stated next step, not yet opened) pins real semantics, callers pass the
three fields as opaque integers, not named booleans -- do not rename these
parameters to "is_gm" or similar without a citation to the RE answer that
proves it.
"""
from __future__ import annotations

GM_UPDATE_GM_STATE_VITAL_ID = 0x5A19

SERIALIZER_FIELDS_SPAN_SHA256 = (
    "03b186737b43884c61c7e82dc9805f7ee161cce3ae3436f2c5d0a5db8033c661"
)

# GT-101 (attended, OBSERVER_CONFIRMED 2026-08-27T14:39+07:00) measured what
# sending vital_version=1 actually does: the client rejects the frame with a
# modal error naming this vital by id ("VitalData version wrong,
# ErrorData=23065" -- 23065 decimal IS 0x5A19), halts processing on the
# whole connection, and closes the socket itself. Not sending this frame at
# all is always safe (every login before this lane existed did exactly
# that); sending version 1 kills the session. CORE-REQUEST-016 (LANE-GM,
# 2026-08-27T15:24+07:00): this stays None -- and runtime.py's call site
# stays gated on it being not-None -- until RE-105 (STATIC-ON-BRIDGE) pins
# the real version. Setting this to a number without that citation is
# exactly the mistake that produced GT-101.
GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED = None


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
