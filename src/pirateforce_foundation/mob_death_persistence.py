"""LANE-B (COMBAT): a grave belongs to the WORLD, not to one session.

WHAT A PLAYER SEES BECAUSE OF THIS FILE.  Yesterday (ka1-A, R309, measured on
the real client -- ``pf_bridge/notes_to_chief/20260904_1430``): kill the
Fighting Fish soldier ``0x203D`` in scene 2, close the client, log straight
back in on a server that never restarted, and the monster is STANDING THERE
AT 3138/3138 as if the fight never happened.  Screenshot ``141440.png`` is
that resurrection.  With this file and the one call site its letter asks
chief for, the corpse the player left is still a corpse when they walk back
in.

THIS IS THE OTHER HALF OF R309, AND IT IS THE SAME DEFECT TWICE.  The drop
that vanished from the floor was ``mob_ground_persistence``'s half: the
ground lived in the ``mob_loot.DropLedgerCell`` of a session that had ended.
The monster that stood back up is this half: the deaths lived in the
``mob_death.DeathRegister`` of that same ended session (``runtime.py:1384``
builds a fresh empty one per session), and ``_sync_combat_scene_state``
re-opens every roster at its table's full HP and then rehydrates zeros from
that register alone.  An empty register means a full-HP roster, which is
exactly what the client was told.

WHY A SECOND STRUCTURE AND NOT A LONGER-LIVED REGISTER.  A ``DeathRegister``
is a VALUE with a compare-and-swap counter on it: ``commit_death`` accepts a
kill only against the generation it was computed from, so that two kills
racing in one tick cannot erase each other.  That counter is a statement
about ONE lineage of reads and writes -- one session's -- and sharing the
object between two logins would share the counter, which is the one thing
that must not be shared.  What is actually common to both logins is smaller
and has no session in it -- WHICH IDENTITY IS DEAD IN WHICH SCENE -- so that
is what :class:`WorldDeaths` holds, and a session's register is SEEDED FROM
it (a fresh value, its own counter) rather than replaced BY it.  Same shape,
same reason, same words as :class:`mob_ground_persistence.WorldGround`.

A GRAVE HAS NO LIFETIME, WHICH IS WHY THIS FILE HAS NO CLOCK.  A ground row
expires after ``mob_loot.DROP_LIFETIME_SECONDS`` because the client drops the
object off its own floor on the same schedule; a dead monster is dead until
something respawns it, and NOTHING IN THIS TREE RESPAWNS ONE TODAY.  So there
is no sweep here, and :meth:`WorldDeaths.forget` exists unused-by-production
and named, waiting for the respawn round that will be its only caller.  When
that round comes it calls ``forget`` and this file needs no other edit.

THE ONE THING THIS FILE REFUSES TO DO, AND THE FAILURE IT IS AVOIDING.  It
never puts a monster in a grave the SERVER did not record.  The remember runs
inside ``mob_death.commit_death`` AFTER the compare-and-swap has accepted the
kill, never inside ``mob_death.kill`` -- ``kill`` composes a step that a stale
register may make the caller throw away and recompute, and remembering there
would bury a monster whose death frames were never sent.  A corpse on the
world's books that no client was ever told about is worse than the bug this
file closes: the player watches a monster they never killed refuse every
hit.

WHAT THIS FILE DOES NOT MAKE TRUE, AND IT IS THE SAME GAP THE GROUND HAS.
Two players standing in one scene each hold their own ``DeathRegister``, and
this book is only READ where a session opens a roster.  So a player already
standing in a scene when somebody else kills a monster there does not learn
about it until their own roster re-opens: their ledger still has the monster
alive, and they can fight and kill it again.  That is what the game does
TODAY with no world book at all, so nothing here makes it worse -- but it is
not fixed either, and the fix is the one the ground already needed: the strike
path consulting the world before the ledger, the way
``mob_ground_persistence.claim_for_pickup`` decides a take before either
session's transaction runs.  That is a round of its own with a ruling of its
own; this file is deliberately not it, and says so rather than leaving a
reader to assume otherwise.

WHAT IS STILL NOT TRUE AFTER THIS FILE.  The grave lives in MEMORY.  It
survives a RELOGIN, which is what R309 measured; it does not survive a server
RESTART.  A durable half would need a ``mob_deaths`` table LANE-DB has not
been asked for yet, and this lane will not invent one behind a store's back:
the ground's own durable door (``mob_ground_persistence.persist_generation``)
is the shape that request will take when its ruling exists.
"""
from __future__ import annotations

import collections
import threading
from dataclasses import dataclass
from typing import Any

from . import mob_death

#: Shippable with no scenario flag: a player gets this by default or not at
#: all -- a grave that only exists under a trial flag is not a grave.
production_allowed = True

#: One console line per death that entered the world's books.
WORLD_REMEMBERED_TOKEN = "MOB_DEATH_WORLD_REMEMBERED"
#: A death that could not enter them, by name.  Never an exception.
WORLD_REMEMBER_REFUSED_TOKEN = "MOB_DEATH_WORLD_REMEMBER_REFUSED"
#: One console line per register seeded at a scene open, INCLUDING the ones
#: that seeded nothing -- "this scene has no graves" and "the seam never ran"
#: are different facts and an attended round greps for exactly that
#: difference (the same reason ``mob_ground_persistence`` gives for its own
#: always-printed seed line).
WORLD_SEEDED_TOKEN = "MOB_DEATH_WORLD_SEEDED"
#: A seed that could not happen, by name.
WORLD_SEED_REFUSED_TOKEN = "MOB_DEATH_WORLD_SEED_REFUSED"

REFUSE_NOT_A_RECORD = "not_a_death_record"
REFUSE_NOT_A_REGISTER = "not_a_death_register"
REFUSE_SCENE_IS_UNREADABLE = "scene_is_unreadable"
REFUSE_SCENE_IS_FULL = "scene_grave_cap_reached"
REFUSE_WORLD_RAISED = "world_raised"
REFUSE_REGISTER_REFUSED_THE_ROW = "register_refused_the_row"

#: How many distinct graves one scene may hold.  A GUARD, NOT A GAME RULE: a
#: scene's roster is finite (the largest mined table in this tree is far
#: under a hundred rows) and an identity can only die once, so production
#: cannot reach this.  It is here so that a caller feeding this module
#: fabricated identities in a loop cannot grow the dict without bound.
#:
#: THE NEWEST IS REFUSED, NOT THE OLDEST RETIRED, and that is the opposite
#: choice from ``mob_ground_persistence.ROWS_PER_SCENE_CAP``.  Retiring the
#: oldest row of a FLOOR forgets an item nobody came back for; retiring the
#: oldest GRAVE stands a monster the player has already killed back up on
#: their screen -- the exact defect this file exists to close, re-introduced
#: at the far end of a counter.  So the cap refuses to bury the newest and
#: says so by name, and the failure stays "one more grave was not kept"
#: instead of "a corpse you were looking at came back to life".
GRAVES_PER_SCENE_CAP = 4096


def _scene_key(scene: Any) -> str:
    """Case-folded scene key.

    ``Bg0002`` and ``bg0002`` are ONE scene everywhere else in this lane
    (``mob_loot.scene_key`` folds for the same reason), and a grave book that
    disagreed with the roster's spelling would resurrect a monster whenever a
    caller happened to hand in the other case.  ``DeathRecord.scene`` is the
    mob table's own ``SCENE`` tag, so the folding is a belt on top of a
    convention rather than a replacement for it.
    """
    if type(scene) is not str or not scene:
        raise ValueError("a scene tag is non-empty text, got %r" % (scene,))
    return scene.casefold()


@dataclass(frozen=True)
class GraveOutcome:
    """What one accepted kill did to the world's books."""

    scene: str
    remembered: Any = None
    already_buried: bool = False
    reason: str = ""

    @property
    def buried(self) -> bool:
        """The world's books hold this death NOW -- newly or already.

        Deliberately true for a re-commit that found the grave already dug:
        the caller's question at this point is "is this monster on the
        world's books", and answering "no" to a retry that succeeded the
        first time would make a caller re-try forever.  ``already_buried``
        is the field that separates the two, and the console line prints it.
        """
        return self.remembered is not None and not self.reason


@dataclass(frozen=True)
class SeedOutcome:
    """What one scene open took from the world's books into a register.

    ``register`` is ALWAYS a usable ``DeathRegister`` -- the merged one on a
    seed, and the caller's own object, unchanged and identical, on every
    refusal.  A call site that writes ``self.mob_death_register =
    seed_register(...).register`` therefore cannot lose its register to a
    refusal, which is the only way this seam could make the game worse than
    it was before it existed.
    """

    scene: str
    register: Any
    admitted: tuple = ()
    buried: int = 0
    reason: str = ""

    @property
    def seeded(self) -> bool:
        return not self.reason


class WorldDeaths:
    """WHICH IDENTITY IS DEAD IN WHICH SCENE, for the whole process.

    Ordered per scene by burial order, which is the order a console line
    prints and the order the cap would refuse in.  Never expires: see the
    module docstring on why a grave has no clock.
    """

    def __init__(self, graves_per_scene: int = GRAVES_PER_SCENE_CAP) -> None:
        # `type(...) is bool` explicitly: `isinstance(True, int)` is True in
        # this language, and `WorldDeaths(graves_per_scene=True)` would
        # silently mean "one grave per scene" -- a book that forgets the
        # second monster a player kills, with nothing raised anywhere.  The
        # same explicit bool rejection `world_scene_folder` writes at its own
        # door, for the same reason.
        if (type(graves_per_scene) is bool
                or not isinstance(graves_per_scene, int)
                or graves_per_scene < 1):
            raise ValueError("graves_per_scene must be a positive int")
        self._cap = graves_per_scene
        self._lock = threading.RLock()
        # scene key -> ordered {actor identity: DeathRecord}
        self._graves: dict = {}

    @property
    def graves_per_scene(self) -> int:
        return self._cap

    def bury(self, record: Any) -> tuple[bool, str]:
        """Put one death on the world's books.

        Returns ``(newly_buried, reason)``.  A record this scene already
        carries is ``(False, "")`` -- already buried, not an error and NOT an
        overwrite: the first burial holds the killer and the ceiling that
        were true when the monster actually died, and a re-commit (a retry
        that reached here twice) must not rewrite them.
        """
        if type(record) is not mob_death.DeathRecord:
            return (False, REFUSE_NOT_A_RECORD)
        try:
            fold = _scene_key(record.scene)
        except ValueError:
            return (False, REFUSE_SCENE_IS_UNREADABLE)
        with self._lock:
            graves = self._graves.setdefault(fold, collections.OrderedDict())
            if record.actor_identity in graves:
                return (False, "")
            if len(graves) >= self._cap:
                return (False, REFUSE_SCENE_IS_FULL)
            graves[record.actor_identity] = record
            return (True, "")

    def buried_in(self, scene: Any) -> tuple:
        """The graves one scene holds, oldest first.  Never raises."""
        try:
            fold = _scene_key(scene)
        except ValueError:
            return ()
        with self._lock:
            graves = self._graves.get(fold)
            if not graves:
                return ()
            return tuple(graves.values())

    def is_buried(self, scene: Any, actor_identity: Any) -> bool:
        try:
            fold = _scene_key(scene)
        except ValueError:
            return False
        with self._lock:
            return actor_identity in self._graves.get(fold, {})

    def forget(self, scene: Any, actor_identity: Any) -> bool:
        """Open one grave.  THE RESPAWN DOOR, and nothing calls it yet.

        Named and tested now rather than left to be invented later: the round
        that adds respawning must have exactly one way to say "this monster
        is alive again", and it must be a removal from these books and not a
        clear of them.
        """
        try:
            fold = _scene_key(scene)
        except ValueError:
            return False
        with self._lock:
            graves = self._graves.get(fold)
            if not graves or actor_identity not in graves:
                return False
            graves.pop(actor_identity, None)
            if not graves:
                self._graves.pop(fold, None)
            return True

    def clear(self) -> None:
        """Empty the books.  A TEST SEAM, and named as one."""
        with self._lock:
            self._graves.clear()


_WORLD: WorldDeaths | None = None
_WORLD_LOCK = threading.RLock()


def world_deaths() -> WorldDeaths:
    """The process's own grave book.  Built on first use, never rebuilt."""
    global _WORLD
    with _WORLD_LOCK:
        if _WORLD is None:
            _WORLD = WorldDeaths()
        return _WORLD


def install_world_deaths(world: Any) -> WorldDeaths:
    """Replace the process's grave book.  A TEST SEAM, named as one.

    Every entry point below takes a ``world=`` argument for the same reason,
    so a test never has to reach for this; it exists for the case a test
    exercises a call site that does not pass one.
    """
    global _WORLD
    if not isinstance(world, WorldDeaths):
        raise TypeError("a world grave book is a WorldDeaths")
    with _WORLD_LOCK:
        _WORLD = world
        return _WORLD


def remember_death(
    record: Any, *, world: Any = None, announce: bool = True,
) -> GraveOutcome:
    """An accepted kill enters the world's books.  NEVER RAISES.

    Called from :func:`mob_death.commit_death`, which sits under an inbound
    frame from a stranger by way of the attack dispatch: an escape here would
    take the v141 listener thread down mid-kill, so every failure comes back
    as a name on the outcome instead -- and, because ``commit_death`` is the
    one function in this lane that must not grow a new way to raise, this
    promise is load-bearing rather than tidy.

    It prints its own bounded ASCII line (G-OBS) rather than handing one back
    for the caller to print, the way ``mob_drop_presence`` does at its own
    call sites: ``mob_death.py`` has never printed anything and the round
    that made it start would have to answer for every test in this tree that
    reads a kill's stdout.  ``announce=False`` is for tests that assert on
    the outcome instead.
    """
    try:
        book = world if isinstance(world, WorldDeaths) else world_deaths()
        newly, reason = book.bury(record)
    except Exception as error:                          # noqa: BLE001
        outcome = GraveOutcome(
            "", reason="%s:%r" % (REFUSE_WORLD_RAISED, error))
        if announce:
            print(describe_remembered(outcome))
        return outcome
    scene = getattr(record, "scene", "")
    if type(scene) is not str:
        scene = ""
    outcome = GraveOutcome(
        scene,
        remembered=record if (newly or not reason) else None,
        already_buried=not newly and not reason,
        reason=reason,
    )
    if announce:
        print(describe_remembered(outcome))
    return outcome


def describe_remembered(outcome: GraveOutcome) -> str:
    """One bounded ASCII console line.  G-OBS."""
    if outcome.reason:
        return "%s scene=%r reason=%s" % (
            WORLD_REMEMBER_REFUSED_TOKEN, outcome.scene, outcome.reason)
    record = outcome.remembered
    return "%s scene=%r identity=0x%X killer=0x%X max_hp=%d already=%s" % (
        WORLD_REMEMBERED_TOKEN, outcome.scene,
        getattr(record, "actor_identity", 0),
        getattr(record, "killer_identity", 0),
        getattr(record, "max_hp", 0),
        "yes" if outcome.already_buried else "no",
    )


def seed_register(
    register: Any, scene: Any, *, world: Any = None,
) -> SeedOutcome:
    """Give a session's register the graves the world says are in one scene.

    THIS IS THE SEAM R309 NEEDS, and the mirror of
    ``mob_ground_persistence.seed_cell``.  Call it where a session learns
    which scene its player is standing in -- ``runtime.py``'s
    ``_sync_combat_scene_state``, at the top of the branch that re-opens the
    roster -- and the corpse a player left is still a corpse when they log
    back in.  NEVER RAISES.

    ONLY THIS SCENE'S GRAVES, never the whole book: the register is keyed by
    ``(scene, actor_identity)`` precisely because one wire identity can name
    two monsters in two scenes, and handing a session every grave in the
    process is the cross-scene leak this lane refuses everywhere else.

    IDEMPOTENT, because the call site is a scene-edge detector that will
    reach it again on every return trip: a grave the register already carries
    is skipped rather than re-added (``DeathRegister.with_death`` refuses a
    duplicate by contract, and a refusal here would be a raise on the
    listener thread).

    THE COUNTER IS PRESERVED, WHICH IS THE WHOLE REASON THIS RETURNS A NEW
    VALUE RATHER THAN MUTATING ONE.  Each admitted grave goes in through
    ``with_death``, so the seeded register's ``generation`` is the caller's
    plus the number admitted, and ``generation == len(records)`` still holds
    for a register that started empty -- the invariant ``commit_death``'s
    "same length, different lineage" guard is written against.  A kill
    computed AFTER the seed therefore commits normally; a kill computed
    BEFORE it and committed after is refused as ``REFUSE_REGISTER_STALE``,
    which is the correct answer and the reason the call site belongs at the
    scene open, before the roster is handed to anyone.
    """
    if type(register) is not mob_death.DeathRegister:
        return SeedOutcome("", register, reason=REFUSE_NOT_A_REGISTER)
    try:
        fold = _scene_key(scene)
    except ValueError:
        return SeedOutcome("", register, reason=REFUSE_SCENE_IS_UNREADABLE)
    try:
        book = world if isinstance(world, WorldDeaths) else world_deaths()
        buried = book.buried_in(fold)
    except Exception as error:                          # noqa: BLE001
        return SeedOutcome(
            fold, register, reason="%s:%r" % (REFUSE_WORLD_RAISED, error))
    if not buried:
        return SeedOutcome(fold, register, (), 0)
    admitted = []
    seeded = register
    for record in buried:
        try:
            if seeded.is_dead(record.actor_identity, record.scene):
                continue
            seeded = seeded.with_death(record)
        except mob_death.MobDeathContractError:
            # One unusable row must not cost the scene every other grave in
            # it.  Counted in the console line, never raised: the caller is
            # the listener thread.
            continue
        except Exception:                               # noqa: BLE001
            return SeedOutcome(
                fold, register, (), len(buried),
                reason=REFUSE_REGISTER_REFUSED_THE_ROW)
        admitted.append(record)
    return SeedOutcome(fold, seeded, tuple(admitted), len(buried))


def describe_seeded(outcome: SeedOutcome) -> str:
    """One bounded ASCII console line.  G-OBS."""
    if outcome.reason:
        return "%s scene=%r buried=%d reason=%s" % (
            WORLD_SEED_REFUSED_TOKEN, outcome.scene, outcome.buried,
            outcome.reason)
    return "%s scene=%r admitted=%d buried=%d identities=%s" % (
        WORLD_SEEDED_TOKEN, outcome.scene, len(outcome.admitted),
        outcome.buried,
        ",".join("0x%X" % row.actor_identity for row in outcome.admitted)
        or "none",
    )


def seed_the_session_register(
    register: Any, scene: Any, *, world: Any = None, announce: bool = True,
) -> Any:
    """The ONE LINE the call site asks for.  NEVER RAISES.

    ``self.mob_death_register = mob_death_persistence.
    seed_the_session_register(self.mob_death_register, folder)``

    Two functions do the work (:func:`seed_register` decides,
    :func:`describe_seeded` says), and they stay separate because a test that
    wants the decision must not have to read stdout for it.  This is the
    third name only so that the edit asked of a file this lane does not own
    is one statement that cannot half-happen.  Returns the caller's own
    register unchanged on every refusal.
    """
    outcome = seed_register(register, scene, world=world)
    if announce:
        print(describe_seeded(outcome))
    return outcome.register


#: The pasteable call site, kept next to the function it names so that the
#: letter and the code cannot drift apart (the same device
#: ``mob_drop_presence.GROUND_REANNOUNCE_WIRING`` uses for its own request).
DEATH_SEED_WIRING = (
    "runtime.py, _sync_combat_scene_state, as the FIRST statement inside\n"
    "`if folder != self.mob_combat_scene_folder:` -- before\n"
    "`ledger = mob_combat.open_ledger(roster, scene=folder)`, because the\n"
    "loop right after it rehydrates the ledger's zeros FROM this register\n"
    "and a seed that lands after the loop would leave the ledger at full HP\n"
    "with the register saying dead: mob_death's own\n"
    "REFUSE_LEDGER_DISAGREES_WITH_REGISTER, and a corpse that answers hits\n"
    "with live damage numbers.\n"
    "\n"
    "    self.mob_death_register = (\n"
    "        mob_death_persistence.seed_the_session_register(\n"
    "            self.mob_death_register, folder))\n"
    "\n"
    "import: `from . import mob_death_persistence`\n"
)
