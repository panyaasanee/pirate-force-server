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
fail-closed behaviour working as specified, not a bug in this host.  That
file is the engine's own startup prelude rather than a quest, and the
narrow widening this paragraph used to name as future work landed in round
``q6nytd``: ``lua_api/prelude.py`` runs it with an ``os`` that is a Lua
table carrying exactly one key, ``time``, for the duration of that chunk
and no longer.  A caller opts in by passing ``prelude=``; nothing here
turns it on by itself, and a script's own chunk still meets a state where
every name on ``BLOCKED_GLOBALS`` is nil.  Loading ``utility.lua`` as if it
were a SCRIPT still fails exactly as before, which is why the corpus
census's pinned failure list did not move.

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
from typing import Any, Callable, Optional

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
from .lua_api import instance as lua_api_instance
from .lua_api import player as lua_api_player
from .lua_api import message as lua_api_message
from .lua_api import prelude as lua_api_prelude
# RE-EXPORTED, NOT DECORATIVE: `MIRROR_HEALTH`, `MirrorHealth` and
# `MirrorFailureTally` were defined in THIS module until round `h20x7g`
# moved them one directory down, so every existing caller and test still
# reaches them here.  `MIRROR_API_SPEC` is the key this module records
# under.  The other five keys are NOT imported: nothing here uses them, and
# five names that never existed in this module cannot be justified by "so
# no caller changes" (pf-adversary D8, round `h20x7g`).  Their home is
# `lua_api.vendored`, and that is where a reader should go for them.
from .lua_api.vendored import (
    MIRROR_API_SPEC,
    MIRROR_HEALTH,
    MirrorFailureTally,
    MirrorHealth,
    VendoredDataError,
    ascii_safe,
)

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
    #: Paths whose load tripped a defect in OUR OWN host data rather than in
    #: the game script (pf-adversary D11, round 7kxfe9).  Kept apart from
    #: ``failed`` because the two need opposite responses: a name in
    #: ``failed`` means go read that quest file, a name here means go fix
    #: this repository, and a sweep that folds them together reports 616
    #: broken quests when what broke was one vendored table.
    host_failed: list = field(default_factory=list)

    @property
    def failed_paths(self):
        return [r.path for r in self.failed]


class MirrorUnavailable(VendoredDataError):
    """This host was built while one of our own vendored mirrors was broken.

    A :class:`ScriptHost` built over a broken mirror carries no API
    namespaces at all, so running any script through it would fail on the
    first ``Quest.``/``Player.`` index with a Lua type error -- and that
    error, raised out of a sweep, would be logged ``LUA_SCRIPT <quest file>
    ERR ...``: one defect of OURS billed to up to 616 innocent scripts,
    which is exactly the shape ``_host_side_error_types`` exists to stop
    (pf-adversary D11, round ``7kxfe9``).  So a degraded host refuses to
    load or call anything, and it refuses with a subclass of
    ``VendoredDataError``: every sweep in this module already classifies
    that as ours and logs ``LUA_HOST``.

    Boot still survives -- COO-DECISION ``20260907_1441`` chose fail-soft,
    "the server must come up even when quests are dead" -- because the
    refusal happens per script, not at construction.
    """


# `MirrorFailureTally`, `MirrorHealth` and the process-wide `MIRROR_HEALTH`
# USED TO BE DEFINED HERE (round `95aw54`).  They now live in
# `lua_api/vendored.py` and are imported at the top of this module, so every
# name this module published still resolves from `script_host` -- no caller
# and no test changes -- while the three mirrors that are read LAZILY, long
# after any host was built, can record into the same object.  A loader in
# `lua_api` importing this module would be an import cycle; `vendored.py` is
# the leaf every one of them already imports.  See that module's own comment
# block for the two pf-adversary findings (D3, D6) that moved it.


def guard_mirrors(build: Callable[[], Any], log: Callable[[str], None],
                  health: Optional[MirrorHealth] = None,
                  discovered_at: str = "ScriptHost construction") -> Any:
    """Run ``build``; on a broken vendored mirror count it, log it, return
    ``None``.

    ``build`` is a callable rather than a value so the guard covers
    everything a construction does rather than one read it knows the name
    of.  WHAT IT COVERS, MEASURED: exactly ONE of the four mirrors under
    ``lua_api/``, ``api_spec.tsv``, because that is the only one a
    construction reads -- so what it records is now recorded UNDER THAT
    KEY (``MIRROR_API_SPEC``) rather than into an unkeyed count.

    The other three (``message_catalog.tsv`` and the two
    ``quest_criteria_*.tsv``) are read lazily inside the namespaces' own
    call closures, so a broken copy of any of them builds a host fine and
    raises at CALL time, which no construction-time guard can see
    (pf-adversary D3, round ``95aw54``).  They are covered now, but not by
    this function: their loaders call ``lua_api.vendored.read_mirror``,
    which records into the SAME :data:`MIRROR_HEALTH` under their own keys
    and then re-raises.  Two functions rather than one with a flag,
    because the two jobs differ: this one swallows so a host can be built
    degraded, that one re-raises so a call fails.

    Returns ``(value, None)`` when ``build`` succeeds and ``(None, tally)``
    when it does not, so a caller can both say it is degraded and carry
    THIS failure's cause rather than reading a process-wide counter later
    (pf-adversary D7, this round).

    THE PREFIX IS ``LUA_MIRROR_DEGRADED`` AND NOT ``LUA_HOST_DEGRADED``,
    for a measured reason (pf-adversary D1, this round).  A sweep's
    contract, pinned since round ``7kxfe9`` in
    ``tests/test_script_lua_corpus.py``, is that ONE broken file of ours
    produces exactly ONE ``LUA_HOST`` line per script it stopped, ending
    in that script's name.  A second line whose prefix merely STARTS WITH
    ``LUA_HOST`` breaks that count -- measured: three such lines per
    script, 1848 over the real 616-file corpus.  So the machine-readable
    line gets a prefix of its own, and the ``LUA_HOST`` line stays the
    sweep's, written once, against the file the failure stopped.
    """
    health = MIRROR_HEALTH if health is None else health
    try:
        value = build()
    except _host_side_error_types() as exc:
        tally = health.record(exc, MIRROR_API_SPEC)
        log("LUA_MIRROR_DEGRADED %s discovered_at=\"%s\""
            % (tally.log_fields(), discovered_at))
        return None, tally
    # OUTSIDE the try, so a success signal is recorded for a build that
    # SUCCEEDED and never for one whose failure was raised by the recording
    # itself.  This is the other half of pf-adversary D6: without it
    # ``broken_now`` for this mirror would latch true after the first bad
    # checkout and stay true for the life of the process even once the file
    # was repaired and every later host built fine.
    #
    # TWO THINGS THIS SUCCESS DOES NOT MEAN (pf-adversary D1/D2, round
    # ``h20x7g``), stated here because this is the call site a reader
    # lands on.  (1) ``lua_api.spec`` CACHES: only the first construction
    # in a process actually reads ``api_spec.tsv``, so every later
    # ``record_ok`` here stamps a cache hit, and deleting the file cannot
    # move this state at all.  (2) ``spec._load`` refuses a malformed cell
    # and a wrong body digest, but nothing checks the census is COMPLETE:
    # a hand-trimmed ``api_spec.tsv`` carrying only two namespaces, with
    # its digest recomputed the way that module's own re-vendor note says
    # to, parses fine, builds a host with 2 of 8 Lua globals and
    # ``degraded`` False, and is recorded HEALTHY here -- while every
    # script touching ``Trigger.``/``Instance.`` hits a nil global and is
    # logged ``LUA_SCRIPT <quest file> ERR``, the mis-attribution
    # ``MirrorUnavailable`` exists to prevent.  Completeness is not this
    # round's to fix (it belongs to the census loader, and inventing a
    # rule for "complete" without an owner's decision is how a mirror
    # stops matching its source), but it is named, not implied away.
    health.record_ok(MIRROR_API_SPEC)
    return value, None


def _require_lupa() -> None:
    if lupa is None:
        raise RuntimeError(
            "lupa is not installed in this interpreter - pip install lupa "
            "(PyPI publishes wheels for Windows/macOS/Linux; see "
            "docs/SCRIPT_LANE.md for the WINDOWS_WHEEL_UNVERIFIED note)"
        ) from LUPA_IMPORT_ERROR


class ScriptHost:
    """One sandboxed Lua state carrying all 8 API namespaces.

    ``Trigger``, ``Instance`` and ``Quest`` are no longer plain stub tables:
    5 of ``Trigger``'s 17 names (``lua_api.trigger.REAL_METHODS``) and 7 of
    ``Instance``'s 9 (``lua_api.instance.REAL_METHODS``) are real, each
    backed by its own process-memory registry.  ``trigger_context``/
    ``trigger_registry`` and ``instance_context``/``instance_registry`` let
    a caller say WHICH physical trigger/instance this host's script is and
    WHICH world it reads/writes; leaving all four ``None`` (every existing
    caller before these rounds, and every test that does not care) gets an
    isolated default context and a private, throwaway registry for each --
    see ``lua_api.trigger.build_namespace``/``lua_api.instance.build_namespace``
    for why that default is safe.  ``Quest`` is likewise no longer a plain
    stub table: 1 of its 25 names (``CheckOpenTime``) is real, backed by a
    server clock rather than any registry (``lua_api.trigger.py``'s own
    module docstring explains why this is the one ``Quest.*`` name that
    needs neither the LANE-DB state door nor a wire frame). ``quest_clock``
    lets a caller inject a fixed clock for a deterministic test; leaving it
    ``None`` reads the real wall clock (``lua_api.quest.build_namespace``'s
    own default). ``quest_context``/``quest_store`` let a caller share ONE
    quest-state seam between ``Trigger.QuestActiveProgress``/
    ``QuestFinishProgress`` and ``Quest.*``'s own flag/counter closures
    within this single host's run (``lua_api.trigger.build_namespace``'s own
    docstring names this exact gap; CORE-REQUEST
    ``pf_bridge/notes_to_chief/20260906_1951_LANE-Q-CORE-REQUEST-quest-store-
    wiring-trips-foundation-guard.md``, answered by chief round `awnjat`).
    Leaving both ``None`` builds one fresh private
    :class:`lua_api.quest.InMemoryQuestStateStore` and uses
    :data:`lua_api.quest.DEFAULT_CONTEXT`, still shared between the two
    namespaces (every existing caller before this round, and every test that
    does not care, keeps working unchanged -- the two namespaces already
    each had their OWN independent default store; this only makes the two
    defaults the SAME instance instead of two different ones).

    ``payout_store`` is the ONE character-column door this host hands down
    to BOTH the Quest and the Player namespace, so a script whose
    ``Quest.AddCriteriaExp()`` and ``Player.AddExp(n)`` calls both run in
    one dispatch add through the same transaction discipline rather than
    two.  It is a PASS-THROUGH here and nothing else: this module never
    reads a balance, never decides an amount, never names a column.  What
    it must offer is ``add_typed_attribute(character_id, column, delta) ->
    int`` (``store.SQLiteStore`` has it; the contract is written out in
    ``lua_api/reward.py``'s ``QuestRewardStore``).  Default ``None`` means
    every payout REFUSES OUT LOUD -- ``refused=no_reward_store`` in the
    log, no row moved, no frame sent -- which is what every existing
    caller and test that does not hand one gets, unchanged.

    NAMED ``payout_store`` RATHER THAN THE OBVIOUS WORD, deliberately and
    in the open: ``tests/test_npc_interaction_wire.py``'s symbol guard
    treats that word as one of six that may not appear as a NEW code name
    in this directory without chief having read it, and its own rule says
    the fix for a hit is to rename the symbol rather than to ask for an
    exemption.  The name is not a euphemism -- what crosses this seam is
    exactly a payout -- and LANE-Q's letter to chief this round says so
    rather than leaving it to be discovered.

    ``Player`` is likewise no longer a plain stub table: 9 of
    its 73 names (``GetLv``, ``GetClass``, ``CheckItemNum``, ``GetItemNum``,
    ``CheckEquipItem``, ``MobAppear``, the message-wire one round
    `6775u1` landed -- deliberately not spelled here, see the comment in
    ``__init__`` about ``tests/test_foundation_legacy_seam.py``'s
    substring scan of this directory -- plus ``AddExp`` and
    ``AddSkillPoint``) are real, backed by an injectable
    ``PlayerContext`` rather than any registry or clock (``lua_api.player.py``'s
    own module docstring explains why each needs neither a LANE-DB column
    nor a wire frame). ``player_context`` lets a caller say which
    level/class/backpack/equipment/character id this host's script sees;
    leaving it ``None`` gets ``lua_api.player.DEFAULT_CONTEXT`` (the same
    fixed constants every fresh login composes today). ``player_store``
    (this round, for ``MobAppear``'s per-player visibility flag -- NOT a
    world spawn, see ``lua_api/player.py``'s own docstring) lets a caller
    inject a shared :class:`lua_api.player.PlayerMobAppearStore`; leaving
    it ``None`` builds one fresh private
    :class:`lua_api.player.InMemoryPlayerMobAppearStore` per host, the same
    posture ``quest_store`` takes for its own default. Every other
    namespace is unchanged: a plain ``ApiNamespaceStub``.

    DEGRADED HOSTS (COO-DECISION ``20260907_1441``).  A construction reads
    EXACTLY ONE vendored mirror of ours, ``lua_api/api_spec.tsv``.  If it
    is broken this constructor no longer raises: it records the failure in
    ``mirror_health`` (readable without a log, which is the whole point of
    the decision), logs one ``LUA_MIRROR_DEGRADED`` line, and builds a host
    with ``degraded`` True and NO namespaces, which then refuses to
    ``load``/``call`` anything with :class:`MirrorUnavailable` rather than
    letting Lua blame the next quest file for our own broken file.  The
    sandbox is unaffected: ``BLOCKED_GLOBALS`` are nil on a degraded host
    exactly as on a healthy one.

    TWO SENTENCES THAT USED TO BE HERE AND WERE BOTH FALSE (pf-adversary
    D3, round ``h20x7g``).  "and the message catalog while
    ``Player``/``Trigger`` build" -- measured false: deleting
    ``message_catalog.tsv`` and calling either ``build_namespace`` builds
    fine and records nothing, because that mirror is read inside the call
    closures.  ``docs/SCRIPT_LANE.md`` says round ``95aw54`` corrected this
    claim "in all three places"; it corrected two, and this one was
    re-shipped.  And ``LUA_HOST_DEGRADED`` is a prefix NOTHING writes --
    :func:`guard_mirrors` says in capitals that it is deliberately
    ``LUA_MIRROR_DEGRADED``, because a second prefix starting ``LUA_HOST``
    is what turned the gate red at 1848 lines where 616 are pinned.  A
    reader who greps for the name this docstring used found nothing; a
    reader who trusted it would have re-introduced the gate-red shape.
    """

    def __init__(self, log: Optional[Callable[[str], None]] = None, *,
                 trigger_context: "Optional[lua_api_trigger.TriggerContext]" = None,
                 trigger_registry: "Optional[lua_api_trigger.TriggerStatusRegistry]" = None,
                 instance_context: "Optional[lua_api_instance.InstanceContext]" = None,
                 instance_registry: "Optional[lua_api_instance.InstanceRegistry]" = None,
                 quest_clock: "Optional[lua_api_quest.Clock]" = None,
                 quest_context: "Optional[lua_api_quest.QuestContext]" = None,
                 quest_store: "Optional[lua_api_quest.QuestStateStore]" = None,
                 player_context: "Optional[lua_api_player.PlayerContext]" = None,
                 player_store: "Optional[lua_api_player.PlayerMobAppearStore]" = None,
                 message_sink: "Optional[lua_api_message.MessageSink]" = None,
                 payout_store: Optional[Any] = None,
                 prelude: "Optional[lua_api_prelude.Prelude]" = None,
                 mirror_health: Optional[MirrorHealth] = None):
        _require_lupa()
        self.log = log or default_logger
        #: Where this host records a broken vendored mirror, readable
        #: without opening a log (COO-DECISION 20260907_1441).  Defaults to
        #: the process-wide :data:`MIRROR_HEALTH`; a test hands its own.
        self.mirror_health = MIRROR_HEALTH if mirror_health is None else mirror_health
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
        # One shared quest-state seam for THIS host's run, so a script whose
        # Trigger.QuestActiveProgress/QuestFinishProgress and Quest.* calls
        # both land in this same call stack see each other's writes -- built
        # once, here, rather than letting Trigger's and Quest's own
        # build_namespace calls each default to their OWN private store (see
        # the class docstring above and lua_api.trigger.build_namespace's own
        # docstring for why that used to be the gap).
        # Rebound in place (not into new local names) so the only new
        # symbols this constructor introduces are the two parameters
        # themselves -- both already earned in ALLOWED_SYMBOLS["script_
        # host.py"] together with the InMemoryQuestStateStore reference,
        # per the CORE-REQUEST cited above.
        quest_context = (
            quest_context if quest_context is not None else lua_api_quest.DEFAULT_CONTEXT)
        quest_store = (
            quest_store if quest_store is not None else lua_api_quest.InMemoryQuestStateStore())
        # ONE sink per host run, normalized here rather than left to each
        # build_namespace's own private default, so the Player and Trigger
        # message closures inside the SAME script land in one ordered
        # record -- the same reason quest_store is normalized above.
        # (Deliberately not spelling either Lua method name here:
        # tests/test_foundation_legacy_seam.py's own
        # test_no_foundation_module_emits_the_legacy_system_message is a
        # SUBSTRING scan of src/pirateforce_foundation/*.py for that name.
        # Its real subject is the frozen legacy BUILDER of the vital, which
        # nothing in this package touches; the proxy is simply broader than
        # the claim. That test is LANE-E's file, not this lane's, so this
        # lane worked around its own comment rather than loosening someone
        # else's guard -- reported to COO in round `6775u1`'s letter.)
        message_sink = (
            message_sink if message_sink is not None else lua_api_message.InMemoryMessageSink())
        def build_all() -> dict:
            # Built into a LOCAL dict and only installed as Lua globals
            # once every namespace is built.  NO MIRROR THAT EXISTS TODAY
            # CAN BREAK HALFWAY THROUGH THIS LOOP (pf-adversary D4, this
            # round, correcting an earlier claim here): the census is read
            # by the `for` header, before the first namespace is built, and
            # the other three mirrors are not read during a build at all.
            # The local dict is kept anyway, for the mirror read inside a
            # build_namespace that does not exist yet -- a half-built host
            # reads, to a script and to a log, as a working host with half
            # its API missing.  All or none.
            built: dict = {}
            for namespace, methods in lua_api_spec.NAMESPACE_METHODS.items():
                if namespace == "Trigger":
                    stub = lua_api_trigger.build_namespace(
                        methods, self.log,
                        context=trigger_context, registry=trigger_registry,
                        quest_context=quest_context, quest_store=quest_store,
                        sink=message_sink)
                elif namespace == "Instance":
                    stub = lua_api_instance.build_namespace(
                        methods, self.log,
                        context=instance_context, registry=instance_registry)
                elif namespace == "Quest":
                    stub = lua_api_quest.build_namespace(
                        methods, self.log, clock=quest_clock,
                        context=quest_context, store=quest_store,
                        payout_store=payout_store)
                elif namespace == "Player":
                    stub = lua_api_player.build_namespace(
                        methods, self.log, context=player_context, store=player_store,
                        sink=message_sink, payout_store=payout_store)
                else:
                    stub = ApiNamespaceStub(namespace, methods, self.log)
                built[namespace] = stub
            return built

        built, failure = guard_mirrors(build_all, self.log, self.mirror_health)
        #: THIS host's own failure, snapshotted at construction rather than
        #: read live off a shared counter (pf-adversary D7, this round): a
        #: host degraded by a missing census must not later describe itself
        #: with some other host's error.
        self.mirror_failure: Optional[MirrorFailureTally] = failure
        #: True when a vendored mirror of OURS was broken while this host
        #: was built.  The host still exists (fail-soft, COO-DECISION
        #: 20260907_1441) but carries no API namespaces, so it refuses to
        #: load or call a script rather than blaming one -- see
        #: :class:`MirrorUnavailable`.
        self.degraded: bool = built is None
        self.namespaces: dict = {} if built is None else built
        g = self.runtime.globals()
        for namespace, stub in self.namespaces.items():
            g[namespace] = stub
        # Set LAST and unconditionally: a degraded host is still a SANDBOX.
        # Nothing above this line may leave io/os/require/load/python
        # reachable, and a mirror failure is not an excuse to.
        for name in BLOCKED_GLOBALS:
            g[name] = None
        #: Whether THIS host ran the game's own startup prelude, and how it
        #: went: None = the caller handed none (every caller that existed
        #: before `lua_api/prelude.py` did), True = it ran, False = it
        #: raised and was logged.  Three states, not a bool, because "no
        #: prelude was asked for" and "the prelude failed" are different
        #: facts and a caller reading one as the other would blame the
        #: wrong thing.  Run AFTER the BLOCKED_GLOBALS loop above on
        #: purpose: `run_prelude` installs its one-key `os` shim on top of
        #: an already-sandboxed state and re-nils every blocked name in its
        #: own `finally`, so the invariant that loop establishes is the
        #: invariant a script's chunk still meets.  A degraded host runs no
        #: prelude: it carries no API namespaces and refuses load/call
        #: anyway, so running one would only add a log line about a host
        #: nobody can use.
        self.prelude_ok: Optional[bool] = None
        if prelude is not None and not self.degraded:
            self.prelude_ok = lua_api_prelude.run_prelude(
                self.runtime, prelude, self.log, BLOCKED_GLOBALS)

    def _refuse_if_degraded(self, what: str) -> None:
        """A degraded host says whose defect this is, before Lua can.

        The cause quoted is THIS host's own (``mirror_failure``), never the
        shared counter's latest, so the ``LUA_HOST`` line a sweep writes
        for this refusal names the file that actually broke it.
        """
        if self.degraded:
            cause = ("no failure recorded" if self.mirror_failure is None
                     else self.mirror_failure.last_error)
            raise MirrorUnavailable(
                "%s refused: this host was built with a broken vendored "
                "mirror and carries no API namespaces (%s)" % (what, cause))

    def load(self, source: str) -> None:
        """Compile and run a script's top-level chunk (its function defs)."""
        self._refuse_if_degraded("load")
        self.runtime.execute(source)

    def has_function(self, function_name: str) -> bool:
        # Guarded like load/call (pf-adversary D9, this round): unguarded,
        # a degraded host answers False and the caller that is coming --
        # a live dispatch doing has_function() then call() -- would file
        # OUR broken mirror as "this script defines no entry point".
        self._refuse_if_degraded("has_function")
        return self.runtime.globals()[function_name] is not None

    def call(self, function_name: str, *args):
        self._refuse_if_degraded("call")
        fn = self.runtime.globals()[function_name]
        if fn is None:
            raise LookupError("script defines no function named %r" % function_name)
        return fn(*args)


def load_script_file(path: Path, log: Optional[Callable[[str], None]] = None, *,
                      trigger_context: "Optional[lua_api_trigger.TriggerContext]" = None,
                      trigger_registry: "Optional[lua_api_trigger.TriggerStatusRegistry]" = None,
                      instance_context: "Optional[lua_api_instance.InstanceContext]" = None,
                      instance_registry: "Optional[lua_api_instance.InstanceRegistry]" = None,
                      quest_clock: "Optional[lua_api_quest.Clock]" = None,
                      quest_context: "Optional[lua_api_quest.QuestContext]" = None,
                      quest_store: "Optional[lua_api_quest.QuestStateStore]" = None,
                      player_context: "Optional[lua_api_player.PlayerContext]" = None,
                      player_store: "Optional[lua_api_player.PlayerMobAppearStore]" = None,
                      message_sink: "Optional[lua_api_message.MessageSink]" = None,
                      payout_store: Optional[Any] = None,
                      prelude: "Optional[lua_api_prelude.Prelude]" = None) -> ScriptHost:
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
                      trigger_registry=trigger_registry,
                      instance_context=instance_context,
                      instance_registry=instance_registry,
                      quest_clock=quest_clock,
                      quest_context=quest_context,
                      quest_store=quest_store,
                      player_context=player_context,
                      player_store=player_store,
                      message_sink=message_sink,
                      payout_store=payout_store,
                      prelude=prelude)
    source = Path(path).read_bytes().decode("latin-1")
    host.load(source)
    return host


def _host_side_error_types():
    """Exception types that mean THIS REPOSITORY is broken, not the script.

    pf-adversary D11 (round 7kxfe9): every sweep body caught bare
    ``Exception`` and logged ``LUA_SCRIPT <file> ERR ...``, so a
    a vendored-mirror error -- raised because one of OUR OWN vendored data
    files under ``lua_api/`` is missing or corrupt -- came out
    wearing the name of whichever quest file happened to be loading when
    the catalog was first touched, and then again for the next one, and
    the next: one host defect printed as up to 616 accusations against
    innocent scripts, with the real cause named nowhere.

    ONE BASE CLASS, NOT A LIST OF CLASSES (pf-adversary, round xlk7hl).
    The previous shape was a hand-maintained tuple with no test that it was
    complete, so the next vendored mirror to exist would have raised an
    unlisted error and been blamed on a script again.  Every loader in
    ``lua_api`` now raises a subclass of ``VendoredDataError``, so this
    classification cannot fall behind the files it classifies.
    """
    from .lua_api.vendored import VendoredDataError

    return (VendoredDataError,)


def _ascii_safe(exc: BaseException) -> str:
    """Console-safe text for any exception (AGENTS.md section 7: everything
    printed is ASCII -- the bridge console is cp874).

    ONE implementation, in ``lua_api/vendored.py``, because the counter
    that lives there escapes the same way and two copies of an escaping
    rule are two copies that can drift.  This name is kept because every
    caller in this module already uses it.
    """
    return ascii_safe(exc)


def _log_host_side(log: Callable[[str], None], rel: str,
                   exc: BaseException, entry: Optional[str] = None) -> str:
    """One ``LUA_HOST`` line, deliberately NOT ``LUA_SCRIPT``.

    Still fail-closed: this logs and returns, it never re-raises, because
    the charter's "one broken file must never take a boot down" holds for
    our own defects too.  What changes is only that the line names the
    defect and the file it was DISCOVERED in, instead of blaming the file.

    THE PATH IS QUOTED, AND ``entry`` IS A FIELD (pf-adversary D6, round
    ``oghyca``).  The corpus contains a file whose name has a space in it --
    ``t_test auto.lua``, measured, exactly one -- and the caller used to
    hand this function the string ``"<rel> entry=<name>"`` already joined.
    Together those produced ``discovered_at=t_test auto.lua
    entry=ScriptStart``: a reader splitting the line on whitespace got
    ``discovered_at=t_test`` and no way at all to recover where the path
    ended.  Quoting the path makes the boundary explicit, and ``entry``
    being a parameter rather than something smuggled inside ``rel`` means
    the two fields can never trade places.
    """
    message = _ascii_safe(exc)
    suffix = "" if entry is None else " entry=%s" % (entry,)
    log('LUA_HOST %s ERR %s discovered_at="%s"%s'
        % (type(exc).__name__, message, rel, suffix))
    return message


class _ShippedPrelude:
    """Sentinel default for the corpus sweeps' ``prelude=`` parameter.

    THREE STATES, NOT TWO, AND THAT IS THE WHOLE REASON THIS OBJECT EXISTS.
    Before round ``e5epdj`` the sweeps took ``prelude=None`` and ran no
    prelude, so "the caller wants yesterday's behaviour" and "the caller
    said nothing" were the same value and a default could not be flipped
    without taking the explicit opt-out away with it.  Now:

    * :data:`SHIPPED_PRELUDE` (the default) -- read ``utility.lua`` from
      the sweep's OWN ``root`` and run it.  A root that ships no such file,
      or ships different bytes, logs ``LUA_PRELUDE ABSENT``/``REFUSED`` and
      the sweep continues with no prelude: this is the supported shape for
      every fixture root in the test suite, which is why flipping the
      default did not have to touch one of them.
    * ``None`` -- explicitly no prelude.  Yesterday's behaviour, still
      reachable, still tested.
    * a :class:`~.lua_api.prelude.Prelude` -- use exactly that one.  What
      the census tests pass, because they need a FIXED seed (see
      ``tests/test_script_lua_corpus.py::CENSUS_PRELUDE_SEED``).

    Not a bare ``object()``: a reader who prints the default in a traceback
    or a help() should see a name that says what it means.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "SHIPPED_PRELUDE"


#: See :class:`_ShippedPrelude`.  The sweeps' default.
SHIPPED_PRELUDE = _ShippedPrelude()


def _resolve_prelude(root, prelude, log):
    """Turn a sweep's ``prelude=`` argument into a ``Prelude`` or ``None``.

    One function so the two sweeps cannot drift apart on the question, and
    so the ``read_prelude`` call happens ONCE per sweep rather than once
    per file -- 616 reads of the same 450 bytes would be waste, and 616
    DIFFERENT seeds would be a behaviour change nobody asked for (each host
    would get its own stream; see :class:`~.lua_api.prelude.Prelude` on why
    the seed's ownership is still an open question either way).
    """
    if prelude is SHIPPED_PRELUDE:
        return lua_api_prelude.read_prelude(root, log=log)
    return prelude


def load_corpus(root, log: Optional[Callable[[str], None]] = None, *,
                prelude: Any = SHIPPED_PRELUDE) -> LoadReport:
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
    prelude = _resolve_prelude(root, prelude, log)
    report = LoadReport()
    for path in sorted(root.rglob("*.lua")):
        report.total += 1
        rel = path.relative_to(root).as_posix()
        try:
            load_script_file(path, log=log, prelude=prelude)
        except _host_side_error_types() as exc:  # our defect, not the script's
            _log_host_side(log, rel, exc)
            report.host_failed.append(rel)
        except Exception as exc:  # noqa: BLE001 - fail-closed by design, see module docstring
            message = _ascii_safe(exc)
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
#: stubs.  Deliberately NOT repeated as per-namespace counts here: this
#: comment carried "2 of ``Player``'s 73" for four rounds after
#: ``REAL_METHODS`` had grown past it (pf-adversary, round `6775u1`).  The
#: live numbers are the ``REAL_METHODS`` sets themselves --
#: ``lua_api.trigger`` / ``lua_api.instance`` / ``lua_api.quest`` /
#: ``lua_api.player`` -- which is what the expression below composes, and
#: ``docs/SCRIPT_LANE.md``'s own status table is the one place a count is
#: written down and re-checked.
#: Every other namespace is a plain ``ApiNamespaceStub`` where 100% of
#: tracked calls are stubs, but ``RealTriggerNamespace``/
#: ``RealInstanceNamespace``/``RealQuestNamespace``/``RealPlayerNamespace``
#: append BOTH real and stub calls to the same ``.calls`` list
#: (``lua_api/trigger.py``, ``lua_api/instance.py``, ``lua_api/quest.py``,
#: ``lua_api/player.py``), so
#: :func:`run_corpus_entry_points` checks the qualified name against this
#: set, not against which Python object the call came from, to keep "real"
#: and "still stubbed" from being silently conflated in the corpus-wide
#: tally.
REAL_QUALIFIED_NAMES: frozenset = frozenset(
    ["Trigger.%s" % _name for _name in lua_api_trigger.REAL_METHODS]
    + ["Instance.%s" % _name for _name in lua_api_instance.REAL_METHODS]
    + ["Quest.%s" % _name for _name in lua_api_quest.REAL_METHODS]
    + ["Player.%s" % _name for _name in lua_api_player.REAL_METHODS]
)


@dataclass
class EntryPointRun:
    path: str
    called: list
    #: False if ANY called entry point failed, whether the defect was the
    #: script's (:attr:`errors`) or ours (:attr:`host_errors`).  One bool
    #: over three states -- clean / ours / the script's -- so it answers
    #: "did this run finish cleanly" and nothing else; WHOSE fault it was
    #: is a question for the two dicts, never for this flag.  A caller that
    #: reads ``ok`` alone and pins quest behaviour on it is reading a broken
    #: checkout of ours as a broken quest, which is the whole defect D12
    #: (round ``8ou0zg``) was raised about.  Pinned in both directions:
    #: ``test_a_run_that_only_WE_broke_still_reports_ok_False`` and
    #: ``test_the_two_kinds_of_failure_are_kept_in_separate_dicts``
    #: (``tests/test_script_lua_corpus.py``) -- before round ``5qtaqy``
    #: deleting ``run.ok = False`` from the host-side branch left 137 tests
    #: green (pf-adversary D4, round ``oghyca``).
    ok: bool = True
    #: entry-point name -> ascii-safe exception message, keyed structurally
    #: (not a concatenated string a caller would have to substring-match to
    #: recover which of possibly several called names actually failed).
    #:
    #: THE SCRIPT'S OWN FAILURES ONLY.  A failure raised by a defect in THIS
    #: repository goes in :attr:`host_errors` instead, never here, so a
    #: caller that pins "which quest entry points are known to fail" (see
    #: ``KNOWN_ENTRY_POINT_CALL_FAILURES`` in
    #: ``tests/test_script_lua_corpus.py``) cannot have our own broken
    #: vendored data quietly added to its pin as if a shipped script had a
    #: bug (pf-adversary D12, round 8ou0zg).
    errors: dict = field(default_factory=dict)
    #: entry-point name -> ascii-safe message, for failures classified as
    #: OURS by :func:`_host_side_error_types`.  Kept beside ``errors``
    #: rather than merged into it for the reason ``errors`` gives.
    host_errors: dict = field(default_factory=dict)


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
    :data:`REAL_QUALIFIED_NAMES` (the union of ``lua_api_trigger.REAL_METHODS``,
    ``lua_api_instance.REAL_METHODS`` and ``lua_api_quest.REAL_METHODS`` --
    round 4jsydv wrote this split against the first one only, round 4fxvsq
    added Instance's 7 real names and round 0rgg6q (recovering the round
    after 4jsydv) added Quest's 1, each into the same set rather than
    duplicating the split logic again)
    and tallies it as real, never stub, regardless of which Python object's
    ``.calls`` list it came from -- so the day another namespace grows a mix
    of real and stub methods, this split keeps working without changes here.
    """
    total: int = 0
    load_failed: list = field(default_factory=list)
    #: Same meaning as :attr:`LoadReport.host_failed` -- paths where a defect
    #: in THIS repository surfaced, kept out of ``load_failed``/``call_failed``
    #: so a sweep never reports our own broken data as broken quests.
    #:
    #: ONE ENTRY PER FILE, NOT PER ENTRY POINT (pf-adversary D12, round
    #: 8ou0zg).  A file defines up to len(STANDARD_ENTRY_POINTS) == 8 of
    #: them, and a broken vendored mirror fails EVERY one it reaches: the
    #: first shape of this loop appended the same path once per failing
    #: entry point, so three affected files could be reported as up to 24
    #: "host failures" -- a count nobody could reconcile against a corpus
    #: of files.  The number in this list is now a file count, which is
    #: what its name says and what ``LoadReport.host_failed`` (one load
    #: per file, so never able to double-count) always meant.
    host_failed: list = field(default_factory=list)
    no_entry_point: list = field(default_factory=list)
    ran: list = field(default_factory=list)
    #: Runs where THE SCRIPT failed.  A run whose only failures were ours
    #: is in :attr:`host_failed_runs` instead; a run with both is in both.
    #:
    #: BUCKETS OVERLAP, SO THEY DO NOT SUM (pf-adversary D3, round
    #: ``oghyca``).  Round ``oghyca``'s comment said the overlap applies to
    #: RUNS and left the file lists reading as a partition; they are not
    #: one.  A file with both kinds of failure is counted in ``call_failed``
    #: AND ``host_failed``, so on that round's own three-file fixture the
    #: file-level buckets summed to 4 against a ``total`` of 3.  The
    #: equation that does hold, and is pinned on the real corpus and on a
    #: deliberately overlapping fixture by
    #: ``test_every_file_lands_in_exactly_one_bucket_or_a_named_overlap``::
    #:
    #:     total == len(load_failed) + len(no_entry_point) + len(ran)
    #:              + len(set(run.path for run in call_failed)
    #:                    | set(host_failed))
    call_failed: list = field(default_factory=list)
    #: Runs carrying at least one host-side (our defect) entry-point
    #: failure, so the detail is not lost by keeping those runs out of
    #: ``call_failed``.  Same runs whose paths appear in ``host_failed``,
    #: except for load-time host failures, which never produce a run.
    host_failed_runs: list = field(default_factory=list)
    total_stub_calls: int = 0
    stub_call_counts: dict = field(default_factory=dict)
    total_real_calls: int = 0
    real_call_counts: dict = field(default_factory=dict)


def run_corpus_entry_points(root, log: Optional[Callable[[str], None]] = None, *,
                             quest_clock: "Optional[lua_api_quest.Clock]" = None,
                             prelude: Any = SHIPPED_PRELUDE) -> CorpusEntryPointReport:
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

    NOT FAIL-CLOSED AGAINST A LUA PANIC EITHER, MEASURED (pf-adversary D5,
    round ``oghyca``).  Second shape of the same structural gap, worse than
    the hang because it is not even a Python-level event.  A script whose
    TOP LEVEL installs a metamethod that raises -- ``setmetatable(_G,
    {__index = function(t, k) error(...) end})`` -- loads fine (the chunk is
    legal), and then the very next thing this function does,
    ``host.has_function("ScriptStart")``, reaches that metamethod from
    inside the Lua C API where there is no protected call: ``PANIC:
    unprotected error in call to Lua API``, ``SIGABRT``, exit 134.  Neither
    ``except Exception`` nor ``except BaseException`` sees anything; the
    process is gone, this function never returns, and the other 615 files
    are never touched.  No trigger exists in the shipped corpus today
    (``grep -rli setmetatable gamedata/lua`` = 0 files, re-checked round
    ``5qtaqy``), so this is a structural gap with no live trigger, written
    down rather than discovered later.  The fix is the same shape as the
    hang's and is not attempted here: the panic must be caught below this
    layer (a subprocess per file, or ``lupa``'s own panic hook if a later
    version exposes one), because by the time Python could look, there is
    no interpreter left to look with.

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
    prelude = _resolve_prelude(root, prelude, log)
    report = CorpusEntryPointReport()
    for path in sorted(root.rglob("*.lua")):
        report.total += 1
        rel = path.relative_to(root).as_posix()
        try:
            host = load_script_file(path, log=log, quest_clock=quest_clock,
                                    prelude=prelude)
        except _host_side_error_types() as exc:  # our defect, not the script's
            _log_host_side(log, rel, exc)
            report.host_failed.append(rel)
            continue
        except Exception as exc:  # noqa: BLE001 - fail-closed, see load_corpus
            message = _ascii_safe(exc)
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
                except _host_side_error_types() as exc:  # our defect
                    # An entry point that TOUCHES the broken catalog is the
                    # commonest way this surfaces: the corpus reaches the
                    # message-showing API long before it reaches anything
                    # else that reads a vendored file.  (The API's own name
                    # is deliberately NOT spelled here -- LANE-E's guard
                    # `test_no_foundation_module_emits_the_legacy_system_message`
                    # is a substring scan over src/ that does not skip
                    # comments, and round 02mkqc turned it red by writing
                    # the name in this very comment.  Same class of defect
                    # as round 7kxfe9's docstring vs. the n/327 census.)
                    message = _log_host_side(log, rel, exc, entry=name)
                    run.ok = False
                    run.host_errors[name] = message
                except Exception as exc:  # noqa: BLE001 - fail-closed, one script must not sink the corpus
                    message = _ascii_safe(exc)
                    log("LUA_SCRIPT %s ERR entry=%s %s" % (rel, name, message))
                    run.ok = False
                    run.errors[name] = message
            # Bucket the FILE once, by what kind of failure it had.  Both
            # kinds at once puts it in both buckets; neither leaves it in
            # ``ran``.  See CorpusEntryPointReport.host_failed for why this
            # is per file rather than per entry point.
            if run.host_errors:
                report.host_failed.append(rel)
                report.host_failed_runs.append(run)
            if run.errors:
                report.call_failed.append(run)
            elif not run.host_errors:
                report.ran.append(run)

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
