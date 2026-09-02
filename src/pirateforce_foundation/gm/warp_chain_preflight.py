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
# A map that is SHUT ON PURPOSE (`login_entry_allowed` false) is its own
# answer, never `nothing`: the runtime declines and ships no frame, the
# screen is empty, and it is not a defect.  Folding it into `nothing` is
# what made the first version of this module dangerous (pf-adversary D1).
SOURCE_SHUT_TO_PLAYERS = "shut_to_players"
SOURCE_NOTHING = "nothing"

# `runtime.py:993`.  Printed with every run, because a boot that fails this
# ships no census on any map and would otherwise read as thirteen bugs.
BOOT_PRECONDITION = (
    "census ships ONLY on a boot with no scenario/lane object AND "
    "second_password_mode=required (runtime.py:993); otherwise every map "
    "below is empty and that is the boot, not a bug"
)

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


def _scene_registry(scene_entry_registry: Any) -> Any:
    """The boot-loaded registry the runtime hands its composers.

    Loaded once and cached: ``preflight_chain`` asks for thirteen scenes and
    re-reading the file thirteen times would make a fast tool slow for no
    reason.  Injectable so a test can shut a map without editing one.
    """
    if scene_entry_registry is not None:
        return scene_entry_registry
    if not hasattr(_scene_registry, "cached"):
        _scene_registry.cached = world_scene_travel.load_scene_registry()
    return _scene_registry.cached


def preflight_for(
    scene_id: int, *, legacy: Any, scene_entry_registry: Any = None
) -> ScenePreflight:
    """One scene's expectation.  Never raises for an ``int`` scene id.

    FAILS CLOSED AND NAMED.  Anything this module cannot derive comes back as
    a row carrying the reason -- never a crash, and never ``0`` standing in
    for "do not know".  A preflight that crashes on one map takes the other
    twelve down with it, and a preflight that guesses is worse than none at
    all: the tester would grade a real bug as "expected".

    ``bool`` IS NOT AN INT HERE, and that is a fix, not pedantry.  The warp
    gate accepts ``True`` (it hashes as 1) but the scene registry type-checks
    strictly and raises, so the first version of this function answered
    ``preflight_for(True)`` with "the registry does not pin a spawn" for Port
    Royal -- printing the name of the one scene whose spawn is most certainly
    pinned, and rendering it as an unexplained empty map (pf-adversary D6).
    Two entry points gave opposite verdicts for one scene.  Now the type is
    refused by name, once, at the top.
    """
    if type(scene_id) is not int:
        return _row(
            -1, SOURCE_NOTHING, None, None, False,
            "scene id must be an int, not %s" % type(scene_id).__name__,
        )

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
                scene_id, SOURCE_NOTHING, "runtime.py", None, False,
                "the bg0002 arm refused: %s" % type(error).__name__,
            )
        return _row(
            scene_id, SOURCE_RUNTIME_BG0002_ARM, "runtime.py", count, True,
            "ships from the runtime's own arm, not from lane_hooks; the "
            "everyday arrival seam reports clear/0 for this scene",
        )

    # SCENE 1 SECOND, and for the same structural reason as scene 2: there are
    # THREE arms in this runtime, not two.  Scene 2 is the bg0002 arm, scene 1
    # is the HOME arm, and everything else is a `lane_hooks` composer.  Neither
    # of the first two has a composer in the registry, so a version of this
    # function that reached the registry lookup first answered `nothing` for
    # BOTH -- measured, and it is why this branch sits above that lookup.
    #
    # ASKED OF THE HOME ARM ITSELF, not of `handoff_for_arrival`.  A first
    # version of this branch went through that seam and the FULL SUITE caught
    # it: `test_world_population_bg0015.py::
    # test_only_the_population_seam_imports_this_module` is another lane's gate
    # naming the exact three files allowed to be call sites of the arrival
    # seam, and this module is not one of them.  Going around another lane's
    # gate to make a diagnostic prettier is how a diagnostic starts altering
    # dispatch, so the branch was rewritten rather than the gate widened.
    #
    # The ARRIVAL PATH then holds this scene shut until the player moves,
    # which is the design and not a defect.
    if scene_id == world_population.SCENE_ID:
        try:
            generation = world_population.build_world_population(
                legacy, anchor, world_population.effective_actor_count(),
                scene_id=scene_id,
                count_source=world_population.COUNT_SOURCE_MEASURED_CEILING,
            )
            count = world_population.wire_actor_count(generation)
        except Exception as error:  # noqa: BLE001
            return _row(
                scene_id, SOURCE_NOTHING, "runtime.py", None, False,
                "the home arm refused: %s" % type(error).__name__,
            )
        return _row(
            scene_id, SOURCE_HELD_UNTIL_THE_PLAYER_MOVES,
            "runtime.py", count, False,
            "EMPTY ON ARRIVAL BY DESIGN (KA1A-AMENDMENT 20260901_1120); "
            "take ONE STEP and the census follows",
        )

    composer = lane_hooks.scene_census_composer(scene_id)
    if composer is None:
        return _row(
            scene_id, SOURCE_NOTHING, None, None, False,
            "reachable, but no lane composer claims it and it is neither of "
            "the two scenes the runtime serves from its own arms",
        )
    if not lane_hooks.module_production_allowed(composer.module):
        return _row(
            scene_id, SOURCE_NOTHING, composer.module, None, False,
            "a composer is registered but its module is not production-allowed",
        )

    outcome, count = _composed_count(
        composer, scene_id, anchor,
        legacy=legacy, scene_entry_registry=scene_entry_registry,
    )
    if outcome != _COMPOSED:
        # The composer's two failure answers are NOT the same event and the
        # runtime does not treat them as one: a DECLINE latches
        # `world_census_sent` for this map alone, while a RAISE latches
        # `world_census_refused`, which silences every remaining map of the
        # login until the next hop clears it.  Collapsing them and printing
        # the harmless word was pf-adversary D5.
        if outcome == _DECLINED:
            return _row(
                scene_id, SOURCE_SHUT_TO_PLAYERS, composer.module, None, False,
                "SHUT ON PURPOSE: the composer declined (login_entry_allowed "
                "is false for this scene); an empty screen here is the design",
            )
        return _row(
            scene_id, SOURCE_NOTHING, composer.module, None, False,
            "the composer raised: %s -- the runtime would latch "
            "world_census_refused and silence later maps too" % outcome,
        )

    return _row(
        scene_id, SOURCE_LANE_COMPOSER, composer.module, count, True,
        "composed by the registered lane hook at this scene's pinned spawn",
    )


_COMPOSED = "composed"
_DECLINED = "declined"


def _composed_count(
    composer: Any, scene_id: int, anchor: Any, *, legacy: Any,
    scene_entry_registry: Any,
) -> tuple:
    """CALL THE COMPOSER, the way the runtime does, and count the BYTES.

    Not ``handoff_for_arrival``.  That seam is one gate short: it never sees
    the composer's own admission check, so it answers with a roster for a map
    the runtime would decline (pf-adversary D1).  The route the runtime takes
    is the only route worth predicting.

    And the number is read back off ``result.pc`` rather than off
    ``result.actor_count``, for the reason
    ``test_gm_warp_chain_census_shipped.py`` gives for the same choice: the
    label is an integer a lane handed over, which the runtime's own comment
    at that hand-off calls untrusted, and a label can say 56 over an empty
    buffer.
    """
    try:
        result = composer.compose(
            legacy=legacy,
            anchor=anchor,
            scene_id=scene_id,
            scene_entry_registry=_scene_registry(scene_entry_registry),
        )
    except Exception as error:  # noqa: BLE001 - the caller names the type
        return type(error).__name__, None
    if result is None:
        return _DECLINED, None
    try:
        return _COMPOSED, world_population_handoff.wire_count_of(result.pc)
    except Exception as error:  # noqa: BLE001
        return type(error).__name__, None


def preflight_chain(
    scene_ids: Any = None, *, legacy: Any, scene_entry_registry: Any = None
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
    return tuple(
        preflight_for(
            s, legacy=legacy, scene_entry_registry=scene_entry_registry,
        )
        for s in scene_ids
    )


def render(rows: Any) -> tuple[str, ...]:
    """ASCII console lines: a precondition, one per scene, then a summary.

    ASCII on purpose: the bridge console is cp874 (`GT-145`), and a tool whose
    output the owner cannot paste back is a tool that did not run.

    ``rows`` IS MATERIALISED FIRST, and that is a bug fix, not a style.  An
    earlier version counted the chain with ``len(tuple(rows))`` AFTER the loop
    below had already walked it; handed a generator -- which
    ``preflight_chain`` is one comprehension away from returning -- it printed
    thirteen correct scene lines and then a summary saying ``chain=0``.
    Measured, not imagined.  A summary that disagrees with the lines above it
    is worse than no summary: it is the one line a reader quotes.

    EVERY ROW PRINTS ITS REASON.  ``note`` used to be computed with care and
    shown to nobody (pf-adversary D4), so a ``/warp`` REFUSED BY NAME, a map
    shut on purpose and a map with the real census bug all printed the same
    line and were all swept into ``empty_unexplained``.  The distinction this
    module exists to make has to reach a console, not a dataclass.

    THE PRECONDITION LEADS, because it can invalidate every line under it.
    """
    rows = tuple(rows)
    lines = ["%s PRECONDITION %s" % (CONSOLE_TOKEN, BOOT_PRECONDITION)]
    by_design = []
    shut = []
    unexplained = []
    for row in rows:
        lines.append(
            "%s scene=%d actors_on_arrival=%s source=%s name=%s why=%s"
            % (
                CONSOLE_TOKEN,
                row.scene_id,
                ("?" if row.actor_count is None else str(row.actor_count))
                if row.on_arrival else "0",
                row.source,
                _ascii(row.gm_name),
                _ascii(row.note),
            )
        )
        if row.on_arrival:
            continue
        if row.source == SOURCE_HELD_UNTIL_THE_PLAYER_MOVES:
            by_design.append(row.scene_id)
        elif row.source == SOURCE_SHUT_TO_PLAYERS:
            shut.append(row.scene_id)
        else:
            unexplained.append(row.scene_id)
    # `chain=` counts, the rest are SCENE ID LISTS, and with one scene held
    # the old spelling `empty_by_design=1` read identically as "one scene" and
    # as "scene 1" (pf-adversary D9).  The brackets say which.
    lines.append(
        "%s chain_scenes=%d empty_until_you_step=[%s] shut_on_purpose=[%s] "
        "empty_unexplained=[%s]"
        % (
            CONSOLE_TOKEN,
            len(rows),
            _joined(by_design),
            _joined(shut),
            _joined(unexplained),
        )
    )
    lines.append(
        "%s NOTE this predicts what the SERVER composes, never what the "
        "client draws; an empty screen on a scene listed above with actors "
        "is a real finding for GT-192, not a preflight error" % CONSOLE_TOKEN
    )
    return tuple(lines)


def _joined(scene_ids: Any) -> str:
    return ",".join(str(s) for s in scene_ids)


def _ascii(text: Any) -> str:
    """cp874-safe, space-free, and one token: a console line is grepped."""
    flat = str(text).encode("ascii", "replace").decode("ascii")
    return "_".join(flat.split())


def main(argv: Any = None) -> int:
    """``python3 -m pirateforce_foundation.gm.warp_chain_preflight``.

    Optional positional scene ids run a custom chain; no arguments runs the
    whole reachable world in the owner's order.

    IT REFUSES BY NAME AND IT RETURNS A VERDICT, both because pf-adversary
    (D8) measured this entry point -- the only thing a human ever runs --
    doing neither.  A junk argument died with a bare ``int()`` traceback and
    printed no line at all, so the fail-closed-and-named promise the rest of
    this module keeps stopped at the front door.  And it returned 0 whether
    every scene resolved or every scene came back unknown, so nothing could
    gate on it and no wrapper could fail on it.

    Non-zero means: at least one scene in the chain is empty for a reason
    this tool could NOT explain.  A map held until the player steps, and a
    map shut on purpose, are explanations -- they do not make it non-zero.
    """
    import sys

    from ..legacy_bridge import load_legacy

    args = list(sys.argv[1:] if argv is None else argv)
    scenes = []
    for arg in args:
        try:
            scenes.append(int(arg))
        except (TypeError, ValueError):
            print(
                "%s REFUSED not a scene id: %s" % (CONSOLE_TOKEN, _ascii(arg))
            )
            return 2
    root = pathlib.Path(__file__).resolve().parents[3]
    try:
        legacy = load_legacy(root / str(LEGACY_RELATIVE_PATH))
    except Exception as error:  # noqa: BLE001 - named, never a traceback
        print(
            "%s REFUSED cannot load the legacy server: %s"
            % (CONSOLE_TOKEN, type(error).__name__)
        )
        return 2
    rows = preflight_chain(scenes or None, legacy=legacy)
    for line in render(rows):
        print(line)
    unexplained = [
        row.scene_id for row in rows
        if not row.on_arrival and row.source == SOURCE_NOTHING
    ]
    return 1 if unexplained else 0


if __name__ == "__main__":  # pragma: no cover - the entry point itself
    raise SystemExit(main())
