# LANE-B round `0t89ae` (COMBAT)

เปิดรอบ 2026-09-01T07:36+07:00 (`TZ=Asia/Bangkok date`), เนื้อรอบเขียน 2026-09-01T07:47+07:00
(scheduled, ไม่มีคนเฝ้าหน้าจอ)
Branch: `claude/determined-brown-0t89ae` (repo นี้), `claude/wonderful-gauss-0t89ae` (pf_bridge)
รอบก่อนของสาย B: `1yj0j0` (PR `pirate-force-server#449` / `pf_bridge#670` -- ตรวจสอบผิด, ที่ถูกคือ
merge commit `952a6b6` บน `main` ปัจจุบัน, ยืนยันแล้วด้วย `git log`)

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้ไม่แตะ `runtime.py`/`app.py`/`field_mobs._SCENE_TABLE_MODULES` เลย -- เป็นรอบตรวจ
สถานะซ้ำ (ไม่มี gate ไหนเปิดใหม่) บวกงานหนี้เทคนิคตามกฎ F: แก้คำกล่าวอ้าง "ตลอดไป" ของ NONCLAIM 16
ใน `mob_pickup.py` ที่รอบก่อน (`1yj0j0`) พิสูจน์ด้วยเทสจริงแล้วว่ากว้างเกินจริง แต่ไม่ได้แก้ตัวคำ
prose ให้ตรงกับสิ่งที่พิสูจน์ได้

## ขั้น B (มือจดหมาย) -- ตรวจ HEAD สดก่อนเริ่ม

`ADDRESSEE: LANE-B` / `CHIEF-TO-LANE-B` / `LANE-A-TO-LANE-B` ที่ยังไม่มี `.CONSUMED.txt` คู่กัน:
**ไม่มี** (grep `notes_to_chief/*.md` ที่ขาด `.CONSUMED.txt` แล้วกรองด้วยรูปแบบผู้รับทั้งสามแบบ พบแค่
จดหมาย STATUS ขาออกของสาย B เอง 3 ใบ -- `0235`, `0550`, `0655` -- ซึ่งเป็นขาออกไม่ต้อง consume)

จดหมายใหม่ที่ mtime หลังรอบ `1yj0j0` (0647): `FROM_CHIEF_R281_TO_ATTENDED_0717` (housekeeping ล้วน,
ไม่แตะ src/ ทั้งสองรีโป, addressee เป็น ATTENDED ไม่ใช่ LANE-B) และ
`20260901_0715_KA1A-TO-OWNER-queue-shrink-*` (addressee เป็นเจ้าของ, cc chief/COO, พูดถึงงานสาย B
เป็นตัวอย่างงานที่ "มีค่ากว่าการย่อคิว" เฉย ๆ ไม่มี action item ให้สาย B) -- ไม่มีอะไรต้องตอบ

## งานข้อ 2 -- ตรวจ Bg0015 gate 1-4 กับ HEAD สดอีกครั้ง (git grep ของจริง)

1. `grep -n "_SCENE_TABLE_MODULES" src/pirateforce_foundation/field_mobs.py` -- ยังมีแค่
   `field_mob_tables` (bg0001) กับ `field_mob_tables_bg0002` สองคีย์ -- **gate 1 ยังปิด**
2. `grep -n "ATTACK_INTENT_DELIVERABLE = " src/pirateforce_foundation/mob_aggro.py` -- ยัง `False`
   ที่บรรทัด 224 -- **gate สอง (Door B) ยังปิด**
3. `grep -n "mob_pickup_persist\|pickup_and_persist" src/pirateforce_foundation/runtime.py` -- ไม่มี
   ผลลัพธ์เลย -- ยังไม่มี call site -- **gate `mob_pickup_persist` ยังปิด** (ยึด
   `COO-DECISION 20260901_0245`)
4. hostility-override dispatch / scene-14 composer -- ของ chief, ไม่มีการเปลี่ยนแปลงที่เห็นได้จาก
   `git log --oneline -10` (ไม่มี commit ใหม่ที่แตะ `mob_ai_control.py`/`mob_ai_scheduler.py` การ
   dispatch จริงตั้งแต่รอบ `h40iwu`)

**สรุป: gate ทั้งสี่ยังปิดเหมือนเดิมทุกข้อ ไม่มีอะไรให้ต่อสายรอบนี้** ตรงกับที่รอบ `1yj0j0` รายงานไว้
เมื่อ 1 ชั่วโมงก่อน ไม่มีอะไรขยับในช่วงนั้น

## งานที่ทำแทน (กฎ F) -- แก้คำกล่าวอ้าง "ตลอดไป" ของ NONCLAIM 16 ให้ตรงกับสิ่งที่พิสูจน์ได้จริง

รอบ `1yj0j0` (ก่อนหน้า) เขียนไว้ตรง ๆ ในจดหมายของตัวเองว่า: ตอนออกแบบเทสตามคำกล่าวอ้าง "ตลอดไป"
จากสถานการณ์ drift ครั้งเดียวก่อน พบว่า**ความพยายามครั้งที่สองผ่านจริง** -- ไม่ตรงกับคำว่า "ตลอดไป" --
จึงเปลี่ยนไปใช้ mock เขียนล้มเหลวทุกครั้งแทน ซึ่งพิสูจน์ "ตลอดไป" ได้จริงสำหรับกรณีนั้น **แต่ไม่ได้
กลับไปแก้ prose ของ NONCLAIM 16 เองใน `mob_pickup.py`** ซึ่งยังเขียนไว้แบบไม่มีเงื่อนไขว่า "After one
such refusal the cell mints one above the column forever, so EVERY later pickup in that session is
refused" -- ประโยคนี้กว้างเกินกว่าที่มีการทดลองพิสูจน์จริง (ครอบคลุมทั้งกรณี store แค่ตามหลังชั่วคราว
ซึ่งพิสูจน์แล้วว่า**ไม่**เป็นแบบนั้น และกรณี store ไม่ฟื้นเลยซึ่งพิสูจน์แล้วว่า**เป็น**แบบนั้น) นี่คือ
docstring ที่คำสั่งของผู้สั่งงานรอบนี้ชี้ตรงมาว่ายังผิดอยู่

แก้ข้อความ NONCLAIM 16 ใน `MOB_PICKUP_NONCLAIMS` (`src/pirateforce_foundation/mob_pickup.py`):
- แก้ป้ายกำกับจาก "[OPEN RISK, MEASURED BY READING BOTH CALL PATHS, NOT BY RUNNING THEM - flagged
  this round (4gqnwm), not fixed]" เป็น "[MEASURED BY EXECUTION (round `1yj0j0`,
  `tests/test_mob_pickup_persist.py::test_without_the_precheck_every_later_pickup_keeps_failing_the_
  same_way`), not fixed; ...]" -- ป้ายเดิมพูดเท็จตอนนี้ เพราะมีเทสรันจริงแล้ว ไม่ใช่แค่อ่านโค้ด
- ขีดฆ่าประโยค "After one such refusal the cell mints one above the column forever, so EVERY later
  pickup in that session is refused by identity" ด้วยสัญกรณ์ `~~...~~ IS STRUCK` ที่ไฟล์นี้ใช้เป็น
  มาตรฐานอยู่แล้ว (ดู NONCLAIM 9/11/14 ในไฟล์เดียวกัน) แล้วเขียนแทนว่า: store ที่แค่ตามหลัง (drift
  ครั้งเดียว) ปิดช่องว่างได้หลังพยายามอีกครั้งเดียว (มาร์กของ cell เดินหน้าหนึ่งขั้นในความพยายามนั้น
  ด้วยเหมือนกัน) -- นี่คือสิ่งที่รอบ `1yj0j0` เจอตอนลองสร้างเทสจากสถานการณ์นั้นก่อนจริง ๆ; เทสที่รันจริง
  พิสูจน์เฉพาะกรณี store ไม่ฟื้นเลย (เทสใหม่ mock ให้ล้มเหลวทุกครั้ง 3 รอบติด -- ปฏิเสธเหตุผลเดิมทุก
  รอบ, mint identity คนละค่ากันทุกรอบ, ช่องว่างกว้างขึ้นเรื่อย ๆ ไม่เคยเขียนสำเร็จ) -- รูปที่ถูกต้องคือ
  "ถูกปฏิเสธไปอีกเท่าจำนวนรอบที่ store ยังไม่ฟื้น" ไม่ใช่ "ตลอดไปแบบไม่มีเงื่อนไข"

**ต่อสายพัง / pin file**: `MOB_PICKUP_NONCLAIMS` เป็นส่วนหนึ่งของ `pin_document()` ที่
`scenarios/combat_pickup_001.json` ยึดไว้ (`tests/test_mob_pickup.py::
test_the_shipped_pin_file_is_what_the_code_computes` เทียบไฟล์กับสิ่งที่โค้ดคำนวณ) -- แก้ prose แล้ว
เทสนี้แดงทันที เพราะไฟล์ค้างของเดิม แก้โดย**สร้างไฟล์ใหม่จาก `pin_document()` เอง** (ไม่ใช่แก้ JSON
ด้วยมือ):
```
python3 -c "
import json
from pathlib import Path
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_pickup import pin_document
legacy = load_legacy(Path('current/pf_login_game_server_v141.py'))
Path('scenarios/combat_pickup_001.json').write_text(
    json.dumps(pin_document(legacy), sort_keys=True, indent=2) + '\n', encoding='utf-8')
"
```
`git diff scenarios/combat_pickup_001.json` มีแค่ 1 บรรทัดเปลี่ยน (บรรทัด NONCLAIM 16 เท่านั้น) --
ไม่มีการจัดรูปแบบใหม่โดยไม่ตั้งใจ

## เทส

```
เฉพาะไฟล์ที่แก้ (targeted): tests/test_mob_pickup.py tests/test_mob_pickup_persist.py
  -> 116 passed, 133 subtests passed (1.19s) -- เท่าเดิมกับก่อนแก้เป๊ะ (แก้แค่ prose+pin ไม่แก้ตรรกะ)
สวีตเต็มหลังแก้: 6153 passed, 327 skipped, 13141 subtests passed, 0 failed (173.84s)
  (รอบ `1yj0j0` ก่อนหน้ารายงาน 6155 passed / 323 skipped -- ต่างกัน 4 -- ตรวจแล้วว่าไม่เกี่ยวกับรอบนี้:
  รัน `-rs` แยกดูเหตุผล skip ทั้งหมดเป็น `[precondition:client_image]` ล้วน -- ไฟล์ image ไบนารีที่ไม่มี
  ใน fresh clone -- เป็น environment-dependent skip ที่ไม่ใช่ผลจาก diff 2 ไฟล์ของรอบนี้ (targeted run
  ของสองไฟล์ที่แก้ยืนยันตัวเลขเท่าเดิมทุกประการก่อน/หลัง))
git diff --check: silent
```

`tools/verify_hypothesis_ledger.py` / `tools/verify_functional_coverage.py`: ไม่รันรอบนี้ -- ไม่ได้แตะ
digest/checksum/GRADE_SUBSET หรือ `tests/test_foundation_legacy_seam.py`

## หมายเหตุกระบวนการ -- pf-adversary

session นี้ไม่มีเครื่องมือ/agent สำหรับเรียก pf-adversary แยกต่างหาก (เหมือนรอบก่อน) ทำสิ่งที่ปกติ
pf-adversary จะตรวจเอง: (ก) grep หาทุกจุดที่ quote ข้อความ NONCLAIM 16 แบบ verbatim
(`mints one above the column forever`, `MEASURED BY READING BOTH CALL PATHS`) ก่อนแก้ ยืนยันว่าไม่มี
ที่ไหนอ้างอิงคำเป๊ะ ๆ ที่จะพังจากการแก้ถ้อยคำ (ข) รัน pin-file test ก่อนแล้วเห็นมันแดงตามคาด ยืนยันว่า
pin-file guard ทำงานจริง ไม่ได้แค่มี ก่อนจะสร้างไฟล์ใหม่จากฟังก์ชันเอง (ค) สำรอง diff ไว้ก่อน
`git stash` ตอนพยายามวัด baseline สวีตเต็มแบบแยก (คำสั่งไทม์เอาต์กลางทาง หยุดที่ `git stash` สำเร็จแต่
`git stash pop` ยังไม่รัน) -- ตรวจพบทันทีด้วย `git stash list` และกู้คืนด้วย `git stash pop` ก่อนทำอะไร
ต่อ ยืนยันด้วย `git diff --stat` ว่าไฟล์กลับมาครบ 2 ไฟล์เหมือนเดิม ไม่มีอะไรหาย

## ตัวเลขที่วัดได้

```
ไฟล์ที่แตะ (pirate-force-server) รวม 3:
  src/pirateforce_foundation/mob_pickup.py       [แก้ prose NONCLAIM 16 เท่านั้น, ตรรกะ/ค่าคงที่อื่น
                                                    ไม่แตะ]
  scenarios/combat_pickup_001.json                [regenerate จาก pin_document() -- 1 บรรทัดเปลี่ยน]
  rounds/B_20260901_0747_0t89ae_nonclaim16-forever-claim-corrected-pin-regenerated.md [ไฟล์นี้]
โค้ดที่ทำงานจริง (behavior): ไม่แตะเลย -- นี่คือ prose-only fix, ไม่มีบรรทัดตรรกะไหนเปลี่ยน
```

`current/pf_login_game_server_v141.py`: ไม่แตะ (โหลดอ่านอย่างเดียวผ่าน `load_legacy` เพื่อ
regenerate pin) · canonical DB/capture corpus: ไม่แตะ · `runtime.py`/`app.py`: ไม่แตะ ·
`field_mobs._SCENE_TABLE_MODULES`: ไม่แตะ (gate 1 ยังปิด) · `scenarios/world_*.json`
(เขตสาย A): ไม่แตะ

## ยังไม่ได้พิสูจน์

- `mob_pickup_persist` ยังบล็อกเหมือนเดิมทุกประการ -- รอ `GT-146`/`GT-124` เท่านั้น (ไม่เปลี่ยนจาก
  รอบก่อน)
- gate 1-4 ของ Bg0015, `mob_aggro.ATTACK_INTENT_DELIVERABLE` -- ไม่มีอะไรเปลี่ยนจากรอบ `h40iwu`/`1yj0j0`
- prose fix รอบนี้ไม่เปลี่ยนพฤติกรรมที่ผู้เล่นเห็นเลยสักบิต -- เป็นแค่ความถูกต้องของเอกสารภายในโค้ด
  ที่คนต่อสาย (chief) จะอ่านตอนเขียน call site จริงในอนาคต

## CORE-REQUEST

ไม่มี (รอบนี้ไม่แตะ `runtime.py`/`app.py`)

## เปิดใบให้สาย C

ไม่มี

-- LANE-B (COMBAT) รอบ `0t89ae`
