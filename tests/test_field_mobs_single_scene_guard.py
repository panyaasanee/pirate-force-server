"""Guard: field_mobs.load_roster() must refuse to merge two scenes' tables.

COO-DECISION 2026-08-27T14:41+07:00 (pf_bridge/notes_to_chief), answering
CHIEF-ASK-COO 2026-08-27T14:25+07:00: WIDENING_RULINGS (mob_death.py) keys a
kill-permission purely by MOBS template_id, with no scene dimension, and
bg0001's and bg0015's committed field-mob tables already share four
template ids (31, 34, 35, 103). Rather than add a scene field to
FieldMob/WIDENING_RULINGS now (deferred past M4), COO chose the lighter
option: gate the load/merge point itself so a second scene's rows can never
silently enter one roster.

This proves three things about that gate, field_mobs.assert_single_scene_
tables: it refuses the EXACT real collision (bg0001 + bg0015), it accepts
today's single-table call unchanged, and load_roster() itself is
unaffected (still the same bg0001 roster) -- the guard is a no-op today by
design, not a behaviour change.

Importing field_mob_tables_bg0015 here does not trip
test_field_mob_tables_bg0015.py's own
test_nothing_under_src_imports_the_bg0015_module guard, which scans only
src/pirateforce_foundation/**/*.py -- this file lives under tests/.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from pirateforce_foundation import field_mob_tables, field_mobs  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0015  # noqa: E402

EXPECTED_MOB_COUNT = 13
EXPECTED_DISTINCT_TEMPLATES = 10


class SingleSceneGuardTests(unittest.TestCase):
    def test_refuses_the_real_bg0001_bg0015_collision(self) -> None:
        with self.assertRaises(field_mobs.FieldMobContractError):
            field_mobs.assert_single_scene_tables(
                (field_mob_tables, field_mob_tables_bg0015)
            )

    def test_accepts_a_single_table_unchanged(self) -> None:
        field_mobs.assert_single_scene_tables((field_mob_tables,))

    def test_refuses_an_empty_tuple(self) -> None:
        with self.assertRaises(field_mobs.FieldMobContractError):
            field_mobs.assert_single_scene_tables(())

    def test_refuses_a_module_with_no_scene_constant(self) -> None:
        class NoScene:
            pass

        with self.assertRaises(field_mobs.FieldMobContractError):
            field_mobs.assert_single_scene_tables((NoScene(),))

    def test_accepts_two_modules_that_share_one_scene(self) -> None:
        # Same SCENE string on both -- the guard blocks CROSS-scene merges,
        # not merely more than one module, since a single scene split across
        # generated chunk files is not the danger this gate exists for.
        field_mobs.assert_single_scene_tables(
            (field_mob_tables, field_mob_tables)
        )

    def test_the_check_is_by_scene_STRING_not_by_module_identity(self) -> None:
        # pf-adversary (this round): a mutant that dedupes by id(module)
        # instead of the SCENE string passes every other test in this file
        # unchanged, because test_accepts_two_modules_that_share_one_scene
        # above passes the literal SAME object twice. Two DISTINCT module
        # objects that both happen to carry SCENE == "bg0001" (e.g. a
        # reload, or the same scene split across generated chunk files)
        # must still be accepted -- if the guard compared identity, this
        # would wrongly refuse them.
        class ReloadedBg0001:
            SCENE = field_mob_tables.SCENE

        self.assertIsNot(field_mob_tables, ReloadedBg0001)
        field_mobs.assert_single_scene_tables(
            (field_mob_tables, ReloadedBg0001())
        )

    def test_load_roster_is_unaffected_by_the_new_guard(self) -> None:
        roster = field_mobs.load_roster()
        self.assertEqual(len(roster), EXPECTED_MOB_COUNT)
        self.assertEqual(
            len({mob.template_id for mob in roster}),
            EXPECTED_DISTINCT_TEMPLATES,
        )


if __name__ == "__main__":
    unittest.main()
