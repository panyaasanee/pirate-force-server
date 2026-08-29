"""LANE-B / ROUND k3qe9q: the scene a player stands in decides the roster.

WHAT THIS FILE IS DEFENDING.  Round ``j0u64p`` measured that a player standing
in Bg0002 cannot land a hit on any monster there: ``runtime.py`` composes the
combat ledger from ``field_mobs.load_roster()`` with no argument, which is
bg0001's rows always, so ``mob_combat.strike`` refuses every Bg0002 monster
with ``target_not_in_ledger`` before the death half is asked anything at all.
That round could name only one owner for the two lines it needed, because
nothing turned a scene id into a scene name.  Lane A landed that reader
(``world_scene_folder``, COO-DECISION 2026-08-29T08:48+07:00 item 3), so this
round ships the join, and this file pins the four properties that make the
join safe to wire from one call site line.

1. ``test_the_two_live_scenes_bind_to_their_own_tables`` -- the mapping is
   right, and it is checked through each returned row's own ``scene`` tag
   rather than by trusting the lookup that produced it.

2. ``test_a_scene_with_no_shipped_roster_opens_an_empty_ledger`` and
   ``test_an_empty_ledger_refuses_every_strike_by_name`` -- together these are
   the fail-closed half.  ``()`` must never be read as "use the default
   roster", because that reading IS today's defect.

3. ``test_scene_1_is_bit_identical_to_what_runtime_opens_today`` -- the
   wiring line chief is being asked for must be provably a no-op for the scene
   the server actually runs in today.  Without this the ask is "change the
   live scene's behaviour and trust us".

4. ``test_the_addressability_guard_fails_when_a_live_scene_is_unreachable``
   -- the guard is a join between two lanes' tables, and a join fails
   SILENTLY in the direction that matters: a live roster nothing addresses
   returns ``()`` everywhere and nothing raises.  A guard nobody has watched
   fail is not a guard, so this test breaks the join on purpose and requires
   the refusal.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    field_mob_tables,
    field_mob_tables_bg0002,
    field_mobs,
    mob_ai_control,
    mob_combat,
    mob_death,
    world_scene_folder,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.field_mobs import FieldMobContractError  # noqa: E402
from pirateforce_foundation.mob_combat import MobCombatContractError  # noqa: E402


BG0001_SCENE_ID = 1
BG0002_SCENE_ID = 2
# Addressed by lane A's registry, mined by this lane, and deliberately NOT
# live: field_mob_tables_bg0015 is in _KNOWN_SCENE_TABLE_MODULES_FOR_REPORTING
# and not in _SCENE_TABLE_MODULES.  Making it live is an act someone has to
# perform on purpose; until then this scene ships no monsters.
BG0015_SCENE_ID_DORMANT = 14
# Addressed by lane A, no roster mined at all.
BG1001_SCENE_ID_UNSHIPPED = 17
# Not addressed by lane A's registry: the reader answers None for it.
UNADDRESSED_SCENE_ID = 999


class SceneBindingTest(unittest.TestCase):

    def test_the_two_live_scenes_bind_to_their_own_tables(self):
        self.assertEqual(
            field_mobs.scene_for_scene_id(BG0001_SCENE_ID),
            field_mob_tables.SCENE)
        self.assertEqual(
            field_mobs.scene_for_scene_id(BG0002_SCENE_ID),
            field_mob_tables_bg0002.SCENE)
        # Checked through the rows themselves, not through the lookup that
        # chose them: every FieldMob carries the table module's own SCENE
        # string, so a binding that silently loaded the wrong table would
        # show up here even though the lookup "succeeded".
        for scene_id, expected in (
            (BG0001_SCENE_ID, field_mob_tables.SCENE),
            (BG0002_SCENE_ID, field_mob_tables_bg0002.SCENE),
        ):
            roster = field_mobs.roster_for_scene_id(scene_id)
            self.assertTrue(roster, "scene %d shipped no rows" % scene_id)
            self.assertEqual({mob.scene for mob in roster}, {expected})
            self.assertEqual(roster, field_mobs.load_roster(expected))

    def test_the_spelling_is_matched_exactly_not_case_folded(self):
        # The client's own folder names are inconsistently cased -- scene 1 is
        # 'bg0001' and scene 2 is 'Bg0002' -- and this project's table modules
        # carry those two spellings verbatim.  Pinned here so that a future
        # table module whose SCENE string drifts in case fails this file
        # instead of being absorbed by a case-folding match.
        self.assertEqual(field_mob_tables.SCENE, "bg0001")
        self.assertEqual(field_mob_tables_bg0002.SCENE, "Bg0002")
        self.assertEqual(
            world_scene_folder.scene_folder_for_scene_id(BG0001_SCENE_ID),
            field_mob_tables.SCENE)
        self.assertEqual(
            world_scene_folder.scene_folder_for_scene_id(BG0002_SCENE_ID),
            field_mob_tables_bg0002.SCENE)

    def test_a_scene_with_no_shipped_roster_opens_an_empty_ledger(self):
        for scene_id in (
            BG0015_SCENE_ID_DORMANT,
            BG1001_SCENE_ID_UNSHIPPED,
            UNADDRESSED_SCENE_ID,
        ):
            self.assertIsNone(field_mobs.scene_for_scene_id(scene_id))
            self.assertEqual(field_mobs.roster_for_scene_id(scene_id), ())
            ledger = mob_combat.open_ledger_for_scene_id(scene_id)
            self.assertEqual(ledger.balances, ())

    def test_the_dormant_scene_is_addressed_and_still_ships_nothing(self):
        # The distinction this pins: lane A DOES address scene 14, and this
        # lane HAS mined that scene's table.  The empty answer above is not an
        # accident of a missing address -- it is _SCENE_TABLE_MODULES saying
        # the scene is not live yet.
        self.assertEqual(
            world_scene_folder.scene_folder_for_scene_id(
                BG0015_SCENE_ID_DORMANT), "Bg0015")
        self.assertNotIn("Bg0015", field_mobs.live_scenes())

    def test_an_empty_ledger_refuses_every_strike_by_name(self):
        empty = mob_combat.open_ledger_for_scene_id(BG1001_SCENE_ID_UNSHIPPED)
        mob = field_mobs.roster_for_scene_id(BG0002_SCENE_ID)[0]
        with self.assertRaises(MobCombatContractError) as caught:
            mob_combat.apply_hit(empty, 0x750059, mob.actor_identity, 10)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_TARGET_NOT_IN_LEDGER)

    def test_scene_1_is_bit_identical_to_what_runtime_opens_today(self):
        # The whole safety case for the one-line wiring ask: for the scene the
        # server runs in today, the new call composes exactly what the old one
        # composed.  Compared as values, both directions, so a ledger that
        # merely had the same length would not pass.
        self.assertEqual(
            mob_combat.open_ledger_for_scene_id(BG0001_SCENE_ID),
            mob_combat.open_ledger())
        self.assertEqual(
            field_mobs.roster_for_scene_id(BG0001_SCENE_ID),
            field_mobs.load_roster())

    def test_every_row_a_live_scene_ships_is_in_that_scenes_ledger(self):
        # GT-132's real precondition, stated as an invariant rather than as
        # one sampled monster: a player standing in that scene can address
        # every monster the scene ships, and none from any other scene.
        for scene_id in (BG0001_SCENE_ID, BG0002_SCENE_ID):
            roster = field_mobs.roster_for_scene_id(scene_id)
            ledger = mob_combat.open_ledger_for_scene_id(scene_id)
            in_ledger = {row.actor_identity for row in ledger.balances}
            self.assertEqual(in_ledger, {mob.actor_identity for mob in roster})
            for mob in roster:
                self.assertEqual(
                    ledger.balance_of(mob.actor_identity).max_hp, mob.max_hp)

    def test_a_scene_id_that_is_not_an_integer_is_refused_by_name(self):
        for bad in ("2", 2.0, None, True, False):
            with self.assertRaises(FieldMobContractError):
                field_mobs.scene_for_scene_id(bad)

    def test_each_live_scene_is_addressed_by_exactly_one_scene_id(self):
        # Measured, not assumed: neither live folder is in lane A's
        # scene_ids_sharing_a_folder list, so neither has a second scene id
        # that would also have to be wired.  The day one of them does, this
        # test is where it is noticed.
        self.assertEqual(field_mobs.scene_ids_addressing("bg0001"), (1,))
        self.assertEqual(field_mobs.scene_ids_addressing("Bg0002"), (2,))
        field_mobs.assert_live_scenes_are_addressable()

    def test_the_addressability_guard_fails_when_a_live_scene_is_unreachable(
            self):
        # A guard nobody has watched fail is not a guard.  Register a live
        # scene no scene id can name and require the refusal.
        table = field_mobs._SCENE_TABLE_MODULES
        self.assertNotIn("Zz9999", table)
        table["Zz9999"] = field_mob_tables
        try:
            with self.assertRaises(FieldMobContractError) as caught:
                field_mobs.assert_live_scenes_are_addressable()
            self.assertIn("Zz9999", str(caught.exception))
        finally:
            del table["Zz9999"]
        # And the guard is green again once the break is undone, so a later
        # test in this process is not running against a poisoned table.
        field_mobs.assert_live_scenes_are_addressable()

    def test_the_console_line_stays_inside_cp874(self):
        for scene_id in (
            BG0001_SCENE_ID,
            BG0002_SCENE_ID,
            BG0015_SCENE_ID_DORMANT,
            UNADDRESSED_SCENE_ID,
        ):
            line = field_mobs.describe_scene_roster_binding(scene_id)
            self.assertEqual(line, line.encode("ascii").decode("ascii"))
            self.assertTrue(line.startswith("MOB_SCENE_ROSTER scene_id="))
        self.assertEqual(
            field_mobs.describe_scene_roster_binding(BG0002_SCENE_ID),
            "MOB_SCENE_ROSTER scene_id=2 folder=Bg0002 live=1 mobs=%d"
            % len(field_mobs.roster_for_scene_id(BG0002_SCENE_ID)))
        # An id nothing addresses still prints a line, and says so.
        self.assertIn(
            "folder=? live=0 mobs=0",
            field_mobs.describe_scene_roster_binding(UNADDRESSED_SCENE_ID))


class EmptyRosterReachesEveryCallSiteTest(unittest.TestCase):
    """The four ``runtime.py`` sites that read a roster, measured with ``()``.

    This is here because of what the wiring ask actually is.  ``runtime.py``
    reads a roster in FOUR places -- the ledger (1119), the AI register
    (1174), the combat dispatch (3911) and the death-frame census override
    (6486) -- and the request to chief is "change all four together or none
    of them", because a half-wired set makes the census and the ledger
    disagree in any scene that is not scene 1, which is the shape GT-084
    measured as a world wipe.  A reviewer weighing that ask needs to know
    that the empty roster a town produces does not RAISE anywhere
    downstream, so these are measured rather than asserted in a letter.
    """

    def test_the_ai_register_opens_empty_rather_than_refusing(self):
        register = mob_ai_control.open_register((), epoch=0)
        self.assertEqual(register.rows, ())

    def test_the_death_census_override_is_falsy_so_the_census_stands(self):
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        override = mob_death.full_roster_override(
            legacy, (), mob_death.DeathRegister(),
            ledger=mob_combat.open_ledger(()))
        # Falsy, so runtime.py's `if mob_death_override:` skips the override
        # and world_population's own census stands -- which is exactly what
        # happens today in a scene with no monsters.
        self.assertFalse(override)
        populated = mob_death.full_roster_override(
            legacy, field_mobs.roster_for_scene_id(BG0002_SCENE_ID),
            mob_death.DeathRegister(),
            ledger=mob_combat.open_ledger_for_scene_id(BG0002_SCENE_ID))
        self.assertEqual(
            len(populated),
            len(field_mobs.roster_for_scene_id(BG0002_SCENE_ID)))


if __name__ == "__main__":
    unittest.main()
