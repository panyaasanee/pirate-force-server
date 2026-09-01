round 57alcd (chief / LANE-E, cloud, no screen) -- 2026-09-01

## NOW.md check (done first, per protocol)

3 urgent items (P-1/P-2/P-3) + GM-A/UI-A/GM-B/UI-B/census-latch queue. None require a chief.py
change directly except GM-B (COO-ORDER: chief opens a GT entry) -- done, see pf_bridge companion
round file. This round's NOW.md line moved: GM-B (GT-193 opened). P-1/P-2/P-3/UI-A/UI-B/GM-A
untouched -- other lanes' or awaiting Panya's attended test.

## Round-collision guard (section 2)

git fetch --all both repos: no open [LANE-E] PR in either repo at round start. Checked previous
round's ([LANE-E] round 2zr22w / R290) PR fate in both repos: pf_bridge#728 merged=true
(09:12:06Z), pirate-force-server#487 merged=true (09:20:11Z) -- both landed on main, prior round's
"push แล้ว รอ merge" claim confirmed correct this round.

## What this round did (pirate-force-server side)

**RE-157 job 2** (mob-combat announced-actor membership guard) -- delegated to a pf-builder
subagent given the well-bounded spec from `pf_bridge/notes_to_chief/20260830_1111_RE-157-RESULT-*`.
Wired `mob_combat_membership.admits()` into `_dispatch_mob_combat` (`runtime.py:4247-4256`),
right after `target_is_field_mob` and before the cadence branch. Stamped the membership at the
three census-commit points that already know their own outgoing actor identities: bg0002
(`:7941-7947`), lane-composer (`:8204-8210`), bg0001/home (`:8556-8567`). Cleared on GM `/warp`
scene handoff (`:5537-5541`, bumping a new per-session generation counter so a warp back to an
already-visited scene can't replay stale membership).

Added `tests/test_mob_combat_membership_wiring.py` (7 new tests proving admit/refuse/generation-
mismatch/scene-mismatch through the real dispatcher) and fixed/rewrote 19 pre-existing tests across
6 files that assumed the old (weaker) fallback-success behavior the guard now correctly refuses.
Full suite: 6361 passed, 0 failed (subagent's run) -- independently re-verified by chief on the
touched test files directly (85 + 69 = 154 targeted tests, all green) and a fresh full-suite run
in progress at round close (see companion letter/PR body for the final number once it lands).
`tools/verify_hypothesis_ledger.py`: PASS entries=48, no drift.

**pf-adversary review** (mandatory before commit, run in an isolated worktree): confirmed the
fail-closed property genuinely holds (`admits()` never raises), confirmed the guard's single call
site is unconditionally reached before any cadence/ledger mutation with no bypass path, confirmed
the three census-commit stamp sites and the one clear site keep the generation counter and the
membership record in sync, confirmed the three rewritten tests correctly tighten (not weaken) what
they prove, and confirmed the empty-set stamp for lane-composed scenes (scene 14, not yet
`production_allowed`) degrades safely (an empty `frozenset` refuses every identity, same failure
mode as a missing record -- never more permissive).

**Real finding, not yet closed**: the clear/stamp only fires on the GM `/warp` path. The other two
production-live scene-transition mechanisms (`world_travel_gate.py` crossings,
`world_m2_crossing_handoff.py` Columbus M2) never touch `mob_combat_announced_membership`/
`_generation`. Traced statically (not live-reproduced) as fail-closed -- a scene reached via those
paths, if it isn't one of the three already-stamped commit points, refuses ALL combat there for the
rest of the connection, rather than wrongly admitting anything. No GT test currently proves combat
working end-to-end via a non-GM-warp scene entry, so this is not a regression of anything proven,
but it is a real, open scope gap. Wrote to LANE-B (owner of `mob_combat`/combat gameplay) asking
them to choose: accept as a documented limitation, open a CORE-REQUEST for chief to close it, or
propose the exact spec themselves. Not fixed this round -- outside RE-157 job 2's original 3-point
spec, and closing it properly needs a design decision LANE-B is better placed to make than chief
guessing at it under round pressure.

**RE-157 job 1** (TradeCmd active-session stamp) remains completely unbuilt. Queue entry updated
(pf_bridge companion) to say so plainly, so nobody reads job 2 landing as job 1 also being done.

## CORE-REQUEST

Answered RE-189 branches 2/3 (LANE-A, `logout_hypothesis.py` teardown-timer-variant and
ack-first-reorder profiles): granted option (b), LANE-A may edit again under the same 5-condition
spec from the prior one-time grant, with condition 4 (pf-adversary) revised to "chief reviews with
Agent tool at PR-review time" since chief's session has Agent tool access and LANE-A's reported
(twice now) that theirs does not.

No new CORE-REQUEST opened against this repo. WIRED = 5/6 lane_hooks modules
production_allowed=True (lane_a_choose_npc_scene1 intentionally still False) -- unchanged from
prior rounds' reporting, re-verified by direct grep this round, not carried forward blind.

## Mailbox triage (pf_bridge side, see companion round file for the full list)

11 chief-addressed letters stubbed. Several turned out to already be resolved on current main from
earlier rounds (classify_against/issued_through decision, RE-118 closed in queue, 4 Codex doc
corrections already applied per R289's own "2 CODEX-CORRECTION reference updates") -- verified by
reading the actual source, not trusted from the stub claims alone.

## Not proven / nonclaim

- RE-157 job 1 (TradeCmd) not built.
- The scene-transition scope gap above is traced statically, not measured live -- no attended or
  headless session drove a travel-gate/Columbus crossing against the new guard this round.
- GT-193 (companion pf_bridge entry) is PENDING interface, not run -- LANE-DB/LANE-GM have not yet
  shipped the sparse `/speed` path this entry depends on.

## Files touched

- `src/pirateforce_foundation/runtime.py` (RE-157 job 2 guard + 2 new state fields + 3 stamp sites
  + 1 clear site)
- `tests/test_mob_combat_membership_wiring.py` (new)
- `tests/test_gm_warp_position_confirmed.py`, `tests/test_mob_ai_control_dispatch.py`,
  `tests/test_mob_combat_bg0015_gates.py`, `tests/test_mob_combat_cadence_wiring.py`,
  `tests/test_mob_combat_census_wiring.py`, `tests/test_mob_combat_dispatch.py`,
  `tests/test_mob_scene_recompose_wiring.py`, `tests/test_scene_scoped_combat_wiring.py` (fixed)

-- chief (LANE-E) round `57alcd`
