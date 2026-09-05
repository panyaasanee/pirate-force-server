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

from .lua_api import spec as lua_api_spec

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
    """One sandboxed Lua state carrying all 8 stub API namespaces."""

    def __init__(self, log: Optional[Callable[[str], None]] = None):
        _require_lupa()
        self.log = log or default_logger
        self.runtime = lupa.LuaRuntime(
            unpack_returned_tuples=True,
            # Both default to True in lupa and both hand a script a way out
            # of the sandbox: register_eval puts python.eval in the Lua
            # state, register_builtins puts the whole builtins module
            # there.  See BLOCKED_GLOBALS for the third door these two do
            # not close on their own.
            register_eval=False,
            register_builtins=False,
        )
        self.namespaces: dict = {}
        g = self.runtime.globals()
        for namespace, methods in lua_api_spec.NAMESPACE_METHODS.items():
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


def load_script_file(path: Path, log: Optional[Callable[[str], None]] = None) -> ScriptHost:
    """Load one ``.lua`` file into a fresh sandboxed :class:`ScriptHost`.

    Reads the file as bytes decoded latin-1 (one byte in, one Lua string
    byte out) rather than utf-8/cp874: these scripts carry Traditional
    Chinese and Thai comments in a legacy Windows codepage that is not
    valid utf-8, and Lua's parser only cares that ASCII syntax bytes
    (keywords, punctuation, identifiers) round-trip -- which latin-1
    guarantees for any input -- not what a comment or string literal means.
    """
    host = ScriptHost(log=log)
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
