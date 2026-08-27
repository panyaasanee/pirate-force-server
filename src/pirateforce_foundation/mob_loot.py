"""LANE-B / MOB-LOOT-001: the monster a player kills leaves something behind.

WHAT THIS MODULE IS FOR.  M5 is "loot drops, you pick it up, it is in your bag
after a relog".  This module is its FIRST half and says so in every claim it
makes: a kill rolls the dead monster's OWN drop sets out of the real game
tables, the roll becomes a ledger of what that kill produced, and each row
becomes one frame of the exact list shape an attended run has already watched
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
    frame     <- one single-element frame each (the V43 one-record lesson)

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
  change-mask byte 0x08 selecting the list, and ONE element per frame: a
  combined multi-record derived-mask collection is the one shape a real client
  has already rejected with ErrorData=28317.
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

from dataclasses import dataclass
import hashlib
import math
import random as _random
import struct
import threading
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
    "hold_ms -- one frame each, in the order returned.  NOT between the dying "
    "and dead frames: nothing measured says a derived-mask-0x08 RuntimeRes "
    "may be interleaved into another lane's typed lethal sequence for the "
    "same actor, and the label lives 0.2-0.4 s, so loot sent inside the hold "
    "is gone before the corpse frame is.\n"
    "  4. PRUNE THROUGH THE CELL (cell.take(key)).  Nothing in this module "
    "expires a row and the label is off screen in under half a second; a "
    "caller that never prunes grows the ledger without bound.  Pruning beside "
    "the cell, on a value you kept, loses whatever a kill wrote in between.\n"
    "  5. nothing else, and ONE ANNOUNCEMENT PER DROP.  The COO REFUSED this "
    "lane's assumption 4 on 2026-08-26 (07:45 +07:00): DROP_REFRESH_MS may "
    "not be wired into a production path, because 12.5 frames a second per "
    "row is too much to spend on a mechanism nobody has measured.  "
    "cell.frames(legacy) "
    "and refresh_frames() remain EXPERIMENT TOOLS -- do not put either on a "
    "timer in runtime.py.  What reopens the question is a measurement of the "
    "label's lifetime from real play, not a cheaper number."
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
# TOOL and the production behaviour is ONE ANNOUNCEMENT PER DROP, until
# somebody measures the label's lifetime from real play.  The constant is kept
# (deleting it would delete the arithmetic that argues against it) and the
# wiring line no longer offers it.
DROP_REFRESH_MS_IS_EXPERIMENT_ONLY = True
DROP_REFRESH_MS = 80
MAX_DROPS_PER_KILL = 16

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
    "3. NOT ONE OF THE 63 IDS THIS LANE CAN EMIT HAS EVER BEEN ON A "
    "CLIENT'S WIRE.  Three ids have (2200423 and 2200003 in the GT-045 v3 "
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
    "13. DELTA OR REPLACEMENT IS UNPROVEN, and it matters for every kill that "
    "drops more than one object.  This lane sends one element per frame "
    "because a multi-record derived-mask collection is the shape a real "
    "client rejected; if the client treats each such frame as the WHOLE "
    "ground list rather than as a change to it, the second row of a kill "
    "removes the first and a player sees one name instead of three.",
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


def _require_identity(value: Any, label: str) -> int:
    identity = _require_int(value, label, -(2 ** 62), 2 ** 62)
    if identity <= 0:
        raise MobLootContractError(
            REFUSE_IDENTITY_NOT_POSITIVE, "%s must be positive" % label)
    return identity


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
    """One object standing where a monster fell."""

    drop_key: int
    item_id: int
    quantity: int
    x: float
    y: float
    z: float
    mob_identity: int
    killer_identity: int

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

    @property
    def display_name(self) -> str:
        return field_drop_tables.ITEMS[self.item_id][2]


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
            actor_identity, killer_identity,
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

    It is deliberately tiny and it still does nothing on its own: no clock, no
    socket, no thread, no expiry.  Pruning is still the caller's duty (there
    is nothing in this lane that knows when a label has faded), but it is now
    a duty performed THROUGH the cell instead of on a value beside it.
    """

    def __init__(self, ledger: Any = None) -> None:
        if ledger is None:
            ledger = DropLedger()
        if type(ledger) is not DropLedger:
            raise MobLootContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "a cell holds a typed DropLedger")
        self._ledger = ledger
        self._lock = threading.Lock()

    @property
    def ledger(self) -> DropLedger:
        """The current value.  A snapshot; storing it is not owning it."""
        with self._lock:
            return self._ledger

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
            current = self._ledger
            drops = place_drops(
                mob, record, roll, current.next_key, position=position)
            self._ledger = commit_drops(
                current, drops, base_generation=current.generation,
                kill_token=kill_token,
                mob_identity=getattr(record, "actor_identity", None))
            return drops

    def take(self, drop_key: int) -> Any:
        """Remove one row -- a pickup, or the prune the caller owes."""
        with self._lock:
            self._ledger, taken = take_drop(self._ledger, drop_key)
            return taken

    def frames(self, legacy: Any) -> tuple:
        """Re-emit every live row.  See :func:`refresh_frames` for the caveat."""
        return refresh_frames(legacy, self.ledger)


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


def drop_pc(legacy: Any, drop: Any) -> bytes:
    """The single-element RuntimeRes pc that carries one ground drop."""
    element = drop_element(legacy, drop)
    pc = bytearray()
    pc += legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_RES)
    pc += legacy.u32tag(0x14, 0)
    pc += legacy.u8tag(0x08, ENVELOPE_VERSION)
    pc += legacy.u8tag(0x0B, 0)                                # inherited none
    pc += legacy.u8tag(0x0B, RUNTIME_DERIVED_BIT_GROUND_LIST)  # derived 0x08
    pc += legacy.u16tag(ELEMENT_LIST_COUNT_TAG, 1)             # ONE element
    pc += element
    pc = bytes(pc)
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
    if pc[DROP_ENVELOPE_SIZE:] != element:
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the composed pc does not end in the element it was built from")
    coordinates = b"".join(pc[start:end] for start, end in DROP_COORD_SPANS)
    if coordinates != struct.pack("<fff", drop.x, drop.y, drop.z):
        raise MobLootContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the composed coordinates are not the drop's coordinates")
    return pc


def drop_frames(legacy: Any, drops: Any) -> tuple:
    """One framed single-element message per drop, in ledger order.

    ONE element per frame on purpose: a combined multi-record derived-mask
    collection is the one shape a real client has already rejected with
    ErrorData=28317 (the V43 lesson the probe lane also obeys).
    """
    out = []
    for drop in drops:
        pc = drop_pc(legacy, drop)
        frame = legacy.frame_pc(pc)
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
        if frame[DROP_FRAME_HEADER_SIZE:] != pc:
            raise MobLootContractError(
                REFUSE_COMPOSED_BYTES_OFF_PIN,
                "the framed body is not the pc that was composed")
        shifted = b"".join(
            frame[start + DROP_FRAME_COORD_SHIFT:end + DROP_FRAME_COORD_SHIFT]
            for start, end in DROP_COORD_SPANS
        )
        if shifted != struct.pack("<fff", drop.x, drop.y, drop.z):
            raise MobLootContractError(
                REFUSE_COMPOSED_BYTES_OFF_PIN,
                "the framed coordinates are not the drop's coordinates")
        out.append((pc, frame))
    return tuple(out)


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

    AND THE COO HAS SINCE REFUSED IT FOR PRODUCTION (2026-08-26 07:45 +07:00).
    This function may be called by hand, by a test, or by an attended
    experiment.  It may NOT be put on a timer in ``runtime.py``: the shipped
    behaviour is one announcement per drop until the label's lifetime is
    measured from real play.
    """
    if type(ledger) is not DropLedger:
        raise MobLootContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "ledger must be a typed DropLedger")
    return drop_frames(legacy, ledger.drops)


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
    sample = GroundDrop(
        DROP_KEY_BASE, 2400046, 1, as_wire_float(1.0), as_wire_float(2.0),
        as_wire_float(3.0), 0x201F, 0x0101,
    )
    pc = drop_pc(legacy, sample)
    frame = legacy.frame_pc(pc)
    masked = bytearray(pc)
    for start, end in DROP_COORD_SPANS:
        masked[start:end] = b"\x00" * (end - start)
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
            "elements_per_frame": 1,
            "pc_size": DROP_PC_SIZE,
            "frame_size": DROP_FRAME_SIZE,
            "masked_pc_sha256": hashlib.sha256(bytes(masked)).hexdigest().upper(),
            "sample_frame_size": len(frame),
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
    wiring pass can ``print()`` at the ``mob_loot.drop_frames`` call site in
    ``runtime.py``, so this lane -- unlike its siblings -- becomes visible to
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
    return (
        "MOB_LOOT_DROPS_CENSUS mob=%s template=%d identity=0x%X drops=%d "
        "items=%s" % (
            ascii(mob.display_name), mob.template_id, mob.actor_identity,
            len(drops), items if items else "none",
        )
    )
