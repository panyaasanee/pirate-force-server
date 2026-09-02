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

TWO KINDS OF NUMBER, SAID OUT LOUD.  Eleven of the thirteen rows are obtained
by calling the very composer the runtime calls and counting the bytes that
come back.  Scenes 1 and 2 have no composer: their rosters ship from arms
inside ``runtime.py``, a file this lane may not touch, so those two rows are a
RECONSTRUCTION of chief's call.  Both kinds used to print identically, which
left a tester with no way to know which number to doubt when the screen
disagreed -- pf-adversary's closing question on the round that shipped this
module.  Every row now carries ``route=``, the summary lists the reconstructed
scenes as ``mirrored_not_measured``, and the AST gates in the test file turn a
drift in either call site red instead of silent.  Those two gates are NOT the
same strength and the console does not pretend they are: scene 2's pins the
number (no positional count, no ``actor_count`` keyword, therefore the
default), while scene 1's can only pin the SHAPE of the branch its count comes
from, and neither of them says anything about the anchor the runtime composes
at.  The legend names both open caveats rather than claiming they are closed.

AND THE LAST MAP OF THE CHAIN NOW PRINTS ITS NUMBER.  The owner's list closes
on scene 1, which is judged only after one step, and the count for that step
was being computed into ``actor_count`` and dropped by ``render`` -- the same
defect as pf-adversary D4 (a field computed with care and shown to nobody),
one field over.  ``actors_after_one_step`` is on every line now, ``n/a``
wherever this tool predicts nothing, never ``0``.
"""

from __future__ import annotations

import pathlib
import sys
from dataclasses import dataclass
from typing import Any

# THESE TWO CONSTANTS LIVE ABOVE THE PACKAGE IMPORTS ON PURPOSE, and the
# stderr line under them is the reason.  chief's ask (a) of `pf_bridge/
# notes_to_chief/20260902_1712_CHIEF-TO-LANE-GM-gt192-debt-paid-all-five-
# proposals-landed.md`: the PRECONDITION is stdout line 1 and the tester
# still meets it at roughly line 29, because importing the package below
# registers the lane hooks and writes 28 lines to STDERR first -- both
# streams land in one console and stderr gets there first.  Printed HERE it
# is the first line her eye actually reaches.  Guarded on `__main__` so an
# importer (every test in this repo, and any future caller) never sees it,
# and DUPLICATED rather than moved: stdout keeps its line 1, so a redirected
# `*> file` capture is byte-for-byte what it was.

# Every line this module prints starts with this, for the same reason every
# other console token in this lane does: a tester greps for it, and a
# diagnostic that cannot be found is a diagnostic that was not written.
CONSOLE_TOKEN = "GM_WARP_PREFLIGHT"

# `runtime.py:993`.  Printed with every run, because a boot that fails this
# ships no census on any map and would otherwise read as thirteen bugs.
BOOT_PRECONDITION = (
    "census ships ONLY on a boot with no scenario/lane object AND "
    "second_password_mode=required (runtime.py:993); otherwise every map "
    "below is empty and that is the boot, not a bug"
)

if __name__ == "__main__":  # pragma: no cover - the script entry only
    if not __package__:
        # Run BY PATH (`python src/.../warp_chain_preflight.py`) the relative
        # imports below cannot resolve, and the line above would otherwise
        # report a confident precondition for a module that is about to die of
        # ImportError two lines later (pf-adversary, round `et2ux4`, D10).
        # Refuse by name instead, the way `main()` refuses a junk argument.
        print(
            "%s REFUSED run this as a module: python -m "
            "pirateforce_foundation.gm.warp_chain_preflight" % CONSOLE_TOKEN,
            file=sys.stderr,
        )
        raise SystemExit(2)
    print(
        "%s PRECONDITION %s" % (CONSOLE_TOKEN, BOOT_PRECONDITION),
        file=sys.stderr,
    )

from .. import (
    lane_hooks,
    world_population,
    world_population_bg0002,
    world_population_handoff,
    world_scene_travel,
)
from . import scene_catalog
from .warp_executor import warp_no_coords_live_target

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

# HOW the number under it was obtained.  Not decoration: the counts on this
# console come from two different kinds of derivation and only one of them is
# the route the runtime actually walks.  pf-adversary closed the round that
# shipped this module with the question this field answers -- "when preflight
# and runtime disagree, what in the OUTPUT tells her which one to doubt" --
# and the honest answer that day was "nothing", for scenes 1 and 2.
#
# `production_composer`: the tool called the very seam the runtime calls
# (`composer.compose`) and counted the bytes that came back.  A disagreement
# here means the world changed between the two runs, not that the tool guessed.
#
# `mirrored_runtime_arm`: scenes 1 and 2 have NO composer.  Their rosters ship
# from arms inside `runtime.py`, which this lane may not touch and may not
# import a call site from, so the tool RECONSTRUCTS the call chief's file
# makes.  A reconstruction can drift from its original; the AST gates in
# `tests/test_gm_warp_chain_preflight.py` turn that drift red instead of
# silent, but they cannot make the reconstruction into the real thing.
ROUTE_PRODUCTION_COMPOSER = "production_composer"
ROUTE_MIRRORED_RUNTIME_ARM = "mirrored_runtime_arm"
ROUTE_NONE = "none"

# Printed once per run, under PRECONDITION.  A tester who sees two rows
# disagree with her screen needs to know which of them this tool derived and
# which it copied.
ROUTE_LEGEND = (
    "production_composer=this tool called the composer the runtime calls and "
    "counted the bytes it queued; mirrored_runtime_arm=scenes 1 and 2 have no "
    "composer, so this tool REBUILDS runtime.py's own call and its number is "
    "only as true as that reconstruction; none=no arm was consulted at all, "
    "the why= on that row says which of the four reasons; scene 1 carries TWO "
    "caveats no gate closes: a boot with --world-census-actors selects "
    "another rung for that scene alone, and the runtime composes it at the "
    "position you STEPPED TO while this tool composes it at the pinned spawn "
    "(measured: the count does not move with the anchor today, only the "
    "order)"
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
    route: str
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
         note: str, route: str = ROUTE_NONE) -> ScenePreflight:
    return ScenePreflight(
        scene_id=scene_id,
        gm_name=_gm_name(scene_id),
        source=source,
        route=route,
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
                route=ROUTE_MIRRORED_RUNTIME_ARM,
            )
        return _row(
            scene_id, SOURCE_RUNTIME_BG0002_ARM, "runtime.py", count, True,
            "ships from the runtime's own arm, not from lane_hooks; the "
            "everyday arrival seam reports clear/0 for this scene",
            route=ROUTE_MIRRORED_RUNTIME_ARM,
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
            # THE RUNTIME'S OWN EXPRESSION, not a lookalike.  `runtime.py`
            # takes the count for this arm from `census_count_for_dispatch()`
            # on the flagless boot GT-192 asks for; this branch used to pass
            # `effective_actor_count()` with a `count_source` hand-picked
            # beside it.
            #
            # RETRACTION, WRITTEN WHERE THE CLAIM WAS.  The first version of
            # this comment said the two spellings recorded DIFFERENT reasons
            # and that the difference would start moving bytes the day a
            # client ceiling was measured.  BOTH HALVES WERE FALSE, and
            # pf-adversary caught it by reading twenty lines above the call
            # being mirrored: `build_world_population` (world_population.py,
            # the `count < CENSUS_COUNT and count == len(available)` branch)
            # OVERWRITES whatever `count_source` a caller passes with
            # `identity_resolved`.  Swept every legal ceiling
            # (`None` plus 1..115, 116 builds of each spelling): the two agree
            # on bytes, on wire count, and on the recorded reason at EVERY
            # value.  There is no day when it starts to matter, and this
            # module never reads `count_source` at all -- it takes
            # `wire_actor_count` and drops the generation.
            #
            # SO THIS CHANGE IS A NO-OP, and it stays for the only reason that
            # survives measurement: a mirror should copy the EXPRESSION its
            # original evaluates, so that the day chief's flagless rung
            # changes, this branch changes with it instead of agreeing with it
            # by coincidence.  That is a claim about tomorrow, not a bug fixed
            # today, and it is worth exactly what the AST gate below is worth.
            count_for_dispatch, count_source = (
                world_population.census_count_for_dispatch()
            )
            generation = world_population.build_world_population(
                legacy, anchor, count_for_dispatch,
                scene_id=scene_id,
                count_source=count_source,
            )
            count = world_population.wire_actor_count(generation)
        except Exception as error:  # noqa: BLE001
            return _row(
                scene_id, SOURCE_NOTHING, "runtime.py", None, False,
                "the home arm refused: %s" % type(error).__name__,
                route=ROUTE_MIRRORED_RUNTIME_ARM,
            )
        return _row(
            scene_id, SOURCE_HELD_UNTIL_THE_PLAYER_MOVES,
            "runtime.py", count, False,
            "EMPTY ON ARRIVAL BY DESIGN (KA1A-AMENDMENT 20260901_1120); "
            "take ONE STEP and the census follows",
            route=ROUTE_MIRRORED_RUNTIME_ARM,
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
                route=ROUTE_PRODUCTION_COMPOSER,
            )
        return _row(
            scene_id, SOURCE_NOTHING, composer.module, None, False,
            "the composer raised: %s -- the runtime would latch "
            "world_census_refused and silence later maps too" % outcome,
            route=ROUTE_PRODUCTION_COMPOSER,
        )

    return _row(
        scene_id, SOURCE_LANE_COMPOSER, composer.module, count, True,
        "composed by the registered lane hook at this scene's pinned spawn",
        route=ROUTE_PRODUCTION_COMPOSER,
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
    lines = [
        "%s PRECONDITION %s" % (CONSOLE_TOKEN, BOOT_PRECONDITION),
        "%s ROUTE %s" % (CONSOLE_TOKEN, ROUTE_LEGEND),
    ]
    by_design = []
    shut = []
    unexplained = []
    mirrored = []
    for row in rows:
        lines.append(
            "%s scene=%d actors_on_arrival=%s actors_after_one_step=%s "
            "source=%s route=%s name=%s why=%s"
            % (
                CONSOLE_TOKEN,
                row.scene_id,
                _on_arrival(row),
                _after_one_step(row),
                row.source,
                row.route,
                _ascii(row.gm_name),
                _ascii(row.note),
            )
        )
        if row.route == ROUTE_MIRRORED_RUNTIME_ARM:
            mirrored.append(row.scene_id)
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
        "empty_unexplained=[%s] mirrored_not_measured=[%s]"
        % (
            CONSOLE_TOKEN,
            len(rows),
            _joined(by_design),
            _joined(shut),
            _joined(unexplained),
            _joined(mirrored),
        )
    )
    # chief's ask (b) of `pf_bridge/notes_to_chief/20260902_1712_CHIEF-TO-
    # LANE-GM-gt192-debt-paid-all-five-proposals-landed.md`: this warning
    # lived in this module's DOCSTRING, which a tester at a console does not
    # open.  Her console during `GT-192` prints `LANE_A_CENSUS_SKIPPED
    # scene=2` -- correctly, that scene has no lane composer -- and nothing
    # on her screen said this is NOT a licence for map 2 to come up empty.
    #
    # It rides the EXISTING note rather than a line of its own, for two
    # reasons that are both about not breaking what already works: `render`
    # ships exactly four framing lines and this module's test file asserts
    # each appears exactly once, and a fifth line would have to be printed
    # even for a chain that contains no mirrored scene at all to keep that
    # count honest.  The map number and its count are read off the ROW, never
    # typed in here, so they cannot drift from the table above.
    mirrored_arm = [
        (row.scene_id, _on_arrival(row))
        for row in rows
        if row.source == SOURCE_RUNTIME_BG0002_ARM
    ]
    skipped_clause = "".join(
        "; the LANE_A_CENSUS_SKIPPED line your server console prints for map "
        "%d is NOT a licence for an empty map there -- its %s actors ship "
        "from the runtime's own arm, not from a lane hook" % (scene_id, count)
        for scene_id, count in mirrored_arm
    )
    lines.append(
        "%s NOTE this predicts what the SERVER composes, never what the "
        "client draws; an empty screen on a scene listed above with actors "
        "is a real finding for GT-192, not a preflight error%s"
        % (CONSOLE_TOKEN, skipped_clause)
    )
    return tuple(lines)


def _on_arrival(row: Any) -> str:
    """What she sees when she lands.  ``0`` only where ``0`` is a measurement.

    THE SAME DISEASE THIS ROUND DIAGNOSED ONE FIELD OVER (pf-adversary D8).
    ``render`` printed ``0`` for every row that was not ``on_arrival``, which
    swept up rows where nothing is known at all: a ``/warp`` REFUSED BY NAME,
    a registry that pins no spawn, a scene no composer claims.  Nobody ever
    lands on those, so ``0`` there is a fabricated number, and
    ``ScenePreflight``'s own docstring forbids exactly that -- ``never 0
    standing in for "do not know"`` -- a promise the dataclass kept and the
    console line broke.

    ``0`` stays for the two rows where it IS the prediction: a map held until
    she moves, and a map shut on purpose.  Both are maps she reaches and both
    show her an empty screen.
    """
    if row.on_arrival:
        return "?" if row.actor_count is None else str(row.actor_count)
    if row.source in (SOURCE_HELD_UNTIL_THE_PLAYER_MOVES,
                      SOURCE_SHUT_TO_PLAYERS):
        return "0"
    return "n/a"


def _after_one_step(row: Any) -> str:
    """The number a tester grades on the ONE map that is empty when she lands.

    THIS FIELD EXISTS BECAUSE THE NUMBER WAS BEING COMPUTED AND SHOWN TO
    NOBODY.  ``preflight_for`` has always put the home arm's wire count in
    ``actor_count`` for scene 1, and a test named
    ``test_it_still_says_what_she_gets_after_the_step`` has always asserted it
    is there -- but ``render`` printed ``actors_on_arrival=0`` for that row and
    dropped the count on the floor, so the last map of the owner's own chain,
    the one ``COO-DECISION 2026-09-02T05:44+07:00`` says to judge only after
    one step, reached her console with no number to judge against.  That is
    pf-adversary D4 (a field computed with care and never printed) happening a
    second time on a different field, in a module that had already been fixed
    for it once.

    ``n/a`` IS NOT ZERO.  Every other row has already shipped its census on
    arrival, and this tool has measured nothing about what a step does there;
    printing a number would be an invention and printing ``0`` would read as a
    bug.  ``n/a`` says: no second prediction is made for this row.
    """
    if row.source != SOURCE_HELD_UNTIL_THE_PLAYER_MOVES:
        return "n/a"
    if row.actor_count is None:
        # UNREACHABLE THROUGH `preflight_for` TODAY and kept as an explicit
        # answer rather than deleted: the home arm either yields a count or
        # returns a `nothing` row, so this branch has no driver.  pf-adversary
        # found it dead (D10).  It is not `0` for the same reason nothing else
        # here is.
        return "?"
    return str(row.actor_count)


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
