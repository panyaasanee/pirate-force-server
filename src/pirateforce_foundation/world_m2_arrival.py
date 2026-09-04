r"""LANE-A / M2: where a confirmed docking actually puts the player.

WHY THIS FILE EXISTS
--------------------
M2's pass bar has four beats: sail near an island -> a captain-report window
-> the player confirms -> **you are standing on island 2 (Prison Exile) and
island 3 (Spice Paradise)**.  This lane has built beats one and three:

* the survey-record encoder module encodes the proximity record (beat 1),
  called from no send path -- COO-DECISION 20260904_0747 item 3(b) forbids
  sending one before GT-228 measures real island XYZ, and COO-DECISION
  20260904_1147 item 2 adds that the first real provisioning must be an
  attended round.  It is NAMED here only in this indirect way, because that
  module's own guard test greps the whole repository for its name and a
  mention would be indistinguishable from an import.
* `world_m2_survey_plan` decides WHICH records this build would provision and
  WHICH handle each carries, and answers "is this echoed u16 one of ours".
* `lane_hooks/lane_a_enter_instance_log` walks the confirm frame (beat 3) and
  prints what arrived.

Beat four is where the confirm becomes a place to stand, and **for the
DOCKING path nothing joined it up**.  `confirm_resolution()` stops at a
`scene_name_tip_id` -- a number out of the client's text tables -- and from
there every reader has had to assume the rest: that the number is also the
wire `scene_id`, that the registry has a row for it, and that this tree can
compose an arrival for that row at all.

WHAT THIS MODULE CAN AND CANNOT TELL YOU -- READ THIS BEFORE THE COUNT
-----------------------------------------------------------------------
`arrival_readiness()` answers **"could this server compose an arrival for
these destinations"**.  That is a fact about this repository's own pin file
and code paths.  It is true on a server with no client attached, and it would
read the same on the day the first confirm frame arrives and the player does
not move.

It is therefore NOT a measurement of M2's pass bar, and the console fragment
is spelled `arrival_plan=` rather than `arrival=` so that the word on the line
matches what was actually checked.  **The check that fails when the player is
not standing on the island is an attended one and lives in the ticket after
GT-228, not here.**  Everything below is input well-formedness; pf-adversary
asked for that sentence in exactly those terms and it is the honest answer.

WHAT IT DOES NOT REBUILD, WHICH IS MOST OF IT
----------------------------------------------
This module is a JOIN, not a second scene-transition path.  The arrival
itself is composed by `world_scene_entry.resolve_entry`, which is the door
CORE-REQUEST-003/004 already wired at login and the same one
`columbus_quest_dispatch.resolve_columbus_arrival` goes through for the other
M2 crossing -- so the teleport tuple, the relocation rule, the ground
evidence check and the refusal vocabulary are all ITS, read back here rather
than recomputed.  A first draft of this file composed its own teleport tuple
out of `world_scene_travel.login_teleport_fields`; it produced identical bytes
for both M2 targets and was still wrong, because a second composer is a
second thing to keep in step.

    `via_login=False`, AND THE FLAG THIS MODULE CHECKS ITSELF INSTEAD.  The
    synthetic row handed to the door is not a character's persisted position,
    which is the case that kwarg exists to name, so it is passed -- but
    pf-adversary measured what passing it silently costs: `login_entry_allowed`
    stops applying, and this path is NOT the case that flag's own comment
    reserves the bypass for.  `resolve_columbus_arrival` resolves ONE
    hardcoded destination from a server-side dispatch path (`columbus_quest_
    dispatch`, spelled here as the identifier only: the bare word is a
    tripwire `tests/test_npc_interaction_wire.py` greps every module in this
    package for, and this file implements none of that behaviour); this
    function by contrast is
    parameterised over `world_m2_survey_plan.PLANNED_TRIGGER_IDS` and is
    reached from an INBOUND FRAME whose destination descends from a
    client-echoed u16.  A shut door is a kill switch somebody threw on
    purpose, so this module reads the flag itself and refuses with
    `ARRIVAL_REFUSED_DOOR_SHUT` before the door is ever asked.  A test pins
    the refusal; an earlier draft of this round pinned the BYPASS, which is
    the mistake this paragraph exists to keep from coming back.

    THE SYNTHETIC ROW HAS A SECOND COST, AND IT IS REFUSED RATHER THAN
    DOCUMENTED AWAY.  `resolve_entry`'s home branch keeps the row it was
    given instead of relocating to the pinned spawn -- correct for a login
    reading a real row, wrong for a fabricated one.  Fed `(0, 0, 0)` for
    trigger 152 (Port Royal is a real dock row, one plan-widening line away)
    it returned a deliverable order whose persisted `Position` was the scene
    origin, 9,679 units from the actual spawn: exactly the "a row nobody
    chose" shape GT-106 is about.  `arrival_order` now refuses any order
    whose position is still the synthetic row
    (`ARRIVAL_REFUSED_DOOR_KEPT_THE_SYNTHETIC_ROW`), which catches the home
    branch by its behaviour rather than by its scene id.

    THE RELOCATION REPORT ON THIS PATH IS AN ARTEFACT, ALWAYS.  Because the
    synthetic row is `(0, 0, 0)` and no M2 destination has pinned ground,
    `entry.relocated` is True and `entry.relocation_reason` is
    `no_pinned_ground_for_scene` for every order this module will ever
    produce.  `stored=(0.000,0.000,0.000)` in the door's own
    `WORLD_SCENE_RELOCATED` line is THIS MODULE's fabricated input, not a
    player's position, and the reason names a gap in our pins rather than
    anything about this arrival.  `ArrivalOrder.relocation_is_an_artefact`
    is True by construction and a test pins it, so a reader who meets the
    field has been told before they have to guess.

    AND THE DOOR'S CONSOLE LINES MUST NOT BE PRINTED ON THIS PATH.  They
    carry the words `scene` and `island` (`WORLD_SCENE scene_id=2 ...
    name=Prison_Exile_Island`), which RE-227 nonclaim 3 forbids beside a
    confirm frame, and `WORLD_SCENE` is the line GT-079 pins as "this is
    where the boot is putting the player" -- printed for a frame with
    `bytes_out=0` it reads as an arrival that did not happen.  They are
    swallowed here and `ArrivalOrder` does not offer them.

So what is genuinely THIS module's is narrow: the handle, the crosswalk from
tip id to wire scene id, the door flag, and the discipline of refusing by
name rather than raising into a frame handler that has a live player waiting.

WHAT IT MEASURED, AND HOW STRONG EACH COLUMN ACTUALLY IS
---------------------------------------------------------
`world_island_dock_table` carries, per destination, a `wire_scene_id_status`
of "PROVEN" or "CANDIDATE", and for M2's two targets they differ: row 153
(Prison Exile Island, tip id 2) is PROVEN, row 154 (Spice Paradise Island,
tip id 3) is CANDIDATE.  That status is the bridge RE queue's, not this
module's, and this module does not change it.

What this module does is CHECK the crosswalk instead of taking the number on
faith.  Both checks pass for both M2 rows -- and they are NOT of equal
strength, which an earlier draft of this docstring got wrong by calling them
"two independent columns":

    names_agree   TWO FILES.  `dock.name` is the client's own
                  `s_Trigger_NAME` out of `TEXTDATA_TH__Trigger_TIP.tsv`
                  (row 153 is literally " Prison Exile Island ").
                  `registry.scene_name_ascii` is an ASCII rendering of the
                  Chinese `s_SCENE_NAME`.  Different files, different
                  authors.
    models_agree  ONE FILE, TWICE.  `dock.scene_model` and the registry's
                  `model_id` both come from `CONSTDATA_TH__SCENE_NAME.tsv`
                  -- measured: `world_island_dock_table.
                  CONST_SCENE_NAME_SHA256` and the registry's own
                  `provenance.scene_name_table_sha256` are the same
                  e38114a8...5d60b.  It can catch a transcription slip by
                  one of the two readers and NOTHING else.  It is kept for
                  that, and it is not corroboration.

    STATED AT ITS TRUE STRENGTH, because it is easy to overread: both sides
    are keyed by the SAME id, so this is not independent proof that the wire
    `scene_id` field equals that id.  What it rules out is the cheaper and
    likelier failure -- an off-by-one or a misaligned column -- which would
    show up as two different island names against one number.  It does not
    rule out the whole table being shifted in a way both readings inherited.
    The thing that would settle it is what settled scene 2: a live client
    standing in it.

    AND THE NAME CHECK HAS A MEASURED FALSE-REFUSAL RATE.  Across the ten
    dock rows that have a registry row, nine agree and one does not: trigger
    161 is "Hell Volcanic Island" against the registry's "Hell Volcano
    Island" -- one English rendering of one Chinese name against another,
    not a broken crosswalk.  So a name disagreement is reported as
    `ARRIVAL_REFUSED_NAME_DISAGREEMENT`, kept apart from
    `ARRIVAL_REFUSED_MODEL_DISAGREEMENT`, so that an attended tester meeting
    the refusal is not told the id crosswalk is broken when what differs is
    a translation.  It stays fail-closed: this lane does not fuzzy-match
    names to widen a plan.

    A CITATION CORRECTED, BECAUSE ITS OWN SOURCES REFUSE IT.  An earlier
    draft of this docstring wrote "R306 warped a live client 2 -> 14 -> 3 ->
    4 -> 5 with full NPC rosters (GT-210 / GT-212 PASS)".  Stated properly:
    `pf_bridge/NOW.md` (COO, 2026-09-04) records `/warp` succeeding five
    times across those scenes with NPCs present, and `docs/GM_LANE.md`'s R306
    entry records the TeleportVital halves passing five times -- a WIRE
    result naming no scenes.  This repository's own files say GT-210 and
    GT-212 are OPEN, not PASS (`lane_hooks/lane_a_choose_npc_roster_scenes`:
    "Nobody has yet clicked an NPC on scene 3 ... whether the client draws it
    is GT-210 for scene 3 and GT-212 for the nine").  So the client-observable
    layer is NOT established for scene 3 here, and
    `SceneDestination.sent_before` staying False for it is consistent with
    this tree rather than stale.  What the round's letter raises with COO is
    the DISCREPANCY between NOW.md's account and `MEASURED_SCENE_IDS`, for
    COO to resolve -- not a widening this module assumes.  `client_confirmed`
    in the report is that field, printed as it stands.

~~WHY IT REFUSES EVERY HANDLE TODAY, AND WHY THAT IS NOT A BUG~~
WHAT IT ANSWERS NOW THAT GT-228 HAS REPORTED
-------------------------------------------------------------
`arrival_order()` starts by asking `world_m2_survey_plan.confirm_resolution`
whether the handle is one this build issued.  ~~With `MEASURED_XYZ` empty
that is False for every possible u16, so every call today returns a refusal
of `ARRIVAL_REFUSED_HANDLE_NOT_ISSUED`.~~

That day arrived: GT-228 reported PASS (R308) and `MEASURED_XYZ` carries
both M2 destinations, so **`arrival_readiness()` is 2/2 and both targets
compose a real, deliverable order** -- Prison Exile at wire scene 2 and
Spice Paradise at wire scene 3, each with the door's own teleport tuple and
spawn position.  It happened with no code change here, exactly as the
paragraph below promised, which is why that promise is left standing rather
than rewritten:

That is fail-closed ON DATA, not behind a flag, and it is the same shape the
rest of this chain already has: the day GT-228 fills two lines of
`MEASURED_XYZ`, the plan starts issuing handles and this module starts
composing real orders, with no code change and no switch to remember.  It
also means this module cannot be the thing that moves a player early -- it
has no send path of its own, and even its ANSWER is closed until the
provisioning half opens in an attended round.

BOTH VALUES A CONFIRM CAN CARRY REACH THE SAME PLACE (round `16uvmp`).  The
first provisioning trial writes the destination number (2/3) into the record
instead of the plan's 0xA0xx handle, so that is what its confirm echoes;
`confirm_resolution` resolves both and this module reads its `trigger_id`,
so an order composed from either value is the same order.  The difference
is confidence, and it stays on the plan's console fragment where a grader
reads it (`match=trial confidence=low`), not in the order: a destination is
a destination or it is a refusal.

IT SENDS NOTHING, AND IT WRITES NOTHING
----------------------------------------
No frame is composed, no bytes are queued, no character row is written, no
session is touched.  `teleport_fields` and `position` are VALUES -- the ones
`resolve_entry` produced -- and the caller that would actually put them on
the wire lives in `runtime.py`, which is the chief's file.

WHAT THIS MODULE DOES NOT CLAIM
-------------------------------
* NOT that the client accepts a handle of the server's choosing.  That
  nonclaim belongs to `world_m2_survey_plan` and is unchanged here.
* NOT that `TeleportVital` is the frame that performs the change.  RE-227
  nonclaim 6 leaves that a candidate.
* NOT a level check.  `min_level` travels with the order because the client's
  own tables gate Spice Paradise Island at 25, and `level_refusal()` is
  offered for a caller that wants to enforce it -- but `arrival_order()` is
  level-blind by construction.
* NOT a promise the character stays there.  `persist_allowed` and
  `return_ticket_required` are carried, not acted on.
* NOT a measurement of M2.  See "WHAT THIS MODULE CAN AND CANNOT TELL YOU".

HOW TO RE-DERIVE
-----------------
    python -c "import sys; sys.path.insert(0,'src'); \
        from pirateforce_foundation import world_m2_arrival as a; \
        print(a.console_report())"
"""
from __future__ import annotations

from typing import Any, NamedTuple

from . import world_island_dock_table as islands
from . import world_m2_survey_plan as plan
from . import world_scene_entry as entry_door
from . import world_scene_travel as travel
from .model import Position


# The console token this module's report opens each line with.  Greppable,
# and it must stay distinct from `LANE_A_ENTER_INSTANCE` (the confirm
# walker's) and from `WORLD_SCENE` (the entry door's GT-079 line) -- a test
# asserts the distinctness rather than just asserting the token appears,
# because a grader greps an attended log by these strings.
TOKEN = "LANE_A_M2_ARRIVAL"

# The synthetic row handed to `resolve_entry`.  Zeroed, exactly as
# `columbus_quest_dispatch` builds its own: the player is not in the
# destination yet, so there is no stored position to read.  Never a
# character's row -- and never trusted to come back unchanged either, see
# `ARRIVAL_REFUSED_DOOR_KEPT_THE_SYNTHETIC_ROW`.
_SYNTHETIC_SEQ = 0
_SYNTHETIC_XYZ = (0.0, 0.0, 0.0)
_SYNTHETIC_HEADING = 0.0

# Refusals THIS module owns.  The door's own refusals are reported in ITS
# vocabulary instead, tagged by `door_refusal()`.
ARRIVAL_REFUSED_HANDLE_NOT_ISSUED = "ARRIVAL_REFUSED_HANDLE_NOT_ISSUED"
ARRIVAL_REFUSED_NO_DESTINATION_ROW = "ARRIVAL_REFUSED_NO_DESTINATION_ROW"
ARRIVAL_REFUSED_NO_REGISTRY_ROW = "ARRIVAL_REFUSED_NO_REGISTRY_ROW"
# Split apart on purpose: a name difference between two renderings of one
# Chinese name (measured: 1 of 10 rows) must not be reported to an attended
# tester in the same words as a model-id mismatch, which really would mean
# the id crosswalk is wrong.
ARRIVAL_REFUSED_NAME_DISAGREEMENT = "ARRIVAL_REFUSED_NAME_DISAGREEMENT"
ARRIVAL_REFUSED_MODEL_DISAGREEMENT = "ARRIVAL_REFUSED_MODEL_DISAGREEMENT"
# The registry's kill switch, read HERE because `via_login=False` stops the
# door from reading it.  See the docstring paragraph that owns this.
ARRIVAL_REFUSED_DOOR_SHUT = "ARRIVAL_REFUSED_DOOR_SHUT"
# The door handed our fabricated row straight back instead of relocating to
# a pinned spawn (its home branch does this by design).  Refused rather than
# persisted: a caller writing that row writes the scene origin.
ARRIVAL_REFUSED_DOOR_KEPT_THE_SYNTHETIC_ROW = (
    "ARRIVAL_REFUSED_DOOR_KEPT_THE_SYNTHETIC_ROW"
)

# The prefix a `SceneEntryRefused` reason is reported under.  Kept as its own
# reason string rather than translated into a local constant: inventing a
# parallel vocabulary for the door's refusals is how two spellings of the
# same failure end up in two console lines.
ARRIVAL_REFUSED_BY_DOOR = "ARRIVAL_REFUSED_BY_DOOR"

# The refusal a caller that DOES enforce the client's level gate would use.
# Never returned by `arrival_order()` -- see the docstring's nonclaim.
ARRIVAL_REFUSED_BELOW_MIN_LEVEL = "ARRIVAL_REFUSED_BELOW_MIN_LEVEL"

# The registry, loaded at most once per process for callers that pass none.
#
# WHY A CACHE.  pf-adversary measured the console fragment at 0.671 ms per
# confirm frame, effectively all of it `json.loads` plus a full re-validation
# of the pin file, on the connection's listener thread, for a player who is
# not moving -- client-triggerable off the same dispatch path a previous
# round capped `_MAX_HEX_BYTES` for.  The pin is static for a process (the
# runtime loads it once at boot for the same reason), so reading it once here
# is the same decision that module already made.  A caller that passes its
# own registry never touches this.
_CACHED_REGISTRY: Any | None = None


def door_refusal(reason: str) -> str:
    """`world_scene_entry`'s refusal reason, tagged with whose it is."""
    return f"{ARRIVAL_REFUSED_BY_DOOR}:{reason}"


class CrosswalkRow(NamedTuple):
    """One M2 destination, checked against the scene registry and the door.

    ``names_agree`` and ``models_agree`` are ``None`` -- not ``False`` --
    when there was no registry row to compare against.  Nothing was
    compared, and reporting an absence as a disagreement is the mistake this
    module refuses on the ``scene_model`` column two functions down.

    ``door_refusal_reason`` is ``None`` both when the door composed an
    arrival and when the door was never asked; ``door_was_asked`` tells the
    two apart.

    ``entry`` is the ``SceneEntry`` the door composed for this row, or None.
    It is carried so that ``arrival_order`` uses the SAME resolution the
    readiness count did, rather than resolving a second time.
    """

    trigger_id: int
    dock_name: str
    dock_scene_model: str | None
    wire_scene_id: int
    registry_name: str | None
    registry_model_id: str | None
    names_agree: bool | None
    models_agree: bool | None
    door_open_at_login: bool | None
    door_was_asked: bool
    door_refusal_reason: str | None
    entry: Any | None
    wire_scene_id_status: str
    confirmed_by_a_client: bool | None
    min_level: int
    refusal: str | None

    @property
    def ready(self) -> bool:
        """Whether everything EXCEPT the handle is in place for this row."""
        return self.refusal is None


class ArrivalOrder(NamedTuple):
    """Everything a caller needs to land a confirming player, or the reason.

    ``refusal`` is None on a complete order and a reason string otherwise.
    On a refusal every field that could not be established is None, rather
    than a zero a caller could mistake for an answer.

    ``teleport_fields`` and ``position`` are `world_scene_entry`'s, read off
    the ``SceneEntry`` it composed -- not rebuilt here.

    ``relocation_is_an_artefact`` is True on every order this module
    produces, by construction, and is here so the field cannot be read as a
    fact about the player -- see the docstring paragraph that owns it.  The
    door's console lines are deliberately NOT carried: they name a scene and
    an island beside a frame with `bytes_out=0`.
    """

    handle: int
    trigger_id: int | None
    destination_name: str | None
    wire_scene_id: int | None
    wire_scene_id_status: str | None
    wire_scene_id_confirmed_by_a_client: bool | None
    teleport_fields: tuple[int, int, float, float, float] | None
    position: Position | None
    population_source: str | None
    return_ticket_required: bool | None
    relocation_is_an_artefact: bool | None
    min_level: int | None
    persist_allowed: bool | None
    refusal: str | None

    @property
    def deliverable(self) -> bool:
        return self.refusal is None


def _registry(registry: Any = None) -> Any:
    """The scene registry: the caller's, or this process's cached load.

    See `_CACHED_REGISTRY` for why the None path caches.  A malformed pin
    file raises here, from the loader, and is deliberately NOT caught --
    reporting a broken file as "this destination is not pinned" would send
    the reader hunting for a destination that is present.  A test pins that
    it propagates, so a later round cannot quietly turn a broken pin into a
    quiet `arrival_plan=1/2`.
    """
    global _CACHED_REGISTRY
    if registry is not None:
        return registry
    if _CACHED_REGISTRY is None:
        _CACHED_REGISTRY = travel.load_scene_registry()
    return _CACHED_REGISTRY


def forget_cached_registry() -> None:
    """Drop the cached load.  For tests, and for a caller that reloads pins."""
    global _CACHED_REGISTRY
    _CACHED_REGISTRY = None


def _registry_row(wire_scene_id: int, registry: Any) -> Any | None:
    """The registry's row for a wire scene id, or None when it has none.

    `SceneRegistry.__getitem__` raises `KeyError` for an unpinned id; a
    missing row is an ordinary answer here, not an exception, because the
    whole point of this module is to name that case instead of raising it at
    a caller that is mid-confirm.
    """
    try:
        return registry[wire_scene_id]
    except KeyError:
        return None


def synthetic_row(wire_scene_id: int) -> Position:
    """The row handed to the entry door for a docking arrival.

    PUBLIC so a test can pin every field of it.  The destination's id, and
    zeroes for everything else: a docking player has no stored position in
    the scene they are arriving in, and reading their real row here would be
    the login case this call is explicitly not.
    """
    x, y, z = _SYNTHETIC_XYZ
    return Position(
        wire_scene_id, _SYNTHETIC_SEQ, x, y, z, _SYNTHETIC_HEADING
    )


def _resolve_through_the_door(wire_scene_id: int, registry: Any):
    """``(entry, None)`` or ``(None, reason)`` -- the door's verdict.

    `emit` is swallowed: the door's lines name a scene and an island and
    claim an arrival, none of which may appear beside a confirm frame that
    sent no bytes (RE-227 nonclaim 3; GT-079's own `WORLD_SCENE` line).  A
    test pins the swallow by asserting nothing reaches stdout.
    """
    try:
        return (
            entry_door.resolve_entry(
                synthetic_row(wire_scene_id),
                registry=registry,
                emit=lambda _line: None,
                via_login=False,
            ),
            None,
        )
    except entry_door.SceneEntryRefused as refused:
        return (None, refused.reason)


def _door_kept_the_synthetic_row(wire_scene_id: int, entry: Any) -> bool:
    """Whether the door handed our fabricated row back as the arrival.

    True for `resolve_entry`'s home branch, which keeps the row it was given
    rather than relocating to the pinned spawn -- right for a login reading a
    real row, wrong for the invented one this module supplies.  Checked by
    VALUE rather than by scene id so any future branch with the same
    behaviour is caught too.
    """
    return entry.position == synthetic_row(wire_scene_id)


def _row(trigger_id, dock, wire_scene_id, registry_row, **fields) -> CrosswalkRow:
    """One `CrosswalkRow`, with the fields every branch shares filled in."""
    base: dict[str, Any] = {
        "trigger_id": trigger_id,
        "dock_name": dock.name,
        "dock_scene_model": dock.scene_model,
        "wire_scene_id": wire_scene_id,
        "registry_name": None if registry_row is None else registry_row.scene_name_ascii,
        "registry_model_id": None if registry_row is None else registry_row.model_id,
        "names_agree": None,
        "models_agree": None,
        "door_open_at_login": (
            None if registry_row is None else registry_row.login_entry_allowed
        ),
        "door_was_asked": False,
        "door_refusal_reason": None,
        "entry": None,
        "wire_scene_id_status": dock.wire_scene_id_status,
        "confirmed_by_a_client": (
            None if registry_row is None else registry_row.sent_before
        ),
        "min_level": dock.min_level,
        "refusal": None,
    }
    base.update(fields)
    return CrosswalkRow(**base)


def crosswalk_row(trigger_id: int, registry: Any = None) -> CrosswalkRow | None:
    """Check one destination against the scene registry and the entry door.

    Returns None only when ``trigger_id`` is not a destination row at all --
    an input error, distinct from every refusal below, which are states of a
    real destination.
    """
    dock = islands.destination_for_trigger_id(trigger_id)
    if dock is None:
        return None
    loaded = _registry(registry)
    wire_scene_id = dock.scene_name_tip_id
    registry_row = _registry_row(wire_scene_id, loaded)
    if registry_row is None:
        # Nothing was compared, so `names_agree` / `models_agree` stay None.
        return _row(
            trigger_id, dock, wire_scene_id, None,
            refusal=ARRIVAL_REFUSED_NO_REGISTRY_ROW,
        )
    names_agree = dock.name == registry_row.scene_name_ascii
    # A dock row whose CONSTDATA table has no entry carries `scene_model =
    # None` (true for tip ids 12/15/16).  That is an ABSENT column, not a
    # disagreement -- an absence read as a mismatch is the mirror of the
    # absence-read-as-a-zero mistake `world_island_dock_table` warns about.
    models_agree = (
        dock.scene_model is None or dock.scene_model == registry_row.model_id
    )
    compared = {"names_agree": names_agree, "models_agree": models_agree}
    if not models_agree:
        return _row(
            trigger_id, dock, wire_scene_id, registry_row,
            refusal=ARRIVAL_REFUSED_MODEL_DISAGREEMENT, **compared
        )
    if not names_agree:
        return _row(
            trigger_id, dock, wire_scene_id, registry_row,
            refusal=ARRIVAL_REFUSED_NAME_DISAGREEMENT, **compared
        )
    if not registry_row.login_entry_allowed:
        # The registry's kill switch, read here because `via_login=False`
        # stops the door from reading it.  The door is not asked at all: a
        # destination somebody shut is not a destination to compose for.
        return _row(
            trigger_id, dock, wire_scene_id, registry_row,
            refusal=ARRIVAL_REFUSED_DOOR_SHUT, **compared
        )
    entry, door_reason = _resolve_through_the_door(wire_scene_id, loaded)
    if entry is None:
        return _row(
            trigger_id, dock, wire_scene_id, registry_row,
            door_was_asked=True, door_refusal_reason=door_reason,
            refusal=door_refusal(door_reason), **compared
        )
    if _door_kept_the_synthetic_row(wire_scene_id, entry):
        return _row(
            trigger_id, dock, wire_scene_id, registry_row,
            door_was_asked=True, entry=entry,
            refusal=ARRIVAL_REFUSED_DOOR_KEPT_THE_SYNTHETIC_ROW, **compared
        )
    return _row(
        trigger_id, dock, wire_scene_id, registry_row,
        door_was_asked=True, entry=entry, **compared
    )


def crosswalk_rows(registry: Any = None) -> tuple[CrosswalkRow, ...]:
    """Every M2 destination the survey plan plans for, checked.

    Driven by ``world_m2_survey_plan.PLANNED_TRIGGER_IDS`` rather than by a
    list of its own, so widening the plan widens this report in the same
    edit and the two can never disagree about which islands M2 is about.
    """
    loaded = _registry(registry)
    rows = []
    for trigger_id in plan.PLANNED_TRIGGER_IDS:
        row = crosswalk_row(trigger_id, loaded)
        if row is not None:
            rows.append(row)
    return tuple(rows)


def arrival_readiness(registry: Any = None) -> tuple[int, int]:
    """``(ready, planned)`` -- the arrival half's INPUTS, handle aside.

    Read the docstring section "WHAT THIS MODULE CAN AND CANNOT TELL YOU"
    before quoting this number: it is about this repository's pin file, not
    about a player standing anywhere.

    ``planned`` counts every id in the survey plan, including one whose dock
    row is missing entirely, so the pair can never read "0 of 0 -- fine".
    """
    rows = crosswalk_rows(registry)
    return (sum(1 for row in rows if row.ready), len(plan.PLANNED_TRIGGER_IDS))


def _refused(handle: int, reason: str, **known: Any) -> ArrivalOrder:
    """A refusal carrying only the fields that were actually established."""
    fields: dict[str, Any] = {
        "handle": handle,
        "trigger_id": None,
        "destination_name": None,
        "wire_scene_id": None,
        "wire_scene_id_status": None,
        "wire_scene_id_confirmed_by_a_client": None,
        "teleport_fields": None,
        "position": None,
        "population_source": None,
        "return_ticket_required": None,
        "relocation_is_an_artefact": None,
        "min_level": None,
        "persist_allowed": None,
        "refusal": reason,
    }
    fields.update(known)
    return ArrivalOrder(**fields)


def arrival_order(handle: int, registry: Any = None) -> ArrivalOrder:
    """The complete order for a confirmed docking, or the reason there is none.

    LEVEL-BLIND BY CONSTRUCTION -- see ``level_refusal``.  Never raises a
    refusal: every state this can meet comes back as a reason string, because
    the caller this is written for is a frame handler with a live player
    waiting, and `SceneEntryRefused` escaping there would unwind the
    connection's listener thread (that class's own docstring says so).

    A malformed registry FILE is deliberately not caught -- see ``_registry``
    -- and a test pins that it propagates rather than becoming a quiet
    refusal.  PASS ``registry`` from the load `runtime.py` already does at
    boot if you want that fault to surface at server start instead.
    """
    resolution = plan.confirm_resolution(handle)
    if not resolution.issued or resolution.trigger_id is None:
        return _refused(handle, ARRIVAL_REFUSED_HANDLE_NOT_ISSUED)
    trigger_id = resolution.trigger_id
    # Loaded once and passed down, so the row the crosswalk approved is the
    # row the door was asked about.
    loaded = _registry(registry)
    row = crosswalk_row(trigger_id, loaded)
    if row is None:
        # Unreachable while `confirm_resolution` only issues handles for dock
        # rows; kept because "unreachable" is a property of today's plan, not
        # of this function's inputs.
        return _refused(
            handle, ARRIVAL_REFUSED_NO_DESTINATION_ROW, trigger_id=trigger_id
        )
    established = {
        "trigger_id": trigger_id,
        "destination_name": row.dock_name,
        "wire_scene_id": row.wire_scene_id,
        "wire_scene_id_status": row.wire_scene_id_status,
        "wire_scene_id_confirmed_by_a_client": row.confirmed_by_a_client,
        "min_level": row.min_level,
    }
    if row.refusal is not None:
        return _refused(handle, row.refusal, **established)
    # THE SAME resolution the crosswalk (and therefore the readiness count)
    # used -- carried on the row rather than resolved a second time, so the
    # two can never disagree and the frame path pays for one.
    entry = row.entry
    target = _registry_row(row.wire_scene_id, loaded)
    if entry is None or target is None:     # pragma: no cover - row said yes
        return _refused(handle, ARRIVAL_REFUSED_NO_REGISTRY_ROW, **established)
    return ArrivalOrder(
        handle=handle,
        teleport_fields=entry.teleport_fields,
        position=entry.position,
        population_source=entry.population_source,
        return_ticket_required=entry.return_ticket_required,
        relocation_is_an_artefact=entry.relocated,
        persist_allowed=target.persist_position_allowed,
        refusal=None,
        **established,
    )


def level_refusal(order: ArrivalOrder, character_level: int) -> str | None:
    """``ARRIVAL_REFUSED_BELOW_MIN_LEVEL`` when the client's own table would
    gate this character out of this destination, else None.

    Offered, never applied.  The gate is the CLIENT's (`n_SCENE_LV`), and
    nothing in this project has measured what the client does when a
    below-level character is put in the scene anyway -- so enforcing it here
    would be this lane choosing a behaviour, and reporting it is not.
    """
    if order.min_level is None:
        return None
    return (
        ARRIVAL_REFUSED_BELOW_MIN_LEVEL
        if character_level < order.min_level
        else None
    )


def console_annotation(registry: Any = None) -> str:
    """The ASCII fragment the confirm hook appends to its own line.

    Says NOTHING about what the confirmed u16 means -- no destination name,
    no wire id, no trigger id -- for the same reason
    `world_m2_survey_plan.console_annotation` does not: RE-227 nonclaim 3.

        `arrival_plan=2/2`

    SPELLED `arrival_plan`, NOT `arrival`, and the word is the whole point:
    this counts destinations whose INPUTS are well-formed in this
    repository's pin file.  It would read `2/2` on a server that had never
    seen a frame, and it will read `2/2` on the day a confirm arrives and the
    player does not move.  Beside `provisioned=0` it says the landing half's
    inputs are ready and no record was sent; it does not say anybody landed.
    """
    ready, planned = arrival_readiness(registry)
    return f"arrival_plan={ready}/{planned}"


def console_report(registry: Any = None) -> str:
    """A multi-line ASCII report of the arrival half, one line per row.

    NOT a hook line: no point fires this today, so it is written for a person
    at a terminal and for the attended ticket that follows GT-228.  It names
    destinations, which is exactly why it is NOT the confirm hook's line.
    """
    ready, planned = arrival_readiness(registry)
    lines = [f"{TOKEN} ready={ready}/{planned}"]
    for row in crosswalk_rows(registry):
        lines.append(
            f"{TOKEN} trigger={row.trigger_id}"
            f" name={islands.console_safe(row.dock_name).replace(' ', '_')}"
            f" wire_scene_id={row.wire_scene_id}"
            f" names_agree={_yes_no_na(row.names_agree)}"
            f" models_agree={_yes_no_na(row.models_agree)}"
            f" door_asked={'yes' if row.door_was_asked else 'no'}"
            f" status={row.wire_scene_id_status}"
            f" client_confirmed={_yes_no_na(row.confirmed_by_a_client)}"
            f" min_level={row.min_level}"
            f" refusal={row.refusal or 'none'}"
        )
    return "\n".join(lines)


def _yes_no_na(value: bool | None) -> str:
    """`yes` / `no` / `n_a` -- an absence printed as an absence.

    `n_a` and not `no`: a console that answers a question nobody could ask is
    how "there was no row to compare" gets read as "the two names differ".
    """
    if value is None:
        return "n_a"
    return "yes" if value else "no"
