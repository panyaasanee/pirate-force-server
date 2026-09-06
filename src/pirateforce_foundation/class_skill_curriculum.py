"""LANE-CS: per-class FULL curriculum skill list, pinned to committed tables.

Source: pf_bridge/gamedata/tables/CONSTDATA_TH__CURRICULUM.tsv (class code ->
skill id), CONSTDATA_TH__SKILL_CONTEXT.tsv (per-skill fields) and
TEXTDATA_TH__SKILL_TEXT.tsv (display titles), copied into
data/class_skill_curriculum.tsv / data/skill_context_curriculum.tsv /
data/skill_text_curriculum.tsv by
``tools/pf_class_skill_curriculum_extract.py`` -- read that tool's docstring
first, it carries the mapping proof this whole module rests on.

    All three SOURCE_SHA256 constants below are the sha256 of those copies,
    checked at import time so a hand-edit fails loudly.  Real upstream drift
    is caught separately by the ``BRIDGE_GAMEDATA``-guarded test in
    ``tests/test_class_skill_curriculum.py`` that re-runs the extractor and
    diffs.

WHAT THIS ADDS OVER ``skill_catalog.py``.  That module carries the 8-skill
STARTING KIT and its docstring says plainly that no committed table was known
to map a class to its full skill list, citing four measured blockers.  This
module retires blocker 3 of those four.  ``CURRICULUM.n_PPCLASS`` was recorded
as "a different class code than ``CHARCREATE_CLASS.n_ID``"; the committed data
says otherwise -- the six distinct n_PPCLASS values are 1, 2, 4, 16, 32 and
1024, and the first five ARE the five CHARCREATE_CLASS n_ID values.

    The mapping is not asserted on "the numbers look the same."  It is
    corroborated by a second, independent witness -- each class's own "Basic
    Training" skill id from its own ``s_SKILL_2`` row, which is a block
    prefix -- and every skill id CURRICULUM files under a class code lands
    inside that same class's own block, 5 of 5, including the two crossed
    pairs (class 2 Paladin -> 43xxx while class 4 Sniper -> 41xxx, so the
    id order is NOT the class-id order and a wrong mapping would not
    survive).  The extractor re-measures this on every run and refuses to
    write if it ever stops holding; ``test_class_skill_curriculum.py`` pins
    it as a test besides.

SO THIS IS A LOWER BOUND, NOT "EVERY SKILL".  Retiring blocker 3 does not
retire the other three.  The client's own quest Lua scripts
(``gamedata/lua/Quest/q_add_skill*.lua``) grant further skills out of band,
so what CURRICULUM files under a class is a floor on that class's real skill
list.  Every accessor here is named after the table it came from
(``curriculum_skill_ids``, never ``all_skills_of_class``) so no caller can
mistake the floor for the ceiling.

THE 1024 BUCKET IS NOT A SIXTH CLASS.  1024 is not a CHARCREATE_CLASS n_ID.
What is measured: it holds 11 skill ids, none inside any of the five class
blocks, and it contains exactly the three ids every one of the five classes
shares in CHARCREATE_CLASS (99 Normal Attack, 110 Strive Jump, 111 VIP
Strive Jump).  Reading that as "the every-class bucket" is the obvious
inference but it is an inference:

    [assumption of lane CS, pending COO confirmation] 1024 == "granted to
    all classes".  If COO rules otherwise, the revert is local -- callers
    use ``shared_bucket_skill_ids()``, which is named after the raw bucket,
    and no per-class accessor folds 1024 in.  ``curriculum_skill_ids(class)``
    deliberately returns ONLY that class's own bucket, so a wrong reading of
    1024 cannot silently widen any class's list.

NO SKILL TYPE IS DECODED HERE, AND ONE TEMPTING SHORTCUT IS EXPLICITLY
REFUSED.  SKILL_CONTEXT still has no basic/attack/AOE/buff/heal/passive enum
and no MP column, so raw rows are carried verbatim under the client's own
column names, exactly as ``skill_catalog.py`` does.  In particular, within
these 137 curriculum ids all 15 rows at ``n_PASSIVE == 1`` have zero
``n_CD``, zero ``n_STAMINA_COST`` and blank ``s_CAST_BEHAVIOR``, and every
one of their titles contains "Discipline" -- a clean-looking split that
would decode ``n_PASSIVE`` as the passive flag.  IT IS NOT ONE, and this
module does not ship that accessor:

    ``NPassiveIsNotATypeColumnTests`` in ``tests/test_skill_catalog.py``
    (round 6o11t1) already falsified that shortcut twice over, and the full
    table still says so this round -- table-wide, 118 rows carry
    ``n_PASSIVE == 1`` and 97 of them have a NON-blank ``s_CAST_BEHAVIOR``
    with 96 carrying a non-zero ``n_CD``, i.e. most n_PASSIVE=1 skills in
    the game are actively cast.  ``n_PASSIVE`` also takes six distinct
    values table-wide (0..5), not two.  The tidy split above is a property
    of THIS 137-row subset, not a decode of the column, and
    ``test_class_skill_curriculum.py`` pins it as a correlation with the
    counter-evidence attached so a future round cannot quietly promote it.

ZERO PRODUCTION CALLERS, DELIBERATELY.  This is a data module; it answers
reads and gates nothing.  Nothing in the skill-learning path calls it yet
(that path is still blocked on ``GT-276``), and no production caller reads a
skill id at all today -- see ``damage_by_skill.py``.  It is the table half of
LANE-CS queue item 1 ("catalog of every class and every skill per class"),
now covering 137 skill ids across all 5 classes instead of the starting 8.
"""
from __future__ import annotations

from pathlib import Path
import csv
import hashlib

_CURRICULUM_PATH = Path(__file__).parent / "data" / "class_skill_curriculum.tsv"
_CONTEXT_PATH = Path(__file__).parent / "data" / "skill_context_curriculum.tsv"
_TEXT_PATH = Path(__file__).parent / "data" / "skill_text_curriculum.tsv"

CURRICULUM_SOURCE_SHA256 = (
    "26b4b54437b1995d506bc52a711c2d77783ad4fd8f40450f079e66240da1d4b2")
CONTEXT_SOURCE_SHA256 = (
    "d0d5d0ac84c15df31e7d87843fb183659480c0e52d82c93983f831018e4e1f0d")
TEXT_SOURCE_SHA256 = (
    "7e552497197bc338af7d184ba2e986e6e4de5f94ff312b7864c708d72fce7087")

# The raw SKILL_CONTEXT columns this module carries verbatim, by their own
# client-given names -- no renaming, no reinterpretation.  Same list as
# skill_catalog._CONTEXT_COLUMNS, on purpose: the two catalogs describe
# overlapping skill ids and must not disagree about what a column is called.
_CONTEXT_COLUMNS = (
    "n_LEVEL_LEARN", "n_PASSIVE", "n_ISCLASS", "n_CD", "n_TARGET",
    "n_EQUIPTYPE", "n_EQUIPTYPE_LHAND", "n_STAMINA_COST",
    "s_CAST_CONDITION", "s_CAST_BEHAVIOR",
    "n_LEVELS", "f_SP_LEVE1", "f_SP_LEVEL2PLUS",
)

# The sixth n_PPCLASS bucket.  Deliberately not called a class id.
SHARED_BUCKET_CODE = 1024


class ClassSkillCurriculumError(RuntimeError):
    """Raised when a committed table has drifted or a lookup fails."""


def _check_sha256(path: Path, expected: str) -> bytes:
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ClassSkillCurriculumError(
            "%s sha256 mismatch: expected %s, got %s -- table drifted from "
            "the pinned client source, re-derive with "
            "tools/pf_class_skill_curriculum_extract.py before trusting this "
            "catalog" % (path.name, expected, actual))
    return raw


def _load_rows(path: Path, expected_sha: str) -> list:
    _check_sha256(path, expected_sha)
    with path.open("r", encoding="ascii", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


_CURRICULUM_ROWS = _load_rows(_CURRICULUM_PATH, CURRICULUM_SOURCE_SHA256)
_CONTEXT_ROWS = _load_rows(_CONTEXT_PATH, CONTEXT_SOURCE_SHA256)
_TEXT_ROWS = _load_rows(_TEXT_PATH, TEXT_SOURCE_SHA256)

SKILL_ID_TO_TITLE: dict[int, str] = {
    int(row["n_ID"]): row["s_SKILL_TITLE"] for row in _TEXT_ROWS
}

SKILL_ID_TO_RAW_CONTEXT: dict[int, dict[str, str]] = {
    int(row["n_ID"]): {column: row[column] for column in _CONTEXT_COLUMNS}
    for row in _CONTEXT_ROWS
}

_BUCKETS: dict[int, list[int]] = {}
for _row in _CURRICULUM_ROWS:
    _BUCKETS.setdefault(int(_row["n_PPCLASS"]), []).append(int(_row["n_SKILL"]))

# Every bucket except the shared one is a class id -- see the module
# docstring for the two-witness proof and the extractor for its re-measure.
CLASS_ID_TO_CURRICULUM_SKILL_IDS: dict[int, tuple[int, ...]] = {
    code: tuple(sorted(ids))
    for code, ids in _BUCKETS.items()
    if code != SHARED_BUCKET_CODE
}
SHARED_BUCKET_SKILL_IDS: tuple[int, ...] = tuple(
    sorted(_BUCKETS.get(SHARED_BUCKET_CODE, ())))

CURRICULUM_CLASS_IDS: tuple[int, ...] = tuple(
    sorted(CLASS_ID_TO_CURRICULUM_SKILL_IDS))
CURRICULUM_SKILL_IDS: tuple[int, ...] = tuple(sorted(SKILL_ID_TO_RAW_CONTEXT))
SKILL_COUNT = len(CURRICULUM_SKILL_IDS)

if set(SKILL_ID_TO_TITLE) != set(SKILL_ID_TO_RAW_CONTEXT):
    raise ClassSkillCurriculumError(
        "skill_context_curriculum.tsv and skill_text_curriculum.tsv name "
        "different skill ids (%s vs %s) -- the two committed copies drifted "
        "from each other" % (
            sorted(SKILL_ID_TO_RAW_CONTEXT), sorted(SKILL_ID_TO_TITLE)))

_ids_in_curriculum = set()
for _ids in _BUCKETS.values():
    _ids_in_curriculum.update(_ids)
if _ids_in_curriculum != set(SKILL_ID_TO_RAW_CONTEXT):
    raise ClassSkillCurriculumError(
        "class_skill_curriculum.tsv names skill ids the per-skill copies do "
        "not carry (or vice versa) -- the three committed copies drifted "
        "from each other; re-derive all three with "
        "tools/pf_class_skill_curriculum_extract.py")


def _require_skill(skill_id: int) -> dict:
    try:
        return SKILL_ID_TO_RAW_CONTEXT[skill_id]
    except KeyError:
        raise ClassSkillCurriculumError(
            "skill id %r is not in the curriculum catalog (it carries %d "
            "ids); this module refuses to answer for a skill it has no "
            "committed row for" % (skill_id, SKILL_COUNT)) from None


def curriculum_skill_ids(class_id: int) -> tuple[int, ...]:
    """The skill ids CURRICULUM files under this class, ascending.

    A LOWER BOUND on the class's real skill list, not proven to be all of it
    -- see the module docstring.  Returns only the class's own bucket; the
    1024 bucket is deliberately never folded in here.
    """
    try:
        return CLASS_ID_TO_CURRICULUM_SKILL_IDS[class_id]
    except KeyError:
        raise ClassSkillCurriculumError(
            "class id %r has no CURRICULUM bucket (this catalog carries %s)"
            % (class_id, list(CURRICULUM_CLASS_IDS))) from None


def shared_bucket_skill_ids() -> tuple[int, ...]:
    """The ids under raw n_PPCLASS bucket 1024, ascending.

    Named after the raw bucket on purpose: whether 1024 means "every class"
    is an assumption pending COO confirmation (module docstring).
    """
    return SHARED_BUCKET_SKILL_IDS


def skill_title(skill_id: int) -> str:
    """The client's own s_SKILL_TITLE for this skill."""
    _require_skill(skill_id)
    return SKILL_ID_TO_TITLE[skill_id]


def skill_raw_context(skill_id: int) -> dict[str, str]:
    """A copy of the raw SKILL_CONTEXT columns, client column names intact."""
    return dict(_require_skill(skill_id))


def level_learn(skill_id: int) -> int:
    """Raw n_LEVEL_LEARN -- the level the client's table files this skill at."""
    return int(_require_skill(skill_id)["n_LEVEL_LEARN"])


def cooldown_raw(skill_id: int) -> int:
    """Raw n_CD.  Named 'raw' because this lane has not RE'd its unit."""
    return int(_require_skill(skill_id)["n_CD"])


def stamina_cost(skill_id: int) -> int:
    """Raw n_STAMINA_COST, named as the table names it -- NOT claimed to be MP."""
    return int(_require_skill(skill_id)["n_STAMINA_COST"])


def curriculum_by_level_learn(class_id: int) -> tuple[tuple[int, int], ...]:
    """``(level_learn, skill_id)`` pairs for a class, ascending by level.

    The read a skill-learning screen or a skill-point validator would want
    first.  Ties break on skill id so the order is total and stable.
    """
    return tuple(sorted(
        (level_learn(skill_id), skill_id)
        for skill_id in curriculum_skill_ids(class_id)))


__all__ = [
    "ClassSkillCurriculumError",
    "SHARED_BUCKET_CODE",
    "CLASS_ID_TO_CURRICULUM_SKILL_IDS",
    "SHARED_BUCKET_SKILL_IDS",
    "CURRICULUM_CLASS_IDS",
    "CURRICULUM_SKILL_IDS",
    "SKILL_COUNT",
    "SKILL_ID_TO_TITLE",
    "SKILL_ID_TO_RAW_CONTEXT",
    "curriculum_skill_ids",
    "shared_bucket_skill_ids",
    "skill_title",
    "skill_raw_context",
    "level_learn",
    "cooldown_raw",
    "stamina_cost",
    "curriculum_by_level_learn",
]
