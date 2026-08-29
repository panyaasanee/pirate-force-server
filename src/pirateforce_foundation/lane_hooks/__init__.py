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

ROUND apk7ue, ACCURACY NOTE -- "once at each real firing" is now true of ONE
of the two registered points. CORE-REQUEST-GM-029 replaced the 0xAC52 call
site with a direct call into ``gm/chat_command_action.py``, so
``vital_inbound_chat_local_talk`` is REGISTERED AND NEVER FIRED: its
registration token still prints at import and no firing token can follow it.
Only ``vital_inbound_gm_run_command`` (0x51E9) still fires. A WIRED-v2 grep
that treats a registration token as evidence of emission would read this
package as 2/2 when the measured answer is 1/2.

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
from pathlib import Path
from typing import Callable, NamedTuple

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
    """Remove every hook AND every scene census composer a module
    registered.  Used when the module turns out not to be
    production_allowed (see module docstring).  For census composers this
    is belt-and-braces on purpose: the call site reads
    ``module_production_allowed()`` before calling anyway (option (b)),
    but a withdrawn entry also frees the scene slot: ``_discover()`` gates
    each module right after importing it, so a closed lane's claim is gone
    before the next file in filename-sort order even imports, and cannot
    block another lane from registering the same scene."""
    for point, entries in list(_HOOKS.items()):
        _HOOKS[point] = [(m, fn) for (m, fn) in entries if m != module_name]
    for scene_id, entry in list(_SCENE_CENSUS_COMPOSERS.items()):
        if entry.module == module_name:
            del _SCENE_CENSUS_COMPOSERS[scene_id]


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
