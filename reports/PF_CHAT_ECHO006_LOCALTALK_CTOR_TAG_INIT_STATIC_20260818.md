# PF_CHAT_ECHO006 — LocalTalk render-tag: constructor initializes `+0x44/+0x45` (static disasm)

รอบ 56 (2026-08-18 scheduled) · chief · report-only additive · binary `GameClient.local.bin` SHA `9627211412AC60D5..` · capstone 5.0.7 (CS_MODE_32, ImageBase 0x400000)

เป้า: หนุน Q2 จาก B→A ตาม **next-hop ที่รอบ 55 ระบุ** = resolve vtable base ของ `0xF3640C`-region → constructor → คำสั่ง SET `+0x44/+0x45` → caller

> **ผลสรุปล่วงหน้า: เกรดของ Q2 ไม่เปลี่ยน** (negative A / positive B เดิม) — แต่รอบนี้**ปิดคำถาม "single-SET" ที่รอบ 55 ตั้งไว้** ได้ชั้นหนึ่ง: constructor **ไม่ได้** เขียน `+0x44/+0x45` เป็นค่าคงที่ประจำคลาส แต่ **zero-init ด้วย immediate 0** → ตัด hypothesis "hardcoded per-class discriminator ในตัว constructor" ออก และตอกย้ำว่า `+0x44/+0x45` เป็น per-instance byte field ที่ถูก populate ทีหลังตอน parse (runtime)

---

## 1. `0xF363xx`-region = message descriptor table (12 rows, stride 0x2C) — ไม่ใช่ vtable เดี่ยว

รอบ 55 เรียก `0xF3640C` ว่า "vtable get-type slot". รอบนี้ resolve โครงจริง: ย่านนี้เป็น**ตารางเรียงติดกัน stride `0x2C` (11 dwords/row)** ยืนยันจาก anchor คงที่ที่ recur ทุก 0x2C:

| column (off ใน row) | ค่า | หมายเหตุ |
|---|---|---|
| `+00` | get-type thunk (แปรตาม row) | คืน type-node ของคลาสนั้น |
| `+08` | `0x401B20` **คงที่ทุก row** | framework method ร่วม |
| `+1C` | `0x645BF0` **คงที่** | shared handler |
| `+20` | `0x710440` **คงที่** | shared handler |
| `+24` | `0x642AB0` **คงที่** | shared handler |
| `+28` | `0x9F17E0` **คงที่** | shared handler |

ตารางเริ่ม `0xF363B4` จบ `0xF365C4` = **12 rows** ต่อด้วย ASCII class-name strings ทันที (`Community_CommunityCommandNotAllowVital`, `Community_AddFriendVital`, `Community_RequestBeFriend…`).

- **target row #2** `0xF3640C` (get-type `0x642320` → node `0x1083F84`) = คลาสตัวจริงที่ gate 539/540 อ้างถึง (ตาม downcast chain รอบ 55)
- คอลัมน์ที่เป็น constant ร่วมทุก row (`0x401B20/0x645BF0/0x710440/0x642AB0/0x9F17E0`) = โครง base ร่วม; คอลัมน์ที่แปร = per-type → **โครงสร้าง registry keyed per message-type ตอกย้ำ negative Grade A** (dispatch ตาม id/registry ไม่ใช่ hardcoded switch ของ `0xAC52`)

## 2. Constructor ของคลาสตัวจริง — พบแล้ว 2 ตัว (target + sibling)

xref immediate ของ row-base `0xF3640C` ใน `.text` มีจุดเดียว = `0x642612` ซึ่งอยู่ในตัว constructor:

**target ctor `0x6425D0`** (ติดตั้ง vtable `0xF3640C`):
```
0x006425E3: 8bf1            mov  esi, ecx            ; esi = this
0x006425E9: 33db            xor  ebx, ebx            ; ebx = 0 (bl = 0)
0x006425EB: 885e04          mov  byte [esi+0x04], bl ; zero base fields...
0x006425F1: c7066c6df800    mov  dword [esi], 0xF86D6C ; vptr#1 = base vtable (COL RTTI ที่ -4)
   ... (zero +0x08/0x0C/0x10/0x11/0x18/0x1C/0x20) ...
0x00642610: c7060c64f300    mov  dword [esi], 0xF3640C ; vptr#2 = vtable ตัวจริง (row #2)
0x00642616: ff1578b4c300    call dword [0xC3B478]     ; MSVCP90 basic_string<wchar_t>::ctor -> [esi+0x28] = std::wstring
0x0064261C: 885e44          mov  byte [esi+0x44], bl  ; *** SET +0x44 = 0 (immediate ศูนย์ผ่าน bl) ***
0x0064261F: 8bc6            mov  eax, esi             ; return this
```

**sibling ctor `0x642540`** (ติดตั้ง vtable `0xF363E0` = row #1):
```
0x00642570: c706e063f300    mov  dword [esi], 0xF363E0 ; vptr = row #1
0x00642576: ff1578b4c300    call dword [0xC3B478]      ; [esi+0x28] = std::wstring
0x0064257C: 885e44          mov  byte [esi+0x44], bl   ; *** SET +0x44 = 0 ***
0x0064257F: 885e45          mov  byte [esi+0x45], bl   ; *** SET +0x45 = 0 ***
```

**ข้อสรุปสำคัญ:** ทั้งสอง constructor เขียน `+0x44` (และ sibling เขียน `+0x45` ด้วย) เป็น **`bl` = 0** — immediate ศูนย์ ไม่ใช่ค่าคงที่ประจำคลาส. object ที่เพิ่ง construct จึงมี `+0x44==0` → ตาม gate รอบ 55 (`+0x44==0 ∧ +0x45==0 → id 539`) จะ render `539` เป็นค่าตั้งต้น. การได้ `id 540 [ทั่วไป]` (`+0x44!=0`) ต้องมี **write ค่า nonzero ทีหลัง** = per-instance/runtime ไม่ได้มาจาก constructor
- หมายเหตุ: target ctor เขียนเฉพาะ `+0x44` (ไม่แตะ `+0x45`) ส่วน sibling เขียนทั้งคู่ → คลาสในตระกูลใช้ subset ของคู่ discriminator ต่างกัน; `+0x45` ของ target-class พึ่ง zeroing ก่อนหน้า/allocator (ยืนยัน static ไม่ได้ว่า memset — ไม่ claim)

## 3. Constructor ถูกเรียกทางอ้อม (factory/registry) — ตอกย้ำ negative A

- **ไม่มี `call rel32` ตรงไปที่ `0x6425D0` หรือ `0x642540`** (สแกน `.text` ทั้งหมด: 0 hit)
- **ไม่มี immediate `0x6425D0`/`0x642540` เก็บที่ใดในอิมเมจ** (สแกนทั้งไฟล์: 0 hit — ไม่ถูกเก็บเป็น absolute หรือ push constant)
- → object ถูกสร้างผ่าน **factory/registry ทางอ้อม** (สอดคล้องกับ dispatch keyed per-type) ไม่ใช่ `new Class()` ที่มี call ตรง

## 4. Render path อ่านอย่างเดียว — write อยู่คนละที่ (parse/populate)

สแกนช่วง render resolver `0x63F9B0..0x640700`: `+0x44/+0x45` ถูก **อ่านล้วน** (`movzx`/`cmp`) 6 จุด — `0x63FBEE, 0x63FE38, 0x63FF70, 0x640574, 0x6405AE (+0x45), 0x6405E7 (gate)` — **ไม่มี write** ในเส้น render → ยืนยันว่า `+0x44` ถูก set ตอน parse/populate (คนละ path) แล้ว render ค่อยอ่าน · `+0x28` = std::wstring (จาก call MSVCP90 ใน ctor) = text/speaker ของ message

---

## verify (byte-exact, .text off = VA−0x400C00 · .rdata off = VA−0x401C00 — ตรงรอบ 55)

| จุด | VA | file off | bytes | disasm |
|---|---|---|---|---|
| target ctor install vtable | `0x642610` | `0x241A10` | `c7060c64f300` | `mov dword [esi], 0xF3640C` |
| target ctor SET `+0x44`=bl | `0x64261C` | `0x241A1C` | `885e44` | `mov byte [esi+0x44], bl` |
| bl=0 source | `0x6425E9` | `0x2419E9` | `33db` | `xor ebx, ebx` |
| target ctor `[+0x28]` wstring | `0x642616` | `0x241A16` | `ff1578b4c300` | `call dword [0xC3B478]` (MSVCP90 wstring ctor) |
| sibling ctor install vtable | `0x642570` | `0x241970` | `c706e063f300` | `mov dword [esi], 0xF363E0` |
| sibling ctor SET `+0x44`=bl | `0x64257C` | `0x24197C` | `885e44` | `mov byte [esi+0x44], bl` |
| sibling ctor SET `+0x45`=bl | `0x64257F` | `0x24197F` | `885e45` | `mov byte [esi+0x45], bl` |
| render gate cmp `+0x44` | `0x6405E7` | `0x23F9E7` | `385844` | `cmp byte [eax+0x44], bl` |
| render read `+0x45` | `0x6405AE` | `0x23F9AE` | `0fb64845` | `movzx ecx, byte [eax+0x45]` |
| row#2 base (get-type dword) | `0xF3640C` | `0xB3480C` | `20236400` | `.rdata` → thunk `0x642320` |
| row#1 base (get-type dword) | `0xF363E0` | `0xB347E0` | `b0256400` | `.rdata` → thunk `0x6425B0` |

## grade
- **Q2 negative = A เดิม** (id/registry-keyed dispatch): เสริมด้วยโครง descriptor table 12-row + constructor เรียกทางอ้อม
- **Q2 positive = B เดิม** (render tag จาก object field ไม่ใช่ payload): เสริม/แคบลงด้วยการพิสูจน์ว่า constructor **zero-init** `+0x44/+0x45` (per-instance byte field ไม่ใช่ per-class const)
- **ไม่ดัน B→A**: ค่า nonzero ที่เขียน `+0x44` (เลือก 540 แทน 539) เกิดตอน parse/populate (runtime) — รอบนี้ยัง**ไม่ได้ pin static ว่า source ของค่านั้น = message identity** (ยังเป็นกำแพงเดิมของรอบ 55: ค่าถูกเขียนตอน runtime)

## nonclaims
1. ไม่ได้ trace ถึงคำสั่งที่เขียน `+0x44` เป็น **nonzero** และที่มาของค่า (wire channel field vs อื่น) — next hop
2. ไม่ได้ยืนยัน static ว่า block ถูก memset ก่อน ctor (จึงไม่ claim ว่า `+0x45` ของ target-class = 0 แน่นอน)
3. ไม่ได้พิสูจน์ client-observable ใด ๆ (เป็น static ล้วน) — ชั้นนั้นเป็นของ GT-012 รอบใหญ่

## next hop (รอบหน้า / attended)
1. **static:** หา parse/populate ที่เขียน `[obj+0x44]` เป็น nonzero บน object ตระกูลนี้ (vtable `0xF363B4..0xF365C4`) แล้วดูว่า source = wire channel/identity field หรือไม่ → ถ้าใช่ = ปิด B→A
2. **runtime:** GT-012 (attended) — จด label ที่ render จริงเทียบ prediction `[ทั่วไป]` id 540
