# PF_CHAT_ECHO008 — render-tag cohort: vtable → get-type node + get-id slot → **plaintext class name** (static disasm)

รอบ 60 (2026-08-18 scheduled) · chief · report-only additive · binary `GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` · capstone 5.0.7 (CS_MODE_32, ImageBase 0x400000, PE section table parsed)

เป้า: ปิด **next-hop #2 (static option) ของ ECHO007 / LOCK milestone สำรอง (i)** = map cohort vtable `0xf35c2c..0xf36490` → get-type thunk → node แล้ว**เทียบกับ descriptor table 12-row** (ECHO006 §1) เพื่อดูว่าคลาสใด bake `+0x44` = channel ใด

> **ผลสรุปล่วงหน้า:** ทำได้เกินเป้า — พบว่า cohort vtable **แต่ละตัวมี method ที่สอง (col+0x10) รูปแบบ `mov ax,[id-slot]; ret`** ชี้ไปที่ .data id-slot ที่ผูกกับ **plaintext class name** ผ่าน registration table → **map ครบ 10 คลาส: vtable → +0x44 tag → id-slot → ชื่อคลาส → render id (539/540)** แบบ byte-exact static ทั้งหมด. cohort นี้ = ตระกูล **`Community_*Vital`** (AddFriend, AddBlackList, SoulMateMatch, …) ไม่ใช่ LocalTalk เอง — ตอกย้ำว่า render gate 539/540 เป็น **shared** และ `+0x44` = per-class identity (ยืนยัน ECHO007 พร้อม**ชื่อคลาสจริง**)
>
> **เกรด net ของ Q2 positive คงที่ = B** (ไม่ดันเป็น A): id ตัวเลข 16-bit ของแต่ละคลาสถูก **assign ตอน runtime** — .data id-slot ในอิมเมจเป็น filler ซ้ำ (0x8888/0x7F00/…) จึงยังผูก `0xAC52 → คลาส` static ไม่ได้ (เหลือ GT-012). แต่ **Q2 negative = A แข็งขึ้นอีก**: การเลือก tag ไม่แตะ wire เลย — มาจาก class identity ล้วน และตอนนี้ระบุ**ชื่อคลาส**ได้

---

## 1. Descriptor table `0xf363b4` — 12 rows stride 0x2C, resolve ครบ (byte-exact)

ทุก row 11 dwords. col+00 = get-type thunk (`mov eax,<node>; ret`) → type node; col+08/+1C/+20/+24/+28 = ค่าคงที่ร่วมทุก row (framework/shared handlers ตาม ECHO006 §1) — **ไม่มี column ใดชี้ไปที่ name pool** (ชื่อผูกทางอื่น = §3):

| row | vtable | get-type thunk | → node | +08 (const) |
|---|---|---|---|---|
| 0 | `0xf363b4` | `0x6422c0` | `0x1083fd8` | `0x401b20` |
| 1 | `0xf363e0` | `0x6425b0` | `0x1083f90` | `0x401b20` |
| 2 | `0xf3640c` | `0x642320` | `0x1083f84` | `0x401b20` |
| 3 | `0xf36438` | `0x6426f0` | `0x1083f6c` | `0x401b20` |
| 4 | `0xf36464` | `0x6427e0` | `0x1083f48` | `0x401b20` |
| 5 | `0xf36490` | `0x642360` | `0x1083f3c` | `0x401b20` |
| 6 | `0xf364bc` | `0x642940` | `0x1083f30` | `0x401b20` |
| 7 | `0xf364e8` | `0x642370` | `0x1083f24` | `0x401b20` |
| 8 | `0xf36514` | `0x642a80` | `0x1083f00` | `0x401b20` |
| 9 | `0xf36540` | `0x642aa0` | `0x1084044` | `0x401b20` |
| 10 | `0xf3656c` | `0x642250` | `0x1084038` | `0x401b20` |
| 11 | `0xf36598` | `0x642350` | `0x1083f54` | `0x401b20` |

shared handler columns (คงที่ทุก row): `+1C=0x645bf0 +20=0x710440 +24=0x642ab0 +28=0x9f17e0` — ตรง ECHO006 §1 เป๊ะ. cohort ของ ECHO007 3 ตัว (`0xf363e0/0c`, `0xf36490`) = row 1/2/5 ของตารางนี้ ส่วนอีก 7 ตัวอยู่ block vtable ที่ต่ำกว่า (`0xf35c2c..0xf35e10`) — layout เดียวกัน (shared cols ท้ายแถวตรงกัน) แต่ get-type เป็น `jmp thunk` (indirect)

## 2. Cohort get-id method (col+0x10) = `mov ax,[id-slot]; ret` — ตัวผูกชื่อคลาส

col+0x10 ของ cohort vtable แต่ละตัวชี้ไปที่ stub รูปแบบ `66 A1 <abs32> C3` (`mov ax, word [id-slot]; ret`) — คืน **16-bit vital-id** จาก .data slot ประจำคลาส. slot นั้นถูกเขียนโดย registration (§3) พร้อม plaintext name → จึง**ผูก vtable ↔ ชื่อคลาสได้ static**:

```
0x0063a5b0: 66 a1 68400801   mov ax, word [0x1084068]   ; get-id ของ vtable 0xf35c2c
0x0063a5b6: c3               ret
```

## 3. Name registration: `push <name>; call once-init-registry; store 16-bit id → .data slot`

pattern ต่อคลาส (linear, ทุกยูนิต 0x20 ไบต์, ปิดด้วย int3 padding):
```
0x00bf59e0: 68 ec65f300      push 0xf365ec              ; "Community_AddFriendVital"
0x00bf59e5: e8 ..            call 0x89c080              ; once-init singleton registry (@0x108cf90)
0x00bf59ea: 8bc8             mov ecx, eax               ; ecx = registry (this)
0x00bf59ec: e8 ..            call 0x89bd00              ; thiscall id-assign(name) -> ax
0x00bf59f2: 66a3 68400801    mov word [0x1084068], ax   ; *** store id -> slot ของคลาสนี้ ***
0x00bf59f9: c3               ret
```
- `0x89c080` = MSVC once-init guard ของ global registry singleton (magic `0x108cf90`, `_Init_thread`-style) — **ไม่ใช่ hash** ของชื่อ
- 29 registration blocks ต่อเนื่อง (`0xbf5980..0xbf5d0x`) เขียน id ลง slot ต่อเนื่อง `0x108405c..0x10840cc` (stride 2)
- **สำคัญ:** ค่าใน id-slot ที่อยู่ในอิมเมจเป็น **filler ซ้ำ** (`0x8888, 0x88, 0x7F00, 0x8777, 0x7778, 0x8F, …` วนซ้ำ, ชื่อคลาสที่ไม่เกี่ยวกันได้ค่าเดียวกัน) = **uninitialized** → id ตัวเลข **assign ตอน runtime** ผ่าน `0x89bd00` ตอน startup ยืนยันชัด ๆ ว่าอิมเมจไม่มี id จริง

## 4. ⭐ FULL binding map: vtable → +0x44 → id-slot → class name → render id

| vtable (ctor install) | `+0x44` const | get-id via | id-slot | **class name** | render id |
|---|---|---|---|---|---|
| `0xf35c2c` | `0x0c` | col+0x10→`0x63a5b0` | `0x1084068` | `Community_AddFriendVital` | **540** `[ทั่วไป]` |
| `0xf35c58` | `0x00` | col+0x10→`0x63a650` | `0x108406c` | `Community_RequestBeFriendVital` | 539 |
| `0xf35cb0` | `0x07` | col+0x10 | `0x1084074` | `Community_AddBlackListVital` | **540** |
| `0xf35cdc` | `0x04` | col+0x10 | `0x1084078` | `Community_RemoveBlackListVital` | **540** |
| `0xf35d8c` | `0x03` | col+0x10 | `0x108408c` | `Community_ChangeActorCommentVital` | **540** |
| `0xf35db8` | `0x01` | col+0x10 | `0x1084090` | `Community_SetReceiveActiveChangeVital` | **540** |
| `0xf35e10` | `0x06` | col+0x10 | `0x10840a0` | `Community_ThrowLetterInABottleVital` | **540** |
| `0xf36490` | `0x05` | col+0x10 | `0x10840b4` | `Community_ChangeActorPenNameVital` | **540** |
| `0xf3640c` | `0x00` | col+0x10 | `0x108409c` | `Community_TargetConfirmSoulMateMatchVital` | 539 |
| `0xf363e0` | `0x00` | col+0x10 | `0x1084098` | `Community_RequestorConfirmSoulMateMatchVital` | 539 |

**อ่านผล:**
- `+0x44` เป็น **per-class small-int identity code** (`0xc,7,4,3,1,6,5,0` — distinct ต่อคลาส) — ยืนยัน ECHO007 (immediate constant ใน ctor) **พร้อมชื่อคลาสจริง**
- render gate (`0x6405e7`, ECHO007 §2) อ่านแค่ 0-vs-nonzero → 539 (`+0x44==0`) / 540 `[ทั่วไป]` (`+0x44!=0`) — คลาสที่ได้ 539 ทั้งหมดเป็นกลุ่ม "confirm/request" (RequestBeFriend, SoulMate confirm ×2); ที่ได้ 540 เป็น action Vital (AddFriend, BlackList, Comment, …)
- cohort = ตระกูล **Community message Vital** — **ไม่ใช่ LocalTalk (`0xAC52`)** → 0xAC52 อยู่คนละ registration family; render gate นี้ shared ข้ามหลาย family (สอดคล้อง ECHO004: gate อ่าน object field ไม่ใช่ payload)

## 5. ทำไม Q2 ยังไม่ดัน B→A
เพื่อผูก `0xAC52 (LocalTalk) → คลาส → +0x44 → 539/540` ต้องรู้ **id ตัวเลข** ของแต่ละคลาส — แต่ §3 พิสูจน์ว่า id assign ตอน runtime (.data slot = filler ในอิมเมจ). static จึงได้แค่ **ชื่อคลาส ↔ vtable ↔ +0x44** (รอบนี้สำเร็จ) แต่ **id ↔ ชื่อคลาส** ต้องรัน. เหลือ:
- **runtime (GT-012, attended):** LocalTalk render label จริง → pin `0xAC52 → คลาส → +0x44` ปิด B→A
- **static (option):** เดินตัว `0x89bd00`/`0x89b220` id-assign ต่อ — แต่ถ้ามันดึงจาก config/counter (ไม่ใช่ pure fn ของชื่อ) จะปิด static ไม่ได้อยู่ดี (ต้นทาง id อยู่นอกอิมเมจ)

---

## verify (byte-exact · .text off = VA−0x400C00 · .rdata off = VA−0x401C00 — PE-parse ยืนยันตรง ECHO005–007)

| จุด | VA | file off | bytes | ความหมาย |
|---|---|---|---|---|
| descriptor row0 base (get-type dword) | `0xf363b4` | `0xb347b4` (rdata) | `c0226400` | → thunk `0x6422c0` |
| descriptor row5 base | `0xf36490` | `0xb34890` (rdata) | `60236400` | → thunk `0x642360` |
| get-id stub `0xf35c2c` (col+0x10) | `0x63a5b0` | `0x2399b0` | `66a168400801c3` | `mov ax,[0x1084068]; ret` |
| get-id stub `0xf35c58` (col+0x10) | `0x63a650` | `0x239a50` | `66a16c400801c3` | `mov ax,[0x108406c]; ret` |
| reg block CommunityCommandNotAllow | `0xbf5980` | `0x7f4d80` | `68c465f300e8f666caff8bc8e86f63caff66a35c400801c3` | push name→registry→store id 0x108405c |
| reg block AddFriend | `0xbf59e0` | `0x7f4de0` | `68ec65f300e89666caff8bc8e80f63caff66a368400801c3` | push name→registry→store id 0x1084068 |
| once-init registry guard | `0x89c080` | `0x49b480` | `6aff682b03bc0064…` | `_Init_thread`-style singleton (ไม่ใช่ hash) |
| id-slot base (.data) | `0x108405c` | (.data) | `8888 0088 007f 7787 7877 8f00 …` | filler = id runtime-assigned |

## grade
- **Q2 negative = A (ตอกย้ำหนักสุด + ชื่อคลาส):** tag เลือกจาก per-class `+0x44` identity ล้วน; ไม่มีเส้นทาง wire; ตอนนี้ระบุ**ชื่อคลาส**ของทั้ง cohort ได้ static
- **Q2 positive = B เดิม (net ไม่เปลี่ยน):** map ครบ vtable↔ชื่อคลาส↔`+0x44`↔539/540 แต่ **id ตัวเลข (`0xAC52` ↔ คลาส) = runtime-assigned** (id-slot อิมเมจ = filler) → ยังต้อง GT-012
- **ไม่ re-pin canonical / ไม่รัน Windows gate** (report-only additive; ไม่แตะ ledger/matrix/src) — เกณฑ์เขียวเดิม 108 (pytest 477/0 + canonGuard=0 + ledger 23 + domains 8) ยังใช้

## nonclaims
1. **ไม่** claim ว่า `Community_*` cohort = คลาสของ LocalTalk (`0xAC52`) — cohort นี้เป็น Community family; 0xAC52 อยู่คนละ registration (render gate เท่านั้นที่ shared)
2. **ไม่** ยืนยัน id ตัวเลข 16-bit ของคลาสใด — .data slot เป็น filler ในอิมเมจ (runtime-assigned)
3. `+0x44` เป็น sub-channel/category code ต่อคลาส; ความหมายเชิง label ปลายทางนอกเหนือ 539/540 (finer meaning ของค่า 1..0xc) ไม่ได้ decode รอบนี้
4. static ล้วน — ไม่มี client-observable claim (ชั้นนั้นเป็นของ GT-012 รอบใหญ่)

## next hop
1. **runtime (GT-012, attended):** จด LocalTalk render label — pin `0xAC52 → คลาส → +0x44` → ปิด B→A จบ
2. **static (option):** เดิน `0x89bd00`/`0x89b220` ต่อ — ยืนยันว่า id มาจาก config/counter (ต้นทางนอกอิมเมจ) เพื่อ **falsify "id เป็น pure hash ของชื่อ"** ให้ชี้ขาด (จะปิดความหวังผูก id static)
