"""LANE-A (WORLD): the per-scene census composers this lane owns.

WHAT THIS FILE IS, IN ONE SENTENCE.  It is the end of a wall this lane spent
three rounds behind: ``world_population_bg0015`` has composed 81 actors for
Hell Volcano Island since round ``02k3w5`` and no caller existed, because the
only call site was in ``runtime.py`` and that is the chief's file.  chief built
the per-scene composer point in round ``73fhoc`` (answering this lane's
``CORE-REQUEST 20260829_1845``) and handed the next step here by name.  This
is that step.

    WHAT A PLAYER SEES BECAUSE OF THIS FILE, STATED HONESTLY AND FIRST.
    ~~Nothing today.  Scene 14 is not open to players~~ -- STALE, kept for
    the reasoning that follows it: scene 14 opened at login in LANE-A round
    `vvy6q7` (COO-DECISION 20260829_2342), so a character whose own stored
    row names scene 14 now logs straight in and this composer ships 81
    actors on arrival, exactly as this paragraph predicted it would the day
    the scene opened.  THE ADMISSION CHECK below is what makes that
    conditional rather than automatic - see it for why this module still
    REFUSES to compose the day someone shuts the door again, and it is the
    load-bearing part of the file, added after pf-adversary refuted the
    version without it.

    AN EARLIER DRAFT OF THIS MODULE SAID "the reason is one key" AND THAT WAS
    FALSE, MEASURED.  ``world_scene_entry.resolve_entry`` refuses scene 14
    only on its ``via_login=True`` path; called with ``via_login=False`` it
    resolves scene 14 today, and LANE-GM's ``CORE-REQUEST-GM-038``
    (``notes_to_chief/20260829_1925_...``) is an open request to chief for
    exactly such a login-path call site, for a different scene.  pf-adversary
    simulated that request landing - one lambda, registry file untouched - and
    measured 81 actors reaching a real player with the registry key still
    reading false and this lane's own door-shut test still green.  There were
    two keys, and the second was in another lane's pending letter.  THE
    ADMISSION CHECK below is what makes the registry key the only one again.

THE ADMISSION CHECK, AND WHY IT IS HERE RATHER THAN IN A TEST.  A composer
asks, on every call, whether the scene it is about to populate is one this
lane has declared open to players, and DECLINES if it is not.  The call site
hands this module ``scene_entry_registry`` precisely so a composer can consult
the pin instead of guessing, and declining is a first-class answer there: the
call site latches the census as sent-nothing with a named event
(``world_census_lane_composer_declined_scene_<id>``), which is byte-identical
in outcome to the ``skipped_scene_<id>_not_home`` branch this replaced.

    So the property is now structural rather than circumstantial: no route
    into scene 14 - a login, a ``via_login=False`` call site that does not
    exist yet, a direct call to this module's own factory - ships this
    roster while the registry says the scene is shut.  One boolean in
    ``scenarios/world_scene_registry_001.json`` is the whole gate, and
    ``tests/test_lane_a_scene_census.py`` drives the refusal rather than
    reading the boolean back.

HOW A SCENE GETS ADDED.  Two tables, and a scene needs a row in BOTH: a source
in ``world_scene_travel.CENSUS_SOURCES`` (the seam's own table, which decides
what composes the roster) and a console reader in ``_CONSOLE_LINES_OF`` below
(the lane's evidence choice, which decides what an attended round can grep).
An earlier draft claimed the answer lived in exactly one place and not here;
that was wrong, and the second table is a gate rather than a formality - a
census nobody can grep is a census nobody can grade.  A scene in one table and
not the other is SKIPPED AND SAID SO, loudly, at import
(``LANE_A_CENSUS_SKIPPED``): silence there is the same defect in mirror image
as the one round 80x5ba existed to fix.

WHY IT DELEGATES INSTEAD OF COMPOSING.  ``world_population_handoff`` already
resolves scene -> composer, caps a caller's count against the roster size,
reads membership with the composer's own reader, and carries the
``__post_init__`` that refuses a handoff disagreeing with its own generation.
Re-deriving any of that here would be a second implementation of a module
whose whole reason for existing is that there was one.  This file is an
adapter: seam ``SceneHandoff`` in, ``lane_hooks.SceneCensusResult`` out.

WHICH SEAM ENTRY POINT, AND WHY THE STRICT ONE.  ``handoff_for_arrival``, not
``handoff_on_crossing``.  The seam offers the never-raising variant for frame
paths that have no ``except`` around them; this composer is called from inside
runtime.py's own fail-closed net, which turns a raise into
``world_census_lane_composer_refused_<Type>`` and sends no frame.  That is
strictly more informative than the never-raising variant, which would convert
a composition crash into ``..._declined_scene_14`` - a crash silently
relabelled as a lane decision.  Pinned by a test, because pf-adversary
measured that swapping the two entry points changed nothing any test could
see.

SCENES 1 AND 2 ARE NOT REGISTERED, AND THAT IS BELT AND BRACES.  The call site
reserves them structurally (its ``elif`` cannot be reached for scene 1, and
scene 2's dedicated branch sits above it), so a composer registered for either
could never fire.  This module filters them out anyway, and the filter is
driven by a test that gives scene 1 a console reader and checks it stays out -
without that, the filter is dead code that any refactor could drop unnoticed.

THE CHOOSENPC RESPONDER GATE (COO-DECISION 20260830_0818).  ``membership``
(see ``SceneCensusResult.membership``'s own docstring) defaults to ``None``
-- the composer says nothing, and the three server-side fields stay in
their documented safe state.  ``_membership_if_answerable`` below is the one
place that ever supplies something else: it hands back the seam's own
``handoff.membership_reset`` ONLY when
``lane_hooks.scene_choose_npc_responder(scene_id)`` names a module AND
``lane_hooks.module_production_allowed`` says that module is allowed --
the same option-(b) gate every other direct-call ``lane_hooks`` consumer in
this project already reads, not a bespoke flag invented for this file.
``lane_hooks/lane_a_choose_npc_scene14.py`` is that responder for scene 14.
~~its own docstring is why its ``production_allowed`` is ``False`` today:
pf-adversary (R235 D2) measured that arming real membership for this scene
with no runtime.py guard in front of the frozen ChooseNPC handler is a
GUARANTEED ``KeyError`` on the first click, not merely a risk when no
responder exists.  So this gate does not turn on the moment a responder
file exists on disk -- it turns on the moment that file is ALSO trusted
(``production_allowed = True``), which this round leaves as the one-line
follow-up named in the CORE-REQUEST, not as work done here.  Until then this
composer's own behavior for scene 14 is unchanged from before this round:
``membership`` stays ``None`` and the caller's existing withhold-equivalent
(fields never written) stands, exactly as R235 left it.~~ FLIPPED, LANE-A
round `n8fq3w`: the runtime.py guard R235 D2 required landed first (chief,
round `hd6tac`/R237), and that responder module's own ``production_allowed``
is now ``True``.  So ``_membership_if_answerable`` below now returns real
membership for scene 14, and this composer's ``membership`` field is armed
on every arrival -- see that responder module's own docstring for what a
player sees because of the flip and the two gaps it ships with, pinned
rather than fixed.

THE ONE THING STILL IN THE WAY (defect D3, this lane's debt).
``player_wire``'s faction-1 serializer refuses any ``scene_id`` outside
``(1, 2)``, because the byte shape was only ever proven at those two.  So a
login into scene 14 emits no ``PLAYER_FACTION`` frame, and ``HYP-PF-027``
measured that hostility renders from a faction PAIR - on the one ticket
(``GT-134``) whose question is whether living things appear.  This file does
NOT widen that guard: doing so ships a wire shape nobody has measured, which
is the decision ``COO-DECISION 20260828_2345`` required an ask for when LANE-B
faced its own version of it.  The ask, with this round's driven evidence and a
proposed patch, is ``pf_bridge/notes_to_chief/20260829_2240_LANE-A-ASK-COO-
scene-14-door-has-one-blocker-left.md``.
"""
from __future__ import annotations

import sys
from typing import Any

from .. import lane_hooks
from .. import mob_census_hostility
from .. import world_population_bg0015
from .. import world_population_handoff
from .. import world_scene_travel

# The gate every lane_hooks module is held to.  True means "shippable, no
# scenario flag": this lane's charter forbids a flag-gated lane, and what
# keeps that honest is the admission check below, not a scenario file.
production_allowed = True

# The two the runtime keeps for its own branches.  Filtered here as well as
# there - see the module docstring.
RESERVED_BY_RUNTIME_BRANCHES = (
    world_scene_travel.CENSUS_SCENE_ID,
    world_scene_travel.PRISON_EXILE_SCENE_ID,
)

# Seam source name -> the lane's console evidence for that scene, read from
# the generation the seam ALREADY built.  Deliberately not
# ``world_population_bg0015.census_console_lines``, whose contract is to build
# a generation of its own: calling it here would compose the roster a second
# time and print numbers from a different object than the one on the wire.
_CONSOLE_LINES_OF = {
    "bg0015_roster": lambda generation: (
        (world_population_bg0015.census_console_line(generation),)
        + world_population_bg0015.actor_lines(generation)
        + world_population_bg0015.unresolved_lines()
    ),
}


def skipped_scenes() -> tuple[tuple[int, str, str], ...]:
    """(scene id, seam source, reason) for every scene this lane does NOT take.

    A scene the seam can compose a roster for and this module does not
    register is a decision, and a decision that looks identical to an
    oversight IS an oversight.  Reported here, printed at import, and pinned
    by a test - pf-adversary measured the version that dropped such a scene in
    total silence, with nothing red and no line anywhere.
    """
    skipped = []
    for scene_id, source in sorted(world_scene_travel.CENSUS_SOURCES.items()):
        if scene_id in RESERVED_BY_RUNTIME_BRANCHES:
            skipped.append(
                (scene_id, source, "reserved_by_a_runtime_branch"))
        elif source not in _CONSOLE_LINES_OF:
            skipped.append(
                (scene_id, source, "no_console_reader_in_this_lane_file"))
    return tuple(skipped)


def scenes_this_lane_composes_for() -> tuple[int, ...]:
    """Scene ids this module registers a composer for, in ascending order.

    A scene qualifies when the seam names a roster source for it, the runtime
    does not reserve it, and this file can print evidence for it.  Everything
    that does not qualify is in ``skipped_scenes()`` with its reason.
    """
    reserved_or_unreadable = {
        scene_id for scene_id, _source, _reason in skipped_scenes()
    }
    return tuple(sorted(
        scene_id for scene_id in world_scene_travel.CENSUS_SOURCES
        if scene_id not in reserved_or_unreadable
    ))


def scene_is_open_to_players(scene_id: int, registry: Any = None) -> bool:
    """Has this lane declared ``scene_id`` open for a player to be in?

    THE ADMISSION CHECK.  Read the module docstring before changing this: it
    is the reason a ``via_login=False`` call site landing in someone else's
    round cannot ship this roster behind this lane's back.

    Fail-closed in every direction that is not an explicit yes: a scene not in
    the registry, a registry that will not load, a row whose key is false, and
    any error reading it all answer False.  Refusing to populate a scene is
    always safe - it is what every boot before this file did.
    """
    try:
        destination = world_scene_travel.destination(scene_id, registry)
    except Exception:  # noqa: BLE001 - fail-closed, see the docstring
        return False
    return bool(getattr(destination, "login_entry_allowed", False))


def _hostility_lines(scene_id: int, generation: Any) -> tuple[str, ...]:
    """The hostility-coverage line every other census branch prints.

    ADDED round ucaybn after pf-adversary measured its ABSENCE here (D10):
    the scene-14 census printed 93 lines and not one of them was this one.
    ``mob_census_hostility.describe_census_hostility``'s own docstring says
    it is "printed UNCONDITIONALLY by a wiring call site, never inside an
    ``if``", because "no line at all" is the state ``GT-084`` already
    misread once.  The bg0002 branch prints it (LANE-B CORE-REQUEST
    20260829_1600); the lane branch in ``runtime.py`` does not, and that
    branch is chief's - so this lane prints it for its own scene, from the
    identities of the generation that is actually going out.

    ``unbacked=none`` is the expected answer for scene 14 and is the point:
    none of its 81 actors carries a faction bit, and a line SAYING so is
    what an attended round can grade.  A missing line is what it cannot.

    It cannot take the census down - a reporter that raised here would turn
    a composed roster into a refusal - so a failure becomes a line instead.
    """
    try:
        return tuple(
            str(line)
            for line in mob_census_hostility.describe_census_hostility(
                scene_id, generation.actor_identities,
            )
        )
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as failure:  # noqa: BLE001 - see the docstring
        return (
            "WORLD_CENSUS_HOSTILITY unreportable reason="
            + type(failure).__name__,
        )


def _membership_if_answerable(scene_id: int, handoff: Any) -> Any | None:
    """The seam's own membership, handed back ONLY if a registered,
    production-allowed ChooseNPC responder exists for ``scene_id``.

    See "THE CHOOSENPC RESPONDER GATE" in this module's own docstring for
    why ``module_production_allowed`` -- not merely a registration -- is the
    condition, and why that is a safety gate rather than an oversight.
    ``None`` (the everyday answer while no such responder is both
    registered and allowed) means the caller's three membership fields stay
    exactly as untouched as they were before this function existed.
    """
    responder = lane_hooks.scene_choose_npc_responder(scene_id)
    if responder is None:
        return None
    if not lane_hooks.module_production_allowed(responder.module):
        return None
    return handoff.membership_reset


def _compose_for_scene(scene_id: int):
    """Build the composer closure for one scene.

    A factory rather than a loop body so that ``scene_id`` is bound per
    composer.  ``runtime.py`` passes ``scene_id`` explicitly today, so a
    late-binding closure would still compose the right scene on the
    production path - this is about the direct callers (this lane's own
    tests, and any future non-runtime caller), not about that path.
    """

    def compose(
        *,
        legacy: Any,
        anchor: Any,
        scene_id: int = scene_id,
        scene_entry_registry: Any = None,
        **_ignored: Any,
    ) -> lane_hooks.SceneCensusResult | None:
        if not scene_is_open_to_players(scene_id, scene_entry_registry):
            # THE ADMISSION CHECK.  Decline, which the call site latches with
            # a named event and no frame - the same outcome the not-home skip
            # produced before this file existed.
            return None
        handoff = world_population_handoff.handoff_for_arrival(
            legacy, scene_id, anchor,
        )
        if handoff.kind != world_population_handoff.KIND_CENSUS:
            # CLEAR or UNAVAILABLE for a scene this module only registered
            # BECAUSE it has a roster means the seam and this file disagree
            # about the world.  Declining is the honest answer: no clear frame
            # the arrival path never asked for, and no census either.
            return None
        source = world_scene_travel.CENSUS_SOURCES[scene_id]
        console_lines = (
            (world_population_handoff.handoff_console_line(handoff),)
            + tuple(_CONSOLE_LINES_OF[source](handoff.generation))
            + _hostility_lines(scene_id, handoff.generation)
        )
        return lane_hooks.SceneCensusResult(
            actor_count=handoff.actor_count,
            pc=handoff.pc,
            frame=handoff.frame,
            console_lines=console_lines,
            initial_reapply_ms=handoff.reapply_ms,
            membership=_membership_if_answerable(scene_id, handoff),
        )

    return compose


def _register_all() -> None:
    """Register one composer per qualifying scene, and name every skip.

    A function rather than a bare module-level loop: an earlier draft ended
    with ``del _scene_id``, which had never run with an empty scene list and
    raised ``NameError`` at import the moment one table row changed - killing
    the module with a message naming a loop variable instead of the problem
    (pf-adversary, round ga91m5-r2).
    """
    for scene_id, source, reason in skipped_scenes():
        print(
            lane_hooks.console_safe(
                f"LANE_A_CENSUS_SKIPPED scene={scene_id} source={source} "
                f"reason={reason}"
            ),
            file=sys.stderr,
        )
    for scene_id in scenes_this_lane_composes_for():
        lane_hooks.census_composer(scene_id)(_compose_for_scene(scene_id))


_register_all()
