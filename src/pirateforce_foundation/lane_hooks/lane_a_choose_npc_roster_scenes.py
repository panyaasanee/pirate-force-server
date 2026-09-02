"""LANE-A (WORLD): the ChooseNPC responder for the roster islands.

WHAT A PLAYER SEES BECAUSE OF THIS FILE, STATED HONESTLY AND FIRST.
Yesterday: a player who reached Spice Paradise saw that island's 62-strong
crowd standing there and could CLICK NONE OF THEM.  The click went out on
the wire and the server said nothing back -- no name, no HP, no turn toward
the player.  Today the same click gets the same answer Port Royal (scene 1)
and Hell Volcano Island (scene 14) have already been giving: the clicked
actor turns to face the player and the whole roster is re-sent with its
names, levels and HP intact.

    ONE SCENE TODAY, NINE HELD BACK BEHIND A NAMED GATE, AND THAT IS THE
    MOST IMPORTANT PARAGRAPH IN THIS FILE.  The round that wrote it started
    out registering all ten islands with rosters (scenes 3, 4, 5, 6, 7, 8,
    9, 10, 11 and 130 -- 692 actors).  ``pf-adversary`` measured, on the
    real dispatcher, that nine of those ten would ALSO have opened Port
    Royal's Columbus quest on the wrong island.  See THE COLUMBUS
    PLACEMENT-INDEX COLLISION below: it is not a hazard this file could
    write around, so it registers only the scene that is provably clear of
    it and refuses the other nine, loudly, until a one-line scene guard
    lands in ``runtime.py`` (chief's file, CORE-REQUEST from this round).

    WHAT THIS DOES NOT CLAIM.  This is WIRE/DB evidence only.  Nobody has
    yet clicked an NPC on scene 3 with a real client and reported what
    rendered -- scene 14's own equivalent step is still waiting on
    ``GT-134``, and this file does not shortcut that ticket for another
    scene.  What is measured is that the click now produces a composed,
    byte-checked answer frame where it produced nothing at all, and that
    the bodies in it are the same bodies the arrival census sent.  Whether
    the client draws it is ``GT-210``, not a claim made here.

WHY A TABLE AND NOT ONE FILE PER SCENE.  Every one of
``world_bg0003_identity`` ... ``world_bg4001_identity`` exposes
``SCENE_N_ID`` and ``shippable_placements()``, and every placement exposes
``placement_index``/``x``/``y``/``z``/``identity`` plus the same five
properties.  Ten copies of one function differing only in an import line
would be ten places for the next defect to hide in nine of.  So the table
is the module, ``_make_responder`` is called once per row that passes the
gates, and the gates are what decide which rows those are.

THE COLUMBUS PLACEMENT-INDEX COLLISION (the gate that fires today).
Actor identity on this wire is ``0x2000 + placement_index + 1`` with NO
scene component, so ``population_indices`` is a scene-blind index space
that eleven different tables now write into.  ``runtime.py``'s
``_dispatch_columbus_quest3021`` reads it and asks only:

    ``columbus_quest_dispatch.COLUMBUS_PLACEMENT_INDEX in
    self.population_indices``

-- with no scene check at all.  ``COLUMBUS_PLACEMENT_INDEX`` is 1, and
Columbus's actor identity is therefore ``0x2002``, which is ALSO the actor
at placement index 1 on nine of these ten islands.

Registering a responder for a scene is what arms that scene's
``population_indices`` (``lane_a_scene_census._membership_if_answerable``),
so before this file existed the conjunct was false on every one of these
scenes and the branch was unreachable there.  MEASURED on the real
dispatcher (pf-adversary, round ``326kf4``): with all ten registered, a
single ``ChooseNPC`` for ``0x2002`` on scene 4 returns BOTH this lane's
face frame and ``CORE_REQUEST_014_COLUMBUS_Q3021_NPC_CONVERSATION_ONCE``,
and the matching ``QuestOperateVital`` that follows teleports the player to
scene 17 -- a scene whose registry row reads ``login_entry_allowed:
false``.  Two client frames, on nine islands, to a door the registry has
shut.

``_columbus_collision_scenes()`` below computes the collision from the
identity tables rather than hardcoding a list, and ``_register_all``
refuses to register those scenes.  Today that is scenes 4, 5, 6, 7, 8, 9,
10, 11 and 130; scene 3's own table has no placement at index 1, so it is
clear by measurement rather than by luck being assumed.

    THE FIX IS ONE LINE AND IT IS NOT IN THIS LANE'S ZONE: the branch at
    ``runtime.py:5100`` needs to ask whether the session is standing in
    Columbus's own scene before reading a scene-blind index.  Until that
    lands, flipping the nine rows on is a regression, not a feature.  A
    round that lands the guard can delete
    ``_columbus_collision_scenes`` from ``_SKIP_RULES`` and get nine
    scenes at once; nothing else here has to change.

THE SPLICE GATE (the second gate; it does not fire today).  This responder
rebuilds a roster from the identity table on every click, but a scene's
ARRIVAL census is not always the identity table alone:
``world_population_handoff._roster_handoff`` splices
``field_mob_hostile_bg0015``'s hostile override over 12 of scene 14's 81
actors.  A rebuild that does not know about a splice reverts it on the wire
the moment anyone clicks -- measured once already (chief's letter
``pf_bridge/notes_to_chief/20260831_2318_CHIEF-TO-LANE-A-choosenpc-scene14-
reverts-hostile-splice-to-civilian.md``).  ``_SPLICED_SOURCES`` names every
census source the handoff splices, and ``_register_all`` refuses those
scenes too.

Today that set is exactly ``{"bg0015_roster"}`` and no scene in the table
is in it, so this gate never fires -- which is where a gate normally gets
deleted as dead code.  Its live job is the day a second scene is spliced.
``tests/test_lane_a_choose_npc_roster_scenes.py`` parses
``world_population_handoff.py`` with ``ast`` (not a regex over lines, which
a change of quote style or a line break defeats) and fails if the two sets
disagree; and it drives ``_register_all`` itself, so deleting the refusal
turns a test red rather than leaving it green.

    NOT A CLAIM THAT EITHER GATE IS SUFFICIENT.  A splice applied somewhere
    other than a comparison against ``composer.source`` in
    ``world_population_handoff`` is seen by neither the constant nor the
    test.  A scene-blind consumer of ``population_indices`` OTHER than the
    Columbus branch would not be caught either -- and nothing in
    ``lane_hooks`` has anywhere to state that invariant.  Both gates close
    the one case each was measured on, and this file says so rather than
    implying coverage it does not have.

WHY SCENES 1, 2 AND 14 ARE NOT IN THE TABLE, STATED AS MEASURED.
``lane_hooks`` imports in filename-sort order, so THIS module imports
BEFORE ``lane_a_choose_npc_scene1`` and ``lane_a_choose_npc_scene14``, and
first registration wins.  A duplicate does NOT raise or fail the boot -- it
prints one ``LANE_HOOK_DUPLICATE`` line to stderr and keeps the first
registration (measured, pf-adversary round ``326kf4``; an earlier draft of
this docstring claimed a boot error, which was false in both halves).  So
adding scene 14 to the table here would silently make THIS module win and
the hostile-aware responder lose.  The splice gate happens to catch that
one case; nothing catches it in general, and scene 1's slot is in fact FREE
at runtime (``lane_a_choose_npc_scene1`` prints
``SKIPPED_NOT_PRODUCTION_ALLOWED`` and is withdrawn).  The table is the
only thing keeping this module out of both slots, so do not add a scene to
it without reading this paragraph.

Scene 2 is excluded for a different reason: it has no
``world_bg0002_identity`` module at all.  Its roster (``bg0002_roster``) is
built on a shape that predates this family, so there is no
``shippable_placements()`` to read, and reaching into the population
builder instead would make this module an importer of a module whose own
test asserts an EXACT importer set.  Scene 2's click stays unanswered, said
out loud rather than left for a reader to notice.

THE FIRST CLICK AFTER A WARP DECLINES, AND THAT IS NOT A BUG HERE.
``runtime.py``'s cross-scene GM-warp resync sets ``last_target_pos = None``
(``runtime.py:5684``) along with the rest of the old scene's index space,
on purpose: those fields describe placements in the map the player just
left.  The census re-arms ``population_indices`` for the new scene on
arrival, but ``last_target_pos`` stays ``None`` until the player's own next
``TargetPosVital`` -- so a click taken the instant a ``/warp`` lands has no
player position to compute a heading from, and this responder declines it.
ONE STEP (any movement) fills the field and the next click is answered.
Written down rather than worked around: inventing a position to face would
be the kind of made-up coordinate the arrival-point rule forbids, and a
tester who does not know this would read silence as failure.  ``GT-210``
carries the step as a numbered instruction for that reason.

WHAT FLIPPING A RESPONDER FLAG CLAIMS, WHICH IS MORE THAN ANSWERING A
CLICK.  ``runtime.py:7520-7533`` states the obligation in its own words: a
registered, allowed responder CLAIMS the whole ``TARGET_VITAL`` /
``CHOOSE_NPC`` family for that scene, so v141's own arming of
``action_target_last_identity`` / ``_last_kind`` /
``p30_action_target_armed`` is skipped for every frame this branch takes,
and "a future scene whose players use melee/skill targeting on the SAME
connection a responder claims must re-check this before flipping its flag".
THIS ROUND HAS NOT DISCHARGED THAT for scene 3: no melee or skill targeting
path is wired for these scenes today, and no test here measures one.  It is
recorded as an open obligation, not as a cleared one.  The multi-select gap
``runtime.py:7535-7548`` names (one answer per frame, first named identity
wins) is inherited from the sibling responder unchanged and untested here.

WHY THIS READS THE IDENTITY MODULES AND NOT THE POPULATION BUILDERS.  Same
reason ``lane_a_choose_npc_scene14.py`` gives: every
``tests/test_world_population_bgXXXX.py`` asserts an exact set of importers
for its builder, deliberately, so that "wired" can never happen silently.
This module's identity of a scene does not need the builder, only the table
the builder itself reads.

FAIL-CLOSED, AS A PROPERTY.  Every path returns ``None`` (decline) rather
than raising for every ordinary input: a scene this file does not serve, a
scene the registry has shut, a click before the census armed
``population_indices``, a click before the player has moved, an identity
this scene's table does not hold, an empty roster.  ``runtime.py``'s call
site also wraps the call, but a lane that relies on the caller's net for
its ordinary answers has no contract.  ``BaseException`` is deliberately
not caught, the same named hole ``lane_hooks/__init__.py`` and
``world_logout_button_notice.py`` both state.
"""
from __future__ import annotations

from typing import Any, Callable

from .. import columbus_quest_dispatch
from .. import lane_hooks
from .. import world_census_level
from .. import world_scene_travel
from .. import world_bg0003_identity
from .. import world_bg0004_identity
from .. import world_bg0005_identity
from .. import world_bg0006_identity
from .. import world_bg0007_identity
from .. import world_bg0008_identity
from .. import world_bg0009_identity
from .. import world_bg0010_identity
from .. import world_bg0011_identity
from .. import world_bg4001_identity
from .lane_a_scene_census import scene_is_open_to_players

# SHIPPABLE, FOR THE SCENES THE GATES BELOW ADMIT AND NO OTHERS.  Every
# scene in the table below is already open at login (``login_entry_allowed:
# true`` in scenarios/world_scene_registry_001.json) and already ships its
# roster on arrival through this lane's own census composer.
#
# WHAT FLIPPING THIS ON REALLY DOES, WRITTEN AFTER pf-adversary MEASURED
# THAT AN EARLIER DRAFT OF THIS COMMENT WAS FALSE.  It does not only turn a
# click from silence into an answer.  Registering a responder for a scene
# also ARMS that scene's ``population_indices`` (see
# ``lane_a_scene_census._membership_if_answerable``), and other, scene-blind
# readers of that field then become reachable on that scene -- one of which,
# ``runtime.py``'s Columbus branch, opens a quest that teleports the player
# to a scene the registry has shut.  So this flag CAN open a door, and the
# gates in ``_register_all`` below are what keep it from doing so.  The
# registry pin is still the outer door, and ``scene_is_open_to_players``
# still asks it on every single click -- see lane_a_scene_census.py's THE
# ADMISSION CHECK for why per call rather than once at import.
production_allowed = True

# Scene n_id -> the identity module that holds that scene's placement table.
# Ordered by scene id; ``world_bg4001_identity`` answers for scene 130.
_IDENTITY_OF_SCENE: dict[int, Any] = {
    world_bg0003_identity.SCENE_N_ID: world_bg0003_identity,
    world_bg0004_identity.SCENE_N_ID: world_bg0004_identity,
    world_bg0005_identity.SCENE_N_ID: world_bg0005_identity,
    world_bg0006_identity.SCENE_N_ID: world_bg0006_identity,
    world_bg0007_identity.SCENE_N_ID: world_bg0007_identity,
    world_bg0008_identity.SCENE_N_ID: world_bg0008_identity,
    world_bg0009_identity.SCENE_N_ID: world_bg0009_identity,
    world_bg0010_identity.SCENE_N_ID: world_bg0010_identity,
    world_bg0011_identity.SCENE_N_ID: world_bg0011_identity,
    world_bg4001_identity.SCENE_N_ID: world_bg4001_identity,
}

# Census sources whose ARRIVAL frame is not the identity table alone --
# see THE SPLICE GATE in this module's docstring.  A scene whose
# CENSUS_SOURCES row names one of these gets NO responder from this file.
_SPLICED_SOURCES = frozenset({"bg0015_roster"})

# The wire shapes, taken from the sibling responder rather than re-derived:
# actor type 4 is the NPC style every roster entry in this project uses, and
# scene sequence 0 is what every ``world_population_bgXXXX.SCENE_SEQUENCE``
# carries.  Mask 0x03 is the turn-to-face mask
# ``lane_a_choose_npc_scene14.respond`` sends for the clicked actor.
_NPC_STYLE_ACTOR_TYPE = 4
_SCENE_SEQUENCE = 0
_FACE_MOVEMENT_MASK = 0x03

# Filled by _register_all() below: scene id -> why it was skipped.  Read by
# the tests and by anyone wondering where a scene's responder went.
_SKIPPED: dict[int, str] = {}


def scenes_this_lane_answers_for() -> tuple[int, ...]:
    """The scene ids whose responder slot THIS module actually holds.

    READ FROM THE LIVE REGISTRY, not from ``_IDENTITY_OF_SCENE`` minus
    ``_SKIPPED``.  An earlier draft did the latter and its own docstring
    claimed otherwise; pf-adversary measured the difference: with
    ``production_allowed = False`` -- the owner-approved kill switch, which
    ``lane_hooks._withdraw`` enforces by REMOVING the registrations -- the
    subtraction still reported every scene as answered, and it would also
    report a scene whose slot another lane won first.  Asking the registry
    cannot disagree with the registry.
    """
    return tuple(
        scene_id for scene_id in sorted(_IDENTITY_OF_SCENE)
        if (responder := lane_hooks.scene_choose_npc_responder(scene_id))
        is not None and responder.module == __name__
    )


def skipped_scenes() -> tuple[tuple[int, str], ...]:
    """Scene id -> reason, for every row a gate refused to register."""
    return tuple(sorted(_SKIPPED.items()))


def _census_source_of(scene_id: int) -> str | None:
    """This scene's row in the seam's own source table, or ``None``.

    Read from ``world_scene_travel.CENSUS_SOURCES`` rather than from a
    second copy here: the splice gate has to ask the same table
    ``world_population_handoff`` asks, or it is checking its own opinion.
    """
    return world_scene_travel.CENSUS_SOURCES.get(scene_id)


def _placements_by_index(identity: Any) -> dict[int, Any]:
    """Placement index -> resolved placement, rebuilt per call.

    Not cached, same trade and same reason as the sibling responder's own
    helper: ``shippable_placements()`` is pure over a frozen table, so the
    cost is one dict build per click rather than a re-read of anything that
    can change under us.
    """
    return {p.placement_index: p for p in identity.shippable_placements()}


def _make_responder(scene_n_id: int, identity: Any) -> Callable[..., Any]:
    """Build the responder for ONE scene, closing over its identity module.

    A closure rather than a partial so the returned function carries the
    scene in its own name for a traceback, and so ``respond``'s signature is
    the same keyword-only shape every other registered responder has.
    """

    def respond(
        *,
        legacy: Any,
        chosen_identities: tuple[int, ...],
        population_indices: tuple[int, ...] | None,
        last_target_pos: tuple[float, float, float, float] | None,
        scene_id: int = scene_n_id,
        scene_entry_registry: Any = None,
        **_ignored: Any,
    ) -> "lane_hooks.ChooseNpcResponse | None":
        """Answer one ChooseNPC click for this scene, or decline.

        Keyword-only, same convention as every other registered responder,
        so a future call site can grow arguments without breaking all of
        them at once.  ``chosen_identities`` is exactly what
        ``legacy.extract_choose_npc_identities(parsed)`` returns, so a test
        drives this with no wire bytes at all.
        """
        if scene_id != scene_n_id:
            # The call site keys the registry by the player's own scene, so
            # this cannot happen from production today.  Kept because the
            # sibling responder keeps it for the same reason: a responder
            # that trusts its caller to have looked up the right scene
            # delivers one island's crowd into another.
            return None
        if not scene_is_open_to_players(scene_id, scene_entry_registry):
            return None
        if population_indices is None or last_target_pos is None:
            return None
        by_idx = _placements_by_index(identity)
        player_x, player_y = last_target_pos[0], last_target_pos[1]
        for actor_identity in dict.fromkeys(chosen_identities):
            selected_idx = actor_identity - 0x2000 - 1
            if selected_idx not in population_indices:
                continue
            if selected_idx not in by_idx:
                # Fail closed: never invent a row this scene's own table
                # does not hold.  Try the next named identity in this same
                # frame rather than giving up on the whole click.
                continue
            entries = []
            omitted = 0
            for idx in population_indices:
                placement = by_idx.get(idx)
                if placement is None:
                    # A composed index with no resolvable placement (should
                    # not happen: population_indices comes from this same
                    # table's own generation).  Counted and reported rather
                    # than raised, the same "drop and say so" discipline the
                    # sibling responder uses.
                    omitted += 1
                    continue
                # LEVELED, NOT BARE.  A plain ``legacy.make_npc_attr`` here
                # would re-send every actor in the roster with no level and
                # silently revert round ``7ste68`` on the wire the moment
                # anyone was clicked -- the defect that shipped once already
                # on scene 1 (``world_face_frame.build_face_state``) and was
                # caught a second time on scene 14.  Every one of these ten
                # scenes' arrival censuses composes through this same
                # encoder (``world_population_bgXXXX._entry_for``), so this
                # rebuild matches the arrival bytes per actor rather than
                # approximating them.
                npc_attr_bytes = world_census_level.leveled_npc_attr(
                    legacy,
                    template_n_id=placement.n_id,
                    actor_identity=placement.actor_identity,
                    scene_id=scene_id,
                    scene_sequence=_SCENE_SEQUENCE,
                    visual_preset=placement.visual_preset,
                    current_hp=placement.max_hp,
                    max_hp=placement.max_hp,
                    basic_name=placement.display_name,
                    level=placement.identity.level,
                )
                attrs = [(legacy.NPC_ATTR, npc_attr_bytes)]
                if idx == selected_idx:
                    heading = legacy._heading_to_player(
                        placement.x, placement.y, player_x, player_y,
                    )
                    attrs.append((
                        legacy.MOVEMENT_ATTR,
                        legacy.make_remote_movement_attr(
                            placement.actor_identity,
                            placement.x, placement.y, placement.z,
                            heading, mask=_FACE_MOVEMENT_MASK,
                        ),
                    ))
                entries.append(legacy.make_remote_actor_entry(
                    _NPC_STYLE_ACTOR_TYPE, placement.actor_identity, attrs,
                ))
            if not entries:
                continue
            pc, frame = legacy.make_runtime_remote_actors(entries)
            console_lines = (
                f"LANE_A_CHOOSE_NPC_SCENE{scene_id}_ANSWERED "
                f"placement={selected_idx} visible={len(entries)} "
                f"omitted={omitted}",
            )
            return lane_hooks.ChooseNpcResponse(
                label=(
                    f"LANE_A_CHOOSE_NPC_SCENE{scene_id}_FACE_P{selected_idx}"
                ),
                pc=pc, frame=frame, delay=0.0, console_lines=console_lines,
            )
        return None

    respond.__name__ = f"respond_scene{scene_n_id}"
    respond.__qualname__ = respond.__name__
    return respond


def _columbus_collision_scenes() -> frozenset[int]:
    """Scenes whose own table has an actor at Columbus's placement index.

    THE GATE THAT FIRES TODAY -- read THE COLUMBUS PLACEMENT-INDEX COLLISION
    in this module's docstring before touching it.  ``runtime.py``'s
    Columbus branch asks whether ``COLUMBUS_PLACEMENT_INDEX`` is in
    ``population_indices`` and asks nothing about the scene, so arming that
    field for a scene that HAS such a placement makes Port Royal's quest
    reachable on the wrong island.

    COMPUTED, NEVER A HARDCODED LIST: the collision is a fact about each
    scene's own placement table, so a table that gains or loses index 1
    changes this answer without anyone remembering to edit a constant.
    """
    return frozenset(
        scene_id for scene_id, identity in _IDENTITY_OF_SCENE.items()
        if any(
            placement.placement_index
            == columbus_quest_dispatch.COLUMBUS_PLACEMENT_INDEX
            for placement in identity.shippable_placements()
        )
    )


def _skip_reason_for(scene_id: int) -> str | None:
    """Why this scene gets no responder from this file, or ``None``.

    THE ONE PLACE BOTH GATES ARE DECIDED.  ``_register_all`` calls it and
    the tests call it, so a test cannot pass by re-implementing the rule it
    claims to be checking -- which is exactly what an earlier version of
    this round's splice-gate test did (pf-adversary: deleting the refusal
    from ``_register_all`` left that test green).
    """
    source = _census_source_of(scene_id)
    if source is None:
        return "no_census_sources_row"
    if source in _SPLICED_SOURCES:
        return f"spliced_source_{source}"
    if scene_id in _columbus_collision_scenes():
        return (
            "columbus_placement_index_collision_needs_runtime_scene_guard"
        )
    return None


def _register_all() -> None:
    """Register one responder per admitted scene; name every refusal.

    Runs at import.  A skip is LOUD (a printed token plus a row in
    ``_SKIPPED``) rather than a silent absence, the same discipline
    ``lane_a_scene_census.py``'s own ``LANE_A_CENSUS_SKIPPED`` uses: a scene
    that quietly loses its responder is a click that quietly goes back to
    saying nothing, which is exactly the state this file exists to end.
    Re-entrant: ``_SKIPPED`` is rebuilt rather than appended to, so a test
    may withdraw this module's registrations and call it again.
    """
    import sys

    _SKIPPED.clear()
    for scene_id in sorted(_IDENTITY_OF_SCENE):
        reason = _skip_reason_for(scene_id)
        if reason is not None:
            _SKIPPED[scene_id] = reason
            print(
                f"LANE_A_CHOOSE_NPC_ROSTER_SKIPPED scene={scene_id} "
                f"reason={reason}",
                file=sys.stderr,
            )
            continue
        lane_hooks.choose_npc_responder(scene_id)(
            _make_responder(scene_id, _IDENTITY_OF_SCENE[scene_id])
        )


_register_all()
