# รอบ B_20260901_1436 (round `fbql13`)

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

ไม่มี -- รอบนี้เป็น docstring-only fix ใน `mob_combat.py` ไม่แตะพฤติกรรม/ไบต์ที่ส่งออก

## ต้นรอบ

1. อ่าน `pf_bridge/NOW.md`: ไมล์สโตนทั้งหมดยังพักตาม `PANYA-ORDER 20260901_0215` (ตรวจล่าสุดโดย
   COO 13:41+07:00, ยังเหมือนรอบ `ruigb0` ทุกตัวอักษร) -- P-1 เดินสายครบแล้วรอ `GT-188` attended,
   P-2/P-3 เป็นของสาย GM/RE ไม่ใช่ของสายนี้ · `GT-146` และใบเทสตีมอนทุกใบยังล็อกอยู่
2. ตรวจล็อก: ไม่มี PR `[LANE-B]` ค้างเปิดในทั้งสองรีโปตอนต้นรอบ (ตรวจด้วย GitHub API)
3. ตรวจกล่องจดหมาย `ADDRESSEE: LANE-B` ที่ยังไม่มี `.CONSUMED.txt` -- ไม่พบ (สะอาด)
4. ไม่มี CLAIM ของสายอื่นบล็อกหัวข้อที่หยิบ

## สรุป

เหมือนรอบ `ruigb0` ก่อนหน้า: P-1/P-2/P-3 ไม่มีพื้นผิวใหม่ให้สาย B และ `GT-146`/ใบเทสตีมอนทุกใบล็อกอยู่
เข้ากฎ F ข้อ ง (technical debt) อีกครั้ง กวาด `mob_combat.py` ต่อจากรอบก่อน พบว่า docstring ของ
`bar_frames()` (บล็อก `[UPDATE, round sifsfg, 2026-08-27]`) ยังชี้ว่า "the fix lives in
`mob_death.hostile_census_frames`" และบอกว่า `runtime.py` เรียกฟังก์ชันนั้นตรง ๆ -- แต่ตั้งแต่รอบ
`y9s0xo` (2026-08-29, `mob_scene_recompose.py`) `runtime.py` เปลี่ยนไปเรียก
`mob_scene_recompose.recompose_frames` แทน (scene-dispatched, เพิ่ม composer ของ scene 2)

ต่อท้ายด้วย `[UPDATE, round fbql13]` (ไม่ลบของเดิม) อธิบาย caller ปัจจุบัน -- **แก้สองรอบในรอบเดียว**:
ฉบับร่างแรกอ้างผิดว่าคอมเมนต์ `CORE-REQUEST-008` อยู่ใน `mob_combat.py` เอง (จริง ๆ อยู่ใน
`runtime.py:4301/4310`) และอ้างว่า `mob_death.hostile_census_frames` "เป็นแค่ประวัติศาสตร์" --
pf-adversary (agent จริง เรียกได้รอบนี้) จับได้ว่าอ้างผิด: `diag_multi_object_wiring.
hostile_census_frames` (ที่ `mob_scene_recompose` เรียกสำหรับ scene 1) มีสาขาแรก `if not objects:`
ที่ส่งต่อไปเรียก `mob_death.hostile_census_frames` ตรง ๆ ทุกครั้งที่ไม่มี diagnostic object ทำงาน
(ค่า default ของทุกแอคเคาต์ -- `self.diag_multi_objects = ()` ใน `runtime.py`) จึงแก้ฉบับสอง: ระบุ
ให้ถูกว่าฟังก์ชันนี้ยังเป็น terminal executor ของกรณีปกติ ถูกเรียกลึกลงไปอีกชั้นหนึ่ง ไม่ได้ถูกแทนที่

## pf-adversary

เรียก agent `pf-adversary` จริงรอบนี้ (มีให้เรียก ต่างจากรอบ `ruigb0`/`vzhc6s` ที่ไม่มี) -- พบ 2 ข้อบกพร่อง
ในฉบับร่างแรก (attribution ผิดไฟล์ + claim เกินจริงเรื่อง "history only") ทั้งสองแก้แล้วในฉบับที่ push
ยืนยันซ้ำด้วยการอ่าน `runtime.py:1206` (`self.diag_multi_objects = ()`) และ
`diag_multi_object_wiring.py:606-610` (pass-through เมื่อ `objects` ว่าง) เอง

## ตัวเลขที่วัดได้

```
python3 -m pytest tests/test_mob_combat.py tests/test_mob_scene_recompose.py -q
119 passed, 24 subtests passed (0.54s)
```

## ยังไม่ได้พิสูจน์

- `GT-188` (P-1) ยังไม่มีคนเทส attended
- P-2/P-3 ยังบล็อกภายนอก ไม่ใช่ของสายนี้
- การแก้นี้เป็น docstring-only ไม่มี claim ใหม่เรื่องพฤติกรรม wire/client

## CORE-REQUEST

ไม่มี (ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py`)

## ไฟล์ที่แตะ (2)

- `src/pirateforce_foundation/mob_combat.py` -- docstring `bar_frames()`, ต่อท้าย `[UPDATE, round
  fbql13]` แก้ไข caller ปัจจุบัน (ไม่ลบของเดิม)
- `rounds/B_20260901_1436_fbql13_mob-combat-bar-frames-caller-doc-drift.md` -- ใหม่ (ไฟล์นี้เอง)

PF-AUTOMERGE: v4
