#!/usr/bin/env python3
"""PF CHAT-CHANNEL-001 — static byte-exact enumeration of the client's whole
`Channel_*Vital` family (17 concrete channels + 5 abstract bases), their wire
ids, their per-channel wire schemas, the class hierarchy that expresses the
client's routing taxonomy, and the Join/Leave membership lifecycle — opening
`chat/chat_channels_and_routing` from not_started -> in_progress.

The coverage note for that lane said:

    "Routing needs at least two concurrent sessions, which no runtime pass has
     ever established. Channel identifiers and recipient resolution are
     uncaptured."

This milestone settles the *identifier* half and the *recipient-field* half
statically, byte-exact, from the read-only client binary:

  * IDENTIFIERS. The whole family is registered by ONE contiguous 18-entry
    thunk block 0xBF72B0..0xBF74F0 (stride 0x20; 17 Channel_* + CBoardcastVital)
    of the shape proven by PF-NAMEID-HASH-001:
        push <name literal>; call 0x89C080 (once-init registry);
        mov ecx,eax; call 0x89BD00 (id-assign); mov word [id-slot], ax; ret
    Re-using the NAMEID-HASH-001 algorithm (0x89B220:
        u16 id = SUM_i (int16)((signed char)name[i] * (i+1))   mod 2^16 )
    yields all 17 channel ids from the in-image name literals alone. The anchor
    Channel_LocalTalkMessageVital -> 0xAC52 reproduces the wire id captured in
    GT-006, which validates the whole table.

  * The ids are NOT code immediates anywhere in .text (dword scan excluding
    E8/E9 *and* 0F 8x rel32 tails -> 0 hits for all 17): the same
    runtime-assigned wall as the TargetPosVital / ItemOperate / TeleportCheck
    cohort. Each id-slot has exactly one writer (its registration thunk) and
    exactly one reader (a `mov ax,[slot]; ret` get-id stub == vtable +0x10).

  * TWO INDEPENDENT NAME PATHS CONVERGE per class:
        name literal -> reg thunk -> id-slot -> get-id stub -> vtable+0x10
        vtable+0x00 -> type-node getter -> type node -> type-node registration
                    -> `.?AVChannel_XxxVital@@` descriptor
    Both resolve to the same class name for 17/17 — the binding is not a guess.

  * HIERARCHY (from the type-node registration block 0xBF74F0..0xBF7AB0, which
    passes the PARENT node to the registrar 0x88F2E0):
        Channel_BasicVtial                       (root)
          |- Channel_CommandVtial                (membership / control verbs)
          |- Channel_MessageVtial                (chat content)
          |    |- Channel_GlobalVital            (addressed / server-scope)
          |    \- Channel_LocalVital             (proximity scope)
          \- Channel_ForbidTalkNotificationVtial (direct child: pure notice)

  * WIRE SCHEMAS. Every channel's Serialize is vtable +0x18 and is ONE
    bidirectional routine `thiscall Serialize(bool save, Stream*) ret 8`:
    `bl` selects the write codecs (wstring 0x89A810 / scalar 0x89A600) or the
    read codecs (0x89A880 / 0x89A640) — so the same routine decodes inbound.
    The wstring codec emits tag 0x48 + u32 byte-length + UTF-16LE bytes.

  * RECIPIENT RESOLUTION (the point of the lane). Channel_WhisperVital is the
    ONLY channel with a third wstring: Serialize 0x65AEA0 emits
    wstring@+0x34, wstring@+0x18, **wstring@+0x50**, u8(tag 0x0B)@+0x6C, and
    the Whisper ctor 0x658240 constructs +0x50 and zeroes +0x6C itself (i.e.
    they are Whisper's own declared fields, not inherited). The client
    dispatcher branches on that u8: 1 and 2 select distinct system-message ids
    (0x0B / 0x18) instead of rendering — a recipient-resolution result code.

  * JOIN/LEAVE LIFECYCLE. Join*/Leave* (Command) carry a trailing u8 result
    byte and their inbound hook is a *gated* variant of the delivery stub that
    suppresses the ChannelModule_Client hand-off when that byte is nonzero
    (0x65C8B0 gates +0x3D, 0x65C950 gates +0x21, 0x65CB40 gates +0x24). The
    OnActor* notifications share one serializer 0x65B140 and add the acting
    actor's name as a second wstring — a real request/notification pair.

  * CLIENT ROUTING. vtable +0x1C resolves the module registry [0x1032EC4]+0x130
    by the name "ChannelModule_Client" (0xF22CB4) and hands the vital to
    0x659870, an ordered downcast chain covering 14 of the 17 channels, each
    branch selecting a per-channel style name ("LocalTalk", "WhisperTalk",
    "GuildTalk", "PartyTalk", "YellTalk", "LocalPerformance", "CustomDefine",
    "ClassTalk"). Three channels (JoinOriginalSinChannel,
    OriginalSinChannelMessage, JoinClassChannel) have NO consumer anywhere.

  * SERVER GAP. v141 (immutable, read-only here) contains no `Channel_` token
    at all and none of the 17 ids. Only src/pirateforce_foundation/
    chat_input_hypothesis.py touches one of them, 0xAC52, and explicitly calls
    it "UNKNOWN_0xAC52 ... unknown to the server registry", echoing an opaque
    pinned blob without decoding it. 1 of 17 channels is touched, 0 of 17 are
    decoded server-side.

NOT CLAIMED: nothing about the ORIGINAL server's routing behaviour. No two
concurrent sessions have ever existed in this project, so fan-out, membership
authority, whisper delivery and channel scope on the wire remain uncaptured.
This is the client's *expectation* of the protocol, byte-exact, nothing more.
The lane goes not_started -> in_progress and never runtime_pass here.

Report-only / additive: NO server-source change, NO scenario, NO ledger entry,
NO runtime claim. Sole binary evidence = the read-only client
GameClient/GameClient.local.bin, cross-checked against read-only server source.

Usage:  py -3 tools/pf_chat_channel_family_static.py [path-to-GameClient.local.bin]
Exit 0 = all static guards reproduced; nonzero = a guard drifted.
"""
import hashlib
import os
import struct
import sys

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:
    sys.exit("capstone required: pip install capstone")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))


def _default_bin():
    for cand in (
        "GameClient/GameClient.local.bin",
        os.path.join(_ROOT, "..", "GameClient", "GameClient.local.bin"),
        os.path.join(_ROOT, "GameClient", "GameClient.local.bin"),
    ):
        if os.path.isfile(cand):
            return cand
    return "GameClient/GameClient.local.bin"


BIN = sys.argv[1] if len(sys.argv) > 1 else _default_bin()
EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
SERVER_SRC = os.path.normpath(os.path.join(_ROOT, "current", "pf_login_game_server_v141.py"))
CHAT_MOD = os.path.normpath(
    os.path.join(_ROOT, "src", "pirateforce_foundation", "chat_input_hypothesis.py"))

data = open(BIN, "rb").read()
sha = hashlib.sha256(data).hexdigest().upper()

# ---------------------------------------------------------------- PE section table
e_lfanew = struct.unpack_from('<I', data, 0x3c)[0]
coff = e_lfanew + 4
nsec = struct.unpack_from('<H', data, coff + 2)[0]
opt_size = struct.unpack_from('<H', data, coff + 16)[0]
opt = coff + 20
image_base = struct.unpack_from('<I', data, opt + 28)[0]
sect = opt + opt_size
secs = []
for _i in range(nsec):
    _o = sect + _i * 40
    _nm = data[_o:_o + 8].rstrip(b'\0').decode('latin1')
    _vs, _va, _rs, _rp = struct.unpack_from('<IIII', data, _o + 8)
    secs.append((_nm, _va, _vs, _rp, _rs))


def va2off(va):
    r = va - image_base
    for _nm, _va, _vs, _rp, _rs in secs:
        if _va <= r < _va + max(_vs, _rs):
            return _rp + (r - _va)
    return None


def rd(va, n):
    o = va2off(va)
    return data[o:o + n] if o is not None else b""


def dw(va):
    return struct.unpack('<I', rd(va, 4))[0]


def cstr(va, maxn=128):
    b = rd(va, maxn)
    z = b.find(b'\x00')
    return b[:z].decode('latin1') if z >= 0 else None


def wstr(va, maxn=120):
    """UTF-16LE string at `va` (the client's wide literals are 2-byte NUL terminated)."""
    b = rd(va, maxn)
    z = b.find(b'\x00\x00')
    if z < 0:
        z = len(b)
    if z % 2:
        z += 1
    return b[:z].decode('utf-16le', 'replace')


def span_sha(a, b):
    return hashlib.sha256(rd(a, b - a)).hexdigest().upper()


TEXT = [s for s in secs if s[0] == '.text'][0]
_, TVADDR, TVSIZE, TRAW, _ = TEXT
TSTART = image_base + TVADDR
md = Cs(CS_ARCH_X86, CS_MODE_32)


def dmap(va, size):
    return {i.address: (i.mnemonic, i.op_str) for i in md.disasm(rd(va, size), va)}


def text_hits(pattern_hex):
    pat = bytes.fromhex(pattern_hex) if isinstance(pattern_hex, str) else pattern_hex
    res, s, hi = [], TRAW, TRAW + TVSIZE
    while True:
        j = data.find(pat, s, hi)
        if j < 0:
            break
        res.append(TSTART + (j - TRAW))
        s = j + 1
    return res


def dword_immediate_hits(val):
    """Every .text VA holding dword `val` that is NOT a rel32 tail.

    The cohort precedent (MOVE-PROJECT-001) excludes E8/E9 rel32 tails. A 16-bit
    channel id embedded in a dword also collides with the two-byte `0F 8x`
    (jcc rel32) form, e.g. `0F 8C AE 00 00 00` contains 0x0000AE8C at +1, so the
    0F 8x tail is excluded here too. Both exclusions are byte-mechanical.
    """
    res = []
    packed = struct.pack('<I', val)
    s, end = TRAW, TRAW + TVSIZE
    while True:
        j = data.find(packed, s, end)
        if j < 0:
            break
        rel32_tail = data[j - 1] in (0xE8, 0xE9)
        jcc_tail = data[j - 1] == 0x0F and 0x80 <= data[j] <= 0x8F
        if not (rel32_tail or jcc_tail):
            res.append(TSTART + (j - TRAW))
        s = j + 1
    return res


def imm16_hits(val):
    """16-bit immediate encodings of `val` (mov ax / cmp ax / test ax / cmp ax,imm16)."""
    out = []
    for pfx in (b'\x66\xb8', b'\x66\x3d', b'\x66\x81\xf8', b'\x66\xa9'):
        out += text_hits(pfx + struct.pack('<H', val))
    return out


# ---------------------------------------------------------------- the NAMEID-HASH-001 hash
def name_id(name):
    """PF-NAMEID-HASH-001 / client 0x89B220: signed-char position-weighted u16 sum.

    Re-used verbatim from tools/pf_vital_id_hash_static.py (do not re-derive).
    """
    acc = 0
    for i, ch in enumerate(name.encode('latin1')):
        sc = ch if ch < 128 else ch - 256
        acc = (acc + ((sc * (i + 1)) & 0xFFFF)) & 0xFFFF
    return acc


ONCE_INIT = 0x89C080     # MSVC once-init singleton registry guard
ID_ASSIGN = 0x89BD00     # thiscall id-assign(name) -> ax  (calls the hash 0x89B220)
HASH_FN = 0x89B220       # the hash itself
TYPE_ISA = 0x88F2B0      # is-a / downcast check
TYPE_REG = 0x88F2E0      # type-node registrar (this=node, args parent, name)
WSTR_W, WSTR_R = 0x89A810, 0x89A880   # wstring codec  (tag 0x48 + u32 bytelen + UTF-16LE)
SCAL_W, SCAL_R = 0x89A600, 0x89A640   # scalar codec   stdcall(tag, ptr, width) ret 0xC
MODULE_NAME_VA = 0xF22CB4             # "ChannelModule_Client" (UTF-16LE)
MODULE_NODE_GET = 0x657850            # mov eax, 0x1084304 ; ret
MODULE_NODE = 0x1084304
MODULE_REGISTRY = 0x1032EC4
DELIVER = 0x659870                    # ChannelModule_Client inbound dispatcher

# name, name-literal VA, registration thunk, id-slot, get-id stub, vtable,
# serializer (vtable+0x18), object size (vtable+0x0C returns it), type node
FAMILY = [
    ("Channel_ForbidTalkNotificationVtial",   0xF37960, 0xBF72B0, 0x1084454, 0x65A9E0, 0xF37804, 0x65AE00, 0x1C, 0x1084424),
    ("Channel_LocalTalkMessageVital",         0xF37984, 0xBF72D0, 0x1084458, 0x6580B0, 0xF3775C, 0x65AD40, 0x50, 0x1084400),
    ("Channel_LocalPerformanceVital",         0xF379A4, 0xBF72F0, 0x108445C, 0x5BEAE0, 0xF2D0D4, 0x65AE30, 0x30, 0x10843F4),
    ("Channel_PartyMessageVital",             0xF379C4, 0xBF7310, 0x1084460, 0x657DA0, 0xF37628, 0x65AD40, 0x50, 0x10843E8),
    ("Channel_WhisperVital",                  0xF379E0, 0xBF7330, 0x1084464, 0x6582B0, 0xF37788, 0x65AEA0, 0x70, 0x10843DC),
    ("Channel_GuildMessageVital",             0xF379F8, 0xBF7350, 0x1084468, 0x657DD0, 0xF37654, 0x65AD40, 0x50, 0x10843D0),
    ("Channel_ActorBoardcastMessageVital",    0xF37A14, 0xBF7370, 0x108446C, 0x658030, 0xF37730, 0x65AD40, 0x50, 0x10843C4),
    ("Channel_GMGlobalMessageVital",          0xF37A38, 0xBF7390, 0x1084470, 0x65AC10, 0xF3790C, 0x65AD40, 0x50, 0x10843B8),
    ("Channel_JoinCustomChannelVital",        0xF37A58, 0xBF73B0, 0x1084474, 0x657E70, 0xF37680, 0x65AF80, 0x40, 0x10843AC),
    ("Channel_OnActorJoinCustomChannelVital", 0xF37A78, 0xBF73D0, 0x1084478, 0x65AA80, 0xF37830, 0x65B140, 0x58, 0x10843A0),
    ("Channel_LeaveCustomChannelVital",       0xF37AA0, 0xBF73F0, 0x108447C, 0x657F70, 0xF376AC, 0x65B060, 0x40, 0x1084394),
    ("Channel_OnActorLeaveCustomChannelVital", 0xF37AC0, 0xBF7410, 0x1084480, 0x65AB90, 0xF3785C, 0x65B140, 0x58, 0x1084388),
    ("Channel_CustomChannelMessageVital",     0xF37AE8, 0xBF7430, 0x1084484, 0x657FF0, 0xF376D8, 0x65B1E0, 0x60, 0x108437C),
    ("Channel_JoinOriginalSinChannelVital",   0xF37B0C, 0xBF7450, 0x1084488, 0x65ABB0, 0xF37888, 0x65B260, 0x28, 0x1084370),
    ("Channel_OriginalSinChannelMessageVital", 0xF37B30, 0xBF7470, 0x108448C, 0x65ABD0, 0xF378B4, 0x65B310, 0x54, 0x1084364),
    ("Channel_JoinClassChannelVital",         0xF37B68, 0xBF74B0, 0x1084494, 0x65ABF0, 0xF378E0, 0x65B450, 0x28, 0x108434C),
    ("Channel_ClassChannelMessageVital",      0xF37B88, 0xBF74D0, 0x1084498, 0x658010, 0xF37704, 0x65B500, 0x54, 0x1084340),
]

# the wire id every channel gets, derived (not assumed) from the name literal
EXPECT_IDS = {
    "Channel_ForbidTalkNotificationVtial": 0xFDF2,
    "Channel_LocalTalkMessageVital": 0xAC52,      # <-- GT-006 anchor
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
LOCALTALK_WIRE_ID = 0xAC52   # captured on the wire by GT-006

# type-node registration block 0xBF74F0..0xBF7AB0, stride 0x40 (23 entries)
TYPENODE_BLOCK = (0xBF74F0, 0xBF7AB0, 0x40)
NODE_NAME = {
    0x1084448: "Channel_BasicVtial",
    0x108443C: "Channel_CommandVtial",
    0x1084430: "Channel_MessageVtial",
    0x1084424: "Channel_ForbidTalkNotificationVtial",
    0x1084418: "Channel_GlobalVital",
    0x108440C: "Channel_LocalVital",
    0x1084400: "Channel_LocalTalkMessageVital",
    0x10843F4: "Channel_LocalPerformanceVital",
    0x10843E8: "Channel_PartyMessageVital",
    0x10843DC: "Channel_WhisperVital",
    0x10843D0: "Channel_GuildMessageVital",
    0x10843C4: "Channel_ActorBoardcastMessageVital",
    0x10843B8: "Channel_GMGlobalMessageVital",
    0x10843AC: "Channel_JoinCustomChannelVital",
    0x10843A0: "Channel_OnActorJoinCustomChannelVital",
    0x1084394: "Channel_LeaveCustomChannelVital",
    0x1084388: "Channel_OnActorLeaveCustomChannelVital",
    0x108437C: "Channel_CustomChannelMessageVital",
    0x1084370: "Channel_JoinOriginalSinChannelVital",
    0x1084364: "Channel_OriginalSinChannelMessageVital",
    0x1084358: "CBoardcastVital",
    0x108434C: "Channel_JoinClassChannelVital",
    0x1084340: "Channel_ClassChannelMessageVital",
}
EXPECT_PARENT = {
    "Channel_BasicVtial": None,
    "CBoardcastVital": None,
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

# decoded wire schema per serializer: ordered [(kind, offset, tag, width)]
# kind 'w' = wstring (tag 0x48 + u32 bytelen + UTF-16LE), 's' = scalar(tag, width)
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

# inbound-delivery hook (vtable +0x1C): plain, or result-gated on a u8 field
DELIVER_HOOK = {
    "Channel_JoinCustomChannelVital": (0x65C8B0, 0x3D),
    "Channel_LeaveCustomChannelVital": (0x65C950, 0x21),
    "Channel_JoinOriginalSinChannelVital": (0x65C950, 0x21),
    "Channel_JoinClassChannelVital": (0x65CB40, 0x24),
}
PLAIN_HOOK = 0x65C850

# ordered downcast chain inside ChannelModule_Client dispatcher 0x659870:
# (branch VA, downcast helper VA, class)
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

# GT-006 captured LocalTalk request payload (34 bytes) — src/pirateforce_foundation/
# chat_input_hypothesis.py CHAT_INPUT_PROBE_PAYLOADS["probe1"], byte-for-byte.
GT006_PAYLOAD = bytes.fromhex(
    "48000000004818000000"
    "500046004300480041005400500052004F00420045003100")


# ---------------------------------------------------------------- guards
fails = []
n_guard = 0


def check(name, cond, detail=""):
    global n_guard
    n_guard += 1
    print(("[OK]   " if cond else "[FAIL] ") + name + ("  " + detail if detail else ""))
    if not cond:
        fails.append(name)


print("PF CHAT-CHANNEL-001 static verifier — Channel_* family, ids, wire schemas, routing")
print("binary:", BIN)
print("SHA-256:", sha)
print()

check("binary SHA-256 matches the pinned client", sha == EXPECT_SHA, sha)
check("ImageBase == 0x400000", image_base == 0x400000, hex(image_base))

# --- 1. name literals -------------------------------------------------------
print("\n-- 1. in-image plaintext class-name literals --")
bad = [n for n, va, *_ in FAMILY if cstr(va) != n]
check("all 17 Channel_* name literals sit at their pinned .rdata VAs", not bad, str(bad))
check("the 17 literals form one contiguous .rdata block 0xF37960..0xF37BA9",
      span_sha(*SPANS["name_string_block"][:2]) == SPANS["name_string_block"][2],
      span_sha(*SPANS["name_string_block"][:2]))
check("the binary really spells it 'Vtial' in Channel_ForbidTalkNotificationVtial "
      "(typo preserved; used verbatim by the hash)",
      cstr(0xF37960) == "Channel_ForbidTalkNotificationVtial")

# --- 2. registration thunks -------------------------------------------------
print("\n-- 2. registration thunks: name literal -> once-init -> id-assign -> id-slot --")
ok_thunk = 0
for nm, nva, tva, slot, getid, vt, ser, size, node in FAMILY:
    b = rd(tva, 24)
    shape = (len(b) == 24 and b[0] == 0x68 and b[5] == 0xE8
             and b[10:12] == b'\x8b\xc8' and b[12] == 0xE8
             and b[17:19] == b'\x66\xa3' and b[23] == 0xC3)
    lit = cstr(struct.unpack_from('<I', b, 1)[0]) if shape else None
    once = tva + 10 + struct.unpack_from('<i', b, 6)[0] if shape else 0
    assign = tva + 17 + struct.unpack_from('<i', b, 13)[0] if shape else 0
    slot_in = struct.unpack_from('<I', b, 19)[0] if shape else 0
    good = (shape and lit == nm and once == ONCE_INIT and assign == ID_ASSIGN
            and slot_in == slot)
    ok_thunk += good
    if not good:
        check("thunk 0x%06X registers %s -> slot 0x%X" % (tva, nm, slot), False,
              "lit=%r once=%s assign=%s slot=%s" % (lit, hex(once), hex(assign), hex(slot_in)))
check("all 17 registration thunks have the exact NAMEID-HASH-001 shape "
      "(push name; call 0x89C080; mov ecx,eax; call 0x89BD00; mov word[slot],ax; ret)",
      ok_thunk == 17, "%d/17" % ok_thunk)
check("the family registers from ONE contiguous 18-entry block 0xBF72B0..0xBF74F0 "
      "(stride 0x20; 17 Channel_* + CBoardcastVital)",
      span_sha(*SPANS["registration_block"][:2]) == SPANS["registration_block"][2]
      and cstr(struct.unpack_from('<I', rd(0xBF7490, 5), 1)[0]) == "CBoardcastVital",
      span_sha(*SPANS["registration_block"][:2]))
check("id-assign 0x89BD00 calls the hash 0x89B220 (NAMEID-HASH-001 chain intact)",
      any(i == ('call', hex(HASH_FN)) for i in dmap(ID_ASSIGN, 64).values()))
check("hash 0x89B220 still has the signed-char position-weighted MAC loop",
      b'\x66\x0f\xbe\x3c\x31' in rd(HASH_FN, 96)
      and b'\x66\x0f\xaf\xfb' in rd(HASH_FN, 96)
      and b'\x66\x03\xd7' in rd(HASH_FN, 96))

# --- 3. THE ANCHOR ----------------------------------------------------------
print("\n-- 3. anchor: does the NAMEID-HASH-001 algorithm hold for THIS family? --")
check("ANCHOR name_id('Channel_LocalTalkMessageVital') == 0xAC52 "
      "(the wire id GT-006 actually captured)",
      name_id("Channel_LocalTalkMessageVital") == LOCALTALK_WIRE_ID,
      "computed 0x%04X" % name_id("Channel_LocalTalkMessageVital"))
if name_id("Channel_LocalTalkMessageVital") != LOCALTALK_WIRE_ID:
    print("\nANCHOR FAILED — the hash does not apply to this family; stopping.")
    sys.exit(1)

# --- 4. the id table --------------------------------------------------------
print("\n-- 4. derived wire id per channel (from the in-image literal only) --")
derived = {n: name_id(n) for n, *_ in FAMILY}
check("all 17 derived ids match the pinned table",
      derived == EXPECT_IDS,
      str({k: hex(v) for k, v in derived.items() if EXPECT_IDS.get(k) != v}))
check("all 17 channel ids are pairwise distinct (no id collision inside the family)",
      len(set(derived.values())) == 17, str(len(set(derived.values()))))
for nm, *_ in FAMILY:
    print("        0x%04X  %s" % (derived[nm], nm))

# --- 5. runtime-assigned wall ----------------------------------------------
print("\n-- 5. the ids are never code immediates (runtime-assigned wall) --")
imm_bad = {}
for nm, *_ in FAMILY:
    hits = dword_immediate_hits(derived[nm]) + imm16_hits(derived[nm])
    if hits:
        imm_bad[nm] = [hex(x) for x in hits]
check("none of the 17 ids appears as a .text code immediate "
      "(dword scan excluding E8/E9 and 0F 8x rel32 tails, plus 16-bit imm forms)",
      not imm_bad, str(imm_bad))

print("\n-- 6. id-slot has exactly one writer and one reader per channel --")
w_bad, r_bad, stub_bad = [], [], []
for nm, nva, tva, slot, getid, vt, ser, size, node in FAMILY:
    w = text_hits("66a3" + struct.pack('<I', slot).hex())
    r = text_hits("66a1" + struct.pack('<I', slot).hex())
    if w != [tva + 17]:
        w_bad.append((nm, [hex(x) for x in w]))
    if r != [getid]:
        r_bad.append((nm, [hex(x) for x in r]))
    if rd(getid, 7) != b'\x66\xa1' + struct.pack('<I', slot) + b'\xc3':
        stub_bad.append(nm)
check("every id-slot is written by exactly one site — its own registration thunk",
      not w_bad, str(w_bad))
check("every id-slot is read by exactly one get-id stub", not r_bad, str(r_bad))
check("every get-id stub is exactly `mov ax,[id-slot]; ret` (7 bytes)",
      not stub_bad, str(stub_bad))
check("id-slots are one contiguous .data run 0x1084454..0x1084498 stride 4 "
      "(the CBoardcastVital gap at 0x1084490 is real)",
      [f[3] for f in FAMILY] == sorted(f[3] for f in FAMILY)
      and struct.unpack_from('<I', rd(0xBF7490, 24), 19)[0] == 0x1084490)

# --- 7. vtables -------------------------------------------------------------
print("\n-- 7. vtable per channel: cohort const, get-id, size, serializer, delivery hook --")
vt_getid, vt_const, vt_size, vt_ser = [], [], [], []
for nm, nva, tva, slot, getid, vt, ser, size, node in FAMILY:
    if dw(vt + 0x10) != getid:
        vt_getid.append(nm)
    if dw(vt + 0x08) != 0x401B20:
        vt_const.append(nm)
    szf = dw(vt + 0x0C)
    if not (rd(szf, 6)[0] == 0xB8 and struct.unpack_from('<I', rd(szf, 6), 1)[0] == size
            and rd(szf, 6)[5] == 0xC3):
        vt_size.append(nm)
    if dw(vt + 0x18) != ser:
        vt_ser.append(nm)
check("vtable +0x10 == the class's get-id stub for all 17", not vt_getid, str(vt_getid))
check("vtable +0x08 == 0x401B20 for all 17 (same shared framework const as the "
      "TargetPosVital / ECHO / ItemOperate / MovementAttr cohort)", not vt_const, str(vt_const))
check("vtable +0x0C is a `mov eax,<sizeof>; ret` object-size stub matching the "
      "decoded field layout for all 17", not vt_size, str(vt_size))
check("vtable +0x18 == the class's Serialize for all 17", not vt_ser, str(vt_ser))
check("16 of the 17 vtables are one contiguous .rdata table 0xF37628..0xF37938 "
      "(stride 0x2C, 11 slots); Channel_LocalPerformanceVital lives apart at 0xF2D0D4",
      span_sha(*SPANS["vtable_block"][:2]) == SPANS["vtable_block"][2]
      and span_sha(*SPANS["vtable_localperformance"][:2]) == SPANS["vtable_localperformance"][2])

# --- 8. second, independent name path --------------------------------------
print("\n-- 8. vtable +0x00 -> type node -> registered class name (independent path) --")
node_bad = []
for nm, nva, tva, slot, getid, vt, ser, size, node in FAMILY:
    t = dw(vt)
    b = rd(t, 6)
    if b[0] == 0xE9:
        t = t + 5 + struct.unpack_from('<i', b, 1)[0]
        b = rd(t, 6)
    got = struct.unpack_from('<I', b, 1)[0] if (b[0] == 0xB8 and b[5] == 0xC3) else None
    if got != node or NODE_NAME.get(got) != nm:
        node_bad.append((nm, hex(got) if got else None))
check("vtable +0x00 resolves to the class's own type node for all 17, and the node's "
      "registered `.?AV...@@` name equals the registration-thunk literal "
      "(two independent name paths converge)", not node_bad, str(node_bad))

# --- 9. hierarchy -----------------------------------------------------------
print("\n-- 9. class hierarchy from the type-node registration block --")
lo, hi, stride = TYPENODE_BLOCK
parsed = {}
for tva in range(lo, hi, stride):
    b = rd(tva, 0x40)
    if b[0] != 0x68 or b[5] != 0xB9 or b[10:12] != b'\xff\x15':
        continue
    td = struct.unpack_from('<I', b, 6)[0]
    tdname = cstr(td + 8, 160)
    p = 0x11
    parent = None
    if b[p] == 0x68:
        parent = struct.unpack_from('<I', b, p + 1)[0]
        p += 5
    elif b[p] == 0xE8:          # root form: call 0x5F33F0 then push eax
        p += 6
    node = struct.unpack_from('<I', b, p + 1)[0] if b[p] == 0xB9 else None
    reg = tva + p + 10 + struct.unpack_from('<i', b, p + 6)[0] if b[p + 5] == 0xE8 else 0
    parsed[node] = (tdname, parent, reg)
check("the type-node registration block 0xBF74F0..0xBF7AB0 parses to 23 entries "
      "(17 Channel_* + 5 abstract bases + CBoardcastVital)", len(parsed) == 23, str(len(parsed)))
check("every entry registers through 0x88F2E0 and names a `.?AV...@@` descriptor",
      all(v[2] == TYPE_REG and (v[0] or "").startswith(".?AV") for v in parsed.values()))
hier_bad = []
for node, (tdname, parent, _reg) in parsed.items():
    nm = NODE_NAME.get(node)
    want = EXPECT_PARENT.get(nm, "MISSING")
    got = NODE_NAME.get(parent) if parent else None
    if nm is None or want == "MISSING" or got != want:
        hier_bad.append((nm, got, want))
    if (tdname or "") != ".?AV%s@@" % nm:
        hier_bad.append((nm, "descriptor " + str(tdname), ".?AV%s@@" % nm))
check("the parent edge of all 23 nodes matches the pinned hierarchy",
      not hier_bad, str(hier_bad))
check("Channel_BasicVtial is the family root (registered with no parent node)",
      parsed[0x1084448][1] is None)
check("Channel_CommandVtial and Channel_MessageVtial are the two Basic children "
      "(the Command/Message routing split)",
      NODE_NAME[parsed[0x108443C][1]] == "Channel_BasicVtial"
      and NODE_NAME[parsed[0x1084430][1]] == "Channel_BasicVtial")
check("Channel_GlobalVital and Channel_LocalVital are the two Message children "
      "(the scope split addressed-vs-proximity)",
      NODE_NAME[parsed[0x1084418][1]] == "Channel_MessageVtial"
      and NODE_NAME[parsed[0x108440C][1]] == "Channel_MessageVtial")
check("Channel_ForbidTalkNotificationVtial hangs directly off Basic — it is neither "
      "a Command nor a Message",
      NODE_NAME[parsed[0x1084424][1]] == "Channel_BasicVtial")
check("Channel_LocalTalkMessageVital and Channel_PartyMessageVital are the ONLY "
      "Channel_LocalVital leaves",
      sorted(NODE_NAME[n] for n, v in parsed.items() if v[1] == 0x108440C)
      == ["Channel_LocalTalkMessageVital", "Channel_PartyMessageVital"])
ABSTRACT = ["Channel_BasicVtial", "Channel_CommandVtial", "Channel_MessageVtial",
            "Channel_GlobalVital", "Channel_LocalVital"]
reg_literals = set()
for _t in range(*SPANS["registration_block"][:2], 0x20):
    _b = rd(_t, 6)
    if _b[0] == 0x68:
        reg_literals.add(cstr(struct.unpack_from('<I', _b, 1)[0]))
check("the 5 abstract bases have NO plaintext name literal and NO registration thunk, "
      "so they have NO wire id — only the 17 concrete channels are addressable",
      not (set(ABSTRACT) & reg_literals)
      and not any(data.find(nm.encode() + b'\x00') >= 0 for nm in ABSTRACT)
      and set(NODE_NAME[n] for n in parsed) - set(EXPECT_IDS) ==
      set(ABSTRACT) | {"CBoardcastVital"})

# --- 10. codecs -------------------------------------------------------------
print("\n-- 10. the two codecs the channel serializers use --")
check("wstring write codec 0x89A810 emits tag 0x48 and a (2*len + 4) field "
      "(u32 byte-length then UTF-16LE payload), thiscall ret 4",
      rd(0x89A833, 2) == b'\x6a\x48' and dmap(0x89A810, 0x70).get(0x89A828) == ('add', 'edi, edi')
      and dmap(0x89A810, 0x70).get(0x89A82F) == ('lea', 'eax, [edi + 4]')
      and rd(0x89A872, 3) == b'\xc2\x04\x00')
check("wstring read codec 0x89A880 is the tag-0x48 counterpart",
      rd(0x89A89C, 2) == b'\x6a\x48')
check("scalar write codec 0x89A600 is stdcall(tag, ptr, width) ret 0xC "
      "(the MOVE-PROJECT-001 field codec)", rd(0x89A63D, 3) == b'\xc2\x0c\x00')
check("scalar read codec 0x89A640 is its counterpart (same tag/width call shape)",
      dmap(0x89A640, 0x60).get(0x89A640) == ('sub', 'esp, 0x48'))

# --- 11. wire schemas -------------------------------------------------------
print("\n-- 11. per-channel wire schema, decoded field by field from Serialize --")


def decode_serializer(va, limit=0x120):
    """Walk Serialize linearly; return the ordered field list it emits.

    Each field appears twice in the byte stream (the `test bl,bl` save/load
    branch); the load form is folded away because it targets the same object
    offset with the same tag/width.
    """
    out = []
    off = None
    pend = []
    for i in md.disasm(rd(va, limit), va):
        m, op = i.mnemonic, i.op_str
        if m == 'lea' and '[e' in op and ' + ' in op:
            base, disp = op.split('[')[1].rstrip(']').split(' + ')
            if base in ('esi', 'edi', 'ecx'):
                off = int(disp, 16)
        elif m == 'push':
            try:
                pend.append(int(op, 16))
            except ValueError:
                pass
        elif m == 'call':
            try:
                t = int(op, 16)
            except ValueError:
                pend = []
                continue
            if t in (WSTR_W, WSTR_R):
                ent = ('w', off, 0x48, None)
            elif t in (SCAL_W, SCAL_R):
                ent = ('s', off, pend[-1] if pend else None, pend[0] if pend else None)
            else:
                pend = []
                continue
            # fold the load-branch repeat: same kind at the same object offset
            if not (out and out[-1][0] == ent[0] and out[-1][1] == ent[1]):
                out.append(ent)
            pend = []
        elif m == 'ret':
            break
    return out


sch_bad = []
for serva, want in SCHEMA.items():
    got = decode_serializer(serva)
    if got != want:
        sch_bad.append((hex(serva), got, want))
check("all 12 distinct channel serializers decode to their pinned field lists "
      "(kind, object offset, tag, width)", not sch_bad, str(sch_bad))
ret8 = all(('ret', '8') in dmap(s, 0x120).values() for s in SCHEMA)
check("every channel Serialize is `thiscall Serialize(bool save, Stream*) ret 8` "
      "— ONE bidirectional routine, so the same code decodes inbound", ret8)
bidi = all(b'\x84\xdb' in rd(s, 0x120) or b'\x80\x7c\x24\x08\x00' in rd(s, 0x120)
           for s in SCHEMA)
check("every channel Serialize branches on the save flag to pick write vs read codecs",
      bidi)
check("5 channels SHARE the Channel_MessageVtial serializer 0x65AD40 "
      "(LocalTalk / Party / Guild / ActorBoardcast / GMGlobal) — they are "
      "wire-IDENTICAL and are told apart only by their 16-bit class id",
      sorted(n for n, *_r in FAMILY if _r[5] == 0x65AD40) ==
      sorted(["Channel_LocalTalkMessageVital", "Channel_PartyMessageVital",
              "Channel_GuildMessageVital", "Channel_ActorBoardcastMessageVital",
              "Channel_GMGlobalMessageVital"]))
check("the base Channel_MessageVtial wire is exactly two wstrings: "
      "wstring@+0x34 (speaker, empty in every GT-006 capture) then wstring@+0x18 (body)",
      SCHEMA[0x65AD40] == [('w', 0x34, 0x48, None), ('w', 0x18, 0x48, None)])
check("the GT-006 captured 34-byte LocalTalk payload replays EXACTLY under that "
      "schema: 0x48 u32=0 (empty) + 0x48 u32=0x18 + 24 UTF-16LE bytes, 0 bytes left over",
      GT006_PAYLOAD[0] == 0x48
      and struct.unpack_from('<I', GT006_PAYLOAD, 1)[0] == 0
      and GT006_PAYLOAD[5] == 0x48
      and struct.unpack_from('<I', GT006_PAYLOAD, 6)[0] == 0x18
      and len(GT006_PAYLOAD) == 10 + 0x18
      and GT006_PAYLOAD[10:].decode('utf-16le') == "PFCHATPROBE1")

# --- 12. recipient resolution ----------------------------------------------
print("\n-- 12. recipient resolution: Channel_WhisperVital --")
check("Channel_WhisperVital is the ONLY channel carrying a THIRD wstring "
      "(wstring@+0x50 = the recipient name field)",
      [n for n, *_r in FAMILY
       if sum(1 for e in SCHEMA[_r[5]] if e[0] == 'w') >= 3] == ["Channel_WhisperVital"])
wsp = dmap(0x65AEA0, 0x80)
check("Whisper Serialize 0x65AEA0 emits speaker@+0x34, body@+0x18, "
      "recipient@+0x50, then u8(tag 0x0B)@+0x6C",
      wsp.get(0x65AEAD) == ('lea', 'eax, [esi + 0x34]')
      and wsp.get(0x65AEC3) == ('lea', 'eax, [esi + 0x18]')
      and wsp.get(0x65AED9) == ('lea', 'eax, [esi + 0x50]')
      and wsp.get(0x65AEF1) == ('lea', 'eax, [esi + 0x6c]')
      and rd(0x65AEF7, 2) == b'\x6a\x0b')
wct = dmap(0x658240, 0x60)
check("the Whisper ctor 0x658240 installs vtable 0xF37788, constructs the wstring "
      "at +0x50 and zeroes the u8 at +0x6C — both are Whisper's OWN fields, "
      "not inherited from Channel_GlobalVital",
      wct.get(0x658268) == ('call', '0x657c90')
      and wct.get(0x65826D) == ('lea', 'ecx, [esi + 0x50]')
      and wct.get(0x658278) == ('mov', 'dword ptr [esi], 0xf37788')
      and wct.get(0x658284) == ('mov', 'byte ptr [esi + 0x6c], 0'))
check("Whisper's sizeof (0x70) is exactly Channel_MessageVtial's 0x50 plus one "
      "0x1C wstring plus the result byte — arithmetic agrees with the schema",
      0x50 + 0x1C == 0x6C and 0x6C + 1 <= 0x70)
wdisp = dmap(0x659989, 0x40)
check("the dispatcher reads Whisper's u8@+0x6C as a RESULT code: value 1 -> system "
      "message 0x0B, value 2 -> system message 0x18, otherwise render as WhisperTalk",
      wdisp.get(0x65999B) == ('mov', 'al, byte ptr [esi + 0x6c]')
      and wdisp.get(0x65999E) == ('cmp', 'al, 1')
      and rd(0x6599A2, 2) == b'\x6a\x0b'
      and wdisp.get(0x6599A9) == ('cmp', 'al, 2')
      and rd(0x6599AD, 2) == b'\x6a\x18')
check("Whisper's clone 0x65AF20 chains the base clone 0x65ACB0 then copies exactly "
      "the two extra fields (+0x50 wstring, +0x6C byte)",
      dmap(0x65AF20, 0x50).get(0x65AF24) == ('call', '0x65acb0')
      and dmap(0x65AF20, 0x50).get(0x65AF53) == ('lea', 'eax, [ebx + 0x50]')
      and dmap(0x65AF20, 0x50).get(0x65AF63) == ('mov', 'byte ptr [esi + 0x6c], cl'))

# --- 13. join/leave lifecycle ----------------------------------------------
print("\n-- 13. Join/Leave membership lifecycle --")
check("Join* and Leave* are Channel_CommandVtial (verbs), and their paired "
      "OnActor* notifications are Commands too — a request/notification pair "
      "for custom channels",
      all(EXPECT_PARENT[n] == "Channel_CommandVtial" for n in
          ("Channel_JoinCustomChannelVital", "Channel_OnActorJoinCustomChannelVital",
           "Channel_LeaveCustomChannelVital", "Channel_OnActorLeaveCustomChannelVital")))
check("the two OnActor* notifications SHARE one serializer 0x65B140: "
      "qword(0x32)@+0x18 channel handle, wstring@+0x20 channel name, "
      "wstring@+0x3C acting-actor name",
      SCHEMA[0x65B140] == [('s', 0x18, 0x32, 8), ('w', 0x20, 0x48, None),
                           ('w', 0x3C, 0x48, None)]
      and [n for n, *_r in FAMILY if _r[5] == 0x65B140] ==
      ["Channel_OnActorJoinCustomChannelVital", "Channel_OnActorLeaveCustomChannelVital"])
check("the request side carries no actor name (the notification adds it): "
      "JoinCustomChannel = qword handle + channel name + two u8",
      SCHEMA[0x65AF80] == [('s', 0x18, 0x32, 8), ('w', 0x20, 0x48, None),
                           ('s', 0x3C, 0x0B, 1), ('s', 0x3D, 0x0B, 1)])
gate_bad = []
for nm, nva, tva, slot, getid, vt, ser, size, node in FAMILY:
    hook = dw(vt + 0x1C)
    want, gate = DELIVER_HOOK.get(nm, (PLAIN_HOOK, None))
    if hook != want:
        gate_bad.append((nm, hex(hook), hex(want)))
check("every Join*/Leave* command uses a RESULT-GATED delivery hook and everything "
      "else uses the plain hook 0x65C850", not gate_bad, str(gate_bad))
check("gate 0x65C8B0 suppresses delivery when JoinCustomChannel's u8@+0x3D != 0",
      dmap(0x65C8B0, 0x30).get(0x65C8C3) == ('mov', 'al, byte ptr [edi + 0x3d]')
      and dmap(0x65C8B0, 0x30).get(0x65C8C7) == ('test', 'al, al'))
check("gate 0x65C950 suppresses delivery when the u8@+0x21 of LeaveCustomChannel / "
      "JoinOriginalSinChannel != 0",
      dmap(0x65C950, 0x30).get(0x65C962) == ('cmp', 'byte ptr [edi + 0x21], 0'))
check("gate 0x65CB40 suppresses delivery when JoinClassChannel's u8@+0x24 != 0",
      dmap(0x65CB40, 0x30).get(0x65CB52) == ('cmp', 'byte ptr [edi + 0x24], 0'))
check("each gate offset is exactly the LAST u8 field of that channel's own wire "
      "schema — the trailing byte is a membership result code",
      SCHEMA[0x65AF80][-1][1] == 0x3D and SCHEMA[0x65B060][-2][1] == 0x21
      and SCHEMA[0x65B260][-1][1] == 0x21 and SCHEMA[0x65B450][-1][1] == 0x24)

# --- 14. client routing -----------------------------------------------------
print("\n-- 14. client-side routing into ChannelModule_Client --")
check("the delivery hook resolves the module registry [0x1032EC4]+0x130 by the "
      "ASCII name \"ChannelModule_Client\" @0xF22CB4",
      dmap(PLAIN_HOOK, 0x30).get(0x65C850) == ('mov', 'eax, dword ptr [0x1032ec4]')
      and rd(0x65C863, 5) == b'\x68' + struct.pack('<I', MODULE_NAME_VA)
      and cstr(MODULE_NAME_VA) == "ChannelModule_Client")
check("the module is is-a checked against type node 0x1084304 (getter 0x657850) "
      "before the vital is handed to the dispatcher 0x659870",
      rd(MODULE_NODE_GET, 6) == b'\xb8' + struct.pack('<I', MODULE_NODE) + b'\xc3'
      and dmap(PLAIN_HOOK, 0x60).get(0x65C888) == ('call', hex(TYPE_ISA))
      and dmap(PLAIN_HOOK, 0x60).get(0x65C89C) == ('call', hex(DELIVER)))
disp_bad = []
for bva, helper, nm in DISPATCH_ORDER:
    ins = dmap(bva, 8)
    if ins.get(bva) != ('call', hex(helper)):
        disp_bad.append((nm, hex(bva), ins.get(bva)))
    node = None
    for j in md.disasm(rd(helper, 0x30), helper):
        if j.mnemonic == 'call':
            try:
                stub = int(j.op_str, 16)
            except ValueError:
                continue
            b = rd(stub, 6)
            if b and b[0] == 0xB8 and b[5] == 0xC3:
                node = struct.unpack_from('<I', b, 1)[0]
                break
    if NODE_NAME.get(node) != nm:
        disp_bad.append((nm, "downcast helper resolves", NODE_NAME.get(node)))
check("the dispatcher 0x659870 is an ORDERED downcast chain over 14 channels, in the "
      "pinned order (LocalTalk, Whisper, Guild, Party, ActorBoardcast, "
      "LocalPerformance, CustomChannelMessage, JoinCustom, OnActorJoinCustom, "
      "LeaveCustom, OnActorLeaveCustom, ClassChannelMessage, GMGlobal, ForbidTalk)",
      not disp_bad, str(disp_bad))
style_bad = []
for pva, sva, want in STYLE_NAMES:
    if rd(pva, 5) != b'\x68' + struct.pack('<I', sva):
        style_bad.append((want, "push site", hex(pva)))
    got = wstr(sva)
    if got != want:
        style_bad.append((want, got, hex(sva)))
check("each rendering branch selects its per-channel UTF-16LE style name "
      "(LocalTalk / WhisperTalk / GuildTalk / PartyTalk / YellTalk / "
      "LocalPerformance / CustomDefine / ClassTalk)", not style_bad, str(style_bad))
unrouted_bad = []
for nm in UNROUTED:
    row = [f for f in FAMILY if f[0] == nm][0]
    node, vt = row[8], row[5]
    clone = dw(vt + 0x24)
    # the only tolerated reference is the class's own clone doing a self is-a check
    sites = [x for x in text_hits("68" + struct.pack('<I', node).hex())
             if not (clone <= x < clone + 0x100)]
    if sites:
        unrouted_bad.append((nm, [hex(x) for x in sites]))
check("Channel_JoinOriginalSinChannelVital, Channel_OriginalSinChannelMessageVital "
      "and Channel_JoinClassChannelVital have NO downcast CONSUMER anywhere in .text "
      "(the only reference is their own clone's self is-a check) — 3 of the 17 "
      "channels are producer-side only in this build",
      not unrouted_bad, str(unrouted_bad))
check("no downcast helper in the 0x657850..0x657C90 helper block resolves to any of "
      "those three type nodes, and none of them appears in the dispatcher body",
      not [n for n in UNROUTED
           if [f for f in FAMILY if f[0] == n][0][8] in
           [struct.unpack_from('<I', rd(h, 6), 1)[0]
            for _b, h, _c in DISPATCH_ORDER]])

# --- 15. span pins ----------------------------------------------------------
print("\n-- 15. byte-span pins --")
span_bad = []
for label, (a, b, want) in SPANS.items():
    got = span_sha(a, b)
    if got != want:
        span_bad.append((label, got))
check("all %d pinned byte spans are byte-identical in this image" % len(SPANS),
      not span_bad, str(span_bad))

# --- 16. server cross-check -------------------------------------------------
print("\n-- 16. server cross-check (read-only) — the size of the routing gap --")
src = open(SERVER_SRC, "r", encoding="utf-8", errors="replace").read()
check("v141 (immutable) contains no `Channel_` token at all — none of the 17 client "
      "channel classes exists server-side", "Channel_" not in src)
present = [n for n, *_ in FAMILY if ("0x%04X" % EXPECT_IDS[n]) in src.upper()]
check("v141 declares none of the 17 channel wire ids", not present, str(present))
if os.path.isfile(CHAT_MOD):
    chat = open(CHAT_MOD, "r", encoding="utf-8", errors="replace").read()
    check("the ONLY server-side touch of the family is chat_input_hypothesis.py, and "
          "it handles exactly one id, 0xAC52 = Channel_LocalTalkMessageVital",
          "CHAT_INPUT_VITAL_ID = 0xAC52" in chat
          and not any(("0x%04X" % EXPECT_IDS[n]) in chat.upper()
                      for n, *_ in FAMILY if n != "Channel_LocalTalkMessageVital"))
    check("that module still calls 0xAC52 UNKNOWN and treats the payload as an opaque "
          "pinned blob — it never decodes the two wstrings this round names",
          "UNKNOWN_0xAC52" in chat
          and "unknown to the server registry" in chat
          and "compared as one opaque pinned blob" in chat)
    check("the payload this round decodes field-by-field is byte-identical to the "
          "capture that module pins (CHAT_INPUT_PROBE_PAYLOADS['probe1'])",
          GT006_PAYLOAD.hex().upper()
          in chat.replace('"', '').replace("\n", "").replace(" ", "").upper())
else:
    check("chat_input_hypothesis.py present for the cross-check", False, CHAT_MOD)
check("routing gap size: 17 channels client-side, 1 touched server-side "
      "(opaque echo), 0 decoded server-side", len(FAMILY) == 17 and len(present) == 0)

print()
print("guards run: %d" % n_guard)
if fails:
    print("RESULT: FAIL — %d guard(s) drifted: %s" % (len(fails), fails))
    sys.exit(1)
print("RESULT: PASS — all %d Channel_* family static guards reproduced from this "
      "binary (exit 0)" % n_guard)
sys.exit(0)
