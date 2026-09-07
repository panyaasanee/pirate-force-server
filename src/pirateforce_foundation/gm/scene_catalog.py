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


# --- name -> scene_id, the direction an operator at the client needs ------
#
# `gm_scene_name` answers "what is scene 2 called".  An operator sitting at
# the client at 1 a.m. has the opposite question: they know they want the
# island, not that the island is scene 2.  `resolve_gm_scene_name` is that
# direction, and `gm/commands.py`'s `warp` grammar is its only caller today.
#
# THE TABLE IS NOT A FUNCTION.  Measured on the pinned file: 330 rows,
# 294 distinct GM names.  Seven names repeat -- `Hidden Island` alone is on
# 20 scene ids and `Poseidon Island` on 10 -- and FOUR rows carry an empty
# name (ids 13, 137, 138, 141).  So this returns ALL matching ids and lets
# the caller decide; a "first match wins" resolver would have silently sent
# a GM to one of twenty Hidden Islands, and an empty query would have
# matched four scenes at once.  An empty (or whitespace-only) query matches
# NOTHING here, by construction rather than by a caller remembering to
# check.
#
# Folding: leading/trailing space is stripped, internal whitespace runs
# collapse to one space (the shipped table pads every cell with spaces),
# and case folds.  Measured on the pinned file: folding case merges no two
# distinct names, so the fold cannot invent an ambiguity the table does not
# already have -- `test_gm_scene_catalog.py` pins that.


def _fold_gm_scene_name(name: str) -> str:
    """Fold one GM scene name to the key `resolve_gm_scene_name` matches on."""
    return " ".join(name.split()).casefold()


def _build_name_index() -> dict[str, tuple[int, ...]]:
    index: dict[str, list[int]] = {}
    for n_id, _scene_name, gm_name in _ROWS:
        key = _fold_gm_scene_name(gm_name)
        if not key:
            # The four unnamed rows. They are reachable by id and only by id.
            continue
        index.setdefault(key, []).append(n_id)
    return {key: tuple(sorted(ids)) for key, ids in index.items()}


_GM_NAME_TO_SCENE_IDS: dict[str, tuple[int, ...]] = _build_name_index()

GM_NAME_COUNT = len(_GM_NAME_TO_SCENE_IDS)


def resolve_gm_scene_name(query: str) -> tuple[int, ...]:
    """Every scene id whose GM scene name folds to `query`, ascending.

    Empty tuple means no scene carries that name -- including for an empty
    or whitespace-only query, which never matches the table's four unnamed
    rows.  A tuple longer than one means the name is genuinely ambiguous in
    the client's own table; the caller must not pick one.
    """
    if not isinstance(query, str):
        raise TypeError("query must be a str")
    key = _fold_gm_scene_name(query)
    if not key:
        return ()
    return _GM_NAME_TO_SCENE_IDS.get(key, ())
