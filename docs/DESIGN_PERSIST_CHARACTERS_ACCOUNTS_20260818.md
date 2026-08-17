# DESIGN — Persistence write path: characters / accounts

**สถานะ: PROPOSED — รอ Panya เคาะ ยังไม่ implement** (สถาปัตยกรรมใหญ่ นอกขอบ pre-approval 18:2x)
เขียนโดย chief รอบ 46 · 2026-08-18 · อิง HEAD `9f5e6a2` · ทุกข้ออ้างอิงตรวจจากโค้ด/DB จริง (read-only)

---

## 1. สถานะปัจจุบัน (verified)

Write path ที่**มีแล้ว**ใน runtime:

| ตาราง | write path | จุดเรียก |
|---|---|---|
| `accounts` | INSERT-if-missing ตอน login (`ensure_account`) — เก็บแค่ `login_name` | `lifecycle.login` |
| `characters` | INSERT ตอนสร้างตัวละคร (`create_character`) ผ่าน wire `CREATE_ACTOR_VITAL` | `runtime.py:721` |
| `character_positions` | INSERT ตอน create + UPDATE `save_position` (guard: session เปิด + selected) | checkpoint |
| `character_backpacks/_items` | INSERT ตอน create + 3 mutation (v111 merge / slot2 / free-slot) | HYP-PF-008/010 |
| `sessions` | open/close/select/expire | lifecycle |

Write path ที่**ไม่มี** (ช่องว่างที่ดีไซน์นี้ครอบ):

1. **ลบตัวละคร** — `characters.deleted_at` มีคอลัมน์ และ read query ทุกตัวกรอง `deleted_at IS NULL` แล้ว (store.py:69,168,177,197,202,209,277) แต่**ไม่มีโค้ดเซ็ตค่า** · `delete_actor.py` มี `parse_delete_actor_vital_request` (parse-only) ไม่มี handler/store method → ปุ่มลบตัวละครใน client = ตาย
2. **UPDATE `characters` หลัง create** — ไม่มี path ใด (`updated_at` เซ็ตครั้งเดียวตอน create) เช่น เปลี่ยน avatar/ชื่อ
3. **`accounts` ไม่มี state อื่น** — ไม่มี credential (second password = proactive-OK bypass ไม่ persist), login_name อะไรก็ auto-create

## 2. กับดักสถาปัตยกรรมที่ตรวจพบ (เหตุที่ต้องเคาะก่อน)

**Soft delete แล้วสร้างตัวใหม่จะพัง 2 ชั้น** (store.py:164–186):

- แถวที่ soft-delete **ยังถือ selector เดิม** → INSERT ใหม่ชน `UNIQUE(account_id,selector)` เพราะตัวเลือก selector สแกนเฉพาะ `deleted_at IS NULL` (บรรทัด 177) จึงเลือกเลขซ้ำกับแถวที่ลบ
- ต่อให้ผ่าน ชั้นสอง: `identity_lo = 0x10000000 + account_id*0x10000 + selector+1` เป็นฟังก์ชันของ selector ล้วน → ชน `UNIQUE(identity_lo,identity_hi)` ของแถวที่ลบ
- fingerprint-retry (บรรทัด 168) ก็กรอง deleted → สร้างตัวเดิมซ้ำหลังลบ = INSERT ใหม่ → ชนเหมือนกัน

→ จะเปิด delete ไม่ได้เลยถ้าไม่ตัดสิน selector/identity policy ก่อน

## 3. ข้อเสนอ — 3 lane แยกอิสระ

### Lane 1 (เสนอทำก่อน): soft delete ผ่าน DeleteActorVital — **ไม่แตะ schema เลย**

- store method ใหม่ `soft_delete_character(sid, selector)`: guard = session เปิด + ตัวละครเป็นของ account นั้น + **ไม่ใช่ตัวที่ selected อยู่** → เซ็ต `deleted_at` (ไม่ hard DELETE — cascade ไม่ทำงาน ลูก positions/backpack คงอยู่เป็นหลักฐาน, read ถูกกรองผ่าน join อยู่แล้ว)
- handler ต่อ `delete_actor.py` ที่ parse ไว้แล้ว ตาม pattern มาตรฐาน: **opt-in scenario `delete_actor_hypothesis` · production_allowed=false · fail closed** (parse/guard พลาด = ไม่เขียน ไม่ตอบพิเศษ) · ledger/verifier/matrix ครบ
- **แก้กับดัก ข้อ 2 ด้วย Option A**: เปลี่ยน selector scan + fingerprint-retry ให้**นับรวมแถว deleted** (ตัด `AND deleted_at IS NULL` ใน 2 query ของ create) → selector ไม่ reuse ตลอดชีพ account (เพดาน 256 ครั้งสร้าง/account — พอสำหรับ lab เหลือเฟือ) · identity ไม่ชน · **ไม่มี migration**
- Option B (จดไว้ ไม่เสนอ): rebuild ตารางเป็น partial unique index `WHERE deleted_at IS NULL` — reuse selector ได้ แต่ต้อง migration ใหญ่ + แตะสูตร identity → ค่อยทำเมื่อเพดาน 256 เป็นปัญหาจริง
- headless proof จบในตัว: replay DeleteActorVital → assert `deleted_at` ถูกเซ็ต · `list_characters` ไม่เห็น · re-login เห็น n−1 · สร้างใหม่หลังลบสำเร็จ (selector ตัวถัดไป ไม่ชน)
- response bytes ต่อ client: ถ้า `references/sources/` ไม่มีตัวอย่าง DeleteActor reply → ชั้น wire ตอบ generic ack เท่านั้น (ไม่ประดิษฐ์ bytes ตาม doctrine 0x25A2) — ชั้น DB พิสูจน์ได้เต็มโดยไม่ต้องรอ

### Lane 2: UPDATE characters (avatar/ชื่อ/สถิติ) — **เสนอ: ยังไม่เปิด**

รอ trigger จริง: เจอ vital จาก client ที่สื่อการแก้ตัวละคร + มี reference ยืนยัน schema — ไม่ประดิษฐ์ล่วงหน้า (fail-closed doctrine เดิม)

### Lane 3: accounts hardening — **เสนอ: คงเดิมไปก่อน**

auto-create ตอน login เหมาะกับ lab · credential/second-password persistence ค่อยออกแบบเมื่อ client flow จริงบังคับ (ตอนนี้ bypass ทำงานพิสูจน์แล้ว) · ถ้าจะทำ = migration เพิ่มคอลัมน์ nullable + เกณฑ์ gate ขยับ → เป็นดีไซน์รอบใหม่

## 4. ผลกระทบ gate/matrix

Lane 1 ตามข้อเสนอ = **ไม่มี schema migration** → `schema_migrations` คงที่ · canonical sha ไม่เกี่ยว (ไม่แตะ wire digest) · pytest จะเพิ่มจากเทสใหม่ของ lane นี้เอง — เกณฑ์เขียวรอบถัดไปอ่านจาก release note ตามกติกา

## 5. คำถามให้ Panya เคาะ

- **Q1**: อนุมัติ Lane 1 (soft delete + Option A ตัด filter deleted ใน selector/fingerprint scan ของ create) ไหม? — ถ้าเคาะ chief implement + headless proof จบได้ในรอบ scheduled ถัดไป
- **Q2**: ยืนยัน Option A (selector ไม่ reuse, เพดานสร้าง 256 ครั้ง/account) แทน Option B (migration ใหญ่)?
- **Q3**: Lane 2/3 คงสถานะ "รอ trigger จริง" ตามเสนอ?

*ตอบใน CHIEF_CONTINUATION.md บล็อกลงชื่อ "จาก Panya" ได้เลย — เคาะแล้ว chief เดินต่อเองทั้งสาย*
