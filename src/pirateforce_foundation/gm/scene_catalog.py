"""GM-004: scene id -> GM scene name catalog.

Source: pf_bridge/gamedata/tables/TEXTDATA_TH__SCENE_NAME_TIP.tsv, copied
byte-for-byte into ``gm/data/gm_scene_name_tip.tsv`` (this is the "แมพ GM"
the owner asked for -- 330 GM-labeled scene names shipped in the client's own
data, not anything this lane invented).

    SOURCE_SHA256 below is the sha256 of that copy; it is checked at import
    time against the committed file so a future edit -- accidental or not --
    fails loudly instead of silently drifting from the client's table.

This module answers "what scene id does this GM scene name refer to" and
back.  It does not answer "does warping to this scene id work" -- that is a
runtime/wire question outside a static gamedata table's evidence tier (see
AGENTS.md evidence grades; this table is grade A, a committed client
artifact, and stays grade A only for "this id has this name").
"""
from __future__ import annotations

from pathlib import Path
import csv
import hashlib

_DATA_PATH = Path(__file__).parent / "data" / "gm_scene_name_tip.tsv"

SOURCE_SHA256 = "f9076cfc3c14433b376811437d68375d5dd1ce1ef2c7a50dbc1d4e4d241bfa3a"


def _load_rows() -> list[tuple[int, str, str]]:
    raw = _DATA_PATH.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != SOURCE_SHA256:
        raise RuntimeError(
            f"gm_scene_name_tip.tsv sha256 mismatch: expected {SOURCE_SHA256}, "
            f"got {actual_sha} -- table drifted from the pinned client source, "
            "re-derive from pf_bridge/gamedata before trusting this catalog"
        )
    rows: list[tuple[int, str, str]] = []
    with _DATA_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader)
        assert header == ["n_ID", "s_SCENE_NAME", "s_GM_SCENE_NAME"], header
        for row in reader:
            n_id, scene_name, gm_scene_name = row
            rows.append((int(n_id), scene_name.strip(), gm_scene_name.strip()))
    return rows


_ROWS = _load_rows()

SCENE_ID_TO_GM_NAME: dict[int, str] = {n_id: gm_name for n_id, _, gm_name in _ROWS}
SCENE_ID_TO_NAME: dict[int, str] = {n_id: name for n_id, name, _ in _ROWS}
SCENE_COUNT = len(_ROWS)


def gm_scene_name(scene_id: int) -> str:
    """The GM-facing scene name for scene_id, e.g. 1 -> 'Port Royal'."""
    try:
        return SCENE_ID_TO_GM_NAME[scene_id]
    except KeyError as exc:
        raise KeyError(f"scene_id {scene_id} is not in the GM scene catalog") from exc


def scene_ids_named(gm_scene_name_query: str) -> list[int]:
    """All scene_ids whose GM scene name matches exactly (many names repeat)."""
    return [
        n_id for n_id, name in SCENE_ID_TO_GM_NAME.items() if name == gm_scene_name_query
    ]


def is_known_scene_id(scene_id: int) -> bool:
    return scene_id in SCENE_ID_TO_GM_NAME
