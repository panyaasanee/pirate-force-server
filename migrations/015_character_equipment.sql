-- 015_character_equipment.sql
-- LANE-DB / the equipped-item persistence door.
--
-- WHAT THIS FILE DOES.  A bare, empty table, `character_equipment`, and
-- nothing else -- no ALTER, no UPDATE, no touched row anywhere.  Today
-- nothing in this repository records that a character has an item equipped
-- (weapon in hand, or otherwise): `ItemAttrState`/`character_skills`-style
-- doors cover the bag and skills, but "worn" state has no row anywhere.
-- This is the schema half of `PANYA-ORDER 20260906_1312`'s arm (b) ("equip
-- weapon" persistence) -- the response-frame half (what bytes the server
-- sends back for the client to show the slot on screen) is BLOCKED on RE
-- (`notes_to_chief/20260906_1434_LANE-DB-RE-TICKET-*`): this table exists
-- so the store door is ready the moment that RE answer lands, and does not
-- itself claim to close arm (b).
--
-- WHY NO BACKUP MECHANISM.  Same reasoning `010_ground_drops.sql` and
-- `011_character_skills.sql` give: `COO-DECISION 20260901_1112` point 3
-- requires an automatic pre-apply snapshot only for a migration that
-- touches EXISTING rows (backfill/UPDATE/rebuild).  This file inserts
-- nothing, updates nothing, rebuilds no existing table -- every statement
-- below is a `CREATE`.
--
-- WHY `slot_id` IS AN OPAQUE, VALIDATED INTEGER AND NOT A NAMED ENUM
-- ('weapon'/'head'/...).  The wire-level meaning of "which slot" a real
-- equip occupies is exactly the open RE question this round could not
-- close (`ItemAttr@0x39` bit-shift semantics, `notes_to_chief/
-- reference_codex_attr/PF_ATTR_FIELD_SEMANTICS.tsv:478` -- "gameplay
-- identity is not uniquely bound to Data or an exact UI slot").  Naming a
-- CHECK-constrained enum now would mean guessing which numbers exist,
-- exactly what `COO-DECISION 20260901_1059` forbids ("no unknown field
-- guessed as zero" extends to no unknown category invented as a name).
-- The column stores whatever slot number a future caller is told to write,
-- bounded only to a byte (0..255, `ItemAttr`'s `+0x39` field is one byte
-- per `PF_ATTR_FIELD_SEMANTICS.tsv:478`) so a caller's typo of a larger
-- int is still refused before it reaches the row.
--
-- WHY `item_identity` (THE BAG-INSTANCE ID) AND `item_template_id` BOTH,
-- NOT JUST ONE.  `character_skills` stores one raw client id because a
-- skill has no per-instance identity; an equipped ITEM does: the same
-- `ItemAttrState.identity` this project already threads through
-- `inventory.py`/`item_operate_res_hypothesis.py` distinguishes "the sword
-- with this bag identity" from "any sword of this template", and a caller
-- that only ever has the template id on hand (e.g. re-deriving what a
-- fresh character's starting gear equips) still has a value to write in
-- the template column.  Both are stored so a reader never needs to guess
-- which one a given caller populated.
--
-- WHY `UNIQUE(character_id, slot_id)`, NOT `UNIQUE(character_id,
-- item_identity)`.  One character can only wear one item AT a slot at a
-- time -- a second `equip_item` call for a slot already occupied is meant
-- to REPLACE the occupant (an item swap), the same everyday action
-- `commit_ground_drop`'s "second writer for one key" scenario explicitly
-- is NOT (that one is a real collision this project refuses loudly). This
-- door's write side therefore uses `INSERT OR REPLACE` against this exact
-- constraint, deliberately mirroring `write_typed_attributes`' upsert
-- shape rather than `grant_starting_skills`' `INSERT OR IGNORE` (a skill
-- grant is idempotent-on-repeat; an equip call is a fresh state change
-- every time, even when it repeats the same item in the same slot).
--
-- WHY NO FOREIGN KEY BEYOND `characters(id)`.  Same shape `011` uses:
-- every normal connection runs `PRAGMA foreign_keys=ON`
-- (`store.connect`), so an orphan write is refused by SQLite itself.
CREATE TABLE character_equipment (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(id),
    slot_id INTEGER NOT NULL
        CHECK(typeof(slot_id)='integer' AND slot_id BETWEEN 0 AND 255),
    item_identity INTEGER NOT NULL
        CHECK(typeof(item_identity)='integer'
              AND item_identity BETWEEN 0 AND 9223372036854775807),
    item_template_id INTEGER NOT NULL
        CHECK(typeof(item_template_id)='integer'
              AND item_template_id BETWEEN 0 AND 4294967295),
    equipped_at TEXT NOT NULL,
    UNIQUE(character_id, slot_id)
);

-- The read half (`SQLiteStore.list_equipped_items`) always filters by
-- `character_id`; this index is what keeps that a lookup instead of a scan,
-- the same reason `character_skills_by_character` exists in `011`.
CREATE INDEX character_equipment_by_character ON character_equipment(character_id);
