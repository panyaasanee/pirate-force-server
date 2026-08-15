"""Projection seam into frozen V141 serializers; no gameplay behavior is changed."""
import importlib.util
import struct
import sys
from pathlib import Path

def load_legacy(path: str | Path):
    spec = importlib.util.spec_from_file_location("pf_legacy_v141", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

class LegacyProjector:
    def __init__(self, legacy):
        self.v = legacy

    def character_list(self, characters):
        payload = (self.v.u8tag(0x0B,0)+self.v.u32tag(0x14,0)+self.v.u32tag(0x14,0)+
                   self.v.u32tag(0x1F,0)+self.v.u8tag(0x0B,0)+self.v.u8tag(0x0B,len(characters))+
                   b"".join(c.actor_wire for c in characters)+self.v.u8tag(0x0B,0)+self.v.u8tag(0x0B,0))
        return self.v.make_runtime_vital(self.v.SELECT_ACTOR_VITAL, 10, payload)

    def create_success(self, character):
        return self.v.make_runtime_create_actor_success(character.actor_wire)

    def movement_attr(self, character):
        """Project the persisted position without changing the frozen zero-heading wire."""
        p = character.position
        return (
            self.v.u8tag(0x0B, 1)
            + bytes([0x32])
            + struct.pack("<II", character.identity_lo & 0xFFFFFFFF,
                          character.identity_hi & 0xFFFFFFFF)
            + self.v.u8tag(0x0B, 0xFF)
            + self.v.f32tag(p.x) + self.v.f32tag(p.y) + self.v.f32tag(p.z)
            + self.v.f32tag(p.heading)
            + self.v.u8tag(0x0B, 0)
            + self.v.u32tag(0x26, 0)
            + self.v.f32tag(0.0) * 3
        )

    def start_game(self, character):
        p = character.position
        actor = self.v.make_actor_attr_minimal(character.identity_lo, character.identity_hi, p.scene_id, p.scene_seq)
        avatar = character.avatar_wire
        movement = self.movement_attr(character)
        payload = (self.v.u8tag(0x08,character.selector)+self.v.u8tag(0x05,0)+self.v.u8tag(0x0B,2)+
                   self.v.u16tag(0x0F,3)+self.v.u16tag(0x0F,0)+self.v.u8tag(0x0B,4)+
                   self.v.u16tag(0x12,0x12AD)+actor+self.v.u16tag(0x12,0x16A0)+avatar+
                   self.v.u16tag(0x12,0x2067)+movement+self.v.u16tag(0x12,self.v.BACKPACK_ATTR)+
                   self.v.make_backpack_attr_four_items()+self.v.u8tag(0x0B,0))
        return self.v.make_login_vital(self.v.START_GAME_RES, 3, payload)
