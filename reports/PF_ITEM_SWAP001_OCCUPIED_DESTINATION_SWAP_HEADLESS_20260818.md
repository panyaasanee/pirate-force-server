# PF ITEM-SWAP-001 — HYP-PF-017 occupied-destination swap, headless wire/DB proof (2026-08-18)

One claim (Grade B, wire/DB layer only): behind the new dedicated swap
profile of the existing item-move opt-in flag
(`scenarios/item_move_hypothesis_v111_occupied_swap.json`,
`destination_policy: occupied_by_different_identity_swaps`,
`free_slot_policy: unchanged_hyp_pf_010`, `production_allowed: false`), a
well-formed strict-parse ItemOperate move request (operation 4, exact runtime
envelope) whose destination slot is occupied by a **different** governed item
identity swaps the two items: the pure transition exchanges exactly the two
`slot` fields and preserves every other ItemAttr field of both items, the
store persists both slot changes in **one atomic transaction** against the
two named persistence tables (`character_backpack_items` +
`character_backpacks.updated_at`, the pair named by GT-002), and the response
reuses the live-accepted ItemOperateVitalRes delta structure with the first
ItemBag collection carrying exactly **two complete ItemAttr payloads** (moved
item first, displaced occupant second, count word 2, trailing collection
count 0), queued only after the atomic commit re-validates the swapped
post-state. Same-slot requests keep the silent no-op, free destinations keep
the exact HYP-PF-010 lane and its byte-identical single-item response, the
exact tracked HYP-PF-008 request keeps its frozen lane, and under the
original item-move profile — or no scenario at all — an occupied destination
stays fail-closed with **no reply and no write**, byte-identical to the
pinned HYP-PF-010 behavior (proven at the TCP layer by probe pass E).
**No client-observable claim is made**: whether the real client renders both
swapped items — and what request it actually emits for an
occupied-destination drag — is exactly GT-015, queued for the next attended
big round.

## Why this shape (design lineage)

- The coverage matrix names `inventory/occupied_destination_policy` as the
  domain's next missing behavior; GT-002 (attended, Grade B) proved the
  generalized free-slot lane live but recorded occupied destinations as
  fail-closed-by-test, not exercised.
- ITEM-MOVE-CONSUMER-001 (Grade A static) proved the exact client
  response-apply loop applies **each ItemAttr of the first ItemBag
  collection as a complete replacement** — clear-by-identity then
  place-by-slot — with no occupancy gate and no old-quantity/old-slot
  comparison. A two-entry delta therefore re-places both swapped items
  correctly **in either order** at the display layer. That report's stop
  rule ("do not infer occupied-slot swap/displacement from the replacement
  helper") is honored by opening this as a new opt-in hypothesis
  (HYP-PF-017) with its own falsification lanes, not as a consumer
  inference; its warning that the client's separate Backpack data collection
  could desync is carried verbatim into the GT-015 pass criteria.
- No original-server traffic shows any occupied-destination move being
  accepted or answered (R21: 23 of 24 ItemOperate shapes produce no reply,
  no write). The original server's policy — swap, displace, reject, or
  silence — is unknown and explicitly not claimed. Swap was chosen as the
  designed hypothesis because it is the only shape the proven consumer
  mechanics support without inventing new client behavior: both entries are
  complete replacements of items the client already displays.

## Envelope choice

The swap response is the GT-002 live-accepted single-item delta with two
changes only: the first collection's count word says 2 and a second complete
ItemAttr payload follows the first. Envelope family
(`GSCN_RunTimeProtocolRes` via `make_runtime_vitals`, nested
`ITEM_OPERATE_RES_VITAL` v2), ItemBag base fields, per-item tag layout, and
the trailing empty second collection are byte-identical to the accepted
82-byte response. Frame sizes: 82 (single) → 108 (swap; +26 = one complete
ItemAttr wire). No re-wrapped counts, no invented fields.

## Guard inventory (all fail closed, no reply, no write)

Unknown identity (KeyError), out-of-range slot (ValueError), same-slot
(silent no-op via the free lane), destination not occupied (LookupError —
cannot be reached in practice: the free lane owns it), occupied under the
original profile or without any scenario (pinned HYP-PF-010
FileExistsError silence), wrong operation / envelope / sequence / selection
(existing generalized-lane guards, unchanged), repository failure
(rolls back atomically, in-memory state unchanged, no bytes queued).
Session-level: the swap gate is a separate boolean that **requires** the
item-move gate (constructor rejects swap-without-move); the read-only
scene-load session rejects the mutation outright.

## Loopback unit layer (sandbox, this round)

`tests/test_item_swap_hypothesis.py` — 17 tests: profile loader
(swap profile loads with `occupied_swap=True`, original profile unchanged,
six drift variants rejected); pure transition (initial + merged contents,
five unowned cases raise); codec (two-item structure vs single-item
baseline, moved-before-displaced order, count word 2, guards); session gate;
runtime (swap commits before the composed two-item response with byte-exact
pins and both tables written; swap-back in the same session; free-slot under
the swap profile stays HYP-PF-010; same-slot stays silent; unknown/range
guards; occupied under the original profile keeps the pinned fail-closure
with the swap repository mocked to prove it is never reached;
wrong-sequence; repository-failure rollback; merged-contents swap +
reconnect projection from the store). Full sandbox suite: 447 tests, the
only failures are the known sandbox-environment gaps (capstone-dependent
static probe loaders + one `__notes__` AttributeError on python 3.10 in
`test_server_shutdown`) — none touched by this change; the Windows gate is
the deciding gate as always.

## Headless runtime layer (sandbox, real server processes, real TCP)

Probe `reports/itemswap001_smoke/pf_hyp017_swap_probe.py` (stdlib-only,
sockets + scratch DBs only, refuses repo write targets) booted the real app
(`python3 -m pirateforce_foundation.app --db /tmp/... 
--item-move-hypothesis-scenario <profile>`) on freshly migrated scratch DBs
and ran five serial passes (each: login → create-if-needed → start_game →
first empty runtime req → heartbeats observed → request):

- **pass A (swap-profile server, occupied id1→slot1)**: exactly one
  non-heartbeat frame, 108 bytes, byte-equal to pin
  `2A9CC0C4..76E7A9`; rows `[(1,1),(2,0),(3,2),(4,3)]`
  (identity, slot, quantity and template preserved); `updated_at` advanced.
- **pass B (swap back, id1→slot0)**: one frame byte-equal to pin
  `73FAF8EC..17B6B1`; rows restored to the initial layout; write recorded.
- **pass C (free-slot id4→slot7 under the swap profile)**: one frame
  byte-equal to the **unchanged HYP-PF-010 single-item pin**
  `F5FBC471..AD6DFCC` (82 bytes); rows `[(1,0),(2,1),(3,2),(4,7)]`.
- **pass D (same-slot id2→slot1)**: silence — zero non-heartbeat frames, no
  EOF, rows and `updated_at` byte-identical before/after.
- **pass E (second server, original move profile, second scratch DB,
  occupied id1→slot1)**: silence and **no write** — the pinned HYP-PF-010
  occupied fail-closure reproduced at the TCP layer.

Heartbeats were flowing before every request. Verdict JSON + transcript:
`reports/itemswap001_smoke/ITEM_SWAP001_sandbox_smoke_20260818_075500_probe.json`
(+ transcript alongside). The canonical DB was never opened by the probe.

## Persistence

Both named tables, one transaction: the source row parks on transient slot
65535 (lawful for the column CHECK, invisible outside the transaction) to
satisfy `UNIQUE(character_id,slot)`, the occupant moves into the vacated
slot, the source lands on the destination; every step rowcount-asserted;
post-state re-validated byte-exact against the pure transition before
commit; `character_backpacks.updated_at` touched in the same transaction.
Reconnect projection of the swapped state from the store is covered by the
unit layer (`test_merged_contents_swap_and_reconnect_projection`).

## Files touched

- `scenarios/item_move_hypothesis_v111_occupied_swap.json` (new,
  exact-allowlist second profile of the existing flag; the original profile
  JSON is byte-identical)
- `src/pirateforce_foundation/item_move_hypothesis.py` (second profile +
  `occupied_swap` field; HYP-PF-008 pins untouched)
- `src/pirateforce_foundation/inventory.py` (pure swap transition +
  two-item delta composer; single-item composer untouched)
- `src/pirateforce_foundation/runtime.py` (occupied branch escalates to the
  swap dispatch only under the swap profile; every other event string and
  lane byte-identical)
- `src/pirateforce_foundation/session.py`, `lifecycle.py`, `store.py`
  (gated session method → lifecycle wrapper → atomic store swap)
- `tools/verify_hypothesis_ledger.py` + `docs/HYPOTHESIS_LEDGER.json`
  (HYP-PF-017 registered; ledger PASS 24)
- `tests/test_item_swap_hypothesis.py` (new, 17 tests)
- `docs/FUNCTIONAL_COVERAGE.json`
  (`inventory/occupied_destination_policy` → `in_progress`)

## Non-claims

Not proven here: client display acceptance of the two-item response (and the
client's separate Backpack collection consistency — the CONSUMER-001
warning), what request the real client emits for an occupied-destination
drag (it may gate client-side, emit this operation-4 tuple, or emit a
different operation; only the same-tuple case exercises this lane), the
original server's occupied-destination policy, stack merge/split on
collision (same-template collision still swaps — merging is
`stack_merge_and_limit`'s lane, not this one), displacement-to-free-slot,
cross-container or equipment movement, durability across server restart,
and any production use — `production_allowed` stays false and the lane is
unreachable without the dedicated opt-in profile.
