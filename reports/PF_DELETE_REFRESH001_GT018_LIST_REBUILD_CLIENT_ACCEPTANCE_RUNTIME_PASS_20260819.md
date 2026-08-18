# GT-018 — the real client rebuilds its character list from a `SelectActorVital` sent after a delete

Date: 2026-08-19
Scope: one attended session (big round #4) driven through the real
`GameClient.local.bin` against a fresh copy of the canonical database, with the
server booted under the opt-in `--delete-refresh-hypothesis-scenario` flag. One
claim only; no ledger entry is edited, `production_allowed` stays `false`, and
every fail-closed path of HYP-PF-021 stays exactly as landed in round 81.

## Result

**Runtime pass** for one claim:

> When the server answers one accepted op-1 delete with the unchanged HYP-PF-015
> echo acknowledgement followed 0.35 s later by a `SelectActorVital 0x36EF`
> rebuild carrying the post-delete row set, the real client removes the deleted
> character from its character-select list **and** returns the character-select
> screen to an input-accepting state: the deleted character's nameboard and model
> leave the scene, the "delete character" button removes itself from the button
> row, and a surviving button ("create character") was pressed and did open the
> character-creation screen.

This is the first real-client acceptance evidence for the list-rebuild answer
that `HYP-PF-021` was opened for, and it closes a symptom this project carried
across three attended rounds. GT-011 had produced the split verdict that started
the lane: the soft delete committed in the database, no error dialog appeared
anywhere, and the list did not move. `UI-REFRESH-001` (round 80) explained that
byte-exact from the read-only client image — the character list lives in one
buffer and **there is no erase-by-key path anywhere in the image**, so no shape
of the acknowledgement could ever have removed that row — and named
`SelectActorVital 0x36EF` as the only frame in the protocol that can. Round 81's
re-scan of the page variable `0x107A2C0` found a twenty-first, register-mode
writer inside `cStateCreateActor`'s enter hook and upgraded the prediction from
*"the list changes"* to *"the list changes **and the buttons come back**"*.

**Both halves of that upgraded prediction were observed.** The prediction is the
thing this report grades; the mechanism behind it stays where round 81 left it, a
chain of byte facts rather than an observation (see Non-claims).

## Run identity

| | value |
|---|---|
| tree under test | `11fea4f` (round 82), the HEAD the tester booted; the lane itself landed one commit earlier at `6891372` (round 81, `2026-08-19 02:03 ICT`), which is an ancestor of `11fea4f` |
| current HEAD at time of writing | `0081ac3` (round 83) — later than the run, cited only so the reader can place the run in history |
| session | attended big round #4, 02:42–03:11 ICT, 2026-08-19; Claude main session as tester under the `pf-attended-test` skill, Panya at the machine |
| jobs | `130` (boot + client), `131` (teardown) |
| boot | `--delete-refresh-hypothesis-scenario scenarios\delete_refresh_hypothesis_list_rebuild.json` with an explicit `--db`, visible console, `-SecondPasswordMode bypass` |
| database | a fresh copy of the canonical database; the canonical file itself was not opened by this test. The run-copy filename was not recorded in the session notes |
| capture root | `GameClient\capture_gt018_20260819_024213` |
| character deleted | `Arena01`, the only character in the list |

## Evidence layers

The three layers below are kept apart on purpose. Only the first one is the
claim; the second is corroboration; the third is context and is **never** golden.

### Layer 1 — client-observable (what was on the screen)

Driven exactly as GT-011 was: leftmost character-select button → yes/no dialog →
the second-step randomized password pad, `test` typed on it → confirm.

1. **No error dialog** appeared at any point, as in GT-011.
2. **`Arena01` left the list.** Its nameboard disappeared and its model
   disappeared from the character-select scene.
3. **The "delete character" button removed itself from the button row.** The row
   went from five buttons to four — create character, name, back, change
   appearance. This is the part that distinguishes a rebuilt UI from a hidden
   row: the screen recomputed its own affordances from a list it now reads as
   empty, rather than merely omitting one entry from a rendering pass.
4. **A surviving button was pressed and worked.** "Create character" was clicked
   and the character-creation screen opened, showing five selectable character
   models and a "back" button. Under GT-011 every button on this screen had
   stopped responding after the acknowledgement.

One screenshot of the empty-list moment was written to disk; the remaining
imagery of this test stayed in the tester's chat with the owner and is not a
retained artifact. Photographic coverage of GT-018 is therefore thinner than the
prose above, and the reader should treat items 2–4 as operator observations in
the ledger's established sense.

### Layer 2 — wire

Both designed frames were present in `GAME_LIVE.txt`, in the designed order:

- `HYP_PF_021_DELETE_ACTOR_SELECTOR00_SOFT_DELETE_COMMITTED`
- `HYP_PF_021_DELETE_ACTOR_LIST_REBUILD_0`

No inter-frame timing measurement was recorded for this run; the 0.35 s gap is
the designed value from round 81, not a number this test measured. The canonical
database was not touched — the test ran on a copy.

### Layer 3 — owner testimony (context only, never golden)

Panya was at the machine for this test and watched the same screen. Her account
agrees with Layer 1. It is recorded here as context and adds no weight: for
GT-018 the tester's own direct observation is the evidence, and testimony is
**not** admissible as golden anywhere in this project.

## What this does not prove (non-claims)

- **The delete-then-rebuild policy is our own design, not a recovered rule.**
  No capture anywhere in the curated corpus shows a server answering a delete
  with a list rebuild. The rebuild frame is not invented bytes — it is the
  unchanged `LegacyProjector.character_list` projection, byte-for-byte the frame
  a real client has accepted at every login, taken over the post-delete row set —
  but *deciding to send it in answer to a delete* is a designed hypothesis. The
  original server is gone and never published; nothing here claims it behaved
  this way.
- **Slot reuse was not proven at the client layer.** The create-character screen
  was opened but no character was created; the session ran out of time. That the
  freed selector, identity and fingerprint are recreatable byte-identically is
  proven **headless only** (DELETE-SOFT-001, DELETE-SOFT-003) and remains
  unproven through the real client.
- **The page-variable mechanism is still inference.** The buttons came back; that
  the single rebuild frame restored `0x107A2C0` through `cStateCreateActor`'s
  enter hook is a chain of byte facts, and the live value of that variable was
  never read during GT-011 or GT-018. What is graded here is the observable
  outcome, not the route to it.
- **One list, one row, one deletion.** Deleting one of several characters,
  ordering of the rebuilt list, and any multi-character case are untested.
- **The second-password gate is not graded.** It was driven in bypass mode
  (`-SecondPasswordMode bypass`); the pad accepted `test`. Nothing about the real
  gate is claimed.
- **Negative paths were not exercised in game.** op 2, wrong stage, wrong
  envelope, repository refusal and refused projection are fail-closed by test
  only. `production_allowed` remains `false` and the path stays behind the opt-in
  scenario flag.
- No claim is made about the semantics of the acknowledgement's `+0x14` field,
  and no claim is made about sending `SelectActorVital` while the client sits in
  `StateRunTime` — round 82 established that no inbound frame takes a player out
  of that state, and that is a different question from this one.

## Evidence pointers

Capture set under `GameClient\capture_gt018_20260819_024213` (server console
out/err, `GAME_LIVE.txt`, `GAME_EVENTS_LIVE.txt`, raw GAME and LOGIN logs) and
the job logs `pf_bridge\outbox\130_*`, `131_*`. Both trees are outside the
repository and are not version-controlled, so this report carries no `.manifest`;
the capture root is named here in prose so it can be found. Session notes:
`pf_bridge\notes_to_chief\consumed\20260819_0315_biground4-results.md`. Queue
entry with the pre-registered prediction and pass criteria:
`pf_bridge\archive\GAME_TEST_QUEUE_ARCHIVE_20260819_GT018_GT019_GT020.md`.
