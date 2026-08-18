# PF MP-AUDIT-FOLLOWUP-001 — what the client does with `actor_type`, byte by byte

Round 78 (2026-08-18) · assistant lane · **static RE, report-only, additive** · HEAD `f286945` · reproduce: `py -3 tools/pf_actor_type_dispatch_static.py` (111 guards, exit 0), `py -3 tools/pf_actor_type_dispatch_static.py --json`, `py -3 -m pytest tests/test_actor_type_dispatch_static.py -q`

Follow-up to `PF_MULTIPLAYER_READINESS_AUDIT001_SINGLE_PLAYER_ASSUMPTIONS_20260818.md`. That audit graded the *world-visibility* axis **D** and named one and only one reason: the byte `u8tag(0x0B, actor_type)` at `current/pf_login_game_server_v141.py:1258` — the field that separates a remote **player** from a remote **NPC** — had *zero* evidence. It also predicted the question was answerable from the client binary alone, with one client, no transport work, no second player. **That prediction is confirmed. The byte is now enumerated.**

> **One-paragraph answer.** The client knows **exactly five** `actor_type` values — **2, 3, 4, 5, 6** — and it knows them through a five-entry jump table at `0x446B2C` reached from `movzx eax, byte ptr [entry+0x10]; add eax,-2; cmp eax,4; ja default` in the actor factory `0x446990`. **0, 1 and everything ≥ 7 return NULL and build no actor at all.** The five branches build `CNetActor` (2), `CMyActor` (3), `CNetNPC` (4), `CAvatarNPC` (5) and `Pet` (6), each identified by its object size tied to a `.?AV<name>@@` descriptor in its own class registrar, not by inference. **`CNetActor` (actor_type 2) is the remote-player branch**, and the proof is structural and byte-exact: the type-node registrar `0x88F2E0` records `CMyActor` — the local player — as a **child of `CNetActor`**, while `CNetNPC` is a *sibling* under `CActorBaseClient`, never an ancestor. Our server has only ever emitted `4`. The expensive discovery is not the byte itself: **every `Attr` binds to an actor through a class-gated thunk at its vtable +0x38, and `NPCAttr` gates on `CNetNPC` while `ActorAttr` gates on `CNetActor`.** An `NPCAttr` inside an `actor_type 2` entry is parsed, then silently dropped; an `ActorAttr` inside an `actor_type 4` entry is parsed, then silently dropped. So flipping the byte from 4 to 2 without also swapping `NPCAttr → ActorAttr` produces an actor with **no bound attr at all**, and the over-head name board returns immediately (`je 0x5BD8C7`) when the bound attr is NULL. The visibility axis should move **D → B**: the byte is proven and the required-companion field is proven; what is still missing is a *runtime observation* that the composed entry renders, and the appearance source (`AvatarAttr`) is replay-only.

---

## 0. Method, scope, and what this is not

**Method.** Static disassembly of the read-only client image `GameClient/GameClient.local.bin` (SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`), cross-checked against read-only server sources. Every numeric claim below is re-derived by `tools/pf_actor_type_dispatch_static.py`, which asserts **111 guards** — instruction-level matches, span SHA-256 pins, name-hash reproductions and source counts — and exits nonzero if any one drifts.

**Nothing was executed.** No server booted, no GameClient opened, no socket created, no database touched, no scenario run, no UI test.

**Evidence grades used in this document, and used strictly.**

| grade | meaning |
| --- | --- |
| **① byte-proof** | an instruction, a vtable slot, a jump-table entry, a span hash or a literal, reproduced by a guard in the verifier. Buildable on. |
| **② structural inference** | a conclusion drawn from ①-grade facts plus the code's own shape (a class hierarchy edge, a gate that cannot pass). Reasonable to build on with the inference stated. |
| **③ guess** | not derived from the binary. **Listed only, never built on.** |

**This is not.** Not a claim about the original server — it is closed, was never published, and everything here derives from the client. Not a runtime observation. Not a claim that any specific attr composition *renders*. Not permission to emit a remote player. No `src/` file, matrix row, ledger entry, scenario or hypothesis was touched.

---

## 1. Question 1 — how many `actor_type` values does the client know, and what does each build?

### ① byte-proof — the dispatch

The only consumer of the byte is the actor factory `0x446990`:

```
004469BD  mov   eax, [ebp]                     ; ebp -> pointer to the parsed actor-entry record
004469C0  test  eax, eax  / je default
004469C8  movzx eax, byte ptr [eax + 0x10]     ; <- the wire byte, actor_type
004469CC  add   eax, -2
004469CF  xor   esi, esi                       ; the NULL that the default branch returns
004469D1  cmp   eax, 4
004469D4  ja    0x446B14                       ; -> mov eax, esi ; ret 0xC  = no actor
004469DA  jmp   dword ptr [eax*4 + 0x446B2C]   ; five-entry jump table
```

The jump table at `0x446B2C` holds exactly five dwords. Span `0x446990..0x446B2C` is pinned by SHA-256 `5F68239F…697D`; the table itself by `B50C1D1D…D606`.

| `actor_type` | branch | class | object size | allocator | ctor | vtable | size↔name registrar |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **2** | `0x4469E1` | **`CNetActor`** | `0x3A8` | pool `0x444DE0` | `0x457340` | `0xF0DD08` | `0x405BD9` → `.?AVCNetActor@@` |
| **3** | `0x4469F7` | **`CMyActor`** | `0x488` | `operator new 0x88D020` | `0x44C990` | `0xF0D7A8` | `0x405C69` → `.?AVCMyActor@@` |
| **4** | `0x446A3D` | **`CNetNPC`** | `0x368` | pool `0x444F00` | `0x45CC00` | `0xF0DF58` | `0x40BA39` → `.?AVCNetNPC@@` |
| **5** | `0x446A5A` | **`CAvatarNPC`** | `0x378` | pool `0x445020` | `0x45D000` | `0xF0DFF8` | `0x40BAC9` → `.?AVCAvatarNPC@@` |
| **6** | `0x446A77` | **`Pet`** | `0x4E8` | pool `0x445140` | `0x45E4E0` | `0xF0E0C8` | `0x413259` → `.?AVPet@@` |
| `0`, `1`, ≥ `7` | `0x446B14` | — | — | — | — | — | **returns NULL; no actor is created** |

The class *names* are not inferred from the branch order. Each per-class registrar thunk writes the same object size into its class-info record (`mov dword ptr [edi+0x0C], <size>`) a few bytes after `mov ecx, <RTTI descriptor>`, and that descriptor is the `.?AV<name>@@` string. Size and name are welded together in one function; the factory's allocation size then selects the row.

Two branches carry a real extra precondition:

- **`actor_type 3` is refused unless the local-player global `0x1032EC4` is zero** — `cmp dword ptr [0x1032EC4], esi` (with `esi = 0`), `jne` → NULL. The client will build at most one `CMyActor`.
- **`actor_type 4` and `5` are refused when the factory flag byte `[this+0x6D]` is non-zero.** `2`, `3` and `6` have no such gate.

### ① byte-proof — the byte is one wire byte at record `+0x10`

The setter is unambiguous:

```
005DEC00  mov al, byte ptr [esp + 4]
005DEC04  mov byte ptr [ecx + 0x10], al
005DEC07  ret 4
```

and the record serializer `0x5E21D0` is direction-agnostic exactly like `MovementAttr`'s codec (MOVE-PROJECT-001). Outbound (`test bl,bl` false) it emits `u8(tag 0x0B)` from `+0x10`, `qword(tag 0x32)` identity from `+0x18`, `u8(tag 0x0B)` attr count, then per attr `u16(tag 0x12)` id followed by that Attr's `Serial` (vtable +0x34). Inbound (`je 0x5E2301`) it decodes the same three fields through the inbound codec `0x89A640` into the same offsets. **The byte the server writes is the byte the factory switches on.**

### ① byte-proof — the byte reaches this factory from the RuntimeRes actor stream

`0x5E4060` (the `GSCN_RunTimeProtocolRes` handler) takes the derived `+0x1C` actor-stream collection — the same field MOVE-PROJECT-001 documented — and calls `0x446F30`. `0x446F30` reads the entry identity from record `+0x18/+0x1C`, looks it up (`0x446170`), takes the **update** path (actor vtable `+0x20`) when the identity is known, and calls the **factory `0x446990`** when it is not.

### What our server emits today

| source | fact |
| --- | --- |
| `current/pf_login_game_server_v141.py` | **19** `make_remote_actor_entry` call sites with a literal first argument; **all 19 pass `4`** |
| `src/pirateforce_foundation/population.py:23` | `NPC_STYLE_ACTOR_TYPE = 4`, used at two call sites |
| `src/pirateforce_foundation/scene_object.py:34` | `make_remote_actor_entry(4, …)` hardcoded |

**Of the five values the client understands, our project has ever emitted exactly one.** Values **2, 3, 5, 6 have never been on our wire.**

---

## 2. Question 2 — which branch builds a *remote player*?

### ① byte-proof — the class hierarchy

The type-node registrar `0x88F2E0` is called once per class with `ecx = <own token>` and the parent token pushed. Six edges, each pinned:

```
CActorBase          0x102D00C
  └─ CActorBaseClient  0x102CE88
       ├─ CNetActor       0x102CB2C     <- actor_type 2
       │    ├─ CMyActor      0x102CB04  <- actor_type 3  (THE LOCAL PLAYER)
       │    └─ CViewActor    0x1032758
       └─ CNetNPC         0x102D954     <- actor_type 4  (what we emit today)
            └─ CAvatarNPC    0x102D92C  <- actor_type 5
```

### ② structural inference — therefore `actor_type 2` is the remote-player branch

`CMyActor` **is** the local player: it is what `actor_type 3` builds, it is singleton-gated on the local-player global `0x1032EC4`, and `CSkillAttr` — the skill-book attribute — binds *only* to it. `CMyActor` derives from `CNetActor`. `CNetNPC` is a **sibling** of `CNetActor`, not an ancestor, so no NPC class is ever `is-a CNetActor`.

The inference, stated plainly so it can be checked: *the class the client uses for the local human player is a specialisation of `CNetActor`; the branch that builds a plain `CNetActor` is therefore the branch for a human-shaped actor that is not me — a remote player.* This is grade ② and not ①, because nothing in the image labels branch 2 with the word "player". What **is** grade ① is everything the inference rests on: the parent edge `CMyActor → CNetActor`, the sibling position of `CNetNPC`, and the per-attr gating in §3, which makes the same split from the other direction.

`CViewActor` (also a `CNetActor` child, size `0x3B0`, factory `0x4631A0`) is **not** reachable from this jump table — it is built elsewhere. `Pet` (6) is a summoned-pet actor, `CAvatarNPC` (5) an NPC that additionally accepts `AvatarAttr`.

---

## 3. Question 3 — what else must ride along before the client will render a remote actor?

This is the finding that changes the shape of the work, and it was not visible from the server source at all.

### ① byte-proof — every `Attr` binds to an actor through a **class-gated** thunk

`CNetActor::init` (vtable `+0x10` = `0x454920`) does three things: it copies the entry identity into `actor+0x78/+0x7C`, it calls `0x5DF080`, and then it builds the name board. `0x5DF080` walks the record's Attr vector and, for each attr, calls that attr's **vtable slot `+0x38`**. Every `+0x38` has the identical shape — an `is-a` check `0x88F2B0` against **one** class token, and *silent no-op* when it fails:

| Attr | wire id (name-hash) | vtable | `+0x38` thunk | accepts only | binds into |
| --- | --- | --- | --- | --- | --- |
| **`ActorAttr`** | `0x12AD` | `0xF0E7A0` | `0x469760` | **`CNetActor`** (so 2, 3, and `CViewActor`) | `actor+0x348` |
| **`NPCAttr`** | `0x0AD5` | `0xF0E7E0` | `0x4697B0` | **`CNetNPC`** (so 4, 5) | `actor+0x358` |
| **`MovementAttr`** | `0x2067` | `0xF0D0F8` | `0x469800` | `CActorBaseClient` — **all five** | `actor+0x244` |
| **`AvatarAttr`** | `0x16A0` | `0xF0E088` | `0x469850` | `CNetActor` **or** `CAvatarNPC` | actor vtable `+0x80` |
| **`CSkillAttr`** | `0x1661` | `0xF48B78` | `0x4698B0` | **`CMyActor` only** | `actor+0x3E8` |
| **`BasicAttr`** | `0x1244` | `0xF0E760` | `0x73D360` | — | **`ret 4`, binds nothing** |

All six ids are reproduced from their name literals by PF-NAMEID-HASH-001 (`u16 id = Σᵢ (int16)((signed char)name[i] · (i+1))`), which is the same derivation that already produced `ActorAttr 0x12AD`, `NPCAttr 0x0AD5` and `MovementAttr 0x2067` as committed constants. Each id-slot is written by exactly one registration site and read by exactly one get-id stub, and that stub is the class's vtable `+0x10`.

`BasicAttr` binding nothing is not an omission: `ActorAttr` and `NPCAttr` both *derive* from `BasicAttr`, so the `BasicAttr` fields ride inside whichever of the two is sent. There is no standalone `BasicAttr` on an actor.

### ① byte-proof — the consequence

**`NPCAttr` inside an `actor_type 2` entry is parsed and then dropped. `ActorAttr` inside an `actor_type 4` entry is parsed and then dropped.** Neither produces an error, a log line, or a visible failure; the gate simply falls through.

So the required-vs-optional table for a **remote player actor** (`actor_type 2`) reads:

| field | status | why (①) |
| --- | --- | --- |
| `actor_type = 2` | **required** | any other value builds a different class or no actor |
| identity qword at record `+0x18` | **required** | `CNetActor::init` copies it to `actor+0x78/+0x7C`; the stream apply loop keys its lookup on it |
| **`ActorAttr` (0x12AD)** | **required in practice** | it is the only attr that binds to `actor+0x348`, and `actor+0x348` is what `vtable +0x74` returns — with it NULL the name board returns immediately (`je 0x5BD8C7`) and `GetName` returns the empty literal `0xF0930C` |
| `BasicAttr` name bit `0x0001` (wstring at `+0x28`) | **required for a visible label** | `LABEL_NAME` is fed exactly that wstring |
| `MovementAttr` (0x2067) | **optional to construct, required to place** | it gates on `CActorBaseClient`, so it binds to every actor_type; without it the actor has no projected position |
| `AvatarAttr` (0x16A0) | **appearance** | binds only via `CNetActor`/`CAvatarNPC`; `CNetActor` vtable `+0x80` = `0x459F50` merges it into `actor+0x34C`, which `CNetActor::init` then reads (byte `+0x5D`) to compute the actor scale at `actor+0x12C` |
| `NPCAttr` (0x0AD5) | **must NOT be sent** | it cannot bind to a `CNetActor`; sending it is a silent no-op |
| `CSkillAttr` (0x1661) | **must not be sent** | `CMyActor` only |

### ② structural inference — the minimum viable remote-player entry

An `actor_type 2` entry carrying **`ActorAttr` + `MovementAttr`** is the structural analogue of the `actor_type 4` entry the server already emits (`NPCAttr` + `MovementAttr`) and that OBJECT-POP-002 runtime-proved. Every substitution in that sentence is ①-grade; what is ② is the expectation that the analogue behaves analogously, because **no capture of an `actor_type 2` entry exists** and none can be obtained from the corpus (§7).

---

## 4. Question 4 — where does the label over a remote actor's head come from?

### ① byte-proof — the attr accessor pair

```
CNetActor / CMyActor           vtable +0x74 = 0x44C630   mov eax,[ecx+0x348] ; ret
CNetNPC / CAvatarNPC / Pet     vtable +0x74 = 0x45CD20   mov eax,[ecx+0x358] ; ret
CNetActor / CMyActor           vtable +0x78 = 0x4549E0   -> [+0x348] then wstring +0x28
CNetNPC / CAvatarNPC / Pet     vtable +0x78 = 0x45BB40   -> [+0x358] then wstring +0x28
```

Both `GetName` variants fall back to the literal `0xF0930C`, which is the **empty wide string**. An actor whose attr never bound has an empty name, not a missing one.

### ① byte-proof — the board itself

`CNetActor::init` calls vtable `+0x7C`. For `CNetActor` that is `0x456580`, which allocates **`0x78`** bytes — the registered `NameBoardPlayer` size (`0x40B6D9`, descriptor `.?AVNameBoardPlayer@@`) — stores it at `actor+0x254`, loads the template `L"board01"` (`0xF0DABC`) and sets `actor+0x258 = 1`. For `CNetNPC` it is `0x45C560`, which allocates **`0xC0`** — the registered `NameBoardNPC` size. **The two actor families get two different boards.**

`NameBoardPlayer` binds its child widgets by name at `0x5BE080`:

| board offset | widget literal |
| --- | --- |
| `+0x50` | `L"HPBAR"` (`0xF2CFC8`) |
| `+0x54` | `L"LABEL_NAME"` (`0xF0C794`) |
| `+0x58` | `L"LABEL_NICKNAME"` (`0xF2CD88`) |
| `+0x5C` | `L"LABEL_GUILD"` (`0xF2CDA8`) |

The board update `0x5BD320`:

```
005BD372  mov ecx, [esi + 0x30]     ; the owner actor
005BD377  mov edx, [eax + 0x74]     ; owner vtable +0x74  = the bound attr
005BD37A  call edx
005BD380  test eax, eax
005BD382  je   0x5BD8C7             ; NO ATTR -> the whole update returns
...
005BD4C9  call 0x43B9B0             ; dynamic_cast<ActorAttr*> (token 0x1033484)
005BD4DA  lea  edi, [eax + 0x164]   ; ActorAttr +0x164 wstring
005BD4D5  mov  ecx, [esi + 0x5c]    ; -> the LABEL_GUILD slot
...
005BD624  mov  edi, [esp + 0x14]    ; the attr from vt+0x74
005BD628  add  edi, 0x28            ; attr +0x28 wstring
005BD633  mov  ecx, [esi + 0x54]    ; -> LABEL_NAME
```

So there are **two** name-bearing text slots, and they read two different fields:

- **`LABEL_NAME` (board `+0x54`) ← `attr+0x28`.** That is the `BasicAttr` name field: `BasicAttr::Serial 0x4656F0` emits a `u16` mask (tag `0x12`) at `+0x70` and, on bit `0x0001`, the wstring at `+0x28`. This is the field the server's `NPCAttr` already fills for every Port Royal NPC, and it works identically for `ActorAttr` because `ActorAttr` derives from `BasicAttr`.
- **`LABEL_GUILD` (board `+0x5C`) ← `ActorAttr+0x164`,** reached **only** after `0x43B9B0` succeeds in downcasting the attr to `ActorAttr`. This is the field CHARACTER-NAME-001/002 already pinned and runtime-proved for the local player; this milestone does not re-prove it and only records the mechanical fact that the slot is unreachable for any `CNetNPC`-family actor.

### The audit's "account name is on the wire but never read" — corrected scope

That statement (audit §1.2 I04 / §4 G8) is about `LSCN_LoginVitalReq 0x42BF` at the **LOGIN stage**. **Nothing in the actor render path reads it.** The label over an actor's head is fed from the Attr bound to that actor, never from the login record. The two are unrelated, and G8 is untouched by this milestone: it remains an unrun experiment about the login frame, not about visibility.

---

## 5. The three levels, collected

### ① byte-proof — safe to build on

1. `actor_type` is a `u8` at actor-entry record `+0x10`, written by `0x5DEC00`, serialized/deserialized by `0x5E21D0`/`0x5E2301`.
2. The client understands exactly five values, **2–6**; `0`, `1` and ≥ `7` build no actor.
3. `2 → CNetActor`, `3 → CMyActor`, `4 → CNetNPC`, `5 → CAvatarNPC`, `6 → Pet`, each with its size welded to its `.?AV<name>@@` descriptor.
4. `CMyActor` derives from `CNetActor`; `CNetNPC` is a sibling of `CNetActor` under `CActorBaseClient`.
5. `actor_type 3` requires the local-player global `0x1032EC4` to be zero; `4` and `5` require the factory flag `[this+0x6D] == 0`.
6. `ActorAttr` binds only to `CNetActor`; `NPCAttr` binds only to `CNetNPC`; `MovementAttr` binds to all; `AvatarAttr` to `CNetActor`/`CAvatarNPC`; `CSkillAttr` to `CMyActor`; `BasicAttr`'s bind is `ret 4`.
7. A mismatched Attr is dropped **silently**.
8. `GetName` reads `attr+0x28`; the board update aborts when the bound attr is NULL; `LABEL_NAME ← attr+0x28`, `LABEL_GUILD ← ActorAttr+0x164`.
9. The board classes differ by actor family: `NameBoardPlayer` (`0x78`) vs `NameBoardNPC` (`0xC0`).
10. The byte reaches the factory from the `GSCN_RunTimeProtocolRes` derived `+0x1C` actor stream via `0x5E4060 → 0x446F30 → 0x446990`.
11. v141 has 19 literal `make_remote_actor_entry` call sites, all `4`.

### ② structural inference — reasonable, stated as inference

1. `actor_type 2` (`CNetActor`) is the remote-human-player branch. Rests on facts 4 and 6.
2. The minimum viable remote-player entry is `actor_type 2` + `ActorAttr` (with `BasicAttr` name bit `0x0001`) + `MovementAttr`, the exact analogue of the proven NPC entry.
3. `actor_type 6` (`Pet`) is a summoned-pet actor and `5` (`CAvatarNPC`) an NPC that also accepts `AvatarAttr` — from the class names and the `AvatarAttr` gate, not from any consumer.
4. The `[this+0x6D]` gate on `4`/`5` is an NPC-suppression switch on the actor manager. Its *meaning* is inferred; only its existence is ①.

### ③ guess — listed, built on by nothing

1. That an `actor_type 2` entry actually **renders** a visible human figure. Nothing here shows a draw call succeeding.
2. Which `ActorAttr` mask bits are *mandatory* rather than merely accepted for a remote actor. The mask is 64-bit with 43 gated fields; this milestone enumerated the **binding**, not a required subset.
3. Whether a remote player needs `AvatarAttr` to appear at all, or falls back to a default model. `CNetActor::init` tolerates `actor+0x34C == NULL` (it uses a default scale from `0x10222F8`), but "does not crash" is not "is visible".
4. What the original server put in an `actor_type 2` entry. Unknowable — the server is gone and was never published.
5. Interest management, update cadence, interpolation, and every other two-session question (audit G3/G4/G5/G7). Untouched here.

---

## 6. What this changes for the audit — and the grade

### The audit's own arithmetic, updated

Audit §4 listed **G1** (*the `actor_type` value for a human player*) as the first of nine "must guess" items and stated it was "statically answerable today … no second client required". **G1 is now answered, ①-grade.** Audit §4.2 listed **F8** (`ActorAttr 0x12AD`) as *partial* — "never observed inside a remote-actor entry, so whether a remote player carries `ActorAttr`, `NPCAttr`, or both is open". **That question is now closed by construction**: a remote player carries `ActorAttr` and *cannot* carry `NPCAttr`, because the bind gate makes `NPCAttr` a no-op on a `CNetActor`. **G2** (attr composition) is narrowed from open to a bounded list.

Frame table delta: `18` frames were `7 anchored / 2 partial / 9 guess`. This milestone moves **G1 → anchored** and **F8 → anchored**, and narrows **G2**. That reads **9 anchored / 1 partial / 8 guess** — but see §7 before treating that as a licence.

### Proposed grade for the world-visibility axis: **D → B**

**Why it should move.** The audit's stated blocker was singular and explicit: *"the one byte that distinguishes a remote player from a remote NPC is the single field in the whole projection path with no evidence at all"*, and *"shipping a candidate value makes [B] a D-grade compositional hypothesis"*. That byte now has 111 reproducible guards behind it. Emitting `actor_type = 2` is no longer putting a guessed value on the wire; it is emitting the value the client's own jump table names. The same is true of the companion field the audit did **not** know it needed: `ActorAttr` instead of `NPCAttr` is now ①-grade, and had this milestone not run, a "just flip the byte" change would have shipped an actor with **no attr bound and an empty name board** and looked like the byte was wrong.

**Why it should not move past B.** Three reasons, each concrete:

1. **No runtime observation exists.** Every fact here is what the client's code *would* do. `remote_player_movement_projection` was moved to `in_progress` by MOVE-PROJECT-001 on the same basis; nothing here earns `runtime_pass`.
2. **Appearance is replay-only.** `AvatarAttr` binds through `CNetActor` vtable `+0x80`, but `character_management/appearance_and_avatar_binding` still records *"No field-level appearance model exists"*. We can replay a persisted `avatar_wire`; we cannot compose one.
3. **`ActorAttr`'s required subset is not enumerated.** 43 gated fields behind a 64-bit mask; we know the container binds, not which bits an actor needs.

**Grade A is out of reach from static work alone** and would require a one-client probe that observes a rendered remote actor.

### The remaining missing bytes, concretely

| # | still missing | grade today | what would close it |
| --- | --- | --- | --- |
| M1 | proof that an `actor_type 2` entry **renders** | ③ | one attended one-client probe emitting `2 + ActorAttr + MovementAttr` under a strict opt-in scenario |
| M2 | the mandatory `ActorAttr` mask subset for a remote actor | ③ | a static enumeration of `ActorAttr::Serial 0x466230` + the `0x469760`→`0x464F30` merge, or the same probe by bisection |
| M3 | whether `AvatarAttr` is needed for visibility, and what a composed one looks like | ③ | replay of a persisted `characters.avatar_wire` on a remote actor; composition needs the appearance lane |
| M4 | the meaning of the `[this+0x6D]` gate on `actor_type 4/5` | ② | find its writer; it does not affect `actor_type 2` |
| M5 | interest management, push cadence, interpolation, whisper/party routing | ③ (audit G3/G4/G5/G7) | two live sessions — i.e. the transport package |
| M6 | `LSCN_LoginVitalReq 0x42BF` account-field roles | audit G8, unchanged | one attended login with a different username |

**M1–M3 are all one-client questions.** None of them needs the transport work. The audit's correction #2 — that visibility is not blocked by transport — survives this milestone intact and is now better supported than when it was written.

---

## 7. What this milestone could not answer

Stated plainly, because a silent gap is worse than a named one.

1. **Whether anything renders.** No client was opened. Every statement is about code paths, not pixels.
2. **Which `ActorAttr` fields a remote actor requires.** The bind is proven; the field-level requirement is not, and guessing a mask is exactly the D-grade move this milestone exists to avoid.
3. **Whether `actor_type 2` was ever used by the original server.** The original is closed and was never published. There is no ground truth and there never will be. If we emit `2`, that is *our* design choice validated against *the client*, and it must be labelled that way.
4. **Whether `Pet` (6) or `CAvatarNPC` (5) are reachable from a server-side stream in practice.** The jump table accepts them; no other precondition was traced.
5. **The `[this+0x6D]` flag's writer.** Not traced. It gates `4`/`5` only, so it does not affect the remote-player path, and chasing it was out of scope.
6. **Anything about a second connection.** Untouched. `session_lifecycle/concurrent_multi_client` remains blocked behind HYP-PF-011's recorded preconditions, and this milestone neither relaxes nor re-verifies them.

---

## 8. Reproduce

```
py -3 tools/pf_actor_type_dispatch_static.py            # 111 guards, dispatch table, exit 0
py -3 tools/pf_actor_type_dispatch_static.py --json     # machine-readable counts
py -3 -m pytest tests/test_actor_type_dispatch_static.py -q
```

The test parses the `DISPATCH_COUNTS` block below out of this file and compares it to a live run of the verifier, so no number here can drift away from the binary. Every number is compared exactly.

```json DISPATCH_COUNTS
{
  "actor_type_branch_count": 5,
  "actor_type_branches_with_extra_gate": 3,
  "actor_type_classes": {
    "2": "CNetActor",
    "3": "CMyActor",
    "4": "CNetNPC",
    "5": "CAvatarNPC",
    "6": "Pet"
  },
  "actor_type_max": 6,
  "actor_type_min": 2,
  "actor_type_object_sizes": {
    "2": 936,
    "3": 1160,
    "4": 872,
    "5": 888,
    "6": 1256
  },
  "actor_types_never_emitted_by_us": [
    2,
    3,
    5,
    6
  ],
  "attr_bind_thunks_class_gated": 5,
  "attr_bind_thunks_examined": 6,
  "attr_bind_thunks_noop": 1,
  "class_hierarchy_edges_proven": 6,
  "client_sha256": "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623",
  "guards_total": 111,
  "local_player_actor_type": 3,
  "measured_at_head": "f286945",
  "nameboard_widget_slots_proven": 4,
  "nameid_hash_ids_reproduced": 6,
  "remote_player_actor_type": 2,
  "server_emitted_actor_type": 4,
  "v141_literal_actor_types": [
    4
  ],
  "v141_remote_actor_entry_callsites": 19
}
```

## 9. Evidence manifest

See `PF_MPAUDIT_FOLLOWUP001_ACTOR_TYPE_DISPATCH_STATIC_20260818.manifest` (paths relative to the `Pirate Force` root).

## 10. Nonclaims

1. No claim that a remote player should be emitted, or that any milestone is approved. This is input to a decision that has not been made.
2. No claim about the ORIGINAL server. It is closed, was never published, and every fact here derives from the client binary. Any future `actor_type 2` emission is **our** design validated against the client, not a recovered behaviour.
3. No claim that an `actor_type 2` entry renders, is visible, animates, or is targetable. Nothing was executed.
4. No claim about which `ActorAttr` mask bits are mandatory. The bind is proven; the field-level requirement is not.
5. No claim that `AvatarAttr` can be composed. It can be replayed; the appearance lane's own note stands.
6. No claim about interest management, update cadence, interpolation, PvP, or any two-session behaviour.
7. No claim that `character_management/appearance_and_avatar_binding`, `movement/remote_player_movement_projection`, `session_lifecycle/concurrent_multi_client` or any other coverage row may move. **No matrix row, ledger entry, hypothesis, scenario or `src/` file was changed by this milestone.**
8. The proposed **D → B** grade in §6 is a **proposal to the chief and the project owner**, not a flip. Nothing in `docs/` was edited.
9. `ActorAttr+0x164` is cited, not re-proved: it belongs to CHARACTER-NAME-001/002. This milestone adds only that the slot is reachable exclusively through the `ActorAttr` downcast.
10. The audit's G8 (`LSCN_LoginVitalReq 0x42BF` account field) is unchanged and unrelated to the actor render path.
