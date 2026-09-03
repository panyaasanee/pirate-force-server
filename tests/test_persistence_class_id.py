"""Grades `src/pirateforce_foundation/persistence_class_id.py`.

`resolve_class_id` must return a class id ONLY when the chest/leggings/
right-hand triple exactly matches one row of the gear preset table
transcribed from `CONSTDATA_TH__CHARCREATE_CLASS.tsv`, and `None` on
anything else -- never a guess, per `COO-DECISION 20260901_1059`.

The module under test deliberately takes three already-decoded integers
rather than a raw `avatar_wire` blob (see its own docstring: it does not
import `world_avatar_attr`, which `tests/test_world_avatar_attr.py` pins as
having no production caller yet).  This test file is free to use
`world_avatar_attr.build_body`/`decode_avatar_attr` itself -- that guard
only scans `src/pirateforce_foundation`, `current`, `tools`, `migrations`
and `scenarios`, not `tests` -- to prove the two proven building blocks
(the real wire codec, and this module's matcher) compose correctly end to
end, without this module importing the codec itself.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.persistence_class_id import (
    CLASS_PRESETS,
    resolve_class_id,
)
from pirateforce_foundation.world_avatar_attr import build_body, decode_avatar_attr

# Bit positions the corpus assigns these three fields (world_avatar_attr.FIELDS).
BIT_CHEST = 5
BIT_LEGGINGS = 6
BIT_RHAND = 10


def _triple_from_wire(chest: int, leggings: int, rhand: int) -> tuple:
    """Round-trip through the REAL, proven codec: encode a synthetic body
    carrying these three slots, decode it back, and hand the matcher exactly
    what a real caller would have after decoding a real avatar_wire -- this
    is what proves the two modules compose, without persistence_class_id.py
    itself ever importing world_avatar_attr."""
    body = build_body(
        (BIT_CHEST, BIT_LEGGINGS, BIT_RHAND),
        {BIT_CHEST: chest, BIT_LEGGINGS: leggings, BIT_RHAND: rhand},
    )
    decoded = decode_avatar_attr(body)
    return (
        decoded.raw("n_DRESS_CHEST"),
        decoded.raw("n_DRESS_LEGGINGS"),
        decoded.raw("n_SLOT_RHAND"),
    )


class TableShapeTests(unittest.TestCase):
    def test_transcription_matches_an_independently_typed_pin(self):
        # A `pf-adversary` pass found that every other test in this file
        # derives its expected input AND expected output from
        # `CLASS_PRESETS` itself, so none of them could ever catch a
        # transcription error in the module under test -- a copy-paste that
        # swapped two rows, or swapped the leggings/rhand columns within one
        # row, passed the whole suite unchanged.  This pin is typed out a
        # second time, by hand, straight from `CONSTDATA_TH__CHARCREATE_
        # CLASS.tsv` (columns n_ID / n_DRESS_CHEST / n_DRESS_LEGGINGS /
        # n_SLOT_RHAND) rather than read off `CLASS_PRESETS` -- so the two
        # have to agree independently, not by construction.  It cannot check
        # the module against a live copy of that TSV (the file lives in the
        # `pf_bridge` repo, and this repo's own gate rehearses without
        # `pf_bridge` sitting alongside it), but a future edit to
        # `CLASS_PRESETS` that is not ALSO made here now fails a test
        # instead of shipping silently.
        expected = (
            (1, 2300026, 2300027, 2200002),   # Icon_Class_Gladiator
            (2, 2300038, 2300039, 2200003),   # Icon_Class_Paladin
            (4, 2300002, 2300003, 2200006),   # Icon_Class_Sniper
            (16, 2300083, 2300084, 2200005),  # Icon_Class_Necromancer
            (32, 2300014, 2300015, 2200008),  # Icon_Class_Sorcerer
        )
        self.assertEqual(CLASS_PRESETS, expected)

    def test_exactly_five_rows_no_duplicate_class_id(self):
        # A `pf-adversary` pass appended a sixth row with a duplicate
        # `class_id` (a copy-paste that misattributed a row) and every
        # existing test stayed green, because none of them pinned the row
        # count or checked `class_id` itself for duplicates -- only the
        # three gear columns were checked pairwise-distinct.
        self.assertEqual(len(CLASS_PRESETS), 5)
        ids = [row[0] for row in CLASS_PRESETS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_five_rows_one_per_playable_class(self):
        self.assertEqual(
            {row[0] for row in CLASS_PRESETS}, {1, 2, 4, 16, 32}
        )

    def test_all_five_presets_are_pairwise_distinct_on_every_slot(self):
        # If a future copy of the source TSV ever gave two classes the same
        # chest, leggings or right-hand id, this module's whole matching
        # strategy (an exact triple identifies one class) would stop being
        # sound -- this is the test that would catch that, not an assumption
        # baked silently into the matcher.
        chests = [row[1] for row in CLASS_PRESETS]
        leggings = [row[2] for row in CLASS_PRESETS]
        rhands = [row[3] for row in CLASS_PRESETS]
        self.assertEqual(len(chests), len(set(chests)))
        self.assertEqual(len(leggings), len(set(leggings)))
        self.assertEqual(len(rhands), len(set(rhands)))


class ExactMatchTests(unittest.TestCase):
    def test_every_sourced_preset_resolves_to_its_own_class_id_from_raw_ints(self):
        for class_id, chest, leggings, rhand in CLASS_PRESETS:
            with self.subTest(class_id=class_id):
                self.assertEqual(
                    resolve_class_id(chest, leggings, rhand), class_id
                )

    def test_every_sourced_preset_resolves_correctly_through_the_real_wire_codec(self):
        for class_id, chest, leggings, rhand in CLASS_PRESETS:
            with self.subTest(class_id=class_id):
                triple = _triple_from_wire(chest, leggings, rhand)
                self.assertEqual(resolve_class_id(*triple), class_id)


class NeverGuessesTests(unittest.TestCase):
    def test_a_triple_matching_no_row_returns_none(self):
        self.assertIsNone(resolve_class_id(999999, 999999, 999999))

    def test_a_triple_mixing_two_different_classes_returns_none(self):
        # Gladiator's chest with Paladin's leggings and rhand: no row of the
        # table has this triple, so the answer must be "unknown", not the
        # nearer-looking neighbour.
        self.assertIsNone(resolve_class_id(2300026, 2300039, 2200003))

    def test_missing_chest_returns_none(self):
        self.assertIsNone(resolve_class_id(None, 2300027, 2200002))

    def test_missing_leggings_returns_none(self):
        self.assertIsNone(resolve_class_id(2300026, None, 2200002))

    def test_missing_rhand_returns_none(self):
        self.assertIsNone(resolve_class_id(2300026, 2300027, None))

    def test_all_three_missing_returns_none(self):
        self.assertIsNone(resolve_class_id(None, None, None))

    def test_no_returned_value_is_ever_absent_from_the_sourced_table(self):
        # A defensive property test: whatever this function returns for any
        # input in this sweep, that number must appear as a class_id in
        # CLASS_PRESETS -- it can never invent a class id.
        sourced_ids = {row[0] for row in CLASS_PRESETS}
        probes = [
            (1, 1, 1),
            (2300026, 2300027, 2200002),
            (2300002, 2300003, 2200006),
            (None, 5, 5),
        ]
        for triple in probes:
            result = resolve_class_id(*triple)
            if result is not None:
                self.assertIn(result, sourced_ids)


if __name__ == "__main__":
    unittest.main()
