-- 018_character_skills_gm_grant_source.sql
-- LANE-DB / widen character_skills.source to admit a GM sandbox grant,
-- and be the first rebuild whose guard can see a row's CONTENT.
--
-- WHY THIS ROUND.  `pf_bridge/NOW.md` carries the owner's order `PANYA
-- 20260908_1455` (restated by `1541`) as a red line: a SKILL PRACTICE
-- GROUND, GM ACCOUNTS ONLY -- `/skill all` grants every skill regardless
-- of `n_LEVEL_LEARN`, `/job <1|2|4|16|32>` switches class, and the five
-- classes' weapons sit in the bag.  The same file's LANE-DB row names this
-- lane's half of it: "many skill rows, idempotent + the five classes'
-- weapons (1455)", second in this lane's queue behind `017`, which is now
-- on `origin/main` (`migrations/017_character_experience_skill_points_
-- birth_defaults.sql` is present there) -- so the second item is live.
--
-- A GM's grant is not a thing the character LEARNED.  `migrations/
-- 011_character_skills.sql` created `source` for exactly this question and
-- said in its own docstring how it is meant to grow: "a future source is a
-- new value in the CHECK list, not a new column"; `014` then widened it
-- once already, for `'learned'`.  Writing a `/skill all` row as
-- `'learned'` would put a sentence into the owner's canonical database
-- that is not true -- nobody learned 300 skills at once -- and this lane's
-- charter (`COO-DECISION 20260901_1059`) forbids exactly that kind of
-- convenient guess.  `'gm_grant'` is one new value covering every row a
-- GM command mints; it is deliberately NOT split further (`'skill_all'` /
-- `'job_switch'` / ...) because no committed call site can yet tell those
-- apart, which is the same reason `014` refused to split `'learned'`.
--
-- WHAT THE ROW MEANS AFTER THIS FILE.  `'starting_kit'` = born with it;
-- `'learned'` = paid skill points for it; `'gm_grant'` = an operator on a
-- GM account put it there and no player action did.  The table's
-- `UNIQUE(character_id, skill_id)` is unchanged and still shared across
-- all three sources, so a skill a character already owns is not re-minted
-- under a second provenance -- `SQLiteStore.grant_gm_skills` (the write
-- half, added in the same PR) uses `INSERT OR IGNORE` against it, exactly
-- as `grant_starting_skills` and `grant_learned_skill` do.  A skill that
-- was already `'starting_kit'` therefore STAYS `'starting_kit'` after
-- `/skill all`; the door does not rewrite an existing row's provenance,
-- and this migration rewrites no existing row's value either.
--
-- SQLite CANNOT `ALTER` a `CHECK` constraint, so this rebuilds the table
-- with the recipe `014` used on this same table (create new, copy every
-- column and every row, drop old, rename, recreate the one index).
-- Runner interplay is `014`'s, unchanged and for its reasons: the first
-- `COMMIT` closes the wrapper transaction `SQLiteStore.migrate` opened so
-- that `PRAGMA foreign_keys` can take effect at all (the pragma is a
-- silent no-op inside an open transaction), and this file leaves its own
-- transaction OPEN at the end so the runner's `schema_migrations` INSERT
-- and COMMIT land inside it and the whole rebuild stays atomic.
-- `foreign_keys` is off only for the rest of THIS migration connection;
-- every normal connection re-enables it at open (`store.connect`).
--
-- THE GUARD IS NEW, AND IT IS A DEBT THIS LANE OWED ITSELF.  Every
-- rebuild migration in this repository so far (`004`, `009`, `014`,
-- `017`) guards its copy with a ROW COUNT.  pf-adversary broke that guard
-- against `017` and this lane wrote the finding down rather than arguing
-- with it (`pf_bridge/rounds/DB_20260908_1316_nivlwg_round.md`, D2): an
-- `UPDATE character_positions SET scene_id=99` slipped in before the
-- `DROP` passes a count guard green -- every character silently moves to
-- scene 99 and the migration reports success.  A count cannot see a
-- dropped column filled by a DEFAULT, two columns swapped, a `COALESCE`
-- that turns a NULL into a zero, or any rewritten value.  `017` is
-- applied and frozen, so it can never be repaired; the repair is that the
-- NEXT rebuild carries a guard that compares the row CONTENT, and every
-- rebuild after it borrows the same one.
--
-- That guard is `src/pirateforce_foundation/persistence_rebuild_guard.py`
-- and the four `_pf_mig018_guard` statements below are its output
-- verbatim, not a hand copy: `tests/test_persistence_rebuild_guard.py`
-- regenerates them from the helper and from this table's PRE-migration
-- column list (read out of `PRAGMA table_info` on a database migrated to
-- `017`, not typed a second time) and fails if this file's text has
-- drifted from either.  The guard asks three questions the count could
-- not: no row exists after that was not there before, no row was there
-- before that is missing after, and -- kept from the old shape because it
-- answers a fourth question `EXCEPT` folds away -- the counts still
-- match.  `EXCEPT` is used rather than a join because SQLite compares
-- compound-select rows with NULL-sensitive equality, so a nullable column
-- compares correctly instead of reporting every NULL row as changed.
--
-- WHY THIS COUNTS AS "TOUCHES EXISTING ROWS" AND WHAT COVERS IT.  Like
-- `014`, this file copies every existing `character_skills` row into a new
-- table, which is the backfill/UPDATE/rebuild shape `COO-DECISION
-- 20260901_1112` point 3 requires an automatic pre-apply snapshot for.  No
-- VALUE on any existing row changes here (only the CHECK list widens), but
-- every row is read and reinserted, so the rule applies.
-- `SQLiteStore.migrate_with_backup` (`persistence_backup.should_snapshot`
-- / `snapshot_database`) already exists and already covers every pending
-- migration including this one; this file falls under the mechanism
-- already committed rather than adding a second one.
--
-- WHAT THIS FILE DOES NOT DO.  It does not INSERT a `'gm_grant'` row --
-- `SQLiteStore.grant_gm_skills` is the first and only writer of that
-- value, and nothing in `runtime.py` or `gm/` calls it this round (the GM
-- command half of `1455` is LANE-GM's, and it is not this lane's to
-- wire).  It does not touch `011` or `014` (an applied migration is never
-- edited) -- the CHECK list widens forward in a new file.  It does not
-- change the index, the UNIQUE constraint, the column list, or any
-- existing row's value.
COMMIT;
PRAGMA foreign_keys=OFF;
BEGIN IMMEDIATE;
CREATE TABLE _pf_mig018_before AS SELECT * FROM character_skills;
CREATE TABLE character_skills_rebuild (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(id),
    skill_id INTEGER NOT NULL
        CHECK(typeof(skill_id)='integer' AND skill_id BETWEEN 0 AND 4294967295),
    source TEXT NOT NULL CHECK(source IN ('starting_kit','learned','gm_grant')),
    granted_at TEXT NOT NULL,
    UNIQUE(character_id, skill_id)
);
INSERT INTO character_skills_rebuild (id,character_id,skill_id,source,granted_at)
    SELECT id,character_id,skill_id,source,granted_at FROM character_skills;
DROP TABLE character_skills;
ALTER TABLE character_skills_rebuild RENAME TO character_skills;
CREATE INDEX character_skills_by_character ON character_skills(character_id);
CREATE TABLE _pf_mig018_guard(ok INTEGER NOT NULL CHECK(ok=1));
INSERT INTO _pf_mig018_guard(ok) SELECT CASE WHEN (SELECT COUNT(*) FROM character_skills)=(SELECT COUNT(*) FROM _pf_mig018_before) THEN 1 ELSE 0 END;
INSERT INTO _pf_mig018_guard(ok) SELECT CASE WHEN NOT EXISTS(SELECT id,character_id,skill_id,source,granted_at FROM character_skills EXCEPT SELECT id,character_id,skill_id,source,granted_at FROM _pf_mig018_before) THEN 1 ELSE 0 END;
INSERT INTO _pf_mig018_guard(ok) SELECT CASE WHEN NOT EXISTS(SELECT id,character_id,skill_id,source,granted_at FROM _pf_mig018_before EXCEPT SELECT id,character_id,skill_id,source,granted_at FROM character_skills) THEN 1 ELSE 0 END;
INSERT INTO _pf_mig018_guard(ok) SELECT CASE WHEN (SELECT COUNT(*) FROM pragma_foreign_key_check())=0 THEN 1 ELSE 0 END;
DROP TABLE _pf_mig018_guard;
DROP TABLE _pf_mig018_before;
