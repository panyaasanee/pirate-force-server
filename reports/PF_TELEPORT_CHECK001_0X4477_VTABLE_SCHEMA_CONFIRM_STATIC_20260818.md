# PF_TELEPORT_CHECK001 — `TeleportCheckVital 0x4477`: vtable + schema + field semantics settle the client→server confirm-request; the server correctly need not answer (static disasm + wire corpus)

> ## ⚠ ERRATUM 2026-08-19 (รอบ 84, SCAN-DEBT-001) — ตาราง §4 พิสูจน์ซ้ำได้ **6 จาก 8 แถว** ไม่ใช่ 8/8
>
> **ตัวเลขในรายงานนี้ไม่ได้ผิด แต่ verifier ที่อ้างว่าค้ำมันไว้ ไม่ได้ตรวจอะไรเลยมาสองรอบ**
>
> 1. **สิ่งที่เกิดขึ้น** — `tools/pf_teleportcheck_0x4477_static.py` guard G8 อ่าน corpus ด้วย `glob` ไปที่
>    `<repo>/../GameClient/capture_v13x|v14x/GAME_2*.txt` คือ **โฟลเดอร์ติดตั้งเกม นอก git worktree**
>    เมื่อรันจาก repo root (ซึ่งเป็นวิธีที่ gate/เทส/scheduled job รันทุกครั้ง) glob จึง match 0 ไฟล์ แล้วโค้ด
>    `print("SKIP wire corpus ...")` และ **exit 0** ⇒ เขียวโดยไม่ได้อ่าน wire evidence สักไบต์
>    (เกรด B จาก `reports/PF_CORPUS_PIN001_DIRECTORY_SCAN_SURVEY_20260819.md` จุดที่ 4)
> 2. **หลักฐานหายไปแค่ไหน** — ไม่หายทั้งหมด **6 ใน 8 session** ถูก snapshot ไว้ใน
>    `backups/v13x_*/capture_v13x/` ตั้งแต่ตอนนั้น และ **byte-identical** กับต้นฉบับใน install tree
>    (เทียบ sha256 รอบ 84) จึงถูก **pin** ไว้ใน `docs/PF_CAPTURE_CORPUS.json` ชุด
>    `game_teleportcheck_0x4477` แล้ว
> 3. **สองแถวที่พิสูจน์ซ้ำไม่ได้** — `v141` และ `v142` **ไม่เคยถูก snapshot** เข้ามาใน worktree มีอยู่แค่ใน
>    `<repo>/../GameClient/` ซึ่งไม่เคยอยู่ใต้ version control และไม่มี hash pin ⇒ **unpinnable by
>    construction** verifier รายงานสองแถวนี้เป็น `UNPINNABLE` และ **ไม่นับเข้าในข้ออ้างใด ๆ**
>    ⇒ ประโยค "wire corpus 8 เฟรม" และบรรทัด "(8/8 byte-identical)" ใน §4 **อ่านได้ว่า 6/8 ที่ re-derivable
>    + 2 ที่ต้องเชื่อรายงานฉบับนี้เฉย ๆ** — ไม่ได้แก้ตัวเลขเดิมทิ้ง เพราะตอนเขียนมัน 8 จริง
> 4. **`count ≠ content`** — guard เดิมเช็ค `"77 44 0B 00 0F 01" in text` คือ substring ทั้งไฟล์ ไม่แยกทิศทาง
>    ซึ่ง**ผิดได้จริงบน corpus นี้**: `backups/v137_*/capture_v137/GAME_20260815_052412_181760_54676.txt`
>    มี byte string นั้น **2 ครั้ง** ในเฟรม server→client ที่ harness ประกอบเอง และ **ไม่มี inbound 0x4477
>    เลย** ไฟล์นี้ถูก pin ไว้เป็น **proven negative** เพื่อกันไม่ให้ใครกลับไปนับ substring อีก
>    guard ใหม่ถอด `DECOMPRESSED` + `STRUCTURAL_IDS` แล้ว pin **ทั้งเฟรม 23 ไบต์**
>    `12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 77 44 0B 00 0F 01 00`
> 5. **verifier วันนี้** — pure stdlib (เดิม `import capstone` แล้วไม่ได้ใช้เลย จึงรันใน gate ไม่ได้ด้วยซ้ำ),
>    31 guards, fail closed ทุกทาง: pinned file หาย / ถูกเขียนทับ / มีไฟล์แปลกปลอมในโฟลเดอร์ / client image
>    อ่านไม่ได้ ⇒ exit ≠ 0 ทั้งหมด · trap test ที่พิสูจน์ว่า guard ยิงจริงอยู่ที่
>    `tests/test_teleportcheck_0x4477_corpus.py`
>
> ข้อสรุปเชิงความหมายของรายงาน (identity / schema / field / "server ไม่ต้องตอบ") **ไม่เปลี่ยน** — ทั้ง 6 เฟรมที่
> pin ได้ยังเป็น value = 1 byte-identical และ `teleportcheck_reply=0` เหมือนเดิม

รอบ 61 (2026-08-18 scheduled) · chief · report-only additive · milestone สำรอง pre-approved (ii) จาก LOCK รอบ 60 · binary `GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` · capstone 5.0.7 (CS_MODE_32, ImageBase 0x400000, PE section table parsed) · reproduce: `py -3 tools/pf_teleportcheck_0x4477_static.py`

เป้า: ปิด **bounded unknown ของ MOVE-AUTHORITY-001** ("what `TeleportCheckVital 0x4477` requests/answers" — logged `semantics=unassigned no_response=1") ให้ถึงชั้น identity/schema/field แบบ byte-exact static แล้ว cross-check กับ wire corpus 8 เฟรม (v131 challenge + v136–v142)

> **ผลสรุปล่วงหน้า:** decode ครบทุกไบต์ที่อยู่ในอิมเมจ —
> - **Identity**: vtable `0xf0d66c`, RTTI `.?AVTeleportCheckVital@@`, id-slot `0x1082074`. id ตัวเลข `0x4477` **ไม่เคยเป็น immediate ในโค้ดเลย** (ทั้งอิมเมจ) → **runtime-assigned** ผ่าน `push "TeleportCheckVital"; call 0x89c080 (once-init singleton); call 0x89bd00 (id-assign); store ax→slot` — **กำแพงเดียวกับ ECHO005/007/008 เป๊ะ** (0x89c080 = MSVC once-init guard ไม่ใช่ hash)
> - **Schema**: serializer `0x5E6670` (owner เดียว = vtable +0x18) = **หนึ่ง tagged u16 field ที่ object `+0x14`, tag `0x0F`, nested version 0** — ไม่มี body field อื่น. in/out เลือกด้วย `cmp byte[esp+8],0` → `0x89a600`/`0x89a640`
> - **Field semantics**: `+0x14` = **ผลลัพธ์ของ UI confirm callback** (positive = 1) — wire ทุกเฟรมของ corpus = `... 12 77 44 | 0B 00 | 0F 01 00` = value **1** byte-identical (V131 ผูก `+0x14=1 → MARKER row 1 → Port Royal`)
> - **Direction/response**: เป็น **plain VitalData subclass** (vtable `+0x08 = 0x401b20` = shared framework const ตัวเดียวกับ cohort ECHO) ที่ลงทะเบียนเป็น **prototype ใน generic Vital factory** (`0x5ee9c4`) — **ไม่มี dedicated inbound handler** แยกจาก generic path · ทุก session ใน corpus บันทึก `teleportcheck_reply=0` แล้ว **heartbeat เดินต่อปกติ ไม่ค้าง** → **server ไม่จำเป็นต้องตอบ** (fail-closed แบบเดียวกับ TELEPORT_AUDIT001 ของ 0x25A2)
>
> **เกรด:** identity+schema+field = **A** (byte-exact static + wire cross-ref, serializer owner เดียว) · "server ไม่ต้องตอบ" = **B negative** (bounded — corpus ไม่มี reference-server ที่ตอบเฟรมนี้ เหมือน AUDIT001) · net report = ปิด unknown ของ MOVE-AUTHORITY-001 ที่ชั้น identity/schema/field, เหลือเฉพาะ `value != 1` (ไม่มีใน 8 เฟรม → ต้อง provocation อื่น)

---

## 1. Identity — vtable `0xf0d66c`, id runtime-assigned (กำแพง ECHO เดิม)

RTTI: string `.?AVTeleportCheckVital@@` @ `0x101fd0c`; type descriptor @ `0x101fd04` (อ้างใน ctor path `0x422ecc`, `0xbef5c6`).

Registration (สายเดียวในอิมเมจที่ push ชื่อคลาส):
```
0x00bee820: 68 640af300      push 0xf30a64              ; "TeleportCheckVital"
0x00bee825: e8 56d8caff      call 0x89c080              ; once-init singleton registry (MSVC guard)
0x00bee82a: 8bc8             mov ecx, eax               ; ecx = registry (this)
0x00bee82c: e8 cfd4caff      call 0x89bd00              ; thiscall id-assign(name) -> ax
0x00bee831: 66a3 74200801    mov word [0x1082074], ax   ; *** store runtime id -> id-slot ***
0x00bee837: c3               ret
```
get-id method (vtable `+0x10`):
```
0x00449430: 66 a1 74200801   mov ax, word [0x1082074]   ; return runtime id
0x00449436: c3               ret
```
**กำแพงยืนยัน:** ค่าคงที่ `0x4477` **ไม่ปรากฏเป็น immediate ที่ไหนเลยในอิมเมจ** (สแกน dword `0x00004477` ทั้งไฟล์ เจอครั้งเดียวเป็น displacement ของ `call rel32` โดยบังเอิญ ไม่ใช่ id) และ id-slot `0x1082074` ถูก**อ่านจุดเดียว** (get-id stub) เขียนจุดเดียว (registration) → id เป็น **runtime-assigned ล้วน** ตรงกับ ECHO008 §3 ("image ไม่มี id จริง; assign ตอน startup ผ่าน 0x89bd00").

vtable `0xf0d66c` (8 slot แรก):

| slot | ค่า | บทบาท |
|---|---|---|
| +0x00 | `0x449420` → `jmp 0x5e4610` | get-type thunk (indirect) |
| +0x04 | `0x44b700` | dtor/reset |
| +0x08 | `0x401b20` | **shared framework const — ตัวเดียวกับ cohort ECHO006/008 (`+08`)** |
| +0x0c | `0x721e40` | framework method |
| +0x10 | `0x449430` | **get-id** (`mov ax,[0x1082074]`) |
| +0x14 | `0x44bfe0` | framework method |
| +0x18 | `0x5e6670` | **serializer (owner เดียวของ 0x5E6670)** |
| +0x1c | `0x5f2190` | framework method |

`+0x08 = 0x401b20` เท่ากับค่า const ที่ทุก row ของ descriptor table `0xf363b4` แชร์ (ECHO008 §1) → **TeleportCheckVital เป็น VitalData subclass ธรรมดาในเฟรมเวิร์กเดียวกับ Community_*Vital cohort**.

## 2. Schema — serializer `0x5E6670` = single tagged u16 @ `+0x14`, tag `0x0F`

```
0x005e6670: 83c1 14          add ecx, 0x14              ; this -> field @ +0x14
0x005e6673: 807c2408 00      cmp byte [esp+8], 0        ; direction flag (in vs out)
0x005e6678: 6a 02            push 2                     ; wire mask/version 2
0x005e667a: 51               push ecx                   ; &field(+0x14)
0x005e667b: 8b4c240c         mov ecx, [esp+0xc]         ; ecx = archive/stream
0x005e667f: 6a 0f            push 0x0f                  ; *** field tag 15 (0x0F) ***
0x005e6681: 74 08            je 0x5e668b
0x005e6683: e8 783f2b00      call 0x89a600              ; serialize-out u16
0x005e6688: c2 0800          ret 8
0x005e668b: e8 b03f2b00      call 0x89a640              ; serialize-in u16
0x005e6690: c2 0800          ret 8
```
คือ body ของ TeleportCheckVital = **หนึ่ง u16 field เดียว** (tag `0x0F`) อ่าน/เขียนจาก object `+0x14`, nested version 0. ไม่มี field อื่น — ตรงกับ V131 boundary ("exactly one tagged u16 field at object `+0x14`; no additional nested body fields", pooled ctor/reset `0x44B980`, serializer `0x5E6670`) และตรงกับ wire (§4).

## 3. Direction — prototype ใน generic Vital factory, ไม่มี dedicated inbound handler

vtable `0xf0d66c` ถูกติดตั้ง 3 จุด: `0x44b9d4`/`0x44ba4f` (pooled ctor `0x44B980`) และ **`0x5ee9c4`** — จุดหลังอยู่ในฟังก์ชัน factory-builder ที่ alloc instance ของคลาส Vital หลายตัวติดกัน (`push 0x18; call 0x88d020; mov [obj],0xf86d6c (base VitalData vtable); mov [obj],0xf0d66c (TeleportCheckVital vtable)`) แล้วผูกเข้า prototype list. กล่าวคือคลาสนี้เข้าคิว dispatch ผ่าน **เส้นทาง generic เดียวกับ Vital ทุกตัว** — **ไม่มี handler เฉพาะสำหรับ "รับ 0x4477 จาก server"** (client เป็นฝ่ายส่งอย่างเดียว; ไม่มี consumer path ของ inbound 0x4477 นอกเหนือ generic factory).

## 4. Wire corpus — 8 เฟรม client→server byte-identical value=1, server reply=0, no stall

client→server decompressed (23 B) เหมือนกันทุก capture:
```
12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 77 44 0B 00 0F 01 00
└GSCN_RunTimeProtocolReq (0x6E6F)─┘ outer v0 ─┘ mask02 cnt1 ─┘ │ │  │
                                       nested: 12 77 44 = id 0x4477 ┘ │  │
                                                       0B 00 = ver 0 ─┘  │
                                                       0F 01 00 = tag0x0F u16=1 ┘
```
บันทึกใน journal: `MILESTONE V129_POST_ACTION1_RUNTIME_REQUEST_OBSERVED fields=(17527, 0, 1, '0F0100')` (id 17527=0x4477, ver 0, value 1, raw `0F0100`) และ `V136_MARKER1_POSITIVE_CONFIRM_CAPTURED value=1 teleportcheck_reply=0` — **หลังคลิก confirm บวก client ส่งเฟรมนี้ครั้งเดียว, server ไม่ตอบ (`reply=0`), heartbeat เดินต่อ** (seq 63→71+ หลังเฟรม) โดยไม่ค้าง.

| capture | มีเฟรม 0x4477 | payload `77 44 0B 00 0F 01` (value=1) | server reply |
|---|---|---|---|
| v131 (challenge) | ✓ frame 100 | ✓ | 0 |
| v136 | ✓ | ✓ | 0 |
| v137 | ✓ | ✓ | 0 |
| v138 | ✓ | ✓ | 0 |
| v139 | ✓ | ✓ | 0 |
| v140 | ✓ | ✓ | 0 |
| v141 | ✓ | ✓ | 0 |
| v142 | ✓ | ✓ | 0 |

(8/8 byte-identical — verifier `pf_teleportcheck_0x4477_static.py` guard G8)

## 5. เจตนาเชิงความหมาย (settled) + สิ่งที่เหลือ (bounded)

**Settled (static + wire):** `TeleportCheckVital 0x4477` = **client→server confirmation-request** ที่ UI confirm callback ยิงออกมา ค่า `+0x14` = ผลลัพธ์ callback (1 = positive). V131 ผูก `+0x14=1 → MARKER row 1 → Port Royal docking-confirm`. เป็น plain VitalData ที่ผ่าน generic factory ไม่มี inbound handler เฉพาะ. ทุก corpus session server ไม่ตอบแล้วไม่ค้าง → **การไม่ตอบเฟรมนี้ถูกต้อง (fail-closed)** — ตอกย้ำข้อสรุป TELEPORT_AUDIT001 (0x25A2) ว่า generic first-Req/heartbeat ack ครอบคลุมพอ.

**Bounded remaining:** corpus มีเฉพาะ **value = 1** (positive). ความหมายของ `+0x14 != 1` (เช่น negative/cancel = 0 หรือค่าอื่น) และการมีอยู่ของ reference-server response ใด ๆ ต่อเฟรมนี้ **ยังพิสูจน์ static ไม่ได้** (ไม่มีใน 8 เฟรม, `references/sources/` ว่าง) — ต้อง UI provocation แบบ negative-confirm หรือ original-server capture จึงจะขยายได้. ไม่กระทบข้อสรุป "server ไม่ต้องตอบ" เพราะแม้แต่ positive ก็ไม่ถูกตอบและไม่ค้าง.

**ผลต่อ matrix (report-only, ยังไม่ flip):** ปิดวงเล็บ "what `TeleportCheckVital 0x4477` requests/answers" ของ MOVE-AUTHORITY-001 ที่ชั้น identity/schema/field. แถว `local_player_movement_authority` ยังคง `in_progress` (รอ rubber-band/reference ตามโน้ตเดิม) — TeleportCheck ไม่ใช่ movement-correction แต่เป็น UI-confirm ack แยกส่วน จึงไม่เปลี่ยน authority verdict.

## 6. Evidence (read-only)

- `GameClient\GameClient.local.bin` — SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` (disassembled read-only)
- `GameClient\capture_v131\GAME_2*.txt` … `capture_v142\GAME_2*.txt` — client→server 0x4477 corpus (8 เฟรม)
- verifier: `tools/pf_teleportcheck_0x4477_static.py` (16 guards, exit 0 = PASS)
- อ้างอิงต่อยอด: `reports/PF_RE_V131_TeleportCheck_Challenge_Echo_Capture_20260815.md`, `reports/PF_MOVE_AUTHORITY001_LOCAL_PLAYER_MOVEMENT_AUTHORITY_STATIC_20260818.md`, `reports/PF_TELEPORT_AUDIT001_CLIENT_25A2_FIRSTREQ_ECHO_CORPUS_20260818.md`, `reports/PF_CHAT_ECHO008_LOCALTALK_COHORT_VTABLE_NAME_MAP_STATIC_20260818.md`

ไม่แตะ ledger/matrix/src/canonical · ไม่รัน gate · additive report-only (precedent `cec8c82`)
