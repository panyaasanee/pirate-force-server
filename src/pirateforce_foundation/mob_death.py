"""LANE-B / MOB-DEATH-001: the half where the monster actually dies.

WHAT THIS MODULE IS FOR.  M4 is "hit it, its blood drops, it dies".  The
previous lane-B round built the first half (``mob_combat``) and stopped at a
floor of 1 HP on purpose, because an HP of zero WITHOUT the death timer field
is a state whose client behaviour nobody in this project has observed.  This
module is the second half: it takes a hit outcome that reached zero and
composes the two actor frames the client's own death chain requires, keeps a
register of who is dead, and rebuilds a population without resurrecting them.

    dying frame   <- the SAME identity, HP 0 and death timer STRICTLY POSITIVE
    death frame   <- the SAME identity, HP 0 and death timer <= 0
    register      <- who died, to whom, so nothing re-spawns them alive
    corpse entry  <- what a later re-apply must send for a dead identity

NO FLAG, AND THAT IS THE POINT.  ``production_allowed`` is True.  There is no
scenario id, no dispatch kwarg, no unlock object and no allowlisted profile
anywhere in this file.  The lane that PROVED this chain
(``runtimeres_death_hypothesis``, HYP-PF-023) is a scenario-gated probe whose
BasicAttr bit 0x0080 cannot even be NAMED without a lethal unlock token that
only an allowlisted scenario object hands out - a build the owner boots with no
flags cannot reach one byte of it.  So the encoder is RE-DERIVED here, in
general form, from the same static anchors, and ``tests/test_mob_death.py``
pins the composed bytes against that probe lane's own encoder, byte for byte,
on both sides of the gate.  ~~"pins every constant"~~ is narrower than it
sounded and is now said properly: the constants the probe lane also carries
(the mask bits, the tag, the offset, the two predicate VAs, the two timers)
are cross-pinned against it value by value; the ones only this lane names -
the latch write, the task gate, the task ctor, the animation string and the
three predicate tuples - exist in no probe lane and are pinned by nothing but
this module's own pin document, which is a copy of itself.  Two of them are
printed to a console as facts.  Treat them as transcribed, not derived.
This module imports NO probe lane.

WHAT THE OWNER ACTUALLY APPROVED, AND WHAT IT DOES NOT COVER.  ~~"COO
CHARTER-02 / BUILD-005"~~ was the wrong citation and the adversarial review of
this round caught it: CHARTER-02 authorises this lane to work on the mob
table, aggro, damage and death in parallel, and says nothing about HP 0 or bit
0x0080.  The ruling that lifts a lethal restriction is the owner's of
2026-08-25 18:15 (+07:00), section 3, and it is narrow: it exempts a lethal
frame from HYP-PF-038's stop rule, keeps that lane's production_allowed False,
keeps one shot per connection, keeps identity 0x201F, and then sequences the
work - PROVE THE DEATH LOOP ON 0x201F FIRST, THEN move the target to a real
mob from the game table, and do not merge the two steps into one round.

This module is general and therefore reaches further than that ruling does.
Two things keep it honest rather than quietly past it: its pin and its
:data:`SANCTIONED_FIRST_TARGET_IDENTITY` are 0x201F, the sanctioned target, so
the first wiring the chief writes is step one and not step two; and the letter
for this round puts the widening question to the COO instead of answering it
here.  The restriction this module enforces on itself either way: HP 0 may
only be composed TOGETHER with the timer field, which is exactly the pair the
client's gate reads.

THE CHAIN, AND WHY IT IS TWO FRAMES AND NOT ONE.

* The carrier is the actor-entry collection of ``GSCN_RunTimeProtocolRes``
  (derived change-mask bit 0x02) - the same carrier ``field_mobs`` and
  ``mob_combat.bar_frames`` already use.  ``UpdateAttrVital`` cannot reach the
  death chain at all (its inbound handler contains zero indirect dispatch
  shapes over its whole extent), which is why the bar-refresh carrier is the
  right one and the vital carrier is not.
* AN ACTOR CANNOT BE BORN DEAD.  The inbound handler looks the entry's 64-bit
  identity up: FOUND -> the apply-and-dead-sync path; NOT FOUND -> the spawn,
  which never touches the dead sync.  A field mob a player is hitting is
  already on that player's screen, so the KILL always takes the FOUND branch.
  ~~"this lane always takes the FOUND branch"~~ is false, though, and the
  counterexample is in this module: a client that connects AFTER the kill has
  never seen the identity, so the corpse entry :func:`repopulation_entries`
  hands it takes the spawn, gets no dead sync, and draws a body standing at
  zero HP for that player alone.  Nothing here fixes that - it is written down
  as a nonclaim and it is the chief's to solve at the census, because only the
  census knows a client is new.
* THE TIMER POLARITY IS INVERTED FROM INTUITION.  ``timer > 0`` is the DYING
  side (the latch); ``timer <= 0`` is the DEAD side (the task that builds
  CActorTask_Dead and plays the die animation).  Getting this backwards
  composes two frames that look right and kill nothing.
* THE CLIENT DOES NOT COUNT THE TIMER DOWN.  FACTPACK R102 settled this against
  a live observation: after a dying frame the on-screen number ticks down, but
  ``BasicAttr.f32[+0x58]`` has NO writer anywhere in the image that decrements
  it - not float, not integer - and no display path reads it at all.  The
  number a tester watched belongs to a UI widget counting on its own clock.
  So the field FREEZES at whatever the server last sent.
  ~~"the second frame is REQUIRED: without it the monster falls, shows a
  countdown, and then stands there dying forever"~~ - STRUCK.  GT-029 measured
  the opposite and GT-025 watched to t+240: when the widget's own count
  reaches zero the number simply vanishes and the NPC GOES ON LYING THERE.
  Nothing stands up.  What the frozen field actually means is that the actor's
  stored timer stays 20.0, so the DEAD side of the gate is never satisfied by
  the passage of time; if the death task is worth reaching at all, the server
  is the only thing that can reach it.

WHAT IS CLIENT-OBSERVABLE ALREADY, AND WHAT IS NOT.  READ THIS BEFORE WRITING
ANY SENTENCE ABOUT A CORPSE.  Both frames have already been sent to a real
client through this exact carrier, and the results are split:

* THE FALL IS PROVEN, TWICE OVER.  GT-022 (2026-08-19, run 2, Panya at the
  screen) and GT-025 (repeated twice) sent SPAWN + DYING_LATCH to an
  actor_type 4 NPC standing in Port Royal at identity 0x2001 - a placement the
  client already had on its map, exactly like this lane's monsters.  The NPC
  went from standing to LYING FLAT ON ITS BACK, stayed down at t+10, t+13 and
  t+16, and the client itself wrote a line into chat: "badly wounded and
  fell".  GT-025 is what isolated it: it sent NO death-task frame at all
  (``grep -c DEATH_TASK`` = 0 over the whole console) and got the same fall.
  So the lying pose belongs to the DYING frame.
* THE DEATH TASK'S OWN EFFECT IS NOT PROVEN, AND THIS PROJECT FORBIDS
  CLAIMING IT.  The dead frame has been sent twice and nothing distinguishable
  followed it; ``_F_DIE_000`` has never been observed by anyone here, and
  GT-025's result says in terms that every sentence reading GT-022 as evidence
  of that animation must be withdrawn.  This module therefore sends the frame
  for what is DERIVED (the static gate needs it, and R102 proves the timer
  freezes at 20.0 without it) and claims nothing about what it draws.
* What GT-023 watched escalate all the way to a death window was the LOCAL
  PLAYER's own path, a different actor class, and it is not this lane's
  evidence either.
* [UPDATE, round B_20260827_1637, 2026-08-27] THE NAMED+HOSTILE CASE HAS NOW
  BEEN SENT AND OBSERVED, AND IT DID NOT FALL.  GT-084-R2 (attended,
  OBSERVER_CONFIRMED 2026-08-27T15:52-15:55+07:00, Panya at the screen) hit
  identity 0x201F - named "Tornado Eagle", hostile, actor_type 4, this
  module's own :data:`SANCTIONED_FIRST_TARGET_IDENTITY` - to 0 HP with 5 real
  ActionVital hits, and the dying frame (timer 20.0) then the dead frame
  (700 ms later) both went out on the same carrier GT-022/GT-025 used.  The
  result was NOT the GT-022/GT-025 fall: the corpse froze in a floating pose,
  played no animation, and stopped answering the cursor as an actor at all
  (stayed frozen until logout).  Single-click also got a red outline + red
  lock arrows but NO select-target UI panel (contrast GT-045 v3, a different
  actor, which got one).  So the fall documented above as "PROVEN, TWICE
  OVER" is proven only for the NAMELESS/FACTIONLESS body GT-022/GT-025 used -
  the two-frame chain's client-side effect is confirmed BODY-DEPENDENT, not
  merely a property of actor_type 4 the way the nonclaims below previously
  flagged it as an open question.  RE-107 (CLIENT_RE_QUEUE.md, opened this
  round) asks which field/frame actually drives the fall-vs-freeze branch;
  RE-108 asks what the select-target panel needs.  This module is UNCHANGED
  pending those answers - no guess-fix.  See
  ``notes_to_chief/20260827_1620_GT084R2-RESULT-PASS-hostile-kill-full-wire-
  but-corpse-freezes-no-target-panel.md`` for the full attended account.

WHAT THE PLAYER SEES THAT THEY DID NOT SEE YESTERDAY.  Yesterday a monster a
player fought converged to 1 HP and stayed there forever, and the server
answered every further hit with silence - that was this lane's own nonclaim.
Today the last hit takes it to zero and this module hands back the frames that
drop it, plus the register that keeps it down through a re-apply.
[PROPOSED, not measured] once the chief writes the wiring line, a monster in
Port Royal that a player hits enough times falls flat and stays there on a
build booted with no flags - the state GT-022 and GT-025 watched, reached for
the first time by HITTING something rather than by typing a chat trigger.
It is PROPOSED and not MEASURED for two named reasons: nobody has yet observed
a real attack input producing the EA7D ActionVital ``mob_combat`` reads, and
nobody has watched this lane's own body - named AND hostile AND at zero - land
on a screen at all.

[UPDATE, round B_20260827_1637, 2026-08-27]: both named reasons are now
MEASURED, and the measurement is mixed.  GT-084-R2 sent 5 real ActionVital
hits from a real attack input (first reason resolved: the wire path is real).
The body's landing has also now been watched (second reason resolved), but
~~"falls flat and stays there"~~ did NOT hold - it froze floating instead, so
"stays there" is true and "falls flat" is false.  See the CLIENT-OBSERVABLE
section above for the full account and RE-107/RE-108 for what is still open.

NOTHING IS INSTALLED.  No socket, no clock, no randomness, no database, no
global state, no import-time side effect.  Every function is a pure function of
its arguments and every state object is a frozen dataclass.  Contract breaches
raise :class:`MobDeathContractError` with a NAMED reason.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
import struct
from typing import Any

from . import field_mob_tables
from . import field_mob_tables_bg0002
from . import field_mobs
from . import mob_combat
from . import world_population
from .field_mobs import FieldMob
from .mob_combat import HitOutcome
from .population import (
    FULL_MOVEMENT_MASK,
    MOVEMENT_ATTR_ID,
    NPC_ATTR_ID,
    NPC_STYLE_ACTOR_TYPE,
    SCENE_ID,
    SCENE_SEQUENCE,
)


# Convention markers only; nothing in this tree branches on them.
production_allowed = True
test_only = False

MOB_DEATH_MILESTONE = "MOB-DEATH-001"
MOB_DEATH_BUILD_ORDER = "M4 second half"
MOB_DEATH_LANE = "B_COMBAT"

# COO-DECISION 2026-08-27T22:49+07:00 (answering LANE-B-ASK-COO 2026-08-27
# 21:53+07:00, notes_to_chief/20260827_2153_LANE-B-ASK-COO-actor-identity-
# needs-a-scene-term.md): FieldMob.actor_identity is 0x2000 + placement_index
# + 1 with NO scene term (field_mobs.cross_scene_identity_collisions() finds
# 4 real bg0001 x Bg0002 collisions today, e.g. placement 58 -> 0x203B for
# BOTH bg0001's Jungle Big Tiger and Bg0002's Fighting Fish soldier).  The
# COO's chosen fix is option 3 of 3 offered: do NOT touch that wire formula
# (options 1/2 would move pins already proven against bg0001) -- instead key
# this SERVER-SIDE register by the pair (scene, actor_identity), so two
# different mobs in two different scenes that happen to share a wire
# identity die independently.  DEFAULT_SCENE exists so every call site that
# predates this round (and every test built on the single scene this project
# has ever booted) keeps working with no change: bg0001 is the only scene a
# session has ever loaded, so "no scene given" and "bg0001" are the same
# fact today.  A caller that HAS a FieldMob in hand should pass mob.scene
# explicitly rather than lean on this default -- see kill(), live_roster(),
# repopulation_entries() and corpse_override() below, all updated this round.
DEFAULT_SCENE = field_mob_tables.SCENE

# The one line this lane owes the chief, written where a reader of the module
# finds it rather than only in a PR body.
MOB_DEATH_WIRING = (
    "runtime.py: after mob_combat.commit_step accepts a step whose "
    "step.death_due is True - the CombatStep property, NOT "
    "step.outcome.death_due, which is also True for a hit on something "
    "already dead - call mob_death.kill(legacy, mob, step.outcome, register); "
    "commit it with mob_death.commit_death(register_now, death_step) and send "
    "nothing if that is refused; then send step.frames (the announce), then "
    "death_step.dying_frame, then death_step.dead_frame after "
    "death_step.hold_ms; keep the committed register and hand "
    "mob_death.corpse_override(legacy, roster, register, ledger=ledger) to "
    "whatever builds this scene's census, so the rebuild replaces those "
    "identities' entries rather than re-sending them alive - PASS THE LEDGER, "
    "or the rebuild heals every wounded monster back to its ceiling as well."
)
# The owner's own sequencing, ENFORCED rather than described, because the
# first version of this constant appeared only in prose, a pin and a console
# line - it reported, and reporting is not a gate.
#
# The ruling of 2026-08-25 18:15 (+07:00), section 3, lifts the lethal-frame
# restriction and then says in terms: prove the death loop on identity 0x201F
# FIRST, and only THEN move the target to a real mob from the game table - the
# two steps may not be merged into one round.  So :func:`kill` REFUSES any
# other identity unless the caller passes ``widened=`` with the name of the
# ruling that widened it.  That is not a flag in the sense this lane refuses:
# the sanctioned target works with nothing passed, on a build booted with no
# arguments.  It is a lock on the SCOPE the owner set, held where a wiring
# line cannot walk past it by accident.
SANCTIONED_FIRST_TARGET_IDENTITY = 0x201F
# ADDED round 8ftmbx.  The identity above is a wire number with no scene in
# it, and after COO-DECISION 2026-08-29T00:41+07:00 withdrew bg0001 placement
# 30 there is no shipped actor behind it at all -- so on its own it names an
# INDEX that every scene has, not a monster.  PANYA-RULINGS-FOUR named a
# bg0001 actor; this records the half of that sentence the wire format cannot
# carry, so the bypass cannot be inherited by the next scene wired.
SANCTIONED_FIRST_TARGET_SCENE = field_mob_tables.SCENE
SANCTIONING_RULING = "PANYA-RULINGS-FOUR 2026-08-25 18:15 +07:00 section 3"

# A ruling that widens the scope past SANCTIONED_FIRST_TARGET_IDENTITY names
# ONE identity, not "whatever a caller passes this string for" - but a caller
# that hardcodes the ruling's own name at a SINGLE call site (what
# runtime.py's roster kill site USED TO do, before round j0u64p: one
# ``mob_death.kill(...)`` call reached by every roster identity that dies,
# passing one literal) could not tell, from the string alone, which mob
# the ruling actually named.  pf-adversary (round 67jejl) proved the gap:
# the literal one-line wiring COO-DECISION 20260827_0955's own text asks for
# would authorise a kill on any of the OTHER twelve roster identities that
# ruling itself calls still-misplaced data (Tornado Eagle / Toxic Vine /
# Fighting Fish, mis-attributed from Prison Exile), the moment the line
# existed at all, because ``widened`` only had to be non-empty.
#
# This dict pins every ruling this module has actually been given to the
# MOBS template id(s) (``n_ID``, carried on :class:`field_mobs.FieldMob` as
# ``template_id``) it names, so :func:`kill` can hold the line even when the
# caller passes the RIGHT widened= string for the WRONG monster - and
# :func:`kill` FAILS CLOSED on the string itself: a ``widened`` value that is
# not an exact key here is refused, the same as an empty one, because
# pf-adversary (same round) proved by execution that treating an unrecognised
# string as pre-fix-legal reopens the identical hole through a PARAPHRASE or
# a mistranscription of a real ruling - arguably the likelier real mistake,
# since chief transcribes this string out of a notes_to_chief letter by hand
# rather than importing it.  Every FUTURE widening ruling this lane is given
# must be added here, by its exact quoted name, before any caller can use it
# - there is no leniency fallback for a ruling not yet catalogued.
WIDENING_RULINGS: dict[str, frozenset[int]] = {
    "COO-DECISION widen-death-scope-916-training-iron-man "
    "2026-08-27T09:55+07:00 (ref PANYA-DECISION 2026-08-27T09:50+07:00 "
    "section 3, supersedes COO 0954)": frozenset({916}),
    # COO-DECISION 2026-08-27T13:50+07:00 (notes_to_chief/20260827_1350_
    # COO-DECISION-widen-death-scope-bg0001-full-roster-approved.md),
    # answering LANE-B-ASK-COO 2026-08-27 15:00 (round t48epl): approves
    # stage two, all 13 real MOBS-table field mobs in bg0001 (not just
    # SANCTIONED_FIRST_TARGET_IDENTITY). The letter tells chief to pass
    # this EXACT string as widened= on runtime.py's mob_death.kill() call
    # site (pf-adversary, this round: the letter's own cited line number
    # is already stale -- as of this round that call site passes NO
    # widened= argument at all, so "the string chief adds", not "the
    # string chief changes"; do not trust a hardcoded line number here,
    # re-find the call site by name). The template id set below is the
    # distinct template_id values of field_mobs.load_roster()'s 13
    # entries as of this round (31 Tornado Eagle, 34/35 Fighting Fish,
    # 60 Jungle Big Tiger, 61 Toxic Vine, 62 Ancient Civilization Alert
    # Weapon, 65 Ward Apes, 94 An Gebo Little Firebird, 97 Mutant Green
    # Eagle x4 identities, 103 Orc Chief), re-derived from the roster
    # itself in tests/test_mob_death.py rather than hand-copied twice.
    #
    # [OPEN RISK -- pf-adversary, round 67jejl-era] [PARTIALLY CLOSED, this
    # round, PANYA-DECISION 2026-08-27T20:10+07:00 "M1-P" item 3] this
    # ruling is NAMED for bg0001 and enforced by template_id AS BEFORE, but
    # is now ALSO checked by scene: WIDENING_RULING_SCENES below ties this
    # exact key to field_mob_tables.SCENE ("bg0001"), and kill() refuses a
    # mob whose own .scene disagrees, even when its template_id is also a
    # member of this set. This closes the risk this comment used to
    # describe only as theoretical: Bg0002's own mined roster
    # (field_mob_tables_bg0002.HOSTILE_PLACEMENTS, loaded via
    # field_mobs.load_roster(scene=field_mobs.BG0002_SCENE)) really does
    # share 4 of these 10 template ids (31, 34, 35, 103), and a Bg0002 mob
    # is now refused here rather than silently authorised. What is NOT
    # closed: FieldMob.scene is a plain string a hand-built stand-in could
    # still set wrong -- see field_mobs.assert_single_scene_tables' own
    # "WHAT THIS DOES NOT COVER" paragraph, which says so explicitly rather
    # than implying this is airtight.
    # ROUND szdkgs: ~~97~~ -> 916, and the first draft of this round got it
    # WRONG in a way pf-adversary caught by execution.  That draft removed 97
    # and added nothing, on the principle "do not extend a COO ruling to a
    # template it never saw".  The principle is right; the application was a
    # REGRESSION: ``runtime.py``'s only roster kill site passes THIS string
    # and nothing else, so the four placements that used to die stopped being
    # killable at all -- a dummy stuck at 0 HP forever, with yesterday's
    # behaviour lost, which is worse than either reading of the ruling.
    # 916 is restored to this set on the ruling's own words: COO 2026-08-27
    # 13:50 approves "all 13 real MOBS-table field mobs in bg0001", i.e. it
    # names THE ROSTER, and the set below has always been the roster's own
    # distinct template ids (re-derived in tests/test_mob_death.py, never
    # hand-copied).  This does not enlarge what COO authorised: killing 916 is
    # ALREADY granted outright by the 2026-08-27T09:55 ruling above, so the
    # union of permissions is unchanged and only the string that carries it
    # moves.  What is still unanswered, and is written up as this round's open
    # question: kill() takes ONE widened= string and a roster can now need
    # two, so a lane whose roster stops fitting through one string has to ask
    # chief for its file.  Named, not hidden.
    # ROUND 8ftmbx: ~~{31, 34, 35, 60, 61, 62, 65, 94, 103, 916}~~ -> {916}.
    # The set has always been "the distinct template ids of bg0001's own
    # roster", re-derived from the roster in tests rather than hand-copied,
    # and COO-RULING-20260827-1350 names THE ROSTER ("all 13 real MOBS-table
    # field mobs in bg0001").  COO-DECISION 2026-08-29T00:41+07:00 withdrew
    # the nine set-number rows, so that roster is now the four Training Iron
    # Man placements and nothing else.  The nine templates dropped here were
    # already unreachable through this key -- WIDENING_RULING_SCENES ties it
    # to scene bg0001, and no bg0001 mob carries them any more -- so this
    # narrows dead authorisation, not live behaviour.
    # NOT the szdkgs mistake in reverse: that draft removed the ONLY template
    # the live roster still had (97) and made four shipped dummies unkillable.
    # 916 is what the live roster has, and 916 is what stays.
    "COO-RULING-20260827-1350 widen-death-scope-bg0001": frozenset(
        {916}
    ),
    # PANYA-DECISION 2026-08-27T20:10+07:00 ("M1-P" item 3, notes_to_chief/
    # 20260827_2010_PANYA-DECISION-pause-M2-M1-identity-first-Prison-Exile-
    # Bg0002-MOBSET-equals-nID.md) + its ADDENDUM 20:18 (owner: "nap wa pen
    # khao dee tham loei" / "count it as good news, do it"): widen death
    # scope to cover Bg0002's own hostile roster.  The set below is
    # EXACTLY what tools/pf_mine_scene_mob_roster.py selects for Bg0002
    # (field_mob_tables_bg0002.HOSTILE_PLACEMENTS' distinct template_ids),
    # not a hand-guessed slice of the 27-35 census block the decision
    # letter names: templates 27-30, 32 and 33 all fail the mining tool's
    # outfit-unambiguous rule (their CONSTDATA_TH__MOBS.s_OUTFIT is a
    # multi-variant ";"-joined list) and so are NOT members of this ruling,
    # even though several of them (27 included) pass the RANK+AI_COMBAT
    # hostility predicate on their own. Re-derived from
    # field_mob_tables_bg0002 itself in tests/test_mob_death.py rather than
    # hand-copied twice, the same discipline the bg0001 ruling above is
    # held to. Template 27 (Mountain Deer), the ADDENDUM's separately-named
    # DIAG-001 body, is covered by ITS OWN ruling below, not folded into
    # this one -- see that entry's comment for why.  Tied to
    # field_mob_tables_bg0002.SCENE ("Bg0002") in WIDENING_RULING_SCENES:
    # a bg0001 mob carrying one of these same four template ids (31, 34, 35
    # and 103 all are) is refused here even though the OTHER ruling above
    # would authorise it, because that mob's own .scene is "bg0001", not
    # "Bg0002" -- the exact reverse-direction hazard the task that added
    # this entry named explicitly.
    "PANYA-DECISION 2026-08-27T20:10+07:00 (ADDENDUM 20:18) "
    "widen-death-scope-bg0002": frozenset({31, 34, 35, 103}),
    # Same letter, same timestamp, ADDENDUM 20:18's SEPARATE sentence:
    # the owner named Mountain Deer (MOBS n_ID 27) as the body for all five
    # GT-114/DIAG-001 diagnostic objects
    # (mob_diag_multi_object.DIAG_MOUNTAIN_DEER_TEMPLATE_ID), superseding
    # that module's own earlier Jungle Big Tiger (template 60) pick.
    # Template 27 is deliberately NOT a member of the ruling above: it
    # fails the SAME outfit-unambiguous rule that excludes it from Bg0002's
    # own mined roster (s_OUTFIT is the two-variant list
    # "M005_000_000_SP1;M005_000_000_SP2"), so a caller must not be able to
    # infer "Bg0002's ruling covers Mountain Deer" from template proximity
    # to 31/34/35 alone -- it does not, and this is why it gets its own
    # entry rather than being added to the set above.  Tied to
    # field_mob_tables.SCENE ("bg0001") in WIDENING_RULING_SCENES, NOT
    # "Bg0002": GT-114's five diagnostic objects are placed at the owner's
    # bg0001 city-center test point
    # (mob_diag_multi_object.DIAG_CENTER_X/Y), not at any real Bg0002
    # placement, so the scene tag records WHERE THE KILL HAPPENS, not
    # which scene's MOBS row the body's stats were mined from.
    "PANYA-DECISION 2026-08-27T20:10+07:00 (ADDENDUM 20:18) "
    "diag-mountain-deer-template-27": frozenset({27}),
    # COO-DECISION 2026-09-01T10:46+07:00 (notes_to_chief/20260901_1046_
    # COO-DECISION-bg0015-death-ruling-option-b-six-templates-carlos-held-
    # out.md), answering LANE-B-PROPOSAL 2026-09-01T09:51+07:00 (round
    # vzhc6s, mob_death_bg0015_ruling_proposal.py): OPTION B of that
    # proposal's three -- six of Bg0015's seven candidate templates, the
    # ones the same three-step methodology bg0001/Bg0002 already used
    # (steps 1-3 of that module's own docstring) generalises to cleanly.
    # Template 924 ("Carlos") is DELIBERATELY EXCLUDED, not omitted by
    # oversight: it is the one row two earlier letters already flagged as
    # an open content question (pf_bridge/notes_to_chief/20260829_0739_
    # LANE-A-STATUS-... item 4, and this lane's own scene_identity_rule.py
    # docstring point 8: "It may well be a real boss; nobody has looked."),
    # and this ruling does not answer that question -- see
    # mob_death_bg0015_ruling_proposal.option_b_roster_minus_carlos's own
    # docstring for why Mountain Deer's carve-out is not a precedent here.
    # The six ids below are exactly that function's answer, re-derived from
    # Bg0015's own mined roster in tests/test_mob_death_bg0015_ruling_
    # proposal.py rather than hand-copied a second time.
    # REGISTERING THIS ENTRY DOES NOT OPEN GATE 1: the letter's own words
    # are that registering a ruling and registering Bg0015 into
    # field_mobs._SCENE_TABLE_MODULES are "two separate matters" -- that
    # gate (COO-DECISION 2026-09-01T08:47+07:00 item (c)) stays locked.
    "COO-RULING-20260901-1046": frozenset({343, 345, 348, 350, 353, 355}),
}

# Companion to WIDENING_RULINGS, added this round (PANYA-DECISION
# 2026-08-27T20:10+07:00 "M1-P" item 3) rather than changing that dict's own
# value shape, which several existing tests and the 916 ruling's own
# machinery (registered_widening() in tests/test_mob_death.py) index as a
# bare frozenset.  A ruling with an entry HERE additionally requires
# ``mob.scene`` (FieldMob's own new field) to equal the scene named, on top
# of the template_id check WIDENING_RULINGS already does; a ruling with NO
# entry here (the 916 Training Iron Man ruling, which ~~names no real scene at
# all~~ -- ROUND szdkgs: 916 has FOUR real bg0001 placements now, so that
# sentence is false; the ruling still carries no scene tie in this dict, which
# is a hole worth closing in the round that migrates the rest of the roster
# rather than in the round that discovered it -- it is a training-dummy stand-in with no placement anywhere) is
# UNAFFECTED, exactly as before this round.  This is the "lighter" of the
# two options COO-DECISION 2026-08-27T14:41+07:00 named (a scene-scoped
# ruling NAME plus a call-site check, not a scene field threaded through
# every existing WIDENING_RULINGS value) -- chosen because the two rulings
# that actually need it (the bg0001 one and the new Bg0002 one) have covered
# template sets that OVERLAP (31, 34, 35, 103 are in both), so the
# ruling-name string alone cannot disambiguate them and pf-adversary's own
# 67jejl-round finding ("an unnamed value passes a named check") would
# otherwise re-open across the scene boundary the moment Bg0002 rows reach
# kill() at all -- which, as of field_mobs.load_roster(scene=...), they now
# can.
#
# [CONFIRMED, not just this lane's assumption] pf-adversary (round y7koj9)
# flagged an authority gap here before this was found: this round gives
# FieldMob a `scene` field (field_mobs.py) -- literally the thing
# COO-DECISION 2026-08-27T14:41+07:00 named as "option 1" and said not to do
# yet, deferred to "after M4, when lane A/B actually needs a second scene".
# PANYA-DECISION 2026-08-27T20:10+07:00 item 3 alone ("widen the
# assert_single_scene_tables guard, don't disable it") does not by itself
# name a FieldMob.scene field or this dict. What closes the gap: COO-DECISION
# 2026-08-27T20:45+07:00 (notes_to_chief/20260827_2045_COO-DECISION-
# widening-guard-move-into-kill-closes-gap.md, answering chief's own
# 15:15 CHIEF-STATUS letter that first named this exact gap) explicitly
# picks "add a scene field to check in kill(), comparing mob.template_id /
# the mob's own scene" as this round's M1-P item-3 work, not a separate
# round -- so this is COO-authorised, not merely this lane's own reading of
# the owner's authority. Kept as a dated citation trail rather than deleted,
# per this project's own rule against silently erasing what a round actually
# reasoned through.
WIDENING_RULING_SCENES: dict[str, str] = {
    # ROUND 8ftmbx: the 916 ruling gets its scene tie, and this is the round
    # the paragraph above named for it ("a hole worth closing in the round
    # that migrates the rest of the roster").  pf-adversary (D4) proved by
    # execution that without it a hand-built FieldMob carrying template 916
    # and scene "Bg0002" was killed under a ruling that names bg0001 -- and
    # this round newly routes the shipped death pin through that same ruling
    # (PIN_WIDENING_RULING), so leaving it untied would have been shipping a
    # document produced under an authorisation nobody scoped.  916 is a
    # generic training target; any future scene that mines one would have
    # inherited an unconditional kill from a bg0001 letter.
    # This TIGHTENS: it can only refuse kills that used to be allowed, and
    # every kill the shipped roster performs is a bg0001 one.
    "COO-DECISION widen-death-scope-916-training-iron-man "
    "2026-08-27T09:55+07:00 (ref PANYA-DECISION 2026-08-27T09:50+07:00 "
    "section 3, supersedes COO 0954)": field_mob_tables.SCENE,
    "COO-RULING-20260827-1350 widen-death-scope-bg0001": field_mob_tables.SCENE,
    "PANYA-DECISION 2026-08-27T20:10+07:00 (ADDENDUM 20:18) "
    "widen-death-scope-bg0002": field_mob_tables_bg0002.SCENE,
    "PANYA-DECISION 2026-08-27T20:10+07:00 (ADDENDUM 20:18) "
    "diag-mountain-deer-template-27": field_mob_tables.SCENE,
    # Tied to Bg0015 -- a bg0001/Bg0002 mob sharing one of these six
    # template ids by coincidence (none do at HEAD) would be refused here,
    # the same reverse-direction hazard every other entry in this dict
    # already guards against.
    #
    # THE LITERAL "Bg0015" IS WRITTEN OUT, NOT IMPORTED, ON PURPOSE: this
    # scene's own raw table module has exactly one approved importer under
    # ``src/`` (``field_mob_hostile_bg0015.py``, COO-DECISION
    # 2026-08-31T16:48+07:00's "layer 1" unlock), enforced by an
    # AST+literal sweep this module deliberately stays off the allowlist
    # of.  Cross-checked instead of merely typed and hoped: every row
    # ``field_mob_hostile_bg0015.scene14_hostile_roster()`` returns already
    # carries this exact string as its ``.scene`` (threaded through from
    # the raw table by ``field_mobs._parse_hostile_placements``, the
    # approved path), and ``tests/test_mob_death_bg0015_ruling_proposal.py``
    # asserts ``ruling_for()`` accepts those real rows under this exact key.
    "COO-RULING-20260901-1046": "Bg0015",
}


def rulings_covering(mob: FieldMob) -> tuple[str, ...]:
    """Every registered ruling that authorises killing ``mob``, both axes.

    ROUND j0u64p.  The same two questions :func:`kill` asks -- is this mob's
    template in the ruling's covered set, and if the ruling is tied to a
    scene, is this mob in it.  This is a SECOND expression of them, not a
    shared one: ``kill`` answers about ONE named letter and owes its caller a
    refusal saying why THAT letter declined, so it looks the name up directly
    and never sweeps the table; this function sweeps the table and names no
    refusal.  Neither can be written in terms of the other without one of them
    losing what it is for.  Two expressions of one rule is how a gate and its
    derivation drift apart, so ``tests/test_mob_death_wired_widening.py``
    holds them to the same answer by execution -- over every shipped row
    crossed with every registered ruling, AND over constructed rows that
    exercise the scene axis, which no shipped row does today (pf-adversary,
    this round: the scene branch below never fires on the live rosters, so a
    crossing of shipped rows alone could not have caught a scene-axis drift).

    THE SANCTIONED BYPASS IS DELIBERATELY NOT MODELLED HERE, and callers must
    ask :func:`ruling_for` rather than this function for that reason.
    ``kill`` lets ``SANCTIONED_FIRST_TARGET_IDENTITY`` in its own scene
    through with no ``widened=`` at all, so for that one actor this function
    answers ``()`` while ``kill`` answers "killed".  MEASURED, so the guard is
    not mistaken for the reason a test passes: that identity is in NO shipped
    roster today (COO-DECISION 2026-08-29T00:41+07:00 withdrew bg0001
    placement 30), so the equality test's exclusion of it currently excludes
    nothing.  It is future-proofing for the day that row returns, and the
    disagreement it would then cover is proven on a constructed actor instead.
    """
    covering: list[str] = []
    for name, templates in WIDENING_RULINGS.items():
        if mob.template_id not in templates:
            continue
        required_scene = WIDENING_RULING_SCENES.get(name)
        if required_scene is not None and mob.scene != required_scene:
            continue
        covering.append(name)
    return tuple(covering)


#: The two shapes a letter's own timestamp is written in inside a ruling
#: NAME, both of which are already in ``WIDENING_RULINGS`` at HEAD: the ISO
#: one the letters themselves carry (``2026-08-27T09:55+07:00``) and the
#: compact one a letter id carries (``COO-RULING-20260827-1350``).  Ordered by
#: nothing: :func:`ruling_registered_at` takes whichever match starts
#: EARLIEST in the name, not whichever pattern is listed first.
_RULING_TIMESTAMP_PATTERNS = (
    re.compile(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})"),
    re.compile(r"(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})"),
)


def _is_a_real_minute(
        year: int, month: int, day: int, hour: int, minute: int) -> bool:
    """Calendar validation, written out rather than imported.

    ``datetime`` is on this module's forbidden-import list
    (``tests/test_mob_death.py::test_nothing_is_installed_by_importing_this
    _module``) and the reason is not stylistic: nothing here may be able to
    read a clock, so a death frame can never depend on when it was composed.
    Validating a STRING needs no clock, so the calendar is spelled out here
    instead of reaching for the module that also carries ``now()``.
    """
    if not 1 <= month <= 12:
        return False
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    lengths = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    return (
        1 <= day <= lengths[month - 1]
        and 0 <= hour <= 23
        and 0 <= minute <= 59
    )


def ruling_registered_at(name: str) -> str:
    """When the letter named ``name`` was written, as sortable ``YYYYMMDDHHMM``.

    ROUND uq2lxw, COO-DECISION 2026-08-29T08:48+07:00 item 1 (b).  This is the
    tie-break term :func:`ruling_for` uses when two letters cover one monster
    with equally narrow template sets, replacing the sorted NAME this lane had
    assumed.  COO's reason, in that letter's own words: name-sorting means a
    letter written TOMORROW can move the provenance of every kill that already
    happened under a letter written yesterday, and "provenance you can
    retroactively edit is not provenance".

    THE FIRST TIMESTAMP IN THE NAME IS THE LETTER'S OWN, and that is a
    registration convention this function DEPENDS on rather than one it can
    verify.  The 916 ruling's name carries two (``2026-08-27T09:55+07:00``,
    its own, then ``(ref PANYA-DECISION 2026-08-27T09:50+07:00 ...)``, the
    older letter it cites), and taking the earliest MATCH POSITION -- not the
    earliest TIME -- is what picks the letter's own.  A ruling registered with
    the citation first would be ordered by the cited letter's clock;
    ``tests/test_mob_death_wired_widening.py`` pins the convention on every
    shipped ruling so a name written the other way round is caught in CI, not
    in a kill.

    THAT RULE HAS TWO HALVES AND ONLY ONE OF THEM FIRES ON THE SHIPPED NAMES
    (pf-adversary, this round: two mutants survived here).  Within ONE
    pattern, ``re.search`` is already leftmost -- that is what resolves the
    916 name's own 09:55 over its cited 09:50, and it needs nothing from the
    loop below.  The loop's own comparison decides only when the TWO patterns
    both match one name, which no registered ruling does today; it is
    exercised on constructed names instead
    (``test_the_position_rule_and_the_earliest_time_rule_are_not_the_same``),
    because a term that has never executed is a term nobody has checked.

    THE UTC OFFSET IS NOT READ, and this is a house convention rather than a
    property: both patterns stop before ``+07:00``, so two letters naming the
    same instant in different offsets would order by wall clock.  Every
    letter this project writes is ``+07:00`` (ADDENDUM v2 section C makes the
    stamp come from one command), so the convention holds today and nothing
    here enforces it.

    Raises rather than sorting a nameless letter last: a ruling with no
    timestamp cannot be ordered at all, and a missing sort key silently
    becomes "first" or "last" depending on the comparison, which is how a
    provenance rule turns into a coin toss.
    """
    if not isinstance(name, str):
        raise MobDeathContractError(
            REFUSE_RULING_NAME_HAS_NO_TIMESTAMP,
            "a ruling name must be text, not %r" % type(name).__name__)
    earliest: tuple[int, tuple[str, ...]] | None = None
    for pattern in _RULING_TIMESTAMP_PATTERNS:
        found = pattern.search(name)
        if found is None:
            continue
        if earliest is None or found.start() < earliest[0]:
            earliest = (found.start(), found.groups())
    if earliest is None:
        raise MobDeathContractError(
            REFUSE_RULING_NAME_HAS_NO_TIMESTAMP,
            "ruling %r carries no letter timestamp (expected either "
            "YYYY-MM-DDTHH:MM or YYYYMMDD-HHMM in the name), so there is no "
            "way to say which of two letters was registered first - "
            "COO-DECISION 2026-08-29T08:48+07:00 item 1(b)" % name)
    stamp = "".join(earliest[1])
    if not _is_a_real_minute(*(int(part) for part in earliest[1])):
        raise MobDeathContractError(
            REFUSE_RULING_NAME_HAS_NO_TIMESTAMP,
            "ruling %r carries %r where a letter timestamp should be, and it "
            "is not a real date and time" % (name, stamp))
    return stamp


def ruling_for(mob: FieldMob) -> str | None:
    """The ONE ruling name a kill on ``mob`` should travel under, or None.

    ROUND j0u64p.  This is for THE ROSTER KILL SITE -- ``runtime.py``'s
    ``mob_death.kill()`` call in the ``else`` branch at ~4168, the one every
    field-roster monster dies through.  It hardcodes ONE ruling string,
    bg0001's, which is the wrong letter for the 17 rows Bg0002 ships and will
    be the wrong letter again for a third scene.  This function answers what a
    literal cannot: given this monster, which letter authorises killing it.

    NOT FOR THE DIAGNOSTIC CALL SITE, and this is a scope line, not a caveat.
    ``runtime.py`` reaches a kill through ``diag_multi_object_wiring.
    death_dispatch`` as well, and that path carries its own
    ``DIAG_WIDENED_RULING`` on the stated design position that it "does not
    choose a ruling and must not".  This function does not override that;
    nothing in this round asks that lane to adopt it (pf-adversary, this
    round: the first draft said "ONE call site", which is false -- there are
    two, and only one of them has the problem this solves).

    MEASURED, AND THE MEASUREMENT MATTERS FOR HOW THIS IS READ (pf-adversary,
    this round, breaking this round's own first draft): ``kill`` ALREADY
    authorises every monster the server ships -- the Bg0002 letter has been
    registered since round y7koj9 and covers all 17 of that scene's rows.
    Nothing here is a fix to a broken gate, and the gate is not widened by one
    byte.  What is removed is a hardcoded per-scene argument in a file this
    lane does not own, replaced by a value derived from the world itself.
    AND THE 17 ROWS DO NOT REACH THAT CALL SITE AT ALL TODAY: ``runtime.py``
    loads one scene's roster, so ``mob_combat`` refuses a Bg0002 target before
    this module is consulted.  "The wrong letter for 17 rows" is a statement
    about an argument, not about anything a player has seen.

    Returns ``None`` for the sanctioned first target in its own scene, which
    :func:`kill` admits with no ruling at all -- so ``widened=ruling_for(mob)``
    is the correct argument for EVERY mob, including that one, and a caller
    never needs a special case.

    WHEN TWO LETTERS COVER THE SAME MONSTER: narrower covered set first, then
    the letter registered EARLIER (:func:`ruling_registered_at`), then sorted
    name.  ~~[ASSUMPTION OF LANE B - AWAITING COO] ... narrower covered set
    first, then sorted name~~ IS STRUCK AND ANSWERED: COO-DECISION
    2026-08-29T08:48+07:00 item 1 rules (a) narrower set, (b) tie to the older
    letter by the timestamp IN ITS NAME, (c) sorted name only when two letters
    carry the same timestamp -- and refuses the name sort as the deciding
    term, because it lets a letter written tomorrow move the provenance of
    every kill already recorded under one written yesterday.
    MEASURED ON THE SHIPPED ROSTER, ROUND uq2lxw, so the change is not read as
    doing more than it does: bg0001's two letters BOTH carry
    ``frozenset({916})`` (round 8ftmbx narrowed the roster letter), so the
    ``len`` term separates nothing at HEAD and the new term is what decides.
    It decides the SAME WAY the name sort did -- 2026-08-27T09:55 is both the
    alphabetically first name and the older letter -- so every shipped row's
    answer, and ``PIN_WIDENING_RULING``, are byte-identical before and after
    this round.  What changed is which future letter can move them: under the
    old rule a new letter over template 916 named ``AAA...`` took the pin;
    under this one it cannot, and only a letter registered BEFORE
    2026-08-27T09:55 could.  ``test_a_newer_letter_does_not_move_an_older
    _kills_provenance`` is what says so.

    AND THE SCOPE OF THAT SENTENCE, WHICH A READER WILL OTHERWISE OVERSTATE
    (pf-adversary, this round).  "Them" is this function's own answers and
    ``PIN_WIDENING_RULING`` -- NOT the letter a kill on the live server is
    recorded under.  At the time this docstring was first written, this
    function had NO production caller: ``runtime.py``'s roster kill site
    passed the bg0001 literal, which this function disagreed with on every
    shipped row (it answers the 09:55 letter; the call site passed the 13:50
    one).  Per COO-DECISION 2026-08-29T08:48+07:00 item 3, the roster kill
    site now calls ``widened=mob_death.ruling_for(mob)`` directly
    (``runtime.py``, the ``else`` branch that reaches ``mob_death.kill()``) --
    so the disagreement this paragraph describes is history, not the current
    wiring.  ``test_the_literal_the_call_site_hardcodes_is_the_wrong_letter``
    (``tests/test_mob_death_wired_widening.py``) still measures the OLD
    literal on purpose, as the before-picture that shows why the derived
    lookup was needed -- it is not evidence the old literal is still wired.
    """
    _require_mob(mob)
    if (
        mob.actor_identity == SANCTIONED_FIRST_TARGET_IDENTITY
        and mob.scene == SANCTIONED_FIRST_TARGET_SCENE
    ):
        return None
    covering = rulings_covering(mob)
    if not covering:
        raise MobDeathContractError(
            REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE,
            "no registered ruling covers identity 0x%X (template %d, scene "
            "%r), so there is no letter a kill on it could travel under - see "
            "describe_widening_coverage(), and ask the owner before shipping "
            "a monster nobody authorised killing" % (
                mob.actor_identity, mob.template_id, mob.scene),
        )
    return sorted(
        covering,
        key=lambda name: (
            len(WIDENING_RULINGS[name]), ruling_registered_at(name), name),
    )[0]


def describe_widening_coverage() -> tuple[str, ...]:
    """Console lines: which shipped monsters have a letter, and which do not.

    G-OBS.  A monster no ruling covers is a monster a player can beat to zero
    and never fell, and this project has already shipped that state once
    without noticing (round szdkgs made four dummies unkillable and the suite
    stayed green).  So the uncovered rows are named, by scene and identity.

    THIS FUNCTION ONLY RETURNS THE LINES; printing happens in ``runtime.py``,
    which is not this lane's file (pf-adversary, this round: the first
    draft's docstring claimed they WERE printed, which was false and is the
    exact defect class this lane was burned by last round).  At the time
    that first draft was corrected, nothing in ``src/`` printed these lines
    yet.  It is wired now: ``runtime.py`` prints each line from this
    function's return value in a ``for`` loop right after it prints
    ``mob_death.describe_roster_override_coverage(...)``, at the world-census
    boot gate, per LANE-B letter 20260829_0744 point 3 (COO-DECISION
    2026-08-29T08:48+07:00 item 3) -- see the comment naming that letter at
    the call site.
    """
    lines = []
    for scene in field_mobs.live_scenes():
        roster = field_mobs.load_roster(scene=scene)
        sanctioned = [
            mob for mob in roster
            if mob.actor_identity == SANCTIONED_FIRST_TARGET_IDENTITY
            and mob.scene == SANCTIONED_FIRST_TARGET_SCENE
        ]
        uncovered = [
            mob for mob in roster
            if not rulings_covering(mob) and mob not in sanctioned
        ]
        # The field is named for what it MEASURES -- how many rows a letter
        # authorises -- and not "killable", which is what the first draft
        # called it (pf-adversary, this round).  "killable" would have had
        # chief boot the server, read "Bg0002 killable=17 of 17", and tell the
        # owner Bg0002's monsters can be killed.  They cannot: this module is
        # never even consulted for them, because runtime.py loads one scene's
        # roster and mob_combat refuses the target first.  An authorisation
        # count is not a client-observable one, and this line must not be
        # readable as one.
        lines.append(
            "MOB_DEATH_WIDENING_COVERAGE scene=%s letter_covers=%d of %d "
            "(authorisation only - says nothing about whether a hit can "
            "reach these rows)" % (
                scene, len(roster) - len(uncovered), len(roster)))
        for mob in uncovered:
            lines.append(
                "  UNKILLABLE identity=0x%X template=%d %s - no registered "
                "ruling covers it" % (
                    mob.actor_identity, mob.template_id, mob.display_name))
    # SCOPE, said out loud rather than left to be inferred (pf-adversary, this
    # round): this report walks the scenes load_roster will actually load.  A
    # scene whose table is mined but not registered ships no monsters into any
    # world and raises no coverage question here -- and a report silent about
    # that reads as "there is nothing else", which is a different claim and a
    # false one.
    #
    # The line names the LIVE list rather than asserting anything about what
    # is outside it.  The first draft said the omitted scenes were "mined but
    # unregistered", which would become a false statement the moment
    # live_scenes() drifted from the registry it reads -- the report would
    # then skip a REGISTERED scene and affirmatively give the wrong reason.
    # tests/test_mob_death_wired_widening.py pins live_scenes() to the
    # registry by set equality so that drift cannot happen quietly; this line
    # states only what it can see.
    lines.append(
        "MOB_DEATH_WIDENING_COVERAGE scope=live_scenes(%s) - scenes outside "
        "this list are not counted here and are not claimed empty by it" % (
            ",".join(field_mobs.live_scenes()),))
    return tuple(lines)


# ---------------------------------------------------------------------------
# The wire.  Every constant below is a static anchor carried WITH provenance
# rather than imported from the probe lane that proved it, and every one of
# them is pinned value-for-value against that lane in tests/test_mob_death.py.
#
#   BasicAttr serializer 0x4656F0 writes its fields in ASCENDING MASK-BIT
#   order.  Bit 0x0080 is the f32 at object offset +0x58, wire tag 0x2A, and it
#   is written after 0x0008 (max HP) and before 0x0100 (scene id).
#   legacy.make_npc_attr cannot emit it: V62 chose to omit bit 0x0080 entirely.
# ---------------------------------------------------------------------------
BASIC_BIT_NAME = 0x0001
# ADDED this round (RE-117): field_mobs.hostile_npc_attr now always sends
# the mined MOBS level, bit 0x0002, u16 tag 0x12 @ +0x5E -- proven for an
# NPCAttr body by RE-117 (NPCAttr serializer 0x00466EB0 calls common
# BasicAttr serializer 0x004656F0 before its own derived fields, so the base
# object's bits apply here too, not just to the owner's PC-actor probe).
# Same ascending-mask-bit slot rule as movement speed below: this composer
# must widen by the same bit in the same slot (after the optional name,
# before current HP) or its own self-check (the timerless projection must
# reproduce field_mobs.hostile_npc_attr byte for byte) fails closed.
BASIC_BIT_LEVEL = 0x0002               # u16 tag 0x12 @ +0x5E
BASIC_BIT_CURRENT_HP = 0x0004          # u32 tag 0x14 @ +0x44
BASIC_BIT_MAX_HP = 0x0008              # u32 tag 0x14 @ +0x48
# ADDED (COO-DECISION 2026-08-28T01:46+07:00): field_mobs.
# hostile_npc_attr now always sends the mined MOBS speed via
# legacy.make_npc_attr's own movement_speed parameter, bit 0x0040, f32 tag
# 0x2A @ +0x54 -- the same bit that function's own docstring already RE's
# (0x45C103/0x464960/0x45D2EA/0x484580).  This module's hand-written composer
# must widen by the same bit in the same ascending-mask-bit slot (after max
# HP, before the death timer) or its own self-check below (the timerless
# projection must reproduce field_mobs.hostile_npc_attr byte for byte) fails
# closed -- which is exactly what caught this composer needing the update.
BASIC_BIT_MOVEMENT_SPEED = 0x0040      # f32 tag 0x2A @ +0x54
BASIC_BIT_DEATH_TIMER = 0x0080         # f32 tag 0x2A @ +0x58
BASIC_BIT_SCENE_ID = 0x0100            # u16 tag 0x12
BASIC_BIT_SCENE_SEQ = 0x0200           # qword tag 0x32
BASIC_BIT_FACTION = 0x0400             # u32 tag 0x14 @ +0x68

DEATH_TIMER_TAG = 0x2A
DEATH_TIMER_OBJECT_OFFSET = 0x58
DEATH_TIMER_WIDTH = 4
DEATH_TIMER_SPLICE_BYTES = 1 + DEATH_TIMER_WIDTH

DB_ATTRIBUTE_MASK_TAG = 0x0B
DB_ATTRIBUTE_IDENTITY_MASK = 0x01
BASIC_ATTR_MASK_TAG = 0x12
IDENTITY_TAG = 0x32
U32_TAG = 0x14
NPC_ATTR_MASK_TAG = 0x0B
NPC_BIT_TEMPLATE = 0x01
NPC_BIT_VISUAL_PRESET = 0x04
# Where the BasicAttr u16 mask VALUE sits: the DBAttribute mask (2 bytes) plus
# the tagged identity (9) plus the mask's own tag byte.
_MASK_VALUE_OFFSET = 2 + 9 + 1

# The two sides of the gate.  Timer STRICTLY POSITIVE latches the dying state;
# timer <= 0 is what lets the death task be constructed.  Read that twice: it
# is the single fact most likely to be got backwards.
HP_WHEN_DEAD = 0
DYING_TIMER_SECONDS = 20.0
DEAD_TIMER_SECONDS = 0.0

# Static anchors of the chain, kept so a reader does not have to go and find
# them, and so a test can pin them against the lane that derived them.
DYING_PREDICATE_VA = 0x43BDA0          # actor vtable +0x40, needs timer > 0
DEATH_PREDICATE_VA = 0x43BD70          # actor vtable +0x3C, needs timer <= 0
DYING_LATCH_WRITE_VA = 0x44384C        # [actor+0x70] |= 0x200
DEATH_TASK_GATE_VA = 0x443990          # builds the task when the gate holds
DEATH_TASK_CTOR_VA = 0x472810          # CActorTask_Dead
DEATH_ANIMATION_NAME_VA = 0xF0F060     # L"_F_DIE_000"
DEATH_ANIMATION_NAME = "_F_DIE_000"
# A SECOND pair of predicates reads the same +0x58 field: 0x454A70 at vt+0x3C
# and 0x454AC0 at vt+0x40, plus the local player's Main_Dead open-gate at
# 0x44A540 (FACTPACK R102).  ~~This lane does not claim which actor class each
# pair belongs to.~~ That hedge was an unopened file, not a fact gap: this
# repository does say which, in three places, and they agree -
# docs/FUNCTIONAL_COVERAGE.json (domain 3 / hp_death_and_respawn),
# reports/PF_HP_DEATH001_HP_DEATH_AND_RESPAWN_STATIC_20260819.md and
# reports/PF_CHUNK2_Q3_BIND_THUNK_FINDINGS_20260819.md put 0x454AC0/0x454A70 on
# CNetActor and CMyActor, and 0x43BDA0/0x43BD70 on CNetNPC, CAvatarNPC and Pet.
# So THE PAIR THIS LANE USES IS CLASS-DEPENDENT: the one above is right because
# these monsters ship as actor_type 4 (CNetNPC-style), and a later round that
# moves them to actor_type 2 must move to the other pair as well.
R102_PREDICATE_VAS = (0x454A70, 0x454AC0, 0x44A540)
NETNPC_PREDICATE_VAS = (DEATH_PREDICATE_VA, DYING_PREDICATE_VA)
NETACTOR_PREDICATE_VAS = (0x454A70, 0x454AC0)

# OURS, and MEASURED BY NOBODY.  How long the fallen monster is left in the
# dying state before the frame that finishes it.
#
# ~~"700 ms is the only death-adjacent duration this project has measured
# (GT-030's ~0.7 s animation)"~~  STRUCK BY THE ADVERSARIAL REVIEW OF THIS
# ROUND, AND IT WAS RIGHT: GT-030 is the actor_type 2 remote-player
# VISIBILITY test, it runs at 15 s a frame, its probes are pinned at HP 100
# and nothing in it dies.  The only 0.x-second number near it is GT-030-R3's
# side effect - an NPC DISAPPEARING in 0.6 s, which the queue says cannot be
# told apart from despawn, replacement or occlusion, and which is why GT-072
# is open.  There is no measured death animation anywhere in this project.
# The sentence was a fabricated measurement inside a block labelled as an
# assumption, which is worse than an unlabelled guess, and it is struck here
# rather than deleted so the letter that already quoted it can be corrected
# against something.
#
# What is actually known about spacing: GT-022 sent the two frames 6000 ms
# apart, three times, and that number was chosen so a human with a camera
# could keep up.  Six seconds between a monster falling and a monster dying
# is not a game, so this lane does not inherit it.  700 ms is a round number
# clear of any plausible client frame.  That is the whole justification.
# [COO-CONFIRMED PROVISIONAL - unmeasured, GT ticket pending] - answered by
# notes_to_chief/20260826_0551_COO-DECISION-death-hold-700-stands-and-the-
# roster-stays-locked-to-0x201F.md, item (1): 700 stands as OUR number, not a
# measurement, until chief's 0/250/700/2000 ms sweep ticket lands in
# GAME_TEST_QUEUE.md and the owner reads the result back.  Lane B may not
# touch this number or world_population.py before that lands - the same
# ruling reserves both.  Nothing but this one number depends on the outcome.
#
# AND THE HOLD MAY BE PROTECTING AGAINST NOTHING.  The first draft justified it
# as "two frames in one client frame would race the per-frame update that
# consumes the latch".  That mechanism is not in any artifact this lane cites:
# 0x4437C0 is called synchronously from the attr-apply loop inside 0x4446F0,
# not from a per-frame update, and the HYPOTHESIS_LEDGER's own evidence gap for
# HYP-PF-023 records that the task gate at 0x443990 DOES NOT READ the 0x200
# latch bit - so the dying latch is not a proven prerequisite for the death
# task at all, and a single dead frame may open the gate on its own.  The hold
# is kept because the fall is the half this project has actually watched and
# sending the latch first is how it was watched; it is NOT kept because a race
# was demonstrated.  See MOB_DEATH_NONCLAIMS.
DEATH_TASK_HOLD_MS = 700

MOB_DEATH_NONCLAIMS = (
    "the death animation _F_DIE_000 has never been observed by anyone in this "
    "project; GT-025 proved the lying pose belongs to the DYING frame and "
    "requires every reading of GT-022 as evidence of that animation to be "
    "withdrawn, so this lane claims the FALL and not the corpse",
    "the death-task frame has been sent to a real client twice with nothing "
    "distinguishable following it; it is sent here because the static gate "
    "needs it, not because its effect has been watched",
    "nothing dispatches this module: runtime.py belongs to the chief and the "
    "one wiring line has not been written. "
    "[STALE as of runtime.py CORE-REQUEST-005, PR #63, round mdj01v, "
    "2026-08-26] [MEASURED, by call-site reading]: the wiring line HAS been "
    "written (mob_death.kill/commit_death run after mob_combat.commit_step "
    "reports death_due, unconditionally on a flagless boot, scoped to "
    "SANCTIONED_FIRST_TARGET_IDENTITY 0x201F). What is still true from the "
    "nonclaims around it: nobody has watched the corpse the death task "
    "produces, and the inbound EA7D that would drive a real kill is still "
    "unproven",
    "the hold between the two frames is OURS and unmeasured; the only spacing "
    "ever sent to a client on this carrier is GT-022's 6000 ms, which is "
    "unplayable, and whether the client needs any hold at all is unknown",
    "the dying frame's countdown widget is a client-side counter on its own "
    "clock (FACTPACK R102); how long it lingers over a monster this lane "
    "kills has not been observed",
    "the fall was watched on a NAMELESS, FACTIONLESS actor_type 4 body "
    "(GT-022/GT-025 at identity 0x2001); this lane's body is named and "
    "hostile and nobody has seen one of those at zero HP. "
    "[STALE as of GT-084-R2, attended, OBSERVER_CONFIRMED "
    "2026-08-27T15:52-15:55+07:00] [MEASURED, by "
    "notes_to_chief/20260827_1620_GT084R2-RESULT-PASS-hostile-kill-full-wire-"
    "but-corpse-freezes-no-target-panel.md]: someone HAS now seen the "
    "named+hostile body at zero HP (0x201F, this lane's own sanctioned "
    "target) - and it did NOT fall.  The corpse froze in a floating pose "
    "instead of lying flat; see the module docstring's CLIENT-OBSERVABLE "
    "section for the full account.  The chain's effect is BODY-DEPENDENT, "
    "confirmed, not just an untested extrapolation from actor_type. RE-107 "
    "(opened this round) asks what drives the difference; this module is "
    "unchanged pending that answer",
    "a real attack input has never been observed producing the EA7D "
    "ActionVital that reaches mob_combat, so the inbound half of the kill is "
    "as unproven as the inbound half of the hit",
    "named AND hostile in one body has never been sent and never been "
    "observed; the corpse body inherits that nonclaim from field_mobs and "
    "adds a bit nobody has combined with it either (mask 0x078D). "
    "[STALE as of GT-084-R2, 2026-08-27] [MEASURED]: it HAS now been sent "
    "and observed - see the CLIENT-OBSERVABLE update above and "
    "RE-107/RE-108 (CLIENT_RE_QUEUE.md, opened this round) for what is "
    "still open about it",
    "nothing here decides loot: what a dead monster drops is M5, and the "
    "drop ids in the roster are carried, not read, by this lane",
    "the register lives in the caller's process only; nothing in this project "
    "persists a monster's death across a server restart",
    "the dying latch is NOT a proven prerequisite for the death task: the "
    "HYP-PF-023 evidence gap records that the gate at 0x443990 does not read "
    "the 0x200 bit, so the two-frame shape is how the fall was WATCHED, not a "
    "chain anyone has shown to be required",
    "a client that connects AFTER the kill has never seen the identity, so "
    "the corpse entry takes the SPAWN branch, which never touches the "
    "dead sync: that player sees a body standing at 0 HP, and nothing in this "
    "lane re-sends it",
    "the production census (world_population) reads neither the ledger nor "
    "the register and re-asserts full HP for every placement it rebuilds, and "
    "it has no parameter to receive corpse_override at all; until somebody "
    "gives it one, STAYING down is not this lane's to claim - a corpse "
    "survives exactly until the next rebuild",
    "name colour is not claimed by this lane either: the owner's own ruling "
    "warns that a death proven on the sanctioned target proves 'the target we "
    "built can die', not 'an enemy can die', because the label still renders "
    "in the client's PLAYER colour - RE-067 is open and owns that question. "
    "[STALE as of pf_bridge/CLIENT_RE_QUEUE.md chief R163, 2026-08-25 "
    "~15:xx+07:00 (retracted BEFORE RE-067 was even opened) and chief R165, "
    "2026-08-25 ~17:0x+07:00 (RE-067 itself closed)] [MEASURED, by reading "
    "CLIENT_RE_QUEUE.md line ~1400 (R163's own retraction of this exact "
    "claim) and its RE-067 result block, line ~1655]: both halves of this "
    "sentence are wrong, not just outdated. 'The label renders in the "
    "client's PLAYER colour' is the draft theory chief R163 struck down "
    "before this ticket opened - the re-derived evidence is that the server "
    "always sends actor_type=4 for this identity, not that the client "
    "misclassifies it into a player slot. And 'RE-067 is open' is false: it "
    "closed PASS/MIXED - the item-name half PASSED, the actor-name half "
    "closed BOUNDED NEGATIVE (NameBoardNPC::update does not read actor_type, "
    "faction, or any FONT_COLOR path as a colour selector; the real driver "
    "is unidentified, not misrouted). So the accurate nonclaim is narrower: "
    "name colour is not claimed by this lane, and RE-067/RE-068 already "
    "looked for what decides it and could not find a driver at the static "
    "layer - that is a measured ceiling, not an open ticket waiting on more "
    "static work, and it is GT-084/RIDER-084-A's client-observable layer "
    "that still has to answer whether a player ever sees this render red",
)

REFUSE_VALUE_NOT_INT = "value_not_int"
REFUSE_VALUE_OUT_OF_RANGE = "value_out_of_range"
REFUSE_TYPE_NOT_TYPED_RECORD = "type_not_typed_record"
REFUSE_IDENTITY_NOT_POSITIVE = "identity_not_positive"
REFUSE_SCENE_NOT_TEXT = "scene_not_text"
REFUSE_TIMER_NOT_FINITE = "timer_not_finite"
REFUSE_TIMER_WRONG_SIDE_OF_THE_GATE = "timer_wrong_side_of_the_gate"
REFUSE_LIVE_HP_WITH_A_DEATH_TIMER = "live_hp_with_a_death_timer"
REFUSE_DEAD_HP_WITHOUT_A_DEATH_TIMER = "dead_hp_without_a_death_timer"
REFUSE_BODY_OFF_THE_LIVE_PROJECTION = "body_off_the_live_projection"
REFUSE_COMPOSED_BYTES_OFF_PIN = "composed_bytes_off_pin"
REFUSE_OUTCOME_IS_NOT_A_KILL = "outcome_is_not_a_kill"
REFUSE_OUTCOME_NAMES_ANOTHER_MONSTER = "outcome_names_another_monster"
REFUSE_ALREADY_DEAD = "already_dead"
REFUSE_NOT_DEAD = "not_dead"
REFUSE_REGISTER_NOT_SORTED = "register_not_sorted"
REFUSE_DUPLICATE_REGISTER_IDENTITY = "duplicate_register_identity"
REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER = "register_row_disagrees_with_roster"
REFUSE_LEDGER_DISAGREES_WITH_REGISTER = "ledger_disagrees_with_register"
REFUSE_OUTCOME_DISAGREES_WITH_ROSTER = "outcome_disagrees_with_roster"
REFUSE_REGISTER_STALE = "register_stale"
REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE = "target_outside_the_sanctioned_scope"
# ROUND uq2lxw, COO-DECISION 2026-08-29T08:48+07:00 item 1: a registered
# ruling whose NAME carries no letter timestamp cannot be ordered against the
# others, and the tie-break is the thing that decides which letter a kill is
# recorded under.  Refused by name rather than sorted last, which is what a
# missing key silently becomes.
REFUSE_RULING_NAME_HAS_NO_TIMESTAMP = "ruling_name_has_no_timestamp"
# pf-adversary (round lp6hg4): roster_override_coverage checked only that
# ``override`` itself was a dict, not that its entries were well-typed -
# every real caller's dict happens to satisfy this, so no live failure was
# found, but the module's other contract functions all validate their
# inputs by type rather than trusting the caller, and this one should too.
REFUSE_OVERRIDE_ENTRY_NOT_INT_BYTES = "override_entry_not_int_bytes"
# ~~REFUSE_HOLD_OUT_OF_RANGE~~ never declared as its own name: the hold is
# checked by the same range check as every other integer here, which raises
# REFUSE_VALUE_OUT_OF_RANGE, and a second name that can never be raised is a
# lie told to whoever counts them.
# pf-adversary (round sifsfg): hostile_census_frames forwarded ledger=None
# straight into full_roster_override without ever saying that its OWN
# contract is stricter than the family it calls.  repopulation_entries /
# full_roster_override legitimately accept ledger=None (a caller with no
# ledger open yet still needs to build a scene); hostile_census_frames does
# not have that excuse -- its own docstring says it exists to be called on
# every hit/death frame, and strike() already REQUIRES a typed CombatLedger
# before a hit/death frame can exist at all, so a call site that has this
# function's other arguments has a live ledger too, and one that omits it is
# always a bug, not a legitimate early-boot caller.  The adversary proved by
# execution that omitting it silently heals every damaged-but-alive monster
# back to ceiling HP on the wire -- refused by name instead of left silent.
REFUSE_CENSUS_FRAME_WITHOUT_A_LEDGER = "census_frame_without_a_ledger"
# CODEX_URGENT 2026-09-01T20:40+07:00 (P0-5 corpse/drop state scope), approved
# for LANE-B by COO-DECISION 2026-09-01T21:48+07:00: the ONE-CORPSE LIMIT
# named in hostile_census_frames' own docstring was real -- ``dead_timer`` is
# a single scalar ``repopulation_entries`` used to apply to EVERY dead
# register row, so composing one corpse's DYING frame re-armed every OTHER
# already-dead corpse's timer back to "dying" on the same call.  Once a
# widening ruling lets more than one identity be dead at once (it already
# does -- see WIDENING_RULINGS above), that is a real regression, not the
# hypothetical the docstring described it as.  ``transitioning`` is the fix:
# the ONE ``(scene, actor_identity)`` row this call is actually about.  A
# ``transitioning`` value that names a row the register does not carry as
# dead is refused here, by name, rather than silently ignored -- a caller
# that thinks it is composing identity X's death frame and is wrong about
# that should not get a census that quietly used the old, unsafe scalar
# behaviour for every row instead.
REFUSE_TRANSITIONING_NOT_A_DEAD_ROW = "transitioning_not_a_dead_row"
MOB_DEATH_REFUSAL_REASONS = (
    REFUSE_VALUE_NOT_INT,
    REFUSE_VALUE_OUT_OF_RANGE,
    REFUSE_TYPE_NOT_TYPED_RECORD,
    REFUSE_IDENTITY_NOT_POSITIVE,
    REFUSE_SCENE_NOT_TEXT,
    REFUSE_TIMER_NOT_FINITE,
    REFUSE_TIMER_WRONG_SIDE_OF_THE_GATE,
    REFUSE_LIVE_HP_WITH_A_DEATH_TIMER,
    REFUSE_DEAD_HP_WITHOUT_A_DEATH_TIMER,
    REFUSE_BODY_OFF_THE_LIVE_PROJECTION,
    REFUSE_COMPOSED_BYTES_OFF_PIN,
    REFUSE_OUTCOME_IS_NOT_A_KILL,
    REFUSE_OUTCOME_NAMES_ANOTHER_MONSTER,
    REFUSE_ALREADY_DEAD,
    REFUSE_NOT_DEAD,
    REFUSE_REGISTER_NOT_SORTED,
    REFUSE_DUPLICATE_REGISTER_IDENTITY,
    REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER,
    REFUSE_LEDGER_DISAGREES_WITH_REGISTER,
    REFUSE_OUTCOME_DISAGREES_WITH_ROSTER,
    REFUSE_REGISTER_STALE,
    REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE,
    REFUSE_OVERRIDE_ENTRY_NOT_INT_BYTES,
    REFUSE_CENSUS_FRAME_WITHOUT_A_LEDGER,
    REFUSE_RULING_NAME_HAS_NO_TIMESTAMP,
    REFUSE_TRANSITIONING_NOT_A_DEAD_ROW,
)

_FLOAT32_MAX = 3.4028234663852886e38


class MobDeathContractError(ValueError):
    """A refusal from this module, always carrying a named reason."""

    def __init__(self, reason: str, detail: str) -> None:
        if reason not in MOB_DEATH_REFUSAL_REASONS:
            raise AssertionError("unnamed refusal reason: %s" % reason)
        super().__init__("%s: %s" % (reason, detail))
        self.reason = reason
        self.detail = detail


def _require_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or type(value) is bool:
        raise MobDeathContractError(
            REFUSE_VALUE_NOT_INT, "%s must be a plain int" % label)
    if not minimum <= value <= maximum:
        raise MobDeathContractError(
            REFUSE_VALUE_OUT_OF_RANGE,
            "%s must be within [%d, %d], got %d" % (
                label, minimum, maximum, value),
        )
    return value


def _require_identity(value: Any, label: str) -> int:
    identity = _require_int(value, label, 0, 0xFFFFFFFFFFFFFFFF)
    if identity <= 0:
        raise MobDeathContractError(
            REFUSE_IDENTITY_NOT_POSITIVE, "%s must be positive" % label)
    return identity


def _require_scene(value: Any, label: str) -> str:
    """The other half of the key COO-DECISION 2026-08-27T22:49+07:00 added.

    Same shape as field_mobs.load_roster's own ``scene`` check: non-empty
    text, nothing more -- this module trusts a FieldMob's own ``.scene``
    field the same way it already trusts every other column on that typed
    record (see field_mobs.assert_single_scene_tables' own "WHAT THIS DOES
    NOT COVER" paragraph, which says so explicitly for the same field).
    """
    if type(value) is not str or not value:
        raise MobDeathContractError(
            REFUSE_SCENE_NOT_TEXT, "%s must be non-empty text" % label)
    return value


def _require_timer(value: Any) -> float:
    """The timer AS THE CLIENT WILL READ IT, not as Python holds it.

    The return value is the f32 round trip, and every gate check in this
    module runs on that rather than on the incoming double.  The reason is a
    silent kill this lane nearly shipped: ``struct.pack("<f", 1e-46)`` is four
    zero bytes, so a "strictly positive" dying timer under about 1.4e-45 goes
    on the wire as 0.0 and composes a DEAD frame that passed a DYING check.
    The two frames then come back byte-identical, the 0x200 latch is never
    written, and nothing in the module or the console would have said so.
    """
    if type(value) not in (int, float) or type(value) is bool:
        raise MobDeathContractError(
            REFUSE_TIMER_NOT_FINITE, "the death timer must be a number")
    timer = float(value)
    if not math.isfinite(timer) or abs(timer) > _FLOAT32_MAX:
        raise MobDeathContractError(
            REFUSE_TIMER_NOT_FINITE,
            "the death timer must be a finite float32 value")
    return as_wire_float(timer)


def as_wire_float(value: float) -> float:
    """What ``legacy.f32tag`` will actually put on the wire, read back."""
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _require_mob(mob: Any) -> FieldMob:
    if type(mob) is not FieldMob:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "mob must be the typed FieldMob record")
    return mob


@dataclass(frozen=True)
class DeathRecord:
    """One monster's death: who it was, who killed it, what it stood at.

    ``scene`` was ADDED this round (COO-DECISION 2026-08-27T22:49+07:00) and
    put LAST with a default of :data:`DEFAULT_SCENE`, so every existing
    3-positional-argument construction in this tree keeps meaning exactly
    what it always meant (a bg0001 record, the only scene this project has
    ever booted) and only a caller that names a different scene needs to
    change anything.  Two records may now legitimately share
    ``actor_identity`` as long as their ``scene`` differs -- that is the
    whole point: two different mobs in two different scenes that happen to
    compute the same wire identity (``field_mobs.cross_scene_identity_
    collisions()`` measures 4 such pairs today) are two different graves,
    not one.
    """

    actor_identity: int
    killer_identity: int
    max_hp: int
    scene: str = DEFAULT_SCENE

    def __post_init__(self) -> None:
        _require_identity(self.actor_identity, "actor identity")
        _require_identity(self.killer_identity, "killer identity")
        _require_int(self.max_hp, "max hp", 1, 0xFFFFFFFF)
        _require_scene(self.scene, "scene")
        if self.actor_identity == self.killer_identity:
            raise MobDeathContractError(
                REFUSE_OUTCOME_NAMES_ANOTHER_MONSTER,
                "a monster cannot be its own killer on this lane")


@dataclass(frozen=True)
class DeathRegister:
    """Who is dead, as a tuple sorted by ``(scene, actor_identity)``.

    Sorted-tuple rather than a set or a dict for the reason ``CombatLedger``
    gives: two registers built from the same kills compare equal in any
    process, and no caller can mutate a record behind the lane's back.

    ``generation`` is here for the reason ``CombatLedger`` has one, and the
    first draft of this module did not have it.  A register is a value, so
    "add a death" is a read-modify-write of something nobody owns: two players
    killing two DIFFERENT monsters in the same tick both read the empty
    register, both return a register of one, and whichever is stored second
    erases the other kill.  Nothing raises - and the erased monster stands
    back up at full HP on the next rebuild.  :func:`commit_death` is the
    compare-and-swap that makes the loser retry instead.

    KEYED BY ``(scene, actor_identity)``, NOT ``actor_identity`` ALONE - added
    this round by COO-DECISION 2026-08-27T22:49+07:00.  ``FieldMob.
    actor_identity`` is ``0x2000 + placement_index + 1`` with no scene term,
    so two different mobs in two different scenes can and do compute the same
    wire identity (``field_mobs.cross_scene_identity_collisions()`` measures
    4 real bg0001 x Bg0002 pairs today).  Before this round a single bare-
    identity register would have let killing one of a colliding pair mark the
    OTHER one dead too, in whichever scene it happened to stand in - the
    wrong grave.  Every query method below takes an optional ``scene``
    defaulting to :data:`DEFAULT_SCENE` (bg0001, the only scene this project
    has ever booted), so no existing single-scene call site needed to change
    to keep passing.
    """

    records: tuple[DeathRecord, ...] = ()
    generation: int = 0

    def __post_init__(self) -> None:
        if type(self.records) is not tuple:
            raise MobDeathContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD, "records must be a tuple")
        seen = set()
        for record in self.records:
            if type(record) is not DeathRecord:
                raise MobDeathContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "every register row must be a typed DeathRecord")
            key = (record.scene, record.actor_identity)
            if key in seen:
                raise MobDeathContractError(
                    REFUSE_DUPLICATE_REGISTER_IDENTITY,
                    "identity 0x%X in scene %r appears twice" % key[::-1])
            seen.add(key)
        ordered = tuple(sorted(
            self.records, key=lambda row: (row.scene, row.actor_identity)))
        if ordered != self.records:
            raise MobDeathContractError(
                REFUSE_REGISTER_NOT_SORTED,
                "register rows must be given in ascending (scene, "
                "actor_identity) order")
        _require_int(self.generation, "generation", 0, 2 ** 62)

    def identities(self) -> tuple[int, ...]:
        return tuple(row.actor_identity for row in self.records)

    def is_dead(self, actor_identity: int, scene: str = DEFAULT_SCENE) -> bool:
        wanted = _require_identity(actor_identity, "actor identity")
        wanted_scene = _require_scene(scene, "scene")
        return any(
            row.actor_identity == wanted and row.scene == wanted_scene
            for row in self.records)

    def record_of(
            self, actor_identity: int, scene: str = DEFAULT_SCENE
    ) -> DeathRecord:
        wanted = _require_identity(actor_identity, "actor identity")
        wanted_scene = _require_scene(scene, "scene")
        for row in self.records:
            if row.actor_identity == wanted and row.scene == wanted_scene:
                return row
        raise MobDeathContractError(
            REFUSE_NOT_DEAD,
            "identity 0x%X in scene %r is not in this register" % (
                wanted, wanted_scene))

    def with_death(self, record: DeathRecord) -> "DeathRegister":
        if type(record) is not DeathRecord:
            raise MobDeathContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "the addition must be a typed DeathRecord")
        if self.is_dead(record.actor_identity, record.scene):
            raise MobDeathContractError(
                REFUSE_ALREADY_DEAD,
                "identity 0x%X in scene %r is already in the register: a "
                "second kill on the same monster is a caller bug, not an "
                "event" % (record.actor_identity, record.scene),
            )
        return DeathRegister(
            tuple(sorted(
                self.records + (record,),
                key=lambda row: (row.scene, row.actor_identity))),
            self.generation + 1,
        )


def _compose_body(
    legacy: Any,
    mob: FieldMob,
    *,
    current_hp: int,
    death_timer: float | None,
    faction: int,
    scene_id: int,
    scene_sequence: int,
    with_name: bool,
) -> bytes:
    """The hostile body, optionally carrying BasicAttr bit 0x0080.

    Written out field by field rather than spliced, because the timer lands in
    the MIDDLE of the BasicAttr block (after max HP, before scene id) and a
    splice would have to compute that offset from a body whose name field is
    variable-length.  What keeps a hand-written composer honest is the check in
    :func:`corpse_npc_attr`: with the timer absent it must reproduce
    ``field_mobs.hostile_npc_attr`` byte for byte.
    """
    basic_mask = (
        BASIC_BIT_LEVEL | BASIC_BIT_CURRENT_HP | BASIC_BIT_MAX_HP
        | BASIC_BIT_MOVEMENT_SPEED
        | BASIC_BIT_SCENE_ID | BASIC_BIT_SCENE_SEQ | BASIC_BIT_FACTION
    )
    if with_name and mob.display_name:
        basic_mask |= BASIC_BIT_NAME
    if death_timer is not None:
        basic_mask |= BASIC_BIT_DEATH_TIMER
    npc_mask = NPC_BIT_TEMPLATE | (
        NPC_BIT_VISUAL_PRESET if mob.visual_preset else 0)
    out = bytearray()
    out += legacy.u8tag(DB_ATTRIBUTE_MASK_TAG, DB_ATTRIBUTE_IDENTITY_MASK)
    out += legacy.qwordtag(IDENTITY_TAG, mob.actor_identity)
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, basic_mask)
    # Ascending mask-bit order, which is the order BasicAttr's serializer
    # 0x4656F0 writes and its reader expects.
    if basic_mask & BASIC_BIT_NAME:
        out += legacy.wstr_tag(mob.display_name)               # 0x0001
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, mob.level)        # 0x0002
    out += legacy.u32tag(U32_TAG, current_hp)                  # 0x0004
    out += legacy.u32tag(U32_TAG, mob.max_hp)                  # 0x0008
    out += legacy.f32tag(float(mob.speed_walk))                # 0x0040
    if death_timer is not None:
        out += legacy.f32tag(death_timer)                      # 0x0080
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, scene_id)        # 0x0100
    out += legacy.qwordtag(IDENTITY_TAG, scene_sequence)       # 0x0200
    out += legacy.u32tag(U32_TAG, faction)                     # 0x0400
    out += legacy.u8tag(NPC_ATTR_MASK_TAG, npc_mask)
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, mob.template_id)
    if mob.visual_preset:
        out += legacy.wstr_tag(mob.visual_preset)
    return bytes(out)


def basic_mask_of(legacy: Any, body: bytes, actor_identity: int) -> int:
    """The BasicAttr u16 mask a composed body actually carries.

    Read out of the bytes rather than remembered, so a pin or a test that
    quotes "mask 0x078D" is quoting the wire and not this module's opinion of
    it.  The head is the DBAttribute mask plus the tagged identity, and the
    mask value follows its own tag byte.
    """
    identity = _require_identity(actor_identity, "actor identity")
    if type(body) is not bytes:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "body must be bytes")
    head = (
        bytes(legacy.u8tag(DB_ATTRIBUTE_MASK_TAG, DB_ATTRIBUTE_IDENTITY_MASK))
        + bytes(legacy.qwordtag(IDENTITY_TAG, identity))
    )
    if not body.startswith(head) or len(body) < len(head) + 3:
        raise MobDeathContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "this body does not open with the DBAttribute mask and the "
            "tagged identity 0x%X" % identity,
        )
    at = len(head) + 1
    return int.from_bytes(body[at:at + 2], "little")


def corpse_npc_attr(
    legacy: Any,
    mob: FieldMob,
    *,
    death_timer: float | None,
    current_hp: int = HP_WHEN_DEAD,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    scene_id: int = SCENE_ID,
    scene_sequence: int = SCENE_SEQUENCE,
    with_name: bool = True,
) -> bytes:
    """The hostile body at HP 0 plus EXACTLY the five bytes of the timer.

    THE SELF-CHECK IS THE PROOF, and it runs on every call.  The same composer,
    asked for a LIVE body with no timer, must reproduce
    ``field_mobs.hostile_npc_attr`` byte for byte - the body this project
    already ships and whose bar movement GT-035 watched.  A composer that
    drifts therefore fails closed instead of putting a guessed body on the
    wire, and the lethal body is that known-good body plus one tagged f32 in
    the one position the serializer's ascending-bit order allows.
    """
    _require_mob(mob)
    if type(with_name) is not bool:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "with_name must be a bool")
    hp = _require_int(current_hp, "current hp", 0, mob.max_hp)
    if death_timer is None:
        # The pair is the whole point.  A body at zero HP with no timer field
        # satisfies NEITHER side of the client's gate - 0x43BD70 wants
        # timer <= 0 and 0x43BDA0 wants timer > 0, and an absent field is
        # whatever the actor's BasicAttr already held - so it composes a
        # monster that is empty and not dying and not dead.
        raise MobDeathContractError(
            REFUSE_DEAD_HP_WITHOUT_A_DEATH_TIMER,
            "a body at HP %d must carry the death timer; pick a side of the "
            "gate rather than sending neither" % hp,
        )
    timer = _require_timer(death_timer)
    _require_int(faction, "faction", 1, 0xFFFFFFFF)
    if hp != HP_WHEN_DEAD:
        # Bit 0x0080 on a body that still has HP is a state this project has
        # never composed and whose meaning nobody has derived: 0x43BD70 and
        # 0x43BDA0 both require +0x44 == 0 before they look at the timer at
        # all, so such a frame would carry a lethal field that no gate reads.
        raise MobDeathContractError(
            REFUSE_LIVE_HP_WITH_A_DEATH_TIMER,
            "a death timer belongs on a body at HP %d, not %d" % (
                HP_WHEN_DEAD, hp),
        )
    live_reference = field_mobs.hostile_npc_attr(
        legacy, mob, current_hp=mob.max_hp, scene_id=scene_id,
        scene_sequence=scene_sequence, faction=faction, with_name=with_name,
    )
    degraded = _compose_body(
        legacy, mob, current_hp=mob.max_hp, death_timer=None, faction=faction,
        scene_id=scene_id, scene_sequence=scene_sequence, with_name=with_name,
    )
    if degraded != live_reference:
        raise MobDeathContractError(
            REFUSE_BODY_OFF_THE_LIVE_PROJECTION,
            "the timerless projection of this composer no longer reproduces "
            "field_mobs.hostile_npc_attr byte for byte, so the lethal body it "
            "would compose is a guess",
        )
    composed = _compose_body(
        legacy, mob, current_hp=hp, death_timer=timer, faction=faction,
        scene_id=scene_id, scene_sequence=scene_sequence, with_name=with_name,
    )
    if len(composed) != len(live_reference) + DEATH_TIMER_SPLICE_BYTES:
        raise MobDeathContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the corpse body is %d bytes and the live body plus a tagged f32 "
            "is %d" % (len(composed), len(live_reference)
                       + DEATH_TIMER_SPLICE_BYTES),
        )
    # AND THE FIELD IS READ BACK, WHERE IT LANDED AND WHAT IT SAYS.  The two
    # checks above are blind to both: an adversarial review swapped the
    # composer for one that appends the f32 AFTER the faction field instead of
    # after max HP, and the equality and the length both still passed while
    # the body carried a lethal field in a position the serializer's
    # ascending-bit order does not allow.  The docstring above claims the
    # position; this is what makes the claim true rather than intended.
    prefix = _compose_body(
        legacy, mob, current_hp=hp, death_timer=None, faction=faction,
        scene_id=scene_id, scene_sequence=scene_sequence, with_name=with_name,
    )
    cut = _timer_offset(legacy, mob, prefix, hp, with_name)
    read_back = composed[cut:cut + DEATH_TIMER_SPLICE_BYTES]
    mask_at = _MASK_VALUE_OFFSET
    timerless_mask = int.from_bytes(prefix[mask_at:mask_at + 2], "little")
    composed_mask = basic_mask_of(legacy, composed, mob.actor_identity)
    if (read_back[:1] != bytes([DEATH_TIMER_TAG])
            or composed_mask != timerless_mask | BASIC_BIT_DEATH_TIMER
            or composed[:mask_at] != prefix[:mask_at]
            or composed[mask_at + 2:cut] != prefix[mask_at + 2:cut]
            or composed[cut + DEATH_TIMER_SPLICE_BYTES:] != prefix[cut:]):
        raise MobDeathContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the corpse body is not the timerless body with bit 0x%04X set "
            "and five bytes inserted at offset %d: the field landed somewhere "
            "the BasicAttr serializer does not read it" % (
                BASIC_BIT_DEATH_TIMER, cut),
        )
    if as_wire_float(struct.unpack("<f", read_back[1:])[0]) != timer:
        raise MobDeathContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the composed timer reads back as %r and %r was asked for" % (
                struct.unpack("<f", read_back[1:])[0], timer),
        )
    return composed


def _timer_offset(
    legacy: Any,
    mob: FieldMob,
    timerless: bytes,
    current_hp: int,
    with_name: bool,
) -> int:
    """Where bit 0x0080 belongs: after max HP and speed, before the scene id.

    Computed from the frozen serializers rather than written down, because the
    name field ahead of it is variable-length.  The head is checked against
    the body it is measuring, so a drift in ``make_npc_attr``'s field order
    refuses here instead of putting the timer in the wrong place.

    ADDED this round: the speed field (bit 0x0040) sits between max HP and
    the death timer in ascending-mask-bit order, so its bytes must be
    accounted for here too -- see ``BASIC_BIT_MOVEMENT_SPEED``.

    ADDED this round (RE-117): the level field (bit 0x0002) sits between the
    optional name and current HP in ascending-mask-bit order, so its bytes
    must be accounted for here too -- see ``BASIC_BIT_LEVEL``.
    """
    head = (
        bytes(legacy.u8tag(DB_ATTRIBUTE_MASK_TAG, DB_ATTRIBUTE_IDENTITY_MASK))
        + bytes(legacy.qwordtag(IDENTITY_TAG, mob.actor_identity))
    )
    name = (
        bytes(legacy.wstr_tag(mob.display_name))
        if with_name and mob.display_name else b""
    )
    level = bytes(legacy.u16tag(BASIC_ATTR_MASK_TAG, mob.level))
    speed = bytes(legacy.f32tag(float(mob.speed_walk)))
    upto = (
        len(head) + 3 + len(name) + len(level)
        + len(bytes(legacy.u32tag(U32_TAG, current_hp)))
        + len(bytes(legacy.u32tag(U32_TAG, mob.max_hp)))
        + len(speed)
    )
    expected = (
        head + timerless[len(head):len(head) + 3] + name + level
        + bytes(legacy.u32tag(U32_TAG, current_hp))
        + bytes(legacy.u32tag(U32_TAG, mob.max_hp))
        + speed
    )
    if timerless[:upto] != expected:
        raise MobDeathContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the BasicAttr block no longer opens with identity, mask, name "
            "and the two HP fields, so the timer offset is stale",
        )
    return upto


def death_actor_entry(
    legacy: Any,
    mob: FieldMob,
    *,
    death_timer: float,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    scene_id: int = SCENE_ID,
    scene_sequence: int = SCENE_SEQUENCE,
    with_name: bool = True,
    with_movement: bool = False,
) -> bytes:
    """One actor entry carrying the corpse body.

    ``with_movement`` defaults to False for the reason ``mob_combat.bar_frames``
    gives: a refresh that re-sends the movement attribute snaps the actor back
    to its roster row, which on a kill would teleport the body to where the
    monster was standing when the scene loaded rather than where it fell.
    """
    body = corpse_npc_attr(
        legacy, mob, death_timer=death_timer, faction=faction,
        scene_id=scene_id, scene_sequence=scene_sequence, with_name=with_name,
    )
    if type(with_movement) is not bool:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "with_movement must be a bool")
    attrs = [(NPC_ATTR_ID, body)]
    if with_movement:
        attrs.append((
            MOVEMENT_ATTR_ID,
            legacy.make_remote_movement_attr(
                mob.actor_identity, mob.x, mob.y, mob.z,
                field_mobs.HEADINGS[mob.placement_index & 3],
                mask=FULL_MOVEMENT_MASK,
            ),
        ))
    return legacy.make_remote_actor_entry(
        NPC_STYLE_ACTOR_TYPE, mob.actor_identity, attrs)


def death_frames(
    legacy: Any,
    mob: FieldMob,
    *,
    death_timer: float,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    scene_id: int = SCENE_ID,
    scene_sequence: int = SCENE_SEQUENCE,
    with_name: bool = True,
) -> tuple[bytes, bytes]:
    """One RuntimeRes collection carrying one corpse entry.

    [OPEN RISK, NOT MEASURED - flagged, not fixed, this round (`yjty8a`)] Same
    shape as ``mob_combat.bar_frames``, same citation: a nonempty one-entry
    ``make_runtime_remote_actors`` generation, wired to the unflagged path by
    `pirate-force-server#63` (2026-08-26 16:49+07:00), of the exact kind
    ``pf_bridge/notes_to_chief/20260826_0910_LANE-A-CORE-REQUEST-the-town-must-not-
    follow-you-out-of-town.md`` section 4.bis warned about and
    ``pf_bridge/notes_to_chief/20260826_1017_RE-082-RESULT-OBJECT-REF-IS-ELEMENT-KEY.md``
    later showed erases-by-omission for a sibling collection consumer, still
    unverified for this one.  See ``mob_combat.bar_frames`` for the full
    citation; not repeated twice in one module.

    [UPDATE, round ``sifsfg``, 2026-08-27]: "still unverified for this one"
    above is no longer true - ``RE-092`` (2026-08-26 22:23) verified it, for
    this exact collection (the ``GSCN_RunTimeProtocolRes`` mask-``0x02``
    chain both ``death_frames`` and ``bar_frames`` compose through):
    replace-by-omission, confirmed.  This function is UNCHANGED and still
    callable as-is; :func:`hostile_census_frames` in this module is the fix
    - it composes the same corpse/live body this function would build into a
    full census instead of a one-entry collection.  See
    :func:`mob_combat.bar_frames`'s own matching update for the fuller
    citation; not repeated twice in one module.
    """
    entry = death_actor_entry(
        legacy, mob, death_timer=death_timer, faction=faction,
        scene_id=scene_id, scene_sequence=scene_sequence, with_name=with_name,
    )
    pc, frame = legacy.make_runtime_remote_actors([entry])
    if frame != legacy.frame_pc(pc):
        raise MobDeathContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN, "death frame drift")
    return pc, frame


def dying_frames(
    legacy: Any,
    mob: FieldMob,
    *,
    death_timer: float = DYING_TIMER_SECONDS,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    scene_id: int = SCENE_ID,
    scene_sequence: int = SCENE_SEQUENCE,
    with_name: bool = True,
) -> tuple[bytes, bytes]:
    """The frame that drops the monster: HP 0 and a STRICTLY POSITIVE timer."""
    timer = _require_timer(death_timer)
    if not timer > 0.0:
        raise MobDeathContractError(
            REFUSE_TIMER_WRONG_SIDE_OF_THE_GATE,
            "the dying latch needs a timer above zero (vtable +0x40 at "
            "0x%X compares 0.0 < timer); got %r" % (DYING_PREDICATE_VA, timer),
        )
    return death_frames(
        legacy, mob, death_timer=timer, faction=faction, scene_id=scene_id,
        scene_sequence=scene_sequence, with_name=with_name,
    )


def dead_frames(
    legacy: Any,
    mob: FieldMob,
    *,
    death_timer: float = DEAD_TIMER_SECONDS,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    scene_id: int = SCENE_ID,
    scene_sequence: int = SCENE_SEQUENCE,
    with_name: bool = True,
) -> tuple[bytes, bytes]:
    """The frame that finishes it: HP 0 and a timer AT OR BELOW zero."""
    timer = _require_timer(death_timer)
    if timer > 0.0:
        raise MobDeathContractError(
            REFUSE_TIMER_WRONG_SIDE_OF_THE_GATE,
            "the death task needs a timer at or below zero (vtable +0x3C at "
            "0x%X refuses while 0.0 < timer); got %r" % (
                DEATH_PREDICATE_VA, timer),
        )
    return death_frames(
        legacy, mob, death_timer=timer, faction=faction, scene_id=scene_id,
        scene_sequence=scene_sequence, with_name=with_name,
    )


@dataclass(frozen=True)
class DeathStep:
    """One kill, end to end: both frames, the hold between them, the register.

    The caller owns dispatch.  It owes the two frames IN ORDER with the hold
    between them, and it owes storing :attr:`register` - a caller that sends
    the frames and drops the register has a corpse on screen that the next
    re-apply stands back up at full HP.
    """

    record: DeathRecord
    dying_pc: bytes
    dying_frame: bytes
    dead_pc: bytes
    dead_frame: bytes
    register: DeathRegister
    hold_ms: int = DEATH_TASK_HOLD_MS
    base_generation: int = 0
    # The timers AS COMPOSED, read back through the f32 round trip.  Carried on
    # the step rather than looked up from the module constants, because a
    # console line that prints the constant while the frame carries something
    # else is a diagnostic that lies exactly when it is needed.
    dying_timer: float = DYING_TIMER_SECONDS
    dead_timer: float = DEAD_TIMER_SECONDS

    def __post_init__(self) -> None:
        for label, value in (("record", self.record),
                             ("register", self.register)):
            expected = DeathRecord if label == "record" else DeathRegister
            if type(value) is not expected:
                raise MobDeathContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "%s must be a typed %s" % (label, expected.__name__))
        for label, value in (("dying pc", self.dying_pc),
                             ("dying frame", self.dying_frame),
                             ("dead pc", self.dead_pc),
                             ("dead frame", self.dead_frame)):
            if type(value) is not bytes or not value:
                raise MobDeathContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "%s must be non-empty bytes" % label)
        _require_int(self.hold_ms, "hold ms", 0, 60_000)
        _require_int(self.base_generation, "base generation", 0, 2 ** 62)
        for label, value in (("dying timer", self.dying_timer),
                             ("dead timer", self.dead_timer)):
            if type(value) is not float or not math.isfinite(value):
                raise MobDeathContractError(
                    REFUSE_TIMER_NOT_FINITE, "%s must be a finite float" % label)
        # The polarity, checked on the step and not only where the frames were
        # composed: a caller that hand-builds a DeathStep gets the same gate.
        if not self.dying_timer > 0.0 or self.dead_timer > 0.0:
            raise MobDeathContractError(
                REFUSE_TIMER_WRONG_SIDE_OF_THE_GATE,
                "a step must carry a dying timer above zero and a dead timer "
                "at or below it; got %r and %r" % (
                    self.dying_timer, self.dead_timer),
            )
        if self.dying_frame == self.dead_frame:
            raise MobDeathContractError(
                REFUSE_TIMER_WRONG_SIDE_OF_THE_GATE,
                "the two frames are byte-identical, so only one side of the "
                "gate is on the wire")
        if not self.register.is_dead(
                self.record.actor_identity, self.record.scene):
            raise MobDeathContractError(
                REFUSE_NOT_DEAD,
                "the step's own register does not carry the monster it killed")

    @property
    def frames(self) -> tuple[bytes, ...]:
        """Dying first, dead second.

        Sent in this order because it is the order the fall was WATCHED in
        (GT-022, GT-025) - not because the latch has been shown to be a
        prerequisite for the death task.  The HYP-PF-023 evidence gap records
        that the task gate does not read the latch bit at all.
        """
        return (self.dying_frame, self.dead_frame)

    @property
    def schedule(self) -> tuple[tuple[int, bytes], ...]:
        """The two frames with the GAP each one waits after the previous send.

        A gap, not a cumulative deadline: the dying frame goes out at once and
        the dead frame ``hold_ms`` after IT, which at two frames is the same
        number either way and stops being the same the moment a third appears.
        """
        return ((0, self.dying_frame), (self.hold_ms, self.dead_frame))


def kill(
    legacy: Any,
    mob: FieldMob,
    outcome: HitOutcome,
    register: DeathRegister | None = None,
    *,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    hold_ms: int = DEATH_TASK_HOLD_MS,
    dying_timer: float = DYING_TIMER_SECONDS,
    dead_timer: float = DEAD_TIMER_SECONDS,
    with_name: bool = True,
    widened: str | None = None,
) -> DeathStep:
    """Finish a monster that a hit already took to zero.

    This lane does NO arithmetic.  ``mob_combat`` computed the damage, moved
    the balance and set ``death_due``; the only thing left is to answer the
    frames.  An outcome that is not a kill is REFUSED by name rather than
    quietly turned into one, because a lane that can kill a monster the
    arithmetic did not kill is a lane that can kill a monster at full HP.
    """
    _require_mob(mob)
    if type(outcome) is not HitOutcome:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "outcome must be a typed HitOutcome")
    live = DeathRegister() if register is None else register
    if type(live) is not DeathRegister:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "register must be a typed DeathRegister")
    if outcome.target_identity != mob.actor_identity:
        raise MobDeathContractError(
            REFUSE_OUTCOME_NAMES_ANOTHER_MONSTER,
            "the outcome names 0x%X and the mob is 0x%X" % (
                outcome.target_identity, mob.actor_identity),
        )
    if outcome.max_hp != mob.max_hp:
        # Its own name, not the register's: the announced number came from
        # one ceiling and the body would be composed against another.
        raise MobDeathContractError(
            REFUSE_OUTCOME_DISAGREES_WITH_ROSTER,
            "the outcome stands at a ceiling of %d and the roster says %d" % (
                outcome.max_hp, mob.max_hp),
        )
    if not outcome.death_due or outcome.hp_after != HP_WHEN_DEAD:
        raise MobDeathContractError(
            REFUSE_OUTCOME_IS_NOT_A_KILL,
            "this outcome leaves the monster at %d of %d HP; only a hit that "
            "reached %d may be finished here" % (
                outcome.hp_after, outcome.max_hp, HP_WHEN_DEAD),
        )
    # THE THREE CHECKS THE ADVERSARIAL REVIEW OF THIS ROUND FORCED, because
    # death_due alone was never enough:
    #  - no_room is a hit that landed on something ALREADY dead.  Its outcome
    #    carries death_due=True (it is at the floor), so a wiring line reading
    #    death_due sends a SECOND pair of lethal frames for a body already on
    #    the ground - and with GT-029's widget, re-arms a 20-second countdown
    #    over a corpse.  mob_combat.CombatStep.death_due is the property that
    #    excludes this; this is the same exclusion, enforced where it cannot
    #    be skipped by reading the wrong attribute.
    #  - a zero-damage outcome kills nothing.  With HP_FLOOR now 0, an outcome
    #    with hp_before == hp_after == 0 is CONSTRUCTIBLE for the first time,
    #    and the first draft of this function accepted it and composed both
    #    lethal frames for a monster nobody hit.
    #  - a balance that did not move is not a kill either, whatever the flags
    #    say.
    if outcome.no_room:
        raise MobDeathContractError(
            REFUSE_OUTCOME_IS_NOT_A_KILL,
            "this hit landed on a monster that was already dead (no_room); "
            "read mob_combat.CombatStep.death_due, not outcome.death_due",
        )
    if outcome.damage <= 0 or outcome.hp_before <= outcome.hp_after:
        raise MobDeathContractError(
            REFUSE_OUTCOME_IS_NOT_A_KILL,
            "this outcome moved nothing: damage %d, hp %d -> %d; a kill is a "
            "hit that took a living monster to %d" % (
                outcome.damage, outcome.hp_before, outcome.hp_after,
                HP_WHEN_DEAD),
        )
    # THE SANCTIONED BYPASS, AND WHY IT NOW CARRIES A SCENE (round 8ftmbx).
    # ``actor_identity`` is ``0x2000 + placement_index + 1`` with NO scene
    # term, and every scene has a placement 30 -- so 0x201F is not the name of
    # an actor, it is the name of an INDEX.  pf-adversary (D3) proved by
    # execution that a Bg0015 mob sitting at placement 30 walked through this
    # bypass, the template check AND WIDENING_RULING_SCENES with nothing
    # passed at all, purely for landing on that index.  That was survivable
    # only while 0x201F was a real bg0001 roster row; COO-DECISION
    # 2026-08-29T00:41+07:00 withdrew that row, so the bypass now points at no
    # shipped actor and would hand a free kill to whichever scene is wired
    # next.  PANYA-RULINGS-FOUR named a bg0001 actor, so the bypass is held to
    # bg0001, which is what the ruling always meant and never had to say while
    # only one scene existed.  This TIGHTENS: nothing that could be killed
    # through a named ruling loses that route.
    sanctioned = (
        mob.actor_identity == SANCTIONED_FIRST_TARGET_IDENTITY
        and getattr(mob, "scene", None) == SANCTIONED_FIRST_TARGET_SCENE
    )
    if not sanctioned:
        # The owner's sequencing, held as a gate.  A caller that has a ruling
        # widening this names it; a caller that does not gets a refusal that
        # says which ruling it is standing on and what it was allowed.
        if type(widened) is not str or not widened.strip():
            raise MobDeathContractError(
                REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE,
                "identity 0x%X is not the sanctioned first target 0x%X.  %s "
                "says: prove the death loop on that identity FIRST, then move "
                "to a real table mob, and do not merge the two steps.  If a "
                "later ruling widened this, pass widened='<its name>' and say "
                "so in the round note" % (
                    mob.actor_identity, SANCTIONED_FIRST_TARGET_IDENTITY,
                    SANCTIONING_RULING),
            )
        # FAILS CLOSED on the ruling name itself, not only on the template it
        # names.  The first draft of this guard treated any STRING this
        # module had never catalogued as pre-fix-legal ("just needs to be
        # non-empty"), and pf-adversary (round 67jejl) broke that by
        # execution: a PARAPHRASE of the real 916 ruling - not a reuse of
        # its exact string, a typo-level drift from transcribing it out of a
        # notes_to_chief letter by hand - walked straight through and
        # authorised a kill on a mob the same ruling calls still-misplaced
        # data.  That is the more likely real mistake, not a caller
        # deliberately reusing the right string for the wrong mob, so an
        # UNRECOGNISED ruling name is refused here, by name, same as an
        # empty one - it authorises nothing, on principle, rather than by
        # accident of what happens to already be in WIDENING_RULINGS.
        covered_templates = WIDENING_RULINGS.get(widened)
        if covered_templates is None:
            raise MobDeathContractError(
                REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE,
                "widened=%r is not a ruling this module recognises (see "
                "WIDENING_RULINGS); a string that merely paraphrases or "
                "mistranscribes a real ruling authorises nothing - register "
                "the ruling under its exact name first" % (widened,),
            )
        if mob.template_id not in covered_templates:
            raise MobDeathContractError(
                REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE,
                "widened=%r is a known ruling and it names MOBS template "
                "id(s) %s; mob 0x%X carries template_id %d, which is not "
                "one of them - the ruling's own string does not authorise "
                "this monster" % (
                    widened, sorted(covered_templates), mob.actor_identity,
                    mob.template_id),
            )
        # ADDED this round (PANYA-DECISION 2026-08-27T20:10+07:00 "M1-P" item
        # 3): the template_id check above is no longer sufficient by itself
        # once a second scene's roster can reach this function at all -- the
        # bg0001 and Bg0002 rulings' covered template sets OVERLAP (31, 34,
        # 35, 103 are in both), so a mob whose template_id passes could still
        # be the WRONG scene's instance of that template. WIDENING_RULING_
        # SCENES only names the rulings that actually need this (see its own
        # docstring); a ruling with no entry there is unaffected.
        required_scene = WIDENING_RULING_SCENES.get(widened)
        if required_scene is not None and mob.scene != required_scene:
            raise MobDeathContractError(
                REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE,
                "widened=%r only authorises scene %r; mob 0x%X carries "
                "template_id %d (which IS in the ruling's covered set) but "
                "scene %r, so this ruling's own scope does not cover it - "
                "a template_id match alone is not enough once more than one "
                "scene shares that template" % (
                    widened, required_scene, mob.actor_identity,
                    mob.template_id, mob.scene),
            )
    if live.is_dead(mob.actor_identity, mob.scene):
        raise MobDeathContractError(
            REFUSE_ALREADY_DEAD,
            "identity 0x%X in scene %r is already dead: a second kill would "
            "send a second pair of frames for a corpse" % (
                mob.actor_identity, mob.scene),
        )
    _require_int(hold_ms, "hold ms", 0, 60_000)
    record = DeathRecord(
        mob.actor_identity, outcome.attacker_identity, mob.max_hp, mob.scene)
    dying_pc, dying_frame = dying_frames(
        legacy, mob, death_timer=dying_timer, faction=faction,
        with_name=with_name)
    dead_pc, dead_frame = dead_frames(
        legacy, mob, death_timer=dead_timer, faction=faction,
        with_name=with_name)
    return DeathStep(
        record, dying_pc, dying_frame, dead_pc, dead_frame,
        live.with_death(record), hold_ms, live.generation,
        _require_timer(dying_timer), _require_timer(dead_timer),
    )


def commit_death(current: DeathRegister, step: DeathStep) -> DeathRegister:
    """Compare-and-swap: accept a kill only against the register it was read from.

    The mirror of ``mob_combat.commit_step``, and it exists for the same
    reason.  Two kills computed from the same register both return a register
    of one row, and storing them in turn loses one of them - silently, and on
    a different monster from the one the second kill was about.  Returns the
    new register; refuses with :data:`REFUSE_REGISTER_STALE` when the stored
    register has moved, in which case the caller sends NOTHING, because the
    frames of a refused step describe a death the server has not recorded.

    WHAT "RE-RUN" MEANS HERE, SPELLED OUT, because the sibling lane's identical
    phrase means something different and following it wedges the world: re-read
    the register and call :func:`kill` again with the SAME outcome you are
    still holding.  Do NOT re-run ``mob_combat.strike`` - the ledger already
    holds the kill, so it would answer ``no_room``, which :func:`kill` refuses
    by name.  A caller that drops the outcome at this point has a monster at
    zero in the ledger and absent from the register, which every later
    ``repopulation_entries(..., ledger=...)`` refuses until someone repairs it.
    """
    if type(current) is not DeathRegister:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "current must be a typed DeathRegister")
    if type(step) is not DeathStep:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "step must be a typed DeathStep")
    if current.generation != step.base_generation:
        raise MobDeathContractError(
            REFUSE_REGISTER_STALE,
            "this kill was computed from generation %d and the register is at "
            "generation %d: re-read the register, call kill() again with the "
            "SAME outcome you are holding, and send nothing until this "
            "returns - re-running strike() would answer no_room, because the "
            "ledger already holds the kill" % (
                step.base_generation, current.generation),
        )
    # A generation is a counter, and a counter is not a value.  Every register
    # built through this API has generation == len(records), so two registers
    # holding the same NUMBER of dead monsters carry the same generation even
    # when they carry different monsters - and a step from one lineage would
    # then commit over the other, dropping its rows without a word.  The
    # counter says "nothing has happened since"; this says "and nothing has
    # been lost".
    if not set(current.identities()) <= set(step.register.identities()):
        dropped = sorted(
            set(current.identities()) - set(step.register.identities()))
        raise MobDeathContractError(
            REFUSE_REGISTER_STALE,
            "committing this kill would drop %s from the register: the step "
            "was computed from a different lineage that happens to be the "
            "same length" % ", ".join("0x%X" % i for i in dropped),
        )
    return step.register


def live_roster(
    roster: tuple[FieldMob, ...],
    register: DeathRegister,
) -> tuple[FieldMob, ...]:
    """The monsters that are still alive, in the order they were given.

    Checked per mob with the mob's OWN ``scene`` (``register.is_dead(m.
    actor_identity, m.scene)``), not a bare ``actor_identity in {register.
    identities()}`` set - the latter would wrongly call a live mob dead the
    moment the register also carries a DIFFERENT scene's mob sharing the same
    wire identity (COO-DECISION 2026-08-27T22:49+07:00).
    """
    if type(roster) is not tuple:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "roster must be a tuple of FieldMob")
    if type(register) is not DeathRegister:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "register must be a typed DeathRegister")
    for mob in roster:
        _require_mob(mob)
    return tuple(
        m for m in roster if not register.is_dead(m.actor_identity, m.scene))


def _balance_in(ledger: Any, actor_identity: int) -> int:
    """One ledger row's current HP, with the other lane's refusal renamed.

    ``CombatLedger.balance_of`` raises ``MobCombatContractError`` for an
    identity it does not carry.  That is the right refusal in the wrong
    module's name: this file promises every contract breach arrives as a
    :class:`MobDeathContractError`, and a caller that catches ours would have
    missed this one entirely.
    """
    try:
        return ledger.balance_of(actor_identity).current_hp
    except mob_combat.MobCombatContractError as exc:
        raise MobDeathContractError(
            REFUSE_LEDGER_DISAGREES_WITH_REGISTER,
            "the ledger cannot answer for identity 0x%X (%s): the roster and "
            "the ledger were built from different rosters" % (
                actor_identity, exc.reason),
        ) from exc


def repopulation_entries(
    legacy: Any,
    roster: tuple[FieldMob, ...],
    register: DeathRegister,
    *,
    ledger: Any = None,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    with_name: bool = True,
    dead_timer: float = DEAD_TIMER_SECONDS,
    transitioning: tuple[str, int] | None = None,
) -> list[bytes]:
    """Actor entries for a re-apply that must not resurrect anybody.

    PASS THE LEDGER.  It is optional only because a caller that has not opened
    one yet should still be able to build a scene, and leaving it out has a
    cost written here rather than discovered later: without it every LIVING
    monster is re-sent at its ceiling, so the bar a player just watched fall
    to a third snaps back to full on the next re-apply.  With it, each living
    monster is re-sent at the HP the arithmetic actually holds.

    THE HAZARD THIS CLOSES IS REAL AND IT IS THIS LANE'S OWN.  ``field_mobs``
    states that the accepted evidence was measured with the identical
    collection queued twice, the second time after model readiness
    (``INITIAL_REAPPLY_MS``), and any later census rebuild sends it again.
    Every one of those sends carries a LIVE body for every roster row, so a
    monster killed between two of them stands back up at full HP with no hit,
    no frame and no error anywhere - the client is simply told it is alive.
    A dead identity gets its corpse body here instead: same identity, HP 0,
    timer already on the dead side of the gate.

    ``transitioning`` IS THE RE-ARM FIX, CODEX_URGENT 2026-09-01T20:40+07:00,
    APPROVED BY COO-DECISION 2026-09-01T21:48+07:00.  ``dead_timer`` used to
    be a single scalar applied to EVERY dead row this call composes -- correct
    only while at most one identity could ever be dead at once, which is no
    longer true (see ``WIDENING_RULINGS``).  Pass ``transitioning=(scene,
    actor_identity)`` to name the ONE row this call is actually about: that
    row alone gets ``dead_timer``; every OTHER dead row gets
    :data:`DEAD_TIMER_SECONDS` regardless of what ``dead_timer`` is, because
    an already-dead corpse's steady state is the floor, not whatever timer the
    CURRENT transition happens to be composing.  ``transitioning=None`` (the
    default) keeps the OLD scalar-to-everyone behaviour byte-for-byte, so
    every existing single-corpse call site and test is unaffected -- with at
    most one dead row in the register, "apply to everyone" and "apply to the
    one row named" already agree.  A ``transitioning`` value that names a row
    the register does not carry as dead is refused
    (:data:`REFUSE_TRANSITIONING_NOT_A_DEAD_ROW`): a caller that thinks it
    knows which corpse it is transitioning and is wrong about that must not
    silently fall back to the old, unsafe "apply to everyone" behaviour.
    """
    if type(roster) is not tuple:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "roster must be a tuple of FieldMob")
    if type(register) is not DeathRegister:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "register must be a typed DeathRegister")
    if ledger is not None and type(ledger) is not mob_combat.CombatLedger:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "ledger must be a typed mob_combat.CombatLedger or None")
    if transitioning is not None:
        if (
            type(transitioning) is not tuple or len(transitioning) != 2
            or type(transitioning[0]) is not str
            or type(transitioning[1]) is not int
            or type(transitioning[1]) is bool
        ):
            raise MobDeathContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "transitioning must be a (scene, actor_identity) tuple or "
                "None, not %r" % (transitioning,))
        if not register.is_dead(transitioning[1], transitioning[0]):
            raise MobDeathContractError(
                REFUSE_TRANSITIONING_NOT_A_DEAD_ROW,
                "transitioning names identity 0x%X in scene %r, which the "
                "register does not carry as dead - a caller composing a "
                "specific corpse's frame must be right about which corpse it "
                "is, or every other corpse's timer would fall back to the "
                "unsafe pre-fix behaviour" % (
                    transitioning[1], transitioning[0]),
            )
    # EVERY DEAD IDENTITY MUST HAVE A ROW HERE.  Hand this the LIVING roster -
    # which live_roster(), exported from this same module, is exactly what a
    # caller reaches for when the sentence is "build the census from the
    # living" - and without this check the corpses are simply absent from the
    # result: the override comes back empty, every one of them stands back up
    # at full HP on the rebuild, and nothing raises.  A skipped corpse is not
    # a handled corpse.
    #
    # Checked by (scene, actor_identity), not bare identity (COO-DECISION
    # 2026-08-27T22:49+07:00): a register that also carries a DIFFERENT
    # scene's dead mob sharing this wire identity must not be mistaken for
    # "this roster forgot a row" - that dead mob simply belongs to a roster
    # this call was never given.
    #
    # ROUND qb70g2 (pf-adversary D1, measured end to end): that sentence was
    # only half true in code.  The (scene, identity) key stopped the
    # SHARED-identity confusion, but a record from a scene this roster does
    # not cover at all still landed in ``missing`` and refused - so one
    # authorized kill in Bg0002 made every later bg0001 recompose raise,
    # outside runtime.py's compose catch-all, and the register survives the
    # trip BY DESIGN (it is per-(identity, scene) so deaths persist across
    # scene changes).  A foreign-scene record is now what the comment above
    # always said it was: a row for a roster this call was never given -
    # ignored here, consumed when THAT scene composes.  A record in one of
    # THIS roster's own scenes with no roster row is still the real drift
    # this check exists for, and still refuses by name.
    roster_keys = set((m.scene, m.actor_identity) for m in roster)
    roster_scenes = set(m.scene for m in roster)
    missing = tuple(
        record.actor_identity for record in register.records
        if record.scene in roster_scenes
        and (record.scene, record.actor_identity) not in roster_keys
    )
    if missing:
        raise MobDeathContractError(
            REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER,
            "the register carries %s and this roster has no row for them: "
            "pass the FULL roster, not the living one - the dead need entries "
            "too, which is the whole point of this call" % (
                ", ".join("0x%X" % i for i in missing)),
        )
    entries = []
    for mob in roster:
        _require_mob(mob)
        if not register.is_dead(mob.actor_identity, mob.scene):
            current_hp = None
            if ledger is not None:
                # balance_of raises mob_combat's own named refusal when the
                # ledger and the roster were built from different rosters.
                current_hp = _balance_in(ledger, mob.actor_identity)
                if current_hp == HP_WHEN_DEAD:
                    # Dead in the arithmetic and alive in the register: the
                    # kill was computed and never finished.  Sending a live
                    # body resurrects it, sending a corpse claims a kill
                    # nobody committed, so this refuses and names both.
                    raise MobDeathContractError(
                        REFUSE_LEDGER_DISAGREES_WITH_REGISTER,
                        "identity 0x%X stands at 0 HP in the ledger and is "
                        "not in the death register: call mob_death.kill for "
                        "it, or re-open the ledger" % mob.actor_identity,
                    )
            entries.append(field_mobs.hostile_actor_entry(
                legacy, mob, current_hp=current_hp, faction=faction,
                with_name=with_name))
            continue
        row = register.record_of(mob.actor_identity, mob.scene)
        if ledger is not None:
            # The mirror of the case above: dead in the register and standing
            # in the arithmetic.  Sending the corpse would be right on the
            # wire and wrong in the ledger, and the next hit on it would be
            # answered with a real damage number for a monster already down.
            standing = _balance_in(ledger, mob.actor_identity)
            if standing != HP_WHEN_DEAD:
                raise MobDeathContractError(
                    REFUSE_LEDGER_DISAGREES_WITH_REGISTER,
                    "identity 0x%X is in the death register and stands at %d "
                    "HP in the ledger: the two were built from different "
                    "runs" % (mob.actor_identity, standing),
                )
        if row.max_hp != mob.max_hp:
            raise MobDeathContractError(
                REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER,
                "identity 0x%X died at a ceiling of %d and the roster says "
                "%d: the two were built from different rosters" % (
                    mob.actor_identity, row.max_hp, mob.max_hp),
            )
        # THE RE-ARM FIX ITSELF.  With no ``transitioning`` named, every dead
        # row still gets the scalar ``dead_timer`` (old behaviour, pinned by
        # every existing single-corpse test).  With one named, only THAT row
        # gets ``dead_timer``; every other corpse holds at
        # :data:`DEAD_TIMER_SECONDS` -- its steady state -- instead of being
        # re-armed to whatever timer the CURRENT transition is composing.
        row_timer = dead_timer
        if transitioning is not None and (
            mob.scene, mob.actor_identity) != transitioning:
            row_timer = DEAD_TIMER_SECONDS
        entries.append(death_actor_entry(
            legacy, mob, death_timer=row_timer, faction=faction,
            with_name=with_name))
    return entries


def repopulation_frames(
    legacy: Any,
    roster: tuple[FieldMob, ...],
    register: DeathRegister,
    *,
    ledger: Any = None,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    with_name: bool = True,
    dead_timer: float = DEAD_TIMER_SECONDS,
) -> tuple[bytes, bytes]:
    """One collection for a whole scene, with the dead sent as corpses.

    ``ledger`` is forwarded, and it was MISSING from this signature in the
    first draft - so the module's own whole-scene helper was structurally
    unable to take the safe path and silently re-sent every living monster at
    its ceiling, which is the exact hazard :func:`repopulation_entries`
    documents.  A convenience wrapper that cannot express the safe call is not
    a convenience.
    """
    entries = repopulation_entries(
        legacy, roster, register, ledger=ledger, faction=faction,
        with_name=with_name, dead_timer=dead_timer,
    )
    # An empty collection is a COUNT that is out of range, not a type error:
    # the old name said "this is not a typed record" about a perfectly typed
    # empty roster, which is a refusal that misdescribes what happened.
    _require_int(len(entries), "entry count", 1, 0xFFFF)
    pc, frame = legacy.make_runtime_remote_actors(entries)
    if frame != legacy.frame_pc(pc):
        raise MobDeathContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN, "repopulation frame drift")
    return pc, frame


def corpse_override(
    legacy: Any,
    roster: tuple[FieldMob, ...],
    register: DeathRegister,
    *,
    ledger: Any = None,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    with_name: bool = True,
    dead_timer: float = DEAD_TIMER_SECONDS,
) -> dict[int, bytes]:
    """Identity -> entry, for a census that must not stand the dead back up.

    THIS IS THE FUNCTION THE REAL CARRIER NEEDS, and the first draft of this
    module did not have it.  :func:`repopulation_entries` builds a collection
    of THIS lane's roster (~~thirteen~~ four since round 8ftmbx), but
    ``field_mobs`` says in its own
    docstring that sending that collection alongside the scene census puts
    those identities on the wire twice, and that "the correct wiring is the
    OVERRIDE, not the second collection".  The census the server actually
    ships (``world_population``) rebuilds every placement at full HP, reads
    neither the ledger nor this register, and takes no hook - so a wiring line
    that says "build the collection with repopulation_entries" either drops
    the other hundred-odd actors or gets ignored, and the corpses stand up
    either way.

    What comes back here is a lookup a census can apply to the entries it was
    going to send anyway: for every identity in it, use THIS entry instead.
    What is IN it: every identity the register carries, and - when a ``ledger``
    is passed - every living monster standing below its ceiling, because the
    census would otherwise heal those too.  Nothing else, so a census that
    applies it verbatim changes nothing it was not going to get wrong.
    """
    entries = repopulation_entries(
        legacy, roster, register, ledger=ledger, faction=faction,
        with_name=with_name, dead_timer=dead_timer,
    )
    override: dict[int, bytes] = {}
    for mob, entry in zip(roster, entries):
        if register.is_dead(mob.actor_identity, mob.scene):
            override[mob.actor_identity] = entry
            continue
        if ledger is not None and _balance_in(
                ledger, mob.actor_identity) != mob.max_hp:
            override[mob.actor_identity] = entry
    return override


def full_roster_override(
    legacy: Any,
    roster: tuple[FieldMob, ...],
    register: DeathRegister,
    *,
    ledger: Any = None,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    with_name: bool = True,
    dead_timer: float = DEAD_TIMER_SECONDS,
    transitioning: tuple[str, int] | None = None,
) -> dict[int, bytes]:
    """Identity -> entry, for EVERY roster member, not just the ones that changed.

    ``transitioning`` PASSES STRAIGHT THROUGH to
    :func:`repopulation_entries` -- see that function's own docstring for the
    CODEX_URGENT 2026-09-01T20:40+07:00 re-arm fix this exists to carry.
    ``None`` (the default) is the old scalar-to-everyone behaviour, unchanged.

    THIS CLOSES THE GAP ``field_mobs.py`` DESCRIBES AS "never sent, never
    observed".  :func:`corpse_override` deliberately narrows its result to
    identities whose body differs from what the census sends by default
    (dead, or alive below its ceiling), because the round that wrote it was
    scoped to not resurrecting or over-healing anyone - a census override
    call site that applies ONLY changed identities is cheap and a no-op until
    something has happened.  What that scoping costs a caller: a
    field mob nobody has ever hit is not in the dict, so a census that applies
    only :func:`corpse_override` ships it exactly as ``world_population``
    built it - HP 100, nameless (P30 excepted), faction 0.  BUILD-004 asks for
    the opposite: red-named, hostile monsters standing in the field from the
    first byte the client ever sees, not from the first hit.

    This is that function.  It calls the SAME :func:`repopulation_entries`
    :func:`corpse_override` already calls - the one that already gives every
    living roster member a :func:`field_mobs.hostile_actor_entry` body and
    every dead one a :func:`death_actor_entry` corpse - and keeps ALL of it
    instead of filtering to the delta.  For identities that are dead or
    damaged it returns byte-identical entries to ``corpse_override`` (both
    read the same register/ledger through the same helper); the only
    behavioural difference is that a monster nobody has touched is now IN the
    dict too, at its full-HP hostile body instead of being absent.

    A caller with an existing ``corpse_override`` call site can swap the
    function name and nothing else: the arguments are identical in name,
    order and default, because the delta-only behaviour was never a
    contract this lane asked for - it was the cheapest thing that answered
    MOB-DEATH-001's own question, and the wider one was left for the round
    that had a reason to build it.  This round is that reason.

    NONCLAIMS.  This does not touch, widen or bypass the death-scope gate
    (``SANCTIONED_FIRST_TARGET_IDENTITY`` / ``SANCTIONING_RULING``): a
    non-P30 field mob can show a hostile body and take damage the moment a
    census applies this override, but :func:`kill` still refuses to let it
    actually die until ``widened=`` names a later ruling, exactly as it does
    today - a monster that never dies while the gate holds is BUILD-004's
    claim (the monster exists, is real and is hostile), not BUILD-005's
    (every one of them can be killed), and the two are not conflated here.
    It does not change what ``runtime.py`` calls: nothing in this tree wires
    this function to the census yet, so a boot with no wiring change is
    byte-for-byte what it was before this function existed.
    [STALE as of runtime.py, round q4z3vi, 2026-08-26T22:4x+07:00]
    [MEASURED, by call-site reading on ``pirate-force-server@3036b03``]: the
    swap HAS been made - ``runtime.py``'s census-composition call site now
    reads ``mob_death.full_roster_override(...)`` where it used to read
    ``mob_death.corpse_override(...)``, unconditionally, on a flagless boot.
    Confirmed independently (not copied from the chief's own letter) by
    reading the call site itself; corroborated by
    ``notes_to_chief/20260826_2245_CHIEF-REPLY-LANE-B-full_roster_override-landed-plus-adversary-found-a-vacuous-assertion.md``,
    which also reports the twelve pins this swap turned red (see below) are
    fixed and the full suite is green. What is still true from the sentence
    above: this function itself still does not decide what ``runtime.py``
    calls - that decision was made in ``runtime.py``, the chief's file, not
    here - and BUILD-004/BUILD-005's client-observable question (does a
    player see any of this) is untouched by the swap; see the paragraph
    below for that.

    WIRE LAYER, round 1cwih0 (2026-08-26): chief tried wiring this in and hit
    12 red pins across FOUR files (``tests/test_world_census_wiring.py`` x9,
    plus one each in ``tests/test_ground_loot_dispatch.py``,
    ``tests/test_ground_loot_nameprop_hypothesis.py`` and
    ``tests/test_population_adapter.py`` - chief's own letter only named the
    first file).  All twelve reduce to ONE mechanism, checked by hand per
    roster identity, not assumed: every identity this function's roster
    covers gets the SAME 5-byte ``FACTION_SPLICE_BYTES`` treatment
    :func:`hostile_actor_entry` already gives it, and P30/``0x201F``
    (Tornado Eagle) is simply the one member of the roster that is ALSO part
    of ``world_population``'s own frozen pinned control set
    (``0, 30, 91``), so it is the one that shows up at every rung size
    (3/20/60/115) while the other twelve only show up once a rung is large
    enough to include their placement.  This part is a wire-layer fact, not
    a guess: it is a no-op to fix ``corpse_override``/``full_roster_override``
    themselves, since the shape is exactly what
    ``test_full_roster_override_covers_every_identity_untouched_or_not``
    already pinned when this function was written - the 12 external pins are
    the ones out of date, not this function.

    WHAT THIS DOES NOT SETTLE: whether the client actually renders any of
    these identities as hostile/red once this ships (~~thirteen~~ four since
    round 8ftmbx).  GT-032's
    passing red-name/red-border result was measured on ``0x2001``
    ("Navy Transfer"), which is NOT a member of this roster - nobody has
    reproduced that result for ``0x201F`` or any of the other twelve.
    ``pf_bridge/notes_to_chief/20260825_1420_RE-067-TICKET-DRAFT-what-decides-name-color.md``
    (open) found the client currently classes ``0x201F`` into the PLAYER
    name-color slot,
    not the NPC slot GT-032 used, and ``GT-034``'s own P4 nonclaim records
    that ``0x201F`` may already render red-bordered from ``faction=6`` in
    client-side tables with NO server splice at all - "this is genuinely
    unknown" in that ticket's own words.  So this function's byte-level
    change is real and well-understood; whether it is the thing that makes a
    player see a red monster is exactly what ``GT-084`` (queued, not
    delayed) and ``RE-067`` (open) exist to answer, and this round does not
    pre-empt either one.
    [STALE as of ``pf_bridge/CLIENT_RE_QUEUE.md`` chief R165, 2026-08-25
    ~17:0x+07:00 - already stale when this paragraph was WRITTEN in round
    1cwih0 on 2026-08-26, not just stale since] [MEASURED, by reading
    ``CLIENT_RE_QUEUE.md`` line 1382 and its result block]: ``RE-067`` is
    CLOSED, not open - PASS/MIXED. The item-label half PASSed (selector
    pinned). The actor half closed BOUNDED NEGATIVE: the client's
    ``NameBoardNPC::update`` does not read ``actor_type`` as a colour
    selector, no direct/recursive-decodable path from ``NPCAttr faction``,
    a relation comparator, or the ``FONT_COLOR`` loader was found feeding
    it, and the upstream setter's own value has no known semantic - "cannot
    be named from the evidence available" in that result's own words. That
    is a real, static-layer answer, not silence: nobody has found what
    decides an actor name's colour, and the search that tried (RE-067,
    followed up by RE-068, also closed BOUNDED NEGATIVE on the same
    question from a different angle) has no successor ticket open in
    ``CLIENT_RE_QUEUE.md`` as of this correction. So the sentence above
    should read: whether a player sees a red monster is exactly what
    ``GT-084``/``RIDER-084-A`` (client-observable layer, queued not
    delayed) exists to answer - RE-067/RE-068 already answered what they
    could at the static layer, and what they could not answer they closed
    as a measured ceiling, not an open question waiting on more static
    work.
    [STALE as of ``pf_bridge/CLIENT_RE_QUEUE.md`` chief R163, 2026-08-25
    ~15:xx+07:00] [MEASURED, by reading the draft ticket file itself and
    ``CLIENT_RE_QUEUE.md``'s note on it, line ~1400]: the sentence above
    citing the RE-067 TICKET-DRAFT for "the client currently classes
    ``0x201F`` into the PLAYER name-color slot, not the NPC slot GT-032
    used" is not just outdated, it is a draft theory chief R163 struck
    down and retracted BEFORE RE-067 was even opened - the re-derived
    evidence is that the server always sends ``actor_type=4`` for this
    identity (a real NPC actor class), not that the client misroutes it
    into a player slot. RE-067's actual result (cited above) supersedes
    this anyway: the actor half found no colour-deciding read of
    ``actor_type`` at all, so neither "classed as player" nor "classed as
    NPC" is what determines the label's colour - the driver is simply
    unidentified.
    """
    entries = repopulation_entries(
        legacy, roster, register, ledger=ledger, faction=faction,
        with_name=with_name, dead_timer=dead_timer,
        transitioning=transitioning,
    )
    return {mob.actor_identity: entry for mob, entry in zip(roster, entries)}


def roster_override_coverage(
    override: dict[int, bytes],
    census_identities: Any,
) -> dict[str, Any]:
    """Which override identities actually land in a built census, measured.

    GT-084 (2026-08-27, attended) could not tell from the console whether
    ``full_roster_override``'s splice reached the wire at all: this
    project's console prints one undifferentiated
    ``world_census_committed_actors_N`` line per boot, with no per-identity
    breakdown, so the attended tester's own recommendation (item (5).4 of
    that ticket's result letter) was "give console a way to confirm hostile
    frames went out before calling the owner to sit down again" - this is
    that confirmation, computed rather than assumed.  ``census_identities``
    is whatever the caller's build actually produced
    (``generation.actor_identities`` at the ``runtime.py`` call site), not a
    re-derivation of what it SHOULD contain, so a caller that hands this the
    real dispatch output gets a real answer, and a caller whose census
    changed shape gets a real ``missing`` list instead of a silently wrong
    "all matched".

    NONCLAIMS.  Does not know whether the client renders any matched
    identity as hostile/red - that is GT-084/RIDER-084-A's own open
    question, at a layer this function cannot see.  Coverage is computed at
    the wire/DB layer only.
    """
    if type(override) is not dict:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "override must be a dict")
    for identity, entry in override.items():
        if type(identity) is not int or type(identity) is bool:
            raise MobDeathContractError(
                REFUSE_OVERRIDE_ENTRY_NOT_INT_BYTES,
                "override key must be an int identity")
        if type(entry) is not bytes:
            raise MobDeathContractError(
                REFUSE_OVERRIDE_ENTRY_NOT_INT_BYTES,
                "override value must be bytes")
    census_set = set(census_identities)
    matched = tuple(sorted(i for i in override if i in census_set))
    missing = tuple(sorted(i for i in override if i not in census_set))
    return {
        "matched": matched,
        "missing": missing,
        "matched_count": len(matched),
        "total": len(override),
    }


def describe_roster_override_coverage(
    override: dict[int, bytes],
    census_identities: Any,
) -> tuple[str, ...]:
    """Console lines for :func:`roster_override_coverage`, ASCII-only.

    Same shape as :func:`describe_death`: a tuple of plain-ASCII lines a
    caller can ``print()`` on the bridge's cp874 console with no further
    escaping.  Written so a wiring pass can add ONE print call at the
    ``full_roster_override`` / ``_apply_mob_death_census_override`` call
    site in ``runtime.py`` and have every future attended round read the
    answer to GT-084 item (5).4 straight off the console, with no attended
    session needed to get it.
    """
    coverage = roster_override_coverage(override, census_identities)
    missing = (
        "none" if not coverage["missing"]
        else ",".join("0x%X" % identity for identity in coverage["missing"])
    )
    return (
        "MOB_DEATH_ROSTER_OVERRIDE_COVERAGE matched=%d/%d missing=%s" % (
            coverage["matched_count"], coverage["total"], missing),
    )


def hostile_census_frames(
    legacy: Any,
    anchor: tuple[float, float, float],
    actor_count: int,
    roster: tuple[FieldMob, ...],
    register: DeathRegister,
    *,
    ledger: Any = None,
    scene_id: int = SCENE_ID,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    with_name: bool = True,
    dead_timer: float = DEAD_TIMER_SECONDS,
    count_source: str = world_population.COUNT_SOURCE_CALLER,
    transitioning: tuple[str, int] | None = None,
) -> tuple[bytes, bytes]:
    """A hit/death frame that carries the WHOLE census, not one actor.

    ``transitioning`` PASSES STRAIGHT THROUGH to :func:`full_roster_override`
    / :func:`repopulation_entries` -- see the latter's docstring for the
    CODEX_URGENT 2026-09-01T20:40+07:00 re-arm fix.  ``None`` (the default)
    keeps this function's old byte-for-byte behaviour.

    WHY THIS EXISTS.  ``mob_combat.bar_frames`` and this module's own
    ``death_frames`` each compose a NONEMPTY ONE-ENTRY
    ``legacy.make_runtime_remote_actors([entry])`` collection - flagged as an
    "[OPEN RISK, NOT MEASURED]" in both functions' docstrings since round
    ``yjty8a``.  ``RE-092`` (2026-08-26 22:23) closed that risk from theory
    to measurement: the client's remote-actor consumer is confirmed
    replace-by-omission (not merge), so a live one-entry frame reaching the
    unflagged path removes every OTHER non-exempt actor from the client's
    registry in the same call - the town would empty out on the first hit or
    kill, not just refresh one monster's bar.  Chief's escalation
    (``pf_bridge/notes_to_chief/20260827_0920_CHIEF-URGENT-combat-death-
    frames-confirmed-world-wipe-unconditional-on-flagless-path.md``) asked
    this lane to design the fix; this function is that design's pure half.

    THE FIX IS ENCODER REUSE, NOT A NEW SELECTOR - the same rule arrival's
    own census override already followed.  This rebuilds the census fresh
    with :func:`world_population.build_world_population` (SAME encoder,
    SAME anchor/scene/count a caller already has on hand - ``runtime.py``
    keeps ``population_refresh_anchor``/``world_census_actor_count`` as
    session state since arrival), then splices EVERY roster member's live
    body in with :func:`full_roster_override` (not :func:`corpse_override`:
    the delta-only override would leave an untouched-but-still-alive hostile
    roster member with the plain, non-hostile body ``build_world_population``
    gives everyone by default, undoing the red/hostile styling arrival
    already gave it) through
    :func:`world_population.apply_identity_override` - the same three calls
    arrival's own ``runtime.py:_apply_mob_death_census_override`` composes,
    reimplemented independently in a lane-B module (see that function's
    docstring for why it is a reimplementation and not an import).

    WHAT THIS DOES NOT DO.  It does not decide WHEN a caller uses this
    instead of ``bar_frames``/``death_frames`` - both of those functions are
    left exactly as they were, still callable, still one-entry, because
    removing them would be an editorial decision this lane does not own
    without ``runtime.py``'s cooperation (only ``runtime.py`` knows whether
    every caller of the one-entry functions has been swapped). It does not
    retain or store anything - the caller still owns dispatch and the
    session-state question of what anchor/count to pass belongs to
    ``runtime.py``, this lane's ``CORE-REQUEST`` for the wiring line spells
    out exactly what changes there. It COSTS more than the one-entry frame
    (a full ``actor_count``-body rebuild per hit/death instead of one entry)
    - not measured against a real session's frame-rate budget this round,
    flagged for whoever wires it in.

    NONCLAIM.  Byte-for-byte proof that this composes correctly is this
    module's own test (against the real 115-actor bg0001 census); whether a
    live client that receives this instead of the one-entry frame still
    shows the target's bar move and every other actor unchanged is
    client-observable and unproven this round - the same evidence gap
    GT-084/RIDER-084-A already track for the arrival-census fix.

    LEDGER IS REQUIRED HERE, NOT OPTIONAL, EVEN THOUGH THE FAMILY THIS CALLS
    ACCEPTS ``None``.  ``full_roster_override``/``repopulation_entries``
    legitimately default ``ledger`` to ``None`` because a caller building a
    scene before any ledger has been opened still needs a census - that is a
    real, still-supported call shape for THOSE functions.  This function does
    not have that excuse: it exists, by its own WHY-THIS-EXISTS paragraph
    above, to be composed on every hit/death frame, and a hit/death frame
    cannot exist without :func:`mob_combat.strike` having already required a
    typed :class:`mob_combat.CombatLedger`.  So every real call site of THIS
    function already holds a live ledger, and one that omits it is not a
    legitimate early-boot caller - it is the exact bug class this round exists
    to close, just for HP instead of existence: every living-but-damaged
    monster silently re-renders at its ceiling HP on the wire, with nothing
    that fails or even logs.  Proven by execution (pf-adversary, round
    sifsfg): damage a mob to 3828/3857 via a real ``strike()``, call this
    function without ``ledger=``, and the composed frame carries the mob's
    FULL-HP body.  Per this project's own convention (silent-but-dangerous is
    never allowed to pass quietly - see ``MobDeathContractError`` throughout
    this module and ``mob_combat``'s own typed-ledger requirement in
    ``strike``), this refuses instead: ``ledger=None`` raises
    :data:`REFUSE_CENSUS_FRAME_WITHOUT_A_LEDGER` immediately, before either
    sub-call runs, rather than composing a frame that quietly heals every
    other damaged monster.  A caller with a genuine reason to render the
    roster at ceiling HP (no combat has happened yet) should call
    ``full_roster_override``/``repopulation_frames`` directly with
    ``ledger=None`` - those functions' contracts already say that is a
    supported meaning; this one's does not.

    ~~ONE-CORPSE LIMIT, NAMED SO NOBODY WIDENS THE DEATH GATE WITHOUT SEEING
    IT.~~ CLOSED, CODEX_URGENT 2026-09-01T20:40+07:00 / COO-DECISION
    2026-09-01T21:48+07:00.  This paragraph used to say ``dead_timer`` was a
    single value applied to every register member and that the day
    ``SANCTIONING_RULING``/``SANCTIONED_FIRST_TARGET_IDENTITY`` stopped
    guaranteeing at most one dead identity at a time, composing one corpse's
    DYING frame would re-arm every OTHER already-dead corpse back to "dying"
    on the wire.  That day already came - ``WIDENING_RULINGS`` above lets
    several identities be dead at once - and Codex's audit proved the
    regression by re-reading this exact call chain, not by re-deriving the
    warning fresh.  ``transitioning=(scene, actor_identity)`` is the fix: name
    the ONE row this call is about and every other dead row holds at
    :data:`DEAD_TIMER_SECONDS` instead of following ``dead_timer``.  A caller
    that still passes ``transitioning=None`` gets the OLD unsafe behaviour
    unchanged - this is opt-in, not a silent behaviour change, because a
    caller this module cannot see (``runtime.py``, the chief's file) has to
    be the one that starts passing the identity it already knows it just
    killed; see this round's ``CORE-REQUEST``.
    """
    if ledger is None:
        raise MobDeathContractError(
            REFUSE_CENSUS_FRAME_WITHOUT_A_LEDGER,
            "hostile_census_frames needs the live ledger from the hit/death "
            "step that is calling it: without one, every living-but-damaged "
            "monster in the roster is re-sent at its ceiling HP, silently "
            "healing every actor this frame was not about. If there is "
            "genuinely no combat yet and the roster should render at ceiling "
            "HP, call full_roster_override/repopulation_frames directly with "
            "ledger=None - that is a supported meaning there, not here.",
        )
    generation = world_population.build_world_population(
        legacy, anchor, actor_count, scene_id=scene_id,
        count_source=count_source,
    )
    override = full_roster_override(
        legacy, roster, register, ledger=ledger, faction=faction,
        with_name=with_name, dead_timer=dead_timer,
        transitioning=transitioning,
    )
    composed = world_population.apply_identity_override(
        legacy, generation, override)
    return composed.pc, composed.frame


def describe_death(step: DeathStep) -> tuple[str, ...]:
    """Console lines for a kill, in the shape the runtime console prints."""
    if type(step) is not DeathStep:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "step must be a typed DeathStep")
    record = step.record
    return (
        "MOB-DEATH-001 kill: performer 0x%X -> target 0x%X (ceiling %d)" % (
            record.killer_identity, record.actor_identity, record.max_hp),
        # The timers come off the STEP, not off the module constants: a line
        # that prints 20.0 for a frame carrying something else is a diagnostic
        # that lies exactly when it is needed.  And the GT-022/GT-025 sentence
        # this line used to carry is gone - those runs watched a NAMELESS,
        # FACTIONLESS body (mask 0x038C) and this frame is mask 0x078D, so
        # "this is the frame they watched" contradicted nonclaim 6 twenty
        # lines above it.
        "  dying frame %d bytes, timer %r (> 0, latches 0x%X) - same SHAPE as "
        "the frame GT-022/GT-025 watched drop an NPC, not the same body" % (
            len(step.dying_frame), step.dying_timer, DYING_LATCH_WRITE_VA),
        "  dead frame %d bytes, timer %r (<= 0, gates 0x%X -> "
        "CActorTask_Dead 0x%X) - gate is static; its effect has never been "
        "observed" % (
            len(step.dead_frame), step.dead_timer, DEATH_TASK_GATE_VA,
            DEATH_TASK_CTOR_VA),
        "  hold %d ms between them [COO-confirmed provisional, unmeasured]" % (
            step.hold_ms),
        "  register now holds %d dead: %s" % (
            len(step.register.records),
            ", ".join("0x%X" % i for i in step.register.identities())),
    )


PIN_ID = "mob_death_second_half_001"
PIN_BUILD_ORDER = MOB_DEATH_BUILD_ORDER
PIN_LANE = MOB_DEATH_LANE
# ~~field_mobs.CONTROL_PLACEMENT_INDEX~~ -- round szdkgs moved that constant
# to the roster's own control row (placement 103), and this pin must NOT
# follow it: what this document pins is a kill on the SANCTIONED FIRST TARGET
# 0x201F, an actor named by PANYA-RULINGS-FOUR, not by whichever row the table
# happens to use as its control.  Placement 30 is still in the shipped roster
# (as the legacy set-number reading, pending migration), so the pin is
# unchanged this round; when that row is migrated, this pin moves WITH a
# ruling, not with a table.
# ~~PIN_PLACEMENT_INDEX = field_mobs.LEGACY_SETNUM_CONTROL_PLACEMENT_INDEX~~
# ROUND 8ftmbx: that row IS migrated now, and the condition the paragraph
# above set is met -- the pin moves on a RULING, and here is the ruling.
# COO-DECISION 2026-08-29T00:41+07:00 item 4 says M4 is proven on n_ID 916
# through this module's own kill path ("use mob_death.kill(...) directly,
# under the existing 916 order"), and forbids inventing a target's HP to suit
# a test.  So the pinned subject is the actor that ruling names, which is this
# lane's control row -- and, unlike placement 30, an actor the shipped roster
# still contains.  What placement 30's kill pinned is not deleted: the
# document keeps `sanctioned_first_target_identity` and
# `pin_target_is_the_sanctioned_one`, and the second one is now False and says
# so out loud rather than the pin quietly changing subject.
PIN_PLACEMENT_INDEX = field_mobs.CONTROL_PLACEMENT_INDEX
# The ruling the pinned kill travels under, now that its subject is no longer
# SANCTIONED_FIRST_TARGET_IDENTITY.  Named here rather than passed by a caller
# so the pin cannot be produced under a ruling nobody wrote down.
PIN_WIDENING_RULING = (
    "COO-DECISION widen-death-scope-916-training-iron-man "
    "2026-08-27T09:55+07:00 (ref PANYA-DECISION 2026-08-27T09:50+07:00 "
    "section 3, supersedes COO 0954)"
)


def pin_document(legacy: Any, mob: FieldMob, killer_identity: int = 0x750059) -> dict:
    """The numbers a report should quote, computed rather than transcribed.

    Lives in ``scenarios/`` because that is where this project keeps its pins;
    it is NOT a scenario, declares so in its own body, and no loader reads it.
    The kill it pins is driven all the way through ``mob_combat`` - an attacker
    strong enough to reach zero in one hit - so the pin proves the two lanes
    are joined rather than merely present in the same tree.
    """
    _require_mob(mob)
    ledger = mob_combat.open_ledger()
    attacker = mob_combat.Combatant(
        level=1000, ability_str=100000, ability_con=0)
    step = mob_combat.strike(
        legacy, None, ledger, None, mob, killer_identity, attacker)
    widened = (
        None if mob.actor_identity == SANCTIONED_FIRST_TARGET_IDENTITY
        else PIN_WIDENING_RULING
    )
    death = kill(legacy, mob, step.outcome, DeathRegister(), widened=widened)
    live_body = field_mobs.hostile_npc_attr(
        legacy, mob, current_hp=mob.max_hp)
    corpse_body = corpse_npc_attr(legacy, mob, death_timer=DEAD_TIMER_SECONDS)
    return {
        "pin_id": PIN_ID,
        "build_order": PIN_BUILD_ORDER,
        "lane": PIN_LANE,
        "milestone": MOB_DEATH_MILESTONE,
        "production_allowed": production_allowed,
        "test_only": test_only,
        "not_a_scenario": True,
        "target_identity": mob.actor_identity,
        "target_name": ascii(mob.display_name),
        "target_faction": field_mobs.FIELD_MOB_FACTION,
        "max_hp": mob.max_hp,
        "hp_when_dead": HP_WHEN_DEAD,
        "killer_identity": killer_identity,
        "damage_wire": step.outcome.damage_wire,
        "announce_frame_bytes": len(step.announce_frame),
        "bar_frame_bytes": len(step.bar_frame),
        "dying_timer_seconds": DYING_TIMER_SECONDS,
        "dead_timer_seconds": DEAD_TIMER_SECONDS,
        "dying_frame_bytes": len(death.dying_frame),
        "dead_frame_bytes": len(death.dead_frame),
        "hold_ms": death.hold_ms,
        "hold_ms_is_ours": True,
        "live_body_bytes": len(live_body),
        "corpse_body_bytes": len(corpse_body),
        "basic_mask_live": "0x%04X" % basic_mask_of(
            legacy, live_body, mob.actor_identity),
        "basic_mask_corpse": "0x%04X" % basic_mask_of(
            legacy, corpse_body, mob.actor_identity),
        "death_timer_tag": "0x%02X" % DEATH_TIMER_TAG,
        "death_timer_object_offset": "0x%02X" % DEATH_TIMER_OBJECT_OFFSET,
        "dying_predicate_va": "0x%X" % DYING_PREDICATE_VA,
        "death_predicate_va": "0x%X" % DEATH_PREDICATE_VA,
        "death_task_gate_va": "0x%X" % DEATH_TASK_GATE_VA,
        "death_task_ctor_va": "0x%X" % DEATH_TASK_CTOR_VA,
        # Named with what it is: the string the static chain ends at, NOT a
        # thing anyone has watched play.  The first draft carried it as a bare
        # top-level fact next to measured byte counts, which is how a pin gets
        # quoted as evidence for the one claim this lane refuses to make.
        "death_animation_named_by_the_static_chain_never_observed":
            DEATH_ANIMATION_NAME,
        "predicate_pair_is_class_dependent": {
            "netnpc_actor_type_4_used_here": [
                "0x%X" % va for va in NETNPC_PREDICATE_VAS],
            "netactor_actor_type_2_not_used_here": [
                "0x%X" % va for va in NETACTOR_PREDICATE_VAS],
        },
        "sanctioned_first_target_identity": "0x%X" % (
            SANCTIONED_FIRST_TARGET_IDENTITY),
        "pin_target_is_the_sanctioned_one": (
            mob.actor_identity == SANCTIONED_FIRST_TARGET_IDENTITY),
        "register_generation_after_the_kill": death.register.generation,
        "wiring": MOB_DEATH_WIRING,
        "selection": "none_default_behaviour_no_scenario_flag",
        "nonclaims": list(MOB_DEATH_NONCLAIMS),
    }
