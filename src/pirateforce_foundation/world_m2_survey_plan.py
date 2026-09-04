r"""LANE-A / M2: which proximity records this server would provision, what
handle each one carries, and whether a confirm frame's echo is one of ours.

WHY THIS FILE EXISTS
--------------------
M2's pass bar is "sail near an island -> a captain-report window -> confirm ->
you are standing on island 2 (Prison Exile) and island 3 (Spice Paradise)".
RE-227 (static, full CFG census; pf_bridge/notes_to_chief/20260904_0724) made
that a three-part exchange, and COO-DECISION 20260904_0747 accepted it as the
working hypothesis:

    1. the server provisions a proximity record per destination, carrying an
       opaque u16 and an XYZ triple;
    2. the client, on its own contact tick, compares that triple against the
       player's position (squared distance <= 250000, i.e. <= 500 units) and
       pops the captain report LOCALLY -- no frame reaches us;
    3. the player confirms, and the client sends `NavigationEx_
       EnterInstanceVital` (0xC723) with THAT SAME u16 copied unchanged.

Round `qz4p8n` built the two ends: the record encoder (never called from any
send path -- COO-DECISION 0747 item 3(b) forbids sending one until real
island XYZ is measured) and the log-only walker for step 3
(`lane_hooks/lane_a_enter_instance_log.py`, on main as part of `#720`).

What sat between them, unwritten, is the part that is neither bytes nor a
hook: WHICH records, with WHICH handle, and -- when a confirm comes back --
WHICH destination that handle was issued for.  Two rounds of this lane have
called the u16 "opaque" and printed it raw, correctly, because nothing proves
what the CLIENT thinks it means.  This module adds the only reading of it
that does not need the client's opinion at all: **it is the server's own
handle, and the server is the one who picks it.**  RE-227's item 2 is that
the field is copied unchanged; a value we chose and then see come back is
ours by construction, not by interpretation.

WHY IT PROVISIONS NOTHING TODAY, AND WHY THAT IS THE DELIVERABLE
----------------------------------------------------------------
`MEASURED_XYZ` below is EMPTY.  No destination in this project has a measured
position in the sea the player sails, so `planned_records()` returns `()` and
`provisionable_count()` is 0.  Every function here is fail-closed around that
fact rather than around a flag: no XYZ, no record, no handle issued, and
`confirm_resolution()` answers "not issued by us" for every possible u16.

The day `GT-228` reports the two coordinate triples, this file changes by
DATA ONLY -- two lines in `MEASURED_XYZ` -- and the plan becomes non-empty on
its own.  That is the point of writing it now, while the measurement is
outstanding, instead of writing it in the same round that has to also wire a
send path.

WHY GT-228 IS THE SOURCE, MEASURED THIS ROUND RATHER THAN ASSERTED
------------------------------------------------------------------
NOW.md says the XYZ "must not be guessed, GT-228 reading the HUD on contact
is the source".  The obvious cheaper objection -- "the client ships placement
files with XYZ in them, read it from there" -- has been half-answered before:
LANE-A round `zk50rd` (2026-09-04 05:25) measured `Bg3001` (scene 126, the
ocean PANEL) and found four island actors, none of them M2's two targets.

WHICH SCENE THE PLAYER SAILS IN IS ITSELF TWO ANSWERS, and both had to be
opened.  `GT-228` is written to be run in scene 126 -- that is where R307 put
the ship on THIS build, and the ticket's own screenshots are named `S126-*`.
The other candidate is the block of "character becomes a ship" scenes that
GT-106's attended result reached through Port Royal's Columbus.  Only the
first had ever been checked.  This round opened the second, in a `pf_bridge`
clone, against `gamedata/`:

    scene 17..23 = Bg1001..Bg1007, `n_SCENE_TYPE 4` -- the "character becomes
    a ship" scenes (the crosswalk letter of 2026-08-27 10:50, and GT-106's
    attended result putting the player into scene 17 through Port Royal's
    Columbus).  Their placement files DO carry XYZ, 8/8/8/10/13/20/12 rows:

        Bg1001  8 placements, sets Mob_set_1..6
        Bg1002  8            sets Mob_set_1..5,7
        Bg1003  8            sets Mob_set_1..5
        Bg1004 10 / Bg1005 13 / Bg1006 20 / Bg1007 12

    and every one of those seven scenes carries `n_CLINE_TYPE = 4294967295`
    (0xFFFFFFFF) in `CONSTDATA_TH__SCENE_NAME.tsv` -- the no-cast marker.
    The Mob-Set numbers in those files therefore resolve through NO CLINE
    block, so no committed table names a single one of those placements.

    => one candidate sea holds positions with no names; the other (`Bg3001`,
    the scene GT-228 is actually run in) holds names that are not M2's
    targets.  Neither can supply "the XYZ of island 2 and island 3".  GT-228
    stays the source not because a letter says so but because both cheaper
    sources were opened and measured empty.

Re-derive (both in a `pf_bridge` clone):

    awk -F'\t' 'NR==1 || ($1>=17 && $1<=23) {print $1"\t"$2"\t"$7"\t"$9}' \
        gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv
    for s in Bg1001 Bg1002 Bg1003 Bg1004 Bg1005 Bg1006 Bg1007; do \
        awk -F'\t' 'NR>1{print $2"\t"$6"\t"$7"\t"$8}' \
            gamedata/scene/$s/$s.placements.tsv; done

THE HANDLE RANGE, AND THE ONE LINE TO CHANGE IF IT IS WRONG
-----------------------------------------------------------
`SURVEY_HANDLE_BASE` is 0xA000 and the handle for a destination is
`base + its ordinal in the dock table`.  The value is arbitrary ON PURPOSE:
RE-227 proves the field is copied unchanged and proves nothing else, so a
distinctive range far from any id this project already traffics in (trigger
ids 152..164, scene ids 1..16, placement indices) makes "did this echo come
from us?" a real question with a real answer, instead of a coincidence that
0x0099 is both a trigger id and a plausible client-side number.

    NONCLAIM, AND THE FAILURE IT WOULD PRODUCE: nothing proves the client
    ACCEPTS an arbitrary value here.  If it validates the u16 against a table
    of its own, an 0xA0xx record would be dropped and the captain report
    would never pop -- which looks exactly like "the record never arrived".
    If a capture ever shows that, `SURVEY_HANDLE_BASE` is the single line to
    change (to `152`, making the handle the trigger id), and every function
    here follows.  That is why the base is a constant and not arithmetic
    spread across the file.

WHAT THIS MODULE DOES NOT CLAIM
-------------------------------
* NOT that the u16 means anything to the CLIENT.  `confirm_resolution()`
  answers only "is this a handle THIS BUILD issued", and today it answers no
  for every value because this build issues none.  RE-227 nonclaim 3 and the
  chief letter of 09:10 both stand: the console still prints the value raw.
* NOT that the confirm's destination scene id is a wire scene id.  Rows carry
  `wire_scene_id_status` from the dock table -- "PROVEN" for Prison Exile
  Island (2), "CANDIDATE" for Spice Paradise Island (3) -- and a caller that
  turns a confirm into a scene change must read that field, not the number
  beside it.  This module refuses to collapse the two.
* NOT a send path.  Nothing here composes, queues, or returns bytes, and the
  record encoder is deliberately not imported (its own grep guard requires
  that no other file in this repository so much as names it).
* NOT a level check.  `min_level` travels with the row for the attended
  ticket's preconditions; nothing here enforces it.
"""
from __future__ import annotations

from typing import NamedTuple

from . import world_bg3001_identity as bg3001
from . import world_island_dock_table as islands


# The opaque u16 handles this server issues.  Arbitrary by design; see the
# docstring's "one line to change" note before touching it.
#
# [LANE-A ASSUMPTION - awaiting COO confirmation, letter 20260904_1036]: that
# the client accepts a handle of the server's own choosing at all.  RE-227
# proves only that the value is copied back unchanged.  Rollback if a capture
# shows otherwise: set this to 152, making the handle the trigger id.
SURVEY_HANDLE_BASE = 0xA000

# The record kind byte and the proximity radius are the CLIENT's, from RE-227,
# and are recorded here only so a reader of the plan does not have to open the
# encoder to know what the plan is a plan FOR.
CLIENT_CONTACT_RADIUS = 500

# The ticket that measures the coordinates below, on the owner's machine.
XYZ_SOURCE_TICKET = "GT-228"

# The reason string every M2 destination is blocked with today.  One string,
# so the round file, the console and the tests cannot drift apart about it.
BLOCKED_XYZ_UNMEASURED = "XYZ_UNMEASURED_PENDING_GT-228"

# Destination trigger ids this lane plans records for.  M2's pass bar names
# two islands; widening the plan later is this one line.
PLANNED_TRIGGER_IDS: tuple[int, ...] = islands.M2_TARGET_TRIGGER_IDS

# trigger id -> (x, y, z) in scene 126, the scene GT-228 is run in.
#
# EMPTY, AND THAT IS THE CURRENT TRUTH OF M2.  GT-228 fills it; nothing else
# may.  Neither the ocean panel's island actors (round `zk50rd`: not M2's
# targets) nor the sea scenes' own placements (this round: no committed table
# names them) can supply a row here.
MEASURED_XYZ: dict[int, tuple[float, float, float]] = {}


# ---------------------------------------------------------------------------
# THE THIRD COMPONENT, WHICH GT-228 CANNOT READ
#
# `GT-228` reads the ship's HUD at the moment of contact, and that HUD shows
# TWO numbers (the ticket's own example, from R307's spawn: `X 3,050 Y 232`).
# The record needs THREE floats.  Written as it stood this morning, the
# ticket could not have produced a usable triple at all.
#
# It does not have to.  Every island actor scene 126 ships sits on
# ONE plane, and the four of them are already resolved, in this repository,
# by `world_bg3001_identity` -- so the number below is derived at import from
# the same pinned rows rather than copied out of a note:
#
#     Mad Sand Island      z = 123.57250213623047
#     Pirate Lair          z = 123.57240295410156
#     Blood Blade Island   z = 123.61100006103516
#     Lonely Island        z = 123.64060211181641
#
# a spread of 0.068 units across the whole scene.  And the size of the
# mistake a wrong third component can cause is bounded, which is the part
# that makes this safe rather than convenient: the client's contact test is
# a SQUARED distance against 500 (RE-227), so a z error of `d` leaves a
# horizontal reach of `sqrt(500^2 - d^2)` -- 499.99999 for d = 0.07, 499.0
# for d = 30, 489.9 even for d = 100.  A third component off by the entire
# height range of this scene's props still costs 2% of the radius.
#
# NONCLAIM, and it is the one that matters: nothing proves M2's two targets
# are placed in this scene at all (LANE-A round `zk50rd` measured that
# neither is in its cast), so `ISLAND_PLANE_Z` is "where THIS scene puts an
# island", offered as the default third component, not as their measured z.
# Nothing proves the HUD's two numbers are world x and y either -- see
# `CALIBRATION_ANCHORS`.
# ---------------------------------------------------------------------------

_ISLAND_OUTFIT = "MAP_ISLAND_01"


def _island_plane() -> tuple[tuple[str, float, float, float], ...]:
    """Scene 126's island actors, from the pinned identity module."""
    anchors = []
    for placement in bg3001.shippable_placements():
        identity = placement.identity
        if getattr(identity, "outfit", None) != _ISLAND_OUTFIT:
            continue
        anchors.append(
            (identity.name, placement.x, placement.y, placement.z)
        )
    return tuple(sorted(anchors))


# (name, x, y, z) of every island actor in the scene GT-228 is run in.
#
# WHAT THEY ARE FOR.  They are the only objects in that scene whose world
# position this project already knows AND which a player can sail up to.  A
# HUD reading taken beside one of them is therefore a calibration point: it
# says what the HUD's two numbers ARE.  Until one exists, converting a HUD
# reading into a record is an assumption, and `record_xyz_from_hud` says so
# in its own docstring rather than hiding it behind a plausible-looking
# tuple.
CALIBRATION_ANCHORS: tuple[tuple[str, float, float, float], ...]


def _island_plane_or_raise() -> tuple[tuple[str, float, float, float], ...]:
    """``_island_plane()``, refusing an empty answer.

    The identity module resolves its rows behind its own pinned sha, so no
    island actor at all means that pin moved and took them with it.
    Refusing at import is the posture `world_island_dock_table` already
    takes when its own source drifts: a plane averaged over nothing would be
    a number with no source, which is the one thing this module exists to
    avoid.
    """
    anchors = _island_plane()
    if not anchors:
        raise RuntimeError(
            "world_m2_survey_plan: world_bg3001_identity resolved no "
            f"{_ISLAND_OUTFIT} placement -- the island plane has no source"
        )
    return anchors


CALIBRATION_ANCHORS = _island_plane_or_raise()

# The plane those anchors sit on, and the spread across them.  Derived, not
# typed in: if the identity module's rows ever move, this moves with them.
ISLAND_PLANE_Z: float = (
    sum(anchor[3] for anchor in CALIBRATION_ANCHORS) / len(CALIBRATION_ANCHORS)
)
ISLAND_PLANE_Z_SPREAD: float = (
    max(anchor[3] for anchor in CALIBRATION_ANCHORS)
    - min(anchor[3] for anchor in CALIBRATION_ANCHORS)
)


def horizontal_reach_for_z_error(z_error: float) -> float:
    """How far the client's contact test still reaches horizontally when the
    record's third component is wrong by ``z_error``.

    `sqrt(CLIENT_CONTACT_RADIUS^2 - z_error^2)`, and 0.0 once the error alone
    exceeds the radius.  This is the function that makes "we cannot read the
    third number off the HUD" a bounded cost instead of a blocker.
    """
    squared = float(CLIENT_CONTACT_RADIUS) ** 2 - float(z_error) ** 2
    if squared <= 0.0:
        return 0.0
    return squared ** 0.5


def record_xyz_from_hud(hud_x: float, hud_y: float) -> tuple[float, float, float]:
    """A record triple from GT-228's two HUD numbers, with this scene's
    island plane as the third.

    ASSUMES the HUD's pair is world (x, y).  Nothing proves that -- both
    numbers are also within the range of this scene's world y and z -- and
    `CALIBRATION_ANCHORS` exists so one attended reading beside a named
    island settles it.  A caller writing the result into `MEASURED_XYZ`
    before that reading exists is making the assumption, not reading a
    measurement, and the round file that does it has to say so.
    """
    return (float(hud_x), float(hud_y), ISLAND_PLANE_Z)


class PlannedRecord(NamedTuple):
    """One proximity record this server would provision, if it had the XYZ.

    ``handle``   the opaque u16 the server issues and the client copies back.
    ``x/y/z``    the measured position, from ``MEASURED_XYZ`` only.
    ``wire_scene_id_status``  carried from the dock table so a caller cannot
                 use ``scene_name_tip_id`` as a wire id without seeing it.
    """

    trigger_id: int
    handle: int
    x: float
    y: float
    z: float
    scene_name_tip_id: int
    wire_scene_id_status: str
    min_level: int


class ConfirmResolution(NamedTuple):
    """What a confirm frame's echoed u16 is, as far as THIS BUILD can say.

    ``issued`` is True only when the value equals the handle of a record this
    build could actually provision -- which needs measured XYZ.  With
    ``MEASURED_XYZ`` empty it is False for every possible u16, and that is a
    result, not a gap: a confirm frame arriving today carries a handle this
    server never issued, which would refute the provisioning hypothesis
    rather than confirm it.
    """

    handle: int
    issued: bool
    trigger_id: int | None
    scene_name_tip_id: int | None
    wire_scene_id_status: str | None


_ORDINAL_BY_TRIGGER_ID: dict[int, int] = {
    row.trigger_id: index
    for index, row in enumerate(islands.DESTINATION_ROWS)
}


def handle_for_trigger_id(trigger_id: int) -> int | None:
    """The u16 handle this server issues for a destination, or None if the id
    is not a destination row at all.  Never raises."""
    ordinal = _ORDINAL_BY_TRIGGER_ID.get(trigger_id)
    if ordinal is None:
        return None
    return SURVEY_HANDLE_BASE + ordinal


def trigger_id_for_handle(handle: int) -> int | None:
    """The destination a handle was allocated for, or None.

    ALLOCATION, NOT ISSUANCE.  A non-None answer means "this is the handle
    this build WOULD use for that destination", not "we sent it".  Ask
    ``confirm_resolution()`` for that; it is the one that requires measured
    XYZ.
    """
    for trigger_id, ordinal in _ORDINAL_BY_TRIGGER_ID.items():
        if SURVEY_HANDLE_BASE + ordinal == handle:
            return trigger_id
    return None


def xyz_for_trigger_id(trigger_id: int) -> tuple[float, float, float] | None:
    """The measured position for a destination, or None while unmeasured."""
    return MEASURED_XYZ.get(trigger_id)


def planned_records() -> tuple[PlannedRecord, ...]:
    """Every record this build could provision right now.

    Fail-closed on data, not on a flag: a destination appears here only when
    ``MEASURED_XYZ`` carries a triple for it, so today this returns ``()``.
    """
    planned: list[PlannedRecord] = []
    for trigger_id in PLANNED_TRIGGER_IDS:
        row = islands.destination_for_trigger_id(trigger_id)
        xyz = MEASURED_XYZ.get(trigger_id)
        if row is None or xyz is None:
            continue
        handle = handle_for_trigger_id(trigger_id)
        if handle is None:          # unreachable while row is not None
            continue
        x, y, z = xyz
        planned.append(
            PlannedRecord(
                trigger_id=trigger_id,
                handle=handle,
                x=float(x),
                y=float(y),
                z=float(z),
                scene_name_tip_id=row.scene_name_tip_id,
                wire_scene_id_status=row.wire_scene_id_status,
                min_level=row.min_level,
            )
        )
    return tuple(planned)


def provisionable_count() -> int:
    """How many records this build could provision.  0 until GT-228 reports."""
    return len(planned_records())


def blocked_rows() -> tuple[tuple[int, str], ...]:
    """``(trigger_id, reason)`` for every planned destination that cannot be
    provisioned yet.  The complement of ``planned_records()`` over
    ``PLANNED_TRIGGER_IDS``, so the two can never both be empty."""
    blocked: list[tuple[int, str]] = []
    for trigger_id in PLANNED_TRIGGER_IDS:
        if MEASURED_XYZ.get(trigger_id) is None:
            blocked.append((trigger_id, BLOCKED_XYZ_UNMEASURED))
    return tuple(blocked)


def confirm_resolution(handle: int) -> ConfirmResolution:
    """Whether an echoed u16 is a handle THIS BUILD issued, and for what.

    ``issued`` is True only for a handle in ``planned_records()``.  A handle
    that is merely ALLOCATED to a destination (see ``trigger_id_for_handle``)
    but not provisionable resolves as not issued, with every downstream field
    None: a build that cannot send a record cannot have issued its handle.
    """
    for record in planned_records():
        if record.handle == handle:
            return ConfirmResolution(
                handle=handle,
                issued=True,
                trigger_id=record.trigger_id,
                scene_name_tip_id=record.scene_name_tip_id,
                wire_scene_id_status=record.wire_scene_id_status,
            )
    return ConfirmResolution(
        handle=handle,
        issued=False,
        trigger_id=None,
        scene_name_tip_id=None,
        wire_scene_id_status=None,
    )


def console_annotation(handle: int) -> str:
    """The ASCII fragment the confirm hook appends to its own line.

    Deliberately says NOTHING about what the value means to the client -- no
    destination name, no scene number, no trigger id -- because
    `lane_a_enter_instance_log` prints under RE-227 nonclaim 3 and a guard
    test there refuses those three words in the line.  What it does say is
    the one thing this server knows for certain about the exchange: how many
    records this build could have provisioned, and whether this value is one
    of their handles.

        `issued=no provisioned=0`

    Reading it during GT-228: `provisioned=0` with a confirm line present
    means the client popped its captain report WITHOUT a record from us, and
    the provisioning hypothesis of RE-227 is not what made it pop.
    """
    resolution = confirm_resolution(handle)
    issued = "yes" if resolution.issued else "no"
    return f"issued={issued} provisioned={provisionable_count()}"
