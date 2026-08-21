"""PF CHAT-CHANNEL-001 — static byte-exact enumeration of the client `Channel_*Vital`
family: 17 concrete channels + 5 abstract bases, their wire ids, their per-channel
wire schemas, the routing taxonomy the hierarchy encodes, and the Join/Leave
membership lifecycle. Opens `chat/chat_channels_and_routing` not_started -> in_progress.

The lane's coverage note said "Channel identifiers and recipient resolution are
uncaptured". This test pins, from the read-only client binary:

  * IDENTIFIERS. One contiguous 18-entry registration block 0xBF72B0..0xBF74F0
    (stride 0x20) of the PF-NAMEID-HASH-001 shape
      push <name literal>; call 0x89C080; mov ecx,eax; call 0x89BD00;
      mov word [id-slot], ax; ret
    Re-applying the NAMEID-HASH-001 hash (client 0x89B220,
    u16 id = SUM_i (int16)((signed char)name[i] * (i+1)) mod 2^16) to the in-image
    literals yields all 17 ids. ANCHOR: Channel_LocalTalkMessageVital -> 0xAC52,
    the id GT-006 actually captured on the wire.
  * The ids are never .text code immediates (runtime-assigned wall, same cohort as
    TargetPosVital / ItemOperate / TeleportCheck); each id-slot has exactly one
    writer and one reader (`mov ax,[slot]; ret` == vtable +0x10).
  * TWO independent name paths converge per class: the registration literal, and
    vtable+0x00 -> type node -> `.?AVChannel_XxxVital@@` descriptor.
  * HIERARCHY from the type-node registration block 0xBF74F0..0xBF7AB0:
    Channel_BasicVtial -> {Command, Message, ForbidTalkNotification};
    Message -> {Global, Local}; 7 Command leaves, 7 Global leaves, 2 Local leaves.
  * WIRE SCHEMAS: Serialize is vtable +0x18, one bidirectional
    `thiscall (bool save, Stream*) ret 8` routine selecting wstring codec 0x89A810/
    0x89A880 (tag 0x48 + u32 byte-length + UTF-16LE) or scalar codec 0x89A600/
    0x89A640 (tag, ptr, width). Five channels SHARE the base serializer 0x65AD40
    and are therefore wire-identical, told apart only by their class id.
  * RECIPIENT RESOLUTION: Channel_WhisperVital alone carries a third wstring
    (@+0x50) plus a u8 result @+0x6C, both constructed by its own ctor 0x658240;
    the dispatcher maps result 1/2 to system messages instead of rendering.
  * SERVER GAP: v141 has no `Channel_` token and none of the 17 ids; only
    chat_input_hypothesis.py touches 0xAC52 and still calls it "UNKNOWN", echoing
    an opaque blob it never decodes.

NOT CLAIMED: any behaviour of the ORIGINAL server's routing. No two concurrent
sessions have ever existed in this project, so fan-out, membership authority and
whisper delivery stay uncaptured. See
reports/PF_CHAT_CHANNEL001_CHANNEL_FAMILY_AND_ROUTING_STATIC_20260818.md. The lane
stays in_progress and never flips to runtime_pass here.
"""
from __future__ import annotations

import hashlib
import struct
import sys
import unittest
from pathlib import Path

import capstone
import pefile

ROOT = Path(__file__).resolve().parents[1]
# The proprietary client image cannot be in a fresh clone; every test that reads
# it carries its own @CLIENT_IMAGE guard below - see tests/pf_preconditions.py.
sys.path.insert(0, str(ROOT / "tests"))
from pf_preconditions import CLIENT_IMAGE

BINARY = ROOT.parent / "GameClient" / "GameClient.local.bin"
BINARY_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
SERVER = ROOT / "current" / "pf_login_game_server_v141.py"
CHAT_MOD = ROOT / "src" / "pirateforce_foundation" / "chat_input_hypothesis.py"

ONCE_INIT = 0x89C080
ID_ASSIGN = 0x89BD00
HASH_FN = 0x89B220
TYPE_ISA = 0x88F2B0
TYPE_REG = 0x88F2E0
WSTR_W, WSTR_R = 0x89A810, 0x89A880
SCAL_W, SCAL_R = 0x89A600, 0x89A640
MODULE_NAME_VA = 0xF22CB4
MODULE_NODE, MODULE_NODE_GET = 0x1084304, 0x657850
MODULE_REGISTRY = 0x1032EC4
DELIVER = 0x659870
PLAIN_HOOK = 0x65C850
LOCALTALK_WIRE_ID = 0xAC52          # captured by GT-006
COHORT_CONST = 0x401B20             # shared framework const of the Vital cohort

# name, name VA, reg thunk, id-slot, get-id stub, vtable, serializer, sizeof, type node
FAMILY = [
    ("Channel_ForbidTalkNotificationVtial",    0xF37960, 0xBF72B0, 0x1084454, 0x65A9E0, 0xF37804, 0x65AE00, 0x1C, 0x1084424),
    ("Channel_LocalTalkMessageVital",          0xF37984, 0xBF72D0, 0x1084458, 0x6580B0, 0xF3775C, 0x65AD40, 0x50, 0x1084400),
    ("Channel_LocalPerformanceVital",          0xF379A4, 0xBF72F0, 0x108445C, 0x5BEAE0, 0xF2D0D4, 0x65AE30, 0x30, 0x10843F4),
    ("Channel_PartyMessageVital",              0xF379C4, 0xBF7310, 0x1084460, 0x657DA0, 0xF37628, 0x65AD40, 0x50, 0x10843E8),
    ("Channel_WhisperVital",                   0xF379E0, 0xBF7330, 0x1084464, 0x6582B0, 0xF37788, 0x65AEA0, 0x70, 0x10843DC),
    ("Channel_GuildMessageVital",              0xF379F8, 0xBF7350, 0x1084468, 0x657DD0, 0xF37654, 0x65AD40, 0x50, 0x10843D0),
    ("Channel_ActorBoardcastMessageVital",     0xF37A14, 0xBF7370, 0x108446C, 0x658030, 0xF37730, 0x65AD40, 0x50, 0x10843C4),
    ("Channel_GMGlobalMessageVital",           0xF37A38, 0xBF7390, 0x1084470, 0x65AC10, 0xF3790C, 0x65AD40, 0x50, 0x10843B8),
    ("Channel_JoinCustomChannelVital",         0xF37A58, 0xBF73B0, 0x1084474, 0x657E70, 0xF37680, 0x65AF80, 0x40, 0x10843AC),
    ("Channel_OnActorJoinCustomChannelVital",  0xF37A78, 0xBF73D0, 0x1084478, 0x65AA80, 0xF37830, 0x65B140, 0x58, 0x10843A0),
    ("Channel_LeaveCustomChannelVital",        0xF37AA0, 0xBF73F0, 0x108447C, 0x657F70, 0xF376AC, 0x65B060, 0x40, 0x1084394),
    ("Channel_OnActorLeaveCustomChannelVital", 0xF37AC0, 0xBF7410, 0x1084480, 0x65AB90, 0xF3785C, 0x65B140, 0x58, 0x1084388),
    ("Channel_CustomChannelMessageVital",      0xF37AE8, 0xBF7430, 0x1084484, 0x657FF0, 0xF376D8, 0x65B1E0, 0x60, 0x108437C),
    ("Channel_JoinOriginalSinChannelVital",    0xF37B0C, 0xBF7450, 0x1084488, 0x65ABB0, 0xF37888, 0x65B260, 0x28, 0x1084370),
    ("Channel_OriginalSinChannelMessageVital", 0xF37B30, 0xBF7470, 0x108448C, 0x65ABD0, 0xF378B4, 0x65B310, 0x54, 0x1084364),
    ("Channel_JoinClassChannelVital",          0xF37B68, 0xBF74B0, 0x1084494, 0x65ABF0, 0xF378E0, 0x65B450, 0x28, 0x108434C),
    ("Channel_ClassChannelMessageVital",       0xF37B88, 0xBF74D0, 0x1084498, 0x658010, 0xF37704, 0x65B500, 0x54, 0x1084340),
]

EXPECT_IDS = {
    "Channel_ForbidTalkNotificationVtial": 0xFDF2,
    "Channel_LocalTalkMessageVital": 0xAC52,
    "Channel_LocalPerformanceVital": 0xAE8C,
    "Channel_PartyMessageVital": 0x82E6,
    "Channel_WhisperVital": 0x556C,
    "Channel_GuildMessageVital": 0x8189,
    "Channel_ActorBoardcastMessageVital": 0xEDFA,
    "Channel_GMGlobalMessageVital": 0x9F2C,
    "Channel_JoinCustomChannelVital": 0xBA58,
    "Channel_OnActorJoinCustomChannelVital": 0x18DA,
    "Channel_LeaveCustomChannelVital": 0xC663,
    "Channel_OnActorLeaveCustomChannelVital": 0x2770,
    "Channel_CustomChannelMessageVital": 0xE064,
    "Channel_JoinOriginalSinChannelVital": 0xFA07,
    "Channel_OriginalSinChannelMessageVital": 0x265C,
    "Channel_JoinClassChannelVital": 0xAC9D,
    "Channel_ClassChannelMessageVital": 0xD1F8,
}

NODE_NAME = {
    0x1084448: "Channel_BasicVtial", 0x108443C: "Channel_CommandVtial",
    0x1084430: "Channel_MessageVtial", 0x1084424: "Channel_ForbidTalkNotificationVtial",
    0x1084418: "Channel_GlobalVital", 0x108440C: "Channel_LocalVital",
    0x1084400: "Channel_LocalTalkMessageVital", 0x10843F4: "Channel_LocalPerformanceVital",
    0x10843E8: "Channel_PartyMessageVital", 0x10843DC: "Channel_WhisperVital",
    0x10843D0: "Channel_GuildMessageVital", 0x10843C4: "Channel_ActorBoardcastMessageVital",
    0x10843B8: "Channel_GMGlobalMessageVital", 0x10843AC: "Channel_JoinCustomChannelVital",
    0x10843A0: "Channel_OnActorJoinCustomChannelVital",
    0x1084394: "Channel_LeaveCustomChannelVital",
    0x1084388: "Channel_OnActorLeaveCustomChannelVital",
    0x108437C: "Channel_CustomChannelMessageVital",
    0x1084370: "Channel_JoinOriginalSinChannelVital",
    0x1084364: "Channel_OriginalSinChannelMessageVital",
    0x1084358: "CBoardcastVital", 0x108434C: "Channel_JoinClassChannelVital",
    0x1084340: "Channel_ClassChannelMessageVital",
}
EXPECT_PARENT = {
    "Channel_BasicVtial": None, "CBoardcastVital": None,
    "Channel_CommandVtial": "Channel_BasicVtial",
    "Channel_MessageVtial": "Channel_BasicVtial",
    "Channel_ForbidTalkNotificationVtial": "Channel_BasicVtial",
    "Channel_GlobalVital": "Channel_MessageVtial",
    "Channel_LocalVital": "Channel_MessageVtial",
    "Channel_LocalTalkMessageVital": "Channel_LocalVital",
    "Channel_PartyMessageVital": "Channel_LocalVital",
    "Channel_WhisperVital": "Channel_GlobalVital",
    "Channel_GuildMessageVital": "Channel_GlobalVital",
    "Channel_ActorBoardcastMessageVital": "Channel_GlobalVital",
    "Channel_GMGlobalMessageVital": "Channel_GlobalVital",
    "Channel_CustomChannelMessageVital": "Channel_GlobalVital",
    "Channel_OriginalSinChannelMessageVital": "Channel_GlobalVital",
    "Channel_ClassChannelMessageVital": "Channel_GlobalVital",
    "Channel_LocalPerformanceVital": "Channel_CommandVtial",
    "Channel_JoinCustomChannelVital": "Channel_CommandVtial",
    "Channel_OnActorJoinCustomChannelVital": "Channel_CommandVtial",
    "Channel_LeaveCustomChannelVital": "Channel_CommandVtial",
    "Channel_OnActorLeaveCustomChannelVital": "Channel_CommandVtial",
    "Channel_JoinOriginalSinChannelVital": "Channel_CommandVtial",
    "Channel_JoinClassChannelVital": "Channel_CommandVtial",
}

# ('w', offset, 0x48, None) = wstring ; ('s', offset, tag, width) = scalar
SCHEMA = {
    0x65AD40: [('w', 0x34, 0x48, None), ('w', 0x18, 0x48, None)],
    0x65AEA0: [('w', 0x34, 0x48, None), ('w', 0x18, 0x48, None),
               ('w', 0x50, 0x48, None), ('s', 0x6C, 0x0B, 1)],
    0x65AE00: [('s', 0x18, 0x0B, 1)],
    0x65AE30: [('s', 0x18, 0x32, 8), ('s', 0x20, 0x32, 8), ('s', 0x28, 0x12, 2)],
    0x65AF80: [('s', 0x18, 0x32, 8), ('w', 0x20, 0x48, None),
               ('s', 0x3C, 0x0B, 1), ('s', 0x3D, 0x0B, 1)],
    0x65B060: [('s', 0x18, 0x32, 8), ('s', 0x20, 0x0B, 1),
               ('s', 0x21, 0x0B, 1), ('w', 0x24, 0x48, None)],
    0x65B140: [('s', 0x18, 0x32, 8), ('w', 0x20, 0x48, None), ('w', 0x3C, 0x48, None)],
    0x65B1E0: [('w', 0x34, 0x48, None), ('w', 0x18, 0x48, None),
               ('s', 0x50, 0x08, 1), ('s', 0x58, 0x32, 8)],
    0x65B260: [('s', 0x18, 0x32, 8), ('s', 0x20, 0x08, 1), ('s', 0x21, 0x0B, 1)],
    0x65B310: [('w', 0x34, 0x48, None), ('w', 0x18, 0x48, None), ('s', 0x50, 0x08, 1)],
    0x65B450: [('s', 0x18, 0x32, 8), ('s', 0x20, 0x19, 4), ('s', 0x24, 0x0B, 1)],
    0x65B500: [('w', 0x34, 0x48, None), ('w', 0x18, 0x48, None), ('s', 0x50, 0x19, 4)],
}

DELIVER_HOOK = {
    "Channel_JoinCustomChannelVital": (0x65C8B0, 0x3D),
    "Channel_LeaveCustomChannelVital": (0x65C950, 0x21),
    "Channel_JoinOriginalSinChannelVital": (0x65C950, 0x21),
    "Channel_JoinClassChannelVital": (0x65CB40, 0x24),
}

DISPATCH_ORDER = [
    (0x6598F0, 0x657980, "Channel_LocalTalkMessageVital"),
    (0x65997C, 0x6579B0, "Channel_WhisperVital"),
    (0x6599EE, 0x6579E0, "Channel_GuildMessageVital"),
    (0x659A2A, 0x657A10, "Channel_PartyMessageVital"),
    (0x659A69, 0x657A40, "Channel_ActorBoardcastMessageVital"),
    (0x659AA8, 0x657A70, "Channel_LocalPerformanceVital"),
    (0x659B08, 0x657AA0, "Channel_CustomChannelMessageVital"),
    (0x659BA5, 0x657AD0, "Channel_JoinCustomChannelVital"),
    (0x659D4A, 0x657B00, "Channel_OnActorJoinCustomChannelVital"),
    (0x659D9E, 0x657B30, "Channel_LeaveCustomChannelVital"),
    (0x659F39, 0x657B60, "Channel_OnActorLeaveCustomChannelVital"),
    (0x659F8D, 0x657B90, "Channel_ClassChannelMessageVital"),
    (0x65A028, 0x657BC0, "Channel_GMGlobalMessageVital"),
    (0x65A05A, 0x657BF0, "Channel_ForbidTalkNotificationVtial"),
]
UNROUTED = ["Channel_JoinOriginalSinChannelVital",
            "Channel_OriginalSinChannelMessageVital",
            "Channel_JoinClassChannelVital"]
STYLE_NAMES = [
    (0x659904, 0xF23160, "LocalTalk"),
    (0x6599B6, 0xF23148, "WhisperTalk"),
    (0x659A0F, 0xF23120, "GuildTalk"),
    (0x659A4B, 0xF23134, "PartyTalk"),
    (0x659A8A, 0xF2310C, "YellTalk"),
    (0x659AC9, 0xF23080, "LocalPerformance"),
    (0x659B2D, 0xF230F0, "CustomDefine"),
    (0x659FB2, 0xF230DC, "ClassTalk"),
]

# (start, end, sha256) instruction/data-aligned byte-span pins
SPANS = {
    "name_string_block":       (0xF37960, 0xF37BA9, "CD9E80FCE283FEB404D71547D5C015E6EB15891A08B2B9E1C9F31F918D6EC589"),
    "registration_block":      (0xBF72B0, 0xBF74F0, "807D39728B9A59B4D07C7A73DA033AA62931977C5FEB62B93E37ABE7BA95CFBF"),
    "typenode_reg_block":      (0xBF74F0, 0xBF7AB0, "9988D397D115E53DB9FFAF45874452E29D0AAB343227479BC51B7F1A0B736BB0"),
    "vtable_block":            (0xF37628, 0xF37938, "038DC8D88B415953829CDE2ED4650F96E2CD8569EEE4C5879A62CF8765B490A3"),
    "vtable_localperformance": (0xF2D0D4, 0xF2D100, "08A273CB9B08EF50ACB103F33C7D7F47E2559AA6213D836176C98A2835BB0F04"),
    "ser_message_base":        (0x65AD40, 0x65AD83, "207D532A2C430B964731DBA4032D2655A217C310CEE3AD1F1D9CF1B89280A758"),
    "ser_whisper":             (0x65AEA0, 0x65AF13, "306E7330383EFAEBADC732E7B8A416294517F7BFF6D5A2FB7817CE76B855686E"),
    "ser_joincustom":          (0x65AF80, 0x65AFFB, "A03A3BABB4D04255E9FC5C6BE402AA241E4C04F63B5C4B8A2E3C1161E5E8A73A"),
    "ser_leavecustom":         (0x65B060, 0x65B0DB, "6F215678384C735B14FC1A29762B4C9E1E1F396B318B4B096070F5C51367B046"),
    "ser_onactor_joinleave":   (0x65B140, 0x65B19D, "7E180A3FB5BFF46820A6E2DA053BB80EE487E3C30694878B4CBC5617FCD73151"),
    "ser_customchannelmsg":    (0x65B1E0, 0x65B257, "280B331D3E567CDFC5B5355B45387C67DEFC9F65BA2F925BB6BD8F26043DA96D"),
    "ser_joinoriginalsin":     (0x65B260, 0x65B2C5, "F02791701FA8CF57C02EADA50A1A2243843DEF8D8BA594750AF48CA8DFBAB2FB"),
    "ser_originalsinmsg":      (0x65B310, 0x65B36D, "5EA9C0851D26DD396EFE51C80C7B1D25454D4281E5C49AC3894A1F9ADB4E4F89"),
    "ser_joinclass":           (0x65B450, 0x65B4B5, "3FA44912B0EDAA7B52B2093FBE78CC1E22EC107C73EE9D94DF1DA34E21353186"),
    "ser_classchannelmsg":     (0x65B500, 0x65B55D, "B3968233CC1CDAB4C399699EC07EB682B66984D2063B3EAE0BAEB294110D83A6"),
    "ser_forbidtalk":          (0x65AE00, 0x65AE23, "4C6A0E447E2E16C0AB2EB1E08CC45FFD7B49711D1EFB7B0FD58A11D7ABC5AEF8"),
    "ser_localperformance":    (0x65AE30, 0x65AE95, "CD138FD6E5EE750C131E327C83117A11A81562C09AA17B0A0F2421790014A9C9"),
    "whisper_ctor":            (0x658240, 0x65829B, "EBD689CFAD5352B7F06985BE7E714FC03676648F56B90A78B67779534EF5F82D"),
    "clone_message_base":      (0x65ACB0, 0x65AD32, "668B4339C44D98BAD9E5D74CEA7F4E77DD0044B35D3D0AA1FB27CE9DB31A75A9"),
    "clone_whisper":           (0x65AF20, 0x65AF71, "D2DA3F502301BA02686A2A593CF89BD17542A93F8477EDF888F9E7212D4585DF"),
    "dispatcher":              (0x659870, 0x65A0A0, "AE034BF598B708D02775961156E6675C329A0546AE5F24B55808FBA17B7C9DCE"),
    "wstring_write_codec":     (0x89A810, 0x89A873, "16765A9B04F01961D5119ED7FB14438636F5BD81204143C67D486C8B4A491DDC"),
    "scalar_write_codec":      (0x89A600, 0x89A640, "182016F6C3F32466DF5BC6C9CB88146DCEA0223DC19E66B26A65F4D5F2911472"),
}

# GT-006 captured LocalTalk request payload (34 bytes), byte-for-byte the value in
# src/pirateforce_foundation/chat_input_hypothesis.py CHAT_INPUT_PROBE_PAYLOADS.
GT006_PAYLOAD = bytes.fromhex(
    "48000000004818000000"
    "500046004300480041005400500052004F00420045003100")


def _name_id(name: str) -> int:
    """PF-NAMEID-HASH-001 / client 0x89B220 — re-used verbatim, not re-derived."""
    acc = 0
    for i, ch in enumerate(name.encode("latin1")):
        sc = ch if ch < 128 else ch - 256
        acc = (acc + ((sc * (i + 1)) & 0xFFFF)) & 0xFFFF
    return acc


def _read_va(pe: pefile.PE, start: int, end: int) -> bytes:
    return pe.get_data(start - pe.OPTIONAL_HEADER.ImageBase, end - start)


def _dword(pe: pefile.PE, va: int) -> int:
    return struct.unpack("<I", _read_va(pe, va, va + 4))[0]


def _cstr(pe: pefile.PE, va: int, maxn: int = 128) -> str | None:
    b = _read_va(pe, va, va + maxn)
    z = b.find(b"\x00")
    return b[:z].decode("latin1") if z >= 0 else None


def _wstr(pe: pefile.PE, va: int, maxn: int = 120) -> str:
    b = _read_va(pe, va, va + maxn)
    z = b.find(b"\x00\x00")
    if z < 0:
        z = len(b)
    if z % 2:
        z += 1
    return b[:z].decode("utf-16le", "replace")


def _instructions(pe: pefile.PE, start: int, end: int):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    return {i.address: (i.mnemonic, i.op_str) for i in md.disasm(_read_va(pe, start, end), start)}


def _text_section(pe: pefile.PE):
    base = pe.OPTIONAL_HEADER.ImageBase
    for s in pe.sections:
        if s.Name.rstrip(b"\x00") == b".text":
            return base + s.VirtualAddress, pe.get_data(s.VirtualAddress, s.Misc_VirtualSize)
    raise AssertionError(".text not found")


def _pattern_sites(pe: pefile.PE, pattern: bytes) -> list[int]:
    start, blob = _text_section(pe)
    res, i = [], blob.find(pattern)
    while i >= 0:
        res.append(start + i)
        i = blob.find(pattern, i + 1)
    return res


def _dword_immediate_hits(pe: pefile.PE, val: int) -> list[int]:
    """dword `val` in .text excluding E8/E9 rel32 tails AND 0F 8x (jcc rel32) tails."""
    start, blob = _text_section(pe)
    packed = struct.pack("<I", val)
    res, i = [], blob.find(packed)
    while i >= 0:
        if not (blob[i - 1] in (0xE8, 0xE9)
                or (blob[i - 1] == 0x0F and 0x80 <= blob[i] <= 0x8F)):
            res.append(start + i)
        i = blob.find(packed, i + 1)
    return res


def _imm16_hits(pe: pefile.PE, val: int) -> list[int]:
    out = []
    for pfx in (b"\x66\xb8", b"\x66\x3d", b"\x66\x81\xf8", b"\x66\xa9"):
        out += _pattern_sites(pe, pfx + struct.pack("<H", val))
    return out


def _decode_serializer(pe: pefile.PE, va: int, limit: int = 0x120):
    """Walk Serialize linearly and return the ordered wire fields it emits.

    Every field appears twice (the `test bl,bl` save/load branch); the load repeat
    is folded because it targets the same object offset with the same codec.
    """
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    out, off, pend = [], None, []
    for i in md.disasm(_read_va(pe, va, va + limit), va):
        m, op = i.mnemonic, i.op_str
        if m == "lea" and "[e" in op and " + " in op:
            base, disp = op.split("[")[1].rstrip("]").split(" + ")
            if base in ("esi", "edi", "ecx"):
                off = int(disp, 16)
        elif m == "push":
            try:
                pend.append(int(op, 16))
            except ValueError:
                pass
        elif m == "call":
            try:
                t = int(op, 16)
            except ValueError:
                pend = []
                continue
            if t in (WSTR_W, WSTR_R):
                ent = ("w", off, 0x48, None)
            elif t in (SCAL_W, SCAL_R):
                ent = ("s", off, pend[-1] if pend else None, pend[0] if pend else None)
            else:
                pend = []
                continue
            if not (out and out[-1][0] == ent[0] and out[-1][1] == ent[1]):
                out.append(ent)
            pend = []
        elif m == "ret":
            break
    return out


def _decode_message_wire(payload: bytes):
    """Decode a Channel_MessageVtial payload under the client Serialize 0x65AD40 schema.

    wstring := tag 0x48 + u32 byte-length + <byte-length> bytes UTF-16LE.
    """
    p = 0
    out = []
    for _ in range(2):
        assert payload[p] == 0x48, "wstring tag 0x48"
        n = struct.unpack_from("<I", payload, p + 1)[0]
        p += 5
        out.append(payload[p:p + n].decode("utf-16le"))
        p += n
    return out[0], out[1], len(payload) - p


class ChatChannelFamilyStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Only parse the PE when the client image exists; the pure-python and
        # server-source tests below must still run without it.  This is shared
        # state, not a skip site - see tests/pf_preconditions.py.
        cls.pe = pefile.PE(str(BINARY), fast_load=True) if CLIENT_IMAGE.present else None

    # -- 1 ----------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_binary_hash_and_spans_are_the_pinned_client(self):
        self.assertEqual(hashlib.sha256(BINARY.read_bytes()).hexdigest().upper(), BINARY_SHA)
        for label, (start, end, expected) in SPANS.items():
            data = _read_va(self.pe, start, end)
            self.assertEqual(len(data), end - start, label)
            self.assertEqual(hashlib.sha256(data).hexdigest().upper(), expected, label)

    # -- 2 ----------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_seventeen_name_literals_and_one_registration_block(self):
        for nm, nva, tva, slot, _g, _v, _s, _z, _n in FAMILY:
            self.assertEqual(_cstr(self.pe, nva), nm)
            b = _read_va(self.pe, tva, tva + 24)
            self.assertEqual(b[0], 0x68)                       # push <name literal>
            self.assertEqual(struct.unpack_from("<I", b, 1)[0], nva)
            self.assertEqual(b[5], 0xE8)                       # call once-init
            self.assertEqual(tva + 10 + struct.unpack_from("<i", b, 6)[0], ONCE_INIT)
            self.assertEqual(b[10:12], b"\x8b\xc8")            # mov ecx, eax
            self.assertEqual(b[12], 0xE8)                      # call id-assign
            self.assertEqual(tva + 17 + struct.unpack_from("<i", b, 13)[0], ID_ASSIGN)
            self.assertEqual(b[17:19], b"\x66\xa3")            # mov word [slot], ax
            self.assertEqual(struct.unpack_from("<I", b, 19)[0], slot)
            self.assertEqual(b[23], 0xC3)
        # the block is contiguous, stride 0x20, 18 entries (17 + CBoardcastVital)
        self.assertEqual([f[2] for f in FAMILY],
                         sorted(f[2] for f in FAMILY))
        gap = _read_va(self.pe, 0xBF7490, 0xBF7490 + 24)
        self.assertEqual(_cstr(self.pe, struct.unpack_from("<I", gap, 1)[0]), "CBoardcastVital")
        # the id-assign chain still reaches the NAMEID-HASH-001 hash
        self.assertIn(("call", hex(HASH_FN)), _instructions(self.pe, ID_ASSIGN, ID_ASSIGN + 64).values())

    # -- 3 -- THE ANCHOR ---------------------------------------------------
    def test_anchor_localtalk_hash_equals_the_captured_wire_id_0xac52(self):
        self.assertEqual(_name_id("Channel_LocalTalkMessageVital"), LOCALTALK_WIRE_ID)

    # -- 4 ----------------------------------------------------------------
    def test_all_seventeen_channel_ids_derive_from_the_in_image_literal(self):
        derived = {nm: _name_id(nm) for nm, *_ in FAMILY}
        self.assertEqual(derived, EXPECT_IDS)
        self.assertEqual(len(set(derived.values())), 17)       # no intra-family collision

    # -- 5 ----------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_channel_ids_are_runtime_assigned_never_code_immediates(self):
        for nm, *_ in FAMILY:
            v = EXPECT_IDS[nm]
            self.assertEqual(_dword_immediate_hits(self.pe, v), [], nm)
            self.assertEqual(_imm16_hits(self.pe, v), [], nm)

    # -- 6 ----------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_each_id_slot_has_one_writer_and_one_get_id_reader(self):
        for nm, _nva, tva, slot, getid, _v, _s, _z, _n in FAMILY:
            self.assertEqual(
                _pattern_sites(self.pe, b"\x66\xa3" + struct.pack("<I", slot)), [tva + 17], nm)
            self.assertEqual(
                _pattern_sites(self.pe, b"\x66\xa1" + struct.pack("<I", slot)), [getid], nm)
            self.assertEqual(_read_va(self.pe, getid, getid + 7),
                             b"\x66\xa1" + struct.pack("<I", slot) + b"\xc3", nm)

    # -- 7 ----------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_vtable_slots_and_two_converging_name_paths(self):
        for nm, _nva, _t, _sl, getid, vt, ser, size, node in FAMILY:
            self.assertEqual(_dword(self.pe, vt + 0x08), COHORT_CONST, nm)
            self.assertEqual(_dword(self.pe, vt + 0x10), getid, nm)
            self.assertEqual(_dword(self.pe, vt + 0x18), ser, nm)
            szf = _dword(self.pe, vt + 0x0C)
            b = _read_va(self.pe, szf, szf + 6)
            self.assertEqual(b[0], 0xB8, nm)
            self.assertEqual(struct.unpack_from("<I", b, 1)[0], size, nm)
            self.assertEqual(b[5], 0xC3, nm)
            # independent path: vtable+0x00 -> type-node getter -> node -> name
            t = _dword(self.pe, vt)
            g = _read_va(self.pe, t, t + 6)
            if g[0] == 0xE9:
                t = t + 5 + struct.unpack_from("<i", g, 1)[0]
                g = _read_va(self.pe, t, t + 6)
            self.assertEqual(g[0], 0xB8, nm)
            self.assertEqual(g[5], 0xC3, nm)
            self.assertEqual(struct.unpack_from("<I", g, 1)[0], node, nm)
            self.assertEqual(NODE_NAME[node], nm)

    # -- 8 ----------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_class_hierarchy_from_the_type_node_registration_block(self):
        parsed = {}
        for tva in range(0xBF74F0, 0xBF7AB0, 0x40):
            b = _read_va(self.pe, tva, tva + 0x40)
            self.assertEqual(b[0], 0x68)             # push allocator
            self.assertEqual(b[5], 0xB9)             # mov ecx, <type descriptor>
            self.assertEqual(b[10:12], b"\xff\x15")  # call [demangler]
            td = struct.unpack_from("<I", b, 6)[0]
            p, parent = 0x11, None
            if b[p] == 0x68:
                parent = struct.unpack_from("<I", b, p + 1)[0]
                p += 5
            elif b[p] == 0xE8:                       # root form: call, then push eax
                p += 6
            self.assertEqual(b[p], 0xB9)             # mov ecx, <own node>
            node = struct.unpack_from("<I", b, p + 1)[0]
            self.assertEqual(b[p + 5], 0xE8)         # call the registrar
            self.assertEqual(tva + p + 10 + struct.unpack_from("<i", b, p + 6)[0], TYPE_REG)
            parsed[node] = (_cstr(self.pe, td + 8, 160), parent)
        self.assertEqual(len(parsed), 23)
        for node, (tdname, parent) in parsed.items():
            nm = NODE_NAME[node]
            self.assertEqual(tdname, ".?AV%s@@" % nm)
            self.assertEqual(NODE_NAME.get(parent) if parent else None, EXPECT_PARENT[nm], nm)
        # the routing taxonomy the hierarchy encodes
        self.assertIsNone(parsed[0x1084448][1])                                # Basic = root
        kids = lambda p: sorted(NODE_NAME[n] for n, v in parsed.items() if v[1] == p)
        self.assertEqual(kids(0x1084448), ["Channel_CommandVtial",
                                           "Channel_ForbidTalkNotificationVtial",
                                           "Channel_MessageVtial"])
        self.assertEqual(kids(0x1084430), ["Channel_GlobalVital", "Channel_LocalVital"])
        self.assertEqual(kids(0x108440C), ["Channel_LocalTalkMessageVital",
                                           "Channel_PartyMessageVital"])
        self.assertEqual(len(kids(0x1084418)), 7)   # Global leaves
        self.assertEqual(len(kids(0x108443C)), 7)   # Command leaves
        # the 5 abstract bases carry no wire id at all
        self.assertEqual(set(NODE_NAME[n] for n in parsed) - set(EXPECT_IDS),
                         {"Channel_BasicVtial", "Channel_CommandVtial",
                          "Channel_MessageVtial", "Channel_GlobalVital",
                          "Channel_LocalVital", "CBoardcastVital"})

    # -- 9 ----------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_codecs_and_bidirectional_serializer_shape(self):
        # wstring codec: tag 0x48, field = u32 byte-length + 2*len bytes, ret 4
        w = _instructions(self.pe, WSTR_W, WSTR_W + 0x70)
        self.assertEqual(w[0x89A828], ("add", "edi, edi"))
        self.assertEqual(w[0x89A82F], ("lea", "eax, [edi + 4]"))
        self.assertEqual(_read_va(self.pe, 0x89A833, 0x89A835), b"\x6a\x48")
        self.assertEqual(_read_va(self.pe, 0x89A872, 0x89A875), b"\xc2\x04\x00")
        self.assertEqual(_read_va(self.pe, 0x89A89C, 0x89A89E), b"\x6a\x48")   # read side
        # scalar codec: stdcall(tag, ptr, width) ret 0xC — the MOVE-PROJECT-001 codec
        self.assertEqual(_read_va(self.pe, 0x89A63D, 0x89A640), b"\xc2\x0c\x00")
        # every channel Serialize is one bidirectional thiscall ret 8
        for ser in SCHEMA:
            ins = _instructions(self.pe, ser, ser + 0x120)
            self.assertIn(("ret", "8"), ins.values(), hex(ser))
            body = _read_va(self.pe, ser, ser + 0x120)
            self.assertTrue(b"\x84\xdb" in body or b"\x80\x7c\x24\x08\x00" in body, hex(ser))

    # -- 10 ---------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_every_channel_wire_schema_decodes_byte_exact(self):
        for ser, want in SCHEMA.items():
            self.assertEqual(_decode_serializer(self.pe, ser), want, hex(ser))
        # five channels share the Channel_MessageVtial serializer => wire-identical
        shared = sorted(nm for nm, *r in FAMILY if r[5] == 0x65AD40)
        self.assertEqual(shared, sorted(["Channel_ActorBoardcastMessageVital",
                                         "Channel_GMGlobalMessageVital",
                                         "Channel_GuildMessageVital",
                                         "Channel_LocalTalkMessageVital",
                                         "Channel_PartyMessageVital"]))
        self.assertEqual(SCHEMA[0x65AD40],
                         [("w", 0x34, 0x48, None), ("w", 0x18, 0x48, None)])

    # -- 11 ---------------------------------------------------------------
    def test_gt006_capture_replays_under_the_decoded_localtalk_schema(self):
        speaker, body, remain = _decode_message_wire(GT006_PAYLOAD)
        self.assertEqual(speaker, "")            # wstring@+0x34, empty in every capture
        self.assertEqual(body, "PFCHATPROBE1")   # wstring@+0x18
        self.assertEqual(remain, 0)
        self.assertEqual(len(GT006_PAYLOAD), 34)
        # a re-encode under the same schema reproduces the captured bytes exactly
        def enc(s):
            u = s.encode("utf-16le")
            return b"\x48" + struct.pack("<I", len(u)) + u
        self.assertEqual(enc("") + enc("PFCHATPROBE1"), GT006_PAYLOAD)

    # -- 12 ---------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_whisper_is_the_only_channel_with_a_recipient_field(self):
        triples = [nm for nm, *r in FAMILY
                   if sum(1 for e in SCHEMA[r[5]] if e[0] == "w") >= 3]
        self.assertEqual(triples, ["Channel_WhisperVital"])
        s = _instructions(self.pe, 0x65AEA0, 0x65AF20)
        self.assertEqual(s[0x65AEAD], ("lea", "eax, [esi + 0x34]"))   # speaker
        self.assertEqual(s[0x65AEC3], ("lea", "eax, [esi + 0x18]"))   # body
        self.assertEqual(s[0x65AED9], ("lea", "eax, [esi + 0x50]"))   # recipient
        self.assertEqual(s[0x65AEF1], ("lea", "eax, [esi + 0x6c]"))   # result u8
        self.assertEqual(_read_va(self.pe, 0x65AEF7, 0x65AEF9), b"\x6a\x0b")
        # the ctor proves +0x50/+0x6C are Whisper's OWN fields
        c = _instructions(self.pe, 0x658240, 0x6582A0)
        self.assertEqual(c[0x658268], ("call", "0x657c90"))           # base ctor
        self.assertEqual(c[0x65826D], ("lea", "ecx, [esi + 0x50]"))
        self.assertEqual(c[0x658278], ("mov", "dword ptr [esi], 0xf37788"))
        self.assertEqual(c[0x658284], ("mov", "byte ptr [esi + 0x6c], 0"))
        # and the clone chains the base clone then copies exactly those two
        k = _instructions(self.pe, 0x65AF20, 0x65AF71)
        self.assertEqual(k[0x65AF24], ("call", "0x65acb0"))
        self.assertEqual(k[0x65AF53], ("lea", "eax, [ebx + 0x50]"))
        self.assertEqual(k[0x65AF63], ("mov", "byte ptr [esi + 0x6c], cl"))
        # dispatcher treats +0x6C as a result code (1 -> msg 0x0B, 2 -> msg 0x18)
        d = _instructions(self.pe, 0x659989, 0x6599C0)
        self.assertEqual(d[0x65999B], ("mov", "al, byte ptr [esi + 0x6c]"))
        self.assertEqual(d[0x65999E], ("cmp", "al, 1"))
        self.assertEqual(_read_va(self.pe, 0x6599A2, 0x6599A4), b"\x6a\x0b")
        self.assertEqual(d[0x6599A9], ("cmp", "al, 2"))
        self.assertEqual(_read_va(self.pe, 0x6599AD, 0x6599AF), b"\x6a\x18")

    # -- 13 ---------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_join_leave_membership_lifecycle_is_result_gated(self):
        for nm in ("Channel_JoinCustomChannelVital",
                   "Channel_OnActorJoinCustomChannelVital",
                   "Channel_LeaveCustomChannelVital",
                   "Channel_OnActorLeaveCustomChannelVital"):
            self.assertEqual(EXPECT_PARENT[nm], "Channel_CommandVtial")
        # the two OnActor* notifications share one serializer and add the actor name
        self.assertEqual([nm for nm, *r in FAMILY if r[5] == 0x65B140],
                         ["Channel_OnActorJoinCustomChannelVital",
                          "Channel_OnActorLeaveCustomChannelVital"])
        self.assertEqual(SCHEMA[0x65B140],
                         [("s", 0x18, 0x32, 8), ("w", 0x20, 0x48, None),
                          ("w", 0x3C, 0x48, None)])
        # the request side has no actor name, but does carry a trailing result byte
        self.assertEqual(SCHEMA[0x65AF80][-1], ("s", 0x3D, 0x0B, 1))
        for nm, _nva, _t, _sl, _g, vt, _s, _z, _n in FAMILY:
            want, _gate = DELIVER_HOOK.get(nm, (PLAIN_HOOK, None))
            self.assertEqual(_dword(self.pe, vt + 0x1C), want, nm)
        self.assertEqual(_instructions(self.pe, 0x65C8B0, 0x65C8E0)[0x65C8C3],
                         ("mov", "al, byte ptr [edi + 0x3d]"))
        self.assertEqual(_instructions(self.pe, 0x65C950, 0x65C980)[0x65C962],
                         ("cmp", "byte ptr [edi + 0x21], 0"))
        self.assertEqual(_instructions(self.pe, 0x65CB40, 0x65CB70)[0x65CB52],
                         ("cmp", "byte ptr [edi + 0x24], 0"))
        # each gate offset is the last u8 of that channel's own schema
        self.assertEqual(SCHEMA[0x65AF80][-1][1], 0x3D)
        self.assertEqual(SCHEMA[0x65B060][-2][1], 0x21)
        self.assertEqual(SCHEMA[0x65B260][-1][1], 0x21)
        self.assertEqual(SCHEMA[0x65B450][-1][1], 0x24)

    # -- 14 ---------------------------------------------------------------
    @CLIENT_IMAGE.skip_unless_present()  # see tests/pf_preconditions.py
    def test_client_routing_into_channelmodule_client(self):
        h = _instructions(self.pe, PLAIN_HOOK, PLAIN_HOOK + 0x60)
        self.assertEqual(h[PLAIN_HOOK], ("mov", "eax, dword ptr [0x1032ec4]"))
        self.assertEqual(_read_va(self.pe, 0x65C863, 0x65C868),
                         b"\x68" + struct.pack("<I", MODULE_NAME_VA))
        self.assertEqual(_cstr(self.pe, MODULE_NAME_VA), "ChannelModule_Client")
        self.assertEqual(_read_va(self.pe, MODULE_NODE_GET, MODULE_NODE_GET + 6),
                         b"\xb8" + struct.pack("<I", MODULE_NODE) + b"\xc3")
        self.assertEqual(h[0x65C888], ("call", hex(TYPE_ISA)))
        self.assertEqual(h[0x65C89C], ("call", hex(DELIVER)))
        # ordered downcast chain, 14 of the 17 channels
        for bva, helper, nm in DISPATCH_ORDER:
            self.assertEqual(_instructions(self.pe, bva, bva + 8)[bva],
                             ("call", hex(helper)), nm)
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
            node = None
            for j in md.disasm(_read_va(self.pe, helper, helper + 0x30), helper):
                if j.mnemonic == "call":
                    try:
                        stub = int(j.op_str, 16)
                    except ValueError:
                        continue
                    b = _read_va(self.pe, stub, stub + 6)
                    if b[0] == 0xB8 and b[5] == 0xC3:
                        node = struct.unpack_from("<I", b, 1)[0]
                        break
            self.assertEqual(NODE_NAME.get(node), nm)
        self.assertEqual(len(DISPATCH_ORDER), 14)
        for pva, sva, want in STYLE_NAMES:
            self.assertEqual(_read_va(self.pe, pva, pva + 5),
                             b"\x68" + struct.pack("<I", sva), want)
            self.assertEqual(_wstr(self.pe, sva), want)
        # three channels have no consumer at all (only their own clone self-check)
        for nm in UNROUTED:
            row = [f for f in FAMILY if f[0] == nm][0]
            clone = _dword(self.pe, row[5] + 0x24)
            sites = [x for x in _pattern_sites(self.pe, b"\x68" + struct.pack("<I", row[8]))
                     if not clone <= x < clone + 0x100]
            self.assertEqual(sites, [], nm)

    # -- 15 ---------------------------------------------------------------
    def test_server_knows_none_of_the_family_except_one_opaque_id(self):
        src = SERVER.read_text(encoding="utf-8", errors="replace")
        self.assertNotIn("Channel_", src)
        for nm, *_ in FAMILY:
            self.assertNotIn("0x%04X" % EXPECT_IDS[nm], src.upper(), nm)
        chat = CHAT_MOD.read_text(encoding="utf-8", errors="replace")
        self.assertIn("CHAT_INPUT_VITAL_ID = 0xAC52", chat)
        self.assertIn("UNKNOWN_0xAC52", chat)
        self.assertIn("unknown to the server registry", chat)
        self.assertIn("compared as one opaque pinned blob", chat)
        for nm, *_ in FAMILY:
            if nm != "Channel_LocalTalkMessageVital":
                self.assertNotIn("0x%04X" % EXPECT_IDS[nm], chat.upper(), nm)
        flat = chat.replace('"', "").replace("\n", "").replace(" ", "").upper()
        self.assertIn(GT006_PAYLOAD.hex().upper(), flat)


if __name__ == "__main__":
    unittest.main()
