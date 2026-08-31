"""LANE-B / BUILD-004+005 continuation: the combat-ledger half of scene 14's
hostile splice that the census-only CORE-REQUEST does not cover, measured
this round (`pf_bridge/notes_to_chief/20260831_2151_LANE-A-TO-CHIEF-scene14-
hostile-splice-core-request-both-halves-confirmed-built.md`).

WHAT A PLAYER SEES BECAUSE OF THIS FILE, STATED HONESTLY AND FIRST.  Nothing
yet.  This is a measurement/proof module, the same shape ``mob_combat_
membership.py`` already uses for itself: it has no ``runtime.py`` call site
(that file is chief's, not this lane's) and composes no frame.  What it DOES
do is measure a real gap in the already-sent CORE-REQUEST above, with real
code against real HEAD state, so the day that CORE-REQUEST is wired the
result is not a half-working feature nobody predicted.

WHY THIS MODULE EXISTS.  The 2026-08-31T21:51+07:00 CORE-REQUEST wires
``runtime.py:7501`` to compose a VISUAL census where 12 of Bg0015's actors
carry hostile faction/level bytes (``field_mob_hostile_bg0015
.scene14_hostile_overrides``, spliced via ``mob_scene_recompose
.splice_identity_override``).  It says nothing about whether an attack
against those 12 identities can actually land, and round jqxe6v's own
docstring already flags the reason in one line: "Nothing here sends a frame,
opens a ledger row, or is called from runtime.py/app.py."  Traced further
this round: ``_dispatch_mob_combat``'s already-wired ``damage_step``/
``death_step`` call sites resolve their ledger through ``self
._sync_combat_scene_state()`` (``runtime.py:4027``), which is entirely
scene-generic -- it opens ``field_mobs.load_roster(folder)`` when ``folder
in field_mobs.live_scenes()``, and an EMPTY roster otherwise.  ``field_mobs
._SCENE_TABLE_MODULES`` (round jqxe6v measured: 182 pinned assertions across
six test files depend on it meaning "the two scenes shipped so far",
registering a third deliberately deferred to chief's own ``runtime.py:7501``
coordination rather than slipped in as a side effect) still holds only
bg0001/bg0002 at this round's HEAD, so ``"Bg0015" not in field_mobs
.live_scenes()`` today, and ``_sync_combat_scene_state`` opens an EMPTY
combat ledger for scene id 14.  Every one of the 12 now-hostile-looking
identities would therefore refuse with ``mob_combat.REFUSE_TARGET_NOT_IN_
LEDGER`` the moment a player attacks one -- even AFTER the visual
CORE-REQUEST lands.  Measured, not guessed: see
``today_every_hostile_identity_is_refused`` below, proven against the real
ledger ``mob_combat.open_ledger_for_scene_id`` builds for scene id 14 today,
with a test that fails the day this stops being true.

WHAT THIS MODULE DELIBERATELY DOES NOT DO.  It does not register Bg0015's
table into ``field_mobs._SCENE_TABLE_MODULES`` -- that is exactly the change
round jqxe6v measured and deferred (182 assertions, six files, "not slipped
in as a side effect of an import guard unlocking"), and this module leaves
that call where jqxe6v put it (chief/lane-A/lane-B coordination, a CORE-
REQUEST addendum, not a unilateral edit here).  Instead it hands whoever
makes that call two facts it would otherwise have to re-derive under time
pressure:

1. ``bg0015_registration_would_line_up_with_the_visual_splice`` -- if Bg0015
   is ever registered, the SET of identities a ledger opened from its own
   hostile roster would carry is EXACTLY the same 12 identities
   ``field_mob_hostile_bg0015.scene14_hostile_overrides()`` already splices
   -- both trace back to the one table this project mined for Bg0015 and the
   one ``0x2000 + placement_index + 1`` formula every scene already uses, so
   nobody has to hand-check the two halves agree.
2. ``bg0002_bg0015_identity_collisions`` -- registering Bg0015 would make
   placement 87 collide with Bg0002's OWN placement 87 (both compute actor
   identity ``0x2058``: ``FieldMob.actor_identity`` carries no scene term,
   COO-DECISION 2026-08-27T14:41+07:00 deferred adding one).  This is not a
   new class of risk: bg0001 and bg0002 already share colliding identities
   today (``mob_combat.open_ledger_for_scene_id``'s own docstring names
   ``0x2068``/``0x206a``), and ``_sync_combat_scene_state`` re-opens the
   WHOLE ledger/register on every scene change (M2 cross-scene-in-session is
   paused, PANYA-DECISION 2026-08-27T20:10+07:00), so no live session ever
   holds two scenes' rows in the same ledger at once.  Measured here so the
   day someone registers Bg0015 they inherit a counted fact, not a fresh
   investigation.

NONCLAIM.  Does not import Bg0015's raw table module directly -- everything
here reads Bg0015 rows through ``field_mob_hostile_bg0015.scene14_hostile_
roster()``, the one function the approved composer already exposes, so this
file adds no second importer for that table module's own approved-importer
guard test to track (confirmed: this file's own text does not contain the
raw table module's name -- deliberately not spelled out even here, since
that guard's own literal-string sweep would flag its own name being quoted
in a sibling file).  Does not touch ``field_mobs
._SCENE_TABLE_MODULES``, ``live_scenes()``, or ``runtime.py``/``app.py``.
Does not send anything on the wire.  Does not claim the collision above is
harmless in every future shape this project could take -- only that it is
inert under TODAY's single-scene-ledger session shape, the same way the
bg0001/bg0002 collision already is.
"""

from __future__ import annotations

from . import field_mob_hostile_bg0015
from . import field_mobs
from . import mob_combat

# world_scene_folder._FOLDER_BY_SCENE_ID: (2, "Bg0002"), (14, "Bg0015").
# Read as plain ints here rather than importing world_scene_folder for two
# constants this module only ever compares against, never resolves from a
# live scene_id -- the resolution itself belongs to runtime.py's own
# _sync_combat_scene_state, which this module does not call or duplicate.
BG0002_SCENE_ID = 2
BG0015_SCENE_ID = 14


def today_hostile_identities() -> tuple[int, ...]:
    """The 12 actor identities the visual splice CORE-REQUEST will mark
    hostile, read off the same roster ``field_mob_hostile_bg0015
    .scene14_hostile_overrides`` builds its dict from -- not re-derived,
    not hand-typed.
    """
    return tuple(
        mob.actor_identity
        for mob in field_mob_hostile_bg0015.scene14_hostile_roster()
    )


def today_every_hostile_identity_is_refused() -> tuple[int, ...]:
    """Every one of :func:`today_hostile_identities` that TODAY's real
    scene-14 combat ledger refuses with ``mob_combat.REFUSE_TARGET_NOT_IN_
    LEDGER``.

    Uses ``mob_combat.open_ledger_for_scene_id`` -- the same FUNCTION
    ``_sync_combat_scene_state()`` calls for this purpose -- but NOT a
    byte-identical ledger: ``_sync_combat_scene_state`` tags its ledger with
    the folder ``world_scene_folder`` resolves (``scene="Bg0015"``, since
    that folder IS addressed) while ``open_ledger_for_scene_id`` tags it
    with ``field_mobs.scene_for_scene_id(14)`` (``None``, since Bg0015 is
    not in ``_SCENE_TABLE_MODULES`` -- see that function's own docstring,
    which names Bg0015 by name as one of its three ``None`` cases).  Checked
    this round: the two ledgers compare UNEQUAL on that one field, but both
    carry the SAME EMPTY roster (zero rows either way), and ``balance_of``
    reads only ``self.balances``, never ``self.scene`` -- so both refuse
    every identity identically.  Stated precisely rather than claimed
    identical, because this project's own discipline is not to paper over a
    real difference just because it happens not to matter for one call.
    """
    ledger = mob_combat.open_ledger_for_scene_id(BG0015_SCENE_ID)
    refused = []
    for identity in today_hostile_identities():
        try:
            ledger.balance_of(identity)
        except mob_combat.MobCombatContractError as error:
            if error.reason == mob_combat.REFUSE_TARGET_NOT_IN_LEDGER:
                refused.append(identity)
    return tuple(refused)


def bg0015_registration_would_line_up_with_the_visual_splice() -> bool:
    """``True`` when a ledger opened directly from Bg0015's own hostile
    roster would carry EXACTLY :func:`today_hostile_identities` -- no more,
    no fewer.

    Built the same way ``mob_combat.open_ledger_for_scene_id`` builds any
    other scene's ledger (``mob_combat.open_ledger(roster, scene=...)``),
    fed Bg0015's own rows through the one function that already parses them
    (``field_mob_hostile_bg0015.scene14_hostile_roster``) -- not a new
    selector, not a hand-typed identity list.  This is the fact a future
    registration decision needs and would otherwise have to re-derive: the
    visual half (splice) and the combat half (ledger) agree on WHICH twelve
    identities count as hostile, because both read the same mined table
    through the same formula.
    """
    roster = field_mob_hostile_bg0015.scene14_hostile_roster()
    ledger = mob_combat.open_ledger(roster, scene="Bg0015")
    return set(ledger.identities()) == set(today_hostile_identities())


def bg0002_bg0015_identity_collisions() -> tuple[int, ...]:
    """Every actor identity Bg0002's OWN live roster and Bg0015's hostile
    roster would both compute, sorted ascending.

    Reads Bg0002 through the already-registered, already-live path
    (``field_mobs.roster_for_scene_id``) and Bg0015 through the one approved
    composer (``field_mob_hostile_bg0015.scene14_hostile_roster``) -- no
    second reader of either table, and no re-derivation of the identity
    formula either side already uses.
    """
    bg0002_identities = {
        mob.actor_identity
        for mob in field_mobs.roster_for_scene_id(BG0002_SCENE_ID)
    }
    bg0015_identities = set(today_hostile_identities())
    return tuple(sorted(bg0002_identities & bg0015_identities))
