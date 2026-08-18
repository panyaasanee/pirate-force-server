# PF ITEM-MERGE-001 — HYP-PF-018 occupied-destination same-template merge, headless wire/DB proof (2026-08-18)

One claim (Grade B, wire/DB layer only; the exact V111 direction inside it
is anchored on Grade A original-server capture): behind the new dedicated
merge profile of the existing item-move opt-in flag
(`scenarios/item_move_hypothesis_v111_occupied_merge.json`,
`destination_policy: occupied_by_same_template_merges`,
`different_template_policy: fail_closed_no_reply`,
`free_slot_policy: unchanged_hyp_pf_010`, `production_allowed: false`), a
well-formed strict-parse ItemOperate move request (operation 4, exact
runtime envelope) whose destination slot is occupied by a **different**
governed identity carrying the **same template and identical variant
bytes** merges the source stack into the occupying target: the pure
transition gives the surviving target the summed quantity (u16 wire bound)
and consumes the source item — rejecting any post-state outside the
governed V111 allowlist, which is what keeps the reversed merge direction
fail-closed — the store persists the merge in **one atomic transaction**
against the two named persistence tables (`character_backpack_items`:
target-row quantity update plus source-row delete, each keyed on identity,
slot, template, and pre-merge quantity and rowcount-asserted;
`character_backpacks.updated_at` touched in the same transaction), and the
response reuses the **live-accepted V111 stack-merge delta structure
byte-identically** (first ItemBag collection: exactly one complete ItemAttr
payload for the surviving target, count word 1; second collection: exactly
the consumed source identity, count word 1), queued only after the atomic
commit re-validates the merged post-state. Same-slot requests keep the
silent no-op, free destinations keep the exact HYP-PF-010 lane and its
byte-identical single-item response, a different-template occupant fails
closed with **no reply and no write**, and under the original move profile
— or no scenario at all — the merge lane is unreachable and occupied
destinations keep the pinned HYP-PF-010 fail-closed silence (proven at the
TCP layer by probe pass F).

## Why this shape (design lineage)

- This is the **only occupied-destination behavior with original-server
  evidence**: the V111 capture shows the real client dragging identity 3
  onto occupied slot 0 (same template 2600001) and the original server
  answering with the stack-merge delta — surviving identity 1 at quantity
  2, removal collection naming identity 3 — which the real client accepted
  and rendered live (ITEM-LIFECYCLE-001 runtime pass, persisted). The swap
  hypothesis (HYP-PF-017) had no such anchor; the merge lane generalizes a
  captured behavior instead of designing a new one.
- Until now the server honored that capture only as a **byte-exact frozen
  lane** (`is_exact_merge_request` → `make_item_operate_stack_merge_success`).
  HYP-PF-018 is the generalization: the same merge semantics and the same
  response structure at any governed source/destination slot pair, for
  byte-different strict-parse requests. The composer is pinned byte-for-byte
  against the frozen V141 golden for the exact V111 case, so the
  generalized lane can never drift from the captured instance.
- Under the merge profile the byte-exact V111 request itself parses through
  the generalized strict-parse lane and **converges on the identical frozen
  response bytes** (unit-tested), so the two lanes cannot disagree.
- ITEM-MOVE-CONSUMER-001 (Grade A static) proved the exact client
  response-apply loop applies each ItemAttr of the first ItemBag collection
  as a complete replacement, and the V106/V107 boundary proved the second
  collection's removal role independently; the client accepted exactly this
  merge delta live at V111. What is *not* client-proven is the same
  structure at a destination slot other than 0 — that observation rides
  GT-015 in the attended big round (see Non-claims).

## Envelope choice

The merge response is not a new composition: it is the V111
original-server response reproduced structurally (envelope family
`GSCN_RunTimeProtocolRes` via `make_runtime_vitals`, nested
`ITEM_OPERATE_RES_VITAL` v2, ItemBag base fields, per-item tag layout,
count words 1/1). Frame size 91 bytes in every governed case (82-byte
single-item delta + 9-byte removal entry (`qwordtag`) net of the count-word
difference). For the exact V111 direction the whole frame is byte-equal to
the frozen golden; for other slots only the slot field (and therefore the
bytes) differ. No re-wrapped counts, no invented fields.

## Guard inventory (all fail closed, no reply, no write)

Unknown identity (KeyError), out-of-range slot (ValueError), same-slot
(silent no-op via the free lane), destination not occupied (LookupError —
owned by the free lane in practice), **different template or different
variant bytes (ValueError)**, **reversed direction / any post-state outside
the governed allowlist (ValueError)**, quantity sum beyond the u16 wire
bound (ValueError), occupied under the original or swap profile or without
any scenario (pinned HYP-PF-010 FileExistsError silence / HYP-PF-017 swap
respectively — the profiles are mutually exclusive at the scenario
allowlist), wrong operation / envelope / sequence / selection (existing
generalized-lane guards, unchanged), repository failure (rolls back
atomically, in-memory state unchanged, no bytes queued). Session-level:
the merge gate is a separate boolean that **requires** the item-move gate
(constructor rejects merge-without-move); the read-only scene-load session
rejects the mutation outright.

## Loopback unit layer (sandbox, this round)

`tests/test_item_merge_hypothesis.py` — 21 tests: profile loader (merge
profile loads with `occupied_merge=True`, move/swap profiles unchanged,
six drift variants rejected); pure transition (exact V111 direction
reproduces the merged snapshot, merge lands wherever the target sits,
seven unowned cases raise including different-template, reversed
direction, and the merged snapshot's lack of any same-template pair);
codec (exact case byte-equal to the frozen golden, other slots same
structure/different bytes, guards); session gate; runtime (merge commits
before the byte-exact response with both tables written; the byte-exact
V111 request converges with the frozen lane; merge at a relocated target
slot; free-slot under the merge profile stays HYP-PF-010 byte-identically;
same-slot stays silent; different-template and reversed-direction fail
closed; occupied under the move profile keeps the pinned fail-closure with
the merge repository mocked to prove it is never reached; wrong-sequence;
repository-failure rollback; reconnect projection of the merged state).
Full sandbox suite: 548 passed + 318 subtests, the only failures are the
known sandbox-environment gaps (ledger bidirectional check before this
report existed + one `__notes__` AttributeError on python 3.10 in
`test_server_shutdown`) — the Windows gate is the deciding gate as always.

## Headless runtime layer (sandbox, real server processes, real TCP)

Probe `reports/itemmerge001_smoke/pf_hyp018_merge_probe.py` (stdlib-only,
sockets + scratch DBs only, refuses repo write targets) booted the real app
(`python3 -m pirateforce_foundation.app --db /tmp/...
--item-move-hypothesis-scenario <profile>`) on freshly migrated scratch DBs
and ran six serial passes (each: login → create-if-needed → start_game →
first empty runtime req → heartbeats observed → request):

- **pass A (merge-profile server, DB 1, exact direction id3→slot0)**:
  exactly one non-heartbeat frame, 91 bytes, byte-equal to pin
  `A9899EB9..1541` — which the probe asserts **is the frozen V141 golden**
  (`make_item_operate_stack_merge_success`) before any socket opens; rows
  `[(1,0,2,2600001),(2,1,1,2400901),(4,3,1,2200002)]` (identity 3 row
  deleted, survivor quantity 2, templates preserved); `updated_at` advanced.
- **pass B (second merge-profile server, DB 2, free-slot id1→slot7)**: one
  frame byte-equal to the **unchanged HYP-PF-010 single-item pin**
  `CD70F19E..7AF2` (82 bytes); rows `[(1,7,1),(2,1,1),(3,2,1),(4,3,1)]`.
- **pass C (same server, generalized merge id3→slot7)**: one frame
  byte-equal to the composed merge pin `6210A0FB..BED5` (91 bytes, same
  structure as the golden, different bytes — the first HYP-PF-018 instance
  with no byte-exact capture ancestor); rows `[(1,7,2),(2,1,1),(4,3,1)]`;
  `updated_at` advanced.
- **pass D (same server, different-template id4→slot1)**: silence — zero
  non-heartbeat frames, no EOF, rows and `updated_at` byte-identical
  before/after.
- **pass E (same server, same-slot id2→slot1)**: silence, no write.
- **pass F (third server, original move profile, DB 3, occupied
  same-template id3→slot0)**: silence and **no write** — the pinned
  HYP-PF-010 occupied fail-closure reproduced at the TCP layer; the merge
  lane is unreachable without its dedicated opt-in profile.

Heartbeats were flowing before every request. Verdict JSON + transcript:
`reports/itemmerge001_smoke/ITEM_MERGE001_sandbox_smoke_20260818_105912_probe.json`
(+ transcript alongside). The canonical DB was never opened by the probe.

## Persistence

Both named tables, one transaction: the surviving target row takes the
summed quantity (UPDATE keyed on identity, slot, template, and the
pre-merge quantity, rowcount-asserted), the consumed source row is deleted
(DELETE keyed the same way, rowcount-asserted), and
`character_backpacks.updated_at` is touched in the same transaction; the
post-state is re-validated byte-exact against the pure transition before
commit. No UNIQUE parking is needed (no slot changes hands). Reconnect
projection of the merged state is covered by the unit layer
(`test_merge_and_reconnect_projection`).

## Files touched

- `scenarios/item_move_hypothesis_v111_occupied_merge.json` (new,
  exact-allowlist third profile of the existing flag; the move and swap
  profile JSONs are byte-identical)
- `src/pirateforce_foundation/item_move_hypothesis.py` (third profile +
  `occupied_merge` field; HYP-PF-008 pins and the swap profile untouched)
- `src/pirateforce_foundation/inventory.py` (pure merge transition +
  merge delta composer with the frozen-golden drift pin; single-item and
  swap composers untouched)
- `src/pirateforce_foundation/runtime.py` (occupied branch escalates to the
  merge dispatch only under the merge profile; swap branch and every other
  event string and lane byte-identical)
- `src/pirateforce_foundation/session.py`, `lifecycle.py`, `store.py`
  (gated session method → lifecycle wrapper → atomic store merge)
- `tools/verify_hypothesis_ledger.py` + `docs/HYPOTHESIS_LEDGER.json`
  (HYP-PF-018 registered; ledger PASS 25)
- `tests/test_item_merge_hypothesis.py` (new, 21 tests)
- `docs/FUNCTIONAL_COVERAGE.json`
  (`inventory/stack_merge_and_limit` stays `in_progress`, refs added)

## Non-claims

Not proven here: client display acceptance of the merge delta at any
destination slot other than the captured slot 0 (client acceptance is
proven only for the exact V111 slot-0 response; the generalized rendering
observation rides GT-015 in the attended big round), what request the real
client emits for a same-template drag onto an occupied slot at other
coordinates (only the same operation-4 tuple exercises this lane), the
original server's **generalized** merge policy (arbitrary slots), the
stack ceiling and overflow split-on-merge behavior (no evidence names a
ceiling; sums beyond the u16 wire bound fail closed rather than claim a
game rule), incompatible-template policy beyond fail-closed (the original
server's answer for a different-template drop is unknown — R21 silence),
the reversed merge direction (whose survivor would fall outside the
governed allowlist), displacement-to-free-slot, cross-container or
equipment movement, durability across server restart, and any production
use — `production_allowed` stays false and the lane is unreachable without
the dedicated opt-in profile.
