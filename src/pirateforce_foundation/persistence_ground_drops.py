"""LANE-DB / the ground-drop persistence door -- the row type it hands back.

Round `5d02mu`, `COO-DECISION 20260903_1843`: `migrations/010_ground_drops.
sql` gives the `ground_drops` table; `SQLiteStore.commit_ground_drop` and
`SQLiteStore.list_ground_drops_for_scene` (`store.py`) are the write and the
readback.  This module holds only the row shape those two methods return.

WHY A SEPARATE MODULE INSTEAD OF A TYPE INLINE IN `store.py`.  This lane's
charter (`COO-DECISION 20260901_1100`) draws its write zone as new
`persistence_*.py` modules plus new methods added to `store.py` -- the same
shape `persistence_vitals.py`'s `DamageOutcome`/`HealOutcome` already use
for the doors in `store.py` that return them.

WHY THIS DOES NOT IMPORT `mob_loot`.  `mob_loot.GroundDrop` (`mob_loot.py:
2164`) is the object LANE-B holds in memory and will eventually hand this
door's write method the fields of; this dataclass's field NAMES and ORDER
mirror it on purpose, so a future caller can pass one apart without a
second translation table.  But this lane's charter forbids touching
`mob_loot.py`, and reading a type out of it into `store.py` would still
make the persistence layer depend on a game-logic module for its own return
type -- the wrong direction for a "bare door" whose whole first-round scope
is write-then-read-back (`COO-DECISION 20260903_1843` point 5).  This class
does not validate anything a `GroundDrop` would (no f32-grid check on `x`/
`y`/`z`, no drop-key lane-block check) -- it is the row exactly as the table
holds it, once `SQLiteStore.commit_ground_drop`'s own checks have already
let it in.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class GroundDropRow:
    """One row read back from the ``ground_drops`` table.

    ``scene`` is the value exactly as it was written -- ``migrations/
    010_ground_drops.sql`` explains why the table does not fold it, and why
    folding happens only for the ``UNIQUE`` constraint and for lookup, in a
    column this row does not carry.  Two rows in the same real scene can
    legally show two different ``scene`` spellings here if two callers wrote
    two spellings; nothing in this door normalises that away.
    """

    id: int
    scene: str
    drop_key: int
    item_id: int
    quantity: int
    x: float
    y: float
    z: float
    mob_identity: int
    killer_identity: int
    created_at: str
