"""Grades `src/pirateforce_foundation/persistence_class_id.py`.

`resolve_class_id` must return a class id ONLY when the chest/leggings/
right-hand triple exactly matches one row of the gear preset table built
from `CONSTDATA_TH__CHARCREATE_CLASS.tsv` (via LANE-CS's `class_catalog.py`
plus this module's own read of the one column that accessor does not carry
-- `n_SLOT_RHAND`), and `None` on anything else -- never a guess, per
`COO-DECISION 20260901_1059`.

`CLASS_PRESETS` carries 15 rows: 5 playable classes x 3 character-creation
"looks" (`COO-DECISION 20260904_0551` items D4/D5) -- the table's chest/
leggings column-triple #1, `_2` and `_3`.  There is no per-look right-hand
column, so all three of a class's rows share one `n_SLOT_RHAND`.

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
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pirateforce_foundation.persistence_class_id as persistence_class_id_module
from pirateforce_foundation import class_catalog
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
        # A `pf-adversary` pass (chief 20260904_0535, D4) found the module's
        # first cut held its own hand-transcribed copy of these numbers, so
        # this pin's JOB did not change when that copy became a build
        # (`_build_class_presets`) instead of a literal -- a bug in the
        # BUILDING logic (wrong column read, looks paired with the wrong
        # class, a look silently dropped) still needs something typed out a
        # second time, independently, to catch it.  Typed by hand straight
        # from `CONSTDATA_TH__CHARCREATE_CLASS.tsv` (columns n_ID /
        # n_DRESS_CHEST[_2/_3] / n_DRESS_LEGGINGS[_2/_3] / n_SLOT_RHAND),
        # look #1/_2/_3 in that order per class, rather than read off
        # `CLASS_PRESETS` or `class_catalog` -- so the two have to agree
        # independently, not by construction.  Cannot check against a live
        # copy of the TSV itself (this repo's own gate rehearses without
        # `pf_bridge` sitting alongside it, and this file's `data/` copy
        # is what's actually pinned) -- but a future change to the BUILD
        # that is not ALSO made here now fails a test instead of shipping
        # silently.
        expected = (
            (1, 2300026, 2300027, 2200002),   # Gladiator, look 1
            (1, 2300032, 2300033, 2200002),   # Gladiator, look 2
            (1, 2300122, 2300123, 2200002),   # Gladiator, look 3
            (2, 2300038, 2300039, 2200003),   # Paladin, look 1
            (2, 2300044, 2300045, 2200003),   # Paladin, look 2
            (2, 2300116, 2300117, 2200003),   # Paladin, look 3
            (4, 2300002, 2300003, 2200006),   # Sniper, look 1
            (4, 2300011, 2300012, 2200006),   # Sniper, look 2
            (4, 2300098, 2300099, 2200006),   # Sniper, look 3
            (16, 2300083, 2300084, 2200005),  # Necromancer, look 1
            (16, 2300071, 2300072, 2200005),  # Necromancer, look 2
            (16, 2300110, 2300111, 2200005),  # Necromancer, look 3
            (32, 2300014, 2300015, 2200008),  # Sorcerer, look 1
            (32, 2300023, 2300024, 2200008),  # Sorcerer, look 2
            (32, 2300065, 2300066, 2200008),  # Sorcerer, look 3
        )
        self.assertEqual(CLASS_PRESETS, expected)

    def test_exactly_fifteen_rows_three_per_class(self):
        # A `pf-adversary` pass against the 5-row version appended a sixth
        # row with a duplicate `class_id` and every existing test stayed
        # green, because none of them pinned the row count itself.  Pin both
        # the total and the per-class count so a dropped or duplicated look
        # fails here.
        self.assertEqual(len(CLASS_PRESETS), 15)
        ids = [row[0] for row in CLASS_PRESETS]
        self.assertEqual(
            {cid: ids.count(cid) for cid in set(ids)},
            {1: 3, 2: 3, 4: 3, 16: 3, 32: 3},
        )

    def test_five_playable_classes_covered(self):
        self.assertEqual({row[0] for row in CLASS_PRESETS}, {1, 2, 4, 16, 32})

    def test_all_fifteen_presets_are_pairwise_distinct_on_the_matched_slots(self):
        # This is what makes the matching strategy sound across three looks:
        # an exact (chest, leggings, rhand) triple must identify exactly one
        # of the 15 rows, not just one of the 5 classes on look #1.  If any
        # two of the 15 rows -- even two looks of the SAME class -- ever
        # shared a triple, `resolve_class_id` could not tell them apart, but
        # since every row within a class already carries that class's own
        # `class_id`, a same-class collision would not actually break
        # anything; a CROSS-class collision would.  Checked directly below.
        triples = [(row[1], row[2], row[3]) for row in CLASS_PRESETS]
        self.assertEqual(len(triples), len(set(triples)))

    def test_no_cross_class_triple_collision(self):
        seen: dict[tuple[int, int, int], int] = {}
        for class_id, chest, leggings, rhand in CLASS_PRESETS:
            triple = (chest, leggings, rhand)
            if triple in seen:
                self.assertEqual(
                    seen[triple], class_id,
                    "triple %r shared between class %r and class %r"
                    % (triple, seen[triple], class_id),
                )
            seen[triple] = class_id

    def test_rhand_is_constant_within_a_class_across_all_three_looks(self):
        # The table has no n_SLOT_RHAND_2/_3 column -- the weapon slot does
        # not vary by look.  If a future copy of the table added one and
        # this module's build logic silently kept reading the un-suffixed
        # column for all three looks, this is the test that would notice a
        # class whose looks now disagree on rhand (nothing here would fail
        # loudly otherwise, since resolve_class_id would still work as long
        # as callers only ever see ONE look's decoded rhand per character).
        by_class: dict[int, set[int]] = {}
        for class_id, _chest, _leggings, rhand in CLASS_PRESETS:
            by_class.setdefault(class_id, set()).add(rhand)
        for class_id, rhands in by_class.items():
            with self.subTest(class_id=class_id):
                self.assertEqual(len(rhands), 1)


class ExactMatchTests(unittest.TestCase):
    def test_every_sourced_preset_resolves_to_its_own_class_id_from_raw_ints(self):
        for class_id, chest, leggings, rhand in CLASS_PRESETS:
            with self.subTest(class_id=class_id, chest=chest, leggings=leggings):
                self.assertEqual(
                    resolve_class_id(chest, leggings, rhand), class_id
                )

    def test_every_sourced_preset_resolves_correctly_through_the_real_wire_codec(self):
        for class_id, chest, leggings, rhand in CLASS_PRESETS:
            with self.subTest(class_id=class_id, chest=chest, leggings=leggings):
                triple = _triple_from_wire(chest, leggings, rhand)
                self.assertEqual(resolve_class_id(*triple), class_id)

    def test_all_three_looks_of_the_same_class_resolve_to_that_class(self):
        # The concrete behavior D5 asked for: a character created with look
        # #2 or #3 must no longer resolve to None just because the matcher
        # only knew look #1.
        by_class: dict[int, list[tuple[int, int, int]]] = {}
        for class_id, chest, leggings, rhand in CLASS_PRESETS:
            by_class.setdefault(class_id, []).append((chest, leggings, rhand))
        for class_id, triples in by_class.items():
            with self.subTest(class_id=class_id):
                self.assertEqual(len(triples), 3)
                for triple in triples:
                    self.assertEqual(resolve_class_id(*triple), class_id)


class NeverGuessesTests(unittest.TestCase):
    def test_a_triple_matching_no_row_returns_none(self):
        self.assertIsNone(resolve_class_id(999999, 999999, 999999))

    def test_a_triple_mixing_two_different_classes_returns_none(self):
        # Gladiator look 1's chest with Paladin look 1's leggings and rhand:
        # no row of the table has this triple, so the answer must be
        # "unknown", not the nearer-looking neighbour.
        self.assertIsNone(resolve_class_id(2300026, 2300039, 2200003))

    def test_a_triple_mixing_two_looks_of_the_same_class_returns_none(self):
        # Gladiator look 1's chest with Gladiator look 2's leggings: still
        # not a real row (each look is chest+leggings from the SAME
        # column-triple), so still None, not a lucky same-class guess.
        self.assertIsNone(resolve_class_id(2300026, 2300033, 2200002))

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
            (2300122, 2300123, 2200002),
            (None, 5, 5),
        ]
        for triple in probes:
            result = resolve_class_id(*triple)
            if result is not None:
                self.assertIn(result, sourced_ids)


class AmbiguityGuardTests(unittest.TestCase):
    """`pf-adversary` (round `ub1j2l`) found that mutating the guard from
    "exactly one match" (``len(matches) != 1``) to "first match wins"
    (``if not matches: return None`` / ``return matches[0]``) left the whole
    suite green -- because the REAL 15-row table has zero cross-class
    collisions (`test_no_cross_class_triple_collision` above), nothing in
    this file ever drove a triple through the multi-match branch itself.
    These tests monkeypatch the module's ``CLASS_PRESETS`` with a synthetic
    table that DOES collide, independent of what the real committed table
    contains, restoring it afterward, so the guard is exercised directly
    rather than trusted by absence of a real-world collision."""

    def _patch_presets(self, synthetic):
        original = persistence_class_id_module.CLASS_PRESETS
        persistence_class_id_module.CLASS_PRESETS = synthetic
        self.addCleanup(
            setattr, persistence_class_id_module, "CLASS_PRESETS", original
        )

    def test_a_triple_shared_by_two_synthetic_classes_returns_none(self):
        colliding_triple = (111, 222, 333)
        self._patch_presets((
            (1, *colliding_triple),
            (2, *colliding_triple),
            (4, 444, 555, 666),
        ))
        self.assertIsNone(resolve_class_id(*colliding_triple))
        # an unambiguous row on the same synthetic table still resolves --
        # proves the guard rejects only the ambiguous case, not everything.
        self.assertEqual(resolve_class_id(444, 555, 666), 4)

    def test_two_looks_of_the_same_class_sharing_a_triple_still_resolves(self):
        # A same-class collision (two rows, same class_id) must NOT be
        # treated as ambiguous -- resolve_class_id dedupes by class_id
        # (`matches` is a set of ids, not of rows) before checking count.
        repeated_triple = (111, 222, 333)
        self._patch_presets((
            (1, *repeated_triple),
            (1, *repeated_triple),
        ))
        self.assertEqual(resolve_class_id(*repeated_triple), 1)


class SlotRhandGuardTests(unittest.TestCase):
    def test_a_corrupted_copy_of_the_committed_table_fails_the_hash_guard(self):
        """`pf-adversary` (round `ub1j2l`) found that deleting the sha256
        check inside `_slot_rhand_by_class_id` left the whole suite green,
        because nothing ever pointed the function at bytes that disagree
        with `class_catalog.SOURCE_SHA256` -- the real committed file always
        matches its own pin.  This actually corrupts a temp copy (a single
        flipped byte, anywhere in the file -- the hash check runs BEFORE any
        TSV parsing, so this must fail on the hash, not on a parse error) and
        proves the guard fires."""
        original_path = persistence_class_id_module._DATA_PATH
        real_bytes = original_path.read_bytes()
        corrupted = bytearray(real_bytes)
        corrupted[len(corrupted) // 2] ^= 0xFF
        with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as handle:
            handle.write(bytes(corrupted))
            temp_path = Path(handle.name)
        self.addCleanup(temp_path.unlink)
        self.addCleanup(
            setattr, persistence_class_id_module, "_DATA_PATH", original_path
        )
        persistence_class_id_module._DATA_PATH = temp_path
        with self.assertRaises(class_catalog.ClassCatalogError):
            persistence_class_id_module._slot_rhand_by_class_id()

    def test_the_committed_copy_matches_class_catalogs_own_pin(self):
        # The non-corrupted counterpart: proves this module's guard checks
        # against class_catalog.SOURCE_SHA256 specifically (not some other,
        # independently-chosen constant that could silently drift from it).
        import hashlib

        raw = persistence_class_id_module._DATA_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), class_catalog.SOURCE_SHA256)
        # and the guarded function itself succeeds on the real file
        rhand = persistence_class_id_module._slot_rhand_by_class_id()
        self.assertEqual(rhand[1], 2200002)  # Gladiator


if __name__ == "__main__":
    unittest.main()
