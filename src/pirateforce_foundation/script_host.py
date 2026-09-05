"""LANE-Q's sandboxed Lua host: embeds the game's own quest/trigger scripts.

WHY THIS FILE EXISTS.  ``prompts/LANE-Q.md`` (pf_bridge) charters one lane to
make the 616 shipped ``.lua`` files under ``pf_bridge/gamedata/lua/`` -- the
game's OWN quest and trigger logic, not a Python reimplementation of it --
run against this server.  Those scripts call a 160-function API surface
across 8 namespaces (Player/Quest/Trigger/Party/Mob/Instance/Guild/Scene),
none of which this server implements yet (``gamedata/PF_LUA_API_SPEC.md``,
0/160).  This module is the spike: embed Lua via ``lupa``, sandbox it, and
give every one of the 160 names a stub so a script that calls any of them
gets a safe, logged, non-crashing answer instead of a Lua "attempt to call
a nil value" error.  Namespace-by-namespace real implementations (starting
with Trigger.*, which unblocks LANE-A's M2) replace these stubs one method
at a time; see ``docs/SCRIPT_LANE.md`` for the status table.

SANDBOX.  The charter is explicit: scripts must never reach ``io``, ``os``,
``require`` or ``load`` (arbitrary file/process/code-loading access from
untrusted game-authored Lua).  ``BLOCKED_GLOBALS`` below is that list, wired
to ``nil`` on every runtime this module creates.  One measured consequence:
``gamedata/lua/utility.lua`` calls ``os.time()`` at its own top level to
seed the RNG, so loading it under this sandbox produces one caught
``LUA_SCRIPT ... ERR`` (see ``docs/SCRIPT_LANE.md`` "known findings") -- the
fail-closed behaviour working as specified, not a bug in this host.  A
future round can widen the sandbox to a narrow, safe clock/RNG seed
function instead of blocking ``os`` outright; the spike does not do that
widening itself, to keep this round's diff to what the charter asked for.

FAIL-CLOSED.  A script that fails to parse, or that raises while its
top-level chunk runs, is logged and skipped -- never allowed to raise out
of ``load_corpus`` and take a boot down with it.  Every one of the 160 API
names, when called before it has a real implementation, logs
``LUA_API_STUB <Namespace>.<Name>`` and returns a safe default -- silent
stubs are exactly what the charter forbids.

ONE LUA STATE PER SCRIPT.  The 616 files reuse entry-point names
(``ScriptStart``, ``Accept_Check``, ``Report_Run``, ...) across many quests
and triggers.  A single shared Lua state loading all 616 in sequence would
let the last file silently overwrite an earlier one's functions with the
same name -- invisible corruption a "loaded without error" check would
never catch.  So every :class:`ScriptHost` is its own sandboxed
``lupa.LuaRuntime``; the caller keeps one instance alive for as long as it
needs that particular script's functions callable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

try:
    import lupa
except ImportError as _exc:  # pragma: no cover - exercised on a machine without the package
    lupa = None
    LUPA_IMPORT_ERROR: Optional[BaseException] = _exc
else:
    LUPA_IMPORT_ERROR = None

from .lua_api import quest as lua_api_quest
from .lua_api import spec as lua_api_spec
from .lua_api import trigger as lua_api_trigger

#: Lua standard-library names the game's scripts must never reach
#: (prompts/LANE-Q.md: "sandbox: an script access io/os/require/load of Lua
#: is forbidden").  Wired to nil on every runtime this module creates.
#:
#: ``python`` is on this list for a reason worth writing down.  lupa injects
#: a ``python`` table into every Lua state it builds.  With this module's
#: constructor flags (register_eval=False, register_builtins=False) its
#: ``eval``/``builtins``/``globals``/``import_module`` entries are already
#: nil - MEASURED, not assumed - but ``as_attrgetter`` survives them, and
#: ``as_attrgetter`` flips Lua indexing on a wrapped Python object from
#: __getitem__ to getattr.  The API namespaces this host hands the scripts
#: ARE live Python objects, so that one helper would turn
#: ``python.as_attrgetter(Quest).__class__`` into the first step of the
#: ordinary __class__/__bases__/__subclasses__ walk out to the interpreter.
#: Blanking the whole table closes that door; the flags are kept anyway so
#: two independent things have to fail before a script can reach out.
BLOCKED_GLOBALS: tuple = (
    "io", "os", "require", "load", "loadstring", "loadfile", "dofile",
    "package", "debug", "collectgarbage", "python",
)

#: The one safe value every unknown API return and every non-API attribute
#: (Quest.Var1, Quest.StringVar2, Quest.RewardItem3, Quest.Active, ...)
#: resolves to.  0 keeps every arithmetic/comparison the scripts use
#: (`== 0`, `> 0`, `~=`) well-typed in Lua, where nil would raise a type
#: error the moment a script compared or added it to a number.
STUB_DEFAULT = 0


def default_logger(message: str) -> None:
    """ASCII-only stdout logger (bridge console is code page 874)."""
    print(message)


class LuaAttributeAccessDenied(AttributeError):
    """Raised when a script reaches for a Python attribute of any kind."""


def deny_every_attribute(obj, attr_name, is_setting):
    """lupa attribute_filter: no script may getattr/setattr anything.

    THE HOLE THIS CLOSES, MEASURED (pf-adversary, round s2fxf6).  Blanking
    lupa's ``python`` table is not enough, and neither is
    register_eval/register_builtins=False.  ``ApiNamespaceStub.__getitem__``
    hands a script a live Python closure for every real API name, and lupa
    lets Lua getattr any Python object it can see, so::

        Quest.GetQuestFlag.__globals__["__builtins__"]["__import__"]("os")

    reached ``__import__`` and ran ``os.system`` as the server process -
    measured returning uid=0 - through a path that touches neither the
    ``python`` table nor any blocked global.  The first fix and its tests
    both missed it because the tests probed attributes of the NAMESPACE
    object, which ``__getitem__`` intercepts, and never an attribute of the
    closure a namespace hands back.

    Nothing in this design needs attribute access from Lua: the scripts
    index namespaces (``__getitem__``) and call what comes back.  So the
    filter denies everything rather than allow-listing, and every future
    real API implementation inherits that.
    """
    raise LuaAttributeAccessDenied(
        "Lua scripts may not read or write Python attributes (%r on %s)"
        % (attr_name, type(obj).__name__)
    )


class ApiNamespaceStub:
    """One Lua global table (Player, Quest, Trigger, ...), fully stubbed.

    Indexing an unknown key never errors and never returns nil -- either
    would crash a script none of which was written expecting it.  A key
    that is one of this namespace's real API methods (per
    ``gamedata/PF_GAMEDATA_LUA_API.tsv``, vendored as ``lua_api/api_spec.tsv``)
    returns a callable that logs ``LUA_API_STUB <Namespace>.<Method>`` and
    returns STUB_DEFAULT; every other key returns STUB_DEFAULT silently,
    because Var1..Var20/StringVar1/RewardItem*/Active/Finish/... are
    per-instance script data fields the API census never counted as call
    surface -- not something this lane implements.
    """

    __slots__ = ("namespace", "_methods", "_log", "calls")

    def __init__(self, namespace: str, methods: frozenset, log: Callable[[str], None]):
        self.namespace = namespace
        self._methods = methods
        self._log = log
        self.calls: list = []

    def __getitem__(self, name):
        if name in self._methods:
            qualified = "%s.%s" % (self.namespace, name)

            def stub(*args):
                self.calls.append(qualified)
                self._log("LUA_API_STUB %s" % qualified)
                return STUB_DEFAULT

            return stub
        return STUB_DEFAULT

    def __setitem__(self, name, value):
        # Verified by grep across all 616 files (docs/SCRIPT_LANE.md): no
        # script assigns into a namespace table at runtime -- every
        # "Quest.VarN=" hit is inside a --[[ ... ]] comment documenting the
        # field, never executable code.  Accepting and discarding a write
        # keeps a future script that DOES do this from crashing the host,
        # rather than pretending we persist state nothing reads yet.
        return None


@dataclass
class ScriptResult:
    path: str
    ok: bool
    error: Optional[str] = None


@dataclass
class LoadReport:
    total: int = 0
    ok: int = 0
    failed: list = field(default_factory=list)

    @property
    def failed_paths(self):
        return [r.path for r in self.failed]


def _require_lupa() -> None:
    if lupa is None:
        raise RuntimeError(
            "lupa is not installed in this interpreter - pip install lupa "
            "(PyPI publishes wheels for Windows/macOS/Linux; see "
            "docs/SCRIPT_LANE.md for the WINDOWS_WHEEL_UNVERIFIED note)"
        ) from LUPA_IMPORT_ERROR


class ScriptHost:
    """One sandboxed Lua state carrying all 8 API namespaces.

    ``Trigger`` is no longer a plain stub table: 5 of its 17 names are real
    (``lua_api.trigger.REAL_METHODS``), backed by a
    ``lua_api.trigger.TriggerStatusRegistry``.  ``trigger_context``/
    ``trigger_registry`` let a caller say WHICH physical trigger this host's
    script is and WHICH world it reads/writes; leaving both ``None`` (every
    existing caller before this round, and every test that does not care)
    gets an isolated default context and a private, throwaway registry --
    see ``lua_api.trigger.build_namespace`` for why that default is safe.
    ``Quest`` is likewise no longer a plain stub table: 1 of its 25 names
    (``CheckOpenTime``) is real, backed by a server clock rather than any
    registry (``lua_api.trigger.py``'s own module docstring explains why
    this is the one ``Quest.*`` name that needs neither the LANE-DB state
    door nor a wire frame). ``quest_clock`` lets a caller inject a fixed
    clock for a deterministic test; leaving it ``None`` reads the real
    wall clock (``lua_api.quest.build_namespace``'s own default). Every
    other namespace is unchanged: a plain ``ApiNamespaceStub``.
    """

    def __init__(self, log: Optional[Callable[[str], None]] = None, *,
                 trigger_context: "Optional[lua_api_trigger.TriggerContext]" = None,
                 trigger_registry: "Optional[lua_api_trigger.TriggerStatusRegistry]" = None,
                 quest_clock: "Optional[lua_api_quest.Clock]" = None):
        _require_lupa()
        self.log = log or default_logger
        self.runtime = lupa.LuaRuntime(
            unpack_returned_tuples=True,
            # Both default to True in lupa and both hand a script a way out
            # of the sandbox: register_eval puts python.eval in the Lua
            # state, register_builtins puts the whole builtins module
            # there.  See BLOCKED_GLOBALS for the third door these two do
            # not close on their own, and deny_every_attribute for the
            # fourth, which is the one that mattered most.
            register_eval=False,
            register_builtins=False,
            attribute_filter=deny_every_attribute,
        )
        self.namespaces: dict = {}
        g = self.runtime.globals()
        for namespace, methods in lua_api_spec.NAMESPACE_METHODS.items():
            if namespace == "Trigger":
                stub = lua_api_trigger.build_namespace(
                    methods, self.log,
                    context=trigger_context, registry=trigger_registry)
            elif namespace == "Quest":
                stub = lua_api_quest.build_namespace(
                    methods, self.log, clock=quest_clock)
            else:
                stub = ApiNamespaceStub(namespace, methods, self.log)
            self.namespaces[namespace] = stub
            g[namespace] = stub
        for name in BLOCKED_GLOBALS:
            g[name] = None

    def load(self, source: str) -> None:
        """Compile and run a script's top-level chunk (its function defs)."""
        self.runtime.execute(source)

    def has_function(self, function_name: str) -> bool:
        return self.runtime.globals()[function_name] is not None

    def call(self, function_name: str, *args):
        fn = self.runtime.globals()[function_name]
        if fn is None:
            raise LookupError("script defines no function named %r" % function_name)
        return fn(*args)


def load_script_file(path: Path, log: Optional[Callable[[str], None]] = None, *,
                      trigger_context: "Optional[lua_api_trigger.TriggerContext]" = None,
                      trigger_registry: "Optional[lua_api_trigger.TriggerStatusRegistry]" = None,
                      quest_clock: "Optional[lua_api_quest.Clock]" = None) -> ScriptHost:
    """Load one ``.lua`` file into a fresh sandboxed :class:`ScriptHost`.

    Reads the file as bytes decoded latin-1, because latin-1 is the one
    codec that never raises on any input byte: these scripts carry
    Traditional Chinese and Thai comments in a legacy Windows codepage that
    is not valid utf-8, and utf-8 would refuse to read them at all.  Every
    ASCII syntax byte (keywords, punctuation, identifiers) survives, which
    is what the Lua parser needs.

    WHAT THIS DOES NOT DO, measured (pf-adversary, round s2fxf6).  It is
    NOT byte-preserving end to end: lupa hands Lua a utf-8 encoding of the
    str, so a source byte 0xE4 inside a string LITERAL arrives as the two
    bytes 0xC3 0xA4 - ``string.len`` says 2 and ``string.byte`` says 195,
    not 1 and 228.  Nothing in this round can observe that (every stub
    returns 0, so no script compares a literal against a real table value),
    but the day a real API returns a game string, a script doing
    string.len/string.byte/a compare against a fixed table value would
    diverge from the original engine.  Resolving it belongs to the round
    that lands that API - the choice is a runtime encoding that matches the
    scripts' own codepage, not a different read here.
    """
    host = ScriptHost(log=log, trigger_context=trigger_context,
                      trigger_registry=trigger_registry, quest_clock=quest_clock)
    source = Path(path).read_bytes().decode("latin-1")
    host.load(source)
    return host


def load_corpus(root, log: Optional[Callable[[str], None]] = None) -> LoadReport:
    """Load every ``*.lua`` file under ``root`` into its own sandboxed host.

    Fail-closed, per the LANE-Q charter: a script that fails to parse or
    raises while its top-level chunk runs is logged as
    ``LUA_SCRIPT <relative path> ERR <message>`` and recorded in the
    report's ``failed`` list, but this function itself never raises for a
    single bad script -- one broken quest file must never take a boot down
    with it. Callers that need the corpus to be perfect can inspect
    ``report.failed`` themselves.
    """
    log = log or default_logger
    root = Path(root)
    report = LoadReport()
    for path in sorted(root.rglob("*.lua")):
        report.total += 1
        rel = path.relative_to(root).as_posix()
        try:
            load_script_file(path, log=log)
        except Exception as exc:  # noqa: BLE001 - fail-closed by design, see module docstring
            message = str(exc).encode("ascii", "backslashreplace").decode("ascii")
            log("LUA_SCRIPT %s ERR %s" % (rel, message))
            report.failed.append(ScriptResult(rel, False, message))
        else:
            report.ok += 1
    return report


#: The names the original engine calls on a quest/trigger script, not names
#: this lane invented.  Measured by grepping every top-level
#: ``function Name(...)`` definition across the real 616-file corpus
#: (``gamedata/PF_GAMEDATA_LUA_API.tsv``'s sibling source, ``gamedata/lua/``):
#: these eight take zero arguments and account for 2396 of the roughly 2451
#: top-level function definitions in the corpus (measured 2026-09-05, round
#: 4jsydv) -- ``ScriptStart`` 309, ``Report_Check`` 307, ``Report_Run`` 306,
#: ``Delete_Run`` 306, ``Accept_Check`` 306, ``Accept_Run`` 305,
#: ``OpenReportUI_Run`` 293, ``OpenAcceptUI_Run`` 264.  The remaining ~10
#: definitions (``Ex_Mission``, ``Check_Level``, ``Single_Mission_Check``,
#: ``Kill_Percentage``, ...) are helper functions a script calls on itself
#: from inside one of these eight, take arguments, and are not something an
#: outside caller invokes directly -- they are exercised (or not) as a side
#: effect of calling the eight below, never called by this module directly.
STANDARD_ENTRY_POINTS: tuple = (
    "ScriptStart", "Accept_Check", "Accept_Run", "Report_Check", "Report_Run",
    "Delete_Run", "OpenAcceptUI_Run", "OpenReportUI_Run",
)

#: Fully-qualified (``Namespace.Method``) names that are REAL today, not
#: stubs -- the 5 of ``Trigger``'s 17 (``lua_api.trigger.REAL_METHODS``) and
#: the 1 of ``Quest``'s 25 (``lua_api.quest.REAL_METHODS``,
#: ``CheckOpenTime``).  Every other namespace is a plain
#: ``ApiNamespaceStub`` where 100% of tracked calls are stubs, but both
#: ``RealTriggerNamespace`` and ``RealQuestNamespace`` append BOTH real and
#: stub calls to the same ``.calls`` list (``lua_api/trigger.py``,
#: ``lua_api/quest.py``), so :func:`run_corpus_entry_points` checks the
#: qualified name against this set, not against which Python object the
#: call came from, to keep "real" and "still stubbed" from being silently
#: conflated in the corpus-wide tally.
REAL_QUALIFIED_NAMES: frozenset = frozenset(
    ["Trigger.%s" % _name for _name in lua_api_trigger.REAL_METHODS]
    + ["Quest.%s" % _name for _name in lua_api_quest.REAL_METHODS]
)


@dataclass
class EntryPointRun:
    path: str
    called: list
    ok: bool = True
    #: entry-point name -> ascii-safe exception message, keyed structurally
    #: (not a concatenated string a caller would have to substring-match to
    #: recover which of possibly several called names actually failed).
    errors: dict = field(default_factory=dict)


@dataclass
class CorpusEntryPointReport:
    """What happens when every :data:`STANDARD_ENTRY_POINTS` function a
    script defines is actually CALLED, not just loaded -- one Lua state per
    script, same isolation as :func:`load_corpus`.

    UNDERCOUNTS ON PURPOSE, SAID PLAINLY.  Every ``Quest.VarN`` /
    ``Quest.RewardItemN`` / ``Trigger.VarN`` field this harness supplies
    reads :data:`STUB_DEFAULT` (0), because no real per-instance quest/
    trigger DATA (as opposed to API surface) is wired yet.  A script branch
    gated on one of those fields being nonzero (``if Quest.RewardItem1 > 0
    then Player.AddItem(...) end`` -- half of ``q_kill5.lua``'s own
    ``Report_Run``) never runs here, so ``total_stub_calls`` is a FLOOR on
    what a real quest instance calls, not an exact count.  It is still the
    right number for the charter's own regression ask (backup work item 2:
    "count remaining LUA_API_STUB, this number must fall every week") --
    real API implementations remove calls from every script that uses them
    regardless of instance data, so the floor falls in lockstep with real
    coverage, even though its absolute value undercounts a live game.

    ``total_stub_calls`` COUNTS ONLY STUBS, MEASURED SEPARATELY FROM REAL
    CALLS -- NOT "every namespace call".  ``RealTriggerNamespace`` (5 real
    methods, 12 still-stub methods) appends EVERY call it receives, real or
    stub, to the same ``.calls`` list (``lua_api/trigger.py``); a first
    draft of this function summed every namespace's ``.calls`` length
    directly and got 5403, silently folding 346 real ``Trigger.NextStatus``/
    ``GetTriggerStatus``/``SetTriggerStatus``/``GetTeiggerStatus`` calls
    into a count that is supposed to mean "still stubbed" -- caught before
    push by hand-checking the top-line numbers against
    ``lua_api.trigger.REAL_METHODS``, not by a test (there was no test yet;
    see ``test_stub_vs_real_call_split_is_not_conflated`` in
    ``tests/test_script_lua_corpus.py``, added because of this).  This
    function now checks each qualified name against
    :data:`REAL_QUALIFIED_NAMES` (the union of ``lua_api_trigger.REAL_METHODS``
    and ``lua_api_quest.REAL_METHODS`` -- round 4jsydv wrote this split
    against the first one only, round after it added ``Quest.CheckOpenTime``
    to the same set rather than duplicating the split logic a second time)
    and tallies it as real, never stub, regardless of which Python object's
    ``.calls`` list it came from -- so the day another namespace grows a mix
    of real and stub methods, this split keeps working without changes here.
    """
    total: int = 0
    load_failed: list = field(default_factory=list)
    no_entry_point: list = field(default_factory=list)
    ran: list = field(default_factory=list)
    call_failed: list = field(default_factory=list)
    total_stub_calls: int = 0
    stub_call_counts: dict = field(default_factory=dict)
    total_real_calls: int = 0
    real_call_counts: dict = field(default_factory=dict)


def run_corpus_entry_points(root, log: Optional[Callable[[str], None]] = None, *,
                             quest_clock: "Optional[lua_api_quest.Clock]" = None) -> CorpusEntryPointReport:
    """Load every ``*.lua`` file under ``root`` AND call the standard entry
    points it defines, tallying every ``LUA_API_STUB``/``LUA_TRIGGER_REAL``
    call each one made along the way.

    Fail-closed like :func:`load_corpus`: a script that fails to load, or an
    entry point that raises when called, is logged (``LUA_SCRIPT <path> ERR
    ...`` on load failure, ``LUA_SCRIPT <path> ERR entry=<name> ...`` on a
    call failure) and recorded, but never propagates -- one script's own
    shipped bug (see ``KNOWN_ENTRY_POINT_CALL_FAILURES`` in
    ``tests/test_script_lua_corpus.py`` for two the real corpus has today)
    must never stop this function from finishing the other 615.

    NOT FAIL-CLOSED AGAINST A HANG, MEASURED (pf-adversary, round 4jsydv).
    ``try/except Exception`` catches an entry point that RAISES; it cannot
    catch one that never returns.  ``function f() return f() end`` (Lua's
    proper tail-call optimisation means this never overflows the C stack
    into a catchable error) makes ``host.call`` spin forever with no
    exception to catch -- adversary reproduced this against this exact
    function.  ``grep -rlE '\\bwhile\\b' gamedata/lua`` is empty (re-checked
    independently, round 4jsydv) so the shipped 616-file corpus contains no
    ``while`` loop today, and no unbounded-recursion pattern was confirmed
    in it either (adversary's own recursion heuristic was not reliable
    enough to rule one in or out) -- so this is a real structural gap with
    no known live trigger in the current corpus, not a false alarm to
    dismiss.  It matters most on the path ``lua_api/trigger.py`` names as
    the template a future live ``TriggerVital`` dispatch will reuse
    (``ScriptHost.call`` against a real inbound frame): a hang there would
    wedge the listener thread for every player in the scene, not just fail
    one test.  Adding an instruction-count or wall-clock budget to
    ``ScriptHost.call`` is follow-up work, out of scope for this round
    (named here rather than silently deferred) -- ``lupa.LuaRuntime``
    supports neither natively; the closest primitives are Lua's own debug
    hook (blocked, see ``BLOCKED_GLOBALS``) or a `signal.alarm`-based
    wall-clock cutoff around ``host.call``, both untried here.

    ``quest_clock`` MUST be fixed by any caller that needs a deterministic,
    repeatable call tally (every test in this module does).  Left ``None``,
    ``Quest.CheckOpenTime`` reads the real wall clock -- ``q_sea_join.lua``'s
    own ``Accept_Run`` (module docstring, ``lua_api/quest.py``) short-
    circuits its seven-window ``or`` chain the instant one evaluates true,
    so which of the seven get called, and therefore this report's own
    ``total_real_calls``, would silently depend on the real time of day the
    test happened to run -- a flakiness class this project's own house rule
    forbids (unbounded input must never crash OR silently change behaviour
    based on something a test does not control).  Callers of this function
    over the real corpus pass a fixed instant outside every literal window
    those three files use (see ``tests/test_script_lua_corpus.py``).
    """
    log = log or default_logger
    root = Path(root)
    report = CorpusEntryPointReport()
    for path in sorted(root.rglob("*.lua")):
        report.total += 1
        rel = path.relative_to(root).as_posix()
        try:
            host = load_script_file(path, log=log, quest_clock=quest_clock)
        except Exception as exc:  # noqa: BLE001 - fail-closed, see load_corpus
            message = str(exc).encode("ascii", "backslashreplace").decode("ascii")
            log("LUA_SCRIPT %s ERR %s" % (rel, message))
            report.load_failed.append(rel)
            continue

        present = [name for name in STANDARD_ENTRY_POINTS if host.has_function(name)]
        if not present:
            report.no_entry_point.append(rel)
        else:
            run = EntryPointRun(path=rel, called=present)
            for name in present:
                try:
                    host.call(name)
                except Exception as exc:  # noqa: BLE001 - fail-closed, one script must not sink the corpus
                    message = str(exc).encode("ascii", "backslashreplace").decode("ascii")
                    log("LUA_SCRIPT %s ERR entry=%s %s" % (rel, name, message))
                    run.ok = False
                    run.errors[name] = message
            if run.ok:
                report.ran.append(run)
            else:
                report.call_failed.append(run)

        for namespace in host.namespaces.values():
            calls = getattr(namespace, "calls", None)
            if not calls:
                continue
            for qualified in calls:
                if qualified in REAL_QUALIFIED_NAMES:
                    report.total_real_calls += 1
                    report.real_call_counts[qualified] = report.real_call_counts.get(qualified, 0) + 1
                else:
                    report.total_stub_calls += 1
                    report.stub_call_counts[qualified] = report.stub_call_counts.get(qualified, 0) + 1
    return report
