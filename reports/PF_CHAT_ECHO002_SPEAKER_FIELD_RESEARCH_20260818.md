# PF CHAT-ECHO-002 — speaker field research: ชื่อผู้พูดใน 0xAC52 มาจากไหน และ `[ทั่วไป]` เป็นของใคร (2026-08-18)

งานวิจัยหลักฐานล้วน (ลูกมือวิเคราะห์ รอบหลัง GT-009 PASS) — **ไม่มีการแก้โค้ด ไม่มี hypothesis ใหม่ถูกเปิดในรายงานนี้**
เป้า: (1) decode โครงเฟรม `0xAC52` เท่าที่หลักฐานให้ (2) พิสูจน์ที่มาของ channel tag `[ทั่วไป]`
(3) รวมรายชื่อ vital ตระกูล chat จาก client binary registry (4) เสนอ candidate สำหรับใส่ speaker name
ให้ chief เลือกเปิด HYP รอบถัดไป

ข้อค้นพบใหญ่ที่เปลี่ยนภาพ: **registry จาก client binary ระบุชื่อจริงของ `0xAC52` ไว้แล้ว** —
`Channel_LocalTalkMessageVital` (`pf_bridge\VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv` บรรทัด 259)
ชื่อ "UNKNOWN_0xAC52" ที่ใช้กันมาจึงล้าสมัยแล้ว (registry ไฟล์นี้ลงวันที่ 2026-08-17 — หลังจาก
GT-006/HYP-PF-014 ถูกเขียน) — การตั้งชื่อ semantic อย่างเป็นทางการเป็นอำนาจ chief แต่หลักฐาน static
ชี้ชัดว่า client เรียกมันว่า LocalTalk = แชท "ทั่วไป" ระยะใกล้

---

## (a) Decode โครงเฟรม 0xAC52 เท่าที่หลักฐานให้

### ตัวอย่าง (samples) ที่มีทั้งหมด

GT-009 ให้ payload **สามความยาวต่างกัน** — จุดชี้ขาดที่ GT-006 (สอง sample ยาวเท่ากัน) ไม่มี:

| seq | ข้อความที่พิมพ์ | payload | prefix 10B ที่จับได้ | server echo? |
|---|---|---|---|---|
| 2–4 | `PFCHATPROBE1/2/9` (12 ตัว) | 34B | `48 00 00 00 00 48 18 00 00 00` | ✅ 66B frame |
| 5 | `SHORT` (5 ตัว) | 20B | `48 00 00 00 00 48 0A 00 00 00` | ❌ เงียบ (fail closed) |
| 6 | `PFCHATPROBETOOLONG` (18 ตัว) | 46B | `48 00 00 00 00 48 24 00 00 00` | ❌ เงียบ (fail closed) |

ที่มา: `GameClient\capture_gt009_20260818_015036\capture_v141\GAME_EVENTS_LIVE.txt` บรรทัด 3–7
(payload hex เต็ม) · raw hex เฟรมเต็ม `...\GAME_20260818_015221_742636_53701.txt` (เช่น frame 105
บรรทัด 1373–1385) · ฝั่ง server `...\server_console_live.out.txt` บรรทัด 435–444 (PROBE1+echo),
529–538 (PROBE2), 557–566 (PROBE9), 657–660 (SHORT ไม่มี echo — heartbeat เท่านั้นตามหลัง),
677–683 (TOOLONG ไม่มี echo)

### กุญแจ cross-vital: convention "tag 0x48 wstring" พิสูจน์ Grade A อยู่แล้วที่อื่น

`reports\PF_CHARACTER_NAME001_PLAYER_NAME_PROJECTION_STATIC_IMPLEMENTATION_20260816.md`
(Grade A static, ยืนยัน runtime ใน NAME002):

- `actor_wire.read_name()` parse ชื่อตัวละครใน CreateActorDataEx ด้วยโครง **"tag `0x48`,
  u32 byte length, strict UTF-16LE"** (บรรทัด 55–57 ของ report นั้น)
- StartGame `ActorAttr` name bit เขียน **"exactly one tag-`0x48` name wstring"** (บรรทัด 63)

ดังนั้น `0x48 + u32len + UTF-16LE` คือ wstring serialization มาตรฐานของ client ที่เรามีหลักฐาน
disassembly ระดับ Grade A รองรับแล้ว — ไม่ใช่การเดาจาก chat frame อย่างเดียว

### ตาราง byte offset (payload ของ nested vital 0xAC52 ทิศ client→server)

| offset | ขนาด | ค่าที่จับได้ | การตีความ | ความมั่นใจ |
|---|---|---|---|---|
| 0 | 1 | `0x48` (ทุก sample) | tag เปิด wstring ตัวที่ 1 | **สูง** — ตรง convention Grade A ของ CreateActorDataEx/ActorAttr |
| 1–4 | 4 | `00 00 00 00` (ทุก sample) | u32 LE byte-length ของ wstring#1 = 0 → **wstring ว่าง** | **สูง** ว่าเป็น length ของ wstring ว่าง (โครงสร้าง) |
| — | — | — | wstring#1 = **ชื่อผู้พูด** (client ส่งว่าง ให้ server เติม) | **ปานกลาง** — อนุมานจากผล render (ดูด้านล่าง) ยังไม่มี sample ที่ field นี้ไม่ว่าง |
| 5 | 1 | `0x48` (ทุก sample) | tag เปิด wstring ตัวที่ 2 | **สูง** |
| 6–9 | 4 | `18`/`0A`/`24` `00 00 00` | u32 LE byte-length ของข้อความ = 24/10/36 = 2×(12/5/18 ตัวอักษร) | **สูง** — สามค่าแปรผันตรงตามความยาวข้อความ (GT-006 มองเป็น "candidate" เพราะมีค่าเดียว — ตอนนี้ยืนยันแล้ว) |
| 10.. | len | UTF-16LE | ข้อความที่พิมพ์ ไม่มี terminator | **สูง** — ถอดตรงตัวทุก sample |

ขนาดรวม = 5 + 5 + text_len: 34=10+24 ✓ · 20=10+10 ✓ · 46=10+36 ✓ (ทั้งสาม sample)

**การอ่านแบบแข่ง (ยังตัดไม่ได้ 100%):** bytes 1–4 อาจเป็น "tag 0x48 + u32 *ค่า*"
(เช่น speaker actor id หรือ channel id ที่ client ส่ง 0) แทนที่จะเป็น length ของ wstring ว่าง —
ทุก sample มีค่า 0 เหมือนกันหมดจึงแยกสองการอ่านนี้ไม่ได้จาก wire อย่างเดียว น้ำหนักเอียงไปทาง
wstring เพราะ (1) tag `0x48` ตัวเดียวกับ wstring convention ที่พิสูจน์แล้ว (2) render ของ GT-009
สอดคล้องกับ "ชื่อว่าง" พอดี (ดูข้อ b) — จัดเป็นสมมติฐานรอง ไว้ falsify ด้วย A/B (ข้อ d)

### Envelope (บริบท ไม่ใช่ผลใหม่)

- ทิศ client→server: one-vital `GSCN_RunTimeProtocolReq` (outer id 0x6E6F, version 0, mask 0x02,
  vital_count 1, nested version 0) — pinned ใน `src\pirateforce_foundation\chat_input_hypothesis.py`
- echo ของเรา (GT-009): payload เดิม byte-exact ใน `GSCN_RunTimeProtocolRes` v4 one-vital
  (56B PC / 66B frame; payload อยู่ที่ pc[20:54] ตาม assert ใน `make_chat_input_echo_response`)
  — client **รับและ render** โดยไม่ desync ตลอดเทส

## (b) `[ทั่วไป]` มาจากไหน — **client เอง ไม่ใช่ envelope** (หลักฐานปิดได้)

ผลตาเห็น GT-009 (`pf_bridge\GAME_TEST_QUEUE.md` บรรทัด 341–357):
`PFCHATPROBE1` render เป็น **`[ทั่วไป] : PFCHATPROBE1`** ตัวขาว มี channel tag
**ไม่มีชื่อผู้พูด**หน้า `:`

หลักฐานสามชั้นว่า tag เป็นของ client:

1. **บน wire ไม่มีไบต์ภาษาไทยเลย** — echo เป็น byte-exact ของ request (hash-pinned;
   hex เต็มใน server console บรรทัด 440–444): มีแค่ prefix 10B + ASCII interleave
   ไม่มีทางประกอบ `[ทั่วไป]` จากเฟรมนี้ได้
2. **สตริง `[ทั่วไป] ` อยู่ใน string table ฝั่ง client**: `GameClient\Data\B_TEXTDATA_TH.pc_`
   (container `$pcz` + LZMA1 raw ที่ offset 13, props 0x5D dict 64KiB; decompress ได้
   3,548,508 B ตรงกับ declared size; โครง record = u32 string-id + u32 byte-len + UTF-16LE):
   - id **540** (0x21C) = `'[ทั่วไป] '` (มี วงเล็บ+ช่องว่างท้าย ในตัว resource เอง)
   - id **451** (0x1C3) = `': '`
   - ต่อกัน: `'[ทั่วไป] '` + *ชื่อว่าง* + `': '` + `'PFCHATPROBE1'` =
     **`[ทั่วไป] : PFCHATPROBE1`** — ตรงกับที่ตาเห็นทุกตัวอักษรรวมช่องว่างหน้า `:`
   - หมายเหตุ: ค้น `ทั่วไป` ใน `GameClient.bin`/`GameClient.local.bin` ทั้ง UTF-16LE/UTF-8/TIS-620
     = 0 hit — สตริงอยู่ในไฟล์ data ไม่ใช่ตัว binary
3. **client มี vital แยกรายช่องอยู่แล้ว** (ข้อ c) — LocalTalk/Whisper/Party/Guild/Class/Custom/
   OriginalSin/GMGlobal/Broadcast ต่างมี vital id ของตัวเอง จึงไม่จำเป็นต้องส่ง channel บน payload;
   tag ตระกูลเดียวกันเรียงติดกันเป็นชุดใน string table: 528 `[ＧＭ] `, 529 `[ประกาศ] `,
   530 `[ระบบ] ` (= บรรทัด `[ระบบ]` ที่ GT-006 เห็นค้างในหน้าต่างแชท), 540 `[ทั่วไป] `,
   541 `[กระซิบ] `, 542 `[ทีม] `, 543 `[กิลด์] `, 544 `[ทั้งหมด] `, **545 `[ $V1 ] `**
   (parameterized — สำหรับ custom channel ที่ชื่อช่องต้องมากับ data ซึ่งสนับสนุนว่า
   ช่อง "มาตรฐาน" ใช้ tag คงที่ฝั่ง client)

**สรุป (b):** `[ทั่วไป]` = string resource id 540 ของ client — **พิสูจน์ได้ว่าไม่ได้มาจาก envelope**
(ระดับ: ปิดได้ เพราะ wire ทั้งเฟรม echo ถูก pin ด้วย hash และไม่มีไบต์ที่ประกอบเป็นสตริงนี้ได้)
· กลไก*เลือก* tag (จาก vital id `0xAC52` โดยตรง หรือจาก field ใน payload ที่บังเอิญเป็น 0)
ยังแยกไม่ได้จากหลักฐานปัจจุบัน — น้ำหนักเอียงทาง vital id เพราะสถาปัตยกรรม per-channel vital
(candidate ทดสอบอยู่ในข้อ d)

หลักฐานประกอบเพิ่ม (จาก string table เดียวกัน ชุดชื่อช่องไม่มีวงเล็บ — น่าจะเป็น dropdown
เลือกช่องของกล่องพิมพ์): 428 `ทั่วไป`, 429 `กระซิบ`, 430 `ทีม`, 431 `กิลด์`, 432 `ทั้งหมด`,
433 `บาปกำเนิด` (ตรงกับ OriginalSin ใน registry!), 434–436 `เพื่อน 1/2/3` ·
whisper format: 452 `ท่านได้พูดกับ $V1 ว่า: `, 453 ` $V1 พูดกับท่านว่า: ` — **client ประกอบ
ชื่อผู้พูดจากพารามิเตอร์สตริง ($V1)** · 525–527 `แชนแนลเพื่อน 1 (/1)`…`(/3)` (slash command) ·
555 `ยังไม่ได้เข้าแชนแนล`, 562 `เข้าสู่แชนแนล`, 556–558 แท็บ `สนทนา/ต่อสู้/ระบบ`

## (c) Vital ตระกูล chat/channel จาก client binary registry

จาก `pf_bridge\VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv` (ครบทุกตัวที่ match
chat/talk/say/speak/channel/whisper + เพื่อนบ้านที่เกี่ยว):

ตระกูล Channel_* โดยตรง:

| id | ชื่อใน client | หมายเหตุ |
|---|---|---|
| 0xAC52 | **Channel_LocalTalkMessageVital** | = เฟรมแชทของเรา (GT-006/GT-009) |
| 0x556C | Channel_WhisperVital | กระซิบ |
| 0x82E6 | Channel_PartyMessageVital | ทีม |
| 0x8189 | Channel_GuildMessageVital | กิลด์ |
| 0xD1F8 | Channel_ClassChannelMessageVital | ช่องตามอาชีพ |
| 0xE064 | Channel_CustomChannelMessageVital | ช่องตั้งเอง (คู่กับ tag `[ $V1 ] ` id 545) |
| 0x265C | Channel_OriginalSinChannelMessageVital | "บาปกำเนิด" (ชื่อช่อง id 433) |
| 0x9F2C | Channel_GMGlobalMessageVital | ประกาศ GM |
| 0xEDFA | Channel_ActorBoardcastMessageVital | broadcast ผูก actor |
| 0xAE8C | Channel_LocalPerformanceVital | เพื่อนบ้าน LocalTalk (emote/performance?) — ยังไม่มี wire |
| 0xAC9D | Channel_JoinClassChannelVital | join/leave กลุ่ม: |
| 0xBA58 | Channel_JoinCustomChannelVital | |
| 0xC663 | Channel_LeaveCustomChannelVital | |
| 0x18DA | Channel_OnActorJoinCustomChannelVital | |
| 0x2770 | Channel_OnActorLeaveCustomChannelVital | |
| 0xFA07 | Channel_JoinOriginalSinChannelVital | |

เกี่ยวข้องใกล้เคียง (message/broadcast/moderation):
0x8D30 GM_ForbidToTalkResultVital · 0x309E CBoardcastVital · 0x36D2 ShowMessageVital ·
0x4C63 TriggerMessageVital · 0x6416 CTimerMessageVital_GSGC ·
0xBB41/0xBB73 CAchievementsBoardcastReq/ResVital · 0xDCCD Community_ChangeActorPenNameVital

**Corpus negative (สำคัญเท่าผลบวก):** ค้น `44114|0xAC52` ทั่ว capture ทั้งหมดใต้ `GameClient\`
(ทุก `GAME_LIVE.txt`) เจอแค่ 2 ไฟล์ = ของเราเอง: `capture_gt001_20260817_143122` (2 hit = GT-006)
กับ `capture_gt009_20260818_015036` (5 hit) · ฝั่ง `Pirate Force ServerProject`
(references/capture_v141/evidence/derived/analysis) เจอ "AC52" แค่ใน
`derived\v122_quest_operate_deep_disasm.tmp.txt` ซึ่งเป็น**address โค้ด** `0x61ac52` ไม่ใช่ vital id ·
`references\sources` ว่าง — **ไม่มี chat wire จาก server เดิมแม้แต่เฟรมเดียว ทั้งทิศไปและกลับ
และไม่มี wire ของ Channel_* ตัวอื่นเลย** → ทุก response shape ของตระกูลนี้เป็น designed hypothesis
เท่านั้น ไม่มี golden ให้ replay

## (d) Candidate สำหรับใส่ speaker name — จัดอันดับ (ทุกตัว headless A/B ได้ในเลน opt-in เดิม)

พื้นฐานร่วม: แก้เฉพาะฝั่ง compose ใน scenario lane (`chat_input_hypothesis.py` +
scenario json ใหม่) — request classification เดิมคงไว้ · ชั้น wire พิสูจน์ headless ได้ตามแบบ
CHAT-ECHO-001 · ชั้น render ต้องรอบใหญ่ attended ตามนโยบาย

### อันดับ 1 — HYP "server เติม speaker name เป็น wstring#1" (ความมั่นใจ: สูงสุดในชุดนี้ ~70%)

Res payload = `48 <u32 len(name)> <name UTF-16LE> 48 <u32 len(text)> <text UTF-16LE>`
(vital 0xAC52 เดิม, envelope RuntimeRes v4 one-vital เดิมที่พิสูจน์แล้วว่า deliverable)
โดย name = ชื่อตัวละครที่ select อยู่ (จาก `characters` — canonical name เดียวกับที่
NAME001/002 ส่งเข้า ActorAttr ด้วย tag 0x48 แล้ว client รับ)

- ทำไมอันดับ 1: (1) ตรง convention tag-0x48 wstring ที่มีหลักฐาน Grade A สองจุด
  (2) อธิบายผล GT-009 เป๊ะ — ชื่อว่าง → render `[ทั่วไป] : text` ไม่มีชื่อ แต่โครงประโยค
  (tag+separator) ยังครบ แปลว่า client *พยายาม format ชื่อแล้วได้สตริงว่าง* ไม่ใช่ข้ามส่วนชื่อ
  (3) whisper format strings ($V1) ยืนยันว่า client ประกอบชื่อจากข้อมูลสตริง
  (4) ไม่ต้องพึ่ง lookup id→ชื่อฝั่ง client
- ทำนายผล: render `[ทั่วไป] <ชื่อ> : <ข้อความ>` (ช่องว่างรอบ `:` อาจต่างเล็กน้อย — จดตอนเทส)
- A/B: **A** = echo เดิม (baseline GT-009 ที่รู้ผลแล้ว) · **B** = เติมชื่อใน wstring#1
- Falsifier ชัด: ถ้า client เงียบ/render เพี้ยน/ตัดข้อความ → การอ่าน "wstring#1" ผิด
  (และไปเพิ่มน้ำหนักอันดับ 3 ทันที เพราะ length ที่ไม่ใช่ 0 ทำ parse ต่างจากค่า u32 ทั่วไป)
- Headless พิสูจน์ได้: compose ถูกโครง (pc size = 56+2×len(name)) · byte-exact ผ่าน TCP ·
  no-write · ไม่กระทบ heartbeat — แบบเดียวกับ smoke CHAT-ECHO-001 ทุกประการ
- ควรลองในรอบเดียวกัน: ชื่อ ASCII และชื่อไทย (persisted name จริงเป็นอะไร ใช้อันนั้นก่อน)

### อันดับ 2 — sub-variant ของอันดับ 1: ชื่อคนอื่น + ทดสอบกลไก tag ด้วย vital id อื่น (~เท่ากับ 1 แต่ scope ใหม่)

ส่งเฟรมที่สอง (ไม่ echo — inject ตาม cadence heartbeat แบบ HYP-PF-012 lever) เป็น 0xAC52
ชื่อผู้พูด = ชื่อสมมุติที่ไม่ใช่ตัวเรา เช่น `TESTSPEAKER` — พิสูจน์ว่าเฟรมนี้ใช้แสดง
"คนอื่นพูด" ได้ (ปูทาง multi-client) · และ/หรือส่ง payload สองwstringเดิมด้วย vital id
**0xEDFA (ActorBoardcastMessageVital)** หรือ **0x9F2C (GMGlobal)** ใน Res เดียวกัน —
ถ้า render ด้วย tag ต่าง (`[ทั้งหมด]`/`[ประกาศ]`?) = **พิสูจน์กลไก "tag เลือกตาม vital id"**
ในหนึ่งเทส · เสี่ยงกว่า (payload shape ของ vital เหล่านั้นไม่มี golden — อาจ desync)
จึงควรทำหลังอันดับ 1 ผ่าน หรือท้ายเซสชันเดียวกัน (ยอมเสีย session ได้เพราะเป็นเฟรมสุดท้าย)

### อันดับ 3 — การอ่านแบบแข่ง: field#1 = u32 ค่า (speaker actor id) (~20%)

Res payload = `48 <u32 actor_id> 48 <len> <text>` โดย actor id = identity ที่ client รู้จักจาก
StartGame/population — ทำนายว่า client lookup ชื่อเอง · ขัดกับหลักฐาน convention tag-0x48-wstring
จึงอยู่อันดับรอง แต่เป็น counter-hypothesis ที่ต้องมีไว้: ถ้าอันดับ 1 fail รูปแบบ "ตัดข้อความ/
parse เพี้ยน" อธิบายได้ทันทีว่า field#1 ถูก client อ่านเป็นค่า ไม่ใช่ length →
รอบถัดไปสลับมาเทสตัวนี้ · headless พิสูจน์ได้แค่ compose (ไม่มีทาง falsify โดยไม่ใช้ client จริง)

### ทางเสริมที่ไม่ใช่ A/B บน wire (ถ้า chief ต้องการความแน่นอนก่อนเปลืองรอบ attended)

Static: หา handler ของ `Channel_LocalTalkMessageVital` ใน `GameClient.local.bin`
(วิธีเดียวกับ NAME001 — registry TSV นี้ก็สกัดจาก binary ตัวเดียวกัน) แล้วอ่าน parse ของ
payload ตรง ๆ ว่า field#1 ถูก consume เป็น wstring หรือ u32 และสตริง id 540/451 ถูกประกอบ
ที่ callsite ไหน — ปิดคำถามทั้ง (a) และกลไก tag ได้โดยไม่ต้องเดา แลกกับงาน disassembly
หนึ่งรอบ (ไม่มี wire cost)

## (e) ดัชนีหลักฐาน + สิ่งที่ยังขาด

หลักฐานทุกจุดที่อ้างในรายงานนี้:

| ข้อเท็จจริง | ไฟล์/ตำแหน่ง |
|---|---|
| payload 3 ความยาว + hex | `GameClient\capture_gt009_20260818_015036\capture_v141\GAME_EVENTS_LIVE.txt` บรรทัด 3–7 |
| raw frame เต็ม (ตัวอย่าง 46B) | `...\capture_v141\GAME_20260818_015221_742636_53701.txt` บรรทัด 1373–1385 |
| echo PROBE1/2/9 + SHORT/TOOLONG เงียบ | `...\server_console_live.out.txt` บรรทัด 435–444, 529–538, 557–566, 657–660, 677–683 |
| ผล render ตาเห็น `[ทั่วไป] : PFCHATPROBE1` ไม่มีชื่อ | `pf_bridge\GAME_TEST_QUEUE.md` GT-009 result บรรทัด 341–357 |
| ชื่อ vital + ตระกูล Channel | `pf_bridge\VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv` บรรทัด 16, 43, 46, 150, 213, 216, 232, 249, **259**, 260, 264, 272, 286, 293, 308, 319, 327 (+ 67, 75, 129, 172, 275, 276, 307) |
| convention tag-0x48 wstring (Grade A) | `reports\PF_CHARACTER_NAME001_..._20260816.md` บรรทัด 55–57, 63 (runtime ยืนยัน NAME002) |
| string resources 540 `[ทั่วไป] `, 451 `: `, ครอบครัว tag/ชื่อช่อง/whisper $V1 | `GameClient\Data\B_TEXTDATA_TH.pc_` — decompress: `$pcz` header, u32 decl size @+4, LZMA1 raw @+13 (props `5D 00 00 01 00`); record = u32 id + u32 byte-len + UTF-16LE (ทำสำเนาใน /tmp sandbox เท่านั้น ไฟล์ต้นฉบับไม่ถูกแตะ) |
| `ทั่วไป` ไม่อยู่ใน binary (UTF-16/UTF-8/TIS-620) | grep negative บน `GameClient.bin` + `GameClient.local.bin` |
| corpus ไม่มี chat wire ต้นฉบับ | grep `44114|0xAC52` ทุก `GAME_LIVE.txt` ใต้ GameClient (เจอเฉพาะ gt001_143122=GT-006, gt009) · ServerProject references/capture_v141/evidence/derived/analysis (เจอเฉพาะ address `0x61ac52` ใน `derived\v122_quest_operate_deep_disasm.tmp.txt` — ไม่ใช่ vital) |
| envelope/echo composition ที่ใช้ใน GT-009 | `src\pirateforce_foundation\chat_input_hypothesis.py` (pins + `pc[20:54]`) · `reports\PF_CHAT_ECHO001_..._20260817.md` |

สิ่งที่หลักฐานยัง**ไม่**พอสรุป (ห้ามอ่านรายงานนี้เกินนี้):

1. **wstring#1 = "ชื่อผู้พูด" เป็นการอนุมาน** — ไม่มี sample ที่ field นี้ไม่ว่างแม้แต่ตัวเดียว
   (ทุกเฟรมเป็นทิศ client→server ที่ client ส่งว่าง) การยืนยันต้องมาจาก A/B อันดับ 1
   หรือ static handler analysis
2. **กลไกเลือก tag** (vital id vs field ใน payload) ยังแยกไม่ได้ — ทั้ง vital id และ field#1
   คงที่ในทุก sample · ที่ปิดได้จริงคือ "ตัวสตริง tag มาจาก client resources ไม่ใช่ wire"
3. ช่องว่าง/รูปแบบเป๊ะ ๆ ของชื่อใน render (`name : ` vs `name: `) — รอ B test
4. semantics ของ `Channel_LocalPerformanceVital` (0xAE8C) และ payload shape ของ Channel_*
   ตัวอื่นทุกตัว — ไม่มี wire เลย (corpus negative ข้างบน)
5. ข้อจำกัดความยาว/charset ของข้อความ (คีย์ไทยยังไม่เคยลองบน wire) — nonclaim เดิมของ
   HYP-PF-014 ยังคงอยู่ทั้งหมด
6. ไม่มีการ claim ว่า server เดิมตอบแบบไหน — ไม่มี golden ใด ๆ ของตระกูลนี้

ไฟล์ที่แตะในรอบนี้: **เขียนใหม่ 1 ไฟล์** = รายงานนี้เท่านั้น · อ่านอย่างเดียว: captures gt009/gt001/gt010,
GAME_TEST_QUEUE.md (อ่าน ไม่แก้), registry TSV, reports/docs เดิม, src (อ่าน ไม่แก้),
GameClient Data (decompress ลง /tmp ใน sandbox — ไม่แตะไฟล์จริง) · ไม่แตะ DB/LOCK/QUEUE/CONTINUATION ·
ไม่มี git operation
