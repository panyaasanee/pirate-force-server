# PF MOVE-ISOLATION-001 — generalized item move is isolated to the session's own selected character, headless wire/DB proof (2026-08-18)

One claim (wire/DB layer only, no new hypothesis): the generalized free-slot
item move (HYP-PF-010), behind the **default** item-move opt-in profile
(`scenarios/item_move_hypothesis_v111_slot2.json`, `production_allowed: false`),
mutates **only the Backpack of the character the requesting session has itself
selected**. A request cannot name, read, or write another character's items —
not a sibling in the same account, not a character in another account.

This closes the missing runtime evidence called out by the coverage note for
`inventory/move_negative_paths`: *"Cross-account and cross-session isolation
for a generalized move is not covered and has no runtime evidence."* The
isolation is enforced in **two independent layers**, both proven here.

**No new behavior, no new hypothesis.** No source, scenario, ledger entry,
response builder, or store mutation is introduced. The isolation is a standing
property of already-accepted code; this report and its tests prove it to the
wire and the DB.

## The two isolation layers

**Layer 1 — the wire carries no owner field (structural).**
`parse_item_operate_req` decodes the binary-proven `ItemOperateVitalReq`
serializer as exactly one operation byte, one destination dword, and one
item-identity qword, and raises if any trailing bytes remain
(`Cursor.remain() != 0`). The decoded tuple is `(operation, destination_slot,
item_identity)` — there is **no character/owner field** a client could set.
The item identity is resolved *within* the session's own Backpack
(`move_known_item_to_free_slot(self.foundation.backpack, item_identity, …)`),
never against a global item space. A malformed attempt to smuggle an owner id
as a trailing tagged dword is refused, not silently consumed.

**Layer 2 — the persistence guard (defense in depth).**
Every Backpack read and write in the store first calls
`_require_selected_session(db, sid, character_id)`, whose predicate is:

```sql
SELECT 1 FROM sessions s JOIN characters c
  ON c.id = s.selected_character_id AND c.account_id = s.account_id
  AND c.deleted_at IS NULL
WHERE s.id = ? AND s.selected_character_id = ? AND s.closed_at IS NULL
```

It succeeds only when the open session `sid` has itself selected exactly that
`character_id`, and that character belongs to the session's **own account**.
Any other case raises `PermissionError("stale or non-owning character
session")`. Because the target `character_id` passed to the store is always
the session-bound selected character (never a wire value), this layer is not
even reachable with a foreign id through normal input; it is a second wall.

## What was proven over real TCP

Probe `reports/moveisol001_smoke/pf_move_isolation_probe.py` (stdlib only, one
scratch DB migrated fresh **outside** the repo, never launches or touches
GameClient, never opens the canonical DB, refuses any repo-relative write
target).

Setup: one development account with **two characters**, each seeded with its
own **identical** four-item INITIAL Backpack (identity 1 @ slot 0, 2 @ slot 1,
3 @ slot 2, 4 @ slot 3) but a distinct `character_id`. Character A is created
over the wire; the same-account sibling B is duplicated directly in the scratch
DB (distinct selector, name, fingerprint, identity). A separate account with
its own character is also seeded for the cross-account guard check.

Runtime, serial (no concurrency required — respects the single-session-per-
account serial-accept limitation):

- **Session A** logs in, selects character A, reaches runtime-ready, and sends
  one real free-slot move (identity 1 from slot 0 to free slot 4). The server
  returns a committed **82-byte** HYP-PF-010 move-delta frame. Character A's
  rows change to identity 1 at slot 4; **character B's rows and
  `character_backpacks.updated_at` are byte-identical across A's move.**
- **Session B** reconnects (a new session; the prior lease is closed), selects
  character B, and sends the **byte-identical** wire request. Character B's
  rows change; **character A's rows are byte-identical across B's move** — they
  still carry only A's earlier move (identity 1 at slot 4), persisted across
  the reconnect and untouched by B.

The two moves are the **same wire bytes** yet mutate **disjoint row sets**,
demonstrating that `item_identity` resolves inside each session's own Backpack
only.

DB-guard predicate (the exact `_require_selected_session` SQL, exercised
against the seeded rows):

- **accepts** the owning open session for its own selected character;
- **rejects** a character in a **foreign account**;
- **rejects** an **unselected sibling** character in the same account;
- **rejects** a **closed** session.

All checks held; `verdict.ok = true`, exit 0, deterministic across repeated
runs. Full evidence in `reports/moveisol001_smoke/`.

## Offline unit coverage

`tests/test_item_move_generalized.py::ItemMoveIsolationInvariantTests` adds six
fast tests that mirror both layers without a live server:

- Layer 1: the request decodes exactly three unowned fields; a trailing tagged
  dword (the only place an owner id could ride) is refused.
- Layer 2: the guard accepts the owning selected session; rejects a foreign-
  account character on **both read and the generalized move write path**;
  rejects an unselected same-account sibling; rejects a closed session; and the
  foreign character's own owning session still reads it intact.

## Grade and honest scope

**Grade B (isolation facet of `move_negative_paths`).** What is now proven:
cross-**session** / cross-**character** isolation of the generalized move to
the wire and the DB (runtime), plus the structural absence of any owner field
(wire) and the persistence guard's cross-account rejection (exercised against a
seeded second account). The capability stays **`in_progress`**, not
`runtime_pass`, because full cross-**account** isolation at runtime would
require two live **authenticated** accounts, which the development login path
does not yet support — that remaining gap is the standing
`authenticated_multi_account` / persistence-accounts question. The offline
negative coverage for unknown identity, out-of-range slot, malformed, and
replay already existed; this milestone adds the previously-missing isolation
evidence.

**Non-claims.** No production use is enabled (`production_allowed: false`, lane
opt-in only). No concurrent multi-client behavior is claimed (serial accept is
the recorded known limitation). No credential, rate-limit, or ownership policy
for authentication is claimed. The actor-wire bytes of the seeded sibling are
reused opaque bytes (identity rebinding is by `character_id`); this affects
only client rendering, which is out of scope for a Backpack-row isolation
proof and is not asserted here.
