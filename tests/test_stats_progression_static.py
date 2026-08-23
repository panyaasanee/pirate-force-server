"""PF STATS-PROG-001 - static byte-exact reconstruction of the client's character
STATS AND PROGRESSION surface. Opens `character_management/stats_and_progression`
not_started -> in_progress.

The lane's coverage note said "No level, experience, attribute point, or
progression rule is modeled, persisted, or captured." This test pins, from the
read-only client binary alone:

  * COHORT. 14 classes register through the PF-NAMEID-HASH-001 once-init thunk
    shape (push <name literal>; call 0x89C080; mov ecx,eax; call 0x89BD00;
    mov word[id-slot],ax; ret). Re-applying the hash at 0x89B220 reproduces
    ActorAttr 0x12AD, NPCAttr 0x0AD5 and UpdateAttrVital 0x309A - three ids v141
    already carries as committed constants - which anchors the other eleven.
  * HIERARCHY (registrar 0x88F2E0 + `.?AV...@@` descriptors):
    Attribute -> DBAttribute -> BasicAttr -> {ActorAttr, NPCAttr}; AvatarAttr and
    CSkillAttr off DBAttribute; FightAttr off Attribute; the six progression
    vitals share the vital base node 0x10823A8.
  * WIRE SCHEMAS. Attr serializers live at vtable +0x34, vitals at +0x18, and all
    of them are dirty-mask gated: DBAttribute u8 mask @+0x20, BasicAttr u16 mask
    @+0x70, ActorAttr u64 mask @+0x1B4/+0x1B8, AvatarAttr u32 mask @+0x28.
  * NAMED FIELDS, each tied to an in-image consumer and never to genre habit:
    level = BasicAttr u16 +0x5E (script binding "GetLv" handler 0x460050);
    HP/MP = BasicAttr u32 +0x44/+0x48 and +0x4C/+0x50 (HUD updater 0x53F1AD
    feeding PROGRESSBAR_HP / PROGRESSBAR_MP); experience = ActorAttr qword +0xA0
    (exp bar 0x519299 divides it by STANDARD_STATUS[level+1].n_EXP_CURRENTLV);
    class = ActorAttr u32 +0x8C ("GetClass"); skill points = ActorAttr u32 +0x7C
    (NUMBERLABEL_SPNOW refresh 0x75C613); unspent allocation points = ActorAttr
    u16 +0x80 (spinner cap 0x57DD7A, +/- gate 0x53B1FB); STR/CON/DEX/INT/PER =
    ActorAttr u16 +0x82/84/86/88/8A with bonuses at +0x182/184/186/188/18A.
  * VERBS. AbilityDepolyAll 0x36AD carries exactly five i16 deltas in the order
    STR, CON, DEX, INT, PER - proven by the Char_Info2 UP-button handler and the
    producer that lifts those five counters. AbilityDepoly 0x260B has one single
    producer that always sends the fixed triple (1, 6, 1).
  * NEGATIVES. AddExp / AddAbilityPoint / AddSkillPoint only broadcast a local
    event token ("exp"/"ap"/"sp") and build no vital. Attribute and FightAttr both
    point their serializer slot at `ret 8` and carry zero wire fields.

NOT CLAIMED: anything about the ORIGINAL server, any runtime capture, any
persistence. See
reports/PF_STATS_PROG001_CHARACTER_STATS_AND_PROGRESSION_STATIC_20260818.md.
The lane stays in_progress and never flips to runtime_pass here.
"""
from __future__ import annotations

import ast
import re
import struct
import sys
import unittest
import warnings
from pathlib import Path

import capstone

ROOT = Path(__file__).resolve().parents[1]
# The proprietary client image cannot be in a fresh clone; every test that reads
# it carries its own @CLIENT_IMAGE guard below - see tests/pf_preconditions.py.
sys.path.insert(0, str(ROOT / "tests"))
from pf_preconditions import CLIENT_IMAGE

BINARY_CANDIDATES = [
    ROOT.parent / "GameClient" / "GameClient.local.bin",
    ROOT / "GameClient" / "GameClient.local.bin",
    ROOT / "packages" / ".v134_staging_20260815_0355" / "GameClient.local.bin",
]
BINARY = next((p for p in BINARY_CANDIDATES if p.is_file()), BINARY_CANDIDATES[0])
BINARY_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
SERVER = ROOT / "current" / "pf_login_game_server_v141.py"
SRC_DIR = ROOT / "src"

ONCE_INIT = 0x89C080
ID_ASSIGN = 0x89BD00
HASH_FN = 0x89B220
TYPE_REG = 0x88F2E0
SCAL_W, SCAL_R = 0x89A600, 0x89A640
WSTR_W, WSTR_R = 0x89A810, 0x89A880
BLOB_W, BLOB_R = 0x89A6D0, 0x89A700
WRITE_CODECS = {SCAL_W: "s", WSTR_W: "w", BLOB_W: "b"}
READ_CODECS = {SCAL_R, WSTR_R, BLOB_R}
COHORT_CONST = 0x401B20          # shared framework const of this whole family
NOOP_SER = 0x515EC0              # `ret 8` - the empty serializer slot
WIDGET_LOOKUP = 0xAA1750         # thiscall FindChild(name) -> widget*
PLAYER_ATTR = 0x1032EC4          # module registry root; +0x348 = local player Attr
EVENT_BROADCAST = 0x5F9C70       # local listener fan-out (registry+0x130)
UI_SEND = 0x5DD800               # outbound vital submit
VITAL_BASE_NODE = 0x10823A8

# name, name VA, reg thunk, id-slot, get-id stub, vtable, sizeof, type node,
# serializer vtable slot, serializer VA
COHORT = [
    ("Attribute",              0xF0E748, 0xBD92D0, 0x1033458, 0x467640, 0xF0E850, None,  0x103344C, 0x34, 0x515EC0),
    ("DBAttribute",            0xF0E8D0, 0xBD9530, 0x10334B8, 0x467680, 0xF0E890, 0x28,  0x10334AC, 0x34, 0x467790),
    ("BasicAttr",              0xF0E820, 0xBD93B0, 0x103349C, 0x464A60, 0xF0E760, 0x78,  0x1033490, 0x34, 0x4656F0),
    ("ActorAttr",              0xF0E82C, 0xBD93D0, 0x10334A0, 0x464E40, 0xF0E7A0, 0x1C0, 0x1033484, 0x34, 0x466230),
    ("NPCAttr",                0xF0E838, 0xBD93F0, 0x10334A4, 0x4652C0, 0xF0E7E0, 0xC0,  0x1033478, 0x34, 0x466EB0),
    ("AvatarAttr",             0xF0E754, 0xBD9350, 0x1033468, 0x45E150, 0xF0E088, 0x90,  0x103345C, 0x34, 0x464560),
    ("FightAttr",              0xF0E920, 0xBD95A0, 0x10334CC, 0x467A20, 0xF0E8E0, 0x1C,  0x10334C0, 0x34, 0x515EC0),
    ("CSkillAttr",             0xF48BB8, 0xC0C530, 0x108A32C, 0x751BF0, 0xF48B78, 0x50,  0x108A320, 0x34, 0x7520B0),
    ("UpdateAttrVital",        0xF0B374, 0xBEE5C0, 0x1082028, 0x5E5DB0, 0xF303E0, 0x44,  0x1081E70, 0x18, 0x5E42C0),
    ("AbilityDepoly",          0xF30918, 0xBEE580, 0x1082020, 0x5E5BA0, 0xF30398, 0x18,  0x1081E88, 0x18, 0x5E5BB0),
    ("AbilityDepolyAll",       0xF30928, 0xBEE5A0, 0x1082024, 0x5E5C70, 0xF303BC, 0x20,  0x1081E7C, 0x18, 0x5E5C80),
    ("CLearnSkillVital",       0xF48F00, 0xC0C860, 0x108A3F4, 0x755AA0, 0xF48E94, 0x1C,  0x108A3E8, 0x18, 0x755AC0),
    ("CLearnSkillResultVital", 0xF0B54C, 0xC0C880, 0x108A3F8, 0x755E90, 0xF48EDC, 0x30,  0x108A3DC, 0x18, 0x756100),
    ("CRevertSkilltVital",     0xF48F14, 0xC0C8A0, 0x108A3FC, 0x755B50, 0xF48EB8, 0x20,  0x108A3D0, 0x18, 0x755B70),
]
EXPECT_IDS = {
    "Attribute": 0x1306, "DBAttribute": 0x1B36, "BasicAttr": 0x1244,
    "ActorAttr": 0x12AD, "NPCAttr": 0x0AD5, "AvatarAttr": 0x16A0,
    "FightAttr": 0x1285, "CSkillAttr": 0x1661, "UpdateAttrVital": 0x309A,
    "AbilityDepoly": 0x260B, "AbilityDepolyAll": 0x36AD,
    "CLearnSkillVital": 0x36AA, "CLearnSkillResultVital": 0x673C,
    "CRevertSkilltVital": 0x45F0,
}
V141_ANCHORS = {"ActorAttr": 0x12AD, "NPCAttr": 0x0AD5, "UpdateAttrVital": 0x309A}
EXPECT_PARENT = {
    "Attribute": None, "DBAttribute": "Attribute", "BasicAttr": "DBAttribute",
    "ActorAttr": "BasicAttr", "NPCAttr": "BasicAttr", "AvatarAttr": "DBAttribute",
    "FightAttr": "Attribute", "CSkillAttr": "DBAttribute",
    "UpdateAttrVital": "*vital-base*", "AbilityDepoly": "*vital-base*",
    "AbilityDepolyAll": "*vital-base*", "CLearnSkillVital": "*vital-base*",
    "CLearnSkillResultVital": "*vital-base*", "CRevertSkilltVital": "*vital-base*",
}
NODE_OF = {c[7]: c[0] for c in COHORT}

# serializer write-path bounds: [start, first read-codec call)
SER_BOUNDS = {
    "DBAttribute": (0x467790, 0x4677C9), "BasicAttr": (0x4656F0, 0x465850),
    "ActorAttr": (0x466230, 0x466767), "NPCAttr": (0x466EB0, 0x467010),
    "AvatarAttr": (0x464560, 0x46476E), "CSkillAttr": (0x7520B0, 0x752290),
    "AbilityDepoly": (0x5E5BB0, 0x5E5BF1), "AbilityDepolyAll": (0x5E5C80, 0x5E5CDF),
    "CLearnSkillVital": (0x755AC0, 0x755AF2),
    "CRevertSkilltVital": (0x755B70, 0x755BA2),
    "CLearnSkillResultVital": (0x756100, 0x756130),
}
# (kind, base register, displacement, tag, width) in emission order
SCHEMA = {
    "DBAttribute": [('s', 'esi', 0x20, 0x0B, 1), ('s', 'esi', 0x18, 0x32, 8)],
    "BasicAttr": [
        ('s', 'esi', 0x70, 0x12, 2), ('w', 'esi', 0x28, 0x48, None),
        ('s', 'esi', 0x5E, 0x12, 2), ('s', 'esi', 0x44, 0x14, 4),
        ('s', 'esi', 0x48, 0x14, 4), ('s', 'esi', 0x4C, 0x14, 4),
        ('s', 'esi', 0x50, 0x14, 4), ('s', 'esi', 0x54, 0x2A, 4),
        ('s', 'esi', 0x58, 0x2A, 4), ('s', 'esi', 0x5C, 0x12, 2),
        ('s', 'esi', 0x60, 0x32, 8), ('s', 'esi', 0x68, 0x14, 4),
        ('s', 'esi', 0x6C, 0x14, 4)],
    "ActorAttr": [
        ('s', 'esp', 0x14, 0x32, 8), ('s', 'esi', 0x1BC, 0x05, 1),
        ('s', 'esi', 0x8C, 0x19, 4), ('s', 'esi', 0x90, 0x19, 4),
        ('s', 'esi', 0x78, 0x26, 4), ('s', 'esi', 0x7C, 0x19, 4),
        ('s', 'esi', 0x80, 0x12, 2), ('s', 'esi', 0x82, 0x12, 2),
        ('s', 'esi', 0x84, 0x12, 2), ('s', 'esi', 0x86, 0x12, 2),
        ('s', 'esi', 0x88, 0x12, 2), ('s', 'esi', 0x8A, 0x12, 2),
        ('s', 'esi', 0xA0, 0x32, 8), ('s', 'esi', 0xA8, 0x32, 8),
        ('w', 'esi', 0xB0, 0x48, None), ('s', 'esi', 0x99, 0x0B, 1),
        ('s', 'esi', 0x9A, 0x0B, 1), ('s', 'esi', 0x13E, 0x12, 2),
        ('s', 'esi', 0x13C, 0x12, 2), ('b', 'esi', 0x148, 0x44, None),
        ('s', 'esi', 0x182, 0x12, 2), ('s', 'esi', 0x184, 0x12, 2),
        ('s', 'esi', 0x186, 0x12, 2), ('s', 'esi', 0x188, 0x12, 2),
        ('s', 'esi', 0x18A, 0x12, 2), ('s', 'esi', 0x18C, 0x0B, 1),
        ('w', 'esi', 0x164, 0x48, None), ('s', 'esi', 0x180, 0x0B, 1),
        ('s', 'esi', 0x98, 0x0B, 1), ('s', 'esi', 0x94, 0x19, 4),
        ('s', 'esi', 0x140, 0x32, 8), ('s', 'esi', 0x9B, 0x0B, 1),
        ('w', 'esi', 0xCC, 0x48, None), ('s', 'esi', 0x198, 0x32, 8),
        ('s', 'esi', 0x190, 0x32, 8), ('s', 'esi', 0x1A0, 0x0B, 1),
        ('s', 'esi', 0x1A2, 0x12, 2), ('s', 'esi', 0x1A4, 0x12, 2),
        ('w', 'esi', 0xE8, 0x48, None), ('w', 'esi', 0x104, 0x48, None),
        ('w', 'esi', 0x120, 0x48, None), ('s', 'esi', 0x1A8, 0x14, 4),
        ('s', 'esi', 0x1AC, 0x14, 4), ('s', 'esi', 0x1B0, 0x12, 2),
        ('s', 'esi', 0x1B2, 0x0B, 1)],
    "NPCAttr": [
        ('s', 'esi', 0xBC, 0x0B, 1), ('s', 'esi', 0x78, 0x12, 2),
        ('s', 'esi', 0x7A, 0x0B, 1), ('w', 'esi', 0x7C, 0x48, None),
        ('s', 'esi', 0x98, 0x32, 8), ('s', 'esi', 0xA8, 0x32, 8),
        ('s', 'esi', 0xA0, 0x32, 8), ('s', 'esi', 0xB0, 0x32, 8)],
    "AvatarAttr": [
        ('s', 'esi', 0x28, 0x26, 4), ('s', 'esi', 0x2C, 0x14, 4),
        ('s', 'esi', 0x30, 0x14, 4), ('s', 'esi', 0x34, 0x14, 4),
        ('s', 'esi', 0x38, 0x14, 4), ('s', 'esi', 0x3C, 0x14, 4),
        ('s', 'esi', 0x40, 0x14, 4), ('s', 'esi', 0x44, 0x14, 4),
        ('s', 'esi', 0x48, 0x14, 4), ('s', 'esi', 0x4C, 0x14, 4),
        ('s', 'esi', 0x50, 0x14, 4), ('s', 'esi', 0x54, 0x14, 4),
        ('s', 'esi', 0x58, 0x14, 4), ('s', 'esi', 0x5C, 0x0B, 1),
        ('s', 'esi', 0x5D, 0x08, 1), ('s', 'esi', 0x5E, 0x08, 1),
        ('b', 'esi', 0x64, 0x44, None), ('s', 'esi', 0x60, 0x0B, 1),
        ('s', 'esi', 0x80, 0x14, 4), ('s', 'esi', 0x5F, 0x0B, 1),
        ('s', 'esi', 0x84, 0x0B, 1), ('s', 'esi', 0x88, 0x14, 4)],
    "CSkillAttr": [
        # ESP/EBX-relative stack temps, NOT object offsets - see the report.
        ('s', 'esp', 0x44, 0x12, 2), ('s', 'esp', 0x40, 0x12, 2),
        ('s', 'ebx', 0x10, 0x12, 2), ('s', 'ebx', 0x14, 0x14, 4)],
    "AbilityDepoly": [
        ('s', 'esi', 0x14, 0x08, 1), ('s', 'esi', 0x15, 0x08, 1),
        ('s', 'esi', 0x16, 0x0F, 2)],
    "AbilityDepolyAll": [('s', 'esi', 0x14 + 2 * k, 0x0F, 2) for k in range(5)],
    "CLearnSkillVital": [('s', 'esi', 0x14, 0x14, 4), ('s', 'esi', 0x18, 0x0B, 1)],
    "CRevertSkilltVital": [('s', 'esi', 0x14, 0x14, 4), ('s', 'esi', 0x18, 0x32, 8)],
    "CLearnSkillResultVital": [('s', 'esi', 0x2C, 0x0B, 1)],
}
TAG_WIDTH = {0x05: 1, 0x08: 1, 0x0B: 1, 0x0F: 2, 0x12: 2, 0x14: 4,
             0x19: 4, 0x26: 4, 0x2A: 4, 0x32: 8}

# owner, offset, mask bit, tag, meaning
NAMED_FIELDS = [
    ("BasicAttr", 0x5E, 0x0002, 0x12, "level"),
    ("BasicAttr", 0x44, 0x0004, 0x14, "hp current"),
    ("BasicAttr", 0x48, 0x0008, 0x14, "hp max"),
    ("BasicAttr", 0x4C, 0x0010, 0x14, "mp current"),
    ("BasicAttr", 0x50, 0x0020, 0x14, "mp max"),
    ("ActorAttr", 0x8C, 0x00000001, 0x19, "class"),
    ("ActorAttr", 0x7C, 0x00000008, 0x19, "skill points"),
    ("ActorAttr", 0x80, 0x00000010, 0x12, "unspent allocation points"),
    ("ActorAttr", 0x82, 0x00000020, 0x12, "STR base"),
    ("ActorAttr", 0x84, 0x00000040, 0x12, "CON base"),
    ("ActorAttr", 0x86, 0x00000080, 0x12, "DEX base"),
    ("ActorAttr", 0x88, 0x00000100, 0x12, "INT base"),
    ("ActorAttr", 0x8A, 0x00000200, 0x12, "PER base"),
    ("ActorAttr", 0xA0, 0x00000400, 0x32, "experience"),
    ("ActorAttr", 0x182, 0x00040000, 0x12, "STR bonus"),
    ("ActorAttr", 0x184, 0x00080000, 0x12, "CON bonus"),
    ("ActorAttr", 0x186, 0x00100000, 0x12, "DEX bonus"),
    ("ActorAttr", 0x188, 0x00200000, 0x12, "INT bonus"),
    ("ActorAttr", 0x18A, 0x00400000, 0x12, "PER bonus"),
]
GATE_PIN = {
    (0x4656F0, 0x5E): (0x465736, "f60302"),
    (0x4656F0, 0x44): (0x46574A, "f60304"),
    (0x4656F0, 0x48): (0x46575E, "f60308"),
    (0x4656F0, 0x4C): (0x465772, "f60310"),
    (0x4656F0, 0x50): (0x465786, "f60320"),
    (0x466230, 0x8C): (0x466299, "a801"),
    (0x466230, 0x7C): (0x4662EC, "f686b401000008"),
    (0x466230, 0x80): (0x466304, "f686b401000010"),
    (0x466230, 0x82): (0x46631F, "f686b401000020"),
    (0x466230, 0x84): (0x46633A, "f686b401000040"),
    (0x466230, 0x86): (0x466355, "f686b401000080"),
    (0x466230, 0x88): (0x466370, "859eb4010000"),
    (0x466230, 0x8A): (0x46638A, "f786b401000000020000"),
    (0x466230, 0xA0): (0x4663A8, "f786b401000000040000"),
    (0x466230, 0xA8): (0x4663C6, "f786b401000000080000"),
    (0x466230, 0x182): (0x466490, "f786b401000000000400"),
    (0x466230, 0x184): (0x4664AE, "f786b401000000000800"),
    (0x466230, 0x186): (0x4664CC, "f786b401000000001000"),
    (0x466230, 0x188): (0x4664EA, "f786b401000000002000"),
    (0x466230, 0x18A): (0x466508, "f786b401000000004000"),
}
GATE_EBX_100 = (0x46628C, "bb00010000")

ANCHORS = {
    "GetLv_registration":  (0x461ADE, "68e00a4600685ce6f0008d4c242cc74424245000460089742428"),
    "GetLv_reads_0x5E":    (0x460050, "a1c42e030183ec0885c074248b80480300000fb7485e"),
    "GetClass_reads_0x8C": (0x46016C, "8b80480300008b888c000000"),
    "GetCash_reads_0xA8":  (0x4600AC, "8b80480300008b88a8000000"),
    "exp_open_table":      (0x519260, "68ac52f100b9d0cd0801"),
    "exp_level_lookup":    (0x519299, "8b0dc42e03018b89480300000fb7495e0fb7d16a0068004cf1004252"),
    "exp_reads_0xA0":      (0x5192C6, "a1c42e03018b80480300008b88a00000008b80a4000000"),
    "exp_percentage":      (0x519314, "8b86800000006bc06499f7ff"),
    "hud_attr_load":       (0x53F1AD, "8bb848030000"),
    "hud_hp_pair":         (0x53F1D3, "8b4744518b4f4852"),
    "hud_mp_pair":         (0x53F1E4, "8b6e248b5f4c8b47508b4e20"),
    "hud_binder_shape":    (0x53ED28, "68b429f2008bce894614"),
    "skillpoint_read":     (0x75C613, "8b88480300008b497c398ea0000000"),
    "skillpoint_to_label": (0x75C624, "8b466c898ea0000000898820020000"),
    "getter_STR":          (0x467A90, "0fb788820100000fb7b082000000"),
    "getter_CON":          (0x467B20, "0fb788840100000fb7b084000000"),
    "getter_DEX":          (0x467BB0, "0fb788860100000fb7b086000000"),
    "getter_INT":          (0x467CD0, "0fb788880100000fb7b088000000"),
    "getter_PER":          (0x467C40, "0fb7888a0100000fb7b08a000000"),
    "point_pool_spinner":  (0x57DD6F, "a1c42e03018b88480300000fb79180000000"),
    "point_pool_gate":     (0x53B1DF, "a1c42e030185c0746d8b4e4453578bb848030000"),
    "depolyall_producer":  (0x57F733, "0fb78fc8010000668948140fb797cc010000668950160fb78f"
                                      "d0010000668948180fb797d40100006689501a0fb78fd8"),
    "depoly_producer":     (0x57F83B, "e870e7ffff50c6401506"),
    "depoly_ctor":         (0x5E5B60, "8bc133c9884804894808c7006c6df80089480c884810884811"
                                      "884815b901000000c7009803f300c640140166894816c3"),
    "depolyall_ctor":      (0x5E5C20, "8bc133c933d2c7006c6df80088480489480889480c884810884811"
                                      "c700bc03f3006689481466895016668948186689501a6689481cc3"),
    "actorattr_mask64":    (0x466252, "8b8eb80100008b86b40100008d54241452"),
    "AddExp_token":        (0x460F44, "68cce1f0008d4c2458c68424a400000001c744242808000000"),
    "AddAbilityPoint_tok": (0x461324, "68d8e1f0008d4c2458c68424a400000001c744242808000000"),
    "AddSkillPoint_token": (0x461454, "68dce1f0008d4c2458c68424a400000001c744242808000000"),
}
SCRIPT_BINDINGS = {
    "GetLv":           (0xF0E65C, 0x461ADE, 0x460050),
    "GetCash":         (0xF0E638, 0x461B6B, 0x4600A0),
    "GetClass":        (0xF0E530, 0x461F75, 0x460160),
    "AddExp":          (0xF0E628, 0x461BC9, 0x460EC0),
    "AddAbilityPoint": (0xF0E5F0, 0x461CB4, 0x4612A0),
    "AddSkillPoint":   (0xF0E5E0, 0x461CE3, 0x4613D0),
}
LOCAL_EVENT_TOKENS = {"AddExp": (0xF0E1CC, "exp"),
                      "AddAbilityPoint": (0xF0E1D8, "ap"),
                      "AddSkillPoint": (0xF0E1DC, "sp")}
EVENT_CALL_SITES = {0x460EC0: 0x460F94, 0x4612A0: 0x461374, 0x4613D0: 0x4614A4}

TABLE_LITERALS = {
    0xF152AC: "STANDARD_STATUS", 0xF14C00: "n_EXP_CURRENTLV",
    0xF14BE0: "n_POINT_ABILITY", 0xF14F24: "n_HPMAX", 0xF14EEC: "n_STAMINAMAX",
    0xF14B94: "POTENTIAL", 0xF14B84: "n_LEVEL", 0xF14B70: "n_STRENGH",
    0xF14B50: "n_CONSTITUTION", 0xF14B3C: "n_AGILITY", 0xF14B24: "n_INTELLECT",
    0xF14B08: "n_PERCEPTION",
}
CHARINFO_BINDER = (0x583F00, 0x5856A0)
CHARINFO_EXPECT = {
    "LABEL_STR": 0x84, "LABEL_CON": 0x88, "LABEL_DEX": 0x8C,
    "LABEL_INT": 0x90, "LABEL_PER": 0x94,
    "LABEL_DEPLOY_STR": 0x98, "LABEL_DEPLOY_CON": 0x9C, "LABEL_DEPLOY_DEX": 0xA0,
    "LABEL_DEPLOY_INT": 0xA4, "LABEL_DEPLOY_PER": 0xA8,
    "BUTTON_STRUP": 0xD4, "BUTTON_CONUP": 0xD8, "BUTTON_DEXUP": 0xDC,
    "BUTTON_INTUP": 0xE0, "BUTTON_PERUP": 0xE4,
}
HUD_BINDER = (0x53EC00, 0x53EED0)
HUD_EXPECT = {"PROGRESSBAR_HP": 0x18, "NUMBERLABEL_HP": 0x1C,
              "PROGRESSBAR_MP": 0x20, "NUMBERLABEL_MP": 0x24}
SKILL_BINDER = (0x759C40, 0x759D40)
CHARINFO_UPDATE = [
    (0x57E6C8, 0x467A60, 0x84, "STR"), (0x57E6EB, 0x467AF0, 0x88, "CON"),
    (0x57E70E, 0x467B80, 0x8C, "DEX"), (0x57E731, 0x467CA0, 0x90, "INT"),
    (0x57E754, 0x467C10, 0x94, "PER"),
]
CHARINFO_CLICK_DELTA = {
    "STR": (0x57C25E, "ff86c8010000"), "CON": (0x57C2B1, "01becc010000"),
    "DEX": (0x57C2FF, "01bed0010000"), "INT": (0x57C34D, "01bed4010000"),
    "PER": (0x57C398, "01bed8010000"),
}
DEPOLY_POOL, DEPOLYALL_POOL = 0x57DFB0, 0x57E0C0
DEPOLY_CTOR, DEPOLYALL_CTOR = 0x5E5B60, 0x5E5C20
DEPOLY_POOL_CALLERS = [0x57F83B, 0x5EB07C]
DEPOLYALL_POOL_CALLERS = [0x57F72A, 0x5EB09C]

PROGRESSION_VERBS = ["AbilityDepoly", "AbilityDepolyAll", "CLearnSkillVital",
                     "CLearnSkillResultVital", "CRevertSkilltVital", "CSkillAttr"]


def _name_id(name: str) -> int:
    """PF-NAMEID-HASH-001 / client 0x89B220 - re-used verbatim, not re-derived."""
    acc = 0
    for i, ch in enumerate(name.encode("latin1")):
        sc = ch if ch < 128 else ch - 256
        acc = (acc + ((sc * (i + 1)) & 0xFFFF)) & 0xFFFF
    return acc


class _Image:
    """Minimal PE view: VA -> bytes, plus the .text/.rdata extents."""

    def __init__(self, path: Path):
        self.data = path.read_bytes()
        d = self.data
        e_lfanew = struct.unpack_from("<I", d, 0x3C)[0]
        coff = e_lfanew + 4
        nsec = struct.unpack_from("<H", d, coff + 2)[0]
        opt_size = struct.unpack_from("<H", d, coff + 16)[0]
        opt = coff + 20
        self.image_base = struct.unpack_from("<I", d, opt + 28)[0]
        sect = opt + opt_size
        self.secs = []
        for i in range(nsec):
            o = sect + i * 40
            nm = d[o:o + 8].rstrip(b"\0").decode("latin1")
            vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
            self.secs.append((nm, va, vs, rp, rs))
        _, tva, tvs, traw, _ = [s for s in self.secs if s[0] == ".text"][0]
        self.text_start, self.text_raw, self.text_size = self.image_base + tva, traw, tvs
        _, rva, _rvs, rraw, rrs = [s for s in self.secs if s[0] == ".rdata"][0]
        self.rdata_start, self.rdata_raw, self.rdata_size = self.image_base + rva, rraw, rrs
        self.md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

    def off(self, va):
        r = va - self.image_base
        for _nm, v, vs, rp, rs in self.secs:
            if v <= r < v + max(vs, rs):
                return rp + (r - v)
        return None

    def va(self, off):
        for _nm, v, _vs, rp, rs in self.secs:
            if rp <= off < rp + rs:
                return self.image_base + v + (off - rp)
        return None

    def rd(self, va, n):
        o = self.off(va)
        return self.data[o:o + n] if o is not None else b""

    def dw(self, va):
        return struct.unpack("<I", self.rd(va, 4))[0]

    def cstr(self, va, maxn=160):
        b = self.rd(va, maxn)
        z = b.find(b"\x00")
        return b[:z].decode("latin1") if z >= 0 else None

    def wstr(self, va, maxn=200):
        b = self.rd(va, maxn)
        z = len(b)
        for i in range(0, len(b) - 1, 2):
            if b[i] == 0 and b[i + 1] == 0:
                z = i
                break
        return b[:z].decode("utf-16le", "replace")

    def dmap(self, va, size):
        return {i.address: (i.mnemonic, i.op_str)
                for i in self.md.disasm(self.rd(va, size), va)}

    def bytes_at(self, va, hexstr):
        want = bytes.fromhex(hexstr)
        return self.rd(va, len(want)) == want

    def text_hits(self, pat):
        res, s, hi = [], self.text_raw, self.text_raw + self.text_size
        while True:
            j = self.data.find(pat, s, hi)
            if j < 0:
                return res
            res.append(self.text_start + (j - self.text_raw))
            s = j + 1

    def rdata_hits(self, val):
        res, s, hi = [], self.rdata_raw, self.rdata_raw + self.rdata_size
        pat = struct.pack("<I", val)
        while True:
            j = self.data.find(pat, s, hi)
            if j < 0:
                return res
            res.append(self.rdata_start + (j - self.rdata_raw))
            s = j + 1

    def call_targets(self, lo, hi, targets):
        out, j = [], self.off(lo)
        end = self.off(hi)
        while True:
            j = self.data.find(b"\xe8", j, end)
            if j < 0:
                return sorted(out)
            rel = struct.unpack_from("<i", self.data, j + 1)[0]
            src = self.va(j)
            if src is not None and src + 5 + rel in targets:
                out.append((src, src + 5 + rel))
            j += 1

    def callers_of(self, target):
        out, j = [], self.text_raw
        while True:
            j = self.data.find(b"\xe8", j, self.text_raw + self.text_size)
            if j < 0:
                return out
            rel = struct.unpack_from("<i", self.data, j + 1)[0]
            src = self.text_start + (j - self.text_raw)
            if src + 5 + rel == target:
                out.append(src)
            j += 1

    def imm16_hits(self, val):
        out = []
        for pfx in (b"\x66\xb8", b"\x66\xb9", b"\x66\xba",
                    b"\x66\x3d", b"\x66\x81\xf8", b"\x66\xa9"):
            out += self.text_hits(pfx + struct.pack("<H", val))
        return out

    # ---- serializer decoding ------------------------------------------------
    def _window(self, csite, back):
        ins = []
        for i in self.md.disasm(self.rd(csite - back, back + 8), csite - back):
            if i.address >= csite:
                return ins if (i.address == csite and i.mnemonic == "call") else None
            ins.append(i)
        return None

    def _field_at(self, csite, kind):
        for back in range(6, 0x30):
            ins = self._window(csite, back)
            if ins is None:
                continue
            off = None
            for i in ins:
                if i.mnemonic == "lea" and "[" in i.op_str:
                    inner = i.op_str.split("[", 1)[1].rstrip("]")
                    if " + " in inner:
                        b, d = inner.split(" + ")
                        if not d.startswith("e"):
                            off = (b, int(d, 16))
                    else:
                        off = (inner, 0)
                elif (i.mnemonic == "add"
                      and i.op_str.split(",")[0] in ("esi", "edi", "ecx", "ebx")):
                    try:
                        off = (i.op_str.split(",")[0],
                               int(i.op_str.split(",")[1].strip(), 16))
                    except ValueError:
                        pass
            if off is None:
                continue
            if kind != "s":
                return off, None, None
            seq = []
            for i in ins:
                if i.mnemonic == "push":
                    try:
                        seq.append(("i", int(i.op_str, 16)))
                    except ValueError:
                        seq.append(("r", None))
            if len(seq) >= 3 and seq[-1][0] == "i" and seq[-2][0] == "r" and seq[-3][0] == "i":
                return off, seq[-1][1], seq[-3][1]
        return None, None, None

    def decode_serializer(self, lo, hi):
        out = []
        for src, tgt in self.call_targets(lo, hi, set(WRITE_CODECS) | READ_CODECS):
            if tgt in READ_CODECS:
                break
            kind = WRITE_CODECS[tgt]
            off, tag, wid = self._field_at(src, kind)
            if kind == "w":
                tag, wid = 0x48, None
            elif kind == "b":
                tag, wid = 0x44, None
            out.append((kind, off[0] if off else None, off[1] if off else None, tag, wid))
        return out

    def parse_widget_binder(self, lo, hi):
        """`push <name>; mov ecx,esi; mov [esi+K],eax; call FindChild` - the store
        holds the PREVIOUS name's result, so the pairing is shifted by one."""
        out, pend, prev = {}, None, None
        for i in self.md.disasm(self.rd(lo, hi - lo), lo):
            if i.mnemonic == "push":
                try:
                    v = int(i.op_str, 16)
                except ValueError:
                    continue
                if self.rdata_start <= v < self.image_base + 0x101A000:
                    s = self.wstr(v)
                    if s and s.isprintable() and len(s) > 1:
                        prev, pend = pend, (s, v)
            elif (i.mnemonic == "mov" and i.op_str.startswith("dword ptr [esi + 0x")
                  and i.op_str.endswith(", eax")):
                if prev:
                    out[prev[0]] = int(i.op_str.split("[esi + ")[1].split("]")[0], 16)
                prev = None
        return out


# Only map the image when the client binary exists; the pure-python and
# server-source tests below must still run without it - see tests/pf_preconditions.py.
IMG = _Image(BINARY) if CLIENT_IMAGE.present else None


class StatsProgressionStatic(unittest.TestCase):
    """Every assertion here is anchored to a byte or an address in the client."""

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        import hashlib
        cls.img = IMG
        # Shared state only; this is not a skip site - the guarded tests below
        # skip one by one via @CLIENT_IMAGE.  See tests/pf_preconditions.py.
        if CLIENT_IMAGE.present:
            got = hashlib.sha256(IMG.data).hexdigest().upper()
            assert got == BINARY_SHA, "client binary drifted: %s" % got
            assert IMG.image_base == 0x400000

    # -- 1 -------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_registration_thunks_have_the_nameid_hash_shape(self):
        for nm, nva, tva, slot, _g, _v, _s, _n, _ss, _ser in COHORT:
            self.assertEqual(self.img.cstr(nva), nm)
            b = self.img.rd(tva, 24)
            self.assertEqual(b[0], 0x68, nm)
            self.assertEqual(b[5], 0xE8, nm)
            self.assertEqual(b[10:12], b"\x8b\xc8", nm)
            self.assertEqual(b[12], 0xE8, nm)
            self.assertEqual(b[17:19], b"\x66\xa3", nm)
            self.assertEqual(b[23], 0xC3, nm)
            self.assertEqual(self.img.cstr(struct.unpack_from("<I", b, 1)[0]), nm)
            self.assertEqual(tva + 10 + struct.unpack_from("<i", b, 6)[0], ONCE_INIT, nm)
            self.assertEqual(tva + 17 + struct.unpack_from("<i", b, 13)[0], ID_ASSIGN, nm)
            self.assertEqual(struct.unpack_from("<I", b, 19)[0], slot, nm)
        # the binary's own spelling, typos and all, is what the hash consumes
        self.assertEqual(self.img.cstr(0xF30918), "AbilityDepoly")
        self.assertEqual(self.img.cstr(0xF48F14), "CRevertSkilltVital")

    # -- 2 -------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_hash_anchor_reproduces_the_three_ids_v141_already_committed(self):
        for nm, want in V141_ANCHORS.items():
            self.assertEqual(_name_id(nm), want, nm)
        self.assertTrue(any(i == ("call", hex(HASH_FN))
                            for i in self.img.dmap(ID_ASSIGN, 64).values()))
        blob = self.img.rd(HASH_FN, 96)
        for op in (b"\x66\x0f\xbe\x3c\x31", b"\x66\x0f\xaf\xfb", b"\x66\x03\xd7"):
            self.assertIn(op, blob)

    # -- 3 -------------------------------------------------------------------
    def test_all_fourteen_ids_derive_from_the_in_image_literals(self):
        derived = {nm: _name_id(nm) for nm, *_ in COHORT}
        self.assertEqual(derived, EXPECT_IDS)
        self.assertEqual(len(set(derived.values())), 14)

    # -- 4 -------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_ids_are_runtime_assigned_never_code_immediates(self):
        for nm, *_ in COHORT:
            self.assertEqual(self.img.imm16_hits(EXPECT_IDS[nm]), [], nm)

    # -- 5 -------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_each_id_slot_has_one_writer_and_one_reader(self):
        for nm, _n, tva, slot, getid, _v, _s, _nd, _ss, _ser in COHORT:
            self.assertEqual(
                self.img.text_hits(b"\x66\xa3" + struct.pack("<I", slot)), [tva + 17], nm)
            self.assertEqual(
                self.img.text_hits(b"\x66\xa1" + struct.pack("<I", slot)), [getid], nm)
            self.assertEqual(self.img.rd(getid, 7),
                             b"\x66\xa1" + struct.pack("<I", slot) + b"\xc3", nm)

    # -- 6 -------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_vtables_carry_cohort_const_getid_sizeof_and_serializer(self):
        for nm, _n, _t, _sl, getid, vt, size, _nd, serslot, ser in COHORT:
            self.assertEqual(self.img.dw(vt + 0x10), getid, nm)
            self.assertEqual(self.img.dw(vt + 0x08), COHORT_CONST, nm)
            self.assertEqual(self.img.dw(vt + serslot), ser, nm)
            self.assertEqual(self.img.rdata_hits(getid), [vt + 0x10], nm)
            if size is not None:
                b = self.img.rd(self.img.dw(vt + 0x0C), 6)
                self.assertEqual(b[0], 0xB8, nm)
                self.assertEqual(struct.unpack_from("<I", b, 1)[0], size, nm)
                self.assertEqual(b[5], 0xC3, nm)

    # -- 7 -------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_attribute_and_fightattr_carry_no_wire_fields_at_all(self):
        self.assertEqual(self.img.dw(0xF0E850 + 0x34), NOOP_SER)   # Attribute
        self.assertEqual(self.img.dw(0xF0E8E0 + 0x34), NOOP_SER)   # FightAttr
        self.assertEqual(self.img.rd(NOOP_SER, 3), b"\xc2\x08\x00")

    # -- 8 -------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_type_nodes_name_the_classes_and_encode_the_hierarchy(self):
        def reg_site(node):
            pat = b"\xb9" + struct.pack("<I", node) + b"\xe8"
            k = self.img.text_raw
            while True:
                k = self.img.data.find(pat, k, self.img.text_raw + self.img.text_size)
                if k < 0:
                    return None
                rel = struct.unpack_from("<i", self.img.data, k + 6)[0]
                src = self.img.text_start + (k + 5 - self.img.text_raw)
                if src + 5 + rel == TYPE_REG:
                    return src
                k += 1

        for nm, _n, _t, _sl, _g, _v, _s, node, _ss, _ser in COHORT:
            site = reg_site(node)
            self.assertIsNotNone(site, nm)
            o = self.img.off(site)
            d = self.img.data
            if d[o - 10] == 0x68:
                parent = struct.unpack_from("<I", d, o - 9)[0]
            elif d[o - 6] == 0x50 and d[o - 11] == 0xE8:
                rel = struct.unpack_from("<i", d, o - 10)[0]
                b = self.img.rd(self.img.va(o - 11) + 5 + rel, 6)
                parent = struct.unpack_from("<I", b, 1)[0] if (
                    b[0] == 0xB8 and b[5] == 0xC3) else None
            else:
                parent = None
            want = EXPECT_PARENT[nm]
            if want == "*vital-base*":
                self.assertEqual(parent, VITAL_BASE_NODE, nm)
            elif want is not None:
                self.assertEqual(NODE_OF.get(parent), want, nm)
            rec = None
            for back in range(12, 40):
                if d[o - back] == 0xB9 and d[o - back + 5:o - back + 7] == b"\xff\x15":
                    rec = struct.unpack_from("<I", d, o - back + 1)[0]
                    break
            self.assertIsNotNone(rec, nm)
            self.assertEqual(self.img.cstr(rec + 8, 160), ".?AV%s@@" % nm)

    # -- 9 -------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_serializer_chain_follows_the_class_chain(self):
        self.assertEqual(self.img.dmap(0x466243, 8).get(0x466243), ("call", "0x4656f0"))
        self.assertEqual(self.img.dmap(0x4656FF, 8).get(0x4656FF), ("call", "0x467790"))
        self.assertEqual(self.img.dmap(0x46456F, 8).get(0x46456F), ("call", "0x467790"))
        self.assertEqual(self.img.dmap(0x7520C3, 8).get(0x7520C3), ("call", "0x467790"))

    # -- 10 ------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_every_serializer_decodes_to_its_pinned_field_list(self):
        for nm, (lo, hi) in SER_BOUNDS.items():
            self.assertEqual(self.img.decode_serializer(lo, hi), SCHEMA[nm], nm)
        for nm, sc in SCHEMA.items():
            for e in sc:
                if e[0] == "s":
                    self.assertEqual(TAG_WIDTH.get(e[3]), e[4], (nm, e))

    # -- 11 ------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_dirty_mask_headers_are_where_the_decode_says(self):
        self.assertEqual(SCHEMA["DBAttribute"][0], ("s", "esi", 0x20, 0x0B, 1))
        self.assertEqual(SCHEMA["BasicAttr"][0], ("s", "esi", 0x70, 0x12, 2))
        self.assertEqual(SCHEMA["AvatarAttr"][0], ("s", "esi", 0x28, 0x26, 4))
        self.assertEqual(SCHEMA["ActorAttr"][0], ("s", "esp", 0x14, 0x32, 8))
        self.assertEqual(SCHEMA["ActorAttr"][1], ("s", "esi", 0x1BC, 0x05, 1))
        self.assertTrue(self.img.bytes_at(*ANCHORS["actorattr_mask64"]))

    # -- 12 ------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_every_named_progression_field_is_present_and_gated(self):
        present = {(nm, e[2]) for nm, sc in SCHEMA.items() for e in sc}
        for owner, off, _bit, tag, meaning in NAMED_FIELDS:
            self.assertIn((owner, off), present, meaning)
            hit = [e for e in SCHEMA[owner] if e[2] == off]
            self.assertEqual(hit[0][3], tag, meaning)
        for key, (va, hexb) in GATE_PIN.items():
            self.assertTrue(self.img.bytes_at(va, hexb), key)
        self.assertTrue(self.img.bytes_at(*GATE_EBX_100))

    # -- 13 ------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_level_is_basicattr_u16_at_0x5E(self):
        self.assertEqual(self.img.cstr(0xF0E65C), "GetLv")
        self.assertTrue(self.img.bytes_at(*ANCHORS["GetLv_registration"]))
        self.assertTrue(self.img.bytes_at(*ANCHORS["GetLv_reads_0x5E"]))
        self.assertIn(("s", "esi", 0x5E, 0x12, 2), SCHEMA["BasicAttr"])
        # three further independent readers of the same word
        for va, hexb in ((0x43290C, "0fb74a5e"), (0x5192A5, "0fb7495e"),
                         (0x57F81A, "0fb7525e")):
            self.assertTrue(self.img.bytes_at(va, hexb), hex(va))

    # -- 14 ------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_hp_and_mp_pairs_feed_the_two_named_hud_bars(self):
        hud = self.img.parse_widget_binder(*HUD_BINDER)
        for name, slot in HUD_EXPECT.items():
            self.assertEqual(hud.get(name), slot, name)
        self.assertTrue(self.img.bytes_at(*ANCHORS["hud_binder_shape"]))
        self.assertEqual(self.img.dmap(0x53ED32, 8).get(0x53ED32),
                         ("call", hex(WIDGET_LOOKUP)))
        self.assertTrue(self.img.bytes_at(*ANCHORS["hud_attr_load"]))
        self.assertTrue(self.img.bytes_at(*ANCHORS["hud_hp_pair"]))
        self.assertTrue(self.img.bytes_at(*ANCHORS["hud_mp_pair"]))
        self.assertEqual(self.img.dmap(0x53F1FC, 0x30).get(0x53F20C),
                         ("divsd", "xmm0, xmm1"))
        self.assertEqual([e for e in SCHEMA["BasicAttr"] if e[2] in (0x44, 0x48, 0x4C, 0x50)],
                         [("s", "esi", 0x44, 0x14, 4), ("s", "esi", 0x48, 0x14, 4),
                          ("s", "esi", 0x4C, 0x14, 4), ("s", "esi", 0x50, 0x14, 4)])
        self.assertEqual(self.img.wstr(0xF14F24), "n_HPMAX")
        self.assertEqual(self.img.wstr(0xF14EEC), "n_STAMINAMAX")

    # -- 15 ------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_experience_is_the_actorattr_qword_at_0xA0(self):
        self.assertEqual(self.img.wstr(0xF152AC), "STANDARD_STATUS")
        self.assertEqual(self.img.wstr(0xF14C00), "n_EXP_CURRENTLV")
        for key in ("exp_open_table", "exp_level_lookup", "exp_reads_0xA0",
                    "exp_percentage"):
            self.assertTrue(self.img.bytes_at(*ANCHORS[key]), key)
        self.assertEqual(SCHEMA["ActorAttr"][12], ("s", "esi", 0xA0, 0x32, 8))
        self.assertEqual(SCHEMA["ActorAttr"][13], ("s", "esi", 0xA8, 0x32, 8))
        # the neighbouring qword is the already-proven cash field
        self.assertTrue(self.img.bytes_at(*ANCHORS["GetCash_reads_0xA8"]))

    # -- 16 ------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_class_and_skill_points(self):
        self.assertEqual(self.img.cstr(0xF0E530), "GetClass")
        self.assertTrue(self.img.bytes_at(*ANCHORS["GetClass_reads_0x8C"]))
        self.assertEqual(SCHEMA["ActorAttr"][2], ("s", "esi", 0x8C, 0x19, 4))
        skl = self.img.parse_widget_binder(*SKILL_BINDER)
        self.assertEqual(skl.get("NUMBERLABEL_SPNOW"), 0x6C)
        self.assertTrue(self.img.bytes_at(*ANCHORS["skillpoint_read"]))
        self.assertTrue(self.img.bytes_at(*ANCHORS["skillpoint_to_label"]))
        self.assertEqual(SCHEMA["ActorAttr"][5], ("s", "esi", 0x7C, 0x19, 4))

    # -- 17 ------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_five_primary_attributes_are_named_by_the_char_info_panel(self):
        for lbl in ("STR", "CON", "DEX", "INT", "PER"):
            self.assertTrue(self.img.bytes_at(*ANCHORS["getter_" + lbl]), lbl)
        ci = self.img.parse_widget_binder(*CHARINFO_BINDER)
        for name, slot in CHARINFO_EXPECT.items():
            self.assertEqual(ci.get(name), slot, name)
        for site, getter, slot, lbl in CHARINFO_UPDATE:
            self.assertEqual(self.img.dmap(site, 8).get(site), ("call", hex(getter)), lbl)
            nxt = self.img.dmap(site + 5, 12)
            self.assertTrue(any(v[0] == "mov" and v[1].endswith("dword ptr [esi + 0x%x]" % slot)
                                for v in nxt.values()), lbl)
        self.assertEqual([e[2] for e in SCHEMA["ActorAttr"][7:12]],
                         [0x82, 0x84, 0x86, 0x88, 0x8A])
        self.assertEqual([e[2] for e in SCHEMA["ActorAttr"][20:25]],
                         [0x182, 0x184, 0x186, 0x188, 0x18A])

    # -- 18 ------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_actorattr_0x80_is_the_unspent_allocation_point_pool(self):
        self.assertTrue(self.img.bytes_at(*ANCHORS["point_pool_spinner"]))
        self.assertTrue(self.img.bytes_at(*ANCHORS["point_pool_gate"]))
        self.assertTrue(self.img.bytes_at(0x53B1FB, "0fb79f80000000"))
        self.assertTrue(self.img.bytes_at(0x53B215, "6683bf8000000000"))
        self.assertTrue(self.img.bytes_at(0x53B237, "6683bf8000000000"))
        self.assertEqual(SCHEMA["ActorAttr"][6], ("s", "esi", 0x80, 0x12, 2))

    # -- 19 ------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_static_data_schema_declares_exactly_five_primary_attributes(self):
        for va, want in TABLE_LITERALS.items():
            self.assertEqual(self.img.wstr(va), want, hex(va))
        self.assertEqual(
            [self.img.wstr(v) for v in (0xF14B70, 0xF14B50, 0xF14B3C, 0xF14B24, 0xF14B08)],
            ["n_STRENGH", "n_CONSTITUTION", "n_AGILITY", "n_INTELLECT", "n_PERCEPTION"])

    # -- 20 ------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_abilitydepolyall_wire_order_is_str_con_dex_int_per(self):
        self.assertEqual(SCHEMA["AbilityDepolyAll"],
                         [("s", "esi", 0x14 + 2 * k, 0x0F, 2) for k in range(5)])
        for lbl, (va, hexb) in CHARINFO_CLICK_DELTA.items():
            self.assertTrue(self.img.bytes_at(va, hexb), lbl)
        self.assertTrue(self.img.bytes_at(*ANCHORS["depolyall_producer"]))
        self.assertTrue(self.img.bytes_at(*ANCHORS["depolyall_ctor"]))
        self.assertEqual(self.img.dmap(0x57F772, 8).get(0x57F772), ("call", hex(UI_SEND)))

    # -- 21 ------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_abilitydepoly_has_exactly_one_fixed_producer(self):
        self.assertTrue(self.img.bytes_at(*ANCHORS["depoly_ctor"]))
        self.assertTrue(self.img.bytes_at(*ANCHORS["depoly_producer"]))
        self.assertEqual(sorted(self.img.callers_of(DEPOLY_POOL)), DEPOLY_POOL_CALLERS)
        self.assertEqual(sorted(self.img.callers_of(DEPOLYALL_POOL)), DEPOLYALL_POOL_CALLERS)
        self.assertEqual(self.img.wstr(0xF29168), "COIN_CONSUME")
        self.assertTrue(self.img.bytes_at(0x57F7E7, "686891f200"))
        self.assertEqual(self.img.dmap(0x57F84C, 8).get(0x57F84C), ("call", hex(UI_SEND)))

    # -- 22 ------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_skill_verbs_and_update_transport(self):
        self.assertEqual(SCHEMA["CLearnSkillVital"],
                         [("s", "esi", 0x14, 0x14, 4), ("s", "esi", 0x18, 0x0B, 1)])
        self.assertEqual(SCHEMA["CRevertSkilltVital"],
                         [("s", "esi", 0x14, 0x14, 4), ("s", "esi", 0x18, 0x32, 8)])
        self.assertEqual(SCHEMA["CLearnSkillResultVital"], [("s", "esi", 0x2C, 0x0B, 1)])
        self.assertEqual(self.img.dmap(0x756114, 8).get(0x756114), ("call", "0x755d30"))
        # UpdateAttrVital owns no fields; it tail-jumps to the Attr-collection codec
        self.assertTrue(self.img.bytes_at(0x5E42C0, "83c114807c240800"))
        self.assertEqual(self.img.dmap(0x5E42D2, 8).get(0x5E42D2), ("jmp", "0x463de0"))
        self.assertEqual(self.img.dw(0xF303E0 + 0x1C), 0x5F2400)

    # -- 23 ------------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_addexp_addabilitypoint_addskillpoint_grant_nothing(self):
        for nm, (nva, site, _handler) in SCRIPT_BINDINGS.items():
            self.assertEqual(self.img.cstr(nva), nm)
            b = self.img.rd(site, 10)
            self.assertEqual(b[0], 0x68, nm)
            self.assertEqual(struct.unpack_from("<I", b, 1)[0], 0x460AE0, nm)
            self.assertEqual(b[5], 0x68, nm)
            self.assertEqual(struct.unpack_from("<I", b, 6)[0], nva, nm)
        for nm, (tva, tok) in LOCAL_EVENT_TOKENS.items():
            self.assertEqual(self.img.cstr(tva), tok, nm)
        for key in ("AddExp_token", "AddAbilityPoint_tok", "AddSkillPoint_token"):
            self.assertTrue(self.img.bytes_at(*ANCHORS[key]), key)
        for _handler, site in EVENT_CALL_SITES.items():
            self.assertEqual(self.img.dmap(site, 8).get(site),
                             ("call", hex(EVENT_BROADCAST)), hex(site))
        # the fan-out itself never touches a codec and never builds a vital
        self.assertEqual(
            self.img.call_targets(0x5F9C70, 0x5F9D08, set(WRITE_CODECS) | READ_CODECS), [])
        for ctor in (DEPOLY_CTOR, DEPOLYALL_CTOR):
            self.assertFalse([c for c in self.img.callers_of(ctor)
                              if 0x460EC0 <= c < 0x4614C0])

    # -- 24 ------------------------------------------------------------------
    # The deliberate exceptions to the "no progression verb name under src/"
    # negative, as exact (file, verb, occurrence count) triples -- one owning
    # module per lane (HYP-PF-033 outbound encoder, HYP-PF-034 inbound strict
    # decoder), docstring mentions only.  This is the TEST's own copy; test 24
    # below also re-reads the identical constant out of
    # tools/pf_stats_progression_static.py (the tool twin of this guard, which
    # the cloud cannot run because it needs the client image) and asserts the
    # two copies are equal, so the twins cannot drift apart silently.
    LEARN_SKILL_RESULT_SRC_EXCEPTIONS = (
        ("learn_skill_result_hypothesis.py", "CLearnSkillVital", 1),
        ("learn_skill_result_hypothesis.py", "CLearnSkillResultVital", 1),
        ("learn_skill_request_hypothesis.py", "CLearnSkillVital", 1),
    )

    def test_server_side_progression_gap_names_its_one_exception(self):
        """The learn-skill lanes deliberately changed what this guard asserts.

        Until 2026-08-23 this test asserted the strongest possible negative:
        no progression verb NAME appeared anywhere under src/, so the "5
        verbs, 0 encoders, 0 dispatch" statement of STATS-PROG-001 was true
        by construction.  LEARN-SKILL-RESULT-001 (HYP-PF-033) built the
        OUTBOUND encoder for CLearnSkillResultVital 0x673C, and
        LEARN-SKILL-REQUEST-001 (HYP-PF-034, 2026-08-24) built the INBOUND
        strict decoder for CLearnSkillVital 0x36AA (decode-count-and-record
        only: no reply, no learn rule, no write) -- so this assertion had to
        move rather than be worked around.  (It was NOT worked around: no
        derived name, no obfuscated spelling -- each owning module names its
        class in its docstring on purpose.)  The exceptions are pinned three
        ways so they cannot quietly widen: exact occurrence COUNTS per
        (file, verb), so a new mention of either verb in an owning module
        trips this guard again; every allowed mention must sit inside the
        owning module's DOCSTRING, so no code path may name a verb; and the
        identical triple list is re-read out of the tool twin
        tools/pf_stats_progression_static.py, which enforces the same
        triples on the bridge, so the two guards cannot drift apart.  The
        frozen v141 module still names no verb and no cohort id, the other
        three verbs still have zero encoders, zero decoders and zero
        dispatch anywhere under src/, and the HYP-PF-020 progression lane
        itself still names none of them.
        """
        src = SERVER.read_text(encoding="utf-8", errors="replace")
        up = src.upper()
        for nm, *_ in COHORT:
            self.assertNotIn("0x%04X" % EXPECT_IDS[nm], up, nm)
        for verb in PROGRESSION_VERBS:
            self.assertNotIn(verb.upper(), up, verb)
        # the single ActorAttr encoder sets exactly one of the 43 fields: cash
        self.assertIn('struct.pack("<II", 0x800, 0)', src)
        self.assertIn("basic_mask = 0x0004 | 0x0008 | 0x0100 | 0x0200", src)
        self.assertIn("basic_mask = 0x000C | 0x0100 | 0x0200", src)
        hits = []
        if SRC_DIR.is_dir():
            for p in SRC_DIR.rglob("*.py"):
                if "__pycache__" in p.parts:
                    continue
                t = p.read_text(encoding="utf-8", errors="replace")
                for v in PROGRESSION_VERBS:
                    # Trailing identifier-boundary lookahead, exactly as the
                    # tool twin counts: "AbilityDepoly" must not count
                    # "AbilityDepolyAll", and a NEW mention of an allowed
                    # verb must move the count and fail this assertion.
                    n = len(re.findall(re.escape(v) + r"(?![A-Za-z0-9_])", t))
                    if n:
                        hits.append((p.name, v, n))
        self.assertEqual(
            sorted(hits), sorted(self.LEARN_SKILL_RESULT_SRC_EXCEPTIONS),
        )
        # Context restriction: every allowed mention sits inside its owning
        # module's DOCSTRING (title lines and nonclaims).  A verb name
        # appearing in executable code -- constants, dispatch, a handler
        # body -- is not covered by these exceptions.
        docstrings = {}
        for file, verb, count in self.LEARN_SKILL_RESULT_SRC_EXCEPTIONS:
            if file not in docstrings:
                owner = SRC_DIR / "pirateforce_foundation" / file
                docstrings[file] = ast.get_docstring(
                    ast.parse(owner.read_text(encoding="utf-8")), clean=False,
                )
            self.assertEqual(
                len(re.findall(
                    re.escape(verb) + r"(?![A-Za-z0-9_])", docstrings[file],
                )),
                count,
                f"{verb} mention moved outside the {file} docstring",
            )
        # Twin binding: the tool's exception constant is the SAME triples.
        # The tool's own (pre-existing) docstring ASCII art carries a "\-"
        # escape that ast.parse flags as a DeprecationWarning; that is the
        # tool's cosmetic debt, not this guard's finding, so it is silenced
        # for exactly this parse.
        tool = ROOT / "tools" / "pf_stats_progression_static.py"
        tool_exceptions = None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            warnings.simplefilter("ignore", SyntaxWarning)
            tool_tree = ast.parse(tool.read_text(encoding="utf-8"))
        for node in ast.walk(tool_tree):
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name)
                and target.id == "LEARN_SKILL_RESULT_SRC_EXCEPTIONS"
                for target in node.targets
            ):
                tool_exceptions = ast.literal_eval(node.value)
        self.assertIsNotNone(
            tool_exceptions,
            "tools/pf_stats_progression_static.py lost its "
            "LEARN_SKILL_RESULT_SRC_EXCEPTIONS constant",
        )
        self.assertEqual(
            sorted(tool_exceptions),
            sorted(self.LEARN_SKILL_RESULT_SRC_EXCEPTIONS),
        )

    # -- 25 ------------------------------------------------------------------
    def test_gap_numbers_are_exactly_what_the_report_states(self):
        self.assertEqual(len(COHORT), 14)
        self.assertEqual(len(NAMED_FIELDS), 19)
        emitted = [f for f in NAMED_FIELDS if f[4] in ("hp current", "hp max")]
        self.assertEqual(len(emitted), 2)
        self.assertEqual(len(SCHEMA["ActorAttr"]), 45)   # 2 header + 43 gated
        self.assertEqual(len(SCHEMA["BasicAttr"]), 13)   # 1 header + 12 gated
        self.assertEqual(len(PROGRESSION_VERBS) - 1, 5)  # CSkillAttr is not a verb


if __name__ == "__main__":
    unittest.main()
