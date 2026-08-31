"""LANE-B / BUILD-004+005: what registering Bg0015 would actually do,
measured at HEAD by this lane, one measurement per function.

THE HEADLINE, AND IT IS NOT "MONSTERS THAT CANNOT DIE".  With Bg0015
registered in ``field_mobs._SCENE_TABLE_MODULES``, the FIRST swing in scene
14 raises out of ``dispatch`` and unwinds the listener thread.  Measured
end-to-end this round (real login -> StartGame -> scene 14 -> one
ActionVital, with the registration applied in-process):

    runtime.py:4156  _dispatch_mob_combat: roster = self._sync_combat_scene_state()
    runtime.py:4103  _sync_combat_scene_state: mob_ai_control.open_register(...)
    mob_ai_control.py:403
    MobAiControlError: ai_row_missing: placement 22 points at AI_COMBAT 301,
    which is not in the mined rows: regenerate field_mob_ai_tables

Nothing on that path catches it: ``_sync_combat_scene_state`` has no
``try`` at all, and the call at 4156 sits ABOVE every ``except`` in
``_dispatch_mob_combat`` (the first is at 4214).  ``MobAiControlError``
subclasses ``ValueError``, so it would have been swallowed had the call sat
a few dozen lines lower -- it does not.  All 12 Bg0015 rows want
``AI_COMBAT`` ids the mined table does not carry, and placement 87
additionally wants ``AI_WANDER 22``; see :func:`ai_rows_missing_for_scene14`.
Clearing this needs a regenerated ``field_mob_ai_tables`` -- a miner run
against bridge gamedata, which is not a code edit any lane can make from
this tree.

WHY THIS FILE EXISTS AT ALL.  Earlier drafts of this round reported a
"gate table" assembled from predicates that were already readable
(``live_scenes()``, ``composer_scene_ids()``, ``ruling_for``).  Not one of
them walked the path a swing actually takes, which is why the raise above --
two lines below the ``load_roster`` call those drafts quoted -- was missed
twice.  The procedure that found it, and its limits, are written down in
:data:`ENUMERATION_PROCEDURE` rather than left as a lesson nobody can rerun.

WHAT A PLAYER SEES BECAUSE OF THIS FILE: nothing.  No ``runtime.py`` call
site, no frame composed, nothing registered.

WHAT THIS FILE DOES NOT DO ANY MORE, AND WHY.  Earlier drafts shipped a
``GATE_OWNERS`` table naming who owns each precondition.  WITHDRAWN: two
successive drafts guessed ownership wrong -- once sending COO to widen a
test allowlist that turns out to name nothing, once promising a composer
this lane cannot write yet -- in a document whose whole purpose is to stop
someone doing something destructive.  This file now reports measurements
and marks inferences as inferences; who moves what is a question for
chief/COO, asked in this round's letter, not answered here.

WHAT IS MEASURED, AND WHAT IS ONLY INFERRED
-------------------------------------------
MEASURED (each has a test that fails if it stops being true):
  * the raise above, end to end, and its cause
    (:func:`ai_rows_missing_for_scene14`, :func:`open_register_refusal_for_scene14`);
  * ``field_mobs`` ships no Bg0015 roster today (:func:`roster_gate_open`);
  * no Bg0015 template has a death ruling
    (:func:`templates_without_a_death_ruling`);
  * ``mob_scene_recompose`` has no scene-14 composer but DOES carry a dated
    written acknowledgement of that hole, whose own words are that it
    composes one in the same round the first roster row lands
    (:func:`recompose_status`);
  * the visual splice preserves all 81 of lane A's census identities and
    rewrites exactly 12 entries -- run in this module's tests rather than
    inherited from lane A's letter, which explicitly disclaims having
    tested it;
  * registering Bg0015 would create the tree's first live cross-scene
    identity collision (:func:`live_cross_scene_collisions_today` is ``()``
    today; :func:`bg0002_bg0015_identity_collisions` is ``(0x2058,)``).

INFERRED, NOT EXECUTED -- treat as a lead, not a finding:
  * ``_apply_mob_death_census_override`` appears only at ``runtime.py:7508``
    (bg0002 branch) and ``runtime.py:7950`` (bg0001 branch), while scene 14
    composes through ``lane_hooks.scene_census_composer`` at
    ``runtime.py:7626``, which has no such step -- so a census rebuild in
    scene 14 would LIKELY heal every wounded monster back to its ceiling,
    the defect ``mob_census_hostility.hostile_override_for_scene_id``'s own
    docstring names.  READ-ONLY INFERENCE: nothing in this round drove that
    path, because the raise above happens first and ends the session.

WITHDRAWN CLAIMS FROM EARLIER DRAFTS OF THIS ROUND, KEPT VISIBLE
----------------------------------------------------------------
* ~~"a hit refuses with mob_combat.REFUSE_TARGET_NOT_IN_LEDGER"~~ -- false;
  ``attack_from_observed_action`` walks the roster first, so the wired call
  site cannot build that state.  Today's answer is
  :data:`WIRED_ANSWER_FOR_A_TABLELESS_SCENE`.
* ~~"the approved-importer guard names field_mobs.py and encodes a COO
  decision, so lane B cannot register at all"~~ -- false: that guard's CODE
  is an allowlist holding one path; ``field_mobs.py`` appears only in its
  DOCSTRING prose, excluded by omission exactly like every other file under
  ``src/``.  What actually stands in the way of registration is this lane's
  own pinned assertions plus the raise above.  Sending COO to move that
  allowlist would have been sending them to move something that never
  blocked it.
* ~~"the scene-14 recompose composer is lane B's to build next round"~~ --
  false: ``mob_scene_recompose``'s own text says it composes scene 14 "in
  the same round its first roster row lands", so it is downstream of
  registration, not an independent choice.
* ~~"bg0001/Bg0002 already collide, so this is not a new class of risk"~~ --
  false at HEAD; see :func:`live_cross_scene_collisions_today`.
"""

from __future__ import annotations

from typing import Any, Iterable

from . import field_mob_ai_tables
from . import field_mob_hostile_bg0015
from . import field_mobs
from . import mob_ai_control
from . import mob_death
from . import mob_scene_recompose

# world_scene_folder._FOLDER_BY_SCENE_ID: (2, "Bg0002"), (14, "Bg0015").
BG0002_SCENE_ID = 2
SCENE14_SCENE_ID = 14
BG0015_FOLDER = "Bg0015"

# The event runtime.py appends today for a swing in an addressed scene this
# lane ships no table for.  NOTE WHAT THIS DOES AND DOES NOT IDENTIFY: any
# integer target produces it in scene 14 (0xDEADBEEF as readily as 0x2017),
# because the roster it is checked against is empty.  It pins "scene 14
# resolves to folder Bg0015 over an empty roster", not anything about the
# twelve identities specifically.
WIRED_ANSWER_FOR_A_TABLELESS_SCENE = "mob_combat_target_not_a_field_mob_no_reply"

#: How the raise in this module's headline was found, written down so the
#: next round can rerun it instead of re-deriving it -- and so the honest
#: limit of the finding is visible.  Steps 1-2 are what earlier drafts did;
#: step 3 is what they skipped and what actually found it.
ENUMERATION_PROCEDURE = (
    "1. read the predicates a scene must satisfy (live_scenes, "
    "composer_scene_ids, ruling_for) -- cheap, and finds only what someone "
    "already thought to name; "
    "2. apply the change on a scratch tree and run the suite -- finds "
    "whatever the suite already pins, and nothing it does not; "
    "3. APPLY THE CHANGE AND THEN DRIVE ONE REAL REQUEST END TO END through "
    "the production dispatch (login -> StartGame -> scene -> ActionVital), "
    "reading the traceback rather than the event list.  Step 3 is the only "
    "one that found the ai_row_missing raise, because that raise happens in "
    "a helper two lines below the call earlier drafts quoted and no test "
    "drives it. "
    "WHAT THIS PROCEDURE STILL DOES NOT PROVE: it walks ONE request (a "
    "swing) to its FIRST failure, and a first failure hides every later "
    "one.  Kill, loot, corpse and census-rebuild paths in scene 14 have "
    "never been driven at all -- the session ends before reaching them.  "
    "This list is a floor, not a total: nobody should budget from it as if "
    "it were complete.  The honest statement is that the count is unknown "
    "and at least this many."
)


class MobCombatBg0015GateError(ValueError):
    """A refusal from this module, always with a reason in the message."""


def roster_gate_open() -> bool:
    """Does ``field_mobs`` ship a roster for Bg0015 today?  (No.)"""
    return BG0015_FOLDER in field_mobs.live_scenes()


def scene14_roster_size_today() -> int:
    """Rows ``roster_for_scene_id(14)`` answers with today -- zero, which is
    why every swing there answers
    :data:`WIRED_ANSWER_FOR_A_TABLELESS_SCENE` instead of resolving a
    target."""
    return len(field_mobs.roster_for_scene_id(SCENE14_SCENE_ID))


def ai_rows_missing_for_scene14() -> dict[str, tuple]:
    """The AI table ids Bg0015's rows want and the mined table lacks.

    THE CAUSE OF THE UNWIND IN THIS MODULE'S HEADLINE.
    ``mob_ai_control.open_register`` -- which ``_sync_combat_scene_state``
    calls on every scene change -- refuses a roster row whose ``ai_combat``
    or ``ai_wander`` id is absent from ``field_mob_ai_tables``.  Reported as
    both id sets plus the difference, so whoever regenerates the mined table
    sees exactly what is short without rerunning this.
    """
    rows = field_mob_hostile_bg0015.scene14_hostile_roster()
    # Both mined tables are dicts keyed by the id a roster row cites -- read
    # the keys, never a positional row shape this module would be guessing.
    mined_combat = set(field_mob_ai_tables.AI_COMBAT_ROWS)
    mined_wander = set(field_mob_ai_tables.AI_WANDER_ROWS)
    wanted_combat = {mob.ai_combat for mob in rows if mob.ai_combat}
    wanted_wander = {mob.ai_wander for mob in rows if mob.ai_wander}
    return {
        "mined_combat": tuple(sorted(mined_combat)),
        "wanted_combat": tuple(sorted(wanted_combat)),
        "missing_combat": tuple(sorted(wanted_combat - mined_combat)),
        "mined_wander": tuple(sorted(mined_wander)),
        "wanted_wander": tuple(sorted(wanted_wander)),
        "missing_wander": tuple(sorted(wanted_wander - mined_wander)),
    }


def open_register_refusal_for_scene14() -> str | None:
    """The refusal reason ``mob_ai_control.open_register`` gives for
    Bg0015's roster, or ``None`` if it accepts it.

    The raise the headline traceback shows, reached here directly rather
    than through a session: ``_sync_combat_scene_state`` hands the freshly
    loaded roster to exactly this function, so a registered Bg0015 reaches
    this line on the first scene change.
    """
    try:
        mob_ai_control.open_register(
            field_mob_hostile_bg0015.scene14_hostile_roster())
    except mob_ai_control.MobAiControlError as error:
        return error.reason
    return None


def templates_without_a_death_ruling() -> tuple[int, ...]:
    """Bg0015 template ids ``mob_death.ruling_for`` refuses, ascending.

    Derived by calling the real predicate on the real rows, never a
    hand-typed list, so one owner letter landing shortens this on its own.
    """
    refused = set()
    for mob in field_mob_hostile_bg0015.scene14_hostile_roster():
        try:
            mob_death.ruling_for(mob)
        except mob_death.MobDeathContractError:
            refused.add(mob.template_id)
    return tuple(sorted(refused))


def recompose_status() -> dict[str, Any]:
    """Where scene 14 stands with ``mob_scene_recompose`` -- BOTH halves.

    An earlier draft read ``composer_scene_ids()`` alone and reported scene
    14 as an unacknowledged hole.  It is not: that module carries a dated
    written acknowledgement for scene 14 (round ``le2dox``) whose own words
    are that it composes one "in the same round its first roster row
    lands" -- downstream of registration, not an independent gate.
    ``scene_is_accounted_for`` is the predicate that reads both halves, and
    this function reports what it says rather than half of it.
    """
    return {
        "composer_scene_ids": mob_scene_recompose.composer_scene_ids(),
        "has_composer": (
            SCENE14_SCENE_ID in mob_scene_recompose.composer_scene_ids()),
        "acknowledged_without_composer": (
            SCENE14_SCENE_ID
            in mob_scene_recompose.ACKNOWLEDGED_WITHOUT_COMPOSER),
        "accounted_for": mob_scene_recompose.scene_is_accounted_for(
            SCENE14_SCENE_ID),
    }


def splice_identities(legacy: Any) -> tuple[int, ...]:
    """The identities the VISUAL path actually splices, ascending -- read
    off ``field_mob_hostile_bg0015.scene14_hostile_overrides(legacy)``, the
    real dict a future runtime branch would hand
    ``mob_scene_recompose.splice_identity_override``."""
    return tuple(sorted(
        field_mob_hostile_bg0015.scene14_hostile_overrides(legacy)))


def splice_identities_missing_from(
        external_identities: Iterable[int], legacy: Any) -> tuple[int, ...]:
    """Which spliced identities are absent from an EXTERNALLY supplied set.

    Fail closed and name them: a splice identity the census never ships
    would decorate a body the client was never sent.  The independent side
    is the caller's on purpose -- lane A's census
    (``world_bg0015_identity._PLACEMENT_ROWS``) and this lane's table
    (Bg0015's own ``HOSTILE_PLACEMENTS``) are separate runtime paths that do
    not import each other, which is the only sense in which this
    cross-check is independent.

    WHAT IT CANNOT DO, SAID PLAINLY: it is NOT independent of the shared
    ``0x2000 + placement + 1`` formula, and it cannot catch a small
    placement shift -- lane A ships 81 of 91 placements, so a ``+1`` shift
    lands on another real actor roughly nine times in ten.  The hand-typed
    twelve-number pin in this module's tests is what catches that case.
    Saying so is cheaper than pretending this function catches everything.
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
    """Owner-refused placements Bg0015 carries today: none.

    ``field_mobs.load_roster`` drops ``OWNER_REFUSED_PLACEMENTS`` rows
    (eight of Bg0002's) while ``scene14_hostile_roster`` does not filter at
    all.  The two agree for Bg0015 only because the refusal list has no
    Bg0015 entry -- a property of today's data, not of the code.
    """
    return tuple(sorted(
        field_mobs.OWNER_REFUSED_PLACEMENTS.get(BG0015_FOLDER, ())))


def live_cross_scene_collisions_today() -> tuple[dict, ...]:
    """``field_mobs.cross_scene_identity_collisions()`` for the live scenes
    -- ``()`` at HEAD, which is why registering Bg0015 would create the
    first one rather than join an accepted class."""
    return field_mobs.cross_scene_identity_collisions()


def bg0002_bg0015_identity_collisions() -> tuple[int, ...]:
    """Identities Bg0002's LIVE (owner-filtered) roster and Bg0015's hostile
    roster share: ``(0x2058,)``, placement 87 on both sides.

    The same survivor ``tests/test_field_mobs.py``'s three-table collision
    test already pins from the RAW tables (round ua236k).  This reads the
    Bg0002 side through the owner-filtered path instead, so the day a
    refusal removes placement 87 the two answers diverge on purpose.
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
