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
from unittest import mock
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.model import Position               # noqa: E402
from pirateforce_foundation.persistence_quest_state import (    # noqa: E402
    QuestCounterRow,
)
from pirateforce_foundation import store as store_module         # noqa: E402
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
        # PAYS pf-adversary D4 (round `euskyd`): this fixture used to
        # write `counter_value = quest_id`, which makes `ORDER BY
        # quest_id`, `ORDER BY counter_value` and NO `ORDER BY` at all
        # indistinguishable -- adversary deleted the ordering from the door
        # and all 26 tests here stayed green.  The values below disagree
        # with the ids on purpose, so each of those three doors answers
        # differently.
        for quest_id, counter_value in (
            (900, 1), (12, 5), (65535, 3), (0, 9),
        ):
            self.store.set_quest_counter(
                self.character_id, quest_id, "mob:900", counter_value
            )
        rows = self.store.quest_counters_named(self.character_id, "mob:900")
        self.assertEqual(
            [row.quest_id for row in rows], [0, 12, 900, 65535]
        )
        # ... and the same rows under `ORDER BY counter_value` would be
        # `[900, 65535, 12, 0]`, which is what this assertion exists to
        # tell apart.
        self.assertEqual(
            [row.counter_value for row in rows], [9, 5, 1, 3]
        )

    def test_it_reads_the_table_rather_than_echoing_a_cached_number(self):
        """A second connection rewrites the stored number behind the door's
        back, so a door answering from anything but the table reports 5.

        NONCLAIM (pf-adversary D7, round `euskyd`): this door never
        RECEIVES a `counter_value`, so "echoes its argument" is not an
        expressible bug for it, and no SQL mutant of the door turns this
        test red.  It pins the weaker, still-worth-pinning fact that the
        answer follows the table when the table changes underneath.  It is
        also NOT a trigger, which an earlier draft of this docstring
        claimed -- it is a plain UPDATE from a connection of this test's
        own."""
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


class ItCreatesNoRowTests(_Workspace):
    """`1757`: a mob dying must not push a quest the player never accepted.

    ROW-LEVEL, and pf-adversary (D7, round `euskyd`) is right that the
    distinction matters: this door goes through `connect()` like its five
    siblings, which opens the file read-write and sets `journal_mode`, so
    asking about a database that does not exist CREATES an empty file.  No
    row is created, ever, which is the fact LANE-Q asked for; the file is
    not a fact this class measures or claims."""

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

    def _statement_the_door_runs(self):
        """The SELECT `quest_counters_named` actually executes, captured
        off the connection it opens.

        PAYS pf-adversary D3 (round `euskyd`): the plan test used to
        EXPLAIN a copy of the SQL typed into this file, so it was blind to
        every change of the DOOR -- adversary rewrote the door with `LIKE`,
        with `COLLATE NOCASE`, with the `character_id` filter deleted and
        with the ordering deleted, and this test stayed green through all
        four.  A `set_trace_callback` on the store's own connection is what
        ties the pin to the code."""
        statements = []

        def spy(*args, **kwargs):
            db = real_connect(*args, **kwargs)
            db.set_trace_callback(statements.append)
            return db

        real_connect = store_module.sqlite3.connect
        with mock.patch.object(store_module.sqlite3, "connect", spy):
            self.store.quest_counters_named(self.character_id, "mob:900")
        against_the_table = [
            statement for statement in statements
            if "character_quest_counter" in statement
        ]
        self.assertEqual(
            len(against_the_table), 1,
            "the door should touch the counter table exactly once: %r"
            % (against_the_table,),
        )
        return against_the_table[0]

    def test_the_query_plan_of_the_statement_the_door_runs_does_not_scan(
        self,
    ):
        statement = self._statement_the_door_runs()
        db = sqlite3.connect(str(self.path))
        try:
            # `set_trace_callback` hands back the statement with its
            # parameters already substituted on CPython 3.12+, and with
            # `?` placeholders before that -- bind only when there are
            # placeholders left to bind.
            arguments = (
                (self.character_id, "mob:900") if "?" in statement else ()
            )
            plan = " ".join(
                str(row[3]) for row in db.execute(
                    "EXPLAIN QUERY PLAN " + statement, arguments,
                )
            )
        finally:
            db.close()
        self.assertIn("SEARCH", plan)
        self.assertIn("character_quest_counter", plan)
        # Both spellings: SQLite before 3.36 prints `SCAN TABLE <name>`.
        self.assertNotIn("SCAN character_quest_counter", plan)
        self.assertNotIn("SCAN TABLE character_quest_counter", plan)
        # NONCLAIM: only `character_id` is a seek key on this schema --
        # `counter_name` is filtered over that character's own rows.  This
        # pins "not a table scan", not "an index seek on both columns".
        self.assertIn("character_id", plan)

    def test_the_statement_the_door_runs_orders_and_filters_as_published(
        self,
    ):
        """The letter to LANE-Q publishes three properties of this query:
        an exact `=` on the name, a filter on the character, and an order.
        Read them off the statement the door really executes."""
        statement = self._statement_the_door_runs()
        self.assertIn("character_id=", statement)
        self.assertIn("counter_name=", statement)
        self.assertIn("ORDER BY quest_id", statement)
        self.assertNotIn("LIKE", statement.upper())
        self.assertNotIn("NOCASE", statement.upper())

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

    def test_the_signature_is_the_one_the_letter_was_written_against(self):
        """NONCLAIM (pf-adversary D7, round `euskyd`): the expected names
        below are typed here, not read out of the letter -- `pf_bridge/` is
        not a tracked path in this repository, so no test here can open it.
        This pins the signature against drift; the letter agreeing with it
        was checked by hand when the letter was written."""
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
