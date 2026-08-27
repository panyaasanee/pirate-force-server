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

WHAT IS EVIDENCED BUT DELIBERATELY REFUSED - TWO OPEN GAPS, NOT ONE.

* **Scene 17 has no pinned player-arrival spawn.**
  ``scenarios/world_scene_registry_001.json``'s scene-17 entry (added this
  round by Lane A) carries ``spawn: null`` - ``Bg1001.placements.tsv`` has
  only 8 monster-spawn rows, no player marker.  ``world_scene_entry.
  resolve_entry`` (the SAME entry point CORE-REQUEST-003/004 already wired at
  login, and the one RE-077 - DONE, T0-T4 pinned - names as the correct wire
  for moving an already-live character too) refuses any non-home destination
  with no pinned spawn by raising ``SceneEntryRefused(REFUSED_NO_PINNED_
  SPAWN, ...)``.  Reusing it here means the teleport half of this request
  fails CLOSED on real evidence rather than inventing an XYZ nobody
  measured.  Open ask: an RE runner needs to find scene 17's arrival marker
  (or an owner-attended measurement) before this can complete.

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
  day RE-103 T3 evidence lands (tracked as ``GT-105``, not ``GT-104`` -
  that number is MOB-DEATH-002's, a different ticket).  ``dispatch_
  columbus_quest3021`` below therefore no longer reports this half as a
  refusal reason - see its own docstring's matching update.

* **No wire evidence for what a vehicle-bind message should contain.**
  RE-085 (``notes_to_chief/20260827_0156_RE-085-RESULT-SAME-ACTOR-VEHICLE-
  MODULE.md``) proves the CLIENT mechanism is actor-local (``CGCVehicleModule``
  binds the player's own actor, no separate ship actor) but its own nonclaims
  say plainly: "did not prove which ship model/vehicle row is actually used"
  and "CVehicleVital's qword meaning is not proven enough to name it vehicle
  id/actor id".  RE-096 (open) exists exactly to close that gap.  Composing a
  ``CVehicleVital`` frame today would mean inventing the one field RE-085
  says is unproven - CHARTER-02's "never invent a row the client's own tables
  do not have" applies to a wire field exactly as much as to a database row.

``dispatch_columbus_quest3021`` therefore ALWAYS refuses today (see its own
docstring) - not because the dispatch is unwired, but because two of the
things it would need to send have no measured value yet.  Both are reported,
not merged into one vague refusal, so a human reading the console can tell
which RE ticket to chase.

WHAT THIS MODULE DOES NOT DO.  It does not decide when the vehicle bind or
the teleport becomes safe to send - that is the day RE-096 closes and a scene
17 spawn is measured.  It does not touch ``current/pf_login_game_server_v141
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
    """
    synthetic_stored = Position(COLUMBUS_DEST_SCENE_ID, 0, 0.0, 0.0, 0.0, 0.0)
    return world_scene_entry.resolve_entry(
        synthetic_stored, registry=registry, emit=emit,
    )


def dispatch_columbus_quest3021(*, registry=None, emit=print):
    """The compound action CORE-REQUEST-014 asks for: bind the vehicle, then
    move the player to scene 17.

    STILL ALWAYS REFUSES TODAY, BUT ON ONE GAP NOW, NOT TWO.  UPDATED
    2026-08-27T14:45+07:00: the scene-17 arrival is attempted FIRST (so a
    human reading the console gets whatever ``world_scene_entry`` prints),
    and as of ``PANYA-DECISION`` 2026-08-27T14:45+07:00's provisional spawn
    decree (see the module docstring), that half now SUCCEEDS rather than
    raising - it no longer contributes a reason to ``reasons`` below.  The
    vehicle bind is still refused unconditionally: no wire evidence for its
    payload exists in this tree at all (RE-096, open), so there is no code
    path here that would ever compose it today, evidenced or not.  Never
    partially applies: no frame is queued unless both halves clear, so a
    future evidence close on the vehicle gap still cannot ship a player
    riding nothing or a player stranded mid-transform.
    """
    reasons: list[str] = []
    try:
        resolve_columbus_arrival(registry=registry, emit=emit)
    except world_scene_entry.SceneEntryRefused as error:
        reasons.append(f"scene17_teleport_refused_{error.reason}")
    reasons.append(VEHICLE_BIND_REFUSED_NO_VEHICLE_ROW)
    raise ColumbusDispatchRefused(
        tuple(reasons),
        "Columbus quest 3021 op1 dispatch cannot complete yet: "
        + "; ".join(reasons),
    )
