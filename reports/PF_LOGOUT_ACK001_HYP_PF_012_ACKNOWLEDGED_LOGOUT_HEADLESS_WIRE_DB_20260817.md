# PF LOGOUT-ACK-001 — HYP-PF-012 acknowledged logout, headless wire/DB proof (2026-08-17)

One claim (Grade B, wire/DB layer only): behind the explicit
`--logout-hypothesis-scenario` opt-in, the Foundation server acknowledges both
captured `LogoutVital` (0x1B40) client request forms — subcode 01 (exit game)
and subcode 03 (return to character select) — with a designed hash-pinned echo
composition, after committing a clean session close (`sessions.closed_at`,
no position rewrite), and the connection is silent afterward. Everything else
fails closed with no reply and no write. **No client-observable claim is made**:
whether the real client exits or returns to character select on this ack is
queued for the attended big round.

## Provenance of the request decode (accepted, prior rounds)

- R38 (`pf_bridge\FINDINGS_R38_0x1B40_DECODED_LOGOUTVITAL.md`): registry-hash
  identification `0x1B40 = LogoutVital` (unique in 15,954 client-binary strings,
  method validated 46/47 against the v141 NAMES table, 0 collisions in the
  327-name vital namespace), subcode correlation to the two dialog buttons.
- R40 (`pf_bridge\FINDINGS_R40_0x3D4B_GETWORLDINFO_PAYLOAD_DECODED.md`): corpus
  sweep — both request forms byte-identical across `capture_gt002` (16:44–16:52,
  4 frames) and `capture_item_move_hyp001` (00:38, 2 frames); Foundation sent no
  response; the real client hung until End task (GT-002 client2, observed).
- Captured request pins (34-byte PC / 44-byte frame, deterministic):
  - subcode 01 PC sha256 `EF3B19F34A5FA55698617A16254BA5F722AC0BE44AF12170E1352CD206408973`
  - subcode 03 PC sha256 `EC5B53DCC49C034A9B716F893F4315104146B4220E9551C0101F1F699BB0FAA0`

## Designed response (hypothesis, no golden exists)

No lawful original-server response to `LogoutVital` exists in the corpus
(checked R38 nonclaim 3, re-checked R40). The designed shape is the exact
14-byte request payload echoed inside the accepted `GSCN_RunTimeProtocolRes` v4
single-vital collection envelope (`make_runtime_vitals`, binary-proven +0x1C
serializer with the proven trailing derived-class mask byte), version 0 as in
the client's own request:

- subcode 01 ack: PC 36B sha256 `9E4FA00E408910204C91DE264ED9274ECF7A3C7E8C37C75199F090AB7DE23C67`,
  frame 46B sha256 `9B417B5F0EF05B1096FA000C7FC154DF952EF817232115DA077253BDC27A3D0A`
- subcode 03 ack: PC 36B sha256 `FC8B9E2CC2BD590458F1EAAFCE712D283538D525F136AD0F9838B108395F6DC6`,
  frame 46B sha256 `AB172DFFCBC1195F086A848018FC4797D53945B6B2854D651D37B3740F4E6696`

Ordering: the ack is composed and hash-verified first; the session lease is
closed (`closed_at` committed via the pre-existing `close_connection` path —
no new store write path) and only then are the ack bytes queued. After the
ack every frame on the connection is counted and ignored.

## Loopback unit layer (sandbox, this round)

`tests/test_logout_hypothesis.py` — 10 tests: both subcodes ack after clean
close with `closed_at` verified in the DB; post-ack silence (duplicate logout,
empty poll, login-shaped frame all ignored); wrong payload (uncaptured subcode
02, truncated), wrong sequence, and no-scenario runs leave the session open
with no HYP-PF-012 action; composed acks byte-equal the pinned echo; tampered
scenario JSON rejected; logout and item-move scenarios mutually exclusive.

## Headless runtime layer (Windows, real server process, real TCP)

Job 076 (bridge, 18:51:29–18:52:32 ICT): server booted direct
(`py -3 -m pirateforce_foundation.app`, visible console) on a fresh copy of the
canonical DB (sha verified `CACE7F77..F493`; canonical untouched; mandatory
backup taken) with `--second-password-mode bypass --logout-hypothesis-scenario
scenarios\logout_hypothesis_ack_echo.json`. Probe
`pf_bridge\replay\pf_hyp012_probe.py`: proven R17 world-entry replay (canonical
demo capture, 10 frames, 0.34/1.75 cadence, GAME port only) reached
`start=True teleport=True runtime_ack=True`, then sent the byte-exact captured
LogoutVital frames (44B each, recovered from the GT-002 raw capture).

- **Subcode 01** (lease 5): server logged
  `SENT label=HYP_PF_012_LOGOUT_SUBCODE01_ACK_AFTER_CLEAN_CLOSE frame_bytes=46
  delay=0.00 late_ms=0.2`; the probe received that 46B frame as the **first**
  frame after the logout send, sha256 **equal to the composed pin**
  `9B417B5F..3D0A`.
- **Subcode 03** (fresh connection, lease 6): same shape, ack sha256 equal to
  pin `AB172DFF..6696`, `late_ms=0.2`.
- **Dispatch silence after ack, on the real wire**: before the logout, empty
  runtime polls provoked HYP-PF-009 keepalive replies (4 observed across both
  passes). After the ack, the same empty poll produced **zero** dispatch
  frames in a 4 s window on both passes. The only post-ack traffic was the
  frozen v141 clock-driven transport `HEARTBEAT` (24B, sha `B4F6CFA2..ACB1`,
  ~2 s cadence) which also ran before the logout, is not dispatch output, and
  is unchanged by this claim.
- **DB layer** (read-only copy after both passes): `sessions` 4 → **6**, both
  new rows with `selected_character_id` set; **open sessions = 0** (both new
  leases have `closed_at`); `max(lease_generation)` 4 → 6;
  `PRAGMA integrity_check = ok`; backpack rows `[(0,1,2),(1,2,1),(3,4,1)]`
  byte-identical to BEFORE; `character_positions.updated_at` unchanged
  (`2026-08-17T05:32:03Z`) — no table other than `sessions` moved.
- **Close-before-ack ordering — direct runtime timestamps (job 077 rerun,
  19:09–19:10, fresh canonical copy, probe exit 0, all criteria green)**:
  lease 5 (subcode 01) `closed_at 12:09:59.207Z` vs server ack SENT
  `12:09:59.223Z` — the close committed **16 ms before** the ack left; lease 6
  (subcode 03) `closed_at 12:10:24.784Z` vs ack `12:10:24.797Z` (**13 ms
  before**). Both sockets stayed open ~10 s longer (post-ack probe windows),
  so `closed_at` provably belongs to the acknowledged logout, not the socket
  teardown. Server stderr: 0 bytes. The same ordering is pinned at the
  loopback layer (`test_logout_hypothesis.py`: ack returned only after
  `closed_at` commits; the later socket-teardown close returns `False`).
- Probe run 076 exited 3 by its own verdict logic — it wrongly counted the
  pre-existing 24B clock heartbeat as dispatch traffic. The frame-level sha
  data in `outbox\076_probe_20260817_185129.json` already contained the
  evidence quoted above; run 077 with the corrected criteria (heartbeat
  excluded by its pinned sha) reproduced everything at exit 0:
  `ack_byte_exact=true` and `post_ack_dispatch_frames=0` on both passes.

Artifacts: `pf_bridge\outbox\076_hyp012_headless.utf8.txt`,
`outbox\076_probe_20260817_185129.json`,
`GameClient\capture_hyp012_20260817_185129\` (server console + GAME_LIVE +
GAME_EVENTS_LIVE), run DB `state\pirateforce_hyp012_20260817_185129.sqlite3`,
backup `pf_bridge\backup\pirateforce_before_hyp012_20260817_185129.sqlite3`.

## Nonclaims

1. No client-observable claim: real-client exit / character-select return on
   this ack is unmeasured (attended big round item).
2. No claim about the original server's logout response bytes or teardown
   ordering (unknowable from the corpus).
3. No claim for subcodes other than 01/03 or payload variants (fail closed).
4. No production or default-mode behavior: `production_allowed=false`, the
   lane is unreachable without the opt-in scenario flag.
5. The clean close writes `sessions.closed_at` only; no position rewrite is
   part of this claim (movement persistence is a separate accepted domain).
