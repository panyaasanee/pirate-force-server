# PF UI-REFRESH-001 — the character-select state machine, the one buffer the list is drawn from, and why an acknowledgement can never refresh it (static, byte-exact)

Date: 2026-08-19
Round: chief scheduled round 79 (report-only, additive, static reverse engineering)
Grade claim: **static / byte-exact** — client-binary only. No runtime claim, no ledger entry, no matrix flip, no `src/` change, no scenario.
Verifier: `tools/pf_ui_state_refresh_static.py` — **292 guards**, pure standard library, exit 0 = PASS.
Regression test: `tests/test_ui_state_refresh_static.py`.

---

## WHY THIS EXISTS

Two attended rounds produced the same shape of failure:

* **GT-011** — a spec-exact 79-byte `DeleteActorVital` (0x36DB) acknowledgement (77 B + trailing derived-class mask). No error dialog at all, the soft delete committed in the database, and the character-select list did **not** refresh: the character stayed, its name board stayed, and afterwards other buttons on that screen stopped responding.
* **GT-013** — a complete worldinfo-first logout sequence (283 B → 46 B). Every byte accepted, and the client did **not** transition. Shapes 1 (echo), 2 (ack+close) and 3 (worldinfo-first) are all falsified.

The tester's lead — *the client may not change state from the acknowledgement of a command, but waits for a different KIND of frame (list-refresh / state-change / screen-transition)* — was explicitly **not** a conclusion. This milestone decides it from the bytes of the read-only client image, and enumerates the machinery so the next design round does not have to guess a fourth shape.

**Sole evidence:** `GameClient/GameClient.local.bin` (PE32 x86, ImageBase 0x400000, 14,759,424 B, SHA-256 `9627211412AC60D5…B623`), plus a read-only cross-check against `current/pf_login_game_server_v141.py`. **Nothing was executed:** no server booted, no GameClient opened, no socket, no database, no network. capstone was used to *find* these facts on the sandbox; the shipped verifier is pure `struct`/`hashlib`/`os`/`sys`/`json` and reduces every claim to a byte comparison, because the release gate runs `py -3` on Windows with no third-party packages.

---

## THE ANSWER IN ONE PARAGRAPH

The client keeps the whole character list in **one** buffer: the collection at offset `+0x180` of a process-wide singleton cached in `[0x1081A90]` (accessor `0x4011A0`, constructor `0x5DE7D0`). An exhaustive scan of `.text` finds **32** instructions that form `<reg>+0x180`; only six of them belong to this singleton, and the complete set of mutators is *fill* `0x5DDD00` (one caller in the entire image: `0x5EFCAC`, inside the `SelectActorVital` 0x36EF apply method), *append-one* `0x5DDE10` (one caller: `0x5EFD76`, inside the `CreateActorVital` 0x36CF apply method), and *clear* `0x5DDF00` / `0x5DE540`. **There is no erase-by-key path anywhere in the image.** The `DeleteActorVital` acknowledgement (apply `0x5EFDC0` → `cStateCreateActor::OnDeleteResult 0x4BAEB0`) only writes `record+0xF4` — and only when its first field is 3 or 4; for every other value, including the `1` our server sends, it *repaints* the screen from that same, unchanged collection. That is why GT-011's list did not refresh: the ack is a repaint command, and the only frame in the protocol that can make a character disappear is a fresh `SelectActorVital` (0x36EF), which resets the singleton and refills it. Symmetrically, `LogoutVital` (0x1B40) apply `0x5EF930` → `0x5DC660` is a *confirm-dialog controller*: field `+0x18` values `-0x13..-1` print a client string, `0x14` opens `L"SystemSetting_LogoutConfirm"`, `0x16` closes it, everything else returns — **no branch of it calls `CState::RequestNext 0x4C7320` and no branch touches the live state pointer `[0x1093198]+0x34C`**. Of the eighteen state transitions that exist in the whole image, only three sit inside an inbound vital apply (`SelectActorVital`→`cStateCreateActor`, `TeleportVital`→`cStateSwitchScene`, and a singleton method→`cStateSwitchScene`); leaving the world is not one of them. So the tester's lead is **confirmed for GT-011** (a different frame *kind* — `SelectActorVital` — is required) and **refined for GT-013** (there is no logout frame kind at all; the vital only drives a dialog).

---

## WHAT IS PROVEN

### 1. The screen is a state object — ten registered state classes  · evidence: **byte-proof**

The client uses a custom RTTI-ish registrar (`0x88F2E0`), one thunk per class, each pushing its own `.?AV<name>@@` type descriptor and caching a class-node token in a global slot. Ten state classes are registered:

| class | type descriptor | registrar thunk | class-node token | token getter | state vtable |
|---|---|---|---|---|---|
| `cStateInitGame` | `0x1022EB0` | `0xBDBBA0` | `0x107A52C` | `0x4C4CB0` | `0xF169D8` |
| `cStateDisplayLogo` | `0x1022ED0` | `0xBDBBE0` | `0x107A520` | `0x4C4C80` | `0xF16A10` |
| `cStateLogin` | `0x1022EF4` | `0xBDBD70` | `0x107A5AC` | `0x4C51D0` | `0xF16B58` |
| `cStateSelectServer` | `0x1022F14` | `0xBDBEE0` | `0x107A5BC` | `0x4C5CE0` | `0xF16D30` |
| **`cStateCreateActor`** | **`0x1022D5C`** | **`0xBDB800`** | **`0x107A38C`** | **`0x4C0110`** | **`0xF16520`** |
| `cStateSwitchScene` | `0x1022F3C` | `0xBDC050` | `0x107A608` | `0x4C65D0` | `0xF16E7C` |
| `cStateFullScreenMovie` | `0x102150C` | `0xBDB9D0` | `0x107A4B4` | `0x4C40E0` | `0xF168CC` |
| `CState` (base) | `0x1022F60` | `0xBDC090` | `0x107A640` | `0x4C7310` | — |
| `StateNavigation` | `0x1022F7C` | `0xBDC330` | `0x107A6A8` | `0x4C7690` | — |
| `StateRunTime` | `0x1022FA0` | `0xBDC4A0` | `0x107A6E4` | `0x4C8740` | `0xF170E4` |

The **character-select screen is `cStateCreateActor`** — not a guess: `SelectActorVital`'s apply allocates exactly `0x770` bytes and runs constructor `0x4C03E0`, whose vtable `0xF16520` slot 0 *is* the token getter `0x4C0110`, whose returned slot `0x107A38C` *is* the one the registrar thunk at `0xBDB800` filled from the literal `.?AVcStateCreateActor@@`. The class name is bound to a string literal in the image, not invented here.

The live state pointer is `[0x1093198] + 0x34C`; every consumer reads it with the same two instructions (`A1 98 31 09 01` / `8B B0 4C 03 00 00`).

Transitions all go through `CState::RequestNext 0x4C7320`, byte-exact:

```
0x4C7320: 56              push esi
          8B F1           mov  esi, ecx
          8B 4E 10        mov  ecx, [esi+0x10]      ; previous pending state
          85 C9 / 74 10   test/je
          8B 01 8B 50 04 6A 01 FF D2                ; delete it
          C7 46 10 00000000
          80 7C 24 0C 00  cmp  byte [esp+0xC], 0    ; "immediate" flag
          8B 44 24 08     mov  eax, [esp+8]         ; next state
          89 46 10        mov  [esi+0x10], eax
          74 07 / C7 46 0C 02000000                 ; this+0x0C = 2
          5E              pop esi
```

### 2. The character-select screen has a page variable that gates its input  · evidence: **byte-proof**

`cStateCreateActor` vtable **+0x14 = `0x4C3C40`** is the per-frame method, and it dispatches on the global dword **`0x107A2C0`** through a **15-entry** jump table at `0x4C3E30` (pages `0x00 … 0x0E`; entry 15 is `CC CC CC CC` padding, i.e. **any page value above 0x0E makes the whole screen do nothing**):

```
0x4C3C40: A1 C0 A2 07 01     mov eax, [0x107A2C0]
          56 57 8B F1
          83 F8 0E           cmp eax, 0x0E
          0F 87 87 01 00 00  ja  0x4C3DD9          ; -> nothing at all
          FF 24 85 30 3E 4C 00   jmp [eax*4 + 0x4C3E30]
```

Input handling is gated on the same global being zero, e.g. `0x4BEEA9: 83 3D C0 A2 07 01 00 / 75 3C` (`cmp dword [0x107A2C0], 0 ; jne skip`). Exactly **20** instructions in `.text` write it with an immediate; the verifier pins all twenty with their values. The delete animation immediately above the delete-result handler sets it to **0x0B** (`0x4BAE91: C7 05 C0 A2 07 01 0B 00 00 00`), and — see §4 — **`OnDeleteResult` contains no write to `0x107A2C0` at all.**

### 3. The character list buffer, and every path that writes, clears or rebuilds it  · evidence: **byte-proof**

```
0x4011A0   accessor: mov eax,[0x1081A90]; if null -> new 0x1A8 bytes, ctor 0x5DE7D0,
                     store back, register destructor 0x5DE9C0 at exit
singleton  +0x180    the character collection (built by 0x58CD10 at 0x5DE8C3)
           +0x19C    element count (read by the free-slot gate)
```

| operation | function | callers in the ENTIRE image |
|---|---|---|
| bulk fill (one record per actor in the frame) | `0x5DDD00` | **exactly one:** `0x5EFCAC`, inside `SelectActorVital` (0x36EF) apply `0x5EFC40` |
| append one record | `0x5DDE10` | **exactly one:** `0x5EFD76`, inside `CreateActorVital` (0x36CF) apply `0x5EFD50` |
| clear | `0x5DDF00` | three: `0x406C3A` (app reset — itself the first call `SelectActorVital`'s apply makes), `0x5DE2E4`, `0x5DE994` (constructor) |
| clear (teardown) | `0x5DE540` | one: `0x5DE9CD`, the atexit destructor |
| look one record up by key | `0x5F8400` | used by the delete-result handler only, to write `record+0xF4` |
| **erase one record by key** | — | **none exists** |

The verifier enumerates *all 32* `<reg>+0x180` instructions in `.text` and pins the exact address list, so "there is no other writer" is a checked statement rather than a claim about how hard someone looked. The free-slot gate `0x4B405F` reads the collection size and compares it with the global `0x10337FC`, which is the client setting named `L"MAX_CHAR_COUNT"` (`0xF135E0`).

**Consequence, stated plainly:** the client cannot be told "one character went away". It can only be told "here is the whole list again" (`SelectActorVital`) or "here is one more" (`CreateActorVital`).

### 4. `DeleteActorVital` 0x36DB — what the acknowledgement actually does  · evidence: **byte-proof**

Vital classes expose their wire id at vtable **+0x10**, their serializer at **+0x18** and their **inbound apply at +0x1C**. For 0x36DB (vtable `0xF301A0`): id getter `0x5E4D90` (`66 A1 D0 1F 08 01 C3` → slot `0x1081FD0`), serializer `0x5E4E10` (u8 `+0x14`, u8 `+0x15`, u32 `+0x18`, wstring `+0x1C` — the field order DELETE-003 already pinned), apply **`0x5EFDC0`**.

`0x5EFDC0` checks that the live state is `cStateCreateActor` (token getter `0x4C0110`, is-a `0x88F2B0`) and forwards the three scalars to **`cStateCreateActor::OnDeleteResult 0x4BAEB0`** — which has exactly one caller in the image.

`0x4BAEB0` does, in order:

1. `push 0xF15F00` → looks up the UI window `L"Login_CharSelect_Panel_Operations"`; **if that window is absent it returns immediately**.
2. `call 0x4011A0` → `lea esi,[eax+0x180]` (the character collection).
3. `cmp al,3 / je` … `cmp al,4 / jne 0x4BB155` on field `+0x14`.
   * **field+0x14 ∈ {3,4}** → `0x5F8400` finds a record and writes `record+0xF4 = field+0x18`. `record+0xF4` is exactly the field the slot-rebuild `0x4B9980` tests (`cmp dword [eax+0xF4], 0 / jle skip`) before it creates a name board — i.e. **a pending-delete countdown**.
   * **every other value, including the `1` our server sends** → `0x4BB155`: `call 0x4B90A0` (scene actor rebuild), `call 0x4B9980` (slot widget rebuild), then a loop that resets each slot widget, then three UI descriptors pushed into the operations panel: `L"Set_DeleteBtn_Visible"` (`0xF161A0`), `L"Set_DeleteBtn_Text"` (`0xF16178`, parameter = `field+0x18 == 0`) and `L"Set_EditBtn_Disable"` (`0xF16150`).
4. Return.

Checked negatives inside the whole handler body `[0x4BAEB0, 0x4BB618)`:

* it **never** calls `0x5DDD00`, `0x5DDE10`, `0x5DDF00`, `0x5DE540` or the app reset `0x406C30` — so it cannot change the list;
* it **never** calls `CState::RequestNext 0x4C7320` — so it cannot change screen;
* it **never** references `0x107A2C0` — so it cannot restore the page variable it was entered on.

### 5. `LogoutVital` 0x1B40 — a confirm-dialog controller  · evidence: **byte-proof**

Apply `0x5EF930` is eleven instructions: it pushes `+0x1C`, `+0x18`, `+0x14` and calls `0x5DC660` on the singleton. `0x5DC660` computes `field+0x18 + 0x13`, and:

* `> 0x12` → default: store `+0x14` into singleton `+0xE0`, then `cmp edx,0x14` …
* `-0x13 … -1` → 19-entry byte index into the jump table at `0x5DC79C`; each branch pushes a client string resource id (`0x290`, `0x293`, `0x292`, `0x291`, `0x24B`, `0x24A`, `0x249`) into the message list and **returns**;
* `== 0x14` → open the UI window `L"SystemSetting_LogoutConfirm"` (`0xF2FDAC`);
* `== 0x16` → find that same window and call its vtable `+0x20C` (close);
* anything else → return.

**No branch calls `CState::RequestNext`; no branch reads or writes `[0x1093198]+0x34C`.** The vital is a dialog controller, full stop.

### 6. Every state transition in the image, and which of them a server can cause  · evidence: **byte-proof** (targets) / **structural inference** (the human names of the source contexts)

`CState::RequestNext 0x4C7320` has **exactly 18** call sites. The target class of each is derived from the constructor called just before it, and each constructor is tied to a class by *its own vtable slot 0 = that class's token getter* — again not a naming guess:

| call site | target state | constructor | context (structural inference) |
|---|---|---|---|
| `0x4323FA` | `cStateFullScreenMovie` | `0x4C3FF0` | generic "play movie" helper `0x432290` |
| `0x4B01C3` | `cStateSelectServer` | `0x4C5D40` | char-select band, reached from `LSCN_LoginVitalRes` apply |
| `0x4B4DE7` | `cStateSwitchScene` | `0x4C6560` | **start-game routine `0x4B4910`** |
| `0x4B4EB0` | `cStateSwitchScene` | `0x4C6560` | same routine, second path |
| `0x4C481A` | `StateRunTime` | `0x4C8790` | switch-scene band |
| `0x4C4D35` | `cStateLogin` | `0x4C51B0` | `cStateDisplayLogo` per-frame `0x4C4CC0` |
| `0x4C4F8F`, `0x4C4F9F` | `cStateDisplayLogo` | inline (vtable `0xF16A10`) | `cStateInitGame` per-frame `0x4C4F60` |
| `0x4C589B`, `0x4C58C0` | `cStateSelectServer` | `0x4C5D40` | login band `0x4C57A0` |
| `0x4C61FE` | `cStateCreateActor` | `0x4C03E0` | `cStateSelectServer` per-frame `0x4C60C0` |
| `0x4C70C7` | `StateRunTime` | `0x4C8790` | `cStateSwitchScene` per-frame `0x4C6E80` |
| `0x4DA407`, `0x4DB1BC`, `0x4DB27C` | `cStateLogin` | `0x4C51B0` | `LogoEventHandler` vtable `0xF2F3E8` (ESC / key `0x1B` on the intro) |
| `0x5DE3AA` | `cStateSwitchScene` | `0x4C6560` | singleton method `0x5DE000` |
| **`0x5EFD1E`** | **`cStateCreateActor`** | `0x4C03E0` | **`SelectActorVital` 0x36EF apply** |
| **`0x5F16C9`** | **`cStateSwitchScene`** | `0x4C6560` | **`TeleportVital` 0x25A2 apply** |

Only three of the eighteen live at or above `0x5D0000`, the vital/singleton band — those are the only transitions a server frame can reach.

`SelectActorVital`'s apply is worth quoting because it is the refresh mechanism:

```
0x5EFC66  mov ecx,[0x1093198] ; call 0x406C30    ; app reset -> model.Clear() (0x5DDF00)
0x5EFCAC  call 0x5DDD00                          ; refill the +0x180 collection
0x5EFCB1  mov ecx,[0x1093198]; mov edi,[ecx+0x34C]
0x5EFCC7  call [state vtable 0]                  ; live state's class token
0x5EFCCA  call 0x4C5CE0                          ; cStateSelectServer's token
0x5EFCD0  call 0x88F2B0                          ; is-a
0x5EFCE1  je  0x5EFCE9
0x5EFCE3  mov byte [edi+0x20], 5                 ; already on SelectServer: just nudge it
0x5EFCE9  push 0x770 ; call new ; call 0x4C03E0  ; otherwise BUILD a cStateCreateActor
0x5EFD1E  call 0x4C7320                          ; ...and request the transition
```

So a `SelectActorVital` received while the client is already on the character-select screen does **not** short-circuit: the `is-a cStateSelectServer` test fails, and the client constructs a *brand-new* `cStateCreateActor` and requests a transition into it. Mechanically that is a full screen rebuild from a freshly refilled collection.

### 7. Character-select → world is a client-local UI command  · evidence: **byte-proof**

`cStateCreateActor` has a 27-entry UI command table (`0x4C0120`, jump table `0x4C02DC`, keyed on `event+0x94`; nine of the twenty-seven entries write the page variable `0x107A2C0`, five of them doing nothing else). **Command 3** (`0x4C015B: 8B CE 5E E9 AD 47 FF FF`) tail-jumps to `0x4B4910`, whose only reference in the image is that jump. `0x4B4910`:

```
close L"Login_CharSelect_Panel_CharInfo"
call 0x4011A0                                  ; the model singleton
mov eax,[edi+0x718]  ; the SELECTED actor
test eax,eax / jne  ...                        ; if none: show a widget and RETURN
... otherwise build cStateFullScreenMovie / cStateSwitchScene and RequestNext
```

There is **no wait on any inbound frame**: the condition to leave the character-select screen is `cStateCreateActor+0x718 != 0`, i.e. the player has picked a slot. `StartGameReq` (0x1E87) has the **no-op** inbound apply `0x710440` (`mov al,1 ; ret 4`), as do `LoginVerifyVital`, `NotifyEnterCreateActor`, `LSCN_LoginVitalReq`, `LSCN_SelectServerReq` and `LSCN_ReloginVerifyVital` — sending any of those to the client does literally nothing.

### 8. The complete inbound vital surface of this screen  · evidence: **byte-proof**

`cStateCreateActor`'s token getter `0x4C0110` has exactly **8** call sites (`0x4E61D4`, `0x510D45`, `0x5D118B`, `0x5EFD88`, `0x5EFDDC`, `0x5EFECC`, `0x5F11AC`, `0x5F334B`). Five of them are inside a Vital apply method — and those five are the entire set of inbound frames the character-select screen reacts to:

| wire id | class (from the `.?AV…@@`-bound registrar literal) | vtable | apply | what it does to the screen |
|---|---|---|---|---|
| `0x36CF` | `CreateActorVital` | `0xF3017C` | `0x5EFD50` | appends one record (`0x5DDE10`) when `+0x14 == 1` and `+0x18` present, then calls into the state |
| `0x36DB` | `DeleteActorVital` | `0xF301A0` | `0x5EFDC0` | `0x4BAEB0` — countdown write for ops 3/4, repaint otherwise |
| `0x4323` | `StartGameFailVital` | `0xF3020C` | `0x5EFEB0` | state-gated failure path |
| `0x709E` | `ReturnSelectServerVital` | `0xF304DC` | `0x5F1190` | state-gated |
| `0x42E3` | `LSCN_LoginVitalRes` | `0xF30D64` | `0x5F3300` | state-gated (also drives `cStateLogin`/`cStateSelectServer`) |

and, one level above, the frame that *creates* the screen:

| `0x36EF` | `SelectActorVital` | `0xF30744` | `0x5EFC40` | reset + refill the list, then build a new `cStateCreateActor` |

For completeness the verifier also pins `StartGameRes` 0x1E9F (`0x5EFE10`), `LSCN_SelectServerRes` 0x5396 (`0x5F3390`), `LogoutVital` 0x1B40 (`0x5EF930`), `GetWorldInfoVital` 0x3D4B (`0x5F0B00`), `TeleportVital` 0x25A2 (`0x5F14B0`) and `CheckSecondPwdVital` 0x4B98 (`0x5F05B0`). Every id in the table is reproduced by the PF-NAMEID-HASH-001 name hash of the class-name literal the registrar thunk pushes.

---

## EFFECT ON GT-011 AND GT-013

### GT-011 — "list did not refresh"

* **Why the list stayed** — *byte-proof.* The acknowledgement's handler cannot change the list. Field `+0x14 = 1` (what v141 echoes) is outside the `{3,4}` range that touches the collection at all, and no value of `+0x14` erases a record because **no erase-by-key path exists in the image**. The handler's `0x4B90A0` / `0x4B9980` calls do repaint — from the collection that still has the character in it. So the client's behaviour was correct with respect to what we sent.
* **The tester's lead is confirmed** — *byte-proof.* A different frame **kind** is required, and the byte evidence names it: `SelectActorVital` (0x36EF), which is the only frame that resets (`0x5DDF00` via `0x406C30`) and refills (`0x5DDD00`) the collection.
* **Why field `+0x14 = 1` is not obviously "success"** — *structural inference.* The only values the handler distinguishes are 3 and 4 (write countdown) versus everything else (repaint). `+0x18` behaves as the countdown value: for ops 3/4 it is written into `record+0xF4`, and in the repaint branch `(+0x18 == 0)` is passed to `Set_DeleteBtn_Text`. That is consistent with a delayed-deletion design (mark, count down, cancel). It does **not** prove that some other `+0x14` value makes a character disappear — nothing can, without a list rebuild.
* **"Other buttons stopped responding" — partially answered.** *byte-proof:* the screen's whole per-frame behaviour is selected by the page variable `0x107A2C0` (15 pages; > 0x0E does nothing), main-screen input is gated on it being 0, the delete animation path sets it to `0x0B` at `0x4BAE91`, and `OnDeleteResult` never writes it. *Not proven:* which page value was actually live at the moment of the ack in GT-011. That is a runtime fact this static pass cannot settle; a screenshot/attended observation or a memory read of `0x107A2C0` would settle it. I did **not** find a separate "modal lock" boolean; on this evidence the page variable *is* the modal mechanism. Calling `0x107A2C0 == 0x0B` the specific cause is a **guess** until observed.

### GT-013 — "no transition"

* **Why nothing transitioned** — *byte-proof.* `LogoutVital`'s apply reaches only dialog code. Zero of the eighteen `CState::RequestNext` sites are reachable from it, and it never touches `[0x1093198]+0x34C`. There is **no inbound vital in the image that moves the client out of `StateRunTime`**: the only three network-reachable transitions are `SelectActorVital`→`cStateCreateActor`, `TeleportVital`→`cStateSwitchScene` and singleton `0x5DE000`→`cStateSwitchScene`.
* **Therefore shape 4 should not be another logout envelope** — *structural inference.* The falsification of shapes 1–3 is explained: they were all variations of "answer the logout command", and the client's logout handler has no state-changing branch to reach. If the goal is "client leaves the world", the byte evidence points at the two frames that *do* have a transition edge, not at 0x1B40.
* **Open, honestly:** I did not disassemble `SelectActorVital`'s apply for the case where the live state is `StateRunTime` beyond noting that the is-a test against `cStateSelectServer` fails and a new `cStateCreateActor` is therefore built and requested. Whether the engine tolerates that transition *from inside the world* (teardown order, scene unload) is **not proven here** and must not be assumed.

---

## WHAT IS NOT CLAIMED

1. **No runtime claim.** Nothing was executed. No GameClient was launched, no server booted, no socket opened, no database touched. Every statement above is a statement about bytes in one file.
2. **No claim about the ORIGINAL server.** It is closed and was never published; `current/pf_login_game_server_v141.py` is a read-only snapshot of prior work and is referred to as v141, never as the original server.
3. **Not proven: that re-sending `SelectActorVital` visibly refreshes the screen.** The static path is complete (reset → refill → new state → RequestNext), but "the pixels change" is a client-observable claim and needs an attended round.
4. **Not proven: which page value `0x107A2C0` held during GT-011.** See above; the mechanism is proven, the live value is not.
5. **Not proven: the semantics of `DeleteActorVital` field `+0x14`.** I proved which values branch where. The names "op", "status", "countdown" are labels; only `record+0xF4`'s use by the name-board rebuild is byte-backed, and calling it "days until deletion" would be a **guess**.
6. **Not proven: the meaning of the 32-byte opaque wstring `+0x1C`.** DELETE-SOFT-002's negative probes stand; I did not resolve `0x4E6190`'s string source this round.
7. **Not decoded: `StartGameRes` 0x1E9F apply `0x5EFE10` past its first block**, `StartGameFailVital` `0x5EFEB0`, `ReturnSelectServerVital` `0x5F1190` and `LSCN_LoginVitalRes` `0x5F3300` bodies. They are pinned by address and by state gate, not analysed. Three of the eight `0x4C0110` call sites (`0x4E61D4`, `0x510D45`, `0x5D118B`) are UI-side, not vital applies, and were not analysed either.
8. **Not verified: parity with the non-`.local` `GameClient.bin`.** Only `.local.bin` was read.

---

## PROPOSED NEXT STEPS (proposal only — I am not deciding anything)

These are options for the chief, ranked by how much they are supported by the bytes. **No ledger entry, no matrix flip and no hypothesis was opened by this report.**

1. **GT-011 follow-up — answer the delete with a `SelectActorVital` rebuild.** The byte evidence says this is the *only* mechanism that can make a character leave the client's list. v141 already has both builders (`make_runtime_select_actor_empty` / `..._preset`) and the exact wire shape is runtime-proven. Note the governance flag the chief already recorded: HYP-PF-015's stop rule currently forbids "list-refresh compositions", so this needs an owner nod first.
2. **GT-011 diagnostic — probe field `+0x14` ∈ {3,4} with a non-zero `+0x18`.** That is the only branch that writes the collection, and it should be *observable*: the name board rebuild `0x4B9980` creates a board only when `record+0xF4 > 0`. A visible countdown board would confirm the delayed-delete reading; nothing visible would falsify it. Cheap, and it does not require touching the list-refresh stop rule.
3. **GT-013 — stop designing logout envelopes.** Shapes 1–3 failed for a structural reason. If "client returns to character select" is the goal, the byte-supported candidates are (a) send `SelectActorVital` while the client is in `StateRunTime` and observe whether the engine survives the transition, or (b) accept that the client-side exit is UI-local and re-scope the test. I recommend the chief choose; I am not choosing.
4. **Cheap static follow-ups** that would raise confidence without an attended round: finish `0x5EFE10` / `0x5F3300`; identify the exact page value the delete confirm flow leaves in `0x107A2C0` by disassembling `0x4BAC40`/`0x4BED40`'s callers; resolve `0x4E6190`'s 32-byte token source.

---

## REPRODUCE

```
py -3 tools\pf_ui_state_refresh_static.py                       # 292 guards, exit 0
py -3 tools\pf_ui_state_refresh_static.py --json                # the counts block below
py -3 -m pytest tests\test_ui_state_refresh_static.py -q
```

The verifier imports only `hashlib`, `json`, `os`, `struct`, `sys`.

```json UI_REFRESH_COUNTS
{
  "character_list_add_one_callers": [
    "0x5efd76"
  ],
  "character_list_clear_callers": [
    "0x406c3a",
    "0x5de2e4",
    "0x5de994"
  ],
  "character_list_collection_offset": "+0x180",
  "character_list_erase_by_key_paths": 0,
  "character_list_fill_callers": [
    "0x5efcac"
  ],
  "character_list_singleton_global": "0x01081A90",
  "character_select_state": "cStateCreateActor",
  "character_select_state_object_size": 1904,
  "character_select_state_token": "0x0107A38C",
  "client_sha256": "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623",
  "delete_ack_handler": "0x4BAEB0",
  "delete_ack_op_our_server_sends": 1,
  "delete_ack_ops_that_touch_the_list": [
    3,
    4
  ],
  "delete_ack_vital_id": "0x36DB",
  "guards_total": 292,
  "live_state_pointer": "[0x1093198]+0x34C",
  "measured_at_head": "08fb65b",
  "page_jump_table_entries": 15,
  "page_variable": "0x0107A2C0",
  "page_variable_immediate_writes": 20,
  "plus_0x180_instructions_in_text": 32,
  "state_classes_registered": 10,
  "state_transition_sites": 18,
  "state_transition_sites_inside_a_vital_apply": 3,
  "ui_command_table_entries": 27,
  "v141_cross_check_ran": true,
  "vitals_enumerated": 18,
  "vitals_gated_on_character_select": 5,
  "vitals_gated_on_character_select_ids": [
    "0x36CF",
    "0x36DB",
    "0x42E3",
    "0x4323",
    "0x709E"
  ],
  "vitals_with_noop_inbound_apply": 6
}
```
