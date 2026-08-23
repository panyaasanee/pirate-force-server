"""Strict verifier for the canonical bounded-hypothesis ledger."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / "docs" / "HYPOTHESIS_LEDGER.json"
# Lineage: 08FD966F.. (HYP-PF-011 append, round 34) -> 276FF122.. (2026-08-17:
# HYP-PF-010 evidence_gap rewritten + GT-002 runtime report appended to
# evidence_refs after the first real-client acceptance, commit b1087bb lineage)
# -> 00142EB6.. (HYP-PF-012 append) -> 2B844F29.. (2026-08-17 round 43:
# HYP-PF-013 ack+socket-close append after the GT-007 echo-only client-layer
# falsification, under the owner's standing pre-approval of 18:2x)
# -> 741C5CE5.. (that append's canonical content) -> 6933C363.. (2026-08-17:
# HYP-PF-014 chat input echo append on the GT-006 wire capture, under the
# owner's standing pre-approval of 18:2x) -> 6C16037F.. (2026-08-18:
# HYP-PF-015 soft delete + slot reuse append on the DELETE-003 static decode,
# under the owner's explicit Lane-1 Option-B decision of 2026-08-18 00:52)
# -> 20AF62F3.. (2026-08-18 chief round 52: attended รอบใหญ่ #2 answers
# processed into three amendments -- PF-013 evidence_gap/decision record the
# GT-008 client-layer falsification of the ack+close shape; PF-014
# evidence_gap/decision/evidence_refs record the GT-009 client acceptance of
# the chat echo; PF-015 transform/gap/decision/refs/tracked_versions open
# DELETE-SOFT-002, the trailing-mask v2 delete ack, after GT-010 confirmed
# the request envelope via the first natural 0x36DB and falsified the v1
# ack live with ErrorData=28317; no entry added or removed, count stays 22).
# -> 56FC5454.. (2026-08-18 chief round 53: PF-014 opens CHAT-ECHO-002, the
# speaker-name wstring variant behind its own opt-in scenario, headless-proven
# the same round per the CHAT-ECHO-002 research; HYP-PF-016 appended --
# logout response-first, mirror-echo of the stored full-form 0x3D4B before
# the unchanged PF-012 ack plus the composed PF-013 close, after GT-008
# falsified the ack+close shape at the client layer; count moves to 23).
# -> 01E19C08.. (2026-08-18 chief round 65: HYP-PF-017 occupied-destination
# swap appended behind the dedicated swap profile, headless-proven the same
# round; count moves to 24) -> 2707A863.. (2026-08-18 chief round 71:
# HYP-PF-018 occupied-destination same-template merge appended behind the
# dedicated merge profile -- generalizing the single original-server-evidenced
# V111 merge capture with the composer pinned to the frozen V141 golden --
# headless-proven the same round per ITEM-MERGE-001; count moves to 25).
# -> CE3CC161.. (2026-08-18 chief round 76: HYP-PF-019 appended -- the
# bidirectional codec for the five channel classes sharing base serializer
# 0x65AD40, behind its own opt-in scenario, on the CHAT-CHANNEL-001 static
# milestone.  Unlike every prior append this one is NOT headless-proven over TCP
# the same round: it is proven offline instead, by re-encoding the decoded GT-006
# capture back to the captured bytes AND to the PC/frame pins an independent lane
# (HYP-PF-014) produced without ever parsing the payload.  Client acceptance is
# established for 0xAC52 only; the other four channels are composed but have
# never been on this project's wire.  Count moves to 26).
# -> 6A3D2465.. (2026-08-18 chief round 77: HYP-PF-019 AMENDED, not appended --
# CHAT-CHANNEL-003 opens the second tracked version, the dispatch hookup the codec
# version deliberately withheld.  transform/scope/ceiling/gap/falsification/
# stop_rule/decision record the sweep behind its own second opt-in file
# scenarios/channel_message_hypothesis_channel_sweep.json and the new
# --channel-message-hypothesis-scenario flag; evidence_refs gain the CHAT-CHANNEL-003
# report, the sweep scenario and tests/test_channel_message_dispatch.py; source_refs
# gain runtime.py and app.py (the lane is imported on purpose now, which is exactly
# what the amended containment test says) and the second scenario file.  The claim
# moves only at the WIRE layer: five frames leave the dispatcher in pinned order with
# byte-identical payloads and a two-byte PC delta.  No client has seen a sweep and this
# lane has NOT been driven over real TCP, unlike CHAT-ECHO-002.  Count stays 26).
# -> E5D94616.. (2026-08-18 chief round 78: HYP-PF-020 APPENDED -- the server-side
# mask-gated ActorAttr progression encoder/decoder plus the nine-frame UpdateAttrVital
# 0x309A sweep that ships it, behind its own opt-in scenario
# scenarios/stats_progression_hypothesis_xp_sweep.json and the new
# --stats-progression-hypothesis-scenario flag, on the STATS-PROG-001 static milestone.
# Appended at the end so every existing entry index stays stable.  Like HYP-PF-019 this
# one is NOT driven over real TCP: it is proven offline -- the generic mask-driven encoder
# reproduces player_wire.make_actor_attr_with_name byte for byte for the baseline field
# set, which is the one ActorAttr projection a real client has already accepted -- and
# through the real dispatcher on a temp database.  NO progression field has ever been seen
# on this project's wire in either direction and no client has seen one of these frames;
# that is GT-017.  Count moves to 27.
# -> EE0C4EFC.. (2026-08-19 DELETE-REFRESH-001: HYP-PF-021 APPENDED -- the
# post-acknowledgement character-list rebuild that answers a committed soft delete
# with a SelectActorVital 0x36EF, behind its own opt-in scenario
# scenarios/delete_refresh_hypothesis_list_rebuild.json and the new
# --delete-refresh-hypothesis-scenario flag, on the UI-REFRESH-001 static milestone.
# Appended at the end so every existing entry index stays stable.  Unlike every prior
# append this one composes NO new wire byte at all: the rebuild frame is the unchanged
# LegacyProjector.character_list projection -- the frame a real client has accepted at
# every login since the first runtime pass -- taken over the post-delete row set, and the
# lane's module only verifies and hash-pins it before the dispatcher may queue it.  What
# is designed is the POLICY (answer a delete with a full list rebuild), which no capture
# has ever shown.  HYP-PF-015 is untouched and still active: its stop rule still forbids a
# list-refresh composition under ITS scenario, and the two scenarios are mutually
# exclusive because they key on the same vital id 0x36DB.  Proven offline through the real
# dispatcher on a temp database; the headless TCP replay
# (tools/pf_delete_refresh001_headless_replay.py) is written and ready but was NOT run --
# the server boot is LOCK-protected.  No client has seen a delete answered by a rebuild;
# that is GT-021.  Count moves to 28.
# -> 7A2BC611.. (2026-08-19 HP-DEATH-002: HYP-PF-022 APPENDED -- emission of the one
# BasicAttr bit the client's death predicate reads and nothing in this repository had
# ever emitted, the f32 death timer at +0x58 (mask bit 0x0080, wire tag 0x2A, gate pin
# 0x4657AE), behind its own opt-in scenario
# scenarios/hp_death_hypothesis_death_sweep.json and the new
# --hp-death-hypothesis-scenario flag, on the HP-DEATH-001 static milestone.  Appended at
# the end so every existing entry index stays stable.  It is a SEPARATE entry rather than
# a second HYP-PF-020 version on purpose: HYP-PF-020's stop rule allows exactly 23 fields
# behind exactly one scenario file, and this lane adds a 24th field, a new wire width, a
# second scenario and a lethal claim with its own falsification.  HYP-PF-020 is untouched
# and still active -- bit 0x0080 stays in its NOT_IMPLEMENTED list, stays out of its field
# tables, and its baseline projection is byte-identical with and without this lane's
# unlock token.  Proven offline: 38 + 21 tests, 66 verifier guards (9 of them byte spans
# against the read-only client image), and the wire replay
# tools/pf_hp_death002_headless_replay.py, which reads the dispatcher's own bytes back
# with an INDEPENDENT tag walker and confirms that exactly one of the four frames carries
# hp_current == 0 together with a positive death timer.  Not driven over TCP; no client has
# ever seen bit 0x0080; that is GT-019.  Count moves to 29.
# -> EE1CE2A2.. (2026-08-19 RUNTIMERES-ENCODER-001: HYP-PF-023 APPENDED -- the
# three-frame spawn-then-kill sweep over the ACTOR-ENTRY carrier of
# GSCN_RunTimeProtocolRes 0x6E9D, behind its own opt-in scenario
# scenarios/runtimeres_death_hypothesis_spawn_then_kill.json and the new
# --runtimeres-death-hypothesis-scenario flag.  Appended at the end so every existing
# entry index stays stable.  It exists because round 85 proved a negative that invalidates
# the route HYP-PF-022 was built on: the UpdateAttrVital handler contains not one dispatch
# of the shape the engine's death chain requires, so that lane can open the local player's
# downed window -- which is exactly what the owner watched happen on her own screen -- and
# can never latch the dead state, spawn CActorTask_Dead or play _F_DIE_000, no matter what
# it sends.  This is therefore a SEPARATE entry and not a second HYP-PF-022 version:
# different carrier (derived change mask bit 0x02 at PC offset 13, the actor-entry
# collection at object +0x1C, not the VitalData sub-object at +0x18), different frame id,
# different arity and a different claim.  HYP-PF-022 is untouched and still active, and
# stays the lane that owns the Main_Dead window.  TWO FACTS ARE LOAD-BEARING AND EASY TO
# GET WRONG.  First, THE TIMER POLARITY IS INVERTED FROM INTUITION: the positive value
# that opens the dying window is the same value that PREVENTS the animation, because the
# two engine predicates differ only in the sign test on the f32 at BasicAttr +0x58, so
# BOTH sides must be sent and in that order.  Second, AN ACTOR CANNOT BE BORN DEAD: an
# unrecognised 64-bit identity takes the spawn path, which never touches the dead-state
# sync, so the sweep needs three frames -- SPAWN, DYING_LATCH, DEATH_TASK -- and killing
# anything requires a second message about an identity the client already knows.  Nothing
# about the envelope is invented: the frames are composed by the frozen V141 serializers,
# and what is DESIGNED is the policy of answering one accepted chat-input frame with this
# sweep, which no capture has ever shown.  Proven offline through the real dispatcher; no
# client has ever seen one of these frames, and no client has ever been observed to play
# the death animation by anything in this project.  That is GT-022.  Count moves to 30.
# -> D69DA821.. (2026-08-19 DEATH-ESCALATE-001: HYP-PF-022 AMENDED, no entry added and no
# entry index moved -- count stays 30).  Three things changed in that one entry.  First, the
# dying_hold profile gains a FOURTH frame, TIMER_ELAPSED, which lowers the f32 at BasicAttr
# +0x58 to a pinned POSITIVE zero (tag 0x2A and four zero bytes) while current HP stays 0, so
# the OTHER engine predicate becomes true: vtable +0x3C = 0x454A70, HP == 0 AND timer <= 0,
# the one CMyActor::Update reads at 0x44E58D before the single OpenWindow of L"Common_Death"
# at 0x44E5C7.  It exists because of a MEASURED NEGATIVE, not a guess: GT-021 held the downed
# window on a real client for over four minutes without escalating, so the client does not
# lower this float by itself.  THE FRAME KEEPS MASK BIT 0x0080 SET ON PURPOSE, because
# BasicAttr::Merge copies a field FORWARD when its bit is clear (0x4656A3), so dropping the
# bit would latch the armed 20.0 forever rather than clear it.  Second, the stop rule is
# CORRECTED: it had said "do not ship a sweep that does not end on a revive frame", which the
# dying_hold profile of DYING-HOLD-001 had already contradicted in the tree, so the rule now
# states the bound that is actually enforced -- ends-alive profiles must end on a restore,
# ends-dead profiles must end on the kill or on one pinned elapsed step that immediately
# follows it, at most one elapsed step, one admissible elapsed value, and the band is
# unreachable without naming the step.  Third, tracked_versions now names all three
# checkpoints (HP-DEATH-002, DYING-HOLD-001, DEATH-ESCALATE-001), which FILLS max_versions:
# a fourth widening of this lane needs a new entry or an extension approval, not a profile.
# ROUND 90 APPEND (HYP-PF-024, DAMAGE-ENCODER-001 + DAMAGE-DISPATCH-001).  Entry 31 is
# ADDED, not an amendment: the two checkpoints of this round open a lane that puts a
# damage NUMBER on the wire, over the CHitResult 0x16F7 carrier inside the VitalData
# collection.  The value that number carries comes from a formula THIS PROJECT WROTE.
# Round 83 proved the client computes no damage at all -- it is a pure display of what
# the server sends -- so there was no original formula inside the image to recover, and
# the owner approved designing one on 2026-08-19 11:45 within a scope of one signed i32
# plus one flag word per target.  Two versions of three are spent on arrival.
# ROUND 91 AMENDMENT (HYP-PF-023, RUNTIMERES-LATCHONLY-001).  No entry added, no entry
# index moved, count stays 31.  The entry gains a SECOND NAMED PROFILE, dying_latch_only,
# behind its own opt-in file: SPAWN, DYING_LATCH, stop.  It exists because of a measurement
# that could not be made rather than a new reading of the image.  GT-022 put a real corpse
# on a real client -- the probe NPC went from standing to flat and stayed there, and the
# owner walked over and photographed it herself -- and could not say WHICH FRAME did it,
# because the photographs sit about one second from the t+6 / t+12 boundary and capture
# latency was never instrumented.  A sweep that stops after the latch answers that with no
# appeal to a clock at all.  Its two frames are the three-frame sweep's first two BYTE FOR
# BYTE, structurally rather than incidentally: the profile's step rows are a SLICE of the
# same plan, so the two cannot drift apart, and that identity is asserted independently by
# the encoder, the verifier and the replay.  The validator is STRICTER for it, not looser --
# no frame may satisfy vt+0x3C, the DEATH_TASK label may not appear, and the sweep must END
# on the latch -- and each profile now carries its OWN unlock token compared by identity, so
# one profile's key opens no byte of the other.  It is TRACKED AS THE THIRD VERSION, which
# FILLS max_versions, and it is counted as a version rather than waved through as a mere
# profile even though every byte it sends is a subset of the pinned frames, because it lets
# the lane end a session in a state no earlier version could produce: an NPC latched dying
# with the death task never opened.  No client has ever been shown one byte of it; that is
# GT-025, queued and not run, and the coverage row stays where it is until then.
# ROUND 95 AMENDMENT (HYP-PF-024, DAMAGE-NPC-TARGET-001).  No entry added, no entry index
# moved, count stays 31.  The damage entry gains a SECOND NAMED PROFILE, npc_target, behind
# its own opt-in file and its own identity-compared unlock token (the same round-91 repair
# HYP-PF-023 got).  It exists because GT-024 answered everything the first profile could ask
# -- the numbers rendered, they were exactly 63 and 379, MISS drew the marker and no number
# -- and left exactly one question it cannot: has the client ever been asked to draw our
# number over an actor that is not the player?  The profile changes two things and nothing
# else: the hit entry's TARGET is the fixed placement identity 0x2001 (the identity the
# HYP-PF-023 death lane already drives; copied with a drift test, never imported) while the
# performer stays the player, because one side must be the player or the visibility filter
# at 0x43FEF0 draws nothing; and the spacing is 15 s so an attended tester can photograph
# every frame (the round-84 lesson).  Both profiles hold the SAME step tuple object, so the
# plan cannot fork.  Whether 0x2001 is in the client's identity map AT RUNTIME is
# deliberately not claimed -- a target the client cannot resolve is skipped silently at
# 0x750D27, and GT-027's meaningful negative is exactly that skip.  This FILLS the entry's
# version budget (3 of 3): the stop rule now says so, and the next widening of the damage
# lane needs a new entry or a scoped approval, not another profile.  The scope sentence
# "never an NPC" is rewritten to name the two profiles, because a scope that contradicts
# the tree is worse than no scope.  No client has ever been shown one byte of the npc
# profile; that is GT-027, queued and not run, and the coverage row stays where it is.
#
# ROUND 96 APPEND (HYP-PF-025, REMOTE-PLAYER-ENCODER-001 + REMOTE-PLAYER-DISPATCH-001).
# Entry 32 is appended -- no earlier entry moved, no earlier index changed -- and the
# canonical content hash below is re-pinned for the same reason every earlier append
# re-pinned it: the pin exists so the ledger cannot drift SILENTLY, not so it can never
# grow.  The entry registers multiplayer chunk 2's first deliverable, the actor_type 2
# (CNetActor, the remote-player branch) visibility probe: five one-entry RuntimeRes
# frames for three synthetic identities in the 0x00A0_xxxx band -- an ActorAttr that
# carries BasicAttr bit 0x0001 (the NAME, the field the name board reads and the field
# no encoder in this tree ever put on the ActorAttr wire), an opaque replayed AvatarAttr
# rebound to probe B and riding LAST so an independent walker can find its boundary, two
# lone-MovementAttr update frames (mask 0x01 then 0x03) for a known identity, and a
# deliberately wrong-class NPCAttr as the negative control, which the proven CNetNPC
# bind gate must drop in silence -- a name over that actor falsifies chunk 1 and stops
# the lane.  The design is OURS: the original server is closed, unpublished and
# unrecoverable, and the entry says so in its first sentence.  Everything is behind one
# opt-in scenario file and an identity-compared wire unlock, production_allowed false,
# one-shot, 15-second spacing (the round-84 camera lesson), pins in three agreeing
# copies (module, scenario, composed bytes) with the avatar-bearing frame skeleton-
# pinned because its tail is per-character database content.  No client has ever been
# shown one byte of actor_type 2; that is the queued attended visibility test, and the
# movement/remote_player_movement_projection coverage row does not move until it runs.
#
# ROUND 97 APPEND (HYP-PF-026, DAMAGE-HP-LINK-001).  Entry 33 is appended -- no earlier
# entry moved, no earlier index changed -- and the canonical content hash below is
# re-pinned for the same reason every earlier append re-pinned it: the pin exists so the
# ledger cannot drift SILENTLY, not so it can never grow.  The entry registers the middle
# piece of the hit -> bleed -> die loop: EIGHT frames behind one opt-in scenario,
# alternating the CHitResult damage frames GT-024 proved on a real screen (-63, the MISS
# control, -379 -- byte-identical to the HYP-PF-024 composer's own output) with ActorAttr
# hp frames GT-019 proved on a real screen (100 -> 37 -> 0 + death timer 20.0, then timer
# 0.0 -- byte-identical to the HYP-PF-022 composer's own output), where the hp values are
# DERIVED by a server-held balance ladder (100, 100, 37, 37, 37, 37, 0, 0) that real
# arithmetic must reproduce on every composition.  The arithmetic and the link are OURS:
# no capture shows damage linked to hit points, and round 83 proved the client never
# subtracts, which is exactly why the server must say both halves itself.  The lane is
# deliberately NARROWER than every neighbour: the dispatcher refuses any selected identity
# other than the canonical smoke identity the pins were computed for, so a tester sees the
# pinned bytes byte for byte or nothing.  One-shot, production_allowed false, no database
# write (hit points have no column and this lane adds none), 15-second spacing (the
# round-84 camera lesson).  No client has ever been shown one byte of this sweep; that is
# the queued attended link test (GT-031), and no coverage row grade moves until it runs.
#
# ROUND 99 APPEND (HYP-PF-027, NPC-HOSTILE-001).  Entry 34 is appended -- no earlier
# entry moved, no earlier index changed -- and the canonical content hash below is
# re-pinned for the same reason every earlier append re-pinned it: the pin exists so the
# ledger cannot drift SILENTLY, not so it can never grow.  The entry registers Door A of
# the round-98 mob-aggro design: make the first Port Royal placement PRESENT as hostile,
# on proven ground only.  ONE actor-entry frame -- the HYP-PF-023 SPAWN for the frozen NPC
# 0x2001, byte-identical to the parent lane's own SPAWN composer except a five-byte
# BasicAttr faction splice (bit 0x0400, u32 value 6, widening the mask 0x030C -> 0x070C) --
# paired with the SCENE-005 player faction 1 recomposed onto the pinned smoke identity's
# StartGame through the frozen faction serializer.  Both halves are required: the arena-v2
# negative proved NPC 6 alone against the constructor-default player 0 is neutral, so a
# half-paired sweep re-runs a proven neutral and answers nothing, and the dispatcher
# refuses it by name.  The faction values are OUR composition -- the pair SCENE-005
# rendered hostile on a real screen -- and the original server's assignment is
# unrecoverable, which is the entry's first nonclaim.  One-shot, production_allowed false,
# no database write (faction has no column and this lane adds none).  No client has ever
# been shown one byte of this profile; that is the queued attended test (GT-032), and no
# coverage row grade moves until it runs.
# ROUND 101 APPEND (HYP-PF-028, LOGOUT-RETURN-SELECT-001).  Entry 35 is appended -- no
# earlier entry moved, no earlier index changed -- and the canonical content hash below is
# re-pinned for the same reason every earlier append re-pinned it.  The entry registers the
# server half of GT-033 variant B: answer a captured LogoutVital with a well-formed
# ReturnSelectServerVital (0x709E) response whose 16-byte body is the client serializer
# 0x5e69f0's own field layout (descriptor 0xf304ec slot2) with every field zero, then the
# unchanged PF-012 ack and PF-013 close.  Round-100 static RE (agent D) proved an echo
# cannot transition the client and named 0x709E the strongest candidate while finding no
# client consumer, so whether the client transitions on 0x709E is undecidable statically
# and is the queued attended A/B (GT-033).  Every tag byte is read from the client; the
# field values default to zero (no client producer), an explicit nonclaim.  One-shot,
# production_allowed false, no database write beyond the session close.  No client has ever
# been shown one byte of this profile; no coverage row grade moves until GT-033 runs.
# ROUND 111 APPEND (HYP-PF-029, NPC-HP-LINK-001/002/003).  Entry 36 is appended -- no earlier
# entry moved, no earlier index changed -- and the canonical content hash below is re-pinned
# for the same reason every earlier append re-pinned it.  The entry registers the first lane in
# this tree that moves a TARGET's hit points: eight GSCN_RunTimeProtocolRes 0x6E9D v4 frames
# alternating the VitalData hit carrier (CHitResult 0x16F7, BASE mask 0x02 at +0x18) with the
# actor-entry target carrier (DERIVED mask 0x02 at +0x1C, actor_type 4) against the frozen Port
# Royal placement identity 0x2001, over a server-held balance ladder 100/100/37/37/37/37/0/0.
# THE ARITHMETIC AND THE LINK ARE OURS; the original server is unrecoverable.  Three tracked
# versions, budget now 3/3: the composer, the runtime.py dispatch branch, and the app.py
# flag-to-branch join that also corrected the scenario file's stale dispatch block.  The same
# append also carries the HYP-PF-024 GT-027 amendment (that test HAS now run) and the
# provenance caveat on the 2026-08-20 attended negative, which is testimony plus screenshots
# and not a re-derivable receipt.  No coverage row grade moves on it.
# -> 39AB04EB.. (2026-08-21 chief round 116, cloud: HYP-PF-030 appended --
# MOVE-AUTHORITY-002, the server-side gate that decides whether a reported
# position may be persisted at all.  It is the first lane here that answers
# with a WITHHELD WRITE instead of bytes: it composes nothing on any path,
# so the gated and ungated sessions return the same action list for the same
# frame and only the character row differs.  Opened under the owner's
# standing gameplay pre-approval; count moves 36 -> 37 and no earlier entry
# is touched.  No coverage row grade moves on it.
# -> 225C4C49.. (2026-08-21, cloud: HYP-PF-031 appended -- LOGOUT-CHAT-PUSH-001,
# the unsolicited chat-triggered push of the frozen HYP-PF-028
# ReturnSelectServerVital.  GT-033 is blocked at the TRIGGER (the attended
# tester cannot click the HOME menu item, so LogoutVital never arrives and the
# request-paired shapes can never fire), and the chat-input trigger is proven
# end to end by HYP-PF-027, so this lane decouples the pinned 0x709E response
# from its request pairing: one accepted ascii12 chat frame pushes it
# unsolicited, exactly once, with no ack, no close, no write and no socket
# action, and a LogoutVital under this scenario is deliberately left
# unanswered so the session asks exactly one question.  Not one content byte
# is new -- the pushed frame is byte-identical to the HYP-PF-028 pins -- and
# what is designed is the DELIVERY POLICY only, an explicit nonclaim.  Count
# moves 37 -> 38 and no earlier entry is touched.  No client has ever been
# shown an unsolicited 0x709E push; that is GT-033 variant C, queued, not
# run, and no coverage row grade moves on it.)
# -> 41D132EF.. (2026-08-21, cloud round 122: GEO-PF-006 appended --
# HOSTILE-NATIVE-001, the GT-034 observation geometry, on the owner's
# explicit decision of 11:04 (+07:00): target 0x201F Tornado Eagle, relocate
# the placement point instead of walking or teleporting.  The read-only
# scene-load player is placed at the frozen bg0001 P30 row +100 X, same Y,
# same Z -- the identical trick the P0 observation point uses -- with
# heading pi from the v141 _heading_to_player convention so the character
# faces the placement.  Same map is established at the strongest level the
# committed data allows (P0 and P30 are rows of the single frozen 115-row
# bg0001/Port Royal table); the numeric scene id, native render, client
# standing position and camera orientation are all explicit nonclaims
# pending the GT-034 attended verdict.  No spawn, no splice, no write, no
# runtime change; count moves 38 -> 39 and no earlier entry is touched.
# No coverage row grade moves on it.)
# -> 2CBF3F72.. (2026-08-23, cloud round 123: FOUR evidence_gap AMENDMENTS,
# no entry added or removed, count stays 39, no status/kind/checkpoint moves,
# recording the first attended results delivered against four lanes in the
# overnight big round of 2026-08-22/23 (+07:00), each consumed from the
# tester's own notes in pf_bridge/notes_to_chief/:
# HYP-PF-024 -- GT-038 A/B PASS: the figure renders with AND without target
# selection (red 379 untargeted arm, red 63 plus reaction 63 targeted arm),
# selection is not a necessary condition, exactly the round-102 static
# prediction; HYP-PF-027 -- GT-032 passed earlier (big round 12) and GT-043
# measured that the red outline/target panel surfaces only AFTER Tab-select,
# not from the hostility frame alone; HYP-PF-030 -- GT-041 ran 122 reports,
# zero over budget, so the refusal branch stayed unexercised while last-wire
# -wins persistence proved client-tolerated (relog returns to the last wire
# position, 2187.65 units short of the local-only position); HYP-PF-031 --
# GT-033 variant C delivered the unsolicited 0x709E to a runtime-ready
# client and NOTHING persistent happened, the measured outcome matching the
# round-100 static reading for this state.  Every amendment narrows an
# evidence gap with a measured attended fact and widens nothing; the round's
# adversarial reviewer then tightened two phrasings before commit -- the
# GT-043 blind window is 0-3.524 s of any duration, not "sub-second", and
# the GT-038 boot was HEAD-with-clean-worktree whose green was established
# retroactively through the GT-041 resolver, not a resolver-first boot --
# and the pin is re-pinned so the ledger cannot drift silently, not so it
# can never learn.)
# -> 25C526E2.. (2026-08-23, cloud round 124: HYP-PF-032 appended --
# GROUND-LOOT-001, the GT-045 render probe.  The first attended ground-drop
# evidence ever held (frame measurement 2026-08-23: a loot object stood on
# the ground 0.633 s with a floating label, vanishing in the same frame as
# the green received-item chat line) says the client CAN draw such a thing;
# the only shipped pipe for non-actor world-positioned records is RuntimeRes
# derived bit 0x08 -> the 0x5F85B0 list, whose field table survived the
# GT-042 adversarial re-derive, releasing encoder permission for exactly
# those rows.  The new lane emits TWO pinned single-element frames (near
# +30X and far +800X of the V135 placement) at the first TargetPos after
# runtime ack, once per session, behind --ground-loot-hypothesis-scenario
# only -- one element per frame because V43 measured ErrorData=28317 on a
# combined multi-record derived-mask collection, and the round's adversary
# flagged a count=2 draft as the likeliest way the attended run measures
# the count instead of the rendering -- and claims nothing about rendering:
# that is attended GT-045, and a wire-proven negative at both coordinates
# retires the candidate as a complete answer.)
# -> 22D2BBA0.. (2026-08-23, cloud: HYP-PF-033 appended --
# LEARN-SKILL-RESULT-001, the first server-side encoder for one of the five
# progression verbs.  GT-050 (letter 20260824_0055, jobs 1-3 closed) proved
# the CLearnSkillResultVital 0x673C body shape byte-exactly from the
# read-only client image -- u16 tag 0x12 count, then count 12-byte-stride
# records of (u32 tag 0x14, u16 tag 0x12, u32 tag 0x14), then u8 tag 0x0B at
# object+0x2C; top serializer [0x00756100,0x00756156) sha256 c6a66b70..,
# nested WRITE loop sha256 35eaeb47.., nested READ loop sha256 0c78744e..,
# W/R agreeing -- and this lane implements exactly that shape behind
# --learn-skill-result-hypothesis-scenario: five pinned frames per accepted
# ascii12 chat trigger (count 0/1/3, both trailing values, the count=1 pair
# differing in exactly the one unexplained trailing byte), through the frozen
# v141 make_runtime_vitals envelope.  The record SEMANTICS are unknown and
# deliberately unnamed (opaque triples named by wire position only), the
# trailing u8 meaning is unknown, the version byte 0 is our design, the
# inbound 0x36AA direction is NOT implemented, and no client has ever seen a
# 0x673C frame -- that is the queued attended ticket, and no coverage row
# grade moves on this append.  Count moves 40 -> 41 and no earlier entry is
# touched.)
CANONICAL_CONTENT_SHA256 = "0265A2C8BDFE98EDAB87DB36F3A8785F36D697012A637E72E317C5BEAD638742"
IMMUTABLE_V141_PATH = "current/pf_login_game_server_v141.py"
IMMUTABLE_V141_SHA256 = "2EB05ED2FDBDD5EE3D91F7FBB8C1D16A4C7A02A843BC97169B16A389E4EA4C22"
ANNOTATION_RE = re.compile(
    r"^\s*# PF-HYPOTHESIS-LEDGER: ([A-Z]+-PF-[0-9]{3}) "
    r"(active|frozen|retired|harness_only)\s*$", re.MULTILINE,
)
EXPECTED_IDS = (
    "HYP-PF-001", "HYP-PF-002", "HYP-PF-003", "HYP-PF-004",
    "HYP-PF-005", "HYP-PF-006", "HYP-PF-007", "HYP-PF-008",
    "HYP-PF-009", "HYP-PF-010",
    "DIAG-PF-001",
    "RET-PF-001", "GEO-PF-001", "GEO-PF-002", "GEO-PF-003",
    "GEO-PF-004", "GEO-PF-005",
    # HYP-PF-011 is appended after the geometry block on purpose: the ledger
    # list order is canonical, and appending keeps every existing entry index
    # stable for the index-based test fixtures (the round-31 lesson).
    "HYP-PF-011",
    # HYP-PF-012 (acknowledged logout, owner option A 2026-08-17 18:35) is
    # likewise appended so all prior entry indices stay stable.
    "HYP-PF-012",
    # HYP-PF-013 (ack + server-initiated clean socket close, chief round 43
    # under the owner's standing pre-approval of 2026-08-17 18:2x, after the
    # GT-007 echo-only client-layer falsification) is likewise appended.
    "HYP-PF-013",
    # HYP-PF-014 (designed echo-ack for the chat input frame UNKNOWN_0xAC52,
    # on the GT-006 grade-B wire capture, under the owner's standing
    # pre-approval of 2026-08-17 18:2x) is likewise appended.
    "HYP-PF-014",
    # HYP-PF-015 (soft delete via DeleteActorVital + migration-004 partial
    # unique indexes for genuine slot reuse, on the DELETE-003 grade-A static
    # decode, under the owner's explicit Lane-1 Option-B decision of
    # 2026-08-18 00:52) is likewise appended.
    "HYP-PF-015",
    # HYP-PF-016 (response-first logout: echo the stored client-sent
    # GetWorldInfoVital 0x3D4B payload before the unchanged PF-012 ack and
    # PF-013 close, after attended GT-008 falsified the bare ack+close shape,
    # on the R40 grade-B payload decode, under the owner's standing
    # pre-approval of 2026-08-17 18:2x) is likewise appended.
    "HYP-PF-016",
    # HYP-PF-017 (occupied-destination swap behind the dedicated swap profile
    # of the item-move opt-in scenario, composed on the ITEM-MOVE-CONSUMER-001
    # grade-A response-apply decode after GT-002 proved the generalized
    # free-slot lane live, under the owner's standing pre-approval of
    # 2026-08-17 18:2x; HYP-PF-010's occupied fail-closure is byte-identical
    # under every other mode) is likewise appended.
    "HYP-PF-017",
    # HYP-PF-018 (occupied-destination same-template stack merge behind the
    # dedicated merge profile of the item-move opt-in scenario, generalizing
    # the single original-server-evidenced V111 merge capture -- the one
    # occupied-destination behavior the real server is known to have answered
    # -- with the composer pinned byte-for-byte to the frozen V141 golden for
    # the exact captured case, under the owner's standing pre-approval of
    # 2026-08-17 18:2x; HYP-PF-010's occupied fail-closure and HYP-PF-017's
    # swap stay byte-identical under their own modes) is likewise appended.
    "HYP-PF-018",
    # HYP-PF-019 (bidirectional codec plus designed server-originated composition
    # for the five channel classes that share the base serializer 0x65AD40,
    # behind its own channel-message opt-in scenario, under the owner's standing
    # pre-approval of 2026-08-17 18:2x, on the CHAT-CHANNEL-001 static milestone)
    # is likewise appended.  It reads the same 0xAC52 bytes HYP-PF-014 treats as
    # an opaque blob; HYP-PF-014 is left untouched and still active, and the two
    # lanes agreeing byte-for-byte where they overlap IS the evidence the parse
    # is correct.
    "HYP-PF-019",
    # HYP-PF-020 (server-side mask-gated ActorAttr progression encoder behind the
    # UpdateAttrVital 0x309A delta pipe, with its own stats-progression opt-in
    # scenario, under the owner's standing pre-approval of 2026-08-17 18:2x, on the
    # STATS-PROG-001 static milestone) is likewise appended.  It emits fields
    # STATS-PROG-001 named and nothing else: none of the five progression VERBS has
    # an encoder or a dispatch branch here, so that milestone's "5 verbs, 0
    # encoders" statement and its src/ guard stay literally true.
    "HYP-PF-020",
    # HYP-PF-021 (DELETE-REFRESH-001: answer one accepted op-1 delete with the
    # unchanged pinned HYP-PF-015 echo ack AND, 0.35 s later, the unchanged
    # runtime-proven character-list projection over the post-delete row set,
    # behind its own delete-refresh opt-in scenario, under the owner's standing
    # pre-approval of 2026-08-17 18:2x, on the UI-REFRESH-001 static milestone)
    # is likewise appended at the end so every existing entry index stays
    # stable.  It composes no new wire byte -- the rebuild frame is an
    # already-client-accepted projection over a different set of rows -- and it
    # leaves HYP-PF-015 completely untouched: that lane's stop rule still
    # forbids a list-refresh composition under ITS scenario, and the two
    # scenarios are mutually exclusive because they key on the same vital id.
    "HYP-PF-021",
    # HYP-PF-022 (HP-DEATH-002: emit BasicAttr mask bit 0x0080, the f32 death
    # timer at +0x58 that the client's IsDead predicate 0x454AC0 gates on,
    # alongside the already-emitted current-HP bit 0x0004 set to zero, behind
    # its own hp-death opt-in scenario, under the owner's standing pre-approval
    # of 2026-08-17 18:2x, on the HP-DEATH-001 static milestone) is likewise
    # appended at the end so every existing entry index stays stable.  It rides
    # HYP-PF-020's encoder but is deliberately NOT a second version of it: that
    # entry's stop rule allows 23 fields behind one scenario file, and bit
    # 0x0080 stays in its NOT_IMPLEMENTED list and out of its field tables, so
    # the progression lane's own statements stay literally true and its
    # baseline projection is byte-identical with and without this lane's
    # unlock token.
    "HYP-PF-022",
    # HYP-PF-023 (RUNTIMERES-ENCODER-001: answer one accepted chat-input frame
    # with a three-frame SPAWN / DYING_LATCH / DEATH_TASK sweep for ONE identity
    # over the actor-entry carrier of GSCN_RunTimeProtocolRes 0x6E9D, behind its
    # own runtimeres-death opt-in scenario, under the owner's standing
    # pre-approval of 2026-08-17 18:2x, on the RUNTIMERES-ACTOR-ENTRY-001 static
    # milestone) is likewise appended at the end so every existing entry index
    # stays stable.  It is NOT a second version of HYP-PF-022: round 85 proved
    # that the UpdateAttrVital pipe that entry rides cannot reach the engine's
    # death chain at all, so this lane uses a different carrier, a different
    # frame id and a different arity to make a claim that one cannot make.
    # HYP-PF-022 is untouched and still active as the lane that owns the local
    # player's Main_Dead window, which is the half a human has actually seen.
    "HYP-PF-023",
    # HYP-PF-024 (our own damage model on the CHitResult 0x16F7 carrier,
    # under the owner's explicit "way 1" decision of 2026-08-19 11:45) is
    # likewise appended at the end so every existing entry index stays
    # stable.  It rides the VitalData collection (BASE change mask 0x02,
    # object +0x18), which is a DIFFERENT collection from the actor-entry
    # one HYP-PF-023 uses (DERIVED mask 0x02, object +0x1C) despite the
    # matching bit number, and it makes a claim about a NUMBER rather than
    # about a state: the client computes no damage of its own, so the value
    # it displays is whatever the server sent, and the formula behind that
    # value is this project's own design and not a recovered one.
    "HYP-PF-024",
    # HYP-PF-025 (multiplayer chunk 2: the first actor_type 2 / CNetActor
    # frames in this tree, the remote-player visibility probe) is appended so
    # every existing entry index stays stable.  Like HYP-PF-024 it is a
    # DESIGNED value: the original server is unrecoverable and no corpus
    # holds a remote-human-player capture, so the entry's first nonclaim is
    # that this is our design, checked against our client, not a recovery.
    "HYP-PF-025",
    # HYP-PF-026 (the hit -> bleed -> die link: our own damage arithmetic
    # applied to a server-held HP balance, told to the client over the two
    # carriers GT-024 and GT-019 already proved on a real screen) is appended
    # so every existing entry index stays stable.  Like its two parent lanes
    # it is a DESIGNED value: no capture links damage to hit points in either
    # direction and the client provably never subtracts (round 83), so the
    # entry's first nonclaim is that the link is ours, not a recovery.
    "HYP-PF-026",
    # HYP-PF-027 (NPC-HOSTILE-001, the mob-aggro Door A checkpoint: make the
    # first Port Royal placement PRESENT as hostile by pairing the SCENE-005
    # player faction 1 on the StartGame entry with a five-byte BasicAttr
    # faction splice, bit 0x0400 value 6, on the proven HYP-PF-023 spawn) is
    # appended so every existing entry index stays stable.  Both faction
    # values are OUR composition -- the pair a real client rendered hostile
    # in SCENE-005 -- and the original server's faction assignment is
    # unrecoverable, which is the entry's first nonclaim.
    "HYP-PF-027",
    # HYP-PF-028 (return-select-server logout response, chief round 101 under
    # the owner's standing pre-approval, GT-033 variant B) is likewise
    # appended so all prior entry indices stay stable.
    "HYP-PF-028",
    # HYP-PF-029 (the NPC target hit-point link, chief round 111 under the
    # owner's standing damage-model approval of 2026-08-19 11:45) is appended
    # for the same reason every entry since HYP-PF-011 was: appending keeps
    # every earlier entry index stable for the index-based fixtures.
    "HYP-PF-029",
    # HYP-PF-030 (the server-side movement-authority gate, chief round 116 on
    # the cloud, under the owner's standing gameplay pre-approval) is appended
    # for the same reason: appending keeps every earlier entry index stable.
    # It is the first entry in this ledger whose lane composes no bytes at all
    # -- it can only WITHHOLD a durable write -- so nothing downstream of it
    # reads a frame pin.
    "HYP-PF-030",
    # HYP-PF-031 (LOGOUT-CHAT-PUSH-001: the unsolicited chat-triggered push
    # of the frozen HYP-PF-028 ReturnSelectServerVital, opened on the GT-033
    # trigger blocker under the owner's standing gameplay pre-approval) is
    # appended for the same reason: appending keeps every earlier entry index
    # stable.  It composes no new byte -- the pushed frame is byte-identical
    # to the HYP-PF-028 pins -- and what is designed is the delivery policy
    # only, which no capture has ever shown.
    "HYP-PF-031",
    # GEO-PF-006 (HOSTILE-NATIVE-001: the GT-034 observation geometry --
    # read-only scene-load player at bg0001 P30 "Tornado Eagle" +100X, same
    # Y, same Z, heading pi toward the placement -- opened on the owner's
    # explicit GT-034 decision of 2026-08-21 11:04) is appended after the
    # HYP block, out of GEO numeric adjacency, for the same reason every
    # entry since HYP-PF-011 was: appending keeps every earlier entry index
    # stable for the index-based fixtures.
    "GEO-PF-006",
    # HYP-PF-032 (GROUND-LOOT-001: the GT-045 bit-0x08 render probe -- two
    # pinned single-element RuntimeRes derived-bit-0x08 frames of re-derived
    # 0x5F85B0 shape at scene load, near and far of the V135 placement,
    # behind --ground-loot-hypothesis-scenario only.  Whether the client
    # draws anything for that list is the attended question; no capture has
    # ever shown the original server using this bit.)  Appended at the end,
    # after GEO-PF-006, to keep every earlier entry index stable for the
    # index-based fixtures.
    "HYP-PF-032",
    # HYP-PF-033 (LEARN-SKILL-RESULT-001: the CLearnSkillResultVital 0x673C
    # encoder lane -- five pinned frames of the GT-050-proven body shape
    # behind --learn-skill-result-hypothesis-scenario, record semantics
    # unknown and unnamed, inbound 0x36AA not implemented, no client has
    # ever seen one).  Appended at the end to keep every earlier entry index
    # stable for the index-based fixtures.
    "HYP-PF-033",
)
EXPECTED_META = {
    "HYP-PF-001": ("protocol_hypothesis", "SCENE-005", "frozen"),
    "HYP-PF-002": ("protocol_hypothesis", "SCENE-007", "frozen"),
    "HYP-PF-003": ("protocol_hypothesis", "V134", "expired_pending_decision"),
    "HYP-PF-004": ("protocol_hypothesis", "V136", "expired_pending_decision"),
    "HYP-PF-005": ("protocol_hypothesis", "V137", "expired_pending_decision"),
    "HYP-PF-006": ("protocol_hypothesis", "V138", "expired_pending_decision"),
    "HYP-PF-007": ("protocol_hypothesis", "SCENE-001", "expired_pending_decision"),
    "HYP-PF-008": ("protocol_hypothesis", "ITEM-MOVE-HYP-001", "active"),
    "HYP-PF-009": (
        "protocol_hypothesis", "SECOND-PASSWORD-BYPASS-001", "active",
    ),
    "HYP-PF-010": ("protocol_hypothesis", "ITEM-MOVE-GEN-001", "active"),
    "DIAG-PF-001": ("diagnostic_value", "SCENE-003", "expired_pending_decision"),
    "RET-PF-001": ("retired_claim", "ARENA-002", "retired"),
    "GEO-PF-001": ("test_geometry", "ARENA-001", "harness_only"),
    "GEO-PF-002": ("test_geometry", "SCENE-002", "expired_pending_decision"),
    "GEO-PF-003": ("test_geometry", "SCENE-007", "expired_pending_decision"),
    "GEO-PF-004": ("test_geometry", "V135", "expired_pending_decision"),
    "GEO-PF-005": ("test_geometry", "V140", "harness_only"),
    "HYP-PF-011": ("protocol_hypothesis", "MULTI-CLIENT-001", "active"),
    "HYP-PF-012": ("protocol_hypothesis", "LOGOUT-ACK-001", "active"),
    "HYP-PF-013": ("protocol_hypothesis", "LOGOUT-CLOSE-001", "active"),
    "HYP-PF-014": ("protocol_hypothesis", "CHAT-ECHO-001", "active"),
    "HYP-PF-015": ("protocol_hypothesis", "DELETE-SOFT-001", "active"),
    "HYP-PF-016": ("protocol_hypothesis", "LOGOUT-RESP-001", "active"),
    "HYP-PF-017": ("protocol_hypothesis", "ITEM-SWAP-001", "active"),
    "HYP-PF-018": ("protocol_hypothesis", "ITEM-MERGE-001", "active"),
    "HYP-PF-019": ("protocol_hypothesis", "CHAT-CHANNEL-002", "active"),
    "HYP-PF-020": ("protocol_hypothesis", "STATS-PROG-002", "active"),
    "HYP-PF-021": ("protocol_hypothesis", "DELETE-REFRESH-001", "active"),
    "HYP-PF-022": ("protocol_hypothesis", "HP-DEATH-002", "active"),
    "HYP-PF-023": ("protocol_hypothesis", "RUNTIMERES-ENCODER-001", "active"),
    "HYP-PF-024": ("protocol_hypothesis", "DAMAGE-ENCODER-001", "active"),
    "HYP-PF-025": (
        "protocol_hypothesis", "REMOTE-PLAYER-ENCODER-001", "active",
    ),
    "HYP-PF-026": ("protocol_hypothesis", "DAMAGE-HP-LINK-001", "active"),
    "HYP-PF-027": ("protocol_hypothesis", "NPC-HOSTILE-001", "active"),
    "HYP-PF-028": (
        "protocol_hypothesis", "LOGOUT-RETURN-SELECT-001", "active",
    ),
    "HYP-PF-029": ("protocol_hypothesis", "NPC-HP-LINK-001", "active"),
    "HYP-PF-030": ("protocol_hypothesis", "MOVE-AUTHORITY-002", "active"),
    "HYP-PF-031": (
        "protocol_hypothesis", "LOGOUT-CHAT-PUSH-001", "active",
    ),
    "GEO-PF-006": ("test_geometry", "HOSTILE-NATIVE-001", "harness_only"),
    "HYP-PF-032": ("protocol_hypothesis", "GROUND-LOOT-001", "active"),
    "HYP-PF-033": (
        "protocol_hypothesis", "LEARN-SKILL-RESULT-001", "active",
    ),
}
KINDS = {"protocol_hypothesis", "diagnostic_value", "retired_claim", "test_geometry"}
STATUSES = {"active", "frozen", "retired", "harness_only", "expired_pending_decision"}
COMMON_FIELDS = {
    "id", "kind", "introduced_checkpoint", "exact_value_or_transform", "scope",
    "status", "provenance", "evidence_refs", "accepted_ceiling", "evidence_gap",
    "falsification", "stop_rule", "production_allowed", "expiry", "max_versions",
    "extension_approval_ref", "source_refs",
}


class LedgerError(ValueError):
    """The canonical hypothesis ledger is malformed or has drifted."""


def _exact_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        raise LedgerError(f"{label} fields mismatch; missing={missing}, extra={extra}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LedgerError(f"{label} must be a non-empty string")
    return value


def _string_list(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise LedgerError(f"{label} must be a non-empty list")
    result = tuple(_text(item, f"{label} item") for item in value)
    if len(result) != len(set(result)):
        raise LedgerError(f"{label} contains duplicates")
    return result


def _repo_path(root: Path, raw: Any, label: str) -> Path:
    text = _text(raw, label)
    posix = PurePosixPath(text)
    if posix.is_absolute() or ".." in posix.parts or "\\" in text:
        raise LedgerError(f"{label} must be a safe repo-relative POSIX path")
    path = (root / Path(*posix.parts)).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise LedgerError(f"{label} escapes the repository") from exc
    if not path.is_file():
        raise LedgerError(f"{label} does not exist: {text}")
    return path


@dataclass(frozen=True)
class SourceRef:
    path: str
    required_markers: tuple[str, ...]
    active_claim_marker: bool
    immutable: bool

    @classmethod
    def parse(cls, value: Any, root: Path, label: str) -> "SourceRef":
        if not isinstance(value, dict):
            raise LedgerError(f"{label} must be an object")
        immutable = value.get("immutable") is True
        expected = {"path", "required_markers", "active_claim_marker"}
        if immutable:
            expected |= {"immutable", "sha256", "immutable_anchors"}
        _exact_fields(value, expected, label)
        path_text = _text(value["path"], f"{label}.path")
        path = _repo_path(root, path_text, f"{label}.path")
        markers = _string_list(value["required_markers"], f"{label}.required_markers")
        active = value["active_claim_marker"]
        if type(active) is not bool:
            raise LedgerError(f"{label}.active_claim_marker must be bool")
        try:
            contents = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise LedgerError(f"{label}.path must be UTF-8 text") from exc
        for marker in markers:
            if marker not in contents:
                raise LedgerError(f"{label} marker not found in {path_text}: {marker!r}")
        if immutable:
            if path_text != IMMUTABLE_V141_PATH:
                raise LedgerError(f"{label} immutable exception is not allowlisted")
            if value["sha256"] != IMMUTABLE_V141_SHA256:
                raise LedgerError(f"{label} immutable SHA-256 drift")
            if hashlib.sha256(path.read_bytes()).hexdigest().upper() != IMMUTABLE_V141_SHA256:
                raise LedgerError(f"{label} immutable file hash mismatch")
            anchors = _string_list(value["immutable_anchors"], f"{label}.immutable_anchors")
            for anchor in anchors:
                if contents.count(anchor) != 1:
                    raise LedgerError(f"{label} immutable anchor must occur exactly once: {anchor!r}")
        return cls(path_text, markers, active, immutable)


@dataclass(frozen=True)
class Expiry:
    tracked_versions: tuple[str, ...]
    decision: str

    @classmethod
    def parse(cls, value: Any, label: str) -> "Expiry":
        if not isinstance(value, dict):
            raise LedgerError(f"{label} must be an object")
        _exact_fields(value, {"tracked_versions", "decision"}, label)
        return cls(
            _string_list(value["tracked_versions"], f"{label}.tracked_versions"),
            _text(value["decision"], f"{label}.decision"),
        )


@dataclass(frozen=True)
class Entry:
    id: str
    kind: str
    introduced_checkpoint: str
    status: str
    expiry: Expiry
    source_refs: tuple[SourceRef, ...]
    extension_approval_ref: dict[str, Any] | None

    @classmethod
    def parse(cls, value: Any, root: Path, index: int) -> "Entry":
        label = f"entries[{index}]"
        if not isinstance(value, dict):
            raise LedgerError(f"{label} must be an object")
        kind = value.get("kind")
        expected_fields = COMMON_FIELDS | ({"authentic"} if kind == "test_geometry" else set())
        _exact_fields(value, expected_fields, label)
        ident = _text(value["id"], f"{label}.id")
        kind = _text(kind, f"{label}.kind")
        checkpoint = _text(value["introduced_checkpoint"], f"{label}.introduced_checkpoint")
        status = _text(value["status"], f"{label}.status")
        if kind not in KINDS or status not in STATUSES:
            raise LedgerError(f"{label} has unknown kind/status")
        expected = EXPECTED_META.get(ident)
        if expected is None:
            raise LedgerError(f"unknown hypothesis id: {ident}")
        if (kind, checkpoint, status) != expected:
            raise LedgerError(f"{ident} metadata drift: {(kind, checkpoint, status)!r} != {expected!r}")

        for name in (
            "exact_value_or_transform", "scope", "provenance", "accepted_ceiling",
            "evidence_gap", "falsification", "stop_rule",
        ):
            _text(value[name], f"{label}.{name}")
        evidence_refs = _string_list(value["evidence_refs"], f"{label}.evidence_refs")
        for number, ref in enumerate(evidence_refs):
            _repo_path(root, ref, f"{label}.evidence_refs[{number}]")

        if value["production_allowed"] is not False:
            raise LedgerError(f"{ident} production_allowed must be false")
        max_versions = value["max_versions"]
        if type(max_versions) is not int or max_versions != 3:
            raise LedgerError(f"{ident} max_versions must be exactly 3")
        approval = value["extension_approval_ref"]
        approved_through = None
        if approval is not None:
            if not isinstance(approval, dict):
                raise LedgerError(f"{ident} extension approval must be a scoped object")
            _exact_fields(
                approval, {"approval_id", "approved_entry_ids", "approved_through"},
                f"{label}.extension_approval_ref",
            )
            _text(approval["approval_id"], f"{label}.extension_approval_ref.approval_id")
            approved_ids = _string_list(
                approval["approved_entry_ids"],
                f"{label}.extension_approval_ref.approved_entry_ids",
            )
            if ident not in approved_ids or any(item not in EXPECTED_IDS for item in approved_ids):
                raise LedgerError(f"{ident} approval is not scoped to canonical IDs")
            approved_through = _text(
                approval["approved_through"],
                f"{label}.extension_approval_ref.approved_through",
            )
        expiry = Expiry.parse(value["expiry"], f"{label}.expiry")
        if approval is not None and approved_through != expiry.tracked_versions[-1]:
            raise LedgerError(f"{ident} approval must end at the last tracked checkpoint")
        if len(expiry.tracked_versions) > max_versions:
            if approval is None and status not in {"frozen", "expired_pending_decision"}:
                raise LedgerError(f"{ident} exceeds max_versions but is not expired/frozen")
        elif approval is not None:
            raise LedgerError(f"{ident} has extension approval without exceeding max_versions")

        refs_value = value["source_refs"]
        if not isinstance(refs_value, list) or not refs_value:
            raise LedgerError(f"{label}.source_refs must be a non-empty list")
        refs = tuple(SourceRef.parse(item, root, f"{label}.source_refs[{i}]") for i, item in enumerate(refs_value))
        if len({ref.path for ref in refs}) != len(refs):
            raise LedgerError(f"{ident} source_refs contains duplicate paths")
        if status in {"active", "frozen", "harness_only", "expired_pending_decision"} and not any(ref.active_claim_marker for ref in refs):
            raise LedgerError(f"{ident} requires an active source marker")
        if kind == "retired_claim":
            if status != "retired" or any(ref.active_claim_marker for ref in refs):
                raise LedgerError(f"{ident} retired claim cannot have an active source marker")
            if approval is not None:
                raise LedgerError(f"{ident} retired claim cannot have an extension approval")
        if kind == "test_geometry":
            if value["authentic"] is not False:
                raise LedgerError(f"{ident} geometry authentic must be false")
            if status not in {"harness_only", "expired_pending_decision"}:
                raise LedgerError(f"{ident} geometry must be harness-only or expired")
        return cls(ident, kind, checkpoint, status, expiry, refs, approval)


@dataclass(frozen=True)
class Ledger:
    schema: int
    entries: tuple[Entry, ...]


def _annotation_state(status: str) -> str:
    if status in {"frozen", "expired_pending_decision"}:
        return "frozen"
    return status


def verify_source_annotations(
    entries: tuple[Entry, ...], root: Path, *,
    scan_items: list[tuple[str, str]] | None = None,
    require_complete: bool = True,
) -> None:
    """Bidirectionally bind inline emitter annotations to canonical source refs."""
    declared: dict[tuple[str, str], str] = {}
    for entry in entries:
        expected_state = _annotation_state(entry.status)
        for ref in entry.source_refs:
            if ref.immutable or not ref.path.endswith(".py"):
                continue
            key = (ref.path, entry.id)
            if key in declared:
                raise LedgerError(f"duplicate declared emitter: {key!r}")
            declared[key] = expected_state

    if scan_items is None:
        paths = [*sorted((root / "src").rglob("*.py")), *sorted((root / "scenarios").glob("*.json"))]
        scan_items = [
            (path.relative_to(root).as_posix(), path.read_text(encoding="utf-8"))
            for path in paths if "__pycache__" not in path.parts
        ]
    observed: set[tuple[str, str]] = set()
    for path_text, contents in scan_items:
        for match in ANNOTATION_RE.finditer(contents):
            ident, state = match.groups()
            if ident not in EXPECTED_META:
                raise LedgerError(f"unregistered emitter annotation {ident} in {path_text}")
            key = (path_text, ident)
            if key not in declared:
                raise LedgerError(f"annotation is not declared by source_refs: {key!r}")
            if state != declared[key]:
                raise LedgerError(
                    f"annotation state mismatch for {key!r}: {state!r} != {declared[key]!r}"
                )
            if key in observed:
                raise LedgerError(f"duplicate emitter annotation: {key!r}")
            observed.add(key)
    if require_complete:
        missing = sorted(set(declared) - observed)
        if missing:
            raise LedgerError(f"declared emitter is missing adjacent annotation: {missing!r}")


def load_ledger(path: Path = DEFAULT_LEDGER, *, root: Path = ROOT) -> Ledger:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LedgerError(f"cannot read ledger: {exc}") from exc
    if not isinstance(raw, dict):
        raise LedgerError("ledger root must be an object")
    _exact_fields(raw, {"schema", "policy", "entries"}, "ledger")
    if raw["schema"] != 1 or type(raw["schema"]) is not int:
        raise LedgerError("ledger schema must be integer 1")
    policy = raw["policy"]
    if not isinstance(policy, dict):
        raise LedgerError("policy must be an object")
    _exact_fields(policy, {"max_related_versions", "approval_schema", "policy_text"}, "policy")
    if policy["max_related_versions"] != 3 or type(policy["max_related_versions"]) is not int:
        raise LedgerError("policy max_related_versions must be integer 3")
    approval_schema = policy["approval_schema"]
    if not isinstance(approval_schema, dict):
        raise LedgerError("policy approval_schema must be an object")
    _exact_fields(approval_schema, {"required_fields", "rule"}, "policy.approval_schema")
    if _string_list(approval_schema["required_fields"], "policy.approval_schema.required_fields") != (
        "approval_id", "approved_entry_ids", "approved_through",
    ):
        raise LedgerError("policy approval fields drift")
    _text(approval_schema["rule"], "policy.approval_schema.rule")
    _text(policy["policy_text"], "policy.policy_text")
    values = raw["entries"]
    if not isinstance(values, list):
        raise LedgerError("entries must be a list")
    entries = tuple(Entry.parse(value, root, index) for index, value in enumerate(values))
    ids = tuple(entry.id for entry in entries)
    if len(ids) != len(set(ids)):
        raise LedgerError("duplicate hypothesis id")
    if ids != EXPECTED_IDS:
        raise LedgerError(f"canonical hypothesis inventory drift: {ids!r}")
    verify_source_annotations(entries, root)
    canonical = json.dumps(
        raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    if hashlib.sha256(canonical).hexdigest().upper() != CANONICAL_CONTENT_SHA256:
        raise LedgerError("canonical hypothesis content drift")
    return Ledger(1, entries)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    args = parser.parse_args(argv)
    try:
        ledger = load_ledger(args.ledger)
    except LedgerError as exc:
        parser.error(str(exc))
    print(f"HYPOTHESIS_LEDGER PASS entries={len(ledger.entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
