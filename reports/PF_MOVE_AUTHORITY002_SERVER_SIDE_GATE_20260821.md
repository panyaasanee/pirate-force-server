# PF MOVE-AUTHORITY-002 - the server-side gate on the local player's position

- **Checkpoint**: MOVE-AUTHORITY-002 (HYP-PF-030)
- **Round**: chief round 116 (cloud), 2026-08-21 (+07:00)
- **Machine**: Claude Code Routine cloud clone, Linux 6.18 x86_64, Python 3.11.15,
  pytest 9.1.1. No client image, no capture corpus, no canonical database exist here.
- **Grade claimed**: none. No coverage row moves on this checkpoint.

## 1. What this checkpoint closes, and what it does not

`docs/FUNCTIONAL_COVERAGE.json` states the movement gap in one sentence: the server
"accepts client-reported positions without any validation". MOVE-AUTHORITY-001
(round 72) characterized the transport that gap rides - TargetPosVital `0x2A90`, four
f32 then two u8, decoded by `parse_v141_refresh_target_pos` - and stopped there on
purpose: "the authority model itself is uncaptured".

This checkpoint builds that authority model as OUR OWN design and wires it behind an
opt-in scenario. It can do exactly one thing: **refuse the durable write**. It cannot
and does not send a corrective reposition, because no captured frame, producer or
client-side consumer for a server-initiated correction has ever been found. Refusing
to write invents nothing; composing a correction would invent a wire.

## 2. What is proven here, and at which layer

**Wire / DB layer (headless, this machine):**

- `tests/test_move_authority_dispatch.py` (20 tests) drives the REAL
  `make_state_class` path with the opt-in scenario and a hand-cranked clock:
  - the FIRST reading of a connection is measured against the authoritative
    character row - the baseline is seeded from the row, not from whatever the
    client says first;
  - a refused reading leaves the row byte-identical, records one named
    `move_authority_hypothesis_<reason>_no_write` event, and never becomes the
    baseline the next reading is measured against;
  - an admitted reading is recorded ONLY AFTER the durable write survived: a
    checkpoint that raises (stale or stolen lease) leaves no admitted event, no
    counter movement and no moved baseline;
  - a server-initiated teleport reopens the one-reading grace window, so the frozen
    dispatcher moving the player itself cannot freeze the durable row for the rest
    of the session;
  - for the frame in hand the gated and ungated sessions return the **same action
    list** - the gate withholds a write, it never replies;
  - the withheld write **is** visible in the next login's StartGame bytes, because
    the frozen projector composes them from the character row. That is proven here,
    not deferred to the attended test;
  - with the scenario absent no lane event appears and the write path is exactly the
    frozen one MOVE-AUTHORITY-001 characterized.
- `tests/test_move_authority_hypothesis.py` (43 tests) proves the ladder and its
  ORDER offline, the scenario file's role as a permission token, the containment of
  the module - and replays the one authentic walk this project holds (below).
- `tools/verify_move_authority_gate.py` re-derives the arithmetic independently
  (its own `hypot`, its own ceiling): **87 guards, RESULT: PASS**. The suite runs it
  and also runs a deliberately broken copy to prove it can go red.

**Client-observable layer: NOTHING IS PROVEN.** No client has ever been run against
this lane. What a real client does when the position it reported is quietly not
persisted - keep walking, snap back, or not care - is undecidable from static
analysis and from any headless run. That is the queued attended test (GT-041).

**Where the lane's events live, stated plainly:** `move_authority_hypothesis_*`
events are appended to the in-memory `state.events` list. Nothing in `src/` prints
that list, and this lane emits no frame, so **a person watching the server console
sees nothing new**. The two signals a tester can actually collect are the raw GAME
log (every reported `TargetPosVital`) and the `character_positions` row. The
signature of a refusal is a position that appears in the log and never in the row.

## 3. The ladder (OUR DESIGN, in this order)

Clock-free checks come first on purpose: a verdict that does not depend on a clock is
reproducible from the frames alone.

| # | condition | verdict | reachable through the dispatcher? |
|---|---|---|---|
| 1 | malformed argument or unknown policy | refuse `malformed_report` | no - the parser rejects those frames first |
| 2 | any non-finite coordinate | refuse `nonfinite_component` | no - same reason |
| 3 | grace window open | accept `teleport_grace` | yes, once per server teleport |
| 4 | no previously admitted position | accept `anchor` | no - the runtime seeds from the row |
| 5 | no displacement at all | accept `stationary` | yes |
| 6 | moving flag says standing, yet moved | refuse `moving_flag_inconsistent` | only if a profile enables it; the shipped one does not |
| 7 | vertical delta over budget | refuse `vertical_over_budget` | yes |
| 8 | one step over the step budget | refuse `step_over_budget` | yes |
| 9 | elapsed missing, unusable or negative | refuse `nonpositive_elapsed` | no - the runtime always measures |
| 10 | elapsed below the measurable floor | accept `clock_too_coarse` | yes |
| 11 | speed over budget plus tolerance | refuse `speed_over_budget` | yes |
| 12 | otherwise | accept `within_budget` | yes |

Rungs 1, 2, 4 and 9 are defence in depth, not dead weight: they are the module's
fail-closed contract for any caller, and the offline suite exercises all of them.

Budgets shipped in `scenarios/move_authority_hypothesis_speed_gate.json`:
`max_step_units 2000.0`, `max_speed_units_per_second 1200.0`,
`max_vertical_step_units 400.0`, `speed_tolerance_ratio 0.25`,
`min_measurable_elapsed_seconds 0.5`, `enforce_moving_flag false`,
`teleport_grace_reports 1`.

## 4. The one authentic walk, and the two budgets it falsified before shipping

`reports/move_cadence001_smoke/replay_output.txt` (MOVE-CADENCE-001, round 74) is the
committed per-reading table of the authentic GT-005 boot1 walk: 29 TargetPosVital
readings, 19 writes, 10 dedup skips, with a heartbeat index that gives a 2.0 s clock.
`tests/test_move_authority_hypothesis.py` replays all 29 through this ladder. Two
budgets did not survive that replay and were changed before anything was committed:

1. **`enforce_moving_flag` ships FALSE.** The client set `moving` on five of the 29
   readings while moving through nineteen distinct positions. With the rung enabled
   the replay refuses **23 of 29** readings, all `moving_flag_inconsistent`. The flag
   is not a statement about whether the player is walking.
2. **An elapsed below `min_measurable_elapsed_seconds` is an accept, not a
   division.** Readings 60 and 62 share heartbeat 43, so the measured elapsed is
   0.0 and the reading was refused as `nonpositive_elapsed` on an ordinary walk.
   With a real monotonic clock the same pair yields a tiny positive elapsed whose
   quotient is a huge apparent speed - the same false refusal wearing another name.

With the shipped profile the replay refuses **nothing**: 1 anchor, 17 `within_budget`,
1 `clock_too_coarse`, 10 `stationary`. Measured across that walk: largest single-step
horizontal **538.4** (budget 2000), largest speed **269.2 u/s** (tolerated ceiling
1500), largest vertical step **8.0** (budget 400). That is headroom against one real
walk, not validation of the numbers.

**Where the numbers do NOT come from.** The client's const data carries
`n_SPEED_WALK` / `n_SPEED_RUN` columns for MOBS
(`pf_bridge/FACTPACK_R100_CONSTDATA_MONSTER_LOOT.md` lines 179-180 and 232). Those are
MOB columns in unknown units and there is no PLAYER speed column behind them. **They
are not the source of any threshold in this lane** and must never be cited as one.

## 5. Known gaps, stated rather than hidden

1. **One unmeasured reading per server-initiated teleport.** Grace exists because the
   server itself moves the player (scene entry, and the V137 marker transport
   mid-session, about 2340 units horizontally and 448 vertically from spawn) and the
   gate's baseline is stale by definition at that moment. During that one reading
   nothing is measured, so a client that lies in exactly that window writes an
   arbitrary position, and reconnecting re-arms it once. Closing it needs the
   teleport's DESTINATION, which the frozen dispatcher publishes only as a label.
   Pinned by a test that names it a gap.
2. **A burst below the clock floor outruns the speed budget.** Readings arriving
   faster than `min_measurable_elapsed_seconds` are bounded only by
   `max_step_units` each. Closing it needs a windowed accumulator.
3. **Vertical speed is unbounded.** Only horizontal displacement is divided by
   elapsed time.
4. **The gate sits on one caller, not on the write.** `lifecycle.exit` is a second
   writer of the same row; nothing in `src/` calls it today, and a test pins that
   fact so a future logout lane cannot reintroduce the bypass silently.
5. **One event per reading grows an unbounded in-memory list.** The measured cadence
   is about one reading per 2-6 s while moving (19 writes over ~302 s), so this is
   tens of strings per minute of play, on a list the frozen dispatcher already
   appends to twice per reading. Recorded, not fixed.

## 6. Non-claims that travel with every future citation of this checkpoint

1. This is not the original server's movement policy. That policy is unrecoverable
   and is not approximated here.
2. No client has ever been shown one byte of this lane, because it emits none.
3. Refusing a write is not collision, terrain or line-of-sight validation.
4. `production_allowed` is false and the coverage grade does not move.
5. The gate is mutually exclusive with every other scenario mode, so nothing about
   how it composes with another opt-in lane is proven.
6. The budgets are unvalidated against any real walk except the single 29-reading
   trace above, which is one route, one player, one boot.

## 7. Reproduce

```
python3 -m pytest tests/test_move_authority_hypothesis.py tests/test_move_authority_dispatch.py -q
python3 tools/verify_move_authority_gate.py
```
