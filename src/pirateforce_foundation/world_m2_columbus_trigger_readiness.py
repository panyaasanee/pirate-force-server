"""Whether each island's own Columbus is actually standing where a player
could click him - LANE-A, M2.

WHAT THIS MODULE IS FOR.  ``world_m2_sea_destination`` already answers one
half of "can a later round wire the other seven islands' Columbus crossings":
does the registry hold a place to LAND (``sea_map_lines`` / ``WORLD_M2_SEA_
MAP``).  Its own docstring names the other half, unmeasured, in so many
words: "whether the other seven islands' own Columbus NPCs are even placed
on a default boot is unmeasured by this module."  This module measures it -
the TRIGGER side, not the arrival side - by reusing the exact placement
tables ``BUILD-001``'s own per-scene population modules already resolved,
not a second, silently divergent copy of them.

WHAT IT DOES NOT DO.  It does not dispatch anything, wire a new NPCConversation,
or touch ``runtime.py``.  It composes a report and nothing else - the same
report-only, never-raises-on-the-frame-path shape as every other file in this
family (``world_m2_sea_destination``, ``world_m2_crossing_handoff``,
``world_m2_return_leg``).  It hooks into the ONE call site that already runs
every boot, flagless - ``columbus_quest_dispatch.dispatch_columbus_quest3021``
- so this round needs no runtime.py edit and no CORE-REQUEST to make it fire.

WHY THIS IS SAFE WITHOUT PLAYER IDENTITY.  Every accessor this module reads
is a FROZEN, per-scene, scene-shaped table (the same ones each scene's own
``world_population_bgXXXX`` module already builds a census from) - nothing
here is keyed by a player, a character row, or a session.  "Is Columbus
placed in this scene's own default cast" is a fact about the scene, measured
once per boot exactly like the sea-map's own registry-readiness question.

HOME SCENE 1 (PORT ROYAL) IS SPECIAL-CASED, ON PURPOSE, NOT AN OVERSIGHT.
``population.load_port_royal_placements`` returns ``SceneActorPlacement``
rows whose ``template_id`` field is NOT the same column the other seven
scenes expose as their placement's MOBS n_id (see the "TWO DIFFERENT COLUMNS,
SAME NAME" section below) - Port Royal's own working dispatch has never
needed to match Columbus by MOBS n_id at all; it matches by
``placement_index == COLUMBUS_PLACEMENT_INDEX`` (``columbus_quest_dispatch.
columbus_actor_identity``), which is the ONLY check this project's own
shipped, GT-148-confirmed dispatch actually relies on.  This module reuses
that exact function for home scene 1 rather than inventing a second,
n_id-keyed check that the working code does not use.

TWO DIFFERENT COLUMNS, SAME NAME, AND THE MISTAKE THIS ROUND CAUGHT IN ITS
OWN FIRST DRAFT.  ``Bg0004Placement.template_id`` (and its five siblings'
same-named field) is NOT the placement's MOBS n_id - it is the per-scene
Mob-Set number, the same column ``world_bg0004_identity``'s own
``_RESOLVED_ROWS`` header names first: "(Mob-Set number, CLINE row n_ID,
MOBS.n_ID, ...)".  The placement's real MOBS n_id is the THIRD field of its
resolved ``identity`` (``Bg0004Placement.identity.mobs_n_id``), a completely
different number from ``template_id`` for every placement in every one of
these six scenes.  This module's first draft matched ``COLUMBUS_ROUTES``'
MOBS n_ids against ``template_id`` directly and got every one of the seven
non-Port-Royal islands wrong (0 of 7 matched); re-reading each identity
module's own ``_RESOLVED_ROWS`` header caught it before this round's numbers
went anywhere.  ``scene2_prison_exile_tables.Bg0002Placement`` is the one
exception that needed no correction: its own field really is named ``n_id``
and its own header confirms it is the MOBS column
("(placement_index, mm_instance, n_id, x, y, z, ...)").

WHAT THIS ROUND MEASURED, RE-DERIVED FROM THE SIX SCENES' OWN SHIPPED TABLES
RATHER THAN QUOTED (every accessor below is exercised by this module's own
tests against the real, committed identity/placement modules):

    home 1 (Port Royal,      MOBS 156): PLACED     (columbus_actor_identity
                                                      resolves placement_index 1)
    home 2 (Prison Exile,    MOBS 360): NOT PLACED - see the discrepancy below
    home 3 (Spice Paradise,  MOBS  36): PLACED (world_bg0003_identity, 62 shippable)
    home 4 (Slave Market,    MOBS  67): PLACED (world_bg0004_identity, 109 shippable)
    home 5 (Evil Port,       MOBS 105): PLACED (world_bg0005_identity, 87 shippable)
    home 6 (Ocean Walled City,MOBS196): PLACED (world_bg0006_identity, 66 shippable)
    home 7 (Voodoo,          MOBS 362): PLACED (world_bg0007_identity, 56 shippable)
    home 8 (Silver Harbour,  MOBS 250): PLACED (world_bg0008_identity, 69 shippable)

A GENUINE DISCREPANCY, REPORTED RATHER THAN GUESSED AT.  Home scene 2
(Prison Exile)'s own ``scene2_prison_exile_tables.KNOWN_PLACEMENTS`` row 63
carries a placement named "Columbus" (outfit ``M055_000_000_N``, title
"Marine Transport Station" - the exact same outfit/title every other
island's Columbus row carries) with MOBS n_id **36**, not the **360**
``world_m2_sea_destination.COLUMBUS_ROUTES`` names for home scene 2.  This is
not a made-up number on either side: ``gamedata/tables/CONSTDATA_TH__
MOBS.tsv`` carries TWO separate rows, n_id 36 AND n_id 360, both named
"..." (Columbus, in the client's own CJK string) with the identical outfit
``M055_000_000_N`` - so both ids are real, committed MOBS rows, and n_id 36
is also the id ``world_bg0003_identity`` (home 3, Spice Paradise) already
uses for ITS OWN Columbus.  Two different scenes' own resolved tables cannot
both be citing the correct row for two different islands if they name the
SAME id, so this module reports home 2 as NOT_PLACED against the id
``COLUMBUS_ROUTES`` names for it (360) rather than silently accepting 36 as
a stand-in - CHARTER-02's "never invent a row the client's own tables do not
have" cuts against guessing which of the two tables is the one that is
wrong.  Sent to lane C (RE) rather than fixed here - see the round handoff.

WHAT THIS DOES NOT CLAIM.  It does not claim any of these seven islands'
Columbus is CLICKABLE today - reaching him needs a runtime.py dispatch this
lane has not asked for this round (would require the same per-scene
``population_indices`` gate Port Royal's own dispatch uses, wired seven more
times), and it does not claim the arrival side is ready either -
``world_m2_sea_destination.sea_map_lines`` already answers that, separately,
and this module never re-derives it.  "Placed" here means only "this scene's
own frozen cast, as this project's own population module already resolved
it, contains an actor with this MOBS n_id" - nothing about wiring, nothing
about the client having rendered it, nothing about whether any door to that
home scene is even open on a default boot today.
"""
from __future__ import annotations

from . import columbus_quest_dispatch
from . import scene2_prison_exile_tables
from . import world_bg0003_identity
from . import world_bg0004_identity
from . import world_bg0005_identity
from . import world_bg0006_identity
from . import world_bg0007_identity
from . import world_bg0008_identity
from . import world_m2_sea_destination

# Convention marker: this module is not a scenario and is not behind a flag.
production_allowed = True
test_only = False

CONSOLE_TAG = "WORLD_M2_TRIGGER_READINESS"

STATE_PLACED = "PLACED"
STATE_NOT_PLACED = "NOT_PLACED"
# Only reachable for home scene 1 today (Port Royal), and only when a caller
# hands over no ``legacy`` module - every other home scene's accessor reads
# a frozen, in-tree table and needs nothing external, so it can never go
# unmeasured.
STATE_UNMEASURED = "UNMEASURED"

UNMEASURED_REASON_NO_LEGACY = "call_site_passed_no_legacy"

# The one home scene whose Columbus check is not "does this MOBS n_id appear
# among this scene's own resolved placements" - see the module docstring's
# "HOME SCENE 1 IS SPECIAL-CASED" section for why reusing ``columbus_quest_
# dispatch.columbus_actor_identity`` here is the correct reuse, not a
# shortcut.
PORT_ROYAL_HOME_SCENE = 1


class TriggerReadinessError(Exception):
    """This module refused rather than guessed."""


def _bg0002_mobs_n_ids() -> frozenset[int]:
    """Prison Exile's own resolved MOBS n_ids - ``n_id`` is the real column
    here (see the module docstring; this scene's placement dataclass needed
    no template_id/mobs_n_id correction, unlike the other five)."""
    return frozenset(
        placement.n_id
        for placement in scene2_prison_exile_tables.load_known_placements()
    )


def _bg0003_mobs_n_ids() -> frozenset[int]:
    return frozenset(
        placement.identity.mobs_n_id
        for placement in world_bg0003_identity.shippable_placements()
    )


def _bg0004_mobs_n_ids() -> frozenset[int]:
    return frozenset(
        placement.identity.mobs_n_id
        for placement in world_bg0004_identity.shippable_placements()
    )


def _bg0005_mobs_n_ids() -> frozenset[int]:
    return frozenset(
        placement.identity.mobs_n_id
        for placement in world_bg0005_identity.shippable_placements()
    )


def _bg0006_mobs_n_ids() -> frozenset[int]:
    return frozenset(
        placement.identity.mobs_n_id
        for placement in world_bg0006_identity.shippable_placements()
    )


def _bg0007_mobs_n_ids() -> frozenset[int]:
    return frozenset(
        placement.identity.mobs_n_id
        for placement in world_bg0007_identity.shippable_placements()
    )


def _bg0008_mobs_n_ids() -> frozenset[int]:
    return frozenset(
        placement.identity.mobs_n_id
        for placement in world_bg0008_identity.shippable_placements()
    )


# Home scene -> a zero-argument callable returning that scene's own resolved
# MOBS n_ids.  Home scene 1 (Port Royal) is deliberately absent - see
# ``trigger_state_for`` for why it is handled through a different, already-
# shipped check instead of an accessor of this shape.
HOME_SCENE_MOBS_N_ID_ACCESSORS = {
    2: _bg0002_mobs_n_ids,
    3: _bg0003_mobs_n_ids,
    4: _bg0004_mobs_n_ids,
    5: _bg0005_mobs_n_ids,
    6: _bg0006_mobs_n_ids,
    7: _bg0007_mobs_n_ids,
    8: _bg0008_mobs_n_ids,
}


def trigger_state_for(mobs_n_id: int, home_scene: int, *, legacy=None) -> str:
    """PLACED, NOT_PLACED or UNMEASURED for one ``COLUMBUS_ROUTES`` row.

    Raises on a malformed CALL (wrong types, an unknown home scene) - this is
    the strict half; :func:`trigger_readiness_console_line` is the
    never-raises wrapper for the frame path, same two-function shape as every
    report next door.
    """
    if type(mobs_n_id) is not int or type(home_scene) is not int:
        raise TriggerReadinessError(
            "mobs_n_id and home_scene must both be int")
    if home_scene == PORT_ROYAL_HOME_SCENE:
        if legacy is None:
            return STATE_UNMEASURED
        try:
            columbus_quest_dispatch.columbus_actor_identity(legacy)
        except columbus_quest_dispatch.ColumbusActorNotFound:
            return STATE_NOT_PLACED
        return STATE_PLACED
    accessor = HOME_SCENE_MOBS_N_ID_ACCESSORS.get(home_scene)
    if accessor is None:
        raise TriggerReadinessError(
            "no placement accessor wired for home scene %d - COLUMBUS_ROUTES "
            "names a home scene this module has not been taught to read"
            % home_scene
        )
    return STATE_PLACED if mobs_n_id in accessor() else STATE_NOT_PLACED


def trigger_readiness_rows(
    *, legacy=None,
) -> tuple[tuple[int, int, str], ...]:
    """(MOBS n_id, home scene, state) for every ``COLUMBUS_ROUTES`` island.

    Reuses ``world_m2_sea_destination.COLUMBUS_ROUTES`` - the same eight-row
    table the sea-map report already widens across - rather than holding a
    second, silently divergent copy of "the eight islands".
    """
    rows = []
    for mobs_n_id, home_scene, _row_id, _target, _ocean in (
        world_m2_sea_destination.COLUMBUS_ROUTES
    ):
        rows.append((
            mobs_n_id, home_scene,
            trigger_state_for(mobs_n_id, home_scene, legacy=legacy),
        ))
    return tuple(rows)


def trigger_readiness_console_line(*, legacy=None) -> str:
    """The ``WORLD_M2_TRIGGER_READINESS`` line, for every crossing, every
    boot.

    NEVER RAISES, same reason and same shape as every other report in this
    family: composed on the frame path, with no ``except`` of its own at the
    call site.
    """
    try:
        rows = trigger_readiness_rows(legacy=legacy)
    except Exception as error:  # noqa: BLE001 - report-only, see docstring
        return (
            CONSOLE_TAG + " unmeasured reason=refused:"
            + type(error).__name__
        )
    try:
        placed = sum(1 for _m, _h, state in rows if state == STATE_PLACED)
        not_placed = sum(
            1 for _m, _h, state in rows if state == STATE_NOT_PLACED)
        unmeasured = sum(
            1 for _m, _h, state in rows if state == STATE_UNMEASURED)
        detail = ",".join(
            "%d:%s" % (home, state) for _mobs, home, state in rows
        )
        return (
            "{tag} islands={islands} placed={placed} not_placed={not_placed} "
            "unmeasured={unmeasured} detail={detail}".format(
                tag=CONSOLE_TAG,
                islands=len(rows),
                placed=placed,
                not_placed=not_placed,
                unmeasured=unmeasured,
                detail=detail,
            )
        )
    except Exception as error:  # noqa: BLE001 - report-only, see docstring
        return CONSOLE_TAG + " uncomposable reason=" + type(error).__name__


def _self_check() -> None:
    """Internal consistency only - this file has no tables of its own."""
    routes_home_scenes = {
        home for _mobs, home, _row, _target, _ocean in
        world_m2_sea_destination.COLUMBUS_ROUTES
    }
    known_home_scenes = set(HOME_SCENE_MOBS_N_ID_ACCESSORS) | {
        PORT_ROYAL_HOME_SCENE,
    }
    if routes_home_scenes != known_home_scenes:
        raise TriggerReadinessError(
            "HOME_SCENE_MOBS_N_ID_ACCESSORS (plus the Port Royal special "
            "case) must name exactly the home scenes COLUMBUS_ROUTES lists - "
            "this report would silently drop or invent an island"
        )


_self_check()
