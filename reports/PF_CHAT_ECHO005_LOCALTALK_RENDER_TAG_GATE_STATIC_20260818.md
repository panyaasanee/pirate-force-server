# PF CHAT-ECHO-005 — LocalTalk (0xAC52) render tag-select: pin gate ของ 539/540 + type-node registry map (2026-08-18, chief รอบ 55)

งานวิจัยหลักฐานล้วน (static disassembly ต่อยอด ECHO-004) — **ไม่แก้โค้ด/ไม่แตะ binary/ไม่เปิด UI/ไม่แตะ DB**
เป้า: หนุน Q2 จาก B→A ตาม next-item รอบ 54 = trace render resolver `0x63F9B0` ถึงคำสั่งที่ set channel id 540

> **ผลสรุปล่วงหน้า: เกรดของ Q2 ไม่เปลี่ยน** (negative A / positive B เดิม) — รอบนี้**บีบช่องว่างให้แคบลงและระบุ next hop เป๊ะ**
> พร้อมเหตุผลว่าทำไม single-SET ปิด static ไม่ได้ในรอบนี้ (parent-chain ของ type registry ถูกสร้างตอน runtime ไม่มีในไฟล์อิมเมจ)
> — ไม่ claim เกินหลักฐาน, report-only, ยึด precedent `9f5e6a2`/`5789f13` (digest untouched)

## Binary ที่วิเคราะห์
- `GameClient/GameClient.local.bin` — PE32 x86, ImageBase `0x400000`, 14,759,424 B
- SHA-256 = `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` (โปรไฟล์เดียวกับ ECHO-004/NAME001)
- Sections: `.text` VA=0x00401000 raw@0x400 · `.rdata` VA=0x00C3B000 raw@0x839400 · `.data` VA=0x0101A000 raw@0xC17800
- ทุก VA/offset/guard byte reproducible ผ่าน capstone (CS_MODE_32) จาก binary นี้เท่านั้น

---

## สิ่งที่ ECHO-004 เปิดค้าง (recap)
- Q2 **negative = GRADE A**: payload 0xAC52 ไม่มี field เลือก tag (de/serialize `0x65AD40` อ่านแค่ 2 wstring)
- Q2 **positive = GRADE B**: `[ทั่วไป]`(540) เลือกจาก C++ type + byte subtype ของ message object — แต่**ยังไม่ trace ถึงคำสั่งเดียวที่ SET** และ "transform received-vital(+0x18/+0x34) → display object(+0x28/+0x30/+0x44)" ยังไม่ disassemble

---

## รอบ 55 — หลักฐานใหม่ (byte-exact)

### 1. Pin gate ของ render tag-select #1 (0x6405E7) — เจาะจงกว่าเดิม
ECHO-004 บันทึกจุดเลือก `cmp [eax+0x44],bl` (539/540) แต่ไม่ได้ระบุว่ามาถึงจุดนั้นได้อย่างไร. รอบนี้ disassemble ต้นทาง `0x64059C..0x6405FB` พบว่า **จุดนี้ถูก gate ด้วย downcast ตัวที่สาม (`0x639FD0`) สำเร็จ + byte `+0x45 == 0`**:

```
0x0064059C: e82f9affff       call 0x639FD0            ; downcast #3 -> node 0x1083FA8
0x006405A1: 83c404           add esp,4
0x006405A5: 85c0             test eax,eax
0x006405A7: 7457             je  0x640600             ; ไม่ match -> ไปสาขาอื่น (tag-select #2)
0x006405A9: e8229affff       call 0x639FD0            ; re-narrow -> eax = pointer ชนิดนั้น
0x006405AE: 0fb64845         movzx ecx,byte [eax+0x45]
0x006405B5: 2bcb             sub ecx,ebx              ; ebx=0
0x006405B7: 742e             je  0x6405E7             ; +0x45==0 -> ไปเลือก 539/540 ด้วย +0x44
0x006405B9: 83e901 740c ...  ; +0x45==1 -> id 0x1F7 ; +0x45==2 -> append run ; อื่น -> default
0x006405E7: 385844           cmp byte [eax+0x44],bl   ; +0x44==0 -> 539(0x21B) ; !=0 -> 540(0x21C)[ทั่วไป]
```
สรุปเงื่อนไขเต็ม: **object เป็นชนิดที่ is-a `node 0x1083FA8` ∧ `+0x45==0` ∧ `+0x44!=0` ⟹ id 540 `[ทั่วไป]`**. `+0x45` คือ sub-selector ชั้นบน, `+0x44` คือ channel discriminator ชั้นล่าง — ทั้งคู่เป็น field ของ message object ชนิดเดียวกัน ไม่ใช่ payload (ตอกย้ำ negative A)

### 2. Downcast helper → type-thunk → type-node (ครบ 5 สาย)
แต่ละ helper เรียก object's vtable[0] (`call [eax]`) เอา type node ของ object แล้วเทียบกับ node คาดหวังจาก thunk ผ่าน registry equality `0x88F2B0`:

| resolver downcast | type thunk | expected type node | หมายเหตุ |
|---|---|---|---|
| `0x639F70` | `0x6422D0` | `0x1083FCC` | |
| `0x639FA0` | `0x6422F0` | `0x1083FB4` | |
| **`0x639FD0`** | **`0x642300`** | **`0x1083FA8`** | **gate 539/540 (#1)** |
| `0x63A000` | `0x642440` | `0x108402C` | สาขา tag-select #2 (`+0x34`) |
| `0x642AA0` (บนสุด) | — | `0x1084044` | pre-filter |

thunk เป็นแค่ `mov eax,<node>; ret` (เช่น `0x642300 = B8A83F0801 C3`)

### 3. Type-node เป็น registry ที่สร้างตอน runtime (custom RTTI) — ตอกย้ำ dispatch = id/registry-keyed
node `0x1083FA8` และพี่น้อง (`0x1083F24/3C/54/84/90/9C/FCC`, `0x108402C`, `0x1084044`) ถูก**สร้างตอน startup** ด้วย static initializer ต่อเนื่องที่ `0xBF6040..0xBF6115` (registry-init `0x88F2E0`, descriptor ร่วม `0x10945D0`, key ต่อชนิดผ่าน `call [0xC3B7AC]` ด้วย ecx=`0x102053C/56C/5A0…`) และตั้ง vftable `0xF36384`, register dtor ที่ `0xC2FF50..0xC2FFBx`:
```
0x00BF60A0: 68d0450901       push 0x10945D0
0x00BF60A5: b96c050201       mov  ecx,0x102056C          ; key ของชนิดนี้
0x00BF60AA: ff15acb7c300     call [0xC3B7AC]             ; registry lookup/insert
0x00BF60B0: 50 6850400801    push eax; push 0x1084050
0x00BF60B6: b9a83f0801       mov  ecx,0x1083FA8          ; type node ที่กำลัง init
0x00BF60BB: e82092c9ff       call 0x88F2E0
0x00BF60C5: c705 a83f0801 8463f300  mov [0x1083FA8],0xF36384   ; vftable ของ type node
```
key เป็น**ค่า hash ไม่ใช่ plaintext ชื่อคลาส** (ไม่มีสตริงชื่อคลาสที่ site) → ตรงกับข้อสรุป ECHO-004 ว่า dispatch ใช้ id/registry ไม่ใช่ hardcoded switch เทียบ `0xAC52`

### 4. คลาส message ตัวจริง (instantiated) = vtable ที่ `0xF363xx..0xF365xx`
สแกน `.rdata` หา slot get-type ที่ชี้เข้าบล็อก thunk `[0x6422D0,0x642460)` เจอ vtable ตัวจริง 6 ตัว:

| vtable get-type slot (.rdata) | thunk | node ที่ return |
|---|---|---|
| `0xF36388` | `0x642440` | `0x108402C` |
| `0xF3640C` | `0x642320` | `0x1083F84` |
| `0xF36490` | `0x642360` | `0x1083F3C` |
| `0xF364E8` | `0x642370` | `0x1083F24` |
| `0xF36598` | `0x642350` | `0x1083F54` |

**สังเกตสำคัญ:** ไม่มี vtable ตัวไหน get-type = node `0x1083FA8` โดยตรง และค่า `0x1083FA8` ถูกผลิตในโค้ดแค่ 3 จุด (thunk `0x642300`, static init `0xBF60B7/C7`, dtor-register `0xC2FF81`) — object จึง**ไม่ได้ฝัง `0x1083FA8` เป็น immediate**. แปลว่า `0x1083FA8` เป็น **base type node ที่ไม่ถูก instantiate ตรง ๆ**; คลาสตัวจริง (เช่น node `0x1083F84`) match `0x1083FA8` ผ่านการเดิน parent-chain ใน `0x88F2B0` (is-a). `+0x44/+0x45` จึงเป็น field ของ **base "channel message" ที่หลาย channel ใช้ร่วม**

---

## ทำไม Q2 ยังเป็น B (ไม่ดันเป็น A รอบนี้)
เพื่อจะปิด single-SET ต้อง: (a) หา vtable base ของคลาสตัวจริง → constructor → คำสั่งที่เขียน `+0x44/+0x45` → (b) หา caller ที่แปลง received 0xAC52 vital → display object และพิสูจน์ว่า `+0x44` ถูกตั้งจาก **vital identity** ไม่ใช่ payload. อุปสรรคเชิงหลักการ: **is-a parent link ของ type node (`0x1083F84`→…→`0x1083FA8`) ถูกเซ็ตตอน runtime โดย `call [0xC3B7AC]` — ไฟล์อิมเมจมีค่า uninitialized** จึง**ยืนยัน static ไม่ได้ว่า node ของคลาสตัวจริงเดินขึ้นถึง `0x1083FA8`**. การดัน B→A ที่ sound ต้องใช้อย่างใดอย่างหนึ่ง: (i) disasm constructor + resolve vtable base ต่ออีก 2-3 hop (งาน static รอบหน้า), หรือ (ii) observation ตอน attended (runtime) — **ไม่ควร claim จากการอนุมาน parent-chain**

## next hop ที่ระบุแล้ว (สำหรับรอบหน้า/attended)
1. หา COL/vtable base ของ vtable `0xF3640C`-region → xref immediate ของ base → constructor
2. ในนั้นหา `mov byte [obj+0x44], <imm>` / `[obj+0x45]` → คือ SET จริง
3. ยืนยัน caller คือ receive/notify ของ LocalTalk vital (สายจาก 0xBF72D0 registration) — ปิด transform received→display
4. ทาง attended: GT-012 สังเกต `[ทั่วไป]` render ตรงกับ +0x44 ที่ตั้งจาก identity

---

## ดัชนีหลักฐาน (VA / .text off = VA−0x400C00 / guard)
| fact | VA | off | guard |
|---|---|---|---|
| +0x45 preselect + downcast#3 | 0x6405A1 | 0x23F9A1 | `83C4045685C07457E8229AFFFF0FB6484583C4042BCB742E` |
| downcast helper #3 (→node A8) | 0x639FD0 | 0x2393D0 | `568B74240885F674228B068B108BCEFFD250E81983000050` |
| type thunk → node 0x1083FA8 | 0x642300 | 0x241700 | `B8A83F0801C3` |
| static init node 0x1083FA8 | 0xBF60A0 | 0x7F54A0 | `68D0450901B96C050201FF15ACB7C300506850400801B9A8` |
| dtor-register node 0x1083FA8 | 0xC2FF80 | 0x82F380 | `B9A83F0801E966F2C5FF` |
| 539/540 select (+0x44) | 0x6405E7 | 0x23F9E7 | `385844750A681B020000E939F4FFFF681C020000E9` |
| vtable get-type→node 0x1083F84 (.rdata off=VA−0x401C00) | 0xF3640C | 0xB3480C | `20236400` |

## Nonclaims
1. ไม่ได้ยืนยัน static ว่า node คลาสตัวจริงเดิน parent-chain ถึง `0x1083FA8` (runtime-built) — จึงไม่ upgrade positive เป็น A
2. ไม่ได้ trace ถึง constructor/คำสั่ง SET `+0x44/+0x45` เดียว (next hop)
3. ไม่ได้รัน client — ไม่ยืนยัน render pixel; ความหมาย `+0x45` sub-selector (0/1/2) เป็น inference จาก id ปลายทาง
4. parity กับ `GameClient.bin` (non-local) ไม่ได้ re-verify รอบนี้

## Verdict
- **ไม่เปลี่ยนเกรด Q2**: negative (payload ไม่มี channel field) = **A** เดิม · positive (single-SET mapping 0xAC52→540) = **B** เดิม
- เพิ่มค่า: pin gate 539/540 = downcast `0x639FD0`→node `0x1083FA8` + `+0x45==0`; แผน type-node registry family + คลาสตัวจริง (vtable `0xF363xx`); ระบุ next hop + เหตุผลที่ปิด static ไม่ได้ตอนนี้ — ตอกย้ำ Q2 negative A (type/registry-driven) อีกชั้น
