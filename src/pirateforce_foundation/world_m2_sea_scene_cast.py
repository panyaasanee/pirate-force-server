"""Which table answers "what cast can this scene hold" - LANE-A, M2.

THIS FILE EXISTS BECAUSE ITS OWN FIRST DRAFT WAS WRONG, AND THE WRONG
VERSION IS THE REASON FOR THE SHAPE OF THE RIGHT ONE.

The first draft of this module read ``n_CLINE_TYPE`` out of
``CONSTDATA_TH__SCENE_NAME.tsv``, found the all-ones sentinel on all eight
Columbus destination scenes, found no ``CONSTDATA_TH__CLINE.tsv`` row
carrying that value, and concluded: no cast is derivable for any of them,
ever, so M2's two halves cannot be reconciled by populating the door's
destination.  ``pf-adversary`` refuted it in one step: THREE committed
tables carry an ``n_CLINE_TYPE`` column, and the draft had opened one.

    CONSTDATA_TH__SCENE_NAME.tsv     keyed by n_ID       (the scene's own)
    CONSTDATA_TH__INSTANCE.tsv       keyed by n_SCENE_ID (338 rows)
    CONSTDATA_TH__SAILING_RESULT.tsv keyed by n_AREA     (138 rows)

``CONSTDATA_TH__INSTANCE.tsv`` answers for every one of the eight, and
``grep -rn "INSTANCE.tsv" src/ docs/`` returned ZERO hits before this
round: no file in this project had ever opened it.  So the module is not
the sentinel reader it started as.  It is the enumeration of the sources a
"this scene can hold nothing" claim has to exhaust before it may be made,
plus the measurement of what those sources actually answer.

THE CORRECTED MEASUREMENT.  Re-derived at HEAD from the digests pinned
below, using THIS PROJECT'S OWN key rule - ``world_m2_sea_destination``'s
``CLINE_KEY_COLUMN``: ``CLINE[n_CLINE_TYPE == <type> and n_CREATURE_TYPE ==
<Mob-Set number>] -> n_LEADER_BK1 -> CONSTDATA_TH__MOBS`` - against each
scene's own committed ``.placements.tsv``:

    scene  model   n_SCENE_TYPE  direct  via INSTANCE   placements resolved
    17     Bg1001  4             none    801 814 816    8          7
    18     Bg1002  4             none    803 805 818    8          8
    19     Bg1003  4             none    821            8          8
    20     Bg1004  4             none    809 823        10         10
    21     Bg1005  4             none    811 825        13         13
    39     Bg1023  4             none    519            11         11
    40     Bg1024  4             none    520            37         35
    41     Bg1025  4             none    521            10         10
    126    Bg3001  8             3001    (sailing 8000) 38         37

EIGHT OF EIGHT RESOLVE.  Scene 21 at 13/13 and scene 39 at 11/11 resolve
MORE COMPLETELY than scene 126 does at 37/38, and 126 is the scene this
project already ships a roster for.  ``world_population_bg1001`` and its
seven siblings are buildable today, from committed data, with the same
identity-module shape this lane has shipped thirteen times.  The first
draft would have told a later round not to try.

THREE OF THE EIGHT ARE NOT SHIPS, WHICH MATTERS FOR M2 SPECIFICALLY.
``s_SCENE_NAME`` at HEAD: 17-21 are "one/two/three ships at sea"
variants, but 39, 40 and 41 are "small island, style 9/10/11" - islands,
which is the noun M2's own bar uses ("sail near an island ... stand on the
island").  The first draft called all eight "ship destinations" and hid
that.  They are named here as what the table calls them.

WHAT IS MEASURED AND WHAT IS NOT, KEPT APART ON PURPOSE.

[MEASURED] every number in the table above, and the fact that no CLINE row
carries the all-ones sentinel.
[MEASURED] that ``INSTANCE.n_SCENE_ID`` and ``SAILING_RESULT.n_AREA`` carry
an ``n_CLINE_TYPE`` for these scenes, and which types.
[PROPOSED] that a walk-in arrival may compose a cast FROM an INSTANCE row.
The rows carry ``n_MIN_LEVEL``/``n_MAX_LEVEL`` tiers and an ``n_EXIT``,
which is the shape of an instanced dungeon entry, not necessarily of an
ordinary arrival.  Nothing here decides that; a round that builds the
roster owns the question, and this module deliberately makes the DATA
question ("does a cast resolve") separate from the DESIGN question ("may
this arrival send it").
[CONTESTED] that the door's destination is scene id 17 at all.
``world_m2_sea_destination`` labels ``DESTINATION_SCENE_N_ID`` `[CONTESTED]`
in its own source and says in so many words that nothing in that file may
be quoted as measuring row 3021's destination is a scene id: the rival
reading is ``MARKER.n_ID``, under which 17 resolves to ``MARKER[17].n_SCENE
= 126``.  This module carries that tag rather than dropping it -
``DOOR_SCENE_ID_IS_CONTESTED`` below - because under the rival reading the
door and the survey trial are the SAME scene and ``halves_agree()`` is
True.

WHAT THIS MODULE DOES NOT DO.

1. IT SENDS NOTHING, REFUSES NOTHING, MOVES NOTHING.  No frame, no row, no
   gate, no door.  It composes a console line, the same report-only shape
   as every other file in this M2 family (``world_m2_sea_destination``,
   ``world_m2_crossing_handoff``, ``world_m2_return_leg``,
   ``world_m2_columbus_trigger_readiness``).
2. IT READS NO FILE.  The rows below are frozen with the digests that
   produced them, because this package is imported by a gate run with no
   ``pf_bridge`` beside it - the same reason every identity module in this
   lane carries frozen rows instead of a reader.  ``tools/pf_scene_cast_
   sources_extract.py`` is the re-derivation, and it is the thing to run
   when a digest below stops matching.
3. IT DOES NOT SAY ANY SCENE IS CASTLESS.  After this round, that sentence
   is only sayable about a scene for which every source in
   ``CREATURE_LINE_SOURCES`` was checked and answered nothing, and the
   verdict names which sources were checked.
"""

from __future__ import annotations

from typing import NamedTuple

from . import world_m2_sea_destination
from . import world_m2_survey_plan
from . import world_scene_travel

# Shippable on the default path, no scenario flag: this is a report.
production_allowed = True


MEASURED_AT = "2026-09-05T07:46+07:00"

# THE ENUMERATED SEARCH SPACE.  A "no cast is derivable" claim about a
# scene is only well formed once every entry here has been checked for it.
# Named as data, with the key column each one is joined on, so the next
# round that wants to make such a claim has a list to exhaust instead of a
# habit to follow - which is the exact hole pf-adversary put this round's
# first draft through.
CREATURE_LINE_SOURCES = (
    ("gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv", "n_ID",
     "e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b"),
    ("gamedata/tables/CONSTDATA_TH__INSTANCE.tsv", "n_SCENE_ID",
     "e3b54a192b886284f30cdf94922d3ee2f5907f4db6c8ab24a6850318d21558f4"),
    ("gamedata/tables/CONSTDATA_TH__SAILING_RESULT.tsv", "n_AREA",
     "9a047da026c12c2909e9c2725a19e49713161c5d9e10c108e386157446323d2c"),
)
# The block table every source above resolves INTO, and the row table the
# block's leader points at.  Not sources of an n_CLINE_TYPE; the other end
# of the join.
CLINE_TABLE = "gamedata/tables/CONSTDATA_TH__CLINE.tsv"
CLINE_TABLE_SHA256 = (
    "aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40"
)
MOBS_TABLE = "gamedata/tables/CONSTDATA_TH__MOBS.tsv"
MOBS_TABLE_SHA256 = (
    "3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b"
)

# The value a SCENE_NAME row carries when it names no creature line of its
# own.  252 of the 271 scene rows carry it - it is the DEFAULT, not a
# marker for "empty", which is the reading the first draft got wrong.
NO_DIRECT_CLINE_TYPE = 0xFFFFFFFF

SCENE_TYPE_SEA_MAP = 4        # what 17-21 and 39-41 all are
SCENE_TYPE_OCEAN_PANEL = 8    # what 126/127/304/305 all are

SOURCE_DIRECT = "SCENE_NAME"
SOURCE_INSTANCE = "INSTANCE"
SOURCE_SAILING = "SAILING_RESULT"

VERDICT_CAST_RESOLVES = "CAST_RESOLVES"
VERDICT_CAST_RESOLVES_PARTIALLY = "CAST_RESOLVES_PARTIALLY"
VERDICT_NO_SOURCE_ANSWERS = "NO_SOURCE_ANSWERS"
VERDICT_NOT_MEASURED = "NOT_MEASURED"

# ``world_m2_sea_destination`` labels its own DESTINATION_SCENE_N_ID
# [CONTESTED]; carried here rather than dropped.  See the docstring.
DOOR_SCENE_ID_IS_CONTESTED = True
DOOR_RIVAL_READING_SCENE_ID = 126


class SceneCast(NamedTuple):
    """What cast one scene resolves, and out of which source.

    ``resolved``/``placements`` are counts of that scene's own committed
    ``.placements.tsv`` rows that reach a ``MOBS`` row through
    ``best_cline_type``.  ``composer_source`` is this lane's registered
    roster builder for the scene if there is one, read live from
    ``world_scene_travel.CENSUS_SOURCES`` rather than frozen, so the day a
    roster lands the report changes with it.
    """

    scene_id: int
    model_id: str
    name_gloss: str
    scene_type: int
    direct_cline_type: int
    instance_cline_types: tuple[int, ...]
    sailing_cline_types: tuple[int, ...]
    placements: int
    resolved: int
    best_cline_type: int
    answering_source: str | None
    composer_source: str | None
    verdict: str

    @property
    def a_cast_resolves(self) -> bool:
        return self.resolved > 0


# scene id -> (model, ASCII gloss of s_SCENE_NAME, n_SCENE_TYPE,
#              direct n_CLINE_TYPE, INSTANCE types, SAILING_RESULT types,
#              placements, resolved, best type)
# Measured at MEASURED_AT from the digests above; re-derivable with
# tools/pf_scene_cast_sources_extract.py.  The glosses are translations of
# the CJK s_SCENE_NAME column, kept ASCII because this console is cp874.
_MEASURED_ROWS: dict[int, tuple] = {
    17: ("Bg1001", "one ship at sea", 4, NO_DIRECT_CLINE_TYPE,
         (801, 814, 816), (), 8, 7, 801),
    18: ("Bg1002", "two ships at sea style 1", 4, NO_DIRECT_CLINE_TYPE,
         (803, 805, 818), (), 8, 8, 818),
    19: ("Bg1003", "two ships at sea style 2", 4, NO_DIRECT_CLINE_TYPE,
         (821,), (), 8, 8, 821),
    20: ("Bg1004", "two ships at sea style 3", 4, NO_DIRECT_CLINE_TYPE,
         (809, 823), (), 10, 10, 809),
    21: ("Bg1005", "three ships at sea style 1", 4, NO_DIRECT_CLINE_TYPE,
         (811, 825), (), 13, 13, 811),
    39: ("Bg1023", "small island style 9", 4, NO_DIRECT_CLINE_TYPE,
         (519,), (), 11, 11, 519),
    40: ("Bg1024", "small island style 10", 4, NO_DIRECT_CLINE_TYPE,
         (520,), (), 37, 35, 520),
    41: ("Bg1025", "small island style 11", 4, NO_DIRECT_CLINE_TYPE,
         (521,), (), 10, 10, 521),
    126: ("Bg3001", "Atlantis", 8, 3001, (), (8000,), 38, 37, 3001),
}

# The eight scenes row 302x's own options target, and the panels those
# options advertise.  Both read from world_m2_sea_destination's
# COLUMBUS_ROUTES columns rather than typed again here.
COLUMBUS_TARGET_SCENE_IDS = tuple(
    sorted({row[3] for row in world_m2_sea_destination.COLUMBUS_ROUTES})
)
ADVERTISED_PANEL_SCENE_IDS = tuple(
    sorted({row[4] for row in world_m2_sea_destination.COLUMBUS_ROUTES})
)

# The scene a player's own action reaches, and the scene the survey records
# are provisioned in.  Both READ from the modules that own them; neither
# number is re-declared here.
DOOR_SCENE_ID = world_m2_sea_destination.DESTINATION_SCENE_N_ID
TRIAL_SCENE_ID = world_m2_survey_plan.XYZ_FRAME_SCENE_ID


def cast_capacity(scene_id: int) -> SceneCast:
    """What cast ``scene_id`` resolves, as a measured row.

    A scene this round did not measure answers ``VERDICT_NOT_MEASURED``
    rather than raising, and rather than answering "no cast": those are
    different sentences and conflating them is what the first draft did.
    """
    try:
        key = int(scene_id)
    except (TypeError, ValueError):
        key = -1
    row = _MEASURED_ROWS.get(key)
    source = _composer_source(key)
    if row is None:
        return SceneCast(key, "", "", -1, -1, (), (), 0, 0, -1, None,
                         source, VERDICT_NOT_MEASURED)
    (model, gloss, scene_type, direct, instance_types, sailing_types,
     placements, resolved, best) = row
    if direct != NO_DIRECT_CLINE_TYPE:
        answering = SOURCE_DIRECT
    elif instance_types:
        answering = SOURCE_INSTANCE
    elif sailing_types:
        answering = SOURCE_SAILING
    else:
        answering = None
    if resolved <= 0:
        verdict = VERDICT_NO_SOURCE_ANSWERS
    elif resolved < placements:
        verdict = VERDICT_CAST_RESOLVES_PARTIALLY
    else:
        verdict = VERDICT_CAST_RESOLVES
    return SceneCast(key, model, gloss, scene_type, direct, instance_types,
                     sailing_types, placements, resolved, best, answering,
                     source, verdict)


def _composer_source(scene_id: int) -> str | None:
    """This lane's registered roster builder for the scene, or None.

    Wrapped rather than inlined so a table that will not answer cannot make
    a report path raise - the same fail-closed shape the admission
    predicates in ``lane_hooks/lane_a_scene_census.py`` use.
    """
    try:
        return world_scene_travel.CENSUS_SOURCES.get(scene_id)
    except Exception:  # noqa: BLE001 - fail-closed, see the docstring
        return None


def targets_with_a_resolvable_cast() -> tuple[int, ...]:
    """Which of the eight Columbus targets resolve a cast at all.

    Derived from ``_MEASURED_ROWS`` through ``cast_capacity`` rather than
    stated, so a corrected row changes the answer instead of leaving a
    sentence somebody has to remember to edit.
    """
    return tuple(
        scene_id
        for scene_id in COLUMBUS_TARGET_SCENE_IDS
        if cast_capacity(scene_id).a_cast_resolves
    )


def targets_with_no_roster_yet() -> tuple[int, ...]:
    """Targets whose cast resolves and which this lane has NOT built yet.

    This is the buildable-today list the first draft would have hidden.
    """
    return tuple(
        scene_id
        for scene_id in targets_with_a_resolvable_cast()
        if cast_capacity(scene_id).composer_source is None
    )


def halves_agree() -> bool:
    """Do the door and the survey trial name the same scene?

    False under the scene-id reading of the door (17 vs 126) and True under
    the rival ``MARKER`` reading (126 vs 126).  Reported with
    ``DOOR_SCENE_ID_IS_CONTESTED`` beside it precisely because the answer
    is a function of an unsettled reading, not a measurement.
    """
    return DOOR_SCENE_ID == TRIAL_SCENE_ID


def sea_scene_cast_console_line() -> str:
    """One ASCII line: what each half of M2's sea resolves, and how many of
    the eight targets are buildable but unbuilt.

    Greppable token: ``M2_SEA_CAST``.
    """
    door = cast_capacity(DOOR_SCENE_ID)
    trial = cast_capacity(TRIAL_SCENE_ID)
    unbuilt = targets_with_no_roster_yet()
    unbuilt_text = ",".join(str(scene_id) for scene_id in unbuilt) or "none"
    return (
        "M2_SEA_CAST"
        f" door={door.scene_id}"
        f" door_contested={'YES' if DOOR_SCENE_ID_IS_CONTESTED else 'NO'}"
        f" door_verdict={door.verdict}"
        f" door_source={door.answering_source or 'none'}"
        f" door_cast={door.resolved}/{door.placements}"
        f" door_composer={door.composer_source or 'none'}"
        f" trial={trial.scene_id}"
        f" trial_verdict={trial.verdict}"
        f" trial_source={trial.answering_source or 'none'}"
        f" trial_cast={trial.resolved}/{trial.placements}"
        f" trial_composer={trial.composer_source or 'none'}"
        f" halves_agree={'YES' if halves_agree() else 'NO'}"
        f" targets_resolving={len(targets_with_a_resolvable_cast())}"
        f"/{len(COLUMBUS_TARGET_SCENE_IDS)}"
        f" targets_buildable_unbuilt={unbuilt_text}"
        f" sources_checked={len(CREATURE_LINE_SOURCES)}"
    )


def sea_scene_cast_console_line_safe() -> str:
    """The line, on a path that must never raise.

    Same contract as ``world_m2_sea_destination.console_line_safe``: a
    report that fails says so on one line and the crossing carries on.
    """
    try:
        return sea_scene_cast_console_line()
    except Exception as error:  # noqa: BLE001 - report path, see the docstring
        return f"M2_SEA_CAST unmeasured reason={type(error).__name__}"
