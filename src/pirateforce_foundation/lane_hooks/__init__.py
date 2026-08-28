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

Every hook prints a token twice: once at registration (import time, via the
``hook`` decorator below, on STDERR -- see the decorator's own comment for
why not stdout) and once at each real firing on the production path
(inside ``fire()``, also on STDERR since round lo7e03, for the same reason:
the 0xAC52 point fires on a vital every client sends, and the token landed
inside a replay tool's --json stdout artifact). These tokens are DESIGNED to be grepped by a
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
from typing import Callable

_HOOKS: dict[str, list[tuple[str, Callable[..., None]]]] = {}
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


def registered_points() -> dict[str, int]:
    """Point name -> number of hooks registered.  For tests/diagnostics only."""
    return {point: len(fns) for point, fns in _HOOKS.items()}


def _withdraw(module_name: str) -> None:
    """Remove every hook a module registered.  Used when the module turns
    out not to be production_allowed (see module docstring)."""
    for point, entries in list(_HOOKS.items()):
        _HOOKS[point] = [(m, fn) for (m, fn) in entries if m != module_name]


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
            continue
        if not getattr(module, "production_allowed", False):
            _withdraw(qualified_name)
            print(
                f"LANE_HOOK_DISCOVERY {qualified_name} SKIPPED_NOT_PRODUCTION_ALLOWED",
                file=sys.stderr,
            )


_discover()
