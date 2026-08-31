# LANE-A round `p7wm17`, 2026-08-31T20:07+07:00

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

บัญชี GM ที่ staged ไปฉาก 3 (Bg0003, Spice Paradise Island) หรือใช้ `/warp 3` แล้วล็อกอิน
จะไม่โดนปฏิเสธที่หน้า login อีกต่อไป และจะเห็นตัวละคร/มอนสเตอร์ 62 ตัว (จาก 72 placement จริงของฉาก)
ยืนอยู่บนเกาะ แทนที่จะเป็นเกาะว่างเปล่าหรือการปฏิเสธล็อกอิน

## บริบท / ทำไมฉากนี้

ลำดับประตูที่ `COO-DECISION 2026-08-30T14:41+07:00` อนุมัติ (round `12lyda`'s placement-count
table): เปิดแล้ว 4(116), 5(92), 10(100), 14(81), 6(80), 8(76). เหลือ 3(72), 7(68), 9(63), 11(56),
130(42). **ฉาก 3 (Spice Paradise Island, 72 placements) เป็นตัวถัดไปที่มากที่สุดในสี่บานที่เหลือ**
(72 > 68 ของฉาก 7) — ตามที่ CLAIM ของรอบนี้ระบุไว้ก่อนเริ่มงาน
(`pf_bridge/notes_to_chief/` ใบ CLAIM ของรอบ `p7wm17`)

สร้าง+ผูก+เปิดในรอบเดียว ตามรูปแบบบีบอัดที่รอบ `l03cgh`/`fx0007`/`p4wire` ใช้กับฉาก 5/6/8:
เทสทั่วไป (`tests/test_lane_a_scene_census.py::ComposerContractTests`) สมมติไว้แล้วว่าทุกฉากที่
lane นี้ผูก census ให้ต้องเปิดด้วย เพราะฉาก 4/5/6/8/10/14 เปิดหมดแล้วตอนรอบนี้เริ่ม

## สิ่งที่สร้าง

- `src/pirateforce_foundation/world_bg0003_identity.py` (ใหม่) — crosswalk ของ CLINE type 3:
  41 resolved / 10 unresolved จาก 51 Mob-Set numbers (CLINE type 3's ทั้งช่วง key, เหมือนฉาก
  5/6/8) ไม่มี CJK-name drop (ทุก resolved identity เป็น ASCII) แต่มี 9 sets ที่ multi-variant
  outfit — 1 ใน 9 มี 9 variants (P_MALE_015_000_SINGLE ถึง SINGLE9), fan-out กว้างที่สุดที่ lane
  นี้เคยบันทึก
- `src/pirateforce_foundation/world_population_bg0003.py` (ใหม่) — census composer, 62/72
  shippable placements, ไม่มี faction bit (เป็นการตัดสินใจของสาย B), refuse ทุกฉากยกเว้น 3
- wiring: `world_scene_travel.py` (SPICE_PARADISE_SCENE_ID=3 ใน CENSUS_SOURCES),
  `world_population_handoff.py` (ROSTER_COMPOSERS entry), `lane_hooks/lane_a_scene_census.py`
  (console reader), `mob_scene_recompose.py` (ACKNOWLEDGED_WITHOUT_COMPOSER entry — field_mobs
  ไม่รู้จักฉาก 3 เช่นกัน)
- `scenarios/world_scene_registry_001.json` แถว n_id=3: `login_entry_allowed: true` +
  `login_entry_allowed_because` (D1/D2/D3 safety case เหมือนฉาก 5/6/8), ปรับ narrative
  `why_the_ten_doors_are_shut` เป็น SIXTH UPDATE (เหลือ 4 ฉากที่ยังปิด: 7, 9, 11, 130)
- mechanical fallout ใน `tools/pf_runtimeres_actor_entry_static.py` (SRC_ACTOR_ENTRY_SITES
  22→23, SRC_ACTOR_STREAM_SITES 31→32, SRC_MODULES_WITH_ACTOR_ENTRY 21→22), re-pin ใน
  `tests/test_runtimeres_actor_entry_static.py` และใน
  `reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md`

## เทสที่เพิ่ม/แก้

- `tests/test_world_bg0003_identity.py` (ใหม่), `tests/test_world_population_bg0003.py` (ใหม่)
- `tests/test_lane_a_scene_census.py`: เพิ่ม `SpiceParadiseRegistrationTests`
- เก้าไฟล์ admissible-scene-ids widened เป็นฉาก 3: `test_gm_login_scene_admission.py`,
  `test_gm_login_scene_override_position_resync.py`, `test_gm_login_scene_registry_snapshot.py`,
  `test_gm_login_scene_sanctioned_barred.py`, `test_gm_login_scene_stage.py`,
  `test_world_faction_admission.py`, `test_world_scene_marker.py`,
  `test_world_scene_registry_rule_1_scenes.py`, `test_gm_login_scene_consume_cause.py`

### ผลกระทบที่ pf-adversary self-review จับได้ (ไม่ใช่แค่ 8 ไฟล์ตามแบบรอบ p4wire)

การเปิดฉาก 3 ทำให้ `world_faction_admission.admits(3)` เป็น True (เพราะ `login_entry_allowed`
AND `n_SAVE==1`) ซึ่งกระทบ `player_wire.make_actor_attr_with_name_class_and_faction`'s scene
guard ด้วย — สามไฟล์ที่ hardcode ฉาก 3 เป็นตัวอย่าง "refused/unaccepted scene" พังตอนรัน full
suite และถูกย้ายไปฉาก 7 (Voodoo Island, ยังปิดอยู่) แทน: `tests/test_player_hostile_pairing.py`,
`tests/test_player_wire_probe_base1.py`, และ `tests/test_gm_login_scene_admission.py`'s
`NAMED_BUT_UNPINNED` constant. เช่นเดียวกับ `BARRED_ON_DISK` ใน
`test_gm_login_scene_registry_snapshot.py` และ `SHUT_AT_LOGIN` ใน
`test_world_faction_admission.py` ที่ต้องย้ายจากฉาก 3 ไปฉาก 7 ด้วยเหตุผลเดียวกัน — ค้นพบด้วยการ
รัน full suite แทนที่จะเชื่อว่า 8 ไฟล์ตามรูปแบบรอบก่อนคือขอบเขตที่สมบูรณ์

## ตัวเลขที่วัดได้

- assembled 62 shippable placements / 72 native placements (10 unshippable: 1 no-MOBS-row +
  9 no-s_OUTFIT)
- 41 resolved Mob-Set identities / 10 unresolved / 51 total (CLINE type 3's ทั้งช่วง key)
- 9 multi-variant outfit sets, ครอบคลุม 25 ของ 62 shippable placements
- full suite ก่อน commit: **5920 passed, 327 skipped, 11910 subtests passed, 0 failed**
  (เทียบกับ 5878/323/11573 ก่อนรอบนี้ — เพิ่ม 42 test methods ใหม่จากไฟล์ที่เพิ่ม/แก้ทั้งหมด)

## ยังไม่ได้พิสูจน์

- ไม่มีมนุษย์ยืนในฉากนี้มาก่อนในโปรเจกต์นี้ (`status` เดิม: `never_sent_to_any_client_by_this_project`)
  จุดเกิด `MARKER[3]` ยังเป็นชั้นหลักฐาน `authored` เท่านั้น ห่างจาก placement ที่ใกล้ที่สุด 405.0
  หน่วย (นอกขอบเขต placement) — ต้องรอ attended round ยืนดูจริง
- ticket สาย C: เปิด GT ใหม่ใน `pf_bridge/GAME_TEST_QUEUE.md` (ดูจดหมายแยก)

## ขอบเขตที่ไม่แตะ

`runtime.py`, `app.py`, `current/pf_login_game_server_v141.py` — ไม่แตะเลย

## CORE-REQUEST

ไม่มี (ไม่มีอะไรต้องแก้ใน runtime.py/app.py รอบนี้)
