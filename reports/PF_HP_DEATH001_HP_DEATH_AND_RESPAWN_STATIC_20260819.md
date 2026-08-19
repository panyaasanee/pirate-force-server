# PF HP-DEATH-001 — how the client knows an actor is dead, byte by byte: the HP field that is tested against zero, the four `IsDead` predicates, the three-verb Relive family, and what a server would actually have to send

2026-08-19 · assistant lane · **static RE, report-only, additive** · HEAD `fc204c7` · binary `GameClient/GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` · reproduce: `py -3 tools/pf_hp_death_respawn_static.py` (**191 guards, exit 0**), `py -3 tools/pf_hp_death_respawn_static.py --json`, `py -3 -m pytest tests/test_hp_death_respawn_static.py -q`

Milestone: `combat / hp_death_and_respawn`, whose coverage note read **"HP is projected as a static attribute value only. No depletion, death state, corpse, penalty, or respawn path is captured or implemented."** This round settles the *evidence* half — the same shape STATS-PROG-001 used to open the stats lane before STATS-PROG-002 wrote an encoder.

> ⚠️ **READ THIS BEFORE THE ANSWER — ERRATUM 2026-08-19 (รอบ 85, HP-DEATH-ERRATA-001).** Two claims in the paragraph immediately below are **refuted byte-exact** by `reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md` (round 85 lane B, 150 guards). In short: **(1)** *"to make a character die, a server sends one `UpdateAttrVital` … **That is the whole trigger**"* is true **only** for the local player's `Main_Dead` window — `UpdateAttrVital`'s inbound handler `0x5F2400..0x5F261A` contains **zero** `+0x20` dispatch shapes, so that transport **cannot** reach `0x4437C0`, cannot latch `[actor+0x70] |= 0x200`, cannot build `CActorTask_Dead` and **cannot play the animation**. **(2)** §2's *"mask bit `0x0080` set to a **positive** float"* has the **polarity backwards** for the animation: `vt+0x40` (`HP==0 && timer > 0`) latches *dying*, `vt+0x3C` (`HP==0 && timer <= 0`) is what gates the death **task**. Also: §7's open debt ("the inbound `UpdateAttrVital` → `0x4446F0` chain is NOT traced end to end") is now **answered, with a negative**. **Every number and byte span published below still reproduces; what was wrong is the transport sentence and the timer sign.** Full detail: [the ERRATUM appended at the foot of this document](#-erratum-2026-08-19-รอบ-85-hp-death-errata-001--carrier-และ-polarity).

> **One-paragraph answer.** **The client derives death entirely by itself, from the attribute value the server already sends.** Every actor class answers `IsDead` at vtable `+0x40` out of its own bound `Attr`: for `CNetActor`/`CMyActor` that is `0x454AC0`, which loads the attr through `GetAttr` (`vtable +0x74` → `0x44C630` = `mov eax,[ecx+0x348]`), requires the `f32` at `attr+0x58` to be **greater than the constant `0.0f` at `0xF0989C`**, and then returns **`attr.u32[+0x44] == 0`** — i.e. *current HP is zero*. `CNetNPC`/`CAvatarNPC`/`Pet` use the mirror `0x43BDA0` on the same two `BasicAttr` fields. `BasicAttr +0x44` is mask bit `0x0004` and `+0x48` is bit `0x0008` — **the exact pair our server already emits as `current_hp` / `max_hp`** — and `+0x58` is mask bit `0x0080`, the field v141 deliberately omits. There is **no death frame, no death flag and no death verb inbound**: `0x4437C0` (the dead-state sync that latches `[actor+0x70] |= 0x200`, spawns `CActorTask_Dead` and plays `L"_F_DIE_000"`) has exactly one call site, welded to the attr-apply loop inside `0x4446F0` (`call 0x5DF080` then `call 0x4437C0`), and the local player's `Main_Dead` window is opened per frame from `CMyActor::Update` (`vtable +0x18` → `0x44E4E0` → `0x44A540`). **So: to make a character die, a server sends one `UpdateAttrVital` carrying a `BasicAttr` with mask bit `0x0004` = 0 and mask bit `0x0080` set to a positive float. That is the whole trigger.** The other direction — coming back — is a **request-only** verb: `ReliveVital` (`0x1AD4`, 2 bytes of payload, `u8@+0x14` selecting `1` = revive-in-place-with-item and `0` = respawn-at-marker) is one of 69 protocol classes whose inbound slot is the shared no-op `0x710440`, so the client will *decode* a `ReliveVital` echo and then do nothing with it. The **respawn position is not chosen by the client at all**: `ReliveMarkerVital` (`0x3DD6`) merely deposits a marker object in `CMyActor+0x400`, whose only other reader (`0x4E4370`) uses the marker's `u16 @+0x12` as a **scene id** to render a confirmation string — there is not one movement, teleport or position call anywhere in the relive UI span. Our server side of all of this is **zero**: 0 of the 3 verbs have an encoder or dispatch, and 1 of the 3 fields the death predicate reads (`+0x58`) is never emitted.

**Grade:** field identification · four predicates · transition path · verb family with ids and vtables · marker path · negatives = **A** (byte-exact static; the verifier reproduces every address, offset, mask bit and count) · **anything about the ORIGINAL server = not claimed** · net: `combat/hp_death_and_respawn` **`not_started` → `in_progress`** (does **not** flip `runtime_pass`).

---

## 0. Method, scope, and what this is not

**Method.** Static disassembly of the read-only client image, cross-checked against read-only server sources. Everything below is re-derived by `tools/pf_hp_death_respawn_static.py`, which asserts **191 guards** — literal byte spans at fixed addresses, vtable slots, call-site censuses, name-hash reproductions and source counts — and exits non-zero if any one of them drifts. The verifier is **pure stdlib** (`struct`, `hashlib`, `json`, `os`, `re`, `sys`): capstone was used during the investigation, and every disassembly conclusion is frozen here as a byte-pattern guard so the release gate can run it on a bare `py -3`.

**Nothing was executed.** No server booted, no GameClient opened, no socket created, no database touched, no scenario run, no UI test, no network.

**Evidence grades, used strictly.**

| grade | meaning |
| --- | --- |
| **① byte-proof** | an instruction span, a vtable slot, a literal or a reproducible count, asserted by a guard in the verifier. Buildable on. |
| **② structural inference** | a conclusion drawn from ①-grade facts plus the code's own shape. Reasonable to build on **with the inference stated**. |
| **③ guess** | not derived from the binary. **Listed only, never built on.** |

**This is not.** Not a claim about the ORIGINAL server — it is closed, was never published, and everything here derives from the client. Not a runtime observation. Not a damage model, not a combat rule, not a death penalty rule. `current/pf_login_game_server_v141.py` is a **read-only snapshot of a prior AI's work**, not ground truth and not "the original server"; it is opened here only to count what our side does and does not emit. No `src/` file, ledger entry, scenario or hypothesis was touched.

---

## 1. Question 1 — which field is current HP, which is max, and who reads them

### ① byte-proof — the wire layout

`BasicAttr::Serialize 0x4656F0` emits its own `u16` change mask (tag `0x12`, width 2) out of `+0x70`, then gates each field on one bit. The five bits this milestone needs:

| mask bit | offset | tag / width | gate span | field |
| --- | --- | --- | --- | --- |
| `0x0004` | `+0x44` | u32 `0x14` | `0x46574A` `f6 03 04 74 0f 6a 04 8d 56 44 52 6a 14` | **HP current** |
| `0x0008` | `+0x48` | u32 `0x14` | `0x46575E` `f6 03 08 74 0f 6a 04 8d 46 48 50 6a 14` | **HP max** |
| `0x0010` | `+0x4C` | u32 `0x14` | `0x465772` | MP current |
| `0x0020` | `+0x50` | u32 `0x14` | `0x465786` | MP max |
| `0x0080` | `+0x58` | **f32 `0x2A`** | `0x4657AE` `f6 03 80 74 0f 6a 04 8d 4e 58 51 6a 2a` | **death / down timer** |

There is a **second, alternate HP pair** on `ActorAttr`, gated by the *high* half of the 64-bit `ActorAttr` mask at `+0x1B8`:

| high-mask bit | offset | tag / width | gate span |
| --- | --- | --- | --- |
| `0x40` (global bit 38) | `+0x1A8` | u32 `0x14` | `0x4666D7` `f6 86 b8 01 00 00 40 74 12 6a 04 8d 86 a8 01 00 00 50 6a 14` |
| `0x80` (global bit 39) | `+0x1AC` | u32 `0x14` | `0x4666F2` |

### ① byte-proof — current vs max is decided by a consumer, not by a name

The HUD updater `0x53F180` reads the local player (`[0x1032EC4]`), switches on **`byte [actor+0x358]`**, and pushes one of the two pairs into the bar helper `0x53EED0`:

```
0053F1A3  80 b8 58 03 00 00 00   cmp  byte [eax+0x358], 0
0053F1AD  8b b8 48 03 00 00      mov  edi, [eax+0x348]        ; the Attr
0053F1B3  74 18                  je   0x53F1CD
          ; +0x358 != 0  -> the alternate pair
0053F1B5  8b 46 1c / 8b 4e 18 / 8b 97 a8 01 00 00 / 50 / 8b 87 ac 01 00 00 / 51 / 52 / 50
0053F1CD  ; +0x358 == 0  -> the BasicAttr pair
0053F1CD  8b 4e 1c               mov  ecx, [esi+0x1C]         ; NUMBERLABEL_HP widget
0053F1D0  8b 56 18               mov  edx, [esi+0x18]         ; PROGRESSBAR_HP widget
0053F1D3  8b 47 44               mov  eax, [edi+0x44]
0053F1D6  51                     push ecx
0053F1D7  8b 4f 48               mov  ecx, [edi+0x48]
0053F1DA  52 / 50 / 51           push edx ; push eax ; push ecx     <-- +0x48 pushed LAST
0053F1DD  e8 ec fc ff ff         call 0x53EED0
```

`0x53EED0` is unambiguous about which argument is which:

```
0053EEE1  8b 44 24 08            mov  eax, [esp+8]      ; arg0  = the LAST push  = +0x48
0053EEEA  8b 74 24 10            mov  esi, [esp+0x10]   ; arg1  = +0x44
0053EEFE  f2 0f 5e c1            divsd xmm0, xmm1       ; arg1 / arg0
0053EF20  89 b7 20 02 00 00      mov  [edi+0x220], esi  ; the NUMBER the label prints = arg1
```

A value that is the **numerator** of the fill ratio and the **number printed on the label** is *current*; the denominator is *max*. So `+0x44` = current, `+0x48` = max — earned from the consumer, not from adjacency and not from the field name. The MP pair is divided inline in the same routine (`8b 5f 4c` numerator, `8b 47 50` denominator, `f2 0f 5e c1`), which is the same convention on the same class.

### ① byte-proof — the pair selector has exactly one writer

`byte [actor+0x358]` (a `CNetActor`-family field, not to be confused with `CNetNPC::GetAttr`'s `[ecx+0x358]`) is written in exactly one place in the whole `.text`:

```
004564A5  e8 66 a9 fd ff   call 0x430E10            ; scene id -> scene category
004564AD  83 f8 08         cmp  eax, 8
004564B0  0f 94 c0         sete al
004564B3  88 86 58 03 00 00  mov byte [esi+0x358], al
```

**② structural inference:** the alternate HP pair `+0x1A8/+0x1AC` is the HP that applies in scene category `8`. What category 8 *is* is **not claimed** — the mapping lives inside `0x430E10` and the external scene data, and this milestone did not decode it. What is ①-grade is that the *same* selector byte chooses the *same* pair in both the HUD and the death predicate, which is what welds the two fields together.

---

## 2. Question 2 — does the client know "dead", and where does it learn it? ⭐

**This is the answer with the most value, and it is entirely ①-grade.**

### ① byte-proof — four predicates, all reading the HP field

Every actor class in the factory cohort (MP-AUDIT-FOLLOWUP-001: `actor_type` 2..6 → `CNetActor`, `CMyActor`, `CNetNPC`, `CAvatarNPC`, `Pet`) carries **two** death predicates:

| class | `vtable +0x40` | `vtable +0x3C` | `vtable +0x74` (GetAttr) |
| --- | --- | --- | --- |
| `CNetActor` (`0xF0DD08`) | `0x454AC0` | `0x454A70` | `0x44C630` |
| `CMyActor` (`0xF0D7A8`) | `0x454AC0` | `0x454A70` | `0x44C630` |
| `CNetNPC` (`0xF0DF58`) | `0x43BDA0` | `0x43BD70` | `0x45CD20` |
| `CAvatarNPC` (`0xF0DFF8`) | `0x43BDA0` | `0x43BD70` | `0x45CD20` |
| `Pet` (`0xF0E0C8`) | `0x43BDA0` | `0x43BD70` | `0x45CD20` |

`0x44C630` is `mov eax,[ecx+0x348] ; ret`; `0x45CD20` is `mov eax,[ecx+0x358] ; ret`. Both return the bound `Attr`.

The player predicate, in full (`0x454AC0`, 74 bytes, pinned literally by the verifier):

```
00454AC0  56 / 8b f1                     this
00454AC3  8b 06 / 8b 50 74 / ff d2       attr = this->GetAttr()          (vtable +0x74)
00454ACA  f3 0f 10 40 58                 movss xmm0, [attr+0x58]         ; the death timer
00454ACF  0f 2f 05 9c 98 f0 00           comiss xmm0, [0xF0989C]         ; the constant is 0.0f
00454AD6  76 2e                          jbe  -> return false
00454AD8  8b 86 48 03 00 00              eax = this->attr                (the same pointer)
00454ADE  85 c0 / 74 24                  null -> return false
00454AE2  80 be 58 03 00 00 00           cmp  byte [this+0x358], 0
00454AE9  74 0f                          je   0x454AFA
00454AEB  33 c9 / 39 88 a8 01 00 00      cmp  [attr+0x1A8], 0            ; alternate HP
00454AF4  0f 94 c1                       return  altHP == 0
00454AFA  33 d2 / 39 50 44               cmp  [attr+0x44], 0             ; <-- CURRENT HP
00454B00  0f 94 c2                       return  HP == 0
```

`0x454A70` is the same function with the timer gate reversed (`0f 57 c0` / `0f 2f 40 58` / `72 2e`, i.e. it proceeds only when the timer is **≤ 0**). The NPC pair does the HP test first and the timer test second, but on the identical fields:

```
0043BDA0  attr = GetAttr()
0043BDAA  83 78 44 00 / 75 1e      if [attr+0x44] != 0 -> return false
0043BDB0  attr = GetAttr()  (again)
0043BDB9  f3 0f 10 40 58 / 0f 2f 05 9c 98 f0 00 / 76 07   timer must be > 0.0f
0043BDC7  b8 01 00 00 00           return true
```

**None of the four is ever reached by a direct `E8` call** — the verifier asserts `calls_to(...) == []` for all four, so they are pure vtable entry points, which is why they are cheap for any actor class to override and why no other code path can bypass them.

### ① byte-proof — the transition is welded to the attr apply

```
004446F0  8b 44 24 04              eax = arg0 (the incoming attr collection)
004446F4  56 / 8b f1               esi = this (the actor)
004446F7  8b 08 / 85 c9 / 74 2f    null -> nothing to do
004446FD  56 / e8 7d a9 19 00      call 0x5DF080     ; THE ATTR APPLY LOOP
00444703  8b ce / e8 b6 f0 ff ff   call 0x4437C0     ; THE DEAD-STATE SYNC
```

`0x4446F0` **is** `CNetNPC` vtable `+0x20`; `CNetActor`/`CMyActor` vtable `+0x20` is `0x456630`, which reaches `0x4446F0` at `0x4566A7`. Per MP-AUDIT-FOLLOWUP-001, vtable `+0x20` is the *update* path taken by `0x446F30` when an inbound actor entry's identity is already known. `0x4437C0` has **exactly one call site in the image** (`0x444705`) — the verifier asserts the whole list, not just membership.

Inside `0x4437C0`:

```
00443828  8b 42 40 ... ff d0        bl  = this->vtable[+0x40]()      ; IsDead
0044383C  8b 42 3c / 8b ce / ff d0  al  = this->vtable[+0x3C]()
00443843  88 44 24 13               keep it
0044384C  84 db / 0f 84 ...         if !IsDead -> the "still alive / clear" paths
00443854  85 56 70 / 0f 85 ...      already latched?  (edx = 0x200)
0044385D  09 56 70                  [actor+0x70] |= 0x200            ; THE DEAD LATCH
...                                 stop looping sounds, spawn effect 0x232B,
                                    cancel tasks, deregister from 0x5CB9A0
00443990  807c2413 00 / 0f 84 ...   if vtable[+0x3C] -> build the death task
004439C7  ba 24 00 00 00 ...        allocate 0x24 bytes
004439E9  e8 22 ee 02 00            call 0x472810                    ; CActorTask_Dead ctor
00443A01  ...                       if the dead actor is my current target, push
                                    L"TargetIsDead" into L"Main_Panel_Target_Enemy_New"
00443942  81 66 70 ff f9 ff ff      the alive path CLEARS the 0x200/0x400 latch
```

`0x472810` installs vtable `0xF0F048` and task id `0x80000005`; the task's update `0x472850` gates on `test byte [actor+0x70], 0x40` and plays the animation literal at `0xF0F060` — **`L"_F_DIE_000"`** — through actor vtable `+0x28`. `0x472810` also has exactly one call site (`0x4439E9`). The RTTI descriptor at `0x101CDE4` spells **`.?AVCActorTask_Dead@@`**, bound to type node `0x102ED98` by the registrar at `0xBD10B0`; the class name is therefore in-image and not inferred.

### ① byte-proof — the local player's death UI runs per frame

`CMyActor` vtable `+0x18` is `0x44E4E0` (a per-tick update: it decays the float at `[this+0x428]` by the frame delta immediately before the call). At `0x44E828` it calls `0x44A540`:

```
0044A543  8b 06 / 8b 50 40 / ff d2      al = this->vtable[+0x40]()      ; IsDead
0044A54A  84 c0 / 74 5a                 not dead -> close the window
0044A54E  f6 46 10 80 / 75 54           a `this+0x10` bit suppresses it
0044A554  68 38 d7 f0 00                push L"Main_Dead"               (0xF0D738)
0044A559  b9 08 07 09 01 / e8 ...       FindWindow
0044A565  75 3f                         already open -> done
0044A567  8b 86 48 03 00 00             attr = [this+0x348]
0044A56D  f3 0f 10 40 58                xmm0 = [attr+0x58]              ; the same timer
          ... compare against a wall-clock derived value ...
0044A5A1  e8 6a 61 65 00                OpenWindow(L"Main_Dead", ...)   (0xAA0710)
```

**So the death UI is a pure function of the projected attribute, re-evaluated every frame.** No frame from the server is required beyond the attribute itself.

### The consequence for the server, stated plainly

**② structural inference (from ①-grade parts):** to make a character die on this client, a server has to deliver a `BasicAttr` in which mask bit `0x0004` carries `0` **and** mask bit `0x0080` carries a positive float. The already-proven transport for that is `UpdateAttrVital` (`0x309A`, handler `0x5F2400`) or a `RuntimeRes` actor-entry update, both of which end at the same `0x5DF080` apply loop. What is ①-grade: the two fields, the two mask bits, the four predicates, the weld at `0x4446F0` and the per-frame UI gate. What is ②: that *those* transports are the ones a server would pick — this milestone did not trace an inbound `UpdateAttrVital` all the way to `0x4446F0`, and says so in §7.

---

## 3. Question 3 — the death / revive verb family, enumerated

### ① byte-proof — three names in five hundred and nineteen

Every protocol class in this client registers through the PF-NAMEID-HASH-001 once-init thunk shape (`push <literal>; call 0x89C080; mov ecx,eax; call 0x89BD00; mov word [slot],ax; ret`). A full `.text` sweep finds **519** such thunks with **519 distinct names**. Filtering those names for `dead|death|relive|reviv|respawn|corpse|resurrect|dying` returns **exactly three**:

| class (spelled as in the binary) | name VA | **id** | thunk | id-slot | get-id | vtable | sizeof | serializer (`vt +0x18`) | inbound (`vt +0x1C`) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ReliveVital` | `0xF3096C` | **`0x1AD4`** | `0xBEE640` | `0x1082038` | `0x5E5F70` | `0xF30404` | `0x1C` | `0x5E5F80` | **`0x710440` = none** |
| `ReliveMarkerVital` | `0xF30978` | **`0x3DD6`** | `0xBEE660` | `0x108203C` | `0x5E7440` | `0xF305D8` | `0x18` | `0x5EB6D0` | `0x5F0410` |
| `Pets_NotifySailorDeadVital` | `0xF423F8` | **`0x8B12`** | `0xC04410` | `0x1088364` | `0x6FF0B0` | `0xF422BC` | `0x20` | `0x642B00` | `0x700DC0` |

The ids are the PF-NAMEID-HASH-001 hash of the plaintext literal, re-anchored in the same verifier against the three constants v141 already carries (`ActorAttr 0x12AD`, `NPCAttr 0x0AD5`, `UpdateAttrVital 0x309A`). Each sizeof stub (`0x716010`→`0x1C`, `0x721E40`→`0x18`, `0x6217D0`→`0x20`) matches the size the class registrar welds to the `.?AV…@@` descriptor — for `ReliveVital`, `0x42265B` loads descriptor `0x101FB00` (`.?AVReliveVital@@`) and `0x422689` writes `c7 47 0c 1c 00 00 00`.

**The runtime-assigned wall holds:** none of the three ids appears anywhere in `.text` as a 16-bit immediate (`66 B8/B9/BA/BB/3D`, `66 81 F8`, `66 A9`) or as a dword (excluding `E8`/`E9` and `0F 8x` rel32 tails). All three are computed at once-init, same as every earlier cohort.

### ① byte-proof — which ones the client can actually act on

Resolving all 519 registrations to their vtables (via `mov ax,[slot]; ret` → its single `.rdata` slot at `vtable+0x10`) succeeds for **501**; of those, **69 point vtable `+0x1C` at the shared stub `0x710440` (`b0 01 c2 04 00` = `mov al,1 ; ret 4`)** and **432 have a real handler**. `ReliveVital` is one of the 69.

- **`ReliveVital` is request-only.** Its serializer `0x5E5F80` *does* contain a full inbound branch (`e8 73 46 2b 00` → the read codec `0x89A640`), so a server echo will parse — and then hit a stub that returns `true` and discards it. **A `ReliveVital` sent by a server changes nothing on this client.**
- **`ReliveMarkerVital` has a real handler**, `0x5F0410` (see §4).
- **`Pets_NotifySailorDeadVital`** carries exactly one field — `qword` tag `0x32` at `+0x18`, an identity — and its handler `0x700DC0` looks a module up in the local registry (`[0x1032EC4]+0x130`) and forwards. It is about pets/sailors, **not** about the player's own death, and this milestone claims nothing further about it.

### ① byte-proof — `ReliveVital`'s wire, and its three producers

```
ReliveVital  id 0x1AD4  sizeof 0x1C
  u8  (tag 0x08)  @ +0x14        ; ctor zeroes it
  u8  (tag 0x05)  @ +0x18        ; ctor zeroes it
```

The ctor `0x5E5F30` installs vtable `0xF30404`, sets `[+0x10] = 1`, and zeroes `+0x14` and `+0x18`.

The pool allocator `0x4E45B0` has **exactly four** call sites: `0x4E4731`, `0x4E4AE4`, `0x4E4B84` (three UI producers) and `0x5EB11C` (the vtable `+0x14` clone thunk). Each producer writes `+0x14` and then sends through `0x4011A0` → `0x5DD800`:

| producer | gate | `+0x14` |
| --- | --- | --- |
| `0x4E4731` — `BUTTON_RELIVE` handler `0x4E46C0` | local query `has(0x10, 0)` via `0x44A200` returns true | **`1`** |
| `0x4E4B84` — `BUTTON_SPAWN` handler `0x4E4B20`, fast path | `0x432510(0)` returns true | **`0`** |
| `0x4E4AE4` — the confirm-dialog OK callback `0x4E4A90` | user confirmed the `n_DEADLOSS` message | **`0`** |

The whole relive UI span `0x4E46C0..0x4E4D8C` contains **exactly three** sends. `+0x18` is **never written by any producer** — the verifier asserts the absence of both `c6 40 18 xx` and `c7 40 18 …` in that span — so this build always ships `+0x18 = 0`. **② structural inference:** `+0x14` is a two-valued respawn-choice selector (`1` = the item-backed revive, `0` = the marker respawn); `+0x18` is a second selector the UI never exercises. What is ①: the two field offsets, the two tags, the three producers and the exact constants they write.

### ① byte-proof — the death window's widgets

`ReliveConfirmEventHandler` (descriptor `0x10232EC`, node `0x107B3E4`, vtable `0xF2E6A8`) binds three widgets at `vtable +0x18` = `0x4E43A0` and dispatches clicks at `vtable +0x28` = `0x4E4D90`:

| widget literal | VA | cached at | click handler |
| --- | --- | --- | --- |
| `L"BUTTON_RELIVE"` | `0xF1A704` | `this+0x14` | `0x4E46C0` |
| `L"BUTTON_SPAWN"` | `0xF1A6E8` | `this+0x18` | `0x4E4B20` |
| `L"BUTTON_RELIVE_TEXT"` | `0xF1A6C0` | `this+0x1C` | — (label only) |

`MainDeadEventHandler` (descriptor `0x1023E60`, vtable `0xF1F550`) binds `L"BUTTON_DIE"` (`0xF1F5CC`) at `vtable +0x60` = `0x5183D0` and hooks `0x518450` onto it at `vtable +0x18` = `0x5184C0`. `0x518450` builds an action record and writes **`[record+0x30] = 0xEA7C`** before sending — a sibling of the `0xEA7D` attack action this project already documented (SCENE-006/007). **② structural inference:** `0xEA7C` is a "die" / suicide command available from that panel. **③ guess, listed only:** that this button ships in a retail build rather than being a developer affordance — the binary carries a `MainDeadEditorEventHandler` right next to it (descriptor `0x1023E34`), which is suggestive, but nothing in the image says so.

---

## 4. Question 4 — the respawn point: the client does not pick one

### ① byte-proof — `ReliveMarkerVital` deposits a marker and nothing else happens

```
005F0410  a1 c4 2e 03 01           eax = [0x1032EC4]                ; the local player
005F0418  85 c0 / 74 30            no local player -> return true
005F041C  8b 88 00 04 00 00        ecx = [player+0x400]             ; the current marker
005F0423  8d b0 00 04 00 00        esi = &player[0x400]
005F0429  3b 4f 14 / 74 17         same object -> done
005F042E  ... e8 29 cc 29 00       release the old  (0x88D060)
005F0437  8b 4f 14 / 89 0e         [player+0x400] = vital[+0x14]
005F043C  ... e8 0b cc 29 00       addref the new   (0x88D050)
```

The marker sub-object's own serializer is `0x5DF250`:

```
u16    (tag 0x12)  @ +0x12
qword  (tag 0x32)  @ +0x18
u8     (tag 0x0B)  @ +0x10
u8     (tag 0x0B)  @ +0x11
nested list        @ +0x20   (0x5F3490)
```

`CMyActor+0x400` has exactly **two** readers in `.text`: the handler above, and `0x4E4370` (`GetMarker`: read, addref, return), which has exactly **one** caller — `0x4E4BBA`, inside the `BUTTON_SPAWN` handler. What that caller does with the marker is one thing only:

```
004E4BDD  0f b7 4f 12              movzx ecx, word [marker+0x12]    ; treat +0x12 as a SCENE ID
004E4BE2  68 9c c5 f0 00           push L"SCENE_NAME_TIP"           (0xF0C59C)
004E4BE7  b9 d0 cd 08 01 / e8 ...  static-data row lookup
004E4BFF  68 c4 c3 f0 00           push L"s_SCENE_NAME"             (0xF0C3C4)
```

— i.e. it renders the destination scene's *name* into the confirmation text.

### ① byte-proof — nothing in the relive path moves the player

The verifier asserts that the relive UI span `0x4E46C0..0x4E4D8C` contains **no call** to the movement-control entry `0x484580`, the position setter `0x485B90`, or `0x43E1D0`. Combined with `ReliveVital` having no inbound handler, that closes the question: **the client neither chooses a respawn position nor applies one on its own.** It sends a two-byte request and waits.

**② structural inference:** the respawn position must therefore arrive the same way every other authoritative reposition does in this project — as a `MovementAttr` / actor-entry update or a `TeleportVital` — which is consistent with the project's existing finding that *movement* is client-authoritative for the local walk loop while *placement* is server-projected (MOVE-AUTHORITY-001). What is ①: the absence of any position call in the relive span, and the marker's only use being a name lookup.

### ① byte-proof — the death penalty is external data, read for display only

`BUTTON_SPAWN` looks up `L"STANDARD_STATUS"` (`0xF152AC`) keyed by the level word `BasicAttr+0x5E` (`8b 81 48 03 00 00 / 0f b7 40 5e`) and pulls the column **`L"n_DEADLOSS"`** (`0xF14BC8`) — twice, once per scene-variant branch — to format the confirmation string. The *value* of `n_DEADLOSS` is not in the executable; only the column name and the lookup are. **The client displays the penalty; it does not apply it.** Whatever `n_DEADLOSS` means numerically is **not claimed here**.

---

## 5. Server gap, in numbers

All of these are counted by the verifier against the read-only `current/pf_login_game_server_v141.py` snapshot and `src/pirateforce_foundation/`, never by eye.

```json HP_DEATH_COUNTS
{
  "measured_at_head": "fc204c7",
  "guards": 191,
  "registered_protocol_classes": 519,
  "registered_classes_with_resolved_vtable": 501,
  "classes_with_no_inbound_handler": 69,
  "classes_with_inbound_handler": 432,
  "client_death_revive_verbs": 3,
  "client_death_revive_verbs_with_client_decoder": 2,
  "server_death_revive_encoders": 0,
  "server_death_revive_dispatch": 0,
  "death_predicates_in_client": 4,
  "basicattr_wire_fields_total": 12,
  "basicattr_mask_bits_emitted_by_us": 7,
  "fields_read_by_the_death_predicate": 3,
  "fields_read_by_the_death_predicate_emitted_by_us": 2,
  "server_call_sites_emitting_zero_current_hp": 0,
  "server_references_to_basicattr_bit_0x0080": 0,
  "server_references_to_actorattr_0x1A8_pair": 0,
  "server_handlers_for_action_0xEA7C": 0
}
```

| dimension | client | server (v141 snapshot + `src/`) |
| --- | --- | --- |
| death/revive protocol classes | **3** (`ReliveVital`, `ReliveMarkerVital`, `Pets_NotifySailorDeadVital`) | **0 encoders, 0 dispatch, 0 id literals** |
| fields the death predicate reads | **3** (`+0x44`, `+0x58`, and the alternate `+0x1A8`) | **2** — `+0x44` and its partner `+0x48` are already emitted; `+0x58` and `+0x1A8/+0x1AC` are never emitted |
| `BasicAttr` wire fields | **12 gated** (measured from the serializer, not typed) | **7 mask bits ever set by us** (`0x0001` name, `0x0004`/`0x0008` HP pair, `0x0040` speed, `0x0100`/`0x0200` scene pair, `0x0400` faction). STATS-PROG-001 reported 6 for v141 alone; the seventh, `0x0400`, is set only in `src/`. |
| current HP values ever sent | any `u32` | **never `0`** — `current_hp` is a parameter but no call site passes zero |
| respawn marker | `ReliveMarkerVital` → `CMyActor+0x400` | **not built** |
| debug die action `0xEA7C` | one UI producer | **no handler** |

**The single most useful number in this table:** the gap between "the client can be made to die" and "our server can make it die" is **one mask bit and one float**. Bit `0x0004` is already wired end to end for both NPC and player projections; bit `0x0080` (`f32 @ +0x58`, tag `0x2A`) has never been set by our side, and it is the *only* extra field the predicate needs.

---

## 6. Negative results — proven absences, each one a guard

1. **There is no "you died" frame.** Of 519 registered protocol classes, exactly three carry a death token, and none of the three is an inbound death notification for the local player. The client's death state is computed, not received.
2. **`ReliveVital` has no client-side effect.** Its inbound slot is the shared `mov al,1 ; ret 4` stub `0x710440`, one of 69 such classes. A server that echoes a `ReliveVital` accomplishes nothing.
3. **The client never writes `ReliveVital +0x18`.** All three producers leave it at the constructor's `0`. Whatever that byte means, this build cannot express it.
4. **The client selects no respawn position.** No call to `0x484580`, `0x485B90` or `0x43E1D0` exists in `0x4E46C0..0x4E4D8C`; the only three sends in that span are the three `ReliveVital` producers.
5. **`CMyActor+0x400` (the marker) is read in exactly two places**, and the only use of its contents is a `SCENE_NAME_TIP` name lookup on the `u16 @ +0x12`.
6. **The four death predicates are never called directly.** No `E8` call anywhere in `.text` targets `0x454AC0`, `0x454A70`, `0x43BDA0` or `0x43BD70`; they are vtable-only.
7. **The dead-state sync has exactly one entry point.** `0x4437C0` ← `0x444705` only, and `CActorTask_Dead`'s constructor `0x472810` ← `0x4439E9` only. There is no second, hidden death path.
8. **The death penalty number is not in the executable.** `n_DEADLOSS` is a column name in the external `STANDARD_STATUS` table; only the literal and the lookup are in-image. No penalty *rule* is recoverable from the binary.
9. **The three wire ids never appear as `.text` constants.** 0 imm16 hits and 0 dword hits for `0x1AD4`, `0x3DD6`, `0x8B12` — the runtime-assigned wall holds for this cohort too.
10. **Our side has none of it.** 0 id literals, 0 encoders, 0 dispatch, 0 emissions of `current_hp == 0`, 0 uses of `BasicAttr` bit `0x0080`, 0 handlers for action `0xEA7C`.

---

## 7. Explicit non-claims and known debt

- **Nothing about the ORIGINAL server.** No death rule, no respawn policy, no penalty formula, no revive cost is claimed to be what any server ever did. The original is closed and was never published; there is no capture of any of this, and none can exist.
- **Nothing was captured or executed.** This is entirely static. `combat/hp_death_and_respawn` moves `not_started` → `in_progress` and **never** `runtime_pass` here.
- **The inbound `UpdateAttrVital` → `0x4446F0` chain is NOT traced end to end.** `0x5F2400` (the `UpdateAttrVital` handler) merges each attr through the Attr's own vtable `+0x24` copy thunk and fans out local events; this milestone did **not** prove which call re-enters `0x4446F0`/`0x4437C0` for that transport. What *is* proven is that the per-frame `0x44A540` gate re-reads the attribute every tick, so the death **UI** does not depend on that chain. Anyone building the encoder should treat "an `UpdateAttrVital` alone latches `[actor+0x70] |= 0x200`" as **② at best** until it is either traced or observed.
- **`0x430E10`'s scene-category mapping is not decoded.** The alternate HP pair's activation condition is stated as "category == 8", not as a scene name.
- **The nested list at marker `+0x20` is not decoded**, nor are the marker's `u8` fields at `+0x10`/`+0x11`, nor the `qword` at `+0x18`.
- **`Pets_NotifySailorDeadVital`'s downstream behaviour is not traced** past its first forward.
- **No damage model.** How HP *reaches* zero — who computes it, what a hit costs — is entirely outside this milestone and outside the binary's static reach. SCENE-013's structural combat-corpus negative still stands.
- **No claim that any composition renders.** Nothing here says that a real client shown a zero-HP `BasicAttr` will visibly fall over; that requires a runtime pass.
- **③ guesses, listed and not built on:** that `BasicAttr +0x58` counts *down* rather than up; that `+0x1A8/+0x1AC` is a ship/vehicle HP pool; that `BUTTON_DIE` ships to players. None of the three is derived from the binary and none is used anywhere above.

---

## 8. Suggested next steps (not done here)

- **The cheapest possible GT.** One headless or attended pass that sends a single `UpdateAttrVital` carrying `BasicAttr` mask `0x0004|0x0080` with `current_hp = 0` and a positive `+0x58`, then observes whether `Main_Dead` opens. That single frame flips this lane from static to runtime-proven and simultaneously settles the §7 debt about the inbound chain.
- **The encoder.** A `src/` module that can emit the `BasicAttr` death pair (`0x0004` = 0, `0x0080` = f32) — the natural HP-DEATH-002, mirroring STATS-PROG-002.
- **`ReliveVital` inbound.** Because the client has no handler, a server must answer a relive request with an *attribute + placement* update, not with an echo. Worth writing down before anyone builds a request/response pair that cannot work.
- **Scene-category decode.** Resolve `0x430E10`'s mapping so the alternate HP pair can be named rather than described.

---

## 9. How to reproduce

```
py -3 tools/pf_hp_death_respawn_static.py                        # 191 guards, exit 0
py -3 tools/pf_hp_death_respawn_static.py --json                 # machine-readable
py -3 -m pytest tests/test_hp_death_respawn_static.py -q
```

The verifier is pure stdlib and needs no third-party package. It reads the client image at `GameClient/GameClient.local.bin` (with the same staging fallback the other static tools use) and opens `current/pf_login_game_server_v141.py` and `src/` **read-only** for the gap count. It touches no network, no database, no GameClient process and no server source.

---

## ⚠ ERRATUM 2026-08-19 (รอบ 85, HP-DEATH-ERRATA-001) — carrier และ polarity

**ตัวเลข ที่อยู่ (address) มาสก์บิต และ span hash ทุกตัวในรายงานนี้ยังถูกต้องและยังรีโปรดิวซ์ได้ทั้งหมด — `py -3 tools/pf_hp_death_respawn_static.py` ยัง 191 guards / exit 0 · สิ่งที่ผิดคือ *ประโยค* สองประโยค: ตัวขนส่ง (carrier) กับเครื่องหมายของ timer**

ตามแบบแผนที่รอบ 82 ตั้งไว้และรอบ 84 ใช้ซ้ำ: **ประโยคเดิมไม่ถูกลบและไม่ถูกแก้ให้เนียน** — ถ้าลบทิ้ง คนที่เคยอ่านและเอาไปอ้างต่อจะไม่มีทางรู้ว่าตัวเองอ้างอะไรผิด บล็อกนี้จึงเป็นส่วนเพิ่ม และมีบล็อกเตือนคู่กันวางไว้ **เหนือย่อหน้า one-paragraph answer** เพื่อไม่ให้คำเตือนไปซ่อนอยู่ท้ายไฟล์ 400 บรรทัด (บังคับด้วยเทส `tests/test_hp_death_erratum.py`)

**แหล่งหักล้าง:** `reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md` (RUNTIMERES-ACTOR-ENTRY-001, รอบ 85 เลน B) · reproduce: `py -3 tools/pf_runtimeres_actor_entry_static.py` (**150 guards, exit 0**), `py -3 -m pytest tests/test_runtimeres_actor_entry_static.py -q` · binary เดียวกัน SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` · วิธีนับเป็น byte matching ล้วน ไม่ใช้ linear disassembler เลย (ซึ่งคือ failure mode ที่รอบ 83 โดน)

### E1 — §2 "That is the whole trigger" ผิดสำหรับทุกอย่างที่ไม่ใช่หน้าต่างของผู้เล่นเอง

| | |
| --- | --- |
| **ประโยคเดิม** (§0 one-paragraph answer และ §2 "The consequence for the server, stated plainly") | *"to make a character die, a server sends one `UpdateAttrVital` carrying a `BasicAttr` with mask bit `0x0004` = 0 and mask bit `0x0080` set to a positive float. **That is the whole trigger**."* |
| **สิ่งที่พิสูจน์ได้ตอนนี้** | ทั่วทั้งช่วง `0x5F2400..0x5F261A` (inbound handler ของ `UpdateAttrVital`) มี `mov r,[reg+0x20] … call r` dispatch shape **0 อัน** และมี direct call ไปยัง `0x4446F0` / `0x456630` / `0x4437C0` / `0x446F30` **0 อัน** (span ถูกตรึงด้วย hash ⇒ เป็น negative ทั้งช่วง ไม่ใช่การสุ่มดู) |
| **ผลที่ตามมา** | `UpdateAttrVital` **ไปไม่ถึง** `0x4437C0` ⇒ ไม่ latch `[actor+0x70] \| 0x200` · ไม่หยุด looping sound · ไม่สร้าง `CActorTask_Dead` · **ไม่เล่น `L"_F_DIE_000"`** · ไม่ดัน `L"TargetIsDead"` |
| **ส่วนที่ยังจริง** | หน้าต่าง `Main_Dead` ของ **ผู้เล่นเอง** ยังเปิดได้จริงด้วยเฟรมเดียวนั้น เพราะ `0x44A540` อ่าน attribute ใหม่ทุกเฟรม ไม่ต้องพึ่งโซ่นี้ — §2's "the death UI is a pure function of the projected attribute" **ไม่ถูกหักล้าง** |
| **carrier ที่ถูก** | `GSCN_RunTimeProtocolRes` (id `0x6E9D` = 28317, sizeof `0x28`) → **derived change-mask bit `0x02`, object `+0x1C`** → `0x5E4060` → `0x5E4085 call 0x446F30` (**1 caller ทั้งอิมเมจ, 0 pointer**) → identity **ที่รู้จักแล้ว** → vtable `+0x20` → `0x4446F0` → `0x4437C0` |

> 🔴 **และมีเงื่อนไขที่รายงานฉบับนี้ไม่ได้พูดถึงเลย: actor เกิดมาตายเลยไม่ได้.** `0x446F30` ค้น identity 64-bit ของ entry ก่อน — *เจอ* → vtable `+0x20` (apply + dead-sync); *ไม่เจอ* → `0x446990` (spawn) ซึ่ง apply ผ่าน vtable `+0x10` และ **ไม่แตะ `0x4437C0` เลยทั้ง 5 คลาส** ⇒ ลำดับขั้นต่ำฝั่งเซิร์ฟเวอร์คือ **สองเฟรมของ identity เดียวกัน**: เฟรมที่ spawn แล้วค่อยเฟรมที่ฆ่า

### E2 — §2 "positive float" มี polarity กลับด้านสำหรับแอนิเมชัน

| | |
| --- | --- |
| **ประโยคเดิม** | *"mask bit `0x0080` set to a **positive** float"* / §2 "a `BasicAttr` in which mask bit `0x0004` carries `0` **and** mask bit `0x0080` carries a positive float" / §8 "with `current_hp = 0` and **a positive `+0x58`**" |
| **สิ่งที่พิสูจน์ได้ตอนนี้** | `vt+0x40` (`0x43BDA0`) = `HP==0 **AND** timer > 0.0f` → gate **ของ dying latch** · `vt+0x3C` (`0x43BD70`) = `HP==0 **AND** timer <= 0.0f` → gate **ของ death task** · ภายใน `0x4437C0`: `bl` (`+0x40`) คุม `0x44384C` (`[actor+0x70] \|= 0x200`) และ `[esp+0x13]` (`+0x3C`) คุม `0x443990` ซึ่งครอบ `0x4439E9 call 0x472810` ทั้งก้อน |
| **ผลที่ตามมา** | ทั้งสอง predicate **เป็นจริงพร้อมกันไม่ได้บน snapshot เดียว**: `+0x58` เป็นบวก ⇒ ได้ latch **แต่ไม่ได้แอนิเมชัน** · `+0x58` ≤ 0 หรือไม่ส่งบิต `0x0080` มาเลย (พร้อม `HP == 0`) ⇒ **ได้แอนิเมชัน** |
| **สิ่งที่ *ไม่* ถูกหักล้าง** | ตัวฟิลด์เอง (`f32 @ +0x58`, mask bit `0x0080`, tag `0x2A`) ยังถูกต้องทุกตัวเลข · การอ่าน gate ใน §2 (`0x454AC0` ใช้ `timer > 0`) ก็ยังถูกต้อง — สิ่งที่ผิดคือ **สรุปว่าค่าบวกคือค่าที่เซิร์ฟเวอร์อยากส่ง** |
| **ข้อควรระวังเพิ่ม (เลน B, ②)** | `[actor+0x70] & 0x40` ("model loaded", เขียนได้ 2 ที่: `0x4448B4`, `0x4599B4`) เป็น gate ที่สองของแอนิเมชัน — actor ที่ visual ไม่เคย resolve จะ latch และได้ `CActorTask_Dead` แต่ **ไม่มีวันเล่นท่าตาย** |

### E3 — §7 หนี้ที่เปิดไว้ ตอนนี้ปิดแล้ว ด้วยคำตอบ "ไม่"

§7 เขียนว่า *"The inbound `UpdateAttrVital` → `0x4446F0` chain is NOT traced end to end … treat 'an `UpdateAttrVital` alone latches `[actor+0x70] |= 0x200`' as **② at best** until it is either traced or observed."* — **ประโยคนี้ตั้งท่าถูกต้อง** และตอนนี้ถูกตอบแล้ว: มันถูก trace แล้ว และคำตอบคือ **ไม่ ①-grade** (E1) ⇒ ข้อความ "② at best" ควรอ่านว่า **"พิสูจน์แล้วว่าเป็นเท็จ"** ไม่ใช่ "ยังไม่รู้"

**§8 ("Suggested next steps") จึงต้องอ่านใหม่:** GT ที่แนะนำไว้ — ส่ง `UpdateAttrVital` เดียวพร้อม `+0x58` เป็นบวกแล้วดูว่า `Main_Dead` เปิดไหม — **ยังเป็น GT ที่มีความหมาย** แต่มันเทสได้แค่ครึ่งเดียว (หน้าต่างของผู้เล่นเอง) และ **จะไม่มีวันทำให้อะไรล้มลง** สูตรที่จะทำให้ NPC ล้มอยู่ใน RUNTIMERES-ACTOR-ENTRY-001 §4 (spawn ก่อน แล้วส่ง actor-entry ซ้ำของ identity เดิมด้วย `current_hp = 0` และ **ละ** bit `0x0080`) และยังเป็น **②** จนกว่าจะมี runtime pass

### สิ่งที่ erratum นี้ **ไม่** อ้าง

- ไม่อ้างว่ามีเลขใดในรายงานนี้ผิด — เลน B รีโปรดิวซ์ `0x4446F0` / `0x4437C0` / `0x472810` / `L"_F_DIE_000"` ได้ตรงกันทุกตัว และ census ของ `0x4437C0` (1 direct caller, **0 pointer**) ยืนยัน §6 ข้อ 7 ตามเดิม
- ไม่อ้างอะไรเกี่ยวกับ **ORIGINAL server** — ปิดไปแล้ว ไม่เคย publish ไม่มี capture ของการตาย
- ไม่อ้างว่า client จริงเคยเรนเดอร์ศพ — ยังไม่มี runtime pass ทั้งสองเลน
- ไม่แตะ matrix row, ledger, scenario หรือ `src/` — erratum นี้เป็น report-only เหมือนตัวรายงาน
- **หมายเหตุถึง chief:** เลน B บันทึกว่าการ flip `runtime_pass` ของ `combat/hp_death_and_respawn` ในรอบ 84 ทำบนเลนที่ทำให้อะไรล้มไม่ได้ — erratum นี้ **ไม่** ขยับแถวนั้นเอง เป็นคำตัดสินของ chief

**บังคับด้วยเทส:** `tests/test_hp_death_erratum.py` — พิสูจน์ว่าบล็อกเตือนอยู่ **ก่อน** ย่อหน้า one-paragraph answer จริง ๆ (ไม่ใช่แค่ "มีอยู่ที่ไหนสักแห่งในไฟล์"), ว่า erratum ท้ายไฟล์มีอยู่และชี้ไปหาแหล่งหักล้าง, และว่าประโยคเดิมทั้งสองยัง **อยู่ครบไม่ถูกลบ**
