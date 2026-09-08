-- 017_character_experience_skill_points_birth_defaults.sql
-- LANE-DB / the half of `016` that a newborn never got.
--
-- WHAT THIS FILE DOES, IN ONE SENTENCE.  It rebuilds `characters` so that two
-- columns carry a DEFAULT they did not have before -- `experience = 0` and
-- `skill_points = 0` -- and changes nothing else about the table, nothing at
-- all about the rows in it, and no other object in the database.
--
-- WHY IT EXISTS, WHICH IS A COST `016` WROTE DOWN RATHER THAN HID.
-- `016_character_experience_skill_points_backfill.sql` wrote 0 over the NULL
-- every EXISTING row held in these two columns, and its own header names what
-- it could not reach: "with no column default a character rolled after this
-- migration holds NULL in both columns and gets exactly the refusal it would
-- have got yesterday".  That is measured, not feared -- `pf-adversary` on
-- round `ywpicw`, finding D1:
--
--     pre-016 character  grant_experience -> OK       spend_skill_points -> OK
--     born after 016     grant_experience -> REFUSES  spend_skill_points -> REFUSES
--
-- The refusals are `store.grant_experience` raising
-- `UnmeasuredTypedAttributeError` on a NULL `experience` and
-- `store.spend_skill_points` raising `UnmeasuredSkillPointsError` on a NULL
-- `skill_points`; `lua_api/reward.py` turns both into `refused=store_error`.
-- LANE-Q counted 497 call sites in 166 quest scripts behind those two doors
-- (letter `20260908_0555`).  So without this file every character created from
-- today onward -- every character on a fresh install, where `016` meets an
-- empty table -- walks into the same wall `016` was written to pull down.
-- `009`'s header calls this exact shape the mistake `007` and `008` made:
-- "007 and 008 seeded the cohort that existed when they ran and can never run
-- again, so on a fresh install every character born afterwards held NULL in
-- all four forever."  `016` is a cohort seed of that kind knowingly; this file
-- is the half that ends it.
--
-- WHO ORDERED IT, AND WHAT THAT OVERRULES.  `016` did not carry the DEFAULT
-- because `tests/pf_birth_state.py` named exactly four birth columns, on the
-- authority of `COO-DECISION 20260902_1607` -- the owner settling it herself
-- in session and naming four.  She reopened it herself on 2026-09-08 at 12:18
-- (`PANYA-DECISION 20260908_1218` point 3, recorded from her own words: "do
-- not hold to what I once said, that a newly born character's defaults are
-- only four columns; there are more than that as the discoveries keep coming.
-- Make it correct logic"), which orders this file out AND orders the pin
-- rewritten so that the fifth and sixth birth column are not a project-wide
-- test failure.  `COO-DECISION 20260908_1246` sequences it: `017` first,
-- ahead of the V111 door and the five-bag set.  The two halves ship in ONE
-- pull request because either alone is red: this file without the pin rewrite
-- turns 39 tests red at a shared fixture (measured on round `ywpicw`), and the
-- pin rewrite without this file pins a birth state nothing produces.
--
-- WHY 0 IS THE NUMBER.  `COO-DECISION 20260901_1059` forbids guessing an
-- unmeasured field to be zero, so the two columns are not equally supported
-- and this file says which is which rather than averaging them:
--
--   * `experience` -- MEASURED.  `src/pirateforce_foundation/data/
--     standard_status.tsv`, the committed, sha-pinned experience table this
--     repository already reads through
--     `persistence_experience.threshold_for_next_level`, holds
--     `n_EXP_CURRENTLV = 0` at level 1: the client's own curve starts at
--     zero.  Separately, nothing in the 616 scripts of `gamedata/lua/**` SETS
--     experience -- every call site adds to it -- and there is no `SetExp`
--     among the 160 functions of `gamedata/PF_LUA_API_SPEC.md` (LANE-Q letter
--     `20260908_0555` point 1, re-grepped across all six
--     `CONSTDATA_TH__CHARCREATE_*` tables by `pf-adversary` on round
--     `ywpicw`).
--
--   * `skill_points` -- NOT MEASURED, AND ORDERED ANYWAY.  `016`'s header
--     records how thin this is: `CONSTDATA_TH__LEVEL_SP.tsv` is not a
--     skill-point balance, but "thirteen million cannot be skill points" is
--     not an argument either, because `lua_api/quest_criteria_curve.tsv`
--     ships a `skill_point` column topping out at 14,252,800.  No table,
--     frame or script anybody has read says what a character is BORN
--     holding.  LANE-CS committed the measurement of that table itself the
--     same day (`src/pirateforce_foundation/skill_point_curve.py`, landed on
--     main at 53c5941): 120 rows, strictly increasing, equal to the
--     experience curve at zero of 120 levels, and -- in its own words -- no
--     statement at all about what a character is born holding.  So the gap
--     is measured and still open.
--     What changed on 2026-09-08 is not the evidence but the
--     authority: the owner ordered `DEFAULT 0` for both columns by name.  The
--     0 on THIS column is hers, not a measurement, and it is written here so
--     that the day an RE answers it, the reader knows which of the two
--     numbers to go back and change.
--
-- WHY A REBUILD, AND WHY THAT IS THE EXPENSIVE WORD IN THIS FILE.  SQLite
-- cannot attach a DEFAULT to an existing column; `ALTER TABLE ... ADD COLUMN`
-- is the only place a default can be introduced.  So this file does what
-- `009` did: build `characters_rebuild` with the new declaration, copy every
-- row across naming every column on both sides, `DROP TABLE characters`,
-- rename, recreate the four indexes.  A `DROP TABLE characters` with
-- `PRAGMA foreign_keys` ON cascade-deletes every child row in six tables and
-- the grandchild behind one of them, and afterwards NOTHING IS ORPHANED,
-- because nothing is left -- which is why guard 5 counts survivors instead of
-- asking for orphans, the correction a `pf-adversary` pass forced on `009`.
--
-- WHY THE DDL TEXT AND NOT `PRAGMA table_info` (guard 6).  `009`'s header
-- records six WRONG rebuilds that a `pragma_table_info`-only draft let commit
-- green: one dropped `REFERENCES accounts(id)` from `account_id`, three
-- dropped a CHECK constraint (`cash`, `hp_max`, `mp_max`), one added `COLLATE
-- NOCASE` to `name_key`, one widened a CHECK range.  None of those six
-- appears in `pragma_table_info` at all, and the lost foreign key would have
-- made every future orphan check on `characters` permanently vacuous.  The
-- stored DDL text sees all six.
--
-- HOW GUARD 6 SUBTRACTS THIS FILE'S OWN CHANGE, and why it is not `009`'s
-- spelling.  `009` removed its four defaults from the after-side by
-- `replace('DEFAULT1','')` and friends, and its own comment records the trap
-- in that: `DEFAULT1` is a prefix of `DEFAULT100`, so the order of the
-- replaces is load-bearing.  This file's default text is `DEFAULT0`, and
-- `identity_hi` ALREADY carries `DEFAULT 0` -- so a blind
-- `replace('DEFAULT0','')` would delete a default this file must not touch
-- from BOTH sides and go green over its loss.  Instead the two replacements
-- name their columns: `experienceINTEGERDEFAULT0` -> `experienceINTEGER`.
-- Nothing else in the declaration can match those strings, so guard 6
-- subtracts exactly the change this file makes and no more.
--
-- WHAT THIS FILE IS NOT.  It is not a backfill.  Not one existing value is
-- read, tested or written -- guard 1 grades that on the rows themselves with
-- NULL-safe `IS NOT`, so a row whose `experience` was NULL and is 0
-- afterwards FAILS this file.  A DEFAULT applies to an INSERT that does not
-- name the column, and `store.create_character`'s INSERT
-- (`store.py:748`) names `level`, `hp_current`, `hp_max` and nothing else of
-- the typed set, so it applies to `experience` and `skill_points` from the
-- next character created onward.  Rows that exist already were reached by
-- `016`, which is why the two files are two files.
--
-- THE BACKUP, WHICH IS NOT OPTIONAL FOR THIS FILE.  A table rebuild on the
-- owner's live database is the case `COO-DECISION 20260901_1112` point 3 is
-- about, and the automatic pre-apply snapshot is already wired, measured
-- rather than assumed: `persistence_backup.should_snapshot` votes True while
-- ANY migration is pending, `SQLiteStore.migrate_with_backup` takes the copy
-- BEFORE `migrate()` and raises `BackupError` without migrating if it cannot
-- (`store.py:568`), and both boot call sites that migrate go through it
-- (`app.py:791`, `app.py:794`).  Undoing this file is that snapshot plus an
-- older server; nothing here rolls a schema backwards on its own and nothing
-- here claims it does.  Once applied, the checksum ledger makes this file
-- immutable -- editing it afterwards makes the owner's database refuse to
-- boot, which is why a later change is a later NUMBER.
--
-- ORDER OF THE GUARDS.  Specific first, catch-all last, one named CONSTRAINT
-- each, for the reason `009` gives at length: SQLite reports a NAMED
-- constraint by its name, so a failure on the owner's machine reads
-- `CHECK constraint failed: guard_exactly_the_two_defaults_were_added`
-- instead of `CHECK constraint failed: ok=1`.
-- `tests/test_migration_017_experience_skill_points_birth_defaults.py`
-- asserts WHICH guard each mutant trips, so a mutant caught by the wrong
-- guard is a test failure rather than a green tick.

-- FOREIGN KEYS OFF FOR THE REBUILD, WHICH IS NOT A CONVENIENCE.  Measured on
-- this round, on a database at `016` carrying one character: without these
-- three lines the `DROP TABLE characters` below performs its implicit
-- `DELETE FROM`, the ON DELETE CASCADE on `character_positions` and
-- `character_backpacks` fires, and the grandchild `character_backpack_items`
-- goes with them -- one character, four backpack rows and its position row,
-- gone, with the rebuilt table still holding every character row and nothing
-- orphaned to find afterwards.  Guard 5 below catches it and rolls the file
-- back, so the failure mode is "the owner's server will not boot" rather than
-- "the owner's characters lost their backpacks", but a migration that can
-- only fail is not a migration.  `009` carries the same three lines for the
-- same reason and its header does not say why; this one does.
-- The `COMMIT` closes the empty transaction the runner opened (`BEGIN
-- IMMEDIATE` is the first line it prepends and nothing has run inside it
-- yet), because `PRAGMA foreign_keys` is a silent no-op inside a
-- transaction; the `BEGIN IMMEDIATE` reopens one immediately, so the rebuild,
-- every guard and the runner's own ledger row are still one all-or-nothing
-- transaction.  Nothing of this file's work happens outside it.
-- Guard 5's `pragma_foreign_key_check()` is what still holds while the
-- enforcement is off: it is an explicit check, not a constraint, so it
-- answers the same question whether or not the pragma is on.
COMMIT;
PRAGMA foreign_keys=OFF;
BEGIN IMMEDIATE;

-- The "before" pictures every guard is graded against, all read from the live
-- table inside the runner's own transaction, so none of them can describe a
-- different moment than the rebuild does.
CREATE TABLE _pf_mig017_rows_before AS SELECT * FROM characters;
CREATE TABLE _pf_mig017_ddl_before AS
    SELECT sql AS ddl FROM sqlite_master WHERE type='table' AND name='characters';
CREATE TABLE _pf_mig017_cols_before AS
    SELECT cid, name, type, "notnull", dflt_value, pk
      FROM pragma_table_info('characters');
CREATE TABLE _pf_mig017_idx_before AS
    SELECT name, sql FROM sqlite_master
     WHERE type='index' AND tbl_name='characters';
CREATE TABLE _pf_mig017_master_before AS
    SELECT type, name, tbl_name, sql FROM sqlite_master
     WHERE NOT (type='table' AND name='characters')
       AND name NOT LIKE '\_pf\_mig017\_%' ESCAPE '\';
-- Every table that references `characters`, plus the grandchild that hangs
-- off `character_backpacks`.  `009`'s list named four; three more have landed
-- since (`011` character_skills, `013` character_home_marker, `015`
-- character_equipment), and this file cascades, so a guard that silently
-- stopped watching new tables is exactly how a rebuild gets through.
-- `test_the_children_guard_names_every_table_that_references_characters`
-- derives this list from the schema so it cannot fall behind again.
CREATE TABLE _pf_mig017_children_before AS
    SELECT (SELECT COUNT(*) FROM character_positions)       AS positions,
           (SELECT COUNT(*) FROM character_backpacks)       AS backpacks,
           (SELECT COUNT(*) FROM character_backpack_items)  AS items,
           (SELECT COUNT(*) FROM character_skills)          AS skills,
           (SELECT COUNT(*) FROM character_home_marker)     AS homes,
           (SELECT COUNT(*) FROM character_equipment)       AS equipment,
           (SELECT COUNT(*) FROM sessions)                  AS sessions_;

-- THE REBUILD.  This declaration is `009`'s, character for character, with
-- `DEFAULT 0` inserted on `experience` and on `skill_points` and nothing else
-- touched -- including every CHECK range, every `REFERENCES`, and the order
-- of the columns, all of which guard 6 grades on the stored text.
CREATE TABLE characters_rebuild (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    selector INTEGER NOT NULL CHECK(selector BETWEEN 0 AND 255),
    name TEXT NOT NULL,
    actor_wire BLOB NOT NULL,
    avatar_wire BLOB NOT NULL,
    avatar_typed_json TEXT,
    identity_lo INTEGER NOT NULL,
    identity_hi INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    name_key TEXT NOT NULL DEFAULT '',
    create_fingerprint TEXT NOT NULL DEFAULT '',
    level INTEGER DEFAULT 1
        CHECK(level IS NULL OR (typeof(level)='integer' AND level BETWEEN 0 AND 65535)),
    hp_current INTEGER DEFAULT 100
        CHECK(hp_current IS NULL OR (typeof(hp_current)='integer' AND hp_current BETWEEN 0 AND 4294967295)),
    hp_max INTEGER DEFAULT 100
        CHECK(hp_max IS NULL OR (typeof(hp_max)='integer' AND hp_max BETWEEN 0 AND 4294967295)),
    mp_current INTEGER
        CHECK(mp_current IS NULL OR (typeof(mp_current)='integer' AND mp_current BETWEEN 0 AND 4294967295)),
    mp_max INTEGER
        CHECK(mp_max IS NULL OR (typeof(mp_max)='integer' AND mp_max BETWEEN 0 AND 4294967295)),
    speed_walk REAL DEFAULT 400.0
        CHECK(speed_walk IS NULL OR (typeof(speed_walk)='real' AND speed_walk BETWEEN -3.4028234663852886e38 AND 3.4028234663852886e38)),
    class_id INTEGER
        CHECK(class_id IS NULL OR (typeof(class_id)='integer' AND class_id BETWEEN 0 AND 4294967295)),
    skill_points INTEGER DEFAULT 0
        CHECK(skill_points IS NULL OR (typeof(skill_points)='integer' AND skill_points BETWEEN 0 AND 4294967295)),
    unspent_points INTEGER
        CHECK(unspent_points IS NULL OR (typeof(unspent_points)='integer' AND unspent_points BETWEEN 0 AND 65535)),
    stat_str INTEGER
        CHECK(stat_str IS NULL OR (typeof(stat_str)='integer' AND stat_str BETWEEN 0 AND 65535)),
    stat_con INTEGER
        CHECK(stat_con IS NULL OR (typeof(stat_con)='integer' AND stat_con BETWEEN 0 AND 65535)),
    stat_dex INTEGER
        CHECK(stat_dex IS NULL OR (typeof(stat_dex)='integer' AND stat_dex BETWEEN 0 AND 65535)),
    stat_int INTEGER
        CHECK(stat_int IS NULL OR (typeof(stat_int)='integer' AND stat_int BETWEEN 0 AND 65535)),
    stat_per INTEGER
        CHECK(stat_per IS NULL OR (typeof(stat_per)='integer' AND stat_per BETWEEN 0 AND 65535)),
    experience INTEGER DEFAULT 0
        CHECK(experience IS NULL OR (typeof(experience)='integer' AND experience BETWEEN 0 AND 9223372036854775807)),
    cash INTEGER
        CHECK(cash IS NULL OR (typeof(cash)='integer' AND cash BETWEEN 0 AND 9223372036854775807)),
    bonus_str INTEGER
        CHECK(bonus_str IS NULL OR (typeof(bonus_str)='integer' AND bonus_str BETWEEN 0 AND 65535)),
    bonus_con INTEGER
        CHECK(bonus_con IS NULL OR (typeof(bonus_con)='integer' AND bonus_con BETWEEN 0 AND 65535)),
    bonus_dex INTEGER
        CHECK(bonus_dex IS NULL OR (typeof(bonus_dex)='integer' AND bonus_dex BETWEEN 0 AND 65535)),
    bonus_int INTEGER
        CHECK(bonus_int IS NULL OR (typeof(bonus_int)='integer' AND bonus_int BETWEEN 0 AND 65535)),
    bonus_per INTEGER
        CHECK(bonus_per IS NULL OR (typeof(bonus_per)='integer' AND bonus_per BETWEEN 0 AND 65535))
);

-- Every column named on both sides, so a column added to one list and not the
-- other is a syntax error here rather than a silent NULL on the owner's rows.
-- `id` is copied explicitly: a rebuild that let SQLite reassign it would
-- leave every child row pointing at the wrong character, which guard 5's
-- orphan half is what catches.
INSERT INTO characters_rebuild
    (id,account_id,selector,name,actor_wire,avatar_wire,avatar_typed_json,
     identity_lo,identity_hi,created_at,updated_at,deleted_at,name_key,
     create_fingerprint,level,hp_current,hp_max,mp_current,mp_max,speed_walk,
     class_id,skill_points,unspent_points,stat_str,stat_con,stat_dex,stat_int,
     stat_per,experience,cash,bonus_str,bonus_con,bonus_dex,bonus_int,bonus_per)
    SELECT
     id,account_id,selector,name,actor_wire,avatar_wire,avatar_typed_json,
     identity_lo,identity_hi,created_at,updated_at,deleted_at,name_key,
     create_fingerprint,level,hp_current,hp_max,mp_current,mp_max,speed_walk,
     class_id,skill_points,unspent_points,stat_str,stat_con,stat_dex,stat_int,
     stat_per,experience,cash,bonus_str,bonus_con,bonus_dex,bonus_int,bonus_per
    FROM characters;

DROP TABLE characters;
ALTER TABLE characters_rebuild RENAME TO characters;

-- The four indexes of `004`, recreated with byte-identical text so guard 4
-- can compare `sqlite_master.sql` rather than a summary of it.
CREATE INDEX characters_active_name_lookup ON characters(name_key) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX characters_create_fingerprint ON characters(account_id, create_fingerprint) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX characters_active_selector ON characters(account_id, selector) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX characters_active_identity ON characters(identity_lo, identity_hi) WHERE deleted_at IS NULL;

-- -- THE GUARDS.  `CHECK(ok=1)` turns any 0 below into a failed INSERT, which
-- -- fails the whole script, which rolls the runner's transaction back: the
-- -- owner's table is either fully rebuilt and proved, or untouched.

-- 1. NO ROW APPEARED, DISAPPEARED, OR CHANGED IN ANY COLUMN -- including the
--    two this file gives a default, which is what makes "this is not a
--    backfill" a measurement.  `IS NOT` is the NULL-safe comparison, so a
--    row whose `experience` was NULL and holds 0 afterwards fails HERE.
--    `deleted_at` is in the list: a rebuild that lost a tombstone would
--    resurrect a deleted character into its account's selector list.
CREATE TABLE _pf_mig017_guard_rows(
    ok INTEGER NOT NULL
        CONSTRAINT guard_no_row_changed_in_any_column CHECK(ok=1));
INSERT INTO _pf_mig017_guard_rows(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM characters) = (SELECT COUNT(*) FROM _pf_mig017_rows_before)
    AND NOT EXISTS (SELECT 1 FROM _pf_mig017_rows_before b
                     WHERE NOT EXISTS (SELECT 1 FROM characters c WHERE c.id = b.id))
    AND NOT EXISTS (SELECT 1 FROM characters c
                     WHERE NOT EXISTS (SELECT 1 FROM _pf_mig017_rows_before b WHERE b.id = c.id))
    AND NOT EXISTS (
        SELECT 1 FROM characters c JOIN _pf_mig017_rows_before b ON b.id = c.id
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
            OR c.skill_points IS NOT b.skill_points
            OR c.unspent_points IS NOT b.unspent_points
            OR c.stat_str IS NOT b.stat_str
            OR c.stat_con IS NOT b.stat_con
            OR c.stat_dex IS NOT b.stat_dex
            OR c.stat_int IS NOT b.stat_int
            OR c.stat_per IS NOT b.stat_per
            OR c.experience IS NOT b.experience
            OR c.cash IS NOT b.cash
            OR c.bonus_str IS NOT b.bonus_str
            OR c.bonus_con IS NOT b.bonus_con
            OR c.bonus_dex IS NOT b.bonus_dex
            OR c.bonus_int IS NOT b.bonus_int
            OR c.bonus_per IS NOT b.bonus_per)
    THEN 1 ELSE 0 END;

-- 2. THE COLUMN LIST IS THE SAME LIST, in the same order, with the same
--    names, types, NOT NULLs and primary key -- and with the same DEFAULT on
--    every column except the two named here.  Guard 6 sees everything this
--    guard sees; this one runs first so the failure names the smallest true
--    reason instead of "the text differs".
CREATE TABLE _pf_mig017_guard_columns(
    ok INTEGER NOT NULL
        CONSTRAINT guard_the_column_list_is_unchanged CHECK(ok=1));
INSERT INTO _pf_mig017_guard_columns(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM pragma_table_info('characters'))
        = (SELECT COUNT(*) FROM _pf_mig017_cols_before)
    AND NOT EXISTS (
        SELECT 1 FROM pragma_table_info('characters') a
          JOIN _pf_mig017_cols_before b ON a.cid = b.cid
         WHERE a.name IS NOT b.name
            OR a.type IS NOT b.type
            OR a."notnull" IS NOT b."notnull"
            OR a.pk IS NOT b.pk
            OR (a.dflt_value IS NOT b.dflt_value
                AND a.name NOT IN ('experience','skill_points')))
    THEN 1 ELSE 0 END;

-- 3. EXACTLY TWO DEFAULTS WERE ADDED, THEY ARE THESE TWO COLUMNS, AND THEY
--    ARE 0.  The count is written as a RELATION (after = before + 2) rather
--    than as the absolute 7 and 9 this database happens to hold, so the guard
--    stays true if an earlier-numbered migration is ever added beneath it;
--    and both columns are checked to have held NO default before, so a file
--    that "adds" a default a column already had -- and quietly drops one
--    elsewhere to keep the count -- fails here rather than balancing out.
CREATE TABLE _pf_mig017_guard_defaults(
    ok INTEGER NOT NULL
        CONSTRAINT guard_exactly_the_two_defaults_were_added CHECK(ok=1));
INSERT INTO _pf_mig017_guard_defaults(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM pragma_table_info('characters')
      WHERE (name='experience' AND dflt_value='0')
         OR (name='skill_points' AND dflt_value='0')) = 2
    AND (SELECT COUNT(*) FROM _pf_mig017_cols_before
          WHERE name IN ('experience','skill_points')
            AND dflt_value IS NOT NULL) = 0
    AND (SELECT COUNT(*) FROM pragma_table_info('characters')
          WHERE dflt_value IS NOT NULL)
        = (SELECT COUNT(*) FROM _pf_mig017_cols_before
            WHERE dflt_value IS NOT NULL) + 2
    THEN 1 ELSE 0 END;

-- 4. EVERY INDEX CAME BACK, with the same name and the same text.  Lose
--    `characters_active_selector` and two live characters share a slot; lose
--    `characters_create_fingerprint` and a retransmitted create packet makes
--    a second character instead of returning the first.  Both are PARTIAL
--    indexes (`WHERE deleted_at IS NULL`); a rebuild that recreated them
--    without the predicate would leave a soft-deleted row holding its
--    selector forever, and comparing the stored text is what sees that.
CREATE TABLE _pf_mig017_guard_indexes(
    ok INTEGER NOT NULL
        CONSTRAINT guard_every_index_came_back CHECK(ok=1));
INSERT INTO _pf_mig017_guard_indexes(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM sqlite_master
      WHERE type='index' AND tbl_name='characters')
        = (SELECT COUNT(*) FROM _pf_mig017_idx_before)
    AND NOT EXISTS (
        SELECT 1 FROM _pf_mig017_idx_before b
         WHERE NOT EXISTS (
            SELECT 1 FROM sqlite_master m
             WHERE m.type='index' AND m.tbl_name='characters'
               AND m.name = b.name AND m.sql IS b.sql))
    THEN 1 ELSE 0 END;

-- 5. THE CHILDREN ARE STILL THERE.  Counting SURVIVORS, which is not the
--    sentence "nothing is orphaned": with `PRAGMA foreign_keys` ON, the
--    `DROP TABLE characters` above cascade-deletes every child row, and
--    afterwards nothing is orphaned because nothing is left.  The orphan
--    check is kept beside the counts because it catches the other direction
--    -- a rebuild that renumbers `id` -- which counting cannot see.
CREATE TABLE _pf_mig017_guard_children(
    ok INTEGER NOT NULL
        CONSTRAINT guard_the_child_rows_all_survived CHECK(ok=1));
INSERT INTO _pf_mig017_guard_children(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM character_positions)
        = (SELECT positions FROM _pf_mig017_children_before)
    AND (SELECT COUNT(*) FROM character_backpacks)
        = (SELECT backpacks FROM _pf_mig017_children_before)
    AND (SELECT COUNT(*) FROM character_backpack_items)
        = (SELECT items FROM _pf_mig017_children_before)
    AND (SELECT COUNT(*) FROM character_skills)
        = (SELECT skills FROM _pf_mig017_children_before)
    AND (SELECT COUNT(*) FROM character_home_marker)
        = (SELECT homes FROM _pf_mig017_children_before)
    AND (SELECT COUNT(*) FROM character_equipment)
        = (SELECT equipment FROM _pf_mig017_children_before)
    AND (SELECT COUNT(*) FROM sessions)
        = (SELECT sessions_ FROM _pf_mig017_children_before)
    AND (SELECT COUNT(*) FROM pragma_foreign_key_check()) = 0
    THEN 1 ELSE 0 END;

-- 6. THE WHOLE TABLE DECLARATION -- the catch-all the five above cannot
--    replace.  Whitespace is removed from both sides (the rebuild legitimately
--    reflows the text) and the two DEFAULT clauses this file adds are
--    subtracted from the after-side BY COLUMN NAME, for the reason the header
--    gives: `identity_hi` already carries `DEFAULT 0`, so a bare
--    `replace('DEFAULT0','')` would hide the loss of a default this file must
--    not touch.  A CHECK constraint, a `REFERENCES` clause, a `COLLATE`, a
--    widened range or a renamed constraint all change this text and none of
--    them changes `pragma_table_info`.
CREATE TABLE _pf_mig017_guard_ddl(
    ok INTEGER NOT NULL
        CONSTRAINT guard_the_table_declaration_is_unchanged CHECK(ok=1));
INSERT INTO _pf_mig017_guard_ddl(ok) SELECT CASE WHEN
    replace(replace(
        replace(replace(replace(replace(
            (SELECT sql FROM sqlite_master
              WHERE type='table' AND name='characters'),
            ' ', ''), char(10), ''), char(9), ''), char(13), ''),
        'experienceINTEGERDEFAULT0', 'experienceINTEGER'),
        'skill_pointsINTEGERDEFAULT0', 'skill_pointsINTEGER')
    = replace(replace(replace(replace(
        (SELECT ddl FROM _pf_mig017_ddl_before),
        ' ', ''), char(10), ''), char(9), ''), char(13), '')
    THEN 1 ELSE 0 END;

-- 7. EVERY OTHER OBJECT IN THE DATABASE IS BYTE-IDENTICAL, by name and by
--    stored SQL: the four indexes this file recreates, and also any trigger
--    or view on `characters`, which a rebuild destroys silently and which no
--    per-column check can see.  `schema_migrations` is excluded because the
--    runner inserts this file's own ledger row inside this transaction -- a
--    row, not a schema change.  The `_pf_mig017_*` scratch tables are
--    excluded on both sides because they exist only between the first
--    statement of this transaction and the last, which is what
--    `test_no_scratch_table_of_this_migration_survives` proves.
CREATE TABLE _pf_mig017_guard_other_objects(
    ok INTEGER NOT NULL
        CONSTRAINT guard_every_other_object_is_unchanged CHECK(ok=1));
INSERT INTO _pf_mig017_guard_other_objects(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM sqlite_master
      WHERE NOT (type='table' AND name='characters')
        AND name NOT LIKE '\_pf\_mig017\_%' ESCAPE '\')
        = (SELECT COUNT(*) FROM _pf_mig017_master_before)
    AND NOT EXISTS (
        SELECT 1 FROM _pf_mig017_master_before b
         WHERE NOT EXISTS (
            SELECT 1 FROM sqlite_master m
             WHERE m.type IS b.type AND m.name IS b.name
               AND m.tbl_name IS b.tbl_name AND m.sql IS b.sql))
    THEN 1 ELSE 0 END;

DROP TABLE _pf_mig017_guard_other_objects;
DROP TABLE _pf_mig017_guard_ddl;
DROP TABLE _pf_mig017_guard_children;
DROP TABLE _pf_mig017_guard_indexes;
DROP TABLE _pf_mig017_guard_defaults;
DROP TABLE _pf_mig017_guard_columns;
DROP TABLE _pf_mig017_guard_rows;
DROP TABLE _pf_mig017_children_before;
DROP TABLE _pf_mig017_master_before;
DROP TABLE _pf_mig017_idx_before;
DROP TABLE _pf_mig017_cols_before;
DROP TABLE _pf_mig017_ddl_before;
DROP TABLE _pf_mig017_rows_before;
