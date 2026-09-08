"""LANE-DB: `quest_counters_named` -- the (character, counter name) ->
quest_id direction the five doors of `2212` could not answer.

WHY THIS DOOR EXISTS.  `pf_bridge/notes_to_chief/20260908_1757_LANE-Q-TO-
LANE-DB-one-more-door-which-quests-does-this-character-count-mobs-for.md`
measured the gap and asked for exactly this shape: a mob dying arrives from
LANE-B carrying a TEMPLATE id, so the host knows the counter's name and not
the quest it belongs to, while every existing counter door needs the full
three-part key.  The letter's two honest workarounds are a 65,536-statement
scan per dead mob and a guess from `QUESTDATA_*` that cannot say whether
this character ever ACCEPTED the quest.

WHAT THIS FILE PINS.  That the answer is exact (no `LIKE`, no prefix), that
it creates nothing, that it refuses what its five siblings refuse, and that
it reads through the table's PRIMARY KEY rather than scanning it.

WHAT IT DOES NOT CLAIM.  Nothing calls this door yet: LANE-Q's adapter has
no dispatcher and `runtime.py` is not this lane's zone, so no player's
kill has ever moved a counter.  Wire/DB layer only.
"""
from __future__ import annotations

import inspect
import sqlite3
import sys
import tempfile
import unittest
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.model import Position               # noqa: E402
from pirateforce_foundation.persistence_quest_state import (    # noqa: E402
    QuestCounterRow,
)
from pirateforce_foundation.store import SQLiteStore            # noqa: E402

MIGRATIONS = ROOT / "migrations"


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


class _Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "quest_counters_named.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.home = Position(1, 0, 0.0, 0.0, 0.0, heading=0.0)
        self.account_id = self.store.ensure_account("counters-named-tests")
        self.character_id = self._make_character("a")

    def _make_character(self, tag):
        return self.store.create_character(
            self.account_id, f"CN{tag}", f"cn{tag}",
            f"fingerprint-cn-{tag}", _build_wire, self.home,
        ).id

    def _raw_count(self):
        """Rows in the table as a connection of this test's own sees them,
        never through the accessor under test."""
        db = sqlite3.connect(str(self.path))
        try:
            return db.execute(
                "SELECT COUNT(*) FROM character_quest_counter"
            ).fetchone()[0]
        finally:
            db.close()


class TheAnswerTests(_Workspace):
    """What LANE-Q asked for: from (character, counter name) to quest ids."""

    def test_two_quests_counting_the_same_mob_come_back_together(self):
        """The whole point of the letter: one dead mob, two accepted quests
        that both count it."""
        self.store.set_quest_counter(self.character_id, 11, "mob:900", 3)
        self.store.set_quest_counter(self.character_id, 22, "mob:900", 7)
        rows = self.store.quest_counters_named(self.character_id, "mob:900")
        self.assertEqual([row.quest_id for row in rows], [11, 22])
        self.assertEqual([row.counter_value for row in rows], [3, 7])

    def test_the_rows_are_quest_counter_rows(self):
        self.store.set_quest_counter(self.character_id, 11, "mob:900", 3)
        rows = self.store.quest_counters_named(self.character_id, "mob:900")
        self.assertEqual(len(rows), 1)
        self.assertIsInstance(rows[0], QuestCounterRow)
        self.assertEqual(rows[0].character_id, self.character_id)
        self.assertEqual(rows[0].counter_name, "mob:900")

    def test_the_result_is_a_tuple_not_a_list(self):
        """A frozen answer: the caller iterates it in a Lua host and must
        not be able to hand a mutated copy back to the next reader."""
        self.assertIsInstance(
            self.store.quest_counters_named(self.character_id, "mob:900"),
            tuple,
        )

    def test_a_name_nothing_wrote_is_an_empty_tuple_not_an_error(self):
        self.assertEqual(
            self.store.quest_counters_named(self.character_id, "mob:404"), ()
        )

    def test_the_order_is_by_quest_id_whatever_order_they_were_written_in(
        self,
    ):
        for quest_id in (900, 12, 65535, 0):
            self.store.set_quest_counter(
                self.character_id, quest_id, "mob:900", quest_id
            )
        rows = self.store.quest_counters_named(self.character_id, "mob:900")
        self.assertEqual(
            [row.quest_id for row in rows], [0, 12, 900, 65535]
        )

    def test_it_reads_the_table_rather_than_echoing_the_last_write(self):
        """A trigger rewrites the stored number behind the door's back, so
        a door that answered from its own memory would report 5."""
        self.store.set_quest_counter(self.character_id, 11, "mob:900", 5)
        db = sqlite3.connect(str(self.path))
        try:
            db.execute(
                "UPDATE character_quest_counter SET counter_value=4242 "
                "WHERE character_id=? AND quest_id=?", (self.character_id, 11)
            )
            db.commit()
        finally:
            db.close()
        rows = self.store.quest_counters_named(self.character_id, "mob:900")
        self.assertEqual(rows[0].counter_value, 4242)

    def test_an_increment_is_visible_through_this_door_too(self):
        self.store.increment_quest_counter(self.character_id, 11, "mob:900")
        self.store.increment_quest_counter(self.character_id, 11, "mob:900")
        rows = self.store.quest_counters_named(self.character_id, "mob:900")
        self.assertEqual([row.counter_value for row in rows], [2])

    def test_it_survives_a_reopen(self):
        """A second `SQLiteStore` over the same file -- the relog shape."""
        self.store.set_quest_counter(self.character_id, 11, "mob:900", 3)
        reopened = SQLiteStore(self.path, MIGRATIONS)
        rows = reopened.quest_counters_named(self.character_id, "mob:900")
        self.assertEqual([row.quest_id for row in rows], [11])


class TheMatchIsExactTests(_Workspace):
    """`counter_name` is caller-chosen text, so a widened match is a wrong
    answer, not a convenience."""

    def setUp(self):
        super().setUp()
        for quest_id, name in (
            (11, "mob:900"), (12, "mob:9000"), (13, "mob:90"),
            (14, "MOB:900"), (15, "mob:900 "),
        ):
            self.store.set_quest_counter(self.character_id, quest_id, name, 1)

    def test_a_longer_name_with_the_same_prefix_is_not_returned(self):
        rows = self.store.quest_counters_named(self.character_id, "mob:900")
        self.assertEqual([row.quest_id for row in rows], [11])

    def test_case_is_not_folded(self):
        rows = self.store.quest_counters_named(self.character_id, "MOB:900")
        self.assertEqual([row.quest_id for row in rows], [14])

    def test_trailing_space_is_a_different_counter(self):
        rows = self.store.quest_counters_named(self.character_id, "mob:900 ")
        self.assertEqual([row.quest_id for row in rows], [15])

    def test_like_metacharacters_in_the_name_do_not_widen_the_answer(self):
        """`_` and `%` are LIKE's wildcards.  A door written with LIKE
        would answer `mob:900`, `mob:9000` and `mob:90` here; `=` answers
        with the one row that carries this exact text -- none."""
        for pattern in ("mob:9_0", "mob:90%", "%", "_"):
            with self.subTest(pattern=pattern):
                self.assertEqual(
                    self.store.quest_counters_named(
                        self.character_id, pattern
                    ),
                    (),
                )


class ItCreatesNothingTests(_Workspace):
    """`1757`: a mob dying must not push a quest the player never accepted."""

    def test_asking_for_an_unknown_name_writes_no_row(self):
        before = self._raw_count()
        self.store.quest_counters_named(self.character_id, "mob:404")
        self.assertEqual(self._raw_count(), before)

    def test_asking_twice_leaves_the_stored_numbers_untouched(self):
        self.store.set_quest_counter(self.character_id, 11, "mob:900", 3)
        self.store.quest_counters_named(self.character_id, "mob:900")
        self.store.quest_counters_named(self.character_id, "mob:900")
        db = sqlite3.connect(str(self.path))
        try:
            self.assertEqual(
                db.execute(
                    "SELECT counter_value FROM character_quest_counter"
                ).fetchall(), [(3,)]
            )
        finally:
            db.close()


class ItRefusesWhatItsSiblingsRefuseTests(_Workspace):
    """One family of refusals across six doors, so LANE-Q's adapter -- which
    catches `KeyError` / `ValueError` / `sqlite3.Error` and nothing else --
    never meets a stranger."""

    def test_a_character_that_does_not_exist_is_a_key_error(self):
        with self.assertRaises(KeyError):
            self.store.quest_counters_named(4242, "mob:900")

    def test_a_soft_deleted_character_is_a_key_error(self):
        db = sqlite3.connect(str(self.path))
        try:
            db.execute(
                "UPDATE characters SET deleted_at=? WHERE id=?",
                ("2026-09-08T00:00:00+00:00", self.character_id),
            )
            db.commit()
        finally:
            db.close()
        with self.assertRaises(KeyError):
            self.store.quest_counters_named(self.character_id, "mob:900")

    def test_a_non_string_name_is_a_type_error(self):
        for name in (900, None, b"mob:900"):
            with self.subTest(name=name):
                with self.assertRaises(TypeError):
                    self.store.quest_counters_named(self.character_id, name)

    def test_a_name_outside_one_to_128_characters_is_a_value_error(self):
        for name in ("", "x" * 129):
            with self.subTest(length=len(name)):
                with self.assertRaises(ValueError):
                    self.store.quest_counters_named(self.character_id, name)

    def test_a_name_of_exactly_128_characters_is_allowed(self):
        self.assertEqual(
            self.store.quest_counters_named(self.character_id, "x" * 128), ()
        )

    def test_a_bool_character_id_is_a_type_error(self):
        """`sqlite3` binds `True` as `1` without complaining, which would
        answer for character 1 -- the same trap `_quest_key` names."""
        with self.assertRaises(TypeError):
            self.store.quest_counters_named(True, "mob:900")

    def test_a_character_id_sqlite_cannot_hold_is_a_value_error(self):
        """pf-adversary D6 (round `6vv9mi`): an unbounded id reached
        `sqlite3` and raised `OverflowError`, outside the family LANE-Q's
        adapter catches."""
        with self.assertRaises(ValueError):
            self.store.quest_counters_named(2 ** 70, "mob:900")


class ItReadsThroughThePrimaryKeyTests(_Workspace):
    """`1757` asked whether this shape is expensive for the index this lane
    has.  It is not -- and the plan is pinned rather than asserted in
    prose, so a later schema change that turns it into a scan goes red."""

    def test_the_query_plan_searches_and_does_not_scan(self):
        db = sqlite3.connect(str(self.path))
        try:
            plan = " ".join(
                str(row[3]) for row in db.execute(
                    "EXPLAIN QUERY PLAN SELECT character_id,quest_id,"
                    "counter_name,counter_value,updated_at "
                    "FROM character_quest_counter "
                    "WHERE character_id=? AND counter_name=? "
                    "ORDER BY quest_id", (self.character_id, "mob:900"),
                )
            )
        finally:
            db.close()
        self.assertIn("SEARCH", plan)
        self.assertNotIn("SCAN character_quest_counter", plan)
        self.assertIn("character_quest_counter", plan)

    def test_another_characters_rows_are_not_returned(self):
        other = self._make_character("b")
        self.store.set_quest_counter(other, 11, "mob:900", 99)
        self.store.set_quest_counter(self.character_id, 11, "mob:900", 3)
        rows = self.store.quest_counters_named(self.character_id, "mob:900")
        self.assertEqual([row.character_id for row in rows],
                         [self.character_id])
        self.assertEqual([row.counter_value for row in rows], [3])


class TheContractLANEQCopiesTests(_Workspace):
    """`1757`'s second question, answered by the code rather than by prose:
    what is the numeric field on `QuestCounterRow` called?"""

    def test_the_row_field_names_are_the_ones_the_adapter_copies(self):
        self.assertEqual(
            [field.name for field in fields(QuestCounterRow)],
            ["character_id", "quest_id", "counter_name", "counter_value",
             "updated_at"],
        )

    def test_the_signature_is_the_one_the_reply_letter_publishes(self):
        signature = inspect.signature(SQLiteStore.quest_counters_named)
        self.assertEqual(
            list(signature.parameters), ["self", "character_id",
                                         "counter_name"],
        )

    def test_the_five_older_doors_keep_their_signatures(self):
        """A sixth door may not move the five `2212` published -- LANE-Q's
        adapter is written against those names today."""
        expected = {
            "set_quest_flag": ["self", "character_id", "quest_id",
                               "flag_value"],
            "get_quest_flag": ["self", "character_id", "quest_id"],
            "set_quest_counter": ["self", "character_id", "quest_id",
                                  "counter_name", "counter_value"],
            "increment_quest_counter": ["self", "character_id", "quest_id",
                                        "counter_name", "delta"],
            "get_quest_counter": ["self", "character_id", "quest_id",
                                  "counter_name"],
        }
        for name, parameters in expected.items():
            with self.subTest(door=name):
                signature = inspect.signature(getattr(SQLiteStore, name))
                self.assertEqual(list(signature.parameters), parameters)


if __name__ == "__main__":       # pragma: no cover - parity with the file's
    unittest.main()              # neighbours in tests/
