# LANE-B round `1yj0j0` (COMBAT)

เปิดรอบ 2026-09-01T06:35+07:00 (ตามที่ผู้สั่งงานแจ้ง), เนื้อรอบเขียน 2026-09-01T06:47+07:00
(scheduled, ไม่มีคนเฝ้าหน้าจอ)
Branch: `claude/determined-brown-1yj0j0` (repo นี้), `claude/wonderful-gauss-1yj0j0` (pf_bridge)
รอบก่อนของสาย B: `h40iwu` (PR `pirate-force-server#443` / `pf_bridge#670`, ทั้งคู่ merged แล้ว
ยืนยันด้วย `git log` ของ `main` ปัจจุบัน)

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้ไม่แตะ `runtime.py`/`app.py`/`field_mobs._SCENE_TABLE_MODULES` เลย — เป็นรอบตรวจ
สถานะ (งานข้อ 1 ของผู้สั่งงาน) บวกรอบเทสเชิงป้องกัน (กฎ F ของ CHARTER) หลังพบว่าทุกเส้นทางที่จะ
ทำให้ผู้เล่นเห็นของใหม่ยังบล็อกจริงเหมือนเดิม

## ขั้น B (มือจดหมาย) -- ตรวจ HEAD สดก่อนเริ่ม

`ADDRESSEE: LANE-B` ที่ยังไม่มี `.CONSUMED.txt`: **ไม่มี** (grep ทั้ง `notes_to_chief/*.md` ที่ขาด
`.CONSUMED.txt` คู่ ไม่พบใบที่ addressee เป็น LANE-B) จดหมาย STATUS ของสาย B เองรอบก่อน
(`20260901_0550_LANE-B-STATUS-dropledger-*`) เป็นขาออก ไม่ต้อง consume

## งานข้อ 1 -- ตรวจสถานะ `mob_pickup_persist` ตามที่สั่ง

อ่าน `src/pirateforce_foundation/mob_pickup_persist.py` เต็มไฟล์ + `mob_pickup.py` (THE WALL,
NONCLAIM 1/9/16) + จดหมายที่เกี่ยวข้องทั้งหมดใน `pf_bridge` (`grep -rl mob_pickup_persist
notes_to_chief/`):

1. `COO-DECISION 20260901_0145` (consumed) สั่งให้ต่อสาย `mob_pickup_persist.pickup_and_persist`
   เข้า `runtime.py` รอบนั้น
2. สาย B รอบ `p05wire` (ก่อนรอบนี้) ตรวจแล้วพบว่าคำสั่งนั้นขัดกับ `COO-DECISION 20260830_1145`
   (ผูก insertion point นี้กับ `GT-124`/capture opcode จริง ห้ามต่อสายผ่าน hypothesis-lane hack)
   เขียน `20260901_0230_LANE-B-ASK-COO-two-conflicting-decisions-*` ถามแทนเดา (ตาม CHARTER ข้อ ค)
3. `COO-DECISION 20260901_0245-pickup-wiring-stays-blocked-0145-corrected` (consumed) **แก้ไข
   `0145` อย่างเป็นทางการ**: ยึด `20260830_1145` เดิม ห้ามต่อสาย `pickup_and_persist` จนกว่า
   `GT-124` จะ capture opcode จริงจาก attended click — `0145` ข้อนี้ถูกยกเลิก

**ตรวจซ้ำที่ HEAD วันนี้ (ไม่เชื่อจดหมายเก่าเฉย ๆ):**
- `grep -rn "mob_pickup_persist" src/pirateforce_foundation/*.py` — ยังไม่มี caller ใน
  `runtime.py` (ไฟล์นั้นไม่มีในสาย B แก้ไม่ได้อยู่แล้ว, และเนื้อหาที่ตรวจผ่านการอ่านไฟล์ก็ไม่มี
  import ของโมดูลนี้)
- `GAME_TEST_QUEUE.md`: `GT-124` ยังเป็น `BLOCKED-ON-WIRING`, `GT-146` (ใบ capture opcode) ยังเป็น
  `PENDING` (ยังไม่ boot), `RE-125` ยังปิดแบบ `CLOSED BOUNDED-NEGATIVE` (ห้ามใช้ `0x4543` เป็น
  production opcode) — ยืนยันซ้ำล่าสุด 31 ส.ค. 23:22/23:29
- ไม่มีจดหมายใหม่ตั้งแต่ `0245` ที่แก้สถานะนี้อีก (ตรวจทุกไฟล์ที่ mtime ใหม่กว่ารอบ `h40iwu` ใน
  `notes_to_chief/` แล้ว ไม่มีใบไหนพูดถึง `GT-124`/`mob_pickup_persist`/`0x4543`)

**สรุป: ยังบล็อกด้วยเหตุผลเดิมทุกประการ — ไม่มีอะไรให้ต่อสายรอบนี้** COO-DECISION 0245 ปิดประเด็นนี้
ชัดเจนแล้ว ไม่ใช่คำถามเปิดอีกต่อไป จึงไม่ต้องเขียนใบ ASK-COO ซ้ำ

## งานข้อ 2/3 -- ไม่มีพื้นผิว player-visible ใหม่ -> ทำตามกฎ F

ไล่ทุกเส้นทางซ้ำที่ HEAD (ไม่เชื่อใบเก่า):
- `field_mobs._SCENE_TABLE_MODULES` (บรรทัด 475): ยังมีแค่ `bg0001`/`bg0002` สองคีย์ — ฉาก 14
  (Bg0015) ยังไม่ลงทะเบียน gate 1 ยังปิด (merge #444/#445 ของสาย A ไม่แตะบรรทัดนี้ ตรวจแล้ว)
- `mob_aggro.ATTACK_INTENT_DELIVERABLE` (บรรทัด 224): ยัง `False`
- `mob_pickup_persist`: ยังบล็อกตาม `COO-DECISION 20260901_0245` (ด้านบน)

ไม่มีเส้นไหนเปิดใหม่ตั้งแต่รอบ `h40iwu` — ยึดกฎ F: หา technical debt จริงที่มี concrete failure
scenario แทน ไม่ใช่แค่จดหมายว่าง

## สิ่งที่ทำ -- ปัก "forever" claim ของ `mob_pickup.py` NONCLAIM 16 เป็นเทสจริง

`mob_pickup.py` NONCLAIM 16 (เขียนไว้ตั้งแต่รอบ `4gqnwm`) อ้างว่า: ถ้าผู้เรียกข้าม precheck ของ
`mob_pickup_persist` (ใช้สูตรสองขั้นเดิมที่ `MOB_PICKUP_WIRING` เก็บไว้เป็นบันทึกเหตุผลเท่านั้น
ไม่ใช่สูตรที่ควรใช้จริง) แล้วการเขียนลง DB ล้มเหลวครั้งหนึ่ง **"ทุกการเก็บของถัดไปในเซสชันนั้นจะถูก
ปฏิเสธด้วยเหตุผล identity ตลอดไป — แต่ละครั้งก็เอาของออกจากพื้นไปแล้วด้วย"**

ตรวจแล้วพบว่า **ไม่มีเทสไหนพิสูจน์คำว่า "ตลอดไป" จริง** — เทสที่มีอยู่
(`test_without_the_precheck_the_same_drift_destroys_the_drop`) พิสูจน์แค่ครั้งเดียว และกรณีที่มัน
ใช้ (drift จาก stranger เขียนไปครั้งเดียวก่อนเก็บของ) มีช่องว่างพอดี 1 หน่วย ซึ่ง**ปิดตัวเองได้**หลัง
ความพยายามครั้งแรกล้มเหลว (ลองสร้างเทสตามสูตรนี้ก่อนจริง ๆ พบว่าความพยายามครั้งที่สองผ่านจริง ๆ
ไม่ตรงกับคำอ้าง "ตลอดไป" — ต้องออกแบบสถานการณ์ใหม่ที่ DB ไม่มีวันไล่ตามทัน)

เพิ่มเทสใหม่ `test_without_the_precheck_every_later_pickup_keeps_failing_the_same_way` ใน
`tests/test_mob_pickup_persist.py`: mock `store.commit_acquired_backpack_item` ให้ล้มเหลวทุกครั้ง
(`sqlite3.OperationalError`, แบบเดียวกับที่ `test_a_write_that_fails_after_the_take_is_named_and_
printed` ใช้) แล้ววนสูตรสองขั้น (ไม่มี precheck) 3 รอบติด — พิสูจน์ว่าทุกรอบ (ก) เอาของออกจากพื้น
สำเร็จ (ข) เขียน DB ล้มเหลวด้วยเหตุผลเดิมเป๊ะ (`REFUSE_WRITE_FAILED_AFTER_THE_TAKE`, cause เดิม)
(ค) mint identity คนละค่ากันทุกรอบ (เครื่องหมายในหน่วยความจำเดินหน้าเรื่อย ๆ ไม่มีวันหยุด) (ง) ไม่มี
แถวไหนถึงตารางจริงเลยสักแถว

**พิสูจน์ว่าเทสตรวจของจริง (mutation-proof)**: ลบบรรทัด `self._issued_through = item.identity` ใน
`mob_pickup.py::BagCell.commit_pickup` (บรรทัด ~1461) ชั่วคราว รันเทสใหม่ -> **แดง** (คนละ exception
เลย — `MobPickupContractError: identity_high_water_below_the_bag`, ไม่ใช่แค่ assertion ธรรมดา เพราะ
mark ที่ไม่เดินหน้าทำให้ ครั้งที่ 2 ของ loop ส่ง mark ต่ำกว่าที่ bag มีอยู่แล้ว) แล้ว revert กลับของเดิม
เป๊ะ (`git diff -- src/pirateforce_foundation/mob_pickup.py` ว่างก่อน commit — ตรวจด้วย `diff`
บรรทัดต่อบรรทัดกับสำเนาที่เก็บไว้ก่อนมิวเทต ไม่ใช่แค่เชื่อ `git diff`)

## หมายเหตุกระบวนการ -- pf-adversary

session นี้ไม่มีเครื่องมือ/agent สำหรับเรียก pf-adversary แยกต่างหาก ทำสิ่งที่ปกติ pf-adversary ทำเอง:
(ก) mutation-proof ข้างบน (ข) ตอนออกแบบเทสตัวแรก ลองสร้างจากสถานการณ์ "drift ครั้งเดียวจาก stranger"
ก่อน พบว่ามันไม่พิสูจน์ "ตลอดไป" จริง (ครั้งที่สองผ่าน) — บันทึกไว้เป็นเหตุผลว่าทำไมถึงเปลี่ยนไปใช้
mock แทน ไม่ใช่แค่ทิ้งของที่ผิดไปเงียบ ๆ (ค) อ่าน `git diff` ทุก hunk ก่อน commit

## เทส

```
เฉพาะไฟล์ที่แก้ (tests/test_mob_pickup_persist.py + tests/test_mob_pickup.py ที่เกี่ยวข้อง):
  tests/test_mob_pickup_persist.py tests/test_mob_pickup.py -> 116 passed, 133 subtests passed (1.14s)
  (ก่อนแก้: 115 passed ตามที่รอบ p05wire บันทึกไว้; เดลต้า +1 ตรงกับเทสใหม่ 1 ใบเป๊ะ)
mutation-proof: ลบการเดิน _issued_through -> เทสใหม่แดง 1 ใบ (MobPickupContractError ผิดชนิดไปเลย
ไม่ใช่แค่ assertion ล้ม) -> revert -> เขียวหมดอีกครั้ง (ยืนยันด้วย diff บรรทัดต่อบรรทัด)
สวีตเต็มหลังแก้ (HEAD รอบนี้): 6155 passed, 323 skipped, 13141 subtests passed, 0 failed (157.64s)
git diff --stat: เปลี่ยนไฟล์เดียว tests/test_mob_pickup_persist.py (+55 บรรทัด, เพิ่มเทส 1 ฟังก์ชัน
เท่านั้น ไม่มีบรรทัดอื่นถูกแก้) -> เดลต้าของสวีตเต็มคือ +1 passed เป๊ะ ไม่มี skip/failed เปลี่ยน
(baseline ก่อนแก้ = 6154 passed คำนวณจาก diff บวก ไม่ได้รันแยกเพราะรันเต็มใช้เวลา ~2.5 นาที/ครั้ง
และ diff เป็น pure-addition ที่ตรวจแล้วว่าไม่แตะเทสเดิมสักบรรทัด)
git diff --check: silent
```

`tools/verify_hypothesis_ledger.py` / `tools/verify_functional_coverage.py`: ไม่รันรอบนี้ — ไม่ได้
แตะไฟล์ pin/digest/ledger/checksum/GRADE_SUBSET หรือ `tests/test_foundation_legacy_seam.py`

## ตัวเลขที่วัดได้

```
ไฟล์ที่แตะ (pirate-force-server) รวม 2:
  tests/test_mob_pickup_persist.py  [เพิ่ม 1 เทสใหม่ (+55 บรรทัด), ไม่แก้เทสเดิม]
  rounds/B_20260901_0647_1yj0j0_pickup-persist-status-recheck-nonclaim16-forever-pinned.md [ไฟล์นี้]
เทสใหม่: 1 ใบ (test_without_the_precheck_every_later_pickup_keeps_failing_the_same_way)
มิวเทตชั่วคราวแล้ว revert (ไม่ commit): src/pirateforce_foundation/mob_pickup.py (1 บรรทัด, revert
สำเร็จ ยืนยันด้วย git diff ว่าง)
```

`current/pf_login_game_server_v141.py`: ไม่แตะ · canonical DB/capture corpus: ไม่แตะ ·
`runtime.py`/`app.py`: ไม่แตะ · `field_mobs._SCENE_TABLE_MODULES`: ไม่แตะ (gate 1 ยังปิด) ·
`scenarios/world_*.json` (เขตสาย A): ไม่แตะ · `mob_pickup.py`/`mob_pickup_persist.py`
(โค้ดทำงานจริง): ไม่แตะ (มิวเทตแค่ชั่วคราวเพื่อพิสูจน์เทส แล้ว revert หมด)

## ยังไม่ได้พิสูจน์

- เทสใหม่ปักพฤติกรรม**ปัจจุบัน**ของสูตรสองขั้นที่ไม่มีใครควรใช้จริง (`pickup_and_persist` ตัวเดียว
  คือสิ่งที่ `MOB_PICKUP_WIRING` แนะนำ) — ถ้าวันหนึ่ง `runtime.py` ถูกต่อสายผิดสูตร เทสนี้ช่วยยืนยัน
  ว่าอาการที่เจอ (เก็บของหายเรื่อย ๆ ทุกครั้งในเซสชันเดียวกัน) ตรงกับที่ NONCLAIM 16 ทำนายไว้จริง
  ไม่ใช่การป้องกันไม่ให้ต่อสายผิด — นั่นยังเป็นหน้าที่ของคนต่อสาย (chief) ที่ต้องอ่าน `MOB_PICKUP_
  WIRING` เอง
- `mob_pickup_persist` ยังบล็อกเหมือนเดิมทุกประการ — ไม่มีอะไรขยับตั้งแต่ `COO-DECISION 20260901_0245`
- gate 1-4 ของ Bg0015 ทั้งสี่ยังปิดเหมือนเดิม (ไม่มีอะไรเปลี่ยนจาก `h40iwu`)
- `mob_aggro.ATTACK_INTENT_DELIVERABLE` ยัง `False`

## CORE-REQUEST

ไม่มี (รอบนี้ไม่แตะ `runtime.py`/`app.py`)

## เปิดใบให้สาย C

ไม่มี

-- LANE-B (COMBAT) รอบ `1yj0j0`
