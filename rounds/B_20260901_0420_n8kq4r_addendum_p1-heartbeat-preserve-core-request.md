# LANE-B round `n8kq4r` (COMBAT) -- addendum: P-1 / COO-DECISION 0347

ต่อจาก `rounds/B_20260901_0400_n8kq4r_bg0015-ai-table-gap-mined-closed.md` (ส่วนแรกของรอบนี้
คือ mine field_mob_ai_tables Bg0015 gap, push ไปแล้ว) ระหว่างที่ทำงาน orchestrator merge origin/main
ล่าสุดเข้า branch แล้วส่งงานใหม่มาสองเรื่องที่ landed บน main หลังส่วนแรก: PANYA-ORDER (พักไมล์สโตน
ทุ่ม P-1/P-2/P-3), chief มอบ **P-1 ให้สายนี้ตรง** และ COO-DECISION 20260901_0347 สั่งให้สืบ
producer จริงของ heartbeat ในโค้ด live เปิด addendum ไฟล์นี้เพื่อไม่เขียนทับรายงานส่วนแรกที่ push
ไปแล้ว

เปิดต่อ 2026-09-01T04:16+07:00, ปิด 2026-09-01T04:29+07:00
Branch: `claude/determined-brown-apti62` (repo นี้), `claude/wonderful-gauss-apti62` (pf_bridge)
Draft PR ที่ถืออยู่: `pirate-force-server#437`, `pf_bridge#662`

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ยังไม่มี ณ push นี้** -- ส่วนนี้เป็น CORE-REQUEST (ฟังก์ชันแก้พร้อมเรียกแล้ว byte-pinned เทสผ่าน
แต่การเดินสายจริงเข้า `app.py` เป็นเขตของ chief คนเดียว) เมื่อ chief เดินสายรอบหน้า ผู้เล่นจะเห็น:
ของที่มอนดรอปไม่หายไปจากพื้น/จอทุก ~2 วินาทีอีกต่อไป (ถ้าคำอ่าน image ของ Codex ที่ COO รับไว้ถูก) --
ปัจจุบัน heartbeat ของทุกเซสชัน (วิ่งอยู่แล้วทุกวันนี้ ทุก session, ไม่มีแฟล็ก) ส่ง RuntimeRes ที่มาสก์
ground-list เป็น "absent" ทุก ~2 วิ ซึ่งตามหลักฐานของ Codex คือสัญญาณเคลียร์ทั้งชุดฝั่งไคลเอนต์

## COO-DECISION 0347: ผลสืบสวน

**สรุป: ใช่ ยืนยันบั๊กเดียวกับที่ Codex ชี้ ตรงกันเป๊ะ** และข้อค้นพบที่สำคัญกว่าคำตอบ ใช่/ไม่ใช่ คือ
**"producer จริง" ในโค้ด live ไม่ใช่โค้ดคู่ขนานอีกชุด -- มันคือ v141's heartbeat_worker เอง รันตรง ๆ**:

```
$ grep -rn "heartbeat_worker" src/          # ว่างเปล่า -- ไม่มีการ reimplement
$ sed -n '845,850p' src/pirateforce_foundation/app.py
    legacy.game_listener = adapt_game_listener(
        legacy.game_listener, connection_bindings, managed_sockets,
    )
$ sed -n '226,242p' src/pirateforce_foundation/connection.py
def adapt_game_listener(original, bindings, socket_module):
    """Run frozen listener code with late-bound globals and a GAME socket facade."""
    ...
        listener = types.FunctionType(
            original.__code__, listener_globals, original.__name__, ...)
        ...
```

`original.__code__` คือบายต์โค้ด**ของ v141's `game_listener` ฟังก์ชันตรง ๆ** -- ไม่มีการเขียนใหม่
ดังนั้นทุก session ที่เซิร์ฟเวอร์ live รับวันนี้ วิ่ง `heartbeat_worker` (nested อยู่ข้างในฟังก์ชันเดียว
กัน) ตัวเดียวกับที่ Codex อ่านจาก v141 ทุกตัวอักษร

ยืนยันไบต์จริง (ไม่ใช่การอ่านซ้ำจดหมาย Codex):

```
$ python3 -c "
import sys; sys.path.insert(0,'src')
from pirateforce_foundation.legacy_bridge import load_legacy
legacy = load_legacy('current/pf_login_game_server_v141.py')
pc, frame = legacy.make_runtime_res_empty_exact()
print('pc', pc.hex(), len(pc))
"
pc 129d6e140000000008040b000b00 14
```

`offset 10-11 = 0b 00` (inherited VitalData list, absent) และ `offset 12-13 = 0b 00` (ground-object
`0x08` list, **ก็ absent ด้วย**) -- ตรงกับ pattern ที่ Codex อ้างจาก image: derived bit `0x08` ไม่
set = NULL pool ที่ reconciler อ่านเป็น "clear" `pf_login_game_server_v141.py:2182-2200` (ฟังก์ชัน),
`:7417-7436` (worker thread, `while not conn_done.wait(2.0): ... if not state.teleport_sent:
continue` -- **ไม่มีเงื่อนไขเรื่องของบนพื้นเลย** ยิงทุก ~2 วิไม่สนบริบท)

ยืนยันข้ามแหล่งอิสระ: `src/pirateforce_foundation/logout_hypothesis.py:11-13` (คนละเลน เขียนไว้ก่อน
รอบนี้ ไม่ได้เขียนเพื่อตอบจดหมายนี้) บันทึกไว้แล้วว่า "the frozen v141 clock-driven transport
heartbeat is unchanged and continues until socket close, as it does in every accepted session"

## สร้างไว้แล้ว: ฟังก์ชันแก้ (CORE-REQUEST ready-to-call)

`src/pirateforce_foundation/mob_loot.py` -- ของเดิมในไฟล์ไม่แก้แม้บรรทัดเดียว, เพิ่มสองฟังก์ชันใหม่
ท้าย `refresh_frames` ก่อน `money_element`:

- `preserve_ground_heartbeat_pc(legacy)` -- 17 bytes, pin `129d6e140000000008040b000b08120000`
  (envelope เดียวกับ `drop_collection_pc`, derived mask `0x08` **PRESENT**, count = 0)
- `preserve_ground_heartbeat_frame(legacy)` -- `(pc, frame)`, frame 27 bytes, pin
  `ac3e255f130000001140129d6e140000000008040b000b08120000`

**ไม่ใช่** `drop_collection_pc(legacy, ())` ซึ่งตั้งใจปฏิเสธ (`REFUSE_GENERATION_IS_EMPTY`, RE-130)
-- คนละความหมาย: generation ว่างของการฆ่า (ไม่มีเหตุผลให้ส่ง) เทียบกับ heartbeat ที่ไม่มีอะไรใหม่ต้อง
reconcile (มีเหตุผลให้ส่งเสมอ, และการส่ง "preserve" ปลอดภัยไม่ว่าจะมีของบนพื้นหรือไม่)

## CORE-REQUEST -- 1 บรรทัด + 1 import ใน `app.py` (ไม่ใช่ `connection.py`, ไม่ใช่ v141)

พิสูจน์ semantics แยกต่างหาก (Python ทั่วไป ไม่เจาะจงโปรเจกต์นี้) ว่า monkeypatch attribute บน
module object `legacy` หลัง `load_legacy()` แต่ก่อน listener thread เริ่ม เปลี่ยนพฤติกรรมของ nested
function ข้างในได้ทันที โดยไม่แก้ไฟล์ v141 แม้ไบต์เดียว:

```
$ python3 -c "
import types
mod = types.ModuleType('testmod')
exec('''
def outer():
    def inner():
        return helper()
    return inner
def helper():
    return \"original\"
''', mod.__dict__)
inner = mod.outer()
print('before patch:', inner())
mod.helper = lambda: 'patched'
print('after patch:', inner())
print('inner.__globals__ is mod.__dict__:', inner.__globals__ is mod.__dict__)
"
before patch: original
after patch: patched
inner.__globals__ is mod.__dict__: True
```

ask เต็มอยู่ในจดหมาย `notes_to_chief/20260901_0420_LANE-B-CORE-REQUEST-heartbeat-preserve-ground-
list-fixes-drop-clear.md` (bridge repo) -- สรุปบรรทัดที่ขอ:

```python
# app.py, เพิ่ม import
from .mob_loot import preserve_ground_heartbeat_frame
# app.py, ราวบรรทัด 848, ก่อนหรือหลัง legacy.game_listener = adapt_game_listener(...) ก็ได้
legacy.make_runtime_res_empty_exact = lambda: preserve_ground_heartbeat_frame(legacy)
```

## พบเพิ่ม (นอกแผนเดิม): สวีตเต็มแดง 1 เทสหลัง merge -- แก้แล้ว ไม่ใช่บั๊กของงานรอบนี้

รัน `pytest tests -q` เต็มสวีตหลังต่อรอบ (ตามกฎ "รันเทสที่เกี่ยวข้อง + full suite") เจอ 1 failed ที่ไม่
เกี่ยวกับงาน P-1/0347 เลย: `tests/test_mob_combat_bg0015_gates.py::Bg0015WiredPathTests::
test_registering_bg0015_clears_the_ai_table_gate_but_the_swing_is_still_inert` (เทสที่แก้ไว้ใน**ส่วน
แรก**ของรอบนี้เอง ก่อน merge) คาดหวัง event `..._skipped_no_population_anchor` แต่ได้
`..._skipped_no_composer_for_scene` แทน

สาเหตุ: main ที่ orchestrator merge เข้ามามีคอมมิต `b69071f6` (chief round `4w5j25`/R278: "widen eager
NPC census from bg0002-only to every scene but home") ซึ่งทำให้ฉาก 14 ได้ arrival-census anchor
(`last_target_pos`-equivalent) แม้เทสนี้จะไม่เคยส่ง `TargetPosVital` เลยก็ตาม -- swing จึงไม่ตกใน
"attack ก่อนมี anchor" (`no_population_anchor`) อีกต่อไป แต่ไปตกที่ compose จริงซึ่งยังถูกปฏิเสธเพราะ
ฉาก 14 ไม่มี composer ขึ้นทะเบียน (`recompose_status()['has_composer'] == False` เหมือนเดิมทุกประการ
-- ยืนยันสดแล้ว) นี่คือ**ความคืบหน้าจริงจากงานสายอื่น ไม่ใช่การถอยหลัง** และไม่ใช่ผลจากโค้ด mob_loot.py
ของรอบนี้เลย -- แก้เฉพาะ docstring/assertion ของเทสให้ตรงความจริงใหม่ (ขีดฆ่าข้อความเดิมที่ผิดแล้ว ไม่ลบ
ตามกฎ, ไม่แตะ `mob_combat_bg0015_gates.py` โค้ดจริงแม้บรรทัดเดียว, ไม่แตะ `runtime.py`)

`tests/test_mob_combat_bg0015_gates.py`: แก้ 1 เทส (docstring + assertion เปลี่ยนชื่อ event ที่คาด
+ เพิ่ม assert ยืนยัน `has_composer` ยัง False) -> `17 passed` ทั้งไฟล์

## ทดสอบ

```
tests/test_mob_loot.py -k PreserveGroundHeartbeat            -> 7 passed
tests/test_mob_loot.py ทั้งไฟล์                                -> 95 passed, 1 skipped, 12 subtests passed
tests/test_mob_combat_bg0015_gates.py ทั้งไฟล์ (หลังแก้)         -> 17 passed
สวีตเต็มก่อนแก้เทส bg0015 (ยืนยันด้วยตัวเอง หลังต่อรอบ)          -> 1 failed, 6052 passed, 383 skipped,
                                                                    13126 subtests passed (191.64s)
สวีตเต็มหลังแก้เทส bg0015 (ยืนยันซ้ำ)                            -> 6053 passed, 383 skipped,
                                                                    13126 subtests passed, 0 failed (190.08s)
```

## ตัวเลขที่วัดได้

```
ไฟล์ที่แตะรอบนี้ (ส่วน P-1/0347) (pirate-force-server):
  src/pirateforce_foundation/mob_loot.py           [เพิ่ม 2 ฟังก์ชันใหม่ + 3 ค่าคงที่ pin, ของเดิม 0 บรรทัดแก้]
  tests/test_mob_loot.py                           [เพิ่ม import 4 ชื่อ + คลาสเทสใหม่ 7 เทส, ของเดิม 0 แก้]
  tests/test_mob_combat_bg0015_gates.py            [แก้ 1 เทส -- docstring+assertion ตามความจริงหลัง merge]
  rounds/B_20260901_0420_n8kq4r_addendum_p1-heartbeat-preserve-core-request.md  [ไฟล์นี้]
รวมส่วนแรก+ส่วนนี้ของรอบ n8kq4r: 6 + 4 = 10 ไฟล์ (repo นี้)

preserve_ground_heartbeat_pc  : 17 bytes, pin 129d6e140000000008040b000b08120000
preserve_ground_heartbeat_frame: 27 bytes, pin ac3e255f130000001140129d6e140000000008040b000b08120000
เทสใหม่ที่ผ่าน: 7/7 (PreserveGroundHeartbeatTests)
เทสไฟล์เดิมทั้งไฟล์หลังแก้: 95 passed, 1 skipped, 12 subtests passed, 0 failed
```

`current/pf_login_game_server_v141.py`: ไม่แตะ (อ่านอย่างเดียว, ผ่าน `load_legacy`) ·
`runtime.py`/`app.py`: ไม่แตะ (CORE-REQUEST เขียนไว้ให้ chief) · `connection.py`: ไม่แตะ (พิจารณา
แล้วว่าไม่จำเป็น -- wiring ทำได้ด้วยบรรทัดเดียวใน app.py) · canonical DB/capture corpus: ไม่แตะ

## ยังไม่ได้พิสูจน์

- ว่าการอ่าน image ของ Codex (`0x006AF970`, NULL pool = clear) ถูกจริง -- สายนี้ตรวจแค่ codepath/
  byte-level ฝั่งเซิร์ฟเวอร์ ไม่ได้รันไบนารีไคลเอนต์เอง
- ว่า fix นี้ทำให้ label/ของกลับมาอยู่บนจอจริง -- ต้องมี attended round ยิงจริงหลัง chief เดินสาย CORE-
  REQUEST (เกณฑ์ปิด: ฆ่ามอนหนึ่งตัว รอเกิน 2 วิ (ข้ามอย่างน้อยหนึ่ง heartbeat) แล้วดูว่า label/ของยัง
  อยู่ไหม)
- ว่า wiring บรรทัดเดียวทำงานจริงเมื่อรันเซิร์ฟเวอร์เต็ม end-to-end (verify แค่ semantics ของ Python
  nested-function-globals แยกต่างหาก ไม่ได้รันเซิร์ฟเวอร์เพราะ `app.py` ไม่ใช่เขตของสายนี้)
- ทุกอย่างที่รอบก่อนหน้ายกไว้ (color mapping RE-067/RE-155 -> ตอนนี้เป็น P-2, มอบ LANE-GM แล้ว, pickup
  opcode RE-125/GT-124 -- ดูข้อสังเกตในจดหมาย CORE-REQUEST) ไม่มีข้อไหนขยับเพิ่มรอบนี้

## CORE-REQUEST

มี -- ดูหัวข้อข้างบน + จดหมายเต็ม
`notes_to_chief/20260901_0420_LANE-B-CORE-REQUEST-heartbeat-preserve-ground-list-fixes-drop-clear.md`
(bridge repo): 1 import + 1 บรรทัดใน `app.py` (`legacy.make_runtime_res_empty_exact = lambda:
preserve_ground_heartbeat_frame(legacy)`, ก่อน/หลังบรรทัด 848 ก็ได้)

## เปิดใบให้สาย C

ไม่มี

-- LANE-B (COMBAT) รอบ `n8kq4r` (addendum)
