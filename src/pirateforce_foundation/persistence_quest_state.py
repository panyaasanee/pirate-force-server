"""LANE-DB / the quest-state persistence doors -- the row types they hand
back.

`migrations/019_character_quest_state.sql` gives the two bare tables;
`SQLiteStore.set_quest_flag` / `get_quest_flag` / `set_quest_counter` /
`get_quest_counter` / `increment_quest_counter` (`store.py`) are the writes
and the read-backs.  This module holds only the row shapes those five
methods return -- the same split `persistence_home_marker.HomeMarkerRow`
and `persistence_ground_drops.GroundDropRow` already use, for the same
reason: this lane's charter (`COO-DECISION 20260901_1100`) draws its write
zone as new `persistence_*.py` modules plus new methods added to
`store.py`.

WHY THESE DOORS EXIST.  `PANYA 20260908_1520` (carried in `pf_bridge/
NOW.md`) puts the quest-flag store first, and `notes_to_chief/
20260908_1642_COO-DECISION-quest-flags-schema-comes-before-the-bulk-skill-
rows-LANE-DB.md` routes it here with one instruction: implement the
contract this lane itself published in `notes_to_chief/20260905_2212_LANE-
DB-TO-LANE-Q-quest-state-doors-declared-and-opened-this-round.md`, do not
redesign it.  LANE-Q's half already exists and calls these names
(`notes_to_chief/20260908_1647_LANE-Q-TO-LANE-DB-the-quest-state-doors-are-
not-on-main.md`: `lua_api/quest_state_store.StoreBackedQuestStateStore`),
so every name and every signature here is `2212`'s, verbatim.

WHAT THESE ROWS ARE NOT.  They carry no meaning for the numbers they hold.
`flag_value` is whatever `Quest.SetFlag` was handed (`Quest.Active`,
`Quest.Finish`, ... are LANE-Q's constants read out of `QUESTDATA_*`, not
values this database knows), and `counter_value` is a count whose TARGET
lives in the quest definition, not here -- `2212`'s own "things this round
deliberately does not do": no pass/fail logic, no enum, no automatic reset
when a quest ends.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class QuestFlagRow:
    """One row read back from the ``character_quest_flag`` table.

    ``quest_id`` is the client's own u16 quest id -- the range
    ``columbus_quest_dispatch.py`` already puts on the wire with
    ``legacy.u16tag(0x12, quest_id)``, not a separate identifier space this
    door invents.  ``flag_value`` is an opaque integer (see the module
    docstring): this database stores the number the caller sent and never
    interprets it.
    """

    character_id: int
    quest_id: int
    flag_value: int
    updated_at: str


@dataclass(frozen=True)
class QuestCounterRow:
    """One row read back from the ``character_quest_counter`` table.

    The key is ``(character_id, quest_id, counter_name)`` -- two counters
    inside the SAME quest are two rows, which is the whole reason the name
    is part of the key: ``pf_bridge/gamedata/lua/Quest/q_kill5.lua`` tracks
    two mobs at once inside one quest and neither tracker may overwrite the
    other.
    """

    character_id: int
    quest_id: int
    counter_name: str
    counter_value: int
    updated_at: str
