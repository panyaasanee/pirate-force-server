"""LANE-DB round `o5zblc`: the HP pair the client actually displays.

`NOW.md` (COO round `0445`) carries one line for this lane that is not the
equip arm: a creation ticket for A/DB, "leaving 126 restores HP; BoatHealth
must not be -1".  The owner's observation behind it
(`notes_to_chief/20260907_0123_KA1A-R322B-RESULTS-*.md`) is that the self
panel showed HP **-1/1** at sea and STILL showed HP -1 after landing.

WHAT THIS FILE PROVES (wire/DB layer only -- nothing here is on a screen):

1. The three field indices this module reasons about are DERIVED from
   `gm/attr_wire.FIELDS` by name, not typed.  A rename or a removal in that
   table (LANE-GM's zone, not ours) makes the import raise rather than let
   this module pin a stale number.
2. The alternate pair's client construction default really is the corpus
   copy in `persistence_attr_compose`, and it really prints as -1/1.
3. The refusal has teeth: a block carrying the selector row with no honest
   alternate pair is refused, and deleting either half of the guard makes a
   test here go red.
4. A block that does not carry the selector is NOT this module's business
   and passes -- the guard is narrow on purpose.
5. `live_hp_pair_report` reads a real migrated store through LANE-DB's own
   `read_typed_attributes`, writes nothing, and reports an unseeded HP as
   `None` rather than 0.
6. Nothing in the module or this file claims scene 126 is category 8, or
   names any scene that takes the alternate pair.  `SELECTOR_NOTE_R301`
   says the mapping is not decoded; a test greps for the overclaim.

WHAT THIS FILE DOES NOT PROVE.  It does not evaluate `0x430E10` -- nothing
in this repository can.  It does not claim the alternate branch is what the
owner hit; it claims only that IF that branch is taken and the server has
set nothing, the HUD shows -1/1.  It has not run against the canonical
database.
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_attr_compose as compose  # noqa: E402,E501
from pirateforce_foundation import persistence_hp_pair_selector as sel  # noqa: E402,E501
from pirateforce_foundation.gm import attr_wire  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"
SRC = ROOT / "src" / "pirateforce_foundation"
MODULE_FILE = SRC / "persistence_hp_pair_selector.py"


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


class TheIndicesComeFromTheWireTableTests(unittest.TestCase):
    def test_primary_pair_is_the_rows_named_hp_current_and_hp_max(self):
        by_name = {row[6]: row[0] for row in attr_wire.FIELDS}
        self.assertEqual(
            sel.PRIMARY_PAIR, (by_name["hp_current"], by_name["hp_max"])
        )

    def test_alternate_pair_is_the_rows_named_alt_hp(self):
        by_name = {row[6]: row[0] for row in attr_wire.FIELDS}
        self.assertEqual(
            sel.ALTERNATE_PAIR,
            (by_name["alt_hp_current"], by_name["alt_hp_max"]),
        )

    def test_selector_is_the_row_named_category_5C(self):
        by_name = {row[6]: row[0] for row in attr_wire.FIELDS}
        self.assertEqual(sel.SELECTOR_FIELD, by_name["category_5C"])

    def test_the_three_groups_are_disjoint(self):
        seen = set(sel.PRIMARY_PAIR) | set(sel.ALTERNATE_PAIR)
        self.assertEqual(len(seen), 4)
        self.assertNotIn(sel.SELECTOR_FIELD, seen)

    def test_a_missing_name_raises_rather_than_defaulting(self):
        with self.assertRaises(sel.HpPairError):
            sel._x_named("a_row_gm_never_shipped")

    def test_the_wire_table_note_still_ties_x52_to_the_selector(self):
        """Derived from the shipped note, not from memory: if LANE-GM ever
        detaches x=52 from `0x430E10(x9)`, this module's whole premise is
        stale and this test says so."""
        note = {row[0]: row[8] for row in attr_wire.FIELDS}
        self.assertIn("0x430E10", note[sel.ALTERNATE_PAIR[0]])
        self.assertIn("0x430E10", note[sel.SELECTOR_FIELD])


class TheMinusOneIsTheCorpusValueTests(unittest.TestCase):
    def test_defaults_are_the_compose_corpus_copy(self):
        self.assertEqual(
            sel.ALTERNATE_CONSTRUCTION_DEFAULTS,
            (
                compose.CLIENT_CONSTRUCTION_DEFAULTS[sel.ALTERNATE_PAIR[0]].value,
                compose.CLIENT_CONSTRUCTION_DEFAULTS[sel.ALTERNATE_PAIR[1]].value,
            ),
        )

    def test_the_current_default_prints_as_minus_one(self):
        self.assertEqual(
            sel.as_signed_u32(sel.ALTERNATE_CONSTRUCTION_DEFAULTS[0]), -1
        )

    def test_the_max_default_prints_as_one(self):
        self.assertEqual(
            sel.as_signed_u32(sel.ALTERNATE_CONSTRUCTION_DEFAULTS[1]), 1
        )

    def test_signed_conversion_is_a_conversion_not_a_clamp(self):
        self.assertEqual(sel.as_signed_u32(0), 0)
        self.assertEqual(sel.as_signed_u32(100), 100)
        self.assertEqual(sel.as_signed_u32(0x7FFFFFFF), 0x7FFFFFFF)
        self.assertEqual(sel.as_signed_u32(0x80000000), -(1 << 31))

    def test_non_u32_values_raise(self):
        for bad in (None, "100", 1.5, True, -1, 1 << 32):
            with self.subTest(bad=bad):
                with self.assertRaises(sel.HpPairError):
                    sel.as_signed_u32(bad)


class TheGapsNameEveryDishonestRowTests(unittest.TestCase):
    def test_an_empty_block_gaps_both_rows_as_absent(self):
        gaps = sel.alternate_pair_gaps({})
        self.assertEqual([g.x for g in gaps], list(sel.ALTERNATE_PAIR))
        self.assertEqual(
            {g.reason for g in gaps}, {sel.REASON_MISSING}
        )

    def test_the_construction_default_is_a_gap_not_a_value(self):
        values = {
            sel.ALTERNATE_PAIR[0]: sel.ALTERNATE_CONSTRUCTION_DEFAULTS[0],
            sel.ALTERNATE_PAIR[1]: sel.ALTERNATE_CONSTRUCTION_DEFAULTS[1],
        }
        gaps = sel.alternate_pair_gaps(values)
        self.assertEqual(
            {g.reason for g in gaps}, {sel.REASON_CONSTRUCTION_DEFAULT}
        )

    def test_a_negative_printing_value_is_a_gap(self):
        values = {
            sel.ALTERNATE_PAIR[0]: 0xFFFFFFFE,
            sel.ALTERNATE_PAIR[1]: 100,
        }
        gaps = sel.alternate_pair_gaps(values)
        self.assertEqual([g.x for g in gaps], [sel.ALTERNATE_PAIR[0]])
        self.assertEqual(gaps[0].reason, sel.REASON_NEGATIVE)

    def test_a_non_integer_is_a_gap_not_a_crash(self):
        values = {sel.ALTERNATE_PAIR[0]: "100", sel.ALTERNATE_PAIR[1]: 100}
        gaps = sel.alternate_pair_gaps(values)
        self.assertEqual([g.reason for g in gaps], [sel.REASON_NOT_AN_INT])

    def test_an_honest_pair_has_no_gaps(self):
        values = {sel.ALTERNATE_PAIR[0]: 87, sel.ALTERNATE_PAIR[1]: 100}
        self.assertEqual(sel.alternate_pair_gaps(values), ())

    def test_every_gap_carries_the_wire_table_name(self):
        for gap in sel.alternate_pair_gaps({}):
            with self.subTest(x=gap.x):
                self.assertEqual(gap.field_name, sel._field_name(gap.x))


class TheGuardHasTeethTests(unittest.TestCase):
    def test_selector_without_an_honest_pair_is_refused(self):
        with self.assertRaises(sel.HpPairError) as caught:
            sel.guard_alternate_pair({sel.SELECTOR_FIELD: 0})
        message = str(caught.exception)
        self.assertIn(f"x={sel.SELECTOR_FIELD}", message)
        self.assertIn("HP -1/1", message)

    def test_selector_with_the_construction_default_is_refused(self):
        values = {
            sel.SELECTOR_FIELD: 0,
            sel.ALTERNATE_PAIR[0]: sel.ALTERNATE_CONSTRUCTION_DEFAULTS[0],
            sel.ALTERNATE_PAIR[1]: 100,
        }
        with self.assertRaises(sel.HpPairError):
            sel.guard_alternate_pair(values)

    def test_selector_with_an_honest_pair_passes(self):
        values = {
            sel.SELECTOR_FIELD: 0,
            sel.ALTERNATE_PAIR[0]: 87,
            sel.ALTERNATE_PAIR[1]: 100,
        }
        self.assertIsNone(sel.guard_alternate_pair(values))

    def test_a_block_without_the_selector_is_not_this_guards_business(self):
        """The narrowness is the property: this module must not become a
        second, quieter permission gate over blocks that never touch x=9."""
        self.assertIsNone(
            sel.guard_alternate_pair(
                {sel.PRIMARY_PAIR[0]: 100, sel.PRIMARY_PAIR[1]: 100}
            )
        )
        self.assertIsNone(sel.guard_alternate_pair({}))


class TheModuleDoesNotDecodeCategoryEightTests(unittest.TestCase):
    """`SELECTOR_NOTE_R301`: "WHAT CATEGORY 8 IS: not decoded".  An earlier
    draft of that very note had to strike out a sentence telling a tester
    which scene to visit.  This test is that lesson, applied to this lane's
    own file."""

    _FORBIDDEN = (
        re.compile(r"scene\s*126\s*(is|=|==)", re.IGNORECASE),
        re.compile(r"126\s*(is|=|==)\s*category", re.IGNORECASE),
        re.compile(r"category\s*8\s*(is|means)\s+(the\s+)?(sea|boat|ocean|water)",
                   re.IGNORECASE),
    )

    @staticmethod
    def _affirmative_hits(text, pattern):
        """Matches that are NOT inside an explicit denial.

        The module states the forbidden claim in order to disown it ("It
        does NOT claim scene 126 is category 8"), so a raw search would
        forbid the disclaimer and permit nothing else.  A hit counts only
        when no denial word stands in the 60 characters before it."""
        denial = re.compile(r"\b(not|never|no)\b", re.IGNORECASE)
        hits = []
        for match in pattern.finditer(text):
            window = text[max(0, match.start() - 60):match.start()]
            if not denial.search(window):
                hits.append(match.group(0))
        return hits

    def test_the_module_never_maps_a_scene_to_the_category(self):
        text = MODULE_FILE.read_text(encoding="utf-8")
        for pattern in self._FORBIDDEN:
            with self.subTest(pattern=pattern.pattern):
                self.assertEqual(self._affirmative_hits(text, pattern), [])

    def test_the_detector_still_catches_an_undenied_claim(self):
        """Control: without this, the denial window could be widened until
        the detector permits everything."""
        for pattern in self._FORBIDDEN:
            with self.subTest(pattern=pattern.pattern):
                self.assertNotEqual(
                    self._affirmative_hits(
                        "scene 126 is category 8, and category 8 is the sea.",
                        pattern,
                    ),
                    [],
                )

    def test_the_module_says_the_comparison_is_on_the_result(self):
        text = MODULE_FILE.read_text(encoding="utf-8")
        self.assertIn("RESULT that is compared", text)

    def test_the_module_is_ascii_only(self):
        raw = MODULE_FILE.read_bytes()
        self.assertEqual(raw, raw.decode("ascii").encode("ascii"))


class TheLiveReportReadsARealStoreTests(unittest.TestCase):
    def _store(self, directory):
        store = SQLiteStore(str(Path(directory) / "pf.db"), MIGRATIONS)
        store.migrate()
        return store

    def _character(self, store, key):
        account_id = store.ensure_account("hp-" + key)
        character = store.create_character(
            account_id, "Hp" + key, key, "fingerprint-" + key, _build_wire,
            Position(1, 0, 0.0, 0.0, 0.0, heading=0.0),
        )
        return character.id

    def test_a_born_character_reports_its_seeded_hp(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            character_id = self._character(store, "a")
            report = sel.live_hp_pair_report(store, character_id)
            self.assertEqual(report.character_id, character_id)
            self.assertIsNotNone(report.primary_current)
            self.assertIsNotNone(report.primary_max)

    def test_the_alternate_branch_is_reported_as_unsupplied(self):
        """Not a placeholder: no `characters` column maps to x=52 or x=53,
        so there is nothing this server could read for them."""
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            character_id = self._character(store, "b")
            report = sel.live_hp_pair_report(store, character_id)
            self.assertFalse(report.alternate_pair_supplied)
            self.assertTrue(report.branch_would_lie())
            self.assertEqual(report.alternate_if_unset_current, -1)
            self.assertEqual(report.alternate_if_unset_max, 1)

    def test_neither_alternate_row_is_a_server_owned_column(self):
        for x in sel.ALTERNATE_PAIR:
            with self.subTest(x=x):
                self.assertNotIn(x, compose.SERVER_OWNED_FIELDS)

    def test_both_primary_rows_are_server_owned_columns(self):
        for x in sel.PRIMARY_PAIR:
            with self.subTest(x=x):
                self.assertIn(x, compose.SERVER_OWNED_FIELDS)

    def test_the_report_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            character_id = self._character(store, "c")
            before = store.read_typed_attributes(character_id)
            sel.live_hp_pair_report(store, character_id)
            self.assertEqual(store.read_typed_attributes(character_id), before)

    def test_a_missing_character_raises_the_store_s_own_error(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            with self.assertRaises(KeyError):
                sel.live_hp_pair_report(store, 999999)

    def test_the_console_block_is_ascii_and_names_both_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            character_id = self._character(store, "d")
            text = sel.format_report(
                sel.live_hp_pair_report(store, character_id)
            )
            text.encode("ascii")
            self.assertIn("HP_PAIR_SELECTOR_REPORT", text)
            self.assertIn(f"x={sel.PRIMARY_PAIR[0]}", text)
            self.assertIn(f"x={sel.ALTERNATE_PAIR[0]}", text)
            self.assertIn("0x430E10 is not evaluated here", text)


if __name__ == "__main__":
    unittest.main()
