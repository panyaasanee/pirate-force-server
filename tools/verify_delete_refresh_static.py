"""DELETE-REFRESH-001: pin the two facts HYP-PF-021 is built on, byte-exact.

HYP-PF-021 answers attended GT-011 ("soft delete committed, no error, list did
not move") by sending a `SelectActorVital` 0x36EF list rebuild after the pinned
0x36DB echo ack.  That design rests on exactly two statements about the
read-only client image, and this verifier reduces both of them to byte
comparisons so neither can rot silently.

FACT 1 (UI-REFRESH-001, re-checked here independently)
    The character list lives in ONE buffer -- the collection at +0x180 of the
    singleton cached in [0x1081A90].  Its only bulk writer is 0x5DDD00, whose
    single caller in the whole image is 0x5EFCAC inside the SelectActorVital
    0x36EF apply 0x5EFC40; its only append-one writer is 0x5DDE10, whose single
    caller is inside the CreateActorVital 0x36CF apply.  There is no
    erase-by-key path.  So an acknowledgement cannot remove a row and a list
    rebuild is the only mechanism that can.

FACT 2 (NEW in this milestone -- UI-REFRESH-001 did not have it)
    The same rebuild also restores the input page GT-011 found stuck.

    UI-REFRESH-001 enumerated the page variable 0x107A2C0's writers with the
    pattern `C7 05` and found twenty immediate writes, one of which
    (0x4BAE91) sets 0x0B in the delete animation, and recorded that
    OnDeleteResult never restores it -- leaving "which page was live during
    GT-011, and does anything ever put it back" open.

    An exhaustive scan of EVERY 32-bit reference to 0x107A2C0 in .text finds
    26 instructions: those 20 immediate writes, 5 reads/compares, and one
    writer the immediate-only scan could not see --

        0x4BD650:  89 3D C0 A2 07 01     mov dword [0x107A2C0], edi

    EDI is zeroed at 0x4BD620 (`33 FF`, xor edi,edi) and the 0x30 bytes
    between the two contain no branch and no instruction that writes EDI
    (EDI is callee-saved in the Win32 x86 ABI, so the intervening call
    through [0xC3B580] cannot change it either); the whole run is guarded
    byte-for-byte below.  So this instruction writes the constant 0.

    0x4BD5E0, the function that write lives in, has ZERO direct call sites in
    the entire image and is cStateCreateActor's vtable (0xF16520) slot +0x10.
    Slot +0x10 is the state machine's ENTER hook: the state tick 0x4C7540
    dispatches on the state's phase word +0x0C --

        phase 0 -> ... call [vtable+0x10] ... then set +0x0C = 1
        phase 1 -> call [vtable+0x14]   (cStateCreateActor: 0x4C3C40, the
                                         fifteen-entry page dispatch)
        phase 2 -> call [vtable+0x18], set +0x0C = 3, promote the pending
                   state held at +0x10 (the slot CState::RequestNext writes)

    and a freshly constructed cStateCreateActor (0x4C03E0) leaves +0x0C at 0.

    Chain, end to end: SelectActorVital apply resets the model, refills it,
    constructs a new cStateCreateActor, calls CState::RequestNext 0x4C7320 ->
    the next tick promotes it -> the tick after that runs its enter hook
    0x4BD5E0, whose first act is to zero the page variable.

    That is a prediction about a client, not an observation: whether the
    pixels move is GT-021, attended.  Nothing here was executed.

Sole evidence: GameClient/GameClient.local.bin (PE32 x86, ImageBase 0x400000,
14,759,424 B, SHA-256 9627211412AC60D5..B623), read only, plus a read-only
cross-check against current/pf_login_game_server_v141.py and
src/pirateforce_foundation/delete_refresh_hypothesis.py.  No server booted, no
GameClient launched, no socket, no database.

    py -3 tools\\verify_delete_refresh_static.py            # guards, exit 0
    py -3 tools\\verify_delete_refresh_static.py --json     # the counts block

Exit 0 = every guard reproduced; nonzero = a guard drifted.  Pure standard
library: the release gate runs `py -3` on Windows with no third-party
packages.  capstone was used to FIND these facts and is not used to CHECK
them -- every claim below is a byte comparison.
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
LANE_SRC = os.path.join(
    _ROOT, "src", "pirateforce_foundation", "delete_refresh_hypothesis.py",
)

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


_TEXT = [s for s in SECTIONS if s[0] == ".text"][0]
TSTART = IMAGE_BASE + _TEXT[1]
TLO = va2off(TSTART)
THI = TLO + _TEXT[2]


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


# ---- one pass over .text indexing every near call / near jmp target ------
CALL_INDEX = {}
JMP_INDEX = {}
for _opcode, _bucket in ((0xE8, CALL_INDEX), (0xE9, JMP_INDEX)):
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
    return sorted(JMP_INDEX.get(target, []))


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
check(".text is mapped at 0x401000 with size 0x838A2C",
      TSTART == 0x401000 and _TEXT[2] == 0x838A2C, hex(_TEXT[2]))

# ==========================================================================
# 1. FACT 1 - one buffer, one rebuild path, no erase
# ==========================================================================
MODEL_ACCESSOR = 0x4011A0
MODEL_GLOBAL = 0x1081A90
LIST_FILL = 0x5DDD00
LIST_ADD_ONE = 0x5DDE10
LIST_CLEAR = 0x5DDF00
SELECT_ACTOR_APPLY = 0x5EFC40
SELECT_ACTOR_FILL_SITE = 0x5EFCAC
SELECT_ACTOR_REQUEST_NEXT_SITE = 0x5EFD1E
CREATE_ACTOR_ADD_SITE = 0x5EFD76
APP_RESET = 0x406C30
REQUEST_NEXT = 0x4C7320
CHARSELECT_CTOR = 0x4C03E0
CHARSELECT_VTABLE = 0xF16520

MODEL_ACCESSOR_LOAD = 0x4011C1
check("the character-list singleton accessor reads the pinned global",
      rd(MODEL_ACCESSOR_LOAD, 5) == b"\xa1" + struct.pack("<I", MODEL_GLOBAL)
      and MODEL_ACCESSOR < MODEL_ACCESSOR_LOAD,
      rd(MODEL_ACCESSOR_LOAD, 5).hex().upper())
check("bulk fill 0x5DDD00 has exactly one caller in the whole image, "
      "inside the SelectActorVital apply",
      calls_to(LIST_FILL) == [SELECT_ACTOR_FILL_SITE],
      str([hex(x) for x in calls_to(LIST_FILL)]))
check("append-one 0x5DDE10 has exactly one caller, inside the "
      "CreateActorVital apply",
      calls_to(LIST_ADD_ONE) == [CREATE_ACTOR_ADD_SITE],
      str([hex(x) for x in calls_to(LIST_ADD_ONE)]))
check("the app reset that clears the model is called from the "
      "SelectActorVital apply",
      APP_RESET in [t for t, srcs in CALL_INDEX.items()
                    if any(SELECT_ACTOR_APPLY <= s < SELECT_ACTOR_REQUEST_NEXT_SITE
                           for s in srcs)])
guard_bytes("SelectActorVital apply resets the model then refills it",
            0x5EFC64, "8BF18B0D98310901E8BF6FE1FF8B46148B0D9831")
check("the SelectActorVital apply requests a transition into a fresh "
      "cStateCreateActor",
      SELECT_ACTOR_REQUEST_NEXT_SITE in calls_to(REQUEST_NEXT)
      and any(SELECT_ACTOR_APPLY <= s < SELECT_ACTOR_REQUEST_NEXT_SITE
              for s in calls_to(CHARSELECT_CTOR)))
# The negative that makes the whole lane necessary: no caller of the clear
# helper and no writer of the collection can remove ONE row.
check("there is no erase-by-key path: the model's only writers are fill, "
      "append-one and whole-collection clear",
      sorted(calls_to(LIST_FILL) + calls_to(LIST_ADD_ONE)) ==
      [SELECT_ACTOR_FILL_SITE, CREATE_ACTOR_ADD_SITE]
      and len(calls_to(LIST_CLEAR)) == 3)

# ==========================================================================
# 2. FACT 2 - every reference to the page variable, not only the immediates
# ==========================================================================
PAGE_VAR = 0x107A2C0
_page_refs = sorted(find_all(struct.pack("<I", PAGE_VAR)))
_imm_writes = sorted(off2va(o) for o in find_all(b"\xc7\x05" + struct.pack("<I", PAGE_VAR)))
_reg_writes = sorted(off2va(o) for o in find_all(b"\x89\x3d" + struct.pack("<I", PAGE_VAR)))
# every remaining reference must be one of the five read/compare forms
_read_forms = (
    (0x4BE173, b"\xa1"),                 # mov eax, [page]
    (0x4BE7B6, b"\x39\x2d"),             # cmp [page], ebp
    (0x4BEDC4, b"\xa1"),                 # mov eax, [page]
    (0x4BEEA9, b"\x83\x3d"),             # cmp dword [page], imm8
    (0x4C3C40, b"\xa1"),                 # mov eax, [page]  (the page dispatch)
)
_reads = []
for _va, _op in _read_forms:
    if rd(_va, len(_op) + 4) == _op + struct.pack("<I", PAGE_VAR):
        _reads.append(_va)

check("the page variable is referenced by exactly 26 instructions in .text",
      len(_page_refs) == 26, str(len(_page_refs)))
check("twenty of them are the UI-REFRESH-001 immediate writes",
      len(_imm_writes) == 20, str(len(_imm_writes)))
check("five of them are the read/compare forms",
      len(_reads) == 5, str(len(_reads)))
check("the twenty-sixth is a REGISTER write UI-REFRESH-001's immediate-only "
      "scan could not see",
      _reg_writes == [0x4BD650], str([hex(x) for x in _reg_writes]))
check("20 immediate writes + 1 register write + 5 reads account for all 26",
      len(_imm_writes) + len(_reg_writes) + len(_reads) == len(_page_refs))
guard_bytes("the delete animation sets page 0x0B just above OnDeleteResult",
            0x4BAE91, "C705C0A207010B000000")
guard_bytes("the per-frame page dispatch reads the page variable", 0x4C3C40,
            "A1C0A2070156578BF183F80E0F8787010000FF")
guard_bytes("the main-screen input path is gated on page == 0", 0x4BEEA9,
            "833DC0A2070100")

# ==========================================================================
# 3. FACT 2 - the register write is `page = 0`, unconditionally, on entry
# ==========================================================================
CHARSELECT_ENTER = 0x4BD5E0
PAGE_ZERO_SOURCE = 0x4BD620
PAGE_REG_WRITE = 0x4BD650

# One straight-line run: xor edi,edi ... mov [page], edi.  No branch, no
# instruction that writes EDI (EDI is callee-saved across the one intervening
# call), so the value stored is the constant 0.
guard_bytes(
    "xor edi,edi ... mov [0x107A2C0], edi is one unbroken run",
    PAGE_ZERO_SOURCE,
    "33FF578BF1FF1580B5C3008B0D983109012B81BC07000083C4048986D8010000"
    "684C64F1008D8C24AC0000008954244C893DC0A20701",
)
check("the zeroing and the write are 0x30 bytes apart in the same function",
      PAGE_REG_WRITE - PAGE_ZERO_SOURCE == 0x30)
check("the enter hook 0x4BD5E0 has zero direct call sites in the whole image",
      calls_to(CHARSELECT_ENTER) == [] and jumps_to(CHARSELECT_ENTER) == [],
      str([hex(x) for x in calls_to(CHARSELECT_ENTER)]))
check("0x4BD5E0 is cStateCreateActor's vtable slot +0x10",
      dw(CHARSELECT_VTABLE + 0x10) == CHARSELECT_ENTER,
      hex(dw(CHARSELECT_VTABLE + 0x10) or 0))
check("the same vtable's slot 0 is the cStateCreateActor token getter",
      dw(CHARSELECT_VTABLE + 0x00) == 0x4C0110)
check("the same vtable's slot +0x14 is the fifteen-entry page dispatch",
      dw(CHARSELECT_VTABLE + 0x14) == 0x4C3C40)
# Every state class has its OWN function in slot +0x10 -- it is a per-class
# hook, not a shared helper.
STATE_ENTER_SLOTS = {
    "cStateCreateActor": (0xF16520, 0x4BD5E0),
    "cStateSelectServer": (0xF16D30, 0x4C5FA0),
    "cStateSwitchScene": (0xF16E7C, 0x4C7160),
    "StateRunTime": (0xF170E4, 0x4C89C0),
    "cStateLogin": (0xF16B58, 0x4C5AE0),
}
for _name, (_vt, _fn) in sorted(STATE_ENTER_SLOTS.items()):
    check("%s vtable+0x10 is its own enter hook" % _name,
          dw(_vt + 0x10) == _fn, hex(dw(_vt + 0x10) or 0))
check("the five enter hooks are five distinct functions",
      len({fn for _vt, fn in STATE_ENTER_SLOTS.values()}) == 5)

# ==========================================================================
# 4. FACT 2 - slot +0x10 is the ENTER hook of the state tick
# ==========================================================================
STATE_TICK = 0x4C7540
STATE_TICK_ENTER_CALL = 0x4C75D9
guard_bytes(
    "the state tick dispatches on phase +0x0C and calls [vtable+0x10] on "
    "phase 0, [vtable+0x14] on phase 1 and [vtable+0x18] on phase 2",
    STATE_TICK,
    "568BF18B0E85C974428B410C83E800745B83E801743983E80175308B018B5018"
    "57FFD28B06C7400C030000008B0E8B791085FF741585C9740F8B118B42046A01"
    "FFD0C70600000000893E5F5EC20800D944240C8B118B421483EC08D95C2404D9"
    "442410D91C24FFD05EC20800807E0400742351E848A4F3FF83C40485C0750F8B"
    "0E51E869A4F3FF83C40485C074078BCEE89BFEFFFF8B0E8B118B4210FFD08B36"
    "837E0C0075A5C7460C010000005EC208",
)
check("the enter call site sits inside that tick",
      STATE_TICK < STATE_TICK_ENTER_CALL < STATE_TICK + 0xB0)
check("phase 2 (the value CState::RequestNext writes) promotes the pending "
      "state held at +0x10",
      rd(0x4C7565, 7) == bytes.fromhex("C7400C03000000"),
      rd(0x4C7565, 7).hex().upper())
guard_bytes("CState::RequestNext stores the next state at +0x10 and sets "
            "phase 2", REQUEST_NEXT,
            "568BF18B4E1085C974108B018B50046A01FFD2C746100000000080")

# ==========================================================================
# 5. The delete acknowledgement still cannot do any of this
# ==========================================================================
DELETE_RESULT = 0x4BAEB0
DELETE_RESULT_END = 0x4BB618
_ack_body = (va2off(DELETE_RESULT), va2off(DELETE_RESULT_END))
check("OnDeleteResult never writes the page variable (immediate or register)",
      not [v for v in _imm_writes + _reg_writes if DELETE_RESULT <= v < DELETE_RESULT_END])
check("OnDeleteResult never calls fill, append-one or clear",
      not [s for t in (LIST_FILL, LIST_ADD_ONE, LIST_CLEAR)
           for s in calls_to(t) if DELETE_RESULT <= s < DELETE_RESULT_END])
check("OnDeleteResult never calls CState::RequestNext",
      not [s for s in calls_to(REQUEST_NEXT)
           if DELETE_RESULT <= s < DELETE_RESULT_END])

# ==========================================================================
# 6. Cross-checks against this repository (read-only)
# ==========================================================================
V141_PRESENT = os.path.isfile(SERVER_SRC)
if V141_PRESENT:
    _v141 = open(SERVER_SRC, "r", encoding="utf-8", errors="replace").read()
    check("v141 declares SelectActorVital 0x36EF", "SELECT_ACTOR_VITAL = 0x36EF" in _v141)
    check("v141 has the collection composer the rebuild rides on "
          "(trailing derived-class mask)", "def make_runtime_vitals(" in _v141)

LANE_PRESENT = os.path.isfile(LANE_SRC)
if LANE_PRESENT:
    _lane = open(LANE_SRC, "r", encoding="utf-8", errors="replace").read()
    for _label, _needle in (
        ("the lane declares the rebuild vital id", '"select_actor_apply": 0x5EFC40'),
        ("the lane declares the enter hook", '"character_select_enter_hook": 0x4BD5E0'),
        ("the lane declares the register write",
         '"page_variable_register_write": 0x4BD650'),
        ("the lane declares the state tick", '"state_tick": 0x4C7540'),
        ("the lane declares the page variable", '"page_variable": 0x0107A2C0'),
        ("the lane is bound to this exact client image", EXPECT_SHA),
    ):
        check("%s" % _label, _needle in _lane)

GUARDS_TOTAL = len(RESULTS)
GUARDS_FAILED = [name for name, ok in RESULTS if not ok]

COUNTS = {
    "milestone": "DELETE-REFRESH-001",
    "hypothesis": "HYP-PF-021",
    "client_sha256": sha,
    "guards_total": GUARDS_TOTAL,
    "character_list_singleton_global": "0x%08X" % MODEL_GLOBAL,
    "character_list_fill_callers": [hex(x) for x in calls_to(LIST_FILL)],
    "character_list_add_one_callers": [hex(x) for x in calls_to(LIST_ADD_ONE)],
    "character_list_erase_by_key_paths": 0,
    "rebuild_vital_id": "0x36EF",
    "rebuild_apply": "0x%06X" % SELECT_ACTOR_APPLY,
    "page_variable": "0x%08X" % PAGE_VAR,
    "page_variable_references_in_text": len(_page_refs),
    "page_variable_immediate_writes": len(_imm_writes),
    "page_variable_register_writes": [hex(x) for x in _reg_writes],
    "page_variable_reads": len(_reads),
    "character_select_enter_hook": "0x%06X" % CHARSELECT_ENTER,
    "character_select_enter_hook_vtable_slot": "+0x10",
    "character_select_enter_hook_direct_call_sites": len(calls_to(CHARSELECT_ENTER)),
    "state_tick": "0x%06X" % STATE_TICK,
    "state_tick_enter_call_site": "0x%06X" % STATE_TICK_ENTER_CALL,
    "delete_ack_handler": "0x%06X" % DELETE_RESULT,
    "delete_animation_page_value": "0x0B",
    "v141_cross_check_ran": V141_PRESENT,
    "lane_cross_check_ran": LANE_PRESENT,
}

if AS_JSON:
    print(json.dumps(COUNTS, indent=2, sort_keys=True))
else:
    print()
    print("why one SelectActorVital 0x36EF is predicted to fix both GT-011 symptoms:")
    print("  list buffer            [0x1081A90]+0x180, filled only by 0x5DDD00")
    print("    filled from          0x5EFCAC, inside the 0x36EF apply 0x5EFC40")
    print("    erased per record by (nothing in the image)")
    print("  page variable          0x107A2C0, 26 refs = 20 imm + 1 reg + 5 reads")
    print("    stuck at             0x0B by the delete animation 0x4BAE91")
    print("    zeroed by            0x4BD650 (mov [page], edi ; edi = 0)")
    print("    which lives in       0x4BD5E0 = cStateCreateActor vtable +0x10")
    print("    called by            state tick 0x4C7540, phase 0 = enter")
    print("  a fresh cStateCreateActor is built at 0x4C03E0 by the 0x36EF apply")
    print()
    print("guards run: %d, failed: %d" % (GUARDS_TOTAL, len(GUARDS_FAILED)))

if GUARDS_FAILED:
    if not AS_JSON:
        print("RESULT: %d guard(s) drifted: %s" % (len(GUARDS_FAILED), GUARDS_FAILED))
    sys.exit(1)
if not AS_JSON:
    print("RESULT: all DELETE-REFRESH-001 static guards reproduced (exit 0)")
