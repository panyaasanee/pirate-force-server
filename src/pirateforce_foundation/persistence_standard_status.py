"""LANE-DB / PLAYER-CHARACTER piece 2 scaffold: typed, level-indexed access
to the client's own per-level progression table, pinned to the committed
copy.

WHY THIS FILE EXISTS AND WHAT IT DOES NOT DO.
``COO-DECISION 20260904_1450`` item 6 named this as LANE-DB's starting
reserve task: "piece 2, the part that does not wait on RE -- a scaffold that
reads ``STANDARD_STATUS`` per level from the table, DEFAULT value
unchanged".  Piece 2 of ``COO-ORDER 20260904_0329`` ("seed values from
``CHARCREATE_CLASS``/``STANDARD_STATUS`` instead of the constant DEFAULT
100") is still blocked exactly where ``RE-229`` left it: CLOSED
BOUNDED-NEGATIVE (a method ceiling, not a "not yet tried") on the one
question that would let a character's five ability stats be seeded from
anything but that constant -- no field or consumer anywhere in the
committed corpus crosswalks ``CHARCREATE_CLASS.s_SCORE``'s six components to
the five wire ``ActorAttr`` ability fields.  ``migrations/
009_character_birth_defaults.sql``'s ``hp_current``/``hp_max DEFAULT 100``
is untouched by this file, and ``COO-DECISION 20260904_0942`` ("item 4
means existing defaults only, ``1607`` stands, no migration") still governs
every one of the 17 columns that decision left ``NULL``.  This module
writes NOTHING -- no migration, no ``store.py`` call, no character row --
and changes no existing seed value.  It has no caller anywhere in this
repository as of the round that added it.

WHAT THIS MODULE DOES DO.  ``CONSTDATA_TH__STANDARD_STATUS.tsv`` is a
plain, already-committed gamedata table -- ``class_catalog.py``'s own
docstring names it as LANE-DB's territory under the same ``0329`` order --
and reading it needs no RE at all, unlike the ``s_SCORE`` crosswalk
``RE-229`` closed.  Exactly ONE of its seven columns is an independently
proven consumer, cited BY NAME in the docstring of LANE-B's ``HYP-PF-020``
progression-delta encoder module (deliberately not spelled out as a literal
string here -- that module's own ``ContainmentTests`` scans every
``src/pirateforce_foundation/*.py`` file for its filename and this lane has
no business tripping that guard, the same reason ``persistence_class_id.py``
never names a sibling module it deliberately does not import): the client's
own XP bar (``0x519299``) divides displayed experience by
``STANDARD_STATUS[level+1].n_EXP_CURRENTLV``.  That module's
``unspent_ability_points`` field (mask bit ``0x00000010``, offset ``+0x80``)
is cited THERE only against a UI spinner-cap address (``0x57DD7A``) -- no
gamedata table, no ``n_POINT_ABILITY``, appears anywhere in that citation.
The reading "``n_POINT_ABILITY`` is the per-level grant that field carries"
below is this module's OWN inference from the two columns' names and roles,
never independently proven or cited by any STATS-PROG-001/``RE-229`` result
-- pf-adversary (round ``epxry7``) caught an earlier draft of this
paragraph stating it as a citation, which it is not.  Treat it exactly like
any other unlabeled hypothesis in this project: not to be built on as if it
were measured.  This module is the typed READ ACCESSOR for the table the
one proven fact (the XP-bar column) and the one unproven guess
(``n_POINT_ABILITY``) are both about, built once so the next round that
needs a row does not hand-copy one out of the TSV.

WHAT IT DELIBERATELY DOES NOT ANSWER.  This table has no STR/CON/DEX/INT/
PER columns -- ``n_POINT_ABILITY`` is, AT MOST, a POINT BUDGET granted at a
level, not a seeded stat value, and turning a budget into an actual
starting stat total is exactly the ``RE-229`` question this module does not
reopen -- and even the "budget" reading itself is the unproven guess named
above, not a fact this module or any prior round has measured.  Nothing
here resolves piece 2; it only removes "no typed reader exists yet" from
the list of reasons piece 2 cannot move once ``RE-229``'s ceiling is ever
lifted by a result this lane does not control.
"""
from __future__ import annotations

from dataclasses import dataclass
import csv
import hashlib
from pathlib import Path

_DATA_PATH = Path(__file__).parent / "data" / "standard_status.tsv"
# sha256 of the byte-for-byte copy of pf_bridge/gamedata/tables/
# CONSTDATA_TH__STANDARD_STATUS.tsv committed alongside this module; checked
# at import time so a future hand-edit fails loudly instead of silently
# drifting from the client's table (same pattern as
# class_catalog.SOURCE_SHA256 / persistence_class_id's re-check of it).
SOURCE_SHA256 = (
    "d7794acfe3261a16c52a1b8235ad685a2a40d2ddfaaa226a44f2e74b009f94c4"
)


class StandardStatusError(KeyError):
    """The committed table could not answer a lookup: wrong type, a level
    outside its 1..255 range, or the committed copy no longer matches
    ``SOURCE_SHA256``.  Never a guessed or synthesized row."""


@dataclass(frozen=True)
class StandardStatusRow:
    """One row of ``CONSTDATA_TH__STANDARD_STATUS.tsv``, typed, unmodified."""

    level: int
    exp_currentlv: int
    point_ability: int
    deadloss: int
    pvp_exp: int
    pvp_sp: int
    pvp_money: int
    defence_constant: int


def _load_rows() -> dict[int, StandardStatusRow]:
    """Read, hash-check and parse the committed table.  A plain function
    (not inlined at module scope) so a test can point ``_DATA_PATH`` at a
    corrupted temp copy and call this directly, the same guard-testing
    pattern ``persistence_class_id._slot_rhand_by_class_id`` uses."""
    raw = _DATA_PATH.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != SOURCE_SHA256:
        raise StandardStatusError(
            "standard_status.tsv sha256 mismatch: expected %s, got %s -- "
            "table drifted from the pinned client source"
            % (SOURCE_SHA256, actual_sha)
        )
    rows: dict[int, StandardStatusRow] = {}
    with _DATA_PATH.open("r", encoding="ascii", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for record in reader:
            row = StandardStatusRow(
                level=int(record["n_ID"]),
                exp_currentlv=int(record["n_EXP_CURRENTLV"]),
                point_ability=int(record["n_POINT_ABILITY"]),
                deadloss=int(record["n_DEADLOSS"]),
                pvp_exp=int(record["n_PVP_EXP"]),
                pvp_sp=int(record["n_PVP_SP"]),
                pvp_money=int(record["n_PVP_MONEY"]),
                defence_constant=int(record["n_DEFENCE_CONSTANT"]),
            )
            if row.level in rows:
                raise StandardStatusError(
                    "standard_status.tsv duplicate n_ID %d" % row.level
                )
            rows[row.level] = row
    return rows


# Built once at import time; the sha256 check inside `_load_rows` is what
# makes this safe to trust without re-reading the file on every lookup.
STANDARD_STATUS_ROWS: dict[int, StandardStatusRow] = _load_rows()
STANDARD_STATUS_MIN_LEVEL = min(STANDARD_STATUS_ROWS)
STANDARD_STATUS_MAX_LEVEL = max(STANDARD_STATUS_ROWS)


def standard_status_row(level: int) -> StandardStatusRow:
    """The committed table's row for ``level``, or a fail-closed refusal.

    ``level`` must be an ``int`` (``bool`` excluded -- ``type(level) is not
    int`` rejects it, since ``type(True) is bool``) inside the table's own
    ``[STANDARD_STATUS_MIN_LEVEL, STANDARD_STATUS_MAX_LEVEL]`` range;
    anything else raises ``StandardStatusError`` naming the reason.  No
    default is ever synthesized for a level the table does not carry.
    """
    if type(level) is not int:
        raise StandardStatusError(
            "standard status level must be an int, got %r" % (level,)
        )
    if level not in STANDARD_STATUS_ROWS:
        raise StandardStatusError(
            "standard status level %d outside committed range %d..%d"
            % (level, STANDARD_STATUS_MIN_LEVEL, STANDARD_STATUS_MAX_LEVEL)
        )
    return STANDARD_STATUS_ROWS[level]
