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

THE RULING THAT NAMED THIS FEATURE BEFORE COO-DECISION 20260905_1152 DID,
and it must be read beside it rather than instead of it.  ``runtime.py``
(the docstring of the scene-edge resync) records ``COO-DECISION
20260903_2245``: a wound register parallel to the death one was ratified as
a real, queued feature, ruled **LANE-B's**, and given its seam -- "it plugs
in HERE, at the same seam, AFTER the death rehydrate in
``_sync_combat_scene_state`` -- not at another call site".  This module IS
that wound register, and it is LANE-A's because ``COO-DECISION
20260905_1152`` (two days later, under ``PANYA-DECISION 1140``) put the
whole per-scene world registry in this lane's hands with LANE-B writing
into it.  THE SEAM OF 2245 IS TAKEN UNCHANGED -- plus ONE statement 2245 did
not name (a once-per-session seed at login), because that ruling's seam alone
never runs for a character whose stored scene is the scene the process booted
into, which is the town this game starts in.  Only the owner moved.  If
COO reads the two rulings the other way, nothing in this file changes but
the lane tag at the top -- and the round's letter puts that question in
front of COO rather than deciding it here.  Round trips healing a wound is
the behaviour 2245 ratified as today's correct one; this is the change that
ends it, not a claim it was a bug all along.

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

#: A scene cannot hold more remembered vitals than this.  This is process
#: memory with no eviction clock on it, and a caller in a loop must hit a
#: named refusal rather than grow the dictionary until the box stops.  4096
#: is far above the largest roster this project has mined (bg0001, 115
#: placements) and far below anything that costs real memory.
VITALS_PER_SCENE_CAP = 4096

#: And a bound on how many SCENES may be remembered at once, because the
#: per-scene cap alone is not a bound on the book -- pf-adversary (round
#: ``tz2rgc``) measured the first draft holding 20,000 fabricated scene keys
#: without a single refusal, under a comment claiming the cap prevented
#: exactly that.  128 is well above this game's mined scene count (the
#: identity modules ship six live rosters today, the folder copy names a few
#: hundred) and it refuses by name rather than growing.
#:
#: !! WHAT IS DELIBERATELY *NOT* HERE, and it is a real bound on this book:
#: ``WorldDeaths.bury`` gates every row through ``roster_key_of`` -- a grave
#: for an identity no mined table ships is refused, because such a row seeds
#: a later login with a monster ``mob_death.repopulation_entries`` will
#: reject.  This book has NO roster gate: it will remember a diag object's
#: identity (``0x4329``) as happily as a mined one.  It is not reachable as
#: a crash today (the seed writes only into identities the destination
#: ledger already carries, so an unmined row can never leave this book) --
#: but a future reader must not mistake the two books for equals here.
SCENES_CAP = 128

#: A scene cannot hold more remembered OTHER PLAYERS than this, for the same
#: reason ``VITALS_PER_SCENE_CAP`` exists: this is process memory with no
#: eviction clock, and a caller in a loop must hit a named refusal rather
#: than grow the dictionary until the box stops.  256 is far above any
#: concurrent roster this project has ever measured in one scene and far
#: below anything that costs real memory.
PLAYERS_PER_SCENE_CAP = 256

#: Named refusals.  A caller reads these; nothing here is a bare False.
REFUSE_A_GRAVE_IS_NOT_A_VITAL = "a_grave_is_not_a_vital"
REFUSE_BAD_SCENE = "bad_scene"
REFUSE_BAD_IDENTITY = "bad_identity"
REFUSE_BAD_HP = "bad_hp"
REFUSE_BAD_POSITION = "bad_position"
REFUSE_BAD_NAME = "bad_name"
REFUSE_SCENE_IS_FULL = "scene_is_full"
REFUSE_TOO_MANY_PLAYERS_IN_SCENE = "too_many_players_in_scene"
REFUSE_NOT_A_LEDGER = "not_a_ledger"
REFUSE_ANOTHER_SCENES_LEDGER = "another_scenes_ledger"
REFUSE_LEDGER_REFUSED_THE_ROW = "ledger_refused_the_row"
REFUSE_TOO_MANY_SCENES = "too_many_scenes"

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


def _require_player_name(name: Any) -> str:
    """The same name check ``remote_player_hypothesis._require_probe_name``
    already proved: non-empty ``str``, UTF-16LE encodable (the wire's own
    string encoding, ``PcBinary::wstring`` tag 0x48), even byte length."""
    if type(name) is not str or not name:
        raise ValueError("a player name must be a non-empty str")
    try:
        raw = name.encode("utf-16le")
    except UnicodeEncodeError as exc:
        raise ValueError("a player name must be utf-16le encodable") from exc
    if len(raw) % 2:
        raise ValueError("a player name must be utf-16le encodable")
    return name


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
class PlayerVital:
    """What the world remembers about one OTHER PLAYER standing in a scene
    right now -- the roster half of ``PANYA-DECISION 20260905_1140`` (this
    module's own docstring quotes it for the monster half: "roster and
    monster positions ... lives in the SERVER PROCESS'S MEMORY and is SHARED
    BY EVERY SESSION STANDING IN THAT SCENE").  ``COO-DECISION 20260906_1147``
    is what asks for the roster half to be filled in.

    UNLIKE ``MobVital``, every field is required rather than optional: a
    player worth remembering here is always standing somewhere with a name
    and a current health, because a caller only reaches this door once it
    already has all three (see ``world_remote_player_actor`` for the reader
    this row exists to feed).
    """

    actor_identity: int
    name: str
    current_hp: int
    max_hp: int
    position: tuple[float, float, float]

    def __post_init__(self) -> None:
        _require_identity(self.actor_identity)
        _require_player_name(self.name)
        _require_hp(self.current_hp, "current hp")
        _require_hp(self.max_hp, "max hp")
        if self.current_hp > self.max_hp:
            raise ValueError("current hp is above max hp")
        if self.current_hp < 1:
            # The same floor remote_player_hypothesis.py measured and named
            # (its own REMOTE_PLAYER_HP_MIN comment): 0x4446F0 calls the
            # dead-state sync 0x4437C0 on every update-path frame once
            # BasicAttr +0x44 == 0, so a remembered player at zero health
            # would walk any session that re-sends this row into the death
            # chain on its very next resend.  A dead player's own session
            # already has its own dying/death path; this book is not where
            # that number goes -- the same reasoning ``REFUSE_A_GRAVE_IS_
            # NOT_A_VITAL`` applies to a monster, restated for a player.
            raise ValueError("a player below 1 hp is not a vital")
        _require_position(self.position)


@dataclass(frozen=True)
class PlayerNoteOutcome:
    """What one player-presence write did.  Mirrors ``NoteOutcome`` exactly,
    with its own type so a player row and a monster row can never be
    confused by a caller that only checked ``isinstance(..., NoteOutcome)``.
    ``reason`` empty means it landed."""

    scene: str
    actor_identity: int | None
    reason: str = ""
    remembered: "PlayerVital | None" = None

    @property
    def noted(self) -> bool:
        return not self.reason


@dataclass(frozen=True)
class SceneWorldView:
    """One scene's whole world, as one immutable answer.

    THE POINT OF THIS TYPE.  ``COO-DECISION 20260905_1152`` item 2(2) asks
    for a registry a caller can ask "what does scene N look like right now"
    and get ground, graves and monsters from ONE place.  The three books stay
    where they are; this is the single reading of them.  ``players`` is the
    fourth book this same question needs an answer for, added under
    ``COO-DECISION 20260906_1147``.
    """

    scene: str
    mobs: tuple[MobVital, ...] = ()
    graves: tuple[Any, ...] = ()
    ground: tuple[Any, ...] = ()
    players: tuple[PlayerVital, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not (self.mobs or self.graves or self.ground or self.players)


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

    def __init__(self, vitals_per_scene: int = VITALS_PER_SCENE_CAP,
                 scenes: int = SCENES_CAP,
                 players_per_scene: int = PLAYERS_PER_SCENE_CAP) -> None:
        if (type(vitals_per_scene) is bool
                or not isinstance(vitals_per_scene, int)
                or vitals_per_scene < 1):
            raise ValueError("vitals_per_scene must be a positive int")
        if (type(scenes) is bool or not isinstance(scenes, int)
                or scenes < 1):
            raise ValueError("scenes must be a positive int")
        if (type(players_per_scene) is bool
                or not isinstance(players_per_scene, int)
                or players_per_scene < 1):
            raise ValueError("players_per_scene must be a positive int")
        self._cap = vitals_per_scene
        self._scenes_cap = scenes
        self._players_cap = players_per_scene
        self._lock = threading.RLock()
        # scene key -> {actor identity: MobVital}
        self._scenes: dict = {}
        # scene key -> {actor identity: PlayerVital}.  A SEPARATE dict from
        # ``_scenes`` on purpose: a monster identity and a player identity
        # are drawn from disjoint bands everywhere else in this project
        # (``NPC_IDENTITY_BAND_BASE``/``CHARACTER_IDENTITY_FLOOR`` in
        # ``remote_player_hypothesis.py``), but this book does not assume
        # that -- sharing one dict would let a caller's bug on one door
        # silently overwrite the other door's row for the same identity.
        self._players: dict = {}

    @property
    def vitals_per_scene(self) -> int:
        return self._cap

    @property
    def players_per_scene(self) -> int:
        return self._players_cap

    def _scene_count(self) -> int:
        """Scenes remembered by EITHER book -- the true shared bound.

        `_scenes` (monsters) and `_players` are separate dicts (see the
        `__init__` comment on why), so counting only one of them under-counts
        the process's real scene footprint: a scene with players but no
        monsters noted yet would be invisible to a check that only looked at
        `_scenes`, letting the process remember up to `2 * scenes_cap`
        distinct scene keys instead of the one bound both doors claim to
        share.  pf-adversary caught this live in round 6bpbe3 (scenes=1
        accepted a second, distinct scene key through the player door).
        """
        return len(self._scenes.keys() | self._players.keys())

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

    def note_player(self, scene: Any, actor_identity: Any, name: Any,
                    current_hp: Any, max_hp: Any,
                    position: Any) -> PlayerNoteOutcome:
        """Remember one OTHER PLAYER standing in ``scene`` right now, so a
        second session (or the same character reading back its own arrival)
        can be told about them.  Never raises.

        THE CALL SITE THIS IS FOR: wherever a session confirms a character's
        identity/name/health/position for a scene it is already reading the
        mob/ground/grave books of -- the login seed and the movement report,
        the same shape ``WORLD_REGISTRY_SEED_WIRING`` already asks chief for
        on the monster side.  See ``world_remote_player_actor.
        PLAYER_PRESENCE_WIRING`` for the pasteable ask this door still needs.
        """
        try:
            fold = _scene_key(scene)
        except Exception:                                    # noqa: BLE001
            return PlayerNoteOutcome("", None, REFUSE_BAD_SCENE)
        try:
            identity = _require_identity(actor_identity)
        except Exception:                                    # noqa: BLE001
            return PlayerNoteOutcome(fold, None, REFUSE_BAD_IDENTITY)
        try:
            safe_name = _require_player_name(name)
        except Exception:                                    # noqa: BLE001
            return PlayerNoteOutcome(fold, identity, REFUSE_BAD_NAME)
        try:
            current = _require_hp(current_hp, "current hp")
            ceiling = _require_hp(max_hp, "max hp")
        except Exception:                                    # noqa: BLE001
            return PlayerNoteOutcome(fold, identity, REFUSE_BAD_HP)
        if current > ceiling or current < 1:
            return PlayerNoteOutcome(fold, identity, REFUSE_BAD_HP)
        try:
            where = _require_position(position)
        except Exception:                                    # noqa: BLE001
            return PlayerNoteOutcome(fold, identity, REFUSE_BAD_POSITION)
        with self._lock:
            rows = self._players.get(fold)
            if rows is None:
                if fold not in self._scenes and (
                        self._scene_count() >= self._scenes_cap):
                    # Same scene cap the monster book is held to -- one
                    # bound on how many SCENES this process remembers
                    # anything about at all, shared across both books
                    # (checked against their UNION, see `_scene_count`).
                    return PlayerNoteOutcome(
                        fold, identity, REFUSE_TOO_MANY_SCENES)
                rows = self._players.setdefault(fold, {})
            standing = rows.get(identity)
            if standing is None and len(rows) >= self._players_cap:
                return PlayerNoteOutcome(
                    fold, identity, REFUSE_TOO_MANY_PLAYERS_IN_SCENE)
            try:
                row = PlayerVital(identity, safe_name, current, ceiling, where)
            except Exception:                                # noqa: BLE001
                # Unreachable through this public door (every field is
                # validated above); kept because PlayerVital's own rules can
                # outgrow this door's, and this door must never raise.
                return PlayerNoteOutcome(fold, identity, REFUSE_BAD_HP)
            rows[identity] = row
            return PlayerNoteOutcome(fold, identity, "", row)

    def forget_player(self, scene: Any, actor_identity: Any) -> bool:
        """THE LOGOUT/SCENE-DEPARTURE DOOR.  True when a row was actually
        held.  Same shape as :meth:`forget`, for the same reason: the round
        that wires disconnect/scene-change must have one way to say "this
        player is no longer here" that is a removal, never a clear."""
        try:
            fold = _scene_key(scene)
            identity = _require_identity(actor_identity)
        except Exception:                                    # noqa: BLE001
            return False
        with self._lock:
            rows = self._players.get(fold)
            if not rows or identity not in rows:
                return False
            rows.pop(identity, None)
            if not rows:
                self._players.pop(fold, None)
            return True

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
        """Empty both books.  A TEST SEAM, and named as one."""
        with self._lock:
            self._scenes.clear()
            self._players.clear()

    def _write(self, fold: str, identity: int, current: Any, ceiling: Any,
               position: Any) -> NoteOutcome:
        """Merge one field-set into the row, under the lock.

        ``_KEEP`` means "leave whatever is already remembered", which is what
        makes a position write and a health write independent without a
        read-modify-write the caller could lose a race on.
        """
        with self._lock:
            rows = self._scenes.get(fold)
            if rows is None:
                if fold not in self._players and (
                        self._scene_count() >= self._scenes_cap):
                    # A NEW scene when the book is full is refused; every
                    # scene already remembered keeps working.  Refusing the
                    # scene rather than clearing one is the same choice
                    # `WorldDeaths` makes at its own cap: a world that
                    # forgets a scene a player is standing in is worse than
                    # one that refuses to learn a new one.
                    return NoteOutcome(fold, identity, REFUSE_TOO_MANY_SCENES)
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

    def remembered_players(self, scene: Any) -> tuple[PlayerVital, ...]:
        """One scene's remembered OTHER PLAYERS, by identity.  Never raises."""
        try:
            fold = _scene_key(scene)
        except Exception:                                    # noqa: BLE001
            return ()
        with self._lock:
            rows = self._players.get(fold)
            if not rows:
                return ()
            return tuple(rows[key] for key in sorted(rows))

    def scenes(self) -> tuple[str, ...]:
        """Every scene this process has remembered anything about.

        The union of both books -- a scene with only players noted (no
        monster has ever been hit or placed there yet) is still a scene this
        process remembers, and `_scene_count`'s cap check depends on this
        method and the cap agreeing on what "remembered" means.
        """
        with self._lock:
            return tuple(sorted(self._scenes.keys() | self._players.keys()))


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
    try:
        players = book.remembered_players(fold)
    except Exception:                                        # noqa: BLE001
        players = ()
    return SceneWorldView(fold, mobs, graves, rows, players)


def seed_the_session_ledger(ledger: Any, scene: Any, *, registry: Any = None,
                            deaths: Any = None, announce: bool = True):
    """THE CALL SITE.  Fill a fresh session ledger from the world's memory.

    ``self.mob_combat_ledger = world_scene_registry.seed_the_session_ledger(
        self.mob_combat_ledger, folder)``

    !! WHERE IT MAY BE CALLED: wherever a ledger is OPENED -- after a scene
    change, and once at login -- and NOWHERE ELSE.  It is a seed, not an
    authority: a caller that re-runs it on every dispatch pushes the book's
    value back over blows this session has already landed, which
    pf-adversary (round ``tz2rgc``, N1) measured as 2,218 of 6,000 damage
    lost between two players on one monster.  See
    :data:`WORLD_REGISTRY_SEED_WIRING`.

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
    * A LEDGER OPEN ON A DIFFERENT SCENE, whole and by name, before any row
      is considered.  THIS IS THE FIRST CHECK AND IT IS NOT A BELT: the
      first draft of this function had only the identity check below, on the
      stated ground that "a ledger open on the scene being LEFT holds none
      of the destination's rows", and pf-adversary (round ``tz2rgc``)
      MEASURED that sentence false on this game's own tables -- ``field_
      mobs`` identities are ``0x2000 + placement + 1`` with no scene term,
      so eight of the fifteen live-scene pairs share at least one wire
      identity (re-derived from `field_mobs.load_roster` over
      `live_scenes()` at this round's HEAD -- the "nine" an earlier draft
      of this comment carried was copied from a report and never re-run).  A Bg0003 ledger was rewritten with bg0004's memory of
      ``0x2046``: 12 HP out of one scene's monster under the other's
      ceiling, printed as a green seed.  ``CombatLedger.scene`` exists to
      answer exactly this question and now it is asked.
    * an identity the ledger does not carry -- kept as the second belt for
      the case the scenes DO match and the roster has since shrunk.
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
    try:
        ledger_fold = _scene_key(ledger.scene)
    except Exception:                                        # noqa: BLE001
        # A ledger with no scene tag on it cannot be proved to be this
        # scene's, and "cannot prove" is a refusal here rather than a
        # default: the defect this check exists for wrote one scene's
        # monster into another scene's ledger and printed a green line.
        ledger_fold = None
    if ledger_fold != fold:
        outcome = SeedOutcome(fold, ledger, (), 0, REFUSE_ANOTHER_SCENES_LEDGER)
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
    except Exception as error:                               # noqa: BLE001
        # THE REASON CARRIES THE ERROR, the way ``mob_death_persistence``'s
        # own refusal does.  pf-adversary (round ``tz2rgc``) measured the
        # first draft reporting a raising grave book, a ``MemoryError`` out
        # of ``with_balance`` and a broken ``identities()`` under one
        # borrowed name -- "above the ledger ceiling" -- which sends whoever
        # greps it to the mob tables for a fault that was never there.
        # THROUGH ``_clamp`` AND NOT ``%r``: the same review measured a raw
        # repr putting a five-million-character line, a non-cp874 character
        # (which made the bridge console drop the WHOLE refusal line), and
        # an exception whose own ``__repr__`` raises -- straight through the
        # one line that says why the world was not seeded.
        outcome = SeedOutcome(
            fold, ledger, (), skipped,
            "%s:%s" % (REFUSE_LEDGER_REFUSED_THE_ROW, _clamp(error)))
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


def describe_noted_player(outcome: Any) -> str:
    """One bounded ASCII console line for a player-presence write.  Mirrors
    :func:`describe_noted` exactly, for the player book.  Never raises."""
    try:
        if outcome.noted:
            row = outcome.remembered
            hp = ("hp=none" if row is None
                  else "hp=%d/%d" % (row.current_hp, row.max_hp))
            where = ("pos=none" if row is None
                     else "pos=%.1f,%.1f,%.1f" % row.position)
            return ("WORLD_REGISTRY_PLAYER_NOTED scene=%s id=0x%X %s %s"
                    % (outcome.scene, outcome.actor_identity, hp, where))
        return ("WORLD_REGISTRY_PLAYER_REFUSED scene=%s id=%s reason=%s"
                % (outcome.scene,
                   "none" if outcome.actor_identity is None
                   else "0x%X" % outcome.actor_identity,
                   outcome.reason))
    except Exception:                                        # noqa: BLE001
        return "WORLD_REGISTRY_PLAYER_REFUSED scene=? id=? reason=undescribable"


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
                " players=%d"
                % (scene_view.scene, len(scene_view.mobs),
                   len(scene_view.graves), len(scene_view.ground),
                   len(scene_view.players)))
    except Exception:                                        # noqa: BLE001
        return (
            "WORLD_REGISTRY_VIEW scene=? monsters=? graves=? ground=? "
            "players=?"
        )


def _clamp(error: Any) -> str:
    """One short, ASCII, never-raising description of an exception.

    Three separate scars in one helper, all measured by pf-adversary in
    round ``tz2rgc`` against a raw ``%r``: a repr can be megabytes long, it
    can carry characters cp874 has no mapping for (which makes ``print``
    raise and the console lose the ENTIRE refusal line, so the one line that
    says why becomes silence), and it can raise on its own.
    """
    try:
        text = repr(error)
    except Exception:                                        # noqa: BLE001
        try:
            text = type(error).__name__
        except Exception:                                    # noqa: BLE001
            return "unreprable"
    try:
        text = text[:120].encode("ascii", "replace").decode("ascii")
    except Exception:                                        # noqa: BLE001
        return "unreprable"
    return text.replace("\n", " ").replace("\r", " ")


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
    "TWO STATEMENTS, in runtime.py's `_sync_combat_scene_state`, and the\n"
    "reason there are two is measured rather than defensive (pf-adversary,\n"
    "round tz2rgc, D3).  This ask does NOT depend on anything else being\n"
    "wired first: as of this round runtime.py contains NO\n"
    "`seed_the_session_state` call and does not import\n"
    "`mob_death_persistence` at all (`grep -c` = 0 for both), so an earlier\n"
    "draft of this note that told chief to paste 'after the existing death\n"
    "seed' was pointing at a line that does not exist.\n"
    "\n"
    "(1) INSIDE `if folder != self.mob_combat_scene_folder:`, immediately\n"
    "    after the `for record in respawned.records:` loop\n"
    "    (chief's round fyrtvt, CORE-REQUEST 20260905_1952, renamed this\n"
    "    loop's iterable from `self.mob_death_register.records` -- the\n"
    "    grave rehydrate is unchanged, only the variable is)\n"
    "    that rehydrates the graves, and BEFORE `register =\n"
    "    mob_ai_control.open_register(roster, epoch=0)`.  On the LOCAL:\n"
    "\n"
    "        ledger = world_scene_registry.seed_the_session_ledger(\n"
    "            ledger, folder)\n"
    "\n"
    "    THE LOCAL, NOT `self.`, is load-bearing: the three fields below it\n"
    "    (ledger, mob_ai_register, mob_combat_scene_folder) are assigned\n"
    "    together on purpose so that a raise out of `open_register` cannot\n"
    "    leave them on two different scenes (pf-adversary, round pk14rf,\n"
    "    quoted in runtime.py's own comment).  A statement writing `self.\n"
    "    mob_combat_ledger` above that trio would break exactly the\n"
    "    property the trio exists to hold.\n"
    "\n"
    "    THIS IS THE SEAM COO-DECISION 20260903_2245 ALREADY NAMED for a\n"
    "    wound register: 'it plugs in HERE, at the same seam, AFTER the\n"
    "    death rehydrate in _sync_combat_scene_state -- not at another call\n"
    "    site' (runtime.py's own words).  That ruling assigned the feature\n"
    "    to LANE-B; COO-DECISION 20260905_1152 (two days later) put the\n"
    "    per-scene world registry in LANE-A's hands with LANE-B writing\n"
    "    into it, which is why this module is LANE-A's -- the SEAM is\n"
    "    unchanged and taken from 2245, only the owner moved.  If COO reads\n"
    "    the two rulings differently, this module moves lanes without a\n"
    "    line of it changing.\n"
    "\n"
    "(2) ONCE PER SESSION, in __init__, on the line after\n"
    "    `self.mob_combat_ledger = mob_combat.open_ledger(_boot_roster)`\n"
    "    (runtime.py:1348), with the boot roster's own folder:\n"
    "\n"
    "        self.mob_combat_ledger = (\n"
    "            world_scene_registry.seed_the_session_ledger(\n"
    "                self.mob_combat_ledger,\n"
    "                self.mob_combat_scene_folder))\n"
    "\n"
    "    !! NOT ON EVERY DISPATCH, and this is the correction that matters\n"
    "    most in this note.  An earlier draft asked for this statement\n"
    "    outside the branch on every dispatch, and pf-adversary (round\n"
    "    tz2rgc, N1) MEASURED what that does to a live fight: the book\n"
    "    would be re-read into the session ledger between every blow, so\n"
    "    two players hitting one monster lost 2,218 of 6,000 damage and a\n"
    "    player's own landed hit was pushed back UP by the next dispatch's\n"
    "    seed.  This function is a SEED -- it belongs where a ledger is\n"
    "    OPENED (statement (1) after a scene change, statement (2) at\n"
    "    login) and nowhere else.  A caller that re-seeds a ledger already\n"
    "    carrying this session's own blows is using it as an authority it\n"
    "    was never built to be.\n"
    "\n"
    "    WHY BOTH, and this is the whole of D3: runtime.py seeds\n"
    "    `self.mob_combat_scene_folder` from the BOOT roster's own scene in\n"
    "    __init__, so for a character whose stored scene IS the boot scene\n"
    "    the branch in (1) never runs at all -- statement (2) is the only\n"
    "    one that reaches bg0001, the scene the game boots into.  And for\n"
    "    every OTHER scene, statement (2) alone is a no-op on the dispatch\n"
    "    that matters: the ledger it is handed still belongs to the scene\n"
    "    being left, and the scene-2 and scene-1 census branches compose\n"
    "    the arrival frame from `self.mob_combat_ledger` in that SAME\n"
    "    dispatch -- so the client is told the monster is at its ceiling,\n"
    "    which is the R309 symptom this module exists to end.  Statement\n"
    "    (1) is the one that reaches those; statement (2) exists only for\n"
    "    the login into the boot scene, where (1) never runs.\n"
    "\n"
    "!! THE ONE RULE THIS ASK DOES NOT SETTLE, and LANE-B must have an\n"
    "answer before its write call site lands: when two sessions in one\n"
    "scene write the same monster's health, `note_balance` is\n"
    "last-writer-wins -- it has no compare-and-swap the way\n"
    "`mob_death.commit_death` does.  With the seed confined to ledger-open\n"
    "(above) a player's own blows are never undone, but two players on ONE\n"
    "monster can still each overwrite the other's number.  The round's\n"
    "letter puts that question to COO rather than inventing a rule here.\n"
    "\n"
    "import: `from . import world_scene_registry`\n"
    "\n"
    "NEITHER STATEMENT CAN WRITE THE WRONG SCENE'S LEDGER: the function\n"
    "refuses by name (`another_scenes_ledger`) unless `ledger.scene` folds\n"
    "equal to `folder`, so (2) is inert precisely when it would be wrong\n"
    "and (1) applies precisely when it is right.\n"
    "\n"
    "SAFE IN ANY ORDER WITH A FUTURE DEATH SEED: this one re-reads the\n"
    "grave book itself and skips every identity buried there, and it can\n"
    "only raise a row's health, never zero one.\n"
    "\n"
    "IT RETURNS THE CALLER'S OWN LEDGER on every refusal and never raises,\n"
    "so both statements are safe on every dispatch.  It is silent when the\n"
    "scene's book is empty, which is the ordinary state of most scenes.\n"
    "\n"
    "COST, MEASURED on this clone (the convention runtime.py holds this\n"
    "seam to): 3.0 us on an empty book, 29 us on a full bg0001 book, 93 us\n"
    "on a full Bg0002 book -- paid once per scene change and once per\n"
    "login, not per dispatch.\n"
    "\n"
    "THE WRITE HALF IS LANE-B'S AND IS NOT PART OF THIS ASK: LANE-B calls\n"
    "`world_scene_registry.world_scene_registry().note_balance(...)` from\n"
    "its own accepted-hit call site (COO-DECISION 20260905_1153).  Until it\n"
    "does, this seed finds an empty book and changes nothing -- which is why\n"
    "landing it early costs nothing and closes the wiring gap ahead of the\n"
    "lane that needs it.\n"
)
