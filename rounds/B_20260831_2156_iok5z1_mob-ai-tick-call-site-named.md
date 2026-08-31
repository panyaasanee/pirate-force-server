# LANE-B round `iok5z1` (COMBAT)

Opened 2026-08-31T21:36+07:00 (scheduled, no human watching). Branch:
`claude/beautiful-carson-iok5z1`. Orchestrator note for this round: steps
2-3 of the end-of-round protocol (PR title/body edit, undraft via MCP) are
the orchestrator's own job this round, not this session's -- this session
only pushes.

## Player-visible change

**None yet.** The new hook file has zero callers in `runtime.py` (pinned by
`tests/test_lane_b_mob_ai_tick.py::test_nothing_in_runtime_py_calls_maybe_
tick_yet`). This round answers the one thing round `256rvs` deliberately
left open -- WHICH existing dispatch point, and WHERE a real player
identity comes from -- with code already reading two production call sites
in `runtime.py`, not a guess.

## What this round found and built

Round `256rvs` (2026-08-31T18:50) built `mob_ai_scheduler.tick_session`
(a pure driver for `mob_ai_control.tick_step`, which had existed since
round `3lzfhw` with zero production callers) and deliberately did NOT name
a concrete `runtime.py` line, because it did not yet know (a) which
existing per-session dispatch point runs on a live cadence, or (b) where a
real player actor-identity number comes from on this connection. Both were
resolved this round by reading, not guessing:

* **Dispatch point**: `runtime.py`'s own `dispatch(self, parsed)` (~line
  5164) already runs once per parsed vital and already threads
  cross-cutting state around `self._dispatch_with_lanes(parsed)` inside
  itself (CORE-REQUEST-GM-030's warp-confirm window does exactly this in
  the same method). Guarding on `parsed.nested_id ==
  legacy.TARGET_POS_VITAL` -- the same constant that method's own GM-warp
  code already compares against a few lines below -- ties a tick to the
  vital a moving player already sends continuously.
* **Player identity**: `((selected.identity_hi & 0xFFFFFFFF) << 32) |
  (selected.identity_lo & 0xFFFFFFFF)` where `selected =
  self.foundation.selected` -- not invented for this round: it is the
  SAME formula `runtime.py`'s own combat dispatch (`performer`, ~line
  4142) and its scene007 EA7D action-ack path (~line 6728) already use for
  "this connection's own actor identity," on paths that already reach real
  players. Reused, not re-derived.

Built `src/pirateforce_foundation/lane_hooks/lane_b_mob_ai_tick.py` (new):
the option-(b) direct-call wrapper (COO-DECISION 20260829_0041 shape,
same as `lane_a_scene_census.py`/`lane_a_choose_npc_scene14.py`) around
`mob_ai_scheduler.tick_session`, since `tick_session` must hand back an
updated register and `lane_hooks.fire()` is report-only by contract. No new
registry needed: `lane_hooks._discover()` already gates ANY `lane_*.py`
file's `production_allowed` flag on import, whether or not it registers a
hook/composer/responder, so a future `runtime.py` call site only needs this
file's bare name (`lane_hooks.module_production_allowed(
"lane_hooks.lane_b_mob_ai_tick")`) and its one function
(`maybe_tick(...)`). The module's own `LANE_B_MOB_AI_TICK_WIRING` constant
carries the exact block to paste, so it lives where a reader of the module
finds it, not only in this file or a PR body.

`maybe_tick` prints one console line per row that ACTUALLY CHANGED PHASE,
not one per row per call: `tick_session` would run on every TargetPos a
moving player sends, and printing all 17 Bg0002 rows every step (this
project's largest per-session roster) would flood the console with
`idle->idle` repeats for the common case. Measured, not assumed:
`tests/test_lane_b_mob_ai_tick.py::test_only_a_phase_transition_prints_a_
row_line` drives a real acquisition and pins that only the rows that
transitioned printed (5 of 17 at the tested position -- more than one
mob shares that offensive group, not the single row an earlier draft of
this test assumed). `test_a_no_op_pass_prints_no_row_lines` pins the
opposite case with bg0001's four practice dummies.

## Containment gap found and fixed while building this

`tests/test_mob_ai_scheduler.py::test_the_scheduler_has_no_importer_yet`
only ever scanned `SRC_ROOT.glob("*.py")` -- the flat top level of
`src/pirateforce_foundation/`, never the `lane_hooks/` subpackage. Adding
this round's new file there would have made that test's "zero importers"
claim silently false while the test kept reporting green: exactly the kind
of undercount this project's own charter names as the defect worth
noticing. Widened to `SRC_ROOT.rglob("*.py")`, renamed to
`test_the_scheduler_has_exactly_the_one_ready_importer`, and the expected
list updated to `["lane_hooks/lane_b_mob_ai_tick.py"]` with a comment
naming the round and the reason for the widening.

## Numbers

```
tests/test_lane_b_mob_ai_tick.py : new, 9 tests, all pass
tests/test_mob_ai_scheduler.py : 1 test renamed + widened (recursive glob),
  still passes
Full suite (pytest tests -q), run twice for a real before/after (git stash,
not just re-run -- a re-run of the same tree proves nothing about this
round's own delta):
  before (git stash, this round's 3 files removed):
    0 failed, 5874 passed, 387 skipped, 11981 subtests passed (122.66s)
  after (git stash pop, this round's changes restored):
    0 failed, 5883 passed, 387 skipped, 11981 subtests passed (124.64s)
  delta: +9 passed, +0 skipped, +0 subtests -- exactly the 9 new test
  methods in tests/test_lane_b_mob_ai_tick.py, nothing else moved
git diff --check: silent
Files touched (pirate-force-server), 3 total:
  src/pirateforce_foundation/lane_hooks/lane_b_mob_ai_tick.py [new]
  tests/test_lane_b_mob_ai_tick.py [new]
  tests/test_mob_ai_scheduler.py [widened containment test]
Plus this file (rounds/B_20260831_2156_iok5z1_mob-ai-tick-call-site-
named.md).
```

`current/pf_login_game_server_v141.py`: read only (grepped for
`last_target_pos`/`identity_hi`/`identity_lo` to confirm the formula this
round reused), never edited. `runtime.py`: read only, never edited -- the
exact insertion is a CORE-REQUEST for chief (see the letter this round
also writes), not done here. Canonical DB: not touched. Capture corpus:
not touched. `scenarios/world_*.json` (lane A's zone): not touched.

## Not yet proven

- No production caller exists yet for `lane_b_mob_ai_tick.maybe_tick` --
  pinned by this round's own test. Wiring it is a `runtime.py` edit and
  therefore chief's, per CORE-REQUEST below.
- Even once wired, this composes no frame (unchanged from `mob_ai_scheduler`
  itself) -- Door B (turning an AI intent into bytes a client renders) is
  still a separate, larger, unbuilt decision. The ASK-COO round `256rvs`
  sent about Door B direction has not been answered as of this round's
  start (checked: no `COO-DECISION` naming `mob_ai_scheduler`/"Door B" in
  `notes_to_chief/` since `256rvs`). This round's work is useful either way
  (it only prepares the AI register to start tracking proactive truth) and
  does not presuppose an answer.
- BUILD-006 final wire still waits on `GT-146` (attended, human-only) --
  unchanged from prior rounds.

## nonclaim

Did not touch `runtime.py`/`app.py`/`current/pf_login_game_server_v141.py`.
Did not touch `scenarios/world_*.json` (lane A's zone). Did not claim a new
on-screen milestone -- the module docstring's own "WHAT THE PLAYER WILL SEE
DIFFERENTLY" section says "nothing today" and a test pins that claim
mechanically.

-- LANE-B (COMBAT) round `iok5z1`
