"""LANE-Q's ``Trigger`` namespace: the status-machine half of the 17 names.

WHAT THIS FILE MAKES REAL, AND WHY THESE FIVE FIRST, PLUS TWO MORE THIS
ROUND.  ``docs/SCRIPT_LANE.md`` (round ``s2fxf6``) shipped all 17
``Trigger.*`` names as stubs that log and return 0.  Reading the corpus
(``gamedata/lua/t_*.lua``, grepped before writing a line of this module --
see the per-name notes below) shows the 17 names split cleanly in two:

  * a STATUS STATE MACHINE -- ``GetTriggerStatus``/``GetTeiggerStatus``
    (read another trigger's status), ``SetStatus``/``NextStatus`` (write the
    CURRENT trigger's own status), ``SetTriggerStatus`` (write ANOTHER
    trigger's status) -- pure bookkeeping a script reads and writes with no
    outbound frame involved.  542 of 828 call sites (65%), including the two
    highest-volume names in the whole namespace (``NextStatus`` 353,
    ``GetTriggerStatus`` 134).  Nothing blocks these from being real: no
    client frame, no Quest state, no skill/animation encoder.
  * everything a script fires that must reach the CLIENT or the QUEST
    system -- ``CastSkill``/``CastSkillBy``/``CastSkillXYZ``, ``PlayFx``,
    ``StartAnimation``/``StartTriggerAnimation``, ``HideModel``/
    ``HideTriggerModel``, ``TriggerShowMessage``, ``GetContactMode``,
    ``QuestActiveProgress``/``QuestFinishProgress``.  Each is blocked on a
    seam this lane does not own yet (see ``STILL_STUBBED`` below, one
    sentence per name, no guessing) and stays a logged stub.

So round ``456vso`` made the first five real; the other twelve kept the
exact ``ApiNamespaceStub`` contract (log ``LUA_API_STUB``, return
:data:`script_host.STUB_DEFAULT`) they had before this file existed.

TWO MORE, THIS ROUND (COO-DECISION ``20260906_1846``, "flag-quest-state").
``QuestActiveProgress``/``QuestFinishProgress`` (8 + 3 = 11 call sites) are
the ONLY two ``Trigger.*`` names that read/write ``Quest.*`` per-character
state rather than a wire frame -- and, grepped before writing a line of
this addition, an exact behavioural pair: ``t_opnq_t1.lua``'s
``ScriptStart`` calls ``Trigger.QuestActiveProgress(Trigger.Var1)`` only
after confirming ``Quest.GetQuestFlag(Trigger.Var1) == 0`` (i.e. ``Quest.
None``, see ``lua_api.quest``'s own module docstring); ``t_clsq.lua``'s
``ScriptStart`` -- the paired CLOSING half of the same open/close family --
calls ``Trigger.QuestFinishProgress(Trigger.Var1)`` only after confirming
that SAME flag now reads ``1`` (``Quest.Active``). The two names are
therefore exactly ``Quest.SetQuestFlag(quest_id, Quest.Active)`` /
``Quest.SetQuestFlag(quest_id, Quest.Finish)`` under a `Trigger.*`-shaped
name, sharing the identical :class:`lua_api.quest.QuestStateStore` door
``lua_api.quest``'s own nine newly-real names use -- not a second, competing
implementation of quest-flag state. See :func:`build_namespace` below for
how a caller shares one store instance between both namespaces (proven in
this round's own tests) -- NOT yet wired that way inside
``script_host.ScriptHost`` itself, see :func:`build_namespace`'s own
docstring for why and what is asked to fix it.

WRONG-ARITY CALLS DO NOT CRASH THE HOST, MEASURED (pf-adversary, this
round).  A first draft gave the five real closures fixed positional
parameters (``def set_status(status): ...``), which is exactly right for
every call site the 616-file corpus actually has (grepped: ``SetStatus``
is always called with 1 argument, ``NextStatus`` with 0, and so on) but
silently dropped the invariant every OTHER name in this file still keeps
-- ``script_host.py``'s own module docstring: "a script that calls any of
[the 160 names] gets a safe, logged, non-crashing answer instead of ... an
error."  ``Trigger.SetStatus()`` (0 args) or ``Trigger.NextStatus(1)`` (1
arg) raised a raw Python ``TypeError`` straight out of ``ScriptHost.call``
-- dormant only because no shipped script happens to call these five names
at the wrong arity today, and a live landmine for the day one does (a
corrupted file, a future quest-editor-authored script, or simply the next
namespace copying this file's shape).  Every real closure below now takes
``*args`` and checks its own expected count FIRST, logging
``LUA_TRIGGER_BAD_ARITY`` and returning :data:`STUB_DEFAULT` instead of
letting Python raise -- the same fail-closed shape ``STILL_STUBBED``'s
stub callables already had for free by using ``*args`` throughout.

WHAT "REAL" MEANS HERE, PRECISELY.  A :class:`TriggerStatusRegistry` --
process memory, one int per (scene, trigger id), shared by every session in
that scene, gone on reboot -- the same shape ``world_scene_registry`` uses
for monster vitals, for the same reason (``PANYA-DECISION 20260905_1057``:
world state is server-process memory, not per-session, not the DB).  This is
a SEPARATE book from LANE-A's, not a second front door to it: trigger status
is not a monster vital or a scene roster, and the charter draws the line
explicitly -- LANE-A owns island ENTRY, LANE-Q owns the trigger SCRIPT
deciding what happens (prompts/LANE-Q.md's own words, translated: "A owns
entering the island; LANE-Q owns the trigger script that decides what
happens").  No interface from LANE-A is needed to own this.

WHAT IS **NOT** DONE THIS ROUND, SAID PLAINLY.  Nothing wires a live
``TriggerVital`` (0x1FB2) arrival to a specific script file yet -- that
needs the trigger-id -> script-file mapping the charter names
(``gamedata/scene/*.placements.tsv`` / a trigger table) and this round did
not go mine it, to keep this diff to the state machine itself.  So today, a
:class:`TriggerContext` is supplied by the CALLER (a test, or a future
dispatch module); nothing here reads a real inbound frame.  A player sailing
into a trigger sees NO change on screen from this file, this round -- see
``docs/SCRIPT_LANE.md`` nonclaims.  ``lane_hooks.lane_a_island_trigger_log``
(LANE-A's own module) is still the only subscriber to
``vital_inbound_trigger_vital`` and still prints ``no_responder
bytes_out=0``; this file changes nothing about that frame or that hook.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .. import mob_loot as _mob_loot  # scene_key: the one scene-fold used project-wide
from . import quest as _quest  # QuestStateStore door: QuestActiveProgress/QuestFinishProgress
                                # share it with lua_api.quest's own nine real names

#: Mirrors ``script_host.STUB_DEFAULT`` without importing that module (which
#: imports THIS package, via ``lua_api/__init__.py`` -> would be circular).
#: Kept equal to it by a cross-module test
#: (``tests/test_script_lua_api_trigger.py``), not by trust.
STUB_DEFAULT = 0

#: A trigger status registry is bounded the same way
#: ``world_scene_registry.WorldSceneRegistry`` is: a per-scene cap and a
#: total-scenes cap, both refused-by-name rather than silently evicted, so a
#: caller in a loop cannot grow this book past the box's memory.  The
#: numbers are the same ones LANE-A picked for the same reason (no roster
#: this project has mined comes close).
TRIGGERS_PER_SCENE_CAP = 4096
SCENES_CAP = 128

REFUSE_BAD_SCENE = "bad_scene"
REFUSE_BAD_TRIGGER_ID = "bad_trigger_id"
REFUSE_BAD_STATUS = "bad_status"
REFUSE_SCENE_IS_FULL = "scene_is_full"
REFUSE_TOO_MANY_SCENES = "too_many_scenes"

#: A status is whatever a script's own Var table says it is (``Trigger.Var7``
#: in ``t_nex_t6.lua`` is a plain small int).  No script in the corpus was
#: found writing anything but a small non-negative int (grepped: no
#: ``SetStatus(-`` in ``gamedata/lua/**/*.lua``), so this range is a sanity
#: door, not a guessed game rule -- wide enough for every literal seen, tight
#: enough to refuse a NaN/inf/huge float arriving from Lua by mistake.
_MAX_STATUS = 0xFFFF
_MAX_TRIGGER_ID = 0xFFFFFFFF

#: quest_id ceiling for QuestActiveProgress/QuestFinishProgress -- same
#: value as ``lua_api.quest._MAX_QUEST_ID`` (u16, LANE-DB's own measured
#: evidence cited there), duplicated rather than imported across the
#: leading-underscore boundary, the convention every ``lua_api`` module in
#: this package already follows for its small validation constants.
_MAX_QUEST_ID = 0xFFFF


def _scene_key(scene: Any) -> str:
    return _mob_loot.scene_key(scene)


def _coerce_int(value: Any, ceiling: int) -> Optional[int]:
    """Lua hands numbers back as floats; an int door that never raises.

    ``None`` means "not a usable number" -- the caller's job is to refuse
    the whole write/read rather than guess, exactly like every other
    ``_require_*`` door in this codebase (``world_scene_registry``,
    ``mob_loot``).  Booleans are rejected explicitly: ``True`` is an
    ``int`` in Python and would otherwise silently become trigger id 1.
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
class TriggerContext:
    """Which physical trigger is running the script asking these questions.

    ``NextStatus()``/``SetStatus(n)`` take no trigger id in the script's own
    source (grepped: zero call sites pass one) -- the game's own engine
    always knows which trigger invoked the script it is running.  This
    server has no such call stack yet, so the caller (today: a test; later:
    whatever dispatches a real inbound trigger hit to its script) supplies
    the answer up front instead.
    """

    scene: str
    trigger_id: int


#: The context a :class:`RealTriggerNamespace` gets when nothing more
#: specific is supplied (``ScriptHost`` outside of a real dispatch, e.g.
#: every existing corpus/spike test).  A well-defined, inert bucket -- NOT
#: the production singleton -- so two unrelated tests that both take the
#: default never see each other's writes (see :class:`TriggerStatusRegistry`
#: below: the default namespace also gets its OWN fresh registry, not the
#: process one).
#:
#: NOT the empty string.  MEASURED, not assumed (a first draft used ``""``
#: and every read/write under it silently no-opped): ``mob_loot._require_
#: scene`` -- the same door ``TriggerStatusRegistry`` goes through for every
#: scene key -- refuses an empty string by name
#: (``REFUSE_SCENE_NOT_A_SCENE``), so ``get_status``/``set_status`` on scene
#: ``""`` fail the scene check every time and fall back to
#: :data:`STUB_DEFAULT` -- ``SetStatus``/``NextStatus`` would look like they
#: ran (no exception, a logged line) while never actually writing anything.
DEFAULT_CONTEXT = TriggerContext(scene="unscoped_default", trigger_id=0)


class TriggerStatusRegistry:
    """One int per (scene, trigger id).  Process memory.

    Same shape as ``world_scene_registry.WorldSceneRegistry`` for the same
    reason: shared by every session in a scene, gone on reboot
    (``PANYA-DECISION 20260905_1057``).  Every method a live script call
    can reach -- :meth:`get_status`, :meth:`set_status`,
    :meth:`next_status` -- returns an answer instead of raising (fuzzed,
    pf-adversary: None/list/dict/huge ints/nan/-0.0/bytes/complex, at every
    argument position, never raises).  The CONSTRUCTOR is not on that path
    (nothing in this file, and no test, ever builds a
    ``TriggerStatusRegistry`` from data a script controls) and does raise
    ``ValueError`` on a non-positive cap, on purpose, the same as
    ``WorldSceneRegistry.__init__`` -- a caller-programming-error door, not
    a script-reachable one.  An earlier draft of this docstring said "never
    raises" without that distinction (pf-adversary, this round).
    """

    def __init__(self, triggers_per_scene: int = TRIGGERS_PER_SCENE_CAP,
                 scenes: int = SCENES_CAP) -> None:
        if (type(triggers_per_scene) is bool
                or not isinstance(triggers_per_scene, int)
                or triggers_per_scene < 1):
            raise ValueError("triggers_per_scene must be a positive int")
        if type(scenes) is bool or not isinstance(scenes, int) or scenes < 1:
            raise ValueError("scenes must be a positive int")
        self._cap = triggers_per_scene
        self._scenes_cap = scenes
        self._lock = threading.RLock()
        self._scenes: dict[str, dict[int, int]] = {}

    def get_status(self, scene: Any, trigger_id: Any) -> int:
        """The remembered status, or ``STUB_DEFAULT`` for anything unknown
        or unusable -- a trigger nothing has ever written to is
        indistinguishable from bad input, on purpose: a script's very first
        ``GetTriggerStatus`` on a trigger this process has never seen is the
        ORDINARY case, not an error."""
        fold = self._try_scene(scene)
        tid = _coerce_int(trigger_id, _MAX_TRIGGER_ID)
        if fold is None or tid is None:
            return STUB_DEFAULT
        with self._lock:
            return self._scenes.get(fold, {}).get(tid, STUB_DEFAULT)

    def set_status(self, scene: Any, trigger_id: Any, status: Any) -> int:
        """Write one trigger's status; returns the value now on record.

        Bad input, or a full book, changes nothing and returns whatever
        :meth:`get_status` would already answer -- the caller cannot tell
        "refused" from "already was 0" from the return value alone, which is
        deliberate: every existing stub in this codebase already collapses
        every failure into the one safe default, and a script has no way to
        branch on a richer answer than that (the source calls these as bare
        statements, return value discarded, in the one namespace method that
        even provides a call-site to check: none does).
        """
        fold = self._try_scene(scene)
        tid = _coerce_int(trigger_id, _MAX_TRIGGER_ID)
        value = _coerce_int(status, _MAX_STATUS)
        if fold is None or tid is None or value is None:
            return self.get_status(scene, trigger_id)
        with self._lock:
            rows = self._scenes.get(fold)
            if rows is None:
                if len(self._scenes) >= self._scenes_cap:
                    return STUB_DEFAULT
                rows = self._scenes.setdefault(fold, {})
            if tid not in rows and len(rows) >= self._cap:
                return rows.get(tid, STUB_DEFAULT)
            rows[tid] = value
            return value

    def next_status(self, scene: Any, trigger_id: Any) -> int:
        """Advance one trigger's status by exactly 1; returns the new value.

        Read-modify-write under the SAME lock acquisition as the write, so
        two sessions calling ``NextStatus`` on the same trigger in the same
        dispatch tick cannot both read the old value and both write the same
        "new" one (``RLock`` makes the nested ``get_status``/``set_status``
        calls below atomic with respect to any other caller of this
        instance, because both take the same lock).
        """
        with self._lock:
            current = self.get_status(scene, trigger_id)
            return self.set_status(scene, trigger_id, current + 1)

    def _try_scene(self, scene: Any) -> Optional[str]:
        try:
            return _scene_key(scene)
        except Exception:                                    # noqa: BLE001
            return None


_REGISTRY: Optional[TriggerStatusRegistry] = None
_REGISTRY_LOCK = threading.RLock()


def trigger_status_registry() -> TriggerStatusRegistry:
    """The process's own trigger-status book.  Built on first use.

    NOT used by default: :func:`build_namespace` without an explicit
    registry gets its own PRIVATE instance (see its docstring) so that
    ordinary tests and spikes never share state with the production
    singleton or with each other.  A future live-dispatch module is the
    intended caller of this accessor.
    """
    global _REGISTRY
    with _REGISTRY_LOCK:
        if _REGISTRY is None:
            _REGISTRY = TriggerStatusRegistry()
        return _REGISTRY


def install_trigger_status_registry(registry: Any) -> TriggerStatusRegistry:
    """Put a registry in the process slot.  A TEST SEAM, named as one."""
    global _REGISTRY
    if not isinstance(registry, TriggerStatusRegistry):
        raise ValueError("only a TriggerStatusRegistry can be installed")
    with _REGISTRY_LOCK:
        _REGISTRY = registry
        return _REGISTRY


#: The five names this round makes real.  ``GetTeiggerStatus`` is the
#: game's own shipped misspelling of ``GetTriggerStatus`` (one call site,
#: ``gamedata/lua/t_getm_t1.lua``) -- aliased to the exact same real
#: handler rather than treated as dead code, because the game engine this
#: server is re-implementing plainly resolved it to something (the script
#: shipped and the corpus census counted a real call site), and the
#: conservative reading is "the original engine tolerated the typo", not
#: "the original engine silently ignored it".  Decision left open by round
#: ``s2fxf6`` on purpose (its own round file: "whoever implements Trigger.*
#: next round decides"); this is that decision.
REAL_METHODS = frozenset({
    "GetTriggerStatus", "GetTeiggerStatus", "SetStatus", "NextStatus",
    "SetTriggerStatus", "QuestActiveProgress", "QuestFinishProgress",
})

#: The remaining ten, one honest sentence each for why they are NOT real
#: this round -- no guessing, per charter.  Every reason names the missing
#: seam, not "not done yet".
STILL_STUBBED: dict[str, str] = {
    "GetContactMode": (
        "semantics unclear from the one call site in the corpus "
        "(t_popmo_ui1.lua: `Trigger.GetContactMode(22) == 1`) -- needs an "
        "RE ticket on what a 'contact mode' enum means before this becomes "
        "real logic instead of a guess"
    ),
    "CastSkill": "needs a skill-cast wire frame encoder this lane does not own (LANE-CS territory)",
    "CastSkillBy": "needs a skill-cast wire frame encoder this lane does not own (LANE-CS territory)",
    "CastSkillXYZ": "needs a skill-cast wire frame encoder this lane does not own (LANE-CS territory)",
    "PlayFx": "needs an effect-play wire frame this server has no encoder for yet",
    "StartAnimation": "needs an animation wire frame this server has no encoder for yet",
    "StartTriggerAnimation": "needs an animation wire frame this server has no encoder for yet",
    "HideModel": "needs a hide-model wire frame (LANE-A's Scene.PlacementOFF territory)",
    "HideTriggerModel": "needs a hide-model wire frame (LANE-A's Scene.PlacementOFF territory)",
    "TriggerShowMessage": "needs a client message/UI wire frame this lane does not own",
}


def _log_get(log: Callable[[str], None], api_name: str, context: TriggerContext,
             trigger_id: int, status: int) -> None:
    log("LUA_TRIGGER_REAL Trigger.%s scene=%r trigger=%d status=%d"
        % (api_name, context.scene, trigger_id, status))


def _log_write(log: Callable[[str], None], api_name: str, context: TriggerContext,
                trigger_id: int, old: int, new: int) -> None:
    log("LUA_TRIGGER_REAL Trigger.%s scene=%r trigger=%d from=%d to=%d"
        % (api_name, context.scene, trigger_id, old, new))


def _log_bad_arity(log: Callable[[str], None], api_name: str, got: int, want: str) -> None:
    log("LUA_TRIGGER_BAD_ARITY Trigger.%s got=%d want=%s" % (api_name, got, want))


class RealTriggerNamespace:
    """Drop-in replacement for ``script_host.ApiNamespaceStub`` on ``Trigger``.

    Same three-way ``__getitem__`` contract the stub has (real API name ->
    callable; other API name -> stub callable that logs and returns
    :data:`STUB_DEFAULT`; anything else, e.g. ``Var1``/``Active`` -> bare
    :data:`STUB_DEFAULT`, silently) so ``ScriptHost`` can hand a script this
    object instead of the generic stub without the script being able to
    tell the difference except by the answers it gets back.
    """

    __slots__ = ("_context", "_registry", "_log", "_stub_methods", "namespace", "calls",
                 "_quest_context", "_quest_store")

    def __init__(self, methods: frozenset, context: TriggerContext,
                 registry: TriggerStatusRegistry, log: Callable[[str], None],
                 quest_context: "Optional[_quest.QuestContext]" = None,
                 quest_store: "Optional[_quest.QuestStateStore]" = None):
        self.namespace = "Trigger"
        self._context = context
        self._registry = registry
        self._log = log
        self._stub_methods = methods - REAL_METHODS
        self.calls: list = []
        self._quest_context = (
            quest_context if quest_context is not None else _quest.DEFAULT_CONTEXT)
        self._quest_store = (
            quest_store if quest_store is not None else _quest.InMemoryQuestStateStore())

    def __getitem__(self, name):
        if name == "GetTriggerStatus" or name == "GetTeiggerStatus":
            api_name = name

            def get_status(*args, _api=api_name):
                self.calls.append("Trigger.%s" % _api)
                if len(args) != 1:
                    _log_bad_arity(self._log, _api, len(args), "1")
                    return STUB_DEFAULT
                tid = _coerce_int(args[0], _MAX_TRIGGER_ID)
                status = self._registry.get_status(self._context.scene,
                                                     tid if tid is not None else -1)
                _log_get(self._log, _api, self._context,
                         tid if tid is not None else -1, status)
                return status

            return get_status

        if name == "SetStatus":
            def set_status(*args):
                self.calls.append("Trigger.SetStatus")
                if len(args) != 1:
                    _log_bad_arity(self._log, "SetStatus", len(args), "1")
                    return STUB_DEFAULT
                before = self._registry.get_status(
                    self._context.scene, self._context.trigger_id)
                after = self._registry.set_status(
                    self._context.scene, self._context.trigger_id, args[0])
                _log_write(self._log, "SetStatus", self._context,
                           self._context.trigger_id, before, after)
                return after

            return set_status

        if name == "NextStatus":
            def next_status(*args):
                self.calls.append("Trigger.NextStatus")
                if len(args) != 0:
                    _log_bad_arity(self._log, "NextStatus", len(args), "0")
                    return STUB_DEFAULT
                before = self._registry.get_status(
                    self._context.scene, self._context.trigger_id)
                after = self._registry.next_status(
                    self._context.scene, self._context.trigger_id)
                _log_write(self._log, "NextStatus", self._context,
                           self._context.trigger_id, before, after)
                return after

            return next_status

        if name == "SetTriggerStatus":
            def set_trigger_status(*args):
                self.calls.append("Trigger.SetTriggerStatus")
                if len(args) != 2:
                    _log_bad_arity(self._log, "SetTriggerStatus", len(args), "2")
                    return STUB_DEFAULT
                tid = _coerce_int(args[0], _MAX_TRIGGER_ID)
                target = tid if tid is not None else -1
                before = self._registry.get_status(self._context.scene, target)
                after = self._registry.set_status(
                    self._context.scene, target, args[1])
                _log_write(self._log, "SetTriggerStatus", self._context,
                           target, before, after)
                return after

            return set_trigger_status

        if name == "QuestActiveProgress" or name == "QuestFinishProgress":
            api_name = name
            new_flag = _quest.QUEST_ACTIVE if name == "QuestActiveProgress" else _quest.QUEST_FINISH

            def set_quest_progress(*args, _api=api_name, _flag=new_flag):
                self.calls.append("Trigger.%s" % _api)
                if len(args) != 1:
                    _log_bad_arity(self._log, _api, len(args), "1")
                    return STUB_DEFAULT
                quest_id = _coerce_int(args[0], _MAX_QUEST_ID)
                if quest_id is None:
                    self._log("LUA_TRIGGER_BAD_VALUE Trigger.%s quest_id=%r" % (_api, args[0]))
                    return STUB_DEFAULT
                after = self._quest_store.set_quest_flag(
                    self._quest_context.character_id, quest_id, _flag)
                self._log("LUA_TRIGGER_REAL Trigger.%s character=%d quest=%d flag=%d"
                           % (_api, self._quest_context.character_id, quest_id, after))
                return after

            return set_quest_progress

        if name in self._stub_methods:
            qualified = "Trigger.%s" % name

            def stub(*_args, _qualified=qualified):
                self.calls.append(_qualified)
                self._log("LUA_API_STUB %s" % _qualified)
                return STUB_DEFAULT

            return stub

        return STUB_DEFAULT

    def __setitem__(self, name, value):
        # Same posture as ApiNamespaceStub: no script in the corpus assigns
        # into a namespace table at runtime (verified there, not re-verified
        # here since this IS that namespace); accept and discard.
        return None


def build_namespace(methods: frozenset, log: Callable[[str], None], *,
                     context: Optional[TriggerContext] = None,
                     registry: Optional[TriggerStatusRegistry] = None,
                     quest_context: "Optional[_quest.QuestContext]" = None,
                     quest_store: "Optional[_quest.QuestStateStore]" = None,
                     ) -> RealTriggerNamespace:
    """The ``Trigger`` global ``ScriptHost`` installs, real half included.

    ``context``/``registry`` default to :data:`DEFAULT_CONTEXT` and a FRESH
    private :class:`TriggerStatusRegistry` -- not the process singleton --
    so a caller that does not ask for the live world (every test today) can
    never collide with another caller's state.  The production dispatch
    path (not built this round -- see module docstring) is the one expected
    to pass both explicitly. ``quest_context``/``quest_store`` are the same
    kind of seam for ``QuestActiveProgress``/``QuestFinishProgress`` (this
    round's addition): default to ``lua_api.quest.DEFAULT_CONTEXT`` and a
    fresh private ``InMemoryQuestStateStore`` when not given. A caller that
    wants ``Trigger.QuestActiveProgress`` and ``Quest.SetFlag`` in the SAME
    script run to see each other's writes MUST pass the identical
    ``quest_store`` instance to both this function and
    ``lua_api.quest.build_namespace``.

    NOT WIRED IN ``script_host.ScriptHost`` THIS ROUND, SAID PLAINLY.  A
    first draft threaded ``quest_context``/``quest_store`` through
    ``ScriptHost.__init__``/``load_script_file`` too, sharing one store
    between the ``Trigger`` and ``Quest`` namespace builders the way this
    docstring describes -- reverted before push because it trips
    ``tests/test_npc_interaction_wire.py``'s foundation quest/shop guard
    (three new symbols in ``script_host.py`` -- ``quest_context``,
    ``quest_store``, and the normalized ``InMemoryQuestStateStore``
    reference -- none in that test's ``ALLOWED_SYMBOLS``), and that
    exemption is chief's to grant after reading the names, not this lane's
    to add itself (the guard's own rule, and the same posture the EARLIER
    ``lua_api_quest``/``quest``/``quest_clock`` exemption already went
    through, per ``pf_bridge/notes_to_chief/consumed/
    20260906_0510_CHIEF-GRANT-...``). Asked for again this round:
    ``pf_bridge/notes_to_chief/20260906_1951_LANE-Q-CORE-REQUEST-quest-store-wiring-trips-foundation-guard.md``.
    Until it lands, a live ``ScriptHost`` running BOTH namespaces still
    gets ``QuestActiveProgress``/``QuestFinishProgress`` and ``Quest.*``
    each fully working on their OWN independent private store -- only the
    CROSS-namespace consistency (one script's ``Trigger.QuestActiveProgress``
    call visible to that SAME script's later ``Quest.GetQuestFlag`` call)
    is the gap, and no script in the corpus is known to need it in one call
    (the two are always in different files, `t_opnq_t1.lua`/`t_clsq.lua`
    run as separate `ScriptHost` instances today regardless).
    """
    return RealTriggerNamespace(
        methods,
        context if context is not None else DEFAULT_CONTEXT,
        registry if registry is not None else TriggerStatusRegistry(),
        log,
        quest_context=quest_context,
        quest_store=quest_store,
    )
