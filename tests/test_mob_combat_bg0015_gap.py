"""LANE-B: tests/test_mob_combat_bg0015_gap.py -- pins the combat-ledger gap
``src/pirateforce_foundation/mob_combat_bg0015_gap.py`` measures.

Four load-bearing tests.

``test_todays_ledger_refuses_all_twelve_hostile_identities`` is the whole
finding: scene 14's real combat ledger, opened the same way runtime.py's own
``_sync_combat_scene_state`` already opens it, refuses every one of the 12
identities the already-sent census CORE-REQUEST is about to mark visually
hostile.

``test_a_registered_ledger_would_carry_exactly_the_spliced_identities``
proves the visual half and the combat half would agree on WHICH twelve
identities, if someone registers Bg0015.

``test_bg0002_and_bg0015_share_exactly_one_colliding_identity`` measures the
one real collision (placement 87 on both sides, actor identity 0x2058) and
pins the count so a mining update to either table's silently adding a second
collision is noticed here rather than assumed away.

``test_this_module_does_not_import_the_raw_table_module`` guards this file's
own NONCLAIM: it must never become a second importer
``tests/test_field_mob_tables_bg0015.py``'s guard would have to track.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from pirateforce_foundation import field_mob_hostile_bg0015 as hostile_bg0015
from pirateforce_foundation import field_mobs
from pirateforce_foundation import mob_combat
from pirateforce_foundation import mob_combat_bg0015_gap as gap

MODULE_PATH = SRC / "pirateforce_foundation" / "mob_combat_bg0015_gap.py"

# Same 12 numbers tests/test_field_mob_hostile_bg0015.py cross-checks against
# lane A's independently-measured letter; reproduced here only as the
# expected COUNT, not re-typed as the identity list itself.
EXPECTED_HOSTILE_COUNT = 12


class MobCombatBg0015GapTests(unittest.TestCase):
    def test_today_hostile_identities_matches_the_splice_composer(self) -> None:
        expected = {
            mob.actor_identity for mob in hostile_bg0015.scene14_hostile_roster()
        }
        self.assertEqual(set(gap.today_hostile_identities()), expected)
        self.assertEqual(len(expected), EXPECTED_HOSTILE_COUNT)

    def test_todays_ledger_refuses_all_twelve_hostile_identities(self) -> None:
        refused = gap.today_every_hostile_identity_is_refused()
        self.assertEqual(
            set(refused), set(gap.today_hostile_identities()),
            "every hostile-splice identity must be refused by today's real "
            "scene-14 ledger -- an identity NOT refused here means Bg0015 "
            "became live and this module's own premise is stale",
        )
        self.assertEqual(len(refused), EXPECTED_HOSTILE_COUNT)

        # Cross-check against the real ledger directly, not just this
        # module's own wrapper -- the wrapper must not be hiding a
        # different refusal reason or swallowing a real hit.
        ledger = mob_combat.open_ledger_for_scene_id(gap.BG0015_SCENE_ID)
        self.assertEqual(ledger.identities(), ())
        for identity in gap.today_hostile_identities():
            with self.assertRaises(mob_combat.MobCombatContractError) as ctx:
                ledger.balance_of(identity)
            self.assertEqual(
                ctx.exception.reason, mob_combat.REFUSE_TARGET_NOT_IN_LEDGER)

    def test_open_ledger_for_scene_id_vs_sync_combat_scene_state_scene_tag(
            self) -> None:
        # Pins the one real difference this module's own docstring names:
        # open_ledger_for_scene_id(14) tags its (empty) ledger scene=None
        # (field_mobs.scene_for_scene_id(14) is None, Bg0015 unregistered),
        # while runtime.py's _sync_combat_scene_state would tag the very
        # same empty roster scene="Bg0015" (world_scene_folder DOES address
        # scene id 14). Both refuse every hostile identity identically
        # (balance_of never reads .scene) -- checked here so a future reader
        # cannot mistake "same outcome" for "same object".
        from pirateforce_foundation import world_scene_folder
        folder = world_scene_folder.scene_folder_for_scene_id(
            gap.BG0015_SCENE_ID)
        self.assertEqual(folder, "Bg0015")
        self.assertIsNone(field_mobs.scene_for_scene_id(gap.BG0015_SCENE_ID))
        via_sync_shape = mob_combat.open_ledger((), scene=folder)
        via_helper = mob_combat.open_ledger_for_scene_id(gap.BG0015_SCENE_ID)
        self.assertNotEqual(via_sync_shape, via_helper)
        self.assertEqual(via_sync_shape.identities(), via_helper.identities())

    def test_a_registered_ledger_would_carry_exactly_the_spliced_identities(
            self) -> None:
        self.assertTrue(
            gap.bg0015_registration_would_line_up_with_the_visual_splice())

        # Adversarial check: prove the function is measuring something real,
        # not vacuously true. A ledger opened for the WRONG scene must not
        # accidentally satisfy the same equality.
        wrong = mob_combat.open_ledger_for_scene_id(gap.BG0002_SCENE_ID)
        self.assertNotEqual(
            set(wrong.identities()), set(gap.today_hostile_identities()))

    def test_bg0002_and_bg0015_share_exactly_one_colliding_identity(self) -> None:
        collisions = gap.bg0002_bg0015_identity_collisions()
        self.assertEqual(collisions, (0x2058,))

        # 0x2058 is placement 87 on both sides (LANE-A's measured table,
        # tests/test_field_mob_hostile_bg0015.py's LANE_A_MEASURED_IDENTITIES
        # names it too) -- confirm both rosters actually carry placement 87
        # at that identity, not merely that a set intersection is non-empty.
        bg0015_row = next(
            mob for mob in hostile_bg0015.scene14_hostile_roster()
            if mob.actor_identity == 0x2058)
        self.assertEqual(bg0015_row.placement_index, 87)
        bg0002_row = next(
            mob for mob in field_mobs.roster_for_scene_id(gap.BG0002_SCENE_ID)
            if mob.actor_identity == 0x2058)
        self.assertEqual(bg0002_row.placement_index, 87)

    def test_this_module_does_not_import_the_raw_table_module(self) -> None:
        text = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("field_mob_tables_bg0015", text)

    def test_module_touches_no_wire_no_registry(self) -> None:
        # Behavioural containment: importing/reloading this module must
        # never mutate field_mobs' own live-scene registry. Prose in this
        # module's docstring is allowed to NAME _SCENE_TABLE_MODULES/
        # runtime.py/app.py (it does, explaining why it avoids them) -- the
        # real guard is that doing so leaves no trace on the registry
        # itself, checked here rather than by forbidding the words.
        before = field_mobs.live_scenes()
        import importlib
        importlib.reload(gap)
        after = field_mobs.live_scenes()
        self.assertEqual(before, after)
        self.assertEqual(set(after), {"bg0001", "Bg0002"})


if __name__ == "__main__":
    unittest.main()
