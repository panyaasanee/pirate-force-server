"""LANE-A (WORLD): the ChooseNPC responder for scene 14 (Hell Volcano Island).

WHAT A PLAYER SEES BECAUSE OF THIS FILE, STATED HONESTLY AND FIRST.  ~~Nothing
yet.  ``production_allowed`` below is ``False`` on purpose -- read WHY THIS
FILE'S OWN GATE IS CLOSED before treating anything in this module as live.~~
FLIPPED, LANE-A round `n8fq3w`, 2026-08-30.  The
``runtime.py`` guard this file's own CORE-REQUEST asked for landed on `main`
(chief, round `hd6tac`/R237) and stayed there unflipped through one more
round (`e2q8c6`, zero-diff) -- the chief's own reply letter
(`pf_bridge/notes_to_chief/20260830_1022_CHIEF-REPLY-CORE-REQUEST-choosenpc-
scene-guard-wired.md`) named this exact line as "your one line, not started
here" and left flipping it to this lane's own judgement.  Scene 14's login
door is independently already open (`login_entry_allowed: true`, LANE-A round
`vvy6q7`) and its 81-actor roster's WIRE frame already ships on arrival
regardless of this flag (``SceneCensusResult.membership`` only ever governed
whether a CLICK on one of them is answered, never whether the census frame
carries them -- see ``lane_a_scene_census.py``'s own docstring).  `GT-134` is
the still-unmeasured attended ticket for whether those 81 actors actually
RENDER on a real client, and this file does not shortcut that -- WIRE/DB
evidence (what a boot's console/DB shows) and CLIENT-OBSERVABLE evidence
(what `GT-134` will show) are kept apart here on purpose.  What is provably
true only at the wire layer, before this flip: a session on scene 14 never
arms `population_indices`, so a `ChooseNPC`/`TARGET_VITAL` frame on this
scene never reaches the frozen handler's per-actor loop at all today (the
frozen dispatcher only runs it once `population_indices` is non-``None``) --
so there was no observed crash risk either, only an unanswered click at the
wire layer.  AFTER this flip, driven end to end by this lane's own tests
(not yet by `GT-134`): the same click gets an answer -- name, HP and a
player-facing turn, through the same frozen wire shapes Port Royal already
uses, sourced from this scene's own placement table.  Nothing about the 81
actors' positions, models or names changes; only "click gets no wire
response" becomes "click gets an answered frame" -- whether a client renders
that answer the same way it renders Port Royal's is exactly what `GT-134`
and a follow-up click test still have to measure.
UPDATED, LANE-A round `yfbqmg`, 2026-09-01: a defect chief's
pf-adversary run caught (see "WHY IT NOW ALSO READS
``field_mob_hostile_bg0015``" below) meant that clicking ANY of scene 14's
81 actors silently reverted the 12 hostile-spliced ones back to civilian on
the wire -- so `GT-178` would have read as "hostile splice does not work"
the moment a tester clicked before checking aggro, when the real defect was
one layer down and wire-only.  After this round's fix: a click leaves all
81 actors' civilian/hostile identity exactly as the arrival census set it;
only whether a wire-level regression test would have caught this earlier
changes, not anything `GT-134`/`GT-178` themselves render differently
(neither ticket has run yet against this fix).

WHY THIS FILE EXISTS.  COO-DECISION 20260830_0818 (answering chief's
``CHIEF-ASK-COO`` 20260830_0155) approved a ChooseNPC responder for roster
scenes, registered through ``lane_hooks`` the same way
``lane_hooks/lane_a_scene_census.py`` registers its census composer, so that
scene 14's composed roster (81 actors, that same file) can eventually answer
a real click instead of shipping with ``population_indices`` /
``population_refresh_anchor`` / ``world_census_indices`` withheld
(the crossing branch's ``world_pop_handoff_membership_withheld_scene_14``,
pf-adversary R235 D2).  This module is that responder, and
``lane_a_scene_census.py``'s ``_membership_if_answerable`` is the one place
that now asks whether it exists before arming real membership -- see that
file for the wiring half of this decision.

WHY THIS FILE'S GATE **WAS** CLOSED (``production_allowed = False`` until
LANE-A round `n8fq3w`), AND WHAT CLOSED IT.  ~~Building this responder does
not, by itself, change the mechanism pf-adversary R235 D2 measured.~~  THAT
WAS TRUE UNTIL THE runtime.py GUARD LANDED (chief, round `hd6tac`/R237); it
is quoted rather than rewritten because the crash it describes was real and
the next three paragraphs of this section are the reason it does not fire
today.  Before round `hd6tac`, the ONLY thing that answered a real
``ChooseNPC``/``TARGET_VITAL`` click was the
frozen ``current/pf_login_game_server_v141.py:4395``, reached
UNCONDITIONALLY from ``runtime.py``'s own ``super().dispatch(parsed)``
(``runtime.py:6644`` at that round) on every ``RuntimeProtocolReq`` frame
whose ``nested_id`` is ``TARGET_VITAL``/``CHOOSE_NPC`` -- BEFORE any lane
code, this module included, got a turn (``runtime.py``'s own additive lane
branches, e.g. ``_dispatch_columbus_quest3021``, all ran AFTER that call
returned, appended to the action list; none of them could prevent it from
running first).  Its handler, ``make_v98_conversation_face_state``
(v141:1078-1106), loops over the WHOLE of ``self.population_indices`` -- not
only the clicked actor -- and does an unconditional
``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS``-keyed dict lookup for every one of
them (v141:1093-1094: ``for idx in population_indices: ... by_idx[idx]``,
with no ``.get()`` and no guard).  Sixteen of scene 14's 81 composed indices
have no row in that table, so the moment ``self.population_indices`` carries
scene 14's real membership, the FIRST ``TARGET_VITAL``/``CHOOSE_NPC`` frame
of the session -- for ANY of the 81 actors, not only the 16 missing ones --
raises ``KeyError`` inside a listener thread with no ``except`` around that
call (v141:7440's own contract), dropping the connection.  This is the exact
defect R235 D2 measured and the exact reason the crossing branch withholds
membership.  Even the 65 indices that DO happen to resolve are not a safe
subset either: ``by_idx[idx]`` for those returns PORT ROYAL's row, so the
frame would recompose Port Royal's townsfolk into Hell Volcano at Hell
Volcano's own placement coordinates -- the second defect R235 D2 named,
wrong actors rather than a crash, and this module refuses to trade one for
the other (see FAIL CLOSED below).

~~Nothing this module can do from ``src/`` prevents the frozen loop from
running, because ``super().dispatch()`` does not consult ``lane_hooks`` at
all today~~ -- SUPERSEDED, round `hd6tac`: ``runtime.py``'s own dispatch
method (``runtime.py:6714`` at this round) now checks, ahead of
``super().dispatch(parsed)``, whether the session's current scene has a
REGISTERED and ALLOWED ``lane_hooks.scene_choose_npc_responder`` and, if so,
answers through it INSTEAD of ever running the frozen loop for that frame.
That guard is the ``CORE-REQUEST`` this section used to ask for; it is now
on `main` and is the chief's file, not this lane's, so it is described here
rather than repeated.

This module was always complete and correct for what it answers -- a
caller could drive ``respond()`` end to end before the guard existed, and
this lane's own tests did -- and ``production_allowed`` stayed ``False``
only until the guard landed and this lane confirmed it, which round
`n8fq3w` did.  Two gaps the guard's own comment and this lane's tests pin
rather than fix, read before touching this file again: (1) claiming a scene
skips v141's own unconditional TARGET_VITAL arming
(``action_target_last_identity``/``_last_kind``/``p30_action_target_armed``),
harmless here only because scene 14's real actors do not have the
arena-harness identity shape that arming's later consumer wants; (2) a
multi-select ``ChooseNPC`` click is answered with only ONE frame through a
claimed scene, because ``respond()`` returns at most one
``ChooseNpcResponse`` per call, where the frozen path would have answered
every named identity.  Both are pinned by
``tests/test_lane_a_choose_npc_scene14.py``
(``TheGuardAnsweredTheClickInsteadOfCrashingTests``) so neither can get
silently worse.

THE ADMISSION CHECK.  Reuses
``lane_a_scene_census.scene_is_open_to_players`` rather than re-deriving
it: the registry key is one gate this project already has a fail-closed
reader for, and a second implementation of the same question is the risk
that module's own docstring already refused once.

HOW IT ANSWERS, AND WHY IT NEVER TOUCHES ``self.population_indices``
ITSELF.  Given the population indices a caller says are already live for
this session (the membership ``lane_a_scene_census`` supplies once armed)
and the identities the client actually chose, this rebuilds the exact V98
conversation-face wire shape -- ``NPCAttr`` for every visible actor,
``MovementAttr`` (a player-facing heading, via the same frozen
``_heading_to_player``) for the clicked one only -- through the same frozen
serializers ``world_face_frame.py`` already uses for Port Royal
(``make_npc_attr``, ``make_remote_movement_attr``, ``make_remote_actor_entry``,
``make_runtime_remote_actors``), sourced from ``world_bg0015_identity``'s
placement table instead of ``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS``.  No wire
shape is invented; only the table it is filled from changes, the same claim
``world_face_frame.py`` makes for its own scene.  This function never reads
or writes ``self`` -- it takes the state it needs as arguments, the same
``census_composer`` convention -- so it cannot arm the frozen path by
accident.

WHY IT NOW ALSO READS ``field_mob_hostile_bg0015`` (LANE-A round `yfbqmg`,
2026-09-01).  CONFIRMED DEFECT
(``pf_bridge/notes_to_chief/20260831_2318_CHIEF-TO-LANE-A-choosenpc-
scene14-reverts-hostile-splice-to-civilian.md``, chief's own mutation-tested
pf-adversary run, round R274): before this round, every ``NPCAttr`` body
above came from ``legacy.make_npc_attr`` alone, which knows nothing about
``field_mob_hostile_bg0015.scene14_hostile_overrides`` -- the hostile
faction+level splice ``world_population_handoff._roster_handoff`` writes
into 12 of the 81 placements on arrival (this same round's LANE-A+LANE-B
CORE-REQUEST, ``20260831_2151_LANE-A-TO-CHIEF-*.md``).  So the FIRST
``ChooseNPC``/``TARGET_VITAL`` click after arrival -- on ANY of the 81
actors, spliced or not, because this function always rebuilds all of
``population_indices`` to answer one -- silently overwrote the wire's own
already-sent hostile bodies back to civilian, with no error and nothing in
``console_lines`` naming it.  The fix is the same choice
``_hostile_mobs_by_placement_index`` and its call site below make: for each
of the 12 overridden placement indices, build the NPCAttr body with
``field_mobs.hostile_npc_attr`` (the SAME encoder ``_roster_handoff``'s
splice already ships, not a re-derivation) instead of
``legacy.make_npc_attr``; every other placement is unaffected.  The clicked
actor's ``MovementAttr`` (heading toward the player) is unchanged either
way -- that half of the response answers "where do I turn to face them",
which has nothing to do with civilian vs. hostile identity, so a hostile
placement's ``MovementAttr`` is still built from the same
``_heading_to_player`` call as before, not from
``field_mobs.hostile_actor_entry``'s own fixed-heading movement (that
function bakes together a body this responder does not want, since it
answers every click with the SAME heading regardless of where the player
stands -- correct for an arrival census, wrong for a face-the-player click).

FAIL CLOSED.  A chosen identity outside ``population_indices``, a placement
this table does not carry (never invented -- see the module docstring of
``world_bg0015_identity`` on the ten placements with no shippable identity),
or a caller that has not opened this scene (the admission check) all answer
``None`` for that identity: a click with no honest answer gets no frame,
never an invented one, and ``extract_choose_npc_identities`` can name more
than one actor in a single frame, so every named identity is tried before
giving up.
"""
from __future__ import annotations

from typing import Any

from .. import field_mob_hostile_bg0015 as hostile_bg0015
from .. import field_mobs
from .. import lane_hooks
from .. import world_bg0015_identity as identity
from .lane_a_scene_census import scene_is_open_to_players

# WHY THIS IS True, NOT False, AS OF LANE-A round `n8fq3w`: see "WHY THIS
# FILE'S GATE WAS CLOSED" in the module docstring above -- the runtime.py
# guard that made this flip safe is on `main` (chief, round `hd6tac`/R237)
# and this lane's own tests (test_lane_a_choose_npc_scene14.py) drive the
# real dispatcher both ways.  Nothing else in this file, and nothing in
# lane_a_scene_census.py, needed to change to flip this.
production_allowed = True

# Read from world_bg0015_identity directly, NOT from world_population_bg0015
# -- tests/test_world_population_bg0015.py's own guard test asserts an EXACT
# set of importers for that module (deliberately, per its own comment: "so
# 'wired' can never happen silently"), and this module's identity of scene
# 14 does not need the population builder itself to state it.
SCENE_N_ID = identity.SCENE_N_ID


def _placements_by_index() -> dict[int, Any]:
    """Placement index -> resolved placement, rebuilt per call.

    Not cached at module scope on purpose: ``shippable_placements()`` is
    itself a pure function over a fixed table (no per-boot state), so the
    cost is a dict build per click, not a re-read of anything mutable -- the
    same trade ``world_face_frame.build_face_state`` already makes for
    ``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS``.
    """
    return {p.placement_index: p for p in identity.shippable_placements()}


def _hostile_mobs_by_placement_index() -> dict[int, Any]:
    """Placement index -> ``field_mobs.FieldMob`` for this scene's 12
    hostile-splice placements, rebuilt per call (same non-caching convention
    as :func:`_placements_by_index` above, same reason: pure over a fixed
    table).

    THE BUG THIS EXISTS TO CLOSE (``pf_bridge/notes_to_chief/20260831_2318_
    CHIEF-TO-LANE-A-choosenpc-scene14-reverts-hostile-splice-to-civilian.md``,
    confirmed by chief's own mutation-tested pf-adversary run, round R274):
    before this function existed, EVERY ``ChooseNPC``/``TARGET_VITAL`` click
    on scene 14 -- the clicked actor or any of the other 80 -- rebuilt all 81
    ``NPCAttr`` bodies through ``legacy.make_npc_attr`` alone, which knows
    nothing about ``field_mob_hostile_bg0015``'s hostile-faction+level
    splice.  ``world_population_handoff._roster_handoff`` already splices
    that override into the ARRIVAL census (``composer.source ==
    "bg0015_roster"`` branch, this round's own CORE-REQUEST with lane B) --
    but this responder rebuilds its OWN collection from scratch on every
    click instead of reusing that composed generation, so the very first
    click after arrival silently overwrote the 12 spliced actors back to
    plain civilians on the WIRE, with no error and no console line naming
    it.  This helper is the one addition that lets :func:`respond` tell the
    two apart before choosing which encoder to call -- see its own call
    site below.
    """
    return {
        mob.placement_index: mob for mob in hostile_bg0015.scene14_hostile_roster()
    }


def respond(
    *,
    legacy: Any,
    chosen_identities: tuple[int, ...],
    population_indices: tuple[int, ...] | None,
    last_target_pos: tuple[float, float, float, float] | None,
    scene_id: int = SCENE_N_ID,
    scene_entry_registry: Any = None,
    **_ignored: Any,
) -> "lane_hooks.ChooseNpcResponse | None":
    """Answer one ChooseNPC click for scene 14, or decline (see module doc).

    Keyword-only, same convention as ``census_composer``'s ``compose``, for
    the same reason: a future call site can grow arguments without breaking
    every registered responder at once.  ``chosen_identities`` is exactly
    what ``legacy.extract_choose_npc_identities(parsed)`` returns -- this
    function does not parse the frame itself, so it can be driven directly
    by a test with no wire bytes at all.
    """
    if scene_id != SCENE_N_ID:
        return None
    if not scene_is_open_to_players(scene_id, scene_entry_registry):
        return None
    if population_indices is None or last_target_pos is None:
        return None
    by_idx = _placements_by_index()
    hostile_by_idx = _hostile_mobs_by_placement_index()
    player_x, player_y = last_target_pos[0], last_target_pos[1]
    for actor_identity in dict.fromkeys(chosen_identities):
        selected_idx = actor_identity - 0x2000 - 1
        if selected_idx not in population_indices:
            continue
        if selected_idx not in by_idx:
            # Fail closed: never invent a row this scene's own table does
            # not have.  Try the next named identity in this same frame
            # rather than giving up on the whole click.
            continue
        entries = []
        omitted = 0
        for idx in population_indices:
            placement = by_idx.get(idx)
            if placement is None:
                # A composed index with no resolvable placement (should not
                # happen: population_indices comes from this same table's
                # own generation), counted rather than raised -- the same
                # "drop and say so" discipline world_face_frame.py uses.
                omitted += 1
                continue
            hostile_mob = hostile_by_idx.get(idx)
            if hostile_mob is not None:
                # THE FIX: this placement is one of the 12 the arrival
                # census splices hostile (field_mob_hostile_bg0015).  A
                # civilian legacy.make_npc_attr body here would silently
                # revert that splice on the wire the moment ANY of the 81
                # actors gets clicked -- see _hostile_mobs_by_placement_
                # index's own docstring for the confirmed defect this
                # branch closes.
                npc_attr_bytes = field_mobs.hostile_npc_attr(
                    legacy, hostile_mob, current_hp=hostile_mob.max_hp,
                    scene_id=scene_id, scene_sequence=0,
                )
            else:
                npc_attr_bytes = legacy.make_npc_attr(
                    placement.n_id, placement.actor_identity, scene_id, 0,
                    placement.visual_preset, current_hp=placement.max_hp,
                    max_hp=placement.max_hp,
                    basic_name=placement.display_name,
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
                        heading, mask=0x03,
                    ),
                ))
            entries.append(legacy.make_remote_actor_entry(
                4, placement.actor_identity, attrs,
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
            label=f"LANE_A_CHOOSE_NPC_SCENE{scene_id}_FACE_P{selected_idx}",
            pc=pc, frame=frame, delay=0.0, console_lines=console_lines,
        )
    return None


lane_hooks.choose_npc_responder(SCENE_N_ID)(respond)
