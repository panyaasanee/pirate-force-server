ALTER TABLE characters ADD COLUMN name_key TEXT NOT NULL DEFAULT '';
ALTER TABLE characters ADD COLUMN create_fingerprint TEXT NOT NULL DEFAULT '';
UPDATE characters SET name_key=lower(name), create_fingerprint='legacy:' || id;
CREATE INDEX characters_active_name_lookup ON characters(name_key) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX characters_create_fingerprint ON characters(account_id, create_fingerprint);

ALTER TABLE character_positions ADD COLUMN heading REAL NOT NULL DEFAULT 0;

ALTER TABLE sessions ADD COLUMN lease_generation INTEGER NOT NULL DEFAULT 0;
UPDATE sessions SET closed_at=COALESCE(closed_at, CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX sessions_one_active_character ON sessions(selected_character_id) WHERE closed_at IS NULL AND selected_character_id IS NOT NULL;
