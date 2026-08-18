#!/usr/bin/env python3
"""PF MP-OPT1-B - static byte-exact decode of ``LSCN_LoginVitalReq`` (0x42BF):
what the frame contains, which field is the account, what type and length each
field has, where the client gets both values from, and what else the account is
bound to inside the client.

WHY THIS EXISTS.  MULTIPLAYER-READINESS-AUDIT-001 (round 77) listed nine wire
facts a real multiplayer server would have to guess.  G8 is the account and
credential field roles of ``LSCN_LoginVitalReq``.  The audit's exact wording is
that the bytes "exist in every archived capture and the tool reproduces them
byte-exact - but the value never varies (``test``)", so from the corpus alone
nothing could be shown to be the account.  Panya approved Option 1, "answer the
byte first"; part (a), the ``actor_type`` dispatch, landed in round 78.  This is
part (b).  It removes a guess; it creates none.

SOLE EVIDENCE: the read-only client image GameClient/GameClient.local.bin,
disassembled, plus the read-only archived ``LOGIN_*.txt`` and ``capture_v141``
corpora and the read-only frozen server ``current/pf_login_game_server_v141.py``.
Nothing was executed: no server booted, no GameClient opened, no socket, no
database, no ``src/`` change, no matrix flip, no new hypothesis.

WHAT IS PROVEN (byte-exact static disassembly, every address asserted below):

  * THE CLASS.  ``LSCN_LoginVitalReq`` is the literal at 0xF0B084.  Its
    registration thunk 0xBEFDF0 has the exact PF-NAMEID shape settled in round
    62 (``push <lit>; call 0x89C080; mov ecx,eax; call 0x89BD00;
    mov word ptr [0x1082344], ax; ret``), so the wire id lives in slot
    0x1082344, and the round-62 name hash of that literal is 0x42BF.  The type
    registrar 0xBEFE90 ties class token 0x1082338 to the RTTI descriptor
    ``.?AVLSCN_LoginVitalReq@@``, whose parent descriptor is ``.?AVVitalData@@``.
    Vtable slot +0x00 returns that same token, which is what makes vtable
    0xF16B34 this class's vtable and not a neighbour's.

  * THE OBJECT.  Constructor 0x4C5090 (0x4C bytes, allocated by the prototype
    registrar at 0x5F2E83) builds exactly two string members:

        this+0x14   std::wstring   (MSVCP90 basic_string<wchar_t> ctor, IAT 0xC3B478)
        this+0x30   std::string    (MSVCP90 basic_string<char>    ctor, IAT 0xC3B458)

    The destructor 0x4C5130 destroys the same two and nothing else.

  * THE FRAME.  ``Serial`` is vtable +0x18 = 0x5F2780, 0x45 bytes long,
    direction-agnostic, with exactly two fields per direction and no others:

        write (flag != 0, at 0x5F278F)  0x89A810(this+0x14) then 0x89A6D0(this+0x30)
        read  (flag == 0, at 0x5F27AA)  0x89A880(this+0x14) then 0x89A740(this+0x30)

    and the four codec helpers pin the wire encoding themselves:

        0x89A810  tag 0x48  u32 = 2 * wstring::length()  then the UTF-16LE bytes
        0x89A6D0  tag 0x44  u32 =     string::length()   then the raw bytes
        0x89A880  tag 0x48  inbound twin
        0x89A740  tag 0x44  inbound twin

    So the whole frame body is, in this order and with nothing else in it:

        48 <u32 byte-len> <UTF-16LE account>   44 <u32 byte-len> <ANSI password>

  * WHICH FIELD IS THE ACCOUNT.  ``cStateLogin::DoLogin`` = 0x4C5920 (class token
    0x107A5AC resolves to descriptor ``.?AVcStateLogin@@``, parent
    ``.?AVCState@@``) takes (account_wstring*, password_wstring*) and fills the
    request at 0x4C5A50..0x4C5A79:

        pool-allocate the request           (0x4C5690, pool head 0x107A498)
        lea ecx,[req+0x14]; wstring::operator=(*account)     <- +0x14 IS THE ACCOUNT
        lea ecx,[req+0x30]; string::operator=(narrowed pwd)  <- +0x30 IS THE PASSWORD
        then send it                        (app singleton 0x4011A0 -> 0x5DD890)

    The password's ANSI form is produced by 0x88E200 -> 0x88E090, which is a
    plain ``wstring::c_str()`` plus ``WideCharToMultiByte`` (IAT 0xC3B0EC).
    There is no hash, no salt and no cipher on that path: the password crosses
    the wire in clear text.

  * WHERE THE TWO VALUES COME FROM.  WinMain 0x40AE70 reads the process command
    line (``GetCommandLineW``, IAT 0xC3B208) through the option parser 0xB00B20
    for L"-acc" (0xF0A12C) and L"-pwd" (0xF0A120).  Only when BOTH are present
    does it set the flag byte 0x102C5AC to 1 and copy the two values into the
    globals 0x102C5B0 (account) and 0x102C5CC (password).  ``cStateLogin``'s
    state-entry hook (its own vtable 0xF16B58, slot +0x10 = 0x4C5AE0) branches on
    that flag: set -> ``DoLogin(0x102C5B0, 0x102C5CC)`` with no UI at all; clear
    -> open the L"Prototype_Login1" dialog, whose OK handler 0x4D9630 calls the
    same ``DoLogin`` with GetText of its two edit boxes (+0x14 account, +0x18
    password - the same two widgets the auto-fill 0x4D9990 pushes the two globals
    into).  The account field is therefore an argument- or UI-sourced variable in
    both paths.  It is not a constant and it is not hard-coded.

  * WHY EVERY ARCHIVED CAPTURE SHOWS 0E 00 00 00 AND NOT L"test".  On the
    command-line path only, ``DoLogin`` first rewrites the account through
    0x89B070 and assigns the result back over the account wstring.  0x89B070 is
    a HEX DECODER, recovered instruction by instruction:

        empty input   -> L"" (the empty-wide literal 0xF0930C)
        odd length    -> substr(0, len-1)              (IAT 0xC3B46C)
        then for i in 0,2,4,...  wchar = (hexval(s[i]) << 4) + hexval(s[i+1])
                                 appended with wstring::operator+=(wchar_t)

    ``hexval`` is 0x89ACC0: ``c - 0x30``, bounds-checked against 0x36, indexed
    into the 0x37-byte map at 0x89AD7C and dispatched through the 17-entry jump
    table at 0x89AD38.  This verifier rebuilds that table out of the image and
    proves it is exactly hexadecimal, returning 0 for every other character.

    Therefore, for the arguments every launcher job in this project has always
    used, ``-acc test``:

        hexval('t')=0, hexval('e')=0xE -> wchar 0x000E
        hexval('s')=0, hexval('t')=0   -> wchar 0x0000
        account wstring = U+000E U+0000 = the wire bytes 0E 00 00 00

    which is byte-for-byte the field in every archived login capture.  The field
    was never constant.  It has always been ``decode_hex(the -acc argument)``,
    and this project has only ever passed one argument.

  * WHAT ELSE THE ACCOUNT IS BOUND TO.  Before sending, ``DoLogin`` copies the
    account into the app singleton at +0xE4; after sending, into the global
    0x107A590, which 0x4C8E70 reads back through ``c_str()`` and which the
    login-response handler 0x4C57A0 clears (IAT 0xC3B2C8) when the response is
    not success.  The L"SaveLastLoginName" literal 0xF16C04 sits in the same
    state's UI path.  The same decoded account wstring is also the first field
    of the ``LoginVerifyVital`` frame the client sends to the GAME listener,
    which is why v141 carries it as the frozen literal
    ``b"\\x0B\\x68\\x48\\x04\\x00\\x00\\x00\\x0E\\x00\\x00\\x00"``.

WHAT THIS TOOL DOES NOT CLAIM.
  * Nothing about ``LSCN_LoginVitalRes`` beyond its name, hash and id slot.
  * Nothing about the outer envelope (id, version, mask, count); that was
    decoded elsewhere and is used here only to locate the nested body.
  * No claim that any *original* server validated either field.  The original
    server is gone and there was never a publish.  Our own server never reads
    either field: it answers 0x42BF by nested id alone and takes the
    ``login_name`` it persists from its own ``--token`` argument (default
    ``localtest``).
  * No claim about what the client does when the account it receives back
    differs from the one it sent.  That is the runtime question GT-020 asks.
  * The wire model is restricted to ASCII arguments; ``WideCharToMultiByte``
    under a non-ASCII code page is out of scope and the model refuses it.

Usage:  py -3 tools/pf_login_vital_req_static.py [path-to-GameClient.local.bin]
        py -3 tools/pf_login_vital_req_static.py --json
Exit 0 = every guard reproduced; nonzero = a guard drifted.
"""
from __future__ import annotations

import glob
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

V141_SRC = os.path.join(_ROOT, "current", "pf_login_game_server_v141.py")
STORE_SRC = os.path.join(_ROOT, "src", "pirateforce_foundation", "store.py")

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
_opt_magic = struct.unpack_from("<H", data, _opt)[0]
IMAGE_BASE = struct.unpack_from("<I", data, _opt + 28)[0]
_dd = _opt + (96 if _opt_magic == 0x10B else 112)
IMPORT_RVA, IMPORT_SIZE = struct.unpack_from("<II", data, _dd + 8)
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
    return data[off:off + n] if off is not None else b""


def dw(va):
    return struct.unpack("<I", rd(va, 4))[0]


def span_sha(a, b):
    return hashlib.sha256(rd(a, b - a)).hexdigest().upper()


def cstr(va, limit=256):
    off = va2off(va)
    if off is None:
        return ""
    end = data.find(b"\0", off, off + limit)
    return data[off:end].decode("latin1")


def wstr(va, limit=256):
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


def dis(va, size):
    return list(md.disasm(rd(va, size), va))


def dmap(va, size):
    return {i.address: (i.mnemonic, i.op_str) for i in dis(va, size)}


def imm32_refs(va):
    """Every .text position that carries this VA as a literal dword."""
    pat = struct.pack("<I", va)
    out = []
    start = _TLO
    while True:
        j = data.find(pat, start, _THI)
        if j < 0:
            return out
        out.append(off2va(j))
        start = j + 1


def call_xrefs(target):
    """Every ``E8 rel32`` call site in .text whose target is exactly ``target``."""
    out = []
    i = _TLO
    while i < _THI - 5:
        j = data.find(b"\xe8", i, _THI - 5)
        if j < 0:
            return out
        rel = struct.unpack_from("<i", data, j + 1)[0]
        src = off2va(j)
        if src is not None and (src + 5 + rel) == target:
            out.append(src)
        i = j + 1
    return out


def name_hash(name):
    """PF-NAMEID-HASH-001: u16 id = SUM_i (int16)((signed char)name[i] * (i+1))."""
    total = 0
    for index, byte in enumerate(name.encode("latin1")):
        signed = byte - 256 if byte > 127 else byte
        total = (total + ((signed * (index + 1)) & 0xFFFF)) & 0xFFFF
    return total


# --------------------------------------------------------------------------
# Import table.  "This slot is std::wstring's constructor" has to be evidence,
# not a guess about which of two identically shaped thunks is which.
# --------------------------------------------------------------------------
def _read_imports():
    table = {}
    if not IMPORT_RVA:
        return table
    index = 0
    while True:
        entry = va2off(IMAGE_BASE + IMPORT_RVA + index * 20)
        oft, _ts, _fc, name_rva, first_thunk = struct.unpack_from("<IIIII", data, entry)
        if name_rva == 0 and first_thunk == 0:
            return table
        dll = cstr(IMAGE_BASE + name_rva)
        thunk = oft or first_thunk
        slot = 0
        while True:
            value = dw(IMAGE_BASE + thunk + slot * 4)
            if value == 0:
                break
            iat = IMAGE_BASE + first_thunk + slot * 4
            if value & 0x80000000:
                table[iat] = (dll, "ord_%d" % (value & 0xFFFF))
            else:
                table[iat] = (dll, cstr(IMAGE_BASE + value + 2, 512))
            slot += 1
        index += 1


IAT = _read_imports()


def iat_name(slot):
    return IAT.get(slot, ("", ""))[1]


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
LIT_REQ_NAME = 0xF0B084          # "LSCN_LoginVitalReq"
LIT_RES_NAME = 0xF0B070          # "LSCN_LoginVitalRes"
REG_THUNK_REQ = 0xBEFDF0         # id registration thunk (PF-NAMEID shape)
REG_THUNK_RES = 0xBEFE10
ID_SLOT_REQ = 0x1082344
ID_SLOT_RES = 0x1082348
GET_ID_REQ = 0x4C5120            # mov ax, word ptr [ID_SLOT_REQ]; ret
VTABLE_REQ = 0xF16B34            # LSCN_LoginVitalReq vtable  (+0x00..+0x20)
VTABLE_STATE = 0xF16B58          # cStateLogin vtable         (+0x00..+0x28)
CTOR_REQ = 0x4C5090
DTOR_REQ = 0x4C5130
CLONE_REQ = 0x4C5900             # vt+0x14
SERIAL_REQ = 0x5F2780            # vt+0x18
SERIAL_WRITE = 0x5F278F
SERIAL_READ = 0x5F27AA
SERIAL_END = 0x5F27C5
INBOUND_NOOP = 0x710440          # vt+0x1C and vt+0x20 (the client only sends this)
CLASS_TOKEN_REQ = 0x1082338
TOKEN_THUNK_REQ = 0x4C5110       # vt+0x00 -> jmp 0x5F2770
TOKEN_ACCESSOR_REQ = 0x5F2770
TYPE_REG_REQ = 0xBEFE90
TYPEDESC_REQ = 0x1022DD0         # RTTI type descriptor, name at +8
TYPEDESC_REQ_PARENT = 0x101B16C
CLASS_TOKEN_STATE = 0x107A5AC
TYPE_REG_STATE = 0xBDBD70
TYPEDESC_STATE = 0x1022EF4
TYPEDESC_STATE_PARENT = 0x1022F60
PROTO_REGISTER = 0x5F2E60        # push 0x4C; call new; call ctor; register prototype
PROTO_NEW_SIZE_AT = 0x5F2E83
PROTO_CTOR_CALL = 0x5F2E9D
OBJ_SIZE = 0x4C
FIELD_ACCOUNT = 0x14             # std::wstring
FIELD_PASSWORD = 0x30            # std::string

OUT_WSTR = 0x89A810
OUT_STR = 0x89A6D0
IN_WSTR = 0x89A880
IN_STR = 0x89A740
TAG_WSTR = 0x48
TAG_STR = 0x44

WINMAIN = 0x40AE70
LIT_ACC = 0xF0A12C               # L"-acc"
LIT_PWD = 0xF0A120               # L"-pwd"
CMDLINE_OPT = 0xB00B20
G_FLAG = 0x102C5AC
G_ACC = 0x102C5B0
G_PWD = 0x102C5CC
WINMAIN_CMDLINE_BLOCK = (0x40B00D, 0x40B06E)

STATE_ENTER = 0x4C5AE0           # cStateLogin vt+0x10
DO_LOGIN = 0x4C5920
ON_LOGIN_RES = 0x4C57A0
DOLOGIN_FILL = (0x4C5A3D, 0x4C5A86)
POOL_ALLOC = 0x4C5690
POOL_HEAD = 0x107A498
SEND_VITAL = 0x5DD890
APP_SINGLETON = 0x4011A0
APP_ACCOUNT_OFFSET = 0xE4
G_LAST_ACCOUNT = 0x107A590
LIT_SAVE_LAST = 0xF16C04         # L"SaveLastLoginName"
LIT_PROTOTYPE_LOGIN1 = 0xF16B84  # L"Prototype_Login1"

HEX_DECODE = 0x89B070
HEX_LOOP = (0x89B194, 0x89B1C9)
HEXVAL = 0x89ACC0
HEXVAL_JT = 0x89AD38
HEXVAL_MAP = 0x89AD7C
HEXVAL_MAP_LEN = 0x37
HEXVAL_BIAS = 0x30
EMPTY_WSTR_LIT = 0xF0930C

PWD_NARROW = 0x88E200
NARROW_IMPL = 0x88E090
EMPTY_ANSI_LIT = 0xF0DA12

DLG_OK = 0x4D9630
DLG_AUTOFILL = 0x4D9990
DLG_WIDGET_ACCOUNT = 0x14
DLG_WIDGET_PASSWORD = 0x18

IAT_WSTR_CTOR = 0xC3B478
IAT_STR_CTOR = 0xC3B458
IAT_WSTR_ASSIGN = 0xC3B460
IAT_STR_ASSIGN = 0xC3B48C
IAT_WSTR_DTOR = 0xC3B488
IAT_STR_DTOR = 0xC3B498
IAT_WSTR_LEN = 0xC3B464
IAT_STR_LEN = 0xC3B470
IAT_WSTR_CSTR = 0xC3B484
IAT_WSTR_PUSHBACK = 0xC3B2B4
IAT_WSTR_SUBSTR = 0xC3B46C
IAT_WSTR_CLEAR = 0xC3B2C8
IAT_GETCOMMANDLINEW = 0xC3B208
IAT_WIDECHARTOMULTIBYTE = 0xC3B0EC

SPANS = {
    "serial": (SERIAL_REQ, SERIAL_END, "2AC9B84DCF1A5C9D21B51813D8728CC6"),
    "hexval_code": (HEXVAL, HEXVAL_JT, "5842234A4AC7C7A0B5279631020B7D31"),
    "hexval_jumptable": (HEXVAL_JT, HEXVAL_MAP, "22B552EB3A1B45DD583C2F220492422A"),
    "hexval_map": (HEXVAL_MAP, HEXVAL_MAP + HEXVAL_MAP_LEN,
                   "FBA01DEEEEB7E7E53A2C24CBFA8E5A4F"),
    "dologin_fill": (DOLOGIN_FILL[0], DOLOGIN_FILL[1],
                     "BB27E0D1D49B804ADB2B9B0D9ADB2789"),
    "winmain_cmdline": (WINMAIN_CMDLINE_BLOCK[0], WINMAIN_CMDLINE_BLOCK[1],
                        "35DDEF186779BED712D3E0B3A37A9F94"),
    "hex_decode_loop": (HEX_LOOP[0], HEX_LOOP[1],
                        "5490647B49969C2B927D891B9DFDAF24"),
    "registration_thunk": (REG_THUNK_REQ, REG_THUNK_REQ + 0x18,
                           "4F4D86CB6CCB9E34800F10D40709632E"),
}

# ==========================================================================
# 0. The image itself
# ==========================================================================
check("client image sha256 is the pinned build", sha == EXPECT_SHA, sha)
check("PE image base is 0x400000", IMAGE_BASE == 0x400000, hex(IMAGE_BASE))
check("the import directory resolved", len(IAT) > 500, "%d imports" % len(IAT))

# ==========================================================================
# 1. The class identity
# ==========================================================================
check("0xF0B084 is the literal LSCN_LoginVitalReq",
      cstr(LIT_REQ_NAME) == "LSCN_LoginVitalReq")
check("0xF0B070 is the literal LSCN_LoginVitalRes",
      cstr(LIT_RES_NAME) == "LSCN_LoginVitalRes")
check("the round-62 name hash of LSCN_LoginVitalReq is 0x42BF",
      name_hash("LSCN_LoginVitalReq") == 0x42BF,
      hex(name_hash("LSCN_LoginVitalReq")))
check("the round-62 name hash of LSCN_LoginVitalRes is 0x42E3",
      name_hash("LSCN_LoginVitalRes") == 0x42E3,
      hex(name_hash("LSCN_LoginVitalRes")))

_thunk = dmap(REG_THUNK_REQ, 0x18)
check("registration thunk pushes the LSCN_LoginVitalReq literal",
      _thunk[REG_THUNK_REQ] == ("push", hex(LIT_REQ_NAME)))
check("registration thunk calls the once-init 0x89C080",
      _thunk[REG_THUNK_REQ + 5] == ("call", "0x89c080"))
check("registration thunk calls the id-assign 0x89BD00",
      _thunk[REG_THUNK_REQ + 12] == ("call", "0x89bd00"))
check("registration thunk stores the id into slot 0x1082344",
      _thunk[REG_THUNK_REQ + 17] == ("mov", "word ptr [%s], ax" % hex(ID_SLOT_REQ)))
check("the LSCN_LoginVitalRes thunk stores into the adjacent slot 0x1082348",
      dmap(REG_THUNK_RES, 0x18)[REG_THUNK_RES + 17]
      == ("mov", "word ptr [%s], ax" % hex(ID_SLOT_RES)))
check("only two .text sites touch the LSCN_LoginVitalReq id slot",
      sorted(imm32_refs(ID_SLOT_REQ)) == [GET_ID_REQ + 2, REG_THUNK_REQ + 19],
      str([hex(x) for x in sorted(imm32_refs(ID_SLOT_REQ))]))

_getid = dmap(GET_ID_REQ, 0x10)
check("the id accessor is mov ax, word ptr [id slot]; ret",
      _getid[GET_ID_REQ] == ("mov", "ax, word ptr [%s]" % hex(ID_SLOT_REQ))
      and _getid[GET_ID_REQ + 6][0] == "ret")

_typereg = dmap(TYPE_REG_REQ, 0x40)
check("the type registrar 0xBEFE90 registers class token 0x1082338",
      _typereg[TYPE_REG_REQ + 23] == ("mov", "ecx, %s" % hex(CLASS_TOKEN_REQ)))
check("that registrar's RTTI descriptor names LSCN_LoginVitalReq",
      cstr(TYPEDESC_REQ + 8) == ".?AVLSCN_LoginVitalReq@@",
      cstr(TYPEDESC_REQ + 8))
check("its parent descriptor is VitalData",
      cstr(TYPEDESC_REQ_PARENT + 8) == ".?AVVitalData@@",
      cstr(TYPEDESC_REQ_PARENT + 8))
_statereg = dmap(TYPE_REG_STATE, 0x40)
check("the sibling registrar 0xBDBD70 registers class token 0x107A5AC",
      _statereg[TYPE_REG_STATE + 23] == ("mov", "ecx, %s" % hex(CLASS_TOKEN_STATE)))
check("and its RTTI descriptor names cStateLogin",
      cstr(TYPEDESC_STATE + 8) == ".?AVcStateLogin@@", cstr(TYPEDESC_STATE + 8))
check("cStateLogin's parent descriptor is CState",
      cstr(TYPEDESC_STATE_PARENT + 8) == ".?AVCState@@", cstr(TYPEDESC_STATE_PARENT + 8))

# Vtable identity: slot +0x00 returns the same class token the registrar used.
check("vtable+0x00 thunks to the class-token accessor",
      dmap(TOKEN_THUNK_REQ, 8)[TOKEN_THUNK_REQ] == ("jmp", hex(TOKEN_ACCESSOR_REQ)))
check("that accessor returns the LSCN_LoginVitalReq class token",
      dmap(TOKEN_ACCESSOR_REQ, 8)[TOKEN_ACCESSOR_REQ]
      == ("mov", "eax, %s" % hex(CLASS_TOKEN_REQ)))
check("vtable 0xF16B34 slot +0x00 is that thunk", dw(VTABLE_REQ) == TOKEN_THUNK_REQ)
check("vtable 0xF16B34 slot +0x10 is the id accessor",
      dw(VTABLE_REQ + 0x10) == GET_ID_REQ)
check("vtable 0xF16B34 slot +0x14 is the pooled clone",
      dw(VTABLE_REQ + 0x14) == CLONE_REQ)
check("vtable 0xF16B34 slot +0x18 is Serial", dw(VTABLE_REQ + 0x18) == SERIAL_REQ)
check("vtable slots +0x1C and +0x20 are the shared inbound no-op 0x710440",
      dw(VTABLE_REQ + 0x1C) == INBOUND_NOOP and dw(VTABLE_REQ + 0x20) == INBOUND_NOOP)
check("the next vtable (cStateLogin's) starts right after slot +0x20",
      VTABLE_STATE == VTABLE_REQ + 0x24)

_state_vt_installers = []
for _v in imm32_refs(VTABLE_STATE):
    for _back in range(1, 9):
        _ins = dmap(_v - _back, 12).get(_v - _back)
        if (_ins and _ins[0] == "mov" and "ptr [" in _ins[1]
                and _ins[1].endswith(hex(VTABLE_STATE))):
            _state_vt_installers.append(_v - _back)
            break
check("cStateLogin's vtable is installed by its own constructor",
      len(_state_vt_installers) >= 1,
      str([hex(x) for x in _state_vt_installers]))

# ==========================================================================
# 2. The object: exactly two string members
# ==========================================================================
_ctor = dmap(CTOR_REQ, 0x78)
check("the constructor installs vtable 0xF16B34",
      _ctor[0x4C50D6] == ("mov", "dword ptr [esi], %s" % hex(VTABLE_REQ)))
check("the constructor builds a member at +0x14 with ecx = this+0x14",
      _ctor[0x4C50CF] == ("lea", "ecx, [esi + %s]" % hex(FIELD_ACCOUNT)))
check("that member's constructor is MSVCP90 basic_string<wchar_t>::ctor()",
      _ctor[0x4C50DC] == ("call", "dword ptr [%s]" % hex(IAT_WSTR_CTOR))
      and "basic_string@_W" in iat_name(IAT_WSTR_CTOR),
      iat_name(IAT_WSTR_CTOR)[:44])
check("the constructor builds a member at +0x30 with ecx = this+0x30",
      _ctor[0x4C50E2] == ("lea", "ecx, [esi + %s]" % hex(FIELD_PASSWORD)))
check("that member's constructor is MSVCP90 basic_string<char>::ctor()",
      _ctor[0x4C50EA] == ("call", "dword ptr [%s]" % hex(IAT_STR_CTOR))
      and "basic_string@D" in iat_name(IAT_STR_CTOR),
      iat_name(IAT_STR_CTOR)[:44])
_dtor = dmap(DTOR_REQ, 0x78)
check("the destructor destroys the +0x30 std::string",
      _dtor[0x4C515E] == ("lea", "ecx, [esi + 0x30]")
      and _dtor[0x4C5169] == ("call", "dword ptr [%s]" % hex(IAT_STR_DTOR))
      and "basic_string@D" in iat_name(IAT_STR_DTOR))
check("the destructor destroys the +0x14 std::wstring",
      _dtor[0x4C516F] == ("lea", "ecx, [esi + 0x14]")
      and _dtor[0x4C5177] == ("call", "dword ptr [%s]" % hex(IAT_WSTR_DTOR))
      and "basic_string@_W" in iat_name(IAT_WSTR_DTOR))
_proto = dmap(PROTO_REGISTER, 0x50)
check("the prototype registrar allocates 0x4C bytes for this class",
      _proto[PROTO_NEW_SIZE_AT] == ("push", hex(OBJ_SIZE)))
check("and runs this constructor on that allocation",
      _proto[PROTO_CTOR_CALL] == ("call", hex(CTOR_REQ)))
check("the constructor has exactly three callers (prototype plus two class thunks)",
      len(call_xrefs(CTOR_REQ)) == 3, str([hex(x) for x in call_xrefs(CTOR_REQ)]))

# ==========================================================================
# 3. Serial: the frame body, both directions, nothing else
# ==========================================================================
_ser = dmap(SERIAL_REQ, SERIAL_END - SERIAL_REQ)
check("Serial branches on its direction byte at [esp+8]",
      _ser[SERIAL_REQ] == ("cmp", "byte ptr [esp + 8], 0")
      and _ser[0x5F278D] == ("je", hex(SERIAL_READ)))
check("write path field 1 is this+0x14 through the tag-0x48 writer",
      _ser[SERIAL_WRITE] == ("lea", "eax, [esi + 0x14]")
      and _ser[0x5F2795] == ("call", hex(OUT_WSTR)))
check("write path field 2 is this+0x30 through the tag-0x44 writer",
      _ser[0x5F279A] == ("add", "esi, 0x30")
      and _ser[0x5F27A0] == ("call", hex(OUT_STR)))
check("read path field 1 is this+0x14 through the tag-0x48 reader",
      _ser[SERIAL_READ] == ("lea", "ecx, [esi + 0x14]")
      and _ser[0x5F27B0] == ("call", hex(IN_WSTR)))
check("read path field 2 is this+0x30 through the tag-0x44 reader",
      _ser[0x5F27B5] == ("add", "esi, 0x30")
      and _ser[0x5F27BB] == ("call", hex(IN_STR)))
_ser_calls = sorted(op for mn, op in _ser.values() if mn == "call")
check("Serial makes exactly four calls and they are the four codec helpers",
      _ser_calls == sorted([hex(OUT_WSTR), hex(OUT_STR), hex(IN_WSTR), hex(IN_STR)]),
      str(_ser_calls))
_ser_fields = sorted({m for mn, op in _ser.values() if mn in ("lea", "add")
                      for m in re.findall(r"0x[0-9a-f]+", op)})
check("Serial touches exactly two object offsets, 0x14 and 0x30",
      _ser_fields == ["0x14", "0x30"], str(_ser_fields))
check("both directions return with ret 8",
      [mn for mn, _ in _ser.values()].count("ret") == 2)

_ow = dmap(OUT_WSTR, 0x40)
check("the tag-0x48 writer measures wstring::length()",
      _ow[0x89A81B] == ("call", "dword ptr [%s]" % hex(IAT_WSTR_LEN))
      and "?length@" in iat_name(IAT_WSTR_LEN) and "@_W" in iat_name(IAT_WSTR_LEN))
check("the tag-0x48 writer doubles that length into a byte count",
      _ow[0x89A828] == ("add", "edi, edi"))
check("the tag-0x48 writer emits tag 0x48", _ow[0x89A833] == ("push", hex(TAG_WSTR)))
_ostr = dmap(OUT_STR, 0x40)
check("the tag-0x44 writer measures string::length()",
      _ostr[0x89A6DB] == ("call", "dword ptr [%s]" % hex(IAT_STR_LEN))
      and "?length@" in iat_name(IAT_STR_LEN) and "@D" in iat_name(IAT_STR_LEN))
check("the tag-0x44 writer emits tag 0x44", _ostr[0x89A6F1] == ("push", hex(TAG_STR)))
check("the inbound wstring reader is the tag-0x48 twin",
      dmap(IN_WSTR, 0x30)[0x89A89C] == ("push", hex(TAG_WSTR)))
check("the inbound string reader is the tag-0x44 twin",
      dmap(IN_STR, 0x30)[0x89A75C] == ("push", hex(TAG_STR)))

# ==========================================================================
# 4. The producer: which field is the account, and where both values come from
# ==========================================================================
_win = dmap(WINMAIN, 0x420)
check('WinMain carries the L"-acc" literal', wstr(LIT_ACC) == "-acc")
check('WinMain carries the L"-pwd" literal', wstr(LIT_PWD) == "-pwd")
check("the -acc option is read through the command-line parser 0xB00B20",
      _win[0x40B015] == ("push", hex(LIT_ACC))
      and _win[0x40B022] == ("call", hex(CMDLINE_OPT)))
check("the -pwd option is read through the same parser",
      _win[0x40B033] == ("push", hex(LIT_PWD))
      and _win[0x40B038] == ("call", hex(CMDLINE_OPT)))
check("that parser's source is GetCommandLineW",
      dmap(CMDLINE_OPT, 0x60)[0xB00B66]
      == ("call", "dword ptr [%s]" % hex(IAT_GETCOMMANDLINEW))
      and iat_name(IAT_GETCOMMANDLINEW) == "GetCommandLineW")
check("-pwd is only consulted when -acc was present (both branches skip together)",
      _win[0x40B02C] == ("je", "0x40b06e") and _win[0x40B042] == ("je", "0x40b06e"))
check("both present sets the flag byte 0x102C5AC to 1",
      _win[0x40B051] == ("mov", "byte ptr [%s], 1" % hex(G_FLAG)))
check("the account value lands in the global 0x102C5B0",
      _win[0x40B04C] == ("mov", "ecx, %s" % hex(G_ACC))
      and _win[0x40B058] == ("call", "dword ptr [%s]" % hex(IAT_WSTR_ASSIGN)))
check("the password value lands in the global 0x102C5CC",
      _win[0x40B063] == ("mov", "ecx, %s" % hex(G_PWD))
      and _win[0x40B068] == ("call", "dword ptr [%s]" % hex(IAT_WSTR_ASSIGN)))

_enter = dmap(STATE_ENTER, 0x140)
check("cStateLogin's state-entry hook is vtable 0xF16B58 slot +0x10",
      dw(VTABLE_STATE + 0x10) == STATE_ENTER)
check("the state-entry hook branches on the command-line flag",
      _enter[0x4C5B18] == ("cmp", "byte ptr [%s], 0" % hex(G_FLAG))
      and _enter[0x4C5B1F] == ("je", "0x4c5be8"))
check("with the flag set it calls DoLogin(account global, password global)",
      _enter[0x4C5B25] == ("push", hex(G_PWD))
      and _enter[0x4C5B2A] == ("push", hex(G_ACC))
      and _enter[0x4C5B2F] == ("call", hex(DO_LOGIN)))
check('with the flag clear it opens the L"Prototype_Login1" dialog instead',
      _enter[0x4C5BF4] == ("push", hex(LIT_PROTOTYPE_LOGIN1))
      and wstr(LIT_PROTOTYPE_LOGIN1) == "Prototype_Login1")
check("DoLogin has exactly two callers: the state hook and the dialog OK handler",
      sorted(call_xrefs(DO_LOGIN)) == [0x4C5B2F, 0x4D9769],
      str([hex(x) for x in sorted(call_xrefs(DO_LOGIN))]))

_do = dmap(DO_LOGIN, 0x1C0)
check("DoLogin takes arg0 (account) into edi and arg1 (password) into ebp",
      _do[0x4C5952] == ("mov", "edi, dword ptr [esp + 0x7c]")
      and _do[0x4C5956] == ("mov", "ebp, dword ptr [esp + 0x80]"))
check("DoLogin narrows arg1 to ANSI in a local",
      _do[0x4C5999] == ("push", "ebp") and _do[0x4C599B] == ("call", hex(PWD_NARROW)))
_narrow = dmap(NARROW_IMPL, 0x90)
check("that narrowing is wstring::c_str() plus WideCharToMultiByte, no hash step",
      dmap(PWD_NARROW, 0x40)[0x88E22E] == ("call", "dword ptr [%s]" % hex(IAT_WSTR_CSTR))
      and _narrow[0x88E100] == ("mov", "ebp, dword ptr [%s]" % hex(IAT_WIDECHARTOMULTIBYTE))
      and iat_name(IAT_WIDECHARTOMULTIBYTE) == "WideCharToMultiByte")
check("DoLogin's command-line branch rewrites arg0 through the hex decoder",
      _do[0x4C59A7] == ("cmp", "byte ptr [%s], bl" % hex(G_FLAG))
      and _do[0x4C5A19] == ("call", hex(HEX_DECODE))
      and _do[0x4C5A22] == ("mov", "ecx, edi")
      and _do[0x4C5A29] == ("call", "dword ptr [%s]" % hex(IAT_WSTR_ASSIGN)))
check("DoLogin pool-allocates the request before filling it",
      _do[0x4C5A50] == ("push", "0xf0a90c")
      and _do[0x4C5A55] == ("mov", "ecx, %s" % hex(POOL_HEAD))
      and _do[0x4C5A5A] == ("call", hex(POOL_ALLOC)))
check("DoLogin assigns the ACCOUNT wstring into request+0x14",
      _do[0x4C5A61] == ("push", "edi")
      and _do[0x4C5A62] == ("lea", "ecx, [esi + %s]" % hex(FIELD_ACCOUNT))
      and _do[0x4C5A65] == ("call", "dword ptr [%s]" % hex(IAT_WSTR_ASSIGN)))
check("DoLogin assigns the narrowed PASSWORD string into request+0x30",
      _do[0x4C5A6F] == ("push", "eax")
      and _do[0x4C5A70] == ("lea", "ecx, [esi + %s]" % hex(FIELD_PASSWORD))
      and _do[0x4C5A73] == ("call", "dword ptr [%s]" % hex(IAT_STR_ASSIGN)))
check("DoLogin then sends that request object", _do[0x4C5A81] == ("call", hex(SEND_VITAL)))
check("DoLogin copies the account into the app singleton at +0xE4",
      _do[0x4C5A3D] == ("call", hex(APP_SINGLETON))
      and _do[0x4C5A43] == ("lea", "ecx, [eax + %s]" % hex(APP_ACCOUNT_OFFSET)))
check("DoLogin copies the account into the last-login global 0x107A590",
      _do[0x4C5A87] == ("mov", "ecx, %s" % hex(G_LAST_ACCOUNT)))
check("the login-response handler clears that global when the response is not success",
      dmap(ON_LOGIN_RES, 0x160)[0x4C58E5]
      == ("call", "dword ptr [%s]" % hex(IAT_WSTR_CLEAR))
      and "?clear@" in iat_name(IAT_WSTR_CLEAR))
check('the neighbouring literal is L"SaveLastLoginName"',
      wstr(LIT_SAVE_LAST) == "SaveLastLoginName", wstr(LIT_SAVE_LAST))

_dlg = dmap(DLG_OK, 0x100)
check("the dialog OK handler reads widget +0x14 first (the account box)",
      _dlg[0x4D96CB] == ("mov", "ecx, dword ptr [esi + %s]" % hex(DLG_WIDGET_ACCOUNT))
      and _dlg[0x4D96D0] == ("mov", "eax, dword ptr [edx + 0x124]"))
check("the dialog OK handler reads widget +0x18 second (the password box)",
      _dlg[0x4D96E3] == ("mov", "ecx, dword ptr [esi + %s]" % hex(DLG_WIDGET_PASSWORD))
      and _dlg[0x4D96E8] == ("mov", "eax, dword ptr [edx + 0x124]"))
_auto = dmap(DLG_AUTOFILL, 0x70)
check("the dialog auto-fill pushes the account global into widget +0x14",
      _auto[0x4D99A5] == ("mov", "eax, dword ptr [esi + %s]" % hex(DLG_WIDGET_ACCOUNT))
      and _auto[0x4D99AB] == ("mov", "ecx, %s" % hex(G_ACC)))
check("the dialog auto-fill pushes the password global into widget +0x18",
      _auto[0x4D99C2] == ("mov", "eax, dword ptr [esi + %s]" % hex(DLG_WIDGET_PASSWORD))
      and _auto[0x4D99C7] == ("mov", "ecx, %s" % hex(G_PWD)))
check("the UI-path ANSI prefix constant 0xF0DA12 is the empty string",
      cstr(EMPTY_ANSI_LIT) == "")

# ==========================================================================
# 5. The hex decoder, rebuilt from the image
# ==========================================================================
_hv = dmap(HEXVAL, HEXVAL_JT - HEXVAL)
check("hexval loads its argument as a 16-bit character",
      _hv[HEXVAL] == ("movzx", "eax, word ptr [esp + 4]"))
check("hexval biases by -0x30 and bounds-checks against 0x36",
      _hv[0x89ACC5] == ("add", "eax, -%s" % hex(HEXVAL_BIAS))
      and _hv[0x89ACC8] == ("cmp", "eax, %s" % hex(HEXVAL_MAP_LEN - 1)))
check("hexval indexes the 0x37-byte map at 0x89AD7C",
      _hv[0x89ACCD] == ("movzx", "eax, byte ptr [eax + %s]" % hex(HEXVAL_MAP)))
check("hexval dispatches through the jump table at 0x89AD38",
      _hv[0x89ACD4] == ("jmp", "dword ptr [eax*4 + %s]" % hex(HEXVAL_JT)))

# Rebuild the table.  Every jump-table target is either `mov eax,imm; ret` or
# `xor eax,eax; ret`; nothing is assumed about what those values mean.
_JT_VALUES = []
for _k in range((HEXVAL_MAP - HEXVAL_JT) // 4):
    _target = dw(HEXVAL_JT + 4 * _k)
    _first = dmap(_target, 8).get(_target)
    if _first == ("xor", "eax, eax"):
        _JT_VALUES.append(0)
    elif _first and _first[0] == "mov" and _first[1].startswith("eax, "):
        _JT_VALUES.append(int(_first[1].split(", ")[1], 16))
    else:
        _JT_VALUES.append(None)
check("every hexval jump-table target is a constant return",
      all(v is not None for v in _JT_VALUES), str(_JT_VALUES))
check("the hexval jump table has 17 entries returning 0..15 plus a zero default",
      _JT_VALUES == [0] + list(range(1, 16)) + [0], str(_JT_VALUES))

_HEX_MAP = list(rd(HEXVAL_MAP, HEXVAL_MAP_LEN))


def hexval(ch):
    """The client's 0x89ACC0, re-implemented from the bytes read above."""
    index = ord(ch) - HEXVAL_BIAS
    if index < 0 or index > HEXVAL_MAP_LEN - 1:
        return 0
    return _JT_VALUES[_HEX_MAP[index]]


_HEX_MISMATCH = []
for _cp in range(0x10000):
    _c = chr(_cp)
    _expected = int(_c, 16) if _c in "0123456789abcdefABCDEF" else 0
    if hexval(_c) != _expected:
        _HEX_MISMATCH.append(_cp)
check("the recovered table is exactly hexadecimal over all 65536 characters",
      not _HEX_MISMATCH, "%d mismatches" % len(_HEX_MISMATCH))

_dec = dmap(HEX_DECODE, 0x1B0)
check("the decoder returns the empty wide literal for an empty input",
      _dec[0x89B0BA] == ("cmp", "dword ptr [eax + 0x14], esi")
      and _dec[0x89B0BF] == ("push", hex(EMPTY_WSTR_LIT))
      and wstr(EMPTY_WSTR_LIT) == "")
check("the decoder drops the last character when the length is odd",
      _dec[0x89B0F5] == ("test", "al, 1")
      and _dec[0x89B105] == ("call", "dword ptr [%s]" % hex(IAT_WSTR_SUBSTR))
      and "?substr@" in iat_name(IAT_WSTR_SUBSTR))
_loop = dmap(HEX_LOOP[0], HEX_LOOP[1] - HEX_LOOP[0])
check("the decoder loop reads s[i] and s[i+1] and calls hexval on both",
      _loop[0x89B194] == ("movzx", "eax, word ptr [edi + esi*2]")
      and _loop[0x89B199] == ("call", hex(HEXVAL))
      and _loop[0x89B19E] == ("movzx", "edx, word ptr [edx + esi*2 + 2]")
      and _loop[0x89B1A9] == ("call", hex(HEXVAL)))
check("the decoder combines them as (high << 4) + low",
      _loop[0x89B1A6] == ("shl", "ecx, 4") and _loop[0x89B1AE] == ("add", "ecx, eax"))
check("the decoder appends each result with wstring::operator+=(wchar_t)",
      _loop[0x89B1B8] == ("call", "dword ptr [%s]" % hex(IAT_WSTR_PUSHBACK))
      and "??Y?$basic_string@_W" in iat_name(IAT_WSTR_PUSHBACK))
check("the decoder advances two characters per output character",
      _loop[0x89B1C2] == ("add", "esi, 2"))
check("the hex decoder is called from exactly one place, DoLogin",
      call_xrefs(HEX_DECODE) == [0x4C5A19],
      str([hex(x) for x in call_xrefs(HEX_DECODE)]))

# ==========================================================================
# 6. The model, and the corpus it has to reproduce
# ==========================================================================
NESTED_ID_REQ = 0x42BF


def decode_hex_wstring(argument: str) -> str:
    """0x89B070, re-implemented.  Maps a -acc argument to the account wstring."""
    if not argument:
        return ""
    trimmed = argument[:-1] if len(argument) & 1 else argument
    if not trimmed:
        return ""
    return "".join(
        chr(((hexval(trimmed[i]) << 4) + hexval(trimmed[i + 1])) & 0xFFFF)
        for i in range(0, len(trimmed), 2)
    )


def encode_hex_argument(account: str) -> str:
    """The inverse: the -acc argument that produces this account name."""
    if any(ord(c) > 0xFF for c in account):
        raise ValueError("one wide character per two hex digits: 0x00..0xFF only")
    return "".join("%02X" % ord(c) for c in account)


def wstring_field(text: str) -> bytes:
    """0x89A810: tag 0x48, u32 byte length, UTF-16LE payload."""
    body = text.encode("utf-16-le")
    return bytes([TAG_WSTR]) + struct.pack("<I", len(body)) + body


def string_field(text: str) -> bytes:
    """0x89A6D0: tag 0x44, u32 byte length, raw payload."""
    if not text.isascii():
        raise ValueError("the ANSI model is restricted to ASCII arguments")
    return bytes([TAG_STR]) + struct.pack("<I", len(text)) + text.encode("ascii")


def login_vital_req_body(acc_argument: str, pwd_argument: str) -> bytes:
    """The Serial output of LSCN_LoginVitalReq for one pair of client arguments."""
    return wstring_field(decode_hex_wstring(acc_argument)) + string_field(pwd_argument)


def login_vital_req_nested(acc_argument: str, pwd_argument: str) -> bytes:
    """The nested block as the golden decoder prints it: id, version, body."""
    return (
        bytes([0x12]) + struct.pack("<H", NESTED_ID_REQ) + bytes([0x0B, 0x00])
        + login_vital_req_body(acc_argument, pwd_argument)
    )


NESTED_HEADER_LEN = 5


def split_body(body: bytes):
    """Parse a Serial body back into (account_utf16_bytes, password_bytes)."""
    if len(body) < 5 or body[0] != TAG_WSTR:
        raise ValueError("field 1 is not tag 0x48")
    n = struct.unpack_from("<I", body, 1)[0]
    account = body[5:5 + n]
    if len(account) != n:
        raise ValueError("field 1 is truncated")
    rest = body[5 + n:]
    if len(rest) < 5 or rest[0] != TAG_STR:
        raise ValueError("field 2 is not tag 0x44")
    m = struct.unpack_from("<I", rest, 1)[0]
    password = rest[5:5 + m]
    if len(password) != m or len(rest) != 5 + m:
        raise ValueError("field 2 is truncated or the body has a tail")
    return account, password


JOB_ACC_ARGUMENT = "test"        # every launcher job in this project: -acc test
JOB_PWD_ARGUMENT = "test"        # every launcher job in this project: -pwd test
GOLDEN_NESTED = login_vital_req_nested(JOB_ACC_ARGUMENT, JOB_PWD_ARGUMENT)
GOLDEN_BODY = login_vital_req_body(JOB_ACC_ARGUMENT, JOB_PWD_ARGUMENT)
PROBE_ACC_ARGUMENT = "4142"      # decodes to L"AB": same length, two bytes apart
PROBE_BODY = login_vital_req_body(PROBE_ACC_ARGUMENT, JOB_PWD_ARGUMENT)

check("the model turns -acc test into the two wide characters U+000E U+0000",
      [ord(c) for c in decode_hex_wstring("test")] == [0x000E, 0x0000],
      str([ord(c) for c in decode_hex_wstring("test")]))
check("so the account field of every job's login frame is 48 04 00 00 00 0E 00 00 00",
      wstring_field(decode_hex_wstring("test")) == bytes.fromhex("48040000000E000000"),
      wstring_field(decode_hex_wstring("test")).hex(" ").upper())
check("and the password field is 44 04 00 00 00 74 65 73 74",
      string_field("test") == bytes.fromhex("4404000000") + b"test",
      string_field("test").hex(" ").upper())
check("a hex-encoded argument round-trips to a readable account name",
      decode_hex_wstring("74657374") == "test" and decode_hex_wstring("4142") == "AB")
check("the inverse helper reproduces those arguments",
      encode_hex_argument("test") == "74657374" and encode_hex_argument("AB") == "4142")
check("an odd-length argument loses its last character, as the binary does",
      decode_hex_wstring("41424") == "AB" and decode_hex_wstring("4") == "")
check("an empty argument yields an empty account field",
      decode_hex_wstring("") == "" and wstring_field("") == bytes.fromhex("4800000000"))
check("the -acc 4142 probe keeps the frame length identical",
      len(PROBE_BODY) == len(GOLDEN_BODY),
      "%d vs %d" % (len(PROBE_BODY), len(GOLDEN_BODY)))
check("the -acc 4142 probe changes exactly two bytes of the body",
      sum(1 for a, b in zip(PROBE_BODY, GOLDEN_BODY) if a != b) == 2,
      str([i for i, (a, b) in enumerate(zip(PROBE_BODY, GOLDEN_BODY)) if a != b]))

# ---- the archived login corpus -------------------------------------------
def _decompressed_blocks(text):
    """Every DECOMPRESSED hexdump in one capture file, as raw bytes."""
    blocks = []
    for match in re.finditer(r"DECOMPRESSED \d+\n((?:[0-9A-F]{8}  .*\n)+)", text):
        raw = bytearray()
        for line in match.group(1).splitlines():
            for token in line[10:58].split():
                raw.append(int(token, 16))
        blocks.append(bytes(raw))
    return blocks


LOGIN_CAPTURES = sorted(
    glob.glob(os.path.join(_ROOT, "**", "LOGIN_*.txt"), recursive=True)
)
CORPUS_ROWS = []
for _path in LOGIN_CAPTURES:
    _text = open(_path, encoding="utf-8", errors="replace").read()
    for _block in _decompressed_blocks(_text):
        _at = _block.find(b"\x12\xbf\x42")
        if _at < 0:
            continue
        CORPUS_ROWS.append((_path, _block[_at:]))
        break

check("the archived login corpus is not empty", len(CORPUS_ROWS) > 0,
      "%d captures carry a 0x42BF frame" % len(CORPUS_ROWS))
_PARSE_FAILURES = []
for _path, _nested in CORPUS_ROWS:
    try:
        split_body(_nested[NESTED_HEADER_LEN:])
    except ValueError as exc:
        _PARSE_FAILURES.append((os.path.basename(_path), str(exc)))
check("every archived 0x42BF frame parses under the recovered field model",
      not _PARSE_FAILURES, str(_PARSE_FAILURES[:3]))

DISTINCT_NESTED = sorted({row[1] for row in CORPUS_ROWS})
DISTINCT_ACCOUNTS = sorted(
    {split_body(n[NESTED_HEADER_LEN:])[0] for n in DISTINCT_NESTED}
)
DISTINCT_PASSWORDS = sorted(
    {split_body(n[NESTED_HEADER_LEN:])[1] for n in DISTINCT_NESTED}
)
check("the whole archived corpus reproduces byte-exact from the model of the "
      "arguments every job uses",
      DISTINCT_NESTED == [GOLDEN_NESTED],
      " / ".join(n.hex(" ").upper() for n in DISTINCT_NESTED))
check("which is the audit's G8 observation restated: one distinct account value",
      len(DISTINCT_ACCOUNTS) == 1 and len(DISTINCT_PASSWORDS) == 1,
      "%d accounts, %d passwords" % (len(DISTINCT_ACCOUNTS), len(DISTINCT_PASSWORDS)))

# ---- the same account value on the game listener --------------------------
VERIFY_PREFIX = bytes.fromhex("0B68") + wstring_field(decode_hex_wstring(JOB_ACC_ARGUMENT))
GAME_CAPTURES = sorted(glob.glob(os.path.join(_ROOT, "capture_v141", "GAME_*.txt")))
_verify_hits = 0
for _path in GAME_CAPTURES:
    _text = open(_path, encoding="utf-8", errors="replace").read()
    for _block in _decompressed_blocks(_text):
        if VERIFY_PREFIX in _block:
            _verify_hits += 1
            break
check("the same decoded account also opens LoginVerifyVital on the game listener",
      _verify_hits > 0,
      "%d of %d capture_v141 GAME files" % (_verify_hits, len(GAME_CAPTURES)))

# ==========================================================================
# 7. What our own server does with all this (read-only)
# ==========================================================================
V141_TEXT = open(V141_SRC, encoding="utf-8").read()
V141_ACK_LITERAL = r'b"\x0B\x68\x48\x04\x00\x00\x00\x0E\x00\x00\x00"'
check("v141 carries the decoded account as a frozen literal in its game-login ack",
      V141_ACK_LITERAL in V141_TEXT)
check("that literal is exactly the model's encoding of decode_hex(-acc test)",
      bytes.fromhex("0B68") + wstring_field(decode_hex_wstring("test"))
      == bytes.fromhex("0B6848040000000E000000"))
check("v141 answers 0x42BF by nested id alone and never reads its payload",
      "parsed.nested_id == LOGIN_REQ" in V141_TEXT
      and "parse_login_req" not in V141_TEXT
      and len(re.findall(r"\bLOGIN_REQ\b", V141_TEXT)) == 3,
      "%d LOGIN_REQ mentions" % len(re.findall(r"\bLOGIN_REQ\b", V141_TEXT)))
check("v141 takes the account name it persists from its own --token argument",
      'ap.add_argument("--token", default="localtest")' in V141_TEXT)
STORE_TEXT = open(STORE_SRC, encoding="utf-8").read()
check("the store creates an accounts row on demand, so no account has to be "
      "prepared in advance",
      "INSERT OR IGNORE INTO accounts(login_name,created_at)" in STORE_TEXT)

# ==========================================================================
# 8. Tamper-evident spans
# ==========================================================================
for _label, (_a, _b, _pin) in sorted(SPANS.items()):
    check("span %s (0x%X..0x%X) is unchanged" % (_label, _a, _b),
          span_sha(_a, _b).startswith(_pin), span_sha(_a, _b)[:32])

# ==========================================================================
# Counts block (the report is pinned to these, never to hand-typed numbers)
# ==========================================================================
GUARDS_TOTAL = len(RESULTS)
GUARDS_FAILED = [n for n, ok in RESULTS if not ok]

COUNTS = {
    "measured_at_head": "dd1a66c",
    "client_sha256": sha,
    "guards_total": GUARDS_TOTAL,
    "wire_id": "0x%04X" % NESTED_ID_REQ,
    "object_size": OBJ_SIZE,
    "serial_field_count": 2,
    "account_field_offset": "0x%02X" % FIELD_ACCOUNT,
    "account_field_type": "std::wstring",
    "account_field_wire_tag": "0x%02X" % TAG_WSTR,
    "password_field_offset": "0x%02X" % FIELD_PASSWORD,
    "password_field_type": "std::string",
    "password_field_wire_tag": "0x%02X" % TAG_STR,
    "account_sources": ["-acc argument (hex-decoded)",
                        "Prototype_Login1 edit box +0x14"],
    "password_sources": ["-pwd argument", "Prototype_Login1 edit box +0x18"],
    "password_is_hashed": False,
    "hexval_table_entries": len(_JT_VALUES),
    "hexval_map_bytes": HEXVAL_MAP_LEN,
    "hexval_mismatches_over_65536_chars": len(_HEX_MISMATCH),
    "archived_login_captures": len(LOGIN_CAPTURES),
    "archived_login_captures_with_0x42bf": len(CORPUS_ROWS),
    "distinct_request_bodies": len(DISTINCT_NESTED),
    "distinct_account_values": len(DISTINCT_ACCOUNTS),
    "distinct_password_values": len(DISTINCT_PASSWORDS),
    "golden_nested_hex": GOLDEN_NESTED.hex(" ").upper(),
    "golden_account_wchars": [ord(c) for c in decode_hex_wstring(JOB_ACC_ARGUMENT)],
    "probe_argument": PROBE_ACC_ARGUMENT,
    "probe_account_name": decode_hex_wstring(PROBE_ACC_ARGUMENT),
    "probe_body_length_delta": len(PROBE_BODY) - len(GOLDEN_BODY),
    "probe_bytes_changed": sum(1 for a, b in zip(PROBE_BODY, GOLDEN_BODY) if a != b),
    "game_captures_with_the_same_account": _verify_hits,
    "dologin_callers": len(call_xrefs(DO_LOGIN)),
    "hex_decode_callers": len(call_xrefs(HEX_DECODE)),
}

if AS_JSON:
    print(json.dumps(COUNTS, indent=2, sort_keys=True))
else:
    print()
    print("LSCN_LoginVitalReq 0x42BF, as the client builds it:")
    print("  field 1  this+0x14  std::wstring  wire tag 0x48  = THE ACCOUNT")
    print("           value = decode_hex(-acc <arg>), or the login dialog's box +0x14")
    print("  field 2  this+0x30  std::string   wire tag 0x44  = THE PASSWORD, cleartext")
    print("           value = WideCharToMultiByte(-pwd <arg>), or the box +0x18")
    print("  nothing else is serialized, in either direction")
    print()
    print("  every job in this project passes -acc test -pwd test, and")
    print("  decode_hex('test') = U+000E U+0000, which is why all %d archived"
          % len(CORPUS_ROWS))
    print("  captures show 48 04 00 00 00 0E 00 00 00 and never L'test'.")
    print()
    print("  -acc 4142 would put L'AB' there: same length, two bytes different.")
    print("  -acc 74657374 would put the literal name L'test' there.")
    print()
    print("guards run: %d, failed: %d" % (GUARDS_TOTAL, len(GUARDS_FAILED)))

if GUARDS_FAILED:
    if not AS_JSON:
        print("RESULT: %d guard(s) drifted: %s" % (len(GUARDS_FAILED), GUARDS_FAILED))
    sys.exit(1)
if not AS_JSON:
    print("RESULT: all LSCN_LoginVitalReq static guards reproduced (exit 0)")
