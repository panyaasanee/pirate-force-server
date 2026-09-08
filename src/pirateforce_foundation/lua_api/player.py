"""LANE-Q's ``Player`` namespace: 11 of 73 names real
(``GetLv``/``GetClass``, ``CheckItemNum``/``GetItemNum``/``CheckEquipItem``,
``MobAppear``, ``ShowMessage``, round `yfeauz`'s ``AddExp``/
``AddSkillPoint`` -- the first two that WRITE -- round `2euu94`'s
``AddCash``, the first that can write in EITHER direction, and, added by
LANE-A on the COO's M2 order of round `2241`, ``TeleportCheck``).

WHY ``TeleportCheck`` STOPPED BEING A STUB, AND WHO OWNS IT.  Its stub reason
(``_TELEPORT_VEHICLE``) was "needs a world-movement/vehicle wire frame this
lane does not own, cross-lane with LANE-A's world registry", and that is
exactly what has now arrived: ``RE-303`` (PASS) measured the whole exchange
byte by byte, and ``world_m2_teleport_check`` -- a LANE-A module -- owns the
frame.  The closure below is therefore LANE-A's, living in LANE-Q's file
because that is where the name is, not because the lane boundary moved.

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
GUESSED.  See `STILL_STUBBED` below -- 61 names, one of seven named
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
from .. import world_m2_teleport_check as _teleport_check
from . import message as _message
from . import quest_criteria as _quest_criteria
from . import reward as _reward

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


def _coerce_signed_int(value, magnitude_ceiling: int):
    """:func:`_coerce_int` with the floor removed -- and NOTHING else.

    ``_coerce_int`` refuses everything below 0 because every name that
    uses it wants an id or an amount that only ever adds.  ``AddCash``
    does not: ``q_ship.lua:50`` writes ``Player.AddCash(-Quest.Var3)``,
    and a coercion whose floor is 0 turns that charge into ``None`` --
    logged as a bad value, and the ship handed over for free.  So this
    door accepts ``[-magnitude_ceiling, +magnitude_ceiling]`` and hands
    the SIGN on to the caller to resolve.

    WHY A SECOND FUNCTION AND NOT A ``floor=`` PARAMETER ON THE FIRST
    (this is the asymmetry a reader should ask about).  ``AddExp`` and
    ``AddSkillPoint`` MUST keep the floor: their columns have no
    subtracting door this lane routes to, so a negative arriving at one of
    them is a decode fault, and it must stay a refused BAD VALUE rather
    than become a charge nobody asked for.  A shared function with a
    default would put both behaviours one keyword apart, and the day
    someone adds a ninth name the safe choice would be the one you get by
    forgetting to type something.  Two functions with two names cannot be
    got wrong by omission.

    EVERY OTHER REFUSAL OF ``_coerce_int`` IS KEPT, deliberately and not
    by accident of copying: ``bool`` (``True`` would become 1 currency),
    ``nan``/``inf`` (they compare false against every bound, so an
    unguarded range check lets them through), a float with a fractional
    part (Lua has one number type; ``2.5`` coins is a decode fault, not a
    rounding question), and a magnitude past the ceiling.  ``-0.0``
    becomes ``0``, which both callers then refuse as "nothing to pay" --
    the same answer ``0`` gets, which is the right one.
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
    if value < -magnitude_ceiling or value > magnitude_ceiling:
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

#: The twelve names real so far. See the module docstring for why these
#: eleven, and why every other Player.* name is not real yet.
REAL_METHODS = frozenset({
    "GetLv", "GetClass", "CheckItemNum", "GetItemNum", "CheckEquipItem",
    "MobAppear", "ShowMessage",
    # The captain-report half of M2: RE-303 (PASS) measured the whole
    # handshake, so this name no longer needs a frame nobody owns.
    "TeleportCheck",
    # The two ADD-a-stat names whose column exists and whose sign is
    # always positive in the corpus (see :data:`GRANT_KINDS`).
    "AddExp", "AddSkillPoint",
    # The one stat name the corpus calls in BOTH directions, real from
    # round `2euu94` now that a spend door with a floor answer exists
    # (see :data:`SIGNED_STAT_KINDS`).
    "AddCash",
    # The purse READ the four spending quests gate themselves on, real
    # from round `yzdgx1` (see :data:`STAT_READ_KINDS`).
    "GetCash",
})

#: The API name -> reward kind map for the grant closures: which
#: ``characters`` column each name adds to.  FROZEN AND CLOSED, two
#: entries, and the value is one of this package's own
#: ``quest_criteria.KIND_*`` constants -- never a string a script can
#: produce, never a column name spelled here (``lua_api.reward.
#: KIND_COLUMN`` owns that mapping and a test pins it against
#: ``persistence_typed_attrs.TYPED_COLUMNS``).
#:
#: WHY ONLY TWO, when eight names sit under ``_STAT_GRANT``.  Neither is
#: called with a negative LITERAL anywhere in the corpus: all four call
#: sites are ``Player.GetLv()*Trigger.Var5`` in ``t_getm_rat_exp&sp.lua``
#: and ``t_inskyev_getm_rat_exp&sp.lua`` (grepped across all 616 files,
#: the only call sites of either).  SAID EXACTLY (pf-adversary D6, round
#: yfeauz, correcting an earlier wording here that claimed more): that is
#: a fact about the argument's SHAPE, not about its VALUE -- ``Var5`` is
#: trigger placement data that does not live in this repository, so its
#: sign is UNMEASURED, and the closure below is what actually holds the
#: floor by refusing anything negative before the store is touched.  Both
#: names land in a column
#: ``store.add_typed_attribute`` already accepts.  ``AddCash`` is NOT
#: here and never will be: it is the one name the corpus calls in both
#: directions, so it goes through :data:`SIGNED_STAT_KINDS` instead.  The
#: other five need columns (HP/ST/pp-class/morale) or a
#: percentage-of-level rule that no table in the committed artifacts pins.
GRANT_KINDS: dict[str, str] = {
    "AddExp": _quest_criteria.KIND_EXP,
    "AddSkillPoint": _quest_criteria.KIND_SKILL_POINT,
}

#: The API name -> reward kind map for the SIGNED closure: names the
#: corpus calls with amounts that go BOTH WAYS.  One entry, and the entry
#: is the reason this map is separate from :data:`GRANT_KINDS` rather than
#: a flag on it.
#:
#: ALL SIX CALL SITES, GREPPED (``grep -rn AddCash gamedata/lua/`` across
#: all 616 files, no other name in this map): four ADD --
#: ``q_guildgather1.lua:60`` and ``q_guild_boss2.lua:59``
#: (``Player.AddCash(Quest.Var8)``), ``q_class.lua:60`` and
#: ``q_class2.lua:58`` (``Player.AddCash(Quest.Var4)``) -- and two
#: SUBTRACT: ``q_ship.lua:50`` (``Player.AddCash(-Quest.Var3)``, buying a
#: ship) and ``q_boat_health.lua:21`` (``Player.AddCash(Quest.Var2 * -1)``,
#: repairing one).
#:
#: THAT SPLIT IS A FACT ABOUT SCRIPT TEXT, AND THE DATA DISAGREES WITH IT
#: (pf-adversary `D2`/`D3`, round `2euu94`, correcting this round's own
#: first draft, which said the ``VarN`` values "are not in this
#: repository" -- they are: ``pf_bridge/gamedata/tables/
#: QUESTDATA_TH__QUEST.tsv``, the same file
#: ``lua_api/quest_criteria_rows.tsv`` names in its own ``# source:``
#: header, and the file this lane's regen tool reads every time it runs).
#: Read against that table, the six call sites are:
#:
#: * ``q_class.lua:60`` and ``q_guild_boss2.lua:59`` -- written as ADDS,
#:   but their cells are u32-wrapped NEGATIVES
#:   (see :data:`_MAX_SIGNED_STAT_MAGNITUDE`).  Two charges the text
#:   census counted as payments.
#: * ``q_guildgather1.lua:60`` (rows 8041-8042) and ``q_class2.lua:58``
#:   (rows 3195-3199) -- their cells are ``0``, so they move nothing.
#: * ``q_boat_health.lua:21`` -- ``n_VARI_2 = 100``, negated in the
#:   script.  The one charge that is a charge in both text and data.
#: * ``q_ship.lua:50`` -- NO ROW AT ALL.  No ``s_LUASCRIPT`` in the
#:   table's 1544 rows dispatches that file (the only SHIP name is
#:   ``Q_SHIP_DYING``, a different script), which makes it a poor
#:   flagship citation however vivid the line is.
#:
#: So: ZERO of the six deliver a positive amount in today's data, and the
#: adding half of this door has no shipped caller yet.  Nothing in the
#: closure depends on the census either way -- it reads the SIGN OF THE
#: VALUE, never the sign of the source text.  The grep is provenance for
#: why the name needed both halves before it could open at all, not a
#: promise about what will arrive.
SIGNED_STAT_KINDS: dict[str, str] = {
    "AddCash": _quest_criteria.KIND_CASH,
}

#: The API name -> reward kind map for the balance-READ closures: which
#: ``characters`` column each name reports.  FROZEN AND CLOSED, one entry
#: today, and the value is one of this package's own ``KIND_*`` constants
#: for the same reason :data:`GRANT_KINDS` and :data:`SIGNED_STAT_KINDS`
#: use them -- ``lua_api.reward.KIND_COLUMN`` owns the column spelling and
#: a test pins it against ``persistence_typed_attrs.TYPED_COLUMNS``.
#:
#: WHY ``GetCash`` AND NOT THE OTHER FOURTEEN ``_STAT_READ`` NAMES.  Cash
#: is the only one of them whose column this lane ALREADY WRITES:
#: ``AddCash`` opened in round ``2euu94`` through
#: ``reward.grant``/``reward.charge`` onto ``characters.cash``.  Reading
#: the same column back through the same store is not new per-character
#: state and needs no wider ``PlayerContext`` -- which is precisely what
#: ``_STAT_READ`` says the other fourteen are still waiting for, and why
#: this one name leaves that group and the rest stay.
#:
#: WHAT IT UNBLOCKS, GREPPED (``grep -rn "Player.GetCash" gamedata/lua/``
#: = 7 call sites, 7 files, arity 0 at every one).  Four of them are the
#: guard in front of a charge this lane has already built the charging
#: half of:
#:
#:   * ``Quest/q_class.lua:47``       ``Player.GetCash() >= (Quest.Var3)``
#:     (``n_VARI_3`` = 15000, the class-change fee ``q_class.lua:60``
#:     then debits as ``n_VARI_4`` = 4294952296 = -15000)
#:   * ``Quest/q_class2.lua:44``      the same shape
#:   * ``Quest/q_boat_health.lua:18`` ``Player.GetCash() >= Quest.Var2``
#:     (the 100-cash boat repair of round ``kkuqzo``)
#:   * ``Quest/q_ship.lua:12``        the ship purchase
#:
#: With the name stubbed at ``STUB_DEFAULT`` every one of those four
#: guards was FALSE for every player forever, so the else branch ran and
#: the shipped quest's own affordability check never executed once.  That
#: is the limit ``reward.charge``'s docstring names from the other side:
#: ``q_ship.lua`` charges and then hands the ship over with no check of
#: its own, so the script's guard is the only thing standing between a
#: broke player and a free ship.
#:
#: The other three ask the same question for a quest that does not charge
#: through this lane's doors: ``q_guildgather1.lua:42`` and
#: ``q_guild_boss2.lua:42`` (``>= (Quest.Var5)``), and ``q_con3.lua:19``,
#: the only one of the seven that asks ``<=`` -- a CEILING, "you are poor
#: enough for this".  So the stub did NOT fail safe everywhere: it made
#: that one guard silently TRUE for everybody while the other six were
#: silently false, which is the direction worth naming.  ``q_con3`` is
#: also the one call site an unbound corpus sweep never reaches -- its
#: ``(Quest.Var4 == 0) or ...`` short-circuits on a 0 cell -- which is why
#: the corpus pins move by SIX where the grep counts seven (measured per
#: file, ``tests/test_script_lua_corpus.py``).
STAT_READ_KINDS: dict[str, str] = {
    "GetCash": _quest_criteria.KIND_CASH,
}

#: Sanity ceiling on a grant amount decoded off the Lua stack, the same
#: role ``_MAX_TEMPLATE_ID``/``_MAX_MOB_ID`` play for ids: not a game rule,
#: a door against a garbage float.  ``u32``, and THIS LANE'S OWN CHOICE
#: rather than the column's (pf-adversary D10, round yfeauz, correcting an
#: earlier comment here that presented it as deference):
#: ``persistence_typed_attrs`` calls ``experience`` a ``u64``
#: (max 9223372036854775807) and ``skill_points`` a ``u32``, so this bound
#: is 2**32 tighter than the wider of the two columns.  Deliberate: no
#: script in the corpus asks for a number anywhere near it, and a single
#: grant past ``u32`` is far likelier to be a decode fault than a reward.
#: The cost is named rather than hidden -- such an amount is refused as a
#: BAD VALUE with no ``refused=`` token, in the same bucket as ``nan``;
#: widening it is a one-constant change the day a real script needs it.
_MAX_GRANT_AMOUNT = 0xFFFFFFFF

#: The magnitude ceiling for the SIGNED door, and it is DELIBERATELY HALF
#: of :data:`_MAX_GRANT_AMOUNT` rather than the same number.
#:
#: THE DEFECT THIS CLOSES, MEASURED IN THE SHIPPED TABLE (pf-adversary
#: `D1`, round `2euu94`, against this round's own first draft).
#: ``gamedata/tables/QUESTDATA_TH__QUEST.tsv`` stores a negative ``n_VARI``
#: as UNSIGNED 32-BIT TWO'S COMPLEMENT, and each script's own gate proves
#: the sign rather than suggesting it:
#:
#: * ``Q_CLASS`` rows 3200-3204: ``n_VARI_3 = 15000`` is what
#:   ``q_class.lua:47`` checks the purse against
#:   (``Player.GetCash() >= Quest.Var3``), and ``n_VARI_4 = 4294952296``
#:   is what ``q_class.lua:60`` hands to ``AddCash`` -- and
#:   ``4294952296 == 2**32 - 15000`` exactly.
#: * ``Q_GUILD_BOSS2`` rows 8061-8065: the gate is ``n_VARI_5``
#:   (10000/40000/50000/50000/50000) and ``n_VARI_8`` is
#:   ``2**32 - n_VARI_5`` on every one of the five rows.
#:
#: With a ``u32`` ceiling those cells arrive as huge POSITIVE ints, the
#: closure below reads their sign as positive, and the class-change quest
#: CREDITS 4,294,952,296 instead of debiting 15,000 -- into a ``u64``
#: column that accepts it without a murmur.  A ceiling of ``i32`` max
#: turns every one of them into a REFUSED BAD VALUE with nothing written
#: and a log line naming the number, which is the correct answer for a
#: door that cannot yet tell a wrapped negative from a real payout.
#:
#: WHAT THIS IS NOT: it is not a decode rule.  Deciding that
#: ``n_VARI_4`` in ``Q_CLASS`` is signed currency while ``n_VARI_13``
#: elsewhere is an unsigned mob id is a per-column signedness rule that
#: belongs to whatever wires ``Quest.VarN`` to that table (which nothing
#: does yet -- ``Quest.VarN`` still answers ``STUB_DEFAULT``), and this
#: lane will not invent it inside a coercion.  Asked of COO by letter this
#: round.  Until it is answered, REFUSING is the only honest answer, and
#: no shipped reward comes anywhere near this bound: the largest cash
#: magnitude in the whole table is 50,000.
_MAX_SIGNED_STAT_MAGNITUDE = 0x7FFFFFFF


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

#: The remaining names -- 61 of them the day this line was last counted
#: (2026-09-08, LANE-A round 1v5i3h, answering LANE-Q's letter
#: ``20260908_1648_LANE-Q-TO-LANE-A-the-player-stub-count-moved-again``)
#: -- one of seven grouped, grep-grounded reasons each
#: -- no per-name guess, the same posture ``lua_api.quest.STILL_STUBBED``
#: takes for its own DB-blocked names. Category text is shared verbatim
#: across every name in that category (the same repetition
#: ``lua_api.quest.STILL_STUBBED`` already uses for its own LANE-DB-blocked
#: entries), not independently reworded per name.
#: DO NOT TRUST THE NUMBER IN THIS COMMENT, AND DO NOT COPY IT ANYWHERE:
#: it has now gone stale twice (63 -> 62 -> 61) because names leave this
#: tuple every time a lane makes one real. ``len(STILL_STUBBED)`` is the
#: only count that cannot be wrong, and it is what
#: ``tests/test_script_lua_api_player.py`` pins -- the partition
#: (STILL_STUBBED | REAL_METHODS == every Player name, and the two do not
#: overlap), never a literal total.
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
    # AddExp/AddSkillPoint moved to REAL_METHODS in round `yfeauz` (see
    # GRANT_KINDS); AddCash moved in round `2euu94`, once LANE-DB's
    # store.spend_typed_attribute gave its negative call sites a floor
    # answer (see SIGNED_STAT_KINDS).  The five below do not qualify,
    # each for a reason named rather than "not done yet".
    "AddHP": _STAT_GRANT,
    "AddST": _STAT_GRANT,
    "AddPpClass": _STAT_GRANT,
    "GiveLvCriteriaPercentageEXP": _STAT_GRANT,
    "Addmoralized": _STAT_GRANT,
    # other per-character stat reads (14) -- GetCash moved to
    # REAL_METHODS in round `yzdgx1` (see STAT_READ_KINDS): its column is
    # the one this lane already writes, so it needed no wider
    # PlayerContext.  The fourteen below still do.
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
    # teleport/vehicle/camera (13) -- TeleportCheck moved to REAL_METHODS
    # this round (RE-303 PASS, COO order round `2241`); the other thirteen
    # still need an outbound frame no letter has measured.
    "BoatHealth": _TELEPORT_VEHICLE,
    "GetBoatHealth": _TELEPORT_VEHICLE,
    "ChangeShip": _TELEPORT_VEHICLE,
    "EnableGlide": _TELEPORT_VEHICLE,
    "HasAnySailorBeenSummoned": _TELEPORT_VEHICLE,
    "OutVehicle": _TELEPORT_VEHICLE,
    "CameraFocus": _TELEPORT_VEHICLE,
    "ResetMarker": _TELEPORT_VEHICLE,
    "Teleport": _TELEPORT_VEHICLE,
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

    ASCII ONLY, and that is why it is ``ascii()`` rather than ``%r``: the value
    printed here comes straight off a Lua stack, the bridge console is cp874,
    and a script that passes a character outside that page killed the line that
    was reporting the script's own mistake (pf-adversary, round `ew9416`).
    """
    log("LUA_PLAYER_BAD_VALUE Player.%s %s" % (
        api_name,
        " ".join("%s=%s" % (k, ascii(v)) for k, v in raw_args.items())))


class RealPlayerNamespace:
    """Drop-in replacement for ``script_host.ApiNamespaceStub`` on ``Player``.

    Same three-way ``__getitem__`` contract ``lua_api.trigger.
    RealTriggerNamespace``/``lua_api.quest.RealQuestNamespace`` already
    establish: real API name -> callable; other API name -> stub callable
    that logs and returns :data:`STUB_DEFAULT`; anything else (e.g.
    ``Var1``) -> bare :data:`STUB_DEFAULT`, silently.
    """

    __slots__ = ("_context", "_store", "_sink", "_payout_store", "_log",
                 "_stub_methods", "namespace", "calls",
                 "_teleport_check_sink")

    def __init__(self, methods: frozenset, context: PlayerContext,
                 log: Callable[[str], None],
                 store: "PlayerMobAppearStore",
                 sink: "_message.MessageSink",
                 payout_store=None,
                 teleport_check_sink=None):
        self.namespace = "Player"
        self._context = context
        self._store = store
        self._sink = sink
        # The character-column store the grant closures add through.  None
        # is the honest default and it REFUSES OUT LOUD rather than
        # pretending (lua_api.reward.REFUSE_NO_STORE): a namespace built
        # without one must never tell a script -- or a client -- that a
        # reward was paid when no row moved.
        self._payout_store = payout_store
        # Defaults to a FRESH PRIVATE recorder, same posture as ``store`` and
        # ``sink`` above -- never a process singleton.  Unlike ``payout_store``
        # this one DOES get a default, and the difference is real: a recorded
        # travel order that reaches no wire shows the player nothing and
        # promises nothing, whereas an in-memory reward balance would look
        # paid.  Nothing here can be mistaken for a completed journey.
        # SHAPE-CHECKED AT BUILD TIME, not at the first script call.  Every
        # other injected collaborator here is either a default this class
        # constructs or one whose absence refuses out loud; this one was the
        # only sink with no check at all, so a recorder missing ``record``
        # raised ``AttributeError`` out of the middle of a Lua closure, where
        # the traceback names the script and not the caller who passed the
        # wrong object (pf-adversary, round `w4cp5c`).  Raising here names it.
        if teleport_check_sink is not None:
            for required in ("record", "record_refusal"):
                if not callable(getattr(teleport_check_sink, required, None)):
                    raise TypeError(
                        "teleport_check_sink must have a callable %s(); %r "
                        "does not (record(character_id, pending) must also "
                        "RETURN 1 stored / 0 capped -- a recorder that returns "
                        "nothing is read as stored=unknown, never as a crash)"
                        % (required, type(teleport_check_sink)))
        self._teleport_check_sink = (
            teleport_check_sink if teleport_check_sink is not None
            else _teleport_check.InMemoryTeleportCheckSink())
        self._log = log
        self._stub_methods = methods - REAL_METHODS
        self.calls: list = []

    @property
    def teleport_check_sink(self):
        """The recorder every accepted travel order is written to.

        Readable BY NAME because the host that builds this namespace has to be
        able to hand the same object to whoever dispatches frames.  While it
        lived only in a private attribute the orders were unreachable from
        outside the namespace, so `Player.TeleportCheck` recorded a window no
        code could ever ask a client to draw (pf-adversary, round `ebh143`,
        D2).  Read-only on purpose: a namespace that swapped its sink
        mid-session would strand the orders already in the old one.
        """
        return self._teleport_check_sink

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

        if name in STAT_READ_KINDS:
            kind = STAT_READ_KINDS[name]

            def read_stat(*args, _name=name, _kind=kind):
                self.calls.append("Player.%s" % _name)
                if len(args) != 0:
                    _log_bad_arity(self._log, _name, len(args), "0")
                    return STUB_DEFAULT
                value, _reason = _reward.balance(
                    "Player.%s" % _name, _kind,
                    self._context.character_id,
                    store=self._payout_store, log=self._log)
                if value is None:
                    # STUB_DEFAULT ON EVERY REFUSAL, AND IT IS NOT A
                    # GUESS OF ZERO -- `reward.balance` has already
                    # logged WHICH refusal it was (an unmeasured column
                    # is `balance_was_never_measured`, never `0`), and
                    # this is the value a Lua comparison gets when the
                    # host cannot answer.  The direction it errs in is
                    # deliberate: six of the seven corpus guards are
                    # `>=`, so 0 makes them false and the player is
                    # refused a purchase rather than handed one they
                    # cannot pay for.  The seventh (`q_con3.lua:19`,
                    # `<= Quest.Var4`) errs the other way and is named
                    # here rather than left for someone to discover.
                    return STUB_DEFAULT
                return value

            return read_stat

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
                    self._sink.record_refusal(_message.REFUSE_BAD_ARITY)
                    return STUB_DEFAULT
                message_id = _coerce_int(args[0], _message.max_message_id())
                if message_id is None or not _message.is_known_message_id(message_id):
                    # An id with no row in the shipped table is a message
                    # the client could never render -- refused by name, not
                    # recorded as if it were showable.  COUNTED as well as
                    # logged: an unmined Trigger.VarN landing in one of the
                    # table's 54 id gaps is an expected recurring event
                    # (pf-adversary D12), so a run has to be able to say how
                    # many it dropped without grepping its own log.
                    _log_bad_value(self._log, "ShowMessage", message_id=args[0])
                    self._sink.record_refusal(
                        _message.REFUSE_UNKNOWN_MESSAGE_ID)
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

        if name == "TeleportCheck":
            def teleport_check(*args):
                # Player.TeleportCheck(marker_id) -- ask this player to
                # confirm travel to one MARKER row.  RE-303 (PASS) measured
                # every byte of the exchange this records an order for: the
                # client draws the window from the marker id alone, echoes
                # the same id back on OK, and sends NOTHING on Cancel.
                #
                # RECORDS the order.  Does NOT build or send the frame --
                # no module in this package does (lua_api/message.py's own
                # rule, kept rather than broken for this one name).  The
                # composer that turns this into bytes is
                # world_m2_teleport_check.encode_prompt.
                self.calls.append("Player.TeleportCheck")
                if len(args) != 1:
                    # Counted under ITS OWN name.  Borrowing the marker-id
                    # refusal here told a reader that a script had passed a
                    # bad id when it had passed the wrong NUMBER of arguments
                    # -- two different fixes in two different scripts
                    # (pf-adversary, round `ebh143`, D6).
                    _log_bad_arity(self._log, "TeleportCheck", len(args), "1")
                    self._teleport_check_sink.record_refusal(
                        _teleport_check.CHECK_REFUSED_BAD_ARITY)
                    return STUB_DEFAULT
                try:
                    # Coerced WITHOUT this door's bound, so an out-of-field id
                    # reaches the refusal that names it.  `_coerce_int` refuses
                    # anything ABOVE MARKER_ID_MAX and anything NEGATIVE by
                    # returning None, which arrived here as "not an int" and
                    # left CHECK_REFUSED_MARKER_ID_OUT_OF_FIELD unreachable for
                    # those two shapes.  It was NOT unreachable for 0: that
                    # floor was already 0, so the sentinel reached the field
                    # refusal under the wrong name, and now reaches
                    # CHECK_REFUSED_MARKER_ID_IS_ABSENT_SENTINEL
                    # (pf-adversary, round `ew9416`, D-A2).
                    pending = _teleport_check.open_check(
                        _teleport_check.coerce_wire_marker_id(args[0]))
                except _teleport_check.TeleportCheckError as exc:
                    # Refused BY NAME and counted, never a silent no-op: an
                    # unpinned marker id is the expected recurring event here
                    # (world_m2_teleport_check resolves the 13 marker rows a
                    # SCENE_NAME row names plus the 3 the owner decreed, out
                    # of the client's 390), so a run has to be able to say how
                    # many orders it dropped without grepping its own log.
                    reason = str(exc).split(" ", 1)[0]
                    _log_bad_value(self._log, "TeleportCheck",
                                   marker_id=args[0])
                    self._teleport_check_sink.record_refusal(reason)
                    return STUB_DEFAULT
                character_id = self._context.character_id
                if type(character_id) is not int or character_id <= 0:
                    # The recorded id and the CONSUMED id must be the same
                    # domain.  The dispatch branch takes an echo with the id
                    # the socket proved (`foundation.selected.id`), so an order
                    # filed under this namespace's context DEFAULT (0, from
                    # lua_api.player.DEFAULT_CONTEXT, which mirrors quest's)
                    # opens a window whose echo
                    # can never find it -- R307's "window that goes nowhere",
                    # produced by this chain itself (chief letter
                    # `20260908_0432`, D6).  A caller that wants live orders
                    # builds the host with a player_context carrying the id the
                    # CONNECTION proved; until it does, this refuses BY NAME
                    # and the tally says so, instead of filling a sink with
                    # orders nobody can consume.
                    # The NAME on the console too: nothing in src/ reads
                    # `sink.refusals` today (chief's R397 D7 measured the same
                    # thing), so a tally nobody prints is not evidence a
                    # reader can reach (pf-adversary, round `nilasm`, M2/M5).
                    _log_bad_value(self._log, "TeleportCheck",
                                   character_id=character_id,
                                   refusal=(_teleport_check
                                            .CHECK_REFUSED_NO_CHARACTER_BOUND))
                    self._teleport_check_sink.record_refusal(
                        _teleport_check.CHECK_REFUSED_NO_CHARACTER_BOUND)
                    return STUB_DEFAULT
                returned = self._teleport_check_sink.record(
                    character_id, pending)
                # A recorder that answers nothing is not a crash: see
                # world_m2_teleport_check.sink_stored_count (pf-adversary,
                # round `ew9416`, D-A5 -- the plain recorder anyone would write
                # killed this door with a TypeError AFTER recording the order).
                stored = _teleport_check.sink_stored_count(returned)
                self._log(
                    "LUA_PLAYER_REAL Player.TeleportCheck character=%d "
                    "marker_id=%d scene=%d confirm_predicted=%d stored=%s "
                    "(recorded only, no frame sent; stored=0 means the sink "
                    "refused it at a cap, stored=unknown means the sink did "
                    "not answer)"
                    % (character_id, pending.marker_id,
                       pending.destination.scene_id, pending.confirm_id,
                       "unknown" if stored is None else stored))
                if stored is not None and stored > 0:
                    # The one console line this lane's token is FOR, printed
                    # from the live door rather than from a test (pf-adversary,
                    # round `ebh143`, D9: nothing outside tests/ called it, so
                    # the token could not be fired at all).  It says
                    # ORDER_RECORDED and sent=0 because that is all that
                    # happened here -- the send half is chief's drain, and it
                    # prints prompt_sent_console_line (D-A1).  Not printed for
                    # anything but a POSITIVE count.  "Not zero" was not the
                    # same rule: a recorder that spells refusal `False` or
                    # `-1` -- the two shapes sink_stored_count's own docstring
                    # calls plausible -- printed the token for an order it had
                    # just refused, which is D9/D-A1 re-opened one line below
                    # where it was paid (pf-adversary, round `nilasm`, H1).
                    # An unknown count is not a licence either: the door
                    # cannot say a window was opened, so the LUA_PLAYER_REAL
                    # line above says stored=unknown and no proof token is
                    # printed.
                    # The sink goes WITH the line.  Recording into a recorder
                    # nobody drains is R307's window that goes nowhere all over
                    # again, and this token used to read the same either way;
                    # now it names the recorder and says `drain=unclaimed`
                    # until the code that drains it says otherwise
                    # (pf-adversary, round `nilasm`, H4).
                    self._log(_teleport_check.prompt_console_line(
                        pending, self._teleport_check_sink))
                return returned

            return teleport_check

        if name in GRANT_KINDS:
            kind = GRANT_KINDS[name]

            def add_stat(*args, _name=name, _kind=kind):
                self.calls.append("Player.%s" % _name)
                if len(args) != 1:
                    _log_bad_arity(self._log, _name, len(args), "1")
                    return STUB_DEFAULT
                amount = _coerce_int(args[0], _MAX_GRANT_AMOUNT)
                if amount is None:
                    # Includes every NEGATIVE amount: _coerce_int's floor is
                    # 0.  Neither of these two names is ever called with one
                    # in the corpus (GRANT_KINDS' own docstring), so a
                    # negative arriving here is a script this host has not
                    # seen or a Var that decoded wrong -- refused and
                    # logged, never turned into a silent charge.
                    _log_bad_value(self._log, _name, amount=args[0])
                    return STUB_DEFAULT
                _granted, _reason = _reward.grant(
                    "Player.%s" % _name, _kind,
                    self._context.character_id, amount,
                    store=self._payout_store, log=self._log)
                # THE RETURN VALUE STAYS STUB_DEFAULT EVEN ON A PAID GRANT,
                # the same rule the six Quest.Add*Criteria* names already
                # live under (tests/test_script_lua_api_reward.py::
                # test_the_stub_still_returns_the_stub_default): a payout is
                # a SIDE EFFECT, and nobody has measured what the game's own
                # engine returns from these two names.  Both corpus call
                # sites use them as statements
                # (`Player.AddExp(Player.GetLv()*Trigger.Var5);`), so no
                # script observes the difference today -- and handing back a
                # raw column balance would be this lane inventing an API
                # contract, which is the one thing its charter forbids.
                # NO FRAME GOES OUT either: a client watching its EXP bar
                # does not see this move until whatever Player.* frame
                # reports a stat change is wired, which is not this round.
                return STUB_DEFAULT

            return add_stat

        if name in SIGNED_STAT_KINDS:
            kind = SIGNED_STAT_KINDS[name]

            def add_or_charge_stat(*args, _name=name, _kind=kind):
                self.calls.append("Player.%s" % _name)
                if len(args) != 1:
                    _log_bad_arity(self._log, _name, len(args), "1")
                    return STUB_DEFAULT
                amount = _coerce_signed_int(
                    args[0], _MAX_SIGNED_STAT_MAGNITUDE)
                if amount is None:
                    # nan/inf, a fractional float, a bool, a string, or a
                    # magnitude past the ceiling -- which for THIS door
                    # includes every u32-wrapped negative in the shipped
                    # quest table (see _MAX_SIGNED_STAT_MAGNITUDE).  NOT a
                    # negative that arrives AS a negative: the whole reason
                    # this closure exists is that such a value is a real
                    # instruction from a shipped quest.
                    _log_bad_value(self._log, _name, amount=args[0])
                    return STUB_DEFAULT
                if amount > 0 and not _reward.can_charge(
                        self._payout_store, _kind):
                    # A NAME THAT CAN CHARGE MUST NOT PAY THROUGH A STORE
                    # THAT CANNOT CHARGE (pf-adversary D5, this round).
                    # Otherwise an add-only store pays this name's rewards
                    # and refuses its charges -- the free ship, arriving
                    # through the store's SHAPE instead of through the
                    # sign, which is the one outcome this whole round
                    # exists to prevent.  Refused under the spend door's
                    # own token so a census sees the cause, not a mystery.
                    self._log(
                        "LUA_PLAYER_GRANT Player.%s character=%s kind=%s "
                        "refused=%s unpaid=%r (this name can also CHARGE, "
                        "and a store that cannot charge must not be "
                        "allowed to pay only the rewards)"
                        % (_name, self._context.character_id, _kind,
                           _reward.REFUSE_STORE_CANNOT_SPEND, amount))
                    return STUB_DEFAULT
                if amount < 0:
                    # THE SIGN IS RESOLVED HERE, on the side of the seam
                    # that can cite the call site (q_ship.lua:50), and the
                    # MAGNITUDE is what crosses it.  reward.charge refuses
                    # a negative of its own accord, so a future caller that
                    # forgets this line gets a refusal, not a double
                    # negative that silently pays.
                    _reward.charge(
                        "Player.%s" % _name, _kind,
                        self._context.character_id, -amount,
                        store=self._payout_store, log=self._log)
                else:
                    # Zero goes down the granting door on purpose: it is
                    # refused as `amount_is_zero` there, one token for
                    # "nothing to move" instead of two that a census would
                    # have to add together.
                    _reward.grant(
                        "Player.%s" % _name, _kind,
                        self._context.character_id, amount,
                        store=self._payout_store, log=self._log)
                # STUB_DEFAULT EITHER WAY, INCLUDING WHEN THE PLAYER COULD
                # NOT AFFORD IT.  Same rule as the grant closure above:
                # nobody has measured what the game's own engine returns
                # from this name, and all six corpus call sites use it as a
                # statement, so no script observes the difference today.
                # This is a REAL LIMIT, not a formality: q_ship.lua charges
                # and then hands over the ship on the next lines with no
                # check, so a player who cannot afford it gets the ship
                # anyway -- the refusal is honest in the log and invisible
                # to the script.  Closing that needs Player.GetCash (still
                # stubbed, _STAT_READ) so the script's own guard works, the
                # way q_boat_health.lua:19 already guards with it.
                return STUB_DEFAULT

            return add_or_charge_stat

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
                     sink: "Optional[_message.MessageSink]" = None,
                     payout_store=None,
                     teleport_check_sink=None) -> RealPlayerNamespace:
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

    ``payout_store`` (this round, for ``AddExp``/``AddSkillPoint``) has NO
    default and no in-memory stand-in on purpose, unlike every parameter
    above it. A private in-memory reward balance would be a number that
    looks paid, survives nothing, and reaches no client -- the exact shape
    ``lua_api.reward`` refuses. Without one, both grant closures refuse
    with ``no_reward_store`` and say so in the log; with one (the process's
    real ``store.SQLiteStore``, handed down by ``script_host.ScriptHost``)
    they move an actual ``characters`` row.
    """
    return RealPlayerNamespace(
        methods, context if context is not None else DEFAULT_CONTEXT, log,
        store if store is not None else InMemoryPlayerMobAppearStore(),
        _message.check_sink(sink) if sink is not None
        else _message.InMemoryMessageSink(),
        payout_store, teleport_check_sink)
