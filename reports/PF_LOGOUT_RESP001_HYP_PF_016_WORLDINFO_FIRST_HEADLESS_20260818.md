# PF LOGOUT-RESP-001 — HYP-PF-016 response-first logout (0x3D4B before ack), headless wire/DB proof (2026-08-18)

One claim (Grade B, wire/DB layer only): behind the new
`scenarios/logout_hypothesis_worldinfo_first.json` opt-in
(`response_policy: worldinfo_response_first`, `post_ack_action: close_socket`,
`close_delay_ms: 250`, `production_allowed: false`), the Foundation server
stores in connection-local memory the last full 248-byte `GetWorldInfoVital`
(0x3D4B) payload the client itself sent during a runtime-ready session
(never replying at dialog-open time, matching the observed server behavior),
and answers both captured `LogoutVital` (0x1B40) request forms
**response-first**: the designed 0x3D4B response — the stored payload echoed
verbatim inside the accepted `GSCN_RunTimeProtocolRes` v4 envelope with the
client's own collection count (3) mirrored and the proven trailing
derived-class change mask `0B 00` — goes on the wire strictly before the
**byte-identical hash-pinned PF-012 ack**, followed by the unchanged PF-013
clean `shutdown(2)+close` ~250 ms later. The session lease
(`sessions.closed_at`) commits before any response byte is queued. A session
that never produced a full 0x3D4B payload gets **silence** on logout: no
reply, no write, no ack fallback. Everything else fails closed exactly as
under PF-012/PF-013, and the two pre-existing logout scenarios stay
byte-identical. **No client-observable claim is made**: whether the real
client now transitions (01: exit, 03: character select) is exactly GT-013,
queued for the next attended big round.

## Why this shape (design lineage)

- GT-008 (attended, 2026-08-18, both subcodes) falsified the client layer of
  ack+close (HYP-PF-013): the real client never notices a bare server FIN —
  no transition, no dialog, no disconnect handling for 40+ s. A transition
  therefore needs a protocol response frame the client recognizes; PF-013's
  decision recorded the 0x3D4B-first design as the fallback requiring a new
  entry, opened here as HYP-PF-016.
- R40 decoded the only logout-correlated frame the client produces:
  `GetWorldInfoVital` 0x3D4B fires on every logout-dialog open (7/7 across
  two sessions, always followed by `LogoutVital` in 2–14 s) as a 268-byte PC
  (envelope count 3 + 248-byte payload). The payload skeleton is byte-stable
  across sessions; only six float32 value slots per 123-byte record vary
  (semantics unproven — kept as nonclaims). **No golden response exists in
  the corpus**, so the response is a designed hypothesis, not a reproduction.

## Envelope choice (the one design freedom, and why)

The response is composed manually as a **mirrored container**: outer id
`0x6E9D` (Res), protocol version 4, mask 0x02, collection count **3 exactly
as the client's own request serialized it**, nested `0x3D4B` v0, then the
stored 248 payload bytes verbatim, then the trailing derived-class mask
`0B 00`. Reasoning, anchored to proven evidence only:

1. **Envelope family**: every response the real client ever accepted live is
   a `GSCN_RunTimeProtocolRes` v4 collection (PF-012 delivered without
   desync in GT-007; PF-014 chat echo rendered in GT-009; PF-015 v2 after
   GT-010). No other deliverable envelope is proven.
2. **Trailing mask is mandatory**: DELETE-SOFT-002 proved live that a
   RuntimeRes collection without the trailing `0B 00` derived-class mask is
   over-read and rejected with `ErrorData=28317`. The mirror composition
   carries it.
3. **Count mirrored, not re-wrapped**: `make_runtime_vitals` with one vital
   would rewrite the collection count to 1 while the 248-byte body still
   contains the client's three-record structure — precisely the
   count/stream misalignment class the 28317 error punishes. R40 pinned the
   request layout (count 3, id+version declared once, then the records), so
   mirroring count 3 and echoing the bytes keeps the collection stream
   byte-for-byte as the client's own writer produced it; whatever the
   client's reader convention is, it sees the same correspondence it wrote.
   Relative to the client's request container, exactly three bytes-groups
   differ — outer id Res, version 4, trailing mask — all three the proven
   Res-envelope constants. Zero content bytes are invented.

## Close lever: composed, default ON in the new scenario

The scenario keeps the PF-013 close (`close_socket`, 250 ms after the ack)
rather than making a second no-close variant, because (a) GT-008 proved the
close is invisible to this client at worst — it cannot add a spurious
disconnect dialog; (b) the accepted v141 process serves one client at a
time, so a logout that leaves the socket open would wedge the listener
(GT-007 showed the client parks forever on an open socket); (c) PF-013's
post-GT-008 decision explicitly keeps the wire-proven close available for
composition with a response-first design. The delay is unchanged (250 ms)
and the ordering [response, ack, FIN] is asserted on the wire.

## Fail-closed path: silence, deliberately no ack-only fallback

If no full 0x3D4B payload was ever stored on the connection, the logout lane
returns nothing and writes nothing (`logout_hypothesis_worldinfo_missing_no_reply`).
A fallback to the PF-012 ack would (a) silently re-run the shapes GT-007/
GT-008 already falsified, contaminating the attended evidence for GT-013,
and (b) commit `closed_at` while the client provably keeps playing — the
exact server/client state divergence GT-010 demonstrated must be avoided.
R40's 7/7 correlation says a real client always sends the full form before
LogoutVital, so this guard should never fire outside malformed drivers.

## Pins (all sha256, upper-case)

Request side (captured, read-only):
- LogoutVital request PCs (34B, unchanged PF-012 pins): 01 `EF3B19F3..8973`,
  03 `EC5B53DC..FAA0`.
- 0x3D4B full-form request: PC 268B = 20B envelope
  `126F6E140000000008000B02120300124B3D0B00` + 248B payload; probe payloads
  `capture_gt002` `5959EC6B..F324` (request PC `F185DE9A..DF99`),
  `capture_item_move_hyp001` `9D4D11E1..BCF1` (request PC `D33E068B..A559`);
  record skeleton pinned in `logout_hypothesis.py`
  (`WORLDINFO_RECORD_SKELETON`, float slots free), two records byte-identical
  + `0B 00` terminator enforced.

Response side (designed, deterministic given the stored payload):
- 0x3D4B response: PC 270B (envelope
  `129D6E140000000008040B02120300124B3D0B00` + payload + `0B00`), frame 283B.
  Probe pins: gt002 PC `7879485A..3EFF` / frame `21D7971D..98A8`; hyp001 PC
  `3E7C2A20..98C9` / frame `8AEB3973..114C`.
- Logout ack: unchanged PF-012 bytes (36B PC / 46B frame): 01 frame
  `9B417B5F..3D0A`, 03 frame `AB172DFF..6696`.
- Ordering pin: actions queued `[0x3D4B response, ack]`, both delay 0.0; the
  frozen listener sends in list order on the one TCP stream; FIN scheduled
  +250 ms after queueing.

## Loopback unit layer (sandbox, this round)

`tests/test_logout_worldinfo_first.py` — 15 tests: both subcodes return
`[HYP_PF_016_*_WORLDINFO_RESPONSE_FIRST, HYP_PF_016_*_ACK_THEN_SERVER_SOCKET_CLOSE]`
byte-exact vs pins with `closed_at` committed and one 250 ms close
scheduled; the LAST stored payload is echoed; composed response is
structurally and hash-pinned for both probes (envelope prefix, verbatim
payload at +20, trailing mask, `frame_pc` equality) and rejects malformed
payloads; missing stored payload / empty form / malformed full forms
(truncated, extended, diverging records, skeleton-broken, bad terminator) /
out-of-sequence worldinfo / wrong logout payload / wrong sequence / missing
transport lever / already-closed lease all fail closed with no write and no
schedule; float-slot variants inside the skeleton remain lawful; post-ack
frames (including 0x3D4B) stay counted-and-ignored; the echo and ack_close
scenarios ignore 0x3D4B (nothing stored, no new events) and keep their exact
PF-012/PF-013 action bytes; tampered scenario JSON (production flag, delay,
action, policy, missing key, sizes, pins) is rejected. Targeted run:
`tests/test_logout_worldinfo_first.py` + `test_logout_hypothesis.py` +
`test_logout_ack_close.py` = **36 passed**.

## Headless runtime layer (sandbox, real server process, real TCP)

Probe `reports/logout_resp001_smoke/pf_hyp016_worldinfo_probe.py`
(stdlib-only, sockets + scratch DB only, refuses repo write targets) booted
the real app (`python3 -m pirateforce_foundation.app --db
/tmp/hyp016_scratch.sqlite3 --logout-hypothesis-scenario
scenarios/logout_hypothesis_worldinfo_first.json`) on a freshly migrated
scratch DB and ran three serial passes
(login → create → start_game → first empty runtime req → runtime-ready):

- **pass A (subcode 01, gt002 payload)**: worldinfo stored with **no reply**;
  heartbeats flowing before logout (2 seen); after the logout send exactly
  two non-heartbeat frames in order — 283B `21D7971D..98A8` (response pin)
  then 46B `9B417B5F..3D0A` (ack pin); `closed_at` **13.8 ms before** the
  response arrival (10.3 ms after the logout send); **EOF at ack+244.5 ms**
  (window 100–2000 ms).
- **pass B (negative, subcode 03, nothing stored)**: zero non-heartbeat
  frames, heartbeats continue (3 in window), **no EOF**, lease `closed_at`
  **stays NULL**.
- **pass C (subcode 03, gt002 then hyp001 stored)**: response echoes the
  **latest** stored payload — 283B `8AEB3973..114C` (hyp001 pin) then 46B
  `AB172DFF..6696` (ack 03 pin); `closed_at` 14.2 ms before the response;
  EOF at ack+244.3 ms.
- Verdict JSON all-true, probe exit 0:
  `reports/logout_resp001_smoke/LOGOUT_RESP001_sandbox_smoke_20260818_034540_probe.json`
  (+ transcript alongside). Canonical DB untouched (sha `B5557E9F..` head
  unchanged; the probe never opens it).

## Files touched

- `scenarios/logout_hypothesis_worldinfo_first.json` (new, exact-allowlist)
- `src/pirateforce_foundation/logout_hypothesis.py` (PF-016 constants,
  third profile, classifier, mirror-echo composer; PF-012/013 pins untouched)
- `src/pirateforce_foundation/runtime.py` (logout area only: 0x3D4B
  observation lane behind the worldinfo_first policy + response-first branch
  in the logout dispatch; old scenarios byte-identical)
- `tests/test_logout_worldinfo_first.py` (new)
- `docs/HYPOTHESIS_LEDGER.json` (HYP-PF-016 appended),
  `tools/verify_hypothesis_ledger.py` (EXPECTED_IDS/EXPECTED_META appended;
  canonical content sha left for the chief to re-pin — the ledger sha test
  is expected red until then)
- `reports/logout_resp001_smoke/` (probe script + timestamped verdict and
  transcript), this report + `.manifest`

## Nonclaims

1. **No client-observable claim**: whether the real client transitions on
   the 0x3D4B-first sequence (01 exits, 03 returns to character select) is
   GT-013 in the attended big round; this report proves wire/DB layer only.
2. **No original-server claim**: no golden 0x3D4B or 0x1B40 response exists
   in the corpus (R40 re-verified); the original server may never have
   answered GetWorldInfoVital at all.
3. **No payload semantics**: the four float32 values and the constants in
   the 248B payload stay uninterpreted (R40 nonclaims); they are echoed
   verbatim, never edited or generated.
4. No production or default-mode behavior; the scenario is opt-in with
   `production_allowed: false`, and worldinfo storage is connection memory
   only (no table, no write path, not persisted).
5. No claim about subcodes other than 01/03, the empty 2-byte 0x3D4B form
   (observed mid-gameplay, never stored, never answered), or requests
   outside the runtime-ready sequence — all fail closed.
