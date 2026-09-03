"""Both HOME-menu buttons stop being dead clicks: they answer where she looks.

WHAT THE PLAYER GETS FROM THIS FILE
-----------------------------------
Round `1d6rta` (2026-09-02) extended this file from ONE button to BOTH.  The
paragraphs below are the UI-A half as it was written in round `od1xso`; the
UI-B half is described under "THE SECOND BUTTON" further down, and point 3 of
the nonclaims carries the struck sentence it replaced.

~~Today, on a default boot with no scenario flag, clicking the HOME menu's
"back to character select" button (`LogoutVital 0x1B40` subcode 3) produces
NOTHING: no reply frame, no console line, no pixel.~~  READ THAT AS
"BEFORE THIS MODULE", NOT AS "TODAY": on 2026-09-02 the owner clicked that
button on a flagless boot carrying this file and `BACK REFUSED` appeared on
her screen (R303, `GT-205`; the whole measurement, and the three things it
did NOT settle, are under point 2 of WHAT THIS FILE DOES NOT CLAIM).  The
silence is what this module was built to end, and the sentence is kept
because it is the reason the file exists.  The owner measured
that herself on 2026-09-01 (`pf_bridge/notes_to_chief/consumed/20260901_
1930_KA1A-CAPTURE-*.md`, capture `gt192_20260901_184254`, boot with no
logout scenario at all): the client sent a real 34-byte subcode-3 frame and
the server said nothing back.  Two attended rounds in a row were lost to
that silence (`pf_bridge/NOW.md`, item UI-A).

This module composes the smallest honest answer this project has a codec
for: one `Channel_LocalTalkMessageVital` line carrying exactly twelve ASCII
characters, `BACK REFUSED`, through LANE-GM's already proven composer
(`gm/say_wire.make_local_talk_notice_frame`).  It is the same shape COO
approved for `/speed` refusals (`SPEED DENIED`, COO-DECISION `20260902_
0345`) and for command typos (`TYPO REFUSED`, COO-DECISION `20260902_
0647`): when the server cannot do the thing, it SAYS SO where the player is
looking, rather than dropping the request on the floor.

WHAT THIS FILE DOES NOT CLAIM
-----------------------------
1. It does NOT implement UI-A.  Returning to the character-select screen is
   still unsolved: `GT-033` measured both response policies we own
   (ack+close; `0x709E`+ack+close) leaving the client on the same map for
   50-77 seconds across three attended rounds, and `RE-197` (result
   `20260902_0333`) closed the last candidate pre-click discriminator.  A
   notice is a receipt, not a transition.
2. It does NOT claim the words render ON AN ARBITRARY BOOT, and one
   sentence of this point is now struck while the rest of it stands.
   ~~`gm/say_wire.py`'s own docstring states it in capitals and this file
   repeats it rather than softening it: NO SERVER-COMPOSED LINE ON THIS
   CHANNEL HAS EVER BEEN SEEN ON A SCREEN ON A DEFAULT BOOT.~~  NARROWED,
   round `kozzu1` (2026-09-03), by a positive `GT-205` -- see WHAT R303
   ACTUALLY SHOWS below for exactly how far, which is less far than the
   first draft of this correction claimed.  The rest of this point is NOT
   struck and is still load-bearing: the twelve-character length comes
   from `GT-006`/`GT-009`, where what rendered was the client's OWN echoed
   text behind a scenario flag -- and with the logout dialog closed, which
   is not the state this module fires in.  `GT-205` is the entry that
   decides it for UI-A and `GT-211` (opened round `1d6rta`) for UI-B --
   named separately because `GT-205` was amended in that same round to say
   the exit line is NOT its evidence, so citing it alone would point a
   reader at a ticket that disclaims the question (pf-adversary D8).  A
   negative in either is a finding about the dialog and about this
   channel, not proof the composer is wrong.  THAT LAST SENTENCE IS WHY
   THE STRIKE ABOVE IS ONE SENTENCE WIDE: a POSITIVE `GT-205` is not
   evidence for `GT-211` either, and the first draft of this correction
   struck the sentence that says so, which would have reopened D8 through
   the back door (pf-adversary, this round, D6).

   WHAT R303 ACTUALLY SHOWS, AND THE WORD "DEFAULT" IS WHERE THE FIRST
   DRAFT OF THIS PARAGRAPH WENT WRONG.
   Quoted rather than paraphrased, from `pf_bridge/notes_to_chief/
   20260902_1755_KA1A-R303-RESULTS-*.md`: "after 'back to character
   select' the chat line `[thua pai] : BACK REFUSED` appeared on screen,
   which is the ticket's own success text.  Screenshot held by the owner."
   Round R303, owner at the keyboard, capture
   `capture_r303_20260902_161029`, boot commit `7e14bde1` (verified this
   round: that commit's `runtime.py` carries this module's import and its
   `observe_parsed` call site, and this module's `production_allowed` is
   `True` there).
   * ESTABLISHED: the line rendered on a boot that carried NO LOGOUT
     SCENARIO.  That is not read off the ticket -- it follows from the
     guard: `runtime.py` composes this notice only when
     `logout_hypothesis_scenario is None`, so a rendered `BACK REFUSED`
     could not have come from a logout-scenario boot.
   * NOT ESTABLISHED: that the boot was FLAGLESS.  `GT-205`'s server-args
     line instructs "NO scenario flag of any kind", but an instruction is
     not a measurement, and the result letter records head, boot commit,
     boot tree, run db, capture, jobs and teardown -- and NO argv.  The
     boot tree it names is not in either repository.  Point 3 of this same
     docstring already measured that around twenty-eight OTHER scenario
     keywords leave this branch live, so a non-logout scenario boot would
     render this line too.  An earlier draft of this very paragraph wrote
     "on a flagless boot" anyway -- the same inference point 3 exists to
     forbid (pf-adversary, this round, D1).
   * ATTRIBUTION, ARGUED RATHER THAN ASSERTED: the rendered string has an
     EMPTY SPEAKER SLOT.  This project's other render evidence reads
     `[<channel label>] <speaker> : <text>` (`[thai general] Arena01:
     PFCHATPROBE1`), and `say_wire.DEFAULT_SPEAKER` is `""` and pinned --
     a client echo carries the character's name there, a server-composed
     frame does not.  That is the discriminator, and it is why "these were
     this module's bytes" is a reasonable reading.  It is NOT proof: no
     one in this repository has seen the screenshot.

   WHAT R303 DID NOT SETTLE, BECAUSE A ROUND THAT ONLY REPORTS THE GOOD
   HALF IS HOW THIS PROJECT GOT `GT-192`'S TWICE-PAID DEBT.  The first
   draft of this list had three items; the reviewer found four more.
   * The console token was not copied back.  The result letter says, in
     its own words, "wire/DB: not separately instrumented for this
     ticket", so `LANE_A_UIA_NOTICE_COMPOSED` was NOT read off that boot.
     The wire/DB rung still rests where it always rested -- the headless
     pins in `tests/test_world_logout_button_notice.py` -- and this
     paragraph is not a second layer.
   * The dialog state was not recorded.  Step 8 asks whether the logout
     dialog was still open when the line appeared; the result does not
     say.  The sentence above about the dialog being CLOSED in `GT-009` is
     therefore NOT resolved either way.
   * The length pin does not move.  R303 rendered TWELVE characters, which
     is the length this module already sends.  Nothing here licenses 5, 26
     or any other body length.
   * The boot's argv was never recorded (see NOT ESTABLISHED above).
   * WHERE on screen, at what offset from the click, and for how long: step
     8 asks five things and the result answers one.  "in the local
     chat/talk area" is part of the pass criterion and is unverified.
   * The name-label colour table the pass criteria makes mandatory for
     every still is absent from the result.  That is an uncounted skip in
     an attended round, not a detail.
   * n = 1.  One click, one session, one attempt, in a boot where the
     PRECEDING ticket (`GT-193`) had just killed the character and left
     the client sending nothing.  Whether a relog happened between the two
     is not documented.
   * The screenshot is held by the owner and is in neither repository: no
     path, no sha256, no console `.out`/`.err`.  The rung this correction
     promotes is auditable by one person; the rung it does NOT promote
     (wire/DB) is auditable by anyone.
   NOT THIS LANE'S TO EDIT: `gm/say_wire.py:107` still carries the same
   sentence and still names `GT-193` step 9 as "the first attempt", which
   R303 overtook (and `GT-193` itself came back FAIL that round).  That
   file is LANE-GM's; this round tells chief in one line and does not
   touch it.
3. ~~It does NOT send bytes for the UI-B ("exit game", subcode 1) button.
   That path has a live ticket of its own (`GT-194`) whose bytes must not
   change under it, so subcode 1 gets `None` -- pinned by a test.  It DOES
   print one console line for that click, which is itself evidence a
   reader of `GT-194`'s log will see; "nothing" would be the wrong word.~~
   SUPERSEDED, round `1d6rta`, by COO-DECISION `20260902_1145` (`NOW.md`
   queue item UI-B, quoted whole because the second half is a constraint
   on how this round was allowed to work: "LANE-A starts next round, same
   pattern as UI-A - THE FIRST DELIVERABLE IS EVIDENCE OF WHAT FRAME THE
   BUTTON SENDS, NOT CODE".  The evidence half is
   `pf_bridge/FINDINGS_A_1d6rta_UI_B_LOGOUT_BUTTON_FRAME_EVIDENCE.md`, and
   it was measured before this file was touched.)

   Subcode 1 now composes `EXIT REFUSED` on any boot that has NOT loaded a
   LOGOUT scenario.  STATED THAT WAY BECAUSE THE WIDER VERSION WAS FALSE
   (pf-adversary D4, MEASURED): an earlier draft of this comment said
   "on a DEFAULT boot only", but `runtime.py`'s guard reads
   `logout_hypothesis_scenario is not None`, and there are around
   twenty-eight other scenario keywords on `make_state_class`.  A boot
   carrying, say, the chat-echo scenario DOES compose this notice.  That
   is the real behaviour, it is pinned by a test, and any ticket that
   boots a non-logout scenario and clicks this button will see the frame.

   Why `GT-194`'s evidence still cannot move: that ticket needs
   `_dispatch_logout_hypothesis` to answer, which only happens with a
   logout scenario loaded, and `runtime.py`'s call site composes NOTHING
   and prints `LANE_A_UIA_NOTICE_NOT_THIS_BOOT` whenever
   `logout_hypothesis_scenario is not None`.  The two tickets are on
   disjoint boots THROUGH THAT ONE FLAG -- not through session state,
   which this branch never consults -- and a wiring test drives the UI-B
   frame down that branch to pin it.

4. It sends nothing and closes nothing.  It composes bytes and hands them
   back, the same posture as `gm/say_wire.py` and `gm/warp_executor.py`.
   The one line that calls it lives in `runtime.py`, which is chief's file
   (it is already there, from round `od1xso`'s CORE-REQUEST; this round
   asks chief for no new line at all -- see "NO NEW WIRING" below).
5. It does NOT perform a logout.  `NOW.md` states the owner's requirement
   in her own words -- a REAL logout button, not closing the window with
   the X -- and a receipt is not that.  `GT-033` measured both response
   shapes this project owns (ack+close; `0x709E`+ack+close) leaving the
   real client on the same map for 50-77 seconds across three attended
   rounds, and `RE-189` (result `20260901_1008`) found the one writer of
   the field the client's own transition gate requires is LOCAL UI
   BINDING, with no inbound frame able to reach it.  So UI-B is not
   solved here; what changes is that the click answers.

THE SECOND BUTTON (UI-B, "exit game", subcode 1)
------------------------------------------------
Same measurement, same silence: on the owner's flagless capture
(`gt192_20260901_184254`, frame `[G< #1402]`) the client sent a real
119-byte subcode-1 frame -- the button carries three other vitals with it,
two `COnLandVital` (`0x1EB4`) and one `TargetPosVital` (`0x2A90`), which is
why it is 119 bytes and not 34 -- and the server said nothing back.  What
this file delivers is the same twelve-character receipt UI-A got, so the
click stops being indistinguishable from a broken mouse.

The two buttons are told apart by SUBCODE, which is in the request itself
(`RE-197` closed the pre-click discriminator: the 268-byte frame that
precedes the dialog is byte-identical for both, so nothing can tell them
apart before the click -- but nothing needs to, because the click says).

NO NEW WIRING
-------------
`runtime.py`'s 0x1B40 branch already calls `observe_parsed` and already
sends whatever notice comes back, for ANY button, because round `od1xso`
wrote the call site around the return value rather than around UI-A.  So
this round ships a player-visible change with no chief-owned line to wait
for.

ONE MISMATCH IS LEFT BEHIND, AND IT IS NOT COSMETIC.  The action label and
event name at that call site read
`LANE_A_UIA_BACK_REFUSED_LOCAL_TALK_NOTICE` /
`lane_a_uia_back_refused_notice_composed`, and they now carry the
`EXIT REFUSED` frame too.  ~~An earlier draft of this paragraph called that
cosmetic because "the label is not on the wire".~~  MEASURED, pf-adversary
D1: the label is not on the wire, but it IS in the evidence.  The frozen
sender writes it into all three artifacts an attended ticket keeps and
shas (`current/pf_login_game_server_v141.py:7755-7776`): the console line
`[G>] <label> (N bytes; ...)`, the live log `SENT label=<label> ...`, and
the exported events file.  Both sentences are twelve characters, so both
receipts are `pc=56 frame=66` -- which makes the two clicks' `SENT` lines
BYTE-IDENTICAL in `GAME_LIVE.txt`.  The one place the capture tells them
apart is this module's own `LANE_A_UIA_NOTICE_COMPOSED ... button=...`
print, which is why `GT-211` grades on that line and says so.

~~The names are chief's to rename (`runtime.py` is his file); the request is
in this round's PR body and in
`pf_bridge/notes_to_chief/20260902_1341_LANE-A-TO-CHIEF-*`, upgraded there
from "cosmetic, whenever" to "the capture layer of `GT-211` reads better
with it".~~  HALF OF THAT IS NOW DONE HERE, round `omhpqj` (2026-09-03),
on COO-DECISION `20260903_1746` item 2, which ordered the mismatch out of
the evidence: the name this lane wants is DATA IN THIS FILE now
(`ACTION_LABEL_BY_BUTTON`, read off a notice as `notice.action_label`), so
the chief-owned half is no longer "pick a name" but one literal swapped
for one attribute read -- `CORE-REQUEST 20260903_1832` carries the exact
line.  The struck sentence is kept because it is the request that stood
for a day, and because the rest of it is still true: it blocks nothing,
the bytes the player receives are correct either way, and the console line
already disambiguates.

ONLY THE EXIT BUTTON IS RENAMED, and the first draft of this paragraph
justified that with a sentence that is FALSE.  ~~It is the house rule that
a PR moving a string a ticket greps must keep the grep answering: `GT-205`
grades on the UI-A label, and a rename of both would have taken its
command to zero hits.~~  MEASURED FALSE (pf-adversary D4, this round):
`GT-205`'s block in `pf_bridge/GAME_TEST_QUEUE.md` contains ZERO
occurrences of `LANE_A_UIA_BACK_REFUSED_LOCAL_TALK_NOTICE`.  What that
ticket greps is `LANE_A_UIA_NOTICE_COMPOSED` (three occurrences) and the
sentence `BACK REFUSED` (ten), neither of which this round touches.  The
grep rule (`pf_bridge/AGENTS.md`, COO-DECISION `20260903_1545` item 3) is
about a string a ticket greps being deleted or moved, and this round
deletes and moves nothing: chief's UI-A literal is untouched and the UI-B
name is new.  THE REAL REASON is smaller and it is enough: COO's order
names one button (`EXIT_GAME` => `EXIT_REFUSED`), the UI-A label is not
wrong for the UI-A click, and a second rename would put a second line of
chief's file in this lane's request for no gain to any reader.

ONE ENTRY POINT, ON PURPOSE
---------------------------
`observe_parsed(legacy, parsed)` is the only public way in.  An earlier
draft of this file also exported a raw-bytes path, and pf-adversary
measured what two doors cost: the two accepted DIFFERENT frame sets (the
raw reader accepted `vital_count == 1` plus fifty bytes of junk, which
`logout_hypothesis.classify_logout_attempt` calls `wrong_payload`), and
reported a broken seam under two different tokens.  "chief adds ONE call
site" is only a specification if there is one function with one line
format.  So there is.

WHY THE CLASSIFICATION GOES THROUGH `logout_hypothesis`
-------------------------------------------------------
`classify_logout_attempt` is the function the scenario-gated logout
dispatch itself branches on (`runtime.py:1860`).  Reusing it means this
lane cannot answer a click that dispatch would have called `wrong_payload`.
STATED EXACTLY, because pf-adversary caught the softer version: before
round `od1xso` wired this module, nothing on a DEFAULT boot called that
function at all (its other call site sits behind
`logout_hypothesis_scenario is not None`), so the call site chief added is
its first production-mode caller and still has not been watched running on
a real client.  The claim is "one reader of these bytes, not two", not
"already proven live".

`logout_request_envelope` is imported for its two subcode CONSTANTS only --
same reason: one spelling of `1` and `3` in the tree, not three.

FAIL-CLOSED, STATED AS A PROPERTY, WITH ITS ONE HOLE NAMED
----------------------------------------------------------
Every entry point returns a value rather than raising for every ordinary
input: a malformed parse, an unknown subcode, a `legacy` seam that
misbehaves, a composer that refuses.  The hole, named because
`lane_hooks/__init__.py` names its own: `BaseException` (`KeyboardInterrupt`,
`SystemExit`, `GeneratorExit`) is deliberately NOT caught, here or in
`say_wire`, so a seam that raises one of those still propagates.  That is
Python's own convention for thread targets, not an oversight.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import logout_hypothesis
from . import logout_request_envelope
from .gm import say_wire


# Flag-free by charter: LANE-A ships behaviour that is live on a default
# boot or it does not ship it.  The gate that remains is the standard
# module-level one every lane module is held to.
#
# READ THIS FLAG DIRECTLY, NOT THROUGH `lane_hooks`.
# `lane_hooks.module_production_allowed()` resolves names only under
# `pirateforce_foundation.lane_hooks.` and returns False for everything
# else -- including this module, forever (pf-adversary D7: a call site that
# asked lane_hooks would stand down on every click while `GT-205`'s RECHECK
# reported the wiring present, and the owner would spend a whole attended
# round on it).  `observe_parsed` also checks the flag itself, so a call
# site that forgets still cannot compose bytes.
production_allowed = True

# Twelve ASCII characters, because twelve is the only body length anything
# on this channel has been watched to render (GT-006/GT-009 probe bodies
# `PFCHATPROBE1`/`PFCHATPROBE2`; a five-character body was measured
# SILENT).  The wording follows the house pattern for a visible refusal:
# `SPEED DENIED`, `TYPO REFUSED`, and now `BACK REFUSED` -- "back" being
# the button's own word ("back to character select"), refused because the
# server cannot yet perform it, not because it declined to.
#
# WHAT IS PINNED AND WHAT IS NOT: the LENGTH is measured; the CHARACTER
# CLASS is not.  Both watched bodies were twelve alphanumerics with no
# space, and this text puts a space at index 4 (as `SPEED DENIED` already
# does, so the risk is house-wide, not new here).  Nothing measured covers
# it -- `GT-205` is where that is first exercised.
#
# ~~[assumption of lane A - awaiting COO confirmation; the letter carrying
# it is pf_bridge/notes_to_chief/20260902_0910_LANE-A-ASK-COO-uia-notice-
# wording.md]~~ RULED, round 8z9h9n: COO-DECISION 2026-09-02T09:43+07:00
# (pf_bridge/notes_to_chief/20260902_0943_COO-DECISION-uia-notice-text-
# back-refused-confirmed.md) confirms this exact spelling.  The
# strikethrough-plus-RULED shape is this repo's own (mob_scene_recompose.py
# does the same for a LANE-B assumption): the sweep that hunts for still-
# open lane assumptions greps for the label text, so a retired one has to
# be distinguishable from a live one ON the matched line, not three lines
# further down.
#
# WHAT THE DECISION ACTUALLY SAYS, no wider: it confirms option 1 and
# refuses TWO of the ask letter's four options -- `EXIT REFUSED` (collides
# with the UI-B button) and staying silent (the outcome that burned two of
# the owner's attended rounds).  The letter's option 2, `BACK NOT YET`, is
# NOT adjudicated anywhere: this lane dropped it itself for style, and it
# stays the honest wording for the day the transition becomes performable,
# so a later round should reach for it rather than assume it was refused.
# The one-vocabulary reading (`SPEED DENIED`, `TYPO REFUSED`, `BACK
# REFUSED`) is the REASONING COO gave, not a house rule anyone wrote down;
# it also does not decide REFUSED vs DENIED, and `SPEED DENIED` answers a
# chat command rather than a button, so do not cite this comment as policy.
#
# WHAT IS STILL NOT SETTLED (not a complete list -- see point 2 of this
# module's own docstring for the bigger one): whether a twelve-character
# body with a space at index 4 RENDERS while the logout dialog is open.
# `GT-205` is where a human first sees that -- it accepts the line either
# while the dialog stands or right after it closes -- and a negative result
# there is worth as much as a positive one.
#
# WHAT CHANGING THE SPELLING COSTS, counted rather than guessed: this
# constant, the two test lines that pin the literal, the two prose lines in
# this file that quote it (module docstring and the paragraph above), a new
# COO decision -- and four lines of pf_bridge/GAME_TEST_QUEUE.md's GT-205,
# including the console line a tester copies by hand, which is a
# chief-owned queue file only editable from a cloud clone through a PR.
UIA_NOTICE_TEXT = "BACK REFUSED"

# THE UI-B BODY.  Twelve printable ASCII characters, the same pinned length
# (`say_wire.NOTICE_TEXT_EXACT_LENGTH`) and the same house pattern as
# `SPEED DENIED` / `TYPO REFUSED` / `BACK REFUSED`.
#
# WHY THIS SPELLING AND NOT A REUSE OF `BACK REFUSED`: a tester (and the
# owner) must be able to tell WHICH button she clicked from the screen
# alone.  Two buttons answering with one sentence would make the screen
# half of the evidence unable to distinguish them, which is the exact
# defect COO-DECISION `20260902_0147` set out to avoid for the GM commands.
#
# WHY `EXIT REFUSED` IS AVAILABLE: COO-DECISION `20260902_0943` refused it
# *as UI-A's wording*, with the reason "it collides with the UI-B button".
# That is a statement about which button owns the words, not a ban on the
# words -- so this round claims them for the button they name.
#
# It was a reading of someone else's sentence rather than a ruling, so it
# shipped labelled, and the label is now retired:
#
# ~~[assumption of lane A - awaiting COO confirmation]~~
# RULED, round `gwwpmr` -- AND THE RULING IS NOT VERIFIABLE FROM THIS
# REPOSITORY (pf-adversary D6).  Every COO decision, letter and GT/RE
# ticket this project cites lives in the SEPARATE `pf_bridge` repository,
# which is not a path in this tree; the test below can only assert that
# this comment names a file, never that the file exists or says what the
# comment claims.  That is a property of the two-repo split, not of this
# round, and it is written here so a reader does not mistake a green test
# for corroboration.  The decision, quoted only as far as it was read:
# COO-DECISION 2026-09-02T14:45+07:00
# (pf_bridge/notes_to_chief/20260902_1445_COO-DECISION-lane-a-uib-word-
# exit-refused-confirmed-drop-the-assumption-tag.md) confirms this exact
# spelling and says the reading above was correct -- "collides with UI-B"
# means "reserved FOR UI-B".  Same strikethrough-plus-RULED shape as
# UI-A's retired label above, and for the same reason: the sweep that
# hunts for open lane assumptions matches on the label text, so a retired
# one has to be distinguishable ON the matched line.
#
# The letter that carried it, one topic per letter as the lane charter
# asks, and which that decision answers:
# pf_bridge/notes_to_chief/20260902_1341_LANE-A-ASK-COO-uib-notice-wording.md
#
# WHAT THAT DECISION ALSO REFUSED, kept because a later round will reach
# for it otherwise: the ask letter's option 2, `EXIT NOT YET`.  COO's
# reason was that the whole game's refusal vocabulary is one shape,
# `<the button's verb> REFUSED/DENIED`, and that "not ready yet" is not
# what the server is doing -- it is refusing.  Options 3 and 4 were
# refused for the reason this lane had already written: one screenshot
# must say which button was clicked.
#
# WHAT CHANGING THE SPELLING COSTS.  ~~counted rather than guessed: this
# constant, the two test lines that pin the literal, the two prose lines
# in this file that quote it~~ -- BOTH NUMBERS WERE WRONG (pf-adversary
# D5, round `gwwpmr`, counted at HEAD: neither was 2).  A count written
# into a comment is stale the moment anyone adds a line, and the round
# that tried to correct it made its own replacement numbers stale in the
# same edit.  So the durable half is the METHOD, and this is it:
#
#     grep -n "EXIT REFUSED" src/pirateforce_foundation/
#         world_logout_button_notice.py
#         tests/test_world_logout_button_notice.py
#         tests/test_world_logout_button_notice_wiring.py
#
# plus the console line a tester copies by hand in `GT-211`, which no
# grep of this repository will find because that ticket lives in
# `pf_bridge`.  No byte of the composer moves either way.
#
# WHAT IT DOES NOT SAY: `EXIT REFUSED` does not mean the server decided the
# player may not leave.  It means this server cannot yet PERFORM the exit
# (`GT-033` measured both response shapes this project owns leaving the
# real client on the same map for 50-77 s, three attended rounds), so it
# answers instead of dropping the click.  Nonclaim 5 states it again.
UIB_NOTICE_TEXT = "EXIT REFUSED"

BUTTON_CHARACTER_SELECT = "BACK_TO_CHARSELECT"
BUTTON_EXIT_GAME = "EXIT_GAME"

# The one place a button is mapped to what the screen will say.  A button
# that is NOT in this table composes nothing and stands down -- fail-closed
# is the default for a shape nobody has measured, not an answer invented on
# the spot.
#
# TODAY BOTH KNOWN BUTTONS ARE HERE, so the stand-down branch is
# unreachable from any frame (pf-adversary D5, and `observe_parsed`'s
# docstring says it in full).  This table is therefore the thing the
# stand-down guards: the failure it prevents is a row removed or a button
# added without a sentence, silently falling back to the OTHER button's
# twelve characters and putting the wrong word on the owner's screen.
NOTICE_TEXT_BY_BUTTON = {
    BUTTON_CHARACTER_SELECT: UIA_NOTICE_TEXT,
    BUTTON_EXIT_GAME: UIB_NOTICE_TEXT,
}

# THE NAME THE CAPTURE CARRIES, ONE ROW PER BUTTON.
#
# This is not on the wire and never will be: the client is handed `pc` and
# `frame`, nothing else.  It is what the FROZEN SENDER writes beside those
# bytes, and WHERE IT GOES WAS RE-MEASURED THIS ROUND rather than copied
# from the sentence that has been repeated since round `1d6rta`
# (pf-adversary D1, round `omhpqj`).  From
# `current/pf_login_game_server_v141.py:7755-7776`, the label reaches
# exactly three places, and an attended ticket keeps and shas the first
# two:
#
#   * `live(f"SENT label={label} frame_bytes=...")`  -> `GAME_LIVE.txt`
#   * `print(f"[G>] {label} (N bytes; ...)")`        -> the console
#   * `f.write(f"SENT {label} bytes=...")`           -> the per-session
#     raw log the listener already had open
#
# ~~and the exported events file~~  MEASURED FALSE, this round.
# `GAME_EVENTS_LIVE.txt` is written ONLY by `event()`
# (`v141:7378-7381`), whose thirteen call sites are `SESSION_START` and
# eleven `MILESTONE` lines plus one at `:7494`; NONE of them is inside
# 7755-7776 and none of them is ever handed a label or a `state.events`
# entry.  `state.events` is read in the frozen file only inside its
# SELFTEST block.  That is why this round ships ONE table and asks chief
# for ONE line: an `events`-name table would have been a second name for
# a second artifact THAT DOES NOT EXIST.
#
# WHY ONE NAME FOR TWO BUTTONS WAS A DEFECT.  Both sentences this module
# composes are twelve characters, so both receipts are `pc=56 frame=66`;
# with one label for both, the `SENT` line for "back" and the `SENT` line
# for "exit" were byte-identical in `GAME_LIVE.txt` and the capture could
# not tell the owner's two clicks apart (pf-adversary D1, round
# `1d6rta`).  COO-DECISION `20260903_1746` item 2 ordered it removed.
#
# WHAT THIS FILE CAN AND CANNOT DO ABOUT IT.  The literal lives at
# `runtime.py`'s 0x1B40 branch, which is chief's file, so this lane cannot
# swap it itself.  What it can do is stop asking chief to CHOOSE a name:
# the rows below are the answer, `notice.action_label` reads them, and
# `CORE-REQUEST 20260903_1832` asks for one literal to become one
# attribute read.  Until that lands, nothing here changes what a player or
# a tester sees, and `tests/test_world_logout_button_notice_wiring.py`
# reads chief's file to say WHICH of the two worlds this tree is in, so
# "chief never got to it" can never look like "chief did it".
#
# `BUTTON_CHARACTER_SELECT` KEEPS CHIEF'S CURRENT STRING, on purpose; see
# the docstring section "ONLY THE EXIT BUTTON IS RENAMED".
UIA_ACTION_LABEL = "LANE_A_UIA_BACK_REFUSED_LOCAL_TALK_NOTICE"
UIB_ACTION_LABEL = "LANE_A_UIB_EXIT_REFUSED_LOCAL_TALK_NOTICE"

ACTION_LABEL_BY_BUTTON = {
    BUTTON_CHARACTER_SELECT: UIA_ACTION_LABEL,
    BUTTON_EXIT_GAME: UIB_ACTION_LABEL,
}

# What a notice reports when its button has bytes but no row above.  It
# cannot happen from a frame -- `classify_parsed` returns one of the two
# known buttons and both are in both tables, pinned by a key-parity test
# -- and it is NOT a fallback to the other button's name, which is the
# failure the text table's stand-down branch guards against for the words
# on screen.  It exists because the reader of this property is chief's
# `else:` branch, which is OUTSIDE his `try`: a `KeyError` from a property
# read there would take the listener thread down for the player whose
# click it was, and Python does not route an `else:`-body exception to
# that `except`.  A capture carrying this token names the defect instead
# of pointing at the wrong button.
UNLABELLED_BUTTON_ACTION_LABEL = "LANE_A_LOGOUT_NOTICE_UNLABELLED_BUTTON"

# ASCII console tokens (the bridge console is cp874; nothing Thai here).
# A human reading a capture log next to a screenshot lines the two up by
# these, which is the wire/DB half of `GT-205`'s two-layer evidence.
#
# `COMPOSED` MEANS BYTES EXIST.  It is emitted only from a
# `LogoutButtonNotice`, i.e. only after `say_wire` returned a frame
# (pf-adversary D2: an earlier draft printed it straight off the
# classification, so a refused composer still logged "COMPOSED").  Every
# other outcome has its own token, so no reader has to guess which of two
# meanings a line carries.
TOKEN_NOTICE_COMPOSED = "LANE_A_UIA_NOTICE_COMPOSED"
TOKEN_NOTICE_FAILED = "LANE_A_UIA_NOTICE_FAILED"
TOKEN_WITHDRAWN = "LANE_A_UIA_WITHDRAWN"
TOKEN_STOOD_DOWN = "LANE_A_UIA_STOOD_DOWN"
TOKEN_UNCLASSIFIED = "LANE_A_LOGOUT_FRAME_UNCLASSIFIED"


@dataclass(frozen=True)
class ButtonClassification:
    """Which of the two HOME-menu buttons a `LogoutVital` frame came from.

    `envelope_vital_count` and `trailing_byte_count` are reported because
    the owner's capture showed the two buttons differing in both, and a
    reader of a console line should be able to tell a lone subcode-3 from a
    bundle without opening the capture file.  They are DESCRIPTION, not the
    discriminator: the code branches on the subcode alone, because the
    capture is n=1 per button and an envelope shape measured once is not a
    rule (the capture letter's own nonclaim says so).
    """

    subcode: int
    button: str
    envelope_vital_count: int
    trailing_byte_count: int

    @property
    def is_character_select(self) -> bool:
        return self.button == BUTTON_CHARACTER_SELECT

    @property
    def is_exit_game(self) -> bool:
        return self.button == BUTTON_EXIT_GAME

    def describe(self) -> str:
        """The fields every console line of this module carries, in order."""

        return "button=%s subcode=%d vitals=%d trailing=%d" % (
            self.button,
            self.subcode,
            self.envelope_vital_count,
            self.trailing_byte_count,
        )

    def console_line(self, token: str) -> str:
        return "%s %s" % (token, self.describe())


@dataclass(frozen=True)
class LogoutButtonNotice:
    """Composed bytes for one on-screen line, plus what they answer.

    `pc` and `frame` are handed back exactly as `gm/say_wire.py` produced
    them; this module never edits a byte of either.
    """

    classification: ButtonClassification
    text: str
    pc: bytes
    frame: bytes

    @property
    def action_label(self) -> str:
        """The name the sender should write beside these bytes.

        Read `ACTION_LABEL_BY_BUTTON`'s comment for why a name that never
        reaches the client is worth a table: it is the field an attended
        ticket greps in three artifacts, and one name for two buttons made
        the owner's two clicks indistinguishable in all three.

        Never raises.  Its one intended caller is chief's `else:` branch,
        which is outside his `try`.
        """

        return ACTION_LABEL_BY_BUTTON.get(
            self.classification.button, UNLABELLED_BUTTON_ACTION_LABEL,
        )

    def console_line(self) -> str:
        return "%s %s text=%s pc=%d frame=%d" % (
            TOKEN_NOTICE_COMPOSED,
            self.classification.describe(),
            self.text,
            len(self.pc),
            len(self.frame),
        )


def _pinned_payload_length(subcode: int) -> int:
    """Length of the LogoutVital payload, read from the module that pins it.

    Not a hand-copied `14`: `classify_logout_attempt` compares the first
    `len(pinned)` bytes, so the trailing count this module reports has to
    follow that same pin or `GT-205`'s `trailing=` field goes quietly wrong
    the day the pin moves (pf-adversary D11).
    """

    return len(logout_hypothesis.LOGOUT_REQUEST_PAYLOADS[subcode])


def classify_parsed(legacy: object, parsed: object) -> ButtonClassification | None:
    """Name the button from the parsed frame `runtime.py` holds, or `None`.

    Never raises for ordinary input; see the module docstring for the
    `BaseException` hole.
    """

    try:
        verdict = logout_hypothesis.classify_logout_attempt(legacy, parsed)
    except Exception:  # noqa: BLE001 - a courtesy must not kill a listener
        return None

    buttons = {
        logout_request_envelope.LOGOUT_SUBCODE_CHARACTER_SELECT: (
            BUTTON_CHARACTER_SELECT
        ),
        logout_request_envelope.LOGOUT_SUBCODE_EXIT_GAME: BUTTON_EXIT_GAME,
    }
    for subcode, button in buttons.items():
        if verdict != "exact_%02d" % (subcode,):
            continue
        try:
            vital_count = int(parsed.vital_count)
            payload_len = len(parsed.nested_payload)
            pinned_len = _pinned_payload_length(subcode)
        except Exception:  # noqa: BLE001 - verdict stands, counters do not
            return None
        return ButtonClassification(
            subcode=subcode,
            button=button,
            envelope_vital_count=vital_count,
            trailing_byte_count=max(0, payload_len - pinned_len),
        )
    return None


def notice_text_for(classification: ButtonClassification | None) -> str | None:
    """What the screen says for this button, or `None` if nothing does.

    One table, read by both the composer and `observe_parsed`, so the line
    printed and the bytes sent can never name two different sentences
    (round `1d6rta`: the same discipline that made the classification a
    single computation in `observe_parsed`).
    """

    if classification is None:
        return None
    return NOTICE_TEXT_BY_BUTTON.get(classification.button)


def make_button_notice(
    legacy: object, parsed: object
) -> LogoutButtonNotice | None:
    """Compose the on-screen receipt for either HOME-menu button, or `None`.

    Renamed from `make_uia_notice` in round `1d6rta`, when the UI-B button
    stopped standing down: a function whose name says UI-A while it answers
    both buttons is the kind of lie a later reader pays for.  Nothing
    outside this module and its tests ever called the old name (`runtime.py`
    calls `observe_parsed` only), so nothing was left pointing at it.

    `None` means "this lane has nothing to send for this click", for every
    reason: an unrecognised frame, a button with no text in the table, a
    withdrawn module, or a composer that refused.  `observe_parsed` is the
    entry point that also says WHICH.
    """

    if production_allowed is not True:
        return None
    classification = classify_parsed(legacy, parsed)
    text = notice_text_for(classification)
    if text is None:
        return None
    try:
        pc, wire_frame = say_wire.make_local_talk_notice_frame(legacy, text)
    except Exception:  # noqa: BLE001 - includes NoticeWireError
        # A courtesy that cannot be composed is dropped, never raised: the
        # same standing rule `gm/chat_command_action.py` applies to the
        # `/speed` refusal notice.
        return None
    return LogoutButtonNotice(
        classification=classification,
        text=text,
        pc=pc,
        frame=wire_frame,
    )


def observe_parsed(
    legacy: object, parsed: object
) -> tuple[LogoutButtonNotice | None, str]:
    """THE ONE CALL `runtime.py`'s 0x1B40 branch is asked to make.

    Returns `(notice_or_None, console_line)`.  The line is always ASCII and
    always names exactly one of five outcomes, so a click that produces no
    bytes still produces a line an attended tester can line up against a
    screenshot:

    * `LANE_A_UIA_NOTICE_COMPOSED` -- a known button, and `notice` carries
                                      bytes.  The `text=` field says which
                                      sentence, so UI-A and UI-B are told
                                      apart on the SAME token rather than
                                      by two tokens.
    * `LANE_A_UIA_STOOD_DOWN`      -- a button this lane recognises but has
                                      no sentence for.  STATED EXACTLY,
                                      because the softer version was wrong
                                      (pf-adversary D5): NO INPUT CAN REACH
                                      THIS LINE TODAY.  `classify_parsed`
                                      can only ever return one of the two
                                      known buttons, and both are in the
                                      text table, so a THIRD button would
                                      land on `UNCLASSIFIED`, not here.
                                      What this branch really guards is the
                                      table itself -- a row deleted or a
                                      button added without a sentence -- and
                                      the one test that reaches it does so
                                      by removing a row on purpose.  It is
                                      the fail-closed default, and it is the
                                      single test standing between this
                                      module and a silent fallback to UI-A's
                                      sentence; it is not a path a player
                                      can walk.
    * `LANE_A_UIA_WITHDRAWN`       -- a known button, but this module is
                                      switched off.
    * `LANE_A_UIA_NOTICE_FAILED`   -- a known button, and the composer
                                      refused (a bug to chase, never this
                                      lane's decision).
    * `LANE_A_LOGOUT_FRAME_UNCLASSIFIED` -- not a LogoutVital this lane
                                      answers; carries the live classifier's
                                      own verdict word so the reason is in
                                      the log, not guessable from silence.

    The classification is computed ONCE and reused for both halves, so the
    line printed and the bytes returned can never describe two different
    reads of the same object.
    """

    classification = classify_parsed(legacy, parsed)
    if classification is None:
        return None, "%s verdict=%s" % (
            TOKEN_UNCLASSIFIED,
            _safe_verdict(legacy, parsed),
        )

    text = notice_text_for(classification)
    if text is None:
        return None, classification.console_line(TOKEN_STOOD_DOWN)

    if production_allowed is not True:
        return None, classification.console_line(TOKEN_WITHDRAWN)

    try:
        pc, wire_frame = say_wire.make_local_talk_notice_frame(legacy, text)
    except Exception:  # noqa: BLE001 - includes NoticeWireError
        return None, classification.console_line(TOKEN_NOTICE_FAILED)

    composed = LogoutButtonNotice(
        classification=classification,
        text=text,
        pc=pc,
        frame=wire_frame,
    )
    return composed, composed.console_line()


def _safe_verdict(legacy: object, parsed: object) -> str:
    """The live classifier's own word for this frame, or why there is none.

    A tester diagnosing `GT-205`'s P3 outcome needs to tell "the frame
    never reached this lane" from "it reached it and was rejected", and a
    bare token cannot (pf-adversary D15).  ASCII, single token, no spaces.
    """

    try:
        verdict = logout_hypothesis.classify_logout_attempt(legacy, parsed)
    except Exception as error:  # noqa: BLE001
        return "seam_%s" % (type(error).__name__,)
    if not isinstance(verdict, str) or not verdict.isascii():
        return "nonascii"
    return verdict.replace(" ", "_")
