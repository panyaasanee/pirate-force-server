"""GM-042 prep: item id -> name/category/stack catalog for the future
``item <id> <n>`` GM command.

Source (pf_bridge/gamedata, as of this extraction):
    CONSTDATA_TH__ITEM_MISC.tsv         1,646 rows  sha256 8cd1774d42230938
        d429f8fe849f1073467489daac9ac265689bfa70302d5292
    CONSTDATA_TH__ITEM_CONSUMABLES.tsv  1,260 rows  sha256 04586d54730fee23
        b7120ec03d7e7b5b17345d23fe4c1d946e7e71222e698e29
    CONSTDATA_TH__ITEM_QUEST.tsv          579 rows  sha256 9bb9ca8f416812cf
        724284146d704a8ece86f61e612cdd688005caf9f860a05c
    TEXTDATA_TH__ITEM_MISC_TIP.tsv        sha256 163cf4d0862e7f5797d9dcb0
        e110e4f5cd78e089800b5e9328326499a5585ed2
    TEXTDATA_TH__ITEM_CONSUMABLES_TIP.tsv sha256 8f9fac6170750bbdc4410420
        498f60563e15653523f1a4461cbae1a84f1046dc
    TEXTDATA_TH__ITEM_QUEST_TIP.tsv       sha256 2818474f4e9c3ce983d74edc
        b9dc8f7207e1a351c04bb7146de5aacdc098b346

Each CONST table's own ``n_ID`` set is a strict subset of its matching TIP
file's ids (TIP carries extra unused/reserved names), so every row copied
here has a resolved display name -- see the extraction check that ran
against the source tables (0 missing names in all three categories).

Extracted columns only (``n_ID``, display ``s_NAME`` from the TIP table,
``n_QUATITY_STACK`` = max stack size from the CONST table), copied
byte-for-byte-per-row into three local TSVs so this module never reads
across the pf_bridge/pirate-force-server repo boundary at runtime:
    gm/data/gm_item_misc.tsv         (1,646 rows + header)
    gm/data/gm_item_consumable.tsv   (1,260 rows + header)
    gm/data/gm_item_quest.tsv          (579 rows + header)

    Each SOURCE_SHA256_* constant below is the sha256 of the matching
    local copy (not the pf_bridge source table -- this module never reads
    that file), checked at import time so an accidental edit to the copy
    fails loudly.

IMPORTANT finding for whoever wires this catalog to a runtime command:
item ``n_ID`` is NOT a single global namespace -- the same numeric id is
reused across the misc/consumable/quest tables for unrelated items, e.g.
id 6 is "Earth Element" (misc) but "Fruit Wine Jar" (consumable); id 1 is
"Adventure Key" (misc) but "Sky Lantern" (quest). Measured overlap: 230
ids shared between misc/consumable, 213 between misc/quest, 239 between
consumable/quest (out of 1,646 / 1,260 / 579 rows respectively). A GM
command that takes a bare ``item <id> <n>`` with no category will be
ambiguous for any id that collides -- see ``item_category()`` below,
which returns every category an id resolves in rather than picking one
silently.

Same evidence-tier note as ``scene_catalog.py``/``npc_switch_catalog.py``:
this table only answers "what is item_id called and what category/stack
size does it declare" -- it says nothing about whether granting one to a
player currently does anything, because ``item <id> <n>`` is not wired to
any runtime effect yet (see GM-042 prep note in notes_to_chief).
"""
from __future__ import annotations

from pathlib import Path
import csv
import hashlib

_DATA_DIR = Path(__file__).parent / "data"

_CATEGORY_FILES: dict[str, str] = {
    "misc": "gm_item_misc.tsv",
    "consumable": "gm_item_consumable.tsv",
    "quest": "gm_item_quest.tsv",
}

SOURCE_SHA256_MISC = "a3df3b791258027d9a233be07242eadfd8db496287bcf78b14765e9455ad6cd7"
SOURCE_SHA256_CONSUMABLE = "6348e1ea5761d24cb0f1d7795b3e7b6d3cce1625d578f7fce935a33e3eeec965"
SOURCE_SHA256_QUEST = "649829df9b359907bf39e0b7d4c1507f5cbf977a902c2a605fc1db272f4d5dd5"

_SOURCE_SHA256_BY_CATEGORY: dict[str, str] = {
    "misc": SOURCE_SHA256_MISC,
    "consumable": SOURCE_SHA256_CONSUMABLE,
    "quest": SOURCE_SHA256_QUEST,
}


class _ItemRow(tuple):
    __slots__ = ()

    def __new__(cls, item_id: int, name: str, max_stack: int):
        return super().__new__(cls, (item_id, name, max_stack))

    @property
    def item_id(self) -> int:
        return self[0]

    @property
    def name(self) -> str:
        return self[1]

    @property
    def max_stack(self) -> int:
        return self[2]


def _load_category(category: str) -> dict[int, _ItemRow]:
    data_path = _DATA_DIR / _CATEGORY_FILES[category]
    raw = data_path.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    expected_sha = _SOURCE_SHA256_BY_CATEGORY[category]
    if actual_sha != expected_sha:
        raise RuntimeError(
            f"gm_item_{category}.tsv sha256 mismatch: expected {expected_sha}, "
            f"got {actual_sha} -- table drifted from the pinned extraction, "
            "re-derive from pf_bridge/gamedata before trusting this catalog"
        )
    rows: dict[int, _ItemRow] = {}
    with data_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader)
        assert header == ["n_ID", "s_NAME", "n_QUATITY_STACK"], header
        for row in reader:
            n_id, name, stack = row
            rows[int(n_id)] = _ItemRow(int(n_id), name.strip(), int(stack))
    return rows


_BY_CATEGORY: dict[str, dict[int, _ItemRow]] = {
    category: _load_category(category) for category in _CATEGORY_FILES
}

MISC_ITEM_COUNT = len(_BY_CATEGORY["misc"])
CONSUMABLE_ITEM_COUNT = len(_BY_CATEGORY["consumable"])
QUEST_ITEM_COUNT = len(_BY_CATEGORY["quest"])

# Ordered so category resolution / iteration is deterministic.
CATEGORIES: tuple[str, ...] = ("misc", "consumable", "quest")


def item_category(item_id: int) -> tuple[str, ...]:
    """Every category item_id resolves in (usually one, sometimes more --
    see the module docstring's id-collision note). Empty tuple = unknown."""
    return tuple(cat for cat in CATEGORIES if item_id in _BY_CATEGORY[cat])


def _validate_category(category: str) -> None:
    if category not in _BY_CATEGORY:
        raise ValueError(f"unknown item category {category!r}, expected one of {CATEGORIES}")


def is_known_item(item_id: int, category: str | None = None) -> bool:
    """True if item_id exists. Pass ``category`` to scope the check to one
    of the three tables and sidestep cross-category id collisions."""
    if category is not None:
        _validate_category(category)
        return item_id in _BY_CATEGORY[category]
    return bool(item_category(item_id))


def item_name(item_id: int, category: str | None = None) -> str:
    """Display name for item_id. If the id collides across categories and
    ``category`` is not given, raises ValueError naming the candidates --
    callers must disambiguate rather than silently getting one at random."""
    if category is not None:
        _validate_category(category)
    cats = (category,) if category is not None else item_category(item_id)
    if not cats or (category is not None and item_id not in _BY_CATEGORY[category]):
        raise KeyError(f"item_id {item_id} is not a known item"
                        + (f" in category {category!r}" if category else ""))
    if len(cats) > 1:
        raise ValueError(
            f"item_id {item_id} is ambiguous across categories {cats} -- "
            "pass category= to disambiguate"
        )
    return _BY_CATEGORY[cats[0]][item_id].name


def item_max_stack(item_id: int, category: str) -> int:
    """Max stack size (n_QUATITY_STACK) for item_id within one category.
    Category is required here (unlike item_name) because stack size can
    differ across colliding ids and silently picking one is unsafe."""
    _validate_category(category)
    return _BY_CATEGORY[category][item_id].max_stack
