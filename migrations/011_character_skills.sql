-- 011_character_skills.sql
-- LANE-DB / the starting-skill-kit persistence door.
--
-- WHAT THIS FILE DOES.  A bare, empty table, `character_skills`, and nothing
-- else -- no ALTER, no UPDATE, no touched row anywhere.  This is the schema
-- half of `PANYA-DECISION 20260904_0328` piece 5 (`COO-ORDER 20260904_0329`
-- item 5, "skill rows + basic attack born"): today a character's skill
-- window is empty forever -- nothing in this repository writes a skill a
-- character owns anywhere, including the one every class starts with
-- (`CONSTDATA_TH__SKILL_TEXT.tsv` id 99, "Normal Attack").
--
-- WHY NO BACKUP MECHANISM.  `COO-DECISION 20260901_1112` point 3 requires an
-- automatic pre-apply snapshot only for a migration that touches EXISTING
-- rows (backfill/UPDATE/rebuild -- `004` and `009` are the two examples on
-- disk).  This file inserts nothing, updates nothing, and rebuilds no
-- existing table; every statement below is a `CREATE`, the same ground
-- `010_ground_drops.sql` stood on for the same reason.
--
-- WHAT "skill_id" MEANS AND WHERE IT COMES FROM.  This table stores the raw
-- client skill id (`CONSTDATA_TH__SKILL_CONTEXT.n_ID` /
-- `TEXTDATA_TH__SKILL_TEXT.n_ID`) verbatim -- no renaming, no local
-- enumeration.  This lane does not own skill data and does not decide which
-- ids a class starts with: `src/pirateforce_foundation/class_catalog.py`
-- (LANE-CS, `CHARCREATE_CLASS.s_SKILL_1..4`, sha256-pinned) is the single
-- committed source for that, and `persistence_starting_skills.py` in this
-- same PR only RESOLVES a `class_id` to that already-decided tuple; it does
-- not re-derive or re-type the mapping.
--
-- WHY `source` AND NOT JUST "every row is a starting-kit row".  A character
-- learning a skill later (a level-up grant, a trainer, a quest reward) is
-- explicitly out of this round's scope -- there is no such call site yet --
-- but a bare table with no provenance column would make a future writer's
-- first move "add a column", which is an ALTER on a table real rows may
-- already be in by then.  Recording the reason a row exists costs one CHECK-
-- constrained column now and avoids that later migration entirely for the
-- one shape this round actually needs. `'starting_kit'` is the only value
-- this round's writer (`SQLiteStore.grant_starting_skills`) ever inserts;
-- a future source is a new value in the CHECK list, not a new column.
--
-- WHY `UNIQUE(character_id, skill_id)` AND `INSERT OR IGNORE`, NOT A
-- COLLISION REFUSAL LIKE `ground_drops`.  A ground-drop key collision is two
-- DIFFERENT drops racing for one slot -- refusing loudly is the point.  A
-- second grant of the SAME skill to the SAME character is not a collision at
-- all: `CharacterLifecycle.create`'s existing create-fingerprint retry path
-- (see `lifecycle.py`, and `persist_class_id_from_starting_gear`'s own
-- docstring for the same shape) can call the starting-kit grant twice for
-- one character, and the second call must be a no-op, not an error, exactly
-- as `write_typed_attributes` re-writing the same `class_id` twice is.  The
-- UNIQUE constraint's job here is idempotency, not collision detection --
-- `SQLiteStore.grant_starting_skills` uses `INSERT OR IGNORE` against it.
--
-- WHY NO FOREIGN KEY DECLARED HERE THAT `characters(id)` DOES NOT ALREADY
-- COVER.  `character_id INTEGER NOT NULL REFERENCES characters(id)` is the
-- same shape `009`'s rebuilt `characters.account_id` uses for its own parent
-- reference; every normal connection runs with `PRAGMA foreign_keys=ON`
-- (`store.connect`), so an orphan write is refused by SQLite itself, not by
-- Python-side bookkeeping this file would otherwise have to duplicate.
CREATE TABLE character_skills (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(id),
    skill_id INTEGER NOT NULL
        CHECK(typeof(skill_id)='integer' AND skill_id BETWEEN 0 AND 4294967295),
    source TEXT NOT NULL CHECK(source IN ('starting_kit')),
    granted_at TEXT NOT NULL,
    UNIQUE(character_id, skill_id)
);

-- The read half (`SQLiteStore.list_character_skills`) always filters by
-- `character_id`; this index is what keeps that a lookup instead of a scan
-- once a real account has more than a handful of characters.
CREATE INDEX character_skills_by_character ON character_skills(character_id);
