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

WHAT IS EVIDENCED BUT DELIBERATELY REFUSED - ONE GAP LEFT, ONE RESOLVED BY
OWNER DECREE RATHER THAN BY MEASUREMENT.

    CORRECTION 2026-08-27 ~14:2x (Lane A, mailbox-consumption round kqrlhr).
    Both gaps below used to read "open" - naming a ticket a reader could
    expect to watch move.  Both RE tickets have since CLOSED, and closing did
    not open either gap: ``RE-096`` (``notes_to_chief/20260827_0509_RE-096-
    RESULT-NO-VEHICLE-SEASCENE-CROSSWALK.md``) and ``RE-103``
    (``notes_to_chief/20260827_1321_RE-103-RESULT-NO-STATIC-SEA-ARRIVAL-
    MARKER.md``) are both DONE/BOUNDED-NEGATIVE: the static/gamedata layer
    that this whole tree already treats as its evidence ceiling has been
    searched and does not contain either answer.  At the time of that
    correction neither gap changed dispatch behaviour - both refusals still
    fired, unconditionally.

    CORRECTION 2026-08-27T15:1x+07:00 (Lane A, round 0z3kjx).  The first gap
    below now behaves differently, on evidence a bounded-negative RE ticket
    cannot manufacture: an explicit owner decree
    (``notes_to_chief/20260827_1445_PANYA-DECISION-scene17-provisional-
    arrival-xyz-0-0-0-owner-decree-ka1-B.md``) that exercises a one-time,
    named exception to CHARTER-02's anti-fabrication rule for exactly one
    value at exactly this scene: XYZ=(0,0,0), the owner's own words "not a
    coordinate the team invented, an owner order".  ``scenarios/
    world_scene_registry_001.json``'s scene-17 entry now carries that value,
    tagged with a ``ground_bound_waiver`` citing the decree so the sanity
    check that would otherwise refuse it (the point sits nowhere near this
    ship's own measured z-range, 746-1272; see that file's ``ground`` block)
    stays honest about WHY it did not fire, instead of being silently
    loosened for everyone.  RE-103 itself is unchanged and still open at the
    evidence ceiling: this is the owner overriding that ceiling for one named
    value, not a new measurement closing it.  The decree expires the moment
    RE-103's own T3 (an attended capture) lands a real value - see that
    letter's item 3 - and until then a boot that reaches this point prints
    ``SCENE_ENTRY ... source=PROVISIONAL-OWNER-DECREE-20260827-1445`` so a
    console reader always knows which arrivals used it.

* **Scene 17's player-arrival spawn is a decreed placeholder, not a
  measurement - and the dispatch no longer refuses on it.**
  ``world_scene_entry.resolve_entry`` (the SAME entry point CORE-REQUEST-
  003/004 already wired at login, and the one RE-077 - DONE, T0-T4 pinned -
  names as the correct wire for moving an already-live character too) no
  longer raises ``SceneEntryRefused(REFUSED_NO_PINNED_SPAWN, ...)`` for scene
  17, because the pin now carries a spawn.  ``Bg1001.placements.tsv`` still
  has only 8 monster-spawn rows and no player marker - RE-103 confirmed that
  is not an oversight, re-checking ``Bg1001``'s ``.gat``/``.dmc`` files
  (identical across all seven sea scenes) and the land-scene marker crosswalk
  (``SCENE_NAME.n_MARKER -> MARKER.n_ID -> n_SCENE``) with no equivalent for
  scenes 17-23, and its own words remain true: "TELEPORT-TARGET-OWNS-XYZ" -
  the only place a MEASURED coordinate can come from is an attended capture
  of a live Teleport frame, which nobody has run for scene 17.  What changed
  is that the owner supplied a value through a different door than
  measurement.  ``resolve_columbus_arrival`` below emits the decree's
  required console token whenever it resolves through this value, so
  "measured" and "decreed" never look the same on the console.

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

``dispatch_columbus_quest3021`` therefore STILL ALWAYS refuses today (see its
own docstring) - not because the dispatch is unwired, and no longer because
BOTH halves lack a value, but because the vehicle-bind half has no measured
value ANYWHERE this project can still look, per RE-096 above, and this
module never partially applies (see ``dispatch_columbus_quest3021``'s own
docstring for why).  A boot that reaches this point today prints the scene-17
arrival lines and the decree token, then still refuses on the vehicle-bind
reason alone - one named reason now, not two, and a human reading the
console can see exactly which one.  Whether M2 should ever let a character
enter scene 17 WITHOUT the vehicle bind - i.e. whether these two halves
should stop being one atomic action - is a question already in front of the
owner as of 2026-08-27T15:10+07:00 (``notes_to_chief/20260827_1510_PANYA-
DECISION-M2-skip-Columbus-quest-gate-path-A-...``, item 4: "NOT YET DECIDED",
someone was asking live at the time this correction was written).  This
module does not pre-empt that answer either way: it keeps both halves atomic
until told otherwise, exactly as before this round.

WHAT THIS MODULE DOES NOT DO.  It does not decide when the vehicle bind
becomes safe to send - RE-096 has searched the static/gamedata evidence
ceiling this project holds and found no answer there, so what unblocks that
half is an ATTENDED capture (a live ``CVehicleVital`` frame with a non-zero
handler to observe), not a further static ticket.  It does not decide
whether scene-17 entry and the vehicle bind should ever be split into two
separate actions - see the owner-decision citation above.  It does not touch
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

# The exact citation the scene registry's scene-17 spawn carries in its
# ground_bound_waiver field.  Read back from the resolved destination at
# dispatch time (never hardcoded into a comparison) so a stale copy of this
# string cannot silently diverge from the pin - see resolve_columbus_arrival.
SCENE17_PROVISIONAL_SPAWN_SOURCE = "PROVISIONAL-OWNER-DECREE-20260827-1445"


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
    17 - or the ``SceneEntryRefused`` it would raise for a scene with no
    spawn at all, letting that speak for itself rather than reporting a
    second time.  As of round 0z3kjx scene 17 carries a spawn (an
    owner-decreed placeholder, not a measurement - see the module docstring's
    "CORRECTION 2026-08-27T15:1x" section), so this no longer raises for
    scene 17 specifically; the ``try`` in ``dispatch_columbus_quest3021``
    stays, because a scene this project stops pinning, or a registry fault,
    still needs to be caught by name rather than assumed away.

    SAME-ROUND ADVERSARY FIX, READ ALONGSIDE THE ABOVE.  Making
    ``resolve_entry`` succeed for scene 17 also made it succeed for ANY
    caller of ``resolve_entry`` - including ``runtime.py``'s login path,
    which calls the same function with whatever ``scene_id`` a character's
    persisted row happens to carry, and which nothing in this schema stops
    from ever being 17.  The registry's ``login_entry_allowed: false`` for
    scene 17 and the ``via_login=False`` passed below together keep that
    login path refusing a stored scene-17 row exactly as before, while this
    function - the one place that is supposed to resolve the decree - still
    can.  See ``world_scene_entry.resolve_entry``'s own docstring for the
    full mechanism.

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

    THE EXTRA CONSOLE TOKEN.  PANYA-DECISION 2026-08-27T14:45+07:00 item 2
    requires a printed token distinct from the ordinary ``WORLD_SCENE`` line,
    naming the decree, whenever a resolution actually uses the decreed value
    - "so WIRED v2/a tester can grep it, and so it's known which player
    entered the sea with a temporary coordinate".  This reads the resolved
    destination's ``spawn_ground_bound_waiver`` back from the registry rather
    than assuming scene 17 is the only scene that will ever carry one, so a
    future decreed scene gets the same line for free.
    """
    synthetic_stored = Position(COLUMBUS_DEST_SCENE_ID, 0, 0.0, 0.0, 0.0, 0.0)
    # via_login=False, added round 0z3kjx (adversary-flagged): this call does
    # not read a character's persisted position row - synthetic_stored above
    # is built fresh every call, never loaded from a database - so it is the
    # one caller in this tree entitled to resolve scene 17 despite the
    # registry's login_entry_allowed=False for it.  resolve_entry defaults
    # via_login to True precisely so that runtime.py's OWN call, which never
    # passes this keyword and never will without a runtime.py edit, keeps
    # refusing a stored/persisted scene-17 row exactly as it did before this
    # scene had a spawn at all.
    entry = world_scene_entry.resolve_entry(
        synthetic_stored, registry=registry, emit=emit, via_login=False,
    )
    waiver = entry.destination.spawn_ground_bound_waiver
    if waiver is not None:
        x, y, z = entry.destination.spawn
        emit(
            "SCENE_ENTRY scene={0} xyz={1:g},{2:g},{3:g} source={4}".format(
                entry.destination.n_id, x, y, z, waiver,
            )
        )
    return entry


def dispatch_columbus_quest3021(*, registry=None, emit=print):
    """The compound action CORE-REQUEST-014 asks for: bind the vehicle, then
    move the player to scene 17.

    ALWAYS REFUSES TODAY - but on one named reason now, not the two this
    function reported before round 0z3kjx.  The scene-17 arrival is
    attempted FIRST (so a human reading the console also gets whatever
    ``world_scene_entry`` would have printed, and now also the decree token
    when the placeholder spawn is what resolved), and the vehicle bind is
    refused unconditionally because no wire evidence for its payload exists
    in this tree at all - there is no code path here that would ever compose
    it today, evidenced or not.  ``reasons`` is still a tuple, and a future
    round's registry fault or an unpinned scene would still add a second
    entry to it - this function does not assume scene 17 stays resolvable,
    it observes whether it was.  Never partially applies: no frame is queued
    unless every computed reason clears, so a future evidence close on the
    vehicle-bind gap still cannot ship a player riding nothing.  Whether the
    two halves should ever be split into two separate, non-atomic actions is
    the owner's open question named in the module docstring, not something
    this function decides.
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
