# PF_STATS_PROG001 — the client's character stats & progression surface: the `*Attr` class chain, level / experience / HP-MP / primary attributes / allocation points / skill points as named fields with byte offsets and dirty-mask bits, the five progression verbs and their wire schemas — byte-exact static + server cross-check

2026-08-18 · chief assistant (single-scope task) · report-only additive · milestone `character_management / stats_and_progression` (`not_started`) · binary `GameClient/GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` · capstone 5.0.x (CS_MODE_32, ImageBase 0x400000, PE section table parsed in-tool) · reproduce: `py -3 tools/pf_stats_progression_static.py` (99 guards, exit 0) + `py -3 -m pytest tests/test_stats_progression_static.py -q` (25 passed)

Goal: retire the lane's coverage note — **"The proven projection carries name and cash only. No level, experience, attribute point, or progression rule is modeled, persisted, or captured."** — for its *identifier* and *field* halves, from static byte-exact evidence only, **without touching v141 (immutable), without touching the canonical DB, without opening GameClient, without any network**, and **without claiming anything about the ORIGINAL server** (nothing here was captured on a wire).

> **Headline results:**
> - **Level, experience, HP, MP, class, skill points, allocation points and the five primary attributes are no longer unmodeled.** Each one is a concrete field with an owning class, a byte offset, a dirty-mask bit, a wire tag and a width — and each name comes from an **in-image consumer** (a script binding, a HUD bar, a UI panel), never from genre convention.
> - **14 classes** form the cohort, all registered by the same PF-NAMEID-HASH-001 once-init thunk shape (`push <name literal>; call 0x89C080; mov ecx,eax; call 0x89BD00; mov word[id-slot],ax; ret`). Re-applying the hash at `0x89B220` reproduces **ActorAttr `0x12AD`, NPCAttr `0x0AD5`, UpdateAttrVital `0x309A`** — three ids v141 *already carries as committed constants* — which anchors the other eleven.
> - **Hierarchy:** `Attribute` → `DBAttribute` → `BasicAttr` → {`ActorAttr`, `NPCAttr`}; `AvatarAttr` and `CSkillAttr` hang off `DBAttribute`; `FightAttr` off `Attribute`. The wire layout is the class chain, base first: `ActorAttr::Serialize` calls `BasicAttr::Serialize` calls `DBAttribute::Serialize`.
> - **Every Attr is dirty-mask gated.** `DBAttribute` u8 mask `+0x20`; `BasicAttr` u16 mask `+0x70` (12 gated fields); `ActorAttr` **64-bit** mask staged from `+0x1B4`/`+0x1B8` (43 gated fields); `AvatarAttr` u32 mask `+0x28` (21 gated fields).
> - **⭐ LEVEL = `BasicAttr` u16 `+0x5E`, mask bit `0x0002`.** Proven by the script binding `"GetLv"` whose handler `0x460050` does `mov eax,[[0x1032EC4]+0x348]; movzx ecx, word [eax+0x5E]`. Three further independent readers hit the same word.
> - **⭐ EXPERIENCE = `ActorAttr` qword `+0xA0`, mask bit `0x400`.** The XP bar at `0x519299` reads the level word, looks up `STANDARD_STATUS[level+1].n_EXP_CURRENTLV`, reads the 64-bit value at `+0xA0/+0xA4`, and computes `value*100/requirement` — a progress percentage. The already-proven **cash** qword sits immediately after it at `+0xA8`, bit `0x800`; the two are told apart by their consumers, not by position.
> - **⭐ MP = `BasicAttr` u32 `+0x4C`/`+0x50`, bits `0x0010`/`0x0020`**, alongside the already-proven HP pair `+0x44`/`+0x48`. The HUD updater `0x53F1AD` divides `+0x4C` by `+0x50` into the widget cached for `PROGRESSBAR_MP`. The static-data schema calls the same ceiling `n_STAMINAMAX`, so "MP" in this game is the stamina pool.
> - **⭐ SKILL POINTS = `ActorAttr` u32 `+0x7C`, bit `0x0008`** — the skill window at `0x75C613` writes it straight into `NUMBERLABEL_SPNOW`. **CLASS = `ActorAttr` u32 `+0x8C`, bit `0x0001`** (binding `"GetClass"`).
> - **⭐ Five primary attributes = `ActorAttr` u16 `+0x82/+0x84/+0x86/+0x88/+0x8A`** (bits `0x20/0x40/0x80/0x100/0x200`) with **matching bonus fields at `+0x182/+0x184/+0x186/+0x188/+0x18A`** (bits `0x40000..0x400000`). Named **STR / CON / DEX / INT / PER** by the `Char_Info2` panel, which binds one getter per label row. `ActorAttr` u16 `+0x80` (bit `0x10`) is **not** a sixth attribute: it caps the allocation spinner and gates the ±buttons — it is the **unspent allocation-point pool**.
> - **⭐ `AbilityDepolyAll` `0x36AD` carries exactly five signed 16-bit deltas at `+0x14/16/18/1A/1C`, in the order STR, CON, DEX, INT, PER** — proven end to end: the `BUTTON_STRUP..BUTTON_PERUP` click handler writes five pending counters, and the producer lifts those same five counters into those same five fields.
> - **`AbilityDepoly` `0x260B` has exactly one UI producer**, `0x57F83B`, which always ships the constructor defaults with only `+0x15` forced to `6` — a single fixed `(1, 6, 1)` triple, gated on level and on a `COIN_CONSUME` row. It is the **paid attribute-reset** verb, not the per-point allocate verb.
> - **Negatives that are worth as much as the positives:** the script bindings `AddExp` / `AddAbilityPoint` / `AddSkillPoint` build **no vital and touch no Attr field** — they only broadcast a *local* event carrying the ASCII token `"exp"` / `"ap"` / `"sp"`. `Attribute` and `FightAttr` both point their serializer slot at `0x515EC0`, a bare `ret 8`, so they carry **zero** wire fields in this build. And the per-level *numbers* (`n_EXP_CURRENTLV`, `n_POINT_ABILITY`, `POTENTIAL.n_STRENGH`…) live in the external static-data tables — only the column names and the lookup code are in-image.
> - **Server gap is total.** v141 declares **none** of the 14 ids as a literal, emits **1 of the 43** `ActorAttr` fields (cash, mask `0x800`) and **6 of the 12** `BasicAttr` fields (name, HP pair, speed, scene pair). Of the **19 named progression fields, exactly 2 are emitted** (the HP pair, already runtime-proven for a different lane). Of the **5 progression verbs, 0** have any encoder or dispatch, in v141 or in `src/`.
>
> **Grade:** class/id table · id wall · vtable map · hierarchy · 11 decoded serializers · 19 named fields with mask bits · verb schemas · producer chains = **A** (byte-exact static, verifier reproduces, every claim carries an address or a byte pin) · **anything about the original server's progression rules = not claimed** · net: `character_management/stats_and_progression` **`not_started` → `in_progress`** (does **not** flip `runtime_pass`).

---

## 1. The cohort — 14 classes, ids derived from the in-image literals

The id is computed from the plaintext class-name literal alone, with the PF-NAMEID-HASH-001 hash (client `0x89B220`, `u16 id = Σᵢ (int16)((signed char)name[i]·(i+1)) mod 2¹⁶`). Every row has one registration thunk, one id-slot, one get-id stub and one vtable.

| # | class (spelled as in the binary) | name VA | **id** | reg thunk | id-slot | get-id | vtable | serializer | sizeof | parent |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `Attribute` | `0xF0E748` | **`0x1306`** | `0xBD92D0` | `0x1033458` | `0x467640` | `0xF0E850` | `0x515EC0` *(none)* | — | *(engine root)* |
| 2 | `DBAttribute` | `0xF0E8D0` | **`0x1B36`** | `0xBD9530` | `0x10334B8` | `0x467680` | `0xF0E890` | `0x467790` | `0x28` | `Attribute` |
| 3 | `BasicAttr` | `0xF0E820` | **`0x1244`** | `0xBD93B0` | `0x103349C` | `0x464A60` | `0xF0E760` | `0x4656F0` | `0x78` | `DBAttribute` |
| 4 | `ActorAttr` | `0xF0E82C` | **`0x12AD`** ⭐ | `0xBD93D0` | `0x10334A0` | `0x464E40` | `0xF0E7A0` | `0x466230` | `0x1C0` | `BasicAttr` |
| 5 | `NPCAttr` | `0xF0E838` | **`0x0AD5`** ⭐ | `0xBD93F0` | `0x10334A4` | `0x4652C0` | `0xF0E7E0` | `0x466EB0` | `0xC0` | `BasicAttr` |
| 6 | `AvatarAttr` | `0xF0E754` | **`0x16A0`** | `0xBD9350` | `0x1033468` | `0x45E150` | `0xF0E088` | `0x464560` | `0x90` | `DBAttribute` |
| 7 | `FightAttr` | `0xF0E920` | **`0x1285`** | `0xBD95A0` | `0x10334CC` | `0x467A20` | `0xF0E8E0` | `0x515EC0` *(none)* | `0x1C` | `Attribute` |
| 8 | `CSkillAttr` | `0xF48BB8` | **`0x1661`** | `0xC0C530` | `0x108A32C` | `0x751BF0` | `0xF48B78` | `0x7520B0` | `0x50` | `DBAttribute` |
| 9 | `UpdateAttrVital` | `0xF0B374` | **`0x309A`** ⭐ | `0xBEE5C0` | `0x1082028` | `0x5E5DB0` | `0xF303E0` | `0x5E42C0` | `0x44` | vital base |
| 10 | `AbilityDepoly` | `0xF30918` | **`0x260B`** | `0xBEE580` | `0x1082020` | `0x5E5BA0` | `0xF30398` | `0x5E5BB0` | `0x18` | vital base |
| 11 | `AbilityDepolyAll` | `0xF30928` | **`0x36AD`** | `0xBEE5A0` | `0x1082024` | `0x5E5C70` | `0xF303BC` | `0x5E5C80` | `0x20` | vital base |
| 12 | `CLearnSkillVital` | `0xF48F00` | **`0x36AA`** | `0xC0C860` | `0x108A3F4` | `0x755AA0` | `0xF48E94` | `0x755AC0` | `0x1C` | vital base |
| 13 | `CLearnSkillResultVital` | `0xF0B54C` | **`0x673C`** | `0xC0C880` | `0x108A3F8` | `0x755E90` | `0xF48EDC` | `0x756100` | `0x30` | vital base |
| 14 | `CRevertSkilltVital` | `0xF48F14` | **`0x45F0`** | `0xC0C8A0` | `0x108A3FC` | `0x755B50` | `0xF48EB8` | `0x755B70` | `0x20` | vital base |

⭐ = the three ids v141 already carries as committed constants (`ACTOR_ATTR`, `NPC_ATTR`, `UPDATE_ATTR_VITAL`). They are the **anchor**: the hash reproduces them from the literals, so the other eleven derived ids inherit that confidence.

- All 14 ids are pairwise distinct.
- **No id appears as a 16-bit immediate anywhere in `.text`** (`66 B8/B9/BA/3D/81 F8/A9 <imm16>` scan → 0 hits). 12 of the 14 have **no `.text` dword occurrence at all** (dword scan excluding `E8/E9` **and** `0F 8x` rel32 tails). The two that do are pinned byte coincidences, not immediates: `0x16A0` × 5 are the disp32 of `[esi+0x16A0]` field accesses (`f3 0f 10 8e a0 16 00 00` etc.), and `0x1306` × 1 is the modrm+imm straddle of `c7 06 13 00 00 00` = `mov dword [esi],0x13`. The runtime-assigned wall holds, same as the TargetPos / Channel_* / ItemOperate cohorts.
- Every id-slot has **exactly one writer** (its own thunk) and **exactly one reader** (`mov ax,[slot]; ret`, which is vtable `+0x10`). Every get-id stub is referenced from **exactly one** `.rdata` slot, so each class has exactly one vtable and this table is complete for the cohort.
- vtable `+0x08` is `0x401B20` for all 14 — the same shared framework const as the earlier cohorts. vtable `+0x0C` is a `mov eax,<sizeof>; ret` stub whose value matches the decoded layout for the 13 classes that declare one.
- **The serializer slot differs by branch:** Attr classes use vtable **`+0x34`**, vitals use vtable **`+0x18`**. That is why a naive "+0x18 is Serialize" sweep, which works for the `Channel_*` family, returns a setter (`0x43BB80`) for `AvatarAttr` and finds nothing.
- **Spelling in the binary is authoritative:** `AbilityDepoly` (not "Deploy"), `CRevertSkilltVital` (not "SkillVital"), `n_STRENGH` (not "STRENGTH"). Correcting any of them changes the hash.

## 2. Hierarchy and the base-first wire layout

Read from the type-node registrar `0x88F2E0`; each node also carries an MSVC `.?AV…@@` descriptor that reproduces the class name, so **two independent name paths converge for all 14**.

```
Attribute                       (serializer slot -> ret 8; no wire fields)
  |- DBAttribute                u8 mask +0x20, qword identity +0x18
  |    |- BasicAttr             u16 mask +0x70, 12 gated fields
  |    |    |- ActorAttr        u64 mask +0x1B4/+0x1B8, 43 gated fields
  |    |    \- NPCAttr          u8 mask +0xBC, 7 gated fields
  |    |- AvatarAttr            u32 mask +0x28, 21 gated fields
  |    \- CSkillAttr            learned-skill container
  \- FightAttr                  (serializer slot -> ret 8; no wire fields)

UpdateAttrVital / AbilityDepoly / AbilityDepolyAll /
CLearnSkillVital / CLearnSkillResultVital / CRevertSkilltVital
                                 all parented on the vital base node 0x10823A8
```

The wire follows the chain, base first:
`ActorAttr::Serialize 0x466230` → `call 0x4656F0` (`BasicAttr`) → `call 0x467790` (`DBAttribute`).
`AvatarAttr::Serialize 0x464560` → `call 0x467790` directly, skipping `BasicAttr` — it is a sibling appearance block, not a character block. `CSkillAttr::Serialize 0x7520B0` likewise chains `DBAttribute` only.

## 3. Codecs

Same codec family as MOVE-PROJECT-001 / CHAT-CHANNEL-001, so nothing new is asserted about the encoding itself:

- **scalar** `0x89A600` write / `0x89A640` read — `stdcall(tag, ptr, width) ret 0xC`
- **wstring** `0x89A810` write / `0x89A880` read — tag `0x48` + `u32` byte-length + UTF-16LE payload
- **blob** `0x89A6D0` write / `0x89A700` read — tag `0x44`, an opaque byte block. Used by `ActorAttr@+0x148` and `AvatarAttr@+0x64`. **Its contents are not claimed here.**

Tags seen in this cohort and their widths: `0x05`/1, `0x08`/1, `0x0B`/1, **`0x0F`/2 (signed 16-bit)**, `0x12`/2, `0x14`/4, `0x19`/4, `0x26`/4, `0x2A`/4 (float), `0x32`/8, `0x44` blob, `0x48` wstring.

## 4. `BasicAttr` — the shared character header (mask `+0x70`, 12 gated fields)

| bit | offset | tag / width | gate pin | meaning |
|---|---|---|---|---|
| `0x0001` | `+0x28` | wstring `0x48` | `0x465727` | name *(already proven upstream)* |
| **`0x0002`** | **`+0x5E`** | **u16 `0x12`** | `0x465736` `f6 03 02` | **LEVEL** |
| `0x0004` | `+0x44` | u32 `0x14` | `0x46574A` | HP current *(already proven upstream)* |
| `0x0008` | `+0x48` | u32 `0x14` | `0x46575E` | HP max *(already proven upstream)* |
| **`0x0010`** | **`+0x4C`** | **u32 `0x14`** | `0x465772` `f6 03 10` | **MP current** |
| **`0x0020`** | **`+0x50`** | **u32 `0x14`** | `0x465786` `f6 03 20` | **MP max** |
| `0x0040` | `+0x54` | f32 `0x2A` | `0x46579A` | movement speed *(already proven upstream)* |
| `0x0080` | `+0x58` | f32 `0x2A` | `0x4657AE` | down-state timer *(already proven upstream)* |
| `0x0100` | `+0x5C` | u16 `0x12` | `0x4657C2` | scene id *(already proven upstream)* |
| `0x0200` | `+0x60` | qword `0x32` | `0x4657E3` | scene sequence *(already proven upstream)* |
| `0x0400` | `+0x68` | u32 `0x14` | `0x465804` | faction *(already proven upstream)* |
| `0x0800` | `+0x6C` | u32 `0x14` | `0x465825` | *(not claimed)* |

## 5. `ActorAttr` — the player block (64-bit mask, 43 gated fields)

The mask is **two dwords** at `+0x1B4`/`+0x1B8`, copied onto the stack at `0x466252` (`8b 8e b8 01 00 00 / 8b 86 b4 01 00 00 / 8d 54 24 14 / 52`) and emitted as **one qword, tag `0x32`**. Then a **u8 extra-group flag, tag `0x05`, at `+0x1BC`** gates the whole high half.

Named fields (the rest of the 43 are decoded in the harness but **not named** here):

| bit | offset | tag / width | gate pin | meaning | naming evidence |
|---|---|---|---|---|---|
| `0x00000001` | `+0x8C` | u32 `0x19` | `0x466299` | **class** | script binding `"GetClass"` handler `0x460160` |
| `0x00000008` | `+0x7C` | u32 `0x19` | `0x4662EC` | **skill points** | skill window `0x75C613` → `NUMBERLABEL_SPNOW` |
| `0x00000010` | `+0x80` | u16 `0x12` | `0x466304` | **unspent allocation points** | spinner cap `0x57DD7A`; ± gate `0x53B1FB/0x53B215/0x53B237` |
| `0x00000020` | `+0x82` | u16 `0x12` | `0x46631F` | **STR base** | getter `0x467A60` → `LABEL_STR` |
| `0x00000040` | `+0x84` | u16 `0x12` | `0x46633A` | **CON base** | getter `0x467AF0` → `LABEL_CON` |
| `0x00000080` | `+0x86` | u16 `0x12` | `0x466355` | **DEX base** | getter `0x467B80` → `LABEL_DEX` |
| `0x00000100` | `+0x88` | u16 `0x12` | `0x466370` (`ebx`=0x100 @`0x46628C`) | **INT base** | getter `0x467CA0` → `LABEL_INT` |
| `0x00000200` | `+0x8A` | u16 `0x12` | `0x46638A` | **PER base** | getter `0x467C10` → `LABEL_PER` |
| **`0x00000400`** | **`+0xA0`** | **qword `0x32`** | `0x4663A8` | **EXPERIENCE** | XP bar `0x519299`/`0x5192C6`/`0x519314` |
| `0x00000800` | `+0xA8` | qword `0x32` | `0x4663C6` | cash *(already proven upstream)* | binding `"GetCash"` `0x4600AC` |
| `0x00040000` | `+0x182` | u16 `0x12` | `0x466490` | **STR bonus** | second half of getter `0x467A60` |
| `0x00080000` | `+0x184` | u16 `0x12` | `0x4664AE` | **CON bonus** | second half of getter `0x467AF0` |
| `0x00100000` | `+0x186` | u16 `0x12` | `0x4664CC` | **DEX bonus** | second half of getter `0x467B80` |
| `0x00200000` | `+0x188` | u16 `0x12` | `0x4664EA` | **INT bonus** | second half of getter `0x467CA0` |
| `0x00400000` | `+0x18A` | u16 `0x12` | `0x466508` | **PER bonus** | second half of getter `0x467C10` |

Also decoded but **not named**: `+0x90` (u32, bit `0x2`), `+0x78` (u32 tag `0x26`, bit `0x4`), `+0x94`, `+0x98`, `+0x99`, `+0x9A`, `+0x9B`, `+0xB0`/`+0xCC`/`+0xE8`/`+0x104`/`+0x120` (wstrings), `+0x140` (qword), `+0x148` (blob), `+0x164` (wstring — the persisted player name, already proven upstream by `src/pirateforce_foundation/player_wire.py`), `+0x13C`/`+0x13E`, `+0x180`, `+0x18C`, `+0x190`/`+0x198`, `+0x1A0`/`+0x1A2`/`+0x1A4`, `+0x1A8`/`+0x1AC`, `+0x1B0`, `+0x1B2`.

## 6. How each name was earned (no genre guessing anywhere)

**LEVEL — `BasicAttr` u16 `+0x5E`.**
The script-binding table registers the literal `"GetLv"` (`0xF0E65C`) at `0x461ADE` with handler `0x460050`, and that handler is six instructions long:

```
0x460050  a1 c4 2e 03 01     mov  eax, [0x1032EC4]        ; module registry root
0x46005C  8b 80 48 03 00 00  mov  eax, [eax+0x348]        ; the LOCAL PLAYER's Attr
0x460062  0f b7 48 5e        movzx ecx, word [eax+0x5E]   ; <-- level
```

Three further independent consumers read the same word: a level gate at `0x43290C`, the XP-bar lookup at `0x5192A5`, and the attribute-reset cost gate at `0x57F81A`.

**EXPERIENCE — `ActorAttr` qword `+0xA0`.**
The XP bar opens the static table `"STANDARD_STATUS"` (`0xF152AC`), reads the level word, increments it, looks up the column `"n_EXP_CURRENTLV"` (`0xF14C00`) for `level+1`, then:

```
0x5192C6  a1 c4 2e 03 01     mov  eax, [0x1032EC4]
0x5192CB  8b 80 48 03 00 00  mov  eax, [eax+0x348]
0x5192D1  8b 88 a0 00 00 00  mov  ecx, [eax+0xA0]        ; low half
0x5192D7  8b 80 a4 00 00 00  mov  eax, [eax+0xA4]        ; high half
...
0x51931A  6b c0 64           imul eax, eax, 0x64          ; * 100
0x51931E  f7 ff              idiv edi                     ; / requirement
```

A value divided by "experience required for the next level" to make a percentage is experience. The neighbouring qword `+0xA8` is the field the `"GetCash"` binding reads — so the two adjacent qwords are separated by their consumers, not by guesswork about which one is money.

**HP / MP — `BasicAttr` `+0x44`/`+0x48` and `+0x4C`/`+0x50`.**
The HUD binder emits, per widget, `push <name>; mov ecx,esi; mov [esi+K],eax; call 0xAA1750`. Because the store precedes the lookup, **each store holds the previous name's result** — a one-instruction shift that mislabels every slot if ignored. Applying it: `PROGRESSBAR_HP`→`+0x18`, `NUMBERLABEL_HP`→`+0x1C`, `PROGRESSBAR_MP`→`+0x20`, `NUMBERLABEL_MP`→`+0x24`. The updater `0x53F1AD` then loads the same player Attr, pushes `+0x44`/`+0x48` into the HP path, and divides `+0x4C` by `+0x50` (`divsd` at `0x53F20C`) into the widget cached at `+0x20`. The client's own static-data schema names the two ceilings `n_HPMAX` (`0xF14F24`) and `n_STAMINAMAX` (`0xF14EEC`) — **"MP" here is the stamina pool**, which is why the second bar exists at all.

**SKILL POINTS — `ActorAttr` u32 `+0x7C`.**

```
0x75C613  8b 88 48 03 00 00  mov  ecx, [eax+0x348]
0x75C619  8b 49 7c           mov  ecx, [ecx+0x7C]        ; <-- skill point balance
0x75C624  8b 46 6c           mov  eax, [esi+0x6C]        ; NUMBERLABEL_SPNOW widget
0x75C62D  89 88 20 02 00 00  mov  [eax+0x220], ecx
```

**The five primary attributes.**
Five sibling getters exist, each of the exact same shape, each reading **one aligned base/bonus pair**:

| getter | base | bonus | equip bonus |
|---|---|---|---|
| `0x467A60` | `+0x82` | `+0x182` | `+0xD4` |
| `0x467AF0` | `+0x84` | `+0x184` | `+0xD8` |
| `0x467B80` | `+0x86` | `+0x186` | `+0xDC` |
| `0x467CA0` | `+0x88` | `+0x188` | `+0xE4` |
| `0x467C10` | `+0x8A` | `+0x18A` | `+0xE0` |

The `Char_Info2` panel binder caches `LABEL_STR`…`LABEL_PER` at `+0x84`…`+0x94` (same one-instruction shift as above), and the stat-row updater at `0x57E6BD..0x57E76C` calls exactly one getter per label:

```
0x57E6C8  call 0x467A60  ->  [esi+0x84] = LABEL_STR   =>  +0x82 is STR
0x57E6EB  call 0x467AF0  ->  [esi+0x88] = LABEL_CON   =>  +0x84 is CON
0x57E70E  call 0x467B80  ->  [esi+0x8C] = LABEL_DEX   =>  +0x86 is DEX
0x57E731  call 0x467CA0  ->  [esi+0x90] = LABEL_INT   =>  +0x88 is INT
0x57E754  call 0x467C10  ->  [esi+0x94] = LABEL_PER   =>  +0x8A is PER
```

Independently, the client's static-data schema declares exactly five primary columns for the `POTENTIAL` table — `n_STRENGH` (sic), `n_CONSTITUTION`, `n_AGILITY`, `n_INTELLECT`, `n_PERCEPTION` — the same cardinality as the five base/bonus pairs and the five UI rows. **The column→offset binding itself is NOT claimed**: the schema binder at `0x4A4372..0x4A4560` writes into a table row struct, not into an `ActorAttr`, and no code path was found that copies a `POTENTIAL` column into `+0x82..+0x8A`. Four of the five names line up with the UI labels by spelling (`STRENGH`/STR, `CONSTITUTION`/CON, `INTELLECT`/INT, `PERCEPTION`/PER), which leaves `AGILITY`/DEX as the only remaining pairing — but that last step is an inference from cardinality, not a byte-exact proof, and is recorded here as such.

**`+0x80` is not a sixth attribute.** Its only consumers cap an allocation spinner (`0x57DD7A`: `movzx edx, word [attr+0x80]` then `cmp [spinner+0x220], edx`) and enable/disable the ± controls while it is `> 0` (`0x53B1FB`, `0x53B215`, `0x53B237`). That is an unspent-point pool, not a stat. The static-data schema has a matching per-level column, `n_POINT_ABILITY` (`0xF14BE0`), sitting right beside `n_EXP_CURRENTLV` — the two progression curves.

## 7. The progression verbs

| id | class | wire schema | notes |
|---|---|---|---|
| `0x260B` | `AbilityDepoly` | `u8(0x08)@+0x14` → `u8(0x08)@+0x15` → **`i16(0x0F)@+0x16`** | ctor `0x5E5B60` defaults `(1, 0, 1)` |
| `0x36AD` | `AbilityDepolyAll` | **`i16(0x0F)@+0x14` → `+0x16` → `+0x18` → `+0x1A` → `+0x1C`** | ctor `0x5E5C20` zeroes all five |
| `0x36AA` | `CLearnSkillVital` | `u32(0x14)@+0x14` → `u8(0x0B)@+0x18` | skill id + flag |
| `0x673C` | `CLearnSkillResultVital` | nested list serializer at `+0x14` (`0x755D30`/`0x756070`), then `u8(0x0B)@+0x2C` | trailing result byte |
| `0x45F0` | `CRevertSkilltVital` | `u32(0x14)@+0x14` → `qword(0x32)@+0x18` | skill id + a 64-bit handle |
| `0x309A` | `UpdateAttrVital` | none of its own — `0x5E42C0` re-bases `this+0x14` and tail-jumps to the shared Attr-collection codec `0x463DE0`; inbound handler is vtable `+0x1C` = `0x5F2400` | the delta transport v141 already documents |

**Tag `0x0F` is a *signed* 16-bit field.** That is what makes `AbilityDepolyAll` an allocate/deallocate delta message rather than an absolute set.

**The STR/CON/DEX/INT/PER order of `AbilityDepolyAll` is proven end to end, not assumed.** The `Char_Info2` click handler `0x57C1F4` compares the clicked widget against the five UP buttons in slot order `+0xD4/D8/DC/E0/E4` (= `BUTTON_STRUP`, `CONUP`, `DEXUP`, `INTUP`, `PERUP` after the binder shift) and increments five pending counters — `+0x1C8`, `+0x1CC`, `+0x1D0`, `+0x1D4`, `+0x1D8` respectively, refreshing the matching `LABEL_DEPLOY_*`. The producer `0x57F6F0` then copies those five counters into the five wire fields in the same order:

```
0x57F733  movzx ecx,[edi+0x1C8] ; mov [eax+0x14],cx     ; STR
0x57F73E  movzx edx,[edi+0x1CC] ; mov [eax+0x16],dx     ; CON
0x57F749  movzx ecx,[edi+0x1D0] ; mov [eax+0x18],cx     ; DEX
0x57F754  movzx edx,[edi+0x1D4] ; mov [eax+0x1A],dx     ; INT
0x57F75F  movzx ecx,[edi+0x1D8] ; mov [eax+0x1C],cx     ; PER
```

**`AbilityDepoly` is used for exactly one thing.** Its allocator `0x57DFB0` has exactly two callers: the generic protocol factory `0x5EB07C` and the single UI producer `0x57F83B`. That producer forces only `+0x15 = 6` (`c6 40 15 06`) and submits the constructor defaults otherwise — a fixed `(1, 6, 1)` triple. The surrounding code gates it on the player's level and on a `COIN_CONSUME` table row, i.e. this is the **paid attribute-reset** verb. All actual per-point allocation goes through `AbilityDepolyAll`.

## 8. Negative results (each one reproduced as a guard)

1. **`AddExp` / `AddAbilityPoint` / `AddSkillPoint` cannot grant anything.** The bindings exist (`0xF0E628`, `0xF0E5F0`, `0xF0E5E0`) with handlers `0x460EC0`, `0x4612A0`, `0x4613D0`, but each one only pushes an ASCII token — `"exp"` `0xF0E1CC`, `"ap"` `0xF0E1D8`, `"sp"` `0xF0E1DC` — and calls the **local listener fan-out** `0x5F9C70` through `[0x1032EC4]+0x130`. That routine is a pure `call [vtable+0x40]` loop over subscribers: it invokes **no codec** and constructs **no vital**. No `AbilityDepoly*` / `CLearnSkill*` / `CRevertSkillt*` object is constructed anywhere inside those three handlers.
2. **`Attribute` (`0x1306`) and `FightAttr` (`0x1285`) carry zero wire fields.** Both point their serializer slot (`+0x34`) at `0x515EC0`, which is the single instruction `ret 8`. This is an in-build fact, not a gap in the analysis.
3. **`CSkillAttr`'s object offsets are not recoverable from its serializer alone.** It stages every emitted value through a stack temp before the codec call, so the decoded displacements are ESP/EBX-relative. Only its *shape* is claimed: it chains `DBAttribute`, emits a u16 count, then iterates a container emitting per-entry u16/u32. **No `CSkillAttr` object offset is claimed by this milestone.**
4. **The progression numbers are not in the executable.** `STANDARD_STATUS` (`n_EXP_CURRENTLV`, `n_POINT_ABILITY`, `n_HPMAX`, `n_STAMINAMAX`, …) and `POTENTIAL` (`n_LEVEL`, `n_STRENGH`, `n_CONSTITUTION`, `n_AGILITY`, `n_INTELLECT`, `n_PERCEPTION`) are **external static-data tables**. Only their column-name literals and the lookup call sites are in-image. Any actual curve — how much XP level N needs, how many points a level grants, what the class base stats are — remains **unknown** and would require decoding those data files, which this milestone did not do.
5. **The opaque blob fields are not decoded.** `ActorAttr@+0x148` and `AvatarAttr@+0x64` go through the tag-`0x44` blob codec; their internal structure is not claimed.
6. **No inbound handler for the progression verbs was traced.** This report names their *producer* side and their wire schema. What the client does when a `CLearnSkillResultVital` or an `AbilityDepolyAll` echo arrives is **not** part of this milestone.

## 9. Explicit non-claims

- **Nothing about the ORIGINAL server.** This is the client's expectation of the protocol, byte-exact, and nothing else. No progression rule, no XP formula, no allocation validation, no reset cost is claimed to be what any server ever did.
- **Nothing was captured.** No wire observation, no runtime pass, no session. Every statement here is static.
- **Nothing about persistence.** Whether level / exp / points survive a logout is untouched by this milestone. The project's persistence scope is unchanged.
- **No `runtime_pass`.** The lane moves `not_started` → `in_progress` only. Turning any of these fields into a runtime claim needs a real game session and a real capture.
- **The 24 unnamed `ActorAttr` fields stay unnamed.** They are decoded (offset, tag, width, mask bit) but deliberately not interpreted.
- **Field *semantics* beyond the 19 named ones are not inferred from neighbours.** Adjacency was never used as evidence; every name has its own consumer.

## 10. Server gap, in numbers

| dimension | client | server (v141 + `src/`) |
|---|---|---|
| classes in the cohort | **14** | 0 ids declared as literals |
| `BasicAttr` wire fields | **12 gated** (+1 mask) | **6 emitted** (name, HP cur/max, speed, scene id, scene seq) |
| `ActorAttr` wire fields | **43 gated** (+2 header) | **1 emitted** (cash, mask bit `0x800`) |
| named progression fields | **19** | **2 emitted** (the HP pair — already runtime-proven for a different lane) |
| level / exp / MP / class / skill points / allocation points / 5 attributes / 5 bonuses | **17 fields** | **0 emitted, 0 decoded** |
| progression verbs (`AbilityDepoly`, `AbilityDepolyAll`, `CLearnSkillVital`, `CLearnSkillResultVital`, `CRevertSkilltVital`) | **5** | **0 encoders, 0 dispatch**, in v141 and in `src/pirateforce_foundation/` |

v141's only `ActorAttr` encoder writes the 64-bit mask literally as `struct.pack("<II", 0x800, 0)`; its `BasicAttr` masks are `0x0004|0x0008|0x0100|0x0200` (+ `0x0001` name, + `0x0040` speed) and `0x000C|0x0100|0x0200`. Mask bit `0x0002` (level) and bits `0x0010`/`0x0020` (MP) are never set anywhere in the file.

## 11. How to reproduce

```
py -3 tools/pf_stats_progression_static.py            # 99 guards, exit 0
py -3 -m pytest tests/test_stats_progression_static.py -q   # 25 passed
```

Both accept the client image at `GameClient/GameClient.local.bin` (the tool also falls back to `packages/.v134_staging_20260815_0355/GameClient.local.bin`; the two are the same SHA-256). Both require `capstone`; the pytest file parses the PE header itself and needs nothing else. Neither touches the network, the DB, the GameClient process, or any server source — v141 and `src/` are opened read-only for the gap cross-check.

## 12. Suggested next steps (not done here)

- **GT candidate:** a runtime pass that observes one `UpdateAttrVital` carrying `ActorAttr` mask bit `0x0400` and confirms the client's XP bar moves. That would be the cheapest way to flip `experience` from static to runtime-proven, and it needs no second session.
- **Data-file lane:** decode `STANDARD_STATUS` and `POTENTIAL` from the external static-data files to recover the actual per-level curves. Purely a data task; no client RE needed once the container format is known.
- **Inbound half:** trace vtable `+0x1C` for `AbilityDepolyAll` / `CLearnSkillResultVital` to see what the client does with a server reply. That is the missing half of this lane's request/response pairs.
