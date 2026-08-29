"""Pin the Foundation/legacy seam and the evidence manifests that back the matrix.

M13 established three facts that nothing in the suite was watching:

  1. The Foundation server is not an alternative to the frozen V141 scenario
     runner.  ``app.py`` loads ``current/pf_login_game_server_v141.py`` and
     ``runtime.make_state_class`` returns a subclass of ``legacy.GameSessionState``
     that calls ``super().dispatch()`` for everything it does not override.  A
     ``runtime_pass`` produced by a Foundation process therefore does not imply
     that Foundation code produced the behavior.
  2. The five opt-in scenario modes are mutually exclusive, so no single server
     run can exhibit every green row, and the launcher used by the playbook
     enables none of them.
  3. Every ``reports/*.manifest`` line still hashes to its recorded sha256, but
     four ``runtime_pass`` rows cite no manifest-backed report at all.

These tests freeze that state.  They are deliberately structural: they assert
what the seam *is*, not that any particular capability works.  A change that
re-points the legacy module, flattens the subclass, makes the modes composable,
or grows the manifest-debt list has to say so in the same commit.

Saying so (SCENARIO-COMPOSE-001, owner rulings by Panya 2026-08-24):
make_state_class modes became composable for an exact allow-list only --
first (chief cloud round R153) the pair ground_loot_hypothesis_scenario
with pickup_listener_hypothesis_scenario, then (chief cloud round R155)
that same pair plus item_operate_res_hypothesis_scenario as the one
allowed triple (runtime.py COMPOSABLE_SCENARIO_LANE_SETS; renamed from
COMPOSABLE_SCENARIO_LANE_PAIRS when the first non-pair member arrived).
None of the five SCENARIO_MODES below is in either allow-listed set, so
fact 2 and the pairwise sweep in this file stay true of those five exactly
as written; the pair's composition is proven in
tests/test_pickup_listener_hypothesis.py, the triple's (and the
still-refused combinations) in tests/test_item_operate_res_hypothesis.py.
"""

import ast
import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
REPORTS = ROOT / "reports"
COVERAGE = ROOT / "docs" / "FUNCTIONAL_COVERAGE.json"
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.runtime import make_state_class  # noqa: E402

# The frozen module the Foundation server is built on.  Changing this pin means
# the whole evidence base moves to a different legacy baseline.
PINNED_LEGACY_MODULE = "current/pf_login_game_server_v141.py"

# The five strictly opt-in scenario parameters of make_state_class.  At most one
# may be active in a run; see test_scenario_modes_are_mutually_exclusive.
SCENARIO_MODES = (
    "scenario",
    "scene_load_scenario",
    "population_scenario",
    "item_move_capture_scenario",
    "item_move_hypothesis_scenario",
)

# Rows graded runtime_pass whose evidence has no .manifest, i.e. whose runtime
# claim rests on report prose rather than on hash-pinned artifacts.  This is
# recorded debt, not an accepted practice: the set may shrink, and shrinking it
# is expected to update this list in the same commit.
MANIFEST_DEBT_RUNTIME_PASS = {
    "movement/npc_locomotion_presentation",
    "movement/teleport_transport",
    "npc_interaction/npc_conversation_handshake",
    "npc_interaction/conversation_operation_sequence",
}

# sha256 over every graded field of every row -- id, status, required, evidence
# refs, test refs, next_missing_behavior, domain_complete -- and nothing else.
# `notes` is excluded on purpose so prose corrections stay cheap while any grade
# movement has to be deliberate.
GRADE_SUBSET_SHA256 = (
    # This pin covers ONE deliberate movement (CORE-REQUEST-014, chief cloud
    # round 4txjyg/R192, 2026-08-27 +07:00): npc_conversation_handshake and
    # quest_accept_and_progress (domain npc_interaction) each gain TWO test
    # refs -- tests/test_columbus_quest_dispatch.py and
    # tests/test_columbus_quest_dispatch_wiring.py.  NEITHER ROW'S STATUS
    # MOVES: npc_conversation_handshake stays runtime_pass (a second actor,
    # Columbus, now composes the same generalised NPCConversation shape RE-094
    # proved, alongside the existing P0/quest-3020 singleton -- still one
    # composition per armed actor, same wire) and quest_accept_and_progress
    # stays in_progress (Columbus's quest-3021 op1 reaches a real dispatch
    # call but that call ALWAYS refuses today on two open evidence gaps -- no
    # pinned scene-17 arrival spawn, no vehicle-bind wire payload -- so no
    # quest state is stored server-side, no tracker update is proven, and
    # completion/rewards stay untouched, exactly as this row's notes already
    # said).  Refs move because they are graded fields and an untested claim
    # of "this new code exercises that row" would be exactly the kind of
    # drift this digest exists to catch -- same lesson round 7ptoku wrote here
    # first.  Previous pin, kept greppable rather than dropped:
    #   R173 / merged 403D468D3D6E828D1FF61E188CCEF45160520A09B56E3987EDE41624255123F3
    #
    # This pin covers ONE deliberate movement (WORLD-CENSUS-001, chief cloud
    # round R173, 2026-08-26 +07:00): world/scene_actor_population_streaming
    # gains ONE test ref, tests/test_world_census_wiring.py.  The row's STATUS
    # DOES NOT MOVE and nothing here claims the census works: it stays
    # runtime_pass for the nearest-20 wire it was graded on, because no client
    # has been shown a 115-actor collection and the highest count with a
    # recorded runtime result in this project is still 20.  What changed is
    # that the DEFAULT boot now sends the whole 115-row bg0001 census instead
    # of three placements -- wired in runtime.py, proven headless only -- so a
    # row whose test refs did not include the test that drives that wire would
    # have been silently wrong about its own coverage.  The row's notes record
    # the same thing in prose, and prose is outside this digest by design.
    # GT-078 is the attended ticket that could move the status; it has not run.
    #   R167 / parent 6CF4AE24A70C7DC8EE447310A640098615B5D9F68AB368D58717C501B4DB4553
    #
    # MERGE (attended rebuild of PR #41, 2026-08-26 +07:00): the R173 movement
    # above is merged onto the main line that had moved past it (rounds vvkff9,
    # 7ptoku and g627j0 below).  No grade field was edited by hand on either
    # side; docs/FUNCTIONAL_COVERAGE.json auto-merged, and the digest below is
    # recomputed over that merged document by grade_digest() in this file,
    # which is the only value that can satisfy both.  BOTH PARENT DIGESTS ARE
    # KEPT HERE, same rule as the R167 merge block further down:
    #   R173  / lane  F80ADB72621F31B2E63EAED9DF6B553B96C79C8E26D6A3E0D3C3E83BE5710926
    #   main  / g627j0 2828B9EDABCCB1123B27DC79B63C280FF536BBF4B423C556BEB716257CCAAC53
    #
    # ROUND vvkff9 (LANE-B, 2026-08-26 +07:00): moved deliberately, and it is
    # the same KIND of movement as the 7ptoku block below -- refs, never a
    # grade.  monster_spawn_and_loot gains two evidence refs
    # (src/pirateforce_foundation/mob_pickup.py,
    # scenarios/combat_pickup_001.json) and one test ref
    # (tests/test_mob_pickup.py) for MOB-PICKUP-001, the server-side pickup
    # transaction.  The row's STATUS DOES NOT MOVE and stays in_progress:
    # nothing dispatches the module, no database row is written by anything,
    # the pickup transport is still unidentified, and no player has picked
    # anything up.  The refs move because they are the graded fields -- an
    # adversarial pass on the previous lane-B round established that a prose
    # amendment alone leaves a machine reading this file unable to find the
    # new lane at all.  Previous pin, kept greppable rather than dropped:
    #   R167 / merged BEA0024925EFB3637A03A4BE69380B882335E1AFD50D63A9DE7F73D23CC3074F
    #
    # ROUND 7ptoku (LANE-B, 2026-08-26 +07:00): moved deliberately, and this
    # is what a deliberate movement looks like when it is NOT a grade change.
    # Domain 3 / hp_death_and_respawn gains two refs -- tests/test_mob_death.py
    # and scenarios/combat_death_001.json -- because MOB-DEATH-001 emits the
    # same BasicAttr bit 0x0080 that row is about, on the actor-entry carrier,
    # with no flag.  The row's STATUS does not move: this lane adds no runtime
    # evidence and claims none.  An adversarial review found the prose
    # amendment alone left the structured refs pointing only at the old lane,
    # so a machine reading this file could not find the new one; the refs are
    # graded fields, so fixing that has to move this digest.
    # This pin covers TWO deliberate movements that land in the same change
    # (chief cloud round R167, 2026-08-25 +07:00).  They are recorded below in
    # the order they were written, newest first.  R167 itself moves no grade
    # field of its own: it merges the R165 ground-loot-nameprop lane, whose
    # branch was gate-green (run 32838572131, sha 13baff27..) but never had a
    # pull request opened for it, onto the R166 main line that had moved past
    # it.  Both prose blocks are kept verbatim so neither movement loses its
    # record; the digest below is recomputed over the merged document, which is
    # the only value that can satisfy both.  BOTH PARENT DIGESTS ARE KEPT HERE,
    # because a merge that recomputes a pin must not take its parents' pins out
    # of the tree -- an auditor asking what main actually asserted at 017af1c,
    # or what the lane branch asserted at 13baff27, has to be able to grep for
    # it rather than reconstruct it from the reflog:
    #   R166 / main   68F9C1454037A525C67C3F37B0DA41385AD3E21EF24661B02C1CB12B2F9FA8D5
    #   R165 / lane   81DCC20F0B6DA6F3DD45885736F74A8A706127088A1EA6437CFC5B179AB25DF0
    #   R154 / before 39034397..F60C (the shared ancestor both sides cite below)
    #
    # This pin covers ONE deliberate movement
    # (LOGOUT-TRANSITION-GT033-ANSWERED, 2026-08-25, chief cloud round R166):
    # session_lifecycle/clean_logout stays in_progress -- its grade does NOT
    # move and nobody claims the behaviour works -- but the row gains FOUR
    # evidence refs (scenarios/logout_hypothesis_ack_close.json,
    # scenarios/logout_hypothesis_return_select_server.json,
    # scenarios/logout_hypothesis_chat_push_return_select.json and the new
    # reports/PF_GT033_LOGOUT_TRANSITION_AB_CLIENT_OBSERVABLE_NEGATIVE_20260825.md)
    # plus TWO test refs (tests/test_logout_return_select_hypothesis.py,
    # tests/test_logout_chat_push_hypothesis.py), taking the row to 9 evidence
    # refs and 4 test refs.  Why now: the row's prose had stood untouched since
    # 2026-08-18, still named "0x3D4B-first" as the next design, and its
    # evidence refs pointed only at the two shapes falsified that day.  The
    # attended GT-033 runs of 2026-08-25 (jobs 1143-1152, three cells of a
    # four-cell table, three separate boots sharing one boot commit
    # 06b62abd423cff9fc9c965d52178fd2fca62c38e, CODE_DELTA 0 -- so the control
    # holds at commit level, not boot level) measured two further response
    # shapes at the client-observable layer and neither makes the client leave
    # the map: HYP-PF-028 put a hash-pinned ReturnSelectServerVital 0x709E on
    # the wire ahead of the ack, answering a genuine owner-pressed LogoutVital
    # subcode 03, and the client did not transition; HYP-PF-013 (ack+close,
    # differing by exactly that one frame, verified by an outbound-frame census
    # over the whole run) did not transition on subcode 03 and did not
    # self-exit on subcode 01.  The fourth cell (variant B on subcode 01) was
    # deliberately cut: it is UNMEASURED, not answered, the table must not be
    # read as complete, and once the code moves it can never again be measured
    # under this boot commit.  This is NOT a falsification of connection
    # teardown: nobody checked whether the client kept sending after the close
    # and no positive control for an in-map disconnect symptom exists anywhere
    # in this project, so "saw it and did nothing" is not separated from "never
    # saw it".  0x3D4B-first was never run and is NOT resurrected here; the
    # branch this round chose is the orchestrator mode/timer (vtable 0xf45030),
    # queued on the bridge as RE-070 -- but the ticket's three-branch table was
    # not exhaustive and most of the branches it missed are still measurable
    # in-game, so the remaining work is NOT static-only and the row is
    # in_progress rather than blocked.  The full record, including all eight
    # nonclaims, is the new report ref; the summary in the coverage row must
    # not be read in its place.  A first draft of this same round called the
    # run the first time a real client received 0x709E bytes -- false, GT-033
    # variant C did so on 2026-08-23 -- and the adversary round that caught
    # that also drove the HYP-PF-028 evidence_gap amendment and the
    # CANONICAL_CONTENT_SHA256 re-pin that ride in the same change.  The ledger
    # GROWS by nothing: count stays 46, no entry added, removed or reindexed.
    #
    # This pin covers ONE deliberate movement (GROUND-LOOT-NAMEPROP-001,
    # 2026-08-25, chief cloud round R165): npc_interaction/
    # monster_spawn_and_loot stays in_progress but gains two evidence refs
    # (src/pirateforce_foundation/ground_loot_nameprop_hypothesis.py and
    # scenarios/ground_loot_nameprop_probe.json) and one test ref
    # (tests/test_ground_loot_nameprop_hypothesis.py) for HYP-PF-039 -- a
    # SEPARATE lane from GROUND-LOOT-001, mutually exclusive with it and
    # with every other mode, that asks whether the name-property selector
    # RE-067 pinned reaches the floating item label.  It sends a CONTROL
    # element (mask 0x12, no selector fields) and a TREATMENT element (mask
    # 0x3A, the gate at +0x1B and index 6 at +0x1A) at the SAME position
    # with the SAME payload dword, so the presence of those two fields is
    # the only variable.  RE-067 pinned that a zero gate makes the client
    # use the default UI text property 0x34 and that an index of 1..6 maps
    # through dword [index*4+0x00F30EC4] to 0x5D..0x62 -- property ids, NOT
    # a palette, which is why the lane is NAMEPROP and not NAMECOLOR.  The
    # attended question is GT-069, and the entry is pushed for the owner's
    # ruling rather than merged (HYP-PF-032 is at 3/3 and its expiry
    # decision has no new-entry clause).  R167 CORRECTS BOTH HALVES OF THAT
    # PARENTHESIS: the entry was merged in the end, because the owner ruled at
    # ~17:5x (+07:00) that it should exist as a new entry; 3/3 is now 3/5 after
    # the ~18:15 ceiling raise, though HYP-PF-032 stays FROZEN at three by the
    # earlier ruling and carries a note in the ledger saying so; and the
    # new-entry claim is narrow-true at best -- 032's expiry.decision has no
    # such clause, its stop_rule ends with one, and it was that disagreement
    # between the two fields that sent the question to the owner.  Status, required and
    # next_missing_behavior are untouched everywhere; only that one row's
    # ref lists moved, which is what the digest is for.  Previous pin
    # 39034397..F60C (round R154) recorded the movement described below.
    # ---- lineage of the previous pin, kept verbatim ----
    # This pin covered ONE deliberate movement (ITEMOP-RES-GREENLINE-001,
    # 2026-08-24, chief cloud round R154): presentation/
    # system_message_display stays in_progress but gains one evidence ref
    # (scenarios/item_operate_res_greenline_sweep.json) and one test ref
    # (tests/test_item_operate_res_hypothesis.py) for HYP-PF-037 -- the
    # pinned ItemOperateVitalRes 0x4C13 sweep the attended GT-063 ticket
    # fires to learn which shape puts the green message-id-131 chat line
    # ("received [ $V1 ] * $V2" -- an ASCII rendering of the Thai template,
    # kept ASCII here for cp874 discipline; GT-049: emitted from the INBOUND 0x4C13
    # handler chain 0x005EF5E0 -> 0x005CC309, so the server decides) on
    # the real screen.  Behind --item-operate-res-hypothesis-scenario one
    # accepted ascii12 trigger from the pinned smoke identity is answered
    # with THREE frames through the V111-accepted golden codec
    # (inventory.make_item_move_delta_response): the RE-059 frame-1
    # capture replay, whose dual derivation -- committed capture hex on
    # one side, the codec over ItemAttrState(1, 2600001, 2, 2) on the
    # other -- is re-compared at every composition, then the same proven
    # bag-update shape carrying the RE-060 consumable 2400901 at quantity
    # 1 and at quantity 5.  The vital version byte 2 is CAPTURE-PINNED
    # (all five RE-059 frames), affected_identity_count stays 0 in every
    # frame (the count>0 element shape is statically OPEN -- R13
    # membership -- and went to the bridge as RE-064 instead of onto a
    # socket), and the status deliberately does NOT move: nobody has ever
    # recorded what a screen shows for any of these frames -- that is
    # exactly the attended GT-063 question.  The ledger GROWS: HYP-PF-037
    # appended, count 44 -> 45, every existing index stable.
    #
    # Previous pin BC582520..297C covered ONE deliberate movement
    # (PICKUP-LISTENER-001,
    # 2026-08-24, cloud round R151): npc_interaction/monster_spawn_and_loot
    # stays in_progress but gains two evidence refs
    # (src/pirateforce_foundation/pickup_listener_hypothesis.py and
    # scenarios/pickup_listener_hypothesis_decode_probe.json) and one test
    # ref (tests/test_pickup_listener_hypothesis.py) for HYP-PF-036 -- the
    # inbound strict decoder for the PickupTerrainThing pickup request.
    # The codec is statically CLOSED (PF_SERIALIZER_FIELDS rows 859-862:
    # u32 tag 0x14 at object+0x14, u8 tag 0x08 at object+0x18, serializer
    # span [0x005E5E30,0x005E5E83) sha256 8e439d4f..) and GT-046 proved
    # the client-outbound mouse-click producer 0x006B0639 -- but the vital
    # id 0x4543 is DERIVED from the name-hash only and has NEVER been
    # observed on any wire (the runtime id slot is zero on disk; the
    # capture corpus holds zero frames of it in either direction), which
    # is why the lane is decode-count-and-record ONLY behind
    # --pickup-listener-hypothesis-scenario: no reply, no pickup rule, no
    # write, listen-only.  The same change corrects the row's notes per
    # the 2026-08-23 15:20 erratum letter (the 'pre-placed quest-object
    # system' reading of PickupTerrainThing is retracted -- GT-046 job 5
    # proved +0x14 comes from a live runtime drop-object -- while the
    # FightingDrop* monster-drop caution stands); notes are excluded from
    # this digest, the ref additions are what move it.  The status
    # deliberately does NOT move: no client frame of this vital has ever
    # been observed and the attended opcode question has not run.  The
    # ledger GROWS: HYP-PF-036 appended, count 43 -> 44, every existing
    # index stable.
    #
    # Previous pin E443800F..FC06 covered ONE deliberate movement
    # (SKILL-ATTR-001,
    # 2026-08-24, cloud): combat/skill_use stays in_progress but gains one
    # evidence ref (scenarios/skill_attr_hypothesis_attr_sweep.json) and
    # one test ref (tests/test_skill_attr_hypothesis.py) for HYP-PF-035 --
    # the server-side encoder for the 0x1661 skill-attr block RE-061
    # pinned byte-exactly from the read-only client image as the Skill
    # window controller gate's prerequisite (body serializer 0x7520B0:
    # DBAttribute u8 mask + u64 identity, u16 record_count, per record
    # u16 key / u16 opaque / u32 opaque; carrier UpdateAttrVital 0x309A
    # attr collection with class id 0x1661; window gate init 0x761ED0
    # returns false when the container derived from [actor+0x3E8] is
    # absent -- the leading static explanation of GT-058's K-does-not-
    # open finding).  Behind --skill-attr-hypothesis-scenario one accepted
    # ascii12 trigger from the pinned smoke identity is answered with two
    # pinned frames (record_count 0, then one arbitrary probe record
    # key=1/0/0), every frame hash-pinned in module and scenario plus
    # golden full-hex test pins.  The opaque field semantics stay unknown
    # and unnamed, one packet is NOT claimed sufficient to open the
    # window, and the status deliberately does NOT move: no client has
    # ever seen one of these frames -- that is the queued attended GT
    # ticket.  The ledger GROWS: HYP-PF-035 appended, count 42 -> 43,
    # every existing index stable.  The STATS-PROG-001 static guard test
    # 24 gained its fourth exact exception triple (its third owning
    # module) in the same change rather than be worked around.
    #
    # Previous pin 203CF083..B6DC covered ONE deliberate movement (R147
    # re-land by R148,
    # 2026-08-24, cloud): combat/monster_spawn_and_loot not_started ->
    # in_progress.  The entry was stale -- loot work had in fact begun
    # (door 2 roll: loot_roll.py LOOT-ROLL-001; door 3 render hypothesis:
    # ground_loot_hypothesis.py GROUND-LOOT-001, GT-045 WIRE PASS / CLIENT
    # NO-RESULT; door 4b/5 carrier: inventory.py ItemOperateVitalRes 0x4C13
    # already ships and is client-accepted) -- so the row gains six
    # evidence refs and three test refs and records the true next missing
    # behavior (whether a 0x4C13 acquire body fires the client id-131 green
    # line; bridge tickets RE-059/RE-060 already queued, do not duplicate).
    # The original commit (4bf8da6, chief round R147) moved these grade
    # fields WITHOUT moving this pin -- exactly the mistake this pin exists
    # to force into the open -- and the gate correctly went red (run
    # 32696299639) and the PR was auto-closed with the branch kept.  R148
    # re-lands the same edit with the pin moved in the same commit.  No
    # code, ledger or scenario changes ride along.
    #
    # Previous pin AAC38258..51CD covered ONE deliberate movement
    # (LEARN-SKILL-REQUEST-001,
    # 2026-08-24, cloud): combat/skill_use stays in_progress but gains one
    # evidence ref (scenarios/learn_skill_request_hypothesis_decode_probe
    # .json) and one test ref (tests/test_learn_skill_request_hypothesis.py)
    # for HYP-PF-034 -- the INBOUND half of the learn-skill lane and the
    # first server-side inbound decoder for any of the five progression
    # verbs.  The CLearnSkillVital 0x36AA body shape comes from COMMITTED
    # ARTIFACTS ONLY (PF_SERIALIZER_FIELDS.tsv, four byte-symmetric W/R
    # rows re-verified by GT-050 jobs 1-2: u32 tag 0x14 at object+0x14 then
    # u8 tag 0x0B at object+0x18, 7 bytes), and behind
    # --learn-skill-request-hypothesis-scenario one accepted inbound frame
    # is strictly decoded, counted and recorded -- and NOTHING is sent back
    # and nothing is written: no learn rule exists and none is invented.
    # The field semantics stay unknown and unnamed, the natural direction
    # of 0x36AA is UNPROVEN (the direction census is bridge work, queued),
    # and the status deliberately does NOT move.  The ledger GROWS:
    # HYP-PF-034 appended, count 41 -> 42, every existing index stable.
    # The STATS-PROG-001 static guard test 24 gained its third exact
    # exception triple (its second owning module) in the same commit rather
    # than be worked around.
    #
    # Previous pin 2BC8A93C..F407 covered ONE deliberate movement
    # (LEARN-SKILL-RESULT-001,
    # 2026-08-23, cloud): combat/skill_use stays in_progress but gains one
    # evidence ref (scenarios/learn_skill_result_hypothesis_learn_sweep.json)
    # and one test ref (tests/test_learn_skill_result_hypothesis.py) for
    # HYP-PF-033 -- the first server-side encoder for one of the five
    # progression verbs.  GT-050 closed the CLearnSkillResultVital 0x673C
    # body shape byte-exactly from the read-only client image (u16 tag 0x12
    # count, then count 12-byte-stride records of u32 tag 0x14 / u16 tag
    # 0x12 / u32 tag 0x14, then u8 tag 0x0B at object+0x2C; W and R loops
    # agree), and behind --learn-skill-result-hypothesis-scenario one
    # accepted ascii12 trigger is answered with five pinned frames -- count
    # 0/1/3, both trailing values, the count=1 pair differing in exactly the
    # one unexplained trailing byte -- through the frozen v141
    # make_runtime_vitals envelope, every frame hash-pinned and re-decoded
    # before it is queued.  The record SEMANTICS stay unknown and unnamed
    # (opaque triples named by wire position only), the inbound 0x36AA
    # direction is NOT implemented, and the status deliberately does NOT
    # move: no client has ever seen a 0x673C frame -- that is the queued
    # attended GT ticket.  The ledger GROWS: HYP-PF-033 appended, count
    # 40 -> 41, every existing index stable.  The STATS-PROG-001 static
    # guard test 24 was amended in the same commit to name its one exact
    # exception rather than be worked around.
    #
    # Previous pin 18504603..6432 covered ONE deliberate movement (chief
    # round 116, 2026-08-21,
    # cloud): movement/local_player_movement_authority stays in_progress but
    # gains one evidence ref and two test refs for MOVE-AUTHORITY-002
    # (HYP-PF-030) -- the first lane in this tree that answers with a WITHHELD
    # DURABLE WRITE instead of bytes.  Behind its opt-in scenario the server
    # decides, per reported TargetPosVital singleton, whether the position
    # checkpoint may be written at all, and refuses it by name when the report
    # exceeds our own step, vertical or speed budget; the refused reading never
    # becomes the baseline the next report is measured against.  Nothing is
    # composed on any path -- for the same frame the gated and ungated sessions
    # return the same action list -- because no captured frame, producer or
    # client-side consumer for a server-initiated corrective reposition exists,
    # so none is invented.  Proven headless at the wire/DB layer only: 48 lane
    # tests and a 78-guard offline verifier.  The status deliberately does NOT
    # move: no client has ever been run against this lane, the budgets are ours
    # and are unvalidated against any real walk (the client const data has mob
    # speed columns in unknown units and no player speed column), and the
    # queued attended test has not run.
    #
    # Previous pin 56EE376C..9394 covered ONE deliberate movement (chief round
    # 96, 2026-08-20):
    # movement/remote_player_movement_projection stays in_progress but gains four
    # evidence refs and two test refs for REMOTE-PLAYER-ENCODER-001 +
    # REMOTE-PLAYER-DISPATCH-001 (HYP-PF-025) -- the first actor_type 2 (CNetActor)
    # frames this tree can compose and dispatch: the five-frame visibility probe
    # (ActorAttr carrying the BasicAttr name bit for the first time on that wire, an
    # opaque replayed AvatarAttr rebound to a probe identity and riding last, two
    # lone-MovementAttr update frames for a known identity, and a wrong-class NPCAttr
    # negative control), proven at the wire/dispatcher layer only (129-guard offline
    # verifier, 162-guard headless replay, 88 lane tests).  The new evidence includes
    # the three imported CHUNK2 static findings whose Q2 result also refines this
    # row's own apply/merge sentence: 0x467130 completes the just-deserialized attr
    # against the PREVIOUS frame's collection copy, and the actor bind is the
    # mask-blind CopyTo at +0x24 = 0x464F30.  The status deliberately does NOT move:
    # no client has ever been shown one byte of actor_type 2, the queued attended
    # visibility test has not run, and a remote HUMAN player still needs chunk 3.
    # The design is ours; the original server is unrecoverable.
    #
    # Previous pin EFCDB531..5A21 covered TWO deliberate movements, both of them
    # attended-runtime results
    # from big rounds #4 and #5 (2026-08-19, tree 11fea4f; both lanes landed at 6891372),
    # and it is the first pin this project has moved on the strength of what was on a
    # screen rather than on what was in the image.
    #
    # 1. character_management/character_deletion in_progress -> runtime_pass, gaining
    #    reports/PF_DELETE_REFRESH001_GT018_LIST_REBUILD_CLIENT_ACCEPTANCE_RUNTIME_PASS_20260819.md.
    #    GT-018 drove one delete through the real UI against a list holding exactly ONE
    #    character and the server answered it with the unchanged HYP-PF-015 echo ack plus
    #    the HYP-PF-021 SelectActorVital 0x36EF rebuild. Round 81's upgraded prediction
    #    was confirmed on BOTH halves: the character left the list (nameboard and model
    #    gone), the 'delete character' button removed itself from the button row (five
    #    buttons to four, i.e. the screen recomputed its affordances from a list it reads
    #    as empty rather than hiding a row), and 'create character' was pressed and did
    #    open the creation screen -- closing both symptoms GT-011 left open. Wire markers
    #    HYP_PF_021_DELETE_ACTOR_SELECTOR00_SOFT_DELETE_COMMITTED then
    #    HYP_PF_021_DELETE_ACTOR_LIST_REBUILD_0; the run used a copy and the canonical
    #    database was never opened. The grade is narrow ON PURPOSE and the note says so in
    #    its own words: slot reuse is still headless-only (the creation screen was opened,
    #    no character was created), the second-password gate ran in bypass, multi-character
    #    deletion and list ordering are untested, every negative path is fail-closed by
    #    test only, and the page-variable route stays a chain of byte facts because
    #    0x107A2C0's live value was never read. Answering a delete with a rebuild remains
    #    OUR designed policy, shown by no capture anywhere.
    #
    # 2. combat/hp_death_and_respawn in_progress -> runtime_pass, gaining
    #    reports/PF_HP_DEATH002_GT019_CLIENT_DERIVED_DEATH_RUNTIME_PASS_20260819.md.
    #    Read the note before reading the status: ONLY THE DEATH HALF IS OBSERVED and the
    #    respawn half has no evidence of any kind, which is why the note names GT-021
    #    (dying_hold) as the first test that will touch it. What GT-019 proved on a real
    #    screen is HP-DEATH-001's central prediction: HP +0x44 (bit 0x0004) at zero plus
    #    the f32 at +0x58 (bit 0x0080) positive is enough, with no further frame, for the
    #    client to derive a death by itself -- HUD '0 /100', a collapsed pose, and a
    #    previously unknown gold-rimmed red cross button captioned in Thai 'abandon the
    #    rescue', which is this project's first evidence that a player-rescue system
    #    exists and that HP == 0 alone raises it. Round #5 photographed it and fired the
    #    sweep eight times in one session, complete every time, lateness under 2.5 ms.
    #    The process note travels with the result: round #4 first called this a FAIL by
    #    straddling the 6.0 s lethal window with point sampling, and the permanent rule is
    #    that a time-ordered test may never conclude 'nothing happened' from point samples.
    #    Deployed DURATION_DYING is still unknown (image 20, scenario sent 60.0f), no
    #    countdown was SEEN in three observed frames which is not the same as none, and
    #    nothing here is claimed about the original server.
    #
    # Neither domain moved: domain_complete stays false for all eight, both banners stay
    # INCOMPLETE, and next_missing_behavior is unchanged in both (character_creation is
    # still in_progress, damage_and_hit_result is still blocked). The manifest-debt list
    # is unchanged because both rows already cite manifest-backed reports
    # (PF_DELETE_SOFT001 and PF_HP_DEATH001); the two new reports carry no .manifest
    # because their artifacts are capture and bridge trees outside the repository.
    # Previous pin 50D475A2..06E6 covered ONE deliberate movement,
    # DELETE-REFRESH-001 (2026-08-19):
    # character_management/character_deletion gains the DELETE-REFRESH-001 evidence and
    # test refs (status already in_progress, unchanged, and deliberately NOT moved to
    # runtime_pass). evidence_refs
    # reports/PF_UI_REFRESH001_CHARACTER_SELECT_STATE_MACHINE_STATIC_20260819.md,
    # scenarios/delete_refresh_hypothesis_list_rebuild.json and
    # tools/verify_delete_refresh_static.py; test_refs
    # tests/test_delete_refresh_hypothesis.py and tests/test_delete_refresh_static.py.
    # Attended GT-011 committed the soft delete, raised no error, and left the
    # character-select list where it was; UI-REFRESH-001 proved from the client image
    # that this was never fixable in the acknowledgement -- the list has ONE buffer
    # ([0x1081A90]+0x180), its only writers are bulk fill 0x5DDD00 (one caller in the
    # image, inside the SelectActorVital 0x36EF apply), append-one 0x5DDE10 (one caller,
    # inside the CreateActorVital apply) and whole-collection clear, and there is NO
    # erase-by-key path anywhere. HYP-PF-021 therefore answers one accepted op-1 delete
    # with two frames: the unchanged hash-pinned HYP-PF-015 echo ack, then the unchanged
    # runtime-proven LegacyProjector.character_list projection over the POST-DELETE row
    # set 0.35 s later. No wire byte is invented -- only the set of rows differs from a
    # frame real clients have accepted at every login -- and the lane verifies and
    # hash-pins the projection (0x36EF v10 header, record-count byte, 0B 00 0B 00 tail,
    # byte-equality with make_runtime_vitals over the payload minus its last two bytes,
    # i.e. the DELETE-SOFT-002 trailing mask, frame == frame_pc(pc), and the 45/55-byte
    # empty-list pins) before the dispatcher may queue it. The milestone also adds a
    # byte-exact finding UI-REFRESH-001 did not have: 0x107A2C0 has 26 references in
    # .text -- 20 immediate writes, 5 reads, and a twenty-first REGISTER writer 0x4BD650
    # (edi = 0) inside 0x4BD5E0, which has zero direct call sites and is
    # cStateCreateActor's vtable slot +0x10, the enter hook the state tick 0x4C7540 runs
    # on phase 0; since the 0x36EF apply builds a fresh cStateCreateActor and calls
    # RequestNext, the same frame is predicted to unstick the page the delete animation
    # left at 0x0B. The ledger GROWS: HYP-PF-021 appended, every existing index stable.
    # NOT runtime_pass: no client has seen a delete answered by a rebuild, the page-reset
    # half is a chain of byte facts rather than an observation, and the headless TCP
    # replay is written but unrun (LOCK-protected boot). That is GT-021, attended.
    # Previous pin 19319329..3991 covered ONE deliberate movement, HP-DEATH-001
    # (2026-08-19):
    # combat/hp_death_and_respawn moves not_started -> in_progress and gains its first
    # evidence and test refs -- evidence_refs
    # reports/PF_HP_DEATH001_HP_DEATH_AND_RESPAWN_STATIC_20260819.md, test_refs
    # tests/test_hp_death_respawn_static.py. Deliberately NOT runtime_pass: nothing was
    # captured, executed or observed; this is the same evidence-first shape STATS-PROG-001
    # used to open the stats lane. What earns the movement is that the lane's central
    # unknown -- "what would a server have to send to make a character die?" -- is now
    # answered byte-exact from the client image alone. Death is a CLIENT-SIDE derivation,
    # not a frame: the four IsDead predicates (0x454AC0 / 0x454A70 on CNetActor and
    # CMyActor, 0x43BDA0 / 0x43BD70 on CNetNPC, CAvatarNPC and Pet) each fetch the bound
    # Attr through vtable +0x74 and return `current HP == 0`, reading BasicAttr +0x44
    # (mask bit 0x0004) under an f32 gate on +0x58 (bit 0x0080) against the constant 0.0f
    # at 0xF0989C; max HP is +0x48 (bit 0x0008), and current-vs-max is earned from the HUD
    # bar helper 0x53EED0 (arg1/arg0, arg1 is the printed number) rather than from the
    # field names. The transition is welded to the attr apply -- 0x4446F0 is
    # `call 0x5DF080 ; call 0x4437C0` -- and 0x4437C0 has exactly one call site in the
    # whole image, latches [actor+0x70] |= 0x200, builds CActorTask_Dead (ctor 0x472810,
    # also one call site) and plays L"_F_DIE_000"; the local player's L"Main_Dead" window
    # is opened per frame from CMyActor vtable +0x18. The verb family is exhaustive, not
    # sampled: of 519 registered protocol classes exactly three carry a death token --
    # ReliveVital 0x1AD4, ReliveMarkerVital 0x3DD6, Pets_NotifySailorDeadVital 0x8B12 --
    # and ReliveVital is one of 69 classes whose inbound slot is the shared no-op
    # 0x710440, so it is REQUEST-ONLY and a server echo of it does nothing. The client
    # also picks no respawn point: CMyActor+0x400 has two readers, and the only use of the
    # marker is its u16 +0x12 as a scene id for a SCENE_NAME_TIP name lookup; there is no
    # movement, teleport or position call anywhere in the relive UI span, and n_DEADLOSS
    # is external data the client only displays. Server gap, counted not eyed: three verbs,
    # zero encoders and zero dispatch; three fields the predicate reads, two emitted -- the
    # gap is exactly one mask bit (0x0080) and one float. Report-only and additive: no
    # src/ change, no scenario, NO ledger entry (count stays 27), no other matrix row and
    # no other axis touched. The one open debt is recorded in the report, not the ledger:
    # the inbound UpdateAttrVital -> 0x4446F0 chain is NOT traced end to end.
    # Previous pin 0C16D386..FE90 (chief round 78, 2026-08-18) covered ONE deliberate
    # movement:
    # character_management/stats_and_progression gains the STATS-PROG-002 evidence and
    # test refs (status already in_progress, unchanged, and deliberately NOT moved to
    # runtime_pass). evidence_refs
    # reports/PF_STATS_PROG002_SERVER_ENCODER_20260818.md and
    # scenarios/stats_progression_hypothesis_xp_sweep.json, test_refs
    # tests/test_stats_progression_hypothesis.py and
    # tests/test_stats_progression_dispatch.py. STATS-PROG-001 measured the gap at
    # nineteen named progression fields, two emitted, zero decoded; this milestone moves
    # the FIELD half of it. src/pirateforce_foundation/stats_progression_hypothesis.py is
    # a generic mask-driven ActorAttr encoder/decoder over 23 fields in the three chained
    # blocks, emitting in ascending mask-bit order -- which is read off the report rather
    # than assumed, because STATS-PROG-001 records a gate-test address per gated field and
    # those addresses ascend strictly with the bits in both tables. The encoder is pinned
    # externally, not self-certified: for the baseline field set it reproduces
    # player_wire.make_actor_attr_with_name byte for byte (73 bytes), a hand-written
    # projection a real client has accepted since NAME-002, and that check runs on every
    # composition. A new opt-in scenario plus the new --stats-progression-hypothesis-scenario
    # flag (explicit --db, mutually exclusive with every other mode including the two chat
    # lanes, which key on the same trigger vital) wires it into runtime.py: one accepted
    # ascii12 frame is a TRIGGER (nothing in it is read) answered with nine UpdateAttrVital
    # 0x309A frames 3.0 s apart -- baseline, exp 1234, exp 987654, level 7, then
    # STR/CON/DEX/INT/PER = 11/22/33/44/55 one at a time, cumulative because V141 records
    # that the client's ActorAttr apply 0x464F30 copies the incoming object whole. Proven on
    # dispatched bytes: nine actions in order, every Attr body at the fixed offset 31
    # re-decoding to the declared cumulative field set, all 27 per-step hashes matching the
    # scenario pins, eighteen frames for two requests with no accumulated state, database
    # byte-identical across accepted and refused windows. The ledger GROWS: HYP-PF-020
    # appended, count 26 -> 27, every existing index stable. NOT runtime_pass: no client has
    # seen one of these frames and no progression field has ever been on this project's wire
    # in either direction -- that is GT-017, attended, unblocked but unanswered. No other
    # lane's module, scenario or test was touched; tests/test_presentation_ownership.py and
    # the STATS-PROG-001 static guards needed no change (the new module spells neither the
    # chat vital id nor any of the five progression verb names).
    # Previous pin B6002E45..E1F3 (round 77) covered ONE deliberate movement:
    # chat/chat_channels_and_routing gains the CHAT-CHANNEL-003 evidence and test
    # refs (status already in_progress, unchanged, and deliberately NOT moved to
    # runtime_pass). evidence_refs
    # reports/PF_CHAT_CHANNEL003_DISPATCH_HOOKUP_HEADLESS_20260818.md and
    # scenarios/channel_message_hypothesis_channel_sweep.json, test_ref
    # tests/test_channel_message_dispatch.py. This is the dispatch hookup
    # CHAT-CHANNEL-002 withheld on purpose: the codec existed but nothing could
    # put a byte on the wire, so GT-016 was unblocked on paper and BLOCKED in
    # practice. A second opt-in scenario file plus the new
    # --channel-message-hypothesis-scenario flag (explicit --db required, mutually
    # exclusive with every other mode including --chat-input-hypothesis-scenario,
    # which keys on the same vital id) wires the lane into runtime.py: one
    # accepted 34-byte ascii12 0xAC52 frame, under the unchanged selected +
    # runtime-ready guards, is DECODED (not spliced) and answered with five
    # composed frames -- LocalTalk, Party, Guild, GMGlobal, ActorBoardcast -- 3.0 s
    # apart. Proven on dispatched bytes: five actions in pinned order, the five
    # nested payloads identical byte for byte (empty speaker by policy, one
    # sha256), the five 56-byte PCs differing in exactly the two bytes pc[16:18],
    # all ten per-channel hashes matching the scenario pins, ten frames for two
    # requests with no accumulated state, the database file byte-identical across
    # accepted and refused windows, and every fail-closed family silent with a
    # named event. The ledger does NOT grow: HYP-PF-019 is amended in place,
    # tracked_versions CHAT-CHANNEL-002 -> +CHAT-CHANNEL-003, count stays 26.
    # Note: tests/test_channel_message_hypothesis.py's containment test, which
    # asserted that NO runtime module imports the lane, was deliberately rewritten
    # in the same commit -- that assertion is precisely what this milestone had to
    # break. It was not worked around: no hidden id, no derived name, no lazy
    # import. The rewritten guard pins an exact importer list (app.py, runtime.py),
    # keeps connection.py/scenario.py clean, and requires every runtime mention to
    # sit inside the scenario gate. tests/test_presentation_ownership.py needed no
    # change: its chat-vital allowlist already covered both modules from round 76.
    # Previous pin CB3ADB10..F404 (round 76) covered two deliberate movements.
    # Unlike round 75 these are NOT both report-only: the ledger moves 25 -> 26.
    #  1. character_management/stats_and_progression not_started -> in_progress
    #     with STATS-PROG-001 (report-only static). evidence_ref
    #     reports/PF_STATS_PROG001_CHARACTER_STATS_AND_PROGRESSION_STATIC_20260818.md
    #     and test_ref tests/test_stats_progression_static.py. Fourteen attribute
    #     classes, every id derived from its in-image name literal by
    #     PF-NAMEID-HASH-001 and anchored on the three the delivered V141 snapshot
    #     already hardcodes (ActorAttr 0x12AD, NPCAttr 0x0AD5, UpdateAttrVital
    #     0x309A). Nineteen progression fields are named with an in-binary consumer
    #     each -- level BasicAttr u16 +0x5E (GetLv 0x460050), experience ActorAttr
    #     qword +0xA0 (XP bar 0x519299), the five ability u16 at +0x82..+0x8A and
    #     their bonuses at +0x182..+0x18A (LABEL_STR..PER getters), skill point
    #     +0x7C, unspent points +0x80, class +0x8C, HP/MP pairs on BasicAttr -- all
    #     mask-gated through UpdateAttrVital 0x309A. Five progression verbs pinned,
    #     of which AbilityDepolyAll 0x36AD is proven end to end (UP button ->
    #     pending counter -> five i16 tag 0x0F in STR,CON,DEX,INT,PER order).
    #     Evidenced negatives: the AddExp/AddAbilityPoint/AddSkillPoint script
    #     bindings only broadcast an in-process event through 0x5F9C70 and can grant
    #     nothing; Attribute 0x1306 and FightAttr 0x1285 have no wire fields at all
    #     (serializer slot is a bare ret 8 at 0x515EC0); and the curve numbers are
    #     not in the executable -- only column names and lookup code. Server gap:
    #     fourteen classes, zero ids in V141; nineteen progression fields, two
    #     emitted, zero decoded; five verbs, zero encoders and zero dispatch. Status
    #     is in_progress and NOT runtime_pass: no capture has ever carried a
    #     progression field. The POTENTIAL column-to-offset binding is NOT claimed
    #     (AGILITY<->DEX is cardinality inference, not a byte proof).
    #  2. chat/chat_channels_and_routing gains the CHAT-CHANNEL-002 evidence and
    #     test refs (status already in_progress, unchanged): evidence_refs
    #     reports/PF_CHAT_CHANNEL002_SHARED_SERIALIZER_EMITTER_20260818.md and
    #     scenarios/channel_message_hypothesis_shared_serializer.json, test_ref
    #     tests/test_channel_message_hypothesis.py. This one carries a ledger entry,
    #     HYP-PF-019 (ledger 25 -> 26): the shared serializer 0x65AD40 implemented
    #     both directions over the five channels that share it, with the five ids
    #     derived from the name hash at import rather than transcribed. The decode
    #     is pinned externally, not self-certified -- re-encoding the decoded GT-006
    #     capture reproduces both 34-byte payloads byte-for-byte AND reproduces the
    #     PC/frame sha256 that HYP-PF-014 pinned through a path that never parsed
    #     anything, plus the CHAT-ECHO-002 46/68/79-byte pins. Across all five
    #     channels the composed PC differs in exactly two bytes (pc[16:18] = class
    #     id), re-proving CHAT-CHANNEL-001's channel-id-is-the-selector conclusion on
    #     server-produced bytes. Opt-in only, production_allowed false, no DB write,
    #     not imported by runtime/app/connection/scenario. Whisper 0x556C is rejected
    #     on purpose (third wstring + result byte = different schema). Only 0xAC52
    #     has ever been on this project's wire: the other four channels' pins say
    #     what the bytes would be, NOT that they were observed. GT-016 unblocked.
    #     Note: tests/test_presentation_ownership.py's chat-vital allowlist grew
    #     from two modules to three in the same commit. That was deliberate and was
    #     not avoided -- deriving the id from the hash at import would have kept the
    #     scanner green while leaving the repo asserting something false.
    # Previous pin 70E1668D..48BD (round 75) recorded two deliberate movements, both
    # report-only static characterizations that left the ledger at 25:
    #  1. inventory/use_drop_sell not_started -> in_progress with USE-DROP-SELL-001.
    #     evidence_ref
    #     reports/PF_USE_DROP_SELL001_ITEM_OPERATE_USE_DROP_SELL_STATIC_20260818.md
    #     and test_ref tests/test_use_drop_sell_static.py. Byte-exact from the client
    #     binary: neither use nor sell rides ItemOperate. USE is its own class
    #     UseItemVital (vtable 0xF30950, single registration 0xBEE600 -> id-slot
    #     0x1082030, get-id 0x5BEA50) whose serializer 0x6C0180 emits one qword
    #     (tag 0x32) and nothing else; SELL is the Stall/BlackMarket/ItemMall system,
    #     whose StallOperateVital serializer 0x76A630 is a priced wire. No ItemOperate
    #     producer references any vendor/price string, retiring the sell-N candidate
    #     SPLIT-OPERATE-002 left open. op3's single caller 0x5B9D0C is a dialog
    #     callback (never e8-called; registered via 0x405D40 into dialog+0x12CC) that
    #     fires only on confirm: identity-only, no quantity, destination or
    #     counterparty. Server has no handler for op3, op6 or USE_ITEM_VITAL 0x1F4F,
    #     and the one shop route TradeCmdVital 0x23B5 is buy-only, so status stays
    #     in_progress. Which verb is literally drop/discard/destroy is NOT claimed.
    #  2. chat/chat_channels_and_routing not_started -> in_progress with
    #     CHAT-CHANNEL-001. evidence_ref
    #     reports/PF_CHAT_CHANNEL001_CHANNEL_FAMILY_AND_ROUTING_STATIC_20260818.md
    #     and test_ref tests/test_chat_channel_family_static.py. The seventeen
    #     Channel_*Vital classes register from one contiguous block
    #     0xBF72B0..0xBF74F0 in PF-NAMEID-HASH-001 shape, so every channel id derives
    #     from its in-image name literal; the anchor holds exactly
    #     (Channel_LocalTalkMessageVital = 0xAC52, the id GT-006 captured on the
    #     wire), no id is ever a code immediate once E8/E9 AND 0F 8x rel32 tails are
    #     excluded, and two independent naming routes converge 17/17. Recipient
    #     resolution is decoded: Whisper alone carries a third wstring
    #     (Serialize 0x65AEA0, recipient@+0x50) plus a u8 result code @+0x6C. Five
    #     channels share base serializer 0x65AD40, so the channel identifier IS the
    #     16-bit class id, not a payload selector, and the 34-byte GT-006 payload
    #     parses with zero bytes left over. Server carries no Channel_ token and none
    #     of the seventeen ids: seventeen client-side, one touched, zero decoded. The
    #     original server's fan-out/membership behaviour still needs two concurrent
    #     sessions, so this is NOT runtime_pass.
    # Previous pin C98EB5B8..B58C (rounds 73-74) recorded
    #  0. movement/remote_player_movement_projection not_started -> in_progress
    #     with MOVE-PROJECT-001. evidence_ref
    #     reports/PF_MOVE_PROJECT001_REMOTE_MOVEMENT_PROJECTION_STATIC_20260818.md
    #     and test_ref tests/test_remote_movement_projection_static.py. It
    #     characterizes byte-exact, from the read-only client binary cross-checked
    #     against the read-only server source, the transport a remote actor's
    #     movement projection rides -- MovementAttr 0x2067 inside every remote-actor
    #     entry of the RuntimeRes actor stream: runtime-assigned id wall (name
    #     @0xF0E840, single registration 0xBD9410 -> id-slot 0x10334A8, 0x2067 never
    #     a code immediate, one get-id stub 0x43BBB0), vtable 0xF0D0F8 (+0x2C delta
    #     0x467040, +0x30 apply/merge 0x467130, +0x34 Serial 0x4671C0), the
    #     mask-gated sparse wire schema (submask u8 + identity qword(0x32) + field
    #     mask u8, then per-bit pos vec3/heading f32/mode u8/flags u32(0x26)/three
    #     f32) matching make_remote_movement_attr byte-exact, and the projection
    #     apply/merge that completes a sparse delta against existing projected state
    #     (copies only fields whose target-mask bit is NOT set). Server only ever
    #     emits remote actors of actor_type 4 (CNetNPC): no authentic remote
    #     human-PLAYER capture exists, so status stays in_progress (interest
    #     management, cadence, interpolation uncaptured; not runtime_pass).
    #     Report-only additive: no server behavior changed; ledger stays 25. The
    #     movement domain has no not_started rows left; next_missing_behavior stays
    #     remote_player_movement_projection (first row still short of runtime_pass).
    # Previous pin 0F705C08..C4F8 (round 72) recorded
    # movement/local_player_movement_authority not_started -> in_progress with
    # MOVE-AUTHORITY-001 (TargetPosVital 0x2A90 producer + wire schema, server
    # accepts-as-given gap); E04F22D1..CCE8 (round 71) recorded inventory/stack_merge_and_limit
    # gaining the ITEM-MERGE-001 (HYP-PF-018) evidence/test refs; 594DEB56..DCF5
    # (round 69) recorded split_stack's second evidence set (SPLIT-OPERATE-002;
    # round 70 touched notes prose only so the digest held); 3A78B4B6..A766
    # (round 68) recorded split_stack not_started -> in_progress with
    # SPLIT-OPERATE-001; CF031345..BC3B (round 67) recorded
    # inventory/move_negative_paths isolation (MOVE-ISOLATION-001); 35082475..E228C0
    # (round 66) same_slot_noop blocked -> runtime_pass under HYP-PF-010;
    # 26D752FE..BA9A (round 65) occupied_destination_policy not_started ->
    # in_progress under HYP-PF-017 (ITEM-SWAP-001); see its lineage note before that
    # for round 53's 78558E56..6DC8.
    # 6CF4AE24..4553 is the parent digest, kept rather than dropped: it is the
    # value round R167 recorded, and a re-pin that erases its parent takes the
    # earlier movement's record with it.
    #
    # ROUND g627j0 (LANE-B, 2026-08-26 +07:00) moves this pin ONE more step,
    # and again it is NOT a grade change.  npc_interaction/
    # monster_spawn_and_loot stays in_progress -- no player has seen one byte
    # of MOB-LOOT-001 and it claims nothing on the client -- but the row gains
    # four evidence refs (src/pirateforce_foundation/mob_loot.py,
    # src/pirateforce_foundation/field_drop_tables.py,
    # tools/pf_mine_scene_drop_tables.py, scenarios/combat_loot_001.json) and
    # one test ref (tests/test_mob_loot.py).  Why the refs have to move with
    # the prose: the row's notes said Door 2 was an isolated library with
    # production_allowed false and Door 3 was hypothesis-grade only, and both
    # sentences stopped being the whole truth this round -- there is now a
    # flagless production lane that rolls a dead monster's own drop sets and
    # composes the same derived-bit-0x08 element.  Refs are graded fields, and
    # the lesson round 7ptoku wrote here holds: a prose amendment that leaves
    # the structured refs pointing only at the old lanes hides the new one
    # from any machine reading this file.
    #   R167 / parent EB932A54B4958527BA172D34A81673B6B91AA54A0979372EED3A3525902C65DB
    #
    # ROUND uq2lxw (LANE-B, 2026-08-29 +07:00) moves this pin ONE more step,
    # and again it is NOT a grade change.  npc_interaction/
    # monster_spawn_and_loot stays in_progress -- runtime.py still has no
    # inbound pickup call site (GT-124), so no player has caused one byte of
    # this round to run and nothing here is client-observable -- but the row
    # gains one evidence ref (src/pirateforce_foundation/mob_pickup_persist.py)
    # and one test ref (tests/test_mob_pickup_persist.py).  Why the refs have
    # to move with the prose: the row's notes said the pickup row is still
    # log-only and nothing advances the identity counter, and that stopped
    # being true when chief's STORE-INSERT-001 landed; this round adds the
    # only caller of that write in src/, so a machine reading the structured
    # refs would otherwise see a row whose evidence stops at the log.
    # Parent digest, kept greppable, and labelled with the round that
    # RECORDED it rather than the one replacing it (pf-adversary read the
    # two older lines the other way round, so this one says which is which):
    #   parent 034304EA80D0C8119BC208A8EB1AA5F934F3D8C34AB473223492B7E629E3ABB3, recorded by round g627j0
    #   this pin, recorded by round uq2lxw:
    "DB3F2D0DC76426B0EF93DBF33809E3E0A87AA99FDD1F9D4559371C846238064B"
)



# Two manifest formats exist in reports/.  PIPE is the house format used by 21 of
# the 22 manifests; COLUMNS is a single earlier file whose paths are relative to
# its capture root rather than to the repository.  Both are accepted, but the
# COLUMNS set is pinned so a new report cannot quietly reintroduce the old shape.
MANIFEST_PIPE = re.compile(r"^(?P<path>[^|]+)\|(?P<size>\d+)\|(?P<sha>[0-9A-F]{64})$")
MANIFEST_COLUMNS = re.compile(r"^(?P<sha>[0-9A-F]{64})\s+(?P<size>\d+)\s+(?P<path>\S.*)$")

LEGACY_FORMAT_MANIFESTS = {
    "PF_RELATION_COMPARATOR_RUNTIME_TRACE_20260815.manifest",
}


def grade_subset(document):
    """Every field the matrix grades on, in file order, excluding prose."""
    return [
        (
            domain["id"],
            domain.get("domain_complete"),
            [
                (
                    row["id"],
                    row["status"],
                    row["required"],
                    tuple(row["evidence_refs"]),
                    tuple(row["test_refs"]),
                    row.get("next_missing_behavior"),
                )
                for row in domain["capabilities"]
            ],
        )
        for domain in document["domains"]
    ]


def grade_digest(document):
    payload = json.dumps(grade_subset(document), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def parse_manifest(text, pattern=MANIFEST_PIPE):
    """Return parsed rows, or raise ValueError naming the first bad line."""
    rows = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = pattern.match(line)
        if match is None:
            raise ValueError(f"line {number} does not match the manifest format: {line!r}")
        rows.append((match["path"], int(match["size"]), match["sha"]))
    return rows


def parse_any_manifest(path):
    pattern = MANIFEST_COLUMNS if path.name in LEGACY_FORMAT_MANIFESTS else MANIFEST_PIPE
    return parse_manifest(path.read_text(encoding="utf-8"), pattern)


def modules_mentioning(root, pattern):
    found = []
    for path in sorted(Path(root).glob("*.py")):
        if re.search(pattern, path.read_text(encoding="utf-8")):
            found.append(path.name)
    return found


class FoundationLegacySeamTests(unittest.TestCase):
    """The architectural facts behind every runtime_pass grade."""

    def test_app_pins_exactly_one_frozen_legacy_module(self):
        source = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
        pins = re.findall(r"current/pf_login_game_server_v\d+\.py", source)
        self.assertEqual(pins, [PINNED_LEGACY_MODULE])
        self.assertTrue((ROOT / PINNED_LEGACY_MODULE).is_file())

    def test_app_loads_the_legacy_module_rather_than_importing_a_package(self):
        source = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("load_legacy(", source)
        # A plain import would make the frozen script a build-time dependency and
        # silently change which copy runs.
        self.assertNotIn("import pf_login_game_server", source)

    def test_the_foundation_state_class_subclasses_frozen_v141(self):
        source = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        classes = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == "PersistentGameSessionState"
        ]
        self.assertEqual(len(classes), 1)
        bases = [ast.unparse(base) for base in classes[0].bases]
        self.assertEqual(bases, ["legacy.GameSessionState"])

    def test_dispatch_still_falls_through_to_the_frozen_implementation(self):
        source = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
        # If this ever drops to zero, Foundation stopped relaying legacy actions
        # and every passthrough row in the coverage matrix needs re-grading.
        self.assertGreater(source.count("super().dispatch(parsed)"), 0)

    def test_scenario_modes_are_mutually_exclusive(self):
        for first in range(len(SCENARIO_MODES)):
            for second in range(first + 1, len(SCENARIO_MODES)):
                kwargs = {
                    SCENARIO_MODES[first]: object(),
                    SCENARIO_MODES[second]: object(),
                }
                with self.subTest(modes=(SCENARIO_MODES[first], SCENARIO_MODES[second])):
                    with self.assertRaises(ValueError) as raised:
                        make_state_class(None, None, None, **kwargs)
                    self.assertIn("mutually exclusive", str(raised.exception))

    def test_a_single_mode_is_never_refused_for_being_exclusive(self):
        """The exclusion must reject pairs, not reject scenarios generally.

        Three of the five modes run their own allowlist validator that also
        raises ValueError, so the discriminating signal is the message, not the
        exception type.
        """
        for mode in SCENARIO_MODES:
            with self.subTest(mode=mode):
                try:
                    make_state_class(None, None, None, **{mode: object()})
                except Exception as error:  # noqa: BLE001 - any failure is fine here
                    self.assertNotIn("mutually exclusive", str(error))
                else:
                    self.fail("a bare object cannot produce a usable state class")

    def test_the_visible_launcher_enables_no_scenario_mode(self):
        launcher = (ROOT / "tools" / "run_foundation_visible.ps1").read_text(encoding="utf-8")
        for flag in (
            "--scenario", "--scene-load-scenario", "--population-scenario",
            "--item-move-capture-scenario", "--item-move-hypothesis-scenario",
        ):
            self.assertNotIn(flag, launcher)


class EvidenceManifestTests(unittest.TestCase):
    """Manifests are the only re-checkable link between a claim and bytes."""

    def setUp(self):
        self.manifests = sorted(REPORTS.glob("*.manifest"))

    def test_reports_carry_manifests_at_all(self):
        self.assertGreaterEqual(len(self.manifests), 22)

    def test_every_manifest_line_is_well_formed(self):
        for manifest in self.manifests:
            with self.subTest(manifest=manifest.name):
                rows = parse_any_manifest(manifest)
                self.assertTrue(rows, "an empty manifest pins nothing")
                for path, size, _sha in rows:
                    # Zero is legitimate and load-bearing: an empty stderr file is
                    # itself the evidence for several clean-shutdown claims.
                    self.assertGreaterEqual(size, 0)
                    self.assertNotIn("..", path)

    def test_only_the_recorded_manifests_use_the_older_column_format(self):
        odd = set()
        for manifest in self.manifests:
            try:
                parse_manifest(manifest.read_text(encoding="utf-8"), MANIFEST_PIPE)
            except ValueError:
                odd.add(manifest.name)
        self.assertEqual(odd, LEGACY_FORMAT_MANIFESTS)

    def test_no_manifest_pins_the_same_path_twice(self):
        for manifest in self.manifests:
            with self.subTest(manifest=manifest.name):
                paths = [row[0] for row in parse_any_manifest(manifest)]
                self.assertEqual(len(paths), len(set(paths)))

    def test_every_manifest_belongs_to_a_report_that_exists(self):
        for manifest in self.manifests:
            with self.subTest(manifest=manifest.name):
                self.assertTrue(manifest.with_suffix(".md").is_file())

    def test_the_parser_rejects_a_damaged_manifest(self):
        """A guard that never fails is not a guard."""
        good = "GameClient/capture_x/server.out.txt|12|" + "A" * 64
        self.assertEqual(len(parse_manifest(good)), 1)
        for damaged in (
            "GameClient/capture_x/server.out.txt|12",                      # no sha
            "GameClient/capture_x/server.out.txt|12|" + "A" * 63,          # short sha
            "GameClient/capture_x/server.out.txt|12|" + "a" * 64,          # lowercase
            "GameClient/capture_x/server.out.txt|-1|" + "A" * 64,          # negative
            "GameClient/capture_x/server.out.txt|12|" + "G" * 64,          # non-hex
            "A" * 64 + "  12  server.out.txt",                             # wrong format
        ):
            with self.subTest(damaged=damaged):
                with self.assertRaises(ValueError):
                    parse_manifest(damaged)

    def test_the_column_parser_rejects_a_pipe_line(self):
        good = "A" * 64 + "  12  server.out.txt"
        self.assertEqual(len(parse_manifest(good, MANIFEST_COLUMNS)), 1)
        with self.assertRaises(ValueError):
            parse_manifest(
                "GameClient/capture_x/server.out.txt|12|" + "A" * 64,
                MANIFEST_COLUMNS,
            )


class CoverageProvenanceTests(unittest.TestCase):
    """Ratchets that keep the M13 findings from being reopened quietly."""

    def setUp(self):
        self.document = json.loads(COVERAGE.read_text(encoding="utf-8"))
        self.rows = {
            f"{domain['id']}/{row['id']}": row
            for domain in self.document["domains"]
            for row in domain["capabilities"]
        }

    def test_grade_fields_match_the_pinned_digest(self):
        self.assertEqual(grade_digest(self.document), GRADE_SUBSET_SHA256)

    def test_the_digest_would_notice_a_single_status_change(self):
        mutated = json.loads(COVERAGE.read_text(encoding="utf-8"))
        row = mutated["domains"][0]["capabilities"][0]
        row["status"] = "complete" if row["status"] != "complete" else "blocked"
        self.assertNotEqual(grade_digest(mutated), GRADE_SUBSET_SHA256)

    def test_the_digest_ignores_prose_only_edits(self):
        mutated = json.loads(COVERAGE.read_text(encoding="utf-8"))
        mutated["domains"][0]["capabilities"][0]["notes"] += " (edited)"
        self.assertEqual(grade_digest(mutated), GRADE_SUBSET_SHA256)

    def _manifest_debt(self):
        debt = set()
        for key, row in self.rows.items():
            if row["status"] != "runtime_pass":
                continue
            backed = any(
                (ROOT / ref).with_suffix(".manifest").is_file()
                for ref in row["evidence_refs"]
            )
            if not backed:
                debt.add(key)
        return debt

    def test_manifest_debt_matches_the_recorded_list(self):
        self.assertEqual(self._manifest_debt(), MANIFEST_DEBT_RUNTIME_PASS)

    def test_every_recorded_debt_row_still_exists_and_is_runtime_pass(self):
        for key in MANIFEST_DEBT_RUNTIME_PASS:
            with self.subTest(row=key):
                self.assertIn(key, self.rows)
                self.assertEqual(self.rows[key]["status"], "runtime_pass")

    def test_the_system_message_row_records_its_legacy_ownership(self):
        notes = self.rows["chat/server_system_message"]["notes"]
        self.assertIn("no Foundation module owns it", notes)
        self.assertNotIn("has no offline test", notes)
        self.assertTrue(self.rows["chat/server_system_message"]["test_refs"])

    def test_no_foundation_module_emits_the_legacy_system_message(self):
        self.assertEqual(modules_mentioning(SRC_ROOT, r"ShowMessage"), [])
        legacy = (ROOT / PINNED_LEGACY_MODULE).read_text(encoding="utf-8")
        self.assertIn("V99_SHOW_MESSAGE_LOCAL_SERVER_ONLINE", legacy)

    def test_the_source_scanner_would_notice_a_module_that_emitted_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "clean.py").write_text("nothing to see\n", encoding="utf-8")
            self.assertEqual(modules_mentioning(root, r"ShowMessage"), [])
            (root / "chat.py").write_text("SHOW = legacy.ShowMessage\n", encoding="utf-8")
            self.assertEqual(modules_mentioning(root, r"ShowMessage"), ["chat.py"])


if __name__ == "__main__":
    unittest.main()
