-- 014_character_skills_learned_source.sql
-- LANE-DB / widen character_skills.source to admit a "learned" grant.
--
-- WHY THIS ROUND.  `pf_bridge/notes_to_chief/
-- 20260905_2119_LANE-CS-CORE-REQUEST-character-skills-learned-source-to-
-- lane-db.md`: LANE-CS's `skill_grant_wiring.learn_and_grant_skill`
-- (real, tested against a `typing.Protocol`, zero production caller yet)
-- has nowhere to write a skill a character LEARNS (as opposed to one it
-- starts with) -- `migrations/011_character_skills.sql`'s own `source TEXT
-- NOT NULL CHECK(source IN ('starting_kit'))` refuses every other value,
-- and `skill_learn_wiring.learn_skill_spend`'s own docstring says outright
-- that granting the skill itself is "a separate write this module does not
-- attempt".  LANE-DB owns `character_skills`/`store.py` (this lane's
-- charter, `COO-DECISION 20260901_1100`) and decides the shape; the
-- CORE-REQUEST is a proposal, not an order, and this migration accepts its
-- simplest option: one new value, `'learned'`, covering every grant that
-- is not the starting kit (no finer split into `'trainer'`/`'quest'`/
-- `'level_up'` -- there is no committed call site yet that needs to tell
-- those apart, and inventing that split now would be exactly the kind of
-- unproven distinction `COO-DECISION 20260901_1059` forbids).
--
-- SQLite CANNOT `ALTER` a `CHECK` constraint, so this rebuilds the table
-- with the documented recipe (`004_character_soft_delete_reuse.sql`'s own
-- shape: create new, copy every column and every row byte-for-byte, drop
-- old, rename, recreate the one index) -- everything below the second
-- `BEGIN IMMEDIATE` is that recipe, not a new one.
--
-- Runner interplay (`store.py` `migrate()` wraps this file in `BEGIN
-- IMMEDIATE .. schema_migrations INSERT .. COMMIT`): the first `COMMIT`
-- below closes that wrapper transaction so `PRAGMA foreign_keys` can take
-- effect (the pragma is a silent no-op inside any open transaction), and
-- this file deliberately leaves its own transaction OPEN at the end so the
-- runner's `schema_migrations` `INSERT` and `COMMIT` land inside it and
-- the whole rebuild stays atomic -- the exact interplay `004`'s own
-- docstring explains for the same reason.  `foreign_keys` is off only for
-- the remainder of THIS migration connection; every normal connection
-- re-enables it at open (`store.connect`).
--
-- WHY THIS COUNTS AS "TOUCHES EXISTING ROWS" AND WHAT COVERS IT.  Unlike
-- `010`-`013` (bare `CREATE TABLE`, zero existing rows to touch), this
-- file copies every existing `character_skills` row into a new table --
-- `COO-DECISION 20260901_1112` point 3's backup requirement for a
-- migration in this shape (backfill/UPDATE/REBUILD) applies, the same as
-- it did for `004` and `009`.  No VALUE on any existing row changes here
-- (this migration only widens a CHECK list; every row's `source` stays
-- `'starting_kit'`, nothing is rewritten to `'learned'`), but the rebuild
-- recipe itself still means every row is read and reinserted, which is
-- the shape the rule is written for.  `SQLiteStore.migrate_with_backup`
-- (`persistence_backup.should_snapshot`/`snapshot_database`) already
-- exists in this codebase and already covers every pending migration,
-- including this one, the same "day chief wires a boot path to call it
-- instead of bare `migrate()`" precedent `013`'s own docstring names --
-- this migration does not need to add a second backup mechanism, only to
-- fall under the one already committed.
--
-- WHAT THIS FILE DOES NOT DO.  It does not INSERT any `'learned'` row --
-- no caller in this codebase writes one yet (`SQLiteStore.
-- grant_learned_skill`, added alongside this file, is the first, and it is
-- not called from `runtime.py` this round).  It does not touch
-- `migrations/011_character_skills.sql` (an already-applied migration is
-- never edited, per this lane's own house rule) -- the CHECK list widens
-- forward, in a NEW file, the same way `004` widened `characters`'
-- constraints in a new file rather than editing `001`.
COMMIT;
PRAGMA foreign_keys=OFF;
BEGIN IMMEDIATE;
CREATE TABLE _pf_mig014_before(n INTEGER NOT NULL);
INSERT INTO _pf_mig014_before(n) SELECT COUNT(*) FROM character_skills;
CREATE TABLE character_skills_rebuild (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(id),
    skill_id INTEGER NOT NULL
        CHECK(typeof(skill_id)='integer' AND skill_id BETWEEN 0 AND 4294967295),
    source TEXT NOT NULL CHECK(source IN ('starting_kit','learned')),
    granted_at TEXT NOT NULL,
    UNIQUE(character_id, skill_id)
);
INSERT INTO character_skills_rebuild (id,character_id,skill_id,source,granted_at)
    SELECT id,character_id,skill_id,source,granted_at FROM character_skills;
DROP TABLE character_skills;
ALTER TABLE character_skills_rebuild RENAME TO character_skills;
CREATE INDEX character_skills_by_character ON character_skills(character_id);
CREATE TABLE _pf_mig014_guard(ok INTEGER NOT NULL CHECK(ok=1));
INSERT INTO _pf_mig014_guard(ok) SELECT CASE WHEN (SELECT COUNT(*) FROM character_skills)=(SELECT n FROM _pf_mig014_before) THEN 1 ELSE 0 END;
INSERT INTO _pf_mig014_guard(ok) SELECT CASE WHEN (SELECT COUNT(*) FROM pragma_foreign_key_check())=0 THEN 1 ELSE 0 END;
DROP TABLE _pf_mig014_guard;
DROP TABLE _pf_mig014_before;
