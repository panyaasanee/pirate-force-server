"""GM-003 support: which NPCs carry the client's own "GM switch" flag.

Source: pf_bridge/gamedata/tables/CONSTDATA_TH__MOBS.tsv (3211 rows, 54
columns, source sha256 3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca
479b7e1b3916b as of this extraction) -- filtered to the 7 rows where
``n_GM_SWITCH == 1``, keeping only ``n_ID``/``s_NAME``, copied into
``gm/data/gm_npc_switch.tsv``.  These are the "NPC กิจกรรม 7 ตัว" the owner's
1630 order letter already found; this module is the first code that turns
that finding into something ``gm/commands.py`` can check against.

    SOURCE_SHA256 below is the sha256 of the extracted copy (not the 3211-row
    source table -- this module never reads that file), checked at import
    time so an accidental edit to the 7-row copy fails loudly.

Same evidence-tier note as ``scene_catalog.py``: this table only answers "is
mob_id one of the 7 client-flagged GM-switch NPCs" -- it says nothing about
whether toggling one on the live server currently does anything, because
``npc on|off`` is not wired to any runtime effect yet (see GM-003 in
docs/GM_LANE.md).
"""
from __future__ import annotations

from pathlib import Path
import csv
import hashlib

_DATA_PATH = Path(__file__).parent / "data" / "gm_npc_switch.tsv"

SOURCE_SHA256 = "484d664741965e767025637bde4c65f93b9c264684bc45bbd3b6bc9fb5ba5237"


def _load_rows() -> list[tuple[int, str]]:
    raw = _DATA_PATH.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != SOURCE_SHA256:
        raise RuntimeError(
            f"gm_npc_switch.tsv sha256 mismatch: expected {SOURCE_SHA256}, "
            f"got {actual_sha} -- table drifted from the pinned client source, "
            "re-derive from pf_bridge/gamedata before trusting this catalog"
        )
    rows: list[tuple[int, str]] = []
    with _DATA_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader)
        assert header == ["n_ID", "s_NAME"], header
        for row in reader:
            n_id, name = row
            rows.append((int(n_id), name.strip()))
    return rows


_ROWS = _load_rows()

NPC_ID_TO_NAME: dict[int, str] = dict(_ROWS)
GM_SWITCH_NPC_COUNT = len(_ROWS)


def is_gm_switchable_npc(mob_id: int) -> bool:
    """True if mob_id is one of the 7 client-flagged (n_GM_SWITCH=1) NPCs."""
    return mob_id in NPC_ID_TO_NAME


def npc_gm_name(mob_id: int) -> str:
    """The client's own name string for a GM-switchable mob_id."""
    try:
        return NPC_ID_TO_NAME[mob_id]
    except KeyError as exc:
        raise KeyError(f"mob_id {mob_id} is not a GM-switchable NPC") from exc
