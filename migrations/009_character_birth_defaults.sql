-- 009_character_birth_defaults.sql
-- LANE-DB.  The four columns a character is born holding get a DEFAULT, so a
-- character created on a FRESH INSTALL is born with them instead of with NULL.
--
-- WHOSE DECISION THIS IS, AND WHICH ONE IT REPLACES.  `COO-DECISION
-- 20260902_0443` point 2 forbade exactly this file: it chose a write at
-- character creation over a DEFAULT, because a DEFAULT means rebuilding the
-- table.  `COO-DECISION 20260902_1546` then refused a rebuild outright.  Both
-- were overruled by the project owner in person on 2026-09-02 at 16:0x +07:00,
-- relayed as `COO-DECISION 20260902_1607` ("Panya overrules 1546: migration
-- 009 with defaults is approved"), which also fixes the four numbers and
-- forbids changing them:
--
--     level = 1 . hp_current = 100 . hp_max = 100 . speed_walk = 400.0
--
-- They are not new numbers and they are not guessed here.  Each is the number
-- the migration that seeded the EXISTING rows already used, so a character
-- born after this file holds exactly what a character born before it was
-- backfilled to: `007_character_vitals_seed.sql` (level 1, hp 100/100) and
-- `008_character_speed_walk_seed.sql` (speed_walk 400.0, itself the client's
-- own `BasicAttr@0x54` default measured in
-- `pf_bridge/notes_to_chief/reference_codex_attr/`).
--
-- THE OTHER SEVENTEEN TYPED COLUMNS GET NO DEFAULT, and that is the whole
-- point of the file rather than an omission.  `COO-DECISION 20260901_1059`
-- (the owner, verbatim) forbids sending a block in which a field nobody knows
-- is guessed as zero, and `store.read_typed_attributes` implements that by
-- OMITTING a NULL column so `persistence_attr_compose` reports a named gap.
-- A DEFAULT of 0 on `class_id`, `experience`, `cash`, the five stats or the
-- five bonuses would turn every one of those honest gaps into a confident
-- wrong number, silently, for every character ever created afterwards.  They
-- stay NULL until something measures them.  `COO-DECISION 20260902_1607`
-- states this in the same sentence that approves the four.
--
-- WHY A TABLE REBUILD.  SQLite cannot add a DEFAULT to an existing column;
-- `ALTER TABLE ... ADD COLUMN` is the only place it accepts one.  The recipe
-- is the documented one and it is deliberately the same recipe, statement for
-- statement, as `004_character_soft_delete_reuse.sql` already ran on this same
-- table -- including the transaction shape described in that file's header
-- (the leading COMMIT closes the runner's wrapper so `PRAGMA foreign_keys`
-- can take effect at all, and this file leaves its own transaction OPEN so
-- the runner's `schema_migrations` INSERT and COMMIT land inside it and the
-- whole rebuild is atomic).  Dropping the parent table with foreign_keys ON
-- would cascade-delete `character_positions` and the backpack rows.
--
-- THE BACKUP THIS FILE DEPENDS ON IS ALREADY IN.  The owner's rule
-- (`COO-DECISION 20260901_1112` point 3) is that a migration touching
-- existing rows must land with an automatic pre-apply copy of the .db file.
-- That mechanism is `SQLiteStore.migrate_with_backup` +
-- `persistence_backup`, on `main` since round `liq4ri`, and BOTH migrating
-- boot call sites (`app.py:786` and `app.py:789`) go through it; a snapshot
-- that cannot be taken aborts the boot with exit code 13 and the database
-- unchanged.  `COO-DECISION 20260902_1607` condition 1 requires that to be
-- proven by a test that a backup FILE appears, not by a test that a function
-- is called: `tests/test_persistence_birth_defaults_009.py`,
-- `TheOwnerKeepsACopyBefore009Tests`.
--
-- WHAT THE GUARDS BELOW ARE FOR.  A rebuild is the one shape of migration
-- that can lose the whole table, so this file refuses to finish unless it can
-- prove it did not.  Every guard is an INSERT into a table whose CHECK
-- constraint is `ok=1`: a `0` raises, the raise propagates out of
-- `executescript`, the runner rolls back, and NOTHING is applied -- the
-- version is not written to `schema_migrations` either, so the next boot
-- retries from the pre-migration state.  They are inside the migration on
-- purpose, so the proof travels with the owner's own upgrade and does not
-- live only in a test on a developer's machine:
--
--   G1  the row count is unchanged.
--   G2  EVERY row is unchanged in EVERY one of the 35 columns, compared
--       NULL-safely (`IS`) against a copy taken before the rebuild.
--   G3  the column list, types, NOT NULL flags and primary key are identical
--       before and after -- only `dflt_value` is allowed to differ, and only
--       for the four columns named above.
--   G4  the four partial indexes `004` installed are back, by name AND by
--       their exact SQL text (a rebuild that silently loses
--       `characters_active_selector` would let one account hold two
--       characters in the same slot).
--   G5  `pragma_foreign_key_check` is empty.
--
-- WHAT THIS FILE DOES NOT DO.  It does not touch a single existing row's
-- values: a DEFAULT applies to future INSERTs only, and G2 proves that is
-- what happened.  A character that already holds `level 9, hp 480/500` keeps
-- it.  It also does not decide what `class_id` is for a newborn -- the player
-- picks a career at creation and nothing in this server knows which one, so
-- that column stays NULL and the question is open in
-- `notes_to_chief/20260902_1650_LANE-DB-ASK-CHIEF-*`.
COMMIT;
PRAGMA foreign_keys=OFF;
BEGIN IMMEDIATE;
CREATE TABLE _pf_mig009_rows_before AS SELECT * FROM characters;
CREATE TABLE _pf_mig009_cols_before AS
    SELECT cid,name,type,"notnull",dflt_value,pk FROM pragma_table_info('characters');
CREATE TABLE _pf_mig009_idx_before AS
    SELECT name,sql FROM sqlite_master WHERE type='index' AND tbl_name='characters';
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
INSERT INTO characters_rebuild (id,account_id,selector,name,actor_wire,avatar_wire,avatar_typed_json,identity_lo,identity_hi,created_at,updated_at,deleted_at,name_key,create_fingerprint,level,hp_current,hp_max,mp_current,mp_max,speed_walk,class_id,skill_points,unspent_points,stat_str,stat_con,stat_dex,stat_int,stat_per,experience,cash,bonus_str,bonus_con,bonus_dex,bonus_int,bonus_per)
    SELECT id,account_id,selector,name,actor_wire,avatar_wire,avatar_typed_json,identity_lo,identity_hi,created_at,updated_at,deleted_at,name_key,create_fingerprint,level,hp_current,hp_max,mp_current,mp_max,speed_walk,class_id,skill_points,unspent_points,stat_str,stat_con,stat_dex,stat_int,stat_per,experience,cash,bonus_str,bonus_con,bonus_dex,bonus_int,bonus_per FROM characters;
DROP TABLE characters;
ALTER TABLE characters_rebuild RENAME TO characters;
CREATE INDEX characters_active_name_lookup ON characters(name_key) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX characters_create_fingerprint ON characters(account_id, create_fingerprint) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX characters_active_selector ON characters(account_id, selector) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX characters_active_identity ON characters(identity_lo, identity_hi) WHERE deleted_at IS NULL;
CREATE TABLE _pf_mig009_guard(ok INTEGER NOT NULL CHECK(ok=1));
INSERT INTO _pf_mig009_guard(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM characters)=(SELECT COUNT(*) FROM _pf_mig009_rows_before)
    THEN 1 ELSE 0 END;
INSERT INTO _pf_mig009_guard(ok) SELECT CASE WHEN (
    SELECT COUNT(*) FROM characters c JOIN _pf_mig009_rows_before b ON b.id=c.id
     WHERE c.account_id IS b.account_id
       AND c.selector IS b.selector
       AND c.name IS b.name
       AND c.actor_wire IS b.actor_wire
       AND c.avatar_wire IS b.avatar_wire
       AND c.avatar_typed_json IS b.avatar_typed_json
       AND c.identity_lo IS b.identity_lo
       AND c.identity_hi IS b.identity_hi
       AND c.created_at IS b.created_at
       AND c.updated_at IS b.updated_at
       AND c.deleted_at IS b.deleted_at
       AND c.name_key IS b.name_key
       AND c.create_fingerprint IS b.create_fingerprint
       AND c.level IS b.level
       AND c.hp_current IS b.hp_current
       AND c.hp_max IS b.hp_max
       AND c.mp_current IS b.mp_current
       AND c.mp_max IS b.mp_max
       AND c.speed_walk IS b.speed_walk
       AND c.class_id IS b.class_id
       AND c.skill_points IS b.skill_points
       AND c.unspent_points IS b.unspent_points
       AND c.stat_str IS b.stat_str
       AND c.stat_con IS b.stat_con
       AND c.stat_dex IS b.stat_dex
       AND c.stat_int IS b.stat_int
       AND c.stat_per IS b.stat_per
       AND c.experience IS b.experience
       AND c.cash IS b.cash
       AND c.bonus_str IS b.bonus_str
       AND c.bonus_con IS b.bonus_con
       AND c.bonus_dex IS b.bonus_dex
       AND c.bonus_int IS b.bonus_int
       AND c.bonus_per IS b.bonus_per
    )=(SELECT COUNT(*) FROM _pf_mig009_rows_before) THEN 1 ELSE 0 END;
INSERT INTO _pf_mig009_guard(ok) SELECT CASE WHEN (
    SELECT COUNT(*) FROM pragma_table_info('characters') a
      JOIN _pf_mig009_cols_before b ON b.name=a.name
     WHERE a.cid=b.cid AND a.type=b.type AND a."notnull"=b."notnull" AND a.pk=b.pk
       AND (a.dflt_value IS b.dflt_value
            OR (b.dflt_value IS NULL
                AND ((a.name='level' AND a.dflt_value='1')
                     OR (a.name='hp_current' AND a.dflt_value='100')
                     OR (a.name='hp_max' AND a.dflt_value='100')
                     OR (a.name='speed_walk' AND a.dflt_value='400.0'))))
    )=(SELECT COUNT(*) FROM _pf_mig009_cols_before) THEN 1 ELSE 0 END;
INSERT INTO _pf_mig009_guard(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM pragma_table_info('characters'))
    =(SELECT COUNT(*) FROM _pf_mig009_cols_before) THEN 1 ELSE 0 END;
INSERT INTO _pf_mig009_guard(ok) SELECT CASE WHEN (
    SELECT COUNT(*) FROM sqlite_master m JOIN _pf_mig009_idx_before b
        ON b.name=m.name AND b.sql IS m.sql
     WHERE m.type='index' AND m.tbl_name='characters'
    )=(SELECT COUNT(*) FROM _pf_mig009_idx_before) THEN 1 ELSE 0 END;
INSERT INTO _pf_mig009_guard(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND tbl_name='characters')
    =(SELECT COUNT(*) FROM _pf_mig009_idx_before) THEN 1 ELSE 0 END;
INSERT INTO _pf_mig009_guard(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM pragma_foreign_key_check())=0 THEN 1 ELSE 0 END;
DROP TABLE _pf_mig009_guard;
DROP TABLE _pf_mig009_idx_before;
DROP TABLE _pf_mig009_cols_before;
DROP TABLE _pf_mig009_rows_before;
