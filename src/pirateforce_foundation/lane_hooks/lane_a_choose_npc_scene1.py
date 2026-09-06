"""LANE-A (WORLD): the ChooseNPC responder for scene 1 (Port Royal / bg0001).

WHAT A PLAYER SEES BECAUSE OF THIS FILE, STATED HONESTLY AND FIRST.
Nothing yet.  ``production_allowed`` below is ``False`` on purpose -- and
from round ``zqmosn`` it is False for a MEASURED reason, not the
second-hand one it carried before.  Read "WHAT THE FLIP WOULD COST TODAY" before
reading anything else in this module as live, and before flipping the
flag.

WHAT THE FLIP WOULD COST TODAY (round ``zqmosn``, driven through
``runtime.make_state_class`` itself -- the same connection, the same
click, the responder registered in one run and withdrawn in the other;
``tests/test_lane_a_choose_npc_scene1.py``'s
``TheGateStaysClosedForAMeasuredReasonTests`` pins it):

    click        on main today                       with this responder
    ---------    --------------------------------    -------------------
    P1           face 14,142 B                       face 14,142 B
                 + V98_NPC_CONVERSATION_DEFAULT 34 B   (LOST)
                 + Columbus quest 44 B               + Columbus quest 44 B
    P91          face 14,142 B                       face 14,142 B
                 + TRADE_ZOOM_STORE5 48 B              (LOST)
    P30          (nothing -- refused by name)        face 14,142 B (a gain)

    READ THAT TABLE WITH ROUND ``yjjtyn``'s AMENDMENT, WHICH CHANGES ONE
    ROW AND NOT THE VERDICT.  The P1 row's "(LOST)" is now conditional:
    this responder COMPOSES that talk trigger into ``extra_actions``, so
    the day chief's one line queues that field, an ordinary click keeps
    it.  P91's "(LOST)" is unchanged and still measured -- the trade-zoom
    is once-per-session state no argument reaches this responder carries
    (step 2 below).  Until BOTH the chief line and the shop latch land,
    the flip still costs the town its shop, so the gate below stays
    False.

THE FACE FRAME IS ALREADY AT PARITY, AND THAT IS NOT ENOUGH.  Its 14,142
bytes are byte-identical to ``world_face_frame.build_face_state``'s, which
is what runtime.py really sends today (``rebuild_face_actions``,
``runtime.py:10410-10414`` -- re-derived at HEAD this round,
the old ``9103`` pin had rotted -- gated on the census's own
``world_census_identity_resolved``).  An earlier draft of this round read
that equality as "the flip is free" and was wrong: THE ANSWER TO A CLICK
IS NOT ONE ACTION.  The frozen loop also emits the empty NPCConversation
collection that is the client's authentic default-talk trigger (v141's own
comment above ``make_v98_conversation_face_state``) and, for the shop
trigger, the trade-zoom action.  ~~A ``ChooseNpcResponse`` carries ONE
``pc``/``frame`` pair, so this responder cannot emit them~~ -- STRUCK,
ROUND ``yjjtyn``: it carries ``extra_actions`` now, and this responder
fills it with the talk trigger for an ordinary townsperson's click.  The rest of the
sentence still stands and is why the gate has not moved: the call site
sets ``actions = []`` on a decline with NO fallback to the frozen loop,
NOTHING READS ``extra_actions`` YET (that line is chief's -- see step 1
below), and the shop's trade-zoom is still not composable from here at
all.  So flipping this flag today would still leave every NPC in the town
unable to talk and the shop unable to open.

WHAT MUST LAND BEFORE THIS FLAG MOVES (steps 1-3 in this order; 4-7 in
any order, all of them before the flip):
1.  ``ChooseNpcResponse`` becomes a COLLECTION of actions rather than one
    pair.  NOT STRUCK, AND THE UN-STRIKING IS DELIBERATE (pf-adversary
    ``yjjtyn`` D7): this file's convention is that struck text means
    SHIPPED, and half of this item is not.  LANE HALF DONE, ROUND
    ``yjjtyn``, ADDITIVELY: the type gained
    ``extra_actions`` (default ``()``, so every responder and the call
    site keep their present meaning) -- read that field's own paragraph in
    ``lane_hooks/__init__.py`` before reading anything here as live.  THE
    LANE HALF IS DONE AND THE FIELD IS STILL INERT: the one line that
    queues it (``actions.extend(response.extra_actions)`` in runtime.py's
    responder branch, right after ``actions = [(response.label, ...)]``)
    is chief's, and CORE-REQUEST ``20260904_0137`` asks for it.  Strike
    this item the day that line merges, not before.  runtime.py's own
    call-site comment named this as the fix and said whose it is: "a
    ``lane_hooks``/lane_a design change outside a runtime.py guard's
    scope".
2.  ~~This responder composes the conversation-default action for every
    click, and the trade-zoom action for the shop trigger, from the frozen
    helpers rather than from copies of their bytes.~~  HALF DONE, ROUND
    ``yjjtyn``, AND THE UNDONE HALF IS NAMED RATHER THAN ESTIMATED.  The
    CONVERSATION DEFAULT is composed for every ordinary click, by calling
    ``legacy.make_npc_conversation_empty`` under the label
    ``V98_NPC_CONVERSATION_DEFAULT_P<idx>_VIA_LANE_A`` (see
    ``_conversation_extra``, including the four kinds of placement that
    get nothing -- among them every row LANE B's own registry calls
    hostile in this scene, which the frozen loop's single monster INDEX
    does not cover).
    The two LATCHED actions are not, and cannot be from here as this
    responder is called today: the trade-zoom at the shop trigger
    (``shop_store5_open_sent``) and the q3020 conversation at the quest
    actor (``quest3020_conversation_sent``) are each ONCE PER SESSION in
    the frozen loop, and ``respond()`` is handed no session state that
    could say whether that once has been spent.  Composing them
    unconditionally would re-open the shop on every click; composing the
    EMPTY conversation in their place would replace a quest conversation
    with a blank one.  So step 2 is not finished until the call site
    passes those two latches (or their successor) as arguments -- a
    keyword on ``respond``, which is why every responder in this package
    takes ``**kwargs``.
3.  Only then the flag, with an attended ticket that clicks a townsperson,
    a shop keeper and placement 30 in Port Royal and reports what opened.
4.  Every other v141 behaviour that rides a ``TARGET_VITAL`` frame in
    scene 1 is enumerated and either reproduced or shown unreachable.  The
    responder branch runs INSTEAD of ``super().dispatch(parsed)``
    (``runtime.py:9026-9027``), so it swallows the whole frame, not only
    the ChooseNPC loop; pf-adversary ``zqmosn`` measured two that exist --
    v141's V138 marker branch (its ``V138_MARKER1_READY_PC`` opens with a
    ``TARGET_VITAL`` id) and the ``runtime_ack_sent`` latch, which only
    v141 ever sets and which ``runtime.py:9457`` makes the census depend
    on.
5.  ~~The responder honours the census authority ``runtime.py:10410``
    honours (``world_census_identity_resolved``) and DECLINES rather than
    composes on a boot whose login shipped Mob-Set numbers.~~  LANE HALF
    DONE, ROUND ``6dvcer``, ADDITIVELY, AND THE UNDONE HALF IS NAMED
    RATHER THAN ESTIMATED: ``respond`` grew a
    ``world_census_identity_resolved`` keyword that declines on an
    explicit ``False``.  IT IS INERT UNTIL THE CALL SITE PASSES IT --
    every call today omits it, the keyword defaults to ``None``, and
    ``None`` deliberately means "never told" rather than "failed", so this
    module's behaviour is byte-identical to what it was before.  The one
    line that arms it is chief's (``runtime.py``); it is written out
    verbatim in ``WORLD_CENSUS_IDENTITY_RESOLVED_WIRING`` below.  Strike
    this item the day that line merges, not before.  The measured cost
    that makes it necessary is unchanged and stated here:  Measured on a
    second-password-bypass boot, where the frozen v134 fallback arms
    ``(0, 30, 91)``: with the gate open a click on P0 answered with
    silence where the frozen path opened a quest conversation, and a click
    on P91 shipped two actors after login had announced three.  That also
    refutes this file's own "unreachable from a real composed generation"
    line about the unresolvable-placement branch below: it is reachable on
    every such boot.
6.  Multi-select answers every named identity, not the first
    (``TheResponderAnswersDirectlyTests`` pins today's one-answer shape;
    the frozen path returns four actions for two identities).
7.  ``docs/FUNCTIONAL_COVERAGE.json``'s ``npc_conversation_handshake``
    (``required``, ``runtime_pass``) gains a DISPATCH-level test.  Its
    three current ``test_refs`` exercise the builders, so the flip would
    have removed that capability for every Port Royal NPC but Columbus
    with all three still green.
Steps 1-6 are lane A's own work.  Nothing here is chief's.  THIS LIST IS
NOT PROMISED COMPLETE: it is what two measured passes found, and every
item on it after step 3 was found by the SECOND pass, on boot shapes the
first pass never drove.

This file is the SAFETY NET half of a two-part fix; the other half
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

HOW THE TWO REASONS BELOW READ AFTER ROUND ``zqmosn`` MEASURED THEM.
Reason 1 is unchanged and was never, on its own, a reason to wait -- but
the round that wrote it had NOT read the passage it defers to, and a
draft of round ``zqmosn`` then made that worse by calling the pair
circular and putting a sentence in quotation marks that does not exist in
``runtime.py`` (pf-adversary ``zqmosn`` B1: ``grep`` for it returns
nothing).  WHAT THAT PASSAGE ACTUALLY SAYS, at ``runtime.py:9429-9451``,
quoted from the file: home is not widened because of a "MEASURED uncaught
crash rather than parity taste", the bg0001 arm being "the only census
arm that arms ``self.population_indices`` with no lane_hooks ChooseNPC
responder standing in front of it"; and it names TWO ways out -- "either
a deferred install of population_indices at the first TargetPosVital, or
a runtime.py ChooseNPC guard for scene 1".  THE FIRST NEEDS NOTHING FROM
THIS FILE.  So there is no deadlock and never was: chief's half can move
without this flag, and this flag is one of two answers, not the gate on
the other.  Reason 2 asked for a parity check
before the swap; the check was run, and it FAILED in a way reason 2 did
not anticipate -- not on the frame's bytes, which match exactly, but on
the ACTIONS the frozen loop emits beside it.  So the caution was right and
its stated grounds were incomplete; both are kept below, and the measured
grounds are at the top of this docstring.

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

from .. import field_mobs
from .. import lane_hooks
from .. import world_census_level
from .. import world_population
from .. import world_port_royal_identity as identity
from .lane_a_ground_preserve import compose_answer
from .lane_a_scene_census import scene_is_open_to_players

# ~~Flip only after the runtime.py login trigger widen (CORE-REQUEST) has
# landed AND this lane has reviewed the tests with pf-adversary once
# more~~ -- STRUCK ROUND ``zqmosn``: that condition deferred to a passage
# (``runtime.py:9429-9451``) which names a deferred install of
# ``population_indices`` as a way out that needs nothing from this file,
# so waiting on it was never the only option -- and it was not the real
# blocker either.  Round ``zqmosn`` drove the real
# dispatcher with and without this responder and MEASURED what the flip
# would cost -- see "WHAT THE FLIP WOULD COST TODAY" in the module
# docstring.  The gate stays False for that measured reason, which is now
# pinned by ``TheGateStaysClosedForAMeasuredReasonTests``.
production_allowed = False

SCENE_N_ID = world_population.SCENE_ID

# WHAT ARMING STEP 5 ACTUALLY COSTS -- TWO LINES, NOT ONE, AND THE
# SECOND ONE IS THE IMPORTANT ONE (pf-adversary, round ``6dvcer``, D1).
# An earlier draft of this round wrote that declining "hands the frame back
# to ``super().dispatch(parsed)`` -- the frozen loop".  THAT IS FALSE, and
# this file's own docstring said so 500 lines above the sentence that
# claimed it: the call site sets ``actions = []`` on a decline with NO
# fallback (``runtime.py:10255-10262``); ``super().dispatch(parsed)`` sits
# in the OTHER arm, the one taken only when no responder is registered
# (``runtime.py:10263-10264``).
#
# MEASURED through ``runtime.make_state_class`` itself, one ordinary click
# on placement 3, three runs:
#
#     responder withdrawn (main today)   ['..._FACE_PLAYER_POSITION_HEADING_P3',
#                                         'V98_NPC_CONVERSATION_DEFAULT_P3']
#     responder answering                ['LANE_A_CHOOSE_NPC_SCENE1_FACE_P3']
#     responder declining                []            <- ZERO bytes
#
# So on a boot whose census could not resolve identities, arming the
# keyword ALONE turns "a wrong frame for two placements" into "no frame for
# every placement in the town".  That is a worse boot, not a safer one, and
# it is why the ask below is two lines rather than one.  The keyword is
# shipped anyway because it is inert (nothing passes it) and because the
# lane half has to exist before the call-site half can be asked for.
WORLD_CENSUS_IDENTITY_RESOLVED_WIRING = """runtime.py, the responder branch.
TWO changes, and neither is useful without the other.

(1) At the respond() call (runtime.py:10081-10235), add the keyword.  The
    surrounding names are LOCALS and attributes of the state object, so it
    reads exactly like the keywords already there:

        response = scene_choose_npc_responder.respond(
            legacy=legacy,
            chosen_identities=chosen_identities,
            population_indices=self.population_indices,
            last_target_pos=self.last_target_pos,
            scene_id=self.foundation.selected.position.scene_id,
            scene_entry_registry=scene_entry_registry,
            mob_combat_ledger=self.mob_combat_ledger,
            mob_loot_cell=self.mob_loot_cell,
            mob_death_register=self.mob_death_register,
            world_census_identity_resolved=self.world_census_identity_resolved,
        )

    self.world_census_identity_resolved is the census's own flag, the same
    one runtime.py:10410 already gates rebuild_face_actions on.

(2) At the decline branch (runtime.py:10255-10262), a decline that came
    from THIS guard must fall back to the frozen loop rather than to
    actions = [].  Without (2), (1) makes an already-bad boot silent.
    Whoever writes (2) decides how the two decline reasons are told apart;
    the lane's proposal is a distinct event, because today both produce
    scene_choose_npc_responder_declined and nothing else (adversary D5).
"""


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


def _frozen_index(legacy: Any, name: str) -> int | None:
    """One of the frozen loop's own special placement indices, or ``None``.

    Read off ``legacy`` rather than copied as a literal, for the same
    reason every other number in this file is: the frozen module is the
    authority on which placement is the quest actor, which is the shop
    trigger and which is the monster, and a second copy of those numbers
    here would be a silently divergent one the day v141 is re-pinned.
    ``None`` means the constant is not on this ``legacy`` at all, which is
    a real possibility for a stub in a test and is handled fail-closed by
    the one caller -- see ``_conversation_extra``.
    """
    value = getattr(legacy, name, None)
    return value if isinstance(value, int) else None


def _conversation_extra(
    legacy: Any, placement: Any, selected_idx: int, scene_id: int,
) -> tuple[tuple[tuple[str, bytes, bytes, float], ...], str]:
    """The talk trigger the frozen loop emits beside the face frame.

    Returns ``(extra_actions, reason)``; ``reason`` is what the console
    line says about this click, so a capture can tell "composed it" from
    each separate way of composing nothing.

    WHAT IT REPRODUCES, AND FROM WHERE.  The frozen loop
    (``current/pf_login_game_server_v141.py:4395-4480``) answers an
    ORDINARY scene-1 click with two actions: the face frame, then
    ``make_npc_conversation_empty(actor_identity)`` under the label
    ``V98_NPC_CONVERSATION_DEFAULT_P<idx>``.  That second action is the
    client's authentic default-talk trigger (v141's own comment above
    ``make_v98_conversation_face_state``), so a responder that takes this
    scene over without it makes every townsperson unable to talk.  This
    composes it BY CALLING THE FROZEN BUILDER through the ``legacy`` module
    the call site handed us -- never a copy of its bytes.

    THE LABEL CARRIES THE FROZEN NAME PLUS ``_VIA_LANE_A``, AND BOTH HALVES
    ARE LOAD-BEARING (pf-adversary ``yjjtyn`` D5, MEASURED).  ~~The frozen
    label verbatim~~ kept the queue's ``V98_NPC_CONVERSATION_DEFAULT``
    greps answering -- true, and a prefix grep still answers with the
    suffix on -- but it also made the two worlds indistinguishable: the
    round's own control test (``test_todays_answer_to_an_ordinary_click_
    carries_the_talk_trigger``) passed identically with the responder
    withdrawn and with it live, so the one test whose job is to say "the
    lane reproduces the frozen answer" could no longer say WHICH path
    answered.  The suffix costs no grep (the tickets that name this string
    match it as a prefix of ``..._DEFAULT_P<idx>``) and buys back the
    distinction on every capture.

    FOUR KINDS OF PLACEMENT GET NOTHING FROM HERE, EACH FOR A MEASURED
    REASON, AND NONE OF THEM IS "not implemented yet" IN DISGUISE:

    * the QUEST ACTOR (``V129_QUEST_ACTOR_INDEX``): the frozen loop sends
      ``make_npc_conversation_quest3020`` there, ONCE PER SESSION
      (``quest3020_conversation_sent``).  This responder is handed no
      session latch, so it cannot know whether that once has been spent.
      Composing the EMPTY conversation instead would replace a quest
      conversation with a blank one, which is worse than the gap.
      NOTE: THIS ARM IS UNREACHABLE FROM ``respond()`` TODAY AND SAYING SO IS
      THE POINT (pf-adversary ``yjjtyn`` D4, MEASURED): P0 has no
      shippable identity, so it is not a key of ``_placements_by_index``
      and ``respond()`` skips it before this function is called.  The arm
      stays, because "unreachable today" is a property of the identity
      table and not of this rule; what it is NOT is "the gap this round
      named" -- the real quest-actor gap is that this responder cannot
      answer P0 at all, which is item 5 of the module docstring's list,
      not this function's business.
    * the SHOP TRIGGER (``V112_SHOP_TRIGGER_INDEX``): same latch shape --
      ``make_trade_zoom_store5`` once per session
      (``shop_store5_open_sent``), and no empty conversation at all.  This
      arm IS reachable: P91 is in the table.
    * the MONSTER (``V112_MONSTER_INDEX``): the frozen loop ``continue``s
      before composing anything for it.  This responder deliberately
      answers that click with a face frame (the module docstring's "P30 (a
      gain)"), and giving it a talk trigger the frozen path never sent
      would be a second, unmeasured change riding on the first.
    * ANY ROW LANE B'S OWN REGISTRY CALLS HOSTILE IN THIS SCENE
      (``field_mobs.roster_for_scene_id(scene_id)``, that lane's public
      per-scene reader -- the same route ``lane_a_scene_census``
      already takes, never a per-scene table import).  ADDED AFTER
      pf-adversary ``yjjtyn`` D3 MEASURED that ``V112_MONSTER_INDEX`` is
      the frozen HARNESS monster (placement 30) while the rows this
      scene's AI actually ticks are placements 103/105/107/109 -- so the
      index list alone would have handed every real Port Royal mob an
      empty conversation window.  That is a symptom already on record
      with an owner (``GT-104``: the empty conversation window opens and
      there is no way into attack mode), and a lane must not quietly
      become its second owner by shipping the same bytes from a new
      place.  Parity with the frozen loop is not the test here; the
      registry is.

    Those two latched actions are the rest of step 2 in the module
    docstring's list, and they need a session-state argument at the call
    site before any lane can compose them honestly.  Named here rather
    than half-covered.
    """
    # THE TWO NAMES BELOW READ ODDLY ON PURPOSE.  The frozen module's own
    # constants are `V112_SHOP_TRIGGER_INDEX` and `V129_QUEST_ACTOR_INDEX`
    # (string literals, still spelled exactly that way one line down), but
    # the local that HOLDS each one may not repeat the word: chief's
    # quest/shop code-name guard goes recursive over the subpackages by
    # 2026-09-05 03:21 (`pf_bridge/notes_to_chief/20260904_2016`, addressed
    # to this lane), and its rule is rename-the-symbol, not
    # exempt-the-file.  `vendor_trigger_idx`/`mission_actor_idx` are this
    # lane's names for somebody else's frozen rows; nothing about which row
    # is meant has changed, and neither has any string a ticket greps.
    monster_idx = _frozen_index(legacy, "V112_MONSTER_INDEX")
    vendor_trigger_idx = _frozen_index(legacy, "V112_SHOP_TRIGGER_INDEX")
    mission_actor_idx = _frozen_index(legacy, "V129_QUEST_ACTOR_INDEX")
    if None in (monster_idx, vendor_trigger_idx, mission_actor_idx):
        # FAIL CLOSED, and in the direction that composes LESS: without
        # the frozen module's own numbers this cannot tell an ordinary
        # townsperson from the shop trigger, and composing a talk trigger
        # for the shop trigger would be an action the frozen path never
        # sent for that click.
        return (), "no_extra_frozen_indices_unreadable"
    if selected_idx == mission_actor_idx:
        return (), "no_extra_quest_actor_needs_session_latch"
    if selected_idx == vendor_trigger_idx:
        return (), "no_extra_shop_trigger_needs_session_latch"
    if selected_idx == monster_idx:
        return (), "no_extra_monster_frozen_path_sends_none"
    try:
        hostile_identities = frozenset(
            mob.actor_identity
            for mob in field_mobs.roster_for_scene_id(scene_id)
        )
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as failure:  # noqa: BLE001 - lane B's registry is
        # not this answer's dependency, but it IS this rule's input, and
        # without it this cannot tell a townsman from a hostile row.  Fail
        # closed in the direction that composes LESS, and say which of the
        # two silences this is -- the same distinction
        # ``lane_a_scene_census._field_mob_identities`` already draws for
        # its own reader.
        return (), (
            f"no_extra_hostile_registry_unreadable_{type(failure).__name__}"
        )
    if placement.actor_identity in hostile_identities:
        return (), "no_extra_hostile_row_lane_b_registry"
    try:
        conv_pc, conv_frame = legacy.make_npc_conversation_empty(
            placement.actor_identity,
        )
    except Exception as error:  # noqa: BLE001 - a responder must never
        # take the listener thread down for every player, and an answer
        # that loses its talk trigger is still a better answer than a
        # dropped click.  Named, never silent.
        return (), f"no_extra_builder_refused_{type(error).__name__}"
    return (
        (
            (
                f"V98_NPC_CONVERSATION_DEFAULT_P{selected_idx}"
                "_VIA_LANE_A",
                conv_pc, conv_frame, 0.0,
            ),
        ),
        "conversation_default",
    )


def respond(
    *,
    legacy: Any,
    chosen_identities: tuple[int, ...],
    population_indices: tuple[int, ...] | None,
    last_target_pos: tuple[float, float, float, float] | None,
    scene_id: int = SCENE_N_ID,
    scene_entry_registry: Any = None,
    mob_loot_cell: Any = None,
    world_census_identity_resolved: bool | None = None,
    **_ignored: Any,
) -> "lane_hooks.ChooseNpcResponse | None":
    """Answer one ChooseNPC click for scene 1, or decline (see module doc).

    Keyword-only, same convention as ``lane_a_choose_npc_scene14.respond``,
    for the same reason: a future call site can grow arguments without
    breaking every registered responder at once.
    """
    if scene_id != SCENE_N_ID:
        return None
    if world_census_identity_resolved is False:
        # STEP 5 OF THE PROMOTION LIST, LANE HALF.  ``is False`` and not a
        # bare falsy test on purpose: ``None`` means the call site never
        # passed the keyword (which is every call today -- see
        # ``WORLD_CENSUS_IDENTITY_RESOLVED_WIRING``) and MUST keep the
        # behaviour this module had before the keyword existed, byte for
        # byte.  Only an explicit ``False`` -- the census telling us it
        # could not resolve identities on this boot -- declines.
        #
        # DECLINING IS NOT FREE, AND THE COST IS NAMED RATHER THAN
        # HIDDEN (pf-adversary ``6dvcer`` D1): the call site answers a
        # decline with ``actions = []`` -- ZERO bytes -- not with the
        # frozen loop.  Read ``WORLD_CENSUS_IDENTITY_RESOLVED_WIRING``
        # before arming this: on its own the keyword makes a census-failed
        # boot SILENT for the whole town rather than wrong for two
        # placements.  It is inert today (nothing passes the keyword) and
        # the ask that arms it is two lines, not one.
        #
        # WHY ANSWERING IS NOT SAFE EITHER, MEASURED
        # (pf-adversary ``zqmosn``, second pass, on a
        # second-password-bypass boot where the frozen v134 fallback arms
        # ``(0, 30, 91)``): with this responder registered, a click on P0
        # answered with SILENCE where the frozen path opened a quest
        # conversation, and a click on P91 shipped two actors after login
        # had announced three.
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
            # THE LEVEL, ROUND ``zqmosn``, AND THE DEFECT IT REMOVES.
            # ~~``legacy.make_npc_attr(...)`` directly~~ -- STRUCK, not
            # deleted: this module composed with the bare frozen helper,
            # which has NO level parameter, from the round it was written
            # until this one.  That is the SAME defect ``world_face_frame``
            # already found and fixed on the frozen click path in round
            # ``2p4n3h`` (read its own comment at
            # ``world_face_frame.py:206-219``): one click re-sent every
            # Port Royal actor with no level at all and silently reverted
            # round ``7ste68`` on the wire.  It never reached a player from
            # HERE only because ``production_allowed`` was False -- so the
            # gate was not protecting the town from a hypothetical, it was
            # holding back a KNOWN regression, and flipping the gate
            # without this line would have put the defect back the day the
            # town's clicks moved to this responder.
            #
            # DERIVED FROM THE CENSUS'S OWN COMPOSER, NOT A SECOND COPY OF
            # ITS RULES: ``world_census_level.leveled_npc_attr`` is the one
            # call ``world_population._entry`` makes, with the same
            # ``SCENE_SEQUENCE`` and the same ``identity`` row, so a click
            # REPEATS the census instead of approximating it.  If the
            # frozen body's layout ever moves, that module refuses rather
            # than guesses, and this responder inherits the refusal.
            npc_attr_bytes = world_census_level.leveled_npc_attr(
                legacy,
                template_n_id=resolved.mobs_n_id,
                actor_identity=placement.actor_identity,
                scene_id=scene_id,
                scene_sequence=world_population.SCENE_SEQUENCE,
                visual_preset=resolved.outfit,
                current_hp=hp,
                max_hp=hp,
                basic_name=resolved.name,
                level=resolved.level,
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
        # GROUND PRESERVE (LANE-B letter 20260902_1845 item 2, the
        # call-site half COO-DECISION 20260902_1946 approved).  Same
        # bytes as ``legacy.make_runtime_remote_actors`` whenever no
        # row is standing in THIS scene, which includes every boot
        # where chief has not passed a cell yet.  The scene naming
        # and the fail-closed path live in one module for all four
        # responders - see ``lane_a_ground_preserve``, including why
        # ~~the letter's own ``scene_id`` argument had to be resolved
        # to a scene FOLDER before it could gate anything~~ - STRUCK,
        # round ``umlyof``: the ID is what gates now, because the
        # ambiguity card that keeps one scene's floor out of another
        # scene's frame can only refuse an id.
        pc, frame = compose_answer(
            legacy, entries, scene_id, mob_loot_cell)
        extra_actions, extra_reason = _conversation_extra(
            legacy, by_idx[selected_idx], selected_idx, scene_id,
        )
        console_lines = (
            f"LANE_A_CHOOSE_NPC_SCENE{scene_id}_ANSWERED "
            f"placement={selected_idx} visible={len(entries)} "
            f"omitted={omitted} "
            f"anchor={'known' if last_target_pos is not None else 'none'} "
            # THE EXTRA IS REPORTED ON EVERY CLICK, INCLUDING THE CLICKS
            # THAT GET NONE, because "composed nothing" and "composed the
            # talk trigger" are indistinguishable on a capture otherwise --
            # the same reason the census's own
            # ``..._ACTOR_IDENTITIES_UNREPORTABLE`` line exists (round
            # ``t8m3ab``).  ``extra=`` counts what a call site would queue
            # after the pair; ``extra_reason=`` says which of the four
            # reasons in ``_conversation_extra`` this click took.
            f"extra_composed={len(extra_actions)} "
            f"extra_reason={extra_reason}",
        )
        return lane_hooks.ChooseNpcResponse(
            label=f"LANE_A_CHOOSE_NPC_SCENE{scene_id}_FACE_P{selected_idx}",
            pc=pc, frame=frame, delay=0.0, console_lines=console_lines,
            extra_actions=extra_actions,
        )
    return None


lane_hooks.choose_npc_responder(SCENE_N_ID)(respond)
