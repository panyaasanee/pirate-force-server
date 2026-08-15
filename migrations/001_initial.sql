PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE accounts (id INTEGER PRIMARY KEY, login_name TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
CREATE TABLE characters (id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), selector INTEGER NOT NULL CHECK(selector BETWEEN 0 AND 255), name TEXT NOT NULL, actor_wire BLOB NOT NULL, avatar_wire BLOB NOT NULL, avatar_typed_json TEXT, identity_lo INTEGER NOT NULL, identity_hi INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT, UNIQUE(account_id, selector), UNIQUE(identity_lo, identity_hi));
CREATE TABLE character_positions (character_id INTEGER PRIMARY KEY REFERENCES characters(id) ON DELETE CASCADE, scene_id INTEGER NOT NULL, scene_seq INTEGER NOT NULL, x REAL NOT NULL, y REAL NOT NULL, z REAL NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE sessions (id TEXT PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), selected_character_id INTEGER REFERENCES characters(id), opened_at TEXT NOT NULL, closed_at TEXT);
