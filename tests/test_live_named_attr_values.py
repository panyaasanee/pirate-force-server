"""The live named-attr read point: what it answers, and what it refuses to
invent.

COO-DECISION 20260904_0047 item 1 / 20260904_0145 item 3.  Two lanes stand
still without this point (LANE-GM's `RawBlockCache` seeding, LANE-B's Door B
hit frame), and both of them are safe today only because a MISSING row costs
a refused send rather than a zeroed field on the client (`RE-222` Q0 full
object copy; `GT-218` is the owner watching the price of getting it wrong).

So the tests that matter here are the ones that go RED when a row starts
being invented, not the ones that prove a happy path.
"""
from __future__ import annotations

import ast
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import live_named_attr_values as live  # noqa: E402
from pirateforce_foundation import (  # noqa: E402
    persistence_typed_attrs as typed_attrs,
)
from pirateforce_foundation.gm import attr_wire  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"


class _Character:
    def __init__(self, name):
        self.name = name


class _StubStore:
    """Only the two read-only methods the source uses, nothing else.

    IT HONOURS ``character_id``, and that is the repair of pf-adversary
    defect D2 (round ``dwvbpm``): the first draft of this stub returned the
    same dict and the same name whatever id it was handed, so two mutants --
    a source hard-wired to `values_for(store, 1)` and a name read for
    character 1 -- both left the whole suite green.  A stub that ignores the
    key under test cannot test threading of the key.  Per-id rows are given
    as ``{character_id: {...}}``; a single ``columns=``/``name=`` is sugar
    for "character 7 only", so an unknown id reads as a missing character.
    """

    def __init__(self, columns=None, name="Blackbeard", raises=None,
                 rows=None):
        self._rows = (
            {int(cid): dict(row) for cid, row in rows.items()}
            if rows is not None
            else {7: {"columns": dict(columns or {}), "name": name}}
        )
        self._raises = raises

    def read_typed_attributes(self, character_id):
        if self._raises is not None:
            raise self._raises
        if character_id not in self._rows:
            raise KeyError(character_id)
        return dict(self._rows[character_id].get("columns") or {})

    def get_character(self, character_id):
        if self._raises is not None:
            raise self._raises
        if character_id not in self._rows:
            raise KeyError(character_id)
        name = self._rows[character_id].get("name")
        if name is None:
            raise KeyError(character_id)
        return _Character(name)


def _every_typed_column_populated() -> dict:
    """A store row with EVERY typed column carrying a legal value.

    Derived from `persistence_typed_attrs.TYPED_COLUMNS` rather than typed
    out, so a column added tomorrow is covered here without an edit -- the
    same reason the module under test reads through the column map.
    """
    values = {}
    for spec in typed_attrs.TYPED_COLUMNS.values():
        values[spec.column] = 1.0 if spec.sql_type == "REAL" else 1
    return values


class WhatTheSourceCanAnswerTests(unittest.TestCase):
    def test_the_three_seeded_columns_and_the_name_come_back(self):
        store = _StubStore(
            columns={"level": 3, "hp_current": 40, "hp_max": 250},
            name="Anne",
        )
        values = live.values_for(store, 7)
        self.assertEqual(values[2], 3)
        self.assertEqual(values[3], 40)
        self.assertEqual(values[4], 250)
        self.assertEqual(values[1], "Anne")

    def test_a_null_column_is_absent_never_zero(self):
        # THE HEART OF IT.  `read_typed_attributes` omits a NULL column; this
        # must arrive at the consumer as a MISSING key, because a key present
        # with 0 would set a mask bit and zero that field on the client.
        store = _StubStore(columns={"level": 1, "hp_current": 100, "hp_max": 100})
        values = live.values_for(store, 7)
        cash_x = attr_wire.BY_NAME["cash"][0]
        self.assertNotIn(cash_x, values)
        self.assertNotIn(attr_wire.BY_NAME["mp_current"][0], values)
        self.assertNotIn(attr_wire.BY_NAME["str"][0], values)
        for value in values.values():
            self.assertNotEqual(value, 0)

    def test_the_speed_column_is_never_reported_because_x7_is_not_named(self):
        # `speed_walk` IS a typed column, and x=7 is `known=False` in
        # attr_wire.FIELDS -- a row whose meaning nobody has confirmed.  It
        # must not ride in on the column map.
        store = _StubStore(columns={"speed_walk": 400.0, "level": 1})
        values = live.values_for(store, 7)
        self.assertNotIn(7, values)
        self.assertEqual(values[2], 1)

    def test_only_the_five_unreachable_rows_are_missing_when_every_column_is_set(self):
        # Pins ROWS_WITH_NO_COLUMN_AT_ALL against the real column map: if a
        # future migration addresses one of the five, this goes red and the
        # constant (and the module docstring behind it) get updated instead
        # of quietly disagreeing with the schema.
        store = _StubStore(columns=_every_typed_column_populated(), name="Anne")
        values = live.values_for(store, 7)
        missing = sorted(set(live.named_rows_wanted()) - set(values))
        self.assertEqual(missing, sorted(live.ROWS_WITH_NO_COLUMN_AT_ALL))

    def test_an_unknown_character_is_an_empty_answer_not_a_raise(self):
        store = _StubStore(raises=KeyError(7))
        self.assertEqual(live.values_for(store, 7), {})

    def test_a_broken_store_is_an_empty_answer_not_a_raise(self):
        # A driver error must not unwind into the listener thread: START_GAME
        # catches only KeyError/PermissionError/ValueError/RuntimeError.
        store = _StubStore(raises=OSError("disk"))
        self.assertEqual(live.values_for(store, 7), {})

    def test_an_empty_name_is_absent_rather_than_sent(self):
        # An empty string is a VALUE the client would apply -- a character
        # whose label goes blank.  Absent is the only honest answer.
        store = _StubStore(columns={"level": 1}, name="")
        self.assertNotIn(1, live.values_for(store, 7))

    def test_a_non_string_name_is_absent(self):
        store = _StubStore(columns={"level": 1}, name=b"Anne")
        self.assertNotIn(1, live.values_for(store, 7))

    def test_every_key_returned_is_a_named_row(self):
        store = _StubStore(columns=_every_typed_column_populated(), name="Anne")
        values = live.values_for(store, 7)
        self.assertTrue(set(values) <= set(live.named_rows_wanted()))
        # x=30 is SENSITIVE_FIELDS and must never be reachable from here.
        self.assertNotIn(30, values)


class TheReadPointOnTheRealPackageTests(unittest.TestCase):
    """`lane_hooks.current_named_attr_values` itself."""

    def setUp(self):
        self.addCleanup(
            lane_hooks.register_live_attr_values_source,
            lane_hooks._LIVE_ATTR_VALUES_SOURCE,
        )

    def test_the_read_point_exists_under_the_name_attr_wire_resolves(self):
        # Replaces `test_gm_attr_wire.py`'s
        # `..._still_has_no_read_point`, which that lane wrote with the
        # instruction "when chief lands it: delete this test".  The claim it
        # pinned is now the opposite one, pinned here.
        self.assertTrue(
            hasattr(lane_hooks, attr_wire.LIVE_VALUE_READ_POINT)
        )
        self.assertTrue(
            callable(getattr(lane_hooks, attr_wire.LIVE_VALUE_READ_POINT))
        )

    def test_with_no_source_installed_it_answers_nothing_and_does_not_raise(self):
        lane_hooks.register_live_attr_values_source(None)
        self.assertEqual(lane_hooks.current_named_attr_values(7), {})

    def test_a_source_that_raises_is_swallowed_named_on_stderr_and_answers_nothing(self):
        def boom(character_id):
            raise RuntimeError("no")

        lane_hooks.register_live_attr_values_source(boom)
        captured, sys.stderr = sys.stderr, io.StringIO()
        try:
            answer = lane_hooks.current_named_attr_values(7)
            said = sys.stderr.getvalue()
        finally:
            sys.stderr = captured
        self.assertEqual(answer, {})
        self.assertIn("LANE_HOOK", said)
        self.assertIn("current_named_attr_values", said)

    def test_a_source_returning_a_non_dict_answers_nothing(self):
        lane_hooks.register_live_attr_values_source(lambda cid: [1, 2, 3])
        captured, sys.stderr = sys.stderr, io.StringIO()
        try:
            answer = lane_hooks.current_named_attr_values(7)
            said = sys.stderr.getvalue()
        finally:
            sys.stderr = captured
        self.assertEqual(answer, {})
        self.assertIn("not dict", said)

    def test_string_keys_are_coerced_and_unusable_keys_dropped(self):
        lane_hooks.register_live_attr_values_source(
            lambda cid: {"2": 5, 3: 40, "not-an-int": 1}
        )
        self.assertEqual(lane_hooks.current_named_attr_values(7), {2: 5, 3: 40})

    def test_a_float_key_is_dropped_not_truncated_onto_a_neighbour(self):
        # pf-adversary D7: `int(2.9)` landed a value on x=2 (`level`) -- a row
        # nobody addressed.  A row number is never a float, so this is a bug
        # in the source, not a value to round.
        lane_hooks.register_live_attr_values_source(lambda cid: {2.9: 999})
        captured, sys.stderr = sys.stderr, io.StringIO()
        try:
            answer = lane_hooks.current_named_attr_values(7)
            said = sys.stderr.getvalue()
        finally:
            sys.stderr = captured
        self.assertEqual(answer, {})
        self.assertIn("not a row number", said)

    def test_a_bool_key_is_dropped_because_true_is_one_in_python(self):
        lane_hooks.register_live_attr_values_source(lambda cid: {True: 5})
        captured, sys.stderr = sys.stderr, io.StringIO()
        try:
            self.assertEqual(lane_hooks.current_named_attr_values(7), {})
        finally:
            sys.stderr = captured

    def test_two_keys_that_collide_after_coercion_keep_the_first_and_say_so(self):
        # pf-adversary D7: `{2: 40, "2": 999}` silently dropped one of two.
        lane_hooks.register_live_attr_values_source(
            lambda cid: {2: 40, "2": 999}
        )
        captured, sys.stderr = sys.stderr, io.StringIO()
        try:
            answer = lane_hooks.current_named_attr_values(7)
            said = sys.stderr.getvalue()
        finally:
            sys.stderr = captured
        self.assertEqual(answer, {2: 40})
        self.assertIn("duplicate row 2", said)

    def test_a_mapping_whose_iteration_raises_cannot_escape(self):
        # pf-adversary D5: `values.items()` was outside the net, so a dict
        # SUBCLASS could raise straight past a docstring promising this
        # function never does -- into a START_GAME handler that catches only
        # KeyError/PermissionError/ValueError/RuntimeError.
        class Hostile(dict):
            def items(self):
                raise MemoryError("not today")

        lane_hooks.register_live_attr_values_source(lambda cid: Hostile({2: 1}))
        captured, sys.stderr = sys.stderr, io.StringIO()
        try:
            answer = lane_hooks.current_named_attr_values(7)
            said = sys.stderr.getvalue()
        finally:
            sys.stderr = captured
        self.assertEqual(answer, {})
        self.assertIn("iterating", said)

    def test_no_source_registered_says_so_once_rather_than_looking_like_no_data(self):
        # pf-adversary D4: `{}` from "nobody wired a source in this process"
        # and `{}` from "this character has no values" become the SAME
        # `missing_named_rows` refusal upstairs.  The return value cannot
        # carry the difference; the console does, once, so a client cannot
        # drive an unbounded log with it.
        lane_hooks._LIVE_ATTR_NO_SOURCE_ANNOUNCED = False
        lane_hooks.register_live_attr_values_source(None)
        captured, sys.stderr = sys.stderr, io.StringIO()
        try:
            lane_hooks.current_named_attr_values(7)
            lane_hooks.current_named_attr_values(8)
            said = sys.stderr.getvalue()
        finally:
            sys.stderr = captured
        self.assertEqual(said.count("NO_SOURCE_REGISTERED"), 1)

    def test_registering_prints_a_token_a_wired_grep_can_find(self):
        # pf-adversary D3: this package prints a token for every hook,
        # composer and responder it registers; this source printed nothing,
        # so "boot installed it" and "nobody did" read identically.
        captured, sys.stderr = sys.stderr, io.StringIO()
        try:
            lane_hooks.register_live_attr_values_source(lambda cid: {})
            first = sys.stderr.getvalue()
            lane_hooks.register_live_attr_values_source(lambda cid: {})
            second = sys.stderr.getvalue()
        finally:
            sys.stderr = captured
        self.assertIn("LANE_HOOK_LIVE_ATTR_SOURCE REGISTERED", first)
        self.assertNotIn("REPLACED_AN_EARLIER_SOURCE", first)
        # pf-adversary D6: a second registration is two authors for one
        # answer.  The sibling registries refuse a duplicate loudly; this one
        # is last-wins by design (boot must beat whatever a test left), so it
        # says so instead of overwriting in silence.
        self.assertIn("REPLACED_AN_EARLIER_SOURCE", second)

    def test_the_source_the_boot_installs_names_itself_in_the_token(self):
        store = _StubStore(columns={"level": 1}, name="Anne")
        captured, sys.stderr = sys.stderr, io.StringIO()
        try:
            lane_hooks.register_live_attr_values_source(
                live.source_for_store(store)
            )
            said = sys.stderr.getvalue()
        finally:
            sys.stderr = captured
        self.assertIn("live_named_attr_values.source_for_store", said)

    def test_a_non_callable_source_is_refused_at_registration(self):
        with self.assertRaises(TypeError):
            lane_hooks.register_live_attr_values_source(object())

    def test_the_store_backed_source_reaches_the_point_end_to_end(self):
        store = _StubStore(
            columns={"level": 2, "hp_current": 90, "hp_max": 120}, name="Anne",
        )
        lane_hooks.register_live_attr_values_source(
            live.source_for_store(store)
        )
        values = lane_hooks.current_named_attr_values(7)
        self.assertEqual(values[2], 2)
        self.assertEqual(values[1], "Anne")


class WhatAttrWireDoesWithItTests(unittest.TestCase):
    """The consumer's answer through the REAL read point, not a fake."""

    def setUp(self):
        self.addCleanup(
            lane_hooks.register_live_attr_values_source,
            lane_hooks._LIVE_ATTR_VALUES_SOURCE,
        )

    def test_todays_shipped_answer_is_a_named_per_row_refusal(self):
        # The whole value of this round in one assertion: the refusal stops
        # being "nobody built the door" and becomes the list of values this
        # server does not know.
        store = _StubStore(
            columns={"level": 1, "hp_current": 100, "hp_max": 100}, name="Anne",
        )
        lane_hooks.register_live_attr_values_source(
            live.source_for_store(store)
        )
        with self.assertRaises(attr_wire.AttrWireError) as caught:
            attr_wire.live_named_values(7, hooks=lane_hooks)
        message = str(caught.exception)
        self.assertIn("missing_named_rows", message)
        self.assertNotIn("no_read_point", message)
        cash_x = attr_wire.BY_NAME["cash"][0]
        self.assertIn(str(cash_x), message)

    def test_a_fully_seeded_row_still_refuses_on_the_five_unreachable_rows(self):
        store = _StubStore(columns=_every_typed_column_populated(), name="Anne")
        lane_hooks.register_live_attr_values_source(
            live.source_for_store(store)
        )
        with self.assertRaises(attr_wire.AttrWireError) as caught:
            attr_wire.live_named_values(7, hooks=lane_hooks)
        message = str(caught.exception)
        for x in live.ROWS_WITH_NO_COLUMN_AT_ALL:
            self.assertIn(str(x), message)

    def test_the_seeder_refuses_out_loud_and_caches_nothing(self):
        store = _StubStore(
            columns={"level": 1, "hp_current": 100, "hp_max": 100}, name="Anne",
        )
        lane_hooks.register_live_attr_values_source(
            live.source_for_store(store)
        )
        cache = attr_wire.RawBlockCache()
        stream = io.StringIO()
        ok = attr_wire.seed_cache_from_live_values(
            cache, 7, hooks=lane_hooks, stream=stream,
        )
        self.assertFalse(ok)
        self.assertFalse(cache.is_captured())
        self.assertIn(attr_wire.SEED_REFUSED_CONSOLE_TOKEN, stream.getvalue())


class TheBootWiringTests(unittest.TestCase):
    def test_app_installs_the_source_from_the_store_it_opens(self):
        # PARSED, NOT GREPPED, and that is the repair of pf-adversary defect
        # D3 (round `dwvbpm`): the first version of this test asserted two
        # substrings were somewhere in app.py's TEXT, and stayed green when
        # the whole call was replaced by a COMMENT containing both of them.
        # A check that cannot tell wired from unwired is the "reports on a
        # substring instead of acting on the wiring" shape this project has
        # been bitten by before.  An AST walk sees code or it does not.
        #
        # Still not a behaviour test -- booting app.py needs a socket and a
        # v141 image -- but it now fails for the one thing it claims to
        # guard: the call being gone.
        tree = ast.parse(
            (ROOT / "src" / "pirateforce_foundation" / "app.py").read_text(
                encoding="utf-8"
            )
        )
        installs = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr != "register_live_attr_values_source":
                continue
            installs.append(node)
        self.assertEqual(
            len(installs), 1,
            "app.py must install the live-attr source exactly once as real "
            "code (found %d call sites)" % len(installs),
        )
        argument = installs[0].args[0] if installs[0].args else None
        self.assertIsInstance(
            argument, ast.Call,
            "the installed source must be built by a call, not a name or a "
            "literal",
        )
        self.assertEqual(argument.func.attr, "source_for_store")
        self.assertEqual(
            [a.id for a in argument.args if isinstance(a, ast.Name)],
            ["store"],
            "the source must be bound to the store this boot opened",
        )


class AgainstARealMigratedStoreTests(unittest.TestCase):
    """The one test that is not duck-typed.

    pf-adversary defect D9 (round `dwvbpm`): every other test in this file
    hands `values_for` a stub, so renaming `SQLiteStore.read_typed_attributes`
    or `get_character` would leave the file green while the real server
    answered nothing forever -- and the round's own headline number ("4 of
    26") was measured in a throwaway script rather than by anything in the
    repository.  This measures it here, on a store built from the real
    migrations, through the real birth path.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = SQLiteStore(
            str(Path(self._tmp.name) / "pf.sqlite3"), MIGRATIONS,
        )
        self.store.migrate()

    def _born(self, tag, identity_base):
        def build_wire(selector):
            return b"wire", b"avatar", 0x20000001 + identity_base + selector, 0

        account_id = self.store.ensure_account(tag)
        return self.store.create_character(
            account_id, "Born%s" % tag, "born%s" % tag,
            "fingerprint-%s" % tag, build_wire,
            Position(3, 0, 1.0, 2.0, 3.0, heading=0.0),
        )

    def test_a_newborn_answers_exactly_the_four_rows_the_round_claims(self):
        character = self._born("A", 0x1000)
        values = live.values_for(self.store, character.id)
        self.assertEqual(sorted(values), [1, 2, 3, 4])
        self.assertEqual(values[1], "BornA")
        self.assertEqual((values[2], values[3], values[4]), (1, 100, 100))

    def test_the_other_twenty_two_rows_are_absent_on_a_real_row(self):
        character = self._born("B", 0x2000)
        values = live.values_for(self.store, character.id)
        missing = sorted(set(live.named_rows_wanted()) - set(values))
        self.assertEqual(len(missing), 22)
        for name in ("cash", "mp_current", "class_id", "str", "experience"):
            self.assertIn(attr_wire.BY_NAME[name][0], missing)

    def test_the_consumer_names_those_rows_rather_than_the_missing_door(self):
        character = self._born("C", 0x3000)
        self.addCleanup(
            lane_hooks.register_live_attr_values_source,
            lane_hooks._LIVE_ATTR_VALUES_SOURCE,
        )
        lane_hooks.register_live_attr_values_source(
            live.source_for_store(self.store)
        )
        with self.assertRaises(attr_wire.AttrWireError) as caught:
            attr_wire.live_named_values(character.id, hooks=lane_hooks)
        self.assertIn("missing_named_rows", str(caught.exception))
        self.assertNotIn("no_read_point", str(caught.exception))

    def test_two_characters_do_not_read_each_others_rows(self):
        # pf-adversary defect D2: a source hard-wired to one id passed every
        # test in the first draft.  Two real rows, two real names.
        first = self._born("D", 0x4000)
        second = self._born("E", 0x5000)
        source = live.source_for_store(self.store)
        self.assertEqual(source(first.id)[1], "BornD")
        self.assertEqual(source(second.id)[1], "BornE")

    def test_an_id_that_is_not_a_character_answers_nothing(self):
        self.assertEqual(live.values_for(self.store, 999999), {})


class NothingIsInventedForARowWithAColumnTests(unittest.TestCase):
    """pf-adversary defect D1 (round `dwvbpm`), the highest-value repair here.

    The module's founding rule is "a row with no honest source is ABSENT".
    The first draft's tests checked that for cash, mp_current, str and the
    five column-less rows -- and for zeros.  A mutant adding
    `values.setdefault(13, 1)` (class_id, the exact constant the docstring
    declines by name) plus two more non-zero guesses left the ENTIRE suite
    green: 9139 passed, identical to control.

    So the assertion is inverted here: the key set must be EXACTLY what the
    store handed over, for every column, with nothing added.
    """

    def test_the_answer_names_exactly_the_columns_the_store_returned(self):
        for column, spec in typed_attrs.TYPED_COLUMNS.items():
            with self.subTest(column=column):
                value = 1.0 if spec.sql_type == "REAL" else 1
                store = _StubStore(columns={column: value}, name=None)
                values = live.values_for(store, 7)
                expected = (
                    {spec.x} if spec.x in set(live.named_rows_wanted()) else set()
                )
                self.assertEqual(
                    set(values), expected,
                    "one column in, %s out -- a key nobody handed over is an "
                    "invented value" % sorted(values),
                )

    def test_an_empty_store_row_answers_nothing_at_all(self):
        store = _StubStore(columns={}, name=None)
        self.assertEqual(live.values_for(store, 7), {})

    def test_a_read_that_fails_says_so_instead_of_answering_silently(self):
        # pf-adversary D9: the first draft swallowed both reads with no line,
        # so a renamed store method looked exactly like an unseeded character.
        store = _StubStore(raises=OSError("no such column: level"))
        stream = io.StringIO()
        self.assertEqual(live.values_for(store, 7, stream=stream), {})
        said = stream.getvalue()
        self.assertIn(live.READ_REFUSED_CONSOLE_TOKEN, said)
        self.assertIn("typed_columns", said)
        self.assertIn("character_row", said)
        self.assertTrue(all(32 <= ord(c) <= 126 or c == "\n" for c in said))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
