# LANE-A round `20260901_0550`

2026-09-01T05:37+07:00 - 2026-09-01T05:50+07:00 (+07:00 via `TZ=Asia/Bangkok date`).

**ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน:** ไม่มีสิ่งใหม่บน default boot (พฤติกรรมเดิมทุกจุด, ยืนยันด้วยเทสทั้งชุด
ผ่านเท่ากันก่อน/หลัง) - แต่มนุษย์ที่นั่งหน้าจอตอนนี้ **เดินสายจริงเพื่อทดสอบ GT-079 ได้แล้ว** (สแตจ GM
account ไปฉาก 278 แล้วล็อกอิน) ซึ่งก่อนรอบนี้ใบเทสบอกผิดว่ายังไม่มีเส้นทาง wiring ให้ทำแบบนั้นเลย

## 0. บริบทก่อนเริ่ม

อ่านสถานะจริงตามที่ orchestrator ขอ: `pf_bridge/rounds/A_20260901_0202..0442_*.md` (สี่รอบล่าสุด: `yfbqmg`
ปิดสิบประตูเดิมครบ, `trig7s` สำรวจ M2 trigger-readiness, `re173w` แก้ Columbus mob 360, `re188x` audit
Bg0002 96 placement) ยืนยันว่า **BUILD-001/BUILD-002 (สิบประตูเดิม) เสร็จแล้วจริง** M3 wired นานแล้ว
GT-180 รอ merge+human คนเดียว ไม่มีงานสร้างฉากใหม่ที่ค้างให้สาย A ในคิว M-milestone

**พบจดหมายสำคัญที่ยังไม่ถูกนำมาปรับแผน:**
`notes_to_chief/consumed/20260901_0302_FROM_CHIEF_R278_priority-reorg-panya-order-P1-P2-P3-plus-new-builds.md`
(R278, 03:02+07:00 - ก่อนรอบ `re188x` เริ่มด้วยซ้ำ) - เจ้าของสั่ง**พัก M1-M6 ทั้งหมด** ทุ่มไปที่ P-1/P-2/P-3
+ งานสร้างใหม่สี่ชิ้น มอบ **UI-A (`GT-184`/`GT-185`)** และ **UI-B (`GT-186`)** ให้สาย A โดยตรง - นี่คือ
priority ปัจจุบันจริง ไม่ใช่ฉากถัดไปของ M2 ที่รอบก่อน ๆ กำลังเดินอยู่ บันทึกไว้ให้ชัดว่ารอบนี้ตรวจแล้ว
ไม่ได้พลาด

## 1. สำรวจ UI-A/UI-B ก่อนตัดสินใจว่าจะสร้างอะไร

อ่าน `GT-184`/`GT-185`/`GT-186` เต็ม + `archive/GAME_TEST_QUEUE_ARCHIVE_20260827_closed.md`'s `GT-033`
(variant A/B วัดแล้วทั้งคู่ให้ผลลบ, หกกิ่งที่ตารางสามช่องเดิมไม่ครอบ) + `RE-070`'s ผลเต็ม (DONE/PASS-MIXED)

**สิ่งที่เจอ:** `RE-070` ตอบ objective 3 ข้อของตัวเองครบ (MODE branch map, writer ของ `+0x28`/`+0x24`,
เงื่อนไข gate จริง) แต่ **ไม่มีที่ไหนรายงานว่าใครเขียน `[object+0x18]`** (ตัวแปรอีกตัวที่ gate จริงที่
`0x719620` ต้องการ non-NULL ก่อนจะเรียก teardown) - จ็อบ T5/T6 ของใบเดิมระบุไว้ในลิสต์แต่ผลที่บันทึกไม่ตอบ
ถ้า `+0x18` เขียนได้จาก local UI init เท่านั้น (แบบเดียวกับที่ `+0x28`/`+0x24` วัดว่าไม่มี writer จาก inbound
handler เลย) **การส่ง response ใหม่จากเซิร์ฟเวอร์อาจไม่มีทางเปิดประตูนี้ได้เลย** - ตรงข้ามกับสมมติฐานเดิมของ
ทั้งโปรเจกต์

**ตัดสินใจ:** ไม่เดา ไม่สร้าง variant ใหม่แบบไม่มีหลักฐาน (ตามกฎ "ไม่ตอบคำถาม สร้างของ - แต่ห้ามเดา") เปิด
`RE-189` แทน (`pf_bridge/CLIENT_RE_QUEUE.md`) ถามตรงจุดที่ขาด: ใครเขียน `+0x18` และกิ่งไหนในหกกิ่งที่ยังไม่
ได้ลอง (`GT-033`) สร้างได้จริงในสถาปัตยกรรมของเซิร์ฟเวอร์จำลองนี้เอง (โดยเฉพาะกิ่ง 5 - ปิดพอร์ต LOGIN ด้วย -
ซึ่งต้องเช็คจาก `runtime.py`/`session.py` ที่เป็นไฟล์ของ chief ไม่ใช่ของสาย A) แนบ CORE-REQUEST ล่วงหน้าไว้
(ดูข้อ 4) สำหรับตอนที่ RE-189 ชี้ทางที่สร้างได้จริง

## 2. ระหว่างรอ RE-189 - เจอบั๊กเอกสารจริงสองจุดจากการอ่านโค้ดเดินสาย

ระหว่างไล่โค้ด `resolve_entry`/`world_scene_travel` เพื่อทำความเข้าใจกลไก login ให้ครบก่อนเขียน RE-189
เจอ docstring สองจุดที่ **เขียนผิดข้อเท็จจริงที่วัดได้จริงจาก HEAD**:

1. `world_scene_entry.py` (module docstring): เขียนว่า *"NOTHING IN THIS FILE REACHES A PLAYER UNTIL
   SOMETHING CALLS IT, AND NOTHING CALLS IT YET"* - **เท็จที่ HEAD**: `runtime.py` เรียก
   `world_scene_entry.resolve_entry(` จริงสองจุด (บรรทัด 6244 เป็น probe เงียบ, 6324 เป็นการเรียกจริง)
   ทั้งคู่อยู่ใน login handler ที่ทำงานบน default boot ไม่มีแฟล็ก - ยืนยันด้วยเทสที่ขับ `runtime.py` ตรง ๆ
   (`tests/test_gm_login_scene_override_wiring.py`,
   `tests/test_gm_login_scene_registry_wiring_in_runtime.py`)
2. `world_scene_travel.py` (comment เหนือ `production_allowed`): เขียนคู่กันว่า *"Until runtime.py calls
   into this module, a player logs in exactly where they logged in yesterday"* - เท็จเช่นกัน:
   `runtime.py` เรียกโมดูลนี้ตรง ๆ สามจุด (`is_position_persist_allowed` บรรทัด 3755;
   `spawn_position`/`destination` คู่กันบรรทัด 7603-7604) และอ้อมผ่าน `resolve_entry` +
   `gm/login_scene_admission.py`

ทั้งสองประโยคเคยเป็นจริงตอนรอบที่เขียน (สองรอบแรกของโมดูลนี้ตามที่ docstring บอกไว้เอง) แต่ล้าสมัยหลังรอบ
ที่ต่อสายจริง (ไม่ใช่รอบของสาย A - `runtime.py` เป็นไฟล์ของ chief) **แก้แล้วตามธรรมเนียมเดิมของโปรเจกต์**
(ขีดฆ่า ไม่ลบ ต่อด้วยคำแก้ที่มี span/line citation) ไม่ใช่การเปลี่ยน logic ใด ๆ - ตรวจสอบตัวเองซ้ำ (self
pf-adversary pass) พบว่าฉบับร่างแรกของคำแก้ใน `world_scene_travel.py` **overclaim** ว่า `runtime.py`
เรียก `entry_fields`/`home_return_position` ตรง ๆ ด้วย - grep แล้วพบว่าสองตัวนี้ถูกเรียกทางอ้อมผ่าน
`resolve_entry` เท่านั้น ไม่ใช่ตรง ๆ - **แก้คำก่อน commit** ให้แยก "ตรง" (3 จุด) กับ "อ้อม" ให้ถูกต้อง

## 3. ผลข้างเคียง: `GT-079` เปิดใหม่ได้จริงแล้ว (เคยเขียนว่า BLOCKED-ON-WIRING ผิด)

เพราะ `resolve_entry` ต่อสายแล้วจริง และ `login_entry_allowed` ของฉาก 278 เป็น `true` มาโดย **default**
อยู่แล้ว (`DEFAULT_LOGIN_ENTRY_ALLOWED`, ฟิลด์ไม่เคยถูกปักในทะเบียนมาก่อน - ยืนยันด้วยการรัน
`gm.login_scene_admission.stageable_scene_ids()` สดจาก HEAD ก่อนแก้อะไร: `278` อยู่ในผลลัพธ์แล้ว)
`GT-079` (`SCENE-278-ENTRY-AND-STAGE-EYECHECK-001`) **ไม่ได้ถูก BLOCKED-ON-WIRING อีกต่อไป** - หัวใบเดิม
(2026-08-26) ล้าสมัยตามธรรมเนียมเดียวกับที่ `GT-080` เคยได้รับการแก้มาแล้ว (ขีดฆ่า ไม่ลบ)

รอบนี้ **ปักฟิลด์ `login_entry_allowed` ให้ฉาก 278 อย่างชัดเจนในทะเบียน** (`true`, ไม่เปลี่ยนพฤติกรรม -
ค่า default เดิมก็ `true` อยู่แล้ว) พร้อมเขียน safety case แบบ D1/D2/D3 เต็มรูปแบบตามมาตรฐานที่สิบประตูเดิม
ได้รับ (ซึ่งฉาก 278 ไม่เคยได้รับมาก่อน เพราะมันเปิดอยู่โดย "ค่า default ที่ไม่มีใครสังเกต" ไม่ใช่การตัดสินใจ)
D3 (faction byte) ไม่เกี่ยวเพราะฉากนี้ไม่มีประชากรโดยตั้งใจ (`RE-152`, CLOSED BOUNDED-NEGATIVE)

ปรับหัวใบ `GT-079` ทั้งสองจุด (หัวใบเต็ม + บรรทัดสารบัญ) ตามกฎ "ห้ามลบประวัติเดิม ให้ขีดฆ่าแทน" เพิ่มหัวข้อ
"ทางเข้า" อธิบายว่าต้องผ่าน staged GM account (`config/gm_login_scene.json`, scene_id=278) หรือ
GM `/warp 278` - กลไกเดียวกับสิบประตูเดิม ไม่ใช่ "บูตธรรมดาเข้าเองอัตโนมัติ"

## 4. เทสที่รัน

```
python3 -m pytest tests/test_world_scene_travel.py tests/test_world_scene_entry.py \
  tests/test_world_scene_registry_rule_1_scenes.py tests/test_world_faction_admission.py -q
=> 173 passed, 147 subtests passed

python3 -m pytest tests/test_gm_login_scene_stage.py tests/test_gm_login_scene_override_position_resync.py \
  tests/test_gm_login_scene_override_wiring.py tests/test_gm_login_scene_registry_wiring_in_runtime.py \
  tests/test_gm_login_scene_admission.py tests/test_gm_login_scene_sanctioned_admission.py \
  tests/test_gm_login_scene_sanctioned_barred.py tests/test_gm_login_scene_sanctioned_bypass_wiring.py \
  tests/test_gm_login_scene_override_registry_authority.py \
  tests/test_gm_login_scene_override_standalone_at_login.py tests/test_gm_login_scene_registry_snapshot.py \
  tests/test_lane_a_scene_census.py -q
=> 252 passed, 1026 subtests passed

python3 -m pytest tests/test_tree_is_cp874_safe.py -q
=> 5 passed, 531 subtests passed (ก่อนแก้: 455 - เพิ่มเพราะไฟล์/เนื้อหาใหม่ที่ถูกสแกน)

python3 -m pytest tests/ -q  (ทั้งชุด, ก่อนแก้)
=> 6147 passed, 327 skipped, 13141 subtests passed, 0 failed (143s)

python3 -m pytest tests/ -q  (ทั้งชุด, หลังแก้ครบทุกจุด รวม overclaim fix)
=> 6147 passed, 327 skipped, 13141 subtests passed, 0 failed (133s)
```

จำนวนเทสไม่เปลี่ยน (docstring/comment/JSON metadata เท่านั้น ไม่มีโค้ด logic เปลี่ยนแม้บรรทัดเดียว) 0 failed
ทั้งสองฝั่ง cp874-encodability: `tests/test_tree_is_cp874_safe.py` ครอบคลุมไฟล์ที่แก้ทั้งหมดใน
`src/`/`scenarios/` แล้วผ่าน

## 5. pf-adversary

ไม่มี Agent/subagent tool ให้เรียกในเซสชันนี้ (ตรวจ tool list แล้ว - Read/Grep/Glob/Bash/Edit/Write เท่านั้น)
รายงานให้ orchestrator เรียกเองก่อน push ตามที่ prompt อนุญาต ("รายงานกลับมาให้ฉันเรียกก็ได้") ระหว่างรอ
ทำ **self-adversarial pass** เอง - พบและแก้ 1 ข้อบกพร่องจริงก่อน commit (ดูข้อ 2: overclaim เรื่อง
`entry_fields`/`home_return_position` ถูกเรียกตรง ๆ จาก `runtime.py` - grep แล้วพบว่าเรียกอ้อมผ่าน
`resolve_entry` เท่านั้น แก้คำให้ตรงหลักฐานก่อน commit) **ต้องขอให้ pf-adversary จริงตรวจซ้ำก่อน push**

## 6. ไฟล์ที่แตะ

**pirate-force-server** (3 ไฟล์):
- `src/pirateforce_foundation/world_scene_entry.py` (docstring แก้ - ขีดฆ่าประโยคเท็จ + เขียนคำแก้พร้อม
  line citation ไม่แตะ logic)
- `src/pirateforce_foundation/world_scene_travel.py` (comment แก้ - เดียวกัน)
- `scenarios/world_scene_registry_001.json` (ฉาก 278: เพิ่มฟิลด์ `login_entry_allowed: true` ชัดเจน +
  `login_entry_allowed_because` D1/D2/D3 เต็ม + strike ข้อความ `status` เดิม - ไม่เปลี่ยนพฤติกรรม)

**pf_bridge** (5 ไฟล์):
- `CLIENT_RE_QUEUE.md` (เปิด `RE-189`)
- `GAME_TEST_QUEUE.md` (แก้หัวใบ `GT-079` สองจุด - หัวใบเต็ม + บรรทัดสารบัญ, ขีดฆ่าไม่ลบ)
- `notes_to_chief/20260901_0537_CLAIM-LANE-A-round-scene278-stage-wiring-docs-correction.md` (ใบจอง)
- `notes_to_chief/<timestamp>_LANE-A-STATUS-*.md` (ใหม่ - จดหมายสถานะ)
- `rounds/A_20260901_0550_stale_docstring_fix_scene278_and_re189_opened.md` (ไฟล์นี้เอง)

## 7. CORE-REQUEST

ไม่มีของรอบนี้ - ไม่แตะ `runtime.py`/`app.py`/`current/pf_login_game_server_v141.py` เลย (ตรวจแล้วว่า
`entry_fields`/`home_return_position` overclaim ไม่ใช่การเรียกร้องให้ chief แก้อะไร เป็นแค่คำอธิบายที่ต้อง
แม่นขึ้น) **ล่วงหน้าสำหรับรอบถัดไปเมื่อ `RE-189` ตอบแล้ว:** ถ้า RE-189 ชี้ว่ามีกิ่งที่สร้างได้จริง (เช่น กิ่ง 5
ปิดพอร์ต LOGIN) การต่อสาย variant ใหม่เข้า `LogoutVital` response path จะต้องเป็น CORE-REQUEST ใหม่ (แตะ
call site ใน `runtime.py`) - ยังไม่ขอตอนนี้เพราะยังไม่รู้ว่ากิ่งไหนสร้างได้จริง

## 8. เปิดใบให้สาย C

`RE-189` (`pf_bridge/CLIENT_RE_QUEUE.md`) - ถามว่าใครเขียน `[object+0x18]` ของ orchestrator ที่ `RE-070`
ทิ้งไว้ (T5/T6 ไม่มีผลบันทึก) และกิ่งไหนในหกกิ่งของ `GT-033` สร้างได้จริงในสถาปัตยกรรมเซิร์ฟเวอร์นี้เอง -
ปลดบล็อก `GT-184`/`GT-185`/`GT-186` (UI-A/UI-B, priority ปัจจุบันของสาย A ตาม `PANYA-ORDER 20260901_0215`)

## 9. ASK-COO

ไม่มี - การตัดสินใจไม่เดา variant ใหม่โดยไม่มีหลักฐานใช้หลักการเดิมที่มีอยู่แล้ว (CHARTER, "ห้ามเดา")

-- LANE-A (WORLD) round `20260901_0550`
