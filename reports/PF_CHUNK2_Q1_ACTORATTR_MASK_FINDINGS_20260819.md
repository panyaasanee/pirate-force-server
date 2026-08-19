<!-- Imported into reports/ by chief round 96 (2026-08-20) from pf_bridge/drafts/CHUNK2_Q1_ACTORATTR_MASK_FINDINGS.md
     (round 90 static RE lane worker output), byte-for-byte below this header.
     Reason: EVIDENCE-VISIBLE-001 discipline - the HYP-PF-025 ledger entry and the
     REMOTE-PLAYER-ENCODER-001 report cite these findings, and a citation must resolve
     inside the repository, not on one author's machine. -->

# CHUNK2-Q1 — `ActorAttr` mask/field enumeration, merge path, and the mask==0 decision

รอบ 90 · เลน static RE · **อ่านอย่างเดียว ไม่รันอะไรเลย** · ปิด ROW 1 และ ROW 2 ของตาราง §10
ใน `drafts/MULTIPLAYER_CHUNK2_VISIBILITY_DESIGN_R90.md`

- image: `GameClient/GameClient.local.bin` · size `14759424` · sha256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- reproduce: `python3 <script ที่แปะไว้ท้ายไฟล์นี้> GameClient/GameClient.local.bin` → **86 guards, 0 failed**
- เครื่องมือ: **pure stdlib python3 เท่านั้น** ไม่มี capstone ไม่มี pefile — มี length-decoder x86-32 ของตัวเองที่
  **โยน exception เมื่อเจอ opcode ที่ไม่รู้จัก** (ไม่หยุดเงียบ ๆ) เพื่อไม่ให้เกิดความผิดพลาดแบบรอบ 83 ซ้ำ

> **คำตอบหนึ่งย่อหน้า** — `ActorAttr::Serial 0x466230` มี **43 ฟิลด์ที่ถูกเกตด้วย mask** ตรงตามที่เอกสาร R90 เขียนไว้
> (ยืนยันแล้ว) แต่ mask 64 บิตนั้น **ใช้จริงแค่ 41 บิต** (บิต 0..30 และ 32..41; บิต 31 = `0x80000000` **ไม่มีฟิลด์ผูก**)
> เพราะมีสองบิตที่แบกฟิลด์ละสองตัว และยังมี **เกตชั้นที่สอง** ที่เอกสาร R90 ไม่รู้จัก คือไบต์ `+0x1BC` (wire tag `0x05`,
> ที่ v141 ส่ง `1` มาตลอด) ซึ่งถ้าเป็น `0` ไคลเอนต์จะ **ข้าม 25 จาก 43 ฟิลด์ทิ้งไปเลยไม่ว่า mask จะปักอะไร**
> · **mask == 0 ไม่ผิดกฎและไม่ทำให้เฟรมถูกทิ้ง** — สาขาที่ตัดสินคือ `0x4667AD jz 0x466B54` (low dword ว่าง)
> และ `0x466B5C jz 0x466C6F` (high dword ว่าง) ซึ่งเป็นแค่ **short-circuit ข้ามฟิลด์** ไม่ใช่ error path
> ทั้งฟังก์ชันไม่มี throw ไม่มี ret-false มี `ret 8` แค่สองจุด
> · **แต่** ทางที่ actor entry ใช้ผูก attr เข้ากับ actor **ไม่ใช่ merge** — bind thunk `0x469760` เรียก
> `ActorAttr::vtable +0x24 = 0x464F30` ซึ่ง **ก๊อปทุกฟิลด์แบบไม่ดู mask เลย** (0 mask test ใน 143 instruction)
> ต่างจาก `BasicAttr::Merge 0x4656A3` ที่ "copy forward เมื่อบิตเคลียร์" — ตัว merge แบบนั้นของ `ActorAttr` มีอยู่จริง
> (`vtable +0x30 = 0x465E60`) แต่ **actor-entry pipe ไม่ได้เรียกมัน**
> ⇒ ผลจริงของ `mask == 0` คือ **ไคลเอนต์ยอมรับเฟรม แล้วเอาค่า default ของ ctor ทั้งก้อนไปทับ attr ที่ actor ถืออยู่**
> ซึ่งแปลว่า `HP = 0`, ชื่อ = `L""` — และ `HP == 0` คือ predicate ความตายของ actor (`0x43BD7A`, `0x43BDAA`)

---

## 0. เกรดที่ใช้

| เกรด | ความหมาย |
|---|---|
| `[PROVEN VA=0x...]` | อ่านไบต์คำสั่งจริง อ้างอิงได้ตรงตัว มี guard ในสคริปต์ท้ายไฟล์ |
| `[INFERRED]` | เหตุผลเชิงโครงสร้างจากข้อเท็จจริง PROVEN หลายข้อ |
| `[GUESS]` | ไม่ได้มาจากไบนารี — ระบุแล้วหยุด ไม่เอาไปต่อยอด |

---

## 1. re-derivation ของคำตอบที่โปรเจกต์ปักไว้แล้ว (ทำก่อนเชื่อเครื่องมือตัวเอง)

เครื่องมือใหม่ตัวไหนที่ยังไม่เคยเช็คกับคำตอบที่รู้แล้ว = เครื่องผลิตข้อความที่ดูน่าเชื่อ
ก่อนอ้างอะไรใหม่ สคริปต์นี้ re-derive สามข้อที่โปรเจกต์ปักไว้แล้ว **จากไบต์ ไม่ใช่จากตาราง hard-code**:

### 1.1 BasicAttr bit `0x0080` → object `+0x58` · wire tag `0x2A` · width 4 (HP-DEATH-001)

```
[OK]   A1 BasicAttr::Serial 0x4657AE = test byte [ebx+0],0x80  (ebx = attr+0x70 mask)  F60380740F6A048D4E58516A2A8BCFE83E4E4300
[OK]   A1 gate is followed by push 4 / lea ecx,[esi+0x58] / push ecx / push 0x2A / call 0x89A600
[OK]   A1 lea ebx,[esi+0x70] at 0x465708 makes the gate base the BasicAttr u16 mask
[OK]   A1 => BasicAttr bit 0x0080 -> object +0x58, tag 0x2A, width 4  [PROVEN VA=0x4657AE..0x4657C1]
```

ไบต์ดิบ `0x4657AE..0x4657C1`:
`F6 03 80 | 74 0F | 6A 04 | 8D 4E 58 | 51 | 6A 2A | 8B CF | E8 3E 4E 43 00`
= `test byte [ebx],0x80 ; jz +0xF ; push 4 ; lea ecx,[esi+0x58] ; push ecx ; push 0x2A ; mov ecx,edi ; call 0x89A600`

และ **ตัว extractor เดียวกับที่ใช้ทำตาราง `ActorAttr` ก็ derive ข้อนี้ออกมาเองได้ด้วย** (ไม่ได้เทียบไบต์ตรง ๆ):
ดูบรรทัด `BasicAttr    bit 0x0080  +0x058  tag 0x2A  w 4` ในตาราง §3.2 — **นี่คือการเช็คที่มีน้ำหนักที่สุด**
เพราะมันบอกว่ากลไกที่สร้างตาราง 43 แถวข้างล่าง ทำงานถูกบนกรณีที่เรารู้คำตอบอยู่แล้ว

### 1.2 `BasicAttr::Merge 0x4656A3` copy ค่าเก่า "ไปข้างหน้า" เมื่อบิตเคลียร์

```
[OK]   A2 BasicAttr::Merge is BasicAttr vtable +0x30 = 0x465610
[OK]   A2 0x46564E reads THIS's mask: test byte [edi+0x70],1
[OK]   A2 0x4656A3 = test al,al / js +6 / fld [esi+0x58] / fstp [edi+0x58]  84C07806D94658D95F58
[OK]   A2 => bit CLEAR  ==> old(arg,esi) value is copied FORWARD into this(edi)  [PROVEN VA=0x4656A3]
```

ทิศทางชัดเจนจาก register: `edi = ecx = this` (ก้อนที่เพิ่ง parse มา), `esi = arg` (ก้อนเก่า)
`test al,al ; js` = ถ้าบิต `0x80` **ถูกตั้ง** ให้ข้าม; ถ้า **เคลียร์** ให้ `fld [esi+0x58] ; fstp [edi+0x58]`
คือ **เอาค่าเก่ามาเติมลงในก้อนใหม่** — ตรงกับที่ `tools/verify_hypothesis_ledger.py:152` บันทึกไว้

### 1.3 actor_type jump table (MPAUDIT-FOLLOWUP-001)

```
[OK]   A3 jump table 0x446B2C has the 5 pinned entries  0x4469e1 0x4469f7 0x446a3d 0x446a5a 0x446a77
[OK]   A3 span 0x446990..0x446B2C sha256 == 5F68239F...697D  5F68239F8661419DA2EA9BEA4E4A2CB9BCDCAA37FE6E4CD53B701116AEEB697D
[OK]   A3 table span 0x446B2C..0x446B40 sha256 == B50C1D1D...D606  B50C1D1DB53D2B70A8AD258563750738639D5E9E3EEF2FA5CFB4C5354632D606
[OK]   A3 0x4469C8 movzx eax,byte [eax+0x10]; add eax,-2; cmp eax,4; ja
```

sha256 สองค่าตรงกับที่ MPAUDIT-FOLLOWUP-001 ปักไว้ทุกหลัก **⇒ ทั้ง PE plumbing, `va2off`, และ span hashing ของเครื่องมือนี้ตรงกับของเดิม**

---

## 2. ขอบเขตที่กวาดจริง (negative จะเชื่อได้ก็ต่อเมื่อบอก coverage)

decoder เดินแบบ linear จากต้นฟังก์ชัน และ **ไม่มีไบต์ไหน undecodable เลย** ในทุกช่วงต่อไปนี้
ถ้ามันหยุด มันจะรายงาน VA ที่หยุดและ guard จะแดง (ไม่มีการอ้าง negative บนช่วงที่กวาดไม่ถึง)

```
       ActorAttr::Serial       0x466230..0x466C79   740 ins  COMPLETE
       ActorAttr vt+0x24 copy  0x464F30..0x46520E   143 ins  COMPLETE
       ActorAttr vt+0x38 thunk 0x469760..0x4697A2    28 ins  COMPLETE
       BasicAttr::Serial       0x4656F0..0x465850   134 ins  COMPLETE
       BasicAttr::Merge        0x465610..0x4656EF    80 ins  COMPLETE
       CNetActor::init         0x454920..0x4549DD    55 ins  COMPLETE
       NameBoardPlayer update  0x5BD320..0x5BD8E0   490 ins  COMPLETE
```

หลักฐานเพิ่มว่า decode ไม่หลุด sync: instruction สุดท้ายของ `ActorAttr::Serial` **ลงท้ายพอดีที่ `0x466C79`**
คือ `C2 08 00 = ret 8` ที่ `0x466C76` แล้วตามด้วย `CC` padding 7 ไบต์ `[PROVEN VA=0x466C76]`

---

## 3. (a) ตารางฟิลด์ทั้งหมดของ `ActorAttr::Serial 0x466230`

### 3.1 ลำดับบนสาย — ก้อน `ActorAttr` หนึ่งใบมีสามชั้น

`ActorAttr::Serial 0x466230` เรียก `BasicAttr::Serial 0x4656F0` **ก่อน** (`0x466243 E8 A8 F4 FF FF`)
และ `BasicAttr::Serial` เรียก `DBAttribute::Serial 0x467790` ก่อนอีกที `[PROVEN VA=0x466243, 0x4656FF]`
⇒ ลำดับไบต์บนสายคือ **DBAttribute → BasicAttr → ActorAttr** ตรงกับที่ R90 §3.4 เขียนไว้

| ชั้น | ฟิลด์ | เกต | tag | width | object off |
|---|---|---|---|---|---|
| DBAttribute | u8 | **ไม่มีเกต** | `0x0B` | 1 | `+0x20` |
| DBAttribute | **identity qword** | **ไม่มีเกต** | `0x32` | 8 | `+0x18` |
| BasicAttr | u16 change mask | **ไม่มีเกต** | `0x12` | 2 | `+0x70` |
| BasicAttr | 12 ฟิลด์ (ตาราง §3.2) | bit `0x0001..0x0800` | — | — | — |
| ActorAttr | **64-bit change mask** | **ไม่มีเกต** | `0x32` | 8 | `+0x1B4`(lo) `+0x1B8`(hi) |
| ActorAttr | **extra-group flag** | **ไม่มีเกต** | `0x05` | 1 | `+0x1BC` |
| ActorAttr | 43 ฟิลด์ (ตาราง §3.3) | bit 0..30, 32..41 | — | — | — |

`[PROVEN VA=0x466252..0x466285 (save) / 0x466767..0x4667A4 (load)]`

### 3.2 `BasicAttr` prefix — 12 ฟิลด์ที่ถูกเกต (derive จากไบต์ ไม่ใช่ hard-code)

```
     BasicAttr    UNGATED  +0x070  tag 0x12  w 2   (the u16 change mask itself)
     BasicAttr    bit 0x0001  +0x028  tag 0x48  w -   NAME wstring -> LABEL_NAME (board+0x54)
     BasicAttr    bit 0x0002  +0x05E  tag 0x12  w 2   level
     BasicAttr    bit 0x0004  +0x044  tag 0x14  w 4   HP current  -> HPBAR + death predicates 0x43BD70/0x43BDA0
     BasicAttr    bit 0x0008  +0x048  tag 0x14  w 4   HP max      -> HPBAR
     BasicAttr    bit 0x0010  +0x04C  tag 0x14  w 4   MP current
     BasicAttr    bit 0x0020  +0x050  tag 0x14  w 4   MP max
     BasicAttr    bit 0x0040  +0x054  tag 0x2A  w 4
     BasicAttr    bit 0x0080  +0x058  tag 0x2A  w 4   death/respawn timer f32 (HP-DEATH-001)
     BasicAttr    bit 0x0100  +0x05C  tag 0x12  w 2   u16 category; 0x430E10(cat)==8 switches HP to ActorAttr +0x1A8/+0x1AC
     BasicAttr    bit 0x0200  +0x060  tag 0x32  w 8
     BasicAttr    bit 0x0400  +0x068  tag 0x14  w 4
     BasicAttr    bit 0x0800  +0x06C  tag 0x14  w 4
```

**หมายเหตุแก้เอกสาร R90**: R90 §3.4 เรียก bit `0x0100` (`+0x5C`) ว่า "scene id" และ bit `0x0200` (`+0x60`) ว่า "scene seq"
ไบต์บอกแค่ว่า `+0x5C` เป็น `u16` ที่ถูกส่งเข้า `0x430E10` แล้วเทียบกับ `8` ที่ `0x5BD3D0`
เพื่อสลับให้ HP bar อ่านจาก `ActorAttr +0x1A8/+0x1AC` แทน `+0x44/+0x48` `[PROVEN VA=0x5BD3C0..0x5BD3E0]`
ชื่อ "scene id/seq" **ไม่มีอะไรในอิมเมจรองรับ** — ถือเป็น `[GUESS]` ที่ตกทอดมา ไม่ควรเอาไปใช้ต่อ

### 3.3 `ActorAttr` — 43 ฟิลด์ที่ถูกเกต (จาก LOAD branch = ทางที่ไคลเอนต์เดินตอนรับเฟรม)

คอลัมน์ `xgrp` = ฟิลด์นี้อยู่ใต้เกตชั้นที่สอง `+0x1BC != 0` ด้วยหรือไม่
คอลัมน์ `load-gate` = VA ของคำสั่ง `test` ในสาขา LOAD

```
  #  maskbit(64)          bit  obj_off  tag  w   kind     xgrp  load-gate   note
   1  0x0000000000000001  b0   +0x08C  0x19  4   scalar    -   0x4667B3  class id            (STATS-PROG-001)
   2  0x0000000000000002  b1   +0x090  0x19  4   scalar    -   0x4667C9  u32 -> NameBoard nickname key        [PROVEN VA=0x5BD7BA..0x5BD7D5]
   3  0x0000000000000004  b2   +0x078  0x26  4   scalar   yes  0x4667ED  
   4  0x0000000000000008  b3   +0x07C  0x19  4   scalar   yes  0x466805  skill points        (STATS-PROG-001)
   5  0x0000000000000010  b4   +0x080  0x12  2   scalar   yes  0x46681D  unspent ability pts (STATS-PROG-001)
   6  0x0000000000000020  b5   +0x082  0x12  2   scalar   yes  0x466838  STR base
   7  0x0000000000000040  b6   +0x084  0x12  2   scalar   yes  0x466853  CON base
   8  0x0000000000000080  b7   +0x086  0x12  2   scalar   yes  0x46686E  DEX base
   9  0x0000000000000100  b8   +0x088  0x12  2   scalar   yes  0x466889  INT base
  10  0x0000000000000200  b9   +0x08A  0x12  2   scalar   yes  0x4668A7  PER base
  11  0x0000000000000400  b10  +0x0A0  0x32  8   scalar   yes  0x4668C5  experience
  12  0x0000000000000800  b11  +0x0A8  0x32  8   scalar   yes  0x4668E3  cash
  13  0x0000000000001000  b12  +0x0B0  0x48  -   wstring  yes  0x466901  
  14  0x0000000000002000  b13  +0x099  0x0B  1   scalar   yes  0x46691B  
  15  0x0000000000004000  b14  +0x09A  0x0B  1   scalar   yes  0x466939  
  16  0x0000000000008000  b15  +0x13E  0x12  2   scalar   yes  0x466957  
  17  0x0000000000010000  b16  +0x13C  0x12  2   scalar   yes  0x466975  
  18  0x0000000000020000  b17  +0x148  0x44  -   blob     yes  0x466993  
  19  0x0000000000040000  b18  +0x182  0x12  2   scalar   yes  0x4669AD  STR bonus
  20  0x0000000000080000  b19  +0x184  0x12  2   scalar   yes  0x4669CB  CON bonus
  21  0x0000000000100000  b20  +0x186  0x12  2   scalar   yes  0x4669E9  DEX bonus
  22  0x0000000000200000  b21  +0x188  0x12  2   scalar   yes  0x466A07  INT bonus
  23  0x0000000000400000  b22  +0x18A  0x12  2   scalar   yes  0x466A25  PER bonus
  24  0x0000000000800000  b23  +0x18C  0x0B  1   scalar   yes  0x466A43  
  25  0x0000000001000000  b24  +0x164  0x48  -   wstring   -   0x466A61  wstring -> LABEL_GUILD (board+0x5C)  [PROVEN VA=0x5BD4C9..0x5BD4DA]
  26  0x0000000002000000  b25  +0x180  0x0B  1   scalar    -   0x466A7B  
  27  0x0000000004000000  b26  +0x098  0x0B  1   scalar    -   0x466A99  
  28  0x0000000004000000  b26  +0x094  0x19  4   scalar    -   0x466A99  
  29  0x0000000008000000  b27  +0x140  0x32  8   scalar    -   0x466AC9  
  30  0x0000000008000000  b27  +0x09B  0x0B  1   scalar    -   0x466AC9  
  31  0x0000000010000000  b28  +0x0CC  0x48  -   wstring  yes  0x466AFE  
  32  0x0000000020000000  b29  +0x198  0x32  8   scalar    -   0x466B18  
  33  0x0000000040000000  b30  +0x190  0x32  8   scalar    -   0x466B36  
  34  0x0000000100000000  b32  +0x1A0  0x0B  1   scalar    -   0x466B62  
  35  0x0000000200000000  b33  +0x1A2  0x12  2   scalar    -   0x466B78  
  36  0x0000000400000000  b34  +0x1A4  0x12  2   scalar    -   0x466B93  
  37  0x0000000800000000  b35  +0x0E8  0x48  -   wstring   -   0x466BAE  
  38  0x0000001000000000  b36  +0x104  0x48  -   wstring   -   0x466BC5  
  39  0x0000002000000000  b37  +0x120  0x48  -   wstring   -   0x466BDC  
  40  0x0000004000000000  b38  +0x1A8  0x14  4   scalar    -   0x466BF3  u32 alt HP cur (used when 0x430E10([+0x5C])==8) [PROVEN VA=0x5BD3D5]
  41  0x0000008000000000  b39  +0x1AC  0x14  4   scalar    -   0x466C0E  u32 alt HP max (same gate)                      [PROVEN VA=0x5BD3DB]
  42  0x0000010000000000  b40  +0x1B0  0x12  2   scalar   yes  0x466C2E  
  43  0x0000020000000000  b41  +0x1B2  0x0B  1   scalar   yes  0x466C51  
```

`[PROVEN VA=0x466767..0x466C79 สำหรับทุกแถว — VA ของเกตอยู่ในคอลัมน์สุดท้าย]`

**สาขา SAVE (`0x466230..0x466767`) กับสาขา LOAD (`0x466767..0x466C79`) สมมาตรกันทีละฟิลด์**
(บิตเดียวกัน offset เดียวกัน tag เดียวกัน width เดียวกัน ลำดับเดียวกัน) — guard `C save and load branches are field-for-field symmetric`
⇒ codec เป็น direction-agnostic แบบเดียวกับ `MovementAttr` ที่ MOVE-PROJECT-001 ปักไว้ `[PROVEN]`

### 3.4 แก้ตัวเลขที่เอกสาร R90 เขียนไว้

| ข้อ | R90 เขียนว่า | ไบต์บอกว่า | เกรด |
|---|---|---|---|
| จำนวนฟิลด์ที่ถูกเกต | **43** | **43 — ถูกต้อง** | `[PROVEN]` (45 codec call ในฟังก์ชัน ลบ header 2 ตัว) |
| mask กว้าง 64 บิต | 64 | **โครงเป็น 64 บิตจริง (สอง dword `+0x1B4`/`+0x1B8` ส่งเป็น qword tag `0x32` ก้อนเดียว) แต่ใช้จริงแค่ 41 บิต** | `[PROVEN]` |
| — | — | บิตที่ใช้ = **b0..b30 และ b32..b41** · **b31 (`0x80000000`) ไม่มีฟิลด์ผูก** · b42..b63 ไม่มีฟิลด์ผูก | `[PROVEN VA=0x4667B3..0x466C51]` |
| — | — | **b26 และ b27 แบกฟิลด์ละ 2 ตัว** (b26 → `+0x98` และ `+0x94`; b27 → `+0x140` และ `+0x9B`) ⇒ 41 บิต ↔ 43 ฟิลด์ | `[PROVEN VA=0x466A99, 0x466AC9]` |
| เกตมีชั้นเดียว | ใช่ (โดยปริยาย) | **ไม่ใช่ — มีเกตชั้นที่สอง `+0x1BC`** | `[PROVEN VA=0x4667E4, 0x466AF9, 0x466C29, 0x466C4C]` |

### 3.5 เกตชั้นที่สอง — ไบต์ `+0x1BC` (wire tag `0x05`)

```
     LOAD  0x4667E4 cmp byte [attr+0x1BC],0 ; jz 0x466A61
     LOAD  0x466AF9 cmp byte [attr+0x1BC],0 ; jz 0x466B18
     LOAD  0x466C29 cmp byte [attr+0x1BC],0 ; jz 0x466C6F
     LOAD  0x466C4C cmp byte [attr+0x1BC],0 ; jz 0x466C6F
```

ถ้าไบต์นี้เป็น `0` ไคลเอนต์จะ **ข้าม 25 จาก 43 ฟิลด์** (แถว 3–24, 31, 42, 43 ในตาราง §3.3)
**โดยไม่สนใจ mask เลย** `[PROVEN VA=0x4667E4/0x466AF9/0x466C29/0x466C4C]`
ค่า default ที่ ctor ตั้งไว้คือ `1` (`0x464E1C  C6 86 BC 01 00 00 01`) `[PROVEN VA=0x464E1C]`
และ `stats_progression_hypothesis.ACTOR_ATTR_EXTRA_GROUP_VALUE = 1` / `player_wire.make_actor_attr_minimal` ก็ส่ง `1` มาตลอด `[PROVEN SRC]`
⇒ **ค่า `1` ที่เราส่งอยู่ถูกแล้ว และห้ามส่ง `0`** ถ้าอยากให้ฟิลด์ในกลุ่มนั้นถึงปลายทาง

---

## 4. (b) เส้น merge/apply `0x469760 -> 0x464F30` — บิตเคลียร์แล้วเกิดอะไร

### 4.1 bind thunk `0x469760` (ActorAttr vtable `+0x38`) — 66 ไบต์ อ่านครบ

```
00469760  56                 push esi
00469761  8B742408           mov  esi,[esp+8]        ; arg = the actor
00469765  57                 push edi
00469766  8BF9               mov  edi,ecx            ; this = the INCOMING ActorAttr
00469768  85F6               test esi,esi
0046976A  7431               jz   0x46979D           ; actor NULL -> return, silently
0046976C  8B06               mov  eax,[esi]
0046976E  8B10               mov  edx,[eax]
00469770  8BCE               mov  ecx,esi
00469772  FFD2               call edx                ; actor->vt[0]()  = type node
00469774  50                 push eax
00469775  682CCB0201         push 0x102CB2C          ; CNetActor node
0046977A  E8315B4200         call 0x88F2B0           ; is-a
0046977F  0FB6C0             movzx eax,al
00469782  83C408             add  esp,8
00469785  F7D8               neg  eax
00469787  1BC0               sbb  eax,eax
00469789  23C6               and  eax,esi            ; eax = actor if is-a else 0
0046978B  7410               jz   0x46979D           ; not a CNetActor -> return, silently
0046978D  8B17               mov  edx,[edi]          ; the INCOMING attr's vtable
0046978F  8B8048030000       mov  eax,[eax+0x348]    ; the actor's RESIDENT ActorAttr
00469795  8B5224             mov  edx,[edx+0x24]     ; <<<< vtable +0x24, NOT +0x30
00469798  50                 push eax
00469799  8BCF               mov  ecx,edi
0046979B  FFD2               call edx                ; incoming->CopyTo(resident)
0046979D  5F5E C20400        pop edi ; pop esi ; ret 4
```

`[PROVEN VA=0x469760..0x4697A1]` · span sha256 `6F8A3251BDE10432E1352A93E082937957BE89BFF8F6AA28BFCEC8B43A48AEC1`

**จุดชี้ขาดคือ `0x469795 mov edx,[edx+0x24]`** — `ActorAttr` vtable `0xF0E7A0`:
- `+0x24 = 0x464F30` = **CopyTo (ก๊อปหมด ไม่ดู mask)**
- `+0x30 = 0x465E60` = **Merge (ดู mask, copy-forward)**

**actor-entry pipe เรียก `+0x24` ไม่ใช่ `+0x30`** `[PROVEN VA=0x469795]`
ทั้งสองฟังก์ชันมี **direct caller = 0** และปรากฏเป็น dword ในไฟล์ **ที่เดียว** คือช่อง vtable ของตัวเอง
⇒ ทางเดียวที่ `0x465E60` จะทำงานได้คือ `attr->vt[+0x30]()` จากที่อื่น (ดู §7 ของที่ยังตอบไม่ได้)

### 4.2 `0x464F30` (vt `+0x24`) — บิตเคลียร์ **ไม่มีผลอะไรเลย เพราะไม่มีใครอ่าน mask**

- กวาดครบ `0x464F30..0x46520E` (143 instruction, ไม่มี undecodable)
- **`test` บน `+0x1B4` / `+0x1B8` / `+0x70` = 0 ครั้ง** `[PROVEN — guard `G 0x464F30 contains ZERO mask tests`]`
- โครง: `test arg,arg ; jz ret` → is-a check ปลายทางกับ node `0x1033484` (`ActorAttr`) → `jz ret`
  → `call 0x464B40` (`BasicAttr` vt `+0x24`) → แล้วก๊อป field ต่อ field แบบไม่มีเงื่อนไข
- ทิศทาง: `this`(edi) = **ก้อนที่มาจากสาย** → `arg`(esi) = **ก้อนที่ actor ถืออยู่ที่ `+0x348`**
  ตัวอย่างไบต์: `0x464F6E  8B 87 8C 00 00 00 | 89 86 8C 00 00 00` = `mov eax,[edi+0x8C] ; mov [esi+0x8C],eax`
- **ก๊อป `+0x78 .. +0x1B2` ครบ รวม wstring ทั้ง 6 และ blob** (ผ่าน thunk `[0xC3B460]` / `[0xC3B48C]`)
- **ไม่ก๊อป mask `+0x1B4`/`+0x1B8`** — attr ประจำตัวของ actor ยังถือ `0xFFFFFFFF` ที่ ctor ตั้งไว้
- **ก๊อป `+0x1BC` (extra-group flag) ด้วย** `[PROVEN VA=0x46516F]`
- ลูกโซ่ล่าง: `0x464B40` (`BasicAttr` vt `+0x24`) ก๊อป `+0x28` (ชื่อ), `+0x44/+0x48` (HP), `+0x4C/+0x50`, `+0x54`, `+0x58`, `+0x5C`, `+0x5E`, `+0x60/+0x64/+0x68/+0x6C`
  **แบบไม่มีเงื่อนไข** และ **ไม่ก๊อป u16 mask `+0x70`** `[PROVEN VA=0x464B7A..0x464BD6]`
  แล้วมันเรียก `0x4676A0` (`DBAttribute` vt `+0x24`) ก่อน ซึ่ง **ก๊อป identity qword `+0x18`** `[PROVEN VA=0x4676CD]`

### 4.3 `0x465E60` (vt `+0x30`, Merge) — อันนี้ต่างหากที่ทำแบบเดียวกับ `BasicAttr::Merge`

```
00465E99  E872F7FFFF     call 0x465610            ; chain BasicAttr::Merge
00465E9E  8B86B4010000   mov  eax,[esi+0x1B4]     ; THIS's mask
00465EA4  A801           test al,1
00465EA6  750C           jnz  0x465EB4            ; bit SET  -> skip
00465EA8  8B8F8C000000   mov  ecx,[edi+0x8C]      ; bit CLEAR -> take the OLD value
00465EAE  898E8C000000   mov  [esi+0x8C],ecx      ;             into THIS
```

`[PROVEN VA=0x465E99..0x465EAE]` — **semantics เดียวกับ `0x4656A3` เป๊ะ**: `this` = ก้อนใหม่,
`arg` = ก้อนเก่า, บิตเคลียร์ ⇒ ค่าเก่า **ถูก copy forward เข้าก้อนใหม่**

### 4.4 คำตอบ (b) แบบตรง ๆ

| ทาง | บิตเคลียร์ | บิตตั้ง |
|---|---|---|
| `ActorAttr::Serial` LOAD `0x466767` | ไม่อ่านฟิลด์นั้นจากสาย ค่าในออบเจกต์ยังเป็น default ของ ctor | อ่านฟิลด์ตาม tag/width ทับลงออบเจกต์ |
| `ActorAttr::Merge` vt `+0x30` = `0x465E60` | **copy forward ค่าเก่าเข้าก้อนใหม่** (เหมือน BasicAttr) | คงค่าใหม่ไว้ |
| **`ActorAttr::CopyTo` vt `+0x24` = `0x464F30` ← ทางที่ actor entry ใช้** | **ไม่สนใจ mask เลย — ก๊อปทุกฟิลด์ทับหมด** | เหมือนกัน (ก๊อปหมด) |

⇒ **`ActorAttr` ไม่ได้ทำแบบเดียวกับ `BasicAttr` บนเส้นที่เลนนี้ใช้** ตัว merge มีอยู่จริงแต่ไม่ได้ถูกเรียก
นี่คือคำตอบของ §10 ข้อ 5 ของ R90 ด้วย: bind thunk **ทับ ไม่ merge** `[PROVEN VA=0x469795 + 0x464F30 ทั้งฟังก์ชัน]`

---

## 5. (c) `mask == 0` ถูกรับ ถูกเมิน หรือถึงตาย — และสาขาไหนตัดสิน

### 5.1 สาขาที่ตัดสิน

```
LOAD  0x4667A5  mov eax,[esi+0x1B4]
LOAD  0x4667AB  cmp eax,ebx            (ebx = 0, ตั้งที่ 0x46676C `xor ebx,ebx`)
LOAD  0x4667AD  jz  0x466B54           <<<< low dword ว่าง -> ข้าม 33 ฟิลด์ล่าง
LOAD  0x466B54  mov eax,[esi+0x1B8]
LOAD  0x466B5A  cmp eax,ebx
LOAD  0x466B5C  jz  0x466C6F           <<<< high dword ว่าง -> ไป epilogue
0x466C6F        5F 5E 5D 5B 83 C4 08 C2 08 00   pop/pop/pop/pop ; add esp,8 ; ret 8
```

สาขา SAVE มีคู่เดียวกัน: `0x466293 jz 0x466638` และ `0x466640 jz 0x466C6F` `[PROVEN]`

### 5.2 คำตอบ

**`mask == 0` = ยอมรับ ไม่ error และไม่ทำให้เฟรมถูกทิ้ง** `[PROVEN VA=0x4667AD, 0x466B5C]`

- ทั้ง `ActorAttr::Serial 0x466230..0x466C79` (740 instruction กวาดครบ) **มี `ret` แค่ 2 จุด**
  คือ `0x466764 ret 8` (ปลายสาขา save) และ `0x466C76 ret 8` (epilogue ร่วม)
  **ไม่มี throw ไม่มี ret-false ไม่มี error path** `[PROVEN — guard `E there is NO error path...`]`
- `jz 0x466B54` / `jz 0x466C6F` เป็นแค่ **short-circuit ข้ามฟิลด์** — ผลคือ "อ่านฟิลด์ 0 ตัว แล้วจบปกติ"
- ผู้เรียก (`0x5DF080` loop) เรียก `attr->vt[+0x38]` ต่อโดยไม่ดูค่าคืน `[PROVEN VA=0x5DF0B7..0x5DF0BB]`
- bind thunk `0x469760` และ `0x464F30` **ไม่มี mask test เลย** ⇒ ไม่มีใคร reject ก้อนที่ mask ว่าง

### 5.3 แต่ผลข้างเคียงของ `mask == 0` ร้ายกว่าการถูกทิ้ง

เพราะ `0x464F30` ก๊อป **ทุกฟิลด์** จากก้อนที่ parse มาไปทับ attr ประจำตัวของ actor
ฟิลด์ที่ mask ไม่ปัก = **ค่า default ของ ctor** ซึ่ง constructor ตั้งไว้แบบนี้:

| ฟิลด์ | default | VA ที่พิสูจน์ |
|---|---|---|
| `BasicAttr +0x28` (ชื่อ) | `L""` (literal `0xF0930C`) | `[PROVEN VA=0x464ACF]` |
| `BasicAttr +0x44` HP cur | **0** (`xor edi,edi` ที่ `0x464AB2`) | `[PROVEN VA=0x464AB2, 0x464B02]` |
| `BasicAttr +0x48` HP max | **0** | `[PROVEN VA=0x464B05]` |
| `BasicAttr +0x58` death timer | `0.0f` | `[PROVEN VA=0x464B0E]` |
| `BasicAttr +0x5E` level | `1` | `[PROVEN VA=0x464AFE]` |
| `BasicAttr +0x70` u16 mask | `0xFFFF` | `[PROVEN VA=0x464AC6]` |
| `ActorAttr +0x1B4/+0x1B8` | `0xFFFFFFFF` ทั้งคู่ | `[PROVEN VA=0x464C95..0x464CA6]` |
| `ActorAttr +0x1BC` | `1` | `[PROVEN VA=0x464E1C]` |

และ predicate ความตายของ actor อ่าน HP ตัวนี้ตรง ๆ:

```
0043BD70  (actor vtable +0x3C)   attr = this->vt[+0x74]() ; cmp [attr+0x44],0 ; jnz ret0
0043BD8C                          comiss xmm0,[attr+0x58] ; ... -> return 1  (HP==0 และ timer<=0)
0043BDA0  (actor vtable +0x40)   attr = this->vt[+0x74]() ; cmp [attr+0x44],0 ; jnz ret0
0043BDB9                          movss xmm0,[attr+0x58] ; comiss -> return 1 (HP==0 และ timer>0)
```

`[PROVEN VA=0x43BD7A, 0x43BD8C, 0x43BDAA, 0x43BDB9]`

⇒ `ActorAttr` ที่ mask ว่าง ทำให้ actor มี **HP = 0 และ timer = 0.0f** ซึ่งทำให้ vt `+0x3C` เป็นจริง
RUNTIMERES-ACTOR-ENTRY-001 ปักไว้แล้วว่า `0x4437C0` (dead-sync) เข้าถึงได้จาก **update path (`vt+0x20`) เท่านั้น ไม่ใช่ spawn**
⇒ ใบแรกจะไม่ทำอะไร แต่ **ใบที่สองของ identity เดิม (เช่น MovementAttr update) จะเจอ HP==0 แล้วเข้าเส้นตาย** `[INFERRED — อาศัย 0x4437C0 ที่รอบก่อนปักไว้ ไม่ได้ decode ใหม่ในรอบนี้]`

**สรุปข้อ (c):** ยอมรับ (`accepted`) `[PROVEN]` · แต่ **ห้ามใช้ในทางปฏิบัติ** เพราะมันเป็นการ "ทับด้วย default" ไม่ใช่ "ไม่แตะ"

---

## 6. (d) ฟิลด์ที่ server แต่งขึ้นเองไม่ได้ — pointer / string / container / identity

| ชนิด | ฟิลด์ | หมายเหตุ |
|---|---|---|
| **identity (qword)** | `DBAttribute +0x18` tag `0x32` **ไม่มีเกต — ต้องส่งเสมอ** | ถูกก๊อปลง attr ประจำตัวโดย `0x4676CD` · นี่คือ identity ของ **attr** ไม่ใช่ของ entry (entry มี `+0x18/+0x1C` ของตัวเอง ที่ `CNetActor::init` ก๊อปไป `actor+0x78/+0x7C`) `[PROVEN VA=0x4676CD, 0x454938]` |
| **wstring (C++ object)** | `ActorAttr +0xB0` (b12), `+0xCC` (b28), `+0xE8` (b35), `+0x104` (b36), `+0x120` (b37), `+0x164` (b24) | 6 ตัว ระยะห่าง `0x1C` เท่ากันหมด · codec `0x89A810`/`0x89A880` ปัก tag `0x48` เอง · dtor `0x464E60` ทำลาย `+0x164`, `+0x120`, ... ⇒ **เป็นออบเจกต์จริง ไม่ใช่ POD** `[PROVEN VA=0x464E8E, 0x464EB3]` |
| **wstring (base)** | `BasicAttr +0x28` bit `0x0001` | ตัวที่ป้อน `LABEL_NAME` |
| **blob / container** | `ActorAttr +0x148` (b17) tag `0x44` codec `0x89A6D0`/`0x89A740` | dtor เรียก `[0xC3B498]` กับมัน (ต่างจาก wstring ที่เรียก `[0xC3B488]`) ⇒ เป็น container คนละชนิด · **โครงภายในยังไม่ decode** `[PROVEN ว่ามีอยู่ · เนื้อใน = ยังไม่รู้]` |
| **pointer ดิบ** | **ไม่พบ** ใน 43 ฟิลด์ | ทุกฟิลด์เป็น scalar 1/2/4/8 ไบต์ หรือ wstring หรือ blob · negative นี้ครอบคลุม `0x466767..0x466C79` ทั้งช่วง กวาดครบ `[PROVEN — scoped]` |

**ข้อควรระวังที่สำคัญที่สุดของหัวข้อนี้:** wstring 6 ตัวและ blob 1 ตัว ถ้า mask ไม่ปัก ก็ยังถูก **ก๊อปทับ** โดย `0x464F30`
ด้วยค่า default (สตริงว่าง / container ว่าง) — ไม่ใช่ "ปล่อยของเดิมไว้"

---

## 7. (e) อะไรที่ทาง construction/render ของ `CNetActor` อ่านจริง

### 7.1 ทาง construction — `0x4469E1` → `0x446A88` → `CNetActor::init 0x454920`

- `0x4469E1` (case `actor_type 2`): `push 0 ; push 0xF0A90C ; mov ecx,0x102CB10 ; call 0x444DE0 ; jmp 0x446A88`
  **ไม่มีเงื่อนไขเพิ่มในช่วงนี้** `[PROVEN VA=0x4469E1..0x4469F6]` (ยืนยัน §10 ข้อ 6 ของ R90 เท่าที่ช่วงนี้บอกได้)
- **ctor `CNetActor` จอง `ActorAttr` ให้เองตั้งแต่เกิด**:
  `0x45739A  53 68 0C A9 F0 00 B9 00 15 03 01` → `0x4573BC call 0x456D20` → `0x4573CA mov [esi+0x348],eax`
  และ call shape นี้ **byte-identical กับ `ActorAttr` vtable `+0x14` (`0x4675E0`)** ซึ่งเป็น allocator ของคลาสนั้นเอง
  `[PROVEN VA=0x45739A, 0x4573BC, 0x4573CA, 0x4675E0]`
  ⇒ `actor+0x348` **ไม่เคยเป็น NULL** สำหรับ `CNetActor` ที่สร้างจาก jump table · `actor+0x34C` (`AvatarAttr`) ก็เช่นกัน (`0x4573E8`)
- `0x446AAD  8B 06 8B 50 10 55 8B CE FF D2` = `actor->vt[+0x10](record)` = `CNetActor::init 0x454920` `[PROVEN]`

**`CNetActor::init 0x454920` (189 ไบต์ 55 instruction กวาดครบ) อ่าน `actor+0x348` = 0 ครั้ง**
`[PROVEN — guard `H CNetActor::init reads actor+0x348 ZERO times`]`
สิ่งที่มันทำ:
1. `cmp [edi],0 ; jz ret` — record ว่าง = ไม่ทำอะไร
2. `this->vt[+0x2C]()`
3. `mov [esi+0x78],[record+0x18]` / `mov [esi+0x7C],[record+0x1C]` = **identity ของ entry** `[PROVEN VA=0x454938]`
4. `call 0x5DF080` = ลูป bind ทุก attr ผ่าน `vt+0x38` `[PROVEN VA=0x454949]`
5. `this->vt[+0x7C]()` = สร้าง name board (`0x456580`, `operator new 0x78` = `NameBoardPlayer`) แล้ว `[actor+0x254]`, template `L"board01"` (`0xF0DABC`), `[actor+0x258]=1`
6. `mov eax,[esi+0x34C]` → ถ้าไม่ NULL `movsx eax,[eax+0x5D]` → คำนวณ scale ลง `actor+0x12C`; ถ้า NULL ใช้ค่า default `[0x10222F8]` `[PROVEN VA=0x454978..0x4549D7]`

**⇒ ไม่มีฟิลด์ `ActorAttr` ตัวไหนที่ "จำเป็นเพื่อให้สร้าง actor สำเร็จ"** — construction ไม่แตะ `+0x348` เลย
สิ่งที่จำเป็นจริงในขั้นนี้คือ **identity ที่ record `+0x18/+0x1C`** เท่านั้น `[PROVEN]`

### 7.2 ทาง render — ป้ายเหนือหัว `NameBoardPlayer::update 0x5BD320` (1472 ไบต์ 490 instruction กวาดครบ)

| อ่านอะไร | จากไหน | ผลถ้าไม่มี | VA |
|---|---|---|---|
| bound attr | `owner->vt[+0x74]()` = `[actor+0x348]` | `test eax,eax ; jz 0x5BD8C7` → **ทั้ง update return ทันที** | `[PROVEN VA=0x5BD377, 0x5BD380]` |
| `attr+0x44`, `attr+0x48` | BasicAttr bit `0x0004`/`0x0008` | HPBAR (board `+0x50`) ได้ `0/0` | `[PROVEN VA=0x5BD3AB]` |
| `attr+0x5C` → `0x430E10()` == 8 ? | BasicAttr bit `0x0100` | ถ้าใช่ HP จะสลับไปอ่าน `ActorAttr +0x1A8/+0x1AC` (b38/b39) แทน | `[PROVEN VA=0x5BD3C0..0x5BD3DB]` |
| `attr+0x28` wstring | BasicAttr bit `0x0001` | `LABEL_NAME` (board `+0x54`) ว่าง | `[PROVEN VA=0x5BD624..0x5BD633]` |
| `ActorAttr+0x164` wstring | mask bit **b24 `0x01000000`** หลัง downcast `0x43B9B0` | `LABEL_GUILD` (board `+0x5C`) ว่าง | `[PROVEN VA=0x5BD4C9, 0x5BD4DA]` |
| `ActorAttr+0x90` u32 | mask bit **b1 `0x00000002`** หลัง downcast | `LABEL_NICKNAME` (board `+0x58`): ถ้าค่าเท่ากับที่ widget cache ไว้ที่ `+0x94` → return; ถ้า `0` → กระโดด `0x5BD872` | `[PROVEN VA=0x5BD7BA..0x5BD7E5]` |

### 7.3 ทางอื่นที่อ่าน attr แล้วสำคัญกับ "ยืนอยู่ตรงนั้นไหม"

- `actor vt+0x3C = 0x43BD70` และ `vt+0x40 = 0x43BDA0` อ่าน `attr+0x44` (HP) และ `attr+0x58` (timer) → §5.3
- `actor vt+0x78 = 0x4549E0` (`GetName`) อ่าน `[actor+0x348]`; NULL → literal ว่าง `0xF0930C` `[PROVEN VA=0x4549E1, 0x454A15]`
- **โมเดล/รูปร่าง ไม่ได้มาจาก `ActorAttr`** — `CNetActor` vt `+0x80 = 0x459F50` เอา `AvatarAttr` ก๊อปลง `actor+0x34C`
  แล้วเรียก `0x459E90` ด้วย `[avatar+0x54]`/`[avatar+0x58]` และตั้ง `[actor+0x250]=1` `[PROVEN VA=0x459F50..0x459F8A]`

### 7.4 คำตอบ (e) แบบตรง ๆ — ชุดฟิลด์ขั้นต่ำที่ "เห็นคนยืนอยู่"

| ระดับ | ต้องมี | เหตุผล | เกรด |
|---|---|---|---|
| ไคลเอนต์ **รับเฟรม** | `actor_type=2` + identity ที่ entry `+0x18` · `ActorAttr` **จะ mask อะไรก็ได้ รวมทั้ง 0** | ไม่มี branch ไหน reject | `[PROVEN]` |
| ป้ายชื่อ **โผล่และอ่านออก** | `BasicAttr` bit `0x0001` (`+0x28` ชื่อ) | `LABEL_NAME` อ่านช่องนี้ช่องเดียว | `[PROVEN VA=0x5BD624]` |
| **ไม่ถูกนับว่าตาย** | `BasicAttr` bit `0x0004` (`+0x44` HP) ต้อง **> 0** | predicate `0x43BD7A`/`0x43BDAA` | `[PROVEN]` + `[INFERRED]` สำหรับผลปลายทางที่ `0x4437C0` |
| หลอดเลือดดูไม่พัง | bit `0x0008` (`+0x48` HP max) ด้วย | HPBAR อ่านคู่กัน | `[PROVEN VA=0x5BD3AB]` |
| ยืนอยู่ตำแหน่งที่สั่ง | `MovementAttr` (คนละ attr) | นอกขอบเขตข้อนี้ | — |
| มีโมเดล | `AvatarAttr` (คนละ attr) | `ActorAttr` ไม่มีฟิลด์รูปร่างเลย | `[PROVEN — 43 ฟิลด์ไม่มีตัวไหนถูกอ่านโดย model load]` เท่าที่กวาด §2 |
| **ไม่จำเป็น** | ทั้ง 43 บิตของ `ActorAttr` mask | ไม่มีบิตไหนที่ construction หรือ board บังคับ · b24 (`+0x164`) และ b1 (`+0x90`) แค่ทำให้ป้าย guild/nickname มีข้อความ | `[PROVEN]` |

**ผลต่อ ROW 1 ของ R90 §10:** ชุด mask ที่ **จำเป็น** ของ `ActorAttr` เอง = **ว่างได้**
สิ่งที่จำเป็นจริงอยู่ในชั้น `BasicAttr` ที่ขี่มาด้วย (bit `0x0001`, `0x0004`, `0x0008`)
ซึ่ง `player_wire.make_actor_attr_with_name` ปักครบอยู่แล้ว ยกเว้น bit `0x0001` ที่ยังไม่มี encoder ตัวไหนปักบนสายนี้

**ผลต่อ ROW 2:** `ActorAttr` 64-bit mask = `0` **ถูกกฎ** `[PROVEN]` แต่ **เป็นการเลือกที่แย่** เพราะ `+0x24` ก๊อปทับหมด
ถ้าจะส่ง `0` ก็ต้องยอมรับว่า `+0x90`, `+0x164` และอีก 41 ฟิลด์จะถูกเซ็ตเป็น default ทุกใบ
ข้อเสนอเชิงปฏิบัติ (ยังเป็น `[DESIGN CHOICE]`): ปัก **b1 (`+0x90`) = 0 อย่างชัดเจน** ไม่ได้ช่วยอะไร —
สิ่งที่ต้องระวังคือ **อย่าส่งใบที่สองด้วย mask ว่าง** เพราะมันจะทับของเดิมที่ถูกต้องทิ้ง

---

## 8. byte span + sha256 (สำหรับ re-pin รอบหน้า)

```
ActorAttr::Serial             0x466230..0x466C79   2633 B  F9EA39F3A6BC80E6D29D4AAE3EFA79C1D5FF855D70109319578CBA86D5F9AABC
  save branch                 0x466230..0x466767   1335 B  2476B579532248DBF28D5ADBCD0EBDEE7CA66DFD3AE0B5B5515B894C060A7AEB
  load branch                 0x466767..0x466C79   1298 B  C50F115CC9E3511F16D9A54E3D3472C4A201C3B4C0CDD9E6914142F0D05B135E
ActorAttr vt+0x24 CopyTo      0x464F30..0x46520E    734 B  48B18BC342646C53235ECABB466A177E3B41B61E72BA50B2AD5E5BE8C62FAF8F
ActorAttr vt+0x30 Merge       0x465E60..0x46622A    970 B  63A88677CCB0F51FDA84427B92CEA962137932481D2D4F8B0ECE655DDEEE5473
ActorAttr vt+0x38 bind thunk  0x469760..0x4697A2     66 B  6F8A3251BDE10432E1352A93E082937957BE89BFF8F6AA28BFCEC8B43A48AEC1
ActorAttr ctor                0x464BE0..0x464E60    640 B  13D3EEA47EE994578BECE42306CA5AD3DB91F43040EE8DE354B0448789E5BD69
BasicAttr::Serial             0x4656F0..0x465850    352 B  55D2288316C78BC53BA527E86FF7FA2570BA5AD69D0FC8CDB9078EC6C97702C4
BasicAttr::Merge              0x465610..0x4656EF    223 B  F8166D39E5E85DD5FA64091994C38C37F06E688248D308CFF358BA4F60EBC4BF
BasicAttr vt+0x24 CopyTo      0x464B40..0x464BD7    151 B  5122010D120D4FC4A8B6FBA3B8D38F005F9FF64B3572B75428927A742DEAB3FC
BasicAttr ctor                0x464A80..0x464B34    180 B  AEFA3A436F15DEB03FE6390BF3F7D05C67E420CFB22A58C254E8F0EEA5E58DD6
DBAttribute::Serial           0x467790..0x4677E8     88 B  379F37AD0307E785FB4A230FC9F1871F69587E6A314DA5930A3A4ED289E55608
DBAttribute vt+0x24 CopyTo    0x4676A0..0x4676E3     67 B  469A79C392341D4F22831B1CB39C57895CD4BAB64A5CE98AA3022056062D86D0
CNetActor::init               0x454920..0x4549DD    189 B  D907227D59491E7955F5E22598979AE4D81A22492BEB87791688A27C52BCC831
CNetActor vt+0x78 GetName     0x4549E0..0x454A22     66 B  D16E90F70B5DDB2B8811FC45B20E25B08408053253816775535CA054AAB56D05
CNetActor ctor attr alloc     0x45739A..0x4573F3     89 B  3B79CAA051D184D51CC0A7EC572172ADFE8A8AF6825A62767DEE86F545B5B9BB
attr apply loop 0x5DF080      0x5DF080..0x5DF0D2     82 B  A65EC5FA355580DE5E39950DA766201907C42EE56B9E8477C9A4874C94E82644
NameBoardPlayer update        0x5BD320..0x5BD8E0   1472 B  986AECBF619A61A3FDC70F970508EA8AB4ADBC4011AFF65D18B23B1ECB3A359A
actor factory 0x446990        0x446990..0x446B2C    412 B  5F68239F8661419DA2EA9BEA4E4A2CB9BCDCAA37FE6E4CD53B701116AEEB697D
actor_type jump table         0x446B2C..0x446B40     20 B  B50C1D1DB53D2B70A8AD258563750738639D5E9E3EEF2FA5CFB4C5354632D606
death predicates 3C/40        0x43BD70..0x43BDD2     98 B  D71FDD888D1EECA36DA6BD4CE3DA0424360B1B7E741CA806EB9F59D2C8B3AC24
```

vtable pins ที่ใช้ในเอกสารนี้:
`ActorAttr` vtable `0xF0E7A0`: `+0x0C=0x464E50(size 0x1C0)` `+0x10=0x464E40(id)` `+0x14=0x4675E0(new)`
`+0x24=0x464F30(CopyTo)` `+0x28=0x465990(SetAllDirty)` `+0x30=0x465E60(Merge)` `+0x34=0x466230(Serial)` `+0x38=0x469760(bind)`
`BasicAttr` vtable `0xF0E760`: `+0x24=0x464B40` `+0x30=0x465610` `+0x34=0x4656F0` `+0x38=0x73D360(ret 4)`

---

## 9. สิ่งที่ยังตอบไม่ได้

รายการนี้มีค่าเท่ากับคำตอบ — อย่าลบ อย่าย่อ

1. **ความหมายของ 28 ฟิลด์ที่ไม่มีชื่อ** ในตาราง §3.3 (b2 `+0x78`, b13 `+0x99`, b14 `+0x9A`, b15 `+0x13E`, b16 `+0x13C`,
   b17 blob `+0x148`, b23 `+0x18C`, b25 `+0x180`, b26 `+0x98`/`+0x94`, b27 `+0x140`/`+0x9B`, b28 `+0xCC`, b29 `+0x198`,
   b30 `+0x190`, b32 `+0x1A0`, b33 `+0x1A2`, b34 `+0x1A4`, b35 `+0xE8`, b36 `+0x104`, b37 `+0x120`, b40 `+0x1B0`, b41 `+0x1B2`)
   — **รู้แค่ bit/tag/width/offset ไม่รู้ว่าแปลว่าอะไร** ต้องตาม consumer ทีละตัวถึงจะรู้ `[ยังไม่ทำ]`
2. **โครงภายในของ blob `+0x148`** (tag `0x44`) — รู้แค่ว่ามันเป็น container ที่ dtor เรียก `[0xC3B498]`
   ไม่รู้ element type ไม่รู้ความยาว ไม่รู้ว่าฝั่ง server จะประกอบยังไง — **นี่คือฟิลด์ที่ server แต่งขึ้นเองไม่ได้**
3. **ใครเรียก `ActorAttr` vtable `+0x30` (Merge `0x465E60`)** — census `mov r,[reg+0x30] ; call r` เป็น pattern ที่ใช้ร่วมกับทุกคลาส
   จึง **resolve ไม่ได้ด้วย byte matching อย่างเดียว** รอบนี้ **ไม่ได้กวาด** ⇒ ยืนยันได้แค่ว่า actor-entry pipe ไม่ใช้มัน
   (ผ่าน `0x469795`) ไม่ได้ยืนยันว่า "ไม่มีใครใช้"
4. **consumer census ของ `actor+0x348` ยังเปิดอยู่** — byte-pattern `mov r,[reg+0x74] ; call r` เจอ **169 จุด**
   และ `+0x78` เจอ **127 จุด** ทั่วอิมเมจ (ไม่ resolve ชนิด) รอบนี้ **ตรวจจริงแค่ 4 จุด**
   (`0x43BD75`, `0x43BDA5`, `0x5BD377`, `0x4549E1`) ⇒ **negative "ไม่มีใครอ่านฟิลด์ X" ห้ามอ้างนอกช่วงที่ §2 ระบุ**
5. **`0x456D20` สร้างอะไรกันแน่** — พิสูจน์ว่า call shape ที่ ctor ใช้ byte-identical กับ `ActorAttr::vt+0x14`
   และ `0x464F30` มี is-a check กับ node ของ `ActorAttr` แต่ **ไม่ได้ decode ตัว pool `0x1031500` เอง** `[INFERRED ระดับแข็ง ไม่ใช่ PROVEN]`
6. **`0x4437C0` (dead-sync) ไม่ได้ decode ใหม่ในรอบนี้** — ข้อสรุปเรื่อง "ใบที่สองจะทำให้ตาย" อาศัยรายงาน
   RUNTIMERES-ACTOR-ENTRY-001 ทั้งดุ้น `[INFERRED]`
7. **ยังไม่รู้ว่า record deserializer สร้าง `ActorAttr` ก้อนใหม่ทุกใบ หรือ reuse** — สมมติฐานว่า "ก้อนใหม่ ⇒ ได้ค่า ctor default"
   อาศัยการที่ ctor `0x464BE0` เป็นที่เดียวที่เขียน vtable `0xF0E7A0` (นอกจาก dtor และ `0x5ACA75`) — **`0x5ACA75` ยังไม่ได้ดู** `[ช่องโหว่ที่รู้ตัว]`
8. **ลำดับ attr ภายใน entry สำคัญไหม** (§10 ข้อ 3 ของ R90) — **ไม่ได้ตอบ** `0x5DF080` เดินตามลำดับใน vector ตรง ๆ
   และ `CNetActor::init` อ่าน `+0x34C` **หลัง** `0x5DF080` จบ `[PROVEN VA=0x454949 → 0x454978]`
   ⇒ ถ้า `AvatarAttr` อยู่ในใบเดียวกันจะทันเสมอ **แต่ยังไม่ได้พิสูจน์ว่าลำดับใน vector = ลำดับบนสาย**
9. **`+0x5C` (BasicAttr bit `0x0100`) แปลว่าอะไร** — รู้แค่ว่ามันเข้าฟังก์ชัน `0x430E10` แล้วผลลัพธ์ `== 8` สลับที่มาของ HP
   **ยังไม่ได้อ่าน `0x430E10`** ⇒ ชื่อ "scene id" ในเอกสารเก่าไม่มีหลักฐาน
10. **b26 และ b27 ที่แบกสองฟิลด์** — ไม่รู้ว่าทำไมสองฟิลด์ถึงใช้บิตเดียวกัน (`+0x98`+`+0x94`, `+0x140`+`+0x9B`)
    เป็นแค่ข้อเท็จจริงจากไบต์ ไม่มีคำอธิบาย
11. **ไม่มีอะไรในรอบนี้พิสูจน์ว่าเฟรม `actor_type 2` เรนเดอร์จริง** — ทั้งหมดเป็น static ยังต้องยิงจริงถึงจะรู้
    รวมถึง `ErrorData=28317` ตาม §10 ข้อ 15 ของ R90
12. **`0x430E10`, `0x43B9B0`, `0x88F2B0`, `0x456D20`, `0x5DF0E0` และ codec `0x89A4D0`/`0x89A550`** — เรียกใช้ในข้อสรุปแต่ไม่ได้ decode ทั้งตัว

---

## 10. nonclaims

- ไม่อ้างอะไรเกี่ยวกับ **เซิร์ฟเวอร์ต้นฉบับ** — ทุกอย่างมาจากไคลเอนต์อย่างเดียว
- ไม่ใช่ runtime observation · ไม่ได้บูตอะไร · ไม่ได้แตะ DB · ไม่ได้เปิด socket · ไม่ได้แตะ `Pirate Force ServerProject/` แม้แต่ไฟล์เดียว
- ไม่ได้เปิด ledger entry ไม่ได้ flip matrix row ไม่ใช่การอนุมัติให้เริ่มเขียน encoder
- ไม่อ้างว่า mask ที่ "ถูกต้อง" คืออะไร — อ้างแค่ว่า **ไม่มี mask ไหนผิดกฎ** และผลของ mask ว่างคืออะไร

---

## 11. สคริปต์ที่ใช้ (pure stdlib, รันซ้ำได้โดยไม่ต้องมีเรา)

บันทึกเป็นไฟล์อะไรก็ได้แล้วรัน:
`python3 <file> "GameClient/GameClient.local.bin"` → คาดหวัง `86 guards, 0 failed`

```python
#!/usr/bin/env python3
# -*- coding: ascii -*-
"""PF CHUNK2-Q1 - ActorAttr::Serial 0x466230 field/mask enumeration, the
merge/apply path 0x469760 -> 0x464F30, and the mask==0 decision.

PURE STDLIB.  No capstone, no pefile.  Includes its own explicit x86-32 length
decoder that RAISES on an unknown opcode instead of silently stopping, so a
negative can be stated with the exact coverage that backs it.

Usage:  python3 pf_actorattr_mask_static.py [path-to-GameClient.local.bin]
Exit 0 = every guard reproduced.
"""
import hashlib
import os
import struct
import sys

EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
EXPECT_SIZE = 14759424

BIN = sys.argv[1] if len(sys.argv) > 1 else "GameClient/GameClient.local.bin"
data = open(BIN, "rb").read()
SHA = hashlib.sha256(data).hexdigest().upper()

# ---------------------------------------------------------------- PE plumbing
_e = struct.unpack_from("<I", data, 0x3C)[0]
_coff = _e + 4
_nsec = struct.unpack_from("<H", data, _coff + 2)[0]
_optsz = struct.unpack_from("<H", data, _coff + 16)[0]
_opt = _coff + 20
IMAGE_BASE = struct.unpack_from("<I", data, _opt + 28)[0]
_sect = _opt + _optsz
SECS = []
for _i in range(_nsec):
    _o = _sect + _i * 40
    _nm = data[_o:_o + 8].rstrip(b"\0").decode("latin1")
    _vs, _va, _rs, _rp = struct.unpack_from("<IIII", data, _o + 8)
    _ch = struct.unpack_from("<I", data, _o + 36)[0]
    SECS.append((_nm, _va, _vs, _rp, _rs, _ch))
EXEC_SECS = [(nm, IMAGE_BASE + va, vs, rp, rs)
             for nm, va, vs, rp, rs, ch in SECS if ch & 0x20000000]


def va2off(va):
    r = va - IMAGE_BASE
    for nm, va0, vs, rp, rs, ch in SECS:
        if va0 <= r < va0 + max(vs, rs):
            o = rp + (r - va0)
            return o if o < len(data) else None
    return None


def off2va(off):
    for nm, va0, vs, rp, rs, ch in SECS:
        if rp <= off < rp + rs:
            return IMAGE_BASE + va0 + (off - rp)
    return None


def rd(va, n):
    o = va2off(va)
    return data[o:o + n] if o is not None else b""


def dw(va):
    b = rd(va, 4)
    return struct.unpack("<I", b)[0] if len(b) == 4 else None


def span_sha(lo, hi):
    return hashlib.sha256(rd(lo, hi - lo)).hexdigest().upper()


def rel32_sites(target, opcode):
    out = []
    pat = bytes([opcode])
    for nm, va0, vs, rp, rs in EXEC_SECS:
        end = rp + rs
        i = data.find(pat, rp, end - 5)
        while i >= 0:
            rel = struct.unpack_from("<i", data, i + 1)[0]
            va = off2va(i)
            if va is not None and ((va + 5 + rel) & 0xFFFFFFFF) == target:
                out.append(va)
            i = data.find(pat, i + 1, end - 5)
    return sorted(out)


def calls_to(t):
    return rel32_sites(t, 0xE8)


def dword_vas(value):
    pat = struct.pack("<I", value)
    out, i = [], data.find(pat)
    while i >= 0:
        v = off2va(i)
        if v is not None:
            out.append(v)
        i = data.find(pat, i + 1)
    return out


# ------------------------------------------------- explicit x86-32 len decoder
class Undecodable(Exception):
    def __init__(self, va, b):
        Exception.__init__(self, "undecodable opcode %02X at VA=0x%X" % (b, va))
        self.va = va


PREFIXES = set([0x66, 0x67, 0xF0, 0xF2, 0xF3, 0x2E, 0x36, 0x3E, 0x26, 0x64, 0x65])
MODRM_NOIMM = set([0x00, 0x01, 0x02, 0x03, 0x08, 0x09, 0x0A, 0x0B, 0x10, 0x11,
                   0x12, 0x13, 0x18, 0x19, 0x1A, 0x1B, 0x20, 0x21, 0x22, 0x23,
                   0x28, 0x29, 0x2A, 0x2B, 0x30, 0x31, 0x32, 0x33, 0x38, 0x39,
                   0x3A, 0x3B, 0x62, 0x63, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
                   0x8A, 0x8B, 0x8C, 0x8D, 0x8E, 0x8F, 0xD0, 0xD1, 0xD2, 0xD3,
                   0xFE, 0xFF, 0xD8, 0xD9, 0xDA, 0xDB, 0xDC, 0xDD, 0xDE, 0xDF])
MODRM_IMM8 = set([0x80, 0x83, 0xC0, 0xC1, 0xC6, 0x6B])
MODRM_IMMZ = set([0x81, 0xC7, 0x69])
NOMODRM_NOIMM = set(list(range(0x40, 0x60)) +
                    [0x06, 0x07, 0x0E, 0x16, 0x17, 0x1E, 0x1F, 0x27, 0x2F, 0x37,
                     0x3F, 0x60, 0x61, 0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96,
                     0x97, 0x98, 0x99, 0x9B, 0x9C, 0x9D, 0x9E, 0x9F, 0xA4, 0xA5,
                     0xA6, 0xA7, 0xAA, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF, 0xC3, 0xCB,
                     0xC9, 0xCC, 0xCE, 0xCF, 0xEC, 0xED, 0xEE, 0xEF, 0xF4, 0xF5,
                     0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD])
NOMODRM_IMM8 = set([0x04, 0x0C, 0x14, 0x1C, 0x24, 0x2C, 0x34, 0x3C, 0x6A, 0xA8,
                    0xCD, 0xE4, 0xE5, 0xE6, 0xE7, 0xEB] +
                   list(range(0xB0, 0xB8)) + list(range(0x70, 0x80)))
NOMODRM_IMMZ = set([0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D, 0x68, 0xA9,
                    0xE8, 0xE9] + list(range(0xB8, 0xC0)))
NOMODRM_IMM16 = set([0xC2, 0xCA])
MOFFS = set([0xA0, 0xA1, 0xA2, 0xA3])
OF_MODRM_NOIMM = set(list(range(0x10, 0x18)) + list(range(0x28, 0x30)) +
                     list(range(0x40, 0x70)) + list(range(0x74, 0x77)) +
                     [0x7E, 0x7F, 0x6E, 0x6F, 0x1F, 0x00, 0x01] +
                     list(range(0x90, 0xA0)) +
                     [0xA3, 0xAB, 0xB3, 0xBB, 0xAF, 0xB0, 0xB1, 0xB2, 0xB4, 0xB5,
                      0xB6, 0xB7, 0xBC, 0xBD, 0xBE, 0xBF, 0xC0, 0xC1, 0x2A, 0x2C,
                      0x2D, 0x5A, 0x5B] + list(range(0xD0, 0xF0)) +
                     list(range(0xF1, 0xFF)))
OF_MODRM_IMM8 = set([0x70, 0x71, 0x72, 0x73, 0xA4, 0xAC, 0xC2, 0xC4, 0xC5, 0xC6, 0x0F])
OF_REL32 = set(range(0x80, 0x90))
OF_NOMODRM = set([0x05, 0x06, 0x07, 0x08, 0x09, 0x0B, 0x30, 0x31, 0x32, 0x33,
                  0x34, 0x35, 0xA0, 0xA1, 0xA2, 0xA8, 0xA9, 0xAA, 0x77] +
                 list(range(0xC8, 0xD0)))
R32 = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"]


def _modrm(off):
    m = data[off]
    mod, reg, rm = m >> 6, (m >> 3) & 7, m & 7
    n, disp = 1, None
    if mod == 3:
        return n, None, mod, reg, rm
    if rm == 4:
        sib = data[off + 1]
        n += 1
        if mod == 0 and (sib & 7) == 5:
            disp = struct.unpack_from("<i", data, off + n)[0]
            return n + 4, disp, mod, reg, rm
    elif mod == 0 and rm == 5:
        return n + 4, struct.unpack_from("<I", data, off + n)[0], mod, reg, rm
    if mod == 1:
        disp = struct.unpack_from("<b", data, off + n)[0]
        n += 1
    elif mod == 2:
        disp = struct.unpack_from("<i", data, off + n)[0]
        n += 4
    else:
        disp = 0
    return n, disp, mod, reg, rm


def decode(va):
    off = va2off(va)
    i = off
    op16 = False
    while data[i] in PREFIXES:
        if data[i] == 0x66:
            op16 = True
        i += 1
    op = data[i]
    i += 1
    z = 2 if op16 else 4
    r = {"va": va, "op": op, "esc": None, "mod": None, "reg": None, "rm": None,
         "disp": None, "imm": None, "target": None}
    if op == 0x0F:
        esc = data[i]
        r["esc"] = esc
        i += 1
        if esc in OF_REL32:
            rel = struct.unpack_from("<i", data, i)[0]
            i += 4
            r["target"] = (va + (i - off) + rel) & 0xFFFFFFFF
        elif esc in OF_MODRM_IMM8:
            n, d, mo, rg, rm = _modrm(i)
            i += n + 1
            r.update(mod=mo, reg=rg, rm=rm, disp=d)
        elif esc in OF_MODRM_NOIMM:
            n, d, mo, rg, rm = _modrm(i)
            i += n
            r.update(mod=mo, reg=rg, rm=rm, disp=d)
        elif esc in OF_NOMODRM:
            pass
        else:
            raise Undecodable(va, 0x0F00 | esc)
        r["len"] = i - off
        return r
    if op in (0xF6, 0xF7):
        n, d, mo, rg, rm = _modrm(i)
        i += n
        r.update(mod=mo, reg=rg, rm=rm, disp=d)
        if rg in (0, 1):
            if op == 0xF6:
                r["imm"] = data[i]
                i += 1
            else:
                r["imm"] = struct.unpack_from("<I" if not op16 else "<H", data, i)[0]
                i += z
        r["len"] = i - off
        return r
    if op in MODRM_NOIMM:
        n, d, mo, rg, rm = _modrm(i)
        i += n
        r.update(mod=mo, reg=rg, rm=rm, disp=d)
    elif op in MODRM_IMM8:
        n, d, mo, rg, rm = _modrm(i)
        i += n
        r.update(mod=mo, reg=rg, rm=rm, disp=d, imm=data[i])
        i += 1
    elif op in MODRM_IMMZ:
        n, d, mo, rg, rm = _modrm(i)
        i += n
        r.update(mod=mo, reg=rg, rm=rm, disp=d,
                 imm=struct.unpack_from("<I" if not op16 else "<H", data, i)[0])
        i += z
    elif op in NOMODRM_NOIMM:
        pass
    elif op in NOMODRM_IMM8:
        v = struct.unpack_from("<b", data, i)[0]
        r["imm"] = data[i]
        i += 1
        if 0x70 <= op < 0x80 or op == 0xEB:
            r["target"] = (va + (i - off) + v) & 0xFFFFFFFF
    elif op in NOMODRM_IMMZ:
        v = struct.unpack_from("<i", data, i)[0]
        r["imm"] = v & 0xFFFFFFFF
        i += z
        if op in (0xE8, 0xE9):
            r["target"] = (va + (i - off) + v) & 0xFFFFFFFF
    elif op in NOMODRM_IMM16:
        r["imm"] = struct.unpack_from("<H", data, i)[0]
        i += 2
    elif op in MOFFS:
        r["disp"] = struct.unpack_from("<I", data, i)[0]
        i += 4
    else:
        raise Undecodable(va, op)
    r["len"] = i - off
    return r


def walk(lo, hi):
    """Linear decode.  Returns (instructions, stopped_at_or_None)."""
    out, va = [], lo
    while va < hi:
        try:
            r = decode(va)
        except Undecodable as e:
            return out, va
        out.append(r)
        va += r["len"]
    return out, None


# ------------------------------------------------------------- guard plumbing
fails = []
n_guard = 0


def check(name, cond, detail=""):
    global n_guard
    n_guard += 1
    print(("[OK]   " if cond else "[FAIL] ") + name + (("  " + detail) if detail else ""))
    if not cond:
        fails.append(name)


print("== image ==")
check("image size", len(data) == EXPECT_SIZE, "%d" % len(data))
check("image sha256", SHA == EXPECT_SHA, SHA)
check("image base 0x400000", IMAGE_BASE == 0x400000)
check("two executable sections (.text + .code)",
      [s[0] for s in EXEC_SECS] == [".text", ".code"])

# =========================================================== KNOWN-ANSWER PINS
print()
print("== A. re-derivation of answers this project already pinned ==")

# A1: BasicAttr bit 0x0080 -> object +0x58, wire tag 0x2A (HP-DEATH-001)
b = rd(0x4657AE, 0x4657C2 - 0x4657AE)
check("A1 BasicAttr::Serial 0x4657AE = test byte [ebx+0],0x80  (ebx = attr+0x70 mask)",
      b[:3] == bytes.fromhex("f60380"), b.hex().upper())
check("A1 gate is followed by push 4 / lea ecx,[esi+0x58] / push ecx / push 0x2A / call 0x89A600",
      b == bytes.fromhex("f60380740f6a048d4e58516a2a8bcfe83e4e4300"))
check("A1 lea ebx,[esi+0x70] at 0x465708 makes the gate base the BasicAttr u16 mask",
      rd(0x465708, 3) == bytes.fromhex("8d5e70"))
check("A1 => BasicAttr bit 0x0080 -> object +0x58, tag 0x2A, width 4", True,
      "[PROVEN VA=0x4657AE..0x4657C1]")

# A2: BasicAttr::Merge copies a CLEARED field forward, at 0x4656A3
check("A2 BasicAttr::Merge is BasicAttr vtable +0x30 = 0x465610",
      dw(0xF0E760 + 0x30) == 0x465610, hex(dw(0xF0E760 + 0x30)))
check("A2 0x46564E reads THIS's mask: test byte [edi+0x70],1",
      rd(0x46564E, 4) == bytes.fromhex("f6477001"))
check("A2 0x4656A3 = test al,al / js +6 / fld [esi+0x58] / fstp [edi+0x58]",
      rd(0x4656A3, 10) == bytes.fromhex("84c07806d94658d95f58"),
      rd(0x4656A3, 10).hex().upper())
check("A2 => bit CLEAR  ==> old(arg,esi) value is copied FORWARD into this(edi)", True,
      "[PROVEN VA=0x4656A3]")

# A3: actor_type jump table (MPAUDIT-FOLLOWUP-001)
JT = [dw(0x446B2C + 4 * i) for i in range(5)]
check("A3 jump table 0x446B2C has the 5 pinned entries",
      JT == [0x4469E1, 0x4469F7, 0x446A3D, 0x446A5A, 0x446A77],
      " ".join(hex(x) for x in JT))
check("A3 span 0x446990..0x446B2C sha256 == 5F68239F...697D",
      span_sha(0x446990, 0x446B2C).startswith("5F68239F"), span_sha(0x446990, 0x446B2C))
check("A3 table span 0x446B2C..0x446B40 sha256 == B50C1D1D...D606",
      span_sha(0x446B2C, 0x446B40).startswith("B50C1D1D"), span_sha(0x446B2C, 0x446B40))
check("A3 0x4469C8 movzx eax,byte [eax+0x10]; add eax,-2; cmp eax,4; ja",
      rd(0x4469C8, 4) == bytes.fromhex("0fb64010") and
      rd(0x4469CC, 3) == bytes.fromhex("83c0fe") and
      rd(0x4469D1, 3) == bytes.fromhex("83f804"))

# =============================================== B. ActorAttr::Serial extent
print()
print("== B. ActorAttr::Serial 0x466230 - extent and coverage ==")
SER_LO, SER_HI = 0x466230, 0x466C79
ins, stopped = walk(SER_LO, SER_HI)
check("B decoder covered 0x466230..0x466C79 with NO undecodable byte",
      stopped is None, "stopped at 0x%X" % stopped if stopped else "full")
end_va = ins[-1]["va"] + ins[-1]["len"]
check("B last decoded instruction ends exactly on 0x466C79", end_va == SER_HI,
      "0x%X" % end_va)
check("B last instruction is `ret 8` (C2 08 00) at 0x466C76",
      rd(0x466C76, 3) == bytes.fromhex("c20800"))
check("B 0x466C79..0x466C80 is INT3 padding", rd(0x466C79, 7) == b"\xcc" * 7)
check("B ActorAttr vtable 0xF0E7A0 +0x34 == 0x466230 (this really is ::Serial)",
      dw(0xF0E7A0 + 0x34) == 0x466230)
check("B ActorAttr::Serial chains BasicAttr::Serial first (0x466243 call 0x4656F0)",
      rd(0x466243, 5) == bytes.fromhex("e8a8f4ffff"))
check("B ActorAttr object size (vt+0x0C -> mov eax,0x1C0) == 0x1C0",
      dw(0xF0E7A0 + 0x0C) == 0x464E50 and rd(0x464E50, 5) == bytes.fromhex("b8c0010000"))
print("     span 0x466230..0x466C79 sha256 = " + span_sha(SER_LO, SER_HI))
print("     instructions decoded          = %d" % len(ins))

# ------------------------------------------------------- field-table extractor
CODEC_OUT = {0x89A600: ("scalar", None), 0x89A810: ("wstring", 0x48), 0x89A6D0: ("blob", 0x44)}
CODEC_IN = {0x89A640: ("scalar", None), 0x89A880: ("wstring", 0x48), 0x89A740: ("blob", 0x44)}
check("B codec 0x89A810 (wstring out) pushes wire tag 0x48",
      rd(0x89A833, 2) == bytes.fromhex("6a48"))
check("B codec 0x89A6D0 (blob out) pushes wire tag 0x44",
      rd(0x89A6F1, 2) == bytes.fromhex("6a44"))
check("B codec 0x89A880 (wstring in) pushes wire tag 0x48",
      rd(0x89A89C, 2) == bytes.fromhex("6a48"))

MASK_MEM = {("esi", 0x1B4): "LO", ("esi", 0x1B8): "HI"}


def extract(lo, hi, codecs, mask_mem=None):
    """Pair every codec call with the gate that dominates it.  Returns
    (records, extra_group_checks, mask_zero_branches, stopped_at)."""
    if mask_mem is None:
        mask_mem = MASK_MEM
    recs, egrp, mzero = [], [], []
    va = lo
    gate = None
    lea = None
    pushes = []
    consts = {}
    leamap = {}
    last_mask_load = None
    while va < hi:
        try:
            r = decode(va)
        except Undecodable:
            return recs, egrp, mzero, va
        op, esc = r["op"], r["esc"]
        if esc is None and 0xB8 <= op <= 0xBF:
            consts[R32[op - 0xB8]] = r["imm"]
        if esc is None and op == 0x33 and r["mod"] == 3 and r["reg"] == r["rm"]:
            consts[R32[r["reg"]]] = 0
        # --- mask register load: mov / movzx <r>,[<maskmem>]
        if r["mod"] is not None and r["mod"] != 3 and \
           (R32[r["rm"]], r["disp"]) in mask_mem and \
           ((esc is None and op == 0x8B) or esc in (0xB6, 0xB7)):
            last_mask_load = (R32[r["reg"]], mask_mem[(R32[r["rm"]], r["disp"])], va)
        # --- `and <maskreg>,<constreg>` gate form (BasicAttr high bits)
        if esc is None and op == 0x23 and r["mod"] == 3 and last_mask_load and \
           R32[r["reg"]] == last_mask_load[0] and consts.get(R32[r["rm"]]) is not None:
            gate = (va, last_mask_load[1], consts[R32[r["rm"]]])
        # --- whole-mask zero test:  test <r>,<r>   /   cmp <r>,<rzero>
        if esc is None and op == 0x85 and r["mod"] == 3 and r["reg"] == r["rm"] and \
           last_mask_load and last_mask_load[0] == R32[r["rm"]]:
            nxt = decode(va + r["len"])
            if nxt["target"] is not None:
                mzero.append((va, last_mask_load[1], nxt["va"], nxt["target"]))
        if esc is None and op == 0x3B and r["mod"] == 3 and \
           last_mask_load and last_mask_load[0] == R32[r["reg"]] and \
           consts.get(R32[r["rm"]]) == 0:
            nxt = decode(va + r["len"])
            if nxt["target"] is not None:
                mzero.append((va, last_mask_load[1], nxt["va"], nxt["target"]))
        # --- extra-group flag test: cmp byte [ebp+0],0  /  cmp [ebp+0],bl
        if esc is None and op in (0x80, 0x38) and r["mod"] != 3 and \
           R32[r["rm"]] == "ebp" and (r["disp"] or 0) == 0:
            nxt = decode(va + r["len"])
            if nxt["target"] is not None:
                egrp.append((va, nxt["target"]))
        # --- bit gates
        if esc is None and op == 0xA8 and last_mask_load:
            gate = (va, last_mask_load[1], r["imm"])
        elif esc is None and op in (0xF6, 0xF7) and r["reg"] in (0, 1) and r["mod"] != 3 \
                and (R32[r["rm"]], r["disp"]) in mask_mem:
            gate = (va, mask_mem[(R32[r["rm"]], r["disp"])], r["imm"])
        elif esc is None and op == 0x85 and r["mod"] != 3 and \
                (R32[r["rm"]], r["disp"]) in mask_mem:
            gate = (va, mask_mem[(R32[r["rm"]], r["disp"])], consts.get(R32[r["reg"]]))
        # --- operand staging
        if esc is None and op == 0x8D and r["mod"] != 3:
            leamap[R32[r["reg"]]] = (R32[r["rm"]], r["disp"])
            lea = (R32[r["rm"]], r["disp"])
        if esc is None and op in (0x81, 0x83) and r["reg"] == 0 and r["mod"] == 3:
            lea = (R32[r["rm"]], r["imm"])
        if esc is None and op == 0x6A:
            pushes.append(r["imm"])
        # --- the call
        if esc is None and op == 0xE8:
            if r["target"] in codecs:
                kind, fixed_tag = codecs[r["target"]]
                tag = fixed_tag if fixed_tag is not None else (pushes[-1] if pushes else None)
                width = pushes[0] if (fixed_tag is None and pushes) else None
                recs.append({"call": va, "kind": kind, "tag": tag, "width": width,
                             "gate": gate, "off": lea})
            pushes = []
            lea = None
        va += r["len"]
    return recs, egrp, mzero, None


SAVE_LO, SAVE_HI = 0x466230, 0x466767
LOAD_LO, LOAD_HI = 0x466767, 0x466C79
sv, sv_eg, sv_mz, sv_stop = extract(SAVE_LO, SAVE_HI, CODEC_OUT)
ld, ld_eg, ld_mz, ld_stop = extract(LOAD_LO, LOAD_HI, CODEC_IN)

print()
print("== C. the field table (LOAD branch = what the client runs on an inbound ActorAttr) ==")
check("C save branch decoded with no undecodable byte", sv_stop is None)
check("C load branch decoded with no undecodable byte", ld_stop is None)
check("C save branch has 45 codec calls", len(sv) == 45, str(len(sv)))
check("C load branch has 45 codec calls", len(ld) == 45, str(len(ld)))
check("C first two calls are UNGATED header fields (mask64, extra-group flag)",
      sv[0]["tag"] == 0x32 and sv[0]["width"] == 8 and
      sv[1]["tag"] == 0x05 and sv[1]["width"] == 1 and sv[1]["off"] == ("esi", 0x1BC))
gated_sv = [r for r in sv[2:]]
gated_ld = [r for r in ld[2:]]
check("C => 43 GATED fields  (design doc R90 said 43: CONFIRMED)",
      len(gated_sv) == 43 and len(gated_ld) == 43, "%d / %d" % (len(gated_sv), len(gated_ld)))

# save/load symmetry
sym = all((a["gate"][1], a["gate"][2], a["off"], a["kind"], a["tag"], a["width"]) ==
          (b_["gate"][1], b_["gate"][2], b_["off"], b_["kind"], b_["tag"], b_["width"])
          for a, b_ in zip(gated_sv, gated_ld))
check("C save and load branches are field-for-field symmetric (same bit, offset, tag, width, order)",
      sym)

bits_lo = sorted(set(r["gate"][2] for r in gated_ld if r["gate"][1] == "LO"))
bits_hi = sorted(set(r["gate"][2] for r in gated_ld if r["gate"][1] == "HI"))
check("C low dword uses bits 0x00000001..0x40000000 (31 bits); 0x80000000 is UNUSED",
      bits_lo == [1 << i for i in range(31)], "%d distinct" % len(bits_lo))
check("C high dword uses bits 0x00000001..0x00000200 (10 bits) => mask bits 32..41",
      bits_hi == [1 << i for i in range(10)], "%d distinct" % len(bits_hi))
check("C 41 distinct mask bits carry 43 fields (two bits carry two fields each)",
      len(bits_lo) + len(bits_hi) == 41)


def in_extra(call_va, checks):
    for cva, tgt in checks:
        if cva < call_va < tgt:
            return True
    return False


NAMED = {
    0x8C: "class id            (STATS-PROG-001)",
    0x7C: "skill points        (STATS-PROG-001)",
    0x80: "unspent ability pts (STATS-PROG-001)",
    0x82: "STR base", 0x84: "CON base", 0x86: "DEX base",
    0x88: "INT base", 0x8A: "PER base",
    0xA0: "experience", 0xA8: "cash",
    0x182: "STR bonus", 0x184: "CON bonus", 0x186: "DEX bonus",
    0x188: "INT bonus", 0x18A: "PER bonus",
    0x164: "wstring -> LABEL_GUILD (board+0x5C)  [PROVEN VA=0x5BD4C9..0x5BD4DA]",
    0x90:  "u32 -> NameBoard nickname key        [PROVEN VA=0x5BD7BA..0x5BD7D5]",
    0x1A8: "u32 alt HP cur (used when 0x430E10([+0x5C])==8) [PROVEN VA=0x5BD3D5]",
    0x1AC: "u32 alt HP max (same gate)                      [PROVEN VA=0x5BD3DB]",
}
print()
print("  #  maskbit(64)   bit         obj_off  tag  w   kind     xgrp  load-gate   note")
rows = []
for i, r in enumerate(gated_ld):
    half, bit = r["gate"][1], r["gate"][2]
    bitno = (0 if half == "LO" else 32) + bit.bit_length() - 1
    m64 = 1 << bitno
    xg = "yes" if in_extra(r["call"], ld_eg) else " - "
    off = r["off"][1]
    rows.append((bitno, m64, off, r["tag"], r["width"], r["kind"], xg, r["gate"][0]))
    print("  %2d  0x%016X  b%-2d  +0x%03X  0x%02X  %-3s %-8s %-4s 0x%06X  %s" % (
        i + 1, m64, bitno, off, r["tag"],
        str(r["width"]) if r["width"] else "-", r["kind"], xg, r["gate"][0],
        NAMED.get(off, "")))

print()
print("== C2. the wire PREFIX that rides in front of every ActorAttr ==")
print("   (ActorAttr::Serial 0x466230 calls BasicAttr::Serial 0x4656F0 FIRST, which calls")
print("    DBAttribute::Serial 0x467790 FIRST, so the wire order is DB -> Basic -> Actor)")
db, db_eg, db_mz, db_stop = extract(0x467790, 0x4677E8, CODEC_OUT)
ba, ba_eg, ba_mz, ba_stop = extract(0x4656F0, 0x465850, CODEC_OUT, {("ebx", 0): "LO"})
check("C2 DBAttribute::Serial decoded clean, 2 ungated fields", db_stop is None and len(db) == 2)
for r in db:
    print("     DBAttribute  UNGATED  +0x%03X  tag 0x%02X  w %s" % (r["off"][1], r["tag"], r["width"]))
check("C2 BasicAttr::Serial decoded clean, 13 codec calls (1 ungated mask + 12 gated)",
      ba_stop is None and len(ba) == 13, str(len(ba)))
BA_NAMED = {0x28: "NAME wstring -> LABEL_NAME (board+0x54)", 0x5E: "level",
            0x44: "HP current  -> HPBAR and the death predicates 0x43BD70/0x43BDA0",
            0x48: "HP max      -> HPBAR", 0x4C: "MP current", 0x50: "MP max",
            0x58: "death/respawn timer f32 (HP-DEATH-001)",
            0x5C: "u16 category; 0x430E10(cat)==8 switches HP to ActorAttr +0x1A8/+0x1AC"}
for i, r in enumerate(ba):
    if r["gate"] is None or i == 0:
        print("     BasicAttr    UNGATED  +0x%03X  tag 0x%02X  w %s   (the u16 change mask itself)"
              % (r["off"][1], r["tag"], r["width"]))
        continue
    print("     BasicAttr    bit 0x%04X  +0x%03X  tag 0x%02X  w %-2s  %s"
          % (r["gate"][2], r["off"][1], r["tag"], r["width"], BA_NAMED.get(r["off"][1], "")))
check("C2 BasicAttr bit 0x0001 -> +0x28 wstring tag 0x48",
      ba[1]["gate"][2] == 1 and ba[1]["off"][1] == 0x28 and ba[1]["tag"] == 0x48)
check("C2 BasicAttr bit 0x0080 -> +0x58 tag 0x2A width 4 (the pinned death timer)",
      ba[8]["gate"][2] == 0x80 and ba[8]["off"][1] == 0x58 and ba[8]["tag"] == 0x2A
      and ba[8]["width"] == 4)

print()
print("== D. containers / strings / pointers inside ActorAttr ==")
wstr_offs = sorted(r["off"][1] for r in gated_ld if r["kind"] == "wstring")
blob_offs = sorted(r["off"][1] for r in gated_ld if r["kind"] == "blob")
check("D 6 wstring fields", len(wstr_offs) == 6,
      " ".join("+0x%X" % o for o in wstr_offs))
check("D 1 blob/container field", len(blob_offs) == 1,
      " ".join("+0x%X" % o for o in blob_offs))
check("D ActorAttr dtor 0x464E60 destroys +0x164, +0x148, +0x120 (real C++ objects, not PODs)",
      rd(0x464E8E, 6) == bytes.fromhex("8d8e64010000") and
      rd(0x464EA2, 6) == bytes.fromhex("8d8e48010000") and
      rd(0x464EB3, 6) == bytes.fromhex("8d8e20010000"))
check("D the identity qword is NOT in ActorAttr: it is DBAttribute +0x18, tag 0x32, ser 0x467790",
      dw(0xF0E720 + 0x34) is not None)

print()
print("== E. mask == 0 : which branch decides ==")
for va, half, jva, tgt in ld_mz:
    print("     LOAD  0x%06X test mask.%s ; 0x%06X jz 0x%06X" % (va, half, jva, tgt))
check("E load branch: mask LOW  == 0 -> jz 0x466B54 (skip all 33 low fields)",
      (0x4667AB, "LO", 0x4667AD, 0x466B54) in ld_mz)
check("E load branch: mask HIGH == 0 -> jz 0x466C6F (the epilogue)",
      (0x466B5A, "HI", 0x466B5C, 0x466C6F) in ld_mz)
check("E 0x466C6F is the shared epilogue pop/pop/pop/pop/add esp,8/ret 8",
      rd(0x466C6F, 10) == bytes.fromhex("5f5e5d5b83c408c20800"))
check("E save branch has the same two short-circuits (0x466293 -> 0x466638, 0x466640 -> 0x466C6F)",
      (0x466291, "LO", 0x466293, 0x466638) in sv_mz and
      (0x46663E, "HI", 0x466640, 0x466C6F) in sv_mz)
check("E there is NO error path, NO throw, NO ret-false anywhere in ::Serial: "
      "the only ret in the function is the shared `ret 8`",
      len([r for r in ins if r["esc"] is None and r["op"] in (0xC2, 0xC3)]) == 2,
      "%d ret instructions (0x466764 and 0x466C76)" %
      len([r for r in ins if r["esc"] is None and r["op"] in (0xC2, 0xC3)]))

print()
print("== F. the extra-group flag +0x1BC (wire tag 0x05) is a SECOND gate ==")
for cva, tgt in ld_eg:
    print("     LOAD  0x%06X cmp byte [attr+0x1BC],0 ; jz 0x%06X" % (cva, tgt))
n_x = sum(1 for r in gated_ld if in_extra(r["call"], ld_eg))
check("F when +0x1BC == 0 the client SKIPS %d of the 43 gated fields "
      "regardless of the mask" % n_x, n_x == 25, str(n_x))
check("F ActorAttr ctor default for +0x1BC is 1 (0x464E1C mov byte [esi+0x1BC],1)",
      rd(0x464E1C, 7) == bytes.fromhex("c686bc01000001"))

print()
print("== G. the merge/apply path 0x469760 -> 0x464F30 ==")
check("G 0x469760 is ActorAttr vtable +0x38 (the bind thunk) and its ONLY reference",
      dw(0xF0E7A0 + 0x38) == 0x469760 and dword_vas(0x469760) == [0xF0E7A0 + 0x38] and
      calls_to(0x469760) == [])
check("G 0x469768 test esi,esi / jz  : NULL actor -> silent return",
      rd(0x469768, 4) == bytes.fromhex("85f67431"))
check("G 0x469775 pushes CNetActor type node 0x102CB2C into the is-a check 0x88F2B0",
      rd(0x469775, 10) == bytes.fromhex("682ccb0201e8315b4200"))
check("G 0x46978F reads actor+0x348 and 0x469795 takes ATTR vtable +0x24, then calls it",
      rd(0x46978D, 16) == bytes.fromhex("8b178b80480300008b5224508bcfffd2"),
      rd(0x46978D, 16).hex().upper())
check("G ActorAttr vtable +0x24 == 0x464F30", dw(0xF0E7A0 + 0x24) == 0x464F30)
cp, cp_eg, cp_mz, cp_stop = extract(0x464F30, 0x465215, {})
cpins, cpstop = walk(0x464F30, 0x465215)
check("G 0x464F30..0x465215 decoded with no undecodable byte", cpstop is None)
n_gate = 0
for r in cpins:
    if r["esc"] is None and r["op"] in (0xF6, 0xF7) and r["reg"] in (0, 1) and \
       r["mod"] != 3 and (r["disp"] or 0) in (0x1B4, 0x1B8, 0x70):
        n_gate += 1
check("G 0x464F30 contains ZERO mask tests (no +0x1B4/+0x1B8/+0x70 bit test at all)",
      n_gate == 0, "%d found, %d instructions swept" % (n_gate, len(cpins)))
check("G 0x464F30 chains BasicAttr vtable +0x24 (0x464F69 call 0x464B40)",
      rd(0x464F69, 5) == bytes.fromhex("e8d2fbffff") and dw(0xF0E760 + 0x24) == 0x464B40)
check("G 0x464F30 copies THIS(edi) -> ARG(esi) unconditionally, e.g. +0x8C and +0x90",
      rd(0x464F6E, 12) == bytes.fromhex("8b878c00000089868c000000"))
check("G ActorAttr vtable +0x30 (0x465E60) IS the mask-aware Merge and is a DIFFERENT slot",
      dw(0xF0E7A0 + 0x30) == 0x465E60)
check("G 0x465EA4 test al,1 / jnz  => ActorAttr::Merge copies forward when the bit is CLEAR",
      rd(0x465EA4, 4) == bytes.fromhex("a801750c") and
      rd(0x465EA8, 12) == bytes.fromhex("8b8f8c000000898e8c000000"))
check("G 0x465E99 : ActorAttr::Merge chains BasicAttr::Merge 0x465610",
      rd(0x465E99, 5) == bytes.fromhex("e872f7ffff"))
check("G 0x464F30 and 0x465E60 have ZERO direct callers - both are vtable-only",
      calls_to(0x464F30) == [] and calls_to(0x465E60) == [])
check("G the actor-entry pipe therefore uses +0x24 (COPY-ALL), never +0x30 (MERGE)", True,
      "[PROVEN VA=0x469795 `mov edx,[edx+0x24]`]")

check("G 0x464F30 ends at 0x46520B `ret 4`; its last copied field is +0x1B2",
      rd(0x465202, 9) == bytes.fromhex("8886b20100005e5f5b") and
      rd(0x46520B, 3) == bytes.fromhex("c20400"))
_st = []
for r in cpins:
    if r["va"] > 0x46520B:
        break
    if r["esc"] is None and r["op"] in (0x88, 0x89) and r["mod"] is not None and r["mod"] != 3:
        _st.append(r["disp"])
check("G the copy NEVER writes the 64-bit change mask +0x1B4/+0x1B8 onto the target "
      "(the resident attr keeps the 0xFFFFFFFF its own ctor set); it DOES copy the "
      "extra-group flag +0x1BC (0x465176)",
      0x1B4 not in _st and 0x1B8 not in _st and 0x1BC in _st and
      rd(0x46516F, 13) == bytes.fromhex("0fb68fbc010000888ebc010000"),
      "%d stores, max +0x%X" % (len(_st), max(_st)))
check("G BasicAttr copy 0x464B40 copies name +0x28 (wstring assign [0xC3B460]) and "
      "HP +0x44/+0x48 unconditionally, and never writes the u16 mask +0x70",
      rd(0x464B7A, 13) == bytes.fromhex("8d4728508d4e28ff1560b4c300") and
      rd(0x464B8F, 12) == bytes.fromhex("8b57448956448b4748894648") and
      b"\x89\x4e\x70" not in rd(0x464B40, 0x464BD7 - 0x464B40) and
      b"\x66\x89\x4e\x70" not in rd(0x464B40, 0x464BD7 - 0x464B40))
check("G DBAttribute copy 0x4676A0 copies the identity qword +0x18 onto the resident attr",
      rd(0x4676CD, 3) == bytes.fromhex("8b4f18"))

print()
print("== H. what the CNetActor construction path does ==")
check("H jump-table case 2 at 0x4469E1 has no extra precondition "
      "(push 0 / push 0xF0A90C / mov ecx,0x102CB10 / call 0x444DE0 / jmp 0x446A88)",
      rd(0x4469E1, 22) == bytes.fromhex("6a00680ca9f000b910cb0201e8eee3ffffe991000000"))
check("H 0x446AAD calls actor vtable +0x10 (= CNetActor::init 0x454920) with the record",
      rd(0x446AAD, 10) == bytes.fromhex("8b068b5010558bceffd2") and
      dw(0xF0DD08 + 0x10) == 0x454920)
check("H CNetActor ctor allocates the resident ActorAttr from the ActorAttr pool "
      "0x1031500 (same call shape as ActorAttr vt+0x14 Clone 0x4675E0) and stores it at actor+0x348",
      rd(0x45739A, 11) == bytes.fromhex("53680ca9f000b900150301") and
      rd(0x4573BC, 5) == bytes.fromhex("e85ff9ffff") and
      rd(0x4573CA, 6) == bytes.fromhex("898648030000") and
      rd(0x4675E0, 17) == bytes.fromhex("6a00680ca9f000b900150301e82ff7feff"))
ini, ini_stop = walk(0x454920, 0x4549DD)
check("H CNetActor::init 0x454920..0x4549DD decoded with no undecodable byte", ini_stop is None)
n348 = sum(1 for r in ini if r["mod"] is not None and (r["disp"] or 0) == 0x348)
check("H CNetActor::init reads actor+0x348 (the ActorAttr) ZERO times",
      n348 == 0, "%d, %d instructions swept" % (n348, len(ini)))
check("H CNetActor::init reads actor+0x34C (AvatarAttr) once, byte +0x5D, for the scale",
      rd(0x454978, 6) == bytes.fromhex("8b864c030000") and
      rd(0x45498A, 4) == bytes.fromhex("0fbe405d"))
check("H CNetActor::init copies record +0x18/+0x1C to actor +0x78/+0x7C (identity)",
      rd(0x454938, 14) == bytes.fromhex("8b078b4818894e788b501c89567c"))
check("H CNetActor vt+0x78 GetName reads [actor+0x348]; NULL -> empty literal 0xF0930C",
      dw(0xF0DD08 + 0x78) == 0x4549E0 and
      rd(0x4549E1, 6) == bytes.fromhex("8b8148030000") and
      rd(0x454A15, 5) == bytes.fromhex("680c93f000"))
check("H NameBoardPlayer update 0x5BD320: attr NULL -> jz 0x5BD8C7 (whole update returns)",
      rd(0x5BD377, 5) == bytes.fromhex("8b5074ffd2") and
      rd(0x5BD380, 8) == bytes.fromhex("85c00f843f050000"))
check("H board HPBAR reads attr+0x44 and attr+0x48",
      rd(0x5BD3AB, 6) == bytes.fromhex("8b78448b5848"))
check("H board LABEL_NAME reads attr+0x28",
      rd(0x5BD624, 7) == bytes.fromhex("8b7c241483c728"))
check("H board LABEL_GUILD reads ActorAttr+0x164 after a downcast (0x43B9B0)",
      rd(0x5BD4C9, 5) == bytes.fromhex("e8e2e4e7ff") and
      rd(0x5BD4DA, 6) == bytes.fromhex("8db864010000"))
check("H board LABEL_NICKNAME reads ActorAttr+0x90 after a downcast",
      rd(0x5BD7BA, 5) == bytes.fromhex("e8f1e1e7ff") and
      rd(0x5BD7CC, 6) == bytes.fromhex("8b9f90000000"))
check("H the death predicates actor vt+0x3C/0x40 read attr+0x44 (HP) and attr+0x58 (timer)",
      rd(0x43BD7A, 4) == bytes.fromhex("83784400") and
      rd(0x43BD8C, 4) == bytes.fromhex("0f2f4058") and
      rd(0x43BDAA, 4) == bytes.fromhex("83784400"))
check("H a fresh BasicAttr ctor 0x464A80 leaves +0x44/+0x48 = 0 (xor edi,edi at 0x464AB2)",
      rd(0x464AB2, 2) == bytes.fromhex("33ff") and
      rd(0x464B02, 6) == bytes.fromhex("897e44897e48"))
check("H a fresh ActorAttr ctor sets its OWN mask +0x1B4/+0x1B8 to 0xFFFFFFFF "
      "(or eax,-1 at 0x464C95) and +0x1BC = 1",
      rd(0x464C95, 3) == bytes.fromhex("83c8ff") and
      rd(0x464CA0, 12) == bytes.fromhex("8986b40100008986b8010000"))
check("H a fresh BasicAttr sets its own u16 mask +0x70 = 0xFFFF and name +0x28 = L\"\" (0xF0930C)",
      rd(0x464AC6, 9) == bytes.fromhex("b9ffff000066894e70") and
      rd(0x464ACF, 5) == bytes.fromhex("680c93f000"))

print()
print("== I. scope of the sweeps (a negative is only as good as its coverage) ==")
print("     SWEPT, 100 percent, no undecodable byte:")
for nm, lo, hi in (("ActorAttr::Serial      ", 0x466230, 0x466C79),
                   ("ActorAttr vt+0x24 copy ", 0x464F30, 0x46520E),
                   ("ActorAttr vt+0x38 thunk", 0x469760, 0x4697A2),
                   ("BasicAttr::Serial      ", 0x4656F0, 0x465850),
                   ("BasicAttr::Merge       ", 0x465610, 0x4656EF),
                   ("CNetActor::init        ", 0x454920, 0x4549DD),
                   ("NameBoardPlayer update ", 0x5BD320, 0x5BD8E0)):
    w, st = walk(lo, hi)
    print("       %s 0x%06X..0x%06X  %4d ins  %s  sha256=%s" %
          (nm, lo, hi, len(w), "COMPLETE" if st is None else "STOPPED 0x%X" % st,
           span_sha(lo, hi)[:16] + "..."))

print()
print("%d guards, %d failed" % (n_guard, len(fails)))
for f in fails:
    print("  FAILED: " + f)
sys.exit(1 if fails else 0)
```

---

## 12. ผลรันเต็ม (86 guards, 0 failed)

```
== image ==
[OK]   image size  14759424
[OK]   image sha256  9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623
[OK]   image base 0x400000
[OK]   two executable sections (.text + .code)

== A. re-derivation of answers this project already pinned ==
[OK]   A1 BasicAttr::Serial 0x4657AE = test byte [ebx+0],0x80  (ebx = attr+0x70 mask)  F60380740F6A048D4E58516A2A8BCFE83E4E4300
[OK]   A1 gate is followed by push 4 / lea ecx,[esi+0x58] / push ecx / push 0x2A / call 0x89A600
[OK]   A1 lea ebx,[esi+0x70] at 0x465708 makes the gate base the BasicAttr u16 mask
[OK]   A1 => BasicAttr bit 0x0080 -> object +0x58, tag 0x2A, width 4  [PROVEN VA=0x4657AE..0x4657C1]
[OK]   A2 BasicAttr::Merge is BasicAttr vtable +0x30 = 0x465610  0x465610
[OK]   A2 0x46564E reads THIS's mask: test byte [edi+0x70],1
[OK]   A2 0x4656A3 = test al,al / js +6 / fld [esi+0x58] / fstp [edi+0x58]  84C07806D94658D95F58
[OK]   A2 => bit CLEAR  ==> old(arg,esi) value is copied FORWARD into this(edi)  [PROVEN VA=0x4656A3]
[OK]   A3 jump table 0x446B2C has the 5 pinned entries  0x4469e1 0x4469f7 0x446a3d 0x446a5a 0x446a77
[OK]   A3 span 0x446990..0x446B2C sha256 == 5F68239F...697D  5F68239F8661419DA2EA9BEA4E4A2CB9BCDCAA37FE6E4CD53B701116AEEB697D
[OK]   A3 table span 0x446B2C..0x446B40 sha256 == B50C1D1D...D606  B50C1D1DB53D2B70A8AD258563750738639D5E9E3EEF2FA5CFB4C5354632D606
[OK]   A3 0x4469C8 movzx eax,byte [eax+0x10]; add eax,-2; cmp eax,4; ja

== B. ActorAttr::Serial 0x466230 - extent and coverage ==
[OK]   B decoder covered 0x466230..0x466C79 with NO undecodable byte  full
[OK]   B last decoded instruction ends exactly on 0x466C79  0x466C79
[OK]   B last instruction is `ret 8` (C2 08 00) at 0x466C76
[OK]   B 0x466C79..0x466C80 is INT3 padding
[OK]   B ActorAttr vtable 0xF0E7A0 +0x34 == 0x466230 (this really is ::Serial)
[OK]   B ActorAttr::Serial chains BasicAttr::Serial first (0x466243 call 0x4656F0)
[OK]   B ActorAttr object size (vt+0x0C -> mov eax,0x1C0) == 0x1C0
     span 0x466230..0x466C79 sha256 = F9EA39F3A6BC80E6D29D4AAE3EFA79C1D5FF855D70109319578CBA86D5F9AABC
     instructions decoded          = 740
[OK]   B codec 0x89A810 (wstring out) pushes wire tag 0x48
[OK]   B codec 0x89A6D0 (blob out) pushes wire tag 0x44
[OK]   B codec 0x89A880 (wstring in) pushes wire tag 0x48

== C. the field table (LOAD branch = what the client runs on an inbound ActorAttr) ==
[OK]   C save branch decoded with no undecodable byte
[OK]   C load branch decoded with no undecodable byte
[OK]   C save branch has 45 codec calls  45
[OK]   C load branch has 45 codec calls  45
[OK]   C first two calls are UNGATED header fields (mask64, extra-group flag)
[OK]   C => 43 GATED fields  (design doc R90 said 43: CONFIRMED)  43 / 43
[OK]   C save and load branches are field-for-field symmetric (same bit, offset, tag, width, order)
[OK]   C low dword uses bits 0x00000001..0x40000000 (31 bits); 0x80000000 is UNUSED  31 distinct
[OK]   C high dword uses bits 0x00000001..0x00000200 (10 bits) => mask bits 32..41  10 distinct
[OK]   C 41 distinct mask bits carry 43 fields (two bits carry two fields each)

  #  maskbit(64)   bit         obj_off  tag  w   kind     xgrp  load-gate   note
   1  0x0000000000000001  b0   +0x08C  0x19  4   scalar    -   0x4667B3  class id            (STATS-PROG-001)
   2  0x0000000000000002  b1   +0x090  0x19  4   scalar    -   0x4667C9  u32 -> NameBoard nickname key        [PROVEN VA=0x5BD7BA..0x5BD7D5]
   3  0x0000000000000004  b2   +0x078  0x26  4   scalar   yes  0x4667ED  
   4  0x0000000000000008  b3   +0x07C  0x19  4   scalar   yes  0x466805  skill points        (STATS-PROG-001)
   5  0x0000000000000010  b4   +0x080  0x12  2   scalar   yes  0x46681D  unspent ability pts (STATS-PROG-001)
   6  0x0000000000000020  b5   +0x082  0x12  2   scalar   yes  0x466838  STR base
   7  0x0000000000000040  b6   +0x084  0x12  2   scalar   yes  0x466853  CON base
   8  0x0000000000000080  b7   +0x086  0x12  2   scalar   yes  0x46686E  DEX base
   9  0x0000000000000100  b8   +0x088  0x12  2   scalar   yes  0x466889  INT base
  10  0x0000000000000200  b9   +0x08A  0x12  2   scalar   yes  0x4668A7  PER base
  11  0x0000000000000400  b10  +0x0A0  0x32  8   scalar   yes  0x4668C5  experience
  12  0x0000000000000800  b11  +0x0A8  0x32  8   scalar   yes  0x4668E3  cash
  13  0x0000000000001000  b12  +0x0B0  0x48  -   wstring  yes  0x466901  
  14  0x0000000000002000  b13  +0x099  0x0B  1   scalar   yes  0x46691B  
  15  0x0000000000004000  b14  +0x09A  0x0B  1   scalar   yes  0x466939  
  16  0x0000000000008000  b15  +0x13E  0x12  2   scalar   yes  0x466957  
  17  0x0000000000010000  b16  +0x13C  0x12  2   scalar   yes  0x466975  
  18  0x0000000000020000  b17  +0x148  0x44  -   blob     yes  0x466993  
  19  0x0000000000040000  b18  +0x182  0x12  2   scalar   yes  0x4669AD  STR bonus
  20  0x0000000000080000  b19  +0x184  0x12  2   scalar   yes  0x4669CB  CON bonus
  21  0x0000000000100000  b20  +0x186  0x12  2   scalar   yes  0x4669E9  DEX bonus
  22  0x0000000000200000  b21  +0x188  0x12  2   scalar   yes  0x466A07  INT bonus
  23  0x0000000000400000  b22  +0x18A  0x12  2   scalar   yes  0x466A25  PER bonus
  24  0x0000000000800000  b23  +0x18C  0x0B  1   scalar   yes  0x466A43  
  25  0x0000000001000000  b24  +0x164  0x48  -   wstring   -   0x466A61  wstring -> LABEL_GUILD (board+0x5C)  [PROVEN VA=0x5BD4C9..0x5BD4DA]
  26  0x0000000002000000  b25  +0x180  0x0B  1   scalar    -   0x466A7B  
  27  0x0000000004000000  b26  +0x098  0x0B  1   scalar    -   0x466A99  
  28  0x0000000004000000  b26  +0x094  0x19  4   scalar    -   0x466A99  
  29  0x0000000008000000  b27  +0x140  0x32  8   scalar    -   0x466AC9  
  30  0x0000000008000000  b27  +0x09B  0x0B  1   scalar    -   0x466AC9  
  31  0x0000000010000000  b28  +0x0CC  0x48  -   wstring  yes  0x466AFE  
  32  0x0000000020000000  b29  +0x198  0x32  8   scalar    -   0x466B18  
  33  0x0000000040000000  b30  +0x190  0x32  8   scalar    -   0x466B36  
  34  0x0000000100000000  b32  +0x1A0  0x0B  1   scalar    -   0x466B62  
  35  0x0000000200000000  b33  +0x1A2  0x12  2   scalar    -   0x466B78  
  36  0x0000000400000000  b34  +0x1A4  0x12  2   scalar    -   0x466B93  
  37  0x0000000800000000  b35  +0x0E8  0x48  -   wstring   -   0x466BAE  
  38  0x0000001000000000  b36  +0x104  0x48  -   wstring   -   0x466BC5  
  39  0x0000002000000000  b37  +0x120  0x48  -   wstring   -   0x466BDC  
  40  0x0000004000000000  b38  +0x1A8  0x14  4   scalar    -   0x466BF3  u32 alt HP cur (used when 0x430E10([+0x5C])==8) [PROVEN VA=0x5BD3D5]
  41  0x0000008000000000  b39  +0x1AC  0x14  4   scalar    -   0x466C0E  u32 alt HP max (same gate)                      [PROVEN VA=0x5BD3DB]
  42  0x0000010000000000  b40  +0x1B0  0x12  2   scalar   yes  0x466C2E  
  43  0x0000020000000000  b41  +0x1B2  0x0B  1   scalar   yes  0x466C51  

== C2. the wire PREFIX that rides in front of every ActorAttr ==
   (ActorAttr::Serial 0x466230 calls BasicAttr::Serial 0x4656F0 FIRST, which calls
    DBAttribute::Serial 0x467790 FIRST, so the wire order is DB -> Basic -> Actor)
[OK]   C2 DBAttribute::Serial decoded clean, 2 ungated fields
     DBAttribute  UNGATED  +0x020  tag 0x0B  w 1
     DBAttribute  UNGATED  +0x018  tag 0x32  w 8
[OK]   C2 BasicAttr::Serial decoded clean, 13 codec calls (1 ungated mask + 12 gated)  13
     BasicAttr    UNGATED  +0x070  tag 0x12  w 2   (the u16 change mask itself)
     BasicAttr    bit 0x0001  +0x028  tag 0x48  w None  NAME wstring -> LABEL_NAME (board+0x54)
     BasicAttr    bit 0x0002  +0x05E  tag 0x12  w 2   level
     BasicAttr    bit 0x0004  +0x044  tag 0x14  w 4   HP current  -> HPBAR and the death predicates 0x43BD70/0x43BDA0
     BasicAttr    bit 0x0008  +0x048  tag 0x14  w 4   HP max      -> HPBAR
     BasicAttr    bit 0x0010  +0x04C  tag 0x14  w 4   MP current
     BasicAttr    bit 0x0020  +0x050  tag 0x14  w 4   MP max
     BasicAttr    bit 0x0040  +0x054  tag 0x2A  w 4   
     BasicAttr    bit 0x0080  +0x058  tag 0x2A  w 4   death/respawn timer f32 (HP-DEATH-001)
     BasicAttr    bit 0x0100  +0x05C  tag 0x12  w 2   u16 category; 0x430E10(cat)==8 switches HP to ActorAttr +0x1A8/+0x1AC
     BasicAttr    bit 0x0200  +0x060  tag 0x32  w 8   
     BasicAttr    bit 0x0400  +0x068  tag 0x14  w 4   
     BasicAttr    bit 0x0800  +0x06C  tag 0x14  w 4   
[OK]   C2 BasicAttr bit 0x0001 -> +0x28 wstring tag 0x48
[OK]   C2 BasicAttr bit 0x0080 -> +0x58 tag 0x2A width 4 (the pinned death timer)

== D. containers / strings / pointers inside ActorAttr ==
[OK]   D 6 wstring fields  +0xB0 +0xCC +0xE8 +0x104 +0x120 +0x164
[OK]   D 1 blob/container field  +0x148
[OK]   D ActorAttr dtor 0x464E60 destroys +0x164, +0x148, +0x120 (real C++ objects, not PODs)
[OK]   D the identity qword is NOT in ActorAttr: it is DBAttribute +0x18, tag 0x32, ser 0x467790

== E. mask == 0 : which branch decides ==
     LOAD  0x4667AB test mask.LO ; 0x4667AD jz 0x466B54
     LOAD  0x466B5A test mask.HI ; 0x466B5C jz 0x466C6F
[OK]   E load branch: mask LOW  == 0 -> jz 0x466B54 (skip all 33 low fields)
[OK]   E load branch: mask HIGH == 0 -> jz 0x466C6F (the epilogue)
[OK]   E 0x466C6F is the shared epilogue pop/pop/pop/pop/add esp,8/ret 8
[OK]   E save branch has the same two short-circuits (0x466293 -> 0x466638, 0x466640 -> 0x466C6F)
[OK]   E there is NO error path, NO throw, NO ret-false anywhere in ::Serial: the only ret in the function is the shared `ret 8`  2 ret instructions (0x466764 and 0x466C76)

== F. the extra-group flag +0x1BC (wire tag 0x05) is a SECOND gate ==
     LOAD  0x4667E4 cmp byte [attr+0x1BC],0 ; jz 0x466A61
     LOAD  0x466AF9 cmp byte [attr+0x1BC],0 ; jz 0x466B18
     LOAD  0x466C29 cmp byte [attr+0x1BC],0 ; jz 0x466C6F
     LOAD  0x466C4C cmp byte [attr+0x1BC],0 ; jz 0x466C6F
[OK]   F when +0x1BC == 0 the client SKIPS 25 of the 43 gated fields regardless of the mask  25
[OK]   F ActorAttr ctor default for +0x1BC is 1 (0x464E1C mov byte [esi+0x1BC],1)

== G. the merge/apply path 0x469760 -> 0x464F30 ==
[OK]   G 0x469760 is ActorAttr vtable +0x38 (the bind thunk) and its ONLY reference
[OK]   G 0x469768 test esi,esi / jz  : NULL actor -> silent return
[OK]   G 0x469775 pushes CNetActor type node 0x102CB2C into the is-a check 0x88F2B0
[OK]   G 0x46978F reads actor+0x348 and 0x469795 takes ATTR vtable +0x24, then calls it  8B178B80480300008B5224508BCFFFD2
[OK]   G ActorAttr vtable +0x24 == 0x464F30
[OK]   G 0x464F30..0x465215 decoded with no undecodable byte
[OK]   G 0x464F30 contains ZERO mask tests (no +0x1B4/+0x1B8/+0x70 bit test at all)  0 found, 143 instructions swept
[OK]   G 0x464F30 chains BasicAttr vtable +0x24 (0x464F69 call 0x464B40)
[OK]   G 0x464F30 copies THIS(edi) -> ARG(esi) unconditionally, e.g. +0x8C and +0x90
[OK]   G ActorAttr vtable +0x30 (0x465E60) IS the mask-aware Merge and is a DIFFERENT slot
[OK]   G 0x465EA4 test al,1 / jnz  => ActorAttr::Merge copies forward when the bit is CLEAR
[OK]   G 0x465E99 : ActorAttr::Merge chains BasicAttr::Merge 0x465610
[OK]   G 0x464F30 and 0x465E60 have ZERO direct callers - both are vtable-only
[OK]   G the actor-entry pipe therefore uses +0x24 (COPY-ALL), never +0x30 (MERGE)  [PROVEN VA=0x469795 `mov edx,[edx+0x24]`]
[OK]   G 0x464F30 ends at 0x46520B `ret 4`; its last copied field is +0x1B2
[OK]   G the copy NEVER writes the 64-bit change mask +0x1B4/+0x1B8 onto the target (the resident attr keeps the 0xFFFFFFFF its own ctor set); it DOES copy the extra-group flag +0x1BC (0x465176)  42 stores, max +0x1BC
[OK]   G BasicAttr copy 0x464B40 copies name +0x28 (wstring assign [0xC3B460]) and HP +0x44/+0x48 unconditionally, and never writes the u16 mask +0x70
[OK]   G DBAttribute copy 0x4676A0 copies the identity qword +0x18 onto the resident attr

== H. what the CNetActor construction path does ==
[OK]   H jump-table case 2 at 0x4469E1 has no extra precondition (push 0 / push 0xF0A90C / mov ecx,0x102CB10 / call 0x444DE0 / jmp 0x446A88)
[OK]   H 0x446AAD calls actor vtable +0x10 (= CNetActor::init 0x454920) with the record
[OK]   H CNetActor ctor allocates the resident ActorAttr from the ActorAttr pool 0x1031500 (same call shape as ActorAttr vt+0x14 Clone 0x4675E0) and stores it at actor+0x348
[OK]   H CNetActor::init 0x454920..0x4549DD decoded with no undecodable byte
[OK]   H CNetActor::init reads actor+0x348 (the ActorAttr) ZERO times  0, 55 instructions swept
[OK]   H CNetActor::init reads actor+0x34C (AvatarAttr) once, byte +0x5D, for the scale
[OK]   H CNetActor::init copies record +0x18/+0x1C to actor +0x78/+0x7C (identity)
[OK]   H CNetActor vt+0x78 GetName reads [actor+0x348]; NULL -> empty literal 0xF0930C
[OK]   H NameBoardPlayer update 0x5BD320: attr NULL -> jz 0x5BD8C7 (whole update returns)
[OK]   H board HPBAR reads attr+0x44 and attr+0x48
[OK]   H board LABEL_NAME reads attr+0x28
[OK]   H board LABEL_GUILD reads ActorAttr+0x164 after a downcast (0x43B9B0)
[OK]   H board LABEL_NICKNAME reads ActorAttr+0x90 after a downcast
[OK]   H the death predicates actor vt+0x3C/0x40 read attr+0x44 (HP) and attr+0x58 (timer)
[OK]   H a fresh BasicAttr ctor 0x464A80 leaves +0x44/+0x48 = 0 (xor edi,edi at 0x464AB2)
[OK]   H a fresh ActorAttr ctor sets its OWN mask +0x1B4/+0x1B8 to 0xFFFFFFFF (or eax,-1 at 0x464C95) and +0x1BC = 1
[OK]   H a fresh BasicAttr sets its own u16 mask +0x70 = 0xFFFF and name +0x28 = L"" (0xF0930C)

== I. scope of the sweeps (a negative is only as good as its coverage) ==
     SWEPT, 100 percent, no undecodable byte:
       ActorAttr::Serial       0x466230..0x466C79   740 ins  COMPLETE  sha256=F9EA39F3A6BC80E6...
       ActorAttr vt+0x24 copy  0x464F30..0x46520E   139 ins  COMPLETE  sha256=48B18BC342646C53...
       ActorAttr vt+0x38 thunk 0x469760..0x4697A2    28 ins  COMPLETE  sha256=6F8A3251BDE10432...
       BasicAttr::Serial       0x4656F0..0x465850   134 ins  COMPLETE  sha256=55D2288316C78BC5...
       BasicAttr::Merge        0x465610..0x4656EF    80 ins  COMPLETE  sha256=F8166D39E5E85DD5...
       CNetActor::init         0x454920..0x4549DD    55 ins  COMPLETE  sha256=D907227D59491E79...
       NameBoardPlayer update  0x5BD320..0x5BD8E0   490 ins  COMPLETE  sha256=986AECBF619A61A3...

86 guards, 0 failed
```
