# DELETE-SOFT-002 — First natural 0x36DB decode and response-envelope failure analysis (GT-010)

Date: 2026-08-18
Test: GT-010 (attended), capture root `GameClient/capture_gt010_20260818_015927`
Hypothesis under test: HYP-PF-015 (`docs/HYPOTHESIS_LEDGER.json` entries 966-1017)

## Summary

GT-010 produced the project's first natural `DeleteActorVital` (0x36DB) wire. The
designed request envelope (HYP-PF-015) is **confirmed byte-for-byte at every
structural field**; only the content of the opaque wstring differs from both
designed probe forms (it is a 32-byte ASCII-hex, MD5-digest-shaped token, not a
UTF-16LE name and not empty). The soft delete committed before the ack
(`deleted_at` 39 ms before the SENT event). The client rejected our 77-byte echo
ack with `GSCN_RunTimeProtocolRes ErrorData=28317`.

Root-cause finding: **28317 = 0x6E9D = the GSCN_RunTimeProtocolRes protocol
class id itself**, and the failure mechanism is the documented RuntimeRes-v4
stream over-read: our ack was built with `make_runtime_vital` (singular), which
does **not** append the derived-class trailing change mask `0B 00` that every
previously accepted RuntimeRes packet carries and whose omission was already
live-proven (three separate precedents) to raise exactly ErrorData=28317. The
echoed record itself is very likely fine; the envelope is one `0B 00` short.

## (a) Natural 0x36DB request — hex and field decode vs. the HYP-PF-015 design

Client frame #93, 02:04:21.680, `capture_v141/GAME_20260818_020106_955833_62358.txt`
lines 248-260 (also `server_console_live.out.txt` lines 159-164; event index
`capture_v141/GAME_LIVE.txt` line 98).

Raw frame (74 B, snappy-compressed payload, magic 0x5F253EAC):

```
00000000  AC 3E 25 5F 42 00 00 00 42 5C 12 3A 45 14 00 00  |.>%_B...B\.:E...|
00000010  00 00 08 00 0B 02 12 01 00 12 DB 36 0B 01 08 01  |...........6....|
00000020  08 00 05 15 90 44 20 00 00 00 37 44 30 31 34 45  |.....D ...7D014E|
00000030  35 34 31 41 46 41 41 34 33 32 36 37 43 41 38 30  |541AFAA43267CA80|
00000040  42 43 43 42 43 33 46 44 36 42                    |BCCBC3FD6B|
```

Decompressed PC (66 B) — note the client used a real snappy back-reference
(`05 15 90` at frame offset 0x22) for the zero run; our own frames are
literal-only. Framing layer is symmetric and not at issue.

```
00000000  12 3A 45 14 00 00 00 00 08 00 0B 02 12 01 00 12  |.:E.............|
00000010  DB 36 0B 01 08 01 08 00 14 00 00 00 00 44 20 00  |.6...........D .|
00000020  00 00 37 44 30 31 34 45 35 34 31 41 46 41 41 34  |..7D014E541AFAA4|
00000030  33 32 36 37 43 41 38 30 42 43 43 42 43 33 46 44  |3267CA80BCCBC3FD|
00000040  36 42                                            |6B|
```

Field decode (PC-relative offsets) against the designed accepted shape
(`src/pirateforce_foundation/delete_actor_hypothesis.py` lines 14-19, 67-78):

| off | bytes | field | designed guess | verdict |
|---|---|---|---|---|
| 0x00 | `12 3A 45` | outer protocol 0x453A GSCN_LoginProtocol | same | **MATCH** |
| 0x03 | `14 00 00 00 00` | u32 = 0 | same | **MATCH** |
| 0x08 | `08 00` | protocol version 0 | same | **MATCH** |
| 0x0A | `0B 02` | change mask 0x02 | same | **MATCH** |
| 0x0C | `12 01 00` | vital count 1 | same | **MATCH** |
| 0x0F | `12 DB 36` | nested vital id 0x36DB DeleteActorVital | same | **MATCH** |
| 0x12 | `0B 01` | nested version 1 | same | **MATCH** |
| 0x14 | `08 01` | op = 1 (raw +0x14) | op 1 | **MATCH** |
| 0x16 | `08 00` | selector = 0 (raw +0x15) | selector 0 | **MATCH** |
| 0x18 | `14 00 00 00 00` | u32 = 0 (raw +0x18) | 0 | **MATCH** |
| 0x1D | `44 20 00 00 00` | wstring byte-length 0x20 (raw +0x1C) | 0x00 (empty) or 0x10 (name) | **DIFFERENT** |
| 0x22 | `"7D014E541AFAA43267CA80BCCBC3FD6B"` | 32 B opaque payload | empty / UTF-16LE `DelTst01` | **DIFFERENT** |

Verdict on the request side: the HYP-PF-015 designed envelope
(`gscn_login_protocol_one_vital_designed`, outer 0x453A v0 mask 0x02 count 1,
nested 0x36DB v1, DELETE-003 field order 08/08/14/44) is **exactly right** —
capture tool agrees: `STRUCTURAL_IDS [(0, 17722, 'GSCN_LoginProtocol'),
(15, 14043, '0x36DB')] OUTER version=0 mask=0x02 count=1 nested_version=1`
(raw log line 260). Our strict parser accepted it (content-agnostic on the
string, even-length rule satisfied) and the server classified `exact_op1` and
committed. Only the two designed probe *string contents* were wrong guesses.

About the token `7D014E541AFAA43267CA80BCCBC3FD6B`:

- 32 ASCII hex characters = MD5-digest-shaped; it is ASCII, not UTF-16LE text
  (the "UTF-16LE" typing in our parser is a host-side label; DELETE-003
  nonclaims stand).
- It is **not** the character GUID we issued in the character list
  (`E33FEDFD8E171A2FE668EABF4138084A`, char-list wire offset 0x57 and DB
  `characters.actor_wire`), so the client derived it at delete time via the
  DELETE-003 UI virtual call (`0x4E6190`).
- Negative MD5 probes (both ASCII and UTF-16LE encodings, sandbox-computed):
  `Arena01`, `arena01`, `test` (the plaintext password on the login wire,
  `capture_v141/LOGIN_20260818_020024_632361_62355.txt` line 5), `localtest`,
  `DelTst01`, the issued GUID, empty string, common PINs, and simple
  concatenations — no match. The token remains semantically opaque; a future
  static pass on `0x4E6190`'s string source can resolve it. It did not gate the
  server path and does not gate the response fix.

## (b) Our 77-byte response — hex and the exact stumble point

SENT `HYP_PF_015_DELETE_ACTOR_SELECTOR00_SOFT_DELETE_COMMITTED`, 02:04:21.729
(`GAME_LIVE.txt` line 99; raw log lines 261-273; console lines 165-170).
DB proof of commit-before-ack: `characters.deleted_at =
2026-08-17T19:04:21.690592+00:00` (= 02:04:21.690 local, 39 ms before SENT) in
`state/pirateforce_gt010_20260818_015927.sqlite3` (queried from a /tmp copy,
read-only).

Frame (77 B):

```
00000000  AC 3E 25 5F 45 00 00 00 42 F0 41 12 9D 6E 14 00  |.>%_E...B.A..n..|
00000010  00 00 00 08 04 0B 02 12 01 00 12 DB 36 0B 01 08  |............6...|
00000020  01 08 00 14 00 00 00 00 44 20 00 00 00 37 44 30  |........D ...7D0|
00000030  31 34 45 35 34 31 41 46 41 41 34 33 32 36 37 43  |14E541AFAA43267C|
00000040  41 38 30 42 43 43 42 43 33 46 44 36 42           |A80BCCBC3FD6B|
```

Decode: magic (4) + payload len 0x45=69 (4) + snappy varint uncompressed size
0x42=66 (1) + snappy literal tag `F0 41` = 66-byte literal run (2) + PC (66):

| PC off | bytes | field |
|---|---|---|
| 0x00 | `12 9D 6E` | outer protocol **0x6E9D = 28317** GSCN_RunTimeProtocolRes |
| 0x03 | `14 00 00 00 00` | u32 = 0 |
| 0x08 | `08 04` | protocol version 4 |
| 0x0A | `0B 02` | change mask 0x02 (vital collection present) |
| 0x0C | `12 01 00` | vital count 1 |
| 0x0F | `12 DB 36 0B 01` | vital id 0x36DB, version 1 |
| 0x14 | `08 01 08 00 14 00 00 00 00 44 20 00 00 00` + token | echoed request record (fully consumable by codec 0x5E4E10: u8, u8, u32, wstring) |
| 0x42 | — (end of buffer) | **MISSING: RuntimeRes-v4 derived-class trailing change mask `0B 00`** |

Byte-diff against the RuntimeRes response the client **accepted 3 minutes
earlier in the same session** (FOUNDATION_CHARACTER_LIST_ONCE, 253-B PC, raw
log lines 23-39 / console lines 137-153):

- PC offsets 0x00-0x0E (`12 9D 6E | 14 00 00 00 00 | 08 04 | 0B 02 | 12 01 00`)
  are **byte-identical**. The envelope head is not the problem.
- Nested id/version differ by design (0x36EF v10 vs 0x36DB v1).
- **Tail**: the accepted char-list PC ends `... 0B 00 0B 00` — its final
  `0B 00` is the RuntimeRes-v4 derived-class trailing change mask. Our delete
  ack ends `... 36 42` (`"6B"`, last token chars) — **no trailing mask at all**.

Every RuntimeRes packet this client build has ever accepted carries that
trailing mask: the runtime-proven SelectActorVital shape appends it explicitly
(`current/pf_login_game_server_v141.py` lines 662-686), the V131 TeleportCheck
selftest states "with trailing mask" (console line 23), and `make_runtime_vitals`
(plural, lines 689-712) appends `0B 00` unconditionally, with this comment
(lines 706-709):

> RuntimeRes v4 has a second (derived-class) change mask after the inherited
> VitalData collection. Empty RuntimeRes proved this exact trailing 0B 00 on
> the wire; **omitting it makes the client over-read the collection response
> and raise ErrorData=28317.**

`make_runtime_vital` (singular, lines 747-765) — the builder
`make_delete_actor_ack_response` used (`delete_actor_hypothesis.py` lines
237-264) — does **not** append it, and unlike every prior caller, the delete
ack's payload does not happen to end with its own `0B 00`. So the client read
the envelope head, the count, the full echoed record, then tried to read the
derived-class mask tag, hit end-of-stream, and aborted the protocol read.
That is the stumble point: **PC offset 0x42, the byte that isn't there.**

(Corollary: the module docstring's claim that this is "the same envelope every
accepted character-select-stage response uses" was doubly off — CreateActor
success is actually delivered on GSCN_LoginProtocol via `make_login_vital`
(v141 lines 2292-2302, 1109-1127; console banner line 72), and the one
character-select response that does use RuntimeRes, the character list,
carries the trailing mask.)

## (c) ErrorData=28317 — hypothesis and evidence

**Hypothesis: ErrorData is the 16-bit protocol class id of the protocol whose
Read failed; 28317 = 0x6E9D = GSCN_RunTimeProtocolRes, i.e. the client is
reporting a deserialization failure of the very envelope we sent, caused by
stream over-read (missing trailing mask), not an unknown vital id.**

Evidence:

1. `GSCN_RUNTIME_PROTOCOL_RES = 0x6E9D` in the frozen serializer
   (`current/pf_login_game_server_v141.py` line 384). 0x6E9D = 28317 decimal.
   The first three PC bytes of our rejected frame are `12 9D 6E` — the id in
   the error equals the id on the wire. The dialog also *names* the class
   (`GSCN_RunTimeProtocolRes`), consistent with id ↔ class.
2. Three independent prior **live** reproductions of exactly ErrorData=28317,
   all RuntimeRes stream-tail/misalignment faults, none vital-id faults:
   - empty-RuntimeRes trailing-mask experiment (v141 lines 706-709, quoted
     above);
   - v26 SelectActorVital wrong tail count — "the 2-tail variant is rejected
     immediately (GSCN_RunTimeProtocolRes ErrorData=28317)" (v141 lines
     672-677);
   - V43 combined actor stream — "V43 proved the combined actor stream
     triggers ErrorData=28317" (v141 lines 1292-1298).
3. Alternative readings checked and rejected:
   - *vital id the client expected*: no vital 0x6E9D/28317 exists in the
     client-binary registry (`pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`
     — only hit for our ids is line 76 `0x36DB DeleteActorVital`); and the
     client demonstrably parses other vitals under 0x6E9D in this session.
   - *little-endian swap 0x9D6E = 40302*: no registry entry, no code
     reference anywhere in the serializer.
   - *offset into the frame*: 28317 > 77 (frame length); nonsensical.
4. Post-error behavior fits an envelope-layer abort: the client sent nothing
   further and closed both connections (console lines 171-175; `GAME_LIVE.txt`
   ends at rx=93), and the character list on screen stayed stale — the read
   aborted before any UI consumer (`0x5EFDC0 -> 0x4BAEB0`) could run, so no
   claim about the consumer is falsified yet.

## (d) Candidate response designs, ranked

### Candidate 1 (top) — same echo, RuntimeRes v4, **plus the trailing derived-class mask `0B 00`**

Wire: current 66-B PC + `0B 00` = 68-B PC / 79-B frame. One-line server
change: build via `legacy.make_runtime_vitals([(0x36DB, 1, nested_payload)])`
(which appends the mask) instead of `make_runtime_vital`, or append
`u8tag(0x0B, 0)` to the payload. Everything else (commit-before-ack, fail-
closed gates, hash pins regenerated) unchanged.

Why first:
- The failure mechanism it fixes is the only one with an **exact, thrice
  live-proven ErrorData=28317 precedent** (section c, evidence 2).
- The fixed shape becomes structurally congruent with every RuntimeRes packet
  this client build has ever accepted, including the char list accepted
  earlier in the same GT-010 session.
- DELETE-003 grade-A statics say the inbound consumer exists and its codec
  (`0x5E4E10`) visits exactly u8/u8/u32/wstring — the echoed record is
  readable; only the envelope tail was short. Response op=1 lands inside
  `0x4BAEB0`'s handled branch range 1..4.

Headless tests:
- Unit: new ack PC == old ack PC + `0B 00` (single-byte-pair diff, nothing
  else moved); new PC equals `make_runtime_vitals` output for the same tuple;
  re-pin the SHA-256 probe constants in `delete_actor_hypothesis.py`.
- Property: every outgoing RuntimeRes PC the server can emit ends with the
  trailing mask (guards the char-list/TeleportCheck invariant too).
- Structural replay: pf_bridge structural parser consumes envelope + one
  vital + trailing mask to exact EOF (no over/under-read) on the new frame.

Risk / residual claim for the attended round: parse acceptance is predicted;
whether `0x4BAEB0` branch-1 visibly refreshes the list is still the queued
client-observable claim (DELETE-003 explicitly does not prove refresh).

### Candidate 2 — echo on GSCN_LoginProtocol 0x453A (byte-exact request echo)

Wire: reply PC == request PC (66 B), exactly as LOGIN_VERIFY_ACK_ONCE does.
Rationale: request/response symmetry precedent — **both** other character-
select-stage exchanges answer on LoginProtocol and are runtime-proven accepted
(LoginVerify echo, this session lines 133-136; CreateActor success moved from
RuntimeRes to LoginProtocol at v30, `make_login_vital` v141 lines 1109-1127
"LoginVerifyVital responses under the same GSCN_LoginProtocol envelope are
already accepted by this client build"). The natural delete request arrived on
LoginProtocol; LoginProtocol v0 has no trailing-mask requirement (accepted
echoes end at the vital record).

Why second: it also removes the over-read, but explains the v30 CreateActor
envelope move as its precedent rather than the exact-error precedent; the
GT-010 error text points at the RuntimeRes reader mechanism specifically, and
Candidate 1 is the minimal byte change from an envelope family already proven
deliverable mid-session. Choose Candidate 2 if a rerun of Candidate 1 still
errors — that outcome would itself be strong evidence the client's delete
consumer only hangs off the LoginProtocol dispatch path, like CreateActor's.

Headless tests: assert reply PC is byte-identical to the captured natural
request PC (pin the GT-010 bytes as fixture); envelope-field equality with the
accepted LOGIN_VERIFY_ACK shape (outer 0x453A, `08 00`, mask 0x02, count 1);
SHA-256 pins.

### Candidate 3 (escalation, gated) — Candidate 1 + immediate refreshed character list

After the fixed ack, queue one FOUNDATION-style RuntimeRes SelectActorVital
v10 list rebuilt from the post-delete DB (for GT-010's account: the runtime-
proven empty-list wire, `make_select_actor_empty_payload` shape, v141 lines
662-686). This forces the client-observable outcome (character gone) even if
`0x4BAEB0` branch-1 performs only dialog dismissal.

Why third: it is not a decode of the original response policy — it masks
whether the ack alone drives the refresh, so it should only run after
Candidate 1 shows "parse OK but list stale". **Governance gate:** HYP-PF-015's
stop rule currently says "do not add ... list-refresh compositions"
(`HYPOTHESIS_LEDGER.json` line 978) — this candidate requires a ledger
amendment/owner nod before implementation.

Headless tests: Candidate 1's suite + the refreshed-list PC equals the
runtime-proven v25 empty-list wire (hash pin) for the zero-character case, and
the one-character composition path reuses the byte-exact GT-010 char-list
builder against a non-deleted fixture.

Not proposed: guessing a different nested record schema (status codes, ops
2..4) — no static or wire evidence supports any alternative record layout,
and the codec statics say the echo is readable; schema roulette would burn
attended rounds.

## (e) Evidence file index

| claim | file (project-relative unless absolute) |
|---|---|
| natural request frame + decompressed PC + STRUCTURAL_IDS | `GameClient/capture_gt010_20260818_015927/capture_v141/GAME_20260818_020106_955833_62358.txt` lines 248-260 |
| our 77-B ack PC + frame bytes | same file, lines 261-273 |
| event timeline (RECV .680 / SENT .729) | `GameClient/capture_gt010_20260818_015927/capture_v141/GAME_LIVE.txt` lines 98-100 |
| server-side console mirror of both, milestone, clean shutdown | `GameClient/capture_gt010_20260818_015927/server_console_live.out.txt` lines 127-175 (esp. 159-175); stderr empty (`server_console_live.err.txt`) |
| accepted char-list RuntimeRes (envelope head identical, tail `0B 00 0B 00`) | raw game log lines 23-39; console lines 137-153 |
| accepted LoginProtocol echo (LOGIN_VERIFY_ACK) | raw game log lines 12-21; console lines 129-136 |
| plaintext password `test` on login wire (token negative-probe input) | `GameClient/capture_gt010_20260818_015927/capture_v141/LOGIN_20260818_020024_632361_62355.txt` lines 2-10 |
| commit-before-ack (`deleted_at` 19:04:21.690Z) + issued GUID + fingerprint | `Pirate Force ServerProject/state/pirateforce_gt010_20260818_015927.sqlite3` `characters` row id=1 (read-only /tmp copy) |
| GSCN_RUNTIME_PROTOCOL_RES = 0x6E9D = 28317; GSCN_LOGIN_PROTOCOL = 0x453A | `Pirate Force ServerProject/current/pf_login_game_server_v141.py` lines 382-384 |
| trailing-mask requirement + 28317 precedent (empty RuntimeRes) | same file, lines 689-712 (comment 706-709) |
| 28317 precedent (v26 2-tail SelectActor) | same file, lines 662-686 (comment 672-677) |
| 28317 precedent (V43 combined actor stream) | same file, lines 1291-1298 |
| `make_runtime_vital` (singular) has no trailing mask | same file, lines 747-765 |
| CreateActor success on LoginProtocol (v30 move) | same file, lines 1109-1127, 2292-2302; console banner line 72 |
| delete ack builder + envelope claim under test | `Pirate Force ServerProject/src/pirateforce_foundation/delete_actor_hypothesis.py` lines 14-33, 237-264 |
| strict request parser (content-agnostic wstring) | `Pirate Force ServerProject/src/pirateforce_foundation/delete_actor.py` |
| char-list payload construction (trailing `0B 00 0B 00`) | `Pirate Force ServerProject/src/pirateforce_foundation/legacy_bridge.py` lines 22-29 |
| 0x36DB registry identity; no 0x6E9D/28317/0x9D6E vital exists | `pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv` line 76 (+ negative grep) |
| DELETE-003 statics: codec 0x5E4E10 field order, producers, inbound consumer 0x5EFDC0->0x4BAEB0 branches 1..4 | `Pirate Force ServerProject/reports/PF_DELETE003_PRODUCER_OUTER_FRAMING_NEGATIVE_20260816.md` |
| HYP-PF-015 claim/stop rule/falsification hooks | `Pirate Force ServerProject/docs/HYPOTHESIS_LEDGER.json` lines 966-1017 |
| opt-in scenario under test | `Pirate Force ServerProject/scenarios/delete_actor_hypothesis_soft_delete.json` |

## Ledger note (for the chief; no ledger edit made by this analysis)

Per HYP-PF-015's falsification clause, GT-010 *confirms* the request-envelope
half and *falsifies only the response-envelope half* ("if the real client
rejects ... the echo ack"). The request side should be promoted from designed
to natural-wire-confirmed; the response side redesigned per Candidate 1. The
stop-rule sentence "Stop and record if the first attended run shows the client
emitting a different delete envelope" was not triggered — the client emitted
exactly the designed envelope.
