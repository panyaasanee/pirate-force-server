"""LANE-Q's ``Player`` namespace: the first two of 73 names to go real,
``GetLv`` and ``GetClass``.

WHY THESE TWO, WHY TOGETHER.  ``docs/SCRIPT_LANE.md`` (round `bxly5p`) found
both of LANE-Q's own charter blockers still closed at this round's own
start: `Trigger.*`'s remaining 12 names need `RE-273`'s wire-id/`.tgr`-
ordinal crosswalk (still `OPEN`, needs an attended capture from the
bridge's own machine); `Quest.*`'s remaining 24 names need the LANE-DB
per-character quest-state column (`COO-DECISION 20260905_2058`, still not
landed on `main` -- `grep -rln "persistence_quest_state\\|character_quest_
state" src/` is zero hits this round, same as every round since `4jsydv`
found it). `AGENTS.md` SS7's own backup-work order for a blocked round is
"implement the next stub-table name that needs no other lane and no DB,
highest call count first" -- so this round read every one of `Player`'s 73
names (call counts from `api_spec.tsv`, grepped, not guessed) looking for
one with that shape.

``GetLv`` (91 calls, 89 files, arity 0) and ``GetClass`` (60 calls, 14
files, arity 0) are the only two: every call site in the corpus invokes
them with zero arguments (`api_spec.tsv`'s own `arity_min`/`arity_max`
columns are both 0 for each), which only makes sense if the answer is
"the level/class of THE PLAYER RUNNING THIS SCRIPT" -- a value the calling
convention supplies implicitly, not one the script passes in. And
`model.Character` (this repository's own row-backed player record, not a
LANE-Q invention) already carries exactly that pair, `level: int | None`
and `class_id: int | None`, filled in by `session.py` from the login-vitals
seam (`COO-DECISION 20260903_0647` for level/HP, `COO-DECISION
20260904_0446` point 3 for class) -- the same object `world_m2_arrival.
level_refusal()` already reads a character's level off of, elsewhere in
this codebase. No new state, no new column, no other lane's write zone
touched: this file only reads a per-invocation context a future dispatcher
fills from that existing `Character`, the same shape
`lua_api.trigger.TriggerContext`/`lua_api.instance.InstanceContext` already
established for their own namespaces.

WHY EVERY OTHER PLAYER.* NAME STAYS A STUB THIS ROUND, GROUPED, NOT
GUESSED.  See `STILL_STUBBED` below -- 71 names, one of eight named
category reasons each (item/equipment state, a stat-grant write seam,
other per-character stat reads this lane's context does not carry yet,
skill/buff state cross-lane with combat, a teleport/vehicle/camera wire
frame, a UI/cutscene/message wire frame, the instance-entry frame, and
`MobAppear` itself, which LANE-A's own letter names explicitly as not
servable: `pf_bridge/notes_to_chief/20260906_0727_LANE-A-TO-LANE-Q-world-
registry-interface-and-trigger-hit-hook-point.md`, section (c).1, "there is
no function name that means add one monster to an already-populated scene
and tell the client -- Player.MobAppear cannot be serviced yet").

WHAT "REAL" MEANS HERE, PRECISELY, AND WHAT IT DOES NOT MEAN.  Same posture
as `lua_api.trigger.RealTriggerNamespace`/`lua_api.quest.RealQuestNamespace`:
a script that calls `Player.GetLv()`/`Player.GetClass()` through a live
`ScriptHost` gets back a real integer from an injectable `PlayerContext`
instead of the logged `LUA_API_STUB` default, backed by a test. This round
does NOT wire a live session's actual `Character.level`/`Character.class_id`
into that context at real dispatch time -- there is no live Lua-script
dispatch point yet at all (the nearest thing, `lane_hooks/
lane_q_trigger_vital_dispatch.py`, only ever touches the `Trigger`
namespace's registry, never loads or runs a `.lua` file) -- so
`DEFAULT_CONTEXT` below reads the same fixed constants every fresh login
composes today (`player_wire.PLAYER_LOGIN_LEVEL`, `player_wire.
PLAYER_LOGIN_CLASS_ID`), openly labelled as such. The day a real dispatcher
exists, it supplies its own `PlayerContext` built from the actual session's
`Character`, the same way a future real `Trigger`/`Instance` dispatch would
supply its own `TriggerContext`/`InstanceContext` instead of each
namespace's own inert default.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .. import player_wire

#: Mirrors ``script_host.STUB_DEFAULT`` without importing that module
#: (``script_host`` imports THIS package, via ``lua_api/__init__.py`` ->
#: importing it back here would be circular) -- same posture
#: ``lua_api/trigger.py`` and ``lua_api/quest.py`` already take, kept equal
#: to it by the same cross-module test those two are checked by
#: (``tests/test_script_lua_api_player.py``).
STUB_DEFAULT = 0

#: The two names this round makes real. See the module docstring for why
#: these two, and why every other Player.* name is not real yet.
REAL_METHODS = frozenset({"GetLv", "GetClass"})


@dataclass(frozen=True)
class PlayerContext:
    """What "the player running this script" means to ``GetLv``/``GetClass``.

    Both fields default to the exact constants every fresh login composes
    today (``player_wire.PLAYER_LOGIN_LEVEL`` == 1, ``player_wire.
    PLAYER_LOGIN_CLASS_ID`` == 1) -- not a guess, the same values
    ``model.Character``'s own two fields (``level``, ``class_id``, both
    ``int | None``) fall back to when a login does not override them. A
    real per-session dispatcher (not built this round) supplies its own
    ``PlayerContext`` built from that ``Character`` instead of relying on
    this default, the same seam ``lua_api.trigger.TriggerContext``/
    ``lua_api.instance.InstanceContext`` already established for their own
    namespaces.
    """

    level: int = player_wire.PLAYER_LOGIN_LEVEL
    class_id: int = player_wire.PLAYER_LOGIN_CLASS_ID


#: The context a :class:`RealPlayerNamespace` gets when nothing more
#: specific is supplied (``ScriptHost`` outside of a real dispatch, e.g.
#: every existing corpus/spike test) -- a well-defined, inert default, not
#: a production singleton, mirroring ``lua_api.trigger.DEFAULT_CONTEXT``.
DEFAULT_CONTEXT = PlayerContext()

#: The remaining 71 names, one of eight grouped, grep-grounded reasons each
#: -- no per-name guess, the same posture ``lua_api.quest.STILL_STUBBED``
#: takes for its own DB-blocked names. Category text is shared verbatim
#: across every name in that category (the same repetition
#: ``lua_api.quest.STILL_STUBBED`` already uses for its own LANE-DB-blocked
#: entries), not independently reworded per name.
_ITEM_STATE = (
    "needs per-character inventory/equipment state; a LANE-DB column this "
    "lane does not own (Player.* item/exp/money queue item, not built yet)"
)
_STAT_GRANT = (
    "needs a per-character stat WRITE/grant seam this lane does not own "
    "yet (Player.* item/exp/money queue item, not built yet)"
)
_STAT_READ = (
    "needs per-character state this lane's PlayerContext does not carry "
    "yet (level/class_id are the only two PlayerContext exposes this "
    "round; widening it to more Character fields is a CORE-REQUEST-shaped "
    "follow-up, not a guess)"
)
_SKILL_BUFF = (
    "needs the skill/buff state and cast wire frame, cross-lane with "
    "LANE-B/CS's combat state, not owned by Q"
)
_TELEPORT_VEHICLE = (
    "needs a world-movement/vehicle wire frame this lane does not own, "
    "cross-lane with LANE-A's world registry"
)
_UI_MOVIE_MESSAGE = (
    "needs an outbound UI/cutscene/message wire frame this lane does not "
    "own"
)
_INSTANCE_ENTRY = (
    "needs the world-entry frame that actually moves a session into an "
    "instance, cross-lane with LANE-A's M2 island-entry flow -- this "
    "lane's own Instance.* registry (lua_api/instance.py) only tracks "
    "state AFTER entry, never the entry frame itself"
)
_MOB_APPEAR = (
    "LANE-A's own letter (pf_bridge/notes_to_chief/"
    "20260906_0727_LANE-A-TO-LANE-Q-world-registry-interface-and-trigger-"
    "hit-hook-point.md, section (c).1) states explicitly there is no "
    "function yet that adds one monster to an already-populated scene and "
    "tells the client -- not nameable by this lane, not a guess"
)

STILL_STUBBED: dict[str, str] = {
    # item/equipment state (13)
    "AddAndEquip": _ITEM_STATE,
    "AddItem": _ITEM_STATE,
    "RemoveItem": _ITEM_STATE,
    "CheckItemNum": _ITEM_STATE,
    "GetItemNum": _ITEM_STATE,
    "CheckEquipItem": _ITEM_STATE,
    "ItemAddon": _ITEM_STATE,
    "OpenStorage": _ITEM_STATE,
    "AppraiseItem": _ITEM_STATE,
    "AppraiseCollectPiece": _ITEM_STATE,
    "CheckCollect": _ITEM_STATE,
    "CheckAllCollectItemSynthesisBuff": _ITEM_STATE,
    "DropProcess": _ITEM_STATE,
    # stat-grant writes (8)
    "AddCash": _STAT_GRANT,
    "AddHP": _STAT_GRANT,
    "AddST": _STAT_GRANT,
    "AddExp": _STAT_GRANT,
    "AddSkillPoint": _STAT_GRANT,
    "AddPpClass": _STAT_GRANT,
    "GiveLvCriteriaPercentageEXP": _STAT_GRANT,
    "Addmoralized": _STAT_GRANT,
    # other per-character stat reads (15)
    "GetCash": _STAT_READ,
    "GetCurrentHP": _STAT_READ,
    "GetMaxHP": _STAT_READ,
    "GetCurrentST": _STAT_READ,
    "GetMaxST": _STAT_READ,
    "GetPpClass": _STAT_READ,
    "CheckMoralized": _STAT_READ,
    "CheckGender": _STAT_READ,
    "CheckGuild": _STAT_READ,
    "GetGuildRank": _STAT_READ,
    "CheckParty": _STAT_READ,
    "CheckPartyLeader": _STAT_READ,
    "CheckSoulmate": _STAT_READ,
    "CheckThrowAnyPenpalLetter": _STAT_READ,
    "CheckAchievement": _STAT_READ,
    # skill/buff (6)
    "CastSkillAt": _SKILL_BUFF,
    "CastSkillXYZ": _SKILL_BUFF,
    "AddBuff": _SKILL_BUFF,
    "RemoveBuff": _SKILL_BUFF,
    "CheckSkill": _SKILL_BUFF,
    "CheckBuff": _SKILL_BUFF,
    # teleport/vehicle/camera (14)
    "BoatHealth": _TELEPORT_VEHICLE,
    "GetBoatHealth": _TELEPORT_VEHICLE,
    "ChangeShip": _TELEPORT_VEHICLE,
    "EnableGlide": _TELEPORT_VEHICLE,
    "HasAnySailorBeenSummoned": _TELEPORT_VEHICLE,
    "OutVehicle": _TELEPORT_VEHICLE,
    "CameraFocus": _TELEPORT_VEHICLE,
    "ResetMarker": _TELEPORT_VEHICLE,
    "Teleport": _TELEPORT_VEHICLE,
    "TeleportCheck": _TELEPORT_VEHICLE,
    "TeleportThenPlayMovie": _TELEPORT_VEHICLE,
    "TeleportWithVehicle": _TELEPORT_VEHICLE,
    "Warp": _TELEPORT_VEHICLE,
    "WarpNearestMarker": _TELEPORT_VEHICLE,
    # UI/cutscene/message (11)
    "BookBattleField": _UI_MOVIE_MESSAGE,
    "EnterInstanceThenPlayMovie": _UI_MOVIE_MESSAGE,
    "LoadConditionStore": _UI_MOVIE_MESSAGE,
    "LoadItemExchangeStore": _UI_MOVIE_MESSAGE,
    "LoadSmithStore": _UI_MOVIE_MESSAGE,
    "LoadStore": _UI_MOVIE_MESSAGE,
    "OpenHelpUI": _UI_MOVIE_MESSAGE,
    "OpenUI": _UI_MOVIE_MESSAGE,
    "PlayMovie": _UI_MOVIE_MESSAGE,
    "ShowMessage": _UI_MOVIE_MESSAGE,
    "SuveryOwner": _UI_MOVIE_MESSAGE,
    # instance entry (3)
    "EnterInstance": _INSTANCE_ENTRY,
    "LeaveInstance": _INSTANCE_ENTRY,
    "LoadInstanceGroup": _INSTANCE_ENTRY,
    # world spawn (1)
    "MobAppear": _MOB_APPEAR,
}


def _log_bad_arity(log: Callable[[str], None], api_name: str, got: int, want: str) -> None:
    log("LUA_PLAYER_BAD_ARITY Player.%s got=%d want=%s" % (api_name, got, want))


class RealPlayerNamespace:
    """Drop-in replacement for ``script_host.ApiNamespaceStub`` on ``Player``.

    Same three-way ``__getitem__`` contract ``lua_api.trigger.
    RealTriggerNamespace``/``lua_api.quest.RealQuestNamespace`` already
    establish: real API name -> callable; other API name -> stub callable
    that logs and returns :data:`STUB_DEFAULT`; anything else (e.g.
    ``Var1``) -> bare :data:`STUB_DEFAULT`, silently.
    """

    __slots__ = ("_context", "_log", "_stub_methods", "namespace", "calls")

    def __init__(self, methods: frozenset, context: PlayerContext,
                 log: Callable[[str], None]):
        self.namespace = "Player"
        self._context = context
        self._log = log
        self._stub_methods = methods - REAL_METHODS
        self.calls: list = []

    def __getitem__(self, name):
        if name == "GetLv":
            def get_lv(*args):
                self.calls.append("Player.GetLv")
                if len(args) != 0:
                    _log_bad_arity(self._log, "GetLv", len(args), "0")
                    return STUB_DEFAULT
                level = self._context.level
                self._log("LUA_PLAYER_REAL Player.GetLv level=%d" % level)
                return level

            return get_lv

        if name == "GetClass":
            def get_class(*args):
                self.calls.append("Player.GetClass")
                if len(args) != 0:
                    _log_bad_arity(self._log, "GetClass", len(args), "0")
                    return STUB_DEFAULT
                class_id = self._context.class_id
                self._log("LUA_PLAYER_REAL Player.GetClass class_id=%d" % class_id)
                return class_id

            return get_class

        if name in self._stub_methods:
            qualified = "Player.%s" % name

            def stub(*_args, _qualified=qualified):
                self.calls.append(_qualified)
                self._log("LUA_API_STUB %s" % _qualified)
                return STUB_DEFAULT

            return stub

        return STUB_DEFAULT

    def __setitem__(self, name, value):
        # Same posture as ApiNamespaceStub/RealTriggerNamespace/
        # RealQuestNamespace: no script in the corpus assigns into a
        # namespace table at runtime; accept and discard.
        return None


def build_namespace(methods: frozenset, log: Callable[[str], None], *,
                     context: Optional[PlayerContext] = None) -> RealPlayerNamespace:
    """The ``Player`` global ``ScriptHost`` installs, real half included.

    ``context`` defaults to :data:`DEFAULT_CONTEXT` -- not a production
    singleton, an inert well-defined default -- so a caller that does not
    ask for anything special (every test today except the ones that
    specifically probe context behaviour) gets the same fixed constants
    every fresh login composes, the same posture
    ``lua_api.trigger.build_namespace``/``lua_api.quest.build_namespace``
    already take for their own default context/registry/clock.
    """
    return RealPlayerNamespace(
        methods, context if context is not None else DEFAULT_CONTEXT, log)
