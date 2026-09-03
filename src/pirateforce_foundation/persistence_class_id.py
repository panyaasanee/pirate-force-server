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
``gamedata/tables/CONSTDATA_TH__CHARCREATE_CLASS.tsv`` (lives in the
``pf_bridge`` repo, not this one; the five rows are transcribed below
verbatim, cell by cell), are ALL FIVE mutually distinct on every one of the
three columns.  So a character whose avatar body carries exactly one class's
(chest, leggings, rhand) triple can only be that class among these five --
provided the character-creation screen sends that row's item ids for those
slots unmodified, which is the one part of this still not independently
confirmed for more than one class (JOB-001's single ``test01`` capture
matches the Gladiator row on all three fields; a second class was never
captured to confirm the crossing).

The decoder for those three fields already exists and is already proven, in
a sibling module of this package this file deliberately never names in its
own text.  That sibling's own docstring says why: "this module is a CHECK,
not a wiring" (``COO-DECISION 20260902_0543``, Rule 14.13(d)), and its own
test enforces the no-caller property with a hard, whole-repo TEXT scan (not
just an import check) for its own module name across every file under
``src/pirateforce_foundation``, ``current``, ``tools``, ``migrations`` and
``scenarios`` -- which is exactly why this file avoids writing that name as
a literal token anywhere in itself, docstring included, rather than relying
on a reader to notice an import.  This module respects that boundary on
purpose and therefore does not import it: it takes the three slot values as
already-decoded plain integers, so lifting the isolation guard to wire a
real decode call is a separate, visible, reviewed change for whoever owns
that guard (see the CORE-REQUEST this round's letter opens), not something
this file does by a side door.

So ``resolve_class_id`` is a MATCHER over three already-known integers, not
a decoder: it returns a class id only on an EXACT, UNAMBIGUOUS match against
the sourced table, and ``None`` on anything else.  ``None`` is the fail-closed
answer required by the owner's rule relayed in ``COO-DECISION 20260901_1059``:
a field nobody has measured for THIS character is a named gap, never a guess.
Callers must treat ``None`` the same way -- leave ``class_id`` unwritten, not
zero, not a default.
"""
from __future__ import annotations

# Transcribed from ``gamedata/tables/CONSTDATA_TH__CHARCREATE_CLASS.tsv``
# (pf_bridge repo), columns n_ID / n_DRESS_CHEST / n_DRESS_LEGGINGS /
# n_SLOT_RHAND, one tuple per data row of that file in file order.  All four
# columns are mutually unique across all five rows in the committed file --
# checked by ``test_all_five_presets_are_pairwise_distinct_on_every_slot``
# in ``tests/test_persistence_class_id.py``, so a rename or an added class in
# a future copy of that TSV that breaks the uniqueness this module relies on
# fails a test instead of silently mismatching a character.
CLASS_PRESETS: tuple[tuple[int, int, int, int], ...] = (
    # (class_id, n_DRESS_CHEST, n_DRESS_LEGGINGS, n_SLOT_RHAND)
    (1, 2300026, 2300027, 2200002),   # Icon_Class_Gladiator
    (2, 2300038, 2300039, 2200003),   # Icon_Class_Paladin
    (4, 2300002, 2300003, 2200006),   # Icon_Class_Sniper
    (16, 2300083, 2300084, 2200005),  # Icon_Class_Necromancer
    (32, 2300014, 2300015, 2200008),  # Icon_Class_Sorcerer
)


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
    ``CLASS_PRESETS``.  No case here returns a number that was not read
    verbatim off a sourced table row.
    """
    if dress_chest is None or dress_leggings is None or slot_rhand is None:
        return None
    matches = [
        class_id
        for class_id, chest, leggings, rhand in CLASS_PRESETS
        if (dress_chest, dress_leggings, slot_rhand) == (chest, leggings, rhand)
    ]
    if len(matches) != 1:
        return None
    return matches[0]
