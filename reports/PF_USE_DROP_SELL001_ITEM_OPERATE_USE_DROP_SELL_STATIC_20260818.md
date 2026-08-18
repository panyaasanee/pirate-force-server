# PF_USE_DROP_SELL001 — use / drop / sell: op3 คือ single-target ที่มี modal confirm, op6 อีก 3 site ไม่มี vendor context เลย, และ **use กับ sell ไม่ได้วิ่งบน ItemOperate** (static disasm + server cross-check)

2026-08-18 · ลูกมือ chief · report-only additive · milestone `inventory/use_drop_sell` (`not_started`, coverage note = **"Tracked as separate later milestones."**) · binary `GameClient/GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` (14,759,424 B) · capstone 5.0.7 (CS_MODE_32, ImageBase 0x400000, PE section table parsed เอง) · reproduce: `py -3 tools/pf_use_drop_sell_static.py` (88 guards, exit 0)

เป้า: characterize byte-exact ว่า client ผลิต **use / drop / sell** อย่างไร แล้ว cross-check ช่องว่างฝั่ง server — โดย **ไม่แตะ v141 (immutable), ไม่แตะ canonical DB, ไม่เปิด GameClient, ไม่มี network I/O** และเคารพวินัย bounded-claim ของ SPLIT-OPERATE-002 (ห้าม claim ว่า op ใด ≡ verb ใดถ้าไม่มีหลักฐาน positive)

> **ผลสรุปล่วงหน้า:**
> - **use ไม่ได้วิ่งบน ItemOperate — พิสูจน์เชิงบวก.** `UseItemVital` @`0xF30950` เป็น **request class ของตัวเอง** (registration เดียว `0xBEE600`, id-slot `0x1082030` เขียนจุดเดียว/อ่านจุดเดียวโดย get-id `0x5BEA50`, vtable `0xF2D0B0` รูป cohort เดียวกับ `ItemOperateVitalReq`) และ serializer `0x6C0180` ปล่อย **field เดียว: qword tag 0x32 @+0x18** — ไม่มี operation byte ไม่มี value32 = `use(item_identity)` ล้วน ๆ
> - **sell ก็ไม่ได้วิ่งบน ItemOperate — พิสูจน์เชิงบวก.** การขายมีระบบของตัวเองครบ: `StallModule_Client` / `StallStartVital` / `StallOpenVital` / **`StallOperateVital`** (แผงขายผู้เล่น), ตระกูล `GSCN_BlackMarketPutOnSale` / `OffSale` / `Buy` / `Search*`, `UpdateConditionalStoreItemVital` (+ `StoreEventHandler`), และตระกูล `ItemMall*`. serializer ของ `StallOperateVital` (`0x76A630`) เป็น **priced wire** (u8 tag 0x08 @+0x14 + qword tag 0x32 @+0x18 + string @+0x24 + **u32 tag 0x14 @+0x20 = ราคา**) — คนละรูปกับ 3-field wire ของ ItemOperate
> - **ไม่มี vendor/price/counterparty context ที่ op6 site ใดเลย.** ทั้ง 5 ฟังก์ชันที่ผลิต ItemOperate (A `0x57CF50`, B `0x582730`, C `0x5A2A70`, D `0x5B9F70`, op3-callback `0x5B9CE0`) **ไม่อ้างสตริงใดที่มีคำว่า stall/market/store/sell/buy/shop/vendor/money/price เลยสักตัว** → **sell-N ไม่ได้อยู่ในตระกูล op6** (ตัดตัวเลือกที่ 002 เปิดค้างไว้ออกได้หนึ่งข้อ)
> - **op3 = single-target identity-only ที่อยู่หลัง modal confirm.** caller เดียว `0x5B9D0C` อยู่ในฟังก์ชันขนาด 0x3E ไบต์ `[0x5B9CE0,0x5B9D1E)` ซึ่ง **ไม่เคยถูก e8-call เลย** — reference เดียวทั้งอิมเมจคือ `push 0x5B9CE0` @`0x5BA16C` คือถูก **ลงทะเบียนเป็น callback ของ dialog** (`0x405D40` เก็บลง `dialog+0x12CC`). callback ยิง op3 เฉพาะเมื่อ `[arg1+0x94] == 1` โดยอ่าน identity จาก global qword `0x1080F40/0x1080F44` แล้วเคลียร์ทิ้งทันที. ตัว latch อยู่ใน body ของ **verb `eax==2` ของพาเนล `0x5B9F70`** ซึ่งเปิด message box template `0x69` ก่อน → **op3 = destructive-shaped: ไม่มีจำนวน ไม่มีปลายทาง ไม่มีคู่สัญญา + ต้องกดยืนยัน**
> - **op6 อีก 3 site แยกกันชัดเจน:** site **A** `0x57D1F4` (fn `0x57CF50`) เป็น **verb 0x16 ตัวที่สาม** ที่ 003 มองไม่เห็นเพราะเขียนเป็น `cmp dword [esi+0x94], 0x16` (`83 BE 94 00 00 00 16`) ไม่ใช่ `83 F8 16` — body ถือ **item handle สองตัว** และตาม op6 ด้วย **op5 (equip) สองครั้ง** → quantity-parameterised equip/swap · site **B** `0x58294D` (fn `0x582730`) **ไม่ได้ gate ด้วย verb เลย** แต่ gate ด้วย context field `[ctx+8]` (`cmp ecx,1` vs `cmp ecx,2`, op6 = โหมด 2) และแขนโหมด-1 เป็นทาง **GetAsyncKeyState SHIFT/CTRL** · site **D** `0x5BA208` = แขน verb 0x16 ของพาเนล `0x5B9F70` (ตรงกับ 003)
> - **ช่องว่างฝั่ง server:** v141 ประกาศ `USE_ITEM_VITAL = 0x1F4F` และใส่ใน `NAMES` แต่ **ไม่มี dispatch branch** (ปรากฏ 3 ครั้ง = const + NAMES + self-test) · ItemOperate รับเฉพาะ operation 4/5 **ไม่มี 3 และไม่มี 6** · **ไม่มี id ของ stall/black-market เลย** · เส้นทางร้าน NPC ที่ implement แล้วคือ `TradeCmdVital 0x23B5` และรับ **คำสั่งเดียว = cart-add (buy) = 6** ไม่มีสาขา sell · foundation `runtime.py` ปิดตายทุก operation ที่ไม่ใช่ 4
> - **แก้ป้ายกำกับ (incidental, evidenced):** `mov dword [esp+0x180], 0x12` @`0x5A34D7` ที่ 001/002 เรียกว่า "numeric-input dialog resource 0x12" จริง ๆ คือ **MSVC EH trylevel store** ไม่ใช่ dialog id (สล็อตเดียวกันรับ `0xFFFFFFFF` @`0x5A3502` และ `0x0A` @`0x5A335A`/`0x5A30C0`) — **โครงสร้างที่ 001–003 พิสูจน์ไม่กระทบ** และ **R2 ของ 003 (static caption route ปิด) แข็งขึ้น** เพราะไม่มี dialog id ให้ไปหา caption ตั้งแต่ต้น
>
> **เกรด: A** สำหรับ enumeration/identity/serializer/ callsite-context/ server-gap (byte-exact, reproduced ด้วย verifier 88 guards + pytest 16 เคส) · **ไม่ claim:** op3 ≡ "drop"/"discard"/"destroy" และ op6 verb ใด ≡ "split"/"drop-N" (ดู §6) · net: `inventory/use_drop_sell` **`not_started` → `in_progress`** (ไม่ flip runtime_pass)

---

## 1. op3 — caller เดียว, ฟังก์ชันเดียว, และมันคือ callback ของ dialog

### 1.1 arg contract (byte-exact)

```
0x0059f780: 6a00 / 68 0ca9f000 / b9 18060301 / e8 ...   ; alloc ItemOperateVitalReq
0x0059f795: 8b4c2404      mov ecx,[esp+4]      ; arg1 = identity low
0x0059f799: 8b542408      mov edx,[esp+8]      ; arg2 = identity high
0x0059f79e: c6401403      mov byte [eax+0x14], 3   ; *** operation = 3 ***
0x0059f7a2: 894820        mov [eax+0x20], ecx      ; qword low  (tag 0x32)
0x0059f7a5: 895024        mov [eax+0x24], edx      ; qword high
0x0059f7b4: c20800        ret 8                    ; stdcall, สองอาร์กิวเมนต์เท่านั้น
```
`value32 (+0x18, tag 0x14)` **ไม่ถูกเขียนเลยทั้งฟังก์ชัน** (guard สแกน `mov dword [eax+0x18], *` = 0 hit) → op3 = `op3(identity_low, identity_high)` เทียบกับ op4 `ret 0x18` และ op6 `ret 0xC` · span `[0x59F780,0x59F7B7)` sha `0601F7B4…260767`

### 1.2 ฟังก์ชันของ caller `0x5B9D0C` = `[0x5B9CE0, 0x5B9D1E)` — 0x3E ไบต์ ล้อมด้วย int3

```
0x005b9ce0: 8b442404              mov eax,[esp+4]
0x005b9ce4: 83b89400000001        cmp dword [eax+0x94], 1     ; *** ผลจาก dialog ต้อง == 1 ***
0x005b9ceb: 7524                  jne 0x5b9d11
0x005b9ced: a1 400f0801           mov eax,[0x1080f40]         ; identity low  (global latch)
0x005b9cf2: 8b0d 440f0801         mov ecx,[0x1080f44]         ; identity high
0x005b9cfa: 0bd1 / 7413           or edx,ecx ; je  0x5b9d11   ; ต้องไม่เป็นศูนย์ทั้งคู่
0x005b9cfe: 51 / 50               push high ; push low
0x005b9d0c: e8 6f5afeff           call 0x59f780               ; *** op3(identity) ***
0x005b9d13: a3 400f0801           mov [0x1080f40], 0
0x005b9d18: a3 440f0801           mov [0x1080f44], 0          ; เคลียร์ latch เสมอ
0x005b9d1d: c3                    ret
```
span `[0x5B9CE0,0x5B9D1E)` sha `CF572F96…39E2F7`

**หลักฐานว่าเป็น callback ไม่ใช่ฟังก์ชันธรรมดา:**
- e8-scan ทั่ว `.text` → **0 caller**
- dword reference ทั้งอิมเมจของค่า `0x005B9CE0` → **จุดเดียว** `0x5BA16D` (คือ operand ของ `push 0x5B9CE0` @`0x5BA16C`)
- ตัวลงทะเบียน `0x405D40` เก็บ arg1 ลง `[dialog+0x12CC]` (`0x405D79: mov [esi+0x12cc], eax`)

### 1.3 ต้นทาง latch = verb `eax==2` ของพาเนล `0x5B9F70`

verb ถูกโหลดจาก `[record+0x94]` (`0x5B9FE0: 8b8094000000`) แล้วเทียบเป็นบันได `cmp eax,1` @`0x5B9FE6` · `cmp eax,2` @`0x5BA03C` · `cmp eax,0x16` @`0x5BA183`

```
0x005ba0f9: 8b4128 / 8b492c       mov eax,[ecx+0x28] ; mov ecx,[ecx+0x2c]   ; identity ของ slot ที่เลือก
0x005ba105: 890d 440f0801         mov [0x1080f44], ecx      ; *** latch high ***
0x005ba115: a3 400f0801           mov [0x1080f40], eax      ; *** latch low  ***
0x005ba11a: e8 610fffff           call 0x5ab080             ; ประกอบข้อความ
0x005ba13b: 6a69                  push 0x69                 ; *** message-box template id 0x69 ***
0x005ba13d: e8 ae14ffff           call 0x5ab5f0             ; เปิดกล่องข้อความ (คืน dialog object)
0x005ba16c: 68 e09c5b00           push 0x5b9ce0             ; *** callback = op3 launcher ***
0x005ba179: e8 c2bbe4ff           call 0x405d40             ; register -> dialog+0x12CC
```
span `[0x5BA0F1,0x5BA17E)` sha `816FF7AE…4F3F80` · span `[0x5BA03C,0x5BA08B)` sha `C6D331C0…6ECBA6`

global latch `0x1080F40`/`0x1080F44` มี **4 reference พอดีต่อครึ่ง**: init-clear ที่ panel เปิด (`0x5B9DA1`/`0x5B9DAB`), latch ตรงนี้ (`0x5BA116`/`0x5BA107`), อ่านใน callback (`0x5B9CEE`/`0x5B9CF4`), เคลียร์ใน callback (`0x5B9D14`/`0x5B9D19`) → **latch มีอายุแค่ช่วง dialog เดียว** ไม่ใช่ selection ถาวร

**สรุปรูปของ op3 (โครงสร้าง, ไม่ใช่ป้ายชื่อ):** single-target · identity-only · ไม่มีจำนวน · ไม่มี destination slot · ไม่มี counterparty handle · **ต้องผ่าน modal confirm** · latch ถูกล้างทิ้งไม่ว่าจะกดยืนยันหรือไม่

---

## 2. op6 อีกสามจุด — โครงสร้างต่างกันจริง

| site | call VA | ฟังก์ชัน (SEH prologue) | ตัว gate | รูปของ body |
|---|---|---|---|---|
| **A** | `0x57D1F4` | `[0x57CF50, 0x57D2BC)` | `cmp dword [esi+0x94], 0x16` @`0x57D0C0` (`83 BE 94 00 00 00 16`) | **สอง item handle** (`[edi+0x94]` เก็บลง `[esp+0x14]`, `[esi+0x94]` → op6 arg3) แล้วตามด้วย **op5 (equip) สองครั้ง** `0x57D220`, `0x57D277` |
| **B** | `0x58294D` | `[0x582730, 0x58298F)` | **ไม่ใช่ verb** — `mov ecx,[ecx+8]` @`0x58284B` แล้ว `cmp ecx,1` @`0x58284E` / `cmp ecx,2` @`0x58292D`; op6 = แขนโหมด **2** | แขนโหมด-1 เรียก `0x448EC0(0x10)` = VK_SHIFT และ `0x448EC0(0x11)` = VK_CONTROL (`0x448EC0` = `GetAsyncKeyState(vk) & 0x8000`, thunk `0xC3B990`) |
| **C** | `0x5A3532` | dispatcher `[0x5A2A70, 0x5A40B0)` | `cmp eax,0x16` @`0x5A349B` | 002/003 pin ไว้แล้ว (มี op4 = MOVE verb 2 อยู่ในฟังก์ชันเดียวกัน) |
| **D** | `0x5BA208` | `[0x5B9F70, 0x5BABF7)` | `cmp eax,0x16` @`0x5BA183` | 003 pin ไว้แล้ว — และเป็นฟังก์ชันเดียวกับที่ verb 2 ยิง **op3** (§1.3) |

**ข้อกลั่นของ 003:** 003 บอกว่า "2 ใน 4 op6 site gate ด้วย `cmp eax,0x16` (`83 F8 16`)" — ถูกต้องตามที่เขียน. รอบนี้พบว่า **site A ก็เป็น verb 0x16 เช่นกัน** แต่เขียนด้วย memory operand จึงหลุด byte-scan ของ 003 → **verb 0x16 กว้างกว่าที่คิด (3 ใน 4 site)** ส่วน **site B ไม่ใช่ verb-driven เลย** เป็น context-mode

`0x5A349B` และ `0x5BA183` ยังอยู่ครบใน `83 F8 16` scan (regression ผ่าน) และ **ไม่มี `83 F8 16` อยู่ใน `[0x582730,0x58298F)`** เลย (ยืนยันว่า B ไม่ใช่ verb gate)

span pin: A body `[0x57D0C0,0x57D1F9)` sha `29632E47…AB3BE5` · B mode gate `[0x582844,0x582952)` sha `762A003F…27B71F` · prologue A/B/D pin ครบใน verifier

---

## 3. ไม่มี shop / vendor / price context ที่ ItemOperate เลย (negative, มีหลักฐาน)

สแกน immediate ทุกตัวใน body ของทั้ง 5 ฟังก์ชันที่ผลิต ItemOperate แล้ว resolve เป็น ASCII string:

| ฟังก์ชัน | สตริงที่อ้างถึง | ตรงกับ `stall\|market\|store\|sell\|buy\|shop\|vendor\|auction\|money\|price` |
|---|---|---|
| A `0x57CF50` | (ไม่มี) | **0** |
| B `0x582730` | (ไม่มี) | **0** |
| C `0x5A2A70` | `EquipmentModule`, `TradeModule_Client`, `StorageModule_Client`, `CGCGuildModule`, `PopItem`, `ItemMallModule_Client`, `GetBack` | **0** |
| D `0x5B9F70` | `EquipmentModule`, `TradeModule_Client`, `StorageModule_Client`, `CGCGuildModule`, `PopItem` | **0** |
| op3-callback `0x5B9CE0` | (ไม่มี) | **0** |

(`TradeModule_Client` = player-to-player trade ที่ verb 7/8 ไม่ใช่ร้านค้า) และ **ไม่มี callsite ใดของ ItemOperate อยู่ในย่านโค้ด `0x6C0000..0x790000`** ซึ่งเป็นที่อยู่ของ serializer ตระกูล Stall/BlackMarket → sell wire อยู่คนละเขต

→ **บทสรุปเชิงลบที่มีค่า: "op6 site ใดสักตัว = sell-N" ตกไป** — ตัวเลือกที่ 002 เปิดไว้ (split / drop-N / **sell-N**) เหลือ split / drop-N / give-N เท่านั้น

---

## 4. use กับ sell วิ่งบน transport อื่น — หลักฐานเชิงบวก

### 4.1 `UseItemVital` — คลาสของตัวเอง, wire ฟิลด์เดียว

```
0x00bee600: 68 5009f300      push 0xf30950            ; "UseItemVital"
0x00bee605: e8 76dacaff      call 0x89c080            ; once-init singleton registry
0x00bee60a: 8bc8             mov ecx, eax
0x00bee60c: e8 efd6caff      call 0x89bd00            ; id-assign(name) -> ax
0x00bee611: 66a3 30200801    mov word [0x1082030], ax ; *** id-slot ***
0x00bee617: c3               ret
```
- id-slot `0x1082030`: เขียนจุดเดียว (`0xBEE611`) อ่านจุดเดียว (get-id `0x5BEA50: 66 a1 30 20 08 01 / c3`) — **กำแพง runtime-assigned เดียวกับ ECHO/TELEPORT/ItemOperate cohort**
- vtable `0xF2D0B0` (9 slot, รูปเดียวกับ `ItemOperateVitalReq` `0xF30374`): `+0x08 = 0x401B20` (shared framework const), `+0x10 = 0x5BEA50` get-id, **`+0x18 = 0x6C0180` serializer**, `+0x1C = 0x710440`
- object ขนาด `0x20` สร้างผ่าน generic class factory (`mov dword [eax], 0xF2D0B0` @`0x5BFEAB` และ `0x5EE649`, `push 0x20` @`0x5EE626`) — **ไม่มีการสร้างจากในฟังก์ชัน ItemOperate producer ทั้ง 5 ตัวเลย**

serializer `0x6C0180` (byte-exact, ทั้งฟังก์ชันมีแค่นี้):
```
0x006c0180: 83c118           add ecx, 0x18            ; ptr = obj+0x18
0x006c0183: 807c240800       cmp byte [esp+8], 0      ; direction
0x006c0188: 6a08             push 8                   ; width 8
0x006c018a: 51               push ecx
0x006c018f: 6a32             push 0x32                ; *** tag 0x32 = qword ***
0x006c0193: e8 ... 0x89a600  (out)   /  0x006c019b: e8 ... 0x89a640  (in)
0x006c0198: c20800           ret 8
```
**ไม่มี tag 0x0B (operation) และไม่มี tag 0x14 (value32) ที่ไหนเลยในช่วง `[0x6C0180,0x6C01A3)`** → wire ของ use = **9 ไบต์: `32` + `<Q identity>`** เทียบกับ ItemOperate ที่เป็น 16 ไบต์สามฟิลด์

span: registration `[0xBEE600,0xBEE618)` sha `29646D0D…93FCFB` · vtable `[0xF2D0B0,0xF2D0D4)` sha `95C403FD…FA0C9E` · serializer `[0x6C0180,0x6C01A3)` sha `C0910C6E…943BCE`

### 4.2 ระบบขายเป็นของตัวเองทั้งชุด

registration table ของ client มี **521 คลาส** ในนั้นมี (ทุกตัว verify ว่า `push <name>` → `call 0x89C080` ที่ VA ที่ระบุ):

| คลาส | name VA | registration | บทบาท |
|---|---|---|---|
| `StallModule_Client` | `0xF4A404` | `0xC0E3D5` | โมดูลแผงขายผู้เล่น |
| `StallStartVital` | `0xF4A4C8` | `0xC0E5B5` | เริ่มเปิดแผง |
| `StallOpenVital` | `0xF4A4D8` | `0xC0E5D5` | เปิด/เข้าแผง |
| **`StallOperateVital`** | `0xF4A4E8` | `0xC0E5F5` | **ดำเนินการกับของในแผง (มีราคา)** |
| `GSCN_BlackMarketPutOnSale` | `0xF3E89C` | `0xC00765` | ลงขายในตลาด |
| `GSCN_BlackMarketOffSale` | `0xF3E8B8` | `0xC00785` | ถอนขาย |
| `GSCN_BlackMarketBuy` | `0xF3E8D0` | `0xC007A5` | ซื้อจากตลาด |
| `UpdateConditionalStoreItemVital` | `0xF0B328` | `0xBF8895` | ร้าน NPC |
| `PickupTerrainThing` | `0xF3093C` | `0xBEE5E5` | เก็บของจากพื้น |

`StallOperateVital` vtable `0xF4A418` (+0x08 = `0x401B20`, +0x18 = serializer `0x76A630`), serializer:
```
0x0076a63f: lea eax,[esi+0x14]  push 8    ; u8   tag 0x08 @+0x14   (operation ของแผง)
0x0076a652: lea ecx,[esi+0x18]  push 0x32 ; qword tag 0x32 @+0x18  (item identity)
0x0076a65f: lea edx,[esi+0x24]  call 0x89a810 ; string @+0x24
0x0076a66c: lea eax,[esi+0x20]  push 0x14 ; u32  tag 0x14 @+0x20   (*** ราคา ***)
0x0076a68b: push 0xb                      ; u8   tag 0x0B presence flag -> sub-record
```
span `[0x76A630,0x76A738)` sha `3D1138E7…DBD501`

→ การขาย **มี operation byte ของตัวเอง + ราคา + string** บน wire คนละเส้น ไม่มีทางที่ ItemOperate (3 ฟิลด์, ไม่มีช่องราคา) จะรับหน้าที่นี้ได้

---

## 5. ช่องว่างฝั่ง server (read-only cross-check)

`current/pf_login_game_server_v141.py` (immutable) + `src/pirateforce_foundation/runtime.py`:

| หัวข้อ | สถานะ | หลักฐาน |
|---|---|---|
| **USE** | ประกาศแล้ว **แต่ไม่มี handler** | `USE_ITEM_VITAL = 0x1F4F` + `NAMES[USE_ITEM_VITAL] = "UseItemVital"` + self-test — รวม **3 occurrence**, ไม่มี `nested_id == USE_ITEM_VITAL` ที่ไหน |
| **id ตรงกับ client** | ตรง | ฟังก์ชันแฮชของ server เอง `sum((i+1)*ord(c)) & 0xFFFF` ให้ `UseItemVital → 0x1F4F` และ `ItemOperateVitalReq → 0x4BED` (คำนวณซ้ำเองใน verifier/test) |
| **ItemOperate op3** | **ไม่มี handler** | ไม่มี `operation==3` ทั้งไฟล์ |
| **ItemOperate op6** | **ไม่มี handler** | ไม่มี `operation==6` ทั้งไฟล์ |
| ItemOperate op4/op5 | มี | `make_item_operate_move_delta_success` + `V123_EQUIP_FROM_BAG_OPERATION = 5` |
| **SELL / stall / black market** | **ไม่มีเลย** | ไม่มีสตริง `StallOperateVital` / `BlackMarket` / `STALL_`; ไม่มี `def` ตัวใดใน 154 ตัวที่ชื่อมี sell/stall/market/vendor |
| ร้าน NPC (ฝั่ง **ซื้อ**) | มีบางส่วน (คนละ wire) | `TRADE_ZOOM_VITAL = 0x2A7A` / `TRADE_CMD_VITAL = 0x23B5` / `TRADE_ITEM_RESULT_VITAL = 0x557B`; รับ **คำสั่งเดียว** `V118_TRADE_CART_ADD_COMMAND = 6` → `make_trade_item_result_store_buy_cart_ack` — **buy-only ไม่มีสาขา sell** |
| foundation | ปิดตาย | `runtime.py`: `if operation != ITEM_MOVE_CAPTURE_FIELDS[0]` (=4) → `item_move_generalized_wrong_operation_no_reply` (ไม่ตอบ ไม่เขียน) |

→ **use / drop / sell = characterized แล้วฝั่ง client แต่ยัง unimplemented ทั้งหมดฝั่ง server** (ยกเว้น buy-cart ของร้าน NPC ที่เป็นคนละเลน)

---

## 6. แก้ป้ายกำกับ: `0x12` ที่ `0x5A34D7` คือ EH trylevel ไม่ใช่ dialog resource id

`0x5A2A70` มี SEH frame แบบ MSVC: `push -1` (= trylevel เริ่มต้น) · `push 0xB9AFD7` · `push fs:[0]` แล้ว `lea eax,[esp+0x170]; mov fs:[0], eax` → ตรึงตำแหน่งของ EHRec ได้ และ **สล็อต trylevel อยู่เหนือ EHRec 8 ไบต์**

เมื่อไล่ความลึกของ esp ตามเส้นทางจริง สล็อตเดียวกันนั้นรับค่าเหล่านี้:

| VA | ไบต์ | ความลึก esp | ค่า |
|---|---|---|---|
| `0x5A30C0` | `c78424800100000a000000` | −0x180 | `0x0A` |
| `0x5A335A` | `c68424780100000a` | −0x178 | `0x0A` (byte store) |
| `0x5A34D7` | `c784248001000012000000` | −0x180 | **`0x12`** |
| `0x5A3502` | `c7842478010000ffffffff` | −0x178 | `0xFFFFFFFF` |

สล็อตที่รับ `-1` ได้คือ trylevel ไม่ใช่ resource id · พาเนล `0x5B9F70` แสดงรูปเดียวกัน (`lea eax,[esp+0x128]` anchor; `0` @`0x5BA07B`, `2` @`0x5BA1C5`, `0xFFFFFFFF` @`0x5BA211`)

**ผลกระทบ:** ห่วงโซ่โครงสร้างที่ 001–003 พิสูจน์ **ไม่เปลี่ยน** — `cmp eax,0x16` @`0x5A349B` → `call 0x5A1630` @`0x5A34E2` → guard 64-bit `> 0` เข้ม @`0x5A34EF` → `call 0x59F870` @`0x5A3532` ยังยืนครบ (guard ในverifier ยืนยันซ้ำ) เปลี่ยนเฉพาะ **ป้ายของค่า `0x12`** เท่านั้น. และ **R2 ของ 003 แข็งขึ้น**: เดิมบอกว่า "map dialog id 0x12 → caption ทำไม่ได้เพราะ asset packed" ตอนนี้เพิ่มว่า **ไม่มี dialog id ให้ map ตั้งแต่แรก** — เลนนี้ปิดสองชั้น ไม่ต้องกลับไปไล่อีก

> ระวังต่อไป: `mov dword [esp+X], <imm>` ในฟังก์ชันที่มี SEH prologue ควรถูกตรวจกับตำแหน่ง EHRec ก่อนตีความเป็นข้อมูลของโดเมน

---

## 7. เกรด & สถานะ matrix

**A (byte-exact static, reproduced):**
- op3 arg contract (identity-only, `ret 8`, ไม่แตะ value32) + caller เดียว + ฟังก์ชันเป็น dialog callback (0 e8-caller, dword ref เดียว, `dialog+0x12CC`) + result gate `==1` + global latch 4-ref lifecycle
- ต้นทาง latch = verb `eax==2` ของพาเนล `0x5B9F70` + message-box template `0x69` + การลงทะเบียน callback
- op6 site A/B/D context: verb-0x16 ตัวที่สามแบบ memory-operand, สอง handle + op5 สองครั้ง (A) · context-mode gate `[ctx+8]` + SHIFT/CTRL arm (B) · verb-0x16 (D)
- **ไม่มี stall/market/store/sell/buy/shop/vendor/money/price string ในทั้ง 5 ฟังก์ชัน**
- `UseItemVital` identity + vtable cohort + serializer ฟิลด์เดียว (qword tag 0x32) + object 0x20 ไบต์
- ตระกูล Stall/BlackMarket/Store/Pickup เป็นคลาสลงทะเบียนของตัวเอง + `StallOperateVital` priced wire
- server gap: use ไม่ dispatch, op3/op6 ไม่มี handler, ไม่มี stall/market, ร้าน NPC buy-only, foundation fail-closed
- การแก้ป้าย `0x12` = EH trylevel (พร้อม EHRec anchor + ค่า `-1` ในสล็อตเดียวกัน)

**ไม่ claim (bounded):**
1. **op3 ≡ "drop" / "discard" / "destroy" — ไม่ claim.** หลักฐานเป็นเชิงโครงสร้างล้วน (identity-only + modal confirm + ไม่มีคู่สัญญา/ปลายทาง/จำนวน) caption ของ message-box `0x69` อยู่ใน packed text table (003 R2) จึงอ่านไม่ได้แบบ static. op3 ยังเข้ากันได้กับ destroy / discard / unequip-with-confirm / consume-with-confirm
2. **op6 verb ใด ≡ "split" หรือ "drop-N" — ไม่ claim.** รอบนี้ตัดได้แค่ **sell-N** ออกจากตัวเลือก (ไม่มี vendor context) ที่เหลือยังต้อง live capture
3. **"client ไม่มี drop request เลย" — ไม่ claim.** สิ่งที่พิสูจน์คือใน registration table 521 คลาสไม่มีชื่อคลาสที่สะกดว่า drop/discard สำหรับ item ในกระเป๋า (มีแต่ `DropThingModule_Client` / `DropThingBoard` / `DropThingGameObj` ซึ่งเป็นวัตถุที่ตกบนพื้น และ `PickupTerrainThing` ซึ่งเป็นการเก็บ) → ภายในกรอบ ItemOperate เหลือ op3/op6 เป็นตัวเลือกเดียวของ destroy/discard family
4. **`0x5A1630` ทำอะไรกันแน่ — ไม่ re-claim.** รอบนี้ใช้ตามที่ 001–003 pin ไว้ (ทาง quantity ที่คืน record ซึ่งถูก guard `> 0`) ไม่ได้ขยายหรือกลับคำ
5. **ไม่มี runtime claim ใด ๆ** — ไม่เปิด GameClient ไม่ต่อ network ไม่แตะ DB

**สถานะ matrix:** `inventory/use_drop_sell`: `not_started` → **`in_progress`** — evidence_ref = report นี้, test_ref = `tests/test_use_drop_sell_static.py`. **ไม่ flip runtime_pass** (ไม่มี server handler และไม่มี runtime capture) · ledger คง **25** (characterization ของ client binary ไม่ใช่ server hypothesis ใหม่ — ไม่มี src/scenario/entry ใหม่) · ไม่แตะ `split_stack` (คง `in_progress` ตามเดิม) แม้ผลรอบนี้จะช่วยแคบ search space ของมัน

**next hop ที่แนะนำ (ไม่ได้ทำในรอบนี้):**
- ยืนยัน op3 ด้วย **live capture**: เปิด verb-2 ในพาเนล `0x5B9F70`, กดยืนยันในกล่อง `0x69`, แล้วจับเฟรม `ItemOperateVitalReq` ที่ `operation==3` (จะได้ทั้ง caption ที่ผู้เล่นเห็นและ byte จริงพร้อมกัน = ปิดข้อ 1 กับ 2 ทีเดียว)
- ถ้าจะทำ **use** ให้ครบเลน: producer ของ `UseItemVital` ยังไม่ pin (object สร้างผ่าน generic class factory ตาม runtime class-id จึงไล่แบบ static ไม่ถึง) — ต้อง live capture หรือ hook

---

## 8. Reproduce

```
py -3 tools/pf_use_drop_sell_static.py                    # 88 guards, exit 0
py -3 -m pytest tests/test_use_drop_sell_static.py -q     # 16 tests
```
verifier รับ path ของ binary ทาง `sys.argv[1]` ได้ (มี `_default_bin()` fallback) · pytest จะ `skip` ทั้งโมดูลถ้าหา `GameClient/GameClient.local.bin` ไม่เจอ

Evidence ทั้งหมด read-only: client binary (disassemble ในเครื่อง ไม่ส่งออก) + server source. **ไม่แตะ GameClient runtime, ไม่แตะ canonical DB, ไม่มี network I/O, ไม่มี git operation.**
