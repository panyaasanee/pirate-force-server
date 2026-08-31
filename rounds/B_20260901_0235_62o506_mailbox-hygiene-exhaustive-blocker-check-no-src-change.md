# LANE-B round `62o506` (COMBAT)

เปิดรอบ 2026-09-01T02:35+07:00 (scheduled, ไม่มีคนเฝ้าหน้าจอ)
Branch: `claude/determined-brown-62o506` (repo นี้), `claude/wonderful-gauss-62o506` (pf_bridge)
Draft PR ที่ถืออยู่: `pirate-force-server#431`, `pf_bridge#655`

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้ไม่แก้ `src/` เลยแม้แต่บรรทัดเดียว หลังตรวจสอบ BUILD-004/005/006 ทุกเส้นทางที่ยัง
เปิดอยู่จริงในสาย COMBAT วันนี้และพบว่า**ทุกเส้นทางถูกบล็อกด้วยการตัดสินใจที่ต้องรอ COO/เจ้าของ/สาย
RE โดยเฉพาะ ไม่ใช่ของที่สาย B ตัดสินเองได้** (รายละเอียดทีละเส้นข้างล่าง) แทนที่จะบังคับเขียนโค้ดที่ไม่
มีผลบนจอเพื่อให้มีอะไรให้ commit -- ตามกฎข้อ 3 ของ charter ("เขียนประโยคนี้ไม่ได้ ก็ไม่ใช่งานสาย A/B")
รอบนี้จึงเป็นรอบตรวจสอบ+ทำความสะอาดกล่องจดหมายแทน ไม่ใช่รอบสร้างของ

## ต้นรอบ -- อ่านของเดิมก่อน (ตามกฎ)

อ่าน `rounds/B_20260901_0106_6cm6ry_bg0015-combat-ledger-gap-measured.md` (ล่าสุดใน repo นี้),
`pf_bridge/rounds/B_20260901_0210_p05wire.md` (รอบก่อนหน้าจริง -- ไม่มีคู่ในฝั่งนี้ ดูหมายเหตุท้าย
ไฟล์), และจดหมายที่เกี่ยวข้องทั้งหมดใน `pf_bridge/notes_to_chief/` ย้อนไปถึง PANYA-ORDER
2026-09-01T02:15 ล่าสุด

ยืนยันสด: `lane_hooks.lane_b_mob_ai_tick.maybe_tick` ต่อสายเข้า `runtime.py` แล้วจริง (รอบ p05wire) --
`grep -n "lane_b_mob_ai_tick" src/pirateforce_foundation/runtime.py` = 4 hit (บรรทัด 37, 5176,
5190, 5198 -- จุดเรียกจริง ไม่ใช่คอมเมนต์) ครึ่งแรกของ `COO-DECISION 20260901_0145` ปิดแล้ว

## เส้นทางที่ตรวจแล้วและเหตุผลที่ไม่แตะรอบนี้ (ตรวจทีละเส้นกับ HEAD จริง ไม่ใช่รับช่วงจากใบเก่า)

**BUILD-004/005 (bg0001/Bg0002, สองฉาก live วันนี้)** -- ยังต่อสายอยู่ ไม่มี drift (สวีตเต็มยืนยันด้าน
ล่าง) ไม่มีการเปลี่ยนแปลงตั้งแต่รอบ 6cm6ry

**BUILD-004/005 ขยายไป Bg0015 (ฉาก 14)** -- ยืนยันซ้ำตารางสี่ประตูจากรอบ 6cm6ry ตรงกับ HEAD:
```
field_mobs.live_scenes()                    : ('Bg0002', 'bg0001')   -- Bg0015 ยังไม่อยู่
field_mobs.scene_for_scene_id(14)           : None                   -- gate 1 ยังปิด
mob_scene_recompose.composer_scene_ids()    : (1, 2)                 -- gate 4 ยังไม่ทำ
```
🔴 ตรวจเพิ่มรอบนี้ (ไม่มีในรอบ 6cm6ry): `mob_scene_recompose.py`'s
`ACKNOWLEDGED_WITHOUT_COMPOSER[14]` เขียนไว้เองตรง ๆ ว่า **"field_mobs names no scene 14 at all, so
it has no combat roster"** -- แปลว่าการสร้าง gate 4 (composer) ตอนนี้จะเป็นโมดูลที่ไม่มีข้อมูลจริงให้
ทดสอบด้วยเลย (ไม่มี roster ของฉาก 14 ในทรีนี้) จะได้แค่โครงเปล่าที่ไม่มีเทสที่มีความหมาย -- **ตัดสิน
ไม่สร้างรอบนี้** เพราะไม่ใช่ "งานเล็กที่จริง" แต่เป็น "โครงที่รอของจริงมาเติม" ซึ่งขัดกับกฎ "ห้ามส่งของ
ที่ไม่มีข้อมูลรองรับ" gate 1 (ลงทะเบียน roster) ยังต้องรอ gate 2 (ขยาย guard, COO/เจ้าของเท่านั้น)
เปิดก่อน

**BUILD-006 (เก็บของ, GT-146)** -- `mob_pickup_persist.pickup_and_persist` ยังไม่ต่อสาย
(`grep -c` = 0 ใน `runtime.py`) รอบก่อน (p05wire) ส่งใบ ASK-COO แล้วเรื่องคำสั่ง COO สองใบขัดกันเอง
(`pf_bridge/notes_to_chief/20260901_0230_LANE-B-ASK-COO-...md`) ยังไม่มีคำตอบ ณ ต้นรอบนี้ (ตรวจสด
mailbox แล้ว) -- ไม่ relitigate ไม่เดาเลือกฝ่าย

**PANYA-ORDER P-1 (ของดรอปต้องอยู่นานพอให้เดินไปเก็บ)** -- ตรวจ `mob_drop_presence.py` แล้ว: ตัวขวาง
จริงไม่ใช่ server-side lifetime (ledger อยู่ 120 วินาทีอยู่แล้ว, เขียนไว้ในโมดูลเองมาตั้งแต่รอบก่อน ๆ)
แต่เป็น**client-side label life 0.2-0.4 วินาที** ที่ COO เคยสั่งห้ามเปิด repeated-resend path ใด ๆ
(รวมถึงแบบ movement-gated) จนกว่า**รอบ attended จะยิง resend ซ้ำเพียงครั้งเดียวแล้วดูว่าป้ายกลับมาไหม**
(`COO-DECISION 2026-08-30T17:42+07:00`) -- นี่คือคำถามที่ต้องมีคนหน้าจอตอบ ไม่ใช่โค้ดที่สาย B เขียน
เพิ่มได้เองตอนนี้ กลไก resend เดี่ยว (`sustain_a_kill(cell, legacy, ())`) มีอยู่แล้วและมีเทสปักไว้แล้ว
(รอบก่อน ๆ) -- ไม่มีอะไรใหม่ให้สร้างในชั้นนี้จนกว่าจะมีคนกดทดสอบ

**PANYA-ORDER P-2 (สีชื่อมอน: ส้ม/แดง/เทา, ห้ามชมพู)** -- ไม่ใช่ของสาย B: `RE-067` (อะไรกำหนดสีชื่อ)
ยังเปิดอยู่และเป็นเขตของสาย RE โดยตรง ตามที่คำสั่งงานรอบนี้ระบุไว้เอง สาย A ตรวจไปแล้วเมื่อ 30 ส.ค.
(`20260830_0939_LANE-A-STATUS-npc-mob-color-hits-re067-068-109-ceiling-re155-opened.md`) ว่าชนเพดาน
static evidence เดิมสามใบ (`RE-067`/`RE-068`/`RE-109`) และเปิด `RE-155` ขอ attended capture แล้ว --
ยังไม่มีผลใหม่ ไม่มีอะไรให้สาย B ต่อสายรอบนี้ (การ hard-code สีตอนนี้จะขัดกับ `RE-109`'s
`BUILD_IMPACT: NONE` โดยตรง)

**PANYA-ORDER สั่งให้ chief มอบหมายสายละหนึ่งเรื่องให้ P-1/P-2/P-3 ในรอบถัดไป** -- ใบสั่ง (0215)
ยังไม่ถูก chief ประกาศมอบหมายเลนในกล่องจดหมาย ณ ต้นรอบนี้ (รอบ chief ล่าสุดที่เห็น, R277, มาก่อนใบสั่ง
0215) -- รอบนี้จึงยังไม่รับ P-1/P-2/P-3 มาเป็นเจ้าของแทนที่ charter เดิม (BUILD-004/005/006) รอ chief
ระบุชื่อสายตามที่เจ้าของสั่งเอง

**KA1B defect ① (fixed attacker profile) และ Door B (มอนขยับ/ตีกลับบนจอ)** -- ยัง ASK-COO ค้างอยู่
(รอบ 256rvs, ยังไม่มีคำตอบ) ไม่ relitigate

**ของแถมจากรอบ 6cm6ry (`DropLedger.looted` ไม่มี scene term)** -- ยังไม่พังจริงวันนี้ (kill_token
โตทางเดียวข้ามฉาก) และรอบ 6cm6ry ระบุไว้เองว่าการแก้จริงแตะ BUILD-006 ที่กำลังบล็อกอยู่ -- ไม่ควรขยับ
โดยไม่มีข้อมูลใหม่ ตัดสินไม่แตะซ้ำตามเดิม

## กล่องจดหมาย (Section B)

ตรวจ `ADDRESSEE: LANE-B` ที่ยังไม่มี `.CONSUMED.txt` ใน `pf_bridge/notes_to_chief/`: พบ 3 ใบ ปิดครบ
รอบนี้ (สอง STATUS ของสาย B เองที่ตกหล่นสตับ + `COO-DECISION 20260901_0145` ซึ่งครึ่งหนึ่งทำแล้ว/
ครึ่งหนึ่งยกไปให้ ASK-COO ที่ยังเปิดอยู่ -- ดูเนื้อ `.CONSUMED.txt` แต่ละไฟล์) ใช้สิทธิ์ self-close ตาม
`COO-DECISION 20260901_0148` (ใบจ่าหน้าถึงสายเดียวที่มีคำตอบแล้ว สายนั้นปิดเองได้)

## เทส

สวีตเต็ม `pirate-force-server` (`pytest tests -q`), ต้นรอบ: **6076 passed, 327 skipped, 13107
subtests passed, 0 failed (135.63s)** -- เทียบ baseline รอบ 6cm6ry (6073 passed) ต่างกัน +3 (สาม
เทสของ `test_lane_b_mob_ai_tick.py` ที่พลิกผลตอนต่อสายจริงในรอบ p05wire) ตรงตามที่คาด ไม่มี failure
ใหม่ ไม่มี regression

## ตัวเลขที่วัดได้

```
ไฟล์ที่แตะรอบนี้ (pirate-force-server) รวม 1:
  rounds/B_20260901_0235_62o506_mailbox-hygiene-exhaustive-blocker-check-no-src-change.md [ไฟล์นี้]

ไฟล์ที่แตะรอบนี้ (pf_bridge) รวม 4:
  notes_to_chief/20260831_0147_LANE-B-STATUS-addendum-2355-...md.CONSUMED.txt [ใหม่]
  notes_to_chief/20260831_2239_LANE-B-STATUS-server-lane-locked-no-code-this-round.md.CONSUMED.txt [ใหม่]
  notes_to_chief/20260901_0145_COO-DECISION-mob-pickup-persist-and-ai-tick-still-unwired-wire-both-this-round.md.CONSUMED.txt [ใหม่]
  notes_to_chief/20260901_0235_LANE-B-STATUS-mailbox-hygiene-no-buildable-surface-this-round.md [ใหม่, จดหมายคู่กัน]

grep -n "lane_b_mob_ai_tick" src/pirateforce_foundation/runtime.py     : 4 hit (จริง)
grep -c "mob_pickup_persist.pickup_and_persist" src/pirateforce_foundation/runtime.py : 0
field_mobs.live_scenes()                                               : ('Bg0002', 'bg0001')
mob_scene_recompose.composer_scene_ids()                               : (1, 2)
สวีตเต็มก่อน/หลังรอบนี้ (ไม่มีการแก้ src/ จึงเท่ากันทั้งคู่): 6076 passed, 327 skipped,
  13107 subtests passed, 0 failed
```

`current/pf_login_game_server_v141.py`: ไม่แตะ ไม่แตะ canonical DB/capture corpus ไม่แตะ
`runtime.py`/`app.py` ไม่แตะ `scenarios/world_*.json` (เขตสาย A)

## ยังไม่ได้พิสูจน์

- ทุกอย่างที่ยกไว้ข้างบนยังเหมือนเดิมทุกข้อ: color mapping (RE-067/RE-155), pickup opcode (RE-125/
  GT-124/GT-146), drop label re-emission (COO-DECISION 2026-08-30 17:42), Bg0015 ทั้งสี่ประตู, Door B,
  KA1B defect ① -- ไม่มีข้อไหนขยับรอบนี้ เพราะไม่มีข้อมูลใหม่มาให้ขยับ

## CORE-REQUEST

ไม่มี

## เปิดใบให้สาย C

ไม่มี -- ไม่มีคำถามใหม่ที่ต้องรอนอกโปรเจกต์รอบนี้ (RE-067/RE-125/RE-155 เป็นใบที่เปิดอยู่แล้วของสาย RE
ก่อนรอบนี้ ไม่ใช่ใบใหม่)

## หมายเหตุ -- "pirate-force-server round file คู่กัน" ที่ p05wire อ้างถึงไม่มีอยู่จริง

`pf_bridge/rounds/B_20260901_0210_p05wire.md` เขียนไว้ว่ามีไฟล์คู่กันในฝั่งนี้ ("ดูรายละเอียดใน
`pirate-force-server` round file คู่กัน") แต่ `rounds/` ของ repo นี้ไม่มีไฟล์ p05wire เลย (ตรวจแล้ว:
เทียบกับ `B_20260901_0106_6cm6ry_*.md` ที่มีจริง) -- น่าจะเป็นผลจากเหตุการณ์ session คู่ขนานที่
p05wire's ไฟล์เองบันทึกไว้ (git reset --hard ทิ้งงานตัวเองแล้วรับของ session อื่นแทน) บันทึกไว้ตรงนี้
เพื่อไม่ให้ใครค้นหาไฟล์นั้นแล้วคิดว่าหาย ไม่ใช่ของรอบนี้ที่ต้องแก้ย้อนหลัง

-- LANE-B (COMBAT) รอบ `62o506`
