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
from typing import Any, NamedTuple

from . import player_wire
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


#: WHERE THE HP PAIR OF A LIVE-PLAYER ROW COMES FROM.  Two sources, never
#: mixed, and each one is what the client of THAT character was already told
#: at its own login -- so a second session is shown the same pair the first
#: session is showing itself.
PRESENCE_HP_SOURCE_ROW = "character_row"
PRESENCE_HP_SOURCE_LOGIN_CONSTANTS = "player_wire_login_constants"

#: WHERE THE POSITION OF A LIVE-PLAYER ROW COMES FROM.  A login resolves ONE
#: position (``world_scene_entry.resolve_entry``) and sends THAT point to the
#: client.  The stored row it was resolved from can name a DIFFERENT scene:
#: on the GM login-scene-override path ``runtime.py`` resolves the override,
#: sends it, and only then replaces the in-memory row's position -- its own
#: comment there calls ``entry.position`` "the ONE resolved position".  A
#: presence row is read to tell OTHER players where somebody is standing, so
#: it must carry the point that character's own client was sent, never the
#: row the point was derived from.
PRESENCE_POSITION_SOURCE_ROW = "character_row_position"
PRESENCE_POSITION_SOURCE_RESOLVED_ENTRY = "resolved_scene_entry"

PRESENCE_REFUSED_NO_POSITION = "character_row_has_no_position"
PRESENCE_REFUSED_ENTRY_HAS_NO_POSITION = "resolved_entry_has_no_position"
PRESENCE_REFUSED_HP_PAIR_HALF_SET = "character_row_hp_pair_only_half_set"
PRESENCE_REFUSED_LOGIN_VITALS_PARTIAL = "character_row_login_vitals_partial"
PRESENCE_REFUSED_HP_PAIR_NOT_INTS = "character_row_hp_pair_is_not_two_ints"
PRESENCE_REFUSED_HP_CURRENT_BELOW_ONE = "character_row_hp_current_below_one"
PRESENCE_REFUSED_HP_MAX_BELOW_ONE = "character_row_hp_max_below_one"
PRESENCE_REFUSED_HP_CURRENT_ABOVE_MAX = "character_row_hp_current_above_max"
PRESENCE_REFUSED_HP_ABOVE_CEILING = "character_row_hp_above_registry_ceiling"

#: The registry stores an HP pair the encoder writes as u32, and refuses
#: anything above ``world_scene_registry._MAX_HP``.  This door carries its
#: own copy of that ceiling so a refusal at this level is NAMED (the
#: registry's own answer is a bare outcome that does not say "too big"), and
#: a test pins the two against each other -- a copied ceiling that silently
#: drifts from the registry's is worse than no ceiling at all.
PRESENCE_HP_CEILING = 0xFFFFFFFF

#: Prefix of the one console line this module prints.  A presence write that
#: refuses is a player who is about to be INVISIBLE to every other session in
#: the scene, and until this line existed that happened without a byte on the
#: console -- the "silent skip" shape the house forbids, in a file whose
#: neighbours in ``runtime.py`` (``BACKPACK_LOAD_REFUSED``,
#: ``GM_LOGIN_SCENE_OVERRIDE_CONSUME_FAILED``) all announce.  Found by
#: pf-adversary, round q6a8oa, finding D5.
PRESENCE_REFUSED_CONSOLE_TOKEN = "LANE_A_PRESENCE_REFUSED"


def _ascii_token(value: Any) -> str:
    """``value`` as a single ASCII word that can never break the console.

    The bridge console is cp874: one non-ASCII byte from a name or a
    ``__repr__`` takes the print statement -- and with it the login -- down.
    Everything this function is handed is a value some other lane or the
    database chose, so nothing here trusts it.
    """
    try:
        text = str(value)
    except Exception:  # noqa: BLE001 - a __str__ that throws is still a value
        text = "<unprintable>"
    text = text.encode("ascii", "replace").decode("ascii")
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text)[:48]


def _announce_presence_refusal(reason: str, scene_id: Any, identity: Any) -> None:
    """Say out loud that a live player just failed to enter the world book.

    Never raises, for the same reason the doors below never raise: this runs
    on the login and movement paths, and a session must not die because a
    diagnostic could not be printed.
    """
    try:
        print(
            PRESENCE_REFUSED_CONSOLE_TOKEN + " " + _ascii_token(reason)
            + " scene=" + _ascii_token(scene_id)
            + " character=" + _ascii_token(identity)
        )
    except Exception:  # noqa: BLE001 - a broken stdout is not a login failure
        pass


class PresenceHpPair(NamedTuple):
    """The pair a presence row will carry, and WHICH source it came from."""

    current_hp: int
    max_hp: int
    source: str


class PresencePosition(NamedTuple):
    """The point a presence row will carry, and WHICH source it came from."""

    scene_id: int
    x: Any
    y: Any
    z: Any
    source: str


def hp_pair_for_character(selected: Any) -> PresenceHpPair:
    """The HP pair to remember for ``selected``, or raise by name.

    THIS FUNCTION EXISTS TO CLOSE THE ONE OPEN QUESTION THIS LANE'S OWN ASK
    CARRIED.  ``PLAYER_PRESENCE_WIRING`` used to hand chief a paste with
    ``<current hp>`` / ``<max hp>`` in it and say the read had no single
    obvious source.  It has one, and it is not a new guess -- it is the
    predicate ``legacy_bridge.start_game`` already applies to the very same
    row when it composes that character's OWN login frame:

    * ``PANYA-DECISION 20260901_1059`` makes the login vitals ALL THREE OR
      NONE, and ``legacy_bridge`` spells that predicate out --
      ``level is not None and hp_current is not None and hp_max is not
      None``.  When it holds, the client of that character was sent the
      row's own pair; when NONE of the three is set, it was sent
      ``player_wire.PLAYER_LOGIN_HP_CURRENT`` / ``_HP_MAX``.  Either way the
      answer here is what that character's client is displaying right now.
    * ANY OTHER MIX IS REFUSED BY NAME.  A row carrying a real pair beside a
      ``None`` level is a row whose own login sent the CONSTANTS -- reading
      380/520 off it here would show the second player a bar the first
      player is not looking at.  (pf-adversary, round q6a8oa, finding D3:
      the earlier version of this door cited the three-value rule and then
      guarded only two of the three.)

    AND IT NEVER LETS A ZERO THROUGH.  ``HP == 0`` is the client's DEATH
    predicate (0x43BD7A / 0x43BDAA, the Q1 finding this module's header
    already cites, which is why the encoder refuses HP < 1 too).  A presence
    row built from a zero pair would put a dead-looking second player in the
    world book that every later frame reads, so the refusal happens at the
    write door as well, not only at the encoder.
    """
    level = getattr(selected, "level", None)
    current = getattr(selected, "hp_current", None)
    maximum = getattr(selected, "hp_max", None)
    set_count = sum(1 for value in (level, current, maximum) if value is not None)
    if set_count == 0:
        return PresenceHpPair(
            player_wire.PLAYER_LOGIN_HP_CURRENT,
            player_wire.PLAYER_LOGIN_HP_MAX,
            PRESENCE_HP_SOURCE_LOGIN_CONSTANTS,
        )
    if set_count != 3:
        if (current is None) != (maximum is None):
            _refuse(PRESENCE_REFUSED_HP_PAIR_HALF_SET, repr((current, maximum)))
        _refuse(PRESENCE_REFUSED_LOGIN_VITALS_PARTIAL,
                repr((level, current, maximum)))
    for value in (current, maximum):
        if type(value) is not int:
            _refuse(PRESENCE_REFUSED_HP_PAIR_NOT_INTS, repr((current, maximum)))
    if current < 1:
        _refuse(PRESENCE_REFUSED_HP_CURRENT_BELOW_ONE, repr(current))
    if maximum < 1:
        _refuse(PRESENCE_REFUSED_HP_MAX_BELOW_ONE, repr(maximum))
    if current > maximum:
        _refuse(PRESENCE_REFUSED_HP_CURRENT_ABOVE_MAX, repr((current, maximum)))
    if maximum > PRESENCE_HP_CEILING:
        _refuse(PRESENCE_REFUSED_HP_ABOVE_CEILING, repr((current, maximum)))
    return PresenceHpPair(current, maximum, PRESENCE_HP_SOURCE_ROW)


def presence_position_for_login(selected: Any, entry: Any = None) -> PresencePosition:
    """The point a login's presence row must carry, or raise by name.

    ``entry`` is the ``world_scene_entry.resolve_entry`` result the login
    already holds.  When it is present its position WINS OUTRIGHT -- scene
    included -- because that is the point the client was actually sent.

    WHY THIS ARGUMENT EXISTS AT ALL (pf-adversary, round q6a8oa, finding
    D1).  The earlier ask told chief to paste the presence write straight
    after ``lane_hooks.register_live_session(...)``, hundreds of lines
    BEFORE the login resolves its entry -- and on the GM login-scene
    override path the stored row still names the scene the player came
    from.  Measured on that paste: the viewer standing in the overridden
    scene saw nobody, and a ghost row sat in the old scene.  With ``entry``
    in hand there is no path where the two can disagree, whether the paste
    moves or not.

    ``entry=None`` is the honest answer for a call site that has no resolved
    entry (the movement door below): the row's own position is then the best
    fact anybody has.
    """
    if entry is not None:
        where = getattr(entry, "position", None)
        scene_id = getattr(where, "scene_id", None)
        if type(scene_id) is not int:
            _refuse(PRESENCE_REFUSED_ENTRY_HAS_NO_POSITION, repr(where))
        return PresencePosition(
            scene_id, getattr(where, "x", None), getattr(where, "y", None),
            getattr(where, "z", None), PRESENCE_POSITION_SOURCE_RESOLVED_ENTRY,
        )
    where = getattr(selected, "position", None)
    scene_id = getattr(where, "scene_id", None)
    if type(scene_id) is not int:
        _refuse(PRESENCE_REFUSED_NO_POSITION, repr(where))
    return PresencePosition(
        scene_id, getattr(where, "x", None), getattr(where, "y", None),
        getattr(where, "z", None), PRESENCE_POSITION_SOURCE_ROW,
    )


def register_presence_for_character(
    selected: Any, *, position: Any = None, entry: Any = None,
    registry: Any = None,
) -> "world_scene_registry.PlayerNoteOutcome":
    """Remember the character ``selected`` as standing where it stands.

    THE WHOLE POINT: this is the door the ``runtime.py`` call sites of
    :data:`PLAYER_PRESENCE_WIRING` need, so no paste has to read an HP field
    or do a scene-id-to-folder lookup itself.  Identity and name come off
    the row the call site already has in hand, the HP pair comes from
    :func:`hp_pair_for_character`, and the point comes from
    :func:`presence_position_for_login`.

    ``entry`` is the resolved scene entry, when the call site has one; its
    position wins outright, scene included.  ``position`` overrides the x/y/z
    of whichever position won and NOTHING else -- that is the movement call
    site, where a position report is fresher than the row but is the SAME
    character in the SAME scene.  Passing both means "the entry decided the
    scene, this report decided the point".

    IT DOES NOT RAISE FOR ANY SHAPE A ``model.Character`` CAN TAKE.  Every
    refusal comes back as a named ``PlayerNoteOutcome`` -- the shape
    :func:`register_player_presence` already answers with -- because a
    presence write sits on the login and movement paths, where an exception
    would take the session down with it.  The bounded exception (measured,
    not assumed): a hand-built stand-in whose property or ``__getattr__``
    throws can still raise through the ``getattr`` calls here, because a
    door that swallowed THAT would be hiding a broken caller rather than a
    bad row.  ``model.Character`` is a frozen dataclass and has no such
    shape.  (pf-adversary, round q6a8oa, finding D9: the previous docstring
    said "NEVER RAISES" flatly, and that was one word too strong.)
    """
    identity = getattr(selected, "id", None)
    try:
        point = presence_position_for_login(selected, entry)
    except RemotePlayerActorRefusal as refusal:
        reason = _refusal_token(refusal)
        _announce_presence_refusal(reason, None, identity)
        return world_scene_registry.PlayerNoteOutcome("", None, reason)
    if position is None:
        xyz = (point.x, point.y, point.z)
    else:
        xyz = position
    try:
        pair = hp_pair_for_character(selected)
    except RemotePlayerActorRefusal as refusal:
        reason = _refusal_token(refusal)
        _announce_presence_refusal(reason, point.scene_id, identity)
        return world_scene_registry.PlayerNoteOutcome(
            world_scene_folder.scene_folder_for_scene_id(point.scene_id) or "",
            None,
            reason,
        )
    outcome = register_player_presence(
        point.scene_id,
        identity,
        getattr(selected, "name", None),
        pair.current_hp,
        pair.max_hp,
        xyz,
        registry=registry,
    )
    if not getattr(outcome, "noted", True):
        _announce_presence_refusal(
            getattr(outcome, "reason", None) or "unnamed", point.scene_id,
            identity,
        )
    return outcome


def register_presence_for_login(
    selected: Any, entry: Any = None, *, registry: Any = None,
) -> "world_scene_registry.PlayerNoteOutcome":
    """The login call site's door: one row, one resolved entry, no decisions.

    Exactly :func:`register_presence_for_character` with the entry threaded
    through -- it exists so the paste in ``PLAYER_PRESENCE_WIRING`` reads as
    the sentence it is, and so the login path can never accidentally be
    given a ``position=`` override it has no business carrying.
    """
    return register_presence_for_character(
        selected, entry=entry, registry=registry,
    )


def _refusal_token(refusal: "RemotePlayerActorRefusal") -> str:
    """The bare reason name out of a refusal message, for a caller that
    answers outcomes rather than exceptions.  ASCII in, ASCII out: the token
    is one of the module constants above, and the detail after ``" ("`` --
    which may carry a repr of anything at all -- is dropped here."""
    return str(refusal).split("refused: ", 1)[-1].split(" (", 1)[0]


#: The pasteable call site, kept next to the module it names -- the same
#: device ``world_scene_registry.WORLD_REGISTRY_SEED_WIRING`` and
#: ``mob_death_persistence.DEATH_SEED_WIRING`` already use.  ``runtime.py``
#: is chief's file; LANE-A does not edit it.
#:
#: REVISION 2 (this text was WRONG in revision 1, and the errors were this
#: lane's own -- pf-adversary, round q6a8oa, findings D1/D4/D6).  What
#: changed: call site (1) moved to AFTER the login resolves its entry and
#: takes that entry as an argument (revision 1 pasted it hundreds of lines
#: earlier, where the row still names the pre-override scene); the two
#: sentences claiming no paste reads a field and that all three doors read
#: the HP pair were struck, because neither was true; and call site (2) now
#: says out loud how much of walking it actually covers.
PLAYER_PRESENCE_WIRING = (
    "THREE CALL SITES, all in runtime.py, all keyed by the selected\n"
    "character row or by scene id.  This module's doors do the\n"
    "scene-id-to-folder lookup, the HP-pair read and the position choice,\n"
    "so no paste computes any of those three; the fields a paste does read\n"
    "are named in the paste itself (call site (3) reads .id, and the\n"
    "disconnect call reads a scene id and a character id, because those are\n"
    "arguments and there is no row in hand there).\n"
    "\n"
    "(1) ONCE PER SESSION, in the START_GAME_REQ handler, AFTER the\n"
    "    login-scene-override position resync -- the block ending with\n"
    "    `self.events.append(f\"gm_login_scene_override_selected_position_\"\n"
    "    f\"resynced_{entry.position.scene_id}\")` -- and before the\n"
    "    CORE-REQUEST-006 GM-state block that opens with\n"
    "    `is_gm = is_gm_account(self.token)`:\n"
    "\n"
    "        world_remote_player_actor.register_presence_for_login(\n"
    "            self.foundation.selected, entry)\n"
    "\n"
    "    WHY NOT AT `lane_hooks.register_live_session(...)`, WHICH IS WHERE\n"
    "    REVISION 1 OF THIS ASK PUT IT.  That line runs before\n"
    "    `entry = world_scene_entry.resolve_entry(...)`, and on the GM\n"
    "    login-scene-override path the row still carries the scene the\n"
    "    player came FROM -- runtime.py's own comment at the resync calls\n"
    "    entry.position 'the ONE resolved position' and says this override\n"
    "    is the first login path in this project where the two can differ.\n"
    "    Pasted there, an overridden login puts a ghost row in the old\n"
    "    scene and is invisible in the scene the player is standing in.\n"
    "    Measured on the revision-1 paste: viewer in the override scene saw\n"
    "    0 others, viewer in the stored scene saw 1.\n"
    "    Passing `entry` makes the choice belt-and-braces rather than\n"
    "    positional: presence_position_for_login takes the resolved point\n"
    "    outright, scene included, so the write is correct even if this\n"
    "    paste later moves again.\n"
    "\n"
    "    NOTHING IS LEFT FOR THE PASTE TO DECIDE.  Identity, name and the\n"
    "    HP pair are read off that row inside the door; the pair is the\n"
    "    row's own hp_current/hp_max when its login sent them and\n"
    "    player_wire's login constants when it did not, using the SAME\n"
    "    all-three-or-none predicate legacy_bridge.start_game applies to\n"
    "    that row (PANYA-DECISION 20260901_1059).  A partial vitals row, a\n"
    "    half pair and any pair containing a zero are refused BY NAME and\n"
    "    printed as `LANE_A_PRESENCE_REFUSED <reason> scene=<n>\n"
    "    character=<id>`, because a refused write means that player is\n"
    "    invisible to everyone else in the scene and that must not happen\n"
    "    silently.\n"
    "\n"
    "(2) IN `_vital_walk_promote_target_pos`, right after\n"
    "    `self.last_target_pos = (x, y, z, heading)`:\n"
    "\n"
    "        world_remote_player_actor.register_presence_for_character(\n"
    "            self.foundation.selected, position=(x, y, z))\n"
    "\n"
    "    HOW MUCH OF WALKING THIS COVERS, SAID PLAINLY: not all of it.\n"
    "    That method returns 'v141_reads_this_frame_itself' before this line\n"
    "    for an ordinary TargetPos frame -- v141 writes the field itself in\n"
    "    its own branch, and this method deliberately stands down so one\n"
    "    field never has two authors.  The line above is reached on the\n"
    "    promoted path (the frame that also carries a pickup click).  So\n"
    "    with only this paste, a presence row is refreshed on SOME steps and\n"
    "    otherwise stays at the position call site (1) wrote.  Covering\n"
    "    ordinary walking needs a second writer somewhere v141's own branch\n"
    "    reaches -- that is chief's file and chief's call, and this ask does\n"
    "    not invent it.  A stale-but-real position is a correct thing to\n"
    "    show while that is decided; a wrong SCENE is not, and (1) is what\n"
    "    fixes the scene.\n"
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
