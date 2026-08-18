# PF MP-OPT1-B — `LSCN_LoginVitalReq` 0x42BF decoded statically: the account field is a variable, and we can compute it

**Milestone:** MP-OPT1-B (Option 1 "answer the byte first", part **(b)**)
**Question answered:** MULTIPLAYER-READINESS-AUDIT-001 **G8**
**Date:** 2026-08-19 · **Measured at HEAD:** `dd1a66c`
**Kind:** report-only static RE. No `src/` change, no matrix flip, no ledger entry, no scenario, no new hypothesis, no runtime claim, no network, no GameClient launch, no database access.
**Verifier:** `tools/pf_login_vital_req_static.py` — **126 guards, 0 failed, exit 0**
**Client image:** `GameClient/GameClient.local.bin`, sha256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`

---

## 0. The one-line answer

> **The account field is real, it is a variable, and it has always been `decode_hex(the client's `-acc` argument)`.**
> Every archived capture shows `48 04 00 00 00 0E 00 00 00` not because the field is a constant, but because this project has only ever launched the client with `-acc test`, and the client hex-decodes that argument: `hexval('t')=0, hexval('e')=0xE → U+000E`; `hexval('s')=0, hexval('t')=0 → U+0000`.

That is a **byte-exact static** answer, reproduced from the binary by a verifier, not an inference from the corpus. What remains for a live test is only the client-observable half: whether a login with a different account still completes on our server (§7, GT draft).

---

## 1. Why this milestone existed

MULTIPLAYER-READINESS-AUDIT-001 (round 77) graded the multiplayer axis and listed nine wire facts a real multiplayer server would have to guess. **G8** was:

> `LSCN_LoginVitalReq` (`0x42BF`) account and credential field roles — the bytes exist in every archived capture and the tool reproduces them byte-exact — but the value never varies (`"test"`). **Decodable with one attended run** that types a different username. Not a guess; an unrun experiment.

Panya approved **Option 1** — remove the guesses before writing code. Part **(a)** (enumerate `actor_type` → class dispatch) landed in round 78 as `reports/PF_MPAUDIT_FOLLOWUP001_ACTOR_TYPE_DISPATCH_STATIC_20260818.md`. This is part **(b)**.

The audit's framing turned out to be **too pessimistic in one direction and too optimistic in another**:

* too pessimistic — the field roles did **not** need a run at all. They are fully determined by the client image.
* too optimistic — "type a different username" is not quite what a tester does here. Because of the hex decoder found in §5, typing `-acc bob` does **not** put `L"bob"` on the wire. The GT draft in §7 says exactly what to type.

---

## 2. The class, pinned to its own identity

| fact | evidence |
|---|---|
| literal `LSCN_LoginVitalReq` | `0xF0B084` |
| wire id `0x42BF` | round-62 name hash of that literal; registration thunk `0xBEFDF0` stores it into slot `0x1082344` in the exact PF-NAMEID shape (`push lit; call 0x89C080; mov ecx,eax; call 0x89BD00; mov word [0x1082344],ax; ret`) |
| id accessor | `0x4C5120` = `mov ax, word ptr [0x1082344]; ret` — one of only **two** `.text` sites that touch the slot, the other being the thunk |
| class token | `0x1082338`, registered by `0xBEFE90` against RTTI descriptor `.?AVLSCN_LoginVitalReq@@`, parent `.?AVVitalData@@` |
| vtable | `0xF16B34` (`+0x00` returns that same class token, which is what proves the vtable belongs to this class) |
| object size | `0x4C`, from the prototype registrar `0x5F2E60` (`push 0x4C; call new; call 0x4C5090`) |

Vtable, all nine slots:

```
+0x00  0x4C5110 -> jmp 0x5F2770   class-token accessor -> 0x1082338
+0x04  0x4C5400                   scalar deleting destructor (pool return)
+0x08  0x401B20
+0x0C  0x5ECAF0
+0x10  0x4C5120                   GetProtocolID -> 0x42BF
+0x14  0x4C5900                   Clone (pooled, head 0x107A498)
+0x18  0x5F2780                   Serial            <-- the frame
+0x1C  0x710440                   inbound slot = the shared no-op
+0x20  0x710440                   inbound slot = the shared no-op
```

`0xF16B58` is the **next** vtable, installed by a different constructor; its class token `0x107A5AC` resolves to `.?AVcStateLogin@@`, parent `.?AVCState@@`. That neighbour is the login **state machine**, and it is the producer in §4. Keeping the two apart matters: `0x4C5AE0` opens a login dialog, and it belongs to `cStateLogin`, not to the packet class.

**Both `+0x1C` and `+0x20` are the project's already-known no-op `0x710440`.** The client only ever *sends* this class; it has no inbound handler for it.

---

## 3. The frame: exactly two fields, nothing else

`Serial` = `0x5F2780`, 0x45 bytes, direction-agnostic:

```
0x5F2780  cmp  byte ptr [esp+8], 0
0x5F278D  je   0x5F27AA                    ; 0 = read, non-zero = write
; ---- write ----------------------------------------------------------
0x5F278F  lea  eax, [esi+0x14]  ; push ; call 0x89A810     (tag 0x48, UTF-16)
0x5F279A  add  esi, 0x30        ; push ; call 0x89A6D0     (tag 0x44, ANSI)
0x5F27A7  ret  8
; ---- read -----------------------------------------------------------
0x5F27AA  lea  ecx, [esi+0x14]  ; push ; call 0x89A880     (tag 0x48, UTF-16)
0x5F27B5  add  esi, 0x30        ; push ; call 0x89A740     (tag 0x44, ANSI)
0x5F27C2  ret  8
```

The verifier asserts that `Serial` makes **exactly four calls**, and that they are exactly those four codec helpers, and that the only object offsets it touches are `0x14` and `0x30`. There is no third field, no mask, no version byte inside the body.

The codec helpers pin the encoding themselves — no assumption is made about what "tag 0x48" means:

| helper | direction | tag | length prefix |
|---|---|---|---|
| `0x89A810` | out | `0x48` | `u32` = `2 * wstring::length()` (IAT `0xC3B464`), then UTF-16LE bytes |
| `0x89A6D0` | out | `0x44` | `u32` = `string::length()` (IAT `0xC3B470`), then raw bytes |
| `0x89A880` | in | `0x48` | inbound twin |
| `0x89A740` | in | `0x44` | inbound twin |

The two members are typed by their **MSVCP90 imports**, not by shape:

```
this+0x14   std::wstring   ctor IAT 0xC3B478 = ??0?$basic_string@_WU?$char_traits@_W...
this+0x30   std::string    ctor IAT 0xC3B458 = ??0?$basic_string@DU?$char_traits@D...
```

So the complete body of `0x42BF`, in wire order, is:

```
48 <u32 byte-length> <UTF-16LE account>    44 <u32 byte-length> <ANSI password>
```

and the golden nested block every archived capture carries is

```
12 BF 42 | 0B 00 | 48 04 00 00 00 0E 00 00 00 | 44 04 00 00 00 74 65 73 74
   id      version    field 1 = account            field 2 = password
```

---

## 4. Which field is which, and where the values come from

`cStateLogin::DoLogin` = **`0x4C5920`**, signature `(account_wstring*, password_wstring*)`. It has exactly two callers (asserted): the state-entry hook `0x4C5B2F` and the login dialog's OK handler `0x4D9769`.

The fill sequence at `0x4C5A3D..0x4C5A79`:

```
call 0x4011A0                 ; app singleton
push edi                      ; the ACCOUNT wstring
lea  ecx, [eax+0xE4]
call wstring::operator=       ; app.account = account         (identity binding #1)

push 0 ; push "file" ; mov ecx, 0x107A498
call 0x4C5690                 ; pool-allocate an LSCN_LoginVitalReq -> esi

push edi                      ; the ACCOUNT wstring
lea  ecx, [esi+0x14]
call wstring::operator=       ; req.field@+0x14 = account      <-- ACCOUNT
lea  eax, [esp+0x4C]          ; the narrowed password
push eax
lea  ecx, [esi+0x30]
call string::operator=        ; req.field@+0x30 = password     <-- PASSWORD

push esi ; call 0x4011A0 ; call 0x5DD890     ; send it
push edi ; mov ecx, 0x107A590 ; call wstring::operator=  ; g_LastAccount   (identity binding #2)
```

### 4.1 The password is plaintext

`0x88E200(out, pwd)` is `wstring::c_str()` (IAT `0xC3B484`) fed to `0x88E090`, whose one worker is **`WideCharToMultiByte`** (IAT `0xC3B0EC`). There is no hash, no salt, no cipher anywhere on that path. **The `-pwd` value reaches the wire verbatim as ANSI.** That is why the golden field 2 is literally `t e s t`.

The UI path prepends a constant before the password — but that constant is `0xF0DA12`, which is the **empty string**, so the UI path produces the same bytes.

### 4.2 The two sources of both values

**(A) command line.** WinMain `0x40AE70` reads the process command line through `GetCommandLineW` (IAT `0xC3B208`) and the option parser `0xB00B20`, for `L"-acc"` (`0xF0A12C`) and `L"-pwd"` (`0xF0A120`). The block at `0x40B00D..0x40B06E` is a **nested** test: `-pwd` is only consulted if `-acc` was found, and only if **both** are present does it

```
mov byte ptr [0x102C5AC], 1      ; the "we have command-line credentials" flag
0x102C5B0 = the -acc value       ; std::wstring
0x102C5CC = the -pwd value       ; std::wstring
```

**(B) the login dialog.** `cStateLogin`'s state-entry hook (its vtable `0xF16B58` slot `+0x10` = `0x4C5AE0`) branches on that flag:

* flag set → `DoLogin(0x102C5B0, 0x102C5CC)` immediately, **no dialog at all**;
* flag clear → open `L"Prototype_Login1"`, whose OK handler `0x4D9630` calls the same `DoLogin` with `GetText` of widget `+0x14` (account) then widget `+0x18` (password). The auto-fill `0x4D9990` pushes the same two globals into the same two widgets, which independently corroborates which widget is which.

**Neither source is a constant.** The field is a variable in both paths. That, and not the corpus, is the answer to G8.

### 4.3 What else the account is bound to

| binding | where |
|---|---|
| app singleton `+0xE4` | set **before** the request is sent, `0x4C5A43` |
| global `0x107A590` ("last account") | set **after** the request is sent, `0x4C5A87`; read back through `c_str()` by `0x4C8E70`; **cleared** (IAT `0xC3B2C8`) by the login-response handler `0x4C57A0` when the response is not the success value |
| `LoginVerifyVital` on the GAME listener | the *same decoded account wstring* is the first field of the frame the client sends to port 10189 — see §6 |
| `L"SaveLastLoginName"` (`0xF16C04`) | a literal in the same state's UI path — recorded, **not** traced |

---

## 5. The hex decoder — why nobody could read the field before

On the **command-line path only**, `DoLogin` first rewrites the account:

```
0x4C59A7  cmp byte ptr [0x102C5AC], 0
0x4C59AD  jne 0x4C5A13
0x4C5A13  lea edx,[local] ; push edi(account) ; push edx ; call 0x89B070
0x4C5A22  mov ecx, edi    ; call wstring::operator=     ; account = f(account)
```

`0x89B070` is called from **exactly one place in the whole image** (asserted) and it is a **hex decoder**:

```
size == 0                 -> L""                      (empty-wide literal 0xF0930C)
size odd                  -> substr(0, size-1)        (IAT 0xC3B46C)
for i = 0, 2, 4, ...
    wchar = (hexval(s[i]) << 4) + hexval(s[i+1])      (0x89B194..0x89B1C9)
    result += wchar                                   (IAT 0xC3B2B4, operator+=(wchar_t))
```

`hexval` = `0x89ACC0`: bias `c - 0x30`, bound `0x36`, 0x37-byte map at `0x89AD7C`, 17-entry jump table at `0x89AD38`. **The verifier rebuilds that table out of the image** (every jump-table target is a constant return, recovered by disassembling it) and then proves the reconstruction is exactly hexadecimal across **all 65536** character values, with `0` for everything else — 0 mismatches.

Consequence for `-acc test`:

```
't' -> 0x74; 0x74-0x30 = 0x44 > 0x36  -> 0
'e' -> 0x65; 0x65-0x30 = 0x35, map[0x35]=14, jt[14] -> 0xE
      wchar = (0 << 4) + 0xE = 0x000E
's' -> 0 ; 't' -> 0
      wchar = 0x0000

account wstring = U+000E U+0000  ->  48 04 00 00 00 0E 00 00 00
```

which is the exact field in **all 63** archived login captures. The model reproduces the entire nested block byte-for-byte from nothing but the two launcher arguments.

**Practical inverse (this is what the tester needs):**

| you want the account to be | pass |
|---|---|
| `test` | `-acc 74657374` |
| `AB` | `-acc 4142` |
| `mptest02` | `-acc 6D70746573743032` |
| whatever the corpus has today | `-acc test` — because `t`,`s` are not hex digits, this decodes to `U+000E U+0000` |

One wide character per two hex digits, `0x00..0xFF` only, odd input loses its last character, non-hex characters silently become `0`.

---

## 6. The same field on the game listener, and what our server does with it

The `LoginVerifyVital` (`0x3784`) frame the client sends to the GAME listener starts with the **same decoded account wstring**:

```
0B 68 | 48 04 00 00 00 0E 00 00 00 | 44 09 00 00 00 "localtest"
 u8       the decoded account          the token the server handed out
```

**44 of the capture_v141 GAME files** carry it (asserted).

Our own server, read-only facts:

* v141 answers `0x42BF` **by nested id alone** — three `LOGIN_REQ` mentions in the whole file (constant, name table, dispatch condition) and no payload parser at all. It never reads the account or the password.
* v141 carries the decoded account as a **frozen literal**: `make_game_login_ack` builds its reply from `b"\x0B\x68\x48\x04\x00\x00\x00\x0E\x00\x00\x00" + astr_tag(token)`. That literal is exactly `decode_hex("test")` under this model. **If the client is launched with a different `-acc`, the server's ack will echo back the old account bytes.** That is a live-test hazard, not a static one, and the GT draft calls it out.
* the account name our server persists comes from **its own** `--token` argument (`default="localtest"`), not from the wire: `game_listener(..., token)` → `GameSessionState(token)` → `FoundationSession(..., token)` → `lifecycle.login(login_name)` → `store.ensure_account(login_name)`.
* `store.ensure_account` is `INSERT OR IGNORE INTO accounts(login_name,created_at)`, so **no account has to be prepared in advance** — but changing the client's `-acc` will **not** create a row today, because the server never looks at it.

---

## 7. What is proven, what is inferred, what is still open

### ① byte-exact / statically proven (126 guards)

1. `0x42BF` = `LSCN_LoginVitalReq`, vtable `0xF16B34`, object `0x4C` bytes, `VitalData` subclass.
2. The frame has **exactly two fields**, in this order: `wstring @ +0x14` (tag `0x48`) then `string @ +0x30` (tag `0x44`). Length prefixes are **byte counts**.
3. `+0x14` is the **account**; `+0x30` is the **password**. Proven by the assignment site, not by position.
4. The password is transmitted in **clear text** (WideCharToMultiByte only, no hash).
5. The account is `decode_hex(-acc)` on the command-line path and the dialog's `+0x14` edit box otherwise; the password is `-pwd` or the `+0x18` edit box.
6. The hex decoder is exactly hexadecimal over all 65536 character values.
7. All 63 archived login captures reproduce byte-for-byte from the model of `-acc test -pwd test`; the corpus has **one** distinct account value and **one** distinct password value — which is precisely the audit's G8 observation, now explained instead of merely observed.
8. Our server never reads either field and persists a name from its own `--token`.

### ② structural inference (stated as inference)

* `cStateLogin`'s state-entry hook is the only path that reaches `DoLogin` at boot. Any other caller would have to come through the dialog, and the dialog only opens when the command-line flag is clear. This is read off the two branch targets; no execution trace backs it.
* `LSCN_LoginVitalRes` `+0x14 == 1` is treated as "success" by `0x4C57A0`. **Recorded only** — the Res class's own `Serial` was not decoded in this milestone and no claim is made about its field layout.

### ③ still open — needs a live run (this is GT-020)

* Whether the client completes login when the account it sends differs from the account echoed back in v141's frozen ack.
* Whether anything downstream of login (character list, StartGame, DB rows) changes when the account changes. Statically the answer is "no, because the server never reads it", but that has never been observed.

### Not claimed, deliberately

* Nothing about what an original server did with either field. **The original server is gone and there was never a publish.**
* Nothing about the outer envelope, decoded elsewhere and used here only to locate the nested body.
* Nothing about the `-pcc_multi` switch (`0xF0A108`) that WinMain parses two lines below `-pwd`. It was seen and is recorded here as a literal fact only; its consumer was not traced, no hypothesis is opened, and it is **not** proposed as follow-up work.
* The wire model is restricted to ASCII arguments. `WideCharToMultiByte` under a non-ASCII code page is out of scope and the model refuses it.

---

## 8. Reproduce

```
py -3 tools\pf_login_vital_req_static.py            # 126 guards, exit 0
py -3 tools\pf_login_vital_req_static.py --json     # the counts block below
py -3 -m pytest tests\test_login_vital_req_static.py -q
```

The test parses the `LOGIN_REQ_COUNTS` block below out of this file and compares it, key by key, to a live run of the verifier, so no number here can drift away from the binary. Every number is compared exactly.

> **Re-pinning rule.** `distinct_account_values`, `distinct_password_values`, `distinct_request_bodies`, `archived_login_captures` and `archived_login_captures_with_0x42bf` are the corpus numbers. **They are supposed to move when GT-020 runs** — that is the whole point of the test. When a capture with a different `-acc` lands in the repo, re-run `--json` and update this block in the same change, and say in the commit message which account was used.

```json LOGIN_REQ_COUNTS
{
  "account_field_offset": "0x14",
  "account_field_type": "std::wstring",
  "account_field_wire_tag": "0x48",
  "account_sources": [
    "-acc argument (hex-decoded)",
    "Prototype_Login1 edit box +0x14"
  ],
  "archived_login_captures": 63,
  "archived_login_captures_with_0x42bf": 63,
  "client_sha256": "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623",
  "distinct_account_values": 1,
  "distinct_password_values": 1,
  "distinct_request_bodies": 1,
  "dologin_callers": 2,
  "game_captures_with_the_same_account": 44,
  "golden_account_wchars": [
    14,
    0
  ],
  "golden_nested_hex": "12 BF 42 0B 00 48 04 00 00 00 0E 00 00 00 44 04 00 00 00 74 65 73 74",
  "guards_total": 126,
  "hex_decode_callers": 1,
  "hexval_map_bytes": 55,
  "hexval_mismatches_over_65536_chars": 0,
  "hexval_table_entries": 17,
  "measured_at_head": "dd1a66c",
  "object_size": 76,
  "password_field_offset": "0x30",
  "password_field_type": "std::string",
  "password_field_wire_tag": "0x44",
  "password_is_hashed": false,
  "password_sources": [
    "-pwd argument",
    "Prototype_Login1 edit box +0x18"
  ],
  "probe_account_name": "AB",
  "probe_argument": "4142",
  "probe_body_length_delta": 0,
  "probe_bytes_changed": 2,
  "serial_field_count": 2,
  "wire_id": "0x42BF"
}
```

---

## 9. Hand-off

* The GT spec that closes ③ is drafted at `pf_bridge\drafts\GT_DRAFT_MPOPT1B_LOGIN_USERNAME_20260819.md`. **The chief moves it into `GAME_TEST_QUEUE.md`; this milestone did not touch the queue.**
* Option 1 is now complete: **(a)** round 78, **(b)** here. Per Panya's instruction, **Options 2 and 3 are not started** — only their ordering was approved, not their budget.
