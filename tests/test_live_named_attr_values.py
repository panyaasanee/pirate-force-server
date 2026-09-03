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

import io
import sys
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


class _Character:
    def __init__(self, name):
        self.name = name


class _StubStore:
    """Only the two read-only methods the source uses, nothing else."""

    def __init__(self, columns=None, name="Blackbeard", raises=None):
        self._columns = dict(columns or {})
        self._name = name
        self._raises = raises

    def read_typed_attributes(self, character_id):
        if self._raises is not None:
            raise self._raises
        return dict(self._columns)

    def get_character(self, character_id):
        if self._raises is not None:
            raise self._raises
        if self._name is None:
            raise KeyError(character_id)
        return _Character(self._name)


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
        self.assertNotIn(1, live.values_for(store, 1))

    def test_a_non_string_name_is_absent(self):
        store = _StubStore(columns={"level": 1}, name=b"Anne")
        self.assertNotIn(1, live.values_for(store, 1))

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
        # Not a behaviour test (booting the app needs a socket and a v141
        # image); it pins that the ONE boot call site exists and names both
        # halves, so deleting either is a red test rather than a server that
        # silently answers nothing forever.
        text = (
            ROOT / "src" / "pirateforce_foundation" / "app.py"
        ).read_text(encoding="utf-8")
        self.assertIn("register_live_attr_values_source", text)
        self.assertIn("live_named_attr_values.source_for_store(store)", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
