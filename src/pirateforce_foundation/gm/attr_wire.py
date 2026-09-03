"""Groundwork for GM `/lv` (and future `/item`/`/npc`/`/spawn`-adjacent stat
commands) -> a real `UpdateAttrVital` (0x309A) frame.

STATUS AS OF R294 (`happy-dirac-69cabr`/`focused-turing-69cabr`, 2026-09-01):
this module's own three-point unlock (a/b/c below) is UNCHANGED and the
full-block door (`build_named_field_update`) still refuses every field and
still cannot be reached -- `gm/chat_command_action.py` does not import
`build_named_field_update` and no chat command dispatches into it.  What DID
change: `UPDATE_ATTR_VITAL_VERSION_CONFIRMED` (below) is no longer
unconditionally `None` -- see that constant's own comment for the SCOPED,
temporary exception (`/speed` sparse x=7 only, via `gm/speed_wire.py`, not
this module's named-field API) and why it does not reopen this door.  The
rest of this docstring's history is unchanged, per `COO-DECISION
2026-08-31T16:50+07:00`
(`pf_bridge/notes_to_chief/20260831_1650_COO-DECISION-attr-wire-unlock-
condition-revised-name-all-24-fields-replaced-with-lossless-preserve.md`):
this round's job is to "design and prove the raw-block-per-connection
mechanism ... before asking for a version-confirmation unlock", not to ship
a live send.

## History, briefly (full chain in the round file, not repeated here)

`COO-DECISION 20260831_0146` approved lifting the owner's own ad-hoc
`PF_ADHOC_ATTR_PROBE` experiment (`pf_bridge/notes_to_chief/
reference_adhoc_probe/adhoc_attr_probe.py`, a fork the owner ran live for
266 commands / 2h20m in one connection, no crash) into this lane, with three
hard conditions: (a) always send the FULL block, never a sparse delta
(the client's ActorAttr apply is a bulk copy of the incoming object, not a
merge -- v141 note on 0x464F30, independently confirmed 2026-09-03 by static
RE with the exact same address named: `pf_bridge/notes_to_chief/consumed/
20260903_2149_RE-222-RESULT-PARTIAL-updateattr-and-name-color-gates.md` Q0
traces the full-copy apply to `ActorAttr::full copy [0x00464F30,0x004652AC)`
and its constructors, SHA-pinned; `gm/speed_wire.py`'s own RE-222 comment
block carries the detail); (b) real DB persistence across relog; (c)
normal audit/gate/test discipline. This lane's own round `w8hnu9`-successor
found condition (a) impossible with the only wired encoder that existed
then (`stats_progression_hypothesis.encode_actor_attr`, 23/47 fields), so
`COO-DECISION 20260831_1244` shelved the work pending 24 more named fields.
`COO-DECISION 20260831_1650` then relaxed that: the encoder only has to
cover every NAMED field (this module's 55-row `FIELDS` table below, not a
100%-of-47 bar), and the remaining unnamed fields must be preserved
losslessly from whatever the real current block is -- not zeroed, not
invented. That is the mechanism this module exists to build.
`COO-DECISION 2026-09-01T00:43+07:00` (`pf_bridge/notes_to_chief/
20260901_0043_COO-DECISION-attr-wire-unlock-criteria-replaced-shelve-stays-
locked.md`) ratified this as the standing 3-point unlock definition -- (a)
encoder covers every named field, (b) unnamed fields preserved lossless,
never zeroed, (c) a version-confirmation constant gates the live send, same
shape as `warp`/`say`. That letter does NOT audit this module against the
three points, and neither does this note: (a) and (c) hold at the code
level (`FIELDS` covers every `known=True` row; the gate constant below
mirrors `teleport_wire`/`say_wire`'s pattern exactly), but (b) is NOT yet
true as an outcome -- this module's own "open part" section above already
says the first named-field send will still zero every currently-nonzero
UNNAMED field, because there is no raw-block source to preserve them from
today. ~~Whether that gap is closed by path 1 (accept the risk) or path 2
(name-only, possibly not viable) is still routed to the owner
(`pf_bridge/notes_to_chief/20260831_2327_LANE-GM-TO-OWNER-attr-wire-path1-
vs-path2-after-re172-negative.md`), per `COO-DECISION 20260831_1843`.~~

## (b) IS NOW (b') -- `COO-DECISION 2026-09-04T00:46+07:00`

Struck above, and this is the replacement, not a softening of it
(`pf_bridge/notes_to_chief/20260904_0046_COO-DECISION-lane-gm-2348-
confirmed-the-live-value-source-is-ordered-to-chief-and-unlock-b-is-
revised-after-gt218.md`, item 3).  The old (b) -- "unnamed fields preserved
lossless, never zeroed" -- was a condition NOBODY COULD EVER SATISFY from
this repository: `CORE-REQUEST-GM-044` came back NEGATIVE on 2026-08-31
(`characters.actor_wire` is a `CreateActorDataEx` BLOB, a different codec,
not a DBAttribute collection), so there is no raw-block source to preserve
unnamed fields FROM, and there never was one to wait for.  A gate whose
condition cannot be met is not a gate, it is a shelf.

  (b') EVERY `known=True` ROW CARRIES ITS REAL VALUE AT SEND TIME, read
  from the live-value point `COO-DECISION 2026-09-04T00:47+07:00` ordered
  chief to add: `lane_hooks.current_named_attr_values(character_id) ->
  {x: value}`, covering every `known=True` row of `FIELDS`.  Rows with
  `known=False` are NOT sent -- their mask bits stay unset.

  ~~which is byte-for-byte the shape the owner's own live probe ran for 266
  commands over 2h20m in one connection without a crash~~ -- STRUCK BEFORE
  IT COULD BE INHERITED (pf-adversary, round `3qh50k`).  The 266-commands
  session is real and is this table's provenance (`docs/GM_LANE.md:5540`),
  but no artifact in this repository records WHICH MASK BITS that probe
  set, and `reference_adhoc_probe` appears in exactly two files, neither of
  which says.  So "byte-for-byte the same shape" is unsourced.  It matters
  because the "known=False bits unset" property held for the `GT-218` send
  that killed the client in one frame too: whatever separates them is in
  the known=TRUE bits, which is precisely the fact not written down.  The
  wording came from COO's letter; putting it into source would have made a
  future round read it as settled.  [PROPOSED, load-bearing -- flagged back
  to COO in `20260904_02xx_LANE-GM-ALARM-*`.]

  What can be said without a source: this is the shape (b') defines, and
  the risk COO accepted is named in the next paragraph rather than
  disguised as a measurement.

WHY THE RESIDUAL RISK IS NOW SOMEONE'S TO ACCEPT RATHER THAN NOBODY'S TO
CLOSE.  Under the client's full-object-copy apply (`RE-222` Q0, SHA-pinned,
`ActorAttr::full copy [0x00464F30,0x004652AC)` -- and its constructor zeroes
HP/MP/cash BEFORE decode touches them), an unset mask bit is not "leave it
alone", it is "make it zero".  So (b') trades a guarantee that cannot be
built for one that can: the fields we KNOW keep their true values, and the
fields we do not know take the same trip they demonstrably survived in the
owner's hands.  COO's stated grounds for deciding it without the owner:
it is reversible (a relog rebuilds the row from the DB -- `GT-218` proved
exactly that, the client died in one frame and the row was intact) and it
contradicts no standing owner order.  What remains open is closed ON A
SCREEN, not here: an attended `GT` in which cash / HP-max / MP must be
unchanged after ONE frame.

!! ONE THING (b') DOES NOT COVER, AND IT IS NOT A DETAIL (pf-adversary,
round `3qh50k`, D11 -- [PROPOSED], raised to COO the same round rather than
resolved here).  (b') guarantees the NAMED rows.  x=9 `category_5C`
(BasicAttr +0x5C) is `known=False`, so under (b') its bit stays unset and
the full-object copy ZEROES IT -- and this module's own `SELECTOR_NOTE_R301`
says [PROVEN, in-repo] that +0x5C is the u16 fed to `0x430E10`, whose result
`== 8` is what switches the client from reading HP at x=3/x=4 to reading it
at x=52/x=53.  So one frame can change WHICH HP pair the client displays.
Both pairs are seeded honestly, but for a character outside a category-8
context the honest `alt_hp_current/alt_hp_max` is plausibly `0/0` -- i.e.
HP `0/0` on the HUD after one frame, `GT-218`'s symptom arriving through
the very door (b') was revised to open.  The attended GT's stated criteria
(cash / HP-max / MP unchanged after one frame) would catch this only by
luck.  Nothing in this module sends yet, so nothing is at risk today; the
decision belongs to COO before any GT is written, not to this lane.

PATH 1 AND PATH 2 ARE CLOSED BY THIS, and that is the point of writing it
down: the owner's letter `20260831_2327` had been waiting on her since
31 Aug.  Path 1 ("send sparse and accept the risk") is REFUTED, not chosen
-- `GT-218` is what refutes it: `/speed 400`, a value the login path sends
every day, killed the client in one frame (HP `0/1`, cash `0`) through a
sparse send, so "accept the risk" was priced by measurement and the price
was the session.  Path 2 (name-only) is what (b') is, with the live-value
source that made it viable ordered into existence rather than assumed.

STILL SHUT, AND (b') DOES NOT ON ITS OWN OPEN IT.  Nothing below sends
live: chief's read point does not exist yet (see `seed_cache_from_live_
values`, which refuses by name when it is missing), the version gate is
unflipped for this module's named-field door, and `/speed`'s own two locks
(`SPEED_LOGIN_READ_LANDED`, `SHAPES_CLEARED_BY_A_REAL_CLIENT`) are shut
independently of everything in this file (`COO-DECISION 2147`, standing).

## The proven part

`FIELDS` below reproduces the probe's own 55-row table (12 BasicAttr rows +
43 ActorAttr rows: tag, byte offset, kind, mask bit, name-or-placeholder) --
DATA the owner's live session already exercised byte-for-byte, not logic
copied from that reference (`reference_adhoc_probe/README_WHAT_THIS_IS.md`
rule 2: "if you want to use this for real, rewrite it in your own lane's
zone, with tests -- not copy-paste". This is a rewrite: same numbers,
independently re-derived call shape, this lane's own tests).
`encode_field`/`encode_block`/`make_update_attr_frame` below are new code
built for this module, not the probe's; they happen to produce the same
bytes the probe proved the client accepts, which is the point.

## The open part, stated exactly (this is the "design and prove" COO asked for)

The probe's own module docstring makes a strong claim: "a sparse delta would
zero what it omits" -- i.e. any field whose mask bit is NOT set in a given
`UpdateAttrVital` send does not survive as "unchanged", it becomes 0 on the
client. That claim is STATIC (a read of the v141 client apply routine at
0x464F30), never empirically checked against a real PRE-EXISTING nonzero
value, because every probe session started from a freshly created character
via `ProbeState.reset()` -- there was never a real prior value to check
against. If the claim is right, "preserve unknown fields losslessly"
requires supplying their CURRENT TRUE VALUE on every send, not merely
omitting them.

Where would this module get that value from, for a field it does not know
the name of? Searched before writing this docstring (rule: ค้นก่อนถอด):

  1. `model.Character` (this repo's own server-side character record) has
     NO level/hp/stat fields at all -- `id, account_id, selector, name,
     actor_wire, avatar_wire, identity_lo, identity_hi, position`. There is
     nothing here to read.
  2. `characters.actor_wire` (`migrations/001_initial.sql`) is a real,
     per-character, byte-preserved BLOB -- but it is `CreateActorDataEx`
     (a DIFFERENT vital/codec from `gm/actor_wire.py`, this repo's own
     `Known-safe edits to the otherwise opaque CreateActorDataEx wire`),
     not a standalone ActorAttr/BasicAttr DBAttribute collection. WHETHER
     its embedded sub-structure shares this module's `FIELDS` offsets is an
     open, answerable, static question -- if yes, that BLOB is a ready-made
     raw-block source needing no runtime.py change at all; if no, there is
     no source at all today. NOT ANSWERED HERE -- routed to chief/RE, see
     the round's CORE-REQUEST-GM-044 letter. [สมมติของสาย GM - รอ RE]
  3. No `lane_hooks` point exists today that hands a lane the fields
     `runtime.py`'s login path is about to send for this shape, because
     (per point 1/2) runtime.py does not compose an ActorAttr/BasicAttr
     DBAttribute block at login at all -- there is nothing at that point to
     capture. A CORE-REQUEST asking chief to add one would be asking for a
     hook onto data that provably does not exist yet, so this round does
     NOT open one (would have been last round's first draft of this
     docstring's mistake, caught before writing the letter).

## This round's provisional decision (build now, do not stall)

Per this lane's own rule ("you do not answer questions, you build things --
what you do not know yet, ask; build what you already can"), this module
ships with a decision, tagged for COO confirmation:

  [สมมติของสาย GM - รอ COO ยืนยัน] Until question 2 above is answered, this
  module's public compose entry point (`build_named_field_update`) refuses
  to touch ANY field this table marks `known=False` -- their mask bits are
  NEVER set by this module, in any send, ever. This does not resolve the
  open question (if the probe's "omission = zero" claim is right, the very
  first named-field send this module ever makes will still zero every
  currently-nonzero unnamed field on that character, once, the same way the
  probe's own sessions would have on a non-fresh character) -- it bounds
  the scope of what THIS module claims to have solved to exactly the set
  COO's revised wording named ("every field with a confirmed name/offset"),
  and refuses to guess at the rest. Whether that first-send risk is
  acceptable is a COO/owner call, not this lane's to make alone, and is
  named again in the round letter and CORE-REQUEST-GM-044.

  RawBlockCache (below) is deliberately SOURCE-AGNOSTIC: whichever answer
  question 2 gets, `capture_initial()` takes a plain `{x: value}` dict, so
  this class needs no rewrite once a real source exists -- only a caller
  that seeds it does.

## The one unconditional guarantee this round DOES ship

`build_named_field_update` raises `AttrWireError` -- refuses to compose
anything at all -- for ANY connection whose `RawBlockCache` has never been
seeded via `capture_initial()`. No call site in this lane, this round, ever
calls it. That is what makes "nothing sends yet" true by construction
rather than by convention: there is no path through this module today that
can invent a baseline it was not handed.
"""
from __future__ import annotations

import struct
import sys

AC_ATTR_ID = 0x12AD
UPDATE_ATTR_VITAL_ID = 0x309A
DB_ATTRIBUTE_IDENTITY_BIT = 1
ACTOR_ATTR_EXTRA_GROUP_VALUE = 1

# !! THIS LANE'S SEND GATE FOR 0x309A.  `None` meant: no `UpdateAttrVital`
# frame this module composes may reach a real socket.  Shaped like
# `teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED` /
# `say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED`: an `int` once a real
# vital_version byte is proven AND the raw-block-source question above is
# closed AND COO says the flip is allowed -- three conditions, not one.
#
# !! FLIPPED 0 BY A SCOPED, TEMPORARY EXCEPTION -- NOT BY THE THREE-POINT
# UNLOCK ABOVE, WHICH IS STILL SHUT.  `COO-DECISION 2026-09-01T18:47+07:00`
# (`pf_bridge/notes_to_chief/20260901_1847_COO-DECISION-gm049-vital-version-
# gate-scoped-exception-c.md`) approved exception (ค) for exactly ONE send
# site: the `/speed` sparse x=7 door (`gm/speed_wire.py`'s
# `compose_sparse_speed_update`, reached from
# `chat_command_action._speed_action`). It is NOT a general unblock of this
# module -- the letter says so in as many words ("ไม่ใช่บรรทัดฐานทั่วไปของ
# โมดูล"): conditions (a)/(b)/(c) of the module docstring's "STATUS THIS
# ROUND" three-point unlock still stand for the full-block door and every
# other opcode, unchanged by this line. (b) in particular (lossless
# unnamed-field preservation) is still open, and no chat command dispatches
# into `build_named_field_update` this round -- this flip does not change
# that, because that door does not read this constant to decide anything
# (see `make_update_attr_frame`'s own docstring: "not gated on
# UPDATE_ATTR_VITAL_VERSION_CONFIRMED").
#
# WHY 0, SPECIFICALLY.  The COO-DECISION forbids lifting the byte from
# either `teleport_wire`/`say_wire` alone, since 0x309A is a different
# opcode from both of theirs (0x0E80 / 0x9F2C) and a single borrowed value
# would be a guess dressed as a citation. What this line rests on instead is
# a CONVERGENCE across two independently-measured vitals in the same "GM
# wire" family, not a copy of either:
#   * `gm/state_wire.py`'s `GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED = 0`,
#     RE-105-pinned: the 0x5A19 prototype constructor stores its version
#     byte as a literal 0 (`mov`), and the generic VitalData reader does an
#     exact-equality compare against it.
#   * `gm/teleport_wire.py`'s `FORCE_POS_VITAL_VERSION_CONFIRMED = 0`,
#     RE-129-pinned by the SAME static method (ForcePos's own prototype
#     constructor: `xor ecx,ecx` / `mov byte ptr [eax+0x10],cl`) against the
#     SAME generic reader.
# Two vitals, two independent RE tickets, one shared generic-reader
# mechanism, one answer both times: 0. Nothing here claims that pattern
# proves 0x309A's own byte -- it has never been measured, and RE-105/RE-129
# also measured a THIRD vital (TeleportVital) landing on 4, not 0, so "the
# generic reader always sees 0" is not a rule this line invokes. What
# justifies accepting the risk for this one narrow door is COO-DECISION
# 1847's own reasoning: the failure mode a wrong version byte produces
# (client rejects the frame, reconnect, re-login -- GT-101) is bounded and
# reversible, not silent data corruption, and a real measurement of THIS
# byte is tracked separately and in parallel (a new RE ticket, per the same
# COO-DECISION item 3) rather than being blocked on it.
UPDATE_ATTR_VITAL_VERSION_CONFIRMED: int | None = 0

# x, block, mask_bit, offset, tag, kind, name, known, note
#
# kinds: u8 u16 u32 i32 f32 u64 wstr blob
# `known` mirrors the probe table's own "[รู้]"/"[ไม่รู้]"/"[รู้บางส่วน]"
# tags, collapsed to a bool: True only for a field this lane's own
# `build_named_field_update` is allowed to set a mask bit for (see module
# docstring, "This round's provisional decision"). "[รู้บางส่วน]" rows are
# `known=False` here -- a partial/unconfirmed name is not the same claim as
# a proven one, and this module's refusal gate cares about the stronger
# claim only.
FIELDS = (
    (1,  "basic", 0x0001, 0x028, 0x48, "wstr", "name",            True,  "LABEL_NAME"),
    (2,  "basic", 0x0002, 0x05E, 0x12, "u16",  "level",           True,  "GetLv"),
    (3,  "basic", 0x0004, 0x044, 0x14, "u32",  "hp_current",      True,  "HP bar"),
    (4,  "basic", 0x0008, 0x048, 0x14, "u32",  "hp_max",          True,  ""),
    (5,  "basic", 0x0010, 0x04C, 0x14, "u32",  "mp_current",      True,  ""),
    (6,  "basic", 0x0020, 0x050, 0x14, "u32",  "mp_max",          True,  ""),
    (7,  "basic", 0x0040, 0x054, 0x2A, "f32",  "basic_f32_54",    False, "unknown f32"),
    (8,  "basic", 0x0080, 0x058, 0x2A, "f32",  "death_timer",     True,  "dying countdown f32"),
    (9,  "basic", 0x0100, 0x05C, 0x12, "u16",  "category_5C",     False, "0x430E10(this)==8 swaps HP to x52/53; see SELECTOR_NOTE_R301"),
    (10, "basic", 0x0200, 0x060, 0x32, "u64",  "basic_q60",       False, "unknown"),
    (11, "basic", 0x0400, 0x068, 0x14, "u32",  "basic_faction",   True,  "1 = player side"),
    (12, "basic", 0x0800, 0x06C, 0x14, "u32",  "basic_u32_6C",    False, "unknown"),
    (13, "actor", 1 << 0,  0x08C, 0x19, "u32",  "class_id",        True,  "GetClass"),
    (14, "actor", 1 << 1,  0x090, 0x19, "u32",  "nameboard_key",   False, "partial: NameBoard nickname key"),
    (15, "actor", 1 << 2,  0x078, 0x26, "i32",  "actor_x26_78",    False, "unknown tag 0x26"),
    (16, "actor", 1 << 3,  0x07C, 0x19, "u32",  "skill_points",    True,  "SP"),
    (17, "actor", 1 << 4,  0x080, 0x12, "u16",  "unspent_points",  True,  "unspent stat points"),
    (18, "actor", 1 << 5,  0x082, 0x12, "u16",  "str",             True,  "LABEL_STR"),
    (19, "actor", 1 << 6,  0x084, 0x12, "u16",  "con",             True,  "LABEL_CON"),
    (20, "actor", 1 << 7,  0x086, 0x12, "u16",  "dex",             True,  "LABEL_DEX"),
    (21, "actor", 1 << 8,  0x088, 0x12, "u16",  "int_",            True,  "LABEL_INT"),
    (22, "actor", 1 << 9,  0x08A, 0x12, "u16",  "per",             True,  "LABEL_PER"),
    (23, "actor", 1 << 10, 0x0A0, 0x32, "u64",  "experience",      True,  "XP bar"),
    (24, "actor", 1 << 11, 0x0A8, 0x32, "u64",  "cash",            True,  "GetCash"),
    (25, "actor", 1 << 12, 0x0B0, 0x48, "wstr", "wstr_B0",         False, "unknown text 1"),
    (26, "actor", 1 << 13, 0x099, 0x0B, "u8",   "u8_99",           False, "unknown"),
    (27, "actor", 1 << 14, 0x09A, 0x0B, "u8",   "u8_9A",           False, "unknown"),
    (28, "actor", 1 << 15, 0x13E, 0x12, "u16",  "u16_13E",         False, "unknown"),
    (29, "actor", 1 << 16, 0x13C, 0x12, "u16",  "u16_13C",         False, "unknown"),
    # x=30: SENSITIVE, see SENSITIVE_FIELDS below. Never set via the named-
    # field API even once this field is renamed True by a future RE result.
    (30, "actor", 1 << 17, 0x148, 0x44, "blob", "blob_148",        False, "unknown hex; SEE SENSITIVE_FIELDS"),
    (31, "actor", 1 << 18, 0x182, 0x12, "u16",  "bonus_str",       True,  ""),
    (32, "actor", 1 << 19, 0x184, 0x12, "u16",  "bonus_con",       True,  ""),
    (33, "actor", 1 << 20, 0x186, 0x12, "u16",  "bonus_dex",       True,  ""),
    (34, "actor", 1 << 21, 0x188, 0x12, "u16",  "bonus_int",       True,  ""),
    (35, "actor", 1 << 22, 0x18A, 0x12, "u16",  "bonus_per",       True,  ""),
    (36, "actor", 1 << 23, 0x18C, 0x0B, "u8",   "u8_18C",          False, "unknown"),
    (37, "actor", 1 << 24, 0x164, 0x48, "wstr", "wstr_164_guild",  True,  "-> LABEL_GUILD (probe sent a character name here safely)"),
    (38, "actor", 1 << 25, 0x180, 0x0B, "u8",   "u8_180",          False, "unknown; a [CORPUS, UNVERIFIED] domain is recorded in SELECTOR_NOTE_R301"),
    (39, "actor", 1 << 26, 0x098, 0x0B, "u8",   "u8_98_pairA",     False, "unknown, shares bit with x40"),
    (40, "actor", 1 << 26, 0x094, 0x19, "u32",  "u32_94_pairA",    False, "unknown, shares bit with x39"),
    (41, "actor", 1 << 27, 0x140, 0x32, "u64",  "q_140_pairB",     False, "unknown, shares bit with x42"),
    (42, "actor", 1 << 27, 0x09B, 0x0B, "u8",   "u8_9B_pairB",     False, "unknown, shares bit with x41"),
    (43, "actor", 1 << 28, 0x0CC, 0x48, "wstr", "wstr_CC",         False, "unknown text 2"),
    (44, "actor", 1 << 29, 0x198, 0x32, "u64",  "q_198",           False, "unknown"),
    (45, "actor", 1 << 30, 0x190, 0x32, "u64",  "q_190",           False, "unknown"),
    # Bit 30 -> 32 skips bit 31 (0x80000000) on purpose, not a transcription
    # gap: the mask is a real 64-bit ActorAttr change mask but only 41 of its
    # 64 bits are ever bound to a field, and bit 31 is one of the unused ones
    # -- [PROVEN], pf_bridge/drafts/CHUNK2_Q1_ACTORATTR_MASK_FINDINGS.md:12
    # ("mask 64 บิตนั้น ใช้จริงแค่ 41 บิต (บิต 0..30 และ 32..41; บิต 31 =
    # 0x80000000 ไม่มีฟิลด์ผูก)"). Re-flagged as an open suspicion by
    # pf-adversary round egee8l and closed the same round by re-reading the
    # original probe report rather than re-guessing from this table alone.
    (46, "actor", 1 << 32, 0x1A0, 0x0B, "u8",   "u8_1A0",          False, "unknown"),
    (47, "actor", 1 << 33, 0x1A2, 0x12, "u16",  "u16_1A2",         False, "unknown"),
    (48, "actor", 1 << 34, 0x1A4, 0x12, "u16",  "u16_1A4",         False, "unknown"),
    (49, "actor", 1 << 35, 0x0E8, 0x48, "wstr", "wstr_E8",         False, "unknown text 3"),
    (50, "actor", 1 << 36, 0x104, 0x48, "wstr", "wstr_104",        False, "unknown text 4"),
    (51, "actor", 1 << 37, 0x120, 0x48, "wstr", "wstr_120",        False, "unknown text 5"),
    (52, "actor", 1 << 38, 0x1A8, 0x14, "u32",  "alt_hp_current",  True,  "used when 0x430E10(x9)==8; see SELECTOR_NOTE_R301"),
    (53, "actor", 1 << 39, 0x1AC, 0x14, "u32",  "alt_hp_max",      True,  ""),
    (54, "actor", 1 << 40, 0x1B0, 0x12, "u16",  "u16_1B0",         False, "unknown"),
    (55, "actor", 1 << 41, 0x1B2, 0x0B, "u8",   "u8_1B2",          False, "unknown"),
)
BY_X = {f[0]: f for f in FIELDS}
BY_NAME = {f[6]: f for f in FIELDS}

# -- SELECTOR_NOTE_R301 -----------------------------------------------------
# Trigger: `ka1-B`'s letter 20260901_2215 (items 3, 4, 5) asked this lane to
# rename four rows from the Codex IMAGE corpus and to mark nineteen rows
# known.  NONE of that is done here, and the reason is worth writing down
# once because this lane got it wrong first and had to be refuted:
#
#   The corpus IS mirrored in this repository -- `persistence_attr_compose.
#   _CLIENT_DEFAULT_ROWS` -- but `ClientConstructionDefault`'s own docstring
#   says that table is "One row of the Codex corpus, copied with its
#   provenance attached".  A copy is not a second source.
#
#   This lane's first attempt renamed x=9 to `scene_id`, arguing that seven
#   in-repo modules reach that name independently.  pf-adversary refuted it
#   before commit: those seven are one lineage (R90 section 3.4 -> the
#   stats-progression lane -> modules that say "Copied, not imported"), and
#   this repository's OWN byte-exact sweep retracted the name in writing --
#   `reports/PF_CHUNK2_Q1_ACTORATTR_MASK_FINDINGS_20260819.md`, the note
#   under the BasicAttr table: the bytes only show that +0x5C is a u16 fed
#   into 0x430E10 and compared with 8; the name "scene id/seq" has nothing
#   in the image behind it, is an inherited [GUESS], and must not be carried
#   forward.  That same report's table calls +0x5C `u16 category`, which is
#   what this table already called it.  So: NO RENAMES.  x=9 keeps
#   `category_5C`, x=38 keeps `u8_180`, x=52/53 keep `alt_hp_current`/
#   `alt_hp_max`.
#
# What IS corrected here is one word in two notes.
#
# THE SELECTOR, as far as the bytes actually go [PROVEN, in-repo]:
#   The alternate HP pair is not chosen by comparing x=9 to 8.  x=9's value
#   is passed to the function 0x430E10 and it is that function's RESULT that
#   is compared with 8.  Two independently reported paths do it:
#     * the nameboard updater 0x5BD320 computes it inline --
#       `attr+0x5C -> 0x430E10() == 8 ?` -> HP switches to ActorAttr
#       +0x1A8/+0x1AC, [PROVEN VA=0x5BD3C0..0x5BD3DB]
#       (`PF_CHUNK2_Q1_ACTORATTR_MASK_FINDINGS_20260819.md`, section 7.2);
#     * the HUD updater 0x53F180 and the death predicate both switch on the
#       cached byte [actor+0x358] instead, and the one writer of that byte
#       found by the sweep, 0x4564B3, is `al = (0x430E10(sceneId) == 8)`
#       (`tools/pf_hp_death_respawn_static.py`, the HP-fields section and the
#       one-writer guard).
#   Scope of that writer claim, stated exactly because the tool's own
#   message is narrower than it is tempting to quote: the guard searches ONE
#   instruction encoding (`mov [esi+0x358], al`) in `.text` only.  It does
#   not exclude a write through another register or a different encoding,
#   and +0x358 is class-overloaded -- for the NPC classes the same offset is
#   an Attr pointer (`GetAttr 0x45CD20`), not a selector byte.
#
# WHAT CATEGORY 8 IS: not decoded.  `PF_HP_DEATH001_HP_DEATH_AND_RESPAWN_
# STATIC_20260819.md` says so in as many words ("What category 8 *is* is not
# claimed -- the mapping lives inside 0x430E10 and the external scene data,
# and this milestone did not decode it"), and the CHUNK2 report lists
# "0x430E10 not yet read" as an open question.  So NOTHING here says which
# scene, or which kind of scene, gets the alternate pair.  A note that told
# a tester to go to scene 8 -- or to avoid it -- would be inventing the
# mapping.  ~~An earlier draft of this very block did exactly that.~~
#
# x=38, note only, no rename:
#   The corpus calls x=38 `LABEL_GUILD_FontStyleID_selector` and gives it a
#   domain -- 1..3 -> FontStyleID 64, 4..7 -> 65, 8..9 -> 66, 10 -> 67.
#   [CORPUS, UNVERIFIED] -- single-source, encoded nowhere in this module,
#   and `NOW.md` P-2 forbids hardcoding a FontStyleID in any case.  It is
#   recorded for one reason: the trigger letter reports that an earlier
#   probe table wrote "x38 != 0 turns the orange name purple" -- a TWO-STATE
#   reading of something the corpus gives at least four bands.  That probe
#   table is NOT in this repository and neither the letter nor this lane can
#   locate it, so the rebuttal is [PROPOSED] on both sides: what is recorded
#   is that a two-state reading and a four-band domain cannot both be right,
#   not which one is.
#
# NOT DONE: the letter's item 4, eighteen rows to `known=True` (its list of
# nineteen includes x=30, which `SENSITIVE_FIELDS` forbids outright, so
# eighteen is the real count).  `known` is the ONLY gate deciding which mask
# bits `build_named_field_update` may set, so those flips would widen this
# module's send permission by eighteen fields in one commit on the strength
# of a corpus that still ships open CONFLICTS files.  `RefusedWideningTests`
# pins every one of them.  Asked of COO, not assumed.

# x=30 (ActorAttr +0x148): an UNADJUDICATED Codex checkpoint corpus
# (`pf_bridge/notes_to_chief/reference_codex_attr/`, still carrying open
# "CONFLICTS"/"UNRESOLVED_BUCKETS" files as of this round -- not treated as
# settled fact) names this offset as an MD5 of the account's second
# password plus its account name. Not cross-checked against a second
# source, and `known` above stays False for it either way -- but a
# SECURITY-shaped guess is worth refusing outright rather than merely
# leaving unnamed, in case a future round widens `known` from this same
# unresolved corpus without re-reading this comment first.
SENSITIVE_FIELDS = frozenset({30})


class AttrWireError(ValueError):
    """A `/lv`-family attribute update cannot be composed as given."""


def parse_value(kind: str, text: str):
    if kind in ("u8", "u16", "u32", "u64"):
        value = int(text, 0)
        width = {"u8": 1, "u16": 2, "u32": 4, "u64": 8}[kind]
        if value < 0 or value >= (1 << (8 * width)):
            raise AttrWireError(f"value out of range for {kind}: {text!r}")
        return value
    if kind == "i32":
        value = int(text, 0)
        if value < -(1 << 31) or value >= (1 << 31):
            raise AttrWireError(f"value out of range for i32: {text!r}")
        return value
    if kind == "f32":
        return float(text)
    if kind == "wstr":
        return text
    if kind == "blob":
        return bytes.fromhex(text)
    raise AttrWireError(f"unknown field kind {kind!r}")


_UNSIGNED_LIMITS = {"u8": 0xFF, "u16": 0xFFFF, "u32": 0xFFFFFFFF, "u64": 0xFFFFFFFFFFFFFFFF}

# This lane's own bound on a `wstr` field, NOT a measured client limit --
# see `validate_field_value`'s `wstr` branch for why it exists and what
# would replace it.
WSTR_MAX_CHARS = 512


def validate_field_value(field: tuple, value) -> None:
    """Would `encode_field` accept this value for this row? Raise if not.

    SPLIT OUT OF `encode_field`, WHICH NOW CALLS IT, so there is exactly ONE
    answer to "is this value sendable" in this module.  The seeding path
    (`seed_cache_from_live_values`) has to ask that question BEFORE anything
    is cached, and a second copy of these bounds would be two answers to
    keep in agreement -- the failure mode being a value the seeder blessed
    and the encoder then refused mid-compose, i.e. a `RawBlockCache` holding
    a baseline no send can ever use.

    IT DOES NOT NEED `legacy`, deliberately: the bounds are properties of
    the wire kinds in `FIELDS`, not of the loaded v141 module, so the seeder
    can validate on a connection that has not loaded one.

    The `u*`/`i32`/`wstr` messages are UNCHANGED from the ones `encode_field`
    raised before the split.  `f32` and `blob` gained one each: both used to
    let a bad value out as a bare `TypeError`/`ValueError` from `float()` or
    `bytes()`, which is the one exception class this module's callers do not
    catch by name.
    """
    kind, name = field[5], field[6]
    limit = _UNSIGNED_LIMITS.get(kind)
    if limit is not None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise AttrWireError(f"{name}: {kind} out of range: {value!r}")
        if not (0 <= value <= limit):
            raise AttrWireError(f"{name}: {kind} out of range: {value!r}")
        return
    if kind == "i32":
        if isinstance(value, bool) or not isinstance(value, int):
            raise AttrWireError(f"{name}: i32 out of range: {value!r}")
        if not (-(1 << 31) <= value < (1 << 31)):
            raise AttrWireError(f"{name}: i32 out of range: {value!r}")
        return
    if kind == "f32":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise AttrWireError(f"{name}: f32 requires a real number, got {value!r}")
        # THE MAGNITUDE CHECK, AND IT IS A FIX (pf-adversary, round
        # `3qh50k`, D8, MEASURED end to end).  A type check alone left this
        # function BLESSING `1e40` for x=8 `death_timer` -- the only
        # `known=True` f32 row, so a required row -- while `struct.pack`
        # then raised `OverflowError` mid-compose.  That is verbatim the
        # outcome this function's own docstring promises is impossible: a
        # cache seeded with a baseline no send can ever use.  Worse,
        # `OverflowError` is not a `ValueError`, so `except AttrWireError`
        # misses it entirely.  Asking `struct` itself is the only bound
        # guaranteed to agree with the encoder, because it IS the encoder.
        try:
            struct.pack("<f", float(value))
        except (OverflowError, ValueError) as error:
            raise AttrWireError(
                f"{name}: f32 out of range: {value!r} ({type(error).__name__})"
            ) from None
        return
    if kind == "wstr":
        if not isinstance(value, str):
            raise AttrWireError(f"{name}: wstr requires str, got {value!r}")
        # Same defect, second half: the length prefix is a `<I`, and nothing
        # bounded what went into it.  `WSTR_MAX_CHARS` is this lane's own
        # bound, not a client-derived one -- named as a constant so a future
        # RE result can replace it with a measured limit rather than hunt a
        # literal.  A name is 32 characters in every table this lane has
        # seen; 512 is generous by an order of magnitude and still refuses
        # the 100,000-character string that measured through unchallenged.
        if len(value) > WSTR_MAX_CHARS:
            raise AttrWireError(
                f"{name}: wstr too long: {len(value)} > {WSTR_MAX_CHARS}"
            )
        return
    if kind == "blob":
        if not isinstance(value, (bytes, bytearray)):
            raise AttrWireError(f"{name}: blob requires bytes, got {value!r}")
        return
    raise AttrWireError(f"unknown field kind {kind!r}")  # pragma: no cover - FIELDS-shape guard


def encode_field(legacy, field: tuple, value) -> bytes:
    """One tagged field, using the loaded `pf_login_game_server_v141`
    module's own tag helpers (`legacy_bridge.load_legacy`) -- this module
    does not re-derive `u8tag`/`u16tag`/`u32tag`/`qwordtag`, the same seam
    `gm/state_wire.py`/`gm/bt_gm_probe.py` already use.

    The range/type checks live in `validate_field_value` above, called here
    first so this function and the seeding path can never disagree."""
    validate_field_value(field, value)
    tag, kind = field[4], field[5]
    if kind == "u8":
        return legacy.u8tag(tag, value)
    if kind == "u16":
        return legacy.u16tag(tag, value)
    if kind == "u32":
        return legacy.u32tag(tag, value)
    if kind == "i32":
        return bytes([tag]) + struct.pack("<i", value)
    if kind == "f32":
        return bytes([tag]) + struct.pack("<f", float(value))
    if kind == "u64":
        return legacy.qwordtag(tag, value)
    if kind == "wstr":
        body = value.encode("utf-16le")
        return bytes([tag]) + struct.pack("<I", len(body)) + body
    if kind == "blob":
        raw = bytes(value)
        return bytes([tag]) + struct.pack("<I", len(raw)) + raw
    raise AttrWireError(f"unknown field kind {kind!r}")  # pragma: no cover - FIELDS-shape guard


def encode_block(legacy, identity_lo: int, identity_hi: int, values: dict) -> tuple[bytes, int, int]:
    """`values` (`{x: value}`) -> the DBAttribute body:
    `identity` -> `BasicAttr(mask u16 + fields asc)` -> `ActorAttr(mask u64
    + group flag + fields asc)`.  Only `x` keys present in `values` get a
    mask bit; the caller (`build_named_field_update`) is what enforces the
    `known`/`SENSITIVE_FIELDS` policy -- this function trusts its input,
    the same separation `gm/warp_executor.py` keeps between its parse-time
    catalog hint and its dispatch-time refusal.

    Paired mask bits (x39/x40 share one ActorAttr bit, as does x41/x42) are
    enforced HERE, not upstream: both halves of a pair must be present
    together or neither -- a caller that sets one without the other gets a
    named `AttrWireError`, never a frame with one half silently missing.
    """
    for a, b in ((39, 40), (41, 42)):
        if (a in values) != (b in values):
            raise AttrWireError(
                f"fields {a} and {b} share one mask bit -- set both or neither"
            )
    basic_mask = 0
    basic_body = b""
    actor_mask = 0
    actor_body = b""
    for field in FIELDS:
        x, block, bit = field[0], field[1], field[2]
        if x not in values:
            continue
        encoded = encode_field(legacy, field, values[x])
        if block == "basic":
            basic_mask |= bit
            basic_body += encoded
        else:
            actor_mask |= bit
            actor_body += encoded
    body = (
        legacy.u8tag(0x0B, DB_ATTRIBUTE_IDENTITY_BIT)
        + bytes([0x32])
        + struct.pack("<II", identity_lo & 0xFFFFFFFF, identity_hi & 0xFFFFFFFF)
        + legacy.u16tag(0x12, basic_mask)
        + basic_body
        + legacy.qwordtag(0x32, actor_mask)
        + legacy.u8tag(0x05, ACTOR_ATTR_EXTRA_GROUP_VALUE)
        + actor_body
    )
    return body, basic_mask, actor_mask


def make_update_attr_frame(legacy, identity_lo: int, identity_hi: int, values: dict) -> tuple[bytes, bytes]:
    """Full runtime-vital envelope for one `UpdateAttrVital` (0x309A) send.

    Not gated on `UPDATE_ATTR_VITAL_VERSION_CONFIRMED` -- same separation
    `state_wire.make_gm_update_state_frame` keeps from its own caller-side
    gate: this is a pure byte builder, exercised freely by this module's own
    tests; the gate lives at the one call site allowed to reach a real
    socket, which this round has none of (see module docstring).
    """
    body, _basic_mask, _actor_mask = encode_block(legacy, identity_lo, identity_hi, values)
    payload = (
        legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, AC_ATTR_ID)
        + legacy.u32tag(0x14, len(body))
        + body
    )
    return legacy.make_runtime_vitals(
        [(UPDATE_ATTR_VITAL_ID, 0, payload)]
    )


class RawBlockCache:
    """Per-connection memory of "the last full ActorAttr/BasicAttr block
    this module itself put on the wire for this character" -- deliberately
    SOURCE-AGNOSTIC (see module docstring, "This round's provisional
    decision"): `capture_initial` takes a plain `{x: value}` dict from
    whatever caller eventually seeds it (a decoded `characters.actor_wire`,
    a future runtime.py hand-off, or -- today -- nobody, which is exactly
    why nothing can send yet).

    One instance per connection, held on the session object by whatever
    future dispatch wiring adds it (out of scope this round -- no call site
    constructs one yet outside this module's own tests).
    """

    def __init__(self) -> None:
        self._values: dict[int, object] = {}
        self._captured = False

    def is_captured(self) -> bool:
        return self._captured

    def capture_initial(self, values: dict) -> None:
        """Seed the cache with the connection's real starting values.
        Idempotent by design (a reconnect may call this again) -- the LATEST
        capture always wins, never merged with a stale one."""
        self._values = dict(values)
        self._captured = True

    def current_values(self) -> dict:
        return dict(self._values)

    def merged_with(self, overrides: dict) -> dict:
        if not self._captured:
            raise AttrWireError(
                "RawBlockCache has no captured baseline for this connection "
                "-- refusing to synthesize one (see attr_wire module "
                "docstring, the one unconditional guarantee)"
            )
        merged = dict(self._values)
        merged.update(overrides)
        return merged

    def record_sent(self, values: dict) -> None:
        """Update the cache to exactly what a send just put on the wire --
        called by `build_named_field_update` after a successful compose, so
        the NEXT command in this connection builds on real prior state, not
        a second guess."""
        self._values = dict(values)
        self._captured = True


# The name of chief's live-value read point, ordered by `COO-DECISION
# 2026-09-04T00:47+07:00` and NOT YET BUILT.  Spelled once, here, so the day
# it lands nothing in this lane has to be hunted for -- and so a test can
# pin the name this lane is waiting on without importing a module that does
# not exist.
LIVE_VALUE_READ_POINT = "current_named_attr_values"

# The two console lines the seeding path may print, both pure ASCII (the
# bridge console is cp874).  A refusal is the SHIPPED outcome today -- chief's
# read point does not exist -- so it gets a real line rather than silence:
# "nothing happened" with no console line is the exact shape the owner
# reported as a bug on `/warp`, and this lane does not get to repeat it.
SEED_REFUSED_CONSOLE_TOKEN = "GM_ATTR_SEED_REFUSED"
SEED_CAPTURED_CONSOLE_TOKEN = "GM_ATTR_SEED_CAPTURED"


def named_field_x() -> tuple:
    """Every `x` that (b') says must carry a real value on a send.

    `known=True` MINUS `SENSITIVE_FIELDS`, and the subtraction is not
    currently a no-op by luck: `SENSITIVE_FIELDS` holds x=30, which is
    `known=False` today, so the two sets do not overlap yet.  They would the
    moment an RE result renames x=30 -- and x=30's own row comment says it
    must never be settable through this API "even once this field is renamed
    True".  Doing the subtraction here means that rename cannot quietly turn
    a sensitive blob into a required seed value.
    """
    return tuple(
        field[0] for field in FIELDS if field[7] and field[0] not in SENSITIVE_FIELDS
    )


def live_named_values(character_id, *, hooks=None) -> dict:
    """Read every named field's REAL current value, or raise saying why not.

    THIS IS CONDITION (b') OF THE UNLOCK, in code (see the module docstring's
    "(b) IS NOW (b')" section and `COO-DECISION 20260904_0046` item 3).  It
    returns a dict covering EXACTLY `named_field_x()` -- no more, no fewer --
    read from `lane_hooks.current_named_attr_values(character_id)`.

    EVERY FAILURE IS A NAMED `AttrWireError`, never a partial dict.  Partial
    is the one outcome that must be impossible here: `encode_block` sets a
    mask bit for every key it is given and for no key it is not, and the
    client's apply is a FULL-OBJECT COPY whose constructor zeroes HP, MP and
    cash before decode touches them (`RE-222` Q0, SHA-pinned).  So a dict
    missing `cash` does not send "cash unchanged", it sends "cash = 0" --
    which is not a hypothetical: it is what the owner watched happen in one
    frame during `GT-218` (HP `0/1`, cash `0`).  A missing row must therefore
    cost a refusal, never a send.

    THE HOOK IS RESOLVED LAZILY AND BY NAME.  `lane_hooks` modules import
    this lane's modules, so an import at module scope would close a cycle;
    and the attribute does not exist yet in any case, which is why the
    "missing" branch is the shipped one.  `hooks` is injectable for tests --
    the same seam every other module in this lane uses for a runtime object.
    """
    if hooks is None:
        try:
            from .. import lane_hooks as hooks  # noqa: PLC0415 - see docstring
        except Exception as error:  # noqa: BLE001 - any import failure is a refusal
            raise AttrWireError(
                f"no_read_point: lane_hooks is unimportable "
                f"({type(error).__name__})"
            ) from None
    read_point = getattr(hooks, LIVE_VALUE_READ_POINT, None)
    if not callable(read_point):
        raise AttrWireError(
            f"no_read_point: lane_hooks.{LIVE_VALUE_READ_POINT} does not "
            f"exist yet (ordered by COO-DECISION 20260904_0047)"
        )
    try:
        values = read_point(character_id)
    except Exception as error:  # noqa: BLE001 - a hook may never take dispatch down
        raise AttrWireError(
            f"read_point_raised_{type(error).__name__}"
        ) from None
    if not isinstance(values, dict):
        raise AttrWireError(f"not_a_mapping: read point returned {type(values).__name__}")

    wanted = named_field_x()
    seeded = {}
    absent = []
    unsendable = []
    for x in wanted:
        if x not in values:
            absent.append(x)
            continue
        field = BY_X[x]
        try:
            validate_field_value(field, values[x])
        except AttrWireError:
            # A row that is present but unsendable is exactly as fatal as a
            # row that is absent: both end in a mask bit this module cannot
            # set with a true value.  They are reported apart (D13) because
            # they send an operator to two different places.
            unsendable.append(x)
            continue
        seeded[x] = values[x]
    if absent or unsendable:
        # TWO FACTS, TWO NAMES (pf-adversary, round `3qh50k`, D13).  The
        # first draft filed "the hook did not return this row" and "the hook
        # returned a value this wire cannot carry" under one word, so an
        # operator debugging chief's hook would go looking for an absent key
        # and find it present.
        parts = []
        if absent:
            parts.append("absent=" + ",".join(str(x) for x in absent))
        if unsendable:
            parts.append("unsendable=" + ",".join(str(x) for x in unsendable))
        raise AttrWireError("missing_named_rows: " + " ".join(parts))
    # EXTRA KEYS ARE DROPPED, NOT REFUSED, and dropping is the safe half:
    # a key this module does not send cannot set a mask bit.  An extra key
    # for a `known=False` row would set that row's bit with a value nobody
    # has confirmed the meaning of, and one for x=30 would put
    # `SENSITIVE_FIELDS` on the wire -- `seeded` is built from `wanted`
    # alone, so neither can reach the cache by any input to this function.
    return seeded


def seed_cache_from_live_values(
    cache: RawBlockCache,
    character_id,
    *,
    hooks=None,
    stream=None,
) -> bool:
    """Seed one connection's cache from the live values, or refuse out loud.

    Returns True only when the cache now holds a real, complete named-field
    baseline.  NEVER RAISES: this is the function a future dispatch path
    calls before composing, and this module's founding property is that an
    accepted command never vanishes without a console line.

    ~~TODAY IT ALWAYS RETURNS FALSE~~ -- struck by pf-adversary (round
    `3qh50k`, D12, MEASURED): it returns True in three lines through the
    documented `hooks=` seam, and this module's own tests do exactly that.
    What is true is narrower and worth saying precisely: **on a real boot
    today it always refuses**, because `lane_hooks` has no
    `current_named_attr_values` for the default resolution path to find.

    ~~the refusal path is the one that will run in production first~~ --
    struck by the same finding.  This helper has NO production call site at
    all: nothing in `src/` outside this module names it, so
    `GM_ATTR_SEED_REFUSED` will not print on a boot until a dispatch path
    calls it.  The honest reason to ship it now is smaller: the day chief's
    read point lands, the consumer and its refusals already exist, tested,
    rather than being written in the same hurried round that first has
    something to send.  `COO-DECISION 20260904_0046` item 3's instruction to
    this lane was exactly that -- "prepare the consumer; not landed yet =
    stand still with a console line, no bytes out".

    NO BYTES CAN LEAVE THROUGH HERE UNDER ANY OUTCOME.  This function seeds a
    cache; it does not compose, and it does not send.  What stands between a
    seeded cache and a socket is `build_named_field_update`, which refuses
    every `known=False` row, refuses an unseeded cache, and (since D10)
    refuses a cache that does not satisfy (b') in full.
    ~~and `UPDATE_ATTR_VITAL_VERSION_CONFIRMED` still gates the one exception
    site that may reach a socket~~ -- struck as MISLEADING HERE (D12): that
    constant is real and untouched, but it does not gate THIS path.
    `make_update_attr_frame`'s own docstring says it is "not gated on
    `UPDATE_ATTR_VITAL_VERSION_CONFIRMED`".  So "no bytes leave" on the
    named-field door rests on the door's own refusals and on the ABSENCE of
    a caller -- not on the version gate, and absence of a caller is not a
    gate at all.  Saying so is the point: a future round must not read this
    file as if two gates guard a door that has one.
    """
    if stream is None:
        stream = sys.stderr
    try:
        values = live_named_values(character_id, hooks=hooks)
    except AttrWireError as error:
        _print_seed_line(stream, SEED_REFUSED_CONSOLE_TOKEN, character_id, str(error))
        return False
    except Exception as error:  # noqa: BLE001 - see docstring: never raises
        _print_seed_line(
            stream,
            SEED_REFUSED_CONSOLE_TOKEN,
            character_id,
            f"unexpected_{type(error).__name__}",
        )
        return False
    try:
        cache.capture_initial(values)
    except Exception as error:  # noqa: BLE001 - a cache object may be anything
        _print_seed_line(
            stream,
            SEED_REFUSED_CONSOLE_TOKEN,
            character_id,
            f"capture_failed_{type(error).__name__}",
        )
        return False
    # READ BACK AFTER WRITE, AND READ THE CONTENT, NOT THE FLAG
    # (pf-adversary, round `3qh50k`, D9, MEASURED).  The first draft asked
    # `cache.is_captured()` -- a bool the cache sets itself -- and then
    # printed `named_rows=` from its own local variable.  Measured against a
    # cache whose `capture_initial` stored ONE row: the function returned
    # True and the console said `named_rows=26`.  Both halves compared the
    # answer against the function's own input instead of against the thing
    # claimed ("the cache now holds every named row"), which is the one
    # mistake this house has a scar for.  So the check is the set itself,
    # and the count printed is the CACHE's.
    try:
        held = set(cache.current_values())
    except Exception as error:  # noqa: BLE001 - a cache object may be anything
        _print_seed_line(
            stream,
            SEED_REFUSED_CONSOLE_TOKEN,
            character_id,
            f"cache_not_readable_{type(error).__name__}",
        )
        return False
    if held != set(values):
        _print_seed_line(
            stream, SEED_REFUSED_CONSOLE_TOKEN, character_id, "capture_did_not_hold"
        )
        return False
    _print_seed_line(
        stream,
        SEED_CAPTURED_CONSOLE_TOKEN,
        character_id,
        f"named_rows={len(held)}",
    )
    return True


def _print_seed_line(stream, token: str, character_id, why: str) -> None:
    """One ASCII console line, and never raise printing it."""
    try:
        safe = "".join(
            ch if 32 <= ord(ch) < 127 else "?" for ch in str(why)
        )
        ident = "".join(
            ch if 32 <= ord(ch) < 127 else "?" for ch in str(character_id)
        )
        print(
            f"{token} character_id='{ident}' why='{safe}'",
            file=stream,
        )
    except Exception:  # noqa: BLE001 - a diagnostic may never alter dispatch
        pass


def build_named_field_update(
    legacy, cache: RawBlockCache, identity_lo: int, identity_hi: int, x: int, value,
) -> tuple[bytes, bytes]:
    """The one entry point a future chat-command action should call.

    Refuses, by name, every one of:
      * `x` not in `FIELDS` at all;
      * `x` in `SENSITIVE_FIELDS` (never settable through this API, known or
        not -- see that set's own comment);
      * `x` present but `known=False` (this round's provisional scope
        limit, [สมมติของสาย GM - รอ COO ยืนยัน] -- see module docstring);
      * `cache` never seeded (`RawBlockCache.merged_with` raises).

    On success, updates `cache` to the merged block it just composed (see
    `RawBlockCache.record_sent`) and returns `(pc, frame)` -- NOT sent by
    this function; same posture as `gm/warp_executor.py`/`gm/say_wire.py`,
    a caller sends.
    """
    field = BY_X.get(x)
    if field is None:
        raise AttrWireError(f"unknown field x={x!r} (valid: 1..{len(FIELDS)})")
    if x in SENSITIVE_FIELDS:
        raise AttrWireError(f"field x={x} ({field[6]}) is refused: SENSITIVE_FIELDS")
    if not field[7]:
        raise AttrWireError(
            f"field x={x} ({field[6]}) is not in this round's known-field "
            f"scope -- see attr_wire module docstring 'provisional decision'"
        )
    # (b') IS ENFORCED AT THE DOOR, NOT ONLY IN THE HELPER THAT SEEDS
    # (pf-adversary, round `3qh50k`, D10, and it is the finding that changed
    # this round's shape).  `seed_cache_from_live_values` refuses an
    # incomplete answer -- but `RawBlockCache.capture_initial` is PUBLIC and
    # unvalidated, and `COO-DECISION 20260904_0046` item 2 names TWO
    # consumers of chief's read point: this lane's seeder AND LANE-B's Door
    # B, which was ordered to call `capture_initial()` -- the function the
    # helper does not gate.  A peer lane doing exactly what it was told,
    # with a hook that omits `cash` for a row whose cash is NULL, would
    # compose 25 of 26 bits here and the client's full-object copy would
    # zero the missing one.  That is GT-218's mechanism with the new gate
    # fully installed and looking the other way.
    #
    # So the completeness question is asked HERE, where every consumer must
    # pass, and it is asked of the CACHE rather than of whoever filled it.
    # `merged_with` already refuses an unseeded cache; this refuses a
    # half-seeded one, which is the more dangerous of the two because it
    # composes.
    held = set(cache.current_values())
    wanted = set(named_field_x())
    if held != wanted:
        raise AttrWireError(
            "cache does not satisfy unlock (b'): it holds "
            f"{len(held)} of {len(wanted)} named rows "
            f"(missing={sorted(wanted - held)}, unexpected={sorted(held - wanted)})"
            " -- an unset mask bit is a ZERO on the client, not 'unchanged'"
            " (see the module docstring, section \"(b) IS NOW (b')\")"
        )
    merged = cache.merged_with({x: value})
    pc, frame = make_update_attr_frame(legacy, identity_lo, identity_hi, merged)
    cache.record_sent(merged)
    return pc, frame
