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

  LOGIN-PATH GAP, CLOSED 2026-08-27 (round 0z3kjx, pf-adversary-flagged,
  rebased onto e0daaa's shipped decree+ground merge).  Making scene 17
  resolve here also made it resolve for ANY caller of ``world_scene_entry.
  resolve_entry`` - including ``runtime.py``'s login path, which calls the
  same function with whatever ``scene_id`` a character's persisted row
  happens to carry.  Nothing in the DB schema stops that row from ever
  naming 17, and nothing before this fix would have refused it once this
  scene had a spawn.  Closed with two additions, neither touching
  ``runtime.py``: the registry's ``login_entry_allowed: false`` for scene 17
  (``world_scene_registry_001.json``), and ``resolve_entry``'s own
  ``via_login`` parameter, which defaults to the login path's answer (fail
  closed) so the unmodified login call site stays safe for free.
  ``resolve_columbus_arrival`` below is the one sanctioned door through it,
  passing ``via_login=False`` explicitly because its own ``stored`` row is
  synthetic and never a character's persisted position.

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

OPTION 2 ADDED, PURELY ADDITIVE.  ``COO-DECISION`` 2026-08-27T17:46+07:00
(``pf_bridge/notes_to_chief/20260827_1746_COO-DECISION-M2-not-closed-fix-
persistence-and-destination-scene-before-passing.md``) reopens GT-106 (4).1
(``pf_bridge/notes_to_chief/20260827_1710_GT106-RESULT-...-ka1-B.md``):
Port Royal's real Columbus (MOBS ``n_ID=156``) has a second entry in its own
``s_QUEST_BEGIN`` list -- ``111;998;3021;3205;7062;7063`` -- read straight
from the committed ``CONSTDATA_TH__MOBS.tsv`` row this module already trusts
for quest 3021.  Quest 3205 is ``Q_BORNAGAIN`` (``QUESTDATA_TH__QUEST.tsv``),
Thai label "tang than tap thi Port Royal" (save Port Royal as spawn point),
with ``n_VARI_2=1`` which the original client's Lua reads as
``Player.ResetMarker(1)`` -- a spawn/marker-save action, not a scene
teleport, and it does not touch the scene-17-vs-126 destination question the
same COO-DECISION assigns to a separate lane GM/RE ticket ("ham dao" - do
not guess).

Added below, all purely additive -- nothing about quest 3021's existing
wire shape or dispatch outcome changes:

* ``make_columbus_conversation_two_options`` -- the SAME per-entry byte
  layout ``make_columbus_conversation`` already emits (factored out as
  ``_conversation_entry`` so neither copies the other), with a second entry
  for quest 3205 appended and the entry count raised from 1 to 2.
  ``make_columbus_conversation`` itself is untouched byte-for-byte (see its
  own tests) and stays the encoder for a single-option descriptor.
* ``matches_columbus_bornagain_dispatch`` -- ``matches_columbus_dispatch``
  generalised with an optional ``quest_id`` (default unchanged at 3021, so
  every existing 1-argument call site keeps its exact old behaviour) and a
  thin wrapper naming quest 3205.
* ``dispatch_columbus_quest3205`` -- refuses every time, with a named
  reason, because no persisted column for a player-chosen respawn scene
  exists anywhere in this project's schema and no wire frame for a
  ``Player.ResetMarker`` acknowledgement has ever been captured.  Composing
  either would invent a row or a frame CHARTER-02 forbids inventing; see the
  function's own docstring and the round handoff for the RE/CORE-REQUEST
  tickets this refusal opens instead.

Wiring either new function into the live ``ChooseNPC``/``QuestOperateVital``
dispatch loop in ``runtime.py`` is NOT done here -- that file is the
chief's, not this lane's -- see the round handoff's ``CORE-REQUEST`` for the
exact one-line hook needed.
"""

from __future__ import annotations

from . import population
from . import world_m2_crossing_handoff
from . import world_m2_return_leg
from . import world_population_handoff
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
# ID SPACE, STATED BECAUSE A RULING REQUIRES IT (COO-DECISION 2026-08-29
# 14:44, "var2 attended test before any flip", item 4: a destination module
# must say whether its number is a ``SCENE_NAME.n_ID`` or a ``MARKER.n_ID``,
# and a value legal in both spaces may not be labelled measured until a
# control exists that the rival reading answers differently and wrong).
#
#     17 is read here as ``CONSTDATA_TH__SCENE_NAME.n_ID`` - the scene id -
#     taken from ``QUESTDATA_TH__QUEST`` row 3021's ``n_VARI_2``.
#     [CONTESTED, NOT MEASURED] The rival reading is ``MARKER.n_ID``, under
#     which the same 17 resolves to ``MARKER[17].n_SCENE = 126`` at
#     (3050, 232, 90).  Both readings are legal for this value; the
#     discriminating control does not exist in any table, which is why the
#     COO ruled it goes to an attended test rather than to another
#     re-reading.  Until that result: this constant stays 17, by
#     COO-DECISION 20260829_0441, and NOBODY MAY FLIP IT FROM A TABLE.
COLUMBUS_DEST_SCENE_ID = 17

# Option 2, added 2026-08-27 per COO-DECISION-M2-not-closed and GT-106 (4).1
# (see the module docstring's "OPTION 2 ADDED" section for the full
# citation).  Quest 3205 = Q_BORNAGAIN, n_VARI_2=1 -> Player.ResetMarker(1),
# a spawn/marker-save action, not a scene teleport - it deliberately shares
# no destination-scene constant with quest 3021 above.
COLUMBUS_QUEST_BORNAGAIN_ID = 3205
COLUMBUS_QUEST_BORNAGAIN_MARKER_ID = 1
# Thai label transliterated for this file per this round's ASCII-only-in-
# code constraint (see GT-106 4.1 / round handoff for the original Thai
# string, kept out of src/ here on purpose): "save Port Royal as spawn
# point". Documentation only, never rendered on a console.
COLUMBUS_QUEST_BORNAGAIN_LABEL_TH_TRANSLIT = "tang than tap thi Port Royal"

# The reason string this module reports when the vehicle bind refuses.  Named
# after the open ticket that would close it, so a console reader knows
# exactly which RE ticket to chase rather than a generic "not implemented".
VEHICLE_BIND_REFUSED_NO_VEHICLE_ROW = "no_re096_vehicle_row_evidence"

# The reason string this module reports when the quest-3205 marker-save
# refuses.  See dispatch_columbus_quest3205's own docstring for why no
# persisted column or wire ack exists yet for this action.
BORNAGAIN_MARKER_RESET_REFUSED_NO_PERSISTENCE_ROW = (
    "no_home_marker_persistence_row_evidence"
)


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


def _conversation_entry(legacy, quest_id: int, descriptor_byte: int = 0) -> bytes:
    """One quest entry's bytes within an NPCConversation descriptor.

    Factored out so ``make_columbus_conversation`` (below) and
    ``make_columbus_conversation_two_options`` (option 2, added 2026-08-27)
    repeat the exact same per-entry layout instead of one copying the other.
    Per ``make_npc_conversation_quest3020``'s own docstring (``current/
    pf_login_game_server_v141.py:782-804``): NPCConversation serializer
    0x622F10 calls the nested descriptor serializer 0x606890 once for EACH
    entry the u16 count names, and that nested serializer writes qid/+0x10
    as a tagged u16 then +0x12 as a tagged u8 (factory 0x622130 initialises
    the latter to zero) - the exact two fields this helper emits, in that
    order, for whichever quest id and descriptor byte it is given.
    """
    return legacy.u16tag(0x12, quest_id) + legacy.u8tag(0x08, descriptor_byte)


def make_columbus_conversation(legacy, actor_identity: int) -> tuple[bytes, bytes]:
    """One NPCConversation descriptor: Columbus's actor, quest 3021 ONLY.

    Byte-for-byte the same shape as the frozen ``make_npc_conversation_
    quest3020`` (``current/pf_login_game_server_v141.py:798-804``), read
    here and parameterised on actor identity and quest id instead of
    hardcoded to P0/3020 - see the module docstring for why RE-094 makes
    that generalisation safe rather than invented.

    UNCHANGED, BYTE-FOR-BYTE, by the 2026-08-27 option-2 addition below (see
    ``tests/test_columbus_quest_dispatch.py``'s
    ``test_matches_the_general_wire_shape_re094_pinned`` for the pin) - this
    function stays the single-option encoder; ``make_columbus_conversation_
    two_options`` is the new, separate, two-option one.
    """
    if type(actor_identity) is not int or actor_identity <= 0:
        raise ValueError("actor_identity must be a positive int")
    payload = (
        legacy.qwordtag(0x32, actor_identity)
        + legacy.u16tag(0x0F, 1)
        + _conversation_entry(legacy, COLUMBUS_QUEST_ID)
    )
    return legacy.make_runtime_vitals([(legacy.NPC_CONVERSATION, 0, payload)])


def make_columbus_conversation_two_options(
    legacy, actor_identity: int,
) -> tuple[bytes, bytes]:
    """One NPCConversation descriptor: Columbus's actor, TWO entries - quest
    3021 (existing, unchanged ordering/bytes) then quest 3205 (Q_BORNAGAIN,
    option 2, added 2026-08-27 per COO-DECISION-M2-not-closed and GT-106
    (4).1 - see the module docstring's "OPTION 2 ADDED" section for the full
    citation trail).

    PURELY ADDITIVE relative to ``make_columbus_conversation``: same actor
    qword, same per-entry layout (``_conversation_entry``, shared with that
    function so this is not a second, silently divergent copy of the wire
    shape), just ``u16tag(0x0F, 2)`` instead of 1 and a second entry
    appended.  Quest 3205's descriptor byte is 0, the same factory default
    quest 3021's entry already carries - no evidence anywhere suggests a
    non-zero byte for this or any other conversation entry.

    Quest 3205 is a marker-save action (``Player.ResetMarker(1)``), not a
    scene teleport, and composing this descriptor decides nothing about the
    scene-17-vs-126 destination question a separate lane GM/RE ticket is
    chasing per the same COO-DECISION.
    """
    if type(actor_identity) is not int or actor_identity <= 0:
        raise ValueError("actor_identity must be a positive int")
    payload = (
        legacy.qwordtag(0x32, actor_identity)
        + legacy.u16tag(0x0F, 2)
        + _conversation_entry(legacy, COLUMBUS_QUEST_ID)
        + _conversation_entry(legacy, COLUMBUS_QUEST_BORNAGAIN_ID)
    )
    return legacy.make_runtime_vitals([(legacy.NPC_CONVERSATION, 0, payload)])


def matches_columbus_dispatch(
    quest_fields: dict, quest_id: int = COLUMBUS_QUEST_ID,
) -> bool:
    """Whether one decoded ``QuestOperateVital`` frame is Columbus's op1 for
    ``quest_id`` (default 3021, the pre-existing single-option lane).

    ``quest_fields`` is whatever ``legacy.parse_quest_operate_vital`` (the
    already-general decoder, see the module docstring) returned.  Only quest
    id and the operation byte gate the match - RE-094 could only call the
    remaining fields opaque/default-0 in the one path it observed, and
    refusing on them would repeat the over-narrow exact-tuple match RE-094's
    own result criticised in the existing 3020 lane.

    ``quest_id`` PARAMETER ADDED 2026-08-27 (option 2 / quest 3205), DEFAULT
    UNCHANGED.  Every pre-existing 1-argument call site (``matches_columbus_
    dispatch(fields)``) keeps matching exactly quest 3021 exactly as before;
    this generalisation only exists so ``matches_columbus_bornagain_
    dispatch`` below can reuse this same gating logic for quest 3205 instead
    of duplicating it.
    """
    if type(quest_fields) is not dict:
        return False
    return (
        quest_fields.get("quest_id") == quest_id
        and quest_fields.get("field_u8_16") == COLUMBUS_QUEST_OP_DISPATCH
    )


def matches_columbus_bornagain_dispatch(quest_fields: dict) -> bool:
    """Whether one decoded ``QuestOperateVital`` frame is Columbus's option
    2 / op1 for quest 3205 (Q_BORNAGAIN, added 2026-08-27).

    Thin wrapper around ``matches_columbus_dispatch`` naming
    ``COLUMBUS_QUEST_BORNAGAIN_ID`` - see that function's own docstring for
    why gating on quest id + the op byte alone, and not the remaining
    opaque fields, is the same reuse RE-094 already validated for quest
    3021, not a new, unproven pattern invented for this quest.
    """
    return matches_columbus_dispatch(
        quest_fields, quest_id=COLUMBUS_QUEST_BORNAGAIN_ID,
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

    ``via_login=False``, ROUND 0z3kjx, pf-adversary-flagged.  Making
    ``resolve_entry`` succeed for scene 17 (the owner's provisional spawn
    decree, above) also made it succeed for ANY caller of ``resolve_entry`` -
    including ``runtime.py``'s login path, which calls the exact same
    function with whatever ``scene_id`` a character's persisted row happens
    to carry, and which nothing in this schema stops from ever being 17. The
    registry's ``login_entry_allowed: false`` for scene 17 and the
    ``via_login=False`` passed below together keep that login path refusing a
    stored scene-17 row exactly as it did before this scene had a spawn at
    all, while this function - the one sanctioned door to the decree - still
    resolves it: ``synthetic_stored`` above is built fresh every call and is
    never a character's own persisted row, which is exactly the case
    ``via_login=False`` exists to name.
    """
    synthetic_stored = Position(COLUMBUS_DEST_SCENE_ID, 0, 0.0, 0.0, 0.0, 0.0)
    return world_scene_entry.resolve_entry(
        synthetic_stored, registry=registry, emit=emit, via_login=False,
    )


M2_NO_VEHICLE_TAG = "M2-NO-VEHICLE-OWNER-20260827-1525"


def _emit_arrival_stowaways(entry, *, legacy, held_indices, emit):
    """Print who the client is still holding at the point this boat lands.

    Report only, and it cannot raise: every path here ends in a printed
    line, including the one where ``entry`` itself is the wrong shape.  That
    matters more than the usual amount because the caller is on the frame
    path with no ``except`` of its own - see the module ``dispatch``
    function's own docstring.
    """
    try:
        fields = tuple(entry.teleport_fields)
        anchor = (float(fields[2]), float(fields[3]), float(fields[4]))
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as failure:  # noqa: BLE001 - report-only, see docstring
        # ``_console_safe`` on the class NAME, not only on the message:
        # Python 3 allows non-ASCII identifiers, so an exception class named
        # in Thai raises UnicodeEncodeError inside ``print`` on the cp874
        # bridge console - outside this try, in the one line of this feature
        # that used to skip the escaping every other line goes through
        # (pf-adversary, round 2pdf6j, D7).
        emit(
            "WORLD_POP_STOWAWAYS unmeasured reason=no_arrival_anchor:"
            + type(failure).__name__.encode("ascii", "backslashreplace").decode("ascii")
        )
        return
    if legacy is None:
        # NOT a failure and deliberately not silent.  The call site in
        # runtime.py does not pass the frozen module or the membership
        # today, so the honest answer is "nobody asked the table", printed
        # in the same field shape as the measured line so one grep catches
        # both states.
        emit(
            "WORLD_POP_STOWAWAYS unmeasured reason=call_site_passed_no_legacy "
            "anchor=({0:.3f},{1:.3f},{2:.3f})".format(*anchor)
        )
        return
    view = world_population_handoff.stowaways_on_crossing(
        legacy, held_indices, anchor,
    )
    emit(world_population_handoff.stowaway_console_line(view))


def dispatch_columbus_quest3021(*, registry=None, emit=print, legacy=None,
                                held_indices=None, departed_from=None,
                                crossing_handoff_dispatched=False):
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

    ROUND 2pdf6j (LANE-A, M2) ADDS ONE REPORT LINE AND NO FRAME.  A player
    who takes this boat keeps the actor collection they were sent at login -
    nothing in this crossing replaces it (``world_population_handoff``'s
    module docstring, "the town follows you out of it") - and until this
    round nothing anywhere said WHO that leaves standing around them.  Now
    the crossing prints it.  ``legacy`` and ``held_indices`` are OPTIONAL and
    default to the call site as it stands today, which has neither to hand:
    without them the line still prints, saying it is unmeasured and why, so
    the console never goes quiet about a question it cannot answer.  ~~The
    one-token change that turns it into names and distances -
    ``legacy=legacy, held_indices=self.world_census_indices`` at
    ``runtime.py``'s existing call - is this round's CORE-REQUEST to
    chief.~~ LANDED (chief, round R229/qb70g2, ``runtime.py``'s
    ``_dispatch_columbus_quest3021`` now passes both at its call to
    ``dispatch_columbus_quest3021`` below).  Struck rather than deleted:
    accurate when written, and a reader who still believes it would go
    looking for a CORE-REQUEST that already landed instead of reading the
    live call site.  ``departed_from`` (see the parameter of the same name
    on this function) landed the same way, one CORE-REQUEST later.

    NOTHING HERE DECIDES ANYTHING.  No refusal reads this line, the wire is
    untouched, the returned ``SceneEntry`` is untouched, and a failure inside
    the report cannot reach the caller: it goes through
    ``stowaways_on_crossing``.

    NOT "purely additive", THOUGH, AND THE DIFFERENCE IS WORTH THE SENTENCE
    (pf-adversary, round 2pdf6j, D8): ``runtime.py``'s ``emit`` both prints
    AND appends to ``self.events``, which is the ``--export-events``
    evidence stream.  So every quest-3021 dispatch now records one more
    event than it did yesterday.  Nothing asserts that sequence today; a
    round that starts asserting it should know this line is in it.
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
    _emit_arrival_stowaways(entry, legacy=legacy, held_indices=held_indices,
                            emit=emit)
    # The way back, named at the moment the way out is taken (LANE-A round
    # mcxexp).  Report only, never raises, and it changes nothing that is
    # sent: see world_m2_return_leg's docstring for the three things it does
    # not claim.  ``departed_from`` is the row this character was standing on
    # in Port Royal; the call site does not pass it yet, and the line says so
    # in the same field shape as the measured one rather than going quiet.
    emit(world_m2_return_leg.return_leg_console_line(
        entry, departed=departed_from, registry=registry))
    # THE POPULATION HANDOFF THIS CROSSING OWES AND DOES NOT SEND.  Composed
    # here, on the default path, for every crossing -- see
    # ``world_m2_crossing_handoff``'s docstring for the two independent
    # sources (this lane's own WORLD_POP_STOWAWAYS line, and RE-162 Job 4)
    # that found the same gap from opposite directions.  For scene 17 the
    # answer is a 27-byte CLEAR in slot ``before_teleport``; the whole of
    # Port Royal is on the client until something queues it.
    #
    # REPORT ONLY, TODAY.  The bytes exist on this line and go nowhere: this
    # function returns a ``SceneEntry`` and the caller in ``runtime.py``
    # composes the outbound action list, so the queueing is a block in the
    # chief's file (this round's CORE-REQUEST).
    #
    # ``crossing_handoff_dispatched`` IS THE ONE-TOKEN FLIP, and it is the
    # same shape the three keywords above it landed by (``legacy=``,
    # ``held_indices=``, ``departed_from=``, each a CORE-REQUEST of its own).
    # It defaults to False because that is currently TRUE - nothing queues
    # these bytes - and it is a parameter rather than a constant so the edit
    # that starts queueing them is also the edit that stops the console
    # claiming otherwise.  A ``dispatched=YES`` printed by a boot that queued
    # nothing would be worse than no line at all.
    #
    # ``held_indices`` is the collection the client is still holding, the same
    # value the stowaway line above reads, so the two lines cannot disagree
    # about the number they are both describing.
    emit(world_m2_crossing_handoff.crossing_handoff_console_line(
        world_m2_crossing_handoff.crossing_handoff(legacy, entry),
        dispatched=crossing_handoff_dispatched,
        held=held_indices,
    ))
    return entry


def dispatch_columbus_quest3205(*, emit=print):
    """Option 2 arriving (op1/quest 3205, Q_BORNAGAIN) -- what this module
    can honestly do with it TODAY: refuse, with a named reason, every time.

    ADDED 2026-08-27 alongside ``make_columbus_conversation_two_options`` /
    ``matches_columbus_bornagain_dispatch`` (see the module docstring's
    "OPTION 2 ADDED" section).  This function is the third piece of that
    trio and intentionally does NOT succeed yet -- unlike quest 3021's
    scene-17 teleport (an established encoder, a decreed destination, and a
    registry pin this module could resolve through ``world_scene_entry``),
    a "save Port Royal as spawn point" action has:

    * no persisted column anywhere in this project's schema for a
      player-chosen respawn scene (grep ``src/pirateforce_foundation`` for
      "home"/"marker"/"spawn" as of this round turns up only unrelated hits
      -- population/monster spawn points, convention-marker comments, and
      this module's own citation of scene-17's missing arrival marker; no
      character-scoped respawn column exists), and
    * no captured wire frame for what, if anything, the client expects back
      after ``Player.ResetMarker`` runs server-side.

    Composing either would mean inventing a row or a frame this project has
    not measured -- CHARTER-02's "never invent a row the client's own
    tables do not have" applies here exactly as it did to RE-096's
    vehicle-bind gap (see the module docstring).  This refuses, every time,
    with a named reason, so a caller has something to catch and a console
    reader has something to grep instead of a silent no-op -- the same
    shape ``dispatch_columbus_quest3021`` had before the scene-17 decree
    closed ITS gap.

    Raises ``ColumbusDispatchRefused`` (reused rather than a third
    exception type, since any future wiring in ``runtime.py`` would want to
    catch quest 3021's and quest 3205's refusals the same way).
    """
    reason = BORNAGAIN_MARKER_RESET_REFUSED_NO_PERSISTENCE_ROW
    emit("COLUMBUS_QUEST3205_BORNAGAIN_REFUSED reason=" + reason)
    raise ColumbusDispatchRefused(
        (reason,),
        "Columbus quest 3205 op1 (Q_BORNAGAIN) dispatch cannot complete "
        "yet: " + reason,
    )
