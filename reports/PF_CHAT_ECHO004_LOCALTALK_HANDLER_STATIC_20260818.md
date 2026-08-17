# PF CHAT-ECHO-004 — LocalTalk (0xAC52) handler static disassembly: field#1 semantics + channel-tag selection (2026-08-18)

งานวิจัยหลักฐานล้วน (static disassembly, ลูกมือใต้ lease ของ chief) — **ไม่มีการแก้โค้ด/ไม่แตะ binary/ไม่เปิด UI/ไม่แตะ DB/ไม่มี git**
เป้า: ปิดคำถามที่ CHAT-ECHO-002 ข้อ (d) ระบุว่าต้องใช้ static handler analysis — (Q1) field#1 ของ payload 0xAC52 ถูก consume เป็น length-prefixed wstring หรือ bare u32, (Q2) `[ทั่วไป]` (id 540) ถูกเลือกด้วย vital id หรือด้วย field ใน payload

## Binary ที่วิเคราะห์
- `GameClient/GameClient.local.bin` — PE32 x86, ImageBase `0x400000`, 14,759,424 B, SHA-256 เริ่ม `9627211412AC60D5...` (โปรไฟล์เดียวกับ NAME001; ผมวิเคราะห์ **เฉพาะ .local.bin** — parity กับ `GameClient.bin` อ้าง NAME001 ไม่ได้ re-verify รอบนี้)
- Sections: `.text` VA=0x00401000 raw@0x400 · `.rdata` VA=0x00C3B000 raw@0x839400 · `.data` VA=0x0101A000 raw@0xC17800
- สูตร VA↔offset: off = VA − ImageBase − sec.VA + sec.RawPtr (ใช้ per-section)

---

## สายหลักฐาน (anchor → handler) — ทำตามแนว NAME001

### 1. ชื่อ vital → id ที่ resolve ตอน runtime → cache ลง global word

ASCII `Channel_LocalTalkMessageVital` อยู่ 2 ที่: `.rdata` VA `0xF37984` (off `0xB35D84`) และสำเนาใน `.data` VA `0x10209EC`.
**เฉพาะสำเนา .rdata** ถูก push เป็น immediate ใน `.text` ที่เดียว: VA `0xBF72D0`.

```
0x00BF72D0: 68 84 79 f3 00     push 0xf37984                 ; &"Channel_LocalTalkMessageVital"
0x00BF72D5: e8 a6 4d ca ff     call 0x89c080                 ; resolve vital class by name
0x00BF72DA: 8b c8              mov ecx, eax
0x00BF72DC: e8 1f 4a ca ff     call 0x89bd00                 ; -> get numeric id (u16 in ax)
0x00BF72E1: 66 a3 58 44 08 01  mov word ptr [0x1084458], ax  ; cache LocalTalk id
0x00BF72E7: c3                 ret
```
guard@0xBF72D0[24] = `688479F300E8A64DCAFF8BC8E81F4ACAFF66A358440801C3`

เพื่อนบ้านชุดเดียวกัน (registration เรียงติดกัน) ยืนยันว่าเป็นตระกูล Channel_*:
- `0xBF72F0`: push `0xF379A4` (`Channel_LocalPerformanceVital`) → `mov [0x108445C], ax`
- `0xBF7330`: push `0xF379E0` (`Channel_WhisperVital`) → `mov [0x1084464], ax`

**Vital-id hash (สูตรที่โปรเจกต์กู้มา) ตรงกับ id ที่ใช้จริง — ตรวจซ้ำได้:**
`id = sum((i+1)*ord(c)) & 0xFFFF` ของ `Channel_LocalTalkMessageVital` = **0xAC52** ✓ · `Channel_WhisperVital` = **0x556C** ✓ · `Channel_LocalPerformanceVital` = **0xAE8C** ✓
(ตรงกับ registry TSV: 0xAC52/0x556C/0xAE8C) → global `[0x1084458]` = LocalTalk id 0xAC52, `[0x1084464]` = Whisper id 0x556C

### 2. global id ถูกอ่านโดย getter ตัวจิ๋ว = vtable method ของ vital class

`[0x1084458]` ถูกอ้างสองที่: (a) เขียนตอน register (0xBF72E3) (b) อ่านที่ getter `0x6580B0`:
```
0x006580B0: 66 a1 58 44 08 01  mov ax, word ptr [0x1084458] ; return LocalTalk id
0x006580B6: c3                 ret
```
guard@0x6580B0[7] = `66A158440801C3` · Whisper getter `0x6582B0` guard = `66A164440801C3` · LocalPerf getter `0x5BEAE0` guard = `66A15C440801C3`

getter ทั้งสามไม่ถูกเรียกด้วย `call` ตรง ๆ — มันเป็น **vtable slot** (เก็บเป็น pointer ใน `.rdata`): 0x6580B0 @ `0xF3776C`, 0x6582B0 @ `0xF37798`. ห่างกัน 0x2C = 11 dwords = ขนาด vtable ของ vital class นี้

### 3. vtable ของ LocalTalk vs Whisper — โครงเดียวกัน โค้ด wire เดียวกัน ต่างแค่ identity

| slot | LocalTalk (@0xF37744) | Whisper (@0xF37770) | บทบาท (จากการ disassemble) |
|---|---|---|---|
| idx1 | **0x65AD40** | **0x65AD40** (แชร์) | **(de)serialize visitor** — อ่าน/เขียน payload |
| idx4 | 0x65ACB0 | 0x65ACB0 (แชร์) | clone/copy — คัดลอกสมาชิก |
| idx6 | 0x6580A0→0x65A940 | 0x6582A0→0x65A970 | get object-pool (ต่างแค่ pointer pool ต่อ class) |
| idx7 | 0x6580C0 | 0x658320 | scalar deleting destructor (คืน object เข้า pool) |
| idx10| 0x6580B0 | 0x6582B0 | **get-id getter** (id ต่างกัน: 0xAC52 vs 0x556C) |
| idx2/3/8 | 0x65C850 / 0x710440 / 0x401B20 | เหมือนกัน | base methods ร่วม |

จุดสำคัญ: **LocalTalk กับ Whisper ใช้ (de)serialize (idx1) และ clone (idx4) ตัวเดียวกันเป๊ะ** — wire shape เหมือนกัน — ต่างกันแค่ vital id (idx10) กับ memory pool. นี่แปลว่า channel ถูกแยกด้วย "vital id ไหนถูก instantiate" ล้วน ๆ ไม่ใช่จาก field ใน payload

---

## Q1 — field#1 คือ length-prefixed wstring หรือ bare u32?  **ตอบ: length-prefixed tag-0x48 wstring — GRADE A**

### (de)serialize visitor 0x65AD40 (แชร์ LocalTalk+Whisper) — หลักฐานชี้ขาด
```
0x0065AD40: 53                push ebx
0x0065AD41: 8a 5c 24 0c       mov bl, [esp+0xc]      ; bl = direction (1=store/write, 0=load/read)
0x0065AD46: 8b f1             mov esi, ecx           ; esi = this (message object)
0x0065AD49: 8b 7c 24 10       mov edi, [esp+0x10]    ; edi = archive/stream
0x0065AD4D: 8d 46 34          lea eax, [esi+0x34]    ; &FIELD#1  (object+0x34)
0x0065AD50: 50                push eax
0x0065AD51: 8b cf             mov ecx, edi
0x0065AD53: 84 db             test bl, bl
0x0065AD55: 74 07             je 0x65AD5E
0x0065AD57: e8 b4 fa 23 00    call 0x89A810          ; WRITE wstring  (field#1)
0x0065AD5C: eb 05             jmp 0x65AD63
0x0065AD5E: e8 1d fb 23 00    call 0x89A880          ; READ  wstring  (field#1)  <== reader
0x0065AD63: 8d 46 18          lea eax, [esi+0x18]    ; &FIELD#2  (object+0x18)
0x0065AD66: 50                push eax
0x0065AD67: 8b cf             mov ecx, edi
0x0065AD69: 84 db             test bl, bl
0x0065AD6B: 74 0b             je 0x65AD78
0x0065AD6D: e8 9e fa 23 00    call 0x89A810          ; WRITE wstring  (field#2)
0x0065AD72: c2 08 00          ret 8
0x0065AD78: e8 03 fb 23 00    call 0x89A880          ; READ  wstring  (field#2)  <== reader
0x0065AD80: c2 08 00          ret 8
```
guard@0x65AD40[65] = `538A5C240C568BF1578B7C24108D4634508BCF84DB7407E8B4FA2300EB05E81DFB23008D4618508BCF84DB740BE89EFA23005F5E5BC20800E803FB23005F5E5BC2`

**ทั้ง field#1 (object+0x34) และ field#2 (object+0x18) อ่านด้วย reader ตัวเดียวกัน `0x89A880` — ไม่มี raw-u32 read ที่ไหนเลย**

### reader 0x89A880 = "อ่าน tag-0x48 wstring" (เดียวกับ codec ที่ NAME001 พิสูจน์ Grade A)
```
0x0089A89C: 6a 48             push 0x48              ; expected TAG byte = 0x48
0x0089A89E: e8 ad fc ff ff    call 0x89A550          ; verify next stream byte == 0x48
0x0089A8A3: 84 c0             test al,al
0x0089A8A5: 75 09             jne 0x89A8B0
...
0x0089A8B0: 8b 46 18          mov eax,[esi+0x18]     ; buffer base
0x0089A8B3: 8b 4e 1c          mov ecx,[esi+0x1c]     ; read cursor
0x0089A8B7: 8b 3c 08          mov edi,[eax+ecx]      ; edi = u32 BYTE-LENGTH (little-endian)
0x0089A8BA: 83 c0 04          add eax,4              ; advance 4
0x0089A8BD: 89 46 18          mov [esi+0x18],eax
0x0089A8C0: 85 ff             test edi,edi
0x0089A8C2: 75 0a             jne 0x89A8CE           ; len==0 -> empty wstring, return
...                            ; len!=0 -> bounds-check + copy edi bytes UTF-16LE (shr ebp,1 = char count)
```
guard@0x89A880[80] = `83EC48568BF1807E2100751B807E200075156830A4F50068080200006A48E8ADFCFFFF84C075098BC65E83C448C204008B46188B4E1C578B3C0883C00489461885FF750A5F8BC65E83C448C204007C62`

tag-checker `0x89A550` เทียบ byte ที่ stream กับ 0x48; ไม่ตรง → error id `0xE0000012`:
```
0x0089A5B7: 8b 51 1c          mov edx,[ecx+0x1c]
0x0089A5BB: 8a 5c 24 54       mov bl,[esp+0x54]      ; expected = 0x48
0x0089A5BF: 3a 1c 10          cmp bl,[eax+edx]       ; compare tag
0x0089A5C3: 74 2b             je 0x89A5F0            ; match
0x0089A5C5: ...               ; mismatch -> raise 0xE0000012
```
guard@0x89A5B7[16] = `8B511C538A5C24543A1C105B742B8B44`

### writer 0x89A810 — เขียน `tag 0x48` + `u32 byte-length` + UTF-16LE (ตรง wire เป๊ะ)
```
0x0089A833: 6a 48             push 0x48              ; emit TAG 0x48
0x0089A835: 8b ce             mov ecx,esi
0x0089A837: e8 94 fc ff ff    call 0x89A4D0          ; write tag byte
...
0x0089A843: 8b 4e 1c          mov ecx,[esi+0x1c]
0x0089A846: 89 3c 11          mov [ecx+edx],edi      ; write u32 length (edi = 2*charcount)
0x0089A849: 83 46 14 04       add [esi+0x14],4
0x0089A84D: 85 ff             test edi,edi
0x0089A84F: 7e 1c             jle 0x89A86D           ; length 0 -> stop (empty)
...                            ; else memcpy edi bytes UTF-16LE
```
guard@0x89A833[30] = `6A488BCEE894FCFFFF84C0742D8B56148B4E1C893C118346140485FF7E1C`

### clone/copy 0x65ACB0 (idx4) — ยืนยันซ้ำอิสระว่า +0x34 และ +0x18 เป็น wstring
คัดลอก byte flag ที่ +0x14 แล้วคัดลอกสมาชิก wstring สองตัวด้วย wstring-copy helper `[0xC3B460]`:
`lea ecx,[esi+0x34]` … `call [0xC3B460]` (field#1) และ `lea ecx,[esi+0x18]` … `call [0xC3B460]` (field#2). ทั้งคู่คือ wstring object จริง

### แมป payload ↔ object (จาก 0x65AD40 ตอน read, bl=0)
payload `48 <u32 A> | 48 <u32 textlen> <text>` (A=0 ทุก sample GT-009):
- **field#1** = tag 0x48 + u32 A → อ่านเข้า **object+0x34** = wstring (A=0 → wstring ว่าง)
- **field#2** = tag 0x48 + u32 textlen + text → อ่านเข้า **object+0x18** = wstring (ข้อความ)

**verdict Q1 = reading (a) — GRADE A (instruction-level).** field#1 ถูก consume ด้วย tag-0x48 wstring codec ตัวเดียวกับ field#2 และตัวเดียวกับ name codec ที่ NAME001 พิสูจน์ Grade A มาแล้ว. ไม่มี code path ใดอ่าน field#1 เป็น bare u32 scalar. ดังนั้นดีไซน์ของ CHAT-ECHO-002 (แต่งชื่อผู้พูดใส่ wstring#1) **ถูกต้องเชิงโครงสร้าง** — server ที่เติมชื่อลง wstring#1 (tag 0x48 + len จริง + UTF-16) จะถูก parse ด้วย helper เดียวกับข้อความ

หมายเหตุ semantic: static พิสูจน์ว่า field#1 = "wstring ตัวแรกของ message object (+0x34)" ระดับ A; การว่า +0x34 = "ชื่อผู้พูดที่ render หน้า `:`" ยังเป็น **inference (Grade C)** — ดู Q2/nonclaims

---

## Q2 — `[ทั่วไป]` (id 540) เลือกจาก vital id หรือจาก field ใน payload?  **ตอบ: ไม่ใช่ payload-field (A); เป็น identity/type-driven (B)**

### หลักฐานเชิงลบ (ชี้ขาด, GRADE A): payload 0xAC52 ไม่มี field ช่องเลย
(de)serialize 0x65AD40 อ่าน **แค่ 2 wstring** (name +0x34, text +0x18) แล้ว `ret 8` — **ไม่มีการอ่าน scalar/enum/channel byte จาก payload เลย**. clone 0x65ACB0 ก็คัดลอกแค่ byte+0x14 กับ wstring สองตัว. **บน wire ของ 0xAC52 ไม่มีไบต์ใดที่ทำหน้าที่เลือก tag ได้** → `[ทั่วไป]` เป็น payload-field-driven **ไม่ได้** (ปิดได้)

### ไม่มี hardcoded switch เทียบ 0xAC52/0x556C
`.text` ไม่มี immediate 4-byte `0xAC52` หรือ `0x556C` เลย (word-match 2 จุดของ 0xAC52 = ไบต์บังเอิญ `52`=push edx ทับ rel32 ของ call ที่ 0x50465A/0x58465A — ไม่ใช่ immediate). dispatch ใช้ **id ที่ resolve ตอน runtime ผ่าน factory/virtual getter** (idx10) ไม่ใช่ compare ค่าคงที่ → สอดคล้อง prototype-factory keyed by id

### หลักฐานเชิงบวก (GRADE B): tag เลือกจาก C++ TYPE ของ message object
สตริง id 540 (`0x21C`) ถูกโหลดเป็น immediate จริง 3 จุด: `0x5440BB` (legend composer), และ **สองจุดใน render `0x63F9B0`** (`0x6405F6`, `0x6408BA`). (`mov ebp,0x21c`@0x4F402E = misalignment artifact, ทิ้ง)

`0x63F9B0` รับ message object แล้วทำ **RTTI-style checked downcast ต่อเนื่อง** (`0x639F70/0x639FA0/0x639FD0/0x63A000` — แต่ละตัว: เรียก type-getter ของ object แล้วเทียบ type-descriptor ผ่าน `0x88F2B0`; type descriptors อยู่ที่ global `0x1083F84/9C/A8/B4`, `0x1084044`). เมื่อ match subtype แล้วเลือก tag ด้วย byte field:

จุดเลือก tag (id 539 `0x21B` vs 540 `0x21C`) สองแห่ง คุมด้วย field ของ object:
```
0x006405E7: 38 58 44          cmp [eax+0x44], bl     ; bl=0
0x006405EA: 75 0a             jne 0x6405F6
0x006405EC: 68 1b 02 00 00    push 0x21B             ; id 539
0x006405F1: e9 ...            jmp resolver
0x006405F6: 68 1c 02 00 00    push 0x21C             ; id 540 [ทั่วไป]
```
guard@0x6405E7[21] = `385844750A681B020000E939F4FFFF681C020000E9`
```
0x006408A5: 83 7e 34 00       cmp dword [esi+0x34], 0
0x006408A9: 75 0f             jne 0x6408BA
0x006408AB: 68 1b 02 00 00    push 0x21B ; 539  -> call 0x5CBC00 (append to chat list [0x1093198]+0x728)
0x006408BA: 68 1c 02 00 00    push 0x21C ; 540  -> call 0x5CBC00
```
guard@0x6408A5[27] = `837E3400750F681B020000E84BB3F8FFE948F5FFFF681C020000E8`

tag ถูกเลือกจาก **type ของ message object (dynamic_cast) + byte subtype (+0x44 / field +0x34)** ซึ่งถูกตั้งตอน *สร้าง* object จาก vital 0xAC52 (identity) — **ไม่ใช่จาก payload** (payload ไม่มี field นั้น). สตริง `[ทั่วไป]` เองคือ client resource id 540 (ยืนยันแล้วใน ECHO002)

**verdict Q2:** payload-field-driven = **ปฏิเสธ GRADE A** (payload ไม่มี channel field เลย) · identity/vital-id-driven = **GRADE B** — channel แยกบน wire ด้วย vital id ล้วน และ render เลือก tag จาก C++ type + subtype byte ที่มาจากการ instantiate ตาม vital identity

**ช่องว่าง (ทำไมไม่ใช่ A เต็มสำหรับด้านบวก):** ผมไม่ได้ตาม trace เส้นทาง "received 0xAC52 vital object (layout +0x18/+0x34) → display/log message object (layout +0x28/+0x30/+0x44 ที่ 0x63F9B0 ใช้)" ถึงคำสั่งเดียวที่ SET type/+0x44 = 540-path. layout สองแบบต่างกัน มี transform คั่นที่ยังไม่ถูก disassemble. ที่แน่คือ: (i) payload ไม่มี field เลือก tag, (ii) การเลือก tag ในตัว render เป็น type/field-driven ไม่ใช่ wire-driven

---

## โบนัส — Whisper (0x556C)
- Whisper **แชร์ (de)serialize 0x65AD40 และ clone 0x65ACB0 กับ LocalTalk** → wire shape เดียวกัน (`48 <wstr#1> 48 <wstr#2>`) ต่างแค่ vital id 0x556C (getter 0x6582B0, global [0x1084464]) กับ memory pool. ดังนั้น field#1 ของ Whisper ก็เป็น tag-0x48 wstring เช่นกัน (Grade A โดยอนุมานจาก code ที่แชร์)
- format `$V1` ของ whisper (id 452/453) — พบ template/token processor ที่ `0x545D80` (เทียบ token ผ่าน `call ebp`, push id 545 `[ $V1 ]`, push id 451 `: `, lookup ผ่าน `0x482400`) = เส้นทาง parameterized-format แยกจาก render หลัก. ไม่ได้เจาะลึกรอบนี้
- **ยังไม่มี wire golden ของ Whisper** (corpus negative เดิมของ ECHO002 ยังคงอยู่) — response shape เป็น designed hypothesis

## helper อ้างอิง (สำหรับ chief re-verify)
- `0x89A880` wstring reader (verify tag 0x48 → u32 len → UTF-16LE) · `0x89A810` wstring writer · `0x89A550` tag byte checker (err 0xE0000012) · `0x89A4D0` tag byte writer
- `0x8923B0` / `0x482400` string-resource lookup (id→string) · `0x542760` / `0x5CBC00` / `0x5CBD00` append colored text run · `[0xC3B460]` wstring copy/assign · `0x88F2B0` type/registry equality
- render/tag resolver: `0x63F9B0` (entry, SEH prologue) ครอบ 0x6405F6 และ 0x6408BA · downcast helpers `0x639F70/0x639FA0/0x639FD0/0x63A000`
- legend/multi-tag composer (ไม่ใช่ per-message): `0x5437xx–0x5446xx` (push 529/530/538/539/541/544/545/451 ต่อเนื่อง append) — distractor

## ดัชนีหลักฐาน (fact → VA / file-offset / guard)
| fact | VA | file off | guard |
|---|---|---|---|
| ชื่อ `Channel_LocalTalkMessageVital` (.rdata) | 0xF37984 | 0xB35D84 | `4368616E6E656C5F4C6F63616C54616C6B4D657373616765566974616C` |
| register LocalTalk id → [0x1084458] | 0xBF72D0 | 0x7F66D0 | `688479F300E8A64DCAFF8BC8E81F4ACAFF66A358440801C3` |
| get-id getter LocalTalk (id 0xAC52) | 0x6580B0 | 0x2574B0 | `66A158440801C3` |
| get-id getter Whisper (id 0x556C) | 0x6582B0 | 0x2576B0 | `66A164440801C3` |
| (de)serialize visitor (แชร์ LT+WH) | 0x65AD40 | 0x25A140 | ดู guard[65] ด้านบน |
| clone/copy (2 wstring +0x34/+0x18) | 0x65ACB0 | 0x25A0B0 | (ดูข้อความ Q1) |
| wstring reader (tag0x48→u32len→UTF16) | 0x89A880 | 0x499C80 | ดู guard[80] ด้านบน |
| tag checker (cmp ==0x48) | 0x89A5B7 | 0x4999B7 | `8B511C538A5C24543A1C105B742B8B44` |
| wstring writer (emit 0x48 + u32len) | 0x89A833 | 0x499C33 | `6A488BCEE894FCFFFF84C0742D8B56148B4E1C893C118346140485FF7E1C` |
| render tag 539/540 select #1 | 0x6405E7 | 0x23F9E7 | `385844750A681B020000E939F4FFFF681C020000E9` |
| render tag 539/540 select #2 | 0x6408A5 | 0x23FCA5 | `837E3400750F681B020000E84BB3F8FFE948F5FFFF681C020000E8` |
| vital-id hash ตรวจ | — | — | H("...LocalTalkMessageVital")=0xAC52, H("...WhisperVital")=0x556C |

## Nonclaims (static ไม่พิสูจน์)
1. **runtime/render pixel** — ไม่ได้รัน client; ไม่ยืนยันว่าพอ server เติมชื่อ wstring#1 แล้วจะเห็น `[ทั่วไป] <ชื่อ> : <text>` บนจอ (ต้อง attended A/B)
2. **semantic "+0x34 = ชื่อผู้พูดที่โชว์หน้า `:`"** = inference (Grade C) — พิสูจน์แค่ว่า +0x34 เป็น wstring ตัวแรกของ message object; transform received-vital → display object ยังไม่ trace
3. **positive mapping "0xAC52 → id 540" ถึงคำสั่งเดียว** = ยังมี gap (Grade B) — ที่ปิดได้คือ payload ไม่มี field เลือก tag
4. server behavior / ความยาว-charset จริง / Whisper wire shape — ไม่มี golden (corpus negative เดิม)
5. parity กับ `GameClient.bin` (โปรไฟล์ non-local) — ไม่ได้ re-verify รอบนี้ (อ้าง NAME001 ว่า relevant code เหมือนกัน)

## Verdict สรุป
- **Q1 = reading (a): field#1 เป็น length-prefixed tag-0x48 wstring, ไม่ใช่ bare u32 — GRADE A.** CHAT-ECHO-002 ออกแบบถูกเชิงโครงสร้าง
- **Q2 = ไม่ใช่ payload-field-driven (GRADE A, ปิดได้: payload ไม่มี channel field); เป็น identity/vital-id-driven (GRADE B).** `[ทั่วไป]` = client resource id 540 เลือกจาก type/subtype ของ message object ที่ตั้งตาม vital identity
