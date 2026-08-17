# GT-002 — the real client's free-slot move is accepted end to end by HYP-PF-010

Date: 2026-08-17
Scope: one attended session driven through the real `GameClient.local.bin`
against a fresh, never-merged copy of the canonical database, at HEAD
`55c7c59`, with the server booted under the opt-in
`--item-move-hypothesis-scenario` flag. One claim only; no ledger entry is
edited, `production_allowed` stays `false`, and every negative path stays
fail-closed exactly as landed by M4.

## Result

**Grade B runtime pass** for one claim:

> At HEAD `55c7c59`, a real-client drag of the known item (identity 1) from
> slot 0 to the free slot 10 is accepted end to end under the opt-in scenario:
> the client emits one `ItemOperateVitalReq` wire frame, the server answers it
> with an explicit HYP-PF-010 commit response, both persistence tables record
> the move (`character_backpack_items` slot update + `character_backpacks`
> touched `updated_at`, the pair named by `store.py:360`), and a second client
> logging in afterwards renders the item at slot 10 from server state.

This is the first real-client acceptance evidence for the generalized
free-slot move that `HYP-PF-008`/`HYP-PF-010.evidence_gap` called for — the
evidence static work could no longer produce. The slot-0 origin was chosen
deliberately: HYP-PF-008's replayed capture frame moves from slot 2, so a
slot-0 drag cannot be satisfied by the old exact-match lane and must traverse
the generalized path landed in M3/M4 (`runtime.py` → 
`session.move_backpack_item_to_free_slot`).

## Run identity

| | value |
|---|---|
| HEAD under test | `55c7c59` |
| database | run copy `state\pirateforce_gt002_20260817_163028.sqlite3`, taken from a canonical whose pre-run sha `CACE7F7755E79AF0C2E637BC6C09C131E6152436F3141E136BC457ECA74DF493` matched the pin; never merged before this run |
| pre-test backup | `pf_bridge\backup\pirateforce_before_gt002_20260817_163028.sqlite3` |
| boot | direct `pirateforce_foundation.app` boot (the launcher does not forward the flag) with `--item-move-hypothesis-scenario scenarios\item_move_hypothesis_v111_slot2.json`, visible console, `-SecondPasswordMode bypass` |
| capture root | `GameClient\capture_gt002_20260817_163028` |
| shim / server PID | 13428 / 9196 |
| client PIDs | 6844 (move leg, 16:30) · 2828 (reconnect leg, 16:38) — both window title `Pirate Force` |
| jobs | `067` (boot + client), `068` (reconnect client), `069` (teardown; ran 17:26 after the stuck client2 was ended by the user) |
| driver | attended session, Claude as tester, Panya at the machine; computer-use granted tier full at 16:32 while the game window was open, `systemKeyCombos` added 16:54 |

## Measurements

### Layer 1 — wire request

`GAME_EVENTS_LIVE.txt` seq 2 records the drag as capture frame 132:
`ItemOperateVitalReq` id `0x4BED`, `operation=4`, `value32=10`,
`item_identity=1`, payload 16 bytes. This is the generic well-formed shape —
not the HYP-PF-008 exact frame, which names slot 2 as the origin.

### Layer 2 — server response (not silence)

The server console answers the frame immediately:
`[G>] HYP_PF_010_ITEM_MOVE_ID1_TO_FREE_SLOT10_COMMITTED (82 bytes; late=0.3 ms)`.
Contrast with the corpus finding R21 where 23 of 24 `ItemOperate` shapes
produce no reply and no write: this shape both replies and writes.

### Layer 3 — database persistence, both named tables

Run-copy BEFORE (job `067`): items `[(0,1,2600001,2), (1,2,2400901,1),
(3,4,2200002,1)]`, `character_backpacks.updated_at`
`2026-08-16T10:30:39.278511+00:00`, sessions with character 4, max lease 4.
Run-copy AFTER (chief-collected, see the operational note): items
`[(1,2,2400901,1), (3,4,2200002,1), (10,1,2600001,2)]` — identity 1 now at
slot 10 with quantity 2 intact, slot 0 gone — and `updated_at` moved to
`2026-08-17T09:37:24.806094+00:00` (= 16:37:24 ICT, the moment of the drag).
Sessions with a selected character 4→6 (one per client leg), blank sessions 0,
open sessions 0 after teardown, max lease 6, `integrity_check` ok.

### Layer 4 — client-observable, including reconnect

On the drag, client 1 rendered "Adventure Key" at slot 10 at once, slot 0
empty, count unchanged at 3/40. Client 2 (job `068`, fresh login, same
identity) rendered the item at slot 10 with quantity 2 and slot 0 empty —
a projection read back from server state, not client memory. Operator
observations in the ledger's established sense; no screenshots retained.

### Teardown

Ctrl+C against shim 13428 on the first attempt: `ctrl_c_sent: true`, helper
exit 0, server exited, listeners after stop 0. Canonical database untouched
throughout: post-run sha `CACE7F77..F493` equal to the pre-run pin, verified
twice (job `069`, and independently re-hashed from the sandbox).

## Operational note recorded against the tooling, not the claim

Job `069`'s in-job AFTER snapshot failed before it read anything: the
PowerShell argument carrying the run-DB path was truncated at the first space
(`C:\Users\Panya\Desktop\Pirate` — the folder is `Pirate Force`), and
`sqlite3.connect(..., uri=True)` on that non-existent path opened an empty
database, so every query died with `no such table: character_backpack_items`.
The run copy itself was never touched by the failure. The chief re-collected
the full AFTER set read-only from a `/tmp` copy of the run DB; its content is
what Layer 3 reports. The run copy's post-run file sha256 is pinned here in
prose (the file is deletable after this report lands, per queue rule):
`F9D44AB51E4C2B12D1A9FCB93B4C58F770A731F7FB8B19D0076BF7B76E7511F9`.
Lesson for every future teardown job: quote-or-8.3-escape DB paths containing
spaces; a failed snapshot inside a job must not be recorded as a failed test.

## Observations recorded without interpretation

- Client 2's in-game exit dialog emits an unanswered protocol:
  `UNKNOWN_0x1B40`, 14 bytes, subcode `01` (quit game, captured 3×: seq 3/5/7)
  and `03` (back to character select, seq 9), each accompanied by a
  `GetWorldInfoVital` `0x3D4B` when the dialog opens (16:44–16:52). The
  Foundation answers neither; the dialog closes without effect, after which
  client 2 stopped responding to X / Alt+F4 / Esc and had to be ended by the
  user — while client 1 had closed normally through its (apparently
  client-local) X-button dialog. Decoding is chief work;
  `session_lifecycle/clean_logout` is a candidate matrix row. Nothing about
  logout is claimed by this report.
- The reconnect leg used a second full login while the first session's rows
  were already closed serially — consistent with, and not evidence beyond,
  the known single-session limitation (HYP-PF-011).

## Non-claims

Not proven here: occupied-destination behavior (fail-closed by test, not
exercised in game), same-slot no-op, swap, stack operations, any other item
identity or slot pair, multi-move sequences, durability across a server
restart (only reconnect under the same server process was shown), clean
logout, and any production use — `production_allowed` remains `false` and the
path stays behind the opt-in scenario flag.

## Evidence

Hash-pinned in
`PF_GT002_GENERALIZED_FREE_SLOT_MOVE_FIRST_CLIENT_ACCEPTANCE_RUNTIME_PASS_20260817.manifest`:
the full capture set under `GameClient\capture_gt002_20260817_163028` (server
console out/err, `GAME_LIVE.txt`, `GAME_EVENTS_LIVE.txt`, both raw GAME logs
and both LOGIN logs — one pair per client leg) and the job logs
`pf_bridge\outbox\067_gt002_boot.*`, `068_gt002_reconnect*`,
`069_gt002_teardown*`, `069_ctrlc_20260817_172613.json`.
