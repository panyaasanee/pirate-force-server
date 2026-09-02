"""GM-A preflight: what the SERVER will compose for every map ``/warp`` reaches.

WHY THIS EXISTS.  ``NOW.md`` records the owner's acceptance criterion for
GM-A in her own words: warping across several maps in a row must find the
NPCs on EVERY map.  ``COO-DECISION 2026-09-02T05:44+07:00`` turned that into
the closed list a tester types -- scenes ``2-11``, ``14``, ``130``, closing
with ``1`` -- and ``GT-192`` is the attended entry that grades it.

An attended round is this project's most expensive resource, and today a
tester types those thirteen lines with no way to tell three different things
apart when a map comes up empty:

* the census-latch bug ``GT-192`` exists to catch (a real FAIL);
* a map that is empty ON ARRIVAL BY DESIGN and fills once she takes one step
  (scene 1's walk-before-census disjunct, held shut on purpose by
  ``KA1A-AMENDMENT 20260901_1120``);
* a map whose census comes from an arm this lane does not own, so the
  everyday seam every other scene answers through reports ``clear``/0 for it.

This module answers all three from the registries BEFORE she boots, one line
per scene, so an empty map is graded against a stated prediction instead of
being a surprise.

WHAT IT IS NOT.  It predicts what the SERVER WILL COMPOSE.  It does not open
a socket, does not boot a runtime, does not send a frame, and says nothing
whatsoever about what the client RENDERS -- that is the whole point of
``GT-192``'s client-observable layer and no number printed here can stand in
for it.  A green preflight and an empty screen is exactly the valuable
negative result ``GT-192``'s own pass criteria ask the tester to write up.

IT GRANTS NOBODY ANYTHING.  There is no account in this module, no GM state,
no gate to flip.  It reads the scene registry, the ``lane_hooks`` composer
registry and the ``/warp`` production gate, all read-only, and it runs with
``production_allowed`` false everywhere, like every other tool in this lane.

THE TRAP THIS MODULE WAS BUILT AROUND, WRITTEN DOWN SO IT CANNOT BE LOST.
The obvious implementation -- ask ``world_population_handoff
.handoff_for_arrival`` for every reachable scene and print its
``actor_count`` -- MISPREDICTS SCENE 2.  Measured on this clone: that seam
answers ``kind='clear'``, ``actor_count=0`` for scene 2, because scene 2 is
``reserved_by_a_runtime_branch`` in ``lane_a_scene_census.skipped_scenes()``
and its roster ships from the runtime's own bg0002 arm
(``runtime.py:8536``), not through a lane composer.  A preflight built that
way would print ``0`` for the FIRST map on the owner's list and send a
tester looking for a bug that is not there.  Scene 2 is therefore asked of
its own arm, with the same arguments the runtime's call site passes, and
``tests/test_gm_warp_chain_preflight.py`` reads that call site's source to
keep the two from drifting.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Any

from .. import (
    lane_hooks,
    world_population,
    world_population_bg0002,
    world_population_handoff,
    world_scene_travel,
)
from . import scene_catalog
from .warp_executor import warp_no_coords_live_target

# Every line this module prints starts with this, for the same reason every
# other console token in this lane does: a tester greps for it, and a
# diagnostic that cannot be found is a diagnostic that was not written.
CONSOLE_TOKEN = "GM_WARP_PREFLIGHT"

# Where a scene's arrival roster comes from.  Four answers, not two: the
# difference between "nothing, and that is the bug" and "nothing until you
# move, and that is the design" is the entire reason this module exists.
SOURCE_LANE_COMPOSER = "lane_composer"
SOURCE_RUNTIME_BG0002_ARM = "runtime_bg0002_arm"
SOURCE_HELD_UNTIL_THE_PLAYER_MOVES = "held_until_the_player_moves"
SOURCE_NOTHING = "nothing"

LEGACY_RELATIVE_PATH = pathlib.PurePosixPath("current/pf_login_game_server_v141.py")


@dataclass(frozen=True)
class ScenePreflight:
    """One row: one scene the tester will type, and what to expect there.

    ``actor_count`` is what the server will COMPOSE, and it is ``None``
    whenever this module could not derive a number -- never ``0`` standing in
    for "do not know".  ``on_arrival`` is the field a tester actually reads:
    False means she will see an empty map without having done anything wrong.
    """

    scene_id: int
    gm_name: str
    source: str
    module: str | None
    actor_count: int | None
    on_arrival: bool
    note: str


def reachable_scene_ids() -> tuple[int, ...]:
    """Every scene id a bare ``/warp <scene>`` can reach today.

    Asked of the PRODUCTION gate, never listed here: the day LANE-A opens
    another marker-backed scene this preflight covers it without an edit, and
    the day one closes, no row here describes a map nobody can reach.  A
    ``/warp`` to a scene outside this set is REFUSED BY NAME, which is a
    different thing from an empty map and must not be confused with one.
    """
    return tuple(
        scene_id
        for scene_id in sorted(scene_catalog.SCENE_ID_TO_GM_NAME)
        if warp_no_coords_live_target(scene_id) is not None
    )


def _gm_name(scene_id: int) -> str:
    return scene_catalog.SCENE_ID_TO_GM_NAME.get(scene_id, "?")


def _row(scene_id: int, source: str, module: Any, count: Any, arrival: bool,
         note: str) -> ScenePreflight:
    return ScenePreflight(
        scene_id=scene_id,
        gm_name=_gm_name(scene_id),
        source=source,
        module=module,
        actor_count=count,
        on_arrival=arrival,
        note=note,
    )


def preflight_for(scene_id: int, *, legacy: Any) -> ScenePreflight:
    """One scene's expectation.  Never raises for a scene-shaped input.

    FAILS CLOSED AND NAMED.  Anything this module cannot derive comes back as
    ``SOURCE_NOTHING`` with the exception type in ``note`` and
    ``actor_count=None``.  A preflight that crashes on one map takes the
    other twelve down with it, and a preflight that guesses is worse than no
    preflight at all -- the tester would grade a real bug as "expected".
    """
    if warp_no_coords_live_target(scene_id) is None:
        return _row(
            scene_id, SOURCE_NOTHING, None, None, False,
            "/warp refuses this scene by name; it is not an empty map",
        )

    try:
        anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(scene_id)
        )
    except Exception as error:  # noqa: BLE001 - reported, never swallowed
        return _row(
            scene_id, SOURCE_NOTHING, None, None, False,
            "the registry does not pin a spawn: %s" % type(error).__name__,
        )

    # SCENE 2 FIRST, before the composer registry is consulted, because the
    # registry's honest answer for it is None and the seam's honest answer is
    # `clear`/0 -- see this module's docstring.
    if scene_id == world_population_bg0002.SCENE2_N_ID:
        try:
            generation = world_population_bg0002.build_bg0002_population(
                legacy, anchor, scene_id=scene_id,
                count_source=world_population_bg0002.COUNT_SOURCE_FULL_ROSTER,
            )
            count = world_population_bg0002.wire_actor_count(generation)
        except Exception as error:  # noqa: BLE001
            return _row(
                scene_id, SOURCE_NOTHING, None, None, False,
                "the bg0002 arm refused: %s" % type(error).__name__,
            )
        return _row(
            scene_id, SOURCE_RUNTIME_BG0002_ARM, "runtime.py", count, True,
            "ships from the runtime's own arm, not from lane_hooks; the "
            "everyday arrival seam reports clear/0 for this scene",
        )

    # SCENE 1: the composer answers, and the arrival path holds it shut.
    if scene_id == world_population.SCENE_ID:
        count = _lane_count(scene_id, anchor, legacy=legacy)
        return _row(
            scene_id, SOURCE_HELD_UNTIL_THE_PLAYER_MOVES,
            None, count, False,
            "EMPTY ON ARRIVAL BY DESIGN (KA1A-AMENDMENT 20260901_1120); "
            "take one step and the census follows",
        )

    composer = lane_hooks.scene_census_composer(scene_id)
    if composer is None:
        return _row(
            scene_id, SOURCE_NOTHING, None, None, False,
            "reachable, but no lane composer claims it and it is not scene 2",
        )
    if not lane_hooks.module_production_allowed(composer.module):
        return _row(
            scene_id, SOURCE_NOTHING, composer.module, None, False,
            "a composer is registered but its module is not production-allowed",
        )
    count = _lane_count(scene_id, anchor, legacy=legacy)
    if count is None:
        return _row(
            scene_id, SOURCE_NOTHING, composer.module, None, False,
            "the composer declined for this scene",
        )
    return _row(
        scene_id, SOURCE_LANE_COMPOSER, composer.module, count, True,
        "composed by the registered lane hook at this scene's pinned spawn",
    )


def _lane_count(scene_id: int, anchor: Any, *, legacy: Any) -> int | None:
    """The actor count the arrival seam would compose, or ``None``.

    Read off the SEAM rather than off a composer's label for the same reason
    ``test_gm_warp_chain_census_shipped.py`` reads its counts off the wire:
    a label is a number a lane handed over, and the runtime's own comment at
    that hand-off calls it untrusted.
    """
    try:
        handoff = world_population_handoff.handoff_for_arrival(
            legacy, scene_id, anchor,
        )
    except Exception:  # noqa: BLE001 - the caller turns this into a named row
        return None
    if handoff.kind != world_population_handoff.KIND_CENSUS:
        return None
    return int(handoff.actor_count)


def preflight_chain(
    scene_ids: Any = None, *, legacy: Any
) -> tuple[ScenePreflight, ...]:
    """Every reachable scene by default, in the order the tester types them.

    The default order is the owner's own list: the non-home scenes ascending,
    with scene 1 LAST.  That is not cosmetic -- a session boots in scene 1, so
    warping there first is a same-scene no-op that returns before the resync
    runs, and a chain that opens on it proves nothing about the latch.
    """
    if scene_ids is None:
        reachable = reachable_scene_ids()
        home = world_population.SCENE_ID
        ordered = [s for s in reachable if s != home]
        if home in reachable:
            ordered.append(home)
        scene_ids = ordered
    return tuple(preflight_for(int(s), legacy=legacy) for s in scene_ids)


def render(rows: Any) -> tuple[str, ...]:
    """ASCII console lines, one per scene plus one summary.

    ASCII on purpose: the bridge console is cp874 (`GT-145`), and a tool whose
    output the owner cannot paste back is a tool that did not run.
    """
    lines = []
    empty_by_design = []
    empty_unexplained = []
    for row in rows:
        count = "?" if row.actor_count is None else str(row.actor_count)
        lines.append(
            "%s scene=%d actors_on_arrival=%s source=%s name=%s"
            % (
                CONSOLE_TOKEN,
                row.scene_id,
                count if row.on_arrival else "0",
                row.source,
                _ascii(row.gm_name),
            )
        )
        if row.on_arrival:
            continue
        if row.source == SOURCE_HELD_UNTIL_THE_PLAYER_MOVES:
            empty_by_design.append(row.scene_id)
        else:
            empty_unexplained.append(row.scene_id)
    lines.append(
        "%s chain=%d empty_by_design=%s empty_unexplained=%s"
        % (
            CONSOLE_TOKEN,
            len(tuple(rows)),
            _joined(empty_by_design),
            _joined(empty_unexplained),
        )
    )
    # The sentence a tester needs and no count gives her.
    lines.append(
        "%s NOTE this predicts what the SERVER composes, never what the "
        "client draws; an empty screen on a scene listed above with actors "
        "is a real finding for GT-192, not a preflight error" % CONSOLE_TOKEN
    )
    return tuple(lines)


def _joined(scene_ids: Any) -> str:
    return ",".join(str(s) for s in scene_ids) if scene_ids else "none"


def _ascii(text: Any) -> str:
    return str(text).encode("ascii", "replace").decode("ascii").replace(" ", "_")


def main(argv: Any = None) -> int:
    """``python3 -m pirateforce_foundation.gm.warp_chain_preflight``.

    Optional positional scene ids run a custom chain; no arguments runs the
    whole reachable world in the owner's order.
    """
    import sys

    from ..legacy_bridge import load_legacy

    args = list(sys.argv[1:] if argv is None else argv)
    root = pathlib.Path(__file__).resolve().parents[3]
    legacy = load_legacy(root / str(LEGACY_RELATIVE_PATH))
    scenes = [int(a) for a in args] if args else None
    for line in render(preflight_chain(scenes, legacy=legacy)):
        print(line)
    return 0


if __name__ == "__main__":  # pragma: no cover - the entry point itself
    raise SystemExit(main())
