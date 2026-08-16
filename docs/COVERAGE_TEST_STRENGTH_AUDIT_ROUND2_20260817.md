# Coverage test-strength audit, round 2 — 2026-08-17

Follow-up to `COVERAGE_TEST_STRENGTH_AUDIT_20260817.md`. That audit swept all 36
graded rows once and closed the one row with nothing watching it at all. It ended
by naming three rows whose citations looked thin but had not been read closely:

1. `character_management/appearance_and_avatar_binding`
2. `character_management/character_creation`
3. `inventory/stack_merge_and_limit`

This round reads those three against the source seam each one claims. Two needed
a new test module; one did not, and the reason it did not is recorded here rather
than left silent.

**Nothing in `src/` was modified.** No hypothesis ledger entry was touched. The
M3 work in progress in the dirty tree is untouched and unrelated: the seam tested
here (`actor_wire.py`, `CharacterLifecycle.create`, `SQLiteStore.create_character`)
sits entirely below the `session.select_and_start` gate that M3 is changing.

---

## 1. `character_management/appearance_and_avatar_binding` — was under-watched

**The claim (row `notes`):** "Actor and avatar wires are persisted and replayed as
opaque bytes with server-side identity rebinding, which preserves appearance
without decoding it."

**What was watching it:** `tests/test_foundation.py` only.

That module proves the *identity is present*: `read_identity(actor_wire)` returns
the bound pair, the identity tag appears twice in the actor wire and three times
in the start projection, and the avatar wire is a substring of the projection.
`test_character_lifecycle_golden_hashes` additionally pins a sha256 of the actor
wire, which does catch drift.

**What nothing was watching:** the word *preserves*. Every existing test creates
from the same canonical preset with only the name field swapped, so the golden
hash pins one appearance payload rather than the property that an arbitrary
submitted appearance survives. Concretely, the following changes to
`bind_identity_and_selector` / `bind_actor_and_avatar_identity` were not covered:

- rewriting or truncating bytes outside the identity windows;
- writing the identity at the wrong offset while the value still reads back;
- returning the pre-rebind AvatarAttr to the caller;
- dropping the "embedded AvatarAttr boundary is unique" check;
- accepting a malformed common-Attr prefix.

Nothing outside `lifecycle.py` even imported `bind_actor_and_avatar_identity`,
`bind_identity_and_selector` or `bind_common_attr_identity` — those three
functions had no direct test.

**What was added:** `tests/test_character_identity_binding.py` asserts the exact
set of byte offsets that a rebind is allowed to change. For the preset wire that
set is `{1..8, 10}` for the actor identity and selector, plus `{102..109}` for the
embedded AvatarAttr identity, computed from the extractor at run time rather than
hard-coded. Any byte changed outside that set fails the test with the offset named.

One end-to-end test creates two characters whose submitted wires differ in name
*and* in one opaque tail byte, then asserts each stored wire differs from what was
submitted only inside the identity windows, and that the opaque byte each client
submitted is the one that came back. That is the property the row claims.

## 2. `character_management/character_creation` — was under-watched

**The claim (row `notes`):** "The store implements creation with identity binding,
a normalized name key, and a submitted-wire fingerprint, and it is offline-tested."

**What was watching it:** `tests/test_foundation.py` only.

Identity binding was watched. The other two nouns in the claim were not:

- **normalized name key.** The strings `name_key` and `create_fingerprint` appear
  in exactly one existing test, `test_upgrade_from_original_foundation_schema`,
  and there they assert the *migration backfill* for a legacy row
  (`("old", "legacy:1")`). No test asserted what `create()` computes for a live
  creation. `CharacterLifecycle.create` also refuses names that are not already
  NFKC-normalized and stripped, refuses an empty name, and refuses a name that
  disagrees with the name inside the submitted wire. None of those three guards
  had a test.
- **submitted-wire fingerprint.** `test_retry_multi_character_and_account_isolation`
  proves a retry returns the same character id, but it submits the identical wire
  with the identical name, so it cannot distinguish dedup by wire fingerprint from
  dedup by name — and the fingerprint is what the store actually keys on.

**What was added:** tests that pin `create_fingerprint == sha256(submitted_wire)`
(and explicitly *not* the sha of the stored, rebound wire), that pin
`name_key == name.casefold()` while the `name` column keeps its original case,
that create a second character from the same name with one appearance byte changed
and require a *new* row, and that create the same wire under two accounts and
require two rows. The identity derivation
`lo = 0x10000000 + account_id * 0x10000 + selector + 1, hi = 0` is asserted against
the persisted wire rather than only against the returned object.

The normalization guards get one test each, and each one submits a wire that
really does carry the rejected name. Without that, the name/wire agreement guard
catches the input first and the normalization guard could be deleted with the
suite still green — which is exactly what the first draft of this module did, and
what the mutation run below caught.

## 3. `inventory/stack_merge_and_limit` — already watched, no test added

**The claim (row `notes`):** "One exact V111 merge to quantity 2 is runtime-proven
and persisted. The stack ceiling, overflow split-on-merge behavior, and
incompatible-template rejection are unproven."

**Verdict: the single citation is sufficient.** The claim is narrow on purpose and
`tests/test_item_lifecycle.py::test_exact_merge_commits_before_reply_and_survives_reconnect`
covers it directly: it asserts the store returns exactly `MERGED_V111_BACKPACK`,
that `state.item_quantity == 2`, that the source identity is gone from the merged
attr wire, that the commit happens before the reply is built while connection-local
memory is still pre-state, that the merged backpack survives a reconnect, that a
replayed merge produces no second reply, and it pins five sha256 goldens.

The unproven parts of the row — ceiling, overflow, incompatible template — have no
test **and should not have one**, because a test would have to invent behavior the
evidence does not establish. The correct state is a row that says so in `notes`,
which is what it says. No change made.

---

## 4. Mutation results

Nineteen mutations were applied to a copy of `src/pirateforce_foundation` under
`/tmp` and the new module was run against the copy. The repository working tree
was never modified. A mutation "bites" when at least one test fails.

| # | mutation | result | caught by |
|---|---|---|---|
| M00 | none (baseline) | survives, as required | — |
| M01 | selector byte never written | bites | identity/full bind, derived identity |
| M02 | last appearance byte zeroed on bind | bites | two characters keep own appearance |
| M03 | embedded AvatarAttr identity left unbound | bites | avatar rebound, full bind |
| M04 | AvatarAttr uniqueness check dropped | bites | ambiguous avatar refused |
| M05 | pre-rebind AvatarAttr returned to caller | bites | avatar rebound, full bind |
| M06 | identity written one byte off | bites | avatar rebound, fingerprint, derived identity |
| M07 | common-Attr prefix validation relaxed | bites | malformed prefixes refused |
| M08 | name/wire agreement guard removed | bites | name disagreeing with wire refused |
| M09 | NFKC-and-strip guard removed | bites | unnormalized names refused |
| M10 | fingerprint taken from the name, not the wire | bites | fingerprint is sha of wire, retry dedup |
| M11 | `name_key` not casefolded | bites | name key is casefolded |
| M12 | opaque avatar extractor no longer required | bites | extractor required |
| M13 | empty-name guard removed | bites | empty name refused |
| M14 | dedup by `name_key` instead of fingerprint | bites | retry deduped by wire not name |
| M15 | dedup ignores the account scope | bites | fingerprint dedup scoped to account |
| M16 | identity not scoped by account | bites | derived identity, account scoping |
| M17 | normalization switched to NFKD | bites | precomposed name accepted |
| M18 | `name` column stored casefolded | bites | name key vs. name case |
| M19 | selector always 0 instead of first free | bites | derived identity, retry, appearance |

M09, M13 and M17 survived the first draft. M09 and M13 survived because the test
submitted the canonical wire, so the name/wire agreement guard rejected the input
before normalization ran — the tests passed for the wrong reason. M17 survived
because every name used was NFKC- and NFKD-identical. Both were fixed by making
the inputs discriminating, not by weakening the mutation. **A guard that is not
mutation-checked is a guard nobody has confirmed bites**; two of the three
survivors here were tests that looked correct and were not.

## 5. Nonclaims

- This module tests the offline seam only. It does **not** create a character
  through the real client, and `character_creation` stays `in_progress` for that
  reason. No row status, `required` flag, evidence reference or `notes` string was
  changed by this round — only `test_refs` on the two rows above.
- Appearance preservation is proven as *byte preservation outside two identity
  windows*. It is not a claim that the client renders the appearance correctly,
  nor that any appearance field has been decoded. The row says the opposite, and
  that remains true.
- `name_key` is asserted to be computed and stored. It is **not** asserted to be
  enforced as unique, because it is not: the schema permits two live characters
  with the same `name_key` under one account, and
  `test_upgrade_from_original_foundation_schema` already relies on that. Whether
  duplicate names should be rejected is an unanswered design question, not a bug
  this audit found, and it is left alone.
- `OPAQUE_TAIL_OFFSET = 213` is one byte in the preset's opaque tail, chosen
  because it lies outside every window the binder writes. It is a probe, not a
  claim about what that byte means.
