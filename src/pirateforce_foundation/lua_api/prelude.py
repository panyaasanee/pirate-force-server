"""The game's OWN startup prelude (``utility.lua``), run inside the sandbox.

WHAT THIS IS.  ``pf_bridge/gamedata/lua/utility.lua`` is not a quest and not
a trigger.  Its own header says what it is, in the shipped file, above the
one function it defines::

    --  LuaAdapter <CJK> Script
    --  <CJK> Lua <CJK>
    --  Roy20110112

Those two comment lines decode cleanly as Big5/cp950 and as nothing else
this project uses -- they are not valid utf-8, and byte 0xFC at offset 70
is undefined in cp874, the bridge console's own codepage.  Decoded they
read "LuaAdapter loads this Script at initialisation" and "you can call
these shared functions from inside Lua".

WHAT LAYER THAT IS, SAID PLAINLY (pf-adversary D11, this round, correcting
an earlier draft that wrote the paraphrase as "i.e." and dropped the
hedge): a COMMENT IN A SHIPPED DATA FILE, written by one person in 2011.
Nobody has disassembled a ``LuaAdapter`` in the client binary, and this
lane has not measured how the original engine loads this file.
``tests/test_script_lua_corpus.py``'s own long-standing nonclaim says the
engine "PLAUSIBLY loads utility.lua once into a shared global
environment".  That hedge is still the honest word and this module does
not spend it.

The file defines exactly one global, ``rate(dicevalue)`` (a percent roll:
``math.random(0, 1000000) / 10000 <= dicevalue``), and calls
``math.randomseed(os.time())`` at its own top level to seed the RNG.

WHY IT MATTERS, AND EXACTLY HOW MUCH.  Grepping the corpus for a call to
`rate` returns 18 paths; one is this file (it DEFINES `rate`), so 17
shipped scripts CALL it, over 34 call sites.  The exact grep is in
`tests/test_script_lua_prelude.py` beside the pinned list.  Without the
prelude `rate` is a nil global.

**13**, not 17, is the number the prelude repairs, and the corrected
figure is not a guess: ``tests/test_script_lua_corpus.py::
KNOWN_ENTRY_POINT_CALL_FAILURES`` -- this lane's own instrument, readable
without a Lua runtime -- has always pinned exactly those 13 (pf-adversary
D3, this round, who then reproduced it on a real sweep: 17 call failures
before, 4 after).  The other four callers never reach ``rate`` at all and
could not: ``t_escaphk_sp.lua`` returns on an empty backpack,
``t_getm&cat_himd_q1_rat.lua`` and ``t_getmorpopmo_q1.lua`` return on
``0 >= 0``, and ``t_opnplc_rat_lv&buf.lua`` returns because
``Player.CheckBuff`` stubs to 0 and **0 is truthy in Lua**.

"Dies before doing anything" is also too strong for five of the 13
(``t_ins_ratx3/4/5/6_lv.lua``, ``t_opnplc_rat_lv.lua``): they call
``Player.GetLv()`` -- a real method -- first.  What IS true of all 13 is
that their entry point stops at the ``rate`` line and their body never
runs.

AND THE ROLL STILL FAILS.  Measured by pf-adversary on the real corpus:
turning the prelude on moves 22 API calls (5449 -> 5471), and **not one of
the 34 ``rate(...)`` sites takes the true branch**, because
``Trigger.VarN`` reads ``STUB_DEFAULT`` = 0, so every roll is ``rate(0)``.
In particular ``Player.AddExp``/``Player.AddSkillPoint`` stay at ZERO
reached call sites: theirs sit in the ``else`` of
``if (not rate(Trigger.Var2))`` and the ``not`` sends every run down the
first branch.  An earlier draft of this docstring said the opposite AND
called those two names "real" when ``lua_api/player.py`` still lists them
in ``STILL_STUBBED`` -- both wrong, both corrected here rather than left
for a reader to trip over.

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

import hashlib
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
#: extracted bytes that actually reach Lua).  ENFORCED by
#: :func:`read_prelude`, and the reason is a measured one, not a taste
#: (pf-adversary D2, this round).  A prelude is the ONE chunk this host
#: runs whose global writes are restored from a Python ``finally``, i.e.
#: OUTSIDE any protected Lua call.  Adversary fed an edited prelude
#: (``setmetatable(_G, {__newindex = function() error('locked') end})``)
#: and the restore loop took the whole process down -- ``PANIC:
#: unprotected error in call to Lua API``, SIGABRT, exit 134, no log line
#: at all.  The SAME Lua text as an ordinary SCRIPT is catchable at HEAD
#: (the write happens inside the protected chunk, ``load_corpus`` logs one
#: ``LUA_SCRIPT ... ERR locked`` and finishes the other 615), so this is a
#: surface the prelude seam ADDS.  An earlier draft of this constant said
#: "recorded, NOT enforced" -- which put the answer in the file and
#: declined to use it, the exact shape this project's house rules call
#: out.  So: bytes that do not match are not run.  Refusing is cheap
#: (``read_prelude`` returns None, the host is the host of yesterday, one
#: log line says which digest it saw) and running unknown bytes is not.
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

#: What a prelude must leave behind for :func:`run_prelude` to call it a
#: success.  Exactly the shipped file's one global; a prelude that runs
#: clean and installs nothing is a broken prelude, not an OK one.
REQUIRED_GLOBALS: tuple = ("rate",)

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

    ONE ``Prelude`` SEEDS EVERY HOST IT IS GIVEN TO IDENTICALLY, AND THAT
    IS AN OPEN DESIGN QUESTION, NOT A SETTLED CHOICE (pf-adversary D5, this
    round, measured: five independent hosts built from one ``Prelude`` all
    answered 465252 to their first ``math.random(0, 1000000)``; and
    ``_time.time`` has one-second resolution, so re-reading per host does
    not fix it either).  ``load_corpus`` and ``run_corpus_entry_points``
    take a single ``Prelude`` and hand it to all 616 hosts, which is the
    only usage shape this API offers -- so a dispatcher that reads one at
    boot would give every player at every rate-gated trigger the same roll
    for the life of the process, and the same roll again after they walk
    away and come back.

    The original engine seeds ONCE, at LuaAdapter init, into one advancing
    stream every script shares; seeding per host inverts that.  This lane
    will NOT invent the replacement policy in the same round it found the
    problem: whether ``rate``'s stream is per-scene world state, per
    character, or genuinely per invocation -- and what seeds it so two
    players touching two triggers in the same second differ -- is a
    decision with owners (PANYA-DECISION 20260905_1057 puts world state in
    the server process, per scene), and it is asked of COO by letter this
    round.  Until it is answered the seam stays OFF by default, so no
    player can be hit by this: it is a defect in a capability nothing in
    production calls yet, written down rather than quietly shipped.
    """

    source: str
    origin: str
    seed: int


def read_prelude(root, clock: Optional[Callable[[], float]] = None,
                 log: Optional[Callable[[str], None]] = None,
                 expect_digest: Optional[str] = EXTRACTED_PRELUDE_SHA256) -> Optional[Prelude]:
    """Read ``<root>/utility.lua``, or ``None`` when there is none to run.

    ``None`` rather than a raise: a deployment without the game's script
    tree beside it is a supported configuration (the server runs, the 616
    scripts simply are not there), and this function is called on that
    path.  A caller that REQUIRES a prelude checks for None itself.

    THREE ``None``S, AND EACH ONE SAYS SO (pf-adversary D7, this round: the
    first draft returned a silent ``None`` for a missing file, which is
    indistinguishable from "the caller asked for no prelude" and reverts a
    deployment to yesterday's behaviour with nothing in the log to find):
    ``LUA_PRELUDE ABSENT`` when the root ships no such file,
    ``LUA_PRELUDE REFUSED`` when its bytes are not the ones this lane
    measured (see :data:`EXTRACTED_PRELUDE_SHA256` for why that is fatal
    rather than interesting), and ``LUA_PRELUDE READ`` when one is
    returned.  ``log`` defaults to a sink so an existing caller's behaviour
    does not change; a caller that wants the line passes its own.

    ``clock`` is the seed source, injectable so a test gets a repeatable
    RNG.  Default is wall clock, which is what the original engine's
    ``os.time()`` gives the shipped file.  A SINGLE ``Prelude`` HANDED TO
    A SWEEP SEEDS EVERY HOST IDENTICALLY -- see :class:`Prelude`.

    ``expect_digest=None`` disables the check.  It exists for a test that
    needs to read a deliberately different prelude off disk, and for the
    round that decides a second shipped prelude is legitimate; it is not a
    production escape hatch, and no caller in this package passes it.
    """
    log = log or (lambda _message: None)
    path = Path(root) / PRELUDE_FILENAME
    if not path.is_file():
        log('LUA_PRELUDE ABSENT origin="%s"' % (path.as_posix(),))
        return None
    raw = path.read_bytes()
    if expect_digest is not None:
        seen = hashlib.sha256(raw).hexdigest()
        if seen != expect_digest:
            log('LUA_PRELUDE REFUSED origin="%s" sha256=%s expected=%s'
                % (path.as_posix(), seen, expect_digest))
            return None
    source = raw.decode("latin-1")
    seed = int((clock or _time.time)())
    log('LUA_PRELUDE READ origin="%s" bytes=%d seed=%d'
        % (path.as_posix(), len(raw), seed))
    return Prelude(source=source, origin=path.as_posix(), seed=seed)


def run_prelude(runtime, prelude: Prelude, log: Callable[[str], None],
                blocked_globals) -> bool:
    """Run ``prelude`` in ``runtime`` with a one-key ``os``, then take it back.

    Returns True when the chunk ran AND left the helper it exists to
    install; False otherwise.

    "AND LEFT THE HELPER" IS THE WHOLE POINT (pf-adversary D6, this round).
    The first draft compared the token against "the chunk did not raise",
    which is a delta from the previous state rather than the target -- and
    adversary made it fire: a prelude that is empty, comment-only,
    truncated by the extractor, or has ``rate`` renamed logged
    ``LUA_PRELUDE OK`` with ``rate`` still nil, after which 13 scripts died
    on a nil ``rate`` and were billed as broken quest files.  So the check
    is against :data:`REQUIRED_GLOBALS` -- what a caller actually needs to
    be true -- and a chunk that ran but installed nothing logs
    ``LUA_PRELUDE ERR reason=no_helpers`` and answers False.

    DOES NOT RAISE FOR A PRELUDE THAT RAISES.  It can still raise, and
    worse, for a prelude that is not the shipped file: the ``finally``
    below writes Lua globals OUTSIDE any protected call, so a prelude that
    installs a raising ``__newindex`` on ``_G`` takes the process down with
    a C-level PANIC that no ``except`` can see (measured, pf-adversary D2 --
    see :data:`EXTRACTED_PRELUDE_SHA256`, which is why
    :func:`read_prelude` now refuses bytes it does not recognise).  An
    earlier draft of this docstring said "Never raises" flatly.  It is not
    true, and the honest sentence is the one above.

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
        missing = [name for name in REQUIRED_GLOBALS
                   if globals_table[name] is None]
        if missing:
            log('LUA_PRELUDE ERR reason=no_helpers missing=%s origin="%s"'
                % (",".join(missing), prelude.origin))
            return False
        log('LUA_PRELUDE OK origin="%s" seed=%d' % (prelude.origin, prelude.seed))
        return True
    finally:
        seed_clock.disarm()
        # `os` FIRST, not in `blocked_globals` order (pf-adversary D8):
        # that tuple starts with "io", and the one name this function
        # actually moved would have been restored LAST -- so a raise on any
        # earlier write left the shim installed.  Now the shim is the first
        # thing taken back, and the rest is the belt to that brace.
        globals_table["os"] = None
        for name in blocked_globals:
            globals_table[name] = None


__all__ = [
    "DISARMED_TIME",
    "EXTRACTED_PRELUDE_BYTES",
    "EXTRACTED_PRELUDE_SHA256",
    "OS_SHIM_KEYS",
    "PRELUDE_FILENAME",
    "REQUIRED_GLOBALS",
    "Prelude",
    "SeedClock",
    "read_prelude",
    "run_prelude",
]
