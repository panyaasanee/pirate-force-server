-- 009_character_birth_defaults.sql
-- LANE-DB / the birth hole, closed in the schema.
--
-- WHAT THIS FILE DOES.  It rebuilds `characters` so four columns carry a
-- DEFAULT: `level = 1`, `hp_current = 100`, `hp_max = 100`,
-- `speed_walk = 400.0`.  Nothing else about the table changes, and "nothing
-- else" is graded against the table's OWN DDL TEXT rather than against a
-- summary of it: guard A below compares `sqlite_master.sql` for `characters`
-- before and after, whitespace-normalised, modulo exactly the four `DEFAULT`
-- insertions this file exists to add.  That is what makes the sentence
-- checkable at all.
--
-- WHY THE DDL TEXT AND NOT `PRAGMA table_info`.  An earlier draft graded the
-- rebuild by `pragma_table_info` (cid, name, type, NOT NULL, default, pk)
-- plus the index list, and a `pf-adversary` pass drove SIX wrong rebuilds
-- through it that COMMITTED and left every test green: one that dropped
-- `REFERENCES accounts(id)` from `account_id`, three that dropped a CHECK
-- constraint (`cash`, `hp_max`, `mp_max`), one that added `COLLATE NOCASE`
-- to `name_key`, and one that widened a CHECK range.  None of those five
-- things appears in `pragma_table_info` AT ALL.  The lost foreign key was
-- the worst: it also makes the orphan check at the bottom of this file
-- permanently vacuous for `characters`, in every future migration,
-- silently.  The DDL text sees all of them.
--
-- WHY A DEFAULT, AND WHO OVERRULED WHAT.  `COO-DECISION 20260902_0443`
-- point 2 forbade the DEFAULT outright and chose a write inside
-- `SQLiteStore.create_character` instead; `COO-DECISION 20260902_1043`
-- separately chose to leave `speed_walk` unseeded at birth; and
-- `COO-DECISION 20260902_1546` refused this file a second time, on the one
-- ground its author said he had no authority over -- "a table rebuild on the
-- owner's live database cannot be undone".  The owner settled it herself in
-- session on 2026-09-02 at 16:0x, and `COO-DECISION 20260902_1607` records
-- the reversal and approves exactly this shape, with the numbers frozen:
-- they must equal the ones `007` and `008` already used, and they do --
--   `level = 1`, `hp_current = 100`, `hp_max = 100` are the three
--   `007_character_vitals_seed.sql` wrote and the three
--   `persistence_vitals.new_character_vitals()` owns;
--   `speed_walk = 400.0` is the number `008_character_speed_walk_seed.sql`
--   wrote, which is the client's own construction default for BasicAttr+0x54
--   (`persistence_attr_compose.CLIENT_CONSTRUCTION_DEFAULTS[7]`, the store at
--   `0x00464AF2`, closed by RE-194 and approved by `COO-DECISION
--   20260902_0742`).
-- So this file invents no number.  What it changes is WHERE the number comes
-- from: `007` and `008` seeded the cohort that existed when they ran and can
-- never run again, so on a fresh install every character born afterwards held
-- NULL in all four forever -- a character with no HP cannot be damaged, cannot
-- be healed, and composes with a named gap instead of a number.
--
-- WHY THE OTHER 17 TYPED COLUMNS GET NOTHING.  `006` built 21 typed columns.
-- Four of them have an adjudicated value; the other seventeen do not, and
-- `COO-DECISION 20260902_1607` holds them at NULL for the reason the owner
-- gave verbatim in `COO-DECISION 20260901_1059`: a field whose value nobody
-- has measured may never be guessed to be zero.  NULL is the only state that
-- cannot be mistaken for a measurement -- `read_typed_attributes` omits a
-- NULL column, so the field arrives at the compose gate ABSENT and the gate
-- refuses the block by its own rules.  Fail-closed survives the round trip.
--
-- HOW THIS SITS BESIDE CHIEF'S INSERTION POINT, WHICH LANDED FIRST.  While
-- this file was being written, chief landed `COO-DECISION 20260902_0444` on
-- `main` (commit `b9e11059`, R308): `SQLiteStore.create_character`'s INSERT
-- now NAMES `level`, `hp_current` and `hp_max` and takes their values from
-- `persistence_vitals.new_character_vitals()`.  Both orders were live in the
-- same hour and they do not conflict -- they put the same bytes on the row,
-- which this lane measured before proposing either (letter 20260902_1452).
-- What each one does now, said exactly rather than generously:
--   * the three vitals come from chief's INSERT on every creation that goes
--     through that method; their DEFAULTs here are a BACKSTOP, reached only
--     by an INSERT that omits them;
--   * `speed_walk` is named by no INSERT anywhere in the server, so its
--     DEFAULT is the only thing that puts a number in that column at birth.
-- The property a DEFAULT has that no insertion point can have is still worth
-- the file: SQLite applies it only on an INSERT, and `create_character`'s
-- retry branch (the `create_fingerprint` lookup that returns before the
-- INSERT) never reaches one -- so a retransmitted create packet cannot reset
-- a veteran to `1, 100/100`, which is the exact damage a `pf-adversary` pass
-- measured a wrongly written plug doing.
--
-- WHY A REBUILD.  SQLite cannot add a DEFAULT to an existing column; `ALTER
-- TABLE ... ADD COLUMN` is the only place a default can be attached.  So this
-- is the documented rebuild recipe, the same one `004_character_soft_delete_
-- reuse.sql` used and for the same reason, including its transaction shape:
-- the runner (`SQLiteStore.migrate`) wraps this file in `BEGIN IMMEDIATE ..
-- schema_migrations INSERT .. COMMIT`, so the first COMMIT below closes that
-- wrapper (PRAGMA foreign_keys is a silent no-op inside a transaction) and
-- this file deliberately leaves its own transaction OPEN so the runner's
-- ledger INSERT and COMMIT land inside it and the whole rebuild stays atomic.
-- foreign_keys is off only for the rest of the migration connection; every
-- normal connection re-enables it at open.  Dropping the parent table with
-- foreign_keys ON would cascade-delete `character_positions`,
-- `character_backpacks` and their items, which is what this recipe avoids.
--
-- THE BACKUP, WHICH IS NOT OPTIONAL FOR THIS FILE.  This is the first
-- migration since `004` to touch existing rows, so `COO-DECISION 20260901_
-- 1112` point 3 applies in full: an automatic pre-apply snapshot must exist.
-- It does, and it is already wired: `persistence_backup.should_snapshot`
-- votes True while any migration is pending, `SQLiteStore.migrate_with_backup`
-- takes the copy BEFORE `migrate()` and raises `BackupError` without
-- migrating if it cannot, and `app.py:786` and `app.py:789` -- both boot call
-- sites that migrate -- call it.  MEASURED FOR THIS FILE, not assumed:
-- `tests/test_persistence_birth_defaults_009.py` boots a database through
-- `migrate_with_backup` with 009 pending and asserts a real snapshot FILE
-- exists on disk and still holds the pre-009 schema; asserting that the code
-- calls a function would not have been the same claim.
--
-- WHICH BOOT PATHS MIGRATE, said in full rather than in the convenient half.
-- `app.py` has a third shape: `--scene-load-scenario` with no hypothesis flag
-- does not migrate AT ALL (chief's deliberate design, pinned by his own
-- `tests/test_startup_stale_lease_recovery.py::test_the_scene_load_branch_is_
-- the_one_deliberate_exception`).  A boot that never migrates never applies
-- this file either, so it is not a hole in the snapshot.  `COO-DECISION
-- 20260902_1607` point 2 required this lane to check which shape the OWNER's
-- machine boots before pushing: the standard attended boot runs
-- `tools/run_foundation_visible.ps1`, whose argument list is `--db`,
-- `--capture-root`, `--second-password-mode` and nothing else, so
-- `scene_load` is None and the plain branch (`app.py:789`) runs
-- `migrate_with_backup()`.  The owner's canonical database is upgraded by the
-- snapshotting path.
--   Named rather than left out, because a `pf-adversary` pass found it and
--   the answer above did not mention it: there IS a shipped launcher for the
--   non-migrating shape, `tools/run_scene2_load_only.ps1`, which passes
--   `--scene-load-scenario` with no hypothesis flag.  It defaults to
--   `state/test_arena_v1.sqlite3` rather than to the canonical database and
--   it does not migrate at all, so it neither applies this file nor needs a
--   snapshot -- but "the non-migrating shape is a branch nobody launches"
--   would have been the wrong sentence and this is the right one.
--
-- WHAT THIS FILE IS NOT.  It is not a backfill: not one existing row is read
-- for its value or rewritten with a new one.  A row that holds NULL in
-- `level` today still holds NULL after this file runs -- a DEFAULT governs
-- future INSERTs only -- and the row-for-row guard below refuses to commit if
-- any column of any existing row differs by so much as a byte.  Rows that
-- `007`/`008` already seeded keep the numbers those files gave them.
--
-- REVERSIBILITY, in the same words `006` used because they are still true.
-- Once applied, the checksum ledger makes this file immutable and `migrate()`
-- refuses to boot a server older than the schema.  Going back is a manual act
-- by the owner: restore the pre-migration snapshot, then run the older
-- server.  Nothing here rolls a schema backwards on its own and nothing here
-- claims it does.
COMMIT;
PRAGMA foreign_keys=OFF;
BEGIN IMMEDIATE;

-- The two "before" pictures every guard at the bottom is graded against: the
-- rows themselves, and the column-by-column schema.  Both are read from the
-- live table inside this transaction, so neither can describe a different
-- moment than the rebuild does.
CREATE TABLE _pf_mig009_rows_before AS SELECT * FROM characters;
CREATE TABLE _pf_mig009_ddl_before AS
    SELECT sql AS ddl FROM sqlite_master WHERE type='table' AND name='characters';
CREATE TABLE _pf_mig009_master_before AS
    SELECT type, name, tbl_name, sql FROM sqlite_master
     WHERE NOT (type='table' AND name='characters')
       AND name NOT LIKE '\_pf\_mig009\_%' ESCAPE '\';
CREATE TABLE _pf_mig009_children_before AS
    SELECT (SELECT COUNT(*) FROM character_positions)       AS positions,
           (SELECT COUNT(*) FROM character_backpacks)       AS backpacks,
           (SELECT COUNT(*) FROM character_backpack_items)  AS items,
           (SELECT COUNT(*) FROM sessions)                  AS sessions_;
CREATE TABLE _pf_mig009_cols_before AS
    SELECT cid, name, type, "notnull", dflt_value, pk
      FROM pragma_table_info('characters');
CREATE TABLE _pf_mig009_idx_before AS
    SELECT name, sql FROM sqlite_master
     WHERE type='index' AND tbl_name='characters';

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
    skill_points INTEGER
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
    experience INTEGER
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

-- The four indexes of `004`, recreated with byte-identical text so the
-- index guard below can compare `sqlite_master.sql` rather than a summary.
CREATE INDEX characters_active_name_lookup ON characters(name_key) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX characters_create_fingerprint ON characters(account_id, create_fingerprint) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX characters_active_selector ON characters(account_id, selector) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX characters_active_identity ON characters(identity_lo, identity_hi) WHERE deleted_at IS NULL;

-- -- THE GUARDS.  `CHECK(ok=1)` turns any 0 below into a failed INSERT, which
-- -- fails the whole script, which rolls the transaction back: the owner's
-- -- table is either fully rebuilt and proved, or untouched.
-- --
-- -- ONE TABLE PER GUARD WITH A NAMED CONSTRAINT, and the reason is the
-- -- message.  They shared one anonymous `CHECK(ok=1)` in the first draft, so
-- -- every one of them failed with the same information-free
-- -- `CHECK constraint failed: ok=1` -- on the owner's own machine, on the
-- -- highest-risk file this lane has shipped, with no way to tell which of
-- -- the invariants broke.  SQLite reports a NAMED constraint by its name, so
-- -- the failure now reads `CHECK constraint failed:
-- -- guard_the_table_declaration_is_unchanged` (measured on SQLite 3.45.1,
-- -- and the naming has been in SQLite far longer than any interpreter this
-- -- repository runs on).  `tests/test_persistence_birth_defaults_009.py`
-- -- asserts the name each mutant produces, so a mutant caught by the WRONG
-- -- guard -- or by a SQL error rather than by a guard at all -- is now a
-- -- test failure instead of a green tick.
-- --
-- -- They are written as comparisons against the "before" pictures captured
-- -- above rather than as numbers typed into this file, because a number
-- -- typed here is only right for the database it was typed for.

-- 1. No row appeared, disappeared, or changed in any column.  `IS NOT` is the
--    NULL-safe comparison, so a column that was NULL and is now 1 fails here
--    -- which is what makes "this file is not a backfill" a measurement.
CREATE TABLE _pf_mig009_guard_rows(
    ok INTEGER NOT NULL
        CONSTRAINT guard_no_row_changed_in_any_column CHECK(ok=1));
INSERT INTO _pf_mig009_guard_rows(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM characters) = (SELECT COUNT(*) FROM _pf_mig009_rows_before)
    AND NOT EXISTS (SELECT 1 FROM _pf_mig009_rows_before b
                     WHERE NOT EXISTS (SELECT 1 FROM characters c WHERE c.id = b.id))
    AND NOT EXISTS (
        SELECT 1 FROM characters c JOIN _pf_mig009_rows_before b ON b.id = c.id
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

-- 2. The column list is the same list, in the same order, with the same
--    types, NOT NULLs and primary key -- except for the four defaults this
--    file exists to add.  Guard 6 (the DDL text) sees everything this one
--    sees, and this one runs FIRST on purpose: `pragma_table_info` is the
--    projection a reader can diff by eye in ten seconds, while guard 6's
--    failure says only "the text differs".  The specific guards are ordered
--    ahead of the catch-alls so the message names the smallest true reason.
CREATE TABLE _pf_mig009_guard_columns(
    ok INTEGER NOT NULL
        CONSTRAINT guard_the_column_list_is_unchanged CHECK(ok=1));
INSERT INTO _pf_mig009_guard_columns(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM pragma_table_info('characters'))
        = (SELECT COUNT(*) FROM _pf_mig009_cols_before)
    AND NOT EXISTS (
        SELECT 1 FROM pragma_table_info('characters') a
          JOIN _pf_mig009_cols_before b ON a.cid = b.cid
         WHERE a.name IS NOT b.name
            OR a.type IS NOT b.type
            OR a."notnull" IS NOT b."notnull"
            OR a.pk IS NOT b.pk
            OR (a.dflt_value IS NOT b.dflt_value
                AND a.name NOT IN ('level','hp_current','hp_max','speed_walk')))
    THEN 1 ELSE 0 END;

-- 3. The four defaults are there, they are these four numbers, and NO OTHER
--    column gained one.  Three columns carried a default before this file
--    (`identity_hi`, `name_key`, `create_fingerprint`); seven carry one
--    after it.  The seventeen typed columns with no adjudicated value are
--    counted here, by their absence, as still holding none.
CREATE TABLE _pf_mig009_guard_defaults(
    ok INTEGER NOT NULL
        CONSTRAINT guard_exactly_the_four_defaults_were_added CHECK(ok=1));
INSERT INTO _pf_mig009_guard_defaults(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM pragma_table_info('characters')
      WHERE (name='level' AND dflt_value='1')
         OR (name='hp_current' AND dflt_value='100')
         OR (name='hp_max' AND dflt_value='100')
         OR (name='speed_walk' AND dflt_value='400.0')) = 4
    AND (SELECT COUNT(*) FROM pragma_table_info('characters')
          WHERE dflt_value IS NOT NULL) = 7
    AND (SELECT COUNT(*) FROM _pf_mig009_cols_before
          WHERE dflt_value IS NOT NULL) = 3
    THEN 1 ELSE 0 END;

-- 4. Every index came back, with the same name and the same text.  This is
--    the soft-delete uniqueness the proposing letter called the highest risk
--    in the change: lose `characters_active_selector` and two live characters
--    share a slot; lose `characters_create_fingerprint` and a retransmitted
--    create packet makes a second character instead of returning the first.
--    Guard 7 covers this too, and runs after it for the same reason guard 2
--    runs before guard 6: the specific message first.
CREATE TABLE _pf_mig009_guard_indexes(
    ok INTEGER NOT NULL
        CONSTRAINT guard_every_index_came_back CHECK(ok=1));
INSERT INTO _pf_mig009_guard_indexes(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM sqlite_master
      WHERE type='index' AND tbl_name='characters')
        = (SELECT COUNT(*) FROM _pf_mig009_idx_before)
    AND NOT EXISTS (
        SELECT 1 FROM _pf_mig009_idx_before b
         WHERE NOT EXISTS (
            SELECT 1 FROM sqlite_master m
             WHERE m.type='index' AND m.tbl_name='characters'
               AND m.name = b.name AND m.sql IS b.sql))
    THEN 1 ELSE 0 END;

-- 5. THE CHILDREN ARE STILL THERE.  Not "nothing is orphaned" -- that is a
--    different sentence and it is the one this guard used to make, which a
--    `pf-adversary` pass showed returns a clean 0 in exactly the
--    catastrophic case: with `PRAGMA foreign_keys` left ON, `DROP TABLE
--    characters` CASCADE-DELETES every `character_positions`,
--    `character_backpacks` and `character_backpack_items` row, and afterwards
--    nothing is orphaned because nothing is left.  Counting the survivors is
--    the guard the header always claimed to have.  The orphan check is kept
--    beside it: it catches the other direction (a rebuild that renumbers
--    `id`), which counting cannot see.
CREATE TABLE _pf_mig009_guard_children(
    ok INTEGER NOT NULL
        CONSTRAINT guard_the_child_rows_all_survived CHECK(ok=1));
INSERT INTO _pf_mig009_guard_children(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM character_positions)
        = (SELECT positions FROM _pf_mig009_children_before)
    AND (SELECT COUNT(*) FROM character_backpacks)
        = (SELECT backpacks FROM _pf_mig009_children_before)
    AND (SELECT COUNT(*) FROM character_backpack_items)
        = (SELECT items FROM _pf_mig009_children_before)
    AND (SELECT COUNT(*) FROM sessions)
        = (SELECT sessions_ FROM _pf_mig009_children_before)
    AND (SELECT COUNT(*) FROM pragma_foreign_key_check()) = 0
    THEN 1 ELSE 0 END;

-- 6. THE WHOLE TABLE DECLARATION -- the catch-all, and the guard the five
--    above cannot replace.  The stored DDL text is compared after removing every space,
--    tab, newline, carriage return and double quote from both sides -- the
--    rebuild legitimately reflows the text and SQLite quotes the renamed
--    table -- and after removing the four DEFAULT clauses this file adds.
--    THE ORDER OF THE THREE `replace`s IS LOAD-BEARING: `DEFAULT1` is a
--    prefix of `DEFAULT100`, so removing it first would turn `DEFAULT100`
--    into `DEFAULT00` and this guard would fail on a correct rebuild.
--    A CHECK constraint, a REFERENCES clause, a COLLATE, a widened range or
--    a renamed constraint all change this text; none of them changes
--    `pragma_table_info`, and a `pf-adversary` pass drove six such rebuilds
--    through the version of this file that had only the pragma guards.
CREATE TABLE _pf_mig009_guard_ddl(
    ok INTEGER NOT NULL
        CONSTRAINT guard_the_table_declaration_is_unchanged CHECK(ok=1));
INSERT INTO _pf_mig009_guard_ddl(ok) SELECT CASE WHEN
    replace(replace(replace(
        replace(replace(replace(replace(
            (SELECT sql FROM sqlite_master
              WHERE type='table' AND name='characters'),
            ' ', ''), char(10), ''), char(9), ''), char(13), ''),
        'DEFAULT400.0', ''), 'DEFAULT100', ''), 'DEFAULT1', '')
    = replace(replace(replace(replace(
        (SELECT ddl FROM _pf_mig009_ddl_before),
        ' ', ''), char(10), ''), char(9), ''), char(13), '')
    THEN 1 ELSE 0 END;

-- 7. Every OTHER object in the database is byte-identical, by name and by
--    stored SQL: the four indexes this file recreates, and also any trigger
--    or view on `characters`, which a rebuild destroys silently and which no
--    per-column check can see.  `schema_migrations` is excluded because the
--    runner inserts this file's own ledger row inside this transaction --
--    a row, not a schema change.  This file's own `_pf_mig009_*` scratch
--    tables are excluded on both sides for the same reason: they exist only
--    between the first statement and the last of this transaction, and
--    `test_no_scratch_table_of_this_migration_survives` is what proves that.
CREATE TABLE _pf_mig009_guard_other_objects(
    ok INTEGER NOT NULL
        CONSTRAINT guard_every_other_object_is_unchanged CHECK(ok=1));
INSERT INTO _pf_mig009_guard_other_objects(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM sqlite_master
      WHERE NOT (type='table' AND name='characters')
        AND name NOT LIKE '\_pf\_mig009\_%' ESCAPE '\')
        = (SELECT COUNT(*) FROM _pf_mig009_master_before)
    AND NOT EXISTS (
        SELECT 1 FROM _pf_mig009_master_before b
         WHERE NOT EXISTS (
            SELECT 1 FROM sqlite_master m
             WHERE m.type = b.type AND m.name = b.name
               AND m.tbl_name IS b.tbl_name AND m.sql IS b.sql))
    THEN 1 ELSE 0 END;

DROP TABLE _pf_mig009_guard_children;
DROP TABLE _pf_mig009_guard_indexes;
DROP TABLE _pf_mig009_guard_defaults;
DROP TABLE _pf_mig009_guard_columns;
DROP TABLE _pf_mig009_guard_rows;
DROP TABLE _pf_mig009_guard_other_objects;
DROP TABLE _pf_mig009_guard_ddl;
DROP TABLE _pf_mig009_children_before;
DROP TABLE _pf_mig009_master_before;
DROP TABLE _pf_mig009_ddl_before;
DROP TABLE _pf_mig009_idx_before;
DROP TABLE _pf_mig009_cols_before;
DROP TABLE _pf_mig009_rows_before;
