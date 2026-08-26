"""GM-001: the GM_UpdateGMStateVital body, from a proven field layout only.

PROVENANCE (pf_bridge/external/PF_SERIALIZER_FIELDS.tsv, rows tagged
GM_UpdateGMStateVital, span 0x00729720-0x00729785, span sha256
03b186737b43884c61c7e82dc9805f7ee161cce3ae3436f2c5d0a5db8033c661):

    W/R 1   tag 0x0B (u8)   object offset +0x14   1 byte
    W/R 2   tag 0x0B (u8)   object offset +0x15   1 byte
    W/R 3   tag 0x14 (u32)  object offset +0x18   4 bytes

Three fields, always present (gate_condition ALWAYS on every row), read and
written by the same handler code -- the layout is proven both directions.

WHAT IS NOT PROVEN.  Nobody has yet correlated a live client screen to any
value of field_a, field_b or field_c (that is GM-001's own attended probe,
queued in pf_bridge/GAME_TEST_QUEUE.md).  This module therefore takes all
three as plain parameters and claims NOTHING about what they mean --
[SMMUT_LANE_GM_ROR_RE] is the tag used in pf_bridge letters for exactly this:
a placeholder pending RE confirmation.  The best current guess, carried only
in ``for_gm_grant``/``for_gm_revoke`` as a readable on/off shape and NOT as a
proven semantic, is field_a = is_gm (0/1), with field_b and field_c left at
their most conservative value (0) until RE-002 (queued to chief) says
otherwise.

WHAT THIS MODULE DOES NOT DO.  It does not send anything, does not decide who
is a GM (see accounts.py) and does not choose vital id 0x5A19's place in the
wire framing (version, ``make_runtime_vital`` vs. a login-time vital) -- that
wiring is chief's runtime.py, requested in CORE-REQUEST-007.
"""

FIELD_A_TAG = 0x0B
FIELD_B_TAG = 0x0B
FIELD_C_TAG = 0x14

SPAN_SHA256 = "03b186737b43884c61c7e82dc9805f7ee161cce3ae3436f2c5d0a5db8033c661"


def make_gm_state_body(legacy, field_a: int, field_b: int, field_c: int) -> bytes:
    """Compose the three proven fields in their proven order.

    ``legacy`` is any object exposing ``u8tag``/``u32tag`` with the same
    signature as the frozen v141 projector (see legacy_bridge.py) -- this
    module never imports or hand-encodes those tags itself.
    """
    for name, value in (("field_a", field_a), ("field_b", field_b)):
        if not 0 <= value <= 0xFF:
            raise ValueError("%s must fit in the proven 1-byte field" % name)
    if not 0 <= field_c <= 0xFFFFFFFF:
        raise ValueError("field_c must fit in the proven 4-byte field")
    return (
        legacy.u8tag(FIELD_A_TAG, field_a)
        + legacy.u8tag(FIELD_B_TAG, field_b)
        + legacy.u32tag(FIELD_C_TAG, field_c)
    )


def for_gm_grant(legacy) -> bytes:
    """[SMMUT_LANE_GM_ROR_RE] field_a=1, field_b=0, field_c=0 -- unconfirmed."""
    return make_gm_state_body(legacy, field_a=1, field_b=0, field_c=0)


def for_gm_revoke(legacy) -> bytes:
    """The all-zero body -- the one value nobody disputes means "not a GM"."""
    return make_gm_state_body(legacy, field_a=0, field_b=0, field_c=0)
