# PF_SPLIT_OPERATE003 — verb 0x16 → op6 is reused across two inventory panels, and the static caption route for the split label is evidenced-closed (static disasm + read-only client assets)

รอบ: chief scheduled รอบ 70 (2026-08-18) · milestone สำรอง pre-approved (LOCK รอบ 69 next②: "split_stack ขาต่อสุดทาง")
เกรด: **B** (structural anchors byte-exact = A-level; headline เป็น bounded refinement + negative closure = B โดยรวม — ไม่ overclaim)
สถานะ: **split_stack ยัง `in_progress`** (characterized เพิ่ม, ไม่ flip runtime_pass) · report-only / additive: ไม่มี src/scenario/ledger ใหม่ · ไม่แตะ coverage grade (แตะเฉพาะ `notes` prose ซึ่ง seam grade-digest ไม่นับ)

## 0. เป้า และที่มา

SPLIT-OPERATE-001 (รอบ 68) พิสูจน์ว่า stack-split ไม่มี opcode เฉพาะ — ทุก item action ขี่ `ItemOperateVitalReq 0x4BED` แยกด้วย operation byte เดียว, op6 = quantity-op producer (factory `0x59F870`).
SPLIT-OPERATE-002 (รอบ 69) enumerate op6 factory ได้ **4 call site พอดี** → op6 เป็น shared quantity-op family; bound split candidate ไปที่ inventory verb `eax==0x16` (site `0x5A3532`) ใน dispatcher `[0x5A2A70,0x5A40B0)` แล้วหยุด พร้อมระบุ next hop: **resolve caption ของ numeric dialog id `0x12` หรือ live capture**.

003 เดิน next hop นั้นให้สุดเท่าที่ static ไปได้ ผลออกมาเป็น **การกลั่น (refinement) ไม่ใช่การกลับคำ** ของ 002 สองข้อ ทั้งคู่ byte-exact:

## 1. R1 — verb 0x16 ไม่ unique ทั้งไบนารี: 2 ใน 4 op6 site gate ด้วย `cmp eax,0x16`

จาก op6 factory `0x59F870` 4 caller เดิม (`0x57D1F4 0x58294D 0x5A3532 0x5BA208`), **สองตัว** ถูก guard ด้วย `cmp eax, 0x16` (ไบต์ `83 F8 16`) ทันทีก่อนลำดับ dialog→op6:

| op6 site | ฟังก์ชันที่อยู่ | verb guard | dialog helper | หมายเหตุ |
|---|---|---|---|---|
| **C** `0x5A3532` | dispatcher `0x5A2A70` (มี op4=MOVE verb2) | `cmp eax,0x16` @`0x5A349B` | `call 0x5A1630` @`0x5A34E2` | backpack move/equip dispatcher |
| **D** `0x5BA208` | fn แยก `0x5B9F70` (SEH, boundary `C3 CC`) | `cmp eax,0x16` @`0x5BA183` | `call 0x5A1630` @`0x5BA1D0` | อีกพาเนล inventory-like |

- ทั้งสอง body วิ่งผ่าน **numeric-input dialog helper เดียวกัน `0x5A1630`** ก่อนเรียก op6 (e8-rel target ยืนยัน == `0x5A1630` ทั้งสอง)
- ทั้งสอง site อยู่ **คนละฟังก์ชัน** → action code `0x16` + quantity dialog ตัวเดียวกัน **ถูกใช้ซ้ำข้ามพาเนล (อย่างน้อย 2)**
- dispatcher มี switch ladder หลาย verb: `cmp eax, 0x2d / 0x35 / 2 / 0x16` — verb 2 = MOVE(op4), verb 0x16 = op6

**ความหมาย:** การที่ action code `0x16` ผูกกับ quantity-op (op6) และ dialog เดียวกันในหลายพาเนล **สอดคล้องกับ** สมมุติฐาน "generic split/divide-by-quantity ที่ reuse ข้ามพาเนล" — แต่ **ยังไม่ใช่ป้าย "split" เชิงบวก**: op6 ไม่มี destination slot จึงเข้ากันได้พอ ๆ กันกับ shared drop-N / destroy-N / give-N. 002 พูดถูกว่า "verb 0x16 = op6 site เดียว *ใน dispatcher*"; 003 เพิ่มว่า verb 0x16 เอง **ไม่ unique ทั้งไบนารี** (มี op6 site ที่ verb 0x16 อีกตัวใน `0x5B9F70`).

span-hash pin (byte-identical): body C `[0x5A349B,0x5A3537)` = `1E2EB3E2…089979` · body D `[0x5BA183,0x5BA20D)` = `9C84D296…8E5ED4`.

## 2. R2 — เส้นทาง caption แบบ static ปิดแล้ว (evidenced)

numeric dialog เป็น **generic reusable control** ไม่ใช่ dialog เฉพาะ split:

- `Data/GUI/Model/Common_NumInput.model` (และ `Common_NumberInput2/3.model`) = plaintext `<UIControlData>` XML (UTF-8 BOM) **ไม่มี caption ฝังใน model** — ไม่มีไฟล์ `.model` ชื่อ split/divide เลย
- caption ถูก resolve ตอน runtime จาก **packed text table `B_TEXTDATA_TH.pc_`** (file magic `$pcz`) และ UI Lua (`*.lu_` ก็ `$pcz`-packed เช่นกัน)
- จึง **ไม่มี client asset ที่อ่านได้** ที่ map dialog id `0x12` → caption "split" โดยไม่ถอดรหัส/แตก packed proprietary (นอกขอบเขต + ไม่แตะ proprietary)

**สรุป R2:** static caption route ปิดด้วยหลักฐาน (assets packed) → hop เดียวที่เหลือสำหรับป้าย split เชิงบวก = **live capture** ของ verb-0x16 numeric dialog + เฟรม op6 ที่มันยิง.

## 3. แก้ความเข้าใจข้างเคียง — `0x42AB40` = destructor ไม่ใช่ dialog opener

ใน body verb-0x16 มี `call 0x42AB40` ก่อน op6 ซึ่งอาจเข้าใจผิดว่าเป็น "เปิด dialog ด้วย id". ที่จริง `0x42AB40` คือ **temp-object destructor**: SEH prologue `6A FF 68 53 53 B8 00 64 A1 00 00 00 00`, เขียน vtable สองครั้ง (`0xF0B978` → `0xF0B8FC`) และเรียก free/dtor `0x88D060`. ส่วน dialog id `0x12` เป็น **stack local** ตั้งที่ `0x5A34D7` (`C7 84 24 80 01 00 00 12 00 00 00` = `mov dword [esp+0x180], 0x12`) พร้อมพารามิเตอร์กล่องตัวเลข `[esp+0x178]` (0xa แล้ว 0xFFFFFFFF) — ถูกใช้ภายใน body ไม่ใช่ argument ของ call ใด.

## 4. หลักฐาน / reproducibility

- ไบนารี read-only: `GameClient/GameClient.local.bin` sha256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` (14,759,424 B)
- verifier: `tools/pf_split_operate_verb_panels_static.py` — 21 static guards, exit 0 = PASS (capstone CS_MODE_32, ImageBase 0x400000, PE section table parsed)
- regression test: `tests/test_split_operate_verb_panels_static.py` — 11 cases (pefile + capstone)
- readable client assets ใช้เป็นหลักฐาน: `Data/GUI/Model/Common_NumInput.model` (plaintext), `Data/B_TEXTDATA_TH.pc_` (magic `$pcz` = packed)
- ไม่มี network / GameClient runtime / canonical DB ถูกแตะ

## 5. Governance

report-only additive: ไม่มี server-source change, ไม่มี scenario, ไม่มี ledger entry (ledger คง 24), ไม่มี grade change ใน coverage matrix. อัปเดตเฉพาะ `notes` prose ของแถว `split_stack` ให้ชี้มา 003 (seam grade-digest ไม่นับ prose → ไม่ขยับ). split_stack ยัง `in_progress`.

**next hop (ปรับจาก 002):** static caption route ปิดแล้ว → เหลือทางเดียว = **live capture** ของ verb-0x16 numeric dialog + op6 frame (อยู่ในคิว GT-015). ไม่ต้องไล่ caption แบบ static อีก.
