# PF-NAMEID-HASH-001 — the 16-bit Vital wire id is a PURE HASH of the plaintext class-name string (settles the ECHO-008 open question)

Date: 2026-08-18
Round: chief scheduled รอบ 62 (report-only, additive)
Grade claim: **static / byte-exact** — no runtime hypothesis changed, no ledger/matrix/src edit this round.
Precedent for report-only additive integration: `96b76fe`, `cec8c82`, `e1741db`.

## Question (queued by CHAT-ECHO-008, commit `cec8c82`)

Across ECHO-005/007/008 and TELEPORT-CHECK-001 the same wall recurred: every Vital's
16-bit numeric id is **never a code immediate** in the image; the id-slot in `.data`
holds filler/zero and is written at runtime by the once-init chain
`push <name>; call 0x89c080 (once-init); mov ecx,eax; call 0x89bd00 (id-assign); store ax→slot`.
CHAT-ECHO-008 correctly noted the once-init **guard** `0x89c080` is *not* a hash, and
queued the decisive next step (ECHO-008 §next 1–2):

> walk `0x89bd00`/`0x89b220` id-assign further — **falsify "id is a pure hash of the name"**;
> if instead it pulls from config/counter, the id source is outside the image and static
> binding is impossible.

This round walks that chain. **Result: the id IS a pure hash of the plaintext class name.**
The hash is not in the guard `0x89c080` (ECHO-008 was right about that) — it is one call
deeper, at `0x89b220`. The id source is therefore fully **inside** the image (name literal
in `.rdata` + hash code in `.text`); nothing external is involved.

## Findings

### 1. `0x89b220` is the hash — a position-weighted signed-char sum mod 2¹⁶

Disassembly of `0x89b220` (char* → u16), byte-exact:

```
0x89b220  push esi
0x89b221  mov  esi,[esp+8]              ; esi = name (char*)
0x89b22f  ...  strlen(esi) -> eax
0x89b24e  xor  ecx,ecx                  ; i = 0 ; dx = 0 (accumulator)
0x89b260  movsx di, byte [ecx+esi]      ; di = (signed char) name[i]     <-- SIGNED
0x89b265  lea  ebx,[ecx+1]              ; bx = i+1  (one-based index)
0x89b268  imul di, bx                   ; di = di * (i+1)   (16-bit)
0x89b26c  inc  ecx
0x89b26d  add  dx, di                   ; acc += di         (16-bit wrap)
0x89b272  jl   0x89b260
0x89b276  mov  ax, dx                   ; return acc
0x89b27a  ret  4
```

Equivalent, exact:

```
uint16 id = 0
for i in 0..len-1:  id += (int16)( (signed char)name[i] * (i+1) )   # all mod 2^16
return id & 0xFFFF
```

There is no counter, no table lookup, no config read, no external source — the return value
is a deterministic function of the name bytes alone.

### 2. `0x89bd00` (id-assign) returns that hash verbatim

`0x89bd00` receives `ecx` = the registry singleton and the name pointer, calls `0x89b220`
(`push ebx; call 0x89b220; movzx edi, ax`), registers `(name → id)` into the registry via
`0x89bb60`, and returns `ax = di` (the hash) on success. The registry is a name→id map used
for lookup/dedup; it does **not** alter the value the hash produced.

### 3. `0x89c080` is the once-init singleton guard — not a hash (confirms ECHO-008)

`0x89c080` is a textbook `_Init_thread`-style lazy singleton: `mov eax,[0x108cf90];
test eax; jne done; else malloc 0x20; construct @0x89bfc0; register atexit dtor @0x89c010;
store singleton → [0x108cf90]`. It builds the registry object once and returns it. No hashing
here — exactly as CHAT-ECHO-008 stated.

### 4. In-image name literals tie directly to wire ids (10/10 byte-exact)

A full `.text` scan finds **519** registration thunks of the shape
`push <name-literal>; call 0x89c080; mov ecx,eax; call 0x89bd00; mov word[slot], ax`.
For every Vital whose wire id is a committed constant, the pushed literal is the plaintext
class name and its `0x89b220` hash equals the wire id, and the id-slot matches prior rounds:

| in-image thunk | literal (`.rdata`) | id-slot | hash | wire id |
|---|---|---|---|---|
| `0xbee820` | `TeleportCheckVital` | `0x1082074` | `0x4477` | `0x4477` |
| `0xbee380` | `TargetPosVital` | `0x1081FE0` | `0x2A90` | `0x2A90` |
| `0xbee400` | `TeleportVital` | `0x1081FF0` | `0x25A2` | `0x25A2` |
| `0xbee7c0` | `GetWorldInfoVital` | `0x1082068` | `0x3D4B` | `0x3D4B` |
| `0xbee860` | `LogoutVital` | `0x108207C` | `0x1B40` | `0x1B40` |
| `0xbee600` | `UseItemVital` | `0x1082030` | `0x1F4F` | `0x1F4F` |
| `0xbf2b70` | `QuestOperateVital` | `0x108324C` | `0x3E34` | `0x3E34` |
| `0xbf72d0` | `Channel_LocalTalkMessageVital` | `0x1084458` | `0xAC52` | `0xAC52` |
| `0xbf8830` | `TradeCmdVital` | `0x1084AE8` | `0x23B5` | `0x23B5` |
| `0xbf8870` | `TradeZoomVital` | `0x1084AF0` | `0x2A7A` | `0x2A7A` |

The `TeleportCheckVital` row (`slot 0x1082074`) is the **exact slot** TELEPORT-CHECK-001
identified last round (commit `96b76fe`), directly corroborating that finding.

### 5. Full corpus: 13/13 committed (name, id) pairs reproduced byte-exact

Applying the recovered hash to every `(name, id)` pair committed in
`current/pf_login_game_server_v141.py` (VITAL constants + `protocol_name_id` asserts)
reproduces all 13: TeleportCheck/TargetPos/Teleport/GetWorldInfo/Logout/LocalTalk/
ItemOperate{,Req,Res}/QuestOperate/TradeCmd/TradeZoom/UseItem. Chance of 13 independent
16-bit matches ≈ 2⁻²⁰⁸.

### 6. One precise nuance: signed (client) vs unsigned (server model)

The committed server helper models this as
`sum((i+1) * ord(c) for i,c in enumerate(name)) & 0xFFFF` — **unsigned** `ord()` (0–255).
The client uses `movsx` — **signed** char (−128…127). For every all-ASCII protocol name
(all current names are ASCII identifiers) the two are byte-identical, which is why every
test and every wire id matches. They diverge only for a name byte ≥ `0x80` (e.g. `"A\x80"`:
signed vs unsigned differ). This is a harmless-today but exact sharpening of
`protocol_name_id`; the faithful algorithm is signed-char.

## Conclusion

- **CONFIRMED**: the 16-bit Vital wire id **is a pure hash of the plaintext class-name
  string** — `Σ_i (signed char)name[i]·(i+1) mod 2¹⁶`, computed at once-init and cached in a
  per-class `.data` slot. (byte-exact static: hash disassembled + 10 in-image literal→id ties
  + 13/13 corpus reproduction)
- **FALSIFIED**: the ECHO-008 alternative that the id might come from a config/counter with a
  **source outside the image**. The source is a name literal in `.rdata` plus the hash in
  `.text`; the image contains everything needed to derive every id statically.
- **CLOSES** the recurring "id runtime-assigned, source uncapturable" wall for the whole
  identity cohort (ECHO-005/007/008, TELEPORT-CHECK-001): "runtime-assigned" was only
  deferred initialization of a deterministic hash, not an opaque external source.
- **HARDENS** the server model: `protocol_name_id` is exact for ASCII names; the faithful
  algorithm is signed-char and would diverge only on a high-bit byte.

**Matrix impact:** none (report-only additive). This does not flip a coverage cell; it raises
confidence on a cohort of prior identity claims from "id runtime-assigned (source unproven)"
to "id = static, byte-exact function of the class name."

## Nonclaims

- Does not assert any behavioral/gameplay change; purely the id-derivation mechanism.
- Does not enumerate every one of the 519 thunks' ids — only the 10 whose wire ids are
  committed constants are tied; the rest are asserted to follow the same mechanism, not
  individually cross-checked to wire values.
- The signed/unsigned divergence is demonstrated on a synthetic high-bit input; no shipping
  protocol name contains a high-bit byte, so no live divergence is claimed.

## Next step / queued

- No UI test required; fully settled statically. An optional follow-up (low value) would be
  to fold the signed-char form into `protocol_name_id` as a hardening comment — deferred to a
  future src-touching round (not this report-only round).

## Evidence (read-only; see companion .manifest for sizes + SHA-256)

- `GameClient\GameClient.local.bin` — binary underlying every cited VA (`0x89b220`,
  `0x89bd00`, `0x89c080`, thunks `0xbee380…0xbf8870`), ImageBase `0x400000`
- `current/pf_login_game_server_v141.py` — committed VITAL id constants + `protocol_name_id`
  asserts (the 13 (name,id) pairs)
- `reports/PF_TELEPORT_CHECK001_0X4477_VTABLE_SCHEMA_CONFIRM_STATIC_20260818.md` — slot
  `0x1082074` cross-reference (round 61)
- `reports/PF_CHAT_ECHO008_LOCALTALK_COHORT_VTABLE_NAME_MAP_STATIC_20260818.md` — the open
  question this round settles
- `tools/pf_vital_id_hash_static.py` — verifier (22 guards, exit 0 = PASS; reproduces every
  cited VA/byte/tie from this exact binary via capstone)
