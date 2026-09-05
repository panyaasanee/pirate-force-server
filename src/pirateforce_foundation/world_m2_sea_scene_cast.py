"""Which sea a cast can stand on at all - LANE-A, M2.

WHAT THIS MODULE MEASURES.  M2's bar is "leave the town": sail out, see an
island, get the captain-report window, confirm, stand on the island.  Two
halves of that are already built in this tree and they target DIFFERENT
scenes, which ``world_m2_survey_plan``'s own docstring has said in prose
since round ``zk50rd``:

* the door a player can walk through by themselves sends them to scene
  **17** (``world_m2_sea_destination.DESTINATION_SCENE_N_ID``), and
* the survey/docking mechanism provisions its records in scene **126**
  (``world_m2_survey_plan.XYZ_FRAME_SCENE_ID``).

Prose is where that stopped.  Nothing in this tree ever asked the question
that decides which of the two is reconcilable with the other: CAN EITHER
SCENE CARRY A CAST AT ALL?  This module asks it, from the client's own
tables, and the answer is eight-of-eight and one-sided.

THE MEASUREMENT, AND IT IS THE WHOLE POINT OF THE FILE.  Every scene row in
``CONSTDATA_TH__SCENE_NAME.tsv`` carries ``n_CLINE_TYPE``: the creature-line
block a scene's Mob-Set placements resolve through.  Every per-scene
identity module in this lane (``world_bg0002_identity`` .. ``world_bg4001_
identity``) is built on exactly that resolution.  Read for the eight
Columbus ship destinations and the four ocean panels those options
advertise:

    scene  n_SCENE_TYPE  n_CLINE_TYPE  CLINE rows  n_MARKER  n_SAVE
    17     4             0xFFFFFFFF    0           0         0
    18     4             0xFFFFFFFF    0           0         0
    19     4             0xFFFFFFFF    0           0         0
    20     4             0xFFFFFFFF    0           0         0
    21     4             0xFFFFFFFF    0           0         0
    39     4             0xFFFFFFFF    0           0         0
    40     4             0xFFFFFFFF    0           0         0
    41     4             0xFFFFFFFF    0           0         0
    126    8             3001          56          0         0
    127    8             3002          58          0         0
    304    8             3007          58          0         0
    305    8             3008          58          0         0

``0xFFFFFFFF`` is the same value scene 278 (the beach test field) and scene
997 (the film set) carry in this project's own pinned registry - the three
scenes nobody has ever composed a cast for.  It is read here as "this row
names no creature line", NOT decoded from the client image, and the
distinction is stated because it is the one inference in the file: what is
MEASURED is that no ``CONSTDATA_TH__CLINE.tsv`` row carries that value in
``n_CLINE_TYPE``, so the resolution every identity module in this lane
performs returns nothing for these scenes whatever the sentinel means.

WHAT THAT SETTLES, AND WHAT IT DOES NOT.

SETTLED: the eight ship scenes cannot be given a cast by this server from
committed data.  Scene 17's own eight placements are real (they carry
coordinates; the registry's ``ground`` block for scene 17 is derived from
them) and they resolve to NOTHING, because there is no creature-line block
for them to resolve through.  A round that sets out to build
``world_population_bg1001`` the way this lane built thirteen other rosters
would find that out after writing the identity module, not before.  That is
the day of work this file exists to not spend.

SETTLED: the four ocean panels can.  Scene 126 already has its roster
(``world_population_bg3001``, 37 of 38 placements resolving, the missing one
being a CLINE row with leader 0), and R313 measured 37 actors on screen in
that scene at 2026-09-05T02:07+07:00.  The measurement and the screen agree.

NOT SETTLED, AND NOT DECIDED HERE: which scene the door should lead to.
``PANYA-DECISION 2026-08-27T15:25+07:00`` (``M2-NO-VEHICLE-OWNER-20260827-
1525``) accepted "talk to Columbus, arrive at scene 17 as an ordinary
character" as M2's bar, and ``QUESTDATA_TH__QUEST.tsv`` row 3021's
``n_VARI_2`` says 17 with eight sibling rows agreeing.  Moving the door
would contradict an owner ruling on a measurement, which is not a thing a
lane does on its own - so this module MOVES NOTHING.  It measures, it
prints, and this round's letter to the COO asks for the ruling.  The
attended ticket that would decide it by eye already exists and is blocked
for the matching reason (it needs a server that sends the panel, and no such
server is on ``main``).

WHAT THIS MODULE DOES NOT CLAIM.

1. IT DOES NOT CLAIM SCENE 17 IS EMPTY ON A PLAYER'S SCREEN.  A scene with
   no creature line still has terrain, a skybox and a ship model; what is
   measured here is that no SERVER-COMPOSED ACTOR can be derived for it,
   which is a different sentence.  Nobody in this project has watched scene
   17 with an eye on what is standing in it.
2. IT SENDS NOTHING AND REFUSES NOTHING.  No frame, no row, no gate.  It
   composes a console line, the same report-only shape as every other file
   in this M2 family (``world_m2_sea_destination``,
   ``world_m2_crossing_handoff``, ``world_m2_return_leg``,
   ``world_m2_columbus_trigger_readiness``).
3. IT READS NO FILE.  The table above is frozen here with the two source
   sha256 digests that produced it, because this package is imported by a
   gate run that has no ``pf_bridge`` beside it - the same reason every
   identity module in this lane carries frozen rows instead of a reader.
"""

from __future__ import annotations

from typing import NamedTuple

from . import world_m2_sea_destination
from . import world_m2_survey_plan
from . import world_scene_travel

# Shippable on the default path, no scenario flag: this is a report.
production_allowed = True


# The two tables the frozen rows below came from, pinned by digest so a
# later round can re-derive them and find out if they moved.
SCENE_NAME_TABLE = "gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv"
SCENE_NAME_TABLE_SHA256 = (
    "e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b"
)
CLINE_TABLE = "gamedata/tables/CONSTDATA_TH__CLINE.tsv"
CLINE_TABLE_SHA256 = (
    "aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40"
)
MEASURED_AT = "2026-09-05T07:2x+07:00"

# The value the scene row carries when it names no creature-line block.
# NOT decoded from the client image - see the module docstring for exactly
# what is measured and what is inferred.
NO_CLINE_TYPE = 0xFFFFFFFF

# n_SCENE_TYPE families this file distinguishes, by their own numbers.
SCENE_TYPE_SHIP = 4
SCENE_TYPE_OCEAN_PANEL = 8

VERDICT_NO_CAST_POSSIBLE = "NO_CAST_POSSIBLE_NO_CLINE_TYPE"
VERDICT_CAST_POSSIBLE_COMPOSED = "CAST_POSSIBLE_COMPOSED"
VERDICT_CAST_POSSIBLE_NOT_COMPOSED = "CAST_POSSIBLE_NOT_COMPOSED"
VERDICT_NOT_MEASURED = "NOT_MEASURED"


class SeaSceneCast(NamedTuple):
    """One sea scene's ability to carry a server-composed cast.

    ``composer_source`` is this lane's own name for the roster builder
    registered for the scene in ``world_scene_travel.CENSUS_SOURCES``, or
    ``None`` when no builder is registered.  It is read live rather than
    frozen, so the day a roster is added for one of these scenes the verdict
    below changes with it instead of going stale.
    """

    scene_id: int
    scene_type: int
    cline_type: int
    cline_rows: int
    marker: int
    save: int
    composer_source: str | None
    verdict: str

    @property
    def can_carry_a_cast(self) -> bool:
        return self.cline_rows > 0


# scene id -> (n_SCENE_TYPE, n_CLINE_TYPE, CLINE rows carrying that type,
#              n_MARKER, n_SAVE)
# The eight Columbus ship destinations (world_m2_sea_destination.
# COLUMBUS_ROUTES' own target scenes) and the four ocean panels those same
# options advertise.  Measured, not modelled; see the module docstring's
# table, which is this data in prose.
_MEASURED_ROWS: dict[int, tuple[int, int, int, int, int]] = {
    17: (SCENE_TYPE_SHIP, NO_CLINE_TYPE, 0, 0, 0),
    18: (SCENE_TYPE_SHIP, NO_CLINE_TYPE, 0, 0, 0),
    19: (SCENE_TYPE_SHIP, NO_CLINE_TYPE, 0, 0, 0),
    20: (SCENE_TYPE_SHIP, NO_CLINE_TYPE, 0, 0, 0),
    21: (SCENE_TYPE_SHIP, NO_CLINE_TYPE, 0, 0, 0),
    39: (SCENE_TYPE_SHIP, NO_CLINE_TYPE, 0, 0, 0),
    40: (SCENE_TYPE_SHIP, NO_CLINE_TYPE, 0, 0, 0),
    41: (SCENE_TYPE_SHIP, NO_CLINE_TYPE, 0, 0, 0),
    126: (SCENE_TYPE_OCEAN_PANEL, 3001, 56, 0, 0),
    127: (SCENE_TYPE_OCEAN_PANEL, 3002, 58, 0, 0),
    304: (SCENE_TYPE_OCEAN_PANEL, 3007, 58, 0, 0),
    305: (SCENE_TYPE_OCEAN_PANEL, 3008, 58, 0, 0),
}

# The eight ship scenes, in the order world_m2_sea_destination lists their
# routes.  Derived from the measurement above rather than typed twice.
SHIP_DESTINATION_SCENE_IDS = tuple(
    scene_id
    for scene_id, row in sorted(_MEASURED_ROWS.items())
    if row[0] == SCENE_TYPE_SHIP
)
OCEAN_PANEL_SCENE_IDS = tuple(
    scene_id
    for scene_id, row in sorted(_MEASURED_ROWS.items())
    if row[0] == SCENE_TYPE_OCEAN_PANEL
)

# The scene a player's own action reaches, and the scene the survey records
# are provisioned in.  Both READ from the modules that own them; neither
# number is re-declared here, so this file cannot drift away from the two
# halves it is comparing.
DOOR_SCENE_ID = world_m2_sea_destination.DESTINATION_SCENE_N_ID
TRIAL_SCENE_ID = world_m2_survey_plan.XYZ_FRAME_SCENE_ID


def cast_capacity(scene_id: int) -> SeaSceneCast:
    """What this project can compose for ``scene_id``, as a measured row.

    A scene this round did not measure answers ``VERDICT_NOT_MEASURED`` with
    zeroes rather than raising: the callers are report paths, and a scene id
    nobody measured is a thing to say out loud, not to fail a crossing over.
    """
    try:
        key = int(scene_id)
    except (TypeError, ValueError):
        key = -1
    row = _MEASURED_ROWS.get(key)
    source = _composer_source(key)
    if row is None:
        return SeaSceneCast(key, -1, -1, 0, -1, -1, source,
                            VERDICT_NOT_MEASURED)
    scene_type, cline_type, cline_rows, marker, save = row
    if cline_rows <= 0:
        verdict = VERDICT_NO_CAST_POSSIBLE
    elif source is None:
        verdict = VERDICT_CAST_POSSIBLE_NOT_COMPOSED
    else:
        verdict = VERDICT_CAST_POSSIBLE_COMPOSED
    return SeaSceneCast(key, scene_type, cline_type, cline_rows, marker,
                        save, source, verdict)


def _composer_source(scene_id: int) -> str | None:
    """This lane's registered roster builder for the scene, or None.

    Wrapped rather than inlined so a table that will not import cannot make
    a report path raise - the same fail-closed shape the admission
    predicates in ``lane_hooks/lane_a_scene_census.py`` use.
    """
    try:
        return world_scene_travel.CENSUS_SOURCES.get(scene_id)
    except Exception:  # noqa: BLE001 - fail-closed, see the docstring
        return None


def every_ship_destination_refuses_a_cast() -> bool:
    """Is the eight-of-eight result still eight-of-eight?

    Exists as a function rather than a constant so the day one of these
    scenes turns out to have a creature line after all - a corrected table,
    a wider measurement - the answer changes with the data instead of with
    a sentence somebody has to remember to edit.
    """
    return all(
        not cast_capacity(scene_id).can_carry_a_cast
        for scene_id in SHIP_DESTINATION_SCENE_IDS
    )


def halves_agree() -> bool:
    """Do the door and the survey trial name the same scene?

    False today (17 vs 126).  Reported, not enforced: the door's number is
    an owner ruling and a table column, and this module moves neither.
    """
    return DOOR_SCENE_ID == TRIAL_SCENE_ID


def sea_scene_cast_console_line() -> str:
    """One ASCII line naming both halves of M2's sea and what each can hold.

    Greppable token: ``M2_SEA_CAST``.  ``door_*`` is the scene a player
    reaches by their own action; ``trial_*`` is the scene the survey records
    are provisioned in.
    """
    door = cast_capacity(DOOR_SCENE_ID)
    trial = cast_capacity(TRIAL_SCENE_ID)
    return (
        "M2_SEA_CAST"
        f" door={door.scene_id}"
        f" door_verdict={door.verdict}"
        f" door_cline={_cline_text(door)}"
        f" door_cline_rows={door.cline_rows}"
        f" door_composer={door.composer_source or 'none'}"
        f" trial={trial.scene_id}"
        f" trial_verdict={trial.verdict}"
        f" trial_cline={_cline_text(trial)}"
        f" trial_cline_rows={trial.cline_rows}"
        f" trial_composer={trial.composer_source or 'none'}"
        f" halves_agree={'YES' if halves_agree() else 'NO'}"
        " ship_destinations_refusing_a_cast="
        f"{sum(1 for s in SHIP_DESTINATION_SCENE_IDS if not cast_capacity(s).can_carry_a_cast)}"
        f"/{len(SHIP_DESTINATION_SCENE_IDS)}"
    )


def _cline_text(row: SeaSceneCast) -> str:
    if row.cline_type == NO_CLINE_TYPE:
        return "none"
    if row.cline_type < 0:
        return "unmeasured"
    return str(row.cline_type)


def sea_scene_cast_console_line_safe() -> str:
    """The line, on a path that must never raise.

    Same contract as ``world_m2_sea_destination.console_line_safe``: a
    report that fails says so on one line and the crossing carries on.
    """
    try:
        return sea_scene_cast_console_line()
    except Exception as error:  # noqa: BLE001 - report path, see the docstring
        return f"M2_SEA_CAST unmeasured reason={type(error).__name__}"
