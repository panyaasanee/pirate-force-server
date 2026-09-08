-- 016_character_experience_skill_points_backfill.sql
-- LANE-DB / the two columns a quest reward cannot pay into.
--
-- WHAT THIS FILE DOES, IN ONE SENTENCE.  It writes 0 over the NULL that every
-- EXISTING row holds in `characters.experience` and `characters.skill_points`,
-- and it changes nothing else -- not the schema, not a default, not what a
-- character born tomorrow holds.
--
-- WHY THIS UNBLOCKS A PLAYER AND NOT ONLY A COLUMN.  `store.grant_experience`
-- raises `UnmeasuredTypedAttributeError` on a NULL `experience` and
-- `store.spend_skill_points` raises `UnmeasuredSkillPointsError` on a NULL
-- `skill_points`; `lua_api/reward.py` turns both into `refused=store_error`.
-- LANE-Q counted 497 call sites in 166 quest scripts on the other side of
-- those two doors (`Quest.AddCriteriaExp` / `AddCriteriaSkillPoint` /
-- `AddCriteriaCash`, letter `20260908_0555`).  Today every one of them
-- refuses for every character in the owner's database, because every row
-- holds NULL.  The paying code is already on `main`; after this file those
-- doors open for every character that EXISTS.
--
-- AND NOT FOR ONE CREATED AFTERWARDS, WHICH IS THIS FILE'S REAL COST.
-- `store.create_character`'s INSERT names `level`, `hp_current` and `hp_max`
-- and nothing else (`store.py:748`), so with no column default a character
-- rolled after this migration holds NULL in both columns and gets exactly the
-- refusal it would have got yesterday.  Measured, not conceded in the
-- abstract -- `pf-adversary` on round `ywpicw`, finding D1:
--
--     pre-016 character  grant_experience -> OK       spend_skill_points -> OK
--     born after 016     grant_experience -> REFUSES  spend_skill_points -> REFUSES
--
-- That is the same shape `009`'s own header calls the mistake `007` and `008`
-- made: "007 and 008 seeded the cohort that existed when they ran and can
-- never run again, so on a fresh install every character born afterwards held
-- NULL in all four forever."  This file is a cohort seed of that kind,
-- knowingly, because the half that would fix it is the half a pin holds (see
-- below) -- and the consequence is written here rather than left for somebody
-- to discover on the owner's machine.  Two things follow from it in this same
-- round: the question goes to COO as the round's first ask, and
-- `persistence_null_audit.NULL_AUDIT_COLUMNS` now audits both columns, so the
-- population of new characters holding NULL is COUNTABLE while that answer is
-- waited for, instead of accumulating unseen.
--
-- WHY 0 IS A MEASUREMENT HERE AND NOT A GUESS.  `COO-DECISION 20260901_1059`
-- forbids guessing an unmeasured field to be zero, which is exactly why `009`
-- left these two columns alone.  Two lanes measured them on 2026-09-08:
--
--   * `experience` -- LANE-Q, `pf_bridge/notes_to_chief/20260908_0555_
--     LANE-Q-TO-LANE-DB-experience-is-0-skill-points-is-NOT-obviously-0.md`
--     point 1.  Nothing in the 616 scripts of `gamedata/lua/**` SETS
--     experience; every call site adds to it (`Player.AddExp`,
--     `Quest.AddCriteriaExp`, `Quest.AddLvCriteriaExp`), and there is no
--     `SetExp` among the 160 functions of `gamedata/PF_LUA_API_SPEC.md`.  No
--     `CONSTDATA_TH__CHARCREATE_*` table carries an experience column.
--     (LANE-Q's letter says it checked four such tables; there are six --
--     `+LOOK_TIP`, `+SKIN_TIP`.  `pf-adversary` re-ran the grep across all
--     six this round and the conclusion holds, so the miscount is recorded
--     and the finding stands.)
--     STRONGER THAN THAT GREP, and found by `pf-adversary` rather than by
--     either letter: `src/pirateforce_foundation/data/standard_status.tsv`,
--     the committed, sha-pinned experience table this repository already
--     reads, holds `n_EXP_CURRENTLV = 0` at level 1.  The client's own curve
--     starts at zero.
--
--   * `skill_points` -- LANE-CS, `pf_bridge/notes_to_chief/20260908_0458_
--     LANE-CS-TO-DB-Q-level-sp-is-an-experience-curve-not-a-skill-point-
--     column.md`.  `gamedata/tables/CONSTDATA_TH__LEVEL_SP.tsv`, the table
--     that looked like it awarded 2 points at level 1, runs to 13,645,740 by
--     level 120 over 120 strictly increasing rows.  Thirteen million is not a
--     skill-point balance under either reading, per-level or cumulative.
--
-- WHERE THIS LANE COULD NOT FOLLOW LANE-CS, MEASURED THIS ROUND.  That letter
-- reaches its conclusion by a second step -- `LEVEL_SP` is the only
-- level-indexed table in the game data, therefore it must BE the experience
-- curve -- and that step is false in this repository:
--
--     LEVEL_SP.n_SP         lv1=2  lv2=4   lv10=42   lv120=13,645,740
--     STANDARD_STATUS
--       .n_EXP_CURRENTLV    lv1=0  lv2=79  lv10=714  lv120=91,699,378
--     rows identical out of 120: 0
--
-- The experience curve already exists, in
-- `src/pirateforce_foundation/data/standard_status.tsv`, and
-- `persistence_experience.threshold_for_next_level` has been reading it on
-- `main` all along.  So `LEVEL_SP` is a level-indexed table that is NOT the
-- experience curve, and what it IS remains unmeasured.
--
-- AND LANE-CS'S FIRST ARGUMENT DOES NOT SURVIVE EITHER, measured by
-- `pf-adversary` on this round (D3) against a file already committed here:
-- `src/pirateforce_foundation/lua_api/quest_criteria_curve.tsv` carries a
-- `skill_point` column that tops out at 14,252,800,
-- `lua_api/quest_criteria.py` maps `KIND_SKILL_POINT` onto it, and that
-- module says so in its own words ("the shipped curve tops out at
-- 14252800").  A skill-point number in the tens of millions is not
-- impossible in this game; it is shipped.  So "thirteen million cannot be
-- skill points" is not an argument this file may lean on, and it does not.
-- What is left standing for `skill_points` is thinner than either letter
-- suggested: no table, frame or script anybody has read says what a
-- character is born holding.  It ships tagged
-- `[LANE-DB assumption - awaiting COO]`, which is what LANE-Q asked for.
-- The tag is on the NUMBER, not a reason to hold the file: every row holds
-- NULL today, so nothing here can overwrite a value anybody measured -- it
-- replaces "nobody has looked" with a 0 the pre-migration snapshot can
-- still undo, row for row.
--
-- WHY THERE IS NO `DEFAULT` AND NO TABLE REBUILD HERE, WHICH IS THE WHOLE
-- SHAPE OF THIS FILE.  The obvious version of this migration is `009`'s: a
-- rebuild that also attaches `DEFAULT 0` to both columns, so a character born
-- tomorrow starts at 0 like every character alive.  That version was written
-- in full this round, with ten guards and forty-five tests, and then measured
-- against the suite -- and it turns 39 tests red, 30 of them at one shared
-- fixture.  `tests/pf_birth_state.py` names the THREE typed states a newly
-- created character may hold and refuses everything else by design, saying so
-- in its own words: "an insertion point that adds a FIFTH column turns every
-- file that imports this one red at its fixture".  A DEFAULT on these two
-- columns is that fifth and sixth column.  That pin is not a bug and is not
-- this file's to move -- NOW.md `2050` says a pin is released by its owner
-- while the caller withdraws, and `COO-DECISION 20260902_1607`, the ruling
-- that allowed DEFAULTs at all, was the owner settling it herself in session
-- and naming exactly four columns.
-- So the file was cut down to the half that contradicts nothing.  A BACKFILL
-- IS NOT A BIRTH RULE: it changes what characters who already exist hold, and
-- leaves what `create_character` produces exactly as the pin requires -- a
-- newborn still holds NULL, `get_skill_points` still answers `None` for it,
-- and both doors still refuse it by name.  The DEFAULT question goes to COO
-- in `pf_bridge/notes_to_chief/20260908_0631_LANE-DB-ASK-COO-may-016-give-
-- experience-and-skill-points-a-birth-default.md` with these
-- numbers attached, and if the answer is yes it is one rebuild migration,
-- whose ten guards this round already wrote and proved.
-- The narrowing is also the safer file by a wide margin on the owner's live
-- database: no `DROP TABLE characters`, so no cascade to disarm, no DDL to
-- reproduce byte for byte, no index to recreate.  Guard 4 below turns "the
-- schema is untouched" from an intention into a measurement.
--
-- THE BACKUP, WHICH IS NOT OPTIONAL FOR THIS FILE.  This file writes over
-- existing rows, so `COO-DECISION 20260901_1112` point 3 applies in full: an
-- automatic pre-apply snapshot must exist.  It does, and it needed no new
-- wiring -- measured this round rather than assumed:
-- `persistence_backup.should_snapshot` votes True while ANY migration is
-- pending, `SQLiteStore.migrate_with_backup` takes the copy BEFORE
-- `migrate()` and raises `BackupError` without migrating if it cannot
-- (`store.py:568`), and both boot call sites that migrate go through it,
-- `app.py:791` and `app.py:794`.  Undoing this file is that snapshot plus an
-- older server; nothing here rolls a schema backwards on its own and nothing
-- here claims it does.
--
-- ORDER OF THE GUARDS.  Specific first, catch-all last, one named CONSTRAINT
-- each, for the reason `009` gives at length: SQLite reports a NAMED
-- constraint by its name, so a failure on the owner's machine reads
-- `CHECK constraint failed: guard_only_null_became_zero_in_the_two_columns`
-- instead of `CHECK constraint failed: ok=1`.

-- The "before" pictures every guard is graded against, all read inside the
-- runner's own transaction so none of them can describe a different moment
-- than the write does.
CREATE TABLE _pf_mig016_rows_before AS SELECT * FROM characters;
CREATE TABLE _pf_mig016_ddl_before AS
    SELECT sql AS ddl FROM sqlite_master WHERE type='table' AND name='characters';
CREATE TABLE _pf_mig016_cols_before AS
    SELECT cid, name, type, "notnull", dflt_value, pk
      FROM pragma_table_info('characters');
CREATE TABLE _pf_mig016_idx_before AS
    SELECT name, sql FROM sqlite_master
     WHERE type='index' AND tbl_name='characters';
CREATE TABLE _pf_mig016_master_before AS
    SELECT type, name, tbl_name, sql FROM sqlite_master
     WHERE NOT (type='table' AND name='characters')
       AND name NOT LIKE '\_pf\_mig016\_%' ESCAPE '\';
-- Every table that references `characters`, plus the grandchild that hangs
-- off `character_backpacks`.  `009`'s list named four and three more have
-- landed since (`011` character_skills, `013` character_home_marker, `015`
-- character_equipment); a backfill cannot cascade, but a guard that silently
-- stops watching new tables is how the NEXT rebuild gets through.
-- `test_the_children_guard_names_every_table_that_references_characters`
-- derives the list from the schema so this cannot fall behind again.
CREATE TABLE _pf_mig016_children_before AS
    SELECT (SELECT COUNT(*) FROM character_positions)       AS positions,
           (SELECT COUNT(*) FROM character_backpacks)       AS backpacks,
           (SELECT COUNT(*) FROM character_backpack_items)  AS items,
           (SELECT COUNT(*) FROM character_skills)          AS skills,
           (SELECT COUNT(*) FROM character_home_marker)     AS homes,
           (SELECT COUNT(*) FROM character_equipment)       AS equipment,
           (SELECT COUNT(*) FROM sessions)                  AS sessions_;
-- THE WRITE.  Two statements, each with the `IS NULL` that makes it a
-- backfill rather than a reset; guard 2 is what proves the difference on the
-- rows themselves rather than on the text of these two lines.
-- SOFT-DELETED ROWS ARE BACKFILLED TOO, deliberately.  `deleted_at` is a
-- tombstone `004` lets a character come back from, and a row that came back
-- holding NULL would be a character whose quests refuse to pay -- the exact
-- state this file exists to end.
UPDATE characters SET experience = 0 WHERE experience IS NULL;
UPDATE characters SET skill_points = 0 WHERE skill_points IS NULL;

-- WHERE THE ROW COUNT WENT, AND WHY IT IS NOT A TABLE HERE.  LANE-Q asked for
-- the number of rows this backfill touches to be recorded, so the write can
-- be undone if the `skill_points` answer is ever revised -- and after this
-- transaction the table cannot answer it, because there is no NULL left to
-- count.  A `migration_backfill_audit` table was written this round to hold
-- it, and then withdrawn: `tests/test_npc_interaction_wire.py`'s
-- `EXPECTED_TABLES` pins the exact set of tables this store may own, every
-- previous addition to it cites the COO or PANYA decision that ORDERED the
-- table, and nothing ordered this one.  NOW.md `2050` says the caller
-- withdraws while the pin's owner decides, so it withdrew.
-- The reversibility the owner's rule actually requires is not weakened by
-- that: the automatic pre-migration snapshot named above holds every row
-- exactly as it stood, so the count remains derivable -- from the snapshot
-- and the live database together, which is what the next round proposes to
-- build, as a reader over artifacts that already exist rather than as a new
-- table.  Asked in `pf_bridge/notes_to_chief/20260908_0632_LANE-DB-ASK-COO-
-- may-a-backfill-record-its-own-row-count.md`.

-- -- THE GUARDS.  `CHECK(ok=1)` turns any 0 below into a failed INSERT, which
-- -- fails the whole script, which rolls the runner's transaction back: the
-- -- owner's rows are either fully backfilled and proved, or untouched.

-- 1. NOTHING OUTSIDE THE TWO COLUMNS MOVED, and no row appeared or vanished.
--    `IS NOT` is the NULL-safe comparison, so a column that was NULL and is
--    now a number fails here -- which is what holds the write to the two
--    columns it claims.
CREATE TABLE _pf_mig016_guard_rows(
    ok INTEGER NOT NULL
        CONSTRAINT guard_no_row_changed_outside_the_two_columns CHECK(ok=1));
INSERT INTO _pf_mig016_guard_rows(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM characters) = (SELECT COUNT(*) FROM _pf_mig016_rows_before)
    AND NOT EXISTS (SELECT 1 FROM _pf_mig016_rows_before b
                     WHERE NOT EXISTS (SELECT 1 FROM characters c WHERE c.id = b.id))
    AND NOT EXISTS (
        SELECT 1 FROM characters c JOIN _pf_mig016_rows_before b ON b.id = c.id
         WHERE c.account_id IS NOT b.account_id
            OR c.selector IS NOT b.selector
            OR c.name IS NOT b.name
            OR c.actor_wire IS NOT b.actor_wire
            OR c.avatar_wire IS NOT b.avatar_wire
            OR c.avatar_typed_json IS NOT b.avatar_typed_json
            OR c.identity_lo IS NOT b.identity_lo
            OR c.identity_hi IS NOT b.identity_hi
            OR c.created_at IS NOT b.created_at
            OR c.updated_at IS NOT b.updated_at
            OR c.deleted_at IS NOT b.deleted_at
            OR c.name_key IS NOT b.name_key
            OR c.create_fingerprint IS NOT b.create_fingerprint
            OR c.level IS NOT b.level
            OR c.hp_current IS NOT b.hp_current
            OR c.hp_max IS NOT b.hp_max
            OR c.mp_current IS NOT b.mp_current
            OR c.mp_max IS NOT b.mp_max
            OR c.speed_walk IS NOT b.speed_walk
            OR c.class_id IS NOT b.class_id
            OR c.unspent_points IS NOT b.unspent_points
            OR c.stat_str IS NOT b.stat_str
            OR c.stat_con IS NOT b.stat_con
            OR c.stat_dex IS NOT b.stat_dex
            OR c.stat_int IS NOT b.stat_int
            OR c.stat_per IS NOT b.stat_per
            OR c.cash IS NOT b.cash
            OR c.bonus_str IS NOT b.bonus_str
            OR c.bonus_con IS NOT b.bonus_con
            OR c.bonus_dex IS NOT b.bonus_dex
            OR c.bonus_int IS NOT b.bonus_int
            OR c.bonus_per IS NOT b.bonus_per)
    THEN 1 ELSE 0 END;

-- 2. THE WRITE DID EXACTLY WHAT IT SAYS.  Every value that moved moved from
--    NULL to 0; every value that was already a number is still that number,
--    including a legitimately stored 0 and including a veteran's 12345.  An
--    `UPDATE` that lost its `WHERE` clause is caught here and nowhere else.
CREATE TABLE _pf_mig016_guard_backfill(
    ok INTEGER NOT NULL
        CONSTRAINT guard_only_null_became_zero_in_the_two_columns CHECK(ok=1));
INSERT INTO _pf_mig016_guard_backfill(ok) SELECT CASE WHEN
    NOT EXISTS (
        SELECT 1 FROM characters c JOIN _pf_mig016_rows_before b ON b.id = c.id
         WHERE NOT (
                 (b.experience IS NULL AND c.experience = 0)
              OR (b.experience IS NOT NULL AND c.experience IS b.experience))
            OR NOT (
                 (b.skill_points IS NULL AND c.skill_points = 0)
              OR (b.skill_points IS NOT NULL AND c.skill_points IS b.skill_points)))
    THEN 1 ELSE 0 END;

-- 3. NO NULL IS LEFT IN EITHER COLUMN.  Guard 2 alone is satisfied by a file
--    that copies the NULLs faithfully; this one is what makes the door at
--    `store.grant_experience` open for every row that exists today.
CREATE TABLE _pf_mig016_guard_no_nulls(
    ok INTEGER NOT NULL
        CONSTRAINT guard_no_null_remains_in_the_two_columns CHECK(ok=1));
INSERT INTO _pf_mig016_guard_no_nulls(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM characters
      WHERE experience IS NULL OR skill_points IS NULL) = 0
    THEN 1 ELSE 0 END;

-- 4. THE SCHEMA IS UNTOUCHED -- the guard that says out loud what makes this
--    file a backfill and not `009`.  The stored DDL text is compared byte for
--    byte (no normalisation: this file must not reflow it either), and the
--    column list with it, DEFAULTS INCLUDED.  A `DEFAULT 0` sneaked onto
--    `experience` here -- the very change this file was cut down to avoid --
--    fails at this line, so the narrowing is a measurement and not a promise
--    in a comment.
CREATE TABLE _pf_mig016_guard_schema(
    ok INTEGER NOT NULL
        CONSTRAINT guard_the_schema_is_untouched CHECK(ok=1));
INSERT INTO _pf_mig016_guard_schema(ok) SELECT CASE WHEN
    (SELECT sql FROM sqlite_master WHERE type='table' AND name='characters')
        IS (SELECT ddl FROM _pf_mig016_ddl_before)
    AND (SELECT COUNT(*) FROM pragma_table_info('characters'))
        = (SELECT COUNT(*) FROM _pf_mig016_cols_before)
    AND NOT EXISTS (
        SELECT 1 FROM pragma_table_info('characters') a
          JOIN _pf_mig016_cols_before b ON b.cid = a.cid
         WHERE a.name IS NOT b.name
            OR a.type IS NOT b.type
            OR a."notnull" IS NOT b."notnull"
            OR a.dflt_value IS NOT b.dflt_value
            OR a.pk IS NOT b.pk)
    THEN 1 ELSE 0 END;

-- 5. EVERY INDEX IS STILL THERE, with the same name and the same text: lose
--    `characters_active_selector` and two live characters share a slot; lose
--    `characters_create_fingerprint` and a retransmitted create packet makes
--    a second character instead of returning the first.
CREATE TABLE _pf_mig016_guard_indexes(
    ok INTEGER NOT NULL
        CONSTRAINT guard_every_index_is_unchanged CHECK(ok=1));
INSERT INTO _pf_mig016_guard_indexes(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM sqlite_master
      WHERE type='index' AND tbl_name='characters')
        = (SELECT COUNT(*) FROM _pf_mig016_idx_before)
    AND NOT EXISTS (
        SELECT 1 FROM _pf_mig016_idx_before b
         WHERE NOT EXISTS (
            SELECT 1 FROM sqlite_master m
             WHERE m.type='index' AND m.tbl_name='characters'
               AND m.name = b.name AND m.sql IS b.sql))
    THEN 1 ELSE 0 END;

-- 6. THE CHILDREN ARE STILL THERE.  Counting the SURVIVORS, which is not the
--    same sentence as "nothing is orphaned": a `pf-adversary` pass on `009`
--    showed the orphan check returns a clean 0 in exactly the catastrophic
--    case, because a cascade leaves nothing to be orphaned.  The orphan check
--    is kept beside it -- it catches the other direction, a write that
--    renumbers `id`, which counting cannot see.
CREATE TABLE _pf_mig016_guard_children(
    ok INTEGER NOT NULL
        CONSTRAINT guard_the_child_rows_all_survived CHECK(ok=1));
INSERT INTO _pf_mig016_guard_children(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM character_positions)
        = (SELECT positions FROM _pf_mig016_children_before)
    AND (SELECT COUNT(*) FROM character_backpacks)
        = (SELECT backpacks FROM _pf_mig016_children_before)
    AND (SELECT COUNT(*) FROM character_backpack_items)
        = (SELECT items FROM _pf_mig016_children_before)
    AND (SELECT COUNT(*) FROM character_skills)
        = (SELECT skills FROM _pf_mig016_children_before)
    AND (SELECT COUNT(*) FROM character_home_marker)
        = (SELECT homes FROM _pf_mig016_children_before)
    AND (SELECT COUNT(*) FROM character_equipment)
        = (SELECT equipment FROM _pf_mig016_children_before)
    AND (SELECT COUNT(*) FROM sessions)
        = (SELECT sessions_ FROM _pf_mig016_children_before)
    AND (SELECT COUNT(*) FROM pragma_foreign_key_check()) = 0
    THEN 1 ELSE 0 END;

-- 7. EVERY OTHER OBJECT IN THE DATABASE IS BYTE-IDENTICAL, by name and by
--    stored SQL -- including any trigger or view, which no per-column check
--    can see.  `schema_migrations` is excluded because the runner inserts
--    this file's own ledger row inside this transaction.  The `_pf_mig016_*`
--    scratch tables are excluded on both sides because they exist only
--    between the first statement of this transaction and the last, which is
--    what `test_no_scratch_table_of_this_migration_survives` proves.
--    THIS FILE CREATES NO PERMANENT OBJECT AT ALL, so anything new in
--    `sqlite_master` after it has run is something it did not mean to do.
CREATE TABLE _pf_mig016_guard_other_objects(
    ok INTEGER NOT NULL
        CONSTRAINT guard_every_other_object_is_unchanged CHECK(ok=1));
INSERT INTO _pf_mig016_guard_other_objects(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM sqlite_master
      WHERE NOT (type='table' AND name='characters')
        AND name NOT LIKE '\_pf\_mig016\_%' ESCAPE '\')
        = (SELECT COUNT(*) FROM _pf_mig016_master_before)
    AND NOT EXISTS (
        SELECT 1 FROM _pf_mig016_master_before b
         WHERE NOT EXISTS (
            SELECT 1 FROM sqlite_master m
             WHERE m.type IS b.type AND m.name IS b.name
               AND m.tbl_name IS b.tbl_name AND m.sql IS b.sql))
    THEN 1 ELSE 0 END;

DROP TABLE _pf_mig016_guard_other_objects;
DROP TABLE _pf_mig016_guard_children;
DROP TABLE _pf_mig016_guard_indexes;
DROP TABLE _pf_mig016_guard_schema;
DROP TABLE _pf_mig016_guard_no_nulls;
DROP TABLE _pf_mig016_guard_backfill;
DROP TABLE _pf_mig016_guard_rows;
DROP TABLE _pf_mig016_children_before;
DROP TABLE _pf_mig016_master_before;
DROP TABLE _pf_mig016_idx_before;
DROP TABLE _pf_mig016_cols_before;
DROP TABLE _pf_mig016_ddl_before;
DROP TABLE _pf_mig016_rows_before;
