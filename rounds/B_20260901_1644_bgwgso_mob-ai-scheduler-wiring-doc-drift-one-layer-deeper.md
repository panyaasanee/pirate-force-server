# รอบ B_20260901_1644 (round `bgwgso`) -- pirate-force-server

เปิดรอบ 2026-09-01T16:30+07:00 (โดยประมาณ), เนื้อรอบเขียน 2026-09-01T16:44+07:00 (scheduled,
ไม่มีคนเฝ้าหน้าจอ)
Branch: `claude/zen-einstein-bgwgso`

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้แก้ docstring/comment/nonclaims (prose ล้วน) ใน `mob_ai_scheduler.py`,
`mob_ai_control.py` และ `tests/test_mob_ai_scheduler.py` เท่านั้น ไม่แตะ logic/control-flow ใด ๆ
`mob_ai_scheduler.tick_session` ยัง "composes no frame" เหมือนเดิมทุกประการ

## ต้นรอบ

1. `git checkout -B claude/zen-einstein-bgwgso origin/main` จาก tip ปัจจุบัน (`49284252`) ครั้งเดียว
   ตอนต้นรอบเท่านั้น (ไม่ re-run ระหว่างรอบ -- ป้องกัน commit หาย ตามที่ orchestrator เตือนกลางรอบ
   เมื่อพบว่า pf_bridge ฝั่งนี้ถูก reset ไปที่ origin/main เช่นกัน แต่ตรวจแล้วพบว่าเป็นแค่การ checkout
   ครั้งแรกครั้งเดียวที่ทำก่อนแตะไฟล์ใด ๆ ทั้งสองรีโป ไม่มีคอมมิตหายจริง)
2. ตรวจล็อก: ไม่มี PR `[LANE-B]` ค้างเปิดในทั้งสองรีโปตอนต้นรอบ (ยืนยันแล้วโดย orchestrator)
3. ตรวจกล่องจดหมาย `ADDRESSEE: LANE-B` ที่ยังไม่มี `.CONSUMED.txt` ใน `pf_bridge` -- ไม่พบของใหม่
   (ตรวจ `git log` ตั้งแต่ merge ของรอบ `3w2mfu` (`7cf633d8`) ถึง HEAD ปัจจุบัน (`2129337c`): มีแต่
   จดหมาย LANE-E/LANE-GM/LANE-A/LANE-DB, ไม่มีที่จ่าหน้าถึง LANE-B)
4. อ่าน `pf_bridge/NOW.md` (ตรวจล่าสุด 14:47+07 โดย COO): P-1/P-2/P-3 สถานะเหมือนเดิมทุกจุด --
   `GT-146` และใบเทสตีมอนทุกใบยังล็อกตาม "ห้ามทำจนกว่า P-1 กับ P-2 จะปิด" (ยืนยันซ้ำที่
   `GAME_TEST_QUEUE.md:33,7420`)

## ตรวจ BUILD-004/5/6 ซ้ำจากซอร์สสดของรอบนี้เอง

```
grep -c mob_pickup_persist src/pirateforce_foundation/runtime.py       -> 0 (BUILD-006 จุดสาม
  ยังไม่ต่อสาย)
grep -n lane_b_mob_ai_tick src/pirateforce_foundation/runtime.py       -> :37, :5188-5210 (ต่อสาย
  แล้วจริงตั้งแต่รอบ p05wire)
grep -c mob_combat_membership src/pirateforce_foundation/runtime.py    -> 0 (RE-157 job2 --
  CORE-REQUEST ค้างในโมดูลเอง)
```

ไม่มีพื้นผิว src ใหม่ให้สายนี้ทำเพิ่มโดยไม่ผิดกฎ (chief's file / COO-decision / attended-only) --
ตรงกับ 7 รอบก่อนหน้าทุกจุด (`4qwc1x`/`hqzp16`/`ruigb0`/`fbql13`/`3w2mfu` และย้อนไป)

## กฎ F: ปิดหนี้เทคนิคจริงหนึ่งจุด -- ไปลึกกว่ารอบ `3w2mfu` หนึ่งชั้น

รอบ `3w2mfu` (รอบก่อนหน้าของสายนี้) แก้ docstring drift ของ **wrapper** `lane_hooks/
lane_b_mob_ai_tick.py` และเทสของมันเองไปแล้ว (ที่ยังพูดว่า "nothing calls this yet" หลังจากรอบ
`p05wire`/`COO-DECISION 20260901_0145` ต่อสาย `maybe_tick` เข้า `runtime.py` จริงที่ commit
`5ac93b31`) **แต่ไม่ได้ไล่ไปแก้โมดูลที่ wrapper นั้นห่ออยู่** -- `mob_ai_scheduler.py` (ซึ่ง
`maybe_tick` เรียก `tick_session` ตรง ๆ ที่บรรทัด 181 ของ wrapper) และ `mob_ai_control.py`
(ซึ่ง `tick_session` เรียก `tick_step`/`commit_step` ต่อแถว) ยังพูดแบบเดียวกันว่า "nothing calls
this today" / "no caller anywhere in this tree runs it in production" / "What remains
UNDISPATCHED is the tick loop" -- เป็นบั๊กคลาสเดียวกัน (stale wiring-status prose) แค่อยู่ลึกลง
ไปอีกชั้นที่รอบก่อนไม่ได้ไล่ตาม import chain ลงไปถึง

ยืนยันสายเรียกจริงด้วยการอ่านโค้ด (ไม่ใช่แค่อ่านจดหมาย):

```
runtime.py:5196-5214           -- guard 6 เงื่อนไข + เรียก lane_b_mob_ai_tick.maybe_tick(...)
lane_hooks/lane_b_mob_ai_tick.py:181  -- maybe_tick เรียก mob_ai_scheduler.tick_session(...) ตรง ๆ
mob_ai_scheduler.py:265        -- tick_session เรียก mob_ai_control.tick_step(...) ต่อแถว
production_allowed ของทั้งสามโมดูล (lane_b_mob_ai_tick / mob_ai_scheduler / mob_ai_control)
  -> True ทั้งหมด (grep ยืนยันแล้ว) -- เป็นเส้นทาง flagless จริง ไม่ใช่ probe
```

### แก้ตามธรรมเนียมโปรเจกต์ ([STALE ...][MEASURED ...] ต่อท้าย ไม่ลบของเดิม)

1. `mob_ai_scheduler.py` module docstring -- 3 จุด: ย่อหน้า "WHY THIS MODULE EXISTS" (อ้างว่า
   "no caller anywhere in this tree runs it in production"), bullet "THE CLOCK IS THE CALLER'S"
   (อ้างว่า "Today: nothing calls it"), ย่อหน้า "WHAT THE PLAYER WILL SEE DIFFERENTLY" (อ้างว่า
   "nothing today" และพูดถึง call site เป็นเรื่องอนาคต) -- เติม `[STALE][MEASURED]` ทั้งสามจุด
2. `mob_ai_scheduler.MOB_AI_SCHEDULER_WIRING` -- คอมเมนต์เหนือ constant (อ้างว่าเป็น "the one line
   this lane owes the chief" ที่ยังไม่จ่าย) -- เติมคอมเมนต์ `[STALE][MEASURED]` ระบุว่าจ่ายแล้ว
   ตัว string ค่าคงที่เอง **ไม่แก้** เพราะเทสสองเส้น (`test_the_wiring_line_names_runtime_py_and_
   stays_unwired_today`) ยังพินไว้ว่าต้องมีคำว่า `"runtime.py"` และ `"mob_ai_scheduler.tick_session"`
   อยู่ในสตริง -- แก้เฉพาะคอมเมนต์ ไม่แก้ค่าที่เทสพิน
3. `mob_ai_control.MOB_AI_CONTROL_NONCLAIMS[0]` (อ้างว่า "What remains UNDISPATCHED is the tick
   loop") -- เติม `[STALE][MEASURED]` ระบุว่า `tick_step` ถูก dispatch แล้ว ส่วน `reconcile()` ยัง
   undispatched จริง (ยังไม่แก้ครึ่งนั้น เพราะยังจริงอยู่ -- คลาสนี้ไม่เคย rebuild roster หลังเปิด
   register ครั้งแรกต่อ session, ยืนยันด้วยการอ่านโค้ดซ้ำ)
4. `tests/test_mob_ai_scheduler.py` module docstring -- อ้างชื่อเทสผิด (`test_the_scheduler_has_
   no_importer_yet` ซึ่งไม่มีอยู่จริง -- ชื่อจริงคือ `test_the_scheduler_has_exactly_the_one_ready_
   importer`, เปลี่ยนชื่อไปแล้วตั้งแต่รอบ `iok5z1` ตามคอมเมนต์ในโค้ดเอง แต่ docstring ของไฟล์เทสไม่ได้
   ตามไปแก้) -- เติม `[STALE, name mismatch][MEASURED]`
5. `test_the_wiring_line_names_runtime_py_and_stays_unwired_today` -- ชื่อเทสเองอ้างว่า "stays
   unwired today" ซึ่งเป็นเท็จแล้วในความหมายที่ใช้งานจริง (มี caller จริงผ่าน wrapper) แต่สิ่งที่เทส
   ตรวจจริง (สตริงมีคำว่า "runtime.py" กับ "mob_ai_scheduler.tick_session") ยังถูกต้อง -- เติม
   คอมเมนต์อธิบาย **ไม่เปลี่ยนชื่อฟังก์ชัน** (การเปลี่ยนชื่อเทสเป็นการตัดสินใจที่ต้องเช็คว่าไม่มีไฟล์อื่น
   อ้างชื่อนี้ก่อน -- ทิ้งไว้ให้รอบที่มีเวลาตรวจครบกว่านี้)

### ไฟล์ pin ที่ต้อง regenerate

`scenarios/combat_aggro_001.json` เป็น pin ตัวเลขที่คอมมิตไว้ ผลิตจาก
`mob_ai_control.pin_document()` -- `nonclaims` เป็นหนึ่งในฟิลด์ที่ pin นี้ echo ค่าจาก
`MOB_AI_CONTROL_NONCLAIMS` ตรง ๆ (ยืนยันด้วยการอ่าน `tools/pf_write_mob_ai_pin.py` และเนื้อไฟล์ pin
เดิมก่อนแก้) รันคำสั่ง `python3 tools/pf_write_mob_ai_pin.py --out scenarios/combat_aggro_001.json`
แล้ว `git diff --stat` ยืนยัน **1 บรรทัดเปลี่ยน** ตรงกับ nonclaim ตัวเดียวที่แก้พอดี ไม่มีตัวเลข/ฟิลด์
อื่นขยับ

`MOB_AI_SCHEDULER_WIRING` **ไม่มี pin แยก** (`grep -rl MOB_AI_SCHEDULER_WIRING scenarios/ tools/`
ว่างเปล่า) -- ไม่ต้อง regenerate อะไรเพิ่ม

## Self-review เชิง adversarial (ไม่มี Agent/Task tool ให้เรียก pf-adversary subagent ตรงในเซสชันนี้)

ไม่มีเครื่องมือ Agent/Task ในเซสชันนี้ (เหมือนรอบ `ruigb0`/`vzhc6s`/`3w2mfu`) ทำเองตามขั้นตอนที่
pf-adversary จะทำ:

1. **cross-check บรรทัด runtime.py ที่อ้าง**: อ่าน `runtime.py:5188-5214` เองอีกครั้งหลังแก้ --
   ยืนยัน guard 6 เงื่อนไข, เรียก `lane_b_mob_ai_tick.maybe_tick(self.mob_ai_register,
   self.mob_combat_ledger, performer, (x, y, z))` ตรงกับที่อ้างในคอมเมนต์ที่เติม
2. **cross-check ห่วงโซ่การเรียกจริง**: อ่าน `lane_hooks/lane_b_mob_ai_tick.py:181` (เรียก
   `mob_ai_scheduler.tick_session`) และ `mob_ai_scheduler.py:265` (เรียก `mob_ai_control.
   tick_step`) เอง -- ไม่ได้เชื่อจากจดหมายเก่า
3. **ตรวจ pin ไม่ให้ตัวเลข/ฟิลด์อื่นขยับโดยไม่ตั้งใจ**: `git diff scenarios/combat_aggro_001.json`
   มีแค่ 1 บรรทัด (nonclaims[0]) เปลี่ยน
4. **ตรวจว่าไม่ทำลายเทสที่มีอยู่**: รัน `test_the_wiring_line_names_runtime_py_and_stays_unwired_
   today` และ `test_the_committed_pin_is_what_the_code_computes` (ทั้งคู่ผ่าน) -- ยืนยันว่าการเติม
   `[STALE][MEASURED]` ไม่ไปลบสตริงย่อยที่เทสสองเส้นนี้ยังพินไว้
5. **ตรวจว่าไม่แก้ logic**: `git diff` เต็มอ่านด้วยตา -- ทุกบรรทัดที่เปลี่ยนเป็น string
   literal/comment ล้วน ไม่มีบรรทัด control-flow เปลี่ยนแม้แต่บรรทัดเดียว
6. **ตรวจ `git diff --check`**: silent (ไม่มี whitespace error)
7. **ตรวจ cp874/ast**: ทั้งสามไฟล์ src/tests ที่แก้ผ่าน `ast.parse` และ `.encode('cp874')` โดยไม่มี
   error
8. **ตรวจว่าไม่แตะเขต P-2/GM**: ไม่แตะ nonclaim เรื่องสีชื่อมอนสเตอร์ใน `mob_combat.py` (เขตของสาย
   GM/RE-067) -- นอกขอบเขตรอบนี้เจตนา
9. รันสวีตย่อย (`test_mob_ai_scheduler.py` + `test_mob_ai_control.py` + `test_lane_b_mob_ai_tick.py`
   + `test_mob_combat.py`) ก่อน/หลังแก้ -- ตัวเลขเท่ากันทั้งสองรอบ ไม่มี regression

**พบ 1 จุดในร่างแรกของตัวเอง**: อ้าง "see that test's own docstring below" สำหรับคอมเมนต์ inline
เหนือ `test_the_scheduler_has_exactly_the_one_ready_importer` -- ที่จริงเป็น **comment** ไม่ใช่
docstring (ฟังก์ชันนั้นไม่มี `"""..."""` ของตัวเอง มีแค่ `#` คอมเมนต์เหนือมัน) แก้คำเป็น "inline
comment" ก่อน push

## ตัวเลขที่วัดได้

```
pytest tests/test_mob_ai_scheduler.py tests/test_mob_ai_control.py tests/test_lane_b_mob_ai_tick.py -q
  -> 82 passed, 37 subtests passed (ก่อนแก้และหลังแก้เท่ากัน)
pytest tests/test_mob_ai_scheduler.py tests/test_mob_ai_control.py tests/test_lane_b_mob_ai_tick.py
  tests/test_mob_combat.py -q
  -> 139 passed, 37 subtests passed
full suite (tests/ ทั้งหมด, รันพื้นหลังระหว่างรอบ): 6352 passed, 323 skipped, 13717 subtests
  passed, 0 failed (265.62s)
git diff --check: silent
cp874-encodability ของ 3 ไฟล์ที่แก้ (2 src + 1 test): ยืนยันด้วย .encode('cp874') -- ไม่มี error
scenarios/combat_aggro_001.json regenerate: 1 บรรทัดเปลี่ยน (ตรงกับ nonclaim ที่แก้)
```

## ไฟล์ที่แตะ (5)

- `src/pirateforce_foundation/mob_ai_scheduler.py` -- เติม `[STALE][MEASURED]` 4 จุด (docstring x3,
  คอมเมนต์เหนือ `MOB_AI_SCHEDULER_WIRING` x1), ไม่แก้ logic
- `src/pirateforce_foundation/mob_ai_control.py` -- เติม `[STALE][MEASURED]` 1 จุดใน
  `MOB_AI_CONTROL_NONCLAIMS[0]`, ไม่แก้ logic
- `tests/test_mob_ai_scheduler.py` -- เติม `[STALE][MEASURED]` ใน module docstring + คอมเมนต์เหนือ
  `test_the_wiring_line_names_runtime_py_and_stays_unwired_today`, ไม่แก้ assertion ใด ๆ
- `scenarios/combat_aggro_001.json` -- regenerate จาก `pin_document()` จริง (1 บรรทัดเปลี่ยน)
- `rounds/B_20260901_1644_bgwgso_mob-ai-scheduler-wiring-doc-drift-one-layer-deeper.md` -- ไฟล์นี้
  (ใหม่)

## ยังไม่ได้พิสูจน์

- `GT-188` (P-1) ยังไม่มีคนเทส attended
- P-2/P-3 ยังบล็อกภายนอก ไม่ใช่ของสายนี้
- BUILD-006 จุดเสียบที่สามยังรอ `GT-124` (attended capture opcode pickup จริง)
- `reconcile()` ใน `mob_ai_control.py` ยังไม่มี dispatcher จริง (ยังไม่แก้ ยังจริงอยู่)
- การเปลี่ยนชื่อ `test_the_wiring_line_names_runtime_py_and_stays_unwired_today` เป็นชื่อที่ตรงความจริง
  กว่านี้ -- ทิ้งเป็นคอมเมนต์ ไม่ได้ทำจริงรอบนี้ (ต้องเช็คก่อนว่าไม่มีไฟล์อื่นอ้างชื่อนี้)

## CORE-REQUEST

ไม่มี (ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py` รอบนี้) -- CORE-REQUEST เก่าที่
ยังค้าง (`mob_combat_membership.py`, RE-157 job 2) ไม่ใช่คำขอใหม่ของรอบนี้ ไม่ได้แตะซ้ำ

## เปิดใบให้สาย C

ไม่มี

-- LANE-B (COMBAT) รอบ `bgwgso`
