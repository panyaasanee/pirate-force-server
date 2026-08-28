"""LANE-B / SCENE-IDENTITY-001: the project's one identity rule, and the
places where choosing it is not free.

WHY THIS MODULE EXISTS.  ``COO-DECISION 20260829_0345`` settled a question
this lane raised: a project with two identity rules alive at once ("a Mob-Set
number IS the MOBS.n_ID" vs "the CLINE crosswalk says which MOBS.n_ID it is")
has to re-decide the question every time a scene arrives, and ``GT-078`` is
what a wrong re-decision costs -- a whole town wearing the wrong names.  The
ruling is ONE rule for the whole project: ``cline``.

It attached a mandatory condition, and this module exists to make that
condition executable rather than quoted:

    "ตาราง Bg0002 ที่ regenerate ด้วย cline ต้องออกมาเหมือนเดิมทุกแถว 35/35
     ⇒ ต้องมีเทสพินความเท่ากันนี้ไว้ ถ้าวันไหนมีแถวไหนต่าง ⇒ หยุด ห้าม merge
     และส่งใบถามเจ้าของ"

WHAT THE PIN FOUND, AND WHY THIS LANE DID NOT FLIP Bg0002 THIS ROUND.  The
condition has two halves that were being read as one, and they do not have
the same answer:

    35/35 within Mob-Set 1..35          TRUE.  CLINE type 2 maps every one of
                                        1..35 to the same number.  The
                                        equality COO asked for is real and
                                        pinned below.

    the regenerated table is identical  FALSE.  Bg0002 does not only place
                                        Mob-Set numbers from that block.  Five
                                        of its seventeen shipped placements
                                        (92-96) carry Mob-Set 103, which is
                                        OUTSIDE 1..35, and there the two rules
                                        give different creatures.

So the ruling's own stop condition fires: a row differs, and this lane holds
rather than merging the flip.  ``IDENTITY_RULE`` in
``field_mob_tables_bg0002`` is unchanged this round, deliberately, and the
letter is
``notes_to_chief/20260829_0549_LANE-B-ASK-COO-cline-deletes-five-prison-exile-rows.md``
IN THE pf_bridge REPOSITORY -- this repository has no ``notes_to_chief``.

THE DISAGREEMENT, IN FULL, BECAUSE A COUNT WOULD HIDE IT.  What the five
placements are under each reading, straight from ``CONSTDATA_TH__MOBS``:

    setnum  MOBS 103  rank 1, combat AI 332, outfit M023_000_001_SP3,
                      level 58 -- "Orc Chief", a real hostile that renders
    cline   MOBS 917  rank 0, combat AI 0, outfit INVISIBLE, level 100

Under ``cline`` those five placements do not become a different monster.
They become an invisible, rank-zero, AI-less marker, so the hostility
predicate drops them and the scene ships TWELVE hostiles instead of
seventeen.  That is not a rename; it is five monsters leaving the map, and it
is why this is a question for the owner rather than a regeneration.

WHAT THIS DOES NOT CLAIM.  It does not say ``setnum`` is right for those five
rows.  ``cline`` is the client's own crosswalk and it is the rule this
project chose; MOBS 917 being INVISIBLE is exactly the sort of thing a real
scene file does place.  The honest statement is that the two readings differ
on five rows the owner has never seen either way -- at the time of
``M1P-RESULT-PASS`` (2026-08-28T01:50) Mob-Set 101/102/103/104 were still in
the UNRESOLVED list and shipped nothing, so no sighting supports either
reading -- and that COO's condition says a differing row stops the merge.

AND IT DOES NOT GENERALISE THE 35/35.  This is the trap the pin is really
for.  ``35/35`` is a property of ONE block that happens to start at 1, not a
property of the crosswalk.  Measured over the other scene type in play:

    CLINE type  2  (Bg0002)   45 rows, 35 identical, 10 not
    CLINE type 14 (Bg0015)    51 rows,  0 identical, 51 not

Zero.  For ``Bg0015`` the two rules disagree about EVERY row, which is why
this lane's dormant ``Bg0015`` table is regenerated under ``cline`` in the
same round that holds ``Bg0002`` -- there is no owner ruling on that scene,
nothing is wired to it, and "the rules happen to agree" was never true there
for a single row.

SOURCE, AND WHY THE NUMBERS ARE COMMITTED HERE INSTEAD OF READ.
``CONSTDATA_TH__CLINE.tsv`` lives on the bridge clone, not in this
repository, so a test that reads it can only run where that clone is
checked out.  The blocks below are mined from it and committed, with the
digest of the file they came from; ``tests/test_scene_identity_rule.py``
re-derives them from the bridge clone WHEN it is present and skips loudly
when it is not.  The digest is the thing that makes the committed copy
falsifiable: it is the same ``aa4a55b8...`` that every generated roster
module in this lane records, so a drift in the source shows up as a digest
mismatch rather than as two tables quietly disagreeing.
"""

from __future__ import annotations


#: The project's identity rule, by ruling, not by preference.
#: ``COO-DECISION 20260829_0345``: "เลือกทางเลือกที่ 1 ``cline`` เป็นกฎอ่าน
#: ตัวตนของทุกฉาก ตั้งแต่วันนี้ รวมฉากใหม่ที่ยังไม่เข้ามา".
PROJECT_IDENTITY_RULE = "cline"

#: The older reading, kept named because two scenes still ship under it and a
#: reader has to be able to say which one a table used.
LEGACY_IDENTITY_RULE = "setnum"

SOURCE_DIGESTS = {
    "cline": "aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40",
    "mobs": "3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b",
    "scene_name": "e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b",
}

#: ``SCENE_NAME[s_MODLE_ID].n_CLINE_TYPE`` for the scenes this lane ships a
#: roster for.  Not a full table: the two scenes in play, so a reader can see
#: which block each roster resolves through.
SCENE_CLINE_TYPE = {
    "Bg0002": 2,
    "Bg0015": 14,
}

#: ``CLINE[(n_CLINE_TYPE, n_CREATURE_TYPE)].n_LEADER_BK1`` -- the whole block
#: for each type in play, not just the keys some scene happens to use.  The
#: keys a scene does not use are the point: they are where the next scene's
#: placements will land.
CLINE_BLOCKS = {
    2: {
        1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10,
        11: 11, 12: 12, 13: 13, 14: 14, 15: 15, 16: 16, 17: 17, 18: 18,
        19: 19, 20: 20, 21: 21, 22: 22, 23: 23, 24: 24, 25: 25, 26: 26,
        27: 27, 28: 28, 29: 29, 30: 30, 31: 31, 32: 32, 33: 33, 34: 34,
        35: 35,
        36: 360, 37: 230, 38: 231, 39: 742, 40: 743, 41: 914,
        101: 10003, 102: 10004, 103: 917, 104: 927,
    },
    14: {
        1: 321, 2: 322, 3: 323, 4: 324, 5: 325, 6: 326, 7: 327, 8: 328,
        9: 329, 10: 330, 11: 331, 12: 332, 13: 333, 14: 334, 15: 335,
        16: 336, 17: 337, 18: 338, 19: 339, 20: 340, 21: 341, 22: 342,
        23: 343, 24: 344, 25: 345, 26: 346, 27: 347, 28: 348, 29: 349,
        30: 350, 31: 351, 32: 352, 33: 353, 34: 354, 35: 355, 36: 465,
        101: 10063, 102: 10064, 103: 10065, 104: 10066, 105: 10067,
        106: 10068, 107: 10069, 108: 10070, 109: 921, 110: 922, 111: 923,
        112: 924, 113: 925, 114: 926, 115: 944,
    },
}

#: The block COO's condition is about, stated as a range rather than left
#: implicit in a count.  "35/35" means: every Mob-Set number in this range,
#: under CLINE type 2, resolves to itself.
AGREEING_BLOCK_SCENE_TYPE = 2
AGREEING_BLOCK = range(1, 36)

#: (placement_index, set_number) - the Bg0002 placements that fall OUTSIDE
#: ``AGREEING_BLOCK`` and are therefore not covered by the 35/35 measurement.
#: These are the rows that make "the regenerated table is identical" false.
BG0002_PLACEMENTS_OUTSIDE_THE_AGREEING_BLOCK = (
    (92, 103), (93, 103), (94, 103), (95, 103), (96, 103),
)

#: What ``CONSTDATA_TH__MOBS`` says about the two readings of Mob-Set 103,
#: so the cost of the rule change is a row a reader can check and not an
#: adjective.  (n_ID, n_RANK, n_AI_COMBAT, s_OUTFIT, n_LEVEL_MIN, name)
DISPUTED_SET_103_READINGS = {
    LEGACY_IDENTITY_RULE: (103, 1, 332, "M023_000_001_SP3", 58, "Orc Chief"),
    PROJECT_IDENTITY_RULE: (917, 0, 0, "INVISIBLE", 100, "(no MOBS_TIP name)"),
}


class IdentityRuleError(ValueError):
    """A Mob-Set number cannot be read under the rule asked for."""


def resolve(cline_type: int, set_number: int, rule: str) -> int:
    """A scene file's Mob-Set number -> the ``MOBS.n_ID`` it means.

    ``setnum`` is the identity function and cannot fail, which is exactly why
    it survived as long as it did: it always returns something.  ``cline``
    can fail, and a raise here is the honest outcome -- a Mob-Set number with
    no row in its block is a number this project cannot read, not a number
    that means itself.
    """
    if rule == LEGACY_IDENTITY_RULE:
        return set_number
    if rule != PROJECT_IDENTITY_RULE:
        raise IdentityRuleError("unknown identity rule %r" % (rule,))
    block = CLINE_BLOCKS.get(cline_type)
    if block is None:
        raise IdentityRuleError(
            "no CLINE block mined for scene type %r; this module carries "
            "only the types in play (%s), and guessing is what GT-078 cost"
            % (cline_type, ", ".join(str(key) for key in sorted(CLINE_BLOCKS)))
        )
    if set_number not in block:
        raise IdentityRuleError(
            "CLINE type %d has no row for Mob-Set number %d"
            % (cline_type, set_number)
        )
    return block[set_number]


def agreement(cline_type: int) -> tuple[int, int]:
    """(rows where the two rules agree, rows in the block).

    The number COO's condition is stated in.  Returned as a pair rather than
    a ratio so a caller cannot print "35/35" for a block that has 45 rows.
    """
    block = CLINE_BLOCKS[cline_type]
    return sum(1 for key, value in block.items() if key == value), len(block)


def divergent_set_numbers(
    cline_type: int, set_numbers: object,
) -> tuple[int, ...]:
    """Which of these Mob-Set numbers the two rules read differently.

    Unreadable numbers count as divergent: under ``setnum`` they resolve to
    themselves and under ``cline`` they resolve to nothing, which is a
    difference a caller must not miss because it took the shape of an
    exception.
    """
    block = CLINE_BLOCKS[cline_type]
    return tuple(sorted(
        {int(number) for number in set_numbers
         if block.get(int(number)) != int(number)}
    ))


def console_line(cline_type: int) -> str:
    """One ASCII line for the bridge console (cp874), grep-able by token.

    ``SCENE_IDENTITY`` is the token.  Printed with the block size beside the
    agreement count because the pair is the whole finding: 35 agreeing rows
    means nothing until you know whether the block has 35 rows or 45.
    """
    agreeing, total = agreement(cline_type)
    return (
        "SCENE_IDENTITY rule=%s cline_type=%d block=%d agree_with_setnum=%d"
        % (PROJECT_IDENTITY_RULE, cline_type, total, agreeing)
    )


SCENE_IDENTITY_NONCLAIMS = (
    "1. The 35/35 equality is a property of CLINE type 2's block 1..35, not "
    "of the crosswalk.  Type 14 agrees on 0 of 51.",
    "2. Bg0002 is NOT regenerated under cline yet.  Five shipped placements "
    "(92-96, Mob-Set 103) resolve to MOBS 917, which is INVISIBLE and rank "
    "0, so cline drops them from the map.  COO-DECISION 20260829_0345's own "
    "stop condition applies and the question is with the owner.",
    "3. This module does not say setnum is right for those five rows.  It "
    "says the two readings differ and that no sighting supports either: at "
    "M1P-RESULT-PASS the 101/102/103/104 placements were unresolved and "
    "shipped nothing.",
    "4. The blocks here are a committed copy of a table on the bridge clone, "
    "pinned by digest.  A test re-derives them where that clone exists and "
    "skips where it does not, so on a machine without it this module is "
    "trusted, not verified.",
    "5. Only the two scene types in play are carried.  resolve() raises for "
    "any other rather than falling back to the identity function.",
)
