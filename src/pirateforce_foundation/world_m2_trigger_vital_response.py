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
          `RE-298`'s measurement since 2026-09-07.  Until that day it was
          ``None`` because NOBODY HAD MEASURED ONE, and tier 3 refused
          every call.  It can pass now, for a reading tagged with that
          name and standing inside a committed box; this lookup still
          answers ``None`` for every (scene, id) pair whose slot is empty,
          which today is all of them.

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
That is NOT the shape that was built THAT ROUND.  ``ISLAND_EXTENT_BOXES``
was consulted BY VALUE ONLY -- the containment test iterated ``.values()``
and no code path in the file indexed it by a wire id -- so the question
tier 3 asked was "is this session standing inside ANY box the measurement
produced", answered by the session's own coordinates and by geometry alone.

AND THAT SHAPE HAD A HOLE IN IT, WHICH pf-adversary MEASURED (C1 against
`pirate-force-server#1052`): tier 2 checked the id, tier 3 checked the
geometry, and NOTHING CHECKED THAT THEY AGREED, so a reading taken inside
island 2 passed all three tiers while carrying wire id 3.  `RE-298` had by
then supplied the crosswalk the paragraph above demanded -- fifteen island
points over TWO id/ordinal pairings, and an open-water pair carrying a
third id with no box at all -- so tier 3
indexes the table by the wire id NOW, and the paragraph above is satisfied
rather than skipped.  See ``ISLAND_EXTENT_BOX_ORDINALS`` for the evidence
and for what a round would need to widen it back.

The wire id still keeps the job it had at tier 2, "is this one of the two
ids attended runs actually observed", which was never trusted on its own
and is the reason tier 3 exists at all.  What is new is that tier 3 no
longer answers a question the id is absent from.

WHAT THE CROSSWALK IS STILL NEEDED FOR, so a later round does not read the
paragraph above as "the ticket is unnecessary": knowing WHICH island a given
wire id refers to -- i.e. the destination -- is a per-id fact and still has
no measurement behind it.  This module does not answer that question today
and must not start by indexing the extent table.
The ask was
`notes_to_chief/20260907_1022_LANE-A-ASK-COO-containment-discriminator-does-
not-need-the-ordinal-crosswalk.md`, and it is no longer an open assumption.
THE PERMIT IS ``COO-DECISION 20260907_1441`` ITEM 4, NOT ``RE-298``:
`RE-298` supplied the crosswalk observation -- recorded in
`M2_WIRE_ORDINAL_CROSSWALK_OBSERVATIONS` -- and `COO-DECISION 20260907_1245`
section 1 says in red that the observation arriving does NOT by itself grant
the right to fill the name.  Evidence and authority are different layers and
this paragraph used to collapse them (pf-adversary D5).  What stays true is the
paragraph above it: the DESTINATION a wire id names is still unmeasured,
and this module still does not answer that.  Reverting remains one line --
put ``ISLAND_CONTACT_DISCRIMINATOR`` back to ``None`` -- and costs no
caller a frame, because item 4(b) leaves both candidate slots empty.

THIS MODULE HAS A PRODUCTION IMPORTER SINCE ROUND `p7rob4`, AND THE
SENTENCE THAT SAID IT DOES NOT IS GONE FROM BOTH PLACES IT APPEARED.
``lane_hooks/lane_a_island_trigger_log.py`` imports ``answer_guard_reason``
and ``IslandContactEvidence`` (lazily, inside ``guard_verdict_line`` --
that module imports ``M2_OBSERVED_ISLAND_TRIGGER_IDS`` back out of the
hook, and a top-level import here closes the cycle and kills both lanes'
hooks at boot) and PRINTS the verdict for every inbound ``0x1FB2`` frame.
Reverting the discriminator would therefore change what that console line
says -- from a possible ``verdict=PASS`` back to
``CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED`` on every frame -- and
nothing else.  NO FRAME IS COMPOSED OR SENT by that importer: the hook is
report-only by construction and its own tests assert ``actions == []``.
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

# Named refusal for the TEST-ONLY `registry=` parameter, which since this
# round lives only on the two PRIVATE twins below (`_candidate_for_trigger_id`
# and `_registered_count`) and on `_table_for` itself; the public pair take
# no such argument.  It is deliberately LOUD (a raise), not fail-closed like the wire
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
# `RE-298` ANSWERED ON 2026-09-07T14:26+07:00 AND THIS IS NO LONGER `None`.
# The crosswalk ticket that three documents named as the missing step is the
# ticket that answered, and it answered the exact question they scoped it to:
#
#   * the open-water frame of `GT-228` (`rx112`, wire id 35, ship at
#     (-872.04, 3175.01, 86.0)) is OUTSIDE all three committed island boxes,
#     on both the trigger position and the ship position.  So a box really
#     does separate "touching an island" from "sailing open water in the
#     same scene", which is the one thing `RE-234` item (3) said the wire id
#     alone could not do, and the one thing this constant was withheld for.
#   * `rx248` (wire id 2, ship at (-6231.26, 4871.58, 86.0)) is inside box
#     ordinal 2 AND ONLY THAT ONE, of all 52 boxes in the scene.
#   * the `.tgr` `ordinal` is a STORED u16 FIELD, not the record's position
#     in the file: the values run 1, 2, 3, 6, 7, 8, 13, ... so reading the
#     table by file order gives the wrong answer from the fourth record on.
#     The name string's own `[nn]` agrees with the binary field 52/52.
#   * the crosswalk is 15 measured points now, not 13, and it survived
#     CROSSING TRIGGER TYPES (`TELCHK_LV` and `OPNPLC_RAT_LV`) without a
#     relabel.
#
# WHAT THE NAME BELOW MEANS, EXACTLY.  It is the name of the MEASUREMENT a
# reading must have been taken by, not a description of a place.  A caller
# tags its `IslandContactEvidence` with this string to say "these
# coordinates were read the way `RE-298` read them"; tier 3 refuses any
# reading tagged with a different name, because a reading taken by an older
# measurement is a reading this module cannot grade.
#
# WHAT IS STILL FORBIDDEN, IN THE SAME BREATH.  `RE-298` nonclaim (1) is
# explicit: it did not measure WHAT THE SERVER SHOULD ANSWER when the frame
# arrives.  Naming the discriminator lets the module DECIDE "island or open
# water" from coordinates it owns.  It does not license a reply frame, and
# `NOW.md` still says: NO GUESSED FRAMES.
#
# AND ONE THING THIS OPENS THAT NOBODY SHOULD MISREAD, `RE-298`'s own
# emphasis: `TriggerVital 0x1FB2` is NOT an island-contact frame.  It fires
# for a ship entering ANY trigger box -- `rx112`'s id 35 is a real
# `OPNPLC_RAT_LV` box the ship was standing in, not a client misfire.  So
# "a 0x1FB2 arrived" must never be read as "the ship touched an island".
# The classification happens HERE, from the box table, or it does not
# happen at all.  That sentence is why filling this name is a step toward
# M2 and not the arrival of it.
ISLAND_CONTACT_DISCRIMINATOR: str | None = (
    "RE-298 Bg3001.tgr ordinal box contains the ship position"
)

# `RE-298`, the letter that unlocked the name above, and its sha256 on
# `origin/main` of the bridge at the moment of the copy -- same posture, and
# the same citation gate, as `RE289_RESULT_LETTER` below.
RE298_RESULT_LETTER = (
    "20260907_1426_RE-298-RESULT-open-water-frame-is-trigger-35-and-"
    "ordinal-is-a-stored-field.md"
)
RE298_RESULT_LETTER_SHA256 = (
    "683557d964c27c8da0821d895b7ebe1c092058d07cb397a46b8092783e106161"
)

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

# `RE-297` answered the question `RE-289` left open: how to READ the two
# vectors above.  Same runner, same read-only `.tgr`, same sha as the row
# just above, so the two letters are about one artifact and not two.
RE297_RESULT_LETTER = (
    "20260907_1505_RE-297-RESULT-pos-is-the-centre-and-extent-is-full-"
    "width.md"
)
RE297_RESULT_LETTER_SHA256 = (
    "38ac2661bc93b634bbc4542ae3a1bd0b05ff304acf0254224b5f19cad162c451"
)
# AND THE EVIDENCE STOPPED BEING SOMEBODY ELSE'S MACHINE.  This lane asked
# twice that `RE-289` be re-checkable from a clone; the answer is this
# letter, which carries the full 52-record dump verbatim.  Every number the
# comments above reason with -- the wall ordinals, their spacing, the 52
# `pos.z` values -- is in it, so the argument for the reading is auditable
# without a bridge machine.  It is a letter, not a data file, because
# `notes_to_chief/` is the only way new artifacts leave the bridge.
RE289_TGR_DUMP_LETTER = (
    "20260907_1510_RE-289-ARTIFACT-Bg3001-tgr-full-dump-verbatim.md"
)
RE289_TGR_DUMP_LETTER_SHA256 = (
    "7e7ad9b108868523b6729cb93ef79c7227b00ec5c22e1fa5b0a3bd6b89b6641a"
)

# HOW THE SIX NUMBERS OF A ROW COME OUT OF THE TWO VECTORS `RE-289` GIVES.
# A NAME, so that changing the reading is an edit to a constant a test reads
# rather than a silent re-transcription of three rows -- and so that the
# refuted readings are written down next to the surviving one instead of
# being remembered.  `RE-297` measured `CENTRE_PLUS_FULL_WIDTH`; the other
# two are what it ruled out, and they are kept because a table of boxes with
# no record of what they are NOT is a table nobody can check.
ISLAND_EXTENT_BOX_INTERPRETATION = "CENTRE_PLUS_FULL_WIDTH"
ISLAND_EXTENT_BOX_INTERPRETATIONS_REFUTED = ("MIN_CORNER_PLUS_FULL_WIDTH", "CENTRE_PLUS_HALF_WIDTH")

# THE ROWS THAT MUST NEVER BE IN THE TABLE, named rather than merely absent.
# `RE-289` read ordinals 6/7/8 and 68/69/70 as MAP-EDGE WALLS and `RE-297`
# proved it, by using them as the discriminator above: they are the records
# that tile the frame boundary.  A round that widened the selection rule and
# swept them in would turn "touching an island" into "sailing near the edge
# of the map" -- `RE-234` item (3)'s confusion, rebuilt.  A test keeps them
# out of both `ISLAND_EXTENT_BOX_ORDINALS` and the table itself.
ISLAND_EXTENT_BOX_EDGE_WALL_ORDINALS = (6, 7, 8, 68, 69, 70)

# The six edge-wall records, exactly as `RE289_TGR_DUMP_LETTER` prints them:
# ordinal -> (pos_x, pos_y, extent_x, extent_y).  They are HERE and not in
# `_ISLAND_EXTENT_BOXES` on purpose -- they are the evidence for how to read
# that table, not rows of it.  z is dropped: all six sit at 86.01 and the
# wall argument is a two-axis one.
ISLAND_EXTENT_EDGE_WALL_RECORDS: dict[int, tuple[float, float, float, float]] = {
    6: (-9084.53, 6462.22, 2000.0, 7000.0),
    7: (-9084.53, -325.84, 2000.0, 7000.0),
    8: (-9084.53, -7024.29, 2000.0, 7000.0),
    68: (-6027.36, -9416.95, 7000.0, 2000.0),
    69: (760.60, -9381.61, 7000.0, 2000.0),
    70: (7458.96, -9346.74, 7000.0, 2000.0),
}

# THE SECOND ENTRY FOR THE SIX ROWS ABOVE, and it is not a copy of them.
# A transposed digit is the likely typo in a hand-transcribed table -- this
# file says so about the box rows and then left these six unchecked: a
# mutant moving ordinal 7 from -325.84 to -352.84 passed the whole file.
# What catches it is the QUANTITY THE ARGUMENT ACTUALLY USES: the spacing
# between consecutive boxes along each wall.  `RE-297` published three of
# these four numbers independently (6698.45 / 6788.06 on the west wall,
# 6698.36 on the south), so this is a real second source and not the same
# entry written twice.  The fourth, 6787.96, is the one `RE-297` printed as
# 6787.97; this file quotes what it re-derived from the dump's own two
# coordinates.
ISLAND_EXTENT_EDGE_WALL_SPACINGS = (6698.36, 6698.45, 6787.96, 6788.06)

CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED = (
    "CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED"
)
CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED = "CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED"
CONTACT_REFUSED_EVIDENCE_OF_ANOTHER_DISCRIMINATOR = (
    "CONTACT_REFUSED_EVIDENCE_OF_ANOTHER_DISCRIMINATOR"
)
# NOT `CONTACT_REFUSED_OPEN_WATER`, which is what this constant was called
# until pf-adversary pointed out that the module cannot know it.  Every miss
# reaches this name: a session really in open water, but also a half-width
# truth, a transposed digit, a row skipped for bad arity, an ordinal the
# table left out, a berth 129 units off.  A later round reading
# "OPEN_WATER" concludes the `.tgr` route is dead; reading this one, it
# looks at the table.  Same split, same reason, as
# `SCENE_REFUSED_NOT_AN_INT` vs `SCENE_REFUSED_NOT_THE_SEA_SCENE`.
CONTACT_REFUSED_OUTSIDE_EVERY_COMMITTED_EXTENT = (
    "CONTACT_REFUSED_OUTSIDE_EVERY_COMMITTED_EXTENT"
)
# THE SHIP IS STANDING IN A MEASURED ISLAND, BUT NOT THE ONE ITS WIRE ID
# CLAIMS.  Split from the name above rather than folded into it, for the
# same reason `OPEN_WATER` was split off in the first place: a later round
# reading "OUTSIDE EVERY" concludes the ship was at sea and goes looking at
# the table, and here the table is right and the PAIR is wrong.  This is
# pf-adversary's C1 against `pirate-force-server#1052`, measured on the tree
# that shipped it: `answer_guard_reason(126, 3, reading@rx248)` returned
# `None` -- a pass -- while `rx248` is a position inside ordinal 2's box.
# Tier 2 asked "is the id 2 or 3", tier 3 asked "is the ship inside SOME
# island", and nothing asked whether they were the SAME island, so a ship
# berthed at Prison Exile could ask for and receive Spice Paradise's frame
# the day `_CANDIDATES` holds one.
CONTACT_REFUSED_INSIDE_ANOTHER_ISLANDS_EXTENT = (
    "CONTACT_REFUSED_INSIDE_ANOTHER_ISLANDS_EXTENT"
)
# THE ID PASSED TIER 2 AND THE TABLE HAS NO ROW FOR IT.  Not reachable on
# the shipped tree -- `CANDIDATE_TRIGGER_IDS` is (2, 3) and both have boxes
# -- and it exists because the two sets are maintained in different places
# from different letters, so the day one grows without the other this
# refuses instead of falling back to "any box", which is the behaviour
# being deleted.  Fail-closed in the direction the whole file leans.
CONTACT_REFUSED_NO_EXTENT_FOR_THIS_TRIGGER_ID = (
    "CONTACT_REFUSED_NO_EXTENT_FOR_THIS_TRIGGER_ID"
)


# THE KEYS OF THE EXTENT TABLE ARE `.tgr` FILE ORDINALS, AND SINCE `RE-298`
# TIER 3 IS ALLOWED TO READ THEM AS WIRE TRIGGER IDS.  THAT PERMISSION IS
# NEW AND IT IS THE ONLY REASON THIS ROUND'S CHANGE IS NOT THE ACCIDENT THE
# PARAGRAPH BELOW WAS WRITTEN TO REFUSE.
#
# WHAT THIS COMMENT SAID UNTIL THIS ROUND, kept because the reasoning was
# right on the day it was written: `RE-289` nonclaim (1) -- nothing had
# shown that ordinal 2 in `Bg3001.tgr` is the id the client puts in a
# `TriggerVital 0x1FB2` tag `0x0F`; they were equal by coincidence of
# numbering, which is the shape of accident this file exists to refuse; so
# the containment test iterated `.values()` and NEVER indexed by a wire id,
# and a later round wanting a per-id box was told to get the crosswalk
# first.
#
# THE CROSSWALK ARRIVED.  `M2_WIRE_ORDINAL_CROSSWALK_OBSERVATIONS` below is
# it, and it is not an argument from equal numbers: FIFTEEN island points
# from an attended session each fall inside the box of the ordinal whose
# number equals the wire id the client sent at that moment, and inside NO
# OTHER BOX -- and `RE-298`'s open-water pair (id 35) falls inside no
# committed box at all.
#
# THE COUNT, SAID EXACTLY, because the round that wrote the sentence above
# first wrote "seven pairings" and its own test refuted it before the
# commit: the observations carry TWO distinct id/ordinal pairings (2 and 3)
# across fifteen points, plus a third id, 35, that pairs with NO box.  Two
# pairings is not many, and the strength is not in that number -- it is
# that the two artifacts were produced three days apart by different
# parties from different sources, that no point is inside more than one
# box, and that a point exists which is inside NONE.  A crosswalk with no
# negative case is not one.  `test_the_crosswalk_this_change_rests_on_re_
# derives_from_the_tables` computes all three counts from the committed
# tables, so this paragraph goes red rather than stale.
#
# SO THE `.values()` SWEEP IS GONE, and what replaced it is narrower, not
# wider: tier 3 now asks whether the reported position is inside THE BOX OF
# THE ID THE SESSION SENT.  Every input that used to pass still has to pass
# the same geometry, and the inputs that used to pass on the WRONG island
# no longer do (`CONTACT_REFUSED_INSIDE_ANOTHER_ISLANDS_EXTENT`).  A round
# that ever wants to widen this back to "any box" needs a letter saying the
# crosswalk was wrong, not a convenience.
ISLAND_EXTENT_BOX_ORDINALS = (1, 2, 3)

# HOW A ROW WAS DERIVED FROM THE LETTER, once, here, so the arithmetic is
# auditable instead of being three transcribed numbers:
#
#     x0 = pos_x - extent_x / 2      x1 = pos_x + extent_x / 2
#
# i.e. `pos` is read as the box's CENTRE and `extent` as its FULL WIDTH.
# `RE-289` SAID NEITHER, so for three rounds both halves stood here labelled
# as guesses.  `RE-297` MEASURED THEM, out of the same file, and the reading
# above is the one it returned -- see `ISLAND_EXTENT_BOX_INTERPRETATION` for
# the constant and `RE297_RESULT_LETTER` for the letter.  The three
# paragraphs that used to argue the guess are gone, not rewritten; what
# replaces them is the discriminating record, because a reader who does not
# trust this file has to be able to redo the step, and now can:
#
#   THE DISCRIMINATOR IS THE MAP-EDGE WALLS, six records over two axes.
#   Ordinals 6/7/8 all sit at `x = -9084.53` with extent `(2000, 7000, 500)`
#   and are spaced 6788.06 and 6698.45 apart in y; ordinals 68/69/70 lie
#   along the south edge (y from -9416.95 to -9346.74) with extent
#   `(7000, 2000, 500)` and are spaced 6787.96 and 6698.36 apart in x --
#   THE SAME TWO NUMBERS, transposed with the axes.  (`RE-297` prints the
#   first as 6787.97; the value re-derived here from the dump's own two
#   coordinates is 6787.96, and one hundredth of a unit changes nothing in
#   the argument -- but this file quotes what it re-derived, not what it
#   was told.)
#   Both spacings are slightly UNDER 7000, so under CENTRE + FULL WIDTH the
#   three boxes tile the scene edge with a small overlap, which is how a
#   wall is laid.  Under MIN CORNER the same three leave 2392.6 units of the
#   south edge (and 3057 of the west edge) with no wall at all while
#   throwing a box of the same size away outside the frame -- the identical
#   mistake, at the same corner, on both axes, by coincidence.  Under HALF
#   WIDTH the boxes are 14000 wide and overlap by more than half, so laying
#   three of them means nothing.
#
#   RE-DERIVE IT FROM THE REPOSITORY, no bridge machine needed: the whole
#   52-record dump is `RE289_TGR_DUMP_LETTER` in the bridge repo, and
#   `test_the_edge_walls_tile_only_under_centre_plus_full_width` below
#   redoes this arithmetic from the numbers pinned in this file.
#
# WHAT `RE-297` DID NOT ANSWER, kept because a later round will want the
# distinction: it measured `Bg3001.tgr` and nothing else, so "centre + full
# width" is this scene's reading and not a claim about the `.tgr` format
# (its nonclaim 2).  And it could not tie a box to the real island collision
# outline -- scene 126 has no NavMesh or collision file in the repository at
# all (its answer to item 2) -- so a box remains the trigger volume the
# scene file draws, not the coastline.
#
# THE ONE PIECE OF EVIDENCE THAT LEANED THE OTHER WAY, kept so the next
# round does not rediscover it and re-open a settled question.  This lane
# noticed that scene 126's berths in `world_m2_sea_destination.py` --
# MARKER[17] (3050, 232, 90) and MARKER[18] (-5072, 4000, 90) -- fall
# OUTSIDE the full-width boxes in -y and inside the half-width ones.
# `RE-297` got the same two distances (625.5 and 129.33) and read them as
# evidence of nothing, for the reason this file had already written down
# next to them: AN ARRIVAL BERTH NEED NOT SIT INSIDE A DEPARTURE VOLUME.
# Six records agreeing across two axes outweighs two points that may not be
# about the same thing.

# THE THIRD GUESS, Z, IS ALSO ANSWERED AND IT FELL THE OTHER WAY.  This file
# used to reason that `extent_z` might be measured UPWARD from a floor
# anchor, "consistent with every record's `pos.z` being the scene minimum,
# 86.0".  THE PREMISE WAS FALSE, and the same dump refutes it: 32 of the 52
# records have `pos.z` ABOVE 86.0 (29 at 192.33, three at ~224.5).  `pos.z`
# is an ordinary coordinate like x and y, so the band below -- which does
# dip 250 units under the water no ship is beneath -- is the right one.
ISLAND_EXTENT_BOX_SOURCE = "RE-289 Bg3001.tgr block[0x34] +0x0E pos, +0x1A extent"

# WHICH ROWS EARN A PLACE, AND ON WHAT MEASUREMENT.  The rule is the
# TICKET'S OWN BAR applied to every record the letter returned: a
# `TELCHK_LV` box whose extent is under 20% of the scene frame ON BOTH AXES.
# `RE-289` returned exactly three of those -- ordinals 1, 2 and 3 -- and all
# three are here.
#
# THE FIRST DRAFT OF THIS TABLE HELD ONLY 2 AND 3, and pf-adversary named
# what that was: ordinal 1 (16.0% / 14.4%, and the CLOSEST of the three to
# its `BGFX0041` marker at 9.2 units) was excluded because "the M2 pass
# criteria name islands 2 and 3" -- and those criteria name WIRE ids 2 and
# 3 (R318: id 2 Prison Exile, id 3 Spice Paradise).  Selecting the rows by
# number-matching a wire id IS the ordinal-to-wire crosswalk, performed in
# the one file that says it performs none, and it would have told a ship
# standing at the letter's strongest island candidate that it was in open
# water.  Selection by the measurement's own shape does not do that.
#
# WHAT IS DELIBERATELY NOT IN THE TABLE: ordinals 6/7/8 and 68/69/70, which
# are 37.2% on ONE axis and sit on the map border.  `RE-289` reads them as
# edge walls, and they fail the both-axes bar the other three pass.  They
# are the rows that would turn "touching an island" into "sailing near the
# edge of the map", which is the exact confusion `RE-234` item (3) reported.
_ISLAND_EXTENT_BOXES: dict[int, tuple[float, float, float, float, float, float]] = {
    # ordinal 1: TELCHK_LV [01], pos (3098.22, 2207.49, 86.01),
    # extent (3000, 2700, 500) -- 16.0% / 14.4% of the scene frame.
    # THESE THREE DIGITS CHANGED WHEN `RE289_TGR_DUMP_LETTER` ARRIVED.  The
    # row was transcribed as (3098.2, 2207.5, 86.0) from the prose of
    # `RE-289`; the verbatim dump prints (3098.22, 2207.49, 86.01), and
    # ordinals 2 and 3 were already exact.  It moves a bound by two
    # hundredths of a unit and decides nothing differently -- it is here
    # because a table whose rows are rounded in different amounts is a table
    # nobody can check against its source, and now there is a source in the
    # repository to check against.
    1: (1598.22, 857.49, -163.99, 4598.22, 3557.49, 336.01),
    # ordinal 2: TELCHK_LV [02], pos (-5426.19, 5129.33, 86.01),
    # extent (2000, 2000, 500) -- 10.6% / 10.6% of the scene frame.
    2: (-6426.19, 4129.33, -163.99, -4426.19, 6129.33, 336.01),
    # ordinal 3: TELCHK_LV [03], pos (-1916.55, -6137.92, 86.02),
    # extent (1800, 1800, 500) -- 9.6% / 9.6% of the scene frame.
    3: (-2816.55, -7037.92, -163.98, -1016.55, -5237.92, 336.02),
}

# EVERY ROW CITES THE LETTER AND CARRIES ITS RAW MEASUREMENT, in a form a
# test re-parses and re-derives (COO-DECISION `20260907_0945` item 3).
# pf-adversary measured why the machine-readable half matters: a single
# transposed digit typed into BOTH the box and the test's own centre
# constant left all 81 tests green while the citation twenty lines below
# still read the correct number.  Double entry that shares a source is
# single entry, so the numbers below are the ones the test re-derives from
# and the box is what it checks against.
ISLAND_EXTENT_BOX_CITATIONS: dict[int, str] = {
    1: "RE-289 (%s) ordinal 1 TELCHK_LV[01] pos 3098.22,2207.49,86.01 "
       "extent 3000x2700x500" % RE289_RESULT_LETTER_SHA256,
    2: "RE-289 (%s) ordinal 2 TELCHK_LV[02] pos -5426.19,5129.33,86.01 "
       "extent 2000x2000x500" % RE289_RESULT_LETTER_SHA256,
    3: "RE-289 (%s) ordinal 3 TELCHK_LV[03] pos -1916.55,-6137.92,86.02 "
       "extent 1800x1800x500" % RE289_RESULT_LETTER_SHA256,
}

# ---------------------------------------------------------------------------
# THE SECOND MEASUREMENT.  THE SLOT ABOVE HAS BEEN WAITING FOR THIS ONE, AND
# IT WAS ALREADY IN THE REPOSITORY.
# ---------------------------------------------------------------------------
# This file has said, in the same words, for three rounds: "a SECOND,
# separate measurement has to tie that box to the wire before
# `ISLAND_CONTACT_DISCRIMINATOR` may name it.  A round that fills this slot
# from the `.tgr` table alone has skipped that step."  `RE-289` supplied the
# boxes and said so itself in its nonclaim (1).  The round that consumed it
# wrote a crosswalk TICKET as the way to get the other half.
#
# The other half is `GT-228` / R308, `OBSERVER_CONFIRMED 2026-09-04T13:22`,
# and it has been sitting in the bridge repository since 4 September with
# every number this needs.  This round went looking for a coordinate it
# expected to be missing, and found the letter's section (kho) decoding four
# of the six `0x1FB2` frames of the sea session into `trigger_xyz` and the
# ship's `TargetPos`, plus five HUD contact positions in its section (kor)
# table.  Thirteen points then; SEVENTEEN since `RE-298` decoded the two
# frames this letter left as ids without coordinates.  Each carries the wire
# id the client sent at that moment.
#
# WHAT IS MEASURED BELOW, AND IT IS A CROSSWALK, NOT A RESTATEMENT:  every
# one of the FIFTEEN ISLAND points falls inside the box of the ordinal
# whose NUMBER EQUALS THE WIRE ID, and inside NO OTHER BOX.  The other two
# are `RE-298`'s OPEN-WATER pair (wire id 35), and they fall inside NO
# COMMITTED BOX AT ALL, which is the half of the crosswalk that no round
# before `RE-298` could write down.  The two tables were
# produced three days apart by different parties from different artifacts --
# the boxes from `Bg3001.tgr` by the RE runner, the points from the wire and
# the screen by ka1-A with Panya at the client -- and neither was derived
# from the other.  That is the independence the slot was asking for.
#
# WHAT THIS PARAGRAPH SAID UNTIL `p7rob4`, AND WHY IT IS NOW HISTORY:
# it read "`ISLAND_CONTACT_DISCRIMINATOR` IS STILL `None` twenty lines up",
# and it was true on the day it was written.  It is not true now -- the
# constant is assigned `RE-298 Bg3001.tgr ordinal box contains the ship
# position` -- and two other paragraphs in this file (at the constant
# itself and in `_tier3_contact_reason`) had already been updated to say
# so, leaving the file contradicting itself for three rounds.
# pf-adversary D8 caught it three times before a round paid it.
#
# AND THE FIRST FIX OF IT REPEATED THE DEFECT INSIDE THE SENTENCE THAT
# ANNOUNCED THE FIX.  The replacement written earlier this round said the
# constant was at "line 509" and, one sentence later, that "a comment that
# names a distance ages worse than one that names a symbol, so this one
# names the symbol" -- while naming a line number.  It was already wrong
# when committed (514, because the same commit added five lines above it)
# and is wrong again now.  pf-adversary D2 of THIS round measured both.
# So this paragraph now names ONLY the symbol: search
# `^ISLAND_CONTACT_DISCRIMINATOR`.  No line number, no distance in lines.
#
# The decision the old paragraph was deferring HAS been taken: naming the
# discriminator is a decision, not a measurement, and it was routed through
# the crosswalk ticket exactly as written -- `RE-298` answered it, and the
# evidence that licenses the name is the table above plus
# `M2_WIRE_ORDINAL_CROSSWALK_OBSERVATIONS`.  The letter that asked is
# `notes_to_chief/20260907_1152_LANE-A-ASK-COO-*`.  What is still not done
# is downstream of the name, not the name: no frame reaches the client yet.
#
# AND ONE PREMISE THIS PROJECT HAS BEEN REPEATING IS REFUTED BY ITS OWN
# PRIMARY SOURCE.  `RE-234` item (3), quoted in `CLIENT_RE_QUEUE.md`, in
# `tickets/RE-289.md`, and beside `ISLAND_CONTACT_DISCRIMINATOR` in this
# file, says `GT-228` saw wire id 3 BOTH on island contact AND while sailing
# open water -- which is the whole reason the id alone was called an unsafe
# classifier.  `GT-228`'s results letter enumerates every `0x1FB2` frame of
# that session, three independent ways that agree (raw capture, EVENTS, and
# the lane hook's own console, six lines, no `UNPARSED`):
#
#     rx112 id=35   <- the open-water frame, sailing toward island 2
#     rx130 id=2  rx152 id=2  rx248 id=2
#     rx433 id=3  rx491 id=3
#
# The open-water frame carried id 35, not id 3.  There is no id-3 open-water
# sighting in `GT-228` at all.  This lane is NOT rewriting the shared
# documents on its own reading -- the ASK-COO letter carries it -- and the
# refutation changes nothing here today, because tier 3 refuses on the
# unmeasured discriminator either way.  It is recorded because a premise
# repeated in three places while its source says otherwise is a fact this
# project should stop paying for.
M2_WIRE_ORDINAL_CROSSWALK_LETTER = (
    "20260904_1331_KA1A-R308-RESULTS-gt228-pass-box-B-island-contact-fires-"
    "triggervital-id-2-at-prison-exile-and-id-3-at-spice-paradise-not-153-"
    "154.md"
)

# (label, wire trigger id the client sent, x, y, z).  Transcribed from the
# letter's sections (kho) and (kor), NOT recomputed from anything in this
# file.  `trigger` rows are the frame's own `trigger_xyz`; `ship` rows are
# the `TargetPos` carried in the same frame; `HUD` rows are the on-screen
# contact positions from the letter's table, which are the ones Panya
# watched happen.
M2_WIRE_ORDINAL_CROSSWALK_OBSERVATIONS: tuple[
    tuple[str, int, float, float, float], ...
] = (
    ("rx130 trigger", 2, -4451.6, 4531.1, 186.0),
    ("rx130 ship", 2, -4800.0, 4632.2, 86.0),
    ("rx152 trigger", 2, -5613.8, 4162.5, 186.0),
    ("rx152 ship", 2, -5613.8, 4162.5, 86.0),
    ("rx433 trigger", 3, -1563.5, -5275.1, 186.0),
    ("rx433 ship", 3, -1560.1, -5331.6, 86.0),
    ("rx491 trigger", 3, -1720.4, -5251.6, 186.0),
    ("rx491 ship", 3, -1877.2, -5370.0, 86.0),
    ("HUD ISL2-CONTACT-1", 2, -5064.0, 4492.0, 86.0),
    ("HUD ISL2-CONTACT-2", 2, -5406.0, 4397.0, 86.0),
    ("HUD ISL2-CONTACT-3", 2, -6167.0, 5130.0, 86.0),
    ("HUD ISL3-CONTACT-1", 3, -1560.0, -5331.0, 86.0),
    ("HUD ISL3-CONTACT-2", 3, -1877.0, -5370.0, 86.0),
    # THE TWO FRAMES THE LETTER LEFT UNDECODED, DECODED BY `RE-298` FROM THE
    # RAW CAPTURE ITSELF (not from `GT-228`'s prose).  They are the two rows
    # this lane wrote, four screens down, that it "most wants".  The id-35
    # pair is the OPEN-WATER control: it is the only pair here that must
    # fall outside every island box, and the pass path is worth nothing
    # without a point that has to fail it.
    ("rx112 trigger", 35, -752.17, 3138.06, 186.0),
    ("rx112 ship", 35, -872.04, 3175.01, 86.0),
    ("rx248 trigger", 2, -6412.74, 4629.52, 186.0),
    ("rx248 ship", 2, -6231.26, 4871.58, 86.0),
)

# The box `rx112` WAS standing in, from `RE-298`'s sweep of all 52 records:
# `ordinal 35`, `Trigger OPNPLC_RAT_LV [35]`, pos (-1488.53, 2518.85, 86.0),
# extent (1500, 1500, 300).  Read the committed way -- centre plus full
# width -- that is x[-2238.53, -738.53] y[1768.85, 3268.85].
#
# IT IS NOT IN `ISLAND_EXTENT_BOXES` AND MUST NOT BE PUT THERE.  It is here
# to carry one fact that changes how every later round reads a 0x1FB2: the
# open-water frame was not the client firing at nothing.  The ship was
# inside a real trigger volume of a DIFFERENT KIND.  A round that "fixes"
# open water by adding boxes until every observed frame lands in one has
# rebuilt exactly the classifier `RE-234` item (3) rejected.
M2_OPEN_WATER_CONTROL_ORDINAL = 35
M2_OPEN_WATER_CONTROL_BOX = (-2238.53, 1768.85, -64.0, -738.53, 3268.85, 236.0)
M2_OPEN_WATER_CONTROL_TRIGGER_NAME = "Trigger OPNPLC_RAT_LV [35]"

# NOT DECODED IN THE LETTER, so not here either, and named rather than left
# for a later round to notice as an absence: `rx248` (id 2) and `rx112`
# (id 35, the open-water frame) have timestamps and ids but no coordinates
# in section (kho).  The id-35 one is the row this lane most wants -- an
# open-water position to check against the boxes would turn "the boxes
# separate the two islands" into "the boxes separate contact from open
# water".  It is the one question the crosswalk ticket still has to ask.
# EMPTY SINCE `RE-298`, AND KEPT RATHER THAN DELETED.  Both names moved up
# into the observations tuple with coordinates.  The tuple stays so the test
# that pairs it against the observations can say "nothing is waiting" in the
# same shape it used to say "two frames are waiting", instead of the absence
# of a name meaning two different things on two different days.
M2_WIRE_ORDINAL_CROSSWALK_UNDECODED_FRAMES: tuple[str, ...] = ()

# COO-DECISION `20260907_1245` item 2 pointed at line 35 of the same letter
# as "a clue you have not used", and said in the same breath that it is
# supporting evidence and NOT a permit to name the discriminator.  It is
# transcribed here because transcribing numbers is copying, not deciding:
#
#     LANE_A_TRIGGER_VITAL id=35 name=Thorn Flower  PROP no_responder bytes_out=0
#     LANE_A_TRIGGER_VITAL id=2  name=Edmund Hidden Treasure PROP no_responder bytes_out=0  (x3)
#     LANE_A_TRIGGER_VITAL id=3  name=Seafood Cargo  PROP no_responder bytes_out=0          (x2)
#
# AND THE ROWS AROUND IT KILL THE CLUE, WHICH IS WHY ALL THREE ARE HERE AND
# NOT ONLY THE ONE THE LETTER OFFERED.  The open-water frame's id resolves
# to a `PROP` with `no_responder` and `bytes_out=0` -- and so does every
# CONTACT frame in the same session, on lines 36 and 37 of the same letter.
# Contact and open water are INDISTINGUISHABLE on this field: all six
# frames of `GT-228` got the identical `PROP no_responder bytes_out=0`.  So
# "the id resolves to a prop with no responder" cannot answer "is this
# frame an island contact", which is the one question
# `ISLAND_CONTACT_DISCRIMINATOR` exists to answer.
#
# NONCLAIM, stated so no later round can quote the id-35 row on its own:
# this table is NOT a discriminator and MUST NOT be read as one.  What it
# does support is the narrower, already-committed claim that the open-water
# frame carried id 35 rather than id 3 -- `name=Thorn Flower` is a third
# independent spelling of that, after the raw capture and the EVENTS log.
# `ISLAND_CONTACT_DISCRIMINATOR` IS NO LONGER `None` -- `RE-298` filled it
# -- and this paragraph is still true and still load-bearing: the name
# resolution table did NOT fill it and must never be quoted as the thing
# that did.  What filled it was the box sweep.
M2_WIRE_ORDINAL_CROSSWALK_NAME_RESOLUTION: tuple[
    tuple[int, str, str, str, int], ...
] = (
    (35, "Thorn Flower", "PROP", "no_responder", 0),
    (2, "Edmund Hidden Treasure", "PROP", "no_responder", 0),
    (3, "Seafood Cargo", "PROP", "no_responder", 0),
)


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

# The `boxes` seam gets the same named raise `registry` has, for the reason
# pf-adversary gave: the file spent a constant and twelve lines of docstring
# teaching that lesson for one test-only parameter and then added a second
# one without it.  `_tier3_contact_reason(reading, boxes=[1, 2])` used to
# die with `AttributeError: 'list' object has no attribute 'values'`.
EXTENT_TABLE_REFUSED_NOT_A_MAPPING = "EXTENT_TABLE_REFUSED_NOT_A_MAPPING"


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
# it has to spell out that it is doing so.
#
# THAT SENTENCE WAS WRONG AND pf-adversary RAN IT: a module-level
# `__NAME` is NOT mangled -- mangling happens only inside a class body -- so
# `vars(module)` holds the plain `__CANDIDATES` and `getattr(module,
# "__CANDIDATES")[2] = forged` worked.  The name `__CANDIDATES` is in
# `__FROZEN` now, so REBINDING it is refused.
#
# AND THAT IS STILL NOT THE SAME THING, WHICH THE SENTENCE HERE USED TO
# CLAIM IT WAS.  pf-adversary re-ran the original repro against this round
# and it STILL SUCCEEDS: freezing a name stops `module.__CANDIDATES = {}`,
# it does nothing about `getattr(module, "__CANDIDATES")[2] = forged`, which
# writes THROUGH the name into the dict the proxy is a view of.  The same
# holds for `_ISLAND_EXTENT_BOXES[99] = a box the size of the world`, which
# the freeze docstring lists among the bypasses it closed.  With a
# discriminator measured, that second one hands a session sitting in open
# water a frame nobody cited.  `test_the_two_tables_cannot_be_mutated_in_
# place` checks the PROXIES; nothing checks the dicts behind them.  This is
# not fixed in this round -- it is a different door from C6 and the round
# is out of budget -- and it is written down here, unhedged, as the first
# job of the next one rather than left as a sentence that reads as though
# it were already handled.
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

    NO TIER ASKS THIS QUESTION ANY MORE.  Tier 3 asked it until this round
    and that was pf-adversary's C1: "inside some island" is not "inside the
    island this id names", and the gap between the two sentences was a
    pass.  It is now a one-line view over ``_ordinals_containing_position``,
    which owns the geometry and which tier 3 asks instead.  Kept because it
    is the honest spelling of the weaker question and the tests that pin the
    weaker one are the tests that would notice the geometry drifting.

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

    A row of the WRONG ARITY, or with a key that is not a plain ``int``, is
    skipped rather than unpacked or compared -- see
    ``_ordinals_containing_position``, which does the skipping now and
    carries the measurement behind it.
    """
    return bool(_ordinals_containing_position(x, y, z, boxes))


def _ordinals_containing_position(
    x: float,
    y: float,
    z: float,
    boxes: "Mapping[int, object] | None" = None,
) -> tuple[int, ...]:
    """The ORDINALS whose box contains ``(x, y, z)``, in table order.

    THE ONE PLACE THE GEOMETRY IS WRITTEN, since this round.
    ``_position_is_inside_a_committed_extent`` is now a one-line view over
    it and tier 3 asks this one, because tier 3's question stopped being
    "is the ship inside SOME island" -- see
    ``CONTACT_REFUSED_INSIDE_ANOTHER_ISLANDS_EXTENT`` for the pass this
    file was giving away while those were the same question.  Two copies of
    an inclusive six-bound comparison would have been two places for the
    `<=` pf-adversary's C8 says nothing pins yet to drift apart.

    Rows are skipped, never unpacked, when the KEY is not a plain ``int``
    or the value is not a 6-tuple.  Both skips are the fail-closed
    direction and both are reachable only through the ``boxes`` seam on the
    shipped tree; the arity one has a measured history (a five-field typo
    raised ``ValueError`` out of ``candidate_for_trigger_id``, whose caller
    is promised a named refusal and never an exception), and the key one is
    new with the per-id lookup: a key of some other type cannot be the wire
    id this module now compares against, and comparing it could dispatch to
    a caller's ``__eq__``.  Same lesson, third sighting, as step 3 of
    ``_tier3_contact_reason``: BOTH sides have to be exact before ``==``.
    """
    table = ISLAND_EXTENT_BOXES if boxes is None else boxes
    found: list[int] = []
    for ordinal, box in table.items():
        if type(ordinal) is not int or not _is_a_readable_row(box):
            continue
        x0, y0, z0, x1, y1, z1 = box
        if x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1:
            found.append(ordinal)
    return tuple(found)


_UNSET = object()


def _tier3_contact_reason(
    island_contact: object,
    wire_trigger_id: object,
    *,
    discriminator: object = _UNSET,
    boxes: "Mapping[int, object] | None" = None,
) -> str | None:
    """TIER 3 ALONE, AND PRIVATE FOR THE SAME REASON
    ``_tier2_id_is_a_candidate`` IS: a caller able to ask tier 3 by itself
    would be one import away from answering the world with a fact that never
    passed tiers 1 and 2.  ``answer_guard_reason`` is the only caller.

    ``wire_trigger_id`` IS REQUIRED AND IS NOT A SEAM.  It is the id tier 2
    just admitted, handed down so tier 3 can ask its question about THE
    ISLAND THAT ID NAMES rather than about islands in general.  It has no
    default, because every default available is a lie: ``None`` would mean
    "no island in particular", which is the passing-on-the-wrong-island
    behaviour this parameter deletes, and any int would answer for an
    island the caller never named.  A caller with no id has no business
    reaching tier 3 at all -- ``_answer_guard_reason`` is the only
    production route here and it arrives with the id already checked.

    SEVEN refusals, in this order, each a different thing being wrong:

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
      5. the wire id has NO ROW in the committed table.  Unreachable on the
         shipped tree (`CANDIDATE_TRIGGER_IDS` is (2, 3), both have boxes)
         and kept because the two sets are written from different letters
         in different parts of this file, so the day one grows first this
         refuses instead of falling back to the sweep being deleted.
      6. the position is inside a committed extent, but NOT the one this
         id names -- pf-adversary's C1, and the reason this function grew
         an argument.  It was measured as a PASS on `#1052`: the `rx248`
         reading, which is a position inside ordinal 2's box, went through
         all three tiers carrying wire id 3.  The right to refuse it comes
         from `RE-298`, not from the numbers being equal; see
         ``ISLAND_EXTENT_BOX_ORDINALS``.
      7. the position is not inside any committed extent at all: the
         session is in OPEN WATER.  `RE-234` item (3)'s finding -- the wire
         id alone cannot tell an island from open water -- now decided
         HERE, by the committed table, rather than by the presence of a
         frame.
         SAY WHOSE COORDINATES THESE ARE, because an earlier draft of
         this line said "coordinates the server owns" and that is FALSE:
         they arrive in ``island_contact`` from the caller, and the caller
         the next round is going to write reads them out of the CLIENT's
         ``TargetPos`` in the `0x1FB2` frame.  So this refusal decides
         "does the position the client reported fall in a box we measured",
         which is a strictly weaker sentence than "where the ship is".  The
         question of what the server's own source of truth for the ship
         position is, and which one wins when they disagree, IS NOT
         ANSWERED ANYWHERE IN THIS PROJECT YET -- pf-adversary asked it
         against this round and it is written here rather than left for a
         later round to assume the strong reading.

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

    Returns ``None`` only when all seven are satisfied.  Never raises on
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
    if not isinstance(table, Mapping):
        raise TypeError(EXTENT_TABLE_REFUSED_NOT_A_MAPPING)
    if not table:
        return CONTACT_REFUSED_NO_EXTENT_TABLE
    if not _is_a_wire_int(wire_trigger_id) or _readable_extent_for(
        wire_trigger_id, table
    ) is None:
        return CONTACT_REFUSED_NO_EXTENT_FOR_THIS_TRIGGER_ID
    containing = _ordinals_containing_position(
        island_contact.x, island_contact.y, island_contact.z, table
    )
    if wire_trigger_id in containing:
        return None
    if containing:
        return CONTACT_REFUSED_INSIDE_ANOTHER_ISLANDS_EXTENT
    return CONTACT_REFUSED_OUTSIDE_EVERY_COMMITTED_EXTENT


def _readable_extent_for(
    wire_trigger_id: object,
    table: "Mapping[int, object]",
) -> "tuple[object, ...] | None":
    """The box ``table`` holds for exactly this plain ``int``, or ``None``.

    THE RETURN IS ANNOTATED ``tuple[object, ...]``, NOT SIX FLOATS, because
    six floats is more than ``_is_a_readable_row`` checks: it counts the
    fields and does not look inside them.  A seam row of six strings is
    "readable" here and raises on comparison in
    ``_ordinals_containing_position`` -- a hazard the ``.values()`` sweep
    had too, unchanged by this round and named rather than annotated away.
    The caller only tests this against ``None``.

    READABLE, NOT MERELY PRESENT, and the difference is a measured one: a
    row whose value is a five-field typo is a key that EXISTS and a box
    nothing can be judged against.  Answering "the id has a row" for it
    sent tier 3 on to report `OUTSIDE_EVERY_COMMITTED_EXTENT` -- "we
    measured this island and you are not on it" -- when the truth is "we
    cannot read the row for this island".  The first version of this
    function did exactly that and a test caught it before the commit.  So
    the same row filter ``_ordinals_containing_position`` applies decides
    here too: exactly the rows either one can act on.

    NOT ``wire_trigger_id in table``, and the difference is the same one
    step 3 of ``_tier3_contact_reason`` cost three rounds to learn: ``in``
    on a Mapping runs the TABLE's ``__contains__`` and then ``__eq__``
    between whatever the table holds and whatever the caller sent, either
    of which a hostile value can own.  This walks the keys the module can
    vouch for -- ``type(key) is int``, the same predicate ``_is_a_wire_int``
    applies to the other side -- and compares two plain ints, which cannot
    dispatch anywhere.  The caller checks ``_is_a_wire_int`` first, so both
    halves are exact before ``==`` runs.  Keeps this function's promise
    never to raise on either argument, which ``in`` did not.
    """
    for key, box in table.items():
        if type(key) is int and key == wire_trigger_id and _is_a_readable_row(box):
            return box
    return None


def _is_a_readable_row(box: object) -> bool:
    """``True`` for a value this module will unpack as a six-bound box.

    ONE SPELLING, because the two callers have to agree.  A row this says
    ``False`` about is skipped by ``_ordinals_containing_position`` AND
    reported as no-extent by ``_readable_extent_for``; if they disagreed,
    a malformed row would make its id "present but never containing", which
    is the open-water verdict wearing a typo's clothes.
    """
    return type(box) is tuple and len(box) == 6


def answer_guard_reason(
    current_scene_id: object,
    wire_trigger_id: object,
    island_contact: object = None,
) -> str | None:
    """``None`` when all THREE tiers pass; otherwise the NAMED reason the
    first failing tier gives, in tier order (scene, then id, then contact).

    Since `RE-289` the third tier can PASS: a reading tagged with the
    module's measured discriminator whose position falls inside THE
    COMMITTED BOX OF THE WIRE ID IT WAS SENT WITH returns ``None`` from all
    three tiers.  "OF THE WIRE ID IT WAS SENT WITH" is this round's change
    and it is a NARROWING: until now any of the three boxes would do, so a
    reading taken at island 2 passed while carrying id 3 (pf-adversary C1,
    measured as a pass on `#1052`).  The permission to tie the two together
    is `RE-298`'s crosswalk, not the numbers being equal -- and
    since `RE-298` named that discriminator, it can do so ON THE SHIPPED
    TREE, not only through the private seam.  A call that
    supplies no reading at all still gets
    ``CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED`` for the ONE input
    that gets that far (scene 126 with wire id 2 or 3) and a tier-1/tier-2
    reason for everything else.  Never raises, on any of the three
    arguments.

    ``island_contact`` IS THE THIRD ARGUMENT AND IT DEFAULTS TO ``None``,
    which is a refusal, not a pass -- see ``IslandContactEvidence`` for why
    the parameter exists at all and ``_tier3_contact_reason`` for the seven
    ways it is refused.  The default keeps every call written before this
    round answering EXACTLY what it answered before -- which was true of
    EVERY call while the discriminator was unmeasured.  `RE-298` ended
    that: a call that passes no reading now earns
    ``CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED`` rather than
    ``CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED``, because the module
    HAS a measurement and the caller has no reading -- a different
    sentence about a different world, and the tests moved with it.  An earlier draft of this docstring
    said the module's own suite passed "unedited", which its own diff
    refutes -- about fifteen call sites in the test file had to be given an
    `island_contact=` argument to keep reaching the code they were named
    for.  No PRODUCTION call changed, because there are no production
    callers.
    """
    return _answer_guard_reason(current_scene_id, wire_trigger_id, island_contact)


def _answer_guard_reason(
    current_scene_id: object,
    wire_trigger_id: object,
    island_contact: object = None,
    *,
    discriminator: object = _UNSET,
    boxes: "Mapping[int, object] | None" = None,
) -> str | None:
    """``answer_guard_reason`` WITH ``_tier3_contact_reason``'s two test
    seams carried through, and PRIVATE for the same reason they are: a
    caller able to supply the discriminator it is judged against is
    answering itself.

    IT EXISTS BECAUSE THE PASS PATH HAD NEVER BEEN RUN.  pf-adversary's F5
    against the previous round measured it as a surviving mutant: change
    ``_candidate_for_trigger_id``'s last line from
    ``table.get(wire_trigger_id)`` to ``table.get(current_scene_id)`` and
    THE WHOLE FILE STAYS GREEN, because ``ISLAND_CONTACT_DISCRIMINATOR`` is
    ``None`` on the shipped tree, so every call in every test is refused at
    tier 3 and the lookup below it is dead code under test.  The lane's
    central function -- the only one in this file that hands a frame to a
    caller -- was reached by no test at all.  ``_tier3_contact_reason``
    already had the seams; nothing carried them the two frames up to where
    the lookup happens, so this function does.

    WHY NOT JUST GIVE THE SEAMS TO ``answer_guard_reason``: because that one
    is public and takes its arguments from a live session.  The rule this
    file has followed since C6 is that a seam lives on a private twin and
    the public function forwards nothing to it, and the same tests that pin
    the absence of ``registry=`` from the public surface pin these two.

    THE ORDER OF THE THREE TIERS IS HERE, not in the public function, so
    there is one copy of it.  ``answer_guard_reason`` is now a forwarding
    line, exactly as ``candidate_for_trigger_id`` is.
    """
    scene_reason = scene_guard_reason(current_scene_id)
    if scene_reason is not None:
        return scene_reason
    trigger_reason = _trigger_id_guard_reason(wire_trigger_id)
    if trigger_reason is not None:
        return trigger_reason
    return _tier3_contact_reason(
        island_contact,
        wire_trigger_id,
        discriminator=discriminator,
        boxes=boxes,
    )


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


def _candidate_for_trigger_id(
    current_scene_id: object,
    wire_trigger_id: object,
    island_contact: object = None,
    *,
    discriminator: object = _UNSET,
    boxes: "Mapping[int, object] | None" = None,
    registry: "Mapping[int, CandidateFrame | None] | None" = None,
) -> "CandidateFrame | None":
    """``candidate_for_trigger_id`` WITH the test-only ``registry`` seam, and
    PRIVATE for exactly the reason ``_tier3_contact_reason``'s
    ``discriminator=``/``boxes=`` are private: a caller able to supply the
    table it is answered from is answering itself.

    pf-adversary's finding C6 against `pirate-force-server#1015` is what
    closed this: ``registry`` was a PUBLIC keyword on the function below,
    "unreachable today" only because tier 3 refused every input on an
    unmeasured discriminator.  That is a door held shut by a fact that the
    next round is expected to change -- the round that fills in
    ``ISLAND_CONTACT_DISCRIMINATOR`` would have opened it by doing nothing
    at all.  So it is shut here, BEFORE the discriminator is measured, which
    is the order the previous round wrote down as its first job.

    The public function forwards NOTHING to this parameter, and two tests
    measure that: ``test_the_public_lookup_has_exactly_three_parameters``,
    which pins the parameter LIST rather than the absence of one name, and
    ``test_no_public_callable_carries_any_of_the_three_seams``, which is the
    sole killer for a seam re-appearing on ``answer_guard_reason`` or under
    a new public re-export.

    NOT the public-surface test, and this sentence used to say it was.
    pf-adversary measured it blind here: that test's SHAPE prong is only
    consulted for a callable that is NOT tier-ordered, and this function is
    tier-ordered, so re-adding ``registry=`` to it leaves that test green.
    Deleting its ``registry`` allowlist entry was still right -- an
    allowlist entry does not close a door -- but its power is over
    ``registered_count``, not over this function, and claiming otherwise was
    an assertion dressed as a measurement.

    ``discriminator=`` AND ``boxes=`` ARE THE SAME KIND OF SEAM AND ARRIVED
    FOR A BLUNTER REASON: without them the two lines below this docstring
    had never been executed by a passing call.  See ``_answer_guard_reason``
    for the mutant pf-adversary used to prove it.  They are forwarded, not
    consumed, and the public function forwards NEITHER -- so on the shipped
    tree this function reads the module's own MEASURED discriminator (since
    `RE-298`) and can return ``None``.  Before that letter it read an
    unmeasured one and refused every input in the world.
    """
    if (
        _answer_guard_reason(
            current_scene_id,
            wire_trigger_id,
            island_contact,
            discriminator=discriminator,
            boxes=boxes,
        )
        is not None
    ):
        return None
    table = _table_for(registry)
    return table.get(wire_trigger_id)


def candidate_for_trigger_id(
    current_scene_id: object,
    wire_trigger_id: object,
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

    THERE IS NO ``registry`` PARAMETER ON THIS FUNCTION, and there was one
    until this round.  It defaulted to this module's own ``_CANDIDATES`` and
    existed only so a test could pass a synthetic mapping without mutating
    production state -- but it was PUBLIC, so it also let any caller supply
    the whole table this function answers from, which is the one thing the
    three tiers exist to decide.  pf-adversary named it C6 against
    `pirate-force-server#1015`; the previous round agreed and wrote it down
    as this round's first job, precisely because the door was standing open
    behind a tier-3 refusal that the next round is meant to remove.  The
    seam now lives on ``_candidate_for_trigger_id``, private, the same way
    ``discriminator=`` and ``boxes=`` live on ``_tier3_contact_reason``.

    ``island_contact`` is TIER 3's reading and is passed straight through to
    ``answer_guard_reason``; ``None`` is a refusal, not a pass.  It is now
    the THIRD POSITIONAL argument, which it could not be while the test-only
    keyword sat in front of it.  Callers that already spell it
    ``island_contact=`` keep working unchanged; the previous round's
    docstring predicted this move and named it as the change to make "the
    day a discriminator is measured", and closing C6 is what made it free.

    NEVER RAISES, FULL STOP, ON ANY ARGUMENT -- and that sentence became
    sayable this round.  Every value of ``current_scene_id``,
    ``wire_trigger_id`` and ``island_contact``, of every type, is answered
    with ``None`` rather than an exception, because all three come from a
    live session.  Until this round the promise had to carry a long
    exception for ``registry``: a non-mapping raised
    ``TypeError(REGISTRY_REFUSED_NOT_A_MAPPING)``, conditionally, only once
    tier 3 could pass, so the docstring spent a screen explaining when the
    "never raises" claim was and was not true.  With the seam moved to
    ``_candidate_for_trigger_id`` there is no argument left on this function
    that can raise, and the paragraph explaining the exception is deleted
    rather than rewritten.  ``REGISTRY_REFUSED_NOT_A_MAPPING`` still exists
    and is still raised, by ``_table_for``, reached from the private
    function and from ``_registered_count`` -- see those two for the
    posture and for which of them validates unconditionally.

    ONE PRODUCTION CALL SITE PASSES TO THIS, SINCE ROUND `p7rob4`, AND THE
    SENTENCE HERE USED TO SAY THERE WERE NONE.  Repo-wide grep for this
    module's name now finds its own test file AND
    ``lane_hooks/lane_a_island_trigger_log.py``, which calls
    ``answer_guard_reason`` on every inbound ``0x1FB2`` frame and prints
    the verdict on stderr as ``LANE_A_M2_GUARD ... verdict=...``.  What
    that importer does NOT do is send: it composes no frame, queues no
    bytes and touches no session state, and its tests assert
    ``actions == []`` through the real dispatcher.  So the OLD claim
    ("nothing in `src/` imports this module") is retired, and what stands
    in its place is narrower and still true: NOTHING IN `src/` TURNS THIS
    MODULE'S ANSWER INTO A FRAME.  That is the line `PANYA 1910` draws,
    and the RE ticket asking which inbound vital opens the captain-report
    window (`pf_bridge/notes_to_chief/20260907_1932_LANE-A-TO-K-re-body-*`)
    is what has to land before it can move.
    """
    return _candidate_for_trigger_id(
        current_scene_id, wire_trigger_id, island_contact
    )


def _registered_count(
    registry: "Mapping[int, CandidateFrame | None] | None" = None,
) -> int:
    """``registered_count`` WITH the test-only ``registry`` seam, private for
    the same reason ``_candidate_for_trigger_id`` is.

    This one validates its registry UNCONDITIONALLY -- there are no tiers in
    front of it -- so it is the place to look for the unconditional form of
    the ``REGISTRY_REFUSED_NOT_A_MAPPING`` posture, and a test says so.
    """
    table = _table_for(registry)
    return sum(1 for trigger_id in CANDIDATE_TRIGGER_IDS if table.get(trigger_id) is not None)


def registered_count() -> int:
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
    could be answered.  It used to add "tier 3 refuses every lookup today
    regardless"; since `RE-298` that is false, and the count is still a
    count of slots -- every one of which is empty, so every lookup still
    answers ``None`` for want of a REGISTERED FRAME, not for want of a
    measurement.

    IT TAKES NO ARGUMENTS AT ALL SINCE THIS ROUND.  It used to take the
    test-only ``registry``, which made it the one public callable in this
    file that a caller could hand a table to; the seam is
    ``_registered_count`` now.  Taking nothing is also what makes it exempt
    from the public-surface test's tier-ordering prong by SHAPE rather than
    by an allowlist entry -- the entry that used to spell ``registry`` there
    is deleted in the same commit."""
    return _registered_count()


# ---------------------------------------------------------------------------
# THE MODULE FREEZE -- COO-DECISION `20260907_0945` item 1.
# ---------------------------------------------------------------------------
# WHICH BOUNDARY IS THIS FREEZE?  DISCIPLINE, NOT SECURITY.
# CONFIRMED BY COO-DECISION `20260907_1744`, which upheld reading (b) and
# made both consequences below BINDING, not this lane's assumption.  The
# `[assumption of LANE-A]` tag that stood here is gone because the
# decision arrived, and that decision added a third rule which is now
# item 3.  (The first version of this line said "for five rounds".
# pf-adversary D6 re-derived it: the tag exists in the tree of exactly two
# LANE-A rounds, `fr81hi` (#1054, which added it) and `yw28ea` (#1058).
# A count of rounds nobody can re-derive from the repository is the same
# defect as a stale line number, so this sentence no longer carries one.)
#
# pf-adversary asked the question that the last four rounds of this file
# were avoiding: "who is the importer this freeze protects against, and
# what can they already do?"  Its own answer is right and this file now
# says so instead of leaving it implied.  Every door that is still open --
# `getattr(module, "__CANDIDATES")[2] = forged`, `gc.get_referents` on the
# proxies, rebinding a name nobody thought to freeze -- needs the SAME
# capability: run arbitrary Python in this process.  Anybody holding that
# capability does not need any of these doors; they can call
# `_tier3_contact_reason` themselves and ignore the module entirely.  So
# this freeze CANNOT be a security boundary, and no test in this file may
# be sold as buying one.
#
# What it IS: the boundary between "a measured fact arrives through an RE
# result letter, a citation and a test" and "a measured fact arrives
# through an assignment".  The failure it exists to prevent is not an
# attacker.  It is A LATER ROUND OF THIS LANE, at minute 70, writing
# `module.ISLAND_CONTACT_DISCRIMINATOR = "yes"` to make a red test green
# and shipping a world that decides islands from nothing.  That has
# happened here: `""` was measured unlocking all three tiers on `550a36d`
# and on `#993`.
#
# THREE CONSEQUENCES, ALL BINDING ON LATER ROUNDS.  (This header said TWO
# over three items for the length of one round: item 3 was added with the
# count left alone -- the exact D7 shape this same commit was paying.
# pf-adversary D3 of round `p7rob4` measured it.)
#   1. SCOPE FOLLOWS THE TIERS, NOT THE ATTACKER.  The set below must
#      contain every name a tier READS while deciding -- which is why a
#      test now derives that list from the tiers' own syntax instead of
#      trusting this set to be typed correctly by hand.  It does NOT have
#      to contain every name reachable by every trick.
#   2. AN UNCLOSABLE DOOR IS NOT A CRITICAL BUG HERE.  `gc.get_referents`
#      is not a hole in a discipline boundary; it is deliberate effort,
#      which is exactly what a discipline boundary is allowed to require.
#      A round that spends itself chasing those instead of covering a name
#      a tier reads has the priority backwards.
#
#   3. NO ROUND OF THIS LANE MAY SPEND ITSELF CLOSING PROCESS-LEVEL DOORS
#      IN THIS FILE AGAIN (COO-DECISION `1744`, the part that binds beyond
#      the answer).  A pf-adversary finding of that shape -- `gc.get_referents`,
#      `module.__class__ = ...`, overwriting `__CANDIDATES` -- is answered
#      with one line, "process level, not a critical bug, per decision
#      `1744`", and the round moves to its next job.  It does not open a
#      round.  What the freeze buys is item 1 and only item 1, and item 1
#      is worth paying for because it has already been breached: `""`
#      unlocked all three tiers on `550a36d` and `#993`.
#
# The letter that asked is
# `pf_bridge/notes_to_chief/20260907_1622_LANE-A-ASK-COO-what-boundary-is-the-
# tier3-freeze.md`; the answer is
# `notes_to_chief/20260907_1744_COO-DECISION-a1622-freeze-is-a-discipline-line-
# LANE-A.md`.
#
# THE DECISION THAT LICENSED NAMING `ISLAND_CONTACT_DISCRIMINATOR` IS
# `COO-DECISION 20260907_1441` ITEM 4, AND UNTIL ROUND `p7rob4` THIS FILE
# NEVER CITED IT.  That matters twice.  First, because `RE-298` is
# evidence, not authority: `COO-DECISION 20260907_1245` section 1 says in
# red that the crosswalk being answered does NOT by itself grant the right
# to fill the name, and any sentence in this file reading "`RE-298`
# licenses it" is repeating the reading that decision refused -- the
# permit is `1441` item 4, which cites `RE-298` as its grounds.  Second,
# because `1441` attached a condition this lane did not meet: fill the
# name AND remove the docstring prohibition IN THE SAME COMMIT.  The name
# was filled at `8ce0c44`; the prohibition text was still being corrected
# rounds later.  Recorded here rather than quietly fixed, because a
# condition missed and unlogged is how the next one gets missed too.
# (pf-adversary D5 of round `p7rob4` found both.)
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
    every ``__setattr__`` Python has; so do
    ``object.__setattr__(module, name, value)`` and
    ``ModuleType.__setattr__(module, name, value)``, which reach past this
    subclass by naming the base explicitly (both added after pf-adversary
    named them as the two spellings a determined author actually reaches
    for); and so does re-executing the module body through
    ``importlib.reload``.  Nothing in a Python process can prevent those.

    WHAT IT USED TO ALSO NOT STOP, CLOSED THIS ROUND:
    ``candidate_for_trigger_id(..., registry=...)`` was a PUBLIC keyword
    that supplied the whole registry, so freezing ``_CANDIDATES`` protected
    a copy the caller need not use.  pf-adversary filed it as C6 against
    `pirate-force-server#1015` and the previous round wrote it down as this
    round's first job, for a reason worth keeping in view: it was
    "unreachable" only because tier 3 refuses on an unmeasured
    discriminator, i.e. it was held shut by the very fact the next round is
    sent to change.  Both lookups now keep the seam on a private twin
    (``_candidate_for_trigger_id``, ``_registered_count``); the public pair
    take no registry at all, which is checked by the exact-parameter-list
    pin and by the discovery-based seam pin.  NOT by the public-surface
    test: pf-adversary measured that one blind to a TIER-ORDERED function
    re-growing the keyword, so its deleted allowlist entry has power over
    ``registered_count`` alone.  The freeze converts an ACCIDENT (an ordinary assignment, which
    is what the repro used and what a hurried round would write) into a
    named error, and leaves the deliberate act visible in a diff as a line
    no honest caller has a reason to contain.  That distinction is the whole
    claim -- see the wording COO ratified in `0945`: the guard exists to
    stop a DECISION being taken silently, not to stop a determined author.
    """

    # THE SET GREW AFTER pf-adversary MEASURED THE FIRST ONE.  It held the
    # three names of the repro and nothing else, and four one-line
    # assignments walked around it:
    #   * `module.__class__ = types.ModuleType` -- un-freeze, then write.
    #   * `module._tier3_contact_reason = lambda *a, **k: None` -- the
    #     module's functions call each other through module globals, so
    #     rebinding ANY of them defeats the guard without touching the data.
    #     Seven names each did it on their own.
    #   * `module._ISLAND_EXTENT_BOXES[99] = a box the size of the world` --
    #     the proxy was over a dict that was itself a public attribute.
    #   * `module.ISLAND_EXTENT_BOX_CITATIONS[...] = ...` -- the table the
    #     citation gate reads.
    # Data alone was never the boundary; the boundary is "everything tier 3
    # decides with".
    __FROZEN = frozenset(
        {
            "__class__",
            "ISLAND_CONTACT_DISCRIMINATOR",
            "ISLAND_EXTENT_BOXES",
            "_ISLAND_EXTENT_BOXES",
            "ISLAND_EXTENT_BOX_CITATIONS",
            "ISLAND_EXTENT_BOX_ORDINALS",
            "RE289_RESULT_LETTER",
            "RE289_RESULT_LETTER_SHA256",
            # `RE-297`'s answer and the dump that makes it re-checkable from
            # a clone.  They are tier-3 state for the same reason the two
            # names above are: the citation gate's whole point is that a
            # table with no letter behind it is a refusal, and a name an
            # importer can rewrite is a letter an importer can invent.
            "RE297_RESULT_LETTER",
            "RE297_RESULT_LETTER_SHA256",
            "RE289_TGR_DUMP_LETTER",
            "RE289_TGR_DUMP_LETTER_SHA256",
            # HOW the boxes are read, and the six records that decided it.
            # Rebinding `ISLAND_EXTENT_BOX_INTERPRETATION` does not move a
            # box on its own, but it is the name a later round is meant to
            # consult before touching one, and the edge-wall rows are the
            # oracle that keeps map-border volumes out of the island table.
            "ISLAND_EXTENT_BOX_INTERPRETATION",
            "ISLAND_EXTENT_BOX_INTERPRETATIONS_REFUTED",
            "ISLAND_EXTENT_BOX_EDGE_WALL_ORDINALS",
            "ISLAND_EXTENT_EDGE_WALL_RECORDS",
            "ISLAND_EXTENT_EDGE_WALL_SPACINGS",
            "_CANDIDATES",
            "__CANDIDATES",
            "TIER3_STATE_IS_READ_ONLY",
            "_is_a_wire_int",
            "_trigger_id_guard_reason",
            "scene_guard_reason",
            "_position_is_inside_a_committed_extent",
            # SAME D1 SHAPE, THE THREE FUNCTIONS `yw28ea` MINTED.  Closing
            # C1 minted `_ordinals_containing_position` (which owns the
            # geometry the name above used to own), `_readable_extent_for`
            # (which returns the box of one id, or `None` when that id has
            # no readable row) and `_is_a_readable_row` (which decides
            # whether a row may be unpacked at all).  Any one of them
            # rebound is tier 3 deciding whatever the caller wants: the
            # first can return every ordinal, the second can hand back a
            # box the table never held, the third can wave any object
            # through to be unpacked.
            #
            # THIS COMMENT WAS WRONG TWICE AND `p7rob4` IS FIXING IT, NOT
            # THE CODE (pf-adversary D7 and D1 against `yw28ea`).  It said
            # TWO functions and named `_ordinal_is_in_table`, a name that
            # was renamed to `_readable_extent_for` in the same commit and
            # survives nowhere in this file except the two sentences
            # discussing it -- a comment describing an earlier draft of its
            # own commit.  (The first version of THIS sentence said "zero
            # hits", which its own existence refuted: pf-adversary D3.)  And it claimed these names "go in
            # the set in the SAME commit that creates them", which
            # `git show 4014f72` refutes about these very functions: that
            # commit minted `_ordinals_containing_position` OUTSIDE this
            # set, went red on its own suite (45 failed, including
            # `test_every_name_a_tier_reads_is_frozen`), and left the D1
            # hole open until `e748577`.
            #
            # PRECISELY, BECAUSE THE FIRST DRAFT OF THIS CORRECTION
            # OVERSTATED ITSELF IN THE OTHER DIRECTION (pf-adversary D7 of
            # round `p7rob4`): `4014f72` never contained
            # `_readable_extent_for` or `_is_a_readable_row` at all.  Both
            # were minted at `e748577`, WHICH ADDED ALL THREE NAMES TO THIS
            # SET IN THAT SAME COMMIT.  So the "same commit" rule held for
            # two of the three functions and was broken for one.  What the
            # lane actually learned from D1 stands either way: the set is
            # kept honest by a test that walks the tiers' own syntax, not
            # by the author remembering -- and that test is what went red.
            "_ordinals_containing_position",
            "_readable_extent_for",
            "_is_a_readable_row",
            "_tier3_contact_reason",
            "answer_guard_reason",
            "_tier2_id_is_a_candidate",
            "_table_for",
            "candidate_for_trigger_id",
            "registered_count",
            # pf-adversary D1 AGAINST THIS ROUND'S OWN FIX, and it was
            # CRITICAL: closing C6 minted two new module-level functions and
            # left them out of this set, while the public pair -- which ARE
            # in it -- do nothing but delegate to them.  One assignment,
            # `module._candidate_for_trigger_id = lambda *a, **k: forged`,
            # then made the FROZEN public function hand a forged frame to a
            # caller standing in no scene, with no reading and no measured
            # discriminator.  That is strictly worse than C6, which needed
            # both a discriminator and an in-box reading.  The comment three
            # screens up says exactly why -- "the module's functions call
            # each other through module globals, so rebinding ANY of them
            # defeats the guard without touching the data" -- and this round
            # walked past its own sentence.  The set is no longer typed by
            # hand alone: a test DERIVES this module's function names and
            # requires this set to contain every one of them, so the next
            # twin cannot be forgotten the same way.
            "_candidate_for_trigger_id",
            "_registered_count",
            # The third private twin, minted this round for pf-adversary's
            # F5.  Same trap as D1 above, and this time the derived test
            # that D1 bought would have caught it.
            "_answer_guard_reason",
            # The crosswalk table landed this round too.  It decides nothing
            # today, and it is the table a discriminator would be judged
            # against tomorrow -- the same argument that put
            # `_ISLAND_EXTENT_BOXES` here.
            "M2_WIRE_ORDINAL_CROSSWALK_LETTER",
            "M2_WIRE_ORDINAL_CROSSWALK_OBSERVATIONS",
            "M2_WIRE_ORDINAL_CROSSWALK_UNDECODED_FRAMES",
            "M2_WIRE_ORDINAL_CROSSWALK_NAME_RESOLUTION",
            # pf-adversary C2, CRITICAL, and it is the hole that MATTERED
            # the day `ISLAND_CONTACT_DISCRIMINATOR` stopped being `None`.
            # Every name below is READ BY A TIER while it decides, and none
            # of them was frozen.  One assignment,
            # `module.CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED = None`,
            # turned "refuse everything" into "pass everything" for a
            # session with no reading at all, because tier 3 returns that
            # constant and `answer_guard_reason` returning `None` MEANS
            # PASS.  `M2_ISLAND_CONTACT_SCENE_ID = <your scene>` opened tier
            # 1; `CANDIDATE_TRIGGER_IDS = (your id,)` opened tier 2;
            # `IslandContactEvidence = <a class that accepts anything>`
            # opened tier 3's type test.  Freezing the data the tiers PRINT
            # while leaving the data the tiers DECIDE WITH writable was the
            # shape of the whole hole.
            "SCENE_REFUSED_NOT_AN_INT",
            "SCENE_REFUSED_NOT_THE_SEA_SCENE",
            "TRIGGER_ID_REFUSED_NOT_AN_INT",
            "TRIGGER_ID_REFUSED_NOT_M2",
            "CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED",
            "CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED",
            "CONTACT_REFUSED_EVIDENCE_OF_ANOTHER_DISCRIMINATOR",
            "CONTACT_REFUSED_OUTSIDE_EVERY_COMMITTED_EXTENT",
            "CONTACT_REFUSED_INSIDE_ANOTHER_ISLANDS_EXTENT",
            "CONTACT_REFUSED_NO_EXTENT_FOR_THIS_TRIGGER_ID",
            "CONTACT_REFUSED_NO_EXTENT_TABLE",
            "EXTENT_TABLE_REFUSED_NOT_A_MAPPING",
            "REGISTRY_REFUSED_NOT_A_MAPPING",
            "M2_ISLAND_CONTACT_SCENE_ID",
            "CANDIDATE_TRIGGER_IDS",
            "IslandContactEvidence",
            "_UNSET",
            # Named in `ISLAND_EXTENT_BOX_SOURCE`'s own sentence and read by
            # the citation gate, and the one name pf-adversary went looking
            # for specifically because it was in neither the freeze nor the
            # data census.
            "RE289_BG3001_TGR_SHA256",
            "ISLAND_EXTENT_BOX_SOURCE",
            # `RE-298`: the letter that filled the discriminator, and the
            # open-water control that is the only committed point which MUST
            # fail the pass path.  A round that can rewrite the control can
            # make the pass path look two-sided while it is not.
            "RE298_RESULT_LETTER",
            "RE298_RESULT_LETTER_SHA256",
            "M2_OPEN_WATER_CONTROL_ORDINAL",
            "M2_OPEN_WATER_CONTROL_BOX",
            "M2_OPEN_WATER_CONTROL_TRIGGER_NAME",
            # pf-adversary C2 AGAINST THIS ROUND'S OWN FIX, and it is D1's
            # shape one level up: `__setattr__` and `__delattr__` resolve
            # the name `_FrozenTier3Module` FROM MODULE GLOBALS at call
            # time, so the freeze depended on a name the freeze did not
            # cover.  `module._FrozenTier3Module = <a shim carrying an
            # empty __FROZEN>` -- an ORDINARY ASSIGNMENT, exactly the
            # accident this boundary exists to turn into a named error --
            # switched the whole thing off without ever meeting
            # `_is_the_same_freeze`.  Measured: a forged frame then reached
            # a caller standing in no scene with no reading.
            "_FrozenTier3Module",
            # pf-adversary C5: tier 3 LOADS `Mapping` (`isinstance(table,
            # Mapping)` guards the named raise) and it arrives by `from
            # ... import`, which the AST derivation does not walk -- so the
            # derivation could not have required it.  Rebinding it turns
            # "the caller is promised a named refusal, never an exception"
            # into a `TypeError` on a valid reading.
            "Mapping",
        }
    )

    @staticmethod
    def _is_the_same_freeze(value: object) -> bool:
        """``True`` for the class this module installs on itself, INCLUDING
        the fresh one a reload builds -- and for NOTHING ELSE THAT IS CHEAP
        TO WRITE.

        `importlib.reload` re-executes the body, which ends by assigning
        `__class__` again -- with a NEW class object, so an identity test
        against the closure's own class would make every reload raise.  That
        is why this is not `value is _FrozenTier3Module`, and it stays not
        that.

        WHAT THIS USED TO BE, AND WHY IT WAS THE WHOLE FREEZE'S HOLE.  It
        was `getattr(value, "_FrozenTier3Module__FROZEN", None) is not
        None` -- a DUCK TYPE.  pf-adversary wrote three lines against it:

            class Unfrozen(ModuleType):
                _FrozenTier3Module__FROZEN = frozenset()
            module.__class__ = Unfrozen

        `Unfrozen` defines no `__setattr__` at all, so after that
        assignment EVERY name in the set below is writable again and the
        public, "frozen" `candidate_for_trigger_id` hands out a forged
        frame to a caller standing in no scene with no reading.  One
        attribute name was the whole gate.

        The test now asks five things a reload reproduces exactly and a
        three-line stand-in does not: it is a class; it is a module class;
        it is THIS class by name and by defining module; it DEFINES ITS OWN
        `__setattr__` AND `__delattr__` (`vars`, not `getattr` -- inherited
        ones are what `Unfrozen` had); and it carries a frozen set EQUAL to
        the live one, not merely present.  Equality rather than presence is
        the half that matters most: `frozenset()` is exactly what an
        attacker supplies and exactly what a reload does not.

        Never raises: a hostile `value` whose attribute access explodes is
        "not the same freeze", not an exception escaping `__setattr__`.
        """
        try:
            if not isinstance(value, type) or not issubclass(value, ModuleType):
                return False
            if value.__name__ != "_FrozenTier3Module":
                return False
            if value.__module__ != __name__:
                return False
            own = vars(value)
            if "__setattr__" not in own or "__delattr__" not in own:
                return False
            incoming = own.get("_FrozenTier3Module__FROZEN")
            if type(incoming) is not frozenset:
                return False
            return incoming == _FrozenTier3Module.__FROZEN
        except Exception:
            return False

    def __setattr__(self, name: str, value: object) -> None:
        if name == "__class__" and _FrozenTier3Module._is_the_same_freeze(value):
            ModuleType.__setattr__(self, name, value)
            return
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
