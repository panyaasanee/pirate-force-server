"""LANE-B / ROUND k3qe9q: the scene a player stands in decides the roster.

WHAT THIS FILE IS DEFENDING.  ``runtime.py`` composes the combat ledger from
``field_mobs.load_roster()`` with no argument -- bg0001's four identities, in
every scene -- so almost every monster the Bg0002 census puts in front of a
player is refused with ``target_not_in_ledger``.  This file pins the reader
that lets a call site compose the ledger from the scene the session is in.

~~a player standing in Bg0002 cannot land a hit on any monster there~~
STRUCK, pf-adversary defect 1, re-derived by this lane before accepting it:
the Bg0002 census composes 97 actors with identities ``0x2001..0x206a``, and
``0x2068``/``0x206a`` are ALSO bg0001 roster rows.  Two of them are therefore
hittable today -- as Port Royal monsters, debiting a Port Royal monster's HP,
which is worse than a refusal and was not what the earlier sentence said.
The honest count is 2 of 97 hittable today and 12 of 97 after the binding, so
this reader is a step, not a fix.  See ``mob_combat_scene_ledger`` in the
round record and the letter this round opened about the collision itself.

That measurement is the reason the numbers below are stated as counts rather
than as "cannot".  Lane A landed the scene-id reader
(``world_scene_folder``, COO-DECISION 2026-08-29T08:48+07:00 item 3), so this
round ships the join, and this file pins the properties that make the join
safe for a call site to use.

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
    field_mob_tables_bg0015,
    field_mobs,
    mob_ai_control,
    mob_combat,
    mob_death,
    world_population_bg0002,
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
        # carry those two spellings verbatim.
        self.assertEqual(field_mob_tables.SCENE, "bg0001")
        self.assertEqual(field_mob_tables_bg0002.SCENE, "Bg0002")
        self.assertEqual(
            world_scene_folder.scene_folder_for_scene_id(BG0001_SCENE_ID),
            field_mob_tables.SCENE)
        self.assertEqual(
            world_scene_folder.scene_folder_for_scene_id(BG0002_SCENE_ID),
            field_mob_tables_bg0002.SCENE)
        # pf-adversary defect 8 / mutant M1: the four assertions above pin two
        # module constants and two of LANE A's lookups and NEVER CALL the
        # function whose 14-line docstring paragraph claims the exact-match
        # rule.  A case-folding implementation survived all of them.  This is
        # the half that calls it: register a live table under a spelling that
        # differs from the client's folder ONLY in case, and require that the
        # scene id resolving to that folder still refuses to find it.  An
        # implementation that case-folds returns "BG0015" here.
        table = field_mobs._SCENE_TABLE_MODULES
        self.assertNotIn("BG0015", table)
        table["BG0015"] = field_mob_tables_bg0015
        try:
            self.assertIsNone(
                field_mobs.scene_for_scene_id(BG0015_SCENE_ID_DORMANT))
            self.assertEqual(
                field_mobs.roster_for_scene_id(BG0015_SCENE_ID_DORMANT), ())
        finally:
            del table["BG0015"]

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

    def test_the_three_empty_cases_are_three_different_cases(self):
        # pf-adversary defect 10: the three constants above are commented as
        # three DIFFERENT reasons for an empty roster, and only one of them
        # had its reason asserted.  All three could have silently become the
        # same case and the file's stated distinction would have evaporated
        # green.  Addressed-ness is what separates them, so it is pinned.
        self.assertEqual(
            world_scene_folder.scene_folder_for_scene_id(
                BG1001_SCENE_ID_UNSHIPPED), "Bg1001")
        self.assertIsNone(
            world_scene_folder.scene_folder_for_scene_id(UNADDRESSED_SCENE_ID))

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
        # pf-adversary defect 6: THIS assertion, not the guard, is what would
        # notice a second scene id -- the guard is a truthiness test and one
        # id and two ids both satisfy it.  Driven here so that is a measured
        # statement and not a claim: with a second id addressing bg0001, the
        # guard still passes and scene 186 quietly serves Port Royal's
        # monsters, while the tuple above is what changes.  This also kills a
        # mutant that returned the ids unsorted (defect 8 / M12).
        registry = world_scene_folder._FOLDER_BY_SCENE_ID
        world_scene_folder._FOLDER_BY_SCENE_ID = ((186, "bg0001"),) + registry
        try:
            self.assertEqual(
                field_mobs.scene_ids_addressing("bg0001"), (1, 186))
            field_mobs.assert_live_scenes_are_addressable()
            self.assertEqual(len(field_mobs.roster_for_scene_id(186)), 4)
        finally:
            world_scene_folder._FOLDER_BY_SCENE_ID = registry
        self.assertEqual(field_mobs.scene_ids_addressing("bg0001"), (1,))

    def test_a_scene_name_that_is_not_text_is_refused_by_name(self):
        # pf-adversary defect 8 / mutant M13: the non-empty-string guard on
        # scene_ids_addressing was unpinned.
        for bad in ("", None, 1, ()):
            with self.assertRaises(FieldMobContractError):
                field_mobs.scene_ids_addressing(bad)

    def test_the_guard_runs_without_the_curated_copy_on_disk(self):
        # pf-adversary defect 5: the first version of scene_ids_addressing
        # read world_scene_folder.load_copy(), whose JSON file is NOT in the
        # release archive tools/build_foundation_release.py builds (it
        # collects *.py only).  Measured out of a built archive, the guard
        # raised SceneFolderCopyError -- another lane's RuntimeError
        # subclass, so not even catchable as FieldMobContractError -- and
        # would have taken boot down had chief asserted it at start-up as the
        # docstring invited.  This makes any return of that read fail here.
        def refuse():
            raise RuntimeError("the curated copy is not in the release archive")

        copy_reader = world_scene_folder.load_copy
        world_scene_folder.load_copy = refuse
        try:
            field_mobs.assert_live_scenes_are_addressable()
            self.assertEqual(field_mobs.scene_ids_addressing("Bg0002"), (2,))
            self.assertEqual(
                field_mobs.describe_scene_roster_binding(BG0002_SCENE_ID),
                "MOB_SCENE_ROSTER scene_id=2 folder=Bg0002 live=1 mobs=%d"
                % len(field_mobs.roster_for_scene_id(BG0002_SCENE_ID)))
        finally:
            world_scene_folder.load_copy = copy_reader

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
        # pf-adversary defect 8 / mutant M6: `live=` is the ONE field that
        # carries the addressed-vs-live distinction, and it was asserted only
        # for scene 2 (live) and for an id nothing addresses.  The case it
        # exists to describe -- ADDRESSED but NOT live -- was checked for its
        # prefix and its ASCII only, so a mutant reporting `live=1` for the
        # dormant scene survived the whole suite.  Pinned as a whole line.
        self.assertEqual(
            field_mobs.describe_scene_roster_binding(BG0015_SCENE_ID_DORMANT),
            "MOB_SCENE_ROSTER scene_id=14 folder=Bg0015 live=0 mobs=0")
        self.assertEqual(
            field_mobs.describe_scene_roster_binding(BG0001_SCENE_ID),
            "MOB_SCENE_ROSTER scene_id=1 folder=bg0001 live=1 mobs=%d"
            % len(field_mobs.load_roster()))


class Bg0002CensusAndRosterOverlapTest(unittest.TestCase):
    """What this reader is and is not worth, in counts, on the wire layer.

    pf-adversary defect 1.  The round's first draft said a player in Bg0002
    "cannot land a hit on anything there".  Re-derived here rather than
    taken on trust, and it is false in the direction that matters: the
    Bg0002 census hands out identities ``0x2001..0x206a``, ``actor_identity``
    is ``0x2000 + placement index + 1`` with no scene component, and two of
    those identities are ALSO bg0001 roster rows.  So today two bodies in
    Bg0002 are hittable -- as Port Royal monsters.

    These counts are asserted, not printed, because every one of them is a
    number a later change can move silently: a row added to either scene's
    table, or a change to the census actor count, walks straight into a
    cross-scene HP debit that nothing else in this repository would notice.
    ``field_mobs.load_roster``'s own docstring calls this hazard "not fixed,
    only unrealised" between the two ROSTERS; between a roster and the other
    scene's CENSUS it is realised today.
    """

    @classmethod
    def setUpClass(cls):
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.census = set(world_population_bg0002.build_bg0002_population(
            legacy, (0.0, 0.0, 0.0), scene_id=2).actor_identities)
        cls.today = {row.actor_identity
                     for row in mob_combat.open_ledger().balances}
        cls.bound = {row.actor_identity for row
                     in mob_combat.open_ledger_for_scene_id(2).balances}

    def test_two_bg0002_bodies_are_hittable_today_as_port_royal_monsters(self):
        self.assertEqual(len(self.census), 97)
        self.assertEqual(
            sorted(self.today & self.census), [0x2068, 0x206A])

    def test_the_binding_removes_those_two_and_adds_twelve(self):
        self.assertEqual(self.bound & self.today & self.census, set())
        self.assertEqual(len(self.bound & self.census), 12)

    def test_the_binding_leaves_most_of_the_scene_unhittable(self):
        # Not a defect of this reader -- this lane ships no roster row for
        # those 85 bodies -- but it is the number that stops "the scene is
        # fixed" from being said.
        self.assertEqual(len(self.census - self.bound), 85)

    def test_five_ledger_rows_name_bodies_the_census_never_sends(self):
        # The other direction, equally worth seeing: the roster carries five
        # placements the Bg0002 census does not put on any client.
        self.assertEqual(
            sorted(self.bound - self.census),
            [0x205D, 0x205E, 0x205F, 0x2060, 0x2061])


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
