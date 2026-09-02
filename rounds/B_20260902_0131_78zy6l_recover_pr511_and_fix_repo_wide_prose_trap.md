# Round B_20260902_0131 (branch 78zy6l) — LANE-B (COMBAT), scheduled round

เริ่ม 2026-09-02T01:31+07:00 · เขียนไฟล์นี้ 2026-09-02T01:4x+07:00
(เวลาจากคำสั่ง `TZ=Asia/Bangkok date` ทุกจุด)

รายงานเต็มของรอบนี้อยู่ที่
`pf_bridge/rounds/B_20260902_0131_78zy6l_recover_pr511_and_fix_repo_wide_prose_trap.md`
ไฟล์นี้เก็บเฉพาะส่วนที่เป็นของรีโปนี้

## รอบนี้ทำอะไรในรีโปนี้ (2 ไฟล์ ไม่แตะ `src/` เลย)

### 1. `tests/test_inventory.py` — กู้กลับมา verbatim

หายไปทั้งรอบพร้อม PR #511 (closed, `merged=false`) งานยังอยู่บน branch
`claude/zen-einstein-i7cwdh` เท่านั้น ไม่เคยขึ้น `main` — 458 บรรทัด, 47 เทสตรงของ
`src/pirateforce_foundation/inventory.py` (โมเดล Backpack ของ BUILD-006/M5) รวมเทสของ
`parse_merge_candidate` / `is_exact_merge_request` ที่ `runtime.py` เรียกจริงทุก ItemOperate
request แต่ไม่เคยมีไฟล์เทสไหนอ้างชื่อมาก่อน · ดึงมาโดยไม่แก้เนื้อหาแม้แต่บรรทัดเดียว

### 2. `tests/test_gate2_bag_admission_wiring.py` — ปิดกับดักที่ทำให้รอบนั้นหาย

`test_nothing_outside_the_package_calls_it_either` รัน `git grep` หาชื่อโมดูล gate-2 ทั้งรีโป
แล้วบังคับ allowlist กับ **ทุกไฟล์ที่โผล่มา** ไฟล์ใหม่ของ PR #511 แค่ **เอ่ยชื่อไฟล์พี่น้องสองใบใน
docstring** ก็ติด grep → เทสแดง → gate แดง (run `33522539202`, ช่อง `pytest_subset exit=1`
ช่องเดียวในตาราง) → reaper ปิด PR ทั้งใบ ทั้งที่ไฟล์นั้นไม่ import ไม่เรียก ไม่แตะ predicate เลย

แผลเป็นสองรอยในตัวเทสเองบอกว่าเคยเสียรอบไปกับกลไกเดียวกันมาแล้ว (รอบ `uq2lxw`, และ entry ของ
chief รอบ `4gqnwm`) วิธีแก้เดิมคือเติมชื่อไฟล์เข้า allowlist หลังเกิดเหตุ ซึ่งไม่ปิดกับดัก

**สิ่งที่เปลี่ยน** (allowlist เดิมไม่ถูกลบ ยังเป็นทะเบียนของผู้เรียกจริงต่อไป):

- `PROSE_SUFFIXES = {".md", ".txt"}` ผ่านโดยกฎ — markdown ไม่ถูกรันโดยอะไรในรีโปนี้ (ตรวจว่าไม่มี
  doctest runner ก่อนเขียน) **ไฟล์รอบนี้เองคือหลักฐาน**: มันเอ่ยชื่อโมดูลนั้นในภาษาไทย และ gate
  ต้องเขียว
- `_names_bag_admission_as_code(path)` — คืนเหตุผลถ้าไฟล์ `.py` เข้าถึง predicate จริง คืน `None`
  ถ้าทุกจุดที่เอ่ยเป็น docstring/คอมเมนต์ กฎเดียวกับที่ไฟล์นี้ใช้กับตัวแพ็กเกจอยู่แล้ว: identifier ใน
  AST · สตริงที่มีชื่อโมดูลในตำแหน่งที่ไม่ใช่ docstring (ปิด `import_module` / `getattr` / `sys.modules[...]` และปิด `MODULE = "..."` ที่ผูกชื่อไว้ก่อนแล้วค่อย import ทีหลัง ซึ่งการเช็คแบบ "เฉพาะในคอลล์" หลุด) ·
  import ตรง · parse ไม่ผ่าน = ไม่ผ่าน (ไม่ปล่อยเงียบ)
- คลาสเทสใหม่ `ProseIsNotACallerButEveryDynamicRouteStillIs` — 10 เทส เขียนไฟล์ `.py` จริงชั่วคราว
  แล้วถามฟังก์ชัน ไม่ใช่ assert ลอย ๆ · เทสสุดท้ายถามกับไฟล์จริงที่รอบนี้กู้กลับมา

## ตัวเลขที่วัดได้

```
tests/test_gate2_bag_admission_wiring.py + tests/test_inventory.py : 82 passed, 2 subtests
สวีตเต็มทั้งรีโป : 6673 passed, 327 skipped, 13778 subtests passed, 0 failed (182.96s)
```

🔴 `git add` ทั้งสองไฟล์ **ก่อน** รันสวีต ตามแผลเป็นในตัวเทสเอง (`git grep` อ่าน INDEX)

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ยังไม่มีอะไรต่างบนจอ** — ไม่มีบรรทัดใน `src/` ถูกแก้ ผลทางอ้อมคือใบเทส `GT-198` (ของตกพื้นมีโมเดล
3D ไหม) บูตได้แล้วหลังแก้หัวใบ+คำสั่ง RECHECK ที่ให้ผลลบเสมอ (ดูรายงานฝั่ง `pf_bridge`)

## CORE-REQUEST ถึง chief (ย้ำใบเดิมจากรอบ `4ztr6t` ไม่ใช่ใบใหม่)

P-1 ขยับไม่ได้จนกว่า `runtime.py` (ไฟล์ของ chief) จะเรียกสองจุดนี้:

1. `hostile_census_frames(..., transitioning=(scene, actor_identity))` — `runtime.py:4743-4760`
2. `cell.reconcile_scene_transition()` ตรงจุด scene-sync — `runtime.py:4111-4191`

## pf-adversary

**เรียกจริงและกลับมาแล้วก่อน commit** (`AGENTS.md` ข้อ 107) — เจอ **9 ข้อ HIGH สามข้อ**
วัดจริงทุกข้อในเวิร์กทรีแยกพร้อม control กับโค้ดก่อนแก้ · **แก้ครบทั้งเก้าข้อในรอบนี้** ก่อน commit
รายละเอียดเต็มอยู่ในไฟล์รอบฝั่ง `pf_bridge` · หัวข้อที่สำคัญที่สุดสามข้อ:

- **D1** ร่างก่อนหน้ายังหลุดผู้เรียกจริง: ทำ module docstring ให้เป็น path ของโมดูล แล้ว
  `import_module(__doc__)` → แก้ด้วย `DYNAMIC_LOOKUP_NAMES` (docstring เป็น prose ได้เฉพาะในไฟล์
  ที่ไม่มีเครื่องมือแปลงสตริงเป็นโมดูลเลย)
- **D2** คลาสของบั๊ก #511 ยังไม่ปิด: ข้อความ assertion / ลิสต์ชื่อไฟล์ ยังทำ gate แดง → กฎใหม่ปิดทั้งสองด้าน
- **D3** สองบรรทัดที่ทำงานจริงของสแกนไม่เคยรัน (mutant สามตัวยังเขียว) → แยกสแกนเป็นฟังก์ชัน
  (`_repo_wide_hits` / `_classify_repo_wide_hits`) + คลาสเทสใหม่ที่ปลูกไฟล์จริงแล้วขับสแกน
  **วัดซ้ำ: mutant ทั้งสามตัวตายหมด**

อีกหกข้อ: returncode ของ `git grep` (D4), BOM → `utf-8-sig` (D5), `core.quotePath`/`-z` (D6),
`.pyw`/`.pyi` + `.lower()` (D7), ตัดการผูกกับ prose ของ `test_inventory.py` และการทิ้งไฟล์ 458
บรรทัดลง cp874 (D8), เอา `.txt` ออกจากชุด prose เพราะในรีโปนี้ `.txt` คือ **ล็อกรอบ** (D9) ·
D10 เป็น exposure ไม่ใช่ defect ไม่แก้

stage ทีละไฟล์ ไม่ใช้ `git add -A` และอ่าน `git diff --cached` ก่อน commit (`AGENTS.md` ข้อ 104)
