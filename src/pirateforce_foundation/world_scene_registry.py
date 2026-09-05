"""LANE-A (WORLD): the per-scene world registry, in this process's memory.

WHAT A PLAYER SEES BECAUSE OF THIS FILE.  Today: hit a monster four times,
leave it standing at a third of its health, close the client and log straight
back in on a server that never restarted -- and the monster is back at FULL
HEALTH.  Not dead and resurrected (``mob_death_persistence`` answers that
half): simply healed, because the only place its remaining health was ever
written down was the ``mob_combat.CombatLedger`` of the session that ended.
The same is true of a second player standing in the same scene: they see the
table's full-health roster, not the fight the first player is in the middle
of.  This file is where that number lives instead.

THE RULING THIS IMPLEMENTS.  ``PANYA-DECISION 20260905_1057`` + ``1140``:
every scene's world state -- roster and monster positions, monster health,
corpses and respawns, ground items and their lifetime -- lives in the SERVER
PROCESS'S MEMORY and is SHARED BY EVERY SESSION STANDING IN THAT SCENE.  Not
in the database (only characters and accounts go there), and a server reboot
is a NEW WORLD with no recovery.  ``COO-DECISION 20260905_1152`` names
LANE-A the owner of that registry and LANE-B the lane that writes combat
state INTO it.  A per-session register, or a relogin that resets what the
player did, is a DEFECT by that ruling -- which is what this lane measured
and is fixing here.

THE THREE BOOKS, AND WHY THIS FILE ONLY WRITES ONE OF THEM.  A scene's world
is three facts, and two of them already had a home when this file was
written:

    ground items + lifetime  ->  ``mob_ground_persistence.WorldGround``
    corpses                  ->  ``mob_death_persistence.WorldDeaths``
    live monster vitals      ->  NOWHERE.  This file.

Copying the first two here would create a SECOND truth for a fact that
already has one, and two books that can disagree about whether a monster is
dead is not a smaller version of this feature -- ``mob_death.
repopulation_entries`` refuses a ledger that disagrees with its register
(``REFUSE_LEDGER_DISAGREES_WITH_REGISTER``), the arrival census reaches that
refusal from an ``else:`` its own ``try`` does not cover, and ``runtime.py``
says in its own words what happens next: the v141 listener thread unwinds.
So this file HOLDS one book and LOOKS THROUGH to the other two: `view` is the
single per-scene answer COO's decision asks for ("what does this scene look
like right now"), assembled from all three, owning only the third.

WHY A GRAVE IS REFUSED BY NAME AT THIS DOOR.  ``note_balance`` will not
accept ``current_hp`` of zero.  A monster at zero is a grave, graves are
``WorldDeaths``'s book, and a caller that could write one here would be
writing the disagreement described above with no error anywhere.  The
refusal is named (:data:`REFUSE_A_GRAVE_IS_NOT_A_VITAL`) and it points at
the door that IS correct for a kill: ``mob_death.commit_death``.

WHAT A SESSION DOES WITH THIS BOOK.  It is SEEDED FROM, never replaced BY --
the same shape, and for the same reason, as ``mob_ground_persistence.
seed_cell`` and ``mob_death_persistence.seed_the_session_state``: a
``CombatLedger`` is a VALUE with a compare-and-swap generation on it, and
that counter is a statement about ONE lineage of reads and writes.  Sharing
the object between two logins would share the counter, which is the one
thing that must not be shared.  What is common to both logins is smaller and
has no session in it -- WHICH IDENTITY STANDS AT WHAT HEALTH, WHERE -- so
that is what this file holds, and :func:`seed_the_session_ledger` copies it
into a session's own fresh value.

ORDER AT THE CALL SITE: GRAVES FIRST, THEN VITALS.  ``mob_death_
persistence.seed_the_session_state`` zeroes the ledger rows of monsters this
world has buried; this seed then fills in the ones still standing.  Running
this one first would still be CORRECT -- it skips every identity the grave
book has buried, re-reading that book at seed time rather than trusting the
order -- but the ask states the order anyway, because a reader of
``runtime.py`` should not have to derive it (see
:data:`WORLD_REGISTRY_SEED_WIRING`).

NEVER RAISES INTO A CALLER.  Every public entry point on this module returns
a value and a named reason instead of an exception: this book sits on the
arrival path, and a world registry that can take down the listener thread
would be a worse defect than the one it fixes.  The refusals are counted and
printable so that "nothing was seeded" and "nothing was there to seed" are
never the same line.

A REBOOT IS A NEW WORLD, and that is deliberate rather than unfinished
(``PANYA-DECISION 20260905_1224``).  There is no store here, no restore, and
no file: the registry is built on first use inside one process and dies with
it.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from typing import Any

from . import mob_combat
from . import mob_death
from . import mob_death_persistence
from . import mob_ground_persistence
from . import mob_loot

#: A scene cannot hold more remembered vitals than this.  The bound exists
#: for the reason ``WorldDeaths.GRAVES_PER_SCENE_CAP`` exists: this is
#: process memory with no eviction clock on it, and a caller in a loop must
#: hit a named refusal rather than grow the dictionary until the box stops.
#: 4096 is far above the largest roster this project has mined (bg0001, 115
#: placements) and far below anything that costs real memory.
VITALS_PER_SCENE_CAP = 4096

#: Named refusals.  A caller reads these; nothing here is a bare False.
REFUSE_A_GRAVE_IS_NOT_A_VITAL = "a_grave_is_not_a_vital"
REFUSE_BAD_SCENE = "bad_scene"
REFUSE_BAD_IDENTITY = "bad_identity"
REFUSE_BAD_HP = "bad_hp"
REFUSE_BAD_POSITION = "bad_position"
REFUSE_SCENE_IS_FULL = "scene_is_full"
REFUSE_NOT_A_LEDGER = "not_a_ledger"
REFUSE_NOTHING_REMEMBERED = "nothing_remembered"
REFUSE_ABOVE_THE_LEDGER_CEILING = "above_the_ledger_ceiling"

_MAX_HP = 0xFFFFFFFF
#: The client's world coordinates are floats in the tens of thousands (the
#: sea scenes measured in R318 run to +-8400).  This is a sanity bound, not a
#: map boundary: it exists so that ``inf``, ``nan`` and a mis-parsed integer
#: are refused by name at the door instead of being remembered forever.
_MAX_COORDINATE = 1.0e7


def _scene_key(scene: Any) -> str:
    """Case-folded scene key, or ``ValueError``.

    Delegates to ``mob_loot.scene_key`` so this book folds a scene tag the
    SAME WAY the ground book beside it does.  ``Bg0002`` and ``bg0002`` are
    one scene everywhere else in this tree, and a registry that disagreed
    with the ground's spelling would hand a player a healed monster whenever
    a caller happened to pass the other case.
    """
    return mob_loot.scene_key(scene)


def _require_identity(actor_identity: Any) -> int:
    if type(actor_identity) is bool or not isinstance(actor_identity, int):
        raise ValueError("actor identity must be an int")
    if actor_identity < 1 or actor_identity > 0xFFFFFFFF:
        raise ValueError("actor identity out of range")
    return actor_identity


def _require_hp(value: Any, what: str) -> int:
    if type(value) is bool or not isinstance(value, int):
        raise ValueError("%s must be an int" % what)
    if value < 0 or value > _MAX_HP:
        raise ValueError("%s out of range" % what)
    return value


def _require_position(position: Any) -> tuple[float, float, float]:
    if type(position) not in (tuple, list) or len(position) != 3:
        raise ValueError("a position is three coordinates")
    out = []
    for value in position:
        if type(value) is bool or not isinstance(value, (int, float)):
            raise ValueError("a coordinate is a number")
        number = float(value)
        if not math.isfinite(number) or abs(number) > _MAX_COORDINATE:
            raise ValueError("a coordinate is finite and on the map")
        out.append(number)
    return (out[0], out[1], out[2])


@dataclass(frozen=True)
class MobVital:
    """What the world remembers about one monster that is still standing.

    ``current_hp``/``max_hp`` are both present or both absent: a health with
    no ceiling cannot be turned back into a ``MobBalance``, and a ceiling
    with no health says nothing the roster table did not already say.
    ``position`` is independent of them -- a monster that has walked but not
    been hit has a position and no health, and that is a real row.
    """

    actor_identity: int
    current_hp: int | None = None
    max_hp: int | None = None
    position: tuple[float, float, float] | None = None

    def __post_init__(self) -> None:
        _require_identity(self.actor_identity)
        if (self.current_hp is None) != (self.max_hp is None):
            raise ValueError("health and its ceiling travel together")
        if self.current_hp is not None:
            _require_hp(self.current_hp, "current hp")
            _require_hp(self.max_hp, "max hp")
            if self.current_hp > self.max_hp:
                raise ValueError("current hp is above max hp")
            if self.current_hp == mob_death.HP_WHEN_DEAD:
                # The door refuses this too (see REFUSE_A_GRAVE_IS_NOT_A_
                # VITAL); the type refuses it as well, so no path -- a test,
                # a future caller, a replay -- can construct the row the
                # door exists to keep out.
                raise ValueError("a grave is not a vital")
        if self.position is not None:
            _require_position(self.position)

    @property
    def remembers_health(self) -> bool:
        return self.current_hp is not None


@dataclass(frozen=True)
class SceneWorldView:
    """One scene's whole world, as one immutable answer.

    THE POINT OF THIS TYPE.  ``COO-DECISION 20260905_1152`` item 2(2) asks
    for a registry a caller can ask "what does scene N look like right now"
    and get ground, graves and monsters from ONE place.  The three books stay
    where they are; this is the single reading of them.
    """

    scene: str
    mobs: tuple[MobVital, ...] = ()
    graves: tuple[Any, ...] = ()
    ground: tuple[Any, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not (self.mobs or self.graves or self.ground)


@dataclass(frozen=True)
class NoteOutcome:
    """What one write did.  ``reason`` empty means it landed."""

    scene: str
    actor_identity: int | None
    reason: str = ""
    remembered: MobVital | None = None

    @property
    def noted(self) -> bool:
        return not self.reason


@dataclass(frozen=True)
class SeedOutcome:
    """What one seed did to a session's ledger."""

    scene: str
    ledger: Any
    applied: tuple[int, ...] = ()
    skipped: int = 0
    reason: str = ""

    @property
    def seeded(self) -> bool:
        return bool(self.applied)


class WorldSceneRegistry:
    """The process's own per-scene world book.  One per server.

    Deliberately reachable through :func:`world_scene_registry` rather than
    handed in by a constructor: the two books it sits beside
    (``mob_ground_persistence.world_ground``, ``mob_death_persistence.
    world_deaths``) are reached that way, LANE-B writes into this one from
    call sites that have no registry in scope, and a fourth spelling of "the
    world" would be the thing this file exists to prevent.  Every method
    takes an explicit instance too, so a test never touches the process's.
    """

    def __init__(self, vitals_per_scene: int = VITALS_PER_SCENE_CAP) -> None:
        if (type(vitals_per_scene) is bool
                or not isinstance(vitals_per_scene, int)
                or vitals_per_scene < 1):
            raise ValueError("vitals_per_scene must be a positive int")
        self._cap = vitals_per_scene
        self._lock = threading.RLock()
        # scene key -> {actor identity: MobVital}
        self._scenes: dict = {}

    @property
    def vitals_per_scene(self) -> int:
        return self._cap

    # ---- the write door (LANE-B's API) --------------------------------

    def note_balance(self, scene: Any, actor_identity: Any,
                     current_hp: Any, max_hp: Any) -> NoteOutcome:
        """Remember one monster's remaining health.  Never raises.

        THE CALL SITE THIS IS FOR: LANE-B, immediately after a hit is
        accepted against the session ledger -- the same moment
        ``mob_combat.commit_step`` produces the new balance.  A kill does NOT
        come here: it goes to ``mob_death.commit_death``, which already
        writes ``WorldDeaths`` (see REFUSE_A_GRAVE_IS_NOT_A_VITAL).
        """
        try:
            fold = _scene_key(scene)
        except Exception:                                    # noqa: BLE001
            return NoteOutcome("", None, REFUSE_BAD_SCENE)
        try:
            identity = _require_identity(actor_identity)
        except Exception:                                    # noqa: BLE001
            return NoteOutcome(fold, None, REFUSE_BAD_IDENTITY)
        try:
            current = _require_hp(current_hp, "current hp")
            ceiling = _require_hp(max_hp, "max hp")
        except Exception:                                    # noqa: BLE001
            return NoteOutcome(fold, identity, REFUSE_BAD_HP)
        if current > ceiling:
            return NoteOutcome(fold, identity, REFUSE_BAD_HP)
        if current == mob_death.HP_WHEN_DEAD:
            # A grave, at the one door that must not accept one.  See the
            # module docstring: two books that can disagree about death are
            # a crash on the arrival path, not a cosmetic duplication.
            return NoteOutcome(fold, identity, REFUSE_A_GRAVE_IS_NOT_A_VITAL)
        return self._write(fold, identity, current, ceiling, _KEEP)

    def note_position(self, scene: Any, actor_identity: Any,
                      position: Any) -> NoteOutcome:
        """Remember where one monster is standing now.  Never raises.

        Independent of health on purpose: a monster that has walked its
        leash but has never been hit is a real row, and the arrival census
        is the reader that wants it.
        """
        try:
            fold = _scene_key(scene)
        except Exception:                                    # noqa: BLE001
            return NoteOutcome("", None, REFUSE_BAD_SCENE)
        try:
            identity = _require_identity(actor_identity)
        except Exception:                                    # noqa: BLE001
            return NoteOutcome(fold, None, REFUSE_BAD_IDENTITY)
        try:
            where = _require_position(position)
        except Exception:                                    # noqa: BLE001
            return NoteOutcome(fold, identity, REFUSE_BAD_POSITION)
        return self._write(fold, identity, _KEEP, _KEEP, where)

    def forget(self, scene: Any, actor_identity: Any) -> bool:
        """THE RESPAWN DOOR.  True when a row was actually held.

        Named and tested now rather than invented later, exactly as
        ``WorldDeaths.forget`` was: the round that adds respawning must have
        one way to say "this monster is new again", and it must be a removal
        from these books rather than a clear of them.
        """
        try:
            fold = _scene_key(scene)
            identity = _require_identity(actor_identity)
        except Exception:                                    # noqa: BLE001
            return False
        with self._lock:
            rows = self._scenes.get(fold)
            if not rows or identity not in rows:
                return False
            rows.pop(identity, None)
            if not rows:
                self._scenes.pop(fold, None)
            return True

    def clear(self) -> None:
        """Empty the book.  A TEST SEAM, and named as one."""
        with self._lock:
            self._scenes.clear()

    def _write(self, fold: str, identity: int, current: Any, ceiling: Any,
               position: Any) -> NoteOutcome:
        """Merge one field-set into the row, under the lock.

        ``_KEEP`` means "leave whatever is already remembered", which is what
        makes a position write and a health write independent without a
        read-modify-write the caller could lose a race on.
        """
        with self._lock:
            rows = self._scenes.setdefault(fold, {})
            standing = rows.get(identity)
            if standing is None and len(rows) >= self._cap:
                # `rows` is non-empty here by construction (the cap is a
                # positive int), so the scene key this `setdefault` just
                # created is never left behind empty by this arm.
                return NoteOutcome(fold, identity, REFUSE_SCENE_IS_FULL)
            new_current = standing.current_hp if standing else None
            new_max = standing.max_hp if standing else None
            new_position = standing.position if standing else None
            if current is not _KEEP:
                new_current, new_max = current, ceiling
            if position is not _KEEP:
                new_position = position
            try:
                row = MobVital(identity, new_current, new_max, new_position)
            except Exception:                                # noqa: BLE001
                # Unreachable through the public doors (both validate first);
                # kept because MobVital's own rules can outgrow theirs, and a
                # registry that raised here would raise on the arrival path.
                return NoteOutcome(fold, identity, REFUSE_BAD_HP)
            rows[identity] = row
            return NoteOutcome(fold, identity, "", row)

    # ---- the read door ------------------------------------------------

    def remembered(self, scene: Any) -> tuple[MobVital, ...]:
        """One scene's remembered monsters, by identity.  Never raises."""
        try:
            fold = _scene_key(scene)
        except Exception:                                    # noqa: BLE001
            return ()
        with self._lock:
            rows = self._scenes.get(fold)
            if not rows:
                return ()
            return tuple(rows[key] for key in sorted(rows))

    def remembered_one(self, scene: Any, actor_identity: Any):
        """One row, or ``None``.  Never raises."""
        try:
            fold = _scene_key(scene)
            identity = _require_identity(actor_identity)
        except Exception:                                    # noqa: BLE001
            return None
        with self._lock:
            return self._scenes.get(fold, {}).get(identity)

    def scenes(self) -> tuple[str, ...]:
        """Every scene this process has remembered anything about."""
        with self._lock:
            return tuple(sorted(self._scenes))


_KEEP = object()

_WORLD: WorldSceneRegistry | None = None
_WORLD_LOCK = threading.RLock()


def world_scene_registry() -> WorldSceneRegistry:
    """The process's own world registry.  Built on first use, never rebuilt."""
    global _WORLD
    with _WORLD_LOCK:
        if _WORLD is None:
            _WORLD = WorldSceneRegistry()
        return _WORLD


def install_world_scene_registry(registry: Any) -> WorldSceneRegistry:
    """Put a registry in the process slot.  A TEST SEAM, named as one.

    Returns the one now installed.  A non-registry is refused rather than
    stored: the failure this prevents is a test leaving a stub behind that a
    later production path then writes the world into.
    """
    global _WORLD
    if not isinstance(registry, WorldSceneRegistry):
        raise ValueError("only a WorldSceneRegistry can be installed")
    with _WORLD_LOCK:
        _WORLD = registry
        return _WORLD


def view(scene: Any, *, registry: Any = None, deaths: Any = None,
         ground: Any = None) -> SceneWorldView:
    """THE SINGLE PER-SCENE ANSWER: ground, graves and monsters together.

    Never raises, and a book that cannot be read contributes ``()`` rather
    than taking the whole view down with it -- an arrival that shows a
    player the ground and the graves is better than one that shows them a
    disconnect because the vitals book was mid-migration.
    """
    try:
        fold = _scene_key(scene)
    except Exception:                                        # noqa: BLE001
        return SceneWorldView("")
    book = registry if registry is not None else world_scene_registry()
    try:
        mobs = book.remembered(fold)
    except Exception:                                        # noqa: BLE001
        mobs = ()
    try:
        grave_book = (deaths if deaths is not None
                      else mob_death_persistence.world_deaths())
        graves = tuple(grave_book.buried_in(fold))
    except Exception:                                        # noqa: BLE001
        graves = ()
    try:
        ground_book = (ground if ground is not None
                       else mob_ground_persistence.world_ground())
        rows = tuple(ground_book.standing(fold))
    except Exception:                                        # noqa: BLE001
        rows = ()
    return SceneWorldView(fold, mobs, graves, rows)


def seed_the_session_ledger(ledger: Any, scene: Any, *, registry: Any = None,
                            deaths: Any = None, announce: bool = True):
    """THE CALL SITE.  Fill a fresh session ledger from the world's memory.

    ``self.mob_combat_ledger = world_scene_registry.seed_the_session_ledger(
        self.mob_combat_ledger, folder)``

    NEVER RAISES, and on every refusal the caller gets back ITS OWN LEDGER,
    unchanged -- the same contract ``mob_death_persistence.
    seed_the_session_state`` gives, for the same reason: this runs on the
    arrival path, where an exception is a dropped listener thread rather
    than a missing feature.

    WHAT IT SKIPS, AND WHY EACH SKIP IS A CORRECTNESS RULE, NOT A CONVENIENCE

    * an identity the world has BURIED -- the grave book is the authority on
      death, and a row here that said "alive at 40" beside a register that
      says "dead" is ``mob_death.REFUSE_LEDGER_DISAGREES_WITH_REGISTER``,
      which the arrival census reaches from an uncovered ``else:``.  The
      grave book is re-read HERE rather than trusted from call order, so
      this seed is safe on either side of the grave seed.
    * an identity the ledger does not carry -- a ledger still open on the
      scene the player is LEAVING holds none of the destination's rows, and
      writing into it would be composing another scene's world.
    * a remembered health ABOVE the ledger's own ceiling -- the roster table
      changed under the world's memory (a re-mine, a different build), and
      ``MobBalance`` would refuse it.  Counted and named, never clamped:
      silently lowering a monster to a ceiling this file guessed at is the
      kind of invented number this project refuses on sight.
    * a row that remembers only a position -- there is nothing in a
      ``CombatLedger`` to put it in.  The census composer is that row's
      reader, not this function.

    ALL OR NOTHING on an unexpected failure: ``mutated`` is a local, and any
    exception hands back the caller's own object rather than a ledger
    carrying half the world.
    """
    try:
        fold = _scene_key(scene)
    except Exception:                                        # noqa: BLE001
        outcome = SeedOutcome("", ledger, (), 0, REFUSE_BAD_SCENE)
        if announce:
            _say(describe_seeded(outcome))
        return ledger
    if not isinstance(ledger, mob_combat.CombatLedger):
        outcome = SeedOutcome(fold, ledger, (), 0, REFUSE_NOT_A_LEDGER)
        if announce:
            _say(describe_seeded(outcome))
        return ledger
    book = registry if registry is not None else world_scene_registry()
    try:
        rows = book.remembered(fold)
    except Exception:                                        # noqa: BLE001
        rows = ()
    if not rows:
        # Silent: an untouched scene is the ordinary state of most of this
        # world most of the time, and a line per arrival per scene would
        # bury the ones that matter.
        return ledger
    try:
        grave_book = (deaths if deaths is not None
                      else mob_death_persistence.world_deaths())
    except Exception:                                        # noqa: BLE001
        grave_book = None
    applied = []
    skipped = 0
    try:
        mutated = ledger
        carried = set(mutated.identities())
        for row in rows:
            if not row.remembers_health:
                skipped += 1
                continue
            if row.actor_identity not in carried:
                skipped += 1
                continue
            if grave_book is not None and grave_book.is_buried(
                    fold, row.actor_identity):
                skipped += 1
                continue
            standing = mutated.balance_of(row.actor_identity)
            if standing.current_hp == mob_death.HP_WHEN_DEAD:
                # Already a corpse in this ledger (the grave seed ran first).
                # Leave it lying down.
                skipped += 1
                continue
            if row.current_hp > standing.max_hp:
                skipped += 1
                continue
            if standing.current_hp == row.current_hp:
                # Nothing to say and nothing to write: a re-arrival into a
                # scene whose ledger already carries the world's number.
                continue
            mutated = mutated.with_balance(mob_combat.MobBalance(
                row.actor_identity, standing.max_hp, row.current_hp))
            applied.append(row.actor_identity)
    except Exception:                                        # noqa: BLE001
        outcome = SeedOutcome(fold, ledger, (), skipped,
                              REFUSE_ABOVE_THE_LEDGER_CEILING)
        if announce:
            _say(describe_seeded(outcome))
        return ledger
    outcome = SeedOutcome(fold, mutated, tuple(applied), skipped)
    if announce and (applied or skipped):
        _say(describe_seeded(outcome))
    return mutated


def describe_noted(outcome: Any) -> str:
    """One bounded ASCII console line for a write.  Never raises."""
    try:
        if outcome.noted:
            row = outcome.remembered
            health = ("hp=none" if row is None or not row.remembers_health
                      else "hp=%d/%d" % (row.current_hp, row.max_hp))
            where = ("pos=none" if row is None or row.position is None
                     else "pos=%.1f,%.1f,%.1f" % row.position)
            return ("WORLD_REGISTRY_NOTED scene=%s id=0x%X %s %s"
                    % (outcome.scene, outcome.actor_identity, health, where))
        return ("WORLD_REGISTRY_REFUSED scene=%s id=%s reason=%s"
                % (outcome.scene,
                   "none" if outcome.actor_identity is None
                   else "0x%X" % outcome.actor_identity,
                   outcome.reason))
    except Exception:                                        # noqa: BLE001
        return "WORLD_REGISTRY_REFUSED scene=? id=? reason=undescribable"


def describe_seeded(outcome: Any) -> str:
    """One bounded ASCII console line for a seed.  Never raises."""
    try:
        if outcome.reason:
            return ("WORLD_REGISTRY_SEED_REFUSED scene=%s reason=%s skipped=%d"
                    % (outcome.scene, outcome.reason, outcome.skipped))
        return ("WORLD_REGISTRY_SEEDED scene=%s monsters=%d skipped=%d"
                % (outcome.scene, len(outcome.applied), outcome.skipped))
    except Exception:                                        # noqa: BLE001
        return "WORLD_REGISTRY_SEED_REFUSED scene=? reason=undescribable"


def describe_view(scene_view: Any) -> str:
    """One bounded ASCII console line for a whole scene.  Never raises.

    The line a person greps to answer the shared-world question on a live
    boot: two sessions in one scene, or one session before and after a
    relogin, must read the SAME three numbers here.
    """
    try:
        return ("WORLD_REGISTRY_VIEW scene=%s monsters=%d graves=%d ground=%d"
                % (scene_view.scene, len(scene_view.mobs),
                   len(scene_view.graves), len(scene_view.ground)))
    except Exception:                                        # noqa: BLE001
        return "WORLD_REGISTRY_VIEW scene=? monsters=? graves=? ground=?"


def _say(line: str) -> None:
    """Print without ever being the reason a caller failed.

    The bridge console is cp874; every line this module composes is ASCII by
    construction, and this still cannot raise into a caller on a stdout that
    has been closed or replaced under it.
    """
    try:
        print(line)
    except Exception:                                        # noqa: BLE001
        pass


#: The pasteable call site, kept next to the function it names so the letter
#: and the code cannot drift apart (the device ``mob_death_persistence.
#: DEATH_SEED_WIRING`` and ``mob_scene_recompose.GROUND_COMPANION_WIRING``
#: both use).  ``runtime.py`` is chief's file; LANE-A does not edit it.
WORLD_REGISTRY_SEED_WIRING = (
    "runtime.py, _sync_combat_scene_state, on the line AFTER the existing\n"
    "`mob_death_persistence.seed_the_session_state(...)` statement that\n"
    "DEATH_SEED_WIRING asks for (graves first, then the monsters still\n"
    "standing).\n"
    "\n"
    "    self.mob_combat_ledger = (\n"
    "        world_scene_registry.seed_the_session_ledger(\n"
    "            self.mob_combat_ledger, folder))\n"
    "\n"
    "import: `from . import world_scene_registry`\n"
    "\n"
    "WHY IT IS SAFE IN EITHER ORDER, even though the ask states one: this\n"
    "seed re-reads the grave book itself and skips every identity buried\n"
    "there, so a deploy that lands it before the grave seed still cannot\n"
    "stand a corpse back up.  The stated order is for the reader of\n"
    "runtime.py, not for correctness.\n"
    "\n"
    "WHY IT IS OUTSIDE `if folder != self.mob_combat_scene_folder:` for the\n"
    "same reason DEATH_SEED_WIRING is: runtime.py seeds\n"
    "`self.mob_combat_scene_folder` from the BOOT roster's own scene in\n"
    "__init__, so for a character whose stored scene is the boot scene that\n"
    "branch never runs -- and bg0001 is the scene the game boots into.\n"
    "\n"
    "IT RETURNS THE CALLER'S OWN LEDGER on every refusal and never raises,\n"
    "so the statement is safe on every dispatch.  It is silent when the\n"
    "scene's book is empty, which is the ordinary state of most scenes.\n"
    "\n"
    "THE WRITE HALF IS LANE-B'S AND IS NOT PART OF THIS ASK: LANE-B calls\n"
    "`world_scene_registry.world_scene_registry().note_balance(...)` from\n"
    "its own accepted-hit call site (COO-DECISION 20260905_1153).  Until it\n"
    "does, this seed finds an empty book and changes nothing -- which is why\n"
    "landing it early costs nothing and closes the wiring gap ahead of the\n"
    "lane that needs it.\n"
)
