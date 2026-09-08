"""LANE-Q: the adapter that puts quest progress on a DURABLE row.

Three levels, same shape as ``tests/test_script_lua_api_quest.py``, and all
three run on a machine with no ``lupa`` and no database: the adapter alone
against a fake carrying LANE-DB's contract, the substitutability of that
adapter for ``quest.InMemoryQuestStateStore`` at the seam
``quest.build_namespace(store=...)`` publishes, and the refusal behaviour a
store's own documented errors must produce.

The fake here is NOT a stand-in for a schema nobody has agreed on: every
method name, argument order, return shape and error family it implements is
copied from LANE-DB's letter (``pf_bridge/notes_to_chief/20260905_2212_
LANE-DB-TO-LANE-Q-quest-state-doors-declared-and-opened-this-round.md``),
which is the contract the real accessor will honour when it lands.  The day
it lands, THIS FILE is what says the adapter already spoke to it correctly.
"""
import sqlite3
import unittest

from pirateforce_foundation.lua_api import quest
from pirateforce_foundation.lua_api import quest_state_store as qss


class _FlagRow(object):
    """LANE-DB's ``QuestFlagRow``, the fields this lane reads."""

    def __init__(self, character_id, quest_id, flag_value):
        self.character_id = character_id
        self.quest_id = quest_id
        self.flag_value = flag_value
        self.updated_at = "2026-09-08T16:00:00+07:00"


class _CounterRow(object):
    """LANE-DB's ``QuestCounterRow``."""

    def __init__(self, character_id, quest_id, counter_name, counter_value):
        self.character_id = character_id
        self.quest_id = quest_id
        self.counter_name = counter_name
        self.counter_value = counter_value
        self.updated_at = "2026-09-08T16:00:00+07:00"


class FakeQuestStateDoors(object):
    """A store carrying exactly the five doors LANE-DB's letter declared.

    Rows are read back after the write (never an echo of the argument):
    ``set_quest_flag`` stores, then builds its row from what it stored, so a
    test can make the two differ (see ``coerce``) and prove the adapter
    reports the STORED number rather than the one it was handed.
    """

    def __init__(self, coerce=None, known_characters=(1, 2, 7)):
        self.flags = {}
        self.counters = {}
        self.known = set(known_characters)
        self.coerce = coerce or (lambda value: value)
        self.calls = []

    def _check(self, character_id, quest_id):
        if character_id not in self.known:
            raise KeyError(character_id)
        if not 0 <= quest_id <= 0xFFFF:
            raise ValueError("quest_id out of u16 range: %r" % (quest_id,))

    def get_quest_flag(self, character_id, quest_id):
        self.calls.append(("get_quest_flag", character_id, quest_id))
        self._check(character_id, quest_id)
        if (character_id, quest_id) not in self.flags:
            return None
        return _FlagRow(character_id, quest_id, self.flags[(character_id, quest_id)])

    def set_quest_flag(self, character_id, quest_id, flag_value):
        self.calls.append(("set_quest_flag", character_id, quest_id, flag_value))
        self._check(character_id, quest_id)
        self.flags[(character_id, quest_id)] = self.coerce(flag_value)
        return _FlagRow(character_id, quest_id, self.flags[(character_id, quest_id)])

    def get_quest_counter(self, character_id, quest_id, counter_name):
        self.calls.append(("get_quest_counter", character_id, quest_id, counter_name))
        self._check(character_id, quest_id)
        key = (character_id, quest_id, counter_name)
        if key not in self.counters:
            return None
        return _CounterRow(character_id, quest_id, counter_name, self.counters[key])

    def set_quest_counter(self, character_id, quest_id, counter_name, counter_value):
        self.calls.append(
            ("set_quest_counter", character_id, quest_id, counter_name, counter_value))
        self._check(character_id, quest_id)
        key = (character_id, quest_id, counter_name)
        self.counters[key] = self.coerce(counter_value)
        return _CounterRow(character_id, quest_id, counter_name, self.counters[key])

    def increment_quest_counter(self, character_id, quest_id, counter_name, delta=1):
        key = (character_id, quest_id, counter_name)
        return self.set_quest_counter(
            character_id, quest_id, counter_name, self.counters.get(key, 0) + delta)


def without_doors(store, *names):
    """``store`` minus some doors -- an object carrying only the attributes
    left, which is what a half-implemented accessor looks like from here.

    A proxy rather than ``del store.method``: the doors are class
    attributes on the fake, so deleting them through an instance raises
    and would make the test about Python rather than about the adapter.
    """

    class _Stripped(object):
        pass

    stripped = _Stripped()
    for name in qss.REQUIRED_DOORS + qss.OPTIONAL_DOORS:
        if name in names:
            continue
        door = getattr(store, name, None)
        if door is not None:
            setattr(stripped, name, door)
    return stripped


class DoorDetectionTests(unittest.TestCase):
    """What counts as "this object can hold quest state"."""

    def test_a_store_with_every_door_is_missing_none(self):
        self.assertEqual(qss.missing_doors(FakeQuestStateDoors()), ())

    def test_a_store_with_no_doors_names_all_four(self):
        self.assertEqual(qss.missing_doors(object()), qss.REQUIRED_DOORS)

    def test_a_half_wired_door_set_to_none_counts_as_missing(self):
        store = FakeQuestStateDoors()
        store.set_quest_flag = None
        self.assertEqual(qss.missing_doors(store), ("set_quest_flag",))

    def test_construction_refuses_a_store_that_cannot_hold_quest_state(self):
        with self.assertRaises(qss.QuestStateDoorsMissing) as caught:
            qss.StoreBackedQuestStateStore(object())
        for door in qss.REQUIRED_DOORS:
            self.assertIn(door, str(caught.exception))

    def test_the_optional_door_is_not_required(self):
        store = without_doors(FakeQuestStateDoors(), "increment_quest_counter")
        self.assertFalse(hasattr(store, "increment_quest_counter"))
        self.assertEqual(qss.missing_doors(store), ())
        self.assertIsNotNone(qss.quest_state_store_for(store, [].append))


class VolatileFallbackIsLoudTests(unittest.TestCase):
    """The one thing this round makes impossible: a silent memory-only host."""

    def test_no_store_at_all_returns_none_and_says_so(self):
        log = []
        self.assertIsNone(qss.quest_state_store_for(None, log.append))
        self.assertEqual(len(log), 1)
        self.assertIn(qss.VOLATILE_TOKEN, log[0])
        self.assertIn("store=none", log[0])
        for door in qss.REQUIRED_DOORS:
            self.assertIn(door, log[0])

    def test_a_store_without_the_doors_is_named_door_by_door(self):
        log = []
        store = without_doors(FakeQuestStateDoors(),
                              "get_quest_counter", "set_quest_counter")
        self.assertIsNone(qss.quest_state_store_for(store, log.append))
        self.assertEqual(len(log), 1)
        self.assertIn("get_quest_counter", log[0])
        self.assertIn("set_quest_counter", log[0])
        self.assertNotIn("get_quest_flag", log[0])

    def test_a_store_with_the_doors_yields_a_durable_adapter_and_no_alarm(self):
        log = []
        adapter = qss.quest_state_store_for(FakeQuestStateDoors(), log.append)
        self.assertIsInstance(adapter, qss.StoreBackedQuestStateStore)
        self.assertTrue(adapter.durable)
        self.assertEqual(log, [])

    def test_the_in_memory_default_does_not_claim_to_be_durable(self):
        """The attribute is the whole point of the token above: a caller can
        tell the two apart without importing either module's class."""
        self.assertIs(quest.InMemoryQuestStateStore().durable, False)
        self.assertIs(
            qss.StoreBackedQuestStateStore(FakeQuestStateDoors()).durable, True)

    def test_the_console_token_is_ascii(self):
        for token in (qss.VOLATILE_TOKEN, qss.REFUSED_TOKEN):
            token.encode("ascii")


class FlagsAndCountersRoundTripTests(unittest.TestCase):
    """The adapter's own contract against a store that honours LANE-DB's."""

    def setUp(self):
        self.log = []
        self.store = FakeQuestStateDoors()
        self.adapter = qss.StoreBackedQuestStateStore(self.store, self.log.append)

    def test_a_flag_never_set_reads_none_not_zero(self):
        self.assertIsNone(self.adapter.get_quest_flag(1, 33))

    def test_a_flag_written_reads_back_the_same_value(self):
        self.assertEqual(self.adapter.set_quest_flag(1, 33, 2), 2)
        self.assertEqual(self.adapter.get_quest_flag(1, 33), 2)
        self.assertEqual(self.log, [])

    def test_two_characters_do_not_share_a_flag(self):
        self.adapter.set_quest_flag(1, 33, 2)
        self.assertIsNone(self.adapter.get_quest_flag(2, 33))

    def test_two_quests_of_one_character_do_not_share_a_flag(self):
        self.adapter.set_quest_flag(1, 33, 2)
        self.assertIsNone(self.adapter.get_quest_flag(1, 34))

    def test_a_write_reports_what_the_store_kept_not_what_it_was_handed(self):
        """LANE-DB's contract is "read back after the write, never a bare
        echo".  A store that clamps must be believed, not overruled."""
        store = FakeQuestStateDoors(coerce=lambda value: min(value, 9))
        adapter = qss.StoreBackedQuestStateStore(store, self.log.append)
        self.assertEqual(adapter.set_quest_flag(1, 33, 40), 9)

    def test_two_counters_in_one_quest_are_separate_rows(self):
        self.adapter.set_quest_counter(1, 33, "820", 3)
        self.adapter.set_quest_counter(1, 33, "821", 7)
        self.assertEqual(self.adapter.get_quest_counter(1, 33, "820"), 3)
        self.assertEqual(self.adapter.get_quest_counter(1, 33, "821"), 7)

    def test_a_counter_never_set_reads_none(self):
        self.assertIsNone(self.adapter.get_quest_counter(1, 33, "820"))

    def test_the_counter_name_this_lane_uses_for_a_mob_survives_the_trip(self):
        name = quest._mob_kill_counter_name(820)
        self.assertEqual(self.adapter.set_quest_counter(1, 33, name, 1), 1)
        self.assertEqual(self.adapter.get_quest_counter(1, 33, name), 1)


class RefusalsAreOursNotTheScriptsTests(unittest.TestCase):
    """Every store refusal answers "no progress", logs, and never raises."""

    def setUp(self):
        self.log = []
        self.store = FakeQuestStateDoors()
        self.adapter = qss.StoreBackedQuestStateStore(self.store, self.log.append)

    def test_the_default_context_character_never_reaches_the_store(self):
        """``quest.DEFAULT_CONTEXT`` is character 0 and real ids start at 1."""
        self.assertEqual(quest.DEFAULT_CONTEXT.character_id, 0)
        self.assertIsNone(self.adapter.get_quest_flag(0, 0))
        self.assertEqual(self.adapter.set_quest_flag(0, 0, 2), qss.REFUSED_VALUE)
        self.assertEqual(self.store.calls, [])
        self.assertTrue(any("no-character" in line for line in self.log))

    def test_an_unknown_character_is_refused_and_logged_not_raised(self):
        self.assertIsNone(self.adapter.get_quest_flag(9999, 33))
        self.assertEqual(self.adapter.set_quest_flag(9999, 33, 2), qss.REFUSED_VALUE)
        self.assertTrue(any("no-such-character" in line for line in self.log))
        self.assertTrue(all(qss.REFUSED_TOKEN in line for line in self.log))

    def test_a_quest_id_outside_u16_is_refused_by_name(self):
        self.assertIsNone(self.adapter.get_quest_flag(1, 0x1FFFF))
        self.assertTrue(any("out-of-range" in line for line in self.log))

    def test_a_write_lock_timeout_is_refused_not_re_raised(self):
        """``store.WriteLockTimeout`` subclasses ``sqlite3.OperationalError``;
        this asserts the FAMILY, which is what the adapter catches."""

        def locked(*args, **kwargs):
            raise sqlite3.OperationalError("database is locked")

        self.store.set_quest_flag = locked
        self.assertEqual(self.adapter.set_quest_flag(1, 33, 2), qss.REFUSED_VALUE)
        self.assertTrue(any("write-locked" in line for line in self.log))

    def test_a_row_of_an_unrecognized_shape_is_refused_not_guessed(self):
        self.store.get_quest_flag = lambda *a: object()
        self.assertIsNone(self.adapter.get_quest_flag(1, 33))
        self.assertTrue(any("unreadable-row" in line for line in self.log))

    def test_a_boolean_is_not_accepted_as_a_flag_value(self):
        class _Boolish(object):
            flag_value = True

        self.store.get_quest_flag = lambda *a: _Boolish()
        self.assertIsNone(self.adapter.get_quest_flag(1, 33))
        self.assertTrue(any("unreadable-row" in line for line in self.log))

    def test_a_door_that_answers_none_to_a_write_has_not_honoured_the_contract(self):
        self.store.set_quest_flag = lambda *a: None
        self.assertEqual(self.adapter.set_quest_flag(1, 33, 2), qss.REFUSED_VALUE)
        self.assertTrue(any("no-row-after-write" in line for line in self.log))

    def test_a_bug_in_this_lane_is_not_swallowed_as_a_store_refusal(self):
        """A ``TypeError`` from a mis-wired adapter must reach the caller;
        only the three documented families degrade."""

        def wrong_arity(character_id):
            return None

        self.store.get_quest_flag = wrong_arity
        with self.assertRaises(TypeError):
            self.adapter.get_quest_flag(1, 33)

    def test_the_refusal_log_is_capped_but_never_silences_the_first_of_a_kind(self):
        for quest_id in range(qss.REFUSAL_LOG_CAP + 50):
            self.adapter.get_quest_flag(9999, quest_id)
        self.assertEqual(len(self.log), qss.REFUSAL_LOG_CAP)
        before = len(self.log)
        self.store.get_quest_flag = lambda *a: object()
        self.adapter.get_quest_flag(1, 1)
        self.assertEqual(len(self.log), before,
                         "cap reached: this documents the cost, see the "
                         "module's REFUSAL_LOG_CAP docstring")

    def test_a_repeated_refusal_is_logged_once(self):
        for _ in range(20):
            self.adapter.get_quest_flag(9999, 33)
        self.assertEqual(len(self.log), 1)

    def test_a_store_backed_adapter_without_a_log_still_refuses_quietly(self):
        adapter = qss.StoreBackedQuestStateStore(self.store)
        self.assertIsNone(adapter.get_quest_flag(9999, 33))
        self.assertEqual(adapter.set_quest_flag(9999, 33, 2), qss.REFUSED_VALUE)


class SubstitutableAtTheSeamTests(unittest.TestCase):
    """The adapter is what ``build_namespace(store=...)`` already accepts."""

    def _namespace(self, store):
        from pirateforce_foundation.lua_api import spec as api_spec
        calls = []
        ns = quest.build_namespace(
            api_spec.NAMESPACE_METHODS["Quest"], calls.append,
            context=quest.QuestContext(character_id=7, quest_id=33),
            store=store)
        return ns, calls

    def test_every_protocol_method_exists_with_the_same_signature(self):
        import inspect
        for name in ("get_quest_flag", "set_quest_flag",
                     "get_quest_counter", "set_quest_counter"):
            memory = inspect.signature(
                getattr(quest.InMemoryQuestStateStore(), name))
            durable = inspect.signature(
                getattr(qss.StoreBackedQuestStateStore(FakeQuestStateDoors()), name))
            self.assertEqual(str(memory), str(durable), name)

    def test_a_real_quest_namespace_writes_and_reads_through_the_adapter(self):
        """The token PANYA's order names: SetFlag then GetQuestFlag reads the
        same value back -- here through a DURABLE store, not process memory."""
        store = FakeQuestStateDoors()
        ns, _ = self._namespace(qss.StoreBackedQuestStateStore(store))
        ns["SetFlag"](2)
        self.assertEqual(store.flags[(7, 33)], 2)
        self.assertEqual(ns["GetQuestFlag"](33), 2)

    def test_the_row_outlives_the_namespace_that_wrote_it(self):
        """A second namespace -- the shape a relog produces once the rows are
        real -- reads what the first one wrote, which is exactly what
        ``InMemoryQuestStateStore`` cannot do across a process."""
        store = FakeQuestStateDoors()
        first, _ = self._namespace(qss.StoreBackedQuestStateStore(store))
        first["SetFlag"](2)
        second, _ = self._namespace(qss.StoreBackedQuestStateStore(store))
        self.assertEqual(second["GetQuestFlag"](33), 2)

    def test_the_same_two_namespaces_over_memory_do_not_share_anything(self):
        """The control for the test above: this is today's behaviour."""
        first, _ = self._namespace(quest.InMemoryQuestStateStore())
        first["SetFlag"](2)
        second, _ = self._namespace(quest.InMemoryQuestStateStore())
        self.assertEqual(second["GetQuestFlag"](33), quest.STUB_DEFAULT)


if __name__ == "__main__":
    unittest.main()
