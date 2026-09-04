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

[UPDATE, round `kd06fo`]: ``cooldown_seconds()`` and ``stamina_cost()`` join
``level_learn()`` as named accessors for ``n_CD``/``n_STAMINA_COST`` -- the
"ค่า MP/CD/ระยะ" (MP/CD/range values) half of LANE-CS's queue item 1 that the
starting-kit catalog carried in ``skill_raw_context()`` since round `iazmrv`
but never gave a named reader.  Neither has a caller outside this module's
own tests today, same as ``level_learn()`` before it: the catalog answers
reads, it does not yet gate anything, because no lane calls
``resolve_skill_damage`` in production yet either (see ``damage_by_skill.py``).
``n_TARGET`` is deliberately NOT given an accessor here: unlike ``n_CD``/
``n_STAMINA_COST`` its raw values (0 for every non-99 id, 1 for 99) have no
unit or direction this project has RE'd, so naming it "range" or "target
mode" would be exactly the invented-meaning mistake this section warns
against for ``n_PASSIVE`` -- ``skill_raw_context()`` still carries it
verbatim for a future round that does RE it.

[UPDATE, this round]: ``own_class_bit()`` is a THIRD, narrower kind of
accessor -- unlike ``cooldown_seconds()``/``stamina_cost()`` it does not
accept every starting-kit id.  ``tools/pf_class_skill_starting_kit_extract.py``'s
own docstring already measured (round `iazmrv`, before this catalog was
code) that ``n_ISCLASS`` is "self-referential UI bookkeeping" for the 5
per-class "Basic Training" rows -- each row's OWN class bit, matching
``class_catalog``'s ``class_id`` for the class that grants it -- and
explicitly "not a general skill-to-class foreign key usable for other skill
ids."  ``own_class_bit()`` therefore only answers for those 5 ids (raising
``SkillCatalogError`` for 99/110/111, whose raw ``n_ISCLASS`` values 63/0/0
have no established meaning here) and ``tests/test_skill_catalog.py`` cross-
checks every one of the 5 against ``class_catalog.starting_skill_ids()``,
not against a hand-typed table. The same extractor docstring records a 6th
value (id 45000, bit 8, the unselectable "Voodooist" lead) this catalog does
not carry -- which is also why 99's raw ``n_ISCLASS`` of 63 (0b111111, one
bit more than the 5 known classes OR together) is left unexplained rather
than read as "usable by every class."

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
    accessor on ``n_PASSIVE``; see ``tests/test_skill_catalog.py``'s
    ``NPassiveIsNotATypeColumnTests`` for the pinned counter-examples that
    make this a red test, not a comment, if anyone re-copies the shortcut.

    DECODING ``s_CAST_CONDITION``/``s_CAST_BEHAVIOR`` HAS ALSO BEEN TRIED,
    AND IT ALSO FAILED.  A round reading this docstring might reasonably
    read the paragraph above as "the untried next step is to decode
    ``s_CAST_CONDITION``/``s_CAST_BEHAVIOR`` (``GO(0)``, ``CHASE(n)``,
    ``SKIP(n)``, ``ISVIP_I(n)``, ...)" -- that step has already been run,
    as ``RE-232`` (pf_bridge CLIENT_RE_QUEUE.md, closed round `tp9rpy`,
    result letter pf_bridge/notes_to_chief/20260904_1055_RE-232-RESULT-
    BOUNDED-NEGATIVE-EIGHT-ROWS-DO-NOT-CLASSIFY.md), and it came back
    BOUNDED-NEGATIVE: the grammar has real condition/behavior structure
    (loader span ``[0x00754450,0x007549A6)``, parser span
    ``[0x007534F0,0x007537D4)``, both span-pinned in the result letter), but
    among these 8 skills there is no independently-labeled AOE, self-buff or
    heal example to check a classifier against, and the tokens actually seen
    (``GO``, ``CHASE``, ``SKIP``, ``ISVIP_I``) are control-flow/edge data,
    not a type enum -- ``GO(0)`` alone appears on the one real attack (99)
    and both movement skills (110/111), so it cannot even separate attack
    from movement.  Re-deriving this span from scratch is not the next
    round's starting point any more; a NEW ticket adding at least 8 more
    independently-labeled rows (2 single-target, 2 AOE, 2 self-buff, 2 heal)
    is, per the result letter's own suggestion, and no such ticket exists
    yet as of this round.
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

# Derived from the client's own titles (SKILL_ID_TO_TITLE), not typed by
# hand: the 5 ids own_class_bit() answers for.  See the module docstring's
# [UPDATE, this round] paragraph for why these 5 and not the other 3.
_BASIC_TRAINING_SKILL_IDS: tuple[int, ...] = tuple(
    skill_id for skill_id in STARTING_KIT_SKILL_IDS
    if SKILL_ID_TO_TITLE[skill_id].endswith(" Basic Training")
)


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


def cooldown_seconds(skill_id: int) -> int:
    """The client's own ``n_CD`` column, unmodified.  Named ``_seconds``
    because the two known values in this catalog (skill 99's 25, movement's
    1) are consistent with a seconds unit, not because any table or report
    in this project states the unit -- treat the name as a guess about UNIT
    only, never about what the column measures beyond "cooldown"."""
    return int(skill_raw_context(skill_id)["n_CD"])


def stamina_cost(skill_id: int) -> int:
    """The client's own ``n_STAMINA_COST`` column, unmodified.  See the
    module docstring: this is the closest cost field the table has, named as
    the table names it -- this function does not claim it means "MP"."""
    return int(skill_raw_context(skill_id)["n_STAMINA_COST"])


def own_class_bit(skill_id: int) -> int:
    """The client's own ``n_ISCLASS`` column for skill_id -- but ONLY for the
    5 per-class "Basic Training" ids (see the module docstring's [UPDATE,
    this round] paragraph). Raises :class:`SkillCatalogError` for the other
    3 starting-kit ids (99/110/111), whose raw ``n_ISCLASS`` values have no
    established meaning, and ``KeyError`` for an id outside the catalog
    entirely, same as every other accessor here."""
    if skill_id not in SKILL_ID_TO_RAW_CONTEXT:
        raise KeyError("skill_id %r is not in the starting-kit catalog" % (skill_id,))
    if skill_id not in _BASIC_TRAINING_SKILL_IDS:
        raise SkillCatalogError(
            "own_class_bit(%r) refused: n_ISCLASS is only established as a "
            "self-referential class bit for the 5 Basic Training skill ids "
            "%r (tools/pf_class_skill_starting_kit_extract.py's own "
            "docstring) -- see this function's docstring for why the other "
            "starting-kit ids are not given a meaning here" % (
                skill_id, _BASIC_TRAINING_SKILL_IDS))
    return int(skill_raw_context(skill_id)["n_ISCLASS"])


def is_known_skill_id(skill_id: int) -> bool:
    return skill_id in SKILL_ID_TO_RAW_CONTEXT
