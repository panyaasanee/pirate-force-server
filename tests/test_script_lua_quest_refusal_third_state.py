"""LANE-Q: a refused quest-state write is a THIRD state, not "not started".

WHAT THIS FILE PINS, in the player's words: a daily quest whose store is
write-locked takes the player's items ONCE and then refuses, instead of
taking them again every time the player clicks the NPC.

The failure it pins against was measured on the game's own shipped scripts
by pf-adversary in round ``7qw2tr`` (findings F1/F4/F6).  ``pf_bridge/
gamedata/lua/Quest/q_day_business.lua`` reads, in that order:

    function Accept_Check()
        if( Quest.CanReportDailyQuest()) and ...            -- the gate
    function Report_Run()
        Player.RemoveItem(Quest.Var2,Quest.Var3)            -- the charge
        Quest.ReportDailyQuest()                            -- the record

so the charge happens BEFORE the record.  When the record is refused and
the refusal answers with the same ``None``/``0`` a never-started quest
answers with, the gate says yes again and the charge runs again.

Every test below drives that exact sequence through the real ``Quest``
namespace (``quest.build_namespace``), not through a paraphrase of it.
"""
import threading
import unittest

from pirateforce_foundation.lua_api import dispatch
from pirateforce_foundation.lua_api import quest
from pirateforce_foundation.lua_api import quest_state_signal as qs_signal
from pirateforce_foundation.lua_api import quest_state_store as qss


class _CounterRow(object):
    def __init__(self, counter_value):
        self.counter_value = counter_value


class _FlagRow(object):
    def __init__(self, flag_value):
        self.flag_value = flag_value


class WriteLockedStore(object):
    """LANE-DB's five doors, with the writes failing the way a busy
    SQLite file fails.

    ``store.WriteLockTimeout`` subclasses ``sqlite3.OperationalError``
    (``store.py``'s own definition), which is the family the adapter
    catches; raising the base class here keeps this file free of an import
    of ``store`` and still exercises the same branch.
    """

    def __init__(self):
        self.flags = {}
        self.counters = {}
        self.writes_refused = 0
        self.reads = 0

    # -- reads keep working: this is the hard case ---------------------
    def get_quest_flag(self, character_id, quest_id):
        self.reads += 1
        value = self.flags.get((character_id, quest_id))
        return None if value is None else _FlagRow(value)

    def get_quest_counter(self, character_id, quest_id, counter_name):
        self.reads += 1
        value = self.counters.get((character_id, quest_id, counter_name))
        return None if value is None else _CounterRow(value)

    # -- writes are the thing that is broken ---------------------------
    def set_quest_flag(self, character_id, quest_id, flag_value):
        self.writes_refused += 1
        raise __import__("sqlite3").OperationalError("database is locked")

    def set_quest_counter(self, character_id, quest_id, counter_name, value):
        self.writes_refused += 1
        raise __import__("sqlite3").OperationalError("database is locked")

    def increment_quest_counter(self, character_id, quest_id, counter_name,
                                delta=1):
        self.writes_refused += 1
        raise __import__("sqlite3").OperationalError("database is locked")


class HealingStore(WriteLockedStore):
    """Write-locked for ``fail_writes`` writes, then healthy.

    Proves the poison CLEARS: a transient lock must not lock a character
    out of a quest forever.
    """

    def __init__(self, fail_writes=1):
        WriteLockedStore.__init__(self)
        self.remaining = fail_writes

    def set_quest_counter(self, character_id, quest_id, counter_name, value):
        if self.remaining > 0:
            self.remaining -= 1
            return WriteLockedStore.set_quest_counter(
                self, character_id, quest_id, counter_name, value)
        self.counters[(character_id, quest_id, counter_name)] = value
        return _CounterRow(value)

    def set_quest_flag(self, character_id, quest_id, flag_value):
        if self.remaining > 0:
            self.remaining -= 1
            return WriteLockedStore.set_quest_flag(
                self, character_id, quest_id, flag_value)
        self.flags[(character_id, quest_id)] = flag_value
        return _FlagRow(flag_value)


def _namespace(store, log, character_id=7, quest_id=33):
    """The real ``Quest`` global, every method REAL, over ``store``."""
    return quest.build_namespace(
        quest.REAL_METHODS, log.append,
        context=quest.QuestContext(character_id=character_id,
                                   quest_id=quest_id),
        store=store)


class TheChargeThatRanFourTimesTests(unittest.TestCase):
    """``q_day_business.lua``'s own order of operations, replayed."""

    def setUp(self):
        self.log = []
        self.store = WriteLockedStore()
        self.adapter = qss.StoreBackedQuestStateStore(self.store,
                                                      self.log.append)
        self.ns = _namespace(self.adapter, self.log)

    def _report_run(self):
        """``Report_Run``: charge, then record.  Returns the charge amount
        the script would have passed to ``Player.RemoveItem``."""
        charge = (self.ns["Var2"], self.ns["Var3"])
        self.ns["ReportDailyQuest"]()
        return charge

    def test_the_gate_closes_after_the_record_is_refused(self):
        """FOUR CLICKS, ONE CHARGE.

        Before round `7cf5ak` this loop charged on every pass: the refused
        write answered 0, the next ``CanReportDailyQuest`` read a missing
        stamp as "not reported today", and said yes again.
        """
        self.assertTrue(self.ns["CanReportDailyQuest"]())
        self._report_run()

        for _ in range(3):
            self.assertFalse(
                self.ns["CanReportDailyQuest"](),
                "the gate must stay shut while the report is unrecorded")

    def test_the_amount_cells_are_left_alone_by_a_poisoned_row(self):
        """THE OPPOSITE OF WHAT THIS TEST USED TO ASSERT, ON PURPOSE.

        Its first version pinned "a poisoned quest answers ``VarN`` with
        the stub default" as the requirement.  pf-adversary (round
        ``7cf5ak``, A3) measured what that does to the shipped corpus:
        ``Quest.VarN == 0`` is the "this quest has no prerequisite" idiom
        at 299 call sites across 302 scripts, including
        ``q_day_business.lua:12`` and the level cap at ``:14``.  Zeroing
        the cell did not stall those gates, it OPENED them -- a fail-open
        introduced by the fail-closed mechanism, in the same script.

        So the cells keep answering the table, and the refusal is enforced
        at the decisions instead (the gate above, and ``_pay_criteria``).
        """
        before = (self.ns["Var2"], self.ns["Var3"], self.ns["RewardItem1"])
        self.ns["ReportDailyQuest"]()
        after = (self.ns["Var2"], self.ns["Var3"], self.ns["RewardItem1"])
        self.assertEqual(before, after,
                         "a poisoned row must not rewrite a table cell")
        self.assertNotEqual(
            after[2], quest.STUB_DEFAULT,
            "this quest has a reward row; if it did not, the test proves "
            "nothing about the gate having been removed")

    def test_the_console_names_the_reason_not_just_the_refusal(self):
        self.ns["ReportDailyQuest"]()
        self.ns["CanReportDailyQuest"]()
        unreadable = [line for line in self.log
                      if line.startswith(qs_signal.UNREADABLE_TOKEN)]
        self.assertTrue(unreadable, "a refused gate must be visible")
        self.assertTrue(any("reason=write-locked" in line
                            for line in unreadable))
        self.assertTrue(any("Quest.CanReportDailyQuest" in line
                            for line in unreadable))

    def test_every_line_this_round_adds_is_ascii(self):
        """The bridge console is cp874; a non-ASCII byte kills the tool."""
        self.ns["ReportDailyQuest"]()
        self.ns["CanReportDailyQuest"]()
        self.ns["Var2"]
        for line in self.log:
            line.encode("ascii")


class TheLedgerIsAskedAboutTheRightQuestTests(unittest.TestCase):
    """``Quest.GetQuestFlag(id)`` asks about a quest the SCRIPT chose.

    ``q_day_business.lua``'s ``Accept_Check`` reads
    ``Quest.GetQuestFlag(Quest.Var1) == Quest.Finish`` -- a PREREQUISITE
    quest, not the running one.  Consulting the ledger under the running
    quest's id would refuse the wrong pair in one direction and miss a
    poisoned one in the other.
    """

    def setUp(self):
        self.log = []
        self.store = WriteLockedStore()
        self.store.flags[(7, 99)] = quest.QUEST_FINISH
        self.adapter = qss.StoreBackedQuestStateStore(self.store,
                                                      self.log.append)

    def test_a_poisoned_prerequisite_is_not_read_as_unfinished(self):
        self.adapter.set_quest_flag(7, 99, quest.QUEST_NONE)   # refused
        ns = _namespace(self.adapter, self.log, character_id=7, quest_id=33)
        self.assertEqual(ns["GetQuestFlag"](99), quest.QUEST_NONE)
        self.assertTrue(any("quest=99" in line and
                            line.startswith(qs_signal.UNREADABLE_TOKEN)
                            for line in self.log))

    def test_a_clean_prerequisite_is_still_readable_from_a_poisoned_quest(self):
        """The running quest is poisoned; the prerequisite is not.

        Refusing this read too would be the mirror mistake, and it would
        make one lost write hide every other quest a script asks about.
        """
        ns = _namespace(self.adapter, self.log, character_id=7, quest_id=33)
        ns["SetFlag"](quest.QUEST_ACTIVE)                      # refused -> 33
        self.assertEqual(ns["GetQuestFlag"](99), quest.QUEST_FINISH)


class TheRefusalIsNotForeverTests(unittest.TestCase):
    """A transient lock must not become a permanent lockout."""

    def test_a_write_to_another_row_does_not_clear_this_one(self):
        """``q_day_business.lua`` LINES 59 AND 63, IN THAT ORDER.

        Its first version asserted the opposite and pinned the bug as the
        requirement (pf-adversary, round ``7cf5ak``, A4).  In the shipped
        script the refused ``Quest.ReportDailyQuest()`` at line 59 is
        followed four lines later, in the same run, by a ``SetFlag`` that
        SUCCEEDS.  Keyed to the pair, that success cleared the poison with
        the daily stamp still missing from disk, so the gate was open
        again before any click could read it.  The poison is keyed to the
        ROW now: the flag row is repaired, the counter row is not.
        """
        log = []
        store = HealingStore(fail_writes=1)
        adapter = qss.StoreBackedQuestStateStore(store, log.append)
        ns = _namespace(adapter, log)

        ns["ReportDailyQuest"]()                       # line 59: refused
        self.assertFalse(ns["CanReportDailyQuest"]())  # shut

        self.assertEqual(ns["SetFlag"](quest.QUEST_ACTIVE),
                         quest.QUEST_ACTIVE)           # line 63: lands
        self.assertFalse(
            ns["CanReportDailyQuest"](),
            "a flag write must not vouch for a counter row it never wrote")

    def test_a_write_to_the_same_row_does_clear_it(self):
        """The other half: this is a refusal, not a blacklist."""
        log = []
        store = HealingStore(fail_writes=1)
        adapter = qss.StoreBackedQuestStateStore(store, log.append)
        ns = _namespace(adapter, log)

        ns["ReportDailyQuest"]()                       # refused, poisons
        self.assertFalse(ns["CanReportDailyQuest"]())
        ns["ReportDailyQuest"]()                       # the store has healed
        self.assertFalse(
            ns["CanReportDailyQuest"](),
            "the stamp is now on record for today, so the daily gate is "
            "shut because it was REPORTED, not because it is unreadable")
        self.assertEqual(
            adapter.refusals.rows(), (),
            "the row that was repaired must be forgotten")

    def test_only_the_pair_that_lost_a_write_is_poisoned(self):
        log = []
        store = WriteLockedStore()
        adapter = qss.StoreBackedQuestStateStore(store, log.append)

        _namespace(adapter, log, character_id=7, quest_id=33)[
            "ReportDailyQuest"]()

        other_quest = _namespace(adapter, log, character_id=7, quest_id=34)
        other_player = _namespace(adapter, log, character_id=8, quest_id=33)
        self.assertTrue(other_quest["CanReportDailyQuest"]())
        self.assertTrue(other_player["CanReportDailyQuest"]())


class TheThirdStateIsNotADisguisedZeroTests(unittest.TestCase):
    """``Refused`` must not change any number it rides on."""

    def test_a_refusal_is_the_number_it_replaces(self):
        self.assertEqual(qs_signal.refused("write-locked"), 0)
        self.assertEqual(int(qs_signal.refused("write-locked")), 0)
        self.assertEqual(qs_signal.refused("write-locked") + 1, 1)
        self.assertFalse(bool(qs_signal.refused("write-locked")))
        self.assertEqual(qs_signal.refused("cap-characters", 5), 5)

    def test_a_real_zero_is_not_a_refusal(self):
        """A quest flag of ``QUEST_NONE`` and a counter at 0 are FACTS."""
        self.assertFalse(qs_signal.is_refused(0))
        self.assertFalse(qs_signal.is_refused(None))
        self.assertIsNone(qs_signal.reason_of(0))

    def test_a_refusal_must_name_a_reason(self):
        self.assertRaises(ValueError, qs_signal.refused, "")
        self.assertRaises(ValueError, qs_signal.refused, None)

    def test_the_in_memory_store_marks_its_cap_refusals_too(self):
        """A cap refusal is a lost write exactly as a locked row is.

        The value it answers with is unchanged (the row still on record);
        what is added is that it can be told apart from a stored number.
        """
        store = quest.InMemoryQuestStateStore(characters=1)
        self.assertEqual(store.set_quest_flag(1, 33, quest.QUEST_ACTIVE),
                         quest.QUEST_ACTIVE)
        refused = store.set_quest_flag(2, 33, quest.QUEST_ACTIVE)
        self.assertTrue(qs_signal.is_refused(refused))
        self.assertEqual(int(refused), quest.STUB_DEFAULT)
        self.assertEqual(store.refusals.unreadable(2, 33), "cap-characters")
        self.assertIsNone(store.refusals.unreadable(1, 33))

    def test_a_store_with_no_ledger_is_unchanged(self):
        """LANE-A's own fakes, and any store another lane wires in."""

        class Bare(object):
            def get_quest_flag(self, character_id, quest_id):
                return quest.QUEST_ACTIVE

        self.assertIsNone(
            qs_signal.unreadable_reason(Bare(), 7, 33))
        self.assertTrue(quest.is_quest_accepted(Bare(), 7, 33))


class TheCrossLaneReadsRefuseTooTests(unittest.TestCase):
    """LANE-A gates NPC visibility on these two."""

    def setUp(self):
        self.log = []
        self.store = WriteLockedStore()
        self.store.flags[(7, 33)] = quest.QUEST_ACTIVE
        self.adapter = qss.StoreBackedQuestStateStore(self.store,
                                                      self.log.append)

    def test_a_stale_active_flag_does_not_show_the_npc(self):
        """The row says ACTIVE; the ``SetFlag(Finish)`` that would have
        moved it was refused.  Showing the quest-giver on that would put
        an NPC in front of a player who has already finished the quest."""
        self.assertTrue(quest.is_quest_accepted(self.adapter, 7, 33))
        self.adapter.set_quest_flag(7, 33, quest.QUEST_FINISH)   # refused
        self.assertFalse(quest.is_quest_accepted(self.adapter, 7, 33))
        self.assertFalse(quest.is_quest_reported(self.adapter, 7, 33))


class TheLedgerHoldsUnderConcurrencyTests(unittest.TestCase):
    """Two mobs of one template dying in the same tick reach this from two
    threads."""

    def test_concurrent_records_and_clears_do_not_corrupt_the_ledger(self):
        ledger = qs_signal.RefusalLedger()
        errors = []

        def churn(pair):
            try:
                for _ in range(200):
                    ledger.record(pair, 33, "write-locked")
                    ledger.unreadable(pair, 33)
                    ledger.clear(pair, 33)
            except Exception as exc:            # pragma: no cover - a fail
                errors.append(exc)

        threads = [threading.Thread(target=churn, args=(n,))
                   for n in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(ledger.pairs(), ())

    def test_the_ledger_refuses_new_pairs_rather_than_forgetting_old_ones(self):
        """Evicting a pair would turn "unreadable" back into "not
        started" -- the exact confusion this module exists to end -- so a
        full ledger keeps what it has and says it is saturated."""
        ledger = qs_signal.RefusalLedger(cap=2)
        ledger.record(1, 33, "write-locked")
        ledger.record(2, 33, "write-locked")
        ledger.record(3, 33, "write-locked")
        self.assertEqual(ledger.unreadable(1, 33), "write-locked")
        self.assertEqual(ledger.unreadable(2, 33), "write-locked")
        self.assertIsNone(ledger.unreadable(3, 33))
        self.assertTrue(ledger.saturated())

    def test_the_first_reason_is_the_one_kept(self):
        ledger = qs_signal.RefusalLedger()
        ledger.record(1, 33, "write-locked")
        ledger.record(1, 33, "no-such-character")
        self.assertEqual(ledger.unreadable(1, 33), "write-locked")


if __name__ == "__main__":       # pragma: no cover
    unittest.main()


class TheMemoryOutlivesTheDispatchTests(unittest.TestCase):
    """A1: the click that charges and the click that would charge again
    are DIFFERENT dispatches.

    ``dispatch.load_quest_script()`` builds a fresh
    ``StoreBackedQuestStateStore`` on every run, so a ledger owned by the
    adapter was empty by the time the second click asked.  pf-adversary
    (round `7cf5ak`, A1) measured it and called the whole mechanism
    theatre, correctly: a memory shorter than the fact it stands for
    cannot gate anything.  Every test here crosses that boundary by
    building the adapter TWICE over one backing store, the way the
    resolver does.
    """

    def setUp(self):
        self.log = []
        self.store = WriteLockedStore()

    def _dispatch(self):
        """One `load_quest_script`-worth of adapter, through the same
        resolver the loader calls -- not a hand-built one."""
        adapter = dispatch.resolve_quest_state_store(self.store,
                                                     self.log.append)
        return adapter, _namespace(adapter, self.log)

    def test_the_resolver_really_does_build_a_new_adapter_each_time(self):
        """If this ever stops being true the tests below prove nothing."""
        first, _ = self._dispatch()
        second, _ = self._dispatch()
        self.assertIsNot(first, second)
        self.assertIsInstance(first, qss.StoreBackedQuestStateStore)

    def test_the_gate_stays_shut_on_the_next_dispatch(self):
        """FOUR CLICKS, FOUR DISPATCHES, ONE CHARGE."""
        _, first = self._dispatch()
        self.assertTrue(first["CanReportDailyQuest"]())
        first["ReportDailyQuest"]()                     # refused

        for _ in range(3):
            _, later = self._dispatch()
            self.assertFalse(
                later["CanReportDailyQuest"](),
                "a new dispatch must not forget the unrecorded report")

    def test_two_adapters_over_one_store_share_one_ledger(self):
        first, _ = self._dispatch()
        second, _ = self._dispatch()
        self.assertIs(first.refusals, second.refusals)
        self.assertTrue(qs_signal.ledger_is_shared(self.store))

    def test_two_adapters_over_different_stores_do_not(self):
        first = qss.StoreBackedQuestStateStore(WriteLockedStore())
        second = qss.StoreBackedQuestStateStore(WriteLockedStore())
        self.assertIsNot(first.refusals, second.refusals)

    def test_the_ledger_dies_with_the_store_it_describes(self):
        """Not a leak: the side table holds the store weakly."""
        import gc
        store = WriteLockedStore()
        qss.StoreBackedQuestStateStore(store)
        self.assertTrue(qs_signal.ledger_is_shared(store))
        del store
        gc.collect()
        self.assertEqual(len(qs_signal._LEDGERS), 0)


class TheDefaultContextIsNotAPoisonedCharacterTests(unittest.TestCase):
    """A6: ``character_id < 1`` is the inert default context, not a
    character whose progress went missing.

    Recording it left a HEALTHY store poisoned forever -- no write for
    character 0 will ever be made, so nothing could clear it -- which made
    ``LUA_QUEST_STATE_UNREADABLE`` on the console mean nothing.
    """

    def test_a_write_for_character_zero_poisons_nothing(self):
        log = []
        adapter = qss.StoreBackedQuestStateStore(HealingStore(fail_writes=0),
                                                 log.append)
        answer = adapter.set_quest_flag(0, 33, quest.QUEST_ACTIVE)
        self.assertTrue(qs_signal.is_refused(answer))
        self.assertEqual(qs_signal.reason_of(answer), "no-character")
        self.assertEqual(adapter.refusals.rows(), ())

    def test_a_healthy_store_answers_a_real_character_normally(self):
        log = []
        store = HealingStore(fail_writes=0)
        adapter = qss.StoreBackedQuestStateStore(store, log.append)
        adapter.set_quest_flag(0, 33, quest.QUEST_ACTIVE)     # the default
        ns = _namespace(adapter, log, character_id=7, quest_id=33)
        self.assertTrue(
            ns["CanReportDailyQuest"](),
            "character 7 must not inherit character 0's refusal")


class TheLedgerKeysRowsNotPairsTests(unittest.TestCase):
    """A2, at the ledger itself."""

    def setUp(self):
        self.ledger = qs_signal.RefusalLedger()

    def test_two_counters_of_one_quest_are_two_facts(self):
        self.ledger.record(7, 33, "write-locked",
                           qs_signal.COUNTER_ROW, "mob:900")
        self.ledger.record(7, 33, "write-locked",
                           qs_signal.COUNTER_ROW, "mob:901")
        self.ledger.clear(7, 33, qs_signal.COUNTER_ROW, "mob:900")
        self.assertIsNone(self.ledger.unreadable(
            7, 33, qs_signal.COUNTER_ROW, "mob:900"))
        self.assertEqual(self.ledger.unreadable(
            7, 33, qs_signal.COUNTER_ROW, "mob:901"), "write-locked")

    def test_the_flag_row_has_no_name_of_its_own(self):
        self.ledger.record(7, 33, "write-locked", qs_signal.FLAG_ROW, "x")
        self.assertEqual(
            self.ledger.unreadable(7, 33, qs_signal.FLAG_ROW), "write-locked",
            "a caller must not be able to poison one flag row and clear "
            "another by passing a different name")

    def test_asking_about_the_quest_sees_any_poisoned_row(self):
        self.ledger.record(7, 33, "write-locked",
                           qs_signal.COUNTER_ROW, "mob:900")
        self.assertEqual(self.ledger.unreadable(7, 33), "write-locked")
        self.assertIsNone(self.ledger.unreadable(
            7, 33, qs_signal.FLAG_ROW))

    def test_an_unknown_kind_is_refused_not_silently_accepted(self):
        with self.assertRaises(ValueError):
            self.ledger.record(7, 33, "write-locked", "rumour", "")
