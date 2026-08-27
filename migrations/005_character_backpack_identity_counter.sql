-- 005_character_backpack_identity_counter.sql
-- COO-DECISION 20260826_0950 (c): a counter derived from "what is still in the
-- bag" (e.g. MAX(item_identity)+1 over the surviving rows) reissues a freed
-- identity the moment its row is gone -- mob_loot already proved this is a
-- real bug, not a theoretical one, and the client's clear-by-identity /
-- place-by-slot pickup loop is exactly the shape that a repeated identity
-- confuses.  This column is a monotonic per-character counter that is never
-- derived from present rows again once it exists; the item lane
-- (mob_pickup.py) marks new issuance through it once it lands (see
-- issued_through in that module).
--
-- Naming note for whichever lane wires this column in (mob_pickup.py's own
-- nonclaim 14 flags the exact hazard): this value is EXCLUSIVE, the next
-- free identity to hand out, matching the column name literally.  It is one
-- MORE than mob_pickup.next_item_identity()'s own `issued_through` parameter,
-- which that function documents as INCLUSIVE (the highest identity already
-- issued).  Passing this column's value straight through as `issued_through`
-- without subtracting 1 first would skip one identity per issuance -- wasteful,
-- not unsafe, but still the wrong number.
--
-- Default 5 satisfies SQLite's ADD COLUMN NOT NULL requirement (a constant);
-- the UPDATE immediately below overwrites every existing row with the real
-- next-free value computed from that character's own current items, so the
-- constant is only ever observed transiently mid-migration, never read back.
ALTER TABLE character_backpacks
    ADD COLUMN next_item_identity INTEGER NOT NULL DEFAULT 5
    CHECK(next_item_identity BETWEEN 1 AND 9223372036854775807);

UPDATE character_backpacks
SET next_item_identity = (
    SELECT COALESCE(MAX(item_identity), 4) + 1
    FROM character_backpack_items
    WHERE character_backpack_items.character_id = character_backpacks.character_id
);
