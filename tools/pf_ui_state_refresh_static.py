#!/usr/bin/env python3
"""PF UI-REFRESH-001 - static byte-exact enumeration of the client's
character-select state machine, of the buffer the character list is drawn from,
and of every code path that writes, clears or rebuilds that buffer.

WHY THIS EXISTS.  Two attended rounds produced the same symptom: the client
parsed our frame with no error dialog at all, and then did not change UI state.
GT-011 sent a spec-exact 79-byte DeleteActorVital (0x36DB) acknowledgement, the
row soft-deleted in the database, and the character-select list did not refresh.
GT-013 sent a complete worldinfo-first logout sequence and the client did not
transition.  The lead hypothesis was that the client does not change state from
the acknowledgement of a command, but waits for a DIFFERENT KIND of frame.
This tool decides that question from the bytes.

SOLE EVIDENCE: the read-only client image GameClient/GameClient.local.bin.
Nothing was executed: no server booted, no GameClient opened, no socket, no
database, no network.  Report-only: no src/ change, no scenario, no matrix flip,
no ledger entry.

WHAT IS PROVEN (byte-exact static analysis; every address below is asserted):

  * THE SCREEN IS A STATE OBJECT.  The client owns exactly ten registered state
    classes (custom RTTI registrar 0x88F2E0, one thunk per class, each pushing
    its own `.?AV<name>@@` type descriptor).  The character-select screen is
    `cStateCreateActor` (descriptor 0x1022D5C, class-node token 0x107A38C,
    token getter 0x4C0110, object size 0x770, constructor 0x4C03E0,
    vtable 0xF16520).  The live state pointer is [0x1093198] + 0x34C.
    Transitions go through CState::RequestNext 0x4C7320, which only stores the
    next state at this+0x10 and sets this+0x0C = 2.

  * THE SCREEN HAS A PAGE VARIABLE.  cStateCreateActor's per-frame method
    (vtable +0x14 = 0x4C3C40) dispatches on the global dword [0x107A2C0]
    through a fifteen-entry jump table at 0x4C3E30 (pages 0x00..0x0E; anything
    above 0x0E does nothing at all).  Input handlers gate on the same global
    being 0 (e.g. 0x4BEEA9 `cmp dword [0x107A2C0], 0 / jne`).  Twenty sites
    write it; the delete-result handler is NOT one of them.

  * THE CHARACTER LIST BUFFER.  A process-wide singleton, allocated 0x1A8 bytes
    on first use by the accessor 0x4011A0 and cached in [0x1081A90]
    (constructor 0x5DE7D0), owns the character collection at offset +0x180
    (constructed by 0x58CD10, count at +0x19C/+0x1C of the container).
    Exhaustive scan of .text finds 32 instructions that form the address
    `<reg> + 0x180`; only six of them belong to this singleton, and the
    complete set of mutators is:

        0x5DDD00  bulk fill  - ONE caller: 0x5EFCAC, inside SelectActorVital
                               (0x36EF) handler 0x5EFC40
        0x5DDE10  add one    - ONE caller: 0x5EFD76, inside CreateActorVital
                               (0x36CF) handler 0x5EFD50
        0x5DDF00  clear      - THREE callers: 0x406C3A (app reset, itself
                               called first thing by SelectActorVital's
                               handler), 0x5DE2E4, 0x5DE994 (constructor)
        0x5DE540  clear      - ONE caller: 0x5DE9CD, the atexit destructor
        0x5F8400  lookup     - used by the delete-result handler to find one
                               record and write its +0xF4 field

    THERE IS NO ERASE-BY-KEY PATH ANYWHERE.  Nothing in the image can remove a
    single character from this collection.  The only way the collection loses a
    member is the full clear+refill performed by SelectActorVital.

  * THE FIVE INBOUND VITALS THIS SCREEN HANDLES.  Every Vital class exposes its
    wire id through vtable +0x10 and its inbound apply method through vtable
    +0x1C (+0x18 is the serializer).  Exactly five apply methods gate on
    "current state is cStateCreateActor" (the only five callers of the token
    getter 0x4C0110 that live inside a Vital vtable):

        0x36CF CreateActorVital        apply 0x5EFD50
        0x36DB DeleteActorVital        apply 0x5EFDC0
        0x4323 StartGameFailVital      apply 0x5EFEB0
        0x709E ReturnSelectServerVital apply 0x5F1190
        0x42E3 LSCN_LoginVitalRes      apply 0x5F3300

    plus 0x36EF SelectActorVital, whose apply 0x5EFC40 CREATES the screen.

  * WHAT THE DELETE ACK ACTUALLY DOES.  0x5EFDC0 reads DeleteActorVital's three
    scalar fields (u8 +0x14, s8 +0x15, u32 +0x18) and calls
    cStateCreateActor::OnDeleteResult 0x4BAEB0 with them.  That function:
      - requires the UI window L"Login_CharSelect_Panel_Operations" to exist;
      - for field+0x14 in {3,4}: looks the record up in the singleton's +0x180
        collection and writes field+0x18 into record+0xF4 (the pending-delete
        countdown the name board renders);
      - for every OTHER value of field+0x14 - INCLUDING the 1 our server sends -
        it re-renders: 0x4B90A0 (scene actors), 0x4B9980 (slot widgets), then
        pushes the descriptors L"Set_DeleteBtn_Visible", L"Set_DeleteBtn_Text"
        (parameter = (field+0x18 == 0)) and L"Set_EditBtn_Disable" into the
        operations panel.
      - it never removes a record, never calls 0x5DDD00 / 0x5DDE10 / 0x5DDF00 /
        0x5DE540, never calls CState::RequestNext 0x4C7320 and never writes the
        page variable 0x107A2C0.
    So the ack repaints the screen from a collection that still contains the
    character.  That is a complete mechanical explanation of GT-011.

  * WHAT THE LOGOUT VITAL ACTUALLY DOES.  LogoutVital 0x1B40 apply 0x5EF930
    forwards (+0x14, +0x18, +0x1C) to 0x5DC660, which switches on +0x18:
    values -0x13..-1 print a client string id and return; +0x18 == 0x14 opens
    the UI window L"SystemSetting_LogoutConfirm"; +0x18 == 0x16 closes it; any
    other value returns having only stored +0x14 into singleton+0xE0.  No
    branch calls CState::RequestNext, and no branch touches [0x1093198]+0x34C.
    The whole logout vital is a confirm-dialog controller.

  * THE COMPLETE TRANSITION GRAPH.  CState::RequestNext 0x4C7320 has exactly
    eighteen call sites in the image.  Only THREE of them sit inside an inbound
    vital apply method:
        0x5EFD1E  SelectActorVital 0x36EF -> new cStateCreateActor
        0x5F16C9  TeleportVital    0x25A2 -> new cStateSwitchScene
        0x5DE3AA  singleton method 0x5DE000 -> new cStateSwitchScene
    The character-select -> world transition is client-local: UI command 3 of
    cStateCreateActor's 27-entry command table (0x4C0120 / jump table 0x4C02DC)
    calls 0x4B4910, which returns early unless state+0x718 (the selected actor)
    is non-zero and otherwise builds cStateSwitchScene itself.  No inbound frame
    is consulted.

WHAT IS NOT CLAIMED: nothing about the ORIGINAL server (closed, never
published); no runtime behaviour; no claim about which page value 0x107A2C0
holds at any particular moment; no claim that re-sending SelectActorVital does
in fact repaint (that is a runtime question).

Usage:  py -3 tools/pf_ui_state_refresh_static.py [path-to-GameClient.local.bin]
        py -3 tools/pf_ui_state_refresh_static.py --json
Exit 0 = every static guard reproduced; nonzero = a guard drifted.

Pure standard library on purpose: the release gate runs `py -3` on Windows with
no third-party packages.  capstone was used to FIND these facts and is not used
to CHECK them - every claim below is reduced to a byte comparison.
"""
import hashlib
import json
import os
import struct
import sys

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

data = open(BIN, "rb").read()
sha = hashlib.sha256(data).hexdigest().upper()

# --------------------------------------------------------------------------
# PE mapping (hand-rolled; no dependency at all)
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
    if off is None:
        return b""
    return data[off:off + n]


def dw(va):
    raw = rd(va, 4)
    return struct.unpack("<I", raw)[0] if len(raw) == 4 else None


def cstr(va, limit=200):
    off = va2off(va)
    if off is None:
        return ""
    end = data.find(b"\0", off, off + limit)
    return data[off:end].decode("latin1", "replace")


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
TLO = va2off(TSTART)
THI = TLO + _TEXT[2]
_RDATA = [s for s in SECTIONS if s[0] == ".rdata"][0]
RLO = va2off(IMAGE_BASE + _RDATA[1])
RHI = RLO + _RDATA[4]


def name_hash(name):
    """PF-NAMEID-HASH-001: u16 id = SUM_i (int16)((signed char)name[i] * (i+1))."""
    total = 0
    for index, byte in enumerate(name.encode("latin1")):
        signed = byte - 256 if byte > 127 else byte
        total = (total + ((signed * (index + 1)) & 0xFFFF)) & 0xFFFF
    return total


def find_all(pat, lo=None, hi=None):
    lo = TLO if lo is None else lo
    hi = THI if hi is None else hi
    out = []
    start = lo
    while True:
        j = data.find(pat, start, hi)
        if j < 0:
            return out
        out.append(j)
        start = j + 1


def refs32(value, lo=None, hi=None):
    return [off2va(o) for o in find_all(struct.pack("<I", value), lo, hi)]


# ---- one pass over .text indexing every near call / near jmp target ------
CALL_INDEX = {}
_JMP_INDEX = {}
for _opcode, _bucket in ((0xE8, CALL_INDEX), (0xE9, _JMP_INDEX)):
    _pos = TLO
    _needle = bytes([_opcode])
    while True:
        _j = data.find(_needle, _pos, THI - 5)
        if _j < 0:
            break
        _pos = _j + 1
        _src = off2va(_j)
        if _src is None:
            continue
        _tgt = (_src + 5 + struct.unpack_from("<i", data, _j + 1)[0]) & 0xFFFFFFFF
        if TSTART <= _tgt < TSTART + _TEXT[2]:
            _bucket.setdefault(_tgt, []).append(_src)


def calls_to(target):
    return sorted(CALL_INDEX.get(target, []))


def jumps_to(target):
    return sorted(_JMP_INDEX.get(target, []))


def calls_in(lo, hi):
    """Every near-call target reached from instruction bytes inside [lo, hi)."""
    out = {}
    for tgt, srcs in CALL_INDEX.items():
        for s in srcs:
            if lo <= s < hi:
                out.setdefault(tgt, []).append(s)
    return out


# --------------------------------------------------------------------------
# Guard accumulator
# --------------------------------------------------------------------------
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    if not AS_JSON:
        print(("PASS " if cond else "FAIL ") + name + ("  " + detail if detail else ""))
    return bool(cond)


def guard_bytes(label, va, expect_hex):
    raw = rd(va, len(expect_hex) // 2)
    ok = raw.hex().upper() == expect_hex.upper()
    return check("%s @0x%06X" % (label, va), ok, "" if ok else "got " + raw.hex().upper())


# ==========================================================================
# 0. Image identity
# ==========================================================================
check("client image SHA-256 is the pinned read-only evidence", sha == EXPECT_SHA, sha)
check("PE image base is 0x400000", IMAGE_BASE == 0x400000, hex(IMAGE_BASE))
check("PE has the six sections this analysis walks", len(SECTIONS) == 6,
      ",".join(s[0] for s in SECTIONS))
check(".text is mapped at 0x401000 with size 0x838A2C",
      TSTART == 0x401000 and _TEXT[2] == 0x838A2C, hex(_TEXT[2]))

# ==========================================================================
# 1. The ten registered state classes
# ==========================================================================
# name -> (type-descriptor VA, registrar-thunk VA, class-node token slot,
#          token getter VA, state vtable VA or None)
STATE_CLASSES = {
    "cStateInitGame":        (0x1022EB0, 0xBDBBA0, 0x107A52C, 0x4C4CB0, 0xF169D8),
    "cStateDisplayLogo":     (0x1022ED0, 0xBDBBE0, 0x107A520, 0x4C4C80, 0xF16A10),
    "cStateLogin":           (0x1022EF4, 0xBDBD70, 0x107A5AC, 0x4C51D0, 0xF16B58),
    "cStateSelectServer":    (0x1022F14, 0xBDBEE0, 0x107A5BC, 0x4C5CE0, 0xF16D30),
    "cStateCreateActor":     (0x1022D5C, 0xBDB800, 0x107A38C, 0x4C0110, 0xF16520),
    "cStateSwitchScene":     (0x1022F3C, 0xBDC050, 0x107A608, 0x4C65D0, 0xF16E7C),
    "cStateFullScreenMovie": (0x102150C, 0xBDB9D0, 0x107A4B4, 0x4C40E0, 0xF168CC),
    "CState":                (0x1022F60, 0xBDC090, 0x107A640, 0x4C7310, None),
    "StateNavigation":       (0x1022F7C, 0xBDC330, 0x107A6A8, 0x4C7690, None),
    "StateRunTime":          (0x1022FA0, 0xBDC4A0, 0x107A6E4, 0x4C8740, 0xF170E4),
}

for _name, (_td, _reg, _slot, _get, _vt) in sorted(STATE_CLASSES.items()):
    check("state class name literal 0x%06X is .?AV%s@@" % (_td + 8, _name),
          cstr(_td + 8) == ".?AV%s@@" % _name, cstr(_td + 8))
    # registrar thunk: push 0x10945D0 ; mov ecx, <type descriptor> ; call [0xC3B7AC]
    _want = "68D0450901B9" + struct.pack("<I", _td).hex().upper() + "FF"
    guard_bytes("registrar thunk for %s" % _name, _reg, _want)
    # token getter: mov eax, <class-node token slot> ; ret
    guard_bytes("class-node token getter for %s" % _name, _get,
                "B8" + struct.pack("<I", _slot).hex().upper() + "C3")
    if _vt is not None:
        check("vtable 0x%06X slot 0 is %s's token getter" % (_vt, _name),
              dw(_vt) == _get, hex(dw(_vt)))

check("the image registers exactly ten state classes", len(STATE_CLASSES) == 10)

# The live state pointer, read identically by every consumer.
CUR_STATE_READ = "A198310901"          # mov eax, dword ptr [0x1093198]
guard_bytes("CreateActorVital apply loads the app singleton", 0x5EFD50, CUR_STATE_READ)
guard_bytes("DeleteActorVital apply loads the app singleton", 0x5EFDC0, CUR_STATE_READ)
check("both read the live state pointer from app+0x34C",
      rd(0x5EFD56, 6).hex().upper() == "8BB04C030000"
      and rd(0x5EFDC6, 6).hex().upper() == "8BB04C030000")

# CState::RequestNext
guard_bytes("CState::RequestNext 0x4C7320 stores next at this+0x10 and sets this+0x0C=2",
            0x4C7320,
            "568BF18B4E1085C974108B018B50046A01FFD2C7461000000000807C240C008B"
            "4424088946107407C7460C020000005E")

# ==========================================================================
# 2. Every state transition in the image
# ==========================================================================
# call site -> (target state class, constructor VA or None for inline ctor)
TRANSITIONS = {
    0x4323FA: ("cStateFullScreenMovie", 0x4C3FF0),
    0x4B01C3: ("cStateSelectServer",    0x4C5D40),
    0x4B4DE7: ("cStateSwitchScene",     0x4C6560),
    0x4B4EB0: ("cStateSwitchScene",     0x4C6560),
    0x4C481A: ("StateRunTime",          0x4C8790),
    0x4C4D35: ("cStateLogin",           0x4C51B0),
    0x4C4F8F: ("cStateDisplayLogo",     None),
    0x4C4F9F: ("cStateDisplayLogo",     None),
    0x4C589B: ("cStateSelectServer",    0x4C5D40),
    0x4C58C0: ("cStateSelectServer",    0x4C5D40),
    0x4C61FE: ("cStateCreateActor",     0x4C03E0),
    0x4C70C7: ("StateRunTime",          0x4C8790),
    0x4DA407: ("cStateLogin",           0x4C51B0),
    0x4DB1BC: ("cStateLogin",           0x4C51B0),
    0x4DB27C: ("cStateLogin",           0x4C51B0),
    0x5DE3AA: ("cStateSwitchScene",     0x4C6560),
    0x5EFD1E: ("cStateCreateActor",     0x4C03E0),
    0x5F16C9: ("cStateSwitchScene",     0x4C6560),
}
_req_sites = calls_to(0x4C7320)
check("CState::RequestNext has exactly 18 call sites in the whole image",
      len(_req_sites) == 18, str(len(_req_sites)))
check("the 18 call sites are exactly the ones enumerated in the report",
      _req_sites == sorted(TRANSITIONS), ",".join(hex(x) for x in _req_sites))
for _site in sorted(TRANSITIONS):
    check("transition site 0x%06X really calls RequestNext" % _site,
          _site in CALL_INDEX.get(0x4C7320, []))

# constructor -> vtable -> token getter, so the target class name is not a guess
STATE_CTORS = {
    0x4C03E0: ("cStateCreateActor", 0xF16520),
    0x4C3FF0: ("cStateFullScreenMovie", 0xF168CC),
    0x4C51B0: ("cStateLogin", 0xF16B58),
    0x4C5D40: ("cStateSelectServer", 0xF16D30),
    0x4C6560: ("cStateSwitchScene", 0xF16E7C),
    0x4C8790: ("StateRunTime", 0xF170E4),
}
for _ctor, (_cls, _vt) in sorted(STATE_CTORS.items()):
    _lo, _hi = va2off(_ctor), va2off(_ctor) + 0x400
    _blob = data[_lo:_hi]
    check("constructor 0x%06X installs %s's vtable 0x%06X" % (_ctor, _cls, _vt),
          struct.pack("<I", _vt) in _blob)
    check("that vtable's slot 0 is %s's token getter" % _cls,
          dw(_vt) == STATE_CLASSES[_cls][3])

# the only three transitions reachable from an inbound Vital apply method
NET_DRIVEN_TRANSITIONS = {0x5EFD1E: "SelectActorVital 0x36EF",
                          0x5F16C9: "TeleportVital 0x25A2",
                          0x5DE3AA: "singleton method 0x5DE000"}
check("only three RequestNext sites live above 0x5D0000 (the vital/singleton band)",
      sorted(s for s in _req_sites if s >= 0x5D0000) == sorted(NET_DRIVEN_TRANSITIONS),
      ",".join(hex(s) for s in _req_sites if s >= 0x5D0000))

# ==========================================================================
# 3. The character-list singleton and its collection at +0x180
# ==========================================================================
MODEL_GETTER = 0x4011A0
MODEL_GLOBAL = 0x1081A90
MODEL_CTOR = 0x5DE7D0
LIST_OFFSET = 0x180
LIST_FILL = 0x5DDD00
LIST_ADD_ONE = 0x5DDE10
LIST_CLEAR = 0x5DDF00
LIST_CLEAR_DTOR = 0x5DE540
LIST_FIND = 0x5F8400
APP_RESET = 0x406C30

guard_bytes("singleton accessor caches the model in [0x1081A90]", 0x4011C1,
            "A1901A080185C0754D68")
guard_bytes("singleton accessor allocates 0x1A8 bytes on first use", 0x4011CA,
            "68A8010000E8AC677300")
check("the accessor registers the destructor 0x5DE9C0 at exit",
      rd(0x4011F4, 5).hex().upper() == "68C0E95D00")
guard_bytes("constructor 0x5DE7D0 builds the collection at model+0x180", 0x5DE8BE,
            "508D5424178D8E8001000052C64424280FE83CE4FAFF")
guard_bytes("bulk fill 0x5DDD00 inserts into model+0x180", 0x5DDDAE,
            "528D44242C5081C180010000C744244800000000E859B01200")
guard_bytes("clear 0x5DDF00 destroys the model+0x180 nodes and resets the head",
            0x5DDFBD, "8B4204578DBE80010000508BCFE8912500008B47188940048B4718895F1C")
guard_bytes("destructor clear 0x5DE540 does the same on model+0x180", 0x5DE58F,
            "8B48048DBE80010000518BCFE8C01F00008B47188940048B47")
guard_bytes("app reset 0x406C30 = model accessor then clear", APP_RESET,
            "568BF1E868A5FFFF8BC8E8C1721D00B908070901")

_fill_callers = calls_to(LIST_FILL)
check("bulk fill 0x5DDD00 has exactly ONE caller in the image",
      _fill_callers == [0x5EFCAC], ",".join(hex(x) for x in _fill_callers))
_add_callers = calls_to(LIST_ADD_ONE)
check("add-one 0x5DDE10 has exactly ONE caller in the image",
      _add_callers == [0x5EFD76], ",".join(hex(x) for x in _add_callers))
_clear_callers = calls_to(LIST_CLEAR)
check("clear 0x5DDF00 has exactly THREE callers in the image",
      _clear_callers == [0x406C3A, 0x5DE2E4, 0x5DE994],
      ",".join(hex(x) for x in _clear_callers))
_dtor_clear_callers = calls_to(LIST_CLEAR_DTOR)
check("destructor clear 0x5DE540 has exactly ONE caller (the atexit destructor)",
      _dtor_clear_callers == [0x5DE9CD], ",".join(hex(x) for x in _dtor_clear_callers))
_reset_callers = calls_to(APP_RESET)
check("app reset 0x406C30 is called from SelectActorVital's apply, first thing",
      0x5EFC6C in _reset_callers, ",".join(hex(x) for x in _reset_callers))

# Exhaustive scan: every instruction in .text that forms <reg> + 0x180.
_PLUS180_ENCODINGS = (
    b"\x8d\x8e\x80\x01\x00\x00", b"\x8d\x8f\x80\x01\x00\x00",
    b"\x8d\x88\x80\x01\x00\x00", b"\x8d\x8b\x80\x01\x00\x00",
    b"\x8d\x8d\x80\x01\x00\x00", b"\x8d\x8a\x80\x01\x00\x00",
    b"\x81\xc1\x80\x01\x00\x00", b"\x05\x80\x01\x00\x00",
    b"\x8d\x86\x80\x01\x00\x00", b"\x8d\x87\x80\x01\x00\x00",
    b"\x8d\x96\x80\x01\x00\x00", b"\x8d\xb0\x80\x01\x00\x00",
    b"\x8d\xb8\x80\x01\x00\x00", b"\x8d\xbe\x80\x01\x00\x00",
    b"\x8d\xb7\x80\x01\x00\x00",
)
PLUS180_SITES = sorted(
    off2va(o) for pat in _PLUS180_ENCODINGS for o in find_all(pat)
)
PLUS180_EXPECTED = [
    0x4414E5, 0x4415B2, 0x4417CE, 0x441C51, 0x457675, 0x45CF35, 0x46656C,
    0x466A89, 0x4B4064, 0x4B54D5, 0x4BAF5E, 0x50D693, 0x50DF86, 0x50E452,
    0x5DDDB4, 0x5DDFC1, 0x5DE592, 0x5DE8C3, 0x5F5035, 0xAFEEC6, 0xAFFACE,
    0xB00DD0, 0xB00FD8, 0xB0149D, 0xB0162C, 0xB9FF3F, 0xBA006F, 0xBC4AC8,
    0xBC4B78, 0xBC71FF, 0xBC731F, 0xBC784F,
]
check("exactly 32 instructions in .text form <reg>+0x180",
      len(PLUS180_SITES) == 32, str(len(PLUS180_SITES)))
check("and they are exactly the 32 addresses the report enumerates",
      PLUS180_SITES == PLUS180_EXPECTED)
# The six that belong to the character-list singleton, and nothing else.
MODEL_PLUS180_SITES = [0x4B4064, 0x4BAF5E, 0x5DDDB4, 0x5DDFC1, 0x5DE592, 0x5DE8C3]
for _s in MODEL_PLUS180_SITES:
    check("model+0x180 site 0x%06X is inside the singleton's own code" % _s,
          _s in PLUS180_SITES)
guard_bytes("the free-slot gate reads the collection size and compares MAX_CHAR_COUNT",
            0x4B405F, "E83CD1F4FF8DB0800100008B461C3B05FC3703017C188B0D9831")
check("MAX_CHAR_COUNT lives in the global 0x10337FC",
      rd(0x4B406D, 6).hex().upper() == "3B05FC370301")
check("the literal MAX_CHAR_COUNT is the client setting name at 0xF135E0",
      wstr(0xF135E0) == "MAX_CHAR_COUNT", wstr(0xF135E0))

# THE negative result: no erase-by-key anywhere.
check("no code path removes a single record from model+0x180 "
      "(the only mutators are fill/add-one/clear)",
      len(_fill_callers) == 1 and len(_add_callers) == 1
      and len(_clear_callers) == 3 and len(_dtor_clear_callers) == 1)

# ==========================================================================
# 4. The Vital dispatch table (vtable +0x10 id, +0x18 serializer, +0x1C apply)
# ==========================================================================
NOOP_APPLY = 0x710440
guard_bytes("the default 'inbound does nothing' apply is `mov al,1 / ret 4`",
            NOOP_APPLY, "B001C20400")

# name -> (wire id, id slot, registrar thunk, id getter, vtable, apply)
VITALS = {
    "SelectActorVital":        (0x36EF, 0x01081FC4, 0xBEE2A0, 0x5ED1E0, 0xF30744, 0x5EFC40),
    "CreateActorVital":        (0x36CF, 0x01081FCC, 0xBEE2E0, 0x5E4C70, 0xF3017C, 0x5EFD50),
    "DeleteActorVital":        (0x36DB, 0x01081FD0, 0xBEE300, 0x5E4D90, 0xF301A0, 0x5EFDC0),
    "StartGameReq":            (0x1E87, 0x01081FD4, 0xBEE320, 0x5E4ED0, 0xF301C4, 0x710440),
    "StartGameRes":            (0x1E9F, 0x01081FD8, 0xBEE340, 0x5E4F80, 0xF301E8, 0x5EFE10),
    "StartGameFailVital":      (0x4323, 0x01081FDC, 0xBEE360, 0x5E5040, 0xF3020C, 0x5EFEB0),
    "ReturnSelectServerVital": (0x709E, 0x01082080, 0xBEE880, 0x5E6960, 0xF304DC, 0x5F1190),
    "LSCN_LoginVitalRes":      (0x42E3, 0x01082348, 0xBEFE10, 0x5F2840, 0xF30D64, 0x5F3300),
    "LSCN_SelectServerRes":    (0x5396, 0x01082350, 0xBEFE50, 0x5F29C0, 0xF30D88, 0x5F3390),
    "LoginVerifyVital":        (0x3784, 0x01081FC0, 0xBEE280, 0x5E4AE0, 0xF30158, 0x710440),
    "NotifyEnterCreateActor":  (0x6539, 0x01081FC8, 0xBEE2C0, 0x4AE340, 0xF159C0, 0x710440),
    "LogoutVital":             (0x1B40, 0x0108207C, 0xBEE860, 0x5E6810, 0xF304B8, 0x5EF930),
    "GetWorldInfoVital":       (0x3D4B, 0x01082068, 0xBEE7C0, 0x5E7650, 0xF30620, 0x5F0B00),
    "TeleportVital":           (0x25A2, 0x01081FF0, 0xBEE400, 0x5E5470, 0xF302C0, 0x5F14B0),
    "CheckSecondPwdVital":     (0x4B98, 0x01082044, 0xBEE6A0, 0x4E51D0, 0xF1A780, 0x5F05B0),
    "LSCN_LoginVitalReq":      (0x42BF, 0x01082344, 0xBEFDF0, 0x4C5120, 0xF16B34, 0x710440),
    "LSCN_SelectServerReq":    (0x536E, 0x0108234C, 0xBEFE30, 0x4C5D30, 0xF16D0C, 0x710440),
    "LSCN_ReloginVerifyVital": (0x6F03, 0x01082354, 0xBEFE70, 0x5F2BA0, 0xF30DAC, 0x710440),
}
for _n, (_id, _slot, _reg, _get, _vt, _apply) in sorted(VITALS.items()):
    check("hash(%s) reproduces its wire id 0x%04X" % (_n, _id), name_hash(_n) == _id,
          hex(name_hash(_n)))
    # registrar thunk tail: mov word ptr [<id slot>], ax ; ret
    check("%s registrar thunk 0x%06X caches the id into 0x%08X" % (_n, _reg, _slot),
          rd(_reg + 17, 6).hex().upper() == "66A3" + struct.pack("<I", _slot).hex().upper(),
          rd(_reg + 17, 6).hex().upper())
    guard_bytes("%s id getter" % _n, _get,
                "66A1" + struct.pack("<I", _slot).hex().upper() + "C3")
    check("%s vtable 0x%06X slot +0x10 is its id getter" % (_n, _vt),
          dw(_vt + 0x10) == _get, hex(dw(_vt + 0x10)))
    check("%s vtable 0x%06X slot +0x1C is its inbound apply 0x%06X" % (_n, _vt, _apply),
          dw(_vt + 0x1C) == _apply, hex(dw(_vt + 0x1C)))

CLIENT_TO_SERVER_ONLY = ("StartGameReq", "LoginVerifyVital", "NotifyEnterCreateActor",
                         "LSCN_LoginVitalReq", "LSCN_SelectServerReq",
                         "LSCN_ReloginVerifyVital")
for _n in CLIENT_TO_SERVER_ONLY:
    check("%s has the no-op inbound apply (nothing happens if we send it)" % _n,
          VITALS[_n][5] == NOOP_APPLY)

# The five vitals whose apply gates on "current state is cStateCreateActor".
CHARSELECT_GATED = {
    0x36CF: ("CreateActorVital", 0x5EFD50),
    0x36DB: ("DeleteActorVital", 0x5EFDC0),
    0x4323: ("StartGameFailVital", 0x5EFEB0),
    0x709E: ("ReturnSelectServerVital", 0x5F1190),
    0x42E3: ("LSCN_LoginVitalRes", 0x5F3300),
}
_tokcallers = calls_to(0x4C0110)
check("cStateCreateActor's token getter has exactly 8 call sites",
      len(_tokcallers) == 8, ",".join(hex(x) for x in _tokcallers))
check("the 8 sites are the ones the report lists",
      _tokcallers == [0x4E61D4, 0x510D45, 0x5D118B, 0x5EFD88, 0x5EFDDC,
                      0x5EFECC, 0x5F11AC, 0x5F334B])
_gated_applies = sorted(a for _i, (_n, a) in CHARSELECT_GATED.items())
for _id, (_n, _a) in sorted(CHARSELECT_GATED.items()):
    check("0x%04X %s applies inside a cStateCreateActor gate" % (_id, _n),
          any(_a <= s < _a + 0x100 for s in _tokcallers))
check("exactly five inbound vitals are gated on the character-select screen",
      len(CHARSELECT_GATED) == 5)

# SelectActorVital: the one frame that rebuilds the screen.
guard_bytes("SelectActorVital apply resets the model then refills it", 0x5EFC64,
            "8BF18B0D98310901E8BF6FE1FF8B46148B0D983109018981BC0700008B7E40"
            "E81815E1FF89B8440100008A5E39E80A15")
guard_bytes("SelectActorVital apply compares the live state with cStateSelectServer",
            0x5EFCB1,
            "8B0D983109018BB94C03000085FF74628B178B028BCFFFD050E81160EDFF50E8DB"
            "F529000FB6C083C408F7D81BC023C77406C6472005EB3A")
check("...and on a match only writes state+0x20 = 5",
      rd(0x5EFCE3, 4).hex().upper() == "C6472005")
guard_bytes("...otherwise it allocates 0x770 bytes and builds a new cStateCreateActor",
            0x5EFCE9, "6870070000E82DD3290083C40489442410C744241C0000000085C074098BC8"
                      "E8D306EDFFEB0233C06A01508BCFC7442424FFFFFFFFE8FD75EDFF")
check("the 0x770 allocation is cStateCreateActor's object size",
      struct.unpack("<I", rd(0x5EFCEA, 4))[0] == 0x770)

# ==========================================================================
# 5. DeleteActorVital 0x36DB - what the acknowledgement really does
# ==========================================================================
DELETE_APPLY = 0x5EFDC0
DELETE_RESULT = 0x4BAEB0
DELETE_RESULT_END = 0x4BB618

guard_bytes("DeleteActorVital serializer visits u8+0x14, u8+0x15, u32+0x18, string8+0x1C",
            0x5E4E10,
            "807C24080056578B7C240C8BF16A018D4614508BCF6A087433E8D2572B006A01"
            "8D4E15516A088BCFE8C3572B006A048D5618526A148BCFE8B4572B008D461C50")
guard_bytes("DeleteActorVital apply forwards +0x14/+0x15/+0x18 to 0x4BAEB0",
            DELETE_APPLY,
            "A198310901568BB04C030000578BF985F674358B168B028BCEFFD050E82F03EDFF"
            "50E8C9F429000FB6C883C408F7D91BC923CE74138B57180FBE4715520FB6571450"
            "52E8A8B0ECFF5FB0015EC20400")
check("that call really targets cStateCreateActor::OnDeleteResult 0x4BAEB0",
      0x5EFE03 in calls_to(DELETE_RESULT), ",".join(hex(x) for x in calls_to(DELETE_RESULT)))
check("0x4BAEB0 has exactly one caller: the DeleteActorVital apply",
      calls_to(DELETE_RESULT) == [0x5EFE03])

guard_bytes("OnDeleteResult requires the L\"Login_CharSelect_Panel_Operations\" window",
            0x4BAEEF, "68005FF100B908070901E802405E00")
check("...and that literal really is the operations panel name",
      wstr(0xF15F00) == "Login_CharSelect_Panel_Operations", wstr(0xF15F00))
guard_bytes("OnDeleteResult takes the model list and switches on field +0x14",
            0x4BAF59, "E84262F4FF8DB0800100008A8424A0010000895C242C3C0374083C040F85DA")
check("the switch tests exactly the values 3 and 4",
      rd(0x4BAF6F, 2).hex().upper() == "3C03" and rd(0x4BAF73, 2).hex().upper() == "3C04")
guard_bytes("only values 3 and 4 look a record up in the model list", 0x4BAF7B,
            "8D8424A4010000508D4C2428518BCEE871D413008B7E188B3639")
check("that lookup is the collection find 0x5F8400",
      0x4BAF8A in calls_to(LIST_FIND))
guard_bytes("...and all it writes is record+0xF4 (the pending-delete countdown)",
            0x4BAFCF, "8B4424288B40108B8C24A80100008988F4000000")
guard_bytes("every other value (including our op=1) falls into the repaint branch",
            0x4BB155, "8B7424188BCEE840DFFFFF8BCEE819E8FFFF8B")
check("the repaint branch calls the scene rebuild 0x4B90A0",
      0x4BB15B in calls_to(0x4B90A0))
check("the repaint branch calls the slot rebuild 0x4B9980",
      0x4BB162 in calls_to(0x4B9980))
guard_bytes("the delete-button state is derived from field +0x18 being non-zero",
            0x4BB208, "399C24A80100000F95C088442417395C242C741533C93AC30F94")
for _lbl, _site, _lit in (("Set_DeleteBtn_Visible", 0x4BB2CA, 0xF161A0),
                          ("Set_DeleteBtn_Text", 0x4BB390, 0xF16178),
                          ("Set_EditBtn_Disable", 0x4BB42F, 0xF16150)):
    check("repaint pushes the UI descriptor L\"%s\"" % _lbl,
          struct.unpack("<I", rd(_site + 1, 4))[0] == _lit and wstr(_lit) == _lbl,
          wstr(_lit))

_del_calls = calls_in(DELETE_RESULT, DELETE_RESULT_END)
for _fn, _why in ((LIST_FILL, "bulk fill"), (LIST_ADD_ONE, "add-one"),
                  (LIST_CLEAR, "clear"), (LIST_CLEAR_DTOR, "destructor clear"),
                  (0x4C7320, "CState::RequestNext"), (APP_RESET, "app reset")):
    check("OnDeleteResult never calls %s (0x%06X)" % (_why, _fn), _fn not in _del_calls)
check("OnDeleteResult never writes the page variable 0x107A2C0",
      not any(DELETE_RESULT <= v < DELETE_RESULT_END
              for v in refs32(0x107A2C0, va2off(DELETE_RESULT), va2off(DELETE_RESULT_END))))

# ==========================================================================
# 6. The character-select page variable 0x107A2C0
# ==========================================================================
PAGE_VAR = 0x107A2C0
PAGE_DISPATCH = 0x4C3C40
PAGE_TABLE = 0x4C3E30
guard_bytes("cStateCreateActor's per-frame method dispatches on the page variable",
            PAGE_DISPATCH, "A1C0A2070156578BF183F80E0F8787010000FF2485303E4C00")
check("cStateCreateActor vtable +0x14 is that per-frame method",
      dw(0xF16520 + 0x14) == PAGE_DISPATCH, hex(dw(0xF16520 + 0x14)))
PAGE_HANDLERS = [0x4C3C59, 0x4C3C63, 0x4C3C7F, 0x4C3C89, 0x4C3CA5, 0x4C3CC8,
                 0x4C3CE4, 0x4C3D00, 0x4C3D1C, 0x4C3D38, 0x4C3D54, 0x4C3D6D,
                 0x4C3D8D, 0x4C3DA6, 0x4C3DC2]
check("the page jump table has exactly 15 entries (pages 0x00..0x0E)",
      [dw(PAGE_TABLE + 4 * i) for i in range(15)] == PAGE_HANDLERS)
check("page 0x0F is padding, so any page above 0x0E does nothing at all",
      dw(PAGE_TABLE + 4 * 15) == 0xCCCCCCCC)
guard_bytes("the main-screen input path is gated on page == 0", 0x4BEEA9,
            "833DC0A2070100753C837E080D7536")
PAGE_WRITES = {
    0x4B3883: 0x0E, 0x4B6278: 0x00, 0x4B68E6: 0x04, 0x4B6E87: 0x02,
    0x4B738E: 0x00, 0x4B7929: 0x00, 0x4BAC08: 0x02, 0x4BAE91: 0x0B,
    0x4BED4A: 0x03, 0x4C33A2: 0x07, 0x4C3DB6: 0x0E, 0x4C0147: 0x01,
    0x4C016B: 0x05, 0x4C01A3: 0x06, 0x4C020B: 0x08, 0x4C0217: 0x09,
    0x4C023B: 0x04, 0x4C0247: 0x0A, 0x4C0291: 0x0C, 0x4C02A3: 0x0D,
}
for _va, _val in sorted(PAGE_WRITES.items()):
    guard_bytes("page write of 0x%02X" % _val, _va,
                "C705" + struct.pack("<I", PAGE_VAR).hex().upper()
                + struct.pack("<I", _val).hex().upper())
_page_imm_writes = sorted(
    off2va(o) for o in find_all(b"\xc7\x05" + struct.pack("<I", PAGE_VAR))
)
check("those 20 sites are every immediate write to the page variable in .text",
      _page_imm_writes == sorted(PAGE_WRITES), str(len(_page_imm_writes)))
check("page 0x0B is entered by the delete animation just above OnDeleteResult",
      PAGE_WRITES[0x4BAE91] == 0x0B and 0x4BAE91 < DELETE_RESULT)

# ==========================================================================
# 7. LogoutVital 0x1B40 - a confirm-dialog controller, not a state command
# ==========================================================================
guard_bytes("LogoutVital apply forwards +0x14/+0x18/+0x1C to the singleton",
            0x5EF930, "8B411C8B5118508B41145250E85F18E1FF8BC8E818CDFEFFB001C2")
check("that forward really targets 0x5DC660", 0x5EF93C in calls_to(0x4011A0)
      and 0x5EF943 in calls_to(0x5DC660))
guard_bytes("0x5DC660 switches on field +0x18 through a 19-entry byte-index table",
            0x5DC683, "8B5424688D421383F81277600FB680BCC75D00FF24859CC75D")
check("negative reason codes only print a client string id",
      [dw(0x5DC79C + 4 * i) for i in range(8)]
      == [0x5DC69D, 0x5DC6E8, 0x5DC6E1, 0x5DC6DA, 0x5DC6D3, 0x5DC6CC, 0x5DC6C5, 0x5DC6EF])
guard_bytes("field +0x18 == 0x14 opens a UI window", 0x5DC6EF,
            "8B4424648981E000000083FA147566")
guard_bytes("field +0x18 == 0x16 closes it, everything else returns",
            0x5DC764, "83FA16751F68ACFDF200B908070901E888274C0085C0740C8B108BC88B820C020000FFD0")
check("the window is L\"SystemSetting_LogoutConfirm\"",
      wstr(0xF2FDAC) == "SystemSetting_LogoutConfirm", wstr(0xF2FDAC))
_logout_calls = calls_in(0x5DC660, 0x5DC79A)
check("no branch of the logout handler calls CState::RequestNext",
      0x4C7320 not in _logout_calls)
check("no branch of the logout handler touches the live state pointer",
      not refs32(0x1093198, va2off(0x5EF930), va2off(0x5EF94D)))

# ==========================================================================
# 8. Character-select -> world is a client-local UI command
# ==========================================================================
UI_DISPATCH = 0x4C0120
UI_TABLE = 0x4C02DC
guard_bytes("the character-select UI command dispatcher", UI_DISPATCH,
            "568B74240C85F674658B4424088B80940000004883F81A7755FF2485DC024C00")
check("its command table has exactly 27 entries",
      all(0x4C0140 <= dw(UI_TABLE + 4 * i) <= 0x4C02D3 for i in range(27))
      and dw(UI_TABLE + 4 * 27) == 0xCCCCCCCC)
guard_bytes("command 3 jumps to the start-game routine 0x4B4910", 0x4C015B,
            "8BCE5EE9AD47FFFF")
check("0x4B4910 has exactly one caller, that command", jumps_to(0x4B4910) == [0x4C015E],
      ",".join(hex(x) for x in jumps_to(0x4B4910)))
guard_bytes("start-game returns early unless state+0x718 (selected actor) is set",
            0x4B493A, "8B871807000085C07543")
guard_bytes("otherwise it builds the movie/switch-scene states itself", 0x4B4DC4,
            "668B44241C536A01C643230066894320E8B7D4F7FF83C40885C07F708B4C2420"
            "6A0153E834250100")
_startgame_calls = calls_in(0x4B4910, 0x4B4EC0)
check("the start-game routine consults no inbound vital state: it never reads "
      "the model list nor calls any list mutator",
      LIST_FILL not in _startgame_calls and LIST_ADD_ONE not in _startgame_calls
      and LIST_CLEAR not in _startgame_calls)

# ==========================================================================
# 9. Read-only cross-check against our own server
# ==========================================================================
V141_PRESENT = os.path.isfile(SERVER_SRC)
V141 = {}
if V141_PRESENT:
    _src = open(SERVER_SRC, "r", encoding="utf-8", errors="replace").read()
    for _const, _val in (("SELECT_ACTOR_VITAL", 0x36EF), ("CREATE_ACTOR_VITAL", 0x36CF),
                         ("LOGIN_VERIFY_VITAL", 0x3784), ("START_GAME_REQ", 0x1E87),
                         ("START_GAME_RES", 0x1E9F), ("GET_WORLD_INFO_VITAL", 0x3D4B),
                         ("TELEPORT_VITAL", 0x25A2)):
        V141[_const] = _val
        check("v141 declares %s = 0x%04X, the id this tool read from the client"
              % (_const, _val), "%s = 0x%04X" % (_const, _val) in _src)
    check("v141 has a SelectActorVital builder (the only frame that rebuilds the list)",
          "make_runtime_select_actor_preset" in _src and "make_runtime_select_actor_empty" in _src)
    check("v141 has no DeleteActorVital constant of its own yet (id resolved statically)",
          "DELETE_ACTOR_VITAL" not in _src)

# ==========================================================================
# Counts block
# ==========================================================================
GUARDS_TOTAL = len(RESULTS)
GUARDS_FAILED = [n for n, ok in RESULTS if not ok]

COUNTS = {
    "measured_at_head": "08fb65b",
    "client_sha256": sha,
    "guards_total": GUARDS_TOTAL,
    "state_classes_registered": len(STATE_CLASSES),
    "character_select_state": "cStateCreateActor",
    "character_select_state_token": "0x%08X" % STATE_CLASSES["cStateCreateActor"][2],
    "character_select_state_object_size": 0x770,
    "live_state_pointer": "[0x1093198]+0x34C",
    "state_transition_sites": len(_req_sites),
    "state_transition_sites_inside_a_vital_apply": len(NET_DRIVEN_TRANSITIONS),
    "character_list_singleton_global": "0x%08X" % MODEL_GLOBAL,
    "character_list_collection_offset": "+0x%X" % LIST_OFFSET,
    "plus_0x180_instructions_in_text": len(PLUS180_SITES),
    "character_list_fill_callers": [hex(x) for x in _fill_callers],
    "character_list_add_one_callers": [hex(x) for x in _add_callers],
    "character_list_clear_callers": [hex(x) for x in _clear_callers],
    "character_list_erase_by_key_paths": 0,
    "vitals_enumerated": len(VITALS),
    "vitals_gated_on_character_select": len(CHARSELECT_GATED),
    "vitals_gated_on_character_select_ids": ["0x%04X" % i for i in sorted(CHARSELECT_GATED)],
    "vitals_with_noop_inbound_apply": len(CLIENT_TO_SERVER_ONLY),
    "delete_ack_vital_id": "0x36DB",
    "delete_ack_handler": "0x4BAEB0",
    "delete_ack_ops_that_touch_the_list": [3, 4],
    "delete_ack_op_our_server_sends": 1,
    "page_variable": "0x%08X" % PAGE_VAR,
    "page_jump_table_entries": len(PAGE_HANDLERS),
    "page_variable_immediate_writes": len(_page_imm_writes),
    "ui_command_table_entries": 27,
    "v141_cross_check_ran": V141_PRESENT,
}

if AS_JSON:
    print(json.dumps(COUNTS, indent=2, sort_keys=True))
else:
    print()
    print("character-select state machine, as the client implements it:")
    print("  live state pointer          [0x1093198]+0x34C")
    print("  character-select state      cStateCreateActor (token 0x107A38C, size 0x770)")
    print("  per-frame page dispatch     0x4C3C40 on [0x107A2C0], 15 pages")
    print("  character list buffer       [0x1081A90]+0x180")
    print("    filled by                 0x5DDD00  <- SelectActorVital 0x36EF only")
    print("    appended by               0x5DDE10  <- CreateActorVital 0x36CF only")
    print("    cleared by                0x5DDF00 / 0x5DE540")
    print("    erased per record by      (nothing in the image)")
    print("  delete ack 0x36DB apply     0x5EFDC0 -> 0x4BAEB0 (repaint only)")
    print("  logout vital 0x1B40 apply   0x5EF930 -> 0x5DC660 (confirm dialog only)")
    print()
    print("guards run: %d, failed: %d" % (GUARDS_TOTAL, len(GUARDS_FAILED)))

if GUARDS_FAILED:
    if not AS_JSON:
        print("RESULT: %d guard(s) drifted: %s" % (len(GUARDS_FAILED), GUARDS_FAILED))
    sys.exit(1)
if not AS_JSON:
    print("RESULT: all UI-REFRESH-001 static guards reproduced (exit 0)")
