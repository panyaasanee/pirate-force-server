# DAMAGE-MODEL ทาง 1 — เอกสารออกแบบ (ร่าง)

Date: 2026-08-19 (รอบ 89)
Lane: `combat/damage_and_hit_result` · ทาง 1 = **ออกแบบสูตรความเสียหายของเราเอง**
Status: **ร่างออกแบบเท่านั้น** — ยังไม่มี `src/` เปลี่ยน, ไม่มี scenario, ไม่มี encoder,
ไม่มี ledger entry, ไม่มี matrix flip, ไม่มีการบูตเซิร์ฟเวอร์
อนุมัติโดย: Panya 2026-08-19 11:45 — ขอบเขตที่เคาะ = **i32 มีเครื่องหมาย 1 ตัว + flag word 1 ตัว ต่อเป้าหมาย**
ฐานหลักฐาน: `reports/PF_DAMAGE_MODEL001_CLIENT_HIT_RESULT_EXPECTATION_20260819.md`
(verifier `tools/pf_damage_hit_result_static.py`, 235/235 guards PASS · tests `tests/test_damage_hit_result_static.py` 56 passed)
ไบนารีอ้างอิงเดียว: `GameClient.local.bin` อ่านอย่างเดียว
SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`

> **ข้อแรกสุดของเลนนี้ และต้องติดไปกับทุกอย่างที่เลนนี้ผลิต:**
> **นี่คือสูตรของเรา ไม่ใช่สูตรของเซิร์ฟเวอร์ต้นฉบับ ซึ่งกู้ไม่ได้ตลอดกาล**
> เซิร์ฟเวอร์ต้นฉบับปิดไปแล้ว ไม่มี publish ไม่มี capture server->client ที่ใช้ได้ (SCENE-013 พิสูจน์ว่า corpus มีศูนย์เฟรม)
> และ DAMAGE-MODEL-001 พิสูจน์แล้วว่า **ไคลเอนต์ไม่มีสูตรอยู่ในตัวให้กู้** เพราะไคลเอนต์เป็นแค่ตัวแสดงผล
> ตัวเลขทุกตัวในเอกสารนี้เป็น **ตัวเลขที่เราตั้งขึ้นเอง** เว้นแต่จะระบุว่า `[PROVEN]`

---

## 0. สรุปหนึ่งย่อหน้า

ไคลเอนต์รับ `CHitResult` (wire id `0x16F7`) ที่มีหัว 5 ฟิลด์ + อาเรย์ hit-entry
โดยแต่ละ entry มี 5 ฟิลด์บนสาย (stride ในหน่วยความจำ 32 ไบต์) และในนั้นมีเพียง **สองฟิลด์**
ที่เป็น "ความหมายของความเสียหาย": **i32 มีเครื่องหมายที่ `+0x08`** (ตัวเลขที่ผู้เล่นเห็น, แสดงผ่าน `abs()` ล้วน ๆ)
และ **u16 flag word ที่ `+0x1C`**  อีกสามฟิลด์ (identity เป้าหมาย, ตำแหน่ง Vector3, มุม yaw)
เป็นโครงสร้างที่ **ต้องส่งอยู่ดี** เพราะสายเป็น tagged stream — เราไม่ได้ "ออกแบบ" มัน แต่ต้อง **ปักหมุดค่าที่รู้ว่าปลอดภัย**
เอกสารนี้เสนอสูตร integer ล้วน deterministic, ช่วงค่าปลอดภัยของ i32, allowlist ของ flag bits,
และแผน implement/พิสูจน์/เทสตาม pattern เดียวกับ HYP-PF-022 / HYP-PF-023

---

## 1. contract ระดับไบต์ที่ยืนยันได้แล้ว

### 1.1 codec และ tag map — `[PROVEN]`

สายเป็น **tagged stream**: ทุกฟิลด์ = 1 ไบต์ tag + payload ความกว้างคงที่
ตอนอ่าน ไคลเอนต์ **เทียบไบต์ tag** และ **ตั้ง error flag เมื่อไม่ตรง** — ส่งความกว้างถูกแต่ tag ผิด = สายพัง

| รายการ | VA | หมายเหตุ |
|---|---|---|
| `CStream::WriteField(tag, ptr, size)` | `0x89A600` | `__thiscall`, `ecx` = stream |
| READ twin | `0x89A640` | |
| tag store | `0x89A53B` | `mov [eax+edx], cl` |
| tag check | `0x89A5BF` | `cmp bl, [eax+edx]` |
| decode-error flag | `stream+0x20` ตั้งที่ `0x89A5C9` | |
| buffer-overflow flag | `stream+0x21` ตั้งที่ `0x89A590` | คนละตัวกับข้างบน |
| Vector3 write / read | `0x5F3490` / `0x5F34D0` | ไม่ใช่ tag — เป็น helper ที่ปล่อย f32 tag `0x2A` สามตัว = 12 ไบต์ |

| tag | ชนิด | ความกว้าง payload |
|---|---|---|
| `0x0B` | u8 | 1 |
| `0x12` | u16 | 2 |
| `0x14` | u32 | 4 |
| `0x2A` | f32 | 4 |
| `0x32` | qword | 8 |
| `0x0F` | i16 (sign-extend ตอนอ่าน) | 2 |

### 1.2 ตัวคลาส `CHitResult` — `[PROVEN]`

| รายการ | ค่า |
|---|---|
| name literal | `0xF0B5F8` = `"CHitResult"` |
| wire id | `0x16F7` (PF-NAMEID hash ของ literal, reproduce ได้ใน Python) |
| registration thunk | `0xC0C180` -> id global `0x108A2E4` |
| get-id stub | `0x74F9C0` |
| vtable | `0xF48AA0` |
| ctor | `0x74F940` |
| sizeof | `0x48` |
| serializer (vtable +0x18) | `0x750040` |
| inbound handler (vtable +0x1C) | `0x750770` |

ฝาแฝด `CMissileHitResult`: id `0x3EE5`, vtable `0xF48AC4`, serializer `0x750110`, handler `0x750EC0`
— ใช้ **อาเรย์ hit-entry ตัวเดียวกัน** แต่เก็บไว้ที่ `+0x40` ของตัวเอง

### 1.3 หัวเฟรม (emission order จาก `0x750040`) — `[PROVEN]`

serializer ทั้งก้อนถูก pin เป็นไบต์ (`gbytes(0x750040, ...)`) และมี guard ว่า
**หัวปล่อยพอดี 5 ฟิลด์ก่อนอาเรย์** (`calls_to_in(STREAM_WRITE, 0x750040, 0x7500AC) == 5`)

| # | object offset | tag | ชนิด | ความกว้าง wire | emit VA | ความหมาย |
|---|---|---|---|---|---|---|
| 1 | `+0x18` | `0x32` | qword | 9 | `0x750059` | identity ผู้กระทำ (performer / attacker) `[PROVEN ว่าเป็น qword identity]` |
| 2 | `+0x20` | `0x12` | u16 | 3 | `0x750068` | **ยังไม่รู้** |
| 3 | `+0x22` | `0x12` | u16 | 3 | `0x750077` | **ยังไม่รู้** |
| 4 | `+0x24` | `0x14` | u32 | 5 | `0x750086` | รายงานเรียกว่า "resource delta ของผู้เล่นเอง แสดงตรง ๆ" — **ความหมายแม่นยำยังไม่รู้ / ยังไม่รู้ว่าถูกอ่านเป็น signed หรือไม่** |
| 5 | `+0x28` | `0x0B` | u8 | 2 | `0x750095` | **ยังไม่รู้** |
| 6 | `+0x2C` | — | array | — | `0x75009F` | เรียก array serializer `0x74F5A0` |

รวมความกว้างหัวบนสาย = **22 ไบต์** `[DERIVED — เลขคณิตจาก tag map ยังไม่ได้ยืนยันกับ encoder จริง ต้อง assert ในเทส]`

### 1.4 อาเรย์ hit-entry — `[PROVEN]`

| รายการ | ค่า |
|---|---|
| array WRITE | `0x74F5A0` (call site พอดี 2 จุด: `0x75009F` CHitResult+0x2C, `0x75019E` CMissileHitResult+0x40) |
| array READ | `0x74FF60` (call site สะท้อนพอดี 2 จุด: `0x7500F8`, `0x750222`) |
| count | u16 tag `0x12` emit ที่ `0x74F5C8` (read twin `0x74FF6A`) |
| element stride | **32 ไบต์** พิสูจน์สองทางอิสระ: `sar eax,5` @ `0x74F5B3` และ `add ebx,0x20` @ `0x74F686` |
| จำนวนฟิลด์ต่อ element | **5 พอดี** (guard นับ call ของ STREAM_WRITE+VEC3_WRITE ในช่วง `0x74F625..0x74F670` ได้ 5) |
| ทั้งโซ่ emission ของ element | pin เป็นไบต์ยาว 0x50 ที่ `0x74F625` |

| offset | tag | ชนิด | ความกว้าง wire | write VA | read VA | ความหมาย |
|---|---|---|---|---|---|---|
| `+0x00` | `0x32` | qword | 9 | `0x74F62C` | `0x74FFCF` | identity เป้าหมาย `[PROVEN]` |
| `+0x08` | `0x14` | **i32 อ่านแบบ SIGNED** | 5 | `0x74F63E` | `0x74FFDF` | **ตัวเลขความเสียหายที่ผู้เล่นเห็น** `[PROVEN]` |
| `+0x0C` | `0x2A` x3 | Vector3 f32 | 15 | `0x74F645` -> `0x5F3490` | `0x74FFEA` | ตำแหน่งจุดโดน `[PROVEN]` |
| `+0x18` | `0x2A` | f32 | 5 | `0x74F657` | `0x74FFFD` | **มุม yaw ไม่ใช่ค่าความเสียหาย** `[PROVEN]` |
| `+0x1C` | `0x12` | u16 | 3 | `0x74F666` | `0x75000D` | **result-flag bitfield** `[PROVEN ว่าเป็น bitfield]` |
| `+0x1E..+0x1F` | — | — | — | — | — | padding ให้ครบ stride 32 (ไม่ขึ้นสาย) `[PROVEN]` |

รวมความกว้าง 1 element บนสาย = 9+5+15+5+3 = **37 ไบต์**
`[DERIVED — เลขคณิตจาก tag map ยังไม่ได้ยืนยันกับ encoder จริง ต้อง assert ในเทส]`

### 1.5 ความหมายของเครื่องหมาย — `[PROVEN]`

`+0x08` ถูกเทียบแบบ **มีเครื่องหมาย** สี่จุด และทั้งสี่จุดคือ `cmp dword ptr [ebx+8], 0` ตามด้วย `jge`:

| ตัวจัดการ | VA | ไบต์ที่ปัก |
|---|---|---|
| CHitResult | `0x750919` | `83 7b 08 00 0f 8d b3 00 00 00` (`jge` near = `0F 8D` ไม่ใช่ `jae` `0F 83`) |
| CHitResult | `0x7509E0` | `83 7b 08 00 7d 32` (`jge` short = `7D` ไม่ใช่ `jae` `73`) |
| CMissileHitResult | `0x751219` | `83 7b 08 00 0f 8d b3 00 00 00` |
| CMissileHitResult | `0x7512E0` | `83 7b 08 00 7d 32` |

**ค่าติดลบ = เส้นทาง "โดนความเสียหาย"** · ค่าไม่ติดลบ = ข้ามปฏิกิริยาการโดนตี
**ยังไม่รู้:** ค่าไม่ติดลบหมายถึงอะไร (heal / absorb / no-op) — รายงานปฏิเสธที่จะอ้าง เพราะไม่มี constant ในอิมเมจผูกไว้

### 1.6 เส้นทางตัวเลขขึ้นจอ — `[PROVEN]`

```
element +0x08  (0x750D90: mov ecx,[esi+8]  = arg5 ; 0fb7561c = movzx edx,word[esi+0x1C] = arg4 flags)
  -> 0x43FDE0   FX dispatcher (call site พอดี 4 จุดทั้งอิมเมจ อยู่ในตัวจัดการ hit-result ทั้งสองตัวทั้งหมด:
                 0x750DAA, 0x750E43, 0x751105, 0x75161F) ; ค่าลงที่ esi ที่ 0x43FF11 แล้วถูก push อย่างเดียว
  -> 0x43FBB0   FxNumber spawn (10 call site ทั้งอิมเมจ, 9 อยู่ใน 0x43FDE0 เอง)
  -> 0xA7C010   FxNumber ctor -> เก็บค่า verbatim ที่ 0xA7C046 (mov [esi+0xF8], eax)
  -> 0xA7EBA0   glyph builder: 0xA7EBFB mov eax,[esp+0x68] ; 0xA7EBFF cdq ; 0xA7EC00 xor eax,edx ;
                 0xA7EC02 sub eax,edx   <-- abs()  เลขคณิตเดียวทั้งเส้นทาง
  -> 0x896100   sprintf(buf, "%d", ...)  format literal ที่ 0xF14A94
```

* ค่าโหลด + abs() เป็น **9 ไบต์ต่อเนื่อง** ไม่มีอะไรแทรก (`span(0xA7EBFB, 0xA7EC04)` pin แล้ว)
* ไม่มี scale ไม่มี round ไม่มี clamp ไม่มี table lookup — `damage_field_scale_factor = 1`
* encoding ของ `imul` / `mulss` / `divss` / `mulsd` / `divsd` / `mulpd` / `divpd`
  ถูก assert ว่า **ไม่มี** ในสามช่วง `0x43FDE0..0x440164`, `0x43FBB0..0x43FDD0`, `0xA7E940..0xA7EBA0`
* ตัวจัดการ `CHitResult` (`0x750770..0x750EC0`) **ไม่มี memory operand ที่ BasicAttr +0x44/+0x48/+0x4C/+0x50/+0x58/+0x1A8/+0x1AC เลย**
  — ไม่อ่านและไม่เขียน HP · HP ขยับเพราะเซิร์ฟเวอร์บอกเท่านั้น
* stat ที่คำนวณเอง 19 ตัว (`0x467E90..0x468E30`, `base*const + equipBonus + tableCol` จากตาราง `STANDARD_STATUS` @ `0xF152AC`)
  เป็น **UI เท่านั้น** — caller ทั้งหมดอยู่ในบล็อก tooltip/panel ไม่มี caller ตัวไหนอยู่ใน combat handler

### 1.7 flag word `+0x1C` — bit test ที่ปักไบต์แล้ว vs ที่เป็นการอนุมาน

**`[PROVEN]` — bit test ที่ verifier ปักไบต์จริง** (`RESULT["hit_element"]["flags"]["bit_tests"]`):

| bit | mask | VA ที่เทส | ไบต์ |
|---|---|---|---|
| 0 | `0x0001` | `0x7509D6`, `0x7512D6` | `f6 43 1c 01` — คุมทั้งบล็อก apply |
| 1 | `0x0002` | `0x75137D` | `f6 43 1c 02` (พบใน missile handler) |
| 3 | `0x0008` | `0x750A1C`, `0x75131C` | `a8 08` หลัง `0fb7431c` — คุมบล็อกปฏิกิริยา |
| 4 | `0x0010` | `0x750A24`, `0x751324` | `a8 10` — ตั้งแล้ว push wide literal `0xF48B4C` = `L"_F_KNOCKED_002"` ที่ `0x750A33`/`0x751333` |
| 7 | `0x0080` | `0x750A84`, `0x75138F` | `f6 43 1c 80` — **ถูกเทสจริง แต่ไม่รู้ว่าทำอะไร** |

`bit_labels_claimed = False` ในผลลัพธ์ของ verifier — **verifier ไม่อ้างชื่อ bit ใด ๆ ทั้งสิ้น**

**`[INFERRED]` — bit ที่รายงาน DAMAGE-MODEL-001 §3 ระบุเพิ่ม โดยอ่านจาก texture/effect ที่ถูกเลือก ไม่ใช่จาก label:**

| bit | mask | ที่มา | ชื่อที่อนุมาน |
|---|---|---|---|
| 1 | `0x0002` | `0x7511EF`, `0x75137D` | block (`bm_block.tga`, `S_H_BLOCK.fxs`) |
| 5 / 6 | `0x0020`/`0x0040` | `test al,0x60` @ `0x751204` | สีของตัวเลข HP / MP |
| 9 | `0x0200` | ผ่าน flag->texture map ใน `0x43FDE0` | special / critical (เลขสีส้ม) |
| 10 | `0x0400` | ผ่าน flag->texture map ใน `0x43FDE0` | overkill |

**กติกาที่รายงานให้ และเราจะใช้:** `bit0 clear && damage == 0` = **miss**

**`[UNKNOWN]`** — bit 2, bit 8, bit 11..15 ไม่มีจุดเทสที่พบเลย · bit 7 มีจุดเทสแต่ไม่รู้ความหมาย

### 1.8 endianness

**ไม่ได้ระบุตรง ๆ ในรายงาน DAMAGE-MODEL-001** จัดเป็น `[DERIVED ความเชื่อมั่นสูง]`:
ไคลเอนต์เป็น x86 32-bit และ codec เขียนด้วย `memcpy` ตรง ๆ จาก object field
และเซิร์ฟเวอร์ของเราประกอบสายเป็น little-endian ทุกที่แล้ว
(`current/pf_login_game_server_v141.py` : `u32tag` = `struct.pack("<I", ...)`, `u16tag` `<H`, `f32tag` `<f`)
โดยไคลเอนต์รับมาแล้วในหลายเลน (NAME-002, GT-017, GT-018, GT-019)
=> **little-endian** และ f32 = IEEE-754 binary32
ถ้าจะอ้างเป็น `[PROVEN]` ต้องมี guard เพิ่มในเลนนี้ที่อ่านค่าที่เรารู้กลับออกมาจากสายจริง

### 1.9 สรุปว่าอะไร "พิสูจน์แล้ว" vs "ยังเดา"

**พิสูจน์แล้ว (grade A static, จากไคลเอนต์เท่านั้น):**
tag map · codec VA · CHitResult/CMissileHitResult identity+vtable+ctor+serializer+handler ·
หัว 5 ฟิลด์พร้อม emit VA · array count u16 tag `0x12` · element stride 32 · element 5 ฟิลด์พร้อม write/read VA ·
การอ่าน `+0x08` แบบ signed (4 จุด) · `+0x18` เป็นมุมไม่ใช่ damage · `+0x1C` เป็น u16 bitfield ·
เส้นทางแสดงผลที่มีเลขคณิตเดียวคือ `abs()` · ไคลเอนต์ไม่แตะ HP จาก hit · derived stats เป็น UI-only ·
bit test ที่ปักไบต์แล้ว 5 bit (0,1,3,4,7)

**ยังเดา / ยังไม่รู้ (ห้ามเขียนเหมือนพิสูจน์):**
1. ชื่อ/ความหมายของทุก bit ใน `+0x1C` (รวม bit 7 ที่ถูกเทสจริงแต่ไม่รู้ทำอะไร)
2. ความหมายของหัวฟิลด์ที่ 2 (`+0x20`), 3 (`+0x22`), 5 (`+0x28`) และรายละเอียดของ 4 (`+0x24`)
3. ค่าไม่ติดลบที่ `+0x08` แปลว่าอะไร (heal / absorb / no-op)
4. **หมายเลข version byte ของ vital `0x16F7`** — ไม่มีที่ไหนในรายงานหรือ verifier บอก
5. **ว่า factory ที่ประกอบ VitalData collection ของ `GSCN_RunTimeProtocolRes` สร้าง `0x16F7` ได้หรือไม่**
   — เรารู้ว่ามัน register ใน id registry เดียวกัน (`0xC0C180` -> `0x108A2E4`) แต่ยังไม่ได้พิสูจน์ว่าตัว dispatch ครอบคลุมมัน
6. ว่าตัวจัดการค้นหา performer identity แล้ว bail-out ถ้าไม่พบหรือไม่
7. เซิร์ฟเวอร์ต้นฉบับใส่ค่าอะไรลงฟิลด์ไหน — **กู้ไม่ได้ตลอดกาล**
8. ความไม่ตรงกันที่ต้องเคลียร์: `tools/pf_damage_hit_result_static.py` บรรยาย apply loop `0x464436..0x4644E0`
   ว่า "bit `0x40` คุม `+0x44` (HP ปัจจุบัน), sign bit คุม `+0x48` (HP สูงสุด), bit `0x800` คุม `+0x58` (นาฬิกาตาย)"
   ขณะที่ HYP-PF-020/022 ใช้ mask bit `0x0004`/`0x0008`/`0x0080` สำหรับ offset เดียวกัน
   — น่าจะเป็นคนละ mask (mask ของ apply loop ฝั่งแสดงผล vs mask ของ serializer) แต่ **ยังไม่ได้พิสูจน์**
   ห้ามให้เลนไหนอ้างทั้งสองชุดพร้อมกันจนกว่าจะเคลียร์

---

## 2. สูตรที่เสนอ

### 2.1 หลักการออกแบบ

1. **integer ล้วน ไม่มี float ในสูตร** — float32 ที่เรามีบนสายคือ yaw กับ position เท่านั้น
   ค่าความเสียหายเป็น i32 ดังนั้นถ้าคำนวณเป็น float แล้วปัด จะมีปัญหาการทำซ้ำข้ามแพลตฟอร์ม
   คำนวณด้วย `int` ของ Python (ความละเอียดไม่จำกัด) แล้ว **ตรวจช่วงตอนท้าย** ไม่ใช่ปล่อยให้ wrap
2. **deterministic 100%** — ไม่มี `random` ไม่มี `time` ไม่มี dict ordering
   ถ้าจะมีความแปรผัน ให้ใช้ jitter ที่ได้จาก hash (ดู 2.3) ซึ่งทำซ้ำได้บิตต่อบิต
3. **input ต้องเป็นสิ่งที่เซิร์ฟเวอร์รู้จริง** — ไคลเอนต์คำนวณ atk/def เองแค่เพื่อแสดง tooltip
   จากตาราง `STANDARD_STATUS` ที่เรา **ยังไม่ได้ถอด column** ดังนั้นเราจะไม่แกล้งใช้ "atk/def ของเกม"
   เราจะ **นิยาม atk/def ของเราเอง** จากฟิลด์ที่เซิร์ฟเวอร์เราปล่อยได้จริงอยู่แล้ว
   (จากตาราง 23 ฟิลด์ของ HYP-PF-020: `level`, `hp_current`, `hp_max`, `mp_current`, `mp_max`,
   `ability_str/con/dex/int/per`, `ability_bonus_*`, `class_id`)
4. **เครื่องหมายคือความหมาย** — ค่าที่ส่งจริงเป็น **ลบ** ผู้เล่นเห็นเป็นบวกเพราะ `abs()`
   นี่คือจุดที่พลาดง่ายที่สุดของเลนนี้ ต้องมี guard ที่ปฏิเสธค่าบวก

### 2.2 สูตร

นิยามของเรา (ทุกค่าเป็น int):

```
ATK(a) = ATK_BASE + K_ATK_STR * (a.ability_str + a.ability_bonus_str)
                  + K_ATK_LV  * a.level

DEF(d) = DEF_BASE + K_DEF_CON * (d.ability_con + d.ability_bonus_con)
                  + K_DEF_LV  * d.level

base   = ATK(a) - DEF(d)
base   = max(base, MIN_HIT)                      # พื้นความเสียหาย

rolled = base * (100 + jitter_pct) // 100        # jitter_pct ดู 2.3 ; phase 1 = 0
rolled = max(rolled, MIN_HIT)

if CRIT : rolled = rolled * CRIT_NUM // CRIT_DEN     # phase 2 เท่านั้น
if BLOCK: rolled = max(rolled * BLOCK_NUM // BLOCK_DEN, MIN_HIT)   # phase 2 เท่านั้น

damage_wire = -rolled                            # ลบ = โดนความเสียหาย
if MISS: damage_wire = 0  และ flags ต้องไม่ตั้ง bit0
```

ค่าคงที่ที่เสนอ (**ทั้งหมดเป็นตัวเลขที่เราตั้งเอง — ไม่ใช่ของเซิร์ฟเวอร์ต้นฉบับ**):

| ค่าคงที่ | ค่า | เหตุผล |
|---|---|---|
| `ATK_BASE` | 100 | ทำให้ตัวละครเริ่มต้นยังตีติด (ไม่ตกพื้น) |
| `K_ATK_STR` | 7 | เลขเฉพาะ ไม่ใช่กำลังสอง ทำให้เลขที่ขึ้นจอ "ไม่ดูเหมือนของบังเอิญ" |
| `K_ATK_LV` | 3 | เลเวลมีผลจริงแต่น้อยกว่า STR |
| `DEF_BASE` | 10 | |
| `K_DEF_CON` | 2 | |
| `K_DEF_LV` | 1 | |
| `MIN_HIT` | 1 | ต่ำสุดที่ยังเป็น "โดน" ตามกติกา miss = damage 0 + bit0 clear |
| `CRIT_NUM/DEN` | 3/2 | phase 2 |
| `BLOCK_NUM/DEN` | 1/2 | phase 2 |

ตัวอย่างที่คำนวณจริง (ผู้ป้องกัน = ตัวละครผู้เล่นที่ baseline ของ HYP-PF-020:
`level=7`, `ability_con=22`, `ability_bonus_con=0`):

```
DEF = 10 + 2*22 + 1*7 = 61
```

| โปรไฟล์ผู้โจมตี | str | level | ATK | base | damage_wire | เลขบนจอ |
|---|---|---|---|---|---|---|
| `MOB_WEAK` | 3 | 1 | 100 + 21 + 3 = 124 | 63 | **-63** | **63** |
| `MOB_STRONG` | 40 | 20 | 100 + 280 + 60 = 440 | 379 | **-379** | **379** |
| `MOB_TINY` (unit test) | 0 | 0 | 100 | 39 | -39 | 39 |
| floor case (unit test, `DEF` สูง: con 60 lv 30 => 160) | 0 | 0 | 100 | -60 -> `MIN_HIT` | **-1** | 1 |

63 กับ 379 ถูกเลือกเพราะ **ไม่กลม ไม่ใช่กำลังสอง ไม่ใช่ค่าที่ UI จะสร้างเองได้**
ถ้าผู้เทสเห็นเลขอื่น = สูตร drift หรือไคลเอนต์ scale (ซึ่งจะ falsify `damage_field_scale_factor = 1`)

### 2.3 jitter ที่ทำซ้ำได้ (phase 2)

ไม่มี RNG ในเลนนี้ ความแปรผันมาจาก hash ที่กำหนดผลได้แน่นอน:

```
h = sha256(seed_bytes || u64_le(attacker_identity) || u64_le(target_identity) || u32_le(step_index))
jitter_pct = (int.from_bytes(h[:8], "big") % (2*JITTER_PCT_MAX + 1)) - JITTER_PCT_MAX
```

* `seed_bytes` = ค่าคงที่ยาว 16 ไบต์ ปักไว้ในไฟล์ scenario (เปลี่ยน seed = version ใหม่ ไม่ใช่แก้ของเดิม)
* `JITTER_PCT_MAX` = **0 ใน phase 1** (เลขต้องเดาได้แน่นอนเพื่อให้ผู้เทสตัดสินได้) และ 10 ใน phase 2
* ใช้ `hashlib` stdlib ไม่มี dependency และ reproduce ได้ข้ามเครื่อง

### 2.4 ช่วงค่าปลอดภัยของ i32 และพฤติกรรมเมื่อเกิน / ติดลบ

ช่วงจริงของ i32 = `-2147483648 .. 2147483647`

| กติกา | ค่า | เหตุผล |
|---|---|---|
| `DAMAGE_WIRE_MAX` | `0` | **ห้ามส่งค่าบวกเด็ดขาดใน phase 1** เพราะความหมายของค่าไม่ติดลบ (heal/absorb/no-op) **ยังไม่รู้** |
| `DAMAGE_WIRE_MIN` (encoder hard band) | `-1_000_000` | ห่างจาก `INT32_MIN` มากพอที่ `abs()` ปลอดภัย และเลข 7 หลักยังพอเป็นไปได้บน glyph builder |
| `DAMAGE_WIRE_SCENARIO_MIN` (phase 1) | `-9999` | เลขไม่เกิน 4 หลัก อ่านออกบนจอชัด ๆ ในรอบเทสแรก |
| `INT32_MIN` | ปฏิเสธแยกเป็นข้อของตัวเอง | **อันตรายจริง:** `abs(INT32_MIN)` ด้วยลำดับ `cdq/xor/sub` ให้ `0x80000000` กลับมา แล้ว `"%d"` พิมพ์ `-2147483648` — เครื่องหมายลบจะโผล่บนจอทั้งที่เส้นทางออกแบบมาเพื่อไม่ให้โผล่ |

**พฤติกรรมเมื่อ overflow:** ห้าม wrap ห้าม mask ห้าม clamp เงียบ ๆ
คำนวณด้วย int ความละเอียดไม่จำกัด แล้ว **ตรวจช่วงตอนท้าย ถ้าออกนอกช่วง = raise ไม่มีไบต์ออก**
(ถ้า clamp เงียบ ๆ เราจะไม่มีวันรู้ว่าสูตรพัง — fail closed สำคัญกว่าเฟรมที่ส่งได้)

**heal:** **ไม่ implement ใน phase 1** ค่าบวกคือ `[UNKNOWN]` — "ยังไม่รู้ = ห้ามส่ง"
ถ้าจะทำ heal ต้องเป็น version ใหม่ที่มี GT ของตัวเองมาพิสูจน์ว่าไคลเอนต์ทำอะไรกับค่าบวก

### 2.5 flag word `+0x1C` เข้ารหัสอะไร

**allowlist ระดับค่าเต็ม (แน่นที่สุด — encoder รับได้แค่ค่าเหล่านี้ใน phase 1):**

| ค่า | bits | ความหมายที่เราตั้ง | อาศัยหลักฐาน |
|---|---|---|---|
| `0x0000` | — | **MISS** (ต้องคู่กับ `damage_wire == 0`) | กติกาที่รายงานให้: `bit0 clear && damage == 0` |
| `0x0001` | 0 | **HIT** ธรรมดา เปิดบล็อก apply | bit0 ปักไบต์แล้ว `0x7509D6` |
| `0x0009` | 0,3 | **HIT + REACTION** | bit3 ปักไบต์แล้ว `0x750A1C` |

**mask ป้องกันชั้นสอง:** `FLAGS_ALLOWED_MASK_PHASE1 = 0x0009` — ค่าใดที่มี bit นอก mask = ปฏิเสธ

**bit ที่ "ยังไม่รู้ = ห้ามส่ง" (forbidden ตลอด phase 1):**

| bit | mask | เหตุผลที่ห้าม |
|---|---|---|
| 2 | `0x0004` | ไม่พบจุดเทสเลย |
| 7 | `0x0080` | **ถูกเทสจริง** (`0x750A84`) แต่ไม่รู้ว่าทำอะไร — อันตรายที่สุดในกลุ่มนี้ |
| 8 | `0x0100` | ไม่พบจุดเทส |
| 11..15 | `0xF800` | ไม่พบจุดเทส |

**bit ที่มีหลักฐานแต่ยังไม่ใช้ใน phase 1 (ต้องผ่าน GT ก่อน จึงย้ายเข้า allowlist ใน version ถัดไป):**

| bit | mask | ทำไมยังไม่ใช้ |
|---|---|---|
| 1 | `0x0002` | ชื่อ "block" เป็นการอนุมานจาก texture |
| 4 | `0x0010` | **ตั้งแล้วไคลเอนต์เล่น `_F_KNOCKED_002` แทนการโชว์ตัวเลข** — ห้ามผสมกับเฟรมที่ต้องการให้ผู้เทสอ่านเลข ต้องเป็น GT แยก |
| 5, 6 | `0x0020`, `0x0040` | สีตัวเลข HP/MP เป็นการอนุมาน และเกี่ยวพันกับหัวฟิลด์ที่ 4 (`+0x24`) ที่ยังไม่รู้ |
| 9 | `0x0200` | crit เป็นการอนุมานจาก flag->texture map |
| 10 | `0x0400` | overkill เป็นการอนุมานจาก flag->texture map |

### 2.6 อีกสามฟิลด์ของ element ที่ "ต้องส่งแต่ไม่ได้ออกแบบ"

Panya อนุมัติพื้นที่ออกแบบ = 2 ฟิลด์ (i32 + flag word) แต่สายบังคับให้ปล่อยครบ 5
ดังนั้นอีกสามฟิลด์ **ปักหมุด ไม่ออกแบบ**:

| ฟิลด์ | ค่าที่ปัก phase 1 | เหตุผล |
|---|---|---|
| `+0x00` identity เป้าหมาย | identity ของ actor ผู้เล่นที่ selected | เป็น identity เดียวที่แน่ใจว่าไคลเอนต์รู้จัก |
| `+0x0C` Vector3 | XYZ ที่มาจาก source ที่ hash-pin แล้ว (frozen placement / ตำแหน่ง spawn V135) | ห้ามแต่ง XYZ ขึ้นเอง |
| `+0x18` yaw | `0.0f` พอดี | เป็นมุม ถูกป้อนเข้า sin/cos และบวก pi (`0xF0D140` = 3.14159274) — 0.0f คือค่าที่ไร้ผลที่สุดที่ยังถูกต้องตามชนิด |

หัวเฟรมฟิลด์ 2, 3, 5 และ 4 (`+0x20`, `+0x22`, `+0x28`, `+0x24`) ปัก `0` ทั้งหมด
และ encoder ปฏิเสธถ้ามีใครส่งค่าอื่น — **การปัก 0 ก็เป็นข้อสมมติ** (ว่า 0 เฉื่อย) และต้องอยู่ในรายการ nonclaims

### 2.7 ขนาดที่คาดว่าจะได้ `[DERIVED — ต้อง assert ในเทส ไม่ใช่เชื่อ]`

* payload `CHitResult` (N=1) = 22 (หัว) + 3 (count) + 37 (1 element) = **62 ไบต์**
* PC ทั้งเฟรมผ่าน `legacy.make_runtime_vitals([...])` = `STATS_PC_PAYLOAD_OFFSET`(20) + 62 + trailing `0B 00`(2) = **84 ไบต์**
* ขนาด frame (หลัง `frame_pc`) **ไม่ทำนายในเอกสารนี้** — ใน HYP-PF-023 ส่วนต่าง pc->frame ไม่คงที่ (173->185 แต่ 120->131)
  ให้ encoder pin เอาจากการคำนวณจริง

---

## 3. แผน implement ตาม pattern มาตรฐาน

### 3.1 หมายเลข hypothesis

ตรวจ `docs/HYPOTHESIS_LEDGER.json` แล้ว: entries 30 รายการ id สูงสุดในตระกูล HYP-PF คือ **HYP-PF-023** (active)
(`HYP-PF-999` ที่ grep เจอในรีโปมาจากไฟล์เทส ไม่ได้อยู่ใน ledger)

=> เสนอ **`HYP-PF-024`**

| ช่อง ledger | ค่าที่เสนอ |
|---|---|
| `id` | `HYP-PF-024` |
| `kind` | `protocol_hypothesis` |
| `introduced_checkpoint` | `DAMAGE-ENCODER-001` |
| `status` | `active` |
| `production_allowed` | `false` |
| `max_versions` | 3 |
| `expiry.tracked_versions` | `["DAMAGE-ENCODER-001"]` แล้วเพิ่ม `"DAMAGE-DISPATCH-001"` เมื่อ runtime.py ต่อสาย (แบบเดียวกับ HYP-PF-023) |
| `evidence_refs` | รายงาน DAMAGE-MODEL-001, scenario, verifier, headless replay, ไฟล์เทสทั้งสอง, และเอกสารร่างนี้ |

### 3.2 ชื่อไฟล์ทั้งชุด

| ของ | ชื่อที่เสนอ |
|---|---|
| module ใหม่ | `src/pirateforce_foundation/damage_model_hypothesis.py` |
| scenario json | `scenarios/damage_model_hypothesis_hit_sweep.json` |
| `response_policy` | `compose_chit_result_hit_entries_from_our_own_formula_no_write_no_close` |
| CLI flag | `--damage-model-hypothesis-scenario` (ลงทะเบียนใน `src/pirateforce_foundation/app.py` บรรทัด `pre.add_argument(...)` ต่อจาก `--runtimeres-death-hypothesis-scenario` และ **ต้องเพิ่มเข้าในรายการ mutually exclusive** กับข้อความ error `--damage-model-hypothesis-scenario requires an explicit existing --db`) |
| dispatch kwarg | `damage_model_hypothesis_scenario` |
| runtime dispatch fn | `_dispatch_damage_model_hypothesis` ใน `src/pirateforce_foundation/runtime.py` |
| verifier | `tools/verify_damage_model_encoder.py` |
| headless replay | `tools/pf_damage_model_headless_replay.py` |
| เทส encoder | `tests/test_damage_model_hypothesis.py` |
| เทส dispatch | `tests/test_damage_model_dispatch.py` |
| รายงานปิดงาน | `reports/PF_DAMAGE_ENCODER001_OUR_OWN_HIT_RESULT_20260819.md` |
| action label prefix | `HYP_PF_024_DAMAGE_MODEL_` |

### 3.3 โครงภายใน module (ตาม pattern HYP-PF-022 / HYP-PF-023)

```
production_allowed = False
DAMAGE_MODEL_SCENARIO_ID    = "damage_model_hypothesis_hit_sweep"
DAMAGE_MODEL_HYPOTHESIS_ID  = "HYP-PF-024"
DAMAGE_MODEL_DISPATCH_KWARG = "damage_model_hypothesis_scenario"

CHIT_RESULT_VITAL_ID = 0x16F7
CHIT_RESULT_VITAL_VERSION = <ยังไม่รู้ - ต้องปิด unknown #4 ก่อนเขียนบรรทัดนี้>
HIT_ELEMENT_STRIDE = 32
HIT_ELEMENT_WIRE_SIZE = 37          # assert กับ encoder จริง
CHIT_RESULT_HEADER_WIRE_SIZE = 22   # assert กับ encoder จริง
DAMAGE_TAG = 0x14 ; DAMAGE_OFFSET = 0x08
FLAGS_TAG  = 0x12 ; FLAGS_OFFSET  = 0x1C
YAW_TAG    = 0x2A ; YAW_OFFSET    = 0x18
TARGET_ID_TAG = 0x32 ; TARGET_ID_OFFSET = 0x00
DAMAGE_WIRE_MIN = -1_000_000 ; DAMAGE_WIRE_MAX = 0 ; INT32_MIN = -2147483648
FLAGS_VALUE_ALLOWLIST_PHASE1 = (0x0000, 0x0001, 0x0009)
FLAGS_ALLOWED_MASK_PHASE1 = 0x0009
FLAGS_FORBIDDEN_MASK = 0xF184        # bit 2,7,8,11..15
STATIC_ANCHORS = { ... VA ทุกตัวจากหัวข้อ 1 ... }

@dataclass(frozen=True) class DamageProfile:      # atk/def ของเราเอง
@dataclass(frozen=True) class DamageModelWireUnlock
@dataclass(frozen=True) class DamageModelHypothesisScenario
_UNLOCK / _PROFILE  (singleton เทียบด้วย identity ไม่ใช่ค่า)

def damage_model_wire_unlock(value) -> DamageModelWireUnlock
def require_damage_model_wire_unlock(value)
def require_damage_model_hypothesis_scenario(value)
def compute_damage(attacker: DamageProfile, defender: DamageProfile, step_index, seed) -> int
def encode_hit_entry(legacy, target_identity, damage_wire, position, yaw, flags, unlock) -> bytes
def encode_chit_result(legacy, performer_identity, entries, unlock) -> bytes
def make_damage_model_step_response(legacy, actor, step_index, unlock, profile) -> (pc, frame)
def build_damage_model_sweep(legacy, actor, unlock, profile) -> list[(label, pc, frame, delay)]
def decode_chit_result_frame(pc) -> dict          # decoder ของ module เอง (คนละตัวกับของ verifier)
def validate_damage_model_sweep(actions, profile) -> list[dict]
DAMAGE_MODEL_PINS: dict[str, dict]                # pc_size / pc_sha256 / frame_size / frame_sha256 ต่อ step
```

**Ledger markers ที่ต้องมี** (ผูกสองทางโดย `tools/verify_hypothesis_ledger.py` / `tests/test_hypothesis_ledger.py`):
`PF-HYPOTHESIS-LEDGER: HYP-PF-024 active` ใน module (คอมเมนต์เดียวบน emitter), ใน `runtime.py`, ใน `app.py`
และ scenario json ต้องมี `"hypothesis_id": "HYP-PF-024"`, `"hypothesis_id_is_registered_in_the_ledger": true`,
`"production_allowed": false`, `"test_only": true`, `"one_shot": true`, `"database_write": "none"`, `"socket_action": "none"`

### 3.4 sweep ที่เสนอ (phase 1, 4 เฟรม)

| # | step label | ผู้โจมตี | damage_wire | flags | สิ่งที่คาดว่าจะเห็น |
|---|---|---|---|---|---|
| 1 | `HIT_WEAK` | `MOB_WEAK` | `-63` | `0x0001` | เลข **63** ลอยเหนือหัวตัวเอง |
| 2 | `HIT_STRONG` | `MOB_STRONG` | `-379` | `0x0001` | เลข **379** |
| 3 | `MISS` | `MOB_WEAK` | `0` | `0x0000` | **ไม่มีเลข ไม่มีปฏิกิริยา** |
| 4 | `HIT_REACTION` | `MOB_WEAK` | `-63` | `0x0009` | เลข **63** + ท่าปฏิกิริยาการโดนตี |

* `spacing_seconds` = 6.0, `first_frame_delay_seconds` = 0.0, `delay_semantics` = `gap_before_each_send_on_a_cumulative_deadline` (เหมือนทุกเลน)
* `one_shot` = true
* trigger = เฟรม chat input ascii12 34 ไบต์ที่ `classify_chat_input_attempt` รับอยู่แล้ว **ใช้เป็นทริกเกอร์เท่านั้น ไม่อ่านเนื้อหา**
* guard ก่อนตอบ: `selected` ไม่ใช่ None, `teleport_sent` และ `runtime_ack_sent` เป็นจริง, ยังไม่เคยส่ง sweep
* event ที่บันทึก:
  `damage_model_hypothesis_hit_sweep_sent` /
  `damage_model_hypothesis_no_selected_no_reply` /
  `damage_model_hypothesis_wrong_sequence_no_reply` /
  `damage_model_hypothesis_already_sent_no_reply` /
  `damage_model_hypothesis_<classification>_no_reply`
* **ผู้โจมตีและเป้าหมายเป็น identity ของผู้เล่นเองทั้งคู่ใน phase 1** (self-hit) เพราะเป็น identity เดียวที่แน่ใจว่าไคลเอนต์รู้จัก
  — เป็น **design choice** เพื่อเลี่ยง unknown #6 ไม่ใช่ข้อพิสูจน์ว่านี่คือรูปแบบที่ถูก

### 3.5 รายการ rejection ที่ต้อง fail closed (ไม่มีไบต์ ไม่มีการตอบ ไม่เขียน DB)

ทุกข้อต้องมีชื่อ reason ของตัวเอง และมี guard ใน verifier ว่า "rejection นี้ไม่ผลิตไบต์"

| # | reason | เงื่อนไข |
|---|---|---|
| 1 | `damage_not_integer` | ไม่ใช่ `int` (รวม `bool` ต้องถูกปฏิเสธ) |
| 2 | `damage_positive_heal_semantics_unknown` | `> 0` |
| 3 | `damage_below_safe_band` | `< DAMAGE_WIRE_MIN` |
| 4 | `damage_is_int32_min` | `== -2147483648` (abs overflow) |
| 5 | `damage_outside_scenario_band` | นอก `-9999..0` เมื่ออยู่ใน scenario phase 1 |
| 6 | `damage_zero_with_apply_flag` | `damage == 0` แต่ `flags & 0x0001` |
| 7 | `damage_nonzero_without_apply_flag` | `damage != 0` แต่ `not (flags & 0x0001)` |
| 8 | `flags_not_u16` | ไม่ใช่ int, `bool`, หรือ `< 0` / `> 0xFFFF` |
| 9 | `flags_outside_value_allowlist` | ไม่อยู่ใน `FLAGS_VALUE_ALLOWLIST_PHASE1` |
| 10 | `flags_bit_outside_allowed_mask` | `flags & ~FLAGS_ALLOWED_MASK_PHASE1` |
| 11 | `flags_forbidden_bit` | `flags & FLAGS_FORBIDDEN_MASK` (bit 2/7/8/11..15) |
| 12 | `flags_knockback_bit_suppresses_the_number` | `flags & 0x0010` บนเฟรมที่ประกาศว่าต้องอ่านเลขได้ |
| 13 | `yaw_not_finite_float32` | ไม่ใช่ float / เป็น inf / nan / เกินช่วง float32 / แทนใน 32 บิตไม่ตรง |
| 14 | `yaw_outside_pinned_value` | phase 1 บังคับ `0.0` พอดี |
| 15 | `position_not_from_the_pinned_source` | XYZ ไม่ตรงกับแหล่งที่ hash-pin |
| 16 | `target_identity_outside_qword` | ไม่อยู่ใน 0..2**64-1 |
| 17 | `performer_identity_not_the_selected_actor` | phase 1 บังคับให้เป็น identity ของผู้เล่น |
| 18 | `entry_count_not_pinned` | phase 1 บังคับ count == 1 |
| 19 | `header_reserved_field_nonzero` | `+0x20`/`+0x22`/`+0x24`/`+0x28` ไม่เท่ากับ 0 |
| 20 | `missing_or_forged_wire_unlock` | token ไม่ใช่ตัวเดียวกัน (เทียบด้วย `is`) — ของปลอมที่ `==` ต้องยังเปิดไม่ได้ |
| 21 | `scenario_object_exceeds_allowlist` | scenario object ไม่ใช่ singleton ที่กำหนด |
| 22 | `scenario_file_exceeds_allowlist` | ไฟล์ json มี key เกิน / ขาด / ชนิดเปลี่ยน (เทียบทั้งต้นไม้แบบ exact) |
| 23 | `unknown_step_label` | step index นอก plan (รวม `-1`, `len()`, `True`, `1.0`) |
| 24 | `formula_input_outside_declared_domain` | level / ability นอกช่วง u16 ที่ประกาศ |
| 25 | `formula_output_not_reproducible` | คำนวณซ้ำแล้วได้คนละค่า |
| 26 | `vital_version_not_pinned` | version byte ไม่ใช่ค่าที่ปัก (ต้องปิด unknown #4 ก่อน) |
| 27 | `composed_bytes_do_not_match_the_pin` | pc/frame sha256 ไม่ตรง pin ทั้งใน module และในไฟล์ scenario |
| 28 | `sweep_does_not_contain_a_miss_frame` | sweep ที่ไม่มีเฟรม miss (เฟรม miss คือ control ของการทดลอง) |

หมายเหตุการล็อกโดยปริยาย: **ถ้าไม่มี unlock token ตัวโมดูลต้องเรียกชื่อฟิลด์ `+0x08`/`+0x1C` ไม่ได้เลย**
และ decoder ต้องปฏิเสธ body ที่มี `CHitResult` ทั้งก้อน — เหมือนที่ HYP-PF-022 ทำกับ BasicAttr bit `0x0080`

---

## 4. แผนพิสูจน์ headless (ไม่ต้องมี UI)

### 4.1 `tools/verify_damage_model_encoder.py` — offline, pure stdlib, ไม่มี network ไม่มี DB

| หมวด | สิ่งที่ตรวจ |
|---|---|
| 1. contract | ถอด contract จากหัวข้อ 1 ของเอกสารนี้มาไว้ในตัว verifier **อีกชุดหนึ่งอิสระ** แล้วเทียบกับค่าคงที่ของ module: tag map, หัว 5 ฟิลด์พร้อม offset/tag/emit VA, element 5 ฟิลด์, stride 32, ความกว้าง wire 22 / 37 |
| 2. ล็อกโดยปริยาย | ไม่มี token -> เรียกชื่อฟิลด์ไม่ได้, compose ไม่ได้, decode body ที่มี CHitResult ไม่ได้; token ปลอมที่ `==` ของจริงยัง **เปิดไม่ได้** (เทียบด้วย `is`) |
| 3. pins | ทั้ง 4 step reproduce ทุก sha256 pin ที่อยู่ใน module **และ** ที่อยู่ในไฟล์ scenario จากการคำนวณสด |
| 4. สูตร | ตาราง input->output ที่คำนวณมือไว้ในตัว verifier (63, 379, 39, floor=1) ต้องตรงกับ `compute_damage` |
| 4b. determinism | เรียก `build_damage_model_sweep` 1000 ครั้งได้ไบต์เดียวกันทุกครั้ง; เรียกใน interpreter ใหม่แล้ว sha256 เท่าเดิม; ไม่มี `random`/`time`/`os.urandom` ใน module (ตรวจด้วยการอ่าน source) |
| 4c. เครื่องหมาย | ทุกเฟรมที่มีตัวเลข ค่าที่อ่านกลับจากไบต์ต้อง **ติดลบ** และ `abs()` ของมันตรงกับเลขที่ประกาศไว้ใน scenario |
| 5. rejection | ทั้ง 28 ข้อในตาราง 3.5 -> ไม่มีไบต์ออก และข้อความ error มีชื่อ reason นั้น |
| 6. containment | มีแค่ `app.py` กับ `runtime.py` ที่ import module นี้; การอ้างถึงใน `runtime.py` อยู่หลัง scenario gate; module ไม่เอ่ยชื่อ verb ใด ๆ ที่อยู่นอกขอบเขต (Relive/ActionVital/skill) |
| 7. `--binary` (optional, SKIP ได้) | re-assert byte span จากไคลเอนต์: `0x750040` (ตัว serializer), `0x74F625` (โซ่ element ยาว 0x50), `0x74F5B3` (`c1f805`), `0x74F686` (`83c320`), 4 จุด signed compare, `0xA7EBFB..0xA7EC04` (9 ไบต์ของ abs), `0xF48B4C` = `L"_F_KNOCKED_002"`, `0xF14A94` = `"%d"` · ถ้าไม่ส่ง `--binary` ให้ SKIP และ **ไม่กระทบ exit code** (release gate ห้ามพึ่งไฟล์นอกรีโป) |

exit 0 = ทุก guard ผ่าน · exit 1 = มี guard drift พร้อมรายการ

### 4.2 `tools/pf_damage_model_headless_replay.py` — ผ่าน dispatcher จริง บน DB ชั่วคราว

* **คัดลอก** DB ไปไฟล์ temp (ห้ามแตะ `state/pirateforce.sqlite3`) แล้วรัน dispatcher จริงผ่าน `make_state_class`
* ป้อนเฟรม chat input ascii12 34 ไบต์หนึ่งเฟรม แล้วเก็บ actions ที่ dispatcher คืนมา
* **อ่านกลับด้วย tag walker อิสระที่เขียนอยู่ในไฟล์ tool นี้เอง — ห้าม import decoder ของ module**
  (เหมือนที่ HYP-PF-022/023 ทำ) walker ต้องเดินจากศูนย์: `0x12 0x6E9D` -> `0x14 u32` -> `0x08 u8=4` ->
  `0x0B u8=2` -> `0x12 count` -> `0x12 vital_id` -> `0x0B version` -> หัว 5 ฟิลด์ -> `0x12 entry count` -> N x 5 ฟิลด์ -> `0x0B 0x00`
* assert รายเฟรม: vital id = `0x16F7`, version = ค่าที่ปัก, header reserved 4 ตัวเป็น 0,
  entry count = 1, target identity = identity ผู้เล่น, damage เป็น i32 **signed** ตรงกับค่าที่ reference implementation
  (เขียนซ้ำในตัว tool ไม่ import ของ module) คำนวณได้, flags อยู่ใน allowlist, yaw = `0.0f` พอดี (เทียบไบต์ `00 00 00 00`),
  position ตรงกับแหล่งที่ pin
* assert ระดับ sweep: 4 เฟรม เรียงตาม `step_order`, label ตรง prefix, delay สะสม 0/6/12/18
* assert pin: pc_size / pc_sha256 / frame_size / frame_sha256 ทุก step ตรงทั้ง **pin ใน module** และ **pin ในไฟล์ scenario**
* assert ไม่มีผลข้างเคียง: นับจำนวนแถวทุกตารางก่อน/หลัง ต้องเท่ากัน, ไม่มี socket action, ไม่มีการปิด connection
* assert เชิงลบ: เมื่อ scenario **ไม่ได้** เปิด ต้องไม่มีไบต์ถูกประกอบเลย และการเรียก encoder ตรง ๆ ต้อง raise

### 4.3 หลักฐานที่จะเก็บ

1. `reports/PF_DAMAGE_ENCODER001_OUR_OWN_HIT_RESULT_20260819.md` พร้อมจำนวน guard ที่ผ่าน
2. stdout ของ verifier (จำนวน guard, exit code) และของ headless replay (json ผลลัพธ์ต่อ step)
3. `scenarios/damage_model_hypothesis_hit_sweep.json` ที่มี pin ครบ 4 step x 4 ค่า (pc_size, pc_sha256, frame_size, frame_sha256)
4. ledger entry `HYP-PF-024` พร้อม `source_refs` + `required_markers` ผูกสองทาง
5. ผล `pytest` ของไฟล์เทสทั้งสอง
6. sha256 ของ `GameClient.local.bin` ตรวจซ้ำก่อน/หลังทุกครั้งที่รัน `--binary`

**เพดานหลักฐานที่เลนนี้ไปถึงได้แบบ headless:** ชั้น **wire + dispatcher** เท่านั้น
ยังไม่ถึงไคลเอนต์แม้แต่มิลลิเมตรเดียว และยังไม่เคยผ่าน TCP จริง

---

## 5. รายการ UI test ที่ต้องเข้าคิวรอบใหญ่ (ร่าง)

> **หมายเลข GT เป็นข้อเสนอ** — เลขสูงสุดที่ค้นเจอในรีโป (docs/reports/scenarios/src/tools/STATUS.md) คือ **GT-022**
> คิวจริงอยู่ใน `pf_bridge/GAME_TEST_QUEUE.md` ซึ่งลูกมือไม่แตะ **ต้องให้ chief ยืนยันเลขก่อนจอง**

### GT-023 (เสนอ) — "ตัวเลขความเสียหายขึ้นจอตรงกับที่เซิร์ฟเวอร์ส่ง"

* **เตรียม:** บูตเซิร์ฟเวอร์ด้วย `--damage-model-hypothesis-scenario scenarios/damage_model_hypothesis_hit_sweep.json --db <db ที่มีอยู่จริง>`
* **ผู้เทสต้องกด:** ล็อกอิน -> เลือกตัวละคร -> เข้าฉาก -> รอจนตัวละครยืนนิ่ง -> พิมพ์ข้อความ chat ทริกเกอร์ **หนึ่งครั้ง** แล้วไม่ต้องกดอะไรอีก 20 วินาที
* **ต้องดู:** เหนือหัวตัวละครตัวเอง ที่ 0s / 6s / 12s / 18s
* **ผ่านเมื่อ:**
  1. ที่ 0s เห็นเลข **63** (สามหลัก อ่านได้ชัด)
  2. ที่ 6s เห็นเลข **379**
  3. ที่ 12s **ไม่เห็นเลขใด ๆ และไม่มีปฏิกิริยาใด ๆ** (เฟรม MISS)
  4. ที่ 18s เห็นเลข **63** อีกครั้ง พร้อมท่าปฏิกิริยาการโดนตี
  5. **แถบ HP ไม่ขยับเลยทั้งสี่เฟรม** — นี่คือผลที่คาดไว้ ไม่ใช่บั๊ก และเป็นหลักฐานยืนยันว่าไคลเอนต์ไม่คำนวณ/ไม่ลด HP เอง
  6. ไม่มี `ErrorData` ไม่มีการหลุดการเชื่อมต่อ ไม่มีข้อความสตรีมผิดพลาด
  7. log ฝั่งเซิร์ฟเวอร์มี event `damage_model_hypothesis_hit_sweep_sent` หนึ่งครั้ง
* **ไม่ผ่านเมื่อ:** เห็นเลขอื่นที่ไม่ใช่ 63/379 (= ไคลเอนต์ scale หรือสูตร drift) · เห็นเครื่องหมายลบ (= เครื่องหมายกลับด้าน) ·
  เห็นเลขบนเฟรม MISS (= การตีความ bit0 ผิด) · ไคลเอนต์หลุด (= tag/version/envelope ผิด) · แถบ HP ขยับ (= สมมติฐานว่าไคลเอนต์ไม่แตะ HP ผิด)
* **หลักฐานที่ต้องเก็บ:** ภาพหน้าจอ 4 ใบ (ใบละเฟรม) + วิดีโอ/คลิปสั้นทั้งช่วง 20 วินาที + log ฝั่งเซิร์ฟเวอร์

### GT-024 (เสนอ) — "เครื่องหมายคือความหมาย: บวก vs ลบ"

ต้องรอผลตัดสินจาก chief ก่อนว่าจะยอมส่งค่าบวกหรือไม่ (ตอนนี้ **ห้ามส่ง** ตามข้อ 2.4)
ถ้าอนุมัติ: sweep เฟรมเดียว damage `+63` flags `0x0001`
* **ผ่านเมื่อ:** บันทึกได้ชัดว่าจอแสดงอะไร (เลข 63 สีเดิม / สีอื่น / ไม่แสดง) และ **ไม่มีอาการเสียหายถาวร**
* จุดประสงค์คือ **ปิด unknown ข้อ 3** ไม่ใช่การเพิ่มฟีเจอร์ heal

### GT-025 (เสนอ) — "flag bits ที่ยังเป็นการอนุมาน"

sweep แยกเฟรมละ 1 bit บนค่าเลขเดียวกัน (`-63`) เพื่อให้อ่านความต่างได้:
`0x0003` (bit1 = block?), `0x0011` (bit4 = knockback), `0x0021`/`0x0041` (bit5/6 = สีเลข?), `0x0201` (bit9 = crit?), `0x0401` (bit10 = overkill?)
* **ผู้เทสต้องดู:** เฟรมไหนโชว์ **texture/effect** อะไร, เฟรมไหน **ไม่โชว์เลข**, เฟรมไหนเลขเปลี่ยนสี
* **ผ่านเมื่อ:** ได้ตารางแมป bit -> สิ่งที่เห็น ครบทุกเฟรม พร้อมภาพ (นี่คือ **การเก็บข้อมูล** ไม่ใช่การผ่าน/ไม่ผ่านเชิงฟีเจอร์)
* **หมายเหตุ:** bit 4 คาดว่าจะ **ไม่โชว์เลข** แต่เล่น `_F_KNOCKED_002` — ถ้าโชว์เลขด้วย แปลว่าการอ่าน `0x750A24` ต้องทบทวน
* **bit 7 (`0x0080`) ไม่อยู่ใน GT นี้** เพราะยังไม่รู้ว่ามันทำอะไร — ยังไม่รู้ = ห้ามส่ง

### GT-026 (เสนอ, ทีหลัง) — "ผูกกับ HP จริง"

ต้องรอ chief ตัดสินก่อน (ดูข้อ 7): ส่ง `CHitResult` คู่กับ `UpdateAttrVital` delta ของ `hp_current` (เลน HYP-PF-020/022)
เพื่อให้เลขที่เห็นกับแถบ HP สอดคล้องกัน — **นี่เป็นเลนใหม่ ไม่ใช่การแก้ของเดิม**

---

## 6. nonclaims ที่ต้องติดไปกับเลนนี้เสมอ

ต้องคัดลอกลงทั้ง `scenarios/damage_model_hypothesis_hit_sweep.json` และ ledger entry:

1. **`our_own_formula_not_the_original_servers_which_is_permanently_unrecoverable`**
   — นี่คือสูตรของเรา ไม่ใช่สูตรของเซิร์ฟเวอร์ต้นฉบับ ซึ่งกู้ไม่ได้ตลอดกาล
2. `no_client_has_ever_been_shown_one_byte_of_this_profile`
3. `no_claim_about_what_the_original_server_placed_in_any_field`
4. `no_semantic_name_for_any_result_flag_bit_is_claimed_the_names_are_read_off_textures`
5. `no_claim_about_header_fields_two_three_four_and_five_they_are_pinned_to_zero_as_a_design_choice`
6. `no_claim_that_a_non_negative_damage_value_means_heal_or_absorb_or_no_op`
7. `no_hp_mutation_this_lane_does_not_move_the_hp_bar_and_the_client_provably_will_not_move_it_by_itself`
8. `no_persistence_no_damage_or_combat_state_is_written_to_any_table_and_this_lane_opens_none`
9. `no_inbound_attack_request_is_handled_no_range_no_cooldown_no_authority_no_target_validation`
10. `no_skill_no_missile_no_ai_no_loot_no_death_penalty_and_no_interaction_with_the_hp_death_or_runtimeres_death_lanes`
11. `no_claim_that_the_vitaldata_collection_dispatcher_constructs_0x16F7_until_that_is_separately_proven`
12. `production_dispatch_wiring_the_wiring_is_opt_in_and_production_allowed_is_false`
13. `client_rendering_of_any_number_pending_gt023`
14. `the_wire_sizes_22_and_37_are_arithmetic_from_the_tag_map_not_a_measurement`

---

## 7. ความเสี่ยง / คำถามที่ยังต้องให้ chief ตัดสิน

1. **version byte ของ vital `0x16F7` ยังไม่รู้ และ "ลองเดา" ไม่ใช่ทางเลือกที่ยอมรับได้**
   เสนอ: ทำ static milestone เล็ก ๆ (`DAMAGE-MODEL-002`) ปิด unknown #4 และ #5 ก่อน แล้วค่อยเริ่ม `DAMAGE-ENCODER-001`
   หรือ chief จะให้เริ่มเขียน encoder คู่ขนานโดยเว้นค่าคงที่ไว้เป็น `None` และให้ทุกอย่าง fail closed จนกว่าจะเติมได้?
2. **ผู้โจมตี = ตัวผู้เล่นเอง (self-hit) ใน phase 1 โอเคไหม** หรือ chief ต้องการให้ผู้โจมตีเป็น NPC probe ของ HYP-PF-023
   (ซึ่งต้องรอ GT-022 ยืนยันก่อนว่า NPC ตัวนั้นปรากฏจริง)
3. **ค่าบวก (heal) จะเปิด GT-024 เพื่อปิด unknown ข้อ 3 เลยไหม** หรือปล่อยเป็น "ห้ามส่ง" ไปก่อน
4. **จะผูก `CHitResult` เข้ากับ `hp_current` delta ให้แถบ HP ขยับจริงไหม** — ถ้าจะทำ ต้องเป็นเลน/version ใหม่
   และต้องเคลียร์ความไม่ตรงกันของ mask bit ในข้อ 1.9 #8 ก่อน
5. **ความไม่ตรงกันของ mask bit (`0x40`/sign/`0x800` vs `0x0004`/`0x0008`/`0x0080`)** — ใครเป็นคนเคลียร์และเมื่อไหร่
   ตอนนี้ไม่กระทบเลนนี้ (เลนนี้ไม่แตะ BasicAttr) แต่กระทบทันทีถ้าตอบข้อ 4 ว่า "ทำ"
6. **หมายเลข GT** — GT-023..GT-026 ที่เสนอ ต้องเช็คกับ `pf_bridge/GAME_TEST_QUEUE.md` ก่อนจอง (ลูกมือไม่แตะไฟล์นั้น)
7. **ไฟล์ร่างนี้ถูก git ignore อยู่** — `.gitignore` บรรทัดที่ 1 คือ `/*` ซึ่งครอบ `drafts/` ทั้งโฟลเดอร์
   ถ้าต้องการให้ commit ได้ ต้องเพิ่ม negation ใน `.gitignore` ซึ่งลูกมือไม่ได้รับอนุญาตให้แก้

---

## ภาคผนวก A — ที่มาของทุกอย่างในเอกสารนี้

| อ้างอิง | ใช้ทำอะไร |
|---|---|
| `reports/PF_DAMAGE_MODEL001_CLIENT_HIT_RESULT_EXPECTATION_20260819.md` | contract ระดับไบต์ทั้งหมดในหัวข้อ 1 |
| `tools/pf_damage_hit_result_static.py` | ไบต์ที่ปักจริง, `bit_tests` dict, สรุป json (`damage_field_scale_factor = 1`, `bit_labels_claimed = False`) |
| `docs/HYPOTHESIS_LEDGER.json` | รูปแบบ entry, id ล่าสุด = HYP-PF-023, policy `max_related_versions = 3` |
| `src/pirateforce_foundation/stats_progression_hypothesis.py` | pattern HYP-PF-020/022: `AttrField`, unlock token เทียบด้วย identity, `_expected_*_scenario` allowlist แบบ exact, รายการ rejection, ตาราง 23 ฟิลด์ที่เซิร์ฟเวอร์เราปล่อยได้จริง |
| `src/pirateforce_foundation/runtimeres_death_hypothesis.py` | pattern HYP-PF-023: dataclass profile, `_PROFILE`/`_UNLOCK` singleton, `*_PINS`, `validate_*_sweep` |
| `src/pirateforce_foundation/runtime.py` | ตำแหน่งของ `_dispatch_*_hypothesis`, guard `selected`/`teleport_sent`/`runtime_ack_sent`, ชื่อ event |
| `src/pirateforce_foundation/app.py` | จุดลงทะเบียน CLI flag + รายการ mutually exclusive + ข้อความ `requires an explicit existing --db` |
| `scenarios/runtimeres_death_hypothesis_spawn_then_kill.json` | โครง scenario json ที่ต้องมี (schema/id/test_only/production_allowed/hypothesis_id/entry/dispatch/wire/probe/persisted_post_state/capabilities/nonclaims) |
| `tools/verify_hp_death_encoder.py` | โครง verifier: หมวด 1-7, `check()`, `--binary` แบบ SKIP ได้, pure stdlib |
| `current/pf_login_game_server_v141.py` | `make_runtime_vitals(vitals)` รับ `(msg_id, version, payload)`, `u16tag/u32tag/u8tag/f32tag` ทั้งหมดเป็น little-endian |
