"""LANE-A (WORLD): the always-on actor_type 2 (CNetActor) composer for a
SECOND REAL PLAYER standing in the same scene.

WHAT A PLAYER WOULD SEE BECAUSE OF THIS FILE, STATED HONESTLY.  Nothing yet
on its own: this module composes real bytes from the real, shared, per-scene
world registry (``world_scene_registry``), but nothing in ``runtime.py``
calls it yet -- see :data:`PLAYER_PRESENCE_WIRING` below for the exact,
paste-ready call sites this lane is asking chief for, the same shape
``world_scene_registry.WORLD_REGISTRY_SEED_WIRING`` already used to ask for
the monster half of the same registry.  Once those two call sites land, a
second character standing in a scene this lane's own arrival composer
already opens for players becomes a real, always-on ``actor_type 2``
(``CNetActor``) entry -- name, HP, position -- in the world state the OTHER
session receives, with no scenario flag anywhere in the path.

WHY THIS IS A PROMOTION AND NOT A NEW GUESS.  Every byte value below is
copied, not re-derived, from ``remote_player_hypothesis.py``'s own proven
constants (HYP-PF-025, closed against Q1/Q2/Q3 of the chunk2 static round):
the BasicAttr mask that carries a name for the first time
(``BASIC_MASK_PROBE`` == 0x030D), the ActorAttr 64-bit mask that Q1 proved is
legal at zero because the actor-entry bind pipe never reads it
(``ACTOR_ATTR_MASK_PROBE`` == 0), the +0x1BC extra-group byte v141 always
sent (``ACTOR_ATTR_EXTRA_GROUP_VALUE`` == 1), and ``actor_type`` 2 itself
(``CNetActor``, VA 0x4469E1, jump table 0x446B2C).  What THIS module drops,
on purpose, is everything that made that file a probe rather than a feature:
the wire-unlock token (this module has no scenario to gate it behind -- it is
supposed to run on every normal boot), the three synthetic identities A/B/C,
the AvatarAttr replay, and the negative control.  A real second player's
identity, name, HP and position come from the world registry, not from a
fixed experiment plan.

WHY THE ENCODER IS REUSED AND NOT REWRITTEN.  ``legacy.make_npc_attr``,
``legacy.make_remote_movement_attr``, ``legacy.make_remote_actor_entry`` and
``legacy.make_runtime_remote_actors`` are the same four frozen-image
functions every other emitter in this project already calls (``population.py``,
``remote_player_hypothesis.py``, every ``world_population_bg*.py``).  This
module is the fifth caller, not a second implementation of the wire.

WHERE THE ROSTER COMES FROM.  ``world_scene_registry`` -- LANE-A's own
per-scene, in-process, shared-across-every-session world book
(``PANYA-DECISION 20260905_1140`` / ``COO-DECISION 20260905_1152``), which
until this round held only monsters, graves and ground.  :mod:`world_scene_registry`
now carries a fourth book, ``PlayerVital`` rows, written through
``note_player``/read through ``remembered_players``/``view().players`` --
added in this same round, in that file, not duplicated here.  This module
never keeps its own copy of who is standing where: every call re-reads the
registry, the same "seeded from, never replaced by" discipline
``world_scene_registry.seed_the_session_ledger`` documents for monsters.

FAIL CLOSED, THE SAME LADDER THE PROBE USED.  A malformed scene id, a
malformed viewer identity, or a ``PlayerVital`` row shaped wrong all refuse a
name rather than compose a guess; a viewer never receives their own actor
entry back (filtered by identity before one byte is composed); and nothing
here ever emits ``actor_type`` anything other than 2 -- there is no parameter
that could ask it to.

NONCLAIMS, STATED THE SAME WAY THE PROBE STATED ITS OWN.  No claim that any
of this renders on a real client (that is the same open question
``remote_player_hypothesis.py`` names, now inherited by the production path
instead of the probe).  No interest management, no cadence and no
interpolation -- one call composes one snapshot frame naming every OTHER
player the registry currently remembers for a scene, nothing incremental.  No
despawn path: the registry's own ``forget_player`` exists for that and this
module does not call it.  No write side of the registry either -- this
module only READS ``world_scene_registry`` and turns rows into bytes; who
calls ``note_player``/``forget_player`` and when is exactly the CORE-REQUEST
below.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import world_scene_folder
from . import world_scene_registry
from .population import MOVEMENT_ATTR_ID
from .remote_player_hypothesis import (
    ACTOR_ATTR_EXTRA_GROUP_TAG,
    ACTOR_ATTR_EXTRA_GROUP_VALUE,
    ACTOR_ATTR_ID,
    ACTOR_ATTR_MASK_PROBE as ACTOR_ATTR_MASK_LIVE_PLAYER,
    ACTOR_ATTR_MASK_TAG,
    BASIC_ATTR_MASK_TAG,
    BASIC_MASK_PROBE as BASIC_MASK_LIVE_PLAYER,
    DB_ATTRIBUTE_IDENTITY_MASK,
    DB_ATTRIBUTE_MASK_TAG,
    IDENTITY_TAG,
    MOVEMENT_MASK_FULL,
    REMOTE_PLAYER_ACTOR_TYPE,
    REMOTE_PLAYER_HP_MIN,
)

# Always-on: this module composes no frame on its own and gates on nothing
# but well-formed input.  It is not reachable from a live session yet (see
# the module docstring); that is a missing CALLER, the same honestly-flagged
# gap ``mob_ai_scheduler.py`` records for ``tick_step`` before its own
# caller landed -- not a reason to mark real, unconditional code a probe.
production_allowed = True


class RemotePlayerActorRefusal(ValueError):
    """A live-player actor entry, or a live-players frame, that must never
    reach a socket."""


def _refuse(reason: str, detail: str = "") -> None:
    message = "world_remote_player_actor refused: " + reason
    if detail:
        message += " (" + detail + ")"
    raise RemotePlayerActorRefusal(message)


def _require_scene_id(scene_id: Any) -> int:
    if type(scene_id) is not int or type(scene_id) is bool:
        _refuse("scene_id_not_an_int", repr(scene_id))
    return scene_id


def _require_actor_identity(identity: Any) -> int:
    if type(identity) is not int or type(identity) is bool:
        _refuse("identity_not_an_int", repr(identity))
    return identity


def encode_live_player_actor_attr(
    legacy: Any, player: Any, scene_id: int, scene_sequence: int = 0,
) -> bytes:
    """One ActorAttr body for a real other player, byte-shape identical to
    ``remote_player_hypothesis.encode_remote_player_actor_attr`` minus the
    wire-unlock gate: BasicAttr bit 0x0001 (name) + 0x0004/0x0008 (HP pair) +
    0x0100/0x0200 (scene pair) == mask 0x030D, then the ActorAttr 64-bit mask
    pinned at 0 and the +0x1BC extra-group byte pinned at 1 -- the exact
    values Q1 proved land every field the client's bind pipe actually reads.

    Cross-checked against ``legacy.make_npc_attr`` the same way the probe
    checks itself: BasicAttr::Serial 0x4656F0 runs first on both attr
    classes, so this body's BasicAttr span must equal the same span of the
    frozen, client-proven ``make_npc_attr`` output.  Anything else means the
    name field landed in the wrong place, and NO BYTES leave this function.
    """
    if type(player) is not world_scene_registry.PlayerVital:
        _refuse("not_a_player_vital_row", repr(type(player)))
    scene_id = _require_scene_id(scene_id)
    if type(scene_sequence) is not int or type(scene_sequence) is bool:
        _refuse("scene_sequence_not_an_int", repr(scene_sequence))
    if player.current_hp < REMOTE_PLAYER_HP_MIN:
        # Unreachable through ``PlayerVital`` (its own ``__post_init__``
        # already refuses this) -- kept because this function must never
        # assume a caller only ever hands it a validated row.
        _refuse("hp_zero_would_cross_into_the_death_chain")

    prefix = bytes(
        legacy.u8tag(DB_ATTRIBUTE_MASK_TAG, DB_ATTRIBUTE_IDENTITY_MASK)
        + legacy.qwordtag(IDENTITY_TAG, player.actor_identity)
        + legacy.u16tag(BASIC_ATTR_MASK_TAG, BASIC_MASK_LIVE_PLAYER)
        # Ascending mask-bit order, the order BasicAttr's own serializer
        # 0x4656F0 writes and its reader expects.
        + legacy.wstr_tag(player.name)                          # 0x0001
        + legacy.u32tag(0x14, player.current_hp)                 # 0x0004
        + legacy.u32tag(0x14, player.max_hp)                     # 0x0008
        + legacy.u16tag(BASIC_ATTR_MASK_TAG, scene_id)           # 0x0100
        + legacy.qwordtag(IDENTITY_TAG, scene_sequence)          # 0x0200
    )
    baseline = legacy.make_npc_attr(
        1, player.actor_identity, scene_id, scene_sequence, "",
        player.current_hp, player.max_hp, None, player.name,
    )
    if bytes(baseline[:len(prefix)]) != prefix:
        _refuse(
            "basic_prefix_does_not_reproduce_make_npc_attr",
            "the shared BasicAttr span drifted",
        )
    body = (
        prefix
        + legacy.qwordtag(ACTOR_ATTR_MASK_TAG, ACTOR_ATTR_MASK_LIVE_PLAYER)
        + legacy.u8tag(ACTOR_ATTR_EXTRA_GROUP_TAG, ACTOR_ATTR_EXTRA_GROUP_VALUE)
    )
    return bytes(body)


def encode_live_player_movement_attr(legacy: Any, player: Any) -> bytes:
    """One full-snapshot MovementAttr (mask 0xFF) at the player's own
    remembered position -- the same mask ``SPAWN_BARE``/``SPAWN_AVATAR``
    used in the probe for a first sighting of an identity."""
    if type(player) is not world_scene_registry.PlayerVital:
        _refuse("not_a_player_vital_row", repr(type(player)))
    x, y, z = player.position
    return legacy.make_remote_movement_attr(
        player.actor_identity, x, y, z, 0.0, mask=MOVEMENT_MASK_FULL,
    )


def encode_live_player_actor_entry(
    legacy: Any, player: Any, scene_id: int, scene_sequence: int = 0,
) -> bytes:
    """One ``actor_type`` 2 (``CNetActor``) actor entry for a real other
    player: ActorAttr (name, HP, scene) then MovementAttr (full snapshot),
    the same order ``SPAWN_BARE`` uses -- there is no avatar tail here, so
    the ordering question the probe's ``SPAWN_AVATAR`` deviation exists for
    does not arise."""
    actor_attr = encode_live_player_actor_attr(
        legacy, player, scene_id, scene_sequence,
    )
    movement_attr = encode_live_player_movement_attr(legacy, player)
    return legacy.make_remote_actor_entry(
        REMOTE_PLAYER_ACTOR_TYPE, player.actor_identity,
        [(ACTOR_ATTR_ID, actor_attr), (MOVEMENT_ATTR_ID, movement_attr)],
    )


@dataclass(frozen=True)
class LivePlayersFrame:
    """What one call to :func:`compose_other_live_players_frame` produced.

    ``actor_count == 0`` (``pc``/``frame`` both empty bytes) is the everyday,
    honest answer for a scene where the viewer is the only player the
    registry knows about -- not an error, and never padded with a
    fabricated entry to make the frame non-empty.
    """

    scene_id: int
    pc: bytes
    frame: bytes
    actor_count: int
    identities: tuple[int, ...]


_EMPTY_FRAME_FOR = lambda scene_id: LivePlayersFrame(scene_id, b"", b"", 0, ())  # noqa: E731


def compose_other_live_players_frame(
    legacy: Any, scene_id: int, viewer_identity: int, *,
    scene_sequence: int = 0, registry: Any = None,
) -> LivePlayersFrame:
    """Every OTHER player the world registry remembers for ``scene_id``,
    as one ``GSCN_RunTimeProtocolRes`` actor-entry collection.

    ``viewer_identity`` is filtered out before one byte is composed, so a
    session is structurally unable to receive an entry for itself through
    this door.  Reads ``world_scene_registry`` fresh on every call -- never
    caches -- so a row this scene forgets between two calls is correctly
    absent from the next one.

    Never raises: a scene this registry has no folder for, or whose player
    book cannot be read, answers the empty frame above rather than taking a
    census down over a bookkeeping question.
    """
    try:
        scene_id = _require_scene_id(scene_id)
        viewer_identity = _require_actor_identity(viewer_identity)
    except RemotePlayerActorRefusal:
        return _EMPTY_FRAME_FOR(scene_id if type(scene_id) is int else -1)
    folder = world_scene_folder.scene_folder_for_scene_id(scene_id)
    if not folder:
        return _EMPTY_FRAME_FOR(scene_id)
    book = (
        registry if registry is not None
        else world_scene_registry.world_scene_registry()
    )
    try:
        players = book.remembered_players(folder)
    except Exception:                                        # noqa: BLE001
        players = ()
    others = tuple(
        row for row in players
        if type(row) is world_scene_registry.PlayerVital
        and row.actor_identity != viewer_identity
    )
    if not others:
        return _EMPTY_FRAME_FOR(scene_id)
    entries = [
        encode_live_player_actor_entry(legacy, row, scene_id, scene_sequence)
        for row in others
    ]
    pc, frame = legacy.make_runtime_remote_actors(entries)
    return LivePlayersFrame(
        scene_id, pc, frame, len(others),
        tuple(row.actor_identity for row in others),
    )


def describe_live_players_frame(result: Any) -> str:
    """One bounded ASCII console line.  Never raises."""
    try:
        return (
            "WORLD_REMOTE_PLAYER_ACTOR scene_id=%s other_players=%d"
            % (result.scene_id, result.actor_count)
        )
    except Exception:                                        # noqa: BLE001
        return "WORLD_REMOTE_PLAYER_ACTOR scene_id=? other_players=?"


def register_player_presence(
    scene_id: int, actor_identity: int, name: str, current_hp: int,
    max_hp: int, position: Any, *, registry: Any = None,
) -> "world_scene_registry.PlayerNoteOutcome":
    """Convenience write door keyed by ``scene_id`` (an int) rather than the
    registry's own folder string -- what a future ``runtime.py`` call site
    actually has in hand.  Never raises: a scene id this project's folder
    table does not address answers a named refusal, the same shape every
    other door in this file uses.

    THE ONE THING THIS FUNCTION DOES NOT DO: decide WHEN to call itself.
    See :data:`PLAYER_PRESENCE_WIRING`.
    """
    folder = world_scene_folder.scene_folder_for_scene_id(scene_id)
    if not folder:
        return world_scene_registry.PlayerNoteOutcome(
            "", None, "scene_id_has_no_folder",
        )
    book = (
        registry if registry is not None
        else world_scene_registry.world_scene_registry()
    )
    return book.note_player(
        folder, actor_identity, name, current_hp, max_hp, position,
    )


def clear_player_presence(
    scene_id: int, actor_identity: int, *, registry: Any = None,
) -> bool:
    """Convenience forget door keyed by ``scene_id``.  See
    :func:`register_player_presence`.  Never raises; ``False`` covers both
    "no such scene" and "no such row"."""
    folder = world_scene_folder.scene_folder_for_scene_id(scene_id)
    if not folder:
        return False
    book = (
        registry if registry is not None
        else world_scene_registry.world_scene_registry()
    )
    return book.forget_player(folder, actor_identity)


#: The pasteable call site, kept next to the module it names -- the same
#: device ``world_scene_registry.WORLD_REGISTRY_SEED_WIRING`` and
#: ``mob_death_persistence.DEATH_SEED_WIRING`` already use.  ``runtime.py``
#: is chief's file; LANE-A does not edit it.
PLAYER_PRESENCE_WIRING = (
    "THREE CALL SITES, all in runtime.py, all keyed by scene id (this\n"
    "module's own convenience doors -- register_player_presence /\n"
    "clear_player_presence -- already do the scene-id-to-folder lookup, so\n"
    "none of these three pastes needs to import world_scene_folder itself):\n"
    "\n"
    "(1) ONCE PER SESSION, right after `lane_hooks.register_live_session(\n"
    "    self.foundation.selected.id, self)` in the START_GAME_REQ handler\n"
    "    (the same call site CORE-REQUEST-GM-054 already added), with the\n"
    "    just-selected character's own row and its BOOT position:\n"
    "\n"
    "        world_remote_player_actor.register_player_presence(\n"
    "            self.foundation.selected.position.scene_id,\n"
    "            self.foundation.selected.id,\n"
    "            self.foundation.selected.name,\n"
    "            <current hp>, <max hp>,\n"
    "            (self.foundation.selected.position.x,\n"
    "             self.foundation.selected.position.y,\n"
    "             self.foundation.selected.position.z))\n"
    "\n"
    "    THE HP PAIR HAS NO SINGLE OBVIOUS READ in today's tree (this lane\n"
    "    does not own character HP state) -- naming the exact read is the\n"
    "    one open question in this ask, for chief or whichever lane owns\n"
    "    that field to answer, not a guess this module will make.\n"
    "\n"
    "(2) IN `_vital_walk_promote_target_pos` (or the frame this project ends\n"
    "    up promoting a position report through), right after\n"
    "    `self.last_target_pos = (x, y, z, heading)`:\n"
    "\n"
    "        world_remote_player_actor.register_player_presence(\n"
    "            self.foundation.selected.position.scene_id,\n"
    "            self.foundation.selected.id, <name>, <hp>, <max_hp>,\n"
    "            (x, y, z))\n"
    "\n"
    "    Last-writer-wins, the same rule world_scene_registry.note_balance\n"
    "    already carries for monster health -- named there, not invented\n"
    "    here.\n"
    "\n"
    "(3) ON THE ARRIVAL PATH, after a census (or the scene-1/scene-2\n"
    "    dedicated branch) composes its own frame, ONE more action appended\n"
    "    to the actions list this dispatch already returns:\n"
    "\n"
    "        live_others = world_remote_player_actor.\\\n"
    "            compose_other_live_players_frame(\n"
    "                legacy, scene_id, self.foundation.selected.id)\n"
    "        if live_others.actor_count:\n"
    "            actions.append((\n"
    "                'WORLD_REMOTE_PLAYER_ACTOR_' + str(live_others.actor_count),\n"
    "                live_others.pc, live_others.frame, 0.0))\n"
    "\n"
    "    THIS ONLY REACHES THE SESSION THAT JUST ARRIVED: the session(s)\n"
    "    already standing there receive nothing from this call, because\n"
    "    nothing calls (3) again for them.  A full broadcast (\"the earlier\n"
    "    session sees the new arrival too\") needs a way to hand a frame to\n"
    "    A DIFFERENT connection's socket than the one currently dispatching\n"
    "    -- this project's connection model is one thread per socket\n"
    "    (connection.py, shutdown.py's ManagedThread) with no queue between\n"
    "    them today, and building one is a bigger, cross-cutting decision\n"
    "    this ask does not make for chief.\n"
    "\n"
    "AND ONE DISCONNECT CALL SITE, wherever a session's socket is known to\n"
    "have closed for good: `world_remote_player_actor.clear_player_presence(\n"
    "scene_id, character_id)` -- without it, a logged-out character stays\n"
    "visible to arriving sessions until the process reboots.\n"
    "\n"
    "import: `from . import world_remote_player_actor`\n"
)
