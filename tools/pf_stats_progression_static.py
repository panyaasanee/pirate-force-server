#!/usr/bin/env python3
"""PF STATS-PROG-001 - static byte-exact reconstruction of the client's character
STATS AND PROGRESSION surface: the Attr class chain that carries level /
experience / primary attributes / allocation points / HP-MP, the five
progression vitals that mutate them, and the per-field wire schema of each -
opening `character_management/stats_and_progression` from not_started ->
in_progress.

The coverage note for that lane said:

    "The proven projection carries name and cash only. No level, experience,
     attribute point, or progression rule is modeled, persisted, or captured."

This milestone settles the *identifier* half and the *field* half statically,
byte-exact, from the read-only client binary. It does NOT capture anything.

  * COHORT. 14 classes register through the same PF-NAMEID-HASH-001 once-init
    thunk shape proven for the Channel_* / ItemOperate / TargetPos cohorts
    (push <name literal>; call 0x89C080; mov ecx,eax; call 0x89BD00;
     mov word [id-slot], ax; ret).  Re-using the hash at 0x89B220
        u16 id = SUM_i (int16)((signed char)name[i] * (i+1))  mod 2^16
    reproduces ActorAttr 0x12AD, NPCAttr 0x0AD5 and UpdateAttrVital 0x309A -
    three ids v141 already carries as committed constants - which validates the
    remaining eleven derived ids.

  * HIERARCHY (type-node registrar 0x88F2E0, `.?AV...@@` descriptors):
        Attribute                       (no wire fields)
          |- DBAttribute                (u8 mask +0x20, qword identity +0x18)
          |    |- BasicAttr             (u16 mask +0x70, 12 gated fields)
          |    |    |- ActorAttr        (u64 mask +0x1B4/+0x1B8, 43 gated fields)
          |    |    \- NPCAttr
          |    |- AvatarAttr            (u32 mask +0x28, 21 gated fields)
          |    \- CSkillAttr
          \- FightAttr                  (no wire fields)

  * WHAT EACH PROGRESSION FIELD IS - every naming below is tied to an in-image
    consumer, never to genre convention:
        BasicAttr  u16 +0x5E  bit 0x0002  LEVEL      (script binding "GetLv",
                   handler 0x460050: movzx ecx, word [player_attr+0x5E])
        BasicAttr  u32 +0x44  bit 0x0004  HP current   } HUD updater 0x53F1AD
        BasicAttr  u32 +0x48  bit 0x0008  HP max       } feeds PROGRESSBAR_HP
        BasicAttr  u32 +0x4C  bit 0x0010  MP current   } and PROGRESSBAR_MP
        BasicAttr  u32 +0x50  bit 0x0020  MP max       } widget slots
        ActorAttr  u32 +0x8C  bit 0x00000001 CLASS   (binding "GetClass" 0x460160)
        ActorAttr  u32 +0x7C  bit 0x00000008 SKILL POINTS
                   (skill window 0x75C613 pushes it into NUMBERLABEL_SPNOW)
        ActorAttr  u16 +0x80  bit 0x00000010 UNSPENT ALLOCATION POINTS
                   (spinner cap 0x57DD7A, +/- button gate 0x53B1FB)
        ActorAttr  u16 +0x82/84/86/88/8A  bits 0x20/40/80/100/200
                   STR / CON / DEX / INT / PER base values
        ActorAttr  u16 +0x182/184/186/188/18A bits 0x40000..0x400000
                   the matching STR / CON / DEX / INT / PER bonus values
                   (the five paired getters 0x467A60/AF0/B80/CA0/C10 each add
                    base + bonus, and Char_Info pushes them into LABEL_STR..PER)
        ActorAttr  qword +0xA0 bit 0x00000400 EXPERIENCE
                   (exp bar 0x519299 reads word[+0x5E], looks up
                    STANDARD_STATUS[level+1].n_EXP_CURRENTLV, then divides the
                    qword at +0xA0/+0xA4 by it to get the percentage)
        ActorAttr  qword +0xA8 bit 0x00000800 CASH  (already proven upstream;
                   re-asserted here only as a cross-check anchor)

  * PROGRESSION VERBS.
        AbilityDepoly     0x260B  u8 +0x14 (tag 0x08), u8 +0x15 (tag 0x08),
                                  i16 +0x16 (tag 0x0F)
        AbilityDepolyAll  0x36AD  five i16 (tag 0x0F) at +0x14/16/18/1A/1C, in
                                  the order STR, CON, DEX, INT, PER - proven by
                                  the producer 0x57F733 lifting the five pending
                                  deltas the BUTTON_STRUP..BUTTON_PERUP click
                                  handler 0x57C1F4 wrote
        CLearnSkillVital  0x36AA  u32 +0x14 (tag 0x14), u8 +0x18 (tag 0x0B)
        CRevertSkilltVital 0x45F0 u32 +0x14 (tag 0x14), qword +0x18 (tag 0x32)
        CLearnSkillResultVital 0x673C nested list at +0x14 then u8 +0x2C
        UpdateAttrVital   0x309A  the Attr-collection delta transport

  * NEGATIVE RESULTS THAT COST REAL SCAN TIME (all reproduced as guards):
      - The script bindings AddExp / AddAbilityPoint / AddSkillPoint exist, but
        their client handlers 0x460EC0 / 0x4612A0 / 0x4613D0 only broadcast a
        LOCAL event carrying the ASCII token "exp" / "ap" / "sp". They build no
        vital and touch no Attr field. The client cannot grant progression.
      - AbilityDepoly has exactly one UI producer, 0x57F83B, and it always sends
        the constructor defaults with only +0x15 forced to 6 - a single fixed
        (1, 6, 1) triple. Every real point allocation goes through
        AbilityDepolyAll.
      - Attribute (0x1306) and FightAttr (0x1285) both point their serializer
        slot at 0x515EC0, which is the single instruction `ret 8`. They carry
        ZERO wire fields in this build.
      - The per-level numbers themselves (STANDARD_STATUS.n_EXP_CURRENTLV,
        STANDARD_STATUS.n_POINT_ABILITY, POTENTIAL.n_STRENGH...) live in the
        external static-data tables, NOT in the executable. Only the column
        names and the lookup code are in-image.

  * SERVER GAP. v141 (immutable, read-only here) declares none of the 14 ids as
    a literal, emits exactly one of the 43 ActorAttr fields (cash, mask bit
    0x800) and six of the 13 BasicAttr fields (name / HP pair / speed / scene
    pair). Zero of the twelve named progression fields and zero of the five
    progression verbs have any server-side encoder or dispatch.

NOT CLAIMED: nothing about the ORIGINAL server. No runtime capture, no wire
observation, no persistence claim. This is the client's *expectation* of the
protocol, byte-exact, and nothing else. The lane goes not_started -> in_progress
and never runtime_pass here.

Report-only / additive: NO server-source change, NO scenario, NO ledger entry.
Sole binary evidence = the read-only client GameClient/GameClient.local.bin,
cross-checked against read-only server source.

Usage:  py -3 tools/pf_stats_progression_static.py [path-to-GameClient.local.bin]
Exit 0 = all static guards reproduced; nonzero = a guard drifted.
"""
import hashlib
import os
import re
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
        os.path.join(_ROOT, "packages", ".v134_staging_20260815_0355",
                     "GameClient.local.bin"),
    ):
        if os.path.isfile(cand):
            return cand
    return "GameClient/GameClient.local.bin"


BIN = sys.argv[1] if len(sys.argv) > 1 else _default_bin()
EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
SERVER_SRC = os.path.normpath(os.path.join(_ROOT, "current", "pf_login_game_server_v141.py"))
SRC_DIR = os.path.normpath(os.path.join(_ROOT, "src"))

# The deliberate exceptions to this tool's "no progression verb name anywhere
# under src/" negative -- one owning module per lane, docstring mentions only:
#   * LEARN-SKILL-RESULT-001 (HYP-PF-033, 2026-08-23) built the outbound
#     encoder for CLearnSkillResultVital 0x673C, whose body shape GT-050
#     closed byte-exactly; its module names that class once in its docstring
#     title and names CLearnSkillVital once, in the docstring NONCLAIM about
#     the inbound direction.
#   * LEARN-SKILL-REQUEST-001 (HYP-PF-034, 2026-08-24) built the inbound
#     strict DECODER for CLearnSkillVital 0x36AA (decode-count-and-record
#     only: no reply, no learn rule, no write) from the committed delivery
#     tables GT-050 re-verified; its module names that class once, in its
#     docstring title.
# The triples below are (file, verb, exact occurrence count), counted with a
# trailing identifier-boundary lookahead so a mention inside a longer class
# name is never miscounted; ANY new occurrence of either verb in those files,
# and any occurrence of any verb in any other file, trips the guard again.
# tests/test_stats_progression_static.py test 24 re-reads this constant with
# ast.literal_eval and pins its own scan to the SAME triples, so the tool and
# the cloud-runnable test cannot drift apart silently.
LEARN_SKILL_RESULT_SRC_EXCEPTIONS = (
    ("learn_skill_result_hypothesis.py", "CLearnSkillVital", 1),
    ("learn_skill_result_hypothesis.py", "CLearnSkillResultVital", 1),
    ("learn_skill_request_hypothesis.py", "CLearnSkillVital", 1),
    # SKILL-ATTR-001 (HYP-PF-035, 2026-08-24): the attr-block lane's owning
    # module names its class twice, both in the docstring (title sentence
    # and the "not a standalone vital" pin sentence).  The class sits in
    # this census list because STATS-PROG-001 counted it alongside the five
    # verbs, not because it is a verb.
    ("skill_attr_hypothesis.py", "CSkillAttr", 2),
)

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


def off2va(off):
    for _nm, _va, _vs, _rp, _rs in secs:
        if _rp <= off < _rp + _rs:
            return image_base + _va + (off - _rp)
    return None


def rd(va, n):
    o = va2off(va)
    return data[o:o + n] if o is not None else b""


def dw(va):
    return struct.unpack('<I', rd(va, 4))[0]


def cstr(va, maxn=160):
    b = rd(va, maxn)
    z = b.find(b'\x00')
    return b[:z].decode('latin1') if z >= 0 else None


def wstr(va, maxn=200):
    """UTF-16LE literal at `va`; terminator search is 2-byte aligned."""
    b = rd(va, maxn)
    z = len(b)
    for i in range(0, len(b) - 1, 2):
        if b[i] == 0 and b[i + 1] == 0:
            z = i
            break
    return b[:z].decode('utf-16le', 'replace')


def span_sha(a, b):
    return hashlib.sha256(rd(a, b - a)).hexdigest().upper()


TEXT = [s for s in secs if s[0] == '.text'][0]
_, TVADDR, TVSIZE, TRAW, _ = TEXT
TSTART = image_base + TVADDR
RDATA = [s for s in secs if s[0] == '.rdata'][0]
_, RVADDR, _RVS, RRAW, RRSIZE = RDATA
RSTART = image_base + RVADDR
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


def rdata_hits(val):
    res, s, hi = [], RRAW, RRAW + RRSIZE
    pat = struct.pack('<I', val)
    while True:
        j = data.find(pat, s, hi)
        if j < 0:
            break
        res.append(RSTART + (j - RRAW))
        s = j + 1
    return res


def call_targets(lo, hi, targets):
    """Every `call rel32` / `jmp rel32` in [lo,hi) whose target is in `targets`."""
    out = []
    o1, o2 = va2off(lo), va2off(hi)
    j = o1
    while True:
        j = data.find(b'\xe8', j, o2)
        if j < 0:
            break
        rel = struct.unpack_from('<i', data, j + 1)[0]
        src = off2va(j)
        if src is not None and src + 5 + rel in targets:
            out.append((src, src + 5 + rel))
        j += 1
    return sorted(out)


def callers_of(target):
    """Every .text `call rel32` site that reaches `target`."""
    out, j = [], TRAW
    while True:
        j = data.find(b'\xe8', j, TRAW + TVSIZE)
        if j < 0:
            break
        rel = struct.unpack_from('<i', data, j + 1)[0]
        src = TSTART + (j - TRAW)
        if src + 5 + rel == target:
            out.append(src)
        j += 1
    return out


def dword_immediate_hits(val):
    """Every .text VA holding dword `val` that is NOT a rel32 tail.

    Cohort precedent (MOVE-PROJECT-001 / CHAT-CHANNEL-001): exclude E8/E9 rel32
    tails AND the two-byte `0F 8x` (jcc rel32) tails. Both exclusions are
    byte-mechanical; nothing else is filtered here, so genuine coincidences
    still show up and are pinned explicitly below.
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
    """16-bit immediate encodings of `val` (mov/cmp/test ax|cx|dx, imm16)."""
    out = []
    for pfx in (b'\x66\xb8', b'\x66\xb9', b'\x66\xba',
                b'\x66\x3d', b'\x66\x81\xf8', b'\x66\xa9'):
        out += text_hits(pfx + struct.pack('<H', val))
    return out


# ---------------------------------------------------------------- NAMEID-HASH-001
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
ID_ASSIGN = 0x89BD00     # thiscall id-assign(name) -> ax (calls the hash 0x89B220)
HASH_FN = 0x89B220
TYPE_REG = 0x88F2E0      # type-node registrar (this=node, args parent, descriptor)
SCAL_W, SCAL_R = 0x89A600, 0x89A640   # stdcall(tag, ptr, width) ret 0xC
WSTR_W, WSTR_R = 0x89A810, 0x89A880   # tag 0x48 + u32 byte-length + UTF-16LE
BLOB_W, BLOB_R = 0x89A6D0, 0x89A700   # tag 0x44 opaque byte block
WRITE_CODECS = {SCAL_W: 's', WSTR_W: 'w', BLOB_W: 'b'}
READ_CODECS = {SCAL_R, WSTR_R, BLOB_R}
NOOP_SER = 0x515EC0      # `ret 8` - the empty serializer slot
WIDGET_LOOKUP = 0xAA1750  # thiscall FindChild(name) -> widget*
PLAYER_ATTR = 0x1032EC4  # module registry root; +0x348 = the local player's Attr

# name, name-literal VA, thunk VA, id-slot, get-id stub, vtable, sizeof,
# type node, serializer vtable slot, serializer VA
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
    "Attribute": 0x1306,
    "DBAttribute": 0x1B36,
    "BasicAttr": 0x1244,
    "ActorAttr": 0x12AD,           # <-- v141 ACTOR_ATTR anchor
    "NPCAttr": 0x0AD5,             # <-- v141 NPC_ATTR anchor
    "AvatarAttr": 0x16A0,
    "FightAttr": 0x1285,
    "CSkillAttr": 0x1661,
    "UpdateAttrVital": 0x309A,     # <-- v141 UPDATE_ATTR_VITAL anchor
    "AbilityDepoly": 0x260B,
    "AbilityDepolyAll": 0x36AD,
    "CLearnSkillVital": 0x36AA,
    "CLearnSkillResultVital": 0x673C,
    "CRevertSkilltVital": 0x45F0,
}
# the three ids v141 already carries as committed constants; they anchor the hash
V141_ANCHORS = {"ActorAttr": 0x12AD, "NPCAttr": 0x0AD5, "UpdateAttrVital": 0x309A}

# the only two ids whose 4-byte pattern occurs in .text at all; both are proven
# byte coincidences below (disp32 field offsets / a modrm+imm straddle)
ID_BYTE_COINCIDENCES = {
    0x16A0: {   # `movss/mov reg,[esi+0x16A0]` - a +0x16A0 struct displacement
        0xA995FE: (0xA995FA, "f30f108ea0160000"),
        0xA99D52: (0xA99D4E, "f30f1186a0160000"),
        0xA99E58: (0xA99E54, "f30f1181a0160000"),
        0xA99E70: (0xA99E6E, "8991a0160000"),
        0xA99E8C: (0xA99E8A, "8b89a0160000"),
    },
    0x1306: {   # `c7 06 13 00 00 00` = mov dword [esi],0x13 - modrm+imm straddle
        0xB69A78: (0xB69A77, "c70613000000"),
    },
}

EXPECT_PARENT = {
    "Attribute": None,             # parented on the engine-wide object root
    "DBAttribute": "Attribute",
    "BasicAttr": "DBAttribute",
    "ActorAttr": "BasicAttr",
    "NPCAttr": "BasicAttr",
    "AvatarAttr": "DBAttribute",
    "FightAttr": "Attribute",
    "CSkillAttr": "DBAttribute",
    "UpdateAttrVital": "*vital-base*",
    "AbilityDepoly": "*vital-base*",
    "AbilityDepolyAll": "*vital-base*",
    "CLearnSkillVital": "*vital-base*",
    "CLearnSkillResultVital": "*vital-base*",
    "CRevertSkilltVital": "*vital-base*",
}
VITAL_BASE_NODE = 0x10823A8
NODE_OF = {c[7]: c[0] for c in COHORT}

# serializer decode bounds: [start, first-read-codec-call) - the save branch
SER_BOUNDS = {
    "DBAttribute": (0x467790, 0x4677C9),
    "BasicAttr": (0x4656F0, 0x465850),
    "ActorAttr": (0x466230, 0x466767),
    "NPCAttr": (0x466EB0, 0x467010),
    "AvatarAttr": (0x464560, 0x46476E),
    "CSkillAttr": (0x7520B0, 0x752290),
    "AbilityDepoly": (0x5E5BB0, 0x5E5BF1),
    "AbilityDepolyAll": (0x5E5C80, 0x5E5CDF),
    "CLearnSkillVital": (0x755AC0, 0x755AF2),
    "CRevertSkilltVital": (0x755B70, 0x755BA2),
    "CLearnSkillResultVital": (0x756100, 0x756130),
}

# decoded write-path schema: ordered [(kind, base register, displacement, tag, width)]
# kind 's' = scalar codec, 'w' = wstring codec (tag 0x48), 'b' = blob codec (tag 0x44)
SCHEMA = {
    "DBAttribute": [
        ('s', 'esi', 0x20, 0x0B, 1), ('s', 'esi', 0x18, 0x32, 8)],
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
        # NOTE: CSkillAttr stages every value through a stack temp before the
        # codec call, so these displacements are ESP/EBX-relative, NOT object
        # offsets. Object offsets for this class are deliberately NOT claimed.
        ('s', 'esp', 0x44, 0x12, 2), ('s', 'esp', 0x40, 0x12, 2),
        ('s', 'ebx', 0x10, 0x12, 2), ('s', 'ebx', 0x14, 0x14, 4)],
    "AbilityDepoly": [
        ('s', 'esi', 0x14, 0x08, 1), ('s', 'esi', 0x15, 0x08, 1),
        ('s', 'esi', 0x16, 0x0F, 2)],
    "AbilityDepolyAll": [
        ('s', 'esi', 0x14, 0x0F, 2), ('s', 'esi', 0x16, 0x0F, 2),
        ('s', 'esi', 0x18, 0x0F, 2), ('s', 'esi', 0x1A, 0x0F, 2),
        ('s', 'esi', 0x1C, 0x0F, 2)],
    "CLearnSkillVital": [
        ('s', 'esi', 0x14, 0x14, 4), ('s', 'esi', 0x18, 0x0B, 1)],
    "CRevertSkilltVital": [
        ('s', 'esi', 0x14, 0x14, 4), ('s', 'esi', 0x18, 0x32, 8)],
    "CLearnSkillResultVital": [
        ('s', 'esi', 0x2C, 0x0B, 1)],
}

# tag -> byte width, as emitted by the scalar codec throughout this cohort
TAG_WIDTH = {0x05: 1, 0x08: 1, 0x0B: 1, 0x0F: 2, 0x12: 2, 0x14: 4,
             0x19: 4, 0x26: 4, 0x2A: 4, 0x32: 8}

# the named progression fields: (owner, offset, mask bit, tag, meaning)
NAMED_FIELDS = [
    ("BasicAttr", 0x5E,  0x0002,      0x12, "level"),
    ("BasicAttr", 0x44,  0x0004,      0x14, "hp current"),
    ("BasicAttr", 0x48,  0x0008,      0x14, "hp max"),
    ("BasicAttr", 0x4C,  0x0010,      0x14, "mp current"),
    ("BasicAttr", 0x50,  0x0020,      0x14, "mp max"),
    ("ActorAttr", 0x8C,  0x00000001,  0x19, "class"),
    ("ActorAttr", 0x7C,  0x00000008,  0x19, "skill points"),
    ("ActorAttr", 0x80,  0x00000010,  0x12, "unspent allocation points"),
    ("ActorAttr", 0x82,  0x00000020,  0x12, "STR base"),
    ("ActorAttr", 0x84,  0x00000040,  0x12, "CON base"),
    ("ActorAttr", 0x86,  0x00000080,  0x12, "DEX base"),
    ("ActorAttr", 0x88,  0x00000100,  0x12, "INT base"),
    ("ActorAttr", 0x8A,  0x00000200,  0x12, "PER base"),
    ("ActorAttr", 0xA0,  0x00000400,  0x32, "experience"),
    ("ActorAttr", 0x182, 0x00040000,  0x12, "STR bonus"),
    ("ActorAttr", 0x184, 0x00080000,  0x12, "CON bonus"),
    ("ActorAttr", 0x186, 0x00100000,  0x12, "DEX bonus"),
    ("ActorAttr", 0x188, 0x00200000,  0x12, "INT bonus"),
    ("ActorAttr", 0x18A, 0x00400000,  0x12, "PER bonus"),
]
# the mask-bit gate of every named field, as an exact instruction pin
GATE_PIN = {
    # BasicAttr gates the u16 mask it loaded into ebx from +0x70
    (0x4656F0, 0x5E):  (0x465736, "f60302"),                     # test byte [ebx],2
    (0x4656F0, 0x44):  (0x46574A, "f60304"),
    (0x4656F0, 0x48):  (0x46575E, "f60308"),
    (0x4656F0, 0x4C):  (0x465772, "f60310"),
    (0x4656F0, 0x50):  (0x465786, "f60320"),
    # ActorAttr gates the low half of its 64-bit mask in place at +0x1B4
    (0x466230, 0x8C):  (0x466299, "a801"),                       # test al,1
    (0x466230, 0x7C):  (0x4662EC, "f686b401000008"),
    (0x466230, 0x80):  (0x466304, "f686b401000010"),
    (0x466230, 0x82):  (0x46631F, "f686b401000020"),
    (0x466230, 0x84):  (0x46633A, "f686b401000040"),
    (0x466230, 0x86):  (0x466355, "f686b401000080"),
    (0x466230, 0x88):  (0x466370, "859eb4010000"),               # test dword[..],ebx (=0x100)
    (0x466230, 0x8A):  (0x46638A, "f786b401000000020000"),
    (0x466230, 0xA0):  (0x4663A8, "f786b401000000040000"),
    (0x466230, 0xA8):  (0x4663C6, "f786b401000000080000"),
    (0x466230, 0x182): (0x466490, "f786b401000000000400"),
    (0x466230, 0x184): (0x4664AE, "f786b401000000000800"),
    (0x466230, 0x186): (0x4664CC, "f786b401000000001000"),
    (0x466230, 0x188): (0x4664EA, "f786b401000000002000"),
    (0x466230, 0x18A): (0x466508, "f786b401000000004000"),
}
# the one gate that is not an inline immediate: ebx is loaded with 0x100 first
GATE_EBX_100 = (0x46628C, "bb00010000")

# ------------------------------------------------------------ semantic anchors
# (label, VA, exact bytes) - each is one consumer that names one field
ANCHORS = {
    # script binding registration: push common-thunk; push "GetLv"; ...; handler 0x460050
    "GetLv_registration":  (0x461ADE, "68e00a4600685ce6f0008d4c242cc74424245000460089742428"),
    # handler body: [[0x1032EC4]+0x348] -> movzx ecx, word [attr+0x5E]
    "GetLv_reads_0x5E":    (0x460050, "a1c42e030183ec0885c074248b80480300000fb7485e"),
    "GetClass_reads_0x8C": (0x46016C, "8b80480300008b888c000000"),
    "GetCash_reads_0xA8":  (0x4600AC, "8b80480300008b88a8000000"),
    # exp bar: level -> STANDARD_STATUS[level+1].n_EXP_CURRENTLV
    "exp_open_table":      (0x519260, "68ac52f100b9d0cd0801"),
    "exp_level_lookup":    (0x519299, "8b0dc42e03018b89480300000fb7495e0fb7d16a0068004cf1004252"),
    "exp_reads_0xA0":      (0x5192C6, "a1c42e03018b80480300008b88a00000008b80a4000000"),
    "exp_percentage":      (0x519314, "8b86800000006bc06499f7ff"),
    # HUD: HP pair then MP pair, straight out of BasicAttr
    "hud_attr_load":       (0x53F1AD, "8bb848030000"),
    "hud_hp_pair":         (0x53F1D3, "8b4744518b4f4852"),
    "hud_mp_pair":         (0x53F1E4, "8b6e248b5f4c8b47508b4e20"),
    # skill window: ActorAttr+0x7C -> NUMBERLABEL_SPNOW
    "skillpoint_read":     (0x75C613, "8b88480300008b497c398ea0000000"),
    "skillpoint_to_label": (0x75C624, "8b466c898ea0000000898820020000"),
    # the five paired base/bonus attribute getters
    "getter_STR":          (0x467A90, "0fb788820100000fb7b082000000"),
    "getter_CON":          (0x467B20, "0fb788840100000fb7b084000000"),
    "getter_DEX":          (0x467BB0, "0fb788860100000fb7b086000000"),
    "getter_INT":          (0x467CD0, "0fb788880100000fb7b088000000"),
    "getter_PER":          (0x467C40, "0fb7888a0100000fb7b08a000000"),
    # allocation-point pool: spinner cap and +/- button gate
    "point_pool_spinner":  (0x57DD6F, "a1c42e03018b88480300000fb79180000000"),
    "point_pool_gate":     (0x53B1DF, "a1c42e030185c0746d8b4e4453578bb848030000"),
    # AbilityDepolyAll producer: five pending deltas -> five i16 wire fields
    "depolyall_producer":  (0x57F733, "0fb78fc8010000668948140fb797cc010000668950160fb78f"
                                      "d0010000668948180fb797d40100006689501a0fb78fd8"),
    # the only AbilityDepoly producer forces +0x15 = 6 and ships ctor defaults
    "depoly_producer":     (0x57F83B, "e870e7ffff50c6401506"),
    "depoly_ctor":         (0x5E5B60, "8bc133c9884804894808c7006c6df80089480c884810884811"
                                      "884815b901000000c7009803f300c640140166894816c3"),
    "depolyall_ctor":      (0x5E5C20, "8bc133c933d2c7006c6df80088480489480889480c884810884811"
                                      "c700bc03f3006689481466895016668948186689501a6689481cc3"),
    # ActorAttr stages its 64-bit dirty mask from +0x1B4/+0x1B8 onto the stack
    "actorattr_mask64":    (0x466252, "8b8eb80100008b86b40100008d54241452"),
    # the three script bindings that only broadcast a local token
    "AddExp_token":        (0x460F44, "68cce1f0008d4c2458c68424a400000001c744242808000000"),
    "AddAbilityPoint_tok": (0x461324, "68d8e1f0008d4c2458c68424a400000001c744242808000000"),
    "AddSkillPoint_token": (0x461454, "68dce1f0008d4c2458c68424a400000001c744242808000000"),
}

SCRIPT_BINDINGS = {           # name literal VA -> (registration site, handler)
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
EVENT_BROADCAST = 0x5F9C70    # registry+0x130 listener fan-out

# static-data column names the progression code looks up (UTF-16LE literals)
TABLE_LITERALS = {
    0xF152AC: "STANDARD_STATUS",
    0xF14C00: "n_EXP_CURRENTLV",
    0xF14BE0: "n_POINT_ABILITY",
    0xF14F24: "n_HPMAX",
    0xF14EEC: "n_STAMINAMAX",
    0xF14B94: "POTENTIAL",
    0xF14B84: "n_LEVEL",
    0xF14B70: "n_STRENGH",          # sic - the binary spells it without the T
    0xF14B50: "n_CONSTITUTION",
    0xF14B3C: "n_AGILITY",
    0xF14B24: "n_INTELLECT",
    0xF14B08: "n_PERCEPTION",
}
POTENTIAL_BINDS = [0x4A449D, 0x4A44C5, 0x4A44E5, 0x4A4502, 0x4A4522, 0x4A4542]

# Char_Info2 widget binder: (range, expected name -> slot after the shift)
CHARINFO_BINDER = (0x583F00, 0x5856A0)
CHARINFO_EXPECT = {
    "LABEL_STR": 0x84, "LABEL_CON": 0x88, "LABEL_DEX": 0x8C,
    "LABEL_INT": 0x90, "LABEL_PER": 0x94,
    "LABEL_DEPLOY_STR": 0x98, "LABEL_DEPLOY_CON": 0x9C,
    "LABEL_DEPLOY_DEX": 0xA0, "LABEL_DEPLOY_INT": 0xA4,
    "LABEL_DEPLOY_PER": 0xA8,
    "BUTTON_STRUP": 0xD4, "BUTTON_CONUP": 0xD8, "BUTTON_DEXUP": 0xDC,
    "BUTTON_INTUP": 0xE0, "BUTTON_PERUP": 0xE4,
}
HUD_BINDER = (0x53EC00, 0x53EED0)
HUD_EXPECT = {"PROGRESSBAR_HP": 0x18, "NUMBERLABEL_HP": 0x1C,
              "PROGRESSBAR_MP": 0x20, "NUMBERLABEL_MP": 0x24}
SKILL_BINDER = (0x759C40, 0x759D40)
SKILL_EXPECT = {"NUMBERLABEL_SPNOW": 0x6C}

# Char_Info2 stat-row updater: (call site, getter, panel label slot, meaning)
CHARINFO_UPDATE = [
    (0x57E6C8, 0x467A60, 0x84, "STR"),
    (0x57E6EB, 0x467AF0, 0x88, "CON"),
    (0x57E70E, 0x467B80, 0x8C, "DEX"),
    (0x57E731, 0x467CA0, 0x90, "INT"),
    (0x57E754, 0x467C10, 0x94, "PER"),
]
# Char_Info2 "+" click handler: (button slot, pending-delta slot, deploy label slot)
CHARINFO_CLICK = [
    (0xD4, 0x1C8, 0x98, "STR"),
    (0xD8, 0x1CC, 0x9C, "CON"),
    (0xDC, 0x1D0, 0xA0, "DEX"),
    (0xE0, 0x1D4, 0xA4, "INT"),
    (0xE4, 0x1D8, 0xA8, "PER"),
]
# AbilityDepolyAll producer: (pending-delta slot, wire offset)
DEPOLYALL_ORDER = [(0x1C8, 0x14), (0x1CC, 0x16), (0x1D0, 0x18),
                   (0x1D4, 0x1A), (0x1D8, 0x1C)]

DEPOLY_POOL = 0x57DFB0        # AbilityDepoly allocator
DEPOLYALL_POOL = 0x57E0C0     # AbilityDepolyAll allocator
DEPOLY_CTOR = 0x5E5B60
DEPOLYALL_CTOR = 0x5E5C20
UI_SEND = 0x5DD800            # the client's outbound vital submit

# (start, end, sha256) byte-span pins
SPANS = {
    "attr_reg_thunk_block": (0xBD92D0, 0xBD9420, "5EC8A6B24E0270F4F8D6DFE0BBFBC495A7BBAEC52B85DBBA0116B141F1107BB5"),
    "ser_dbattribute":      (0x467790, 0x4677E8, "379F37AD0307E785FB4A230FC9F1871F69587E6A314DA5930A3A4ED289E55608"),
    "ser_basicattr":        (0x4656F0, 0x465986, None),
    "ser_actorattr":        (0x466230, 0x466C79, None),
    "ser_avatarattr":       (0x464560, 0x464952, None),
    "ser_abilitydepoly":    (0x5E5BB0, 0x5E5C1F, None),
    "ser_abilitydepolyall": (0x5E5C80, 0x5E5D2D, None),
    "ser_clearnskill":      (0x755AC0, 0x755B13, None),
    "ser_crevertskillt":    (0x755B70, 0x755BC3, None),
    "attr_getters_5":       (0x467A60, 0x467D20, "C51979231C11E4B429FAD6A4F7FB82F5449631D2E32405B384E0D85E1B48445B"),
    "charinfo_stat_update": (0x57E6BD, 0x57E76C, "1749236BA50F7342887C1DBA4A83F02DF903F1EEC0755777FA99AD99DDAAD769"),
    "charinfo_up_click":    (0x57C1F4, 0x57C3C3, "5103834A5D8D55BC6B5A9E17FA4FB904EA0820184E8E891A7712D36BE4179871"),
    "depolyall_producer":   (0x57F6F0, 0x57F77C, "EA5EF630FAD0933C3B624C2148B04AE57E859D7B44596789C8D4021D088088A5"),
    "hud_hp_mp_update":     (0x53F1AD, 0x53F23B, "DD5619C1EA3202FA8EC0124353C0DC5B603794CAF25131D0CB8A76F56B1170EF"),
    "exp_bar_percent":      (0x519299, 0x519320, "94E4F036505B2A2EF8DEA018EEFFC8483E433B6A2ADBDA9FEA016927AE26230A"),
    "getlv_handler":        (0x460050, 0x46009B, "154F508F3D61C2C3E507E5A8C5A993A5541499745A78F74C9436B45A0F97AC25"),
    "skillpoint_display":   (0x75C600, 0x75C63A, "060FD7165692D72D46007F1A2DDB37EB9771628582E78CAC9432DA761B3FF532"),
}
# The `None` spans above are function-extent records used by the schema decoder;
# their bytes are already covered field-by-field by SCHEMA and GATE_PIN, so they
# carry no separate hash. Only the entries with an explicit hash are span-pinned.


# ---------------------------------------------------------------- guard plumbing
fails = []
n_guard = 0


def check(name, cond, detail=""):
    global n_guard
    n_guard += 1
    print(("[OK]   " if cond else "[FAIL] ") + name + ("  " + detail if detail else ""))
    if not cond:
        fails.append(name)


def bytes_at(va, hexstr):
    want = bytes.fromhex(hexstr)
    return rd(va, len(want)) == want


# --------------------------------------------------- serializer write-path decode
def _window(csite, back):
    ins = []
    for i in md.disasm(rd(csite - back, back + 8), csite - back):
        if i.address >= csite:
            return ins if (i.address == csite and i.mnemonic == 'call') else None
        ins.append(i)
    return None


def _field_at(csite, kind):
    """Re-synchronised decode of the instruction window ending at the codec call.

    A plain linear sweep of these serializers desynchronises on the inline jump
    padding; anchoring the decode on the (known) call address and growing the
    window backwards until the stream lands exactly on it is deterministic.
    """
    for back in range(6, 0x30):
        ins = _window(csite, back)
        if ins is None:
            continue
        off = None
        for i in ins:
            if i.mnemonic == 'lea' and '[' in i.op_str:
                inner = i.op_str.split('[', 1)[1].rstrip(']')
                if ' + ' in inner:
                    b, d = inner.split(' + ')
                    if not d.startswith('e'):
                        off = (b, int(d, 16))
                else:
                    off = (inner, 0)
            elif i.mnemonic == 'add' and i.op_str.split(',')[0] in ('esi', 'edi', 'ecx', 'ebx'):
                try:
                    off = (i.op_str.split(',')[0], int(i.op_str.split(',')[1].strip(), 16))
                except ValueError:
                    pass
        if off is None:
            continue
        if kind != 's':
            return off, None, None
        seq = []
        for i in ins:
            if i.mnemonic == 'push':
                try:
                    seq.append(('i', int(i.op_str, 16)))
                except ValueError:
                    seq.append(('r', None))
        # emitted shape is: push <width> ; lea reg,[..] ; push reg ; push <tag>
        if len(seq) >= 3 and seq[-1][0] == 'i' and seq[-2][0] == 'r' and seq[-3][0] == 'i':
            return off, seq[-1][1], seq[-3][1]
    return None, None, None


def decode_serializer(lo, hi):
    out = []
    for src, tgt in call_targets(lo, hi, set(WRITE_CODECS) | READ_CODECS):
        if tgt in READ_CODECS:
            break
        kind = WRITE_CODECS[tgt]
        off, tag, wid = _field_at(src, kind)
        if kind == 'w':
            tag, wid = 0x48, None
        elif kind == 'b':
            tag, wid = 0x44, None
        out.append((kind, off[0] if off else None, off[1] if off else None, tag, wid))
    return out


def parse_widget_binder(lo, hi):
    """Recover `widget name -> cached slot` from a UI binder block.

    The compiler emits, per widget:
        push <name literal> ; mov ecx,esi ; mov [esi+K], eax ; call 0xAA1750
    so the store at each site holds the PREVIOUS name's lookup result. This
    one-instruction shift is the whole reason a naive scan mis-labels every
    slot by one; it is applied (and separately asserted) here.
    """
    out, pend, prev = {}, None, None
    for i in md.disasm(rd(lo, hi - lo), lo):
        if i.mnemonic == 'push':
            try:
                v = int(i.op_str, 16)
            except ValueError:
                continue
            if RSTART <= v < image_base + 0x101A000:
                s = wstr(v)
                if s and s.isprintable() and len(s) > 1:
                    prev, pend = pend, (s, v)
        elif (i.mnemonic == 'mov' and i.op_str.startswith('dword ptr [esi + 0x')
              and i.op_str.endswith(', eax')):
            if prev:
                out[prev[0]] = int(i.op_str.split('[esi + ')[1].split(']')[0], 16)
            prev = None
    return out


print("PF STATS-PROG-001 static verifier - character stats & progression family")
print("binary:", BIN)
print("SHA-256:", sha)
print()

check("binary SHA-256 matches the pinned client", sha == EXPECT_SHA, sha)
check("ImageBase == 0x400000", image_base == 0x400000, hex(image_base))

# --- 1. name literals + registration thunks ---------------------------------
print("\n-- 1. in-image plaintext class names and their registration thunks --")
bad = [n for n, va, *_ in COHORT if cstr(va) != n]
check("all 14 cohort class-name literals sit at their pinned .rdata VAs",
      not bad, str(bad))
check("the binary really spells it 'AbilityDepoly' (not 'Deploy') and "
      "'CRevertSkilltVital' (not 'SkillVital') - the hash uses the typos verbatim",
      cstr(0xF30918) == "AbilityDepoly" and cstr(0xF48F14) == "CRevertSkilltVital")
ok_thunk = 0
for nm, nva, tva, slot, getid, vt, size, node, serslot, ser in COHORT:
    b = rd(tva, 24)
    shape = (len(b) == 24 and b[0] == 0x68 and b[5] == 0xE8
             and b[10:12] == b'\x8b\xc8' and b[12] == 0xE8
             and b[17:19] == b'\x66\xa3' and b[23] == 0xC3)
    lit = cstr(struct.unpack_from('<I', b, 1)[0]) if shape else None
    once = tva + 10 + struct.unpack_from('<i', b, 6)[0] if shape else 0
    assign = tva + 17 + struct.unpack_from('<i', b, 13)[0] if shape else 0
    slot_in = struct.unpack_from('<I', b, 19)[0] if shape else 0
    good = (shape and lit == nm and once == ONCE_INIT
            and assign == ID_ASSIGN and slot_in == slot)
    ok_thunk += good
    if not good:
        check("thunk 0x%06X registers %s -> slot 0x%X" % (tva, nm, slot), False,
              "lit=%r once=%s assign=%s slot=%s"
              % (lit, hex(once), hex(assign), hex(slot_in)))
check("all 14 registration thunks have the exact NAMEID-HASH-001 shape "
      "(push name; call 0x89C080; mov ecx,eax; call 0x89BD00; mov word[slot],ax; ret)",
      ok_thunk == 14, "%d/14" % ok_thunk)
check("the eight Attr classes register from ONE contiguous block "
      "0xBD92D0..0xBD9420 that opens the whole attribute registry",
      span_sha(*SPANS["attr_reg_thunk_block"][:2]) == SPANS["attr_reg_thunk_block"][2],
      span_sha(*SPANS["attr_reg_thunk_block"][:2]))
check("id-assign 0x89BD00 calls the hash 0x89B220 (NAMEID-HASH-001 chain intact)",
      any(i == ('call', hex(HASH_FN)) for i in dmap(ID_ASSIGN, 64).values()))
check("hash 0x89B220 still has the signed-char position-weighted MAC loop",
      b'\x66\x0f\xbe\x3c\x31' in rd(HASH_FN, 96)
      and b'\x66\x0f\xaf\xfb' in rd(HASH_FN, 96)
      and b'\x66\x03\xd7' in rd(HASH_FN, 96))

# --- 2. the anchors ----------------------------------------------------------
print("\n-- 2. anchors: does NAMEID-HASH-001 hold for THIS cohort? --")
anchor_bad = {n: hex(name_id(n)) for n, v in V141_ANCHORS.items() if name_id(n) != v}
check("ANCHOR the hash reproduces the three cohort ids v141 already carries as "
      "committed constants: ActorAttr 0x12AD, NPCAttr 0x0AD5, UpdateAttrVital 0x309A",
      not anchor_bad, str(anchor_bad))
if anchor_bad:
    print("\nANCHOR FAILED - the hash does not apply to this cohort; stopping.")
    sys.exit(1)

# --- 3. the id table ---------------------------------------------------------
print("\n-- 3. derived wire id per class (from the in-image literal only) --")
derived = {n: name_id(n) for n, *_ in COHORT}
check("all 14 derived ids match the pinned table", derived == EXPECT_IDS,
      str({k: hex(v) for k, v in derived.items() if EXPECT_IDS.get(k) != v}))
check("all 14 cohort ids are pairwise distinct", len(set(derived.values())) == 14,
      str(len(set(derived.values()))))
for nm, *_ in COHORT:
    print("        0x%04X  %s" % (derived[nm], nm))

# --- 4. runtime-assigned wall ------------------------------------------------
print("\n-- 4. the ids are never code immediates (runtime-assigned wall) --")
imm_bad = {}
coincidence = {}
for nm, *_ in COHORT:
    v = derived[nm]
    hits = dword_immediate_hits(v)
    if imm16_hits(v):
        imm_bad[nm] = [hex(x) for x in imm16_hits(v)]
    if hits:
        coincidence[v] = sorted(hits)
check("not one of the 14 ids appears anywhere in .text as a 16-bit immediate "
      "(mov/cmp/test ax|cx|dx, imm16) - nothing compares against them statically",
      not imm_bad, str(imm_bad))
clean = [n for n, *_ in COHORT if derived[n] not in coincidence]
check("12 of the 14 ids have NO .text dword occurrence at all "
      "(scan excludes E8/E9 and 0F 8x rel32 tails)", len(clean) == 12,
      "%d clean, coincidences on %s"
      % (len(clean), [hex(v) for v in coincidence]))
coin_bad = []
for v, hits in coincidence.items():
    want = ID_BYTE_COINCIDENCES.get(v, {})
    if sorted(want) != hits:
        coin_bad.append((hex(v), [hex(h) for h in hits]))
        continue
    for h, (host, hexb) in want.items():
        if not bytes_at(host, hexb):
            coin_bad.append((hex(v), "host drift at " + hex(host)))
check("the only two ids with a .text dword occurrence (AvatarAttr 0x16A0 x5, "
      "Attribute 0x1306 x1) are byte coincidences, not immediates: five are the "
      "disp32 of `[esi+0x16A0]` field accesses and one is the modrm+imm straddle "
      "of `mov dword [esi],0x13` - each host instruction pinned byte-exact",
      not coin_bad, str(coin_bad))

# --- 5. id slots -------------------------------------------------------------
print("\n-- 5. id-slot has exactly one writer and one reader per class --")
w_bad, r_bad, stub_bad = [], [], []
for nm, nva, tva, slot, getid, vt, size, node, serslot, ser in COHORT:
    w = text_hits("66a3" + struct.pack('<I', slot).hex())
    r = text_hits("66a1" + struct.pack('<I', slot).hex())
    if w != [tva + 17]:
        w_bad.append((nm, [hex(x) for x in w]))
    if r != [getid]:
        r_bad.append((nm, [hex(x) for x in r]))
    if rd(getid, 7) != b'\x66\xa1' + struct.pack('<I', slot) + b'\xc3':
        stub_bad.append(nm)
check("every id-slot is written by exactly one site - its own registration thunk",
      not w_bad, str(w_bad))
check("every id-slot is read by exactly one get-id stub", not r_bad, str(r_bad))
check("every get-id stub is exactly `mov ax,[id-slot]; ret` (7 bytes)",
      not stub_bad, str(stub_bad))

# --- 6. vtables --------------------------------------------------------------
print("\n-- 6. vtable per class: cohort const, get-id, sizeof, serializer --")
vt_getid, vt_const, vt_size, vt_ser, vt_uniq = [], [], [], [], []
for nm, nva, tva, slot, getid, vt, size, node, serslot, ser in COHORT:
    if dw(vt + 0x10) != getid:
        vt_getid.append(nm)
    if dw(vt + 0x08) != 0x401B20:
        vt_const.append(nm)
    if size is not None:
        szf = dw(vt + 0x0C)
        b = rd(szf, 6)
        if not (b[0] == 0xB8 and struct.unpack_from('<I', b, 1)[0] == size and b[5] == 0xC3):
            vt_size.append(nm)
    if dw(vt + serslot) != ser:
        vt_ser.append((nm, hex(dw(vt + serslot)), hex(ser)))
    if rdata_hits(getid) != [vt + 0x10]:
        vt_uniq.append((nm, [hex(x) for x in rdata_hits(getid)]))
check("vtable +0x10 == the class's get-id stub for all 14", not vt_getid, str(vt_getid))
check("vtable +0x08 == 0x401B20 for all 14 (the same shared framework const as the "
      "TargetPosVital / Channel_* / ItemOperate cohorts)", not vt_const, str(vt_const))
check("vtable +0x0C is a `mov eax,<sizeof>; ret` stub matching the decoded field "
      "layout for the 13 classes that declare one", not vt_size, str(vt_size))
check("each get-id stub is referenced from exactly one .rdata slot - so each class "
      "has exactly one vtable and the cohort table is complete",
      not vt_uniq, str(vt_uniq))
check("the serializer slot is +0x34 for the eight Attr classes and +0x18 for the "
      "six Vital classes, and every slot holds the pinned serializer",
      not vt_ser, str(vt_ser))
check("Attribute (0x1306) and FightAttr (0x1285) BOTH point their serializer slot "
      "at 0x515EC0, which is the single instruction `ret 8` - they carry ZERO wire "
      "fields in this build (negative result, not an omission)",
      dw(0xF0E850 + 0x34) == NOOP_SER and dw(0xF0E8E0 + 0x34) == NOOP_SER
      and rd(NOOP_SER, 3) == b'\xc2\x08\x00')

# --- 7. hierarchy ------------------------------------------------------------
print("\n-- 7. class hierarchy from the type-node registrar 0x88F2E0 --")


def reg_site(node):
    pat = b'\xb9' + struct.pack('<I', node) + b'\xe8'
    k = TRAW
    while True:
        k = data.find(pat, k, TRAW + TVSIZE)
        if k < 0:
            return None
        rel = struct.unpack_from('<i', data, k + 6)[0]
        src = TSTART + (k + 5 - TRAW)
        if src + 5 + rel == TYPE_REG:
            return src
        k += 1


def parse_node(node):
    site = reg_site(node)
    if site is None:
        return None
    o = va2off(site)
    if data[o - 10] == 0x68:                       # push <parent node>
        parent = struct.unpack_from('<I', data, o - 9)[0]
    elif data[o - 6] == 0x50 and data[o - 11] == 0xE8:   # call <getter>; push eax
        rel = struct.unpack_from('<i', data, o - 10)[0]
        getter = off2va(o - 11) + 5 + rel
        b = rd(getter, 6)
        parent = struct.unpack_from('<I', b, 1)[0] if (b[0] == 0xB8 and b[5] == 0xC3) else None
    else:
        parent = None
    rec = None
    for back in range(12, 40):
        if data[o - back] == 0xB9 and data[o - back + 5:o - back + 7] == b'\xff\x15':
            rec = struct.unpack_from('<I', data, o - back + 1)[0]
            break
    return site, parent, (cstr(rec + 8, 160) if rec else None)


hier_bad, desc_bad = [], []
for nm, nva, tva, slot, getid, vt, size, node, serslot, ser in COHORT:
    parsed = parse_node(node)
    if parsed is None:
        hier_bad.append((nm, "no registration"))
        continue
    site, parent, desc = parsed
    want = EXPECT_PARENT[nm]
    if want == "*vital-base*":
        got = "*vital-base*" if parent == VITAL_BASE_NODE else hex(parent or 0)
    else:
        got = NODE_OF.get(parent) if (parent and parent in NODE_OF) else None
    if got != want:
        hier_bad.append((nm, got, want))
    if desc != ".?AV%s@@" % nm:
        desc_bad.append((nm, desc))
check("every cohort class registers a type node whose `.?AV...@@` descriptor "
      "equals its registration-thunk literal - two independent name paths converge",
      not desc_bad, str(desc_bad))
check("the parent edge reproduces Attribute -> DBAttribute -> BasicAttr -> "
      "{ActorAttr, NPCAttr}, plus AvatarAttr and CSkillAttr hanging off "
      "DBAttribute and FightAttr off Attribute",
      not hier_bad, str(hier_bad))
check("all six progression vitals share ONE parent node 0x10823A8 (the vital base) "
      "- they are peers of TargetPosVital / Channel_* / ItemOperate, not Attrs",
      all(parse_node(c[7])[1] == VITAL_BASE_NODE
          for c in COHORT if EXPECT_PARENT[c[0]] == "*vital-base*"))
check("ActorAttr's serializer chains BasicAttr's (0x466243 calls 0x4656F0) and "
      "BasicAttr's chains DBAttribute's (0x4656FF calls 0x467790) - the wire layout "
      "is the class chain, base first",
      dmap(0x466243, 8).get(0x466243) == ('call', '0x4656f0')
      and dmap(0x4656FF, 8).get(0x4656FF) == ('call', '0x467790'))
check("AvatarAttr's serializer chains DBAttribute directly (0x46456F -> 0x467790), "
      "skipping BasicAttr - it is a sibling branch, not a character block",
      dmap(0x46456F, 8).get(0x46456F) == ('call', '0x467790'))

# --- 8. codecs ---------------------------------------------------------------
print("\n-- 8. the codecs the cohort serializers use --")
check("scalar write codec 0x89A600 is stdcall(tag, ptr, width) ret 0xC "
      "(the MOVE-PROJECT-001 / CHAT-CHANNEL-001 field codec)",
      rd(0x89A63D, 3) == b'\xc2\x0c\x00')
check("scalar read codec 0x89A640 is its counterpart, so one routine both encodes "
      "and decodes every Attr", dmap(0x89A640, 0x60).get(0x89A640) == ('sub', 'esp, 0x48'))
check("wstring write codec 0x89A810 emits tag 0x48 + u32 byte-length + UTF-16LE",
      rd(0x89A833, 2) == b'\x6a\x48' and rd(0x89A872, 3) == b'\xc2\x04\x00')
check("the third codec 0x89A6D0 used by ActorAttr@+0x148 and AvatarAttr@+0x64 is "
      "an opaque tag-0x44 byte block, NOT a scalar - its contents are not claimed",
      rd(0x89A6F1, 2) == b'\x6a\x44')

# --- 9. wire schemas ---------------------------------------------------------
print("\n-- 9. per-class wire schema, decoded field by field from each serializer --")
sch_bad = []
for nm, (lo, hi) in SER_BOUNDS.items():
    got = decode_serializer(lo, hi)
    if got != SCHEMA[nm]:
        sch_bad.append((nm, got, SCHEMA[nm]))
check("all 11 field-emitting serializers decode to their pinned field lists "
      "(kind, base register, displacement, tag, width)", not sch_bad,
      str([b[0] for b in sch_bad]))
width_bad = [(nm, e) for nm, sc in SCHEMA.items() for e in sc
             if e[0] == 's' and TAG_WIDTH.get(e[3]) != e[4]]
check("every scalar tag maps to one byte width across the whole cohort "
      "(0x05/0x08/0x0B=1, 0x0F/0x12=2, 0x14/0x19/0x26/0x2A=4, 0x32=8)",
      not width_bad, str(width_bad))
check("DBAttribute is the shared header of every Attr: u8 mask (tag 0x0B) at +0x20 "
      "then, when bit 0 is set, the qword identity (tag 0x32) at +0x18",
      SCHEMA["DBAttribute"] == [('s', 'esi', 0x20, 0x0B, 1), ('s', 'esi', 0x18, 0x32, 8)]
      and bytes_at(0x4677AF, "f60701"))
check("BasicAttr leads with a u16 dirty mask (tag 0x12) at +0x70 and gates 12 fields "
      "off it", SCHEMA["BasicAttr"][0] == ('s', 'esi', 0x70, 0x12, 2)
      and len(SCHEMA["BasicAttr"]) == 13)
check("ActorAttr stages a 64-bit dirty mask from +0x1B4/+0x1B8 onto the stack and "
      "emits it as ONE qword (tag 0x32), then a u8 extra-group flag (tag 0x05) at "
      "+0x1BC, then 43 gated fields",
      bytes_at(*ANCHORS["actorattr_mask64"])
      and SCHEMA["ActorAttr"][0] == ('s', 'esp', 0x14, 0x32, 8)
      and SCHEMA["ActorAttr"][1] == ('s', 'esi', 0x1BC, 0x05, 1)
      and len(SCHEMA["ActorAttr"]) == 45)
check("AvatarAttr leads with a u32 dirty mask (tag 0x26) at +0x28 and gates 21 "
      "fields - v141's opaque AvatarAttr extractor sees exactly this shape",
      SCHEMA["AvatarAttr"][0] == ('s', 'esi', 0x28, 0x26, 4)
      and len(SCHEMA["AvatarAttr"]) == 22)
check("NPCAttr's decode reproduces the fields v141 already encodes by hand "
      "(u8 mask +0xBC, u16 template +0x78, wstring visual preset +0x7C)",
      SCHEMA["NPCAttr"][:4] == [('s', 'esi', 0xBC, 0x0B, 1), ('s', 'esi', 0x78, 0x12, 2),
                                ('s', 'esi', 0x7A, 0x0B, 1), ('w', 'esi', 0x7C, 0x48, None)])
check("CSkillAttr stages every emitted value through a stack temp, so its decoded "
      "displacements are ESP/EBX-relative - NO CSkillAttr object offset is claimed "
      "by this milestone",
      all(e[1] in ('esp', 'ebx') for e in SCHEMA["CSkillAttr"]))
present = {(o, off) for o, off, *_ in
           [(nm, e[2]) for nm, sc in SCHEMA.items() for e in sc]}
missing = [(o, hex(f)) for o, f, _b, _t, _m in NAMED_FIELDS
           if (o, f) not in present]
check("every one of the 19 named progression fields is actually present in its "
      "class's decoded schema", not missing, str(missing))
gate_bad = [(hex(k[0]), hex(k[1])) for k, v in GATE_PIN.items()
            if not bytes_at(v[0], v[1])]
check("every named progression field's dirty-mask gate is byte-exact at its pinned "
      "address (%d `test` instruction pins)" % len(GATE_PIN), not gate_bad, str(gate_bad))
check("the single non-immediate gate (ActorAttr +0x88, bit 0x100) is `test dword "
      "[esi+0x1B4], ebx` with ebx loaded as 0x100 at 0x46628C - so the +0x82..+0x8A "
      "run really is bits 0x20/0x40/0x80/0x100/0x200 with no hole",
      bytes_at(*GATE_EBX_100))

# --- 10. LEVEL ---------------------------------------------------------------
print("\n-- 10. LEVEL: BasicAttr u16 +0x5E, mask bit 0x0002 --")
check("the script-binding table registers the literal \"GetLv\" @0xF0E65C at "
      "0x461ADE with handler 0x460050",
      cstr(0xF0E65C) == "GetLv" and bytes_at(*ANCHORS["GetLv_registration"]))
check("handler 0x460050 resolves the LOCAL PLAYER Attr as [[0x1032EC4]+0x348] and "
      "reads `movzx ecx, word [attr+0x5E]` - the level field, named by the client "
      "itself and not by genre convention",
      bytes_at(*ANCHORS["GetLv_reads_0x5E"]))
check("BasicAttr's serializer emits exactly that u16 at +0x5E with tag 0x12 under "
      "mask bit 0x0002",
      ('s', 'esi', 0x5E, 0x12, 2) in SCHEMA["BasicAttr"]
      and bytes_at(0x465736, "f60302") and bytes_at(0x46573B, "6a028d4e5e516a12"))
check("three further independent consumers read the same word: the level gate at "
      "0x43290C, the exp-bar lookup at 0x5192A5 and the reset-cost gate at 0x57F81A",
      bytes_at(0x43290C, "0fb74a5e") and bytes_at(0x5192A5, "0fb7495e")
      and bytes_at(0x57F81A, "0fb7525e"))

# --- 11. HP / MP -------------------------------------------------------------
print("\n-- 11. HP and MP: BasicAttr u32 +0x44/+0x48 and +0x4C/+0x50 --")
hud = parse_widget_binder(*HUD_BINDER)
hud_bad = {k: (hex(hud.get(k, -1)), hex(v)) for k, v in HUD_EXPECT.items()
           if hud.get(k) != v}
check("the HUD binder caches PROGRESSBAR_HP/NUMBERLABEL_HP at +0x18/+0x1C and "
      "PROGRESSBAR_MP/NUMBERLABEL_MP at +0x20/+0x24",
      not hud_bad, str(hud_bad))
check("the binder shape is `push <name>; mov ecx,esi; mov [esi+K],eax; call 0xAA1750`, "
      "so each store holds the PREVIOUS name's result - the one-instruction shift "
      "this decode applies is itself byte-pinned",
      bytes_at(0x53ED28, "68b429f2008bce894614")
      and dmap(0x53ED32, 8).get(0x53ED32) == ('call', hex(WIDGET_LOOKUP)))
check("the bar updater loads the same player Attr and reads the HP pair +0x44/+0x48",
      bytes_at(*ANCHORS["hud_attr_load"]) and bytes_at(*ANCHORS["hud_hp_pair"]))
check("it then reads +0x4C/+0x50 and divides them into the PROGRESSBAR_MP widget "
      "cached at +0x20 (numerator +0x4C, denominator +0x50) - so +0x4C/+0x50 are "
      "current/max MP, the second resource bar",
      bytes_at(*ANCHORS["hud_mp_pair"])
      and dmap(0x53F1FC, 0x30).get(0x53F20C) == ('divsd', 'xmm0, xmm1'))
check("BasicAttr's schema carries both pairs as u32 tag 0x14 under mask bits "
      "0x0004/0x0008 (HP) and 0x0010/0x0020 (MP)",
      [e for e in SCHEMA["BasicAttr"] if e[2] in (0x44, 0x48, 0x4C, 0x50)]
      == [('s', 'esi', 0x44, 0x14, 4), ('s', 'esi', 0x48, 0x14, 4),
          ('s', 'esi', 0x4C, 0x14, 4), ('s', 'esi', 0x50, 0x14, 4)])
check("the client's static-data schema names the same two ceilings n_HPMAX and "
      "n_STAMINAMAX in the STANDARD_STATUS table - 'MP' here is the stamina pool",
      wstr(0xF14F24) == "n_HPMAX" and wstr(0xF14EEC) == "n_STAMINAMAX"
      and bytes_at(0x4A3C1C, "68244ff100") and bytes_at(0x4A3C59, "68ec4ef100"))

# --- 12. EXPERIENCE ----------------------------------------------------------
print("\n-- 12. EXPERIENCE: ActorAttr qword +0xA0, mask bit 0x400 --")
check("the exp bar opens the static table \"STANDARD_STATUS\" @0xF152AC",
      wstr(0xF152AC) == "STANDARD_STATUS" and bytes_at(*ANCHORS["exp_open_table"]))
check("it reads the player's level (word +0x5E), increments it, and looks up column "
      "\"n_EXP_CURRENTLV\" @0xF14C00 for level+1 - the next level's requirement",
      wstr(0xF14C00) == "n_EXP_CURRENTLV" and bytes_at(*ANCHORS["exp_level_lookup"]))
check("it then reads the 64-bit value at ActorAttr +0xA0/+0xA4 out of the same "
      "player Attr", bytes_at(*ANCHORS["exp_reads_0xA0"]))
check("and computes `value * 100 / requirement` - a progress percentage, which is "
      "what makes +0xA0 the CURRENT EXPERIENCE and not another currency",
      bytes_at(*ANCHORS["exp_percentage"]))
check("ActorAttr's schema carries +0xA0 as a qword (tag 0x32) under mask bit 0x400, "
      "immediately before the already-proven cash qword +0xA8 under bit 0x800",
      SCHEMA["ActorAttr"][12] == ('s', 'esi', 0xA0, 0x32, 8)
      and SCHEMA["ActorAttr"][13] == ('s', 'esi', 0xA8, 0x32, 8)
      and bytes_at(0x4663A8, "f786b401000000040000")
      and bytes_at(0x4663C6, "f786b401000000080000"))
check("CROSS-CHECK the neighbouring qword +0xA8 is the cash field the GetCash "
      "binding 0x4600A0 reads - the same anchor v141 already relies on, so the two "
      "qwords are told apart by their consumers, not by position",
      bytes_at(*ANCHORS["GetCash_reads_0xA8"]))

# --- 13. CLASS and SKILL POINTS ---------------------------------------------
print("\n-- 13. CLASS (+0x8C) and SKILL POINTS (+0x7C) --")
check("binding \"GetClass\" handler 0x460160 reads dword [player_attr+0x8C]",
      cstr(0xF0E530) == "GetClass" and bytes_at(*ANCHORS["GetClass_reads_0x8C"]))
check("ActorAttr emits +0x8C as u32 tag 0x19 under mask bit 0x00000001",
      SCHEMA["ActorAttr"][2] == ('s', 'esi', 0x8C, 0x19, 4)
      and bytes_at(0x466299, "a801"))
skl = parse_widget_binder(*SKILL_BINDER)
check("the skill window binds NUMBERLABEL_SPNOW to its slot +0x6C",
      skl.get("NUMBERLABEL_SPNOW") == SKILL_EXPECT["NUMBERLABEL_SPNOW"],
      hex(skl.get("NUMBERLABEL_SPNOW", -1)))
check("its refresh 0x75C613 reads dword [player_attr+0x7C] and writes it straight "
      "into that NUMBERLABEL_SPNOW widget - +0x7C is the SKILL POINT balance",
      bytes_at(*ANCHORS["skillpoint_read"]) and bytes_at(*ANCHORS["skillpoint_to_label"]))
check("ActorAttr emits +0x7C as u32 tag 0x19 under mask bit 0x00000008",
      SCHEMA["ActorAttr"][5] == ('s', 'esi', 0x7C, 0x19, 4)
      and bytes_at(0x4662EC, "f686b401000008"))

# --- 14. the five primary attributes ----------------------------------------
print("\n-- 14. the five primary attributes and their allocation-point pool --")
getter_bad = []
for lbl in ("STR", "CON", "DEX", "INT", "PER"):
    if not bytes_at(*ANCHORS["getter_" + lbl]):
        getter_bad.append(lbl)
check("five sibling getters each compute base + bonus from ONE aligned pair: "
      "+0x82/+0x182, +0x84/+0x184, +0x86/+0x186, +0x88/+0x188, +0x8A/+0x18A",
      not getter_bad, str(getter_bad))
ci = parse_widget_binder(*CHARINFO_BINDER)
ci_bad = {k: (hex(ci.get(k, -1)), hex(v)) for k, v in CHARINFO_EXPECT.items()
          if ci.get(k) != v}
check("the Char_Info2 binder caches LABEL_STR..LABEL_PER at +0x84..+0x94, "
      "LABEL_DEPLOY_STR..PER at +0x98..+0xA8 and BUTTON_STRUP..PERUP at +0xD4..+0xE4",
      not ci_bad, str(ci_bad))
upd_bad = []
for site, getter, slot, lbl in CHARINFO_UPDATE:
    ins = dmap(site, 8)
    if ins.get(site) != ('call', hex(getter)):
        upd_bad.append((lbl, "call", hex(site)))
    nxt = dmap(site + 5, 12)
    if not any(op == 'dword ptr [esi + 0x%x]' % slot
               for m, op in [(v[0], v[1].split(', ')[-1]) for v in nxt.values()]
               if m == 'mov'):
        upd_bad.append((lbl, "slot", hex(slot)))
check("the Char_Info2 stat rows bind getter -> label one-to-one: 0x467A60->LABEL_STR, "
      "0x467AF0->LABEL_CON, 0x467B80->LABEL_DEX, 0x467CA0->LABEL_INT, "
      "0x467C10->LABEL_PER - this is what names +0x82/84/86/88/8A STR/CON/DEX/INT/PER",
      not upd_bad, str(upd_bad))
check("the whole stat-row updater block is byte-identical to its pin",
      span_sha(*SPANS["charinfo_stat_update"][:2]) == SPANS["charinfo_stat_update"][2],
      span_sha(*SPANS["charinfo_stat_update"][:2]))
check("all five base values and all five bonus values are u16 tag 0x12 in "
      "ActorAttr, contiguous and in the same order in both runs",
      [e[2] for e in SCHEMA["ActorAttr"][7:12]] == [0x82, 0x84, 0x86, 0x88, 0x8A]
      and [e[2] for e in SCHEMA["ActorAttr"][20:25]] == [0x182, 0x184, 0x186, 0x188, 0x18A])
check("ActorAttr u16 +0x80 (mask bit 0x10) is NOT a sixth attribute: 0x57DD7A caps "
      "an allocation spinner with it and 0x53B1FB/0x53B215/0x53B237 only enable the "
      "+/- controls while it is > 0 - it is the UNSPENT ALLOCATION POINT pool",
      bytes_at(*ANCHORS["point_pool_spinner"]) and bytes_at(*ANCHORS["point_pool_gate"])
      and bytes_at(0x53B1FB, "0fb79f80000000")
      and bytes_at(0x53B215, "6683bf8000000000")
      and bytes_at(0x53B237, "6683bf8000000000"))
check("the client's static-data schema declares exactly five primary attributes for "
      "the POTENTIAL table - n_STRENGH (sic), n_CONSTITUTION, n_AGILITY, "
      "n_INTELLECT, n_PERCEPTION - matching the five base/bonus pairs one for one",
      [wstr(v) for v in (0xF14B70, 0xF14B50, 0xF14B3C, 0xF14B24, 0xF14B08)]
      == ["n_STRENGH", "n_CONSTITUTION", "n_AGILITY", "n_INTELLECT", "n_PERCEPTION"]
      and wstr(0xF14B94) == "POTENTIAL"
      and all(data.count(struct.pack('<I', va)) >= 1 for va in
              (0xF14B70, 0xF14B50, 0xF14B3C, 0xF14B24, 0xF14B08)))
check("STANDARD_STATUS also declares n_POINT_ABILITY (the per-level allocation-point "
      "grant) and n_EXP_CURRENTLV side by side - the two progression curves",
      wstr(0xF14BE0) == "n_POINT_ABILITY" and bytes_at(0x4A4123, "68e04bf100")
      and bytes_at(0x4A4103, "68004cf100"))

# --- 15. the allocation verbs ------------------------------------------------
print("\n-- 15. AbilityDepoly / AbilityDepolyAll: the allocation verbs --")
check("AbilityDepolyAll's wire is exactly five signed 16-bit deltas (tag 0x0F) at "
      "+0x14/+0x16/+0x18/+0x1A/+0x1C - nothing else",
      SCHEMA["AbilityDepolyAll"] ==
      [('s', 'esi', 0x14 + 2 * k, 0x0F, 2) for k in range(5)])
click_bad = []
click = dmap(0x57C1F4, 0x1E0)
for slot, delta, label, lbl in CHARINFO_CLICK:
    if not any(op == 'dword ptr [esi + 0x%x]' % slot for m, op in
               [(v[0], v[1].split(', ')[-1]) for v in click.values()] if m == 'mov'):
        click_bad.append((lbl, "button slot", hex(slot)))
check("the Char_Info2 click handler tests the clicked widget against the five UP "
      "buttons in slot order +0xD4/D8/DC/E0/E4 = STR/CON/DEX/INT/PER",
      not click_bad, str(click_bad))
check("each UP button increments its own pending-delta counter: STR->+0x1C8, "
      "CON->+0x1CC, DEX->+0x1D0, INT->+0x1D4, PER->+0x1D8, and refreshes the "
      "matching LABEL_DEPLOY_* widget",
      bytes_at(0x57C25E, "ff86c8010000") and bytes_at(0x57C2B1, "01becc010000")
      and bytes_at(0x57C2FF, "01bed0010000") and bytes_at(0x57C34D, "01bed4010000")
      and bytes_at(0x57C398, "01bed8010000")
      and span_sha(*SPANS["charinfo_up_click"][:2]) == SPANS["charinfo_up_click"][2])
check("the producer 0x57F6F0 copies those five counters into the five wire fields "
      "in the SAME order - so AbilityDepolyAll's wire order is STR, CON, DEX, INT, "
      "PER, proven end to end and not assumed",
      bytes_at(*ANCHORS["depolyall_producer"])
      and span_sha(*SPANS["depolyall_producer"][:2]) == SPANS["depolyall_producer"][2])
check("AbilityDepolyAll's ctor 0x5E5C20 zeroes all five deltas, so an unset field "
      "means 'allocate nothing to this attribute'",
      bytes_at(*ANCHORS["depolyall_ctor"]))
check("AbilityDepoly's ctor 0x5E5B60 installs vtable 0xF30398 and the defaults "
      "+0x14 = 1, +0x15 = 0, +0x16 = 1", bytes_at(*ANCHORS["depoly_ctor"]))
check("AbilityDepoly has exactly ONE UI producer, 0x57F83B, and it changes only "
      "+0x15 (to 6) before submitting - so the client only ever sends the single "
      "fixed triple (1, 6, 1) on this id",
      bytes_at(*ANCHORS["depoly_producer"])
      and sorted(callers_of(DEPOLY_POOL)) == [0x57F83B, 0x5EB07C]
      and sorted(callers_of(DEPOLYALL_POOL)) == [0x57F72A, 0x5EB09C])
check("that single AbilityDepoly send is gated on the player's level and on a "
      "COIN_CONSUME table row, i.e. it is the paid attribute-reset verb, not the "
      "per-point allocate verb",
      wstr(0xF29168) == "COIN_CONSUME" and bytes_at(0x57F7E7, "686891f200")
      and bytes_at(0x57F81A, "0fb7525e")
      and dmap(0x57F845, 8).get(0x57F845) == ('call', '0x4011a0'))
check("both producers hand the object to the same outbound submit 0x5DD800",
      dmap(0x57F772, 8).get(0x57F772) == ('call', hex(UI_SEND))
      and dmap(0x57F84C, 8).get(0x57F84C) == ('call', hex(UI_SEND)))

# --- 16. the skill verbs -----------------------------------------------------
print("\n-- 16. CLearnSkill / CRevertSkillt: the skill-point verbs --")
check("CLearnSkillVital 0x36AA is {u32 (tag 0x14) @+0x14, u8 (tag 0x0B) @+0x18}",
      SCHEMA["CLearnSkillVital"] == [('s', 'esi', 0x14, 0x14, 4),
                                     ('s', 'esi', 0x18, 0x0B, 1)])
check("CRevertSkilltVital 0x45F0 is {u32 (tag 0x14) @+0x14, qword (tag 0x32) @+0x18}",
      SCHEMA["CRevertSkilltVital"] == [('s', 'esi', 0x14, 0x14, 4),
                                       ('s', 'esi', 0x18, 0x32, 8)])
check("CLearnSkillResultVital 0x673C delegates its body to a nested list serializer "
      "at +0x14 and only emits one u8 (tag 0x0B) at +0x2C itself - the result byte",
      SCHEMA["CLearnSkillResultVital"] == [('s', 'esi', 0x2C, 0x0B, 1)]
      and dmap(0x756114, 8).get(0x756114) == ('call', '0x755d30'))
check("CSkillAttr 0x1661 hangs off DBAttribute and its serializer walks a container "
      "(one u16 count then per-entry u16/u32) - the learned-skill list",
      dmap(0x7520C3, 8).get(0x7520C3) == ('call', '0x467790')
      and SCHEMA["CSkillAttr"][0][3] == 0x12)

# --- 17. UpdateAttrVital -----------------------------------------------------
print("\n-- 17. UpdateAttrVital 0x309A: the Attr delta transport --")
check("UpdateAttrVital's serializer 0x5E42C0 only re-bases `this+0x14` and tail-jumps "
      "to the shared Attr-collection codec 0x463DE0 - it owns no fields of its own",
      bytes_at(0x5E42C0, "83c114807c240800")
      and dmap(0x5E42D2, 8).get(0x5E42D2) == ('jmp', '0x463de0')
      and dmap(0x5E42DF, 8).get(0x5E42DF) == ('jmp', '0x463de0'))
check("its vtable +0x1C inbound handler is 0x5F2400, the apply-each-Attr path v141 "
      "already documents", dw(0xF303E0 + 0x1C) == 0x5F2400)

# --- 18. the three script bindings that grant nothing ------------------------
print("\n-- 18. NEGATIVE: AddExp / AddAbilityPoint / AddSkillPoint grant nothing --")
bind_bad = []
for nm, (nva, site, handler) in SCRIPT_BINDINGS.items():
    if cstr(nva) != nm:
        bind_bad.append((nm, "literal", hex(nva)))
    b = rd(site, 10)
    if not (b[0] == 0x68 and struct.unpack_from('<I', b, 1)[0] == 0x460AE0
            and b[5] == 0x68 and struct.unpack_from('<I', b, 6)[0] == nva):
        bind_bad.append((nm, "registration", hex(site)))
check("all six progression-relevant script bindings register through the same "
      "common thunk 0x460AE0 with their plaintext names", not bind_bad, str(bind_bad))
tok_bad = []
for nm, (tva, tok) in LOCAL_EVENT_TOKENS.items():
    if cstr(tva) != tok:
        tok_bad.append((nm, cstr(tva), tok))
check("the ASCII tokens \"exp\" @0xF0E1CC, \"ap\" @0xF0E1D8 and \"sp\" @0xF0E1DC are "
      "in the image, adjacent, in the same literal run as \"money\" and \"additem\"",
      not tok_bad, str(tok_bad))
check("AddExp 0x460EC0, AddAbilityPoint 0x4612A0 and AddSkillPoint 0x4613D0 each "
      "push their token and call the LOCAL listener fan-out 0x5F9C70 through "
      "[0x1032EC4]+0x130",
      bytes_at(*ANCHORS["AddExp_token"]) and bytes_at(*ANCHORS["AddAbilityPoint_tok"])
      and bytes_at(*ANCHORS["AddSkillPoint_token"])
      and dmap(0x460F94, 8).get(0x460F94) == ('call', hex(EVENT_BROADCAST))
      and dmap(0x461374, 8).get(0x461374) == ('call', hex(EVENT_BROADCAST))
      and dmap(0x4614A4, 8).get(0x4614A4) == ('call', hex(EVENT_BROADCAST)))
check("0x5F9C70 is a pure listener fan-out (`call [vtable+0x40]` per subscriber) - "
      "it constructs no vital and calls no codec, so those three bindings CANNOT "
      "grant experience or points client-side",
      dmap(0x5F9CE7, 8).get(0x5F9CE7) == ('mov', 'eax, dword ptr [ecx]')
      and dmap(0x5F9CE9, 8).get(0x5F9CE9) == ('mov', 'edx, dword ptr [eax + 0x40]')
      and not call_targets(0x5F9C70, 0x5F9D08, set(WRITE_CODECS) | READ_CODECS))
check("no AbilityDepoly / AbilityDepolyAll / CLearnSkill* / CRevertSkillt* object is "
      "constructed anywhere inside those three handlers",
      not any(0x460EC0 <= c < 0x4614C0
              for ctor in (DEPOLY_CTOR, DEPOLYALL_CTOR)
              for c in callers_of(ctor)))

# --- 19. byte-span pins ------------------------------------------------------
print("\n-- 19. byte-span pins --")
span_bad = []
for label, (a, b, want) in SPANS.items():
    got = span_sha(a, b)
    if want is not None and got != want:
        span_bad.append((label, got))
pinned = [k for k, v in SPANS.items() if v[2] is not None]
check("all %d hash-pinned byte spans are byte-identical in this image" % len(pinned),
      not span_bad, str(span_bad))

# --- 20. server cross-check --------------------------------------------------
print("\n-- 20. server cross-check (read-only) - the size of the progression gap --")
src = open(SERVER_SRC, "r", encoding="utf-8", errors="replace").read()
srcU = src.upper()
id_present = [n for n, *_ in COHORT if ("0x%04X" % derived[n]) in srcU]
check("v141 declares NONE of the 14 cohort ids as a hex literal - not even the "
      "three it uses by name (they are spelled through its own constants)",
      not id_present, str(id_present))
verbs = ["AbilityDepoly", "AbilityDepolyAll", "CLearnSkillVital",
         "CLearnSkillResultVital", "CRevertSkilltVital", "CSkillAttr"]
check("v141 contains no token for any of the five progression verbs or CSkillAttr",
      not [v for v in verbs if v.upper() in srcU])
check("v141's only ActorAttr encoder emits a 64-bit mask of exactly 0x800 - one of "
      "the 43 ActorAttr fields (cash), and none of the 14 named ActorAttr "
      "progression fields",
      'struct.pack("<II", 0x800, 0)' in src)
check("v141's BasicAttr masks are 0x0001 | 0x0004 | 0x0008 | 0x0040 | 0x0100 | "
      "0x0200 - it never sets bit 0x0002 (level) nor 0x0010/0x0020 (MP)",
      "basic_mask = 0x0004 | 0x0008 | 0x0100 | 0x0200" in src
      and "basic_mask = 0x000C | 0x0100 | 0x0200" in src
      and "0x0002" not in src.replace("0x00020000", ""))
src_hits = []
if os.path.isdir(SRC_DIR):
    for root, _d, files in os.walk(SRC_DIR):
        if "__pycache__" in root:
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            t = open(os.path.join(root, f), "r", encoding="utf-8", errors="replace").read()
            for v in verbs:
                # Trailing identifier-boundary lookahead: "AbilityDepoly" must
                # not count "AbilityDepolyAll" occurrences, and a NEW mention
                # of an allowed verb must move the count and trip the guard.
                n = len(re.findall(re.escape(v) + r"(?![A-Za-z0-9_])", t))
                if n:
                    src_hits.append((f, v, n))
check("src/pirateforce_foundation/ contains no encoder, decoder or dispatch for any "
      "progression verb EXCEPT the two named lane exceptions (HYP-PF-033: the "
      "CLearnSkillResultVital outbound encoder module, whose docstring also "
      "names CLearnSkillVital once, in its inbound nonclaim; HYP-PF-034: the "
      "CLearnSkillVital inbound strict-decoder module, decode-only, named "
      "once in its docstring title) -- exact (file, verb, count) triples, so "
      "any new occurrence anywhere trips this again",
      sorted(src_hits) == sorted(LEARN_SKILL_RESULT_SRC_EXCEPTIONS),
      str(sorted(src_hits)))
named_emitted = [f for f in NAMED_FIELDS if f[4] in ("hp current", "hp max")]
print("        gap: 14 client classes  ->  0 ids declared server-side")
print("        gap: 19 named progression fields  ->  %d emitted server-side (%s)"
      % (len(named_emitted), ", ".join(f[4] for f in named_emitted)))
print("        gap: 5 progression verbs  ->  1 encoded outbound-only behind an "
      "opt-in flag (CLearnSkillResultVital 0x673C, LEARN-SKILL-RESULT-001 / "
      "HYP-PF-033), 4 with no server implementation; inbound: 1 strict opt-in "
      "decoder (CLearnSkillVital 0x36AA, LEARN-SKILL-REQUEST-001 / HYP-PF-034, "
      "decode-only, no reply, no learn rule, no write), 0 for the other four")
check("progression gap size: 14 classes client-side, 0 ids declared server-side; "
      "19 named progression fields, 2 emitted (the HP pair, already runtime-proven "
      "for a different lane); 5 progression verbs, 1 with an outbound-only opt-in "
      "encoder (LEARN-SKILL-RESULT-001), 1 with an inbound-only opt-in strict "
      "decoder (LEARN-SKILL-REQUEST-001, decode-only) and 3 with no server "
      "implementation in either direction",
      len(COHORT) == 14 and len(NAMED_FIELDS) == 19
      and len(named_emitted) == 2 and not id_present
      and sorted(src_hits) == sorted(LEARN_SKILL_RESULT_SRC_EXCEPTIONS))

print()
print("guards run: %d" % n_guard)
if fails:
    print("RESULT: FAIL - %d guard(s) drifted: %s" % (len(fails), fails))
    sys.exit(1)
print("RESULT: PASS - all %d stats/progression static guards reproduced from this "
      "binary (exit 0)" % n_guard)
sys.exit(0)
