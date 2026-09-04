"""Auto-discovered per-lane extension points into runtime.py.

v6.3 architecture (owner-approved, notes_to_chief/20260827_1230_PANYA-ORDER-
rebalance-team-lane-hooks-pr-size-world-wipe-to-lane-B.md; ack'd
notes_to_chief/20260827_1241_COO-DECISION-panya-order-1230-acknowledged-
lane-hooks-and-3-more.md): the measured problem this exists to fix is that
every lane wiring runtime.py/app.py had to route through a CORE-REQUEST
letter and wait for chief to hand-splice it in -- 27 Aug measured
CORE-REQUEST 005-014 all going through one person while lane A sat idle
half a day and lane B hit four empty rounds in a row.

This package is the fix: each lane owns its own
``lane_hooks/lane_<x>_*.py`` file (write zone, AGENTS.md hook 6) and can add
or change a hook without a chief round in between.  chief still reviews
every lane_hooks change in its PR -- this removes chief from the *wiring*
critical path, not from review.

Discovery is automatic: every ``lane_<x>_*.py`` module in this directory is
imported once, at process start, by ``_discover()`` below, in filename-sort
order (``pkgutil.iter_modules``'s own contract) -- there is no central list
of hook modules to keep in sync, and no other ordering guarantee than that.

Two fail-closed layers, not one:

1. ``fire()`` (below) catches every exception a REGISTERED hook raises
   *while running*, prints ``LANE_HOOK <module> <point> ERR <repr>``, and
   moves on to the next hook for that point -- a runtime bug in one lane's
   hook can never take down the listener thread for every other player.
2. ``_discover()`` catches every exception a hook MODULE raises *while
   importing* (a typo, a bad top-level reference, anything), prints
   ``LANE_HOOK_DISCOVERY <module> IMPORT_FAILED <repr>`` to stderr, and
   imports the next module regardless -- a broken FILE from one lane can
   never take down boot for every other lane's hooks, or the server itself.
   (Earlier draft of this package only had layer 1; pf-adversary's review
   caught that an import-time bug in any future lane_hooks file would have
   propagated straight through this package's own top-level import, through
   runtime.py's ``from . import lane_hooks``, through app.py, and killed the
   whole process before a single connection could be accepted -- exactly
   what this package exists to prevent, just one layer up. Fixed here.)

Neither layer catches ``BaseException`` (``SystemExit``, ``KeyboardInterrupt``,
``GeneratorExit``): those are deliberately allowed to propagate, same as
Python's own convention for e.g. context managers and thread targets. That
is a real, intentional gap in the "never take the process down" guarantee,
not an oversight -- swallowing a deliberate interpreter shutdown signal
inside a per-hook try/except would be its own bug.

Every hook module may declare a module-level ``production_allowed`` flag,
the same convention every other lane module in this project already uses
(``field_mobs.py``, ``columbus_quest_dispatch.py``, etc: ``True`` means
"shippable, no scenario flag needed"; ``False`` or absent means "opt-in
only, not live today"). A module that does not set ``production_allowed =
True`` has every hook it registered withdrawn again right after import --
see ``_discover()``'s call to ``_withdraw()``. This is the same gate every
other module in this project is already held to, applied here rather than
invented fresh (PANYA-ORDER 20260827_1230, COO-DECISION 20260827_1241 both
name it explicitly as a required property of this package, not optional).

WHAT THAT GATE DOES AND DOES NOT REACH, STATED EXACTLY (round wi1m62,
COO-DECISION 20260829_0041 option (b)). Withdrawal covers a lane module's
code on ONE route: the hooks it registered, which then never fire. It
cannot reach a runtime.py branch that calls a lane's code DIRECTLY, because
no registration is involved for _withdraw() to undo -- and one such branch
exists on purpose: CORE-REQUEST-GM-029's 0xAC52 chat route, which had to
leave the hook shape behind because ``fire()`` cannot hand an action back
(see ``fire()``'s docstring). For one round, round apk7ue, that branch ran
with no production_allowed gate over it at all, which quietly dropped a
switch the owner had approved. The fix is not a property of hooks: the
call site asks ``module_production_allowed("lane_gm_chat_command")`` before
it composes anything, and stands down when the answer is False.

Stated without the flattery a shorter sentence would invite (pf-adversary,
round wi1m62): this is ONE flag read by TWO mechanisms for two different
reasons -- the hook route because the registration is withdrawn, the
direct route because the call site reads the flag. For
``lane_gm_chat_command`` specifically only the second is live, since its
hook is registered and never fired (see the accuracy note below); and the
flag it declares gates code the direct route runs in
``gm/chat_command_action.py``, which has no flag of its own. That is
coupling held by two files agreeing on a string, not a property this
package can enforce: any future direct call site owes the same read, and
nothing here can make it. A PR reviewer has to. The pairing for the one
call site that exists is pinned by
tests/test_gm_chat_command_dispatch_wiring.py and tests/test_lane_hooks.py.

Every hook prints a token twice: once at registration (import time, via the
``hook`` decorator below, on STDERR -- see the decorator's own comment for
why not stdout) and once at each real firing on the production path
(inside ``fire()``, also on STDERR since round lo7e03, for the same reason:
the 0xAC52 point then fired on a vital every client sends, and the token
landed inside a replay tool's --json stdout artifact).

ROUND apk7ue, ACCURACY NOTE -- "once at each real firing" is not true of every
registered point. CORE-REQUEST-GM-029 replaced the 0xAC52 call site with a
direct call into ``gm/chat_command_action.py``, so
``vital_inbound_chat_local_talk`` is REGISTERED AND NEVER FIRED: its
registration token still prints at import and no firing token can follow it.
UPDATED round zsctq7: ``vital_inbound_gm_run_command`` (0x51E9) and
``vital_inbound_trigger_vital`` (0x1FB2, LANE-A's `lane_a_island_trigger_
log.py`, CORE-REQUEST `pf_bridge/notes_to_chief/20260904_0434`/`0437`) both
fire now. A WIRED-v2 grep that treats a registration token as evidence of
emission would overcount ``vital_inbound_chat_local_talk`` regardless of how
many other points are wired -- this note names which points are which, it is
not a fixed count to keep in sync by hand.

These tokens are DESIGNED to be grepped by a
WIRED v2-style check and by a headless smoke test the same way this
project's other console tokens already are (notes_to_chief 20260827 "WIRED
v2" -- import alone does not count, emission on the production path does)
-- no such grep script exists in this repository yet as of this package's
first PR; that is a claim about intended use, not a measured fact about an
existing gate. A grep for either token must check combined stdout+stderr
(``2>&1``), not stdout alone.
"""
from __future__ import annotations

import importlib
import pkgutil
import sys
import threading
import weakref
from pathlib import Path
from typing import Any, Callable, NamedTuple

_HOOKS: dict[str, list[tuple[str, Callable[..., None]]]] = {}
# Scene n_id -> the ONE composer registered for that scene.  Unlike _HOOKS
# (a list per point -- reporting hooks stack), census composition hands a
# value back to runtime.py, and two composers for one scene would mean two
# authors for one frame: first registration wins, a duplicate is refused
# loudly at import time.  See ``census_composer`` below.
_SCENE_CENSUS_COMPOSERS: dict[int, "SceneCensusComposer"] = {}
# Qualified module name -> the module's own ``production_allowed`` flag, as
# read once at discovery.  Only modules that IMPORTED get an entry, so a
# module whose file is missing or raised on import is absent here and
# ``module_production_allowed()`` reports it closed.  See that function.
_PRODUCTION_ALLOWED: dict[str, bool] = {}
_DISCOVERED = False


def hook(point: str) -> Callable[[Callable[..., None]], Callable[..., None]]:
    """Decorator: register ``fn`` to run when ``point`` fires.

    ``point`` is a free-form name the runtime.py call site and the hook
    module agree on out of band (e.g. ``"vital_inbound_gm_run_command"``).
    There is no central registry of valid point names by design -- adding
    a new insertion point in runtime.py is a chief-owned runtime.py edit,
    but wiring more behavior onto an EXISTING point never is.  There is
    also no ownership check tying a ``lane_<x>_`` filename prefix to which
    points it may register onto -- a careless file could register onto
    another lane's point by accident.  Left open by design (matches "no
    central registry"), but a PR reviewer should treat an unexpected
    cross-lane point name as worth asking about.
    """

    def decorator(fn: Callable[..., None]) -> Callable[..., None]:
        module_name = fn.__module__
        _HOOKS.setdefault(point, []).append((module_name, fn))
        # stderr, not stdout: registration runs at IMPORT time, which fires
        # for every process that imports pirateforce_foundation.runtime --
        # including the headless replay tools' --json mode, whose contract
        # with the Windows attended runner is pure JSON on stdout with
        # nothing else mixed in. Found the hard way: this line on stdout
        # broke test_the_replay_tool_json_mode_reports_a_pass_verdict and
        # test_ground_loot_nameprop_hypothesis's own json-mode test the
        # first time this package existed, neither of which touches this
        # hook's point at all -- they just happened to import runtime.py.
        # fire() below is on stderr for the same reason, since round
        # lo7e03 (CORE-REQUEST-GM-028).  It used to be on stdout, with the
        # argument that it "only ever runs on the actual dispatch path for
        # a specific vital, so it cannot leak into an unrelated tool's
        # output".  That argument was written when the only fire point was
        # 0x51E9, a vital GT-103 measured at zero frames per boot.  The
        # second point is 0xAC52, which every client sends freely, and it
        # leaked immediately: measured, tools/pf_runtimeres_death_headless_
        # replay.py --json gained one LANE_HOOK_FIRED line in its stdout
        # artifact, because its scenario-off control dispatches a chat
        # frame.  A grader that greps the console still sees the token --
        # stderr is the console too -- and a tool that redirects stdout to
        # a file gets its JSON back.
        print(f"LANE_HOOK_REGISTERED {module_name} {point}", file=sys.stderr)
        return fn

    return decorator


def _console_safe(text: str) -> str:
    """Best-effort ASCII rendering for anything printed by this module.

    The bridge console runs cp874; a raw f-string containing client-supplied
    text (e.g. a future chat/say hook's exception message) can raise
    UnicodeEncodeError INSIDE this module's own except-handler print, which
    would itself escape fire()'s try/except -- a second, unguarded failure
    breaking the one guarantee this package exists to make.  This project
    has already been bitten by non-ASCII console output twice (rounds 86,
    142, cited in the chief prompt); command_capture.py's own
    ``_escape_for_header`` is the same lesson applied to a capture header.
    No current hook's exception text is client-controlled (verified against
    lane_gm_run_command.py's one caller), but every FUTURE hook this
    package invites is a hook this function has to be safe for on day one.
    """
    return text.encode("ascii", "backslashreplace").decode("ascii")


def fire(point: str, **kwargs: object) -> None:
    """Run every hook registered for ``point``, in registration order.

    Fail-closed: a hook that raises ``Exception`` (not ``BaseException`` --
    see module docstring) is caught, logged by name, and skipped, never
    re-raised.  Never returns a value; hooks that need to hand something
    back to runtime.py are not what this point shape is for (see module
    docstring -- report on the wire/queue/self.events, not a return value,
    so a broken hook can be dropped without touching a chief-owned
    return-value contract).
    """
    for module_name, fn in _HOOKS.get(point, ()):
        print(f"LANE_HOOK_FIRED {module_name} {point}", file=sys.stderr)
        try:
            fn(**kwargs)
        except Exception as exc:  # noqa: BLE001 - fail-closed by design, see docstring
            print(
                _console_safe(f"LANE_HOOK {module_name} {point} ERR {exc!r}"),
                file=sys.stderr,
            )


class SceneCensusComposer(NamedTuple):
    """One lane's claim on one scene's census: who owns it, and the callable
    that composes it.  ``module`` is the qualified module name, which is
    exactly what a call site passes to ``module_production_allowed()``
    before it calls ``compose`` (COO-DECISION 20260829_0041 option (b):
    the call site reads the flag, then calls directly)."""

    module: str
    compose: Callable[..., "SceneCensusResult | None"]


class SceneCensusResult(NamedTuple):
    """What a scene census composer hands back to runtime.py's one lane
    call site (CORE-REQUEST LANE-A 20260829_1845).  This is the whole
    contract: runtime.py consumes exactly these fields and nothing else,
    so a lane module can be reviewed against this tuple instead of against
    runtime.py's internals.

    ``console_lines`` are printed by the call site in order, BEFORE the
    frame is queued -- console-proof-before-frame is the same order the
    bg0001/bg0002 branches already keep, and the lines are the lane's own
    (scene entry line, census line, actor lines -- whatever the lane's
    evidence discipline needs greppable).  ``pc``/``frame`` are the exact
    bytes to queue; ``initial_reapply_ms`` schedules the one reapply the
    sibling branches also send.

    Deliberately NO ``pc_bytes``/``frame_bytes`` fields: the call site
    derives both with ``len()`` from the actual queued bytes, so the
    greppable evidence can never disagree with the wire (pf-adversary,
    round 73fhoc: a redundant lane-asserted length field is an evidence
    channel that can openly contradict the payload it describes).

    The call site treats every field as UNTRUSTED lane input: it coerces
    (``bytes()``, ``int()``, ``float()``, ``str()``) inside its
    fail-closed net, so a malformed-but-typed result -- a str where an int
    should be, a dict instead of this tuple -- refuses the census instead
    of unwinding the listener thread (pf-adversary, round 73fhoc,
    measured both shapes escaping an earlier draft).
    """

    actor_count: int
    pc: bytes
    frame: bytes
    console_lines: tuple[str, ...]
    initial_reapply_ms: int
    # CORE-REQUEST (LANE-A 20260829_2321), option (a): the way BACK for the
    # membership the seam already computes.  A composer that hands one over
    # is handing the call site ``world_population_handoff.MembershipReset``
    # -- BOTH server-side fields in one value, so they cannot disagree (that
    # object's own docstring) -- and the call site then rewrites
    # ``population_indices`` / ``population_refresh_anchor`` /
    # ``world_census_indices`` from it.  The default ``None`` means "do not
    # touch them", which keeps every composer written before this field
    # existed meaning exactly what it meant: those fields stay unset on a
    # lane boot, the documented safe state while nothing answers ChooseNPC
    # for a lane scene.  The annotation is a string on purpose: lane_hooks
    # must not import the seam at module level for a type it never
    # constructs.
    membership: "Any | None" = None

    # COO-DECISION 20260903_2247: the identities lane B's own hostile-mob
    # registry (``field_mobs._SCENE_TABLE_MODULES``) names for this scene --
    # read through that lane's public per-scene-id reader
    # (``field_mobs.roster_for_scene_id``), never by importing one of its
    # per-scene table modules by name.  Lane B needed this to splice
    # hostility onto scene 14's arrivals without guessing.  The field is
    # scene-agnostic in EVERY composer this tuple can come from: no
    # composer special-cases scene 14 to fill it.  CORRECTED, pf-adversary
    # (round t8m3ab): an earlier draft of this comment also named scene 2
    # here, which is false -- scenes 1 and 2 never reach a
    # ``SceneCensusResult`` at all (``runtime.py``'s own lane-census branch
    # excludes both by id, and ``lane_a_scene_census.
    # RESERVED_BY_RUNTIME_BRANCHES`` does the same on this lane's side), so
    # this field is never constructed for either.  Empty for any scene the
    # registry does not (yet) address -- that is a real, safe answer, not a
    # failure: a composer defaults to it and never raises for it.
    actor_identities: "tuple[int, ...]" = ()


def census_composer(scene_id: int) -> Callable[
    [Callable[..., "SceneCensusResult | None"]],
    Callable[..., "SceneCensusResult | None"],
]:
    """Decorator: register ``fn`` as THE census composer for ``scene_id``.

    The registry ``fire()`` points deliberately cannot serve this job:
    ``fire()`` never returns a value, and composing a census means handing
    actors back (stated in fire()'s own docstring; re-stated by the lane's
    letter that asked for this point).  So this is the OTHER house shape,
    COO-DECISION 20260829_0041 option (b): the runtime.py call site looks
    the composer up, reads ``module_production_allowed()`` for the owning
    module, and only then calls ``compose`` directly.

    ``compose`` is called with keyword arguments only -- today ``legacy``,
    ``anchor`` (a resolved (x, y, z)), ``scene_id``, and
    ``scene_entry_registry``; a composer should accept ``**kwargs`` for the
    ones it ignores so the call site can grow arguments without breaking
    every lane at once.  It returns a ``SceneCensusResult``, or ``None`` to
    decline: the call site then latches the census as sent-nothing for the
    session, with a named event -- decline is a permanent answer for the
    process, not a retry (the registry data a composer reads is loaded once
    at boot, same reasoning as the bg0002 anchor latch in runtime.py).

    First registration wins.  Discovery imports lane files in
    filename-sort order (``_discover()``'s only ordering guarantee), so
    which file wins a collision is deterministic -- but a collision is
    always a bug between two lanes, so the loser is refused with a
    ``LANE_HOOK_DUPLICATE`` line on stderr rather than silently shadowed
    or silently stacked.

    Scenes 1 and 2 keep their dedicated runtime.py branches no matter what
    is registered here: the call site consults this table only for scenes
    those branches do not already claim (the no-regression-path property
    the lane's letter asked for by name).
    """

    def decorator(
        fn: Callable[..., "SceneCensusResult | None"],
    ) -> Callable[..., "SceneCensusResult | None"]:
        module_name = fn.__module__
        if not module_name.startswith(f"{__name__}."):
            # A composer whose owning module lives OUTSIDE this package can
            # register but can never pass the gate: ``_gate_module`` only
            # ever records lane_hooks modules, so
            # ``module_production_allowed`` answers False forever and the
            # scene silently degrades to the not-home skip with a green
            # REGISTERED token at boot (pf-adversary, round 73fhoc,
            # measured with a gm/ helper module).  Refused loudly instead:
            # the lane file itself must carry the decorated function (it
            # may still import and delegate to a helper inside it).
            print(
                _console_safe(
                    f"LANE_HOOK_REJECTED {module_name} "
                    f"scene_census_composer:{scene_id} "
                    f"NOT_A_LANE_HOOKS_MODULE"
                ),
                file=sys.stderr,
            )
            return fn
        existing = _SCENE_CENSUS_COMPOSERS.get(scene_id)
        if existing is not None:
            print(
                _console_safe(
                    f"LANE_HOOK_DUPLICATE {module_name} "
                    f"scene_census_composer:{scene_id} "
                    f"KEPT {existing.module}"
                ),
                file=sys.stderr,
            )
            return fn
        # stderr for the same reason as the ``hook`` decorator above:
        # registration runs at import time, inside every --json tool run.
        # Print BEFORE inserting: if this print somehow raises, the raise
        # propagates out of the module's import, _import_module_safely
        # reports IMPORT_FAILED, and no entry was left behind for the
        # failure report to contradict (pf-adversary, round 73fhoc).
        print(
            _console_safe(
                f"LANE_HOOK_REGISTERED {module_name} "
                f"scene_census_composer:{scene_id}"
            ),
            file=sys.stderr,
        )
        _SCENE_CENSUS_COMPOSERS[scene_id] = SceneCensusComposer(
            module_name, fn,
        )
        return fn

    return decorator


def scene_census_composer(scene_id: int) -> SceneCensusComposer | None:
    """The composer registered for ``scene_id``, or ``None`` if no lane has
    claimed it.  ``None`` is the everyday answer, not an error: it means
    the call site walks its existing branches untouched."""
    return _SCENE_CENSUS_COMPOSERS.get(scene_id)


class ChooseNpcResponder(NamedTuple):
    """One lane's claim on answering ``ChooseNPC`` for one scene's composed
    roster (COO-DECISION 20260830_0818): who owns it, and the callable that
    answers a click.  Same shape and same reason as ``SceneCensusComposer`` --
    ``module`` is what a call site passes to ``module_production_allowed()``
    before it calls ``respond`` (option (b), same as the census point)."""

    module: str
    respond: Callable[..., "ChooseNpcResponse | None"]


class ChooseNpcResponse(NamedTuple):
    """What a scene's ChooseNPC responder hands back for one answered click.

    Mirrors ``SceneCensusResult``'s own contract shape on purpose: a future
    runtime.py call site is expected to coerce every field as untrusted lane
    input before using it (bytes()/float()/str()), the same net the census
    call site already runs, and to print ``console_lines`` in order BEFORE
    queuing the frame -- console-proof-before-frame, the same discipline the
    census point uses.  ``None`` from ``respond`` (not this type) means "no
    honest answer for this click", the same everyday-not-an-error meaning
    ``scene_census_composer`` gives its own ``None``.

    ``extra_actions`` IS THE COLLECTION HALF, ADDED ROUND ``yjjtyn``
    (LANE-A), AND ITS DEFAULT IS THE WHOLE SAFETY ARGUMENT.  The frozen
    dispatcher answers ONE scene-1 click with MORE THAN ONE action -- the
    face frame, plus the empty ``NPCConversation`` collection that is the
    client's authentic default-talk trigger, plus a trade-zoom at the shop
    trigger (``current/pf_login_game_server_v141.py:4395-4480``) -- while a
    responder that claims a scene's vital family replaces that whole loop.
    ``runtime.py``'s own call-site comment names the fix and its owner:
    "needs ``ChooseNpcResponse`` to become a collection ... a
    ``lane_hooks``/lane_a design change outside a runtime.py guard's
    scope".  This field is that change, made ADDITIVELY: a tuple of
    ``(label, pc, frame, delay)`` actions a call site should queue AFTER
    the response's own pair, in order.  It defaults to ``()`` so every
    responder written before it existed, and the call site that reads
    ``label``/``pc``/``frame``/``delay`` today, mean exactly what they
    meant.

    NOTHING READS IT YET, AND THAT IS THE PLAIN STATUS OF THE FIELD, not a
    promise about tomorrow: the one line that would read it
    (``actions.extend(...)`` in the responder branch of ``runtime.py``,
    just after ``actions = [(response.label, ...)]``) is chief's, and is
    asked for by CORE-REQUEST rather than taken.  Until that line lands, a
    responder that fills this field composes bytes no player receives --
    read the field's presence as "ready for that line", never as "these
    actions are being sent".

    A CALL SITE MUST COERCE THESE LIKE EVERY OTHER LANE FIELD (the same net
    the census point already runs): ``str(label)``, ``bytes(pc)``,
    ``bytes(frame)``, ``float(delay)``, and a malformed entry means "send
    the main pair only" -- never a dropped answer and never a raise on the
    frame path.
    """

    label: str
    pc: bytes
    frame: bytes
    delay: float
    console_lines: tuple[str, ...]
    extra_actions: tuple[tuple[str, bytes, bytes, float], ...] = ()


_SCENE_CHOOSE_NPC_RESPONDERS: dict[int, "ChooseNpcResponder"] = {}


def choose_npc_responder(scene_id: int) -> Callable[
    [Callable[..., "ChooseNpcResponse | None"]],
    Callable[..., "ChooseNpcResponse | None"],
]:
    """Decorator: register ``fn`` as THE ChooseNPC responder for ``scene_id``.

    Same registry shape as ``census_composer`` and for the same reason: one
    responder per scene (a click has one honest answer), first registration
    wins, a duplicate is refused loudly rather than silently shadowed, and a
    responder from outside this package is rejected loudly rather than
    silently dead (module_production_allowed only ever records lane_hooks
    modules).  ``respond`` is called with keyword arguments only, so a future
    call site can grow arguments without breaking every registered responder
    at once; a responder should accept ``**kwargs`` for ones it ignores.

    NOT YET CONSULTED BY ANY runtime.py CALL SITE, as of this point's first
    round.  The only thing that answers a real ``ChooseNPC``/``TARGET_VITAL``
    click today is the frozen dispatcher
    (``current/pf_login_game_server_v141.py:4395``), reached unconditionally
    from ``runtime.py``'s own ``super().dispatch(parsed)`` before any lane
    code runs, and it answers from ``self.population_indices`` alone -- see
    ``lane_hooks/lane_a_choose_npc_scene14.py``'s module docstring for the
    exact crash a registration on this point does not, by itself, prevent,
    and the CORE-REQUEST asking runtime.py for the guard that would.  This
    registry exists so that guard has something ready to call the day it
    lands, the same order this project already built the census point in
    (registry first, call site by CORE-REQUEST, per
    ``lane_a_scene_census.py``'s own docstring)."""

    def decorator(
        fn: Callable[..., "ChooseNpcResponse | None"],
    ) -> Callable[..., "ChooseNpcResponse | None"]:
        module_name = fn.__module__
        if not module_name.startswith(f"{__name__}."):
            print(
                _console_safe(
                    f"LANE_HOOK_REJECTED {module_name} "
                    f"choose_npc_responder:{scene_id} "
                    f"NOT_A_LANE_HOOKS_MODULE"
                ),
                file=sys.stderr,
            )
            return fn
        existing = _SCENE_CHOOSE_NPC_RESPONDERS.get(scene_id)
        if existing is not None:
            print(
                _console_safe(
                    f"LANE_HOOK_DUPLICATE {module_name} "
                    f"choose_npc_responder:{scene_id} KEPT {existing.module}"
                ),
                file=sys.stderr,
            )
            return fn
        print(
            _console_safe(
                f"LANE_HOOK_REGISTERED {module_name} "
                f"choose_npc_responder:{scene_id}"
            ),
            file=sys.stderr,
        )
        _SCENE_CHOOSE_NPC_RESPONDERS[scene_id] = ChooseNpcResponder(
            module_name, fn,
        )
        return fn

    return decorator


def scene_choose_npc_responder(scene_id: int) -> ChooseNpcResponder | None:
    """The responder registered for ``scene_id``, or ``None`` if no lane has
    claimed it.  ``None`` is the everyday answer, not an error: it means
    whatever the frozen dispatcher already does stands unchanged."""
    return _SCENE_CHOOSE_NPC_RESPONDERS.get(scene_id)


def console_safe(text: str) -> str:
    """Public spelling of ``_console_safe`` for call sites OUTSIDE this
    package that print lane-supplied text -- e.g. runtime.py printing a
    census composer's ``console_lines``.  A lane's line is exactly as
    client-adjacent as a lane hook's exception text, and the cp874 scar
    (rounds 86, 142) does not care which package did the printing."""
    return _console_safe(text)


def announce_direct_fire(module_name: str, point: str) -> None:
    """Print the same ``LANE_HOOK_FIRED`` token ``fire()`` prints, for a
    call site that reaches a lane's code directly because it needs the
    return value.  Exists so the WIRED-v2 grep contract ("emission on the
    production path, combined 2>&1") holds for direct-call routes too,
    with the token format owned here rather than re-spelled at each call
    site.  stderr, same reason as ``fire()``."""
    print(
        _console_safe(f"LANE_HOOK_FIRED {module_name} {point}"),
        file=sys.stderr,
    )


def registered_points() -> dict[str, int]:
    """Point name -> number of hooks registered.  For tests/diagnostics only."""
    return {point: len(fns) for point, fns in _HOOKS.items()}


#: The one process-wide source of live named-field values, installed by boot
#: wiring (``app.py``) and read by ``current_named_attr_values`` below.
#: ``None`` -- the state of any process that has not wired it, every test that
#: does not ask for it, and every import of this package on its own -- means
#: the read point answers "nothing", which its consumer turns into a refusal.
_LIVE_ATTR_VALUES_SOURCE = None
#: One line per process, not per call: see ``current_named_attr_values``.
_LIVE_ATTR_NO_SOURCE_ANNOUNCED = False


def register_live_attr_values_source(source) -> None:
    """Install the callable ``current_named_attr_values`` reads through.

    ``source`` is ``callable(character_id) -> {x: value}``; today the boot
    wiring hands in ``live_named_attr_values.source_for_store(store)``.
    Passing ``None`` uninstalls it, which is how a test puts the process back
    the way it found it.

    LAST REGISTRATION WINS, AND IT SAYS SO OUT LOUD.  The first draft called
    this "deliberately and harmlessly: the process opens exactly one store" --
    pf-adversary (round dwvbpm, D6) measured that claim false: `app.py` is one
    of THIRTEEN places in this repository that construct a ``SQLiteStore``
    (the twelve ``tools/pf_*_headless_replay.py`` each open their own), and
    the sibling registries next door (``census_composer``,
    ``choose_npc_responder``) refuse a duplicate loudly on the grounds that
    two authors for one answer is a bug between two callers.  So a REPLACEMENT
    is now a console line rather than a silent overwrite.  It is still
    last-wins rather than first-wins: unlike a scene composer, this thing is
    installed by boot wiring, and a boot that re-installs must win over
    whatever a test or an earlier boot left behind.

    A non-callable is REFUSED here with a ``TypeError`` rather than stored,
    because the alternative is a failure that surfaces later, at a send, as an
    opaque ``read_point_raised_TypeError`` in a lane that did nothing wrong.

    THE TOKEN IS THE ONLY THING A WIRED-v2 GREP CAN SEE (pf-adversary, D3).
    This package prints a token for every hook, composer and responder it
    registers; this source had none, so "the boot installed it" and "nobody
    installed it" read identically on a console.  stderr, same reason as
    ``fire()``.
    """
    global _LIVE_ATTR_VALUES_SOURCE, _LIVE_ATTR_NO_SOURCE_ANNOUNCED
    if source is not None and not callable(source):
        raise TypeError(
            "live attr values source must be callable(character_id) -> dict, "
            f"got {type(source).__name__}"
        )
    replacing = _LIVE_ATTR_VALUES_SOURCE is not None and source is not None
    _LIVE_ATTR_VALUES_SOURCE = source
    # RE-ARM THE ANNOUNCEMENT (pf-adversary, round dwvbpm second pass, N2).
    # ``_LIVE_ATTR_NO_SOURCE_ANNOUNCED`` was set once and never reset, so a
    # process that installed a source and later CLEARED it went back to
    # answering nothing in silence -- exactly the state the announcement
    # exists to make audible, reached by the one route that looks most like
    # a bug.  The flag tracks "has this been said about the CURRENT state",
    # so any change of source resets it.
    _LIVE_ATTR_NO_SOURCE_ANNOUNCED = False
    if source is None:
        print(
            _console_safe("LANE_HOOK_LIVE_ATTR_SOURCE CLEARED"),
            file=sys.stderr,
        )
        return
    print(
        _console_safe(
            "LANE_HOOK_LIVE_ATTR_SOURCE REGISTERED "
            f"{getattr(source, '__qualname__', type(source).__name__)}"
            + (" REPLACED_AN_EARLIER_SOURCE" if replacing else "")
        ),
        file=sys.stderr,
    )


def current_named_attr_values(character_id) -> dict:
    """Every named ActorAttr/BasicAttr row whose value this server really
    knows for ``character_id``, keyed by ``x``.

    ORDERED BY ``COO-DECISION 2026-09-04T00:47+07:00`` item 1 and named there
    letter for letter -- ``gm.attr_wire`` has been resolving this attribute by
    name (``attr_wire.LIVE_VALUE_READ_POINT``) since before it existed, and
    refusing every send while it did not.  Two consumers were waiting on it:
    LANE-GM's ``RawBlockCache`` seeding (COO-DECISION 20260904_0046) and
    LANE-B's Door B hit frame (COO-DECISION 20260904_0045).

    A MISSING ROW IS AN ABSENT KEY, NEVER A ZERO.  The consumer
    (``attr_wire.live_named_values``) refuses the WHOLE send when one row it
    needs is absent, and that refusal is the point: the client's apply is a
    full-object copy (``RE-222`` Q0), so a mask bit left unset writes zero
    into the field it names.  ``GT-218`` is what that costs when it is got
    wrong.

    THIS POINT READS AND NEVER SENDS.  It composes no frame, touches no
    socket and writes nothing -- the same contract ``fire()`` has, for the
    same reason.

    IT NEVER RAISES.  With no source installed it returns ``{}``; a source
    that raises is reported on stderr with the package's own
    ``LANE_HOOK ... ERR`` shape and also becomes ``{}``.  Both arrive at the
    consumer as "every row is missing", which is a refusal with a named
    per-row reason -- strictly more useful than the opaque
    ``read_point_raised_<Type>`` an escape would produce.  Anything but a
    ``dict`` from a source is treated the same way rather than passed on: the
    consumer's own ``not_a_mapping`` branch would name the read point for a
    fault that belongs to whoever registered.
    """
    global _LIVE_ATTR_NO_SOURCE_ANNOUNCED
    source = _LIVE_ATTR_VALUES_SOURCE
    if source is None:
        # pf-adversary (round dwvbpm, D4): `{}` here and `{}` from a source
        # that genuinely knows nothing become the SAME
        # `missing_named_rows: ...` refusal one layer up, differing only by
        # a few row numbers in a list of twenty-six -- so "nobody wired a
        # source in this process" is indistinguishable from "this server
        # does not know these values", which is exactly the distinction the
        # layer above spent a named constant (`no_read_point`) on.  The
        # return value cannot carry that difference (a dict is the
        # contract), so the CONSOLE does, once per process: repeating it per
        # call would let a client drive an unbounded log.
        # NOT A FULL FIX and it is not claimed as one: a distinct refusal
        # STRING belongs in `gm/attr_wire.live_named_values`, which is
        # LANE-GM's file.  Asked for by letter, not taken here.
        if not _LIVE_ATTR_NO_SOURCE_ANNOUNCED:
            _LIVE_ATTR_NO_SOURCE_ANNOUNCED = True
            print(
                _console_safe(
                    "LANE_HOOK live_attr_values NO_SOURCE_REGISTERED "
                    "current_named_attr_values answers nothing in this "
                    "process"
                ),
                file=sys.stderr,
            )
        return {}
    try:
        values = source(character_id)
    except Exception as error:      # noqa: BLE001 - see docstring
        print(
            _console_safe(
                "LANE_HOOK live_attr_values current_named_attr_values ERR "
                f"{error!r}"
            ),
            file=sys.stderr,
        )
        return {}
    if not isinstance(values, dict):
        print(
            _console_safe(
                "LANE_HOOK live_attr_values current_named_attr_values ERR "
                f"source returned {type(values).__name__}, not dict"
            ),
            file=sys.stderr,
        )
        return {}
    # Keys are coerced to ``int`` because ``x`` is an int everywhere else in
    # this contract and a str key would silently miss every lookup the
    # consumer makes.  A key that cannot be one is dropped, never raised on:
    # one bad key must not cost the other twenty.
    #
    # STRICT, AND THE FIRST DRAFT WAS NOT (pf-adversary, round dwvbpm, D7):
    # it used a bare ``int(key)`` inside ``except (TypeError, ValueError)``,
    # which TRUNCATED ``2.9`` onto x=2 -- landing a value on `level`, a row
    # nobody addressed -- and let ``{2: 40, "2": 999}`` silently drop one of
    # the two.  A row number is never a float and never ambiguous, so a
    # non-integer key is a bug in the source, not a value to round.  Both
    # rejections are named on stderr rather than swallowed.
    #
    # THE ITERATION IS INSIDE THE NET TOO (pf-adversary, round dwvbpm, D5):
    # ``values`` is only known to be a ``dict`` INSTANCE, and a dict subclass
    # may override ``items()``.  An escape from here would leave this
    # function raising out of a docstring that promises it never does, into
    # a START_GAME_REQ handler that catches only KeyError/PermissionError/
    # ValueError/RuntimeError.
    try:
        items = list(values.items())
    except Exception as error:      # noqa: BLE001 - see above
        print(
            _console_safe(
                "LANE_HOOK live_attr_values current_named_attr_values ERR "
                f"iterating the source's mapping raised {error!r}"
            ),
            file=sys.stderr,
        )
        return {}
    coerced: dict = {}
    for key, value in items:
        if isinstance(key, bool) or not isinstance(key, int):
            # `str` digits are accepted because a JSON-ish source hands
            # those back naturally; everything else -- float, None, tuple --
            # is refused rather than rounded or stringified.
            # ``isascii()`` IS LOAD-BEARING, and its absence was a regression
            # this module shipped for one commit (pf-adversary, round
            # dwvbpm second pass, N1).  ``str.isdigit()`` is True for
            # superscripts, subscripts and every non-Latin digit script, and
            # the two halves fail differently and both badly: SUPERSCRIPT TWO
            # (U+00B2) makes ``int()`` RAISE, out of a function whose
            # docstring promises it never does, while ARABIC-INDIC DIGIT
            # THREE (U+0663) makes it SUCCEED -- silently landing a value on
            # x=3, ``hp_current``.  A row number written in another digit
            # script is not a row number this contract has ever meant.
            # The characters are NAMED, not spelled: this file is scanned by
            # tests/test_tree_is_cp874_safe.py, which measured this very
            # paragraph red one run before this sentence existed.
            if isinstance(key, str) and key.isascii() and key.isdigit():
                key = int(key)
            else:
                print(
                    _console_safe(
                        "LANE_HOOK live_attr_values current_named_attr_values"
                        f" ERR dropped key {key!r} ({type(key).__name__} is"
                        " not a row number)"
                    ),
                    file=sys.stderr,
                )
                continue
        if key in coerced:
            print(
                _console_safe(
                    "LANE_HOOK live_attr_values current_named_attr_values ERR"
                    f" duplicate row {key} after key coercion; keeping the"
                    " first"
                ),
                file=sys.stderr,
            )
            continue
        coerced[key] = value
    return coerced


#: The one process-wide source of the LOGIN path's own bytes for the
#: unnamed rows it happens to touch, installed by boot wiring (``app.py``)
#: and read by ``current_login_attr_bytes`` below.  Same shape and same
#: reason as ``_LIVE_ATTR_VALUES_SOURCE``: ``None`` means the read point
#: answers "nothing", which its consumer (``attr_wire.live_login_bytes``)
#: turns into a named refusal rather than a guess.
_LOGIN_ATTR_BYTES_SOURCE = None
#: One line per process, not per call: see ``current_login_attr_bytes``.
_LOGIN_ATTR_BYTES_NO_SOURCE_ANNOUNCED = False


def register_login_attr_bytes_source(source) -> None:
    """Install the callable ``current_login_attr_bytes`` reads through.

    ``source`` is ``callable(character_id) -> {x: value}``; today the boot
    wiring hands in ``live_login_attr_bytes.source_for_store(store)``.
    Passing ``None`` uninstalls it, which is how a test puts the process
    back the way it found it.  Last registration wins, re-arming the
    announcement below -- same reasoning as
    ``register_live_attr_values_source``, restated there in full.
    """
    global _LOGIN_ATTR_BYTES_SOURCE, _LOGIN_ATTR_BYTES_NO_SOURCE_ANNOUNCED
    if source is not None and not callable(source):
        raise TypeError(
            "login attr bytes source must be callable(character_id) -> "
            f"dict, got {type(source).__name__}"
        )
    replacing = (
        _LOGIN_ATTR_BYTES_SOURCE is not None and source is not None
    )
    _LOGIN_ATTR_BYTES_SOURCE = source
    _LOGIN_ATTR_BYTES_NO_SOURCE_ANNOUNCED = False
    if source is None:
        print(
            _console_safe("LANE_HOOK_LOGIN_ATTR_SOURCE CLEARED"),
            file=sys.stderr,
        )
        return
    print(
        _console_safe(
            "LANE_HOOK_LOGIN_ATTR_SOURCE REGISTERED "
            f"{getattr(source, '__qualname__', type(source).__name__)}"
            + (" REPLACED_AN_EARLIER_SOURCE" if replacing else "")
        ),
        file=sys.stderr,
    )


def current_login_attr_bytes(character_id) -> dict:
    """Every ``attr_wire.unnamed_field_x()`` row the ORDINARY LOGIN PATH
    already sends for ``character_id`` today, keyed by ``x``
    (``LOGIN_BYTES_READ_POINT``, ordered by ``COO-DECISION 20260904_0216``).

    A MISSING ROW IS AN ABSENT KEY, NEVER A ZERO -- same rule as
    ``current_named_attr_values``, for the same reason: the client's apply
    is a full-object copy (``RE-222`` Q0), so a mask bit left unset writes
    zero into the field it names.  Most unnamed rows have no login-time
    source AT ALL (``live_login_attr_bytes``'s own module docstring: the
    login composer's mask never sets those bits, a structural fact, not a
    search miss), so this point answering fewer keys than
    ``unnamed_field_x()`` wants is the everyday, correct case -- the
    consumer (``attr_wire.live_login_bytes``) turns each absent one into a
    named ``missing_login_rows`` entry, never a guess.

    THIS POINT READS AND NEVER SENDS, and IT NEVER RAISES -- both exactly
    as ``current_named_attr_values`` documents for itself, for the same
    reasons; see that function's docstring rather than repeating it here.
    Key coercion, non-dict rejection, and the once-per-process console
    announcements below all follow it verbatim.
    """
    global _LOGIN_ATTR_BYTES_NO_SOURCE_ANNOUNCED
    source = _LOGIN_ATTR_BYTES_SOURCE
    if source is None:
        if not _LOGIN_ATTR_BYTES_NO_SOURCE_ANNOUNCED:
            _LOGIN_ATTR_BYTES_NO_SOURCE_ANNOUNCED = True
            print(
                _console_safe(
                    "LANE_HOOK login_attr_bytes NO_SOURCE_REGISTERED "
                    "current_login_attr_bytes answers nothing in this "
                    "process"
                ),
                file=sys.stderr,
            )
        return {}
    try:
        values = source(character_id)
    except Exception as error:      # noqa: BLE001 - see docstring
        print(
            _console_safe(
                "LANE_HOOK login_attr_bytes current_login_attr_bytes ERR "
                f"{error!r}"
            ),
            file=sys.stderr,
        )
        return {}
    if not isinstance(values, dict):
        print(
            _console_safe(
                "LANE_HOOK login_attr_bytes current_login_attr_bytes ERR "
                f"source returned {type(values).__name__}, not dict"
            ),
            file=sys.stderr,
        )
        return {}
    try:
        items = list(values.items())
    except Exception as error:      # noqa: BLE001 - see docstring
        print(
            _console_safe(
                "LANE_HOOK login_attr_bytes current_login_attr_bytes ERR "
                f"iterating the source's mapping raised {error!r}"
            ),
            file=sys.stderr,
        )
        return {}
    coerced: dict = {}
    for key, value in items:
        if isinstance(key, bool) or not isinstance(key, int):
            if isinstance(key, str) and key.isascii() and key.isdigit():
                key = int(key)
            else:
                print(
                    _console_safe(
                        "LANE_HOOK login_attr_bytes current_login_attr_bytes"
                        f" ERR dropped key {key!r} ({type(key).__name__} is"
                        " not a row number)"
                    ),
                    file=sys.stderr,
                )
                continue
        if key in coerced:
            print(
                _console_safe(
                    "LANE_HOOK login_attr_bytes current_login_attr_bytes ERR"
                    f" duplicate row {key} after key coercion; keeping the"
                    " first"
                ),
                file=sys.stderr,
            )
            continue
        coerced[key] = value
    return coerced


#: character_id -> the live runtime.py session object that most recently
#: selected it, as a WEAK reference.  Populated by ``register_live_session``,
#: called once from runtime.py right after a START_GAME_REQ's
#: ``select_and_start`` succeeds -- the only point that has both the
#: character id (``foundation.selected.id``) and the session object carrying
#: ``client_confirmed_scene``/``scene_label_is_server_guess`` (R328).  A
#: WeakValueDictionary on purpose: when a connection closes, its session
#: object is freed and its entry disappears with it, so a disconnected
#: character answers "no live session" (an honest refusal) rather than a
#: stale scene label from a session that no longer exists -- no separate
#: close-connection hook needed to keep this table from lying.
_LIVE_SESSION_BY_CHARACTER: "weakref.WeakValueDictionary[int, Any]" = (
    weakref.WeakValueDictionary()
)
#: Guards the compound check-then-evict-then-register sequence below.
#: LOAD-BEARING, not belt-and-braces (pf-adversary, round 9vec2s, second
#: pass): this project runs one thread per connection (``connection.py``,
#: ``shutdown.py``'s ``ManagedThread``), so two ``register_live_session``
#: calls for two different characters ARE genuinely concurrent.  The
#: eviction's own compare-and-delete -- ``.get(previous) is session`` then
#: ``del`` -- is two separate dict operations with a real gap between them;
#: without a lock around the whole sequence, a second thread's legitimate
#: ``register_live_session(previous, session_2)`` for the SAME previous id
#: (that character reconnecting for real, elsewhere) can complete between
#: this thread's compare and its delete, and the delete then removes
#: ``session_2``'s fresh, correct entry instead of the stale one it was
#: written to protect -- reproduced under a forced interleaving in review.
#: A plain dict get/set/del is atomic on its own (the GIL), but this
#: sequence is three of them read-modify-write across one call, which is
#: exactly the shape the GIL does not protect.
_LIVE_SESSION_LOCK = threading.Lock()


def register_live_session(character_id: int, session: object) -> None:
    """Record ``session`` as the live owner of ``character_id`` right now.

    LAST REGISTRATION WINS, same reasoning as
    ``register_live_attr_values_source``: a reconnect (or a second
    ``START_GAME_REQ`` on one connection) must replace the entry, not be
    refused as a duplicate -- there is exactly one live session that can
    answer for a character at any moment, and the newest caller is always
    the current one.

    EVICTS THIS SESSION'S OWN PREVIOUS CHARACTER (pf-adversary, round
    `9vec2s`): the call site is ``runtime.py``'s ``START_GAME_REQ`` handler,
    right after ``select_and_start`` succeeds -- which is NOT the same
    moment as the login actually completing.  One branch further down
    (``world_scene_entry.SceneEntryRefused``) can still return ``[]`` with
    ``start_game_reply_sent`` left ``False``, by design, so the client can
    retry with a DIFFERENT selector on the SAME connection.  Without this
    eviction, the refused character's id stayed in the table pointing at
    this session, which had gone on to represent an entirely different
    (successfully selected) character -- a query for the refused
    character's scene would answer with the OTHER character's real,
    confirmed location.  Tracked with one attribute on the session itself
    rather than a reverse index, since the session already carries several
    of these (``client_confirmed_scene`` and friends) and there is exactly
    one at a time to remember.

    COMPARE-AND-DELETE, not a plain delete: the evicted key is removed only
    if it STILL points at THIS session.  A stale key some other session has
    since claimed legitimately (the previous character logged in for real,
    elsewhere) must not be evicted by this connection's own reselect -- that
    would be this same bug in reverse, deleting a live answer instead of a
    stale one.

    THE WHOLE SEQUENCE RUNS UNDER ``_LIVE_SESSION_LOCK`` (pf-adversary,
    round 9vec2s, second pass): see that lock's own comment for the race
    this closes -- the compare-and-delete above is exactly the kind of
    check-then-act pair that is unsafe across the connection threads this
    project actually runs one of per socket.
    """
    character_id = int(character_id)
    with _LIVE_SESSION_LOCK:
        previous = getattr(session, "_lane_hooks_registered_character_id", None)
        if previous is not None and previous != character_id:
            if _LIVE_SESSION_BY_CHARACTER.get(previous) is session:
                del _LIVE_SESSION_BY_CHARACTER[previous]
        try:
            session._lane_hooks_registered_character_id = character_id
        except Exception:  # noqa: BLE001 - a session that refuses the write
            # (an exotic stub in some other lane's test, e.g.) still gets
            # registered under the new id below; it just loses this eviction
            # bookkeeping for ITS next call, which only matters for a
            # session this attribute-hostile in the first place.
            pass
        _LIVE_SESSION_BY_CHARACTER[character_id] = session


class NoConfirmedScene(LookupError):
    """``current_session_scene_id`` has no honest answer for this character.

    Covers every refusal CORE-REQUEST-GM-054 asks for under one exception
    type: no live session (never selected a character, or disconnected),
    a session that has not yet had any position report to confirm, and a
    session whose held label is the server's own unconfirmed guess.  The
    letter's own contract text is "raise or leave unregistered" -- read by
    the caller (``gm.attr_wire.live_current_scene``) as "cannot read this
    row" rather than an error to log.
    """


def current_session_scene_id(character_id: int) -> int:
    """The scene ``character_id``'s live session's CLIENT last confirmed.

    CORE-REQUEST-GM-054 (LANE-GM 20260904_1022), contract fixed by
    COO-DECISION 20260904_1151: reads the R328 pair runtime.py already
    maintains on the session itself, ``client_confirmed_scene`` /
    ``scene_label_is_server_guess`` -- **never**
    ``foundation.selected.position.scene_id``, which
    ``_gm_warp_resync_selected_scene`` overwrites with the warp
    DESTINATION at queue time, before anything from the client has agreed
    it arrived (the exact substitution COO-DECISION 20260904_1151 named
    and refused).

    Raises ``NoConfirmedScene`` -- never a guess, never a default -- for
    every one of: no live session found for ``character_id`` (see
    ``register_live_session``), a session whose ``scene_label_is_server_
    guess`` is true (a warp queued but not yet confirmed by the client's
    own coordinates), and a session whose ``client_confirmed_scene`` is
    still ``None`` (logged in, never moved).  All three are the everyday
    "cannot answer yet" case this letter asks for, not a fault to log
    here -- the caller's own read point is where that accounting belongs.
    """
    session = _LIVE_SESSION_BY_CHARACTER.get(int(character_id))
    if session is None:
        raise NoConfirmedScene(
            f"no live session registered for character {character_id}"
        )
    if getattr(session, "scene_label_is_server_guess", False):
        raise NoConfirmedScene(
            f"character {character_id}'s scene label is an unconfirmed "
            "server guess (scene_label_is_server_guess is True)"
        )
    scene_id = getattr(session, "client_confirmed_scene", None)
    if scene_id is None:
        raise NoConfirmedScene(
            f"character {character_id} has no client-confirmed scene yet"
        )
    return int(scene_id)


def module_production_allowed(module_name: str) -> bool:
    """Is this lane module cleared to run on the production path?

    Not a diagnostic: this is the ``production_allowed`` gate itself, read
    by a call site that reaches a lane module by a route other than
    ``fire()``.  ``_discover()`` can only withdraw HOOKS; a runtime.py
    branch that calls a lane's code directly -- which
    CORE-REQUEST-GM-029's 0xAC52 branch does, because the hook route
    cannot return an action -- is invisible to that withdrawal and has to
    ask here first (COO-DECISION 20260829_0041 option (b): the call site
    reads the flag BEFORE it calls, and chief pays the cost of naming a
    lane's module in runtime.py).

    ``module_name`` may be the bare file stem (``"lane_gm_chat_command"``)
    or the fully qualified name; both resolve to the same entry.

    Fail-closed in every direction that is not a truthy
    ``production_allowed`` on a module ``_discover()`` actually imported:
    a module that failed to import, a file that was deleted, a name with a
    typo in it, a name asked for before discovery reached it, and a flag
    set to ``False`` all return ``False``.  A caller that reads this as
    "closed" must not run the lane's code -- and note the shape that
    follows from that: the closed answer is indistinguishable from the
    typo, on purpose, since guessing on behalf of a switch the owner
    approved is the failure this function exists to prevent.  (The flag is
    read with ``bool()``, so ``production_allowed = 1`` opens the gate the
    same as ``True``; the convention every lane module follows is the
    literal ``True``.)

    NOT LIVE: the answer is the snapshot ``_discover()`` took at import.
    Editing a lane file's flag while a server is running changes nothing
    until the process restarts -- said again at the call site, since that
    is where an operator looking for the switch will read it.
    """
    if module_name.startswith(f"{__name__}."):
        qualified_name = module_name
    else:
        qualified_name = f"{__name__}.{module_name}"
    return _PRODUCTION_ALLOWED.get(qualified_name, False)


def _withdraw(module_name: str) -> None:
    """Remove every hook, every scene census composer AND every ChooseNPC
    responder a module registered.  Used when the module turns out not to be
    production_allowed (see module docstring).  For census composers and
    ChooseNPC responders this is belt-and-braces on purpose: a call site
    reads ``module_production_allowed()`` before calling anyway (option
    (b)), but a withdrawn entry also frees the scene slot: ``_discover()``
    gates each module right after importing it, so a closed lane's claim is
    gone before the next file in filename-sort order even imports, and
    cannot block another lane from registering the same scene."""
    for point, entries in list(_HOOKS.items()):
        _HOOKS[point] = [(m, fn) for (m, fn) in entries if m != module_name]
    for scene_id, entry in list(_SCENE_CENSUS_COMPOSERS.items()):
        if entry.module == module_name:
            del _SCENE_CENSUS_COMPOSERS[scene_id]
    for scene_id, entry in list(_SCENE_CHOOSE_NPC_RESPONDERS.items()):
        if entry.module == module_name:
            del _SCENE_CHOOSE_NPC_RESPONDERS[scene_id]


def _import_module_safely(qualified_name: str) -> object | None:
    """``importlib.import_module``, but a failure is caught, logged by name
    to stderr, and reported as ``None`` instead of propagating.  Factored
    out of ``_discover()`` so this fail-closed-at-import-time behavior has
    its own direct test (tests/test_lane_hooks.py) independent of the real
    on-disk discovery loop."""
    try:
        return importlib.import_module(qualified_name)
    except Exception as exc:  # noqa: BLE001 - fail-closed at file granularity, see module docstring
        print(
            _console_safe(
                f"LANE_HOOK_DISCOVERY {qualified_name} IMPORT_FAILED {exc!r}"
            ),
            file=sys.stderr,
        )
        return None


def _gate_module(qualified_name: str, module: object) -> bool:
    """Read one imported module's ``production_allowed`` flag, record it,
    and return it.  The whole gate, in one testable place.

    Factored out of ``_discover()`` on a pf-adversary finding (round
    wi1m62) that measured the real hazard: with the flag read inline in
    the discovery loop, a mutation that replaced it with ``True`` --
    disabling BOTH the hook withdrawal and this record, i.e. the entire
    owner-approved kill switch -- left all 4,000 tests green, because the
    only tests that exercised the gate wrote ``_PRODUCTION_ALLOWED``
    directly and the only module on disk sets the flag to ``True``.  This
    function is what tests/test_lane_hooks.py can call with a module whose
    flag is False, which is the arrow (flag on the module -> recorded
    value -> what a call site is told) that had no test at any point.

    Recorded even when False: ``module_production_allowed()`` answers for
    direct call sites, which need the negative answer just as much as the
    positive one.
    """
    allowed = bool(getattr(module, "production_allowed", False))
    _PRODUCTION_ALLOWED[qualified_name] = allowed
    return allowed


def _discover() -> None:
    global _DISCOVERED
    if _DISCOVERED:
        return
    _DISCOVERED = True
    package_dir = Path(__file__).parent
    for info in pkgutil.iter_modules([str(package_dir)]):
        if not info.name.startswith("lane_"):
            continue
        qualified_name = f"{__name__}.{info.name}"
        module = _import_module_safely(qualified_name)
        if module is None:
            # A module can register hooks/composers at its top level and
            # THEN raise later in the same import.  Without this withdraw,
            # those partial registrations survive as zombie claims: the
            # scene slot stays occupied by a corpse, a later healthy lane
            # is refused as a DUPLICATE whose KEPT names the corpse, and
            # runtime falls to the not-home skip forever (pf-adversary,
            # round 73fhoc, measured on-disk with two lane files).
            _withdraw(qualified_name)
            continue
        if not _gate_module(qualified_name, module):
            _withdraw(qualified_name)
            print(
                f"LANE_HOOK_DISCOVERY {qualified_name} SKIPPED_NOT_PRODUCTION_ALLOWED",
                file=sys.stderr,
            )


_discover()
