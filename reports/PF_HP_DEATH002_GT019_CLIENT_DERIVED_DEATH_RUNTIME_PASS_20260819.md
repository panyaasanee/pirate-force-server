# GT-019 — two fields on the wire are enough for the real client to derive a death by itself

Date: 2026-08-19
Scope: two attended sessions (big rounds #4 and #5) driven through the real
`GameClient.local.bin` against fresh copies of the canonical database, with the
server booted under the opt-in `--hp-death-hypothesis-scenario` flag. One claim
only; no ledger entry is edited, `production_allowed` stays `false`, this lane
writes nothing to any database, and every lock landed in round 81 stays as it
was.

## Result

**Runtime pass** for one claim:

> When the server sends one `UpdateAttrVital` carrying `BasicAttr` current HP
> `+0x44` (mask bit `0x0004`) equal to zero together with the f32 at `+0x58`
> (mask bit `0x0080`) set to a positive, finite, exactly-representable value, the
> real client renders that character as dead without any further frame: the
> heads-up bar reads `0 /100`, the character enters a collapsed pose on the
> ground, and a previously unknown one-control window opens above and to the
> right of the character — a circular button, gold rim, red field, white cross,
> with the orange Thai caption **"ล้มเลิกการช่วยเหลือ"** ("abandon the rescue").
> The state persists until the server sends a frame restoring HP, at which point
> the character stands up again.

This is the first real-client acceptance evidence for `HYP-PF-022` and it
confirms, on a real screen, the central prediction of `HP-DEATH-001` (round 80):
that **the distance between this server and being able to kill a character is one
mask bit and one float**. Death is not a frame the server sends; it is a
derivation the client performs from two values. Nothing in this run made the
client run a server-authored death sequence, because there is no such thing to
run.

The rescue window is the finding this test was not designed to make. Round 81
predicted the `Main_Dead` window would open and said so in the queue; nobody knew
what it contained. A help-request / player-rescue system exists in the client
image and is brought up by `HP == 0` alone.

## Run identity

| | value |
|---|---|
| tree under test | `11fea4f` (round 82) in both rounds; the lane itself landed one commit earlier at `6891372` (round 81, `2026-08-19 02:03 ICT`), which is an ancestor of `11fea4f` |
| current HEAD at time of writing | `0081ac3` (round 83) — later than both runs, cited only so the reader can place them in history |
| session A | attended big round #4, 02:42–03:11 ICT; jobs `132` / `133`; capture root `GameClient\capture_gt019_20260819_025640`; Panya at the machine |
| session B | attended big round #5, 03:38–04:05 ICT; job `136` (boot); capture root `GameClient\capture_gt019_20260819_033154`; run copy `state\pirateforce_gt019_20260819_033154.sqlite3`; Panya asleep, tester unattended by her own instruction |
| boot | `--hp-death-hypothesis-scenario scenarios\hp_death_hypothesis_death_sweep.json` with an explicit `--db`, visible console |
| trigger | one chat line typed by the player after runtime ready; the scenario emits four frames spaced 6.0 s |
| timer value sent | `60.0f` — a choice with headroom, not a proven number (see Non-claims) |
| database writes | none; this lane's `database_write` is `none` and the canonical file was not opened by either run |

## Evidence layers

The three layers below are kept apart on purpose. Only the first is the claim.

### Layer 1 — client-observable (photographed, session B)

Session B is the golden layer of this report because it is the run that produced
retained images.

1. The heads-up bar read **`0 /100`**.
2. The character entered a **collapsed, kneeling pose on the ground**. This was a
   pose change, not only a number change.
3. A **circular button with a gold rim, a red field and a white cross** floated
   above and to the right of the character, captioned in orange Thai text
   **"ล้มเลิกการช่วยเหลือ"**.
4. The state held for **6.000 s** and the character stood back up when the
   `HP_RESTORED` frame arrived.
5. No error dialog; the client did not hang; it exited cleanly through the X
   button and its confirmation dialog.

The images are in `pf_bridge\report_images\` with the owner-facing writeup
`pf_bridge\PANYA_REPORT_20260819_biground5.md`. Both live outside the repository.

**Repeatability.** The chat trigger is re-armable (`one_shot: false` works), and
the full four-frame sweep was fired **eight times in a single session** —
03:37:28, 03:40:11, 03:52:16, 03:53:05, 03:53:49, 03:54:44, 03:55:39, 03:56:19 —
and every one of the eight emitted all four frames at the 6.00 s spacing with
send lateness under 2.5 ms. A result that reproduces eight times inside one
process is a different kind of result from one that happened once.

### Layer 2 — wire

Session A's `GAME_LIVE.txt` timestamps the four frames of the sweep:

| time (ICT) | frame | size |
|---|---|---|
| 03:03:04.245 | `HYP_PF_022_HP_DEATH_BASELINE` | 119 B |
| 03:03:10.245 | `HYP_PF_022_HP_DEATH_TIMER_ARMED` | 124 B |
| 03:03:16.245 | `HYP_PF_022_HP_DEATH_HP_ZERO` | 124 B |
| 03:03:22.245 | `HYP_PF_022_HP_DEATH_HP_RESTORED` | 124 B |

The lethal window is therefore **03:03:16 → 03:03:22, exactly 6.0 s wide**. Frame
2 is the control of this test and behaved as designed: the timer arrives while HP
is still 100 and nothing happens, which is what separates "the timer did it" from
"HP zero did it". Session B repeated the same shape eight times as recorded
above. No database write occurred in either session, which is the correct result
for this lane.

### Layer 3 — owner testimony (context only, never golden)

Two distinct pieces of testimony exist and neither is used as proof:

- **Panya's live sighting during session A.** She watched the screen and reported
  the bar reaching `0/100`, the character collapsing, a strange UI element
  appearing, roughly five seconds of that state, and then a return to `100/100`.
  Session A produced no photograph of any of it. This is what caused the result
  to be corrected (see the Nyquist section). It is recorded as **context**; the
  evidentiary weight sits entirely on session B, which photographed the same
  thing.
- **Panya's memory of the original server.** She played this game when the
  original server was running and recalls that HP reaching zero put the character
  into a downed state with a countdown of "fifteen or twenty seconds" and a
  cancel-the-help-request button beside it; that if the countdown expired the
  character died fully; and that a revive-at-town screen followed. This is
  **`provenance: owner_testimony`** in the strict sense — human memory, possibly
  wrong, and she said so herself about the number. Its value is that it tells us
  what to look for in the binary, not what the binary contains. **Where testimony
  and the image disagree, the image wins.** It must never be written into the
  ledger as fact and it grades nothing in this report.

## The Nyquist lesson

GT-019 was first reported as a **FAIL** — "the HP bar sat at 100/100 across all
four frames and did not move by a single pixel". That report was wrong, and the
way it was wrong is worth more than the test result.

The tester sampled the screen at points rather than continuously, at roughly
03:03:05, 03:03:15, 03:03:25 and 03:03:37. Every one of those readings was
accurate. Three of them fell outside the six-second lethal window; the closest
missed it by about one second on each side. The tester then converted four
correct point readings into a claim about a continuous interval — "nothing
happened" — which the samples could not support. The window was straddled, not
observed.

The rule this produces is permanent, and it is now written into the
`pf-attended-test` skill:

> **A time-ordered test may never conclude "nothing happened" from point
> sampling.** If a scenario has a cadence, observe it continuously, or sample at
> least twice as often as the frame period (Nyquist), or use burst capture. If
> none of that was possible, the honest sentence is **"the interval t1–t2 was not
> observed"** — never "nothing happened".

Three things follow that are worth keeping:

- **The failure mode is asymmetric.** Point sampling can prove that something
  *did* happen; it can almost never prove that something *did not*. A negative
  from sampling is a claim about every instant between the samples, and the
  samples say nothing about those instants.
- **It cost real planning.** The FAIL note proposed chasing the
  `UpdateAttrVital → 0x4446F0` chain on the theory that the frame never reached
  the local player's attributes, and grouped GT-019 with GT-011 and GT-013 as
  another case of "the client parses and ignores". Both conclusions were
  withdrawn. GT-019 is the opposite case: the client did move. The emerging
  belief that this client ignores everything we send is not always true, and one
  bad negative nearly hardened it into doctrine.
- **It was caught by a human, not by a tool.** This is the second error of this
  family from the same tester, and Panya caught both. The remedy is procedural —
  photograph densely, or write down what you did not see.

Session B was run specifically to repair this, and it is the reason this report
has images. The technique that worked is recorded here so the next tester does
not rediscover it: a **short** batch of `[click chat, type, Enter, wait 11]`
followed by three rapid captures inside the same batch. A long batch (eight zooms
spaced two seconds) drifts far enough that the window is missed again, and
`save_to_disk` inside `computer_batch` does not work — `screenshot` and `zoom`
must be called individually. The usable observation window is **trigger + 12.0 s
to trigger + 18.0 s**.

## What this does not prove (non-claims)

- **No respawn. No coming back. Nothing at all.** The "respawn" half of this
  lane has **zero evidence of any kind**. The character standing up at the end of
  the sweep is not a respawn — it is the client re-deriving "alive" from an
  `HP_RESTORED` frame this same scenario sent on purpose. No revive-at-town
  screen was seen, no `ReliveVital 0x1AD4` exchange occurred (round 80 proved it
  is request-only and bound to a shared inbound no-op, so echoing it does
  nothing), no respawn placement exists on this server, and no encoder or
  dispatch exists for any of the three verbs that carry a death token. **GT-021
  (`dying_hold`) is the first test that will touch this half at all.**
- **No death animation is claimed.** A collapsed pose was seen and photographed,
  but nobody read which animation clip played, and this report does not claim
  `_F_DIE_000`. Round 81 traced the inbound chain end to end and established that
  `UpdateAttrVital` does **not** reach `0x4446F0`, so `0x4437C0` and the death
  animation are not reachable from this transport — only the per-frame
  `Main_Dead` gate is. The pose observed here is therefore attributed to the
  client's own dying-state derivation and **not** to a server-driven animation
  trigger. Which client-side clip that pose belongs to is an open question this
  test did not answer.
- **No `TargetIsDead` latch.** Round 81 proved this transport cannot reach it.
  Nothing observed here changes that, and nothing observed here required it.
- **No persistence of HP.** This lane writes nothing to any database. HP zero
  survived nothing: not a relog, not a reconnect, not a server restart, none of
  which were attempted.
- **This is not a rule of the original server.** No golden exists. There is no
  server-to-client combat frame anywhere in the curated corpus, the original
  server is gone and was never published, and the four-frame sweep is a designed
  hypothesis of ours. What is recovered from the image is the *client's*
  expectation; what the original server actually sent is unknown and,
  per round 83, unrecoverable.
- **The deployed `DURATION_DYING` is unknown.** The client image sets it to
  `20`, and the `Main_Dead` gate additionally requires the timer to be within
  0.5 of that constant. The scenario sent `60.0f` as a deliberate headroom
  choice. The window opened, so the deployed value cannot be far above 60.5 —
  but the actual number remains unknown and unproven, and Panya's recollection of
  "fifteen or twenty" is testimony, not measurement.
- **No countdown was found, and that is not the same as there being none.**
  Written to the letter, as required: *no counter was seen in the three frames
  observed, under the conditions timer = 60.0 and a restore at 6 s.* It must not
  be written as "there is no counter".
- **No damage model.** How HP reaches zero is untouched. Round 83 established
  separately that the client computes no damage at all; this test says nothing
  about it.
- **No penalty, no corpse, no rescue mechanics.** `n_DEADLOSS` is external data.
  The rescue window was seen but its button was never pressed and nothing is
  claimed about what it does, what it sends, or whether it sends anything.
- **One character, one class family, one map.** No NPC, pet or remote actor was
  killed; nothing is claimed about the other `IsDead` predicate pairs.

## Evidence pointers

Capture sets under `GameClient\capture_gt019_20260819_025640` (session A) and
`GameClient\capture_gt019_20260819_033154` (session B), the job logs
`pf_bridge\outbox\132_*`, `133_*`, `136_*`, the images in
`pf_bridge\report_images\` and the owner-facing writeup
`pf_bridge\PANYA_REPORT_20260819_biground5.md`. All of those trees are outside
the repository and are not version-controlled, so this report carries no
`.manifest`; the roots are named here in prose so they can be found. Session
notes, in the order they must be read:
`pf_bridge\notes_to_chief\consumed\20260819_0315_biground4-results.md` (contains
the withdrawn FAIL — read the correction before acting on it),
`..._0325_CORRECTION-gt019-is-PASS.md`,
`..._0335_PANYA-EYEWITNESS-death-and-rescue-flow.md`,
`..._0405_biground5-gt019-photographed-and-bridge-died.md`. Queue entry with the
pre-registered per-frame prediction and pass criteria:
`pf_bridge\archive\GAME_TEST_QUEUE_ARCHIVE_20260819_GT018_GT019_GT020.md`.

## Recorded without interpretation

The bridge job runner stopped executing jobs at about 03:32 and the session B
teardown job `137_gt019b_teardown.ps1` was left queued deliberately, so the test
server stayed up. This is an operational note against the tooling, not against
the claim; it cost GT-017 and GT-015 their slots that night.
