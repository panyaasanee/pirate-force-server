# DAMAGE-MODEL-001 — what the client expects from the server about a hit

Date: 2026-08-19 (round 83, scheduled)
Milestone: `DAMAGE-MODEL-001` · lane `combat/damage_and_hit_result`
Status: **report-only.** No `src/` change, no scenario, no encoder, no ledger entry, no matrix flip.
Verifier: `tools/pf_damage_hit_result_static.py` (**235/235 guards PASS**, exit 0)
Tests: `tests/test_damage_hit_result_static.py` (56 passed, 92 subtests)
Sole binary evidence: read-only `GameClient.local.bin`,
SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` (re-checked unchanged after every run).

---

## Claim (grade A static, client-side only)

The client's entire expectation about the outcome of an attack is **a tagged wire record that it
displays verbatim**. It carries no damage formula, applies no scaling, and never mutates HP itself.
Every number the player sees about a hit is a number the server put on the wire.

**NOT CLAIMED: anything whatsoever about the ORIGINAL server.** No runtime capture, no wire
observation, no persistence claim. This is the client's *expectation*, byte-exact, and nothing else.
The lane stays **blocked** — this report exists to answer *whether it can be unblocked and with what*,
not to unblock it.

---

## 1. The answer to "what does the client expect"

The wire is a **self-describing tagged stream**: every field is one tag byte followed by its payload.
On read the client compares the tag byte and **sets an error flag on mismatch** (`0x89A5BF` compare,
`0x89A5C9` flag store) — so the server must emit the exact tag bytes, not merely the right widths.

Tag map (independently confirmed against our own server source, which already uses it):

| tag | type | width |
|---|---|---|
| `0x0B` | u8 | 1 |
| `0x12` | u16 | 2 |
| `0x14` | u32 | 4 |
| `0x2A` | f32 | 4 |
| `0x32` | qword | 8 |
| `0x0F` | i16 (sign-extended on read) | 2 |

Codec: `0x89A600` = WRITE(tag, ptr, size), `0x89A640` = READ twin, both `__thiscall` with `ecx` = stream.
`0x5F3490`/`0x5F34D0` = Vector3 = three `0x2A` f32.

### `CHitResult` — Vital ID `0x16F7`
vtable `0xF48AA0` · ctor `0x74F940` · serializer `0x750040` · inbound handler `0x750770`

**Header** (emitted by `0x750040`):

| # | offset | tag | type | emit VA |
|---|---|---|---|---|
| 1 | +0x18 | `0x32` | qword — performer identity | `0x750059` |
| 2 | +0x20 | `0x12` | u16 | `0x750068` |
| 3 | +0x22 | `0x12` | u16 | `0x750077` |
| 4 | +0x24 | `0x14` | u32 — the local player's own resource delta, displayed verbatim | `0x750086` |
| 5 | +0x28 | `0x0B` | u8 | `0x750095` |
| 6 | +0x2C | — | hit-entry array via `0x74F5A0` | `0x75009F` |

**Hit-entry array** (`0x74F5A0` write / `0x74FF60` read): count = u16 tag `0x12` (`0x74F5C8`),
**element stride 32** (`sar eax,5` at `0x74F5B3`).

| offset | tag | meaning | emit VA |
|---|---|---|---|
| +0x00 | `0x32` | qword — target identity | `0x74F62C` |
| +0x08 | `0x14` | **i32, read SIGNED — this is the damage number the player sees** | `0x74F63E` |
| +0x0C | 3×`0x2A` | Vector3 f32 — position | `0x74F645` |
| +0x18 | `0x2A` | f32 — **a yaw angle, not damage** (feeds the knockdown/falling spawner) | `0x74F657` |
| +0x1C | `0x12` | u16 — **result-flags bitfield** | `0x74F666` |

`CMissileHitResult` (`0x3EE5`, vtable `0xF48AC4`, serializer `0x750110`, handler `0x750EC0`) reuses the
**same** hit-entry array at its `+0x40`.

---

## 2. The headline: the client computes nothing

- **The on-screen number is element `+0x08`, verbatim.** Path: `0x750D90` → `0x43FDE0`
  (argument picked up at `0x43FF11`) → `0x43FBB0` → stored to the number widget at `0xA7C046`.
  The **only** arithmetic applied anywhere on that path is `abs()` —
  `cdq ; xor eax,edx ; sub eax,edx` at `0xA7EBFF..0xA7EC02` — then `sprintf` with `"%d"` at `0xF14A94`.
  No scale, no round, no multiply, no clamp. **A negative worth as much as any positive.**
- **The sign is the semantics.** Element `+0x08` is compared signed (`jge`) at four sites
  (`0x750919`, `0x7509E0` in the `CHitResult` handler; `0x751219`, `0x7512E0` in the missile twin) —
  negative takes the damage-reaction path. The magnitude is then shown through `abs()`.
- **The client never subtracts damage from HP.** The `CHitResult` handler contains **zero** memory
  operands at any of the seven `BasicAttr` HP/MP/timer displacements; the attribute apply loop
  `0x464436..0x4644E0` is a **mask-gated verbatim `mov` copy** with add/sub-into-`+0x44`/`+0x48`
  asserted absent. HP moves only because the server said so.
- **The 19 derived-stat accessors** (`0x467E90..0x468E30`, each `base*const + equipBonus + tableCol`
  out of the `STANDARD_STATUS` table at `0xF152AC`) are **UI-only**: all 45 call sites are in the
  tooltip/panel blocks, none in a combat handler. The client can *show* you your attack rating; it
  never *uses* it.

⇒ **The client is a pure display of server-sent numbers.** There is no formula to recover from it,
because there is no formula in it.

---

## 3. Result flags — element `+0x1C`

Control flow is byte-exact; the *names* are inference from the artwork and effects each bit selects.

| bit | selects | anchor |
|---|---|---|
| 0 | gates the whole apply block | `0x7511EB`, `0x7512D6` |
| 1 | block (`bm_block.tga`, `S_H_BLOCK.fxs`) | `0x7511EF`, `0x75137D` |
| 3 | gates the reaction block | `0x75131C` (`0x750A18` twin) |
| 4 | knockback — plays `_F_KNOCKED_002` (`0xF48B4C`) | `0x751324`/`0x751333` |
| 5 / 6 | HP / MP readout colouring | `test al,0x60` @ `0x751204` |
| 9 | special/critical (orange digits) | via `0x43FDE0` flag→texture map |
| 10 | overkill | via `0x43FDE0` flag→texture map |

`bit0 clear && damage == 0` = **miss**.

🔶 **Bounded unknown:** nothing in the image *labels* these bits. The gating is proven; the names
bit1=block / bit9=crit / bit10=overkill are read off the textures and effect names they select, which
is strong but is not a label. One attended capture would settle it.

---

## 4. Bonus: the dying/rescue debt, closed statically

Driven by the owner's eyewitness account this same night (provenance `owner_testimony` — used only to
decide where to look; the binary decided everything below).

- **`DURATION_DYING` = 20, seconds, counting down.** Config global `0x102249C`, registered `0x483475`,
  sole reader `0x44A572`. **This closes the debt where round 81 picked `60.0f` as a placeholder
  because the deployed value was unknown.** Caveat: 20 is the *image default*; `0x482640` permits an
  external config override.
- **Downed ≠ dead, and both are client derivations.** `IsDying` (vtable +0x40, `0x454AC0`) =
  `HP==0 && timer>0`; `IsDead` (vtable +0x3C, `0x454A70`) = `HP==0 && timer<=0` (`comiss` `0x454A7D`).
  The server sends only two fields — HP at `BasicAttr+0x44` and the dying timer at `+0x58` — and the
  client derives the entire downed → dead → revive sequence from them.
- **The round cross button the owner saw is `L"Main_Dead"`** (`0xF0D738`, opened at `0x44A5A1`),
  a **one-control window** whose only child is `L"BUTTON_DIE"` (`0xF1F5CC`); clicking it sends
  `ActionVital` action id `0xEA7C` (`0x518493`). It is force-closed the moment `IsDying()` goes false.
- **The revive-at-town screen is a different window**, `L"Common_Death"` (`0xF0D860`), opened from
  `CMyActor::Update` at `0x44E5C7` after `IsDead()` at `0x44E594`.
- **The help request never goes on the wire.** Going down latches `[actor+0x70] |= 0x200` and emits a
  **local chat line** (`0x4438E1`); no Vital is sent. The "being rescued" flag `actor+0x10` bit `0x80`
  is mirrored from the motion state each frame (`0x4437F1..0x44380D`) — whole-image scan finds no
  other writer.
- `ReliveVital 0x1AD4` = `{i8 mode @+0x14, u8 @+0x18}`, inbound slot = shared no-op `0x710440`
  (request-only). Three producers: `0x4E4731` (mode 1, revive in place, needs item `0x12D`),
  `0x4E4AE4` and `0x4E4B84` (mode 0, town respawn).

---

## 5. Evidence ceiling

**Proven (grade A static):** the tagged wire format and tag map; `CHitResult` and `CMissileHitResult`
identity, vtable, ctor, serializer and handler; the complete header and hit-entry field tables
including stride; the signed read of `+0x08`; the verbatim abs-only display path; the absence of any
damage arithmetic or client-side HP mutation in the hit path; the dying/downed/revive machinery and
`DURATION_DYING = 20`.

**Not proven:** semantic names for the `+0x1C` bits; header fields 2, 3 and 5; what value the original
server actually placed in any field; hit/miss/critical *rules*; range, cooldown or authority; AI, loot
or skills. **Nothing here proves what the original server sent** — only what this client will accept
and how it will render it.

---

## 6. What this means for the blocked lane — decision for Panya

The question the lane was blocked on was *"what were the real damage numbers?"*. The binary answers a
different and, for our purposes, better-scoped question: **the client imposes no damage semantics at
all.** It accepts a signed integer per target and draws it.

So the negative result the mailbox note anticipated has arrived, but in an unusually clean form:

> **There is no damage formula in the client to recover — not because we failed to find it, but
> because the client is a renderer. The original server's numbers are unrecoverable from this
> artifact by any amount of further static work.**

That closes route 2 (recover the real numbers from the client) **as a matter of fact, not of effort**,
and it means route 3 (find new evidence) is closed too — the original server is gone and SCENE-013
already proved the corpus has zero eligible server→client frames.

**What is now unblocked, and is a much smaller ask than it was this morning:** we know the exact
bytes the client will accept, so a damage model of our own design would be **client-acceptance
testable end to end** the same way HYP-PF-021/022 were. The design space is one signed i32 plus a
flag word per target.

🔴 **Per the mailbox note's explicit instruction, the chief does not start route 1.**
Panya's decision is requested on: *do we design our own damage model, and within what scope?*
