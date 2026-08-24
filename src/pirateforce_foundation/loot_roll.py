"""LOOT-ROLL-001: the server-side loot roller (Door 2 of the round-100 loot loop).

WHY THIS MODULE EXISTS -- Door 2, and only Door 2
--------------------------------------------------
``drafts/MONSTER_SPAWN_LOOT_STATIC_AND_DESIGN_R100_20260820.md`` (round 100)
ranked the six doors a monster-loot loop needs by how proven each one is and
named exactly one that is buildable today with no wire and no guessing:

    "Door 2 -- WHAT IT DROPS (the roll).  Buildable now as pure server logic.
     [OUR DESIGN on PROVEN data] ... given a dead mob's template id, look up
     MOBS.n_DROPS_*, resolve each set, roll the per-slot rates / weighted picks
     / quality weights, and produce the exact item id list a kill would yield.
     ... The nonclaim it must carry: our roller is OUR reconstruction from
     client data; the original server's roll order and RNG are unrecoverable."

That is this module, and nothing else.  Doors 3 and 4 -- a lootable object
appearing on the ground, and a player picking it up -- have NO KNOWN WIRE PATH
(the actor-entry jump table ``0x4469BD`` accepts only actor_type 2..6 and has
no item/object type; ``DropThing*`` and ``PickupTerrainThing`` are registration
NAMES with no transport, serializer, producer or capture).  A roll result
therefore cannot reach a player today, by design and by measurement.

    AMENDED 2026-08-24: the round-100 sentence above is SUPERSEDED for
    ``PickupTerrainThing``.  Since 2026-08-23 that class has a pinned
    serializer field table (0x005E5E30, two fields: u32 tag 0x14 at
    object+0x14, u8 tag 0x08 at object+0x18 -- pinned by
    pf_bridge/external/PF_SERIALIZER_FIELDS.tsv rows 859-862, GT-040
    part C, adversarially re-derived by GT-042) and a pinned producer
    (0x006B0639, the WM_LBUTTONDOWN mouse-click path, outbound queueing
    at 0x006B0653, object+0x14 copied from the selected live runtime
    drop-object -- GT-046, letter pf_bridge/notes_to_chief/
    20260823_1435_GT046-PASS-outbound-mouseclick-runtime-drop-object.md);
    the only proven PRODUCER is client-outbound (a producer proof is not
    a proof the message never travels the other way).  Only "no capture
    frames" remains true --
    the corpus still holds zero PickupTerrainThing frames in either
    direction, and its runtime vital id stays hash-DERIVED (0x4543), never
    observed.  PICKUP-LISTENER-001 (HYP-PF-036) now carries the opt-in
    inbound decoder for that shape; monster-drop pickup may still ride the
    undecoded ``FightingDrop*`` family instead (GT-046 job 6), so a roll
    result still cannot reach a player through any proven loop today.

PROVENANCE OF EVERY CLAIM THE CODE MAKES
----------------------------------------
The single permitted data source is the committed round-100 fact pack
``FACTPACK_R100_CONSTDATA_MONSTER_LOOT.md`` section 5 ("LOOT"), derived from
``B_CONSTDATA_TH.pc_.dec`` (8,443,000 bytes, sha256 ``496DFB2E..0D2D``, client
data version 1.41.0000 built 2014-12-11).  The client image and the const-data
blob do NOT exist on this machine and are never required by this module or its
tests.

* [PROVEN] The id-encoding rule ``MOBS.n_DROPS_* = prefix * 100000 + n_ID`` of
  a row in the matching table, verified on the full data: prefix 27
  DROPS_NORMAL (62/62 low parts resolve), 28 DROPS_SPECIALLY (107/107), 54
  DROPS_EQUIPMENT (36/36), 87 DROPS_QUEST (only 311/2478 -- see the refusal).
* [PROVEN] Item ids inside the drop tables use the same scheme keyed on the
  item-category table: 22 EQUIPMENT_BASE (2200201 -> 201 verified), 24
  ITEM_CONSUMABLES (2400046 -> 46), 25 ITEM_QUEST (2500021 -> 21), 26
  ITEM_MISC (2600041 -> 41).
* [STATIC] DROPS_NORMAL (049, 267 x 121) is ``n_ID`` plus 30 slots of
  ``(n_ITEM, f_RATE, n_MIN, n_MAX)``, "per-slot independent percentage rates".
* [STATIC] DROPS_EQUIPMENT (048, 53 x 44) is ``n_ID, f_DROPS_RATE,
  n_NUMBER_MIN/MAX`` plus 20 x ``(n_ITEM, n_WEIGHT)``: "one roll at
  f_DROPS_RATE then weighted pick".
* [STATIC] DROPS_SPECIALLY (050, 584 x 64) is the same shape with 30 entries.
* [STATIC] E_DROPS_QUALITY (054, 26 x 9) is ``n_ID, n_MOB_RANK,
  n_MOB_LEVELMIN/MAX, n_WEIGHT_W/G/B/P/O`` -- equipment-drop quality
  (White/Green/Blue/Purple/Orange) by mob rank and level band.  The weights are
  NOT always normalized to 100: row 1201 (rank 4096) is G700 B299 P1, sum 1000.
* [INFERENCE] ``n_ITEM = 0`` with a nonzero rate is the MONEY slot.  The fact
  pack marks this reading [INFERENCE] and so does every money drop this module
  emits (tag ``INFERENCE_MONEY_SLOT``).
* [NEGATIVE] DROPS_QUEST is refused by name, never implemented: 2478 distinct
  DROPS_QUEST sets are referenced by mobs and only 311 exist client-side, so
  ~87 pct of that model is absent and a DROPS_QUEST roll here would be
  invention.
* [OUR DESIGN] Everything else below -- the ROLL ORDER, the exact comparison
  used for a percentage rate, the mapping from a uniform draw to a quantity,
  the cumulative-threshold weighted walk, with-replacement multi-picks, and the
  decision to attach quality only to DROPS_EQUIPMENT items -- is OURS.  The
  original server's roll order and RNG are unrecoverable forever.

WHAT THIS MODULE IS NOT
-----------------------
PURE SERVER LOGIC.  It sends nothing on the wire, opens no socket, touches no
database, boots no server, imports nothing from the runtime/dispatch layer, and
has NO SCENARIO FLAG.  It is deliberately NOT reachable from production
dispatch at all: no module in ``src/`` imports it, ``production_allowed`` is
False, and ``LOOT_ROLL_DISPATCH_REACHABLE`` is False.  That is the honest state
of Door 2 -- the roll is computable, the delivery is not.  Importing this module
has no side effects: it reads no file and touches no global state at import
time, and it never uses the module-global ``random`` functions (the caller
injects a ``random.Random``; see DETERMINISM).

DETERMINISM (the point of this checkpoint)
------------------------------------------
Every stochastic decision is a draw from an INJECTED ``random.Random``
instance, taken through ``rng.random()`` and nothing else -- no
``random.choices``, no ``randrange``, no module-global ``random``.  Same tables
+ same mob + same seed produce byte-identical results in any process, and the
draw stream does not depend on whether a row decodes: a slot that wins its rate
roll consumes its quantity draw even when its item id is then refused.  The
three primitives are deliberately small and separately testable:

* ``rate_succeeds(rate, draw)`` is ``draw < rate / 100.0``.  0 pct never drops
  (no draw is < 0.0); 100 pct always drops (every draw is < 1.0); a fractional
  0.5 pct has the exact threshold 0.005 and the entry at the threshold FAILS.
* ``uniform_quantity(low, high, draw)`` is ``low + int(draw * (high - low + 1))``
  clamped to ``high`` -- a flat integer span, min at draw 0.0, max just below 1.
* ``weighted_pick(weights, draw)`` is an explicit cumulative-threshold walk in
  TABLE ORDER: the first index whose running sum EXCEEDS ``draw * total``.  A
  zero-weight entry can never be picked, and the boundary at which each entry
  starts is exactly its predecessor's cumulative sum, so a test can enumerate
  every boundary by hand.

FAIL CLOSED, AND NEVER SILENTLY
-------------------------------
Decoding is TOTAL: it returns a decision object, never raises.  A wrong prefix
for the table being addressed, a value of 0, or a low part that is absent from
the loaded table is a NAMED refusal in :data:`LOOT_ROLL_REFUSAL_REASONS` -- not
a silent skip, not a bare ``KeyError``.  Every refusal that happens during a
roll is carried in ``LootRollResult.refusals`` with the reason, the table it
was addressing, and a human-readable detail; every rate roll that fails is
carried in ``LootRollResult.misses``; padding slots (item 0, rate 0, min 0,
max 0 -- the unused columns of a fixed-width 30-slot row) are counted in
``LootRollResult.padding_slots``.  Nothing that a roll decided is invisible.

NONCLAIMS
---------
* This roller is OUR reconstruction from client-shipped data.  No original
  server behaviour is claimed anywhere.  The original roll order and RNG are
  unrecoverable forever, and two servers using these same tables with different
  orders would both be consistent with the evidence.
* Nothing here has ever touched a wire, a client, or a database.  No coverage
  grade moves; ``monster_spawn_and_loot`` stays ``not_started``.
* The fixture this module reads in tests is a small documented EXCERPT of the
  shipped tables (a handful of published rows plus rows we composed for tests),
  not the tables themselves.
* DROPS_QUEST is refused, not deferred-with-a-stub: there is no partial
  DROPS_QUEST implementation here to mistake for one.
* Whether the original game rolled loot client-side or server-side is
  [UNKNOWN] and undecidable from data alone.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import random
from types import MappingProxyType
from typing import Any, Mapping, Sequence


# This lane is not wired to anything and must not become wired by accident.
production_allowed = False
LOOT_ROLL_MILESTONE = "LOOT-ROLL-001"
LOOT_ROLL_DISPATCH_REACHABLE = False

# ---------------------------------------------------------------------------
# [PROVEN] the id-encoding rule, fact pack section 5.
# ---------------------------------------------------------------------------
ID_PREFIX_SCALE = 100000

TABLE_DROPS_NORMAL = "DROPS_NORMAL"
TABLE_DROPS_SPECIALLY = "DROPS_SPECIALLY"
TABLE_DROPS_EQUIPMENT = "DROPS_EQUIPMENT"
TABLE_DROPS_QUEST = "DROPS_QUEST"

DROP_SET_PREFIXES: Mapping[str, int] = MappingProxyType({
    TABLE_DROPS_NORMAL: 27,
    TABLE_DROPS_SPECIALLY: 28,
    TABLE_DROPS_EQUIPMENT: 54,
    TABLE_DROPS_QUEST: 87,
})

ITEM_TABLE_EQUIPMENT_BASE = "EQUIPMENT_BASE"
ITEM_TABLE_CONSUMABLES = "ITEM_CONSUMABLES"
ITEM_TABLE_QUEST = "ITEM_QUEST"
ITEM_TABLE_MISC = "ITEM_MISC"

ITEM_TABLE_PREFIXES: Mapping[int, str] = MappingProxyType({
    22: ITEM_TABLE_EQUIPMENT_BASE,
    24: ITEM_TABLE_CONSUMABLES,
    25: ITEM_TABLE_QUEST,
    26: ITEM_TABLE_MISC,
})

# ---------------------------------------------------------------------------
# [STATIC] E_DROPS_QUALITY column order.  The five weight columns in the order
# the fact pack prints them, which is also the order the cumulative walk uses.
# ---------------------------------------------------------------------------
QUALITY_WHITE = "WHITE"
QUALITY_GREEN = "GREEN"
QUALITY_BLUE = "BLUE"
QUALITY_PURPLE = "PURPLE"
QUALITY_ORANGE = "ORANGE"
QUALITY_NAMES: tuple[str, ...] = (
    QUALITY_WHITE, QUALITY_GREEN, QUALITY_BLUE, QUALITY_PURPLE, QUALITY_ORANGE,
)
QUALITY_WEIGHT_COLUMNS: tuple[str, ...] = (
    "n_WEIGHT_W", "n_WEIGHT_G", "n_WEIGHT_B", "n_WEIGHT_P", "n_WEIGHT_O",
)

# ---------------------------------------------------------------------------
# Every refusal this module can produce, by name.  Nothing is ever dropped
# silently; a caller can switch on these strings.
# ---------------------------------------------------------------------------
REFUSAL_ID_ZERO = "loot_roll_refused_drop_set_id_zero"
REFUSAL_ID_NOT_A_POSITIVE_INT = "loot_roll_refused_id_not_a_positive_int"
REFUSAL_WRONG_TABLE_PREFIX = "loot_roll_refused_wrong_table_prefix"
REFUSAL_ROW_ABSENT = "loot_roll_refused_row_absent_from_the_loaded_table"
REFUSAL_UNKNOWN_ITEM_PREFIX = "loot_roll_refused_unknown_item_category_prefix"
REFUSAL_QUEST_NOT_IMPLEMENTED = "loot_roll_refused_quest_drops_not_implemented"
REFUSAL_NO_QUALITY_ROW = "loot_roll_refused_no_quality_row_for_rank_and_level"
REFUSAL_WEIGHT_TOTAL_NOT_POSITIVE = (
    "loot_roll_refused_weight_total_not_positive"
)
REFUSAL_RATE_OUT_OF_RANGE = "loot_roll_refused_rate_outside_0_to_100_percent"
REFUSAL_QUANTITY_RANGE_INVERTED = "loot_roll_refused_quantity_range_inverted"

LOOT_ROLL_REFUSAL_REASONS: tuple[str, ...] = (
    REFUSAL_ID_ZERO,
    REFUSAL_ID_NOT_A_POSITIVE_INT,
    REFUSAL_WRONG_TABLE_PREFIX,
    REFUSAL_ROW_ABSENT,
    REFUSAL_UNKNOWN_ITEM_PREFIX,
    REFUSAL_QUEST_NOT_IMPLEMENTED,
    REFUSAL_NO_QUALITY_ROW,
    REFUSAL_WEIGHT_TOTAL_NOT_POSITIVE,
    REFUSAL_RATE_OUT_OF_RANGE,
    REFUSAL_QUANTITY_RANGE_INVERTED,
)

# Readings the fact pack marks [INFERENCE], carried on the result so a caller
# can never mistake one for a proven fact.
INFERENCE_MONEY_SLOT = "inference_money_slot_is_item_id_zero_with_a_nonzero_rate"
INFERENCE_QUALITY_BAND_UNPUBLISHED = (
    "inference_quality_row_level_band_not_published_treated_as_unbounded"
)

# The places where the fact pack was silent and we had to choose a reading.
# Each of these is OUR DESIGN and is stated as such in the report.
LOOT_ROLL_CHOSEN_READINGS: tuple[str, ...] = (
    "roll_order_is_normal_then_equipment_then_specially_then_quest_refusal",
    "a_percentage_rate_succeeds_when_the_draw_is_strictly_below_rate_over_100",
    "a_quantity_is_a_flat_integer_span_low_plus_int_draw_times_span",
    "a_weighted_pick_is_a_cumulative_walk_in_table_order_first_sum_above_target",
    "multi_item_weighted_picks_are_independent_and_may_repeat_an_entry",
    "quality_is_attached_only_to_drops_equipment_items_not_to_specially_items",
    "an_e_drops_quality_row_matches_a_mob_rank_by_exact_equality_not_by_bitmask",
    "an_unpublished_quality_level_band_is_treated_as_unbounded_and_tagged",
    "the_effective_mob_level_is_supplied_by_the_caller_defaulting_to_level_min",
)


class LootTableError(ValueError):
    """A fixture this module refuses to load.  Load-time only, never a roll."""


# ---------------------------------------------------------------------------
# Decoding.  Total: returns a decision, never raises, never a bare KeyError.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class IdDecode:
    """The result of applying the prefix rule to one id.  Always answers."""

    ok: bool
    raw: int
    table: str
    prefix: int
    low: int
    reason: str
    detail: str


def _decode_failure(raw: Any, table: str, reason: str, detail: str) -> IdDecode:
    return IdDecode(
        False, raw if type(raw) is int else -1, table, -1, -1, reason, detail,
    )


def split_prefixed_id(raw: int) -> tuple[int, int]:
    """The rule itself: ``prefix, low = divmod(raw, 100000)``.

    [PROVEN] fact pack section 5, "value = prefix*100000 + target-table n_ID".
    """
    return divmod(raw, ID_PREFIX_SCALE)


def decode_drop_set_id(
    raw: Any,
    table: str,
    tables: Any = None,
) -> IdDecode:
    """Decode a ``MOBS.n_DROPS_*`` value against the table it addresses.

    Fails closed and by name on: a non-positive-int value, a value of 0 (the
    commonest shipped value -- it means "this mob declares no such set", and it
    is reported, never silently skipped), a prefix that belongs to a different
    DROPS_* table, and -- when ``tables`` is supplied -- a low part that is
    absent from the loaded rows.
    """
    if table not in DROP_SET_PREFIXES:
        return _decode_failure(
            raw, str(table), REFUSAL_WRONG_TABLE_PREFIX,
            "%r is not one of the four DROPS_* tables" % (table,),
        )
    expected_prefix = DROP_SET_PREFIXES[table]
    if type(raw) is not int:
        return _decode_failure(
            raw, table, REFUSAL_ID_NOT_A_POSITIVE_INT,
            "a drop-set id must be an int, got %r" % (type(raw).__name__,),
        )
    if raw == 0:
        return _decode_failure(
            raw, table, REFUSAL_ID_ZERO,
            "the mob declares no %s set (n_DROPS_* == 0)" % (table,),
        )
    if raw < 0:
        return _decode_failure(
            raw, table, REFUSAL_ID_NOT_A_POSITIVE_INT,
            "a drop-set id must be positive, got %d" % (raw,),
        )
    prefix, low = split_prefixed_id(raw)
    if prefix != expected_prefix:
        return _decode_failure(
            raw, table, REFUSAL_WRONG_TABLE_PREFIX,
            "id %d carries prefix %d but %s is addressed by prefix %d"
            % (raw, prefix, table, expected_prefix),
        )
    if low == 0:
        return _decode_failure(
            raw, table, REFUSAL_ID_ZERO,
            "id %d decodes to row 0, which is not a row id" % (raw,),
        )
    if tables is not None:
        rows = _rows_for_table(tables, table)
        if rows is None:
            return _decode_failure(
                raw, table, REFUSAL_QUEST_NOT_IMPLEMENTED,
                "%s is refused by name and carries no loaded rows" % (table,),
            )
        if low not in rows:
            return _decode_failure(
                raw, table, REFUSAL_ROW_ABSENT,
                "id %d decodes to %s row %d, which is not in the loaded "
                "excerpt" % (raw, table, low),
            )
    return IdDecode(True, raw, table, prefix, low, "", "")


def decode_item_id(raw: Any) -> IdDecode:
    """Decode an ``n_ITEM`` value into (item-category table, low id).

    [PROVEN] the item tables use the same prefix scheme: 22 EQUIPMENT_BASE,
    24 ITEM_CONSUMABLES, 25 ITEM_QUEST, 26 ITEM_MISC.  Item id 0 is NOT an
    item: in DROPS_NORMAL it is the money slot [INFERENCE], and that reading is
    made by the caller, so a 0 reaching here is a refusal.
    """
    if type(raw) is not int:
        return _decode_failure(
            raw, "ITEM", REFUSAL_ID_NOT_A_POSITIVE_INT,
            "an item id must be an int, got %r" % (type(raw).__name__,),
        )
    if raw == 0:
        return _decode_failure(
            raw, "ITEM", REFUSAL_ID_ZERO,
            "item id 0 is the money slot reading, not an item",
        )
    if raw < 0:
        return _decode_failure(
            raw, "ITEM", REFUSAL_ID_NOT_A_POSITIVE_INT,
            "an item id must be positive, got %d" % (raw,),
        )
    prefix, low = split_prefixed_id(raw)
    if prefix not in ITEM_TABLE_PREFIXES:
        return _decode_failure(
            raw, "ITEM", REFUSAL_UNKNOWN_ITEM_PREFIX,
            "item id %d carries prefix %d, which is not one of the four "
            "item-category prefixes 22/24/25/26" % (raw, prefix),
        )
    if low == 0:
        return _decode_failure(
            raw, "ITEM", REFUSAL_ID_ZERO,
            "item id %d decodes to row 0, which is not a row id" % (raw,),
        )
    return IdDecode(True, raw, ITEM_TABLE_PREFIXES[prefix], prefix, low, "", "")


# ---------------------------------------------------------------------------
# The three primitives.  [OUR DESIGN] -- small on purpose, so each boundary can
# be enumerated by a test rather than argued about.
# ---------------------------------------------------------------------------
def rate_succeeds(rate_percent: float, draw: float) -> bool:
    """``draw < rate / 100``: 0 pct never fires, 100 pct always fires.

    The draw is a ``rng.random()`` value in [0.0, 1.0).  The comparison is
    strict, so the entry EXACTLY AT the threshold fails -- for a 0.5 pct rate
    the threshold is 0.005 and a draw of 0.005 does not drop.
    """
    return float(draw) < float(rate_percent) / 100.0


def uniform_quantity(low: int, high: int, draw: float) -> int:
    """A flat integer span: ``low + int(draw * (high - low + 1))``, clamped.

    Draw 0.0 gives ``low``; a draw just below 1.0 gives ``high``; the clamp
    exists only so a float edge can never return ``high + 1``.
    """
    span = high - low + 1
    if span <= 0:
        raise ValueError("quantity range is inverted: %d..%d" % (low, high))
    value = low + int(float(draw) * span)
    if value < low:
        return low
    if value > high:
        return high
    return value


def weighted_pick(weights: Sequence[int], draw: float) -> int | None:
    """Cumulative-threshold walk in TABLE ORDER; ``None`` if no positive total.

    The target is ``draw * total``; the chosen index is the FIRST whose running
    sum strictly EXCEEDS the target.  Entry ``i`` therefore owns the half-open
    interval ``[sum(weights[:i]), sum(weights[:i+1]))`` of the target line, a
    zero-weight entry owns an empty interval and can never be picked, and the
    walk never consults ``random.choices`` or any other library internal.
    Weights are normalized by the ACTUAL sum, which matters: E_DROPS_QUALITY
    row 1201 sums to 1000, not 100.
    """
    total = 0
    for weight in weights:
        total += int(weight)
    if total <= 0:
        return None
    target = float(draw) * total
    cumulative = 0
    for index, weight in enumerate(weights):
        cumulative += int(weight)
        if cumulative > target:
            return index
    # Unreachable for a draw in [0, 1): the final cumulative IS the total and
    # target < total.  Kept as a fail-closed floor rather than an assert.
    return len(weights) - 1


# ---------------------------------------------------------------------------
# The loaded tables.  Read-only: every mapping is a MappingProxyType and every
# row is a frozen dataclass, so a roll cannot mutate its own inputs.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class NormalSlot:
    slot_index: int
    item_id: int
    rate_percent: float
    minimum: int
    maximum: int

    @property
    def is_padding(self) -> bool:
        """An unused column of the fixed-width 30-slot row, not a decision."""
        return (
            self.item_id == 0
            and self.rate_percent == 0.0
            and self.minimum == 0
            and self.maximum == 0
        )

    @property
    def is_money(self) -> bool:
        """[INFERENCE] item 0 with a nonzero rate is the money slot."""
        return self.item_id == 0 and self.rate_percent > 0.0


@dataclass(frozen=True)
class NormalRow:
    row_id: int
    source: str
    slots: tuple[NormalSlot, ...]


@dataclass(frozen=True)
class WeightedEntry:
    entry_index: int
    item_id: int
    weight: int


@dataclass(frozen=True)
class WeightedRow:
    row_id: int
    source: str
    rate_percent: float
    number_min: int
    number_max: int
    entries: tuple[WeightedEntry, ...]


@dataclass(frozen=True)
class QualityRow:
    row_id: int
    source: str
    mob_rank: int
    level_min: int | None
    level_max: int | None
    band_published: bool
    weights: tuple[int, ...]

    def contains_level(self, level: int) -> bool:
        if not self.band_published:
            # [INFERENCE] the fact pack prints no band for eight rows; we treat
            # those as unbounded and TAG every drop that used one.
            return True
        return int(self.level_min) <= level <= int(self.level_max)


@dataclass(frozen=True)
class MobLootProfile:
    """The MOBS columns Door 2 needs, plus the effective level.

    [OUR DESIGN] the shipped row carries a level BAND (n_LEVEL_MIN..MAX); which
    level a particular spawned mob has is Door 1b (spawn), which does not exist,
    so the caller supplies it and the loader defaults it to ``n_LEVEL_MIN``.
    """

    mob_id: int
    source: str
    rank: int
    level: int
    level_min: int
    level_max: int
    drops_normal: int
    drops_equipment: int
    drops_specially: int
    drops_quest: int


@dataclass(frozen=True)
class LootTables:
    provenance: Mapping[str, Any]
    normal: Mapping[int, NormalRow]
    equipment: Mapping[int, WeightedRow]
    specially: Mapping[int, WeightedRow]
    quality: tuple[QualityRow, ...]
    mobs: Mapping[int, MobLootProfile]


def _rows_for_table(tables: Any, table: str) -> Mapping[int, Any] | None:
    if type(tables) is not LootTables:
        return None
    if table == TABLE_DROPS_NORMAL:
        return tables.normal
    if table == TABLE_DROPS_EQUIPMENT:
        return tables.equipment
    if table == TABLE_DROPS_SPECIALLY:
        return tables.specially
    return None


# ---------------------------------------------------------------------------
# The loader.  Strict: a malformed excerpt is refused at load time so a roll
# never has to reason about impossible data.
# ---------------------------------------------------------------------------
_ROW_SOURCES = ("factpack_r100_section_5", "composed_for_test")


def _require_int(row: Mapping[str, Any], key: str, where: str) -> int:
    if key not in row:
        raise LootTableError("%s is missing %s" % (where, key))
    value = row[key]
    if type(value) is not int:
        raise LootTableError("%s.%s must be an int, got %r" % (where, key, value))
    return value


def _require_rate(row: Mapping[str, Any], key: str, where: str) -> float:
    if key not in row:
        raise LootTableError("%s is missing %s" % (where, key))
    value = row[key]
    if type(value) not in (int, float):
        raise LootTableError("%s.%s must be a number" % (where, key))
    rate = float(value)
    if not 0.0 <= rate <= 100.0:
        raise LootTableError(
            "%s.%s is %r, outside 0..100 percent" % (where, key, rate)
        )
    return rate


def _require_source(row: Mapping[str, Any], where: str) -> str:
    source = row.get("source")
    if source not in _ROW_SOURCES:
        raise LootTableError(
            "%s must declare source as one of %r, got %r"
            % (where, _ROW_SOURCES, source)
        )
    return str(source)


def load_loot_tables(path: str | Path) -> LootTables:
    """Load the documented excerpt.  Called explicitly; never at import time."""
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LootTableError("unreadable loot table excerpt: %s" % (path,)) from exc
    return build_loot_tables(document)


def build_loot_tables(document: Any) -> LootTables:
    if type(document) is not dict:
        raise LootTableError("the excerpt must be a JSON object")
    if document.get("schema") != 1:
        raise LootTableError("unknown loot table excerpt schema")
    provenance = document.get("provenance")
    if type(provenance) is not dict or "factpack" not in provenance:
        raise LootTableError(
            "the excerpt must carry a provenance block naming the fact pack"
        )
    tables = document.get("tables")
    if type(tables) is not dict:
        raise LootTableError("the excerpt must carry a tables object")
    for key in (TABLE_DROPS_NORMAL, TABLE_DROPS_EQUIPMENT,
                TABLE_DROPS_SPECIALLY, "E_DROPS_QUALITY", "MOBS"):
        if type(tables.get(key)) is not list:
            raise LootTableError("the excerpt is missing table %s" % (key,))
    if TABLE_DROPS_QUEST in tables:
        raise LootTableError(
            "DROPS_QUEST is refused by name and must not be carried"
        )

    normal: dict[int, NormalRow] = {}
    for row in tables[TABLE_DROPS_NORMAL]:
        where = "DROPS_NORMAL row"
        row_id = _require_int(row, "n_ID", where)
        where = "DROPS_NORMAL row %d" % row_id
        slots: list[NormalSlot] = []
        raw_slots = row.get("slots")
        if type(raw_slots) is not list or not raw_slots:
            raise LootTableError("%s carries no slots" % where)
        for index, slot in enumerate(raw_slots):
            place = "%s slot %d" % (where, index)
            minimum = _require_int(slot, "n_MIN", place)
            maximum = _require_int(slot, "n_MAX", place)
            if maximum < minimum:
                raise LootTableError(
                    "%s has an inverted quantity range %d..%d"
                    % (place, minimum, maximum)
                )
            slots.append(NormalSlot(
                index,
                _require_int(slot, "n_ITEM", place),
                _require_rate(slot, "f_RATE", place),
                minimum,
                maximum,
            ))
        if row_id in normal:
            raise LootTableError("%s is duplicated" % where)
        normal[row_id] = NormalRow(
            row_id, _require_source(row, where), tuple(slots),
        )

    def weighted(table_key: str) -> dict[int, WeightedRow]:
        out: dict[int, WeightedRow] = {}
        for row in tables[table_key]:
            row_id = _require_int(row, "n_ID", table_key + " row")
            where = "%s row %d" % (table_key, row_id)
            number_min = _require_int(row, "n_NUMBER_MIN", where)
            number_max = _require_int(row, "n_NUMBER_MAX", where)
            if number_min < 0 or number_max < number_min:
                raise LootTableError(
                    "%s has an inverted item-count range %d..%d"
                    % (where, number_min, number_max)
                )
            raw_entries = row.get("entries")
            if type(raw_entries) is not list or not raw_entries:
                raise LootTableError("%s carries no entries" % where)
            entries: list[WeightedEntry] = []
            for index, entry in enumerate(raw_entries):
                place = "%s entry %d" % (where, index)
                weight = _require_int(entry, "n_WEIGHT", place)
                if weight < 0:
                    raise LootTableError("%s has a negative weight" % place)
                entries.append(WeightedEntry(
                    index, _require_int(entry, "n_ITEM", place), weight,
                ))
            if row_id in out:
                raise LootTableError("%s is duplicated" % where)
            out[row_id] = WeightedRow(
                row_id, _require_source(row, where),
                _require_rate(row, "f_DROPS_RATE", where),
                number_min, number_max, tuple(entries),
            )
        return out

    equipment = weighted(TABLE_DROPS_EQUIPMENT)
    specially = weighted(TABLE_DROPS_SPECIALLY)

    quality: list[QualityRow] = []
    seen_quality: set[int] = set()
    for row in tables["E_DROPS_QUALITY"]:
        row_id = _require_int(row, "n_ID", "E_DROPS_QUALITY row")
        where = "E_DROPS_QUALITY row %d" % row_id
        if row_id in seen_quality:
            raise LootTableError("%s is duplicated" % where)
        seen_quality.add(row_id)
        band_published = row.get("band_published")
        if type(band_published) is not bool:
            raise LootTableError("%s must declare band_published" % where)
        level_min = row.get("n_MOB_LEVELMIN")
        level_max = row.get("n_MOB_LEVELMAX")
        if band_published:
            if type(level_min) is not int or type(level_max) is not int:
                raise LootTableError("%s claims a band but carries none" % where)
            if level_max < level_min:
                raise LootTableError("%s has an inverted level band" % where)
        elif level_min is not None or level_max is not None:
            raise LootTableError(
                "%s says the band is unpublished but carries one" % where
            )
        weights = tuple(
            _require_int(row, column, where) for column in QUALITY_WEIGHT_COLUMNS
        )
        if any(weight < 0 for weight in weights):
            raise LootTableError("%s has a negative weight" % where)
        quality.append(QualityRow(
            row_id, _require_source(row, where),
            _require_int(row, "n_MOB_RANK", where),
            level_min, level_max, band_published, weights,
        ))
    quality.sort(key=lambda entry: entry.row_id)

    mobs: dict[int, MobLootProfile] = {}
    for row in tables["MOBS"]:
        mob_id = _require_int(row, "n_ID", "MOBS row")
        where = "MOBS row %d" % mob_id
        level_min = _require_int(row, "n_LEVEL_MIN", where)
        level_max = _require_int(row, "n_LEVEL_MAX", where)
        if level_max < level_min:
            raise LootTableError("%s has an inverted level band" % where)
        if mob_id in mobs:
            raise LootTableError("%s is duplicated" % where)
        mobs[mob_id] = MobLootProfile(
            mob_id, _require_source(row, where),
            _require_int(row, "n_RANK", where),
            level_min, level_min, level_max,
            _require_int(row, "n_DROPS_NORMAL", where),
            _require_int(row, "n_DROPS_EQUIPMENT", where),
            _require_int(row, "n_DROPS_SPECIALLY", where),
            _require_int(row, "n_DROPS_QUEST", where),
        )

    return LootTables(
        MappingProxyType(dict(provenance)),
        MappingProxyType(normal),
        MappingProxyType(equipment),
        MappingProxyType(specially),
        tuple(quality),
        MappingProxyType(mobs),
    )


def mob_at_level(mob: MobLootProfile, level: int) -> MobLootProfile:
    """Same mob, different effective level (Door 1b picks the level, not us)."""
    if type(level) is not int:
        raise ValueError("an effective mob level must be an int")
    return MobLootProfile(
        mob.mob_id, mob.source, mob.rank, level, mob.level_min, mob.level_max,
        mob.drops_normal, mob.drops_equipment, mob.drops_specially,
        mob.drops_quest,
    )


# ---------------------------------------------------------------------------
# The result.  Drops, misses, refusals, padding -- every decision visible.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LootDrop:
    source_table: str
    slot_index: int
    item_id: int | None
    item_table: str | None
    item_low_id: int | None
    quantity: int
    is_money: bool
    quality: str | None
    inference_tags: tuple[str, ...]


@dataclass(frozen=True)
class LootMiss:
    source_table: str
    slot_index: int
    rate_percent: float
    detail: str


@dataclass(frozen=True)
class LootRefusal:
    source_table: str
    reason: str
    detail: str


@dataclass(frozen=True)
class LootRollResult:
    mob_id: int
    level: int
    rank: int
    drops: tuple[LootDrop, ...]
    misses: tuple[LootMiss, ...]
    refusals: tuple[LootRefusal, ...]
    padding_slots: int

    def refusal_reasons(self) -> tuple[str, ...]:
        return tuple(refusal.reason for refusal in self.refusals)


# The roll order.  [OUR DESIGN] -- the original order is unrecoverable; this one
# is fixed, documented, and the determinism pins depend on it.
LOOT_ROLL_ORDER: tuple[str, ...] = (
    TABLE_DROPS_NORMAL,
    TABLE_DROPS_EQUIPMENT,
    TABLE_DROPS_SPECIALLY,
    TABLE_DROPS_QUEST,
)


def _require_rng(rng: Any) -> random.Random:
    if not isinstance(rng, random.Random):
        raise ValueError(
            "loot_roll requires an injected random.Random instance: this "
            "module never uses the module-global random"
        )
    return rng


def select_quality(
    tables: LootTables,
    rank: int,
    level: int,
    draw: float,
) -> tuple[str | None, LootRefusal | None, bool]:
    """Pick a quality by weight from the E_DROPS_QUALITY row for rank + level.

    [OUR DESIGN] the row is matched by EXACT rank equality (the shipped rows
    enumerate single rank values; only DROPS_ACTIVITY.n_MOBRANK is documented
    as a bitmask) and by the level band containing ``level``.  Rows are scanned
    in ascending ``n_ID``; the shipped bands do not overlap.  The weights are
    normalized by their ACTUAL sum -- row 1201 sums to 1000.
    """
    matches = [
        row for row in tables.quality
        if row.mob_rank == rank and row.contains_level(level)
    ]
    if not matches:
        return None, LootRefusal(
            "E_DROPS_QUALITY", REFUSAL_NO_QUALITY_ROW,
            "no quality row matches rank %d at level %d" % (rank, level),
        ), False
    row = matches[0]
    index = weighted_pick(row.weights, draw)
    if index is None:
        return None, LootRefusal(
            "E_DROPS_QUALITY", REFUSAL_WEIGHT_TOTAL_NOT_POSITIVE,
            "quality row %d has no positive weight total" % row.row_id,
        ), not row.band_published
    return QUALITY_NAMES[index], None, not row.band_published


def _roll_normal(
    tables: LootTables,
    mob: MobLootProfile,
    rng: random.Random,
    drops: list[LootDrop],
    misses: list[LootMiss],
    refusals: list[LootRefusal],
) -> int:
    padding = 0
    decoded = decode_drop_set_id(mob.drops_normal, TABLE_DROPS_NORMAL, tables)
    if not decoded.ok:
        refusals.append(LootRefusal(
            TABLE_DROPS_NORMAL, decoded.reason, decoded.detail,
        ))
        return padding
    row = tables.normal[decoded.low]
    for slot in row.slots:
        if slot.is_padding:
            padding += 1
            continue
        if not 0.0 <= slot.rate_percent <= 100.0:
            refusals.append(LootRefusal(
                TABLE_DROPS_NORMAL, REFUSAL_RATE_OUT_OF_RANGE,
                "row %d slot %d rate %r is outside 0..100"
                % (row.row_id, slot.slot_index, slot.rate_percent),
            ))
            continue
        if slot.maximum < slot.minimum:
            refusals.append(LootRefusal(
                TABLE_DROPS_NORMAL, REFUSAL_QUANTITY_RANGE_INVERTED,
                "row %d slot %d range %d..%d"
                % (row.row_id, slot.slot_index, slot.minimum, slot.maximum),
            ))
            continue
        if not rate_succeeds(slot.rate_percent, rng.random()):
            misses.append(LootMiss(
                TABLE_DROPS_NORMAL, slot.slot_index, slot.rate_percent,
                "the per-slot independent percentage roll did not fire",
            ))
            continue
        # The quantity draw is taken BEFORE the item id is judged, so the draw
        # stream never depends on whether the row decodes.
        quantity = uniform_quantity(slot.minimum, slot.maximum, rng.random())
        if slot.is_money:
            drops.append(LootDrop(
                TABLE_DROPS_NORMAL, slot.slot_index, None, None, None,
                quantity, True, None, (INFERENCE_MONEY_SLOT,),
            ))
            continue
        item = decode_item_id(slot.item_id)
        if not item.ok:
            refusals.append(LootRefusal(
                TABLE_DROPS_NORMAL, item.reason, item.detail,
            ))
            continue
        drops.append(LootDrop(
            TABLE_DROPS_NORMAL, slot.slot_index, item.raw, item.table,
            item.low, quantity, False, None, (),
        ))
    return padding


def _roll_weighted_set(
    tables: LootTables,
    mob: MobLootProfile,
    rng: random.Random,
    table: str,
    rows: Mapping[int, WeightedRow],
    raw_id: int,
    with_quality: bool,
    drops: list[LootDrop],
    misses: list[LootMiss],
    refusals: list[LootRefusal],
) -> None:
    decoded = decode_drop_set_id(raw_id, table, tables)
    if not decoded.ok:
        refusals.append(LootRefusal(table, decoded.reason, decoded.detail))
        return
    row = rows[decoded.low]
    if not rate_succeeds(row.rate_percent, rng.random()):
        misses.append(LootMiss(
            table, -1, row.rate_percent,
            "the single f_DROPS_RATE gate roll did not fire",
        ))
        return
    count = uniform_quantity(row.number_min, row.number_max, rng.random())
    weights = [entry.weight for entry in row.entries]
    for pick_index in range(count):
        chosen = weighted_pick(weights, rng.random())
        if chosen is None:
            refusals.append(LootRefusal(
                table, REFUSAL_WEIGHT_TOTAL_NOT_POSITIVE,
                "row %d has no positive weight total, so no entry can be "
                "picked" % row.row_id,
            ))
            continue
        entry = row.entries[chosen]
        quality: str | None = None
        tags: list[str] = []
        if with_quality:
            # Drawn unconditionally so the stream does not depend on the item.
            quality, quality_refusal, unpublished_band = select_quality(
                tables, mob.rank, mob.level, rng.random(),
            )
            if quality_refusal is not None:
                refusals.append(quality_refusal)
            if unpublished_band:
                tags.append(INFERENCE_QUALITY_BAND_UNPUBLISHED)
        item = decode_item_id(entry.item_id)
        if not item.ok:
            refusals.append(LootRefusal(table, item.reason, item.detail))
            continue
        drops.append(LootDrop(
            table, pick_index, item.raw, item.table, item.low, 1, False,
            quality, tuple(tags),
        ))


def _roll_quest(
    mob: MobLootProfile,
    refusals: list[LootRefusal],
) -> None:
    """DROPS_QUEST is refused BY NAME.  It is not implemented and will not be.

    [NEGATIVE] mobs reference 2478 distinct DROPS_QUEST sets and only 311 exist
    client-side (fact pack section 5), so ~87 pct of that model is absent and a
    DROPS_QUEST roll would be invention, not reconstruction.
    """
    if mob.drops_quest == 0:
        refusals.append(LootRefusal(
            TABLE_DROPS_QUEST, REFUSAL_ID_ZERO,
            "the mob declares no DROPS_QUEST set (n_DROPS_QUEST == 0)",
        ))
        return
    decoded = decode_drop_set_id(mob.drops_quest, TABLE_DROPS_QUEST)
    detail = (
        "DROPS_QUEST is refused by name: only 311 of 2478 referenced sets "
        "exist client-side, so rolling one would be invention"
    )
    if not decoded.ok:
        detail = "%s (and the id itself refuses: %s)" % (detail, decoded.reason)
    refusals.append(LootRefusal(
        TABLE_DROPS_QUEST, REFUSAL_QUEST_NOT_IMPLEMENTED, detail,
    ))


def roll_mob_loot(
    tables: Any,
    mob: Any,
    rng: Any,
) -> LootRollResult:
    """Roll every drop set a mob declares, in the pinned order.

    Pure computation: no wire, no socket, no database, no clock.  ``rng`` must
    be an injected ``random.Random``; the module-global ``random`` is never
    touched.  Same tables + same mob + same seed give byte-identical results in
    any process.
    """
    if type(tables) is not LootTables:
        raise ValueError("loot tables must be a loaded LootTables object")
    if type(mob) is not MobLootProfile:
        raise ValueError("the mob must be a MobLootProfile")
    _require_rng(rng)
    drops: list[LootDrop] = []
    misses: list[LootMiss] = []
    refusals: list[LootRefusal] = []
    padding = _roll_normal(tables, mob, rng, drops, misses, refusals)
    _roll_weighted_set(
        tables, mob, rng, TABLE_DROPS_EQUIPMENT, tables.equipment,
        mob.drops_equipment, True, drops, misses, refusals,
    )
    _roll_weighted_set(
        tables, mob, rng, TABLE_DROPS_SPECIALLY, tables.specially,
        mob.drops_specially, False, drops, misses, refusals,
    )
    _roll_quest(mob, refusals)
    return LootRollResult(
        mob.mob_id, mob.level, mob.rank, tuple(drops), tuple(misses),
        tuple(refusals), padding,
    )


# ---------------------------------------------------------------------------
# The canonical rendering.  ASCII only (the gate console is code page 874),
# stable, and the thing determinism is pinned against.
# ---------------------------------------------------------------------------
def describe_loot_roll(result: LootRollResult) -> tuple[str, ...]:
    """One ASCII line per decision, in roll order.  This is the pinned form."""
    if type(result) is not LootRollResult:
        raise ValueError("describe_loot_roll takes a LootRollResult")
    lines = [
        "mob=%d level=%d rank=%d padding_slots=%d"
        % (result.mob_id, result.level, result.rank, result.padding_slots),
    ]
    for drop in result.drops:
        lines.append(
            "drop|%s|slot=%d|item=%s|table=%s|qty=%d|quality=%s|money=%s|tags=%s"
            % (
                drop.source_table,
                drop.slot_index,
                "MONEY" if drop.item_id is None else str(drop.item_id),
                "-" if drop.item_table is None else drop.item_table,
                drop.quantity,
                "-" if drop.quality is None else drop.quality,
                "yes" if drop.is_money else "no",
                ",".join(drop.inference_tags) if drop.inference_tags else "-",
            )
        )
    for miss in result.misses:
        lines.append(
            "miss|%s|slot=%d|rate=%s"
            % (miss.source_table, miss.slot_index, _format_rate(miss.rate_percent))
        )
    for refusal in result.refusals:
        lines.append(
            "refuse|%s|%s" % (refusal.source_table, refusal.reason)
        )
    return tuple(lines)


def _format_rate(rate: float) -> str:
    text = repr(float(rate))
    return text
