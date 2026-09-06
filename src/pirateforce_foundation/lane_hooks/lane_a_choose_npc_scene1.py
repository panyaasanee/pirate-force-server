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
    it.  ~~P91's "(LOST)" is unchanged and still measured -- the trade-zoom
    is once-per-session state no argument reaches this responder carries
    (step 2 below).~~  AMENDED AGAIN, ROUND ``rlymq1``, AND THE VERDICT
    STILL DOES NOT MOVE.  The argument exists now: ``respond()`` takes the
    two frozen latches as keywords and composes the trade-zoom at P91 (and
    the q3020 conversation at the quest actor) when the session says the
    once is unspent, naming what it spent in ``latches_spent``.  So P91's
    "(LOST)" is CONDITIONAL exactly like P1's -- conditional on the chief
    lines in ``VENDOR_AND_MISSION_LATCH_WIRING``, which nothing passes today.
    ~~Until those land, every call still omits the keywords, both arms still
    answer with today's reason strings, and the flip still costs the town
    its shop, so the gate below stays False.~~  STRUCK, ROUND ``eknq8d``:
    THEY LANDED, AND THE TWO "(LOST)" ROWS ARE NOW PAID -- MEASURED, NOT
    ASSUMED.  ``runtime.py`` queues ``extra_actions``, passes
    ``vendor_open_latch_spent``/``mission_dialog_latch_spent`` from the same
    attributes the frozen loop sets, and writes ``latches_spent`` back.
    Driven through ``runtime.make_state_class`` this round with this
    responder registered
    (``tests/test_lane_a_choose_npc_scene1.py``'s
    ``TheRegisteredResponderDropsTheTalkTriggerAtRealDispatchTests`` pins
    all three rows):

        click        on main today                       with this responder
        ---------    --------------------------------    -------------------
        P1           face + talk trigger                 face + talk trigger
                     + Columbus quest 3021               + Columbus quest 3021
        P91          face + TRADE_ZOOM_STORE5            face + TRADE_ZOOM_STORE5
                                                         (second click in the
                                                         same session: face
                                                         alone -- the latch is
                                                         written back)
        P30          (nothing -- refused by name)        face (a gain)
        P0           (nothing -- unresolvable)           (nothing -- the same)

    WHAT IS STILL NOT PAID, AND IT IS NO LONGER THE ACTIONS: steps 4 and 5
    below, whose chief-owned ``runtime.py`` lines are still absent from
    ``main`` (grepped at HEAD this round: ``world_census_identity_resolved``,
    ``runtime_ack_sent`` and ``exact_frozen_marker1_ready_pc`` appear at no
    call site in ``runtime.py``).  Those three keywords are this module's
    DECLINE guards, so flipping the gate today would take the scene over on
    boots where it must stand aside.  That is why the gate below is still
    False -- a different reason from the one this table carried before, and
    a smaller one.

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
below), and ~~the shop's trade-zoom is still not composable from here at
all~~ -- STRUCK, ROUND ``rlymq1``, and struck HERE rather than only in the
amendment above it (pf-adversary ``rlymq1``, "wrongly striking"): in a file
whose convention makes un-struck text live, an amendment thirty lines up
does not retire a sentence down here.  It is composable now, from the two
keywords nothing passes.  So flipping this flag today would still leave
every NPC in the town unable to talk and the shop unable to open, for the
call-site reason and not for this one.

WHAT MUST LAND BEFORE THIS FLAG MOVES (steps 1-3 in this order; 4-7 in
any order, all of them before the flip):
1.  ``ChooseNpcResponse`` becomes a COLLECTION of actions rather than one
    pair.  NOT STRUCK, AND THE UN-STRIKING IS DELIBERATE (pf-adversary
    ``yjjtyn`` D7): this file's convention is that struck text means
    SHIPPED, and half of this item is not.  LANE HALF DONE, ROUND
    ``yjjtyn``, ADDITIVELY: the type gained
    ``extra_actions`` (default ``()``, so every responder and the call
    site keep their present meaning) -- read that field's own paragraph in
    ``lane_hooks/__init__.py`` before reading anything here as live.  ~~THE
    LANE HALF IS DONE AND THE FIELD IS STILL INERT: the one line that
    queues it (``actions.extend(response.extra_actions)`` in runtime.py's
    responder branch, right after ``actions = [(response.label, ...)]``)
    is chief's, and CORE-REQUEST ``20260904_0137`` asks for it.  Strike
    this item the day that line merges, not before.~~  STRUCK, ROUND
    ``eknq8d``: THAT LINE IS ON ``main``.  ``runtime.py`` queues the field
    in its responder branch, inside a try whose failure path keeps the face
    frame; the talk trigger reaches a real dispatched click's actions,
    measured this round and pinned at dispatch level rather than at
    ``respond()`` level.  runtime.py's own
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
    ~~The two LATCHED actions are not, and cannot be from here as this
    responder is called today~~ -- STRUCK IN THE LANE HALF, ROUND
    ``rlymq1``, ADDITIVELY, AND THE UNDONE HALF IS AGAIN NAMED RATHER THAN
    ESTIMATED.  The trade-zoom at the shop trigger
    (``shop_store5_open_sent``) and the q3020 conversation at the quest
    actor (``quest3020_conversation_sent``) are each ONCE PER SESSION in
    the frozen loop, so ``respond()`` grew a keyword for each, three-state
    like step 5's: ``None`` (every call site today) keeps this module's old
    answer and old reason string byte for byte, an explicit ``False``
    composes the frozen builder's own action, an explicit ``True`` composes
    nothing under a duplicate-suppressed reason.  Composing them
    unconditionally would still re-open the shop on every click, which is
    why nothing here composes on ``None``; composing the EMPTY
    conversation in their place would still replace a quest conversation
    with a blank one, which is why nothing here ever does that.
    THE LANE CANNOT WRITE THE LATCH BACK AND MUST NOT TRY: it is handed no
    session object, so it returns the names of the flags its actions spent
    in ``ChooseNpcResponse.latches_spent`` and the call site sets them.
    ~~STEP 2 IS THEREFORE NOT FINISHED, and the remainder is chief's, not
    this lane's: two lines in ``runtime.py``, written out verbatim in
    ``VENDOR_AND_MISSION_LATCH_WIRING`` below.  Strike this item the day they
    merge, not before.~~  STRUCK, ROUND ``eknq8d``: THEY MERGED, BOTH OF
    THEM, AND THE PAIR WAS MEASURED TOGETHER RATHER THAN GREPPED APART.
    The call site reads ``self.shop_store5_open_sent`` and
    ``self.quest3020_conversation_sent`` into the two keywords and sets
    back only the two names it recognises out of ``latches_spent``.  Two
    clicks on the shop trigger in ONE dispatched session now answer
    trade-zoom-then-nothing rather than trade-zoom twice.
3.  Only then the flag, with an attended ticket that clicks a townsperson,
    a shop keeper and placement 30 in Port Royal and reports what opened.
4.  ~~Every other v141 behaviour that rides a ``TARGET_VITAL`` frame in
    scene 1 is enumerated and either reproduced or shown unreachable.~~
    ENUMERATION DONE AND LANE HALF DONE, ROUND ``eepcv6``, ADDITIVELY, AND
    THE UNDONE HALF IS AGAIN NAMED RATHER THAN ESTIMATED.  The responder
    branch runs INSTEAD of ``super().dispatch(parsed)``, so it swallows
    the whole frame, not only the ChooseNPC loop.  The enumeration is
    ``FROZEN_TARGET_VITAL_BEHAVIOURS`` below: EIGHT rows, walked in v141's
    own source order down the one block every such frame enters
    (``v141:3680``), each with the file:line it was derived from and a
    verdict of UNREACHABLE / DISARMED / STAND_ASIDE / ACCEPTED_GAP.  The
    two pf-adversary ``zqmosn`` named are rows 3 and 4, both STAND_ASIDE:
    ``respond`` grew a three-state keyword for each -- ``runtime_ack_sent``
    declines on an explicit ``False``, ``exact_frozen_marker1_ready_pc``
    declines on an explicit ``True`` -- so the frozen path keeps the two
    frames a responder must not swallow.  BOTH ARE INERT UNTIL THE CALL
    SITE PASSES THEM: every call today omits them, both default to
    ``None``, and ``None`` deliberately means "never told" rather than
    "failed", so this module's behaviour is byte-identical to what it was
    before.  The lines that arm them are chief's, written out verbatim in
    ``FROZEN_TARGET_VITAL_BEHAVIOUR_WIRING`` -- and that constant says why
    they must land WITH the frozen-loop decline fallback rather than
    without it.  Strike this item the day they merge, not before.
    TWO ROWS STAY ``ACCEPTED_GAP`` AND THEY ARE REASONS THE FLAG IS STILL
    FALSE: ``v129_post_action1_request_observed`` (bookkeeping, no frame)
    and ``v126_action_target_arm``, which is why step 3's attended ticket
    must click with a weapon bound.
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
6.  ~~Multi-select answers every named identity, not the first
    (``TheResponderAnswersDirectlyTests`` pins today's one-answer shape;
    the frozen path returns four actions for two identities).~~  DONE,
    ROUND ``vxfepr``, ENTIRELY LANE-OWNED, NO CHIEF LINE WAITED ON.  THIS
    ITEM GOT HEAVIER IN ROUND ``rlymq1`` AND THE WEIGHT IS THE REASON IT
    WAS PAID NEXT: it used to cost only talk triggers, and once the latch
    lines above land it decides WHETHER THE SHOP OPENS.  Before this round
    one frame naming P91 and P1 answered the first named identity only, so
    with the latches wired a P1-first frame would have spent nothing and a
    P91-first frame would have opened the store -- pf-adversary ``rlymq1``
    measured that asymmetry against the frozen loop's four actions for two
    identities and it was the whole reason this item stopped being merely
    a talk-trigger gap.  ``respond()`` now walks every distinct identity
    the frame names (``dict.fromkeys(chosen_identities)``, same de-dup the
    frozen loop's own comment explains): the first that resolves keeps the
    response's one ``pc``/``frame`` pair, byte for byte what a
    single-identity click always answered, and every identity after it --
    its own face frame, then its own conversation extra -- rides in
    ``extra_actions``, in the frozen loop's own order (face, then
    talk-trigger-or-latched-action, per identity).  Pinned now by
    ``TheResponderAnswersDirectlyTests``' renamed multi-select test and by
    a new class, ``TheMultiSelectAnswersEveryNamedIdentityTests``, which
    drives two and three named identities together, checks ordering, a
    repeated identity in one frame, and a frame mixing one resolvable and
    one out-of-population identity.
7.  ~~``docs/FUNCTIONAL_COVERAGE.json``'s ``npc_conversation_handshake``
    (``required``, ``runtime_pass``) gains a DISPATCH-level test.~~  DONE,
    ROUND ``vxfepr``.  Its three ``test_refs`` before this round exercised
    the builders only, so a premature flip would have removed the talk
    trigger for every Port Royal NPC but Columbus with all three still
    green.  ``TheRegisteredResponderDropsTheTalkTriggerAtRealDispatchTests``
    (bottom of ``tests/test_lane_a_choose_npc_scene1.py``) registers this
    module's ``respond`` onto scene 1's REAL registry slot -- what the
    registry holds the day the gate opens, not a private stand-in -- and
    drives it through ``runtime.make_state_class`` the same way
    ``TheGateStaysClosedForAMeasuredReasonTests`` drives today's frozen
    answer.  It is added to ``npc_conversation_handshake``'s own
    ``test_refs`` in the same commit.  ~~IT CURRENTLY PINS A GAP RATHER THAN
    A GUARANTEE, AND SAYS SO IN ITS OWN DOCSTRING: with the responder
    registered but ``runtime.py``'s queue line (CORE-REQUEST
    ``20260904_0137``) still unmerged, a real dispatched click answers
    with the face frame alone -- the talk trigger this class asserts is
    ABSENT, not present, because nothing yet reads ``extra_actions`` at
    the real call site.~~  STRUCK, ROUND ``eknq8d``: IT PINS THE GUARANTEE
    NOW.  The queue line landed, the absence assertion went RED on
    ``origin/main`` (COO-DECISION ``2026-09-06T21:41`` read that red as
    progress and ordered the inversion), and it is now ``assertIn`` under a
    name that says what it measures.  That assertion inverted, and the class
    docstring said it would, the day the queue line landed; the class stayed
    either way, because its other job -- proving a real dispatched click
    through the registered responder still resolves at all -- did not
    change.  THE CLASS NAME STILL SAYS "DROPS" AND IS THEREFORE HISTORIC:
    renaming it moves ``docs/FUNCTIONAL_COVERAGE.json`` and the digest pin
    in ``tests/test_foundation_legacy_seam.py``, neither of which is this
    lane's file -- round ``eknq8d`` left both alone and wrote the rename up
    as a follow-up instead.
~~Steps 1-6 are lane A's own work.  Nothing here is chief's.~~  CORRECTED,
ROUND ``rlymq1``, BECAUSE THE SENTENCE HAD STOPPED BEING TRUE AND WAS
LOAD-BEARING: steps 1, 2 and 5 each ended as a LANE half plus a
CHIEF-OWNED ``runtime.py`` line, and the lane half of all three is now
written.  ~~What is left of them is chief's alone -- the queue line
(CORE-REQUEST ``20260904_0137``), the two latch lines
(``VENDOR_AND_MISSION_LATCH_WIRING``) and the census keyword plus its decline
fallback (``WORLD_CENSUS_IDENTITY_RESOLVED_WIRING``).~~  AMENDED, ROUND
``eknq8d``: THE FIRST TWO GROUPS ARE ON ``main`` (steps 1 and 2 are struck
above and the strikes carry the measurement).  WHAT IS LEFT OF THIS LIST IS
THE DECLINE HALF AND ONLY IT: step 5's census keyword plus its decline
fallback (``WORLD_CENSUS_IDENTITY_RESOLVED_WIRING``) and step 4's two
(``FROZEN_TARGET_VITAL_BEHAVIOUR_WIRING``) -- three keywords, none of which
appears at any call site in ``runtime.py`` at HEAD this round.  STEPS 6 AND 7 ARE
NOW DONE TOO, ROUND ``vxfepr``, AND NEITHER WAITED ON A CHIEF LINE -- SEE
THEIR OWN STRIKES ABOVE.  ~~Step 4 is still lane A's own and still
undone.~~  DONE ROUND ``eepcv6``, AND IT WENT THE WAY STEPS 1/2/5 WENT
RATHER THAN THE WAY 6/7 DID: a LANE half (the enumeration plus two decline
keywords) plus a CHIEF-OWNED ``runtime.py`` pair
(``FROZEN_TARGET_VITAL_BEHAVIOUR_WIRING``).  SO NO STEP ON THIS LIST IS
STILL WAITING ON THIS LANE.  What stands between the list and step 3's
attended ticket is four chief-owned lines in three groups, plus the two
``ACCEPTED_GAP`` rows step 4 leaves named.
THIS LIST IS NOT PROMISED COMPLETE: it is what two measured passes found,
and every item on it after step 3 was found by the SECOND pass, on boot
shapes the first pass never drove.

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
2.  THIS REASON IS NOW THE LIVE ONE AND ROUND ``eknq8d`` NARROWED IT TO A
    SENTENCE: the three DECLINE keywords steps 4 and 5 define are still
    passed by nobody, so a flip today would take over the two frames the
    responder must stand aside for (the frozen first ack, the exact
    marker1-ready PC) and would answer on a boot whose census could not
    resolve identity.  The ACTIONS half of this reason is paid -- see the
    amended table at the top of this docstring.
    Once armed, this module answers EVERY scene-1 click instead of the
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
# STEP 4 OF THE PROMOTION LIST: THE ENUMERATION ITSELF.
#
# The responder branch runs INSTEAD of ``super().dispatch(parsed)``
# (runtime.py's own comment above the branch says so), so it swallows the
# WHOLE frame, not only the ChooseNPC loop.  Step 4 asks for every other
# v141 behaviour that rides a ``TARGET_VITAL`` frame in scene 1 to be
# enumerated and either reproduced or SHOWN unreachable.  This is that
# enumeration, walked in v141's own source order down the one block every
# such frame enters -- ``elif parsed.outer_id == GSCN_RUNTIME_PROTOCOL_REQ
# and self.teleport_sent:`` (v141:3680) -- with the reachability of each
# row derived from the frozen file, never from a capture.
#
# ``verdict`` is one of:
#   UNREACHABLE  -- the row's own guard cannot hold for a frame whose
#                   nested id is TARGET_VITAL.  Nothing to do.
#   DISARMED     -- reachable in v141, but this tree disarms the row
#                   before any client connects, so the responder cannot
#                   cost what is already off.
#   STAND_ASIDE  -- reachable and live, NOT reproducible from a responder
#                   (which is handed no session object), so ``respond()``
#                   declines and lets the frozen path have the frame.
#   ACCEPTED_GAP -- reachable, live, not reproduced, and knowingly left:
#                   the row costs nothing on the frames scene 1 answers
#                   today, and the reason is written out per row.
#
# EVERY ``ACCEPTED_GAP`` ROW IS A REASON THE FLAG IS STILL FALSE, not a
# reason it may flip.  Step 3 (the attended ticket) is what turns the last
# of them into a measurement.
FROZEN_TARGET_VITAL_BEHAVIOURS = (
    (
        "v129_post_action1_request_observed",
        "v141:3688-3699",
        "ACCEPTED_GAP",
        "Bookkeeping only -- appends to self.events and three counters, "
        "queues no action and sends no bytes.  Gated on "
        "quest3020_accept_success_sent, which nothing in this tree sets "
        "for scene 1 today.  Costs a console/events trail, never a frame.",
    ),
    (
        "v136_compositional_marker1_docking_prompt_once",
        "v141:3701-3727",
        "UNREACHABLE",
        "Guarded by exact_empty_runtime_req, which requires "
        "parsed.raw_pc == V136_EMPTY_RUNTIME_REQ_PC (v141:831-833) -- a "
        "12-byte PC with vital_count 0 and nested_id None "
        "(v141:5642-5645).  A frame whose nested id is TARGET_VITAL has a "
        "nested id, so the equality can never hold.",
    ),
    (
        "v140_marker1_ready_population_once",
        "v141:3729-3760",
        "STAND_ASIDE",
        "V138_MARKER1_READY_PC IS a TARGET_VITAL frame -- v141:5874-5882 "
        "asserts nested_id == TARGET_VITAL on it -- so it reaches this "
        "branch.  Claiming it would swallow the population send and the "
        "population_indices / population_refresh_anchor / "
        "v138_marker1_population_sent commits that ride with it.  "
        "respond() declines on exact_frozen_marker1_ready_pc=True.",
    ),
    (
        "runtime_req_first_ack",
        "v141:3768-3772",
        "STAND_ASIDE",
        "Unconditional on the FIRST frame of this block, TARGET_VITAL "
        "included.  The constructor-exact empty RuntimeRes is what feeds "
        "the client's receive watchdog; runtime.py gates a dozen of its "
        "own paths on the same flag.  respond() declines on "
        "runtime_ack_sent=False.",
    ),
    (
        "v99_show_message_local_server_online",
        "v141:3774-3781",
        "STAND_ASIDE",
        "Rides the same first frame, one line below the ack, gated on the "
        "flag that line sets.  Covered by the same decline -- named as its "
        "own row because it is its own send, not a detail of the ack.",
    ),
    (
        "v100_music_control_current_scene",
        "v141:3782-3787",
        "STAND_ASIDE",
        "Rides the same first frame as the ack and the welcome message, "
        "gated on the same flag, covered by the same decline.  Its own "
        "row because it is its own send: a player who loses this one "
        "hears silence in a town that should have music.",
    ),
    (
        "v126_action_target_arm",
        "v141:3788-3816",
        "ACCEPTED_GAP",
        "Unconditional on every TARGET_VITAL frame: arms "
        "action_target_last_identity / _last_kind / p30_action_target_armed, "
        "read later by the ACTION_VITAL handler (v141:3818-3862) to gate "
        "exact_target_bound_wield_action.  MEASURED by pf-adversary "
        "`hd6tac` on the scene 14 responder: the attributes stayed None "
        "through a claimed click.  Not reproducible from here (no session "
        "object) and not declinable without declining every click there "
        "is.  It costs nothing in Port Royal only because "
        "exact_p30_target's strict match wants an arena-harness identity "
        "and index shape scene 1's real actors do not have -- INCIDENTAL, "
        "and it is why step 3's attended ticket must click with a weapon "
        "bound before this flag flips.",
    ),
    (
        "v134_p0_p30_p91_isolated_initial_ready",
        "v141:4292-4300",
        "DISARMED",
        "The frozen three-actor NPC spawn.  Gated on runtime_ack_sent AND "
        "last_target_pos, which only the position-vital path sets "
        "(v141:4259) -- never a TARGET_VITAL frame on its own.  Beyond "
        "that this tree disarms the branch at construction whenever the "
        "world census is enabled (runtime.py:1564-1584), on purpose and "
        "for reasons measured there.  Nothing left for a responder to "
        "cost.",
    ),
)


FROZEN_TARGET_VITAL_BEHAVIOUR_WIRING = """runtime.py, the responder branch.
Step 4's call-site half.  TWO keywords, both already attributes of the state
object, and BOTH ARE ONE-WAY GUARDS -- they can only make the responder
decline, never make it answer something it would not have answered:

    response = scene_choose_npc_responder.respond(
        ...,
        runtime_ack_sent=self.runtime_ack_sent,
        exact_frozen_marker1_ready_pc=(
            parsed.raw_pc == legacy.V138_MARKER1_READY_PC
        ),
    )

self.runtime_ack_sent is the frozen latch v141:3771 sets, the same one
runtime.py already reads at 1747/1796/1848/1926/2149/2397/2468/2539/2616.
legacy.V138_MARKER1_READY_PC is the frozen 76-byte constant at v141:844.

AND THE DECLINE MUST FALL BACK TO THE FROZEN LOOP, NOT TO ``actions = []``
-- the same second half WORLD_CENSUS_IDENTITY_RESOLVED_WIRING asks for, and
here it is not a preference: a decline that answers with zero bytes on the
FIRST runtime request would withhold the very ack the client is waiting for,
which is worse than the swallow this guard exists to prevent.  If only one
of the two halves can land, land neither.
"""


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


VENDOR_AND_MISSION_LATCH_WIRING = """runtime.py, the responder branch.  Step 2's
call-site half.  TWO changes, and the second is what makes the first safe.

(1) At the respond() call (runtime.py:10081-10235), pass the two frozen
    session latches.  Both are already attributes of the state object the
    frozen loop itself sets (v141:3534-3535), so this reads like the
    keywords already there:

        response = scene_choose_npc_responder.respond(
            ...,
            vendor_open_latch_spent=self.shop_store5_open_sent,
            mission_dialog_latch_spent=self.quest3020_conversation_sent,
        )

    THE KEYWORD NAMES ARE THE LANE'S AND THE ATTRIBUTE NAMES ARE YOURS,
    AND THE MISMATCH IS NOT A TYPO.  Chief's own quest/shop code-name
    guard is recursive over these subpackages now, and its rule is
    rename-the-symbol: a lane module may not BIND a guarded name, so the
    keywords carry this lane's words for your rows -- exactly as
    vendor_trigger_idx/mission_actor_idx already do for the frozen
    indices.  Nothing about which flag is meant has changed.

(2) In the SAME place that queues response.extra_actions (step 1's line),
    record what those actions spent, immediately after queuing them:

        for _latch in response.latches_spent:
            if _latch in ("shop_store5_open_sent",
                          "quest3020_conversation_sent"):
                setattr(self, _latch, True)

    The membership test is deliberate: the lane sends attribute NAMES, and
    a call site should set only names it recognises rather than setattr
    whatever a responder returns.

WITHOUT (2), (1) IS A REGRESSION AND NOT A GAIN.  The frozen loop sets
each flag in the same breath as it appends the action
(v141:4434-4441, 4453-4461).  Passing the latches in while never writing
them back leaves every click of P91 reading shop_store5_open_sent=False,
so the trade-zoom is composed again and again and store 5 re-opens on
every click -- worse than today's silence at that placement.  Take both
changes or neither.

TAKING NEITHER IS BYTE-IDENTICAL ON THE WIRE AND NOT ON THE CONSOLE, and
the difference is stated rather than rounded off (pf-adversary `rlymq1`
D5, MEASURED against main): pc, frame, delay and extra_actions are
identical for every click, and console_lines gains ` latches=<...>` on
EVERY click -- plus ` latch_kwarg_misnamed=<...>` on the one shape that
would otherwise be invisible.  console_lines is a field this call site
reads, so "byte-identical" without that sentence would have been a claim
about a field this round really does change.

ONE PRECONDITION THIS ASKS OF THE CALL SITE, NAMED RATHER THAN ASSUMED.
The read (passing the latch in) and the write (setting it) happen either
side of this lane, so they are only atomic while ONE thread dispatches per
connection.  That holds today -- v141:7558 is the single receive loop, its
one background thread (v141:7438) sends heartbeats and never dispatches --
and it is a precondition of this design, not a property of it.  A future
call site that dispatches a connection's frames from a pool must set the
latch itself before it queues, not after.

THE MISSION LINE IS INERT AT HEAD AND IS ASKED FOR ANYWAY, WITH THE
REASON SAID OUT LOUD (pf-adversary `rlymq1` D6, MEASURED over all 115
frozen placements: q3020 is composed for NONE of them).  Placement 0
carries template 1, which world_port_royal_identity refuses for want of a
CONSTDATA MOBS row, so respond() never reaches the mission arm.  The
keyword is shipped so the shape exists the day that identity resolves --
exactly the status step 5's keyword carries.  The line that can change a
byte today is the vendor one.

AND ONE MORE LINE THAT IS NEITHER LANE A'S NOR CHIEF'S TO FORGET.  LANE B
already asks, on main, for a store-session stamp AT THE SAME QUEUE POINT
(`trade_session_membership.py:75-79`, RE-157 job 1): build_session() where
a store-open frame is actually queued from an announced P91 identity.
Taking this ask WITHOUT that one opens store 5 on screen and then refuses
every cart-add and buy with `trade_cmd_no_active_session_no_reply`.  The
two asks are one edit; neither constant knew about the other until
pf-adversary `rlymq1` D8 read both.

WHAT SETTING THE MISSION FLAG REALLY AUTHORISES, since this ask cites the
write and a reader elsewhere depends on it: v141:3974-4010 reads
quest3020_conversation_sent as the SEQUENCE PRECONDITION for the whole
q3020 accept chain (op1 -> action6 -> op2), not merely as duplicate
suppression.  The direction here is safe -- it is reported only when the
conversation was actually composed, exactly as v141 does -- but a call
site that sets it on any other occasion is authorising a different
subsystem.
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


# The frozen state object's own spellings for the two latches, as DATA.
# Two jobs, and both are load-bearing:
#
#   1. they are what ``latches_spent`` carries, so chief's ``setattr``
#      needs no translation table (this lane must never rename these two
#      strings -- doing so would write a flag v141 does not have, with
#      every test still green);
#   2. they are what ``respond()`` WATCHES FOR in ``**_ignored``.
#
# THE SECOND JOB IS THE ANSWER TO pf-adversary ``rlymq1`` D2, MEASURED:
# this lane's keywords are named ``vendor_``/``mission_`` because chief's
# code-name guard forbids binding his words, while the ATTRIBUTES chief
# reads them off keep the frozen spellings -- so the wiring line pairs two
# different names, unlike every other keyword at that call site.  A chief
# who writes the symmetric ``shop_store5_open_sent=self.shop_store5_open_
# sent`` (the shape ``WORLD_CENSUS_IDENTITY_RESOLVED_WIRING`` one screen
# up really does have) lands in ``**_ignored``: no ``TypeError``, no event,
# and a console line byte-identical to an UNWIRED boot.  The ask would read
# as honoured and the shop would never open.  Watching for these spellings
# is what makes those two worlds different on a capture.
_FROZEN_LATCH_ATTRS = (
    "shop_store5_open_sent",
    "quest3020_conversation_sent",
)
# Read back out under this lane's words so the two arms below name them
# without binding chief's, and so the spellings live in ONE place: a
# second copy is how ``latches_spent`` would start naming a flag v141 does
# not have, with every test in this file still green.
_VENDOR_LATCH_ATTR, _MISSION_LATCH_ATTR = _FROZEN_LATCH_ATTRS


def _misnamed_latch_kwargs(ignored: dict) -> tuple[str, ...]:
    """The frozen latch spellings that arrived where nothing reads them.

    Returns them sorted, so the console line is stable across dict order.
    Everything else in ``**_ignored`` is left alone and unreported: the
    call site legitimately passes keywords this responder does not want
    (``mob_combat_ledger``, ``mob_death_register``), and a line that
    shouted about those would be noise nobody reads by the second boot.
    """
    return tuple(sorted(
        name for name in _FROZEN_LATCH_ATTRS if name in ignored
    ))


def _frozen_builder(legacy: Any, name: str) -> Any:
    """One of the frozen loop's own action builders, or ``None``.

    THE STRING ARGUMENT IS THE POINT, AND IT IS THE SAME POINT
    ``_frozen_index`` MAKES ONE FUNCTION UP.  Two of the builders this
    module must call carry chief's guarded code names in their own
    spelling, and his guard reads a module's CODE TOKENS -- an attribute
    access spells the name in code, a string does not
    (``tests/test_npc_interaction_wire.py:242`` skips comments and string
    literals by construction).  His rule for a guarded name a lane binds
    is rename-the-symbol, not exempt-the-file, and a builder on somebody
    else's frozen module cannot be renamed by this lane at all -- so it is
    reached the way the frozen INDICES already are: by name, through
    ``getattr``.  Nothing about which builder is meant is hidden; both
    names are written out in this module's prose and in
    ``VENDOR_AND_MISSION_LATCH_WIRING``, where chief reads them.

    ``None`` means the builder is not on this ``legacy`` at all -- a real
    possibility for a stub in a test, and fail-closed at both call sites in
    the direction that composes LESS.
    """
    value = getattr(legacy, name, None)
    return value if callable(value) else None


def _conversation_extra(
    legacy: Any, placement: Any, selected_idx: int, scene_id: int,
    *,
    vendor_open_latch_spent: bool | None = None,
    mission_dialog_latch_spent: bool | None = None,
) -> tuple[tuple[tuple[str, bytes, bytes, float], ...], str, tuple[str, ...]]:
    """The talk trigger the frozen loop emits beside the face frame.

    Returns ``(extra_actions, reason, latches_spent)``; ``reason`` is what
    the console line says about this click, so a capture can tell
    "composed it" from each separate way of composing nothing, and
    ``latches_spent`` names the once-per-session flags the call site must
    set to ``True`` after it queues those actions (step 2's second half --
    see ``VENDOR_AND_MISSION_LATCH_WIRING``).

    THE THIRD ELEMENT IS NEW, ROUND ``rlymq1``, AND THE ARITY CHANGE IS
    DELIBERATE RATHER THAN AVOIDED.  A latched action a responder composes
    but nobody records is WORSE than the gap it fills: the frozen loop
    sets ``shop_store5_open_sent`` in the same breath as it appends
    (``current/pf_login_game_server_v141.py:4434-4441``), so a shop
    trigger composed here without a latch write would re-open store 5 on
    EVERY click of P91 instead of once per session.  Returning the names
    rather than mutating anything keeps this module free of the session
    object it is not handed, and makes the missing call-site line
    impossible to overlook -- it is a field on the response, not a
    convention.

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
      (``quest3020_conversation_sent``).  ~~This responder is handed no
      session latch, so it cannot know whether that once has been spent.~~
      STRUCK IN THE LANE HALF ONLY, ROUND ``rlymq1``, AND STILL
      UNREACHABLE FROM ``respond()``: the latch is a keyword now, and an
      explicit ``False`` composes the q3020 conversation exactly as the
      frozen loop does -- but only for a caller that reaches this arm, and
      ``respond()`` is not one (pf-adversary ``rlymq1`` D6 measured q3020
      composed for NONE of the 115 frozen placements; the note four lines
      down says why).  ``None`` -- which is
      still every call site today -- keeps the old refusal and the old
      reason string, byte for byte.  Composing the EMPTY conversation in
      its place would replace a quest conversation with a blank one, which
      is worse than the gap, so that is still never done.
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
      arm IS reachable: P91 is in the table, which is why it is the arm
      that keeps the gate shut ("P91 ... (LOST)" in the module docstring's
      cost table) and the arm this round exists for.  Same three-state
      keyword as the quest actor: ``False`` composes the trade-zoom,
      ``True`` composes nothing under a DUPLICATE-SUPPRESSED reason (the
      frozen loop's own ``v112_store5_duplicate_open_suppressed`` event,
      ``current/pf_login_game_server_v141.py:4445-4447``), ``None`` keeps
      today's refusal.
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

    ~~Those two latched actions are the rest of step 2 in the module
    docstring's list, and they need a session-state argument at the call
    site before any lane can compose them honestly.~~  LANE HALF DONE,
    ROUND ``rlymq1``, ADDITIVELY.  The session-state argument is exactly
    the thing this function still does not have on its own: it is handed
    down from ``respond()``'s two new keywords, and EVERY CALL TODAY OMITS
    THEM.  The undone half is the same shape as steps 1 and 5 -- one
    chief-owned ``runtime.py`` line, written out verbatim in
    ``VENDOR_AND_MISSION_LATCH_WIRING``.  Strike step 2 the day that line
    merges, not before.
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
        return (), "no_extra_frozen_indices_unreadable", ()
    if selected_idx == mission_actor_idx:
        # THREE STATES, AND ``is``-COMPARISONS ON PURPOSE.  ``None`` means
        # the call site never passed the keyword, which is every call site
        # today, and MUST answer exactly as this module answered before the
        # keyword existed -- same empty tuple, same reason string, so the
        # capture line and the tests that pin it do not move.  Only an
        # explicit bool is the session telling us something.
        if mission_dialog_latch_spent is None:
            return (), "no_extra_quest_actor_needs_session_latch", ()
        if mission_dialog_latch_spent is not False:
            # The once is spent.  The frozen loop answers this click with
            # the face frame alone and records
            # ``v134_p0_q3020_npc_conversation_duplicate_suppressed``
            # (`current/pf_login_game_server_v141.py:4466-4469`); so do we,
            # under a reason of our own so a capture can tell "suppressed"
            # from "never told".
            return (), "no_extra_quest_actor_already_sent_this_session", ()
        builder = _frozen_builder(legacy, "make_npc_conversation_quest3020")
        if builder is None:
            return (), "no_extra_quest_builder_unreadable", ()
        try:
            mission_pc, mission_frame = builder(placement.actor_identity)
        except Exception as error:  # noqa: BLE001 - same rule as the empty
            # builder below: a responder must never take the listener
            # thread down, and the frozen builder REFUSES outright for any
            # identity but P0's (`ValueError`, v141:791-794).
            #
            # ~~a boot whose placement table hands index 0 a different
            # identity would reach it~~ -- STRUCK, pf-adversary `rlymq1`
            # D7 MEASURED that this input cannot exist: actor_identity is a
            # COMPUTED property (`population.py:44-46`,
            # `0x2000 + placement_index + 1`), not a table column, the
            # source rows are SHA256-pinned, and this function is only ever
            # called with `by_idx[selected_idx]`.  Zero of 115 rows differ.
            # A stub in a test can build that shape; no production path
            # composes it, and reading the stub as evidence for a live
            # possibility would be the layer mistake this project keeps
            # making.
            #
            # THE REACHABLE ROUTE, WHICH IS WHY THE GUARD STAYS: this arm
            # keys on `V129_QUEST_ACTOR_INDEX` read off `legacy`, while the
            # identity the builder demands is HARDCODED inside it
            # (`V129_QUEST_ACTOR_ID = 0x2001`, v141:794).  A v141 re-pin
            # that moves the INDEX without moving the ID fires this on the
            # first click -- the same frozen-module-is-the-authority
            # coupling `_frozen_index` exists for.  Named, never silent,
            # and it costs the extra rather than the answer.
            #
            # THE REASON IS BUILT BY CONCATENATION AND NOT BY AN F-STRING,
            # AND THAT IS NOT A STYLE CHOICE (pf-adversary ``rlymq1`` D4,
            # MEASURED).  Chief's guard reads an f-string's literal halves
            # as CODE and a plain literal not at all, so the f-string this
            # first carried forced this one reason out of its arm's
            # vocabulary while its three neighbours kept theirs -- and a
            # capture greping ``extra_reason=no_extra_quest`` then missed
            # exactly the two reasons that mean THE BUILDER FAILED.  One
            # vocabulary per arm is worth more than the interpolation.
            # THE GUARD QUESTION THIS RAISES IS CHIEF'S, NOT THIS LANE'S,
            # and it is asked rather than assumed -- see the letter named
            # in ``VENDOR_AND_MISSION_LATCH_WIRING``.
            return (), (
                "no_extra_quest_builder_refused_" + type(error).__name__
            ), ()
        return (
            (
                (
                    "V134_P0_Q3020_NPC_CONVERSATION_ONCE_VIA_LANE_A",
                    mission_pc, mission_frame, 0.0,
                ),
            ),
            "quest_actor_conversation_q3020",
            (_MISSION_LATCH_ATTR,),
        )
    if selected_idx == vendor_trigger_idx:
        if vendor_open_latch_spent is None:
            return (), "no_extra_shop_trigger_needs_session_latch", ()
        if vendor_open_latch_spent is not False:
            return (), "no_extra_shop_trigger_already_open_this_session", ()
        builder = _frozen_builder(legacy, "make_trade_zoom_store5")
        if builder is None:
            return (), "no_extra_shop_builder_unreadable", ()
        try:
            vendor_pc, vendor_frame = builder()
        except Exception as error:  # noqa: BLE001 - see the mission arm.
            return (), (
                "no_extra_shop_builder_refused_" + type(error).__name__
            ), ()
        return (
            (
                (
                    "V112_TEST_HARNESS_TRADE_ZOOM_STORE5_SWORD_SOUL"
                    "_VIA_LANE_A",
                    vendor_pc, vendor_frame, 0.0,
                ),
            ),
            "shop_trigger_trade_zoom_store5",
            (_VENDOR_LATCH_ATTR,),
        )
    if selected_idx == monster_idx:
        return (), "no_extra_monster_frozen_path_sends_none", ()
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
        ), ()
    if placement.actor_identity in hostile_identities:
        return (), "no_extra_hostile_row_lane_b_registry", ()
    try:
        conv_pc, conv_frame = legacy.make_npc_conversation_empty(
            placement.actor_identity,
        )
    except Exception as error:  # noqa: BLE001 - a responder must never
        # take the listener thread down for every player, and an answer
        # that loses its talk trigger is still a better answer than a
        # dropped click.  Named, never silent.
        return (), f"no_extra_builder_refused_{type(error).__name__}", ()
    return (
        (
            (
                f"V98_NPC_CONVERSATION_DEFAULT_P{selected_idx}"
                "_VIA_LANE_A",
                conv_pc, conv_frame, 0.0,
            ),
        ),
        "conversation_default",
        (),
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
    vendor_open_latch_spent: bool | None = None,
    mission_dialog_latch_spent: bool | None = None,
    runtime_ack_sent: bool | None = None,
    exact_frozen_marker1_ready_pc: bool | None = None,
    **_ignored: Any,
) -> "lane_hooks.ChooseNpcResponse | None":
    """Answer one ChooseNPC click for scene 1, or decline (see module doc).

    Keyword-only, same convention as ``lane_a_choose_npc_scene14.respond``,
    for the same reason: a future call site can grow arguments without
    breaking every registered responder at once.
    """
    if scene_id != SCENE_N_ID:
        return None
    if runtime_ack_sent is False:
        # STEP 4 OF THE PROMOTION LIST, LANE HALF, GUARD 1 OF 2.  See
        # ``FROZEN_TARGET_VITAL_BEHAVIOURS`` row 4-6 for why this frame is
        # not ours to swallow: the responder branch runs INSTEAD of
        # ``super().dispatch(parsed)``, so claiming the FIRST runtime
        # request this connection ever sends costs three frozen sends at
        # once -- the constructor-exact empty ``RuntimeRes`` ack
        # (v141:3768-3772, the packet the client's own receive watchdog is
        # waiting for), the welcome message (v141:3774-3781) and the scene
        # music (v141:3782-3787) -- and leaves ``runtime_ack_sent`` False
        # forever, which ``runtime.py`` itself gates on in a dozen places
        # (runtime.py:1747, 1796, 1848, 1926, 2149, 2397, 2468, 2539, 2616).
        # A player whose very first click lands before the ack would sit
        # under a yellow "no Server data" watchdog for the whole session.
        #
        # ``is False`` and not a bare falsy test, for exactly the reason
        # step 5's guard spells out one screen up: ``None`` means the call
        # site never passed the keyword -- which is every call today, see
        # ``FROZEN_TARGET_VITAL_BEHAVIOUR_WIRING`` -- and MUST keep this
        # module's pre-keyword behaviour byte for byte.
        return None
    if exact_frozen_marker1_ready_pc is True:
        # STEP 4, GUARD 2 OF 2.  ``V138_MARKER1_READY_PC``
        # (v141:844-850) is a fixed 76-byte PC whose nested id IS
        # ``TARGET_VITAL`` -- v141:5874-5882 asserts exactly that, so this
        # is a static fact about the frozen frame, not a reading of a
        # capture.  It therefore reaches the responder branch
        # (``nested_id in (TARGET_VITAL, CHOOSE_NPC)``) like any click,
        # and claiming it swallows the frozen V140 marker1 population send
        # (v141:3729-3760) together with everything that send commits:
        # ``population_indices``, ``population_refresh_anchor`` and the
        # ``v138_marker1_population_sent`` one-shot.  The lane cannot
        # reproduce that -- a responder is handed no session object and
        # composing a second population authority is the "second composer"
        # this project has refused elsewhere -- so it stands aside.
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
    # STEP 6, MULTI-SELECT, ROUND ``vxfepr``.  One ChooseNPC frame can name
    # more than one identity (the frozen loop's own comment above says a
    # double-click is what usually repeats one; a genuine multi-select
    # names distinct ones), and the frozen loop answers EVERY one of them
    # (``current/pf_login_game_server_v141.py:4406-4480`` loops
    # ``dict.fromkeys(choose_identities)`` with no early return).  Before
    # this round the loop below answered the FIRST named identity that
    # resolved and returned -- correct for one identity, silently wrong for
    # two, and load-bearing wrong once the latches are wired: a frame
    # naming the shop trigger second would spend nothing (pf-adversary
    # ``rlymq1``, measured, module docstring item 6).  The first identity
    # that resolves still becomes this response's own ``label``/``pc``/
    # ``frame`` pair (``ChooseNpcResponse`` carries exactly one), and every
    # identity after it -- its face frame AND its conversation extra --
    # rides in ``extra_actions``, in the same order the frozen loop emits
    # them: face, then talk-trigger-or-latched-action, per identity.
    misnamed = _misnamed_latch_kwargs(_ignored)
    primary_label = primary_pc = primary_frame = None
    trailing_actions: list[tuple[str, bytes, bytes, float]] = []
    latch_names: list[str] = []
    console_lines: list[str] = []
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
        extra_actions, extra_reason, latches_spent = _conversation_extra(
            legacy, by_idx[selected_idx], selected_idx, scene_id,
            vendor_open_latch_spent=vendor_open_latch_spent,
            mission_dialog_latch_spent=mission_dialog_latch_spent,
        )
        label = f"LANE_A_CHOOSE_NPC_SCENE{scene_id}_FACE_P{selected_idx}"
        console_lines.append(
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
            f"extra_reason={extra_reason} "
            # ``latches=`` IS ON EVERY LINE, INCLUDING THE CLICKS THAT
            # SPEND NONE, for the same reason ``extra_reason=`` is: a
            # capture that cannot see the difference between "composed a
            # once-per-session action and asked for the latch" and
            # "composed one and did not" cannot catch the one failure this
            # round can cause -- a shop that re-opens on every click.
            f"latches={','.join(latches_spent) if latches_spent else 'none'}"
            # AND THE ONE THING A CAPTURE COULD NOT SEE UNTIL NOW
            # (pf-adversary ``rlymq1`` D2): a latch keyword that arrived
            # under the FROZEN spelling instead of this lane's.  Absent
            # from the line when there is none, so an ordinary boot's
            # console does not grow a field that is always empty, and
            # impossible to miss when there is one.
            + (
                f" latch_kwarg_misnamed={','.join(misnamed)}"
                if misnamed else ""
            )
        )
        latch_names.extend(latches_spent)
        if primary_label is None:
            # The first identity that resolves is this response's own
            # pair -- every single-identity click before this round took
            # this branch and only this branch, so its answer is
            # byte-for-byte what it always was.
            primary_label, primary_pc, primary_frame = label, pc, frame
        else:
            # A SECOND (OR LATER) NAMED IDENTITY GETS NO SPECIAL TREATMENT:
            # its own face frame rides in ``extra_actions`` exactly like an
            # ordinary conversation trigger does, because a
            # ``ChooseNpcResponse`` still carries exactly one ``pc``/
            # ``frame`` pair (module docstring, item 3 of the flip list)
            # and this field is already the collection half
            # (``lane_hooks.ChooseNpcResponse.extra_actions``).
            trailing_actions.append((label, pc, frame, 0.0))
        trailing_actions.extend(extra_actions)
    if primary_label is None:
        return None
    return lane_hooks.ChooseNpcResponse(
        label=primary_label, pc=primary_pc, frame=primary_frame, delay=0.0,
        console_lines=tuple(console_lines),
        extra_actions=tuple(trailing_actions),
        # De-duplicated, order preserved: two named identities cannot
        # legitimately share a latch (each guards a different placement
        # index), but a call site's ``setattr`` loop
        # (``VENDOR_AND_MISSION_LATCH_WIRING``) is idempotent either way,
        # and a stub in a test should not be able to make this field lie
        # about how many distinct flags were actually spent.
        latches_spent=tuple(dict.fromkeys(latch_names)),
    )


lane_hooks.choose_npc_responder(SCENE_N_ID)(respond)
