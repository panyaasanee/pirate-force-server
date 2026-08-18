# PF_SPLIT_OPERATE002 — the op6 quantity-op is a four-site family, and the stack-split candidate is bounded to one inventory verb (static disasm + server cross-check)

รอบ 69 (2026-08-18 scheduled) · chief · report-only additive · milestone สำรอง pre-approved (split_stack — LOCK รอบ 68 next②, ขาต่อของ SPLIT-OPERATE-001) · binary `GameClient/GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` · capstone 5.0.7 (CS_MODE_32, ImageBase 0x400000, PE section table parsed) · reproduce: `py -3 tools/pf_split_operate_family_static.py`

เป้า: ปิดคำถามค้างของ SPLIT-OPERATE-001 ("op6 ≡ split หรือไม่ — ต้อง resolve verb-code→UI ของ `eax==0x16` หรือ live capture") ให้ถึงชั้นที่ static disasm ไปได้สุด โดย **ไม่แตะ v141 (immutable), ไม่แตะ persistence characters/accounts** (ไม่ชนคำถามค้างทั้งสอง) และเคารพ "checkpoint แคบ ≠ เสร็จ" — split_stack ยัง `in_progress` ไม่ flip runtime_pass

> **ผลสรุปล่วงหน้า:** op6 **ไม่ใช่ opcode ของ split** — มันคือ **quantity-op family ที่มี call site 4 จุดพอดี** ในอิมเมจ ทุกจุดส่งรูปเดียวกันและ **ไม่มี destination slot** ที่ไหนเลย:
> - **op6 factory `0x59F870` = 4 caller พอดี** (byte-exact e8-rel32 scan ทั่ว `.text`): `0x0057D1F4`, `0x0058294D`, `0x005A3532`, `0x005BA208` — เทียบ op4(move) `0x59F7C0` = **1 caller** (`0x5A3491`, verb `eax==2`) และ op3 `0x59F780` = **1 caller** (`0x5B9D0C`) → op6 เป็น family จริง ไม่ใช่ artifact ของ scan
> - **รูปสาย op6 สม่ำเสมอทุกจุด:** factory รับ 3 dword arg `(qty_low, qty_high, item_handle)` (`ret 0xC`) เข้ารหัส `value32(+0x18)=item_handle` และ `qword(+0x20/+0x24)=จำนวน 64-bit` — **ไม่มี destination-slot argument ที่ callsite ใดเลย** (ต่างจาก op4/move ที่ value32 = ปลายทาง)
> - **inventory action dispatcher = ฟังก์ชันเดียว** `[0x5A2A70, 0x5A40B0)` (prologue มี SEH, ไม่มี int3 คั่นตลอด body) ที่บรรจุทั้ง **op4=MOVE producer (verb `eax==2` @`0x5A3491`)** และ **op6 site เดียว (verb `eax==0x16` @`0x5A3532`)** — อีก **3 op6 site อยู่ใน 3 ฟังก์ชันแยก** (start `0x0057D041`, `0x00582730`, `0x005B9F70`) นอก dispatcher → **ในตัว dispatch ของกระเป๋า verb 0x16 เป็น quantity-op เดียว = split candidate ที่ถูก bound แล้ว**
> - verb 0x16 เปิด **numeric-input dialog resource `0x12`** (`0x5A34D7`), guard **> 0 เข้ม** (`0x5A34EF`) แล้วจึงเรียก op6
> - **ช่องว่าง server เดิม:** `current/pf_login_game_server_v141.py` สร้าง response ของ operation-4 (`make_item_operate_move_delta_success`) และ decode พิเศษ operation-5 (equip) แต่ **ไม่มี handler ของ operation 6/3** → ทั้ง 4 verb ของ op6 ยัง unimplemented ฝั่ง server
>
> **เกรด:** enumeration byte-exact (4 callsite + arg contract + dispatcher membership) + verb-0x16 path + server gap = **A** (reproduced by verifier 31 guards, cross-checked กับ server source) · **ยังไม่ claim "verb 0x16 ≡ split"** — op6-ไม่มี-destination เข้ากันได้พอ ๆ กับ backpack drop-N/destroy-N ป้าย "split" ต้อง (i) resolve caption ของ dialog resource `0x12` หรือ (ii) live capture = next hop · net: split_stack คง `in_progress` (search space แคบลงจาก "op6 verb ที่ไหนสักที่" → "verb 0x16 ใน inventory dispatcher, 1 ใน 4 op6 verb")

---

## 1. op6 factory `0x59F870` — operation immediate, field layout, calling contract (byte-exact)

```
0x0059f870: push 0; push 0xf0a90c; mov ecx,0x1030618; call 0x59f0d0   ; alloc ItemOperateVitalReq
0x0059f885: mov ecx,[esp+0xc]       ; arg3 = item handle
0x0059f889: mov edx,[esp+4]         ; arg1 = qty low
0x0059f88d: mov [eax+0x18], ecx     ; *** value32 (+0x18, tag 0x14) = item handle ***
0x0059f890: mov ecx,[esp+8]         ; arg2 = qty high
0x0059f895: mov byte [eax+0x14], 6  ; *** operation (+0x14, tag 0x0B) = 6 ***  (C6 40 14 06)
0x0059f899: mov [eax+0x20], edx     ; *** qword low  (+0x20, tag 0x32) = qty low ***
0x0059f89c: mov [eax+0x24], ecx     ; *** qword high (+0x24)          = qty high ***
0x0059f8ab: ret 0xc                 ; stdcall, three dword args
```

รูปสาย op6 = `op6(qty_low, qty_high, item_handle)` → `operation=6 · value32=item_handle · qword=จำนวน 64-bit`. ตรงกับ serializer `0x5E5AF0` ที่ SPLIT-OPERATE-001 pin ไว้ (field `+0x14` tag 0x0B width 1 / `+0x18` tag 0x14 width 4 / `+0x20` tag 0x32 width 8) — **field เดียวกับ move/equip แต่ความหมายผูกกับ operation**: op6 ใช้ `qword` เป็น "จำนวน" ไม่ใช่ item-identity นี่คือกับดักที่ implementation ของ server จะพังถ้าถือว่า qword = identity เสมอ

## 2. Enumeration — op6 มี 4 caller พอดี, op4/op3 มี 1 caller (cross-check)

e8-rel32 scan ทั่ว `.text` (byte-exact, reproducible):

| factory | operation | callers | จำนวน |
|---|---|---|---|
| `0x59F780` | op3 (identity-only) | `0x5B9D0C` | **1** |
| `0x59F7C0` | op4 (MOVE) | `0x5A3491` (verb `eax==2`) | **1** |
| `0x59F870` | op6 (quantity) | `0x57D1F4`, `0x58294D`, `0x5A3532`, `0x5BA208` | **4** |

op4/op3 มี caller เดียว ยืนยันว่า 4 caller ของ op6 **ไม่ใช่ผลของ scan ที่หลวม** — op6 คือ quantity-op family จริง มี UI entry-point อย่างน้อย 4 จุด (split ในกระเป๋า / quantity op ของพาเนลอื่น เช่น sell-N/deposit-N/withdraw-N). ทุก callsite ปิดท้ายด้วย 3 push แล้ว `call 0x59F870` (สอดคล้อง `ret 0xC`) และ**ไม่มี push destination-slot** ที่ใด — op6 wire shape สม่ำเสมอ

byte-span pin ของหน้าต่าง `[call-0x14, call+5]` ทั้ง 4 จุด (ดู verifier `OP6_SITE_SPANS` / test `SPANS`) — ทุกจุด byte-identical

## 3. Membership — verb 0x16 เป็น op6 site เดียวใน inventory action dispatcher

```
prologue 0x5A2A70:  55 8B EC 83 E4 F8 6A FF 68 D7 AF B9 00
                    push ebp; mov ebp,esp; and esp,-8; push -1; push 0xB9AFD7 (SEH)
```

- dispatcher = ฟังก์ชันเดียว `[0x5A2A70, 0x5A40B0)` — prologue ข้างบน, **ไม่มี int3 คั่นตลอด body** (ตรวจถึง `0x5A3540`), และ prologue ถัดไปเริ่มที่ `0x5A40B0` (ขอบบน)
- ภายใน dispatcher มี **op4=MOVE producer call** (`0x5A3491`, verb `eax==2` — generalized item move ที่ MOVE-ISOLATION-001 พิสูจน์ว่า isolate ต่อ session) และ **op6 site เดียว** (`0x5A3532`, verb `eax==0x16`)
- 3 op6 site ที่เหลืออยู่ **นอก dispatcher** ใน 3 ฟังก์ชันแยก (start `0x57D041`, `0x582730`, `0x5B9F70`) — ไม่มีอันไหน start = `0x5A2A70`

→ **ในตัว dispatch ของกระเป๋า (ฟังก์ชันที่ move/equip ของ backpack วิ่งอยู่) verb 0x16 คือ quantity-op เดียว** จึงเป็น split candidate ที่ถูก bound แล้ว ส่วน quantity-op อีก 3 ตัวอยู่คนละพาเนล (ไม่ใช่ backpack split)

## 4. verb 0x16 path — dialog resource 0x12, positive guard, op6

```
0x5A349B: cmp eax, 0x16                         ; 83 F8 16
0x5A34D7: mov dword [esp+0x180], 0x12           ; C7 84 24 80 01 00 00 12 00 00 00  (numeric-input dialog resource 0x12)
0x5A34E2: call 0x5A1630                         ; quantity dialog
0x5A34EF: cmp dword [eax+0x2c], 0 ; jg/jl       ; 83 78 2C 00  (result ต้อง > 0, positive-only)
0x5A3517: mov esi,[esi+0x94]                    ; item handle
0x5A3532: call 0x59F870                         ; op6(qty_low, qty_high, item_handle)
```

verb 0x16 = ลำดับ "เปิด dialog จำนวน (res 0x12) → กัน ≤0 → op6 ด้วย {handle, จำนวน}". ทั้ง case body `[0x5A349B, 0x5A3537)` pin ด้วย span-hash

## 5. Server gap — op4 response + op5 decode, ไม่มี op6/op3

`current/pf_login_game_server_v141.py` (read-only, immutable):
- `ITEM_OPERATE_REQ_VITAL = 0x4BED` · `parse_item_operate_req` → `(operation, value32, item_identity)` จาก tag 0x0B/0x14/0x32
- `make_item_operate_move_delta_success(...)` = response ของ **operation-4** (destination-slot move) · dispatch decode ทำ special-case **operation-5** (`V123_EQUIP_FROM_BAG_OPERATION = 5`)
- **ไม่มี** `operation==6` / `operation==3` handler และ**ไม่มี** `make_item_operate_split`/`..._quantity` → op6 (quantity) และ op3 (identity-only) มี client producer แต่ไม่มี server handler

→ split (และ quantity-op ทั้ง family) = **characterized แต่ยังไม่ implemented** ฝั่ง server

## 6. Response & persistence lanes (คงเดิมจาก 001, ยังไม่ implement)

- **Response:** `ItemOperateVitalRes 0x4C13` (สายเดียวกับ move-merge success ของ HYP-PF-011) — split จะใช้ res path นี้ + `u16tag(0x0F, quantity)`
- **Persistence:** สองตารางเดิม `character_backpack_items` (rows) + `character_backpacks.updated_at` (GT-002 runtime-proven, MOVE-ISOLATION-001 รอบ 67) — split = แตกหนึ่ง row (qty n) → สอง rows (n−k, k) ในบัญชี/เซสชันเดียวใต้ `_require_selected_session` guard

## 7. เกรด & สถานะ matrix

- **A (byte-exact static):** op6 4-callsite enumeration · arg contract `(qty_low,qty_high,handle)` + `ret 0xC` + no-destination · dispatcher membership (verb 0x16 เดียวใน `[0x5A2A70,0x5A40B0)`) · verb-0x16 dialog/guard/op6 path · server op6/op3 gap
- **ยังไม่ claim:** verb 0x16 ≡ split เฉพาะ (op6-ไม่มี-destination ครอบ split/drop-N/destroy-N — ต้อง caption res 0x12 หรือ live capture)
- `inventory/split_stack`: คง **`in_progress`** — เพิ่ม evidence_ref = report นี้, test_ref = `tests/test_split_operate_family_static.py`. **ไม่ flip runtime_pass** (ไม่มี server handler + ไม่มี runtime capture)
- ledger คง **24** (characterization ของ client binary, ไม่ใช่ server hypothesis ใหม่ — ไม่มี src/scenario/entry ใหม่)

## 8. Reproduce

```
py -3 tools/pf_split_operate_family_static.py            # 31 guards, exit 0
py -3 -m pytest tests/test_split_operate_family_static.py  # 9 tests
```
Evidence ทั้งหมด read-only (client binary + server source). ไม่แตะ GameClient runtime, ไม่แตะ canonical DB, ไม่มี network I/O.
