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
import ast
import dataclasses
import hashlib
import sys
import tempfile
import unittest
import unittest.mock
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


class SoleProductionCallerTests(unittest.TestCase):
    #: The caller this pin EXPECTS to see.  It stopped being empty in
    #: LANE-DB round `6n7pam`: `persistence_experience` turns a character's
    #: experience into a LEVEL and needs exactly one thing from this table,
    #: the row for `level + 1`, whose `n_EXP_CURRENTLV` is the number the
    #: client's own XP bar divides by.  Written as a repository-relative
    #: posix path so the assertion below reads as the caller LIST it is,
    #: not as a count -- and never moved into the `mine` set, because a
    #: name the loop skips is a name nobody measures.
    EXPECTED_CALLERS: list = [
        "src/pirateforce_foundation/persistence_experience.py",
    ]

    def test_the_declared_caller_is_the_only_production_caller(self):
        """The scaffold premise RETIRES here, in the module owner's own
        round, which is the only way `COO-ORDER 20260907_2050` allows it.

        THE HISTORY, KEPT BECAUSE IT IS WHY THIS TEST LOOKS LIKE THIS.
        Round `hhmvit` (LANE-CS) made `class_attacker_profile.py` the first
        caller and kept this pin green with an allowlist entry in the
        `mine` set.  `2050` refused the allowlist: this pin is its OWNER's
        declaration that the module is a scaffold, so only LANE-DB retires
        it, in a LANE-DB ticket, with the docstring rewritten and a test
        naming the caller.  LANE-CS withdrew the import instead (main,
        round `b2cnxe`), and round `dcz2sv` -- this lane, arriving with the
        order -- found the premise true again and left it standing rather
        than pin a caller that did not exist.

        WHY IT RETIRES NOW AND NOT THEN.  Round `6n7pam` wrote the caller
        itself: `persistence_experience`, in this lane's own write zone.
        The name in `EXPECTED_CALLERS` is a module that exists in the same
        commit as this line, not one this lane is waiting for.

        WHAT DID NOT CHANGE.  Same roots, same suffixes, same
        `tests/`+`reports/` gap inherited on purpose from
        `test_world_avatar_attr.py::NoOtherCallerTests`.  A second lane
        wiring itself to this table still turns this red and still has to
        declare itself."""
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
        self.assertEqual(offenders, self.EXPECTED_CALLERS)

    def test_the_sole_caller_exists_and_really_imports_this_module(self):
        """The test round `dcz2sv` wrote and could not land, back in the
        commit that moves `EXPECTED_CALLERS` off `[]`, exactly as that
        round said it would be: an AST walk, so a caller that keeps the
        name in a comment but drops the import cannot pass for one."""
        imported = []
        for name in self.EXPECTED_CALLERS:
            path = ROOT / name
            self.assertTrue(path.is_file(), name)
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if (node.module or "").endswith(
                            "persistence_standard_status"):
                        imported.append(name)
                        break
                if isinstance(node, ast.Import):
                    if any(alias.name.endswith("persistence_standard_status")
                           for alias in node.names):
                        imported.append(name)
                        break
        self.assertEqual(imported, self.EXPECTED_CALLERS)

    def test_the_caller_reads_this_table_live(self):
        """Stronger than the import: the caller's answer MOVES when the
        table under it moves.  A caller that had copied the numbers out of
        the table would pass both tests above and fail this one."""
        from pirateforce_foundation import persistence_experience as exp

        level = 7
        untouched = exp.threshold_for_next_level(level)
        self.assertEqual(
            untouched,
            standard_status_module.standard_status_row(level + 1).exp_currentlv,
        )
        row = standard_status_module.STANDARD_STATUS_ROWS[level + 1]
        bent = dataclasses.replace(row, exp_currentlv=row.exp_currentlv + 12345)
        with unittest.mock.patch.dict(
            standard_status_module.STANDARD_STATUS_ROWS,
            {level + 1: bent},
        ):
            self.assertEqual(
                exp.threshold_for_next_level(level), untouched + 12345
            )
        self.assertEqual(exp.threshold_for_next_level(level), untouched)

    def test_this_module_still_writes_nothing(self):
        """`COO-ORDER 20260907_2050` item 2: being READ by somebody did not
        give this module a WRITE.  Measured, not asserted in prose: no
        migration names it, and it reaches no `store` write door.
        """
        module = (ROOT / "src" / "pirateforce_foundation"
                  / "persistence_standard_status.py")
        source = module.read_text(encoding="utf-8")
        for forbidden in ("import store", "from .store", "from pirateforce_foundation.store",
                          "INSERT ", "UPDATE ", "DELETE "):
            self.assertNotIn(forbidden, source, forbidden)
        migrations = ROOT / "migrations"
        naming = [
            path.name for path in sorted(migrations.glob("*.sql"))
            if "persistence_standard_status" in path.read_text(
                encoding="utf-8", errors="replace")
        ]
        self.assertEqual(naming, [])




if __name__ == "__main__":
    unittest.main()
