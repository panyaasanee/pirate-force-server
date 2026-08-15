"""Narrow serializer for the exact Scene2 MOBS34/P60 candidate."""
import math, struct

def make_scene_remote_actor(legacy, profile):
    profile_key = (profile.placement_index, profile.actor_identity, profile.template_id,
        profile.visual_preset, profile.name, profile.faction,
        profile.position.scene_id, profile.position.scene_seq,
        profile.position.x, profile.position.y, profile.position.z, profile.position.heading)
    if profile_key not in {
        (60, 0x203D, 34, "M025_001_000_N", "Fighting Fish soldier", 6, 2, 0,
         21421.0059, 9277.1123, 590.6788, 0),
        (60, 0x203D, 34, "M025_001_000_N", "Fighting Fish soldier", 6, 1, 0,
         1788.796875, -1121.6756591796875, 930.423583984375, 0),
    }:
        raise ValueError("unsupported Scene2 remote actor profile")
    p=profile.position
    if not all(math.isfinite(v) for v in (p.x,p.y,p.z,p.heading)):
        raise ValueError("non-finite remote actor position")
    if profile.diagnostic_hp not in (None, 3857):
        raise ValueError("only the bounded level-27 HP diagnostic is allowed")
    basic_mask=0x0001|0x0100|0x0200|0x0400
    if profile.diagnostic_hp is not None:
        basic_mask |= 0x0004|0x0008
    hp = (legacy.u32tag(0x14, profile.diagnostic_hp) * 2
          if profile.diagnostic_hp is not None else b"")
    npc_attr=(legacy.u8tag(0x0B,1)+legacy.qwordtag(0x32,profile.actor_identity)
        +legacy.u16tag(0x12,basic_mask)+legacy.wstr_tag(profile.name)+hp
        +legacy.u16tag(0x12,2)+legacy.qwordtag(0x32,0)+legacy.u32tag(0x14,6)
        +legacy.u8tag(0x0B,0x05)+legacy.u16tag(0x12,34)+legacy.wstr_tag(profile.visual_preset))
    movement=legacy.make_remote_movement_attr(profile.actor_identity,p.x,p.y,p.z,p.heading,mask=0xFF)
    entry=legacy.make_remote_actor_entry(4,profile.actor_identity,
        [(legacy.NPC_ATTR,npc_attr),(legacy.MOVEMENT_ATTR,movement)])
    return legacy.make_runtime_remote_actors([entry])

def is_scene_remote_target(legacy, parsed, actor_identity):
    if not (parsed.outer_id==legacy.GSCN_RUNTIME_PROTOCOL_REQ and parsed.outer_version==0
        and parsed.outer_mask==2 and parsed.nested_id==legacy.TARGET_VITAL
        and parsed.nested_version==0 and parsed.vital_count==1): return False
    try:
        cursor=legacy.Cursor(parsed.nested_payload)
        return (struct.unpack("<Q",cursor.raw8(0x32))[0]==actor_identity
            and cursor.u8(0x08)==2 and cursor.remain()==0)
    except (ValueError,struct.error): return False

def is_scene_remote_hostile_target(legacy, parsed, actor_identity):
    """SCENE-007-only exact TargetVital kind 1 gate; kind 2 stays unchanged."""
    if not (parsed.outer_id==legacy.GSCN_RUNTIME_PROTOCOL_REQ and parsed.outer_version==0
        and parsed.outer_mask==2 and parsed.nested_id==legacy.TARGET_VITAL
        and parsed.nested_version==0 and parsed.vital_count==1): return False
    try:
        cursor=legacy.Cursor(parsed.nested_payload)
        return (struct.unpack("<Q",cursor.raw8(0x32))[0]==actor_identity
            and cursor.u8(0x08)==1 and cursor.remain()==0)
    except (ValueError,struct.error): return False
