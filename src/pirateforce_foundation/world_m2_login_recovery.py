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

1. IT RECOVERS EXACTLY ONE REFUSAL REASON: ``scene_not_allowed_at_login``.
   The other three (``scene_not_pinned``, ``scene_id_out_of_range``,
   ``scene_has_no_pinned_spawn``) are DECLINED BY NAME, and the reason is a
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

WHERE THIS PLUGS IN (one call, chief's file, chief's round).  The site is
already written and already catches the right exception:
``runtime.py``'s ``except world_scene_entry.SceneEntryRefused as exc:``
handler inside the login path - the one whose own comment says "this is the
deliberate handler that class asks for: print the reason, refuse the login by
name".  Between printing the reason and ``return []``, ask this module; if it
answers, use ``recovery.entry`` exactly as the non-refused path uses its
``entry`` and DO NOT write the row.  ``try_recovery_for_refusal`` is the
entry point for that site specifically: it is inside an ``except`` block, so
it returns ``None`` instead of raising for anything short of a bug in its own
caller's argument types - the shape ``COO 0642`` confirmed for
``try_claim_sink_for_drain`` on the other half of this seam.

WHAT IS NOT CLAIMED.  Nothing calls this yet; on today's tree no durable row
can reach scene 126/304/305, because ``gm.warp_scene_persist`` refuses to
persist a login-shut destination and the M2 seam's own send half is still in
a draft PR.  This module is the guard that has to exist BEFORE that lands,
not a report that the brick is live today.  It has never been measured
against a real client: every fact here is derived from the registry and from
``world_scene_entry``'s own door.
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

#: The one refusal reason a shut door produces on a scene this tree knows.
RECOVERABLE_REASONS = (world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN,)

#: Why the recovery declined.  Named, never inferred from the absence of a
#: recovery: a caller that gets ``None`` has to be able to say WHICH of these
#: happened, and "the reason is not one we recover" and "we recover it but
#: could not" are different bugs to go looking for.
DECLINED_REASON_NOT_RECOVERABLE = "refusal_reason_not_recoverable"
DECLINED_ASHORE_ALSO_REFUSED = "ashore_row_refused_at_the_same_door"
DECLINED_BAD_ARGUMENTS = "recovery_called_with_a_row_it_cannot_read"
DECLINED_REASONS = (
    DECLINED_REASON_NOT_RECOVERABLE,
    DECLINED_ASHORE_ALSO_REFUSED,
    DECLINED_BAD_ARGUMENTS,
)

#: Where the ashore row came from.  ``remembered`` is the row the caller
#: captured before the trip; ``home_pin`` is Port Royal, which is where a NEW
#: character starts and not where this one was standing - the same warning
#: ``world_scene_entry.return_ticket`` carries, kept here because a reader of
#: the console line needs it at the console.
SOURCE_REMEMBERED = "remembered"
SOURCE_HOME_PIN = "home_pin"


def login_shut_scene_ids(registry: SceneRegistry | None = None) -> tuple[int, ...]:
    """The scenes whose door is pinned shut at login, derived not listed.

    The docstring above names 17, 126, 304 and 305 as today's set.  This
    function is how a reader checks that sentence has not gone stale, and it
    is what the tests assert against, so the day somebody opens one of those
    doors the claim in this file is re-derived rather than believed.
    """
    resolved = registry if registry is not None else world_scene_travel.load_scene_registry()
    return tuple(
        sorted(
            target.n_id
            for target in resolved.destinations
            if not target.login_entry_allowed
        )
    )


@dataclass(frozen=True)
class LoginRecovery:
    """One refused login, turned into an arrival ashore.

    ``refused`` is kept alongside ``entry`` deliberately: a report that
    carried only the arrival could not tell a reader that anything had gone
    wrong at all, and the row this character is REALLY carrying is the thing
    an operator needs when they ask why the player is not where they left.
    """

    refused_scene_id: int
    refused_reason: str
    ashore: Position
    ashore_source: str
    entry: world_scene_entry.SceneEntry
    #: Always ``False``.  A recovery is a visit (see the module docstring);
    #: the field exists so the plug site reads the answer instead of
    #: remembering it, and so a future round that wants to change it has to
    #: change a value the tests pin rather than a habit.
    durable_write_allowed: bool = False

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


def _ashore_candidate(
    remembered: Position | None,
    registry: SceneRegistry | None,
) -> tuple[Position, str]:
    """The row to try to arrive on, and where it came from.

    ``remembered`` is used only when it is a ``Position`` naming a DIFFERENT
    scene from a shut one - the check is not "is it home", because the row a
    character sailed from is not necessarily Port Royal and
    ``world_scene_entry.return_ticket``'s home-only rule is about a different
    question.  Whether it is actually admissible is decided by the door in
    ``recovery_for_refusal``, not guessed here.
    """
    if remembered is not None:
        if type(remembered) is not Position:
            raise ValueError("a remembered row must be a Position")
        return remembered, SOURCE_REMEMBERED
    return world_scene_travel.home_return_position(registry), SOURCE_HOME_PIN


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

    Emits exactly one line either way.  ``emit`` is a parameter for the same
    reason ``resolve_entry``'s is: a boot that recovers a character silently
    has taken away the only thing a person at the console can read.
    """
    if type(stored) is not Position:
        raise ValueError("recovery needs the stored Position that was refused")
    reason = _refusal_reason(refusal)
    if reason not in RECOVERABLE_REASONS:
        emit(_declined_line(stored.scene_id, reason, DECLINED_REASON_NOT_RECOVERABLE))
        return None
    ashore, source = _ashore_candidate(remembered, registry)
    try:
        entry = world_scene_entry.resolve_entry(
            ashore,
            registry=registry,
            emit=emit,
            via_login=True,
        )
    except world_scene_entry.SceneEntryRefused:
        # The door said no to the way home as well.  Composing an entry here
        # anyway would be a second door with weaker rules, which is how a
        # character ends up somewhere the login path never admitted.
        emit(_declined_line(stored.scene_id, reason, DECLINED_ASHORE_ALSO_REFUSED))
        return None
    recovery = LoginRecovery(
        refused_scene_id=stored.scene_id,
        refused_reason=reason,
        ashore=ashore,
        ashore_source=source,
        entry=entry,
    )
    emit(recovery_console_line(recovery))
    return recovery


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
    So this wrapper turns a bad argument into a declined line naming
    ``recovery_called_with_a_row_it_cannot_read`` and a ``None``, and the
    login refuses exactly as it does today.  Same shape ``COO 0642`` confirmed
    for ``try_claim_sink_for_drain`` on the send half of this seam.

    It does NOT swallow a failure of ``emit`` itself: a caller whose console
    is broken has a different problem, and eating that would make this
    module's one observable output optional.
    """
    try:
        return recovery_for_refusal(
            stored,  # type: ignore[arg-type]
            refusal,  # type: ignore[arg-type]
            registry=registry,
            remembered=remembered,
            emit=emit,
        )
    except ValueError:
        scene_id = getattr(stored, "scene_id", None)
        emit(
            _declined_line(
                scene_id if isinstance(scene_id, int) else -1,
                getattr(refusal, "reason", "unknown"),
                DECLINED_BAD_ARGUMENTS,
            )
        )
        return None


def _reason_field(reason: object) -> str:
    """A refusal reason safe to print next to other fields on one line.

    The console this lands on is cp874 and the tickets that read it grep for
    whole fields, so a reason carrying a space or an ``=`` would split one
    field into two silently.  Refused loudly instead of sanitised: the reasons
    this module prints all come from ``world_scene_entry``'s own tuple and
    none of them can do this today, so a value that can is a new one nobody
    checked.
    """
    text = reason if isinstance(reason, str) else repr(reason)
    if not text:
        return "unnamed"
    if any(c.isspace() or c in "=@" or not (32 <= ord(c) < 127) for c in text):
        return "unprintable_reason"
    return text


def _declined_line(scene_id: int, refused_reason: object, declined: str) -> str:
    return (
        f"{DECLINED_CONSOLE_TOKEN} scene={scene_id} "
        f"refusal={_reason_field(refused_reason)} declined={_reason_field(declined)}"
    )


def recovery_console_line(recovery: LoginRecovery) -> str:
    """The one line a person at the console reads to explain the arrival.

    Field order is fixed and every field is ``name=value`` with no spaces
    inside a value, because the attended tickets that read this console grep
    by prefix.  ``durable=0`` is on the line rather than implied: the whole
    difference between this recovery and the character-bricking shape it
    replaces is whether anything was written, and a reader must not have to
    take that from a docstring.
    """
    if type(recovery) is not LoginRecovery:
        raise ValueError("console line needs a LoginRecovery")
    return (
        f"{CONSOLE_TOKEN} from_scene={recovery.refused_scene_id} "
        f"refusal={_reason_field(recovery.refused_reason)} "
        f"to_scene={recovery.entry.position.scene_id} "
        f"source={_reason_field(recovery.ashore_source)} "
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
