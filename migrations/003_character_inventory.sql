CREATE TABLE character_backpacks (
    character_id INTEGER PRIMARY KEY REFERENCES characters(id) ON DELETE CASCADE,
    base_mask INTEGER NOT NULL CHECK(base_mask = 255),
    base_identity INTEGER NOT NULL CHECK(base_identity = 0),
    range_mask INTEGER NOT NULL CHECK(range_mask = 1),
    updated_at TEXT NOT NULL
);

CREATE TABLE character_backpack_items (
    character_id INTEGER NOT NULL REFERENCES character_backpacks(character_id) ON DELETE CASCADE,
    item_identity INTEGER NOT NULL CHECK(item_identity BETWEEN 0 AND 9223372036854775807),
    template_id INTEGER NOT NULL CHECK(template_id BETWEEN 0 AND 4294967295),
    quantity INTEGER NOT NULL CHECK(quantity BETWEEN 0 AND 65535),
    slot INTEGER NOT NULL CHECK(slot BETWEEN 0 AND 65535),
    raw_u8_38 INTEGER NOT NULL CHECK(raw_u8_38 BETWEEN 0 AND 255),
    raw_u8_39 INTEGER NOT NULL CHECK(raw_u8_39 BETWEEN 0 AND 255),
    detail_present INTEGER NOT NULL CHECK(detail_present IN (0,1)),
    PRIMARY KEY(character_id,item_identity),
    UNIQUE(character_id,slot)
);

INSERT INTO character_backpacks(
    character_id,base_mask,base_identity,range_mask,updated_at
)
SELECT id,255,0,1,created_at FROM characters WHERE deleted_at IS NULL;

INSERT INTO character_backpack_items(
    character_id,item_identity,template_id,quantity,slot,
    raw_u8_38,raw_u8_39,detail_present
)
SELECT id,1,2600001,1,0,0,255,0 FROM characters WHERE deleted_at IS NULL
UNION ALL
SELECT id,2,2400901,1,1,0,255,0 FROM characters WHERE deleted_at IS NULL
UNION ALL
SELECT id,3,2600001,1,2,0,255,0 FROM characters WHERE deleted_at IS NULL
UNION ALL
SELECT id,4,2200002,1,3,0,255,0 FROM characters WHERE deleted_at IS NULL;
