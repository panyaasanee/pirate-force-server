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


class SoleProductionCallerTests(unittest.TestCase):
    #: The one production module allowed to name this one, written as a
    #: repository-relative posix path so the assertion below reads as the
    #: caller LIST it is, not as a count.  `COO-ORDER 20260907_2050`
    #: (`pf_bridge/notes_to_chief/20260907_2050_COO-ORDER-cs2010-retire-
    #: the-scaffold-pin-for-its-first-caller-LANE-DB.md`) names this file
    #: as the first caller and this lane as the one who must say so.
    SOLE_CALLER = "src/pirateforce_foundation/class_attacker_profile.py"

    def test_class_attacker_profile_is_the_only_production_caller(self):
        """`src/pirateforce_foundation/class_attacker_profile.py` -- and
        nothing else -- may name this module.

        WHAT REPLACED WHAT, SO THE CHANGE IS NOT MISTAKEN FOR A WEAKENING.
        Until `COO-ORDER 20260907_2050` this was
        `NoProductionCallerTests`, pinning that NOTHING imported this
        module ("this is a scaffold, not a wiring"), the same "no caller
        yet" property `test_world_avatar_attr.py::NoOtherCallerTests` pins
        for its own decoder.  LANE-CS's `class_attacker_profile.py` (round
        `hhmvit`) then asked this module the one question it exists to
        answer -- whether a character's level is a level the client's own
        progression table carries -- and the pin went red per its own
        docstring.  LANE-CS proposed allowlisting one name inside a
        LANE-DB pin; COO REFUSED that (the house rule forbids
        skip/xfail/allowlist for a pin that goes red per its own
        docstring) and ruled that the declaration "scaffold, not wiring"
        belongs to the module's owner, which is this lane.  So the pin is
        MOVED, in the ticket that made it red, to the property this
        project now wants held: not "nobody calls it" but "exactly this
        one caller calls it".

        `needle`, `roots` and the suffix set are byte-identical to the
        retired version -- pf-adversary (round `hhmvit`, D1) caught an
        earlier LANE-CS draft calling an allowlist a "narrowing", and the
        honest description of THIS edit is that the scan is unchanged and
        only the EXPECTED RESULT moved from `[]` to a one-name list.
        `class_attacker_profile.py` is deliberately NOT in `mine`: a name
        skipped by the loop is a name nobody measures, and the whole point
        of this test after the order is that the caller list is measured.

        RED ON A SECOND CALLER, which is what makes it a pin at all: any
        other file under `roots` naming this module appends to `offenders`
        and the list stops matching.  A caller that DISAPPEARS turns it
        red too -- an empty list is no longer the pass condition -- so the
        day LANE-CS drops the import (the reversal their own letter
        describes) this test says so instead of quietly going green.

        `tests/` and `reports/` are still not scanned, the same gap the
        reference guard `test_world_avatar_attr.py::NoOtherCallerTests`
        has in its own `roots` list, inherited on purpose rather than
        invented here.  `.json` IS scanned: pf-adversary (round `epxry7`)
        proved the gap live by dropping a `.json` file under `scenarios/`
        carrying this module's name while the suite stayed green.
        """
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
        self.assertEqual(offenders, [self.SOLE_CALLER])

    def test_the_sole_caller_exists_and_really_imports_this_module(self):
        """The list above is a string comparison; this is the fact behind
        it.  Without this, a rename of `class_attacker_profile.py` would
        turn the pin red for the right reason but a DELETION of its import
        while the file kept the name in a comment would keep it green.
        """
        caller = ROOT / self.SOLE_CALLER
        self.assertTrue(caller.is_file(), self.SOLE_CALLER)
        source = caller.read_text(encoding="utf-8")
        self.assertIn("persistence_standard_status", source)
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.rsplit(".", 1)[-1]
                                for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.add(node.module.rsplit(".", 1)[-1])
                imported.update(alias.name for alias in node.names)
        self.assertIn(
            "persistence_standard_status", imported,
            "the sole caller names this module but does not import it -- "
            "the caller list is prose, not a wiring",
        )

    def test_this_module_still_writes_nothing(self):
        """`COO-ORDER 20260907_2050` item 2 asks the owner to confirm, in
        the same ticket, that being READ by somebody did not give this
        module a WRITE.  Measured, not asserted in prose: no migration
        names it, and it reaches no `store` write door.
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
