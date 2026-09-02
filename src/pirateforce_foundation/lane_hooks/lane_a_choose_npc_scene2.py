"""LANE-A (WORLD): the ChooseNPC responder for scene 2 (Prison Exile Island).

WHAT A PLAYER SEES BECAUSE OF THIS FILE, STATED FIRST -- AND "A PLAYER"
MEANS A SESSION THAT REACHED SCENE 2, WHICH TODAY MEANS A GM (pf-adversary
D11).  ``scenarios/world_travel_gates_001.json`` holds exactly two gates
(1 <-> 278), nothing in this tree seeds a stored character on scene 2, and
the only live door is GM ``/warp 2``.  Scene 2 IS ``persist_position_
allowed``, so a session that has been warped there once lands there on
later logins.  Inherited from the census, not introduced here, and stated
because the sentence below would otherwise be broader than the tree.
Yesterday a session standing on Prison Exile Island saw all 97 of its
people -- the arrival census has shipped them since CORE-REQUEST-021 --
and clicking any of them did nothing at all: no frame went back, no line
was printed, and the client was left exactly as it was.  Scene 2 was the LAST
scene in this project that
ships a census and answers no click (scene 1 is the frozen path's own, and
scenes 3-11, 14 and 130 were opened by rounds `326kf4`, `gwwpmr` and
`n8fq3w`).  After this file: the clicked actor turns to face the player and
the whole island is re-sent with names, levels and HP, through the same
frozen wire shapes Port Royal already uses.  **97 more clickable actors:
870 across the twelve scenes this lane's own responders answer for** -- the
ten roster islands' 692, Hell Volcano's 81, and these 97, re-derived from
the live registry rather than added up from round files (Port Royal is not
in that count: scene 1's clicks are the frozen path's own).  870 is a
CEILING, not a promise (pf-adversary D12): the ten roster responders answer
over ``population_indices`` intersected with their table, so a session whose
census armed fewer indices reaches fewer.  This scene's own 97 is not a
ceiling -- it has no index space to intersect with.  All three numbers are
pinned by ``tests/test_lane_a_choose_npc_scene2.py`` so they cannot rot
quietly the way "789 across eleven scenes" did inside this very round.

The evidence layer here is WIRE/DB only.  ``GT-214`` is the attended ticket
that decides it on a real client, and nothing in this file stands in for it.

WHY SCENE 2 IS NOT IN ``lane_a_choose_npc_roster_scenes``'s TABLE, WHICH IS
THE FIRST QUESTION A READER OF THAT FILE WILL HAVE.  That module's own
docstring gives the reason it had when it was written -- scene 2 has no
``world_bg0002_identity`` module, so there is no ``shippable_placements()``
for its table-driven responder to read.  That is still true, and this file
does not add one: it reads ``scene2_prison_exile_tables`` directly, the same
table ``world_population_bg0002`` composes the arrival census from.  Two
further differences make scene 2 a sibling of scene 14 rather than of the
ten table scenes, and either one alone would have kept it out of that table:

  * **Scene 2 never arms ``population_indices``, on purpose and by
    someone else's decision.**  ``runtime.py``'s bg0002 census arm says so
    in its own words ("Deliberately NOT set here: population_indices,
    population_refresh_anchor, world_census_indices, npc_idle_action_sent
    ... bg0002 has no click-dispatch system wired yet").  Every other
    responder in this lane treats ``population_indices is None`` as a
    DECLINE -- for them it means the census has not armed membership yet.
    For scene 2 it is the permanent, designed state, so this responder
    derives membership from the scene's own table instead.  That is safe
    here for a reason that is measured rather than assumed: the bg0002 arm
    composes with ``COUNT_SOURCE_FULL_ROSTER``, so the census that shipped
    is ALWAYS the whole 97-row known table, never a subset a caller chose.
    ``tests/test_lane_a_choose_npc_scene2.py`` drives the real builder and
    asserts the two sets are equal rather than trusting this paragraph.

  * **Twelve of the 97 are spliced hostile at arrival** (``mob_census_
    hostility.hostile_override_for_scene_id``, LANE-B's CORE-REQUEST
    20260829_1600), so a civilian body rebuilt for all 97 would revert that
    splice on the wire the moment anyone was clicked -- the exact defect
    chief's pf-adversary run caught on scene 14 (round R274) and the reason
    that scene has its own file too.  This module composes those 12 through
    ``field_mobs.hostile_npc_attr``, the same encoder the arrival splice
    ends in.

WHY THE WHOLE ISLAND IS RE-SENT AND NOT ONLY THE CLICKED ACTOR.  ``RE-092``
proved replace-by-omission AT THE ACTOR-SET LEVEL: a collection the client
applies replaces the set, so a one-entry answer would delete the other 96
from the screen.  This is also why the 12 hostile rows cannot simply be left
out of the answer to avoid the HP question below -- omitting them is not
"leave them alone", it is "remove them".

THE HP GAP, NAMED RATHER THAN HIDDEN [LANE-A ASSUMPTION - COO ASKED
20260902_1736].  The arrival census composes the 12 hostile bodies through a
ledger (``runtime.py`` passes ``ledger=self.mob_combat_ledger`` after
``_sync_combat_scene_state()``), so a wounded monster arrives wounded.  This
responder is handed no ledger: ``runtime.py``'s ChooseNPC call site passes
``legacy``, ``chosen_identities``, ``population_indices``,
``last_target_pos``, ``scene_id`` and ``scene_entry_registry``, and nothing
else.  So on a click TODAY the 12 are re-sent at their table ceiling, and a
monster the player has already wounded redraws with a full bar until the
next combat frame corrects it.

    AND THE FRAME LANDS CLOSER TO THE FIGHT THAN THAT SENTENCE SOUNDS
    (pf-adversary D3).  ``docs/FUNCTIONAL_COVERAGE.json`` records that a
    real client click produces "TargetVital plus an embedded ChooseNPC" --
    the claimed family -- so this is not only an idle click on a
    townsperson: it is the frame a player sends AT the monster he is
    fighting, and the heal it draws is drawn at the moment he is looking at
    that monster's bar.  The ledger that would prevent it is not missing
    from the server either: ``_sync_combat_scene_state()`` has already
    opened it for ``Bg0002`` before the click arrives.  It is one keyword
    away, at a call site this lane does not own.

Three things about that, each stated as what it is:

  * It is NOT new and it is NOT this scene's alone -- ``lane_a_choose_npc_
    scene14.respond`` composes its own 12 the same way (``current_hp=
    hostile_mob.max_hp``), and has since round `yfbqmg`.
  * It is a WIRE-LAYER statement.  The server's ledger is untouched by a
    click; only the client's picture of HP is re-stated.
  * It has a one-line fix that is not this lane's to make, and this file is
    already written for it: :func:`respond` accepts an optional
    ``mob_combat_ledger`` keyword and uses it when it is there.  The
    CORE-REQUEST (``pf_bridge/notes_to_chief/20260902_1735_LANE-A-CORE-
    REQUEST-choosenpc-call-site-passes-the-combat-ledger.md``) asks chief
    for ``mob_combat_ledger=self.mob_combat_ledger`` on that call, which
    every other responder ignores through its own ``**_ignored``.
    ~~The day it lands, wounded monsters stay wounded here with no further
    change in this lane~~ -- STRUCK, ROUND ``4uztfj``: chief WROTE that line,
    measured it, and withdrew it, because the dead guard this file carried
    refused the whole click and one kill silenced the scene (letter
    ``20260902_1918``).  The guard was narrowed that round
    (``COO-DECISION 20260902_1945``), scene 14's responder was moved with it
    in the same commit, and the promise is true again as written -- but it
    took a change in this lane, not none, and the sentence is kept so nobody
    re-derives the withdrawn version.  ``tests/test_lane_a_choose_npc_
    scene2.py`` and ``tests/test_lane_a_click_after_a_kill.py`` drive that
    path with a real ledger, the second one after a real kill.  THAT PROMISE HAS ONE CONDITION, NAMED
    HERE RATHER THAN DISCOVERED THEN (pf-adversary D9):
    ``_current_hp_of`` asks the ledger PER IDENTITY inside a bare
    ``except``, where ``mob_census_hostility.hostile_override_for_scene_id``
    asks ``mob_ledger_admission.ledger_for_scene`` first, because a
    foreign-scene ledger is safe only for an empty roster.  Measured today:
    scene 1's and scene 2's rosters share NO identity, so a foreign ledger
    raises per row and answers the ceiling.  If a future scene pair does
    collide, this function would quietly serve another scene's HP -- or
    another scene's 0-HP row would turn a scene-2 click on THAT identity
    into ``clicked_body_is_dead_needs_a_mob_death_body_*``, a dropped click
    caused by a kill somewhere else -- one click now, not the whole scene.  The day the keyword lands, this should go through
    the same admission the census uses.

WHAT CLAIMING THIS SCENE COSTS, RE-CHECKED BECAUSE runtime.py TOLD THIS LANE
TO.  The guard's own comment (``runtime.py``, "TWO gaps a lane MUST read")
warns that a claimed scene never runs ``super().dispatch(parsed)`` for that
one frame, so v141's unconditional TARGET_VITAL arming
(``action_target_last_identity`` / ``_last_kind`` /
``p30_action_target_armed``, v141:3788-3816) does not happen -- and it names
the case to re-check before flipping a flag: "a future scene whose players
use melee/skill targeting on the SAME connection a responder claims".
Scene 2 IS that scene: it is where LANE-B's monsters live and where its kill
harness fights.  Re-checked here, not inherited:

  * The ONLY consumer of that arming is ``exact_p30_target``
    (v141:3818-3862), and its match requires ``self.population_indices is
    not None and V112_MONSTER_INDEX in self.population_indices``.  Scene 2
    never arms ``population_indices`` (the bg0002 arm, quoted above), so
    ``exact_p30_target`` is already False on every scene-2 frame, with this
    file or without it.  Nothing that works today stops working.
  * ``ACTION_VITAL`` -- the frame that actually attacks -- is NOT in the
    claimed family (``TARGET_VITAL``/``CHOOSE_NPC``), so LANE-B's combat
    dispatch is not on the path this file changes at all.
  * ``tests/test_lane_a_choose_npc_scene2.py`` drives a real TARGET_VITAL
    through the real dispatcher on scene 2 and pins both halves, so a later
    round that arms ``population_indices`` for scene 2 cannot re-open this
    silently.

The second gap the guard names is unchanged and inherited as-is: a
multi-select click is answered with ONE frame, because ``respond`` returns
at most one ``ChooseNpcResponse``.  Pinned below by the same test file.

WHAT ELSE IS IN THIS FRAME BESIDES THE ACTORS, AND IT IS NOT NOTHING
(pf-adversary D2).  ``legacy.make_runtime_remote_actors`` writes the derived
change mask as ``0B 02`` -- the ground-list bit CLEAR -- and LANE-B's
``mob_loot`` reads clear as "there is no pool", which its own comment says
the client's reconciler is read (Codex, STATIC, not observed) as treating
like "clear everything".  That lane built
``mob_loot.preserve_ground_in_runtime_res_remote_actors`` for exactly this
carrier and wired it to bar/dying/dead.  This module does NOT use it, and
the reason is the fence, not an oversight: the preserve shape carries
``[ASSUMPTION OF LANE B - AWAITING COO/RE CONFIRMATION]`` about field order,
"a frame the client rejects here costs the actors in THAT frame", and
COO-DECISION 0646/1044 keeps it out of the arrival census until an attended
round has seen one accepted.  Swapping it in here would bet all 97 actors of
every click on an unconfirmed shape.

    SO THE INTERACTION IS NAMED INSTEAD, and it is a real one: on the one
    scene where kills drop, a click -- including the click that targets the
    next monster -- sends a frame whose derived mask says the ground list is
    absent.  If the static reading is right, that is the player's loot.  The
    mask value is MEASURED here; what a clear bit does to a client is NOT.
    Raised with COO and LANE-B in
    ``pf_bridge/notes_to_chief/20260902_1806_LANE-A-TO-LANE-B-*`` rather
    than decided by this lane alone, and ``GT-214`` carries a step that
    looks at the ground after a click.

AND ONE ASYMMETRY THIS FILE'S OWN ARGUMENT RESTS ON (pf-adversary D6).  The
whole island is re-sent because ``RE-092`` says omission DELETES at the
actor-set level -- and in the same frame 96 of the 97 entries carry no
MovementAttr at all, which relies on omission MEANING "leave alone" at the
attribute level, since ``make_npc_attr`` carries no position.  Both cannot
be read off one RE.  ``CLIENT_RE_QUEUE.md`` says so itself about the
mask-level question ("still unmeasured -- do not jump to a conclusion").
The shape is inherited from all three sibling responders and is NOT new
here; what is new is that this docstring leans on RE-092 in one direction,
so it must also say where it is leaning on the converse.

THE ONE THING THIS RESPONDER CAN DO THAT ITS SIBLINGS CANNOT, WRITTEN DOWN
BECAUSE IT IS A REAL WEAKENING AND NOT A FEATURE.  Every sibling declines
while ``population_indices is None``, which means none of them can answer
before the arrival census has COMMITTED.  This one does not read that field
at all, so in principle it can answer a click in a session whose census
REFUSED (``world_census_refused``, set when the builder raises) -- a state
this responder cannot see, because the call site does not pass it.  What
bounds it, measured rather than hoped: the refusal is a raise out of
``world_population_bg0002.build_bg0002_population`` over the same frozen
table and the same encoders this module composes with, so a table or
encoder drift that refuses the census raises here too -- and ``runtime.py``
wraps this call in its own ``except``, appends
``scene_choose_npc_responder_failed_<type>`` and sends no bytes.  The
residual is a refusal whose cause is NOT in the shared path (an anchor the
registry cannot answer for is the live example): there, a click would be
answered for a scene whose crowd was never sent.  Nobody has seen that
state; it is named here so a later round can close it with one more
keyword at the call site (the same one the HP gap needs) rather than
discover it.

FAIL CLOSED, EVERY REFUSAL NAMED.  A click this module cannot answer
honestly gets no frame, never an invented one, and every refusal prints
``LANE_A_CHOOSE_NPC_SCENE2_DECLINED reason=<reason>`` to stderr -- the
discipline round `gwwpmr` added to the sibling responder (pf-adversary D7)
after measuring that a silent decline and a build with no responder look
identical to a tester.
"""
from __future__ import annotations

import sys
from typing import Any

from .. import field_mobs
from .. import lane_a_click_hp
from .. import lane_hooks
from .. import scene2_prison_exile_tables as tables
from .. import world_census_level
from .lane_a_scene_census import scene_is_open_to_players

# WHY THIS IS True.  Nothing about this flag opens a door that was shut:
# scene 2's login door is already open (``scene_is_open_to_players`` answers
# True on every click below).  HOW it was open, corrected after
# pf-adversary D7 measured the first draft of this comment false: scene 2's
# registry row carried NO ``login_entry_allowed`` key at all, and
# ``world_scene_travel``'s ``DEFAULT_LOGIN_ENTRY_ALLOWED`` supplied the
# True -- so "measured in the registry" was citing the registry for a value
# it did not hold, and ``scene_is_open_to_players``'s "fail-closed in every
# direction that is not an explicit yes" was not true of a silent row.  This
# round wrote the key down (``scenarios/world_scene_registry_001.json``,
# with the reason in that row's own ``status``): the door is unchanged, the
# citation is now true, and the ``registry_door_shut`` refusal below can be
# driven against a registry that really carries the key.  The rest of the
# safety case is unchanged: scene 2's 97-actor census already ships on
# arrival on every flagless boot, and this scene arms no index space for a
# scene-blind reader to be reached through -- the risk round `gwwpmr` had to
# weigh for the nine table scenes
# does not exist here, because ``population_indices`` stays ``None``.  What
# flipping this does is claim the TARGET_VITAL/CHOOSE_NPC family for scene
# 2, which is re-checked in this module's docstring against the two gaps
# ``runtime.py``'s guard names.
production_allowed = True

SCENE_N_ID = tables.SCENE_N_ID
# The folder this scene's monsters are mined from, and the tag its own
# ledger carries.  Read from ``field_mobs`` rather than typed, and with a
# literal only as the fallback the day that table stops naming this scene
# -- which is exactly what it does for scene 14 (measured), and what made
# the ledger admission refuse everything there until this constant existed.
SCENE_FOLDER = field_mobs.scene_for_scene_id(SCENE_N_ID) or "Bg0002"

#: The wire shapes, carried from the sibling responders rather than
#: re-derived: actor type 4 is the NPC style every roster entry in this
#: project uses, scene sequence 0 is what ``world_population_bg0002``
#: sends (``SCENE2_SEQUENCE``), and mask 0x03 is the turn-to-face mask.
_NPC_STYLE_ACTOR_TYPE = 4
_SCENE_SEQUENCE = 0
_FACE_MOVEMENT_MASK = 0x03


def _placements_by_index() -> dict[int, Any]:
    """Placement index -> resolved placement, rebuilt per call.

    Not cached, the same trade and the same reason the sibling responders
    state: ``load_known_placements()`` is pure over a frozen table, so the
    cost is one dict build per click rather than a re-read of anything that
    can change under us.
    """
    return {p.placement_index: p for p in tables.load_known_placements()}


def _hostile_mobs_by_placement_index() -> dict[int, Any]:
    """Placement index -> ``field_mobs.FieldMob`` for the 12 rows the
    arrival census splices hostile in this scene.

    READ THROUGH ``roster_for_scene_id`` RATHER THAN A SECOND COPY, because
    that is the exact call ``mob_census_hostility.hostile_override_for_
    scene_id`` makes for the arrival splice.  A private list here could
    agree with itself while the census composed something else -- the shape
    of defect this lane has now shipped twice (a constant pinned against
    itself, round `gwwpmr` D2).
    """
    return {
        mob.placement_index: mob
        for mob in field_mobs.roster_for_scene_id(SCENE_N_ID)
    }


def _current_hp_of(mob: Any, ledger: Any) -> tuple[int | None, bool]:
    """``(hp, hp_came_from_the_ledger)``.

    The HP is this monster's as the ledger knows it, its table ceiling, or
    ``None`` for a monster the ledger says is DEAD.  The FLAG is what the
    console line reports, and it exists because reporting the argument
    instead of the outcome is a lie a tester cannot see through
    (pf-adversary D8): a ledger that answers for no row on this scene --
    another scene's, or an empty one -- makes every one of the 12 bodies
    carry its ceiling while ``hp=ledger`` would have said otherwise.  The
    flag is per row and the caller counts them, so the line reports what
    was actually read.

    ``ledger`` is whatever the call site passed -- today that is ``None``
    (see THE HP GAP in the module docstring), tomorrow it may be the
    session's ``mob_combat_ledger``.  Reading it is fail-SAFE rather than
    fail-loud: a ledger that belongs to another scene, or that has no row
    for this identity, answers the ceiling, which is exactly what a click
    sends today.  A raise here would turn a redrawn HP bar into a dropped
    click.

    ~~A DEAD ROW IS THE ONE CASE THAT REFUSES INSTEAD, and it refuses in
    the caller (``respond`` declines the whole click by name).~~ CORRECTED,
    ROUND ``4uztfj``, AND THE OLD SENTENCE IS KEPT BECAUSE IT DESCRIBED A
    MEASURED DEFECT: "the whole click" turned out to mean "every click in
    the scene until the player reconnects", which chief drove on the real
    dispatcher (letter ``20260902_1918``).  ``COO-DECISION 20260902_1945``:
    a dead row refuses ONLY the click that named it, and any other dead
    body in the same frame is sent at its ceiling, counted and named.  The
    debt that ceiling represents is written down in ``lane_a_click_hp``.
    ``0`` still cannot be sent as an alive body's HP -- ``mob_death``
    composes a corpse through a shape this responder does not have.
    """
    # ONE AUTHORITY SINCE ROUND `4uztfj` (COO-DECISION 20260902_1945): the
    # rule now lives in ``lane_a_click_hp`` because scene 14's responder
    # needs the identical one, and the round chief measured had the two
    # answering DIFFERENTLY on the same input.  This wrapper stays so this
    # module's own tests and comments keep their name for it.
    return lane_a_click_hp.current_hp_of(mob, ledger)


def _note(token: str, detail: str) -> None:
    """Print one named OBSERVATION to stderr -- never a refusal.

    THREE TOKENS, AND THE SPLIT IS THE ANSWER TO A QUESTION pf-adversary
    ASKED THIS ROUND: one ChooseNPC packet can name SEVERAL actors
    (``v141`` documents "TargetVital followed by one or more ChooseNPC
    records"), so "the click was refused" and "that identity was refused"
    are different statements and used to share one token.

    * ``..._DECLINED`` -- THE PACKET got no frame at all.
    * ``..._IDENTITY_REFUSED`` -- one named identity was skipped; another
      identity in the SAME packet may still be answered.
    * ``..._DEAD_BODY_AT_CEILING`` -- an observation about a body inside a
      frame that IS being sent.

    Measured before the split: a packet naming a corpse and a civilian
    printed ``..._DECLINED`` and then ``..._ANSWERED``, so a tester
    grepping the refusal token read "the click was refused" about a click
    that was answered.
    """
    print(
        lane_hooks.console_safe(
            f"LANE_A_CHOOSE_NPC_SCENE{SCENE_N_ID}_{token} {detail}"
        ),
        file=sys.stderr,
    )
    return None


def _decline(reason: str) -> None:
    """Print one named refusal to stderr and return nothing.

    Written through ``lane_hooks.console_safe`` because the bridge console
    is cp874 and a raw ``print`` of a non-encodable string there raises
    inside the listener thread.
    """
    print(
        lane_hooks.console_safe(
            f"LANE_A_CHOOSE_NPC_SCENE{SCENE_N_ID}_DECLINED reason={reason}"
        ),
        file=sys.stderr,
    )
    return None


def respond(
    *,
    legacy: Any,
    chosen_identities: tuple[int, ...],
    population_indices: tuple[int, ...] | None = None,
    last_target_pos: tuple[float, float, float, float] | None,
    scene_id: int = SCENE_N_ID,
    scene_entry_registry: Any = None,
    mob_combat_ledger: Any = None,
    **_ignored: Any,
) -> "lane_hooks.ChooseNpcResponse | None":
    """Answer one ChooseNPC click for scene 2, or decline.

    Keyword-only, the same convention every registered responder uses, so a
    future call site can grow arguments without breaking all of them at
    once.  ``chosen_identities`` is exactly what
    ``legacy.extract_choose_npc_identities(parsed)`` returns, so a test
    drives this with no wire bytes at all.

    ``population_indices`` IS ACCEPTED AND DELIBERATELY NOT READ -- see the
    module docstring: on this scene it is ``None`` forever by someone else's
    design, and membership comes from the table the arrival census composed
    from.  It is kept in the signature (with a default, unlike the
    siblings) so the call site's keyword keeps landing somewhere named
    rather than in ``**_ignored``, where a reader would have to guess
    whether it was meant.
    """
    if scene_id != SCENE_N_ID:
        # The call site keys the registry by the player's own scene, so this
        # cannot happen from production today.  Kept for the reason the
        # siblings keep it: a responder that trusts its caller to have
        # looked up the right scene delivers one island's crowd into
        # another.
        return _decline(f"wrong_scene_this_responder_is_{SCENE_N_ID}")
    if not scene_is_open_to_players(scene_id, scene_entry_registry):
        return _decline("registry_door_shut")
    if last_target_pos is None:
        # The pre-movement click.  ONE STEP fixes it: the heading of the
        # clicked actor is computed from the player's own position, and
        # inventing one would be the kind of made-up coordinate the
        # arrival-point rule forbids.  ``GT-214`` carries the step as a
        # numbered instruction for that reason.
        return _decline("no_player_position_walk_one_step")
    by_idx = _placements_by_index()
    hostile_by_idx = _hostile_mobs_by_placement_index()
    membership = tuple(sorted(by_idx))
    player_x, player_y = last_target_pos[0], last_target_pos[1]
    # THE LEDGER IS ADMITTED FOR THIS SCENE BEFORE IT IS READ, ONCE PER
    # PACKET (pf-adversary D4, round `4uztfj`, MEASURED): scene 2's and
    # scene 14's hostile rosters both hold identity 0x2058, so a stale
    # scene-14 ledger made a click on scene 2's LIVING placement 87 refuse
    # itself.  ``lane_a_click_hp.ledger_for_this_scene`` asks the same
    # ``mob_ledger_admission`` the census path asks; a ledger that is not
    # this scene's answers None, which means "compose without consulting
    # HP" -- the ceiling, exactly as a ledger-less boot does today.
    admitted_ledger = lane_a_click_hp.ledger_for_this_scene(
        SCENE_N_ID, mob_combat_ledger,
        field_mobs.roster_for_scene_id(SCENE_N_ID),
        scene_folder=SCENE_FOLDER,
    )
    if mob_combat_ledger is not None and admitted_ledger is None:
        _note(
            "LEDGER_NOT_ADMITTED",
            "reason=not_this_scenes_ledger hp=ceiling",
        )
    refused_identities = 0
    for actor_identity in dict.fromkeys(chosen_identities):
        selected_idx = actor_identity - 0x2000 - 1
        if selected_idx not in by_idx:
            # Fail closed: never invent a row this scene's own table does
            # not hold.  Try the next named identity in this same frame
            # rather than giving up on the whole click -- and SAY SO, one
            # line per dropped identity (pf-adversary D13): on a
            # multi-select frame whose first identity is unknown and whose
            # second is not, the drop used to be completely silent while
            # "EVERY REFUSAL NAMED" was stated absolutely.
            _note(
                "IDENTITY_REFUSED",
                f"reason=placement_not_in_this_scenes_table "
                f"placement={selected_idx} identity=0x{actor_identity:04X}",
            )
            refused_identities += 1
            continue
        # THE DEAD GUARD, ON THE CLICKED BODY AND NOTHING ELSE
        # (COO-DECISION 20260902_1945, correcting 20260902_1843).  It used
        # to sit inside the 97-actor loop below and ``return`` -- so the
        # first hostile row the ledger reported dead refused the WHOLE
        # click, and chief measured what that means on the real dispatcher:
        # kill one monster and every click in scene 2 goes silent until the
        # player reconnects (the death is pulled back out of
        # ``mob_death_register`` on every re-entry).  A click on a corpse
        # is refused BY NAME; a click on anyone else is answered.
        clicked_hostile = hostile_by_idx.get(selected_idx)
        if clicked_hostile is not None:
            clicked_hp, _clicked_from_ledger = _current_hp_of(
                clicked_hostile, admitted_ledger)
            if clicked_hp is None:
                # NAMES THE PLACEMENT THE PLAYER ACTUALLY CLICKED, which
                # the old line did not: it printed the first dead hostile
                # in ``sorted(by_idx)`` order (``placement_50`` for a click
                # on placement 0), sending a tester to look for a bug at a
                # placement that had nothing wrong with it (chief's letter
                # 20260902_1918, item 4.1, measured).
                _note(
                    "IDENTITY_REFUSED",
                    "reason=clicked_body_is_dead_needs_a_mob_death_body "
                    f"placement={selected_idx} "
                    f"identity=0x{actor_identity:04X}",
                )
                refused_identities += 1
                continue
        entries = []
        hostile_sent = 0
        hostile_from_ledger = 0
        hostile_wounded = 0
        dead_bodies_at_ceiling = 0
        for idx in membership:
            placement = by_idx[idx]
            hostile_mob = hostile_by_idx.get(idx)
            if hostile_mob is not None:
                # This placement is one of the 12 the arrival census
                # splices hostile.  A civilian body here would revert that
                # splice on the wire the moment ANY of the 97 was clicked
                # -- the confirmed scene-14 defect, in this scene's
                # numbers.
                current_hp, from_ledger, was_dead = (
                    lane_a_click_hp.hp_for_a_body_that_is_not_the_click(
                        hostile_mob, admitted_ledger)
                )
                hostile_from_ledger += int(from_ledger)
                if was_dead:
                    # A body the ledger says is dead that is NOT the one
                    # clicked.  The frame is still owed to the player, this
                    # responder has no corpse to put in it (the call site
                    # passes no death register), and omitting the row would
                    # DELETE the actor from the client's set (``RE-092``).
                    # So it carries the ceiling -- which is exactly what
                    # every click on ``main`` sends for every hostile body
                    # today -- and it is COUNTED AND NAMED rather than
                    # left for someone to notice as a monster standing back
                    # up.  See ``lane_a_click_hp``'s own docstring for the
                    # ticket that pays this off.
                    dead_bodies_at_ceiling += 1
                    # NOT ``_decline``: that prints ``..._DECLINED``, and a
                    # tester who greps that token reads it as "the click was
                    # refused" -- which this is not.  The click IS answered;
                    # one body in the answer is a corpse wearing its ceiling.
                    # A refusal token on an answered click is exactly the
                    # kind of console line that sends a reader hunting the
                    # wrong bug (chief's item 4.1, in a different shape).
                    _note(
                        "DEAD_BODY_AT_CEILING",
                        f"placement={idx} "
                        f"identity=0x{hostile_mob.actor_identity:04X}",
                    )
                elif current_hp < hostile_mob.max_hp:
                    hostile_wounded += 1
                hostile_sent += 1
                # SCENE 1, NOT SCENE 2, AND THAT IS NOT A TYPO -- MEASURED
                # THIS ROUND.  The arrival splice composes these 12 bodies
                # through ``mob_death.full_roster_override`` ->
                # ``field_mobs.hostile_actor_entry``, and NEITHER of them
                # takes a scene id from the call site: both fall through to
                # ``field_mobs.SCENE_ID`` (1) and ``SCENE_SEQUENCE`` (0).
                # So the hostile bodies the client is holding for scene 2
                # right now carry scene id 1, while the 85 civilians beside
                # them carry 2 (``world_population_bg0002._entry`` passes
                # ``SCENE2_N_ID``).  Driven, not read: with ``scene_id=2``
                # the body this responder builds is NOT a substring of the
                # entry the real override produced; with the defaults it is.
                #
                # This responder therefore sends what ARRIVED, deliberately,
                # because a click that re-states a field differently from
                # the census is exactly the class of defect scene 14's own
                # file exists to stop -- and what that field means to the
                # client is UNMEASURED, so this is not the place to change
                # it on a guess.  The mismatch itself is a real finding and
                # is reported (round file `A_20260902_1740_cu1il6_*`, and
                # the same defaults are used by scene 14's responder's
                # ARRIVAL path while that responder passes 14 -- so it has
                # the mismatch this one does not).  If a later round proves
                # the scene id should be 2 here, the fix belongs in the
                # ARRIVAL composer first and in this line second, never in
                # this line alone.
                npc_attr_bytes = field_mobs.hostile_npc_attr(
                    legacy, hostile_mob, current_hp=current_hp,
                    scene_id=field_mobs.SCENE_ID,
                    scene_sequence=field_mobs.SCENE_SEQUENCE,
                )
            else:
                # LEVELED, NOT BARE, and through the same encoder the
                # arrival census used for this exact row
                # (``world_population_bg0002._entry``): a plain
                # ``legacy.make_npc_attr`` would re-send all 85 civilians
                # with no level and silently revert round `7ste68` on the
                # wire.  ``placement.level`` is the mined
                # ``MOBS.n_LEVEL_MIN`` floor, NOT ``level_max`` -- the same
                # choice, for the same stated reason, that the arrival
                # composer makes.
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
                    level=placement.level,
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
        pc, frame = legacy.make_runtime_remote_actors(entries)
        # ``hp=`` NAMES THE GAP ON EVERY ANSWER, not in a comment a tester
        # will never read: ``ceiling`` says the 12 hostile bodies in this
        # frame carry their table HP because no ledger reached this
        # responder, so a redrawn full bar on a wounded monster is this
        # line's doing and not a combat bug.
        # ``wounded=`` IS THE NUMBER THAT MAY BE QUOTED AS EVIDENCE, and
        # ``hp=ledger`` IS NOT (COO-DECISION 20260902_1945, closing chief's
        # item 4.3): a freshly opened ledger with no combat in it at all
        # prints ``hp=ledger from_ledger=12`` with all twelve bodies at
        # their ceiling, so that token proves only that a ledger was
        # readable.  ``wounded=`` counts the bodies whose HP ON THE WIRE is
        # BELOW the table ceiling, and ``dead_at_ceiling=`` counts the
        # corpses this responder cannot compose yet.
        console_lines = (
            f"LANE_A_CHOOSE_NPC_SCENE{SCENE_N_ID}_ANSWERED "
            f"placement={selected_idx} visible={len(entries)} "
            f"hostile={hostile_sent} "
            f"hp={'ledger' if hostile_from_ledger else 'ceiling'} "
            f"from_ledger={hostile_from_ledger} "
            f"wounded={hostile_wounded} "
            f"dead_at_ceiling={dead_bodies_at_ceiling}",
        )
        return lane_hooks.ChooseNpcResponse(
            label=(
                f"LANE_A_CHOOSE_NPC_SCENE{SCENE_N_ID}_FACE_P{selected_idx}"
            ),
            pc=pc, frame=frame, delay=0.0, console_lines=console_lines,
        )
    if refused_identities:
        # TRUE REASON, not the generic one (pf-adversary D7): every named
        # identity WAS one this scene can answer for -- each was refused
        # for its own reason, already printed above with its placement.
        return _decline(
            f"every_named_identity_refused count={refused_identities}")
    return _decline("no_named_identity_this_scene_can_answer")


lane_hooks.choose_npc_responder(SCENE_N_ID)(respond)
