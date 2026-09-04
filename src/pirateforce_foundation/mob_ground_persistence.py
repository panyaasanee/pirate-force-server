"""LANE-B (COMBAT): the ground belongs to the WORLD, not to one session.

WHAT A PLAYER SEES BECAUSE OF THIS FILE.  Yesterday (KA1A, R309, measured on
the real client -- `pf_bridge/notes_to_chief/20260904_1430`): kill a Fighting
Fish soldier in scene 2, watch the Energy Cubic Crystal land, close the client,
log straight back in on a server that never restarted, and the floor is bare.
The crystal was never taken and never expired; it simply lived in the
`mob_loot.DropLedgerCell` of the session that had ended, and the new session
was handed an empty one.  With this file and its two call sites, the row is
still standing when the player walks back in.

WHY A SECOND STRUCTURE AND NOT A LONGER-LIVED CELL.  A cell is a SESSION'S
view of the ground: it publishes to one client, it carries that client's
scene, and it holds the `looted` bookkeeping that stops one death being rolled
twice.  Sharing one cell between two logins would share all three.  What is
actually shared between them is smaller and has no client in it -- WHICH ROWS
ARE STANDING IN WHICH SCENE -- so that is what :class:`WorldGround` holds, and
a session's cell is seeded FROM it rather than replaced BY it.

THE RULING THIS IMPLEMENTS.  `COO-DECISION 2026-09-03T10:48+07:00`: an object
that has fallen belongs to the world, per scene.  `COO-DECISION
2026-09-03T18:44+07:00` gives LANE-B the drop-time call site and the
server-wide `drop_key`; both are here (`remember_generation`, and
`mob_loot.admit_standing_drops` raising `issued_through` past every key it
readmits, so a new session's issuer can never mint a key that is already lying
on a floor).  `COO-DECISION 2026-09-01T02:53+07:00` -- no ledger row is
removed until a removal publisher exists -- is why :meth:`WorldGround.forget`
is called ONLY from the pickup that already published the removal, and why
expiry here is the same lazy per-row sweep the cell already runs rather than a
clear.

TWO LAYERS, AND ONLY ONE OF THEM IS LIVE TODAY.  In memory
(:class:`WorldGround`) the ground survives a RELOGIN, which is what R309
measured and what this round makes true.  It does not survive a server
RESTART: that needs the `ground_drops` table `COO-DECISION 2026-09-03T18:43
+07:00` ordered, and :func:`persist_generation` below is this lane's call site
for its write half -- live as soon as a caller hands it a store.  THE READ
HALF IS REFUSED BY NAME AND ON PURPOSE (:data:`REFUSE_TAKEN_DOOR_IS_ABSENT`):
that door can say what was ever dropped and cannot yet say what is STILL ON
THE GROUND, so restoring from it would put every picked-up item back on the
floor at every boot -- duplication, dressed as persistence.  The door needs a
`taken` marker (a marker, NOT a delete -- `COO-DECISION 2026-09-01T02:53`);
`pf_bridge/notes_to_chief/20260904_1650_LANE-B-TO-LANE-DB-ground-drops-need-a-
taken-marker.md` is the ticket, and the day those two methods exist
:func:`restore_scene_ground` starts answering with no edit here.
"""
from __future__ import annotations

import collections
import threading
import time as _time
from dataclasses import dataclass
from typing import Any

from . import mob_loot

#: Shippable with no scenario flag: this file's whole purpose is behaviour a
#: player gets by default (lane charter, and `lane_hooks`'s own gate).
production_allowed = True

#: One console line per kill that put rows into the world.
WORLD_REMEMBERED_TOKEN = "MOB_GROUND_WORLD_REMEMBERED"
#: One console line per cell seeded at a scene entry, INCLUDING the ones that
#: seeded nothing -- "the floor was empty" and "the seam never ran" are
#: different facts and an attended round greps for exactly this difference.
WORLD_SEEDED_TOKEN = "MOB_GROUND_WORLD_SEEDED"
#: A seed that could not happen, by name.
WORLD_SEED_REFUSED_TOKEN = "MOB_GROUND_WORLD_SEED_REFUSED"
#: One console line per generation offered to the durable door.
DB_PERSIST_TOKEN = "MOB_GROUND_DB_PERSIST"
#: The durable door was not usable, by name.  Never an exception.
DB_PERSIST_REFUSED_TOKEN = "MOB_GROUND_DB_PERSIST_REFUSED"
#: The durable READ half stood down, by name.  See the module docstring.
DB_RESTORE_REFUSED_TOKEN = "MOB_GROUND_DB_RESTORE_REFUSED"

REFUSE_NOT_A_CELL = "not_a_cell"
REFUSE_ROW_IS_NOT_A_DROP = "row_is_not_a_drop"
REFUSE_SCENE_IS_UNREADABLE = "scene_is_unreadable"
REFUSE_CELL_HAS_NO_SCENE = "cell_has_no_scene"
REFUSE_CELL_RAISED = "cell_raised"
REFUSE_STORE_CANNOT_BE_ASKED = "store_cannot_be_asked"
REFUSE_WRITE_DOOR_IS_ABSENT = "write_door_is_absent"
#: The read half of the durable door cannot say what is STILL on the ground.
#: The module docstring says why this is a refusal and not a best effort.
REFUSE_TAKEN_DOOR_IS_ABSENT = "taken_door_is_absent"
REFUSE_DOOR_RAISED = "door_raised"

#: The two methods `SQLiteStore` needs before a restore is honest.  Probed by
#: name rather than by a version number: LANE-DB lands them when it lands
#: them, and this file wants no round of its own on that day.
TAKEN_DOOR_METHOD = "mark_ground_drop_taken"
STANDING_DOOR_METHOD = "list_ground_drops_still_on_the_ground"

#: How many rows one scene's world floor may hold before the OLDEST standing
#: row is retired to make room.  A bound, not a game rule: rows leave by being
#: taken or by expiring, and this is only here so that a server nobody logs
#: into cannot grow this dict without limit.  Retiring the oldest (rather than
#: refusing the newest) keeps the failure mode "the floor forgets what nobody
#: came back for" instead of "a kill's loot silently never appeared".
ROWS_PER_SCENE_CAP = 512

#: How many taken keys per scene the duplication guard remembers.  Same shape
#: and same reason as ``mob_loot.EXPIRED_KEY_MEMORY``: a refusal needs evidence
#: and evidence must be bounded.  Sized well past one session's kills inside
#: one drop lifetime, so a key rolls out of it only long after every cell that
#: could have been seeded with it has expired the row anyway.
TAKEN_KEY_MEMORY = 4096

#: The refusal a second session gets when it clicks a row its own cell still
#: draws and somebody else already picked up.  A NAME OF ITS OWN, not
#: ``drop_already_taken``: that one means "this session took it", and an
#: operator reading a console needs to be able to tell the day two sessions
#: were seeded from one floor from the day one player double-clicked.
REFUSE_TAKEN_BY_ANOTHER_SESSION = "drop_taken_by_another_session"


@dataclass(frozen=True)
class RememberOutcome:
    """What one generation did to the world's floor."""

    scene: str
    remembered: tuple = ()
    already_standing: tuple = ()
    refused: tuple = ()
    reason: str = ""


@dataclass(frozen=True)
class SeedOutcome:
    """What one scene entry took from the world's floor into a cell."""

    scene: str
    admitted: tuple = ()
    standing: int = 0
    reason: str = ""

    @property
    def seeded(self) -> bool:
        return not self.reason


@dataclass(frozen=True)
class PersistOutcome:
    """What one generation did to the durable door."""

    scene: str
    wrote: tuple = ()
    already_there: tuple = ()
    refused: tuple = ()
    reason: str = ""


class WorldGround:
    """WHICH ROWS ARE STANDING IN WHICH SCENE, for the whole process.

    Keyed by ``mob_loot.scene_key`` (case-folded), because ``bg0002`` and
    ``Bg0002`` are one scene everywhere else in this lane and a floor that
    disagreed would hide a player's own drop from them -- the failure way 1
    exists to end, arrived at from a third direction.

    Rows expire on the SAME lifetime a cell gives them and the sweep is lazy
    in the same way (read the clock when somebody touches this, never a
    thread): a row that outlived its 120 seconds while nobody was logged in
    must not be handed to the next login as if it were standing.  The clock is
    ``time.monotonic`` for the reason ``DropLedgerCell`` gives in its own
    words: a wall clock that steps backwards over an NTP correction freezes
    every deadline in the future.
    """

    def __init__(
        self,
        lifetime_seconds: Any = mob_loot.DROP_LIFETIME_SECONDS,
        clock: Any = None,
        rows_per_scene: int = ROWS_PER_SCENE_CAP,
    ) -> None:
        self._lifetime = float(lifetime_seconds)
        if not 0 < self._lifetime <= 3600.0:
            raise ValueError("a world lifetime is seconds, got %r"
                             % (lifetime_seconds,))
        self._clock = _time.monotonic if clock is None else clock
        if not callable(self._clock):
            raise ValueError("a clock must be callable")
        if not isinstance(rows_per_scene, int) or rows_per_scene < 1:
            raise ValueError("rows_per_scene must be a positive int")
        self._cap = rows_per_scene
        self._lock = threading.RLock()
        # scene key -> ordered {drop key: (GroundDrop, deadline)}.  Ordered
        # because the cap retires the OLDEST and insertion order is exactly
        # that order; a dict comprehension over it would lose the property the
        # cap is defined in terms of.
        self._floors: dict = {}
        # scene key -> the keys somebody has PICKED UP in this process, newest
        # last, bounded.  THE DUPLICATION GUARD, and it is what a shared floor
        # costs: once two sessions can be seeded from one floor, two
        # cells can hold one key, and each cell's own pickup transaction would
        # hand out its own copy of the item with nothing raised anywhere.  A
        # floor that merely FORGOT the row could not answer that, because
        # "never here" and "taken" would both read as absent -- so the take is
        # remembered on purpose.  Bounded like ``DropLedgerCell._expired``: the
        # structure that explains a refusal must not grow without bound.
        self._taken: dict = {}

    @property
    def lifetime_seconds(self) -> float:
        return self._lifetime

    def _sweep_locked(self, scene_fold: str, now: float) -> int:
        floor = self._floors.get(scene_fold)
        if not floor:
            return 0
        dead = [key for key, (_row, deadline) in floor.items()
                if deadline <= now]
        for key in dead:
            floor.pop(key, None)
        if not floor:
            self._floors.pop(scene_fold, None)
        return len(dead)

    def remember(self, drops: Any) -> tuple:
        """Put rows on the world's floor.  Returns ``(new, already, refused)``.

        A key this floor already carries is ``already``, never an overwrite: a
        re-announced generation (``sustain_a_kill`` composes the WHOLE live
        ledger every kill) must not restart another row's clock, or a floor
        that is being re-announced every few seconds never expires anything.
        """
        rows = tuple(drops)
        new, already, refused = [], [], []
        for row in rows:
            if type(row) is not mob_loot.GroundDrop:
                refused.append(row)
                continue
            fold = row.scene_key
            with self._lock:
                now = float(self._clock())
                self._sweep_locked(fold, now)
                floor = self._floors.setdefault(fold, collections.OrderedDict())
                if row.drop_key in floor:
                    already.append(row)
                    continue
                floor[row.drop_key] = (row, now + self._lifetime)
                while len(floor) > self._cap:
                    floor.popitem(last=False)
                new.append(row)
        return (tuple(new), tuple(already), tuple(refused))

    def standing(self, scene: Any) -> tuple:
        """The rows still on one scene's floor, oldest first.  Sweeps first."""
        fold = mob_loot.scene_key(scene)
        with self._lock:
            now = float(self._clock())
            self._sweep_locked(fold, now)
            floor = self._floors.get(fold)
            if not floor:
                return ()
            return tuple(row for row, _deadline in floor.values())

    def claim(self, scene: Any, drop_key: Any) -> Any:
        """ATOMICALLY take one row off the world's floor.  The authority.

        ROUND 59iqwi, pf-adversary D1: this replaces a ``forget`` that was
        called AFTER a pickup had already succeeded, which could not stop the
        second pickup of one row.  Once a floor is shared, one drop can sit in
        two sessions' cells, each cell is authority over its own ledger alone,
        and a memo posted after the fact is not a lock.  MEASURED, on the real
        roster: player A killed, player B was seeded from the floor and
        clicked first, and A -- whose own cell had minted the row -- was then
        handed a second copy of the same crystal.

        So the take is decided HERE, before either transaction runs, and
        exactly one caller can win: the row is removed and returned under this
        lock, and every later claimant gets ``None``.  ``None`` alone is NOT a
        refusal (see :meth:`was_taken`): a row this floor never held is
        somebody else's business and must still reach the cell's own rules.
        """
        fold = mob_loot.scene_key(scene)
        # Checked here rather than through ``mob_loot``'s own ``_require_int``:
        # that helper is private to that module, and a floor that reached into
        # it would be one rename away from a floor that stops forgetting rows
        # -- which is the direction that hands a player the same item twice.
        if type(drop_key) is not int or not 0 <= drop_key <= 0xFFFFFFFF:
            raise ValueError("a drop key is a u32, got %r" % (drop_key,))
        with self._lock:
            now = float(self._clock())
            self._sweep_locked(fold, now)
            floor = self._floors.get(fold)
            if not floor or drop_key not in floor:
                return None
            row, floor_deadline = floor.pop(drop_key)
            if not floor:
                self._floors.pop(fold, None)
            taken = self._taken.setdefault(fold, collections.OrderedDict())
            # THE ROW, NOT THE NUMBER, AND A DEADLINE ON TOP (pf-adversary D2
            # of pass 1, then MEASURED AGAIN by the full suite: 42 tests went
            # red because a record keyed by the NUMBER refuses a different
            # object that merely reuses it).  Keys are minted from
            # ``DROP_KEY_BASE`` by every fresh ledger, so one number names
            # many objects over a process's life.  What the guard has to
            # recognise is THE SAME OBJECT standing in two cells -- which is
            # exactly what identity answers, because a seeded cell is handed
            # the very row this floor holds (:meth:`standing` returns the
            # stored objects) and the killer's cell holds the one it minted
            # and handed here.  The deadline bounds it further: what it must
            # outlive is only the copies other cells may still hold, and every
            # such copy carries at most one full lifetime.
            # THE ROW'S OWN FLOOR DEADLINE IS CARRIED, not recomputed, so a
            # claim that is handed back cannot renew the object's life
            # (pf-adversary pass 2, D4, MEASURED: a claimant standing out of
            # range and clicking every 60 s kept one row standing for 99,960
            # seconds, because ``return_claim`` re-floored it at
            # ``now + lifetime`` every time.  ``DROP_LIFETIME_SECONDS`` has to
            # bound the world floor the way it bounds a cell's).
            taken[drop_key] = (row, now + 2.0 * self._lifetime, floor_deadline)
            while len(taken) > TAKEN_KEY_MEMORY:
                taken.popitem(last=False)
            return row

    def return_claim(self, row: Any) -> bool:
        """Put a claimed row back, ON ITS OWN REMAINING TIME.  Round 59iqwi.

        A claim is taken before the transaction, so a transaction that fails
        BEFORE the take would otherwise delete a row nobody picked up -- the
        floor would lose an object still lying in front of the player, and the
        taken record would then refuse the owner's own clicks for the rest of
        its life (pf-adversary pass 2, D3).

        WHAT IT MUST NOT DO IS EXTEND THE ROW'S LIFE (pass 2, D4).  The
        deadline the claim popped is carried in the taken record and restored
        here; a row whose deadline has passed while it was claimed is NOT
        re-floored, because it is expired and a floor that resurrects expired
        rows is the ghost this lane keeps paying for.  Refusals like
        ``claimant_out_of_range`` are ordinary -- R303 refused two of its four
        decoded clicks that way -- so "every refused click renews the object"
        is not a corner case, it is the common path.
        """
        if type(row) is not mob_loot.GroundDrop:
            return False
        fold = row.scene_key
        with self._lock:
            now = float(self._clock())
            held = self._taken.get(fold, {}).get(row.drop_key)
            deadline = None
            if held is not None and held[0] is row:
                deadline = held[2]
                self._taken[fold].pop(row.drop_key, None)
            if deadline is None or now >= deadline:
                # Either this row was never claimed from this floor (nothing
                # to give back) or it outlived its own deadline while the
                # transaction ran.  Both are refusals, and neither is an
                # error: the caller's own outcome already says what happened.
                return False
            floor = self._floors.setdefault(fold, collections.OrderedDict())
            if row.drop_key in floor:
                return False
            floor[row.drop_key] = (row, deadline)
            while len(floor) > self._cap:
                floor.popitem(last=False)
            return True

    def taken_row(self, scene: Any, drop_key: Any) -> Any:
        """The ROW a claim took off this floor under this key, or None.

        Bounded by count (``TAKEN_KEY_MEMORY``) and by TIME: an entry lives
        two drop lifetimes, which outlasts every copy of that row any cell can
        still be holding and nothing more.  Answers None for a key that merely
        EXPIRED and None for a key this floor never held -- both deliberate,
        because this is the evidence half of a refusal, and a guard that
        answered "maybe" refuses clicks on rows nobody ever took.

        Returning the ROW rather than a boolean is what lets the caller ask
        the only question that is actually about duplication: is the object in
        MY cell the object somebody else already carried away?
        """
        if type(drop_key) is not int:
            return None
        try:
            fold = mob_loot.scene_key(scene)
        except Exception:                                   # noqa: BLE001
            return None
        with self._lock:
            taken = self._taken.get(fold)
            if not taken or drop_key not in taken:
                return None
            row, deadline, _floor_deadline = taken[drop_key]
            if float(self._clock()) >= deadline:
                taken.pop(drop_key, None)
                return None
            return row

    def clear(self) -> None:
        """Forget every floor.  For a test fixture and for nothing else."""
        with self._lock:
            self._floors.clear()
            self._taken.clear()


_WORLD_LOCK = threading.Lock()
_WORLD: WorldGround | None = None


def world_ground() -> WorldGround:
    """The process's own floor.  Built on first use, never rebuilt."""
    global _WORLD
    with _WORLD_LOCK:
        if _WORLD is None:
            _WORLD = WorldGround()
        return _WORLD


def install_world_ground(world: Any) -> WorldGround:
    """Replace the process's floor.  A TEST SEAM, named as one.

    Every entry point below takes a ``world=`` argument for the same reason,
    so a test never has to reach for this; it exists for the case a test
    exercises a call site that does not pass one.  Returns the world it
    installed so a fixture can hold it.
    """
    global _WORLD
    if not isinstance(world, WorldGround):
        raise TypeError("a world floor is a WorldGround")
    with _WORLD_LOCK:
        _WORLD = world
        return _WORLD


def remember_generation(
    drops: Any, *, world: Any = None, store: Any = None,
) -> RememberOutcome:
    """A kill's rows enter the world.  NEVER RAISES.

    Called from ``mob_drop_presence.sustain_a_kill``, which sits under an
    inbound frame from a stranger by way of the death dispatch: an escape here
    would take the v141 listener thread down mid-kill, so every failure comes
    back as a name on the outcome instead (the same promise
    ``mob_pickup_request.dispatch_inbound_pickup_request`` makes at its own
    site, in its own words).

    ``store`` is optional and its absence is NOT a refusal of the whole call:
    the in-memory floor is what a relogin reads, and it is filled either way.
    When a store IS handed in, the same rows are offered to the durable door
    as well -- see :func:`persist_generation`.
    """
    try:
        rows = tuple(drops)
    except Exception:                                   # noqa: BLE001
        return RememberOutcome("", reason=REFUSE_ROW_IS_NOT_A_DROP)
    if not rows:
        return RememberOutcome("")
    try:
        floor = world if isinstance(world, WorldGround) else world_ground()
        new, already, refused = floor.remember(rows)
    except Exception as error:                          # noqa: BLE001
        return RememberOutcome("", reason="%s:%r" % (
            REFUSE_CELL_RAISED, error))
    scene = ""
    for row in rows:
        if type(row) is mob_loot.GroundDrop:
            scene = row.scene
            break
    if store is not None:
        # The durable half is REPORTED SEPARATELY and never folded into this
        # outcome's counts: a row that is on the world's floor and not in the
        # table is a different state from a row that is in neither, and a
        # caller that prints one number for both cannot tell an operator which
        # one they have.
        persist_generation(store, rows)
    return RememberOutcome(scene, tuple(new), tuple(already), tuple(refused))


def describe_remembered(outcome: RememberOutcome) -> str:
    """One bounded ASCII console line.  G-OBS."""
    if outcome.reason:
        return "%s scene=%r refused reason=%s" % (
            WORLD_REMEMBERED_TOKEN, outcome.scene, outcome.reason)
    return (
        "%s scene=%r new=%d already_standing=%d refused=%d keys=%s"
        % (
            WORLD_REMEMBERED_TOKEN, outcome.scene, len(outcome.remembered),
            len(outcome.already_standing), len(outcome.refused),
            ",".join("0x%X" % row.drop_key for row in outcome.remembered)
            or "none",
        )
    )


@dataclass(frozen=True)
class ClaimOutcome:
    """What the world said when a click reached for one of its rows."""

    scene: str
    row: Any = None
    refused: bool = False
    reason: str = ""

    @property
    def claimed(self) -> bool:
        return self.row is not None


def claim_for_pickup(
    cell: Any, drop_key: Any, *, world: Any = None,
) -> ClaimOutcome:
    """Decide the take in ONE place, before either cell's transaction.  NEVER RAISES.

    THE AUTHORITY QUESTION, ANSWERED (pf-adversary D1 of this round, which
    measured one drop becoming two items).  Once a scene's floor is shared,
    two sessions can hold one row and each cell is authority over its own
    ledger alone.  So the click asks the WORLD first:

      * the world held the row and hands it over -> this caller won, and no
        other caller can win it now.  Proceed to the transaction.
      * the world does not hold it AND remembers it being claimed recently ->
        somebody else won.  ``refused`` -- this is the second click on one
        object, and it is the only case that is refused.
      * the world does not hold it and does not remember it -> the world has
        no opinion (a cell built before this feature, a row the floor swept
        while a seeded cell still draws it).  NOT refused: the cell's own
        rules answer, exactly as they did before this round.

    Note which case the KILLER is in: ``remember_generation`` puts a kill's
    rows on the floor at the moment they drop, so the player who made the drop
    claims it from the world like everybody else.  That is the fix for D1 --
    the earlier guard asked whether the row had been readmitted, which is the
    one question that excludes the session most likely to hold the other copy.
    """
    scene = getattr(cell, "current_scene", None)
    try:
        floor = world if isinstance(world, WorldGround) else world_ground()
        row = floor.claim(scene, drop_key)
    except Exception:                                   # noqa: BLE001
        return ClaimOutcome("", None, False, REFUSE_CELL_RAISED)
    if row is not None:
        return ClaimOutcome(row.scene_key, row)
    try:
        gone = floor.taken_row(scene, drop_key)
        if gone is not None and any(
                held is gone for held in cell.ledger.drops):
            # IDENTITY, NOT EQUALITY, AND NOT THE KEY.  The object standing in
            # this cell is the object another claimant carried away: a seeded
            # cell is handed the floor's own row and the killer's cell handed
            # that row to the floor, so the two sessions really do hold ONE
            # python object.  A different drop that merely reuses the number
            # -- which every fresh ledger produces, since keys are minted per
            # session from ``DROP_KEY_BASE`` -- is a different object and is
            # not refused here.
            return ClaimOutcome(
                gone.scene_key, None, True, REFUSE_TAKEN_BY_ANOTHER_SESSION)
    except Exception:                                   # noqa: BLE001
        return ClaimOutcome("", None, False, REFUSE_CELL_RAISED)
    return ClaimOutcome("", None, False, "")


def return_claim(outcome: Any, *, world: Any = None) -> bool:
    """Give a claimed row back to the world.  For a pickup that then refused.

    NEVER RAISES.  A claim is taken before the transaction; a transaction that
    refuses afterwards must not leave the floor short an object that is still
    lying in front of the player.
    """
    row = getattr(outcome, "row", None)
    if row is None:
        return False
    try:
        floor = world if isinstance(world, WorldGround) else world_ground()
        return floor.return_claim(row)
    except Exception:                                   # noqa: BLE001
        return False


def note_taken_in_the_durable_door(
    row: Any, *, store: Any = None,
) -> bool:
    """Mark a claimed row taken in the table, when that door exists.  NEVER RAISES.

    BEST EFFORT, and the asymmetry is the reason: a marker that did not land
    makes a row come back after a server restart, while raising here would
    break a pickup that has already succeeded.  Absent the marker method (the
    state of `SQLiteStore` today) this is a no-op -- and the restore half is
    refused by name for the same absence, so nothing reads what nothing marks.
    """
    if store is None or type(row) is not mob_loot.GroundDrop:
        return False
    mark = getattr(store, TAKEN_DOOR_METHOD, None)
    if not callable(mark):
        return False
    try:
        mark(scene=row.scene_key, drop_key=row.drop_key)
    except Exception:                                   # noqa: BLE001
        return False
    return True


def seed_cell(cell: Any, scene: Any = None, *, world: Any = None) -> SeedOutcome:
    """Give a session's cell the rows the world says are standing.  NEVER RAISES.

    THIS IS THE SEAM R309 NEEDS.  Call it where a session learns which scene
    its player is standing in -- the arrival census on a fresh login, and the
    boundary resync on a warp -- and a player who logs back in sees the floor
    they left.  Calling it twice for one scene is a no-op the second time
    (:meth:`mob_loot.DropLedgerCell.admit_standing_rows` skips keys the cell
    already holds), so a caller may be generous with it.

    ``scene`` may be omitted for a cell that already knows its own; a cell
    that knows no scene and was given none is refused by name rather than
    seeded with a guess -- "every row this process holds" is the cross-scene
    leak this lane refuses everywhere else.
    """
    if not isinstance(cell, mob_loot.DropLedgerCell):
        return SeedOutcome("", reason=REFUSE_NOT_A_CELL)
    if scene is None:
        scene = getattr(cell, "current_scene", None)
        if scene is None:
            return SeedOutcome("", reason=REFUSE_CELL_HAS_NO_SCENE)
    try:
        fold = mob_loot.scene_key(scene)
    except Exception:                                   # noqa: BLE001
        return SeedOutcome("", reason=REFUSE_SCENE_IS_UNREADABLE)
    try:
        floor = world if isinstance(world, WorldGround) else world_ground()
        standing = floor.standing(fold)
    except Exception as error:                          # noqa: BLE001
        return SeedOutcome(fold, reason="%s:%r" % (REFUSE_DOOR_RAISED, error))
    if not standing:
        return SeedOutcome(fold, (), 0)
    try:
        admitted = cell.admit_standing_rows(standing)
    except mob_loot.MobLootContractError as error:
        return SeedOutcome(fold, (), len(standing), reason=str(error.args[0]))
    except Exception as error:                          # noqa: BLE001
        return SeedOutcome(fold, (), len(standing),
                           reason="%s:%r" % (REFUSE_CELL_RAISED, error))
    return SeedOutcome(fold, tuple(admitted), len(standing))


def describe_seeded(outcome: SeedOutcome) -> str:
    """One bounded ASCII console line.  G-OBS."""
    if outcome.reason:
        return "%s scene=%r standing=%d reason=%s" % (
            WORLD_SEED_REFUSED_TOKEN, outcome.scene, outcome.standing,
            outcome.reason)
    return "%s scene=%r admitted=%d standing=%d keys=%s" % (
        WORLD_SEEDED_TOKEN, outcome.scene, len(outcome.admitted),
        outcome.standing,
        ",".join("0x%X" % row.drop_key for row in outcome.admitted) or "none",
    )


def persist_generation(store: Any, drops: Any) -> PersistOutcome:
    """Offer a generation to the durable door.  NEVER RAISES.

    The call site `COO-DECISION 2026-09-03T18:44+07:00` gives this lane for
    `SQLiteStore.commit_ground_drop`.  Every row is offered to the door and
    the DOOR decides -- ~~this function used to read the scene's rows back
    first and skip the keys already there~~ STRUCK, pf-adversary D5 of this
    round, MEASURED: that pre-read turned point 4 of `COO-DECISION
    2026-09-03T18:43+07:00` -- "two issuers minting one key must be refused by
    the database itself, loudly" -- into the quiet counter ``already_there``,
    and, because `list_ground_drops_for_scene` returns every row EVER
    committed, it made the table stop accepting the low keys entirely after
    the first server restart (a fresh ledger issues from ``DROP_KEY_BASE``
    again).  It also cost a full scan of an unbounded table per kill on the
    listener thread.  The caller hands this ONE KILL'S new rows, never a
    re-announced floor, so there was no re-announcement to protect.

    A row the door refuses is COUNTED AND NAMED, never retried and never
    raised: a floor that cannot be written down is a worse day than yesterday
    only for a server restart, while an exception on this path would cost the
    player the kill they are standing over.
    """
    rows = tuple(row for row in tuple(drops)
                 if type(row) is mob_loot.GroundDrop)
    if not rows:
        return PersistOutcome("")
    scene = rows[0].scene
    if store is None:
        return PersistOutcome(scene, reason=REFUSE_STORE_CANNOT_BE_ASKED)
    commit = getattr(store, "commit_ground_drop", None)
    if not callable(commit):
        return PersistOutcome(scene, reason=REFUSE_WRITE_DOOR_IS_ABSENT)
    wrote, already, refused = [], [], []
    for row in rows:
        try:
            commit(
                scene=row.scene, drop_key=row.drop_key, item_id=row.item_id,
                quantity=row.quantity, x=row.x, y=row.y, z=row.z,
                mob_identity=row.mob_identity,
                killer_identity=row.killer_identity,
            )
        except Exception:                               # noqa: BLE001
            # Including the collision the table exists to make loud: it has
            # already printed ``GROUND_DROP_KEY_COLLISION_REFUSED`` by the
            # time it reaches here, and this counts it rather than swallowing
            # it into a benign-sounding "already there".
            refused.append(row)
            continue
        wrote.append(row)
    return PersistOutcome(scene, tuple(wrote), tuple(already), tuple(refused))


def describe_persisted(outcome: PersistOutcome) -> str:
    """One bounded ASCII console line.  G-OBS."""
    if outcome.reason:
        return "%s scene=%r reason=%s" % (
            DB_PERSIST_REFUSED_TOKEN, outcome.scene, outcome.reason)
    return "%s scene=%r wrote=%d already_there=%d refused=%d" % (
        DB_PERSIST_TOKEN, outcome.scene, len(outcome.wrote),
        len(outcome.already_there), len(outcome.refused))


def restore_door_is_open(store: Any) -> bool:
    """Can the durable door say what is STILL on the ground?  Today: no.

    Probed by method name, so the day LANE-DB lands the `taken` marker this
    answers True with no edit here and :func:`restore_scene_ground` starts
    working.  See the module docstring for why a restore without it would be
    item duplication rather than persistence.
    """
    return (
        callable(getattr(store, TAKEN_DOOR_METHOD, None))
        and callable(getattr(store, STANDING_DOOR_METHOD, None))
    )


def restore_scene_ground(store: Any, scene: Any, *, world: Any = None) -> str:
    """Put a scene's durable floor back into the world.  NEVER RAISES.

    Returns ``""`` when it restored, and a refusal NAME otherwise -- today
    always :data:`REFUSE_TAKEN_DOOR_IS_ABSENT` on a real ``SQLiteStore``.

    ~~"the write side above is live and filling the table now, so the day the
    marker lands there is a floor to restore FROM"~~ IS STRUCK, pf-adversary
    pass 2 D6, MEASURED: ``runtime.py``'s kill site calls ``sustain_a_kill``
    WITHOUT a ``store=``, so :func:`persist_generation` has no production
    caller and ``ground_drops`` is empty on a running server.  The write side
    is wired on THIS side of the seam and waiting for one keyword at chief's
    call site (`pf_bridge/notes_to_chief/20260904_1652` item 3).  Saying
    otherwise here while ``sustain_a_kill``'s own docstring said "absent, the
    floor is memory only" left two files in one lane disagreeing about one
    fact.

    A SECOND THING THIS HALF WILL BREAK ON THE DAY IT WORKS, named here
    because it is the design question pass 2 ended on: rows rebuilt from the
    table are NEW objects, and the duplication guard recognises a shared row
    by IDENTITY (``held is gone``).  A floor restored from the database is
    therefore invisible to that guard.  Whatever lands the marker has to land
    an object identity that survives a process too -- the drop key issued
    server-wide, not per session.
    """
    if store is None:
        return REFUSE_STORE_CANNOT_BE_ASKED
    if not restore_door_is_open(store):
        return REFUSE_TAKEN_DOOR_IS_ABSENT
    try:
        rows = getattr(store, STANDING_DOOR_METHOD)(mob_loot.scene_key(scene))
    except Exception as error:                          # noqa: BLE001
        return "%s:%r" % (REFUSE_DOOR_RAISED, error)
    drops = []
    for row in rows:
        try:
            drops.append(mob_loot.GroundDrop(
                drop_key=row.drop_key, item_id=row.item_id,
                quantity=row.quantity, x=row.x, y=row.y, z=row.z,
                mob_identity=row.mob_identity,
                killer_identity=row.killer_identity, scene=row.scene,
            ))
        except Exception:                               # noqa: BLE001
            # A row the in-memory contract refuses (an item no longer in the
            # mined table, a position off the f32 grid) is DROPPED rather than
            # repaired: the alternative is a floor whose rows cannot be
            # published, which reads to a player as a click that never works.
            continue
    if not drops:
        return ""
    floor = world if isinstance(world, WorldGround) else world_ground()
    floor.remember(tuple(drops))
    return ""
