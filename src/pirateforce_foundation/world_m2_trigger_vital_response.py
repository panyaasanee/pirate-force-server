r"""LANE-A / M2: the SHAPE of an answer to TriggerVital (0x1FB2) trigger id
2/3, with NO bytes in it yet, and with a THREE-TIER guard in front of it.

WHY THIS FILE EXISTS
--------------------
COO-DECISION `pf_bridge/notes_to_chief/20260906_1955_COO-DECISION-panya1910-
m2-path-A-server-answers-0x1FB2-LANE-A.md` item 4(b): "prepare the answer
point for TriggerVital trigger 2/3 in the M2 scenario so it can accept a
candidate frame -- it answers with an exact empty RuntimeRes today -- NO
guessed frame, NO self-sent EnterInstanceVital, NO level check, until UI
sends a candidate frame that cites a VA and a vital id."

Three rounds of attended evidence (all already on the bridge, cited in this
round's own file rather than re-measured here) say the same thing about
those two wire ids:

    R313 (`pf_bridge/notes_to_chief/20260905_0212_KA1A-R313-RESULTS-*`):
        ship never touched an island; no 0x1FB2 for id 2/3 this run at all.
    R318 (`pf_bridge/notes_to_chief/20260905_1319_KA1A-R318-RESULTS-*`):
        id 2 fired x3 (Prison Exile), id 3 fired x3 (Spice Paradise); this
        server answered every one with `no_responder bytes_out=0`
        (`lane_hooks/lane_a_island_trigger_log.py`'s own line); no window,
        no error, no disconnect, no scene change on the client.
    R322A (`pf_bridge/notes_to_chief/20260906_1909_KA1A-R322A-RESULTS-*`):
        same two ids, same three-each contact count, this server answered
        `exact empty RuntimeRes` every time (the wire-level reading of the
        same "we said nothing" fact R318 saw); still no window on screen.

WHAT THE BLOCK ACTUALLY IS -- CORRECTED, RE-234 IS THE OWNER OF THIS PARAGRAPH
--------------------------------------------------------------------------------
An earlier draft of this docstring wrote that the block is "not 'the client
refuses our frame' (we have never sent one)".  That sentence was already
refuted, by this lane's OWN closed ticket, before it was written -- recorded
here instead of quietly deleted, because the wrong version is the one a
future round would otherwise re-derive:

    `RE-234 CLIENT-RESPONSE-PATH-FOR-TRIGGERVITAL-1FB2-ISLAND-001`
    (`pf_bridge/CLIENT_RE_QUEUE.md`, CLOSED DONE/MIXED by LANE-A round
    `2mnd7b`; result letter `pf_bridge/notes_to_chief/20260904_1953_RE-234-
    RESULT-TRIGGERVITAL-NOOP-ID-ONLY-UNSAFE.md`)

    An earlier version of this citation also named a repro verifier,
    `pf_bridge/staged/re234_static_verify.py`, "PASS 18/18".  pf-adversary
    found no such path; re-measured this round with
    `git ls-tree -r --name-only origin/main | grep re234_static_verify` in
    the bridge clone: ZERO hits, `staged/` included.  A citation nobody can
    re-run is worse than no citation, so it is gone rather than softened.
    What survives below is measured from files that ARE in the tree.

item (1) measured the client's handler for a TriggerVital RESPONSE at
`[0x00710440,0x00710445)` = `B0 01 C2 04 00` = `mov al,1; ret 4`: a five-byte
success no-op that reads nothing and opens no UI.  LANE-A's own consumption
letter `pf_bridge/notes_to_chief/20260906_1939_LANE-A-R322A-CONSUMED-re234-
refutes-0x1FB2-reply-bg3001-tgr-is-the-door.md` claimed a control that keeps
that from being an empty-tag artifact, and NAMED THE WRONG ROWS: it read
`external/PF_PROTOCOL_REGISTRY.tsv:97,98,109,110,442` by line number, but
line 98 is TriggerVital itself (the subject, not a control) and line 442's
`GeneralUIHandleModule` carries handler_va `0x0073D360`, not this VA.
pf-adversary caught it.  The honest control is a whole-file count of the
handler_va column (field 8), re-measured this round in the bridge clone:

    awk -F'\t' 'NR>1 && $8=="0x00710440"' external/PF_PROTOCOL_REGISTRY.tsv \
        | wc -l
        -> 69     (of 519 DATA rows -- `wc -l` on the whole file says 520
                   because it counts the header, which is the error the
                   first version of this sentence shipped with.  TriggerVital
                   is one of the 69, so 68 OTHER classes are dispatched to
                   the very same five bytes.)

and the same VA in the SERIALIZER column (field 7) gives 19, which is what
says the two columns answer different questions.  0x00710440 is the single
most common `handler_va` in the whole table, and those 69 rows are very
nearly the client-to-server REQUEST set -- so this is not "some shared
helper", it is the client's DEFAULT HANDLER FOR VITALS IT NEVER RECEIVES.
That is the sentence to keep; the bare count was the weaker half of it.

The nature of the original citation error is worth naming too, because
naming it is what stops it recurring: it was a COLUMN CONFUSION, not random
rows.  `GeneralUIHandleModule`'s SERIALIZER really is this VA -- the old
citation read field 7 and reported it as field 8.  Two of the four rows it
named (`ChooseNPC`, `ChooseNPCByTableID`) were correct and got thrown out
with the wrong two.

which is a STRONGER reading than the wrong one it replaces, not a weaker
one: 68 unrelated classes sharing one `mov al,1; ret 4` is a shared stub by
any reading, where four hand-picked neighbours could have been coincidence.
`external/PF_SERIALIZER_FIELDS.tsv:1475-1486` shows real tags on both W and
R -- the client deserialises an inbound TriggerVital fine and then throws
the result away.

So the honest statement of the block, in the shape RE-234 left it:

  * "the original server answered 0x1FB2 WITH a 0x1FB2 frame" is DEAD.  A
    frame of that opcode cannot reach anything on screen through that stub.
  * What survives is the weaker form `pf_bridge/CLIENT_RE_QUEUE.md:644`
    already states: the reply is "some OTHER opcode, nobody knows which
    one" -- which is where `RE-265` is still parked.
  * Therefore this file remains a SLOT, and registering anything in it is
    still blocked -- but blocked for a MEASURED reason, not for "nobody has
    cited a frame yet".

`NO_ORIGINAL_CAPTURE:` for the wire-level version of that question: no
pcap/journal of the ORIGINAL (non-pirate) server's own reply exists on this
bridge.  Re-derived this round in the tree where those directories actually
live (`pf_bridge`) -- the previous version of this table was run in the
SERVER tree, where all four paths are absent, so its zero rows were
vacuously true and its two non-zero rows were wrong:

    gamedata/tables/          grep -rli "1fb2"                  -> 0 files
    external/                 grep -rli "1fb2"                  -> 1 file
                              (`PF_RUNTIME_CLASSMAP.tsv`, and the match is
                              the substring inside the VA `0x00AC1FB2`, not
                              the opcode; `PF_FIELD_VALIDATION.tsv`, named
                              by the old table, has ZERO hits)
    archive/                  grep -rli "1fb2"                  -> 10 files
                              widened to "1fb2|original.*capture|<the Thai
                              phrase for the original server, as spelled in
                              RE-234's own letter>"             -> 32 files
    notes_to_chief/consumed/  the same two greps                -> 38 files,
                                                                   47 files
    find . -iname "*.pcap"    -> 0 hits, in BOTH trees

Both counts are given because the widened pattern is the one the original
table claimed to have run, and it is the one that returns the bigger number;
neither is 0.  What those files are is LETTERS ABOUT 0x1FB2 -- the literal
string `0x1FB2` is the bulk of every hit (`archive/` 14 of 20 raw matches,
`consumed/` 98 of 99, counting the one lowercase spelling) -- not captures, which is the whole reason the
conclusion holds.  Kept from the previous
table because it survived re-derivation and is the load-bearing half: a
``find -iname "*original*"`` across `archive/` and the bridge root turns up
only `evidence_screens/REF_ORIGINAL_SERVER_*` and two PANYA-REFERENCE /
GT078-ADDENDUM letters -- screenshots and clips of the ORIGINAL server's
SCREEN.  Eyewitness, never wire.
Stating them as 0 was the dangerous version: a false evidence table under a
true conclusion, skipping exactly the two directories where RE-234's own
result letter lives.

So this module's registry starts, and stays this round, with BOTH trigger
ids' candidate slots empty.  Filling either one without a cited VA + vital
id from LANE-UI would be exactly the guessed frame item 4(b) forbids.

THE THREE-TIER GUARD (RE-234 item 3, and why the id alone is not enough)
---------------------------------------------------------------------------
RE-234 item (3) is a BOUNDED-NEGATIVE that lands directly on this module:
`GT-228` saw wire trigger id 3 BOTH at island contact AND during ordinary
sailing, so `lane_a_island_trigger_log.M2_OBSERVED_ISLAND_TRIGGER_IDS` is
"log-only, no BUILD_IMPACT" and is "an unsafe classifier if anyone uses it
to decide the world -- narrow its scope with scene/context first."

This module is the first non-log-only consumer of that map.  So it narrows,
in three tiers.  An earlier version of this sentence said the tiers were
"the same shape" as this lane's sibling `world_sea_edge_crossing.
crossing_target()` (COO-DECISION `20260905_1748` item 6).  That was too
strong and pf-adversary said so: that function REFUSES on two things (the
source scene, then the id's presence in its target table) and its third
stage RESOLVES a destination -- a stage that succeeds for both ids rather
than refusing anything.  What this module borrows from it is the argument
ORDER (scene first) and the fail-closed posture, not a third refusing tier;
tier 3 below has no counterpart there:

  TIER 1  SOURCE SCENE.  The session must be IN scene 126
          (`M2_ISLAND_CONTACT_SCENE_ID`) -- the one scene R318/R322A
          actually sailed.  This is not a general trigger-to-scene table.
  TIER 2  A PINNED WIRE ID.  The id must be one of
          `CANDIDATE_TRIGGER_IDS` (2, 3).
  TIER 3  A MEASURED ISLAND-CONTACT DISCRIMINATOR.  Something in the
          session's state, or in the frame, that separates "id 3 while
          touching an island" from "id 3 while sailing open water in the
          same scene".  `ISLAND_CONTACT_DISCRIMINATOR` names it.  It is
          ``None`` today because NOBODY HAS MEASURED ONE -- so tier 3
          refuses every call, and this lookup answers ``None`` for every
          (scene, id) pair even if a slot were filled.

Tier 3 is the point of this guard.  Without it, the day a slot is filled,
a player sailing open water in scene 126 fires id 3 and there is nothing in
the call signature that could refuse it.  With it, filling a slot is not
enough to make this module answer anything: someone must first measure what
makes the two cases different and name it here.  The open design question,
in one line, is therefore recorded rather than answered:

    what makes trigger id 3 at an island different from trigger id 3 in
    open water?

WHAT THIS MODULE IS
--------------------
The shape, not the bytes.  `CANDIDATE_TRIGGER_IDS` names which wire ids this
slot exists for -- the SAME wire ids `lane_hooks/lane_a_island_trigger_log.
M2_OBSERVED_ISLAND_TRIGGER_IDS` already keys its ISLAND override by (2, 3),
reused here rather than re-derived, per this lane's "reuse the encoder that
already ships" rule.  `_CANDIDATES` is a dict from each of those ids to
``None`` -- absent -- and `candidate_for_trigger_id()` is the one function
that reads it, returning whatever is registered UNCHANGED, or ``None``.
Nothing here builds, edits, or synthesizes a frame; there is nothing to
build from until a UI letter names one.

IMPORTING THIS MODULE IS NOT FREE -- SAID OUT LOUD
-----------------------------------------------------
`from .lane_hooks.lane_a_island_trigger_log import ...` imports the
`lane_hooks` PACKAGE, whose `__init__` runs `_discover()` at import time
(around 20 lane modules, 15 hook points, a block of `LANE_HOOK_REGISTERED`
lines on stderr, and it binds `lane_q_trigger_vital_dispatch`'s
process-global singleton).  So "this module is imported by nothing outside
its own test" is true of the CODE, and the import itself is still a
side-effecting act.  It is accepted here because re-deriving (2, 3) locally
would be the duplicated-constant this lane's rules forbid; it is named so
nobody reads "imported by nothing" as "costs nothing".

WHAT THIS MODULE DOES NOT CLAIM
--------------------------------
* NOT a send path.  Nothing here is imported by ``runtime.py`` and nothing
  here composes bytes onto the wire.  ``lane_hooks.fire()`` -- the function
  ``runtime.py``'s TRIGGER_VITAL branch actually calls -- is documented
  (``lane_hooks/__init__.py``, ``fire()``'s own docstring) to never return a
  value BY DESIGN: "hooks that need to hand something back to runtime.py are
  not what this point shape is for."  So wiring this registry's answer onto
  the wire is not a matter of chief editing the existing ``fire()`` call --
  see "THE SEAM, NAMED HONESTLY" below for what it would actually take.
* NOT an EnterInstanceVital sender.  This registry only ever answers the
  QUESTION "is a candidate registered for trigger id N"; nothing here
  decides to change a player's scene.
* NOT a level check.  ``min_level`` lives on the dock table
  (``world_island_dock_table.DestinationRow``) already; this module does not
  read or enforce it.
* NOT proof that the client accepts anything this server might send here.
  RE-234 measured the opposite for the 0x1FB2-answers-0x1FB2 shape (see
  above).  Filling a slot is a precondition for testing some OTHER opcode,
  not a substitute for testing it.
* NOT in the same number space as the dock table.  This module's ids are
  WIRE trigger ids (2, 3, as they arrive in the frame);
  ``world_island_dock_table.destination_for_trigger_id`` takes DOCK ids
  (153, 154).  RE-234 item (3) and `RE-265` both record that the wire id
  space and the catalog id space are not proven to be the same namespace,
  so the sibling module is a POSTURE precedent (fail closed on an unknown
  id), never an id source.

THE SEAM, NAMED HONESTLY (for chief, one round out)
-----------------------------------------------------
``runtime.py``'s TRIGGER_VITAL branch -- the one whose body spells
``lane_hooks.fire("vital_inbound_trigger_vital", ...)``, which is how to
find it, because the LINE NUMBERS this docstring used to carry had rotted
by the time anyone came back to check.  CORRECTED, BECAUSE THE FIRST
VERSION OF THIS SENTENCE OVERCLAIMED AND pf-adversary MEASURED IT: there
were FIVE such pins, not four, and the fifth (`_gm_warp_target_unknown_
reason`, cited far below) was NOT stale -- the citation this round deleted
as rotten was the one citation that still pointed at its subject.  The
four that had rotted all rotted the SAME way: they were exact when written
and every one of them drifted by +2 from one upstream two-line insertion.
So "pointing at unrelated statements" is what they do NOW; "four unrelated
rots" is not what happened, and the difference matters because a uniform
drift is what a line pin always does eventually, not an accident somebody
caused.  The branch always does:

    self.rx_frames += 1
    lane_hooks.fire("vital_inbound_trigger_vital", session=self,
                     payload=bytes(parsed.nested_payload))
    return []

and no subscribed hook can change WHAT that branch returns, because
``fire()`` is report-only by construction: it has no return value to read
and it swallows a failing hook.  One narrow exception, named here rather
than glossed over (pf-adversary finding 2 against
``pirate-force-server#951``): ``fire()`` catches ``Exception``, not
``BaseException`` (``lane_hooks/__init__.py``, the three ``except
Exception`` arms in and around ``fire()``), so a hook raising
``SystemExit``/``KeyboardInterrupt`` propagates out and the ``return []``
below it never runs at all.  That is inherited ``fire()`` behaviour shared
by every hook point in this package, not something this module ships --
this module subscribes to nothing and is imported by nothing outside its
own test -- but "always returns []" is the wrong words for it, so they are
not used.  The GM_RUN_GM_COMMAND_VITAL_ID branch right
above it has the identical shape (also always ``return []``) -- it is NOT
the contrast case.  The real contrast is the ``legacy.CREATE_ACTOR_VITAL``
branch a little further up, which builds its return list from a DIRECT call
(``self.foundation.create(...)``) and returns
``[("FOUNDATION_CREATE_COMMITTED", pc, frame, 0.10)]`` at
the single ``return [("FOUNDATION_CREATE_COMMITTED", pc, frame, 0.10)]``
in ``runtime.py`` -- ``FOUNDATION_CREATE`` is not an identifier in that
file, it is the head of that action-label string, and an earlier draft of
this paragraph named it as if it were the branch.  This package
already has a house shape for "a lane needs to hand a value back to
runtime.py without going through the void-returning hook registry": the
``census_composer``/``choose_npc_responder`` pattern
(``lane_hooks/__init__.py``) -- a small keyed registry, gated by
``module_production_allowed()``, that the call site consults and calls
DIRECTLY, never through ``fire()``.  So the honest one-line ask is not
"read fire()'s result" (it has none) but: a NEW direct-call point of that
same shape, keyed by (session scene id, wire trigger id), that
``runtime.py``'s TRIGGER_VITAL branch checks (after the existing ``fire()``
call, so the log-only hooks -- PLURAL: ``lane_a_island_trigger_log`` AND
``lane_q_trigger_vital_dispatch`` both subscribe to that point today --
still run unconditionally) and, only when
``candidate_for_trigger_id(scene_id, wire_trigger_id)`` answers non-``None``,
builds its return list from that ``CandidateFrame`` instead of always
returning ``[]``.  Not requested as a code change this round -- item 4(b)
forbids sending anything until UI's letter lands; recorded here so the
wiring is one paragraph chief can act on the day it does, not a rediscovery.

WHAT A CANDIDATE LETTER MUST CITE -- AND WHY VA + VITAL ID + BYTES IS NOT ENOUGH
----------------------------------------------------------------------------------
That branch returns 4-tuples, ``(label, pc, frame, delay)``
(the ``return [("<LABEL>", pc, frame, <delay>)]`` shape in ``runtime.py``;
``FOUNDATION_CREATE_COMMITTED`` is the one this paragraph is about).
``CandidateFrame`` carries three
things and NONE of them is ``pc``: ``va`` is a disassembly symbol in the
CLIENT binary, not a server-side program counter, and there is no label and
no delay in it either.  Whoever wires this seam would have to invent those
three values, which is precisely what item 4(b) forbids.  So they are part
of what the candidate letter must supply, not a detail for the wiring round:

    va + vital_id + frame   -- what `CandidateFrame` holds today
    label                   -- the action-label string for the return tuple
    pc                      -- the server-side pc that tuple is built at
    delay                   -- the seconds field, as measured, not chosen

Deliberately NOT added as fields with placeholder values: an empty string or
a 0.0 in a NamedTuple is a guess wearing a type.  Named here so the gap is
answered by the letter that fills the slot.

THE REGISTRY'S SHAPE, AND WHY BOTH SLOTS ARE STILL ``None``
--------------------------------------------------------------
``CandidateFrame`` carries what item 4(b) requires the candidate to cite: a
VA (the client function that PROVES this is the frame -- a string, e.g.
"sub_00ABCDEF"), the vital id the frame answers with, and the frame's own
bytes.  ``_CANDIDATES`` maps each of ``CANDIDATE_TRIGGER_IDS`` (2, 3) to
``None`` at import time and NOTHING in this module ever writes into it after
that -- and since `0945` NOTHING OUTSIDE IT CAN EITHER: the mapping an
importer sees is a ``MappingProxyType`` and the module refuses the
assignment (see `_FrozenTier3Module` at the bottom of this file).  Filling
one entry is NOT by itself enough to make this module answer: tier 3 also
has to accept the session's position, and that needs a reading, not a name.

WHERE TIER 3'S FACT IS SUPPOSED TO COME FROM, AND WHY THAT SOURCE IS STILL
NOT ENOUGH ON ITS OWN
-------------------------------------------------------------------------
The three-tier shape above was ratified by `COO-DECISION 20260907_0405`
(answering this lane's ASK-COO `20260907_0357`), which accepted item 3 whole
-- INCLUDING "tier 3 is `None` today, so every pair is refused" -- and
directed that the discriminator be sought in the client's own scene data,
in `Data/Scene/Save/Bg3001/Bg3001.tgr` (the client ships it with backslash
separators; Bg3001 IS scene 126, see
`world_m2_sea_scene_cast`).  `RE-273` measured that a `.tgr` record carries
a `u16` trigger ordinal, a script filename, and a fixed-size block holding
two f32 triples read as position and extent.  If the record for an ordinal
has a LOCAL extent box, that box is a candidate discriminator; if every
record's box is scene-wide, this route is closed and that is a real answer.
`RE-273`'s own field list for that block does not add up (it names 50 bytes
of a 52-byte block), so the two triples' OFFSETS are not settled either and
the ticket asks for the raw block bytes rather than trusting that list.
LANE-A round `tsdl0w` sent the ticket body for that measurement to LANE-K
(K assigns ticket numbers; A does not).

READ THIS BEFORE FILLING THE SLOT FROM THAT TICKET'S RESULT.  A `.tgr`
result is NOT sufficient by itself.  `RE-273` says so about its own finding,
and `RE-289` repeats it as its own nonclaim (1): neither proved that a
`.tgr` trigger ordinal is the same number as the wire trigger id this module
receives (`TriggerVital` 0x1FB2, tag 0x0F), and this project's rule is that
two numbers are not crosswalked because they are equal.

`RE-289` ANSWERED ON 2026-09-07T09:55+07:00 AND THIS ROUND FILLED THE SLOT,
SO HERE IS WHY THAT IS NOT THE STEP-SKIPPING THE PARAGRAPH ABOVE FORBIDS.
The sentence above was written when the plan was a table of `wire id -> the
box for that id`, which a `.tgr` ordinal cannot key without the crosswalk.
That is NOT the shape that was built.  ``ISLAND_EXTENT_BOXES`` is consulted
BY VALUE ONLY -- ``_position_is_inside_a_committed_extent`` iterates
``.values()`` and no code path in this file indexes it by a wire id -- so
the question tier 3 asks is "is this session standing inside ANY box the
measurement produced", which is answered by the session's own coordinates
and by geometry, and does not depend on which ordinal the box came from.
The wire id keeps exactly the job it had: tier 2, "is this one of the two
ids attended runs actually observed", which was never trusted on its own
and is the reason tier 3 exists at all.

WHAT THE CROSSWALK IS STILL NEEDED FOR, so a later round does not read the
paragraph above as "the ticket is unnecessary": knowing WHICH island a given
wire id refers to -- i.e. the destination -- is a per-id fact and still has
no measurement behind it.  This module does not answer that question today
and must not start by indexing the extent table.
[assumption of LANE-A - pending COO confirmation]: the ask is
`notes_to_chief/20260907_1022_LANE-A-ASK-COO-containment-discriminator-does-
not-need-the-ordinal-crosswalk.md`.  Reverting is one line -- put
``ISLAND_CONTACT_DISCRIMINATOR`` back to ``None`` -- and costs no caller,
because item 4(b) still leaves both candidate slots empty and nothing in
`src/` imports this module.
"""
from __future__ import annotations

import sys
from collections.abc import Mapping
from types import MappingProxyType, ModuleType
from typing import NamedTuple

from .lane_hooks.lane_a_island_trigger_log import M2_OBSERVED_ISLAND_TRIGGER_IDS
from .world_sea_edge_crossing import SEA_EDGE_SOURCE_SCENE_ID

# The wire trigger ids this slot exists for -- reused from the hook module
# that already keys its ISLAND override by these two ids (2 Prison Exile,
# 3 Spice Paradise), rather than re-derived here.  A tuple, not the dict
# itself, so this module cannot accidentally mutate the hook's own mapping.
CANDIDATE_TRIGGER_IDS: tuple[int, ...] = tuple(
    sorted(M2_OBSERVED_ISLAND_TRIGGER_IDS)
)

# Named refusals, same shape as `world_m2_survey_plan.scene_guard_reason`'s
# two named reasons and `world_island_dock_table.destination_for_trigger_id`'s
# fail-closed-on-an-unknown-id posture: a caller gets a NAMED reason for "not
# an M2 trigger id" rather than a bare False/None indistinguishable from "no
# candidate registered yet".
TRIGGER_ID_REFUSED_NOT_AN_INT = "TRIGGER_ID_REFUSED_NOT_AN_INT"
TRIGGER_ID_REFUSED_NOT_M2 = "TRIGGER_ID_REFUSED_NOT_M2"

# Named refusal for the TEST-ONLY `registry=` parameter of the two lookups
# below.  It is deliberately LOUD (a raise), not fail-closed like the wire
# input above, and the two postures are not in tension: `wire_trigger_id`
# arrives from the network, so an unexpected value there is a fact about the
# world and must never crash a session; `registry` can only ever be handed in
# by a test in this repo, so an unexpected value there is a fact about the
# TEST, and swallowing it would hide the bug behind a plausible `None`.
# Raising here is what makes `candidate_for_trigger_id`'s "never raises on
# wire input" claim checkable instead of merely asserted -- pf-adversary's
# finding 1 against `pirate-force-server#951` was that the old docstring said
# "Never raises" full stop while `registry=[]` raised a bare AttributeError.
REGISTRY_REFUSED_NOT_A_MAPPING = "REGISTRY_REFUSED_NOT_A_MAPPING"

# TIER 1.  The one scene R318/R322A actually sailed while ids 2 and 3 were
# observed.  IMPORTED from this lane's sibling rather than re-typed: the
# comment here used to say "same constant" while the file typed `126` a
# second time, which pf-adversary pointed out is the one spelling of "same
# constant" a rename cannot keep true.  Both modules refuse outside this
# scene rather than acting as a general trigger-to-scene table, so they are
# the same FACT (which scene the M2 sea leg is sailed in), not merely two
# variables that happen to hold the same number today.
M2_ISLAND_CONTACT_SCENE_ID = SEA_EDGE_SOURCE_SCENE_ID

# Two named reasons, not one.  `world_m2_survey_plan.scene_guard_reason` was
# split this way by an earlier pf-adversary round for a reason this module
# had not yet paid: a caller passing a scene id of the wrong TYPE has a bug
# of a different shape than a caller standing in the wrong scene, and
# collapsing them means `"126"` off a TEXT column or a JSON round-trip is
# reported forever as "you are in the wrong scene" when the truth is "that
# is a string".
SCENE_REFUSED_NOT_AN_INT = "SCENE_REFUSED_NOT_AN_INT"
SCENE_REFUSED_NOT_THE_SEA_SCENE = "SCENE_REFUSED_NOT_THE_SEA_SCENE"

# TIER 3.  The NAME of the measured fact that separates "wire trigger id 3
# while touching an island" from "wire trigger id 3 while sailing open water
# in the same scene".  `None` meant NOBODY HAD MEASURED ONE, which is the
# state RE-234 item (3) left this project in: `GT-228` saw id 3 in both
# situations, so the id alone is "an unsafe classifier if anyone uses it to
# decide the world".
#
# IT IS NO LONGER `None`.  `RE-289` answered on 2026-09-07T09:55+07:00 (the
# letter is named in `RE289_RESULT_LETTER` below): the two ordinals this
# lane asked about exist in `Bg3001.tgr` as POINT BOXES -- squares under 11%
# of the scene frame on both axes -- and not as scene-wide regions.  So the
# fact tier 3 was waiting for is "is this session's position inside one of
# the boxes that measurement produced", and the name below says exactly
# that and nothing wider.
#
# WHAT THE NAME DOES NOT CLAIM (both are `RE-289`'s own nonclaims, and this
# module is the place they have to survive):
#   * NOT "the boxes are islands".  What was measured is a trigger box that
#     coincides with a `BGFX0041` effect marker.  Calling that an island is
#     an interpretation; the name says `POINT_BOX_CONTAINMENT`, so a later
#     round cannot read an island claim out of a constant.
#   * NOT "the `.tgr` ordinal is the wire trigger id".  See
#     `ISLAND_EXTENT_BOX_ORDINALS` for the crosswalk that is still open, and
#     note that this table is consulted BY VALUE ONLY -- its keys never meet
#     a wire id.
#
# Setting this to a string is a claim that such a fact was measured and is
# enforced at the call site.  Since `0945` it is also enforced by the house:
# only an RE result letter whose git handwriting is checkable may say an
# extent was measured; a lane round COPIES numbers, it does not certify
# them.  This assignment copies `RE-289`.
ISLAND_CONTACT_DISCRIMINATOR: str = "RE-289_BG3001_TGR_POINT_BOX_CONTAINMENT"

# The letter this module copied its numbers out of, and its sha256 as
# published on `origin/main` of the bridge at the moment of the copy.  Both
# are here so a reader can re-derive the table without trusting this file,
# and so the test file can refuse the table when the letter is gone --
# COO-DECISION `20260907_0945` item 3, "a table with no letter behind it is
# a tier-3 refusal, not a pass with a warning".
RE289_RESULT_LETTER = (
    "20260907_0955_RE-289-RESULT-ordinal-2-and-3-exist-as-point-boxes-"
    "discriminator-is-real.md"
)
RE289_RESULT_LETTER_SHA256 = (
    "41f0a1a3a614602f1dab8890c7b996916840ed2b3e0b7be84a0fbe6e69a77f4f"
)
# The two artifacts `RE-289` hashed for itself, carried so a later round can
# tell "the letter changed" apart from "the client data changed".
RE289_BG3001_TGR_SHA256 = (
    "e0022e94e6b780cd0d364ec83e328c5f76b7e1215daf57cc24b51e93153a525f"
)

CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED = (
    "CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED"
)
CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED = "CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED"
CONTACT_REFUSED_EVIDENCE_OF_ANOTHER_DISCRIMINATOR = (
    "CONTACT_REFUSED_EVIDENCE_OF_ANOTHER_DISCRIMINATOR"
)
CONTACT_REFUSED_OPEN_WATER = "CONTACT_REFUSED_OPEN_WATER"


# THE KEYS OF THE EXTENT TABLE ARE `.tgr` FILE ORDINALS, NOT WIRE TRIGGER
# IDS, AND THE DIFFERENCE IS THE WHOLE REASON THIS CONSTANT HAS A NAME.
# `RE-289` nonclaim (1): nothing has shown that ordinal 2 in
# `Bg3001.tgr` is the id the client puts in a `TriggerVital 0x1FB2` tag
# `0x0F`.  They are equal today by coincidence of numbering, which is
# exactly the shape of accident this file exists to refuse -- so the
# containment test iterates `.values()` and NEVER indexes by a wire id.  If
# a later round wants a per-id box it needs the crosswalk ticket first, not
# a `[wire_trigger_id]` on this table.
ISLAND_EXTENT_BOX_ORDINALS = (2, 3)

# HOW A ROW WAS DERIVED FROM THE LETTER, once, here, so the arithmetic is
# auditable instead of being three transcribed numbers:
#
#     x0 = pos_x - extent_x / 2      x1 = pos_x + extent_x / 2
#
# i.e. `extent` is read as the box's FULL WIDTH.  THE LETTER DOES NOT SAY
# WHETHER IT IS FULL WIDTH OR HALF WIDTH.  Full width is the smaller box and
# therefore the fail-closed reading: if the truth is half width, this table
# refuses sessions that were really in contact (a miss, which shows up as
# "the trigger did nothing"), whereas the other guess would accept sessions
# in open water (a false island, which is the failure M2 must never have).
# `RE-289`'s own percentages are computed as `extent / 18750` on both axes,
# which is consistent with either reading and so does not settle it.
# [assumption of LANE-A - pending COO confirmation] -- the question is in
# `notes_to_chief/20260907_1022_LANE-A-TO-K-re-ticket-body-tgr-extent-is-
# full-or-half-width.md`; reverting is doubling the six numbers below.
ISLAND_EXTENT_BOX_SOURCE = "RE-289 Bg3001.tgr block[0x34] +0x0E pos, +0x1A extent"

_ISLAND_EXTENT_BOXES: dict[int, tuple[float, float, float, float, float, float]] = {
    # ordinal 2: TELCHK_LV [02], pos (-5426.19, 5129.33, 86.01),
    # extent (2000, 2000, 500) -- 10.6% / 10.6% of the scene frame.
    2: (-6426.19, 4129.33, -163.99, -4426.19, 6129.33, 336.01),
    # ordinal 3: TELCHK_LV [03], pos (-1916.55, -6137.92, 86.02),
    # extent (1800, 1800, 500) -- 9.6% / 9.6% of the scene frame.
    3: (-2816.55, -7037.92, -163.98, -1016.55, -5237.92, 336.02),
}

# WHAT IS DELIBERATELY NOT IN THE TABLE, so that a later round reads a
# decision here instead of a gap:
#   * ordinal 1 (3000 x 2700 at 3098.2, 2207.5) is the third square box and
#     also passes the ticket's "< 20% on both axes" bar.  It is left out
#     because the ticket asked about ordinals 2 and 3 and the M2 pass
#     criteria name islands 2 and 3; adding a box nobody asked for widens
#     what the server will call contact.
#   * ordinals 6/7/8 and 68/69/70 are 37.2% on one axis and sit on the map
#     border.  `RE-289` reads them as edge walls.  They are the rows that
#     would turn "touching an island" into "sailing near the edge of the
#     map", which is the exact confusion `RE-234` item (3) reported.
ISLAND_EXTENT_BOX_CITATIONS: dict[int, str] = {
    2: "RE-289 (%s) ordinal 2 TELCHK_LV[02] pos -5426.19,5129.33,86.01 "
       "extent 2000x2000x500" % RE289_RESULT_LETTER_SHA256,
    3: "RE-289 (%s) ordinal 3 TELCHK_LV[03] pos -1916.55,-6137.92,86.02 "
       "extent 1800x1800x500" % RE289_RESULT_LETTER_SHA256,
}

# READ-ONLY TO EVERY IMPORTER -- COO-DECISION `20260907_0945` item 1.
# pf-adversary's repro for the tier-3 hole had three legs and this table was
# one of them: a caller that can write a box can decide that open water is
# an island, which is the one decision this module exists to keep away from
# callers.  A `MappingProxyType` refuses `[...] = `, `.clear()`, `.update()`
# and `.pop()`; the module-level freeze at the bottom of this file refuses
# the other spelling, `module.ISLAND_EXTENT_BOXES = {...}`.
ISLAND_EXTENT_BOXES: "Mapping[int, tuple[float, float, float, float, float, float]]" = (
    MappingProxyType(_ISLAND_EXTENT_BOXES)
)
CONTACT_REFUSED_NO_EXTENT_TABLE = "CONTACT_REFUSED_NO_EXTENT_TABLE"


class IslandContactEvidence(NamedTuple):
    """ONE SESSION'S RAW POSITION at the moment it sent the trigger, tagged
    with the name of the measurement it is to be judged against.  Tier 3's
    INPUT -- the thing this module had nowhere to put until this round.

    WHY THIS TYPE EXISTS.
    Before this round tier 3 was, in full, `if ISLAND_CONTACT_DISCRIMINATOR
    is None`.  pf-adversary measured what that means: setting the module
    constant to the EMPTY STRING -- a value whose plain meaning is "nothing
    was measured" -- unlocked all three tiers and produced a live frame, on
    `550a36d` and on `#993` alike.  Tier 3 was a NAME, not a CHECK.  And
    whatever `RE-289` comes back with is a fact about WHERE A SESSION IS,
    which a signature of `(current_scene_id, wire_trigger_id)` has nowhere
    to put -- so the first round to receive a discriminator would have faced
    a choice between growing the signature and simply assigning the name,
    and assigning the name is ONE LINE that passes every test in the file.
    THE SIGNATURE HAS TO GROW BEFORE THE FACT ARRIVES.

    WHY IT CARRIES A POSITION AND NOT A `bool`.
    The first version of this type this round wrote carried `in_contact:
    bool`, and pf-adversary broke it in one line: the CALLER decided the
    thing tier 3 exists to decide, so the module could only check that the
    caller had spelled its answer correctly.  A session sailing open water
    that hands in `in_contact=True` was accepted, and nothing in the module
    could disagree.  That is weaker than the defect it replaced by exactly
    one `import`, not by one measurement.

    So the reading carries what the SERVER ALREADY OWNS AND THE CALLER
    CANNOT INVENT -- the session's own coordinates -- and the CONTAINMENT
    DECISION STAYS INSIDE THIS MODULE, against ``ISLAND_EXTENT_BOXES``, a
    table of committed, auditable extents.  `RE-289`'s pass criteria are a
    position, an extent and a `block[0x34]` dump, i.e. a BOX; a box belongs
    in a table this file owns, not in an argument a caller supplies.

    ``discriminator``  the NAME of the measurement this reading is to be
                       judged against.  Must be exactly a ``str`` (not a
                       subclass) and must equal the module's
                       ``ISLAND_CONTACT_DISCRIMINATOR``, so a reading taken
                       under an older or different measurement cannot be
                       replayed against a newer one.  The exact-``str``
                       rule is not pedantry either: a ``str`` SUBCLASS whose
                       ``__ne__`` raises made the FIRST version of
                       ``_tier3_contact_reason`` raise, which is D1's bug
                       reappearing one round later in the code written to
                       fix it.
    ``x`` ``y`` ``z``  the session's position, exactly ``float`` or ``int``.
    ``source``         where the reading came from: a session field, a vital
                       id, an RE ticket.  Carried so an acceptance or a
                       refusal can be traced to something a person can check.

    NOTHING CONSTRUCTS ONE OF THESE TODAY, in `src/` or anywhere else --
    measured by a test in this module's test file that greps `src/` on every
    run.  ``ISLAND_EXTENT_BOXES`` IS NO LONGER EMPTY, though: `RE-289`
    answered on 2026-09-07T09:55+07:00, so a reading built by hand DOES now
    pass tier 3 when its position falls inside one of the two measured
    boxes.  What still refuses every caller is item 4(b): both candidate
    slots are empty, so the door frame is finished and there is no door
    behind it.

    `COO-DECISION 20260907_0845` ratified this shape (the letter asking was
    `notes_to_chief/20260907_0722_LANE-A-ASK-COO-tier3-signature-must-grow-
    before-re289-answers.md`), so the pending-confirmation tag this type
    carried is gone.
    """

    discriminator: str
    x: float
    y: float
    z: float
    source: str


class CandidateFrame(NamedTuple):
    """A candidate answer to TriggerVital trigger id 2 or 3, cited rather
    than guessed.

    ``va``          the client VA/function name LANE-UI's letter cites as
                    proof this is the frame the client expects (e.g. a
                    disassembly symbol or address string).  Never blank in a
                    real registration; this module does not check that --
                    the registration itself is the trust boundary, and
                    nothing here writes one.
    ``vital_id``    the vital id the answer frame is built from.
    ``frame``       the exact bytes.  Carried, never edited: this module's
                    whole job is to hand this back UNCHANGED, per item
                    4(b)'s ban on sending anything this lane invented.
    """

    va: str
    vital_id: int
    frame: bytes


# trigger id -> the candidate registered for it, or None.  BOTH entries
# start (and, this round, END) absent.  Filling one in without a cited VA +
# vital id from LANE-UI is exactly the guessed frame COO-DECISION 1955 item
# 4(b) forbids -- see the module docstring's "WHY THIS FILE EXISTS".
__CANDIDATES: dict[int, CandidateFrame | None] = {
    trigger_id: None for trigger_id in CANDIDATE_TRIGGER_IDS
}

# READ-ONLY TO EVERY IMPORTER, for the same reason as `ISLAND_EXTENT_BOXES`
# and by COO-DECISION `20260907_0945` item 1: this was the third leg of
# pf-adversary's repro.  A caller that can write a slot can make this module
# hand the client bytes nobody cited, which is the guessed frame item 4(b)
# forbids.  The writable dict is name-mangled (`_world_m2_trigger_vital_
# response__CANDIDATES` in `vars(module)`) so that an importer reaching for
# it has to spell out that it is doing so; that is a speed bump, not a lock,
# and the nonclaim at the bottom of this file says so.
_CANDIDATES: "Mapping[int, CandidateFrame | None]" = MappingProxyType(__CANDIDATES)


def _is_a_wire_int(value: object) -> bool:
    """The module's ONE answer to "did the wire hand us an integer".

    pf-adversary counted FOUR spellings of this question in this one file
    and killed none of them with a test: mutating `type(x) is not int` to
    `isinstance(x, int)` left all 32 tests green, and the docstring reason
    given for the strict spelling (`126.0 == 126`) does not actually
    separate the two -- `isinstance(126.0, int)` is False as well.  The only
    input the two spellings disagree on is an `int` SUBCLASS, and the file
    disagreed with ITSELF about that: an `IntEnum` valued 126 was refused as
    a scene id and accepted as a trigger id in the same module.

    THE PREVIOUS ROUND UNIFIED THEM ON THE WRONG SPELLING AND IT SHIPPED.
    `#993` landed `isinstance(value, int) and not isinstance(value, bool)`,
    borrowed from `world_m2_survey_plan`, which is NOT on this call path.
    THERE IS NO CALL PATH TO BORROW FROM, AND THAT MATTERS.  A repo-wide
    grep for this module and for `candidate_for_trigger_id` finds this file
    and its test file and nothing else -- no `src/`, no `gm/`, no
    `lane_hooks/`, no `tools/` -- so "the spelling used by the modules on
    this call path" was a claim with no call path behind it.  The honest
    comparison is narrower and still decides the question:
    `world_sea_edge_crossing.crossing_target`, the sibling this file's own
    guards cite and whose scene constant it imports, refuses int subclasses
    (`type(x) is not int or isinstance(x, bool)`), and the isinstance
    spelling made the STRICTER of this file's two guards LOOSER.
    (`runtime.py`'s `_gm_warp_target_unknown_reason` was cited here as a
    second witness in the previous round's
    first draft; pf-adversary measured it and it is NOT one -- that
    function's own docstring says it never gates anything and only names
    things after the fact.  A diagnostic label
    is not a guard, and stacking the two was mixing evidence layers.
    Withdrawn rather than quietly dropped.)
    The house has both spellings in it -- roughly 283 `type(...) is int` and
    90 `isinstance(..., int)` across `src/` -- so "one spelling" here is a
    claim about THIS FILE, not about the project.  In particular
    `world_m2_survey_plan.py:526`, which the comment above
    `SCENE_REFUSED_NOT_AN_INT` cites as the model for splitting the two
    named refusals, still spells the type test `isinstance`.  The SPLIT is
    what is borrowed from it; the PREDICATE is not, and this paragraph is
    here so the next reader does not "unify" them back the wrong way.
    pf-adversary measured both halves and this lane reproduced both:

      * it made `candidate_for_trigger_id` RAISE, falsifying that function's
        own "never raises on either argument" promise.  `type(x) is not int`
        short-circuits before `__eq__` ever runs; `isinstance` does not, so
        an `int` subclass whose `__eq__` raises reached the comparison:

            class Boom(int):
                def __eq__(s, o): raise ValueError("wire said no")
                def __hash__(s): return 0

            crossing_target(Boom(126), 3)         -> None      (sibling)
            candidate_for_trigger_id(Boom(126),3) -> ValueError (#993)

      * it let a scene that is NOT 126 pass TIER 1 and, with a discriminator
        set, produce a real frame -- an `int` subclass whose `__eq__` just
        returns True satisfies `current_scene_id != M2_ISLAND_CONTACT_
        SCENE_ID` for ANY value.

    So the docstring sentence that spelling was landed with -- an int
    subclass "IS the integer, and nothing downstream can tell the
    difference" -- is measurably FALSE in this very file: `__eq__` decides
    tier 1 and tier 2, and `__hash__` decides the registry lookup.  Both
    are attacker-chosen on a subclass and neither is on an `int`.

    THE SPELLING IS `type(value) is int`, and A6's split of the two named
    scene refusals -- which nobody questioned -- is kept.  So:

      * `126.0`, `"126"`, `None`, `b"\x02"`, `[]`, `object()` -> False.
        A float is refused even though `126.0 == 126`, which is the whole
        reason a bare equality check is not enough.
      * `True`/`False` -> False, and no separate `bool` clause is needed to
        say so: `type(True) is bool`, not `int`.  The clause the previous
        spelling required is gone because the predicate no longer admits
        subclasses at all.  A test still pins the ANSWER for `bool`, since
        that answer is what callers depend on, not the way it is reached.
      * an `IntEnum` or other `int` subclass valued 126 -> False, the same
        answer in BOTH guards.  This is a real loss of convenience for an
        honest caller holding an `IntEnum`, and it is the price: a session
        hands these two arguments in off the wire, so the guard is written
        against a hostile value, not a tidy one.  An honest caller with an
        enum writes `int(x)` at the boundary, which is where the widening
        should be visible.

    `tests/test_world_m2_trigger_vital_response.py` pins this with two int
    subclasses -- one whose `__eq__` raises, one whose `__eq__` returns
    True -- because a plain `int` subclass valued 126 separates the two
    SPELLINGS but only these two separate their CONSEQUENCES.
    """
    return type(value) is int


def _trigger_id_guard_reason(wire_trigger_id: object) -> str | None:
    """``None`` when ``wire_trigger_id`` is one of ``CANDIDATE_TRIGGER_IDS``;
    otherwise the NAMED reason it is not.

    PRIVATE, AND THE LAST NAME IN THIS FILE TO BECOME SO.  It shipped
    public, answering candidacy from the wire id ALONE, which is exactly
    what `COO-DECISION 20260907_0405` item 1 forbids.  The test that exists
    to catch that shape --
    ``test_no_public_name_answers_candidacy_from_the_wire_id_alone`` --
    did catch it, and the round that wrote the test spent the finding on an
    ``allowed_id_only`` allowlist naming this function.  An allowlist entry
    is not a closed hole: it makes the ONE offender legal by name while
    leaving the door it came through open, and the next offender only has
    to be added to the same set.  The leading underscore is the fix, the
    allowlist is deleted, and the rule now has no exceptions at all.

    Nothing outside this module called it (measured across both
    repositories at rename time: this file and its test file, no ``src/``,
    no ``gm/``, no ``lane_hooks/``, no ``tools/``), so the rename cost no
    caller.  ``answer_guard_reason`` -- which takes the scene id first --
    remains the public way to get this refusal by name.

    Same strict-on-type posture as ``world_m2_survey_plan.scene_guard_
    reason`` (bool rejected explicitly, since it subclasses ``int`` in
    Python and would otherwise pass a stray boolean off as a trigger id).
    Never raises.
    """
    if not _is_a_wire_int(wire_trigger_id):
        return TRIGGER_ID_REFUSED_NOT_AN_INT
    if wire_trigger_id not in CANDIDATE_TRIGGER_IDS:
        return TRIGGER_ID_REFUSED_NOT_M2
    return None


def scene_guard_reason(current_scene_id: object) -> str | None:
    """``None`` when ``current_scene_id`` IS ``M2_ISLAND_CONTACT_SCENE_ID``;
    otherwise the NAMED reason it is not -- ``SCENE_REFUSED_NOT_AN_INT`` for
    a value of the wrong type, ``SCENE_REFUSED_NOT_THE_SEA_SCENE`` for an
    integer scene the player is simply not standing in.

    TWO reasons, not one.  This guard used to answer
    ``SCENE_REFUSED_NOT_THE_SEA_SCENE`` for both, which meant ``"126"`` --
    the shape a scene id has after a TEXT column or a JSON round-trip --
    was reported forever as "wrong scene" when the truth is "wrong type",
    and a caller reading the reason would go looking at the player's
    position instead of at its own serialisation.  ``world_m2_survey_plan``
    was split the same way, by an earlier pf-adversary round, before this
    module copied the collapsed version.

    Type test is ``_is_a_wire_int`` -- see there for why the file now has
    one spelling of that question instead of four, and for what changed
    (an ``int`` subclass such as an ``IntEnum`` valued 126 is now accepted
    here, as it already was in ``_trigger_id_guard_reason``).  Never raises.
    """
    if not _is_a_wire_int(current_scene_id):
        return SCENE_REFUSED_NOT_AN_INT
    if current_scene_id != M2_ISLAND_CONTACT_SCENE_ID:
        return SCENE_REFUSED_NOT_THE_SEA_SCENE
    return None


def _position_is_inside_a_committed_extent(
    x: float,
    y: float,
    z: float,
    boxes: "Mapping[int, object] | None" = None,
) -> bool:
    """``True`` when ``(x, y, z)`` falls inside ANY box in ``boxes``, which
    defaults to ``ISLAND_EXTENT_BOXES``.  ``False`` when the table is empty.

    ``boxes`` EXISTS FOR THE TESTS AND FOR NOTHING ELSE, and it is on a
    PRIVATE function on purpose -- COO-DECISION `20260907_0945` item 2 says
    the test suite must stop being a working demonstration of the hole it is
    testing.  Before this round a test reached the empty-table and
    malformed-row refusals by WRITING the module's own table, which is the
    exact move item 1 now forbids an importer from making; the table is a
    ``MappingProxyType`` since this round, so that route is closed and this
    parameter is the replacement.  ``answer_guard_reason`` and
    ``candidate_for_trigger_id`` DO NOT forward it and take no such
    argument: a wire caller must never be able to supply the boxes it is
    judged against.

    The boxes are inclusive on both bounds and are stored
    ``(x0, y0, z0, x1, y1, z1)`` with each low bound <= its high bound; a
    row written the other way round simply never contains anything, which
    is the fail-closed direction.

    A row of the WRONG ARITY is skipped, not unpacked.  That hazard was
    named only for reversed bounds until pf-adversary measured the other
    one: a five-field typo raised ``ValueError: not enough values to
    unpack`` straight out of ``candidate_for_trigger_id``, whose caller is
    promised a named refusal and never an exception.  `RE-289`'s answer is
    expected to arrive as hand-transcribed floats, so a typo in this table
    is the likely failure, not the exotic one -- and skipping the row is
    the same fail-closed direction reversed bounds already take.
    """
    table = ISLAND_EXTENT_BOXES if boxes is None else boxes
    for box in table.values():
        if type(box) is not tuple or len(box) != 6:
            continue
        x0, y0, z0, x1, y1, z1 = box
        if x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1:
            return True
    return False


_UNSET = object()


def _tier3_contact_reason(
    island_contact: object,
    *,
    discriminator: object = _UNSET,
    boxes: "Mapping[int, object] | None" = None,
) -> str | None:
    """TIER 3 ALONE, AND PRIVATE FOR THE SAME REASON
    ``_tier2_id_is_a_candidate`` IS: a caller able to ask tier 3 by itself
    would be one import away from answering the world with a fact that never
    passed tiers 1 and 2.  ``answer_guard_reason`` is the only caller.

    Five refusals, in this order, each a different thing being wrong:

      1. ``ISLAND_CONTACT_DISCRIMINATOR`` is unmeasured -- ``None``, any
         non-``str``, or a string that is empty or ALL WHITESPACE.  THE
         BLANK CASE IS NOT PEDANTRY: `""` was measured unlocking all three
         tiers on both `550a36d` and `#993`, and `""` is precisely the value
         that asserts nothing was measured.  `"   "` was then caught by this
         round's OWN test after the first version of this check was written
         `if not ISLAND_CONTACT_DISCRIMINATOR`, which a whitespace string
         passes.
      2. the reading is missing, or is not EXACTLY an
         ``IslandContactEvidence``, or its fields are not exactly the types
         they are annotated as.  ``type(...) is`` throughout, NOT
         ``isinstance``: this is the same POSTURE the file spends sixty
         lines explaining in ``_is_a_wire_int``, though deliberately not
         the same predicate -- coordinates admit ``float`` and that one
         does not, so the file has two type tests on purpose and the claim
         that ``_is_a_wire_int`` is its "ONE answer" is scoped to the wire
         INTEGERS of tiers 1 and 2 (pf-adversary read it as a claim about
         the whole file, which is how it was written; corrected here), and the first version of this
         function got it wrong in the round written to fix it -- a
         ``str`` subclass whose ``__ne__`` raised made step 3 raise, and an
         ``IslandContactEvidence`` SUBCLASS overriding ``discriminator``
         with a property walked straight through.  Both were measured by
         pf-adversary against this round's own draft.
      3. the reading names a DIFFERENT measurement than the one this module
         is currently enforcing.  Reached only once BOTH sides are exact
         ``str``, so ``!=`` here cannot dispatch to anything a caller wrote.
         THE WORD "BOTH" IS THE FIX, AND IT COST A THIRD SIGHTING OF THE
         SAME BUG.  Step 2 established it for the READING only; step 1 was
         still spelled ``isinstance(ISLAND_CONTACT_DISCRIMINATOR, str)``,
         so a ``str`` SUBCLASS assigned to the module constant reached step
         3 -- and Python tries the RIGHT operand's ``__ne__`` first when its
         type subclasses the left's, so that subclass's ``__ne__`` ran and
         could raise, falsifying this function's "never raises" promise
         from the side the two previous fixes never looked at.  Measured by
         pf-adversary against THIS round's committed head, having been
         measured twice before against two earlier drafts of the same
         function.  Step 1 is ``type(...) is not str`` now.  Not
         wire-reachable on the shipped tree, because the module's own
         constant is a plain ``str`` and is read-only to importers since
         `0945` -- a test pins both halves.  It stays because the NEXT
         measurement will be transcribed by hand the same way this one was.
      4. ``ISLAND_EXTENT_BOXES`` is empty -- NOBODY HAS COMMITTED AN EXTENT
         YET.  `RE-289` is numbered and open.  A discriminator NAME without
         a table behind it decides nothing, and this is the refusal that
         says so instead of quietly passing.
      5. the position is not inside any committed extent: the session is in
         OPEN WATER.  `RE-234` item (3)'s finding -- the wire id alone
         cannot tell an island from open water -- now decided HERE, from
         coordinates the server owns, rather than accepted from a caller.

    ``discriminator`` and ``boxes`` ARE TEST SEAMS ON A PRIVATE FUNCTION
    (COO-DECISION `20260907_0945` item 2).  Omitted, this function reads the
    module's own measured name and committed table -- which is what
    ``answer_guard_reason`` always does, since it forwards neither.  They
    exist because both of those are read-only to importers since this round,
    so the refusals for "nothing was measured" and "no table" are no longer
    reachable by writing module state, and a refusal nobody can exercise is
    a refusal nobody is testing.  ``_UNSET`` rather than ``None`` as the
    default, because ``None`` is itself one of the values a test needs to
    pass in: it is the state this module shipped in until `RE-289` answered.

    Returns ``None`` only when all five are satisfied.  Never raises on
    ``island_contact``, and unlike the first draft of this function that
    sentence is now pinned by a test that hands in an actual reading built
    from hostile field types, not only by non-readings that die at step 2.
    """
    measured = (
        ISLAND_CONTACT_DISCRIMINATOR if discriminator is _UNSET else discriminator
    )
    if type(measured) is not str or not measured.strip():
        return CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED
    if type(island_contact) is not IslandContactEvidence:
        return CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED
    if type(island_contact.discriminator) is not str:
        return CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED
    if any(
        type(coordinate) is not float and type(coordinate) is not int
        for coordinate in (island_contact.x, island_contact.y, island_contact.z)
    ):
        return CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED
    if island_contact.discriminator != measured:
        return CONTACT_REFUSED_EVIDENCE_OF_ANOTHER_DISCRIMINATOR
    table = ISLAND_EXTENT_BOXES if boxes is None else boxes
    if not table:
        return CONTACT_REFUSED_NO_EXTENT_TABLE
    if not _position_is_inside_a_committed_extent(
        island_contact.x, island_contact.y, island_contact.z, table
    ):
        return CONTACT_REFUSED_OPEN_WATER
    return None


def answer_guard_reason(
    current_scene_id: object,
    wire_trigger_id: object,
    island_contact: object = None,
) -> str | None:
    """``None`` when all THREE tiers pass; otherwise the NAMED reason the
    first failing tier gives, in tier order (scene, then id, then contact).

    Since `RE-289` the third tier can PASS: a reading tagged with the
    module's measured discriminator whose position falls inside one of the
    two committed boxes returns ``None`` from all three tiers.  A call that
    supplies no reading at all still gets
    ``CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED`` for the ONE input
    that gets that far (scene 126 with wire id 2 or 3) and a tier-1/tier-2
    reason for everything else.  Never raises, on any of the three
    arguments.

    ``island_contact`` IS THE THIRD ARGUMENT AND IT DEFAULTS TO ``None``,
    which is a refusal, not a pass -- see ``IslandContactEvidence`` for why
    the parameter exists at all and ``_tier3_contact_reason`` for the four
    ways it is refused.  The default keeps every call written before this
    round answering EXACTLY what it answered before WHILE THE DISCRIMINATOR
    IS UNMEASURED, which is every call today and every call any caller can
    make: tier 3 refused everything then and refuses everything now.  That
    is the honest form of the sentence.  An earlier draft of this docstring
    said the module's own suite passed "unedited", which its own diff
    refutes -- about fifteen call sites in the test file had to be given an
    `island_contact=` argument to keep reaching the code they were named
    for.  No PRODUCTION call changed, because there are no production
    callers.
    """
    scene_reason = scene_guard_reason(current_scene_id)
    if scene_reason is not None:
        return scene_reason
    trigger_reason = _trigger_id_guard_reason(wire_trigger_id)
    if trigger_reason is not None:
        return trigger_reason
    return _tier3_contact_reason(island_contact)


def _tier2_id_is_a_candidate(wire_trigger_id: object) -> bool:
    """TIER 2 ONLY, AND PRIVATE ON PURPOSE.  ``True`` when the wire id is one
    of ``CANDIDATE_TRIGGER_IDS`` -- which is NOT the same question as "may
    this module answer that id", and answering the second with this function
    is the id-only classifier `RE-234` item (3) exists to prevent.

    It was public and named ``is_candidate_trigger_id`` until pf-adversary
    pointed out, against the round that shipped the three tiers, that a
    module whose whole claim is "a filled slot is not sufficient" was
    exporting a yes/no view of tier 2 alone -- one import line away from the
    guard, and with a docstring inviting a caller to use it.  The tier
    discipline is a property of ``candidate_for_trigger_id`` and of nothing
    else in this file, so everything else that can answer from the wire id
    alone is private.  `COO-DECISION 20260907_0405` item 1 says the same
    thing as a rule: no overload that takes the id by itself.
    """
    return _trigger_id_guard_reason(wire_trigger_id) is None


def _table_for(
    registry: "Mapping[int, CandidateFrame | None] | None",
) -> "Mapping[int, CandidateFrame | None]":
    """This module's own ``_CANDIDATES`` when ``registry`` is ``None``, else
    ``registry`` itself -- after checking it really is a mapping.

    Raises ``TypeError(REGISTRY_REFUSED_NOT_A_MAPPING)`` otherwise, so a test
    that hands in a list or a string fails at the call with a named reason
    instead of deeper in with a bare ``AttributeError`` from ``.get``.

    The check is ``isinstance(registry, Mapping)``, NOT ``isinstance(...,
    dict)`` and NOT ``hasattr(registry, "get")``, and the annotation says
    ``Mapping`` to match: a ``MappingProxyType`` is accepted (it is a real
    read-only mapping) and a bare object that merely happens to own a
    ``.get`` attribute is refused (it is not).  Both halves are pinned by
    tests, because all three predicates agree on the easy inputs and only
    disagree on those two.
    """
    if registry is None:
        return _CANDIDATES
    if not isinstance(registry, Mapping):
        raise TypeError(REGISTRY_REFUSED_NOT_A_MAPPING)
    return registry


def candidate_for_trigger_id(
    current_scene_id: object,
    wire_trigger_id: object,
    *,
    registry: "Mapping[int, CandidateFrame | None] | None" = None,
    island_contact: object = None,
) -> "CandidateFrame | None":
    """The candidate registered for ``wire_trigger_id`` when ALL THREE tiers
    of ``answer_guard_reason`` pass, returned UNCHANGED; otherwise ``None``.

    ``current_scene_id`` comes FIRST, in the same argument order as this
    lane's ``world_sea_edge_crossing.crossing_target(current_scene_id,
    wire_trigger_id)``, and it is REQUIRED: RE-234 item (3) measured that the
    wire id on its own cannot tell an island from open water, so a lookup
    that took the id alone would be exactly the unsafe classifier that ticket
    warned about.  There is no id-only overload on purpose: this is the
    ONLY public function in this file that answers with a frame, and the
    only public one that takes the wire id at all takes the scene id
    first.  ``_tier2_id_is_a_candidate`` and ``_trigger_id_guard_reason``
    are tier-2 views, and the first of them is private for that reason.

    ``None`` covers every refusal without distinguishing them for the caller
    (ask ``answer_guard_reason`` if the difference matters): wrong scene,
    non-int or non-M2 id, no measured island-contact discriminator, or all
    three tiers passing and nothing registered for that id yet.  TODAY EVERY
    CALL IS REFUSED AT TIER 3, so this function answers ``None`` for every
    input, registered slot or not -- see ``ISLAND_CONTACT_DISCRIMINATOR``.

    ``registry`` defaults to this module's own ``_CANDIDATES`` and exists
    only so a test can pass a synthetic mapping without mutating production
    state -- never set from calling code outside a test.

    ``island_contact`` is TIER 3's reading and is passed straight through to
    ``answer_guard_reason``; ``None`` is a refusal, not a pass.  It sits
    FOURTH, after the test-only ``registry``, purely so that the third
    POSITIONAL argument keeps meaning what it meant before this round --
    a real caller supplies it by keyword and never supplies ``registry`` at
    all.  If COO accepts the shape (see ``IslandContactEvidence``), the
    round that receives a discriminator should consider moving it to third
    and making ``registry`` keyword-only, which is a change to test call
    sites and to nothing else.

    Never raises on ``current_scene_id`` or ``wire_trigger_id``: EVERY value
    of either, of every type, is answered with ``None`` rather than an
    exception, because both arguments come from a live session.  A
    ``registry`` that is not a mapping raises
    ``TypeError(REGISTRY_REFUSED_NOT_A_MAPPING)`` on purpose -- see that
    constant for why the arguments get opposite postures.

    THAT RAISE IS CONDITIONAL, AND ON THE SHIPPED MODULE IT CANNOT HAPPEN
    HERE AT ALL.  The three tiers are checked BEFORE the registry is
    touched, deliberately -- a malformed test registry must not be able to
    turn a refusal into a traceback -- and until `RE-289` answered, tier 3
    refused every input.  IT NO LONGER DOES, so the raise IS reachable
    through this function now: a caller that hands in a reading inside a
    committed box together with a non-mapping ``registry`` gets the
    ``TypeError``.  No production call site passes a registry at all.  Note
    that reaching the registry now takes TWO things, not one: a measured
    discriminator AND a matching reading whose position falls inside a
    committed extent; before this round the discriminator alone did it, and
    the sentence here said so.  So today
    ``candidate_for_trigger_id(126, 2, registry=[])`` answers ``None``, not
    ``TypeError``, and pf-adversary was right that the flat promise above
    read as though it did otherwise.  The raise becomes reachable through
    this function only once a discriminator is measured (the tests reach it
    by overriding the discriminator locally, which is why they see it);
    ``registered_count`` validates its registry unconditionally and is the
    place to look for the unconditional version of the same posture.  Three
    tests pin this ordering in each direction, so making the raise
    unconditional here would be an edit to them, not a bug fix.  No production
    call site passes a registry at all: repo-wide grep for this module's
    name finds importers only in its own test file, and the parameter is
    third and keyword-named in every call there (a POSITIONAL third argument
    would also reach it, which a grep for ``registry=`` alone would miss --
    so the claim rests on "nothing in `src/` imports this module", not on
    the keyword spelling).
    """
    if (
        answer_guard_reason(current_scene_id, wire_trigger_id, island_contact)
        is not None
    ):
        return None
    table = _table_for(registry)
    return table.get(wire_trigger_id)


def registered_count(
    registry: "Mapping[int, CandidateFrame | None] | None" = None,
) -> int:
    """How many of ``CANDIDATE_TRIGGER_IDS`` currently have a real candidate.
    0 on the shipped tree, for both ids: COO-DECISION `20260906_1955` item
    4(b) bans a frame this lane invented, and no LANE-UI letter has cited
    one.  That is why answering `RE-289` did not close M2 by itself.

    Scoped to ``CANDIDATE_TRIGGER_IDS``, NOT to the registry's own keys: a
    registry carrying an entry for some other id contributes 0, the same way
    ``candidate_for_trigger_id`` refuses a non-M2 id even when one is
    registered for it.  Pinned by a test, because iterating ``table``
    instead is the mutant that reads identically and is wrong.

    This is a COUNT OF SLOTS, and says nothing about whether any of them
    could be answered -- tier 3 refuses every lookup today regardless.

    ``registry`` is the same test-only parameter, with the same named raise
    on a non-mapping, as ``candidate_for_trigger_id``."""
    table = _table_for(registry)
    return sum(1 for trigger_id in CANDIDATE_TRIGGER_IDS if table.get(trigger_id) is not None)


# ---------------------------------------------------------------------------
# THE MODULE FREEZE -- COO-DECISION `20260907_0945` item 1.
# ---------------------------------------------------------------------------
class _FrozenTier3Module(ModuleType):
    """The class this module's own object is given at import time, so that
    ``world_m2_trigger_vital_response.ISLAND_CONTACT_DISCRIMINATOR = "x"``
    raises instead of silently rewriting what tier 3 enforces.

    WHY A CLASS SWAP AND NOT A CONVENTION.  pf-adversary's repro against the
    round that shipped the three tiers set the module constant to the empty
    string from a caller and got a live frame out the other side, twice, on
    two different heads.  The fix that round wrote was a better CHECK; a
    check cannot help when the attacker rewrites the thing being checked.
    The three names below are the three legs of that repro, and this is the
    only spelling of "an importer may not write them" that Python honours
    for the ordinary `module.NAME = value` form.

    WHAT IT DOES NOT STOP, stated here rather than left for the next round
    to discover: `module.__dict__["ISLAND_CONTACT_DISCRIMINATOR"] = ...` and
    `vars(module)[...] = ...` write the module dict directly and bypass
    every ``__setattr__`` Python has; so does re-executing the module body
    through ``importlib.reload``.  Nothing in a Python process can prevent
    those.  The freeze converts an ACCIDENT (an ordinary assignment, which
    is what the repro used and what a hurried round would write) into a
    named error, and leaves the deliberate act visible in a diff as a line
    no honest caller has a reason to contain.  That distinction is the whole
    claim -- see the wording COO ratified in `0945`: the guard exists to
    stop a DECISION being taken silently, not to stop a determined author.
    """

    __FROZEN = frozenset(
        {
            "ISLAND_CONTACT_DISCRIMINATOR",
            "ISLAND_EXTENT_BOXES",
            "_CANDIDATES",
        }
    )

    def __setattr__(self, name: str, value: object) -> None:
        if name in _FrozenTier3Module.__FROZEN:
            raise AttributeError(TIER3_STATE_IS_READ_ONLY % (name,))
        ModuleType.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        if name in _FrozenTier3Module.__FROZEN:
            raise AttributeError(TIER3_STATE_IS_READ_ONLY % (name,))
        ModuleType.__delattr__(self, name)


TIER3_STATE_IS_READ_ONLY = (
    "%s is tier-3 state and is read-only to importers "
    "(COO-DECISION 20260907_0945 item 1); a measured extent comes from an "
    "RE result letter, not from an assignment"
)

sys.modules[__name__].__class__ = _FrozenTier3Module
