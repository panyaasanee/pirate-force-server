"""LANE-CS: starting-skill-kit catalog, pinned to the committed client
tables.

Source: pf_bridge/gamedata/tables/CONSTDATA_TH__SKILL_CONTEXT.tsv (per-skill
fields) and TEXTDATA_TH__SKILL_TEXT.tsv (display titles), filtered to the 8
starting-kit skill ids and copied into data/skill_context_starting_kit.tsv /
data/skill_text_starting_kit.tsv by
``tools/pf_class_skill_starting_kit_extract.py`` -- read that tool's
docstring first, it is the scope note for this whole module.

    Both SOURCE_SHA256 constants below are the sha256 of those copies,
    checked at import time so a hand-edit fails loudly.  Real upstream drift
    is caught separately by the ``BRIDGE_GAMEDATA``-guarded test in
    ``tests/test_skill_catalog.py`` that re-runs the extractor and diffs.

SCOPE: 8 SKILL IDS, NOT "EVERY SKILL."  This module carries exactly the ids
named by ``class_catalog.CLASS_ID_TO_STARTING_SKILL_IDS`` across all 5
classes: 99 (Normal Attack), 110 (Strive Jump), 111 (VIP Strive Jump), and
one "Basic Training" skill per class (40000 Gladiator, 41000 Sniper, 42000
Necromancer, 43000 Paladin, 44000 Sorcerer).  pf-adversary (round iazmrv)
measured that no committed table maps a class to its FULL skill list -- see
the extractor tool's docstring for the four separate reasons (self-
referential n_ISCLASS bookkeeping, a same-id-range different-domain sailor
skill table, a different class-code scheme in CURRICULUM, and further skills
granted out of band by the client's own storyline scripts -- see the
extractor tool's docstring for the exact script paths).  Extending this
catalog to a class's full skill list is future RE work, not something this
module claims to already do.

RAW FIELDS, NOT INVENTED TYPES.  SKILL_CONTEXT has no "basic attack / attack /
AOE / buff / heal / passive" enum column and no MP column (``n_STAMINA_COST``
is the closest cost field, named as the table names it -- this module does
not claim it means "MP").  ``n_PASSIVE`` is carried as the client's own raw
value precisely so nobody downstream mistakes a raw column for a decoded
classification.

    ROUND 6o11t1 CHECKED THE OBVIOUS SHORTCUT AND IT IS A TRAP.
    ``n_PASSIVE`` is not boolean -- table-wide it takes 6 distinct values (0:
    1 row, 1: 118, 2: 1016, 3: 910, 4: 84, 5: 36), which is suspicious given
    the mission's target taxonomy also has 6 categories.  It is NOT that
    taxonomy.  Two independent checks this round (pf-static-re's keyword/
    title cross-reference across all 6 values, and pf-adversary re-deriving
    the 8 starting-kit ids directly) falsify it the same way: skill 99
    ("Normal Attack", the one skill in this whole catalog that is
    unambiguously a basic attack) has ``n_PASSIVE=2`` -- the SAME value as
    110/111 ("Strive Jump" / "VIP Strive Jump", movement skills, not attacks)
    -- while the five per-class "Basic Training" skills (40000/41000/42000/
    43000/44000) all sit at a different single value, ``n_PASSIVE=1``, along
    with 97 of 118 value-1 rows table-wide being actively-cast attack skills
    with a non-blank ``s_CAST_CONDITION`` (e.g. id 5101 "Hammer of Judgment",
    ``CHASE(5101)``) -- so "1" cannot mean "passive, nothing is cast" either.
    Table-wide, a single skill title ("Warm Cure") appears at two different
    ids with two different ``n_PASSIVE`` values (7172 -> 3, 44007 -> 2), and
    heal/buff/AOE keyword hits are smeared across 3-5 of the 6 values each,
    never isolated in one.  The one real pattern found is id-range
    clustering (value 3 is 91% ids 3000-3999, monster "Bite"/"performing"
    titles; value 5 is 97% ids 0-999, ship cannon titles) -- this reads as
    "which subsystem/owner row this is" (player vs. monster-state vs.
    ship-weapon), not a gameplay type tag.  Do not build a ``skill_type()``
    accessor on ``n_PASSIVE``; the next round that wants one has to start
    from decoding ``s_CAST_CONDITION``/``s_CAST_BEHAVIOR`` (a small command
    language: ``GO(0)``, ``CHASE(n)``, ``SKIP(n)``, ``ISVIP_I(n)``, ...) --
    see ``tests/test_skill_catalog.py``'s
    ``NPassiveIsNotATypeColumnTests`` for the pinned counter-examples that
    make this a red test, not a comment, if anyone re-copies the shortcut.
"""
from __future__ import annotations

from pathlib import Path
import csv
import hashlib

_CONTEXT_PATH = Path(__file__).parent / "data" / "skill_context_starting_kit.tsv"
_TEXT_PATH = Path(__file__).parent / "data" / "skill_text_starting_kit.tsv"

CONTEXT_SOURCE_SHA256 = "1b6f95a3f4adc465319c5c5e6f56b212a58ff92cb512906bbfafca926a18d458"
TEXT_SOURCE_SHA256 = "4cf4030fe66084accd0842937ba71ff5c23addaa21f23cb0ab380b141132db5a"

# The raw SKILL_CONTEXT columns this module carries verbatim, by their own
# client-given names -- no renaming, no reinterpretation.
_CONTEXT_COLUMNS = (
    "n_LEVEL_LEARN", "n_PASSIVE", "n_ISCLASS", "n_CD", "n_TARGET",
    "n_EQUIPTYPE", "n_EQUIPTYPE_LHAND", "n_STAMINA_COST",
    "s_CAST_CONDITION", "s_CAST_BEHAVIOR",
)


class SkillCatalogError(RuntimeError):
    """Raised when a committed table has drifted or a lookup fails."""


def _check_sha256(path: Path, expected: str) -> bytes:
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise SkillCatalogError(
            "%s sha256 mismatch: expected %s, got %s -- table drifted from "
            "the pinned client source, re-derive with "
            "tools/pf_class_skill_starting_kit_extract.py before trusting "
            "this catalog" % (path.name, expected, actual))
    return raw


def _load_context_rows() -> list[dict]:
    _check_sha256(_CONTEXT_PATH, CONTEXT_SOURCE_SHA256)
    with _CONTEXT_PATH.open("r", encoding="ascii", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _load_text_rows() -> list[dict]:
    _check_sha256(_TEXT_PATH, TEXT_SOURCE_SHA256)
    with _TEXT_PATH.open("r", encoding="ascii", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


_CONTEXT_ROWS = _load_context_rows()
_TEXT_ROWS = _load_text_rows()

SKILL_ID_TO_TITLE: dict[int, str] = {
    int(row["n_ID"]): row["s_SKILL_TITLE"] for row in _TEXT_ROWS
}

SKILL_ID_TO_RAW_CONTEXT: dict[int, dict[str, str]] = {
    int(row["n_ID"]): {column: row[column] for column in _CONTEXT_COLUMNS}
    for row in _CONTEXT_ROWS
}

STARTING_KIT_SKILL_IDS: tuple[int, ...] = tuple(sorted(SKILL_ID_TO_RAW_CONTEXT))
SKILL_COUNT = len(STARTING_KIT_SKILL_IDS)

if set(SKILL_ID_TO_TITLE) != set(SKILL_ID_TO_RAW_CONTEXT):
    raise SkillCatalogError(
        "skill_context_starting_kit.tsv and skill_text_starting_kit.tsv name "
        "different skill ids (%s vs %s) -- the two committed copies drifted "
        "from each other" % (
            sorted(SKILL_ID_TO_RAW_CONTEXT), sorted(SKILL_ID_TO_TITLE)))


def skill_title(skill_id: int) -> str:
    try:
        return SKILL_ID_TO_TITLE[skill_id]
    except KeyError as exc:
        raise KeyError("skill_id %r is not in the starting-kit catalog" % (skill_id,)) from exc


def skill_raw_context(skill_id: int) -> dict[str, str]:
    """The client's own SKILL_CONTEXT fields for skill_id, unmodified strings."""
    try:
        return dict(SKILL_ID_TO_RAW_CONTEXT[skill_id])
    except KeyError as exc:
        raise KeyError("skill_id %r is not in the starting-kit catalog" % (skill_id,)) from exc


def level_learn(skill_id: int) -> int:
    return int(skill_raw_context(skill_id)["n_LEVEL_LEARN"])


def is_known_skill_id(skill_id: int) -> bool:
    return skill_id in SKILL_ID_TO_RAW_CONTEXT
