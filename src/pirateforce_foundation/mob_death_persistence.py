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

WHAT THIS BOOK IS AUTHORITATIVE OVER  [COO 2049: advisory until Door B].
pf-adversary asked the sharp version of the question below and it deserves a
straight answer rather than an implied one: ``WorldGround`` grew an atomic
``claim`` the moment two sessions could see one floor, and this book has no
operation a second killer can lose.  THE ANSWER, AND IT IS A CHOICE, NOT AN
OVERSIGHT: this book is authoritative over "was this monster dead when a
session opened this scene" and over nothing else.  It is READ at a scene open
and it is ADVISORY everywhere else -- it does not gate a strike, a roll or a
drop.  Making it authoritative over the KILL would change what a second
player standing in the scene sees happen in front of them (a monster that
stops answering their attacks mid-fight), which is a game-design ruling and
not a lane's call.  ``COO-DECISION 20260904_2049`` (answering
``pf_bridge/notes_to_chief/20260904_2005_LANE-B-ASK-COO-what-is-the-
worlds-grave-book-authoritative-over.md``) settled it: (a) advisory stands
for now -- unchanged from the paragraph above; (b) authoritative-over-the-kill
is the destination, queued behind Door B (M4 item 1) landing, because what a
second player sees has to ride the same frame Door B sends.  When that round
comes, the spec is already decided and does not need re-litigating: the
second killer sees the monster become a corpse in the SAME frame a relog
shows one in; their strike is refused by name (``mob_already_dead_in_the_
world``); there is no second drop; and the door is one atomic
``claim_the_kill(scene, identity)``, the same shape as
:meth:`mob_ground_persistence.WorldGround.claim`.  Until that round, this
file does the smaller, strictly-not-worse thing below.

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

from . import field_mobs
from . import mob_combat
from . import mob_death

#: Shippable with no scenario flag: a player gets this by default or not at
#: all -- a grave that only exists under a trial flag is not a grave.
production_allowed = True

#: One console line per death that entered the world's books.
WORLD_REMEMBERED_TOKEN = "MOB_DEATH_WORLD_REMEMBERED"
#: A death that could not enter them, by name.  Never an exception.
WORLD_REMEMBER_REFUSED_TOKEN = "MOB_DEATH_WORLD_REMEMBER_REFUSED"
#: One console line per register seeded at a scene open.
#:
#: ~~INCLUDING the ones that seeded nothing -- "this scene has no graves" and
#: "the seam never ran" are different facts and an attended round greps for
#: exactly that difference.~~ -- STRUCK, pf-adversary round ``amz1w5``, and
#: the strike is a correction of THIS FILE and not of the idea.  The call
#: site runs on every dispatch, so an unconditional line would be one per
#: swing; :func:`_worth_saying` therefore prints every admission, refusal
#: and skip, plus the FIRST empty seed of each scene IN THE PROCESS, and is
#: silent after that.  WHAT THAT COSTS, stated rather than left for a
#: grader to trip over: for the SECOND and later login into a scene whose
#: book is empty, "the seam ran and found nothing" and "the call site was
#: never added" are both silence.  The token proves the seam ran when it
#: prints; its absence proves nothing.  An attended round that needs the
#: negative arm reads the first login of the boot, or greps
#: ``MOB_DEATH_WORLD_REMEMBERED`` from the kill instead.
WORLD_SEEDED_TOKEN = "MOB_DEATH_WORLD_SEEDED"
#: A seed that could not happen, by name.
WORLD_SEED_REFUSED_TOKEN = "MOB_DEATH_WORLD_SEED_REFUSED"

REFUSE_NOT_A_RECORD = "not_a_death_record"
REFUSE_NOT_A_REGISTER = "not_a_death_register"
REFUSE_SCENE_IS_UNREADABLE = "scene_is_unreadable"
REFUSE_SCENE_IS_FULL = "scene_grave_cap_reached"
REFUSE_WORLD_RAISED = "world_raised"
REFUSE_REGISTER_REFUSED_THE_ROW = "register_refused_the_row"
#: A caller named a ``world=`` that is not a grave book.  A REFUSAL AND NOT A
#: FALLBACK: pf-adversary measured the alternative, and it was the worst
#: shape a door can have -- a caller asking for isolation, mistyping the
#: argument, and silently getting the process-global book it was opting out
#: of, under a console line that says the write succeeded.
REFUSE_NOT_A_GRAVE_BOOK = "not_a_grave_book"
#: The ledger handed to :func:`seed_the_session_state` is not a combat
#: ledger.  Its register half still happens; see that function.
REFUSE_NOT_A_LEDGER = "not_a_combat_ledger"
#: The ledger could not take the zeros the register just took.  Costs the
#: register its seed too: see :func:`seed_the_session_state`.
REFUSE_LEDGER_REFUSED_THE_ROW = "ledger_refused_the_row"
#: The record's ceiling is not the ceiling its roster row carries.
#: ``repopulation_entries`` refuses on this field too, and a book that
#: checked only two of the three would still be able to empty a town.
REFUSE_CEILING_IS_NOT_THE_ROSTERS = "ceiling_is_not_the_rosters"
#: The scene has no mined mob table, so nothing in it can be a field mob's
#: grave.  See :func:`roster_key_of` for why this is a refusal and not a
#: best effort.
REFUSE_SCENE_HAS_NO_MINED_ROSTER = "scene_has_no_mined_roster"
#: The identity is not a row of that scene's mined roster -- a diag object, a
#: withdrawn identity, a fabricated number.  THE REFUSAL THAT KEEPS THIS
#: WHOLE FILE FROM BEING A LIABILITY; see :func:`roster_key_of`.
REFUSE_IDENTITY_NOT_IN_THE_ROSTER = "identity_not_in_the_mined_roster"
#: The record spells the scene differently from the roster's own tag.  Kept
#: apart from ``scene_has_no_mined_roster`` on purpose: "there is no such
#: scene" and "there is, and you spelled it the other way" send an operator
#: to two different files.
REFUSE_SCENE_SPELLING_IS_NOT_THE_ROSTERS = "scene_spelling_is_not_the_rosters"

#: How many distinct graves one scene may hold.  A GUARD, NOT A GAME RULE: a
#: scene's roster is finite (the largest mined table in this tree is far
#: under a hundred rows) and an identity can only die once, so production
#: cannot reach this.  It is here so that a caller feeding this module
#: fabricated identities in a loop cannot grow the dict without bound.
#:
#: UNREACHABLE BY CONSTRUCTION, not merely by expectation: :func:`roster_key_of`
#: refuses any identity outside the scene's mined roster, and an identity can
#: only be buried once, so a scene's graves are bounded by its roster (12 rows
#: at the widest table in this tree) whatever a caller does.
#:
#: ~~THE NEWEST IS REFUSED, NOT THE OLDEST RETIRED... the failure stays "one
#: more grave was not kept" instead of "a corpse you were looking at came back
#: to life".~~ -- STRUCK, pf-adversary round ``amz1w5``, and the strike is
#: kept because the reasoning was wrong and somebody will think it again: the
#: grave the cap refuses is the one the player JUST dug, whose corpse is on
#: their screen right now, so "not kept" and "came back to life" are the same
#: sentence for it.  BOTH eviction policies resurrect something; only which
#: corpse differs.  Refusing the newest is still the choice here, for the one
#: honest reason left -- it leaves every grave already established stable
#: rather than reshuffling the book under a player who is standing in it --
#: and the roster gate above is what makes the question moot in production.
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


_ROSTER_CACHE: dict = {}
_ROSTER_CACHE_LOCK = threading.RLock()


def roster_key_of(record: Any) -> tuple[str, str]:
    """``("", reason)`` unless this record is a row of a mined roster.

    THE GATE THAT KEEPS THIS FILE FROM BEING A LIABILITY, and it was added
    after pf-adversary (round ``amz1w5``) MEASURED the failure it prevents,
    on the real rosters, in one process:

        A diag multi-object kill (``mob_diag_multi_object`` stamps its
        identities with ``field_mob_tables.SCENE``, so ``0x4329``/``0x432A``/
        ``0x432C`` arrive here tagged ``bg0001``) puts an identity in the
        world's books that bg0001's mined roster does not contain.  Every
        LATER login into bg0001 -- including a character that has never seen
        a diag config -- would be seeded with it, and
        ``mob_death.repopulation_entries`` refuses a register row whose scene
        is one of the roster's but whose identity is not a roster key
        (``REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER``).  The arrival census
        raises inside its own fail-closed catch, ships NO frame, and the
        player logs into an empty town -- for the life of the process, not
        the session.  ``0x201F``, the sanctioned first target withdrawn from
        the bg0001 roster, does the same thing.

    So a grave is only ever dug for an identity the scene's own mined table
    ships, spelled with the table's own ``SCENE`` tag.  The exact-spelling
    half closes a second measured hole: the book folds case for its KEY but
    stores the record verbatim, and every consumer downstream
    (``runtime.py``'s rehydrate guard, ``live_roster``,
    ``repopulation_entries``) compares ``record.scene`` with ``==``.  A
    record spelled ``bg0002`` would be seeded, silently skipped by all
    three, and the console would print a green line over a monster still
    standing at full HP.

    The roster is read through ``field_mobs``' own public readers and cached
    per scene: a mined table is a frozen constant in this tree, and re-typing
    twelve rows on every kill would put a roster load on the listener
    thread's hot path for a number that cannot change while the process runs.
    """
    if type(record) is not mob_death.DeathRecord:
        return ("", REFUSE_NOT_A_RECORD)
    try:
        fold = _scene_key(record.scene)
    except ValueError:
        return ("", REFUSE_SCENE_IS_UNREADABLE)
    with _ROSTER_CACHE_LOCK:
        cached = _ROSTER_CACHE.get(fold)
        if cached is None:
            cached = ("", frozenset())
            for scene in field_mobs.live_scenes():
                if scene.casefold() != fold:
                    continue
                try:
                    roster = field_mobs.load_roster(scene)
                except Exception:                       # noqa: BLE001
                    # NOT CACHED, and pf-adversary had to say so twice: a
                    # transient raise on the FIRST call for a scene would
                    # otherwise refuse every death in it for the life of the
                    # process, under a name ("scene_has_no_mined_roster")
                    # that sends an operator hunting for a table sitting
                    # right there.  A raise is answered once, not forever.
                    return ("", REFUSE_SCENE_HAS_NO_MINED_ROSTER)
                cached = (
                    scene,
                    frozenset(
                        (mob.actor_identity, mob.max_hp) for mob in roster),
                )
                break
            _ROSTER_CACHE[fold] = cached
    tag, rows = cached
    if not tag:
        return ("", REFUSE_SCENE_HAS_NO_MINED_ROSTER)
    if record.scene != tag:
        return ("", REFUSE_SCENE_SPELLING_IS_NOT_THE_ROSTERS)
    if (record.actor_identity, record.max_hp) in rows:
        return (fold, "")
    # Which of the two fields is wrong decides which file an operator opens,
    # so they are named apart.  BOTH are checked because
    # `repopulation_entries` refuses on BOTH (mob_death's
    # REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER covers the ceiling as well as
    # the identity), and a gate that closed two of the three doors this book
    # can empty a town through would be a gate in name only -- pf-adversary,
    # round amz1w5, second pass.
    if any(identity == record.actor_identity for identity, _hp in rows):
        return ("", REFUSE_CEILING_IS_NOT_THE_ROSTERS)
    return ("", REFUSE_IDENTITY_NOT_IN_THE_ROSTER)


def forget_roster_cache() -> None:
    """Drop the memoised rosters.  A TEST SEAM, named as one -- and the
    symmetry ``forget_announced_scenes`` already has, which this module was
    missing for one round."""
    with _ROSTER_CACHE_LOCK:
        _ROSTER_CACHE.clear()


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
    #: Graves the book held for this scene that the roster gate turned away.
    #: Should always be zero -- `bury` refuses them at the door -- and it is
    #: counted and PRINTED anyway, because the day it is not zero is the day
    #: a mined table shrank under a book that was filled before it did, and
    #: that day must arrive as a number in a console line and not as a town
    #: that silently stopped composing its census.
    skipped: int = 0

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

        THE ROSTER GATE IS HERE AND NOT ONLY IN :func:`remember_death`,
        because what must be true is a property of the BOOK -- "this book
        cannot hold a row that will refuse a scene's census" -- and a
        property of a container that only its polite callers maintain is not
        a property.
        """
        fold, reason = roster_key_of(record)
        if reason:
            return (False, reason)
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
    call sites.  ~~``mob_death.py`` has never printed anything and the round
    that made it start would have to answer for every test in this tree that
    reads a kill's stdout.~~ -- STRUCK, pf-adversary round ``amz1w5``, and the
    strike is the honest half: a burial IS wired into ``commit_death``, so
    ``mob_death.py`` DOES print now, at one line per accepted kill.  That
    sentence described a hazard and then did not close it.  What closes it is
    that ``commit_death`` grew ``announce=`` and ``world=`` keywords of its
    own, so the escape below is reachable from the call site that actually
    needed it -- which is what the sentence should have said the first time.
    """
    if world is not None and not isinstance(world, WorldDeaths):
        outcome = GraveOutcome("", reason=REFUSE_NOT_A_GRAVE_BOOK)
        if announce:
            print(describe_remembered(outcome))
        return outcome
    try:
        book = world if world is not None else world_deaths()
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
    if world is not None and not isinstance(world, WorldDeaths):
        return SeedOutcome("", register, reason=REFUSE_NOT_A_GRAVE_BOOK)
    try:
        book = world if world is not None else world_deaths()
        buried = book.buried_in(fold)
    except Exception as error:                          # noqa: BLE001
        return SeedOutcome(
            fold, register, reason="%s:%r" % (REFUSE_WORLD_RAISED, error))
    if not buried:
        return SeedOutcome(fold, register, (), 0)
    admitted = []
    skipped = 0
    seeded = register
    for record in buried:
        # THE ROSTER GATE, A SECOND TIME.  `bury` already refuses a row the
        # scene's mined table does not ship, so nothing here should ever be
        # skipped -- and it is checked again anyway, because the cost of
        # being wrong is asymmetric and measured: ONE row outside the roster
        # makes `repopulation_entries` refuse the WHOLE census for every
        # later session in the process, and the arrival frame is not sent at
        # all.  A cheap second read against a cached frozenset is the right
        # price for "the seam can never be the thing that empties a town".
        try:
            gated = roster_key_of(record)[1]
        except Exception:                               # noqa: BLE001
            # This function promises never to raise and its caller is the
            # listener thread; `roster_key_of` reads frozen tables and should
            # not raise, and "should not" is not the promise this one makes.
            gated = REFUSE_WORLD_RAISED
        if gated:
            skipped += 1
            continue
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
    return SeedOutcome(fold, seeded, tuple(admitted), len(buried), "", skipped)


def describe_seeded(outcome: SeedOutcome) -> str:
    """One bounded ASCII console line.  G-OBS."""
    if outcome.reason:
        return "%s scene=%r buried=%d reason=%s" % (
            WORLD_SEED_REFUSED_TOKEN, outcome.scene, outcome.buried,
            outcome.reason)
    return "%s scene=%r admitted=%d buried=%d skipped=%d identities=%s" % (
        WORLD_SEEDED_TOKEN, outcome.scene, len(outcome.admitted),
        outcome.buried, outcome.skipped,
        ",".join("0x%X" % row.actor_identity for row in outcome.admitted)
        or "none",
    )


#: Scene keys whose "the seam ran and there was nothing to take" line has
#: already been printed once in this process.  Bounded by the number of
#: scenes that exist, which is seventeen.
_ANNOUNCED_EMPTY: set = set()
_ANNOUNCED_LOCK = threading.RLock()


def _worth_saying(outcome: SeedOutcome) -> bool:
    """Whether this outcome earns a console line.

    THE CALL SITE RUNS ON EVERY ATTACK, so "print every time" is not
    available: it would put one line per swing on a cp874 console and bury
    the lines that matter.  "Print only when something changed" is not
    available either -- the module's own reason for always printing stands:
    "this scene has no graves" and "the seam never ran" are different facts
    and an attended round greps for exactly that difference.

    So: every admission and every refusal says so, and the FIRST empty seed
    of each scene says so too.  After that, a scene whose graves are already
    in the register is silent, which is the only state that repeats.
    """
    with _ANNOUNCED_LOCK:
        if outcome.reason or outcome.admitted or outcome.skipped:
            # A scene that has just said something has, by saying it, also
            # said "the seam ran here" -- so the no-op that follows it does
            # not have to say it again.  Recorded HERE and not only on the
            # empty branch, or every scene with graves would print one
            # redundant empty line after its real one.
            _ANNOUNCED_EMPTY.add(outcome.scene)
            return True
        if outcome.scene in _ANNOUNCED_EMPTY:
            return False
        _ANNOUNCED_EMPTY.add(outcome.scene)
        return True


def forget_announced_scenes() -> None:
    """Let the empty-seed line be printed again.  A TEST SEAM, named as one."""
    with _ANNOUNCED_LOCK:
        _ANNOUNCED_EMPTY.clear()


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

    IDEMPOTENT ON EVERY CALL, because :data:`DEATH_SEED_WIRING` asks for it
    OUTSIDE the scene-change branch and that branch's condition is false on
    the path this whole round exists to fix.  A repeat call for a scene whose
    graves the register already holds admits nothing, returns the caller's
    own object, and (see :func:`_worth_saying`) says nothing.  ~~and cheap:
    one dict lookup per grave~~ -- STRUCK, pf-adversary measured 16.6 us on a
    12-grave register against 0.48 us for that claim: ``DeathRegister.
    is_dead`` is a linear scan that re-validates its arguments on every call.
    Still far under a frame, and the honest number is the one that belongs in
    the note that uses cheapness as an argument.

    PREFER :func:`seed_the_session_state`, which does this AND the ledger.
    This one is the register half alone, kept public because the tests and
    the ledger-less paths want it; a production call site that seeds the
    register without the ledger is the crash that function's docstring
    describes.
    """
    outcome = seed_register(register, scene, world=world)
    if announce and _worth_saying(outcome):
        print(describe_seeded(outcome))
    return outcome.register


def seed_the_session_state(
    register: Any, ledger: Any, scene: Any, *,
    world: Any = None, announce: bool = True,
) -> tuple:
    """THE CALL SITE.  Seed the register AND the ledger together, or neither.

    ``self.mob_death_register, self.mob_combat_ledger = (
        mob_death_persistence.seed_the_session_state(
            self.mob_death_register, self.mob_combat_ledger, folder))``

    WHY THIS TAKES THE LEDGER, AND IT IS THE WHOLE ROUND'S LESSON.  A grave
    that reaches the register and not the ledger is not a smaller version of
    this feature -- it is a CRASH.  ``mob_death.repopulation_entries`` refuses
    when the two disagree (``REFUSE_LEDGER_DISAGREES_WITH_REGISTER``), the
    arrival census reaches it from an ``else:`` clause its own ``try`` does
    not cover, and ``runtime.py`` says in its own words what happens next:
    the v141 listener thread unwinds.  pf-adversary MEASURED exactly that,
    on bg0001, from this round's own first answer:

        kill a Training Iron Man, relog, and the register carried the grave
        while the boot ledger still stood at 198125 HP -- because the loop
        that rehydrates the ledger lives INSIDE ``if folder !=
        self.mob_combat_scene_folder:``, and that branch never runs for a
        character whose stored scene is the one the process booted on.

    So the two structures move together, here, in one statement, and the
    call site cannot land a half of it.  This is also why the ask is no
    longer "put a line inside that branch" (it never runs for bg0001) and no
    longer "put a line before it" (the ledger would be left behind).

    WHAT IT DOES TO THE LEDGER: for each grave admitted, the SAME operation
    the branch's own loop performs -- ``with_balance(MobBalance(identity,
    that row's own ceiling, 0))`` -- and only for identities the ledger
    actually carries.  A ledger that is still open on the scene the player
    is LEAVING carries none of the destination's identities, so it is
    returned untouched and the branch re-opens it a moment later and
    rehydrates it from the register this call just seeded.  Both orders are
    correct; that is the point of doing them together.

    NEVER RAISES.  Returns ``(register, ledger)``, and on every refusal the
    caller's own two objects, unchanged.
    """
    outcome = seed_register(register, scene, world=world)
    seeded = outcome.register
    if not isinstance(ledger, mob_combat.CombatLedger):
        # BOTH HALVES OR NEITHER, and that rule decides this branch too: a
        # seeded register beside a ledger this function could not even look
        # at is the disagreement it exists to prevent, so the register is
        # handed back unseeded and named.
        refused = SeedOutcome(
            outcome.scene, register, (), outcome.buried,
            reason=REFUSE_NOT_A_LEDGER, skipped=outcome.skipped)
        if announce:
            print(describe_seeded(refused))
        return (register, ledger)
    if outcome.reason or not outcome.admitted:
        if announce and _worth_saying(outcome):
            print(describe_seeded(outcome))
        return (seeded, ledger)
    applied = 0
    try:
        carried = set(ledger.identities())
        for record in outcome.admitted:
            if record.actor_identity not in carried:
                continue
            standing = ledger.balance_of(record.actor_identity)
            if standing.current_hp == mob_death.HP_WHEN_DEAD:
                continue
            ledger = ledger.with_balance(mob_combat.MobBalance(
                record.actor_identity, standing.max_hp,
                mob_death.HP_WHEN_DEAD))
            applied += 1
    except Exception as error:                          # noqa: BLE001
        # BOTH HALVES OR NEITHER.  A register holding graves the ledger does
        # not is the crash this function exists to prevent, so a ledger that
        # cannot take them costs the register its seed too -- the caller gets
        # back exactly what it handed in, and the game keeps yesterday's
        # behaviour instead of gaining a way to fall over.
        refused = SeedOutcome(
            outcome.scene, register, (), outcome.buried,
            reason="%s:%r" % (REFUSE_LEDGER_REFUSED_THE_ROW, error),
            skipped=outcome.skipped)
        if announce:
            print(describe_seeded(refused))
        return (register, ledger)
    if announce and _worth_saying(outcome):
        print("%s ledger_zeroed=%d" % (describe_seeded(outcome), applied))
    return (seeded, ledger)


#: The pasteable call site, kept next to the function it names so that the
#: letter and the code cannot drift apart (the same device
#: ``mob_drop_presence.GROUND_REANNOUNCE_WIRING`` uses for its own request).
DEATH_SEED_WIRING = (
    "runtime.py, _sync_combat_scene_state, immediately after\n"
    "`if folder is None: return None` and BEFORE\n"
    "`if folder != self.mob_combat_scene_folder:`.\n"
    "\n"
    "    self.mob_death_register, self.mob_combat_ledger = (\n"
    "        mob_death_persistence.seed_the_session_state(\n"
    "            self.mob_death_register, self.mob_combat_ledger, folder))\n"
    "\n"
    "import: `from . import mob_death_persistence`\n"
    "\n"
    "ONE STATEMENT, BOTH STRUCTURES, and each half of that is a defect this\n"
    "round already shipped a wrong answer for and had measured back at it.\n"
    "\n"
    "OUTSIDE THE BRANCH: runtime.py seeds `self.mob_combat_scene_folder`\n"
    "from the BOOT roster's own scene in __init__, so for a character whose\n"
    "stored scene is the boot scene the condition is false on its very first\n"
    "evaluation and that branch NEVER RUNS.  A seed inside it would fire for\n"
    "scene 2 -- where R309 happened -- and never for bg0001, the scene the\n"
    "game boots into: GT-223 green in one town and the identical corpse\n"
    "standing up in the other.\n"
    "\n"
    "AND THE LEDGER, NOT ONLY THE REGISTER: the loop that rehydrates the\n"
    "ledger's zeros lives INSIDE that same branch.  A seed placed before it\n"
    "that touched only the register would leave the boot ledger at full HP\n"
    "with the register saying dead -- mob_death's own\n"
    "REFUSE_LEDGER_DISAGREES_WITH_REGISTER -- and the arrival census reaches\n"
    "that refusal from an `else:` clause its own `try` does not cover, so it\n"
    "does not degrade: it unwinds the v141 listener thread.  MEASURED on\n"
    "bg0001 (0x2068, ledger 198125 HP, register dead, census raised).\n"
    "So the function takes both and returns both, and returns the caller's\n"
    "own two objects unchanged if either half cannot be done.\n"
    "\n"
    "IT DOES NOT JOIN THE ATOMIC TRIO at the end of that branch (ledger,\n"
    "mob_ai_register, mob_combat_scene_folder, built into locals so a raise\n"
    "from open_register cannot leave them on two different scenes --\n"
    "pf-adversary round pk14rf).  It does not move the session between\n"
    "scenes: it adds the CURRENT folder's graves and removes nothing, and a\n"
    "ledger still open on the scene being LEFT carries none of the\n"
    "destination's identities, so it comes back untouched and the branch\n"
    "re-opens it a moment later from the register this call just seeded.\n"
    "\n"
    "SAFE ON EVERY DISPATCH, which is what being outside the branch costs:\n"
    "idempotent, returns the caller's own objects when it admits nothing,\n"
    "and silent on a repeat (see _worth_saying).  Measured at ~17 us on a\n"
    "12-grave scene -- DeathRegister.is_dead is a linear scan with per-call\n"
    "validation, not the dict lookup an earlier draft of this note claimed.\n"
)
