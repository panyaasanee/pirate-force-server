# PF-NAMEID-RESOLVE-001 — every structural protocol id in the golden corpus is now named (last three bare-hex ids resolved byte-exact)

Date: 2026-08-18
Round: chief scheduled รอบ 63 (report-only, additive)
Grade claim: **static + golden / byte-exact** — identity naming only. No runtime hypothesis changed, no ledger/matrix/src edit this round.
Precedent for report-only additive integration: `7c66b21` (NAMEID-HASH-001), `96b76fe`, `cec8c82`, `e1741db`.

## จุดตั้งต้น

รอบ 62 (`7c66b21`, PF-NAMEID-HASH-001) พิสูจน์ว่า wire id 16-bit ของทุก Vital = **hash บริสุทธิ์ของชื่อคลาส**:

```
uint16 id = 0
for i in 0..len-1:  id += (int16)( (signed char)name[i] * (i+1) )   # mod 2^16
return id & 0xFFFF                # ตัว hash = 0x89b220 · id-assign = 0x89bd00 · once-init = 0x89c080
```

รอบนั้นเป็น **static ล้วน** (name-literal→id ในอิมเมจ + committed constants). รอบนี้ต่อยอดโดยเอา hash ที่ยืนยันแล้วไปใช้กับ **golden corpus ตัวจริง** (`capture_v141/*.txt`, canonical `B5557E9F..C9ED`) — เดิม decoder พิมพ์ id สามตัวเป็นเลขฐานสิบหกดิบเพราะไม่มีชื่อในตาราง `NAMES` ของ v141. รอบนี้ปิดช่องนั้นให้หมด.

## ผลลัพธ์

### 1. golden cross-check — hash reproduces ทุก named id ในเฟรมจริง (ไม่ใช่แค่ tie ในอิมเมจ)

id ที่ **มีชื่อ** ใน 6 ตัวใน corpus reproduce ด้วย hash แบบ byte-exact:
`StartGameReq 0x1E87 · CreateActorVital 0x36CF · LoginVerifyVital 0x3784 · GetWorldInfoVital 0x3D4B · GSCN_LoginProtocol 0x453A · GSCN_RunTimeProtocolReq 0x6E6F`.

เพิ่มเติม: **ทั้ง 49 (id,name) ใน `NAMES` ของ v141 reproduce byte-exact 0 mismatch** — corroboration แข็งกว่ารอบ 62 ที่ยืนยัน 13/13.

### 2. resolution — id ที่เป็นเลขดิบใน golden แต่ละตัว → ชื่อ literal เดียวในอิมเมจ (unique preimage)

corpus มี id เป็นเลขดิบ (ไม่มีชื่อ) เหลืออยู่ **3 ตัวเท่านั้น**. แต่ละตัว hash กลับไปตรงกับ **identifier-style string literal เพียงตัวเดียว** ในบรรดา 65,387 ascii runs ทั้งอิมเมจ และ literal นั้นอยู่ใน registration thunk รูปแบบ byte-exact เดียวกับรอบ 62:

```
push <name-literal>
call 0x89c080        ; once-init guard
mov  ecx, eax
call 0x89bd00        ; id-assign (เรียก hash 0x89b220)
mov  word ptr [<id-slot>], ax
ret
```

| wire id | ชื่อที่ resolve | thunk VA | id-slot | preimage ในอิมเมจ | สถานะเทียบรอบ 62 |
|---|---|---|---|---|---|
| `0x1B40` (6976) | `LogoutVital` | `0xBEE860` | `0x108207C` | unique identifier (3 collisions รวม junk 2) | tie มีในรอบ 62 — **รอบนี้เชื่อมเข้า golden** |
| `0x36DB` (14043) | `DeleteActorVital` | `0xBEE300` | `0x1081FD0` | **unique เดี่ยว** (1 collision) | **net-new tie** (ไม่อยู่ใน 10 ของรอบ 62) |
| `0xAC52` (44114) | `Channel_LocalTalkMessageVital` | `0xBF72D0` | `0x1084458` | **unique เดี่ยว** (1 collision) | tie มีในรอบ 62 — **รอบนี้เชื่อมเข้า golden** |

collisions ที่ไม่ใช่ identifier ของ `0x1B40` เป็น string ขยะล้วน (`'8,8D8\8d8l8x8'`, `'8L9R9Z9\`9h9q9'` — เศษ address table) ไม่ใช่ชื่อโปรโตคอล → ไม่กระทบ uniqueness ของ preimage แบบ identifier.

### 3. semantic corroboration — label ของเฟรม golden ตรงกับชื่อที่ resolve

| wire id | wrapper ใน golden | frame hypothesis label | สอดคล้องกับ |
|---|---|---|---|
| `0x1B40` | `GSCN_RunTimeProtocolReq` | `HYP_PF_016_LOGOUT_SUBCODE01_...` | LogoutVital |
| `0x36DB` | `GSCN_LoginProtocol` | `HYP_PF_015_DELETE_ACTOR_SELECTOR00_SOFT_DELETE_...` | DeleteActorVital |
| `0xAC52` | `GSCN_RunTimeProtocolReq` | `HYP_PF_014_CHAT_INPUT_SPEAKER_ECHO_...` | Channel_LocalTalkMessageVital |

หลักฐานสามชั้นตรงกันหมด: (1) hash byte-exact, (2) registration thunk byte-exact, (3) label ของเฟรม golden ที่จดโดยอิสระ.

## เกรดและขอบเขต

- **เกรด A (identity naming)** — byte-exact static + golden. ปิดสถานะ "structural protocol id เป็นเลขดิบ" ใน golden corpus **ครบทุกตัว** (เหลือ 0 unnamed).
- **ขอบเขต — สิ่งนี้ยังไม่พิสูจน์**: pipeline พฤติกรรมของแต่ละ Vital (handler / schema / effect). เป็นแค่การผูก id↔ชื่อ. เช่น `DeleteActorVital` ถูก "ตั้งชื่อ" แล้ว แต่ soft-delete behavior/persistence ยังเป็นงานของ character_management lane (GT-011 + คำถามค้าง persistence characters).
- **ไม่ flip matrix** — report-only additive, ยกระดับ confidence ของ identity cohort เท่านั้น. ไม่แตะ ledger/matrix/src/canonical · ไม่รัน gate (เกณฑ์เขียวเดิม 108 = pytest 477/0 + canonGuard=0 + ledger 23 + domains 8 ยังใช้).

## follow-up ที่ stage ไว้ (ยังไม่ทำรอบนี้ — เป็น src change ต้องผ่าน gate)

เพื่อให้ decoder เลิกพิมพ์เลขดิบ ให้เติม 3 บรรทัดใน `current/pf_login_game_server_v141.py` (mechanical, pre-approved gameplay identity แต่แตะ src → ต้องรัน Windows gate `py -3` ให้เขียวก่อน commit):

```python
LOGOUT_VITAL = 0x1B40
DELETE_ACTOR_VITAL = 0x36DB
CHANNEL_LOCAL_TALK_MESSAGE_VITAL = 0xAC52
# ... และใน NAMES:
LOGOUT_VITAL: "LogoutVital",
DELETE_ACTOR_VITAL: "DeleteActorVital",
CHANNEL_LOCAL_TALK_MESSAGE_VITAL: "Channel_LocalTalkMessageVital",
```

verifier `tools/pf_vital_id_resolve_static.py` มี guard ที่ **จะ fail** ถ้า id หลุดเข้า NAMES แล้ว (guard "absent from v141 NAMES") — เมื่อ apply patch นี้ ต้องปรับ guard นั้นให้สลับเป็น "present + hash-match" ด้วย. บันทึกไว้ใน QUEUE.

## reproduce

```
py -3 tools/pf_vital_id_resolve_static.py GameClient/GameClient.local.bin capture_v141
# exit 0 = PASS (ยืนยันบน sandbox แล้ว: SHA pin + 6 golden named + 49 NAMES + 3 resolved + 3 semantic)
```
