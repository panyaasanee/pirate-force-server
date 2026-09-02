"""LANE-B / MOB-LOOT-001: the monster a player kills leaves something behind.

WHAT THIS MODULE IS FOR.  M5 is "loot drops, you pick it up, it is in your bag
after a relog".  This module is its FIRST half and says so in every claim it
makes: a kill rolls the dead monster's OWN drop sets out of the real game
tables, the roll becomes a ledger of what that kill produced, and ~~each row
becomes one frame~~ THE WHOLE LEDGER OF THAT KILL BECOMES ONE GENERATION
(struck round ``zxnwtd``, see ``drop_frames`` and ``RE-130``)
of the exact list shape an attended run has already watched
the client turn into a floating item NAME at the coordinate we sent (a name,
not an object -- see WHAT THE PLAYER SEES).  What it does NOT do is the second
half: nothing
here picks anything up, and nothing here writes a database row.  The two halves
are separated at the ledger on purpose -- the pickup side's trigger is a client
message this project has never seen on the wire (see NONCLAIMS 4), and mixing
a proven half with an unproven one inside one round is how a lane ends up
claiming both.

    roll      <- the dead mob's own DROPS_NORMAL / _EQUIPMENT / _SPECIALLY
    ledger    <- what that kill produced, where, and whose kill it was
    element   <- one RuntimeRes derived-bit-0x08 list element per object
    frame     <- ONE generation carrying every element of that kill
                 (~~one single-element frame each~~ STRUCK round ``zxnwtd``:
                 ``RE-130`` measured the consumer erasing every key a
                 nonempty generation omits, so the old shape left only the
                 LAST drop of a multi-drop kill in the client's tree)

NO FLAG, AND THAT IS THE POINT.  ``production_allowed`` is True.  There is no
scenario id, no dispatch kwarg, no unlock object and no allowlisted profile in
this file.  The lane that PROVED the wire shape (``ground_loot_hypothesis``,
HYP-PF-032) is a scenario-gated probe that can only ever emit its own two
hard-coded elements at scene load; a build the owner boots with no flags cannot
reach one byte of it.  So the encoder is RE-DERIVED here, in general form, from
the same static anchors, and ``tests/test_mob_loot.py`` pins the composed bytes
against that probe lane's own encoder, element for element.  This module
imports NO probe lane.

WHAT THE PLAYER SEES, AND FOR HOW LONG.  ~~"a MODEL and a floating NAME LABEL
... the difference between those two ids is n_DROPMODEL_TYPE"~~ IS STRUCK.  It
was in the first draft of this module, it is the exact opposite of what the
ticket measured, and it is kept struck rather than deleted so nobody re-derives
it.  GT-045 is CLOSED-ANSWERED (chief R163, four attended rounds 11:48-13:30 on
2026-08-25, jobs 1122-1136; letter ``pf_bridge/notes_to_chief/20260825_1340_
GT045-ANSWERED-name-label-yes-model-no-plus-the-QE-rule-was-wrong.md``):

  * [MEASURED, pixels not eyes -- the second letter,
    ``20260825_1615_GT045-EVIDENCE-COMMITTED-namelabel-frame-plus-exact-wire-
    to-screen-timing.md``, which is the citation that discharges R163's
    evidence correction and must travel with the first one] A floating NAME
    LABEL is drawn at the coordinate the server sent, in RED text, readable in
    full: "Red leaves Hammer".  Frame-extracted at 30 fps: present at t =
    249.733, gone by t = 250.067, LIFE 0.30 s -- and that letter's own
    mandatory nonclaim says the recorder duplicates frames in threes, so the
    real sampling is ~10 fps and 0.30 MEANS 0.2-0.4.  Writing 0.30, or 0.25,
    or "about a quarter of a second", is forbidden by the measurement itself.
  * [MEASURED, same letter] WIRE TO SCREEN is about 0.12 s -- and that is a
    distance between "the sender logged the send" and "the camera caught the
    frame", not a client render latency.
  * [MEASURED, WITH ITS SCOPE] NO MODEL UNDER THE LABEL THAT WAS SEEN: no
    object, no shadow, nothing to walk up to.  The SCOPE is real and this lane
    may not widen it -- two elements went out 42 ms apart (NEAR 2200423,
    n_ID_MODEL 0; FAR 2200003, n_ID_MODEL 2) and only ONE label is in the
    frame.  Its text names 2200423, so the visible one is NEAR; whether FAR
    drew anything at all is INDISTINGUISHABLE from "off camera" in that
    evidence.  The one element ever confirmed to draw nothing under its label
    is the one whose model-asset id is 0.
  * [MEASURED] BROWN DUST is drawn, immediately after the label.
  * [MEASURED, and it refutes what this module first wrote] ``n_DROPMODEL_TYPE
    = 1`` IS NOT SUFFICIENT to make a model appear -- BOTH GT-045 v3 ids carry
    1.  "Not sufficient" is not "not the switch", and this lane says the
    former; the column the two ids actually differ in is ``n_ID_MODEL``, which
    nothing here mines and nothing here claims.  What makes a model appear is
    the OPEN question of that ticket and nobody may read GT-045 as answering
    it.
  * [MEASURED, and it is why the roll matters] The client resolved the NAME
    ITSELF from the payload dword -- this lane's shape never sends a name
    field.  That matches RE-066 (create path A at 0x00892580 reads s_NAME) and
    RE-060 (TEXTDATA TIP, n_ID 423 = "Red leaves Hammer").
  * [NOT RE-VERIFIABLE FROM THIS REPO, and R163 made this nonclaim mandatory
    forever] The round-3 screenshots the first letter cited contain no item
    label in any frame, and the round-4 .mkv is over the repo's size cap and
    is not committed.  What IS committed is the single extracted frame the
    1615 letter added.  The client-observable layer of GT-045 rests on that
    one frame.

So the honest sentence for this round is: "the monster you killed announces the
NAME of its own loot, in red text, where it fell, for two to four tenths of a
second."  NOT "you can pick it up", and NOT "an item lies on the ground" --
nothing was under the one label anyone has seen.  :func:`refresh_frames` exists so a caller CAN re-emit the
ledger, which is the only lever this lane has toward "it stays"; whether
re-emission redraws the label, does nothing, or restarts the dust is UNMEASURED
and is written as a nonclaim rather than as a feature.

WHAT THIS ROUND ADDS, AND WHAT IT DOES NOT YET REACH (ROUND KA1B-DROPMODEL).
Everything above this paragraph is untouched history and stays exactly as it
was written -- GT-045 measured NO MODEL, and that finding does not move.
What is new: ka1-B's letter (pf_bridge notes_to_chief/20260901_2015_KA1B-
TO-LANE-B-drop-model-selector-field-is-not-on-our-wire.md, [HYPOTHESIS,
unproven]) reads GT-045's own open question -- what makes a model appear --
as a field this lane has simply never SENT: mask bit 0x04 (tag 0x0F, u16,
+0x18, ``n_DROPMODEL_TYPE``), one of three candidates the same static
element table already names.  The other two (mask 0x08 and 0x20) are RULED
OUT by an earlier pin already in this file (RE-067 / NONCLAIM 16: they are
the client's text-label COLOR, not a model selector).  :func:`drop_element_
with_model_type`, :func:`drop_collection_pc_with_model_type`,
:func:`drop_pc_with_model_type` and :func:`drop_frames_with_model_type`
compose the wider mask-0x16 element -- the proven mask-0x12 fields plus
this one -- sourcing the value from
``field_drop_tables.ITEMS[item_id][3]`` (already mined, already matching
ka1-B's 0..12 token table item for item; see :func:`_model_type_for_item`).
NONE OF THIS IS MEASURED: no client has ever been shown these bytes, and
this addition proves nothing about whether ``n_DROPMODEL_TYPE`` is even
read from this wire location -- only that a candidate byte the client's own
decompiled shape reserves for mask 0x04 is no longer silently absent from
what this lane CAN send.  Whether a model appears is therefore still open,
is still GT-045/GT-132's question, and this round does not close it.  It is
production code -- no scenario id, no CLI flag, ``test_only`` unchanged at
False -- gated only by the module-level :data:`DROP_MODEL_TYPE_FIELD_
ENABLED`, and ~~it is NOT (yet) reached by :func:`drop_frames`, the
function ``runtime.py`` actually calls; see that function's own docstring
for why, and this round's CORE-REQUEST for the one-line swap that would
change it~~ IS STRUCK, ROUND KA1B-DROPMODEL FOLLOW-UP (pf-adversary caught
this citing a call site ``runtime.py`` had already stopped using two days
earlier).  The real chain, unchanged by this correction and confirmed by
grep against ``runtime.py`` at the time of writing: ``runtime.py:4921-4922``
calls ``mob_drop_presence.sustain_a_kill(self.mob_loot_cell, legacy,
drops)`` unconditionally on every server-computed mob death
(CORE-REQUEST 2246, COO-DECISION 2026-08-29T23:42, proven live by
``tests/test_mob_drop_presence_wiring.py``), which calls
:func:`refresh_frames` (this file), which -- as of THIS round, not a
pending swap -- calls :func:`drop_frames_with_model_type`, not
:func:`drop_frames`.  So the mask-0x16 element IS reached by the production
dispatch path today; see :func:`refresh_frames`'s own docstring and
NONCLAIM 23 for the one-line rollback if that turns out to be wrong.

PROVENANCE OF EVERY CLAIM THE CODE MAKES
----------------------------------------
* [STATIC, survived adversarial re-derive in GT-042] The 0x5F85B0 element
  shape: key (tag 0x14 u32, +0x10), dirty mask (tag 0x0B, +0x28), then per
  mask bit in order -- 0x02 -> tag 0x14 u32 (+0x14), 0x04 -> tag 0x0F u16
  (+0x18), 0x08 -> tag 0x05 u8 (+0x1B), 0x10 -> three tag 0x2A f32 (+0x1C,
  +0x20, +0x24), 0x20 -> tag 0x08 u8 (+0x1A).  This lane emits mask 0x12 --
  position and the payload dword -- which is the ONE combination that has
  been on a real client's wire.
* [STATIC] The envelope is the proven RuntimeRes v4 envelope, with the derived
  change-mask byte 0x08 selecting the list, and ~~ONE element per frame~~ ONE
  GENERATION PER KILL, carrying every element of that kill (STRUCK and
  replaced round ``zxnwtd`` on ``RE-130``, DONE/PASS: the consumer's codec
  loop takes ``count > 1`` and every nonempty generation ERASES the keys it
  omits, so the old shape could leave only the last drop of a multi-drop kill
  in the client's keyed tree.  A ONE-drop kill still composes the same 44
  bytes GT-045 measured, and since ``drop_frames`` routes that case through
  ``drop_pc``, the 44-byte and envelope pins are asserted on every emission,
  in the server, not only in a test.  A WIDER generation has NEVER been
  in front of a client -- see NONCLAIM 22, which says so and names the
  rollback.)
  ~~"a combined multi-record derived-mask collection is the one shape a real
  client has already rejected with ErrorData=28317"~~ IS STRUCK (round
  ``kfs01z``): 28317 = 0x6E9D = GSCN_RunTimeProtocolRes, the class id the
  client echoes back for WHICHEVER envelope failed to deserialize.  It is a
  parse-failure echo, not a count report -- ``world_population.py:104-113``
  and ``reports/PF_DELETE_SOFT002_NATURAL_0x36DB_DECODE_20260818.md`` decoded
  that on 2026-08-18, and every live reproduction listed there is a
  RuntimeRes stream-tail/misalignment fault.  V43 (six actors, same number)
  therefore gives an INTERVAL, not a cause, and it was measured on the
  mask-0x02 actor list, not on this 0x08 list at all.  ~~One element per frame
  is what this lane SHIPS~~ -- no longer true of what it SHIPS (see above);
  still true of what has been on a real wire, and that gap is GT-132.  ~~"it is not a
  restriction the client has been shown to impose"~~ IS ITSELF STRUCK in the
  same round that wrote it (pf-adversary, D14): a real client DID refuse the
  one combined multi-record stream ever sent to it (V43).  What is not shown
  is that the COUNT was the cause, and nothing about that run transfers to
  this 0x08 list, which has never carried a count>1 frame at all.
* [MEASURED, committed tables] Every rate, weight, quantity span and item id
  comes from ``field_drop_tables``, generated by
  ``tools/pf_mine_scene_drop_tables.py`` from the committed CONSTDATA tables
  with four controls it refuses on; the set-id rule ``prefix * 100000 + n_ID``
  is the round-100 fact pack's, verified there on the full data.
* [OUR DESIGN] The ROLL ORDER, the meaning of a percentage rate, the map from
  a uniform draw to a quantity, the cumulative-threshold weighted walk and the
  with-replacement multi-pick are ours -- the original server's roll order and
  RNG are unrecoverable forever.  The THREE PRIMITIVES are deliberately
  identical to ``loot_roll``'s and ``tests/test_mob_loot.py`` pins them against
  that module value by value.  ~~"so the project has one roll semantics and not
  two"~~ IS STRUCK: the primitives agree, the SET-LEVEL STREAMS DO NOT, and the
  three places they diverge are named here rather than left for someone to
  discover from a bug report -
    1. ``loot_roll`` draws an extra quality value per DROPS_EQUIPMENT pick;
       this lane rolls no quality at all (NONCLAIM 9), so the same mob with the
       same seed yields different loot in the two modules from that pick on.
    2. ``loot_roll`` refuses a rate outside 0..100 BEFORE consuming a draw;
       this lane refuses it too (REFUSE_RATE_OUT_OF_RANGE) but AFTER the rate
       draw, because its stream must not depend on the table's contents.
    3. An inverted quantity span costs ``loot_roll`` zero draws and costs this
       lane two, for the same reason as 2.
  (This module does not IMPORT ``loot_roll``: that module states as part of its
  own contract that nothing in ``src/`` imports it and that it is unreachable
  from production dispatch, and a production import would make its own
  docstring false.)
* [OUR DESIGN] The ground layout: row N of a kill is announced at the death
  position offset by ``DROP_SCATTER_STEP`` * N on X.  30.0 units is the only
  offset any attended run has put on the wire; MULTIPLYING it is ours and is
  measured by nobody -- row 12 of a twelve-item roll is 330 units from the
  corpse, which is far enough that a player may never see it (NONCLAIM 14).
* [OUR DESIGN] The element key block.  The list's key space has no proven
  allocation rule anywhere in this project; this lane allocates from
  ``DROP_KEY_BASE`` upward so its keys cannot collide with the small keys the
  probe lanes compose (1 and 2 in HYP-PF-032, 3 and 4 in HYP-PF-039) or with
  the actor identity range this scene's monsters use (0x2000..0x20FF), and
  refuses any key outside its own block.  Only 1 and 2 have ever reached a
  client; 3 and 4 exist in a lane that has not been run.

WHAT THIS MODULE IS NOT.  PURE SERVER LOGIC WITH ONE COMPOSER.  It opens no
socket, touches no database, boots no server, reads no file, keeps no global
state, calls no clock and never touches the module-global ``random`` (the
caller injects a ``random.Random``; see DETERMINISM).  Importing it has no side
effects.

DETERMINISM.  Every stochastic decision is a draw from an INJECTED
``random.Random`` -- the type is ENFORCED, not requested, because a caller who
passes the module-global ``random`` makes this paragraph false and no test
inside this file would ever see it -- taken through ``rng.random()`` and
nothing else.  Same
tables + same mob + same seed produce identical results in any process, and
the draw stream does not depend on whether a row decodes: a slot that wins its
rate roll consumes its quantity draw even when its item id is then refused.

THE LINE THIS LANE NEEDS FROM THE CHIEF is :data:`MOB_LOOT_WIRING`.  It is one
call after the death frames of ``mob_death``, and it is written there rather
than only in a letter, because letters get lost.
"""

from __future__ import annotations

import collections as _collections
from dataclasses import dataclass
import hashlib
import math
import random as _random
import struct
import threading
import time as _time
from typing import Any

from . import field_drop_tables
from .field_mobs import FieldMob


MOB_LOOT_MILESTONE = "MOB-LOOT-001"
MOB_LOOT_BUILD_ORDER = "BUILD-006 / M5 first half"
MOB_LOOT_LANE = "B_COMBAT"

MOB_LOOT_WIRING = (
    "runtime.py.  Hold ONE mob_loot.DropLedgerCell for the scene -- the cell "
    "is the owner of the ledger and the reason this line is now three calls "
    "instead of five: an earlier version asked you to carry a generation by "
    "hand, and a caller holding a value can always satisfy that check against "
    "the same object it is holding, which is not a lock at all.\n"
    "  For a kill that commit_death() ACCEPTED:\n"
    "  1. roll = mob_loot.roll_drops(mob, rng)   # rng must be a "
    "random.Random the server owns; SystemRandom and the module-global stream "
    "are refused by name\n"
    "  2. drops = cell.loot_a_kill(mob, death_step.record, roll, "
    "kill_token=death_step.register.generation, position=<where it fell, or "
    "None for its placement position>)\n"
    "     - death_step.record, NOT the outcome: the outcome is true of a hit "
    "that landed on a corpse too.\n"
    "     - the kill token must RISE with each real death.  The register "
    "generation does; a constant would refuse every kill after the first, and "
    "a respawned monster killed again is a NEW death and is accepted.\n"
    "     - a refusal leaves the cell untouched.  ledger_generation_moved and "
    "ledger_stale mean try again; mob_already_looted means this death was "
    "already looted and you must NOT retry it in a loop.\n"
    "  3. send every frame of mob_loot.drop_frames(legacy, drops) AFTER "
    "death_step.dead_frame -- i.e. after the whole death schedule including "
    "hold_ms -- in the order returned (~~'one frame each'~~ IS STRUCK, round "
    "zxnwtd: a kill's drops now travel as ONE generation, so the tuple has "
    "one pair in it.  Iterating it is still the contract).  NOT between the "
    "dying "
    "and dead frames: nothing measured says a derived-mask-0x08 RuntimeRes "
    "may be interleaved into another lane's typed lethal sequence for the "
    "same actor, and the label lives 0.2-0.4 s, so loot sent inside the hold "
    "is gone before the corpse frame is.\n"
    "  4. PRUNE THROUGH THE CELL.  ~~'Nothing in this module expires a row "
    "... a caller that never prunes grows the ledger without bound'~~ IS "
    "STRUCK, round 0n9inw: the cell now expires its own rows "
    "(DROP_LIFETIME_SECONDS, evaluated lazily when you touch the cell -- no "
    "thread, no timer), per COO-DECISION 2026-08-29T12:41+07:00.  A caller "
    "that never prunes NO LONGER grows the ledger without bound.  YOU STILL "
    "WANT THE PRUNE, for the other reason: RE-130 says a nonempty generation "
    "erases the keys it omits, so the prune is what keeps the CLIENT'S list "
    "narrow.  The expiry bounds the SERVER'S cell.  Pruning beside the "
    "cell, on a value you kept, loses whatever a kill wrote in between.\n"
    "  4-ROUND-uq2lxw2, AND READ THIS BEFORE WRITING cell.take(key) IN A "
    "LOOP: taking every key of the kill you just sent -- which is what "
    "runtime.py does today, and what the sentence above was read as "
    "asking for -- makes a pickup call site refuse drop_already_taken "
    "100% of the time.  MEASURED by chief in round ni2wh2 with a "
    "control (pf_bridge notes_to_chief/20260829_1221_CHIEF-ASK-COO-"
    "gt124-opcode-forbidden-and-drops-pruned.md, section 2): prune as "
    "runtime does -> 0 live rows, refused; do not prune -> 2 live rows, "
    "accepted.  CALL cell.prune_previous_kills() INSTEAD, once, after "
    "step 3: it derives its own cut point from the cell (the newest "
    "kill's first key), takes no argument to get wrong, leaves the "
    "newest kill's rows on the ground for the player who is reaching "
    "for them, and still bounds the ledger.  ~~CALL cell.prune_previous_"
    "kills() INSTEAD~~ IS ITSELF STRUCK, round 4e9r7g, and pf-adversary is "
    "why: it cuts by KEY, keys are issued from ONE block across every scene, "
    "so after a scene boundary the rows it calls 'older' are the ones "
    "standing in the scene the player just left -- which COO-DECISION "
    "2026-09-02T02:53+07:00 forbids removing until a removal publisher "
    "exists.  A chief following this step would have destroyed the previous "
    "scene's whole ground on the first kill in the new one.  DO NOT CALL IT: "
    "what bounds the ledger today is the per-drop expiry plus the trim "
    "inside mob_drop_presence.sustain_a_kill, which is what runtime.py "
    "already does, and RE-130's narrowness is now served by the scene filter "
    "instead -- a publication carries one scene's rows, not the world's.  "
    "~~'[ASSUMPTION OF LANE B - "
    "AWAITING COO] chief asked the COO what replaces the ledger ceiling "
    "(a timer, a per-drop expiry); the ruling may still name a different "
    "one'~~ IS STRUCK, round 0n9inw -- THE RULING CAME AND IT NAMED THE "
    "PER-DROP EXPIRY (COO-DECISION 2026-08-29T12:41+07:00, evaluated lazily "
    "at insert and dispatch, explicitly not a background timer).  It is "
    "built, it is on by default, and it needs NOTHING from this call site.  "
    "The prune stays for RE-130's reason, not for the ceiling's.\n"
    "  4c. AND A REFUSAL YOU MUST NOT COLLAPSE, round 0n9inw: cell.take(key) "
    "now raises drop_expired for a row whose deadline passed, which is a "
    "DIFFERENT name from drop_already_taken.  A pickup call site that maps "
    "both to one message tells a player 'somebody beat you to it' when "
    "nobody was there.\n"
    "  4b. AND SINCE RE-130 THE PRUNE HAS A COST THIS CONTRACT OWES THE "
    "CALLER, round zxnwtd.  The consumer erases every key a nonempty "
    "generation omits, so a generation built from ONE kill's rows removes "
    "the previous kill's drops from the client's list.  Pruning each row "
    "right after its own kill's frame is what makes the next generation "
    "narrow.  THE ALTERNATIVE, and it is the caller's call because the call "
    "site is not this lane's file: keep the rows and send "
    "cell.frames(legacy) -- the WHOLE live ledger as one generation -- once "
    "per kill.  That is a shape change, not a cadence change, so the COO's "
    "2026-08-26 refusal in step 5 does not cover it; what it does need is an "
    "expiry or a pickup, because without one the ledger and the generation "
    "both grow without bound.  This lane states the option here rather than "
    "only in a letter, and does not take it unilaterally.\n"
    "  5. nothing else, and ONE ANNOUNCEMENT PER DROP -- each drop announced "
    "ONCE and never re-announced.  It is a CADENCE rule, not a frame-count "
    "rule, and round zxnwtd did not touch it: after that round the one "
    "announcement of a kill's drops is one shared generation instead of one "
    "frame each.  The COO REFUSED this "
    "lane's assumption 4 on 2026-08-26 (07:45 +07:00): DROP_REFRESH_MS may "
    "not be wired into a production path, because 12.5 frames a second per "
    "row is too much to spend on a mechanism nobody has measured.  "
    "cell.frames(legacy) "
    "and refresh_frames() remain EXPERIMENT TOOLS -- do not put either on a "
    "timer in runtime.py.  What reopens the question is a measurement of the "
    "label's lifetime from real play, not a cheaper number.\n"
    "  6. SCENE TRANSITION.  ~~call cell.reconcile_scene_transition() ONCE at "
    "the scene boundary~~ IS STRUCK, round 4e9r7g, and runtime.py was RIGHT "
    "not to have wired it (its own comment at the boundary says so): "
    "COO-DECISION 2026-09-02T02:52+07:00 chose WAY 1 -- bind ownership to the "
    "scene -- and reconcile DELETES rows, which COO-DECISION 2026-09-02T02:53 "
    "+07:00 forbids until a removal publisher exists.  WHAT TO CALL INSTEAD, "
    "~~one line, at the SAME boundary (right where mob_combat_scene_folder is "
    "assigned)~~ -- BOTH HALVES OF THAT ARE STRUCK, round 9jrsei: it is two "
    "lines now (see below), and pf-adversary D3 MEASURED that the place it "
    "named is not a scene boundary a walking player crosses.  "
    "_sync_combat_scene_state has three callers: _dispatch_mob_combat (which "
    "returns early unless the packet is an ActionVital at a positive "
    "non-self target -- i.e. THE PLAYER SWUNG AT SOMETHING) and two sites "
    "behind the once-per-session `not self.world_census_sent` latch.  Wired "
    "there and nowhere else, 'walk out and back and your ground is "
    "re-announced' becomes 'walk out and back AND ATTACK SOMETHING'.  SO THE "
    "ASK IS: call it where the session actually learns the scene changed -- "
    "the GM-warp / scene-sync path that assigns the new folder for a "
    "MOVEMENT, not only the combat one -- before the first publish in the "
    "new scene:\n"
    "       ~~self.mob_loot_cell.enter_scene(folder)~~ IS SUPERSEDED, round "
    "9jrsei, by COO-DECISION 2026-09-02T09:44+07:00, which answered the open "
    "question below.  THE LINE TO WRITE IS NOW TWO, and the second one is the "
    "half a player can see:\n"
    "       _prev, _now, _elsewhere, _expired, ground = ("
    "self.mob_loot_cell.enter_scene_frames(legacy, folder))\n"
    "       # then send every (pc, frame) in `ground`, in order, like a "
    "kill's drop frames.  It is EMPTY for a scene with no drops standing, "
    "and then you send nothing.\n"
    "     ORDERING, AND IT IS NOT OPTIONAL (pf-adversary D4, round 9jrsei).  "
    "RE-130: the LAST nonempty generation a client receives is the one that "
    "survives, and it ERASES every key it omits.  So these frames must go "
    "out BEFORE any other ground generation composed in the same dispatch.  "
    "If a kill lands in the same dispatch, sustain_a_kill's generation "
    "carries the whole scene (this kill's rows AND the ones the boundary "
    "just re-announced), so kill-last is correct and boundary-last is NOT: "
    "appending the stashed boundary frames after the kill's rolls the "
    "client's ground back to the state it had BEFORE the player's newest "
    "kill, and the object they just earned is the one that disappears.\n"
    "     enter_scene(folder) still exists and still does exactly what it "
    "did; enter_scene_frames is that call plus the entered scene's own "
    "generation, composed from one snapshot.\n"
    "     It removes nothing FOR BEING A BOUNDARY (its own lazy expiry can "
    "still collect rows whose 120 s deadline had passed; the call returns "
    "how many, as its fourth element): scene A's drops keep standing in "
    "scene A and stay out of scene B's publications.  READ THIS BEFORE "
    "QUOTING IT TO A PLAYER, round 4e9r7g / pf-adversary: 'still there when "
    "the player walks back' is true of the SERVER's ledger and NOT of the "
    "client's screen.  RE-130 says scene B's first publication erases the "
    "keys it omits, and ~~the only emitter is sustain_a_kill, which needs a "
    "KILL -- so a player who returns to scene A sees the drop again only "
    "when something else dies in scene A, inside what is left of the "
    "120 s~~ IS STRUCK, round 9jrsei, AND ITS TWO-LAYER FORM IS KEPT "
    "(COO-DECISION 2026-09-02T09:44+07:00 item 2 orders the server layer and "
    "the screen layer written separately until a GT measures the second).  "
    "SERVER LAYER, and this is what this lane can prove: the boundary now "
    "COMPOSES AND HANDS YOU the entered scene's generation, so nothing else "
    "has to die for those bytes to exist.  SCREEN LAYER, unmeasured: what a "
    "client does with a generation sent at a boundary has never been "
    "watched, and NONCLAIM 1 of this module is the ceiling on any promise "
    "made here -- GT-045 measured a floating NAME LABEL plus dust for "
    "0.2-0.3 s and NO OBJECT under it.  Anybody quoting this to the owner "
    "quotes both layers or neither.  "
    "~~WHO RE-ANNOUNCES A SCENE'S GROUND ON RE-ENTRY IS AN OPEN QUESTION~~ "
    "IS ANSWERED, round 9jrsei: COO-DECISION 2026-09-02T09:44+07:00 rules "
    "that the boundary itself re-announces it -- ONE generation, only when "
    "the entered scene has rows -- because that is an EVENT and not the "
    "cadence refused on 2026-08-26.  That is why the line above is now "
    "enter_scene_frames.  ~~Calling it for the scene the cell is already in "
    "is a no-op, so it is safe to call on every sync~~ IS STRUCK, round "
    "9jrsei (pf-adversary D2): that was true of enter_scene, which composes "
    "nothing, and carrying it to a method that DOES compose measured five "
    "full ground generations for five same-scene calls -- a cadence, the "
    "refused thing, reached through the method that says it is not one.  "
    "enter_scene_frames now publishes ONLY when previous != current, so "
    "calling it on every sync is safe again AND means one generation per "
    "crossing.  WITHOUT IT "
    "the cell keeps publishing for whatever scene its last kill was in, and "
    "before the FIRST kill of a boot it does not know a scene at all, so "
    "mob_drop_presence.sustain_a_kill returns "
    "refused_cell_has_no_scene_to_publish and sends nothing (fail-closed, by "
    "name, never 'send them all').  This is a NEW call site this lane cannot "
    "add itself -- runtime.py owns the scene-sync path -- named here rather "
    "than only in a letter, per this round's own CORE-REQUEST.\n"
    "  7. THE OTHER RUNTIMERES FRAMES, ADDED round ewm6ff.  app.py's "
    "install_ground_heartbeat_preserve substitutes the PRESERVE body for ONE "
    "caller (co_name == 'heartbeat_worker').  v141's make_runtime_vitals ends "
    "on an EMPTY derived change mask and never reaches that wrapper, so the "
    "VitalData responses it composes carry no ground list -- re-derived from "
    "the frozen file's own AST by tests/test_mob_loot_preserve_runtime_res.py, "
    "not taken from a capture corpus.\\n"
    "     ~~'The ask is ONE wrap in app.py: wrap legacy.make_runtime_vitals so "
    "its (pc, frame) passes through this lane's preserve function.'~~ THAT ASK "
    "IS WITHDRAWN, same round, before it was acted on.  pf-adversary installed "
    "exactly that wrapper and MEASURED what it does: mob_pickup.bag_delta_pc "
    "(mob_pickup.py:1786) re-derives its own pc through make_runtime_vitals "
    "and compares it byte for byte against DELTA_PC_PREFIX_PIN, so the wrap "
    "makes EVERY PICKUP REFUSE (composed_bytes_off_pin, 74 bytes vs 71) while "
    "a drop is on the ground -- the exact state this lane exists to create; "
    "and delete_refresh_hypothesis.make_delete_actor_list_rebuild_response "
    "(:347) dies with 'derived-class mask drift'.  Nine other modules call "
    "that composer, several with byte pins of their own.  A blanket wrap is "
    "the wrong shape and the measurement says so.\\n"
    "     THE ASK THAT REPLACES IT is per call site, not global: at an "
    "emission site that must preserve the ground, call "
    "mob_loot.preserve_ground_in_runtime_res_vitals(legacy, vitals) INSTEAD "
    "of legacy.make_runtime_vitals -- same arguments, same (pc, frame) "
    "back (the call is spelled without its argument list here on purpose: "
    "tools/pf_runtimeres_actor_entry_static.py counts CALL SITES with a "
    "regex, and prose that looks like one inflates that census).  "
    "The body is byte-identical; only the trailing mask record differs.  Each "
    "site is its own audit, because a site with a byte pin has to move its pin "
    "with it.  WHICH sites must preserve is a question for the COO and not one "
    "this lane may answer by wrapping them all at once.  This lane's own "
    "emission path (the MOB_LOOT block, steps 1-3 above) does not go through "
    "make_runtime_vitals at all and needs nothing here."
)

production_allowed = True
test_only = False

# ---------------------------------------------------------------------------
# Wire pins.  Every value here is cross-pinned in tests against the probe lane
# that measured it; none of them is chosen by this module.
# ---------------------------------------------------------------------------
RUNTIME_DERIVED_BIT_GROUND_LIST = 0x08   # derived change-mask -> object +0x20
ELEMENT_MASK_POSITION_AND_DWORD = 0x12   # 0x10 position | 0x02 dword at +0x14
ELEMENT_KEY_TAG = 0x14                   # +0x10, always on the wire
ELEMENT_MASK_TAG = 0x0B                  # +0x28 dirty mask
ELEMENT_PAYLOAD_TAG = 0x14               # +0x14, mask bit 0x02
ELEMENT_F32_TAG = 0x2A                   # +0x1C / +0x20 / +0x24
ELEMENT_LIST_COUNT_TAG = 0x12
# ---------------------------------------------------------------------------
# ROUND KA1B-DROPMODEL -- MASK 0x04, n_DROPMODEL_TYPE.  ka1-B's letter
# (pf_bridge notes_to_chief/20260901_2015_KA1B-TO-LANE-B-drop-model-
# selector-field-is-not-on-our-wire.md, [HYPOTHESIS, unproven]) reads
# GT-045's own open question -- "what makes a model appear is the OPEN
# question of that ticket" (see the module docstring above) -- as a field
# this lane has simply never sent, and names three candidates from the
# SAME static element-shape table this file already cites (GT-042).  TWO of
# the three are RULED OUT already, not by this letter but by an EARLIER pin
# in this file: NONCLAIM 16 / RE-067 pinned mask 0x08 (tag 0x05, +0x1B) and
# mask 0x20 (tag 0x08, +0x1A) as the client's TEXT-LABEL-COLOR property, P-2
# territory this lane does not own.  That leaves mask 0x04 (tag 0x0F, u16,
# +0x18) as the one candidate nothing has pinned to something else -- it is
# still [DERIVED, not yet client-measured] itself, just not contradicted.
ELEMENT_MODEL_TYPE_TAG = 0x0F            # +0x18, mask bit 0x04, u16
ELEMENT_MASK_MODEL_TYPE_BIT = 0x04
# mask 0x12 (the proven position+payload shape) | 0x04 (this round's
# untested candidate) = 0x16.
ELEMENT_MASK_WITH_MODEL_TYPE = (
    ELEMENT_MASK_POSITION_AND_DWORD | ELEMENT_MASK_MODEL_TYPE_BIT)
ENVELOPE_VERSION = 4
DROP_PC_SIZE = 44                        # one element, pinned by GT-045
DROP_FRAME_SIZE = 54                     # the same pc, framed
DROP_COORD_SPANS = ((30, 34), (35, 39), (40, 44))
DROP_FRAME_COORD_SHIFT = 10
# The 17 bytes in front of the element are the SAME for every drop this lane
# will ever send (message id, zero id, version, inherited mask, derived mask,
# count of one), so unlike the element they can be pinned as literal bytes and
# compared at RUN TIME, in the server, on every emission.  Without this the
# element was dual-derived and the envelope was taken on the legacy module's
# word: a v142 shim with a moved constant would have shipped bytes no client
# has accepted, and the only thing that would have gone red is a test, which
# does not run inside a server.
DROP_ENVELOPE_PIN = bytes((
    0x12, 0x9D, 0x6E,              # u16 tag 0x12, GSCN_RunTimeProtocolRes
    0x14, 0x00, 0x00, 0x00, 0x00,  # u32 tag 0x14, id 0
    0x08, 0x04,                    # u8  tag 0x08, envelope version 4
    0x0B, 0x00,                    # u8  tag 0x0B, inherited mask: none
    0x0B, 0x08,                    # u8  tag 0x0B, derived mask: the 0x08 list
    0x12, 0x01, 0x00,              # u16 tag 0x12, ONE element
))
DROP_ENVELOPE_SIZE = len(DROP_ENVELOPE_PIN)
# The count is the ONLY field of that envelope that varies with the number of
# drops, so the pin is split rather than duplicated: bytes 0..13 are constant
# for every generation this lane will ever send, and bytes 14..16 are the u16
# count record whose value is the element count.  A one-element generation
# still has to compose to DROP_ENVELOPE_PIN byte for byte -- that is asserted
# below and in tests -- so nothing about the shape measured by GT-045 moves.
DROP_ENVELOPE_CONSTANT_PIN = DROP_ENVELOPE_PIN[:14]
DROP_ENVELOPE_CONSTANT_SIZE = len(DROP_ENVELOPE_CONSTANT_PIN)
DROP_ELEMENT_SIZE = DROP_PC_SIZE - DROP_ENVELOPE_SIZE   # 27, one element
# Coordinate spans of ONE element, relative to that element's first byte.
# Derived from the pc-relative spans above rather than typed again, so a round
# that moves the pc pin moves this with it instead of past it.
DROP_ELEMENT_COORD_SPANS = tuple(
    (start - DROP_ENVELOPE_SIZE, end - DROP_ENVELOPE_SIZE)
    for start, end in DROP_COORD_SPANS
)
# An emitter ceiling, and it is OURS, not a client fact.  Two reasons, both
# ours: the count record is a u16, and ``snappy_raw_literal`` splits anything
# over 65536 bytes into several literal runs, which is a framing shape this
# lane has never composed and does not re-derive.  Refusing above it is how
# this lane avoids emitting a frame shape it cannot check.  RE-130 found no
# upper bound in the consumer and this constant must never be cited as one.
DROP_MAX_ELEMENTS_PER_FRAME = (0x10000 - DROP_ENVELOPE_SIZE) // DROP_ELEMENT_SIZE
# And the ten bytes in front of the PC, for the same reason and because the
# first adversarial repair stopped at the pc: the client's dispatcher reads
# these FIRST.  For a fixed 44-byte pc they are entirely constant -- the V141
# frame magic, the compressed length, and the snappy raw-literal header -- so
# a shim that moved the magic or flipped the length byte order shipped 54
# bytes that passed every length and coordinate check this lane had.
DROP_FRAME_HEADER_PIN = bytes((
    0xAC, 0x3E, 0x25, 0x5F,        # MAGIC 0x5F253EAC, little endian
    0x2E, 0x00, 0x00, 0x00,        # compressed length, 46
    0x2C, 0xAC,                    # snappy raw literal header for 44 bytes
))
DROP_FRAME_HEADER_SIZE = len(DROP_FRAME_HEADER_PIN)
# The four magic bytes are the only part of that header that does not move
# with the body length, so a generation of any width can still be checked
# against them at run time.
DROP_FRAME_MAGIC_PIN = DROP_FRAME_HEADER_PIN[:4]
#: The legacy encoder's literal-chunk stride (v141:564), transcribed with it.
SNAPPY_LITERAL_CHUNK = 65536

# ---------------------------------------------------------------------------
# The mask-0x16 element sizes.  Same 27 bytes as DROP_ELEMENT_SIZE above,
# plus the model-type field -- one tag byte (ELEMENT_MODEL_TYPE_TAG) and one
# little-endian u16 value -- inserted where ELEMENT_FIELD_ORDER's own
# ascending-bit-order convention puts it: after the mask-0x02 payload dword
# this lane already sends, and before the mask-0x10 coordinate triple.
# [DERIVED, not yet client-measured]: unlike DROP_ENVELOPE_PIN and the
# 44-byte DROP_PC_SIZE, nothing here is pinned to bytes a real client took --
# only the ARITHMETIC (existing element + 1 tag byte + 2 value bytes) is
# asserted, at run time, by drop_collection_pc_with_model_type below.
# ---------------------------------------------------------------------------
DROP_ELEMENT_MODEL_TYPE_FIELD_SIZE = 3     # 1 tag byte + u16 little-endian
DROP_ELEMENT_SIZE_WITH_MODEL_TYPE = (
    DROP_ELEMENT_SIZE + DROP_ELEMENT_MODEL_TYPE_FIELD_SIZE)      # 30
DROP_PC_SIZE_WITH_MODEL_TYPE = (
    DROP_ENVELOPE_SIZE + DROP_ELEMENT_SIZE_WITH_MODEL_TYPE)      # 47
# A snappy raw-literal header for a pc THIS SHORT never changes shape (a
# one-byte varint length, a one-byte extended-literal tag) for any length
# <= 60 -- DROP_PC_SIZE_WITH_MODEL_TYPE (47) is inside that range the same
# way DROP_PC_SIZE (44) is -- so the header stays DROP_FRAME_HEADER_SIZE
# bytes long; only its CONTENT bytes differ, and they are not hand-typed
# here for the same [DERIVED] reason as above.  drop_frames_with_model_type
# checks the arithmetic below against a REALLY COMPOSED frame at run time,
# so a wrong assumption here fails loudly instead of shipping quietly.
DROP_FRAME_SIZE_WITH_MODEL_TYPE = (
    DROP_PC_SIZE_WITH_MODEL_TYPE + DROP_FRAME_HEADER_SIZE)       # 57
# Coordinate spans of ONE wide element, relative to that element's first
# byte -- the narrow spans shifted right by the model-type field's width,
# derived rather than typed again for the same reason DROP_ELEMENT_COORD_
# SPANS is derived from DROP_COORD_SPANS.
DROP_ELEMENT_COORD_SPANS_WITH_MODEL_TYPE = tuple(
    (start + DROP_ELEMENT_MODEL_TYPE_FIELD_SIZE,
     end + DROP_ELEMENT_MODEL_TYPE_FIELD_SIZE)
    for start, end in DROP_ELEMENT_COORD_SPANS
)
# Element-relative span of the model-type field's VALUE bytes (the u16, not
# its tag byte).  The tag byte sits exactly where the narrow element's first
# coordinate tag used to sit -- one byte before DROP_ELEMENT_COORD_SPANS'
# first span -- because the model-type field is inserted immediately in
# front of the coordinate triple.
_MODEL_TYPE_TAG_ELEMENT_OFFSET = DROP_ELEMENT_COORD_SPANS[0][0] - 1
DROP_ELEMENT_MODEL_TYPE_SPAN = (
    _MODEL_TYPE_TAG_ELEMENT_OFFSET + 1, _MODEL_TYPE_TAG_ELEMENT_OFFSET + 3)
# An emitter ceiling for the wide element, same reasoning as
# DROP_MAX_ELEMENTS_PER_FRAME and OURS for the same two reasons: it is
# smaller than the narrow ceiling because each wide element costs 3 more
# bytes.
DROP_MAX_ELEMENTS_PER_FRAME_WITH_MODEL_TYPE = (
    (0x10000 - DROP_ENVELOPE_SIZE) // DROP_ELEMENT_SIZE_WITH_MODEL_TYPE)

# The list codec's element field order, re-derived from the same span
# [0x005F85B0,0x005F8869) sha256 ce0a58f7.. that GT-040/GT-042 pinned.
ELEMENT_FIELD_ORDER = (
    "key_u32_tag14",
    "dirty_mask_u8_tag0B",
    "payload_u32_tag14",
    "x_f32_tag2A",
    "y_f32_tag2A",
    "z_f32_tag2A",
)
# The mask-0x16 sibling: the same fields, with the model-type field inserted
# in the ascending-bit-order slot ELEMENT_FIELD_ORDER's own comment
# describes (0x02 before 0x04 before 0x10).  [DERIVED, not yet
# client-measured] -- this ordering is this module's own convention applied
# to a new field, not a re-derivation of anything GT-040/GT-042 measured.
ELEMENT_FIELD_ORDER_WITH_MODEL_TYPE = (
    "key_u32_tag14",
    "dirty_mask_u8_tag0B",
    "payload_u32_tag14",
    "model_type_u16_tag0F",
    "x_f32_tag2A",
    "y_f32_tag2A",
    "z_f32_tag2A",
)

# ---------------------------------------------------------------------------
# Lane constants that are OURS.  Each one is named so a reader can see it is a
# decision, and each is repeated in MOB_LOOT_NONCLAIMS if it is unmeasured.
# ---------------------------------------------------------------------------
DROP_KEY_BASE = 0x00100000
DROP_KEY_LIMIT = 0x00200000
DROP_SCATTER_STEP = 30.0
# The arithmetic, written out rather than tuned: a re-emission is on screen
# about WIRE_TO_SCREEN_SECONDS after it is sent, and the label it is meant to
# replace may die as early as the LOW end of its range, so a cadence that
# cannot leave a gap is at most (0.2 - 0.12) = 0.08 s.  That is 12.5 frames a
# second PER LIVE ROW of a message a real client has been shown twice in its
# life, which is the real reason this stays an experiment: the honest cadence
# is unaffordable, and the affordable ones (200 ms, which this constant was
# before an adversarial pass did the subtraction) are arithmetically
# guaranteed to blink.  Whether re-emission redraws anything at all is
# unmeasured either way -- NONCLAIM 12.
#
# OVERTURNED BY THE COO, 2026-08-26 07:45 +07:00, and the ruling is recorded
# here rather than only in a letter (COO-DECISION, notes_to_chief/
# 20260826_0745_COO-DECISION-M5-stays-whole-M5a-ships-now.md, section 1a):
# this lane's assumption 4 is REFUSED.  DROP_REFRESH_MS MAY NOT BE WIRED INTO
# A PRODUCTION PATH -- 12.5 frames a second per row is too much to spend on a
# mechanism nobody has measured.  refresh_frames() stays as an EXPERIMENT
# TOOL and the production behaviour is ONE ANNOUNCEMENT PER DROP -- once per
# drop, never re-announced, which is a CADENCE rule and not a frame-count one
# (round zxnwtd made that one announcement a shared generation and did not
# touch the cadence) -- until
# somebody measures the label's lifetime from real play.  The constant is kept
# (deleting it would delete the arithmetic that argues against it) and the
# wiring line no longer offers it.
DROP_REFRESH_MS_IS_EXPERIMENT_ONLY = True
DROP_REFRESH_MS = 80
MAX_DROPS_PER_KILL = 16

# ---------------------------------------------------------------------------
# ROUND KA1B-DROPMODEL -- n_DROPMODEL_TYPE, SHIPPED BUT ~~NOT (YET) THE
# PROVEN CALL SITE'S DEFAULT~~ IS STRUCK, ROUND KA1B-DROPMODEL FOLLOW-UP,
# 2026-09-01, PF-ADVERSARY: it is now the proven call site's default; see
# below.  [ASSUMPTION OF LANE B - awaiting COO confirmation]
# Following NONCLAIM 22's own precedent -- additive, reversible, so ship it
# unflagged and let an attended run falsify it cheaply -- this flag is True
# by default and gates :func:`drop_frames_with_model_type` (and the
# mask-0x16 composers under it), which is production code: no scenario id,
# no dispatch kwarg, no CLI switch, ``test_only`` for this module is still
# False.  It does NOT gate :func:`drop_frames` itself -- that function is
# UNCHANGED and still composes only the proven mask-0x12 shape, forever, for
# whatever still calls it directly (this file's own tests, and any future
# caller that wants the narrow shape by name).
# ~~:data:`MOB_LOOT_WIRING` and NONCLAIM 1 both name ``drop_frames`` as the
# literal call site ``runtime.py`` already invokes unconditionally on every
# server-computed mob death ... Making ``drop_frames`` itself pick the wide
# mask would silently break every one of those pins ... So the wide path
# ships as its OWN always-callable function instead ... and the one-line ask
# that would make it the live call site's default is this round's
# CORE-REQUEST, not a change made here to runtime.py, which this lane may
# not edit~~ IS STRUCK, ROUND KA1B-DROPMODEL FOLLOW-UP: the premise was
# wrong.  ``runtime.py`` does not call ``drop_frames`` at all (it has not
# since CORE-REQUEST 2246 / COO-DECISION 2026-08-29T23:42 rewired it through
# ``mob_drop_presence.sustain_a_kill`` -> :func:`refresh_frames`,
# ``runtime.py:4921-4922``, proven by tests/test_mob_drop_presence_wiring.py)
# -- and :func:`refresh_frames` lives IN THIS FILE, so making the wide mask
# ITS default needed no CORE-REQUEST and no edit outside this lane's own
# module.  This round did exactly that: :func:`refresh_frames` now calls
# :func:`drop_frames_with_model_type`.  The pins this paragraph worried
# about (test_ground_drop_multi_drop_emission_shape.py,
# test_mob_drop_presence*.py) all pin ``drop_frames`` directly, which this
# change never touches; the one test that pinned ``refresh_frames``'s own
# output byte-for-byte (tests/test_mob_loot.py,
# test_refreshing_re_emits_the_live_ledger_in_key_order) was updated in the
# same commit as this comment to expect the wide shape, since that is this
# round's deliberate, understood behaviour change.
# Rollback if the assumption is wrong: leave this False -- when it is False,
# :func:`drop_frames_with_model_type` returns :func:`drop_frames`'s own
# output verbatim, so :func:`refresh_frames` (and therefore
# ``runtime.py``'s live dispatch) goes straight back to the exact narrow
# bytes GT-045 measured, with no other code change.
DROP_MODEL_TYPE_FIELD_ENABLED = True

# [MEASURED, GT-045 CLOSED-ANSWERED, four attended rounds 2026-08-25]
GROUND_DROP_DOES_NOT_PERSIST = True
# Named for its SCOPE.  ~~NO_ITEM_MODEL_IS_DRAWN~~ was struck: it stated as a
# universal what was measured of ONE element, whose model-asset id is 0, in a
# frame where the second element cannot be told apart from off-camera.
NO_MODEL_UNDER_THE_LABEL_THAT_WAS_SEEN = True
# The label's life.  The frame extraction says 0.30 s; the letter that made
# that measurement attaches a MANDATORY +/-0.1 s (the recorder duplicates
# frames in threes, so the real sampling is ~10 fps) and forbids writing a
# single exact figure.  0.30 therefore MEANS 0.2-0.4, and the first version of
# this constant wrote (0.2, 0.3) -- it quoted the rule and then dropped half
# the range the rule produces.
GROUND_LABEL_MEASURED_SECONDS = 0.30
GROUND_LABEL_FRAME_SLACK_SECONDS = 0.1
GROUND_LABEL_OBSERVED_LIFETIME_SECONDS = (0.2, 0.4)
# [MEASURED, same letter] Send to pixels.  NOT a render latency: it contains
# socket travel, the recorder's queue and the same +/-0.1 s.
WIRE_TO_SCREEN_SECONDS = 0.12
# ~~0.633~~ IS STRUCK as a lifetime of THIS pipe and kept here so nobody
# re-derives it: it comes from an external video of the ORIGINAL server
# (2026-08-23 frame measurement, clip B) where the object vanished in the same
# frame as the green "received item" line.  That is a PICKUP-TERMINATED
# interval, not an expiry, and that clip contains no case of nobody picking up.
ORIGINAL_SERVER_PICKUP_TERMINATED_SECONDS = 0.633

# ---------------------------------------------------------------------------
# ROUND 0n9inw -- THE LEDGER CEILING, RULED.  COO-DECISION 2026-08-29T12:41
# +07:00 ("gt124-fix-the-prune-loop-open-the-capture-ticket-no-flags") answered
# the question round uq2lxw2 shipped under an [ASSUMPTION OF LANE B] tag: what
# replaces the ledger ceiling when runtime.py stops taking every key of the
# kill it just sent.  THE RULING: a PER-DROP EXPIRY, evaluated LAZILY at insert
# and dispatch -- explicitly NOT a background timer -- because that shape is
# deterministic, testable headless, and adds no thread.
#
# WHAT THE RULING DID NOT NAME IS THE NUMBER, and nothing measured supplies it:
#   * GROUND_LABEL_OBSERVED_LIFETIME_SECONDS (0.2-0.4) is THE LABEL'S life on
#     screen, not the row's.  The row is what makes a click succeed, and RE-130
#     is why a player clicks where nothing is drawn -- so the label's life is
#     the wrong quantity and using it would delete every drop before a player
#     could reach one.
#   * ORIGINAL_SERVER_PICKUP_TERMINATED_SECONDS (0.633) is an interval that
#     ENDED IN A PICKUP on the original server.  It bounds nothing: that clip
#     contains no case of nobody picking up.
# So the number below is this lane's own, and it is tagged as such.  It answers
# one question -- how long after a kill may a player still successfully click
# the object -- and it is sized for a player who has to walk there.
# ~~[ASSUMPTION OF LANE B - AWAITING COO]~~
# [INTERIM - COO 20260829_1444 - AWAITING MEASUREMENT] The MECHANISM is ruled
# and is not an assumption; only this figure is.  Changing it is a one-line
# change with no call-site consequence, which is why the lane took a number
# rather than waiting for one.
# COO-DECISION 2026-08-29T14:44+07:00 item 1 accepted 120.0 as an INTERIM
# default: it no longer waits on anyone, but it is still not a MEASURED
# number.  Item 2 of the same ruling opened GT-149 DROP-LIFETIME-MEASURE-001
# (kill a monster, deliberately do NOT pick the drop up, read the seconds off
# the video's own frame timestamps) -- that ticket, not this comment, is what
# replaces this figure with a measured one.  Item 3 confirmed the shape this
# lane chose: the label belongs on the FIGURE alone and must not spread to
# the mechanism.
DROP_LIFETIME_SECONDS = 120.0
#: A lifetime must be shorter than this.  Not a policy, a tripwire: a cell
#: built with a lifetime measured in days is a cell with no ceiling at all,
#: which is the exact defect the expiry exists to close.
MAX_DROP_LIFETIME_SECONDS = 3600.0
#: How many expired rows a cell remembers so it can tell a late click "your
#: object expired" instead of "no such object".  BOUNDED ON PURPOSE: the memory
#: that names the refusal must not become the unbounded growth the expiry is
#: here to prevent.  Beyond this depth a late click falls back to
#: ``drop_not_in_ledger``, which is true, just less useful.
EXPIRED_KEY_MEMORY = 64

# The money slot: ``n_ITEM = 0`` with a nonzero rate.  [INFERENCE] in the
# round-100 fact pack, [INFERENCE] here, and it can never reach the ground
# through this pipe -- the element's only content field is an ITEM ID, so a
# money drop has nothing to put in it.  Rolled and recorded, never emitted.
# Which ids have ever reached a real client, BY RUN, because merging the runs
# is how the first version of this module produced a set that never existed:
IDS_ON_THE_WIRE_GT045_V3 = (2200423, 2200003)   # four rounds, 2026-08-25
IDS_ON_THE_WIRE_ROUND_1104 = (2600001,)         # a different run, 2026-08-24
ID_WHOSE_LABEL_WAS_READ = 2200423
# And the sentence that matters more than any of them: NOT ONE of the ids this
# lane can emit is in those tuples.  Everything above is evidence about the
# PIPE, never about an id this module will actually send.

MONEY_ITEM_ID = 0
MONEY_TAG = "INFERENCE_MONEY_SLOT"
MONEY_AMOUNT_FROM_QUANTITY_SPAN = "AMOUNT_FROM_QUANTITY_SPAN"
MONEY_AMOUNT_HAS_NO_COLUMN = "AMOUNT_HAS_NO_COLUMN"
MONEY_AMOUNT_PROVENANCES = (
    MONEY_AMOUNT_FROM_QUANTITY_SPAN, MONEY_AMOUNT_HAS_NO_COLUMN,
)

SOURCE_TABLE_NORMAL = "DROPS_NORMAL"
SOURCE_TABLE_EQUIPMENT = "DROPS_EQUIPMENT"
SOURCE_TABLE_SPECIALLY = "DROPS_SPECIALLY"
SOURCE_TABLES = (
    SOURCE_TABLE_NORMAL, SOURCE_TABLE_EQUIPMENT, SOURCE_TABLE_SPECIALLY,
)

_FLOAT32_MAX = 3.4028235e38

MOB_LOOT_NONCLAIMS = (
    "1. Nothing dispatches this module.  runtime.py is the chief's file and "
    "MOB_LOOT_WIRING is a request, not a call site.  No player has seen one "
    "byte of this lane. "
    "[STALE as of runtime.py CORE-REQUEST-007, PR #71, round 3lzfhw, "
    "2026-08-26] [MEASURED, by call-site reading]: DropLedgerCell/"
    "roll_drops/drop_frames ARE now call sites, unconditional on every "
    "server-computed mob death. This is a dispatch claim only, not an "
    "attended-session claim: GT-045's client-observable red-name-label "
    "measurement predates this wiring and used a separate scenario-gated "
    "probe, so no report yet "
    "exists of a human watching THIS exact wired path fire. 'No player has "
    "seen one byte of this lane' therefore still holds as attended evidence, "
    "even though dispatch itself no longer holds as code.",
    "2. NO OBJECT IS DRAWN, and nothing stays.  What GT-045 measured is a "
    "floating NAME LABEL in red text plus brown dust, ~0.2-0.3 s, with no "
    "model under it and nothing left afterwards.  This lane ANNOUNCES loot; "
    "it does not lay an item on the ground, and n_DROPMODEL_TYPE was measured "
    "NOT to be the switch that changes that.",
    "3. NOT ONE OF THE 43 IDS THIS LANE CAN EMIT HAS EVER BEEN ON A "
    "CLIENT'S WIRE.  43 is the PRODUCTION EMIT UNIVERSE -- "
    "len(field_drop_tables.ITEMS), re-derived from the mined table at "
    "field_drop_tables.py:149-193 -- and is a DIFFERENT COUNT from the "
    "externally-specified 43-ID AUDIT SET Codex's GDL-IMG-017 checkpoint "
    "finding names for the client-side ground-drop asset-decode chain: the "
    "two currently share a number by coincidence, not by naming the same "
    "set of ids.  This line used to read '63' (the correct production "
    "count before the bg0001+Bg0002 union mining changed the roster; see "
    "git history on this file for the prior value), so neither the old "
    "'63' nor this '43' may ever be read as naming the audit set.  Three "
    "ids have (2200423 and 2200003 in the GT-045 v3 "
    "rounds; 2600001 in the earlier round 1104) and none of them is in "
    "field_drop_tables.  The evidence is about the PIPE.  Everything this "
    "lane says about what a player will read is an EXPECTATION from RE-066's "
    "create path, and the label evidence itself covers ONE id from ONE item "
    "table.  2200423 "
    "(EQUIPMENT_BASE) drew its name; 2600001 (ITEM_MISC) drew none in the run "
    "that carried it, and no id from ITEM_CONSUMABLES has ever been on this "
    "wire at all -- which is the table the roster's most frequent drop "
    "(2400046, 30 pct on set 2701001) comes from.  That every rolled id draws "
    "its name is an EXPECTATION from RE-066's create path, not a measurement.",
    "4. There is no pickup.  The only proven PickupTerrainThing producer is "
    "client-outbound (GT-046) and its vital id is hash-DERIVED (0x4543), never "
    "observed; the corpus holds zero frames of it in either direction.  Worse "
    "for this lane: GT-060's precondition is a CLICKABLE drop object, and "
    "GT-045 measured that there is no object to click.",
    "5. Ownership is bookkeeping only.  killer_identity is recorded because "
    "the second half will need it; the element has no owner field, so nothing "
    "on the wire enforces who may take a drop.",
    "6. The quantity never reaches the client.  The element carries an item "
    "id and a position and nothing else, so a stack of five is announced -- "
    "if it is announced at all -- exactly like a stack of one.",
    "7. Money cannot be placed.  A money slot has no item id, and the "
    "element's only content field is one.  Rolled, recorded, never emitted -- "
    "and the reading that item id 0 means money is [INFERENCE], not proven.  "
    "The recorded AMOUNT is not a currency amount either: a DROPS_NORMAL slot "
    "carries a quantity span and a weighted entry carries no quantity column "
    "at all, so every MoneyDrop says which of the two its number came from.",
    "8. DROPS_QUEST is refused by name, table and all: only 311 of the 2478 "
    "DROPS_QUEST sets the mobs reference exist client-side.",
    "9. Item quality is not rolled.  E_DROPS_QUALITY exists and loot_roll "
    "implements it, but the element has nowhere to carry a quality, so "
    "rolling one here would produce a number no player could ever see.  The "
    "consequence is that this lane's draw stream and loot_roll's diverge on "
    "every DROPS_EQUIPMENT pick; the module docstring lists all three "
    "divergences.",
    "10. The ledger lives in the caller's process.  Nothing in this project "
    "persists a ground object across a restart, and this module writes no "
    "database row.  Nothing here expires a row either: the caller must prune.",
    "11. The element key block is ours and unproven.  Nobody has shown what "
    "the client does with a key it has never seen, or whether that key space "
    "is shared with anything else.",
    "12. Whether re-emitting an element redraws the label is UNMEASURED.  "
    "DROP_REFRESH_MS is arithmetic (label life 0.2 s at its low end minus 0.12 "
    "s of wire-to-screen), not a tested value, and at 80 ms it costs 12.5 "
    "frames a second per live row.  A cadence that is affordable is "
    "arithmetically guaranteed to blink.",
    "13. ~~DELTA OR REPLACEMENT IS UNPROVEN~~ IS ANSWERED, round zxnwtd, and "
    "the answer was the bad one: RE-130 (DONE/PASS 2026-08-28T20:18+07:00) "
    "found the consumer REPLACES BY OMISSION -- a nonempty generation erases "
    "every key it does not carry (0x005E0D40 at 0x006AFF84 / 0x006B0368).  "
    "The prediction written here ('the second row of a kill removes the "
    "first and a player sees one name instead of three') is what the client "
    "does.  So this lane no longer sends one element per frame: a kill's "
    "drops go out as ONE generation carrying every key.  What is still "
    "unproven, and is now GT-132's question rather than this nonclaim's, is "
    "whether the client DRAWS the labels it accepts.  (~~'because a "
    "multi-record derived-mask collection is the shape a real client "
    "rejected'~~ IS STRUCK, round kfs01z: ErrorData=28317 is a parse-failure "
    "class-id echo, not a count report, and V43 measured it on the mask-0x02 "
    "actor list, not on this one.)",
    "14. THE SCATTER IS OURS AND IT MULTIPLIES.  30.0 units on X is the only "
    "offset ever put on the wire; row N of a kill uses N times that, so row "
    "12 is 330 units from the corpse and may be somewhere the player never "
    "looks.  Nobody has measured how far from a player a label is still "
    "drawn.",
    "15. ONE LABEL WAS SEEN, TWO ELEMENTS WERE SENT.  The attended round that "
    "read the label sent NEAR and FAR 42 ms apart and only one label is in "
    "the frame; the letter states outright that it cannot say which one was "
    "drawn, and that one label from one round for one item is not a rule of "
    "the client.  This lane sends bursts of up to twelve.",
    "16. THE LABEL IS NOT A COLOUR WE CHOSE, AND IT DIVERGES FROM THE REAL "
    "SERVER.  RE-067 pinned that the text property comes from element +0x1B "
    "and +0x1A under mask bits 0x08 and 0x20, which this lane never sends, so "
    "every label it draws uses the client's default property 0x34.  The one "
    "label observed was RED where the original server drew the same item "
    "WHITE -- an open divergence (RE-067 / GT-069), not a thing this lane "
    "fixed or may claim.",
    "17. EVERY BYTE OF EVIDENCE FOR THIS PIPE IS A SCENE-LOAD ONE-SHOT.  It "
    "was emitted once per session, in direct response to a client "
    "TargetPosVital, with no other RuntimeRes in flight.  This lane emits "
    "server-initiated, mid-session, repeatedly, and in bursts.  Nothing "
    "measured covers that.",
    "18. THE CENSUS INTERACTION IS UNMEASURED.  field_mobs re-applies the "
    "actor collection (derived mask 0x02) 3 s after scene entry and rebuilds "
    "later; whether a RuntimeRes carrying a different derived mask clears, "
    "preserves or corrupts a live 0x5F85B0 entry is unknown, and a kill in "
    "the first seconds of a scene hits exactly that.",
    "19a. THE LEDGER IS A VALUE AND SOMEBODY MUST OWN THE CELL.  "
    "DropLedgerCell is that owner and is what MOB_LOOT_WIRING now hands the "
    "chief: commit_drops on a bare value CANNOT provide atomicity, because a "
    "caller holding the value can always satisfy base_generation from the "
    "same object.  A caller that keeps using the value functions directly is "
    "responsible for its own locking, and this lane cannot check that.",
    "19b. THE REPLAY GUARD IS ONLY AS GOOD AS THE KILL TOKEN.  It refuses a "
    "token it has already seen for an identity, so it needs the caller to "
    "pass a token that RISES with each real death (death_step.register."
    "generation).  Pass a constant and every kill after the first is refused; "
    "pass a random number and a replay can slip through.",
    "19. THE LEDGER IS STATE BUILT FOR A HALF THAT DOES NOT EXIST YET.  Its "
    "keys, its compare-and-swap, take_drop, killer_identity and quantity all "
    "serve a pickup half whose transport is unidentified.  If the answer to "
    "'what makes the model appear' sends monster drops down FightingDrop* "
    "instead, the composer goes and the ledger's shape is the part most "
    "likely to change.  [ASSUMPTION OF LANE B - awaiting COO confirmation]",
    "20. COALESCING FIXES ONE KILL, NOT TWO -- AN OPEN DEFECT, AND HALF OF "
    "IT IS THIS LANE'S.  Round zxnwtd made a kill's drops one generation, "
    "which is what RE-130 asked for WITHIN a kill.  ACROSS kills the same "
    "finding says the next nonempty generation erases the previous kill's "
    "keys by omission, so a second monster killed while the first one's "
    "labels are still up takes them down.  ~~'This lane cannot fix that "
    "from here'~~ IS STRUCK IN THE ROUND THAT WROTE IT (pf-adversary D4): "
    "the prune the defect rests on is commanded by WIRING step 4, which is "
    "THIS LANE'S OWN TEXT, and the shape that fixes it (the whole live "
    "ledger as one generation, cell.frames/refresh_frames) is composed in "
    "THIS FILE.  What this lane genuinely cannot do is edit the call site "
    "(runtime.py:4298-4312, chief's file).  So the option is now written "
    "into WIRING step 4b where a caller reads it, not only into a letter, "
    "and it needs an expiry or a pickup before anyone takes it.  Nobody may "
    "read 'coalesced' as 'solved'.",
    "21. THE FRAME RE-DERIVATION IS A TRANSCRIPTION, NOT A SECOND OPINION.  "
    "~~'_snappy_raw_literal_via_struct is written from the format "
    "description'~~ IS STRUCK IN THE ROUND THAT WROTE IT (pf-adversary D7): "
    "expression for expression it is the legacy snappy_raw_literal, "
    "idiosyncratic (59 + width) << 2 rendering and all.  It catches a moved "
    "magic, a changed length field or a swapped compressor -- because those "
    "stop reproducing this text's output -- and it CANNOT catch an error "
    "the two share, because they are one text.  Only the ONE-element frame "
    "is pinned to literal bytes a real client took (GT-045); every wider "
    "frame is checked for self-consistency, which is weaker, and is said so "
    "here.",
    "22. NO CLIENT HAS EVER RECEIVED A WIDE GENERATION FROM THIS LANE, AND "
    "IT SHIPS UNFLAGGED.  Round zxnwtd's 2-drop kill puts an 82-byte frame "
    "on a production path (44/54 remains the ONE-drop shape and is the only "
    "one GT-045 measured).  The evidence for the change is ONE static "
    "letter, RE-130; the client-observable layer is GT-132 and it has not "
    "run.  The old shape is not a safe alternative -- RE-130 proves it "
    "loses k-1 drops -- so both shapes carry a cost and this lane took the "
    "one whose cost is measured.  [ASSUMPTION OF LANE B - awaiting COO "
    "confirmation]  Rollback if the call is wrong: drop_frames returning "
    "one pair per drop again, one function, no call-site change.",
    "23. MASK 0x04 (n_DROPMODEL_TYPE) IS NOW COMPOSED, AND IT IS UNMEASURED "
    "WHETHER THE CLIENT DRAWS ANYTHING FROM IT.  2026-09-01, "
    "drop_element_with_model_type / drop_collection_pc_with_model_type / "
    "drop_pc_with_model_type / drop_frames_with_model_type add tag 0x0F "
    "(u16, element offset +0x18, mask bit 0x04) to the proven mask-0x12 "
    "element, sourcing the value from field_drop_tables.ITEMS[item_id][3] -- "
    "already-mined data, not a guess.  This answers ka1-B's letter "
    "(pf_bridge notes_to_chief/20260901_2015_KA1B-TO-LANE-B-drop-model-"
    "selector-field-is-not-on-our-wire.md, [HYPOTHESIS, unproven]), which "
    "named THREE mask-bit candidates from the same static element table "
    "GT-042 pinned.  TWO OF THOSE THREE ARE NOT TOUCHED HERE: NONCLAIM 16 "
    "already pinned mask 0x08 (tag 0x05, +0x1B) and mask 0x20 (tag 0x08, "
    "+0x1A) as RE-067's TEXT-LABEL-COLOR property -- P-2 territory, not this "
    "lane's -- so only mask 0x04 was built.  NOTHING ABOUT THIS IS "
    "MEASURED: no client has ever been shown these bytes, and GT-045's own "
    "finding (n_DROPMODEL_TYPE = 1 is NOT SUFFICIENT; both v3 ids carried "
    "it and only ID_MODEL differed) is the reason this lane does not read "
    "'the field is now sent' as 'a model will now appear'.  It answers only "
    "whether a byte the decompiled shape reserves is present, not what the "
    "client does with it.  [ASSUMPTION OF LANE B - awaiting COO "
    "confirmation]  It is production code with no CLI flag, gated by "
    "DROP_MODEL_TYPE_FIELD_ENABLED (True), but ~~is NOT wired into "
    "drop_frames -- the function runtime.py actually calls -- because that "
    "function's ONE-drop output is pinned byte-for-byte in test files this "
    "round did not touch (test_ground_drop_multi_drop_emission_shape.py, "
    "test_mob_drop_presence*.py).  The swap that would make it the call "
    "site's default is this round's CORE-REQUEST.  Rollback if the "
    "assumption is wrong: leave DROP_MODEL_TYPE_FIELD_ENABLED False, or "
    "simply never take the CORE-REQUEST swap -- drop_frames itself never "
    "reads this flag~~ IS STRUCK, ROUND KA1B-DROPMODEL FOLLOW-UP, "
    "2026-09-01, PF-ADVERSARY: it named the wrong call site.  "
    "``runtime.py`` never called ``drop_frames`` directly; it has called "
    "``mob_drop_presence.sustain_a_kill`` since CORE-REQUEST 2246 "
    "(COO-DECISION 2026-08-29T23:42, ``runtime.py:4921-4922``, proven by "
    "tests/test_mob_drop_presence_wiring.py), which calls "
    "``mob_loot.refresh_frames``, which lives in THIS FILE, not in "
    "runtime.py/app.py/pf_login_game_server_v141.py -- so no CORE-REQUEST "
    "was needed to reach it.  This round changed refresh_frames's body to "
    "call drop_frames_with_model_type instead of drop_frames, so the wide "
    "mask IS now what the production dispatch path sends by default, on "
    "every kill.  drop_frames itself is untouched and still composes only "
    "the proven mask-0x12 shape byte-for-byte (its own GT-045 pins did not "
    "move); it is refresh_frames, not drop_frames, that changed callee.  "
    "[ASSUMPTION OF LANE B - awaiting COO confirmation]  Rollback if the "
    "assumption is wrong: set DROP_MODEL_TYPE_FIELD_ENABLED = False -- "
    "drop_frames_with_model_type reads that flag and, when it is False, "
    "returns drop_frames's own output verbatim, no other code change, so "
    "refresh_frames goes back to sending exactly the narrow bytes GT-045 "
    "measured.",
)

# ---------------------------------------------------------------------------
# Refusals.  A refusal has a NAME, and every name here is reachable: a name
# that cannot happen is a lie to whoever counts them (the rule mob_combat
# wrote for itself when its floor moved).
# ---------------------------------------------------------------------------
REFUSE_TYPE_NOT_TYPED_RECORD = "type_not_typed_record"
REFUSE_VALUE_NOT_INT = "value_not_int"
REFUSE_VALUE_OUT_OF_RANGE = "value_out_of_range"
REFUSE_IDENTITY_NOT_POSITIVE = "identity_not_positive"
REFUSE_POSITION_NOT_FINITE = "position_not_finite"
REFUSE_RNG_HAS_NO_RANDOM = "rng_has_no_random"
REFUSE_DRAW_OUT_OF_UNIT_INTERVAL = "draw_out_of_unit_interval"
REFUSE_QUANTITY_RANGE_INVERTED = "quantity_range_inverted"
REFUSE_UNKNOWN_DROP_SET = "unknown_drop_set"
REFUSE_UNKNOWN_ITEM_ID = "unknown_item_id"
REFUSE_ITEM_HAS_NO_NAME = "item_has_no_name"
REFUSE_RATE_OUT_OF_RANGE = "rate_out_of_range"
REFUSE_LEDGER_GENERATION_MOVED = "ledger_generation_moved"
REFUSE_MOB_ALREADY_LOOTED = "mob_already_looted"
REFUSE_ROLL_NAMES_ANOTHER_MONSTER = "roll_names_another_monster"
REFUSE_KEY_OUTSIDE_THE_LANE_BLOCK = "key_outside_the_lane_block"
REFUSE_LEDGER_NOT_SORTED = "ledger_not_sorted"
REFUSE_DUPLICATE_LEDGER_KEY = "duplicate_ledger_key"
REFUSE_LEDGER_STALE = "ledger_stale"
REFUSE_DROP_NOT_IN_LEDGER = "drop_not_in_ledger"
REFUSE_TOO_MANY_DROPS_FOR_ONE_KILL = "too_many_drops_for_one_kill"
REFUSE_MONEY_HAS_NO_ELEMENT = "money_has_no_element"
REFUSE_COMPOSED_BYTES_OFF_PIN = "composed_bytes_off_pin"
REFUSE_ELEMENT_ENCODER_DISAGREES = "element_encoder_disagrees"
REFUSE_POSITION_OFF_THE_F32_GRID = "position_off_the_f32_grid"
REFUSE_GENERATION_IS_EMPTY = "generation_is_empty"
REFUSE_GENERATION_TOO_WIDE_TO_FRAME = "generation_too_wide_to_frame"
REFUSE_DUPLICATE_KEY_IN_GENERATION = "duplicate_key_in_generation"
REFUSE_FRAME_ENCODER_DISAGREES = "frame_encoder_disagrees"
#: ROUND uq2lxw2.  A prune cut point above the newest kill's first key would
#: remove the rows a player can still be reaching for -- the one mistake the
#: prune primitive is shaped to make loud rather than silent.
REFUSE_PRUNE_WOULD_TAKE_THE_NEWEST_KILL = "prune_would_take_the_newest_kill"
#: ROUND 0n9inw.  The row was on the ground and its deadline passed before the
#: player's click arrived.  It is a SEPARATE NAME from drop_not_in_ledger and
#: from a row another player took, and that separation is the point: round
#: uq2lxw2 wrote down that expiry and someone-else's-pickup gave the caller the
#: same word, so a call site could not tell a player "you were too slow" apart
#: from "somebody beat you to it".  A refusal that cannot distinguish those two
#: cannot be turned into an honest message on screen.
REFUSE_DROP_EXPIRED = "drop_expired"
#: ROUND 0n9inw.  A cell's clock read lower than its own previous reading.  With
#: the default clock (time.monotonic) this cannot happen; it is reachable, and
#: reached in tests, through an injected clock -- which is exactly the case that
#: must be loud, because a backwards clock silently stops every expiry and the
#: ledger grows without bound again with nothing raised anywhere.
REFUSE_CLOCK_WENT_BACKWARDS = "clock_went_backwards"
#: ROUND 0n9inw.  A lifetime that is zero, negative, non-finite or absurdly
#: large is refused when the cell is built rather than the day a drop either
#: vanishes before the frame carrying it or never leaves the ground.
REFUSE_LIFETIME_OUT_OF_RANGE = "lifetime_out_of_range"
#: ROUND 0n9inw.  The clock handed to a cell is not callable, or does not return
#: a finite real number.
REFUSE_CLOCK_IS_NOT_A_CLOCK = "clock_is_not_a_clock"
#: ROUND ewm6ff.  ~~Four refusals of a ``preserve_ground_in_runtime_res`` that
#: took an already-composed pc: pc_is_not_bytes, pc_is_not_a_runtime_res,
#: pc_tail_is_not_the_derived_mask, derived_mask_is_not_empty.~~  STRUCK the
#: same round, before any of them shipped to main: pf-adversary measured that
#: the function those names belonged to could not tell the derived-mask record
#: from a u32 field ending in 0B 00 (finding D1), and that the fourth name --
#: written to protect ``make_runtime_remote_actors`` -- never fired for that
#: composer at all, because a real actor pc does not end at its mask (D3).
#: Names for a distinction the code could not actually make.  The function was
#: replaced by one that composes the body itself, and its refusals are declared
#: with it: the one below, plus the two this module already had for a moved
#: serializer and a disagreeing framing layer.
#:
#: ROUND ewm6ff.  v141's ``make_runtime_vitals`` no longer composes the body
#: this lane re-derives for the same vitals.  Raised INSTEAD of emitting: the
#: whole reason that function composes rather than patches is that it can prove
#: where the derived mask is, and a composer that moved has taken that proof
#: away.  See :func:`preserve_ground_in_runtime_res_vitals`.
REFUSE_VITALS_COMPOSER_MOVED = "vitals_composer_moved"
#: ROUND jysbar.  The same refusal for the OTHER carrier: v141's
#: ``make_runtime_remote_actors`` no longer composes the body this lane
#: re-derives for the same entries.  Raised INSTEAD of emitting, and it is the
#: more dangerous of the two to get wrong -- this carrier holds whole-scene
#: censuses, so bytes whose mask record this lane can no longer locate would
#: be bytes that move every actor on the map.
#: See :func:`preserve_ground_in_runtime_res_remote_actors`.
REFUSE_ACTORS_COMPOSER_MOVED = "actors_composer_moved"
#: ROUND 4e9r7g, COO-DECISION 2026-09-02T02:52+07:00 (way 1).  A scene name is
#: not a usable scene name: not a str, empty, non-ASCII, or carrying
#: whitespace.  A drop now OWNS the scene it fell in, and a row whose scene
#: cannot be compared is a row no publication can decide about -- so it is
#: refused where it is built, not where it would have been published.
REFUSE_SCENE_NOT_A_SCENE = "scene_not_a_scene"
#: ROUND 4e9r7g.  One commit is one kill, and one kill happens in ONE scene.
#: Two scenes in one commit means the caller assembled rows from two kills, or
#: built a row with the wrong scene; either way the ledger would carry a kill
#: split across two publications with nothing raised.
REFUSE_COMMIT_SPANS_TWO_SCENES = "commit_spans_two_scenes"
#: ROUND 4e9r7g.  A publication was asked for before the cell knew which scene
#: it is publishing.  FAIL-CLOSED BY NAME: the alternative -- publishing every
#: row the ledger holds -- is exactly the cross-scene leak COO-DECISION
#: 2026-09-02T02:52+07:00 way 1 exists to close, so "I do not know the scene"
#: must not degrade into "send them all".
REFUSE_NO_SCENE_TO_PUBLISH = "no_scene_to_publish"
#: ROUND 4e9r7g, after pf-adversary.  The cell was DECLARED into one scene at
#: a boundary and a kill arrived from a monster belonging to another.  Refused
#: rather than resolved: FieldMob.scene has a default, so the quiet resolution
#: would let one hand-built record move a whole session's ground -- and hide
#: the player's own drops from them while telling them the row they stand on
#: is somewhere else.
REFUSE_KILL_IN_ANOTHER_SCENE = "kill_in_another_scene"

MOB_LOOT_REFUSAL_REASONS = (
    REFUSE_TYPE_NOT_TYPED_RECORD,
    REFUSE_VALUE_NOT_INT,
    REFUSE_VALUE_OUT_OF_RANGE,
    REFUSE_IDENTITY_NOT_POSITIVE,
    REFUSE_POSITION_NOT_FINITE,
    REFUSE_RNG_HAS_NO_RANDOM,
    REFUSE_DRAW_OUT_OF_UNIT_INTERVAL,
    REFUSE_QUANTITY_RANGE_INVERTED,
    REFUSE_UNKNOWN_DROP_SET,
    REFUSE_UNKNOWN_ITEM_ID,
    REFUSE_ITEM_HAS_NO_NAME,
    REFUSE_RATE_OUT_OF_RANGE,
    REFUSE_LEDGER_GENERATION_MOVED,
    REFUSE_MOB_ALREADY_LOOTED,
    REFUSE_ROLL_NAMES_ANOTHER_MONSTER,
    REFUSE_KEY_OUTSIDE_THE_LANE_BLOCK,
    REFUSE_LEDGER_NOT_SORTED,
    REFUSE_DUPLICATE_LEDGER_KEY,
    REFUSE_LEDGER_STALE,
    REFUSE_DROP_NOT_IN_LEDGER,
    REFUSE_TOO_MANY_DROPS_FOR_ONE_KILL,
    REFUSE_MONEY_HAS_NO_ELEMENT,
    REFUSE_COMPOSED_BYTES_OFF_PIN,
    REFUSE_ELEMENT_ENCODER_DISAGREES,
    REFUSE_POSITION_OFF_THE_F32_GRID,
    REFUSE_GENERATION_IS_EMPTY,
    REFUSE_GENERATION_TOO_WIDE_TO_FRAME,
    REFUSE_DUPLICATE_KEY_IN_GENERATION,
    REFUSE_FRAME_ENCODER_DISAGREES,
    REFUSE_PRUNE_WOULD_TAKE_THE_NEWEST_KILL,
    REFUSE_DROP_EXPIRED,
    REFUSE_CLOCK_WENT_BACKWARDS,
    REFUSE_LIFETIME_OUT_OF_RANGE,
    REFUSE_CLOCK_IS_NOT_A_CLOCK,
    REFUSE_VITALS_COMPOSER_MOVED,
    REFUSE_ACTORS_COMPOSER_MOVED,
    REFUSE_SCENE_NOT_A_SCENE,
    REFUSE_COMMIT_SPANS_TWO_SCENES,
    REFUSE_NO_SCENE_TO_PUBLISH,
    REFUSE_KILL_IN_ANOTHER_SCENE,
)


class MobLootContractError(ValueError):
    """Every refusal in this module, carrying its reason NAME as args[0]."""


def _require_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int:   # `type(x) is int` is already False for a bool
        raise MobLootContractError(
            REFUSE_VALUE_NOT_INT, "%s must be an int" % label)
    if not minimum <= value <= maximum:
        raise MobLootContractError(
            REFUSE_VALUE_OUT_OF_RANGE,
            "%s must be in [%d, %d], got %d" % (label, minimum, maximum, value))
    return value


#: The widest actor identity either lane accepts, named in round uq2lxw2 so
#: the sibling lane can BE this value rather than repeat it.
#:
#: ~~2 ** 62~~, WHICH IS WHAT THIS LANE HAD APPLIED SINCE IT WAS WRITTEN, AND
#: WHICH DOES NOT COVER WHAT THE SERVER COMPOSES.  ``runtime.py`` builds a
#: performer identity as ``((hi & 0xFFFFFFFF) << 32) | (lo & 0xFFFFFFFF)`` --
#: a full u64 -- so three quarters of the space it can produce was refused by
#: BOTH lanes, not just by the pickup one (pf-adversary, round uq2lxw2,
#: measured: hi=0x80000000 is refused here as well).  The first draft of this
#: round adopted 2 ** 62 for both lanes and its docstring claimed the width
#: "follows the server's composition"; that was false by two bits, and an
#: identity with either top bit set would raise out of ``loot_a_kill`` inside
#: ``runtime.py``'s dispatch, which handles three named ledger refusals and
#: re-raises everything else.
#:
#: An actor identity is a u64 that is compared and printed, never packed by
#: either lane, so the bound is the composition's own.
MAX_IDENTITY = 0xFFFFFFFFFFFFFFFF
#: ~~MAX_IDENTITY_MAGNITUDE~~, the symmetric name the first draft used, is
#: kept pointing at the new value rather than deleted: the word "magnitude"
#: said the floor and the ceiling were one number, and they never were -- a
#: negative identity is refused by name below, not by range.
MAX_IDENTITY_MAGNITUDE = MAX_IDENTITY


def _require_identity(value: Any, label: str) -> int:
    identity = _require_int(value, label, 0, MAX_IDENTITY)
    if identity <= 0:
        raise MobLootContractError(
            REFUSE_IDENTITY_NOT_POSITIVE, "%s must be positive" % label)
    return identity


def _require_lifetime(value: Any) -> float:
    """ROUND 0n9inw.  A drop lifetime, in seconds, or a refusal by name."""
    if type(value) not in (int, float):   # a bool is neither, by exact type
        raise MobLootContractError(
            REFUSE_LIFETIME_OUT_OF_RANGE,
            "a lifetime is a number of seconds, not %r" % (value,))
    lifetime = float(value)
    if not math.isfinite(lifetime):
        raise MobLootContractError(
            REFUSE_LIFETIME_OUT_OF_RANGE, "a lifetime must be finite")
    if lifetime <= 0.0:
        # Zero is refused, not treated as "expire immediately": a cell whose
        # rows are gone before the frame announcing them is sent is a cell that
        # silently eats every drop, and it would look like a loot bug for as
        # long as it took somebody to find this number.
        raise MobLootContractError(
            REFUSE_LIFETIME_OUT_OF_RANGE,
            "a lifetime must be above zero; %r would take every drop off the "
            "ground before the frame carrying it is sent" % (lifetime,))
    if lifetime > MAX_DROP_LIFETIME_SECONDS:
        raise MobLootContractError(
            REFUSE_LIFETIME_OUT_OF_RANGE,
            "a lifetime of %r s is above this lane's tripwire of %r s; a cell "
            "with a lifetime that long has no ceiling, which is the defect "
            "the expiry exists to close"
            % (lifetime, MAX_DROP_LIFETIME_SECONDS))
    return lifetime


def _require_clock(clock: Any) -> Any:
    """ROUND 0n9inw.  A zero-argument callable returning a finite real number."""
    if not callable(clock):
        raise MobLootContractError(
            REFUSE_CLOCK_IS_NOT_A_CLOCK,
            "a clock is called with no arguments; %r is not callable"
            % (clock,))
    return clock


def _read_clock(clock: Any, previous: Any) -> float:
    """Take one reading, refusing a clock that is not one or has gone back."""
    try:
        now = clock()
    except TypeError as exc:
        raise MobLootContractError(
            REFUSE_CLOCK_IS_NOT_A_CLOCK,
            "a clock is called with no arguments: %s" % (exc,)) from exc
    if type(now) not in (int, float):
        raise MobLootContractError(
            REFUSE_CLOCK_IS_NOT_A_CLOCK,
            "a clock returns a number of seconds, not %r" % (now,))
    now = float(now)
    if not math.isfinite(now):
        raise MobLootContractError(
            REFUSE_CLOCK_IS_NOT_A_CLOCK, "a clock reading must be finite")
    if previous is not None and now < previous:
        raise MobLootContractError(
            REFUSE_CLOCK_WENT_BACKWARDS,
            "this cell's clock read %r after reading %r; every deadline it "
            "issued is now in the future and nothing would ever expire again"
            % (now, previous))
    return now


def _require_float32(value: Any, label: str) -> float:
    if type(value) not in (int, float):   # a bool is neither, by exact type
        raise MobLootContractError(
            REFUSE_POSITION_NOT_FINITE, "%s must be a finite number" % label)
    result = float(value)
    if not math.isfinite(result) or abs(result) > _FLOAT32_MAX:
        raise MobLootContractError(
            REFUSE_POSITION_NOT_FINITE, "%s must be finite float32" % label)
    return result


def as_wire_float(value: float) -> float:
    """Quantize to the exact f32 the wire will carry."""
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


#: The longest scene name this lane will carry.  ``bg0001``/``Bg0002``/
#: ``Bg0015`` are six; the ceiling is generous on purpose and exists only so a
#: scene field cannot become an unbounded string somebody stores a message in.
SCENE_NAME_MAX = 32


def _require_scene(value: Any, label: str) -> str:
    """A usable scene name, returned EXACTLY as given.

    ROUND 4e9r7g, COO-DECISION 2026-09-02T02:52+07:00 way 1.

    CASE IS NOT NORMALISED HERE, and that is deliberate: the scene strings
    this project already uses disagree about case (``field_mob_tables.SCENE``
    is ``bg0001`` while ``field_mob_tables_bg0002.SCENE`` is ``Bg0002``), and
    a store that silently lower-cases would make a row's scene stop matching
    the string its own roster module publishes.  So the row keeps what it was
    given, and every COMPARISON goes through :func:`scene_key`.
    """
    if type(value) is not str:
        raise MobLootContractError(
            REFUSE_SCENE_NOT_A_SCENE,
            "%s must be a str scene name, got %s" % (label, type(value).__name__))
    if not value:
        raise MobLootContractError(
            REFUSE_SCENE_NOT_A_SCENE, "%s must not be empty" % label)
    if len(value) > SCENE_NAME_MAX:
        raise MobLootContractError(
            REFUSE_SCENE_NOT_A_SCENE,
            "%s is %d characters; the ceiling is %d"
            % (label, len(value), SCENE_NAME_MAX))
    if not value.isascii():
        raise MobLootContractError(
            REFUSE_SCENE_NOT_A_SCENE,
            "%s must be ASCII; the console this lane prints to is cp874" % label)
    if any(character.isspace() for character in value):
        raise MobLootContractError(
            REFUSE_SCENE_NOT_A_SCENE,
            "%s must not carry whitespace, got %r" % (label, value))
    if not value.isprintable():
        raise MobLootContractError(
            REFUSE_SCENE_NOT_A_SCENE,
            "%s must be printable, got %r" % (label, value))
    return value


def scene_key(scene: Any) -> str:
    """The comparison form of a scene name.  Case-folded, nothing else.

    THE ONLY WAY TWO SCENE NAMES ARE COMPARED IN THIS LANE.  ``bg0002`` and
    ``Bg0002`` are one scene: the roster modules, the mined tables and the
    letters all spell them differently, and a publication that treated them as
    two scenes would hide a player's own drops from them -- the exact failure
    way 1 is meant to end, arrived at from the other side.
    """
    return _require_scene(scene, "scene").casefold()


def _require_draw(draw: Any) -> float:
    if type(draw) not in (int, float):   # a bool is neither, by exact type
        raise MobLootContractError(
            REFUSE_DRAW_OUT_OF_UNIT_INTERVAL, "a draw must be a number")
    value = float(draw)
    if not math.isfinite(value) or not 0.0 <= value < 1.0:
        raise MobLootContractError(
            REFUSE_DRAW_OUT_OF_UNIT_INTERVAL,
            "a draw must be in [0.0, 1.0), got %r" % (draw,))
    return value


class _FixedStream:
    """Marker a test subclasses to script the draw stream deliberately.

    Nothing in ``src/`` inherits it; it exists so the type check above can be
    EXACT for production callers without making the lane untestable.
    """


def _require_rng(rng: Any) -> Any:
    """An INSTANCE of random.Random, not merely something with .random().

    The sibling roller enforces the same sentence the same way, and the reason
    is the failure this check exists to stop: a caller who passes the
    module-global ``random`` module satisfies a duck-type check exactly, and
    from then on this lane's draw stream is shared global state correlated with
    every other consumer in the process.  Every test in this file injects a
    Random or a scripted stub, so no test would ever have noticed.
    """
    if type(rng) is not _random.Random and not isinstance(rng, _FixedStream):
        # EXACT type, not isinstance: random.SystemRandom IS a Random and
        # cannot be seeded, so it satisfies isinstance while making the
        # determinism paragraph false.  Subclasses that a test injects to
        # script the draws register themselves through _FixedStream.
        raise MobLootContractError(
            REFUSE_RNG_HAS_NO_RANDOM,
            "roll_drops needs a random.Random this caller owns: not a "
            "SystemRandom (it cannot be seeded) and not an object that merely "
            "has a .random()")
    if rng is getattr(_random, "_inst", None):
        # random._inst IS the object behind random.random().  isinstance
        # accepts it, which is how the previous version of this check let the
        # module-global stream in through the front door.
        raise MobLootContractError(
            REFUSE_RNG_HAS_NO_RANDOM,
            "that is the module-global random stream itself; this lane's "
            "draws must belong to the caller, not to every consumer in the "
            "process")
    return rng


def _require_known_item(item_id: int, label: str) -> tuple:
    """The item row, refusing an unmined id AND a nameless one.

    The name is the ONLY thing this lane has ever been measured to put on a
    player's screen (GT-045: the client resolves it from the payload dword),
    so an item whose TIP row is missing or blank would be announced as a label
    with nothing in it.  Refused by name rather than drawn as an empty string.
    """
    row = field_drop_tables.ITEMS.get(item_id)
    if row is None:
        raise MobLootContractError(
            REFUSE_UNKNOWN_ITEM_ID,
            "%s: item %d is not in the mined item table" % (label, item_id))
    if not str(row[2]).strip():
        raise MobLootContractError(
            REFUSE_ITEM_HAS_NO_NAME,
            "%s: item %d has no display name, and the name is the only thing "
            "this lane has ever been measured to draw" % (label, item_id))
    return row


def _model_type_for_item(item_id: int) -> int:
    """``n_DROPMODEL_TYPE`` for ``item_id``, PULLED, never guessed.

    ``field_drop_tables.ITEMS[item_id]`` is ``(table_code, low_id,
    display_name, drop_model_type)`` -- the 4th element already IS the 0..12
    token ka1-B's letter names item for item (weapons 1, armor 2, jewelry/
    fittings 3, crystal ids 10/11, and so on).  This function exists so
    every mask-0x16 composer reads that column exactly once and refuses the
    same way :func:`_require_known_item` already refuses an unmined or
    nameless item, rather than re-deriving the value or defaulting it.
    """
    row = _require_known_item(item_id, "model type lookup")
    return _require_int(
        row[3], "drop_model_type for item %d" % item_id, 0, 12)


def _require_mob(mob: Any) -> FieldMob:
    if type(mob) is not FieldMob:
        raise MobLootContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "this lane rolls for a typed FieldMob roster row, not a dict")
    return mob


# ---------------------------------------------------------------------------
# The three primitives.  Identical in semantics to loot_roll's, pinned against
# them value by value in the tests, and re-derived here so that a production
# module does not import a module whose contract says nothing in src/ does.
# ---------------------------------------------------------------------------
def rate_succeeds(rate_percent: float, draw: float) -> bool:
    """``draw < rate / 100``: 0 pct never fires, 100 pct always fires.

    The comparison is strict, so an entry EXACTLY AT the threshold fails: for
    a 0.5 pct rate the threshold is 0.005 and a draw of 0.005 does not drop.
    """
    return _require_draw(draw) < float(rate_percent) / 100.0


def uniform_quantity(low: int, high: int, draw: float) -> int:
    """A flat integer span: ``low + int(draw * (high - low + 1))``, clamped."""
    span = high - low + 1
    if span <= 0:
        raise MobLootContractError(
            REFUSE_QUANTITY_RANGE_INVERTED,
            "quantity range is inverted: %d..%d" % (low, high))
    value = low + int(_require_draw(draw) * span)
    if value < low:
        return low
    if value > high:
        return high
    return value


def weighted_pick(weights: Any, draw: float) -> int | None:
    """Cumulative-threshold walk in TABLE ORDER; ``None`` if no positive total.

    The chosen index is the FIRST whose running sum strictly EXCEEDS
    ``draw * total``, so a zero-weight entry owns an empty interval and can
    never be picked, and the total is the ACTUAL sum rather than an assumed
    100.
    """
    target_draw = _require_draw(draw)
    total = 0
    for weight in weights:
        total += int(weight)
    if total <= 0:
        return None
    target = target_draw * total
    cumulative = 0
    for index, weight in enumerate(weights):
        cumulative += int(weight)
        if cumulative > target:
            return index
    return len(weights) - 1


# ---------------------------------------------------------------------------
# What a roll produces.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DropItem:
    """One item a kill produced: what, how many, and which table said so."""

    item_id: int
    quantity: int
    source_table: str
    source_set_id: int
    source_index: int

    def __post_init__(self) -> None:
        _require_int(self.item_id, "item id", 1, 0xFFFFFFFF)
        _require_int(self.quantity, "quantity", 1, 0xFFFF)
        if self.source_table not in SOURCE_TABLES:
            raise MobLootContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "source table must be one of %s" % (SOURCE_TABLES,))
        _require_int(self.source_set_id, "source set id", 1, 0xFFFFFFFF)
        _require_int(self.source_index, "source index", 1, 0xFF)
        _require_known_item(self.item_id, "rolled item")

    @property
    def display_name(self) -> str:
        return field_drop_tables.ITEMS[self.item_id][2]

    @property
    def drop_model_type(self) -> int:
        """Carried from the table.  NOT a claim, and NOT the model switch.

        GT-045 measured a nonzero value on 2200423 and NO MODEL on screen, so
        this column is data about the tables, not a prediction about drawing.
        """
        return field_drop_tables.ITEMS[self.item_id][3]


@dataclass(frozen=True)
class MoneyDrop:
    """A money slot that won its rate roll.  It can never reach the ground.

    ``amount`` is NOT a currency amount and this lane will not pretend it is.
    A DROPS_NORMAL money slot has the slot's own quantity span and that span
    is what is recorded (``AMOUNT_FROM_QUANTITY_SPAN``); a weighted entry in
    DROPS_EQUIPMENT / DROPS_SPECIALLY has NO quantity column at all, so the
    recorded amount is 1 by convention and says so in its provenance
    (``AMOUNT_HAS_NO_COLUMN``).  Whoever builds the pickup half must read the
    provenance before it converts either number into gold.
    """

    amount: int
    source_table: str
    source_set_id: int
    source_index: int
    amount_provenance: str = "AMOUNT_FROM_QUANTITY_SPAN"
    tag: str = MONEY_TAG

    def __post_init__(self) -> None:
        _require_int(self.amount, "amount", 1, 0xFFFFFFFF)
        if self.amount_provenance not in MONEY_AMOUNT_PROVENANCES:
            raise MobLootContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "a money amount must say where it came from: %s"
                % (MONEY_AMOUNT_PROVENANCES,))
        if self.source_table not in SOURCE_TABLES:
            raise MobLootContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "source table must be one of %s" % (SOURCE_TABLES,))
        _require_int(self.source_set_id, "source set id", 1, 0xFFFFFFFF)
        _require_int(self.source_index, "source index", 1, 0xFF)
        if self.tag != MONEY_TAG:
            raise MobLootContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "a money drop keeps its inference tag")


@dataclass(frozen=True)
class DropRoll:
    """Everything one kill produced, and everything it refused."""

    mob_template_id: int
    mob_identity: int
    items: tuple
    money: tuple
    draws: int
    refusals: tuple

    def __post_init__(self) -> None:
        _require_int(self.mob_template_id, "template id", 1, 0xFFFFFFFF)
        _require_identity(self.mob_identity, "mob identity")
        for label, container in (
            ("items", self.items), ("money", self.money),
            ("refusals", self.refusals),
        ):
            if type(container) is not tuple:
                # Lists compare unequal to tuples, so a list here would make
                # the "same seed, same roll" equality test pass for the wrong
                # reason and fail for a caller that built one by hand.
                raise MobLootContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "%s must be a tuple, not %s"
                    % (label, type(container).__name__))
        for row in self.refusals:
            if type(row) is not tuple or len(row) != 3:
                raise MobLootContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "a refusal row is (reason, set id, index)")
        for item in self.items:
            if type(item) is not DropItem:
                raise MobLootContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "every rolled item must be a typed DropItem")
        for money in self.money:
            if type(money) is not MoneyDrop:
                raise MobLootContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "every money row must be a typed MoneyDrop")
        _require_int(self.draws, "draw count", 0, 0xFFFF)

    @property
    def placeable_count(self) -> int:
        """How many of these can actually be announced on the ground.

        "Stand" would be the wrong word and this lane may not use it: nothing
        stands anywhere -- see WHAT THE PLAYER SEES.
        """
        return len(self.items)


def _set_rows(mob: FieldMob) -> tuple:
    """The three drop sets of one roster row, refusing an unmined one."""
    rows = []
    for set_id, table, source in (
        (mob.drops_normal, field_drop_tables.DROPS_NORMAL,
         SOURCE_TABLE_NORMAL),
        (mob.drops_equipment, field_drop_tables.DROPS_EQUIPMENT,
         SOURCE_TABLE_EQUIPMENT),
        (mob.drops_specially, field_drop_tables.DROPS_SPECIALLY,
         SOURCE_TABLE_SPECIALLY),
    ):
        if set_id == 0:
            continue
        if set_id not in table:
            raise MobLootContractError(
                REFUSE_UNKNOWN_DROP_SET,
                "%s set %d is not in the mined tables; regenerate "
                "field_drop_tables rather than patch it"
                % (source, set_id))
        rows.append((source, set_id, table[set_id]))
    return tuple(rows)


def _roll_normal(set_id, row, rng, items, money, refusals) -> int:
    """Per-slot independent percentage rates, in table order."""
    draws = 0
    for index, item_id, rate, low, high in row:
        draws += 1
        drawn = rng.random()
        if not 0.0 <= rate <= 100.0:
            # AFTER the draw on purpose: the stream must not depend on the
            # table's contents.  The sibling roller refuses before drawing,
            # which is why the two streams diverge on a bad table (see the
            # module docstring).
            refusals.append((REFUSE_RATE_OUT_OF_RANGE, set_id, index))
            continue
        if not rate_succeeds(rate, drawn):
            continue
        # The quantity draw is consumed whether or not the id resolves, so the
        # stream does not depend on the tables' contents.
        draws += 1
        quantity_draw = rng.random()
        if low > high:
            refusals.append((REFUSE_QUANTITY_RANGE_INVERTED, set_id, index))
            continue
        quantity = uniform_quantity(low, high, quantity_draw)
        if quantity <= 0:
            refusals.append((REFUSE_VALUE_OUT_OF_RANGE, set_id, index))
            continue
        if item_id == MONEY_ITEM_ID:
            money.append(MoneyDrop(
                quantity, SOURCE_TABLE_NORMAL, set_id, index,
                MONEY_AMOUNT_FROM_QUANTITY_SPAN))
            continue
        try:
            _require_known_item(item_id, "roll")
        except MobLootContractError as refused:
            refusals.append((refused.args[0], set_id, index))
            continue
        items.append(DropItem(
            item_id, quantity, SOURCE_TABLE_NORMAL, set_id, index))
    return draws


def _roll_weighted(source, set_id, row, rng, items, money, refusals) -> int:
    """One roll at the set rate, then that many weighted picks."""
    rate, number_min, number_max, entries = row
    draws = 1
    drawn = rng.random()
    if not 0.0 <= rate <= 100.0:
        refusals.append((REFUSE_RATE_OUT_OF_RANGE, set_id, 0))
        return draws
    if not rate_succeeds(rate, drawn):
        return draws
    draws += 1
    count_draw = rng.random()
    if number_min > number_max:
        refusals.append((REFUSE_QUANTITY_RANGE_INVERTED, set_id, 0))
        return draws
    count = uniform_quantity(number_min, number_max, count_draw)
    weights = [weight for _index, _item, weight in entries]
    for _pick in range(count):
        draws += 1
        chosen = weighted_pick(weights, rng.random())
        if chosen is None:
            refusals.append((REFUSE_VALUE_OUT_OF_RANGE, set_id, 0))
            continue
        index, item_id, _weight = entries[chosen]
        if item_id == MONEY_ITEM_ID:
            money.append(MoneyDrop(
                1, source, set_id, index, MONEY_AMOUNT_HAS_NO_COLUMN))
            continue
        try:
            _require_known_item(item_id, "roll")
        except MobLootContractError as refused:
            refusals.append((refused.args[0], set_id, index))
            continue
        items.append(DropItem(item_id, 1, source, set_id, index))
    return draws


def roll_drops(mob: Any, rng: Any) -> DropRoll:
    """Roll one dead monster's OWN drop sets, in table order.

    ``rng`` is an injected ``random.Random``.  The order is DROPS_NORMAL (per
    slot), then DROPS_EQUIPMENT, then DROPS_SPECIALLY -- OUR order, taken from
    the column order of the MOBS row itself, because the original server's is
    unrecoverable.
    """
    mob = _require_mob(mob)
    rng = _require_rng(rng)
    items: list = []
    money: list = []
    refusals: list = []
    draws = 0
    for source, set_id, row in _set_rows(mob):
        if source == SOURCE_TABLE_NORMAL:
            draws += _roll_normal(set_id, row, rng, items, money, refusals)
        else:
            draws += _roll_weighted(
                source, set_id, row, rng, items, money, refusals)
    return DropRoll(
        mob.template_id, mob.actor_identity, tuple(items), tuple(money),
        draws, tuple(refusals),
    )


# ---------------------------------------------------------------------------
# The ledger.  "On the ground" below always means "announced at a coordinate",
# never "an object exists there": GT-045 measured that no object does.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GroundDrop:
    """One object standing where a monster fell, IN THE SCENE IT FELL IN.

    ``scene`` IS REQUIRED AND HAS NO DEFAULT, round 4e9r7g (COO-DECISION
    2026-09-02T02:52+07:00, way 1).  A default -- ``field_mob_tables.SCENE``
    was the obvious one, and ``FieldMob.scene`` carries exactly that -- would
    mean a row built in Bg0015 by a caller who forgot the argument claims to
    be a bg0001 row, and the publication filter would then hide it from the
    player standing over it while showing it to a player in the town.  A
    silent wrong answer, in the one field this whole change exists to make
    trustworthy.  Every construction site says which scene, or it does not
    build a row.

    THE SCENE DOES NOT TRAVEL ON THE WIRE.  ``drop_element``* compose key,
    item, position and (since round KA1B-DROPMODEL) model type; none of them
    reads this field.  It is server-side OWNERSHIP -- which publication a row
    belongs to -- so this change moves no pinned byte, and the element and
    frame pins are unchanged by it.
    """

    drop_key: int
    item_id: int
    quantity: int
    x: float
    y: float
    z: float
    mob_identity: int
    killer_identity: int
    scene: str

    def __post_init__(self) -> None:
        _require_int(self.drop_key, "drop key", 0, 0xFFFFFFFF)
        if not DROP_KEY_BASE <= self.drop_key < DROP_KEY_LIMIT:
            raise MobLootContractError(
                REFUSE_KEY_OUTSIDE_THE_LANE_BLOCK,
                "drop key 0x%X is outside this lane's block [0x%X, 0x%X)"
                % (self.drop_key, DROP_KEY_BASE, DROP_KEY_LIMIT))
        _require_int(self.item_id, "item id", 1, 0xFFFFFFFF)
        _require_int(self.quantity, "quantity", 1, 0xFFFF)
        for label, value in (("x", self.x), ("y", self.y), ("z", self.z)):
            coordinate = _require_float32(value, label)
            if coordinate != as_wire_float(coordinate):
                raise MobLootContractError(
                    REFUSE_POSITION_OFF_THE_F32_GRID,
                    "%s is not an exact f32; quantize before building a drop"
                    % label)
        _require_identity(self.mob_identity, "mob identity")
        _require_identity(self.killer_identity, "killer identity")
        if self.mob_identity == self.killer_identity:
            raise MobLootContractError(
                REFUSE_ROLL_NAMES_ANOTHER_MONSTER,
                "a monster cannot loot itself on this lane")
        _require_known_item(self.item_id, "ground drop")
        _require_scene(self.scene, "drop scene")

    @property
    def display_name(self) -> str:
        return field_drop_tables.ITEMS[self.item_id][2]

    @property
    def scene_key(self) -> str:
        """This row's scene in comparison form.  See :func:`scene_key`."""
        return scene_key(self.scene)


@dataclass(frozen=True)
class DropLedger:
    """What is on the ground, as a tuple sorted by key.

    Sorted-tuple with a ``generation`` for the reason ``DeathRegister`` has
    one: a ledger is a VALUE, so "add a drop" is a read-modify-write of
    something nobody owns.  Two kills in the same tick both read the same
    ledger, both return a ledger of their own drops, and whichever is stored
    second erases the other kill's loot with nothing raised anywhere.
    :func:`commit_drops` is the compare-and-swap that makes the loser retry.
    """

    drops: tuple = ()
    generation: int = 0
    issued_through: int = DROP_KEY_BASE
    # ~~NO SCENE TERM~~ IS STRUCK, round 4e9r7g: COO-DECISION 2026-09-02T02:52
    # +07:00 chose WAY 1 -- every row owns the scene it fell in
    # (``GroundDrop.scene``) and a publication carries only the rows of the
    # scene being published (:meth:`for_scene`).  The ledger itself is now
    # explicitly CROSS-SCENE: rows from scene A stay in it while the player is
    # in scene B, and they are still there when the player comes back.  NOTHING
    # IS DELETED AT A SCENE BOUNDARY (COO-DECISION 2026-09-02T02:53+07:00: no
    # ledger row may be removed until a removal publisher exists).
    #
    # The paragraph below is KEPT, not deleted, because the reasoning it
    # records is still the reasoning behind the LOOTED REGISTER, which is
    # keyed by identity alone and is NOT scene-scoped:
    # NO SCENE TERM.  Keyed by ``actor_identity`` alone (round `h40iwu`,
    # answering the risk `pf_bridge/notes_to_chief/20260901_0106_LANE-B-
    # STATUS-bg0015-combat-ledger-gap-measured-*.md` recorded but left
    # unfixed).  This is safe TODAY only because ``kill_token``
    # (``death_step.register.generation``) counts up forever across every
    # scene and never resets, and because
    # ``field_mobs.cross_scene_identity_collisions()`` returns no LIVE
    # collision at HEAD (Bg0002/Bg0015 collide at placement 87, but Bg0015
    # is not registered in ``field_mobs._SCENE_TABLE_MODULES`` yet).  If
    # either of those two facts stops being true -- a scene-scoped or
    # per-scene-reset token, or a second live scene sharing an identity --
    # a re-kill of the colliding identity would be wrongly refused as
    # ``mob_already_looted``.  ``tests/test_mob_loot.py``'s
    # ``test_a_kill_token_that_moves_backward_for_the_same_identity_is_
    # refused_the_same_way_a_replay_is`` pins the exact boundary
    # (``previous >= kill_token``) this depends on.
    looted: tuple = ()

    def __post_init__(self) -> None:
        if type(self.drops) is not tuple:
            raise MobLootContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD, "drops must be a tuple")
        seen = set()
        for drop in self.drops:
            if type(drop) is not GroundDrop:
                raise MobLootContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "every ledger row must be a typed GroundDrop")
            if drop.drop_key in seen:
                raise MobLootContractError(
                    REFUSE_DUPLICATE_LEDGER_KEY,
                    "drop key 0x%X appears twice" % drop.drop_key)
            seen.add(drop.drop_key)
        ordered = tuple(sorted(self.drops, key=lambda row: row.drop_key))
        if ordered != self.drops:
            raise MobLootContractError(
                REFUSE_LEDGER_NOT_SORTED,
                "ledger rows must be given in ascending key order")
        _require_int(self.generation, "generation", 0, 2 ** 62)
        _require_int(
            self.issued_through, "issued through", DROP_KEY_BASE, DROP_KEY_LIMIT)
        if type(self.looted) is not tuple:
            raise MobLootContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD, "looted must be a tuple")
        seen_mobs = set()
        for row in self.looted:
            if type(row) is not tuple or len(row) != 2:
                raise MobLootContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "a looted row is (identity, kill token), not %r" % (row,))
            identity, token = row
            _require_identity(identity, "looted identity")
            _require_int(token, "kill token", 0, 2 ** 62)
            if identity in seen_mobs:
                raise MobLootContractError(
                    REFUSE_MOB_ALREADY_LOOTED,
                    "identity 0x%X appears twice in the looted register; the "
                    "register keeps ONE row per identity, the LAST kill token"
                    % identity)
            seen_mobs.add(identity)
        if tuple(sorted(self.looted)) != self.looted:
            raise MobLootContractError(
                REFUSE_LEDGER_NOT_SORTED,
                "the looted register must be in ascending identity order")
        for drop in self.drops:
            if drop.drop_key >= self.issued_through:
                raise MobLootContractError(
                    REFUSE_KEY_OUTSIDE_THE_LANE_BLOCK,
                    "drop key 0x%X is on the ground but the ledger says keys "
                    "were only issued through 0x%X"
                    % (drop.drop_key, self.issued_through))

    @property
    def next_key(self) -> int:
        """The key a new drop may take.  Refuses when the block is spent.

        A HIGH-WATER MARK, not ``max(key on the ground) + 1``, and the
        difference is a bug the first draft of this module shipped: a player
        who picks up the newest object removes the highest key from the
        ledger, so a derived next key would hand THAT KEY to the next kill
        while the client may still be holding the old object under it.  Keys
        are never reused inside a run; the block is 1,048,576 wide and the
        lane refuses rather than wrapping.
        """
        if self.issued_through >= DROP_KEY_LIMIT:
            raise MobLootContractError(
                REFUSE_KEY_OUTSIDE_THE_LANE_BLOCK,
                "this lane's key block is spent; nothing reuses a key while "
                "the client may still hold it")
        return self.issued_through

    def get(self, drop_key: int) -> GroundDrop:
        for drop in self.drops:
            if drop.drop_key == drop_key:
                return drop
        raise MobLootContractError(
            REFUSE_DROP_NOT_IN_LEDGER,
            "no drop with key 0x%X is on the ground" % drop_key)

    @property
    def scenes(self) -> tuple:
        """Every scene this ledger holds rows for, in comparison form, sorted.

        For a console line and for a test that wants to say "the ledger still
        remembers scene A" without reaching into rows one by one.
        """
        return tuple(sorted({drop.scene_key for drop in self.drops}))

    def rows_in_scene(self, scene: Any) -> tuple:
        """The rows that fell in ``scene``, in key order.  Compares by
        :func:`scene_key`, so ``bg0002`` and ``Bg0002`` are one scene."""
        wanted = scene_key(scene)
        return tuple(
            drop for drop in self.drops if drop.scene_key == wanted)

    def for_scene(self, scene: Any) -> "DropLedger":
        """This ledger as the scene ``scene`` sees it.  A VIEW, NOT A PRUNE.

        ROUND 4e9r7g, COO-DECISION 2026-09-02T02:52+07:00 way 1.  Returns a
        ledger carrying ONLY this scene's rows -- what a publication in this
        scene may announce -- while the ledger it was derived from keeps
        every row it had.  Rows of other scenes are not removed, not
        expired, and not counted here; they are simply not this scene's
        business.

        ``generation``, ``issued_through`` AND ``looted`` ARE CARRIED
        UNCHANGED, and each for its own reason.  ``generation`` because the
        view is not a mutation: a caller that commits against this view's
        generation is committing against the real one, which is what makes
        the stale check keep working.  ``issued_through`` because keys are a
        run-wide high-water mark and are never reused per scene.  ``looted``
        because a mob is looted once per kill token wherever it fell.

        NONCLAIM.  This does NOT make the client forget scene A's rows.  A
        client that was shown a row and then walked away still has whatever
        the client does with it; the only thing this fixes is what the
        SERVER announces.  RE-130 says a nonempty generation erases the keys
        it omits, so scene B's first publication is also what removes scene
        A's keys from the client's list -- but that is the client's list,
        not this ledger.
        """
        return DropLedger(
            self.rows_in_scene(scene), self.generation, self.issued_through,
            self.looted)


def place_drops(
    mob: Any,
    record: Any,
    roll: DropRoll,
    first_key: int,
    position: Any = None,
) -> tuple:
    """Turn a roll into the objects that stand where the monster fell.

    ``record`` is the ``mob_death.DeathRecord`` of the kill -- taken as a duck
    type on purpose so this module does not import the death lane just to read
    two identities off it, but its identities MUST agree with the roll.

    ``position`` is where it fell.  ``None`` means the roster placement
    position, which is a fallback and not a truth: a monster that chased a
    player died somewhere else, and this lane has no live position of its own.

    THE SCENE COMES FROM THE MONSTER, round 4e9r7g, and there is no argument
    for it: ``FieldMob.scene`` is the roster this mob was loaded from, so the
    scene a drop belongs to is the scene the thing that dropped it belonged
    to.  A ``scene=`` parameter here would be a second, guessable source of
    truth for the one field that decides which publication a row rides in --
    and the caller that would have to fill it in is ``runtime.py``, which is
    not this lane's file.

    Object N stands at position + ``DROP_SCATTER_STEP`` * N on X so two drops
    of one kill are not one object at one point.  Money is not placed: see
    NONCLAIM 7.
    """
    mob = _require_mob(mob)
    if type(roll) is not DropRoll:
        raise MobLootContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "roll must be a typed DropRoll")
    actor_identity = _require_identity(
        getattr(record, "actor_identity", None), "record actor identity")
    killer_identity = _require_identity(
        getattr(record, "killer_identity", None), "record killer identity")
    if actor_identity != roll.mob_identity or actor_identity != mob.actor_identity:
        raise MobLootContractError(
            REFUSE_ROLL_NAMES_ANOTHER_MONSTER,
            "the death record, the roll and the roster row must name one "
            "monster: 0x%X, 0x%X, 0x%X"
            % (actor_identity, roll.mob_identity, mob.actor_identity))
    _require_int(first_key, "first key", 0, 0xFFFFFFFF)
    if not DROP_KEY_BASE <= first_key < DROP_KEY_LIMIT:
        raise MobLootContractError(
            REFUSE_KEY_OUTSIDE_THE_LANE_BLOCK,
            "first key 0x%X is outside this lane's block" % first_key)
    if len(roll.items) > MAX_DROPS_PER_KILL:
        raise MobLootContractError(
            REFUSE_TOO_MANY_DROPS_FOR_ONE_KILL,
            "%d objects for one kill exceeds the lane ceiling of %d"
            % (len(roll.items), MAX_DROPS_PER_KILL))
    if position is None:
        base = (mob.x, mob.y, mob.z)
    else:
        try:
            base = tuple(position)
        except TypeError:
            raise MobLootContractError(
                REFUSE_POSITION_NOT_FINITE,
                "position must be an (x, y, z) triple") from None
        if len(base) != 3:
            raise MobLootContractError(
                REFUSE_POSITION_NOT_FINITE,
                "position must be an (x, y, z) triple")
    x0 = _require_float32(base[0], "position x")
    y0 = as_wire_float(_require_float32(base[1], "position y"))
    z0 = as_wire_float(_require_float32(base[2], "position z"))
    scene = _require_scene(getattr(mob, "scene", None), "mob scene")
    drops = []
    for offset, item in enumerate(roll.items):
        key = first_key + offset
        if key >= DROP_KEY_LIMIT:
            raise MobLootContractError(
                REFUSE_KEY_OUTSIDE_THE_LANE_BLOCK,
                "this kill would run past the end of the lane's key block")
        x = as_wire_float(x0 + DROP_SCATTER_STEP * offset)
        if not math.isfinite(x):
            raise MobLootContractError(
                REFUSE_POSITION_NOT_FINITE,
                "the scattered position does not survive the f32 round trip")
        drops.append(GroundDrop(
            key, item.item_id, item.quantity, x, y0, z0,
            actor_identity, killer_identity, scene,
        ))
    return tuple(drops)


def commit_drops(
    ledger_now: DropLedger,
    drops: Any,
    base_generation: Any = None,
    kill_token: Any = None,
    mob_identity: Any = None,
) -> DropLedger:
    """Fold one kill into the ledger VALUE.  Prefer :class:`DropLedgerCell`.

    ~~"a compare-and-swap"~~ IS STRUCK TWICE OVER, and both strikes are kept
    because each was a real defect this module shipped:

      1. The first draft compared key overlap only, so a pruner's ledger and a
         kill's ledger could both report generation 2 with a taken drop back on
         the ground.
      2. ``base_generation`` did not fix that.  A caller holds the ledger
         value, so ``base_generation=ledger_now.generation`` -- the most
         natural line anyone will type, and the line this module's own first
         tests typed -- satisfies the check ALWAYS.  There is no shared cell
         here for a loser to lose against; this function cannot provide
         atomicity because it is a pure function of a value nobody owns.

    So this is now the FOLD, and :class:`DropLedgerCell` is the lock.  The
    generation check stays because it catches an honest stale value, and the
    LINEAGE check below catches what a counter cannot: two ledgers of the same
    generation whose contents disagree.  ``kill_token`` is the caller's
    identifier for the DEATH (``death_step.register.generation`` is the one to
    use), so a REPLAY of one death is refused while a RESPAWNED monster killed
    again -- a new death, a new token -- is not.  ``mob_identity`` is required
    even for a roll that produced nothing, because the replay guard must cover
    the ~38 pct of kills that drop nothing too.
    """
    if type(ledger_now) is not DropLedger:
        raise MobLootContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "ledger must be a typed DropLedger")
    incoming = tuple(drops)
    for drop in incoming:
        if type(drop) is not GroundDrop:
            raise MobLootContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "every drop must be a typed GroundDrop")
    if base_generation is None:
        raise MobLootContractError(
            REFUSE_LEDGER_GENERATION_MOVED,
            "commit_drops needs the generation the caller READ")
    _require_int(base_generation, "base generation", 0, 2 ** 62)
    if ledger_now.generation != base_generation:
        raise MobLootContractError(
            REFUSE_LEDGER_GENERATION_MOVED,
            "the ledger moved from generation %d to %d under this kill; "
            "rebuild the drops against the current ledger and commit again -- "
            "do NOT re-roll, that would give one kill two rolls"
            % (base_generation, ledger_now.generation))
    if kill_token is None:
        raise MobLootContractError(
            REFUSE_MOB_ALREADY_LOOTED,
            "commit_drops needs the kill's token (use "
            "death_step.register.generation); without one, a replayed death "
            "and a respawned monster's new death are the same thing")
    _require_int(kill_token, "kill token", 0, 2 ** 62)
    identities = {drop.mob_identity for drop in incoming}
    if mob_identity is not None:
        identities.add(_require_identity(mob_identity, "mob identity"))
    if len(identities) != 1:
        raise MobLootContractError(
            REFUSE_ROLL_NAMES_ANOTHER_MONSTER,
            "one commit is one kill: name exactly one monster, got %r"
            % (sorted(identities),))
    identity = identities.pop()
    # ONE COMMIT IS ONE KILL, AND ONE KILL IS IN ONE SCENE, round 4e9r7g.
    # place_drops takes every row's scene from the same mob, so incoming rows
    # agree by construction -- which is exactly why a caller that assembled
    # rows by hand, or built one with the wrong scene, has to be refused HERE
    # rather than discovered later as a row that never appears in any
    # publication.
    scenes = {drop.scene_key for drop in incoming}
    if len(scenes) > 1:
        raise MobLootContractError(
            REFUSE_COMMIT_SPANS_TWO_SCENES,
            "one commit is one kill in one scene, got %r" % (sorted(scenes),))
    looted = dict(ledger_now.looted)
    previous = looted.get(identity)
    if previous is not None and previous >= kill_token:
        raise MobLootContractError(
            REFUSE_MOB_ALREADY_LOOTED,
            "identity 0x%X was already looted for kill token %d; a REPLAY of "
            "one death does not roll twice.  A respawn that is killed again "
            "carries a HIGHER token and is accepted -- if this refuses a kill "
            "you believe is new, the token is the thing that is wrong"
            % (identity, previous))
    existing = {drop.drop_key for drop in ledger_now.drops}
    for drop in incoming:
        if drop.drop_key in existing:
            raise MobLootContractError(
                REFUSE_LEDGER_STALE,
                "drop key 0x%X is already on the ground" % drop.drop_key)
        if drop.drop_key < ledger_now.issued_through:
            raise MobLootContractError(
                REFUSE_KEY_OUTSIDE_THE_LANE_BLOCK,
                "drop key 0x%X was issued before and may still be held by a "
                "client under a different item; keys are never reused"
                % drop.drop_key)
    merged = tuple(sorted(
        ledger_now.drops + incoming, key=lambda row: row.drop_key))
    issued = ledger_now.issued_through
    for drop in incoming:
        if drop.drop_key + 1 > issued:
            issued = drop.drop_key + 1
    looted[identity] = kill_token
    looted_next = tuple(sorted(looted.items()))
    return DropLedger(
        merged, ledger_now.generation + 1, issued, looted_next)


def take_drop(ledger_now: DropLedger, drop_key: int) -> tuple:
    """Remove one drop from the ledger and return ``(next_ledger, drop)``.

    This is the seam the pickup half will use, and it is deliberately the only
    thing this module offers toward it: it removes a row from a value.  It
    sends nothing, replies to nothing and writes nothing -- see NONCLAIM 4.
    """
    if type(ledger_now) is not DropLedger:
        raise MobLootContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "ledger must be a typed DropLedger")
    _require_int(drop_key, "drop key", 0, 0xFFFFFFFF)
    taken = ledger_now.get(drop_key)
    remaining = tuple(
        drop for drop in ledger_now.drops if drop.drop_key != drop_key)
    # issued_through and looted are CARRIED, never recomputed: a key must not
    # come back after a pickup (see DropLedger.next_key) and a corpse must not
    # become lootable again because its last drop left the ground.
    return (
        DropLedger(
            remaining, ledger_now.generation + 1, ledger_now.issued_through,
            ledger_now.looted),
        taken,
    )


#: ROUND 4e9r7g.  What replaced the clear-the-ground reconcile, named so a
#: reader who lands on that function first is told where to go instead.
SCENE_TRANSITION_RECONCILE_SUPERSEDED_BY = (
    "COO-DECISION 2026-09-02T02:52+07:00 way 1: GroundDrop.scene + "
    "DropLedger.for_scene + DropLedgerCell.enter_scene.  Do NOT call "
    "reconcile_scene_transition at a scene boundary any more; it DELETES rows, "
    "and COO-DECISION 2026-09-02T02:53+07:00 forbids removing a ledger row "
    "until a removal publisher exists."
)


def reconcile_scene_transition(ledger_now: DropLedger) -> tuple:
    """~~The scene boundary~~ SUPERSEDED, round 4e9r7g.  Do not call this.

    KEPT, NOT DELETED, because this lane strikes through and does not erase --
    and because it is still an honest primitive for "clear the ground",
    should something ever want that with a removal publisher behind it.  What
    is struck is its ROLE: it was the answer to the cross-scene leak, and
    COO-DECISION 2026-09-02T02:52+07:00 chose the OTHER of Codex's two
    bounded options.  See :data:`SCENE_TRANSITION_RECONCILE_SUPERSEDED_BY`.

    Why the replacement is better, in the words of the decision itself:
    clearing at the boundary means a player who walks back into scene A finds
    their own drop gone, and a server that has already announced an object has
    no removal publisher to tell the client the object is gone -- so the clear
    was invisible to the client anyway.  Way 1 keeps the rows, keeps them out
    of other scenes' publications, and gives them back on return.

    ~~Everything below is the reasoning of the superseded role, kept for the
    record.~~

    CODEX_URGENT 2026-09-01T20:40+07:00 (P0-5 corpse/drop state scope),
    approved for LANE-B by COO-DECISION 2026-09-01T21:48+07:00, item 2:
    :class:`DropLedger` has NO scene term (see that class's own docstring for
    why that is safe today only because ``kill_token`` counts up forever and
    no live scene shares a colliding identity) and every kill sends the LIVE
    ledger whole -- so a drop still standing in scene A rides along into the
    next publication once the player is in scene B, which contradicts the
    "cell of the scene" description ``runtime.py`` itself carries for where
    this ledger lives.

    THIS IS THE "RECONCILE THE CELL AT SCENE TRANSITION" HALF of Codex's two
    bounded options (the other being a scene term on every key, which touches
    ``GroundDrop``'s shape and every downstream consumer -- a wider change for
    the same guarantee).  Called at a scene boundary, BEFORE the first
    publish in the new scene, this returns a ledger with EVERY live row gone:
    the next kill's publication in the new scene starts from an empty ground,
    so nothing scene A left behind can ride along into it.

    ``issued_through`` AND ``looted`` ARE CARRIED, NOT RESET -- same
    discipline as :func:`take_drop`.  Drop keys are a monotonic high-water
    mark this module never reuses (a client may still be holding an old key
    under a stale object reference); the looted register is what keeps a
    respawn-and-rekill of the SAME wire identity in a later scene from being
    refused as a replay of the earlier one's kill, since ``kill_token`` only
    ever increases.  Neither of those is a "what is on the ground" fact, so
    neither is a scene fact either.

    ``generation`` ADVANCES BY EXACTLY ONE, not by the count of rows removed:
    this is one commit (a scene boundary), not N separate takes, and a
    caller holding the OLD generation across this call gets the same stale
    refusal :func:`commit_drops` already gives any caller whose read is out
    of date.

    NONCLAIM.  This does not know WHICH drops belong to which scene -- it has
    no scene data to know that with -- so it clears the WHOLE ledger rather
    than guessing.  A player who round-trips back to a scene they just left
    does not find their own recent drop waiting; that is the conservative
    side of an authenticity question CODEX_URGENT's own words leave OPEN
    ("Exact lifetime, shared-world ownership ... still need to be labelled
    RECONSTRUCTED/OPEN"), not a claim about what the original server did.
    Whether a live scene transition should call this at all, and exactly
    where, is ``runtime.py``'s call to make -- this lane's own file limits do
    not reach there; see this round's ``CORE-REQUEST``.
    """
    if type(ledger_now) is not DropLedger:
        raise MobLootContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "ledger must be a typed DropLedger")
    removed = ledger_now.drops
    if not removed:
        return ledger_now, ()
    return (
        DropLedger(
            (), ledger_now.generation + 1, ledger_now.issued_through,
            ledger_now.looted),
        removed,
    )


class DropLedgerCell:
    """THE OWNER OF THE LEDGER.  Every mutation happens here, under a lock.

    THE QUESTION THIS CLASS EXISTS TO ANSWER.  Two adversarial passes asked
    the same thing in different words: a ``DropLedger`` is a frozen value, and
    ``commit_drops`` returns a NEW value that some caller must store somewhere
    this module has never seen.  WHO OWNS THE CELL?  While the answer was
    "the chief, by hand", ``base_generation`` was not a compare-and-swap at
    all -- the caller compared a value against the same object it already
    held, so it could not lose, and a pruner and a kill could both store a
    generation-2 ledger with different contents.  The cell is the answer: the
    read, the build and the fold happen inside one lock, so a caller CANNOT
    supply a stale generation, cannot allocate a key that another kill just
    took, and cannot prune against a ledger that has moved.

    It is deliberately tiny and it still does nothing on its own: no socket and
    no thread.  ~~"no clock, no expiry"~~ IS STRUCK, round 0n9inw: the cell now
    reads a clock and expires its own rows, because COO-DECISION 2026-08-29T
    12:41+07:00 ruled a per-drop expiry to be what bounds the ledger.  What it
    still does not have is a THREAD: nothing here ticks.  The clock is read
    only when a caller touches the cell, which is what "lazy at insert and
    dispatch" means and what makes the whole mechanism testable headless with a
    clock that is just a list of numbers.

    Pruning by key remains the caller's duty and is unchanged; expiry is the
    cell's own and needs no call site at all.  The two answer different
    questions and BOTH are needed: the prune keeps the CLIENT'S generation
    narrow (RE-130 -- a nonempty generation erases the keys it omits), while
    the expiry is what bounds a cell whose caller never prunes, or prunes and
    then stops killing things.
    """

    def __init__(
        self,
        ledger: Any = None,
        lifetime_seconds: Any = DROP_LIFETIME_SECONDS,
        clock: Any = None,
        scene: Any = None,
    ) -> None:
        if ledger is None:
            ledger = DropLedger()
        if type(ledger) is not DropLedger:
            raise MobLootContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "a cell holds a typed DropLedger")
        self._lifetime = _require_lifetime(lifetime_seconds)
        # time.monotonic, not time.time: a wall clock that steps backwards over
        # a DST change or an NTP correction would freeze every deadline in the
        # future and stop the expiry dead, and one that steps forward would
        # take the ground out from under a player mid-walk.  Neither is a
        # failure this lane should be able to have.
        self._clock = _time.monotonic if clock is None else _require_clock(clock)
        self._ledger = ledger
        # Where the newest kill's key block starts, or None until a kill with
        # drops lands.  Round uq2lxw2: this is what lets prune_previous_kills
        # take NO argument -- see its docstring for why an argument was the
        # defect rather than the feature.
        self._newest_kill_first_key = None
        # WHICH SCENE THIS CELL IS PUBLISHING, round 4e9r7g.  ``None`` until a
        # scene is known, and a publication asked for while it is None is
        # REFUSED by name rather than falling back to "every row" -- see
        # :meth:`frames`.  A kill sets it (a kill happens in a scene) and
        # :meth:`enter_scene` sets it at a boundary where nothing was killed.
        self._scene = None if scene is None else _require_scene(scene, "scene")
        # Was this scene DECLARED (ctor / enter_scene), or merely inferred
        # from the last kill?  round 4e9r7g, pf-adversary: a kill used to
        # overwrite the boundary's declaration with no join at all, and
        # FieldMob.scene carries a DEFAULT ('bg0001'), so ONE hand-built mob
        # record could flip a whole session's scene, drop the player's own
        # correct rows out of the publication (RE-130 erases them on the
        # client) and then refuse their pickup as drop_is_in_another_scene.
        # mob_ledger_admission settled the principle for the combat ledger in
        # the same words: an explicit disagreement is never overruled by a
        # membership coincidence.
        self._scene_declared = scene is not None
        self._lock = threading.Lock()
        # Read once here so a broken clock is refused when the cell is built,
        # not in the middle of somebody's kill.
        self._now = _read_clock(self._clock, None)
        # key -> deadline, for the rows on the ground.  Rows handed in through
        # ``ledger`` get a deadline too: a row that entered before the cell
        # existed must not be the one row that lives forever.
        self._deadlines = {
            drop.drop_key: self._now + self._lifetime for drop in ledger.drops}
        # The bounded memory behind REFUSE_DROP_EXPIRED.  A deque, so the
        # structure that explains a refusal cannot itself grow without bound.
        self._expired = _collections.deque(maxlen=EXPIRED_KEY_MEMORY)

    def _read_now_locked(self) -> float:
        """Advance the cell's clock.  Call with the lock held.

        One reading serves a whole call: a sweep and the deadlines the same
        call hands out must agree, or a drop placed in the same breath as a
        sweep could be born already expired.
        """
        self._now = _read_clock(self._clock, self._now)
        return self._now

    def _sweep_locked(self, now: float) -> tuple:
        """Remove every row whose deadline has passed.  Lock held, no clock read.

        ``>=`` rather than ``>``: a deadline is the first instant the row is
        gone, so a click landing exactly on it is late.  With a real clock the
        difference is unobservable; with an injected one it is the difference
        between a test that pins the boundary and a test that pins nothing.
        """
        due = [
            key for key, deadline in self._deadlines.items() if now >= deadline]
        if not due:
            return ()
        ledger = self._ledger
        removed = []
        for key in sorted(due):
            # A key can be in _deadlines without being on the ground if a
            # caller took it through take_drop on a value beside the cell.
            # Dropping the deadline is right either way.
            del self._deadlines[key]
            try:
                ledger, taken = take_drop(ledger, key)
            except MobLootContractError:
                continue
            removed.append(taken)
            self._expired.append(key)
        self._ledger = ledger
        return tuple(removed)

    @property
    def ledger(self) -> DropLedger:
        """The current value.  A snapshot; storing it is not owning it.

        READING IS ONE OF THE LAZY EVALUATION POINTS, and so this property has
        a side effect, which is worth stating rather than hiding: it sweeps
        first, so a snapshot never contains a row that is already past its
        deadline.  The alternative -- a pure read -- means a caller can see a
        row here, call ``take`` on the next line and be refused for a deadline
        that had already passed when it looked.  A property that lies is worse
        than a property that works.
        """
        with self._lock:
            now = self._read_now_locked()
            self._sweep_locked(now)
            return self._ledger

    def sweep_expired(self) -> tuple:
        """Expire what is due and return the removed rows, oldest key first.

        The explicit form of what :attr:`ledger`, :meth:`loot_a_kill`,
        :meth:`take` and :meth:`frames` already do.  A caller wants this when
        it needs the ROWS -- to log them, or to send a narrower generation --
        rather than just the guarantee that they are gone.
        """
        with self._lock:
            now = self._read_now_locked()
            return self._sweep_locked(now)

    def expires_at(self, drop_key: int) -> float:
        """The deadline of one live row, on the cell's own clock.

        Refuses by name for a key that is not on the ground, so it cannot be
        used to ask whether a row exists and get a number that means "no".
        """
        drop_key = _require_int(drop_key, "drop key", 0, 0xFFFFFFFF)
        with self._lock:
            now = self._read_now_locked()
            self._sweep_locked(now)
            if drop_key not in self._deadlines:
                raise MobLootContractError(
                    REFUSE_DROP_NOT_IN_LEDGER,
                    "no drop with key 0x%X is on the ground" % drop_key)
            return self._deadlines[drop_key]

    @property
    def lifetime_seconds(self) -> float:
        """How long a row this cell places is declared to live, in seconds.

        Round m0vp7m, for MOB-DROP-PRESENCE-001: the presence console line has
        to print the lifetime this build ACTUALLY declares, not the module
        default ``DROP_LIFETIME_SECONDS`` -- a cell constructed with a
        different ``lifetime_seconds`` would otherwise be described by a number
        it does not use, which is the same class of defect as a lane-asserted
        length field that can disagree with the payload.  Read-only: the
        deadlines already handed out were computed from this value and would
        not move if it did.
        """
        return self._lifetime

    def time_left(self, drop_key: int) -> float:
        """Seconds until one live row expires, from ONE reading of the clock.

        :meth:`expires_at` plus "what time is it" is not this: those are two
        lock acquisitions with a clock read in each, so the difference between
        them can be negative for a row that expired in between, and a caller
        would have to decide what a negative remainder means.  Here the
        deadline and the now come out of the same locked read, so the value is
        always the remainder of a row that was live when it was measured.

        Refuses by name (:data:`REFUSE_DROP_NOT_IN_LEDGER`) for a key that is
        not on the ground, exactly like :meth:`expires_at`, so it cannot be
        used to ask whether a row exists and get a number that means "no".
        """
        drop_key = _require_int(drop_key, "drop key", 0, 0xFFFFFFFF)
        with self._lock:
            now = self._read_now_locked()
            self._sweep_locked(now)
            if drop_key not in self._deadlines:
                raise MobLootContractError(
                    REFUSE_DROP_NOT_IN_LEDGER,
                    "no drop with key 0x%X is on the ground" % drop_key)
            return self._deadlines[drop_key] - now

    def loot_a_kill(
        self,
        mob: Any,
        record: Any,
        roll: DropRoll,
        kill_token: Any,
        position: Any = None,
    ) -> tuple:
        """Place and fold one accepted kill.  Returns the drops to send.

        The whole read-modify-write is inside the lock, so the key block and
        the generation are the cell's to hand out, never the caller's to
        guess.  A refusal leaves the cell exactly as it was.
        """
        with self._lock:
            # INSERT is one of the two lazy points the ruling names.  Sweeping
            # BEFORE the placement, not after, is deliberate: the new rows must
            # not be measured against a deadline computed one instruction
            # earlier, and a kill is the moment a cell is most likely to be
            # holding rows nobody will ever come back for.
            now = self._read_now_locked()
            self._sweep_locked(now)
            current = self._ledger
            drops = place_drops(
                mob, record, roll, current.next_key, position=position)
            # A KILL IS A SCENE FACT, round 4e9r7g: the mob that died belongs
            # to a roster, the roster belongs to a scene, and that is the scene
            # this cell is publishing for from here on.  Set BEFORE the commit
            # can raise?  No -- AFTER, together with the ledger, so a refused
            # kill leaves the cell exactly as it was (the promise this method's
            # own docstring makes).  A kill that drops NOTHING still moves it:
            # the player is standing in that scene either way, which is what
            # the field means.
            kill_scene = _require_scene(getattr(mob, "scene", None), "mob scene")
            if (self._scene_declared
                    and scene_key(kill_scene) != scene_key(self._scene)):
                raise MobLootContractError(
                    REFUSE_KILL_IN_ANOTHER_SCENE,
                    "this cell was DECLARED into scene %s at a boundary and "
                    "this kill's monster belongs to scene %s.  One of the two "
                    "is wrong -- the scene folder the boundary passed, or the "
                    "roster the mob was loaded from -- and this lane refuses "
                    "rather than letting the kill silently move the whole "
                    "session's ground to the mob's scene.  A cell nobody "
                    "declared (no enter_scene yet) accepts any kill and takes "
                    "its scene from it"
                    % (self._scene, kill_scene))
            self._ledger = commit_drops(
                current, drops, base_generation=current.generation,
                kill_token=kill_token,
                mob_identity=getattr(record, "actor_identity", None))
            # NOT a declaration: a kill INFERS the scene for a cell nobody
            # declared one for, and can never overrule one that was.
            self._scene = kill_scene
            deadline = now + self._lifetime
            for drop in drops:
                self._deadlines[drop.drop_key] = deadline
            if drops:
                # A kill that dropped nothing does not move the mark: the
                # newest kill WITH ROWS is the one a player can be reaching
                # for, and roughly a third of kills drop nothing.
                self._newest_kill_first_key = min(
                    drop.drop_key for drop in drops)
            return drops

    def take(self, drop_key: int) -> Any:
        """Remove one row -- a pickup, or the prune the caller owes.

        DISPATCH is the second lazy point, and a click that arrives after the
        deadline is refused as :data:`REFUSE_DROP_EXPIRED` rather than as a
        missing row.  That distinction is the one round uq2lxw2 wrote down as
        owed: "the row expired" and "somebody else took it" are different
        things to tell a player, and before this round they were the same word.
        """
        drop_key = _require_int(drop_key, "drop key", 0, 0xFFFFFFFF)
        with self._lock:
            now = self._read_now_locked()
            self._sweep_locked(now)
            if drop_key in self._expired:
                raise MobLootContractError(
                    REFUSE_DROP_EXPIRED,
                    "drop 0x%X was on the ground and its deadline passed; it "
                    "was not taken by anyone" % drop_key)
            self._ledger, taken = take_drop(self._ledger, drop_key)
            self._deadlines.pop(drop_key, None)
            return taken

    def prune_previous_kills(self) -> tuple:
        """Remove every row older than the newest kill's block.  NO ARGUMENT.

        ROUND uq2lxw2, and the missing argument is the whole design.
        :meth:`prune_issued_before` takes a cut point, and pf-adversary asked
        the question that shape could not answer: where does the caller get a
        cut point it cannot get wrong?  The only correct value is the newest
        kill's first key -- which the caller would have to carry from a
        previous ``loot_a_kill`` return, does not exist for the roughly one
        kill in three that drops nothing, and sits one keystroke away from
        ``cell.ledger.next_key``, which reads more naturally and CLEARS THE
        WHOLE LEDGER.  The cell knows the right value; asking the caller for
        it was the defect.

        Returns the removed rows.  Empty when no kill has dropped anything
        yet, and empty when the newest kill is the only one -- both are
        no-ops rather than "prune everything", which is the direction that
        costs a player their drop.

        ROUND 4e9r7g, AND THIS METHOD IS NOW SCENE-BLIND IN A WAY THAT
        MATTERS.  It cuts by KEY, and keys are issued across scenes from one
        block, so after a player crosses a scene the "older" rows it removes
        are the ones standing in the scene they left -- which
        COO-DECISION 2026-09-02T02:53+07:00 forbids removing until a removal
        publisher exists.  NOTHING IN PRODUCTION CALLS IT (``runtime.py``
        says so at its own MOB_LOOT block: expiry plus
        ``mob_drop_presence.sustain_a_kill``'s trim are the only bounds), and
        it is not deleted here because it is still correct for what it says
        it does inside ONE scene.  A caller that wants it back under way 1
        needs a scene-scoped cut point, which is a change for the round that
        needs it -- named here rather than discovered by a player whose
        ground vanished when they walked through a door.
        """
        with self._lock:
            mark = self._newest_kill_first_key
        if mark is None:
            return ()
        return self.prune_issued_before(mark)

    def prune_issued_before(self, drop_key: Any) -> tuple:
        """Remove every live row whose key is BELOW ``drop_key``.  Returns them.

        ROUND uq2lxw2, and it exists because of a measurement chief made in
        round ni2wh2 and could not act on inside their own file: ``runtime.py``
        obeys :data:`MOB_LOOT_WIRING` step 4 by taking EVERY key of the kill it
        just sent, in the same dispatch -- so a pickup call site, the day it
        exists, is refused ``drop_already_taken`` 100% of the time.  Their
        control run: prune-as-runtime-does -> 0 live rows, refused; no prune ->
        2 live rows, accepted.

        MOST CALLERS WANT :meth:`prune_previous_kills`, which computes the one
        cut point that is correct and takes nothing to get wrong.  This is the
        primitive under it, for a caller that genuinely has its own cut point.

        A CUT ABOVE THE NEWEST KILL IS REFUSED BY NAME, and that refusal is
        this method's whole safety story (pf-adversary, round uq2lxw2):
        ``prune_issued_before(cell.ledger.next_key)`` is the single most
        natural line a caller would type, and without the refusal it removes
        every live row -- reproducing, in one plausible line, exactly the
        runtime-today behaviour this method exists to replace.  Clearing the
        ledger outright is still possible through :meth:`take` per row; it is
        just no longer something a caller can do by accident while meaning
        the opposite.

        WHY STEP 4 SAYS PRUNE AT ALL, kept in view rather than argued away:
        nothing in this module expires a row, so a caller that never prunes
        grows the ledger without bound.  That ceiling is real and this method
        does not remove it -- it moves WHERE the cut is made.  Pruning the
        PREVIOUS kills when the next kill lands leaves the newest kill's rows
        on the ground (the only ones a player could be reaching for) while
        still bounding the LIVE ROWS a cell holds.  It does not bound the KEY
        BLOCK, which is spent by issuance and not returned by pruning; that
        ceiling refuses by name in ``commit_drops`` when it is reached.

        NO CLOCK, and that is why the cut is by key rather than by age.  Keys
        are a monotonic high-water mark this cell hands out and never reuses
        (``DropLedger.next_key``), so "issued before" is an ordering this
        module can evaluate on its own values.  An expiry in SECONDS would
        need a clock, which this lane does not have and will not grow for
        this.

        [ASSUMPTION OF LANE B - AWAITING COO] chief's letter put the ledger
        ceiling to the COO as an open question (a timer, or a per-drop
        expiry).  This lane shipped the answer that needs no clock and no
        ruling so option 3 does not wait on a design round; a ruling may name
        a different one, and this is a primitive rather than a policy so that
        it can.

        Returns the removed rows, newest last, so a caller can log or re-send
        what it dropped rather than discovering it later.
        """
        # The same bound every other drop key in this module carries; a cut
        # point is a key, so it is validated as one.
        drop_key = _require_int(drop_key, "prune key", 0, 0xFFFFFFFF)
        with self._lock:
            newest = self._newest_kill_first_key
            if newest is not None and drop_key > newest:
                raise MobLootContractError(
                    REFUSE_PRUNE_WOULD_TAKE_THE_NEWEST_KILL,
                    "cut point 0x%X is above the newest kill's first key "
                    "0x%X, so this would take the rows a player can still be "
                    "reaching for - prune_previous_kills() is the call that "
                    "cannot get this wrong, and take(key) is how you remove "
                    "a row deliberately" % (drop_key, newest))
            ledger = self._ledger
            removed = []
            for drop in ledger.drops:
                if drop.drop_key < drop_key:
                    ledger, taken = take_drop(ledger, drop.drop_key)
                    removed.append(taken)
                    # Round 0n9inw: a pruned row must lose its deadline too.
                    # A deadline outliving its row is not harmless -- it is a
                    # key this cell would later "expire" and remember as
                    # expired, so a pickup call site would be told a row the
                    # PRUNE removed had timed out.
                    self._deadlines.pop(drop.drop_key, None)
            self._ledger = ledger
            return tuple(removed)

    def reconcile_scene_transition(self) -> tuple:
        """Clear every live row, under the lock.  See the module function of
        the same name for why (CODEX_URGENT 2026-09-01T20:40+07:00 / COO-
        DECISION 2026-09-01T21:48+07:00, item 2).

        A DEDICATED CELL METHOD RATHER THAN A LOOP OF ``take`` CALLS AT THE
        CALL SITE, same reasoning as every other mutation on this class: the
        read, the clear and the deadline bookkeeping happen inside ONE lock
        acquisition, so a kill landing in the middle of a scene-transition
        reconcile cannot interleave with it and leave a half-cleared cell.
        Also resets ``_newest_kill_first_key`` to ``None`` -- the newest
        kill's rows are gone too, so the mark that used to protect them from
        :meth:`prune_previous_kills` must go with them, or the NEXT scene's
        first kill would be silently protected from a prune it never earned.

        Returns the rows that were on the ground, oldest key first, so a
        caller can log what a scene transition actually cleared.
        """
        with self._lock:
            now = self._read_now_locked()
            self._sweep_locked(now)
            self._ledger, removed = reconcile_scene_transition(self._ledger)
            for drop in removed:
                self._deadlines.pop(drop.drop_key, None)
            self._newest_kill_first_key = None
            return removed

    @property
    def current_scene(self):
        """The scene this cell publishes for, or ``None`` if it does not know.

        ``None`` is a real state and not a bug: a cell that has been built and
        never entered a scene nor looted a kill has nothing to publish for.
        Every publication path treats it as "refuse", never as "all".
        """
        with self._lock:
            return self._scene

    def enter_scene(self, scene: Any) -> tuple:
        """Point this cell at a scene.  Returns ``(previous_scene,
        current_scene, rows_standing_elsewhere, rows_expired_by_this_call)``.

        ~~"DELETES NOTHING"~~ IS STRUCK BEFORE IT EVER SHIPPED, and the
        correction is the reason the fourth element exists.  pf-adversary
        (round 4e9r7g) measured the headline false: this method sweeps, like
        every other entry point on this cell, so a player who crosses a
        boundary after being away longer than DROP_LIFETIME_SECONDS gets
        their expired rows removed BY THIS CALL -- and the third element,
        offered as the number that proves nothing was thrown away, read 0 in
        exactly that case, because by then there was nothing left to count.
        A state reading standing in for a comparison.

        SO, EXACTLY: this call removes nothing FOR BEING A BOUNDARY.  The
        only rows it can drop are rows whose own deadline had already passed
        (the per-drop expiry of COO-DECISION 2026-08-29T12:41+07:00, which is
        lazy and therefore always somebody's call), and it now RETURNS HOW
        MANY, so a caller can tell "nothing was there" from "this call
        collected four corpses of drops".  Removing the sweep instead was the
        other option and it is worse: the elsewhere count would then include
        rows that are already dead, which is a second wrong number in place
        of a reported one.

        ROUND 4e9r7g -- the replacement for
        :meth:`reconcile_scene_transition` at a scene boundary, per
        COO-DECISION 2026-09-02T02:52+07:00 way 1.  Call it ONCE at the scene
        boundary, BEFORE the first publish in the new scene, at the same place
        the census-anchor / combat / AI reset already happens for a scene sync.

        WHAT IT DOES NOT DO IS THE POINT.  It removes no row, expires nothing
        early, and moves neither ``generation`` nor ``issued_through``: the
        drops of the scene being left STAY on the ground, and a player who
        walks back gets them back in that scene's next publication.  The whole
        cross-scene guarantee is carried by the filter in :meth:`frames`, not
        by taking anything away (COO-DECISION 2026-09-02T02:53+07:00: no
        ledger row may be removed until a removal publisher exists).

        Entering the scene the cell is already in is a no-op that still
        answers, so a call site may call it unconditionally on every sync.

        The third element is how many rows are standing in OTHER scenes
        after this call; the fourth is how many rows the lazy expiry
        collected during it.  Read together they are a comparison rather
        than a reading: elsewhere=0 with expired=0 means the ground was
        already empty, elsewhere=0 with expired=4 means it was not.
        """
        previous, scene, elsewhere, expired, _view = self._enter_scene(scene)
        return previous, scene, elsewhere, expired

    def _enter_scene(self, scene: Any) -> tuple:
        """The locked half of :meth:`enter_scene`, plus the entered scene's
        own rows as a value.

        ONE ACQUISITION, for the reason :meth:`publication` is one: a caller
        that entered the scene and then read the ledger holds two facts a kill
        landing between them can make disagree, and the disagreement composes
        a generation that omits a live key of the scene it publishes -- which
        RE-130 says ERASES that key on the client.
        """
        scene = _require_scene(scene, "scene")
        with self._lock:
            now = self._read_now_locked()
            expired = self._sweep_locked(now)
            previous = self._scene
            self._scene = scene
            self._scene_declared = True
            whole = self._ledger
            view = whole.for_scene(scene)
            elsewhere = len(whole.drops) - len(view.drops)
            return previous, scene, elsewhere, len(expired), view

    def enter_scene_frames(self, legacy: Any, scene: Any) -> tuple:
        """:meth:`enter_scene`, and the ONE generation that re-announces the
        entered scene's ground.  ``(previous, current, elsewhere, expired,
        frames)``.

        COO-DECISION 2026-09-02T09:44+07:00, answering this lane's own
        question of 09:15 ("who re-announces a scene's ground when the player
        walks back into it").  Way 1 (COO 0252) keeps scene A's rows STANDING
        while the player is in scene B -- but a row the server holds and the
        screen does not draw is a row the player cannot pick up, so the half
        of way 1 the owner can see did not exist until something re-announced
        it.  Before this, the only thing that did was the next KILL in that
        scene, and "walk back and kill something else" is not what way 1
        promised.

        WHY THIS IS NOT THE REFUSED REFRESH TIMER.  The COO refused a cadence
        on 2026-08-26 (see :func:`refresh_frames`): a periodic re-emission of
        the ground.  This fires on a ONE-OFF EVENT -- a scene boundary, the
        same class of trigger as a kill -- and the same ruling states that
        distinction in those words: what is forbidden is a timer, not an
        event.  One frame per scene crossing.

        AN EMPTY SCENE SENDS NOTHING, and that is the ruling too.  A zero-row
        generation is a no-op on the client per RE-082, so emitting one would
        be bytes that mean nothing; worse, it would spend this lane's only
        UNMEASURED shape (a generation carrying no elements) on a case that
        gains nothing, while the removal publisher COO 0253 asks for has not
        been designed yet.  ``frames`` is the empty tuple there and the caller
        sends nothing.

        ENTERING THE SCENE THE CELL IS ALREADY IN PUBLISHES NOTHING, and that
        is not an optimisation -- it is the ruling.  ~~"calling it for the
        scene the cell is already in is a no-op, so it is safe to call on
        every sync"~~ WAS TRUE OF ``enter_scene`` AND WAS CARRIED OVER HERE
        UNCHECKED (pf-adversary, round 9jrsei, D2): measured, five
        consecutive calls for the same scene composed five full ground
        generations.  A caller following that sentence would have put a
        ground re-emission on every sync -- a cadence, which is the thing
        COO-DECISION 2026-08-26T07:45+07:00 refused, arrived at through a
        method whose own docstring says it is not one.  So the publication is
        bound to the CROSSING: ``previous`` differing from ``current`` is the
        event, and a repeat call for the same scene answers with the same
        four values and no frames.

        The bytes are composed OUTSIDE the lock, from the ledger VALUE this
        call snapshotted, because composing bytes under a lock a kill is
        waiting on is how a lane earns a stall it cannot see.  WHAT THE ONE
        ACQUISITION BUYS, EXACTLY (pf-adversary D7 struck the wider claim):
        the scene and the rows agree with each other, so the generation
        cannot omit a live key of the scene it publishes AS OF THE SNAPSHOT.
        It buys nothing about freshness at SEND time: a kill that lands after
        this returns composes a NEWER generation, and whichever of the two
        reaches the client last is the one RE-130 keeps.  The caller owes the
        ordering, and :data:`MOB_LOOT_WIRING` step 6 now states it.

        [ASSUMPTION OF LANE B - AWAITING AN ATTENDED ROUND] that a client
        which draws a generation sent after a kill also draws the same
        generation sent at a scene boundary.  NONCLAIM 12 (nobody has watched
        what a re-emission does to a label that is already drawn) is
        untouched by this and stays open.  ~~GT-204's re-entry step is where
        both get watched~~ IS STRUCK (pf-adversary D8): GT-204 is the chief's
        ticket, is BLOCKED, and its steps are kill / walk / click / bag with
        no walk-out-and-back step in them.  COO-DECISION 0944 assigns adding
        one to the chief and it has not been added, so nothing is scheduled
        to watch this yet.

        AND THE COST OF THE EMPTY-SCENE RULE, named rather than left for a
        player to find (pf-adversary D11): entering a scene with no rows
        publishes nothing, so nothing clears the LABELS the previous scene
        drew -- a zero-row generation is a client no-op (RE-082).  A click on
        one of those is refused by name, ``drop_is_in_another_scene``.  The
        alternative was to spend the one shape nobody has measured to say
        nothing, and the removal publisher COO-DECISION 0253 asks for is
        where this gets fixed properly.
        """
        previous, scene, elsewhere, expired, view = self._enter_scene(scene)
        if previous is not None and scene_key(previous) == scene_key(scene):
            return previous, scene, elsewhere, expired, ()
        frames = self._boundary_frames(legacy, view)
        return previous, scene, elsewhere, expired, frames

    @staticmethod
    def _boundary_frames(legacy: Any, view: "DropLedger") -> tuple:
        """The entered scene's generation, TRIMMED and typed, or ``()``.

        pf-adversary, round 9jrsei, D5: the first draft called
        :func:`refresh_frames` bare, so a scene holding more rows than one
        frame can carry raised ``generation_too_wide_to_frame`` OUT OF A
        SCENE TRANSITION -- after the cell had already advanced -- and a
        ``legacy`` that is not a serializer raised a bare ``AttributeError``.
        The sibling emitter (``mob_drop_presence.sustain_a_kill``) has
        trimmed to the composer's own cap for exactly this reason since its
        own adversarial pass, with a comment about turning a graceful trim
        into a full refusal.  This is the same trim, kept here rather than
        imported, because ``mob_drop_presence`` imports THIS module.

        The trim keeps the OLDEST rows: the drop a player walked back for is
        older than the one that fell while they were away, and the newer one
        will be re-announced by its own kill's generation anyway.
        """
        if not view.drops:
            return ()
        for name in ("u32tag", "u8tag", "u16tag", "f32tag", "frame_pc"):
            if not callable(getattr(legacy, name, None)):
                raise MobLootContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "enter_scene_frames needs the frozen v141 serializer "
                    "handle; this one has no %s" % name)
        cap = (
            DROP_MAX_ELEMENTS_PER_FRAME_WITH_MODEL_TYPE
            if DROP_MODEL_TYPE_FIELD_ENABLED
            else DROP_MAX_ELEMENTS_PER_FRAME
        )
        rows = view.drops
        if len(rows) > cap:
            view = DropLedger(
                rows[:cap], view.generation, view.issued_through, view.looted)
        return refresh_frames(legacy, view)

    def publication(self) -> tuple:
        """``(scene, scene_ledger, rows_standing_elsewhere)``, ONE acquisition.

        THE REASON THIS EXISTS RATHER THAN TWO READS, and it is the same
        reason :attr:`ledger` sweeps: a caller that reads the ledger and then
        reads :attr:`current_scene` holds two values that a kill landing
        between them can make disagree.  The kill would move the scene AND
        add that scene's rows, so the caller would compose scene B's
        generation out of a ledger snapshot taken before B's rows existed --
        a generation that omits a live key of its own scene, which RE-130
        says ERASES that key on the client.  Narrow, real, and free to close:
        both facts come out of one lock here.

        ``scene`` is ``None`` when the cell does not know its scene, and the
        LEDGER IS ``None`` WITH IT -- pf-adversary (round 4e9r7g): returning
        the whole cross-scene ledger there left a seam pointing the opposite
        way from :meth:`scene_ledger`, which refuses by name in the same
        case.  A future caller writing ``_, ledger, _ = cell.publication()``
        would have published every scene.  The third element still says how
        many rows are standing, so a caller can still report the ground
        without ever being handed rows it may not send.
        """
        with self._lock:
            now = self._read_now_locked()
            self._sweep_locked(now)
            whole = self._ledger
            scene = self._scene
            if scene is None:
                return None, None, len(whole.drops)
            view = whole.for_scene(scene)
            return scene, view, len(whole.drops) - len(view.drops)

    def scene_ledger(self) -> DropLedger:
        """The live rows of :attr:`current_scene` only, as a ledger value.

        Sweeps first, exactly like :attr:`ledger`, so a caller cannot compose
        a publication from a row whose deadline has already passed.  Refuses
        by name when the cell does not know its scene.
        """
        scene, ledger, _elsewhere = self.publication()
        if scene is None:
            raise MobLootContractError(
                REFUSE_NO_SCENE_TO_PUBLISH,
                "this cell does not know which scene it is publishing; "
                "call enter_scene() at the scene boundary (a kill sets it "
                "too).  It will NOT fall back to publishing every scene's "
                "rows -- that is the leak way 1 closed")
        return ledger

    def frames(self, legacy: Any) -> tuple:
        """Re-emit this scene's live rows.  See :func:`refresh_frames` for the
        caveat, and :meth:`enter_scene` for what "this scene" means.

        ROUND 4e9r7g: ~~"every live row"~~ IS STRUCK.  This composes the rows
        of :attr:`current_scene` and nothing else, so a drop still standing in
        scene A cannot ride along into a publication the player receives while
        standing in scene B.  A cell that does not know its scene refuses by
        name rather than publishing everything.
        """
        return refresh_frames(legacy, self.scene_ledger())


# ---------------------------------------------------------------------------
# The composer.  Two independent derivations of the same element, compared on
# every call: if the legacy tag helpers ever drift, this lane stops emitting
# rather than emitting something a client has never accepted.
# ---------------------------------------------------------------------------
def _element_via_tags(legacy: Any, drop: GroundDrop) -> bytes:
    return (
        legacy.u32tag(ELEMENT_KEY_TAG, drop.drop_key)
        + legacy.u8tag(ELEMENT_MASK_TAG, ELEMENT_MASK_POSITION_AND_DWORD)
        + legacy.u32tag(ELEMENT_PAYLOAD_TAG, drop.item_id)
        + legacy.f32tag(drop.x)
        + legacy.f32tag(drop.y)
        + legacy.f32tag(drop.z)
    )


def _element_via_struct(drop: GroundDrop) -> bytes:
    """The same element built from the pinned layout, with no legacy helper."""
    return (
        bytes([ELEMENT_KEY_TAG]) + struct.pack("<I", drop.drop_key)
        + bytes([ELEMENT_MASK_TAG, ELEMENT_MASK_POSITION_AND_DWORD])
        + bytes([ELEMENT_PAYLOAD_TAG]) + struct.pack("<I", drop.item_id)
        + bytes([ELEMENT_F32_TAG]) + struct.pack("<f", drop.x)
        + bytes([ELEMENT_F32_TAG]) + struct.pack("<f", drop.y)
        + bytes([ELEMENT_F32_TAG]) + struct.pack("<f", drop.z)
    )


def drop_element(legacy: Any, drop: Any) -> bytes:
    """One 0x5F85B0 element for one ground drop, mask 0x12."""
    if type(drop) is not GroundDrop:
        raise MobLootContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "drop must be a typed GroundDrop")
    via_tags = _element_via_tags(legacy, drop)
    via_struct = _element_via_struct(drop)
    if via_tags != via_struct:
        raise MobLootContractError(
            REFUSE_ELEMENT_ENCODER_DISAGREES,
            "the legacy tag helpers and the pinned layout disagree; this lane "
            "refuses to emit a shape no client has accepted")
    return via_tags


# ---------------------------------------------------------------------------
# The mask-0x16 sibling.  Same two-derivation-compared shape as
# ``drop_element`` above; the only difference is the extra field and that
# nothing here is pinned to a real client's bytes (see the constants block
# this reads from for why).
# ---------------------------------------------------------------------------
def _element_via_tags_with_model_type(legacy: Any, drop: GroundDrop) -> bytes:
    model_type = _model_type_for_item(drop.item_id)
    return (
        legacy.u32tag(ELEMENT_KEY_TAG, drop.drop_key)
        + legacy.u8tag(ELEMENT_MASK_TAG, ELEMENT_MASK_WITH_MODEL_TYPE)
        + legacy.u32tag(ELEMENT_PAYLOAD_TAG, drop.item_id)
        + legacy.u16tag(ELEMENT_MODEL_TYPE_TAG, model_type)
        + legacy.f32tag(drop.x)
        + legacy.f32tag(drop.y)
        + legacy.f32tag(drop.z)
    )


def _element_via_struct_with_model_type(drop: GroundDrop) -> bytes:
    """The same wide element built from the pinned layout, no legacy helper."""
    model_type = _model_type_for_item(drop.item_id)
    return (
        bytes([ELEMENT_KEY_TAG]) + struct.pack("<I", drop.drop_key)
        + bytes([ELEMENT_MASK_TAG, ELEMENT_MASK_WITH_MODEL_TYPE])
        + bytes([ELEMENT_PAYLOAD_TAG]) + struct.pack("<I", drop.item_id)
        + bytes([ELEMENT_MODEL_TYPE_TAG]) + struct.pack("<H", model_type)
        + bytes([ELEMENT_F32_TAG]) + struct.pack("<f", drop.x)
        + bytes([ELEMENT_F32_TAG]) + struct.pack("<f", drop.y)
        + bytes([ELEMENT_F32_TAG]) + struct.pack("<f", drop.z)
    )


def drop_element_with_model_type(legacy: Any, drop: Any) -> bytes:
    """One mask-0x16 element: the proven mask-0x12 fields plus
    :data:`ELEMENT_MODEL_TYPE_TAG` (mask bit 0x04, ``n_DROPMODEL_TYPE``).

    [DERIVED, not yet client-measured].  See the module docstring's "WHAT
    THIS ROUND ADDS" section and ``MOB_LOOT_NONCLAIMS`` for what is and is
    not proven -- no client has ever been shown these bytes, and this
    function does not claim otherwise.  The value composed is pulled from
    ``field_drop_tables.ITEMS[item_id][3]`` via :func:`_model_type_for_item`,
    never guessed.
    """
    if type(drop) is not GroundDrop:
        raise MobLootContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "drop must be a typed GroundDrop")
    via_tags = _element_via_tags_with_model_type(legacy, drop)
    via_struct = _element_via_struct_with_model_type(drop)
    if via_tags != via_struct:
        raise MobLootContractError(
            REFUSE_ELEMENT_ENCODER_DISAGREES,
            "the legacy tag helpers and the pinned wide layout disagree; "
            "this lane refuses to emit a shape it cannot check")
    if len(via_tags) != DROP_ELEMENT_SIZE_WITH_MODEL_TYPE:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "a mask-0x16 element is %d bytes, composed %d"
            % (DROP_ELEMENT_SIZE_WITH_MODEL_TYPE, len(via_tags)))
    return via_tags


def drop_collection_pc(legacy: Any, drops: Any) -> bytes:
    """ONE RuntimeRes generation carrying every drop THE CALLER PASSES.

    READ THE SCOPE BEFORE THE REASON.  ~~"carrying EVERY drop that must
    coexist"~~ IS STRUCK IN THE ROUND THAT WROTE IT (pf-adversary D8): that
    is ``RE-130``'s wording, and this function only carries what the caller
    hands it.  The shipped caller hands it ONE KILL's rows, so two kills a
    few hundred milliseconds apart still take each other's keys down.  The
    letter's second bullet is satisfied WITHIN a kill and still violated
    ACROSS kills -- see NONCLAIM 20, which is the honest version of this
    line and is not a promise this function keeps.

    THE SHAPE CHANGED IN ROUND ``zxnwtd`` AND ``RE-130`` IS WHY.  ~~"one
    element per frame ... this lane does not change the shape"~~ IS STRUCK,
    not deleted: it was the honest position while the question was open, and
    ``RE-130 GROUND-ITEM-LABEL-LIFETIME-VS-LIST-MEMBERSHIP-001`` closed it
    DONE/PASS on 2026-08-28T20:18+07:00 with a BUILD_IMPACT written for this
    lane by name:

      * the consumer's ``count`` is read from the list object at ``+0x2C``
        and its codec loop takes more than one (span ``[0x006AF970,
        0x006B03E3)``, sha e5eb9e15..., re-confirming RE-082);
      * every NONEMPTY generation updates the keys it carries and then
        ERASES every key it omits (``0x005E0D40`` called at ``0x006AFF84``
        and ``0x006B0368``) -- replacement by omission, not accumulation;
      * so N nonempty single-element generations do NOT put N drops on the
        ground.  Each one erases the one before it, and takes the previous
        element's owned ``NameBoard_ITEM`` (``runtime+0x80``) down the
        destructor path with it.

    That last line is what makes the old shape a DEFECT rather than a
    conservative choice: a kill that rolled three objects announced three
    generations of one element each, and only the LAST of them could still
    be in the client's keyed tree when the dust settled.

    WHAT THIS IS NOT.  RE-130's own nonclaims travel with the change and
    this lane repeats them rather than rounding them off:

      * NOT that a label now lives longer.  The measured 0.2-0.4 s of
        GT-045 is untouched; RE-130 says in terms that fixing the
        membership confound "does not guarantee visible label lifetime".
      * NOT that the client DRAWS N labels at once.  The codec accepting
        ``count > 1`` is a static fact about the deserialiser.  What a
        player sees is client-observable and is what ``GT-132`` is for.
      * NOT that ``count = 0`` clears anything: RE-130 found that branch
        goes straight to the epilogue in this consumer.  This lane never
        emits an empty generation and refuses to compose one.
    """
    rows = tuple(drops)
    if not rows:
        raise MobLootContractError(
            REFUSE_GENERATION_IS_EMPTY,
            "an empty generation is a no-op in this consumer (RE-130 T3), "
            "not a clear; this lane refuses to compose one")
    if len(rows) > DROP_MAX_ELEMENTS_PER_FRAME:
        raise MobLootContractError(
            REFUSE_GENERATION_TOO_WIDE_TO_FRAME,
            "%d elements is wider than this lane can frame without a "
            "multi-run literal it has never composed (ceiling %d, and it is "
            "OURS, not a client limit)"
            % (len(rows), DROP_MAX_ELEMENTS_PER_FRAME))
    elements = [drop_element(legacy, drop) for drop in rows]
    keys = [drop.drop_key for drop in rows]
    if len(set(keys)) != len(keys):
        raise MobLootContractError(
            REFUSE_DUPLICATE_KEY_IN_GENERATION,
            "two drops in one generation carry the same key; the consumer "
            "keys its tree on that dword (RE-130 T3) and the second would "
            "silently replace the first")
    payload = b"".join(elements)
    pc = bytearray()
    pc += legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_RES)
    pc += legacy.u32tag(0x14, 0)
    pc += legacy.u8tag(0x08, ENVELOPE_VERSION)
    pc += legacy.u8tag(0x0B, 0)                                # inherited none
    pc += legacy.u8tag(0x0B, RUNTIME_DERIVED_BIT_GROUND_LIST)  # derived 0x08
    pc += legacy.u16tag(ELEMENT_LIST_COUNT_TAG, len(rows))
    pc += payload
    pc = bytes(pc)
    expected_size = DROP_ENVELOPE_SIZE + DROP_ELEMENT_SIZE * len(rows)
    if len(pc) != expected_size:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "a %d-element ground pc is %d bytes, composed %d"
            % (len(rows), expected_size, len(pc)))
    if pc[:DROP_ENVELOPE_CONSTANT_SIZE] != DROP_ENVELOPE_CONSTANT_PIN:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the composed envelope is not the pinned envelope; the legacy "
            "serializer moved under this lane and it refuses to emit")
    if pc[DROP_ENVELOPE_CONSTANT_SIZE] != ELEMENT_LIST_COUNT_TAG:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the count record does not start with the pinned 0x12 tag")
    declared = struct.unpack(
        "<H", pc[DROP_ENVELOPE_CONSTANT_SIZE + 1:DROP_ENVELOPE_SIZE])[0]
    if declared != len(rows):
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the generation declares %d elements and carries %d"
            % (declared, len(rows)))
    if pc[DROP_ENVELOPE_SIZE:] != payload:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the composed pc does not end in the elements it was built from")
    if len(rows) == 1 and pc[:DROP_ENVELOPE_SIZE] != DROP_ENVELOPE_PIN:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "a one-element generation no longer composes to the envelope "
            "GT-045 measured, byte for byte")
    for index, drop in enumerate(rows):
        base = DROP_ENVELOPE_SIZE + index * DROP_ELEMENT_SIZE
        coordinates = b"".join(
            pc[base + start:base + end]
            for start, end in DROP_ELEMENT_COORD_SPANS
        )
        if coordinates != struct.pack("<fff", drop.x, drop.y, drop.z):
            raise MobLootContractError(
                REFUSE_COMPOSED_BYTES_OFF_PIN,
                "element %d's composed coordinates are not that drop's "
                "coordinates" % index)
    return pc


def drop_collection_pc_with_model_type(legacy: Any, drops: Any) -> bytes:
    """mask-0x16 sibling of :func:`drop_collection_pc`.

    [DERIVED, not yet client-measured].  Same generation shape as the
    proven function above -- one envelope, N elements, RE-130's
    replace-by-omission rules apply identically because this function
    changes the ELEMENT, not the generation/frame structure -- with every
    element carrying the mask-0x04 model-type field
    (:data:`ELEMENT_MODEL_TYPE_TAG`) alongside the mask-0x12 fields this
    lane has already put on a real client's wire.  See ka1-B's letter
    (pf_bridge notes_to_chief/20260901_2015_KA1B-TO-LANE-B-drop-model-
    selector-field-is-not-on-our-wire.md) and ``MOB_LOOT_NONCLAIMS`` for
    what is and is not proven about it.
    """
    rows = tuple(drops)
    if not rows:
        raise MobLootContractError(
            REFUSE_GENERATION_IS_EMPTY,
            "an empty generation is a no-op in this consumer (RE-130 T3), "
            "not a clear; this lane refuses to compose one")
    if len(rows) > DROP_MAX_ELEMENTS_PER_FRAME_WITH_MODEL_TYPE:
        raise MobLootContractError(
            REFUSE_GENERATION_TOO_WIDE_TO_FRAME,
            "%d elements is wider than this lane can frame without a "
            "multi-run literal it has never composed (ceiling %d, and it is "
            "OURS, not a client limit)"
            % (len(rows), DROP_MAX_ELEMENTS_PER_FRAME_WITH_MODEL_TYPE))
    elements = [drop_element_with_model_type(legacy, drop) for drop in rows]
    keys = [drop.drop_key for drop in rows]
    if len(set(keys)) != len(keys):
        raise MobLootContractError(
            REFUSE_DUPLICATE_KEY_IN_GENERATION,
            "two drops in one generation carry the same key; the consumer "
            "keys its tree on that dword (RE-130 T3) and the second would "
            "silently replace the first")
    payload = b"".join(elements)
    pc = bytearray()
    pc += legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_RES)
    pc += legacy.u32tag(0x14, 0)
    pc += legacy.u8tag(0x08, ENVELOPE_VERSION)
    pc += legacy.u8tag(0x0B, 0)                                # inherited none
    pc += legacy.u8tag(0x0B, RUNTIME_DERIVED_BIT_GROUND_LIST)  # derived 0x08
    pc += legacy.u16tag(ELEMENT_LIST_COUNT_TAG, len(rows))
    pc += payload
    pc = bytes(pc)
    expected_size = (
        DROP_ENVELOPE_SIZE + DROP_ELEMENT_SIZE_WITH_MODEL_TYPE * len(rows))
    if len(pc) != expected_size:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "a %d-element wide ground pc is %d bytes, composed %d"
            % (len(rows), expected_size, len(pc)))
    if pc[:DROP_ENVELOPE_CONSTANT_SIZE] != DROP_ENVELOPE_CONSTANT_PIN:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the composed envelope is not the pinned envelope; the legacy "
            "serializer moved under this lane and it refuses to emit")
    if pc[DROP_ENVELOPE_CONSTANT_SIZE] != ELEMENT_LIST_COUNT_TAG:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the count record does not start with the pinned 0x12 tag")
    declared = struct.unpack(
        "<H", pc[DROP_ENVELOPE_CONSTANT_SIZE + 1:DROP_ENVELOPE_SIZE])[0]
    if declared != len(rows):
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the generation declares %d elements and carries %d"
            % (declared, len(rows)))
    if pc[DROP_ENVELOPE_SIZE:] != payload:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the composed pc does not end in the elements it was built from")
    if len(rows) == 1 and pc[:DROP_ENVELOPE_SIZE] != DROP_ENVELOPE_PIN:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "a one-element wide generation does not compose to the same "
            "envelope GT-045 measured for the narrow shape; the envelope is "
            "identical between the two masks and this must never diverge")
    for index, drop in enumerate(rows):
        base = DROP_ENVELOPE_SIZE + index * DROP_ELEMENT_SIZE_WITH_MODEL_TYPE
        coordinates = b"".join(
            pc[base + start:base + end]
            for start, end in DROP_ELEMENT_COORD_SPANS_WITH_MODEL_TYPE
        )
        if coordinates != struct.pack("<fff", drop.x, drop.y, drop.z):
            raise MobLootContractError(
                REFUSE_COMPOSED_BYTES_OFF_PIN,
                "element %d's composed coordinates are not that drop's "
                "coordinates" % index)
        model_start, model_end = DROP_ELEMENT_MODEL_TYPE_SPAN
        expected_model_type = _model_type_for_item(drop.item_id)
        if pc[base + model_start:base + model_end] != struct.pack(
                "<H", expected_model_type):
            raise MobLootContractError(
                REFUSE_COMPOSED_BYTES_OFF_PIN,
                "element %d's composed model type does not match "
                "field_drop_tables.ITEMS[item_id][3]" % index)
    return pc


def drop_pc(legacy: Any, drop: Any) -> bytes:
    """The single-element RuntimeRes pc that carries one ground drop.

    Kept, and kept pinned to 44 bytes, because that is the pc GT-045 put in
    front of a real client.  A one-drop kill still composes exactly these
    bytes after the round-``zxnwtd`` change, and this function is where that
    is asserted rather than assumed.
    """
    pc = drop_collection_pc(legacy, (drop,))
    if len(pc) != DROP_PC_SIZE:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "a one-element ground pc is %d bytes, composed %d"
            % (DROP_PC_SIZE, len(pc)))
    if pc[:DROP_ENVELOPE_SIZE] != DROP_ENVELOPE_PIN:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the composed envelope is not the pinned envelope; the legacy "
            "serializer moved under this lane and it refuses to emit")
    return pc


def drop_pc_with_model_type(legacy: Any, drop: Any) -> bytes:
    """The single-element mask-0x16 pc: :func:`drop_pc`'s bytes plus the
    model-type field.  [DERIVED, not yet client-measured] -- unlike
    ``drop_pc``, nothing here is pinned to bytes GT-045 or any other
    attended round put in front of a real client; only the arithmetic
    (:data:`DROP_PC_SIZE_WITH_MODEL_TYPE`) is asserted.
    """
    pc = drop_collection_pc_with_model_type(legacy, (drop,))
    if len(pc) != DROP_PC_SIZE_WITH_MODEL_TYPE:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "a one-element wide ground pc is %d bytes, composed %d"
            % (DROP_PC_SIZE_WITH_MODEL_TYPE, len(pc)))
    if pc[:DROP_ENVELOPE_SIZE] != DROP_ENVELOPE_PIN:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the composed envelope is not the pinned envelope; the legacy "
            "serializer moved under this lane and it refuses to emit")
    return pc


def _snappy_raw_literal_via_struct(data: bytes) -> bytes:
    """The snappy raw-literal body for ``data``, recomposed here.

    ~~"NOT a second reading of the legacy module: written from the snappy
    format's own description"~~ IS STRUCK IN THE ROUND THAT WROTE IT
    (``zxnwtd``, pf-adversary D7).  Whatever it was written from, WHAT IT
    IS is a transcription of ``pf_login_game_server_v141.snappy_raw_literal``
    -- expression for expression, including that encoder's idiosyncratic
    ``(59 + width) << 2`` rendering of the extended literal tag and its
    ``length <= 60`` form of the boundary.  Calling it an independent
    derivation was a claim about the artifact, and the artifact says
    otherwise.

    So what it is actually for, and this is the whole of it: the composed
    frame stops matching the moment a shim swaps the compressor, moves the
    length field, or reframes the message -- because then the legacy path
    stops producing THIS text's output.  It cannot catch an error this text
    and the legacy encoder share, because they are the same text.  Only the
    ONE-element frame is checked against literal bytes a real client took
    (``DROP_FRAME_HEADER_PIN``, GT-045).

    ROUND ewm6ff -- THIS TRANSCRIPTION WAS ONE LOOP SHORT, and said so about
    itself without noticing: the legacy encoder walks ``data`` in 65536-byte
    CHUNKS and opens a fresh literal tag for each (v141:563-574), and this text
    emitted a single tag for the whole buffer.  Identical output below 65536
    bytes, which is why every existing caller (drop frames, bounded far below
    that by ``REFUSE_GENERATION_TOO_WIDE_TO_FRAME``) never saw it -- and a
    silent divergence above it, where this text would have called the legacy
    framing layer wrong.  Found by the first pc that crossed the boundary.
    """
    out = bytearray()
    value = len(data)
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    position = 0
    while position < len(data):
        chunk = data[position:position + SNAPPY_LITERAL_CHUNK]
        minus_one = len(chunk) - 1
        if len(chunk) <= 60:
            out.append(minus_one << 2)
        else:
            width = max(1, (minus_one.bit_length() + 7) // 8)
            out.append((59 + width) << 2)
            out += minus_one.to_bytes(width, "little")
        out += chunk
        position += len(chunk)
    return bytes(out)


def _frame_via_struct(pc: bytes) -> bytes:
    """The framed message, re-composed from the pinned magic and the format."""
    body = _snappy_raw_literal_via_struct(pc)
    return DROP_FRAME_MAGIC_PIN + struct.pack("<I", len(body)) + body


def drop_frames(legacy: Any, drops: Any) -> tuple:
    """ONE framed generation carrying every drop of that kill, in ledger order.

    ~~"One framed single-element message per drop"~~ IS STRUCK (round
    ``zxnwtd``, ``RE-130`` DONE/PASS): N nonempty single-element generations
    do not leave N drops on the ground -- each one erases the keys the next
    one omits.  See :func:`drop_collection_pc` for the spans and for the
    three things this change does NOT claim.

    The return type is unchanged on purpose -- a tuple of ``(pc, frame)``
    pairs -- so ~~the call site in ``runtime.py:4292``, which is chief's
    file and not this lane's to edit, keeps working unread: it iterates,
    and now it iterates once~~ IS STRUCK, ROUND KA1B-DROPMODEL FOLLOW-UP,
    2026-09-01, PF-ADVERSARY: ``runtime.py:4292`` is unrelated
    ``mob_combat_membership`` code as of this round, and this function is
    no longer what ``runtime.py`` calls at all (see below).  Any caller of
    THIS function still gets that iterate-once contract unread; it simply
    is not the one on the live dispatch path any more.

    ROUND KA1B-DROPMODEL, DELIBERATELY UNCHANGED HERE.  A sibling,
    :func:`drop_frames_with_model_type`, composes the mask-0x16 element
    (mask-0x12 plus [DERIVED, not yet client-measured] ``n_DROPMODEL_TYPE``)
    and is gated by :data:`DROP_MODEL_TYPE_FIELD_ENABLED` (True).  THIS
    function does not read that flag and still composes ONLY the mask-0x12
    shape: the ONE-drop bytes below are GT-045's own measured 44/54, pinned
    not only in this file's tests but in tests/test_ground_drop_multi_
    drop_emission_shape.py and tests/test_mob_drop_presence*.py, none of
    which this round touched -- and none of which calls THIS function
    (``drop_frames``) any differently than before; this function's own
    output is untouched by this round.
    ~~The one-line swap that would make the wide mask THIS function's
    default (which is what would make it runtime.py's default, since that
    file calls this name) is this round's CORE-REQUEST, not a change made
    unilaterally here~~ IS STRUCK, ROUND KA1B-DROPMODEL FOLLOW-UP,
    2026-09-01, PF-ADVERSARY: the premise -- that ``runtime.py`` calls THIS
    function -- was already wrong when it was written (CORE-REQUEST 2246 /
    COO-DECISION 2026-08-29T23:42 had rewired ``runtime.py`` through
    ``mob_drop_presence.sustain_a_kill`` -> :func:`refresh_frames` two days
    earlier).  :func:`refresh_frames` lives in this same file, so making
    IT default to the wide mask needed no CORE-REQUEST; this round did
    that (see :func:`refresh_frames`).  Nothing about ``drop_frames``
    itself changed: it is still called directly by this file's tests, by
    :func:`drop_frames_with_model_type` when :data:`DROP_MODEL_TYPE_FIELD_
    ENABLED` is False, and by nothing else, and it still composes only the
    proven mask-0x12 shape, byte for byte, forever.
    """
    rows = tuple(drops)
    if not rows:
        return ()
    # THE ONE-DROP CASE GOES THROUGH ``drop_pc``, ON THE EMISSION PATH.
    # pf-adversary D2: the first version of this function called
    # ``drop_collection_pc`` for every width, which left ``drop_pc``
    # reachable only from ``pin_document`` and the tests -- while three
    # shipped artifacts said "drop_pc asserts it on every emission".  That
    # sentence is now true because the code was changed to match it, not
    # because the sentence was softened.
    if len(rows) == 1:
        pc = drop_pc(legacy, rows[0])
    else:
        pc = drop_collection_pc(legacy, rows)
    frame = legacy.frame_pc(pc)
    # THE PINS FIRST, THE RE-DERIVATION LAST, AND THAT ORDER IS DELIBERATE.
    # Every one of these refusals has to stay reachable (this module's own
    # rule: a refusal that cannot happen is a lie to whoever counts them).
    # pf-adversary D2 measured what the first version of this order cost:
    # ``_frame_via_struct`` FORCES length 54 and the pinned ten-byte header
    # for any 44-byte pc, so comparing against it first made all three
    # GT-045 frame pins tautologies -- deleting them left the suite green.
    # They are now in front of it, where they can still fail.
    header_size = len(frame) - len(pc)
    if len(rows) == 1:
        # The GT-045 pins, load-bearing for the shape a real client has
        # actually taken.  A one-drop kill must still be these exact bytes.
        if len(frame) != DROP_FRAME_SIZE:
            raise MobLootContractError(
                REFUSE_COMPOSED_BYTES_OFF_PIN,
                "a framed one-element ground message is %d bytes, composed %d"
                % (DROP_FRAME_SIZE, len(frame)))
        if frame[:DROP_FRAME_HEADER_SIZE] != DROP_FRAME_HEADER_PIN:
            raise MobLootContractError(
                REFUSE_COMPOSED_BYTES_OFF_PIN,
                "the frame header is not the pinned header; the framing layer "
                "moved under this lane and it refuses to emit")
        if header_size != DROP_FRAME_COORD_SHIFT:
            raise MobLootContractError(
                REFUSE_COMPOSED_BYTES_OFF_PIN,
                "the one-element frame header is %d bytes, not the pinned %d"
                % (header_size, DROP_FRAME_COORD_SHIFT))
    if frame[:len(DROP_FRAME_MAGIC_PIN)] != DROP_FRAME_MAGIC_PIN:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the frame magic is not the pinned magic; the framing layer "
            "moved under this lane and it refuses to emit")
    if len(frame) < 8 or struct.unpack("<I", frame[4:8])[0] != len(frame) - 8:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the frame's own length field does not describe the frame")
    if frame[header_size:] != pc:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the framed body is not the pc that was composed")
    recomposed = _frame_via_struct(pc)
    if frame != recomposed:
        raise MobLootContractError(
            REFUSE_FRAME_ENCODER_DISAGREES,
            "the legacy framing layer and the pinned frame format disagree; "
            "this lane refuses to emit a frame shape no client has accepted")
    for index, drop in enumerate(rows):
        base = header_size + DROP_ENVELOPE_SIZE + index * DROP_ELEMENT_SIZE
        shifted = b"".join(
            frame[base + start:base + end]
            for start, end in DROP_ELEMENT_COORD_SPANS
        )
        if shifted != struct.pack("<fff", drop.x, drop.y, drop.z):
            raise MobLootContractError(
                REFUSE_COMPOSED_BYTES_OFF_PIN,
                "element %d's framed coordinates are not that drop's "
                "coordinates" % index)
    return ((pc, frame),)


def drop_frames_with_model_type(legacy: Any, drops: Any) -> tuple:
    """mask-0x16 sibling of :func:`drop_frames`.  NO SCENARIO ID, NO DISPATCH
    KWARG, NO CLI FLAG -- this is production code the same way every other
    function in this module is; :data:`DROP_MODEL_TYPE_FIELD_ENABLED` gates
    only whether a CALLER of THIS function is expected to prefer it, not
    whether the function itself is reachable.

    [DERIVED, not yet client-measured].  Composes the same generation/frame
    STRUCTURE :func:`drop_frames` does -- one envelope, N wide elements, the
    RE-130 replace-by-omission rules unchanged -- with every element
    carrying ``n_DROPMODEL_TYPE`` alongside the fields GT-045 already put on
    a real client's wire.  Unlike ``drop_frames``, the ONE-drop case here is
    NOT checked against a hand-typed literal frame-header pin the way
    :data:`DROP_FRAME_HEADER_PIN` checks the narrow shape: nothing has
    measured those bytes, and typing a fake "pin" for an unmeasured shape
    would be exactly the kind of invented row this project's rules forbid.
    What IS checked, at run time, on every call: the envelope pin (which the
    wide element does not change), the frame magic, the frame's own length
    field, the two framing encoders agreeing, and -- per element -- both the
    coordinates and the model-type value against
    ``field_drop_tables.ITEMS[item_id][3]``.

    ~~NOT WIRED INTO ``runtime.py``.  See :func:`drop_frames`'s own
    docstring for why, and this round's CORE-REQUEST for the one-line swap
    that would change that~~ IS STRUCK, ROUND KA1B-DROPMODEL FOLLOW-UP,
    2026-09-01, PF-ADVERSARY: as of this round it IS reached from
    ``runtime.py`` -- indirectly, the way every function in this module is
    -- via ``mob_drop_presence.sustain_a_kill`` -> :func:`refresh_frames`,
    which now calls THIS function instead of :func:`drop_frames`.  See
    :func:`refresh_frames`'s own docstring and NONCLAIM 23 for the chain
    and the rollback.

    :data:`DROP_MODEL_TYPE_FIELD_ENABLED` IS READ HERE, not only documented:
    a caller who flips it to False gets exactly :func:`drop_frames`'s own
    proven mask-0x12 bytes back, with no other code change -- which is what
    makes "leave this False" a real rollback lever and not a comment nobody
    checks.
    """
    if not DROP_MODEL_TYPE_FIELD_ENABLED:
        return drop_frames(legacy, drops)
    rows = tuple(drops)
    if not rows:
        return ()
    if len(rows) == 1:
        pc = drop_pc_with_model_type(legacy, rows[0])
    else:
        pc = drop_collection_pc_with_model_type(legacy, rows)
    frame = legacy.frame_pc(pc)
    header_size = len(frame) - len(pc)
    if frame[:len(DROP_FRAME_MAGIC_PIN)] != DROP_FRAME_MAGIC_PIN:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the frame magic is not the pinned magic; the framing layer "
            "moved under this lane and it refuses to emit")
    if len(frame) < 8 or struct.unpack("<I", frame[4:8])[0] != len(frame) - 8:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the frame's own length field does not describe the frame")
    if frame[header_size:] != pc:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the framed body is not the pc that was composed")
    recomposed = _frame_via_struct(pc)
    if frame != recomposed:
        raise MobLootContractError(
            REFUSE_FRAME_ENCODER_DISAGREES,
            "the legacy framing layer and the pinned frame format disagree; "
            "this lane refuses to emit a frame shape it cannot check")
    for index, drop in enumerate(rows):
        base = (
            header_size + DROP_ENVELOPE_SIZE
            + index * DROP_ELEMENT_SIZE_WITH_MODEL_TYPE)
        shifted = b"".join(
            frame[base + start:base + end]
            for start, end in DROP_ELEMENT_COORD_SPANS_WITH_MODEL_TYPE
        )
        if shifted != struct.pack("<fff", drop.x, drop.y, drop.z):
            raise MobLootContractError(
                REFUSE_COMPOSED_BYTES_OFF_PIN,
                "element %d's framed coordinates are not that drop's "
                "coordinates" % index)
        model_start, model_end = DROP_ELEMENT_MODEL_TYPE_SPAN
        expected_model_type = _model_type_for_item(drop.item_id)
        if frame[base + model_start:base + model_end] != struct.pack(
                "<H", expected_model_type):
            raise MobLootContractError(
                REFUSE_COMPOSED_BYTES_OFF_PIN,
                "element %d's framed model type does not match "
                "field_drop_tables.ITEMS[item_id][3]" % index)
    if len(rows) == 1:
        if len(pc) != DROP_PC_SIZE_WITH_MODEL_TYPE:
            raise MobLootContractError(
                REFUSE_COMPOSED_BYTES_OFF_PIN,
                "a one-element wide ground pc is %d bytes, composed %d"
                % (DROP_PC_SIZE_WITH_MODEL_TYPE, len(pc)))
        if len(frame) != DROP_FRAME_SIZE_WITH_MODEL_TYPE:
            raise MobLootContractError(
                REFUSE_COMPOSED_BYTES_OFF_PIN,
                "a framed one-element wide ground message is %d bytes, "
                "composed %d" % (DROP_FRAME_SIZE_WITH_MODEL_TYPE, len(frame)))
    return ((pc, frame),)


def refresh_frames(legacy: Any, ledger: Any) -> tuple:
    """Re-emit every live row.  AN EXPERIMENT, NOT A BEHAVIOUR.

    ~~"The measured lifetime of a ground object is 0.633 s"~~ IS STRUCK: there
    is no object, and 0.633 is an ORIGINAL-SERVER clip whose interval ended
    because somebody picked the item up.  What was measured of THIS pipe is a
    label that lives 0.2-0.4 s.  Re-emission is the only lever this lane has
    toward "it stays", and whether it redraws the label, does nothing, or
    restarts the dust is UNMEASURED (NONCLAIM 12).  ``DROP_REFRESH_MS`` is
    arithmetic from the measured numbers, not a tuned or tested value, and the
    arithmetic says the honest cadence is expensive.

    AFTER ``RE-130`` THIS IS ALSO THE ONLY FUNCTION HERE THAT COMPOSES THE
    CROSS-KILL-CORRECT GENERATION: the whole live ledger in one collection is
    exactly the shape that does not erase an earlier kill's keys (NONCLAIM
    20).  That does not make it a behaviour -- the refusal below still
    stands, and the reason it stands is the cadence, not the shape.

    AND THE COO HAS SINCE REFUSED IT FOR PRODUCTION (2026-08-26 07:45 +07:00).
    This function may be called by hand, by a test, or by an attended
    experiment.  It may NOT be put on a timer in ``runtime.py``: the shipped
    behaviour is one announcement per drop -- once each, never re-announced,
    a cadence rule -- until the label's lifetime is measured from real play.
    ON A TIMER is the refused part.  Once per kill, carrying the live
    ledger, is a different proposal and is written up as WIRING step 4b.

    WIRING STEP 4b WAS TAKEN: since CORE-REQUEST 2246 (COO-DECISION
    2026-08-29T23:42), ``runtime.py:4921-4922`` calls
    ``mob_drop_presence.sustain_a_kill`` unconditionally on every
    server-computed mob death, and that function calls THIS one once per
    kill (never on a timer -- the refused part above is unaffected).  That
    is proven by ``tests/test_mob_drop_presence_wiring.py``.  So this
    function is not only "may be called by hand" any more: it is the real
    production dispatch path's composer.

    ROUND KA1B-DROPMODEL FOLLOW-UP, 2026-09-01.  [ASSUMPTION OF LANE B -
    awaiting COO confirmation]  Because this function is that composer AND
    it lives in this file (not in ``runtime.py``/``app.py``/
    ``pf_login_game_server_v141.py``, the only files this lane may not
    edit), this round changed its body to call
    :func:`drop_frames_with_model_type` instead of :func:`drop_frames`.
    :func:`drop_frames_with_model_type` still reads
    :data:`DROP_MODEL_TYPE_FIELD_ENABLED` itself (True by default), so this
    function does not duplicate that flag check -- it simply defers to it.
    The practical effect: every real kill's production announcement is now
    the WIDE mask-0x16 element (mask-0x12 plus [DERIVED, not yet
    client-measured] ``n_DROPMODEL_TYPE``), not the narrow mask-0x12 shape
    GT-045 measured.  NONE OF THIS IS MEASURED CLIENT-SIDE -- see NONCLAIM
    23 for the full chain and citations.  Rollback if the assumption is
    wrong: set :data:`DROP_MODEL_TYPE_FIELD_ENABLED` = False --
    :func:`drop_frames_with_model_type` then returns :func:`drop_frames`'s
    own output verbatim, so this function (and the production dispatch
    path behind it) goes straight back to the exact narrow bytes GT-045
    measured, with no other code change.
    """
    if type(ledger) is not DropLedger:
        raise MobLootContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "ledger must be a typed DropLedger")
    return drop_frames_with_model_type(legacy, ledger.drops)


# ---------------------------------------------------------------------------
# HEARTBEAT-PRESERVE-001.  ~~CORE-REQUEST answer, not yet wired anywhere.~~
# IS STRUCK -- wired, TO THE LEVEL CHIEF'S OWN REPLY CERTIFIES, NOT FURTHER
# (pf-adversary, this round: the first draft of this correction said flatly
# "it is done" and named only GT-188 as open, which overclaimed by dropping
# this same reply's own third hedge -- restored below).  ``app.py``'s
# ``install_ground_heartbeat_preserve(legacy)`` (called unconditionally from
# that module's ``main()``, line 890 as of this round) installs a
# caller-frame-checked wrapper around ``legacy.make_runtime_res_empty_exact``
# that substitutes ``preserve_ground_heartbeat_frame`` (this module, below)
# only when the caller is ``heartbeat_worker`` -- see chief's reply,
# pf_bridge notes_to_chief/consumed/20260901_0507_CHIEF-REPLY-CORE-REQUEST-
# heartbeat-preserve-wired.md.  This lane composed the bytes and named the
# fix (below); wiring them into the running server was chief's job per
# COO-DECISION 20260901_0347, and the source-level wiring is done.  That
# same reply names THREE things still open, not one -- carried forward here
# in full, not just the one this lane happens to be closest to:
# (1) whether Codex's client-image reading of the reconciler is itself
# correct; (2) the attended proof (``GT-188``, pf_bridge
# GAME_TEST_QUEUE.md) that a drop label actually survives past one
# heartbeat tick on a real client; (3) THERE IS NO BOOT-LEVEL TEST OF
# ``app.py`` IN THIS REPO -- the reply's own words, confirmed by search, not
# assumed.  What IS confirmed, and no further: a source-order assertion
# (``tests/test_foundation_legacy_seam.py``'s
# ``test_app_installs_the_ground_heartbeat_patch_before_adapting_the_listener``,
# comparing string offsets, not runtime order) and a unit test that drives
# the wrapper through a locally-defined stand-in function also named
# ``heartbeat_worker`` (that file's
# ``test_ground_heartbeat_patch_only_changes_the_heartbeat_worker_caller``),
# not the real v141 thread through an actual server boot.  This lane has
# run none of (1)-(3) and owns none of the channels that would.
#
# Codex static RE (pf_bridge notes_to_chief/CODEX_URGENT_20260901_0324_DROP_
# HEARTBEAT_CLEARS_SET.md) found that ``pf_login_game_server_v141.py``'s
# clock-driven transport heartbeat -- sent every ~2 s by every accepted GAME
# session, independent of any action batch -- calls
# ``make_runtime_res_empty_exact()``, whose body sets BOTH derived-mask bytes
# to ``0x00`` (``u8tag(0x0B, 0)`` twice): the inherited VitalData list AND the
# ground-object (``0x08``) list are both marked ABSENT.  Per the image
# evidence in that letter, an absent 0x08 list means a NULL
# ``TerrainThingPool`` pointer reaches the client reconciler
# (``0x006AF970``), and a NULL pool is read as "clear everything", not "no
# change" -- so this heartbeat erases every ground drop roughly every two
# seconds, regardless of whether ``sustain_a_kill`` (this module, via
# :mod:`mob_drop_presence`) just carried a live ledger onto the wire in the
# SAME session.
#
# ``current/pf_login_game_server_v141.py`` is frozen (COO-DECISION
# 2026-08-29T03:45); COO-DECISION 20260901_0347 (pf_bridge notes_to_chief/)
# ruled the fix must land at a live producer, not at v141, and named the
# exact shape: every RuntimeRes sent while the ground still needs
# preserving must carry a non-NULL pool -- present-count 0 when nothing new
# needs reconciling (PRESERVE, not CLEAR), present-count > 0 with the full
# live set when something does (RECONCILE, what ``refresh_frames`` already
# builds).  This function is the PRESERVE half: same envelope shape
# ``drop_collection_pc`` already composes, ground-list mask 0x08 PRESENT,
# count = 0, zero elements.  It is NOT ``drop_collection_pc(legacy, ())`` --
# that call refuses on purpose (``REFUSE_GENERATION_IS_EMPTY``, RE-130: an
# empty GENERATION is meaningless because nothing dropped) -- this is a
# different wire shape for a different situation: a heartbeat that has
# nothing new to reconcile and must say so without also saying "nothing is
# on the ground".
#
# WHAT THIS FUNCTION DOES NOT DO.  It does not read a ``DropLedgerCell``, a
# session, or any live state -- the PRESERVE body never varies, so nothing
# here needs to.  It does not touch v141, ``runtime.py``, ``app.py``, or the
# heartbeat call site: composing the bytes and WIRING them in are two
# different jobs, and COO-DECISION 20260901_0347 assigned only the first one
# to this lane (find the producer, name the exact fix; chief wires it).  See
# ``notes_to_chief/`` (bridge) for the CORE-REQUEST this function answers.
# ---------------------------------------------------------------------------
PRESERVE_GROUND_HEARTBEAT_PC_SIZE = DROP_ENVELOPE_SIZE   # 17: envelope, no elements
PRESERVE_GROUND_HEARTBEAT_FRAME_SIZE = 27                # measured, pinned below


def preserve_ground_heartbeat_pc(legacy: Any) -> bytes:
    """The PRESERVE heartbeat body: pool present (mask 0x08), count = 0.

    Composed the same way every other pc in this module is -- via the legacy
    tag primitives, then checked against the pin -- so a moved serializer
    fails this function instead of shipping silently different bytes.
    """
    pc = bytearray()
    pc += legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_RES)
    pc += legacy.u32tag(0x14, 0)
    pc += legacy.u8tag(0x08, ENVELOPE_VERSION)
    pc += legacy.u8tag(0x0B, 0)                                # inherited none
    pc += legacy.u8tag(0x0B, RUNTIME_DERIVED_BIT_GROUND_LIST)  # derived 0x08 PRESENT
    pc += legacy.u16tag(ELEMENT_LIST_COUNT_TAG, 0)             # count = 0: preserve
    pc = bytes(pc)
    expected = DROP_ENVELOPE_CONSTANT_PIN + legacy.u16tag(ELEMENT_LIST_COUNT_TAG, 0)
    if pc != expected:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the preserve-heartbeat envelope is not the pinned envelope; the "
            "legacy serializer moved under this lane and it refuses to emit")
    if len(pc) != PRESERVE_GROUND_HEARTBEAT_PC_SIZE:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the preserve-heartbeat pc is %d bytes, composed %d"
            % (PRESERVE_GROUND_HEARTBEAT_PC_SIZE, len(pc)))
    return pc


def preserve_ground_heartbeat_frame(legacy: Any) -> tuple[bytes, bytes]:
    """``(pc, frame)`` for the PRESERVE heartbeat -- same shape ``legacy.
    make_runtime_res_empty_exact()`` returns, so a call site can swap the two
    without changing anything else.  ``frame`` is composed via ``legacy.
    frame_pc``, the same framing entry point every other emitter in this
    module uses, and checked against a byte pin so a moved framing layer
    fails here rather than at a live socket.
    """
    pc = preserve_ground_heartbeat_pc(legacy)
    frame = legacy.frame_pc(pc)
    if len(frame) != PRESERVE_GROUND_HEARTBEAT_FRAME_SIZE:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the preserve-heartbeat frame is %d bytes, composed %d"
            % (PRESERVE_GROUND_HEARTBEAT_FRAME_SIZE, len(frame)))
    if frame[:len(DROP_FRAME_MAGIC_PIN)] != DROP_FRAME_MAGIC_PIN:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the preserve-heartbeat frame magic is not the pinned magic")
    if frame[len(frame) - len(pc):] != pc:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the framed body is not the pc that was composed")
    return pc, frame


# ---------------------------------------------------------------------------
# THE OTHER RUNTIMERES FRAMES -- THE ONES app.py's PRESERVE PATCH NEVER SEES.
#
# app.py's install_ground_heartbeat_preserve substitutes the PRESERVE body for
# exactly one caller: the frame whose co_name is "heartbeat_worker"
# (app.py:128).  v141's make_runtime_vitals (line 689) -- which composes the
# RuntimeRes carrying VitalData responses -- ends its body with
# ``pc += u8tag(0x0B, 0)`` (line 710), an EMPTY derived change mask, and never
# reaches that wrapper.  Bit 0x08 clear means the ground list is absent.
#
# WHAT IS MEASURED, WHAT IS RELAYED, AND WHAT IS THIS LANE GUESSING.  Stated
# separately because a previous draft of this section ran the three together.
#
#   MEASURED, from our own source: make_runtime_vitals ends on an empty derived
#   mask.  tests/test_mob_loot_preserve_runtime_res.py re-derives the census of
#   v141's RuntimeRes composers from that file's AST and goes red when one is
#   added, renamed, or changes a mask.  That test also records what its own
#   detector CANNOT see -- it is a census of the composers that write the tag
#   in one recognisable spelling, not a proof that no other exists.
#
#   RELAYED, NOT RULED.  COO-DECISION 20260901_0347's operative text tells THIS
#   LANE to write a CORE-REQUEST naming exact lines "per Codex's proposal --
#   pool must always be non-NULL, count=0 when only preserving".  That is the
#   COO relaying Codex's proposal for this lane to specify, NOT a ruling this
#   function may cite as settled.  An earlier draft of this comment promoted it
#   to "the rule COO already wrote" and then leaned on that promotion as the
#   part that was not an assumption.  It is withdrawn: pf-adversary, round
#   ewm6ff, finding D6(b).
#
#   [ASSUMPTION OF LANE B - AWAITING COO] that an absent ground list means a
#   NULL TerrainThingPool reaches the reconciler at 0x006AF970 and is read as
#   "clear everything" (Codex, pf_bridge notes_to_chief/CODEX_URGENT_20260901_
#   0324).  That reading does not mention the inherited mask, so applying it to
#   a mask-0x02 frame is this lane's inference.  MOB_LOOT_NONCLAIMS entry 18
#   stands unchanged: what a RuntimeRes carrying a DIFFERENT derived mask does
#   to a live ground entry is UNMEASURED.
#
#   THE SHAPE THIS COMPOSES HAS NEVER BEEN SEEN ON ANY WIRE.  The same ka1-B
#   table this section was written from (pf_bridge notes_to_chief/20260901_
#   2210_KA1B-TO-LANE-B-drop-lane-three-gaps-including-distance-prune.md, point
#   2) reads: pool bit 0x08 absent 14,536 - PRESENT-COUNT-ZERO 0 -
#   present-nonempty 23 - unresolved 729.  Present-count-zero is the exact
#   shape below, and its count in that 15,288-frame corpus is ZERO.  An earlier
#   draft of this comment quoted the columns that motivated the change and
#   omitted the one beside them saying the OUTPUT has never been observed
#   (pf-adversary, round ewm6ff, finding D6(a)).  It is quoted here instead.
#   That corpus also does not prove which server produced it -- the letter
#   nonclaims that itself -- which is why the motivating fact above was
#   re-derived from v141 rather than taken from the count.
#
# WHY THIS TAKES THE VITALS, NOT A COMPOSED pc.  The first draft of this
# section took an already-composed pc and rewrote its last two bytes when they
# were 0B 00.  pf-adversary refuted that (round ewm6ff, finding D1) by
# MEASUREMENT, not argument: make_runtime_vital (SINGULAR, v141:747) appends no
# derived mask at all -- the census below records it as writing (2, "caller") --
# so the last two bytes of its pc are whatever the caller's payload ends with.
# A u32tag(0x14, v) for any v in [720896, 786431] ends in 0B 00.  So does a
# wstring whose final UTF-16LE code unit is U+000B.  The adversary drove
# legacy_bridge.LegacyProjector.character_list -- a real login-path composer,
# session.py:50 and :281 -- through the old function and watched a u32 field go
# from 0x000B0000 to 0x080B0000 with no refusal raised.  Three real composers
# on this server's login path end in 0B 00 for at least two different reasons.
#
# There is no repair for that at the END of the buffer, so this function does
# not look there.  It calls the composer itself and RE-DERIVES the same body
# from the legacy tag primitives, exactly the dual-derivation discipline
# drop_element and _frame_via_struct already use in this module: if the two
# agree, the record this replaces is the derived mask BY CONSTRUCTION, because
# this lane just built the bytes in front of it.  If they disagree the
# composer moved and this refuses.  A caller cannot hand it a pc whose shape
# nobody can vouch for, because it does not accept a pc.
#
# WHAT THIS IS NOT: A WRAPPER FOR make_runtime_vitals.  MOB_LOOT_WIRING step 7
# once asked app.py to wrap that composer globally.  That ask was REFUTED by
# measurement in the same review (finding D2) and is withdrawn: mob_pickup.py's
# bag_delta_pc (:1786) and delete_refresh_hypothesis.py's rebuild response
# (:347) both re-derive their own pc through make_runtime_vitals and compare it
# byte for byte against a pin, so a blanket wrap makes EVERY PICKUP REFUSE
# while a drop is on the ground -- the exact state this lane exists to create --
# and kills the post-delete character-list rebuild.  Nine other modules call
# that composer with pins of their own.  This is therefore an OPT-IN composer a
# call site chooses instead of make_runtime_vitals, one site at a time, each
# site audited on its own; see MOB_LOOT_WIRING step 7 for the ask that replaced
# the withdrawn one.
# ---------------------------------------------------------------------------
# What v141 appends last, and what this composes in its place.  Both are
# re-derived from the legacy primitives on every call and compared with these
# literals, so a moved serializer refuses here instead of shipping bytes no
# client has accepted.
RUNTIME_RES_HEAD_PIN = DROP_ENVELOPE_PIN[:10]
RUNTIME_RES_INHERITED_MASK_VITALS = 0x02
RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN = bytes((0x0B, 0x00))
RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN = bytes((0x0B, 0x08, 0x12, 0x00, 0x00))

# ---------------------------------------------------------------------------
# THE SECOND CARRIER, ROUND jysbar (COO-DECISION 2026-09-02T10:44+07:00,
# items 3 and 4).
#
# ``make_runtime_remote_actors`` (v141:1267-1288) is the OTHER RuntimeRes
# composer this lane's frames ride: the bar refresh, the dying frame and the
# dead frame.  Measured through this repo's own headless dispatcher, all three
# write the derived change mask as ``0B 02`` -- the ground-list bit CLEAR --
# and clear means "there is no pool", which the client's reconciler is read
# (Codex, static) as treating like "clear everything".  So the announce frame
# that opted in to PRESERVE last round has its work undone 0.0 s later by the
# bar, and a kill's drop has its work undone 0.7 s later by the dead frame.
# The measurement is pinned in ``tests/test_mob_combat_dispatch.py`` here,
# and written up in the round file of the OTHER repository (pf_bridge
# rounds/B_20260902_1144_jysbar_*): this repo has no rounds/ directory, so a
# citation to "the round file" alone would point at nothing.
#
# THE SHAPE IS NOT ITS SIBLING'S, AND THAT IS THE WHOLE DIFFICULTY.  In
# ``make_runtime_vitals`` the derived mask is the LAST record, so PRESERVE is
# an appended tail and every byte before it is v141's own.  Here the derived
# mask sits BEFORE the actor collection (offset 12, the record that says which
# derived fields follow), so preserving the ground list means
#   * one byte of v141's output changes: ``0x02`` -> ``0x02 | 0x08``, and
#   * one record is appended after the actor collection: the ground list,
#     present and empty.
# Everything else is compared byte for byte against what v141 itself composed
# for the same entries, and any other difference refuses.  ``mob_loot``'s
# fourth struck refusal from round ewm6ff said this in the negative: "a real
# actor pc does not end at its mask".
#
# WHY THE APPENDED RECORD IS ``12 00 00`` AND WHY THAT IS NOT A GUESS.  It is
# the same three bytes ``preserve_ground_heartbeat_pc`` composes after its own
# ``0B 08``, and that body has been on the production wire on every flagless
# boot, roughly every two seconds, since ``app.py``'s
# ``install_ground_heartbeat_preserve`` landed.  This function derives the
# record through the same primitive and pins it against that composer's, so
# the heartbeat cannot change its final field without this refusing.
#
# WHAT THAT CROSS-PIN IS *NOT* (pf-adversary, round jysbar, rank 6): it is not
# independent corroboration that these three bytes ARE a ground list.  ``12 00
# 00`` is the generic encoding of "u16 field, value 0" and is byte-identical
# to a zero actor count; the two records are told apart by POSITION alone.  So
# the byte identity with the heartbeat is real and worth pinning, and it is
# the SAME assumption restated rather than a second piece of evidence for it.
#
# [ASSUMPTION OF LANE B - AWAITING COO/RE CONFIRMATION] that with BOTH bits
# set the client reads the actor collection FIRST and the ground list SECOND.
# The serializer chain in the composer's own docstring puts the actor stream at
# object +0x1C and this module's own constant comment puts the ground list at
# +0x20, so ascending field order is what the shape assumes.  What IS measured
# is each field alone: the actor collection alone in every census this server
# has ever sent, and the ground list alone in the heartbeat above.  The two
# together have never been on a wire.  A frame the client rejects here costs
# the actors in THAT frame, which is why the wrapper in ``mob_combat`` falls
# back to v141's own bytes and why COO-DECISION 0646/1044 keeps this out of
# the arrival census until an attended round has seen one accepted.
# ---------------------------------------------------------------------------
#: The derived mask v141 writes for an actor collection, and the one this lane
#: writes in its place.  Neither is a tail: both live at offset 12.
RUNTIME_RES_ACTORS_DERIVED_MASK = 0x02
RUNTIME_RES_ACTORS_PRESERVE_DERIVED_MASK = (
    RUNTIME_RES_ACTORS_DERIVED_MASK | RUNTIME_DERIVED_BIT_GROUND_LIST)
#: Where that record sits: u16tag class id (3) + u32tag key (5) + u8tag
#: version (2) + u8tag inherited mask (2).  ``world_population.
#: WIRE_HEADER_BYTES`` counts the same envelope through to the actor count.
RUNTIME_RES_ACTORS_DERIVED_MASK_OFFSET = 12
#: The ground list, present and empty, as the heartbeat has been sending it.
RUNTIME_RES_GROUND_PRESENT_EMPTY_PIN = bytes((0x12, 0x00, 0x00))


def _runtime_remote_actors_body(
        legacy: Any, entries: tuple, derived_mask: int) -> bytes:
    """Everything ``make_runtime_remote_actors`` composes, mask parameterised.

    Re-derived from the legacy tag primitives for the same reason its vitals
    sibling is: the point is to be able to say WHERE the derived mask is
    without reading the end of a buffer and hoping.
    """
    pc = bytearray()
    pc += legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_RES)
    pc += legacy.u32tag(ELEMENT_KEY_TAG, 0)
    pc += legacy.u8tag(0x08, ENVELOPE_VERSION)
    pc += legacy.u8tag(ELEMENT_MASK_TAG, 0)            # inherited VitalData none
    pc += legacy.u8tag(ELEMENT_MASK_TAG, derived_mask)
    pc += legacy.u16tag(ELEMENT_LIST_COUNT_TAG, len(entries))
    for entry in entries:
        pc += entry
    return bytes(pc)


def preserve_ground_in_runtime_res_remote_actors(
        legacy: Any, entries: Any) -> tuple[bytes, bytes]:
    """``(pc, frame)``: what ``make_runtime_remote_actors`` composes for these
    entries, with the ground list PRESERVED instead of absent.

    Same argument and same return shape as ``legacy.make_runtime_remote_
    actors``, so a call site swaps one for the other and changes nothing else.
    Every actor entry is v141's own bytes, in v141's own order, at v141's own
    offsets; the derived-mask record says the ground list is present as well as
    the actor collection, and one empty ground-list record follows.

    Fail-closed at every exit.  The composer is DRIVEN and its output compared
    against this lane's re-derivation, so a v141 that moved refuses here
    instead of shipping bytes whose derived mask this lane can no longer
    locate -- and the comparison is not a prefix check: the whole of v141's
    output has to be present, in order, either side of the one byte that
    changes.
    """
    entries = tuple(entries)
    if len(entries) > 0xFFFF:
        raise MobLootContractError(
            REFUSE_VALUE_OUT_OF_RANGE,
            "a remote-actor collection of %d entries does not fit the u16 "
            "count v141 writes" % len(entries))
    for position, entry in enumerate(entries):
        # An entry that encodes to nothing still counts in the collection's
        # count field, and a stream tail the client cannot align on is the
        # ErrorData=28317 every wire module in this repo has paid for.
        if type(entry) is not bytes or not entry:
            raise MobLootContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "remote-actor entry %d is not a nonempty bytes" % position)
    composed, _composed_frame = legacy.make_runtime_remote_actors(list(entries))
    if composed != _runtime_remote_actors_body(
            legacy, entries, RUNTIME_RES_ACTORS_DERIVED_MASK):
        raise MobLootContractError(
            REFUSE_ACTORS_COMPOSER_MOVED,
            "make_runtime_remote_actors no longer composes this lane's "
            "re-derivation of the same entries, so where its derived mask "
            "sits in its pc is no longer provable here")
    ground = legacy.u16tag(ELEMENT_LIST_COUNT_TAG, 0)
    if ground != RUNTIME_RES_GROUND_PRESENT_EMPTY_PIN:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the present-and-empty ground list is not the pinned record the "
            "heartbeat has been sending; the legacy serializer moved under "
            "this lane and it refuses to emit")
    if ground != preserve_ground_heartbeat_pc(legacy)[-len(ground):]:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the ground record this composer appends is not the one the "
            "production heartbeat appends; the two must never drift")
    pc = _runtime_remote_actors_body(
        legacy, entries, RUNTIME_RES_ACTORS_PRESERVE_DERIVED_MASK) + ground
    # THE BYTE-FOR-BYTE COMPARISON COO-DECISION 1044 item 3 asks for, written
    # for the shape this carrier actually has: v141's output survives whole
    # except for the mask byte, and the only new bytes are at the end.
    offset = RUNTIME_RES_ACTORS_DERIVED_MASK_OFFSET
    if len(pc) != len(composed) + len(ground):
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the preserved actor pc is not v141's pc plus one ground record")
    if pc[:offset] != composed[:offset]:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the envelope before the derived mask is not v141's envelope")
    if pc[offset + 2:len(composed)] != composed[offset + 2:]:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the actor collection is not v141's actor collection byte for "
            "byte; nothing but the derived mask may move")
    if (pc[offset] != ELEMENT_MASK_TAG
            or composed[offset] != ELEMENT_MASK_TAG
            or composed[offset + 1] != RUNTIME_RES_ACTORS_DERIVED_MASK
            or pc[offset + 1] != RUNTIME_RES_ACTORS_PRESERVE_DERIVED_MASK):
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the record at the derived-mask offset is not the mask this lane "
            "sets the ground bit in")
    frame = legacy.frame_pc(pc)
    # Re-derived end to end, not spot-checked -- round ewm6ff, finding D5:
    # a magic-plus-suffix check passed a 75-byte frame with a 0xDEADBEEF
    # length past it, and refused every pc of 65534 bytes or more, which a
    # 108-actor census (20 KB today, and this carrier is the one that carries
    # them) is far closer to than any vitals frame ever gets.
    if frame != _frame_via_struct(pc):
        raise MobLootContractError(
            REFUSE_FRAME_ENCODER_DISAGREES,
            "the legacy framing layer and this module's re-derivation of it "
            "disagree about the preserved remote-actor frame")
    return pc, frame


def _runtime_vitals_body(legacy: Any, vitals: Any) -> bytes:
    """Everything make_runtime_vitals composes BEFORE its derived-mask record.

    Re-derived from the legacy tag primitives rather than sliced off the
    composer's own output -- that is the whole point: the slice is what this
    lane cannot justify, and the re-derivation is what lets it say where the
    derived mask starts without reading the end of a buffer.
    """
    pc = bytearray()
    pc += legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_RES)
    pc += legacy.u32tag(ELEMENT_KEY_TAG, 0)
    pc += legacy.u8tag(0x08, ENVELOPE_VERSION)
    pc += legacy.u8tag(ELEMENT_MASK_TAG, RUNTIME_RES_INHERITED_MASK_VITALS)
    pc += legacy.u16tag(ELEMENT_LIST_COUNT_TAG, len(vitals))
    for msg_id, vital_version, vital_payload in vitals:
        pc += legacy.u16tag(ELEMENT_LIST_COUNT_TAG, msg_id)
        pc += legacy.u8tag(ELEMENT_MASK_TAG, vital_version)
        pc += vital_payload
    return bytes(pc)


def preserve_ground_in_runtime_res_vitals(
        legacy: Any, vitals: Any) -> tuple[bytes, bytes]:
    """``(pc, frame)``: what ``make_runtime_vitals`` composes for these vitals,
    with the ground list PRESERVED instead of absent.

    Same arguments and same return shape as ``legacy.make_runtime_vitals``, so
    a call site swaps one for the other and changes nothing else.  The body is
    byte-identical to that composer's; the only difference is the last record,
    which carries the ground list PRESENT (bit 0x08) with count 0 and no
    elements -- "there is a pool and nothing new to reconcile" rather than
    "there is no pool".

    Fail-closed at every exit, and every exit is reachable by a real body: the
    composer is DRIVEN and its output compared against this lane's own
    re-derivation, so a v141 that moved refuses here instead of shipping bytes
    whose derived mask this lane can no longer locate.
    """
    vitals = tuple(vitals)
    body = _runtime_vitals_body(legacy, vitals)
    composed, _composed_frame = legacy.make_runtime_vitals(list(vitals))
    if composed != body + RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN:
        raise MobLootContractError(
            REFUSE_VITALS_COMPOSER_MOVED,
            "make_runtime_vitals no longer composes this lane's re-derivation "
            "of the same vitals followed by an empty derived mask, so where "
            "the derived mask sits in its pc is no longer provable here")
    tail = (
        legacy.u8tag(ELEMENT_MASK_TAG, RUNTIME_DERIVED_BIT_GROUND_LIST)
        + legacy.u16tag(ELEMENT_LIST_COUNT_TAG, 0)
    )
    if tail != RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the preserve derived-mask tail is not the pinned tail; the "
            "legacy serializer moved under this lane and it refuses to emit")
    pc = body + tail
    frame = legacy.frame_pc(pc)
    # Re-derived end to end, not spot-checked.  mob_pickup.py:1652-1668 wrote
    # this lesson down for its own delta: a magic-plus-suffix check is nearly
    # circular -- the framing layer writes the declared length itself, so a
    # shim that framed completely different bytes passed it.  The first draft
    # of this function re-introduced that weaker check and pf-adversary got a
    # 75-byte frame with a 0xDEADBEEF length past it (round ewm6ff, D5).  The
    # suffix form also refused every pc of 65534 bytes or more, where
    # frame_pc's second snappy literal header is CORRECT and the checker was
    # not.  Comparing against this module's own re-derivation fixes both.
    if frame != _frame_via_struct(pc):
        raise MobLootContractError(
            REFUSE_FRAME_ENCODER_DISAGREES,
            "the legacy framing layer and this module's re-derivation of it "
            "disagree about the preserved RuntimeRes frame")
    return pc, frame
    # ~~return rewritten, frame~~ IS STRUCK, round 9jrsei: a leftover of the
    # draft that rewrote an already-composed pc (refuted in round ewm6ff,
    # finding D1).  It is unreachable AND names a variable this function does
    # not define, so the day somebody deletes the return above it, this line
    # answers with a NameError instead of bytes.  Struck rather than deleted,
    # per the project's rule, with the reason beside it.


def money_element(legacy: Any, money: Any) -> bytes:
    """Refuse, by name.  A money slot has no item id and the element needs one."""
    raise MobLootContractError(
        REFUSE_MONEY_HAS_NO_ELEMENT,
        "money cannot be placed on the ground through this pipe: the element "
        "carries an item id and nothing else")


# ---------------------------------------------------------------------------
# The pin document and the report.
# ---------------------------------------------------------------------------
PIN_ID = "port_royal_field_mob_loot_001"
PIN_BUILD_ORDER = MOB_LOOT_BUILD_ORDER
PIN_LANE = MOB_LOOT_LANE


def pin_document(legacy: Any) -> dict:
    """What this lane emits, computed rather than typed, for scenarios/."""
    # ``field_drop_tables.SCENE`` and not a literal, with the HALF of that
    # artifact the first draft of this comment left out (pf-adversary, round
    # 4e9r7g): that constant is the module's own STRUCK-THROUGH back-compat
    # name for the FIRST scene mined, not "the scene the tables were mined
    # from" -- ``SCENES`` is ('bg0001', 'Bg0002') and is what that module is
    # about now.  It is still the right value HERE for a reason that does not
    # depend on which scene it names: this is a document sample, and the
    # scene changes no composed byte (it does not travel -- see GroundDrop),
    # so the pinned bytes in scenarios/ are unchanged whichever scene the
    # sample declares.
    sample = GroundDrop(
        DROP_KEY_BASE, 2400046, 1, as_wire_float(1.0), as_wire_float(2.0),
        as_wire_float(3.0), 0x201F, 0x0101, field_drop_tables.SCENE,
    )
    pc = drop_pc(legacy, sample)
    frame = legacy.frame_pc(pc)
    masked = bytearray(pc)
    for start, end in DROP_COORD_SPANS:
        masked[start:end] = b"\x00" * (end - start)
    # A SECOND SAMPLE, because the shipped pin now has to describe the shape
    # a MULTI-drop kill emits as well as the one GT-045 measured.  Composed
    # through the real path, not typed: if the wide generation ever stops
    # composing, this document stops being generatable and the shipped file
    # goes stale loudly instead of quietly.
    sample_pair = (
        sample,
        GroundDrop(
            DROP_KEY_BASE + 1, 2400047, 1,
            as_wire_float(1.0 + DROP_SCATTER_STEP),
            as_wire_float(2.0), as_wire_float(3.0), 0x201F, 0x0101,
            field_drop_tables.SCENE,
        ),
    )
    (pair_pc, pair_frame), = drop_frames(legacy, sample_pair)
    masked_pair = bytearray(pair_pc)
    for index in range(len(sample_pair)):
        base = DROP_ENVELOPE_SIZE + index * DROP_ELEMENT_SIZE
        for start, end in DROP_ELEMENT_COORD_SPANS:
            masked_pair[base + start:base + end] = b"\x00" * (end - start)
    # THE WIDE (mask-0x16) SHAPE, sampled through the SAME two real functions
    # (single-element, two-element) the narrow block above uses -- not typed,
    # for the same "goes stale loudly instead of quietly" reason.  Added
    # round KA1B-DROPMODEL FOLLOW-UP pf-adversary LOW finding: refresh_frames
    # (the real per-kill composer) has defaulted to THIS shape since this same
    # round, but the structured "wire" block above still only described the
    # narrow one -- a reader trusting structure over the free-text notes
    # (NONCLAIM 23) would get the machine-checked fields wrong.  Called
    # directly through the "_with_model_type" primitives, not through
    # ``drop_frames_with_model_type``/``refresh_frames``, so this document
    # describes the wide shape regardless of :data:`DROP_MODEL_TYPE_FIELD_
    # ENABLED`'s current value -- the flag's value is recorded separately,
    # below, as ``is_the_default_production_shape``.
    sample_pc_wm = drop_pc_with_model_type(legacy, sample)
    sample_frame_wm = legacy.frame_pc(sample_pc_wm)
    masked_wm = bytearray(sample_pc_wm)
    for start, end in DROP_ELEMENT_COORD_SPANS_WITH_MODEL_TYPE:
        masked_wm[DROP_ENVELOPE_SIZE + start:DROP_ENVELOPE_SIZE + end] = (
            b"\x00" * (end - start))
    pair_pc_wm = drop_collection_pc_with_model_type(legacy, sample_pair)
    pair_frame_wm = legacy.frame_pc(pair_pc_wm)
    masked_pair_wm = bytearray(pair_pc_wm)
    for index in range(len(sample_pair)):
        base = DROP_ENVELOPE_SIZE + index * DROP_ELEMENT_SIZE_WITH_MODEL_TYPE
        for start, end in DROP_ELEMENT_COORD_SPANS_WITH_MODEL_TYPE:
            masked_pair_wm[base + start:base + end] = b"\x00" * (end - start)
    return {
        "schema": 1,
        "id": PIN_ID,
        "build_order": PIN_BUILD_ORDER,
        "lane": PIN_LANE,
        "milestone": MOB_LOOT_MILESTONE,
        "test_only": False,
        "production_allowed": True,
        "scenario": None,
        "wire": {
            "envelope_pin_hex": DROP_ENVELOPE_PIN.hex().upper(),
            "frame_header_pin_hex": DROP_FRAME_HEADER_PIN.hex().upper(),
            "runtime_derived_bit": RUNTIME_DERIVED_BIT_GROUND_LIST,
            "element_mask": ELEMENT_MASK_POSITION_AND_DWORD,
            "element_field_order": list(ELEMENT_FIELD_ORDER),
            "elements_per_generation": "every drop of that kill (RE-130)",
            "generations_per_kill": 1,
            "element_size": DROP_ELEMENT_SIZE,
            "max_elements_per_frame": DROP_MAX_ELEMENTS_PER_FRAME,
            "pc_size": DROP_PC_SIZE,
            "frame_size": DROP_FRAME_SIZE,
            "masked_pc_sha256": hashlib.sha256(bytes(masked)).hexdigest().upper(),
            "sample_frame_size": len(frame),
            "two_element_pc_size": len(pair_pc),
            "two_element_frame_size": len(pair_frame),
            "two_element_masked_pc_sha256": (
                hashlib.sha256(bytes(masked_pair)).hexdigest().upper()),
        },
        "wire_with_model_type": {
            "envelope_pin_hex": DROP_ENVELOPE_PIN.hex().upper(),
            "frame_header_pin_hex": DROP_FRAME_HEADER_PIN.hex().upper(),
            "runtime_derived_bit": RUNTIME_DERIVED_BIT_GROUND_LIST,
            "element_mask": ELEMENT_MASK_WITH_MODEL_TYPE,
            "element_field_order": list(ELEMENT_FIELD_ORDER_WITH_MODEL_TYPE),
            "elements_per_generation": "every drop of that kill (RE-130)",
            "generations_per_kill": 1,
            "element_size": DROP_ELEMENT_SIZE_WITH_MODEL_TYPE,
            "max_elements_per_frame": DROP_MAX_ELEMENTS_PER_FRAME_WITH_MODEL_TYPE,
            "pc_size": DROP_PC_SIZE_WITH_MODEL_TYPE,
            "frame_size": DROP_FRAME_SIZE_WITH_MODEL_TYPE,
            "masked_pc_sha256": (
                hashlib.sha256(bytes(masked_wm)).hexdigest().upper()),
            "sample_frame_size": len(sample_frame_wm),
            "two_element_pc_size": len(pair_pc_wm),
            "two_element_frame_size": len(pair_frame_wm),
            "two_element_masked_pc_sha256": (
                hashlib.sha256(bytes(masked_pair_wm)).hexdigest().upper()),
            "is_the_default_production_shape": DROP_MODEL_TYPE_FIELD_ENABLED,
            "not_yet_client_measured": True,
        },
        "lane_constants": {
            "drop_key_base": DROP_KEY_BASE,
            "drop_key_limit": DROP_KEY_LIMIT,
            "scatter_step": DROP_SCATTER_STEP,
            "refresh_ms": DROP_REFRESH_MS,
            "refresh_ms_is_experiment_only": (
                DROP_REFRESH_MS_IS_EXPERIMENT_ONLY),
            "max_drops_per_kill": MAX_DROPS_PER_KILL,
        },
        "measured": {
            "ground_drop_persists": not GROUND_DROP_DOES_NOT_PERSIST,
            "model_under_the_label_that_was_seen": (
                not NO_MODEL_UNDER_THE_LABEL_THAT_WAS_SEEN),
            "name_label_is_drawn": True,
            "label_lifetime_seconds_range": list(
                GROUND_LABEL_OBSERVED_LIFETIME_SECONDS),
            "label_lifetime_frame_measurement_seconds": (
                GROUND_LABEL_MEASURED_SECONDS),
            "label_lifetime_mandatory_slack_seconds": (
                GROUND_LABEL_FRAME_SLACK_SECONDS),
            "wire_to_screen_seconds": WIRE_TO_SCREEN_SECONDS,
            "ids_on_the_wire_gt045_v3": list(IDS_ON_THE_WIRE_GT045_V3),
            "ids_on_the_wire_round_1104": list(IDS_ON_THE_WIRE_ROUND_1104),
            "id_whose_label_was_read": ID_WHOSE_LABEL_WAS_READ,
            "emittable_ids_ever_on_a_wire": 0,
            "ticket": "GT-045 CLOSED-ANSWERED 2026-08-25 (chief R163)",
            "client_observable_layer_is_re_verifiable_from_the_repo": (
                "one extracted frame only; the round-4 video is over the "
                "size cap and the round-3 screenshots carry no label"
            ),
            "not_a_lifetime_of_this_pipe": {
                "seconds": ORIGINAL_SERVER_PICKUP_TERMINATED_SECONDS,
                "what_it_is": (
                    "original-server video, pickup-terminated interval"
                ),
            },
        },
        "tables": {
            "scene": field_drop_tables.SCENE,
            "normal_sets": sorted(field_drop_tables.DROPS_NORMAL),
            "equipment_sets": sorted(field_drop_tables.DROPS_EQUIPMENT),
            "specially_sets": sorted(field_drop_tables.DROPS_SPECIALLY),
            "item_ids": len(field_drop_tables.ITEMS),
            "source_digests": dict(field_drop_tables.SOURCE_DIGESTS),
        },
        "refusals": list(MOB_LOOT_REFUSAL_REASONS),
        "nonclaims": list(MOB_LOOT_NONCLAIMS),
        "wiring": MOB_LOOT_WIRING,
    }


def loot_report(mob: Any, roll: DropRoll) -> dict:
    """A human-readable summary of one roll, for a console and a round note."""
    mob = _require_mob(mob)
    if type(roll) is not DropRoll:
        raise MobLootContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "roll must be a typed DropRoll")
    return {
        "mob": mob.display_name,
        "template_id": mob.template_id,
        "identity": mob.actor_identity,
        "items": [
            {
                "item_id": item.item_id,
                "name": item.display_name,
                "quantity": item.quantity,
                "source": item.source_table,
                "set_id": item.source_set_id,
                "drop_model_type": item.drop_model_type,
            }
            for item in roll.items
        ],
        "money": [
            {
                "amount": row.amount,
                "amount_provenance": row.amount_provenance,
                "source": row.source_table,
                "tag": row.tag,
            }
            for row in roll.money
        ],
        "draws": roll.draws,
        "refusals": [list(row) for row in roll.refusals],
        "placeable": roll.placeable_count,
    }


def drops_console_line(mob: Any, drops: Any) -> str:
    """One ASCII line reporting the ground drops one kill actually sent.

    Same shape as ``world_population.census_console_line`` and
    ``mob_death.describe_roster_override_coverage``: a pure function a
    wiring pass can ``print()`` at ~~the ``mob_loot.drop_frames`` call site
    in ``runtime.py``~~ CORRECTED, ROUND KA1B-DROPMODEL FOLLOW-UP,
    2026-09-01: the mob-death dispatch site in ``runtime.py``
    (``runtime.py:4923``, beside ``mob_drop_presence.sustain_a_kill``,
    which is what actually calls into this module today -- see NONCLAIM
    23), so this lane -- unlike its siblings -- becomes visible to
    a "WIRED v2" console grep instead of being provably-wired-but-silent.

    ``MOB_LOOT_DROPS_CENSUS`` is the token.  ``mob.display_name`` is escaped
    with ``ascii()`` before it reaches the line, the same guard
    ``field_mobs.roster_report`` already uses for a console this project
    prints on a cp874 code page: a mob's display name is game-data text this
    module has never measured to be cp874-safe, so it is not trusted bare on
    a console any more than any other unproven string is.

    Takes the SENT drops (the ``GroundDrop`` tuple ``DropLedgerCell.loot_a_kill``
    returned for this kill), not the ledger and not the roll -- refusals,
    money and anything the roll produced but this lane never places are
    already visible in ``loot_report`` and repeating them here would blur
    the one count this line exists to make grep-able: how many
    ``MOB_LOOT_DROP`` frames actually went out for this kill.
    """
    mob = _require_mob(mob)
    if type(drops) is not tuple:
        raise MobLootContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "drops must be a tuple")
    for drop in drops:
        if type(drop) is not GroundDrop:
            raise MobLootContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "every drop must be a typed GroundDrop")
    items = ",".join(
        "%d:x%d@0x%X" % (drop.item_id, drop.quantity, drop.drop_key)
        for drop in drops
    )
    # generations= AND pc_bytes= EXIST FOR AN ATTENDED TESTER, round zxnwtd.
    # GT-132 has to tell a build that coalesces from one that does not, from
    # a console with NO flags on it, and its first draft told the tester to
    # grep a token that is never printed (pf-adversary D3).  These two are
    # printed, they are the emitter's own arithmetic (the same numbers
    # drop_collection_pc refuses to differ from), and an older build prints
    # neither -- so their ABSENCE is the build check.
    return (
        "MOB_LOOT_DROPS_CENSUS mob=%s template=%d identity=0x%X drops=%d "
        "generations=%d pc_bytes=%d items=%s" % (
            ascii(mob.display_name), mob.template_id, mob.actor_identity,
            len(drops), 1 if drops else 0,
            DROP_ENVELOPE_SIZE + DROP_ELEMENT_SIZE * len(drops) if drops
            else 0,
            items if items else "none",
        )
    )
