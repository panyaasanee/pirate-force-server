-- 016_character_quest_state.sql
-- chief / the quest flag+counter persistence door, on LANE-Q's CORE-REQUEST.
--
-- WHAT THIS FILE DOES.  Two bare, empty tables and nothing else -- no
-- ALTER, no UPDATE, no touched row anywhere.  Same reasoning `010_ground_
-- drops.sql`/`011_character_skills.sql`/`015_character_equipment.sql` give
-- for skipping the automatic pre-apply snapshot `COO-DECISION 20260901_1112`
-- point 3 requires only for a migration that touches EXISTING rows: every
-- statement below is a `CREATE`.
--
-- WHY THIS EXISTS.  `pf_bridge/notes_to_chief/20260906_1950_LANE-Q-CORE-
-- REQUEST-quest-flag-counter-daily-stamp-columns.md`: `lua_api/quest.py`'s
-- `QuestStateStore` (a `Protocol`, PR #947) codes against exactly this
-- contract already; today the only implementation is `InMemoryQuestStateStore`,
-- named in its own docstring as explicitly not the production answer (it
-- does not survive a relog). These two tables are the DB-backed
-- implementation the request asks for -- `get_quest_flag`/`set_quest_flag`/
-- `get_quest_counter`/`set_quest_counter` below.
--
-- WHY TWO TABLES, NOT THREE.  The request's own letter measured that the
-- three usage groups it names (flag get/set, kill-count, daily-stamp) all
-- route through the SAME two shapes: a flag is one int per (character,
-- quest), a counter is one int per (character, quest, name) -- the daily
-- stamp is a counter whose `counter_name` happens to be a fixed string
-- (`"daily_report_epoch_day"`) rather than a mob id, not a third shape.
--
-- WHY `quest_id` IS BOUNDED TO u16, NOT AN OPEN INTEGER.  Measured on the
-- wire this round (`columbus_quest_dispatch.py:330`, `grep`ped again before
-- writing this file): quest ids travel as `legacy.u16tag(0x12, quest_id)`,
-- so `0..65535` is every value that can ever reach this door from a real
-- client frame, and a wider value is a caller bug this schema can refuse
-- immediately rather than store and never be able to round-trip on the
-- wire.
--
-- WHY `flag_value`/`counter_value` ARE BOUNDED TO u32, NOT AN ENUM.  The
-- request is explicit that this lane owns the numbers' meaning
-- (`Quest.None`/`Active`/`Finish` = 0/1/2 in LANE-Q's own code today, a
-- daily-stamp epoch-day count, or a kill-count progress value) and that DB
-- must not encode that meaning -- same principle
-- `015_character_equipment.sql` states for `slot_id`. u32 is the widest
-- bound that costs nothing today (every value in the request's own
-- examples fits in a handful of bits) while still refusing a caller's
-- overflow/negative-count bug before it reaches a row, the same asymmetric-
-- cost argument `015`'s own comment makes for `slot_id`. `lua_api.quest.
-- QuestStateStore` is a `Protocol` the request itself says can change
-- shape without a rewrite if this bound is ever wrong.
--
-- WHY `counter_name` IS `TEXT CHECK(length BETWEEN 1 AND 128)`, VERBATIM
-- FROM THE REQUEST.  LANE-Q picks this string itself (a mob id rendered as
-- text, or the fixed daily-stamp key) and the request states the bound
-- directly; enforced here so a caller's empty-string or runaway-length bug
-- is refused at the door rather than silently stored.
--
-- WHY `UNIQUE(character_id, quest_id)` / `UNIQUE(character_id, quest_id,
-- counter_name)`, AND `INSERT OR REPLACE` ON THE WRITE SIDE.  A flag is one
-- value per (character, quest) and a `set_quest_flag` call always means
-- "this is now the value", never an accumulation -- the request states
-- `set_quest_counter` is an absolute set too, not an increment (a future
-- `increment_quest_counter` is explicitly NOT asked for here). Same
-- overwrite-on-repeat shape `equip_item` uses for `character_equipment`,
-- for the same reason: every call is a fresh state change, not a repeat of
-- an existing fact (`grant_starting_skills`' `INSERT OR IGNORE` is the
-- wrong shape here, not this one).
--
-- WHY NO FOREIGN KEY BEYOND `characters(id)`.  Same shape `011`/`015` use:
-- every normal connection runs `PRAGMA foreign_keys=ON` (`store.connect`),
-- so an orphan write is refused by SQLite itself.
CREATE TABLE character_quest_flags (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(id),
    quest_id INTEGER NOT NULL
        CHECK(typeof(quest_id)='integer' AND quest_id BETWEEN 0 AND 65535),
    flag_value INTEGER NOT NULL
        CHECK(typeof(flag_value)='integer'
              AND flag_value BETWEEN 0 AND 4294967295),
    updated_at TEXT NOT NULL,
    UNIQUE(character_id, quest_id)
);

CREATE TABLE character_quest_counters (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(id),
    quest_id INTEGER NOT NULL
        CHECK(typeof(quest_id)='integer' AND quest_id BETWEEN 0 AND 65535),
    counter_name TEXT NOT NULL
        CHECK(length(counter_name) BETWEEN 1 AND 128),
    counter_value INTEGER NOT NULL
        CHECK(typeof(counter_value)='integer'
              AND counter_value BETWEEN 0 AND 4294967295),
    updated_at TEXT NOT NULL,
    UNIQUE(character_id, quest_id, counter_name)
);
