# LANE-B round `bdcmkf` (COMBAT)

Opened 2026-09-01T08:36+07:00 (`TZ=Asia/Bangkok date`), round body written 2026-09-01T08:45+07:00
(scheduled, no attended session watching).
Branch: `claude/determined-brown-bdcmkf` (this repo), `claude/wonderful-gauss-bdcmkf` (pf_bridge)
Previous LANE-B round: `0t89ae` (`pirate-force-server#451` / `pf_bridge#679`) -- both confirmed
`merged=true` via the GitHub API before this round started (step A of the addendum), so no cherry-pick
recovery was needed.

## Player-visible difference from yesterday

**None.** This round does not touch `runtime.py`, `app.py`, or `field_mobs._SCENE_TABLE_MODULES` --
it is a prose+test change inside `mob_pickup.py`, same shape as round `0t89ae`'s NONCLAIM 16 fix, on a
different NONCLAIM item that was still genuinely open.

## Step B (mailbox) -- checked HEAD before starting

`ADDRESSEE: LANE-B` / `CHIEF-TO-LANE-B` / `LANE-A-TO-LANE-B` letters without a matching
`.CONSUMED.txt`: found exactly one new one, written after round `0t89ae` closed (07:47) and before
this round opened (08:36):

`notes_to_chief/20260901_0807_CHIEF-REPLY-bg0015-ai-tables-queued-owner-ruling-escalated-to-coo.md`
(chief round `ts0deo`, R282, 08:07+07:00, `ADDRESSEE: LANE-B, COO`)

Content, in order:
- **(a)** chief's own first draft of that letter was wrong (opened `RE-133` against this lane without
  checking the mailbox for a later letter from the same lane that had already closed it) -- pf-adversary
  caught it before commit on the chief's side and the letter says so; re-verified live at this round's
  HEAD: `ai_rows_missing_for_scene14()` -> `missing_combat: ()`, `missing_wander: ()`, matching what
  round `n8kq4r` shipped. Nothing for LANE-B to do here -- already closed.
- **(b)** death ruling for Bg0015's 7 templates (343/345/348/350/353/355/924) -- escalated to COO,
  still unanswered. Not this lane's call to make.
- **(c)** ownership of "gate 1" (registering Bg0015 into `field_mobs._SCENE_TABLE_MODULES`) --
  escalated to COO alongside (b). LANE-B is told explicitly: do not register it until both are answered.
- CORE-REQUEST address correction (`runtime.py:7501` is scene 2's arrival branch, not scene 14's; the
  real scene-14 site is `runtime.py:7626`, `lane_hooks.scene_census_composer`, already wired) --
  informational, no action needed.
- `DropLedger.looted` -- acknowledged, tied to `GT-146`/BUILD-006, nothing to do now.

**No new action item for LANE-B.** Consumed: stub `.CONSUMED.txt` written next to the original, copy
moved to `consumed/`.

Re-checked the four Bg0015 gates fresh at this round's HEAD (same method round `0t89ae` used):
1. `_SCENE_TABLE_MODULES` still has exactly `field_mob_tables` (bg0001) and `field_mob_tables_bg0002`
   -- **gate 1 still closed**, blocked on the COO ruling above.
2. `mob_aggro.ATTACK_INTENT_DELIVERABLE` still `False` at line 224 -- **gate 2 still closed**.
3. `grep -n "mob_pickup_persist\|pickup_and_persist" src/pirateforce_foundation/runtime.py` -- still no
   hits -- **gate `mob_pickup_persist` still closed** (`COO-DECISION 20260901_0245`).
4. No new commits touching `mob_ai_control.py`/`mob_ai_scheduler.py`'s real dispatch since round
   `h40iwu`.

**All four gates unchanged, all blocked on decisions outside this lane.**

## Work done instead (rule F: no buildable surface in the gated combat path this round either)

`mob_pickup.py`'s `MOB_PICKUP_NONCLAIMS` carries item 15, labelled `[OPEN RISK, NOT MEASURED -
flagged, not fixed, this round (\`37ts2b\`)]` since that round: nothing in `BagCell.commit_pickup`
checks that `claim.claimant_identity` (the identity that killed the mob and is claiming the drop) is
the same identity the `BagCell`'s own `character_id` belongs to. `resolve_claim` only checks the claim
against the DROP's `killer_identity`; `commit_pickup` only checks that `bag_cell` is a typed `BagCell`.
A claim killed by one identity can be committed into a totally different character's open `BagCell`
with nothing refusing it -- and until this round, that was asserted in prose but never run.

Wrote `tests/test_mob_pickup.py::test_nothing_binds_the_claim_identity_to_the_bagcells_own_character`:
opens a `BagCell` for `CHARACTER` (77), builds a drop killed by `STRANGER` (0x750060, a different
identity), claims it as `STRANGER`, and asserts the pickup is granted with `row_write.character_id ==
CHARACTER` and `row_write.claimant_identity == STRANGER` both true -- i.e. the mismatch goes through
uncaught. This does not fix the gap (NONCLAIM 15 itself says the fix, if any, belongs to `runtime.py`
or is an open COO design question -- not this module's to decide), it only turns "not measured" into
measured, same pattern round `1yj0j0` used for NONCLAIM 16.

Updated NONCLAIM 15's own label in `MOB_PICKUP_NONCLAIMS` to `[MEASURED BY EXECUTION (round
\`bdcmkf\`, tests/test_mob_pickup.py::test_nothing_binds_the_claim_identity_to_the_bagcells_own_
character), not fixed; the OPEN RISK / flagged-this-round wording is from round \`37ts2b\` and is
stale -- this claim has since been run, not merely read]`. The risk description itself (the paragraph
after the label) is untouched -- it was already accurate, only the label calling it "unmeasured" was
now wrong. `grep -rn "37ts2b\|bag_cell TO THE CLAIMANT" src tests` before editing confirmed nothing
else quotes the old label verbatim, so nothing else breaks from the wording change.

**Pin file**: `MOB_PICKUP_NONCLAIMS` is part of `pin_document()`, pinned by `scenarios/
combat_pickup_001.json` (`tests/test_mob_pickup.py::test_the_shipped_pin_file_is_what_the_code_
computes`). Confirmed the guard actually fires (ran red before regenerating), then regenerated the
pin file from `pin_document()` itself -- same one-liner round `0t89ae` used -- rather than hand-editing
JSON. `git diff scenarios/combat_pickup_001.json` shows exactly 1 line changed (the NONCLAIM 15 line).

## Tests

```
Targeted (files touched): tests/test_mob_pickup.py tests/test_mob_pickup_persist.py
  -> 117 passed, 133 subtests passed (1.67s) -- +1 passed vs round 0t89ae's baseline of 116, exactly
     the one new test added; pin-file test measured red before the regenerate, green after.
Full suite after: 6160 passed, 323 skipped, 13141 subtests passed, 0 failed (228.57s)
  (round 0t89ae reported 6153 passed / 327 skipped for the same suite -- a difference of +7 passed /
  -4 skipped that the targeted run above already accounts for as +1; the rest matches the same
  environment-dependent `[precondition:client_image]` skip/pass toggling round 0t89ae's own letter
  flagged, not this round's two-file diff -- targeted run is the number that actually isolates this
  diff)
git diff --check: clean
```

## Process note -- pf-adversary

No separate pf-adversary tool/agent callable this session (same as prior rounds). Did what
pf-adversary would check itself: (a) grepped for every verbatim quote of the old NONCLAIM 15 label
text before editing, confirmed nothing else references it; (b) ran the pin-file test BEFORE
regenerating and watched it go red, confirming the guard is live and not just present, before writing
the new pin; (c) confirmed both touched files stay cp874-encodable and ASCII (`str.encode('cp874')`
and `str.encode('ascii')` both succeed on both files); (d) confirmed `git diff --check` is clean
(no trailing-whitespace/whitespace-error noise).

## Numbers measured

```
Files touched (pirate-force-server), 4 total:
  src/pirateforce_foundation/mob_pickup.py       [NONCLAIM 15 label only, no logic/constant changed]
  tests/test_mob_pickup.py                        [+1 test, no existing test changed]
  scenarios/combat_pickup_001.json                [regenerated from pin_document() -- 1 line changed]
  rounds/B_20260901_0845_bdcmkf_nonclaim15-identity-binding-measured.md [this file]
Working code behaviour: untouched -- this is a prose+test-only change, zero logic lines changed.
```

`current/pf_login_game_server_v141.py`: untouched (read-only via `load_legacy` to regenerate the pin)
· canonical DB/capture corpus: untouched · `runtime.py`/`app.py`: untouched ·
`field_mobs._SCENE_TABLE_MODULES`: untouched (gate 1 still closed) · `scenarios/world_*.json`
(LANE-A's territory): untouched.

## Not yet proven

- The NONCLAIM 15 gap itself is **not fixed**, only measured. It is unreachable in production today
  (`mob_pickup_persist`/`dispatch_pickup_request` still has no call site in `runtime.py` -- gate 3
  above), so there is no live exposure right now, but the gap is real in the module's own public API
  and the fix owner (runtime.py wiring vs. a COO design ruling) is still an open question, same as the
  letter that opened NONCLAIM 15 originally said.
- All four Bg0015 gates -- unchanged from round `0t89ae`, still blocked on the COO ruling escalated in
  `notes_to_chief/20260901_0807_CHIEF-REPLY-*.md`.
- This round's fix changes zero player-visible behaviour, by design -- it is documentation/test
  correctness for whoever wires `runtime.py`'s pickup call site next.

## CORE-REQUEST

none (this round does not touch `runtime.py`/`app.py`)

## Tickets opened for lane C

none

-- LANE-B (COMBAT) round `bdcmkf`
