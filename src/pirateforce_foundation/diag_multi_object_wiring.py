"""LANE-B: the runtime-facing half of ``GT_DIAG_MULTI_OBJECT_WIRING``.

:mod:`mob_diag_multi_object` is the composition layer for GT-114's five
diagnostic objects (D0, D1a, D1b, D2, D3 -- Mountain Deer bodies at the
owner's own test point in bg0001).  It sends nothing and knows nothing about
sessions, by design.  This module is the thin, tested layer between it and
``runtime.py``: every function here is one call the chief's file makes, and
EVERY ONE OF THEM IS A LITERAL NO-OP WHEN THE GATE IS OFF -- that property is
the point of the shape, not a nicety.  ``objects == ()`` (the default for
every account on earth) makes:

* :func:`census_frames` return ``generation.pc, generation.frame`` unchanged,
  the same two objects the caller already had;
* :func:`widen_for_combat` return the caller's own roster and ledger objects;
* :func:`hostile_census_frames` call straight through to
  :func:`mob_death.hostile_census_frames` with the same arguments.

So the three (four, see the adversary note below) call sites can be pasted in
UNCONDITIONALLY, and a login by an account that is not in the allowlist is
byte-for-byte the login that shipped yesterday.
``tests/test_diag_multi_object_wiring.py`` pins each of those three
identities as a test rather than as a claim.

WHY THIS MODULE EXISTS AT ALL, GIVEN runtime.py IS THE CHIEF'S FILE.  Because
the wiring is four call sites in a 5,800-line file this lane may not edit
(v6.3 lane_hooks architecture: "adding a new insertion point in runtime.py is
a chief-owned runtime.py edit"), and because everything ELSE about those four
call sites -- the splice, the widening, the label dispatch, the fail-closed
behaviour -- is testable here without one.  :data:`RUNTIME_WIRING_PATCH`
below is the exact text of the chief's edit; this module is what it calls.

PF-ADVERSARY NOTE, WRITTEN BEFORE ANY OF THIS RAN (the finding that added a
fourth call site to the wiring's own three).  ``_dispatch_mob_combat``
recomposes the WHOLE census on every hit and every kill
(``mob_death.hostile_census_frames``), because RE-092 proved the client's
remote-actor consumer is replace-by-omission.  Two things follow, and both
are failures, not cosmetics:

1. A recompose over the REAL 13-mob roster omits the five diagnostic entries,
   so the first hit on D0 deletes all five objects off the tester's screen --
   including the one being hit, mid-experiment.
2. Worse: once a diagnostic kill is committed into the session's
   ``DeathRegister``, ``mob_death.repopulation_entries`` REFUSES the whole
   recompose by name (``REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER``: "the
   register carries 0x4329 and this roster has no row for them"), the
   surrounding ``except Exception`` degrades to the one-entry frame, and
   RE-092 says that one-entry frame erases the entire town.  Verified by
   execution in ``tests/test_diag_multi_object_wiring.py``
   (``test_real_roster_recompose_refuses_once_a_diag_object_is_dead``), not
   argued.

:func:`hostile_census_frames` here is the fix and it is the same
encoder-reuse rule the rest of this lane follows: the production call,
composed over a wider input set, with the five diagnostic entries appended to
the collection it was going to send anyway.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import diag_multi_object_config
from . import field_mobs
from . import mob_combat
from . import mob_death
from . import mob_diag_multi_object as diag
from . import world_population
from .field_mobs import FieldMob
from .mob_diag_multi_object import DiagObject

# Convention marker only; nothing in this tree branches on it.
production_allowed = True
test_only = False

# The scene these five objects are placed in.  Read from the census module
# the runtime branch itself gates on, not written down as 1, so a drift
# between the two modules cannot leave this gate open in the wrong map.
DIAG_SCENE_ID = world_population.SCENE_ID

# THE OFF PATH IS SILENT, AND THAT IS A MEASURED REQUIREMENT, NOT A STYLE
# CHOICE.  The first draft of this module returned "diag_multi_object_off"
# for an unlisted account and the runtime call site appended it like every
# other event -- which turned every ordinary login's event list into a list
# with one more string in it.  ``tests/test_arena.py::test_wrong_shape_and_no
# _scenario_preserve_boundaries`` pins that list exactly and went red on the
# first run, which is the tripwire working: a diagnostic that is off must be
# INVISIBLE, not merely inert.  So :func:`activate` returns ``event=None``
# for the two ways an ordinary boot arrives here (nobody is listed; no
# account name yet) and a real string only for the states an operator who
# ASKED for the diagnostic needs to see.
EVENT_ACTIVE = "diag_multi_object_active_%d"
EVENT_SCENE_SKIPPED = "diag_multi_object_skipped_scene_%s"
EVENT_LOOKUP_FAILED = "diag_multi_object_config_lookup_failed_%s"
EVENT_CENSUS_REFUSED = "diag_multi_object_census_splice_refused_%s"
EVENT_COMBAT_WIDEN_REFUSED = "diag_multi_object_combat_widen_refused_%s"
EVENT_DEATH_D1B_UNWIRED = "diag_multi_object_d1b_unwired_no_target_vital_state"
EVENT_DEATH_D3_NO_HANDLING = "diag_multi_object_d3_no_death_handling"
EVENT_DEATH_REFUSED = "diag_multi_object_death_refused_%s"

# -------------------------------------------------------------------------
# D1b, AND WHY IT IS DELIBERATELY NOT WIRED THIS ROUND.
# -------------------------------------------------------------------------
# GT_DIAG_MULTI_OBJECT_WIRING point (3) says of D1b: "dead_only_schedule(
# legacy, obj, target_vital_seen=<whatever this dispatch already tracks about
# a prior TargetVital for that identity, if anything does>) -- if nothing
# already tracks that, say so in the reply rather than passing True to get
# past the refusal, since that is the one fact this object exists to test."
#
# NOTHING IN THIS CODEBASE TRACKS IT.  Re-derived at HEAD rather than
# assumed, and the search was made both ways round because the order's phrase
# ("the client has already been SENT a TargetVital") and the wire's own
# direction disagree:
#
#   * SERVER -> CLIENT.  No server-side TargetVital composer exists at all.
#     Every ``TARGET_VITAL`` (0x1ADD) construction in the tree is inside
#     ``current/pf_login_game_server_v141.py``'s own offline self-test
#     fixtures (v141:5818, 6304, 6746, 6919), building CLIENT-shaped frames
#     to assert a parser against.  v141's own console text states the
#     production behaviour it measured: "TargetVital kind 2 gets no response;
#     the client fills target name/HP from local BasicAttr" (v141:7909).  So
#     there is no send to record.
#   * CLIENT -> SERVER.  ``legacy.parse_target_vital`` exists, and
#     ``runtime.py`` reads ``nested_id == legacy.TARGET_VITAL`` in exactly
#     three places: the Columbus conversation dispatch (which asks only whether
#     Columbus's identity is among the frame's ChooseNPC identities and keeps
#     one session-wide boolean, ``columbus_quest3021_conversation_sent``), and
#     two SCENARIO-GATED probe captures (``arena_target_captured``,
#     ``scene_hostile_target_captured``) that latch a single bool for one
#     pinned probe identity and are off on every production boot.  No
#     per-identity set, dict or index of "this client has targeted 0xNNNN"
#     exists on the session or anywhere else.
#
# WHAT WOULD BE NEEDED (one line, for whoever wires it): a per-session set of
# actor identities, written where the inbound ``TARGET_VITAL`` frame is
# already parsed, e.g. ``self.target_vital_identities.add(identity)`` for each
# identity in ``legacy.extract_choose_npc_identities(parsed)`` /
# ``legacy.parse_target_vital(parsed)``; then D1b's call becomes
# ``dead_only_schedule(legacy, obj, target_vital_seen=obj.mob.actor_identity
# in session.target_vital_identities)``.  That is a runtime.py state change,
# so it is a CORE-REQUEST, not something this module can add.
#
# Until then :func:`death_dispatch` returns D1b with no frames and the event
# above.  ``mob_diag_multi_object.dead_only_schedule`` is NEVER called from
# this module with a hard-coded ``True``: passing True would answer D1b's own
# question with a guess, which is the one thing the object exists to prevent.
D1B_UNWIRED_REASON = (
    "D1b needs a per-identity record of a prior TargetVital for this actor on "
    "this connection; no such state exists in this codebase (see this "
    "module's own comment for the search), so dead_only_schedule is left "
    "uncalled rather than called with target_vital_seen=True"
)


class DiagWiringError(RuntimeError):
    """A refusal from this module, always with a reason in the message."""


@dataclass(frozen=True)
class DiagActivation:
    """Whether this connection gets the diagnostic, and the event that says so.

    ``objects`` is empty for every account that is not in the allowlist, for
    every scene that is not bg0001, and for every malformed config -- the
    three ways this can be off -- and the caller distinguishes them by the
    ``event`` string it appends, never by re-deriving them.

    ``event`` is ``None`` exactly when this boot is an ordinary one that was
    never going to get the diagnostic (nobody listed, or no account name yet):
    the caller appends nothing at all in that case, so an ordinary login's
    event list is byte-for-byte the list it was before this feature existed.
    See the comment on :data:`EVENT_ACTIVE` for the test that measured it.
    """

    objects: tuple[DiagObject, ...]
    event: str | None

    @property
    def active(self) -> bool:
        return bool(self.objects)


def activate(
    account_name: Any,
    scene_id: Any,
    *,
    config_path: Any = None,
) -> DiagActivation:
    """Decide once, for this connection, whether the five objects are in play.

    NEVER RAISES.  ``is_diag_multi_object_account`` raises ``ValueError`` by
    design on a malformed config file (see its docstring: a typo must not
    silently resolve to "off" for the operator who made it), and that is the
    right behaviour for a config loader -- but this function is called on the
    census path of EVERY login, so letting it propagate would unwind out of
    the listener thread (v141:7440 has no except) and take the game down for
    every player over one operator's JSON comma.  This is the same
    refuse-by-name-not-by-crash shape ``runtime.py`` already wraps
    ``is_gm_account`` in (CORE-REQUEST-006, pf-adversary round 3lzfhw).
    """
    if not isinstance(account_name, str) or not account_name:
        return DiagActivation((), None)
    try:
        listed = diag_multi_object_config.is_diag_multi_object_account(
            account_name, config_path,
        )
    except Exception as error:  # noqa: BLE001 - fail closed, see docstring
        return DiagActivation(
            (), EVENT_LOOKUP_FAILED % type(error).__name__,
        )
    if not listed:
        return DiagActivation((), None)
    if scene_id != DIAG_SCENE_ID:
        # These five bodies encode scene 1 in every entry
        # (mob_diag_multi_object._control_body -> field_mob_tables.SCENE) and
        # sit at a bg0001 point, so anywhere else they are not merely useless,
        # they are wrong -- the same sentence runtime.py's own
        # world_census_skipped_scene_N branch already stands on.
        return DiagActivation((), EVENT_SCENE_SKIPPED % (scene_id,))
    try:
        objects = diag.diagnostic_objects()
    except Exception as error:  # noqa: BLE001 - fail closed, see docstring
        return DiagActivation((), EVENT_LOOKUP_FAILED % type(error).__name__)
    return DiagActivation(objects, EVENT_ACTIVE % len(objects))


def console_lines(objects: tuple[DiagObject, ...]) -> tuple[str, ...]:
    """One ``DIAG object=...`` line per object, in the order the owner walks
    them -- exactly ``mob_diag_multi_object.describe_boot``, re-exported here
    so the runtime call site imports one module instead of two."""
    return diag.describe_boot(objects)


def _split_entries(generation: world_population.WorldPopulationGeneration
                   ) -> list[bytes]:
    """The per-actor entry bytes of an already-built census, in wire order.

    The same offset walk ``runtime.py:_apply_mob_death_census_override`` and
    ``world_population.apply_identity_override`` both already do, with the
    same whole-collection guard: ``WIRE_HEADER_BYTES`` and ``entry_bytes``
    are read from ``world_population``'s own public constants, never
    re-derived.
    """
    offset = world_population.WIRE_HEADER_BYTES
    entries = []
    for length in generation.entry_bytes:
        entries.append(generation.pc[offset:offset + length])
        offset += length
    if offset != len(generation.pc):
        raise DiagWiringError(
            "generation.entry_bytes does not account for the whole "
            "collection: the diagnostic entries cannot be appended safely"
        )
    return entries


def _encode(legacy: Any, entries: list[bytes]) -> tuple[bytes, bytes]:
    for position, entry in enumerate(entries):
        # An entry that encodes to nothing still counts in the collection's
        # count field, which is the stream-tail misalignment this client
        # answers with ErrorData=28317 (world_population's own words).
        if type(entry) is not bytes or not entry:
            raise DiagWiringError(
                f"entry {position} of the spliced collection is empty")
    pc, frame = legacy.make_runtime_remote_actors(entries)
    if frame != legacy.frame_pc(pc):
        raise DiagWiringError("diagnostic census frame drift")
    return pc, frame


def census_frames(
    legacy: Any,
    generation: world_population.WorldPopulationGeneration,
    objects: tuple[DiagObject, ...],
) -> tuple[bytes, bytes, str | None]:
    """The arrival census, with the five diagnostic entries ADDED to it.

    Returns ``(pc, frame, event_or_None)`` and NEVER RAISES: on any failure it
    returns the caller's own untouched ``generation.pc/frame`` and names the
    refusal, so a diagnostic that cannot compose costs the tester five objects
    and costs the town nothing.  With ``objects == ()`` it returns those exact
    same two objects with no work done at all.

    ADDITIVE, NOT A REPLACEMENT, and composed with the SAME encoder over a
    wider input set: the census's own 115 entries in their own order, then
    D0, D1a, D1b, D2, D3.  ``generation`` itself is NOT modified and must not
    be -- ``generation.actor_count`` (115) is what ``runtime.py`` stores as
    ``self.world_census_actor_count`` and later hands to
    ``build_world_population`` on every recompose, and that function refuses
    any count above ``CENSUS_COUNT``.  A "helpfully" updated 120 there would
    turn every later hit into a compose failure, which RE-092 says empties the
    town.  So the extra bodies live in the BYTES, and the census's own
    bookkeeping keeps counting the census.
    """
    if not objects:
        return generation.pc, generation.frame, None
    try:
        entries = _split_entries(generation)
        for obj in objects:
            entries.append(diag.alive_entry(legacy, obj))
        pc, frame = _encode(legacy, entries)
    except Exception as error:  # noqa: BLE001 - fail closed, see docstring
        return (
            generation.pc, generation.frame,
            EVENT_CENSUS_REFUSED % type(error).__name__,
        )
    return pc, frame, None


def wire_actor_count(pc: bytes) -> int:
    """Read the collection count back out of bytes that are about to be sent.

    ``world_population.wire_actor_count`` does this for a
    ``WorldPopulationGeneration``; the spliced collection is deliberately not
    one of those (see :func:`census_frames`), so the same read is done here
    against the same two public constants.
    """
    if (
        len(pc) < world_population.WIRE_HEADER_BYTES
        or pc[world_population.WIRE_COUNT_TAG_OFFSET]
        != world_population.COLLECTION_TAG
    ):
        raise DiagWiringError(
            "spliced frame does not carry the expected collection header")
    start = world_population.WIRE_COUNT_TAG_OFFSET + 1
    return int.from_bytes(pc[start:start + 2], "little")


def describe_census(
    generation: world_population.WorldPopulationGeneration,
    objects: tuple[DiagObject, ...],
    pc: bytes,
) -> str:
    """The one counted line this lane owes before the frame is queued.

    Counts what was ASSEMBLED and what the client will be TOLD, separately,
    the same distinction ``world_population.census_console_line`` makes and
    for the same reason: those two numbers are the two ways "5 objects" gets
    printed over a frame that carries four.  ASCII only -- the bridge console
    is cp874.
    """
    try:
        wire = wire_actor_count(pc)
    except DiagWiringError:
        wire = -1
    census = len(generation.actor_identities)
    expected = census + len(objects)
    return (
        "DIAG_CENSUS assembled=%d census=%d wire=%d%s pc=%dB identities=%s"
        % (
            len(objects), census, wire,
            "" if wire == expected else " MISMATCH:expected_%d" % expected,
            len(pc),
            ",".join("0x%X" % obj.mob.actor_identity for obj in objects),
        )
    )


def widen_for_combat(
    roster: tuple[FieldMob, ...],
    ledger: Any,
    objects: tuple[DiagObject, ...],
) -> tuple[tuple[FieldMob, ...], Any, str | None]:
    """The roster and the ledger ``_dispatch_mob_combat`` resolves against,
    widened by the five diagnostic identities.

    Point (2) of ``GT_DIAG_MULTI_OBJECT_WIRING``: "the roster
    _dispatch_mob_combat resolves targets against must also resolve these five
    identities while the config is active, so an attack on one reaches
    mob_combat at all".  THE LEDGER IS PART OF THAT SENTENCE even though the
    sentence does not say so, and it is not optional:
    ``mob_combat.attack_from_observed_action`` refuses by name
    (``REFUSE_TARGET_NOT_IN_LEDGER``) for a target that is in the roster and
    not in the ledger -- it calls that case "a roster/ledger desync in which
    every hit on that monster would silently do nothing forever".  Widening
    one without the other would produce exactly that.

    The five rows open at their ceiling (``max_hp``), which is what
    ``mob_combat.open_ledger`` does for every other monster, and they are
    APPENDED rather than merged-and-sorted: ``CombatLedger`` requires ascending
    identity order and refuses rather than silently re-sorting, and this lane
    does not silently re-sort either.  The append is safe because
    ``DIAG_PLACEMENT_BASE`` is 9000 and no real bg0001 placement reaches four
    digits (the roster tops out at 0x2085, the diagnostic five start at
    0x4329) -- and if that ever stops being true, ``CombatLedger``'s own
    ordering refusal fires here and this function fails closed to the
    untouched pair rather than putting a mis-ordered ledger into a live
    session.

    Returns ``(roster, ledger, event_or_None)``.  With ``objects == ()`` it
    returns the caller's own two objects, untouched and unrebuilt.
    """
    if not objects:
        return roster, ledger, None
    try:
        in_ledger = frozenset(ledger.identities())
        in_roster = frozenset(mob.actor_identity for mob in roster)
        wider_roster = list(roster)
        rows = list(ledger.balances)
        for obj in objects:
            mob = obj.mob
            if mob.actor_identity not in in_roster:
                wider_roster.append(mob)
            if mob.actor_identity not in in_ledger:
                rows.append(mob_combat.MobBalance(
                    mob.actor_identity, mob.max_hp, mob.max_hp))
        # THE ROSTER AND THE LEDGER ARE WIDENED INDEPENDENTLY, and that is
        # the whole reason this loop has two membership sets instead of one.
        # ``roster`` arrives fresh from ``field_mobs.load_roster()`` on EVERY
        # frame (13 rows, always), while ``ledger`` is session state that
        # already carries the five diagnostic rows after the first widening.
        # A single "skip if already known" test would therefore stop adding
        # the five to the ROSTER from the second frame onwards -- the second
        # attack of the session would resolve to nothing, silently, and only
        # the first hit would ever work.
        wider_ledger = (
            ledger if len(rows) == len(ledger.balances)
            # ``ledger.scene`` is carried, round jop8ph.  The widened ledger
            # is the SAME session's ledger with the diagnostic rows added,
            # not a new one for a different place -- dropping the scene here
            # would make the first diagnostic widening silently turn a
            # scoped ledger into an unscoped one, and
            # ``mob_ledger_admission`` would then admit it into any scene
            # whose roster it happens to contain.
            else mob_combat.CombatLedger(
                tuple(rows), ledger.generation, ledger.scene)
        )
    except Exception as error:  # noqa: BLE001 - fail closed, see docstring
        return roster, ledger, EVENT_COMBAT_WIDEN_REFUSED % type(error).__name__
    return tuple(wider_roster), wider_ledger, None


def diag_object_for(
    objects: tuple[DiagObject, ...], actor_identity: Any,
) -> DiagObject | None:
    """Which of the five (if any) an identity names.  ``None`` for every real
    census member, which is what makes the death dispatch below a no-op for
    every ordinary kill."""
    for obj in objects:
        if obj.mob.actor_identity == actor_identity:
            return obj
    return None


@dataclass(frozen=True)
class DiagDeathDispatch:
    """What this lane owes for one diagnostic object's death.

    ``step`` is a ``mob_death.DeathStep`` for D0/D1a/D2 and ``None`` for D1b
    (deliberately unwired, see :data:`D1B_UNWIRED_REASON`) and D3 (not
    expected to reach zero HP this round, per the wiring text).  ``event`` is
    always set, so a caller appends one string and never has to work out which
    of the four cases it was in.
    """

    label: str
    step: Any
    event: str

    @property
    def has_frames(self) -> bool:
        return self.step is not None


def death_dispatch(
    legacy: Any,
    obj: DiagObject,
    outcome: Any,
    register: Any,
) -> DiagDeathDispatch:
    """Point (3) of the wiring, dispatched by ``obj.label`` and nothing else.

    D0/D2 -> ``kill_schedule`` (the production ``hold_ms``, 700).
    D1a    -> ``dying_timer_hold_schedule`` (the same call at a 20s hold; the
              frame BYTES are identical to D0's, only the gap differs, which
              is the byte-diff proof RE-107 needs).
    D1b    -> nothing, by design.  See :data:`D1B_UNWIRED_REASON`.
    D3     -> nothing; the wiring text says it is not expected to die.

    Both live calls pass ``DIAG_WIDENED_RULING`` inside
    ``mob_diag_multi_object`` -- this function does not choose a ruling and
    must not: template 27 is covered by exactly one ruling, scoped to bg0001,
    and that is that module's decision to hold.

    NEVER RAISES: ``mob_death.kill`` refuses by name for a dozen good reasons
    (an outcome that is not a kill, an already-dead identity, a ruling that
    does not cover this template), and a diagnostic refusal must degrade to
    "no death frames for this object" exactly the way the real death path's
    own ``mob_death_refused_...`` branch already does -- never to an exception
    crossing back into dispatch.
    """
    label = obj.label
    if label == diag.DIAG_LABEL_DEAD_ONLY_AFTER_TARGET:
        return DiagDeathDispatch(label, None, EVENT_DEATH_D1B_UNWIRED)
    if label == diag.DIAG_LABEL_NO_FACTION_SPLICE:
        return DiagDeathDispatch(label, None, EVENT_DEATH_D3_NO_HANDLING)
    try:
        if label == diag.DIAG_LABEL_DYING_TIMER_HOLD:
            step = diag.dying_timer_hold_schedule(
                legacy, obj, outcome, register)
        else:
            step = diag.kill_schedule(legacy, obj, outcome, register)
    except Exception as error:  # noqa: BLE001 - fail closed, see docstring
        return DiagDeathDispatch(
            label, None, EVENT_DEATH_REFUSED % type(error).__name__)
    return DiagDeathDispatch(
        label, step, "diag_multi_object_death_%s_hold_ms_%d" % (
            label, step.hold_ms),
    )


SKIP_REASON_ZERO_HP_NOT_DEAD = "zero_hp_but_not_in_the_death_register"
SKIP_REASON_NOT_IN_LEDGER = "not_in_this_sessions_combat_ledger"


def _partition_renderable(
    objects: tuple[DiagObject, ...], register: Any, ledger: Any,
) -> tuple[list[DiagObject], list[tuple[DiagObject, str]]]:
    """Split the five into the ones a recompose can render and the ones it cannot.

    THIS IS D1b's OWN SIDE EFFECT AND IT HAD TO BE HANDLED SOMEWHERE.  D1b is
    deliberately left without death handling (see :data:`D1B_UNWIRED_REASON`),
    so the attended tester WILL take it to zero HP -- that is the experiment --
    and it will sit at zero in the combat ledger with no row in the death
    register.  ``mob_death.repopulation_entries`` refuses exactly that pair by
    name (``REFUSE_LEDGER_DISAGREES_WITH_REGISTER``: "identity 0x%X stands at
    0 HP in the ledger and is not in the death register"), and it is right to:
    for a REAL monster, sending a live body would resurrect it and sending a
    corpse would claim a kill nobody committed.

    But that refusal would come back out of the recompose on EVERY LATER HIT
    OF THE SESSION, into ``runtime.py``'s ``except Exception`` fallback, which
    degrades to the one-entry frame RE-092 proved erases the whole town.  So
    one unanswered D1b would cost the tester the rest of the boot.

    The least-wrong answer, and the one this project's own rules pick: leave
    the object OUT of the recomposed census (a smaller world, never a
    fabricated one -- no invented body, no invented corpse, no guessed
    ``target_vital_seen``) and say so on the console, once per frame, by name.
    The client drops that one actor by omission and every other actor,
    diagnostic and real, is unaffected.  The object comes back the moment the
    state that answers D1b exists.
    """
    renderable: list[DiagObject] = []
    stranded: list[tuple[DiagObject, str]] = []
    for obj in objects:
        identity = obj.mob.actor_identity
        try:
            standing = ledger.balance_of(identity).current_hp
        except Exception:  # noqa: BLE001 - any ledger that cannot answer
            stranded.append((obj, SKIP_REASON_NOT_IN_LEDGER))
            continue
        if standing == mob_death.HP_WHEN_DEAD and not register.is_dead(identity):
            stranded.append((obj, SKIP_REASON_ZERO_HP_NOT_DEAD))
            continue
        renderable.append(obj)
    return renderable, stranded


def hostile_census_frames(
    legacy: Any,
    anchor: tuple[float, float, float],
    actor_count: int,
    roster: tuple[FieldMob, ...],
    register: Any,
    *,
    ledger: Any,
    objects: tuple[DiagObject, ...],
    dead_timer: float = mob_death.DEAD_TIMER_SECONDS,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    with_name: bool = True,
    transitioning: tuple[str, int] | None = None,
) -> tuple[bytes, bytes]:
    """``mob_death.hostile_census_frames`` with the five objects kept on screen.

    ``transitioning`` PASSES STRAIGHT THROUGH to ``mob_death.
    hostile_census_frames``/``full_roster_override`` -- CODEX_URGENT
    2026-09-01T20:40+07:00's corpse re-arm fix, approved by COO-DECISION
    2026-09-01T21:48+07:00.  ``None`` (the default) is byte-for-byte the old
    behaviour.

    THE FOURTH CALL SITE (see this module's own PF-ADVERSARY NOTE).  With
    ``objects == ()`` this is a straight pass-through: the same function, the
    same arguments, the same bytes -- pinned by a byte-equality test.

    With the gate on, ``roster`` MUST be the widened roster
    :func:`widen_for_combat` returned, and this composes:

      build_world_population -> full_roster_override -> apply_identity_override

    exactly as ``mob_death.hostile_census_frames`` does (the widened roster is
    what keeps ``repopulation_entries`` from refusing the whole recompose once
    a diagnostic identity is in the register), and then APPENDS the five
    diagnostic entries -- which ``apply_identity_override`` cannot place,
    since those identities are not in the 115-actor census it is splicing
    into, and which it silently leaves out rather than failing on (its own
    documented behaviour for an override key that is not in the generation).

    D3 IS THE ONE ENTRY NOT TAKEN FROM THE OVERRIDE.  ``full_roster_override``
    composes every live body through ``field_mobs.hostile_actor_entry``, i.e.
    WITH the faction splice -- which is the single field D3 exists to
    withhold.  Taking D3's alive body from ``mob_diag_multi_object.alive_entry``
    instead keeps the object diagnostic; the other four take the override's
    entry, so a diagnostic mob that has been damaged or killed re-renders at
    the HP it actually stands at rather than healing back to 1201 on every
    later frame.

    ONE DIAGNOSTIC OBJECT CAN BE DROPPED FROM THE RESULT, LOUDLY: see
    :func:`_partition_renderable` for the "zero HP and no death record" state
    D1b enters the moment it is killed, why rendering it would mean inventing
    either a resurrection or a kill nobody committed, and why dropping that
    one object beats letting the whole recompose refuse.
    """
    if not objects:
        return mob_death.hostile_census_frames(
            legacy, anchor, actor_count, roster, register, ledger=ledger,
            faction=faction, with_name=with_name, dead_timer=dead_timer,
            transitioning=transitioning,
        )
    renderable, stranded = _partition_renderable(objects, register, ledger)
    for obj, reason in stranded:
        # LOUD, NEVER SILENT, and ASCII for the cp874 bridge console.  See
        # _partition_renderable for what this state is and why dropping the
        # object is the least-wrong answer available.
        print(
            "DIAG_CENSUS_SKIPPED object=%s identity=0x%X reason=%s" % (
                obj.label, obj.mob.actor_identity, reason)
        )
    dropped = frozenset(obj.mob.actor_identity for obj, _ in stranded)
    generation = world_population.build_world_population(
        legacy, anchor, actor_count, scene_id=DIAG_SCENE_ID,
        count_source=world_population.COUNT_SOURCE_CALLER,
    )
    override = mob_death.full_roster_override(
        legacy,
        tuple(m for m in roster if m.actor_identity not in dropped),
        register, ledger=ledger, faction=faction,
        with_name=with_name, dead_timer=dead_timer,
        transitioning=transitioning,
    )
    composed = world_population.apply_identity_override(
        legacy, generation, override)
    entries = _split_entries(composed)
    for obj in renderable:
        identity = obj.mob.actor_identity
        if (
            obj.label == diag.DIAG_LABEL_NO_FACTION_SPLICE
            and not register.is_dead(identity)
        ):
            entries.append(diag.alive_entry(legacy, obj))
            continue
        entry = override.get(identity)
        if entry is None:
            raise DiagWiringError(
                "identity 0x%X has no entry in the roster override: "
                "hostile_census_frames was called with the REAL roster, not "
                "the one widen_for_combat returned" % identity
            )
        entries.append(entry)
    return _encode(legacy, entries)


# -------------------------------------------------------------------------
# CORE-REQUEST: the chief's four call sites, verbatim.
# -------------------------------------------------------------------------
# Written here rather than only in a handback letter, the same convention
# mob_death.MOB_DEATH_WIRING and mob_diag_multi_object.
# GT_DIAG_MULTI_OBJECT_WIRING already use: a reader of the module finds the
# wiring next to the functions it calls.  Every line below is inside
# runtime.py's PersistentGameSessionState, and every one of them is a no-op
# for an account that is not in config/diag_multi_object.json (which this
# repository does not ship).
RUNTIME_WIRING_PATCH = r'''
(0) __init__, beside self.mob_combat_ledger / self.mob_death_register:

        # CORE-REQUEST (GT-DIAG-MULTI-OBJECT-001).  Empty for every account
        # that is not in config/diag_multi_object.json, which this repo does
        # not ship: the default is five zero-length tuple reads per session.
        self.diag_multi_objects = ()

(1) the census branch, in the bg0001 `else:` of WORLD-CENSUS-001, AFTER
    `print(world_population.census_console_line(generation))` (so the
    WORLD_CENSUS line keeps describing the 115-actor census it counted) and
    BEFORE `census_actions = [...]`:

                        activation = diag_multi_object_wiring.activate(
                            self.token, scene_id,
                        )
                        if activation.event is not None:
                            self.events.append(activation.event)
                        self.diag_multi_objects = activation.objects
                        census_pc, census_frame = generation.pc, generation.frame
                        if activation.objects:
                            for line in diag_multi_object_wiring.console_lines(
                                activation.objects,
                            ):
                                print(line)
                            census_pc, census_frame, refusal = (
                                diag_multi_object_wiring.census_frames(
                                    legacy, generation, activation.objects,
                                )
                            )
                            if refusal is not None:
                                self.events.append(refusal)
                                self.diag_multi_objects = ()
                            print(diag_multi_object_wiring.describe_census(
                                generation, self.diag_multi_objects, census_pc,
                            ))

    then the two existing census_actions entries use `census_pc, census_frame`
    in place of `generation.pc, generation.frame`.  Their labels keep the
    census count (`generation.actor_count`) so no existing grep moves; the
    DIAG_CENSUS line above carries the +5.

(2) the top of _dispatch_mob_combat, replacing `roster = field_mobs.load_roster()`:

            roster = field_mobs.load_roster()
            roster, self.mob_combat_ledger, widen_refusal = (
                diag_multi_object_wiring.widen_for_combat(
                    roster, self.mob_combat_ledger, self.diag_multi_objects,
                )
            )
            if widen_refusal is not None:
                self.events.append(widen_refusal)

(3) inside `if step.death_due:`, replacing the `mob = next(...)` line and
    wrapping the existing mob_death.kill retry loop:

                mob = next(m for m in roster if m.actor_identity == target)
                diag_obj = diag_multi_object_wiring.diag_object_for(
                    self.diag_multi_objects, target,
                )
                if diag_obj is not None:
                    dispatch = diag_multi_object_wiring.death_dispatch(
                        legacy, diag_obj, step.outcome, self.mob_death_register,
                    )
                    self.events.append(dispatch.event)
                    death_step = dispatch.step
                    if death_step is not None:
                        try:
                            self.mob_death_register = mob_death.commit_death(
                                self.mob_death_register, death_step,
                            )
                        except mob_death.MobDeathContractError as error:
                            # Same per-session caveat as every other
                            # register/ledger retry in this method: not
                            # reachable today.  Refuse by name rather than
                            # send frames for a death this session did not
                            # record.
                            self.events.append(
                                "diag_multi_object_commit_refused_"
                                f"{error.reason}"
                            )
                            death_step = None
                else:
                    <the existing retry loop, unchanged>

(4) THE ADVERSARY FINDING, both recompose call sites in _dispatch_mob_combat
    (MOB_COMBAT_BAR and MOB_DEATH_FRAMES): replace
    `mob_death.hostile_census_frames(` with
    `diag_multi_object_wiring.hostile_census_frames(` and add
    `objects=self.diag_multi_objects,` to each call.  With no diagnostic
    active that call is a byte-identical pass-through (pinned by
    test_hostile_census_frames_passthrough_is_byte_identical); without it,
    the first hit on a diagnostic object erases all five from the client, and
    the first KILL of one makes every later recompose refuse
    (REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER) and fall back to the
    one-entry frame RE-092 proved erases the town.

    Import at the top of runtime.py:
        from . import diag_multi_object_wiring
'''
