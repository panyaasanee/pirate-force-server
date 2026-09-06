r"""LANE-A / M2: the SHAPE of an answer to TriggerVital (0x1FB2) trigger id
2/3, with NO bytes in it yet.

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

So the block is not "we do not know the ids" (2 and 3 are measured, R308/
R318/R322A agree) and not "the client refuses our frame" (we have never
sent one) -- it is "nobody has yet cited a real answer frame this server
could send".  `NO_ORIGINAL_CAPTURE:` for the wire-level version of that
question: no pcap/journal of the ORIGINAL (non-pirate) server's own 0x1FB2
reply exists on this bridge.  Checked, per AGENTS.md section 7's four-source
rule, before writing that sentence:

    gamedata/tables/    grep -rli "1fb2" -> 0 hits
    external/           grep -rli "1fb2" -> 2 hits, both unrelated TSVs
                         (`PF_FIELD_VALIDATION.tsv`, `PF_RUNTIME_CLASSMAP.tsv`
                         name fields/classes, not a capture)
    archive/            grep -rli "1fb2\|original.*capture\|เซิร์ฟเดิม" ->
                         0 hits; `find -iname "*original*"` under archive/
                         and the repo root turns up only
                         `evidence_screens/REF_ORIGINAL_SERVER_*` (owner's
                         reference screenshots and clips of the ORIGINAL
                         server's SCREEN -- eyewitness, not wire) and two
                         PANYA-REFERENCE/GT078-ADDENDUM letters that are the
                         same kind of screen-level reference, e.g.
                         `archive/notes_to_chief_2026-08/20260827_1635_
                         PANYA-REFERENCE-original-server-combat-loop-*`
    notes_to_chief/consumed/  same two greps -> 0 pcap/journal hits
    find . -iname "*.pcap"  -> 0 hits anywhere in the repo

So this module's registry starts, and stays this round, with BOTH trigger
ids' candidate slots empty.  Filling either one without a cited VA + vital
id from LANE-UI would be exactly the guessed frame item 4(b) forbids.

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
  Filling a slot is a precondition for testing that, not a substitute for
  testing it.

THE SEAM, NAMED HONESTLY (for chief, one round out)
-----------------------------------------------------
``runtime.py:8692``'s TRIGGER_VITAL branch always does:

    self.rx_frames += 1
    lane_hooks.fire("vital_inbound_trigger_vital", session=self,
                     payload=bytes(parsed.nested_payload))
    return []

regardless of what any subscribed hook does, because ``fire()`` is
report-only by construction.  The GM_RUN_GM_COMMAND_VITAL_ID branch right
above it has the identical shape (also always ``return []``) -- it is NOT
the contrast case.  The real contrast is ``FOUNDATION_CREATE`` a little
further up, which builds its return list from a DIRECT call
(``self.foundation.create(...)``), never from ``fire()``.  This package
already has a house shape for "a lane needs to hand a value back to
runtime.py without going through the void-returning hook registry": the
``census_composer``/``choose_npc_responder`` pattern
(``lane_hooks/__init__.py``) -- a small keyed registry, gated by
``module_production_allowed()``, that the call site consults and calls
DIRECTLY, never through ``fire()``.  So the honest one-line ask is not
"read fire()'s result" (it has none) but: a NEW direct-call point of that
same shape, keyed by wire trigger id, that ``runtime.py``'s TRIGGER_VITAL
branch checks (after the existing ``fire()`` call, so the log-only hook
still runs unconditionally) and, only when
``candidate_for_trigger_id(wire_trigger_id)`` answers non-``None``, builds
its return list from that ``CandidateFrame``'s bytes instead of always
returning ``[]``.  Not requested as a code change this round -- item 4(b)
forbids sending anything until UI's letter lands; recorded here so the
wiring is one paragraph chief can act on the day it does, not a rediscovery.

THE REGISTRY'S SHAPE, AND WHY BOTH SLOTS ARE STILL ``None``
--------------------------------------------------------------
``CandidateFrame`` carries exactly what item 4(b) requires the candidate to
cite: a VA (the client function that PROVES this is the frame -- a string,
e.g. "sub_00ABCDEF"), the vital id the frame answers with, and the frame's
own bytes.  ``_CANDIDATES`` maps each of ``CANDIDATE_TRIGGER_IDS`` (2, 3) to
``None`` at import time and NOTHING in this module ever writes into it after
that -- the day LANE-UI's letter lands, filling one entry is the entire
change this file needs, per item 4(b)'s own framing ("filling in that dict
IS the whole change, not a new dispatch shape").
"""
from __future__ import annotations

from typing import NamedTuple

from .lane_hooks.lane_a_island_trigger_log import M2_OBSERVED_ISLAND_TRIGGER_IDS

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
_CANDIDATES: dict[int, CandidateFrame | None] = {
    trigger_id: None for trigger_id in CANDIDATE_TRIGGER_IDS
}


def trigger_id_guard_reason(wire_trigger_id: object) -> str | None:
    """``None`` when ``wire_trigger_id`` is one of ``CANDIDATE_TRIGGER_IDS``;
    otherwise the NAMED reason it is not.

    Same strict-on-type posture as ``world_m2_survey_plan.scene_guard_
    reason`` (bool rejected explicitly, since it subclasses ``int`` in
    Python and would otherwise pass a stray boolean off as a trigger id).
    Never raises.
    """
    if isinstance(wire_trigger_id, bool) or not isinstance(wire_trigger_id, int):
        return TRIGGER_ID_REFUSED_NOT_AN_INT
    if wire_trigger_id not in CANDIDATE_TRIGGER_IDS:
        return TRIGGER_ID_REFUSED_NOT_M2
    return None


def is_candidate_trigger_id(wire_trigger_id: object) -> bool:
    """Thin boolean view of ``trigger_id_guard_reason`` -- for a caller that
    only ever needed yes/no."""
    return trigger_id_guard_reason(wire_trigger_id) is None


def candidate_for_trigger_id(
    wire_trigger_id: int,
    registry: "dict[int, CandidateFrame | None] | None" = None,
) -> "CandidateFrame | None":
    """The candidate registered for ``wire_trigger_id``, returned UNCHANGED,
    or ``None``.

    ``None`` covers three cases this function deliberately does not
    distinguish for the caller (ask ``trigger_id_guard_reason`` first if the
    difference matters): ``wire_trigger_id`` is not an int, it is not one of
    ``CANDIDATE_TRIGGER_IDS``, or it IS one and nothing is registered for it
    yet.  Today every real call falls into the third case for both 2 and 3.

    ``registry`` defaults to this module's own ``_CANDIDATES`` and exists
    only so a test can pass a synthetic mapping without mutating production
    state -- never set from calling code outside a test.  Never raises.
    """
    if trigger_id_guard_reason(wire_trigger_id) is not None:
        return None
    table = _CANDIDATES if registry is None else registry
    return table.get(wire_trigger_id)


def registered_count(
    registry: "dict[int, CandidateFrame | None] | None" = None,
) -> int:
    """How many of ``CANDIDATE_TRIGGER_IDS`` currently have a real candidate.
    0 today, for both ids -- the whole point of this round's deliverable."""
    table = _CANDIDATES if registry is None else registry
    return sum(1 for trigger_id in CANDIDATE_TRIGGER_IDS if table.get(trigger_id) is not None)
