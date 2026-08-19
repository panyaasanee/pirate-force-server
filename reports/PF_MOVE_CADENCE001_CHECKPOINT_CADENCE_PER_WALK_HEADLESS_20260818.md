# MOVE-CADENCE-001 — movement checkpoint cadence per walk, measured headless to the DB layer

Date: 2026-08-18 (chief scheduled round 59)
Scope: one claim. Follows MOVE-AUTHORITY-001 (`856f9e9`) which characterized *who*
has movement authority; this measures *how often* the accepted movement actually
reaches `character_positions`. Closes the cap[1] open note ("กี่ write ต่อ walk,
scene transition, heading") to the wire/DB layer. Client-observable heading at
respawn remains an attended observation (queued under GT-014).

## Claim (Grade B — headless runtime replay of an authentic capture)

> For the GT-005 walk (authentic client, boot1 capture), every inbound
> `TargetPosVital` is the exact v141 singleton shape (29/29); the foundation
> checkpoint gate deduplicates identical positions so exactly **19 of 29** frames
> reach `store.save_position`; replaying those 19 through the **real store code**
> on a copy of the canonical DB reproduces the GT-005 AFTER row byte-for-byte
> (x, y, z, heading). While the player stands still the client re-sends the same
> position and **zero** DB writes occur; while the player moves continuously the
> write rate is bounded at about one write per 2–6 s. The movement lane cannot
> change `scene_id`/`scene_seq` (code-exact), and heading is persisted on every
> write.

Grade rationale: runtime evidence, but driven from a *recorded* authentic capture
through the real gate+store — not a new live client session. The wire→gate→DB
chain is executed for real; only the TCP client end is replayed. Grade B.

## Inputs (all read-only; pinned in the manifest)

| input | role |
|---|---|
| `GameClient\capture_gt005_boot1_20260817_122339\capture_v141\GAME_20260817_122544_319475_53892.txt` | authentic walk capture: 330 inbound frames (hexdump per frame) |
| `GameClient\capture_gt005_boot2_20260817_123551\capture_v141\GAME_20260817_123751_896343_61985.txt` | stand-still control: 42 inbound frames |
| `current\pf_login_game_server_v141.py` | pinned parser (`parse_outer`, `parse_v141_refresh_target_pos`) + heartbeat clock |
| `src\pirateforce_foundation\runtime.py` | checkpoint gate `_checkpoint_exact_target` (both call sites use `durable_target`) |
| `src\pirateforce_foundation\store.py` / `lifecycle.py` | real write path `save_position` (bounds + ownership + UPDATE-in-place) |
| `reports\PF_GT005_..._RUNTIME_PASS_20260817.md` | BEFORE/AFTER row anchors |
| `state\pirateforce.sqlite3` | copied to tmp for the DB-layer replay; canonical file only read |

Tool: `tools\pf_move_cadence001_headless_replay.py` (committed) · full stdout:
`reports\move_cadence001_smoke\replay_output.txt`.

## Measurements

### M1 — wire layer: every walk frame is the exact singleton shape (fact)

Boot1: 330 inbound frames decoded with the pinned v141 parser → **29 TargetPosVital,
29 exact / 0 non-exact / 0 parse errors**. Boot2 (player only stood): 42 inbound
frames, **0 TargetPosVital** — matches GT-005 A2 from the console side.

### M2 — gate layer: 19 writes, 10 dedup skips (fact)

Replaying the exact foundation rule (write iff `(x,y,z,heading)` differs from the
selected position, initial = GT-005 BEFORE row):

- **writes = 19, dedup-skipped = 10** (identical re-sends)
- final simulated position ≡ GT-005 AFTER row `(-8094.6079, -3207.8306, 186.0, 2.4993)` ✓
- `moving` flag: 1 on 5 frames, 0 on 24 — the five `moving=1` frames form one
  continuous run (frames 222–227) with large per-frame deltas (~400–500 units);
  stationary periods re-send the same tuple and are all dedup'd.

### M3 — cadence in seconds (code-exact clock)

The v141 heartbeat worker sends exactly every **2.0 s** (`conn_done.wait(2.0)`,
L7422), giving an in-band clock. TargetPos frames span heartbeat 42→193 ≈ 302 s:

- continuous movement: successive distinct frames arrive 1–3 heartbeats apart →
  **~1 write per 2–6 s** (peak 1 write / 2 s)
- standing still: longest identical stretch = 63 heartbeats ≈ 126 s with **0 writes**
- whole-walk average: 19 writes / ≈302 s ≈ 1 write per 16 s

DB load shape: UPDATE-in-place of one row per character, no idle writes — the
persistence cost of movement is bounded by player action rate, not tick rate.

### M4 — DB layer: real store, real schema, byte-identical result (fact)

The 19 gate-passing positions were driven through `SQLiteStore.save_position`
(the production code path: wire-bounds check, finite check, ownership guard,
UPDATE with rowcount==1 verification) on a `/tmp` copy of the canonical DB with
a synthetic open session for character 1:

```
save_position succeeded ×19 (each rowcount==1)
final row: x=-8094.6079101562 y=-3207.8305664062 z=186.0 h=2.4992544651
== GT-005 AFTER row exactly
```

Canonical DB was only read; its sha256 after the run = `B5557E9F..C9ED`
(unchanged canonical pin).

### M5 — scene transition and heading (code-exact)

- `TargetPosVital` carries **no scene identity** (4×f32 + moving + derived_mask
  only). `_checkpoint_exact_target` constructs the candidate with
  `selected.position.scene_id/scene_seq` inherited → **the movement lane cannot
  change scene**; a scene change must come from another path (today: only the
  StartGame default position; no runtime scene-transition write path exists).
- `heading` is a first-class f32 on the wire (tag 0x2A) and a column in
  `character_positions`; it is written on **every** checkpoint (19/19 here) and
  round-trips into the DB (AFTER h=2.4992544651 = last frame's heading).
  Whether the client visibly *faces* the persisted heading on respawn is
  client-observable → queued as a sub-observation in GT-014.

## Non-claims

- No claim about the client's *send policy* (why it emits a frame when it does —
  waypoint arrival vs sampling): that is client-internal; only the observed
  arrival cadence and its DB consequence are claimed.
- No claim about original-server correction behavior (MOVE-AUTHORITY-001's
  bounded unknown stands; GT-014 provocation remains queued).
- No live-session claim: this replay exercises gate+store, not the TCP listener;
  GT-005 already proved the live end-to-end pass at Grade B.

## Falsifiable predictions for the attended big round (GT-014)

1. During continuous walking the server console will show TargetPosVital roughly
   every 2–6 s, and `character_positions.updated_at` will advance accordingly.
2. Standing still for ≥30 s produces zero `updated_at` movement.
3. After a walk that ends facing a distinct direction, the DB heading equals the
   last TargetPos heading; on next entry the client spawns at that x/y/z (heading
   render = the open observation).

## Integration

- Additive, report-only + one committed tool. No ledger/matrix/src change; the
  cap[1] note closure and matrix wording update ride the next matrix-touching
  commit (same discipline as MOVE-AUTHORITY-001's cap[2] flip).
- Green criteria unchanged (gate 108: pytest 477/0, canonGuard=0, ledger 23,
  domains 8).

## Appended erratum (round 93, 2026-08-20): the tool this report pins was edited, and the manifest line was left alone on purpose

The tool `tools/pf_move_cadence001_headless_replay.py` printed the multiplication
sign and the plus-minus sign on four of its output lines (96, 109, 152, 154).
The console on the machine that runs this project's gate is code page 874, which
cannot encode either character, and an unmappable character does not degrade to a
question mark -- `print()` raises, so the tool would have died mid-run and taken
its test down with it, on the Windows machine only.  Round 86 learned this the
expensive way with an emoji in a different tool; round 92 found these four lines
still sitting here and round 93 replaced the two characters with `x` and `+/-`.
The words carry the meaning and no sentence changed.

Three consequences are recorded rather than smoothed over:

- The tool's bytes moved from `7947 | C78D7C43CAAFAA6982AD8DB7D8637DC8A33F2357BB73D88C986CB59EAB4F4A8C`
  to `8190 | 12AF6098B3A3256063BDF237E561D827399871207C9B9705331E7914830AED86`.
  The line in `.manifest` beside this report still pins the FIRST pair, and that
  is deliberate: an evidence manifest records the bytes that produced the
  evidence, and the run recorded in `reports/move_cadence001_smoke/replay_output.txt`
  was produced by those bytes and by no others.  Re-pinning it to today's file
  would make the manifest agree with the working tree and disagree with history,
  which is the opposite of what it is for.
- `reports/move_cadence001_smoke/replay_output.txt` therefore still contains the
  two characters, because it is a transcript of a run that happened rather than a
  file this project regenerates.  Its pinned size and hash are unchanged.
- **The replay was not re-run.**  Round 93 proved only that what the tool prints
  is now encodable on both machines; it did not execute it, so nothing here
  re-states that the cadence findings above still reproduce.  That check needs
  the GT-005 captures and a throwaway copy of the database, and it is queued
  rather than claimed.
