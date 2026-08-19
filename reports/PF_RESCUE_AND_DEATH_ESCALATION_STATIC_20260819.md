# PF RESCUE-AND-DEATH-ESCALATION-001 — ปุ่ม "ล้มเลิกการช่วยเหลือ" คือปุ่มอะไร คำว่า `Rescue` มาจากไหน และประตูสุดท้ายของวง "ตาย → คืนชีพ" คือค่าอะไรที่ field ไหน

**2026-08-19 · assistant lane (ลูกมือของ Chief) · static RE, report-only, additive · ไม่แตะ src/ ไม่แตะ ledger ไม่แตะ coverage ไม่ commit**
**ไบนารีหลักฐาน:** `GameClient/GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` (ตรงกับที่ HP-DEATH-001 / DAMAGE-MODEL-001 ใช้)
**หลักฐานชั้นสอง (อ่านอย่างเดียว):** `GameClient/Data/GUI/Model/*.model` — ไฟล์ layout ของ UI เป็น XML ธรรมดา ไม่เข้ารหัส
**ไม่ได้รัน:** ไม่บูต server · ไม่เปิด GameClient · ไม่เปิด socket · ไม่แตะ DB · ไม่แตะ capture ที่เป็นหลักฐาน · ไม่ commit

---

## 0. เรื่องนี้มาจากไหน (อ่านย่อหน้านี้ย่อหน้าเดียวก็พอ)

**ใครถาม.** หลังรอบใหญ่ #6 (GT-021, 2026-08-19) ผู้เทสส่งเฟรมจน HP=0 แล้วหน้าต่าง `Main_Dead` เปิดค้างเกิน 4 นาที ไม่ escalate เป็น `IsDead` ไม่มี `Common_Death` เลย · ผู้เทสยังเห็นว่า tooltip ของปุ่มในหน้าต่างนั้นมีคำอังกฤษ `Rescue` ปนในประโยคไทย ป้ายปุ่มบนจอคือ "ล้มเลิกการช่วยเหลือ" และกดแล้วไม่มีอะไรเกิดขึ้นบนจอ · Chief สั่งให้ตามสองเรื่องนี้แบบ static

**อะไรคือหลักฐาน.** disassembly แบบเดินจาก xref จริง (capstone + byte-scan ของ `E8 rel32` และ dword immediate) ไม่ใช่การ "สแกนทั้งอิมเมจแบบ linear" · บวกกับไฟล์ layout `Main_Dead.model` / `Main_Panel_Rescue.model` / `Common_Death.model` ที่เป็น XML อ่านได้ตรง ๆ

**อะไรคือข้อสรุป (สองบรรทัด).**
1. **`Rescue` ไม่ได้อยู่ในไบนารีในฐานะสตริงเดี่ยว** — สิ่งที่มีจริงคือ `L"Main_Panel_Rescue"` (หน้าต่างที่ "คนอื่นกำลังช่วยชุบชีวิตคุณ"), คลาส `MainPanelRescueEventHandler`, และ `L"CURSOR_RESCUE"` · คำว่า `Rescue` ที่ผู้เทสเห็นมาจาก **ตารางข้อความภายนอก `TipID="438"`** ไม่ใช่จากอิมเมจ · และปุ่มที่กดคือ `BUTTON_DIE` ซึ่ง **มี code path ส่งออกสายจริง** (`ActionVital` action `0xEA7C`) แต่ทันทีหลังส่งมันสั่งปิดหน้าต่าง แล้ว `0x44A540` ที่รันทุกเฟรมเปิดหน้าต่างนั้นกลับมาทันทีในเฟรมถัดไป ⇒ **"ไม่มีอะไรเกิดขึ้นบนจอ" คือพฤติกรรมที่โค้ดกำหนดไว้ ไม่ใช่ปุ่มตาย**
2. **ประตูสุดท้ายไม่ใช่ "เฟรมที่สอง" แต่เป็น "ค่า"** — `Common_Death` เปิดโดย `CMyActor::Update` เรียก vtable `+0x3C` (`0x454A70`) ซึ่งเป็นจริงเมื่อ **`attr.u32[+0x44] == 0` และ `attr.f32[+0x58] <= 0.0f`** เท่านั้น · client **ไม่ลด `+0x58` เอง** และ **การไม่ส่ง mask bit `0x0080` ไม่ได้แปลว่า timer กลับเป็น 0** เพราะ `BasicAttr::Merge` คัดลอกค่าเดิมไปข้างหน้าเมื่อบิตไม่ถูกเซ็ต ⇒ **ต้องส่งบิต `0x0080` ออกไปพร้อมค่า `<= 0.0f` แบบชัดเจน**

**อะไรคือ nonclaim.** ไม่อ้างอะไรเกี่ยวกับ ORIGINAL server (ปิดไปแล้ว ไม่เคย publish) · ไม่อ้างว่าเคยเห็น `Common_Death` เรนเดอร์ · ไม่ได้ถอด `$pcz` เพื่ออ่านข้อความ TipID 438 จริง · ไม่ได้พิสูจน์ว่า "ทั้งอิมเมจไม่มีที่ไหนเขียน `+0x58`" (ดู §3.4)

**เกรด.** สตริง/หน้าต่าง/handler/wire ของ `PartyCmdVital` · เงื่อนไข escalate · polarity ของ merge = **① byte-proof** · เหตุผลว่าทำไมกดปุ่มแล้วจอนิ่ง = **② structural inference** (ยังไม่มี runtime pass ยืนยันว่าเฟรม `0xEA7C` ออกจริง)

> 📌 **หมายเหตุถึงคนที่จะ commit:** `.gitignore:8` มีกฎ `/reports/*` ⇒ ไฟล์นี้ถูก ignore โดย default (ยืนยันด้วย `git check-ignore -v`) ตามบทเรียนรอบ 86 ถ้าจะอ้างไฟล์นี้เป็นหลักฐานที่ไหน **ต้อง `git add -f` ให้มันมองเห็นได้จาก fresh clone ก่อน**

---

## 1. เกรดหลักฐาน

| เกรด | ความหมาย |
| --- | --- |
| **① byte-proof** | span ของ instruction ที่ address คงที่ / slot ใน vtable / literal / ข้อความใน XML ที่อ่านได้ตรง ๆ · สร้างต่อได้ |
| **② structural inference** | ข้อสรุปจาก ① บวกรูปทรงของโค้ด · สร้างต่อได้ **โดยต้องพูดว่าอนุมาน** |
| **③ guess** | ไม่ได้มาจากไบนารี · **ลิสต์ไว้เฉย ๆ ไม่เอาไปสร้างต่อ** |

---

## 2. งานที่ (1) — สตริง `Rescue` อยู่ที่ไหนจริง ๆ

### 2.1 ① byte-proof — สำมะโน `Rescue` ทั้งอิมเมจ

สแกนทั้งไฟล์ (ทุก section) ทั้งแบบ ASCII และ UTF-16LE ได้ครบดังนี้ — **ไม่มีตัวไหนเป็นสตริง `L"Rescue"` เดี่ยว ๆ**

| ที่อยู่ | ชนิด | เนื้อ | เป็นอะไร |
| --- | --- | --- | --- |
| `0xF0D52C` | UTF-16 | `Main_Panel_Rescue` | **ชื่อหน้าต่าง UI** |
| `0xF0D542` | UTF-16 | `Rescue` | ❗ **ไม่ใช่สตริงของตัวเอง** — `0xF0D52C + 11*2 = 0xF0D542` คือหางของ `Main_Panel_Rescue` (`Main_Panel_` = 11 ตัวอักษร) · dword-ref ทั้งอิมเมจ = **0 ที่** |
| `0xF0CA7C` | UTF-16 | `CURSOR_RESCUE` | ชื่อ cursor ในตารางชื่อ cursor (`CURSOR_ITEMUNLOCK`, `CURSOR_ITEMLOCK`, `CURSOR_TRANSFORM`, …) ถูก push ที่ `0x437C5E` ที่เดียว |
| `0xF0DDC8` / `0xF0DE1C` | UTF-16 | `.\Data\GC\V\M079_000_000_RESCUE.avt`, `M079_000_000_RESCUE` | **ไม่เกี่ยว** — เป็นชื่อ asset ท่าทางของ NPC ตัว `M079` |
| `0x1024028` → ชื่อที่ `0x1024030` | ASCII (RTTI) | `.?AVMainPanelRescueEventHandler@@` | ตัวบรรยายคลาส ผูกกับ type node `0x107CED8` โดย thunk ที่ `0xBE2B30` |
| `0x1023FF8` → ชื่อที่ `0x1024000` | ASCII (RTTI) | `.?AVMainPanelRescueEditorEventHandler@@` | รุ่น editor · ผูกกับ node `0x107CEE4` โดย thunk ที่ `0xBE2AF0` |

**xref ของ `L"Main_Panel_Rescue"` (`0xF0D52C`) มี 4 ที่ ครบทั้งหมด:**

| ที่อยู่ | ทำอะไร |
| --- | --- |
| `0x4481AA` | `FindWindow` แล้ว **ปิด** — อยู่ในตัวจัดการ input ที่เงื่อนไข `[msg+4]==0x100 && [msg+8]==0x1B` (**คีย์ ESC**) |
| `0x5D9AE5` | ตารางเทียบชื่อหน้าต่าง → **สร้าง handler** `0x51D8F0` (ขนาด `0x38`) |
| `0x62CCCB` | `FindWindow` แล้วยิงข้อความ `L"ReviveAction_KeyDown"` เข้า window vtable `+0x210` — สาขา opcode `0x26` |
| `0x62CD8A` | **`OpenWindow`** แล้วยิง `L"ReviveAction_Update_String"` — สาขา opcode `0x27` |

span ตรึงไว้: `0x4481A9` = `682cd5f000 b908070901 e8486d6500` · `0x62CCCA` = `682cd5f000 b908070901 e827224700` · `0x62CD89` = `682cd5f000 b908070901 e878394700`

### 2.2 ① byte-proof — `Main_Panel_Rescue` คือหน้าจอ "มีคนกำลังชุบชีวิตคุณ"

vtable ของ `MainPanelRescueEventHandler` = **`0xF1FC48`** (สล็อต 0 = `0x51D820` = `mov eax,0x107CED8 ; ret` ซึ่งเป็น type-node getter ของคลาสนี้ตรง ๆ)

* `vt+0x60` = `0x51D830` — ผูกลูก 3 ตัว: `L"PANEL_REVIVE_ACTION"` (`0xF1FD10`) → `[this+0x14]`, `L"ReviveAction_Btns"` (`0xF1FCEC`) → `[this+0x18]`, `L"Common_ProgressBar2"` (`0xF1FCC4`)
* สตริงอื่นในตัวคลาส: `L"ReviveAction_Update_String"`, `L"ReviveAction_KeyDown"`, `L"Revive_Char"`, `L"Char_img"`, `%sbt_saveurlife_%c.tga`, `%sICON_False_S.tga`

และไฟล์ layout ยืนยันตรงกัน — `GameClient/Data/GUI/Model/Main_Panel_Rescue.model`:

```xml
<BigUIBaseWindow ID="Main_Panel_Rescue" Size="(380, 135)" …>
  <UIPanel ID="PANEL_REVIVE_ACTION">
    <UIItemList ID="ReviveAction_Btns" ItemNumPerLine="5" …/>
    <UIProgressBar ID="Common_ProgressBar2" ProgressBarMaxValue="100" …/>
  </UIPanel>
  <UILabel … TextID="1525" …/>
</BigUIBaseWindow>
<EditorExtraData>
  <ControlWrapData InsertedItemName="Revive_Char" InsertedItemNumber="5" …/>
</EditorExtraData>
```

⇒ ช่องคน 5 ช่อง + progress bar 0..100 + ป้ายข้อความ · **ระบบ rescue มีจริงและเป็นระบบผู้เล่นช่วยผู้เล่น** ตามที่บันทึกความจำโปรเจกต์เดาไว้

### 2.3 ① byte-proof — สายของ rescue คือ `PartyCmdVital` (id `0x2466`) ไม่ใช่ `ReliveVital`

opcode `0x25` / `0x26` / `0x27` / `0x49` ถูก dispatch ในฟังก์ชัน **`0x62C840`** (`eax = [msg+0x10]`, เป็น slot ใน vtable `0xF348B8`) ฟังก์ชันเดียวกันนี้ **ส่งออกสาย** ด้วย vital ที่จองจาก pool `0x107CDC0` → ctor `0x62E270`:

```
0062E274  c7 00 7c49f300     mov [obj], 0xF3497C     ; vtable
0062E28F  88 48 14           byte  [obj+0x14] = 0    ; command
0062E292  89 48 18           dword [obj+0x18] = 0    ; identity lo
0062E295  89 48 1C           dword [obj+0x1C] = 0    ; identity hi
```

| สมบัติ | ค่า |
| --- | --- |
| ชื่อคลาส (literal ที่ `0xF349EC`) | **`PartyCmdVital`** |
| id (PF-NAMEID-HASH-001) | **`0x2466`** — anchor ตรวจซ้ำแล้ว: `ReliveVital`=`0x1AD4`, `UpdateAttrVital`=`0x309A`, `ActorAttr`=`0x12AD`, `NPCAttr`=`0x0AD5` |
| sizeof (`0x6217D0`) | `0x20` |
| serializer (`vt+0x18`) | `0x74E310` — wire = **`u8 @+0x14` tag `0x08`** แล้ว **`qword @+0x18` tag `0x32`** |
| inbound (`vt+0x1C`) | **`0x62EA70` — handler จริง ไม่ใช่ stub `0x710440`** |
| outbound (`vt+0x20`) | `0x710440` |

inbound `0x62EA70` หา module ชื่อ **`"PartyModule_Client"`** (`0xF0DA14`, char*) จาก registry `[0x1032EC4]+0x130` แล้วส่งต่อให้ `0x62D0E0`

**คำสั่งที่ client ส่งออกเองในสาขานี้** (ตรึง byte แล้ว):

| ที่อยู่ | `byte +0x14` | span |
| --- | --- | --- |
| `0x62CB2A` | **`0x0C`** | `c640140c 8b4e20 894818` |
| `0x62CBA4` | **`0x0D`** | `c640140d 8b4e20 894818` |

ทั้งคู่ตามด้วย `call 0x4011A0 ; mov ecx,eax ; call 0x5DD800` = ส่งจริง

### 2.4 ① byte-proof — ปุ่มในหน้าต่าง `Main_Dead` คือปุ่มอะไร (ตัวชี้ขาดของ lead นี้)

`GameClient/Data/GUI/Model/Main_Dead.model` ทั้งไฟล์มีคอนโทรลเดียว:

```xml
<BigUIBaseWindow ID="Main_Dead" Size="(163, 58)" TipID="438" DisplayLevel="2" …>
  <Controls>
    <UIButton ID="BUTTON_DIE" Name="放棄救援按鈕" Size="(55, 55)"
              TextID="1648" FontStyleID="142" TipID="438" …>
      <FilePath>.\Data\GUI\Main\Bt_Main_ReviveCancel.tga</FilePath>
    </UIButton>
  </Controls>
</BigUIBaseWindow>
```

* ชื่อภายในภาษาจีน `放棄救援按鈕` = **"ปุ่มล้มเลิกการช่วยเหลือ"** — ตรงกับป้ายไทยที่ผู้เทสเห็นเป๊ะ
* texture คือ `Bt_Main_ReviveCancel.tga` ⇒ **"กากบาท" ที่เห็นคือ `BUTTON_DIE` ตัวเดียวกัน** ไม่มีปุ่ม X ของกรอบหน้าต่างแยกต่างหากในหน้าต่างนี้
* `TipID="438"` ⇒ **ข้อความ tooltip อยู่ในตารางข้อความภายนอก ไม่ได้อยู่ในไบนารี** — นี่คือที่มาของคำว่า `Rescue` ที่ปนภาษาไทย (ผู้แปลไทยแปลไม่หมด) · ตาราง `Data/B_TEXTDATA_TH.pc_` ขึ้นต้นด้วย magic `$pcz` และเป็นข้อมูลบีบอัด/เข้ารหัส — **ไม่ได้ถอดในรอบนี้**

และฝั่งไบนารีก็ยืนยันว่ามีลูกตัวเดียว: `MainDeadEventHandler` vtable `0xF1F550`, `vt+0x60` = `0x5183D0` ผูก `L"BUTTON_DIE"` (`0xF1F5CC`) ที่ `0x5183D2` (`68ccf5f100`) เข้า `[this+0x14]` — **ไม่มีการผูกลูกตัวอื่นเลยในฟังก์ชันนั้น**

### 2.5 ⭐ คำตอบชี้ขาด — การกดปุ่มนั้นมี code path ส่งอะไรออกสายไหม

**มี** และมันคือ `ActionVital` action `0xEA7C` (พี่น้องของ `0xEA7D` = attack ที่ SCENE-006/007 เคยบันทึก)

`vt+0x18` = `0x5184C0` เกี่ยว handler `0x518450` เข้ากับปุ่มด้วย `0x57A090` (event token `[0x1090DC0]`)
`0x518450` ทั้งตัว:

```
00518450  56 8b f1                push esi ; esi = this
00518453  83 7e 10 00 / 74 5a     if ([this+0x10] == 0) -> 0x5184B3 (ไม่ทำอะไรเลย)      <- gate A
00518459  e8 42 8d ee ff          call 0x4011A0            ; net/session singleton
0051845E  85 c0 / 74 44           if (== 0) -> 0x5184A6 (ข้ามการส่ง ไปปิดหน้าต่าง)      <- gate B
00518462  6a 00 / 68 0ca9f000 /   pool alloc (0x102D1C0, "file", 0)                      <- gate C
          b9 c0d10201 / e8 …
00518473  85 c0 / 74 2f           if (== 0) -> 0x5184A6
00518477  … 66 89 48 4a           [vital+0x4A] = current target id (word)
00518493  c7 40 30 7c ea 00 00    [vital+0x30] = 0xEA7C
0051849A  e8 01 8d ee ff          call 0x4011A0
005184A1  e8 5a 53 0c 00          call 0x5DD800            ; *** ส่งจริง ***
005184A6  8b 4e 10 / … / ff d0    window->vtable[+0x20C]() ; *** ปิดหน้าต่าง ***
```

**สิ่งที่ต้องอ่านคู่กัน:** ทั้งเส้นที่ส่งและเส้นที่ไม่ส่ง **ไปลงที่ `0x5184A6` เหมือนกัน คือปิดหน้าต่าง** และหน้าต่างนี้ถูกเปิดใหม่โดย `0x44A540` ซึ่ง `CMyActor::Update` เรียกทุกเฟรม (`0x44E828 → 0x44A540`) ตราบใดที่ `vt+0x40` (`HP==0 && timer > 0`) ยังจริง

**② structural inference:** สิ่งที่ผู้เทสเห็น ("กดแล้วจอนิ่ง") คือ **ปิด-แล้วเปิดใหม่ภายในเฟรมเดียว** ไม่ใช่ปุ่มที่ไม่ทำงาน

**หยุดที่ไหนถ้าไม่มีเฟรมออกสายจริง** — มีได้ 3 จุดเท่านั้น เรียงจากเป็นไปได้มากไปน้อย:

| gate | เงื่อนไข | ความหมาย |
| --- | --- | --- |
| **A** `[handler+0x10] == 0` | framework ยังไม่ผูก window object เข้า handler | handler จบทันที **ไม่ปิดหน้าต่างด้วยซ้ำ** |
| **B** `0x4011A0() == 0` | singleton การส่ง (`[0x1081A90]`) ยังไม่ถูกสร้าง | ปิดหน้าต่างแต่ไม่ส่ง |
| **C** pool alloc คืน 0 | หน่วยความจำหมด | ปิดหน้าต่างแต่ไม่ส่ง |

**🔴 nonclaim ที่สำคัญที่สุดของ lead นี้:** เราพิสูจน์ **ไม่ได้** จาก static ว่ากดแล้วเฟรมออกหรือไม่ออก · ถ้าจอ "นิ่ง" แต่หน้าต่างยังอยู่ นั่นสอดคล้องกับทั้ง "ส่งแล้ว" และ "gate B/C ตก" · ตัวแยกที่ถูกที่สุดอยู่ใน §7 (GT-B)

### 2.6 ① byte-proof — ESC ปิด `Main_Panel_Rescue` แล้วส่ง action `0xEA80`

`0x448180` (ผู้เรียกเดียว: `0x4066BE`):

```
0044819A  cmp dword [msg+4], 0x100     ; class ของ event
004481A3  cmp dword [msg+8], 0x1B      ; VK_ESCAPE
004481A9  FindWindow(L"Main_Panel_Rescue") -> ถ้าเจอ เรียก vtable[+0x20C] (ปิด)
004481C8  ecx = [0x1032EC4] ; call 0x44D7F0
```

`0x44D7F0`:

```
0044D7F3  eax = [player+0x10]
0044D7F6  test al,0x10        / je  -> return false
0044D7FA  test eax,0x100000   / je  -> return false
0044D804  call 0x4A0970(player+0x40)
0044D80B  push 0xEA80 ; call 0x44D260     ; ส่ง ActionVital action 0xEA80
```

**② structural inference:** `0xEA80` คือ action "ยกเลิก/หยุดสิ่งที่กำลังทำ" และ ESC บนหน้าต่าง rescue = ยกเลิกการชุบชีวิต · ที่เป็น ① คือ literal `0xEA80` เงื่อนไขบิต `0x10`/`0x100000` และเส้น call

### 2.7 ① byte-proof — โรงงานหน้าต่าง (ยืนยันการจับคู่ชื่อ↔คลาส)

ตารางเทียบชื่อหน้าต่างที่ `0x5D9AE4`/`0x5DA157` (สายเปรียบเทียบ wide-string ทีละ 2 ตัวอักษร):

| หน้าต่าง | ขนาด object | ctor | vtable |
| --- | --- | --- | --- |
| `L"Main_Panel_Rescue"` | `0x38` | `0x51D8F0` | `0xF1FC48` (`MainPanelRescueEventHandler`) |
| `L"Main_Dead"` | `0x18` | `0x5183A0` (`c706 50f5f100` → `0xF1F550`) | `0xF1F550` (`MainDeadEventHandler`) |

---

## 3. งานที่ (2) — ประตูสุดท้ายของวง "ตาย → คืนชีพ"

### 3.1 ① byte-proof — อะไรเปิด `Common_Death` เป๊ะ ๆ

`CMyActor` vtable `0xF0D7A8` → `+0x18` = `0x44E4E0` = `CMyActor::Update` (รับ frame-delta ที่ `[esp+0xA8]`) · ภายในนั้น:

```
0044E58D  8b 06                 eax = this->vtable
0044E58F  8b 50 3c              edx = vtable[+0x3C]        <-- IsDead / timer-elapsed
0044E592  8b ce / ff d2         call edx
0044E596  84 c0 / 0f 84 86…     ถ้า false -> ข้ามไป 0x44E624 ทั้งบล็อก
0044E59E  FindWindow(L"Common_Death")  (0xF0D860)
0044E5AF  75 1b                 เปิดอยู่แล้ว -> ข้าม
0044E5B1  push 0x1090958 ; push 1 ; push 0x102ADE0 ; push 0xF0D860
0044E5C7  e8 44 21 65 00        call 0xAA0710              ; *** OpenWindow(L"Common_Death") ***
0044E5CC  FindWindow(0xF0D268) -> ถ้าเจอ: 0x43E010(0,0) แล้วปิดหน้าต่างนั้น
0044E5F8  FindWindow(0xF0D2A8) -> ถ้าเจอ: 0x43E1D0(0,0) แล้วปิดหน้าต่างนั้น
```

span ตรึง `0x44E58D` (63 ไบต์): `8b068b503c8bceffd284c00f84860000006860d8f000b908070901e85309650085c0751b68580909016a0168e0ad02016860d8f000b908070901e844216500`

**⇒ ไม่มีเงื่อนไขอื่นเลย ไม่มี timer แยก ไม่มีนับเฟรม ไม่มี state machine — มีแค่ `vt+0x3C` ตัวเดียว**

### 3.2 ⭐ ① byte-proof — เงื่อนไขจริงในโค้ด (คำตอบของคำถามชี้ขาด)

`CMyActor`/`CNetActor` vtable `+0x3C` = `0x454A70` ทั้งตัว:

```
00454A70  56 8b f1                   this
00454A73  8b 06 / 8b 50 74 / ff d2   attr = this->GetAttr()   (vtable +0x74 = 0x44C630 = mov eax,[ecx+0x348])
00454A7A  0f 57 c0                   xmm0 = 0.0f
00454A7D  0f 2f 40 58                comiss xmm0, [attr+0x58]      ; เทียบ 0.0 กับ timer
00454A81  72 2e                      jb  -> return FALSE           ; CF=1 คือ 0.0 < timer  (หรือ NaN)
00454A83  8b 86 48 03 00 00          eax = [this+0x348]
00454A89  85 c0 / 74 24              null -> return FALSE
00454A8D  80 be 58 03 00 00 00       cmp byte [this+0x358], 0
00454A94  74 0f                      == 0 -> ไปสาขา BasicAttr
00454A96  33 c9 / 39 88 a8 01 00 00  return ([attr+0x1A8] == 0)    ; HP ชุดสำรอง (scene category 8)
00454AA5  33 d2 / 39 50 44           return ([attr+0x44]  == 0)    ; *** CURRENT HP ***
```

**เงื่อนไขที่ต้องเป็นจริง ครบชุด ไม่มีอย่างอื่น:**

| # | field | offset ใน `BasicAttr` | mask bit บนสาย | tag/ความกว้าง | ต้องเป็น |
| --- | --- | --- | --- | --- | --- |
| 1 | current HP | `+0x44` | **`0x0004`** | `0x14` / 4 ไบต์ u32 | **`0`** |
| 2 | death/dying timer | `+0x58` | **`0x0080`** | **`0x2A` / 4 ไบต์ f32** | **`<= 0.0f` แบบ ordered** (0.0 ใช้ได้ · ค่าลบใช้ได้ · **NaN ใช้ไม่ได้** เพราะ `comiss` ตั้ง CF=1 ตอน unordered ⇒ `jb` ถูกกิน ⇒ คืน false) |
| 3 | ตัวเลือกคู่ HP | `[actor+0x358]` | — | — | ต้องเป็น `0` เพื่อให้อ่าน `+0x44`; ถ้าไม่ใช่ 0 จะไปอ่าน `+0x1A8` แทน (ผู้เขียนเดียวคือ `0x4564B3`, เป็น `scene_category == 8`) |

เทียบกับพี่น้อง `vt+0x40` (`0x454AC0`) ที่คุม `Main_Dead`:

```
00454ACA  f3 0f 10 40 58        xmm0 = [attr+0x58]
00454ACF  0f 2f 05 9c98f000     comiss xmm0, [0xF0989C]   ; ค่าคงที่ = 0.0f
00454AD6  76 2e                 jbe -> return FALSE       ; ต้อง timer > 0
```

**⇒ สอง predicate นี้เป็นจริงพร้อมกันไม่ได้บน snapshot เดียว** (ยืนยัน E2 ของ HP-DEATH-ERRATA-001 อีกทาง) · และ `Main_Dead` ยังมี gate เพิ่มที่ `0x44A56D`: `timer >= DURATION_DYING - 0.5` = `20 - 0.5` = **19.5** (`DURATION_DYING` = int global `0x102249C` = **20**, ผู้อ่านเดียวคือ `0x44A572`)

**คำตอบตรง ๆ ต่อสมมติฐาน "ต้องมีเฟรมที่สองที่มี `hp_death_timer <= 0`":**
สมมติฐาน **ถูกในทางปฏิบัติแต่ผิดในเหตุผล** — โค้ดไม่รู้จักคำว่า "เฟรมที่สอง" เลย มันรู้จักแค่ **ค่า** · ที่ต้องมีเฟรมที่สองก็เพราะเฟรมแรกของโปรไฟล์ `dying_hold` **ตั้ง `+0x58` = 20.0 ไปแล้ว** และไม่มีใครลดมันลง (§3.4) ⇒ ต้องมีเฟรมที่มาเขียนทับด้วยค่า `<= 0.0`
ถ้าเฟรมแรกส่ง `HP=0` โดย **`+0x58` ยังเป็น 0.0** (ค่าเริ่มต้นจาก ctor) เฟรมเดียวก็ escalate ทันที และ `Main_Dead` **จะไม่เปิดเลย** (เพราะ 19.5 > 0 ⇒ `ja` ⇒ ข้าม)

### 3.3 ⭐ ① byte-proof — "ไม่ส่งบิต `0x0080`" **ไม่เท่ากับ** "timer = 0"

นี่คือกับดักที่ทำให้แผนการทดลองพลาดได้ง่ายที่สุด

**(ก) ค่าเริ่มต้นของ object ใหม่** — ctor ของ `BasicAttr`:

```
00464AC6  b9 ffff0000 / 66 89 4e 70    word [obj+0x70] = 0xFFFF      ; change mask เริ่มต้น = ติดทุกบิต
00464AE3  movss xmm0, [0xF0DD9C]       ; = 400.0f
00464AF2  movss [obj+0x54], xmm0
00464AF7  xorps xmm0, xmm0
00464AFA  word  [obj+0x5C] = 0 ; word [obj+0x5E] = 1                 ; level เริ่มที่ 1
00464B02  dword [obj+0x44] = [obj+0x48] = [obj+0x4C] = [obj+0x50] = 0
00464B0E  f3 0f 11 46 58               movss [obj+0x58], 0.0f        ; *** timer เริ่มที่ 0.0 ***
```

**(ข) ฝั่งอ่านจากสาย** — `BasicAttr::Serialize` `0x4656F0` สาขาอ่านเริ่มที่ `0x465850` อ่าน mask เข้ามาก่อน แล้วอ่านเฉพาะฟิลด์ที่บิตติด:

```
004658E8  f6 03 80 / 74 0f             ถ้าบิต 0x80 ไม่ติด -> ข้าม
004658ED  6a 04 / 8d 46 58 / 50 / 6a 2a / 8bcf / e8 …   read f32 tag 0x2A -> [obj+0x58]
```

**(ค) ฝั่งรวมเข้ากับของเดิม** — `BasicAttr::Merge` `0x465610` (`vt+0x24`):

```
00465661  0f b7 47 70            eax = word [this+0x70]     ; mask ของ "this"
00465671  a8 04 / 75 06          ถ้าบิต 0x04 ติด -> ข้าม (ค่าจากสายชนะ)
00465675  8b 56 44 / 89 57 44    ไม่ติด -> [this+0x44] = [src+0x44]   (เอาค่าเดิมมาเติม)
...
004656A3  84 c0 / 78 06          ถ้าบิต 0x80 ติด (sign ของ al) -> ข้าม
004656A7  d9 46 58 / d9 5f 58    ไม่ติด -> [this+0x58] = [src+0x58]
```

**(ง) ใครเป็น `this` ใครเป็น `src`** — จาก inbound handler ของ `UpdateAttrVital` `0x5F2400`:

```
005F24C9  mov ecx,[ebx]        ; ebx = &vital[+0x10]  => ecx = attr ที่เพิ่งถอดจากสาย
005F24CD  mov edx,[eax+0x10] / call edx      ; ขอ id
005F24E2  call 0x5F8C30                      ; ค้น attr เดิมใน [0x1032EC4]+0x130
005F24E7  edi = ผลลัพธ์ (attr เดิม)
005F2504  8b 0b / 8b 01 / 8b 50 24 / 57 / ff d2
          ; incoming->vtable[+0x24]( existing )   <=== incoming คือ this, existing คือ src
```

**⇒ สรุปเชิงปฏิบัติการ (①):**
* บิตติด → **ค่าจากสายชนะ**
* บิตไม่ติด → **ค่าเดิมถูกคัดลอกไปข้างหน้า** ไม่ได้กลับเป็น 0
* ดังนั้นหลังจาก `dying_hold` ส่ง `+0x58 = 20.0` ไปแล้ว **การ "ละบิต `0x0080`" ในเฟรมถัดไปจะทำให้ timer ยังเป็น 20.0 ตลอดไป**

> ⚠️ นี่คือจุดที่ผู้อ่าน RUNTIMERES-ACTOR-ENTRY-001 §4 ต้องระวัง: สูตร "ส่ง `current_hp = 0` และ **ละ** bit `0x0080`" ใช้ได้ก็ต่อเมื่อ actor นั้น **ยังไม่เคยถูกส่ง `0x0080` เป็นบวกมาก่อน** · ถ้าเคยส่ง ต้องส่ง `0x0080 = 0.0f` แบบชัดเจน

### 3.4 ② — client ลด `+0x58` เองไหม: ไม่พบผู้ลด

* **① ผู้อ่าน `+0x58` ที่รันทุกเฟรม มี 3 ที่ และทั้งสามอ่านอย่างเดียว:** `0x44A56D` (gate ของ `Main_Dead`), `0x454ACA` (`vt+0x40`), `0x454A7D` (`vt+0x3C`)
* **① `CMyActor::Update` (`0x44E4E0`) ลดนาฬิกาจริง — แต่เป็นนาฬิกาคนละตัว:** มันลด **global float `[0x1031790]`** ด้วย frame delta แล้ว clamp ที่ 0 (`0x44E53F..0x44E574`) · global ตัวนี้ถูกตั้งค่าที่ `0x4250A2` เป็น `[0xF092A4]` ทันทีหลังส่ง `ActionVital` (`0x425095 call 0x5DD800`) ⇒ เป็น **cooldown ของ action** ไม่ใช่ death timer · xref ทั้งหมดมี 5 ที่ (`0x4250A6`, `0x44E481`, `0x44E543`, `0x44E56A`, `0x44E574`)
* **② สำมะโนผู้เขียน `[reg+0x58]`:** ทั้ง `.text` มี candidate store ไปยัง `[reg+0x58]` = **394 จุด** (`movss` 115, `fstp` 37, `mov r/m,imm` 43, `mov r/m,reg` 242) · กรองด้วยเงื่อนไข "base register เดียวกันแตะ offset ลายเซ็นของ `BasicAttr` (`+0x44` / `+0x5E` / mask `+0x70`) ในระยะ ±0xC0 ไบต์" เหลือ **6 จุดที่ลายเซ็นแรง** และทุกจุดเป็น ctor หรือคัดลอกฟิลด์ต่อฟิลด์ ไม่มีการคำนวณ:

| ที่อยู่ | เป็นอะไร |
| --- | --- |
| `0x464B0E` | ctor → `0.0f` |
| `0x464BB0` | copy ctor (`fld [edi+0x58] ; fstp [esi+0x58]`) |
| `0x4656AA` | `Merge` (คัดลอกค่าเดิมมาเมื่อบิตไม่ติด) |
| `0x4B19BC`, `0x5AC8CA` | copy ctor ของคลาสพี่น้อง (คัดลอกล้วน) |
| `0x831B70` | ctor ของคลาสอื่นที่ layout ใกล้เคียง |
| (สายอ่านจากสาย) `0x4658EF` | เขียนจาก wire เมื่อบิต `0x80` ติด |

> 🔴 **ขอบเขตของ negative นี้:** ฟิลเตอร์ข้างบนเป็น **heuristic ไม่ใช่การพิสูจน์** · เรา **ไม่อ้าง** ว่า "ทั้งอิมเมจไม่มีที่ไหนลด `+0x58`" · สิ่งที่อ้างได้คือ (ก) ผู้อ่านทุกเฟรมทั้ง 3 ตัวอ่านอย่างเดียว ①, (ข) `CMyActor::Update` ลดนาฬิกาตัวอื่น ①, (ค) ในกลุ่มที่มีลายเซ็น `BasicAttr` ไม่มีตัวไหนลด ② · และ (ง) **GT-021 ค้าง 4 นาทีเป็นหลักฐาน runtime ที่หนักกว่าทั้งสามข้อรวมกัน**

### 3.5 ① — ทำไม `Main_Dead` ไม่ยอมหายไปเอง

`0x44A540` (ผู้เรียกเดียว `0x44E828` ใน `CMyActor::Update`):

```
0044A543  al = this->vtable[+0x40]()      ; IsDying = HP==0 && timer > 0
0044A54C  74 5a                           ไม่จริง -> ไปปิดหน้าต่าง (0x44A5A8)
0044A54E  f6 46 10 80 / 75 54             บิต 0x80 ของ [this+0x10] กด window ไว้
0044A554  FindWindow(L"Main_Dead") -> เจอแล้ว -> จบ
0044A567  attr = [this+0x348]
0044A56D  movss xmm0,[attr+0x58]
0044A572  cvtsi2sd xmm1,[0x102249C]       ; DURATION_DYING = 20
0044A57A  subsd xmm1,[0xF092D0]           ; double 0.5
0044A585  comisd xmm1,xmm0 / 77 1b        ; ถ้า 19.5 > timer -> ไม่เปิด
0044A5A1  OpenWindow(L"Main_Dead")
0044A5A8  (เส้นไม่ตาย) FindWindow -> vtable[+0x20C] = ปิด
```

⇒ **`Main_Dead` ปิดโดยเงื่อนไข "ไม่ dying แล้ว" เท่านั้น** (HP > 0 หรือ timer <= 0) ตรงกับที่ผู้เทสพิสูจน์ในเกม · และเพราะฟังก์ชันนี้รันทุกเฟรม การกดปุ่มปิดเองจึงถูกกลบทันที

---

## 4. ผลลัพธ์เชิงลบ (แต่ละข้อคือของที่ตรวจแล้วไม่เจอ)

1. **ไม่มีสตริง `L"Rescue"` เดี่ยวในอิมเมจ** — `0xF0D542` เป็นหางของ `L"Main_Panel_Rescue"` และมี dword-ref **0 ที่**
2. **`Main_Dead` มีคอนโทรลเดียวคือ `BUTTON_DIE`** — ยืนยันสองทาง: XML layout และ `0x5183D0` ที่ผูกลูกตัวเดียว
3. **ไม่มี handler ใดใน `Main_Dead` ที่ส่ง `PartyCmdVital`** — ทางเดียวที่ออกสายจากหน้าต่างนี้คือ `ActionVital` `0xEA7C`
4. **ไม่มีเฟรมขาเข้าที่บอกว่า "แกตายแล้ว"** — ยืนยัน HP-DEATH-001 §6 ข้อ 1 อีกครั้ง: `Common_Death` มาจาก predicate ล้วน ๆ ไม่ใช่จาก opcode
5. **ฝั่งเรา (server) ยังไม่มีอะไรเลยในสายนี้** — grep `current/` + `src/`: `PartyCmdVital` = 0 ครั้ง, `0x2466` = 0, `0xEA7C`/`0xEA80` = 0, คำว่า `rescue` = 0
6. **`Main_Revive_Notify` / `Main_Revive_Action`** มีไฟล์ `.model` อยู่จริงแต่ **ชื่อทั้งสองไม่ปรากฏเป็น literal ในอิมเมจ** ⇒ ถูกโหลดผ่านระบบ data-driven ไม่ใช่ hardcode

---

## 5. ตัวเลข (นับด้วยเครื่อง ไม่ได้นับด้วยตา)

```json RESCUE_DEATH_ESCALATION_COUNTS
{
  "binary_sha256": "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623",
  "standalone_Rescue_wide_strings": 0,
  "Main_Panel_Rescue_xrefs": 4,
  "Main_Dead_controls_in_layout": 1,
  "Main_Dead_bound_children_in_code": 1,
  "Common_Death_open_sites": 1,
  "Common_Death_gate_conditions": 2,
  "duration_dying_readers": 1,
  "duration_dying_value": 20,
  "per_frame_readers_of_attr_0x58": 3,
  "per_frame_writers_of_attr_0x58": 0,
  "candidate_stores_to_reg_plus_0x58_in_text": 394,
  "candidate_stores_with_basicattr_signature": 6,
  "partycmdvital_id": 9318,
  "partycmdvital_sizeof": 32,
  "partycmdvital_wire_fields": 2,
  "partycmdvital_client_verbs_observed": 2,
  "server_partycmdvital_encoders": 0,
  "server_action_0xEA7C_handlers": 0,
  "server_action_0xEA80_handlers": 0,
  "server_rescue_references": 0
}
```

*(`partycmdvital_id` 9318 = `0x2466`)*

---

## 6. Nonclaims — สิ่งที่ยัง**ไม่ได้**พิสูจน์

1. **ไม่อ้างอะไรเกี่ยวกับ ORIGINAL server** — ปิดไปแล้ว ไม่เคย publish ไม่มี capture ของการตายหรือการ rescue และไม่มีวันมี
2. **ไม่ได้อ่านข้อความ tooltip จริง** — `TipID="438"` / `TextID="1648"` / `TextID="1525"` อยู่ใน `Data/B_TEXTDATA_TH.pc_` ซึ่งเป็น container `$pcz` (บีบอัด/เข้ารหัส) · **ไม่ได้ถอดในรอบนี้** ⇒ ประโยคที่ว่า "คำว่า `Rescue` มาจาก TipID 438" เป็น **② อนุมานจากโครงสร้าง** ไม่ใช่ ① (ที่เป็น ① คือ: `BUTTON_DIE` และหน้าต่างมี `TipID="438"` และคำนั้นไม่ได้อยู่ในไบนารี)
3. **ไม่ได้พิสูจน์ว่ากด `BUTTON_DIE` แล้วเฟรม `0xEA7C` ออกจริง** — static บอกได้แค่ว่าเส้นทางมีอยู่และ gate คืออะไร · gate A (`[handler+0x10]`) กับ gate B (`0x4011A0`) ประเมินจาก static ไม่ได้
4. **ไม่ได้ถอด opcode `0x25/0x26/0x27/0x49` ว่ามาจากไหน** — ค้นแล้วไม่มีที่ไหนเขียน `[obj+0x10] = imm` ตรง ๆ (ทั้ง `C7 4x 10 imm32` และ `C6 4x 10 imm8` = 0 hit ทั่ว `.text`) ⇒ opcode ถูกส่งผ่านพารามิเตอร์ของ ctor · **ยังไม่รู้ว่า `PartyCmdVital` command ตัวไหน map เป็น opcode ตัวไหน**
5. **ไม่ได้ตั้งชื่อคลาสของ manager `0x62C840`** (vtable slot `0xF348B8`) — สำมะโน xref บานเกินงบรอบนี้
6. **ไม่อ้างว่า `PartyCmdVital` เกี่ยวกับ rescue เท่านั้น** — ชื่อบอกว่าเป็นคำสั่งของระบบปาร์ตี้ · สาขา rescue เป็นแค่ 2 จาก opcode ที่ `0x62C840` รู้จัก
7. **negative ของ "ไม่มีใครลด `+0x58`" เป็น ② ไม่ใช่ ①** — ดู §3.4 กล่องแดง · ทำเป็น ① ได้ถ้าเดินสำมะโนผู้เขียนครบ 394 จุด
8. **ไม่มี runtime pass ในรอบนี้เลย** — `Common_Death` ยังไม่เคยถูกโปรเจกต์นี้เห็นแม้แต่ครั้งเดียว
9. **ไม่ได้แตะ** `docs/FUNCTIONAL_COVERAGE.json`, ledger, scenario, `src/`, `tools/`, `tests/`, `pf_bridge/*`, `current/pf_login_game_server_v141.py` · **ไม่มี git command ที่เปลี่ยนสถานะ** (ใช้แค่ `git check-ignore -v`, `git log -1`, `git status --porcelain` ซึ่งอ่านอย่างเดียว)

---

## 7. การทดลองถัดไปที่ถูกที่สุด (เสนอ ไม่ได้ทำ)

**GT-A — ปิดวง "ตาย → คืนชีพ" ด้วยเฟรมเดียวที่ต่อท้ายของเดิม (ราคาถูกที่สุด, คุ้มที่สุด)**
ต่อ step ที่ 4 เข้ากับโปรไฟล์ `dying_hold` ที่มีอยู่แล้ว ชื่อ `TIMER_ELAPSED`:

| ฟิลด์ | ค่า |
| --- | --- |
| carrier | `UpdateAttrVital` (`0x309A`) ตัวเดิม — ไม่ต้องเปลี่ยน transport |
| `BasicAttr` change mask | **`0x0004` \| `0x0080`** (ส่งทั้งสองบิต ห้ามละบิต `0x0080` — §3.3) |
| `+0x44` current HP | `0` |
| `+0x58` death timer | **`0.0f`** (ค่าลบก็ได้ · **ห้าม NaN**) |

สิ่งที่ต้องดู เรียงตามลำดับ: (1) `Main_Dead` **หายไป** (เพราะ `vt+0x40` กลายเป็นเท็จ) · (2) `Common_Death` **ปรากฏ** พร้อมปุ่ม `BUTTON_RELIVE` / `BUTTON_SPAWN` / `BUTTON_RELIVE_TEXT` · (3) กด `BUTTON_SPAWN` แล้วดูว่า `ReliveVital` (`0x1AD4`, `+0x14 = 0`) ออกสายไหม
**เฟรมเดียวนี้ปิดหนี้ที่ค้างมาสามรอบ** และเป็นครั้งแรกที่โปรเจกต์นี้จะได้เห็น `Common_Death`
คาดการณ์ non-event ที่ต้องบอกผู้เทสล่วงหน้า: **ไม่มีท่าตาย ไม่มี `L"TargetIsDead"`** เพราะ transport นี้ไม่ถึง `0x4437C0` (E1 ของ HP-DEATH-ERRATA-001)

**GT-B — ตัวแยกของ lead `Rescue` (ราคาถูกมาก แถมไปกับ GT-A ได้)**
ระหว่างที่ `Main_Dead` เปิดอยู่ (ก่อนยิงเฟรม `TIMER_ELAPSED`) ให้ **กด `BUTTON_DIE` หนึ่งครั้ง** แล้วดู 2 อย่าง:
* ถ้ามี `ActionVital` วิ่งบนสายพร้อม `[+0x30] = 0xEA7C` ⇒ **gate A/B/C ผ่านหมด** ปุ่มทำงานปกติ และ "จอนิ่ง" คือปิด-เปิดใหม่ตามที่ §2.5 อธิบาย ⇒ ปิด lead นี้ได้เลย
* ถ้าไม่มีอะไรบนสาย ⇒ ติดที่ gate A หรือ B และเรารู้แล้วว่าจะไปดูที่ไหนต่อ (`[handler+0x10]` vs `[0x1081A90]`)
ค่าใช้จ่าย: **คลิกเดียว ไม่ต้องแก้โค้ดฝั่งเรา ไม่ต้องเพิ่ม scenario**

**GT-C — ถอด `$pcz` (ทำ offline ได้ ไม่ต้องเปิดเกม, ทำทีหลังได้)**
เขียนตัวถอด `Data/B_TEXTDATA_TH.pc_` แล้วอ่าน `TipID 438`, `TextID 1648`, `TextID 1525` · จะได้ **ตารางข้อความไทยทั้งเกม** ซึ่งใช้ได้อีกหลายเลน ไม่ใช่แค่เลนนี้ · แต่ **ไม่ควรบล็อก GT-A** เพราะไม่จำเป็นต่อการปิดวงตาย

**สิ่งที่ยังไม่ควรทำตอนนี้:** อย่าเพิ่งเขียน encoder ของ `PartyCmdVital` — เรายังไม่รู้ว่า command byte ตัวไหน map เป็น opcode ตัวไหน (nonclaim ข้อ 4) การเดาแล้วเขียนจะได้ระบบที่ทดสอบไม่ได้

---

## 8. วิธีทำซ้ำ

ไม่มีเครื่องมือใหม่ถูกเพิ่มในรอบนี้ (report-only) · ทุกตัวเลขข้างบนได้จาก `pefile` + `capstone` บนอิมเมจ read-only และจากไฟล์ XML ใน `GameClient/Data/GUI/Model/`

span ที่ตรึงไว้ให้ตรวจซ้ำได้ทันทีด้วย hex compare:

| ที่อยู่ | ไบต์ | คืออะไร |
| --- | --- | --- |
| `0x44E58D` | `8b068b503c8bceffd284c00f8486000000` | `CMyActor::Update` เรียก `vt+0x3C` แล้วกระโดดข้ามถ้าเท็จ |
| `0x44E5BD` | `6860d8f000b908070901e844216500` | เปิด `L"Common_Death"` |
| `0x454A7A` | `0f57c00f2f4058722e` | `xorps ; comiss 0.0,[attr+0x58] ; jb` |
| `0x454AA5` | `33d2395044` | `cmp [attr+0x44], 0` |
| `0x464B02` | `897e44897e48897e4c897e50f30f114658` | ctor ตั้ง HP/MP = 0 และ timer = 0.0 |
| `0x464AC6` | `b9ffff000066894e70` | ctor ตั้ง change mask = `0xFFFF` |
| `0x4658E8` | `f60380740f6a048d4658506a2a8bcf` | สายอ่าน: gate บิต `0x80` → f32 `+0x58` |
| `0x4656A3` | `84c07806d94658d95f58` | `Merge`: คัดลอก `+0x58` ต่อเมื่อบิต `0x80` **ไม่** ติด |
| `0x5F2504` | `8b0b8b018b502457ffd2` | `incoming->vt[+0x24](existing)` |
| `0x5183D2` | `68ccf5f100` | `Main_Dead` ผูก `L"BUTTON_DIE"` |
| `0x518450` | `568bf1837e1000745ae8428deeff85c07444` | gate A + gate B ของปุ่ม |
| `0x518493` | `c740307cea0000e8018deeff8bc8` | `[vital+0x30] = 0xEA7C` แล้วส่ง |
| `0x62E274` | `c7006c6df80088480489480889480c884810884811c7007c49f300` | ctor ของ `PartyCmdVital` (vtable `0xF3497C`) |
| `0x74E321` | `8d4614506a088bcfe8d2c214006a0883c618566a32` | wire ของ `PartyCmdVital`: `u8@+0x14` tag `0x08`, `qword@+0x18` tag `0x32` |
| `0x62CB2A` | `c640140c8b4e20894818` | คำสั่ง `0x0C` |
| `0x62CBA4` | `c640140d8b4e20894818` | คำสั่ง `0x0D` |
| `0x44D809` | `6a006880ea00008bcee849faffff` | ESC บน rescue panel → action `0xEA80` |

ไฟล์ layout (อ่านตรง ๆ ไม่ต้องถอด):
`GameClient/Data/GUI/Model/Main_Dead.model` · `Main_Panel_Rescue.model` · `Common_Death.model` · `Main_Revive_Notify.model` · `Main_Revive_Action.model`
