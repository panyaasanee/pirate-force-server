# LANE-B round `ruigb0` (COMBAT)

เปิดรอบ 2026-09-01T13:3x+07:00, เนื้อรอบเขียน 2026-09-01T13:43+07:00 (scheduled, ไม่มีคนเฝ้าหน้าจอ)
Branch: `claude/zen-einstein-ruigb0`

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้แก้เฉพาะ docstring/comment/nonclaims (ข้อมูล prose ล้วน) ใน `mob_combat.py` ที่สาย B
เป็นเจ้าของ ไม่แตะ logic ใด ๆ ไม่แตะ `runtime.py`/`app.py` ไม่มี CORE-REQUEST ใหม่ P-1 ยังคง "เดินสาย
แล้ว รอ `GT-188` attended" เหมือนเดิมทุกข้อ ตามที่บันทึกไว้ในรอบ `hqzp16` ก่อนหน้า

## ต้นรอบ

1. ตรวจ `git log`/`git status`: HEAD ที่ branch นี้คือ `f096fbe` = `origin/main` (PR #470 ของรอบ
   `hqzp16` merge แล้ว), working tree สะอาด ไม่มีอะไรต้องกู้คืน
2. อ่าน `pf_bridge/NOW.md`/`CHIEF_CONTINUATION.md` ("ลำดับงานปัจจุบัน"): ไมล์สโตนพักตามคำสั่งเจ้าของ
   2026-09-01T02:15 · P-1 (ของดรอปอยู่บนพื้นนานพอ) เป็นของสาย B แต่เดินสายแล้วจริง (`app.py:890`,
   `mob_loot.py`, ยืนยันโดยรอบ `hqzp16`) รอ `GT-188` (`PENDING`) เท่านั้น ไม่มีพื้นผิวโค้ดใหม่ให้ทำ ·
   `GT-146`/ใบตีมอนทั้งหมดห้ามเข้าคิว attended จนกว่า P-1+P-2 จะปิด (P-2 บล็อกที่ RE-067/RE-155 — ของ
   สาย GM/RE ไม่ใช่ของสายนี้ ไม่แตะ)
3. ตรวจกล่องจดหมาย `pf_bridge/notes_to_chief`: ไม่มีจดหมาย `ADDRESSEE: LANE-B` ที่ยังไม่มี
   `.CONSUMED.txt` ค้างอยู่เลย (สะอาด, ตรวจซ้ำอีกครั้งก่อนปิดรอบด้วยคำสั่งเดียวกันในใบสั่งงาน)
4. อ่าน `CLIENT_RE_QUEUE.md` หาใบ `OPEN` ที่สาย B ตอบได้จาก source โดยไม่ต้อง capture ใหม่ — ใบเปิดจริง
   ที่เหลือ (RE-106 หัวใบค้าง, RE-137/RE-138 เขต Lane A, RE-155 บล็อกด้วย capture และเป็นเขต P-2 ที่
   ใบสั่งงานห้ามแตะ, RE-135 เป็นงาน tools/ ไม่ใช่ของสาย B) ไม่มีใบไหนเป็นงานที่ทำได้รอบนี้จริง
5. อ่านรอบล่าสุด 5 รอบของสาย B (`bdcmkf`, `vzhc6s`, `n3wqrt`, `4qwc1x`, `hqzp16`) ครบตามที่ใบสั่งงานขอ —
   NONCLAIM 15/16, Bg0015 death-ruling proposal + COO ruling ต่อสายแล้ว, R227 D5 docstrings ปิดแล้ว,
   HEARTBEAT-PRESERVE-001 แก้แล้ว — ไม่มีอะไรให้ทำซ้ำ

## รอบนี้ทำอะไร (กฎ F ข้อ ง: technical debt ที่ pf-adversary ชี้แนวทางมาแล้ว)

ไม่มีพื้นผิวใหม่จาก P-1/P-2/P-3 และไม่มีใบ RE เปิดที่ตอบได้จาก source รอบนี้ จึงกวาดหาข้อความ "false
now" ใน docstring ของโมดูลสาย B เอง (ชนิดบั๊กเดียวกับที่ `n3wqrt` ปิด R227 D5 และ `4qwc1x` แก้ตอนลง
ทะเบียน Bg0015 ruling) ด้วยการ grep หาคำยืนยันเชิงลบที่ผูกกับเหตุการณ์ที่มีวันที่ (`"has never been
observed"`, `"nobody has yet observed"`, `"queued and not yet run"`) ทั่วโมดูลของสาย B ทั้งหมด

**พบ 1 จุดจริงใน `mob_combat.py`** (ไม่มีโมดูลอื่นของสาย B พูดแบบเดียวกัน — grep ยืนยันแล้ว):
โมดูลนี้อ้างซ้ำสามที่ (module docstring 2 ย่อหน้า + `MOB_COMBAT_NONCLAIMS[0]` และ `[1]`) ว่า "a real
attack input has never been observed producing the EA7D ActionVital this driver reads" และ "GT-084,
queued and not yet run" — ทั้งสองข้อความนี้ **ผิดไปแล้วตั้งแต่ 2026-08-27T15:52-15:55+07:00**: ใบผล
`GT-084-R2` (`pf_bridge/archive/notes_to_chief_2026-08/20260827_1620_GT084R2-RESULT-PASS-hostile-
kill-full-wire-but-corpse-freezes-no-target-panel.md`, `OBSERVER_CONFIRMED` โดยเจ้าของเอง) บันทึกไว้
ตรง ๆ ว่าเจ้าของดับเบิลคลิก Tornado Eagle (template 31, field-mobs hostile body) ห้าครั้งจริง คอนโซล
พิมพ์ `MOB-COMBAT-001 hit: performer 0x10010001 -> target 0x201F` ห้าบรรทัด ครั้งที่ห้าเลือดถึงศูนย์
และตาย — คือ inbound EA7D ActionVital ที่ docstring บอกว่า "never been observed" นั้น **ถูกสังเกตแล้ว
จริงในรอบนั้น**

### แก้ตามธรรมเนียมโปรเจกต์ ([STALE ...][MEASURED ...] ต่อท้าย ไม่ลบของเดิม)

1. `mob_combat.py` module docstring ย่อหน้า "What is NOT proven..." (เดิมบรรทัด 79-86) — เติม block
   `[STALE as of GT-084-R2 ...][MEASURED, by console reading]` อ้างใบผลตรง ๆ พร้อมเลขบรรทัดคอนโซลที่
   วัดได้ (ตัว performer/target/เลขครั้ง)
2. ย่อหน้า "WHAT THE PLAYER SEES..." (เดิมบรรทัด 114-134, ซึ่งมี `[STALE][MEASURED]` ชั้นแรกอยู่แล้ว
   จากรอบ `mdj01v` ที่ปิดคำถามเรื่อง wiring line — แต่ประโยคสุดท้ายของชั้นนั้นเองก็ค้างผิดต่อ) — เติม
   `[STALE][MEASURED]` ชั้นที่สองทับชั้นแรก (multi-layer ตามแบบที่ RE-067 annotation chain เคยทำ)
3. `MOB_COMBAT_NONCLAIMS[0]` (inbound-half claim) — เติม `[STALE][MEASURED]` ในสตริงเดียวกัน ระบุ
   ขอบเขตที่ยังไม่พิสูจน์จริง (auto-attack cadence, miss, out-of-range — หนึ่งตัวหนึ่งรอบไม่ใช่บทพิสูจน์
   ทั่วไป)
4. `MOB_COMBAT_NONCLAIMS[1]` (wiring-line claim) — ประโยคอ้างอิงกลับไปที่ nonclaim ตัวแรก ("the inbound
   half... is still unproven") ก็ค้างผิดตามไปด้วย เติม `[STALE][MEASURED]` ชั้นที่สองเช่นกัน ชี้กลับไป
   nonclaim ตัวแรกให้อ่าน scope ล่าสุด

**ไม่แตะ**: nonclaim เรื่องสีชื่อ (RE-067/GT-084/RIDER-084-A, เดิมบรรทัด ~388-394) — อยู่ในเขต P-2 ที่
ใบสั่งงานห้ามแตะ (บล็อกด้วย RE-067/RE-155, ของสาย GM/RE) ถึงแม้ GT-084-R2 จะให้ข้อมูลสีจริงมาแล้ว
(ชมพู ไม่ใช่ตามเกณฑ์เดิม) การเคาะว่า nonclaim นั้นควรเขียนใหม่อย่างไรเป็นคำถามของสายอื่น ไม่ใช่ของรอบนี้
· ไม่แตะ nonclaim "corpse itself has never been watched land" — ยังจริงอยู่ (GT-084-R2 เห็นศพ **ไม่ล้ม**
ค้างท่าลอย ไม่ใช่ "เห็นศพล้มลงพื้น" คนละความหมาย)

### บั๊กที่จับได้เองระหว่างรอบ (ก่อน commit)

ร่างแรกอ้างพาธจดหมายผิด: เขียน `pf_bridge/notes_to_chief/archive/notes_to_chief_2026-08/...`
(พาธที่ไม่มีอยู่จริง — `test -f` ล้ม) พาธจริงคือ `pf_bridge/archive/notes_to_chief_2026-08/...`
(ไม่มี `notes_to_chief/` ซ้อนอยู่ข้างใน `archive/`) ตรวจพบเองด้วยการ `test -f`/`find` ก่อน commit
แก้ด้วย `sed` ทั้งสองจุดที่อ้างพาธนี้ (บรรทัด 94, 155 ของไฟล์หลังแก้)

### ไฟล์ pin ที่ต้อง regenerate

`scenarios/combat_first_hit_001.json` ไม่ใช่ scenario (ประกาศ `not_a_scenario: true` ในตัวเอง) แต่เป็น
pin ตัวเลขที่คอมมิตไว้ ผลิตจาก `mob_combat.pin_document(legacy, mob_combat.pin_subject())` ตรง ๆ —
`nonclaims` เป็นหนึ่งในฟิลด์ที่ pin นี้ echo ค่าจาก `MOB_COMBAT_NONCLAIMS` จริง ดังนั้นการแก้ nonclaims
ต้อง regenerate ไฟล์นี้ด้วย (สคริปต์เดียวกับที่เทสใช้เปรียบเทียบ ไม่ได้พิมพ์มือ) รันแล้วยืนยัน `git diff`
มีแค่ 2 บรรทัดเปลี่ยน (ตรงกับ nonclaim 2 ตัวที่แก้พอดี ไม่มีตัวเลข/ฟิลด์อื่นขยับ)

## เทส

```
เฉพาะไฟล์ที่แตะโดยตรง: tests/test_mob_combat.py -> 57 passed
เกี่ยวข้อง (cross-check): + test_mob_death.py + test_mob_combat_cadence_wiring.py
  + test_mob_combat_bg0015_gates.py + test_mob_death_bg0015_ruling_proposal.py
  + test_mob_death_wired_widening.py -> 208 passed, 177 subtests passed, 0 failed
สวีตเต็ม: 6265 passed, 327 skipped, 13166 subtests passed, 0 failed (236.59s)
```

รอบแรกของ `test_mob_combat.py::test_the_committed_pin_is_what_the_code_produces` แดงจริงก่อน
regenerate pin (ยืนยันว่าเทสจับ text drift จริง ไม่ใช่แค่ผ่านเฉยๆ) -> regenerate แล้วเขียว

## pf-adversary

ไม่มี pf-adversary agent แยกให้เรียกรอบนี้ (เหมือนรอบ `vzhc6s`) ทำเองตามที่ pf-adversary จะทำ:
1. grep คำยืนยันเชิงลบทั่วโมดูลสาย B ทั้งหมด (`mob_*.py`, `field_mob*.py`, `lane_hooks/lane_b_*.py`)
   ก่อนแก้ ยืนยันว่า `mob_combat.py` เป็นจุดเดียวที่พูดแบบนี้เกี่ยวกับ GT-084 inbound-attack — ไม่มีจุดอื่น
2. cross-check ข้อความที่จะเขียนกับใบผลต้นทางคำต่อคำ (performer id, target id, template, จำนวนครั้ง,
   OBSERVER_CONFIRMED timestamp) ก่อน commit — จับพาธจดหมายผิดได้ตรงนี้เอง (ดูหัวข้อข้างบน) แก้แล้ว
3. ยืนยันด้วย `git diff --check` ว่าไม่มี whitespace error
4. ยืนยัน `py_compile` ผ่าน และการแก้เป็น string literal ล้วน (อ่าน diff เต็มด้วยตา ไม่มีบรรทัด logic/
   control-flow เปลี่ยนเลยแม้แต่บรรทัดเดียว)
5. ยืนยัน cp874/ascii encodability ของทั้งสองไฟล์ที่แตะ
6. ยืนยันว่าไม่แตะ nonclaim เรื่องสีชื่อ (เขต P-2 ที่ใบสั่งงานห้าม) ทั้งที่ก็เป็น "false-ish" เหมือนกัน —
   จงใจเว้นไว้ตามขอบเขตที่สั่งมา ไม่ใช่พลาด
7. รันสวีตเต็มก่อน/หลัง (ตัวเลขข้างบน) ไม่มี regression

## ตัวเลขที่วัดได้

```
ไฟล์ที่แตะ (2 src/scenario + 1 round file):
  src/pirateforce_foundation/mob_combat.py          -- แก้ 2 docstring paragraph + 2 nonclaims,
                                                        ไม่แตะ logic/control-flow
  scenarios/combat_first_hit_001.json               -- regenerate จาก pin_document() จริง
                                                        (2 บรรทัดเปลี่ยน ตรงกับ nonclaim 2 ตัว)
  rounds/B_20260901_1343_ruigb0_mob-combat-gt084-inbound-claim-corrected.md  -- ไฟล์นี้
ข้อความ "false now" ที่แก้: 4 จุด (2 docstring paragraph + nonclaims[0] + nonclaims[1])
เทสที่รัน: 208 targeted (0 failed) / 6265 สวีตเต็ม (0 failed)
```

## ยังไม่ได้พิสูจน์

- ขอบเขตที่แก้ยังคง "unproven" ไว้ตรง ๆ ตามที่ GT-084-R2 วัดได้จริง: hostile body อื่นนอกจาก Tornado
  Eagle, auto-attack cadence, miss, out-of-range click — ยังไม่มีการวัดใดครอบคลุมกรณีเหล่านี้
- P-1 ยังรอ `GT-188` attended (ไม่เปลี่ยนจากที่บันทึกไว้)
- nonclaim เรื่องสีชื่อใน `mob_combat.py` (บล็อก RE-067/GT-084/RIDER-084-A) ยังไม่แก้ตามเจตนา — เป็น
  ของเขต P-2/สาย GM ไม่ใช่ของรอบนี้

## CORE-REQUEST

ไม่มี

## เปิดใบให้สาย C

ไม่มี

-- LANE-B (COMBAT) รอบ `ruigb0`
