"""ONE authority for "what HP does a clicked scene's hostile body carry" -
LANE-A.

WHY THIS FILE EXISTS, AND IT IS A DEFECT REPORT RATHER THAN A REFACTOR.
``lane_hooks/lane_a_choose_npc_scene2.py`` and
``lane_hooks/lane_a_choose_npc_scene14.py`` are two production responders
that splice the same kind of hostile body into their answer, and on
2026-09-02 they answered DIFFERENTLY on the same input: scene 2 read a
combat ledger and refused, scene 14 swallowed the same keyword in
``**_ignored`` and sent the table ceiling (chief's letter
``20260902_1918``, item 4.2, measured).  ``COO-DECISION 20260902_1945``
requires both to move in one commit; a rule written twice is a rule that
drifts again, so it is written here once and imported by both.

THE RULE, AND EVERY BRANCH OF IT IS A DECISION SOMEBODY MADE.

* No ledger, an unreadable ledger, a ledger with no row for this identity,
  or a row whose HP is not a non-negative int -> the table CEILING, and
  ``from_ledger`` is FALSE.  Fail-SAFE, not fail-loud: a raise here would
  turn a redrawn HP bar into a dropped click (pf-adversary D8, round
  ``cu1il6``, is why the flag reports the OUTCOME and not the argument).
* A row with HP above zero -> that HP, ``from_ledger`` TRUE.  This is the
  wound the census kept and the reason ``COO-DECISION 20260902_1843``
  wanted the ledger at the call site at all.
* A row with HP zero -> ``(None, True)``: THE LEDGER SAYS THIS BODY IS
  DEAD.  What a caller does with that is the caller's decision, and there
  are exactly two legitimate ones (``COO-DECISION 20260902_1945``):
  - the body is the one the player CLICKED -> refuse that identity by
    name, and answer the rest of the frame normally;
  - the body is any OTHER body in the same frame -> it is not the click's
    business, and the frame is still owed to the player.

WHAT IS *NOT* A LEGITIMATE ANSWER, MEASURED RATHER THAN ARGUED.  Refusing
the WHOLE click because some other actor in the scene is dead: chief drove
it on the real dispatcher and one kill silenced every click in scene 2
until a reconnect, because ``_sync_combat_scene_state`` pulls the death
back out of ``mob_death_register`` on every re-entry.  "Click anything and
nothing happens" is indistinguishable from a dead server, and scene 2 is
the one scene where kills drop loot -- the scene ``GT-204`` has to read.
That behaviour was on this lane's own branch, green, with a test that
asserted it as desired; it never reached ``main`` because the call-site
keyword that would have armed it never landed.

~~THE DEBT THIS FILE DOES NOT PAY, NAMED SO NOBODY READS IT AS PAID.~~
PAID IN ROUND ``qa86im`` (``COO-DECISION 20260903_0252``): :func:`corpse_
body_for` composes the corpse, both responders take the keyword
``mob_death_register`` for it, and the console counts a corpse separately
from a ceiling (``dead_as_corpse=`` beside ``dead_at_ceiling=``).  THE OLD
PARAGRAPH IS KEPT BELOW UNCHANGED because every sentence in it is still
true of a boot whose call site passes no register -- which is every boot
until chief's line lands -- and because it names the reason the ceiling
branch may not simply be deleted.  For a
dead body that is NOT the clicked one, this lane has no corpse to send:
``mob_death.death_actor_entry`` needs the death register, which the
ChooseNPC call site does not pass.  So the caller sends the table ceiling
-- exactly what every click on ``main`` sends today for every hostile body
-- and SAYS SO on the console, one named line per body plus a count.
``RE-092`` forbids the alternative (omitting the row deletes the actor
from the client's set), and a resurrection nobody counted is worse than a
resurrection everybody can grep.  The way out is the bigger path chief
offered in the same letter: ``mob_death_register=`` at the call site
alongside the ledger, opened as its own ticket once the multi-vital walker
is on ``main``.
"""
from __future__ import annotations

from typing import Any


def current_hp_of(mob: Any, ledger: Any) -> tuple[int | None, bool]:
    """``(hp, hp_came_from_the_ledger)``; ``(None, True)`` means DEAD.

    See the module docstring for every branch.  Never raises for a ledger
    of any shape -- WIDENED after pf-adversary drove two shapes past the
    first version of this function (round ``4uztfj``):

    * the ``current_hp`` READ is inside the ``try`` as well as the
      ``balance_of`` call.  A balance whose ``current_hp`` is a property
      that raises used to propagate out of ``respond`` and into the
      listener thread -- a dropped click, which is the outcome this whole
      function exists to avoid;
    * an HP ABOVE this mob's table ceiling answers the CEILING and is not
      counted as a ledger read.  ``2**40`` passed the old guard and then
      crashed inside ``field_mobs.hostile_npc_attr``'s own u32 contract; a
      value merely above the ceiling would have gone on the wire as a
      monster with more HP than its table allows.  A ledger whose maximum
      disagrees with the table is a ledger this lane does not understand
      (``mob_ledger_admission`` exists because those two really can
      disagree), so it is refused rather than believed.
    """
    if ledger is None:
        return mob.max_hp, False
    try:
        balance = ledger.balance_of(mob.actor_identity)
        current = getattr(balance, "current_hp", None)
    except Exception:  # noqa: BLE001 - fail-safe, see the docstring
        return mob.max_hp, False
    if type(current) is not int or type(current) is bool:
        # A boolean or non-integer HP is a ledger this lane does not
        # understand, not a wound.  ``type(...) is not int`` already
        # excludes ``bool``; the second clause is kept because a reader
        # checking "can True reach the wire?" must find the answer here
        # rather than in a chain of two implications.
        return mob.max_hp, False
    if current < 0 or current > mob.max_hp:
        # Ceiling, and NOT counted as a ledger read: the console line must
        # not claim a row it refused.
        return mob.max_hp, False
    if current == 0:
        return None, True
    return current, True


def ledger_for_this_scene(
    scene_id: Any, ledger: Any, roster: Any, *, scene_folder: Any = None,
) -> Any:
    """The ledger a responder for ``scene_id`` may read, or ``None``.

    ADDED ROUND ``4uztfj`` AFTER pf-adversary REFUTED THE SENTENCE THIS
    LANE HAD BEEN LEANING ON.  ``lane_a_choose_npc_scene2``'s own docstring
    argued the per-identity read was safe because "scene 1's and scene 2's
    rosters share NO identity", and treated a collision as hypothetical.
    Measured on this tree: scene 2's and scene 14's hostile rosters BOTH
    contain identity ``0x2058`` (placement 87 in each), and a scene-14
    ledger carrying that row at 0 HP made a click on scene 2's LIVING
    placement 87 refuse itself -- a click dropped by a kill in another
    scene.  Both scenes are this lane's, so the collision is not a future
    scene pair; it is this commit's own two responders.

    The fix is the house function rather than a new rule:
    ``mob_ledger_admission.ledger_for_scene`` is what the census path
    already asks, and it answers ``None`` for a ledger tagged with another
    scene.  ``None`` means "compose without consulting HP", which is
    exactly what every ledger-less path in this tree already does.

    Fail-safe like everything else here: any error answers ``None``.
    """
    if ledger is None:
        return None
    try:
        from . import mob_ledger_admission
        admitted = mob_ledger_admission.ledger_for_scene(
            scene_id, ledger, roster=roster)
    except Exception:  # noqa: BLE001 - fail-safe, see the docstring
        admitted = None
    if admitted is not None:
        return admitted
    # THE HOUSE FUNCTION CANNOT ANSWER FOR EVERY SCENE, MEASURED RATHER
    # THAN ASSUMED.  ``admit_ledger`` resolves a scene id to a FOLDER
    # through ``field_mobs``, and ``field_mobs`` names no scene 14 at all
    # (the same fact ``mob_scene_recompose``'s own table records for it),
    # so for scene 14 it reports ``scene=None``, ``state=other_scene`` and
    # refuses EVERY ledger -- which would have put scene 14 silently back
    # on the table ceiling in the same commit that gave it the ledger.
    # So when the house cannot decide, ask the narrower question the tag
    # itself answers, and ONLY that one: does this ledger say it belongs to
    # this scene's own folder?  A ledger from the other scene still fails
    # it, which is the collision this function exists for.
    if scene_folder and getattr(ledger, "scene", None) == scene_folder:
        return ledger
    return None


def corpse_body_for(
    legacy: Any, mob: Any, register: Any, *,
    scene_id: int, scene_sequence: int,
) -> bytes | None:
    """The corpse NPCAttr bytes for a body the register buried, else ``None``.

    THE DEBT NAMED IN THIS MODULE'S OWN DOCSTRING, PAID.  Until this round
    both responders had exactly one thing to put in a frame for a monster
    that is dead: the table CEILING, a full HP bar on a corpse, counted and
    named because the alternative (omitting the row) DELETES the actor from
    the client's set (``RE-092``).  ``COO-DECISION 20260903_0252`` gave this
    lane the second half of chief's offer -- ``mob_death_register=`` at the
    ChooseNPC call site beside the ledger -- so a click can now answer with
    the body ``mob_death`` composes for the arrival census instead.

    WHY THE REGISTER AND NOT THE LEDGER DECIDES WHO IS DEAD HERE.  The
    ledger says "0 HP"; the register says "this identity in THIS scene is
    dead, and here is the kill it came from".  ``mob_death.corpse_npc_attr``
    needs the second statement, and ``_sync_combat_scene_state`` rebuilds
    the ledger from the register on every scene re-entry (chief's letter
    ``20260902_1918``), so the register is the older and narrower of the
    two.  It is also SCENE-KEYED by construction
    (``DeathRegister.is_dead(identity, scene)``, COO-DECISION
    2026-08-27T22:49): this function asks with ``mob.scene``, the scene the
    roster row itself carries, so a scene-14 kill can never bury scene 2's
    placement 87 through the identity those two rosters really do share --
    the collision ``ledger_for_this_scene`` exists for, closed here by the
    key rather than by a second admission call.

    ``scene_id`` / ``scene_sequence`` ARE THE CALLER'S, NOT THIS MODULE'S
    DEFAULTS, and that is deliberate.  Each responder already sends its
    LIVE hostile bodies with a particular pair (scene 2 sends
    ``field_mobs.SCENE_ID`` -- 1, deliberately, because that is what the
    arrival splice sent; scene 14 sends 14), and a corpse that re-states
    that field differently from the live body it replaces would be a new
    defect of exactly the class scene 14's responder exists to stop.  The
    composer's own self-check makes the pairing measurable rather than
    assumed: ``corpse_npc_attr`` reproduces ``field_mobs.hostile_npc_attr``
    byte for byte for a live body with these same arguments and refuses if
    it cannot, so the corpse is that known-good body plus exactly the five
    bytes of the death timer (measured this round: scene 2 122 -> 127,
    scene 14 108 -> 113).

    THE TIMER IS THE FLOOR, NOT A TRANSITION.  ``mob_death.
    DEAD_TIMER_SECONDS`` (0.0) is the steady state of a body that is
    already dead -- the same value ``repopulation_entries`` gives every
    dead row it is not currently transitioning.  A click is never the frame
    that kills anything, so it never composes the dying side of the gate.

    FAIL-SAFE, LIKE EVERY OTHER RULE IN THIS FILE.  A register of the wrong
    type, a register with no row for this body, or a composer that refuses
    for any reason at all answers ``None``, and ``None`` means "the caller
    does what it did before this round": the ceiling, counted and named.
    A raise here would turn a redrawn HP bar into a dropped click, which is
    the outcome this whole module exists to avoid.
    """
    if register is None:
        return None
    try:
        from . import mob_death
        if type(register) is not mob_death.DeathRegister:
            # Fail CLOSED on the type: an object that merely has an
            # ``is_dead`` attribute is not a register this lane can read a
            # grave out of, and guessing would put an invented corpse on
            # the wire.
            return None
        if not register.is_dead(mob.actor_identity, mob.scene):
            return None
        return mob_death.corpse_npc_attr(
            legacy, mob,
            death_timer=mob_death.DEAD_TIMER_SECONDS,
            scene_id=scene_id, scene_sequence=scene_sequence,
        )
    except Exception:  # noqa: BLE001 - fail-safe, see the docstring
        return None


def hp_token(
    live_hostile_bodies: int, bodies_read_from_the_ledger: int,
) -> str:
    """What the ``hp=`` field of an ANSWERED line may honestly say.

    FOUND BY THIS ROUND'S OWN ADVERSARIAL PROBE, AND IT IS THE DEFECT
    SHAPE pf-adversary D8 NAMED IN ROUND ``cu1il6``: report the OUTCOME,
    not the argument.  Both responders used to print ``hp=ceiling``
    whenever no body had been read from the ledger -- true while every
    hostile body in a frame was a live one, and FALSE the moment corpses
    entered the picture.  Bury all twelve of scene 2's hostile rows and
    the frame contains no ceiling at all, yet the old expression still
    announced one, because a corpse takes its HP from neither source.

    So the three values mean exactly this, and nothing wider:

    * ``ledger``   -- at least one LIVE hostile body carried HP this
      responder read out of the admitted ledger.  It is still NOT
      evidence that a wound survived (``COO-DECISION 20260902_1945``
      item 4.3): only ``wounded=`` is.
    * ``ceiling``  -- there are live hostile bodies and every one of them
      carries its table ceiling.
    * ``no_live_body`` -- there is no live hostile body in this frame to
      describe.  Either the scene has no hostile rows at all, or every
      one of them is in the answer as a corpse (``dead_as_corpse=``).
    """
    if live_hostile_bodies <= 0:
        return "no_live_body"
    return "ledger" if bodies_read_from_the_ledger else "ceiling"


def hp_for_a_body_that_is_not_the_click(
    mob: Any, ledger: Any
) -> tuple[int, bool, bool]:
    """``(hp_to_send, from_ledger, the_ledger_said_this_body_is_dead)``.

    The one place the ceiling-for-a-corpse debt is taken, so both
    responders take it identically and both can count it.  ``from_ledger``
    is FALSE for a dead body on purpose: the console line's ``hp=ledger``
    token must describe the bytes that went out, and what went out for
    this body is the ceiling.
    """
    hp, from_ledger = current_hp_of(mob, ledger)
    if hp is None:
        return mob.max_hp, False, True
    return hp, from_ledger, False
