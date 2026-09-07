"""LANE-DB: experience turns into a level, and the level survives a relog.

TWO LAYERS, MEASURED SEPARATELY ON PURPOSE.
`PlanTests` measure `persistence_experience.plan_experience_gain` -- pure
arithmetic against the client's committed `STANDARD_STATUS` table, no
database at all.  `GrantDoorTests` measure `store.grant_experience`: the
same rule inside one `BEGIN IMMEDIATE`, written to a real SQLite file and
read back off disk through a SECOND store object, which is the closest this
side of the seam gets to "the level is still there after a relog".

WHAT IS STILL NOT PROVEN HERE, so no reader has to infer it: nothing in
this file sends a frame, so nothing here shows that a player SEES the new
level.  That needs the attribute block composed at the next login, and a
GT on the owner's machine.  The claim measured here is the one this lane
owns: the number in `characters.level` moves, by the client's own table's
rule, and it is durable.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pf_birth_state  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.persistence_experience import (  # noqa: E402
    EXPERIENCE_COLUMN,
    ExperienceError,
    InconsistentLevelExperienceError,
    LEVEL_COLUMN,
    plan_experience_gain,
    threshold_for_next_level,
)
from pirateforce_foundation.persistence_standard_status import (  # noqa: E402
    STANDARD_STATUS_MAX_LEVEL,
    standard_status_row,
)
from pirateforce_foundation.store import (  # noqa: E402
    SQLiteStore,
    UnmeasuredTypedAttributeError,
)

MIGRATIONS = ROOT / "migrations"

_HOME = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)

_next_identity = iter(range(0x32000001, 0x32001000))


def _build_wire(selector):
    return b"wire", b"avatar", next(_next_identity), 0


class PlanTests(unittest.TestCase):
    """The rule, without a database."""

    def test_the_threshold_is_the_next_row_the_client_divides_by(self):
        """The one proven consumer of `n_EXP_CURRENTLV`: the XP bar at
        level L divides by row L+1.  The threshold must be that number and
        not the row of the level the character is standing on."""
        self.assertEqual(threshold_for_next_level(1),
                         standard_status_row(2).exp_currentlv)
        self.assertEqual(threshold_for_next_level(40),
                         standard_status_row(41).exp_currentlv)
        self.assertNotEqual(standard_status_row(1).exp_currentlv,
                            standard_status_row(2).exp_currentlv)

    def test_the_top_of_the_table_has_no_next_level(self):
        self.assertIsNone(threshold_for_next_level(STANDARD_STATUS_MAX_LEVEL))

    def test_a_level_the_table_cannot_describe_is_refused(self):
        for bad in (0, STANDARD_STATUS_MAX_LEVEL + 1, True, 1.0):
            with self.assertRaises(ExperienceError):
                threshold_for_next_level(bad)

    def test_short_of_the_line_the_level_does_not_move(self):
        need = threshold_for_next_level(1)
        plan = plan_experience_gain(1, 0, need - 1)
        self.assertEqual(plan.level_after, 1)
        self.assertEqual(plan.levels_gained, 0)
        self.assertEqual(plan.experience_after, need - 1)

    def test_reaching_the_line_exactly_raises_the_level_and_empties_the_bar(self):
        need = threshold_for_next_level(1)
        plan = plan_experience_gain(1, 0, need)
        self.assertEqual(plan.level_after, 2)
        self.assertEqual(plan.levels_gained, 1)
        self.assertEqual(plan.experience_after, 0)

    def test_the_remainder_carries_forward_rather_than_being_dropped(self):
        """The derived half of the rule, pinned so a future measurement
        that says otherwise fails here instead of disagreeing with the
        screen quietly."""
        need = threshold_for_next_level(1)
        plan = plan_experience_gain(1, 0, need + 7)
        self.assertEqual(plan.level_after, 2)
        self.assertEqual(plan.experience_after, 7)

    def test_the_numerator_stays_inside_the_bar_at_every_level_it_reaches(self):
        """The other half of the same reasoning: after any grant, what the
        client would divide (experience / row(level+1)) is below 1.0, which
        a cumulative numerator would not be."""
        plan = plan_experience_gain(1, 0, 5_000_000)
        self.assertGreater(plan.level_after, 1)
        self.assertLess(plan.level_after, STANDARD_STATUS_MAX_LEVEL)
        self.assertLess(
            plan.experience_after,
            standard_status_row(plan.level_after + 1).exp_currentlv,
        )

    def test_dropping_the_remainder_is_a_different_rule_and_the_tests_see_it(self):
        """The discriminating test for the derived half (pf-adversary
        `D3`): `test_the_numerator_stays_inside_the_bar...` is the loop's
        own exit condition restated and passes under EITHER carry rule, so
        it cannot be the pin.  This one names the number the rejected rule
        would produce (0, the remainder thrown away) and the number this
        rule produces, and asserts they are different and which one is
        ours."""
        need = threshold_for_next_level(1)
        plan = plan_experience_gain(1, 0, need + 41)
        dropped_remainder = 0
        self.assertNotEqual(plan.experience_after, dropped_remainder)
        self.assertEqual(plan.experience_after, 41)

    def test_a_pair_already_past_the_line_is_refused_not_harvested(self):
        """Somebody else's write does not become a level here (`D5`)."""
        need = threshold_for_next_level(1)
        with self.assertRaises(InconsistentLevelExperienceError) as caught:
            plan_experience_gain(1, need, 0)
        self.assertIn(str(need), str(caught.exception))
        with self.assertRaises(InconsistentLevelExperienceError):
            plan_experience_gain(1, need * 3, 10)

    def test_one_grant_can_cross_several_levels(self):
        need_2 = threshold_for_next_level(1)
        need_3 = threshold_for_next_level(2)
        plan = plan_experience_gain(1, 0, need_2 + need_3)
        self.assertEqual(plan.level_after, 3)
        self.assertEqual(plan.levels_gained, 2)
        self.assertEqual(plan.experience_after, 0)

    def test_at_the_ceiling_experience_accumulates_and_says_so(self):
        plan = plan_experience_gain(STANDARD_STATUS_MAX_LEVEL, 10, 99)
        self.assertEqual(plan.level_after, STANDARD_STATUS_MAX_LEVEL)
        self.assertEqual(plan.experience_after, 109)
        self.assertTrue(plan.at_table_ceiling)

    def test_a_huge_grant_stops_at_the_ceiling_instead_of_running_off_it(self):
        plan = plan_experience_gain(1, 0, 10 ** 15)
        self.assertEqual(plan.level_after, STANDARD_STATUS_MAX_LEVEL)
        self.assertTrue(plan.at_table_ceiling)

    def test_zero_is_a_legal_grant_and_changes_nothing(self):
        plan = plan_experience_gain(5, 3, 0)
        self.assertEqual((plan.level_after, plan.experience_after), (5, 3))
        self.assertEqual(plan.levels_gained, 0)

    def test_a_negative_amount_is_refused_rather_than_de_levelling(self):
        with self.assertRaises(ExperienceError):
            plan_experience_gain(5, 100, -1)

    def test_bools_are_not_amounts_or_experience(self):
        for bad in (True, 1.5, "10", None):
            with self.assertRaises(ExperienceError):
                plan_experience_gain(5, 0, bad)
            with self.assertRaises(ExperienceError):
                plan_experience_gain(5, bad, 10)


class _StoreFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()

    def _character_at(self, level=None, experience=None,
                      login="acct01", name="Test01"):
        account_id = self.store.ensure_account(login)
        self.store.open_session(account_id)
        character = self.store.create_character(
            account_id, name, name.casefold(), "fp-" + login,
            _build_wire, _HOME,
        )
        values = {}
        if level is not None:
            values[LEVEL_COLUMN] = level
        if experience is not None:
            values[EXPERIENCE_COLUMN] = experience
        if values:
            self.store.write_typed_attributes(character.id, values)
        return character


class GrantDoorTests(_StoreFixture):
    def test_a_quest_payout_that_crosses_the_line_raises_the_level_on_disk(self):
        character = self._character_at(level=1, experience=0)
        need = threshold_for_next_level(1)
        result = self.store.grant_experience(character.id, need + 5)
        self.assertEqual(result.level_after, 2)
        self.assertEqual(result.levels_gained, 1)
        stored = self.store.read_typed_attributes(character.id)
        self.assertEqual(stored[LEVEL_COLUMN], 2)
        self.assertEqual(stored[EXPERIENCE_COLUMN], 5)

    def test_the_new_level_is_still_there_for_a_second_store_object(self):
        """The relog half this side of the seam can measure: a fresh
        `SQLiteStore` on the same file, nothing shared in memory."""
        character = self._character_at(level=1, experience=0)
        self.store.grant_experience(character.id, threshold_for_next_level(1))
        reopened = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(
            reopened.read_typed_attributes(character.id)[LEVEL_COLUMN], 2
        )

    def test_a_payout_short_of_the_line_leaves_the_level_alone(self):
        character = self._character_at(level=1, experience=0)
        result = self.store.grant_experience(
            character.id, threshold_for_next_level(1) - 1)
        self.assertEqual(result.level_after, 1)
        self.assertEqual(result.levels_gained, 0)

    def test_the_returned_values_are_read_back_from_the_row(self):
        character = self._character_at(level=3, experience=11)
        result = self.store.grant_experience(character.id, 0)
        stored = self.store.read_typed_attributes(character.id)
        self.assertEqual(result.level_after, stored[LEVEL_COLUMN])
        self.assertEqual(result.experience_after, stored[EXPERIENCE_COLUMN])
        self.assertEqual(result.level_before, 3)
        self.assertEqual(result.experience_before, 11)

    def test_a_null_level_is_refused_by_name_not_treated_as_level_zero(self):
        """A row from before migration 009 seeded the birth defaults: the
        shared `pf_birth_state` helper is the only way this suite makes
        that state, so the test measures the row shape the canonical
        database really can hold rather than one invented here."""
        character = self._character_at(experience=0)
        pf_birth_state.clear_vitals_to_pre_seed(self.path, [character.id])
        stored = self.store.read_typed_attributes(character.id)
        self.assertNotIn(LEVEL_COLUMN, stored)
        with self.assertRaises(UnmeasuredTypedAttributeError) as caught:
            self.store.grant_experience(character.id, 100)
        self.assertIn(LEVEL_COLUMN, str(caught.exception))
        # pf-adversary `D7`: a door that named the wrong column every time
        # passed this test while the two messages shared a sentence.
        self.assertNotIn(EXPERIENCE_COLUMN, str(caught.exception))

    def test_a_null_experience_is_refused_by_name(self):
        character = self._character_at(level=1)
        with self.assertRaises(UnmeasuredTypedAttributeError) as caught:
            self.store.grant_experience(character.id, 100)
        self.assertIn(EXPERIENCE_COLUMN, str(caught.exception))
        self.assertNotIn(LEVEL_COLUMN, str(caught.exception))

    def test_a_level_outside_the_committed_table_is_refused_before_any_write(self):
        character = self._character_at(level=0, experience=0)
        with self.assertRaises(ExperienceError):
            self.store.grant_experience(character.id, 10 ** 6)
        stored = self.store.read_typed_attributes(character.id)
        self.assertEqual(stored[LEVEL_COLUMN], 0)
        self.assertEqual(stored[EXPERIENCE_COLUMN], 0)

    def test_a_negative_amount_is_refused_and_writes_nothing(self):
        character = self._character_at(level=2, experience=40)
        with self.assertRaises(ExperienceError):
            self.store.grant_experience(character.id, -1)
        stored = self.store.read_typed_attributes(character.id)
        self.assertEqual(stored[LEVEL_COLUMN], 2)
        self.assertEqual(stored[EXPERIENCE_COLUMN], 40)

    def test_a_bool_is_not_an_amount(self):
        character = self._character_at(level=1, experience=0)
        with self.assertRaises(TypeError):
            self.store.grant_experience(character.id, True)

    def test_an_unknown_character_is_a_key_error(self):
        self._character_at(level=1, experience=0)
        with self.assertRaises(KeyError):
            self.store.grant_experience(999999, 10)

    def test_a_soft_deleted_character_is_a_key_error(self):
        account_id = self.store.ensure_account("acct02")
        sid = self.store.open_session(account_id)
        character = self.store.create_character(
            account_id, "Gone01", "gone01", "fp-acct02", _build_wire, _HOME,
        )
        self.store.write_typed_attributes(
            character.id, {LEVEL_COLUMN: 1, EXPERIENCE_COLUMN: 0})
        self.store.soft_delete_character(sid, 0)
        with self.assertRaises(KeyError):
            self.store.grant_experience(character.id, 10)

    def test_a_level_forty_character_levels_from_where_it_actually_stands(self):
        """pf-adversary `D1`: every store test in the first draft granted
        at level 1, so a door that planned from `min(level, 1)` and wrote
        level 1 back over a level-40 character passed all of them.  The
        oracle here is computed from the table BEFORE the call, never read
        back out of the row the method just wrote."""
        need_41 = threshold_for_next_level(40)
        character = self._character_at(level=40, experience=need_41 - 3)
        result = self.store.grant_experience(character.id, 3)
        self.assertEqual(result.level_before, 40)
        self.assertEqual(result.level_after, 41)
        self.assertEqual(result.levels_gained, 1)
        stored = self.store.read_typed_attributes(character.id)
        self.assertEqual(stored[LEVEL_COLUMN], 41)
        self.assertEqual(stored[EXPERIENCE_COLUMN], 0)

    def test_a_high_level_character_short_of_the_line_keeps_its_level(self):
        """The same guard from the other side: no demotion, and the level
        is checked against 40, a number no other door in this test wrote."""
        character = self._character_at(level=40, experience=0)
        result = self.store.grant_experience(character.id, 5)
        self.assertEqual(result.level_after, 40)
        self.assertEqual(
            self.store.read_typed_attributes(character.id)[LEVEL_COLUMN], 40)

    def test_experience_banked_by_the_other_door_is_refused_not_harvested(self):
        """`D5` end to end: the plain add door banks three levels' worth,
        and a ZERO grant through this door refuses instead of awarding
        them.  Nothing is written by the refusal."""
        character = self._character_at(level=1, experience=0)
        self.store.add_typed_attribute(
            character.id, EXPERIENCE_COLUMN, threshold_for_next_level(1) * 3)
        with self.assertRaises(InconsistentLevelExperienceError):
            self.store.grant_experience(character.id, 0)
        stored = self.store.read_typed_attributes(character.id)
        self.assertEqual(stored[LEVEL_COLUMN], 1)
        self.assertEqual(
            stored[EXPERIENCE_COLUMN], threshold_for_next_level(1) * 3)

    def test_a_gm_set_level_is_not_re_derived_by_the_next_payout(self):
        """The same hole through the GM door (`/lv` writes `level` alone):
        a level set by hand with banked experience under it is refused, not
        recomputed into a level nobody granted."""
        character = self._character_at(level=50, experience=10 ** 9)
        with self.assertRaises(InconsistentLevelExperienceError):
            self.store.grant_experience(character.id, 1)
        self.assertEqual(
            self.store.read_typed_attributes(character.id)[LEVEL_COLUMN], 50)

    def test_at_the_table_ceiling_the_flag_comes_back_true_from_the_door(self):
        """The store layer's own ceiling test: a hardcoded `False` on this
        field passed every test in the first draft (`D9`)."""
        character = self._character_at(level=255, experience=7)
        result = self.store.grant_experience(character.id, 11)
        self.assertTrue(result.at_table_ceiling)
        self.assertEqual(result.level_after, 255)
        self.assertEqual(result.experience_after, 18)

    def test_two_payouts_in_a_row_are_both_counted(self):
        """The pair is read inside the transaction, so the second payout
        sees the first one's remainder rather than a stale balance."""
        character = self._character_at(level=1, experience=0)
        need = threshold_for_next_level(1)
        self.store.grant_experience(character.id, need - 10)
        result = self.store.grant_experience(character.id, 10)
        self.assertEqual(result.level_after, 2)
        self.assertEqual(result.experience_after, 0)


class TheOtherDoorIsUnchangedTests(_StoreFixture):
    """`add_typed_attribute` keeps the contract it shipped with: it adds
    the number and does NOT move the level.  Stated as a test because the
    doors on this column are now three (`add_typed_attribute`,
    `spend_typed_attribute`, this one) and a future round must not 'fix'
    one into another by accident.

    WHAT THIS CLASS NO LONGER SAYS.  Its first draft asserted the resulting
    state -- level 1 with three levels' worth of experience banked, a bar
    the client would draw at 300% -- and stopped there, which pinned as
    correct the exact state this module's own derivation calls impossible
    (pf-adversary `D5`).  The state is still what the old door produces;
    what changed is that this file now also measures what the NEW door does
    about it, which is refuse."""

    def test_the_plain_add_door_still_leaves_the_level_where_it_was(self):
        character = self._character_at(level=1, experience=0)
        after = self.store.add_typed_attribute(
            character.id, EXPERIENCE_COLUMN, threshold_for_next_level(1) * 3)
        stored = self.store.read_typed_attributes(character.id)
        self.assertEqual(stored[EXPERIENCE_COLUMN], after)
        self.assertEqual(stored[LEVEL_COLUMN], 1)

    def test_and_the_state_it_leaves_is_one_the_grant_door_refuses(self):
        """The other half, so the class cannot be read as blessing it."""
        character = self._character_at(level=1, experience=0)
        self.store.add_typed_attribute(
            character.id, EXPERIENCE_COLUMN, threshold_for_next_level(1) * 3)
        with self.assertRaises(InconsistentLevelExperienceError):
            self.store.grant_experience(character.id, 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
