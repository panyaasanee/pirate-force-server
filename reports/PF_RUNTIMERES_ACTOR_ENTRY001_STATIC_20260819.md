# PF RUNTIMERES-ACTOR-ENTRY-001 — the chief's three-round-old note, tested: is the "RuntimeRes actor-entry pipe" really the only way to `_F_DIE_000`, what is "RuntimeRes" actually called, and what must our server send

2026-08-19 · assistant lane · **static RE, report-only, additive** · HEAD `8360f57` · binary `GameClient/GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` · reproduce: `py -3 tools/pf_runtimeres_actor_entry_static.py` (**150 guards, exit 0**), `py -3 tools/pf_runtimeres_actor_entry_static.py --json`, `py -3 -m pytest tests/test_runtimeres_actor_entry_static.py -q`

> **The answer, first, in one paragraph.** **The chief's note is correct in substance and wrong in its name — and the round-83 headline that was built next to it is wrong about the carrier.** There is no string `RuntimeRes` anywhere in the 14,759,424-byte image (0 occurrences; also 0 for `RunTimeRes` and `RuntimeProtocol`). The real class is **`GSCN_RunTimeProtocolRes`**, literal at `0xF2FFF8`, id **`0x6E9D` = 28317** — the same 28317 our own lanes have been seeing come back live as `ErrorData`, so the name-hash and the runtime observation agree. "Res" is **Response**, not Resource. Its actor-entry pipe is **derived change-mask bit `0x02`**, object **`+0x1C`**, and the inbound handler `0x5E4060` feeds that collection's list head straight into `0x446F30`. And the pipe really is the **only** way: `0x446F30` has **exactly one caller in the whole image** (`0x5E4085`, inside that handler) and **zero pointer occurrences anywhere in the file**; `0x4437C0` has exactly one caller and zero pointers; `0x472810` has exactly one caller and zero pointers; `0x472850` and `0x4765C0` (the two sites that push `L"_F_DIE_000"`) have zero direct callers and exactly one pointer each — both slots of the *same* `CActorTask_Dead` vtable `0xF0F048`. **But three things everybody assumed are false.** (1) **`UpdateAttrVital` cannot do it.** Its inbound handler `0x5F2400` contains **zero** `mov r,[reg+0x20]; call r` dispatch shapes across its entire extent, so it cannot reach `0x4446F0`, cannot latch `[actor+0x70] |= 0x200`, cannot build a `CActorTask_Dead` and cannot play the animation — HP-DEATH-001's "one `UpdateAttrVital` is the whole trigger" is **only true for the local player's `Main_Dead` window**, which is a separate per-frame read. (2) **The timer polarity is backwards for the animation.** `vtable +0x40` (`0x43BDA0`) is `HP==0 AND timer > 0` and gates the *dying* latch; `vtable +0x3C` (`0x43BD70`) is `HP==0 AND timer <= 0` and is what gates the death task at `0x443990`. A positive `+0x58` gives you the latch and **no animation**. (3) **An actor cannot be born dead.** `0x446F30` looks the entry's 64-bit identity up; *found* → vtable `+0x20` (apply **and** dead-sync); *not found* → `0x446990`, which spawns and applies through vtable `+0x10` and never touches `0x4437C0`. So the death sequence needs **at least two actor-entries for the same identity**. On our side the carrier is already built (`make_runtime_remote_actors`, 4 call sites in `src/`) and the gap is exactly **3 things**, all of them zeros today.

**Grade:** entry-point censuses · class identification · path · polarity · spawn-vs-update · type gate = **A** (byte-exact; the verifier reproduces every address, count and span hash, and five trap tests prove it can reject) · **anything about the ORIGINAL server = not claimed** · net: this closes the RuntimeRes debt carried since round 82 and **corrects two sentences in `reports/PF_HP_DEATH001_…md`** (§2's carrier claim and §7's open debt, which is now answered with a negative). No coverage row is flipped here.

---

## 0. Method, scope, and the specific mistake this round was told not to repeat

**Method.** Static analysis of the read-only client image. **No linear disassembler is used for any claim.** Every census is byte matching:

| what | how | why it cannot fail the round-83 way |
| --- | --- | --- |
| direct calls | `E8 <rel32>` scanned at **every byte offset** of **every executable section** | no decode, no alignment assumption, no early stop |
| tail jumps | `E9 <rel32>`, same sweep | catches `jmp`-thunked entries |
| **table / indirect / immediate references** | the target VA as a little-endian dword, scanned at **every byte offset of the whole 14.7 MB file** | one sweep simultaneously covers vtable slots, jump tables, `mov reg,imm32`, `FF 15` and `FF 25` — because all four store the address as a dword |
| virtual dispatch through slot `+0x20` | the byte shape `8B /r(mod=01,disp8=0x20) … FF D<r>`, optionally with the `8B /r(mod=00)` vtable-load prefix | no decode |

> 🔴 **The round-83 failure mode, named.** A linear disassembler stops at the first byte it cannot decode and then reports a confident negative for everything after it. Nothing here decodes anything. Two of the five trap tests in `tests/test_runtimeres_actor_entry_static.py` exist specifically to prove this: **trap 3** plants the dword `0x004437C0` in `.rdata` and asserts the census rejects (the "reached only through a table, so it has no `E8`" case), and **trap 4** splices a `+0x20` dispatch shape into the `UpdateAttrVital` handler and asserts the negative rejects.

> ⚠️ **A scope gap round 83 had that this round closed.** This image has **two** executable sections — `.text` (`0x401000`, `0x838C00` raw) **and `.code`** (`0xC3A000`, `0x400` raw). `tools/pf_hp_death_respawn_static.py` builds its call index over `.text` only. `.code` is small, but "small" is not "swept". It is swept here, and it contains none of the targets.

**Nothing was executed.** No server booted, no GameClient opened, no socket, no database, no capture, no scenario, no UI test, no network. `current/pf_login_game_server_v141.py` and `src/` were opened **read-only, for counting only**.

**Evidence grades, used strictly.** ① byte-proof = an instruction span, a span hash, a vtable slot or a complete census, asserted by a guard in the verifier. ② structural inference = a conclusion from ①-grade parts plus the code's shape, with the inference stated. ③ guess = **listed only, never built on**.

---

## 1. Q2 first — what "RuntimeRes" actually is, because the name was the problem

### ① byte-proof — the string does not exist

`RuntimeRes`, `RunTimeRes`, `RUNTIMERES`, `RuntimeProtocol`, `RunTimeProtocolVital`, `ActorEntryVital` — **0 occurrences each, anywhere in the file.** What exists is one Req/Res pair:

| literal | VA | id (name-hash) | vtable | sizeof | serializer | inbound |
| --- | --- | --- | --- | --- | --- | --- |
| `GSCN_RunTimeProtocolReq` | `0xF2FFE0` | **`0x6E6F`** (28271) | `0xF2FF80` | `0x1C` | `0x5F4070` | **`0x710440` = discard stub** |
| `GSCN_RunTimeProtocolRes` | `0xF2FFF8` | **`0x6E9D`** (28317) | `0xF2FFC0` | **`0x28`** | `0x5E3EE0` | **`0x5E4060` = real handler** |

Both ids reproduce from the PF-NAMEID-HASH-001 hash of the plaintext literal, re-anchored against the three constants v141 already carries (`ActorAttr 0x12AD`, `NPCAttr 0x0AD5`, `UpdateAttrVital 0x309A`). Registration thunks (`0xBEE030`, `0xBEE050`), get-id stubs (`0x5E36F0` → slot `0x1081C90`, `0x5E37C0` → slot `0x1081C94`) and the sizeof stub `0x51DF20` (`mov eax,0x28 ; ret`) are all pinned byte-for-byte.

> 🟡 **`0x6E9D` == 28317.** That is the exact `ErrorData` number `src/pirateforce_foundation/delete_actor_hypothesis.py` documents the client returning live when a `RuntimeRes` is malformed — *the class id of the envelope itself*. A hash computed from a `.rdata` literal and a number observed on a real socket agreeing is about as good a cross-check as this project gets.

### ① byte-proof — the pipe is a **derived change-mask bit**, and it is bit `0x02`

`GSCN_RunTimeProtocolRes::Serialize 0x5E3EE0` calls the inherited base `0x5F4070` first (which handles the **VitalData collection at `+0x18`** — the thing `make_runtime_vitals` builds), then writes **its own** `u8` change mask with tag `0x0B`:

| derived bit | object | sub-serializer | what the inbound handler does with it |
| --- | --- | --- | --- |
| **`0x02`** | **`+0x1C`** | `0x5E1C10` → write `0x5E01D0` / read `0x5E1AD0` | **`+0x10` (list head) → `0x446F30` — the actor reconcile** |
| `0x04` | `+0x24` | `0x5E2960` | `[+0x10]` → `[0x1093198]+0x7BC`; `[+0x14]` → `0x5F6B70`; `[+0x18]` → `[actor+0x574]` — **not decoded here** |
| `0x08` | `+0x20` | `0x5F85B0` | **not decoded here** |

The collection's own wire is `u16 count` (tag `0x12`, from `+0x2C`) followed by each entry serialising **itself** through its own vtable `+0x18` — i.e. it is polymorphic, which is exactly the shape `v141.make_runtime_remote_actors` already emits (`u8tag(0x0B,0)` inherited-absent, `u8tag(0x0B,0x02)` derived, `u16tag(0x12,count)`, entries).

**So the chief's phrase decodes to:** *`GSCN_RunTimeProtocolRes`, derived mask bit `0x02`, object `+0x1C`, the actor-entry collection.* **The nickname is fine; it is just not a class name in the binary, and "Res" means Response.** Anyone grepping the image for `RuntimeRes` will find nothing and conclude the pipe is imaginary. It is not.

---

## 2. Q1 — how many ways in are there? The complete censuses ⭐

Each row is the **whole list**, not membership. Pointer occurrences are over **every byte of the file**.

| function | role | direct `E8` | tail `E9` | dword pointers anywhere in the file |
| --- | --- | --- | --- | --- |
| `0x446F30` | actor-entry reconcile | **1** — `0x5E4085` | 0 | **0** |
| `0x4446F0` | attr-apply **+ dead-sync** weld | 1 — `0x4566A7` | 0 | **4** — `0xF0D3C0`, `0xF0DF78`, `0xF0E018`, `0xF0E0E8` |
| `0x456630` | player/net-actor bridge → `0x4446F0` | **0** | 0 | **3** — `0xF0D7C8`, `0xF0DD28`, `0xF0E690` |
| `0x4437C0` | dead-state sync | **1** — `0x444705` | 0 | **0** |
| `0x472810` | `CActorTask_Dead` ctor | **1** — `0x4439E9` | 0 | **0** |
| `0x472850` | dead-task update (plays the literal) | **0** | 0 | **1** — `0xF0F054` = task vtable `+0x0C` |
| `0x4765C0` | the *other* literal player | **0** | 0 | **1** — `0xF0F050` = task vtable `+0x08` |
| `0x5DF080` | the attr-apply loop | 3 — `0x4446FE`, `0x454949`, `0x45D24A` | 0 | 0 |
| `0x5E4060` | `GSCN_RunTimeProtocolRes` inbound | 0 | 0 | 1 — `0xF2FFDC` = its own vtable `+0x1C` |

All **7** of the `0x4446F0` / `0x456630` pointer slots are **slot `+0x20` of an actor vtable**:

| vtable | class | `+0x20` |
| --- | --- | --- |
| `0xF0D7A8` | `CMyActor` | `0x456630` |
| `0xF0DD08` | `CNetActor` | `0x456630` |
| `0xF0E670` | a `CNetActor` subclass (ctor `0x457760`; **not spawnable from the actor-entry factory**) | `0x456630` |
| `0xF0DF58` | `CNetNPC` | `0x4446F0` |
| `0xF0DFF8` | `CAvatarNPC` | `0x4446F0` |
| `0xF0E0C8` | `Pet` | `0x4446F0` |
| `0xF0D3A0` | the shared actor **base** (its `+0x10` is a `__purecall`-style import thunk) | `0x4446F0` |

**The chain, therefore:**

```
GSCN_RunTimeProtocolRes derived bit 0x02, object +0x1C
  0x5E4060  inbound            (vtable 0xF2FFC0 +0x1C)
  0x5E4073  mov eax,[esi+0x1C] ; add eax,0x10 ; push eax ; call 0x402A20
  0x5E4085  call 0x446F30                     <-- the ONLY caller, ever
    0x446F91  call 0x446170                   identity lookup (entry+0x18/+0x1C)
    0x446FB6  mov edx,[esi] ; mov eax,[edx+0x20] ; push edi ; mov ecx,esi ; call eax
      0x4446FE  call 0x5DF080                 apply the attrs
      0x444705  call 0x4437C0                 <-- the ONLY caller, ever
        0x44384C  test bl,bl -> [actor+0x70] |= 0x200      (vtable +0x40 gate)
        0x443990  cmp byte [esp+0x13],0                    (vtable +0x3C gate)
        0x4439E9  call 0x472810               <-- the ONLY caller, ever
                  vtable 0xF0F048, task id 0x80000005, 0x24 bytes
          0x472850 / 0x4765C0  (vtable +0x0C / +0x08, no direct callers)
            test byte [actor+0x70],0x40
            push 0xF0F060  ->  actor vtable +0x28  ->  L"_F_DIE_000"
```

`L"_F_DIE_000"` occurs **once** in the image (`0xF0F060`) and its address is referenced from **two** places (`0x4728AF`, `0x47670F`) — both inside the same `CActorTask_Dead` vtable, both behind the same `[actor+0x70] & 0x40` gate. So "two play sites" does not widen the entry surface at all.

### The boundary — stated, not hidden

The one link in that chain that is **not** a closed census is `actor->vtable[+0x20](entry)`. Image-wide there are **387** `mov r,[reg+0x20] … call r` shapes, of which **230** carry the `mov r,[this]` vtable-load prefix that makes them genuine virtual dispatches. **Exactly one of the 230 is proven here to hold an actor pointer: `0x446FB6`**, because its `this` comes out of `0x446170` / `0x446990` — the actor registry itself.

**What is NOT claimed:** that the other 229 cannot be actors. Static type flow was not done. What *is* ①-grade is that any such site would still have to obtain an actor pointer, and in this image the actor registry that hands them out is the one `0x446F30` owns. **Treat "229 sites unexamined" as the exact size of the hole, not as zero.** (Nyquist lesson from round 84: a negative from sampling is a claim about everything you did not look at.)

Two smaller unexamined edges, named: the `0x04`/`+0x24` and `0x08`/`+0x20` sub-objects of `GSCN_RunTimeProtocolRes` were **not decoded**, and `0x402A20` (which returns the actor manager) was **not decoded**.

---

## 3. Q3 — what the server actually has to send, and the three assumptions that were wrong

### ① byte-proof — correction 1: `UpdateAttrVital` cannot reach the death chain

`UpdateAttrVital` (id `0x309A`, inbound handler `0x5F2400`) rides the **inherited** VitalData collection at `Res+0x18`, dispatched separately at `0x5E40DE` (`call 0x5F39E0`) — a *different sub-object* from the actor-entry collection at `+0x1C`.

Across the handler's whole extent `0x5F2400..0x5F261A`:

* **0** `mov r,[reg+0x20] … call r` dispatch shapes;
* **0** direct calls to `0x4446F0`, `0x456630`, `0x4437C0` or `0x446F30`.

The span is frozen by hash, so this negative is asserted over the whole region rather than sampled.

> 🔴 **This corrects `reports/PF_HP_DEATH001_…md` §2.** Its one-paragraph answer says *"to make a character die, a server sends one `UpdateAttrVital` carrying a `BasicAttr` with mask bit `0x0004` = 0 and mask bit `0x0080` set to a positive float. That is the whole trigger."* For the **local player's `Main_Dead` window** that remains true — `0x44A540` re-reads the attribute every frame and does not need the chain. For **everything else** — the `0x200` latch, the looping-sound stop, the FX, the task cancel, `CActorTask_Dead`, `L"_F_DIE_000"`, the `TargetIsDead` panel string — it is **false**. HP-DEATH-001 §7 flagged this exact chain as untraced and asked for it to be treated as ② at best; the answer is now ①-grade and it is **no**.
>
> 🔴 **Concretely for HP-DEATH-002:** `src/pirateforce_foundation/stats_progression_hypothesis.py` ships its death frames through `legacy.make_runtime_vitals(...)` (2 call sites) and never through `make_runtime_remote_actors` (0 call sites). As built, that lane can open the local player's death window and **cannot** make anything fall over.

### ① byte-proof — correction 2: the two predicates have **opposite** timer polarity

```
0043BDA0   vtable +0x40   attr = GetAttr()
           83 78 44 00        [attr+0x44] != 0            -> false
           f3 0f 10 40 58     movss  xmm0, [attr+0x58]
           0f 2f 05 9c98f000  comiss xmm0, [0xF0989C]     ; the constant is 0.0f
           76 07              jbe                          -> false
           => HP == 0  AND  timer >  0.0f      ("dying")

0043BD70   vtable +0x3C   attr = GetAttr()
           83 78 44 00        [attr+0x44] != 0            -> false
           0f 57 c0           xorps  xmm0, xmm0           ; xmm0 = 0.0f
           0f 2f 40 58        comiss xmm0, [attr+0x58]
           72 07              jb                           -> false
           => HP == 0  AND  timer <= 0.0f      ("dead")
```

Inside `0x4437C0`: `bl` = `+0x40`, `[esp+0x13]` = `+0x3C`.
`0x44384C  84 db … 09 56 70` — **`bl` gates the `[actor+0x70] |= 0x200` dying latch.**
`0x443990  80 7c 24 13 00 … 0f 84` — **`[esp+0x13]` gates everything below it, including `0x4439E9 call 0x472810`.**

They are mutually exclusive on one snapshot. **A positive `+0x58` therefore produces the dying latch and no animation; a zero-or-absent `+0x58` with `HP == 0` produces the animation.** (`+0x58` is `f32`, mask bit `0x0080`, tag `0x2A`; a `BasicAttr` that has never carried the field holds whatever the object was constructed with, so "omit bit `0x0080` entirely" is the cheap way to get `timer <= 0`.)

### ① byte-proof — correction 3: an actor **cannot be born dead**

```
00446F87  mov ecx,[eax+0x18] ; mov eax,[eax+0x1C]   ; the entry's 64-bit identity
00446F8D  push eax ; push ecx ; mov ecx,ebp
00446F91  call 0x446170                              ; FIND in the actor registry
00446F98  test esi,esi / 75 18  jne 0x446FB4         ; FOUND  -> vtable +0x20  (UPDATE + DEAD SYNC)
00446F9C  push 1 ; push 1 ; push edi ; mov ecx,ebp
00446FA3  call 0x446990                              ; NOT FOUND -> SPAWN
00446FAC  je  0x446FC7                               ; spawn failed -> skip
00446FAE  jmp 0x446FBE                               ; spawned -> SKIP the +0x20 call entirely
```

and inside the spawn, `0x446AAD  mov eax,[esi] ; mov edx,[eax+0x10] ; push ebp ; mov ecx,esi ; call edx` — the initial attributes are applied through vtable **`+0x10`**:

| class | vtable `+0x10` | reaches the apply loop | reaches `0x4437C0` |
| --- | --- | --- | --- |
| `CNetActor` | `0x454920` | yes (`0x454949`) | **no** |
| `CMyActor` | `0x451B90` → `0x454920` at `0x451BC7` | yes | **no** |
| `CNetNPC` | `0x45D200` | yes (`0x45D24A`) | **no** |
| `CAvatarNPC` | `0x45D9F0` → `0x45D200` at `0x45D9F8` | yes | **no** |
| `Pet` | `0x45DE60` → `jmp 0x45D200` | yes | **no** |

"no" is not an inference — `0x4437C0` has exactly one caller in the image and it is `0x444705`. Both `+0x10` bodies also contain **zero** `+0x20` dispatch shapes.

**So the minimum server sequence is two frames for the same identity: one that spawns, and a later one that kills.**

### ① byte-proof — the actor-type gate is `2..6` and it is a jump table

```
004469BD  mov eax,[ebp]                    ; the entry
004469C8  movzx eax, byte [entry+0x10]     ; <-- the u8 the server writes as u8tag(0x0B, actor_type)
004469CC  add   eax, -2
004469D1  cmp   eax, 4
004469D4  ja    0x446B14                   ; OUT OF RANGE -> return NULL, entry silently dropped
004469DA  jmp   dword [eax*4 + 0x446B2C]
```

| `actor_type` | case | sizeof | ctor | vtable | class | extra gate |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | `0x4469E1` | `0x3A8` | `0x457340` | `0xF0DD08` | `CNetActor` | pool `0x444DE0` |
| 3 | `0x4469F7` | `0x488` | `0x44C990` | `0xF0D7A8` | `CMyActor` | **`[0x1032EC4] == 0`** (only if there is no local player yet) |
| 4 | `0x446A3D` | `0x368` | `0x45CC00` | `0xF0DF58` | `CNetNPC` | pool `0x444F00`, `[mgr+0x6D] == 0` |
| 5 | `0x446A5A` | `0x378` | `0x45D000` | `0xF0DFF8` | `CAvatarNPC` | pool `0x445020`, `[mgr+0x6D] == 0` |
| 6 | `0x446A77` | `0x4E8` | `0x45E4E0` | `0xF0E0C8` | `Pet` | pool `0x445140` |

This *is* the `u8tag(0x0B, actor_type)` at `v141:1258`. Value 4 = `CNetNPC` was already known; the full range and the per-type gates are new here. **All five spawnable classes carry the death slot at vtable `+0x20`**, so type is not what limits dying.

### ① byte-proof — the animation has a second gate nobody had noticed

```
00472898  80 7f 20 00     cmp byte [task+0x20], 0     ; one-shot latch
0047289C  75 1e           jne  ->  skip
0047289E  f6 46 70 40     test byte [actor+0x70], 0x40
004728A2  74 18           je   ->  skip
004728A4  ... push 0 ; push 0 ; push 0 ; push 0xF0F060 ; call actor->vtable[+0x28]
004728B8  c6 47 20 01     mov byte [task+0x20], 1
```

`[actor+0x70]` bit `0x40` is set at exactly two actor-side places, `0x4448B4` and `0x4599B4`, both on the **model-load** path (`0x444730` is actor-base vtable `+0x58` with 4 direct callers; `0x4598B0` is the `CNetActor`-side equivalent). *(A third `or dword [reg+0x70],0x40` exists at `0x46558C`, but that `+0x70` is the **`BasicAttr` change mask**, a different object — the verifier pins all three and separates them.)*

**② structural inference:** an NPC whose visual never resolved — no `NPCAttr` mask bit `0x04` / no visual-preset wstring — will latch, will get a `CActorTask_Dead`, and will still never animate. Our four `src/` actor-entry emitters all do pass a visual preset, so this is a trap for future emitters rather than a present bug.

---

## 4. Q4 — the server-side gap, in numbers

```json RUNTIMERES_COUNTS
{
  "actionable_server_gaps": 0,
  "actor_model_bit_0x40_writers": 2,
  "actor_type_jump_table_cases": 5,
  "actor_type_max": 6,
  "actor_type_min": 2,
  "actor_vtables_carrying_the_death_slot": 7,
  "binary_sha256": "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623",
  "entry_points_0x4437C0_direct": 1,
  "entry_points_0x4437C0_pointers": 0,
  "entry_points_0x4446F0_direct": 1,
  "entry_points_0x4446F0_pointers": 4,
  "entry_points_0x446F30_direct": 1,
  "entry_points_0x446F30_pointers": 0,
  "entry_points_0x456630_direct": 0,
  "entry_points_0x456630_pointers": 3,
  "entry_points_0x472810_direct": 1,
  "entry_points_0x472810_pointers": 0,
  "entry_points_0x472850_direct": 0,
  "entry_points_0x472850_pointers": 1,
  "executable_sections_swept": 2,
  "f_die_literal_occurrences": 1,
  "f_die_literal_reference_sites": 2,
  "gscn_runtime_protocol_req_id": 28271,
  "gscn_runtime_protocol_res_id": 28317,
  "gscn_runtime_protocol_res_sizeof": 40,
  "guards": 152,
  "or_0x40_on_offset_0x70_sites": 3,
  "runtimeres_literal_occurrences_in_image": 0,
  "server_call_sites_emitting_zero_current_hp": 0,
  "src_actor_entry_call_sites": 18,
  "src_actor_stream_call_sites": 27,
  "src_modules_building_actor_entries": 17,
  "src_modules_building_actor_entries_names": [
    "field_mobs.py",
    "hostile_hp_link_hypothesis.py",
    "mob_combat.py",
    "mob_death.py",
    "mob_diag_multi_object.py",
    "npc_hostile_hypothesis.py",
    "npc_hp_link_hypothesis.py",
    "population.py",
    "remote_player_hypothesis.py",
    "runtimeres_death_hypothesis.py",
    "scenario.py",
    "scene_object.py",
    "world_face_frame.py",
    "world_population.py",
    "world_population_bg0002.py",
    "world_population_bg0004.py",
    "world_population_bg0015.py"
  ],
  "src_modules_doing_both": 4,
  "src_modules_doing_both_names": [
    "hostile_hp_link_hypothesis.py",
    "mob_death.py",
    "npc_hp_link_hypothesis.py",
    "runtimeres_death_hypothesis.py"
  ],
  "src_modules_forbidding_basicattr_bit_0x0080": 1,
  "src_modules_forbidding_names": [
    "remote_player_hypothesis.py"
  ],
  "src_modules_mentioning_basicattr_bit_0x0080": 8,
  "src_modules_passing_zero_hp_by_named_constant": [
    "damage_hp_link_hypothesis.py",
    "hostile_hp_link_hypothesis.py",
    "mob_combat.py",
    "mob_death.py",
    "mob_ledger_admission.py",
    "npc_hp_link_hypothesis.py",
    "runtimeres_death_hypothesis.py"
  ],
  "src_vital_stream_call_sites": 25,
  "vt20_dispatch_shapes_image_wide": 387,
  "vt20_dispatch_shapes_in_updateattrvital_handler": 0,
  "vt20_dispatch_shapes_with_vtable_load": 230
}
```

**The good news first: the carrier already exists and is already runtime-accepted.** `v141.make_runtime_remote_actors` (derived bit `0x02`) and `v141.make_remote_actor_entry` (serializer `0x5E21D0`) are implemented, and `src/` calls them at **4** sites across **3** modules (`population.py` ×2, `scenario.py`, `scene_object.py`). Nothing new has to be invented at the envelope level.

**"If we want an NPC to die, how many things must be added?" — three. Each is a countable zero today.**

| # | what is missing | the number that proves it is missing | what it would take |
| --- | --- | --- | --- |
| **1** | **A re-send for an already-known identity.** All 4 actor-entry sites are first-sight spawns. Nothing in `src/` sends a *second* entry for an identity the client already has, which is the only branch that reaches vtable `+0x20`. | `src_actor_entry_call_sites` = 4, all spawn-shaped | one new emitter that reuses the same `actor_identity` after the spawn packet is acknowledged |
| **2** | **`current_hp = 0` on that path.** `make_npc_attr` takes `current_hp` and always sets mask bit `0x0004`, but no call site anywhere passes zero. | `server_call_sites_emitting_zero_current_hp` = **0** (checked across `src/` *and* the v141 snapshot) | one argument |
| **3** | **The death-timer field on the actor-entry path.** Bit `0x0080` (`f32 @ +0x58`, tag `0x2A`) is referenced in 2 modules — `runtime.py` and `stats_progression_hypothesis.py` — and **neither builds an actor entry**; the 3 modules that build actor entries never mention it. | `src_modules_doing_both` = **0** | for the *animation* this is the field you want **absent or ≤ 0**; for the *dying latch* you want it **> 0**. Both need the encoder to live on the entry path, not the vital path. |

> **② structural inference — the shortest credible "make an NPC fall over" recipe**, stated so a future round can either build it or disprove it:
> 1. spawn as today: `make_runtime_remote_actors([make_remote_actor_entry(4, id, [(NPC_ATTR, npc_attr_with_visual_preset), (MOVEMENT_ATTR, …)])])`;
> 2. wait until the client has it (the visual preset is what eventually sets `[actor+0x70] |= 0x40`);
> 3. send a **second** `make_runtime_remote_actors` for the **same `id`**, carrying an `NPCAttr` whose `BasicAttr` mask includes `0x0004` with `current_hp = 0` and **omits** bit `0x0080`.
>
> ①-grade underneath it: the carrier, the derived bit, the identity lookup, the `+0x20` weld, the two predicates and their polarity, the `0x40` gate. ②: that these steps in this order produce a visible corpse — that is a runtime question and this milestone does not answer it.

---

## 5. What is proven, what is supported, what is still a guess

### ① proven, byte-exact — build on these

1. `RuntimeRes` is **not a string in the image**; the class is `GSCN_RunTimeProtocolRes`, id `0x6E9D` = 28317, sizeof `0x28`, vtable `0xF2FFC0`.
2. The actor-entry pipe is **derived mask bit `0x02`, object `+0x1C`**, serialised `u16 count` + polymorphic entries.
3. `0x446F30` — **1** direct caller (`0x5E4085`), **0** pointers anywhere in the file.
4. `0x4437C0` — **1** direct caller (`0x444705`), **0** pointers. `0x472810` — **1** (`0x4439E9`), **0** pointers.
5. `0x472850` and `0x4765C0` — **0** direct callers, **1** pointer each, both slots of `CActorTask_Dead`'s own vtable `0xF0F048`.
6. `L"_F_DIE_000"` at `0xF0F060`: **1** occurrence, **2** reference sites, both in that one class, both behind `[actor+0x70] & 0x40`.
7. `0x4446F0` is **0x3D bytes**, `0x4446F0..0x44472D`, and is `call 0x5DF080` immediately followed by `call 0x4437C0`.
8. `0x5F2400..0x5F261A` (`UpdateAttrVital` inbound) contains **0** `+0x20` dispatch shapes and **0** calls into the death chain.
9. `vtable +0x40` = `HP==0 AND timer>0`; `vtable +0x3C` = `HP==0 AND timer<=0`; the latch uses the first, the task uses the second.
10. Spawn applies through vtable `+0x10`; `+0x10` never reaches `0x4437C0`.
11. Actor type gate = jump table of exactly 5 cases, `2..6`, with per-type sizes, ctors and vtables as tabulated.
12. Our side: 4 actor-entry call sites, 0 of which set bit `0x0080`; 0 call sites anywhere emit `current_hp = 0`.

### ② supported by the bytes, but not closed — reasonable to plan on, state the inference

* That `0x446FB6` is the **only** dispatcher holding an actor pointer. 229 other vtable-load `+0x20` sites were not type-resolved.
* That omitting bit `0x0080` leaves `+0x58` at `0.0f` on a freshly constructed `BasicAttr` (the constructor was not read).
* That `[actor+0x70] & 0x40` corresponds to "model loaded" (read from the two writers' surroundings, not from a symbol).
* That the two-frame spawn-then-kill sequence produces a visible corpse.

### ③ guesses — listed, built on by nothing above

* That derived bits `0x04`/`+0x24` and `0x08`/`+0x20` are scene/zone descriptors.
* That `0xF0E670`'s class is a ship or vehicle variant of `CNetActor`.
* That `[mgr+0x6D]` (the gate on types 4 and 5) is a "scene is loading" flag.

### Explicitly not examined

`0x402A20`; the `+0x24` and `+0x20` sub-objects; `0x446F30`'s second loop (`0x446FE1..0x4470E5`, the reconcile/removal pass); the 229 unresolved `+0x20` dispatch sites; the `BasicAttr` constructor; any damage model; anything at all about the ORIGINAL server, which is closed, was never published, and about which nothing here is claimed.

---

## 6. Three ways forward — pick one, chief

| | proposal | cost | risk |
| --- | --- | --- | --- |
| **A** | **Re-point HP-DEATH-002 at the actor-entry carrier.** Add one `src/` emitter that re-sends an actor entry for a known identity with `current_hp = 0` and no `0x0080`, behind the existing opt-in scenario token. Then one attended GT: spawn an NPC, kill it, watch. | ~1 module + 1 scenario + 1 GT slot. The envelope, the entry serializer and the spawn path all already exist. | **Low technically, medium politically:** it says out loud that the round-84 `runtime_pass` flip on `combat/hp_death_and_respawn` was flipped on a lane that cannot animate anything. May want the row moved back to `in_progress` first. |
| **B** | **Close the 229.** Resolve the remaining vtable-load `+0x20` dispatch sites by type, so "one way in" stops being ②-grade at its weakest link. Pure static, no server, no UI. | 1 round of static RE, no runtime, no risk to anything. | **Low value if the answer is "none of them"** — which is the likely outcome. Buys certainty, not capability. |
| **C** | **Correct HP-DEATH-001 and stop.** Amend the two wrong sentences in `reports/PF_HP_DEATH001_…md` (§2's carrier claim, §7's now-answered debt), note the correction in `STATUS.md`, and leave building for a later round. | ~30 minutes, report-only. | **Lowest cost, and it stops the wrong sentence propagating** — three rounds of notes already quote it. Does not move any capability. |

**Recommendation if one is wanted:** **C then A.** C is nearly free and the current text is actively misleading the next builder; A is the only one of the three that can produce a corpse.

---

## 7. How to reproduce

```
py -3 tools/pf_runtimeres_actor_entry_static.py            # 150 guards, exit 0
py -3 tools/pf_runtimeres_actor_entry_static.py --json     # machine-readable
py -3 -m pytest tests/test_runtimeres_actor_entry_static.py -q
```

The verifier is **pure stdlib** (`hashlib`, `json`, `os`, `re`, `struct`, `sys`) and needs no third-party package — a test asserts that. It reads the client image at `GameClient/GameClient.local.bin` (same staging fallback as the other static tools) and opens `current/pf_login_game_server_v141.py` and `src/pirateforce_foundation/` **read-only** for the gap counts. It touches no network, no database, no GameClient process, no server source and no canonical DB. The test file carries **five trap tests**; two of them (planted vtable pointer, spliced `+0x20` dispatch) exist specifically to prove the verifier can reject the failure modes round 83 was exposed to.

---

## ERRATUM 1 — round 86: the three counted zeros in §4 are no longer zero

**Appended 2026-08-19 (round 86). Nothing above this line has been rewritten
except the `RUNTIMERES_COUNTS` block, which is a live mirror of a tool run and
not a published claim** — this file's own test says in so many words that when
a count legitimately moves, the block is re-pinned in the same change. The
prose is what carries the claim, so the prose gets an erratum instead.

§4 says of the three server-side gaps: *"Each is a countable zero today."*
That sentence was true when it was written and is false now, because round 86
built `RUNTIMERES-ENCODER-001` for the express purpose of making it false. The
table stays as written; read it as the state of the source on 2026-08-19
before that lane landed. What moved:

| §4 gap | round 85 | round 86 | closed by |
| --- | --- | --- | --- |
| 1 — a re-send for an already-known identity | `src_actor_entry_call_sites` = 4, all spawn-shaped | **5**, one of them a second entry for an identity already sent | `src/pirateforce_foundation/runtimeres_death_hypothesis.py` |
| 2 — `current_hp = 0` on that path | `server_call_sites_emitting_zero_current_hp` = 0 | **still 0 by that measure** — see the warning below | same module |
| 3 — the death-timer field on the entry path | `src_modules_doing_both` = 0 | **1** | same module |

`actionable_server_gaps` therefore goes **3 → 0**. Read that zero narrowly: it
counts things missing from *our own source*. It says nothing about whether
these frames produce a corpse on a screen, which is a runtime question, is
still unanswered, and is what GT-022 exists to ask.

### 🔴 The interesting half: gap 2's guard was about to stay green while its sentence stopped being true

Round 85 proved gap 2 by searching `src/` and the v141 snapshot for the literal
`current_hp = 0` and finding none. Round 86's encoder passes exactly that zero
— through a named constant, `RUNTIMERES_DEATH_HP_ZERO = 0`. The literal search
finds nothing, so **the old guard would have gone on reporting a zero that had
stopped being true, in green, indefinitely.** A guard that keeps passing after
the thing it describes has changed is worse than one that fails, because
nothing draws a human's attention to it.

The check now also looks for the named constant, and reports which module
carries it. The general lesson, which is the same shape as round 84's sampling
lesson and round 85's hash lesson: **a negative asserted over a syntax is a
claim about a spelling, not about a behaviour.** Anything that can be
expressed a second way will eventually be expressed the second way, and the
guard will not notice.

Two further changes in the same edit, both tightenings:

- the module *names* are pinned next to the counts, because a count moving
  from 4 to 5 tells the next reader that something arrived but not what, and
  the next person to add an emitter should get a red line that names their
  own file rather than an arithmetic disagreement;
- gap 3's guard is untouched and still green: `HP-DEATH-002` still ships only
  over `make_runtime_vitals` and still never over the actor-entry carrier.
  That lane was not modified by round 86 and keeps its own separate claim.

---

## ERRATUM 2 — round 90: one count in the mirror block moved, and it is not one of this file's own

**Appended 2026-08-19 (round 90). Nothing above this line has been rewritten
except `RUNTIMERES_COUNTS`, which is a live mirror of a tool run and is
re-pinned in the same change that moves it, exactly as ERRATUM 1 describes.**

`src_vital_stream_call_sites` moved **13 -> 14**. The fourteenth site is
`src/pirateforce_foundation/damage_model_hypothesis.py`, which ships
`CHitResult` `0x16F7` over `make_runtime_vitals` for `DAMAGE-ENCODER-001`
(`HYP-PF-024`).

**What did NOT move, and why that is the interesting half:** every actor-entry
count in this file is unchanged — `src_actor_entry_call_sites` 5,
`src_actor_stream_call_sites` 5, `src_modules_building_actor_entries` 4,
`src_modules_doing_both` 1. The damage lane rides the **BASE** change mask
(the VitalData collection at object `+0x18`); this file is about the
**DERIVED** change mask (the actor-entry collection at `+0x1C`). They share a
bit number and nothing else: different mask byte, different reader, different
element shape. A reader who takes the matching `0x02` for a shared carrier
will get this wrong, and two rounds already did; `drafts/DAMAGE_MODEL_UNKNOWNS_R90_STATIC.md`
section 1 pins both side by side.

No claim in this report changes. No guard was loosened: the census guard is
re-pinned at 14 rather than widened to a range, for the same reason ERRATUM 1
gives.

---

## ERRATUM 3 — round 96: a SECOND src/ module now builds actor entries, and the "both" census learned to tell SET from FORBID

**Appended 2026-08-20 (round 96). Nothing above this line has been rewritten
except `RUNTIMERES_COUNTS`, which is a live mirror of a tool run and is
re-pinned in the same change that moves it, exactly as ERRATUM 1 describes.**

`REMOTE-PLAYER-ENCODER-001` (`HYP-PF-025`, multiplayer chunk 2) added
`src/pirateforce_foundation/remote_player_hypothesis.py`, the first `src/`
module to compose `actor_type 2` (`CNetActor`) actor-entry frames. It builds
actor entries and it sends the carrier, so four of this file's `src/` counts
moved together: `src_actor_entry_call_sites` **5 -> 6**,
`src_actor_stream_call_sites` **5 -> 6**,
`src_modules_building_actor_entries` **4 -> 5** (the new name sorts in as the
second entry), and the count of modules that *mention* bit `0x0080` **3 -> 4**.

**The load-bearing half is what did NOT move.** `src_modules_doing_both` is
still **1** and still names only `runtimeres_death_hypothesis.py`, because
GAP 1 was always about which module *SETS* the death timer, and the new lane
never does: it names bit `0x0080` exactly once, as
`BASIC_BIT_DEATH_TIMER_FORBIDDEN`, and every use of that constant is a
fail-closed guard that refuses the bit. Round 96 made the "both" measure
precise rather than a substring match — a module SETS `0x0080` only if it
builds an entry, mentions the bit, and does **not** carry the `FORBIDDEN`
marker — so the count stays exactly one and stays the death lane. A new
mirror key, `src_modules_forbidding_basicattr_bit_0x0080` = **1**
(`remote_player_hypothesis.py`), records the second actor-entry builder as
what it is: a visibility probe that forbids the death bit, not a second death
emitter. The COUNTS key that used to be named
`src_modules_setting_basicattr_bit_0x0080` is renamed to
`src_modules_mentioning_basicattr_bit_0x0080`, because a substring count was
only ever a count of mentions; the SET claim lives in `src_modules_doing_both`
and in the new GAP-1 guard, which now says "SETS" in as many words.

No claim in this report changes. No guard was loosened: every moved count is
re-pinned to its new exact value with the new module named beside it, and one
guard was ADDED (the forbid census), which is why `guards` moved **151 -> 152**.

## NOTE — round 97 (2026-08-20): two live-mirror counts move for DAMAGE-HP-LINK-001

`src_vital_stream_call_sites` moves **14 -> 15** and
`src_modules_mentioning_basicattr_bit_0x0080` moves **4 -> 5**, because
`damage_hp_link_hypothesis.py` (HYP-PF-026, the hit -> bleed -> die link lane)
ships both of its carriers through ONE `make_runtime_vitals` seam and names bit
`0x0080` for its two lethal frames — the same death-timer field, byte-identical
to the HYP-PF-022 composer's output, gated behind the lane's own pinned lethal
steps. The new module builds **no actor entries**, so `src_actor_entry_call_sites`,
`src_actor_stream_call_sites`, `src_modules_doing_both` (the SET census) and the
forbid census are all untouched: the death-chain claims of this report do not
move. This is a NOTE rather than an erratum because no published sentence was
wrong — the two moved numbers live in the `RUNTIMERES_COUNTS` block, which is a
live mirror of a tool run and is expected to move when we write code; both are
re-pinned in the tool with the new module named beside the count, and the
`guards` total stays **152** (two values re-pinned, no guard added or removed).

## NOTE — round 99 (2026-08-20): three live-mirror counts move for NPC-HOSTILE-001

`src_actor_entry_call_sites` moves **6 -> 7**, `src_actor_stream_call_sites`
moves **6 -> 7**, and `src_modules_building_actor_entries` moves **5 -> 6**,
because `npc_hostile_hypothesis.py` (HYP-PF-027, the mob-aggro Door A
hostile-presentation lane) spawns the SAME frozen NPC `0x2001` this report's
death lane kills — the identical HYP-PF-023 SPAWN body plus exactly a
five-byte BasicAttr faction splice (bit `0x0400`, u32 value 6, our
composition per SCENE-005).

Note the THIRD category this creates alongside the round-96 SET/FORBID
split: the new module builds an actor entry and **never names the
death-timer bit at all**. Its walker requires the BasicAttr mask to equal
`0x070C` exactly, which forbids every other bit *structurally* rather than
by name, so `src_modules_mentioning_basicattr_bit_0x0080` stays **5**, the
SET census stays exactly the death lane, and the forbid census stays exactly
the visibility probe. All three timer censuses staying put is the design
working, not an omission. This is a NOTE rather than an erratum because no
published sentence was wrong — the moved numbers live in the
`RUNTIMERES_COUNTS` block, a live mirror of a tool run that is expected to
move when we write code; all three are re-pinned in the tool with the new
module named beside the count, and the `guards` total stays **152** (three
values re-pinned, no guard added or removed).

## NOTE - round 170 (2026-08-25): six live-mirror counts move, and the census that was RED said nothing about the image

The bridge runner working `RE-071` ran `py -3 tools/pf_runtimeres_actor_entry_static.py --json` and
got **exit 1** while reporting that every binary control still matched, `0x446F30` included. That is
exactly what a stale section-[5] census looks like from the outside, and it is worth naming as a
failure mode: **a red line here can mean "we wrote code" and nothing whatever about the client
image**, so a reader who takes the exit code as an image verdict is misled. The counts are re-pinned
to the state of `src/` at this commit, deliberately and upward, never loosened.

| count | was | now | which lane moved it |
|---|---|---|---|
| `src_actor_entry_call_sites` | 8 | **9** | HYP-PF-038 `hostile_hp_link_hypothesis.py` |
| `src_actor_stream_call_sites` | 8 | **11** | HYP-PF-038 (1) + HYP-PF-032 `ground_loot_hypothesis.py` (2) |
| `src_vital_stream_call_sites` | 17 | **20** | HYP-PF-033 `learn_skill_result_hypothesis.py`, HYP-PF-035 `skill_attr_hypothesis.py`, HYP-PF-038 |
| `src_modules_building_actor_entries` | 7 | **8** | HYP-PF-038 |
| `src_modules_mentioning_basicattr_bit_0x0080` | 6 | **7** | HYP-PF-038 |
| `src_modules_doing_both` (SET) | 2 | **3** | HYP-PF-038 |

Two things the table does not say and this note must:

**`ground_loot_hypothesis.py` holds two carrier sites and ZERO actor-entry sites.** It rides
`make_runtime_remote_actors` without ever building an entry, which is why the actor-stream count
moves by three while the entry count moves by one, and why the module censuses do not name it.

**The third SET member is not a timer emitter at all, and this census over-reports it on purpose.**
`hostile_hp_link_hypothesis.py` binds `BASIC_BIT_DEATH_TIMER = 0x0080`, but no path in that module
ORs the bit into an emitted mask: `_compose_npc_attr` raises when handed a timer, its `basic_mask`
literal omits `0x0080`, and the remaining mention is a decoder guard that refuses the bit. The module
states this itself - *"Bit 0x0080 above is named only so that every guard in this file can REFUSE
it"*. That is exactly what `remote_player_hypothesis.py` does, except that one binds the value to a
FORBIDDEN-named constant and therefore lands in the FORBID census; the discriminator keys on the
constant NAME, so this lane lands under SET instead. **This is the mirror image of the round-111
artefact** - there a real SET lane was filed under FORBID, here a FORBID lane is filed under SET.

It is re-pinned rather than repaired by narrowing the discriminator, because narrowing is how a real
emitter goes quiet: this census must be wrong in the direction that over-reports. The clean repair
belongs to whoever owns that module - rename its constant with a FORBIDDEN marker and it classifies
itself. Until then the guard's SENTENCE is looser than its count, which this report says out loud
rather than leaving for a reader to trip over: **"which modules emit a death timer today" is a
question about the composers, not about this number.**

An earlier draft of this note claimed the composer "can emit the bit". That was read off a stale
docstring rather than the body, and it is wrong; it is corrected here in the same commit that
introduced it.

This is a NOTE rather than an erratum because no published sentence was wrong - the six moved numbers
live in the `RUNTIMERES_COUNTS` block, a live mirror of a tool run that is expected to move when we
write code. All six are re-pinned in the tool with the lane named beside the count, and the `guards`
total stays **152** (six values re-pinned, no guard added or removed).

**Round h1utu5 (lane A), `src_actor_entry_call_sites` 17 -> 18, `src_actor_stream_call_sites`
26 -> 27, `src_modules_building_actor_entries` 16 -> 17.** `world_population_bg0004.py`, the
Bg0004 (Slave Market Island) census composer - BUILD-002 door 1, `COO-DECISION
2026-08-30T14:41+07:00` - builds one entry and sends one carrier, the same shape
`world_population_bg0002.py` and `world_population_bg0015.py` added before it. Not wired to any
player-visible path yet (nothing under `src/` imports it - the module's own test pins that as a
tripwire), so this is a `src/`-only move; no runtime behavior changed for this round. This is a
NOTE rather than an erratum for the same reason as the note above: no published sentence in this
report was wrong, the three moved numbers live in `RUNTIMERES_COUNTS`, and the `guards` total
stays **152** (three values re-pinned, no guard added or removed).
