"""LANE-B: the ground survives the session that made it.

WHAT THIS FILE IS THE EVIDENCE FOR.  KA1A's R309 (`pf_bridge/notes_to_chief/
20260904_1430`) killed a Fighting Fish soldier in scene 2, watched an Energy
Cubic Crystal land (screenshot `140947.png`), closed the client, logged back
in on a server that never restarted, and photographed an empty floor
(`141440.png`).  Nothing had taken the crystal and nothing had expired it: the
ground lived in the ended session's `mob_loot.DropLedgerCell`.

The wire/DB layer of this round is here -- the world floor, the readmission
fold, the two seams that fill and drain it, and the durable door's write half.
The client-observable layer is `GT-223` re-run, which needs the one call site
only chief may add (`mob_ground_persistence.seed_cell` at the arrival census)
and is therefore NOT claimed by this file.  What IS claimed: after a kill,
a second cell built from nothing and seeded from the world carries the same
row, with the same key, in the same scene, and a pickup takes it off both.
"""
from __future__ import annotations

import io
import contextlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_ground_persistence as ground   # noqa: E402
from pirateforce_foundation import mob_loot                           # noqa: E402
from pirateforce_foundation.store import SQLiteStore                  # noqa: E402

MIGRATIONS = ROOT / "migrations"

#: A real mined item id, so `GroundDrop`'s own known-item check passes: the
#: Energy Cubic Crystal R309 actually dropped.
CRYSTAL = 2400047


class _Clock:
    """A clock that is a list of numbers, exactly like the cell's own tests."""

    def __init__(self, start: float = 100.0) -> None:
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += float(seconds)


def a_drop(key=0x00100000, scene="bg0002", item_id=CRYSTAL, quantity=1):
    return mob_loot.GroundDrop(
        drop_key=key, item_id=item_id, quantity=quantity,
        x=10.5, y=-20.25, z=30.75,
        mob_identity=0x203D, killer_identity=0x750059, scene=scene)


class TheWorldFloorTests(unittest.TestCase):

    def setUp(self):
        self.clock = _Clock()
        self.world = ground.WorldGround(
            lifetime_seconds=120.0, clock=self.clock)

    def test_a_remembered_row_is_standing_in_its_own_scene_only(self):
        self.world.remember((a_drop(),))
        self.assertEqual(
            [row.drop_key for row in self.world.standing("bg0002")],
            [0x00100000])
        self.assertEqual(self.world.standing("bg0005"), ())

    def test_the_scene_is_matched_case_folded_like_everywhere_else(self):
        self.world.remember((a_drop(scene="Bg0002"),))
        self.assertEqual(len(self.world.standing("bg0002")), 1)

    def test_remembering_the_same_key_twice_does_not_restart_its_clock(self):
        row = a_drop()
        self.world.remember((row,))
        self.clock.advance(119.0)
        new, already, refused = self.world.remember((row,))
        self.assertEqual((new, already, refused), ((), (row,), ()))
        self.clock.advance(2.0)
        self.assertEqual(
            self.world.standing("bg0002"), (),
            "a re-announced generation must not keep a floor alive forever")

    def test_a_row_expires_on_the_same_lifetime_a_cell_gives_it(self):
        self.world.remember((a_drop(),))
        self.clock.advance(119.9)
        self.assertEqual(len(self.world.standing("bg0002")), 1)
        self.clock.advance(0.2)
        self.assertEqual(self.world.standing("bg0002"), ())

    def test_forget_removes_only_the_named_row_and_reports_whether_it_held_it(self):
        self.world.remember((a_drop(0x00100000), a_drop(0x00100001)))
        self.assertTrue(self.world.forget("bg0002", 0x00100000))
        self.assertFalse(self.world.forget("bg0002", 0x00100000))
        self.assertFalse(self.world.forget("bg0005", 0x00100001))
        self.assertEqual(
            [row.drop_key for row in self.world.standing("bg0002")],
            [0x00100001])

    def test_a_row_that_is_not_a_typed_drop_is_refused_not_stored(self):
        new, already, refused = self.world.remember(("not a drop",))
        self.assertEqual((new, already), ((), ()))
        self.assertEqual(refused, ("not a drop",))
        self.assertEqual(self.world.standing("bg0002"), ())

    def test_the_cap_retires_the_oldest_row_rather_than_losing_the_newest(self):
        world = ground.WorldGround(
            lifetime_seconds=120.0, clock=self.clock, rows_per_scene=2)
        world.remember((a_drop(0x00100000),))
        world.remember((a_drop(0x00100001),))
        world.remember((a_drop(0x00100002),))
        self.assertEqual(
            [row.drop_key for row in world.standing("bg0002")],
            [0x00100001, 0x00100002])


class TheReadmissionFoldTests(unittest.TestCase):
    """`mob_loot.admit_standing_drops` -- the ledger half."""

    def test_issued_through_is_raised_past_every_key_admitted(self):
        fresh = mob_loot.DropLedger()
        self.assertEqual(fresh.issued_through, mob_loot.DROP_KEY_BASE)
        after = mob_loot.admit_standing_drops(fresh, (a_drop(0x00100007),))
        self.assertEqual(after.issued_through, 0x00100008)

    def test_a_new_session_cannot_mint_a_key_the_world_is_already_holding(self):
        """The server-wide drop_key, in the one line that makes it true."""
        world_row = a_drop(0x00100000)
        fresh = mob_loot.DropLedger()
        self.assertEqual(
            fresh.next_key, world_row.drop_key,
            "without a readmission a second login re-mints the first key")
        after = mob_loot.admit_standing_drops(fresh, (world_row,))
        self.assertGreater(after.next_key, world_row.drop_key)

    def test_readmitting_a_key_the_ledger_holds_is_a_no_op_not_a_refusal(self):
        row = a_drop()
        once = mob_loot.admit_standing_drops(mob_loot.DropLedger(), (row,))
        twice = mob_loot.admit_standing_drops(once, (row,))
        self.assertIs(twice, once)

    def test_nothing_is_written_to_looted_by_a_readmission(self):
        after = mob_loot.admit_standing_drops(
            mob_loot.DropLedger(), (a_drop(),))
        self.assertEqual(after.looted, ())

    def test_two_scenes_in_one_readmission_are_refused_by_name(self):
        with self.assertRaises(mob_loot.MobLootContractError) as caught:
            mob_loot.admit_standing_drops(mob_loot.DropLedger(), (
                a_drop(0x00100000, scene="bg0002"),
                a_drop(0x00100001, scene="bg0005"),
            ))
        self.assertEqual(
            caught.exception.args[0], mob_loot.REFUSE_COMMIT_SPANS_TWO_SCENES)


class TheCellDoorTests(unittest.TestCase):
    """`DropLedgerCell.admit_standing_rows` -- the session half."""

    def setUp(self):
        self.clock = _Clock()

    def test_an_undeclared_cell_infers_the_scene_from_the_rows(self):
        cell = mob_loot.DropLedgerCell(clock=self.clock)
        admitted = cell.admit_standing_rows((a_drop(),))
        self.assertEqual([row.drop_key for row in admitted], [0x00100000])
        self.assertEqual(mob_loot.scene_key(cell.current_scene), "bg0002")

    def test_a_declared_cell_refuses_another_scenes_row_by_name(self):
        cell = mob_loot.DropLedgerCell(scene="bg0005", clock=self.clock)
        with self.assertRaises(mob_loot.MobLootContractError) as caught:
            cell.admit_standing_rows((a_drop(scene="bg0002"),))
        self.assertEqual(
            caught.exception.args[0], mob_loot.REFUSE_ROW_IS_ANOTHER_SCENES)
        self.assertEqual(cell.ledger.drops, ())

    def test_an_admitted_row_gets_a_full_lifetime_and_then_expires(self):
        cell = mob_loot.DropLedgerCell(
            lifetime_seconds=120.0, clock=self.clock, scene="bg0002")
        cell.admit_standing_rows((a_drop(),))
        self.assertAlmostEqual(cell.time_left(0x00100000), 120.0, places=6)
        self.clock.advance(121.0)
        self.assertEqual(cell.ledger.drops, ())

    def test_admitting_twice_admits_nothing_the_second_time(self):
        cell = mob_loot.DropLedgerCell(clock=self.clock, scene="bg0002")
        row = a_drop()
        self.assertEqual(len(cell.admit_standing_rows((row,))), 1)
        self.assertEqual(cell.admit_standing_rows((row,)), ())
        self.assertEqual(len(cell.ledger.drops), 1)

    def test_a_row_that_is_not_a_typed_drop_is_refused_before_the_lock(self):
        cell = mob_loot.DropLedgerCell(clock=self.clock, scene="bg0002")
        with self.assertRaises(mob_loot.MobLootContractError) as caught:
            cell.admit_standing_rows(("not a drop",))
        self.assertEqual(
            caught.exception.args[0], mob_loot.REFUSE_TYPE_NOT_TYPED_RECORD)


class TheSeedSeamTests(unittest.TestCase):
    """`seed_cell` -- what a relogin walks into.  NEVER RAISES."""

    def setUp(self):
        self.clock = _Clock()
        self.world = ground.WorldGround(
            lifetime_seconds=120.0, clock=self.clock)

    def test_the_second_session_carries_the_first_sessions_row(self):
        """R309, in one test: kill, log out, log in, the crystal is there."""
        first = mob_loot.DropLedgerCell(clock=self.clock, scene="bg0002")
        first.admit_standing_rows((a_drop(),))
        self.world.remember(first.ledger.drops)
        del first

        second = mob_loot.DropLedgerCell(clock=self.clock, scene="bg0002")
        self.assertEqual(second.ledger.drops, ())
        outcome = ground.seed_cell(second, "bg0002", world=self.world)
        self.assertTrue(outcome.seeded, outcome.reason)
        self.assertEqual(
            [row.drop_key for row in second.ledger.drops], [0x00100000])
        self.assertEqual(second.ledger.drops[0].item_id, CRYSTAL)

    def test_a_seed_takes_the_scene_from_the_cell_when_none_is_given(self):
        self.world.remember((a_drop(),))
        cell = mob_loot.DropLedgerCell(clock=self.clock, scene="Bg0002")
        outcome = ground.seed_cell(cell, world=self.world)
        self.assertEqual(len(outcome.admitted), 1)

    def test_a_cell_with_no_scene_and_no_argument_is_refused_by_name(self):
        self.world.remember((a_drop(),))
        cell = mob_loot.DropLedgerCell(clock=self.clock)
        outcome = ground.seed_cell(cell, world=self.world)
        self.assertEqual(outcome.reason, ground.REFUSE_CELL_HAS_NO_SCENE)
        self.assertEqual(cell.ledger.drops, ())

    def test_seeding_a_declared_cell_from_another_scene_refuses_by_name(self):
        self.world.remember((a_drop(scene="bg0002"),))
        cell = mob_loot.DropLedgerCell(clock=self.clock, scene="bg0005")
        outcome = ground.seed_cell(cell, "bg0002", world=self.world)
        self.assertEqual(
            outcome.reason, mob_loot.REFUSE_ROW_IS_ANOTHER_SCENES)
        self.assertEqual(cell.ledger.drops, ())

    def test_something_that_is_not_a_cell_is_named_never_raised(self):
        self.assertEqual(
            ground.seed_cell(object(), "bg0002", world=self.world).reason,
            ground.REFUSE_NOT_A_CELL)

    def test_an_empty_floor_seeds_nothing_and_says_so_without_a_reason(self):
        cell = mob_loot.DropLedgerCell(clock=self.clock, scene="bg0002")
        outcome = ground.seed_cell(cell, "bg0002", world=self.world)
        self.assertTrue(outcome.seeded)
        self.assertEqual((outcome.admitted, outcome.standing), ((), 0))

    def test_an_expired_row_is_never_handed_to_a_new_session(self):
        self.world.remember((a_drop(),))
        self.clock.advance(121.0)
        cell = mob_loot.DropLedgerCell(clock=self.clock, scene="bg0002")
        outcome = ground.seed_cell(cell, "bg0002", world=self.world)
        self.assertEqual((outcome.admitted, outcome.standing), ((), 0))

    def test_a_taken_row_is_not_handed_to_the_next_session(self):
        self.world.remember((a_drop(),))
        ground.forget_taken("bg0002", 0x00100000, world=self.world)
        cell = mob_loot.DropLedgerCell(clock=self.clock, scene="bg0002")
        self.assertEqual(
            ground.seed_cell(cell, "bg0002", world=self.world).admitted, ())

    def test_forget_taken_never_raises_on_a_scene_it_cannot_read(self):
        self.assertFalse(ground.forget_taken(None, 1, world=self.world))
        self.assertFalse(ground.forget_taken("bg0002", None, world=self.world))


class TheDuplicationGuardTests(unittest.TestCase):
    """One drop, two seeded cells, ONE item.  The price of a shared floor."""

    def setUp(self):
        self.clock = _Clock()
        self.world = ground.WorldGround(
            lifetime_seconds=120.0, clock=self.clock)
        self.world.remember((a_drop(),))
        self.first = mob_loot.DropLedgerCell(clock=self.clock, scene="bg0002")
        self.second = mob_loot.DropLedgerCell(clock=self.clock, scene="bg0002")
        ground.seed_cell(self.first, "bg0002", world=self.world)
        ground.seed_cell(self.second, "bg0002", world=self.world)

    def test_both_cells_really_do_hold_the_one_row(self):
        """Otherwise the guard below would be measuring nothing."""
        for cell in (self.first, self.second):
            self.assertEqual(
                [row.drop_key for row in cell.ledger.drops], [0x00100000])

    def test_the_second_session_is_refused_after_the_first_takes_it(self):
        self.first.take(0x00100000)
        ground.forget_taken("bg0002", 0x00100000, world=self.world)
        self.assertTrue(ground.another_session_already_took(
            self.second, 0x00100000, world=self.world))

    def test_the_session_that_took_it_is_not_refused_by_this_guard(self):
        """Its own cell no longer holds the row, so this stays somebody
        else's answer -- a double-click inside one session keeps the
        transaction's own ``drop_already_taken``."""
        self.first.take(0x00100000)
        ground.forget_taken("bg0002", 0x00100000, world=self.world)
        self.assertFalse(ground.another_session_already_took(
            self.first, 0x00100000, world=self.world))

    def test_an_untaken_row_is_never_refused(self):
        self.assertFalse(ground.another_session_already_took(
            self.second, 0x00100000, world=self.world))

    def test_a_row_that_only_expired_is_not_reported_as_taken(self):
        """Expiry is not a take: a guard that conflated the two would refuse
        clicks on rows nobody ever picked up."""
        self.clock.advance(121.0)
        self.assertEqual(self.world.standing("bg0002"), ())
        self.assertFalse(self.world.was_taken("bg0002", 0x00100000))

    def test_a_key_this_cell_minted_itself_is_never_refused(self):
        """The narrowness that keeps every pre-existing pickup path intact.

        The world's taken memory is process-wide, so the number 0x100000 can
        be "taken" while an unrelated cell legitimately holds its OWN row
        under that number.  Only a SEEDED copy can be a duplicate, so only a
        seeded copy is refused -- measured here rather than described, since
        the first draft of this guard turned thirty pickup tests red by
        asking the weaker question.
        """
        self.world.forget("bg0002", 0x00100000)
        mine = mob_loot.DropLedgerCell(
            ledger=mob_loot.DropLedger((a_drop(),), 1, 0x00100001),
            clock=self.clock, scene="bg0002")
        self.assertEqual(
            [row.drop_key for row in mine.ledger.drops], [0x00100000])
        self.assertEqual(mine.admitted_keys, frozenset())
        self.assertFalse(ground.another_session_already_took(
            mine, 0x00100000, world=self.world))

    def test_taking_a_seeded_row_takes_it_out_of_admitted_keys(self):
        self.assertEqual(self.first.admitted_keys, frozenset({0x00100000}))
        self.first.take(0x00100000)
        self.assertEqual(self.first.admitted_keys, frozenset())

    def test_an_expired_seeded_row_leaves_admitted_keys_too(self):
        self.clock.advance(121.0)
        self.assertEqual(self.second.ledger.drops, ())
        self.assertEqual(self.second.admitted_keys, frozenset())

    def test_the_guard_never_raises_on_junk(self):
        self.assertFalse(ground.another_session_already_took(
            object(), 0x00100000, world=self.world))
        self.assertFalse(ground.another_session_already_took(
            self.second, "not a key", world=self.world))

    def test_the_taken_memory_is_bounded_per_scene(self):
        world = ground.WorldGround(clock=_Clock())
        for offset in range(ground.TAKEN_KEY_MEMORY + 5):
            world.forget("bg0002", 0x00100000 + offset)
        self.assertFalse(world.was_taken("bg0002", 0x00100000))
        self.assertTrue(world.was_taken(
            "bg0002", 0x00100000 + ground.TAKEN_KEY_MEMORY + 4))


class TheConsoleLinesTests(unittest.TestCase):

    def setUp(self):
        self.world = ground.WorldGround(clock=_Clock())

    def test_the_remember_line_names_the_scene_the_count_and_the_keys(self):
        line = ground.describe_remembered(
            ground.remember_generation((a_drop(),), world=self.world))
        self.assertIn(ground.WORLD_REMEMBERED_TOKEN, line)
        self.assertIn("scene='bg0002'", line)
        self.assertIn("new=1", line)
        self.assertIn("0x100000", line)
        self.assertEqual(line, line.encode("ascii", "replace").decode("ascii"))

    def test_the_seed_line_of_a_refusal_carries_the_refusal_token(self):
        line = ground.describe_seeded(
            ground.seed_cell(object(), "bg0002", world=self.world))
        self.assertIn(ground.WORLD_SEED_REFUSED_TOKEN, line)
        self.assertIn(ground.REFUSE_NOT_A_CELL, line)

    def test_remember_generation_never_raises_on_junk(self):
        outcome = ground.remember_generation(7, world=self.world)
        self.assertEqual(outcome.reason, ground.REFUSE_ROW_IS_NOT_A_DROP)


class TheDurableDoorTests(unittest.TestCase):
    """The write half is live; the read half stands down BY NAME."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", MIGRATIONS)
        self.store.migrate()

    def test_a_generation_reaches_the_table_and_reads_back_unchanged(self):
        row = a_drop()
        outcome = ground.persist_generation(self.store, (row,))
        self.assertEqual(outcome.reason, "")
        self.assertEqual(len(outcome.wrote), 1)
        stored = self.store.list_ground_drops_for_scene("bg0002")
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].drop_key, row.drop_key)
        self.assertEqual(stored[0].item_id, CRYSTAL)
        self.assertEqual(stored[0].mob_identity, 0x203D)

    def test_re_announcing_a_floor_writes_no_second_row_and_never_raises(self):
        row = a_drop()
        ground.persist_generation(self.store, (row,))
        again = ground.persist_generation(self.store, (row,))
        self.assertEqual(again.wrote, ())
        self.assertEqual(len(again.already_there), 1)
        self.assertEqual(
            len(self.store.list_ground_drops_for_scene("bg0002")), 1)

    def test_a_row_the_door_refuses_is_counted_and_the_rest_still_land(self):
        class RefusingStore:
            def __init__(self, real):
                self._real = real

            def list_ground_drops_for_scene(self, scene):
                return self._real.list_ground_drops_for_scene(scene)

            def commit_ground_drop(self, **kwargs):
                if kwargs["drop_key"] == 0x00100000:
                    raise ValueError("refused on purpose")
                return self._real.commit_ground_drop(**kwargs)

        outcome = ground.persist_generation(
            RefusingStore(self.store), (a_drop(0x00100000), a_drop(0x00100001)))
        self.assertEqual(len(outcome.refused), 1)
        self.assertEqual(len(outcome.wrote), 1)
        self.assertEqual(
            len(self.store.list_ground_drops_for_scene("bg0002")), 1)

    def test_no_store_is_a_named_refusal_not_an_exception(self):
        outcome = ground.persist_generation(None, (a_drop(),))
        self.assertEqual(outcome.reason, ground.REFUSE_STORE_CANNOT_BE_ASKED)

    def test_a_store_without_the_door_is_named_too(self):
        outcome = ground.persist_generation(object(), (a_drop(),))
        self.assertEqual(outcome.reason, ground.REFUSE_WRITE_DOOR_IS_ABSENT)

    def test_the_restore_half_stands_down_until_the_taken_marker_exists(self):
        """Measured, not assumed: today's store cannot say what is STILL down.

        A restore built on `list_ground_drops_for_scene` alone would put every
        item a player has already picked up back on the floor at every boot.
        """
        self.assertFalse(ground.restore_door_is_open(self.store))
        self.assertEqual(
            ground.restore_scene_ground(self.store, "bg0002"),
            ground.REFUSE_TAKEN_DOOR_IS_ABSENT)

    def test_the_restore_half_works_the_day_the_marker_lands(self):
        """The same code, against a store that HAS the two named methods."""
        real = self.store
        ground.persist_generation(real, (a_drop(),))

        class StoreWithTheMarker:
            def __init__(self):
                self.taken = []

            def mark_ground_drop_taken(self, scene, drop_key):
                self.taken.append((scene, drop_key))

            def list_ground_drops_still_on_the_ground(self, scene):
                return tuple(
                    row for row in real.list_ground_drops_for_scene(scene)
                    if (scene, row.drop_key) not in self.taken)

        store = StoreWithTheMarker()
        world = ground.WorldGround(clock=_Clock())
        self.assertTrue(ground.restore_door_is_open(store))
        self.assertEqual(ground.restore_scene_ground(store, "bg0002", world=world), "")
        self.assertEqual(
            [row.drop_key for row in world.standing("bg0002")], [0x00100000])

        store.taken.append(("bg0002", 0x00100000))
        empty = ground.WorldGround(clock=_Clock())
        self.assertEqual(
            ground.restore_scene_ground(store, "bg0002", world=empty), "")
        self.assertEqual(empty.standing("bg0002"), ())


class TheKillSeamTests(unittest.TestCase):
    """`mob_drop_presence.sustain_a_kill` fills the world, and only reports."""

    def test_a_kill_puts_its_rows_on_the_world_floor_and_says_so(self):
        from pirateforce_foundation import mob_drop_presence

        world = ground.WorldGround(clock=_Clock())
        cell = mob_loot.DropLedgerCell(scene="bg0002")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            step = mob_drop_presence.sustain_a_kill(
                cell, None, (a_drop(),), world=world)
        self.assertIn(ground.WORLD_REMEMBERED_TOKEN, stdout.getvalue())
        self.assertEqual(
            [row.drop_key for row in world.standing("bg0002")], [0x00100000])
        # The presence step itself is untouched by the world: no legacy was
        # handed in, so it refuses exactly as it did before this round.
        self.assertFalse(step.frames)


if __name__ == "__main__":       # pragma: no cover
    unittest.main()
