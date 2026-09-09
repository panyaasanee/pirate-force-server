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
from pirateforce_foundation.lua_api import quest_state_signal as qs_signal


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
        """LANE-DB's atomic door.  Records ITS OWN name in ``calls``.

        It used to delegate to ``set_quest_counter`` and so appeared in
        ``calls`` under that name -- which made "the adapter called the
        atomic door" and "the adapter called the absolute-set door"
        indistinguishable from a test, exactly the distinction the seam's
        newest method is about.  The read below is a plain dict lookup,
        not a call to ``get_quest_counter``: it stands in for the
        read-modify-write LANE-DB does INSIDE one transaction, and a fake
        that reached through its own public door would model the very
        window the real door closes.
        """
        self.calls.append(
            ("increment_quest_counter", character_id, quest_id, counter_name, delta))
        self._check(character_id, quest_id)
        key = (character_id, quest_id, counter_name)
        self.counters[key] = self.coerce(self.counters.get(key, 0) + delta)
        return _CounterRow(character_id, quest_id, counter_name, self.counters[key])


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

    def test_a_store_with_no_doors_names_every_required_one(self):
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

    def test_the_increment_door_is_optional_because_nothing_calls_it_yet(self):
        """Round `7qw2tr` promoted it to required and put it straight back.

        The promotion was priced by pf-adversary and lost: a store that
        lands the four flag/counter doors but names the atomic one
        differently, or ships it a round later, would make
        ``missing_doors`` non-empty and throw a WORKING durable store away
        -- every quest in the game back to process memory, over a door no
        production path calls.  Durable flags are worth more than a guard
        on an uncalled path, so the refusal moved to the call itself.
        """
        store = without_doors(FakeQuestStateDoors(), "increment_quest_counter")
        self.assertFalse(hasattr(store, "increment_quest_counter"))
        self.assertEqual(qss.missing_doors(store), ())
        adapter = qss.quest_state_store_for(store, [].append)
        self.assertIsNotNone(adapter)
        self.assertTrue(adapter.durable)

    def test_flags_still_persist_through_a_store_with_no_atomic_door(self):
        """The point of keeping it optional: this must keep working."""
        store = without_doors(FakeQuestStateDoors(), "increment_quest_counter")
        adapter = qss.StoreBackedQuestStateStore(store, [].append)
        self.assertEqual(adapter.set_quest_flag(7, 33, 2), 2)
        self.assertEqual(adapter.get_quest_flag(7, 33), 2)

    def test_the_atomic_method_refuses_by_name_when_the_door_is_absent(self):
        """And never silently falls back to get-then-set, which would be
        the lost update wearing the atomic method's name."""
        log = []
        store = without_doors(FakeQuestStateDoors(), "increment_quest_counter")
        adapter = qss.StoreBackedQuestStateStore(store, log.append)
        self.assertEqual(adapter.increment_quest_counter(7, 33, "mob:900"),
                         qss.REFUSED_VALUE)
        self.assertEqual(len(log), 1)
        self.assertIn("method=increment_quest_counter", log[0])
        self.assertIn("reason=no-atomic-door", log[0])
        self.assertIsNone(adapter.get_quest_counter(7, 33, "mob:900"))


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
        # SAYS "refused", NOT "never set".  Until round `7cf5ak` these two
        # answers were `None` and a bare 0, i.e. exactly what a healthy
        # store says about a quest nobody has started -- which is how a
        # refused write came back out of `Quest.CanReportDailyQuest()` as
        # "you may report again".  Numerically nothing moved (both still
        # equal 0 / read as no progress); what is new is that the answer
        # can be told apart.
        denied = self.adapter.get_quest_flag(0, 0)
        self.assertTrue(qs_signal.is_refused(denied))
        self.assertEqual(qs_signal.reason_of(denied), "no-character")
        self.assertEqual(self.adapter.set_quest_flag(0, 0, 2), qss.REFUSED_VALUE)
        self.assertEqual(self.store.calls, [])
        self.assertTrue(any("no-character" in line for line in self.log))

    def test_an_unknown_character_is_refused_and_logged_not_raised(self):
        denied = self.adapter.get_quest_flag(9999, 33)
        self.assertTrue(qs_signal.is_refused(denied))
        self.assertEqual(int(denied), 0)
        self.assertEqual(self.adapter.set_quest_flag(9999, 33, 2), qss.REFUSED_VALUE)
        self.assertTrue(any("no-such-character" in line for line in self.log))
        self.assertTrue(all(qss.REFUSED_TOKEN in line for line in self.log))

    def test_a_quest_id_outside_u16_is_refused_by_name(self):
        self.assertTrue(qs_signal.is_refused(
            self.adapter.get_quest_flag(1, 0x1FFFF)))
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
        self.assertTrue(qs_signal.is_refused(self.adapter.get_quest_flag(1, 33)))
        self.assertTrue(any("unreadable-row" in line for line in self.log))

    def test_a_boolean_is_not_accepted_as_a_flag_value(self):
        class _Boolish(object):
            flag_value = True

        self.store.get_quest_flag = lambda *a: _Boolish()
        self.assertTrue(qs_signal.is_refused(self.adapter.get_quest_flag(1, 33)))
        self.assertTrue(any("unreadable-row" in line for line in self.log))

    def test_a_door_that_answers_none_to_a_write_has_not_honoured_the_contract(self):
        self.store.set_quest_flag = lambda *a: None
        self.assertEqual(self.adapter.set_quest_flag(1, 33, 2), qss.REFUSED_VALUE)
        self.assertTrue(any("no-row-after-write" in line for line in self.log))

    def test_a_flag_row_written_by_someone_else_outside_the_range_is_refused(self):
        """pf-adversary F1 (re-review of merged PR #1184): ``store.py``
        enforces no range on ``flag_value`` at all (COO decision, and its
        own test proves negative values are stored as given) -- only this
        lane's two coerced Lua-facing closures ever stay inside
        ``0..0xFFFF``.  A row some OTHER writer put outside that range
        (here: directly in the fake, standing in for an admin tool or a
        migration) must be refused at THIS seam, not handed back as a
        number that could equal ``quest.QUEST_FLAG_UNREADABLE`` itself.
        """
        self.store.flags[(1, 33)] = -1
        denied = self.adapter.get_quest_flag(1, 33)
        self.assertTrue(qs_signal.is_refused(denied))
        self.assertEqual(qs_signal.reason_of(denied), "unreadable-row")
        self.assertTrue(any("unreadable-row" in line for line in self.log))

    def test_a_flag_write_that_reads_back_out_of_range_is_refused_not_trusted(self):
        """Same gap, on the WRITE path: the store's read-back after a write
        disagreeing with what this lane's own coercion just sent means a
        concurrent writer this lane does not control landed in between."""
        self.store.coerce = lambda value: -1
        answer = self.adapter.set_quest_flag(1, 33, 5)
        self.assertTrue(qs_signal.is_refused(answer))
        self.assertEqual(qs_signal.reason_of(answer), "unreadable-row")

    def test_a_flag_value_at_the_range_edges_is_still_accepted(self):
        """The fix refuses OUTSIDE ``0..0xFFFF``, not the edges themselves."""
        self.assertEqual(self.adapter.set_quest_flag(1, 33, 0), 0)
        self.assertEqual(self.adapter.get_quest_flag(1, 33), 0)
        self.assertEqual(self.adapter.set_quest_flag(1, 33, 0xFFFF), 0xFFFF)
        self.assertEqual(self.adapter.get_quest_flag(1, 33), 0xFFFF)

    def test_a_bug_in_this_lane_is_not_swallowed_as_a_store_refusal(self):
        """A ``TypeError`` from a mis-wired adapter must reach the caller;
        only the three documented families degrade."""

        def wrong_arity(character_id):
            return None

        self.store.get_quest_flag = wrong_arity
        with self.assertRaises(TypeError):
            self.adapter.get_quest_flag(1, 33)

    def test_the_refusal_log_cap_silences_new_failure_families_too(self):
        """RENAMED, round `7qw2tr` (pf-adversary F8).  It used to be called
        ``..._but_never_silences_the_first_of_a_kind`` and its body asserts
        the exact opposite: once the cap is reached, a brand-new failure
        family (a different reason, a different character, never logged
        before) is silenced too.  A green PASS under the old name read as a
        guarantee nobody has.  The cost is real and stays documented rather
        than asserted away: on a wiring that keeps one adapter alive for
        the process, quest-state refusals go permanently dark after 256
        distinct keys, with no line saying so.  Named as a debt in the
        round file.
        """
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
        self.assertTrue(qs_signal.is_refused(adapter.get_quest_flag(9999, 33)))
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
        """The names are READ OFF the Protocol, never typed here.

        A hand-kept tuple was what let ``increment_quest_counter`` be
        added to one implementation and not the other without this test
        noticing -- the asymmetry would first have shown up as an
        AttributeError in production, never in a test run.
        """
        import inspect
        self.assertIn("increment_quest_counter", quest.QUEST_STATE_STORE_METHODS)
        for name in quest.QUEST_STATE_STORE_METHODS:
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


class AtomicIncrementTests(unittest.TestCase):
    """The one number two server events can move in the same instant.

    ``Quest.MobKillCount`` starts a counter and ``CheckMobKillCount``
    compares it, but the thing that MOVES it is a mob dying -- an event
    that arrives from outside any script, and can arrive twice at once.
    Every test here is about the difference between "add one" and "read,
    add one, write back", because that difference is a player killing six
    mobs for a five-kill quest and being told to keep going.
    """

    def test_the_in_memory_default_counts_from_nothing(self):
        store = quest.InMemoryQuestStateStore()
        self.assertIsNone(store.get_quest_counter(7, 33, "mob:900"))
        self.assertEqual(store.increment_quest_counter(7, 33, "mob:900"), 1)
        self.assertEqual(store.increment_quest_counter(7, 33, "mob:900"), 2)
        self.assertEqual(store.get_quest_counter(7, 33, "mob:900"), 2)

    def test_the_in_memory_default_adds_to_a_value_set_absolutely(self):
        """``MobKillCount`` writes 0 at Accept_Run; kills add to THAT row."""
        store = quest.InMemoryQuestStateStore()
        store.set_quest_counter(7, 33, "mob:900", 0)
        store.increment_quest_counter(7, 33, "mob:900", 3)
        self.assertEqual(store.get_quest_counter(7, 33, "mob:900"), 3)

    def test_the_in_memory_increment_never_goes_through_its_own_public_pair(self):
        """THE MUTANT THIS EXISTS TO KILL, measured this round.

        Rewriting ``increment_quest_counter`` as ``get_quest_counter``
        then ``set_quest_counter`` -- which releases the lock between the
        two and so reopens the lost update -- was NOT caught by the
        threaded test below: 8 threads x 50 increments interleaved cleanly
        every run, because the window is a few bytecodes wide and the GIL
        rarely lands in it.  A test that only sometimes can fail is a test
        that reports "safe" for the wrong reason, so the pin is structural
        instead: the two public methods are observable from a subclass,
        and an implementation that calls either of them has released the
        lock between reading and writing.
        """
        seen = []

        class Watched(quest.InMemoryQuestStateStore):
            def get_quest_counter(self, *args, **kwargs):
                seen.append("get")
                return super(Watched, self).get_quest_counter(*args, **kwargs)

            def set_quest_counter(self, *args, **kwargs):
                seen.append("set")
                return super(Watched, self).set_quest_counter(*args, **kwargs)

        store = Watched()
        self.assertEqual(store.increment_quest_counter(7, 33, "mob:900"), 1)
        self.assertEqual(store.increment_quest_counter(7, 33, "mob:900"), 2)
        self.assertEqual(seen, [])

    def test_concurrent_increments_do_not_lose_one_another(self):
        """Real threads, kept as the coarse check the one above cannot be:
        it would catch an implementation that takes NO lock at all.  It
        does NOT catch a two-call read-modify-write -- see above for the
        measurement -- so it is not the pin, it is the floor."""
        import threading
        store = quest.InMemoryQuestStateStore()
        store.set_quest_counter(7, 33, "mob:900", 0)
        barrier = threading.Barrier(8)

        def kill():
            barrier.wait()
            for _ in range(50):
                store.increment_quest_counter(7, 33, "mob:900")

        threads = [threading.Thread(target=kill) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(store.get_quest_counter(7, 33, "mob:900"), 400)

    def test_the_adapter_never_reads_before_it_increments(self):
        """The atomicity lives in LANE-DB's transaction, so a read HERE
        would put the lost-update window back outside it."""
        store = FakeQuestStateDoors()
        adapter = qss.StoreBackedQuestStateStore(store, [].append)
        adapter.increment_quest_counter(7, 33, "mob:900", 1)
        names = [call[0] for call in store.calls]
        self.assertIn("increment_quest_counter", names)
        self.assertNotIn("get_quest_counter", names)

    def test_the_adapter_reports_the_stored_value_not_the_delta(self):
        """A store that clamps must be believed over the argument."""
        store = FakeQuestStateDoors(coerce=lambda value: min(value, 2))
        adapter = qss.StoreBackedQuestStateStore(store, [].append)
        self.assertEqual(adapter.increment_quest_counter(7, 33, "mob:900", 9), 2)

    def test_a_refused_increment_reports_no_progress_and_says_why(self):
        """It must NOT report the delta as landed: a caller that believes a
        kill was credited will never credit it again."""
        log = []
        store = FakeQuestStateDoors(known_characters=(1,))
        adapter = qss.StoreBackedQuestStateStore(store, log.append)
        self.assertEqual(adapter.increment_quest_counter(7, 33, "mob:900"),
                         qss.REFUSED_VALUE)
        self.assertEqual(len(log), 1)
        self.assertIn(qss.REFUSED_TOKEN, log[0])
        self.assertIn("method=increment_quest_counter", log[0])
        self.assertIn("reason=no-such-character", log[0])

    def test_a_write_lock_on_the_increment_is_refused_not_raised(self):
        """A script must never be blamed for the server's own lock."""
        log = []
        store = FakeQuestStateDoors()

        def locked(*args, **kwargs):
            raise sqlite3.OperationalError("database is locked")

        store.increment_quest_counter = locked
        adapter = qss.StoreBackedQuestStateStore(store, log.append)
        self.assertEqual(adapter.increment_quest_counter(7, 33, "mob:900"),
                         qss.REFUSED_VALUE)
        self.assertIn("reason=write-locked", log[0])

    def test_a_door_that_answers_with_no_row_is_a_contract_breach(self):
        log = []
        store = FakeQuestStateDoors()
        store.increment_quest_counter = lambda *a, **k: None
        adapter = qss.StoreBackedQuestStateStore(store, log.append)
        self.assertEqual(adapter.increment_quest_counter(7, 33, "mob:900"),
                         qss.REFUSED_VALUE)
        self.assertIn("reason=no-row-after-write", log[0])

    def test_a_bug_in_this_lane_is_still_not_swallowed(self):
        """Same posture as every other method here: only the store's own
        documented refusals are absorbed."""
        store = FakeQuestStateDoors()

        def wrong_arity(character_id, quest_id):
            raise AssertionError("unreachable")

        store.increment_quest_counter = wrong_arity
        adapter = qss.StoreBackedQuestStateStore(store, [].append)
        with self.assertRaises(TypeError):
            adapter.increment_quest_counter(7, 33, "mob:900")

    def test_the_default_context_character_never_reaches_the_store(self):
        store = FakeQuestStateDoors()
        adapter = qss.StoreBackedQuestStateStore(store, [].append)
        self.assertEqual(
            adapter.increment_quest_counter(
                quest.DEFAULT_CONTEXT.character_id, 33, "mob:900"),
            qss.REFUSED_VALUE)
        self.assertEqual(store.calls, [])


class DispatchChoosesTheStoreOutLoudTests(unittest.TestCase):
    """``lua_api.dispatch`` is the ONE place the swap happens.

    COO-DECISION 2026-09-08T16:42 asked for a junction where "the real one
    from the DB arrives" is a one-line change rather than a hunt.  These
    tests are about the junction, not about Lua: none of them loads a
    script, so none of them needs ``lupa`` or a corpus.
    """

    def setUp(self):
        from pirateforce_foundation.lua_api import dispatch
        self.dispatch = dispatch

    def test_a_store_with_the_doors_yields_the_durable_one_and_says_so(self):
        log = []
        chosen = self.dispatch.resolve_quest_state_store(
            FakeQuestStateDoors(), log.append)
        self.assertTrue(chosen.durable)
        self.assertEqual(len(log), 1)
        self.assertIn(self.dispatch.DURABLE_TOKEN, log[0])

    def test_no_store_falls_back_to_memory_and_raises_the_alarm(self):
        log = []
        chosen = self.dispatch.resolve_quest_state_store(None, log.append)
        self.assertIsInstance(chosen, quest.InMemoryQuestStateStore)
        self.assertFalse(chosen.durable)
        self.assertEqual(len(log), 1)
        self.assertIn(qss.VOLATILE_TOKEN, log[0])
        self.assertNotIn(self.dispatch.DURABLE_TOKEN, log[0])

    def test_a_half_wired_store_names_the_missing_door_before_degrading(self):
        log = []
        store = without_doors(FakeQuestStateDoors(), "set_quest_counter")
        chosen = self.dispatch.resolve_quest_state_store(store, log.append)
        self.assertIsInstance(chosen, quest.InMemoryQuestStateStore)
        self.assertIn("set_quest_counter", log[0])

    def test_the_fallback_is_a_fresh_bucket_per_dispatch(self):
        """Two dispatches that both degrade must not read each other's
        progress: an accident that looks like persistence is worse than
        the absence of it, because it is only wrong sometimes."""
        first = self.dispatch.resolve_quest_state_store(None)
        second = self.dispatch.resolve_quest_state_store(None)
        first.set_quest_flag(7, 33, 2)
        self.assertIsNone(second.get_quest_flag(7, 33))

    def test_the_token_is_ascii(self):
        self.dispatch.DURABLE_TOKEN.encode("ascii")

    def test_passing_both_seams_is_refused_rather_than_ranked(self):
        """Silently preferring one would leave a caller believing progress
        is on a row when it is in process memory."""
        from pathlib import Path
        original = self.dispatch.script_path_for_quest
        self.dispatch.script_path_for_quest = lambda root, quest_id: Path("q.lua")
        try:
            with self.assertRaises(TypeError) as caught:
                self.dispatch.load_quest_script(
                    Path("."), 2170, character_id=7, log=[].append,
                    persistence=FakeQuestStateDoors(),
                    quest_store=quest.InMemoryQuestStateStore())
        finally:
            self.dispatch.script_path_for_quest = original
        self.assertIn("not both", str(caught.exception))

    def test_a_caller_that_names_neither_is_told_so_rather_than_left_quiet(self):
        """THE INVERSION OF THIS ROUND'S OWN FIRST DRAFT (pf-adversary F2).

        The draft resolved only when a caller named a store, so every
        caller that exists -- all of which name none -- kept the old
        silence, and the test that stood here PINNED that silence as
        correct while the docstring two files over claimed nothing was
        silent any more.  A default that is quiet is exactly the state a
        reader cannot tell apart from a persistent one, so the default is
        reported like any other store that cannot hold quest state.

        What is still guaranteed unchanged: ``LUA_QUEST_DISPATCH`` is
        still the FIRST line (two existing tests read it as ``calls[0]``),
        and the store the host ends up with is still a fresh private
        in-memory one.
        """
        from pathlib import Path
        seen = {}
        original_path = self.dispatch.script_path_for_quest
        self.dispatch.script_path_for_quest = lambda root, quest_id: Path("q.lua")

        def fake_load(path, log, **kwargs):
            seen.update(kwargs)
            return "host"

        from pirateforce_foundation import script_host
        original_load = script_host.load_script_file
        script_host.load_script_file = fake_load
        log = []
        try:
            self.dispatch.load_quest_script(
                Path("."), 2170, character_id=7, log=log.append)
        finally:
            script_host.load_script_file = original_load
            self.dispatch.script_path_for_quest = original_path
        self.assertIn("LUA_QUEST_DISPATCH", log[0])
        self.assertEqual(len(log), 2)
        self.assertIn(qss.VOLATILE_TOKEN, log[1])
        self.assertIsInstance(seen["quest_store"], quest.InMemoryQuestStateStore)

    def test_a_caller_that_injected_its_own_store_is_not_told_about_a_choice(self):
        """It already made the choice; a resolver line would describe a
        decision this function did not take."""
        from pathlib import Path
        seen = {}
        original_path = self.dispatch.script_path_for_quest
        self.dispatch.script_path_for_quest = lambda root, quest_id: Path("q.lua")

        def fake_load(path, log, **kwargs):
            seen.update(kwargs)
            return "host"

        from pirateforce_foundation import script_host
        original_load = script_host.load_script_file
        script_host.load_script_file = fake_load
        injected = quest.InMemoryQuestStateStore()
        log = []
        try:
            self.dispatch.load_quest_script(
                Path("."), 2170, character_id=7, log=log.append,
                quest_store=injected)
        finally:
            script_host.load_script_file = original_load
            self.dispatch.script_path_for_quest = original_path
        self.assertEqual(len(log), 1)
        self.assertIs(seen["quest_store"], injected)

    def test_the_durable_line_reports_what_the_store_says_about_itself(self):
        """``durable`` is READ by production code now, not only set
        (pf-adversary F5): an implementation whose attribute and whose
        behaviour disagree shows up in the console."""
        log = []
        self.dispatch.resolve_quest_state_store(FakeQuestStateDoors(), log.append)
        self.assertIn("durable=True", log[0])


if __name__ == "__main__":
    unittest.main()
