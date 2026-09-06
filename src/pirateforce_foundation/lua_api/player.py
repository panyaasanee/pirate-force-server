"""LANE-Q's ``Player`` namespace: 6 of 73 names real
(``GetLv``/``GetClass``, ``CheckItemNum``/``GetItemNum``/``CheckEquipItem``,
plus this round's ``MobAppear``).

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

WHY THIS ROUND ALSO TAKES `CheckItemNum`/`GetItemNum`/`CheckEquipItem`
(`COO-DECISION 20260906_1846`'s "inventory seam, read side" item, ranked
#2 system-wide).  These are the three highest-call-count `_ITEM_STATE`
names (`api_spec.tsv`: `CheckItemNum` 211 calls/105 files/arity 2,
`GetItemNum` 99 calls/72 files/arity 1, `CheckEquipItem` 14 calls/2
files/arity 1 -- 324 of the item/equipment group's calls) and, unlike
every other `_ITEM_STATE` name, none of the three WRITES anything --
COO's own ranking letter draws exactly this line ("read side first ...
write side needs a wire frame answering the client, blocked on
`RE-280`").  Grepped call shape, not guessed (`gamedata/lua/**/*.lua`):
`Player.CheckItemNum(templateId, count)` -- `Quest/q_guildgather1.lua:41`,
`Quest/q_week_gather1.lua:43`, 103 more files, always exactly 2 args, used
as a boolean gate ("does the player hold at least `count` of item
`templateId`"); `Player.GetItemNum(templateId)` -- `t_getm_t1.lua:7`,
`Quest/q_gather_new.lua:205`, 70 more files, always exactly 1 arg, used as
an integer (assigned into a local, later compared/subtracted); every
`Player.CheckEquipItem(templateId)` call site (`Quest/q_kill1_2.lua:14-20`,
`Quest/q_con3.lua:12-18`, both files, 14 calls total) chains several
literal template ids with `or`/`and` as a plain boolean, e.g. "is any of
these blades equipped".

WHAT "REAL" MEANS HERE, FOR THESE THREE, PRECISELY.  `PlayerContext` widens
by two fields, `backpack` (an `inventory.BackpackState`, the exact type
`store.get_backpack`/`inventory.require_backpack_shape` already use --
NOT a new item model) and `equipped_template_ids` (a `frozenset[int]`, the
exact set `store.list_equipped_items`'s own `(slot_id, item_identity,
item_template_id)` rows reduce to by dropping slot/identity, since none of
these three questions is slot-aware). `GetItemNum` sums
`ItemAttrState.quantity` across every backpack row whose `template_id`
matches; `CheckItemNum` is that sum compared against the caller's second
argument; `CheckEquipItem` is template-id membership in
`equipped_template_ids`. Both new fields default to EMPTY (no items, no
equips) -- the same "inert default, not a guess" posture `level`/
`class_id` already take, not `INITIAL_BACKPACK`/`MERGED_V111_BACKPACK`
(picking either specific golden as "the" default would assert something
about who the anonymous default player is that nothing supports). `store.py`
is charter-listed as NOT LANE-Q's write zone and this round does not import
or call it: no live dispatcher exists yet (same posture `GetLv`/`GetClass`
already documented above) to fetch a real session's actual backpack/
equipment and build a `PlayerContext` from it -- that wiring, when it
lands, calls `store.get_backpack(sid, character_id)` and
`store.list_equipped_items(character_id)` and passes their results
straight through to these two fields, no new store-side reads needed.

WHY EVERY OTHER PLAYER.* NAME STAYS A STUB THIS ROUND, GROUPED, NOT
GUESSED.  See `STILL_STUBBED` below -- 67 names, one of seven named
category reasons each (item/equipment state, a stat-grant write seam,
other per-character stat reads this lane's context does not carry yet,
skill/buff state cross-lane with combat, a teleport/vehicle/camera wire
frame, a UI/cutscene/message wire frame, the instance-entry frame).
`MobAppear` itself moves to `REAL_METHODS` THIS round -- see the next
section for exactly what "real" means for it and, just as importantly,
what it deliberately still does not do.

WHY `MobAppear` IS REAL NOW, AND WHY IT IS STILL A FLAG, NOT A SPAWN
(`COO-DECISION 20260907_0043` answering `PANYA-DECISION 20260907_0039`/
ka1-A's own `20260907_0039_KA1A-PANYA-DECISION-COO-shared-world-plus-
per-player-npc-visibility-rank-rule.md`).  LANE-A's own letter
(`pf_bridge/notes_to_chief/20260906_0727_LANE-A-TO-LANE-Q-world-registry-
interface-and-trigger-hit-hook-point.md`, section (c).1) still states,
unchanged this round, that there is no function name meaning "add one
monster to an already-populated scene and tell the client" -- so this
round does NOT bind `MobAppear` to any spawn/despawn frame, world
registry, or census composer (LANE-A's write zone, untouched by this
diff). What changed is the OWNER'S OWN DESIGN DECISION, not LANE-A's
world-registry readiness: `Player.MobAppear(id, true/false)` is now known
to be a PER-PLAYER VISIBILITY FLAG, never a world event
(`PANYA-DECISION 20260907_0039` point 3: "ติ๊ก/ดับธงในบันทึกของผู้เล่นคนนั้น
-- ไม่สร้าง/ลบตัวละครในโลกร่วม"; ka1-A's own measurement: 1,766 `(id,
true)` calls plus 1,766 `(id, false)` calls across `Accept_Run`/
`Report_Run`, always through the `Player.*` calling convention, never
`Scene.*`) -- a shape this lane CAN service today without waiting on
LANE-A's item 3 (the visibility filter itself), because recording a flag
needs no world registry, no wire frame, and no census composer, only the
same injectable-store seam `lua_api.quest.QuestStateStore` already
established for this package. `PlayerMobAppearStore` below is that seam:
``set_mob_appear_flag``/``get_mob_appear_flag``, keyed by
(character_id, mob_id), an inert process-memory bucket by default
(:class:`InMemoryPlayerMobAppearStore`), same "correct to reset on
reboot, wrong to reset on relog" question `lua_api.quest.
InMemoryQuestStateStore`'s own docstring raises for quest state -- open
here too, not yet answered, and not this round's decision to make.

WHAT THIS ROUND DELIBERATELY DOES NOT DO.  (1) It does not read or write
LANE-A's `world_scene_registry`/`mob_ground_persistence`/
`mob_death_persistence` -- confirmed by this file's own imports (`..
inventory`, `..player_wire` only, unchanged). (2) It does not implement
`PANYA-DECISION 20260907_0039`'s own visibility filter (point 2: "ส่ง
ตัวละครนี้ให้คนนี้ไหม") -- that composition, and the eventual read of
this store from a census/appear frame, stays LANE-A's item 3, after P-2,
per the decision's own "ลำดับ 1->2->3->4->5 ไม่เปลี่ยน" line; this round only
gives A's future filter a store to read FROM. (3) It does not decide the
`rank>0` question `PANYA-DECISION 20260907_0039` point 3 raises ("ถ้าเจอ
สคริปต์เรียก MobAppear กับ id ที่ rank>0 อย่าตัดสินเอง"): grepping every one
of the 3,532 `Player.MobAppear(...)` call sites in the corpus
(`gamedata/lua/**/*.lua`) shows every single argument is a table-driven
`Quest.VarN` (`Var13`-`Var20`, the two highest-count shapes each 294-295
sites), never a literal mob-template id -- so which real `n_ID` (and
therefore which `n_RANK`) any given call actually names is not visible
from the script text alone; it lives in each quest's own
`QUESTDATA_*.tsv` row, not mined this round. Reported plainly rather than
guessed one way or the other; see this round's own round file.

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

try:
    from typing import Protocol
except ImportError:  # pragma: no cover - stdlib since Python 3.8, this project's floor
    Protocol = object  # type: ignore[assignment,misc]

from .. import inventory, player_wire
from . import message as _message

#: Mirrors ``script_host.STUB_DEFAULT`` without importing that module
#: (``script_host`` imports THIS package, via ``lua_api/__init__.py`` ->
#: importing it back here would be circular) -- same posture
#: ``lua_api/trigger.py`` and ``lua_api/quest.py`` already take, kept equal
#: to it by the same cross-module test those two are checked by
#: (``tests/test_script_lua_api_player.py``).
STUB_DEFAULT = 0

#: The corpus's own template-id/quantity bounds (matches
#: ``inventory.require_backpack_shape``'s ``item_template_id``/``quantity``
#: checks and ``store.equip_item``'s ``item_template_id`` bound exactly --
#: not independently guessed) -- a sanity door on decoded arguments, same
#: role ``lua_api.trigger._MAX_TRIGGER_ID``/``_MAX_STATUS`` play there.
_MAX_TEMPLATE_ID = 0xFFFFFFFF
_MAX_QUANTITY = 0xFFFF

#: ``mob_id`` (``MobAppear``'s first argument): same reasoning/value as
#: ``lua_api.quest._MAX_MOB_ID`` -- no table this round mined caps mob
#: template ids explicitly; kept wide, a sanity door against a garbage
#: float arriving from Lua, not a guessed game rule.
_MAX_MOB_ID = 0xFFFFFFFF


def _coerce_int(value, ceiling: int):
    """Lua hands numbers back as floats; an int door that never raises.

    Identical shape to ``lua_api.trigger._coerce_int`` (kept as a separate
    copy, not a shared import, the same posture every namespace module in
    this package already takes to avoid a cross-namespace coupling none of
    them need): ``None`` means "not a usable number", booleans are
    rejected explicitly (``True`` is an ``int`` in Python and would
    otherwise silently become template id 1), and a decoded value outside
    ``[0, ceiling]`` is refused rather than clamped.
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


def _item_count(backpack: "inventory.BackpackState", template_id: int) -> int:
    """Total quantity of ``template_id`` across every backpack row, or 0.

    Sums rather than counts rows: two stacks of the same template (a
    pre-merge V111 bag, for instance) must add up to the total a script's
    ``GetItemNum`` expects, not the row count.

    NEVER RAISES, MEASURED (pf-adversary, round `qbr5h8`).  A first draft
    trusted ``context.backpack`` unconditionally -- fine for every test
    today (``DEFAULT_CONTEXT``/every hand-built ``PlayerContext`` is
    well-formed) but a live crash the day a future dispatcher passes
    through a ``store.get_backpack`` decode failure, a bare ``None``, or a
    row with a non-numeric ``quantity``: adversary reproduced
    ``TypeError``/``AttributeError`` straight out of ``ScriptHost.call`` for
    exactly those three shapes. Every OTHER real closure in this package
    already treats bad input as "answer 0/False", never "raise" -- this
    function now matches that contract for the CONTEXT, not just the Lua
    arguments (``_coerce_int`` already covered those).
    """
    try:
        return sum(
            item.quantity for item in backpack.items
            if item.template_id == template_id
        )
    except Exception:                                    # noqa: BLE001
        return 0


def _is_equipped(equipped_template_ids, template_id: int) -> bool:
    """``template_id in equipped_template_ids``, or ``False`` -- never raises.

    Same posture as :func:`_item_count`: a malformed
    ``equipped_template_ids`` (e.g. ``None``) must degrade to "not
    equipped", not crash the script call.
    """
    try:
        return template_id in equipped_template_ids
    except Exception:                                    # noqa: BLE001
        return False


#: The empty inventory/equipment state -- no items, nothing equipped. The
#: same "inert default, not a guess" posture ``level``/``class_id`` already
#: take on :data:`DEFAULT_CONTEXT` below, not either governed golden
#: snapshot (``inventory.INITIAL_BACKPACK``/``MERGED_V111_BACKPACK``):
#: picking one of those as "the" default anonymous player would assert
#: something about who that player is that nothing supports.
_EMPTY_BACKPACK = inventory.BackpackState(
    inventory.BACKPACK_BASE_MASK, inventory.BACKPACK_BASE_IDENTITY,
    inventory.BACKPACK_RANGE_MASK, (),
)

#: The seven names real so far. See the module docstring for why these
#: seven, and why every other Player.* name is not real yet.
REAL_METHODS = frozenset({
    "GetLv", "GetClass", "CheckItemNum", "GetItemNum", "CheckEquipItem",
    "MobAppear", "ShowMessage",
})


class PlayerMobAppearStore(Protocol):
    """The seam :func:`build_namespace`'s ``store`` parameter names: a
    per-(character, mob template id) boolean visibility FLAG, never a
    world-registry entry -- see the module docstring's "WHY `MobAppear` IS
    REAL NOW" section for the full design citation
    (`COO-DECISION 20260907_0043`/`PANYA-DECISION 20260907_0039`).

    Same shape as ``lua_api.quest.QuestStateStore``: every method takes
    already-COERCED plain ints/bools -- the caller (this module's own
    ``MobAppear`` closure) validates whatever a script handed in before it
    ever reaches a store; a store implementation never sees an unvalidated
    Lua value.
    """

    def get_mob_appear_flag(self, character_id: int, mob_id: int) -> Optional[bool]:
        """The stored flag, or ``None`` if this (character, mob) has never
        had one set."""
        ...

    def set_mob_appear_flag(self, character_id: int, mob_id: int,
                             visible: bool) -> bool:
        """Write the flag; returns the value now on record (read back
        after the write, same contract as
        ``QuestStateStore.set_quest_flag``, never a bare echo of the
        argument)."""
        ...


#: Per-store bounds, same shape/reasoning as ``lua_api.quest``'s
#: ``CHARACTERS_CAP``/``QUESTS_PER_CHARACTER_CAP``: a cap a script cannot
#: grow past by looping, refused by name rather than silently evicted.
_MOB_APPEAR_CHARACTERS_CAP = 4096
_MOB_APPEAR_MOBS_PER_CHARACTER_CAP = 4096


class InMemoryPlayerMobAppearStore:
    """The default :class:`PlayerMobAppearStore` when no real one is
    injected -- PROCESS MEMORY, an INERT BUCKET for tests and spikes, same
    role ``lua_api.quest.InMemoryQuestStateStore`` plays for quest state
    (see that class's own docstring for the "correct to reset on reboot,
    open question on relog" framing this store inherits unanswered, not
    resolved here). Never raises on a read/write a script's own arguments
    could reach; a non-positive cap is a caller-programming error and does
    raise ``ValueError``, same distinction every other in-package store
    documents for itself.
    """

    def __init__(self, characters: int = _MOB_APPEAR_CHARACTERS_CAP,
                 mobs_per_character: int = _MOB_APPEAR_MOBS_PER_CHARACTER_CAP) -> None:
        for name, value in (("characters", characters),
                            ("mobs_per_character", mobs_per_character)):
            if type(value) is bool or not isinstance(value, int) or value < 1:
                raise ValueError("%s must be a positive int" % name)
        self._characters_cap = characters
        self._mobs_per_character_cap = mobs_per_character
        self._flags: dict = {}

    def get_mob_appear_flag(self, character_id: int, mob_id: int) -> Optional[bool]:
        return self._flags.get(character_id, {}).get(mob_id)

    def set_mob_appear_flag(self, character_id: int, mob_id: int,
                             visible: bool) -> bool:
        rows = self._flags.get(character_id)
        if rows is None:
            if len(self._flags) >= self._characters_cap:
                return self.get_mob_appear_flag(character_id, mob_id) or False
            rows = self._flags.setdefault(character_id, {})
        if mob_id not in rows and len(rows) >= self._mobs_per_character_cap:
            return rows.get(mob_id, False)
        rows[mob_id] = visible
        return visible


@dataclass(frozen=True)
class PlayerContext:
    """What "the player running this script" means to this namespace.

    ``level``/``class_id`` default to the exact constants every fresh
    login composes today (``player_wire.PLAYER_LOGIN_LEVEL`` == 1,
    ``player_wire.PLAYER_LOGIN_CLASS_ID`` == 1) -- not a guess, the same
    values ``model.Character``'s own two fields (``level``, ``class_id``,
    both ``int | None``) fall back to when a login does not override them.
    ``backpack``/``equipped_template_ids`` (round `qbr5h8`) default to
    empty -- see :data:`_EMPTY_BACKPACK`'s own docstring for why empty
    rather than either governed golden snapshot. ``character_id`` (this
    round) is the ONLY field ``MobAppear`` reads to key its per-player flag
    store -- 0 by default, the same "not a real character" sentinel
    ``lua_api.quest.DEFAULT_CONTEXT``'s own ``character_id=0`` already uses
    (character ids in this codebase start at 1, per ``store.py``'s own
    autoincrement primary key), so two unrelated tests/spikes that both
    take the default share the default's own bucket with each other
    (harmless: neither is a live player) rather than colliding with a real
    one. A real per-session dispatcher (not built this round) supplies its
    own ``PlayerContext`` built from that ``Character`` plus
    ``store.get_backpack``/``store.list_equipped_items`` instead of relying
    on these defaults, the same seam
    ``lua_api.trigger.TriggerContext``/``lua_api.instance.InstanceContext``
    already established for their own namespaces.
    """

    level: int = player_wire.PLAYER_LOGIN_LEVEL
    class_id: int = player_wire.PLAYER_LOGIN_CLASS_ID
    backpack: "inventory.BackpackState" = _EMPTY_BACKPACK
    equipped_template_ids: frozenset = frozenset()
    character_id: int = 0


#: The context a :class:`RealPlayerNamespace` gets when nothing more
#: specific is supplied (``ScriptHost`` outside of a real dispatch, e.g.
#: every existing corpus/spike test) -- a well-defined, inert default, not
#: a production singleton, mirroring ``lua_api.trigger.DEFAULT_CONTEXT``.
DEFAULT_CONTEXT = PlayerContext()

#: The remaining 67 names, one of eight grouped, grep-grounded reasons each
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
STILL_STUBBED: dict[str, str] = {
    # item/equipment state (10) -- CheckItemNum/GetItemNum/CheckEquipItem
    # (the read-only three) moved to REAL_METHODS this round; the rest
    # still need a write seam (AddAndEquip/AddItem/RemoveItem/...) this
    # lane does not own yet.
    "AddAndEquip": _ITEM_STATE,
    "AddItem": _ITEM_STATE,
    "RemoveItem": _ITEM_STATE,
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
    # UI/cutscene/message (10) -- ShowMessage moved to REAL_METHODS in
    # round `6775u1`; the other ten still need their own outbound frame.
    "BookBattleField": _UI_MOVIE_MESSAGE,
    "EnterInstanceThenPlayMovie": _UI_MOVIE_MESSAGE,
    "LoadConditionStore": _UI_MOVIE_MESSAGE,
    "LoadItemExchangeStore": _UI_MOVIE_MESSAGE,
    "LoadSmithStore": _UI_MOVIE_MESSAGE,
    "LoadStore": _UI_MOVIE_MESSAGE,
    "OpenHelpUI": _UI_MOVIE_MESSAGE,
    "OpenUI": _UI_MOVIE_MESSAGE,
    "PlayMovie": _UI_MOVIE_MESSAGE,
    "SuveryOwner": _UI_MOVIE_MESSAGE,
    # instance entry (3)
    "EnterInstance": _INSTANCE_ENTRY,
    "LeaveInstance": _INSTANCE_ENTRY,
    "LoadInstanceGroup": _INSTANCE_ENTRY,
}


def _log_bad_arity(log: Callable[[str], None], api_name: str, got: int, want: str) -> None:
    log("LUA_PLAYER_BAD_ARITY Player.%s got=%d want=%s" % (api_name, got, want))


def _log_bad_value(log: Callable[[str], None], api_name: str, **raw_args) -> None:
    """One bad-VALUE line (right arity, unusable argument) -- same shape as
    ``lua_api.quest._log_bad_value``, this namespace's first use of it
    (``pf-adversary``, round `7v7yn2`, named this gap for `Quest.*`'s own
    nine closures; ``Player.MobAppear`` is the first ``Player.*`` real
    closure that can be given a right-arity, wrong-TYPE argument -- every
    prior real closure here either has no failure mode past arity
    (``GetLv``/``GetClass``) or already degrades to a plain 0/False result
    without a distinct bad-value log line, per its own docstring).
    """
    log("LUA_PLAYER_BAD_VALUE Player.%s %s" % (
        api_name, " ".join("%s=%r" % (k, v) for k, v in raw_args.items())))


class RealPlayerNamespace:
    """Drop-in replacement for ``script_host.ApiNamespaceStub`` on ``Player``.

    Same three-way ``__getitem__`` contract ``lua_api.trigger.
    RealTriggerNamespace``/``lua_api.quest.RealQuestNamespace`` already
    establish: real API name -> callable; other API name -> stub callable
    that logs and returns :data:`STUB_DEFAULT`; anything else (e.g.
    ``Var1``) -> bare :data:`STUB_DEFAULT`, silently.
    """

    __slots__ = ("_context", "_store", "_sink", "_log", "_stub_methods",
                 "namespace", "calls")

    def __init__(self, methods: frozenset, context: PlayerContext,
                 log: Callable[[str], None],
                 store: "PlayerMobAppearStore",
                 sink: "_message.MessageSink"):
        self.namespace = "Player"
        self._context = context
        self._store = store
        self._sink = sink
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

        if name == "GetItemNum":
            def get_item_num(*args):
                self.calls.append("Player.GetItemNum")
                if len(args) != 1:
                    _log_bad_arity(self._log, "GetItemNum", len(args), "1")
                    return STUB_DEFAULT
                template_id = _coerce_int(args[0], _MAX_TEMPLATE_ID)
                count = (
                    0 if template_id is None
                    else _item_count(self._context.backpack, template_id)
                )
                self._log(
                    "LUA_PLAYER_REAL Player.GetItemNum template_id=%r count=%d"
                    % (args[0], count))
                return count

            return get_item_num

        if name == "CheckItemNum":
            def check_item_num(*args):
                self.calls.append("Player.CheckItemNum")
                if len(args) != 2:
                    _log_bad_arity(self._log, "CheckItemNum", len(args), "2")
                    return STUB_DEFAULT
                template_id = _coerce_int(args[0], _MAX_TEMPLATE_ID)
                required = _coerce_int(args[1], _MAX_QUANTITY)
                if template_id is None or required is None:
                    result = False
                else:
                    held = _item_count(self._context.backpack, template_id)
                    result = held >= required
                self._log(
                    "LUA_PLAYER_REAL Player.CheckItemNum template_id=%r "
                    "required=%r result=%s" % (args[0], args[1], result))
                return result

            return check_item_num

        if name == "CheckEquipItem":
            def check_equip_item(*args):
                self.calls.append("Player.CheckEquipItem")
                if len(args) != 1:
                    _log_bad_arity(self._log, "CheckEquipItem", len(args), "1")
                    return STUB_DEFAULT
                template_id = _coerce_int(args[0], _MAX_TEMPLATE_ID)
                result = template_id is not None and _is_equipped(
                    self._context.equipped_template_ids, template_id)
                self._log(
                    "LUA_PLAYER_REAL Player.CheckEquipItem template_id=%r "
                    "result=%s" % (args[0], result))
                return result

            return check_equip_item

        if name == "MobAppear":
            def mob_appear(*args):
                self.calls.append("Player.MobAppear")
                if len(args) != 2:
                    _log_bad_arity(self._log, "MobAppear", len(args), "2")
                    return STUB_DEFAULT
                mob_id = _coerce_int(args[0], _MAX_MOB_ID)
                visible = args[1]
                if mob_id is None or not isinstance(visible, bool):
                    _log_bad_value(self._log, "MobAppear",
                                    mob_id=args[0], visible=args[1])
                    return STUB_DEFAULT
                after = self._store.set_mob_appear_flag(
                    self._context.character_id, mob_id, visible)
                # NOT a world spawn/despawn -- a per-player visibility flag
                # only (PANYA-DECISION 20260907_0039 point 3, COO-DECISION
                # 20260907_0043 point 2); see the module docstring's "WHY
                # MobAppear IS REAL NOW" section. LANE-A's own world
                # registry (world_scene_registry/mob_ground_persistence/
                # mob_death_persistence) is untouched by this closure.
                self._log(
                    "LUA_PLAYER_REAL Player.MobAppear character=%d mob_id=%d "
                    "visible=%s (per-player flag only, not a world spawn)"
                    % (self._context.character_id, mob_id, after))
                return after

            return mob_appear

        if name == "ShowMessage":
            def show_message(*args):
                self.calls.append("Player.ShowMessage")
                if len(args) != 1:
                    _log_bad_arity(self._log, "ShowMessage", len(args), "1")
                    return STUB_DEFAULT
                message_id = _coerce_int(args[0], _message.MAX_MESSAGE_ID)
                if message_id is None or not _message.is_known_message_id(message_id):
                    # An id with no row in the shipped table is a message
                    # the client could never render -- refused by name, not
                    # recorded as if it were showable.
                    _log_bad_value(self._log, "ShowMessage", message_id=args[0])
                    return STUB_DEFAULT
                # scene=None: an individual message belongs to the
                # character, not to wherever they happen to be standing.
                shown = self._sink.record(
                    None, self._context.character_id,
                    _message.AUDIENCE_INDIVIDUAL, message_id)
                # RECORDS which message to show. Does NOT build or send
                # ShowMessageVital -- no module in this package does; see
                # lua_api/message.py's own module docstring.
                self._log(
                    "LUA_PLAYER_REAL Player.ShowMessage character=%d "
                    "message_id=%d audience=%s notify_type=%d stored=%d "
                    "(recorded only, no frame sent; stored=0 means the "
                    "sink refused it at a cap)"
                    % (self._context.character_id, message_id,
                       _message.audience_name(_message.AUDIENCE_INDIVIDUAL),
                       _message.notify_type(message_id), shown))
                return shown

            return show_message

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
                     context: Optional[PlayerContext] = None,
                     store: Optional["PlayerMobAppearStore"] = None,
                     sink: "Optional[_message.MessageSink]" = None) -> RealPlayerNamespace:
    """The ``Player`` global ``ScriptHost`` installs, real half included.

    ``context`` defaults to :data:`DEFAULT_CONTEXT` -- not a production
    singleton, an inert well-defined default -- so a caller that does not
    ask for anything special (every test today except the ones that
    specifically probe context behaviour) gets the same fixed constants
    every fresh login composes, the same posture
    ``lua_api.trigger.build_namespace``/``lua_api.quest.build_namespace``
    already take for their own default context/registry/clock. ``store``
    (this round, for ``MobAppear``) defaults to a FRESH PRIVATE
    :class:`InMemoryPlayerMobAppearStore` -- not a process singleton, same
    posture ``lua_api.quest.build_namespace`` takes for its own default
    :class:`InMemoryQuestStateStore` -- so two unrelated tests/spikes that
    both take the default can never collide. ``sink`` (round `6775u1`, for
    ``ShowMessage``) defaults the same way to a FRESH PRIVATE
    ``lua_api.message.InMemoryMessageSink``. A caller that wants
    ``Player.ShowMessage`` and ``Trigger.TriggerShowMessage`` in the SAME
    script run to land in one ordered record MUST pass the identical
    ``sink`` instance to both this function and
    ``lua_api.trigger.build_namespace``.
    """
    return RealPlayerNamespace(
        methods, context if context is not None else DEFAULT_CONTEXT, log,
        store if store is not None else InMemoryPlayerMobAppearStore(),
        sink if sink is not None else _message.InMemoryMessageSink())
