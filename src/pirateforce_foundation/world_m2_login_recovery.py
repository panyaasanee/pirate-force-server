"""The way back IN after a trip - LANE-A, M2.

WHAT A PLAYER GETS BECAUSE OF THIS FILE.  Sail out of Port Royal, arrive on
the island, close the client, log back in -- and today the client parks on
"connecting" forever and that character is gone.  Not slow, not misplaced:
gone, because the only row that says where it stands names a scene the login
door is pinned shut against, and the only thing that could rewrite that row
is a login.  With this module wired the same character comes back ASHORE, at
the row it sailed from when the caller kept one and at the Port Royal pin
when it did not, and its console says which of the two it used.

WHY THIS IS LANE-A's TO ANSWER AND NOT THE RUNTIME's.  chief measured the
brick end to end and wrote it up in ``notes_to_chief/20260908_0622_FROM_
CHIEF_R399-to-LANE-A-*`` (R399 sections 1-2): the M2 seam's three
destinations are markers 17/343/345 -> scenes 126/304/305, all three carry
``login_entry_allowed: false``, chief put the G1 scene relabel in and TOOK IT
BACK OUT the same round because the durable row that follows it refuses the
next login permanently.  chief's own words: "the question that needs an
owner, before M2 can go anywhere, is WHERE SHOULD A PLAYER STAND WHEN THEY
LOG BACK IN FROM THE SEA -- who owns the return ticket", and "I do not
appoint owners for other lanes".  It is a question about what the world
MEANS, not about a socket, so this lane answers it here, in this lane's own
file, with the runtime untouched.

THE ANSWER, IN ONE LINE: A RECOVERY IS A VISIT, NOT A MOVE.  That is not a
new principle invented here - it is the sentence ``runtime.py`` already
carries at its ``login_scene_override_visit`` branch (chief R399 section 2),
for this exact class of scene, and ``COO-DECISION 20260828_2130`` already
settled the general rule (the owner of a position is what the client
confirms; a frame leaving the server is a request; the durable write happens
at the first ``TargetPos`` after it).  So this module composes an arrival and
sets ``durable_write_allowed = False``: nothing here writes, and the stale
row heals itself at the first position the recovered character reports.  A
player who logs in twice without moving gets recovered twice, which is
correct and cheap; a player who takes one step is back to a row that agrees
with where they are.

WHAT THIS MODULE REFUSES TO DO, AND THE FAILURE IT IS REFUSING.

1. IT RECOVERS TWO REFUSAL REASONS, AND DECLINES TWO.  ``scene_not_pinned``
   and ``scene_has_no_pinned_spawn`` are DECLINED BY NAME, and the reason is a
   failure scenario rather than a preference.  A shut door is a deliberate,
   pinned property of a scene this tree KNOWS - four scenes today (17, 126,
   304, 305), derived below, not typed in.  The other three reasons all mean
   "the registry does not describe this row's scene", which is exactly what a
   half-written, swapped or truncated registry file looks like to every
   character at once.  Recovering those would answer one bad deploy by
   walking the WHOLE population to Port Royal and then, at each player's
   first step, healing their durable rows to it - a mass position wipe with
   no undo, arriving through a door opened to prevent a single brick.  The
   refusal stands for those, and the console says which reason it stood for.

2. IT NEVER INVENTS AN ARRIVAL.  The ashore row is resolved through
   ``world_scene_entry.resolve_entry(..., via_login=True)`` - the same door,
   asked the same question - and if THAT refuses too, this module reports no
   recovery rather than composing an entry the door never admitted.  A
   recovery that skips the door is a second, weaker door.

3. IT HOLDS NO STATE.  No registry of its own, no per-session anything, no
   module-level mutable.  ``TWO_SESSIONS_SAME_SCENE``: two sessions
   recovering into the same scene are two calls with no shared object
   between them, and neither can see or disturb the other's result; what
   they arrive INTO is ``world_scene_registry``'s shared world, which this
   file does not touch.

4. IT DOES NOT SEND, WRITE, OR SCHEDULE ANYTHING.  It returns a value and
   a console line.  ``runtime.py``, ``app.py`` and the v141 login server are
   the chief's files and this lane does not edit them.

THE PLUG SITE, AND THE HALF THE FIRST DRAFT OF THIS FILE GOT WRONG.  The
site is already written and already catches the right exception:
``runtime.py``'s ``except world_scene_entry.SceneEntryRefused as exc:``
handler inside the login path - the one whose own comment says "this is the
deliberate handler that class asks for: print the reason, refuse the login by
name".  Between printing the reason and ``return []``:

    recovery = world_m2_login_recovery.try_recovery_for_refusal(
        login_row, exc, registry=scene_entry_registry, emit=<the emit above>)
    if recovery is not None:
        selected.position = recovery.selected_resync   # 1. IN MEMORY
        # 2. use recovery.entry exactly as the non-refused path uses entry
        # 3. do NOT take the login_scene_override_visit branch
        # 4. carry the KA1A-ROOTCAUSE block, below

STEP 1 IS NOT OPTIONAL AND STEP 3 IS NOT A PREFERENCE.  pf-adversary (round
``fdo7ex``, D1) measured both halves of the mistake this file used to invite
by saying only "use ``recovery.entry`` and do not write the row":

  * Use ``entry`` alone and the caller's in-memory ``selected.position``
    still names the shut scene.  At the next ``TargetPos``,
    ``_checkpoint_exact_target`` composes ``Position(selected.position
    .scene_id, ..., <the client's NEW x/y/z>)`` - scene 126 carrying Port
    Royal coordinates - and ``is_position_persist_allowed(126)`` is TRUE, so
    it is written.  The brick is re-armed AND the island position is gone.
  * Take the ``login_scene_override_visit`` branch instead and, by that
    branch's own words, no durable row is written for the whole session - so
    the row never heals and every login forever is a recovery.

Adopting ``selected_resync`` is the third behaviour, and it is the one that
makes "the row heals at the first position the recovered character reports"
true rather than hopeful: the next checkpoint composes the RECOVERED scene id
with the client's confirmed coordinates, and that is a row the login door
admits.  ``durable_write_allowed`` stays ``False`` because this module does
not authorise a write; it is ``_checkpoint_exact_target``, at the client's
first confirmed position, that writes - which is exactly the division
``COO-DECISION 20260828_2130`` set.

🔴 CARRY THE ``KA1A-ROOTCAUSE`` BLOCK.  chief marked this red in R399 section
2 for ANYONE performing this VISIT, and measured the price of copying half of
it: the destination scene's census never fires for the whole session (an
empty world), combat membership stays pinned to the departure scene so every
monster's ``ActionVital`` is refused, and loot cells stay behind.  A recovery
is exactly such an in-memory relabel - the row says 126 and the character is
placed in 1 - so the caller must, at the same moment: clear
``world_census_sent``, clear ``last_target_pos``, reset combat membership,
and call ``_mob_loot_cross_scene_boundary``.  This module cannot do any of it
(all four live on the connection, in the chief's file), and saying "this file
holds no state" answers the easy half of that question.  It is written here
so the next reader does not pay it twice.

WHAT WAS ALREADY IN THE TREE, AND WHY THIS IS STILL NEEDED (pf-adversary
D11).  Two shipped things answer neighbouring questions and neither is this:

  * ``gm.warp_relog_stage`` + ``gm.login_scene_admission.SANCTIONED_BARRED_
    SCENES`` give a SANCTIONED, SINGLE-USE login entry into scene 126, seen
    to work on a real screen (R313/R318).  So "only a login can rewrite the
    row, and every login into a shut scene is refused" is NOT universally
    true at HEAD: a GM can let one character back in, by hand, one at a time,
    for the one scene that table holds.  That is an operator's rescue, not a
    property of the world, and it does nothing for 304 or 305.
  * ``world_m2_return_leg`` (this lane's own file) is the half that CAPTURES
    the departed-from row before a crossing.  It is where a caller's
    ``remembered`` argument is meant to come from; the two files are the two
    halves of one ticket and neither is the other.

WHAT IS NOT CLAIMED.  Nothing calls this yet.  No client has ever been
pointed at it: every fact here is derived from the registry and from
``world_scene_entry``'s own door.  The brick is not live today only because
the M2 seam's send half is still in a draft PR - and note that the guard
which keeps a durable row out of 126/304/305 today is NOT
``gm.warp_scene_persist`` alone, as an earlier draft of this docstring said:
``lifecycle.checkpoint`` gates on ``is_position_persist_allowed``, which is
TRUE for all three, so the moment a live character stands in one of them and
takes a step, the row is written by the ordinary walk (pf-adversary D3).
"""
from __future__ import annotations

from dataclasses import dataclass

from . import world_scene_entry, world_scene_travel
from .model import Position
from .world_scene_travel import SceneRegistry

# Convention marker.  Not a scenario, not behind a flag: the day the runtime
# calls it, it runs on the default boot for every character.
production_allowed = True
test_only = False

#: Printed when a refused login was turned into an arrival.
CONSOLE_TOKEN = "WORLD_LOGIN_RECOVERED"

#: Printed when the refusal STANDS - either because this module does not
#: recover that reason (see the docstring, point 1) or because the ashore row
#: was refused too (point 2).  A separate token on purpose: "recovered" and
#: "still bricked" must not be one line a reader has to parse fields out of.
DECLINED_CONSOLE_TOKEN = "WORLD_LOGIN_RECOVERY_DECLINED"

#: The refusal reasons a recovery answers.
#:
#: ``scene_not_allowed_at_login`` is a shut door on a scene this tree KNOWS.
#: ``scene_id_out_of_range`` is added on pf-adversary D5 (round ``fdo7ex``):
#: ``store.save_position`` accepts ``0 <= scene_id <= 0xFFFF`` while
#: ``world_scene_travel.destination`` requires ``1 <= n_id``, so a ZEROED row
#: is persistable and unresolvable - a permanent brick that the first cut
#: declined by name.  It is safe to recover for the reason the other two are
#: not: the range is a pair of literal constants, so no registry fault of any
#: size can make it fire for a population at once.
RECOVERABLE_REASONS = (
    world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN,
    world_scene_entry.REFUSED_SCENE_ID_OUT_OF_RANGE,
)

#: Why the recovery declined.  Named, never inferred from the absence of a
#: recovery: a caller that gets ``None`` has to be able to say WHICH of these
#: happened, and "the reason is not one we recover" and "we recover it but
#: could not" are different bugs to go looking for.
DECLINED_REASON_NOT_RECOVERABLE = "refusal_reason_not_recoverable"
DECLINED_ASHORE_ALSO_REFUSED = "every_ashore_row_refused_at_the_same_door"
DECLINED_BAD_ARGUMENTS = "recovery_called_with_a_row_it_cannot_read"
#: pf-adversary D4.  A registry file that will not load is NOT a bad argument,
#: and reporting it as one sends the person on call hunting a corrupt
#: ``character_positions`` row while ``world_scene_registry_001.json`` is the
#: fault.  ``world_scene_entry`` refuses to launder that same confusion one
#: layer down; this module refused to be the layer that does it.
DECLINED_REGISTRY_FAULT = "scene_registry_would_not_load"
#: pf-adversary D2.  Anything else that escaped the recovery.  Named rather
#: than folded into ``bad arguments`` for the same reason.
DECLINED_UNEXPECTED_FAULT = "recovery_raised_something_it_does_not_understand"
DECLINED_REASONS = (
    DECLINED_REASON_NOT_RECOVERABLE,
    DECLINED_ASHORE_ALSO_REFUSED,
    DECLINED_BAD_ARGUMENTS,
    DECLINED_REGISTRY_FAULT,
    DECLINED_UNEXPECTED_FAULT,
)

#: Where the ashore row came from.  ``remembered`` is the row the caller
#: captured before the trip; ``home_pin`` is Port Royal, which is where a NEW
#: character starts and not where this one was standing - the same warning
#: ``world_scene_entry.return_ticket`` carries, kept here because a reader of
#: the console line needs it at the console.
SOURCE_REMEMBERED = "remembered"
SOURCE_HOME_PIN = "home_pin"
#: pf-adversary D8.  A caller that HAS a remembered row must never end up
#: worse off than one that has none: if the door refuses the remembered row,
#: the home pin is tried after it, and the console says that is what happened.
SOURCE_HOME_PIN_AFTER_REMEMBERED = "home_pin_after_remembered_refused"
ASHORE_SOURCES = (
    SOURCE_REMEMBERED,
    SOURCE_HOME_PIN,
    SOURCE_HOME_PIN_AFTER_REMEMBERED,
)


def login_shut_scene_ids(registry: SceneRegistry | None = None) -> tuple[int, ...]:
    """The scenes whose door is pinned shut at login, derived not listed.

    This is NOT the set of scenes that can brick a character - see
    ``brick_risk_scene_ids``.  pf-adversary D3: a shut door only strands a
    character if a durable row can be WRITTEN naming it, and scene 17 carries
    ``persist_position_allowed = false``, which is why this lane's own
    ``world_m2_return_leg`` says a relog from scene 17 already puts a
    character back on land.  The first cut of this file listed all four as if
    they were the same disease.
    """
    resolved = _registry(registry)
    return tuple(
        sorted(
            target.n_id
            for target in resolved.destinations
            if not target.login_entry_allowed
        )
    )


def brick_risk_scene_ids(registry: SceneRegistry | None = None) -> tuple[int, ...]:
    """The scenes a durable row can name AND never be let back in from.

    Both columns, because it takes both: ``login_entry_allowed`` false (the
    door refuses the next login) AND ``persist_position_allowed`` true (a row
    naming this scene can actually be written).  Today that is 126, 304 and
    305 - the three destinations of the M2 seam - and NOT 17.  Derived on
    every call so the sentence above is re-checked rather than believed.

    ``login_entry_allowed`` alone is the wrong column, and it was the one the
    first cut of this file derived: pf-adversary D3, measured at HEAD.
    """
    resolved = _registry(registry)
    return tuple(
        sorted(
            target.n_id
            for target in resolved.destinations
            if not target.login_entry_allowed and target.persist_position_allowed
        )
    )


def _registry(registry: SceneRegistry | None) -> SceneRegistry:
    """The registry to answer from, refusing a thing that is not one.

    pf-adversary D2: ``registry=<anything>`` used to reach
    ``resolve_entry`` and come back out as a ``TypeError`` from inside a
    subscript, through a wrapper whose whole promise is that it does not
    raise.  The type is checked once, here, at the door.
    """
    if registry is None:
        return world_scene_travel.load_scene_registry()
    if type(registry) is not SceneRegistry:
        raise ValueError("recovery needs a SceneRegistry or None")
    return registry


@dataclass(frozen=True)
class LoginRecovery:
    """One refused login, turned into an arrival ashore.

    ``refused_scene_id`` is kept alongside ``entry`` deliberately: a report
    that carried only the arrival could not tell a reader anything had gone
    wrong, and the row the character is REALLY carrying is what an operator
    needs when they ask why the player is not where they left.

    ``selected_resync`` is the load-bearing field and it exists because of
    pf-adversary D1.  See ``THE PLUG SITE`` in the module docstring: handing
    back ``entry`` alone is not enough, because the caller's in-memory row
    still names the shut scene and the next ``TargetPos`` writes the client's
    NEW coordinates under the OLD scene id - the brick re-armed and the
    player's position destroyed in one write.  This field is the row the
    caller must put into its in-memory ``selected.position`` at the same
    moment it uses ``entry``; it is a VALUE so the instruction cannot be
    followed halfway.
    """

    refused_scene_id: int
    refused_reason: str
    ashore: Position
    ashore_source: str
    entry: world_scene_entry.SceneEntry

    @property
    def selected_resync(self) -> Position:
        """The in-memory row the caller must adopt together with ``entry``."""
        return self.entry.position

    @property
    def relocated(self) -> bool:
        """Whether the door moved the ashore row it was handed.

        pf-adversary D7: ``ashore_source`` describes the row that was OFFERED,
        and the door is free to relocate it to a pin 25,000 units away.  A
        console line that reported only the source claimed "we used the row
        you remembered" about a row that was thrown away.
        """
        return bool(self.entry.relocated)

    @property
    def durable_write_allowed(self) -> bool:
        """Always ``False``, and a property so it cannot be constructed True.

        pf-adversary D6: as a defaulted field this was a habit with a name -
        ``LoginRecovery(..., durable_write_allowed=True)`` constructed fine
        and printed ``durable=1``.  It is now unconstructible.

        WHAT IT DOES AND DOES NOT PROVE.  It is this module's AUTHORISATION,
        not an observation: nothing here can see whether ``runtime.py`` wrote
        a row two hundred lines later.  ``durable=0`` on the console means
        "the recovery did not authorise a write", never "no write happened".
        The thing that decides whether a write happens is the plug site, and
        the module docstring names exactly what it must do.
        """
        return False

    @property
    def console_line(self) -> str:
        return recovery_console_line(self)


def _refusal_reason(refusal: object) -> str:
    if not isinstance(refusal, world_scene_entry.SceneEntryRefused):
        raise ValueError("recovery needs the SceneEntryRefused the door raised")
    reason = getattr(refusal, "reason", None)
    if reason not in world_scene_entry.REFUSAL_REASONS:
        raise ValueError(f"refusal carries an unknown reason {reason!r}")
    return reason


def _require_row(value: object, label: str) -> Position:
    """A ``Position`` whose FIELDS are usable, not merely its type.

    pf-adversary D2: ``Position`` is a bare frozen dataclass with no
    validation at all, so ``Position(278, 0, "a", "b", 0.0)`` passed the old
    ``type(...) is Position`` check and came back out of the wrapper as a
    ``TypeError`` from inside ``abs(x - spawn_x)``.
    """
    if type(value) is not Position:
        raise ValueError(f"{label} must be a Position")
    if type(value.scene_id) is not int or type(value.scene_seq) is not int:
        raise ValueError(f"{label} must carry integer scene ids")
    for name in ("x", "y", "z", "heading"):
        if type(getattr(value, name)) not in (int, float):
            raise ValueError(f"{label} must carry numeric {name}")
    return value


def _ashore_candidates(
    remembered: Position | None,
    registry: SceneRegistry | None,
) -> tuple[tuple[Position, str], ...]:
    """The rows to try to arrive on, in order, each with its own name.

    THE ORDER IS THE FIX FOR pf-adversary D8.  The first cut tried the
    remembered row and, when the door refused it, gave up - so a caller that
    HAD captured a row (say, one naming a shut scene, which is a perfectly
    ordinary thing to have captured before a crossing) ended up worse off than
    a caller that passed nothing at all.  The home pin is always the last
    candidate, and the console names which one arrived.

    No scene filtering happens here on purpose: the earlier draft's docstring
    claimed a "different scene from a shut one" guard that the code did not
    have.  Admissibility is the DOOR's answer, asked below, once per
    candidate.
    """
    home = world_scene_travel.home_return_position(_registry(registry))
    if remembered is None:
        return ((home, SOURCE_HOME_PIN),)
    _require_row(remembered, "a remembered row")
    return (
        (remembered, SOURCE_REMEMBERED),
        (home, SOURCE_HOME_PIN_AFTER_REMEMBERED),
    )


def recovery_for_refusal(
    stored: Position,
    refusal: world_scene_entry.SceneEntryRefused,
    *,
    registry: SceneRegistry | None = None,
    remembered: Position | None = None,
    emit=print,
) -> LoginRecovery | None:
    """Turn a refused login into an arrival ashore, or report that it stands.

    Raises ``ValueError`` for arguments this module cannot read - that is a
    bug in the caller and staying loud about it is the point.  Callers on the
    runtime's ``except`` path want ``try_recovery_for_refusal`` instead.

    EMITS ONE LINE OF ITS OWN, AND FORWARDS ``emit`` TO THE DOOR, WHICH EMITS
    ITS OWN.  pf-adversary D9: an earlier draft said "exactly one line either
    way", which was false the moment ``resolve_entry`` printed its mandatory
    ``WORLD_SCENE`` line through the same sink.  A reader greps this module's
    two tokens; the other lines belong to the module that printed them.
    """
    if not callable(emit):
        raise ValueError("recovery needs a callable emit")
    _require_row(stored, "the stored row that was refused")
    reason = _refusal_reason(refusal)
    if reason not in RECOVERABLE_REASONS:
        emit(_declined_line(stored.scene_id, reason, DECLINED_REASON_NOT_RECOVERABLE))
        return None
    for ashore, source in _ashore_candidates(remembered, registry):
        try:
            entry = world_scene_entry.resolve_entry(
                ashore,
                registry=_registry(registry),
                emit=emit,
                via_login=True,
            )
        except world_scene_entry.SceneEntryRefused:
            # The door said no to this way home.  Composing an entry anyway
            # would be a second door with weaker rules, which is how a
            # character ends up somewhere the login path never admitted.
            continue
        recovery = LoginRecovery(
            refused_scene_id=stored.scene_id,
            refused_reason=reason,
            ashore=ashore,
            ashore_source=source,
            entry=entry,
        )
        emit(recovery_console_line(recovery))
        return recovery
    emit(_declined_line(stored.scene_id, reason, DECLINED_ASHORE_ALSO_REFUSED))
    return None


def try_recovery_for_refusal(
    stored: object,
    refusal: object,
    *,
    registry: SceneRegistry | None = None,
    remembered: Position | None = None,
    emit=print,
) -> LoginRecovery | None:
    """``recovery_for_refusal`` that answers ``None`` instead of raising.

    The plug site is inside ``runtime.py``'s ``except SceneEntryRefused``
    handler.  A second exception raised from inside that handler does not
    refuse a login, it unwinds the connection's listener thread - the failure
    ``world_scene_entry.SceneEntryRefused``'s own docstring exists to avoid.

    IT CATCHES EVERYTHING, AND pf-adversary D2 IS WHY.  An earlier draft
    caught ``ValueError`` only, and the DEFAULT call shape - ``registry=None``,
    which makes two separate code paths read the pin file - escaped as
    ``FileNotFoundError`` the day that file went unreadable.  A broken pin
    file is not "a bug in the caller's argument types", and the wrapper that
    exists to keep a listener thread alive must not be the thing that kills
    it.  Each class of escape gets its OWN declined reason, because "your row
    is unreadable" and "the registry will not load" send an operator to
    different places (D4).

    It does NOT swallow a failure of ``emit`` itself: a caller whose console
    is broken has a different problem, and eating that would make this
    module's one observable output optional.  The declined line is emitted
    OUTSIDE the guarded block for that reason.
    """
    if not callable(emit):
        # There is no console to report to, and the one job of this wrapper is
        # to leave the connection's listener thread alive.  Silence is the
        # only remaining behaviour; the login then refuses exactly as it does
        # without this module.
        return None
    declined = None
    try:
        return recovery_for_refusal(
            stored,  # type: ignore[arg-type]
            refusal,  # type: ignore[arg-type]
            registry=registry,
            remembered=remembered,
            emit=emit,
        )
    except ValueError as exc:
        # world_scene_travel raises ValueError for a malformed pin FILE as
        # well as for a bad row, so the two are separated by asking whether
        # the registry can be loaded at all rather than by exception type.
        declined = (
            DECLINED_BAD_ARGUMENTS if _registry_loads(registry)
            else DECLINED_REGISTRY_FAULT
        )
        del exc
    except (OSError, LookupError, TypeError, AttributeError):
        declined = (
            DECLINED_UNEXPECTED_FAULT if _registry_loads(registry)
            else DECLINED_REGISTRY_FAULT
        )
    except Exception:
        declined = DECLINED_UNEXPECTED_FAULT
    scene_id = getattr(stored, "scene_id", None)
    emit(
        _declined_line(
            scene_id if type(scene_id) is int else -1,
            getattr(refusal, "reason", "unknown"),
            declined,
        )
    )
    return None


def _registry_loads(registry: SceneRegistry | None) -> bool:
    """Whether the pin the recovery would use is readable at all.

    Used only to name a declined reason, never to decide an arrival, so a
    second fault here must not become a third exception.
    """
    try:
        _registry(registry)
    except Exception:
        return False
    return True


def _reason_field(reason: object) -> str:
    """A refusal reason safe to print next to other fields on one line.

    The console this lands on is cp874 and the tickets that read it grep for
    whole fields, so a reason carrying a space or an ``=`` would split one
    field into two silently.  Refused loudly instead of sanitised: the values
    this module prints all come from its own tuples and from
    ``world_scene_entry``'s, and none of them can do this today, so a value
    that can is a new one nobody checked.
    """
    text = reason if isinstance(reason, str) else repr(reason)
    if not text:
        return "unnamed"
    if any(c.isspace() or c in "=@" or not (32 <= ord(c) < 127) for c in text):
        return "unprintable_reason"
    return text


def _scene_field(scene_id: object) -> str:
    """A scene id safe to print, which the raw row's is not.

    pf-adversary D6: ``Position`` validates nothing, ``stored.scene_id`` is
    only ever PRINTED here, and ``Position("126 durable=1 xx", ...)`` produced
    a ``WORLD_LOGIN_RECOVERED`` line carrying a second ``durable=`` field that
    a ticket's grep would have believed.  A non-integer scene id was also a
    ``UnicodeEncodeError`` waiting on a cp874 console, i.e. an exception on
    the one path that must not raise.
    """
    if type(scene_id) is not int or isinstance(scene_id, bool):
        return "not_a_scene_id"
    return str(scene_id)


def _declined_line(scene_id: object, refused_reason: object, declined: object) -> str:
    return (
        f"{DECLINED_CONSOLE_TOKEN} scene={_scene_field(scene_id)} "
        f"refusal={_reason_field(refused_reason)} "
        f"declined={_reason_field(declined)}"
    )


def recovery_console_line(recovery: LoginRecovery) -> str:
    """The one line a person at the console reads to explain the arrival.

    Field order is fixed and every field is ``name=value`` with no spaces
    inside a value, because the attended tickets that read this console grep
    by prefix.  ``arrived=`` is on the line because ``source=`` alone lied
    (D7): it names the row that was OFFERED to the door, and ``relocated``
    is the door's answer about whether it kept it.  ``durable=0`` is this
    module's authorisation and not an observation - see
    ``LoginRecovery.durable_write_allowed``.
    """
    if type(recovery) is not LoginRecovery:
        raise ValueError("console line needs a LoginRecovery")
    return (
        f"{CONSOLE_TOKEN} from_scene={_scene_field(recovery.refused_scene_id)} "
        f"refusal={_reason_field(recovery.refused_reason)} "
        f"to_scene={_scene_field(recovery.entry.position.scene_id)} "
        f"source={_reason_field(recovery.ashore_source)} "
        f"arrived={'relocated' if recovery.relocated else 'as_offered'} "
        f"durable={1 if recovery.durable_write_allowed else 0}"
    )


def recovery_report(recovery: LoginRecovery) -> dict:
    """One flat dict for a round note or an attended ticket.

    Wraps ``world_scene_entry.entry_report`` rather than restating it, and
    refuses a name collision instead of merging - the same rule, and the same
    reason, as the report it wraps.
    """
    if type(recovery) is not LoginRecovery:
        raise ValueError("recovery report needs a LoginRecovery")
    report = world_scene_entry.entry_report(recovery.entry)
    mine = {
        "refused_scene_id": recovery.refused_scene_id,
        "refused_reason": recovery.refused_reason,
        "ashore_source": recovery.ashore_source,
        "ashore_scene_id": recovery.ashore.scene_id,
        "durable_write_allowed": recovery.durable_write_allowed,
        "recovery_console_line": recovery_console_line(recovery),
    }
    collisions = sorted(set(report) & set(mine))
    if collisions:
        raise ValueError(
            "recovery report would overwrite scene entry columns: "
            + ", ".join(collisions)
        )
    report.update(mine)
    return report
