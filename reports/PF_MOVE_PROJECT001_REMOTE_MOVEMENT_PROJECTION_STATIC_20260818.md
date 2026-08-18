# PF_MOVE_PROJECT001 — client `MovementAttr 0x2067` remote-actor movement-projection producer/consumer + wire schema: byte-exact static characterization of the transport a remote player's movement projection rides (static disasm + server cross-check)

รอบ 73→74 (2026-08-18 scheduled; รอบ 73 ทำ tool/test/matrix แล้วตายกลางคัน — รอบ 74 ตรวจซ้ำ+ปิดงาน) · chief · report-only additive · milestone สำรอง pre-approved (movement — LOCK รอบ 72 next② "remote_player_movement_projection (ขา static)") · binary `GameClient/GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` · capstone (CS_MODE_32, ImageBase 0x400000, PE section table parsed) · reproduce: `py -3 tools/pf_remote_movement_projection_static.py`

เป้า: ปลดบล็อก `movement/remote_player_movement_projection` (`not_started`, coverage note = **"No second player has ever been projected, so interest management, update cadence, and interpolation are entirely unknown."**) ให้ถึงชั้น projection-transport + wire-schema + consumer-mechanism + server-coverage-gap แบบ byte-exact static — โดย **ไม่แตะ v141 (immutable), ไม่แตะ persistence characters/accounts** (ไม่ชนคำถามค้างทั้งสอง) และเคารพ "checkpoint แคบ ≠ เสร็จ" (ไม่ flip เป็น runtime_pass)

> **ผลสรุปล่วงหน้า:** position/heading/control-state ของ remote actor ถูก project บน client ผ่าน **`MovementAttr` (MOVEMENT_ATTR = `0x2067`)** — attribute ที่นั่งอยู่ในทุก remote-actor entry ของ RuntimeRes actor stream — decode ครบ identity / vtable / wire-schema / projection-apply / delta-mask / server cross-check แบบ byte-exact:
> - **Identity (id runtime-assigned wall — กำแพงเดียวกับ TargetPosVital/ItemOperate cohort):** name string `"MovementAttr\0"` @ `0xF0E840` · registration จุดเดียว `0xBD9410` เขียน id → id-slot `0x10334A8` (write จุดเดียว `0xBD9421`, read จุดเดียว = get-id stub `0x43BBB0`) · id `0x2067` **ไม่ปรากฏเป็น code immediate ใน .text** (dword scan ตัด rel32 → 0 hit) · class token `0x103346C` = is-a reference ของ type-check `0x88F2B0` ที่ downcast consumer ทั้งสาม (`0x465466`, delta `0x46705A`, apply `0x467145`)
> - **vtable `0xF0D0F8`:** +0x08 = `0x401B20` (shared framework const, cohort เดิม) · +0x10 = get-id `0x43BBB0` · +0x28 = reset `0x467030` (prime submask@+0x20 + field mask@+0x4C = 0xFF) · +0x2C = delta `0x467040` · +0x30 = apply/merge `0x467130` · +0x34 = Serial `0x4671C0`
> - **Wire schema (byte-exact, mask-gated sparse):** header `0x467790` = u8(tag `0x0B`) submask@+0x20 → qword(tag `0x32`) identity@+0x18 · แล้ว field mask u8(tag `0x0B`)@+0x4C · per set bit: pos vec3 (helper `0x5F3490`, f32×3 tag `0x2A`)@+0x28 · heading f32(`0x2A`)@+0x34 · mode u8(`0x0B`)@+0x38 · flags u32(tag `0x26`)@+0x3C · f32(`0x2A`)×3 @+0x40/+0x44/+0x48 — **ตรง server `make_remote_movement_attr` เป๊ะ** · codec `0x89A600` stdcall `(tag,ptr,width)` ret 0xC **direction-agnostic** (routine เดียว decode ขาเข้าได้)
> - **Projection consumer (แก่นของ milestone):** apply/merge `0x467130` — หลังผ่าน is-a guard อ่าน field mask ของ target @+0x4C แล้ว **copy เฉพาะ field ที่ bit ไม่ถูก set** จาก source เข้า offset เดียวกัน → sparse movement delta ถูก complete ทับ projected state เดิมโดยไม่ทับ field ที่ target ถืออยู่ · ฝั่ง outbound: delta `0x467040` clear mask แล้ว set bit ต่อ field ที่ต่างจาก reference (pos ผ่าน `0x4A1720`, heading/f32×3 ผ่าน cvtps2pd+ucomisd, mode u8 cmp, flags u32 cmp)
> - **Server cross-check:** `MOVEMENT_ATTR = 0x2067` · `make_remote_movement_attr` emit schema byte-exact เดียวกัน · `make_remote_actor_entry` (client serializer `0x5E21D0`) แบก attr เป็น u16tag(`0x12`, 0x2067) + Serial
> - **ช่องว่าง (สิ่งที่ยัง uncaptured):** server **emit เฉพาะ remote actor ประเภท actor_type 4 (CNetNPC)** — ไม่เคยมี authentic capture ของ remote human-PLAYER actor_type และ composition ของ projected attrs ของมัน → characterization นี้ = กลไก projection byte-exact แต่**ไม่ claim** พฤติกรรม remote human-player projection ของ original server
>
> **เกรด:** identity + vtable + wire-schema + apply/merge mask semantics + delta semantics + server cross-check = **A** (byte-exact static, reproduced by verifier, span-hash pinned) · **"remote human-player projection ของ original server"** = **ไม่ claim** (uncaptured — interest management / cadence / interpolation ยังไม่มีหลักฐาน) · net: **remote_player_movement_projection `not_started` → `in_progress`** (ไม่ runtime-proven — ยังไม่เคยมี second client)

---

## 1. Identity — vtable `0xF0D0F8`, id runtime-assigned (กำแพง cohort เดิม)

Name string `"MovementAttr"` @ `0xF0E840`. registration site เดียว `0xBD9410` push ชื่อ → call registry → เก็บ id ลง id-slot `0x10334A8` (สโตร์จุดเดียว `0xBD9421`; span `0xBD9410..0xBD9428` byte-identical, sha `C69B3040..5A47`). get-id stub `0x43BBB0` = `mov ax,[0x10334A8]; ret` (`66 A1 A8 34 03 01 C3`) — จุดอ่านเดียว

**กำแพงยืนยัน:** `0x2067` ไม่เป็น code immediate ที่ไหนใน .text (0 hit, ตัด rel32) → id runtime-assigned ล้วน — กำแพงเดียวกับ TargetPosVital `0x2A90`/ItemOperateVitalReq/ECHO/TELEPORT cohort

**Class token `0x103346C`** = is-a reference ที่ type-check `0x88F2B0` ใช้ ณ downcast consumer ทั้งสาม: `0x465466` (รับ attr ขาเข้า), `0x46705A` (delta), `0x467145` (apply/merge)

| vtable `0xF0D0F8` slot | ค่า | บทบาท |
|---|---|---|
| +0x08 | `0x401B20` | **shared framework const — cohort เดียวกับ TargetPosVital/ECHO/TELEPORT/ItemOperate** |
| +0x10 | `0x43BBB0` | **get-id** (`mov ax,[0x10334A8]`) |
| +0x28 | `0x467030` | **reset** — set submask@+0x20 + field mask@+0x4C = `0xFF` |
| +0x2C | `0x467040` | **delta** (outbound mask builder) |
| +0x30 | `0x467130` | **apply/merge** (projection consumer) |
| +0x34 | `0x4671C0` | **Serial** (wire schema) |

vtable span `0xF0D0F8..0xF0D124` byte-identical (sha `BE087352..1294`)

## 2. Object layout

identity qword @+0x18 · submask u8 @+0x20 · position vec3 @+0x28..+0x30 · heading f32 @+0x34 · mode u8 @+0x38 · flags u32 @+0x3C · f32×3 @+0x40/+0x44/+0x48 · field mask u8 @+0x4C

## 3. Wire schema — Serial `0x4671C0` (mask-gated sparse), byte-exact ตรง server

```
header 0x467790:  u8(tag 0x0B, submask@+0x20) → [submask bit1] qword(tag 0x32, identity@+0x18)
Serial 0x4671C0:  call header → u8(tag 0x0B, field mask@+0x4C) → per set bit:
  bit0x01  pos vec3      helper 0x5F3490 @+0x28   (f32×3 tag 0x2A)
  bit0x02  heading f32   tag 0x2A @+0x34
  bit0x04  mode u8       tag 0x0B @+0x38
  bit0x08  flags u32     tag 0x26 @+0x3C
  bit0x10/0x20/0x40  f32 tag 0x2A @+0x40/+0x44/+0x48
```

Serial = stdcall ret 8 (stream @[esp+8]) · span `0x4671C0..0x467288` byte-identical (sha `6A6571BB..180A`) · header span byte-identical (sha `D0BC5201..742E`) · vec3 helper `0x5F3490` span byte-identical (sha `B5F5A206..7454`) · codec `0x89A600` stdcall `(tag,ptr,width)` ret 0xC **direction-agnostic** → routine เดียวกัน decode inbound attr ได้

**ตรง server เป๊ะ:** `make_remote_movement_attr` emit `u8tag(0x0B,1) + qwordtag(0x32,id) + u8tag(0x0B,mask)` แล้ว per-field ตาม mask — f32 ใช้ tag `0x2A`, flags ใช้ u32tag `0x26` — byte-exact กับ Serial `0x4671C0`

## 4. Projection apply/merge `0x467130` — consumer (แก่นของ projection)

หลัง is-a guard (`0x88F2B0` vs token `0x103346C`): อ่าน field mask ของ **target** @+0x4C แล้วสำหรับทุก field ที่ **bit ไม่ถูก set** copy field นั้นจาก incoming source → offset เดียวกันบน target (pos +0x28/+0x30 · heading +0x34 · mode +0x38 · flags +0x3C · f32 +0x40/+0x44/+0x48) — **sparse movement delta ถูก complete ทับ projected state เดิม โดยไม่ทับ field ที่ target ถืออยู่แล้ว** · stdcall ret 4 · span `0x467130..0x4671B7` byte-identical (sha `948B6651..A291`)

ขา outbound: delta `0x467040` clear mask@+0x4C แล้ว or-bit ต่อ field ที่ต่างจาก reference — pos ผ่าน compare `0x4A1720` (bit0x01) · heading ผ่าน cvtps2pd+ucomisd (bit0x02) · mode u8 cmp (bit0x04) · flags u32 cmp (bit0x08) · f32×3 ucomisd (bit0x10/0x20/0x40) · span `0x467040..0x467130` byte-identical (sha `72D39357..72A7`)

## 5. Server cross-check + coverage gap

- `MOVEMENT_ATTR = 0x2067` ประกาศฝั่ง server · `make_remote_movement_attr` = schema byte-exact เดียวกับ Serial `0x4671C0` (per-field mask static)
- `make_remote_actor_entry` แบก MovementAttr ใน actor entry เป็น **u16tag(`0x12`, 0x2067) + Serial payload** — client actor-entry serializer = `0x5E21D0` (RuntimeRes actor stream)
- **gap:** server **emit เฉพาะ actor_type 4 (CNetNPC)** — ไม่เคยมี authentic capture ของ remote human-PLAYER actor_type + full projected-attr composition → **ไม่ claim** พฤติกรรม remote human-player projection ของ original server

→ ช่องว่าง = interest management / update cadence / interpolation ของ second player จริง — next hop = **live two-client capture** (คิวไว้ข้าง GT-011..GT-015 ในรอบใหญ่)

## 6. เกรด & สถานะ matrix

- **A (byte-exact static):** identity wall · vtable slots · wire schema mask-gated sparse · projection apply/merge semantics · delta mask semantics · server cross-check — ทุก span มี sha-256 pin ใน verifier
- **ไม่ claim:** remote human-player projection behavior ของ original server (uncaptured)
- `movement/remote_player_movement_projection`: `not_started` → **`in_progress`** — evidence_ref = report นี้, test_ref = `tests/test_remote_movement_projection_static.py`. **ไม่ flip runtime_pass** (ต้องมี second-client capture ก่อน)
- ledger คง **25** (characterization ของ client binary + cross-check server ที่มีอยู่ — ไม่มี src/scenario/entry ใหม่)
- movement domain: ไม่มีแถว `not_started` เหลือ → `next_missing_behavior` คงที่ `remote_player_movement_projection` (แถวแรกที่ยังไม่ runtime_pass ตามลำดับ missing จริง)

## 7. Reproduce

```
py -3 tools/pf_remote_movement_projection_static.py                  # 55 guards, exit 0
py -3 -m pytest tests/test_remote_movement_projection_static.py -q   # 12 passed
```
Evidence read-only ล้วน (client binary disassembled + read-only server source); ไม่มี network/GameClient runtime/canonical
