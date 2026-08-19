# DAMAGE-MODEL — ปิดช่องที่ยังเดา ด้วย static RE (รอบ 90)

## 0. หัวไฟล์

**จุดประสงค์** — ตอบ 4 คำถามที่ค้างของ DAMAGE-MODEL / HYP-PF-024 ด้วยหลักฐานระดับไบต์จากไบนารีไคลเอนต์อย่างเดียว:

1. **Q1** vital "version byte" ของ `CHitResult` (`0x16F7`) คือเลขอะไร และไคลเอนต์ตรวจที่ VA ไหน
2. **Q2** ตัว dispatch ของ VitalData collection ใน `GSCN_RunTimeProtocolRes` สร้าง/รับ `0x16F7` ได้จริงหรือไม่
3. **Q3** หัวเฟรมฟิลด์ 2/3/4/5 (`+0x20` u16, `+0x22` u16, `+0x24` u32, `+0x28` u8) — "ปัก 0 ทั้งหมด" เฉื่อยจริงไหม
4. **Q4** handler `0x750770` bail-out ถ้าหา performer identity ไม่เจอหรือไม่

**ไบนารีอ้างอิง (อ่านอย่างเดียว)**
`GameClient/GameClient.local.bin`
SHA-256 = `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` — **ตรวจแล้วตรงกับที่คาดไว้**
ImageBase `0x400000` · `.text` VA `0x401000` size `0x838A2C` raw `0x400` · `.rdata` VA `0xC3B000` raw `0x839400`
วิธีแปลง VA→file offset: `off = raw_ptr + (VA − ImageBase − section_VA)` (ลอกจาก `tools/pf_damage_hit_result_static.py`)

**วันที่** — 2026-08-19

**NONCLAIM (สำคัญ)** — ทุกข้อในเอกสารนี้เป็น **ข้อเท็จจริงเกี่ยวกับไคลเอนต์ตัวนี้ตัวเดียว ที่ถูกตรึงด้วยแฮช** เท่านั้น
ไม่ใช่หลักฐานจากเซิร์ฟเวอร์ต้นฉบับ (เซิร์ฟเวอร์ต้นฉบับกู้ไม่ได้ ไม่มี publish และห้ามอ้างอิงว่า "เซิร์ฟเวอร์เดิมทำแบบนี้")
ไม่มี runtime observation ในเอกสารนี้ ไม่มีการเปิดเกม ไม่มีการบูตเซิร์ฟเวอร์
เครื่องมือที่ใช้: `objdump -d -M intel` (pei-i386) + PE plumbing แบบเดียวกับ `tools/pf_damage_hit_result_static.py` (ทำใน `/tmp/` ไม่ทิ้งไฟล์ในรีโป)

---

## 1. โครง wire ที่ re-derive ได้ครบ (ฐานของทุกคำตอบ)

ก่อนตอบ Q1–Q4 ต้องปักโครงให้ตรงก่อน เพราะรอบก่อนหน้ามีการปนกันระหว่าง **"actor-entry collection"** กับ **"VitalData collection"** ซึ่งเป็นคนละ collection

`GSCN_RunTimeProtocolRes` id `0x6E9D` · name literal `0xF2FFF8` · vtable `0xF2FFC0` · sizeof `0x28`
serializer (vtable+0x18) `0x5E3EE0` · inbound handler (vtable+0x1C) `0x5E4060`

`0x5E3EE0` **เรียก base serializer `0x5F4070` ก่อนเป็นอันดับแรก** (`0x5E3EEF` `E8 7C 01 01 00`) แล้วค่อยเขียน/อ่าน change mask ของตัวเอง
ดังนั้นลำดับไบต์บนสายจริงคือ:

```
[frame header: 12 <msgid u16> · 14 <errdata u32> · 08 <protocol version u8 = 4>]
0B <BASE change mask>          <- 0x5F4070 ; bit 0x02 => object ที่ this+0x18
   ถ้า bit 0x02 ติด:
   12 <u16 count>              <- 0x5F3E20 / 0x5F38F0   *** VitalData collection ***
   ต่อ element:
       12 <u16 wire id>
       0B <u8 VERSION>         *** นี่คือ version byte ที่ Q1 ถาม ***
       <payload ของคลาสนั้น ผ่าน vtable+0x18>
0B <DERIVED change mask>       <- 0x5E3EE0 ; bit 0x02 => actor-entry collection ที่ this+0x1C
                                             bit 0x04 => this+0x24 ; bit 0x08 => this+0x20
```

**ตรงกับ `current/pf_login_game_server_v141.py` `make_runtime_vitals()` ทุกไบต์** — `u8tag(0x0B, 2)` คือ **BASE** mask, `u16tag(0x12, len)` คือ count ของ VitalData collection, `u16tag(0x12,msg_id)+u8tag(0x0B,vital_version)` คือ header ต่อ element และ `u8tag(0x0B, 0)` ท้ายสุดคือ **DERIVED** mask = 0 (คอมเมนต์ใน v141 เรียกว่า "second (derived-class) change mask" — ถูกต้อง)

หมายเหตุแก้ความเข้าใจผิด: `tools/pf_runtimeres_actor_entry_static.py` พูดถึง "bit 0x02 -> object +0x1C = THE ACTOR-ENTRY COLLECTION" — นั่นคือ **derived mask** ของ `0x5E3EE0` (element reader `0x5E21D0`, รูปร่าง `0B actorType · 32 id64 · 0B attrCount · [12 attrId + attr payload]*`) ซึ่ง **คนละอันกับ** VitalData collection ที่ CHitResult วิ่งผ่าน ทั้งสองข้อความถูกทั้งคู่ แต่คนละ mask คนละ byte

หลักฐานไบต์:

| VA | file offset | bytes | ความหมาย |
|---|---|---|---|
| `0x5E3EEF` | `0x1E32EF` | `E8 7C 01 01 00` | `call 0x5F4070` — base serializer ถูกเรียกก่อน |
| `0x5F4080` | `0x1F3480` | `83 7F 18 00` | `cmp dword [edi+0x18],0` — base mask bit 0x02 ผูกกับ `this+0x18` |
| `0x5F4086` | `0x1F3486` | `C6 44 24 10 02` | `mov byte [esp+0x10],2` |
| `0x5F4096` | `0x1F3496` | `6A 0B` | tag `0x0B` ของ base mask |
| `0x5F40C9` | `0x1F34C9` | `F6 44 24 14 02` | read path: `test byte [esp+0x14],2` |
| `0x5F4105` | `0x1F3505` | `E8 16 FD FF FF` | `call 0x5F3E20` — VitalData collection READER |
| `0x5F40AA` | `0x1F34AA` | `E8 41 F8 FF FF` | `call 0x5F38F0` — VitalData collection WRITER |
| `0x5E3F78` | `0x1E3378` | `6A 0B` | derived mask tag `0x0B` (อ่านหลัง base) |

---

## 2. Q1 — vital version byte ของ `0x16F7`

### คำตอบ

> **version byte ของ `CHitResult` (`0x16F7`) = `0x00` (ศูนย์)**
> ไคลเอนต์ตรวจที่ **VA `0x5F3EFC`** ด้วยคำสั่ง `cmp cl, byte ptr [esi+0x10]` (`3A 4E 10`)
> โดย `cl` = ไบต์ที่อ่านจากสายด้วย tag `0x0B` และ `[esi+0x10]` = ฟิลด์ version ของอ็อบเจ็กต์ที่ ctor ตั้งไว้

### ระดับความมั่นใจ: **PROVEN**

### หลักฐานระดับไบต์

**(ก) ตัว reader ตรวจ version ที่ไหน — `0x5F3E20`** (VitalData collection READ)

| VA | file offset | bytes | disasm / ความหมาย |
|---|---|---|---|
| `0x5F3EE9` | `0x1F32E9` | `6A 0B` | `push 0x0B` — tag ของ version |
| `0x5F3EF0` | `0x1F32F0` | `C6 45 CF 00` | `mov byte [ebp-0x31],0` — เคลียร์ปลายทางก่อนอ่าน |
| `0x5F3EF4` | `0x1F32F4` | `E8 47 67 2A 00` | `call 0x89A640` = `CStream::ReadField(tag=0x0B, &v, 1)` |
| `0x5F3EF9` | `0x1F32F9` | `8A 4D CF` | `mov cl, [ebp-0x31]` — version ที่มาจากสาย |
| **`0x5F3EFC`** | **`0x1F32FC`** | **`3A 4E 10`** | **`cmp cl, byte ptr [esi+0x10]`** ← จุดตรวจ |
| `0x5F3F01` | `0x1F3301` | `74 36` | `je 0x5F3F39` — ตรงกัน ไปต่อ |
| `0x5F3F03` | `0x1F3303` | `8B 16` | ไม่ตรง: `mov edx,[esi]` → เรียก `[vtable+0x10]` เอา id มาใส่ข้อความ error |
| `0x5F3F18` | `0x1F3318` | `68 31 00 00 E0` | `push 0xE0000031` — โยน exception (mismatch = ตายทันที) |
| `0x5F3F39` | `0x1F3339` | `8B 06 8B 50 18` | `mov eax,[esi]` / `mov edx,[eax+0x18]` — เรียก Serializer ของคลาสจริง |

**(ข) ฝั่ง write ยืนยันว่าไบต์นี้คือ `obj+0x10` — `0x5F38F0`**

| VA | file offset | bytes | disasm |
|---|---|---|---|
| `0x5F398B` | `0x1F2D8B` | `8D 46 10` | `lea eax,[esi+0x10]` |
| `0x5F398F` | `0x1F2D8F` | `6A 0B` | `push 0x0B` |
| `0x5F3993` | `0x1F2D93` | `E8 68 6C 2A 00` | `call 0x89A600` = `WriteField(0x0B, &obj[0x10], 1)` |
| `0x5F399A` | `0x1F2D9A` | `8B 42 18` | `mov eax,[edx+0x18]` — แล้วค่อย Serialize |

⇒ **สล็อตของ vtable ไม่ใช่ที่เก็บ version** vtable ของคลาส wire ทุกตัวมี **9 สล็อตพอดี (`+0x00..+0x20`, ยาว `0x24` ไบต์)** และ `.rdata` วาง vtable ติดกันเป็นพรืด (นี่คือเหตุที่ `0xF48AA0 + 0x24 = 0xF48AC4` = vtable ของ `CMissileHitResult` พอดี ไม่ใช่ base ที่สองของคลาสเดียวกัน) แผนที่สล็อต:

| slot | ความหมาย | ค่าใน `CHitResult` (`0xF48AA0`) |
|---|---|---|
| `+0x00` | คืน pointer ของ class descriptor | `0x74F9D0` = `B8 98A20801 C3` |
| `+0x04` | destructor/cleanup | `0x74FD80` |
| `+0x08` | `xor al,al; ret` (คงที่ false) | `0x401B20` |
| `+0x0C` | **sizeof** | `0x5E6230` = `B8 48000000 C3` → `0x48` ✓ |
| `+0x10` | **get wire id** | `0x74F9C0` = `66 A1 E4A20801 C3` → `[0x108A2E4]` ✓ |
| `+0x14` | factory (สร้าง instance ใหม่) | `0x74FF20` |
| `+0x18` | **serializer (bidirectional)** | `0x750040` ✓ |
| `+0x1C` | **inbound handler** | `0x750770` ✓ |
| `+0x20` | **precondition ก่อน handler** | `0x710440` = `B0 01 C2 04 00` → **คืน true เสมอ** |

ไม่มีสล็อตไหนคืน "เลข version" — version เป็น **ฟิลด์ของ instance ที่ `obj+0x10`**

**(ค) `CHitResult` ตั้ง `+0x10` เป็นอะไร — ctor `0x74F940`**

| VA | file offset | bytes | disasm |
|---|---|---|---|
| `0x74F968` | `0x34ED68` | `33 C0` | `xor eax,eax` (al = 0) |
| `0x74F96A` | `0x34ED6A` | `88 46 04` | `mov [esi+0x04],al` |
| `0x74F96D` | `0x34ED6D` | `89 46 08` | `mov [esi+0x08],eax` |
| `0x74F970` | `0x34ED70` | `C7 06 6C6DF800` | `mov [esi],0xF86D6C` (vtable ชั่วคราวของ base) |
| `0x74F976` | `0x34ED76` | `89 46 0C` | `mov [esi+0x0C],eax` |
| **`0x74F979`** | **`0x34ED79`** | **`88 46 10`** | **`mov byte [esi+0x10], al`  → version = 0** |
| `0x74F97C` | `0x34ED7C` | `88 46 11` | `mov [esi+0x11],al` |
| `0x74F98E` | `0x34ED8E` | `C7 06 A08AF400` | `mov [esi],0xF48AA0` — ปัก vtable CHitResult |

ระหว่าง `0x74F968` (`xor eax,eax`) ถึง `0x74F979` **ไม่มีคำสั่งใดแตะ `eax`/`al`** (`88 46 04`, `89 46 08`, `C7 06 imm32`, `89 46 0C` ล้วนเป็น store) ⇒ `al = 0` แน่นอน

ฝาแฝด `CMissileHitResult` ctor `0x74F9E0`: `0x74FA08` `33 C0` → **`0x74FA19` `88 46 10`** ⇒ **version = 0** เช่นกัน (file offset `0x34EE19`)

### Cross-validation กับคลาสที่รู้ version อยู่แล้ว

สแกน ctor ของคลาส wire แล้วดึงคำสั่งที่เขียน `+0x10` เป็นไบต์ ได้ตารางนี้ (ทุกแถวคือไบต์จริงในอิมเมจ):

| คลาส | VA | file offset | bytes | version |
|---|---|---|---|---|
| **SelectActorVital** (`0x36EF`) | `0x5ED71E` | `0x1ECB1E` | `C6 46 10 0A` | **10** ← ตรงกับที่ v141 เรียก "SelectActorVital v10" |
| CreateActorVital (`0x36CF`) | `0x5E4C2A` | `0x1E402A` | `C6 46 10 08` | 8 |
| TeleportVital (`0x25A2`) | `0x5E5425` | `0x1E4825` | `C6 46 10 04` | 4 |
| QuestOperateVital (`0x3E34`) | `0x621844` | `0x220C44` | `C6 40 10 03` | 3 |
| TriggerVital (`0x1FB2`) | `0x600796` | `0x1FFB96` | `C6 40 10 01` | 1 |
| **UpdateNPCAppearVital** (`0x515F`) | `0x738987` → `0x7389A0` | `0x337D87` → `0x337DA0` | `33 C9` … `88 48 10` | **0** ← ตรงกับ v141 บรรทัด ~715 ที่บอก v0 |
| **CHitResult** (`0x16F7`) | `0x74F968` → `0x74F979` | `0x34ED68` → `0x34ED79` | `33 C0` … `88 46 10` | **0** |
| CMissileHitResult (`0x3EE5`) | `0x74FA08` → `0x74FA19` | `0x34EE08` → `0x34EE19` | `33 C0` … `88 46 10` | 0 |

SelectActorVital = 10 และ UpdateNPCAppearVital = 0 ตรงกับสองจุดที่โปรเจกต์เคยพิสูจน์มาก่อนโดยอิสระ ⇒ ยืนยันว่า `obj+0x10` คือ "vital version" จริง ไม่ใช่ฟิลด์อื่น

### สรุปที่ใช้เขียน encoder ได้ทันที

```
element ของ CHitResult บนสาย =  12 F7 16   0B 00   <payload จาก serializer 0x750040>
```

---

## 3. Q2 — VitalData collection สร้าง `0x16F7` ได้จริงไหม

### คำตอบ

> **ได้ — เป็น registry ทั่วไป (std::map คีย์ u16) ไม่ใช่ switch/allowlist**
> และ `CHitResult` **ถูกลงทะเบียนเข้า registry ตัวเดียวกันนั้นจริง** ที่ `0x755048`
> หลังสร้างแล้ว handler ที่ถูกเรียกคือ **vtable+0x1C = `0x750770`** ตามที่คาด
> guard เดียวก่อนถึง handler คือ **vtable+0x20** ซึ่งของ `CHitResult` คือ `0x710440` = `mov al,1; ret 4` (**true เสมอ ไม่กัน**)

### ระดับความมั่นใจ

* "registry ทั่วไป + `0x16F7` อยู่ใน registry + handler = `0x750770` + ไม่มี guard" → **PROVEN**
* "โค้ดลงทะเบียนถูกรันจริงตอน client boot" → **DERIVED** (เหตุผลอยู่ท้ายหัวข้อ)

### หลักฐานระดับไบต์ — เส้นทางอ่าน

`0x5F3E20` (VitalData collection READ):

| VA | file offset | bytes | disasm / ความหมาย |
|---|---|---|---|
| `0x5F3E5F` | `0x1F325F` | `6A 12` | tag `0x12` |
| `0x5F3E6C` | `0x1F326C` | `E8 CF 67 2A 00` | `ReadField(0x12, &count, 2)` — u16 count |
| `0x5F3E80` | `0x1F3280` | `66 8B 4D C4` | loop: index (u16) |
| `0x5F3E84` | `0x1F3284` | `66 3B 4D C0` | `cmp index,count` |
| `0x5F3E94` | `0x1F3294` | `6A 12` | tag `0x12` |
| `0x5F3E98` | `0x1F3298` | `E8 A3 67 2A 00` | `ReadField(0x12, &id, 2)` — u16 wire id |
| **`0x5F3EA1`** | **`0x1F32A1`** | **`E8 BA F3 FE FF`** | **`call 0x5E3260`** = ดึง registry singleton |
| **`0x5F3EA8`** | **`0x1F32A8`** | **`E8 53 EF FE FF`** | **`call 0x5E2E00`** = `CreateById(id)` |
| `0x5F3EAF` | `0x1F32AF` | `3B F3` | `cmp esi,ebx` (ebx = 0) |
| `0x5F3EB1` | `0x1F32B1` | `75 30` | `jne 0x5F3EE3` — เจอ → ไปต่อ |
| `0x5F3EC2` | `0x1F32C2` | `68 32 00 00 E0` | ไม่เจอ → `push 0xE0000032` แล้วโยน (ข้อความมี id, source line `0xDF` = 223) |

`0x5E2E00` = `CreateById`:

| VA | file offset | bytes | disasm |
|---|---|---|---|
| `0x5E2E15` | `0x1E2215` | `E8 66 E5 14 00` | `call 0x731380` — map lookup |
| `0x5E2E39` | `0x1E2239` | `74 25` | `je 0x5E2E60` → `xor eax,eax; ret 4` (คืน NULL เมื่อไม่มีคีย์) |
| `0x5E2E48` | `0x1E2248` | `8B 4E 10` | `mov ecx,[esi+0x10]` — prototype ของคลาสที่เจอ |
| `0x5E2E4B` | `0x1E224B` | `8B 11` | `mov edx,[ecx]` — vtable ของ prototype |
| `0x5E2E4D` | `0x1E224D` | `8B 42 14` | `mov eax,[edx+0x14]` — **factory slot** |
| `0x5E2E50` | `0x1E2250` | `FF D0` | `call eax` — สร้าง instance |

`0x731380` = std::map lower_bound บน **คีย์ u16**:

| VA | file offset | bytes | disasm |
|---|---|---|---|
| `0x7313A0` | `0x3307A0` | `66 39 48 0C` | `cmp word ptr [eax+0x0C], cx` — เทียบคีย์ 16-bit ในโหนด red-black tree |

⇒ **ไม่มี jump table, ไม่มี `cmp id,imm` ต่อเนื่อง, ไม่มี allowlist** เป็นการค้นต้นไม้ทั่วไป

### หลักฐานระดับไบต์ — `0x16F7` อยู่ใน registry

ฟังก์ชันลงทะเบียน `0x5F3DF0` = `RegisterVitalPrototype(VitalData* proto)`:

| VA | file offset | bytes | disasm |
|---|---|---|---|
| `0x5F3DFA` | `0x1F31FA` | `8B 50 10` | `mov edx,[eax+0x10]` — get-id ของ proto |
| `0x5F3DFE` | `0x1F31FE` | `FF D2` | `call edx` |
| `0x5F3E04` | `0x1F3204` | `E8 57 F4 FE FF` | `call 0x5E3260` — registry เดียวกับ reader |
| `0x5F3E0B` | `0x1F320B` | `E8 A0 FD FF FF` | `call 0x5F3BB0` — `map.insert(id, proto)` |

จุดลงทะเบียนของ `CHitResult` (อยู่ในฟังก์ชัน `0x754EB0`):

| VA | file offset | bytes | disasm |
|---|---|---|---|
| **`0x75501E`** | **`0x35441E`** | **`6A 48`** | `push 0x48` — sizeof CHitResult |
| `0x755020` | `0x354420` | `E8 FB 7F 13 00` | `call 0x88D020` — operator new |
| `0x755038` | `0x354438` | `8B C8` | `mov ecx,eax` |
| **`0x75503A`** | **`0x35443A`** | **`E8 01 A9 FF FF`** | **`call 0x74F940`** — **CHitResult ctor** |
| `0x755043` | `0x354443` | `50` | `push eax` |
| **`0x755048`** | **`0x354448`** | **`E8 A3 ED E9 FF`** | **`call 0x5F3DF0`** — **ลงทะเบียน CHitResult** |
| `0x75504D` | `0x35444D` | `6A 58` | `push 0x58` — sizeof CMissileHitResult (ตัวถัดไป) |
| `0x755069` | `0x354469` | `E8 72 A9 FF FF` | `call 0x74F9E0` — CMissileHitResult ctor |

### หลักฐานระดับไบต์ — handler และ guard

`0x5E4060` (inbound handler ของ `GSCN_RunTimeProtocolRes`) → `0x5E40DE` `E8 FD F8 00 00` = `call 0x5F39E0`
`0x5F39E0`: `8B 49 18` (`mov ecx,[ecx+0x18]` = base collection) · `85 C9` · `74 05` (NULL → `mov al,1; ret 4`) · `E9 54 FE FF FF` → `jmp 0x5F3840`

`0x5F3840` = ลูปยิง handler ต่อ vital:

| VA | file offset | bytes | disasm |
|---|---|---|---|
| `0x5F387F` | `0x1F2C7F` | `8B 4B 08` | `mov ecx,[ebx+0x08]` — vital object |
| `0x5F3882` | `0x1F2C82` | `8B 11` | `mov edx,[ecx]` — vtable |
| **`0x5F3888`** | **`0x1F2C88`** | **`8B 42 20`** | **`mov eax,[edx+0x20]` — precondition** |
| `0x5F388C` | `0x1F2C8C` | `FF D0` | `call eax` |
| `0x5F388E` | `0x1F2C8E` | `84 C0` | `test al,al` |
| `0x5F3890` | `0x1F2C90` | `74 49` | `je 0x5F38DB` → เลิกทั้งลูป คืน false |
| **`0x5F38AE`** | **`0x1F2CAE`** | **`8B 42 1C`** | **`mov eax,[edx+0x1C]` — handler** |
| `0x5F38B2` | `0x1F2CB2` | `FF D0` | `call eax` |

`CHitResult` vtable+0x20 = `0x710440` file offset `0x30F840` bytes `B0 01 C2 04 00` = `mov al,1; ret 4` ⇒ **precondition คืน true เสมอ ไม่มี guard กั้น**
`CHitResult` vtable+0x1C = `0x750770` ⇒ **handler ที่ถูกเรียกคือ `0x750770` ตรงตามคาด**

### ทำไม "โค้ดลงทะเบียนรันจริง" ถึงเป็น DERIVED ไม่ใช่ PROVEN

`0x754EB0` (ฟังก์ชันที่มี `0x755048` อยู่ข้างใน) ไม่มี direct call จาก `.text` เลย — ถูกอ้างเป็น **pointer เดียวใน `.rdata` ที่ `0xF48DB0`** ซึ่งคือ **vtable ของ `CSkillModule` (base `0xF48D88`) สล็อต `+0x28`**

เทียบกับ `UpdateNPCAppearVital` ที่โปรเจกต์พิสูจน์ runtime มาแล้วว่าไคลเอนต์รับ: ฟังก์ชันลงทะเบียนของมันคือ `0x738980` → ถูกอ้างผ่าน thunk `0x7383A0` → pointer เดียวใน `.rdata` ที่ `0xF472B8` = **vtable ของ `NPCAppearModule_Client` (base `0xF47290`) สล็อต `+0x28`** — **สล็อตเดียวกันเป๊ะ**

⇒ กลไกเดียวกัน สล็อตเดียวกัน แต่ static image พิสูจน์ไม่ได้ว่า module list ถูกเดินจริงตอนบูต จึงให้เป็น **DERIVED (มั่นใจสูง)** ไม่ใช่ PROVEN

---

## 4. Q3 — ปัก 0 ที่ฟิลด์ 2/3/4/5 "เฉื่อย" จริงไหม

โครง header ของ `CHitResult` (จาก serializer `0x750040`, ยืนยันซ้ำ):
`+0x18` qword tag `0x32` attacker id · `+0x20` u16 tag `0x12` · `+0x22` u16 tag `0x12` · `+0x24` u32 tag `0x14` · `+0x28` u8 tag `0x0B` · `+0x2C` array ของ hit entry (stride 32)

handler `0x750770` แบ่งเป็น **ลูปที่ 1 = reaction pass** (`0x750877`–`0x750C79`) และ **ลูปที่ 2 = number pass** (`0x750C82`–`0x750DC9`) แล้วตามด้วย **ท้ายฟังก์ชัน** (`0x750DE8`–`0x750E95`)

### สรุปคำตอบต่อฟิลด์

| ฟิลด์ | ปัก 0 แล้วเป็นอย่างไร | ผลต่อ "เลข damage โผล่บนจอ" | ระดับ |
|---|---|---|---|
| `+0x20` u16 (ฟิลด์ 2) | ผ่าน gate `0x5CAE00(0)` → **คืน false** เมื่อ singleton `[0x10339B0]` ไม่เป็น NULL ⇒ **ไม่บล็อก** | **ไม่กระทบ** (แต่มีเงื่อนไข ดูด้านล่าง) | PROVEN (ตัวโค้ด) / เงื่อนไข runtime = UNKNOWN |
| `+0x22` u16 (ฟิลด์ 3) | ≠ `0xEA7A` ⇒ ไปทางปกติ; ใช้เป็น key ค้นตาราง ได้ NULL แล้วแค่ข้ามสาขาเสริม | **ไม่กระทบ** | PROVEN |
| `+0x24` u32 (ฟิลด์ 4) | `test eax,eax; je` ⇒ **ข้าม** FX ตัวที่สอง (เฉพาะกรณีผู้ตี = ผู้เล่นเอง) แล้ว **ไหลต่อ ไม่ return** | ไม่กระทบเลขหลัก | PROVEN |
| `+0x28` u8 (ฟิลด์ 5) | ถูก **ส่งเป็นอาร์กิวเมนต์** เข้า `actor vtable+0x30` และ `0x48D870` ไม่มีสาขาไหนเทียบกับค่าคงที่ | **ไม่กระทบ** | PROVEN |
| `+0x20` **และ** `+0x22` เป็น 0 **พร้อมกัน** | ท้ายฟังก์ชัน **ข้าม** `call 0x5CE010` ทั้งก้อน | ไม่กระทบเลข (แต่ระบบเสริมถูกปิด) | PROVEN |

### ระดับความมั่นใจรวม: **PROVEN** ยกเว้นข้อควรระวังหนึ่งข้อ (ท้ายหัวข้อ)

### หลักฐานระดับไบต์

**ฟิลด์ 3 (`+0x22`) — สาขาพิเศษ `0xEA7A`**

| VA | file offset | bytes | disasm |
|---|---|---|---|
| `0x7507F2` | `0x34FBF2` | `0F B7 45 22` | `movzx eax, word [ebp+0x22]` |
| `0x7507F6` | `0x34FBF6` | `B9 7A EA 00 00` | `mov ecx,0xEA7A` |
| `0x7507FB` | `0x34FBFB` | `66 3B C1` | `cmp ax,cx` |
| `0x7507FE` | `0x34FBFE` | `75 1F` | `jne 0x75081F` — **0 ≠ 0xEA7A ⇒ ไปทางปกติ** |
| `0x750800` | `0x34FC00` | `85 FF` | (ในสาขา `0xEA7A`) `test edi,edi` |
| `0x750802` | `0x34FC02` | `0F 84 8D 06 00 00` | `je 0x750E95` — bail ถ้า performer NULL |
| `0x750808` | `0x34FC08` | `F6 47 10 40` | `test byte [edi+0x10],0x40` |
| `0x75080C` | `0x34FC0C` | `0F 84 83 06 00 00` | `je 0x750E95` — bail ถ้าธงไม่ติด |

⇒ สาขาที่ bail มีเฉพาะเมื่อ `+0x22 == 0xEA7A` เท่านั้น **ปัก 0 หลบสาขานี้ได้ทั้งหมด**

ทางปกติ: `0x750822` `52` (`push edx` = `+0x22`) · `0x750823` `E8 78 5A CC FF` (`call 0x4162A0` = ดึง singleton ตาราง) · `0x75082A` `E8 E1 21 FB FF` (`call 0x702A10` = ค้นตารางด้วยคีย์) · `0x750832` `89 44 24 18` (เก็บผลไว้)
ผลลัพธ์ NULL ถูกใช้แบบ "ข้าม" เท่านั้น:
`0x750A8A` `8B 44 24 18` / `0x750A8E` `85 C0` / `0x750A90` `74 1C` → ข้าม
`0x750AC4` `83 7C 24 18 00` / `0x750AC9` `0F 84 88 01 00 00` → ข้ามไปวนรอบถัดไป (`0x750C57`) **ไม่ return**

**ฟิลด์ 2 (`+0x20`) — gate ของ "เลขบนจอ"**

ในลูปที่ 2 (number pass) ต่อ hit-entry:

| VA | file offset | bytes | disasm |
|---|---|---|---|
| `0x750D1E` | `0x35011E` | `E8 4D 54 CF FF` | `call 0x446170` — หา actor เป้าหมายจาก entry+0x00 |
| `0x750D25` | `0x350125` | `85 FF` | `test edi,edi` |
| `0x750D27` | `0x350127` | `0F 84 82 00 00 00` | `je 0x750DAF` — **หาเป้าไม่เจอ ⇒ ข้าม entry นี้ ไม่มีเลข** |
| `0x750D2D` | `0x35012D` | `0F B7 45 20` | `movzx eax, word [ebp+0x20]` |
| `0x750D3E` | `0x35013E` | `E8 BD A0 E7 FF` | `call 0x5CAE00` |
| `0x750D43` | `0x350143` | `84 C0` | `test al,al` |
| `0x750D45` | `0x350145` | `75 68` | `jne 0x750DAF` — **ถ้า gate คืน true ⇒ ไม่โชว์เลข** |
| `0x750D90` | `0x350190` | `8B 4E 08` | `mov ecx,[esi+0x08]` — **ค่า damage** |
| `0x750DAA` | `0x3501AA` | `E8 31 F0 CE FF` | `call 0x43FDE0` — FX dispatcher (เลขบนจอ) |

`0x5CAE00` เต็มตัว (file offset `0x1CA200`):

| VA | bytes | disasm |
|---|---|---|
| `0x5CAE00` | `8B 0D B0 39 03 01` | `mov ecx,[0x10339B0]` |
| `0x5CAE06` | `85 C9` | `test ecx,ecx` |
| `0x5CAE08` | `75 05` | `jne 0x5CAE0F` |
| `0x5CAE0A` | `B0 01 C2 04 00` | **`mov al,1; ret 4`** ← singleton เป็น NULL ⇒ **คืน true** |
| `0x5CAE14` | `E8 F7 7B 13 00` | `call 0x702A10` — ค้นตารางด้วย id |
| `0x5CAE19` | `85 C0` | `test eax,eax` |
| `0x5CAE1B` | `74 09` | `je 0x5CAE26` — ไม่เจอ ⇒ ไป return false |
| `0x5CAE1D` | `F7 40 24 00 00 00 20` | `test dword [eax+0x24],0x20000000` |
| `0x5CAE26` | `32 C0 C2 04 00` | **`xor al,al; ret 4`** ← คืน false |

`0x702A10` (file offset `0x301E10`):

| VA | bytes | disasm |
|---|---|---|
| `0x702A13` | `83 7C 24 0C 00` | `cmp dword [esp+0x0C],0` — อาร์กิวเมนต์ id |
| `0x702A18` | `75 08` | `jne 0x702A22` |
| `0x702A1A` | `33 C0` | **`xor eax,eax`** ⇒ **id == 0 คืน NULL ทันที** |

⇒ **`+0x20 = 0` ⇒ `0x702A10(0)` = NULL ⇒ `0x5CAE00` คืน false ⇒ ไม่บล็อกเลข damage**

**ข้อควรระวังเดียวที่ static พิสูจน์ไม่ได้** — ถ้า singleton `[0x10339B0]` **เป็น NULL** ตอนที่เฟรมมาถึง `0x5CAE00` จะคืน **true** และ **เลข damage จะไม่โชว์เลย** ทุก entry
`[0x10339B0]` เป็น singleton แบบ set-in-ctor / clear-in-dtor:
`0x491D0C` `89 35 B0 39 03 01` = `mov [0x10339B0], esi` (ctor, vtable `0xF140E8`)
`0x491C5D` `39 35 B0 39 03 01` + `0x491C65` `A3 B0 39 03 01` = เคลียร์ใน dtor
สถานะจริงตอน in-game **อ่านจาก static image ไม่ได้** — จัดเป็น **UNKNOWN** และต้องพิสูจน์ตอนรันจริง

**ฟิลด์ 4 (`+0x24`)**

| VA | file offset | bytes | disasm |
|---|---|---|---|
| `0x750DE8` | `0x3501E8` | `A1 C4 2E 03 01` | `mov eax,[0x1032EC4]` — local player |
| `0x750DED` | `0x3501ED` | `85 C0` | `test eax,eax` |
| `0x750DEF` | `0x3501EF` | `74 57` | `je 0x750E48` |
| `0x750DF4` / `0x750DFE` | | | เทียบ identity ของ local player (`+0x78`/`+0x7C`) กับ attacker (`+0x18`/`+0x1C`) |
| `0x750E05` | `0x350205` | `8B 45 24` | `mov eax,[ebp+0x24]` |
| `0x750E08` | `0x350208` | `85 C0` | `test eax,eax` |
| `0x750E0A` | `0x35020A` | `74 3C` | **`je 0x750E48` — 0 ⇒ ข้าม FX ตัวที่สอง แล้วไหลต่อ (ไม่ return)** |
| `0x750E43` | `0x350243` | `E8 98 EF CE FF` | `call 0x43FDE0` — FX ตัวที่สอง type `0x20` (ทำงานเมื่อ `+0x24 != 0`) |

**ฟิลด์ 5 (`+0x28`)** — ถูกอ่านสามที่ และทุกที่คือ "ส่งเป็นพารามิเตอร์" ไม่มีการเทียบค่า:
`0x7508E3` `0F B6 45 28` → `actor vtable+0x30(0, +0x22, +0x28, performer)`
`0x750903` `0F B6 4D 28` → เส้นทางเดียวกัน (สาขาธง `0x60`)
`0x750A3E` `0F B6 45 28` → เข้า `0x48D870` (knockdown/fall spawner) พร้อม `fld dword [ebx+0x18]` ที่ `0x750A42` (`D9 43 18`)

**ท้ายฟังก์ชัน — `+0x20` และ `+0x22` เป็น 0 พร้อมกัน**

| VA | file offset | bytes | disasm |
|---|---|---|---|
| `0x750E48` | `0x350248` | `0F B7 45 20` | `movzx eax, word [ebp+0x20]` |
| `0x750E59` | `0x350259` | `E8 A2 9F E7 FF` | `call 0x5CAE00` |
| `0x750E5E` | `0x35025E` | `84 C0` | `test al,al` |
| `0x750E60` | `0x350260` | `75 33` | `jne 0x750E95` — จบ |
| `0x750E62` | `0x350262` | `0F B7 45 20` | `movzx eax, word [ebp+0x20]` |
| `0x750E66` | `0x350266` | `66 85 C0` | `test ax,ax` |
| `0x750E69` | `0x350269` | `75 09` | `jne 0x750E74` |
| `0x750E6B` | `0x35026B` | `0F B7 45 22` | `movzx eax, word [ebp+0x22]` |
| `0x750E6F` | `0x35026F` | `66 85 C0` | `test ax,ax` |
| **`0x750E72`** | **`0x350272`** | **`74 21`** | **`je 0x750E95` — ทั้งคู่เป็น 0 ⇒ ข้าม `0x5CE010`** |
| `0x750E90` | `0x350290` | `E8 7B D1 E7 FF` | `call 0x5CE010(attackerLo, attackerHi, id, &hitArray)` |
| `0x750E95` | `0x350295` | `B0 01` | `mov al,1` — คืน true |

`0x5CE010` เป็นระบบเสริมบนโมดูลเดียวกัน (`[0x1093198]+0x728`) และ **อยู่หลัง** number pass ทั้งหมด ⇒ การข้ามมันไม่กระทบเลข damage แต่ **ควรรู้ว่าถูกปิดไปด้วยเมื่อปัก 0 ทั้งคู่**

### ข้อค้นพบเพิ่มเติมที่สำคัญกว่าเรื่องฟิลด์ 0 — flag ที่ hit-entry `+0x1C`

ลูปที่ 1 (reaction pass) มี guard แข็งกว่าฟิลด์หัวเฟรมเสียอีก:

| VA | file offset | bytes | disasm |
|---|---|---|---|
| `0x7508D7` | `0x34FCD7` | `0F B7 43 1C` | `movzx eax, word [ebx+0x1C]` — flag ของ entry |
| `0x7508DB` | `0x34FCDB` | `A8 01` | `test al,1` |
| `0x7508DD` | `0x34FCDD` | `74 20` | `je 0x7508FF` |
| `0x7509D6` | `0x34FDD6` | `F6 43 1C 01` | `test byte [ebx+0x1C],1` |
| `0x7509DA` | `0x34FDDA` | `0F 84 77 02 00 00` | **`je 0x750C57` — bit0 ไม่ติด ⇒ ข้าม reaction block ทั้งก้อน** |

⇒ ลูปที่ 2 (เลขบนจอ) **ไม่ขึ้นกับ bit นี้** แต่ effect/animation ขึ้น — ตอนเขียน encoder ควรตั้งใจเลือกค่า `entry+0x1C` ไม่ใช่ปล่อย 0

---

## 5. Q4 — handler หา performer identity ไม่เจอแล้ว bail-out ไหม

### คำตอบ

> **ไม่ bail-out** (ยกเว้นสาขา `+0x22 == 0xEA7A` ซึ่งแผนของเราไม่แตะ)
> เมื่อหา performer ไม่เจอ ไคลเอนต์แค่ตั้งตัวแปรภายในเป็น 0 แล้ว **ไหลต่อ**
> แต่ **ตัวที่ bail จริงคือ "หา TARGET ไม่เจอ"** ซึ่งข้าม hit-entry นั้นทิ้งทั้งอัน (ไม่มีทั้ง reaction และเลข)

### ระดับความมั่นใจ: **PROVEN**

### หลักฐานระดับไบต์

| VA | file offset | bytes | disasm |
|---|---|---|---|
| `0x7507A7` | `0x34FBA7` | `8B 45 1C` | `mov eax,[ebp+0x1C]` — attacker id (hi) |
| `0x7507AA` | `0x34FBAA` | `8B 4D 18` | `mov ecx,[ebp+0x18]` — attacker id (lo) |
| `0x7507AF` | `0x34FBAF` | `E8 6C 22 CB FF` | `call 0x402A20` — ประกอบ identity key |
| **`0x7507B6`** | **`0x34FBB6`** | **`E8 B5 59 CF FF`** | **`call 0x446170` — ค้น actor จาก identity** |
| `0x7507BB` | `0x34FBBB` | `8B F8` | `mov edi,eax` — performer (อาจ NULL) |
| `0x7507C1` | `0x34FBC1` | `85 FF` | `test edi,edi` |
| **`0x7507C3`** | **`0x34FBC3`** | **`74 25`** | **`je 0x7507EA` — ไม่เจอ ⇒ กระโดดไปตั้ง 0 ไม่ใช่ return** |
| `0x7507EA` | `0x34FBEA` | `C7 44 24 1C 00 00 00 00` | `mov dword [esp+0x1C],0` |
| `0x7507F2` | `0x34FBF2` | `0F B7 45 22` | ไหลต่อเข้าตัวหลักทันที |

จุดที่ **bail จริง** (คนละอย่าง — เป็นเรื่องเป้าหมาย ไม่ใช่ผู้ตี):

| VA | file offset | bytes | ผล |
|---|---|---|---|
| `0x7508A4` | `0x34FCA4` | `E8 C7 58 CF FF` | `call 0x446170` (target ของ entry) — reaction pass |
| `0x7508AB` | `0x34FCAB` | `85 F6` | |
| `0x7508AD` | `0x34FCAD` | `0F 84 A4 03 00 00` | `je 0x750C57` — ข้าม entry นี้ |
| `0x750D1E` | `0x35011E` | `E8 4D 54 CF FF` | `call 0x446170` (target ของ entry) — number pass |
| `0x750D27` | `0x350127` | `0F 84 82 00 00 00` | `je 0x750DAF` — ข้าม entry นี้ (ไม่มีเลข) |

**สำหรับ phase 1 ที่จะใช้ identity ของผู้เล่นเองเป็นทั้งผู้ตีและเป้าหมาย** — ทั้งสองด้านจะ resolve ได้ ทำให้ผ่าน guard ทั้งหมด
แต่ต้องรู้ว่ามี **guard "ผู้ตี/เป้าหมายเป็นผู้เล่นเอง" ในเส้นทาง reaction** (ไม่ใช่เส้นทางเลข):

| VA | file offset | bytes | disasm |
|---|---|---|---|
| `0x750919` | `0x34FD19` | `83 7B 08 00` | `cmp dword [ebx+0x08],0` (damage แบบ signed) |
| `0x75091D` | `0x34FD1D` | `0F 8D B3 00 00 00` | `jge 0x7509D6` — ไม่ติดลบ ⇒ ข้าม impact reaction |
| `0x750923` | `0x34FD23` | `A1 C4 2E 03 01` | `mov eax,[0x1032EC4]` — local player |
| `0x750928` | `0x34FD28` | `3B F8` | `cmp edi,eax` (performer == local player?) |
| `0x75092A` | `0x34FD2A` | `74 6E` | `je 0x75099A` — ข้ามชุด filter ไปสาขาอื่น |
| `0x75092C` | `0x34FD2C` | `3B F0` | `cmp esi,eax` (target == local player?) |
| `0x75092E` | `0x34FD2E` | `74 6A` | `je 0x75099A` |

⇒ ถ้าผู้ตี **หรือ** เป้าหมายเป็นผู้เล่นเอง เส้นทาง `0x750930`–`0x750998` (ชุด filter 4 ชั้น) ถูกข้าม แล้วไปที่ `0x75099A` แทน — ยัง **ไม่ใช่ bail-out** ของฟังก์ชัน และ **ไม่กระทบ number pass** เลย

---

## 6. ตาราง "ไบต์ที่ควรปักเป็น guard" (พร้อมให้ verifier รอบถัดไปใช้ได้ทันที)

ทุกช่วงเป็น half-open `[lo, hi)` · sha256 คือแฮชของไบต์ในช่วงนั้นตรง ๆ จากไฟล์เดิม

| ช่วง VA | ช่วง file offset | sha256 ของช่วง | สิ่งที่กันไม่ให้เปลี่ยน |
|---|---|---|---|
| `0x5F3E20..0x5F4070` | `0x1F3220..0x1F3470` | `FD8CE6B0298E3A46C3AE1760CA71C6D1F60E45BC02CC60D2C2046A03EBA1C3CA` | VitalData collection READER + **จุดตรวจ version `0x5F3EFC`** + registry lookup |
| `0x5F38F0..0x5F39F0` | `0x1F2CF0..0x1F2DF0` | `1AB157252E6D08ACD4F9BFF399C43636E48E35D6CF0281F97AD7AA81A47F36A1` | VitalData collection WRITER (version = `obj+0x10`, tag `0x0B`) |
| `0x5F3840..0x5F38F0` | `0x1F2C40..0x1F2CF0` | `AE0195A6790A0788463351378C1A68677FA3099D46F761DA344FC17AB9BE3F5E` | ลูป dispatch: gate `vtable+0x20`, handler `vtable+0x1C` |
| `0x5F3DF0..0x5F3E11` | `0x1F31F0..0x1F3211` | `7B932CD7C54512C0359344D998E7C7ADFDBF6CB790E6B1FC4CD57C8080D35772` | `RegisterVitalPrototype` |
| `0x5E3260..0x5E3312` | `0x1E2660..0x1E2712` | `2BAAA07EC0DCDBCB52BBAE9AF46A75F070A6136F879726CAE303E880CBCB0DD3` | registry singleton accessor (`[0x1081C44]`) |
| `0x5E2E00..0x5E2E70` | `0x1E2200..0x1E2270` | `8C781596A55336DDFEDAB010CD067D3A547E0AC9B9C12E6FC9E62508D3FFCD78` | `CreateById` (ผ่าน prototype `vtable+0x14`) |
| `0x731380..0x731400` | `0x330780..0x330800` | `1C65776A35BEA6BE5F5F61B036D8446004C59BBEC971FD65CB5F32536A3A2F6A` | map lookup บนคีย์ u16 (พิสูจน์ว่าไม่ใช่ allowlist) |
| `0x74F940..0x74F9C0` | `0x34ED40..0x34EDC0` | `6A9DFA1B75E5DDA568C1EBABCE86007DA4F76228241099CAC27DB74EDB9F16ED` | **CHitResult ctor — จุดที่ตั้ง version = 0** |
| `0x74F9E0..0x74FA60` | `0x34EDE0..0x34EE60` | `22A6C7D6D37C96110C928F0E68536A4CCC5E084520B1468E8119EC174ABF23A2` | CMissileHitResult ctor (version = 0) |
| `0x755014..0x755060` | `0x354414..0x354460` | `30DF114FCDCEB5CCB82FECD3E721C87B812EFA85B4E75F2C81B59854B8FFD8FE` | **จุดลงทะเบียน prototype ของ CHitResult/CMissileHitResult** |
| `0x750770..0x750EC0` | `0x34FB70..0x3502C0` | `151E5425155D5A5DF6F1944F88FA2C041C6EA74DC8A69C8F907A54A807B5AF70` | inbound handler ทั้งตัว (Q3 + Q4) |
| `0x5CAE00..0x5CAE2B` | `0x1CA200..0x1CA22B` | `63C9A17B0EE0BD042C238323D8239E59AF58CFAE691D968427B3F9A2DA8675BC` | gate ของฟิลด์ 2 |
| `0x702A10..0x702A22` | `0x301E10..0x301E22` | `626C50DF2FA55EFB2D78702188DDA3AF40127092D27F0BD6141EBB46B897CA36` | `id == 0 ⇒ NULL` (หัวใจของ "0 เฉื่อย") |
| `0xF48AA0..0xF48AC4` | `0xB46EA0..0xB46EC4` | `5C02749311D280D7D6EA541EED91968C7C37E1EC6A07429D893A31BAB03D0546` | vtable CHitResult ครบ 9 สล็อต |
| `0xF48AC4..0xF48AE8` | `0xB46EC4..0xB46EE8` | `99D4FECE1CD34F3C1E32405CB2FD01F381049004FBEBC6217F30A5E9D0C51B2B` | vtable CMissileHitResult ครบ 9 สล็อต |
| `0x710440..0x710445` | `0x30F840..0x30F845` | `F4C6D7AE520F88AECB3EA65952E885437FA4A6CE4B5C3439A161D1C5D8E42863` | stub `mov al,1; ret 4` (precondition true เสมอ) |

### guard แบบ point-byte ที่ควรใส่คู่กัน (สั้น อ่านง่าย พังทันทีถ้าไบนารีเปลี่ยน)

| VA | file offset | bytes ที่ต้องเจอ | ยืนยันข้อไหน |
|---|---|---|---|
| `0x5F3EE9` | `0x1F32E9` | `6A 0B` | tag ของ version |
| `0x5F3EFC` | `0x1F32FC` | `3A 4E 10` | จุดตรวจ version |
| `0x5F3F01` | `0x1F3301` | `74 36` | สาขา "ตรงกัน" |
| `0x74F979` | `0x34ED79` | `88 46 10` | CHitResult version = al = 0 |
| `0x74F968` | `0x34ED68` | `33 C0` | al = 0 |
| `0x5ED71E` | `0x1ECB1E` | `C6 46 10 0A` | ตัวเทียบ SelectActorVital = 10 |
| `0x7389A0` | `0x337DA0` | `88 48 10` | ตัวเทียบ UpdateNPCAppearVital = 0 |
| `0x5F3EA1` | `0x1F32A1` | `E8 BA F3 FE FF` | เข้า registry |
| `0x5F3EA8` | `0x1F32A8` | `E8 53 EF FE FF` | สร้างจาก id |
| `0x755048` | `0x354448` | `E8 A3 ED E9 FF` | CHitResult ถูกลงทะเบียน |
| `0x75501E` | `0x35441E` | `6A 48` | sizeof `0x48` ของ prototype ที่ลงทะเบียน |
| `0x5F3888` | `0x1F2C88` | `8B 42 20` | gate slot |
| `0x5F38AE` | `0x1F2CAE` | `8B 42 1C` | handler slot |
| `0x710440` | `0x30F840` | `B0 01 C2 04 00` | gate = true เสมอ |
| `0x7507C3` | `0x34FBC3` | `74 25` | performer NULL **ไม่** return |
| `0x7507FE` | `0x34FBFE` | `75 1F` | `+0x22 != 0xEA7A` ⇒ ทางปกติ |
| `0x750D45` | `0x350145` | `75 68` | gate ของเลข damage |
| `0x702A1A` | `0x301E1A` | `33 C0` | id 0 ⇒ NULL |
| `0x750E0A` | `0x35020A` | `74 3C` | `+0x24 == 0` ⇒ ข้าม ไม่ return |
| `0x750E72` | `0x350272` | `74 21` | `+0x20 == 0 && +0x22 == 0` ⇒ ข้าม `0x5CE010` |
| `0x7509DA` | `0x34FDDA` | `0F 84 77 02 00 00` | flag entry+0x1C bit0 gate reaction |

---

## 7. สิ่งที่ยังตอบไม่ได้ (ตรงไปตรงมา)

1. **`[0x10339B0]` เป็น NULL หรือไม่ตอน in-game** — ถ้าเป็น NULL `0x5CAE00` คืน true และ **เลข damage จะไม่โผล่เลย** ไม่ว่าจะปัก `+0x20` เป็นอะไร
   static image บอกได้แค่ว่ามันเป็น singleton ที่ตั้งใน ctor `0x491D0C` และเคลียร์ใน dtor `0x491C65` — **สถานะจริงต้องพิสูจน์ตอนรัน** (UNKNOWN)
2. **ความหมายของแต่ละบิตใน `entry+0x1C`** — พิสูจน์ได้แค่ว่า bit0 เปิด/ปิด reaction block, bit3/bit4 เลือกสาขาข้อความ `_F_KNOCKED_002`, bit7 เปิดสาขาที่ใช้ตารางจาก `+0x22`
   **ยังไม่รู้ว่า bit ไหน = hit / miss / block / critical** และเอกสารนี้ไม่เดา
3. **ค่าที่ "ถูกต้อง" ของ `+0x20` / `+0x22` สำหรับ melee ธรรมดา** — รู้แค่ว่าเป็นคีย์เข้าตารางเดียวกัน (`0x4162A0` → `0x702A10`) และ 0 = ไม่มี row ยังไม่ได้ map ว่าตารางนี้คือ skill/action table แถวไหนใช้กับอะไร
4. **โค้ดลงทะเบียน `0x754EB0` ถูกรันจริงตอน boot หรือไม่** — เป็น DERIVED ไม่ใช่ PROVEN (เหตุผลอยู่หัวข้อ Q2) ต้องยืนยันด้วยการรันจริง
5. **`0x5CE010` ทำอะไร** — ยังไม่ได้ไล่เข้าไปข้างใน รู้แค่ว่ามันถูกข้ามเมื่อ `+0x20` และ `+0x22` เป็น 0 ทั้งคู่ และไม่ได้อยู่บนเส้นทางเลข damage
6. **สิ่งที่เกิดขึ้นเมื่อ `entry+0x08` (damage) ≥ 0** — `0x750919` `83 7B 08 00` + `0x75091D` `jge` พิสูจน์ว่ามีสาขาแยก แต่ **ไม่มีค่าคงที่ในอิมเมจที่บอกว่าแปลว่า heal / absorb / no-op** และเอกสารนี้ไม่ตั้งชื่อให้
7. **ทุกข้อในเอกสารนี้เป็นเรื่องของไคลเอนต์** — ไม่มีข้อไหนเป็นหลักฐานว่าเซิร์ฟเวอร์ต้นฉบับส่งอะไร
