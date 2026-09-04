"""LANE-DB / PLAYER-CHARACTER: match an already-decoded avatar gear triple
against the game's own class presets, without ever guessing.

WHY THIS FILE EXISTS.  ``PANYA-DECISION 20260904_0328`` / ``COO-ORDER
20260904_0329`` piece 1 ordered "the class she chose must not be dropped":
today ``characters.class_id`` (added by ``migrations/006_character_typed_
attribute_columns.sql``, left NULL by ``009`` on purpose) is never written,
and ``player_wire.PLAYER_LOGIN_CLASS_ID = 1`` sends every character back as
a Gladiator regardless of what she picked (R307 GT-215, ``pf_bridge/
notes_to_chief/20260903_1901_KA1A-R307-RESULTS-...md`` lines 30-36).

WHAT THIS FILE DOES NOT DO, ON PURPOSE.  The R307 letter also measured a raw
byte pattern in ``characters.actor_wire`` -- tag ``0x19`` followed by a u32,
value 1 for a Gladiator pick and 4 for a Sharpshooter pick -- and immediately
flagged it as unconfirmed ("whether tag 0x19 u32 is the class id is for RE
to confirm").  This lane's own prior round already named the trap
(``pf_bridge/notes_to_chief/20260902_1650_LANE-DB-ASK-CHIEF-...md`` point 4.2):
tag ``0x19`` in ``CreateActorVital`` (object offset ``+0x1C``) shares its wire
tag byte with the UNRELATED, independently-proven ``ActorAttr.class_id``
field (object offset ``+0x8C``) that ``player_wire.py`` writes at login --
two different structures, two different offsets, one coincidental tag byte.
``pf_bridge/notes_to_chief/reference_codex_attr/PF_TAG_CENSUS.tsv`` row
``0x19`` for the ``CreateActorVital`` codec records ``proven_semantics =
UNKNOWN``.  The most recent standing ruling on this exact question,
``COO-DECISION 20260903_1943`` point 3, is explicit: *"tag 0x19 = class id
ยังเป็นสมมติฐาน -- ยืนยันจากตาราง gamedata ที่ commit แล้วเท่านั้น ห้ามเปิด RE
ใหม่"* ("tag 0x19 = class id is still a hypothesis -- confirm it only from
already-committed gamedata tables, do not open new RE").  So this module
never reads ``actor_wire``'s tag ``0x19`` at all.

WHAT IT DOES INSTEAD, AND WHY IT TAKES THREE INTEGERS RATHER THAN A BLOB.
The 2026-09-02 round found three OTHER fields that are already independently
proven: three slots of the character's ``AvatarAttr`` body -- ``n_DRESS_CHEST``
(bit 5), ``n_DRESS_LEGGINGS`` (bit 6) and ``n_SLOT_RHAND`` (bit 10) -- and
that the five playable classes' STARTING GEAR on those three slots, per
``CONSTDATA_TH__CHARCREATE_CLASS.tsv``, committed in this repo as
``data/charcreate_class.tsv`` and owned by LANE-CS's ``class_catalog.py``,
are ALL FIVE mutually distinct on every one of the three columns -- provided
the character-creation screen sends that row's item ids for those slots
unmodified, which is the one part of this still not independently confirmed
for more than one class (JOB-001's single ``test01`` capture matches the
Gladiator row on all three fields; a second class was never captured to
confirm the crossing).

THREE LOOKS PER CLASS (``COO-DECISION 20260904_0551`` items D4/D5, chief's
``20260904_0535``).  The table carries three parallel chest/leggings column
triples -- column-triple #1, ``_2`` and ``_3`` -- one per on-screen "look"
choice at character creation.  The first cut of this module only matched
look #1, so a character created with look #2 or #3 picked on screen resolved
to ``None`` (an unnecessary gap, not the "field nobody measured" kind).
``CLASS_PRESETS`` below now carries all three looks' (chest, leggings) pairs
per class -- 15 rows total, still one ``n_SLOT_RHAND`` per class (the table
has no ``_2``/``_3`` right-hand column, so the weapon slot does not vary by
look).  Whether look #2/#3 is really what the client sends for a character
created with that look picked on screen is still open (``class_catalog.py``'s
own docstring hedges the same thing, pending ``GT-226``) -- this module
inherits that same open question, it does not resolve it; see nonclaim 2 in
``tests/test_persistence_class_id.py``.

WHERE THE FIFTEEN ROWS COME FROM, AND WHY THIS ISN'T A SECOND HAND COPY.
``pf-adversary`` (chief's ``20260904_0535`` item D4) measured that the first
cut of this file held its own hand-transcribed copy of the five gear rows
and a docstring claiming the source table "lives in the pf_bridge repo, not
this one" -- both wrong by the time that round landed (the table is
committed here, at ``data/charcreate_class.tsv``, and ``class_catalog.py``
already parses it).  A hand-typed second copy of numbers can drift from the
table silently; nothing would catch a future edit to one copy that forgot
the other.  So ``CLASS_PRESETS`` below is BUILT, not typed: the four/leggings
columns for all three looks come from ``class_catalog.starting_dress_sets``,
that module's own public accessor (already sha256-pinned against the
committed file at ITS import time).  The one column that accessor does not
carry -- ``n_SLOT_RHAND``, which has no per-look ``_2``/``_3`` variant, so
``class_catalog`` never needed it -- is read directly off the same committed
file by ``_slot_rhand_by_class_id`` below, independently re-checked against
``class_catalog.SOURCE_SHA256`` before a single value is trusted.  Nothing
in this module types a gear id as a literal; ``tests/test_persistence_class_id.py``
still keeps one independently hand-typed pin (a second, by-hand transcription
of the same five source rows) so a bug in the BUILDING logic itself -- not
just a stale literal -- still fails a test instead of shipping silently.

The decoder for the three matched fields already exists and is already
proven, in a sibling module of this package this file deliberately never
names in its own text.  That sibling's own docstring says why: "this module
is a CHECK, not a wiring" (``COO-DECISION 20260902_0543``, Rule 14.13(d)),
and its own test enforces the no-caller property with a hard, whole-repo
TEXT scan (not just an import check) for its own module name across every
file under ``src/pirateforce_foundation``, ``current``, ``tools``,
``migrations`` and ``scenarios`` -- which is exactly why this file avoids
writing that name as a literal token anywhere in itself, docstring included,
rather than relying on a reader to notice an import.  This module respects
that boundary on purpose and therefore does not import it: it takes the
three slot values as already-decoded plain integers, so lifting the
isolation guard to wire a real decode call is a separate, visible, reviewed
change for whoever owns that guard (see the CORE-REQUEST this lane's letters
have already opened), not something this file does by a side door.

So ``resolve_class_id`` is a MATCHER over three already-known integers, not
a decoder: it returns a class id only on an EXACT, UNAMBIGUOUS match against
the sourced table (any of the 15 rows), and ``None`` on anything else.
``None`` is the fail-closed answer required by the owner's rule relayed in
``COO-DECISION 20260901_1059``: a field nobody has measured for THIS
character is a named gap, never a guess.  Callers must treat ``None`` the
same way -- leave ``class_id`` unwritten, not zero, not a default.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from . import class_catalog

# The identical committed file `class_catalog.py` parses and sha256-pins
# (`class_catalog.SOURCE_SHA256`) -- same package, same `data/` directory,
# not a second copy of the file or its contents.  Read here only for the one
# column `class_catalog`'s own public accessors never expose (see module
# docstring): `n_SLOT_RHAND` has no per-look `_2`/`_3` variant, so it was
# out of scope for `starting_dress_sets`.
_DATA_PATH = Path(__file__).parent / "data" / "charcreate_class.tsv"


def _slot_rhand_by_class_id() -> dict[int, int]:
    """``n_SLOT_RHAND`` per ``class_id``, read live off the same committed
    table ``class_catalog.py`` pins -- re-checked against THAT module's own
    ``SOURCE_SHA256`` (not a second, independently-chosen hash) so the two
    modules can never silently disagree about which bytes they trust."""
    raw = _DATA_PATH.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != class_catalog.SOURCE_SHA256:
        raise class_catalog.ClassCatalogError(
            "charcreate_class.tsv sha256 mismatch: expected %s, got %s -- "
            "table drifted from the pinned client source (see "
            "class_catalog.py's own guard, which checks the same file)"
            % (class_catalog.SOURCE_SHA256, actual_sha))
    with _DATA_PATH.open("r", encoding="ascii", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return {int(row["n_ID"]): int(row["n_SLOT_RHAND"]) for row in reader}


def _build_class_presets() -> tuple[tuple[int, int, int, int], ...]:
    """One row per (class_id, look) -- 3 looks x 5 classes = 15 rows -- each
    ``(class_id, n_DRESS_CHEST, n_DRESS_LEGGINGS, n_SLOT_RHAND)``.  Built
    entirely from ``class_catalog``'s pinned accessors plus the one column
    read above; no gear id is a literal in this file."""
    rhand_by_class_id = _slot_rhand_by_class_id()
    rows: list[tuple[int, int, int, int]] = []
    for class_id in class_catalog.CLASS_IDS:
        rhand = rhand_by_class_id[class_id]
        for _hat, chest, leggings in class_catalog.starting_dress_sets(class_id):
            rows.append((class_id, chest, leggings, rhand))
    return tuple(rows)


# (class_id, n_DRESS_CHEST, n_DRESS_LEGGINGS, n_SLOT_RHAND) -- 15 rows: one
# per playable class per character-creation "look" (column-triple #1/_2/_3
# of `CONSTDATA_TH__CHARCREATE_CLASS.tsv`).  Built by `_build_class_presets`
# above, not hand-typed -- see the module docstring's "WHERE THE FIFTEEN ROWS
# COME FROM" section.  `test_all_fifteen_presets_are_pairwise_distinct_on_
# the_matched_slots` in `tests/test_persistence_class_id.py` is what makes
# this module's whole matching strategy (an exact triple identifies one
# class) safe to rely on.
CLASS_PRESETS: tuple[tuple[int, int, int, int], ...] = _build_class_presets()


def resolve_class_id(
    dress_chest: int | None,
    dress_leggings: int | None,
    slot_rhand: int | None,
) -> int | None:
    """The class id whose committed gear preset exactly matches these three
    already-decoded ``AvatarAttr`` slot values, or ``None`` if that is not
    decidable.

    ``None`` covers every way this can fail to be a confident answer: any of
    the three arguments is ``None`` (the caller's decode found the field
    absent), or the triple present does not match exactly one row of
    ``CLASS_PRESETS`` (across all three looks -- a class matches on ANY of
    its three rows, never more than one, since the 15 rows are pairwise
    distinct on the matched three columns).  No case here returns a number
    that was not read verbatim off a sourced table row.
    """
    if dress_chest is None or dress_leggings is None or slot_rhand is None:
        return None
    matches = {
        class_id
        for class_id, chest, leggings, rhand in CLASS_PRESETS
        if (dress_chest, dress_leggings, slot_rhand) == (chest, leggings, rhand)
    }
    if len(matches) != 1:
        return None
    return next(iter(matches))
