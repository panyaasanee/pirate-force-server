# PF_SPLIT_OPERATE001 — `ItemOperateVitalReq 0x4BED` operation space: byte-exact enumeration of the transport a stack-split must ride (static disasm + server cross-check)

รอบ 68 (2026-08-18 scheduled) · chief · report-only additive · milestone สำรอง pre-approved (split_stack — LOCK รอบ 67 next②) · binary `GameClient/GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` · capstone 5.0.7 (CS_MODE_32, ImageBase 0x400000, PE section table parsed) · reproduce: `py -3 tools/pf_split_operate_static.py`

เป้า: ปลดบล็อก `inventory/split_stack` (`not_started`, coverage note = **"No request producer, response shape, or persistence policy captured"**) ให้ถึงชั้น request-producer + wire-schema + server-coverage-gap แบบ byte-exact static — โดย **ไม่แตะ v141 (immutable), ไม่แตะ persistence characters/accounts** (ไม่ชนคำถามค้างทั้งสอง) และเคารพ "checkpoint แคบ ≠ เสร็จ" (ไม่ flip เป็น runtime_pass)

> **ผลสรุปล่วงหน้า:** stack-split **ไม่มี opcode เดี่ยวของตัวเอง** — ทุก item action วิ่งบน `ItemOperateVitalReq 0x4BED` โดยแยกด้วย **operation byte** ตัวเดียว (obj+0x14, wire tag `0x0B`). decode ครบทั้ง identity / serializer / operation space / field-mapping:
> - **Operation space (byte-exact) = {1, 3, 4, 5, 6}** — `1` = ctor default; producers ที่เขียน immediate จริงในอิมเมจ = `3,4,5,6` (6 factory callsites, op5 มีสองที่)
> - **op4 = MOVE** (identity qword + value32 = destination slot) — ตรงกับ server `operation==4`
> - **op5 = EQUIP-from-bag** (identity qword + value32 = slot bitfield) — ตรงกับ server `V123_EQUIP_FROM_BAG_OPERATION=5`
> - **op3 = identity-only** (ไม่เขียน value32 เลย) — single-target operate family
> - **op6 = quantity-parameterized** — producer ดึง **จำนวนเต็มบวกจาก numeric input dialog** (`0x5A1630`, guard `> 0`) แล้วเข้ารหัส **quantity ลง qword field (tag 0x32)** ส่วน value32 = item handle → **นี่คือ field-encoding ที่ split ต้องใช้** (นับจำนวนใน qword ไม่ใช่ item id)
> - **ช่องว่างฝั่ง server (สิ่งที่ split ยังขาด):** server ปัจจุบันรู้จักเฉพาะ `operation==4` และ `==5` — **ไม่มี handler ของ op3/op6 เลย** → split_stack = characterized ยังไม่ implemented
>
> **เกรด:** identity + serializer field-map + operation enumeration + producer field-usage + server-coverage gap = **A** (byte-exact static, reproduced by verifier, cross-checked กับ server source) · **"op6 == split โดยเฉพาะ"** = **ไม่ claim** (bounded — op6 = quantity-op family ซึ่งครอบ split/drop-N/sell-N; แยก verb ที่แท้จริงต้อง resolve verb-code→UI action `eax==0x16` หรือ live capture ของ interaction จริง = next hop) · net: **split_stack `not_started` → `in_progress`** (request producer family + wire shape + response/persistence lanes ระบุแล้ว, ไม่ runtime-proven)

---

## 1. Identity — vtable `0xf30374`, id runtime-assigned (กำแพง ECHO/TELEPORT เดิม)

RTTI/registration name string `"ItemOperateVitalReq"` @ `0xf30904`. สายเดียวในอิมเมจที่ push ชื่อคลาส:

```
0x00bee520: 68 0409f300      push 0xf30904              ; "ItemOperateVitalReq"
0x00bee525: e8 56db2a00      call 0x89c080              ; once-init singleton registry (MSVC guard)
0x00bee52a: 8bc8             mov ecx, eax
0x00bee52c: e8 cfd72a00      call 0x89bd00              ; thiscall id-assign(name) -> ax
0x00bee531: 66a3 14200801    mov word [0x1082014], ax   ; *** store runtime id -> id-slot ***
0x00bee537: c3               ret
```
get-id stub (vtable `+0x10`): `0x5e5ae0: 66 a1 14200801  mov ax,[0x1082014]; c3 ret`.

**กำแพงยืนยัน:** ค่า `0x4BED` **ไม่ปรากฏเป็น code immediate ที่ไหนในอิมเมจ** (สแกน dword `0x00004BED` ทั้งไฟล์ ตัด `e8/e9` rel32 displacement ออก → 0 hit) และ id-slot `0x1082014` เขียนจุดเดียว (registration) อ่านจุดเดียว (get-id) → id **runtime-assigned ล้วน** — กำแพงเดียวกับ TELEPORT_CHECK/NAMEID/ECHO cohort.

vtable `0xf30374` (8 slot แรก):

| slot | ค่า | บทบาท |
|---|---|---|
| +0x00 | `0x5e5ad0` | get-type |
| +0x04 | `0x5ea390` | dtor/reset |
| +0x08 | `0x401b20` | **shared framework const — VitalData cohort เดียวกับ ECHO/TELEPORT** |
| +0x0c | `0x51df20` | framework method |
| +0x10 | `0x5e5ae0` | **get-id** (`mov ax,[0x1082014]`) |
| +0x14 | `0x5eb050` | framework method |
| +0x18 | `0x5e5af0` | **serializer** (owner เดียวของ `0x5E5AF0`) |
| +0x1c | `0x710440` | framework method |

## 2. Schema — serializer `0x5e5af0` = สาม tagged field, byte-exact

```
0x005e5b03: lea eax,[esi+0x14]   push 0xb    ; field#1 operation  @+0x14  tag 0x0B  width 1
0x005e5b10: lea ecx,[esi+0x18]   push 0x14   ; field#2 value32    @+0x18  tag 0x14  width 4
0x005e5b1f: add esi,0x20         push 0x32   ; field#3 qword      @+0x20  tag 0x32  width 8
```
direction เลือกด้วย `cmp byte[esp+8],0` → out `0x89a600` / in `0x89a640`. **ตรงกับ server `parse_item_operate_req`** เป๊ะ: `operation=c.u8(0x0B); value32=c.u32(0x14); item_identity=<Q>(c.raw8(0x32)); remain()==0` (ไม่มี owner/character field บนสาย — สอดคล้อง MOVE-ISOLATION-001 รอบ 67).

Constructor `0x5e5b60` init `obj+0x14 = 1` (default operation), vtable ptr `0xf30398`.

## 3. Operation space — {1, 3, 4, 5, 6}, byte-exact producers

6 factory callsites (`call 0x59f0d0`, ctx `mov ecx,0x1030618; push 0xf0a90c`) เขียน operation immediate `C6 40 14 <op>`:

| op | producer VA | value32 (+0x18) | qword (+0x20) | semantics (จาก field-usage + server) |
|---|---|---|---|---|
| 1 | ctor `0x5e5b60` | — | — | default (ก่อน producer overwrite) |
| 3 | `0x59f780` | **ไม่เขียน** | item identity | single-target operate (use/consume/unequip family) — **server ไม่มี handler** |
| 4 | `0x59f7c0` | **destination slot** | item identity | **MOVE** — ตรง server `operation==4` |
| 5 | `0x59f800`, `0x5a25c3` | slot bitfield | item identity | **EQUIP-from-bag** — ตรง server `V123=5` |
| 6 | `0x59f870` | item handle | **quantity (64-bit, user-entered)** | **quantity-op family** (split / drop-N / sell-N) — **server ไม่มี handler** |

**op6 = จุดสำคัญของ split.** caller path (inventory handler `0x5a349b`, verb `eax==0x16`):
```
0x5a34d7: mov [esp+0x180],0x12      ; open numeric-input dialog resource
0x5a34e2: call 0x5a1630             ; quantity dialog
0x5a34ef: cmp [eax+0x2c],0 ; jg/jl  ; *** result must be > 0 (positive-only guard) ***
0x5a3521: mov ecx,[eax+0x28]        ; qty low
0x5a3524: mov eax,[eax+0x2c]        ; qty high
0x5a3517: mov esi,[esi+0x94]        ; item handle
0x5a3532: call 0x59f870             ; op6 -> value32=handle, qword=(qty)
```
→ **op6 เข้ารหัส "จำนวน" ลง qword field (tag 0x32)** ที่ move/equip ใช้เป็น item-identity — field semantics **ขึ้นกับ operation**. นี่คือกับดักที่จะทำ server implementation ของ split พังถ้าถือว่า qword = identity เสมอ.

> **ขอบเขตที่ไม่ claim:** op6 = quantity-op family (verb `eax==0x16`). corpus/binary ยังไม่ byte-prove ว่า op6 = "split เข้าช่องปลายทาง" โดยเฉพาะ (op6 ไม่มี destination-slot field — ต่างจาก MOVE) → อาจเป็น drop-N/destroy-N ได้ด้วย. การ pin split ให้ชัดต้อง (i) resolve verb-code→UI action map ของ `eax==0x16`, หรือ (ii) live capture ตอนทำ split จริง = **next hop**.

## 4. Response & persistence lanes (ระบุ, ยังไม่ implement)

- **Response:** `ItemOperateVitalRes 0x4C13` (server `make_runtime_vitals([(ITEM_OPERATE_RES_VITAL,2,payload)])` — สายเดียวกับ move-merge success ของ HYP-PF-011) — split จะใช้ res path นี้ + `u16tag(0x0F, quantity)` (server `inventory.py` ใส่ quantity ทุก item snapshot อยู่แล้ว).
- **Persistence:** สองตารางเดิม `character_backpack_items` (rows) + `character_backpacks.updated_at` (GT-002 runtime-proven, MOVE-ISOLATION-001 รอบ 67) — split = แตกหนึ่ง row (qty n) → สอง rows (n−k, k) ในบัญชี/เซสชันเดียวใต้ `_require_selected_session` guard ที่ pin แล้ว.

## 5. เกรด & สถานะ matrix

- **A (byte-exact static):** operation space {1,3,4,5,6} · serializer field-map · producer field-usage (move vs quantity) · id runtime-assigned · server รับเฉพาะ 4/5.
- **ไม่ claim:** op6 ≡ split (bounded — quantity-op family).
- `inventory/split_stack`: `not_started` → **`in_progress`** — evidence_ref = report นี้, test_ref = `tests/test_split_operate_static.py`. **ไม่ flip runtime_pass** (ต้องมี server handler + runtime capture ก่อน).
- ledger คง **24** (characterization ของ client binary, ไม่ใช่ server hypothesis ใหม่ — ไม่มี src/scenario/entry ใหม่).

## 6. Reproduce

```
py -3 tools/pf_split_operate_static.py            # 36 guards, exit 0
py -3 -m pytest tests/test_split_operate_static.py  # 9 tests
```
Evidence ทั้งหมด read-only (client binary + server source). ไม่แตะ GameClient runtime, ไม่แตะ canonical DB, ไม่มี network I/O.
