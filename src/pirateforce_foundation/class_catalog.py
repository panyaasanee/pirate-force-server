"""LANE-CS: player class (profession) registry, pinned to the committed
client table.

Source: pf_bridge/gamedata/tables/CONSTDATA_TH__CHARCREATE_CLASS.tsv, copied
byte-for-byte into ``data/charcreate_class.tsv`` by
``tools/pf_class_skill_starting_kit_extract.py`` (that tool's docstring is
the fuller scope note; read it before extending this module).

    SOURCE_SHA256 below is the sha256 of that copy; it is checked at import
    time against the committed file so a future hand-edit fails loudly
    instead of silently drifting from the client's table.  It does NOT by
    itself prove the copy still matches ../pf_bridge -- that is a separate,
    ``BRIDGE_GAMEDATA``-guarded check in ``tests/test_class_catalog.py`` that
    re-runs the extractor tool and diffs the result (pf-adversary, round
    iazmrv: a self-hash alone "keeps matching itself forever regardless of
    what pf_bridge does").

WHAT THIS MODULE ANSWERS.  Which of the 5 selectable classes an id names, and
which 4 skill ids (from ``CHARCREATE_CLASS.s_SKILL_1..4``) it starts with.

WHAT THIS MODULE DOES NOT ANSWER (explicit nonclaims, all measured by
pf-adversary round iazmrv before this module existed):

  - Ability/base stats (STR/CON/AGI/INT/PER, HP/MP).  ``s_SCORE`` on this same
    table and ``CONSTDATA_TH__STANDARD_STATUS.tsv`` are LANE-DB's territory
    under COO-ORDER 20260904_0329 item 2 (deadline the same round this module
    was written) -- s_SCORE's semantics have never been RE'd in this project
    (grep ``reports/PF_JOB001_CHARCREATE_CLASS_STATIC_BOUNDARY_20260816.md``:
    it counts s_SCORE among "37 other columns" and decodes none of them).
    ``CONSTDATA_TH__POTENTIAL.tsv``, the one table
    ``docs/FUNCTIONAL_COVERAGE.json`` names as the real ability-stat
    candidate, ships header-only with zero data rows in this snapshot.
  - Main/sub-profession structure.  No column on this table encodes it.  The
    Thai phrase inside ``TEXTDATA_TH__SKILL_TEXT`` row 40000
    ("secondary profession cannot use this skill") confirms the *design
    concept* exists, but nothing here derives a relation from it.
  - A 6th class.  ``CONSTDATA_TH__SKILL_CONTEXT.tsv`` row 45000 (icon
    ``ICON_Class_Voodooist_s``) is a lead for an unselectable/future class --
    see the extractor tool's docstring -- not a row this module carries.
  - Not to be confused with pf_bridge's ``FACTPACK_L2_CLASSCENSUS001``, a
    census of ~1327 C++ RTTI *engine* classes.  Unrelated sense of "class."
"""
from __future__ import annotations

from pathlib import Path
import csv
import hashlib

_DATA_PATH = Path(__file__).parent / "data" / "charcreate_class.tsv"

SOURCE_SHA256 = "2a2668ab38d7a4501cfec8fada9d140f80527b8a4f0f85bfb1c4269e39b7f4c7"

_ICON_PREFIX = "Icon_Class_"


class ClassCatalogError(RuntimeError):
    """Raised when the committed table has drifted or a lookup fails."""


def _class_name_from_icon(icon: str) -> str:
    if not icon.startswith(_ICON_PREFIX):
        raise ClassCatalogError(
            "s_ICON %r does not start with %r -- the naming convention this "
            "module relies on to derive a class name changed" % (icon, _ICON_PREFIX))
    return icon[len(_ICON_PREFIX):]


def _skill_ids(field: str) -> int:
    # Fields look like "40000;1" -- skill id, then a count this module does
    # not interpret (that belongs to the skill/learn-request side, not here).
    skill_id, _, _rest = field.partition(";")
    return int(skill_id)


def _load_rows() -> list[dict]:
    raw = _DATA_PATH.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != SOURCE_SHA256:
        raise ClassCatalogError(
            "charcreate_class.tsv sha256 mismatch: expected %s, got %s -- "
            "table drifted from the pinned client source, re-derive with "
            "tools/pf_class_skill_starting_kit_extract.py before trusting "
            "this catalog" % (SOURCE_SHA256, actual_sha))
    with _DATA_PATH.open("r", encoding="ascii", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
    return rows


_ROWS = _load_rows()

CLASS_ID_TO_NAME: dict[int, str] = {}
CLASS_ID_TO_ICON: dict[int, str] = {}
CLASS_ID_TO_STARTING_SKILL_IDS: dict[int, tuple[int, int, int, int]] = {}

for _row in _ROWS:
    _class_id = int(_row["n_ID"])
    _icon = _row["s_ICON"]
    CLASS_ID_TO_NAME[_class_id] = _class_name_from_icon(_icon)
    CLASS_ID_TO_ICON[_class_id] = _icon
    CLASS_ID_TO_STARTING_SKILL_IDS[_class_id] = (
        _skill_ids(_row["s_SKILL_1"]),
        _skill_ids(_row["s_SKILL_2"]),
        _skill_ids(_row["s_SKILL_3"]),
        _skill_ids(_row["s_SKILL_4"]),
    )

CLASS_IDS: tuple[int, ...] = tuple(sorted(CLASS_ID_TO_NAME))
CLASS_COUNT = len(CLASS_IDS)


def class_name(class_id: int) -> str:
    """The class name derived from CHARCREATE_CLASS's own s_ICON field."""
    try:
        return CLASS_ID_TO_NAME[class_id]
    except KeyError as exc:
        raise KeyError("class_id %r is not in the class catalog" % (class_id,)) from exc


def starting_skill_ids(class_id: int) -> tuple[int, int, int, int]:
    """The 4 skill ids (s_SKILL_1..4 order) class_id starts with."""
    try:
        return CLASS_ID_TO_STARTING_SKILL_IDS[class_id]
    except KeyError as exc:
        raise KeyError("class_id %r is not in the class catalog" % (class_id,)) from exc


def is_known_class_id(class_id: int) -> bool:
    return class_id in CLASS_ID_TO_NAME
