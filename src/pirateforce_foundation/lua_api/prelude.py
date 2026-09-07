"""The game's OWN startup prelude (``utility.lua``), run inside the sandbox.

WHAT THIS IS.  ``pf_bridge/gamedata/lua/utility.lua`` is not a quest and not
a trigger.  Its own header says what it is, in the shipped file, above the
one function it defines::

    --  LuaAdapter <mojibake> Script
    --  <mojibake> Lua <mojibake>
    --  Roy20110112

-- i.e. the file the original engine's LuaAdapter loads at startup so that
every quest/trigger script can call the shared helpers in it.  It defines
exactly one global, ``rate(dicevalue)`` (a percent roll:
``math.random(0, 1000000) / 10000 <= dicevalue``), and calls
``math.randomseed(os.time())`` at its own top level to seed the RNG.

WHY IT MATTERS, MEASURED.  18 shipped corpus files across 34 call sites gate
their ENTIRE body behind ``rate(...)``::

    grep -rlE '(^|[^A-Za-z_])rate[[:space:]]*\\(' --include=*.lua gamedata/lua
    -> 18 files

Without the prelude, ``rate`` is a nil global, so those 18 files do not run
partially -- their entry point dies on the FIRST line that matters
(``attempt to call a nil value (global 'rate')``, measured round ``yfeauz``,
nonclaim 5) and the script accomplishes nothing at all.  Two of them
(``t_getm_rat_exp&sp.lua``, ``t_inskyev_getm_rat_exp&sp.lua``) are the only
corpus call sites of ``Player.AddExp``/``Player.AddSkillPoint``, which is
why those two names show a real implementation and a zero call count in the
same table.

THE ONE SANDBOX HOLE THIS OPENS, AND HOW NARROW IT IS.  ``script_host``
nils ``os`` for every runtime it builds (``BLOCKED_GLOBALS``), so the
shipped prelude cannot run as-is -- ``os.time()`` on its top line raises,
and that is exactly the caught ``LUA_SCRIPT ... ERR`` the spike documented
and deliberately left alone.  This module is the narrow widening
``script_host``'s own module docstring named as the follow-up: for the
duration of the prelude chunk ONLY, ``os`` is a LUA TABLE built here with
exactly one key, ``time``, bound to :class:`SeedClock` -- a host callable
that answers one injected integer.  It is not Python's ``os`` module, it
cannot reach the filesystem or the process, and nothing else from the real
``os`` library is on it.

Three separate things keep it from leaking past the prelude:

1. :func:`run_prelude` re-nils EVERY name in the caller's blocked list in a
   ``finally``, so the shim is gone whether the prelude returned, raised,
   or raised while raising.  A game script's chunk is loaded later, by
   ``ScriptHost.load``, and sees ``os == nil`` like it does today.
2. :class:`SeedClock` DISARMS itself in that same ``finally``.  So even a
   prelude that squirrels the shim away in a global (``_G.saved = os``) --
   the shipped one does not, but a future one could, and a hostile edit to
   the shipped one certainly would -- hands a later script a ``time`` that
   answers :data:`DISARMED_TIME` and logs ``LUA_PRELUDE_OS_DISARMED``
   rather than a live clock.  Fail-closed and LOUD, the house rule.
3. Nothing here touches ``io``/``require``/``load``/``package``/``debug``/
   lupa's ``python`` table.  ``os`` is the only name the shipped prelude
   needs, so ``os`` is the only name this shim carries.

NOT A PYTHON REIMPLEMENTATION.  ``rate`` is not written here.  This module
reads the shipped bytes and hands them to Lua; the roll a script gets is
the roll the game's own file computes.  The charter is explicit about that
("the shipped scripts are the spec -- do not rewrite quest logic in Python
when the script already exists"), and the difference is observable: the
shipped ``rate`` compares against ``math.random(0, 1000000) / 10000``, so
its resolution is 1/10000 of a percent, not the 1/100 a hand-written
percent roll would almost certainly have used.

READ THE SAME WAY THE SCRIPTS ARE.  ``latin-1``, for the reason
``script_host.load_script_file``'s docstring gives at length: it is the one
codec that never raises on any input byte, and these files carry legacy
Windows-codepage comment bytes that are not valid utf-8.  The prelude file
in particular is 450 bytes of which the first ~200 are mojibake Big5
comments; every byte that MATTERS to the Lua parser is ASCII.

WHAT THIS MODULE DOES NOT DO.  It does not turn itself on.  Every caller
passes a prelude explicitly, and every existing caller passes none, so the
corpus census in ``tests/test_script_lua_corpus.py`` -- whose exact pins
(``BASELINE_TOTAL_STUB_CALLS``, ``BASELINE_TOTAL_REAL_CALLS``,
``KNOWN_LOAD_FAILURES``, ``KNOWN_ENTRY_POINT_CALL_FAILURES``) are this
lane's measuring instrument -- keeps measuring exactly what it measured
before.  Flipping the default changes all four of those numbers at once,
and this round could not measure the new ones: this container has no
``lupa`` and COO-DECISION ``20260907_1941`` forbids installing a package
mid-round.  Pinning numbers nobody measured is the one thing the house
rules forbid outright, so the seam ships measured-off rather than guessed-
on.  ``tests/test_script_lua_prelude.py`` proves the capability against the
18 real files by DIFFERENCE (same corpus, same clock, prelude on vs off),
which needs no new absolute number.

AND IT PUTS NOTHING ON A PLAYER'S SCREEN.  There is still no dispatcher
that runs a trigger script when a player sails into a trigger; that seam
lives in ``runtime.py``, which is not this lane's to edit.  What changed is
that 18 shipped scripts can now execute their body at all when a caller
hands them the prelude the original engine hands them.
"""
from __future__ import annotations

import time as _time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from .vendored import ascii_safe

#: The shipped prelude's filename, as the engine's own LuaAdapter names it
#: (``Data/Script/utility.lu_`` -> ``gamedata/lua/utility.lua``,
#: ``gamedata/PF_GAMEDATA_LUA_INDEX.tsv`` row 617).
PRELUDE_FILENAME = "utility.lua"

#: sha256 of the EXTRACTED prelude this lane read while writing this module
#: (``gamedata/PF_GAMEDATA_LUA_INDEX.tsv``'s ``src_sha256`` column is the
#: digest of the packed ``.lu_``, 297 bytes; this is the digest of the 450
#: extracted bytes that actually reach Lua).  Recorded, NOT enforced: this
#: module reads whatever prelude the caller's corpus root ships, and a
#: mismatch is a fact for a test to report, not a reason to refuse to run
#: a server.  See ``tests/test_script_lua_prelude.py``.
EXTRACTED_PRELUDE_SHA256 = (
    "c97c8a08ae524c6fc7f8603e143b4293adaed9bd260e92aee74baea8c7042635")

#: Length in bytes of that same extracted file, pinned beside the digest so
#: a test can report "wrong size" separately from "wrong content".
EXTRACTED_PRELUDE_BYTES = 450

#: What the disarmed clock answers.  0, for the same reason
#: ``script_host.STUB_DEFAULT`` is 0: it keeps every arithmetic and
#: comparison a script might do with it well-typed in Lua, where nil would
#: raise the moment anything compared or added it.
DISARMED_TIME = 0

#: The only key the prelude-time ``os`` shim carries.  A tuple rather than a
#: bare string so a reader greps one name and finds the whole surface.
OS_SHIM_KEYS: tuple = ("time",)


class SeedClock:
    """The one value the prelude-time ``os`` shim can answer, and only then.

    Armed while :func:`run_prelude` runs the prelude chunk; disarmed in that
    function's ``finally``.  Disarmed, it logs and returns
    :data:`DISARMED_TIME` -- it never raises, because a raise out of a Lua
    call is the failure mode ``script_host``'s whole fail-closed design
    exists to avoid.

    Takes ``*args`` and ignores them: ``os.time()`` in the shipped prelude
    passes none, but Lua's real ``os.time`` accepts an optional table, and a
    closure that raises TypeError on an argument nobody in the corpus passes
    today would be a landmine for the first script that does (the same
    lesson ``lua_api/trigger.py`` records under LUA_TRIGGER_BAD_ARITY).
    """

    def __init__(self, seed: int, log: Callable[[str], None]):
        self.seed = int(seed)
        self._log = log
        #: False once the prelude chunk is done.  Public so a test can read
        #: it without reaching into the shim's Lua table.
        self.armed = True

    def __call__(self, *args: Any) -> int:
        if not self.armed:
            self._log("LUA_PRELUDE_OS_DISARMED time")
            return DISARMED_TIME
        return self.seed

    def disarm(self) -> None:
        self.armed = False


@dataclass(frozen=True)
class Prelude:
    """One prelude's source, where it came from, and the seed it will get.

    ``origin`` is carried so a log line names the file rather than saying
    "the prelude" -- a server whose corpus root is misconfigured should be
    able to say WHICH utility.lua it ran.
    """

    source: str
    origin: str
    seed: int


def read_prelude(root, clock: Optional[Callable[[], float]] = None) -> Optional[Prelude]:
    """Read ``<root>/utility.lua``, or ``None`` when the root ships none.

    ``None`` rather than a raise: a deployment without the game's script
    tree beside it is a supported configuration (the server runs, the 616
    scripts simply are not there), and this function is called on that
    path.  A caller that REQUIRES a prelude checks for None itself.

    ``clock`` is the seed source, injectable so a test gets a repeatable
    RNG.  Default is wall clock, which is what the original engine's
    ``os.time()`` gives the shipped file.
    """
    path = Path(root) / PRELUDE_FILENAME
    if not path.is_file():
        return None
    source = path.read_bytes().decode("latin-1")
    seed = int((clock or _time.time)())
    return Prelude(source=source, origin=path.as_posix(), seed=seed)


def run_prelude(runtime, prelude: Prelude, log: Callable[[str], None],
                blocked_globals) -> bool:
    """Run ``prelude`` in ``runtime`` with a one-key ``os``, then take it back.

    Returns True when the chunk ran, False when it raised.  Never raises:
    a prelude that fails must leave a host that still loads scripts (they
    simply see a nil ``rate`` again, exactly as today), not a host that
    refuses to exist.

    ``blocked_globals`` is passed in rather than imported from
    ``script_host`` -- this module is imported BY ``script_host``, and the
    sandbox list has exactly one owner.  Every name on it is re-nilled here,
    not just ``os``: this ``finally`` is the last thing that touches the
    globals before a game script's chunk is loaded, so it restores the whole
    invariant rather than the one name this function happened to move.
    """
    globals_table = runtime.globals()
    seed_clock = SeedClock(prelude.seed, log)
    globals_table["os"] = runtime.table(time=seed_clock)
    try:
        runtime.execute(prelude.source)
    except Exception as exc:  # noqa: BLE001 - fail-closed, see docstring
        log('LUA_PRELUDE ERR %s origin="%s"' % (ascii_safe(exc), prelude.origin))
        return False
    else:
        log('LUA_PRELUDE OK origin="%s" seed=%d' % (prelude.origin, prelude.seed))
        return True
    finally:
        seed_clock.disarm()
        for name in blocked_globals:
            globals_table[name] = None


__all__ = [
    "DISARMED_TIME",
    "EXTRACTED_PRELUDE_BYTES",
    "EXTRACTED_PRELUDE_SHA256",
    "OS_SHIM_KEYS",
    "PRELUDE_FILENAME",
    "Prelude",
    "SeedClock",
    "read_prelude",
    "run_prelude",
]
