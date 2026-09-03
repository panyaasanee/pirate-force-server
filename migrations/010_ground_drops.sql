-- 010_ground_drops.sql
-- LANE-DB / the ground-drop persistence door.
--
-- WHAT THIS FILE DOES.  A bare, empty table, `ground_drops`, and nothing
-- else -- no ALTER, no UPDATE, no touched row anywhere.  This is the answer
-- to `20260903_1740_LANE-DB-REPORT-ground-ledger-in-memory-no-table-door-
-- proposed.md`'s measurement: "what is on the ground and has not been
-- picked up yet" lives ONLY in a per-session, in-memory
-- `mob_loot.DropLedgerCell` today (`runtime.py:1328`, constructed with zero
-- arguments, no registry keyed by token anywhere) -- a second login on the
-- same account sees an empty ground where the first login's kill left a
-- drop.  `COO-DECISION 20260903_1843` ("build the ground-drop door now")
-- answered the three open design questions that letter raised and ordered
-- this file plus two `store.py` methods, this round.
--
-- WHY NO BACKUP MECHANISM.  `COO-DECISION 20260901_1112` point 3 requires
-- an automatic pre-apply snapshot only for a migration that touches EXISTING
-- rows (backfill/UPDATE/rebuild -- `004` and `009` are the two examples on
-- disk).  This file inserts nothing, updates nothing, and rebuilds no
-- existing table; every statement below is a `CREATE`.  `COO-DECISION
-- 20260903_1843` point 5 says this explicitly and, on that ground, does NOT
-- ask chief to change either boot call site's `migrate_with_backup()` call
-- for this file.
--
-- WHY A BARE TABLE AND NOT A DOMAIN OBJECT.  `mob_loot.GroundDrop` (LANE-B's
-- own dataclass, `mob_loot.py:2164`) is what a call site holds in memory;
-- this table's columns are chosen to hold exactly its fields
-- (`drop_key`, `item_id`, `quantity`, `x`, `y`, `z`, `mob_identity`,
-- `killer_identity`, `scene`) so a future LANE-B call site can hand this
-- door primitives straight off one without translating through a second
-- shape.  This lane does not import `mob_loot` and does not construct or
-- validate a `GroundDrop` -- `COO-DECISION 20260903_1843` point 3 draws the
-- charter line (`COO-DECISION 20260901_1100`) exactly here: LANE-DB owns
-- the table and the store methods; the call site that fires when an item
-- actually hits the ground, and the server-wide `drop_key` issuer a shared
-- table needs (today's issuer is a per-session in-memory counter that
-- starts every session at the same `DROP_KEY_BASE`, safe only because
-- sessions cannot see each other's ledger -- letter `1740` question (c)-2),
-- are LANE-B's, ordered separately in `COO-DECISION 20260903_1844`.
--
-- WHY `scene` AND `scene_fold` ARE TWO COLUMNS, NOT ONE.  `mob_loot.
-- _require_scene`'s own docstring is explicit that scene names are stored
-- EXACTLY as given and are never case-normalised, because the roster
-- modules disagree about case today (`field_mob_tables.SCENE` is
-- `"bg0001"`, `field_mob_tables_bg0002.SCENE` is `"Bg0002"`) -- and that
-- EVERY comparison between two scene names goes through `mob_loot.
-- scene_key`, which is `.casefold()`, "nothing else".  `COO-DECISION
-- 20260903_1843` point 4 orders `UNIQUE(scene_id, drop_key)` so two
-- sessions racing for one key in one scene fail loudly at the table rather
-- than one silently overwriting the other; a literal `UNIQUE(scene,
-- drop_key)` on the un-folded column would let `"bg0002"` and `"Bg0002"` --
-- one real scene, two spellings -- each mint the SAME key without ever
-- tripping that constraint, which is the exact silent collision the order
-- exists to make loud.  `scene_fold` is what the constraint is actually
-- taken against; `scene` is kept, unfolded, so a row read back carries
-- back exactly the spelling it was written with (round-trip fidelity is
-- this door's whole first-round scope -- see below).  `store.py`'s
-- `commit_ground_drop`/`list_ground_drops_for_scene` compute the fold in
-- Python with `str.casefold()`, the same call `scene_key` makes; every
-- scene value this table ever holds is required ASCII by that same
-- function (`_require_scene`), which is why plain `casefold()` and SQL's
-- `lower()` cannot disagree on any value this door will ever see, and why
-- this file does not need a SQLite collation or a generated column to get
-- that answer.
--
-- WHY `x`/`y`/`z` ARE BOUNDED, NOT JUST TYPED.  `pf-adversary` (round
-- `5d02mu`) measured that `CHECK(typeof(x)='real')` alone is not the
-- backstop it looks like: SQLite's `typeof()` reports `'real'` for IEEE
-- infinity too, so a row with `x = inf` passed that CHECK and round-tripped
-- through the table with the Python-side `math.isfinite` guard in
-- `SQLiteStore.commit_ground_drop` removed.  The `BETWEEN` bound below is
-- the finite range of an IEEE double (`+-1.7976931348623157e308`), which a
-- comparison against `+-Infinity` always fails, and which a `NaN` also
-- always fails (every comparison with `NaN` is false in both SQL and
-- IEEE 754), so this CHECK now refuses everything `math.isfinite` refuses
-- on the Python side, independently, and does not merely repeat "is this
-- column's storage class REAL".
--
-- WHAT THIS FILE'S SCOPE IS NOT.  Letter `1740` question (c)-3 proposed,
-- and `COO-DECISION 20260903_1843` point 5 confirmed, that round one is
-- "write at drop time, read it back" ONLY -- no removal.  There is no
-- `DELETE`, no expiry column, and no removal-publisher wiring here;
-- `COO-DECISION 20260901_0253` holds that no ledger row may be removed
-- until a removal publisher exists, and `mob_loot.DropLedgerCell` (in
-- memory, `mob_loot.py:2244-2251`) already documents holding to the same
-- rule.  A row this table is ever given stays until a later round builds
-- that publisher.
CREATE TABLE ground_drops (
    id INTEGER PRIMARY KEY,
    scene TEXT NOT NULL,
    scene_fold TEXT NOT NULL,
    drop_key INTEGER NOT NULL
        CHECK(typeof(drop_key)='integer' AND drop_key BETWEEN 0 AND 4294967295),
    item_id INTEGER NOT NULL
        CHECK(typeof(item_id)='integer' AND item_id BETWEEN 1 AND 4294967295),
    quantity INTEGER NOT NULL
        CHECK(typeof(quantity)='integer' AND quantity BETWEEN 1 AND 65535),
    x REAL NOT NULL
        CHECK(typeof(x)='real' AND x BETWEEN -1.7976931348623157e308 AND 1.7976931348623157e308),
    y REAL NOT NULL
        CHECK(typeof(y)='real' AND y BETWEEN -1.7976931348623157e308 AND 1.7976931348623157e308),
    z REAL NOT NULL
        CHECK(typeof(z)='real' AND z BETWEEN -1.7976931348623157e308 AND 1.7976931348623157e308),
    mob_identity INTEGER NOT NULL
        CHECK(typeof(mob_identity)='integer' AND mob_identity BETWEEN 0 AND 4294967295),
    killer_identity INTEGER NOT NULL
        CHECK(typeof(killer_identity)='integer' AND killer_identity BETWEEN 0 AND 4294967295),
    created_at TEXT NOT NULL,
    -- THE COLLISION GUARD, COO-DECISION 20260903_1843 point 4, said in
    -- full: two sessions that mint the same drop_key in the same scene
    -- must have their SECOND write refused by the database itself, not
    -- resolved by whichever write lands last winning.  "scene" in the
    -- decision's own words means "the scene the row is in" -- the folded
    -- column above -- not literally a column spelled `scene_id`.
    UNIQUE(scene_fold, drop_key)
);
