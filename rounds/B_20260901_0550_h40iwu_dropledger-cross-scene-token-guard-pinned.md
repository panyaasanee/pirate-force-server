# LANE-B round `h40iwu` (COMBAT)

เปิดรอบ 2026-09-01T05:35+07:00 (round claim), เนื้อรอบเขียน 2026-09-01T05:50+07:00 (scheduled,
ไม่มีคนเฝ้าหน้าจอ)
Branch: `claude/determined-brown-h40iwu` (repo นี้), `claude/wonderful-gauss-h40iwu` (pf_bridge)
Draft PR ที่ถืออยู่: `pirate-force-server#443`, `pf_bridge#670`

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้ไม่แตะ `runtime.py`/`app.py`/`field_mobs._SCENE_TABLE_MODULES` เลย -- เป็นรอบเทส
เชิงป้องกัน (technical debt ตามกฎ F ของ CHARTER) ไม่ใช่รอบสร้างของที่ผู้เล่นเห็นบนจอ

## ทำไมรอบนี้ไม่ว่าง (ตามกฎ "ห้ามรอบสถานะเปล่าติดกันเกิน 1 รอบ")

รอบก่อน (`n8kq4r`) ไม่ว่างอยู่แล้ว (ปิด AI table gate จริง) จึงไม่ติดเงื่อนไขนี้อยู่ก่อนแล้ว แต่รอบนี้ก็หา
ของจริงมาทำ ไม่ใช่แค่ mailbox hygiene เปล่า ๆ

## ขั้น B (มือจดหมาย) -- ตรวจ HEAD สดก่อนเริ่ม

`ADDRESSEE: LANE-B` ที่ยังไม่มี `.CONSUMED.txt` ที่พบจริง 1 ใบ:
`20260901_0507_CHIEF-REPLY-CORE-REQUEST-heartbeat-preserve-wired.md` -- chief ยืนยัน P-1
(ground-heartbeat preserve) เดินสายแล้วผ่าน `install_ground_heartbeat_preserve(legacy)` (ไม่ใช่ blanket
patch ตามร่างแรก -- แก้ตาม pf-adversary รอบ `6o3gr1`), full suite ฝั่ง `pirate-force-server` ที่ chief วัด
6137 passed/0 failed, `GT-188` เปิดรอผู้เทส attended ยืนยันบนจอจริง บันทึกรับทราบ -- ไม่มีงานให้ LANE-B
ทำต่อจากใบนี้ สร้าง stub + ย้าย consumed แล้ว

`20260901_0444_COO-DECISION-attr-wire-raw-block-proceed-path0-defer-1-vs-2.md` -- ตรวจแล้ว ADDRESSEE
คือ `LANE-GM` ไม่ cc มาที่ `LANE-B` เลย ข้ามไม่ consume (ไม่ใช่ของสาย B)

จดหมาย STATUS สี่ฉบับที่สาย B เปิดเองรอบก่อน (`2341`/`0106`/`0235`/`0400`) เป็นจดหมายขาออก ไม่ใช่ใบ
เข้าที่ต้องมี stub -- ตรวจเนื้อหากับ HEAD สดแล้วยังตรงทุกข้อ (gate 1/2/3/4 ของ Bg0015 ยังปิดเหมือนเดิม
ไม่มีคำตอบใหม่จาก COO/เจ้าของเรื่อง "ใครเป็นเจ้าของประตูไหน" ตั้งแต่ใบ `0243`)

## ขั้นเลือกงาน -- ตรวจซ้ำว่ามีพื้นผิว player-visible ใหม่ไหมก่อนถอยไปทำเทส

ไล่ทุกเส้นทางที่ `62o506`/`6cm6ry`/`n8kq4r` วางไว้ซ้ำที่ HEAD วันนี้ (ไม่เชื่อใบเก่า):

- `field_mobs._SCENE_TABLE_MODULES`: ยังไม่มี Bg0015 -- gate 1 ยังปิด, ยังไม่มีใครมอบหมายเจ้าของประตู 2/3
  (`grep -n "_SCENE_TABLE_MODULES = {" src/pirateforce_foundation/field_mobs.py` -> บรรทัด 475 มีแค่
  bg0001/Bg0002 สองคีย์)
- `mob_death.templates_without_a_death_ruling()` (gate 3, owner-only): ยังไม่ตรวจซ้ำเพราะ gate 1 ยังไม่
  เปิด ไม่มีเหตุผลใหม่ให้เจ้าของออก ruling ก่อนกำหนด
- `mob_scene_recompose.declared_without_composer()` (gate 4): ฉาก 14 ยังอยู่ใน
  `ACKNOWLEDGED_WITHOUT_COMPOSER` ตามที่ออกแบบไว้ (คอมโพสเซอร์ผูกกับรอบที่ roster แถวแรกลงจอด ไม่ใช่
  งานที่แยกทำก่อนได้อย่างมีความหมาย -- ลองแล้วพบว่าการสร้างคอมโพสเซอร์เปล่าไม่มี real data ให้ทดสอบตามที่
  `62o506` บันทึกไว้ ไม่ทำซ้ำ)
- `mob_pickup_persist`: ยังบล็อกด้วย `COO-DECISION 20260901_0245` (รอ `GT-124` capture opcode จริง) --
  `GAME_TEST_QUEUE.md`'s `GT-146`/`GT-124` ยังเป็น PENDING/BLOCKED-ON-WIRING เหมือนเดิม
- `mob_aggro.ATTACK_INTENT_DELIVERABLE`: ยัง `False` (Door B ยังไม่เปิด, ต้องรอ capture หลักฐานจาก RE)

ไม่มีเส้นไหนเปิดใหม่ตั้งแต่รอบ `n8kq4r` -- ยึดกฎ F: ทำเทสที่มีค่าจริงแทน

## สิ่งที่ทำ -- ปักช่องโหว่ที่ตัวเองบันทึกไว้แต่ไม่เคยมีเทสกันไว้ (`mob_loot.DropLedger.looted`)

จดหมาย `20260901_0106` ("ของแถมที่ต้องบันทึก") ชี้ไว้แล้วแต่ไม่เคยแปลงเป็นเทส: `DropLedger.looted` เก็บ
เป็น `(actor_identity, kill_token)` **ไม่มี scene term เลย** ที่ยังปลอดภัยวันนี้เพราะสองข้อเท็จจริงเท่านั้น
(1) `kill_token = death_step.register.generation` นับขึ้นทางเดียวข้ามฉากทั้งหมด ไม่เคยรีเซ็ต (2)
`field_mobs.cross_scene_identity_collisions()` ไม่รายงานการชนที่ยัง live วันนี้ (Bg0002 x Bg0015 ชนกันที่
placement 87 จริง แต่ Bg0015 ยังไม่ลงทะเบียนเป็นฉาก live) -- ถ้าข้อใดข้อหนึ่งเปลี่ยนวันหน้า (token ถูกทำ
per-scene, หรือฉากที่สองชนกับ identity ที่ live อยู่แล้ว) การฆ่าซ้ำ identity เดิมในฉากใหม่จะถูกปฏิเสธผิด ๆ
เป็น `mob_already_looted`

รอบนี้:
1. เติมคอมเมนต์ที่ฟิลด์ `DropLedger.looted` เอง (ไม่ใช่แค่ในจดหมาย) อธิบายสองข้อเท็จจริงที่พึ่งอยู่และชี้ไป
   เทสที่ปักไว้
2. เพิ่มเทสใหม่ `test_a_kill_token_that_moves_backward_for_the_same_identity_is_refused_the_same_way_a_
   replay_is` ใน `tests/test_mob_loot.py` -- ปักขอบเขตจริงของ guard (`previous >= kill_token` ไม่ใช่
   `previous == kill_token`) ที่ไม่มีเทสไหนในไฟล์นี้เคยแยกสองแบบออกจากกันมาก่อน (ทุกเทสเดิมใช้แค่
   token เดิมซ้ำ หรือ token สูงขึ้น ไม่เคยลองให้ token ต่ำลง)
3. **พิสูจน์ว่าเทสตรวจของจริง (ไม่ใช่เขียวเฉย ๆ)**: mutate `mob_loot.py`'s guard จาก `previous >=
   kill_token` เป็น `previous == kill_token` ชั่วคราว รันเทสใหม่ -> **แดง** (`AssertionError:
   MobLootContractError not raised`) แล้ว revert กลับของเดิมเป๊ะ (`git diff` ว่างก่อน commit)

## หมายเหตุกระบวนการ -- pf-adversary

session นี้ไม่มีเครื่องมือ/agent สำหรับเรียก pf-adversary แยกต่างหาก (ไม่มี Task/agent-launch tool ใน
tool list ของ session) แทนที่จะข้ามขั้นนี้เงียบ ๆ ทำสิ่งที่ pf-adversary ทำเป็นประจำด้วยมือเอง: (ก)
mutation-proof ข้างบน (ข) อ่าน `git diff` ทุก hunk ก่อน commit (ค) ตรวจ error string/ค่าคาดหวังทุกบรรทัด
ของเทสใหม่กับโค้ดจริงทีละบรรทัดก่อนรัน -- บันทึกไว้ตรงนี้เพื่อให้ตรวจสอบย้อนหลังได้ว่าไม่ได้ข้ามขั้นแบบ
ไม่มีใครรู้

## เทส

```
เฉพาะไฟล์ที่แก้: tests/test_mob_loot.py -> 97 passed, 12 subtests passed (0.50s)
mutation-proof: guard == แทน >= -> เทสใหม่แดง 1 ใบ (AssertionError) -> revert -> เขียวหมดอีกครั้ง
สวีตเต็มก่อนแก้ (HEAD เดิม): 6149 passed, 327 skipped, 13142 subtests passed, 0 failed (148.48s)
สวีตเต็มหลังแก้: 6150 passed, 327 skipped, 13142 subtests passed, 0 failed (143.11s)
เดลต้า: +1 passed ตรงกับ 1 เทสใหม่เป๊ะ, +0 subtests (เทสนี้ไม่ใช้ subTest), 0 failed, 0 skipped เปลี่ยน
git diff --check: silent
```

`tools/verify_hypothesis_ledger.py` / `tools/verify_functional_coverage.py`: ไม่รันรอบนี้ -- ไม่ได้แตะ
ไฟล์ pin/digest/ledger/checksum/GRADE_SUBSET หรือ `tests/test_foundation_legacy_seam.py` เลย (เงื่อนไข
ที่บังคับให้รันสองคำสั่งนี้ไม่เข้าเงื่อนไขรอบนี้)

## ตัวเลขที่วัดได้

```
ไฟล์ที่แตะ (pirate-force-server) รวม 3:
  src/pirateforce_foundation/mob_loot.py   [เพิ่มคอมเมนต์ที่ฟิลด์ looted เท่านั้น ไม่แก้โค้ดทำงาน]
  tests/test_mob_loot.py                    [เพิ่ม 1 เทสใหม่]
  rounds/B_20260901_0550_h40iwu_dropledger-cross-scene-token-guard-pinned.md [ไฟล์นี้]
เทสใหม่: 1 ใบ (test_a_kill_token_that_moves_backward_for_the_same_identity_is_refused_the_same_way_a_replay_is)
```

`current/pf_login_game_server_v141.py`: ไม่แตะ · canonical DB/capture corpus: ไม่แตะ ·
`runtime.py`/`app.py`: ไม่แตะ · `field_mobs._SCENE_TABLE_MODULES`: ไม่แตะ (gate 1 ยังปิด) ·
`scenarios/world_*.json` (เขตสาย A): ไม่แตะ

## ยังไม่ได้พิสูจน์

- เทสนี้ปักพฤติกรรม**ปัจจุบัน**ไว้เท่านั้น ไม่ได้แก้ปัญหา scene term ที่ยังไม่มีจริง -- ถ้า gate 1 ของ
  Bg0015 เปิดวันหนึ่งพร้อมกับที่ token หรือ identity range เปลี่ยนไปจากวันนี้ ต้องกลับมาดูโมดูลนี้ใหม่
- gate 1/2/3/4 ของ Bg0015 ทั้งสี่ตัวยังปิดเหมือนเดิมทุกประการ (ไม่มีอะไรเปลี่ยนจากใบ `n8kq4r`)
- ทุกอย่างที่รอบก่อนหน้ายกไว้ (color mapping RE-067/RE-155, pickup opcode RE-125/GT-124, drop label
  re-emission, KA1B ①/③) -- ไม่มีข้อไหนขยับรอบนี้เช่นกัน

## CORE-REQUEST

ไม่มี (รอบนี้ไม่แตะ `runtime.py`/`app.py`)

## เปิดใบให้สาย C

ไม่มี

-- LANE-B (COMBAT) รอบ `h40iwu`
