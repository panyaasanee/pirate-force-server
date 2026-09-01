"""LANE-A (WORLD): the ChooseNPC responder for scene 1 (Port Royal / bg0001).

WHAT A PLAYER SEES BECAUSE OF THIS FILE, STATED HONESTLY AND FIRST.  Nothing
yet.  ``production_allowed`` below is ``False`` on purpose -- see "WHY THE
GATE STAYS CLOSED THIS ROUND" before reading anything else in this module as
live.  This file is the SAFETY NET half of a two-part fix; the other half
(widening ``runtime.py``'s login-census trigger for scene 1 so the town is
populated before the player's first step) is a chief-owned ``runtime.py``
edit this lane cannot make -- see the ``CORE-REQUEST`` this round's letter
names by line number.

WHY THIS FILE EXISTS (PANYA-ORDER 2026-09-01T09:55, ``pf_bridge/
notes_to_chief/20260901_0955_PANYA-ORDER-login-path-must-ship-the-census-
eagerly-like-the-warp-path-now-does.md``).  The owner's own words, filmed
mid-session: *"ตอนเข้าเกมมา port royal ยังไม่เจอ npc ใดๆ เพราะไม่เดิน
ทำไมไม่ทำอันนี้ด้วยล่ะ เว้นไว้ทำไม"* -- Port Royal's census ships only after
the player's FIRST ``TargetPosVital`` (i.e. after they have already walked),
not at login, unlike the warp path (``world_population_handoff``'s
``slot=after_teleport``), which composes and ships a destination scene's
roster immediately on arrival with no movement required.

WHY LOGIN CANNOT SIMPLY COPY THE WARP PATH TODAY, MEASURED IN ``runtime.py``
ITSELF (not this lane's guess -- read the comment at ``runtime.py:7544-7568``
and the field comment at ``runtime.py:8256-8265``, both already on ``main``
before this file existed).  The scene-1 census branch unconditionally arms
``self.population_indices`` with the composed roster's placement indices.
The FROZEN dispatcher
(``current/pf_login_game_server_v141.py:4395-4416``), reached for every
``TARGET_VITAL``/``CHOOSE_NPC`` frame that no ``lane_hooks`` responder
claims, loops that whole tuple and unpacks
``x, y, _z, _heading = self.last_target_pos`` for each entry -- WITH NO
``None`` CHECK.  So a login that armed ``population_indices`` before the
player's first move would leave EVERY session exactly one NPC click away
from an uncaught ``TypeError`` inside the listener thread
(``current/pf_login_game_server_v141.py:7440`` has no ``except`` around that
call), which is a dropped connection, not a slow one -- the MEASURED
uncaught crash ``runtime.py``'s own comment names, not a hypothetical this
lane invented to justify a flag.

HOW SCENE 14 CLOSED THE SAME GAP, AND WHY THIS FILE COPIES THE SHAPE RATHER
THAN THE CODE.  ``lane_hooks/lane_a_choose_npc_scene14.py`` answers scene
14's clicks through this exact registry
(``lane_hooks.choose_npc_responder``), and ``runtime.py``'s own guard
(``runtime.py:7088-7160``, already generic over scene id -- see its own
call, ``lane_hooks.scene_choose_npc_responder(self.foundation.selected.
position.scene_id)``) already routes ANY scene's ``TARGET_VITAL``/
``CHOOSE_NPC`` frame through a registered, ``production_allowed`` responder
INSTEAD of the frozen loop, with NO runtime.py change needed to cover a new
scene id -- only a new lane_hooks module.  That guard is why this file can
close the crash gap for scene 1 entirely from ``src/``, the same way scene
14's responder did, without a CORE-REQUEST for the click-routing half.  The
one runtime.py edit that is still required is elsewhere: WIDENING THE LOGIN
TRIGGER so ``population_indices`` gets armed before the first move at all
(see the CORE-REQUEST).  Scene 14's version declines outright when
``last_target_pos`` is ``None`` (see its own ``respond()``); this module
answers that case too -- see "WHY ``None`` IS ANSWERED, NOT DECLINED" below
-- because for scene 1 that is the EVERYDAY state the moment login ships an
eager census, not an edge case.

WHY ``None`` IS ANSWERED, NOT DECLINED.  Declining every click before the
first move would make an eagerly-shipped census look populated but
unresponsive -- every NPC visible, none clickable, until the player takes
one step -- which is a worse first five seconds than the walk it was meant
to remove.  Instead this responder computes a heading the same way the
ARRIVAL census itself already does for every actor
(``world_population.HEADINGS[placement_index & 3]``, four fixed cardinal
headings, the exact table ``world_population.py``'s ``_entry()`` already
uses) rather than inventing a "face the player" heading with no player
position to face -- see ``_answer_heading`` below.  Once ``last_target_pos``
IS known this responder turns to face the player, exactly like scene 14's.

WHY IT REUSES ``world_population``'s OWN TABLES INSTEAD OF RE-DERIVING THEM.
``world_port_royal_identity.resolve`` is the SAME identity filter
``world_population.census_order`` already applies, so the placements this
responder can answer for are, by construction, exactly the set
``population_indices`` can ever contain -- a placement index arriving here
that the identity filter would have dropped cannot happen from a real
composed generation, and this module still refuses it rather than trust
that invariant blindly (FAIL CLOSED below).

THE ADMISSION CHECK.  Reuses ``lane_a_scene_census.scene_is_open_to_players``
rather than re-deriving it, the same choice scene 14's responder makes and
for the same reason: one fail-closed reader for the registry key, not two.

WHY THE GATE STAYS CLOSED THIS ROUND.  Two independent reasons, either one
sufficient on its own:

1.  Nothing arms ``population_indices`` before a move for scene 1 yet (the
    login trigger in ``runtime.py`` still requires ``last_target_pos is not
    None`` for home -- see the CORE-REQUEST), so THE CRASH THIS FILE EXISTS
    TO PREVENT CANNOT HAPPEN TODAY.  Flipping this flag before that trigger
    widens changes nothing about that risk either way.
2.  Once armed, this module answers EVERY scene-1 click instead of the
    frozen path -- including clicks AFTER the player has already walked,
    which the frozen path answers correctly today (unlike scene 14, no
    known defect is on record for that case).  Swapping a working,
    long-lived production path for a brand-new one in the same round it was
    written, with no attended click parity check yet, is a bigger change
    than this round's evidence supports -- flip this flag in a LATER round,
    after ``tests/test_lane_a_choose_npc_scene1.py`` has been read by
    pf-adversary at least once and, ideally, after an attended click on
    Port Royal confirms parity.  See ``rounds/`` for this round's own
    account of why the two steps (runtime.py trigger widen, this flag) are
    kept apart on purpose.
"""
from __future__ import annotations

from typing import Any

from .. import lane_hooks
from .. import world_population
from .. import world_port_royal_identity as identity
from .lane_a_scene_census import scene_is_open_to_players

# See "WHY THE GATE STAYS CLOSED THIS ROUND" in the module docstring.  Flip
# only after the runtime.py login trigger widen (CORE-REQUEST) has landed
# AND this lane has reviewed test_lane_a_choose_npc_scene1.py with
# pf-adversary at least once more, ideally with an attended click-parity
# check on real Port Royal NPCs.
production_allowed = False

SCENE_N_ID = world_population.SCENE_ID


def _placements_by_index(legacy: Any) -> dict[int, Any]:
    """Placement index -> resolved placement, rebuilt per call.

    Filtered through ``world_port_royal_identity.resolve`` -- the SAME
    filter ``world_population.census_order`` applies -- so this table's
    keys are exactly the set ``population_indices`` can ever contain.  Not
    cached at module scope, the same non-caching convention
    ``lane_a_choose_npc_scene14.py``'s own helper uses and for the same
    reason: a pure read over a fixed frozen table, so the cost is a dict
    build per click, not a re-read of anything mutable.  Needs ``legacy`` to
    read the frozen placement table (``world_population.
    load_port_royal_placements``), so unlike scene 14's helper this cannot
    be a zero-argument function.
    """
    return {
        placement.placement_index: placement
        for placement in world_population.load_port_royal_placements(legacy)
        if identity.resolve(placement.template_id) is not None
    }


def _answer_heading(
    legacy: Any,
    placement: Any,
    last_target_pos: tuple[float, float, float, float] | None,
) -> float:
    """The heading the clicked actor turns to face.

    With a known player position this faces the player, exactly like scene
    14's responder (``legacy._heading_to_player``).  With none -- the
    everyday state for an eagerly-shipped login census before the first
    move, see "WHY ``None`` IS ANSWERED, NOT DECLINED" -- this falls back to
    the SAME fixed cardinal heading the arrival census itself already
    assigned that placement (``world_population.HEADINGS``), rather than
    inventing a facing with no position to derive it from.
    """
    if last_target_pos is not None:
        player_x, player_y = last_target_pos[0], last_target_pos[1]
        return legacy._heading_to_player(
            placement.x, placement.y, player_x, player_y,
        )
    return world_population.HEADINGS[placement.placement_index & 3]


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
    """Answer one ChooseNPC click for scene 1, or decline (see module doc).

    Keyword-only, same convention as ``lane_a_choose_npc_scene14.respond``,
    for the same reason: a future call site can grow arguments without
    breaking every registered responder at once.
    """
    if scene_id != SCENE_N_ID:
        return None
    if not scene_is_open_to_players(scene_id, scene_entry_registry):
        return None
    if population_indices is None:
        return None
    by_idx = _placements_by_index(legacy)
    for actor_identity in dict.fromkeys(chosen_identities):
        selected_idx = actor_identity - 0x2000 - 1
        if selected_idx not in population_indices:
            continue
        if selected_idx not in by_idx:
            # Fail closed: never invent a row this scene's own table does
            # not have.  Try the next named identity in this same frame
            # rather than giving up on the whole click.  Unreachable from a
            # real composed generation (population_indices is itself built
            # from this same identity filter), kept as a real refusal
            # rather than an assumption -- see the module docstring.
            continue
        entries = []
        omitted = 0
        for idx in population_indices:
            placement = by_idx.get(idx)
            if placement is None:
                omitted += 1
                continue
            resolved = identity.resolve(placement.template_id)
            if resolved is None:
                # Same fail-closed shape as above, for every OTHER member
                # of the composed roster, not only the clicked one.
                omitted += 1
                continue
            is_monster = idx == world_population.SHIPPED_MONSTER_INDEX
            hp = (
                legacy.V117_P30_EXACT_HP if is_monster
                else world_population.DEFAULT_HP
            )
            npc_attr_bytes = legacy.make_npc_attr(
                resolved.mobs_n_id, placement.actor_identity, scene_id, 0,
                resolved.outfit, current_hp=hp, max_hp=hp,
                basic_name=resolved.name,
            )
            attrs = [(legacy.NPC_ATTR, npc_attr_bytes)]
            if idx == selected_idx:
                heading = _answer_heading(legacy, placement, last_target_pos)
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
            f"omitted={omitted} "
            f"anchor={'known' if last_target_pos is not None else 'none'}",
        )
        return lane_hooks.ChooseNpcResponse(
            label=f"LANE_A_CHOOSE_NPC_SCENE{scene_id}_FACE_P{selected_idx}",
            pc=pc, frame=frame, delay=0.0, console_lines=console_lines,
        )
    return None


lane_hooks.choose_npc_responder(SCENE_N_ID)(respond)
