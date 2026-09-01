# LANE-B round `i7cwdh` -- inventory.py ไม่มี tests/test_inventory.py ของตัวเอง
มาตลอด ทั้งที่ 13 ไฟล์เทสอื่นใช้ symbol จากมันโดยอ้อม และสองฟังก์ชัน
(`parse_merge_candidate`/`is_exact_merge_request`) ที่ `runtime.py` เรียกทุกอินบาวด์
ItemOperate request ไม่เคยมีเทสอ้างถึงเลยแม้แต่บรรทัดเดียว

## ต้นรอบ -- ตรวจ P-1/P-2/P-3, กล่องจดหมาย, ใบ CLAIM, สถานะ push ของรอบก่อน

- `pirate-force-server` checkout จาก `origin/main` tip (`dc311fd`, merge PR #507 ของรอบ
  `focused-turing-69cabr`) -- branch `claude/zen-einstein-i7cwdh` ตรงกับ origin/main พอดี ไม่มี PR
  `[LANE-B]` ค้างเปิด
- `pf_bridge/NOW.md` (ตรวจล่าสุดโดย COO 2026-09-01 17:43): P-1/P-2/P-3 ยังพักตาม PANYA-ORDER
  20260901_0215 -- P-1 (drop ค้างพื้น) โค้ด+เทสจบแล้ว รอ `GT-188` attended อย่างเดียว, P-2 (สีชื่อมอนสเตอร์)
  Codex ปิด static checkpoint แล้ว ยังไม่มีโค้ดเปิดใช้ (ต่อไปคือ P0-3 quest mark, คนละสายกับ combat) --
  ทั้งคู่ไม่ใช่พื้นผิวใหม่ให้สาย B รอบนี้ตามที่ยืนยันซ้ำแล้วสองรอบก่อนหน้า
- 🔴 `ห้ามทำจนกว่า P-1 กับ P-2 จะปิด -- GT-146 และใบเทสตีมอนทุกใบ` ยังบังคับ -- รอบนี้ไม่แตะ GT-146 หรือ
  ใบเทส "ตีมอน" ใด ๆ ทั้งสิ้น
- ไมล์สโตน BUILD-004/005/006 ยังพักตาม PANYA-ORDER 20260901_0215 -- รอบนี้ไม่เพิ่มพื้นผิว build ใหม่
  ให้ไมล์สโตนไหน ไม่แก้ `scenarios/combat_*.json` หรือ `scenarios/*pickup*`/`*loot*`
- 🔴 กฎ F: รอบก่อนหน้า (`unkjpn`, 2026-09-01T19:41+07:00) push จดหมายไปที่ pf_bridge main สำเร็จ
  (commit `f1b6089`) แต่ไฟล์ `rounds/B_*_unkjpn_*.md` คู่กันในฝั่ง `pirate-force-server` ไม่เคย push ขึ้น
  origin/main เลย -- ตรวจแล้วด้วย `git log --all --oneline -- 'rounds/B_*unkjpn*'` ว่างเปล่า -- รอบนั้น
  เนื้อหาเองก็เป็นรอบเปล่า (ไม่แตะ source, ไมล์สโตนพัก, ไม่มี mailbox item) และระบุเองว่า "รอบหน้า...
  จะหยิบ backlog/technical debt ตามกฎ" -- **รอบนี้ต้องหางานจริงมาทำ ห้ามเป็นรอบเปล่ารอบที่สาม**
- กล่องจดหมาย `notes_to_chief/`: ตรวจไฟล์ `ADDRESSEE:.*LANE-B` / `TO-LANE-B` / `KA1B` ที่ยังไม่มี
  `.CONSUMED.txt` คู่กัน พบ **หนึ่งใบใหม่ที่ยังไม่ถูกอ่านโดยรอบไหนมาก่อน**:
  `20260901_2015_KA1B-TO-LANE-B-drop-model-selector-field-is-not-on-our-wire.md` (ka1-B, 20:15+07,
  หลังรอบ `unkjpn` จบพอดี) -- อ่านแล้ว, สรุปด้านล่าง (หัวข้อ "จดหมายที่พบแต่ไม่ได้สร้างโค้ดจากมัน")
- ไม่มี `*CLAIM*` ที่ยัง active เกี่ยวกับพื้นผิวที่รอบนี้แตะ (`inventory.py`, `tests/test_inventory.py`)
- ใบ `20260901_1838_LANE-B-REPLY-re157-job2-scope-gap-option-c-spec.md` (รอบก่อนหน้าของสายนี้เอง)
  ยังไม่มี `.CONSUMED.txt` -- เป็น CORE-REQUEST สเปกสองจุดใน `runtime.py` (travel-gate crossing +
  M2 crossing ไม่ clear `mob_combat_announced_membership`) รอ chief หยิบ ไม่ใช่งานรอบนี้ (เขียนสเปก
  จบแล้วโดยรอบก่อน, ไฟล์ที่ต้องแก้เป็นของ chief ทั้งคู่)

## จดหมายที่พบแต่ไม่ได้สร้างโค้ดจากมัน (ตัดสินใจ, ไม่ใช่ละเลย)

`20260901_2015_KA1B-TO-LANE-B-...`: Codex ปิด static ได้ว่า `n_DROPMODEL_TYPE` (client ground-drop
model selector) อ่านจากช่องที่ `mob_loot.py`'s element mask `0x12` (เฉพาะ `0x02`+`0x10`) **ไม่เคยส่ง**
เลย (bit `0x04`/`0x08`/`0x20`) พร้อมวิธีพิสูจน์ผิดราคาถูก (เพิ่มทีละ bit, สาม mask candidate)

**ทำไมไม่สร้างโค้ดจากใบนี้รอบนี้**: ข้อ ③ ของใบเป็น **[สมมติฐาน] ที่ผู้เขียนใบเองประกาศชัด** ("ผมประกอบเอง
ยังไม่มีใครพิสูจน์") และ ⑤ ย้ำว่าแถวของ Codex ทั้งหมดเป็นชั้น IMAGE ล้วน "ยังไม่มีหลักฐานว่าเห็นบนจอ"
การส่ง element mask ใหม่เข้า production path (ไม่ใช่ scenario ทดลอง) โดยไม่มีใครยืนยันบนจอเลยจะเป็นการ
"invent a row the client's own tables do not have" ผิดกติกา fail-closed ของสาย -- และการต่อ
`ground_loot_hypothesis.py` (HYP-PF-032, `production_allowed = False`, `test_only: True`) ด้วย mask
ใหม่สามตัวตามที่ใบเสนอ ก็เป็นการเพิ่มพื้นผิว **probe** อีกชุด ไม่ใช่ default-runtime path -- ตรงข้ามกับกติกา
ของสายนี้ที่ให้ priority กับงานที่ทำงานได้โดยไม่ต้องมีแฟล็ก ไม่ใช่ probe ใหม่ ไม่มีการรันไคลเอนต์จริงในเซสชันนี้
ให้พิสูจน์ผิด/ถูกได้ด้วย จึงตัดสินใจ **ไม่แตะ** `mob_loot.py`/`ground_loot_hypothesis.py` รอบนี้ -- ปล่อยใบนี้ไว้
ให้ COO/chief ตัดสินว่าจะเปิด GT ใหม่ให้ Panya รันการทดลองสามขั้นเองหรือไม่ (ไม่ใช่คำถามที่ code เปลี่ยน
พฤติกรรมได้ตอบเอง) ไม่เปิดใบสาย C ใหม่ (RE ฝั่ง static ปิดแล้วโดย Codex; สิ่งที่เหลือคือรอบ attended ไม่ใช่
RE เพิ่ม)

## กฎ F -- ปิดหนี้เทคนิคจริงหนึ่งจุด: `tests/test_inventory.py` (ไฟล์ใหม่)

**สิ่งที่พบ**: `src/pirateforce_foundation/inventory.py` (549 บรรทัด) เป็นโมดูล BUILD-006/M5 หลัก --
สองประตูกำแพง (`require_backpack_shape`/`require_known_backpack`), การกลายพันธุ์ที่ควบคุมสามแบบ
(HYP-PF-010/017/018: move/swap/merge), ตัวประกอบไวร์ ItemOperate สามตัว, และ `make_backpack_attr`
ตัวเข้ารหัสไวร์เอง -- **ไม่มี `tests/test_inventory.py` มาตั้งแต่แรกเลย** (`ls tests/test_inventory.py`
-> ไม่มีไฟล์) ทั้งที่ 13 ไฟล์เทสอื่นอิมพอร์ต symbol จากมัน (ยืนยันด้วย
`grep -rln "from pirateforce_foundation.inventory\|import inventory" tests/`) แต่ทุกไฟล์ใช้มันผ่าน
"เลนส์" ของฟีเจอร์ตัวเองเท่านั้น ไม่มีไฟล์ไหน pin สัญญาของโมดูลนี้เองโดยตรง

**ช่องที่แคบกว่านั้นและสำคัญกว่า**: `parse_merge_candidate`/`is_exact_merge_request` -- สองฟังก์ชันที่
`runtime.py` เรียกจริงบนทุก inbound ItemOperate request (`:1459` ใน `_dispatch_v111_persistent_merge`,
`:6999` ก่อนหน้านั้น) เพื่อตัดสินว่า V111 persistent-merge dispatch จะเปิดหรือไม่ -- **ไม่มีเทสไฟล์ไหน
อ้างถึงชื่อสองฟังก์ชันนี้เลยก่อนรอบนี้** (`grep -rln "is_exact_merge_request\|parse_merge_candidate"
tests/` ก่อนรอบนี้ว่างเปล่า, ตรวจแล้วก่อนเขียน)

**สิ่งที่สร้าง**: `tests/test_inventory.py` (ไฟล์ใหม่, ASCII ล้วน) -- 47 เทส, 9 คลาส:
`RequireBackpackShapeTests` (9), `RequireKnownBackpackTests` (3), `IsUnmovedBaselineTests` (3),
`MoveKnownItemToFreeSlotTests` (5), `SwapKnownItemWithOccupiedSlotTests` (4),
`MergeKnownItemIntoOccupiedSlotTests` (6), `WireEncodersTests` (9), `MergeRequestParsingTests` (5+
setUpClass) -- ครอบทุกฟังก์ชัน public ของโมดูล ทั้ง success path และ error path
(`KeyError`/`FileExistsError`/`LookupError`/`ValueError` -- ตรวจว่า exception type ไหนออกกรณีไหน),
พร้อมพาร์สไบต์จริงของ `V111_MERGE_REQUEST_PC` ผ่าน `legacy.parse_outer()` ตัวจริง (ไม่ mock) แล้ว mutate
ทีละไบต์ (nested_id, operation value, outer_mask) เพื่อยืนยันว่า `parse_merge_candidate`/
`is_exact_merge_request` แยกกรณีถูกจริง ไม่ใช่แค่คืนค่าคงที่

**ผลกระทบพฤติกรรม**: **ไม่มี** -- ไฟล์นี้เป็นเทสล้วน ไม่แก้ `src/` แม้แต่บรรทัดเดียว
(`git diff --stat` ยืนยันด้านล่าง: ไฟล์เดียว, untracked, ไม่มีไฟล์อื่นถูกแก้)

## ตรวจก่อน push (self-review, ไม่มี Task/Agent tool ให้เรียก pf-adversary subagent ตรงในเซสชันนี้)

1. **ตรวจ byte offset ของ `V111_MERGE_REQUEST_PC` ด้วยมือก่อนเขียนเทส mutate**: ไม่เชื่อ prose ของ
   `inventory.py`'s comment ("first byte of the nested payload") ตรงๆ -- อ่าน `parse_outer`/
   `Cursor.u8` จริงใน `current/pf_login_game_server_v141.py:2818-2931` แล้วคำนวณ index ทีละไบต์ด้วยมือ
   (`nested_id` อยู่ byte 16-17 ไม่ใช่ 20-21, operation VALUE อยู่ byte 21 ไม่ใช่ 23, `outer_mask` VALUE
   อยู่ byte 11 ไม่ใช่ 7 อย่างที่ draft แรกของเทสเขียนผิด) แล้วยืนยันด้วย python one-liner จริงก่อนวาง
   ลงเทส (`hex(pc[16] | pc[17]<<8) == '0x4bed' == ITEM_OPERATE_REQ_VITAL` ยืนยันแล้ว) -- ป้องกัน
   เทสที่ผ่านโดยบังเอิญเพราะ mutate ไบต์ผิดตำแหน่งแล้วดันไม่กระทบอะไร
2. `test_a_trailing_byte_is_still_a_candidate...`: ตรวจโค้ดจริงว่าทำไมถึงยังเป็น candidate --
   `parse_merge_candidate` เช็ค `payload.startswith(V111_MERGE_PAYLOAD)` ก่อนเรียก
   `legacy.parse_item_operate_req` เสมอ ดังนั้นไบต์ต่อท้ายไม่ทำให้ตกไปเรียก parser ที่จะ raise
   จาก trailing byte -- นี่คือพฤติกรรมจริงของโค้ด ไม่ใช่ assumption ของเทส (อ่าน `inventory.py:520-536`
   ตรง ๆ ก่อนเขียน assertion)
3. `test_make_backpack_attr_refuses_a_frozen_constant_drift`: draft แรกใช้คลาสมี `__getattr__`
   delegate ไปยัง legacy จริง ซึ่ง**ไม่ทำงานตามที่ตั้งใจ** เพราะ class attribute ที่ประกาศตรงจะบัง
   `__getattr__` ไม่ให้ถูกเรียกสำหรับ attribute อื่นที่ต้องการให้ "ผิด" -- แก้เป็น `SimpleNamespace`
   ที่กำหนดค่าตรงทุกตัวที่ `make_backpack_attr`'s required dict เช็ค ยกเว้นตัวเดียว (`V103_ITEM_TEMPLATE`)
   ที่ตั้งใจให้ผิด แล้วรันจริงยืนยันว่า raise `ValueError` -- พบบั๊กของ draft ตัวเองก่อน commit ไม่ใช่
   หลัง
4. รันเฉพาะไฟล์ใหม่ก่อน: `python3 -m pytest tests/test_inventory.py -q` -> **47 passed**
5. รันร่วมกับทุกไฟล์เทสที่แตะ `inventory.py`/`mob_pickup.py` โดยตรงหรืออ้อม เพื่อยืนยันไม่มี test ไหน
   pin ค่าที่รอบนี้แตะ (ไม่มี เพราะไม่แตะ src/) แต่ก็รันเผื่อ side effect จาก import ใหม่:
   `pytest tests/test_inventory.py tests/test_mob_pickup.py tests/test_item_lifecycle.py
   tests/test_item_move_capture.py tests/test_item_move_hypothesis.py
   tests/test_item_move_generalized.py tests/test_item_merge_hypothesis.py
   tests/test_item_swap_hypothesis.py tests/test_bag_admission.py
   tests/test_gate2_bag_admission_wiring.py tests/test_mob_pickup_persist.py -q`
   -> **291 passed, 1017 subtests passed**
6. `ast.parse()` + `.encode('cp874')` ผ่านทั้งไฟล์ใหม่ -- ไฟล์เป็น ASCII ล้วน (ไม่มีอักขระไทย/emoji/CJK)
7. `git status`/`git diff --stat` -- ไฟล์เดียว `tests/test_inventory.py` (untracked, ใหม่ทั้งไฟล์),
   ไม่มีไฟล์ `src/` ไหนถูกแก้เลย
8. `pytest tests/` เต็ม (รันพื้นหลัง เกิน timeout ปกติของคำสั่งเดี่ยว, ตามด้วย poll จน exit code 0):
   **6545 passed, 327 skipped, 13766 subtests passed, 0 failed (176.17s)** -- **0 failed คือตัวเลขที่
   สำคัญที่สุด**: ไม่มี regression จากไฟล์ใหม่นี้เลย (เทสเก่าทุกตัวยังผ่านเหมือนเดิม บวก 47 เทสใหม่)
9. ตรวจว่าไม่มีไฟล์ `runtime.py`/`app.py`/`current/pf_login_game_server_v141.py`/`scenarios/world_*.json`
   ถูกแตะ -- ยืนยันจาก `git diff --stat` ข้อ 7 (ไฟล์เดียว ไม่ใช่ไฟล์เหล่านั้น)

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้เป็นการปิดหนี้เทคนิค (เทสตรงของ `inventory.py`) ล้วน ไม่แก้ `src/` แม้แต่บรรทัดเดียว
จึงไม่มีพฤติกรรม runtime ใดเปลี่ยน -- ประโยชน์คือรอบต่อไปที่แก้ `inventory.py` (move/swap/merge/
encoder/merge-request-parsing) จะมีเทสตรงจับ regression แทนที่จะพังเงียบ ๆ สามชั้นถัดไปใน
`mob_pickup.py`/`test_item_lifecycle.py`/`runtime.py`'s dispatch เท่านั้น

## ไฟล์ที่แตะ

```
tests/test_inventory.py                                                [ไฟล์ใหม่, +416 บรรทัด, 47 เทส]
rounds/B_20260901_2150_i7cwdh_inventory_direct_unit_tests.md            [ใบนี้]
```

รวม **1 ไฟล์ใหม่ใน `src/`/`tests/`** (ไม่มีไฟล์ `src/` ถูกแก้)

## ตัวเลขที่วัดได้

```
เทสไฟล์ใหม่เดี่ยว: 47 passed (tests/test_inventory.py)
เทสไฟล์ที่แตะ inventory.py โดยตรง/อ้อมทั้งหมด (11 ไฟล์): 291 passed, 1017 subtests passed
git diff --stat: 1 file changed (untracked, new), +416/-0
ast.parse: OK / .encode('cp874'): OK (ASCII ล้วน)
สวีตเต็ม: 6545 passed, 327 skipped, 13766 subtests passed, 0 failed (176.17s)
```

## ยังไม่ได้พิสูจน์

- `GT-188` (P-1) ยังไม่มีคนเทส attended -- ไม่ใช่ตัวบล็อกสายตามกติกาใหม่ของ NOW.md
- ใบ `20260901_2015_KA1B-TO-LANE-B-drop-model-selector-...` ยังไม่มีใครยืนยันบนจอ (ดูหัวข้อด้านบน) --
  รอบนี้ไม่สร้างโค้ดจากมัน ทิ้งไว้ให้ COO/chief ตัดสินใจว่าจะเปิด GT attended experiment หรือไม่
- CORE-REQUEST ของรอบก่อนหน้า (ใบ `1838`, travel-gate/M2-crossing membership clear) ยังไม่มี
  `.CONSUMED.txt` -- ยังรอ chief หยิบ ไม่ใช่ของค้างรอบนี้

## CORE-REQUEST

ไม่มี (รอบนี้ไม่แตะ `runtime.py`/`app.py`)

## เปิดใบให้สาย C

ไม่มี

-- LANE-B (COMBAT) รอบ `i7cwdh`
