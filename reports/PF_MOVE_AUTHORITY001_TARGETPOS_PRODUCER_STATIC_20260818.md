# PF_MOVE_AUTHORITY001 — client `TargetPosVital 0x2A90` movement-report producer + wire schema: byte-exact static characterization of the transport a movement-authority model must ride (static disasm + server cross-check)

รอบ 72 (2026-08-18 scheduled) · chief · report-only additive · milestone สำรอง pre-approved (movement — LOCK รอบ 71 next② "ขา static/corpus") · binary `GameClient/GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` · capstone 5.0.7 (CS_MODE_32, ImageBase 0x400000, PE section table parsed) · reproduce: `py -3 tools/pf_move_authority_targetpos_static.py`

เป้า: ปลดบล็อก `movement/local_player_movement_authority` (`not_started`, coverage note = **"Reported positions are accepted as given. No speed, distance, collision, terrain, or line-of-sight validation exists, and no corrective reposition is ever sent. The original server's movement authority model is uncaptured."**) ให้ถึงชั้น request-producer + wire-schema + server-coverage-gap แบบ byte-exact static — โดย **ไม่แตะ v141 (immutable), ไม่แตะ persistence characters/accounts** (ไม่ชนคำถามค้างทั้งสอง) และเคารพ "checkpoint แคบ ≠ เสร็จ" (ไม่ flip เป็น runtime_pass)

> **ผลสรุปล่วงหน้า:** movement report ของ local player (เฟรมที่ client ส่งตอนเดิน/คลิกปลายทาง) วิ่งบน **`TargetPosVital 0x2A90`** — decode ครบทั้ง identity / vtable / constructor field-layout / serializer wire-schema / producer callsite / server-coverage-gap แบบ byte-exact:
> - **Identity (id runtime-assigned wall):** name string `"TargetPosVital\0"` @ `0xF30818`, registration จุดเดียว `0xBEE380` เขียน id → id-slot `0x1081FE0` · id `0x2A90` **ไม่ปรากฏเป็น code immediate ที่ไหนในอิมเมจ** (0 hit, ตัด rel32) · get-id stub อ่าน id-slot จุดเดียว `0x5E50A0` — กำแพงเดียวกับ ItemOperateVitalReq/ECHO/TELEPORT cohort
> - **vtable `0xF30230`:** +0x08 = `0x401B20` (shared VitalData const ของ cohort เดิม), +0x10 = get-id, +0x18 = serializer `0x5E50E0` · ctor `0x5E5050` zero-init สี่ f32 (x/y/z/heading @ +0x14/+0x18/+0x1C/+0x20) + สอง u8 (moving/mask @ +0x24/+0x25)
> - **Wire schema (byte-exact) = f32×4 (tag `0x2A`) + u8×2 (tag `0x0B`):** serializer `0x5E50E0` เรียก vec3 helper `0x5F3490` (x,y,z tag `0x2A` width 4) + heading (tag `0x2A` width 4) + moving/mask (tag `0x0B` width 1) ผ่าน field serializer `0x89A600` (stdcall `(tag,ptr,width)` ret 0xC) · **ตรง server `parse_target_pos_vital` เป๊ะ**
> - **Anchor จริง:** captured `V139_MARKER1_TARGETPOS_PC` ในซอร์ส server decode ใต้ schema นี้ได้ byte-exact = MARKER1 `(x,y,z)=(-10322,-755,671)`, heading 0, moving 1, mask 0, remain 0
> - **ช่องว่างฝั่ง server (สิ่งที่ authority ยังขาด):** server decode schema เดียวกันและ**รับตามที่แจ้ง** (`self.last_target_pos = (x,y,z,heading)`) → **ไม่มี** speed/distance/collision/LoS validation ของ local player และ**ไม่เคยส่ง corrective reposition** — `movement_speed` ตัวเดียวในไฟล์ = NPC walk-speed const (`V73_WALK_SPEED`) ไม่ใช่ authority check
>
> **เกรด:** identity + vtable + ctor field-map + serializer wire-schema (byte-exact) + captured-payload binding + server-coverage gap = **A** (byte-exact static, reproduced by verifier, cross-checked กับ server source + authentic capture) · **"authority model ของ original server"** = **ไม่ claim** (uncaptured — threshold/correction-packet/cadence ยังไม่มีหลักฐาน) · net: **local_player_movement_authority `not_started` → `in_progress`** (request producer + wire shape + server gap ระบุแล้ว, ไม่ runtime-proven)

---

## 1. Identity — vtable `0xF30230`, id runtime-assigned (กำแพง ItemOperate/ECHO/TELEPORT เดิม)

RTTI/registration name string `"TargetPosVital"` @ `0xF30818`. สายเดียวในอิมเมจที่ push ชื่อคลาส:

```
0x00bee380: 68 1808f300      push 0xf30818              ; "TargetPosVital"
0x00bee385: e8 f6dccaff      call 0x89c080              ; once-init singleton registry (MSVC guard)
0x00bee38a: 8bc8             mov ecx, eax
0x00bee38c: e8 6fd9caff      call 0x89bd00              ; thiscall id-assign(name) -> ax
0x00bee391: 66a3 e01f0801    mov word [0x1081fe0], ax   ; *** store runtime id -> id-slot ***
0x00bee397: c3               ret
```
get-id stub (vtable `+0x10`): `0x5e50a0: 66 a1 e0 1f 08 01  mov ax,[0x1081fe0]; c3 ret`.

**กำแพงยืนยัน:** ค่า `0x2A90` **ไม่ปรากฏเป็น code immediate ที่ไหนในอิมเมจ** (สแกน dword `0x00002A90` ทั้ง .text ตัด `e8/e9` rel32 displacement → 0 hit) และ id-slot `0x1081FE0` เขียนจุดเดียว (registration) อ่านจุดเดียว (get-id) → id **runtime-assigned ล้วน** — กำแพงเดียวกับ ItemOperateVitalReq (`0x4BED`)/TELEPORT_CHECK/NAMEID/ECHO cohort.

vtable `0xF30230` (8 slot แรก):

| slot | ค่า | บทบาท |
|---|---|---|
| +0x00 | `0x5e5090` | get-type |
| +0x04 | `0x5e79c0` | dtor/reset |
| +0x08 | `0x401b20` | **shared framework const — VitalData cohort เดียวกับ ECHO/TELEPORT/ItemOperate** |
| +0x0c | `0x51df20` | framework method |
| +0x10 | `0x5e50a0` | **get-id** (`mov ax,[0x1081fe0]`) |
| +0x14 | `0x5eaf10` | framework method |
| +0x18 | `0x5e50e0` | **serializer** |
| +0x1c | `0x710440` | framework method |

## 2. Constructor `0x5E5050` — object field layout (x/y/z/heading + moving/mask)

```
0x5e506c: c7 00 3002f300   mov dword [eax], 0xf30230   ; *** vtable ptr ***
0x5e5072: f3 0f11 40 1c    movss [eax+0x1c], xmm0       ; z        = 0.0
0x5e5077: f3 0f11 40 18    movss [eax+0x18], xmm0       ; y        = 0.0
0x5e507c: f3 0f11 40 14    movss [eax+0x14], xmm0       ; x        = 0.0
0x5e5081: f3 0f11 40 20    movss [eax+0x20], xmm0       ; heading  = 0.0
0x5e5086: 88 48 24         mov  [eax+0x24], cl          ; moving   = 0
0x5e5089: 88 48 25         mov  [eax+0x25], cl          ; mask     = 0
0x5e508c: c3               ret
```
object = 0x28 bytes (factory allocates `push 0x28` before construct, §4). field map: x=+0x14, y=+0x18, z=+0x1C, heading=+0x20 (f32×4), moving=+0x24, mask=+0x25 (u8×2).

## 3. Serializer `0x5E50E0` — wire schema byte-exact, ตรง server parse

```
0x5e50ed: lea eax,[esi+0x14]  ...  call 0x5f3490   ; vec3 -> x,y,z each tag 0x2A width 4
0x5e50fc: push 4  lea ecx,[esi+0x20]  push 0x2a  call 0x89a600   ; heading  tag 0x2A width 4
0x5e510b: push 1  lea edx,[esi+0x24]  push 0x0b  call 0x89a600   ; moving   tag 0x0B width 1
0x5e511a: push 1  add esi,0x25        push 0x0b  call 0x89a600   ; mask     tag 0x0B width 1
0x5e512b: ret 8
```
vec3 helper `0x5F3490` = สาม field ต่อเนื่อง (`[esi+0]`, `[esi+4]`, `[esi+8]`) แต่ละตัว `push 4; push ptr; push 0x2A; call 0x89a600`. field serializer `0x89A600` = stdcall `(tag, ptr, width)` `ret 0xC` (direction เลือกด้วย `cmp byte[esp+8],0`).

**Net wire (นับจาก nested_version tag `0x0B` ที่ parse_outer กินไปแล้ว):**
`[0x2A f32 x][0x2A f32 y][0x2A f32 z][0x2A f32 heading][0x0B u8 moving][0x0B u8 mask]`

**ตรงกับ server `parse_target_pos_vital` เป๊ะ:**
```python
x=c.f32(0x2A); y=c.f32(0x2A); z=c.f32(0x2A); heading=c.f32(0x2A)
moving=c.u8(0x0B) ...            # parse_v141_refresh_target_pos: + derived_mask=c.u8(0x0B); remain()==0
```

**Anchor จริง (byte-exact binding):** captured `V139_MARKER1_TARGETPOS_PC` ในซอร์ส server —
nested payload `2A 00 48 21 C6 · 2A 00 C0 3C C4 · 2A 00 C0 27 44 · 2A 00 00 00 00 · 0B 01 · 0B 00`
→ decode = `x=-10322.0, y=-755.0, z=671.0` (MARKER1: scene 1 seq 0 XYZ) `heading=0`, `moving=1`, `mask=0`, `remain=0`. schema round-trip ตรงทุก byte.

## 4. Producer — object เป็น factory-constructed (alloc 0x28) แล้วเรียก ctor

ctor `0x5E5050` ถูกเรียกจากสอง factory site เดียวกัน `0x44B7C4` / `0x44B842` (branch จัดสรร/placement) ในฟังก์ชัน factory `0x44B700` ที่ `push 0x28; call 0x88D020` (allocate 40-byte object) ก่อน construct. serializer/get-id **ไม่มี direct E8 caller** (0/0) — ถูกเรียกผ่าน vtable `+0x18`/`+0x10` ตาม cohort VitalData (สอดคล้องกำแพง §1). การไล่ต่อจาก factory → mouse/destination handler = corpus/live-capture hop (ไม่อยู่ในขอบเขต static นี้ เช่นเดียวกับ SPLIT-OPERATE ที่หยุดที่ producer family).

## 5. Server coverage gap — decode แต่ accept-as-given, ไม่มี local authority

- **decode:** `TARGET_POS_VITAL = 0x2A90`; `parse_target_pos_vital` / `parse_v141_refresh_target_pos` อ่าน f32×4 + u8×2 schema เดียวกับ client serializer
- **accept-as-given:** runtime handler ของ inbound `TARGET_POS_VITAL` เก็บ `self.last_target_pos = (x, y, z, heading)` แล้วเดินต่อ (ใช้เพื่อขับ population refresh distance เท่านั้น) — **ไม่มี** speed/distance/collision/LoS validation ของ local player และ**ไม่เคยส่ง corrective reposition**
- `movement_speed` ตัวเดียวในไฟล์ = `V73_WALK_SPEED = 150.0` ป้อนให้ `make_npc_attr(...)` (NPC locomotion presentation) ไม่ใช่ authority check ของ player

→ ช่องว่าง = **authority model** (accept threshold + correction packet + cadence) ที่ original server ทำ ยัง uncaptured → milestone = characterization ของ transport ที่ authority ต้องวิ่งบน ไม่ใช่ implementation.

## 6. เกรด & สถานะ matrix

- **A (byte-exact static):** identity (registration + id-slot + runtime-assigned wall) · vtable slots · ctor field-map · serializer wire-schema (f32×4 tag 0x2A + u8×2 tag 0x0B) · captured-payload binding (MARKER1) · server decode-but-no-authority gap.
- **ไม่ claim:** authority model ของ original server (uncaptured).
- `movement/local_player_movement_authority`: `not_started` → **`in_progress`** — evidence_ref = report นี้, test_ref = `tests/test_move_authority_targetpos_static.py`. **ไม่ flip runtime_pass** (ต้องมี authority behavior + runtime validation capture ก่อน).
- ledger คง **25** (characterization ของ client binary + cross-check server ที่มีอยู่ ไม่ใช่ server hypothesis ใหม่ — ไม่มี src/scenario/entry ใหม่).

## 7. Reproduce

```
py -3 tools/pf_move_authority_targetpos_static.py            # 38 guards, exit 0
py -3 -m pytest tests/test_move_authority_targetpos_static.py -q   # 10 passed
```
Evidence read-only ล้วน (client binary disassembled + read-only server source + authentic captured PC ในซอร์ส); ไม่มี network/GameClient runtime/canonical.
