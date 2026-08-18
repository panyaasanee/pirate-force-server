# PF SAME-SLOT-NOOP-001 — HYP-PF-010 same-slot no-op, replay-safe, headless wire/DB proof (2026-08-18)

One claim (wire/DB layer only, no new hypothesis): behind the **default**
item-move opt-in profile
(`scenarios/item_move_hypothesis_v111_slot2.json`,
`production_allowed: false`), a well-formed strict-parse ItemOperate move
request (operation 4, exact runtime envelope) whose destination slot is the
**item's own current slot** is a silent no-op — no reply frame and no write —
and remains one under repeated replay. This is not a new behavior: HYP-PF-010
already states "same-slot requests are a no-op". The occupied-destination
swap milestone (ITEM-SWAP-001, `9126fb5`) proved same-slot silence once under
the *swap* profile (its probe pass D). This report closes the
`inventory/same_slot_noop` capability by proving the same silence under the
*default* free-slot profile and adding the **replay dimension** the coverage
note explicitly requires ("No response, no write and no replay is the
intended behavior").

**No client-observable claim is made.** The same-slot no-op has no visible
effect by construction, so there is nothing for an attended run to add here;
the capability is a wire/DB invariant.

## Why this shape (design lineage)

- The coverage matrix carried `inventory/same_slot_noop` as **blocked**
  behind "the same ledger review as `move_known_item_any_free_slot`". That
  sibling capability is now `runtime_pass` (HYP-PF-010 is an accepted ledger
  entry), so the blocking review is resolved. The only thing the capability
  still lacked was its own runtime evidence.
- The same-slot no-op is a code path of the already-accepted HYP-PF-010
  free-slot lane, not a new claim: `move_known_item_to_free_slot` returns
  the exact same-slot `None` sentinel when `current.slot == destination_slot`,
  and the runtime dispatcher maps that sentinel to
  `item_move_generalized_same_slot_noop_no_reply` with an empty action list.
  No new ledger entry, scenario file, response builder, or store mutation is
  introduced.
- Under the default profile the same-slot request reaches the no-op through
  the honest routing path: it is not the exact tracked HYP-PF-008 request, so
  `_dispatch_item_move_hypothesis` classifies it `wrong_tuple` and offers it
  to `_dispatch_item_move_generalized`, where the pure transition returns
  `None`. The exact HYP-PF-008 request keeps its frozen lane untouched.

## What was proven over real TCP

Probe `reports/samesnoop001_smoke/pf_same_slot_noop_probe.py` (stdlib only,
one scratch DB migrated fresh **outside** the repo, never launches or touches
GameClient, never opens the canonical DB, refuses any repo-relative write
target). One default-profile server process was booted over real TCP on the
fixed GAME port; a fresh four-item initial Backpack (identity 1 at slot 0,
identity 2 at slot 1, identity 3 at slot 2, identity 4 at slot 3) was reached
through the runtime-ready handshake.

Three same-slot targets — identity 1 → slot 0, identity 2 → slot 1,
identity 4 → slot 3 (each an item's own slot) — were each sent **three times**
on one connection (nine same-slot sends total). For every send:

- exactly **zero** non-heartbeat frames were received (silent, no reply);
- no connection EOF;
- a heartbeat was observed before the request window (liveness control), so
  silence is a decision, not a dead socket.

Across all three replays of every target, the two persistence tables were
byte-identical between the read taken immediately after runtime-ready and the
read taken after the final replay:

- `character_backpack_items` rows (identity, slot, quantity, template)
  unchanged;
- `character_backpacks.updated_at` unchanged.

Each target's pure transition was asserted to return the exact same-slot
`None` before any wire byte was sent, tying the wire silence to the accepted
transition.

Verdict JSON: `verdict.ok = true`, every `*_ok = true`,
`heartbeat_seen_before_every_request = true`. Evidence:
`reports/samesnoop001_smoke/SAME_SLOT_NOOP001_sandbox_smoke_20260818_082212_probe.json`
and `..._transcript.txt`.

## Falsification lanes (what would have failed this)

- Any same-slot send producing a non-heartbeat frame → `silent_no_reply`
  false → probe exit 3.
- Any change to `character_backpack_items` rows or
  `character_backpacks.updated_at` across the replays → `no_write` false →
  exit 3.
- The pure transition returning anything other than `None` for a same-slot
  target → assertion failure before the wire step.
- Unit test `test_same_slot_noop_is_idempotent_under_replay`
  (`tests/test_item_move_generalized.py`) dispatches each same-slot target
  three times against the store-backed runtime and asserts empty action
  lists, the `item_move_generalized_same_slot_noop_no_reply` event, an
  unchanged Backpack and unchanged DB rows, and that both the generalized and
  hypothesis move counts stay 0.

## Non-claims

- No original-server policy for same-slot moves is claimed; this pins the
  foundation server's governed behavior only.
- No occupied-destination, free-slot, stack, split, equip, drop, or
  cross-container behavior is asserted here — those remain their own
  capabilities.
- No client-observable behavior is claimed (none exists for a no-op).

## Governance

- Coverage matrix: `inventory/same_slot_noop` moved `blocked → runtime_pass`
  with the probe, transcript, unit test, and this report as evidence.
- Ledger: no new entry. Same-slot no-op is existing accepted HYP-PF-010
  behavior; this report is additive runtime evidence for it.
- Seam: `tests/test_foundation_legacy_seam.py` run before committing the new
  `.manifest` (rule adopted round 64).
