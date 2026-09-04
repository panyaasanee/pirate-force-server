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

Round `qz4p8n` built the two ends: the record encoder (called from no send
path -- COO-DECISION 0747 item 3(b) forbids sending one until real island XYZ
is measured) and the log-only walker for step 3
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
position in the sea, so `planned_records()` returns `()` and
`provisionable_count()` is 0.  Every function here is fail-closed around that
fact rather than around a flag: no XYZ, no record, no handle issued, and
`confirm_resolution()` answers "not issued by us" for every possible u16.

The day `GT-228` reports, this file changes by DATA ONLY -- two lines in
`MEASURED_XYZ` -- and the plan becomes non-empty on its own.

WHICH COORDINATE FRAME, WHICH IS THE QUESTION A RECORD CANNOT DUCK
------------------------------------------------------------------
A triple is meaningless without the space it is expressed in, and this route
touches two scenes: `GT-228` is run in **scene 126** (that is where R307 put
the ship on this build, and the ticket's screenshots are named `S126-*`),
while `columbus_quest_dispatch.COLUMBUS_DEST_SCENE_ID` is **17** and
`world_m2_sea_destination` establishes row 3021 teleporting the player there.
A record provisioned with scene-126 coordinates for a player standing in
scene 17 misses the client's 500-unit test by thousands of units, and the
symptom -- "the captain report never popped" -- is the same symptom as a
rejected handle or a record that never arrived.

So the frame is written down rather than assumed: `XYZ_FRAME_SCENE_ID`, and
every `PlannedRecord` carries it.  `MEASURED_XYZ` is in that frame and in no
other; a measurement taken anywhere else needs its own frame and a caller
that checks (`plan_is_for_scene()`), not a silent insertion here.

WHERE THE COORDINATES CAN AND CANNOT COME FROM, MEASURED, NOT ASSERTED
-----------------------------------------------------------------------
NOW.md says the XYZ "must not be guessed, GT-228 reading the HUD on contact
is the source".  The cheaper objection -- "the client ships tables with XYZ
in them, read it from there" -- deserves the tables actually being opened.
Three have now been, all in a `pf_bridge` clone against `gamedata/`:

1. `Bg3001.placements.tsv` (scene 126's cast), round `zk50rd`: four island
   ACTORS, and neither M2 target is among them.
2. The ship-scene placement files.  `Bg1001`..`Bg1007` -- the folder names
   scenes 17..23 use, and NOT a bijection: scenes 186/187/188 name three of
   the same folders (`lane_a_ground_preserve` already says so by name) --
   ship 8/8/8/10/13/20/12 placements WITH XYZ.  All seven scenes carry
   `n_CLINE_TYPE = 4294967295`, so their Mob-Set numbers resolve through no
   CLINE block and this project's crosswalk cannot name a single one of
   those placements.  Stated at its true strength: that no-cast value is the
   client-wide norm, 252 of 271 scenes (a count `world_m2_sea_destination`
   already carries), so this is "the seven sea scenes are inside the norm",
   not a property discovered about them; and it closes the CLINE path only,
   which is the only crosswalk this project has.
3. `CONSTDATA_TH__MARKER.tsv` (sha256 723c713a...67dc, 390 rows, 11 of them
   for scene 126) -- opened this round after pf-adversary caught the first
   two being written up as if they were the whole world.  It does not carry
   island positions either, BUT it answers a different question the ticket
   was about to spend attended minutes on:

       n_ID 17, n_SCENE 126: n_X 3050, n_Y 232, n_Z 90

   and `GT-228` records the ship's spawn HUD, from R307, as `X 3,050 Y 232`.
   An exact match on both numbers.  The HUD's pair is world x and y in the
   marker table's own frame -- read off a committed table, not calibrated by
   eye -- and the player plane in scene 126 is `n_Z 90` (10 of the 11 rows;
   the eleventh, id 216 at z 190, sits 0.6 units from the Jellyfish King
   placement, so the markers are placed on real objects rather than on a
   grid).

   NONCLAIM: one exact two-number agreement at one point.  It does not prove
   the HUD never scales or offsets elsewhere in the scene, and the contact
   readings GT-228 takes are still the only source for where the ISLANDS
   are.  It does mean the ticket no longer has to establish which axes the
   HUD shows.

Re-derive:

    awk -F'\t' 'NR==1 || $2==126' gamedata/tables/CONSTDATA_TH__MARKER.tsv
    awk -F'\t' 'NR==1 || ($1>=17 && $1<=23) {print $1"\t"$2"\t"$7"\t"$9}' \
        gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv
    for s in Bg1001 Bg1002 Bg1003 Bg1004 Bg1005 Bg1006 Bg1007; do \
        awk -F'\t' 'NR>1{print $2"\t"$6"\t"$7"\t"$8}' \
            gamedata/scene/$s/$s.placements.tsv; done

THE THIRD COMPONENT, WHICH THE HUD DOES NOT SHOW
------------------------------------------------
The HUD gives two numbers; a record needs three.  It does not have to give
the third.  The four island ACTORS of scene 126 sit on one plane --

    Mad Sand Island     123.57250213623047
    Pirate Lair         123.57240295410156
    Blood Blade Island  123.61100006103516
    Lonely Island       123.64060211181641

-- a spread of 0.068 units ACROSS THOSE FOUR ROWS (not across the scene: its
37 shippable placements span z 86.0 to 393.7, and an earlier draft of this
file said "across the whole scene", which pf-adversary measured as wrong by a
factor of 4500).  The player's own plane, from the marker table above, is 90.

What makes a wrong third component survivable is not the tightness of that
plane but the shape of the client's test: a SQUARED distance against 500
(RE-227), so an error of `d` leaves a horizontal reach of
`sqrt(500^2 - d^2)`.  The numbers that matter, each named for what it is:

    d = 0.068  (spread across the four island actors)      499.99999
    d = 33.6   (island-actor plane 123.6 vs player plane 90)   498.87
    d = 307.7  (the full z range of scene 126's placements)    394.13

So the plane this module offers costs nothing at the distance that actually
applies, and even the worst-case error inside this scene still reaches 394 of
500 -- 79%, not the 98% an earlier draft claimed for it.

    NONCLAIM: nothing proves M2's two targets are placed in scene 126 at all
    (round `zk50rd` measured that neither is in its cast), so
    `island_plane_z()` is "where THIS scene puts an island", offered as a
    default third component, not as their measured z.

THE HANDLE, AND THE ROLLBACK THAT IS ACTUALLY TWO EDITS
-------------------------------------------------------
`handle_for_trigger_id(t)` is `SURVEY_HANDLE_BASE + t` -- a function of the
DESTINATION, not of its row position, so reordering the dock table cannot
silently move a handle (pf-adversary measured that an ordinal-based version
did exactly that while every test here stayed green).  With the base at
0xA000 a handle is readable as its own destination in hex (153 -> 0xA099) and
cannot be confused with a trigger id, a scene id or a placement index, which
is what makes "did this echo come from us?" a real question.

    NONCLAIM, AND THE FAILURE IT WOULD PRODUCE: nothing proves the client
    ACCEPTS a value of the server's choosing here.  RE-227 proves it is
    copied back unchanged and nothing more.  If the client validates the u16
    against a table of its own, an 0xA0xx record is dropped and the captain
    report never pops -- indistinguishable, on the console, from "the record
    never arrived".
    THE ROLLBACK IS TWO EDITS, and the second one is why it is written here
    rather than left to be discovered under time pressure: set
    `SURVEY_HANDLE_BASE = 0`, which makes the handle the trigger id exactly;
    and `HandleAllocationTests.test_the_handle_range_does_not_collide_...`
    in `tests/test_world_m2_survey_plan.py` asserts the two configurations
    separately, so it stays green across the change instead of forbidding
    the very value the rollback prescribes.

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
  beside it.
* NOT a send path.  Nothing here composes, queues, or returns bytes, and the
  record encoder is deliberately not imported (its own grep guard requires
  that no other file in this repository so much as names it).
* NOT a level check.  `min_level` travels with the row for the attended
  ticket's preconditions; nothing here enforces it.
"""
from __future__ import annotations

from typing import NamedTuple

from . import world_island_dock_table as islands


# The opaque u16 handles this server issues: `SURVEY_HANDLE_BASE + trigger id`.
#
# [CONFIRMED - COO 20260904_1147, answering letter 20260904_1036 items 5/8]:
# this base and the base+trigger-id allocation scheme are the ones to use;
# rollback is base 0, per the adversary-fixed guard test that covers both.
# NOT settled by that letter, and still open: whether the CLIENT accepts a
# handle of the server's own choosing at all.  See the docstring's "THE
# HANDLE" section for the failure this would produce -- that nonclaim is
# unchanged by the confirmation above.
SURVEY_HANDLE_BASE = 0xA000

# RE-227: the client's contact tick compares squared distance against this.
CLIENT_CONTACT_RADIUS = 500

# The ticket that measures the coordinates below, on the owner's machine.
XYZ_SOURCE_TICKET = "GT-228"

# The scene `MEASURED_XYZ` is expressed in, and the ONLY one it may hold
# coordinates for.  126 because that is the scene GT-228 is run in; a
# measurement from scene 17 (Columbus's destination) is a different frame and
# needs its own table, not a row here.
XYZ_FRAME_SCENE_ID = 126

# The reason string every M2 destination is blocked with today.  Built from
# the ticket constant rather than spelling the number twice.
BLOCKED_XYZ_UNMEASURED = f"XYZ_UNMEASURED_PENDING_{XYZ_SOURCE_TICKET}"

# Destination trigger ids this lane plans records for.  M2's pass bar names
# two islands; widening the plan later is this one line.
PLANNED_TRIGGER_IDS: tuple[int, ...] = islands.M2_TARGET_TRIGGER_IDS

# trigger id -> (x, y, z) in the frame named by `XYZ_FRAME_SCENE_ID`.
#
# EMPTY, AND THAT IS THE CURRENT TRUTH OF M2.  GT-228 fills it; nothing else
# may.  None of the three committed tables opened for it (see the docstring)
# carries a position for either M2 target.
#
# COO 20260904_1147 item 1: a value converted from the HUD X/Y reading plus
# the island plane z (see `island_plane_z()`) and an axis calibrated against
# `CONSTDATA_TH__MARKER.tsv` counts as a source for this dict -- no separate
# "record consumed" capture is required first.  When GT-228 supplies a row,
# tag BOTH lines it adds with a trailing comment `# DERIVED-FROM GT-228 +
# MARKER n_ID 17`, so a later reader can tell a converted value from a
# fabricated one without re-reading this letter.
MEASURED_XYZ: dict[int, tuple[float, float, float]] = {}

# The outfit the client ships every island actor of scene 126 under.
_ISLAND_OUTFIT = "MAP_ISLAND_01"

# Cache for the derived island plane.  Populated on first use, never at
# import: this module is imported by a log-only hook whose whole job is to
# print one evidence line, and an import-time raise there would delete that
# line silently rather than loudly (pf-adversary D2 measured the hook
# dropping out of `lane_hooks._discover()` entirely).
_ANCHORS: tuple[tuple[str, float, float, float], ...] | None = None


class PlannedRecord(NamedTuple):
    """One proximity record this server would provision, if it had the XYZ.

    ``handle``          the opaque u16 the server issues and the client
                        copies back.
    ``x/y/z``           the measured position, from ``MEASURED_XYZ`` only.
    ``frame_scene_id``  the scene those coordinates are expressed in.  A
                        record is only meaningful to a player standing in
                        that scene.
    ``wire_scene_id_status``  carried from the dock table so a caller cannot
                        use ``scene_name_tip_id`` as a wire id without seeing
                        it.
    """

    trigger_id: int
    handle: int
    x: float
    y: float
    z: float
    frame_scene_id: int
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


def handle_for_trigger_id(trigger_id: int) -> int | None:
    """The u16 handle this server issues for a destination, or None if the id
    is not a destination row at all.

    A function of the destination itself, never of its position in the dock
    table.  Never raises.
    """
    if islands.destination_for_trigger_id(trigger_id) is None:
        return None
    return SURVEY_HANDLE_BASE + trigger_id


def trigger_id_for_handle(handle: int) -> int | None:
    """The destination a handle was allocated for, or None.

    ALLOCATION, NOT ISSUANCE.  A non-None answer means "this is the handle
    this build WOULD use for that destination", not "we sent it".  Ask
    ``confirm_resolution()`` for that; it is the one that requires measured
    XYZ.
    """
    candidate = handle - SURVEY_HANDLE_BASE
    if islands.destination_for_trigger_id(candidate) is None:
        return None
    return candidate


def xyz_for_trigger_id(trigger_id: int) -> tuple[float, float, float] | None:
    """The measured position for a destination, or None while unmeasured.

    In the frame named by ``XYZ_FRAME_SCENE_ID``.
    """
    return MEASURED_XYZ.get(trigger_id)


def calibration_anchors() -> tuple[tuple[str, float, float, float], ...]:
    """``(name, x, y, z)`` of every island actor scene 126 ships.

    Derived from `world_bg3001_identity`'s pinned rows on first call and
    cached, so importing this module can never fail on their account.
    Refuses an empty answer: the identity module resolves its rows behind its
    own sha pin, so no island actor at all means that pin moved and took them
    with it, and a plane averaged over nothing would be a number with no
    source.
    """
    global _ANCHORS
    if _ANCHORS is None:
        # Imported here rather than at module scope for the same reason the
        # cache exists: nothing in this module's import path may be able to
        # take the hook's evidence line down with it.
        from . import world_bg3001_identity as bg3001

        anchors = tuple(sorted(
            (placement.identity.name, placement.x, placement.y, placement.z)
            for placement in bg3001.shippable_placements()
            if getattr(placement.identity, "outfit", None) == _ISLAND_OUTFIT
        ))
        if not anchors:
            raise RuntimeError(
                "world_m2_survey_plan: world_bg3001_identity resolved no "
                f"{_ISLAND_OUTFIT} placement -- the island plane has no source"
            )
        _ANCHORS = anchors
    return _ANCHORS


def island_plane_z() -> float:
    """The z every island actor of scene 126 sits on (their mean; they agree
    to 0.068 units).  Derived, never typed in."""
    anchors = calibration_anchors()
    return sum(anchor[3] for anchor in anchors) / len(anchors)


def island_plane_z_spread() -> float:
    """How far apart those four island actors' z values are.  0.068 units --
    a fact about FOUR ROWS, not about the scene, whose 37 shippable
    placements span 86.0 to 393.7."""
    anchors = calibration_anchors()
    return max(a[3] for a in anchors) - min(a[3] for a in anchors)


def horizontal_reach_for_z_error(z_error: float) -> float:
    """How far the client's contact test still reaches horizontally when the
    record's third component is wrong by ``z_error``.

    `sqrt(CLIENT_CONTACT_RADIUS^2 - z_error^2)`, and 0.0 once the error alone
    exceeds the radius.  This is the function that makes "the HUD shows two
    numbers, not three" a bounded cost instead of a blocker -- see the
    docstring for the three errors worth naming and what each of them costs.
    """
    squared = float(CLIENT_CONTACT_RADIUS) ** 2 - float(z_error) ** 2
    if squared <= 0.0:
        return 0.0
    return squared ** 0.5


def record_xyz_from_hud(hud_x: float, hud_y: float) -> tuple[float, float, float]:
    """A record triple from GT-228's two HUD numbers, with scene 126's island
    plane as the third.

    The pair is taken as world x and y in the marker table's frame, which is
    what `CONSTDATA_TH__MARKER.tsv` row 17 agreeing exactly with the ticket's
    recorded spawn HUD (`3050`, `232`) says it is -- one agreement at one
    point, not a proof that the HUD never scales elsewhere.  The third
    component is `island_plane_z()`, which is where THIS scene puts an island
    and not a measurement of M2's targets.  The result belongs to scene
    `XYZ_FRAME_SCENE_ID` and to no other scene.
    """
    return (float(hud_x), float(hud_y), island_plane_z())


def plan_is_for_scene(scene_id: int) -> bool:
    """Whether a player in ``scene_id`` is in the frame the plan's
    coordinates are expressed in.  A caller that provisions records without
    asking this is sending a triple into the wrong space."""
    return scene_id == XYZ_FRAME_SCENE_ID


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
                frame_scene_id=XYZ_FRAME_SCENE_ID,
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

    WHERE IT CAN BE READ, honestly: not during `GT-228` as that ticket is
    written -- its STOP rule forbids pressing confirm, so no
    EnterInstanceVital is sent and this line cannot appear there at all.  It
    is what the FIRST confirm frame this server ever receives will say, from
    whatever run produces one.  `provisioned=0` beside such a line means the
    captain report popped without a record from us, which refutes RE-227's
    provisioning hypothesis rather than supporting it.
    """
    resolution = confirm_resolution(handle)
    issued = "yes" if resolution.issued else "no"
    return f"issued={issued} provisioned={provisionable_count()}"
