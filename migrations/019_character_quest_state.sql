-- 019_character_quest_state.sql
-- LANE-DB / the quest-state persistence doors -- the two bare tables.
--
-- WHAT THIS FILE DOES.  Two new tables, `character_quest_flag` (one row
-- per (character, quest), holding one status number) and
-- `character_quest_counter` (one row per (character, quest, counter name),
-- holding one count).  No existing table is touched, no existing row is
-- written and nothing is backfilled -- every character has zero rows in
-- both tables until `SQLiteStore.set_quest_flag` / `set_quest_counter` /
-- `increment_quest_counter` (added alongside this file) write one.
--
-- WHY THIS ROUND.  `pf_bridge/NOW.md` carries the owner's order
-- `PANYA 20260908_1520` ("quest-flag store first"), routed to this lane by
-- `notes_to_chief/20260908_1642_COO-DECISION-quest-flags-schema-comes-
-- before-the-bulk-skill-rows-LANE-DB.md`: the quest-state doors this lane
-- DECLARED in `notes_to_chief/20260905_2212_LANE-DB-TO-LANE-Q-quest-state-
-- doors-declared-and-opened-this-round.md` never reached `main`, and
-- LANE-Q's own half is already written and waiting on them
-- (`notes_to_chief/20260908_1647_LANE-Q-TO-LANE-DB-the-quest-state-doors-
-- are-not-on-main.md`: `StoreBackedQuestStateStore` calls these five
-- methods by name).  The `2212` contract is implemented here VERBATIM --
-- the COO decision forbids redesigning it -- with one forced change: the
-- migration number.  `2212` reserved `014`; `014` on `main` today is
-- `014_character_skills_learned_source.sql`, and `015`..`018` are taken
-- too, so this is `019`.  Nothing else in that contract moves.
--
-- WHY TWO TABLES AND NOT ONE.  A flag is one number per (character,
-- quest); a counter is one number per (character, quest, NAME).  Folding
-- them together would need a nullable name column that is meaningful on
-- half the rows and meaningless on the other half, and a partial unique
-- index to keep the flag row single -- two facts with two different keys
-- are two tables, the same shape `011_character_skills.sql` and
-- `013_character_home_marker.sql` already use for two different per-
-- character facts.  `pf_bridge/gamedata/lua/Quest/q_kill5.lua` is the
-- committed evidence for the split: `Quest.SetFlag(Quest.Active)` sets one
-- status per quest, while `Quest.MobKillCount(Quest.Var2,Quest.Var3)` and
-- `Quest.CheckMobKillCount(...)` track TWO named counters inside that same
-- quest at the same time -- rows that must not collide.
--
-- WHY `quest_id` IS PINNED TO u16.  `src/pirateforce_foundation/
-- columbus_quest_dispatch.py` puts a quest id on the wire with
-- `legacy.u16tag(0x12, quest_id)` -- the range is the client's, measured,
-- not a bound this schema invents.  The CHECK is written here as well as
-- in the store doors so a second writer (a future migration, a repair
-- script) cannot put a row here that the wire could never carry.
--
-- WHY `flag_value` HAS NO CHECK AND NO ENUM.  `Quest.Active` /
-- `Quest.Finish` and every other status number are the SCRIPT's meanings,
-- read out of `QUESTDATA_*` by LANE-Q's host; this database does not know
-- them and must not guess them (`COO-DECISION 20260901_1059` forbids
-- exactly that guess, and `20260908_1642` restates it: "flag_value has no
-- enum, the DB does not know what the number means").  The only bound is
-- SQLite's own INTEGER.  A later round narrows it the day a proven
-- requirement names a narrower range.
--
-- WHY `counter_name` IS 1..128 CHARACTERS.  The name is the caller's own
-- key (`q_kill5.lua` distinguishes its two trackers by mob id turned into
-- text), so an empty name is a caller bug that would silently merge two
-- trackers into one row, and an unbounded name is an unbounded index key.
-- 128 is the contract's own number (`2212`), kept verbatim.
--
-- WHY NO `ON DELETE CASCADE` DIFFERENCE FROM `013`.  Both tables take
-- `REFERENCES characters(id) ON DELETE CASCADE`, matching
-- `character_home_marker` and `character_skills`: a character row that is
-- ever hard-deleted must not leave quest rows pointing at nothing.  The
-- store doors additionally refuse a SOFT-deleted character
-- (`deleted_at IS NOT NULL`), which the schema cannot express.
--
-- WHY NO AUTOMATIC BACKUP MECHANISM IS ADDED BY THIS FILE.
-- `COO-DECISION 20260901_1112` point 3 requires an automatic pre-apply
-- snapshot for a migration that touches EXISTING ROWS (backfill/UPDATE/
-- rebuild).  This file writes no `UPDATE`, backfills nothing and rebuilds
-- no table -- it is two `CREATE TABLE`s with zero rows the moment they
-- run, the same shape `010_ground_drops.sql`, `012_ground_drops_taken_
-- marker.sql` and `013_character_home_marker.sql` already gave the
-- identical reasoning for.  For the same reason `persistence_rebuild_
-- guard` is NOT used here: there is no pre-existing row for a content
-- guard to compare against.
--
-- WHY NO INDEX BEYOND THE PRIMARY KEYS.  Every read these tables serve is
-- keyed by the full primary key (`get_quest_flag(character_id, quest_id)`,
-- `get_quest_counter(character_id, quest_id, counter_name)`), which the
-- implicit index on the PRIMARY KEY already answers.  `011` added an
-- explicit index because it reads a character's WHOLE skill list; nothing
-- reads a character's whole quest list today, and an index nobody queries
-- is a write cost with no reader.
CREATE TABLE character_quest_flag (
    character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    quest_id INTEGER NOT NULL CHECK(quest_id BETWEEN 0 AND 65535),
    flag_value INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (character_id, quest_id)
);

CREATE TABLE character_quest_counter (
    character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    quest_id INTEGER NOT NULL CHECK(quest_id BETWEEN 0 AND 65535),
    counter_name TEXT NOT NULL CHECK(LENGTH(counter_name) BETWEEN 1 AND 128),
    counter_value INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (character_id, quest_id, counter_name)
);
