-- 006_character_typed_attribute_columns.sql
-- LANE-DB / M4, first typed-column migration.
--
-- WHY.  COO-DECISION 20260901_1100 made typed columns in this server's own
-- database the source of truth for a character's attributes, and
-- COO-DECISION 20260901_1325 point 1 confirmed the shape: the database holds
-- the fields, the server COMPOSES the 0x309A attribute block from them, and
-- a field with no source is never guessed.  Until this file, exactly ONE of
-- the twenty-two server-owned fields had a column (`characters.name`, from
-- 001_initial.sql), so `persistence_attr_compose.block_gaps` reported
-- twenty-one fields as `server_owned_column_not_built`.  This file builds
-- those twenty-one columns.  The column names are the ones that module
-- already names in `SERVER_OWNED_FIELDS`, and its `column_exists` flags move
-- to True in the same commit as this file (a test derives the truth from
-- `PRAGMA table_info` rather than trusting the flag).
--
-- WHY IT ADDS COLUMNS AND NOTHING ELSE.  The owner's rule
-- (COO-DECISION 20260901_1112 point 3) is that a migration which touches
-- existing rows -- backfill, UPDATE, table rebuild -- must land together with
-- an automatic pre-apply snapshot of the .db file.  `SQLiteStore.
-- migrate_with_backup` (store.py) is that mechanism, and CORE-REQUEST-DB-001
-- is now ANSWERED: `app.py:784` and `app.py:787` -- both boot call sites, the
-- hypothesis-enabled branch and the plain one -- call it (wired on main by
-- LANE-E round liq4ri, commit 579a6bb4).  So on those two boot shapes this
-- file is preceded by an automatic snapshot rather than running through the
-- unprotected `migrate()`.
--
-- NOT all three, and the third is named rather than left out: `app.py` also
-- has a `scene_load` path (scene_load set, no hypothesis) that does not
-- migrate AT ALL, which is chief's deliberate design and is pinned by his own
-- test (`tests/test_startup_stale_lease_recovery.py::
-- test_the_scene_load_branch_is_the_one_deliberate_exception`).  A boot that
-- never migrates never applies this file either, so it is not a hole in the
-- snapshot -- but "every boot snapshots" would be the wrong sentence and this
-- is the right one.
--
-- That removes the ONLY reason this file was allowed to exist as ADD COLUMN
-- and nothing else, so the restriction is restated on the reason that still
-- holds: a backfill needs a VALUE, and no value here has been adjudicated.
-- COO-DECISION 20260901_1447 point 2 forbids seeding `speed_walk` with either
-- candidate number (150.0 proven on the wire for NPCs, 400.0 the client's
-- construction default) until an RE answers which one a player object uses --
-- "both numbers are equally a guess without it".  The same is true, untested,
-- of the other twenty.  This file is therefore still restricted, on purpose,
-- to `ALTER TABLE ... ADD COLUMN`: no UPDATE, no DELETE, no INSERT, no DROP,
-- no rebuild.  Existing character rows are not read and not rewritten; every
-- existing column keeps its exact bytes.  A migration that seeds or backfills
-- any of these columns is a LATER file and now waits on an adjudicated value,
-- not on a mechanism.
--
-- WHY EVERY COLUMN IS NULLABLE WITH NO DEFAULT.  This is the owner's
-- "never send a block whose unknown field was guessed to be zero" rule
-- (relayed verbatim in COO-DECISION 20260901_1059) expressed in the schema.
-- A NOT NULL column needs a constant default, and for a live character on the
-- owner's canonical database that constant would be a server invention that
-- reads back exactly like a measured value.  NULL cannot be mistaken for one:
-- `SQLiteStore.read_typed_attributes` omits NULL columns from what it returns,
-- so an unseeded field arrives at the compose gate as ABSENT and the gate
-- refuses the block by its own rules.  Fail-closed survives the round trip.
--
-- THE CHECKS.  Each column carries the range of the wire kind
-- `gm/attr_wire.FIELDS` gives that field, plus a `typeof` guard, so a value
-- that could not survive the encoder cannot be stored in the first place.
-- Two honest narrowings, both permanent properties of SQLite rather than
-- choices:
--   * u64 fields (experience x=23, cash x=24) are capped at 2^63-1, not
--     2^64-1: SQLite's INTEGER is a signed 64-bit value and has no room for
--     the top half of the range.  A character who legitimately exceeds
--     9223372036854775807 experience is not representable here and would need
--     a TEXT/BLOB column.  [PROPOSED - LANE-DB] whether this game ever
--     reaches that number is not measured anywhere; the narrowing is in the
--     safe direction (storage narrower than what `encode_field` accepts), so
--     it fails loudly at the write rather than truncating.
--   * f32 speed (x=7) is stored in an 8-byte REAL, which is WIDER than the
--     wire.  `persistence_typed_attrs.validate` therefore rounds a stored f32
--     through `struct.pack("<f", ...)` -- the same call `gm/attr_wire.py`
--     emits with -- so the number in this column and the number the client
--     receives are the same number.  Without that rounding the two disagree
--     silently: an adversary pass measured `1e-300` stored, read back as
--     `1e-300`, and arriving at the client as an EXACT 0.0, which on this
--     wire is a value rather than an absence (see tests/test_npc_gait_wire.py)
--     -- the owner's banned zero, reached by arithmetic instead of a lookup.
--     Values that underflow that way are now refused at the write.
--
-- THIS MIGRATION IS NOT REVERSIBLE, and that is a different word from
-- "non-destructive".  It destroys nothing (proved row by row in
-- tests/test_persistence_typed_attr_columns.py), but once it is applied the
-- checksum ledger makes this file immutable and `migrate()` refuses to boot a
-- server older than the schema ("database schema is newer than this server",
-- store.py).  So rolling the server back past this commit on a database that
-- has already applied 006 means the server will not start.  What HAS changed
-- since this paragraph was first written is the recovery: measured, not
-- feared, `persistence_backup.should_snapshot` votes True on this very file
-- ("pending migrations: 006"), and as of `app.py:784`/`:787` a boot now acts
-- on that vote, so a copy of the pre-006 database exists to go back to.
--   [CORRECTED - LANE-DB round ekt2kv] an earlier draft of this paragraph
--   said 006 is "the first file in this repository's history" to make that
--   function vote True.  That is not measured and is probably false:
--   `should_snapshot` also votes True for `journal_mode_rewrite_pending` and
--   `ledger_rewrite_pending` (persistence_backup.py:300-310), and the second
--   of those exists precisely because the owner's canonical database predates
--   the ledger's `checksum` column -- so on THAT database it would have voted
--   True at 005 as well, for a different reason.  What is true and is all
--   that this paragraph needs: 006 is the first MIGRATION FILE to do it.  Going back is still a manual
-- act by the owner (restore the snapshot, then run the older server); nothing
-- in this repository rolls a schema backwards on its own, and nothing here
-- claims it does.
--
-- NAMING NOTE, said out loud rather than buried.  x=7 is called `speed_walk`
-- here because that is the field `COO-ORDER 20260901_1101` ordered this lane
-- to build for `/speed`.  What this repository already knows about that
-- offset, read in full rather than in the convenient half:
--   * `gm/attr_wire.py:173` calls it `basic_f32_54`, `known=False`, and the
--     Codex corpus scopes its row to `CNetNPC`, not to the player.
--   * BUT `docs/FUNCTIONAL_COVERAGE.json` grades `npc_locomotion_presentation`
--     as `runtime_pass` on the SAME bit -- "the decoded MOBS walk-speed value
--     carried in BasicAttr bit 0x0040" -- and `tests/test_npc_gait_wire.py:59`
--     pins `PROVEN_WALK_SPEED = 150.0` at that bit and offset.
-- So the offset is not unidentified: it is identified AT THE NPC/VISUAL LAYER
-- and untested for a player character (that same coverage row says the
-- Foundation population path never requests a movement speed).  Two layers
-- also carry two different numbers for it -- 150.0 proven on the wire for
-- NPCs, 400.0 as the client's construction default for the player object --
-- and this lane is not the one to rule which applies to a player.  The COLUMN
-- NAME therefore still encodes a hypothesis.  [สมมติของสาย DB - รอ RE]
-- Nothing else in this file depends on that name being right: the column is
-- bound to BasicAttr+0x54 by x=7, and a rename is a later, cheap migration
-- (verified: ALTER TABLE ... RENAME COLUMN works with the CHECK in place).

ALTER TABLE characters ADD COLUMN level INTEGER
    CHECK(level IS NULL OR (typeof(level)='integer' AND level BETWEEN 0 AND 65535));
ALTER TABLE characters ADD COLUMN hp_current INTEGER
    CHECK(hp_current IS NULL OR (typeof(hp_current)='integer' AND hp_current BETWEEN 0 AND 4294967295));
ALTER TABLE characters ADD COLUMN hp_max INTEGER
    CHECK(hp_max IS NULL OR (typeof(hp_max)='integer' AND hp_max BETWEEN 0 AND 4294967295));
ALTER TABLE characters ADD COLUMN mp_current INTEGER
    CHECK(mp_current IS NULL OR (typeof(mp_current)='integer' AND mp_current BETWEEN 0 AND 4294967295));
ALTER TABLE characters ADD COLUMN mp_max INTEGER
    CHECK(mp_max IS NULL OR (typeof(mp_max)='integer' AND mp_max BETWEEN 0 AND 4294967295));
ALTER TABLE characters ADD COLUMN speed_walk REAL
    CHECK(speed_walk IS NULL OR (typeof(speed_walk)='real' AND speed_walk BETWEEN -3.4028234663852886e38 AND 3.4028234663852886e38));
ALTER TABLE characters ADD COLUMN class_id INTEGER
    CHECK(class_id IS NULL OR (typeof(class_id)='integer' AND class_id BETWEEN 0 AND 4294967295));
ALTER TABLE characters ADD COLUMN skill_points INTEGER
    CHECK(skill_points IS NULL OR (typeof(skill_points)='integer' AND skill_points BETWEEN 0 AND 4294967295));
ALTER TABLE characters ADD COLUMN unspent_points INTEGER
    CHECK(unspent_points IS NULL OR (typeof(unspent_points)='integer' AND unspent_points BETWEEN 0 AND 65535));
ALTER TABLE characters ADD COLUMN stat_str INTEGER
    CHECK(stat_str IS NULL OR (typeof(stat_str)='integer' AND stat_str BETWEEN 0 AND 65535));
ALTER TABLE characters ADD COLUMN stat_con INTEGER
    CHECK(stat_con IS NULL OR (typeof(stat_con)='integer' AND stat_con BETWEEN 0 AND 65535));
ALTER TABLE characters ADD COLUMN stat_dex INTEGER
    CHECK(stat_dex IS NULL OR (typeof(stat_dex)='integer' AND stat_dex BETWEEN 0 AND 65535));
ALTER TABLE characters ADD COLUMN stat_int INTEGER
    CHECK(stat_int IS NULL OR (typeof(stat_int)='integer' AND stat_int BETWEEN 0 AND 65535));
ALTER TABLE characters ADD COLUMN stat_per INTEGER
    CHECK(stat_per IS NULL OR (typeof(stat_per)='integer' AND stat_per BETWEEN 0 AND 65535));
ALTER TABLE characters ADD COLUMN experience INTEGER
    CHECK(experience IS NULL OR (typeof(experience)='integer' AND experience BETWEEN 0 AND 9223372036854775807));
ALTER TABLE characters ADD COLUMN cash INTEGER
    CHECK(cash IS NULL OR (typeof(cash)='integer' AND cash BETWEEN 0 AND 9223372036854775807));
ALTER TABLE characters ADD COLUMN bonus_str INTEGER
    CHECK(bonus_str IS NULL OR (typeof(bonus_str)='integer' AND bonus_str BETWEEN 0 AND 65535));
ALTER TABLE characters ADD COLUMN bonus_con INTEGER
    CHECK(bonus_con IS NULL OR (typeof(bonus_con)='integer' AND bonus_con BETWEEN 0 AND 65535));
ALTER TABLE characters ADD COLUMN bonus_dex INTEGER
    CHECK(bonus_dex IS NULL OR (typeof(bonus_dex)='integer' AND bonus_dex BETWEEN 0 AND 65535));
ALTER TABLE characters ADD COLUMN bonus_int INTEGER
    CHECK(bonus_int IS NULL OR (typeof(bonus_int)='integer' AND bonus_int BETWEEN 0 AND 65535));
ALTER TABLE characters ADD COLUMN bonus_per INTEGER
    CHECK(bonus_per IS NULL OR (typeof(bonus_per)='integer' AND bonus_per BETWEEN 0 AND 65535));
