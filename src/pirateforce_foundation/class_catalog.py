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

WHAT THIS MODULE ANSWERS.  Which of the 5 selectable classes an id names,
which 4 skill ids (from ``CHARCREATE_CLASS.s_SKILL_1..4``) it starts with, and
-- from the table columns alone -- which three ``(hat, chest, leggings)``
value triples the table associates with the class's three character-creation
"look" slots.

STARTING DRESS SETS (COO-DECISION 20260904_0548 item 2) -- table-level fact
ONLY, mechanism still [PROPOSED] not [MEASURED].  The table carries three
parallel column triples -- ``n_DRESS_CHEST``/``n_DRESS_LEGGINGS``, ``_2``,
and ``_3``.  What this module PROVES: those 15 (chest, leggings) values are
internally consistent and pairwise distinct across all 5 classes and all 3
slots.  What it does NOT prove: that slot #2/#3's values are what the client
actually sends for a character created with look #2/#3 picked on screen --
chief's own letter that proposed this accessor
(``pf_bridge/notes_to_chief/20260904_0535_...md`` item D5) labels the
"one column-triple per on-screen look" reading ``[เสนอ] กลไกยังไม่วัด`` and
hedges it on "if the clothing follows the appearance the player actually
picked"; the capture that would measure it (``GT-226``,
``20260904_0549_COO-DECISION...md``) had not run as of this module's
introduction.  Treat ``starting_dress_sets`` as "3 candidate looks per the
table's own column layout", not as a proven character-creation binding,
until GT-226 lands.  There is only one ``n_DRESS_HAT`` column (no
``_2``/``_3``) -- that part IS a plain column-existence fact, not a client
behavior claim -- so the hat slot cannot vary by look in this table and the
same value is the third element of all three sets below.  In this snapshot
``n_DRESS_HAT`` is 0 for every one of the 5 classes; this module returns
that value as read and does not interpret 0 as "no hat" versus a valid
catalog id -- that is out of scope here.  ``persistence_class_id.py``'s
``CLASS_PRESETS`` (LANE-DB, COO-DECISION 20260904_0551) is the intended
consumer: before this accessor existed, that table only matched a player's
chest/leggings against look #1, so a player who picked look #2 or #3 at
creation resolved to no class (chief 0535 D4/D5) -- wiring #2/#3 into
CLASS_PRESETS still inherits the open GT-226 question above.

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

# Each element is (n_DRESS_HAT, chest, leggings) for look #1, #2, #3 in that
# order.  n_DRESS_HAT has no _2/_3 column, so it repeats across all three.
CLASS_ID_TO_STARTING_DRESS_SETS: dict[
    int, tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]
] = {}

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
    _hat = int(_row["n_DRESS_HAT"])
    CLASS_ID_TO_STARTING_DRESS_SETS[_class_id] = (
        (_hat, int(_row["n_DRESS_CHEST"]), int(_row["n_DRESS_LEGGINGS"])),
        (_hat, int(_row["n_DRESS_CHEST_2"]), int(_row["n_DRESS_LEGGINGS_2"])),
        (_hat, int(_row["n_DRESS_CHEST_3"]), int(_row["n_DRESS_LEGGINGS_3"])),
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


def starting_dress_sets(
    class_id: int,
) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    """The 3 (hat, chest, leggings) value triples the table carries for class_id.

    Index 0/1/2 corresponds to the table's chest/leggings column-triple
    #1/_2/_3.  hat is the same value in all three (the table has no per-look
    hat column).  Table-level fact only: whether slot #2/#3 is really what
    the client sends for a character created with on-screen look #2/#3 is
    still unmeasured -- see the module docstring's GT-226 note.
    """
    try:
        return CLASS_ID_TO_STARTING_DRESS_SETS[class_id]
    except KeyError as exc:
        raise KeyError("class_id %r is not in the class catalog" % (class_id,)) from exc


def is_known_class_id(class_id: int) -> bool:
    return class_id in CLASS_ID_TO_NAME
