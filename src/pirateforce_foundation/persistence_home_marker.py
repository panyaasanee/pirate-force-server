"""LANE-DB / the home-marker persistence door -- the row type it hands back.

`migrations/013_character_home_marker.sql` gives the `character_home_
marker` table; `SQLiteStore.set_home_marker` and `SQLiteStore.
get_home_marker` (`store.py`) are the write and the readback.  This module
holds only the row shape those two methods return -- the same split
`persistence_ground_drops.GroundDropRow` already uses for the ground-drop
door, for the same reason: this lane's charter (`COO-DECISION
20260901_1100`) draws its write zone as new `persistence_*.py` modules plus
new methods added to `store.py`.

WHY THIS DOOR EXISTS.  `notes_to_chief/20260905_1154_COO-DECISION-db-
takes-no-world-work-home-marker-persistence-row-queued-after-1044-
LANE-DB.md` point 3(b), answering a live refusal measured in R317
(`notes_to_chief/20260905_1125_KA1A-R317-RESULTS-*.md`): quest 3205
("born again") refuses every attempt today with
`COLUMBUS_QUEST3205_BORNAGAIN_REFUSED reason=no_home_marker_persistence_
row_evidence` because there is nowhere in this database to read or write
which scene is a character's home.  This door is that nowhere, filled in.

WHAT THIS ROW IS NOT.  It is not a full position -- see the migration's own
docstring for why one scene id is the whole fact this round proves a
requirement for, and why a spawn point inside that scene is a later
round's question, not a guess this door makes today.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class HomeMarkerRow:
    """One row read back from the ``character_home_marker`` table.

    ``home_scene_id`` is the scene a "born again" respawn should return the
    character to -- the same integer scene-id space ``character_positions.
    scene_id`` already uses (``0 <= home_scene_id <= 0xFFFF``, matching
    ``SQLiteStore.save_position``'s own range check), not a separate
    identifier space this door invents.
    """

    character_id: int
    home_scene_id: int
    updated_at: str
