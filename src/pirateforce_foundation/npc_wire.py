"""Narrow modular extensions to the frozen legacy NPCAttr serializer."""


def make_npc_attr_with_basic_faction(
    legacy,
    template_id: int,
    actor_identity: int,
    scene_id: int,
    scene_seq: int,
    visual_preset: str,
    current_hp: int,
    max_hp: int,
    basic_name: str,
    basic_faction: int,
) -> bytes:
    """Serialize the proven BasicAttr 0x0400/u32 field in canonical order.

    This is deliberately not a general BasicAttr implementation.  It accepts
    only the P30 diagnostic value whose producer/consumer order is known, and
    leaves the immutable V141 serializer untouched.
    """
    if type(basic_faction) is not int or basic_faction != 6:
        raise ValueError("only the proven diagnostic BasicAttr faction value 6 is allowed")
    if (
        template_id != 31
        or actor_identity != legacy.V112_MONSTER_ACTOR_ID
        or scene_id != 1
        or scene_seq != 0
        or current_hp != legacy.V117_P30_EXACT_HP
        or max_hp != legacy.V117_P30_EXACT_HP
        or basic_name != legacy.V119_P30_TARGET_NAME
        or not visual_preset
    ):
        raise ValueError("the diagnostic serializer accepts only the complete proven P30 profile")

    basic_mask = 0x0001 | 0x0004 | 0x0008 | 0x0100 | 0x0200 | 0x0400
    npc_mask = 0x01 | 0x04
    return (
        legacy.u8tag(0x0B, 1)
        + legacy.qwordtag(0x32, actor_identity)
        + legacy.u16tag(0x12, basic_mask)
        + legacy.wstr_tag(basic_name)
        + legacy.u32tag(0x14, current_hp)
        + legacy.u32tag(0x14, max_hp)
        + legacy.u16tag(0x12, scene_id)
        + legacy.qwordtag(0x32, scene_seq)
        # BasicAttr bit 0x0400 follows the 0x0200 SceneSeq field.
        + legacy.u32tag(0x14, basic_faction)
        + legacy.u8tag(0x0B, npc_mask)
        + legacy.u16tag(0x12, template_id)
        + legacy.wstr_tag(visual_preset)
    )
