# รอบ B_20260901_1540 (round `3w2mfu`) -- pirate-force-server

เปิดรอบ 2026-09-01T15:35+07:00, เนื้อรอบเขียน 2026-09-01T15:40+07:00 (scheduled, ไม่มีคนเฝ้าหน้าจอ)
Branch: `claude/zen-einstein-3w2mfu`

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้แก้เอกสารภายในโค้ด (docstring) สองไฟล์เท่านั้น -- ไม่เปลี่ยนพฤติกรรมรันไทม์ใด ๆ
`lane_b_mob_ai_tick.maybe_tick` ยัง "composes no frame" เหมือนเดิมทุกประการ (ยืนยันด้วยการอ่านโค้ด
ไม่ได้แก้) มีแค่พิมพ์บรรทัด console `LANE_B_MOB_AI_TICK` เมื่อมอนเปลี่ยนเฟส -- ไม่มีอะไรบนจอไคลเอนต์
เปลี่ยน

## ต้นรอบ -- ตรวจล็อกและ merge

1. `git fetch origin` + `git merge origin/main` -- fast-forward `13e229c8` -> `15883cc5`
   (รับ PR #483 `[LANE-A]` ที่เพิ่ง merge, ไฟล์เดียว `docs/GM_LANE.md`, ไม่ชนกับอะไรของสายนี้)
2. ตรวจล็อก: ไม่มี PR `[LANE-B]` ค้างเปิดในทั้งสองรีโปตอนต้นรอบ (ตามที่ orchestrator ยืนยันแล้ว
   pf_bridge#718 / pirate-force-server#479 ทั้งคู่ merged=true)
3. ตรวจกล่องจดหมาย `ADDRESSEE: LANE-B` ที่ยังไม่มี `.CONSUMED.txt` ใน pf_bridge -- ไม่พบ (สะอาด,
   ตามที่ orchestrator ยืนยันแล้วเช่นกัน)

## การตรวจสอบพื้นผิวใหม่ (ตามข้อ 1 ของงานที่ได้รับ)

อ่านรอบล่าสุด 6 รอบของสาย B (`4qwc1x`, `hqzp16`, `ruigb0`, `fbql13` และย้อนถึง `p05wire`/`62o506`)
รวมทั้งจดหมาย `LANE-B-STATUS` ล่าสุดเกี่ยวกับ BUILD-004/5/6 (`20260830_2343`, `20260831_1547`) แล้ว
ตรวจซ้ำสดจากซอร์ส HEAD ปัจจุบัน (ไม่เชื่อจดหมายเก่าเฉย ๆ):

```
grep -c mob_pickup_persist src/pirateforce_foundation/runtime.py            -> 0 (BUILD-006 จุดที่สาม
  ยังไม่มี call site จริง ยืนยันซ้ำ)
grep -n lane_b_mob_ai_tick src/pirateforce_foundation/runtime.py            -> :37, :5188-5210
  (BUILD-004/M6 AI-tick มี call site จริงแล้ว -- ต่อสายโดยรอบ p05wire ตาม COO-DECISION
  20260901_0145, ยืนยันด้วย pytest ผ่านจริง)
grep -n mob_combat_membership src/pirateforce_foundation/runtime.py         -> 0 (RE-157 job2 guard
  ยังไม่ต่อสาย -- CORE-REQUEST ค้างอยู่ในโมดูลเอง, เป็นของ chief)
grep -n field_mob_hostile_bg0015 src/pirateforce_foundation/lane_hooks/lane_a_choose_npc_scene14.py
  -> มี (สาย A ต่อสายโมดูล pre-wire ของสายนี้เข้า live path แล้วจริง, ยืนยันจากจดหมาย
  20260901_0202_LANE-A-STATUS-choosenpc-scene14-hostile-splice-fixed-*.md -- ผู้เล่นเห็นมอน
  แดง 12 ตัวในฉาก 14 แล้วตั้งแต่รอบ `yfbqmg`)
```

**สรุปพื้นผิว BUILD-004/5/6:**
- **BUILD-004 ฉาก 14 (Bg0015):** เดินสายจริงแล้วโดยสาย A + chief (`field_mob_hostile_bg0015.py` ของ
  สายนี้ถูกใช้จริงใน `lane_a_choose_npc_scene14.py`) -- ไม่มีงานเหลือให้สาย B ที่นี่อีก
- **BUILD-005 (hit/die):** เดินสายแล้วสำหรับฉากที่ live วันนี้ (bg0001/Bg0002) -- ไม่มี drift
- **BUILD-006 (pickup persist):** ยังบล็อกจุดเดียว -- `resolve_claim`/`place_in_bag`/
  `BagCell.commit_pickup`/`mob_pickup_persist.pickup_and_persist` ไม่มี call site เพราะ RE-125
  ปิดแบบ BOUNDED-NEGATIVE (opcode `0x4543` ยัง UNOBSERVED, `COO-DECISION 20260830_1145` ยืนยันซ้ำ
  ล่าสุด `20260901_0245`) รอ `GT-124` (attended capture) ก่อน -- ไม่ใช่โค้ดที่เดาได้
- **มอบให้ chief:** `mob_combat_membership.py` (RE-157 job 2) ยังมี CORE-REQUEST ค้างในตัวโมดูลเอง
  (ดูหัวข้อ CORE-REQUEST ด้านล่าง) -- runtime.py เป็นของ chief

ไม่มีจุดไหนในสามข้อ BUILD ที่สาย B แก้เองได้โดยไม่ทำผิดกฎ (chief's file / COO-decision /
attended-only) -- ตรงกับที่ 6 รอบก่อนหน้าสรุปไว้ทุกครั้ง

## P-1 (NOW.md) -- ตรวจว่ายังเป็นตัวบล็อกจริงหรือแค่รอ attended

`NOW.md` 14:47+07 ระบุ P-1 สถานะ "ยังไม่ขยับ" (ยังไม่ถูกย้ายไปหัวข้อ "รอ Panya ติ๊ก") แต่ตรวจ
`GAME_TEST_QUEUE.md:9411` แล้วพบ `GT-188` สถานะ `PENDING -- ... ready to boot` (โค้ด+เทสฝั่งเซิร์ฟเวอร์
เสร็จแล้ว: `app.py` wiring จาก PR #441/#437, `preserve_ground_heartbeat_frame` merged) ตรงกับกฎใหม่ของ
`NOW.md` เอง ("โค้ด+เทสฝั่งเซิร์ฟเวอร์เสร็จแล้ว เหลือแค่รอ Panya รัน GT เทส (attended) เท่านั้น = ไม่ใช่
ตัวบล็อกสาย") -> **P-1 ไม่ใช่ตัวบล็อกโค้ดของรอบนี้** สายนี้จึงไปทำงานคิวปกติต่อได้ (ซึ่งก็คือสิ่งที่รอบนี้ทำ)

## กฎ F: ปิดหนี้เทคนิคจริงหนึ่งจุด (mob_ai_tick wiring doc drift)

รอบ `p05wire` (2026-08-31T~19:11 UTC, COO-DECISION 20260901_0145) ต่อสาย
`lane_hooks.lane_b_mob_ai_tick.maybe_tick` เข้า `runtime.py`'s `dispatch()` จริงแล้ว (commit
`5ac93b31`) และพลิกเทสลบ (`test_nothing_in_runtime_py_calls_maybe_tick_yet` ->
`test_runtime_py_now_calls_maybe_tick_per_coo_decision_0145`) แต่**ไม่ได้แก้ prose สองจุดที่ยังพูดว่า
"nothing calls this yet"**:

1. `src/pirateforce_foundation/lane_hooks/lane_b_mob_ai_tick.py` -- ส่วน "WHAT THE PLAYER WILL SEE
   DIFFERENTLY" ของ module docstring ยังอ้างชื่อเทสเก่าที่ไม่มีอยู่แล้ว
2. `tests/test_lane_b_mob_ai_tick.py` -- module docstring ของไฟล์เทสเองก็อ้างชื่อเทสเก่าเดียวกัน และ
   สัญญาไว้ตรง ๆ ว่า "this test fails the day that stops being true without the module docstring...
   being updated to match" -- วันนั้นมาถึงแล้ว (รอบ `p05wire`) แต่ docstring ยังไม่ถูกอัปเดตตามที่
   สัญญาไว้

แก้ตามธรรมเนียมโปรเจกต์: ขีดฆ่า (`~~...~~`) ไม่ลบ ต่อท้ายด้วย `[STALE ...][MEASURED ...]` อ้างรอบ/
commit/COO-DECISION ที่แก้จริง ยืนยันเนื้อหาด้วยการอ่าน `runtime.py:5195-5202` เอง (นับเงื่อนไข guard
ให้ครบ 6 ข้อ ไม่ใช่ 5 ตามที่ร่างแรกเขียนพลาด -- ดูหัวข้อ self-review ด้านล่าง)

### Self-review เชิง adversarial (ไม่มี Agent/Task tool ให้เรียก pf-adversary subagent ตรงในเซสชันนี้)

พบ 1 จุดบกพร่องในร่างแรกของตัวเอง ก่อน commit: ร่างแรกเขียนว่า "All five guard conditions" แต่
`runtime.py:5195-5202` มีจริง **6** เงื่อนไข (`nested_id==TARGET_POS_VITAL`, `last_target_pos is not
None`, `mob_ai_register is not None`, `mob_combat_ledger is not None`, `foundation.selected is not
None`, `module_production_allowed(...)`) -- ร่างแรกลืมนับเงื่อนไข `production_allowed` เอง (เป็น
class บั๊กเดียวกับที่ pf-adversary จับได้ในรอบ `hqzp16`: "overclaim by omission") แก้แล้วในคอมมิตเดียวกัน
ก่อน push, ตรวจตัวเลขซ้ำด้วยการอ่านโค้ดจริงอีกครั้งหลังแก้ (ดู bash grep ด้านบน)

## ตัวเลขที่วัดได้

```
pytest tests/test_lane_b_mob_ai_tick.py -q: 9 passed
pytest tests -q (full suite, หลังแก้): 6302 passed, 323 skipped, 13373 subtests passed, 0 failed
  (202.98s)
git diff --check: silent (ไม่มี whitespace issue)
cp874-encodability ของทั้งสองไฟล์ที่แก้: ยืนยันด้วย .encode('cp874') ทั้งคู่ -- ไม่มี error
```

## ไฟล์ที่แตะ (3)

- `src/pirateforce_foundation/lane_hooks/lane_b_mob_ai_tick.py` -- แก้ docstring (strike+append)
- `tests/test_lane_b_mob_ai_tick.py` -- แก้ docstring (strike+append)
- `rounds/B_20260901_1540_3w2mfu_mob_ai_tick_wiring_doc_drift_fixed_no_new_src_surface_confirmed_again.md`
  -- ไฟล์นี้ (ใหม่)

## ยังไม่ได้พิสูจน์

- `GT-188` (P-1) ยังไม่มีคนเทส attended
- P-2/P-3 ยังบล็อกภายนอก ไม่ใช่ของสายนี้
- BUILD-006 จุดเสียบที่สามยังรอ `GT-124` (attended capture ของ opcode pickup จริง)

## CORE-REQUEST

ไม่มี (ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py` รอบนี้) -- มี CORE-REQUEST เก่าที่
ยังค้างอยู่ในตัวโมดูลเอง (`mob_combat_membership.py`, RE-157 job 2: หนึ่ง predicate call ใน
`_dispatch_mob_combat`) รอ chief หยิบเมื่อมีที่ว่างในคิว ไม่ใช่คำขอใหม่ของรอบนี้

## เปิดใบให้สาย C

ไม่มี

-- LANE-B (COMBAT) รอบ `3w2mfu`
