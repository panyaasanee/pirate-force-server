# PF NPC-HP-LINK / HYP-PF-029 -- the GT-027 rerun attended result of 2026-08-20

- **date of observation:** 2026-08-20, attended, driven by Panya herself
- **date of this write-up:** 2026-08-20 (transcribed same day), corrected and filed 2026-08-21
- **milestone this record supports:** HYP-PF-029 / NPC-HP-LINK-001 (the load-bearing empirical premise of the lane)
- **claim grade:** CLIENT-OBSERVABLE LAYER, NEGATIVE RESULT ONLY. Never cite as wire-layer evidence.

## READ THIS FIRST -- THE PROVENANCE CAVEAT, UNSOFTENED

**This result is testimony plus surviving screenshots. It is NOT a re-derivable receipt.**

The tester stopped before writing the round up and before running teardown, so the round has
**no wire-layer evidence at all**:

- no server console tail was cut, because no teardown ran;
- no post-run database snapshot exists;
- no traceback count was taken;
- there is **no capture file dated 2026-08-20 anywhere** in the project. The tester's own
  search on the day reported `capture_v141/GAME_LIVE.txt` as dated 18 Aug. Re-measured on
  2026-08-21 for this report: `capture_v141/` contains **zero** files whose name carries
  `20260820`, and the two live tails `GAME_LIVE.txt` / `GAME_EVENTS_LIVE.txt` are the newest
  things in the directory at 2026-08-19 01:52 -- the newest capture bytes in the tree predate
  the round by more than a day either way.

The write-up below was **transcribed from a screenshot of the tester's chat window that Panya
sent at approximately 15:15** on 2026-08-20. It was recorded so the result would not be lost,
not because it met this project's normal evidence bar.

**Anyone who wants to overturn this grade must know that first.** The correct way to overturn
it is to run the observation again with teardown, not to argue with this file.

The one thing that DID survive independently of the testimony is the screenshot set below,
which this document hashes so that it cannot be quietly swapped later.

## WHAT WAS OBSERVED

The rerun differed from every earlier GT-027 attempt in one way that matters: **Panya clicked
the NPC to select it before firing**, so the target's HP bar was on screen for the whole round.
The client log line that records the selection is:

```
12:31:58 TargetVital 0x2001 'Navy Transfer'
```

The shot went out at `12:32:07`.

| | before the shot (video t = 18 s) | after all four frames (video t = 66.5 s) |
|---|---|---|
| player HP | `100/100`, full | `100/100`, full |
| **target HP (`0x2001` 'Navy Transfer')** | `100` Lv.1, full bar | `100` Lv.1, full bar -- **did not move** |

Cumulative damage delivered across the sweep: **63 + 379 + 63 = 505**. The target's hit points
did not move by a single unit.

Two further observations from the same round:

- the `MISS!` marker rendered as a texture, as GT-024 had already shown;
- the two yellow arrows over the NPC's head are the **selected-target marker**, NOT a hit
  effect. They are present in the t = 18 s frame, before anything was fired. This is recorded
  because it is an easy misreading of the screenshots.

The video timestamps `t = 18 s` and `t = 66.5 s` are positions on the recording. They are not
instrumented timestamps.

## THE EVIDENCE THAT SURVIVES ON DISK

Directory: `pf_bridge/evidence_screens/biground10_gt027/`

This directory lives in the bridge repository (`pirate-force-bridge`), NOT in this server
repository. The five files below were verified to exist and were hashed for this report on
2026-08-21. Sizes are bytes; digests are SHA-256, lowercase hex.

| file | size (bytes) | sha256 |
|---|---|---|
| `gt027_f1_HIT_WEAK_63_on_npc.png` | 796073 | `a863ef65e9aef9e02fb00475399f64ab777dc96044c67c7ca0d4bac262358b29` |
| `gt027_f2_HIT_STRONG_379_on_npc.png` | 590106 | `61c105104dacae309f5b10b59ec60254a4e1a4177067a3c44a693307641ad719` |
| `gt027_f2_fullframe_379_hp100.png` | 1202700 | `e9fb5c2c5e8289eb573c2bcf8a64b49ccabc63d5275adbfe990e83fb1e65cc4e` |
| `gt027_f3_MISS_marker.png` | 826540 | `7ab577c36ce13cca5aa972aed206860c99a9c75d030fad7b3f95211e4cec3097` |
| `gt027_f4_HIT_REACTION_63.png` | 798724 | `4af74029543dcbb933d9a91e6bd4a0c826de5420c14e0b2a91df68146cbaa835` |

`gt027_f2_fullframe_379_hp100.png` is the load-bearing one: it is the full frame showing the
379 figure over the NPC and the NPC's HP readout still at 100 in the same image.

The video itself, and some further frames, were left outside the project folder in the agent
session directory. They are NOT in any repository and may be lost at any time. Only the five
PNGs above should be treated as durable.

## THE CONCLUSION THIS LANE RESTS ON, WITH ITS SCOPE

**Client-observable-layer negative only:** four `CHitResult` frames carrying 505 points of
cumulative damage against a selected NPC target did not move that target's HP bar. The
client draws the number and does nothing else with it, which is the on-screen consequence of
what round 83 (DAMAGE-MODEL-001) had already proved byte-exactly: the client computes nothing
about damage and never subtracts it from anything.

This is exactly why HYP-PF-029 exists: if the target's hit points are ever to move, the SERVER
has to say both halves -- the number AND the new balance -- on the two carriers this project
has already rendered on a real screen.

**Scope limits, and they are hard:**

1. This is a **negative** about the hit carrier alone. It says nothing whatsoever about what
   the actor-entry carrier will do, which is the thing HYP-PF-029 tests.
2. It is a **client-observable-layer** result. **It must never be cited as wire-layer
   evidence.** There is no wire-layer evidence from this round at all -- see the caveat above.
3. It does not falsify or confirm question (6) of GT-027 (flag `0x0009` versus `0x0001`):
   frames 1 and 4 were not distinguishable by eye, which is not a measurement.

## METHOD NOTE THAT CAME OUT OF THIS ROUND

Panya ruled on 2026-08-20 that **stretching frame spacing for the human tester is wasted
effort, because the event itself is short; the correct fix is recording video**. The 15-second
photography profile is therefore not to be reproduced for new lanes. HYP-PF-029 ships 6.0 s
spacing for this reason, and the evidence discipline for its attended test is the camera.

## FILING NOTES

- No `.manifest` accompanies this report. Reports filed from chief round 95 onward
  (`PF_DAMAGE_NPC_TARGET001_SECOND_PROFILE_20260820.md`,
  `PF_DAMAGE_HP_LINK001_HIT_BLEED_DIE_LINK_20260820.md`,
  `PF_NPC_HOSTILE001_DOOR_A_HOSTILE_PRESENTATION_20260820.md`,
  `PF_LOGOUT_RETURN_SELECT001_HYP028_20260820.md`,
  `PF_REMOTE_PLAYER_ENCODER001_ACTOR_TYPE_2_VISIBILITY_20260820.md`) carry none either; the
  manifest convention stopped before this block and is not revived here.
- Source of the transcription: `pf_bridge/notes_to_chief/20260820_1520_GT027-RERUN-FINAL-video-npc-hp-does-not-move.md`
  (bridge repository, not this one).
- This report is cited from `docs/HYPOTHESIS_LEDGER.json` in the HYP-PF-029 `evidence_refs`,
  and it is what `reports/PF_DAMAGE_NPC_TARGET001_SECOND_PROFILE_20260820.md` and the
  HYP-PF-024 entry now point at for the GT-027 client layer.
