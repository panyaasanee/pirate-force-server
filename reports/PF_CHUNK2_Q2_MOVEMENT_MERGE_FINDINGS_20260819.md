<!-- Imported into reports/ by chief round 96 (2026-08-20) from pf_bridge/drafts/CHUNK2_Q2_MOVEMENT_MERGE_FINDINGS.md
     (round 90 static RE lane worker output), byte-for-byte below this header.
     Reason: EVIDENCE-VISIBLE-001 discipline - the HYP-PF-025 ledger entry and the
     REMOTE-PLAYER-ENCODER-001 report cite these findings, and a citation must resolve
     inside the repository, not on one author's machine. -->

# CHUNK2-Q2 — `0x467130` MovementAttr apply/merge: ใครเป็น target, ใครเป็นคนเรียก, และเฟรม mask `0x01` ขยับจริงไหม

**สถานะ:** static reverse-engineering อ่านอย่างเดียวจาก `GameClient/GameClient.local.bin`
(14,759,424 bytes, sha256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`)
ไม่มี server / ไม่มี GameClient / ไม่มี network / ไม่มี database / ไม่แตะ `Pirate Force ServerProject/`
เครื่องมือ: python3 stdlib ล้วน (ไม่มี capstone ไม่มี pefile) — สคริปต์เต็มอยู่ท้ายไฟล์ §8

ปิด **ROW 4** ของ `drafts/MULTIPLAYER_CHUNK2_VISIBILITY_DESIGN_R90.md` §10
และปิด **ROW 5** ได้ด้วย (คำถาม "bind thunk `+0x38` ทำอะไรเมื่อ field ปลายทางไม่ใช่ NULL")

---

## 0. สรุปหนึ่งย่อหน้า (อ่านแค่นี้ก็พอถ้ารีบ)

โน้ตเดิมของ MOVE-PROJECT-001 §4 **ถูกครึ่งเดียวและวางผิดที่บนแผนที่**
`0x467130` มีอยู่จริงและเป็น mask-gated merge จริง — แต่ `this` ของมันคือ **attribute ใบที่เพิ่ง deserialize จากสาย**
ไม่ใช่ของที่ actor ถืออยู่ และมันไม่ได้อยู่บนเส้น "เอาค่าไปใส่ actor" เลย
มันอยู่ **ก่อนหน้านั้นหนึ่งสเตจ** ในตัว handler `0x5E4060` เอง:
ไคลเอนต์เก็บ **สำเนาเฟรมก่อนหน้า** ของ actor-entry collection ไว้ใน singleton `[0x01081A90]+0x154`
แล้วเอาใบใหม่ไป **เติมช่องที่ mask ไม่ได้ set จากสำเนาเก่า** ก่อน แล้วค่อยส่งใบที่เติมครบแล้ว
เข้าเส้น actor (`0x446F30` → vt `+0x20` → `0x5DF080` → bind thunk `0x469800` → `0x465450`)
ซึ่งจุดปลายนั้น **copy ครบทั้ง 7 ฟิลด์แบบไม่ดู mask เลย**

ผลจริง: เฟรม `MovementAttr(0x01)` ให้ identity ที่ client รู้จักแล้ว **ทำให้ actor ขยับ**
แต่ heading / mode / flags / f32x3 **ถูกเขียนทับด้วยเสมอ** — เขียนทับด้วยค่าจากสำเนาเฟรมก่อน *ถ้าเจอ*
และเขียนทับด้วย **ค่า ctor (0.0 / 0 ทั้งหมด)** ถ้าไม่เจอ
และ "เจอ" หมายถึงเจอใน **เฟรม RuntimeRes ใบก่อนหน้าใบล่าสุด** เท่านั้น ไม่ใช่ประวัติทั้งหมด

---

## 1. คำตอบ (a) — `0x467130` ใครเป็น target

### 1.1 การถอดรหัสไบต์ต่อไบต์ `[PROVEN VA=0x467130]`

```
00467130  56                 push  esi
00467131  57                 push  edi
00467132  8B 7C 24 0C        mov   edi, [esp+0x0C]      ; arg0  (ret 4 => stdcall/thiscall 1 arg)
00467136  8B F1              mov   esi, ecx             ; esi = this
00467138  85 FF              test  edi, edi
0046713A  74 7B              je    0x4671B7             ; arg == NULL -> ไม่ทำอะไร
0046713C  8B 07              mov   eax, [edi]
0046713E  8B 10              mov   edx, [eax]
00467140  8B CF              mov   ecx, edi
00467142  FF D2              call  edx                  ; arg->vt[0x00]()  -> type node
00467144  50                 push  eax
00467145  68 6C 34 03 01     push  0x0103346C           ; MovementAttr class token
0046714A  E8 61 81 42 00     call  0x0088F2B0           ; is-a
0046714F  0F B6 C0           movzx eax, al
00467152  83 C4 08           add   esp, 8
00467155  F7 D8              neg   eax
00467157  1B C0              sbb   eax, eax             ; 0 หรือ 0xFFFFFFFF
00467159  23 C7              and   eax, edi             ; eax = arg ถ้า is-a, ไม่งั้น 0
0046715B  74 5A              je    0x4671B7             ; ไม่ใช่ MovementAttr -> เงียบ
0046715D  8A 4E 4C           mov   cl, [esi+0x4C]       ; <<< mask ของ THIS (ไม่ใช่ของ arg)
00467160  F6 C1 01           test  cl, 0x01
00467163  75 10              jne   0x467175             ; <<< บิต SET  -> "ข้าม" ไม่ copy
00467165  F3 0F 7E 40 28     movq  xmm0, qword [eax+0x28]
0046716A  66 0F D6 46 28     movq  qword [esi+0x28], xmm0
0046716F  8B 50 30           mov   edx, [eax+0x30]
00467172  89 56 30           mov   [esi+0x30], edx      ;  arg -> this   (pos vec3)
00467175  F6 C1 02 / 75 06   test cl,2  / jne 0x467180
0046717A  D9 40 34 / D9 5E 34                            ;  arg -> this   (heading f32 @+0x34)
00467180  F6 C1 04 / 75 06   test cl,4  / jne 0x46718B
00467185  8A 50 38 / 88 56 38                            ;  arg -> this   (mode u8  @+0x38)
0046718B  F6 C1 08 / 75 06   test cl,8  / jne 0x467196
00467190  8B 50 3C / 89 56 3C                            ;  arg -> this   (flags u32 @+0x3C)
00467196  F6 C1 10 / 75 06 / D9 40 40 / D9 5E 40         ;  arg -> this   (f32 @+0x40)
004671A1  F6 C1 20 / 75 06 / D9 40 44 / D9 5E 44         ;  arg -> this   (f32 @+0x44)
004671AC  F6 C1 40 / 75 06 / D9 40 48 / D9 5E 48         ;  arg -> this   (f32 @+0x48)
004671B7  5F 5E              pop   edi / esi
004671B9  C2 04 00           ret   4
```

สองข้อที่ประโยคเดิมกำกวมและตอนนี้ปักแล้ว:

1. mask ที่อ่าน คือ **`[this+0x4C]`** = mask ของ **ตัวที่เป็น `this`** ไม่ใช่ของ argument
2. ทิศทาง copy คือ **`arg -> this`** — `this` เป็นปลายทางเสมอ, `arg` เป็นแหล่งค่าเสมอ

### 1.2 ประโยคที่โปรแกรมเมอร์เอาไปเขียนโค้ดได้เลย

จาก §2 (caller census) `this` = **ใบที่เพิ่งถอดมาจากสาย (incoming)** และ `arg` = **ใบที่ client เก็บไว้จากเฟรมก่อน (existing)**
ดังนั้น:

> **สำหรับฟิลด์ `heading` (bit `0x02`) เป็นตัวอย่าง:**
> ถ้าบิต `0x02` ใน mask ของใบ **incoming** **ไม่ถูก set** (= เราไม่ได้ส่ง heading มา) ค่าที่เหลืออยู่หลังสเตจนี้
> คือ **heading ของใบ existing** — คือ incoming ถูก *เติม* ด้วยค่าเก่า
> ถ้าบิต `0x02` **ถูก set** (= เราส่ง heading มา) ค่าที่เหลืออยู่คือ **heading ของใบ incoming** — ค่าเก่าไม่ถูกแตะ
> พูดอีกแบบ: `incoming` คือ sparse delta, `existing` คือ base, และ `0x467130` คือ
> `incoming = complete(incoming, existing)` **ไม่ใช่** `existing = merge(existing, incoming)`

เกรด: **`[PROVEN VA=0x467130]`** สำหรับกลไกภายในฟังก์ชัน
เกรด: **`[PROVEN VA=0x5DF8BC, 0x5E0359, 0x5DCBBE, 0x5DCB97, 0x5E406E]`** สำหรับ "ใครคือ this ใครคือ arg"
(ห่วงโซ่เต็มใน §2.3)

**หมายเหตุแก้เอกสารเก่า:** MOVE-PROJECT-001 §4 เขียนว่า "sparse movement delta ถูก complete ทับ projected state เดิม
โดยไม่ทับ field ที่ target ถืออยู่แล้ว" — ครึ่งแรก (complete sparse delta) **ถูก**, ครึ่งหลัง ("ไม่ทับ field ที่ target ถือ")
**ผิด** เพราะ `0x467130` ไม่ได้เขียนอะไรลงบน state ของ actor เลย มันเขียนลงบนใบ incoming เท่านั้น
ตัวที่เขียนทับ state ของ actor คือ `0x465450` และมันทับ **ทุกฟิลด์เสมอ**

---

## 2. คำตอบ (b) — caller census ของ `0x467130` + coverage

### 2.1 census ตรง

| target | `E8 rel32` (direct call) | `E9 rel32` (tail jump) | dword pointer ทั้งไฟล์ |
|---|---|---|---|
| **`0x467130`** | **0** | **0** | **1** — file off `0x00B0B528` = VA `0x00F0D128` |

`0x00F0D128` = `0xF0D0F8 + 0x30` = **MovementAttr vtable slot `+0x30`**
`0xF0D0F8` ถูกเขียนเป็น vtable pointer ที่ 4 จุด (`0x43BB62`, `0x43F905`, `0x442F46`, `0x46540D`)
ซึ่งยืนยันว่า `0xF0D0F8` เป็น **ฐาน** ของ vtable จริง ไม่ใช่ตำแหน่งกลางตาราง `[PROVEN]`

> **ทางเข้าเดียวของ `0x467130` คือ vtable slot `0xF0D0F8 + 0x30` เท่านั้น ไม่มี direct call ไม่มี tail jump
> ไม่มี pointer ที่ไหนอีกในไฟล์ทั้ง 14,759,424 ไบต์** `[PROVEN]`

### 2.2 census ของ dispatch shape `mov <r>,[<obj>+0x30] ; call <r>`

| รูปแบบ | จำนวน site ทั่ว exec region |
|---|---|
| loose (`8B /r` mod=01 disp8=`0x30` + `FF D<r>` ภายใน 16 ไบต์) | **141** |
| strict (บังคับให้มี `mov <r>,[obj]` โหลด vtable นำหน้า) | **91** |

ในจำนวนนี้ **resolve ได้ 1 จุด** ด้วยการถอดฟังก์ชันที่ครอบมันจริง ๆ:
**`0x5DF8BC`** (`8B 50 30` = `mov edx,[eax+0x30]`, `call edx` ที่ `0x5DF8C0`) ในลูป `0x5DF850`
อีก 140 จุด **ยังไม่ resolve** — ดู §7 ข้อ 1 (นี่คือรูโหว่แบบเดียวกับ 229 sites ของ `+0x20`
ที่ RUNTIMERES-ACTOR-ENTRY-001 บันทึกไว้ ไม่ได้แคบลง)

### 2.3 ห่วงโซ่จริงจาก packet ถึง `0x467130` — ทุกขา `[PROVEN]`

```
0x5E4060  GSCN_RunTimeProtocolRes inbound handler   (vtable 0xF2FFC0 +0x1C ; dword occ 1 @0xF2FFDC)
  |
  |-- 0x5E4066  push esi(packet) ; call 0x4011A0  -> singleton [0x01081A90] (0x1A8 bytes, สร้างครั้งเดียว)
  |   0x5E406E  call 0x5DCB40      ***** สเตจ "รวมกับสำเนาเฟรมก่อน" *****       E8=1 (จุดนี้จุดเดียว)
  |     |
  |     |-- 0x5DCB8E  lea esi,[ebp+0x154]        ; ebp = singleton, +0x154 = cache slot ของ stream +0x1C
  |     |   0x5DCB97  cmp dword [esi],0
  |     |   0x5DCBA0  je  0x5DCBD9               ; cache ว่าง -> ข้าม merge ทั้งดุ้น
  |     |   0x5DCBA9  call 0x5DC980              ; = `mov ecx,[packet+0x1C]` -> ACTOR-ENTRY COLLECTION
  |     |   0x5DCBBE  push esi (cache)  ; ecx = ใบใหม่
  |     |   0x5DCBC1  call 0x5E0270              E8=1 (จุดนี้จุดเดียว)
  |     |     |
  |     |     |-- วนทุก entry ของ collection **ใหม่** ([this+0x28] list)
  |     |     |   0x5E02EF  อ่าน identity qword ที่ entry+0x18/+0x1C
  |     |     |   0x5E030C  call 0x493880        ; find identity นั้นใน map ของ collection **เก่า** (*arg0 + 0x10)
  |     |     |   0x5E034F  mov dl,[old+0x10] ; cmp dl,[new+0x10]   ; actor_type ต้องตรงกัน
  |     |     |   0x5E0355  jne  ข้าม
  |     |     |   0x5E0359  mov edx,[eax+0x14] ; push ebx(old) ; mov ecx,esi(new) ; call edx
  |     |     |              = entry vtable 0xF2FE78 **+0x14** = 0x5DF850
  |     |     |     |
  |     |     |     |-- 0x5DF850 วนทุก attr ของ entry **ใหม่**
  |     |     |         0x5DF88B  attr->vt[+0x10]() = get id
  |     |     |         0x5DF896  call 0x5DEFF0   ; หา attr id เดียวกันใน entry **เก่า**
  |     |     |         0x5DF89F  je   ข้ามถ้าไม่เจอ
  |     |     |         0x5DF8BC  mov edx,[eax+0x30] ; push ebx(old attr) ; call edx  <<<< 0x467130
  |     |
  |     |-- 0x5DCBFE/0x5DCC00  mov ecx,[edi] ; mov [esi],ecx   ; cache := collection ใหม่ (ที่เติมครบแล้ว)
  |     |-- 0x5DCC20..0x5DCC90  ทำซ้ำทั้งชุดกับ stream **+0x20** (cache slot ที่ singleton+0x158, ผ่าน 0x5DC9B0)
  |
  |-- 0x5E4073  mov eax,[esi+0x1C] ; add eax,0x10 ; call 0x402A20 (actor manager singleton)
      0x5E4085  call 0x446F30      ***** สเตจ "เอาเข้า actor" *****   E8=1, dword occ 0
        |
        |-- (identity เจอ) actor vtable +0x20 -> 0x4446F0
              0x4446FE  call 0x5DF080     ; วนทุก attr: attr->vt[+0x38](actor)
                 |
                 |-- 0x5DF0B7  mov edx,[eax+0x38] ; push ebx(actor) ; call edx   = 0x469800
                       |
                       |-- 0x469835  mov edx,[this_vt+0x24] ; push [actor+0x244] ; call = 0x465450
                             |
                             |-- 0x465481  call 0x4676A0        ; copy identity qword + byte@+0x12
                             |   0x465486..0x4654B9              ; copy 7 ฟิลด์ **ไม่มี test mask เลย**
              0x444705  call 0x4437C0     ; dead-sync
              0x44470A  mov ecx,[esi+0x244] ; push ; lea ecx,[esi+0xD8] ; 0x444717 call 0x440170
              0x444723  mov byte [actor+0x128],1 ; actor->vt[+0x24]()
```

census ที่ยึดห่วงโซ่นี้ไว้ (ทุกบรรทัดคือผลจริงจากสคริปต์ §8):

| function | `E8` | `E9` | dword ptr |
|---|---|---|---|
| `0x467130` MovementAttr merge (vt `+0x30`) | 0 | 0 | 1 (`0xF0D128`) |
| `0x465450` MovementAttr commit (vt `+0x24`) | 0 | 0 | 1 (`0xF0D11C`) |
| `0x469800` MovementAttr bind thunk (vt `+0x38`) | 0 | 0 | 1 (`0xF0D130`) |
| `0x469760` ActorAttr bind thunk (vt `+0x38`) | 0 | 0 | 1 (`0xF0E7D8` = `0xF0E7A0+0x38`) |
| `0x5DF850` per-attr merge loop | 0 | 0 | 1 (`0xF2FE8C` = entry vt `+0x14`) |
| `0x5DF7C0` per-attr delta loop | 0 | 0 | 1 (`0xF2FE88` = entry vt `+0x10`) |
| `0x5DF080` per-attr bind loop | 3 (`0x4446FE`, `0x454949`, `0x45D24A`) | 0 | 0 |
| `0x5DEFF0` find-attr-by-id | 2 (`0x5DF806`, `0x5DF896`) | 0 | 0 |
| `0x5E0270` per-identity entry merge | **1** (`0x5DCBC1`) | 0 | 0 |
| `0x5DCB40` cache stage | **1** (`0x5E406E`) | 0 | 0 |
| `0x5E4060` inbound handler | 0 | 0 | 1 (`0xF2FFDC`) |
| `0x4446F0` actor vt `+0x20` update | 1 (`0x4566A7`) | 0 | 4 |

### 2.4 COVERAGE — ตัวเลข ไม่ใช่คำคุณศัพท์

| การกวาด | ขอบเขต | จำนวนไบต์ |
|---|---|---|
| `E8`/`E9` rel32 | **ทุก executable section** = `.text` (raw 8,621,056) + `.code` @`0xC3A000` (raw 1,024) | **8,622,080** |
| dword pointer (ทุก alignment) | **ทั้งไฟล์** | **14,759,424** |
| dispatch shape `[reg+0x30]` / `[reg+0x14]` | ทุก executable section | **8,622,080** |

section ทั้ง 6 ที่อ่านจาก PE header:
`.text` VA `0x00401000` VS `0x838A2C` raw `0x400`/`0x838C00` **EXEC** ·
`.code` VA `0x00C3A000` VS `0x2E1` raw `0x839000`/`0x400` **EXEC** ·
`.rdata` `0x00C3B000` · `.data` `0x0101A000` · `.rsrc` `0x0109C000` · `.reloc` `0x010F5000`

**ไม่มีการ disassemble แบบ linear ที่ไหนเลย** — ทุก census เป็น byte-pattern scan ที่ลองทุก offset
เป็นจุดเริ่ม opcode ดังนั้นไม่มีโหมดพัง "decoder หยุดที่ไบต์แรกที่ถอดไม่ได้แล้วประกาศ negative"
แบบที่รอบ 83 เสียเลนไป negative ทุกอันในเอกสารนี้ครอบคลุมตัวเลขข้างบนเต็มจำนวน

### 2.5 การ re-derive คำตอบที่โปรเจกต์ปักไว้แล้ว (ทดสอบเครื่องมือก่อนเชื่อ)

คำตอบที่ตีพิมพ์แล้วและตรวจได้: *"`0x446F30` มี direct caller **หนึ่งเดียว** ในอิมเมจ และ **ศูนย์** pointer
occurrence ในไฟล์ 14,759,424 ไบต์"* (RUNTIMERES-ACTOR-ENTRY-001)

รันด้วยเครื่องมือรอบนี้ ได้ผลตรงคำต่อคำ:

```
--- KNOWN-ANSWER RE-DERIVATION (published: 0x446F30 = 1 direct caller, 0 pointers) ---
0x446F30  E8=1 ['005E4085']  E9=0  dwordptr=0 []
```

**ผ่าน** — และได้ของแถมอีกอันที่ตรงกับที่ตีพิมพ์ไว้เหมือนกัน:
`0x4446F0` = **1 direct caller + 4 vtable slots** (รายงานเก่าเขียนว่า "1 direct caller + 4 vtable slots")
สคริปต์รอบนี้ให้ `E8=1 (0x4566A7)`, `dword=4 (0xF0D3C0, 0xF0DF78, 0xF0E018, 0xF0E0E8)` **ผ่าน**

---

## 3. คำตอบ (c) — bind thunk `0x469800` (และ `0x469760`) ทั้งสองกิ่งของ `je`

### 3.1 `0x469800` = MovementAttr vtable `+0x38` `[PROVEN VA=0x469800]`

```
00469800  56                 push  esi
00469801  8B 74 24 08        mov   esi, [esp+8]         ; arg0 = container ที่ยื่นมาให้ bind
00469805  57                 push  edi
00469806  8B F9              mov   edi, ecx             ; edi = this = ตัว attribute เอง
00469808  85 F6              test  esi, esi
0046980A  74 31              je    0x46983D             ; ---- กิ่งที่ 1 ของ je : arg NULL -> ไม่ทำอะไร
0046980C  8B 06              mov   eax, [esi]
0046980E  8B 10              mov   edx, [eax]
00469810  8B CE              mov   ecx, esi
00469812  FF D2              call  edx                  ; arg->vt[0x00]()
00469814  50                 push  eax
00469815  68 88 CE 02 01     push  0x0102CE88           ; token CActorBaseClient
0046981A  E8 91 5A 42 00     call  0x0088F2B0           ; is-a
0046981F  0F B6 C0 / 83 C4 08 / F7 D8 / 1B C0
00469829  23 C6              and   eax, esi
0046982B  74 10              je    0x46983D             ; ---- กิ่งที่ 2 ของ je : ไม่ใช่ CActorBaseClient -> ไม่ทำอะไร
0046982D  8B 17              mov   edx, [edi]           ; vtable ของ THIS (ของ attribute)
0046982F  8B 80 44 02 00 00  mov   eax, [eax+0x244]     ; <<< สมาชิกของ actor ที่ offset +0x244
00469835  8B 52 24           mov   edx, [edx+0x24]      ; <<< THIS->vtable[+0x24]   (ไม่ใช่ +0x30)
00469838  50                 push  eax
00469839  8B CF              mov   ecx, edi
0046983B  FF D2              call  edx
0046983D  5F 5E              pop   edi / esi
0046983F  C2 04 00           ret   4
```

**คำตอบตรงคำถาม:** thunk ตัวนี้ **ไม่ได้ไป vtable `+0x30` ทั้งสองกิ่ง** — สมมติฐานในโจทย์ผิด
กิ่งที่ **je ถูก take** (ทั้งสองอัน) = ออกทันที ไม่ทำอะไรเลย
กิ่งที่ **je ไม่ถูก take** (คือ `arg != NULL` **และ** `arg` เป็น `CActorBaseClient` จริง)
= เรียก **`this->vtable[+0x24]( *(void**)(arg + 0x244) )`** ซึ่งสำหรับ MovementAttr คือ **`0x465450`**
`je` ทั้งคู่จึงเป็น **type gate** ไม่ใช่ "เช็คว่า bind แล้วหรือยัง"

vtable ที่เกี่ยวข้อง `[PROVEN]`
`0xF0D0F8` (MovementAttr): `+0x10`=`0x43BBB0` · `+0x24`=**`0x465450`** · `+0x28`=`0x467030` ·
`+0x2C`=`0x467040` · `+0x30`=**`0x467130`** · `+0x34`=`0x4671C0` · `+0x38`=**`0x469800`**

### 3.2 `0x469760` = ActorAttr vtable `+0x38` — โครงเดียวกัน byte ต่อ byte ต่างแค่สองค่า

`[PROVEN VA=0x469760]` token = `0x0102CB2C` (ไม่ใช่ `0x0102CE88`) · offset สมาชิก = `[arg+0x348]` (ไม่ใช่ `+0x244`)
ปลายทางเดียวกัน: `this->vtable[+0x24](...)`
`0xF0E7A0` (ActorAttr): `+0x10`=`0x464E40` · `+0x24`=**`0x464F30`** · `+0x28`=`0x465990` ·
`+0x2C`=`0x4659B0` · `+0x30`=**`0x465E60`** · `+0x34`=`0x466230` · `+0x38`=`0x469760`

**แก้เอกสารเก่า:** §10 ข้อ 1 ของ R90 เขียนว่า "merge `0x469760 -> 0x464F30`"
`0x464F30` คือ **commit เข้า actor** (slot `+0x24`) ไม่ใช่ merge · merge จริงของ ActorAttr คือ **`0x465E60`** (slot `+0x30`)

### 3.3 `0x465450` — ปลายทางจริงของ thunk และเป็นที่ที่ state ของ actor ถูกเขียน `[PROVEN VA=0x465450]`

```
00465450  53 / 8B 5C 24 08   push ebx / mov ebx,[esp+8]   ; ebx = actor->[+0x244] = MovementAttr ที่ actor ถืออยู่
00465455  57 / 8B F9         push edi / mov edi,ecx       ; edi = this = ใบ incoming
00465458  85 DB / 74 5F      test ebx,ebx / je 0x4654BB   ; ปลายทาง NULL -> เงียบ
0046545C..0046547A            arg->vt[0]() ; is-a token 0x0103346C ; and esi,ebx
0046547C  74 3C              je 0x4654BA                  ; ปลายทางไม่ใช่ MovementAttr -> เงียบ
0046547E  56 / 8B CF
00465481  E8 1A 22 00 00     call 0x4676A0                ; copy identity qword (+0x18/+0x1C) + byte +0x12  this -> arg
00465486  F3 0F 7E 47 28 / 66 0F D6 46 28    movq  [esi+0x28] <- [edi+0x28]
00465490  8B 47 30 / 89 46 30                mov   [esi+0x30] <- [edi+0x30]
00465496  D9 47 34 / D9 5E 34                fld/fstp  [esi+0x34] <- [edi+0x34]
0046549C  8A 4F 38 / 88 4E 38                mov   [esi+0x38] <- [edi+0x38]
004654A2  8B 57 3C / 89 56 3C                mov   [esi+0x3C] <- [edi+0x3C]
004654A8  D9 47 40 / D9 5E 40                        [esi+0x40] <- [edi+0x40]
004654AE  D9 47 44 / D9 5E 44                        [esi+0x44] <- [edi+0x44]
004654B4  D9 47 48 / D9 5E 48                        [esi+0x48] <- [edi+0x48]
004654BA  5E / 5F / 5B / C2 04 00
```

**ไม่มี `test byte [edi+0x4C], ...` แม้แต่ตัวเดียวในทั้งฟังก์ชัน** — ทั้ง 7 กลุ่มฟิลด์ถูก copy เสมอ
นี่คือคำตอบตรงของ **ROW 5** ด้วย: thunk `+0x38` **ไม่ใช่ "bind ทับ vs merge"** เพราะมันไม่ได้ผูก pointer ใด ๆ
มันเป็น **copy ฟิลด์เข้าไปในวัตถุที่ actor เป็นเจ้าของอยู่แล้ว** เฟรมซ้ำ identity เดิมจึง **"ทับ" เสมอ**

---

## 4. คำตอบ (d) — ส่ง `MovementAttr` mask `0x01` ให้ identity ที่ client รู้จักแล้ว: ขยับ หรือถูกกลืน

### 4.1 คำตอบ

> **ขยับ ไม่ถูกกลืน** — และ **ฟิลด์ที่ไม่ได้ส่งก็ถูกเขียนทับด้วยเสมอ ไม่ว่าจะมี cache หรือไม่**

เพราะเส้นทางที่ตัดสินคือ `0x465450` ซึ่ง copy ทั้ง 7 กลุ่มโดยไม่ดู mask
`0x467130` มีผลแค่ว่า *ค่าอะไร* จะไปนั่งในช่องที่เราไม่ได้ส่ง

สองกรณี:

| สภาพ cache `[0x01081A90]+0x154` ตอนเฟรมมาถึง | ผลบน actor |
|---|---|
| **มี entry ของ identity เดียวกัน และ `actor_type` byte `+0x10` ตรงกัน** | pos = ของเรา · heading/mode/flags/f32x3 = **ค่าจากเฟรม RuntimeRes ใบก่อนหน้า** |
| **ไม่มี** (cache NULL, ไม่มี identity นั้น, actor_type ไม่ตรง, หรือใบเก่าไม่มี `MovementAttr`) | pos = ของเรา · heading = **0.0f** · mode = **0** · flags = **0** · f32x3 = **0.0f** |

ค่า default มาจาก ctor `0x465400` `[PROVEN VA=0x465400]`:
`xorps xmm0,xmm0` แล้ว `movss` ลง `+0x28/+0x2C/+0x30/+0x34/+0x40/+0x44/+0x48`,
`mov byte [esi+0x10],3`, `mov byte [esi+0x11],1`, **`mov byte [esi+0x4C],0xFF`**, `mov [esi+0x38],al`, `mov [esi+0x3C],eax`
(mask ตอนสร้าง = `0xFF` แล้วถูก deserializer เขียนทับด้วย mask จากสาย — `Serial 0x4671C0` ที่ `0x4671D8`
`lea ebx,[esi+0x4C]` แล้วยิง codec tag `0x0B` width 1 `[PROVEN VA=0x4671D8]`)

### 4.2 กับดักที่ดีไซน์ R90 §5 เฟรม 3 เดินเข้าเต็ม ๆ

cache เป็น **pointer เดียว** ที่ singleton `+0x154` และ `0x5DCC00` **แทนที่ทั้งก้อน** ด้วย collection ของเฟรมล่าสุด
มันไม่ใช่ประวัติสะสม มันคือ **"เฟรมที่แล้วเฟรมเดียว"**

ตารางเฟรมของ R90: 1=A spawn(0s) · 2=B spawn(6s) · **3=A move mask 0x01 (12s)** · 4=A mask 0x03 (18s) · 5=C(24s)
ทุกเฟรมส่ง `count = 1`

- ตอนเฟรม 3 มาถึง cache ถือเฉพาะ **entry ของ B** → หา identity A **ไม่เจอ** → `0x5DF850` ไม่เคยถูกเรียกกับ A
  → `0x467130` ไม่ทำงาน → actor A ได้ pos ใหม่ **แต่ heading/mode/flags/f32x3 = 0**
- ตอนเฟรม 4 มาถึง cache ถือ entry ของ **A จากเฟรม 3** (ซึ่งมีแค่ `MovementAttr`) → **เจอ** → merge ทำงาน
  → ฟิลด์ที่ไม่ได้ส่งได้ค่าจากเฟรม 3 ซึ่งก็คือ **0 อยู่ดี**

เกรดของคำตอบ (d):

| ส่วน | เกรด |
|---|---|
| "actor ขยับจริง ไม่ถูกกลืน" | **`[PROVEN VA=0x5DF080, 0x469800, 0x465450, 0x444717]`** |
| "ฟิลด์ที่ไม่ได้ส่งถูกเขียนทับเสมอ (ไม่มี mask gate ที่ปลายทาง)" | **`[PROVEN VA=0x465450]`** — ทั้งฟังก์ชันไม่มี `F6 4x 4C` |
| "ค่าที่ไปแทนคือของเฟรมก่อน ถ้าเจอใน cache" | **`[PROVEN VA=0x467130, 0x5DF8BC, 0x5E0359, 0x5DCB97]`** |
| "cache = เฟรมล่าสุดเฟรมเดียว ไม่ใช่ประวัติ" | **`[PROVEN VA=0x5DCBFE, 0x5DCC00]`** (`mov ecx,[edi]` / `mov [esi],ecx`) |
| "ค่า default คือศูนย์ทั้งหมด" | **`[PROVEN VA=0x465400]`** |
| "`[actor+0x244]` เป็น MovementAttr instance เสมอ" | **`[INFERRED]`** — ดู §7 ข้อ 2 |
| "actor ขยับ **บนจอ**" | **`[GUESS]` — หยุดตรงนี้** ไม่มีอะไร static พิสูจน์การเรนเดอร์ ต้องยิงจริง |

### 4.3 สิ่งที่ควรทำกับ encoder (ข้อเสนอ ไม่ใช่คำสั่ง — เลนนี้ไม่แตะโค้ด)

จากไบต์ล้วน ๆ: **mask `0x01` ไม่ได้ให้ผลอย่างที่ docstring ของ `v141:1220-1223` เข้าใจ**
docstring เขียนว่า *"so the client can merge a position delta without overwriting the existing locomotion/control fields"*
— ข้อความนี้ **ผิด** ตามไบต์ ฟิลด์เหล่านั้นถูกเขียนทับทุกครั้ง คำถามมีแค่ว่าเขียนทับด้วย 0 หรือด้วยค่าเฟรมก่อน
ถ้าเป้าหมายคือ "ควบคุมสิ่งที่ actor ได้รับให้ครบและแน่นอน" ทางที่ตรงกับไบต์คือ **ส่ง mask เต็ม `0xFF` ทุกเฟรม**
แล้วให้ server เป็นคนถือ state ครบ ไม่พึ่ง cache ฝั่ง client ที่มีอายุแค่หนึ่งเฟรม
(ถ้าอยากทดสอบตัว merge จริง ๆ ต้องส่งสองเฟรม **ติดกัน** ที่มี identity เดียวกัน ไม่มีเฟรมอื่นคั่น)

---

## 5. Byte spans + sha256 (ให้รอบถัดไป re-pin ได้)

| span | ช่วง VA | sha256 |
|---|---|---|
| `0x467130` merge ทั้งฟังก์ชันรวม `ret` | `00467130..004671BC` | `97dd85ca3425b380316a047878f41b8bfd5497d9d400b51204dbdef2dc9b3b88` |
| `0x467130` body-only (pin เดิมของ MOVE-PROJECT-001) | `00467130..004671B7` | `948b665113c120ae5d2ffe1c1bbd292182058c704106d1bc3fdf764890a27e91` |
| `0x465450` commit เข้า actor (vt `+0x24`) | `00465450..004654C0` | `afbbbd83879f29460b09590f336acf5e21758a944a9e6ba390553c282256d4a1` |
| `0x469800` bind thunk MovementAttr (vt `+0x38`) | `00469800..00469840` | `368a83127f68c19688c2c32708662c381081d831c0d41fd4a3682cd28220b227` |
| `0x469760` bind thunk ActorAttr (vt `+0x38`) | `00469760..004697A0` | `b122bab7259bf0c83f8fd94c9bc89b1abcd69ddef82e05c5e664a62cfbabb7df` |
| `0x4676A0` identity-header copy | `004676A0..004676E3` | `469a79c392341d4f22831b1cb39c57895cd4bab64a5ce98aa3022056062d86d0` |
| `0x467030` reset (mask := `0xFF`) | `00467030..00467039` | `f20e75abd798ab2c2db32a1535fce2ca0b29dfe73d5e070da3eb8079ae6ab454` |
| `0x5DF080` per-attr bind loop (vt `+0x38`) | `005DF080..005DF0D0` | `02f92197947b7d83df6b1faf6d9d6a2fd1ddeaf7993881d3d03885bc2fd19a46` |
| `0x5DF850` per-attr merge loop (vt `+0x30`) | `005DF850..005DF8D7` | `87bb2e82c65f830746873e2c903417f06a0977f5b36d153c758691770ae83aff` |
| `0x5DEFF0` find-attr-by-id | `005DEFF0..005DF074` | `8c29333b6a386de8413667fa96fcd11e5adaf42a7c4f9809d6555eb0dfa5d728` |
| `0x5E0270` per-identity entry merge | `005E0270..005E038F` | `287383ea571e5356bc30929bae321016cc12bcaa131887ac317beccaa33daa31` |
| `0x5DCB40` last-known-state cache stage | `005DCB40..005DCC10` | `65d14600a5532f56af075783623c4877f0c9a1fa9341165febd98d0eceeae789` |
| `0x5E4060` inbound handler (หัว) | `005E4060..005E408A` | `da8fe015634f5657554e1327e95190702e04b7dd2b38b7b2d7455550647ec2ef` |
| `0x4446F0` actor vt `+0x20` update | `004446F0..00444730` | `e4e5b3719b24f7ee32791e4a419ff37942031610691f25c4d943cae9f1ae4508` |
| vtable MovementAttr `+0x00..+0x3C` | `00F0D0F8..00F0D138` | `e3f8cdd6761046e2e45b0dd871c4dfe2d71cee69351bc23b7ddf84301ae53538` |
| vtable actor-entry `+0x00..+0x1C` | `00F2FE78..00F2FE98` | `ceccb92c349bb18770da2295510adad98d4ae8d4a713132e9d229d752143da22` |

---

## 6. สิ่งที่รอบนี้แก้ให้เอกสารเดิม

| เอกสาร | ข้อความเดิม | สถานะหลังรอบนี้ |
|---|---|---|
| MOVE-PROJECT-001 §4 | "อ่าน field mask ของ **target** @+0x4C แล้ว copy เฉพาะ field ที่ bit ไม่ถูก set … โดยไม่ทับ field ที่ target ถืออยู่แล้ว" | ครึ่งแรกถูก (`this` เป็นทั้ง mask-owner และปลายทาง) · ครึ่งหลัง **ผิด** — `0x467130` ไม่แตะ state ของ actor เลย |
| R90 §10 ROW 4 | "ยังไม่ปักว่าใครเรียก `0x467130`" | **ปักแล้ว** — vtable slot `0xF0D128` จุดเดียว, dispatch ที่ `0x5DF8BC`, ห่วงโซ่ถึง `0x5E4060` มี E8=1 ทุกขา |
| R90 §10 ROW 4 | "อ่าน bind thunk `0x469800` ให้จบว่ากิ่งไหนไป vt `+0x30`" | **ไม่มีกิ่งไหนไป `+0x30`** — thunk ไป `+0x24` เท่านั้น สมมติฐานของคำถามผิด |
| R90 §10 ROW 5 | "bind thunk `+0x38` ทำอะไรเมื่อ field ปลายทางไม่ใช่ NULL (bind ทับ vs merge)" | **ไม่ใช่ทั้งสองอย่าง** — ไม่มีการเขียน pointer เลย มันคือ field copy เข้าวัตถุที่ actor เป็นเจ้าของ = "ทับ" เสมอ · `je` สองอันคือ NULL-check และ type-gate |
| R90 §10 ROW 1 | "merge `0x469760 -> 0x464F30`" | `0x464F30` = commit (slot `+0x24`) · merge จริงของ ActorAttr = **`0x465E60`** (slot `+0x30`) |
| R90 §5 เฟรม 3 เหตุผลใช้ mask `0x01` (อ้าง `v141:1220-1223`) | "merge a position delta without overwriting the existing locomotion/control fields" | **ผิดตามไบต์** — ฟิลด์เหล่านั้นถูกเขียนทับทุกครั้ง |

---

## 7. สิ่งที่ยังตอบไม่ได้

1. **140 จาก 141 dispatch site ของรูป `mov <r>,[reg+0x30]; call <r>` ยังไม่ resolve**
   รอบนี้ถอดได้จุดเดียวคือ `0x5DF8BC` ที่เห็นชัดว่าเดินบน attr object เพราะฟังก์ชันที่ครอบมันคือ `0x5DF850`
   ทางทฤษฎีอาจมีที่อื่นยื่น MovementAttr เข้า `+0x30` — ความเสี่ยงต่ำเพราะวัตถุ MovementAttr
   อยู่ในลิสต์ attr เท่านั้น แต่ **นี่เป็นการอ่านระดับ class-2 ไม่ใช่ census ปิด** และมันคือรูโหว่แบบเดียวกับ
   229 sites ของ `+0x20` ที่ RUNTIMERES-ACTOR-ENTRY-001 บันทึกไว้ **รอบนี้ไม่ได้ทำให้แคบลง**
   (`[reg+0x14]` มี 292 loose / 185 strict — ก็ resolve ได้จุดเดียวคือ `0x5E0359` เหมือนกัน)
2. **`[actor+0x244]` เป็น instance ของ MovementAttr จริงไหม** — `[INFERRED]`
   ปักได้แค่ว่ามี store ไปที่ `[esi+0x244]` ที่ `0x443393` (ในสาย ctor ของ actor base ต่อจาก `call 0x43F960`)
   `0x465450` มี is-a guard ต่อ token `0x0103346C` อยู่แล้ว ดังนั้นถ้าไม่ใช่ ก็เป็น **no-op เงียบ**
   ซึ่งจะทำให้คำตอบ (d) พลิกเป็น "ถูกกลืน" ทันที — เป็น falsification ข้อแรกที่ควรดูถ้า GT ไม่ขยับ
   store ทั้งหมดไปยัง `[reg+0x244]` ในอิมเมจ: `0x443393`, `0x4C079E`, `0x5831D2`, `0x583C4A`, `0x674C30`,
   `0x675813`, `0xB16C80`, `0xB16E27` (8 จุด, กวาดครบ 8,622,080 ไบต์)
3. **cache `[0x01081A90]+0x154` ถูกล้างเมื่อไร** — ยังไม่ไล่ว่ามีใครเซ็ตเป็น NULL ตอนเปลี่ยนซีน / logout /
   reconnect หรือไม่ ถ้ามี พฤติกรรมข้าม session จะต่างจากที่เขียนใน §4
4. **`0x493880` (map find ของ identity)** ยังไม่ถอด — สมมติจากรูปการใช้งานว่าเป็น
   `find(key qword)` ที่คืน iterator ถ้าถอดแล้วพบว่าเป็น lower_bound ที่ไม่ตรวจ equality
   ข้อสรุปเรื่อง "เจอ/ไม่เจอ" จะต้องทบทวน `[INFERRED]`
5. **`0x5DC980` คืน `[packet+0x1C]` ก็จริง แต่ `0x5DCB40` ทำสเตจเดียวกันกับ `[packet+0x20]` ด้วย
   (cache slot `+0x158`, ผ่าน `0x5DC9B0`)** — ยังไม่ได้ไล่ว่าสตรีม `+0x20` คือใครและมี attr อะไร
6. **`0x467040` (delta, vt `+0x2C`) กับลูป `0x5DF7C0` (entry vt `+0x10`) ยังไม่มี caller ที่ resolve แล้ว**
   census ให้ `E8=0 / dword=1` เหมือนกัน — ขาส่งออกจึงยัง **ไม่** ถูกปักในรอบนี้
7. **`0x402A20` (actor manager) และเงื่อนไขเพิ่มของ `actor_type 2`** — ไม่ได้แตะ (R90 §10 ข้อ 6 ยังเปิดอยู่)
8. **ไม่มีข้ออ้างใด ๆ เกี่ยวกับเซิร์ฟเวอร์ต้นฉบับ** ไม่มี capture, ไม่มี runtime observation,
   ไม่มีข้ออ้างเรื่องการเรนเดอร์ ไม่มี ledger entry ไม่มีการ flip matrix row เอกสารนี้ report-only

---

## 8. สคริปต์ที่ใช้ (รันซ้ำได้ทั้งดุ้น, stdlib ล้วน)

รันจากโฟลเดอร์ที่มี `GameClient/GameClient.local.bin`:
`py -3 - < CHUNK2_Q2.py` หรือวางบล็อกนี้ลงไฟล์ชั่วคราวแล้วรัน

```python
import hashlib, struct
BIN = "GameClient/GameClient.local.bin"
data = open(BIN, "rb").read()
SHA  = hashlib.sha256(data).hexdigest().upper()
print("BIN size=%d sha256=%s" % (len(data), SHA))
assert len(data) == 14759424
assert SHA == "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

_e = struct.unpack_from("<I", data, 0x3C)[0]; _c = _e + 4
_n = struct.unpack_from("<H", data, _c + 2)[0]
_os= struct.unpack_from("<H", data, _c + 16)[0]; _o = _c + 20
IMAGE_BASE = struct.unpack_from("<I", data, _o + 28)[0]
_s = _o + _os
SECS = []
for i in range(_n):
    p = _s + i*40
    nm = data[p:p+8].rstrip(b"\0").decode("latin1")
    vs, va, rs, rp = struct.unpack_from("<IIII", data, p+8)
    ch = struct.unpack_from("<I", data, p+36)[0]
    SECS.append((nm, va, vs, rp, rs, ch))
EXEC = [(nm, IMAGE_BASE+va, vs, rp, rs) for nm,va,vs,rp,rs,ch in SECS if ch & 0x20000000]

def va2off(va):
    r = va - IMAGE_BASE
    for nm,v,vs,rp,rs,ch in SECS:
        if v <= r < v + max(vs,rs):
            off = rp + (r - v)
            return off if off < len(data) else None
    return None
def off2va(off):
    for nm,v,vs,rp,rs,ch in SECS:
        if rp <= off < rp+rs: return IMAGE_BASE + v + (off - rp)
    return None
def dw(va):
    o = va2off(va)
    return struct.unpack_from("<I", data, o)[0] if o is not None else None
def span_sha(lo,hi): return hashlib.sha256(data[va2off(lo):va2off(hi)]).hexdigest()
def hexdump(lo,hi,label=""):
    print("=== %s %08X..%08X ===" % (label, lo, hi))
    o = va2off(lo); b = data[o:o+(hi-lo)]
    for i in range(0, len(b), 16):
        print("%08X  %-47s  %s" % (lo+i, " ".join("%02X"%c for c in b[i:i+16]),
              "".join(chr(c) if 32 <= c < 127 else "." for c in b[i:i+16])))
def rel32_sites(target, opcode):
    """ทุก `opcode rel32` ใน EVERY executable section ที่ปลายทาง == target."""
    out = []; pat = bytes([opcode])
    for nm,va0,vs,rp,rs in EXEC:
        end = rp+rs; i = data.find(pat, rp, end-5)
        while i >= 0:
            rel = struct.unpack_from("<i", data, i+1)[0]; va = off2va(i)
            if va is not None and ((va+5+rel)&0xFFFFFFFF) == target: out.append(va)
            i = data.find(pat, i+1, end-5)
    return sorted(out)
def dword_occ(v):
    """ทุกตำแหน่งในไฟล์ ทุก alignment ที่ v ปรากฏเป็น LE dword (vtable/jump table/imm32/FF15)."""
    pat = struct.pack("<I", v); out=[]; i=data.find(pat)
    while i>=0: out.append((i, off2va(i))); i=data.find(pat,i+1)
    return out
def census(t): return rel32_sites(t,0xE8), rel32_sites(t,0xE9), dword_occ(t)
def calltgt(va):
    o = va2off(va)
    if data[o] != 0xE8: return None
    return (va + 5 + struct.unpack_from("<i", data, o+1)[0]) & 0xFFFFFFFF
def vt_sites(disp, strict):
    """`mov <r>,[<reg>+disp8]` ตามด้วย `call <r>` ภายใน 16 ไบต์ (byte match ล้วน ไม่ decode)."""
    out=[]
    for nm,va0,vs,rp,rs in EXEC:
        b = data[rp:rp+rs]
        for i in range(2, len(b)-3):
            if b[i]!=0x8B: continue
            m=b[i+1]
            if (m>>6)!=1 or (m&7)==4 or b[i+2]!=disp: continue
            if bytes([0xFF,0xD0+((m>>3)&7)]) not in b[i+3:i+19]: continue
            if strict:
                p0,p1=b[i-2],b[i-1]
                if not (p0==0x8B and (p1>>6)==0 and ((p1>>3)&7)==(m&7)
                        and (p1&7) not in (4,5)): continue
            va=off2va(rp+i)
            if va: out.append(va)
    return sorted(out)

EXEC_BYTES = sum(rs for nm,va0,vs,rp,rs in EXEC)
print("COVERAGE rel32/shape = %d bytes over %d exec sections %s"
      % (EXEC_BYTES, len(EXEC), [(nm,"%08X"%va0,rs) for nm,va0,vs,rp,rs in EXEC]))
print("COVERAGE dword       = %d bytes (whole file, every alignment)" % len(data))

# ---- known-answer re-derivation ----
c,j,d = census(0x446F30)
print("KNOWN 0x446F30 E8=%d %s E9=%d ptr=%d" % (len(c), ["%08X"%x for x in c], len(j), len(d)))
assert len(c)==1 and c[0]==0x5E4085 and len(j)==0 and len(d)==0

# ---- census ----
for t in (0x467130,0x469800,0x469760,0x465450,0x5DF080,0x5DF850,0x5DF7C0,
          0x5DEFF0,0x5E0270,0x5DCB40,0x5E4060,0x4446F0):
    c,j,d = census(t)
    print("%08X E8=%-2d %-26s E9=%-2d ptr=%d %s"
          % (t,len(c),",".join("%08X"%x for x in c)[:26],len(j),len(d),
             ",".join(("%08X"%v if v else "off%08X"%o) for o,v in d)))
assert census(0x467130) == ([], [], [(0x00B0B528, 0x00F0D128)])

# ---- vtables ----
print("MovementAttr vt 0xF0D0F8:", {hex(o):"%08X"%dw(0xF0D0F8+o)
      for o in (0x10,0x24,0x28,0x2C,0x30,0x34,0x38)})
print("ActorAttr    vt 0xF0E7A0:", {hex(o):"%08X"%dw(0xF0E7A0+o)
      for o in (0x10,0x24,0x28,0x2C,0x30,0x34,0x38)})
print("actor-entry  vt 0xF2FE78:", {hex(o):"%08X"%dw(0xF2FE78+o)
      for o in (0x00,0x04,0x08,0x0C,0x10,0x14,0x18,0x1C)})
assert dw(0xF0D0F8+0x30) == 0x467130
assert dw(0xF0D0F8+0x38) == 0x469800
assert dw(0xF0D0F8+0x24) == 0x465450
assert dw(0xF2FE78+0x14) == 0x5DF850

# ---- dispatch shape census ----
for disp in (0x30, 0x14):
    print("[reg+0x%02X];call : loose=%d strict=%d"
          % (disp, len(vt_sites(disp,False)), len(vt_sites(disp,True))))
assert 0x5DF8BC in vt_sites(0x30, True)
assert 0x5E0359 in vt_sites(0x14, True)

# ---- ห่วงโซ่ call target ----
for va,exp in ((0x5E406E,0x5DCB40),(0x5E4085,0x446F30),(0x5DCBC1,0x5E0270),
               (0x5DCBA9,0x5DC980),(0x4446FE,0x5DF080),(0x465481,0x4676A0),
               (0x46714A,0x88F2B0),(0x46981A,0x88F2B0),(0x5DF896,0x5DEFF0)):
    got = calltgt(va)
    print("call @%08X -> %08X (expect %08X)" % (va, got, exp)); assert got == exp

# ---- ไบต์ที่เป็นหัวใจของข้อสรุป ----
# 0x46715D  mov cl,[esi+0x4C]  = อ่าน mask ของ THIS
assert data[va2off(0x46715D):va2off(0x46715D)+3] == bytes([0x8A,0x4E,0x4C])
# 0x467163  jne = "บิต SET -> ข้าม copy"
assert data[va2off(0x467163):va2off(0x467163)+2] == bytes([0x75,0x10])
# 0x467159  and eax,edi = source คือ arg
assert data[va2off(0x467159):va2off(0x467159)+2] == bytes([0x23,0xC7])
# 0x469835  mov edx,[edx+0x24] = thunk ไป slot +0x24 ไม่ใช่ +0x30
assert data[va2off(0x469835):va2off(0x469835)+3] == bytes([0x8B,0x52,0x24])
# 0x46982F  mov eax,[eax+0x244]
assert data[va2off(0x46982F):va2off(0x46982F)+6] == bytes([0x8B,0x80,0x44,0x02,0x00,0x00])
# 0x465450..0x4654BA : ไม่มี `F6 4x 4C` (test byte [reg+0x4C],imm) เลย -> commit ไม่ดู mask
blob = data[va2off(0x465450):va2off(0x4654BA)]
assert not any(blob[i]==0xF6 and (blob[i+1]&0xF8)==0x40 and blob[i+2]==0x4C
               for i in range(len(blob)-2))
# 0x5DC981  mov ecx,[ecx+0x1C] : stream ที่ merge คือ actor-entry collection
assert data[va2off(0x5DC981):va2off(0x5DC981)+3] == bytes([0x8B,0x49,0x1C])
# 0x5DCB97  cmp dword [esi],0 -> ถ้า cache NULL ข้าม merge
assert data[va2off(0x5DCB97):va2off(0x5DCB97)+3] == bytes([0x83,0x3E,0x00])
assert data[va2off(0x5DCB8E):va2off(0x5DCB8E)+6] == bytes([0x8D,0xB5,0x54,0x01,0x00,0x00])
assert data[va2off(0x5DCC00):va2off(0x5DCC00)+2] == bytes([0x89,0x0E])
# ctor 0x465400 : mask := 0xFF, ฟิลด์อื่นศูนย์
assert data[va2off(0x46542A):va2off(0x46542A)+4] == bytes([0xC6,0x46,0x4C,0xFF])
# singleton
assert struct.unpack_from("<I", data, va2off(0x4011C2))[0] == 0x01081A90
assert struct.unpack_from("<I", data, va2off(0x4011CB))[0] == 0x1A8

for lo,hi,nm in ((0x467130,0x4671BC,"merge 0x467130"),
                 (0x465450,0x4654C0,"commit 0x465450"),
                 (0x469800,0x469840,"thunk 0x469800"),
                 (0x469760,0x4697A0,"thunk 0x469760"),
                 (0x5DF850,0x5DF8D7,"merge loop 0x5DF850"),
                 (0x5DF080,0x5DF0D0,"bind loop 0x5DF080"),
                 (0x5E0270,0x5E038F,"entry merge 0x5E0270"),
                 (0x5DCB40,0x5DCC10,"cache stage 0x5DCB40"),
                 (0x5E4060,0x5E408A,"inbound 0x5E4060"),
                 (0xF0D0F8,0xF0D138,"vt MovementAttr"),
                 (0xF2FE78,0xF2FE98,"vt actor-entry")):
    print("%-24s %08X..%08X %s" % (nm, lo, hi, span_sha(lo,hi)))

for lo,hi,nm in ((0x467130,0x4671C0,"0x467130"),(0x465450,0x4654C0,"0x465450"),
                 (0x469800,0x469840,"0x469800"),(0x5DF850,0x5DF8D8,"0x5DF850"),
                 (0x465400,0x465450,"0x465400 ctor")):
    hexdump(lo,hi,nm)
print("ALL GUARDS OK")
```

ผลรันจริงของบล็อกนี้บนเครื่องที่ทำรอบนี้ (ย่อ):

```
BIN size=14759424 sha256=9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623
COVERAGE rel32/shape = 8622080 bytes over 2 exec sections [('.text','00401000',8621056), ('.code','00C3A000',1024)]
COVERAGE dword       = 14759424 bytes (whole file, every alignment)
KNOWN 0x446F30 E8=1 ['005E4085'] E9=0 ptr=0
00467130 E8=0                            E9=0  ptr=1 00F0D128
00469800 E8=0                            E9=0  ptr=1 00F0D130
00465450 E8=0                            E9=0  ptr=1 00F0D11C
005DF850 E8=0                            E9=0  ptr=1 00F2FE8C
005E0270 E8=1  005DCBC1                  E9=0  ptr=0
005DCB40 E8=1  005E406E                  E9=0  ptr=0
005E4060 E8=0                            E9=0  ptr=1 00F2FFDC
[reg+0x30];call : loose=141 strict=91
[reg+0x14];call : loose=292 strict=185
```

---

## 9. nonclaims

1. ไม่อ้างอะไรเกี่ยวกับ **เซิร์ฟเวอร์ต้นฉบับ** — ไม่มี capture ของ remote human player แม้แต่เฟรมเดียว
2. ไม่อ้างว่าอะไร **แสดงผลบนจอ** — static ตอบได้แค่ค่าที่ถูกเขียนลงโครงสร้าง ไม่ใช่การเรนเดอร์
3. ไม่อ้างว่า census ของ dispatch site เป็น census **ปิด** — resolve ได้จุดเดียวจาก 141 และ 292 (ดู §7 ข้อ 1)
4. เอกสารนี้ **ไม่แตะ** `Pirate Force ServerProject/` ทั้งก้อน (ไม่มี `src/`, `tests/`, `tools/`, `reports/`,
   `docs/`, `current/`, `state/`, git index), ไม่แตะ `pf_bridge/LOCK_*.txt`, `GAME_TEST_QUEUE.md`,
   `CHIEF_CONTINUATION.md` · ไม่เปิด ledger entry ไม่ flip matrix row ไม่ใช่การอนุมัติให้เริ่มเขียนโค้ด
5. ไบนารี `GameClient/GameClient.local.bin` ถูกเปิดอ่านอย่างเดียว ไม่ถูกแก้ ไม่ถูก copy เข้า repo
