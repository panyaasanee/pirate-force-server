"""CORE-REQUEST-014: Columbus (MOBS n_ID 156, bg0001 placement index 1) ->
quest 3021 -> sea-scene transfer, wired only as far as the tree's own evidence
actually reaches today.

WHAT THIS MODULE IS FOR.  ``notes_to_chief/20260827_1052_LANE-A-CORRECTION-
columbus-m2-quest3021-not-3023-scene17-not-19.md``'s CORE-REQUEST asks for one
thing: wire ``NPCConversation``/``QuestOperateVital`` op1 so that when the
player's client sends operation 1 for quest 3021 (after Columbus's conversation
was opened), the server binds ``CGCVehicleModule``/``CVehicleAttr`` to the
player's EXISTING actor (RE-085 - no new actor) and moves the player to scene
17 (``Bg1001``) via ``TeleportVital``/``ForcePos``.

WHAT IS EVIDENCED AND BUILT HERE.

1. **The trigger.**  ``ChooseNPC``/``TargetVital`` naming Columbus's actor
   identity (``population.load_port_royal_placements`` placement index 1,
   ``0x2000 + 1 + 1 = 0x2002`` - the same formula BUILD-001's census already
   uses for every other placement) sends one ``NPCConversation`` descriptor
   naming quest 3021.  The wire shape is the frozen ``make_npc_conversation_
   quest3020`` (``current/pf_login_game_server_v141.py:782-804``) read and
   generalised on actor identity AND quest id - not reinvented - because
   RE-094 (``notes_to_chief/20260827_0156_RE-094-RESULT-OP1-USES-DYNAMIC-
   QUEST-ID.md``) proved this IS the general wire shape (actor qword, u16
   entry count, u16 quest id, u8 descriptor byte) and that 3020 was a server
   policy choice, not a client-side hardcode.

2. **The op1 match.**  ``legacy.parse_quest_operate_vital`` (``current/
   pf_login_game_server_v141.py:3176-3196``) is ALREADY the general decoder
   RE-094 needed - its six fields are exactly the ones RE-094's table names
   at ``+0x14``..``+0x28`` - so this module calls it directly rather than
   re-deriving the same offsets a second time.  ``matches_columbus_dispatch``
   gates on ``quest_id == 3021`` and the operation byte only; RE-094's result
   explicitly criticised the existing 3020 lane's exact-tuple match as having
   "no room for another NPC or another quest to pass through", so this does
   not repeat that over-narrowing onto the fields RE-094 could only call
   opaque.

WHAT IS EVIDENCED BUT DELIBERATELY REFUSED - TWO GAPS, BOTH NOW CLOSED
BOUNDED-NEGATIVE, NEITHER MEASURED.

    CORRECTION 2026-08-27 ~14:2x (Lane A, mailbox-consumption round kqrlhr).
    Both gaps below used to read "open" - naming a ticket a reader could
    expect to watch move.  Both RE tickets have since CLOSED, and closing did
    not open either gap: ``RE-096`` (``notes_to_chief/20260827_0509_RE-096-
    RESULT-NO-VEHICLE-SEASCENE-CROSSWALK.md``) and ``RE-103``
    (``notes_to_chief/20260827_1321_RE-103-RESULT-NO-STATIC-SEA-ARRIVAL-
    MARKER.md``) are both DONE/BOUNDED-NEGATIVE: the static/gamedata layer
    that this whole tree already treats as its evidence ceiling has been
    searched and does not contain either answer.  Nothing below changes
    behaviour - both refusals still fire, unconditionally, exactly as
    before - this correction only stops a reader from waiting on a ticket
    that already reported back "no answer here."

* **Scene 17 has no pinned player-arrival spawn.**
  ``scenarios/world_scene_registry_001.json``'s scene-17 entry (added round
  8pfksm by Lane A) carries ``spawn: null`` - ``Bg1001.placements.tsv`` has
  only 8 monster-spawn rows, no player marker.  ``world_scene_entry.
  resolve_entry`` (the SAME entry point CORE-REQUEST-003/004 already wired at
  login, and the one RE-077 - DONE, T0-T4 pinned - names as the correct wire
  for moving an already-live character too) refuses any non-home destination
  with no pinned spawn by raising ``SceneEntryRefused(REFUSED_NO_PINNED_
  SPAWN, ...)``.  Reusing it here means the teleport half of this request
  fails CLOSED on real evidence rather than inventing an XYZ nobody
  measured.  ``RE-103`` confirmed this is not an oversight: it re-checked
  ``Bg1001``'s ``.gat``/``.dmc`` files (identical across all seven sea
  scenes, so no differentiated arrival datum exists there either) and the
  land-scene control case that DOES have a marker crosswalk
  (``SCENE_NAME.n_MARKER -> MARKER.n_ID -> n_SCENE``), and found no
  equivalent for scenes 17-23.  Its own words: "TELEPORT-TARGET-OWNS-XYZ" -
  the only place this coordinate can come from is an attended capture of a
  live Teleport frame, which nobody has run for scene 17.  This module keeps
  refusing until that capture happens; RE-103 closing bounded-negative is
  the evidence ceiling being reached, not a step toward an answer appearing
  in a table.

  CLOSED (PROVISIONALLY) 2026-08-27T14:45+07:00, APPENDED RATHER THAN
  EDITED SO THE PARAGRAPH ABOVE STAYS TRUE AS HISTORY.  ``PANYA-DECISION``
  2026-08-27T14:45+07:00 (``pf_bridge/notes_to_chief/20260827_1445_PANYA-
  DECISION-scene17-provisional-arrival-xyz-0-0-0-owner-decree-ka1-B.md``)
  exercised the owner's own authority to decree a PROVISIONAL spawn (0, 0,
  0) for this scene, tagged ``PROVISIONAL-OWNER-DECREE-20260827-1445`` in
  the registry's ``spawn.provenance`` field.  ``resolve_columbus_arrival``
  now SUCCEEDS instead of refusing, and ``world_scene_entry.resolve_entry``
  prints a ``SCENE_ENTRY ... source=PROVISIONAL-OWNER-DECREE-20260827-1445``
  token the moment that spawn is actually used, so a decreed landing is
  never mistaken for a measured one.  This is not a retraction of the
  paragraph above: no player-arrival row has been found in the placements
  table, the decree is the owner's own exception to the no-invented-
  coordinate rule, for this exact scene and value only, and it expires the
  day RE-103 T3 evidence lands (tracked as ``GT-106``, not ``GT-104`` -
  that number is MOB-DEATH-002's, a different ticket).  ``dispatch_
  columbus_quest3021`` below therefore no longer reports this half as a
  refusal reason - see its own docstring's matching update.

* **No wire evidence for what a vehicle-bind message should contain.**
  RE-085 (``notes_to_chief/20260827_0156_RE-085-RESULT-SAME-ACTOR-VEHICLE-
  MODULE.md``) proves the CLIENT mechanism is actor-local (``CGCVehicleModule``
  binds the player's own actor, no separate ship actor) but its own nonclaims
  say plainly: "did not prove which ship model/vehicle row is actually used"
  and "CVehicleVital's qword meaning is not proven enough to name it vehicle
  id/actor id".  ``RE-096`` closed BOUNDED-NEGATIVE, not positive: the
  ``VEHICLE`` table (79 rows) carries no model/type/speed/scene
  column at all - the ship data RE-096 expected to find there
  (``n_SHIP_VELOCITY``, ``s_OUTFIT``) lives in a SEPARATE ``SHIP`` table (17
  rows) that nothing crosswalks to a sea scene or to ``VEHICLE``.  Worse for
  this module specifically: the ``CVehicleVital`` handler itself
  (``0x00710440``) is SHA-pinned as the five bytes ``mov al,1; ret 4`` - it
  does not read the qword, write it anywhere, or look anything up, and zero
  capture frames exist in either direction.  So RE-096 did not just fail to
  name the row; it found the one place that field is read does not read it
  for anything.  Composing a ``CVehicleVital`` frame today would still mean
  inventing the one field RE-085 already said was unproven - CHARTER-02's
  "never invent a row the client's own tables do not have" applies to a wire
  field exactly as much as to a database row, and RE-096 closing did not
  loosen that.

``dispatch_columbus_quest3021`` used to ALWAYS refuse for exactly this reason
- neither evidence gap has a measured value ANYWHERE this project can still
look, per the RE tickets above.  UPDATED 2026-08-27T15:25+07:00
(``PANYA-DECISION`` M2-accept-scene17-entry-without-vehicle-fix-later): the
owner decided this project does not need the vehicle bind's answer today at
all - M2 accepts "arrive at scene 17 as an ordinary character" as its bar,
tagged ``M2-NO-VEHICLE-OWNER-20260827-1525`` - so the function below no
longer attempts the vehicle half, and RE-096's gap stops being something
this dispatch waits on.  It still cannot be composed from evidence this
project has today, and remains undone; the owner chose not to require it for
this milestone, which is a decision about SCOPE, not a claim that the
evidence gap closed.

WHAT THIS MODULE DOES NOT DO.  It does not decide when the vehicle bind
becomes safe to send if a future round wants it after all - RE-096 has
searched the static/gamedata evidence ceiling this project holds and found
no answer there, so unblocking THAT (separately from M2, which no longer
needs it) would take an ATTENDED capture (a live ``CVehicleVital`` frame with
a non-zero handler to observe), not a further static ticket.  It does not
persist anything about this dispatch (no quest-state row, no completion
flag, no rewards) - the teleport is a one-shot wire effect, matching
``FUNCTIONAL_COVERAGE.json``'s ``quest_accept_and_progress`` row, which
stays ``in_progress`` for that reason.  It does not touch
``current/pf_login_game_server_v141
.py`` - every frozen symbol it uses (``qwordtag``, ``u16tag``, ``u8tag``,
``make_runtime_vitals``, ``NPC_CONVERSATION``, ``parse_quest_operate_vital``)
is read through the ``legacy`` module the same way ``legacy_bridge.py``
already reads other frozen symbols, never edited.  It does not invent an
actor identity for Columbus: ``columbus_actor_identity`` raises rather than
guess if BUILD-001's own frozen placement table ever ships without index 1
in it.
"""

from __future__ import annotations

from . import population
from . import world_scene_entry
from .model import Position

# Convention marker.  Not behind a flag: once runtime.py calls this on a
# default boot, it runs for every character who chooses Columbus - the
# refusals inside it are what evidence, not a flag, currently allows through.
production_allowed = True
test_only = False

# Static facts this round's letters verified and this module reuses without
# re-deriving (see the module docstring's citation trail for each).
COLUMBUS_PLACEMENT_INDEX = 1
COLUMBUS_MOBS_N_ID = "156"
COLUMBUS_QUEST_ID = 3021
COLUMBUS_QUEST_OP_DISPATCH = 1
COLUMBUS_DEST_SCENE_ID = 17

# The reason string this module reports when the vehicle bind refuses.  Named
# after the open ticket that would close it, so a console reader knows
# exactly which RE ticket to chase rather than a generic "not implemented".
VEHICLE_BIND_REFUSED_NO_VEHICLE_ROW = "no_re096_vehicle_row_evidence"


class ColumbusActorNotFound(LookupError):
    """This boot's frozen census has no placement at Columbus's index.

    Raised rather than falling back to a guessed identity: BUILD-001's own
    table is the only source this module trusts for "which actor identity is
    Columbus", and an index that has moved or vanished is a fact worth
    surfacing, not papering over.
    """


class ColumbusDispatchRefused(LookupError):
    """Columbus's quest-3021 op1 arrived, and this tree cannot compose the
    reply CORE-REQUEST-014 asks for - named reasons, not a swallowed frame.
    """

    def __init__(self, reasons: tuple[str, ...], message: str):
        if type(reasons) is not tuple or not reasons:
            raise ValueError("a refusal needs at least one named reason")
        super().__init__(message)
        self.reasons = reasons


def columbus_actor_identity(legacy) -> int:
    """The wire actor identity for Columbus on THIS boot's frozen census.

    Reuses ``population.load_port_royal_placements`` - the same validated,
    hash-pinned table ``world_population``'s own census encoder walks - so a
    census-table drift is caught here the same way it is caught there,
    instead of this module carrying a second, silently divergent copy of
    ``0x2000 + index + 1``.
    """
    placements = population.load_port_royal_placements(legacy)
    for placement in placements:
        if placement.placement_index == COLUMBUS_PLACEMENT_INDEX:
            return placement.actor_identity
    raise ColumbusActorNotFound(
        f"no census placement at index {COLUMBUS_PLACEMENT_INDEX} - "
        f"Columbus (MOBS n_ID {COLUMBUS_MOBS_N_ID}) has no actor identity "
        "to bind a conversation to on this boot"
    )


def make_columbus_conversation(legacy, actor_identity: int) -> tuple[bytes, bytes]:
    """One NPCConversation descriptor: Columbus's actor, quest 3021.

    Byte-for-byte the same shape as the frozen ``make_npc_conversation_
    quest3020`` (``current/pf_login_game_server_v141.py:798-804``), read
    here and parameterised on actor identity and quest id instead of
    hardcoded to P0/3020 - see the module docstring for why RE-094 makes
    that generalisation safe rather than invented.
    """
    if type(actor_identity) is not int or actor_identity <= 0:
        raise ValueError("actor_identity must be a positive int")
    payload = (
        legacy.qwordtag(0x32, actor_identity)
        + legacy.u16tag(0x0F, 1)
        + legacy.u16tag(0x12, COLUMBUS_QUEST_ID)
        + legacy.u8tag(0x08, 0)
    )
    return legacy.make_runtime_vitals([(legacy.NPC_CONVERSATION, 0, payload)])


def matches_columbus_dispatch(quest_fields: dict) -> bool:
    """Whether one decoded ``QuestOperateVital`` frame is Columbus's op1/3021.

    ``quest_fields`` is whatever ``legacy.parse_quest_operate_vital`` (the
    already-general decoder, see the module docstring) returned.  Only quest
    id and the operation byte gate the match - RE-094 could only call the
    remaining fields opaque/default-0 in the one path it observed, and
    refusing on them would repeat the over-narrow exact-tuple match RE-094's
    own result criticised in the existing 3020 lane.
    """
    if type(quest_fields) is not dict:
        return False
    return (
        quest_fields.get("quest_id") == COLUMBUS_QUEST_ID
        and quest_fields.get("field_u8_16") == COLUMBUS_QUEST_OP_DISPATCH
    )


def resolve_columbus_arrival(*, registry=None, emit=print):
    """What ``world_scene_entry.resolve_entry`` says about arriving at scene
    17 - or the ``SceneEntryRefused`` it raises today, letting that speak for
    itself rather than reporting a second time.

    Reuses ``world_scene_entry.resolve_entry`` - the SAME call CORE-REQUEST-
    003/004 already wired at login, not a second scene-transition path -
    because RE-077 (DONE: T0-T4 pinned, ``current/pf_login_game_server_v141
    .py``-independent client sequence StateRunTime/Navigation -> TeleportVital
    -> cStateSwitchScene -> SCENE_NAME lookup) names ``TeleportVital`` as the
    correct wire for moving an ALREADY-LIVE character too, so the encoder
    that already ships is the right one here as well.  ``stored`` is
    synthetic (there is no persisted "the player is standing in scene 17"
    row - they are not there yet) with home's own zero XYZ; this only matters
    if scene 17 ever gains ground evidence, at which point rule 2 of
    ``resolve_entry``'s own docstring decides what happens to it, not this
    call site.

    ROUND 0z3kjx ADVERSARY FIX, READ ALONGSIDE THE ABOVE.  Making
    ``resolve_entry`` succeed for scene 17 also made it succeed for ANY
    caller of ``resolve_entry`` - including ``runtime.py``'s login path,
    which calls the same function with whatever ``scene_id`` a character's
    persisted row happens to carry, and which nothing in this schema stops
    from ever being 17.  The registry's ``login_entry_allowed: false`` for
    scene 17 and the ``via_login=False`` passed below together keep that
    login path refusing a stored scene-17 row exactly as before, while this
    function - the one place that is supposed to resolve the decree - still
    can.  See ``world_scene_entry.resolve_entry``'s own docstring for the
    full mechanism.  ``via_login=False`` is safe here specifically because
    ``synthetic_stored`` above is built fresh every call and never loaded
    from a database - this is the one caller in this tree entitled to
    resolve scene 17 despite the registry's login restriction on it.
    """
    synthetic_stored = Position(COLUMBUS_DEST_SCENE_ID, 0, 0.0, 0.0, 0.0, 0.0)
    return world_scene_entry.resolve_entry(
        synthetic_stored, registry=registry, emit=emit, via_login=False,
    )


M2_NO_VEHICLE_TAG = "M2-NO-VEHICLE-OWNER-20260827-1525"


def dispatch_columbus_quest3021(*, registry=None, emit=print):
    """The compound action CORE-REQUEST-014 asked for was bind-vehicle-then-
    teleport; what M2 actually ships today, by owner decree, is teleport
    alone.

    UPDATED 2026-08-27T15:25+07:00 (``PANYA-DECISION`` M2-accept-scene17-
    entry-without-vehicle-fix-later, answering the exact question the
    14:45 decree and the 12:15 CHIEF-STATUS both left open): the owner
    accepted "talk to Columbus -> arrive at scene 17 as an ordinary
    character, not a ship" as M2's bar for today, tagged
    ``M2-NO-VEHICLE-OWNER-20260827-1525``, explicitly deferring the vehicle
    transform to a later round.  RE-096's own gap (no wire evidence for a
    ``CVehicleVital`` payload -- see the module docstring) is therefore no
    longer this function's problem to solve before it can succeed; it is
    simply not attempted.

    SUCCEEDS TODAY, RETURNING THE ``SceneEntry``, IF THE SCENE-17 ARRIVAL
    ITSELF SUCCEEDS.  The only way this still raises is if
    :func:`resolve_columbus_arrival` itself raises -- e.g. the scene-17
    pin or its provisional decree is ever removed from the registry
    without a replacement.  Reasons stay a tuple (rather than switching
    return shape) for exactly that case, so a caller's existing
    ``except ColumbusDispatchRefused`` handling keeps working unchanged.
    """
    try:
        entry = resolve_columbus_arrival(registry=registry, emit=emit)
    except world_scene_entry.SceneEntryRefused as error:
        reason = f"scene17_teleport_refused_{error.reason}"
        raise ColumbusDispatchRefused(
            (reason,),
            "Columbus quest 3021 op1 dispatch cannot complete yet: " + reason,
        ) from error
    emit(
        "COLUMBUS_QUEST3021_NO_VEHICLE_DISPATCH scene=17 source="
        + M2_NO_VEHICLE_TAG
    )
    return entry
