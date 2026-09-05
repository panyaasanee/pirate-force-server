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
    roster while the registry says the scene is shut.  ~~One boolean in
    ``scenarios/world_scene_registry_001.json`` is the whole gate~~, and
    ``tests/test_lane_a_scene_census.py`` drives the refusal rather than
    reading the boolean back.

    THE STRUCK SENTENCE WAS TRUE FOR ONE ARM AND IS NOW FALSE FOR THREE, and
    pf-adversary measured it still standing here a round after it stopped
    being true, so it is corrected rather than quietly left.  It is still
    exactly right for scene 14 and for every scene whose only admission is
    the registry pin.  For THREE scenes it is not the whole gate:

        126  the GM lane's sanctioned single-use predicate (arm 2, round
             ``4uztfj``) - its own table is the gate, and revoking it
             darkens the scene again
        304  an owner-decreed arrival point plus a live GM warp (arm 3,
        305  round ``yob0a2``) - the decree is the gate, and it is a
             PANYA/COO artifact rather than a boolean any lane may flip

    Each arm names its own gate in its own docstring, and each is driven by
    a test that revokes that gate rather than reading it back.  What has NOT
    changed is the direction of every arm: all three fail closed, and none
    of them opens a LOGIN door - ``login_entry_allowed`` is still false for
    all three of those scenes.

HOW A SCENE GETS ADDED.  ~~Two tables, and a scene needs a row in BOTH~~ --
SEVEN REGISTRATIONS, counted round ``yob0a2`` by adding scene 304 and reading
the red tests one at a time (pf-adversary: the round found five of the seven
only BECAUSE tests went red, and two more were still missing when it first
committed).  The two this file has always named come first because they are
the ones this module reads:

    1. ``world_scene_travel.CENSUS_SOURCES`` - the seam's own table, which
       decides what composes the roster
    2. ``_CONSOLE_LINES_OF`` below - the lane's evidence choice, which
       decides what an attended round can grep
    3. ``world_population_handoff.ROSTER_COMPOSERS`` - without it the seam
       answers CLEAR and this composer declines with no frame and no reason
       anyone can tell from the one it prints for a shut door
    4. ``gm/identity_registry_census`` - the identity module's own registry
    5. ``mob_scene_recompose.ACKNOWLEDGED_WITHOUT_COMPOSER`` (or a real
       recompose composer) - LANE-B's tripwire, whose stake is the
       one-entry world wipe; the entry must MEASURE that the scene has no
       combat roster, not assert it
    6. ``tests/test_world_census_level.py``'s ``WIRED_SCENES`` and
       ``CENSUS_SOURCE_COMPOSERS`` - the level splice's own two lists
    7. ``tools/pf_runtimeres_actor_entry_static.py`` + its report +
       ``tests/test_runtimeres_actor_entry_static.py`` - three copies of
       the actor-entry call-site counts, which a new composer moves by one

An earlier draft claimed the answer lived in exactly one place and not here;
that was wrong, and the second table is a gate rather than a formality - a
census nobody can grep is a census nobody can grade.  A scene in the first
table and not the second is SKIPPED AND SAID SO, loudly, at import
(``LANE_A_CENSUS_SKIPPED``): silence there is the same defect in mirror image
as the one round 80x5ba existed to fix.  Rows 3-7 have no such import-time
report; they are caught by tests, which is why this list exists rather than
the sentence it replaces.

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

EVERY COMPOSER'S RESULT NOW CARRIES LANE B'S ROSTER IDENTITIES TOO
(COO-DECISION 20260903_2247).  ``SceneCensusResult.actor_identities`` is
``field_mobs.roster_for_scene_id(scene_id)``'s identities, read through that
lane's own public reader in ``_field_mob_identities`` below -- never a
per-scene import of a table module lane B owns.  Lane B asked for this
because it cannot splice hostility onto scene 14's arrivals without knowing
which identities the census that scene actually sent carries, and it could
not answer that question itself without reaching across the lane boundary.
The field is on every scene this file composes for, not only scene 14: a
scene lane B has not mined a roster for (today, every scene but 1, 2 and 14)
answers ``()``, which is a real "nothing registered yet" and not a defect
this file owns.

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

from .. import field_mobs
from .. import lane_hooks
from .. import mob_census_hostility
from .. import world_population_bg0003
from .. import world_population_bg0004
from .. import world_population_bg0005
from .. import world_population_bg0006
from .. import world_population_bg0007
from .. import world_population_bg0008
from .. import world_population_bg0009
from .. import world_population_bg0010
from .. import world_population_bg0011
from .. import world_population_bg0015
from .. import world_population_bg1001
from .. import world_population_bg3001
from .. import world_population_bg3007
from .. import world_population_bg4001
from .. import world_population_handoff
from .. import world_scene_folder
from .. import world_scene_registry
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
    # ADDED round 2jdde8 (2026-08-30, LANE-A): the second table this scene
    # needs a row in, per "HOW A SCENE GETS ADDED" above.  Registered here
    # AND in ``world_scene_travel.CENSUS_SOURCES`` in the same commit, so
    # neither table can be true without the other for even one round - a
    # scene in one and not the other prints ``LANE_A_CENSUS_SKIPPED`` at
    # import (see ``skipped_scenes()``), and that is now testable rather
    # than trusted.  Scene 4's registry row stays ``login_entry_allowed:
    # false`` (COO-DECISION 2026-08-30T14:41+07:00), so THE ADMISSION CHECK
    # above declines every call this composer ever receives in production
    # today - registered, never fired, exactly as scene 14's own composer
    # sat for several rounds before COO-DECISION 20260829_2342 opened it.
    "bg0004_roster": lambda generation: (
        (world_population_bg0004.census_console_line(generation),)
        + world_population_bg0004.actor_lines(generation)
        + world_population_bg0004.unresolved_lines()
    ),
    # ADDED round c42axq (2026-08-31, LANE-A): the second table this scene
    # needs a row in, per "HOW A SCENE GETS ADDED" above.  Registered here
    # AND in ``world_scene_travel.CENSUS_SOURCES`` in the same commit, so
    # neither table can be true without the other for even one round.
    # Scene 10's registry row stays ``login_entry_allowed: false``, so THE
    # ADMISSION CHECK above declines every call this composer ever receives
    # in production today - registered, never fired, exactly as bg0004's
    # own composer sat for a round before a later round judged it ready.
    "bg0010_roster": lambda generation: (
        (world_population_bg0010.census_console_line(generation),)
        + world_population_bg0010.actor_lines(generation)
        + world_population_bg0010.unresolved_lines()
    ),
    # ADDED round l03cgh (2026-08-31, LANE-A): the second table this scene
    # needs a row in, per "HOW A SCENE GETS ADDED" above.  Registered here
    # AND in ``world_scene_travel.CENSUS_SOURCES`` in the same commit, so
    # neither table can be true without the other for even one round.
    # Unlike bg0004's and bg0010's own build/wire/open split across three
    # separate rounds, this round also flips scene 5's registry row in the
    # same pass (see ``scenarios/world_scene_registry_001.json``'s own
    # ``login_entry_allowed_because`` for the D1/D2/D3 check this round ran
    # against THIS scene) - so THE ADMISSION CHECK above now ADMITS calls
    # this composer receives in production.
    "bg0005_roster": lambda generation: (
        (world_population_bg0005.census_console_line(generation),)
        + world_population_bg0005.actor_lines(generation)
        + world_population_bg0005.unresolved_lines()
    ),
    # ADDED round fx0007 (2026-08-31, LANE-A): the second table this scene
    # needs a row in, per "HOW A SCENE GETS ADDED" above.  Registered here
    # AND in ``world_scene_travel.CENSUS_SOURCES`` in the same commit, so
    # neither table can be true without the other for even one round.  Same
    # compressed build+wire+open pass round ``l03cgh`` used for scene 5 -
    # this round also flips scene 6's registry row (see
    # ``scenarios/world_scene_registry_001.json``'s own
    # ``login_entry_allowed_because`` for the D1/D2/D3 check this round ran
    # against THIS scene) - so THE ADMISSION CHECK above now ADMITS calls
    # this composer receives in production.
    "bg0006_roster": lambda generation: (
        (world_population_bg0006.census_console_line(generation),)
        + world_population_bg0006.actor_lines(generation)
        + world_population_bg0006.unresolved_lines()
    ),
    # ADDED round p4wire (2026-08-31, LANE-A): the second table this scene
    # needs a row in, per "HOW A SCENE GETS ADDED" above.  Registered here
    # AND in ``world_scene_travel.CENSUS_SOURCES`` in the same commit, so
    # neither table can be true without the other for even one round.  Same
    # compressed build+wire+open pass rounds ``l03cgh``/``fx0007`` used for
    # scenes 5 and 6 - this round also flips scene 8's registry row (see
    # ``scenarios/world_scene_registry_001.json``'s own
    # ``login_entry_allowed_because`` for the D1/D2/D3 check this round ran
    # against THIS scene) - so THE ADMISSION CHECK above now ADMITS calls
    # this composer receives in production.
    "bg0008_roster": lambda generation: (
        (world_population_bg0008.census_console_line(generation),)
        + world_population_bg0008.actor_lines(generation)
        + world_population_bg0008.unresolved_lines()
    ),
    # ADDED round (this round, 2026-08-31, LANE-A): the second table this
    # scene needs a row in, per "HOW A SCENE GETS ADDED" above. Registered
    # here AND in ``world_scene_travel.CENSUS_SOURCES`` in the same commit,
    # so neither table can be true without the other for even one round.
    # Same compressed build+wire+open pass rounds ``l03cgh``/``fx0007``/
    # ``p4wire`` used for scenes 5, 6 and 8 - this round also flips scene
    # 3's registry row (see ``scenarios/world_scene_registry_001.json``'s
    # own ``login_entry_allowed_because`` for the D1/D2/D3 check this round
    # ran against THIS scene) - so THE ADMISSION CHECK above now ADMITS
    # calls this composer receives in production.
    "bg0003_roster": lambda generation: (
        (world_population_bg0003.census_console_line(generation),)
        + world_population_bg0003.actor_lines(generation)
        + world_population_bg0003.unresolved_lines()
    ),
    # ADDED round 78zayw (2026-08-31, LANE-A): the second table this scene
    # needs a row in, per "HOW A SCENE GETS ADDED" above. Registered here
    # AND in ``world_scene_travel.CENSUS_SOURCES`` in the same commit, so
    # neither table can be true without the other for even one round. Same
    # compressed build+wire+open pass rounds ``l03cgh``/``fx0007``/
    # ``p4wire``/``p7wm17`` used for scenes 5, 6, 8 and 3 - this round also
    # flips scene 7's registry row (see
    # ``scenarios/world_scene_registry_001.json``'s own
    # ``login_entry_allowed_because`` for the D1/D2/D3 check this round ran
    # against THIS scene) - so THE ADMISSION CHECK above now ADMITS calls
    # this composer receives in production.
    "bg0007_roster": lambda generation: (
        (world_population_bg0007.census_console_line(generation),)
        + world_population_bg0007.actor_lines(generation)
        + world_population_bg0007.unresolved_lines()
    ),
    # ADDED round ir0lpw (2026-08-31, LANE-A): the second table this scene
    # needs a row in, per "HOW A SCENE GETS ADDED" above. Registered here
    # AND in ``world_scene_travel.CENSUS_SOURCES`` in the same commit, so
    # neither table can be true without the other for even one round. Same
    # compressed build+wire+open pass rounds ``l03cgh``/``fx0007``/
    # ``p4wire``/``p7wm17``/``78zayw`` used for scenes 5, 6, 8, 3 and 7 -
    # this round also flips scene 9's registry row (see
    # ``scenarios/world_scene_registry_001.json``'s own
    # ``login_entry_allowed_because`` for the D1/D2/D3 check this round ran
    # against THIS scene) - so THE ADMISSION CHECK above now ADMITS calls
    # this composer receives in production.
    "bg0009_roster": lambda generation: (
        (world_population_bg0009.census_console_line(generation),)
        + world_population_bg0009.actor_lines(generation)
        + world_population_bg0009.unresolved_lines()
    ),
    # ADDED round 68mm02 (2026-08-31, LANE-A): the ninth door, same shape
    # as the scene-9 entry above.  Registered here AND in
    # ``world_scene_travel.CENSUS_SOURCES`` in the same commit, so neither
    # table can be true without the other for even one round.  Same
    # compressed build+wire+open pass rounds ``l03cgh``/``fx0007``/
    # ``p4wire``/``p7wm17``/``78zayw``/``ir0lpw`` used for scenes 5, 6, 8,
    # 3, 7 and 9 - this round also flips scene 11's registry row (see
    # ``scenarios/world_scene_registry_001.json``'s own
    # ``login_entry_allowed_because`` for the D1/D2/D3 check this round ran
    # against THIS scene) - so THE ADMISSION CHECK above now ADMITS calls
    # this composer receives in production.
    "bg0011_roster": lambda generation: (
        (world_population_bg0011.census_console_line(generation),)
        + world_population_bg0011.actor_lines(generation)
        + world_population_bg0011.unresolved_lines()
    ),
    # ADDED round 4uztfj (2026-09-02, LANE-A): scene 126, the ocean panel.
    # Registered here AND in ``world_scene_travel.CENSUS_SOURCES`` in the
    # same commit, so neither table can be true without the other for even
    # one round.  This scene's registry door stays SHUT (see that table's
    # own comment and ``scene_is_sanctioned_for_a_gm_entry`` below), so the
    # only arrival that reaches these lines today is a GM single-use entry.
    "bg3001_roster": lambda generation: (
        (world_population_bg3001.census_console_line(generation),)
        + world_population_bg3001.actor_lines(generation)
        + world_population_bg3001.unresolved_lines()
    ),
    # ADDED round yfbqmg (2026-09-01, LANE-A): the tenth and LAST door of
    # the original ten, same shape as the scene-11 entry above.  Registered
    # here AND in ``world_scene_travel.CENSUS_SOURCES`` in the same commit,
    # so neither table can be true without the other for even one round.
    # Same compressed build+wire+open pass rounds ``l03cgh``/``fx0007``/
    # ``p4wire``/``p7wm17``/``78zayw``/``ir0lpw``/``68mm02`` used for
    # scenes 5, 6, 8, 3, 7, 9 and 11 - this round also flips scene 130's
    # registry row (see ``scenarios/world_scene_registry_001.json``'s own
    # ``login_entry_allowed_because`` for the D1/D2/D3 check this round ran
    # against THIS scene) - so THE ADMISSION CHECK above now ADMITS calls
    # this composer receives in production.
    "bg4001_roster": lambda generation: (
        (world_population_bg4001.census_console_line(generation),)
        + world_population_bg4001.actor_lines(generation)
        + world_population_bg4001.unresolved_lines()
    ),
    # ADDED round vwekfq (2026-09-05, LANE-A): scene 17, the ship at sea.
    # Registered here AND in ``world_scene_travel.CENSUS_SOURCES`` in the
    # same commit, so neither table can be true without the other for even
    # one round.  This scene's registry door stays exactly as it was
    # (``login_entry_allowed: false``, guarding the ordinary LOGIN path
    # only - see ``world_scene_travel``'s own comment on
    # ``SHIP_AT_SEA_SCENE_ID``), so THE ADMISSION CHECK above declines
    # every call this composer receives in production today, the same
    # inert-until-opened shape scene 4's and scene 10's own rows carried.
    "bg1001_roster": lambda generation: (
        (world_population_bg1001.census_console_line(generation),)
        + world_population_bg1001.actor_lines(generation)
        + world_population_bg1001.unresolved_lines()
    ),
    # ADDED round yob0a2 (2026-09-05, LANE-A): scene 304 (Bg3007, "Dark Fog
    # Sea"), the first of the two seas COO-DECISION 20260905_1748 names as
    # the destinations of a crossing at scene 126's map edge.  Registered
    # here AND in ``world_scene_travel.CENSUS_SOURCES`` in the same commit,
    # so neither table can be true without the other for even one round.
    # UNLIKE scenes 4, 10 and 17, this one is NOT registered-but-inert: its
    # registry row still reads ``login_entry_allowed: false``, but round
    # n4vqxc's pin made a bare GM ``/warp 304`` land here live, and THE
    # THIRD ADMISSION ARM below (``scene_arrival_was_decreed_and_is_gm_
    # reachable``) admits exactly that session - so this composer answers in
    # production the day it lands, for a GM and for nobody else.
    "bg3007_roster": lambda generation: (
        (world_population_bg3007.census_console_line(generation),)
        + world_population_bg3007.actor_lines(generation)
        + world_population_bg3007.unresolved_lines()
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


def scene_is_sanctioned_for_a_gm_entry(
    scene_id: int, registry: Any = None
) -> bool:
    """Does the GM lane's OWN predicate say a session may be standing here?

    THE SECOND ADMISSION ARM, added round ``4uztfj`` (LANE-A) for scene 126.
    It asks ``gm/login_scene_admission.single_use_entry_is_admissible`` --
    the GM lane's own function, not a re-implementation of its rule -- which
    admits exactly a scene chief's letter sanctions AND whose only remaining
    blocker is the login bar ``CORE-REQUEST-GM-038`` bypasses for it.  One
    scene id qualifies today: 126.

    WHY THIS IS NOT A DOOR, SAID PLAINLY, BECAUSE IT LOOKS LIKE ONE.  This
    predicate gates what a session STANDING IN A SCENE is sent; it is asked
    by a composer the arrival path calls after the login has already put the
    character there.  It cannot move a character, cannot stage a login, and
    cannot make the ordinary login path admit anything: a session with no GM
    grant is still refused at ``resolve_entry`` with
    ``REFUSED_NOT_ALLOWED_AT_LOGIN`` and never reaches this code at all.
    ``login_entry_allowed`` for scene 126 is untouched by this round --
    ``COO-DECISION 20260829_1444`` wants an attended var2 test before any
    flip, and this arm is not that flip: it does not widen who may ENTER,
    only whether a GM who is already there is shown the scene's own cast
    instead of an empty ocean.

    Fail-closed in every direction, the same as the first arm: an import
    that is not there, a registry that will not load, a predicate that
    raises -- all answer False.

    WHAT IT COSTS, MEASURED THIS ROUND RATHER THAN ASSUMED CHEAP.  With no
    registry passed, the GM lane's predicate performs its OWN registry read
    (its docstring says so), and its two arms may each perform one -- so a
    click on scene 126 costs about 3.2 ms against about 1.0 ms for a scene
    the first arm admits, on this clone.  Two things keep that acceptable:
    the second arm is only reached for a scene the first one refused (one
    scene id today), and the production call sites hand this function the
    ``scene_entry_registry`` they were already given, which ~~both arms
    then share~~ THE FIRST TWO ARMS SHARE - amended round ``yob0a2``:
    the third arm's warp half takes no registry argument and loads the pin
    file itself, which its own docstring now states and times.  A click is human-paced; a census is not composed in a loop.
    """
    try:
        from ..gm import login_scene_admission
    except Exception:  # noqa: BLE001 - fail-closed, see the docstring
        return False
    try:
        # BOTH halves, and the first one is why this is not simply a call to
        # ``single_use_entry_is_admissible``: that function's own first arm
        # is PLAIN admission (a scene the registry already pins open), so
        # calling it alone would make this arm a duplicate of the first one
        # for every open scene and hide which arm actually admitted.  ANDing
        # it with the sanction lookup narrows this to what it claims to be:
        # a scene chief's letter names AND the GM lane itself would admit.
        # It can never be WIDER than the GM lane's own predicate.
        return bool(
            login_scene_admission.is_sanctioned_barred_scene(scene_id)
            and login_scene_admission.single_use_entry_is_admissible(
                scene_id, scene_registry=registry,
            )
        )
    except Exception:  # noqa: BLE001 - fail-closed, see the docstring
        return False


def scene_arrival_was_decreed_and_is_gm_reachable(
    scene_id: int, registry: Any = None
) -> bool:
    """Did the OWNER pin this scene's arrival point, and can a live GM warp
    actually land a session on it?

    THE THIRD ADMISSION ARM, added round ``yob0a2`` (LANE-A) for scene 304.
    BOTH halves are required and neither is this lane's own opinion:

    * ``destination(scene_id).has_decreed_arrival`` - the registry row
      carries a validated ``decreed_arrival`` block, which only a
      PANYA-DECISION or a COO-DECISION puts there (126 by
      ``20260905_1329``; 304 and 305 by ``20260905_1748``), and which
      ``world_scene_travel``'s own loader refuses unless the marker row,
      the scene it points back at, the spawn point and the heading all
      agree.
    * ``gm.warp_executor.warp_no_coords_live_target(scene_id)`` resolves -
      the GM lane's OWN gate for "a bare ``/warp <n>`` lands here live
      instead of staging the next login".  Not re-implemented here.

    WHY BOTH, AND WHY NOT SIMPLY "A LIVE WARP CAN REACH IT".  Measured at
    HEAD against the whole registry (19 rows): 16 scenes resolve a live
    warp, and every one of them except 126, 304 and 305 ALREADY has
    ``login_entry_allowed: true``, so the first arm admits it and a bare
    live-warp arm would add nothing for them.  What it WOULD add is a
    standing rule that any future row someone pins a spawn on becomes
    populatable without anyone deciding so - the shape rounds ``2jdde8``,
    ``c42axq`` and ``vwekfq`` deliberately avoided by leaving scenes 4, 10
    and 17 registered-but-inert until a round opened them on purpose.  The
    decree half is what keeps this arm to scenes a ruling already named.

    IT STANDS ASIDE FOR ANY SCENE THE GM LANE'S SANCTION TABLE GOVERNS,
    and this is the load-bearing half of the arm rather than a courtesy.
    pf-adversary (this round) measured what the first draft cost: with
    scene 126 in ``gm/login_scene_admission.SANCTIONED_BARRED_SCENES``, this
    arm answered True for it INDEPENDENTLY of the second arm, so revoking
    ``CORE-REQUEST-GM-038`` -- the GM lane's own on/off switch for that
    scene -- stopped darkening its census.  A lane may not quietly take
    another lane's revocation lever away, and "the test was amended to
    bless it" is not an answer.  So the first thing this arm asks is
    whether the GM lane governs the scene at all; if it does, this arm
    declines and the SECOND arm decides, exactly as it did before this
    round.  Scene 126 is that case today and its behaviour is byte-for-byte
    unchanged; 304 and 305 are in no sanction table, which is why they need
    this arm at all.

    WHY THIS IS NOT A DOOR, the same sentence the second arm carries and
    for the same reason: this predicate gates what a session ALREADY
    STANDING IN A SCENE is sent.  It cannot move a character, cannot stage
    a login, and cannot make the ordinary login path admit anything - a
    session with no GM grant is refused at ``resolve_entry`` with
    ``REFUSED_NOT_ALLOWED_AT_LOGIN`` and never reaches this code, and
    ``/warp`` itself is refused for a non-GM account by
    ``accounts.is_gm_account`` before any of this runs.
    ``login_entry_allowed`` for 126/304/305 is untouched by this round.

    [ASSUMPTION OF LANE A - AWAITING COO CONFIRMATION]  That "the owner
    decreed where you arrive" also means "you should see what is there" is
    this lane's reading, not a ruling anyone has written down; the round's
    letter puts it in front of the COO.  If the answer is no, deleting this
    function restores today's behaviour exactly - an empty ocean for a GM
    standing in 304 - and nothing else in the round depends on it.

    WHAT "GM-ONLY" DOES AND DOES NOT MEAN HERE, stated because the sentence
    above is easy to over-read.  This predicate asks about a SCENE, never
    about an account: it answers the same True for any session standing in
    scene 304, and the only reason that session is a GM today is that a GM
    ``/warp`` is the only route that reaches the scene at all.  The day
    chief wires the sea-edge crossing (``world_sea_edge_crossing``), an
    ORDINARY player who sails across scene 126's edge lands here and is sent
    this same cast.  That is the intended outcome and not a hole - but it is
    a consequence of this arm, so it is written down rather than discovered.

    WHICH REGISTRY EACH HALF READS, because they are not the same one and a
    reader should not have to find that out from a failing test.  The decree
    half reads the registry the CALLER passed (the production call sites
    hand this function the ``scene_entry_registry`` they were already
    given); the warp half asks ``warp_no_coords_live_target``, which takes
    no registry argument and reads the pin file itself.  The asymmetry can
    only NARROW admission, never widen it: both halves must say yes, and the
    half a caller controls is the one that can say no.  A caller-supplied
    registry with no row for the scene, or with the decree removed, shuts
    this arm even though the file on disk still has both.

    WHAT IT COSTS, measured in the same terms the second arm states rather
    than assumed cheap: ``warp_no_coords_live_target`` performs its OWN read
    of the pin file (it takes no registry argument), so a scene that reaches
    this arm pays one extra registry load on top of whatever the first two
    arms did - the same shape and the same order of magnitude as the second
    arm's own ~3.2ms.  Two things keep it acceptable: this arm is only
    reached for a scene BOTH earlier arms refused AND the GM lane does not
    govern (two scene ids today, 304 and 305), and a census is composed once
    per arrival, not in a loop.

    Fail-closed in every direction, the same as the other two arms: a
    registry that will not load, an import that is not there, a predicate
    that raises - all answer False.
    """
    try:
        from ..gm import login_scene_admission
        if login_scene_admission.is_sanctioned_barred_scene(scene_id):
            # The GM lane governs this scene: its own predicate is the
            # answer, and this arm must not override it.  See the docstring.
            return False
    except Exception:  # noqa: BLE001 - fail-closed, see the docstring
        # Cannot tell whether the GM lane governs it, so this arm may not
        # claim it either.
        return False
    try:
        destination = world_scene_travel.destination(scene_id, registry)
    except Exception:  # noqa: BLE001 - fail-closed, see the docstring
        return False
    if not getattr(destination, "has_decreed_arrival", False):
        return False
    try:
        from ..gm import warp_executor
    except Exception:  # noqa: BLE001 - fail-closed, see the docstring
        return False
    try:
        return warp_executor.warp_no_coords_live_target(scene_id) is not None
    except Exception:  # noqa: BLE001 - fail-closed, see the docstring
        return False


def scene_may_be_populated(scene_id: int, registry: Any = None) -> bool:
    """Any admission arm.  The question ``compose`` actually asks.

    Kept as its own function rather than an ``or`` inside the composer so
    that every arm is testable by name, and so a reader who greps for
    ``scene_is_open_to_players`` still finds the registry pin unchanged
    where it always was.  ORDER IS COST, NOT MEANING: the registry pin is
    the cheapest question and answers True for every scene this lane
    composes in production today, so the two GM arms are only reached for a
    scene it refused.
    """
    return (
        scene_is_open_to_players(scene_id, registry)
        or scene_is_sanctioned_for_a_gm_entry(scene_id, registry)
        or scene_arrival_was_decreed_and_is_gm_reachable(scene_id, registry)
    )


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


TOKEN_ACTOR_IDENTITIES_UNREPORTABLE = (
    "WORLD_CENSUS_ACTOR_IDENTITIES_UNREPORTABLE"
)


def _field_mob_identities(scene_id: int) -> tuple[tuple[int, ...], str | None]:
    """Lane B's hostile-mob identities for ``scene_id``, plus a console note.

    COO-DECISION 20260903_2247.  Goes through ``field_mobs.roster_for_scene_id``
    -- that lane's OWN public per-scene-id reader, already scene-agnostic and
    already answering ``()`` for a scene its registry does not address --
    rather than importing a per-scene table module (``field_mob_hostile_
    bg0015`` or any sibling) by name.  That keeps this file from growing one
    new import per scene lane B mines, the same shape ``_CONSOLE_LINES_OF``
    above already avoids for a different reason.

    Fail-closed like every other reporter in this module
    (``_hostility_lines`` is the sibling this mirrors): a failure here must
    become an empty identity list, never a refused census, because the
    census this scene actually sends does not depend on lane B's registry at
    all.  UNLIKE the first draft of this function (pf-adversary, round
    t8m3ab), a failure is not silently identical to "no roster registered":
    it also returns a console note, so a reader of an attended round's
    capture can tell "this scene has no field-mob table yet" from "the
    registry blew up and this lane swallowed it" -- the same distinction
    ``_hostility_lines`` already makes for its own failure, and the one this
    function's own first draft did not.
    """
    try:
        identities = tuple(
            mob.actor_identity
            for mob in field_mobs.roster_for_scene_id(scene_id)
        )
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as failure:  # noqa: BLE001 - see the docstring
        return (), "%s reason=%s" % (
            TOKEN_ACTOR_IDENTITIES_UNREPORTABLE, type(failure).__name__,
        )
    return identities, None


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


def _world_registry_line(scene_id: int) -> tuple[str, ...]:
    """One line saying what the WORLD remembers about this scene.  Never raises.

    WHY IT IS HERE, ON THE ARRIVAL PATH, AND NOT IN A DIAGNOSTIC.  A shared
    world is only shared if it can be MEASURED as shared, and the criterion
    `PANYA-DECISION 20260905_1140` sets is a comparison across two readings:
    two sessions standing in one scene, or one session before and after a
    relogin on a server that never restarted, must see the same monsters,
    the same graves and the same ground.  This line is that reading, printed
    once per arrival at the one seam this lane owns end to end.

    !! WHAT THIS LINE IS NOT EVIDENCE OF, and the trap is worth naming
    because the first draft of this docstring walked into it: "grep the
    token twice and compare" is satisfied on TODAY'S BUILD by any two
    arrivals into any scene, because both readings are `monsters=0 graves=0
    ground=0` and zero equals zero (pf-adversary, round `tz2rgc`, D6 --
    the `GM_WARP_POSITION_CONFIRMED` shape, a token compared against the
    previous reading rather than an intended target).  A comparison of two
    readings is only evidence when the FIRST one is non-zero, i.e. after
    LANE-B's write call site exists.  The GT ticket for this feature is drafted
    in `pf_bridge/notes_to_chief/20260905_1340_LANE-A-TO-CHIEF-world-registry-
    landed-gt-body-relogin-needs-a-number.md` and has no number yet; its own
    preconditions say the same thing, and nobody should be asked to boot for
    it before then.  (Stated as a pointer rather than as a fact about a
    ticket that exists in this repository: it does not -- pf-adversary,
    round `tz2rgc`, N9.)  What the line honestly gives today is that the world books are
    reachable from the arrival path at all, and a place for the numbers to
    appear the moment they are real.

    IT CHANGES NO BYTES.  It is appended to `console_lines`; the census
    frame, the actor count and the membership are exactly what they were.
    Until the seed and write halves are wired (`world_scene_registry.
    WORLD_REGISTRY_SEED_WIRING`, and LANE-B's own write call site) the
    numbers it prints are the honest ones -- an empty book reads zero, which
    is itself the "not wired yet" the round file states rather than hides.

    A scene id with no folder (nothing mined, a scene outside the copy) is
    NOT an error here: this lane composes for scenes it has rosters for, and
    a missing folder means the world books have no key for it either, so
    there is nothing to say and no line is printed.
    """
    try:
        folder = world_scene_folder.scene_folder_for_scene_id(scene_id)
        if not folder:
            return ()
        return (world_scene_registry.describe_view(
            world_scene_registry.view(folder)),)
    except Exception:                                       # noqa: BLE001
        # An observability line is never worth an arrival.  The composer's
        # own contract is that it either composes or declines by name, and
        # "the world registry could not be read" is neither.
        return ()


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
        if not scene_may_be_populated(scene_id, scene_entry_registry):
            # THE ADMISSION CHECK.  Decline, which the call site latches with
            # a named event and no frame - the same outcome the not-home skip
            # produced before this file existed.  TWO ARMS since round
            # `4uztfj`: the registry pin, and the GM lane's own sanctioned
            # single-use predicate for a session that is already standing in
            # a scene whose ordinary door is shut (scene 126 today).  See
            # ``scene_is_sanctioned_for_a_gm_entry`` for why the second arm
            # opens nothing.
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
        field_mob_identities, field_mob_note = _field_mob_identities(scene_id)
        console_lines = (
            (world_population_handoff.handoff_console_line(handoff),)
            + tuple(_CONSOLE_LINES_OF[source](handoff.generation))
            + _hostility_lines(scene_id, handoff.generation)
            + (() if field_mob_note is None else (field_mob_note,))
            + _world_registry_line(scene_id)
        )
        return lane_hooks.SceneCensusResult(
            actor_count=handoff.actor_count,
            pc=handoff.pc,
            frame=handoff.frame,
            console_lines=console_lines,
            initial_reapply_ms=handoff.reapply_ms,
            membership=_membership_if_answerable(scene_id, handoff),
            actor_identities=field_mob_identities,
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
