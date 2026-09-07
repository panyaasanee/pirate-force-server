"""WHICH mirror is broken, and IS IT STILL -- not just how many times.

Round `95aw54` built the counter COO-DECISION `pf_bridge/notes_to_chief/
20260907_1441_COO-DECISION-q1344-fail-soft-with-a-counter-LANE-Q.md`
item 3 asked for, and shipped two of pf-adversary's findings NAMED BUT
NOT FIXED.  This module is the pin for the fix:

* **D6** -- the count had no key and no way down.  Over the real 616-file
  corpus a reader saw `mirror_failures=616`, saw 616 again after
  repairing the file, and could answer neither which mirror broke nor
  whether it still was.
* **D3** -- `script_host.guard_mirrors` runs at `ScriptHost` construction,
  which reads exactly ONE of this package's four vendored mirrors
  (`api_spec.tsv`).  `message_catalog.tsv` and the two
  `quest_criteria_*.tsv` are read lazily inside namespace closures: a
  broken copy of any of them BUILT A HOST FINE and raised at call time,
  where the construction-time guard is blind.

EVERY TEST HERE RUNS WITHOUT `lupa`, on purpose and by construction: not
one of them builds a `ScriptHost`.  The counter is the half the decision
asked for and the half a cloud runner (no `lupa` wheel) can pin, so this
module needs no entry in `docs/PYTEST_SKIP_PINS.json` -- it declares no
precondition and skips nothing.
"""
import contextlib
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pirateforce_foundation import script_host
from pirateforce_foundation.lua_api import message, quest_criteria, spec, vendored
from pirateforce_foundation.lua_api.vendored import VendoredDataError

MISSING = Path("no_such_vendored_mirror_for_this_test.tsv")


@contextlib.contextmanager
def isolated_health():
    """Swap BOTH published names for a fresh counter, then restore.

    Both, not one.  `script_host` imports `MIRROR_HEALTH` by value, so
    `script_host.MIRROR_HEALTH` and `vendored.MIRROR_HEALTH` are two names
    for one object until somebody rebinds one of them -- and the two halves
    under test read different names: `guard_mirrors` reads the
    `script_host` global, the lazy loaders read the `vendored` one.  A test
    that swapped only one would leave the other half writing into the real
    process-wide object (pf-adversary D8, round `95aw54`, the same defect
    one door along).
    """
    fresh = vendored.MirrorHealth()
    host_original = script_host.MIRROR_HEALTH
    vendored_original = vendored.MIRROR_HEALTH
    script_host.MIRROR_HEALTH = fresh
    vendored.MIRROR_HEALTH = fresh
    try:
        yield fresh
    finally:
        script_host.MIRROR_HEALTH = host_original
        vendored.MIRROR_HEALTH = vendored_original


@contextlib.contextmanager
def broken_catalog():
    """Point the message catalog at a file that is not there, then back."""
    original = message._CATALOG_PATH
    message._CATALOG_PATH = MISSING
    message._CATALOG_CACHE = None
    try:
        yield
    finally:
        message._CATALOG_PATH = original
        message._CATALOG_CACHE = None


@contextlib.contextmanager
def broken_criteria(curve=True, rows=True):
    """Point either criteria mirror at a file that is not there."""
    curve_original = quest_criteria._CURVE_PATH
    rows_original = quest_criteria._ROWS_PATH
    if curve:
        quest_criteria._CURVE_PATH = MISSING
    if rows:
        quest_criteria._ROWS_PATH = MISSING
    quest_criteria.reset_caches()
    try:
        yield
    finally:
        quest_criteria._CURVE_PATH = curve_original
        quest_criteria._ROWS_PATH = rows_original
        quest_criteria.reset_caches()


def _clock_ticking_once_per_call(start=None):
    """A clock that advances one second every time it is read.

    Two stamps a test can tell apart without sleeping, which matters
    because the real stamp has one-second resolution.
    """
    moment = [start or datetime(2026, 9, 7, 10, 0, 0, tzinfo=timezone.utc)]

    def clock():
        now = moment[0]
        moment[0] = now + timedelta(seconds=1)
        return now

    return clock


class OneKeyPerMirrorTests(unittest.TestCase):
    """pf-adversary D6, first half: the count must name a mirror."""

    def test_a_failure_lands_under_its_own_key_and_no_other(self):
        health = vendored.MirrorHealth()
        health.record(VendoredDataError("api_spec.tsv is empty"),
                      vendored.MIRROR_API_SPEC)
        self.assertEqual(
            health.tally_for(vendored.MIRROR_API_SPEC).failures, 1)
        for other in (vendored.MIRROR_MESSAGE_CATALOG,
                      vendored.MIRROR_CRITERIA_CURVE,
                      vendored.MIRROR_CRITERIA_ROWS):
            self.assertEqual(health.tally_for(other).failures, 0, other)
            self.assertFalse(health.tally_for(other).broken_now, other)

    def test_a_key_never_read_reads_as_all_zero_not_as_healthy(self):
        # The distinction the docstring promises: absent means UNREAD.
        health = vendored.MirrorHealth()
        tally = health.tally_for(vendored.MIRROR_CRITERIA_ROWS)
        self.assertEqual(tally.failures, 0)
        self.assertIsNone(tally.last_ok_at)
        self.assertFalse(tally.broken_now)
        self.assertEqual(health.mirrors(), ())

    def test_the_roll_up_sums_and_names_every_broken_mirror(self):
        health = vendored.MirrorHealth()
        health.record(VendoredDataError("one"), vendored.MIRROR_CRITERIA_ROWS)
        health.record(VendoredDataError("two"), vendored.MIRROR_API_SPEC)
        health.record(VendoredDataError("three"), vendored.MIRROR_API_SPEC)
        roll_up = health.tally()
        self.assertIsNone(roll_up.mirror, "None is the roll-up shape")
        self.assertEqual(roll_up.failures, 3)
        self.assertEqual(roll_up.broken,
                         (vendored.MIRROR_API_SPEC,
                          vendored.MIRROR_CRITERIA_ROWS))
        self.assertTrue(roll_up.broken_now)

    def test_the_roll_up_quotes_the_most_recent_failure_within_one_second(self):
        # The stamp has one-second resolution, so ordering by stamp would
        # be a coin flip for two mirrors that break inside the same second.
        # A frozen clock makes that the ONLY case under test.
        moment = datetime(2026, 9, 7, 10, 0, 0, tzinfo=timezone.utc)
        health = vendored.MirrorHealth(clock=lambda: moment)
        health.record(VendoredDataError("the older one"),
                      vendored.MIRROR_API_SPEC)
        health.record(VendoredDataError("the newer one"),
                      vendored.MIRROR_MESSAGE_CATALOG)
        self.assertIn("the newer one", health.tally().last_error)
        self.assertEqual(health.tally().last_failed_at,
                         health.tally_for(vendored.MIRROR_API_SPEC)
                         .last_failed_at,
                         "both stamps are the same second, by construction")


class ARepairedMirrorSaysSoTests(unittest.TestCase):
    """pf-adversary D6, second half: a count that only rises is not state."""

    def test_a_successful_read_clears_broken_now_and_stamps_last_ok_at(self):
        health = vendored.MirrorHealth(clock=_clock_ticking_once_per_call())
        health.record(VendoredDataError("boom"), vendored.MIRROR_API_SPEC)
        self.assertTrue(health.tally_for(vendored.MIRROR_API_SPEC).broken_now)
        health.record_ok(vendored.MIRROR_API_SPEC)
        after = health.tally_for(vendored.MIRROR_API_SPEC)
        self.assertFalse(after.broken_now, "the state answers 'is it NOW'")
        self.assertIsNotNone(after.last_ok_at)
        self.assertNotEqual(after.last_ok_at, after.last_failed_at)

    def test_the_history_is_kept_when_the_state_clears(self):
        # Deliberate: `failures` is the history. A reader asking "has this
        # ever broken" must keep getting yes.
        health = vendored.MirrorHealth()
        health.record(VendoredDataError("boom"), vendored.MIRROR_API_SPEC)
        health.record_ok(vendored.MIRROR_API_SPEC)
        tally = health.tally_for(vendored.MIRROR_API_SPEC)
        self.assertEqual(tally.failures, 1)
        self.assertIsNotNone(tally.last_error)

    def test_the_roll_up_stops_calling_itself_broken_once_all_are_repaired(self):
        health = vendored.MirrorHealth()
        health.record(VendoredDataError("boom"), vendored.MIRROR_API_SPEC)
        health.record(VendoredDataError("boom"), vendored.MIRROR_CRITERIA_CURVE)
        self.assertTrue(health.tally().broken_now)
        health.record_ok(vendored.MIRROR_API_SPEC)
        self.assertEqual(health.tally().broken,
                         (vendored.MIRROR_CRITERIA_CURVE,),
                         "one repaired, one still broken")
        health.record_ok(vendored.MIRROR_CRITERIA_CURVE)
        self.assertFalse(health.tally().broken_now)
        self.assertEqual(health.tally().broken, ())
        self.assertEqual(health.tally().failures, 2, "history survives")

    def test_sixteen_threads_over_two_keys_lose_no_count(self):
        health = vendored.MirrorHealth()
        error = VendoredDataError("api_spec.tsv is empty")
        keys = (vendored.MIRROR_API_SPEC, vendored.MIRROR_CRITERIA_ROWS)
        threads = [threading.Thread(target=health.record,
                                    args=(error, keys[i % 2]))
                   for i in range(16)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(health.tally().failures, 16)
        self.assertEqual(health.tally_for(keys[0]).failures, 8)
        self.assertEqual(health.tally_for(keys[1]).failures, 8)


class TheLazilyReadMirrorsAreCountedNowTests(unittest.TestCase):
    """pf-adversary D3: three of four mirrors used to break unseen.

    Each test here MEASURES the gap the finding named, by breaking a real
    mirror through its real loader -- never by calling `record` directly.
    """

    def test_a_broken_message_catalog_is_counted_at_call_time(self):
        with isolated_health() as health, broken_catalog():
            with self.assertRaises(message.MessageCatalogError):
                message.catalog()
        tally = health.tally_for(vendored.MIRROR_MESSAGE_CATALOG)
        self.assertEqual(tally.failures, 1)
        self.assertTrue(tally.broken_now)
        self.assertIn(MISSING.name, tally.last_error)
        self.assertEqual(health.tally().broken,
                         (vendored.MIRROR_MESSAGE_CATALOG,))

    def test_a_broken_criteria_curve_is_counted_under_its_own_key(self):
        with isolated_health() as health, broken_criteria(rows=False):
            with self.assertRaises(VendoredDataError):
                quest_criteria.load_curve()
        self.assertEqual(
            health.tally_for(vendored.MIRROR_CRITERIA_CURVE).failures, 1)
        self.assertEqual(
            health.tally_for(vendored.MIRROR_CRITERIA_ROWS).failures, 0)

    def test_a_broken_criteria_row_table_is_counted_under_its_own_key(self):
        with isolated_health() as health, broken_criteria(curve=False):
            with self.assertRaises(VendoredDataError):
                quest_criteria.load_reward_rows()
        self.assertEqual(
            health.tally_for(vendored.MIRROR_CRITERIA_ROWS).failures, 1)
        self.assertEqual(
            health.tally_for(vendored.MIRROR_CRITERIA_CURVE).failures, 0)

    def test_the_shipped_mirrors_read_clean_and_say_so(self):
        # The success half, over the files this repository actually ships.
        with isolated_health() as health:
            quest_criteria.reset_caches()
            message._CATALOG_CACHE = None
            self.addCleanup(quest_criteria.reset_caches)
            quest_criteria.load_curve()
            quest_criteria.load_reward_rows()
            message.catalog()
        for key in (vendored.MIRROR_MESSAGE_CATALOG,
                    vendored.MIRROR_CRITERIA_CURVE,
                    vendored.MIRROR_CRITERIA_ROWS):
            tally = health.tally_for(key)
            self.assertIsNotNone(tally.last_ok_at, key)
            self.assertFalse(tally.broken_now, key)
        self.assertFalse(health.tally().broken_now)

    def test_the_failure_still_travels_unchanged_to_the_caller(self):
        # `read_mirror` records and RE-RAISES. Swallowing it here would be
        # a behaviour change this lane has no decision for: the callers
        # above already turn a VendoredDataError into a LUA_HOST line.
        with isolated_health(), broken_criteria():
            with self.assertRaises(quest_criteria.QuestCriteriaError):
                quest_criteria.load_curve()

    def test_an_error_that_is_not_a_broken_mirror_is_not_counted(self):
        health = vendored.MirrorHealth()

        def read():
            raise ZeroDivisionError("a defect in this lane, not in a file")

        with self.assertRaises(ZeroDivisionError):
            vendored.read_mirror(vendored.MIRROR_API_SPEC, read, health)
        self.assertEqual(health.tally().failures, 0)
        self.assertEqual(health.mirrors(), (),
                         "and no success was recorded either")


class TheConstructionGuardKeepsItsHalfTests(unittest.TestCase):
    """`guard_mirrors` still owns `api_spec.tsv`, now under a key."""

    @contextlib.contextmanager
    def broken_census(self):
        original = spec._SPEC_PATH
        spec._SPEC_PATH = MISSING
        spec._CACHE.clear()
        try:
            yield
        finally:
            spec._SPEC_PATH = original
            spec._CACHE.clear()

    def test_a_broken_census_is_recorded_under_the_api_spec_key(self):
        health = vendored.MirrorHealth()
        with self.broken_census():
            script_host.guard_mirrors(lambda: spec.NAMESPACE_METHODS,
                                      lambda _line: None, health)
        self.assertEqual(
            health.tally_for(vendored.MIRROR_API_SPEC).failures, 1)
        self.assertEqual(health.tally().broken,
                         (vendored.MIRROR_API_SPEC,))

    def test_a_healthy_build_records_a_success_so_a_repair_shows(self):
        health = vendored.MirrorHealth()
        with self.broken_census():
            script_host.guard_mirrors(lambda: spec.NAMESPACE_METHODS,
                                      lambda _line: None, health)
        built, failure = script_host.guard_mirrors(
            lambda: spec.NAMESPACE_METHODS, lambda _line: None, health)
        self.assertIsNotNone(built)
        self.assertIsNone(failure)
        tally = health.tally_for(vendored.MIRROR_API_SPEC)
        self.assertFalse(tally.broken_now, "the repair is visible")
        self.assertEqual(tally.failures, 1, "and the history is not erased")

    def test_a_build_that_raised_records_no_success(self):
        health = vendored.MirrorHealth()
        with self.broken_census():
            script_host.guard_mirrors(lambda: spec.NAMESPACE_METHODS,
                                      lambda _line: None, health)
        self.assertIsNone(
            health.tally_for(vendored.MIRROR_API_SPEC).last_ok_at)

    def test_the_degraded_line_still_carries_the_original_field_names(self):
        # A reader's grep and `tests/test_script_host_mirror_health.py`
        # both already know these three. The four D6 answers are appended,
        # not mixed in.
        health = vendored.MirrorHealth()
        lines = []
        with self.broken_census():
            script_host.guard_mirrors(lambda: spec.NAMESPACE_METHODS,
                                      lines.append, health)
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith("LUA_MIRROR_DEGRADED "), lines[0])
        for field in ("mirror_failures=1", 'last_failed_at="',
                      'last_error="', 'mirror="api_spec"', "broken_now=true",
                      'broken="api_spec"'):
            self.assertIn(field, lines[0])
        lines[0].encode("ascii")


class TheTwoPublishedNamesAreOneObjectTests(unittest.TestCase):
    """The seam this move created, pinned rather than left to be found."""

    def test_script_host_re_exports_the_very_object_vendored_publishes(self):
        # Not "an equal one": the construction guard reads the script_host
        # global and the lazy loaders read the vendored one, so if these
        # ever stop being the same object a reader gets half the picture
        # from each and no error anywhere.
        self.assertIs(script_host.MIRROR_HEALTH, vendored.MIRROR_HEALTH)
        self.assertIs(script_host.MirrorHealth, vendored.MirrorHealth)
        self.assertIs(script_host.MirrorFailureTally,
                      vendored.MirrorFailureTally)

    def test_every_shipped_mirror_has_a_key_and_the_keys_are_unique(self):
        # NAMES, NOT A COUNT (pf-adversary D10, round `h20x7g`): the first
        # version compared `len(shipped)` with `len(KNOWN_MIRRORS)`, which
        # `("a", "b", "c", "d")` passes. A count proves a fifth file was
        # noticed; it does not prove the four keys mean anything. Each key
        # must be the stem of a file this package actually ships.
        self.assertEqual(len(set(vendored.KNOWN_MIRRORS)),
                         len(vendored.KNOWN_MIRRORS))
        shipped = {p.stem for p in
                   Path(vendored.__file__).parent.glob("*.tsv")}
        # `quest_criteria_curve.tsv` -> key `criteria_curve`: the key drops
        # the package-name prefix the filename carries, so the comparison
        # is over stems with that prefix removed.
        stems = {stem[len("quest_"):] if stem.startswith("quest_") else stem
                 for stem in shipped}
        self.assertEqual(set(vendored.KNOWN_MIRRORS), stems,
                         sorted(shipped))

    def test_a_class_name_outside_ascii_is_escaped_in_both_halves(self):
        health = vendored.MirrorHealth()
        # Written as escapes so this FILE stays ASCII (AGENTS.md section 7)
        # while the values it records are not.
        error_type = type("\u9328Error", (VendoredDataError,), {})
        health.record(error_type("boom \u0e1e\u0e31\u0e07"),
                      vendored.MIRROR_API_SPEC)
        health.tally().log_fields().encode("cp874")
        health.tally_for(vendored.MIRROR_API_SPEC).log_fields().encode("ascii")


class WhatThisStateCannotSeeTests(unittest.TestCase):
    """pf-adversary D1/D4/D7, round `h20x7g` -- pinned, not just written up.

    Two of these pin a LIMIT rather than a capability. A limit that only
    lives in a docstring is a limit the next round deletes by accident.
    """

    def test_a_deleted_mirror_cannot_flip_broken_now_once_the_cache_is_warm(self):
        # THE FINDING, AS A TEST. Not a bug being hidden: the design's
        # honest boundary, pinned so that a future round which claims
        # `broken_now` is a liveness signal has to delete this test first.
        with isolated_health() as health:
            quest_criteria.reset_caches()
            self.addCleanup(quest_criteria.reset_caches)
            quest_criteria.load_curve()
            self.assertFalse(
                health.tally_for(vendored.MIRROR_CRITERIA_CURVE).broken_now)
            stamp = health.tally_for(vendored.MIRROR_CRITERIA_CURVE).last_ok_at
            # The file goes away. Nothing clears the cache, exactly as
            # production never does.
            original = quest_criteria._CURVE_PATH
            quest_criteria._CURVE_PATH = MISSING
            self.addCleanup(setattr, quest_criteria, "_CURVE_PATH", original)
            for _ in range(3):
                quest_criteria.load_curve()
            after = health.tally_for(vendored.MIRROR_CRITERIA_CURVE)
        self.assertFalse(after.broken_now,
                         "measured, and this is the LIMIT: a warm cache is "
                         "never re-read, so healthy -> broken cannot be seen")
        self.assertEqual(after.last_ok_at, stamp,
                         "and no later read stamps a fresher success either")

    def test_the_roll_up_quotes_a_mirror_that_is_still_broken(self):
        # pf-adversary D4: ordering by sequence alone produced a line that
        # named message_catalog in `broken=` and quoted an api_spec error
        # that had already been repaired.
        health = vendored.MirrorHealth()
        health.record(VendoredDataError("message_catalog.tsv is missing"),
                      vendored.MIRROR_MESSAGE_CATALOG)
        health.record(VendoredDataError("api_spec.tsv is missing"),
                      vendored.MIRROR_API_SPEC)
        health.record_ok(vendored.MIRROR_API_SPEC)
        roll_up = health.tally()
        self.assertEqual(roll_up.broken, (vendored.MIRROR_MESSAGE_CATALOG,))
        self.assertIn("message_catalog.tsv", roll_up.last_error)
        self.assertNotIn("api_spec.tsv", roll_up.last_error)

    def test_with_nothing_broken_the_roll_up_still_carries_the_history(self):
        # The other side of the same fix: once every mirror is repaired,
        # the newest failure of all is the right answer, because `broken`
        # is empty and the line reads as history.
        health = vendored.MirrorHealth()
        health.record(VendoredDataError("api_spec.tsv is missing"),
                      vendored.MIRROR_API_SPEC)
        health.record_ok(vendored.MIRROR_API_SPEC)
        roll_up = health.tally()
        self.assertEqual(roll_up.broken, ())
        self.assertFalse(roll_up.broken_now)
        self.assertIn("api_spec.tsv", roll_up.last_error)

    def test_a_mirror_key_outside_cp874_does_not_kill_the_console(self):
        # pf-adversary D7: the key was the third piece of caller-supplied
        # text on this line and the one nothing escaped.
        health = vendored.MirrorHealth()
        health.record(VendoredDataError("boom"), "caf\u00e9_mirror")
        health.tally().log_fields().encode("cp874")
        health.tally_for("caf\u00e9_mirror").log_fields().encode("ascii")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
