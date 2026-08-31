"""LANE-B / BUILD-004+005: the gates between scene 14's ALREADY-SHIPPING
actors and any of them being fightable, each one measured rather than
argued.

RENAMED AND REWRITTEN IN ROUND 6cm6ry after pf-adversary broke the first
draft's central claim.  The first draft was called ``mob_combat_bg0015_gap``
and said the missing thing was the combat LEDGER.  That was wrong twice
over, and both corrections are load-bearing enough to state before anything
else:

* ~~"a hit on a Bg0015 actor refuses with mob_combat.REFUSE_TARGET_NOT_IN_
  LEDGER"~~ -- WITHDRAWN, MEASURED FALSE.  ``mob_combat
  .attack_from_observed_action`` (mob_combat.py:1667-1680) loops the
  ROSTER first and returns ``None`` when the target is not in it; only a
  target that IS in the roster and NOT in the ledger reaches that refusal.
  ``_sync_combat_scene_state`` derives roster AND ledger from the same
  ``field_mobs.load_roster(folder)`` call, so at the one wired call site
  that state is unconstructable.  What a player's swing in scene 14
  actually produces today is the event
  :data:`WIRED_ANSWER_FOR_A_TABLELESS_SCENE`, and
  ``tests/test_scene_scoped_combat_wiring.py::test_an_addressed_tableless_
  scene_answers_over_an_empty_roster`` already pins exactly that outcome for
  exactly this class of scene.  The ledger is a free consequence of the
  roster at that call site; what is missing is the ROSTER.
* ~~"the CORE-REQUEST would ship 12 monsters that look hostile and cannot
  be hit"~~ -- WITHDRAWN, UNDERSTATED.  Scene 14 is already open at login
  and lane A's ``lane_hooks.scene_census_composer(14)`` is live and
  ``production_allowed`` TODAY, shipping its whole roster of actors into a
  real player's client.  So the true fact is larger than the first draft's:
  EVERY actor standing in scene 14 right now is unhittable, and the hostile
  splice changes 12 of their APPEARANCES, not their hittability.

WHAT A PLAYER SEES BECAUSE OF THIS FILE, STATED HONESTLY AND FIRST.
Nothing.  This module measures; it has no ``runtime.py`` call site (that
file is chief's), composes no frame, and registers nothing.

THE FOUR GATES, AND WHO OWNS EACH.  Making scene 14's monsters fightable is
not "one registration".  Measured this round by actually performing the
one-line registration on a scratch tree and running the whole suite (35
failed / 6056 passed; 10 named tests across 5 files that are not this
round's own), the gates are:

  1. ROSTER REGISTRATION -- ``field_mobs._SCENE_TABLE_MODULES`` must name
     Bg0015 before ``load_roster``/``roster_for_scene_id`` answer anything
     for scene 14.  Lane B's file; blocked from inside ``src/`` by gate 2.
     Measured by :func:`roster_gate_open`.
  2. APPROVED-IMPORTER GUARD -- the Bg0015 table module's own guard test
     (deliberately not spelled out here: that guard's literal-string sweep
     flags any file under ``src/`` that names the table module, and the
     test's filename contains that name)
     allows exactly ONE importer of Bg0015's table under ``src/`` and
     excludes ``field_mobs.py`` BY NAME, by AST and by literal-string sweep
     (so the ``importlib`` route is closed too).  That guard encodes
     COO-DECISION 2026-08-26T12:46+07:00 as narrowed by COO-DECISION
     2026-08-31T16:48+07:00, so widening it is a COO/owner scope decision,
     not a lane edit.  Gate 1 cannot land while this stands.
  3. DEATH RULING -- ``mob_death.ruling_for`` refuses all 12 Bg0015 rows
     with ``target_outside_the_sanctioned_scope`` today, because
     ``WIDENING_RULINGS`` carries owner letters for 916/bg0001/Bg0002/the
     diag deer and none for Bg0015's seven templates.  Without a new owner
     letter, registered Bg0015 monsters would take damage and never die.
     An owner-only gate by construction.  Measured by
     :func:`templates_without_a_death_ruling`.
  4. SCENE RECOMPOSE -- ``mob_scene_recompose.composer_scene_ids()`` is
     ``(1, 2)``; scene 14 has no composer, and that module's own test
     (``test_every_scene_this_lane_ships_monsters_for_can_be_recomposed``)
     says in its own words that a scene shipping monsters without one is
     the defect.  Without it, the first swing in scene 14 would ship the
     one-entry recompose frame RE-092 proved erases every other actor from
     the client.  Lane B's own module: THIS is the gate this lane can build
     outright.  Measured by :func:`recompose_gate_open`.

WHAT THIS MODULE DELIBERATELY DOES NOT DO.  It does not register Bg0015,
does not widen any guard, does not write a ruling, and does not compose
anything.  It reports gate status from live data so a decision about
sequencing is made on measured facts instead of on a remembered docstring
-- which is precisely how the first draft of this file went wrong.

NONCLAIM ABOUT THE COLLISION.  Registering Bg0015 would make its placement
87 share wire identity ``0x2058`` with Bg0002's placement 87.  ~~"this is
not a new class of risk -- bg0001/Bg0002 already collide at 0x2068/0x206a
today"~~ -- WITHDRAWN, MEASURED FALSE: ``field_mobs
.cross_scene_identity_collisions()`` returns ``()`` at HEAD (round 8ftmbx
withdrew every bg0001 side; the emptiness is pinned by
``tests/test_field_mobs.py::test_default_set_is_the_two_live_known_scenes_
only`` and again in ``tests/test_mob_death.py``, whose message asks for a
real collision pair the day one exists again).  The ``0x2068``/``0x206a``
sentence lives in ``mob_combat.open_ledger_for_scene_id``'s docstring as
HISTORY -- ``load_roster``'s own docstring carries the strikethrough
correction -- and the first draft of this file read it as present tense.
So the honest statement is the opposite of the first draft's: registering
Bg0015 would create this tree's FIRST live cross-scene identity collision,
against a property two tests currently assert is empty.  The collision
itself is not novel as a FACT -- ``tests/test_field_mobs.py::test_all_
three_known_tables_together_find_one_pairwise_collision`` (round ua236k)
already pins placement 87, templates 34 vs 924, exactly one collision --
only its consequences-if-registered are what this module adds.
"""

from __future__ import annotations

from typing import Any, Iterable

from . import field_mob_hostile_bg0015
from . import field_mobs
from . import mob_death
from . import mob_scene_recompose

# world_scene_folder._FOLDER_BY_SCENE_ID: (2, "Bg0002"), (14, "Bg0015").
BG0002_SCENE_ID = 2
SCENE14_SCENE_ID = 14
BG0015_FOLDER = "Bg0015"

# The event ``runtime.py`` appends for a swing at any actor in an addressed
# scene this lane ships no table for -- measured, not assumed: combat
# dispatch calls mob_combat.attack_from_observed_action, that function walks
# the ROSTER and returns None when the target is not a row in it, and the
# dispatch turns None into this string (runtime.py:4226).  The refusal the
# first draft of this file named instead (REFUSE_TARGET_NOT_IN_LEDGER) needs
# a target that is in the roster and absent from the ledger, which the one
# wired call site cannot build: it fills both from one load_roster call.
WIRED_ANSWER_FOR_A_TABLELESS_SCENE = "mob_combat_target_not_a_field_mob_no_reply"

GATE_ROSTER_REGISTRATION = "roster_registration_scene_table_modules"
GATE_APPROVED_IMPORTER = "approved_importer_guard_widening"
GATE_DEATH_RULING = "owner_widening_ruling_for_bg0015_templates"
GATE_SCENE_RECOMPOSE = "scene_recompose_composer_for_scene_14"

#: Gate -> who can move it.  Written here rather than only in a letter so a
#: reader of the code finds the division of labour with the measurement.
GATE_OWNERS = {
    GATE_ROSTER_REGISTRATION: "LANE-B file, blocked by the guard gate below",
    GATE_APPROVED_IMPORTER: "COO/owner (the guard encodes a COO decision)",
    GATE_DEATH_RULING: "owner (WIDENING_RULINGS takes owner letters only)",
    GATE_SCENE_RECOMPOSE: "LANE-B, buildable today",
}


class MobCombatBg0015GateError(ValueError):
    """A refusal from this module, always with a reason in the message."""


def roster_gate_open() -> bool:
    """Does ``field_mobs`` ship a roster for Bg0015 today?  (Gate 1.)"""
    return BG0015_FOLDER in field_mobs.live_scenes()


def scene14_roster_size_today() -> int:
    """How many rows ``roster_for_scene_id(14)`` answers with today.

    Zero while gate 1 is closed -- and zero rows is what makes every swing
    in scene 14 answer :data:`WIRED_ANSWER_FOR_A_TABLELESS_SCENE`, because
    ``attack_from_observed_action`` never finds the target in the roster it
    was handed.  The ledger being empty as well is a consequence of the
    same call, not a second cause.
    """
    return len(field_mobs.roster_for_scene_id(SCENE14_SCENE_ID))


def templates_without_a_death_ruling() -> tuple[int, ...]:
    """Bg0015 template ids ``mob_death.ruling_for`` refuses, ascending.
    (Gate 3.)

    Calls the real predicate on the real rows and records which ones raise
    ``MobDeathContractError`` -- never a hand-typed list, so an owner letter
    landing for one template shortens this answer on its own.
    """
    refused = set()
    for mob in field_mob_hostile_bg0015.scene14_hostile_roster():
        try:
            mob_death.ruling_for(mob)
        except mob_death.MobDeathContractError:
            refused.add(mob.template_id)
    return tuple(sorted(refused))


def death_ruling_gate_open() -> bool:
    """True when every Bg0015 row has an owner letter to die under."""
    return templates_without_a_death_ruling() == ()


def recompose_gate_open() -> bool:
    """Does ``mob_scene_recompose`` know how to recompose scene 14?
    (Gate 4.)"""
    return SCENE14_SCENE_ID in mob_scene_recompose.composer_scene_ids()


def closed_gates() -> tuple[str, ...]:
    """Every gate that is shut today, in the order they must be thought
    about.  Gate 2 is a policy gate living in a test file, so it is
    reported through the state it enforces (``field_mobs`` not importing
    the table, which is gate 1 being shut) rather than by parsing a test.
    """
    shut = []
    if not roster_gate_open():
        shut.append(GATE_ROSTER_REGISTRATION)
        shut.append(GATE_APPROVED_IMPORTER)
    if not death_ruling_gate_open():
        shut.append(GATE_DEATH_RULING)
    if not recompose_gate_open():
        shut.append(GATE_SCENE_RECOMPOSE)
    return tuple(shut)


def splice_identities(legacy: Any) -> tuple[int, ...]:
    """The identities the VISUAL path actually splices, ascending.

    Read off ``field_mob_hostile_bg0015.scene14_hostile_overrides(legacy)``
    -- the real dict chief's future branch hands
    ``mob_scene_recompose.splice_identity_override`` -- and not off the
    roster the first draft of this file compared against itself.  Comparing
    the roster to the roster proved nothing (pf-adversary: shifting 11 of
    the 12 placement indices by +100 left that check green with 11
    fabricated identities); an INDEPENDENT side has to come from outside
    this lane's table, which is what :func:`splice_identities_missing_from`
    takes as an argument.
    """
    return tuple(sorted(
        field_mob_hostile_bg0015.scene14_hostile_overrides(legacy)))


def splice_identities_missing_from(
        external_identities: Iterable[int], legacy: Any) -> tuple[int, ...]:
    """Which spliced identities are absent from an INDEPENDENTLY built set.

    ``external_identities`` is meant to be the actor identities lane A's own
    census actually ships for scene 14 (a different module, a different
    lane's placement data).  A splice identity missing from that set is a
    body the client was never sent, so the splice would decorate nothing --
    fail closed and name them rather than reporting a count that looks fine.
    """
    external = set()
    for identity in external_identities:
        if type(identity) is not int or identity <= 0:
            raise MobCombatBg0015GateError(
                "external identities must be positive ints, got %r"
                % (identity,))
        external.add(identity)
    if not external:
        raise MobCombatBg0015GateError(
            "an empty external identity set cannot back anything: refusing "
            "to report 'all twelve missing' as if it were a measurement")
    return tuple(
        identity for identity in splice_identities(legacy)
        if identity not in external
    )


def owner_refused_placements_for_scene14() -> tuple[int, ...]:
    """Owner-refused placements Bg0015 carries today.  Empty -- and that
    emptiness is why two other numbers in this project happen to agree.

    ``field_mobs.load_roster`` drops ``OWNER_REFUSED_PLACEMENTS`` rows
    (eight of Bg0002's today) while
    ``field_mob_hostile_bg0015.scene14_hostile_roster`` does not filter at
    all.  For Bg0015 the two therefore agree ONLY because the refusal list
    has no Bg0015 entry: the agreement is a property of today's data, not
    of the code.  The day an owner refuses a Bg0015 placement, a registered
    roster and the splice dict would disagree silently -- said here, and
    pinned by this module's own test, instead of discovered later.
    """
    refused = field_mobs.OWNER_REFUSED_PLACEMENTS.get(BG0015_FOLDER, ())
    return tuple(sorted(refused))


def live_cross_scene_collisions_today() -> tuple[dict, ...]:
    """What ``field_mobs.cross_scene_identity_collisions()`` reports for the
    scenes that are actually live -- ``()`` at HEAD.

    Measured here because the first draft of this module claimed the
    opposite from a historical docstring sentence.  A non-empty answer means
    this project has a live cross-scene collision again and the framing
    below (Bg0015 would be the FIRST) has to be rewritten.
    """
    return field_mobs.cross_scene_identity_collisions()


def bg0002_bg0015_identity_collisions() -> tuple[int, ...]:
    """Identities Bg0002's live roster and Bg0015's hostile roster share.

    Exactly ``(0x2058,)`` today (placement 87 on both sides), the same
    survivor ``tests/test_field_mobs.py::test_all_three_known_tables_
    together_find_one_pairwise_collision`` already pins from the raw
    tables.  This function reads Bg0002 through the LIVE, owner-filtered
    path instead (``roster_for_scene_id``), so the day an owner refusal
    removes placement 87 from Bg0002 the two answers diverge on purpose.
    """
    bg0002 = {
        mob.actor_identity
        for mob in field_mobs.roster_for_scene_id(BG0002_SCENE_ID)
    }
    bg0015 = {
        mob.actor_identity
        for mob in field_mob_hostile_bg0015.scene14_hostile_roster()
    }
    return tuple(sorted(bg0002 & bg0015))
