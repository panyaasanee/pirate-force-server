-- 004_character_soft_delete_reuse.sql
-- Lane 1 Option B (project owner decision 2026-08-18 00:52): replace the two
-- table-level UNIQUE constraints on characters with partial unique indexes
-- that govern only rows whose deleted_at IS NULL, so a soft-deleted slot can
-- be recreated in place (same selector, same derived identity, and -- because
-- the byte-identical wire produces the same fingerprint -- the same create
-- fingerprint).  characters_create_fingerprint therefore becomes partial too;
-- the create-retry scan already filters deleted_at IS NULL (store.py), so
-- idempotent-retry semantics for live rows are unchanged.
-- SQLite cannot drop table constraints, so this rebuilds the table with the
-- documented recipe (create new, copy, drop old, rename, recreate indexes).
--
-- Runner interplay (store.py migrate wraps this file in BEGIN IMMEDIATE ..
-- schema_migrations INSERT .. COMMIT): the first COMMIT below closes that
-- wrapper transaction so PRAGMA foreign_keys can take effect (the pragma is a
-- silent no-op inside any transaction), and this file deliberately leaves its
-- own transaction OPEN so the runner's schema_migrations INSERT and COMMIT
-- land inside it and the whole rebuild stays atomic.  foreign_keys remains
-- off only for the remainder of the migration connection; every normal
-- connection re-enables it at open.  Dropping the parent table with
-- foreign_keys ON would cascade-delete character_positions and backpack rows,
-- which is exactly what this recipe avoids.
COMMIT;
PRAGMA foreign_keys=OFF;
BEGIN IMMEDIATE;
CREATE TABLE _pf_mig004_before(n INTEGER NOT NULL);
INSERT INTO _pf_mig004_before(n) SELECT COUNT(*) FROM characters;
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
    create_fingerprint TEXT NOT NULL DEFAULT ''
);
INSERT INTO characters_rebuild (id,account_id,selector,name,actor_wire,avatar_wire,avatar_typed_json,identity_lo,identity_hi,created_at,updated_at,deleted_at,name_key,create_fingerprint)
    SELECT id,account_id,selector,name,actor_wire,avatar_wire,avatar_typed_json,identity_lo,identity_hi,created_at,updated_at,deleted_at,name_key,create_fingerprint FROM characters;
DROP TABLE characters;
ALTER TABLE characters_rebuild RENAME TO characters;
CREATE INDEX characters_active_name_lookup ON characters(name_key) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX characters_create_fingerprint ON characters(account_id, create_fingerprint) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX characters_active_selector ON characters(account_id, selector) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX characters_active_identity ON characters(identity_lo, identity_hi) WHERE deleted_at IS NULL;
CREATE TABLE _pf_mig004_guard(ok INTEGER NOT NULL CHECK(ok=1));
INSERT INTO _pf_mig004_guard(ok) SELECT CASE WHEN (SELECT COUNT(*) FROM characters)=(SELECT n FROM _pf_mig004_before) THEN 1 ELSE 0 END;
INSERT INTO _pf_mig004_guard(ok) SELECT CASE WHEN (SELECT COUNT(*) FROM pragma_foreign_key_check())=0 THEN 1 ELSE 0 END;
DROP TABLE _pf_mig004_guard;
DROP TABLE _pf_mig004_before;
