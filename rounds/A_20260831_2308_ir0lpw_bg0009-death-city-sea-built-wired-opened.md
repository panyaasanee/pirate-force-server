# LANE-A round `ir0lpw`, 2026-08-31T23:08+07:00

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

บัญชี GM ที่ staged ไปฉาก 9 (Bg0009, Death City Sea) หรือใช้ `/warp 9` แล้วล็อกอิน จะไม่โดนปฏิเสธที่หน้า
login อีกต่อไป และจะเห็นตัวละคร/มอนสเตอร์ 57 ตัว (จาก 63 placement จริงของฉาก) ยืนอยู่ในเมือง แทนที่จะ
เป็นฉากว่างเปล่าหรือการปฏิเสธล็อกอิน

## เหตุการณ์พิเศษของรอบนี้: ชนกับรอบคู่ขนาน แล้วทิ้งงานทั้งหมดหนึ่งครั้ง

รอบนี้จองฉาก 7 (Bg0007, Voodoo Island) ไว้ก่อน (`pf_bridge/notes_to_chief/20260831_2033_CLAIM-LANE-A-...`)
และให้ pf-builder สร้าง+ผูก+เปิดจนเสร็จ ผ่าน pf-adversary (PASS) แล้ว -- แต่ระหว่างเตรียม merge พบว่ารอบ
คู่ขนาน `78zayw` (สาย A เช่นกัน) ทำงานเดียวกันเป๊ะและ merge เข้า main ไปก่อนแล้ว (server PR #417, bridge
PR #636, ใช้ GT-176 ตัวเดียวกันด้วย) ตรวจพบตอน `git merge origin/main` เจอ conflict แบบ add/add บนไฟล์ใหม่
ทั้งคู่ ตัดสินใจทิ้งงานฉาก 7 ทั้งหมด (`git reset --hard origin/main`, ไม่ reconcile เพราะไม่มีส่วนต่างที่
salvage ได้) แล้วจองฉาก 9 แทน (`pf_bridge/notes_to_chief/20260831_2214_CLAIM-LANE-A-round-ir0lpw-bg0009-...`)
รายละเอียดเต็มอยู่ในใบจองฉาก 9 นั้น housekeeping ของ p4wire/p7wm17 ที่รอบนี้เคยทำก็ชนกับรอบ chief `gdawub`
ที่ทำไปแล้วเช่นกัน ทิ้งเช่นกัน ไม่ push ซ้ำ

ผลข้างเคียงหนึ่งอย่าง: PR ของ bridge repo รอบนี้ (#629) ถูก reaper ของ repo ปิดอัตโนมัติระหว่างที่ branch
ยังชี้ไปที่ commit เก่า (ก่อน force-push แก้ไข) เพราะ mergeable=false ชั่วคราว -- เปิด PR ใหม่ (#637) แทน
บน branch เดิม (เนื้อหาถูกต้องแล้ว) ตามที่ reaper's comment สั่งไว้เอง

## สิ่งที่สร้าง (ฉาก 9 จริง)

- `src/pirateforce_foundation/world_bg0009_identity.py` (ใหม่) — crosswalk ของ CLINE type 9: 38
  resolved / 6 unresolved จาก 44 Mob-Set numbers ที่ฉากใช้จริง (CLINE type 9 เต็มมี 48 คีย์ แต่ฉากนี้ใช้
  เพียง 44 -- ครั้งแรกที่ไม่ใช่ full range เหมือนฉากก่อนหน้า) ไม่มี CJK-name drop, มี 11 sets multi-variant
  outfit (ทั้งหมด 2-variant), ครอบคลุม 30/57 shippable placements
- `src/pirateforce_foundation/world_population_bg0009.py` (ใหม่) — census composer, 57/63 shippable
  placements, ไม่มี faction bit
- wiring จุดเดียวกับฉากก่อนหน้าทุกจุด (CENSUS_SOURCES, ROSTER_COMPOSERS, lane_hooks console reader,
  mob_scene_recompose)
- `scenarios/world_scene_registry_001.json` แถว n_id=9: `login_entry_allowed: true` + safety-case
  narrative D1/D2/D3 ปรับ narrative เป็น EIGHTH UPDATE (เหลือ 2 ฉากปิด: 11, 130)
- mechanical fallout ใน `tools/pf_runtimeres_actor_entry_static.py` (25→26, 34→35, 24→25) + report + test

## เทสที่เพิ่ม/แก้

- `tests/test_world_bg0009_identity.py`, `tests/test_world_population_bg0009.py` (ใหม่)
- `tests/test_lane_a_scene_census.py`: เพิ่ม registration tests
- ย้าย hardcode "ฉาก 9 = refused example" ไปฉาก 11 (Deep Sea Temple floor 2, ยังปิดอยู่): 6 ไฟล์
  (`test_gm_login_scene_admission.py`, `test_gm_login_scene_consume_cause.py`,
  `test_gm_login_scene_registry_snapshot.py`, `test_player_hostile_pairing.py`,
  `test_player_wire_probe_base1.py`, `test_world_faction_admission.py`)
- widen admissible-today lists ให้รวมฉาก 9: `test_gm_login_scene_stage.py`,
  `test_gm_login_scene_sanctioned_barred.py`, `test_gm_login_scene_override_position_resync.py`,
  `test_world_scene_marker.py`, `test_world_scene_registry_rule_1_scenes.py`, `test_world_faction_admission.py`

## pf-adversary review ก่อน commit

PASS หลังแก้หนึ่งจุด: pf-adversary ตรวจ join CLINE/MOBS จริงเอง (byte-exact 38 resolved rows + 63
placement rows ตรงตาราง), รัน `build_bg0009_population()` ผ่าน legacy bridge จริงเห็น console line
`WORLD_CENSUS_BG0009 assembled=57/63` เอง, รัน full suite เองยืนยัน 5946/383/12751/0, และคำนวณระยะ
marker ซ้ำเอง (2198.81 หน่วย -- กว้างที่สุดในบรรดาประตูที่เลนนี้เปิดมา) — **พบจุดต้องแก้ก่อน commit จริง
หนึ่งจุด (HIGH):** registry/report อ้างว่า "a GAME_TEST_QUEUE.md ticket is opened this round in
pf_bridge" แต่ตอนตรวจยังไม่มีไฟล์ตั๋วจริงในฝั่ง bridge (มีแค่ใบ CLAIM) — แก้แล้วโดยเปิด GT-177 จริงและ
อ้างอิงเลขที่ถูกต้องในทั้งสองไฟล์ พบจุดเล็กอีกสองจุด (LOW, ไม่กระทบผลเทส): `world_bg0009_identity.py`
docstring นับ "seven occurrences" ของ MOBS-has-no-row family ผิด (ที่ถูกคือแปด, แก้แล้ว) และสลับ
denominator "30 of the 44 shippable" ผิด (ที่ถูกคือ 57, แก้แล้ว)

## ตัวเลขที่วัดได้

- assembled 57 shippable placements / 63 native placements (6 unshippable: 1 no-MOBS-row + 5 no-s_OUTFIT)
- 38 resolved Mob-Set identities / 6 unresolved / 44 total ที่ฉากใช้จริง (CLINE type 9 มี 48 คีย์เต็ม
  แต่ 4 คีย์ไม่ถูกใช้: 38, 39, 40, 106)
- 11 multi-variant outfit sets (ทั้งหมด 2-variant), ครอบคลุม 30 ของ 57 shippable placements
- discrepancy: native_definition_count ของ registry (44) ตรงกับจำนวนที่ฉากใช้จริงพอดี -- ครั้งแรกที่ไม่
  ต่างกัน (ต่างจากฉาก 3/4/6/7/8 ที่ต่าง ±1) บันทึกไว้ตรงๆ
- full suite: pf-adversary รันซ้ำยืนยัน **5946 passed, 383 skipped, 12751 subtests passed, 0 failed**
  (เทียบกับ 5912/383/12379 ก่อนรอบนี้)

## ยังไม่ได้พิสูจน์

- ไม่มีมนุษย์ยืนในฉากนี้มาก่อน จุดเกิด MARKER[9] ห่างจาก placement ที่ใกล้ที่สุด **2198.81 หน่วย** -- กว้าง
  ที่สุดในบรรดาประตูที่เลนนี้เปิดมา (ยังอยู่ในขอบเขต placement ตามทะเบียน แต่กว้างกว่ามาก) — GT-177 เปิดแล้ว
  ใน pf_bridge/GAME_TEST_QUEUE.md ขอให้ผู้เทสรายงานจุดนี้เป็นพิเศษ

## ขอบเขตที่ไม่แตะ

`runtime.py`, `app.py`, `current/pf_login_game_server_v141.py` — ไม่แตะเลย (pf-adversary ยืนยัน)

## CORE-REQUEST

ไม่มี

## เปิดใบให้สาย C

ไม่มี

-- LANE-A (WORLD) round `ir0lpw`
