# PF SESSION_LIMIT001 — Single-session service is a known limitation, recorded by owner decision (2026-08-17)

**One claim.** The v141 server serves exactly one client at a time by structure:
both listeners run `listen(4)` with `accept()` and connection handling in the
same loop, so a second concurrent client is neither rejected nor served — it
waits silently in the TCP backlog until the first connection closes. On
2026-08-17 the project owner recorded this as a **`known_limitation`** (not
`by_design`) and opened hypothesis **HYP-PF-011** so the door to concurrent
multi-client service stays open. Grade B: live wire measurement plus source
mechanism, no client-observable claim.

## Wire evidence (round 18, job 041, 2026-08-17 10:32–10:34)

Headless probe with two concurrent connections against the canonical boot:

| Measurement | Value |
|---|---|
| Connection B on LOGIN port | queued in backlog **42.1 s**, never rejected, never kicked |
| Connection B on GAME port | queued in backlog **22.1 s** |
| B accepted after A closed | within **~30 ms**, then answered byte-correct |
| B session row | opened with `selected_character_id IS NULL` (zero-byte session) |

The wall is at the `accept()` layer, **before any client byte has meaning**, so
two real GameClients must behave the same way: the second hangs silently until
the first exits. What the second client *displays* while queued (loading
screen, error, timeout) remains unmeasured — that is a client-observable layer
question and stays a nonclaim here.

## Source mechanism (read-only, `current/pf_login_game_server_v141.py`)

- `s.listen(4)` appears exactly twice — once per listener (LOGIN and GAME).
- `.accept()` appears exactly twice, each followed by inline handling in the
  same loop: no thread per connection, no selectors, no ThreadingTCPServer.
- Foundation adds a second, independent single-session layer:
  `SQLiteStore.open_session` closes **every** open lease of the same account
  before inserting the new row, so even a future concurrent accept path would
  serialize per-account leases (`tests/test_single_session_limitation.py`
  pins both layers).

## Why `known_limitation` and not `by_design`

Writing `by_design` would assert a client-observable service policy from
wire-layer evidence, which the round-17 rule forbids. No original-server trace
shows how the real deployment handled concurrency; we only know what this
reimplementation structurally does today.

## The interlock warning (round 21, must be read before "fixing" this)

`dispatch` has no exception net (`v141.py` try/finally without except), and the
position-checkpoint lane is the one DB write inside `dispatch` with no
try/except. A stale-lease raise there stops the whole server
(`shutdown.py` `record_thread_failure` → `request_stop`). Today that path is
unreachable **because** the serial accept plus the lease takeover in
`open_session` prevent a second live connection from invalidating the first
mid-dispatch. **The limitation this report records is currently acting as the
interlock for a worse bug.** HYP-PF-011 therefore requires the dispatch
exception boundary and an explicit lease policy as preconditions, not
follow-ups — see the ledger entry's stop rule.

## Owner decision provenance

Recorded 2026-08-17 15:00 ICT through the attended main session
(AskUserQuestion), written to `pf_bridge/CHIEF_CONTINUATION.md` at 15:14:
option (ข) of FINDINGS_R18 — record `known_limitation`, open a pending
hypothesis, release GT-003 from the attended queue. The matrix row
`session_lifecycle/concurrent_multi_client` moves `not_started` → `blocked`
with this report as evidence; it may only move again when HYP-PF-011's
preconditions are met and a real two-client runtime run exists.

## Nonclaims

1. No claim about what the second client renders while queued (unmeasured).
2. No claim that the original server was single-session by policy.
3. No claim about account isolation, remote-player projection, or combat
   between concurrent players — all remain unproven.
4. No claim that fixing N1 alone makes multi-client safe: the lease policy
   (`open_session` takeover) is a separate precondition.

## Evidence manifest

See `PF_SESSION_LIMIT001_SINGLE_SESSION_SERIAL_ACCEPT_KNOWN_LIMITATION_20260817.manifest`
(paths relative to the `Pirate Force` root; the raw probe logs live outside the
repository in `pf_bridge/`, hash-pinned so this report cannot drift from them).
