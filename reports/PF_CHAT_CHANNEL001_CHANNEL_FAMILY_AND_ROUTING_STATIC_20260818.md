# PF_CHAT_CHANNEL001 — ตระกูล `Channel_*Vital` ทั้ง 17 ช่องของ client: channel identifier (id = แฮชของชื่อคลาส) · wire schema รายช่อง · recipient resolution ของ Whisper · ลำดับชั้น routing · Join/Leave membership lifecycle — byte-exact static + cross-check server

2026-08-18 · chief assistant (scope งานเดียว) · report-only additive · milestone `chat / chat_channels_and_routing` (`not_started`) · binary `GameClient/GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` · capstone 5.0.7 (CS_MODE_32, ImageBase 0x400000, PE section table parsed เอง) · reproduce: `py -3 tools/pf_chat_channel_family_static.py` (69 guards, exit 0) + `py -3 -m pytest tests/test_chat_channel_family_static.py -q` (15 passed)

เป้า: ปลดครึ่งหนึ่งของ coverage note เดิม — **"Routing needs at least two concurrent sessions, which no runtime pass has ever established. Channel identifiers and recipient resolution are uncaptured."** — เฉพาะท่อน **"Channel identifiers … are uncaptured"** และท่อน **"recipient resolution"** ด้วยหลักฐาน static byte-exact ล้วน โดย **ไม่แตะ v141 (immutable), ไม่แตะ canonical DB, ไม่เปิด GameClient, ไม่ต่อ network** และ **ไม่ claim พฤติกรรม routing ของ original server** (ยังไม่เคยมี 2 client พร้อมกันจริง — ท่อนแรกของ note ยังยืนอยู่)

> **ผลสรุปล่วงหน้า:**
> - **Channel identifier ไม่ uncaptured อีกต่อไป** — ตระกูลนี้ลงทะเบียนจาก **บล็อกเดียวติดกัน 18 รายการ `0xBF72B0..0xBF74F0` (stride 0x20 = 17 `Channel_*` + `CBoardcastVital`)** ที่มีรูป PF-NAMEID-HASH-001 เป๊ะ (`push <name literal>; call 0x89C080; mov ecx,eax; call 0x89BD00; mov word[id-slot],ax; ret`) → เอาอัลกอริทึมแฮชของ NAMEID-HASH-001 (client `0x89B220`, `u16 id = Σᵢ (int16)((signed char)name[i]·(i+1)) mod 2¹⁶`) มาใช้ซ้ำกับ literal ในอิมเมจ **ได้ id ครบทั้ง 17 ช่อง**
> - **⭐ ANCHOR ตรงเป๊ะ:** `name_id("Channel_LocalTalkMessageVital") = 0xAC52` = id ที่ GT-006 จับได้จริงบน wire → อัลกอริทึมใช้กับตระกูลนี้ได้ ทั้งตารางเชื่อถือได้
> - **id ไม่เคยเป็น code immediate** ทั้ง 17 ตัว (dword scan ตัด rel32 tail ของ `E8/E9` **และ `0F 8x`** + สแกน imm16 → 0 hit) · id-slot มี **writer จุดเดียว** (reg thunk ของตัวเอง) และ **reader จุดเดียว** (`mov ax,[slot]; ret` = vtable +0x10) — กำแพง runtime-assigned เดียวกับ cohort TargetPos/ItemOperate/TeleportCheck
> - **สองเส้นทางชื่อบรรจบกัน 17/17:** (ก) name literal → reg thunk → id-slot → get-id stub → vtable+0x10 และ (ข) vtable+0x00 → type-node getter → type node → registration → descriptor `.?AVChannel_XxxVital@@` — การผูก vtable↔ชื่อ**ไม่ใช่การเดา**
> - **Wire schema decode ครบทุกช่อง** — Serialize = vtable **+0x18** เป็น routine **สองทิศทางตัวเดียว** `thiscall Serialize(bool save, Stream*) ret 8` (`bl` เลือก codec write/read) → routine เดียวกัน decode ขาเข้าได้ · wstring codec `0x89A810/0x89A880` = **tag `0x48` + u32 byte-length + UTF-16LE** · scalar codec `0x89A600/0x89A640` = stdcall(tag,ptr,width) ret 0xC (ตัวเดียวกับ MOVE-PROJECT-001)
> - **⭐ recipient resolution เจอแล้ว:** `Channel_WhisperVital` เป็น**ช่องเดียวที่มี wstring ตัวที่สาม** — Serialize `0x65AEA0` ปล่อย speaker@+0x34, body@+0x18, **recipient@+0x50**, u8(tag `0x0B`)@+0x6C · ctor `0x658240` ของ Whisper เอง construct +0x50 และ zero +0x6C (จึงเป็น field ของ Whisper ไม่ใช่ของ base) · dispatcher อ่าน u8@+0x6C เป็น **result code**: `1` → system message `0x0B`, `2` → `0x18`, อื่น ๆ → render เป็น `WhisperTalk`
> - **5 ช่องใช้ serializer ตัวเดียวกัน** (`0x65AD40` = ของ base `Channel_MessageVtial`): LocalTalk / Party / Guild / ActorBoardcast / GMGlobal → **wire เหมือนกันเป๊ะ แยกกันด้วย 16-bit class id เท่านั้น** ⇒ **channel identifier = vital id ไม่ใช่ selector ใน payload**
> - **payload 34 ไบต์ของ GT-006 replay ผ่าน schema นี้พอดี 0 ไบต์เหลือ:** `48 00000000` (wstring ว่าง = speaker) + `48 18000000` + 24 ไบต์ UTF-16LE `"PFCHATPROBE1"` — decode ท่อน "opaque 10-byte prefix" ที่ CHAT-ECHO-002 อ่านได้แค่ระดับ "น่าจะเป็น wstring header สองตัว" ให้กลายเป็น field ที่มีชื่อและ offset จริง
> - **ลำดับชั้น routing อ่านได้จาก type-node registration block `0xBF74F0..0xBF7AB0` (23 entry):** `Channel_BasicVtial` → {`Channel_CommandVtial`(7 ใบ), `Channel_MessageVtial`, `Channel_ForbidTalkNotificationVtial`} · `Message` → {`Channel_GlobalVital`(7 ใบ), `Channel_LocalVital`(2 ใบ)} — **Command = คำสั่งสมาชิกภาพ / Message = เนื้อหาแชท / Global = มีปลายทางหรือ scope ทั้งเซิร์ฟ / Local = scope ระยะใกล้**
> - **Join/Leave = membership protocol จริง:** ทุก `Join*`/`Leave*` มี **u8 result ต่อท้าย** และใช้ delivery hook แบบ **gated** ที่ **ตัดการส่งต่อเข้า ChannelModule_Client เมื่อ byte นั้น ≠ 0** (`0x65C8B0` gate +0x3D · `0x65C950` gate +0x21 · `0x65CB40` gate +0x24 — offset ตรงกับ u8 ตัวสุดท้ายใน schema ของช่องนั้นเป๊ะ) · คู่ `On Actor*` ใช้ serializer ร่วม `0x65B140` และ **เพิ่ม wstring ชื่อ actor** = notification ของ request
> - **ช่องว่างฝั่ง server ใหญ่มาก:** v141 (immutable) **ไม่มีคำว่า `Channel_` เลยแม้แต่ token เดียว และไม่มี id ใดใน 17 ตัว** · มีแค่ `src/pirateforce_foundation/chat_input_hypothesis.py` ที่แตะ **1 ใน 17** (`0xAC52`) และยังเรียกมันว่า `UNKNOWN_0xAC52` + "compared as one opaque pinned blob" (echo ไม่ decode) → **17 ช่องฝั่ง client · 1 ช่องถูกแตะฝั่ง server · 0 ช่องถูก decode ฝั่ง server**
>
> **เกรด:** identity/id table · id wall · vtable map · hierarchy · wire schema 12 serializer · recipient field · join/leave result gate · client dispatch chain = **A** (byte-exact static, verifier reproduce ได้, ทุก span pin sha-256) · **พฤติกรรม routing ของ original server = ไม่ claim** (uncaptured — ไม่เคยมี 2 session พร้อมกัน) · net: `chat/chat_channels_and_routing` **`not_started` → `in_progress`** (ไม่ flip `runtime_pass`)

---

## 1. ตารางช่องสัญญาณครบ 17 แถว

id คำนวณจาก **name literal ในอิมเมจล้วน ๆ** ด้วยแฮช NAMEID-HASH-001 (`0x89B220`) · ทุกช่องมี reg thunk 1 จุด / id-slot 1 ช่อง / get-id stub 1 ตัว / vtable 1 ตัว

| # | class (สะกดตามไบนารี) | name VA | **id** | reg thunk | id-slot | get-id | vtable | Serialize (vt+0x18) | sizeof | parent | server |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `Channel_ForbidTalkNotificationVtial` | `0xF37960` | **`0xFDF2`** | `0xBF72B0` | `0x1084454` | `0x65A9E0` | `0xF37804` | `0x65AE00` | `0x1C` | Basic | — |
| 2 | `Channel_LocalTalkMessageVital` | `0xF37984` | **`0xAC52`** ⭐ | `0xBF72D0` | `0x1084458` | `0x6580B0` | `0xF3775C` | `0x65AD40` | `0x50` | Local | echo opaque |
| 3 | `Channel_LocalPerformanceVital` | `0xF379A4` | **`0xAE8C`** | `0xBF72F0` | `0x108445C` | `0x5BEAE0` | `0xF2D0D4` | `0x65AE30` | `0x30` | Command | — |
| 4 | `Channel_PartyMessageVital` | `0xF379C4` | **`0x82E6`** | `0xBF7310` | `0x1084460` | `0x657DA0` | `0xF37628` | `0x65AD40` | `0x50` | Local | — |
| 5 | `Channel_WhisperVital` | `0xF379E0` | **`0x556C`** | `0xBF7330` | `0x1084464` | `0x6582B0` | `0xF37788` | `0x65AEA0` | `0x70` | Global | — |
| 6 | `Channel_GuildMessageVital` | `0xF379F8` | **`0x8189`** | `0xBF7350` | `0x1084468` | `0x657DD0` | `0xF37654` | `0x65AD40` | `0x50` | Global | — |
| 7 | `Channel_ActorBoardcastMessageVital` | `0xF37A14` | **`0xEDFA`** | `0xBF7370` | `0x108446C` | `0x658030` | `0xF37730` | `0x65AD40` | `0x50` | Global | — |
| 8 | `Channel_GMGlobalMessageVital` | `0xF37A38` | **`0x9F2C`** | `0xBF7390` | `0x1084470` | `0x65AC10` | `0xF3790C` | `0x65AD40` | `0x50` | Global | — |
| 9 | `Channel_JoinCustomChannelVital` | `0xF37A58` | **`0xBA58`** | `0xBF73B0` | `0x1084474` | `0x657E70` | `0xF37680` | `0x65AF80` | `0x40` | Command | — |
| 10 | `Channel_OnActorJoinCustomChannelVital` | `0xF37A78` | **`0x18DA`** | `0xBF73D0` | `0x1084478` | `0x65AA80` | `0xF37830` | `0x65B140` | `0x58` | Command | — |
| 11 | `Channel_LeaveCustomChannelVital` | `0xF37AA0` | **`0xC663`** | `0xBF73F0` | `0x108447C` | `0x657F70` | `0xF376AC` | `0x65B060` | `0x40` | Command | — |
| 12 | `Channel_OnActorLeaveCustomChannelVital` | `0xF37AC0` | **`0x2770`** | `0xBF7410` | `0x1084480` | `0x65AB90` | `0xF3785C` | `0x65B140` | `0x58` | Command | — |
| 13 | `Channel_CustomChannelMessageVital` | `0xF37AE8` | **`0xE064`** | `0xBF7430` | `0x1084484` | `0x657FF0` | `0xF376D8` | `0x65B1E0` | `0x60` | Global | — |
| 14 | `Channel_JoinOriginalSinChannelVital` | `0xF37B0C` | **`0xFA07`** | `0xBF7450` | `0x1084488` | `0x65ABB0` | `0xF37888` | `0x65B260` | `0x28` | Command | — |
| 15 | `Channel_OriginalSinChannelMessageVital` | `0xF37B30` | **`0x265C`** | `0xBF7470` | `0x108448C` | `0x65ABD0` | `0xF378B4` | `0x65B310` | `0x54` | Global | — |
| 16 | `Channel_JoinClassChannelVital` | `0xF37B68` | **`0xAC9D`** | `0xBF74B0` | `0x1084494` | `0x65ABF0` | `0xF378E0` | `0x65B450` | `0x28` | Command | — |
| 17 | `Channel_ClassChannelMessageVital` | `0xF37B88` | **`0xD1F8`** | `0xBF74D0` | `0x1084498` | `0x658010` | `0xF37704` | `0x65B500` | `0x54` | Global | — |

- **id ทั้ง 17 ไม่ชนกันเลย** · **id ทั้ง 17 ไม่ปรากฏเป็น code immediate ใน `.text`** (dword scan ตัด rel32 ของ `E8/E9` และ `0F 8x`; รวม imm16 form `66 B8 / 66 3D / 66 81 F8 / 66 A9`) → runtime-assigned ล้วน
- reg thunk เรียงติดกัน stride `0x20` · id-slot เรียงติดกัน stride `4` โดยมี **ช่องว่างจริงที่ `0x1084490` = `CBoardcastVital`** (thunk `0xBF7490`, ไม่ใช่ `Channel_*` — ไม่นับรวม)
- `sizeof` มาจาก vtable **+0x0C** (`mov eax,<size>; ret`) และ **ตรงกับ layout ที่ decode ได้ทุกช่อง** (เช่น ForbidTalk `0x1C` = header `0x18` + u8; Whisper `0x70` = `0x50` + wstring `0x1C` + u8)
- vtable **+0x08 = `0x401B20`** ทั้ง 17 = shared framework const ของ cohort เดิม (TargetPos / ECHO / ItemOperate / MovementAttr)
- 16/17 vtable อยู่ในตาราง `.rdata` ต่อเนื่อง `0xF37628..0xF37938` (stride `0x2C`, 11 slot); `Channel_LocalPerformanceVital` อยู่แยกที่ `0xF2D0D4`
- **การสะกดผิดในไบนารีจริง**: `Vtial` (ไม่ใช่ `Vital`) ปรากฏใน 4 คลาส — `Channel_ForbidTalkNotificationVtial`, `Channel_BasicVtial`, `Channel_CommandVtial`, `Channel_MessageVtial` — **แฮชใช้ตัวสะกดตามไบนารี** (เปลี่ยนเป็น `Vital` แล้ว id เพี้ยนทันที)

## 2. Wire schema รายช่อง (decode ทีละ field จาก Serialize)

Serialize = **vtable +0x18** ทุกช่อง เป็น `thiscall Serialize(bool save, Stream*) ret 8` ตัวเดียว: `test bl,bl` เลือกฝั่ง **write** (wstring `0x89A810` / scalar `0x89A600`) หรือ **read** (`0x89A880` / `0x89A640`) → **routine เดียวกัน decode ขาเข้าได้** (direction-agnostic แบบเดียวกับ MOVE-PROJECT-001)

**codec:**
- `wstring` (tag `0x48`) = `tag 0x48` + `u32 byte-length` + `byte-length` ไบต์ UTF-16LE (ไม่มี NUL) — `0x89A810` คำนวณ `edi = 2*len` แล้วส่ง `edi+4` เป็น field width, `ret 4`
- `scalar` = `stdcall(tag, ptr, width) ret 0xC` — tag ที่พบในตระกูลนี้: `0x0B`/w1 (u8) · `0x08`/w1 (u8 อีกชนิด) · `0x12`/w2 (u16) · `0x19`/w4 (u32) · `0x32`/w8 (qword handle/identity)

| serializer | ใช้โดย | ลำดับ field บน wire |
|---|---|---|
| `0x65AD40` **(base `Channel_MessageVtial`)** | LocalTalk · Party · Guild · ActorBoardcast · GMGlobal | `wstring@+0x34` (speaker) → `wstring@+0x18` (body) |
| `0x65AEA0` | **Whisper** | `wstring@+0x34` → `wstring@+0x18` → **`wstring@+0x50` (recipient)** → `u8(0x0B)@+0x6C` (result) |
| `0x65B1E0` | CustomChannelMessage | `wstring@+0x34` → `wstring@+0x18` → `u8(0x08)@+0x50` → `qword(0x32)@+0x58` (channel handle) |
| `0x65B310` | OriginalSinChannelMessage | `wstring@+0x34` → `wstring@+0x18` → `u8(0x08)@+0x50` |
| `0x65B500` | ClassChannelMessage | `wstring@+0x34` → `wstring@+0x18` → `u32(0x19)@+0x50` (class id) |
| `0x65AF80` | JoinCustomChannel | `qword(0x32)@+0x18` → `wstring@+0x20` (ชื่อช่อง) → `u8(0x0B)@+0x3C` → `u8(0x0B)@+0x3D` (**result**) |
| `0x65B060` | LeaveCustomChannel | `qword(0x32)@+0x18` → `u8(0x0B)@+0x20` → `u8(0x0B)@+0x21` (**result**) → `wstring@+0x24` |
| `0x65B140` | **OnActorJoinCustomChannel + OnActorLeaveCustomChannel** | `qword(0x32)@+0x18` → `wstring@+0x20` (ชื่อช่อง) → **`wstring@+0x3C` (ชื่อ actor)** |
| `0x65B260` | JoinOriginalSinChannel | `qword(0x32)@+0x18` → `u8(0x08)@+0x20` → `u8(0x0B)@+0x21` (**result**) |
| `0x65B450` | JoinClassChannel | `qword(0x32)@+0x18` → `u32(0x19)@+0x20` → `u8(0x0B)@+0x24` (**result**) |
| `0x65AE00` | ForbidTalkNotification | `u8(0x0B)@+0x18` เดี่ยว ๆ |
| `0x65AE30` | LocalPerformance | `qword(0x32)@+0x18` → `qword(0x32)@+0x20` → `u16(0x12)@+0x28` |

**ข้อสรุปสำคัญ 3 ข้อจากตารางนี้**
1. **ช่องข้อความ 5 ช่องใช้ serializer ตัวเดียวกันเป๊ะ** → payload บน wire **เหมือนกันทุกไบต์** ⇒ สิ่งที่บอกว่า "ข้อความนี้ไปช่องไหน" คือ **16-bit class id เท่านั้น** ไม่มี channel selector ฝังใน payload — นี่คือคำตอบตรง ๆ ของ "Channel identifiers"
2. **`Channel_WhisperVital` เป็นช่องเดียวที่มี wstring ตัวที่ 3** → นี่คือ **recipient resolution** ที่ coverage note บอกว่า uncaptured
3. **ทุก `Join*`/`Leave*` มี u8 result ต่อท้าย** (ดู §4)

**ยืนยันกับของจริง (GT-006):** payload 34 ไบต์ที่ client ส่งจริงตอนพิมพ์แชท ถอดตาม schema `0x65AD40` ได้พอดีเป๊ะ เหลือ 0 ไบต์
```
48 00 00 00 00                              wstring#1 tag 0x48, len 0   -> speaker  @+0x34 (ว่าง)
48 18 00 00 00                              wstring#2 tag 0x48, len 24  -> body     @+0x18
50 00 46 00 43 00 48 00 41 00 54 00 ...     "PFCHATPROBE1" UTF-16LE
```
ตรงกับ `CHAT_INPUT_PROBE_PAYLOADS["probe1"]` ใน `src/pirateforce_foundation/chat_input_hypothesis.py` byte-for-byte — และ **re-encode กลับได้ไบต์เดิม** (มีเคสใน pytest) · นี่ยกระดับ CHAT-ECHO-002 จาก "อ่าน prefix 10 ไบต์เป็น wstring header สองตัว (สมมติฐาน)" เป็น "field ที่มี offset/เจ้าของคลาส/ลำดับจริงจาก disasm"

**ยังไม่ decode รอบนี้:** ความหมายเชิงค่าของ `u8(0x08)` ใน CustomChannelMessage/OriginalSin (`@+0x50`), ความหมายของ `u8@+0x3C` ใน JoinCustomChannel, ความหมายของ `u16@+0x28` ใน LocalPerformance และ payload ของ `CBoardcastVital` (นอก scope — ไม่ใช่ `Channel_*`)

## 3. ลำดับชั้นคลาส = โครงสร้าง routing ที่ client คาดหวัง

หลักฐาน: **type-node registration block `0xBF74F0..0xBF7AB0`** (23 entry, stride `0x40`) แต่ละ entry คือ
```
push 0x10945D0                       ; allocator
mov  ecx, <type descriptor>          ; ".?AVChannel_XxxVital@@"
call [0xC3B7AC]                      ; demangle -> ชื่อ
push eax
[push <PARENT node>]                 ; <-- ขอบของ hierarchy (root ไม่มี: call 0x5F33F0 แทน)
mov  ecx, <own node>
call 0x88F2E0                        ; ลงทะเบียน type node
```
อ่านขอบทั้ง 23 ได้ต้นไม้:

```
Channel_BasicVtial                              node 0x1084448   (ROOT)
├── Channel_CommandVtial                        node 0x108443C   — คำสั่ง/สมาชิกภาพ (7 ใบ)
│     ├── Channel_LocalPerformanceVital                 0x10843F4
│     ├── Channel_JoinCustomChannelVital                0x10843AC
│     ├── Channel_OnActorJoinCustomChannelVital         0x10843A0
│     ├── Channel_LeaveCustomChannelVital               0x1084394
│     ├── Channel_OnActorLeaveCustomChannelVital        0x1084388
│     ├── Channel_JoinOriginalSinChannelVital           0x1084370
│     └── Channel_JoinClassChannelVital                 0x108434C
├── Channel_MessageVtial                        node 0x1084430   — เนื้อหาแชท
│     ├── Channel_GlobalVital                   node 0x1084418   — มีปลายทาง/scope กว้าง (7 ใบ)
│     │     ├── Channel_WhisperVital                    0x10843DC
│     │     ├── Channel_GuildMessageVital               0x10843D0
│     │     ├── Channel_ActorBoardcastMessageVital      0x10843C4
│     │     ├── Channel_GMGlobalMessageVital            0x10843B8
│     │     ├── Channel_CustomChannelMessageVital       0x108437C
│     │     ├── Channel_OriginalSinChannelMessageVital  0x1084364
│     │     └── Channel_ClassChannelMessageVital        0x1084340
│     └── Channel_LocalVital                    node 0x108440C   — scope ระยะใกล้ (2 ใบ)
│           ├── Channel_LocalTalkMessageVital           0x1084400
│           └── Channel_PartyMessageVital               0x10843E8
└── Channel_ForbidTalkNotificationVtial         node 0x1084424   — ไม่ใช่ทั้ง Command และ Message
```
(`CBoardcastVital` node `0x1084358` เป็น root แยกอีกต้น — ไม่อยู่ในตระกูล `Channel_*`)

- **base ทั้ง 5 ไม่มี name literal แบบ plaintext และไม่มี registration thunk ⇒ ไม่มี wire id** — มีแค่ 17 คลาสรูปธรรมที่ addressable บน wire
- ผูก vtable ↔ node ↔ ชื่อได้ 17/17 ผ่าน vtable **+0x00** (`mov eax,<node>; ret` บางตัวผ่าน `jmp`) และตรงกับชื่อจาก reg thunk ทุกตัว
- clone (`vtable +0x24`) เดินตาม hierarchy จริง: clone ของ Whisper `0x65AF20` **เรียก base clone `0x65ACB0` ก่อน** แล้วค่อย copy `+0x50` (wstring) และ `+0x6C` (u8) ของตัวเอง — โครง inheritance ยืนยันซ้ำจาก code path
- **client-side routing:** vtable **+0x1C** = hook รับเข้า — resolve module registry `[0x1032EC4]+0x130` ด้วยชื่อ ASCII **`"ChannelModule_Client"`** (`0xF22CB4`), is-a กับ type node `0x1084304` แล้วส่งต่อ `0x659870` ซึ่งเป็น **โซ่ downcast เรียงลำดับ 14 ช่อง**:
  `LocalTalk → Whisper → Guild → Party → ActorBoardcast → LocalPerformance → CustomChannelMessage → JoinCustom → OnActorJoinCustom → LeaveCustom → OnActorLeaveCustom → ClassChannelMessage → GMGlobal → ForbidTalkNotification`
  แต่ละกิ่งเลือก **style name ต่อช่อง** (UTF-16LE): `LocalTalk` · `WhisperTalk` · `GuildTalk` · `PartyTalk` · **`YellTalk`** (= ActorBoardcast) · `LocalPerformance` · `CustomDefine` · `ClassTalk` (หน้าต่าง: `Main_Chat`, `Main_Chat_Join`, `Main_Chat_Setting`, `ResetCustomChannelName`)
- **negative ที่มีหลักฐาน:** `Channel_JoinOriginalSinChannelVital`, `Channel_OriginalSinChannelMessageVital`, `Channel_JoinClassChannelVital` **ไม่มี downcast consumer ที่ไหนเลยใน `.text`** (อ้างอิงเดียวคือ self is-a ใน clone ของตัวเอง) → **3 ใน 17 ช่องเป็น producer-side อย่างเดียวในบิลด์นี้**

## 4. Join/Leave lifecycle — มี membership protocol จริง

1. **คู่ request → notification:** `Channel_JoinCustomChannelVital` / `Channel_LeaveCustomChannelVital` (ฝั่งขอ) จับคู่กับ `Channel_OnActorJoinCustomChannelVital` / `Channel_OnActorLeaveCustomChannelVital` (ฝั่งแจ้ง) — ทั้งสี่เป็น `Channel_CommandVtial`
2. **notification เพิ่ม field ที่ request ไม่มี:** ทั้งสอง `OnActor*` ใช้ serializer ร่วม `0x65B140` = `qword(0x32) channel handle @+0x18` → `wstring ชื่อช่อง @+0x20` → **`wstring ชื่อ actor @+0x3C`** — คือ "ใครเข้า/ออก" ซึ่ง request ไม่ต้องส่ง (server เป็นคนเติม)
3. **result code + gate:** ทุก `Join*`/`Leave*` มี u8 ท้าย schema และ **ใช้ delivery hook แบบ gated**

| ช่อง | delivery hook (vt+0x1C) | gate byte | u8 ตัวสุดท้ายใน schema |
|---|---|---|---|
| JoinCustomChannel | `0x65C8B0` | `[this+0x3D] != 0` → ไม่ส่งต่อ | `u8@+0x3D` ✓ |
| LeaveCustomChannel | `0x65C950` | `[this+0x21] != 0` → ไม่ส่งต่อ | `u8@+0x21` ✓ |
| JoinOriginalSinChannel | `0x65C950` | `[this+0x21] != 0` | `u8@+0x21` ✓ |
| JoinClassChannel | `0x65CB40` | `[this+0x24] != 0` | `u8@+0x24` ✓ |
| ทุกช่องที่เหลือ | `0x65C850` (ไม่มี gate) | — | — |

   offset ที่ gate ตรงกับ u8 ตัวสุดท้ายของ schema **เป๊ะทุกช่อง** ⇒ byte นั้นคือ **ผลลัพธ์ของคำสั่งสมาชิกภาพ** (0 = สำเร็จ → เดินต่อเข้า ChannelModule_Client, ≠0 = ล้มเหลว → ตัดทิ้งเงียบ ๆ แต่ยัง return true)
4. **Whisper ก็มี result byte แต่คนละกลไก:** u8@+0x6C ไม่ได้ gate ที่ hook แต่ถูก dispatcher อ่านตรง ๆ (`0x65999B`): `==1` → push system-message id `0x0B`, `==2` → push `0x18`, อื่น ๆ → render ปกติ ⇒ **feedback ของ recipient resolution 2 แบบที่แยกจากกัน** (ค่าที่ 1/2 หมายถึงอะไรแน่ ไม่ claim — ต้องเปิดตาราง string ปลายทางซึ่งอยู่นอก scope รอบนี้)

## 5. ช่องว่างฝั่ง server (cross-check บังคับ)

| ด้าน | ผล |
|---|---|
| `current/pf_login_game_server_v141.py` (immutable, อ่านอย่างเดียว) | **ไม่มี token `Channel_` เลย** และ **ไม่ประกาศ id ใดใน 17 ตัว** |
| `src/pirateforce_foundation/*` | แตะเพียง **1 ใน 17** — `chat_input_hypothesis.py` `CHAT_INPUT_VITAL_ID = 0xAC52` |
| คุณภาพของการแตะนั้น | ยังเรียกว่า `UNKNOWN_0xAC52`, "unknown to the server registry", และ prefix 10 ไบต์ถูก "compared as one opaque pinned blob" → **echo แบบไม่ decode** |
| ผลรวม | **17 ช่องฝั่ง client · 1 ช่องถูกแตะฝั่ง server · 0 ช่องถูก decode ฝั่ง server · 16 ช่องไม่มีตัวตนฝั่ง server เลย** |

สิ่งที่รอบนี้ให้เพิ่มกับ server (โดยยังไม่แก้ src ใด ๆ): **ชื่อจริงของ `0xAC52`** (`Channel_LocalTalkMessageVital`), **schema ของมัน** (wstring speaker + wstring body), และ **สูตรคำนวณ id ของอีก 16 ช่องจากชื่อ** — พร้อมให้รอบถัดไปที่แตะ src เอาไปใช้ตรง ๆ

**ขนาดจริงของ routing gap:** ต่อให้ decode ครบทุก field แล้ว สิ่งที่ยังขาดคือ **พฤติกรรมการ fan-out** — ใครได้รับข้อความของช่องไหน, membership authority อยู่ที่ใคร, whisper resolve ชื่อผู้รับอย่างไรเมื่อไม่พบ — ทั้งหมดต้องมี **2 client พร้อมกัน** ซึ่งโปรเจกต์นี้ยังไม่เคยทำได้ (ดู `PF_SESSION_LIMIT001_...`) → next hop = live two-client capture (คิวไว้ข้าง GT-011..GT-015 รอบใหญ่ #3)

## 6. เกรด & สถานะ matrix

- **A (byte-exact static, verifier reproduce, span pin sha-256 ครบ 23 span):**
  ตาราง id ครบ 17 (พร้อม anchor `0xAC52`) · id wall (0 code immediate) · id-slot writer/reader จุดเดียว · vtable map ครบ 17 · สองเส้นทางชื่อบรรจบ 17/17 · hierarchy 23 node · wire schema 12 serializer · GT-006 replay ตรง 0 ไบต์เหลือ · Whisper recipient field + ctor ownership + result code · Join/Leave result gate 4 ช่อง · dispatcher chain 14 ช่อง + style name 8 ชื่อ · server cross-check
- **ไม่ claim:** พฤติกรรม routing/fan-out/membership authority ของ **original server** (uncaptured — ไม่เคยมี 2 concurrent session) · ความหมายเชิงค่าของ result code แต่ละตัว · ความหมายของ `u8(0x08)`/`u8@+0x3C`/`u16@+0x28` · การ render จริงบนจอ (ชั้น client-observable เป็นของรอบใหญ่)
- `chat/chat_channels_and_routing`: **`not_started` → `in_progress`** — evidence_ref = report นี้, test_ref = `tests/test_chat_channel_family_static.py` · **ไม่ flip `runtime_pass`** (ต้องมี two-client capture ก่อน)
- coverage note ควรถูกแก้จาก "Channel identifiers and recipient resolution are uncaptured" เป็น: *"Channel identifiers are now pinned statically byte-exact (17 classes, ids derived from the in-image name literals via the NAMEID-HASH-001 hash, LocalTalk anchor 0xAC52 confirmed) and the Whisper recipient field is decoded; what remains uncaptured is the original server's fan-out/membership behaviour, which needs two concurrent sessions."* — **การแก้ matrix/coverage เป็นงานของ chief** (รอบนี้ไม่แตะ `docs/FUNCTIONAL_COVERAGE.json`)
- ledger: **ไม่เพิ่ม** (characterization ของ client binary + cross-check server ที่มีอยู่ — ไม่มี src/scenario/hypothesis ใหม่)
- ไม่ขัดกับความรู้เดิม: ยืนยัน CHAT-ECHO-002 (prefix = wstring header สองตัว) ให้แข็งขึ้น · ยืนยัน CHAT-ECHO-008 (cohort `Community_*` คนละ family กับ `0xAC52`) — รอบนี้ระบุ family ของ `0xAC52` ได้ว่าคือ `Channel_*` · ต่อยอด NAMEID-HASH-001 โดยตรง (ใช้แฮชเดิม ไม่คิดใหม่)

## 7. Reproduce

```
py -3 tools/pf_chat_channel_family_static.py                  # 69 guards, exit 0
py -3 -m pytest tests/test_chat_channel_family_static.py -q   # 15 passed
```
Evidence read-only ล้วน: อ่าน client binary (disassemble ด้วย capstone) + อ่าน server source · **ไม่รัน server / ไม่ต่อ network / ไม่เปิด GameClient / ไม่แตะ canonical DB / ไม่ commit** · ไม่มีการอัปโหลด/ส่งออกไฟล์ proprietary ใด ๆ

**ไฟล์ที่รอบนี้เพิ่ม (3 ไฟล์ ไม่มีการแก้ไฟล์เดิม):**
- `tools/pf_chat_channel_family_static.py`
- `tests/test_chat_channel_family_static.py`
- `reports/PF_CHAT_CHANNEL001_CHANNEL_FAMILY_AND_ROUTING_STATIC_20260818.md`
