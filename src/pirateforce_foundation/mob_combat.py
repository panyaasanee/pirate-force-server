"""LANE-B / MOB-COMBAT-001: the driver that turns a real hit into less HP.

WHAT THIS MODULE IS FOR.  M4 ("hit it, its blood drops, it dies") splits in
two, and the COO ruled the halves in order (COO-DECISION 2026-08-26T01:48+07:00,
section 3): first the driver that lowers a monster's HP from a REAL damage
number and feeds the threat table, then the death half.  This module is the
first half and only the first half.  It holds one integer balance per monster,
moves it by the damage the frozen formula computes, and composes the two frames
the client needs to show that movement: the hit announcement that floats the
number, and the actor frame that repaints the bar.

    damage number      <- the HYP-PF-024 formula, attacker profile vs defender
    balance            <- max_hp from field_mob_tables, moved only by a hit
    threat             <- handed to mob_aggro.apply_damage_threat, unchanged
    announce frame     <- CHitResult (vital 0x16F7), damage at entry +0x08
    bar frame          <- the field_mobs hostile body with a lower current_hp

NO FLAG, AND THAT IS THE POINT.  ``production_allowed`` is True, there is no
scenario id, no dispatch kwarg and no unlock object anywhere in this file.  The
proving lanes for both halves of this behaviour (HYP-PF-024 DAMAGE-MODEL-001,
HYP-PF-029, HYP-PF-038 HOSTILE-HP-LINK-001) are scenario-gated probes pinned to
one target, one ladder and one position; a version the owner boots without
flags cannot call any of them.  So the arithmetic and the two encoders are
RE-DERIVED here from the same static anchors, in general form, and the tests
pin this module's constants against the probe lanes' constants value by value.
This module imports NO probe lane; like ``field_mobs`` it takes the frozen V141
serializers as a passed-in ``legacy`` handle, and it takes ``mob_aggro`` the
same way.  BUT SAID PLAINLY, because an adversarial review was right to call
the softer version a dodge: passing a handle keeps mob_aggro's IMPORT claim
true and does NOT keep its REACHABILITY claim true.  A ``runtime.py`` that
passes ``mob_aggro`` in has made a lane reachable from production dispatch
through an edge no static scan of ``src/`` can see, because it is an argument.
So the threat handle is OPTIONAL here and the wiring line this lane hands the
chief passes ``None``.

THE COO ANSWERED THAT WRITE-UP ON 2026-08-26 (COO-DECISION 04:02, sections 1.3
and 2), and the answer was NOT "pass mob_aggro in".  It was: promote mob_aggro
where the scan can see it, and fold threat through a SEPARATE call after the
combat commit.  That call is ``mob_ai_control.damage_step``.  So this line
still passes ``None`` in v4 and in v5, the handle argument is now a test and
legacy-caller convenience rather than the production path, and the threat fold
has an owner with a name.

WHERE THE EVIDENCE FOR EACH HALF COMES FROM, AND WHERE IT STOPS.

* The number.  DAMAGE-MODEL-001 proved byte-exactly that the client computes
  nothing about damage: what floats over an actor is the signed i32 the server
  put at hit-entry +0x08, passed through abs() and printed with "%d".  So the
  server must say both halves itself.  This module says both halves and refuses
  to let them disagree: the number announced is the number subtracted, always,
  including when the subtraction is clamped (see the floor, below).
* The bar.  GT-035 (2026-08-25) watched a target's bar walk
  3857 -> 2893 -> 2893 -> 771 on a real client, driven by a frame pair of this
  SHAPE: hit frame announces, actor frame applies.  Four limits on that
  sentence, each one written here because an adversarial review of this module
  found the first draft had blurred it:
    - it is the CLIENT-OBSERVABLE layer only.  The report
      (reports/PF_HOSTILE_HP_LINK038_GT035_ATTENDED_RESULT_20260825.md) says on
      its own first lines that it must NEVER be cited as wire-layer evidence.
      This module's wire layer is the byte pins in its tests, not GT-035.
    - two observers agree on the TAIL of the ladder.  The first rung (3857 and
      the -964 that moves it) is SINGLE-SOURCE, from the run-2 video.
    - the frames GT-035 watched were NOT hostile: HYP-PF-038 composes its body
      with no faction field (BasicAttr mask 0x030D).  The body this module
      refreshes is the field_mobs hostile body (mask 0x070D), five bytes longer.
      field_mobs' own nonclaim therefore still stands here and is repeated in
      MOB_COMBAT_NONCLAIMS: named AND hostile together has never been observed.
    - "hostile" itself is unproven at the client: the target's name label
      rendered in the colour this client uses for PLAYERS, which is why RE-067
      is open.
      [STALE as of pf_bridge/CLIENT_RE_QUEUE.md chief R163/R165, 2026-08-25,
      round dvxb6f] [MEASURED, by reading CLIENT_RE_QUEUE.md]: RE-067 is
      CLOSED (PASS/MIXED), and the "rendered in PLAYER colour" theory was
      chief R163's own draft, retracted before RE-067 opened - the actor
      half closed BOUNDED NEGATIVE instead (no colour-deciding read of
      actor_type/faction/FONT_COLOR found; the real driver is unidentified,
      not "player colour"). See mob_death.py's full_roster_override
      docstring for the full correction and citations.
* What is NOT proven and is not claimed here: that a player's own click can
  reach this driver.  The inbound side is the SCENE-007 EA7D ActionVital the
  client already sends for an action on a target (``action_ack.py``), and no
  attended round has yet shown that shape arriving from a normal attack input
  on a hostile actor.  :func:`attack_from_observed_action` is written against
  that shape because it is the only inbound action shape this project has ever
  parsed, and the ticket that decides whether a real attack input produces it
  is the wiring step below, not a claim of this module.

THE FLOOR, STATED LOUDLY BECAUSE IT IS THE SEAM.  ``HP_FLOOR`` is 0, and the
death half is what lowered it.

    ~~Round mr1w26: the floor is 1.  A hit that would take a monster to zero
    lands it at 1 instead, because an HP of zero without the timer field is a
    state whose client behaviour nobody in this project has observed.  The
    next lane-B round builds that, and it attaches exactly here.~~
    STRUCK, NOT DELETED (round 7ptoku): that round is this one.  ``mob_death``
    composes the two frames the client's gate reads, so the reason for
    stopping at 1 is gone and a monster now reaches zero like it should.

The rest of the paragraph still holds and is why the seam is where it is: the
client's death gate is ``HP == 0 && timer <= 0`` -> 0x443990 ->
CActorTask_Dead 0x472810, so HP zero is only ever HALF the state.  This module
therefore still refuses to compose a LIVE body at zero - :func:`bar_frames`
says so by name - and hands the killing blow to ``mob_death``, which owns the
body that carries both halves.  ``field_mobs.hostile_npc_attr`` refuses an HP
of zero for the same reason and stays untouched by this round.

WHAT A KILLING BLOW RETURNS.  A hit that reaches zero composes the announce
frame and NO bar frame: the bar of a dead monster is not a bar, it is a
corpse, and the frames for it are ``mob_death.kill``'s to compose.  So on a
killing blow ``CombatStep.frames`` is one frame long and ``death_due`` is
True, which is the caller's signal to call the death lane - see
MOB_COMBAT_WIRING.

WHAT THE PLAYER SEES THAT THEY DID NOT SEE YESTERDAY.  Nothing yet, and this
paragraph is honest rather than promotional: the module sends nothing, because
the dispatch file that would call it (``runtime.py``) belongs to the chief.
What it delivers is that the wiring is now ONE call - see MOB_COMBAT_WIRING -
instead of a lane to design.  [PROPOSED, not measured] once that call exists,
hitting a monster in Port Royal moves that monster's bar on a flagless build.
It is PROPOSED rather than MEASURED for a named reason: nobody has yet observed
a real attack input producing the inbound EA7D shape this driver reads, and in
GT-035 nobody attacked anything - every frame was emitted by the server after
the player typed one line of chat.

[STALE as of runtime.py CORE-REQUEST-005, PR #63, round mdj01v,
2026-08-26T04:0x+07:00, COO-DECISION 2026-08-26T04:02+07:00] [MEASURED, by
call-site reading]: the call exists now.  ``attack_from_observed_action`` and
``commit_step`` run on the boot the owner starts with no flag, and
``mob_ai_control``/``mob_loot`` fold into the same dispatch after this
module's commit succeeds (CORE-REQUEST-007, PR #71/#73).  The one sentence
above that is still true today is the last one: the inbound half (a real
EA7D produced by a real attack input) has still never been observed by
anyone, so whether a real click on a real monster reaches this driver at all
remains PROPOSED, not MEASURED - see GT-084, queued and not yet run.

NOTHING IS INSTALLED.  No socket, no clock, no randomness, no database, no
global state, no import-time side effect.  Every function is a pure function of
its arguments; every state object is a frozen dataclass; the ledger is carried
as a tuple sorted by identity so its representation is unique.  Contract
breaches raise :class:`MobCombatContractError` with a NAMED reason from
:data:`MOB_COMBAT_REFUSAL_REASONS`, never a bare ValueError and never a silent
coercion.

[UPDATE, round B_20260827_1734 (ebbhzt), 2026-08-27]: Panya's attended-session
reference letter (pf_bridge/notes_to_chief/20260827_1635_PANYA-REFERENCE-
original-server-combat-loop-colors-death-loot-vs-ours.md, section "command 3a")
named a real gap directly: nothing before this round limited how OFTEN the
SAME performer's attacks land, so a player who clicks faster than the
original server's own auto-attack cadence (which the letter's clip shows as a
real, timed loop the client drives) extracts more damage per second than the
formula above was ever meant to allow.  :func:`check_attack_cadence` closes
that hole, in front of :func:`strike` rather than inside it, so this module's
"pure function of its arguments, no clock" promise above stays true: the
function takes a caller-supplied millisecond timestamp, it does not read a
clock itself.  :data:`ATTACK_CADENCE_MS_PROVISIONAL` IS A GUESS, LABELLED AS
ONE: nobody has RE'd the original server's real auto-attack period, RE-110
(pf_bridge, opened 2026-08-27) is the open ticket for that number, and this
round does not stop to wait for the answer - it ships a conservative round
number so the exploit closes today, and the docstring says so at the one
place a later round has to look to swap it for a measured value.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from . import field_mobs
from .field_mobs import FieldMob
from .population import (
    FULL_MOVEMENT_MASK,
    MOVEMENT_ATTR_ID,
    NPC_ATTR_ID,
    NPC_STYLE_ACTOR_TYPE,
)


# Convention markers only; nothing in this tree branches on them.
production_allowed = True
test_only = False

MOB_COMBAT_MILESTONE = "MOB-COMBAT-001"
MOB_COMBAT_BUILD_ORDER = "M4 first half, joined to the second"
MOB_COMBAT_LANE = "B_COMBAT"

# The one line this lane owes the chief, written where a reader of the module
# finds it rather than only in a PR body.
MOB_COMBAT_WIRING = (
    "runtime.py: on an EA7D ActionVital whose target is a field-mob identity, "
    "call mob_combat.attack_from_observed_action(legacy, None, ledger, None, "
    "fields, performer, attacker); commit the returned step with "
    "mob_combat.commit_step(ledger_now, step) and send step.frames in order "
    "(announce first, bar second) only if the commit is accepted; on "
    "REFUSE_LEDGER_STALE re-read the ledger and re-run the call; when "
    "step.death_due is True - the CombatStep property, NOT "
    "step.outcome.death_due, which is also True for a hit on something "
    "already dead - the step carries the announce frame ONLY and the kill is "
    "finished by mob_death.kill (see mob_death.MOB_DEATH_WIRING); a hit on "
    "something already dead carries NO frames at all and owes nothing."
)
# Written out because a reader of the line above should not have to guess: the
# second argument is the THREAT handle and passing None is the supported
# production wiring for v4.  It STAYS None, and that is not an oversight: the
# COO ruled on 2026-08-26 that threat must not arrive through an argument at
# all.  The v5 fold is a SEPARATE call after the combat commit -
# mob_ai_control.damage_step - so the edge is an import a scan can see rather
# than a handle it cannot.  See mob_ai_control.MOB_AI_CONTROL_WIRING.
MOB_COMBAT_THREAT_HANDLE_IS_OPTIONAL = True
MOB_COMBAT_THREAT_FOLD_OWNER = "mob_ai_control.damage_step"

# [UPDATE, round B_20260827_1734 (ebbhzt), 2026-08-27] appended to
# MOB_COMBAT_WIRING above, not edited into it: BEFORE the call the paragraph
# above describes, call mob_combat.check_attack_cadence(cadence, performer,
# at_ms), where ``cadence`` is a per-session mob_combat.AttackCadenceLedger
# the caller opens ONCE with mob_combat.open_cadence_ledger() - alongside the
# existing per-session mob_combat_ledger, see runtime.py's
# ``self.mob_combat_ledger = mob_combat.open_ledger()`` - and ``at_ms`` is a
# wall-clock integer millisecond reading the CALLER takes itself (this module
# owns no clock; see NOTHING IS INSTALLED and the round's own update, above).
# If check.accepted is False: print mob_combat.describe_cadence_rejection
# (check), send NOTHING, and do not call attack_from_observed_action at all
# this dispatch - no damage, no ledger commit, no threat fold.  If True:
# store check.cadence back onto the session (cadence = check.cadence) and run
# the rest of this wiring exactly as already written.  CORE-REQUEST to chief:
# wire this into runtime.py's _dispatch_mob_combat, immediately before its
# existing `for _attempt in range(MOB_COMBAT_STALE_RETRY_LIMIT):` /
# `mob_combat.attack_from_observed_action(...)` call.
MOB_COMBAT_CADENCE_WIRING = (
    "runtime.py, in _dispatch_mob_combat, before attack_from_observed_action: "
    "check = mob_combat.check_attack_cadence(self.mob_combat_cadence, "
    "performer, at_ms_wallclock); if not check.accepted: print each line of "
    "mob_combat.describe_cadence_rejection(check) and return [] (no frames, "
    "no ledger touch); else: self.mob_combat_cadence = check.cadence and "
    "proceed exactly as MOB_COMBAT_WIRING already says. "
    "self.mob_combat_cadence starts life as mob_combat.open_cadence_ledger(), "
    "opened next to self.mob_combat_ledger."
)
# [STALE as of runtime.py CORE-REQUEST (LANE-B, 20260828_0337), round
# confident-ride-d9704m, 2026-08-28] [MEASURED, by call-site reading]: the
# wiring line above HAS been written and runs on the production dispatch
# path -- with one DEVIATION from the literal recipe, found by pf-adversary
# before push and applied by chief: the gate above only fires when
# ``target`` resolves to a roster member (the same membership test
# ``attack_from_observed_action`` itself runs), not on every inbound
# ActionVital. Gating unconditionally, as originally written, let an
# ActionVital at a non-monster target silently spend the performer's
# cadence window before the roster-membership check ever ran, so a
# following genuine first attack could be rejected as "too soon" though no
# damage-bearing attack had happened yet -- see
# tests/test_mob_combat_cadence_wiring.py and runtime.py's own comment at
# the call site for the reproduction. Rejections also append
# "mob_combat_cadence_rejected_no_reply" to ``self.events``, matching the
# ``..._no_reply`` convention every other silent return in
# ``_dispatch_mob_combat`` already follows -- the first draft only printed
# the console line, which pf-adversary flagged as inconsistent with that
# convention.

# ---------------------------------------------------------------------------
# [LANE-B ASSUMPTION - PROVISIONAL, awaiting RE-110] Minimum attack cadence.
# Panya's 2026-08-27 16:35 reference letter asked this lane to close the
# "spam-click = runaway damage" gap FIRST, ahead of every colour/panel/death/
# loot item the same letter raised, because it is the one gap that changes
# how much damage a player extracts per real second versus the frozen
# formula below.  The original server's own cadence comes from a real,
# timed auto-attack loop the client drives (letter section 3); nobody on
# this project has RE'd that loop's actual period.  RE-110 (pf_bridge,
# opened 2026-08-27) is the open ticket for the measured number.  The value
# below is NOT that number: it is a conservative, round, PLACEHOLDER
# millisecond figure, picked only so the exploit closes today rather than
# waiting on RE, and named so a later round has exactly one constant to
# change once RE-110 answers - no other line in this module should need to
# move.
# ---------------------------------------------------------------------------
ATTACK_CADENCE_MS_PROVISIONAL = 600

# ---------------------------------------------------------------------------
# The damage formula.  Copied value-for-value, WITH provenance, from the lanes
# that proved it, because importing a scenario-gated probe into a production
# module is how a flagless build ends up depending on a flag.  Every constant
# below is pinned against its source in tests/test_mob_combat.py.
#   attack  = ATK_BASE + K_ATK_STR * ability_str + K_ATK_LV * level
#   defence = DEF_BASE + K_DEF_CON * ability_con + K_DEF_LV * level
#   damage  = max(MIN_HIT, attack - defence)
# Source: HYP-PF-024 DAMAGE-MODEL-001 (round 83), reused unchanged by HYP-PF-029
# and by HYP-PF-038 HOSTILE-HP-LINK-001, whose ladder GT-035 watched on a
# screen.  The arithmetic is OURS: the original server is unrecoverable and no
# capture in any corpus shows a target's HP moving in either direction.
# ---------------------------------------------------------------------------
ATK_BASE = 100
K_ATK_STR = 7
K_ATK_LV = 3
DEF_BASE = 10
K_DEF_CON = 2
K_DEF_LV = 1
MIN_HIT = 1

# OURS, not a table's: no MOBS column carries a constitution.  The value is the
# one HYP-PF-038 used for this same defender, kept so that the numbers this
# production driver ships are the numbers two observers already watched fall on
# a real screen in GT-035, rather than a second set nobody has seen.
MOB_ABILITY_CON = 22

# The wire, from the same static anchors the probe lanes carry.
CHIT_RESULT_VITAL_ID = 0x16F7
CHIT_RESULT_VITAL_VERSION = 0x00
CHIT_RESULT_HEADER_WIRE_SIZE = 22       # qword performer + 4 reserved fields
HIT_COUNT_WIRE_SIZE = 3
HIT_ELEMENT_WIRE_SIZE = 37              # 9 + 5 + 15 + 5 + 3
TAG_QWORD = 0x32
TAG_U32 = 0x14
TAG_U16 = 0x12
TAG_U8 = 0x0B
HEADER_RESERVED_VALUE = 0
YAW_PINNED = 0.0

# The damage field is READ SIGNED at entry +0x08.  Only negative values have an
# observed meaning; a positive one has never been sent and its meaning is
# unknown, so it is refused rather than guessed.
DAMAGE_WIRE_MIN = -1_000_000
DAMAGE_WIRE_MAX = 0
FLAGS_MISS = 0x0000
FLAGS_HIT = 0x0001
MOB_COMBAT_FLAGS_ALLOWLIST = (FLAGS_MISS, FLAGS_HIT)

# The seam described at the top of this file.  ~~1~~ -> 0: the death half
# landed in round 7ptoku and owns everything at the floor, so a monster now
# reaches the number the client's own gate reads.  The constant stays NAMED
# rather than being replaced by a literal zero, because every check in this
# module is written against it and a later round that has to raise it again
# raises it in one place.
HP_FLOOR = 0

# What this lane does NOT claim.  Written as data so a report cannot quote the
# module without quoting these too.
MOB_COMBAT_NONCLAIMS = (
    "a real attack input has never been observed producing the EA7D "
    "ActionVital this driver reads; the inbound half is unproven",
    "nothing dispatches this module: runtime.py belongs to the chief and the "
    "one wiring line has not been written. "
    "[STALE as of runtime.py CORE-REQUEST-005, PR #63, round mdj01v, "
    "2026-08-26] [MEASURED, by call-site reading]: the wiring line HAS been "
    "written and runs unconditionally on a flagless boot; what remains true "
    "is the nonclaim right above this one -- the inbound half that would "
    "drive it from a real attack is still unproven",
    "death is delivered by mob_death, not by this module: what this lane "
    "claims is the arithmetic that reaches zero and the announce frame that "
    "says so, and the corpse itself has never been watched land",
    "the monster's constitution is OURS - no committed table carries one",
    "name colour is not claimed by this lane; RE-067 owns it and is open. "
    "[STALE as of pf_bridge/CLIENT_RE_QUEUE.md chief R165, 2026-08-25, "
    "round dvxb6f] [MEASURED]: RE-067 is CLOSED (PASS/MIXED, actor half "
    "BOUNDED NEGATIVE) - name colour is still not claimed by this lane, "
    "but the question is not open pending more static work, it is a "
    "measured ceiling; the client-observable answer waits on GT-084/"
    "RIDER-084-A instead",
    "the client's draw distance is still unmeasured, so a monster hit from "
    "far away may move a bar nobody can see",
    "named AND hostile in one body has never been sent and never been "
    "observed: field_mobs' nonclaim, inherited here, because the bar frame "
    "this driver refreshes IS that body (mask 0x070D, not GT-035's 0x030D)",
    "a monster this lane took to zero is finished by mob_death and by nothing "
    "else: until that call is made it lies at zero HP with no timer field, "
    "which is a state no client has been shown",
    "the announce frame carries the monster's own world position; for the "
    "sparse bg0001 rows that can be ~12,000 units from a spawning player, and "
    "a neighbouring lane measured no model drawn at that distance",
    "threat is only recorded while the mob's aggro phase is idle or aggro: "
    "mob_aggro absorbs damage silently in its return and dead phases, by that "
    "module's declared design, and this driver does not override it",
)

# Struck, not deleted.  Both of these were true of this module while the death
# half did not exist, and a report that quoted them is not wrong about the
# round it quoted - it is out of date, and the reason is written here rather
# than lost with the line.
MOB_COMBAT_RETIRED_NONCLAIMS = (
    ("death is not delivered: the floor is 1 and RE-071's gate needs the "
     "timer field this lane does not send",
     "retired in round 7ptoku: mob_death sends that timer field and the "
     "floor is 0"),
    ("until the death half lands, every monster a player fights converges to "
     "1 HP and stays there: it absorbs nothing further and the server answers "
     "further hits with silence",
     "retired in round 7ptoku: a monster now reaches 0 and mob_death turns it "
     "into a corpse; the silence that remains is the silence owed to a hit on "
     "something already dead"),
)

REFUSE_VALUE_NOT_INT = "value_not_int"
REFUSE_VALUE_OUT_OF_RANGE = "value_out_of_range"
REFUSE_POSITION_NOT_FINITE = "position_not_finite"
REFUSE_TYPE_NOT_TYPED_RECORD = "type_not_typed_record"
REFUSE_IDENTITY_NOT_POSITIVE = "identity_not_positive"
REFUSE_PERFORMER_IS_THE_TARGET = "performer_is_the_target"
REFUSE_TARGET_NOT_IN_LEDGER = "target_not_in_ledger"
REFUSE_DUPLICATE_LEDGER_IDENTITY = "duplicate_ledger_identity"
REFUSE_BALANCE_ABOVE_MAX = "balance_above_max"
# ~~REFUSE_BALANCE_BELOW_FLOOR~~ retired in round 7ptoku.  With the floor at 0
# it sat behind a range check that already refuses everything below zero, and
# this module's own rule is that a named refusal which cannot occur is a lie
# told to whoever counts them.  The check it guarded is now the u32 range check
# in MobBalance, by name REFUSE_VALUE_OUT_OF_RANGE.
REFUSE_BAR_FRAME_FOR_A_DEAD_BODY = "bar_frame_for_a_dead_body"
REFUSE_DAMAGE_WIRE_POSITIVE = "damage_wire_positive"
REFUSE_LEDGER_NOT_SORTED = "ledger_not_sorted"
REFUSE_LEDGER_SCENE_EMPTY = "ledger_scene_empty"
REFUSE_LEDGER_SCENE_DISAGREES_WITH_ROSTER = (
    "ledger_scene_disagrees_with_roster")
REFUSE_LEDGER_STALE = "ledger_stale"
REFUSE_LEDGER_ROW_DISAGREES_WITH_ROSTER = "ledger_row_disagrees_with_roster"
REFUSE_OUTCOME_SELF_CONTRADICTORY = "outcome_self_contradictory"
REFUSE_DAMAGE_WIRE_OUT_OF_RANGE = "damage_wire_out_of_range"
REFUSE_FLAGS_NOT_ALLOWLISTED = "flags_not_allowlisted"
REFUSE_FLAGS_DISAGREE_WITH_DAMAGE = "flags_disagree_with_damage"
REFUSE_AGGRO_HANDLE_INCOMPLETE = "aggro_handle_incomplete"
REFUSE_ACTION_FIELDS_MALFORMED = "action_fields_malformed"
REFUSE_COMPOSED_BYTES_OFF_PIN = "composed_bytes_off_pin"
# [UPDATE, round B_20260827_1734 (ebbhzt), 2026-08-27] attack-cadence reasons.
REFUSE_DUPLICATE_CADENCE_IDENTITY = "duplicate_cadence_identity"
REFUSE_CADENCE_NOT_SORTED = "cadence_not_sorted"
REFUSE_CADENCE_OUTCOME_SELF_CONTRADICTORY = "cadence_outcome_self_contradictory"
MOB_COMBAT_REFUSAL_REASONS = (
    REFUSE_VALUE_NOT_INT,
    REFUSE_VALUE_OUT_OF_RANGE,
    REFUSE_POSITION_NOT_FINITE,
    REFUSE_TYPE_NOT_TYPED_RECORD,
    REFUSE_IDENTITY_NOT_POSITIVE,
    REFUSE_PERFORMER_IS_THE_TARGET,
    REFUSE_TARGET_NOT_IN_LEDGER,
    REFUSE_DUPLICATE_LEDGER_IDENTITY,
    REFUSE_BALANCE_ABOVE_MAX,
    REFUSE_BAR_FRAME_FOR_A_DEAD_BODY,
    REFUSE_DAMAGE_WIRE_POSITIVE,
    REFUSE_LEDGER_NOT_SORTED,
    REFUSE_LEDGER_SCENE_EMPTY,
    REFUSE_LEDGER_SCENE_DISAGREES_WITH_ROSTER,
    REFUSE_LEDGER_STALE,
    REFUSE_LEDGER_ROW_DISAGREES_WITH_ROSTER,
    REFUSE_OUTCOME_SELF_CONTRADICTORY,
    REFUSE_DAMAGE_WIRE_OUT_OF_RANGE,
    REFUSE_FLAGS_NOT_ALLOWLISTED,
    REFUSE_FLAGS_DISAGREE_WITH_DAMAGE,
    REFUSE_AGGRO_HANDLE_INCOMPLETE,
    REFUSE_ACTION_FIELDS_MALFORMED,
    REFUSE_COMPOSED_BYTES_OFF_PIN,
    REFUSE_DUPLICATE_CADENCE_IDENTITY,
    REFUSE_CADENCE_NOT_SORTED,
    REFUSE_CADENCE_OUTCOME_SELF_CONTRADICTORY,
)


class MobCombatContractError(ValueError):
    """A refusal from this module, always carrying a named reason."""

    def __init__(self, reason: str, detail: str) -> None:
        if reason not in MOB_COMBAT_REFUSAL_REASONS:
            raise AssertionError("unnamed refusal reason: %s" % reason)
        super().__init__("%s: %s" % (reason, detail))
        self.reason = reason
        self.detail = detail


def _require_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or type(value) is bool:
        raise MobCombatContractError(
            REFUSE_VALUE_NOT_INT, "%s must be a plain int" % label)
    if not minimum <= value <= maximum:
        raise MobCombatContractError(
            REFUSE_VALUE_OUT_OF_RANGE,
            "%s must be within [%d, %d], got %d" % (
                label, minimum, maximum, value),
        )
    return value


def _require_identity(value: Any, label: str) -> int:
    identity = _require_int(value, label, 0, 0xFFFFFFFFFFFFFFFF)
    if identity <= 0:
        raise MobCombatContractError(
            REFUSE_IDENTITY_NOT_POSITIVE, "%s must be positive" % label)
    return identity


def _require_position(value: Any) -> tuple[float, float, float]:
    if type(value) is not tuple or len(value) != 3:
        raise MobCombatContractError(
            REFUSE_POSITION_NOT_FINITE, "position must be a 3-tuple")
    out = []
    for component in value:
        if type(component) not in (int, float) or type(component) is bool:
            raise MobCombatContractError(
                REFUSE_POSITION_NOT_FINITE, "position component is not a number")
        as_float = float(component)
        if not math.isfinite(as_float):
            raise MobCombatContractError(
                REFUSE_POSITION_NOT_FINITE, "position component is not finite")
        out.append(as_float)
    return (out[0], out[1], out[2])


@dataclass(frozen=True)
class Combatant:
    """The two ability numbers the formula reads, and the level.

    One record for both sides: the attacker half reads ``level`` and
    ``ability_str``, the defender half reads ``level`` and ``ability_con``.
    Nothing here is invented by this module - the caller supplies the character
    row for the player and the monster row for the mob.
    """

    level: int
    ability_str: int
    ability_con: int

    def __post_init__(self) -> None:
        _require_int(self.level, "level", 1, 1000)
        _require_int(self.ability_str, "ability_str", 0, 100000)
        _require_int(self.ability_con, "ability_con", 0, 100000)

    @property
    def attack(self) -> int:
        return ATK_BASE + K_ATK_STR * self.ability_str + K_ATK_LV * self.level

    @property
    def defence(self) -> int:
        return DEF_BASE + K_DEF_CON * self.ability_con + K_DEF_LV * self.level


@dataclass(frozen=True)
class MobBalance:
    """One monster's live balance: who it is, its ceiling, where it stands."""

    actor_identity: int
    max_hp: int
    current_hp: int

    def __post_init__(self) -> None:
        _require_identity(self.actor_identity, "actor identity")
        _require_int(self.max_hp, "max hp", 1, 0xFFFFFFFF)
        _require_int(self.current_hp, "current hp", 0, 0xFFFFFFFF)
        if self.current_hp > self.max_hp:
            raise MobCombatContractError(
                REFUSE_BALANCE_ABOVE_MAX,
                "current hp %d is above max %d" % (self.current_hp, self.max_hp),
            )
        # ~~a named below-the-floor refusal~~ - see the comment on
        # REFUSE_BAR_FRAME_FOR_A_DEAD_BODY.  With HP_FLOOR at 0 the u32 range
        # check above IS the floor check, and a second name for it could never
        # be raised.

    @property
    def at_floor(self) -> bool:
        """True when this monster is at the floor, which is now zero: dead."""
        return self.current_hp == HP_FLOOR

    @property
    def fraction(self) -> float:
        return self.current_hp / self.max_hp


@dataclass(frozen=True)
class CombatLedger:
    """Every monster's balance, as a tuple sorted by identity.

    Sorted-tuple rather than a dict so two ledgers built from the same hits
    compare equal and hash the same in any process, and so no caller can mutate
    a balance behind the driver's back.  [AMENDED, ROUND jop8ph-2,
    pf-adversary D9: "the same hits" now includes the same ``scene`` tag.
    ``open_ledger(roster) != CombatLedger(open_ledger(roster).balances)``,
    because the first is tagged and the second is not -- an inequality this
    lane's own tests rely on.  No caller in this tree compares two ledgers,
    which is why nothing broke; the sentence was still wrong as it stood.]

    ``scene`` IS THE FIELD ROUND jop8ph ADDED, AND IT EXISTS FOR A CALLER THAT
    MUST NOT BE ALLOWED TO ASK ITS QUESTION THE OTHER WAY.  A census composer
    holding a ledger needs to know "is this one mine?"  Before this field the
    only way to find out was to USE it: ``mob_death._balance_in`` raises
    ``ledger_disagrees_with_register ... target_not_in_ledger`` on the first
    identity a foreign ledger cannot answer for, at a call site inside
    ``runtime.py``'s census dispatch where that refusal unwinds the listener
    thread.  MEASURED, round z096sw: a scene-2 roster against a bg0001 ledger
    refuses at ``0x2033``; a scene-1 roster against a Bg0002 ledger refuses at
    ``0x2068``.  So the Bg0002 census branch passes NO ledger today, and every
    wounded monster in that scene is re-sent at its ceiling by any recompose --
    which is BUILD-005's promise, taken back one frame later.

    The field is OPTIONAL and defaults to ``None``, which is a real state with
    a name ("this ledger does not say which scene it is for"), not a silent
    stand-in for any particular scene.  :func:`open_ledger` fills it in from
    the roster it was handed when every row agrees, so the ledger
    ``runtime.py`` opens at session start is scene-tagged with no call-site
    change at all.  Nothing here refuses a ledger for being unscoped -- that
    decision belongs to :mod:`mob_ledger_admission`, which treats the scene
    label as a declaration and roster containment as the ground truth.

    A ledger's scene never changes once opened: :meth:`with_balance` carries it
    forward, and a ledger for a scene the player has left is stale in exactly
    the way it was before this field existed.  This field makes that
    detectable; it does not make it not happen.
    """

    balances: tuple[MobBalance, ...]
    generation: int = 0
    scene: str | None = None

    def __post_init__(self) -> None:
        if type(self.balances) is not tuple:
            raise MobCombatContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD, "balances must be a tuple")
        if self.scene is not None:
            if type(self.scene) is not str:
                raise MobCombatContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "scene must be a scene folder name or None")
            if not self.scene:
                # The empty string is the shape that would read as "unscoped"
                # at every ``if ledger.scene:`` and as "a scene named ''" at
                # every ``ledger.scene is None``.  One of those readers is
                # always wrong, so neither gets written.
                raise MobCombatContractError(
                    REFUSE_LEDGER_SCENE_EMPTY,
                    "an empty scene name is not 'no scene': pass None")
        seen = set()
        for balance in self.balances:
            if type(balance) is not MobBalance:
                raise MobCombatContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "every ledger row must be a typed MobBalance")
            if balance.actor_identity in seen:
                raise MobCombatContractError(
                    REFUSE_DUPLICATE_LEDGER_IDENTITY,
                    "identity 0x%X appears twice" % balance.actor_identity)
            seen.add(balance.actor_identity)
        ordered = tuple(sorted(
            self.balances, key=lambda row: row.actor_identity))
        if ordered != self.balances:
            # REFUSED rather than silently re-sorted, which is what the first
            # draft did: this module promises no silent coercion, and the
            # sibling mob_aggro.MobAiState refuses this exact shape by name.
            raise MobCombatContractError(
                REFUSE_LEDGER_NOT_SORTED,
                "ledger rows must be given in ascending identity order")
        _require_int(self.generation, "generation", 0, 2 ** 62)

    def identities(self) -> tuple[int, ...]:
        return tuple(row.actor_identity for row in self.balances)

    def balance_of(self, actor_identity: int) -> MobBalance:
        wanted = _require_identity(actor_identity, "actor identity")
        for row in self.balances:
            if row.actor_identity == wanted:
                return row
        raise MobCombatContractError(
            REFUSE_TARGET_NOT_IN_LEDGER,
            "identity 0x%X is not a monster this ledger opened" % wanted,
        )

    def with_balance(self, balance: MobBalance) -> "CombatLedger":
        if type(balance) is not MobBalance:
            raise MobCombatContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD, "replacement must be a MobBalance")
        self.balance_of(balance.actor_identity)
        return CombatLedger(
            tuple(
                balance if row.actor_identity == balance.actor_identity else row
                for row in self.balances
            ),
            self.generation + 1,
            # Carried, not re-derived.  A ledger that forgot its scene on the
            # first hit would be scene-tagged exactly until a player used it,
            # which is the one moment the tag has to still be there.
            self.scene,
        )


@dataclass(frozen=True)
class HitOutcome:
    """What one hit did, in numbers a report can print without re-deriving.

    VALIDATED ON CONSTRUCTION, and that is not decoration.  ``apply_hit`` is not
    the only thing that will ever build one of these: the chief's wiring and the
    death lane that attaches at ``death_due`` both will.  Until an adversarial
    review pointed it out, this was the one record in the module with no
    ``__post_init__``, so a hand-built outcome could announce -1 on the wire
    while subtracting 964 from the balance, and every downstream function -
    ``announce_frames``, ``apply_threat``, ``describe_step`` - would have taken
    it.  The invariant the module is proudest of lives HERE now, not in the one
    function that happens to get it right.
    """

    attacker_identity: int
    target_identity: int
    damage: int
    damage_wire: int
    flags: int
    hp_before: int
    hp_after: int
    max_hp: int
    clamped_by: int
    at_floor: bool
    death_due: bool
    no_room: bool = False

    def __post_init__(self) -> None:
        _require_identity(self.attacker_identity, "attacker identity")
        _require_identity(self.target_identity, "target identity")
        if self.attacker_identity == self.target_identity:
            raise MobCombatContractError(
                REFUSE_PERFORMER_IS_THE_TARGET,
                "the performer and the target must differ")
        _require_int(self.max_hp, "max hp", 1, 0xFFFFFFFF)
        _require_int(self.damage, "damage", 0, -DAMAGE_WIRE_MIN)
        _require_int(self.clamped_by, "clamped by", 0, 2 * -DAMAGE_WIRE_MIN)
        for label, value in (("hp before", self.hp_before),
                             ("hp after", self.hp_after)):
            _require_int(value, label, HP_FLOOR, self.max_hp)
        for label, value in (("at floor", self.at_floor),
                             ("death due", self.death_due),
                             ("no room", self.no_room)):
            if type(value) is not bool:
                raise MobCombatContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD, "%s must be a bool" % label)
        require_damage_and_flags_agree(self.damage_wire, self.flags)
        checks = (
            (self.damage_wire == -self.damage,
             "the announced number %d is not the subtracted number %d" % (
                 self.damage_wire, self.damage)),
            (self.hp_before - self.hp_after == self.damage,
             "the balance moved %d while the hit says %d" % (
                 self.hp_before - self.hp_after, self.damage)),
            (self.at_floor == (self.hp_after == HP_FLOOR),
             "at_floor disagrees with hp_after %d" % self.hp_after),
            (self.death_due == self.at_floor,
             "death_due and at_floor must agree: with the floor at zero they "
             "are the same statement, and mob_death.kill reads death_due"),
            (not self.no_room or (self.damage == 0 and self.clamped_by > 0),
             "no_room means a real hit landed on a monster with nothing left "
             "to lose"),
            (self.no_room or self.damage > 0 or self.clamped_by == 0,
             "a hit that moved nothing must say why"),
        )
        for holds, detail in checks:
            if not holds:
                raise MobCombatContractError(
                    REFUSE_OUTCOME_SELF_CONTRADICTORY, detail)

    @property
    def applied(self) -> int:
        return self.hp_before - self.hp_after


def mob_defender(mob: FieldMob) -> Combatant:
    """The defender record for a roster monster.

    ``level`` comes from the mined MOBS row.  ``ability_con`` does not come
    from a table at all: no committed table gives a MOBS row a constitution -
    the mined columns are level, rank, the two AI ids, walk speed and the drop
    ids (see ``field_mob_tables``).  :data:`MOB_ABILITY_CON` is therefore OURS,
    and it is not a fresh invention: it is the same 22 the HYP-PF-038 ladder
    used for this exact defender, which is why this production driver
    reproduces the two damage numbers GT-035 watched on a screen
    (``test_the_driver_reproduces_the_ladder_gt035_watched``) instead of
    quietly shipping different ones.  A later round that mines a real defence
    column replaces this function and nothing else.
    """
    if type(mob) is not FieldMob:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "mob must be the typed FieldMob record")
    return Combatant(
        level=mob.level, ability_str=0, ability_con=MOB_ABILITY_CON)


def resolve_damage(attacker: Combatant, defender: Combatant) -> int:
    """The frozen formula, floored at :data:`MIN_HIT`.  Positive, always."""
    for who, record in (("attacker", attacker), ("defender", defender)):
        if type(record) is not Combatant:
            raise MobCombatContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "%s must be the typed Combatant record" % who)
    return max(MIN_HIT, attacker.attack - defender.defence)


def damage_to_wire(damage: int) -> int:
    """The signed i32 the client prints: negative, and never zero for a hit."""
    value = _require_int(damage, "damage", 1, -DAMAGE_WIRE_MIN)
    return -value


def require_damage_wire(value: Any) -> int:
    # The lower bound is checked FIRST and by name.  With _require_int first,
    # a value below the window reported a plain range error and
    # REFUSE_DAMAGE_WIRE_OUT_OF_RANGE became unreachable - a named refusal that
    # cannot occur is a lie told to whoever counts them.
    if type(value) is int and type(value) is not bool and value < DAMAGE_WIRE_MIN:
        raise MobCombatContractError(
            REFUSE_DAMAGE_WIRE_OUT_OF_RANGE,
            "damage wire %d is outside the proven window" % value)
    wire = _require_int(value, "damage wire", DAMAGE_WIRE_MIN, 0x7FFFFFFF)
    if wire > DAMAGE_WIRE_MAX:
        raise MobCombatContractError(
            REFUSE_DAMAGE_WIRE_POSITIVE,
            "a positive damage number has never been sent and its meaning is "
            "unknown; got %d" % wire,
        )
    return wire


def require_flags(value: Any) -> int:
    flags = _require_int(value, "flags", 0, 0xFFFF)
    if flags not in MOB_COMBAT_FLAGS_ALLOWLIST:
        raise MobCombatContractError(
            REFUSE_FLAGS_NOT_ALLOWLISTED,
            "flags 0x%04X is outside the two values a hit lane has ever sent"
            % flags,
        )
    return flags


def require_damage_and_flags_agree(damage_wire: int, flags: int) -> None:
    """A miss moves nothing and a hit moves something.  No third case."""
    wire = require_damage_wire(damage_wire)
    value = require_flags(flags)
    if (wire == 0) != (value == FLAGS_MISS):
        raise MobCombatContractError(
            REFUSE_FLAGS_DISAGREE_WITH_DAMAGE,
            "damage %d and flags 0x%04X tell two different stories" % (
                wire, value),
        )


def open_ledger(
    roster: tuple[FieldMob, ...] | None = None,
    *,
    scene: str | None = None,
) -> CombatLedger:
    """Every monster in the roster, standing at its own ceiling.

    THE SCENE COMES OFF THE ROSTER, ROUND jop8ph.  Every ``FieldMob`` already
    carries the scene folder it was mined from -- ``mob_death`` reads
    ``mob.scene`` on the register path -- so the ledger can be tagged with no
    change at any call site, INCLUDING the no-argument one in
    ``runtime.py``'s ``PersistentGameSessionState.__init__``, which is the
    ledger a live boot actually holds.  That mattered more than the explicit
    argument: had the tag only arrived through a new keyword, the one ledger
    in production would have stayed unscoped and
    :mod:`mob_ledger_admission` would have had nothing to read on the only
    boot that counts.

    ``scene=`` overrides the derivation and is checked against it, because a
    caller who names a scene and hands rows from another one has two answers
    and this function will not silently keep the wrong one.  [ROUND jop8ph-2,
    pf-adversary M4/M5: no caller in src or tests passes a ``scene=`` that
    DISAGREES with the derivation, so both the override branch and the
    disagreement refusal were unexercised -- ignoring the argument entirely,
    and dropping the ``derived is not None`` guard, both survived the whole
    suite.  Driven now, in both directions, by
    ``test_naming_one_scene_while_handing_over_another_is_refused`` and
    ``test_naming_the_scene_of_an_empty_roster_is_accepted_not_refused``.]

    A ROSTER WHOSE ROWS DISAGREE STAYS UNSCOPED, and is not refused.  Nothing
    in this tree builds a mixed-scene roster today, but the diagnostic
    widening path (``diag_multi_object_wiring``) grows a ledger past its
    roster on purpose, and an admission decision that falls back to
    membership is strictly safer there than a raise on a path that is inside
    a listener thread's ``try``.  Unscoped is a state with a name, and
    :func:`mob_ledger_admission.admit_ledger` reads it as "prove it by
    containment", never as "trust me".
    """
    mobs = field_mobs.load_roster() if roster is None else roster
    if type(mobs) is not tuple:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "roster must be a tuple of FieldMob")
    rows = []
    scenes = set()
    for mob in mobs:
        if type(mob) is not FieldMob:
            raise MobCombatContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "roster must be a tuple of FieldMob")
        rows.append(MobBalance(mob.actor_identity, mob.max_hp, mob.max_hp))
        scenes.add(mob.scene)
    derived = min(scenes) if scenes else None
    if scene is not None and derived is not None and scene != derived:
        raise MobCombatContractError(
            REFUSE_LEDGER_SCENE_DISAGREES_WITH_ROSTER,
            "caller named scene %r and handed rows from scene %r" % (
                scene, derived),
        )
    return CombatLedger(tuple(rows), 0, scene if scene is not None else derived)


def open_ledger_for_scene_id(scene_id: int) -> CombatLedger:
    """The ledger for the monsters that actually stand in ``scene_id``.

    ROUND k3qe9q.  ``runtime.py`` holds a scene id, not a scene name, and
    today opens the ledger with :func:`open_ledger` and no argument -- which
    means bg0001's four identities, in every scene, forever.  A player
    standing in Bg0002 is refused with ``target_not_in_ledger`` on 95 of the
    97 bodies their client was sent, and lands a hit on a PORT ROYAL monster
    on the other two (identities ``0x2068``/``0x206a`` belong to both
    scenes; see :func:`field_mobs.scene_for_scene_id`).

    This is the shape a call site composes the right ledger with.  It is a
    thin join of two things that already existed -- ``open_ledger(roster=...)``,
    which has taken a roster since it was written, and
    ``field_mobs.roster_for_scene_id``, added this round -- and it holds no
    scene knowledge of its own, so a third scene going live needs nothing
    here.

    WHAT IT IS NOT.  It is not a lifetime.  ``runtime.py`` builds its ledger
    ONCE, in ``PersistentGameSessionState.__init__``, where the session has
    no scene yet (``foundation.selected`` is still ``None``) -- so this
    cannot simply replace that call, and a ledger composed for the scene a
    player logged in from is stale the moment they cross a travel gate.
    Nothing in this module rebuilds it, and ``runtime.py`` has no rebuild
    path today.  pf-adversary defects 2, 3 and 4 are all that same gap, and
    the letter to chief this round asks for a rebuild point rather than a
    one-line swap.  Read this function as "compose the ledger for a scene",
    never as "keep the ledger correct as the scene changes".

    A SCENE WITH NO MONSTERS OPENS AN EMPTY LEDGER, NOT THE DEFAULT ONE.
    ``field_mobs.roster_for_scene_id`` answers ``()`` for every scene this
    project ships no roster for, and ``()`` is not ``None``, so it reaches
    :func:`open_ledger` as a real empty roster rather than as "use the
    default".  An empty ledger refuses every strike by name.  That is the
    intended behaviour and the intended DIFFERENCE from today: a town is a
    place where there is nothing to hit, not a place where bg0001's
    monsters can be hit through the floor.

    ~~ROUND jop8ph: the scene name is passed EXPLICITLY here rather than left
    to :func:`open_ledger`'s derivation ... Named here, it is a ledger that
    says which town it belongs to and refuses the next one by name.~~

    [WITHDRAWN AS WRITTEN, ROUND jop8ph-2, pf-adversary D1 on the jop8ph
    diff, MEASURED.]  The keyword below is a PROVABLE NO-OP in this tree, and
    the paragraph above described an effect it cannot have.
    :func:`field_mobs.scene_for_scene_id` returns ``None`` for exactly the
    scenes :func:`field_mobs.roster_for_scene_id` returns ``()`` for -- both
    go through the same ``_SCENE_TABLE_MODULES`` membership test -- so the
    argument is ``None`` precisely in the empty-roster case it was added for.
    Measured over every addressed scene id: ``open_ledger_for_scene_id(sid)``
    equals ``open_ledger(roster_for_scene_id(sid))`` for all of them, and
    deleting the keyword survives the whole suite.

    It is KEPT rather than deleted, and that is a decision with a reason: the
    two functions are separate today only by coincidence of implementation,
    and the day a scene is addressed with a folder but no mined table this
    call is already correct.  What is NOT kept is the claim that it does
    something today.  ``test_the_explicit_scene_here_is_measured_equivalent_
    today`` pins the equivalence, so the day it stops holding is a noticed
    day rather than a silent one.
    """
    return open_ledger(
        field_mobs.roster_for_scene_id(scene_id),
        scene=field_mobs.scene_for_scene_id(scene_id),
    )


def apply_hit(
    ledger: CombatLedger,
    attacker_identity: int,
    target_identity: int,
    damage: int,
) -> tuple[CombatLedger, HitOutcome]:
    """Subtract a hit from one monster's balance and say exactly what happened.

    The number announced on the wire is the number subtracted here, including
    when the subtraction is clamped at :data:`HP_FLOOR`: the client prints what
    the server sends and the bar shows what the server sets, so the two halves
    are computed once, together, and never separately.
    """
    if type(ledger) is not CombatLedger:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "ledger must be a typed CombatLedger")
    attacker = _require_identity(attacker_identity, "attacker identity")
    target = _require_identity(target_identity, "target identity")
    if attacker == target:
        raise MobCombatContractError(
            REFUSE_PERFORMER_IS_THE_TARGET,
            "the performer and the target must differ: the client's own "
            "visibility filter at 0x43FEF0 draws nothing otherwise",
        )
    requested = _require_int(damage, "damage", 1, -DAMAGE_WIRE_MIN)
    balance = ledger.balance_of(target)
    room = balance.current_hp - HP_FLOOR
    applied = requested if requested <= room else room
    clamped_by = requested - applied
    if applied == 0:
        # The target is already at the floor, which now means DEAD.  The
        # outcome records a real hit that landed on a corpse, and NOTHING is
        # composed for it: an earlier draft answered this case with a MISS
        # frame, which told the client the player had missed when the formula
        # said 964.  The honest wire answer to a hit on something already dead
        # is silence - mob_death already sent that monster's last two frames.
        outcome = HitOutcome(
            attacker, target, 0, 0, FLAGS_MISS, balance.current_hp,
            balance.current_hp, balance.max_hp, clamped_by, True, True, True,
        )
        return ledger, outcome
    moved = MobBalance(
        balance.actor_identity, balance.max_hp, balance.current_hp - applied)
    outcome = HitOutcome(
        attacker, target, applied, damage_to_wire(applied), FLAGS_HIT,
        balance.current_hp, moved.current_hp, moved.max_hp,
        clamped_by, moved.at_floor, moved.at_floor, False,
    )
    return ledger.with_balance(moved), outcome


def apply_threat(aggro: Any, aggro_state: Any, outcome: HitOutcome) -> Any:
    """Hand the damage to ``mob_aggro.apply_damage_threat``, unchanged.

    ``aggro`` is the module handle, passed in rather than imported.  THE REASON
    THIS FUNCTION GAVE FOR THAT IS GONE as of 2026-08-26: it used to say the
    handle kept ``mob_aggro``'s "nothing in src/ imports it" claim true, and
    the COO ruled that arrangement the hole rather than the safeguard
    (COO-DECISION 2026-08-26T04:02+07:00, section 2).  ``mob_aggro`` is
    ``production_allowed = True`` now and ``mob_ai_control`` imports it by
    name.  This function stays, unchanged in behaviour, for the two callers it
    already has - ``strike`` and its tests - and the production wiring folds
    threat through ``mob_ai_control.damage_step`` instead, where a scan can see
    the edge.

    The number handed over is the WIRE number, which is NEGATIVE.  That is not
    a detail: ``apply_damage_threat`` adds threat only for a negative value,
    because only "took damage" has a recorded meaning, and it returns the state
    UNCHANGED and without complaint for a positive one.  Handing it the
    positive arithmetic value would therefore build a monster that is hit,
    loses HP, repaints its bar and never once decides it has an enemy - a bug
    that no exception would ever announce.  ``test_threat_rises_by_the_damage``
    is the guard on this line.
    """
    if type(outcome) is not HitOutcome:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "outcome must be a typed HitOutcome")
    apply_damage_threat = getattr(aggro, "apply_damage_threat", None)
    if apply_damage_threat is None or not callable(apply_damage_threat):
        raise MobCombatContractError(
            REFUSE_AGGRO_HANDLE_INCOMPLETE,
            "the aggro handle must expose a callable apply_damage_threat")
    if outcome.damage == 0:
        return aggro_state
    return apply_damage_threat(
        aggro_state, outcome.attacker_identity, outcome.damage_wire)


def threat_was_recorded(before: Any, after: Any) -> bool:
    """Did the fold actually land, or did the aggro lane drop it silently?

    ``mob_aggro`` returns the state UNCHANGED, without complaint, for a mob in
    its return or dead phase.  That is its declared design, not a bug, but a
    driver that cannot tell the difference reports a monster as aggroed when it
    is not.  ``strike`` records the answer on the step so a console line or a
    report can say it out loud.
    """
    return after is not before


def encode_hit_entry(
    legacy: Any,
    target_identity: int,
    damage_wire: int,
    position: tuple[float, float, float],
    flags: int,
    *,
    yaw: float = YAW_PINNED,
) -> bytes:
    """One 37-byte hit entry in the proven emission order.

    General where the probe lane is pinned: any target identity, any finite
    position.  The widths, the tag order and the signed damage field are the
    static anchors, and the length check below is what keeps this general form
    honest against them.
    """
    target = _require_identity(target_identity, "target identity")
    wire = require_damage_wire(damage_wire)
    value = require_flags(flags)
    require_damage_and_flags_agree(wire, value)
    x, y, z = _require_position(position)
    if type(yaw) not in (int, float) or type(yaw) is bool or not math.isfinite(
            float(yaw)):
        raise MobCombatContractError(
            REFUSE_POSITION_NOT_FINITE, "yaw must be a finite float")
    out = bytearray()
    out += legacy.qwordtag(TAG_QWORD, target)
    out += legacy.u32tag(TAG_U32, wire & 0xFFFFFFFF)
    for component in (x, y, z):
        out += legacy.f32tag(component)
    out += legacy.f32tag(float(yaw))
    out += legacy.u16tag(TAG_U16, value)
    if len(out) != HIT_ELEMENT_WIRE_SIZE:
        raise MobCombatContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "hit entry is %d bytes, the anchor says %d" % (
                len(out), HIT_ELEMENT_WIRE_SIZE),
        )
    return bytes(out)


def encode_chit_result(
    legacy: Any, performer_identity: int, entries: list[bytes],
) -> bytes:
    """The CHitResult payload: the 22-byte header, then the entry array."""
    performer = _require_identity(performer_identity, "performer identity")
    if type(entries) is not list or not entries:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "entries must be a non-empty list")
    header = bytearray()
    header += legacy.qwordtag(TAG_QWORD, performer)
    header += legacy.u16tag(TAG_U16, HEADER_RESERVED_VALUE)
    header += legacy.u16tag(TAG_U16, HEADER_RESERVED_VALUE)
    header += legacy.u32tag(TAG_U32, HEADER_RESERVED_VALUE)
    header += legacy.u8tag(TAG_U8, HEADER_RESERVED_VALUE)
    if len(header) != CHIT_RESULT_HEADER_WIRE_SIZE:
        raise MobCombatContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "header is %d bytes, the anchor says %d" % (
                len(header), CHIT_RESULT_HEADER_WIRE_SIZE),
        )
    out = bytearray(header)
    out += legacy.u16tag(TAG_U16, len(entries))
    for entry in entries:
        if type(entry) is not bytes or len(entry) != HIT_ELEMENT_WIRE_SIZE:
            raise MobCombatContractError(
                REFUSE_COMPOSED_BYTES_OFF_PIN, "an entry is not 37 bytes")
        out += entry
    expected = (
        CHIT_RESULT_HEADER_WIRE_SIZE + HIT_COUNT_WIRE_SIZE
        + HIT_ELEMENT_WIRE_SIZE * len(entries)
    )
    if len(out) != expected:
        raise MobCombatContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "payload is %d bytes, the anchor says %d" % (len(out), expected),
        )
    return bytes(out)


def announce_frames(
    legacy: Any,
    performer_identity: int,
    mob: FieldMob,
    outcome: HitOutcome,
) -> tuple[bytes, bytes]:
    """The frame that floats the number over the monster."""
    if type(mob) is not FieldMob:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "mob must be the typed FieldMob record")
    if type(outcome) is not HitOutcome:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "outcome must be a typed HitOutcome")
    if mob.actor_identity != outcome.target_identity:
        raise MobCombatContractError(
            REFUSE_TARGET_NOT_IN_LEDGER,
            "the outcome names 0x%X and the mob is 0x%X" % (
                outcome.target_identity, mob.actor_identity),
        )
    entry = encode_hit_entry(
        legacy, outcome.target_identity, outcome.damage_wire,
        (mob.x, mob.y, mob.z), outcome.flags,
    )
    payload = encode_chit_result(legacy, performer_identity, [entry])
    pc, frame = legacy.make_runtime_vitals(
        [(CHIT_RESULT_VITAL_ID, CHIT_RESULT_VITAL_VERSION, payload)])
    if frame != legacy.frame_pc(pc):
        raise MobCombatContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN, "announce frame drift")
    return pc, frame


def bar_frames(
    legacy: Any,
    mob: FieldMob,
    current_hp: int,
    *,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    with_movement: bool = False,
) -> tuple[bytes, bytes]:
    """The frame that repaints the bar, built from the hostile body itself.

    ``with_movement`` defaults to False, and that default is not a preference:
    it is what GT-035 actually watched.  In the proven ladder only the
    ``TARGET_SPAWN`` step carries the movement attribute; all three
    ``TARGET_HP_AFTER_*`` frames - the ones whose bar movement two observers
    read off a screen - are composed without it.  A refresh that re-sent
    movement would also snap a monster back to its roster row on every hit.

    [OPEN RISK, NOT MEASURED - flagged, not fixed, this round (`yjty8a`)] This
    frame is a NONEMPTY ONE-ENTRY ``make_runtime_remote_actors`` generation,
    the exact shape ``pf_bridge/notes_to_chief/20260826_0910_LANE-A-CORE-REQUEST-the-
    town-must-not-follow-you-out-of-town.md`` section 4.bis warned would be
    dangerous once a lane-B module reached the unflagged path - which
    `pirate-force-server#63` did on 2026-08-26 16:49+07:00, wiring this
    function in.  ``pf_bridge/notes_to_chief/20260826_1017_RE-082-RESULT-OBJECT-REF-IS-
    ELEMENT-KEY.md`` later proved, for the sibling ``PickupTerrainThing``
    list consumer, that a NONEMPTY generation erases every tree entry the
    generation omits, and a ZERO-entry generation is a no-op.  Nobody has
    run that same static trace against THIS collection's consumer (the
    ``GSCN_RunTimeProtocolRes`` mask-``0x02`` chain at ``0x5E1C10``/
    ``0x5E01D0`` in ``make_runtime_remote_actors``'s own docstring) - RE-077's
    T5 rider closed BOUNDED NEGATIVE on a different collection (scene-switch
    cleanup) and does not answer it either.  GT-035 proves the bar this
    function refreshes reads right; it does not prove any OTHER actor in the
    scene survives the refresh, because nobody was counting them.  This lane
    does not own the fix - the consumer is client code - and does not have
    the RE tooling to trace it, so it documents the shape here and in
    ``tests/test_mob_combat.py`` instead of guessing at one.  See the round
    letter this citation ships with for the request to chief/COO.

    [UPDATE, round ``sifsfg``, 2026-08-27]: the open risk above is CONFIRMED,
    not superseded - ``RE-092`` (2026-08-26 22:23) closed the exact question
    this paragraph left open: the client's remote-actor consumer IS
    replace-by-omission.  A one-entry frame from this function reaching the
    unflagged path really does erase every other non-exempt actor.  This
    function is UNCHANGED and still callable as-is - removing it is not this
    round's call, because only ``runtime.py`` knows every call site that
    would need to move; the fix lives in
    ``mob_death.hostile_census_frames``, which composes the SAME bar entry
    this function builds into a full census instead of a one-entry
    collection.  A ``runtime.py`` caller that wants the safe wire bytes calls
    that function instead of this one - this function's own return value is
    still correct for ITS documented shape (one entry), it is the SHAPE that
    is now known-dangerous on the unflagged path, not this function's
    arithmetic or encoding.
    """
    if type(mob) is not FieldMob:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "mob must be the typed FieldMob record")
    hp = _require_int(current_hp, "current hp", HP_FLOOR, mob.max_hp)
    if hp == 0:
        # The bar of a dead monster is not a bar.  A LIVE body at zero HP
        # carries no death timer, so it satisfies neither side of the client's
        # gate (0x43BD70 and 0x43BDA0 both read +0x58 only after +0x44 == 0):
        # the monster would stand there at an empty bar forever.  The frames
        # for a monster at zero belong to mob_death, which composes the body
        # that carries both halves of the state.
        raise MobCombatContractError(
            REFUSE_BAR_FRAME_FOR_A_DEAD_BODY,
            "current hp 0 is mob_death's to compose, not this lane's: call "
            "mob_death.kill with the outcome that reached it",
        )
    if type(with_movement) is not bool:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "with_movement must be a bool")
    body = field_mobs.hostile_npc_attr(
        legacy, mob, current_hp=hp, faction=faction)
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
    entry = legacy.make_remote_actor_entry(
        NPC_STYLE_ACTOR_TYPE, mob.actor_identity, attrs)
    pc, frame = legacy.make_runtime_remote_actors([entry])
    if frame != legacy.frame_pc(pc):
        raise MobCombatContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN, "bar frame drift")
    return pc, frame


@dataclass(frozen=True)
class CombatStep:
    """One hit, end to end: the new ledger, the new threat, the two frames.

    ``base_generation`` is the generation of the ledger this step was computed
    FROM, and :func:`commit_step` is what makes it load-bearing.  A step is a
    read-modify-write of a value nobody owns; two players actioning the same
    monster in the same tick both read 3857, both compute 964, both announce
    -964, and one write is lost - 1928 announced, 964 subtracted.  The
    per-call invariant survives; the pair does not.  So the caller must commit,
    and a commit against a ledger that has moved underneath it is refused by
    name rather than silently applied.

    ``threat_recorded`` is False when the aggro lane dropped the fold (no
    handle passed, or a mob in its return/dead phase), so nothing downstream
    has to infer it from an unchanged state object.
    """

    ledger: CombatLedger
    aggro_state: Any
    outcome: HitOutcome
    announce_pc: bytes
    announce_frame: bytes
    bar_pc: bytes
    bar_frame: bytes
    base_generation: int = 0
    threat_recorded: bool = False

    @property
    def frames(self) -> tuple[bytes, ...]:
        """Announce first, bar second - the order GT-035 watched.

        EMPTY when the hit landed on a monster that is already dead: this lane
        answers that with silence rather than with a MISS it did not compute.

        ONE FRAME LONG on a killing blow.  The announce still floats the last
        number, but there is no bar to repaint: the frames that drop the body
        are ``mob_death.kill``'s, and ``outcome.death_due`` is the caller's
        signal to go and get them.
        """
        if not self.announce_frame:
            return ()
        if not self.bar_frame:
            return (self.announce_frame,)
        return (self.announce_frame, self.bar_frame)

    @property
    def death_due(self) -> bool:
        """True when the caller still owes this monster its two death frames."""
        return self.outcome.death_due and not self.outcome.no_room


def commit_step(current: CombatLedger, step: CombatStep) -> CombatLedger:
    """Compare-and-swap: accept a step only against the ledger it was read from.

    Returns the new ledger.  Refuses with :data:`REFUSE_LEDGER_STALE` when the
    stored ledger has moved since the step was computed, in which case the
    caller re-reads and re-runs - and sends nothing, because the frames of a
    refused step describe a subtraction that did not happen.
    """
    if type(current) is not CombatLedger:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "current must be a typed CombatLedger")
    if type(step) is not CombatStep:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "step must be a typed CombatStep")
    if current.generation != step.base_generation:
        raise MobCombatContractError(
            REFUSE_LEDGER_STALE,
            "this step was computed from generation %d and the ledger is at "
            "generation %d: re-read and re-run, and send nothing" % (
                step.base_generation, current.generation),
        )
    return step.ledger


# ---------------------------------------------------------------------------
# [LANE-B ASSUMPTION - PROVISIONAL, awaiting RE-110] Attack cadence: the gate
# in front of :func:`strike`, not inside it - see MOB_COMBAT_CADENCE_WIRING
# and the round update on the module docstring, above.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CadenceRecord:
    """One performer's last ACCEPTED attack, in caller-supplied wall-clock ms.

    ``last_accepted_at_ms`` is never read by a clock this module owns: the
    caller hands the timestamp in, at both write time (:func:`with_accepted`)
    and read time (:func:`check_attack_cadence`), so two calls with the same
    two integers always agree - the reason every other function in this
    module is a pure function of its arguments, unbroken here too.
    """

    performer_identity: int
    last_accepted_at_ms: int

    def __post_init__(self) -> None:
        _require_identity(self.performer_identity, "performer identity")
        _require_int(
            self.last_accepted_at_ms, "last accepted at ms", 0, 2 ** 62)


@dataclass(frozen=True)
class AttackCadenceLedger:
    """Per-performer attack-cadence state: sorted, unique, replace-not-mutate.

    Shaped the way :class:`CombatLedger` and ``mob_death.DeathRegister``
    already are - a tuple sorted by identity, so two ledgers built from the
    same accepted attacks compare equal in any process and no caller can
    mutate a row behind this lane's back.

    GROWTH, LOOKED AT AND ACCEPTED RATHER THAN GUESSED AT: unlike
    ``DeathRegister`` (whose rows are capped by the roster's own size - a
    monster dies once and stays in the register) this ledger REPLACES a
    row's timestamp on every accepted attack rather than appending a new
    one, so its size is capped by the count of DISTINCT PERFORMER IDENTITIES
    that have ever landed an accepted hit against the object holding this
    ledger - one row per attacking player, not one row per attack.  No row
    is ever deleted, matching this module's own no-shrink convention for
    ``CombatLedger`` (a monster's balance row lives for the ledger's whole
    life too).  A caller that wants this bounded to a single connection's
    lifetime, rather than a whole process's, gets that for free by storing
    it exactly where ``runtime.py`` already stores the per-session
    ``mob_combat_ledger`` this ledger is meant to sit beside - a wiring
    choice, not a change to this class.
    """

    records: tuple[CadenceRecord, ...] = ()

    def __post_init__(self) -> None:
        if type(self.records) is not tuple:
            raise MobCombatContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD, "records must be a tuple")
        seen = set()
        for record in self.records:
            if type(record) is not CadenceRecord:
                raise MobCombatContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "every cadence row must be a typed CadenceRecord")
            if record.performer_identity in seen:
                raise MobCombatContractError(
                    REFUSE_DUPLICATE_CADENCE_IDENTITY,
                    "performer identity 0x%X appears twice" % (
                        record.performer_identity),
                )
            seen.add(record.performer_identity)
        ordered = tuple(sorted(
            self.records, key=lambda row: row.performer_identity))
        if ordered != self.records:
            raise MobCombatContractError(
                REFUSE_CADENCE_NOT_SORTED,
                "cadence rows must be given in ascending identity order")

    def identities(self) -> tuple[int, ...]:
        return tuple(row.performer_identity for row in self.records)

    def last_accepted_at(self, performer_identity: int) -> int | None:
        """The last accepted timestamp for this performer, or None if new."""
        wanted = _require_identity(performer_identity, "performer identity")
        for row in self.records:
            if row.performer_identity == wanted:
                return row.last_accepted_at_ms
        return None

    def with_accepted(
        self, performer_identity: int, at_ms: int,
    ) -> "AttackCadenceLedger":
        """Replace (or add) one performer's row.  Called on ACCEPT only."""
        wanted = _require_identity(performer_identity, "performer identity")
        stamp = _require_int(at_ms, "at ms", 0, 2 ** 62)
        kept = tuple(
            row for row in self.records
            if row.performer_identity != wanted)
        return AttackCadenceLedger(tuple(sorted(
            kept + (CadenceRecord(wanted, stamp),),
            key=lambda row: row.performer_identity)))


def open_cadence_ledger() -> AttackCadenceLedger:
    """A fresh cadence ledger: nobody has landed an accepted attack yet."""
    return AttackCadenceLedger()


@dataclass(frozen=True)
class CadenceCheck:
    """The verdict on one attack attempt against the minimum cadence.

    VALIDATED ON CONSTRUCTION for the same reason :class:`HitOutcome` is: a
    hand-built check claiming ``accepted=True`` with a nonzero
    ``early_by_ms`` (or the reverse) would be taken at face value by
    :func:`describe_cadence_rejection` and by whatever wiring reads
    ``accepted`` - exactly the class of bug an adversarial review of this
    module already found once, in ``HitOutcome``, before it had this guard.
    """

    accepted: bool
    cadence: AttackCadenceLedger
    performer_identity: int
    at_ms: int
    early_by_ms: int
    cadence_ms: int

    def __post_init__(self) -> None:
        if type(self.accepted) is not bool:
            raise MobCombatContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD, "accepted must be a bool")
        if type(self.cadence) is not AttackCadenceLedger:
            raise MobCombatContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "cadence must be a typed AttackCadenceLedger")
        _require_identity(self.performer_identity, "performer identity")
        _require_int(self.at_ms, "at ms", 0, 2 ** 62)
        _require_int(self.early_by_ms, "early by ms", 0, 2 ** 62)
        _require_int(self.cadence_ms, "cadence ms", 0, 2 ** 31)
        if self.accepted != (self.early_by_ms == 0):
            raise MobCombatContractError(
                REFUSE_CADENCE_OUTCOME_SELF_CONTRADICTORY,
                "accepted %s disagrees with early_by_ms %d" % (
                    self.accepted, self.early_by_ms),
            )


def check_attack_cadence(
    cadence: AttackCadenceLedger,
    performer_identity: int,
    at_ms: int,
    *,
    cadence_ms: int = ATTACK_CADENCE_MS_PROVISIONAL,
) -> CadenceCheck:
    """Accept or reject one attack attempt by wall-clock spacing alone.

    ``at_ms`` is a CALLER-SUPPLIED integer millisecond clock reading, not a
    value this function reads itself - no ``time.time()``, no
    ``time.monotonic()``, matching NOTHING IS INSTALLED at the top of this
    module.  A test drives this with any two integers it likes and the
    result is exactly reproducible; a production caller (see
    MOB_COMBAT_CADENCE_WIRING) takes the reading itself, once, per dispatch.

    A REJECTION DOES NOT MOVE THE LEDGER: the window is measured from the
    last ACCEPTED attack only, so a burst of spam-clicks cannot slide its
    own deadline forward one reject at a time - the shortfall this function
    reports for the fifth click in a row is measured against the same
    accepted timestamp as the second.

    Clock skew (an ``at_ms`` earlier than this performer's own last accepted
    timestamp) FAILS CLOSED: it is scored as zero elapsed time, i.e. a
    maximal rejection, never as a free pass - this lane's rule elsewhere
    (missing data means a smaller world, never a fabricated one) applies to
    a suspicious clock the same way it applies to a missing table row.
    """
    if type(cadence) is not AttackCadenceLedger:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "cadence must be a typed AttackCadenceLedger")
    performer = _require_identity(performer_identity, "performer identity")
    stamp = _require_int(at_ms, "at ms", 0, 2 ** 62)
    window = _require_int(cadence_ms, "cadence ms", 0, 2 ** 31)
    last = cadence.last_accepted_at(performer)
    if last is None:
        elapsed = window
    else:
        elapsed = stamp - last
        if elapsed < 0:
            elapsed = 0
    if elapsed >= window:
        return CadenceCheck(
            True, cadence.with_accepted(performer, stamp), performer, stamp,
            0, window,
        )
    return CadenceCheck(
        False, cadence, performer, stamp, window - elapsed, window)


def describe_cadence_rejection(check: CadenceCheck) -> tuple[str, ...]:
    """The console line PANYA-REFERENCE 2026-08-27 asked for, every rejection.

    ASCII, one line, names the performer and the shortfall - printed by the
    caller, the same convention :func:`describe_step` already documents:
    this module composes the line, it does not call ``print`` itself.
    """
    if type(check) is not CadenceCheck:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "check must be a typed CadenceCheck")
    if check.accepted:
        raise MobCombatContractError(
            REFUSE_CADENCE_OUTCOME_SELF_CONTRADICTORY,
            "describe_cadence_rejection called on an accepted attempt")
    return (
        "MOB-COMBAT-001 attack cadence REJECTED: performer 0x%X, %d ms too "
        "soon (PROVISIONAL minimum %d ms, awaiting RE-110; no damage "
        "applied, no hit consumed)" % (
            check.performer_identity, check.early_by_ms, check.cadence_ms),
    )


def strike(
    legacy: Any,
    aggro: Any,
    ledger: CombatLedger,
    aggro_state: Any,
    mob: FieldMob,
    attacker_identity: int,
    attacker: Combatant,
    *,
    faction: int = field_mobs.FIELD_MOB_FACTION,
) -> CombatStep:
    """One hit on one monster: arithmetic, ledger, threat and both frames.

    This is the whole first half of M4 in one call, and it is the call the
    wiring line at :data:`MOB_COMBAT_WIRING` makes.  It sends nothing and it
    STORES nothing: the caller owns dispatch, owes the frames in the order
    :attr:`CombatStep.frames` returns them, and owes :func:`commit_step` before
    sending any of them.

    ``aggro`` may be None, which is the supported production wiring: the damage
    half then runs without a probe lane being reachable from dispatch at all,
    and ``threat_recorded`` on the step is False.
    """
    if type(mob) is not FieldMob:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "mob must be the typed FieldMob record")
    row = ledger.balance_of(mob.actor_identity)
    if row.max_hp != mob.max_hp:
        # Caught by review, not by a crash: with a ledger row built from some
        # other ceiling, the announced number came from the roster row and the
        # bar frame from the ledger row, so the client saw "99" float while the
        # bar fell 3856.
        raise MobCombatContractError(
            REFUSE_LEDGER_ROW_DISAGREES_WITH_ROSTER,
            "identity 0x%X stands at a ceiling of %d in the ledger and %d in "
            "the roster" % (mob.actor_identity, row.max_hp, mob.max_hp),
        )
    damage = resolve_damage(attacker, mob_defender(mob))
    moved_ledger, outcome = apply_hit(
        ledger, attacker_identity, mob.actor_identity, damage)
    if aggro is None:
        moved_state = aggro_state
    else:
        moved_state = apply_threat(aggro, aggro_state, outcome)
    if outcome.no_room:
        return CombatStep(
            moved_ledger, moved_state, outcome, b"", b"", b"", b"",
            ledger.generation, False,
        )
    announce_pc, announce_frame = announce_frames(
        legacy, attacker_identity, mob, outcome)
    if outcome.hp_after == HP_FLOOR:
        # The killing blow.  The number still floats; the bar does not get
        # repainted, because a body at zero with no death timer is a state the
        # client's gate cannot read.  mob_death.kill composes what comes next
        # and the step says so through death_due.
        return CombatStep(
            moved_ledger, moved_state, outcome,
            announce_pc, announce_frame, b"", b"",
            ledger.generation, threat_was_recorded(aggro_state, moved_state),
        )
    bar_pc, bar_frame = bar_frames(
        legacy, mob, outcome.hp_after, faction=faction)
    return CombatStep(
        moved_ledger, moved_state, outcome,
        announce_pc, announce_frame, bar_pc, bar_frame,
        ledger.generation, threat_was_recorded(aggro_state, moved_state),
    )


def attack_from_observed_action(
    legacy: Any,
    aggro: Any,
    ledger: CombatLedger,
    aggro_state: Any,
    action_fields: dict,
    attacker_identity: int,
    attacker: Combatant,
    *,
    roster: tuple[FieldMob, ...] | None = None,
    faction: int = field_mobs.FIELD_MOB_FACTION,
) -> CombatStep | None:
    """Drive one hit from an inbound SCENE-007 ActionVital.

    ``action_fields`` is what ``action_ack.parse_scene006_ea7d`` returns: the
    target identity is ``field_qword_20``.  Returns None - not an exception -
    when the target is not a monster in the roster at all, because a player
    actioning a townsperson is an ordinary event and not a contract breach.

    A target that IS in the roster but is NOT in the ledger is a different
    thing entirely - a roster/ledger desync in which every hit on that monster
    would silently do nothing forever - and it is REFUSED by name.  The first
    draft returned None for both and documented only the first.
    """
    if type(action_fields) is not dict:
        raise MobCombatContractError(
            REFUSE_ACTION_FIELDS_MALFORMED,
            "action fields must be the dict the EA7D parser returns")
    if "field_qword_20" not in action_fields:
        raise MobCombatContractError(
            REFUSE_ACTION_FIELDS_MALFORMED,
            "action fields carry no target identity at field_qword_20")
    target = _require_identity(
        action_fields["field_qword_20"], "target identity")
    mobs = field_mobs.load_roster() if roster is None else roster
    for mob in mobs:
        if mob.actor_identity == target:
            if target not in ledger.identities():
                raise MobCombatContractError(
                    REFUSE_TARGET_NOT_IN_LEDGER,
                    "identity 0x%X is in the roster but not in this ledger: "
                    "the two were built from different rosters" % target,
                )
            return strike(
                legacy, aggro, ledger, aggro_state, mob,
                attacker_identity, attacker, faction=faction,
            )
    return None


def describe_step(step: CombatStep) -> tuple[str, ...]:
    """Console lines for a hit, in the shape the runtime console prints."""
    if type(step) is not CombatStep:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "step must be a typed CombatStep")
    outcome = step.outcome
    lines = [
        "MOB-COMBAT-001 hit: performer 0x%X -> target 0x%X" % (
            outcome.attacker_identity, outcome.target_identity),
        "  damage announced %d, applied %d, hp %d -> %d of %d (%.1f%%)" % (
            outcome.damage_wire, outcome.applied, outcome.hp_before,
            outcome.hp_after, outcome.max_hp,
            100.0 * outcome.hp_after / outcome.max_hp),
        "  frames: announce %d bytes, bar %d bytes" % (
            len(step.announce_frame), len(step.bar_frame)),
    ]
    if outcome.no_room:
        lines.append(
            "  nothing sent: the target is already dead at %d HP, so the wire "
            "stays silent rather than answering MISS to a real hit of %d" % (
                HP_FLOOR, outcome.clamped_by))
    if not step.threat_recorded and not outcome.no_room:
        lines.append(
            "  threat NOT recorded: no aggro handle was passed, or the mob is "
            "in its return/dead phase, where mob_aggro absorbs damage by "
            "design")
    if outcome.clamped_by:
        lines.append(
            "  overkill by %d: the balance stops at %d and the announced "
            "number is the number subtracted" % (outcome.clamped_by, HP_FLOOR))
    if step.death_due:
        lines.append(
            "  death due: this monster is at 0 HP and owes two frames - call "
            "mob_death.kill(legacy, mob, step.outcome, register) now")
    return tuple(lines)


PIN_ID = "mob_combat_first_half_001"
PIN_BUILD_ORDER = MOB_COMBAT_BUILD_ORDER
PIN_LANE = MOB_COMBAT_LANE

# The pinned attacker is the HYP-PF-038 "MOB_WEAK" profile, on purpose: fed to
# this general driver against placement 30 it must reproduce -964, the first
# rung of the ladder two observers watched land on a real screen in GT-035.  A
# pin whose numbers nobody has ever seen would prove only that the code agrees
# with itself.
# ~~field_mobs.CONTROL_PLACEMENT_INDEX~~ -- round szdkgs moved that constant
# to the roster's own control row (placement 103), and this pin must NOT
# follow it: what this document pins is a kill on the SANCTIONED FIRST TARGET
# 0x201F, an actor named by PANYA-RULINGS-FOUR, not by whichever row the table
# happens to use as its control.  Placement 30 is still in the shipped roster
# (as the legacy set-number reading, pending migration), so the pin is
# unchanged this round; when that row is migrated, this pin moves WITH a
# ruling, not with a table.
# ROUND 8ftmbx: that row IS migrated, and this pin STILL does not follow the
# table -- for the opposite reason to mob_death's.  This document is the
# cross-check against GT-035, the only ladder anyone has WATCHED, and it was
# watched on this actor.  Pointing it at the new control row would compare
# today's arithmetic against numbers nobody ever saw land on that monster,
# which is exactly the "the code agrees with itself" pin the paragraph above
# refuses.  So the subject stays placement 30 and is now built explicitly by
# field_mobs.gt035_observed_subject() rather than looked up in a roster that
# no longer contains it.  The index is kept as the name of that subject.
PIN_PLACEMENT_INDEX = field_mobs.LEGACY_SETNUM_CONTROL_PLACEMENT_INDEX


def pin_subject() -> FieldMob:
    """The actor this pin's numbers were watched on (GT-035), never a roster row.

    Callers used to find it with ``[m for m in load_roster() if
    m.placement_index == PIN_PLACEMENT_INDEX][0]``; that lookup is what broke
    when the row was withdrawn, and re-pointing it at a shipped row would
    have changed the pin's subject in silence.  Named here so a reader of the
    pin can see which actor produced its numbers without reconstructing it.
    """
    return field_mobs.gt035_observed_subject()
PIN_ATTACKER_LEVEL = 7
PIN_ATTACKER_ABILITY_STR = 132


def pin_attacker() -> Combatant:
    return Combatant(
        level=PIN_ATTACKER_LEVEL,
        ability_str=PIN_ATTACKER_ABILITY_STR,
        ability_con=0,
    )


def pin_document(
    legacy: Any, mob: FieldMob, attacker: Combatant | None = None,
) -> dict:
    """The numbers a report should quote, computed rather than transcribed.

    Lives in ``scenarios/`` because that is where this project keeps its pins;
    it is NOT a scenario, declares so in its own body, and no loader reads it.
    """
    if attacker is None:
        attacker = pin_attacker()
    # ~~open_ledger()~~ -- the default ledger is bg0001's shipped roster, and
    # round 8ftmbx withdrew this pin's subject from it (see PIN_PLACEMENT_INDEX
    # on why the subject did not move).  The ledger is opened on the mob being
    # pinned instead, which is what it always meant: a ledger is a per-monster
    # HP balance, and the only monster this document is about is this one.
    ledger = open_ledger(roster=(mob,))
    step = strike(legacy, None, ledger, None, mob, 0x750059, attacker)
    outcome = step.outcome
    return {
        "pin_id": PIN_ID,
        "build_order": PIN_BUILD_ORDER,
        "lane": PIN_LANE,
        "milestone": MOB_COMBAT_MILESTONE,
        "production_allowed": production_allowed,
        "test_only": test_only,
        "not_a_scenario": True,
        "target_identity": mob.actor_identity,
        # ascii() for the same reason field_mobs.roster_report uses it: this
        # gets printed on a code page 874 console, and a field scene's MOBS_TIP
        # name is not guaranteed to be ASCII the way bg0001's own rows are.
        "target_name": ascii(mob.display_name),
        # ADDED round 8ftmbx, because pf-adversary (D5) showed this document
        # was the more misleading of the two pins after the migration: it
        # names an actor with production_allowed true and test_only false,
        # and said nothing about the fact that the actor is no longer on the
        # wire at all.  An attended ticket written from this pin would have
        # sent a tester to hunt 0x201F in game and find a townsman.
        "target_is_in_the_shipped_roster": mob.actor_identity in {
            row.actor_identity for row in field_mobs.load_roster()
        },
        "target_is_the_gt035_observed_actor": (
            mob.placement_index == PIN_PLACEMENT_INDEX),
        "target_withdrawn_note": (
            "bg0001 placement 30 as the SET-NUMBER reading rendered it.  "
            "COO-DECISION 2026-08-29T00:41+07:00 withdrew that row: under "
            "the RE-128 crosswalk this placement is n_ID 248 'Da Vinci', a "
            "townsman, and that is what the census sends today.  This pin "
            "keeps the withdrawn actor ON PURPOSE -- GT-035's damage ladder "
            "was watched on it, and comparing today's arithmetic against a "
            "different actor's numbers would prove nothing.  DO NOT target "
            "this identity in an attended session; the roster's own control "
            "row is placement 103."
        ),
        "target_position": [mob.x, mob.y, mob.z],
        "target_faction": field_mobs.FIELD_MOB_FACTION,
        "target_level": mob.level,
        "attacker_level": attacker.level,
        "attacker_ability_str": attacker.ability_str,
        "attacker_attack": attacker.attack,
        "target_defence": mob_defender(mob).defence,
        "max_hp": outcome.max_hp,
        "damage": outcome.damage,
        "damage_wire": outcome.damage_wire,
        "hp_after": outcome.hp_after,
        "fraction_after": outcome.hp_after / outcome.max_hp,
        "announce_frame_bytes": len(step.announce_frame),
        "bar_frame_bytes": len(step.bar_frame),
        "hp_floor": HP_FLOOR,
        "death_due": step.death_due,
        "death_handover": "mob_death.kill(legacy, mob, step.outcome, register)",
        "threat_recorded": step.threat_recorded,
        "wiring": MOB_COMBAT_WIRING,
        "selection": "none_default_behaviour_no_scenario_flag",
        "nonclaims": list(MOB_COMBAT_NONCLAIMS),
    }
