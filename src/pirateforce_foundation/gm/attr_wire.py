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
  to COO in `pf_bridge/notes_to_chief/20260904_0155_LANE-GM-ALARM-b-prime-
  says-nothing-about-the-selector-that-picks-the-hp-pair.md`, answered by
  `COO-DECISION 20260904_0215` below.]

  What can be said without a source: this is the shape (b') defines, and
  the risk COO accepted is named in the next paragraph rather than
  disguised as a measurement.

## (b') IS NOW (b'') -- `COO-DECISION 2026-09-04T02:15+07:00`

Struck above (not deleted), by this lane's own `20260904_0155_LANE-GM-
ALARM-*` and COO's answer to it.  The alarm found what (b') left open: x=9
`category_5C` is `known=False`, so under (b') its mask bit stayed unset --
and the full-object-copy apply (`RE-222` Q0, cited above) makes an unset
bit a ZERO on the client, on every row, not only the ones this module
happens to have named.  So "`known=False` rows are not sent" was never a
smaller version of the `GT-218` frame; it was the SAME frame, row for row,
for every row this lane has not yet named.  pf-adversary caught this in
round `3qh50k` (D11); COO ruled on it, not this lane alone, per `0215`.

  (b'') NO PARTIAL `0x309A` BLOCK EVER LEAVES THROUGH THIS MODULE'S NAMED-
  FIELD DOOR (`build_named_field_update`).  [CORRECTED -- an earlier draft
  of this paragraph said "for any reason" with no qualifier; pf-adversary
  measured that false: `gm/speed_wire.py`'s OWN sparse composer,
  `compose_sparse_speed_update`, still calls this module's byte-level
  `encode_block`/`make_update_attr_frame` with a one-field `{7: value}`
  block, deliberately, and remains reachable at runtime through the
  COO-approved `PF_SPEED_TRIAL` owner-only trial gate (`gm/speed_wire.py`,
  `trial_admits`) -- exactly the GT-218/GT-193 shape, on a live path this
  round did not touch and does not claim to have closed. See that
  function's own docstring for the full scoping and the open question
  raised to COO in this round's letter (`pf_bridge/notes_to_chief/
  20260904_0309_LANE-GM-ALARM-speed-trial-gate-and-encode-block-not-
  covered-by-bdprime.md`).] Every field `FIELDS` lists carries a byte on every
  send THROUGH THE NAMED-FIELD DOOR:
    * `known=True` rows (now including x=9, moved by `COO-DECISION 0215`
      item 2 -- it is not "an unnamed row", it is the proven selector for
      which HP pair the client reads, `SELECTOR_NOTE_R301` below) carry
      their REAL value at send time, from `live_named_values` exactly as
      (b') defined.
    * `known=False` rows (everything else, `SENSITIVE_FIELDS` included --
      see `live_login_bytes`'s own docstring for why x=30 is not an
      exception to THIS half) carry the SAME bytes the login path already
      sends this character today -- the one shape this house has ever
      measured a real client surviving for a row it does not have a name
      for. Not a guess, not a zero: whatever chief's second read point
      (`LOGIN_BYTES_READ_POINT`, ordered `COO-DECISION 0216`, NOT YET
      BUILT) answers for this character's login send.
    * No byte source for ANY row -- named point missing that row, login
      point missing that row, either point unreadable or wrong-shaped --
      refuses the WHOLE block.  There is no such thing as "send what we
      have"; that is exactly the partial send (b') already forbade, widened
      to every row instead of only the unnamed ones.
  `build_named_field_update`'s cache-completeness check enforces this --
  widened this round from `named_field_x()` (b') checked to `all_field_x()`
  -- and that check is deliberately where this lives, NOT inside the
  shared `encode_block` composer. `COO-DECISION 0215`'s own wording named
  `encode_block` for the raise; this module's own measurement found that
  would break a LANE-DB test outside this lane's write zone and this
  lane's own GT-193 shape-pinning suite, both of which pass `encode_block`
  a deliberately partial `values` for reasons unrelated to a live send.
  [ASSUMPTION OF LANE-GM, AWAITING COO] -- see `encode_block`'s own
  docstring for the full reasoning and this round's letter raising it back
  to COO. The guarantee itself is unweakened: `build_named_field_update`
  is the one door a live send can reach through, LANE-B's Door B included
  (it composes via THIS function, per its own docstring -- `capture_
  initial()` alone cannot reach a socket), so nothing in this repository
  can put a partial (b'') block on the wire through this module's named-
  field API, present caller or future one.

  THE SENTENCE THIS TABLE'S PROVENANCE ONCE BORROWED -- "byte-for-byte the
  shape the owner's own live probe ran for 266 commands" -- IS FORMALLY
  WITHDRAWN, per `COO-DECISION 0215` item 3, not merely struck as
  [PROPOSED] any more: no artifact in this repository records which mask
  bits that probe set, `docs/GM_LANE.md:5540` says only that the table was
  re-derived from that session, and COO has confirmed she has no other
  source for the sentence either. Nothing in this module rests on it.

  GT CRITERIA FOR (b''), NAMED HERE SO A FUTURE ROUND DOES NOT HAVE TO HUNT
  THE LETTER FOR THEM (not opened as a ticket this round -- see the closing
  paragraph below): on a NORMALLY LOGGED-IN CHARACTER (no special selection
  needed, because (b'') drops no row for any character) -- cash, HP-max, MP
  AND THE HP BAR ITSELF must read unchanged after ONE frame.  `STOP-on-
  HP-0` stays standing regardless.

STILL SHUT, EXACTLY AS BEFORE, AND (b'') DOES NOT ON ITS OWN OPEN IT
EITHER: chief's named-value read point EXISTS as of `server#695` and
answers 4 of the 26 rows (name, level, hp_current, hp_max) -- it still
needs x=9 added to what it was ordered to cover, and the other 22 rows
are what the refusal now names; chief's login-byte read point
for the other 29 rows does not exist AT ALL (`COO-DECISION 0216`); the
version gate is unflipped for this module's named-field door; `/speed`'s
own two locks stay shut. This round does not open a GT ticket -- `COO-
DECISION 0215` says so explicitly ("ยังไม่เปิดใบ GT").

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

~~!! ONE THING (b') DOES NOT COVER, AND IT IS NOT A DETAIL~~ -- RESOLVED BY
(b''), ABOVE (pf-adversary, round `3qh50k`, D11 -- [PROPOSED] there, RULED
by `COO-DECISION 0215` here, not resolved by this lane alone).  What this
paragraph found stands as the RECORD of why (b'') exists, so the finding is
struck, not deleted: (b') guarantees the NAMED rows.  x=9 `category_5C`
(BasicAttr +0x5C) was `known=False`, so under (b') its bit stayed unset and
the full-object copy ZEROED IT -- and this module's own `SELECTOR_NOTE_R301`
says [PROVEN, in-repo] that +0x5C is the u16 fed to `0x430E10`, whose result
`== 8` is what switches the client from reading HP at x=3/x=4 to reading it
at x=52/x=53.  So one frame could change WHICH HP pair the client displays.
Both pairs are seeded honestly, but for a character outside a category-8
context the honest `alt_hp_current/alt_hp_max` is plausibly `0/0` -- i.e.
HP `0/0` on the HUD after one frame, `GT-218`'s symptom arriving through
the very door (b') was revised to open.  The attended GT's stated criteria
(cash / HP-max / MP unchanged after one frame) would have caught this only
by luck.  COO's fix is not "flip x=9 alone" -- it is (b'') in full: x=9
moves to the required-real-value set (`named_field_x()` now includes it),
and every OTHER `known=False` row gets the login-byte treatment instead of
staying unset.  Nothing in this module sends yet, so nothing was ever at
risk; this paragraph is kept because a future round should be able to find
the finding that bought (b'') without reading the round file.

PATH 1 AND PATH 2 ARE CLOSED BY THIS, and that is the point of writing it
down: the owner's letter `20260831_2327` had been waiting on her since
31 Aug.  Path 1 ("send sparse and accept the risk") is REFUTED, not chosen
-- `GT-218` is what refutes it: `/speed 400`, a value the login path sends
every day, killed the client in one frame (HP `0/1`, cash `0`) through a
sparse send, so "accept the risk" was priced by measurement and the price
was the session.  Path 2 (name-only) is what (b') is, with the live-value
source that made it viable ordered into existence rather than assumed.

STILL SHUT, AND (b') DOES NOT ON ITS OWN OPEN IT.  Nothing below sends
live: ~~chief's read point does not exist yet~~ -- struck 2026-09-04
round `tof9cw` per `CHIEF-TO-LANE-GM 20260904_0305` item 1: it landed in
`server#695` and answers 4 of 26 rows, so the door refuses on the OTHER
22 (see `seed_cache_from_live_
values`, which refuses by name and now names which rows), the version gate is
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

  1. `model.Character` ~~has NO level/hp/stat fields at all -- `id,
     account_id, selector, name, actor_wire, avatar_wire, identity_lo,
     identity_hi, position`~~ -- struck 2026-09-04 round `tof9cw` per
     `CHIEF-TO-LANE-GM 20260904_0212`: `model.py:37` now carries a walk-speed
     field (the `speed_walk` column `login_speed.py` resolves -- the
     identifier itself is deliberately NOT spelled anywhere in this module,
     because `tests/test_npc_gait_wire.py` scans every `src/` file for it as
     a tripwire and this module genuinely never asks for one; the same
     discipline that file's own comment records for `login_speed.py`) and
     `model.py:65-67` carries `level`/`hp_current`/
     `hp_max` (`COO-DECISION 20260903_0647`).  THE CONCLUSION SURVIVES AND
     IS WHY THIS IS STRUCK RATHER THAN REWRITTEN AS A NEW SOURCE:
     `model.py:55-58` says `store._character` does not read those three
     columns, so a character loaded from the database arrives with all
     three `None` and only `session.py` fills them at login.  Reading them
     here would get `None`, not a value.  There is still nothing here to
     read -- chief's read point (point 3 below) is the seam that closes
     this, and closing the `None` half is LANE-DB's `PLAYER/CHARACTER`
     work (`COO-ORDER 20260904_0329`), not this lane's.
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
  3. ~~No `lane_hooks` point exists today that hands a lane the fields
     `runtime.py`'s login path is about to send for this shape~~ -- struck
     2026-09-04 round `tof9cw`.  One EXISTS:
     `lane_hooks.current_named_attr_values`, ordered by `COO-DECISION
     20260904_0047` item 1 and landed by chief in `server#695`.  It answers
     4 of the 26 named rows -- name, level, hp_current, hp_max -- which is
     what the server actually knows, and it answers nothing for the
     `known=False` rows (that is the SECOND point, `COO-DECISION 0216`,
     still unbuilt).  The old sentence's reasoning was right about the
     cause and wrong about the remedy: runtime.py still does not compose a
     DBAttribute block at login, so chief's point reads typed COLUMNS
     rather than capturing a block, and the 22 rows with no column are a
     work list for LANE-DB (`COO-ORDER 20260904_0329`) rather than a dead
     end.  See `live_named_values` for how this lane consumes it, and
     `src/pirateforce_foundation/live_named_attr_values.py` for chief's
     own account of which rows have no column at all.

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
    (9,  "basic", 0x0100, 0x05C, 0x12, "u16",  "category_5C",     True,  "0x430E10(this)==8 swaps HP to x52/53; known=True by COO-DECISION 20260904_0215 item 2 -- see SELECTOR_NOTE_R301"),
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
#   `COO-DECISION 20260904_0215` item 2 later flipped x=9's `known` column
#   `False` -> `True`.  THIS IS NOT A RENAME and does not reopen the
#   question above: the name stays `category_5C`, still no claim about what
#   category 8 IS.  What changed is narrower and is not about the name at
#   all -- x=9 moved from "this lane may not set it" to "this lane's send
#   MUST carry its real value", because it is proven [PROVEN, in-repo] to
#   select which HP pair the client reads, and (b'') (see module docstring)
#   makes every row's absence a zero on the client.  A selector is not an
#   unnamed row that happened to get lucky; it is load-bearing for what
#   `known=False` rows are now DELIBERATELY NOT: something (b'') is willing
#   to send the wrong-but-safe login byte for.
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

    The `u*`/`i32` messages are UNCHANGED from the ones `encode_field` raised
    before the split.  ~~`wstr` is UNCHANGED too~~ -- struck 2026-09-04,
    chief's letter `20260904_0305` item 2 (MEASURED): it gained an encodability
    check the same round `f32` did, for the same reason (see the `wstr`
    branch below).  `f32` and `blob` gained one each at the split; `wstr`
    gained its second check one round later: all three used to let a bad
    value out as a bare `TypeError`/`OverflowError`/`UnicodeEncodeError`
    from `float()`, `bytes()`, or `str.encode()`.  ~~and `UnicodeEncodeError`
    is the one exception class this module's callers do not catch by name
    either -- same shape as `f32`'s `OverflowError` gap~~ -- struck
    2026-09-04, pf-adversary round `ycqzuz` (MEASURED, `issubclass(
    UnicodeEncodeError, ValueError) is True`): unlike `OverflowError`,
    `UnicodeEncodeError` **is** a `ValueError`, and `runtime.py` has no
    call site for `encode_field`/`encode_block` yet, so no existing
    `except ValueError` net was ever bypassed by it.  The real reason this
    check exists: this module's OWN seeding functions
    (`live_named_values`/`live_login_bytes`) catch only
    `AttrWireError` locally, and without this check a lone surrogate could
    slip past `validate_field_value` and be blessed into `seeded[x]` --
    the "cache holding a baseline no send can ever use" outcome this
    docstring's second paragraph forbids.  A narrower, more precise claim
    than the one originally written here.
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
        # THE SAME SHAPE AS THE f32 FIX ABOVE, NARROWER CLAIM (chief's
        # letter `20260904_0305`; pf-adversary round `ycqzuz` corrected the
        # first draft of this comment): a length check alone still blessed
        # `"Anne\ud800"` for x=1 `name` -- `encode_field`'s
        # `value.encode("utf-16le")` then raised `UnicodeEncodeError`
        # mid-compose.  UNLIKE `OverflowError` above, `UnicodeEncodeError`
        # **is** a `ValueError` subclass (`issubclass(UnicodeEncodeError,
        # ValueError) is True`), and `runtime.py` has no call site for
        # `encode_field`/`encode_block` at all yet -- so this is NOT an
        # uncaught-exception escape at the runtime.py layer, and no
        # existing `except ValueError` net was ever bypassed by it.  What
        # it WAS bypassing: the two LOCAL `except AttrWireError` catches in
        # `live_named_values`/`live_login_bytes` below, which is exactly
        # how a lone surrogate could have been silently blessed into
        # `seeded[x]` -- a `RawBlockCache` holding a value `encode_field`
        # will refuse, the one outcome this function's own docstring
        # forbids.  Asking the actual codec is the only bound guaranteed to
        # agree with the encoder, same reasoning as f32's `struct.pack`
        # probe.  Not reachable today (sqlite refuses a lone surrogate in
        # the `name` column before this ever runs), but x=1 just became
        # the first row `lane_hooks.current_named_attr_values` can feed
        # with an external string, so the surface is wider than when this
        # function's docstring was written.
        try:
            value.encode("utf-16le")
        except UnicodeEncodeError as error:
            raise AttrWireError(
                f"{name}: wstr not encodable as utf-16le: {value!r} ({error})"
            ) from None
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

    (b'') COMPLETENESS IS DELIBERATELY *NOT* ENFORCED HERE, AND THAT IS NOW
    A DECISION, NOT AN ASSUMPTION: `COO-DECISION 20260904_0215`'s wording
    named `encode_block` for the raise; `COO-DECISION 20260904_0345` item 1
    answered this lane's alarm (`20260904_0309`) and MOVED it, by name, to
    "any function that returns a wire-ready `0x309A` frame
    (`make_update_attr_frame` and everything wrapping it)".  The reason COO
    gives is the one this function's own measurement found: `encode_block`
    is a pure byte composer with NO frame header, and bytes with no frame
    header cannot leave the server -- so LANE-DB's `persistence_attr_
    compose` tests do not get touched.  The old `[ASSUMPTION OF LANE-GM]`
    tag is retired here; the wall now exists (see `make_update_attr_frame`),
    so the guarantee below is no longer policy-only.
    Measured before committing, not guessed: this function is the shared
    low-level DBAttribute-body composer every caller in this repository
    uses, not only this lane's own named-field door, and a sparse `values`
    dict is a LEGITIMATE input to two things a completeness check here
    would break --
      * `persistence_attr_compose.py` (LANE-DB's own module,
        `tests/test_persistence_attr_compose.py`,
        `test_the_composed_block_sets_one_mask_bit_and_it_is_x7s`) calls
        this function directly with a one-field block and asserts on the
        resulting sparse mask -- outside this lane's write zone (`gm/`
        only), so this lane may not edit it to match a widened contract;
      * this lane's OWN `tests/test_gm_speed_shape_hold.py` measures GT-193's
        REAL attended-round frame (`GT193_FRAME_LENGTH`,
        `GT193_EMPTY_ACTOR_SECTION`) through this exact sparse call shape
        -- that is measured history.  `COO-DECISION 20260904_0345` item 1
        changed what that file PINS (the shape must now raise at the frame
        exit: "pinning that the shape which killed a client can no longer be
        built is worth more than pinning that it still can"), but the BODY
        this function composes for it is still measurable, which is how that
        file keeps the byte-level history it measured.
    THE THIRD CALLER, the live one pf-adversary found, IS NOW CLOSED:
    `speed_wire.compose_sparse_speed_update` reached this shape at runtime
    through the `PF_SPEED_TRIAL` owner-only gate.  `COO-DECISION
    20260904_0345` item 2 WITHDREW the 2026-09-03 06:46 approval of that
    hatch (it predates `RE-222`) and that function now refuses every call;
    `make_update_attr_frame` would refuse it a second time regardless.  So
    (b'')'s guarantee is no longer narrower than its sentence: no partial
    0x309A FRAME leaves this module, by any route, because the only function
    that puts a header on a body checks the body first.  Sparse BODIES still
    compose here, and cannot leave.  The LANE-B "Door B" scenario
    `COO-DECISION 0046` item 2 named stays closed too (Door B composes
    through `build_named_field_update`, per that module's own docstring: "a
    caller sends" -- `capture_initial()` seeds the cache, it does not itself
    reach `encode_block`).

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

    THIS IS WHERE (b'') IS ENFORCED, AND IT IS ENFORCED STRUCTURALLY
    (`COO-DECISION 20260904_0345` item 1).  A frame that leaves here is a
    frame that can go on a socket, so the completeness question is asked
    HERE, of every caller, rather than only at `build_named_field_update`:
    `values` must cover EVERY row in `all_field_x()` or this raises
    `AttrWireError` and no frame exists at all.

    WHY NOT `encode_block`, which `COO-DECISION 20260904_0215` named first
    and this lane's `20260904_0309` alarm answered: `encode_block` composes
    a DBAttribute body with NO frame header, and bytes with no frame header
    cannot leave the server.  It stays sparse-capable on purpose -- LANE-DB's
    `tests/test_persistence_attr_compose.py` and this lane's own shape
    measurement (`speed_wire.declared_empty_sections`) both compose sparse
    bodies deliberately and neither puts one on a wire.  Moving the raise up
    one layer, to the function that adds the header, closes the hole that
    alarm found (a future caller reaching past `build_named_field_update`
    straight to the byte builders -- which is exactly what
    `speed_wire.compose_sparse_speed_update` was doing) without touching a
    peer lane's tests.  `build_named_field_update`'s own cache check stays
    as the upper layer: it refuses EARLIER and with a better message, but it
    is a rule addressed to callers, and this one is a wall.

    ~~THE UNIT IS `all_field_x()`, NOT `named_field_x()`~~ -- struck
    2026-09-04 round `4fxkam` by `COO-DECISION 20260904_0545` item 1, which
    withdraws `0215` item 1's wording outright.  THE UNIT IS NOW
    `login_mask.login_field_x(legacy)`: the rows PRODUCTION LOGIN ITSELF sets
    bits for, derived from the login composer on every call, never typed.
    `RE-222` Q0 (SHA-pinned) still says an unset mask bit decodes as a ZERO,
    and `GT-218` still measured that (HP `0/1`, cash `0`, one frame) -- what
    changed is the evidence about WHICH set is safe: this server sends a
    9-row block (10 with the faction branch) to a real client at every login
    and the client survives it daily, byte-for-byte IDENTICAL to what
    `encode_block` composes for that set (LANE-GM `20260904_0505`, re-measured
    this round).  A 55-row wall demanded a byte source for 26 rows that no
    code in this repository has -- a gate whose condition cannot be met.
    x=30 is NOT in the login set and `login_mask.field_x_for_masks` raises if
    a future login composer ever puts it there (`0545` item 5).  The paired
    bits (x39/x40, x41/x42) satisfy `encode_block`'s pair rule automatically:
    login sets neither pair's bit, so neither half is ever asked for alone.

    THE MASK IS CHECKED AFTER COMPOSING, NOT ONLY THE KEY SET (`0545` item 2:
    "the frame's basic_mask/actor_mask must EQUAL that login mask exactly").
    Checking the keys alone would pass a frame whose composed mask drifted
    from the login mask for any reason the key set cannot see -- a `FIELDS`
    row rebound to a different bit, say.  The mask is the thing the client
    reads, so the mask is the thing this wall compares.

    Still not gated on `UPDATE_ATTR_VITAL_VERSION_CONFIRMED` -- same
    separation `state_wire.make_gm_update_state_frame` keeps from its own
    caller-side gate.  That gate answers "may this vital be sent at all";
    this one answers "is this frame shaped like the one that killed the
    client".  Neither substitutes for the other.
    """
    from . import login_mask  # noqa: PLC0415 - avoids an import cycle, see below

    admitted_sets = login_mask.admitted_field_x_sets(legacy)
    given = set(values)
    if not any(given == set(shape) for shape in admitted_sets):
        widest = max(admitted_sets, key=len)
        raise AttrWireError(
            "refusing to build a 0x309A frame that is not login-shaped: "
            f"{len(values)} rows given "
            f"(missing={[x for x in widest if x not in given]}, "
            f"unexpected={[x for x in sorted(given) if x not in widest]}) -- "
            f"admitted login shapes are {[list(shape) for shape in admitted_sets]} "
            "(COO-DECISION 20260904_0545 item 1/2: (b'') is the set production "
            "login itself sets bits for); an unset mask bit is a ZERO on the "
            "client, not 'unchanged' (RE-222 Q0, the mechanism GT-218 measured)"
        )
    body, basic_mask, actor_mask = encode_block(legacy, identity_lo, identity_hi, values)
    login_mask.refuse_unless_login_shaped(legacy, basic_mask, actor_mask)
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
# 2026-09-04T00:47+07:00` and ~~NOT YET BUILT~~ LANDED IN `server#695`
# (`CHIEF-TO-LANE-GM 20260904_0305` item 1, struck here rather than
# rewritten so the wait is still legible).  It answers 4 of the 26 rows
# `named_field_x()` asks for; x=9 (`COO-DECISION 0215` item 2) is not among
# them yet.  Spelled once, here, so nothing in this lane has to be hunted
# for -- and so a test can pin the name this lane reads by.
LIVE_VALUE_READ_POINT = "current_named_attr_values"

# The name of chief's SECOND read point -- the login-byte source (b'')
# needs for every `known=False` row, ordered by `COO-DECISION
# 2026-09-04T02:16+07:00` and NOT YET BUILT AT ALL (unlike
# `LIVE_VALUE_READ_POINT`, which exists as a name chief still has to fill
# in; this one is not even named on chief's side yet -- `0216` asks chief
# to "name the login byte source for unnamed rows").  Spelled once, here,
# for the same reason: a test can pin the name this lane is waiting on
# without importing a module that does not exist, and the day chief lands
# it (under this name or another -- see `live_login_bytes`'s own
# docstring), nothing in this lane has to be hunted for.
LOGIN_BYTES_READ_POINT = "current_login_attr_bytes"

# The two console lines the seeding path may print, both pure ASCII (the
# bridge console is cp874).  A refusal is the SHIPPED outcome today -- chief's
# read point does not exist -- so it gets a real line rather than silence:
# "nothing happened" with no console line is the exact shape the owner
# reported as a bug on `/warp`, and this lane does not get to repeat it.
SEED_REFUSED_CONSOLE_TOKEN = "GM_ATTR_SEED_REFUSED"
SEED_CAPTURED_CONSOLE_TOKEN = "GM_ATTR_SEED_CAPTURED"


def named_field_x() -> tuple:
    """Every `x` that (b'') says must carry a REAL, live value on a send
    (as opposed to a login byte -- see `unnamed_field_x()`).

    `known=True` MINUS `SENSITIVE_FIELDS`, and the subtraction is not
    currently a no-op by luck: `SENSITIVE_FIELDS` holds x=30, which is
    `known=False` today, so the two sets do not overlap yet.  They would the
    moment an RE result renames x=30 -- and x=30's own row comment says it
    must never be settable through this API "even once this field is renamed
    True".  Doing the subtraction here means that rename cannot quietly turn
    a sensitive blob into a required seed value.

    Includes x=9 as of `COO-DECISION 20260904_0215` item 2 (`FIELDS` row 9's
    own `known` column carries the change; nothing here had to move).
    """
    return tuple(
        field[0] for field in FIELDS if field[7] and field[0] not in SENSITIVE_FIELDS
    )


def all_field_x() -> tuple:
    """Every `x` in `FIELDS`, in table order -- the completeness bound
    (b'') enforces on every 0x309A send (see `encode_block`'s own
    docstring).  `named_field_x()` and `unnamed_field_x()` partition this
    set exactly; `live_full_block_values` asserts that partition holds."""
    return tuple(field[0] for field in FIELDS)


def unnamed_field_x() -> tuple:
    """Every `x` in `FIELDS` that is NOT in `named_field_x()` -- the rows
    (b'') requires the SAME BYTES the login path already sends this
    character, sourced from `live_login_bytes`, never a real-time read and
    never zero-by-omission.

    INCLUDES `SENSITIVE_FIELDS` (x=30).  This is deliberate and is not a
    back door around that set: `SENSITIVE_FIELDS` forbids this module from
    ever letting a caller CHOOSE x=30's value through `build_named_field_
    update`'s `x` argument -- it says nothing about carrying forward
    whatever byte the login path already sent for it today, which is a
    fact about this character's existing row, not a value this lane
    composed.  `build_named_field_update` still refuses `x=30` outright,
    unchanged by this function existing.
    """
    named = set(named_field_x())
    return tuple(field[0] for field in FIELDS if field[0] not in named)


def live_named_values(character_id, *, hooks=None, wanted=None) -> dict:
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
    this lane's modules, so an import at module scope would close a cycle.
    ~~and the attribute does not exist yet in any case, which is why the
    "missing" branch is the shipped one.~~ -- struck 2026-09-04 round
    `tof9cw`: chief LANDED `lane_hooks.current_named_attr_values` in
    `server#695` and said so in `CHIEF-TO-LANE-GM 20260904_0305` item 1.
    The point EXISTS; it answers 4 of the 26 rows this function wants (name,
    level, hp_current, hp_max), so the shipped refusal today is
    `missing_named_rows`, not `no_read_point`.  (b') is still not satisfied
    and nobody claims it is.  `hooks` is injectable for tests -- the same
    seam every other module in this lane uses for a runtime object.

    THREE REFUSALS, THREE NAMES (`CHIEF-TO-LANE-GM 20260904_0305` item 3).
    Chief's hook returns `{}` both when NOBODY REGISTERED A SOURCE in this
    process and when a registered source knows nothing, and a dict cannot
    carry that difference -- he prints `LANE_HOOK live_attr_values
    NO_SOURCE_REGISTERED` once per process and asked this lane for the other
    half.  It is here: an EMPTY answer is `no_source_registered`, a
    non-empty but incomplete answer is `missing_named_rows`.  The split is
    honest about its own edge -- a registered source that happens to know
    ZERO rows is reported as `no_source_registered` too, because nothing in
    the return contract can tell those apart, and this function will not
    invent a distinction by reading `lane_hooks`' private state.  It matters
    because 12 of the 13 processes that open a store in this repository
    register no source at all: an operator reading `missing_named_rows: 26
    absent` would go hunting for values that were never asked for.
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
    if not values:
        # See this function's "THREE REFUSALS, THREE NAMES" paragraph: the
        # empty answer is the one an operator must NOT read as "the server
        # does not know these 26 values".
        raise AttrWireError(
            f"no_source_registered: lane_hooks.{LIVE_VALUE_READ_POINT} "
            "answered nothing at all in this process -- either no source is "
            "registered (grep the console for LANE_HOOK live_attr_values "
            "NO_SOURCE_REGISTERED) or the registered source knows no row"
        )

    wanted = named_field_x() if wanted is None else tuple(wanted)
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


def live_login_bytes(character_id, *, hooks=None, wanted=None) -> dict:
    """Read every `unnamed_field_x()` row's LOGIN-SENT bytes, or raise
    saying why not.

    THIS IS THE SECOND HALF OF (b'') (`COO-DECISION 20260904_0215` item 1,
    module docstring section "(b') IS NOW (b'')"): a `known=False` row may
    not go unset, because an unset mask bit is a ZERO on the client, the
    exact mechanism `RE-222` names for `GT-218`.  So these rows must carry
    SOME byte too -- and the only byte this house has ever measured a real
    client surviving for a row it has no name for is whatever the login
    path already sends this character every single day.  Mirrors
    `live_named_values` exactly: same all-or-nothing contract (a dict
    covering every wanted row or a named `AttrWireError`, never a partial
    answer), same validation, same reasoning for resolving the hook lazily
    and by name.

    READS A DIFFERENT HOOK FROM `live_named_values` -- `LOGIN_BYTES_READ_
    POINT`, ordered by `COO-DECISION 20260904_0216` and NOT YET BUILT AT
    ALL (chief has not even named it on her side yet; `LOGIN_BYTES_READ_
    POINT`'s value is this lane's own proposal for what to call it, open to
    chief renaming it -- see that constant's own comment).  So on a real
    boot today this function refuses exactly like `live_named_values` did
    before chief's first read point landed, for the same reason: nothing
    calls it into existence by wanting it to exist.
    """
    if hooks is None:
        try:
            from .. import lane_hooks as hooks  # noqa: PLC0415 - see live_named_values
        except Exception as error:  # noqa: BLE001 - any import failure is a refusal
            raise AttrWireError(
                f"no_login_byte_read_point: lane_hooks is unimportable "
                f"({type(error).__name__})"
            ) from None
    read_point = getattr(hooks, LOGIN_BYTES_READ_POINT, None)
    if not callable(read_point):
        raise AttrWireError(
            f"no_login_byte_read_point: lane_hooks.{LOGIN_BYTES_READ_POINT} "
            f"does not exist yet (ordered by COO-DECISION 20260904_0216)"
        )
    try:
        values = read_point(character_id)
    except Exception as error:  # noqa: BLE001 - a hook may never take dispatch down
        raise AttrWireError(
            f"login_read_point_raised_{type(error).__name__}"
        ) from None
    if not isinstance(values, dict):
        raise AttrWireError(
            f"not_a_mapping: login byte read point returned {type(values).__name__}"
        )
    if not values:
        # Symmetric with `live_named_values`, and for the same reason
        # (`CHIEF-TO-LANE-GM 20260904_0305` item 3): an empty answer is a
        # missing SOURCE, not 29 rows this server happens not to know.
        # Written now rather than when chief's second point lands, because
        # the asymmetry would be invisible until the day it misled someone.
        raise AttrWireError(
            f"no_login_byte_source_registered: lane_hooks."
            f"{LOGIN_BYTES_READ_POINT} answered nothing at all in this "
            "process"
        )

    wanted = unnamed_field_x() if wanted is None else tuple(wanted)
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
            unsendable.append(x)
            continue
        seeded[x] = values[x]
    if absent or unsendable:
        parts = []
        if absent:
            parts.append("absent=" + ",".join(str(x) for x in absent))
        if unsendable:
            parts.append("unsendable=" + ",".join(str(x) for x in unsendable))
        raise AttrWireError("missing_login_rows: " + " ".join(parts))
    return seeded


#: Rows whose value must be THE ONE LOGIN SENT THIS CONNECTION, never a
#: typed column and never a constant -- `COO-DECISION 20260904_0545` item 2
#: names them by hand: "x=9 and x=10 from the session, the value login sent;
#: no constant, no zero".  x=11 joins them for the same reason: the login
#: composer takes it from `world_faction_admission.PROVEN_BASIC_FACTION`, not
#: from a character row, and `live_named_attr_values.ROWS_WITH_NO_COLUMN_AT_
#: ALL` lists it as a row the store has no column for at all.
#:
#: WHY THIS IS NOT A HAND-TYPED LIST OF THE (b'') SET.  It is not the set; it
#: is the SOURCE ROUTING for whatever the derived set turns out to hold.  A
#: row that leaves the login set stops being routed anywhere, and a row that
#: joins it lands in the typed-column group unless it is named here -- which
#: is the conservative direction (the typed group refuses loudly when the
#: store has no column, rather than a silent constant).
#:
#: pf-adversary round `4fxkam` D3 is why x=9 moved here rather than staying
#: with the named rows: x=9 is the HP-PAIR SELECTOR (`SELECTOR_NOTE_R301`,
#: [PROVEN in-repo]) and login writes THE SCENE THE PLAYER IS STANDING IN
#: onto it (`player_wire.py`, `u16tag(0x12, scene_id)` at BasicAttr bit
#: 0x0100).  Routing it to a typed column would let a column that disagrees
#: with the live scene flip the selector, and the alternate pair it selects
#: (x=52/x=53) is NOT in the login set -- so the client would read HP from
#: two bits nothing set, i.e. `0/0` on the HUD.  That is `GT-218`'s symptom
#: arriving through the gate built to stop it.  The residual risk is written
#: up in `pf_bridge/notes_to_chief/20260904_0752_LANE-GM-ASK-COO-*`.
LOGIN_SOURCED_ROWS = frozenset({9, 10, 11})


def login_scoped_sources(legacy) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """`(named_rows, login_byte_rows)` -- the login set split by value source.

    `COO-DECISION 20260904_0545` item 2 names the sources row by row: the
    `known=True` rows come from chief's live read point, EXCEPT the rows in
    `LOGIN_SOURCED_ROWS`, which must carry the byte login itself sent this
    connection.  Under the redefined (b'') the second group is x=7, x=9,
    x=10 and x=11 -- and x=7/x=10 are the exact two rows LANE-GM's
    `20260904_0505` measured login as having bytes for.  That is the whole
    reason the redefinition unblocks anything: the 55-row wording wanted 26
    more rows from a source that has never held one.
    """
    from . import login_mask  # noqa: PLC0415 - avoids an import cycle

    return split_sources(login_mask.login_field_x(legacy))


def split_sources(rows) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """`login_scoped_sources` for an EXPLICIT row set (one connection's own
    shape), rather than for the union of every shape production can compose."""
    named = set(named_field_x()) - LOGIN_SOURCED_ROWS
    return (
        tuple(x for x in rows if x in named),
        tuple(x for x in rows if x not in named),
    )


def live_full_block_values(character_id, *, hooks=None, legacy=None, rows=None) -> dict:
    """(b'') IN FULL: a dict covering the LOGIN SET, or a named
    `AttrWireError`, never a partial answer -- this is the ONLY function
    `seed_cache_from_live_values` calls, so nothing in this module can seed
    a cache from one source alone.

    ~~a dict covering every `FIELDS` row~~ -- struck 2026-09-04 round
    `4fxkam`: `COO-DECISION 20260904_0545` item 1 withdrew the 55-row
    wording, and item 2 replaced it with "the set production login itself
    sets bits for".  Combines `live_named_values` (real value) and
    `live_login_bytes` (login byte) over `login_scoped_sources` rather than
    over the whole table.  Either source refusing still refuses the WHOLE
    block -- "no byte source for any row = the door refuses the whole thing,
    never a partial send" survives the redefinition unchanged, and is the
    half of `0215` item 1 that the new wording keeps.  `live_named_values` is
    tried first, so a boot missing chief's first read point (today's shipped
    world) reports `no_read_point`, not the second point's absence.

    `legacy` IS REQUIRED AND HAS NO DEFAULT SHAPE.  The login set can only be
    derived by running the production composer, which needs the loaded
    `pf_login_game_server_v141` module; a caller that cannot supply it cannot
    know which rows (b'') wants, so this refuses by name instead of falling
    back to a set nobody measured.  It is keyword-optional only so that the
    out-of-zone callers in `tests/test_live_named_attr_values.py` keep
    getting the refusal they assert on rather than a `TypeError`.
    """
    if rows is None and legacy is None:
        raise AttrWireError(
            "no_legacy_for_login_set: (b'') is the set production login sets "
            "bits for (COO-DECISION 20260904_0545 item 2), and deriving it "
            "requires the loaded legacy module -- pass legacy=load_legacy(...)"
        )
    if rows is None:
        named_rows, login_rows = login_scoped_sources(legacy)
    else:
        named_rows, login_rows = split_sources(rows)
    named = live_named_values(character_id, hooks=hooks, wanted=named_rows)
    unnamed = live_login_bytes(character_id, hooks=hooks, wanted=login_rows)
    combined = {**named, **unnamed}
    assert set(combined) == set(named_rows) | set(login_rows), (
        "live_full_block_values internal invariant broken: the two sources "
        "must partition the login set exactly"
    )
    return combined


def seed_cache_from_live_values(
    cache: RawBlockCache,
    character_id,
    *,
    hooks=None,
    stream=None,
    legacy=None,
) -> bool:
    """Seed one connection's cache from the live values, or refuse out loud.

    Returns True only when the cache now holds a real, COMPLETE (b'') block
    -- every `FIELDS` row, real value for `known=True`, login byte for
    `known=False` (see `live_full_block_values`).  NEVER RAISES: this is
    the function a future dispatch path calls before composing, and this
    module's founding property is that an accepted command never vanishes
    without a console line.

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
    every `known=False` row as a CHOSEN value, refuses an unseeded cache,
    and (since D10, widened by `COO-DECISION 20260904_0215`) refuses a
    cache that does not satisfy (b'') in full.  `encode_block` itself stays
    a general-purpose composer that still accepts a partial `values` --
    see that function's own docstring for why (b'') is enforced at this
    door instead, not one layer further down.
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
        values = live_full_block_values(character_id, hooks=hooks, legacy=legacy)
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
        f"rows={len(held)}",
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
    # (b'') IS ENFORCED AT THE DOOR, NOT ONLY IN THE HELPER THAT SEEDS
    # (pf-adversary, round `3qh50k`, D10; WIDENED from named-only to every
    # FIELDS row by `COO-DECISION 20260904_0215`).  `seed_cache_from_live_
    # values` refuses an incomplete answer -- but `RawBlockCache.capture_
    # initial` is PUBLIC and unvalidated, and `COO-DECISION 20260904_0046`
    # item 2 names TWO consumers of chief's read point: this lane's seeder
    # AND LANE-B's Door B, which was ordered to call `capture_initial()` --
    # the function the helper does not gate.  A peer lane doing exactly
    # what it was told, with a hook that omits one row, would compose an
    # incomplete block here and the client's full-object copy would zero
    # the missing one.  That is GT-218's mechanism with the new gate fully
    # installed and looking the other way.
    #
    # So the completeness question is asked HERE, where every consumer must
    # pass, and it is asked of the CACHE rather than of whoever filled it.
    # `merged_with` already refuses an unseeded cache; this refuses a
    # half-seeded one, which is the more dangerous of the two because it
    # composes.  `encode_block` does NOT also refuse it (deliberately --
    # see that function's own docstring): this is the one door (b'')
    # governs, not the shared low-level composer every lane uses.
    from . import login_mask  # noqa: PLC0415 - avoids an import cycle

    # THE ROW ITSELF MUST BE ONE THE LOGIN SHAPE CARRIES (`COO-DECISION
    # 20260904_0545` item 2).  Setting a `known=True` row that login does NOT
    # send -- `mp_current`, say -- would add its bit to the frame's mask, and
    # the mask must EQUAL the login mask, not merely contain it.  The wall
    # would refuse it a second time; this refuses it first and by the reason
    # that is actually true of it, instead of telling the caller its block is
    # the wrong shape when what was wrong was the row it asked for.
    login_rows = login_mask.login_field_x(legacy)
    if x not in login_rows:
        raise AttrWireError(
            f"field x={x} ({field[6]}) is not in the login set {list(login_rows)}: "
            "a 0x309A frame's mask must EQUAL the production login mask "
            "(COO-DECISION 20260904_0545 item 2), so a row login does not send "
            "cannot be set through this door -- it would widen the mask"
        )

    held = set(cache.current_values())
    admitted = login_mask.admitted_field_x_sets(legacy)
    if not any(held == set(shape) for shape in admitted):
        widest = set(max(admitted, key=len))
        raise AttrWireError(
            "cache does not satisfy unlock (b''): it holds "
            f"{len(held)} rows, none of the admitted login shapes "
            f"{[list(shape) for shape in admitted]} "
            f"(missing={sorted(widest - held)}, unexpected={sorted(held - widest)})"
            " -- an unset mask bit is a ZERO on the client, not 'unchanged'"
            " (COO-DECISION 20260904_0545 item 1/2 redefined the set; see the"
            " module docstring, section \"(b') IS NOW (b'')\")"
        )
    # THE DOOR MAY CHANGE A VALUE, NEVER THE SHAPE (pf-adversary round
    # `4fxkam`, D1, MEASURED).  `login_field_x` is the UNION of every shape
    # production can compose, so checking `x` against it admits x=11 for a
    # connection whose login composed the PLAIN branch -- a connection in a
    # scene `world_faction_admission` deliberately refuses a faction bit for.
    # Measured: the frame went out with `basic_mask=0x074F` where login had
    # sent `0x034F`, and `record_sent` then froze the faction shape into the
    # cache for every later frame on that connection.  That is this lane
    # overruling a gate it does not own, which `login_mask`'s own docstring
    # forbids in as many words.  The cache is the only per-connection record
    # of the login shape this module has today, so the shape it holds is what
    # the answer must be measured against -- not the union.
    if x not in held:
        raise AttrWireError(
            f"field x={x} ({field[6]}) is not in the shape this connection's "
            f"cache holds {sorted(held)}: this door changes a VALUE, never the "
            "frame's mask -- setting a row login did not send this connection "
            "would widen its mask past the login mask (COO-DECISION "
            "20260904_0545 item 2)"
        )

    merged = cache.merged_with({x: value})
    pc, frame = make_update_attr_frame(legacy, identity_lo, identity_hi, merged)
    cache.record_sent(merged)
    return pc, frame
