<!-- Imported into reports/ by chief round 96 (2026-08-20) from pf_bridge/drafts/CHUNK2_Q3_BIND_THUNK_FINDINGS.md
     (round 90 static RE lane worker output), byte-for-byte below this header.
     Reason: EVIDENCE-VISIBLE-001 discipline - the HYP-PF-025 ledger entry and the
     REMOTE-PLAYER-ENCODER-001 report cite these findings, and a citation must resolve
     inside the repository, not on one author's machine. -->

# CHUNK2 Q3 — bind thunk `+0x38` (ROW 5) + dead-sync `0x4437C0` sweep (ROW 13)

Date: 2026-08-19 · lane: static RE (read-only) · ปิด **ROW 5** ของ
`drafts/MULTIPLAYER_CHUNK2_VISIBILITY_DESIGN_R90.md` §10 และ **ROW 13** ตามที่เวลาอนุญาต

ไบนารีเดียวที่อ่าน (อ่านอย่างเดียว ไม่แก้ ไม่คัดลอกเข้าทรี):
`GameClient/GameClient.local.bin` · size `14759424`
SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`

ไม่แตะ `Pirate Force ServerProject/` เลยแม้แต่ไบต์เดียว · ไม่บูตเซิร์ฟเวอร์ · ไม่เปิด GameClient ·
ไม่แตะ git index · ไม่มี capstone ไม่มี pefile — stdlib python3 ล้วน (ลอกโครง helper จาก
`tools/pf_runtimeres_actor_entry_static.py`: `va2off` / section walking / opcode matching / span hashing)

**ป้ายกำกับ**

| ป้าย | ความหมาย |
|---|---|
| `[PROVEN VA=0x...]` | ปักที่ไบต์จริงในอิมเมจ มี span+sha ให้ re-pin ได้ |
| `[INFERRED]` | อนุมานจากรูปร่างของโค้ด + ข้อ PROVEN — สร้างต่อได้ แต่ต้องเขียนว่าอนุมาน |
| `[GUESS]` | เดา ไม่มีไบต์รองรับ |

---

## 0. สรุปหนึ่งย่อหน้า — คำตอบของ ROW 5

**MERGE ไม่ใช่ bind-over — แต่เป็น "merge" ที่ทับทุกฟิลด์ ไม่ใช่ merge แบบดู mask**
thunk `+0x38` **ไม่เคยเขียนพอยน์เตอร์ปลายทางเลยแม้แต่ครั้งเดียว** มันแค่ *อ่าน* พอยน์เตอร์นั้นออกมา
แล้วส่งเข้าเป็น **argument ของ `attr->vtable[+0x24]`** ซึ่งเป็น **`CopyTo(dst)`** — คัดลอกฟิลด์ค่า
ทุกฟิลด์ของ `this` (ก้อนที่เพิ่งถอดจากสาย) ทับลงบน `dst` (ก้อนที่ actor ถืออยู่แล้วตั้งแต่ ctor)
`[PROVEN VA=0x46978D..0x46979C, 0x464F30, 0x464B40, 0x465450]`
ดังนั้น: **ข้อความที่สองเรื่อง identity เดิม = อัปเดตของเดิม ไม่ทิ้งวัตถุเดิม ไม่ leak ไม่ free ไม่มี refcount**
เพราะ **ไม่มีการเปลี่ยนพอยน์เตอร์เกิดขึ้นเลย** — สิ่งที่หายไปคือ *ค่า* ไม่ใช่ *วัตถุ*
**แต่** และนี่คือส่วนที่ยังไม่เคยมีใครเขียนไว้: `CopyTo` **ไม่ดู mask** ทุกฟิลด์ถูกทับหมด
รวมทั้งฟิลด์ที่ข้อความที่สอง **ไม่ได้ส่ง** (ฟิลด์พวกนั้นจะได้ค่า default ของ ctor ของก้อนขาเข้าแทน)
merge แบบ mask-gated ที่ MOVE-PROJECT-001 อ่านไว้ (`0x467130`) กับ `BasicAttr::Merge 0x465610`
อยู่ที่ **vtable `+0x30` ไม่ใช่ `+0x24`** และ **ไม่มีจุดไหนในท่อ actor-entry เรียกมันเลย**

---

## 1. (a) ถอด `je` ทั้งสองข้าง

thunk มี `je` **สองตัว ไม่ใช่ตัวเดียว** และทั้งคู่กระโดดไป epilogue จุดเดียวกัน

### 1.1 disassembly เต็มของ `0x469760` (`ActorAttr::vtable +0x38`) `[PROVEN VA=0x469760..0x4697A1]`

```
00469760  56                    push  esi
00469761  8b 74 24 08           mov   esi,[esp+8]        ; esi = arg0 = the ACTOR
00469765  57                    push  edi
00469766  8b f9                 mov   edi,ecx            ; edi = this = the INCOMING attr
00469768  85 f6                 test  esi,esi
0046976A  74 31                 je    0046979D           ; *** je #1 ***  actor == NULL
0046976C  8b 06                 mov   eax,[esi]          ; actor vtable
0046976E  8b 10                 mov   edx,[eax]          ; actor vtable[+0x00] = GetTypeNode
00469770  8b ce                 mov   ecx,esi
00469772  ff d2                 call  edx
00469774  50                    push  eax
00469775  68 2c cb 02 01        push  0x0102CB2C         ; gate token = CNetActor
0046977A  e8 31 5b 42 00        call  0x0088F2B0         ; is_a(node, token) -> al
0046977F  0f b6 c0              movzx eax,al
00469782  83 c4 08              add   esp,8
00469785  f7 d8                 neg   eax
00469787  1b c0                 sbb   eax,eax            ; eax = is_a ? 0xFFFFFFFF : 0
00469789  23 c6                 and   eax,esi            ; eax = is_a ? actor : 0
0046978B  74 10                 je    0046979D           ; *** je #2 ***  not an instance
0046978D  8b 17                 mov   edx,[edi]          ; INCOMING attr vtable
0046978F  8b 80 48 03 00 00     mov   eax,[eax+0x348]    ; *** LOAD *** actor->m_pActorAttr
00469795  8b 52 24              mov   edx,[edx+0x24]     ; incoming->vtable[+0x24]
00469798  50                    push  eax                ; arg = the ALREADY-BOUND object
00469799  8b cf                 mov   ecx,edi            ; this = the incoming attr
0046979B  ff d2                 call  edx                ; incoming->CopyTo(existing)
0046979D  5f                    pop   edi
0046979E  5e                    pop   esi
0046979F  c2 04 00              ret   4
```

**หัวใจอยู่ที่ `0x46978F`: opcode คือ `8B` = `mov r32, r/m32` = LOAD ไม่ใช่ `89` = STORE**
`[actor+0x348]` **ถูกอ่าน** ไม่ถูกเขียน `[PROVEN VA=0x46978F]`
span `0x46978D..0x4697A1` = `8b178b80480300008b5224508bcfffd25f5ec20400`

### 1.2 เงื่อนไขและกิ่ง — ประโยคที่โปรแกรมเมอร์เอาไปเขียนโค้ดได้เลย

| `je` | VA | เงื่อนไข (จริง = กระโดด) | กิ่งกระโดด (taken) | กิ่งตก (fall-through) |
|---|---|---|---|---|
| #1 | `0x46976A` | `arg0 (the actor pointer) == NULL` | ออกทันที `ret 4` — **ไม่แตะ destination pointer** | ไปตรวจ is-a ต่อ |
| #2 | `0x46978B` | `is_a(actor, GATE_TOKEN) == false` | ออกทันที `ret 4` — **ไม่แตะ destination pointer** | โหลด `[actor+FIELD]` แล้วเรียก `+0x24` |

**pseudo-code ที่ implement ได้ทันที** `[PROVEN VA=0x469760..0x4697A1]`

```c
/* attr vtable +0x38 : "bind" thunk. __thiscall, stdcall-cleanup, ret 4 */
void Attr_BindToActor(Attr *this, CActorBaseClient *actor)
{
    if (actor == NULL) return;                       /* je #1 @0x46976A */
    if (!is_a(actor->GetTypeNode(), GATE_TOKEN))     /* je #2 @0x46978B */
        return;
    /* NOTE: the destination FIELD is never assigned.  It is only read. */
    Attr *existing = *(Attr **)((char*)actor + FIELD_OFF);   /* 0x46978F, a LOAD */
    this->vtable[0x24 / 4](this, existing);          /* CopyTo(existing) */
}
```

และ `+0x24` เอง `[PROVEN VA=0x464F30 / 0x464B40 / 0x465450 / 0x4676A0]`

```c
/* attr vtable +0x24 : CopyTo(dst).  `this` is the SOURCE, the argument is the DEST. */
void Attr_CopyTo(Attr *this, Attr *dst)
{
    if (dst == NULL) return;                         /* 0x464F3A / 0x464B4A / 0x46545A */
    if (!is_a(dst->GetTypeNode(), MY_CLASS_TOKEN))   /* 0x464F60 / 0x464B70 / 0x46547C */
        return;
    base_CopyTo(this, dst);                          /* 0x4676A0 : +0x18,+0x1C,+0x12 */
    /* then EVERY value field, one by one, with NO mask test at all. */
    /* the change mask itself is NOT copied. */
}
```

**ทิศทาง `this -> arg` พิสูจน์ที่ไบต์** — คู่ load/store คู่แรกของ `ActorAttr::CopyTo`:
```
00464F6E  8b 87 8c 00 00 00     mov eax,[edi+0x8C]     ; edi = this   (source)
00464F74  89 86 8c 00 00 00     mov [esi+0x8C],eax     ; esi = arg    (destination)
```
`[PROVEN VA=0x464F6E..0x464F79]` — ทุกคู่ในฟังก์ชันเป็นรูปนี้หมดตลอด `0x464F6E..0x465205`

**ไม่มี mask test เลยใน `+0x24`** — sweep ทั้งสามตัวหาไบต์ `f6 47 70` / `0f b7 47 70` / `a8 xx` ที่ตามหลัง
mask load: **0 hit** ใน `0x464B40..0x464BD5`, **0 hit** ใน `0x464F30..0x465205`, **0 hit** ใน `0x465450..0x4654B5`
(hit ที่เครื่องมือรายงานเป็น `0f b7 8f/97 <disp32>` = การโหลด word ฟิลด์ธรรมดา ไม่ใช่ mask — ตรวจด้วยตาแล้ว)

**mask ไม่เคยถูกคัดลอก** `[PROVEN]`

| class | ฟิลด์สุดท้ายที่ CopyTo คัดลอก | mask อยู่ที่ | คัดลอก mask ไหม |
|---|---|---|---|
| `BasicAttr` `0x464B40` | `+0x6C` (`0x464BCF`) | word `+0x70` | **ไม่** |
| `ActorAttr` `0x464F30` | byte `+0x1B2` (`0x4651F9`) | qword `+0x1B4` (`ActorAttr::Serial 0x466253` อ่าน `[esi+0x1B4]/[esi+0x1B8]` แล้วเขียน tag `0x32`) | **ไม่** |
| `MovementAttr` `0x465450` | f32 `+0x48` (`0x4654AF`) | u8 `+0x4C` | **ไม่** |

### 1.3 รายการฟิลด์ที่ถูกทับจริง (สำหรับคนที่ต้องคำนวณผลของเฟรมที่สอง)

* `Attr` base `0x4676A0`: dword `+0x18`, dword `+0x1C` (= identity qword ที่ `bind_common_attr_identity` เขียน), byte `+0x12`
* `BasicAttr` `0x464B40`: wstring `+0x28` (ชื่อ), word `+0x5E` (level), dword `+0x44` (**HP**), `+0x48`, `+0x4C`, `+0x50`,
  f32 `+0x54`, **f32 `+0x58` (death timer)**, word `+0x5C`, dword `+0x60`, `+0x64`, `+0x68`, `+0x6C`
* `MovementAttr` `0x465450`: qword `+0x28` (pos xy), dword `+0x30` (pos z), f32 `+0x34` (heading), byte `+0x38` (mode),
  **dword `+0x3C` (flags)**, f32 `+0x40`, `+0x44`, `+0x48`
* `ActorAttr` `0x464F30`: เรียก `BasicAttr::CopyTo` ก่อน แล้วคัดลอกฟิลด์ของตัวเองอีก ~50 ฟิลด์ ตั้งแต่ `+0x78` ถึง `+0x1B2`
  (รวม wstring 5 ก้อนที่ `+0xB0`, `+0xCC`, `+0xE8`, `+0x104`, `+0x120`, `+0x148`, `+0x164`)

**ผลปฏิบัติการที่ตามมาทันที `[INFERRED]` (จากข้อ PROVEN ข้างบนล้วน ๆ):**
เฟรมที่สองที่ส่ง `MovementAttr` mask `0x01` (ตำแหน่งอย่างเดียว) จะทำให้ `+0x34/+0x38/+0x3C/+0x40/+0x44/+0x48`
ของ actor **ถูกทับด้วยค่า default ของก้อนขาเข้า** ไม่ใช่ "คงค่าเดิมไว้"
docstring ของ `make_remote_movement_attr` ที่เขียนว่า *"the client can merge a position delta without
overwriting the existing locomotion/control fields"* จึงเป็น **คำอธิบายของ `0x467130` (vt `+0x30`)
ซึ่งท่อนี้ไม่ได้เรียก** — ดูข้อ 4.3

---

## 2. (b) thunk ทั้งห้า — byte-identical จริงไหม, VA ไหน, slot ไหน, class ไหน

### 2.1 ข้อแรก: **คำว่า "byte-identical" ในเอกสาร R90 ROW 5 ไม่ถูก**

พิสูจน์: sweep prologue shape `56 8b 74 24 08 57 8b f9 85 f6 74` ทั่ว **ทั้งสอง executable section**
(`.text` 0x838A2C ไบต์ + `.code` 0x2E1 ไบต์) ได้ **72 hit** จากนั้นเทียบกับ template ยาว `0x42`
ที่ mask ทิ้งเฉพาะ 3 ช่องอิมมีเดียต → **match แค่ 4 ตัว** `[PROVEN]`

* thunk 4 ตัว (`0x469760`, `0x4697B0`, `0x469800`, `0x4698B0`) **ไม่ byte-identical** — ต่างกันจริง แต่ต่างเฉพาะ 3 ช่อง:
  gate-token imm32 (`+0x15..+0x18`), rel32 ของ `call 0x88F2B0` (`+0x1A..+0x1D`), field disp32 (`+0x31..+0x34`)
  diff index ที่วัดได้: `0x4697B0` = `[22,23,27,28,49]` · `0x469800` = `[22,23,27,28,49,50]` · `0x4698B0` = `[22,27,28,49]`
  **ทุก index อยู่ใน 3 ช่องนั้นครบ 100%**
* thunk ตัวที่ห้า `0x469850` (`AvatarAttr`) **เป็นฟังก์ชันคนละตัว** ยาว `0x5E` ไม่ใช่ `0x42`
  มี is-a check **สองรอบ** (`CNetActor` แล้ว `CAvatarNPC`) และ **ไม่เรียก `+0x24` เลย** —
  มันเรียก **actor vtable `+0x80`** พร้อมส่ง incoming attr เป็น argument (`0x46989E..0x4698A8`)
  `[PROVEN VA=0x469850..0x4698AD]`

**canonical hash** (zero ทั้ง 3 ช่องอิมมีเดียตแล้ว sha256 span `0x42`):
`4106599f09230f8be10376630d32df65fad86856ed365332aebe02d88fa218a8` — **เท่ากันทั้ง 4 ตัว**
`0x469850` canonical = `493898ceb69facbfc44d34f42a43bdb2cccfd6e34bb0b87815432f5250b9ec38` — **ไม่เท่า**

### 2.2 ตาราง 5 thunk — VA / slot / class / field / hash

| # | thunk VA | span | sha256 (span) | vtable slot ที่ชี้มา | attr class | wire id | gate token / class | ปลายทางที่ถูก "merge เข้าไป" |
|---|---|---|---|---|---|---|---|---|
| 1 | `0x469760` | `0x469760..0x4697A1` (0x42) | `6f8a3251bde10432e1352a93e082937957be89bff8f6aa28bfcec8b43a48aec1` | `0xF0E7D8` = vt `0xF0E7A0` `+0x38` | **`ActorAttr`** | `0x12AD` | `0x102CB2C` `CNetActor` | `[actor+0x348]` |
| 2 | `0x4697B0` | `0x4697B0..0x4697F1` (0x42) | `be9bbd866c5eaebe5fed173106049710cd39abc9e4239e63a877087e433aba6a` | `0xF0E818` = vt `0xF0E7E0` `+0x38` | **`NPCAttr`** | `0x0AD5` | `0x102D954` `CNetNPC` | `[actor+0x358]` |
| 3 | `0x469800` | `0x469800..0x469841` (0x42) | `533f517c045c53d6ee7e33249a2836e0b7b1c2536a0feabbd11ed17f34c59ce7` | `0xF0D130` = vt `0xF0D0F8` `+0x38` | **`MovementAttr`** | `0x2067` | `0x102CE88` `CActorBaseClient` | `[actor+0x244]` |
| 4 | `0x4698B0` | `0x4698B0..0x4698F1` (0x42) | `8faf7ce6e971b9a0a35bd1e7c13ceb09d0b3d4789cd188cbc1e75541d5d104e3` | `0xF48BB0` = vt `0xF48B78` `+0x38` | **`CSkillAttr`** | `0x1661` | `0x102CB04` `CMyActor` | `[actor+0x3E8]` |
| 5 | `0x469850` | `0x469850..0x4698AD` (0x5E) | `9b141be64a7e4ea84de514deaf0532588fd05dc4bb97dc99f931d13703c5622e` | `0xF0E0C0` = vt `0xF0E088` `+0x38` | **`AvatarAttr`** | `0x16A0` | `0x102CB2C` **หรือ** `0x102D92C` | **actor vtable `+0x80`** (ไม่ใช่ฟิลด์ตรง) |

`[PROVEN VA=` ทุกช่องในตารางนี้ `]` — vtable slot มาจากสำมะโน dword ทั่วทั้งไฟล์ทุก alignment

**สำมะโนทางเข้าของแต่ละ thunk (ทั้งไฟล์ 14,759,424 ไบต์ ทุก alignment):**

| thunk | dword occurrence ทั้งไฟล์ | `E8` direct call | `E9` tail jmp |
|---|---|---|---|
| `0x469760` | **1** (= `0xF0E7D8`) | 0 | 0 |
| `0x4697B0` | **1** (= `0xF0E818`) | 0 | 0 |
| `0x469800` | **1** (= `0xF0D130`) | 0 | 0 |
| `0x469850` | **1** (= `0xF0E0C0`) | 0 | 0 |
| `0x4698B0` | **1** (= `0xF48BB0`) | 0 | 0 |
| `0x73D360` (`BasicAttr`) | **2020** | 75 | 1 |

⇒ thunk ทั้งห้า **มีทางเข้าเดียวคือ vtable `+0x38`** และแต่ละตัวเป็นของ class เดียว ไม่แชร์กัน `[PROVEN]`
ส่วน `0x73D360` คือ `c2 04 00` (`ret 4`) เปล่า ๆ ที่ **2020 vtable** ใช้ร่วมกัน — เป็น default ของทั้ง framework
ไม่ใช่ "BasicAttr เลือกจะไม่ผูก" `[PROVEN VA=0x73D360]` (แก้ถ้อยคำของ MPAUDIT-FOLLOWUP-001 §3 เล็กน้อย)

### 2.3 ใครเรียก `+0x38` — และเรียกกี่ครั้ง

`0x5DF080` (apply loop) วนทุก attr ในเวกเตอร์ของ record แล้วเรียก **`attr->vtable[+0x38](actor)`**
`[PROVEN VA=0x5DF0B5..0x5DF0BC]` = `8b 01 / 8b 50 38 / 53 / ff d2`
`this` = attr ที่เพิ่งถอดจากสาย, argument = actor ⇒ ยืนยันว่า `this` ในข้อ 1 คือก้อนขาเข้าจริง
span `0x5DF080..0x5DF0D3` sha256 `e44d45fab0d5964a0f2eab2aa65f56be99865f108763f3827ecaf0c1a83f1c67`

สำมะโน vtable-dispatch offset ในฟังก์ชันของท่อ actor-entry ทั้งหมด (shape `mov r,[reg+disp8] ... call r`):

| ฟังก์ชัน | offset ที่ dispatch |
|---|---|
| `0x5E4060` inbound | (ไม่มี) |
| `0x446F30` reconcile | `+0x20` |
| `0x446990` factory | `+0x10` |
| `0x4446F0` update | `+0x24` (บน **actor** vtable ไม่ใช่ attr — ดู 4.4) |
| `0x454920` `CNetActor::init` | `+0x2C`, `+0x7C`, `+0x14` |
| `0x45D200` `CAvatarNPC::init` | `+0x2C` |
| `0x5DF080` apply loop | `+0x38` (`+0x30` ที่รายงานเป็น false positive จาก `mov edx,[esi+0x30]` = vector begin) |
| `0x4437C0` dead-sync | `+0x40`, `+0x3C` |
| `0x456630` `CNetActor` vt`+0x20` | (ไม่มีในช่วง 0x50 ไบต์แรกที่ sweep) |

**`+0x30` ไม่ปรากฏในท่อนี้เลย** ⇒ merge แบบ mask-gated (`0x467130`, `0x465610`) ไม่ถูกเรียกจากสายนี้ `[PROVEN]`

---

## 3. (c) คำตอบตรง ๆ: **merge (update-in-place) — ไม่ใช่ bind-over**

**คำตอบ:** thunk **ไม่ bind ทับ** และ **ไม่มีวัตถุไหนถูกทิ้ง** เพราะพอยน์เตอร์ปลายทางไม่เคยถูกเขียน
เฟรมที่สองเรื่อง identity เดิม **อัปเดตของเดิม** ตามที่เลน death สมมติไว้ — **สมมติฐานถูก** `[PROVEN VA=0x46978F]`

**ชะตากรรมของวัตถุที่ผูกอยู่เดิม:** ไม่ถูก free, ไม่ leak, ไม่มี refcount — **มันคือวัตถุเดิมตัวเดิม**
มีแค่ *ค่าข้างใน* ถูกเขียนทับ วัตถุนี้ถูกจองครั้งเดียวใน **ctor ของ actor** และไม่เคยถูกเปลี่ยนพอยน์เตอร์อีก:

| ฟิลด์ | store แบบ `mov [reg+disp32], r32` / `mov dword [reg+disp32], imm32` | + แบบมี SIB | จุดที่เป็น ctor |
|---|---|---|---|
| `+0x348` `ActorAttr` | **8** (`0x40155F`, `0x401569`, `0x403322`, `0x40332C`, `0x40A368`, `0x40A5F9`, `0x40AB49`, `0x4573CA`) | +1 (`0x4C1E9D`) = 9 | `0x4573CA` ใน `CNetActor::ctor 0x457340` (pool `0x1031500`, alloc ที่ `0x4573BB`) |
| `+0x358` `NPCAttr` | **3** (`0x45CC80`, `0x84FBE3`, `0x851938`) | +1 (`0x42EFC1`) = 4 | `0x45CC80` ใน `CNetNPC::ctor 0x45CC00` |
| `+0x244` `MovementAttr` | **9** (`0x443393`, `0x4C079E`, `0x5831D2`, `0x583C4A`, `0x66D3AB`, `0x674C30`, `0x675813`, `0xB16C80`, `0xB16E27`) | +5 (`0x45141E`, `0x451750`, `0x99090C`, `0x99317C`, `0x9DE2FD`) = 14 | `0x443393` ใน `CActorBaseClient::ctor` |
| `+0x3E8` `CSkillAttr` | **3** (`0x44CA71`, `0x44CBC1`, `0xB5ED45`) | +1 (`0x4C2109`) = 4 | `0x44CBC1` ใน `CMyActor::ctor 0x44C990` |

`[PROVEN — sweep ครอบคลุม 100% ของทั้งสอง exec section]` — store ที่เหลือของแต่ละ offset อยู่คนละ base
register / คนละคลาส (`0x84FBE3`, `0x851938`, `0x99090C`, `0xB16C80` ฯลฯ อยู่นอกตระกูล actor) และ
**ไม่มีตัวไหนเลยอยู่ในช่วง `0x469760..0x4698F1`** — assert ข้อนี้อยู่ในสคริปต์ท้ายเอกสาร
**ข้อจำกัดของสำมะโนนี้:** จับได้เฉพาะ store ที่ disp ปรากฏเป็น imm32 ตรง ๆ · store ที่ผ่าน pointer
arithmetic (คำนวณ base+disp ไว้ล่วงหน้าแล้ว store ด้วย disp8/ไม่มี disp) **ไม่ถูกนับ** `[UNKNOWN ขนาดของรูนี้]`

**ถ้าปลายทางเป็น NULL:** `CopyTo` เช็ค `test ebx,ebx; je` เป็นคำสั่งแรก ⇒ **เงียบสนิท ไม่ crash ไม่ทำอะไรเลย**
`[PROVEN VA=0x464F38, 0x464B48, 0x465458]` — เกิดได้จริงถ้า pool alloc ใน ctor คืน 0

### เกรดของคำตอบ

| ข้อ | เกรด |
|---|---|
| thunk ไม่เขียนพอยน์เตอร์ปลายทาง — เป็น LOAD | `[PROVEN VA=0x46978F]` opcode `8B` |
| `+0x24` = `CopyTo(dst)` ทิศทาง `this -> arg` | `[PROVEN VA=0x464F6E..0x464F79]` |
| `CopyTo` ไม่ดู mask เลย | `[PROVEN]` sweep 100% ของ `0x464B40`/`0x464F30`/`0x465450` — 0 mask-test |
| `CopyTo` ไม่คัดลอก mask | `[PROVEN]` ฟิลด์สุดท้ายอยู่ก่อน mask ทุกคลาส |
| วัตถุปลายทางถูกจองใน ctor ครั้งเดียว | `[PROVEN]` สำมะโน store 100% ของ exec section |
| "เฟรมที่ 2/3 = อัปเดต" | `[PROVEN]` — **สมมติฐานของเลน death ถูกต้อง** |
| "เฟรมที่ 2 ที่ส่ง mask ไม่ครบจะทับฟิลด์ที่ไม่ได้ส่งด้วย ctor default" | `[INFERRED]` — PROVEN ว่าคัดลอกไม่มีเงื่อนไข, ยังไม่ปักค่าที่ deserializer ทิ้งไว้ในฟิลด์ที่ bit ไม่ติด |

**คำเตือนสำหรับเลน multiplayer (ROW 4 ก็ได้คำตอบไปด้วยครึ่งหนึ่ง):**
แผน "ขยับ A สองครั้งด้วย `MovementAttr` mask `0x01` อย่างเดียว" จะ **ทับ heading/mode/flags/f32×3 ด้วยค่า default**
ไม่ใช่ "merge delta" — ถ้าต้องการให้ค่าคงเดิม ต้องส่ง mask ครบและส่งค่าเดิมซ้ำมาเอง `[INFERRED]`

---

## 4. ROW 13 — sweep `0x4437C0` ทั้งตัว

### 4.1 ขอบเขตและ coverage

ฟังก์ชัน `0x4437C0..0x443A99` ปิดท้ายด้วย padding `cc cc cc` ที่ `0x443A9A`
ยาว `0x2DA` = **730 ไบต์ · sweep 730/730 = 100%**
span sha256 `85d294b84843e0bd46256e0257cf5d51be0415081739d82b0b4c254975ee9592`

HYP-PF-023 อ่านเฉพาะ 2 กิ่ง predicate (`0x44385D` latch, `0x443990` task) — **~30 ไบต์จาก 730 = 4%**
รอบนี้อ่านครบ ⇒ ตอบได้ว่า **มี side effect อื่นจริง และมี 3 อย่าง**

### 4.2 คำตอบ: **ใช่ — มีอย่างอื่นที่ยิงตอน re-send ปกติ HP > 0**

ที่ HP > 0: `bl` (= actor vt`+0x40`) = 0 และ `[esp+0x13]` (= actor vt`+0x3C`) = 0 เสมอ
เส้นที่เดินจริงคือ `0x4437E8 -> 0x44384E(je) -> 0x4438EB -> ...`

| # | side effect | VA | เงื่อนไข | ยิงตอน HP>0 ไหม |
|---|---|---|---|---|
| **S1** | `actor+0x10` **บิต `0x80` ถูกเขียนทับ** ให้เท่ากับ `MovementAttr[+0x3C] & 0x80` | `0x4437E8..0x44380F` | **ไม่มีเงื่อนไข** อยู่ก่อน predicate ทุกตัว | **ยิงทุกครั้ง 100%** |
| **S1b** | **deref `[actor+0x244]` โดยไม่เช็ค NULL** แล้วอ่าน `[eax+0x3C]` | `0x4437E8`, `0x4437EE` | ไม่มีเงื่อนไข | **ยิงทุกครั้ง** (ปลอดภัยเพราะ ctor จองไว้ — แต่เป็น NULL-unsafe จริง) |
| **S2** | `actor+0x70 \|= 0x400` แล้วเรียก `0x43E930(actor, 0)` | `0x4438FF..0x44390A` | `MovementAttr[+0x3C] & 0x80` **ติด** และบิต `0x400` ยัง**ไม่**ติด — **ไม่ดู HP เลย** | **ยิงได้ที่ HP > 0** |
| **S3** | `actor+0x70 &= ~0x600` (เคลียร์ทั้ง `0x200` dying และ `0x400`) แล้วเรียกชุด `0x4162A0` -> ... -> `0x43E930(actor,0)` -> `0x880E30(4,1)` + `0x880E30(5,1)` | `0x443942..0x44398F` | `MovementAttr[+0x3C]&0x80` **ไม่**ติด และ `actor+0x70 & 0x200` **ติดอยู่** | **ยิงได้ที่ HP > 0** — นี่คือทาง "คืนชีพ" |
| — | `0x200` dying latch + `0x43E930(actor,1)` + `0x880E30(4,0)/(5,0)` + `0x232B` | `0x44385D..0x4438EA` | ต้อง `bl != 0` = HP==0 && timer>0 | **ไม่ยิง** |
| — | `CActorTask_Dead` (`0x4439D2` pool 0x24 ไบต์, ctor `0x4439E9 -> 0x472810`) | `0x44399B..0x443A86` | ต้อง `[esp+0x13] != 0` = HP==0 && timer<=0 | **ไม่ยิง** |
| — | เทียบ identity กับ local player `[0x1032EC4]+0xC8/+0xCC` แล้วเคลียร์ target + แตะ widget `0xF0D2A8` | `0x443A00..0x443A86` | อยู่ในกิ่ง `[esp+0x13] != 0` | **ไม่ยิง** |

**S1 ไบต์เต็ม** `[PROVEN VA=0x4437E8..0x44380F]`
span sha256 `9b76ad2c55f93b01136a54251dcc93094247a2d192d2c701f9fabeb9733bef19`
```
004437E8  8b 86 44 02 00 00     mov  eax,[esi+0x244]     ; MovementAttr, NO null check
004437EE  8b 48 3c              mov  ecx,[eax+0x3C]      ; flags dword
004437F1  80 e1 80              and  cl,0x80
004437F4  80 f9 80              cmp  cl,0x80
004437F7  0f 94 c0              sete al
004437FA  84 c0                 test al,al
004437FC  8b 46 10              mov  eax,[esi+0x10]
004437FF  74 07                 je   00443808
00443801  0d 80 00 00 00        or   eax,0x80
00443806  eb 05                 jmp  0044380D
00443808  25 7f ff ff ff        and  eax,0xFFFFFF7F
0044380D  89 46 10              mov  [esi+0x10],eax      ; *** WRITE ***
```

**S2 ไบต์เต็ม** `[PROVEN VA=0x4438EB..0x44390A]`
span sha256 `a2958c2e2545974950d82bce86673f29e019a6bce21cd67fb3c5c0b5456db83d`
`8b46102580000000b9000400007416854e707511094e706a008bcee825b0ffff`

**S3 หัวกิ่ง** `[PROVEN VA=0x44393D..0x44398F]`
span sha256 `70ba8a4f595c6757d04352577204e49b856a8cd93ee3979aecc77166933da689`

### 4.3 ทำไม S1/S2/S3 ถึงเป็นเรื่องของเลน death และเลน multiplayer โดยตรง

`MovementAttr` field `+0x3C` = **flags u32** ซึ่ง wire ปักไว้แล้วว่าเดินด้วย **mask bit `0x08`, tag `0x26`**
`[PROVEN VA=0x46722E..0x46723A]` (`f6 03 08` @`0x46722E` / `74 0f` / `6a 04 8d 46 3c 50 6a 26` @`0x467233`)
ตรงกับ `make_remote_movement_attr(..., flags_u32=...)` ที่ `current/pf_login_game_server_v141.py:1204` เป๊ะ

ต่อกับข้อ 1: `MovementAttr::CopyTo` **ทับ `+0x3C` ทุกครั้ง ไม่ดู mask**
⇒ **ทุก re-send ของ identity เดิมจะเขียน `+0x3C` ของ actor ใหม่หมด แล้ว `0x4437C0` จะอ่านมันทันทีในบรรทัดถัดไป**
⇒ ถ้าเฟรมแรกเคยส่ง `flags_u32` ที่มีบิต `0x80` แล้วเฟรมที่สองไม่ส่ง (bit `0x08` ไม่ติด) ค่าจะกลายเป็น default
   และเส้นทางจะสลับจาก S2 ไปเป็น S3 — **เคลียร์ `0x200` dying latch ทิ้ง** `[INFERRED]` แต่ทุกชิ้นย่อยเป็น PROVEN

**ข้อสรุปความปลอดภัยของเลนที่ ship ไปแล้ว:** `0x4437C0` **ไม่ใช่ no-op ตอน HP > 0**
มันแตะ `actor+0x10` ทุกครั้ง และแตะ `actor+0x70` (บิต `0x400` และ `0x600`) ได้โดย**ไม่ดู HP เลย**
เกตเดียวที่คุมสองอันหลังคือ **ค่าของ `MovementAttr[+0x3C]` บิต `0x80`** ไม่ใช่ HP
เลน death ที่ "คุมด้วย HP > 0" จึง **ไม่ได้คุม S1/S2/S3** `[PROVEN]`

### 4.4 ของแถมจากการ sweep — `0x4446F0` ทำมากกว่าที่ RUNTIMERES-ACTOR-ENTRY-001 เขียนไว้

`0x4446F0` (actor vt `+0x20` ของ `CNetNPC`/`CAvatarNPC`/`Pet`) span `0x4446F0..0x44472C` (0x3D ไบต์)
sha256 `77c049b4e256103ef86ca0bc29a24559ea040ee67b630f983a0b0abc8e6335e7` — sweep 100%

```
004446FE  call 0x5DF080                     ; apply loop            (ปักไว้แล้ว)
00444705  call 0x4437C0                     ; dead-sync             (ปักไว้แล้ว)
0044470A  mov ecx,[esi+0x244] ; push ecx
00444711  lea ecx,[esi+0xD8]
00444717  call 0x444170                     ; *** ไม่เคยถูกรายงาน ***
0044471C  mov edx,[esi] ; mov eax,[edx+0x24]
00444723  mov byte [esi+0x128], 1           ; *** ไม่เคยถูกรายงาน ***
0044472A  call eax                          ; actor->vtable[+0x24]() *** ไม่เคยถูกรายงาน ***
```
`[PROVEN VA=0x44470A..0x44472C]` — actor vt`+0x24` = `0x459160` (`CNetActor`) / `0x44E250` (`CMyActor`) /
`0x45D490` (`CNetNPC`/`CAvatarNPC`/`Pet`) · ทั้งสามยัง**ไม่ได้ถอด** ⇒ **มี side effect เพิ่มอีกสองชั้นที่ยังไม่รู้**

### 4.5 แก้ข้อมูลที่ผูกผิดคลาสใน RUNTIMERES-ACTOR-ENTRY-001 §FIFTH

`0x43BD70` / `0x43BDA0` เป็น vt `+0x3C`/`+0x40` ของ **`CNetNPC` / `CAvatarNPC` / `Pet` เท่านั้น**
ของ **`CNetActor` / `CMyActor` คือ `0x454A70` / `0x454AC0`** ซึ่งเป็นฟังก์ชันคนละตัว `[PROVEN]`

| class | vt `+0x20` | vt `+0x3C` | vt `+0x40` | vt `+0x74` |
|---|---|---|---|---|
| `CNetActor` | `0x456630` | `0x454A70` | `0x454AC0` | `0x44C630` |
| `CMyActor` | `0x456630` | `0x454A70` | `0x454AC0` | `0x44C630` |
| `CNetNPC` / `CAvatarNPC` / `Pet` | `0x4446F0` | `0x43BD70` | `0x43BDA0` | `0x45CD20` |

และ `0x454A70` **ไม่เช็ค NULL ก่อน `comiss xmm0,[eax+0x58]`** `[PROVEN VA=0x454A7C]`
⇒ actor_type 2 ที่ `[actor+0x348]` เป็น NULL **จะ crash ตรงนี้ ไม่ใช่แค่ "ป้ายชื่อว่าง"**
และมันยังเลือกฟิลด์ HP ต่างกันตามว่า `[actor+0x358]` (`NPCAttr`) เป็น NULL หรือไม่:
NULL -> `[attr+0x44]==0` · ไม่ NULL -> `[attr+0x1A8]==0` `[PROVEN VA=0x454A8C..0x454AAD]`
span `0x454A70..0x454AB1` sha256 `30b4504e946d31247088b36bf1acf2fd24ada548a0dd5a656a2475d91d907428`

---

## 5. ตรวจเครื่องมือกับคำตอบที่โปรเจกต์ปักไว้แล้ว (ทำก่อนเชื่อผลของตัวเอง)

**ทำแล้ว 3 ข้อ ก่อนเขียนข้อสรุปใด ๆ**

### 5.1 `BasicAttr::Merge 0x4656A3` คัดลอกฟิลด์ไปข้างหน้าเมื่อบิต clear — **re-derive ตรง**

pin ที่มีอยู่: `src/pirateforce_foundation/stats_progression_hypothesis.py:1394`
`BASIC_ATTR_MERGE_TIMER_COPY_FORWARD_VA = 0x4656A3` · byte ที่รายงานเดิมเขียนไว้ `84c07806d94658d95f58`

ผลที่เครื่องมือรอบนี้อ่านได้จากไบนารีสด:
```
004656A3  84 c0        test al,al
004656A5  78 06        js   004656AD        ; บิต 0x80 ติด (sign ของ al) -> ข้าม
004656A7  d9 46 58     fld  dword [esi+0x58]   ; esi = arg (src)
004656AA  d9 5f 58     fstp dword [edi+0x58]   ; edi = this (dst)
```
span `0x4656A3..0x4656AC` = `84c07806d94658d95f58` — **ตรงตัวอักษรกับที่ปักไว้**
sha256 `9a1d2473cf2abcd678a2696c578aa1340c15f5ccef43d472ed2356bc2b31b061`
ทิศทาง arg -> this เมื่อบิต **ไม่** ติด = "copy forward" **ตรงกับข้อสรุปเดิมทุกประการ** ✔

### 5.2 predicate timer polarity ของ RUNTIMERES §FIFTH — **re-derive ตรง**

`0x43BD70` (`vt+0x3C`): `GetAttr()` -> `cmp [eax+0x44],0` (HP) -> `xorps xmm0,xmm0; comiss xmm0,[eax+0x58]; jb -> 0`
⇒ `HP==0 && timer<=0` ✔  span sha256 `b0791af77119cc5d8cf8378da7019ed57a5ebaa973cd47b89842a058fcb10947`
`0x43BDA0` (`vt+0x40`): `movss xmm0,[eax+0x58]; comiss xmm0,[0xF0989C]; ja -> 1`
⇒ `HP==0 && timer>0` ✔  span sha256 `82646de1ca08e023b25cd71fe64f9025bda929822ccf4d8233b0603c4011417a`
และ `0x4437C0` เก็บ `+0x40` ไว้ใน `bl` (`0x44383A`) กับ `+0x3C` ไว้ที่ `[esp+0x13]` (`0x443843`) — **ตรงเป๊ะ** ✔

### 5.3 vtable slot ที่โปรเจกต์ปักไว้ใน `tools/pf_actor_type_dispatch_static.py` — **re-derive ตรงทั้ง 6**

`ActorAttr 0xF0E7A0+0x38=0x469760` ✔ · `NPCAttr 0xF0E7E0+0x38=0x4697B0` ✔ ·
`MovementAttr 0xF0D0F8+0x38=0x469800` ✔ · `AvatarAttr 0xF0E088+0x38=0x469850` ✔ ·
`CSkillAttr 0xF48B78+0x38=0x4698B0` ✔ · `BasicAttr 0xF0E760+0x38=0x73D360` ✔
⇒ การนับ slot index ของเครื่องมือรอบนี้ถูกต้อง (ยืนยันกับค่าที่ commit ไว้แล้ว ไม่ใช่ยืนยันกับตัวเอง)

### 5.4 สิ่งที่การตรวจสอบนี้ทำให้ต้อง **แก้** ในเอกสารเก่า

* `reports/PF_RESCUE_AND_DEATH_ESCALATION_STATIC_20260819.md` เขียนว่า `BasicAttr::Merge 0x465610` คือ `vt+0x24`
  **ไม่ใช่** — `0xF0E760+0x24 = 0x464B40`, `0xF0E760+0x30 = 0x465610` `[PROVEN]`
  และ call site ที่รายงานนั้นอ้าง (`0x5F2504` = `8b0b 8b01 8b5024 57 ffd2`) เป็น **`+0x24`** จริง
  ⇒ **`UpdateAttrVital` เดินผ่าน `CopyTo` (ไม่ดู mask) ไม่ได้เดินผ่าน `0x465610`**
  สำมะโน vtable-dispatch ทั้ง `0x5F2400..0x5F261A` เจอ **แค่ `+0x10`, `+0x24`, `+0x10`** — **ไม่มี `+0x30`** `[PROVEN]`
  ⇒ ข้อสรุป *"ละบิต `0x0080` แล้ว timer 20.0 จะค้างตลอดไป"* **ยังไม่มีไบต์รองรับบนสายนี้**
  และคำแนะนำ *"ต้องส่ง `0x0080 = 0.0f` แบบชัดเจน"* กลับกลายเป็น **ปลอดภัยอยู่แล้วโดยบังเอิญ** `[INFERRED]`
  **ห้ามแก้ตัวเลขในทรีจากเอกสารนี้** — ต้องมีรอบ verify ของตัวเองก่อน (เอกสารนี้ report-only)
* `MULTIPLAYER_CHUNK2_VISIBILITY_DESIGN_R90.md` §10 ROW 5 คำว่า "thunk ทั้งห้าตัว byte-identical" — **ไม่จริง**
  4 ตัวเหมือนกันหลัง mask 3 ช่องอิมมีเดียต ตัวที่ห้า (`0x469850`) เป็นฟังก์ชันคนละตัวยาวคนละขนาด

---

## 6. Coverage — ตัวเลข ไม่ใช่คำว่า "ทั้งหมด"

| การ sweep | ขอบเขต | ตัวเลข | หยุดตรงไหน |
|---|---|---|---|
| prologue-shape sweep หา thunk | **ทั้ง 2 executable section** (raw size): `.text` `0x401000` rs `0x838C00` + `.code` `0xC3A000` rs `0x400` = **8,622,080 ไบต์** | 72 hit, 4 exact-template match | ไม่หยุด — เดินจบทั้งสอง section |
| template match (mask 3 imm field) | 72 hit ทั้งหมด | 4 match / 68 reject | — |
| สำมะโน dword pointer ของ thunk ทั้ง 6 | **ทั้งไฟล์ 14,759,424 ไบต์ ทุก alignment** | 1/1/1/1/1/2020 | ไม่หยุด |
| สำมะโน `E8`/`E9` rel32 ไปที่ thunk ทั้ง 6 | ทั้ง 2 exec section | 0/0/0/0/0 และ 75/1 | ไม่หยุด |
| สำมะโน store `mov [reg+disp32], r32` และ `mov dword [reg+disp32], imm32` | ทั้ง 2 exec section, 4 offset | ไม่นับ SIB: `+0x348`:8 · `+0x358`:3 · `+0x244`:9 · `+0x3E8`:3 · นับ SIB ด้วย: 9 / 4 / 14 / 4 | ไม่หยุด · **ไม่ครอบคลุม** store ผ่าน pointer arithmetic ที่ disp ไม่ปรากฏเป็น imm32 |
| อ่าน `CopyTo` ทั้ง 4 ตัว | `0x4676A0..0x4676E5` (0x46) · `0x464B40..0x464BD5` (0x96) · `0x464F30..0x465205` (0x2D6) · `0x465450..0x4654B5` (0x66) | **100% ของทั้ง 4** | — |
| sweep `0x4437C0` | `0x4437C0..0x443A99` = **730 ไบต์** | **730/730 = 100%** | ขอบเขตยืนยันด้วย padding `cc cc cc` ที่ `0x443A9A` |
| sweep `0x4446F0` | `0x4446F0..0x44472C` = 61 ไบต์ | **61/61 = 100%** | — |
| สำมะโน vtable `+0x30` dispatch (require vtable-load prefix) | ทั้ง 2 exec section | **91 site ทั้งอิมเมจ · 0 site ในท่อ actor-entry** | 91 site **ยังไม่ resolve รายตัว** |
| สำมะโน vtable dispatch ในฟังก์ชันของท่อ | 9 ฟังก์ชัน (ดูตาราง 2.3) | — | `0x456630` sweep แค่ 0x50 ไบต์แรก **ยังไม่จบฟังก์ชัน** |

**negative ที่กล้าประกาศ (มี coverage รองรับ):**
* "ไม่มีการเขียนพอยน์เตอร์ปลายทางใน thunk" — sweep 100% ของ thunk ทั้ง 5
* "ไม่มี mask test ใน `+0x24`" — sweep 100% ของ `CopyTo` ทั้ง 4
* "ไม่มี `+0x30` dispatch ในท่อ actor-entry" — sweep 100% ของ 8 ฟังก์ชัน (`0x456630` ยกเว้น)

**negative ที่ยัง "ไม่กล้า":** ทุกอย่างที่พึ่ง `0x456630` และ 91 vt`+0x30` site — ดูข้อ 7

---

## 7. สิ่งที่ยังตอบไม่ได้

1. **`0x456630` (`CNetActor` / `CMyActor` vt `+0x20`) ยังไม่ถอด** — sweep แค่ 0x50 ไบต์แรกจากฟังก์ชันที่มี SEH frame
   และ locals `0x84` ไบต์ · RUNTIMERES เขียนว่ามันไป `0x4446F0` แต่รอบนี้ **ไม่ได้ยืนยันซ้ำ** ⇒
   **สิ่งที่รายงานในข้อ 4.2/4.4 พิสูจน์แล้วสำหรับ actor_type 4/5/6 เท่านั้น** ยังไม่พิสูจน์สำหรับ actor_type 2/3 `[UNKNOWN]`
2. **`0x43E930` ทำอะไร** — รู้แค่ว่าเป็น `__thiscall(actor, bool)` มี SEH, locals `0x120`, แตะ `[actor+0x238]` แล้วเรียก
   vt `+0x6C` ของมัน · **ไม่ได้ถอด** ⇒ ผลจริงของ S2/S3 ยังไม่รู้
3. **`0x444170` ทำอะไร** — `__thiscall(actor+0xD8, MovementAttr)` เรียกจาก `0x444717` ทุก re-send · **ไม่ได้ถอด**
4. **actor vt `+0x24`** (`0x459160` / `0x44E250` / `0x45D490`) ที่ `0x4446F0` เรียกทุก re-send · **ไม่ได้ถอดสักตัว**
5. **`[actor+0x128] = 1`** ที่ `0x444723` หมายถึงอะไร · **ไม่รู้**
6. **`0x4162A0` และ `0x880E30(x, y)`** ในกิ่ง S3 · **ไม่ได้ถอด**
7. **บิต `0x80` ของ `MovementAttr[+0x3C]` ชื่ออะไร / ความหมายอะไร** — รู้แค่ว่ามันคุม S1/S2 · ไม่มี literal ไหนตั้งชื่อให้
8. **`actor+0x10` บิต `0x80` ถูกอ่านที่ไหนอีกบ้าง** — ไม่ได้ทำสำมะโน
9. **ค่าที่ deserializer ทิ้งไว้ในฟิลด์ที่ mask bit ไม่ติด** — สมมติว่าเป็น ctor default แต่**ไม่ได้อ่าน ctor ของ
   `MovementAttr` / `ActorAttr` จริง** (`0x43BBA0` เป็น `jmp` ไม่ใช่ ctor) ⇒ ข้อสรุปในข้อ 1.3 ยังเป็น `[INFERRED]`
10. **`ActorAttr` mask 64-bit ที่ `+0x1B4` — ยืนยันจาก `Serial 0x466253` เท่านั้น** ยังไม่ได้ enumerate ว่าบิตไหนคุมฟิลด์ไหน
    ⇒ **ROW 1 ยังเปิดอยู่เต็ม ๆ เอกสารนี้ไม่ได้ปิดมัน**
11. **91 vtable `+0x30` dispatch site ทั้งอิมเมจ** — ยังไม่ resolve รายตัว ⇒ ยังไม่รู้ว่าใครเรียก `0x467130` / `0x465610`
    (ROW 4 ปิดได้ครึ่งเดียว: **รู้แล้วว่าท่อ actor-entry ไม่เรียก** แต่**ยังไม่รู้ว่าใครเรียก**)
12. **229 vt `+0x20` dispatch site ที่ RUNTIMERES ไม่ resolve** — สืบทอดมาเต็ม ๆ ไม่ได้ทำให้แคบลง
13. **ไม่มี runtime confirmation ใด ๆ** — ทุกอย่างเป็น static ล้วน · ไม่ได้บูตอะไรทั้งสิ้น
14. **ไม่มีข้ออ้างใดเกี่ยวกับเซิร์ฟเวอร์ต้นฉบับ** — เอกสารนี้พูดถึงพฤติกรรม *ไคลเอนต์ของเรา* เท่านั้น

---

## 8. python ที่ใช้ (stdlib ล้วน — วางแล้วรันได้เลย)

```python
#!/usr/bin/env python3
# CHUNK2 Q3 - bind thunk +0x38 (ROW 5) + dead-sync 0x4437C0 (ROW 13)
# READ-ONLY.  pure stdlib.  helper style copied from
# tools/pf_runtimeres_actor_entry_static.py (va2off / section walk / opcode match / span sha)
import hashlib, struct, sys

BIN = sys.argv[1] if len(sys.argv) > 1 else "GameClient/GameClient.local.bin"
data = open(BIN, "rb").read()
assert hashlib.sha256(data).hexdigest().upper() == (
    "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623")
assert len(data) == 14759424

# ---------------------------------------------------------------- PE plumbing
_e = struct.unpack_from("<I", data, 0x3C)[0]; _coff = _e + 4
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
    for _nm, _va, _vs, _rp, _rs, _ch in SECS:
        if _va <= r < _va + max(_vs, _rs):
            off = _rp + (r - _va)
            return off if off < len(data) else None
    return None

def off2va(off):
    for _nm, _va, _vs, _rp, _rs, _ch in SECS:
        if _rp <= off < _rp + _rs:
            return IMAGE_BASE + _va + (off - _rp)
    return None

def sec_of(va):
    r = va - IMAGE_BASE
    for _nm, _va, _vs, _rp, _rs, _ch in SECS:
        if _va <= r < _va + max(_vs, _rs):
            return _nm
    return None

def rd(va, n):
    o = va2off(va)
    return data[o:o + n] if o is not None else b""

def dw(va):
    b = rd(va, 4)
    return struct.unpack("<I", b)[0] if len(b) == 4 else None

def span_sha(lo, hi):
    return hashlib.sha256(rd(lo, hi - lo)).hexdigest()

def rel32_sites(target, opcode):
    out = []
    for _nm, _va0, _vs, rp, rs in EXEC_SECS:
        i = data.find(bytes([opcode]), rp, rp + rs - 5)
        while i >= 0:
            rel = struct.unpack_from("<i", data, i + 1)[0]
            va = off2va(i)
            if va is not None and ((va + 5 + rel) & 0xFFFFFFFF) == target:
                out.append(va)
            i = data.find(bytes([opcode]), i + 1, rp + rs - 5)
    return sorted(out)

def dword_vas(value):
    p = struct.pack("<I", value); out = []; i = data.find(p)
    while i >= 0:
        va = off2va(i)
        if va is not None:
            out.append(va)
        i = data.find(p, i + 1)
    return out

# ---------------------------------------------------- (b) the five thunk table
THUNKS = {
    "ActorAttr":    (0x469760, 0xF0E7A0, 0x102CB2C, 0x348),
    "NPCAttr":      (0x4697B0, 0xF0E7E0, 0x102D954, 0x358),
    "MovementAttr": (0x469800, 0xF0D0F8, 0x102CE88, 0x244),
    "AvatarAttr":   (0x469850, 0xF0E088, 0x102CB2C, None),
    "CSkillAttr":   (0x4698B0, 0xF48B78, 0x102CB04, 0x3E8),
    "BasicAttr":    (0x73D360, 0xF0E760, None,      None),
}
for name, (thunk, vt, tok, fld) in THUNKS.items():
    assert dw(vt + 0x38) == thunk, name          # re-derive the pinned slot
    ptrs = dword_vas(thunk)
    print("%-13s thunk=%08X vt+0x38 ok  ptrs=%-5d E8=%-3d E9=%d"
          % (name, thunk, len(ptrs), len(rel32_sites(thunk, 0xE8)),
             len(rel32_sites(thunk, 0xE9))))

# prologue sweep over EVERY executable section
PRO = bytes.fromhex("568b7424 08578bf9 85f674".replace(" ", ""))
hits = []
for nm, va0, vs, rp, rs in EXEC_SECS:
    i = data.find(PRO, rp, rp + rs)
    while i >= 0:
        hits.append(off2va(i)); i = data.find(PRO, i + 1, rp + rs)
print("prologue-shape hits over %d exec bytes: %d"
      % (sum(rs for _n, _v, _s, _r, rs in EXEC_SECS), len(hits)))

# the four templated thunks are equal once 3 immediate fields are masked out
VAR = set(range(0x15, 0x19)) | set(range(0x1A, 0x1E)) | set(range(0x31, 0x35))
def canon(t):
    b = bytearray(rd(t, 0x42))
    for i in VAR:
        b[i] = 0
    return bytes(b)
FOUR = [0x469760, 0x4697B0, 0x469800, 0x4698B0]
cs = {hashlib.sha256(canon(t)).hexdigest() for t in FOUR}
assert len(cs) == 1, "the four are NOT one template"
assert hashlib.sha256(canon(0x469850)).hexdigest() not in cs, "0x469850 is not the same shape"
print("canonical(4) =", cs.pop())
for t in FOUR + [0x469850]:
    ln = 0x42 if t in FOUR else 0x5E
    print("  %08X len 0x%02X sha=%s" % (t, ln, hashlib.sha256(rd(t, ln)).hexdigest()))

# ------------------------------------------------- (a) the je / the LOAD proof
# 0x46978F must be `8B 80 <disp32>` = mov eax,[eax+disp32]  (a LOAD, not `89`)
assert rd(0x46978F, 2) == b"\x8b\x80"
assert struct.unpack_from("<I", rd(0x46978F, 6), 2)[0] == 0x348
assert rd(0x469795, 3) == b"\x8b\x52\x24"      # mov edx,[edx+0x24]
assert rd(0x46976A, 1) == b"\x74"              # je #1
assert rd(0x46978B, 1) == b"\x74"              # je #2
assert rd(0x46978D, 0x15).hex() == "8b178b80480300008b5224508bcfffd25f5ec20400"
print("thunk tail span 0x46978D..0x4697A1 sha =", span_sha(0x46978D, 0x4697A2))

# vt+0x24 = CopyTo : `this` -> arg, unconditional, mask never copied
assert rd(0x464F6E, 6) == b"\x8b\x87\x8c\x00\x00\x00"   # mov eax,[edi+0x8C]  (this)
assert rd(0x464F74, 6) == b"\x89\x86\x8c\x00\x00\x00"   # mov [esi+0x8C],eax  (arg)
for lo, hi in ((0x464B40, 0x464BD6), (0x464F30, 0x465206), (0x465450, 0x4654B6)):
    body = rd(lo, hi - lo)
    assert b"\xf6\x47\x70" not in body and b"\x0f\xb7\x47\x70" not in body

# apply loop really calls attr->vt[+0x38](actor)
assert rd(0x5DF0B5, 8) == b"\x8b\x01\x8b\x50\x38\x53\xff\xd2"

# ------------------------------------------- 5.1 re-derive the KNOWN answer(s)
assert rd(0x4656A3, 10).hex() == "84c07806d94658d95f58"      # BasicAttr merge fwd
assert dw(0xF0E760 + 0x24) == 0x464B40                       # +0x24 is NOT 0x465610
assert dw(0xF0E760 + 0x30) == 0x465610                       # 0x465610 is +0x30
assert rd(0x43BD70, 8) == b"\x56\x8b\xf1\x8b\x06\x8b\x50\x74"  # vt+0x3C predicate
assert rd(0x43BDA0, 8) == b"\x56\x8b\xf1\x8b\x06\x8b\x50\x74"  # vt+0x40 predicate
print("KNOWN-ANSWER RE-DERIVATION: 0x4656A3 / vtable indexing / predicates  OK")

# ----------------------------------------------------- (d) ROW 13  0x4437C0
body = rd(0x4437C0, 0x400)
end = 0x4437C0 + body.find(b"\xcc\xcc\xcc")
print("0x4437C0 extent = 0x%X..0x%X  (%d bytes, 100%% swept)  sha=%s"
      % (0x4437C0, end, end - 0x4437C0, span_sha(0x4437C0, end)))
assert rd(0x4437E8, 0x28).hex() == (
    "8b86440200008b483c80e18080f9800f94c084c08b461074070d80000000eb05"
    "257fffffff894610")                                # S1 unconditional mirror
assert rd(0x4438FF, 3) == b"\x09\x4e\x70"              # S2 or [esi+0x70],0x400
assert rd(0x443942, 7) == b"\x81\x66\x70\xff\xf9\xff\xff"   # S3 and ~0x600
assert rd(0x44385D, 3) == b"\x09\x56\x70"              # dying latch (HP==0 only)
# MovementAttr wire: mask bit 0x08 -> u32 tag 0x26 -> field +0x3C
assert rd(0x46722E, 3) == b"\xf6\x03\x08"
assert rd(0x467233, 8) == b"\x6a\x04\x8d\x46\x3c\x50\x6a\x26"

# --------------------------------------------- vtable dispatch offset censuses
def vt_sites_in(lo, hi):
    out = []; b = rd(lo, hi - lo)
    for i in range(len(b) - 4):
        if b[i] != 0x8B:
            continue
        m = b[i + 1]
        if (m >> 6) != 1 or (m & 7) == 4:
            continue
        if bytes([0xFF, 0xD0 + ((m >> 3) & 7)]) in b[i + 3:i + 19]:
            out.append((lo + i, b[i + 2]))
    return out
for lab, lo, hi in (("0x446F30", 0x446F30, 0x447060), ("0x4446F0", 0x4446F0, 0x44472D),
                    ("0x5DF080", 0x5DF080, 0x5DF0D4), ("0x4437C0", 0x4437C0, end),
                    ("0x5F2400", 0x5F2400, 0x5F261A)):
    print(lab, ["%08X:+0x%02X" % s for s in vt_sites_in(lo, hi)])

n30 = 0
for nm, va0, vs, rp, rs in EXEC_SECS:
    blob = data[rp:rp + rs]
    for i in range(2, len(blob) - 3):
        if blob[i] != 0x8B:
            continue
        m = blob[i + 1]
        if (m >> 6) != 1 or (m & 7) == 4 or blob[i + 2] != 0x30:
            continue
        if bytes([0xFF, 0xD0 + ((m >> 3) & 7)]) not in blob[i + 3:i + 19]:
            continue
        p0, p1 = blob[i - 2], blob[i - 1]
        if p0 == 0x8B and (p1 >> 6) == 0 and ((p1 >> 3) & 7) == (m & 7) \
           and (p1 & 7) not in (4, 5):
            n30 += 1
print("vtable +0x30 dispatch sites image-wide:", n30, "(0 of them in the pipe)")

# --------------------------------------- destination pointer written only in ctor
REGN = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"]
def store_sites(disp):
    out = []; d = struct.pack("<I", disp)
    for nm, va0, vs, rp, rs in EXEC_SECS:
        blob = data[rp:rp + rs]; i = blob.find(d)
        while i >= 0:
            if i >= 2 and blob[i - 2] == 0x89 and (blob[i - 1] >> 6) == 2 \
               and (blob[i - 1] & 7) != 4:
                out.append((off2va(rp + i - 2), "mov [%s+0x%X],%s"
                            % (REGN[blob[i - 1] & 7], disp,
                               REGN[(blob[i - 1] >> 3) & 7])))
            if i >= 2 and blob[i - 2] == 0xC7 and (blob[i - 1] >> 6) == 2 \
               and (blob[i - 1] & 7) != 4 and ((blob[i - 1] >> 3) & 7) == 0:
                out.append((off2va(rp + i - 2), "mov dword [%s+0x%X],imm"
                            % (REGN[blob[i - 1] & 7], disp)))
            i = blob.find(d, i + 1)
    return out
for disp in (0x348, 0x358, 0x244, 0x3E8):
    st = store_sites(disp)
    print("+0x%03X stores=%d" % (disp, len(st)),
          [("%08X" % v) for v, _t in st])
assert any(v == 0x4573CA for v, _t in store_sites(0x348))   # CNetActor ctor
assert any(v == 0x45CC80 for v, _t in store_sites(0x358))   # CNetNPC ctor
assert any(v == 0x443393 for v, _t in store_sites(0x244))   # CActorBaseClient ctor
assert any(v == 0x44CBC1 for v, _t in store_sites(0x3E8))   # CMyActor ctor
# none of them lives inside any thunk
for v, _t in (store_sites(0x348) + store_sites(0x358)
              + store_sites(0x244) + store_sites(0x3E8)):
    assert not (0x469760 <= v < 0x4698F2), "a thunk DOES write the pointer!"
print("PROVEN: no thunk ever writes a destination pointer -> MERGE, not bind-over")
```

---

## 9. ภาคผนวก — span ทั้งหมดที่ควร re-pin ในรอบต่อไป

| ชื่อ | span | len | sha256 |
|---|---|---|---|
| `thunk_actorattr` | `0x469760..0x4697A2` | 0x42 | `6f8a3251bde10432e1352a93e082937957be89bff8f6aa28bfcec8b43a48aec1` |
| `thunk_npcattr` | `0x4697B0..0x4697F2` | 0x42 | `be9bbd866c5eaebe5fed173106049710cd39abc9e4239e63a877087e433aba6a` |
| `thunk_movementattr` | `0x469800..0x469842` | 0x42 | `533f517c045c53d6ee7e33249a2836e0b7b1c2536a0feabbd11ed17f34c59ce7` |
| `thunk_skillattr` | `0x4698B0..0x4698F2` | 0x42 | `8faf7ce6e971b9a0a35bd1e7c13ceb09d0b3d4789cd188cbc1e75541d5d104e3` |
| `thunk_avatarattr` | `0x469850..0x4698AE` | 0x5E | `9b141be64a7e4ea84de514deaf0532588fd05dc4bb97dc99f931d13703c5622e` |
| `thunk_canonical_4` | (4 ตัวหลัง mask 3 imm) | 0x42 | `4106599f09230f8be10376630d32df65fad86856ed365332aebe02d88fa218a8` |
| `copyto_base_0x4676A0` | `0x4676A0..0x4676E6` | 0x46 | `6ea21856a9261b281cb2aca033e566ce99793fe87b13b20142b1fa7a154e4189` |
| `copyto_basicattr_0x464B40` | `0x464B40..0x464BD6` | 0x96 | `2b20e1a28362bd575da56f2c062d38776f1dbb7083ca9722cbff27f83e88b078` |
| `copyto_actorattr_0x464F30` | `0x464F30..0x465206` | 0x2D6 | `daed370e8f0a225de68ccedc6415d631e71ca7daba5f66e2b00b946f88a76d33` |
| `copyto_movementattr_0x465450` | `0x465450..0x4654B6` | 0x66 | `6f21f741b751901a9cf23f890e83a581fed234626c9960cc4bdbed4399217a44` |
| `merge_basicattr_0x465610` (vt `+0x30`) | `0x465610..0x4656E6` | 0xD6 | `a8f8fe76be1603ad7a668635a2f0986908ac5561c195d6f4fffbae9a75b38548` |
| `merge_timer_fwd_0x4656A3` | `0x4656A3..0x4656AD` | 0x0A | `9a1d2473cf2abcd678a2696c578aa1340c15f5ccef43d472ed2356bc2b31b061` |
| `applyloop_0x5DF080` | `0x5DF080..0x5DF0D4` | 0x54 | `e44d45fab0d5964a0f2eab2aa65f56be99865f108763f3827ecaf0c1a83f1c67` |
| `update_0x4446F0` | `0x4446F0..0x44472D` | 0x3D | `77c049b4e256103ef86ca0bc29a24559ea040ee67b630f983a0b0abc8e6335e7` |
| `deadsync_0x4437C0` (ทั้งฟังก์ชัน) | `0x4437C0..0x443A9A` | 0x2DA | `85d294b84843e0bd46256e0257cf5d51be0415081739d82b0b4c254975ee9592` |
| `deadsync_head_mirror` (S1) | `0x4437E8..0x443810` | 0x28 | `9b76ad2c55f93b01136a54251dcc93094247a2d192d2c701f9fabeb9733bef19` |
| `deadsync_dying_latch` | `0x44384C..0x443863` | 0x17 | `25c2ec170c0220eaf36b7883fd7b52b979829a6539d659c3570b46a2d4d43ccb` |
| `deadsync_0x400_latch` (S2) | `0x4438EB..0x44390B` | 0x20 | `a2958c2e2545974950d82bce86673f29e019a6bce21cd67fb3c5c0b5456db83d` |
| `deadsync_undying` (S3) | `0x44393D..0x443990` | 0x53 | `70ba8a4f595c6757d04352577204e49b856a8cd93ee3979aecc77166933da689` |
| `pred_netnpc_vt3C_0x43BD70` | `0x43BD70..0x43BD9A` | 0x2A | `b0791af77119cc5d8cf8378da7019ed57a5ebaa973cd47b89842a058fcb10947` |
| `pred_netnpc_vt40_0x43BDA0` | `0x43BDA0..0x43BDCC` | 0x2C | `82646de1ca08e023b25cd71fe64f9025bda929822ccf4d8233b0603c4011417a` |
| `pred_netactor_vt3C_0x454A70` | `0x454A70..0x454AB2` | 0x42 | `30b4504e946d31247088b36bf1acf2fd24ada548a0dd5a656a2475d91d907428` |
| `ctor_store_0x4573CA` | `0x4573C0..0x4573D5` | 0x15 | `82caa0a50d703d3872f625a19ac78c62b6a90b38918b0938e93cdba22e6f8907` |

---

## 10. เอกสารนี้ **ไม่** ทำอะไร

* ไม่แตะไฟล์ใด ๆ นอกจากตัวมันเอง (`pf_bridge/drafts/CHUNK2_Q3_BIND_THUNK_FINDINGS.md`)
* **ไม่เขียนอะไรเลยใน `Pirate Force ServerProject/`** — ไม่มี `src/`, `tests/`, `tools/`, `reports/`, `docs/`, `current/`
* ไม่ commit / add / checkout / reset / stash / clean · ไม่แตะ git index
* ไม่บูตเซิร์ฟเวอร์ · ไม่เปิด GameClient · ไม่แตะ database · ไม่เปิด socket · ไม่ต่อเน็ต
* ไม่แก้ไบนารี ไม่คัดลอกไบนารีเข้าทรี
* ไม่สร้าง ledger entry ไม่ flip matrix ไม่แก้ scenario
* **ไม่แก้ตัวเลขในเอกสารเก่าที่พบว่าคลาดเคลื่อน (§5.4)** — บันทึกไว้เฉย ๆ ให้รอบที่มีสิทธิ์เขียนเป็นคนตัดสิน
