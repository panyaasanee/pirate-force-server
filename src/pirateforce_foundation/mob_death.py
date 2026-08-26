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

NOTHING IS INSTALLED.  No socket, no clock, no randomness, no database, no
global state, no import-time side effect.  Every function is a pure function of
its arguments and every state object is a frozen dataclass.  Contract breaches
raise :class:`MobDeathContractError` with a NAMED reason.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import struct
from typing import Any

from . import field_mobs
from . import mob_combat
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
SANCTIONING_RULING = "PANYA-RULINGS-FOUR 2026-08-25 18:15 +07:00 section 3"

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
BASIC_BIT_CURRENT_HP = 0x0004          # u32 tag 0x14 @ +0x44
BASIC_BIT_MAX_HP = 0x0008              # u32 tag 0x14 @ +0x48
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
    "hostile and nobody has seen one of those at zero HP",
    "a real attack input has never been observed producing the EA7D "
    "ActionVital that reaches mob_combat, so the inbound half of the kill is "
    "as unproven as the inbound half of the hit",
    "named AND hostile in one body has never been sent and never been "
    "observed; the corpse body inherits that nonclaim from field_mobs and "
    "adds a bit nobody has combined with it either (mask 0x078D)",
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
MOB_DEATH_REFUSAL_REASONS = (
    REFUSE_VALUE_NOT_INT,
    REFUSE_VALUE_OUT_OF_RANGE,
    REFUSE_TYPE_NOT_TYPED_RECORD,
    REFUSE_IDENTITY_NOT_POSITIVE,
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
    """One monster's death: who it was, who killed it, what it stood at."""

    actor_identity: int
    killer_identity: int
    max_hp: int

    def __post_init__(self) -> None:
        _require_identity(self.actor_identity, "actor identity")
        _require_identity(self.killer_identity, "killer identity")
        _require_int(self.max_hp, "max hp", 1, 0xFFFFFFFF)
        if self.actor_identity == self.killer_identity:
            raise MobDeathContractError(
                REFUSE_OUTCOME_NAMES_ANOTHER_MONSTER,
                "a monster cannot be its own killer on this lane")


@dataclass(frozen=True)
class DeathRegister:
    """Who is dead, as a tuple sorted by identity.

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
            if record.actor_identity in seen:
                raise MobDeathContractError(
                    REFUSE_DUPLICATE_REGISTER_IDENTITY,
                    "identity 0x%X appears twice" % record.actor_identity)
            seen.add(record.actor_identity)
        ordered = tuple(sorted(
            self.records, key=lambda row: row.actor_identity))
        if ordered != self.records:
            raise MobDeathContractError(
                REFUSE_REGISTER_NOT_SORTED,
                "register rows must be given in ascending identity order")
        _require_int(self.generation, "generation", 0, 2 ** 62)

    def identities(self) -> tuple[int, ...]:
        return tuple(row.actor_identity for row in self.records)

    def is_dead(self, actor_identity: int) -> bool:
        wanted = _require_identity(actor_identity, "actor identity")
        return any(row.actor_identity == wanted for row in self.records)

    def record_of(self, actor_identity: int) -> DeathRecord:
        wanted = _require_identity(actor_identity, "actor identity")
        for row in self.records:
            if row.actor_identity == wanted:
                return row
        raise MobDeathContractError(
            REFUSE_NOT_DEAD,
            "identity 0x%X is not in this register" % wanted)

    def with_death(self, record: DeathRecord) -> "DeathRegister":
        if type(record) is not DeathRecord:
            raise MobDeathContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "the addition must be a typed DeathRecord")
        if self.is_dead(record.actor_identity):
            raise MobDeathContractError(
                REFUSE_ALREADY_DEAD,
                "identity 0x%X is already in the register: a second kill on "
                "the same monster is a caller bug, not an event" % (
                    record.actor_identity),
            )
        return DeathRegister(
            tuple(sorted(
                self.records + (record,),
                key=lambda row: row.actor_identity)),
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
        BASIC_BIT_CURRENT_HP | BASIC_BIT_MAX_HP
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
    out += legacy.u32tag(U32_TAG, current_hp)                  # 0x0004
    out += legacy.u32tag(U32_TAG, mob.max_hp)                  # 0x0008
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
    """Where bit 0x0080 belongs: after max HP, before the scene id.

    Computed from the frozen serializers rather than written down, because the
    name field ahead of it is variable-length.  The head is checked against
    the body it is measuring, so a drift in ``make_npc_attr``'s field order
    refuses here instead of putting the timer in the wrong place.
    """
    head = (
        bytes(legacy.u8tag(DB_ATTRIBUTE_MASK_TAG, DB_ATTRIBUTE_IDENTITY_MASK))
        + bytes(legacy.qwordtag(IDENTITY_TAG, mob.actor_identity))
    )
    name = (
        bytes(legacy.wstr_tag(mob.display_name))
        if with_name and mob.display_name else b""
    )
    upto = (
        len(head) + 3 + len(name)
        + len(bytes(legacy.u32tag(U32_TAG, current_hp)))
        + len(bytes(legacy.u32tag(U32_TAG, mob.max_hp)))
    )
    expected = (
        head + timerless[len(head):len(head) + 3] + name
        + bytes(legacy.u32tag(U32_TAG, current_hp))
        + bytes(legacy.u32tag(U32_TAG, mob.max_hp))
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
        if not self.register.is_dead(self.record.actor_identity):
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
    if mob.actor_identity != SANCTIONED_FIRST_TARGET_IDENTITY:
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
    if live.is_dead(mob.actor_identity):
        raise MobDeathContractError(
            REFUSE_ALREADY_DEAD,
            "identity 0x%X is already dead: a second kill would send a second "
            "pair of frames for a corpse" % mob.actor_identity,
        )
    _require_int(hold_ms, "hold ms", 0, 60_000)
    record = DeathRecord(
        mob.actor_identity, outcome.attacker_identity, mob.max_hp)
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
    """The monsters that are still alive, in the order they were given."""
    if type(roster) is not tuple:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "roster must be a tuple of FieldMob")
    if type(register) is not DeathRegister:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "register must be a typed DeathRegister")
    for mob in roster:
        _require_mob(mob)
    dead = set(register.identities())
    return tuple(m for m in roster if m.actor_identity not in dead)


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
    # EVERY DEAD IDENTITY MUST HAVE A ROW HERE.  Hand this the LIVING roster -
    # which live_roster(), exported from this same module, is exactly what a
    # caller reaches for when the sentence is "build the census from the
    # living" - and without this check the corpses are simply absent from the
    # result: the override comes back empty, every one of them stands back up
    # at full HP on the rebuild, and nothing raises.  A skipped corpse is not
    # a handled corpse.
    missing = tuple(
        identity for identity in register.identities()
        if identity not in tuple(m.actor_identity for m in roster)
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
        if not register.is_dead(mob.actor_identity):
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
        row = register.record_of(mob.actor_identity)
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
        entries.append(death_actor_entry(
            legacy, mob, death_timer=dead_timer, faction=faction,
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
    of THIS lane's thirteen monsters, but ``field_mobs`` says in its own
    docstring that sending that collection alongside the scene census puts
    thirteen identities on the wire twice, and that "the correct wiring is the
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
        if register.is_dead(mob.actor_identity):
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
) -> dict[int, bytes]:
    """Identity -> entry, for EVERY roster member, not just the ones that changed.

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
    these thirteen identities as hostile/red once this ships.  GT-032's
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
PIN_PLACEMENT_INDEX = field_mobs.CONTROL_PLACEMENT_INDEX


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
    death = kill(legacy, mob, step.outcome, DeathRegister())
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
