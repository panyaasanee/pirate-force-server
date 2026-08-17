# PF_CHAT_ECHO007 — LocalTalk render-tag `+0x44` = per-class compile-time constant (static disasm)

รอบ 57 (2026-08-18 scheduled) · chief · report-only additive · binary `GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` · capstone 5.0.7 (CS_MODE_32, ImageBase 0x400000)

เป้า: ปิด **next-hop #1 ของรอบ 56/LOCK** = หา parse/populate ที่เขียน `[obj+0x44]` เป็น nonzero บน object ตระกูล vtable `0xF363B4..0xF365C4` แล้วดูว่า source = wire channel/identity field หรือไม่

> **ผลสรุปล่วงหน้า:** พบ **คำสั่ง SET `+0x44` เดียวต่อคลาส** แล้ว และมันคือ **immediate constant ในตัว constructor ของแต่ละคลาส** (per-class identity) — **ไม่ใช่** runtime write จาก wire. รอบนี้จึง (1) **ปิดคำถาม single-SET** ที่ ECHO005 ค้างไว้ (ด้าน "SET มาจากไหน" ตอบชี้ขาดระดับ A: มาจาก class identity ไม่ใช่ payload), และ (2) **แก้ข้อสรุปนำของ ECHO006** ที่ว่า "`+0x44` zero-init ในตัว ctor → ต้องมี nonzero write ตอน runtime (parse)" — ข้อสรุปนั้นจริงเฉพาะคู่ target/sibling; คลาสที่ render `540` เป็น **คนละคลาส** ที่ ctor bake constant nonzero ตั้งแต่ต้น **ไม่ต้องมี runtime write เลย**
>
> **เกรด net ของ Q2 positive คงที่ = B** (ไม่ดันเป็น A) เพราะลิงก์ปลายทาง "vital id `0xAC52` (LocalTalk) → คลาสไหนในตระกูล → `+0x44`=? → 539/540" ยังผ่าน **runtime type-registry ที่ key ด้วย hash (`call [0xC3B7AC]`)** ซึ่งในไฟล์อิมเมจ uninitialized → เหลือสังเกตชั้น runtime (GT-012). แต่ residual นี้กลายเป็น **คำถาม identity/registry ล้วน ปราศจากการพึ่ง wire-payload โดยสิ้นเชิง** — ซึ่งเป็นการตอกย้ำ Q2 **negative = A** ที่หนักแน่นที่สุดเท่าที่ static ทำได้

---

## 1. พบ constructor cohort ของ display/log-message object — `+0x44` เป็น per-class immediate

รอบ 56 ตรวจแค่ 2 constructor (target `0x6425D0` vtable `0xF3640C`, sibling `0x642540` vtable `0xF363E0`) ซึ่งบังเอิญเขียน `+0x44 = 0` (ผ่าน `bl`). รอบนี้สแกน byte-write ทั้งหมดไปที่ `[reg+0x44]` ใน `.text` (152 จุด) แล้วคัดเฉพาะย่าน message/render (`0x63Axxx`/`0x642xxx`, layout ตรงกัน: install vtable → `call [0xC3B478]` = `std::wstring` ctor ที่ `+0x28` → SET `+0x44`) พบ **cohort ของ constructor ที่ bake `+0x44` เป็นค่าคงที่ต่างกันต่อคลาส**:

| constructor (install vtable) | `+0x44` | `+0x45` | รูปแบบ SET |
|---|---|---|---|
| `0xf35c2c` (`0x63a570`) | `0x0c` | — | `C6 46 44 0C` immediate |
| `0xf35c58` (`0x63a610`) | `0x00` | — | `88 5E 44` (bl=0) |
| `0xf35cb0` (`0x63a740`) | `0x07` | — | `C6 46 44 07` immediate |
| `0xf35cdc` (`0x63a84f`) | `0x04` | — | `C6 46 44 04` immediate |
| `0xf35d8c` (`0x63abcf`) | `0x03` | — | `C6 46 44 03` immediate |
| `0xf35db8` (`0x63ac6f`) | `0x01` | `0x04` | `C6 46 44 01` / `C6 46 45 04` |
| `0xf35e10` (`0x63adff`) | `0x06` | — | `C6 46 44 06` immediate |
| `0xf36490` (`0x642840`) | `0x05` | `0x00` | `C6 46 44 05` / `88 5E 45` |
| `0xf363e0` (`0x642540`, sibling — ECHO006) | `0x00` | `0x00` | `88 5E 44` / `88 5E 45` |
| `0xf3640c` (`0x6425D0`, target row#2 — ECHO006) | `0x00` | — | `88 5E 44` (bl=0) |

**ข้อสรุป:** `+0x44` (และ `+0x45` ที่บางคลาสใช้) เป็น **discriminator byte ประจำคลาส ที่ถูก bake เป็น immediate ตอน construct** — ไม่ใช่ zero-init สากล. คลาสที่ render `539` คือคลาสที่ bake `+0x44 = 0` (target/sibling + `0xf35c58`); คลาสที่ render `540 [ทั่วไป]` คือคลาสที่ bake `+0x44` เป็น nonzero (`0x01,0x03,0x04,0x05,0x06,0x07,0x0c`).

## 2. Render gate byte-exact: `539/540` = zero-vs-nonzero บน `+0x44`

```
0x006405e7  38 58 44         cmp  byte [eax+0x44], bl     ; bl = 0
0x006405ea  75 0a            jne  0x6405f6
0x006405ec  68 1b 02 00 00   push 0x21b                   ; +0x44 == 0  -> id 539
0x006405f1  e9 ..            jmp  0x63fa2f
0x006405f6  68 1c 02 00 00   push 0x21c                   ; +0x44 != 0  -> id 540 [ทั่วไป]
0x006405fb  e9 ..            jmp  0x63fa2f
```

gate อ่าน `+0x44` ของ object แล้วเลือก resource id แบบ **binary (0 → 539, ≠0 → 540)**. object ที่ถึง gate นี้เป็น cohort เดียวกับข้อ 1 (layout `+0x28` wstring / `+0x44` tag; downcast chain `0x639FD0` → node ตาม ECHO005/006). ดังนั้น id ที่ render = **ฟังก์ชันของ constant ที่ ctor ของคลาสนั้น bake ไว้** ล้วน ๆ

## 3. ตัด wire-source ออกชี้ขาด — runtime `+0x44` write ที่มี อยู่คนละตระกูล object

ในย่าน `0x63xxxx` มี runtime write ไป `+0x44` อยู่ 3 จุด แต่**ไม่ใช่** object ตระกูล message descriptor และ**ไม่ได้อ่านจาก wire**:

| จุด | คำสั่ง | source | object มาจาก |
|---|---|---|---|
| `0x63b88a` | `mov [esi+0x44], al` | `al = sete(cmp [ebx+0x94],1)` (mode flag) | registry lookup (`call 0x642320`→`0x88f2b0`) |
| `0x63d900` | `mov [esi+0x44], al` | `al = sete(cmp [ebx+0x94],1)` | factory `call 0x63c5b0` |
| `0x63f1f6` | `mov [edi+0x44], cl` | `cl = [esi+0x14]` (local object field) | factory `call 0x63ce50` |

ทั้งสามเขียน **boolean/สำเนา field ของ local object** (เช่น "is-me/selected" จาก mode `[ebx+0x94]==1`) ลง object ที่ factory (`0x63c5b0`/`0x63ce50`) สร้าง — เป็นตระกูล list/entry view คนละชนิดกับ display-message cohort. **ไม่มีจุดใดอ่านจาก network buffer**

รวมกับหลักฐานเดิม ECHO004 (de/serializer `0x65AD40` ของ payload `0xAC52` อ่านแค่ 2 wstring, ไม่มี scalar/enum/channel byte) → **ไม่มีเส้นทางใดที่ wire/payload เขียนหรือกำหนด `+0x44` ของ message cohort ได้เลย**

## 4. แก้ข้อสรุปนำของ ECHO006

ECHO006 สรุปนำว่า: *"constructor zero-init `+0x44/+0x45` → ไม่ใช่ per-class const → การได้ id 540 (`+0x44!=0`) ต้องมี **nonzero write ทีหลัง (runtime parse)**"*. รอบนี้แสดงว่า **ข้อสรุปนั้นถูกเฉพาะกับ 2 ctor ที่ ECHO006 ดู** (ซึ่ง bake 0 → render 539). สำหรับ id 540: object คือ **คนละคลาส** (vtable ต่างกัน) ที่ ctor **bake `+0x44` เป็น constant nonzero ตั้งแต่ construct** → **ไม่ต้องมี runtime nonzero write** และไม่มีจริง (ข้อ 3) → hypothesis "runtime parse เขียน `+0x44`" **ถูกหักล้าง (falsified)** สำหรับ message cohort

---

## verify (byte-exact · .text off = VA − 0x400C00 — ตรง ECHO005/006)

| จุด | VA | file off | bytes | disasm |
|---|---|---|---|---|
| install vtable `0xf35c2c` | `0x63a570` | `0x239970` | `c7062c5cf300` | `mov [esi], 0xf35c2c` |
| SET `+0x44`=0x0c | `0x63a57c` | `0x23997c` | `c646440c` | `mov byte [esi+0x44], 0xc` |
| install vtable `0xf35cb0` | `0x63a740` | `0x239b40` | `c706b05cf300` | `mov [esi], 0xf35cb0` |
| SET `+0x44`=0x07 | `0x63a74c` | `0x239b4c` | `c6464407` | `mov byte [esi+0x44], 7` |
| SET `+0x44`=0x04 (`0xf35cdc`) | `0x63a85b` | `0x239c5b` | `c6464404` | `mov byte [esi+0x44], 4` |
| SET `+0x44`=0x03 (`0xf35d8c`) | `0x63abdb` | `0x239fdb` | `c6464403` | `mov byte [esi+0x44], 3` |
| SET `+0x44`=0x01 (`0xf35db8`) | `0x63ac7b` | `0x23a07b` | `c6464401` | `mov byte [esi+0x44], 1` |
| SET `+0x45`=0x04 (`0xf35db8`) | `0x63ac7f` | `0x23a07f` | `c6464504` | `mov byte [esi+0x45], 4` |
| SET `+0x44`=0x06 (`0xf35e10`) | `0x63ae0b` | `0x23a20b` | `c6464406` | `mov byte [esi+0x44], 6` |
| install vtable `0xf36490` | `0x642840` | `0x241c40` | `c7069064f300` | `mov [esi], 0xf36490` |
| SET `+0x44`=0x05 | `0x64284c` | `0x241c4c` | `c6464405` | `mov byte [esi+0x44], 5` |
| target SET `+0x44`=0 (`0xf3640c`) | `0x64261c` | `0x241a1c` | `885e44` | `mov byte [esi+0x44], bl` |
| sibling SET `+0x44`=0 (`0xf363e0`) | `0x64257c` | `0x24197c` | `885e44` | `mov byte [esi+0x44], bl` |
| render gate cmp `+0x44` | `0x6405e7` | `0x23f9e7` | `385844` | `cmp byte [eax+0x44], bl` |
| gate jne → 540 | `0x6405ea` | `0x23f9ea` | `750a` | `jne 0x6405f6` |
| push id 539 (`+0x44`==0) | `0x6405ec` | `0x23f9ec` | `681b020000` | `push 0x21b` |
| push id 540 (`+0x44`!=0) | `0x6405f6` | `0x23f9f6` | `681c020000` | `push 0x21c` |
| runtime write#1 (คนละตระกูล) | `0x63b88a` | `0x23ac8a` | `884644` | `mov byte [esi+0x44], al` (al=sete) |
| runtime write#2 (คนละตระกูล) | `0x63f1f6` | `0x23e5f6` | `884f44` | `mov byte [edi+0x44], cl` (cl=[esi+0x14]) |

## grade
- **Q2 negative = A เดิม (ตอกย้ำหนักที่สุด):** payload `0xAC52` ไม่มี field เลือก tag **และ** ไม่มีเส้นทางใดที่ wire เขียน `+0x44` ของ message cohort ได้ → tag เป็น identity-driven ล้วน 100%
- **Q2 positive = B เดิม (net ไม่เปลี่ยน):** **แต่ปิด sub-question "single-SET" ที่ ECHO005 ค้าง** — SET เดียวต่อคลาสคือ immediate ในตัว ctor = class identity (byte-exact) → ด้าน "SET มาจาก identity ไม่ใช่ payload" = **A**. เหตุที่ net ยังไม่ดัน B→A: การ map `0xAC52 → คลาส → constant → 539/540` ยังผ่าน runtime hashed registry (uninitialized ในอิมเมจ) → เหลือสังเกต attended (GT-012)
- **ไม่ re-pin canonical / ไม่รัน Windows gate** (report-only additive, ไม่แตะ ledger/matrix/src) — เกณฑ์เขียวเดิม 108 = pytest 477/0 + canonGuard=0 + ledger 23 + domains 8 ยังใช้

## nonclaims
1. ไม่ได้ยืนยัน static ว่า vital id `0xAC52` map ไปคลาส cohort ตัวใด (registry key เป็น hash รันตอน startup) → คลาสจริงของ LocalTalk (จึงค่า `+0x44` จริง = 539 หรือ 540) ต้องสังเกต runtime — GT-012
2. ไม่ได้ให้ RTTI ชื่อคลาสของ cohort (อิมเมจไม่มี COL/TypeDescriptor ที่ resolve ได้ผ่าน `[vtable-4]`; ชื่อผูกผ่าน hashed registry ตาม ECHO005) — คงชื่อคลาสเป็น vtable VA
3. static ล้วน — ไม่มี client-observable claim (ชั้นนั้นเป็นของ GT-012 รอบใหญ่)

## next hop
1. **runtime (GT-012, attended):** จด label ที่ LocalTalk render จริง — ถ้า `[ทั่วไป]` (540) ⇒ คลาสของมันมี `+0x44 != 0` (หนึ่งใน `{1,3,4,5,6,7,0xc}`); ถ้า 539 ⇒ `+0x44 == 0`. ผลลัพธ์นี้ pin binding `0xAC52 → คลาส → constant` ที่ static ทำไม่ได้ → **ปิด B→A จบ**
2. **static (option):** map cohort vtable (`0xf35c2c..0xf36490`) → get-type thunk → node เพื่อจับคู่กับ descriptor table 12-row (ECHO006 §1) และดูว่าคลาสใด bake `+0x44` ตรงกับ label channel ใด (แต่การจับคู่ id→คลาสสุดท้ายยังผูก runtime registry อยู่ดี)
