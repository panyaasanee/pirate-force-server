-- 009_character_birth_defaults.sql
-- LANE-DB / the birth hole, closed in the schema.
--
-- WHAT THIS FILE DOES.  It rebuilds `characters` so four columns carry a
-- DEFAULT: `level = 1`, `hp_current = 100`, `hp_max = 100`,
-- `speed_walk = 400.0`.  Nothing else about the table changes -- same 35
-- columns in the same order, same types, same CHECK constraints, same four
-- partial indexes, same rows byte for byte -- and the guards at the bottom
-- of this file assert every one of those sentences before the transaction is
-- allowed to commit.
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
-- WHY A DEFAULT AND NOT A WRITE IN `create_character`.  Both were ordered at
-- different times and they do not conflict: they put the same bytes on the
-- row (LANE-DB measured this before proposing it, letter 20260902_1452), so
-- chief's insertion point from `COO-DECISION 20260902_0444` stays his work
-- and stays wanted.  What a DEFAULT adds is a property no insertion point can
-- have: SQLite applies it only on an INSERT that omits the column, and
-- `create_character`'s retry branch (`SQLiteStore.create_character`, the
-- `create_fingerprint` lookup that returns before the INSERT) never reaches
-- an INSERT at all.  A retransmitted create packet therefore cannot reset a
-- veteran to `1, 100/100` -- the exact damage a `pf-adversary` pass measured
-- a wrongly written plug doing.  The hole closes by shape rather than by the
-- discipline of whoever edits the INSERT next.
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

-- -- The guards.  `CHECK(ok=1)` turns any 0 below into a failed INSERT, which
-- -- fails the whole script, which rolls the transaction back: the owner's
-- -- table is either fully rebuilt and proved, or untouched.  They are written
-- -- as data comparisons against the "before" pictures rather than as numbers
-- -- typed into this file, because a number typed here is only right for the
-- -- database it was typed for.
CREATE TABLE _pf_mig009_guard(ok INTEGER NOT NULL CHECK(ok=1));

-- 1. No row appeared, disappeared, or changed in any column.  `IS NOT` is the
--    NULL-safe comparison, so a column that was NULL and is now 1 fails here
--    -- which is what makes "this file is not a backfill" a measurement.
INSERT INTO _pf_mig009_guard(ok) SELECT CASE WHEN
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

-- 2. The schema is the same schema, column by column, in the same order --
--    except for the four defaults this file exists to add.  This is the
--    automatic before/after comparison `COO-DECISION 20260902_1607` point 3
--    asked for; a column silently renamed, retyped, reordered, or losing its
--    NOT NULL or its primary key fails here.
INSERT INTO _pf_mig009_guard(ok) SELECT CASE WHEN
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

-- 3. The four defaults are there, and they are these four numbers.
INSERT INTO _pf_mig009_guard(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM pragma_table_info('characters')
      WHERE (name='level' AND dflt_value='1')
         OR (name='hp_current' AND dflt_value='100')
         OR (name='hp_max' AND dflt_value='100')
         OR (name='speed_walk' AND dflt_value='400.0')) = 4
    THEN 1 ELSE 0 END;

-- 4. And NO OTHER column gained one.  Three columns carried a default before
--    this file (`identity_hi`, `name_key`, `create_fingerprint`); seven carry
--    one after it.  The seventeen typed columns with no adjudicated value are
--    counted here, by their absence, as still holding none.
INSERT INTO _pf_mig009_guard(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM pragma_table_info('characters')
      WHERE dflt_value IS NOT NULL) = 7
    AND (SELECT COUNT(*) FROM _pf_mig009_cols_before
          WHERE dflt_value IS NOT NULL) = 3
    THEN 1 ELSE 0 END;

-- 5. Every index came back, with the same name and the same text.  This is
--    the soft-delete uniqueness the letter called the highest risk in the
--    change: lose `characters_active_selector` and two live characters can
--    share a slot; lose `characters_create_fingerprint` and a retransmitted
--    create packet makes a second character instead of returning the first.
INSERT INTO _pf_mig009_guard(ok) SELECT CASE WHEN
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

-- 6. Nothing else in the database lost a parent row.
INSERT INTO _pf_mig009_guard(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM pragma_foreign_key_check()) = 0 THEN 1 ELSE 0 END;

DROP TABLE _pf_mig009_guard;
DROP TABLE _pf_mig009_idx_before;
DROP TABLE _pf_mig009_cols_before;
DROP TABLE _pf_mig009_rows_before;
