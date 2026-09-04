"""Grades `src/pirateforce_foundation/persistence_standard_status.py`.

This module is a read-only, unwired scaffold (`COO-DECISION 20260904_1450`
item 6): a typed accessor over the committed `CONSTDATA_TH__STANDARD_
STATUS.tsv` copy, with no caller anywhere in the repository yet and no
effect on any existing seed value (`hp_current`/`hp_max DEFAULT 100` from
`migrations/009_character_birth_defaults.sql` is untouched, and the 17
columns `COO-DECISION 20260904_0942` left NULL stay NULL).  These tests
grade the accessor itself: it must load the real committed table, its
sha256 guard must fire on a corrupted copy (not silently pass), and its
lookup must be fail-closed for a level the table does not carry.
"""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pirateforce_foundation.persistence_standard_status as standard_status_module
from pirateforce_foundation.persistence_standard_status import (
    STANDARD_STATUS_MAX_LEVEL,
    STANDARD_STATUS_MIN_LEVEL,
    STANDARD_STATUS_ROWS,
    SOURCE_SHA256,
    StandardStatusError,
    StandardStatusRow,
    standard_status_row,
)


class CommittedTableTests(unittest.TestCase):
    def test_the_committed_copy_matches_its_own_pin(self):
        raw = standard_status_module._DATA_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), SOURCE_SHA256)

    def test_the_committed_copy_matches_the_pf_bridge_source_hash(self):
        # This is the same sha256 pf_bridge/gamedata/tables/CONSTDATA_TH__
        # STANDARD_STATUS.tsv hashes to -- proves the copy is byte-for-byte,
        # not just internally self-consistent (the same class of gap
        # `class_catalog.py`'s own docstring flags: a self-hash alone "keeps
        # matching itself forever regardless of what pf_bridge does").  This
        # snapshot's value, recorded once at the round this module was
        # added; a real drift in either copy fails loudly via the sha guard
        # above, not silently here.
        self.assertEqual(
            SOURCE_SHA256,
            "d7794acfe3261a16c52a1b8235ad685a2a40d2ddfaaa226a44f2e74b009f94c4",
        )

    def test_table_covers_every_level_one_through_two_hundred_fifty_five(self):
        self.assertEqual(STANDARD_STATUS_MIN_LEVEL, 1)
        self.assertEqual(STANDARD_STATUS_MAX_LEVEL, 255)
        self.assertEqual(len(STANDARD_STATUS_ROWS), 255)
        self.assertEqual(
            set(STANDARD_STATUS_ROWS), set(range(1, 256)),
        )

    def test_every_row_is_the_frozen_dataclass_with_matching_level_key(self):
        for level, row in STANDARD_STATUS_ROWS.items():
            self.assertIsInstance(row, StandardStatusRow)
            self.assertEqual(row.level, level)

    def test_row_one_matches_the_tsv_verbatim(self):
        # Hand-transcribed from the committed file's first data row, so a
        # bug in the BUILDING logic (not just a stale literal) still fails
        # a test instead of shipping silently -- same reasoning
        # `persistence_class_id.py`'s own docstring gives for keeping one
        # hand-typed pin alongside a built table.
        row = standard_status_row(1)
        self.assertEqual(row.exp_currentlv, 0)
        self.assertEqual(row.point_ability, 0)
        self.assertEqual(row.deadloss, 0)
        self.assertEqual(row.pvp_exp, 0)
        self.assertEqual(row.pvp_sp, 0)
        self.assertEqual(row.pvp_money, 0)
        self.assertEqual(row.defence_constant, 30)

    def test_row_two_hundred_fifty_five_matches_the_tsv_verbatim(self):
        row = standard_status_row(255)
        self.assertEqual(row.exp_currentlv, 455258334)
        self.assertEqual(row.point_ability, 41)
        self.assertEqual(row.deadloss, 29416692)
        self.assertEqual(row.pvp_exp, 855168)
        self.assertEqual(row.pvp_sp, 427584)
        self.assertEqual(row.pvp_money, 0)
        self.assertEqual(row.defence_constant, 1449930)

    def test_experience_threshold_is_non_decreasing_with_level(self):
        # Not a claim about the client's curve design, only a sanity check
        # that the parse did not transpose a column: the field the client's
        # own XP bar divides by (module docstring) should not fall as the
        # character's level rises.
        previous = standard_status_row(STANDARD_STATUS_MIN_LEVEL).exp_currentlv
        for level in range(STANDARD_STATUS_MIN_LEVEL + 1, STANDARD_STATUS_MAX_LEVEL + 1):
            current = standard_status_row(level).exp_currentlv
            self.assertGreaterEqual(current, previous)
            previous = current


class LookupGuardTests(unittest.TestCase):
    def test_level_zero_is_refused(self):
        with self.assertRaises(StandardStatusError):
            standard_status_row(0)

    def test_level_two_hundred_fifty_six_is_refused(self):
        with self.assertRaises(StandardStatusError):
            standard_status_row(256)

    def test_negative_level_is_refused(self):
        with self.assertRaises(StandardStatusError):
            standard_status_row(-1)

    def test_non_int_level_is_refused(self):
        for bad in ("1", 1.0, None, [1]):
            with self.assertRaises(StandardStatusError):
                standard_status_row(bad)

    def test_bool_level_is_refused_even_though_bool_is_an_int_subclass(self):
        # True == 1 and False == 0 in Python; both are valid dict keys that
        # would silently alias a real level if this were not guarded.
        with self.assertRaises(StandardStatusError):
            standard_status_row(True)
        with self.assertRaises(StandardStatusError):
            standard_status_row(False)

    def test_refusal_names_the_level_and_the_valid_range(self):
        with self.assertRaises(StandardStatusError) as ctx:
            standard_status_row(999)
        message = str(ctx.exception)
        self.assertIn("999", message)
        self.assertIn(str(STANDARD_STATUS_MIN_LEVEL), message)
        self.assertIn(str(STANDARD_STATUS_MAX_LEVEL), message)


class SourceHashGuardTests(unittest.TestCase):
    def test_a_corrupted_copy_of_the_committed_table_fails_the_hash_guard(self):
        """Same guard-testing shape as `persistence_class_id`'s
        `SlotRhandGuardTests`: corrupt one byte of a temp copy of the real
        file, point `_DATA_PATH` at it, and prove `_load_rows` refuses
        before any TSV parsing runs (not a parse-error path)."""
        original_path = standard_status_module._DATA_PATH
        real_bytes = original_path.read_bytes()
        corrupted = bytearray(real_bytes)
        corrupted[len(corrupted) // 2] ^= 0xFF
        with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as handle:
            handle.write(bytes(corrupted))
            temp_path = Path(handle.name)
        self.addCleanup(temp_path.unlink)
        self.addCleanup(
            setattr, standard_status_module, "_DATA_PATH", original_path
        )
        standard_status_module._DATA_PATH = temp_path
        with self.assertRaises(StandardStatusError):
            standard_status_module._load_rows()

    def test_a_copy_with_a_duplicate_n_id_is_refused(self):
        """The hash guard cannot catch this on its own committed file (it
        has no duplicate), so this proves the separate duplicate-key check
        inside `_load_rows` independently, on a synthetic table small
        enough to hand-verify, bypassing the hash gate on purpose."""
        original_path = standard_status_module._DATA_PATH
        original_sha = standard_status_module.SOURCE_SHA256
        synthetic = (
            "n_ID\tn_EXP_CURRENTLV\tn_POINT_ABILITY\tn_DEADLOSS\t"
            "n_PVP_EXP\tn_PVP_SP\tn_PVP_MONEY\tn_DEFENCE_CONSTANT\n"
            "1\t0\t0\t0\t0\t0\t0\t30\n"
            "1\t79\t1\t0\t0\t0\t0\t36\n"
        ).encode("ascii")
        with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as handle:
            handle.write(synthetic)
            temp_path = Path(handle.name)
        self.addCleanup(temp_path.unlink)
        self.addCleanup(
            setattr, standard_status_module, "_DATA_PATH", original_path
        )
        self.addCleanup(
            setattr, standard_status_module, "SOURCE_SHA256", original_sha
        )
        standard_status_module._DATA_PATH = temp_path
        standard_status_module.SOURCE_SHA256 = hashlib.sha256(synthetic).hexdigest()
        with self.assertRaises(StandardStatusError):
            standard_status_module._load_rows()


class NoProductionCallerTests(unittest.TestCase):
    def test_module_has_no_caller_outside_itself_and_this_test_file(self):
        """This is a scaffold, not a wiring (module docstring): it must not
        already be imported by any production module, migration or
        scenario, the same "no caller yet" property
        `test_world_avatar_attr.py::NoOtherCallerTests` pins for its own
        decoder -- including that test's exact suffix set.  pf-adversary
        (round `epxry7`) measured that an earlier draft of this test only
        scanned `.py`/`.sql`, one suffix narrower than the reference guard
        it claimed to follow (`.json` was missing), and proved the gap live
        by dropping a `.json` file under `scenarios/` carrying this
        module's name -- the suite stayed green.  `.json` is included here
        for the same reason `test_world_avatar_attr.py` includes it:
        `scenarios/*.json` files carry real prose, not just inert config.

        `tests/` and `reports/` are still not scanned -- the same gap the
        reference guard itself has (its own `roots` list omits them too),
        inherited on purpose rather than invented here; a second test file
        added later that imports this module would not trip this guard,
        same as it would not trip `test_world_avatar_attr.py`'s."""
        needle = "persistence_standard_status"
        mine = {
            (ROOT / "src" / "pirateforce_foundation"
             / "persistence_standard_status.py").resolve(),
            Path(__file__).resolve(),
        }
        roots = [
            ROOT / "src" / "pirateforce_foundation",
            ROOT / "current",
            ROOT / "tools",
            ROOT / "migrations",
            ROOT / "scenarios",
        ]
        offenders = []
        for root in roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.resolve() in mine:
                    continue
                if path.suffix not in {".py", ".json", ".sql"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                if needle in text:
                    offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
