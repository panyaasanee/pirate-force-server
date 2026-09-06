"""LANE-Q's ``Instance`` namespace: all 9 names, real.

WHAT THIS FILE MAKES REAL, AND WHY THESE SEVEN.  ``docs/SCRIPT_LANE.md``
(round ``s2fxf6``) shipped all 9 ``Instance.*`` names as stubs that log and
return 0.  Grepping the corpus (``gamedata/lua/t_*.lua``, done before writing
a line of this module -- every call site of every one of the 9 names, no
guessing) shows the 9 names split the same way ``Trigger.*`` did:

  * a PURE STATE MACHINE -- ``GetInstanceID``/``GetInstanceId`` (read which
    instance this script belongs to), ``GetLastingTime``/``SetLastingTime``
    (read/write a per-instance countdown), ``AddKeyEvent``/``RemoveKeyEvent``
    (add/remove an id from a per-instance set) and ``CallScoreCount`` (fire a
    per-instance score-tally event) -- no outbound frame, no Quest state.
    52 of 55 call sites (94.5%, re-derived against this file's own
    ``REAL_METHODS``/``api_spec.tsv`` after pf-adversary caught the first
    draft's arithmetic error, which had said 53/55/96%).  Nothing blocks
    these from being real.
  * two names whose ARGUMENT semantics are genuinely ambiguous from the
    corpus alone -- ``AddBonusPoint``/``AddBonusReward``.  A REWARD TABLE
    DOES EXIST: ``gamedata/tables/CONSTDATA_TH__INSTANCE.tsv``'s
    ``n_SCORECOUNT_ID`` column keys into
    ``gamedata/tables/CONSTDATA_TH__SCORECOUNT.tsv``'s
    ``n_COLLECT_BONUS_SCORE``/``n_RANKC_REWARD``..``n_RANKSSS_REWARD``
    columns.  TRACED, round 92j6so (2026-09-06), clean negative: no
    committed table or scene placement file names
    ``t_insbospnt_himdfx.lua``/``t_insbosev_himdfx.lua``/
    ``t_drp&insbospnt_himdfx.lua`` anywhere (grepped every
    ``gamedata/tables/*.tsv`` and all 289 ``gamedata/scene/*.placements.tsv``
    files), and the scene extractor (``gamedata/pf_extract_gamedata.py``)
    has no code path that reads a trigger-to-script binding at all -- it
    only decodes mob-placement records.  So the join key needed to pick
    WHICH ``CONSTDATA_TH__INSTANCE`` row(s) these three scripts run under
    does not exist in any committed artifact; the ``n_SCORECOUNT_ID``
    column mechanically resolves fine for the instance rows that carry a
    nonzero value (73 of 338 rows checked directly), but that fact cannot
    be connected to these three scripts without either a new binary parser
    over the raw ``.npc`` scene files (not proven to be in this clone) or
    an RE ticket against the live client -- a closed dead end for static
    tracing, not "unfinished work" any more.  Round 92j6so's own written
    recommendation named two forward paths for whoever has charter
    priority next: (a) a scoped RE ticket, or (b) accept the negative
    result and implement both names as pure invocation counters, the same
    "advances an int, no invented game rule" shape ``CallScoreCount``
    already uses, without claiming any SCORECOUNT wiring.  THIS round
    picks (b): both names below count CALLS, nothing else -- they do not
    look up ``CONSTDATA_TH__SCORECOUNT.tsv``, do not compute a point value
    from ``AddBonusPoint``'s optional argument, and do not hand out any
    item or score.  The day the trace above is unblocked (new parser, or
    an RE ticket answer), this counter is what a real implementation
    replaces, not what it already is.

So this round makes all nine names real; the two counters just described
keep the exact "no game rule invented" posture the seven before them
already had.

WHAT "REAL" MEANS HERE, PRECISELY.  An :class:`InstanceRegistry` -- process
memory, keyed by instance id, gone on reboot -- the same shape
``lua_api.trigger.TriggerStatusRegistry`` uses for trigger status, for the
same reason (``PANYA-DECISION 20260905_1057``: world/instance state is
server-process memory, not per-session, not the DB).  This lane does not
claim ownership of instance ENTRY/lifecycle (spawning an instance, routing a
party into one) -- only of "the script running inside one reading/writing
its own scratch state", exactly the same ownership line the charter draws
for ``Trigger.*`` vs. LANE-A's island entry.

WHAT IS **NOT** DONE THIS ROUND, SAID PLAINLY.  Nothing wires a live
dispatch that tells this registry which instance id a running script
belongs to -- an :class:`InstanceContext` is supplied by the CALLER (a test,
or a future dispatch module) exactly like ``lua_api.trigger.TriggerContext``
is today. No player sees any change on screen from this file, this round.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

#: Mirrors ``script_host.STUB_DEFAULT`` without importing that module (which
#: imports THIS package, via ``lua_api/__init__.py`` -> would be circular).
#: Kept equal to it by a cross-module test (``tests/test_script_lua_api_instance.py``),
#: not by trust.
STUB_DEFAULT = 0

#: Same posture as ``lua_api.trigger``'s caps: a refused-by-name ceiling, not
#: a silent eviction, so a caller in a loop cannot grow this book past the
#: box's memory. No roster this project has mined comes close to either
#: number.
INSTANCES_CAP = 4096
KEY_EVENTS_PER_INSTANCE_CAP = 256

REFUSE_BAD_INSTANCE_ID = "bad_instance_id"
REFUSE_BAD_EVENT_ID = "bad_event_id"
REFUSE_BAD_TIME = "bad_time"
REFUSE_TOO_MANY_INSTANCES = "too_many_instances"
REFUSE_TOO_MANY_KEY_EVENTS = "too_many_key_events"

#: A lasting-time/instance-id/event-id is whatever a script's own Var table
#: says it is -- no script in the corpus was found writing anything but a
#: plain small non-negative int (grepped: no ``SetLastingTime(-``/
#: ``AddKeyEvent(-`` in ``gamedata/lua/**/*.lua``), so this range is a
#: sanity door, not a guessed game rule.
_MAX_INSTANCE_ID = 0xFFFFFFFF
_MAX_EVENT_ID = 0xFFFFFFFF
_MAX_TIME = 0xFFFFFFFF


def _coerce_int(value: Any, ceiling: int) -> Optional[int]:
    """Lua hands numbers back as floats; an int door that never raises.

    Same shape as ``lua_api.trigger._coerce_int`` (kept as a private copy,
    not a shared import, so each namespace's door stays free to diverge the
    day their ranges do): ``None`` means "not a usable number", the
    caller's job is to refuse the whole read/write rather than guess.
    Booleans are rejected explicitly -- ``True`` is an ``int`` in Python and
    would otherwise silently become instance/event id 1.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        as_int = int(value)
        if float(as_int) != value:
            return None
        value = as_int
    if not isinstance(value, int):
        return None
    if value < 0 or value > ceiling:
        return None
    return value


@dataclass(frozen=True)
class InstanceContext:
    """Which running instance is asking these questions.

    No call site of any of the 7 real names below passes an instance id
    (grepped: zero call sites do) -- the game's own engine always knows
    which instance is running the script that called them. This server has
    no such call stack yet, so the caller (today: a test; later: whatever
    dispatches a real script to a real running instance) supplies the
    answer up front instead, the same shape as
    ``lua_api.trigger.TriggerContext``.
    """

    instance_id: int


#: The context a :class:`RealInstanceNamespace` gets when nothing more
#: specific is supplied -- a well-defined, inert value, NOT the production
#: singleton. Safe as a shared default because :func:`build_namespace`
#: without an explicit registry also gets its OWN fresh, private registry
#: (see :class:`InstanceRegistry` below), so two unrelated tests that both
#: take the default id never see each other's writes.
DEFAULT_CONTEXT = InstanceContext(instance_id=0)


class InstanceRegistry:
    """Per-instance scratch state: lasting time, key events, score-count
    calls. Process memory, gone on reboot (``PANYA-DECISION 20260905_1057``).

    Every method a live script call can reach returns an answer instead of
    raising -- bad input, or a full book, changes nothing and returns
    whatever the matching getter would already answer, the same posture
    ``lua_api.trigger.TriggerStatusRegistry`` takes and for the same reason:
    every existing stub in this codebase already collapses every failure
    into one safe default.  CORRECTION (pf-adversary caught this round's
    first draft claiming "no script in the corpus checks a richer return
    value from any of these 7 names" -- false): 7 scripts DO branch on
    ``GetLastingTime()`` (``t_opnplc_tim.lua``: ``local T =
    Instance.GetLastingTime(); if (T > Trigger.Var2) then return 0 else
    ... end``, and 6 more of the same shape) and several more branch on
    ``GetInstanceID()`` (``t_bg2017_msg.lua``: ``if (Instance.GetInstanceID()
    == 1005) then``).  What stays true, re-checked: every ``SetLastingTime``
    call site in the real corpus passes a plain literal ``Trigger.VarN``
    (grepped, arity 1 always), so the refusal path (a NaN/negative/
    fractional/over-cap write silently reading back as "never written",
    indistinguishable from 0) has no live trigger in today's corpus -- but
    it is a real, load-bearing distinction a future or corrupted script
    COULD hit, since scripts do read this value back and act on it, not a
    theoretical worry a wrong docstring dismissed as impossible. The
    CONSTRUCTOR is not on the script-reachable path and does raise
    ``ValueError`` on a non-positive cap, on purpose, the same as
    ``TriggerStatusRegistry.__init__`` -- a caller-programming-error door,
    not a script-reachable one.
    """

    def __init__(self, instances: int = INSTANCES_CAP,
                 key_events_per_instance: int = KEY_EVENTS_PER_INSTANCE_CAP) -> None:
        if type(instances) is bool or not isinstance(instances, int) or instances < 1:
            raise ValueError("instances must be a positive int")
        if (type(key_events_per_instance) is bool
                or not isinstance(key_events_per_instance, int)
                or key_events_per_instance < 1):
            raise ValueError("key_events_per_instance must be a positive int")
        self._instances_cap = instances
        self._key_events_cap = key_events_per_instance
        self._lock = threading.RLock()
        self._lasting_time: dict[int, int] = {}
        self._key_events: dict[int, set] = {}
        self._score_count_calls: dict[int, int] = {}
        self._bonus_point_calls: dict[int, int] = {}
        self._bonus_reward_calls: dict[int, int] = {}

    def get_lasting_time(self, instance_id: Any) -> int:
        iid = _coerce_int(instance_id, _MAX_INSTANCE_ID)
        if iid is None:
            return STUB_DEFAULT
        with self._lock:
            return self._lasting_time.get(iid, STUB_DEFAULT)

    def set_lasting_time(self, instance_id: Any, value: Any) -> int:
        iid = _coerce_int(instance_id, _MAX_INSTANCE_ID)
        val = _coerce_int(value, _MAX_TIME)
        if iid is None or val is None:
            return self.get_lasting_time(instance_id)
        with self._lock:
            if iid not in self._lasting_time and len(self._lasting_time) >= self._instances_cap:
                return STUB_DEFAULT
            self._lasting_time[iid] = val
            return val

    def add_key_event(self, instance_id: Any, event_id: Any) -> int:
        """Adds ``event_id`` to the instance's set; returns the set's size
        after the call (a plain int, since nothing in the corpus reads the
        set itself -- see the class docstring)."""
        iid = _coerce_int(instance_id, _MAX_INSTANCE_ID)
        eid = _coerce_int(event_id, _MAX_EVENT_ID)
        if iid is None or eid is None:
            return self._key_event_count(instance_id)
        with self._lock:
            events = self._key_events.get(iid)
            if events is None:
                if len(self._key_events) >= self._instances_cap:
                    return STUB_DEFAULT
                events = self._key_events.setdefault(iid, set())
            if eid not in events and len(events) >= self._key_events_cap:
                return len(events)
            events.add(eid)
            return len(events)

    def remove_key_event(self, instance_id: Any, event_id: Any) -> int:
        iid = _coerce_int(instance_id, _MAX_INSTANCE_ID)
        eid = _coerce_int(event_id, _MAX_EVENT_ID)
        if iid is None or eid is None:
            return self._key_event_count(instance_id)
        with self._lock:
            events = self._key_events.get(iid)
            if events is None:
                return STUB_DEFAULT
            events.discard(eid)
            return len(events)

    def call_score_count(self, instance_id: Any) -> int:
        """Records one score-count call; returns the running tally.

        This does NOT compute or know what "score" means for any dungeon.
        CORRECTION (pf-adversary caught this round's first draft claiming
        "no reward/score table has been found committed anywhere" -- false):
        ``gamedata/tables/CONSTDATA_TH__SCORECOUNT.tsv`` exists (columns
        include ``n_COLLECT_BONUS_SCORE`` and rank-tiered
        ``n_RANKC_REWARD``..``n_RANKSSS_REWARD``), and
        ``CONSTDATA_TH__INSTANCE.tsv``'s own ``n_SCORECOUNT_ID`` column keys
        into it.  What is still NOT done -- tracing that link for any of the
        instances that actually run a ``CallScoreCount``-calling script, and
        deciding whether "calling this API" should look up and apply that
        row's reward, or whether the row only matters for
        ``AddBonusPoint``/``AddBonusReward`` (which stay named stubs, see
        ``STILL_STUBBED``) -- is real, unstarted work, not a guess this
        function silently avoids.  What IS unambiguous from every one of the
        12 ``CallScoreCount`` call sites themselves is that the call happens
        per instance, a bare statement with no argument and no read of its
        own return value -- so THIS function counts the INVOCATIONS, the
        same "advance an int, gone on reboot" shape ``TriggerStatusRegistry.
        next_status`` uses, and does not itself look up or apply the
        SCORECOUNT table -- that is next round's work, not silently
        invented here.
        """
        iid = _coerce_int(instance_id, _MAX_INSTANCE_ID)
        if iid is None:
            return STUB_DEFAULT
        with self._lock:
            if iid not in self._score_count_calls and len(self._score_count_calls) >= self._instances_cap:
                return STUB_DEFAULT
            new_value = self._score_count_calls.get(iid, 0) + 1
            self._score_count_calls[iid] = new_value
            return new_value

    def add_bonus_point(self, instance_id: Any, point_arg: Any = None) -> int:
        """Records one ``AddBonusPoint`` call; returns the running tally.

        Same shape and same non-claim as :meth:`call_score_count`: this does
        NOT interpret ``point_arg`` (the corpus calls this with 0 args in
        ``t_drp&insbospnt_himdfx.lua`` and with ``Trigger.Var1`` in
        ``t_insbospnt_himdfx.lua`` -- STILL genuinely ambiguous whether that
        argument is a point value or a bonus-category id, per
        ``STILL_STUBBED``'s history above), does NOT look up
        ``CONSTDATA_TH__SCORECOUNT.tsv``, and does NOT compute or award any
        actual bonus. It counts INVOCATIONS only, gone on reboot, exactly
        the "advance an int" shape ``call_score_count`` already uses.
        ``point_arg`` is accepted and discarded so a 1-argument call site
        does not need special-casing above this method.
        """
        iid = _coerce_int(instance_id, _MAX_INSTANCE_ID)
        if iid is None:
            return STUB_DEFAULT
        with self._lock:
            if iid not in self._bonus_point_calls and len(self._bonus_point_calls) >= self._instances_cap:
                return STUB_DEFAULT
            new_value = self._bonus_point_calls.get(iid, 0) + 1
            self._bonus_point_calls[iid] = new_value
            return new_value

    def add_bonus_reward(self, instance_id: Any) -> int:
        """Records one ``AddBonusReward`` call; returns the running tally.

        Same non-claim as :meth:`add_bonus_point`: does not hand out any
        item or score (the corpus's one call site,
        ``t_insbosev_himdfx.lua``, takes zero arguments -- there is nothing
        here to interpret even if this method wanted to). Counts
        INVOCATIONS only.
        """
        iid = _coerce_int(instance_id, _MAX_INSTANCE_ID)
        if iid is None:
            return STUB_DEFAULT
        with self._lock:
            if iid not in self._bonus_reward_calls and len(self._bonus_reward_calls) >= self._instances_cap:
                return STUB_DEFAULT
            new_value = self._bonus_reward_calls.get(iid, 0) + 1
            self._bonus_reward_calls[iid] = new_value
            return new_value

    def _key_event_count(self, instance_id: Any) -> int:
        iid = _coerce_int(instance_id, _MAX_INSTANCE_ID)
        if iid is None:
            return STUB_DEFAULT
        with self._lock:
            return len(self._key_events.get(iid, ()))


_REGISTRY: Optional[InstanceRegistry] = None
_REGISTRY_LOCK = threading.RLock()


def instance_registry() -> InstanceRegistry:
    """The process's own instance-scratch book. Built on first use.

    NOT used by default: :func:`build_namespace` without an explicit
    registry gets its own PRIVATE instance so ordinary tests and spikes
    never share state with the production singleton or with each other. A
    future live-dispatch module is the intended caller of this accessor.
    """
    global _REGISTRY
    with _REGISTRY_LOCK:
        if _REGISTRY is None:
            _REGISTRY = InstanceRegistry()
        return _REGISTRY


def install_instance_registry(registry: Any) -> InstanceRegistry:
    """Put a registry in the process slot. A TEST SEAM, named as one."""
    global _REGISTRY
    if not isinstance(registry, InstanceRegistry):
        raise ValueError("only an InstanceRegistry can be installed")
    with _REGISTRY_LOCK:
        _REGISTRY = registry
        return _REGISTRY


#: All nine names, now real. ``GetInstanceId`` is the game's own shipped
#: alternate-case spelling of ``GetInstanceID`` (one call site,
#: ``t_indanix2_colct_ins.lua``) -- aliased to the exact same real handler,
#: the same treatment round ``456vso`` gave ``Trigger.GetTeiggerStatus``.
#: ``AddBonusPoint``/``AddBonusReward`` (this round, path (b) of round
#: ``92j6so``'s recommendation) are pure invocation counters -- see
#: :meth:`InstanceRegistry.add_bonus_point`/``add_bonus_reward`` for the
#: explicit non-claim; no SCORECOUNT semantics are implemented.
REAL_METHODS = frozenset({
    "GetInstanceID", "GetInstanceId", "GetLastingTime", "SetLastingTime",
    "AddKeyEvent", "RemoveKeyEvent", "CallScoreCount",
    "AddBonusPoint", "AddBonusReward",
})

#: Empty -- all 9 ``Instance.*`` names are real as of this round. Kept as a
#: named, typed constant (not deleted) so ``tests/test_script_lua_api_instance.py``'s
#: own cross-check against ``REAL_METHODS``/``api_spec.tsv`` keeps working
#: unchanged, and so the next namespace to reach 100% has a precedent for
#: how to record it rather than silently dropping the dict.
STILL_STUBBED: dict[str, str] = {}


def _log_real(log: Callable[[str], None], api_name: str, context: "InstanceContext",
               detail: str) -> None:
    log("LUA_INSTANCE_REAL Instance.%s instance=%d %s"
        % (api_name, context.instance_id, detail))


def _log_bad_arity(log: Callable[[str], None], api_name: str, got: int, want: str) -> None:
    log("LUA_INSTANCE_BAD_ARITY Instance.%s got=%d want=%s" % (api_name, got, want))


class RealInstanceNamespace:
    """Drop-in replacement for ``script_host.ApiNamespaceStub`` on ``Instance``.

    Same three-way ``__getitem__`` contract the stub has (real API name ->
    callable; other API name -> stub callable that logs and returns
    :data:`STUB_DEFAULT`; anything else, e.g. ``Var1`` -> bare
    :data:`STUB_DEFAULT`, silently), the same shape
    ``lua_api.trigger.RealTriggerNamespace`` uses.
    """

    __slots__ = ("_context", "_registry", "_log", "_stub_methods", "namespace", "calls")

    def __init__(self, methods: frozenset, context: InstanceContext,
                 registry: InstanceRegistry, log: Callable[[str], None]):
        self.namespace = "Instance"
        self._context = context
        self._registry = registry
        self._log = log
        self._stub_methods = methods - REAL_METHODS
        self.calls: list = []

    def __getitem__(self, name):
        if name == "GetInstanceID" or name == "GetInstanceId":
            api_name = name

            def get_instance_id(*args, _api=api_name):
                self.calls.append("Instance.%s" % _api)
                if len(args) != 0:
                    _log_bad_arity(self._log, _api, len(args), "0")
                    return STUB_DEFAULT
                _log_real(self._log, _api, self._context, "id=%d" % self._context.instance_id)
                return self._context.instance_id

            return get_instance_id

        if name == "GetLastingTime":
            def get_lasting_time(*args):
                self.calls.append("Instance.GetLastingTime")
                if len(args) != 0:
                    _log_bad_arity(self._log, "GetLastingTime", len(args), "0")
                    return STUB_DEFAULT
                value = self._registry.get_lasting_time(self._context.instance_id)
                _log_real(self._log, "GetLastingTime", self._context, "time=%d" % value)
                return value

            return get_lasting_time

        if name == "SetLastingTime":
            def set_lasting_time(*args):
                self.calls.append("Instance.SetLastingTime")
                if len(args) != 1:
                    _log_bad_arity(self._log, "SetLastingTime", len(args), "1")
                    return STUB_DEFAULT
                value = self._registry.set_lasting_time(self._context.instance_id, args[0])
                _log_real(self._log, "SetLastingTime", self._context, "time=%d" % value)
                return value

            return set_lasting_time

        if name == "AddKeyEvent":
            def add_key_event(*args):
                self.calls.append("Instance.AddKeyEvent")
                if len(args) != 1:
                    _log_bad_arity(self._log, "AddKeyEvent", len(args), "1")
                    return STUB_DEFAULT
                count = self._registry.add_key_event(self._context.instance_id, args[0])
                _log_real(self._log, "AddKeyEvent", self._context, "count=%d" % count)
                return count

            return add_key_event

        if name == "RemoveKeyEvent":
            def remove_key_event(*args):
                self.calls.append("Instance.RemoveKeyEvent")
                if len(args) != 1:
                    _log_bad_arity(self._log, "RemoveKeyEvent", len(args), "1")
                    return STUB_DEFAULT
                count = self._registry.remove_key_event(self._context.instance_id, args[0])
                _log_real(self._log, "RemoveKeyEvent", self._context, "count=%d" % count)
                return count

            return remove_key_event

        if name == "CallScoreCount":
            def call_score_count(*args):
                self.calls.append("Instance.CallScoreCount")
                if len(args) != 0:
                    _log_bad_arity(self._log, "CallScoreCount", len(args), "0")
                    return STUB_DEFAULT
                calls = self._registry.call_score_count(self._context.instance_id)
                _log_real(self._log, "CallScoreCount", self._context, "calls=%d" % calls)
                return calls

            return call_score_count

        if name == "AddBonusPoint":
            def add_bonus_point(*args):
                self.calls.append("Instance.AddBonusPoint")
                if len(args) not in (0, 1):
                    _log_bad_arity(self._log, "AddBonusPoint", len(args), "0..1")
                    return STUB_DEFAULT
                point_arg = args[0] if args else None
                calls = self._registry.add_bonus_point(self._context.instance_id, point_arg)
                _log_real(self._log, "AddBonusPoint", self._context, "calls=%d" % calls)
                return calls

            return add_bonus_point

        if name == "AddBonusReward":
            def add_bonus_reward(*args):
                self.calls.append("Instance.AddBonusReward")
                if len(args) != 0:
                    _log_bad_arity(self._log, "AddBonusReward", len(args), "0")
                    return STUB_DEFAULT
                calls = self._registry.add_bonus_reward(self._context.instance_id)
                _log_real(self._log, "AddBonusReward", self._context, "calls=%d" % calls)
                return calls

            return add_bonus_reward

        if name in self._stub_methods:
            qualified = "Instance.%s" % name

            def stub(*_args, _qualified=qualified):
                self.calls.append(_qualified)
                self._log("LUA_API_STUB %s" % _qualified)
                return STUB_DEFAULT

            return stub

        return STUB_DEFAULT

    def __setitem__(self, name, value):
        # Same posture as ApiNamespaceStub/RealTriggerNamespace: no script in
        # the corpus assigns into a namespace table at runtime; accept and
        # discard.
        return None


def build_namespace(methods: frozenset, log: Callable[[str], None], *,
                     context: Optional[InstanceContext] = None,
                     registry: Optional[InstanceRegistry] = None) -> RealInstanceNamespace:
    """The ``Instance`` global ``ScriptHost`` installs, real half included.

    ``context``/``registry`` default to :data:`DEFAULT_CONTEXT` and a FRESH
    private :class:`InstanceRegistry` -- not the process singleton -- so a
    caller that does not ask for the live world (every test today) can never
    collide with another caller's state. The production dispatch path (not
    built this round) is the one expected to pass both explicitly.
    """
    return RealInstanceNamespace(
        methods,
        context if context is not None else DEFAULT_CONTEXT,
        registry if registry is not None else InstanceRegistry(),
        log,
    )
