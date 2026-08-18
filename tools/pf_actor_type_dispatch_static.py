#!/usr/bin/env python3
"""PF MP-AUDIT-FOLLOWUP-001 - static byte-exact enumeration of the client's
`actor_type` dispatch: which values of the one byte `u8tag(0x0B, actor_type)` at
the head of every remote-actor entry the client understands, which class each
value builds, which Attr each class will accept, and where an actor's on-screen
name comes from.

WHY THIS EXISTS.  MULTIPLAYER-READINESS-AUDIT-001 (round 77) graded the
"players can see each other" axis D and named exactly one reason: the byte that
distinguishes a remote PLAYER from a remote NPC had no evidence at all.  Only
`4` (CNetNPC) had ever been emitted or proven, so any second-player projection
would have had to put a guessed byte on the wire.  The audit also predicted the
question was answerable statically, from the client binary, with one client and
no transport work.  This milestone runs that experiment and reports the result.

SOLE EVIDENCE: the read-only client image GameClient/GameClient.local.bin,
disassembled, cross-checked against the read-only server sources.  Nothing was
executed: no server booted, no GameClient opened, no socket, no database.

WHAT IS PROVEN (byte-exact static disassembly):

  * THE BYTE.  The actor-entry record carries actor_type as a u8 at record+0x10.
    The setter 0x5DEC00 is literally `mov al,[esp+4]; mov [ecx+0x10],al; ret 4`.
    The record serializer 0x5E21D0 is direction-agnostic: the write path emits
    u8(tag 0x0B) @+0x10, qword(tag 0x32) identity @+0x18, u8(tag 0x0B) attr count,
    then per-attr u16(tag 0x12) id + that Attr's Serial; the read path at
    0x5E2301 decodes the same three fields through the inbound codec 0x89A640.

  * THE DISPATCH.  The actor factory 0x446990 is the only consumer of that byte:

        movzx eax, byte ptr [entry + 0x10]     ; the wire byte
        add   eax, -2
        cmp   eax, 4
        ja    0x446B14                         ; -> return NULL, no actor
        jmp   dword ptr [eax*4 + 0x446B2C]     ; 5-entry jump table

    The jump table has exactly five entries, so the client knows exactly five
    actor_type values, 2..6.  0, 1 and everything >= 7 fall through to the
    default and produce no actor at all.

        actor_type 2 -> CNetActor   size 0x3A8  pool 0x444DE0  ctor 0x457340  vtable 0xF0DD08
        actor_type 3 -> CMyActor    size 0x488  new  0x88D020  ctor 0x44C990  vtable 0xF0D7A8
        actor_type 4 -> CNetNPC     size 0x368  pool 0x444F00  ctor 0x45CC00  vtable 0xF0DF58
        actor_type 5 -> CAvatarNPC  size 0x378  pool 0x445020  ctor 0x45D000  vtable 0xF0DFF8
        actor_type 6 -> Pet         size 0x4E8  pool 0x445140  ctor 0x45E4E0  vtable 0xF0E0C8

    Each size is tied to a class NAME, not guessed: the per-class registrar
    thunks store the same object size into their class-info record next to the
    `.?AV<name>@@` descriptor (0x405BD9/0x405C69/0x40BA39/0x40BAC9/0x413259).

  * THE HIERARCHY (type-node registrar 0x88F2E0, parent token pushed per node):

        CActorBase (0x102D00C)
          `- CActorBaseClient (0x102CE88)
               |- CNetActor  (0x102CB2C)      <- actor_type 2, the REMOTE PLAYER branch
               |    |- CMyActor   (0x102CB04) <- actor_type 3, the LOCAL player
               |    `- CViewActor (0x1032758)
               `- CNetNPC   (0x102D954)       <- actor_type 4, what the server emits today
                    `- CAvatarNPC (0x102D92C) <- actor_type 5

    CNetActor is the base of CMyActor.  The class the client builds for a remote
    human player is therefore the same class family it builds for the local
    player, and it is NOT CNetNPC.

  * THE TWO BRANCH GUARDS (both are real preconditions, not decoration):
      - actor_type 3 is refused unless the local-player global 0x1032EC4 is zero
        (`cmp dword ptr [0x1032EC4], esi` with esi = 0, `jne` -> NULL): the
        client will build at most one CMyActor.
      - actor_type 4 and 5 are refused when the factory flag byte [this+0x6D] is
        non-zero.  actor_type 2, 3 and 6 have no such gate.

  * WHICH ATTRS EACH CLASS ACCEPTS.  CNetActor::init (vtable +0x10 = 0x454920)
    copies the entry identity into actor+0x78/+0x7C and then calls 0x5DF080,
    which walks the entry's Attr vector and invokes each Attr's vtable slot
    +0x38.  Every +0x38 is a CLASS-GATED BIND: it runs the runtime is-a check
    0x88F2B0 against one class token and silently does nothing when it fails.

        ActorAttr    0x12AD  vt 0xF0E7A0 +0x38 0x469760  gate CNetActor           -> actor+0x348
        NPCAttr      0x0AD5  vt 0xF0E7E0 +0x38 0x4697B0  gate CNetNPC             -> actor+0x358
        MovementAttr 0x2067  vt 0xF0D0F8 +0x38 0x469800  gate CActorBaseClient    -> actor+0x244
        AvatarAttr   0x16A0  vt 0xF0E088 +0x38 0x469850  gate CNetActor|CAvatarNPC-> actor vt+0x80
        CSkillAttr   0x1661  vt 0xF48B78 +0x38 0x4698B0  gate CMyActor            -> actor+0x3E8
        BasicAttr    0x1244  vt 0xF0E760 +0x38 0x73D360  = `ret 4`, binds nothing

    Consequence, stated plainly: an NPCAttr sent inside an actor_type 2 entry is
    parsed and then DROPPED, and an ActorAttr sent inside an actor_type 4 entry
    is parsed and then DROPPED.  The Attr the server emits today (NPCAttr) is
    the wrong one for the class a remote player is built from.

  * WHERE THE NAME COMES FROM.  Both actor families expose the bound attr through
    vtable +0x74 and its name through vtable +0x78:

        CNetActor / CMyActor            +0x74 = 0x44C630  `mov eax,[ecx+0x348]; ret`
        CNetNPC / CAvatarNPC / Pet      +0x74 = 0x45CD20  `mov eax,[ecx+0x358]; ret`
        CNetActor / CMyActor            +0x78 = 0x4549E0  -> [+0x348] then wstring +0x28
        CNetNPC / CAvatarNPC / Pet      +0x78 = 0x45BB40  -> [+0x358] then wstring +0x28
        both return the empty-wstring literal 0xF0930C when the attr is absent.

    The over-head board is created by vtable +0x7C: CNetActor allocates 0x78
    bytes (NameBoardPlayer) at 0x456580, CNetNPC allocates 0xC0 bytes
    (NameBoardNPC) at 0x45C560; the board is stored at actor+0x254 and loaded
    from the template L"board01" (0xF0DABC).  NameBoardPlayer binds its child
    widgets by name in 0x5BE080: HPBAR -> board+0x50, LABEL_NAME -> board+0x54,
    LABEL_NICKNAME -> board+0x58, LABEL_GUILD -> board+0x5C.  Its update
    0x5BD320 reads the owner at board+0x30, calls owner vt+0x74, and RETURNS
    IMMEDIATELY (je 0x5BD8C7) when that attr is NULL - no attr, no board.  With
    an attr it writes wstring attr+0x28 into LABEL_NAME (0x5BD624..0x5BD645) and,
    only after the ActorAttr downcast 0x43B9B0 succeeds, wstring ActorAttr+0x164
    into the LABEL_GUILD slot (0x5BD4D5..0x5BD512).  attr+0x28 is BasicAttr mask
    bit 0x0001 (Serial 0x4656F0: u16 mask @+0x70, bit 0x0001 -> wstring @+0x28).
    ActorAttr+0x164 is the field CHARACTER-NAME-001/002 already pinned; this
    milestone does not re-prove it, it only records that the slot is reachable
    only through the ActorAttr downcast and therefore only for actor_type 2/3.

  * THE STREAM PATH.  The RuntimeRes handler 0x5E4060 takes the derived +0x1C
    actor-stream collection and calls 0x446F30, which looks an actor up by the
    entry identity (0x446170) and, when absent, calls the factory 0x446990.
    So the byte enumerated here is exactly the byte the server controls in
    make_remote_actor_entry.

  * SERVER CROSS-CHECK (read-only): v141 has 19 make_remote_actor_entry call
    sites and every one of them passes the literal 4.  src population.py declares
    NPC_STYLE_ACTOR_TYPE = 4 and uses it twice; scene_object.py hardcodes 4.
    Of the five values the client knows, our server has ever emitted exactly one.

NOT CLAIMED: nothing about the ORIGINAL server - it is closed, was never
published, and every fact here is derived from the client.  No runtime capture,
no wire observation, no claim that any particular attr composition renders.
Report-only / additive: NO src/ change, NO scenario, NO matrix flip, NO ledger
entry.

Usage:  py -3 tools/pf_actor_type_dispatch_static.py [path-to-GameClient.local.bin]
        py -3 tools/pf_actor_type_dispatch_static.py --json
Exit 0 = every static guard reproduced; nonzero = a guard drifted.
"""
import hashlib
import json
import os
import re
import struct
import sys

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:  # pragma: no cover - environment guard, same as the sibling tools
    sys.exit("capstone required: pip install capstone")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))

EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"


def _default_bin():
    for cand in (
        os.path.join(_ROOT, "..", "GameClient", "GameClient.local.bin"),
        os.path.join(_ROOT, "GameClient", "GameClient.local.bin"),
        "GameClient/GameClient.local.bin",
    ):
        if os.path.isfile(cand):
            return cand
    return "GameClient/GameClient.local.bin"


# Only the script invocation owns argv; when the regression test imports this
# module the caller's argv (pytest's) must never be mistaken for our arguments.
_CLI = sys.argv[1:] if __name__ == "__main__" else []
_ARGS = [a for a in _CLI if a != "--json"]
AS_JSON = "--json" in _CLI
BIN = _ARGS[0] if _ARGS else _default_bin()

SERVER_SRC = os.path.join(_ROOT, "current", "pf_login_game_server_v141.py")
POPULATION_SRC = os.path.join(_ROOT, "src", "pirateforce_foundation", "population.py")
SCENE_OBJECT_SRC = os.path.join(_ROOT, "src", "pirateforce_foundation", "scene_object.py")
POPULATION_SCENARIO_SRC = os.path.join(
    _ROOT, "src", "pirateforce_foundation", "population_scenario.py"
)

data = open(BIN, "rb").read()
sha = hashlib.sha256(data).hexdigest().upper()

# --------------------------------------------------------------------------
# PE mapping (hand-rolled: this tool takes no dependency beyond capstone)
# --------------------------------------------------------------------------
_e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
_coff = _e_lfanew + 4
_nsec = struct.unpack_from("<H", data, _coff + 2)[0]
_opt_size = struct.unpack_from("<H", data, _coff + 16)[0]
_opt = _coff + 20
IMAGE_BASE = struct.unpack_from("<I", data, _opt + 28)[0]
_sect = _opt + _opt_size
SECTIONS = []
for _i in range(_nsec):
    _off = _sect + _i * 40
    _name = data[_off:_off + 8].rstrip(b"\0").decode("latin1")
    _vsize, _vaddr, _rawsize, _rawptr = struct.unpack_from("<IIII", data, _off + 8)
    SECTIONS.append((_name, _vaddr, _vsize, _rawptr, _rawsize))


def va2off(va):
    rel = va - IMAGE_BASE
    for _n, vaddr, vsize, rawptr, rawsize in SECTIONS:
        if vaddr <= rel < vaddr + max(vsize, rawsize):
            return rawptr + (rel - vaddr)
    return None


def off2va(off):
    for _n, vaddr, _vsize, rawptr, rawsize in SECTIONS:
        if rawptr <= off < rawptr + rawsize:
            return IMAGE_BASE + vaddr + (off - rawptr)
    return None


def rd(va, n):
    off = va2off(va)
    return data[off:off + n]


def dw(va):
    return struct.unpack("<I", rd(va, 4))[0]


def span_sha(a, b):
    return hashlib.sha256(rd(a, b - a)).hexdigest().upper()


def cstr(va, limit=128):
    off = va2off(va)
    end = data.find(b"\0", off, off + limit)
    return data[off:end].decode("latin1")


def wstr(va, limit=128):
    raw = rd(va, limit * 2)
    out = []
    for i in range(0, len(raw) - 1, 2):
        unit = raw[i] | (raw[i + 1] << 8)
        if unit == 0:
            break
        out.append(chr(unit))
    return "".join(out)


_TEXT = [s for s in SECTIONS if s[0] == ".text"][0]
TSTART = IMAGE_BASE + _TEXT[1]
TVSIZE = _TEXT[2]
_TLO = va2off(TSTART)
_THI = _TLO + TVSIZE

md = Cs(CS_ARCH_X86, CS_MODE_32)


def dmap(va, size):
    return {i.address: (i.mnemonic, i.op_str) for i in md.disasm(rd(va, size), va)}


def text_hits(pattern_hex):
    pat = bytes.fromhex(pattern_hex)
    out = []
    start = _TLO
    while True:
        j = data.find(pat, start, _THI)
        if j < 0:
            return out
        out.append(off2va(j))
        start = j + 1


def name_hash(name):
    """PF-NAMEID-HASH-001: u16 id = SUM_i (int16)((signed char)name[i] * (i+1))."""
    total = 0
    for index, byte in enumerate(name.encode("latin1")):
        signed = byte - 256 if byte > 127 else byte
        total = (total + ((signed * (index + 1)) & 0xFFFF)) & 0xFFFF
    return total


# --------------------------------------------------------------------------
# Guard accumulator
# --------------------------------------------------------------------------
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    if not AS_JSON:
        print(("PASS " if cond else "FAIL ") + name + ("  " + detail if detail else ""))
    return bool(cond)


# --------------------------------------------------------------------------
# Pinned addresses (every one of them is asserted below, none is decorative)
# --------------------------------------------------------------------------
ENTRY_SERIAL = 0x5E21D0          # actor-entry record serializer (both directions)
ENTRY_SERIAL_READ = 0x5E2301     # the inbound branch of that serializer
SET_ACTOR_TYPE = 0x5DEC00        # record.actor_type setter
CODEC_OUT = 0x89A600             # outbound field codec
CODEC_IN = 0x89A640              # inbound field codec
FACTORY = 0x446990               # actor factory keyed by actor_type
JUMP_TABLE = 0x446B2C
FACTORY_DEFAULT = 0x446B14
STREAM_APPLY = 0x446F30          # remote-actor stream apply loop
RUNTIME_RES_HANDLER = 0x5E4060   # RuntimeRes derived +0x1C consumer
ACTOR_LOOKUP = 0x446170
APPLY_ATTRS = 0x5DF080           # walks the entry attr vector, calls each Attr vt+0x38
ISA_CHECK = 0x88F2B0
TYPE_NODE_REGISTRAR = 0x88F2E0
EMPTY_WSTRING_LITERAL = 0xF0930C
BOARD_TEMPLATE = 0xF0DABC
NAMEBOARD_BIND = 0x5BE080
NAMEBOARD_UPDATE = 0x5BD320
NAMEBOARD_BAILOUT = 0x5BD8C7
ACTORATTR_DOWNCAST = 0x43B9B0
ACTORATTR_TOKEN_STUB = 0x4649A0
BASICATTR_SERIAL = 0x4656F0

# actor_type -> (class, object size, allocator, ctor, vtable, class-info registrar,
#                RTTI descriptor VA, class node token)
BRANCHES = {
    2: ("CNetActor", 0x3A8, 0x444DE0, 0x457340, 0xF0DD08, 0x405BD9, 0x101ABA8, 0x102CB2C),
    3: ("CMyActor", 0x488, 0x88D020, 0x44C990, 0xF0D7A8, 0x405C69, 0x101ABC0, 0x102CB04),
    4: ("CNetNPC", 0x368, 0x444F00, 0x45CC00, 0xF0DF58, 0x40BA39, 0x101B140, 0x102D954),
    5: ("CAvatarNPC", 0x378, 0x445020, 0x45D000, 0xF0DFF8, 0x40BAC9, 0x101B158, 0x102D92C),
    6: ("Pet", 0x4E8, 0x445140, 0x45E4E0, 0xF0E0C8, 0x413259, 0x101DA30, 0x102DA44),
}
BRANCH_ENTRY = {2: 0x4469E1, 3: 0x4469F7, 4: 0x446A3D, 5: 0x446A5A, 6: 0x446A77}

# Attr name -> (wire id, id-slot, vtable, +0x38 bind thunk, gate tokens, actor field)
ATTR_BINDS = {
    "ActorAttr": (0x12AD, 0x10334A0, 0xF0E7A0, 0x469760, (0x102CB2C,), 0x348),
    "NPCAttr": (0x0AD5, 0x10334A4, 0xF0E7E0, 0x4697B0, (0x102D954,), 0x358),
    "MovementAttr": (0x2067, 0x10334A8, 0xF0D0F8, 0x469800, (0x102CE88,), 0x244),
    "AvatarAttr": (0x16A0, 0x1033468, 0xF0E088, 0x469850, (0x102CB2C, 0x102D92C), None),
    "CSkillAttr": (0x1661, 0x108A32C, 0xF48B78, 0x4698B0, (0x102CB04,), 0x3E8),
    "BasicAttr": (0x1244, 0x103349C, 0xF0E760, 0x73D360, (), None),
}

# class token -> readable name (each one is proven against its RTTI descriptor below)
TOKEN_NAMES = {
    0x102D00C: "CActorBase",
    0x102CE88: "CActorBaseClient",
    0x102CB2C: "CNetActor",
    0x102CB04: "CMyActor",
    0x102D954: "CNetNPC",
    0x102D92C: "CAvatarNPC",
    0x1032758: "CViewActor",
    0x1033484: "ActorAttr",
}
# class token -> parent token, as pushed at the 0x88F2E0 registration site
TOKEN_PARENTS = {
    0x102CE88: 0x102D00C,
    0x102CB2C: 0x102CE88,
    0x102CB04: 0x102CB2C,
    0x102D954: 0x102CE88,
    0x102D92C: 0x102D954,
    0x1032758: 0x102CB2C,
}

WIDGETS = {
    0x50: ("HPBAR", 0xF2CFC8),
    0x54: ("LABEL_NAME", 0xF0C794),
    0x58: ("LABEL_NICKNAME", 0xF2CD88),
    0x5C: ("LABEL_GUILD", 0xF2CDA8),
}

# ==========================================================================
# 0. The binary itself
# ==========================================================================
check("binary SHA-256 matches the pinned read-only client", sha == EXPECT_SHA, sha)

# ==========================================================================
# 1. actor_type is one wire byte at record+0x10
# ==========================================================================
check(
    "record.actor_type setter 0x5DEC00 = mov al,[esp+4]; mov [ecx+0x10],al; ret 4",
    rd(SET_ACTOR_TYPE, 10).hex() == "8a442404884110c20400",
    rd(SET_ACTOR_TYPE, 10).hex(),
)
_ser = dmap(ENTRY_SERIAL, 0x140)
check(
    "entry serializer 0x5E21D0 outbound: u8 tag 0x0B @record+0x10 (actor_type)",
    _ser.get(0x5E2227) == ("lea", "eax, [esi + 0x10]")
    and rd(0x5E222B, 2) == bytes([0x6A, 0x0B])
    and _ser.get(0x5E222D) == ("call", hex(CODEC_OUT)),
)
check(
    "entry serializer 0x5E21D0 outbound: qword tag 0x32 identity @record+0x18",
    _ser.get(0x5E2234) == ("lea", "ecx, [esi + 0x18]")
    and rd(0x5E2238, 2) == bytes([0x6A, 0x32])
    and _ser.get(0x5E223C) == ("call", hex(CODEC_OUT)),
)
check(
    "entry serializer 0x5E21D0 outbound: u8 tag 0x0B attr count, then u16 tag 0x12 per Attr id",
    rd(0x5E2251, 2) == bytes([0x6A, 0x0B])
    and rd(0x5E229E, 2) == bytes([0x6A, 0x12])
    and _ser.get(0x5E22C2) == ("mov", "eax, dword ptr [edx + 0x34]"),
)
check(
    "entry serializer 0x5E21D0 direction flag: test bl,bl -> inbound branch 0x5E2301",
    _ser.get(0x5E221F) == ("test", "bl, bl")
    and _ser.get(0x5E2221) == ("je", hex(ENTRY_SERIAL_READ)),
)
_rdr = dmap(ENTRY_SERIAL_READ, 0x70)
check(
    "entry serializer inbound 0x5E2301 decodes u8 tag 0x0B into record+0x10 via codec 0x89A640",
    _rdr.get(0x5E2301) == ("lea", "edx, [esi + 0x10]")
    and rd(0x5E2305, 2) == bytes([0x6A, 0x0B])
    and _rdr.get(0x5E2307) == ("call", hex(CODEC_IN)),
)
check(
    "entry serializer inbound 0x5E2301 decodes qword tag 0x32 identity into record+0x18",
    _rdr.get(0x5E230E) == ("lea", "eax, [esi + 0x18]")
    and rd(0x5E2312, 2) == bytes([0x6A, 0x32])
    and _rdr.get(0x5E2316) == ("call", hex(CODEC_IN)),
)
check(
    "entry serializer spans byte-identical (outbound 0x5E21D0..0x5E22D7, inbound 0x5E2301..0x5E2361)",
    span_sha(ENTRY_SERIAL, 0x5E22D7)
    == "B80A94A7FB0641C38508A93C1AD0E16EA2B91AA78B4E72C302A9341BD6AA9F6F"
    and span_sha(ENTRY_SERIAL_READ, 0x5E2361)
    == "4A1E46BCD6C93E2AD8B532E26A5DB1720932BBA42BEB3814EAB98C83FC2BE761",
)

# ==========================================================================
# 2. The dispatch: five branches, 2..6, everything else builds no actor
# ==========================================================================
_fac = dmap(FACTORY, 0x1C0)
check(
    "actor factory 0x446990 reads the wire byte: movzx eax, byte ptr [entry+0x10]",
    _fac.get(0x4469C8) == ("movzx", "eax, byte ptr [eax + 0x10]"),
)
check(
    "actor factory rebases by -2 and rejects anything above 4 (cmp eax,4 / ja default)",
    _fac.get(0x4469CC) == ("add", "eax, -2")
    and _fac.get(0x4469D1) == ("cmp", "eax, 4")
    and _fac.get(0x4469D4) == ("ja", hex(FACTORY_DEFAULT)),
)
check(
    "actor factory dispatches through the jump table at 0x446B2C",
    _fac.get(0x4469DA) == ("jmp", "dword ptr [eax*4 + 0x446b2c]"),
)
_table = [dw(JUMP_TABLE + 4 * i) for i in range(5)]
check(
    "the jump table has exactly five entries and they are the five branch heads",
    _table == [BRANCH_ENTRY[t] for t in (2, 3, 4, 5, 6)],
    str([hex(x) for x in _table]),
)
check(
    "the default branch 0x446B14 returns esi, which is zero on that path -> no actor at all",
    _fac.get(0x4469CF) == ("xor", "esi, esi")
    and _fac.get(FACTORY_DEFAULT) == ("mov", "eax, esi"),
)
check(
    "actor factory span 0x446990..0x446B2C byte-identical",
    span_sha(FACTORY, JUMP_TABLE)
    == "5F68239F8661419DA2EA9BEA4E4A2CB9BCDCAA37FE6E4CD53B701116AEEB697D",
    span_sha(FACTORY, JUMP_TABLE),
)
check(
    "jump table bytes 0x446B2C..0x446B40 byte-identical",
    span_sha(JUMP_TABLE, 0x446B40)
    == "B50C1D1DB53D2B70A8AD258563750738639D5E9E3EEF2FA5CFB4C5354632D606",
    span_sha(JUMP_TABLE, 0x446B40),
)

# ==========================================================================
# 3. Every branch -> a named class, with its size proven by the class registrar
# ==========================================================================
for _t in (2, 3, 4, 5, 6):
    _name, _size, _alloc, _ctor, _vt, _reg, _desc, _token = BRANCHES[_t]
    _push_size = bytes.fromhex("68" + struct.pack("<I", _size).hex())
    check(
        "actor_type %d branch @0x%06X reaches an allocation of 0x%X bytes (%s)"
        % (_t, BRANCH_ENTRY[_t], _size, _name),
        _push_size in rd(BRANCH_ENTRY[_t], 0x40)
        or any(op == ("push", hex(_size)) for op in dmap(_alloc, 0x140).values()),
    )
    check(
        "actor_type %d class-info registrar 0x%06X ties size 0x%X to descriptor '%s'"
        % (_t, _reg, _size, cstr(_desc)),
        rd(_reg, 7).hex() == ("c7470c" + struct.pack("<I", _size).hex())
        and cstr(_desc).endswith(_name + "@@"),
        cstr(_desc),
    )
    check(
        "actor_type %d builds %s: ctor 0x%06X installs vtable 0x%06X"
        % (_t, _name, _ctor, _vt),
        any(
            m == "mov" and o == "dword ptr [esi], " + hex(_vt)
            for m, o in dmap(_ctor, 0x140).values()
        ),
    )

check(
    "actor_type 2 and 4 route through their per-class pool allocators (0x444DE0 / 0x444F00)",
    dmap(BRANCH_ENTRY[2], 0x18).get(0x4469ED) == ("call", hex(BRANCHES[2][2]))
    and dmap(BRANCH_ENTRY[4], 0x20).get(0x446A53) == ("call", hex(BRANCHES[4][2])),
)
check(
    "actor_type 3 allocates CMyActor inline with the global operator new 0x88D020",
    dmap(BRANCH_ENTRY[3], 0x20).get(0x446A08) == ("call", hex(BRANCHES[3][2])),
)

# ==========================================================================
# 4. The two branch guards
# ==========================================================================
check(
    "actor_type 3 is gated on the local-player global 0x1032EC4 being zero (one CMyActor max)",
    _fac.get(0x4469F7) == ("cmp", "dword ptr [0x1032ec4], esi")
    and _fac.get(0x4469FD) == ("jne", hex(FACTORY_DEFAULT)),
)
check(
    "actor_type 4 and 5 are gated on the factory flag byte [this+0x6D] == 0",
    _fac.get(0x446A3D) == ("cmp", "byte ptr [edi + 0x6d], 0")
    and _fac.get(0x446A41) == ("jne", hex(FACTORY_DEFAULT))
    and _fac.get(0x446A5A) == ("cmp", "byte ptr [edi + 0x6d], 0")
    and _fac.get(0x446A5E) == ("jne", hex(FACTORY_DEFAULT)),
)
check(
    "actor_type 2, 3 and 6 carry no [this+0x6D] gate",
    all(
        ("cmp", "byte ptr [edi + 0x6d], 0") not in dmap(BRANCH_ENTRY[t], 0x14).values()
        for t in (2, 3, 6)
    ),
)

# ==========================================================================
# 5. The class hierarchy (registrar 0x88F2E0)
# ==========================================================================
for _token, _parent in TOKEN_PARENTS.items():
    _reg_site = None
    for _s in text_hits("68" + struct.pack("<I", _parent).hex()):
        _win = dmap(_s, 0x1C)
        if _win.get(_s + 5) == ("mov", "ecx, " + hex(_token)):
            _reg_site = _s
    check(
        "type-node registration: %s (0x%07X) declares parent %s (0x%07X)"
        % (TOKEN_NAMES[_token], _token, TOKEN_NAMES[_parent], _parent),
        _reg_site is not None
        and dmap(_reg_site, 0x20).get(_reg_site + 10) == ("call", hex(TYPE_NODE_REGISTRAR)),
    )
check(
    "CNetActor is the parent of CMyActor, so actor_type 2 is the local player's own class family",
    TOKEN_PARENTS[0x102CB04] == 0x102CB2C,
)
check(
    "CNetNPC is a sibling of CNetActor under CActorBaseClient, not an ancestor of it",
    TOKEN_PARENTS[0x102D954] == 0x102CE88 and TOKEN_PARENTS[0x102CB2C] == 0x102CE88,
)

# ==========================================================================
# 6. CNetActor::init and the attr-application loop
# ==========================================================================
check(
    "CNetActor vtable +0x10 = init 0x454920",
    dw(BRANCHES[2][4] + 0x10) == 0x454920,
    hex(dw(BRANCHES[2][4] + 0x10)),
)
_init = dmap(0x454920, 0xC0)
check(
    "CNetActor::init copies the entry identity qword into actor+0x78/+0x7C",
    _init.get(0x45493D) == ("mov", "dword ptr [esi + 0x78], ecx")
    and _init.get(0x454943) == ("mov", "dword ptr [esi + 0x7c], edx"),
)
check(
    "CNetActor::init then calls the attr-application loop 0x5DF080 with the actor",
    _init.get(0x454949) == ("call", hex(APPLY_ATTRS)),
)
_apply = dmap(APPLY_ATTRS, 0x50)
check(
    "attr-application loop 0x5DF080 walks the record attr vector and calls each Attr vtable +0x38",
    _apply.get(0x5DF0B2) == ("mov", "ecx, dword ptr [edx + edi*4]")
    and _apply.get(0x5DF0B7) == ("mov", "edx, dword ptr [eax + 0x38]"),
)
check(
    "CNetActor::init and the attr loop spans byte-identical",
    span_sha(0x454920, 0x4549DD)
    == "D907227D59491E7955F5E22598979AE4D81A22492BEB87791688A27C52BCC831"
    and span_sha(APPLY_ATTRS, 0x5DF0D0)
    == "02F92197947B7D83DF6B1FAF6D9D6A2FD1DDEAF7993881D3D03885BC2FD19A46",
)

# ==========================================================================
# 7. Per-Attr class gating: which Attr binds to which actor class
# ==========================================================================
for _attr, (_wid, _slot, _vt, _thunk, _gates, _field) in ATTR_BINDS.items():
    check(
        "PF-NAMEID-HASH-001 reproduces %s id 0x%04X from its name literal" % (_attr, _wid),
        name_hash(_attr) == _wid,
        hex(name_hash(_attr)),
    )
    _stores = text_hits("66a3" + struct.pack("<I", _slot).hex())
    _reads = text_hits("66a1" + struct.pack("<I", _slot).hex())
    check(
        "%s id-slot 0x%07X written once and read by exactly one get-id stub" % (_attr, _slot),
        len(_stores) == 1 and len(_reads) == 1,
        "stores=%s reads=%s" % ([hex(x) for x in _stores], [hex(x) for x in _reads]),
    )
    check(
        "%s vtable 0x%06X slot +0x10 is that get-id stub and slot +0x38 is 0x%06X"
        % (_attr, _vt, _thunk),
        len(_reads) == 1 and dw(_vt + 0x10) == _reads[0] and dw(_vt + 0x38) == _thunk,
        "%s / %s" % (hex(dw(_vt + 0x10)), hex(dw(_vt + 0x38))),
    )

check(
    "BasicAttr vtable +0x38 is the no-op `ret 4` 0x73D360 - BasicAttr binds to no actor field",
    rd(ATTR_BINDS["BasicAttr"][3], 3).hex() == "c20400",
)
for _attr in ("ActorAttr", "NPCAttr", "MovementAttr", "CSkillAttr"):
    _wid, _slot, _vt, _thunk, _gates, _field = ATTR_BINDS[_attr]
    _bind = dmap(_thunk, 0x40)
    _gate = _gates[0]
    check(
        "%s +0x38 bind 0x%06X gates on is-a %s (0x%07X) via 0x88F2B0"
        % (_attr, _thunk, TOKEN_NAMES[_gate], _gate),
        any(op == ("push", hex(_gate)) for op in _bind.values())
        and any(op == ("call", hex(ISA_CHECK)) for op in _bind.values()),
    )
    check(
        "%s +0x38 bind targets actor field +0x%X and does nothing when the is-a fails"
        % (_attr, _field),
        any(
            m == "mov" and o == "eax, dword ptr [eax + " + hex(_field) + "]"
            for m, o in _bind.values()
        )
        and any(m == "je" for m, _o in _bind.values()),
    )
_avatar_bind = dmap(ATTR_BINDS["AvatarAttr"][3], 0x60)
check(
    "AvatarAttr +0x38 bind 0x469850 accepts CNetActor OR CAvatarNPC and routes via actor vtable +0x80",
    all(
        any(op == ("push", hex(g)) for op in _avatar_bind.values())
        for g in ATTR_BINDS["AvatarAttr"][4]
    )
    and any(
        m == "mov" and o == "edx, dword ptr [eax + 0x80]" for m, o in _avatar_bind.values()
    ),
)
check(
    "the five bind thunks are byte-identical",
    span_sha(0x469760, 0x4697A0)
    == "B122BAB7259BF0C83F8FD94C9BC89B1ABCD69DDEF82E05C5E664A62CFBABB7DF"
    and span_sha(0x4697B0, 0x4697F0)
    == "804AE4757E744F6E2E1B8FC6C18CAE0923C34F6161AE2F9C1094F781D2B2650A"
    and span_sha(0x469800, 0x469840)
    == "368A83127F68C19688C2C32708662C381081D831C0D41FD4A3682CD28220B227"
    and span_sha(0x469850, 0x4698AE)
    == "9B141BE64A7E4EA84DE514DEAF0532588FD05DC4BB97DC99F931D13703C5622E"
    and span_sha(0x4698B0, 0x4698F0)
    == "C42082A429D7F98289A95FADFA9AAF264180152783A969C09F6F48B38F067CBD",
)
check(
    "the ActorAttr gate and the NPCAttr gate are different classes: an NPCAttr inside an "
    "actor_type 2 entry is dropped, and an ActorAttr inside an actor_type 4 entry is dropped",
    ATTR_BINDS["ActorAttr"][4][0] != ATTR_BINDS["NPCAttr"][4][0]
    and ATTR_BINDS["ActorAttr"][4][0] == BRANCHES[2][7]
    and ATTR_BINDS["NPCAttr"][4][0] == BRANCHES[4][7],
)
check(
    "MovementAttr gates on CActorBaseClient, the common ancestor - it binds to every actor_type",
    ATTR_BINDS["MovementAttr"][4][0] == 0x102CE88,
)

# ==========================================================================
# 8. The name over the head
# ==========================================================================
check(
    "CNetActor / CMyActor vtable +0x74 = 0x44C630 `mov eax,[ecx+0x348]; ret` (bound ActorAttr)",
    dw(BRANCHES[2][4] + 0x74) == 0x44C630
    and dw(BRANCHES[3][4] + 0x74) == 0x44C630
    and rd(0x44C630, 7).hex() == "8b8148030000c3",
)
check(
    "CNetNPC / CAvatarNPC / Pet vtable +0x74 = 0x45CD20 `mov eax,[ecx+0x358]; ret` (bound NPCAttr)",
    dw(BRANCHES[4][4] + 0x74) == 0x45CD20
    and dw(BRANCHES[5][4] + 0x74) == 0x45CD20
    and dw(BRANCHES[6][4] + 0x74) == 0x45CD20
    and rd(0x45CD20, 7).hex() == "8b8158030000c3",
)
_gn_actor = dmap(0x4549E0, 0x50)
_gn_npc = dmap(0x45BB40, 0x50)
check(
    "CNetActor::GetName (vt+0x78 = 0x4549E0) reads wstring [+0x348]+0x28, or the empty "
    "literal 0xF0930C when no ActorAttr is bound",
    dw(BRANCHES[2][4] + 0x78) == 0x4549E0
    and _gn_actor.get(0x4549E1) == ("mov", "eax, dword ptr [ecx + 0x348]")
    and _gn_actor.get(0x4549F4) == ("lea", "ecx, [eax + 0x28]")
    and any(op == ("push", hex(EMPTY_WSTRING_LITERAL)) for op in _gn_actor.values()),
)
check(
    "CNetNPC::GetName (vt+0x78 = 0x45BB40) reads wstring [+0x358]+0x28 with the same fallback",
    dw(BRANCHES[4][4] + 0x78) == 0x45BB40
    and _gn_npc.get(0x45BB41) == ("mov", "eax, dword ptr [ecx + 0x358]")
    and _gn_npc.get(0x45BB54) == ("lea", "ecx, [eax + 0x28]")
    and any(op == ("push", hex(EMPTY_WSTRING_LITERAL)) for op in _gn_npc.values()),
)
check(
    "the GetName fallback literal 0xF0930C is the empty wide string",
    rd(EMPTY_WSTRING_LITERAL, 2) == b"\x00\x00",
)
_basic = dmap(BASICATTR_SERIAL, 0x60)
check(
    "BasicAttr Serial 0x4656F0: u16 mask (tag 0x12) @+0x70, bit 0x0001 -> the wstring @+0x28",
    _basic.get(0x465708) == ("lea", "ebx, [esi + 0x70]")
    and rd(0x46570E, 2) == bytes([0x6A, 0x12])
    and _basic.get(0x465727) == ("test", "al, 1")
    and _basic.get(0x46572B) == ("lea", "eax, [esi + 0x28]"),
)
check(
    "CNetActor vtable +0x7C = 0x456580 allocates 0x78 (NameBoardPlayer) into actor+0x254",
    dw(BRANCHES[2][4] + 0x7C) == 0x456580
    and dmap(0x456580, 0x40).get(0x4565A5) == ("push", "0x78")
    and any(
        m == "mov" and o == "dword ptr [edi + 0x254], esi"
        for m, o in dmap(0x456580, 0x90).values()
    ),
)
check(
    "CNetNPC vtable +0x7C = 0x45C560 allocates 0xC0 (NameBoardNPC) instead",
    dw(BRANCHES[4][4] + 0x7C) == 0x45C560
    and dmap(0x45C560, 0x40).get(0x45C585) == ("push", "0xc0"),
)
check(
    "0x78 / 0xC0 are the registered NameBoardPlayer / NameBoardNPC object sizes",
    rd(0x40B6D9, 7).hex() == "c7470c78000000"
    and rd(0x40B769, 7).hex() == "c7470cc0000000"
    and cstr(0x101B084) == ".?AVNameBoardPlayer@@"
    and cstr(0x101B0A4) == ".?AVNameBoardNPC@@",
)
check(
    'CNetActor::init loads the board template L"board01" (0xF0DABC) and marks actor+0x258',
    wstr(BOARD_TEMPLATE) == "board01"
    and _init.get(0x45496A) == ("push", hex(BOARD_TEMPLATE))
    and _init.get(0x454971) == ("mov", "byte ptr [esi + 0x258], 1"),
)
_bind_map = dmap(NAMEBOARD_BIND, 0x200)
for _off, (_widget, _lit) in WIDGETS.items():
    check(
        'NameBoardPlayer binds widget L"%s" (0x%06X) to board+0x%02X' % (_widget, _lit, _off),
        wstr(_lit) == _widget
        and any(op == ("push", hex(_lit)) for op in _bind_map.values())
        and any(
            m == "mov" and o == "dword ptr [edi + " + hex(_off) + "], eax"
            for m, o in _bind_map.values()
        ),
    )
_upd = dmap(NAMEBOARD_UPDATE, 0x600)
check(
    "name board update 0x5BD320 reads the owner at board+0x30 and calls owner vtable +0x74",
    _upd.get(0x5BD372) == ("mov", "ecx, dword ptr [esi + 0x30]")
    and _upd.get(0x5BD377) == ("mov", "edx, dword ptr [eax + 0x74]"),
)
check(
    "name board update returns immediately when the bound attr is NULL - no attr, no board",
    _upd.get(0x5BD380) == ("test", "eax, eax")
    and _upd.get(0x5BD382) == ("je", hex(NAMEBOARD_BAILOUT)),
)
check(
    "LABEL_NAME (board+0x54) is fed the wstring at attr+0x28 (BasicAttr name, mask bit 0x0001)",
    _upd.get(0x5BD628) == ("add", "edi, 0x28")
    and _upd.get(0x5BD633) == ("mov", "ecx, dword ptr [esi + 0x54]"),
)
check(
    "the LABEL_GUILD slot (board+0x5C) is fed ActorAttr+0x164, reachable only after the "
    "ActorAttr downcast 0x43B9B0 succeeds",
    _upd.get(0x5BD4C9) == ("call", hex(ACTORATTR_DOWNCAST))
    and _upd.get(0x5BD4DA) == ("lea", "edi, [eax + 0x164]")
    and _upd.get(0x5BD4D5) == ("mov", "ecx, dword ptr [esi + 0x5c]"),
)
check(
    "the downcast 0x43B9B0 compares against the ActorAttr class token 0x1033484",
    dmap(ACTORATTR_DOWNCAST, 0x30).get(0x43B9C2) == ("call", hex(ACTORATTR_TOKEN_STUB))
    and rd(ACTORATTR_TOKEN_STUB, 6).hex() == "b884340301c3"
    and TOKEN_NAMES[0x1033484] == "ActorAttr",
)
check(
    "name-board spans byte-identical (GetName pair, GetAttr pair, LABEL_NAME write)",
    span_sha(0x4549E0, 0x454A29)
    == "A849817032D6A66CB8E62FA96FFB61BF6A0D4E64CA5CB05143F3291F53E533F0"
    and span_sha(0x45BB40, 0x45BB89)
    == "9C55AF3EE4A9B51B3A20D701AE2DE3FCCBE9DB328EC8E88EC2B124511D5A82DE"
    and span_sha(0x44C630, 0x44C637)
    == "AA2401D9B386779ADA20899ED924ACFABCF81CE58E8DE01CD56743BEC2BC7063"
    and span_sha(0x45CD20, 0x45CD27)
    == "232E697CEB24D976C5D9FB915AA60FDC994C1B655A70C1FC2F4654884FC11492"
    and span_sha(0x5BD624, 0x5BD646)
    == "736DA6EE7C53CED4A201B4A79169F528DDA4F229C555B09329D16543B5A40E26",
)

# ==========================================================================
# 9. The stream path: the byte the server controls reaches this factory
# ==========================================================================
_rt = dmap(RUNTIME_RES_HANDLER, 0x40)
check(
    "RuntimeRes handler 0x5E4060 takes the derived +0x1C actor-stream collection into 0x446F30",
    _rt.get(0x5E4073) == ("mov", "eax, dword ptr [esi + 0x1c]")
    and _rt.get(0x5E4085) == ("call", hex(STREAM_APPLY)),
)
_sa = dmap(STREAM_APPLY, 0xC0)
check(
    "stream apply 0x446F30 looks the entry identity up (0x446170) and calls the factory when absent",
    _sa.get(0x446F91) == ("call", hex(ACTOR_LOOKUP))
    and _sa.get(0x446FA3) == ("call", hex(FACTORY)),
)
check(
    "stream apply reads the entry identity from record+0x18/+0x1C, the offsets the serializer decodes",
    _sa.get(0x446F87) == ("mov", "ecx, dword ptr [eax + 0x18]")
    and _sa.get(0x446F8A) == ("mov", "eax, dword ptr [eax + 0x1c]"),
)
check(
    "an already-known identity takes the update path (actor vtable +0x20) instead of the factory",
    _sa.get(0x446FB6) == ("mov", "eax, dword ptr [edx + 0x20]"),
)

# ==========================================================================
# 10. Server cross-check (read-only)
# ==========================================================================
_server = open(SERVER_SRC, "r", encoding="utf-8", errors="replace").read()
_v141_calls = re.findall(r"make_remote_actor_entry\(\s*(\d+)", _server)
V141_CALLSITES = len(_v141_calls)
V141_TYPES = sorted({int(v) for v in _v141_calls})
check(
    "v141 has %d make_remote_actor_entry call sites with a literal actor_type" % V141_CALLSITES,
    V141_CALLSITES == 19,
    str(V141_CALLSITES),
)
check(
    "every one of them passes 4 (CNetNPC): the server has emitted 1 of the 5 known values",
    V141_TYPES == [4],
    str(V141_TYPES),
)
check(
    "v141 declares NPC_ATTR 0x0AD5, ACTOR_ATTR 0x12AD and MOVEMENT_ATTR 0x2067",
    "NPC_ATTR = 0x0AD5" in _server
    and "ACTOR_ATTR = 0x12AD" in _server
    and "MOVEMENT_ATTR = 0x2067" in _server,
)
check(
    "v141 never carries ACTOR_ATTR inside a remote-actor entry "
    "(its only two uses are UpdateAttrVital payloads)",
    len(re.findall(r"u16tag\(0x12,\s*ACTOR_ATTR\)", _server)) == 2,
    str(len(re.findall(r"u16tag\(0x12,\s*ACTOR_ATTR\)", _server))),
)
_population = open(POPULATION_SRC, "r", encoding="utf-8", errors="replace").read()
_pop_uses = len(re.findall(r"\bNPC_STYLE_ACTOR_TYPE\b", _population))
check(
    "src population.py declares NPC_STYLE_ACTOR_TYPE = 4 and uses it at two call sites",
    "NPC_STYLE_ACTOR_TYPE = 4" in _population and _pop_uses == 3,
    str(_pop_uses),
)
_scene_object = open(SCENE_OBJECT_SRC, "r", encoding="utf-8", errors="replace").read()
check(
    "src scene_object.py hardcodes actor type 4 as well",
    "make_remote_actor_entry(4," in _scene_object.replace(" ", ""),
)
_pop_scenario = open(POPULATION_SCENARIO_SRC, "r", encoding="utf-8", errors="replace").read()
check(
    "src population_scenario.py still lists remote_player as an explicit nonclaim",
    "remote_player" in _pop_scenario,
)

# ==========================================================================
# Counts block (the report is pinned to these, never to hand-typed numbers)
# ==========================================================================
GUARDS_TOTAL = len(RESULTS)
GUARDS_FAILED = [n for n, ok in RESULTS if not ok]

COUNTS = {
    "measured_at_head": "f286945",
    "client_sha256": sha,
    "guards_total": GUARDS_TOTAL,
    "actor_type_branch_count": len(BRANCHES),
    "actor_type_min": min(BRANCHES),
    "actor_type_max": max(BRANCHES),
    "actor_type_classes": {str(k): v[0] for k, v in sorted(BRANCHES.items())},
    "actor_type_object_sizes": {str(k): v[1] for k, v in sorted(BRANCHES.items())},
    "actor_type_branches_with_extra_gate": 3,
    "remote_player_actor_type": 2,
    "local_player_actor_type": 3,
    "server_emitted_actor_type": 4,
    "attr_bind_thunks_examined": len(ATTR_BINDS),
    "attr_bind_thunks_class_gated": 5,
    "attr_bind_thunks_noop": 1,
    "nameid_hash_ids_reproduced": len(ATTR_BINDS),
    "class_hierarchy_edges_proven": len(TOKEN_PARENTS),
    "nameboard_widget_slots_proven": len(WIDGETS),
    "v141_remote_actor_entry_callsites": V141_CALLSITES,
    "v141_literal_actor_types": V141_TYPES,
    "actor_types_never_emitted_by_us": [t for t in sorted(BRANCHES) if t not in V141_TYPES],
}

if AS_JSON:
    print(json.dumps(COUNTS, indent=2, sort_keys=True))
else:
    print()
    print("actor_type dispatch, as the client sees it:")
    for _t in sorted(BRANCHES):
        _name, _size, _alloc, _ctor, _vt, _reg, _desc, _token = BRANCHES[_t]
        print(
            "  actor_type %d -> %-11s size 0x%03X  ctor 0x%06X  vtable 0x%06X"
            % (_t, _name, _size, _ctor, _vt)
        )
    print("  anything else -> NULL, no actor is created at all")
    print()
    print("guards run: %d, failed: %d" % (GUARDS_TOTAL, len(GUARDS_FAILED)))

if GUARDS_FAILED:
    if not AS_JSON:
        print("RESULT: %d guard(s) drifted: %s" % (len(GUARDS_FAILED), GUARDS_FAILED))
    sys.exit(1)
if not AS_JSON:
    print("RESULT: all actor_type dispatch static guards reproduced (exit 0)")
