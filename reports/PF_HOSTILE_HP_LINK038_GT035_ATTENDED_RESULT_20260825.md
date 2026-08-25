# PF HOSTILE-HP-LINK-001 (HYP-PF-038) -- GT-035 attended result, 2026-08-25

LAYER: client-observable testimony plus screenshots and video.  NEVER to be
cited as wire-layer evidence.  Nothing in this file is re-derivable from this
repository; it is recorded here so that a reader of this tree can see what the
lane's retired nonclaims were retired ON, and on what they were NOT.

Recorded by: chief, cloud round R164, 2026-08-25.
Primary source: pf_bridge/notes_to_chief/20260825_1550_GT035-PASS-hostile-hp-bar-moves-two-observers-agree.md
Ticket: pf_bridge/GAME_TEST_QUEUE.md, GT-035 DAMAGE-ON-HOSTILE-001.
Evidence artifacts live in the SIBLING repository (pf_bridge/evidence_screens/),
not here.  This tree carries no image and no video.

## Run conditions

    BOOT_COMMIT           d856ff4bb8ae498292b276d036b8482a53deaac6
    CODE_DELTA_vs_main    0
    CANON before/after    equal, both runs
    teardown exit         0, both runs
    run 1                 jobs 1137 / 1138 / 1139, UI driven by the attended assistant
    run 2                 jobs 1140 / 1141 / 1142, UI driven by the project owner
    video (run 2)         starts 15:26:23.065 (+07:00), chat trigger at t = 367.3 s

## What was observed

Run 2 is the measured run.  Frame readings off the run-2 video:

    t 368-378   target HP 3857, bar full     spans HIT_WEAK at t 373.3
    t 380-402   target HP 2893, bar ~75%     spans MISS 385.3, AFTER_MISS 391.3,
                                             HIT_STRONG 397.3
    t 404       target HP  771, bar ~20%

On-screen, first time in this project against this identity: a red damage
number 964 above the target's head with a white flash (t 373.3), a readable
"MISS!" with no flash (t 385.4), and 2122 with a flash (t 397.3).  The numbers
match the values the server sent; they are not scaled and carry no minus sign.

The two load-bearing conclusions come from the intervals where the bar did NOT
move, not from the steps: 3857 held across HIT_WEAK and 2893 held across
HIT_STRONG, so an attack frame alone does not move the bar; and 2893 held for
22 seconds across both MISS and AFTER_MISS, so the miss control behaved.

## What the second observer actually corroborates -- read this before citing
## "two independent observers"

Run 1 did NOT see the whole ladder.  Its own artifact
(pf_bridge/evidence_screens/GT035_1138_HPPANEL_432-476s.jpg) shows no target
panel from t 432 to t 458; the panel appears at t 460 already reading 2893, and
771 at t 472.  Run 1 therefore never observed 3857 and never observed the first
step.  The letter also records that run 1's camera was at maximum zoom-in, the
target's head was out of frame, and BOTH damage numbers and every MISS were
missed -- and that the gap was not reported as a gap.

So: the two-observer agreement covers that the model was drawn and covers the
tail of the ladder.  It does NOT cover the first step, the damage numbers, or
the miss control.  Those are single-source, from the run-2 video.

## Latency: what is measured and what is the design constant

The bar dropped between two sampled frames.  The ladder contact sheet
(GT035r2_1141_HPLADDER_v2_366-406s.jpg) samples every 2 s: 378 s reads 3857,
380 s reads 2893.  The measured bound on the delay from the damage number
(t 373.3) to the bar drop is therefore (4.7, 6.7] s.  6.0 s is the frame
spacing this lane was DESIGNED with (HOSTILE_HP_LINK_SPACING_SECONDS = 6.0).
Do not report 6.0 s as a measured client property; the observation is
consistent with it, which is not the same statement.

## What this retires in the source tree

Two nonclaims that this module carried, both now reworded rather than deleted:

1. that nobody had confirmed with their own eyes that a model at these offsets
   is inside the client's model draw distance -- retired for THESE offsets
   only.  The draw distance LIMIT remains unmeasured.  Apparent size on screen
   is a function of camera zoom, not of distance-to-cutoff, so "it filled the
   screen" is not a margin measurement.
2. that whether the client renders the intermediate value 2893 on the target's
   HP bar was the queued attended test -- the test has now run and answered.

## What this does NOT retire, and must ride with any citation of this result

1. The arithmetic, the ladder and the linkage between the damage frame and the
   HP frame are OUR design.  The original server is unrecoverable and no
   capture shows it doing this.
2. Death is not touched.  This lane has no lethal half by design: HP_FLOOR is
   FORBIDDEN, there is no hp = 0 frame, no death timer and no dying latch, and
   the ladder ended at 771 and never reached 0.  GT-036 gains NOTHING from
   this result and must not cite it.
3. The word "hostile" is still unproven.  The target's name label rendered in
   the colour this client uses for PLAYERS; NPC labels on the original server
   were yellow.  What decides that colour is open ticket RE-067.  The HP bar
   moving therefore does not establish that the target is an enemy.
4. Nothing here shows the client COMPUTING anything.  It displayed the numbers
   the server sent.
5. Nobody attacked the target and no skill was used.  Every frame was emitted
   by the server; the player typed one line of chat.

## Layer accounting

The ticket separates a wire/DB layer from a client-observable layer and forbids
citing one for the other.  This file records the client-observable layer only.
The wire-layer checks the ticket lists -- the seven outbound frames counted and
ordered, the identity bytes present in every frame, the DB row counts -- were
NOT reported by the attended round and are NOT recorded here.
