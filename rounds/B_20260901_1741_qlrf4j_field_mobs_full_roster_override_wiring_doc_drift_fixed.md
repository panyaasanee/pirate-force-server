# LANE-B round `qlrf4j` -- field_mobs.py's own headline claim ("never sent,
# never observed") was 3 days stale; runtime.py has called
# mob_death.full_roster_override on every home-scene census since 2026-08-29

## ต้นรอบ -- ตรวจ P-1/P-2/P-3, กล่องจดหมาย, ใบ CLAIM

- `pirate-force-server` checkout จาก `origin/main` tip (`7b1914e`, merge ของรอบ `bgwgso` #491) --
  local branch `claude/zen-einstein-qlrf4j` ตรงกับ origin/main พอดี ไม่มี PR `[LANE-B]` ค้างเปิด
- `pf_bridge` `NOW.md` (ตรวจล่าสุดโดย COO 2026-09-01 16:40): P-1/P-2/P-3 ยังพักตาม PANYA-ORDER
  20260901_0215, แต่มีกติกาใหม่ชัดเจนบรรทัด 19-21: "โค้ด+เทสฝั่งเซิร์ฟเวอร์เสร็จแล้ว เหลือแค่รอ Panya
  รัน GT เทส (attended) เท่านั้น = ไม่ใช่ตัวบล็อกสาย" -- ยืนยันสดในเซสชัน 2026-09-01 14:47+07 ตรงกับที่
  รอบ `ruigb0` (13:34) และรอบต่อ ๆ มาเจอ: P-1 (ของดรอปค้างพื้น, heartbeat PRESERVE) ต่อสายครบแล้วโดย
  chief (PR server#441 merge แล้ว), เปิด `GT-188` รอ attended อย่างเดียว -- **ไม่ใช่พื้นผิวใหม่ให้สาย
  B รอบนี้** ไม่เขียนใบ CLAIM เพราะนี่ไม่ใช่ตั๋วที่ระบุผู้ทำได้มากกว่าหนึ่งสาย -- เป็นงานที่ chief
  ทำเสร็จแล้วและรอ attended เท่านั้น
- `GT-146`/ใบเทสตีมอนทุกใบยังล็อกตาม NOW.md ("ห้ามทำจนกว่า P-1 กับ P-2 จะปิด") -- ไม่แตะ BUILD-005
- RE-098: มี stub `.CONSUMED.txt` อยู่แล้วตั้งแต่ 2026-08-27 (chief round `keen-pasteur-ss84b6` R189) --
  ไม่ใช่ใบค้างของรอบนี้
- กล่องจดหมาย `notes_to_chief/ADDRESSEE:.*LANE-B` และ `FROM_CHIEF_*` ทั้งหมดมี stub ครบ ไม่มีใบใหม่
- ไม่มี `*CLAIM*` ที่ยัง active เกี่ยวกับพื้นผิวที่รอบนี้แตะ (`field_mobs.py`)

## กฎ F -- ปิดหนี้เทคนิคจริงหนึ่งจุด (ตามธรรมเนียม 6 รอบก่อนหน้า: `1247`/`1343`/`1436`/`1540`/`3w2mfu`/
## `bgwgso`)

`field_mobs.py`'s module docstring (ย่อหน้า "CORRECTED 2026-08-26 (round `4z0efc`)") ยังพูดว่า:

> nothing in ``runtime.py`` calls ``full_roster_override`` yet - its one
> existing census-override call site still calls the narrower
> ``corpse_override``...

grep สดที่ HEAD: `runtime.py` มีบรรทัด
`mob_death_override = mob_death.full_roster_override(legacy, synced_roster, self.mob_death_register, ledger=self.mob_combat_ledger)`
จริง (world-census composer, branch `scene_id == world_population.SCENE_ID`) -- คำอ้างเดิมเท็จมา
3 วันแล้ว: `git log -S"full_roster_override" -- runtime.py` ชี้ commit `5a272a0` ("Wire two
CORE-REQUESTs: measured stowaways line and scene-consistent census override", 2026-08-29 10:25
UTC) ตรงกับ `pf_bridge/notes_to_chief/20260829_1603_CHIEF-REPLY-two-core-requests-wired-stowaways-
and-census-override-sync.md` -- ไม่มีรอบ LANE-B ไหนกลับมาแก้ prose ของ `field_mobs.py` เองหลังจากนั้น
(ตรวจ `git log --all -- src/pirateforce_foundation/field_mobs.py` -- คอมมิตล่าสุดที่แตะไฟล์นี้คือ PR
#431 merge ของรอบ `0235`, ไม่ใช่การแก้ prose)

**ผลคือ headline claim ของโมดูลเอง ("named + faction together: THIS module, never sent, never
observed") ก็เท็จไปด้วย** -- ของที่โมดูลนี้สร้าง (มอนสเตอร์มีชื่อ+hostile พร้อมกัน) อยู่บนไวร์จริงทุก
boot ที่ผ่านไปถึง composer นั้น (home scene) มาตั้งแต่ 29 ส.ค. ตราบใดที่ ledger ของฉากตรงกัน (registry
กันไว้กรณีเดียวคือ scene ไม่ addressed)

แก้ตามธรรมเนียมโปรเจกต์: **ต่อท้ายด้วย `[STALE ...][MEASURED ...]`, ไม่ลบ/ไม่แก้ของเดิม** ที่ท้าย
docstring (ก่อน `"""` ปิด) อ้าง commit `5a272a0` + จดหมาย chief `20260829_1603` เป็นหลักฐานว่า wiring
มีจริง และย้ำว่าสิ่งที่ยังไม่วัดคือฝั่ง client (RE-067 ปิดแล้วแต่ตัวขับสีชื่อยังไม่รู้ -- ไม่ใช่เรื่องใหม่
ของรอบนี้ อ้างถึงย่อหน้าแก้เดิมของไฟล์เดียวกัน)

## ตรวจก่อน push (self-review, ไม่มี Task/Agent tool ให้เรียก pf-adversary subagent ตรงในเซสชันนี้)

1. grep หา `never sent, never observed` และ `nothing in .*runtime.py.*calls` ทั่ว `src/` และ
   `tests/` -- ไม่มีเทสไหน pin สตริงนี้ (ต่างจากกรณี `mob_ai_scheduler` รอบ `bgwgso`) จึงไม่มีเทสแดง
2. ยืนยันบรรทัด call-site จริงด้วยการอ่านโค้ด (`runtime.py:8281`) ไม่ใช่เชื่อ prose เก่า
3. `python3 -m pytest tests/test_field_mobs.py tests/test_mob_death.py tests/test_mob_combat.py -q`
   -> 193 passed (เท่าเดิมก่อน/หลัง -- แก้แค่ docstring)
4. `ast.parse()` + `.encode('cp874')` ผ่านทั้งไฟล์ ไม่มีอักขระนอกช่วง
5. `git diff --stat` -- ไฟล์เดียว, +20/-0 (เพิ่มล้วน ไม่มีลบ/แก้บรรทัดเดิม)
6. เช็ค `pin_document()` -- ไม่ได้ดึง `__doc__` หรือ prose ส่วนนี้เข้า pin เลย จึงไม่ต้อง regenerate
   `scenarios/field_mobs_hostile_001.json`
7. `pytest tests/` เต็ม (รันพื้นหลัง เกิน timeout ปกติของคำสั่งเดี่ยว): **6350 passed, 327 skipped,
   13717 subtests passed, 0 failed (198.26s)** -- เทียบรอบก่อน (`bgwgso`: 6352/323/13717/0) ต่างกัน
   2 passed / 4 skipped เท่านั้น ตรงกับรูปแบบที่รอบก่อน ๆ ตรวจแล้วว่าเป็น skip ที่ต่างด้วย
   `[precondition:client_image]` (environment-dependent) ไม่เกี่ยวกับ diff ของรอบนี้ -- 0 failed คือ
   ตัวเลขที่สำคัญที่สุด ไม่มี regression

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้แก้ docstring ล้วน (เพิ่มย่อหน้าแก้ต่อท้าย ไม่ลบของเดิม) ไม่แตะโค้ดที่รัน ไม่เปลี่ยน
พฤติกรรม runtime ใด ๆ ประโยชน์คือคนอ่านโมดูลนี้ต่อ (chief/สายอื่น) จะไม่เข้าใจผิดว่า mixed
named+hostile body ยังไม่เคยถูกส่งจริง ทั้งที่ส่งมา 3 วันแล้ว

## ไฟล์ที่แตะ

```
src/pirateforce_foundation/field_mobs.py   [+20/-0, docstring correction เท่านั้น]
rounds/B_20260901_1741_qlrf4j_field_mobs_full_roster_override_wiring_doc_drift_fixed.md  [ใบนี้]
```

## ตัวเลขที่วัดได้

```
เทสเฉพาะไฟล์ที่แตะและโมดูลเกี่ยวโยง: 193 passed
  (tests/test_field_mobs.py + tests/test_mob_death.py + tests/test_mob_combat.py)
git diff --stat: 1 file changed, 20 insertions(+)
ast.parse: OK / .encode('cp874'): OK
สวีตเต็ม: 6350 passed, 327 skipped, 13717 subtests passed, 0 failed (198.26s)
```

## ยังไม่ได้พิสูจน์

- `GT-188` (P-1) ยังไม่มีคนเทส attended -- ไม่ใช่ตัวบล็อกสายตามกติกาใหม่ของ NOW.md
- ฝั่ง client ยังไม่มีใครยืนยันว่ามอนสเตอร์ named+hostile เรนเดอร์ถูกต้อง (สีชื่อ -- คนละเรื่องกับ
  wiring ที่รอบนี้แก้ prose)
- สวีตเต็มรันจบแล้ว 0 failed (ดูตัวเลขข้างบน) -- ไม่มีอะไรให้ตามต่อจากตัวเลขนี้

## CORE-REQUEST

ไม่มี

## เปิดใบให้สาย C

ไม่มี

-- LANE-B (COMBAT) รอบ `qlrf4j`
