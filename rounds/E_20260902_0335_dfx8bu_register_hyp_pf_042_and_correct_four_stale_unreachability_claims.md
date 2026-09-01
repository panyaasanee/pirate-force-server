# E_20260902_0335 (`dfx8bu`, R298) — ลงทะเบียน HYP-PF-042 + แก้คำอ้างที่กลายเป็นเท็จ 4 จุด

รอบ scheduled ไม่มีคนเฝ้าจอ · สาย E (chief) · PR ของรอบนี้: `pirate-force-server#531`

## ทำไมรอบนี้

R297 ของผมเองเขียนไว้ท้ายไฟล์รอบว่า **"ยังไม่ทำ: HYP-PF-042"** และใบ
`pf_bridge/notes_to_chief/20260902_0215_CHIEF-REPLY-hyp-pf-042-registration-queued-next-pr.md`
สัญญากับสาย A ไว้ว่าเป็น **ใบแรกของ chief ฝั่งเซิร์ฟเวอร์หลัง PR ของ P-1 merge**
PR นั้นคือ `#526` ซึ่ง merge ไปแล้ว ⇒ รอบนี้คือรอบที่ต้องจ่ายหนี้ ไม่ใช่รอบที่เลือกทำ

สาย A (รอบ `4h2nzu`) สร้าง profile ที่เจ็ด `_PROFILE_ACK_FIRST_REORDER` + scenario + เทส 18 ใบ เสร็จแล้ว
และ **จงใจไม่แตะ** `docs/HYPOTHESIS_LEDGER.json` กับ annotation ในโค้ด ซึ่งถูกต้อง: ใส่ annotation ก่อนมีแถวใน
`EXPECTED_META` จะทำให้ `verify_hypothesis_ledger.py` ล้มสำหรับ **ทุกสาย** ไม่ใช่แค่สายเดียว

## สิ่งที่เปลี่ยน (5 ไฟล์)

1. `docs/HYPOTHESIS_LEDGER.json` — เพิ่มหนึ่ง entry ท้ายไฟล์ 49 → 50 (append เท่านั้น ไม่ขยับ index ของใบเก่า)
   `HYP-PF-042` / checkpoint `LOGOUT-ACK-FIRST-REORDER-001` / `status: active` / `production_allowed: false`
2. `tools/verify_hypothesis_ledger.py` — `EXPECTED_IDS` + `EXPECTED_META` + `CANONICAL_CONTENT_SHA256`
   คำนวณใหม่ **ด้วยสูตรของเครื่องมือเอง** (`json.dumps(raw, sort_keys=True, separators=(",",":"),
   ensure_ascii=False)` → utf-8 → sha256 → upper) ไม่ได้เดามือ: `D47A9994…` → `F3E21DD3…`
   พร้อมบล็อก lineage ใหม่ที่ระบุว่ามัน supersede ประโยคของ lineage ก่อนหน้าอย่างไร
3. `src/pirateforce_foundation/logout_hypothesis.py` — บรรทัด annotation
   `# PF-HYPOTHESIS-LEDGER: HYP-PF-042 active` **ต้องอยู่ commit เดียวกับแถว** เพราะ verifier ล้มทั้งสองทาง
   (มี annotation ไม่มีแถว = `unregistered emitter annotation` · มีแถวไม่มี annotation =
   `declared emitter is missing adjacent annotation`) ⇒ ครึ่งเดียวลงไม่ได้
4. + 5. แก้คำอ้างที่ **กลายเป็นเท็จ** ใน `runtime.py` (2 จุด) และ docstring ของ
   `tests/test_logout_ack_first_reorder_routing_wired.py`

## คำอ้างที่กลายเป็นเท็จ — ทำไมต้องแก้ในใบนี้

สี่จุดยังเขียนอยู่ว่า *"ไม่มี allowlisted profile ที่ถือค่านี้ได้ ⇒ branch นี้เอื้อมไม่ถึงจากบูตปกติอย่างพิสูจน์ได้"*
ประโยคนี้ **จริงตอนเขียน** และเลิกจริงตอนสาย A ลง profile — ไม่ใช่เพราะรอบนี้ แต่รอบนี้เป็นรอบที่แตะไฟล์เหล่านี้
และปล่อยคำอ้างเท็จไว้ในไฟล์ที่ตัวเองแก้ไม่ได้

ขีดฆ่า ไม่ลบ (แบบ R166) เพราะคนที่เคยอ่าน audit บรรทัดเก่าต้องรู้ว่ามันเลิกจริงเมื่อไหร่
**สิ่งที่ยังจริงและแคบกว่า**: ถึง branch นี้ได้ต้องมีแฟล็ก `--logout-hypothesis-scenario` ชี้ไฟล์นั้นไฟล์เดียว
(ซึ่งเองก็บังคับให้มี `--db` ชัดเจน) และไฟล์ถูกแมตช์ field-exact กับ allowlist ในโค้ด · บูตปกติไม่ส่งแฟล็ก
⇒ พิสูจน์ด้วยเทสสองใบ (`test_unreachable_from_a_default_boot_with_no_scenario_at_all` และ
`test_default_boot_scenario_files_never_carry_this_policy`) ไม่ใช่ด้วยคอมเมนต์

🔴 จุดที่ต้องระวังและเขียนไว้ในไฟล์แล้ว: `test_scenario_carrying_the_new_policy_is_not_yet_allowlisted`
**ยังผ่านอยู่** แต่ผ่านเพราะ probe ในหน่วยความจำต่างจาก profile จริงสองฟิลด์ (`scenario_id`/`hypothesis_id`)
⇒ มันพิสูจน์ว่า **allowlist เป๊ะ** ไม่ได้พิสูจน์ว่า **ไม่มี profile ไหนถือ policy นี้** อย่างที่ชื่อมันชวนให้เชื่อ
ห้ามยกเทสใบนี้ไปอ้างเรื่องความเอื้อมไม่ถึงอีก

## เนื้อของ entry — หนึ่งบรรทัดว่ามันอ้างอะไร

หลัง ack ของ HYP-PF-012 ออกก่อน แล้วค่อยส่ง 0x709E ของ HYP-PF-028 (กลับด้านจากลำดับเดิมของ HYP-PF-028)
**ตัวแปรเดียวที่ขยับคือลำดับเฟรม** — ไม่มีไบต์ใหม่ที่ไหนเลย ทุก pin เป็นการอ้างค่าคงที่เดิมของโมดูล
และ composer ทั้งสองตัว re-hash สิ่งที่ตัวเองสร้างแล้ว raise ถ้าเพี้ยน ⇒ ไบต์เปลี่ยนเงียบ = crash ไม่ใช่ส่ง
🔴 **ไม่ยุบรวมกับ HYP-PF-041**: ใบนั้นเนื้อความที่ hash ปักไว้แล้วอ้างเรื่อง **ค่าหน่วงเวลา** (close_delay_ms)
เอาข้ออ้างเรื่อง **ลำดับ** ไปใส่จะทำให้ทั้งสองใบอ้างผิดจากกัน · HYP-PF-042 คงค่าหน่วงไว้ที่ 250 ms
(ค่า default ของ HYP-PF-013) โดยตั้งใจ — สองคันโยก สองใบ

## evidence_gap ที่ต้องอ่านก่อนใช้ใบนี้

**ยังไม่มีไคลเอนต์ตัวไหนเคยเห็นลำดับนี้** ทุกอย่างในใบเป็นชั้น wire/DB ล้วน
RE-189 Job 1 วัดไว้แล้วว่าฟิลด์ที่ทุก logout profile พยายามพลิก (`[SystemSetting_LogoutConfirm+0x18]`)
มีผู้เขียนตัวเดียวใน bounded graph คือ UI-tree ของไคลเอนต์เอง ไม่ใช่ payload ขาเข้า
⇒ **ใบนี้ไม่ได้ทำนายผลบวก** ถ้ารอบ attended ได้ผลบวกจากการสลับลำดับ นั่นคือข้อมูลใหม่ในตัวมันเอง
และผลลบก็ไม่ falsify กลไก แค่ bound มัน

## เขียว

- `python3 -m pytest tests/ -q` = **6774 passed · 323 skipped · 13815 subtests · 0 failed** → เขียว(cloud sanity)
- `python3 tools/verify_hypothesis_ledger.py` = **PASS entries=50** (ก่อนรอบนี้ PASS entries=49)
- `pf_bridge/tools_bridge/pf_gate_preflight.py` = **PREFLIGHT PASS** (cp874 + ไม่มี skip ใหม่)
- ยังไม่มี เขียว(gate เต็ม บนสะพาน) — รันจากที่นี่ไม่ได้ตามกติกา

## [วัดแล้ว] ของแถมที่เจอระหว่างตรวจ — เครื่องมือ verifier สองตัว **แดงอยู่บน `main` แล้ว** และไม่มีใครรู้

รอบนี้ผมรันเครื่องมือ standalone ที่ **ไม่ได้อยู่ในชุด pytest** ด้วยมือ (เพราะสำรวจกับดัก prose-mention
พบว่า `tools/verify_hp_death_encoder.py` เป็นขั้นบังคับของ gate ที่รายงานแค่ `exit=1` ไม่เข้า dump รายละเอียด):

| เครื่องมือ | ผลบน branch นี้ | ผลบน `origin/main` |
|---|---|---|
| `tools/verify_hp_death_encoder.py` (**อยู่ใน gate** ขั้น `hpenc`) | exit 0 | exit 0 |
| `tools/verify_npc_hostile_encoder.py` | exit 0 | — |
| `tools/verify_stats_progression_encoder.py` | exit 0 | — |
| `tools/pf_multiplayer_readiness_audit.py` (อยู่ใน gate) | exit 0 | — |
| `tools/verify_loot_roller.py` | **exit 1** | **exit 1 แดงอยู่แล้ว** |
| `tools/verify_remote_player_encoder.py` | **exit 2** | **exit 2 แดงอยู่แล้ว** |

ยืนยันด้วย worktree แยกที่ `origin/main` (สร้าง ตรวจ ลบทิ้ง ต้นไม้จริงไม่ถูกแตะ) ⇒ **ไม่ใช่ผลของรอบนี้**
ทั้งสองใบล้มด้วยกับดักเดียวกัน: `FAIL - no other module in src references the lane` และ
`FAILED GUARD: only app.py and runtime.py reference the module` — คือ guard ที่นับ "ผู้เอ่ยชื่อ" ด้วยข้อความดิบ
🔴 ทั้งคู่ **ไม่อยู่ใน `gate-windows.yml`** จึงไม่มีอะไรทำให้ใครเห็นว่ามันแดง — เข้าข่าย "เครื่องมือที่รู้ว่าพัง"
ตามหัวข้อ 17 ข้อ 7 ของ prompt · ผม **ไม่แก้ในรอบนี้** เพราะเป็นคนละเรื่องกับใบนี้ (กฎหนึ่งเรื่องต่อหนึ่ง PR)
และการตัดสินว่า guard พวกนี้ควรผ่อนหรือควรเข้ม เป็นคำถามที่ผมส่ง COO ไปแล้วในใบ
`pf_bridge/notes_to_chief/20260902_0330_CHIEF-TO-ALL-prose-mention-trap-*` ⇒ รอคำเคาะแล้วไล่แก้ทีเดียว

## nonclaim

1. ไม่มีอะไรในรอบนี้แตะพฤติกรรม runtime — `runtime.py` เปลี่ยนแค่คอมเมนต์ · routing ของ branch นี้อยู่บน main
   ตั้งแต่รอบ `5qs3y7` (R293) แล้ว
2. ไม่อ้างว่า `HYP-PF-042` ถูกพิสูจน์ที่ชั้น client-observable · ห้ามยกไปเลื่อนเกรดแถวไหนใน coverage
3. ไม่ได้ยืนยันว่าค่า SHA256 ที่ pin ไว้ตรงกับไบต์ของเซิร์ฟเวอร์ต้นฉบับ — มันคือการประกอบของรีโปนี้เอง
   ที่ self-check ตอน compose · คำถาม tag ของ field 3 ใน 0x709E ยัง `[STALE][MEASURED]` และต้องใช้อิมเมจ
   บนเครื่องเจ้าของ ปิดจาก cloud clone ไม่ได้
4. annotation ในโค้ดใส่โดย chief ไม่ใช่สาย A — สาย A เสนอจะใส่เองรอบหน้า แต่ใส่แยก commit ไม่ได้
   ด้วยเหตุผลข้อ 3 ข้างบน จึงใส่ให้ในใบนี้เลย
