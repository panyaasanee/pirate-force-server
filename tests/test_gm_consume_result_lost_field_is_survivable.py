"""A `ConsumeResult` that lost a field must cost the OVERRIDE, not the port.

Round `npo898`, consuming chief's reply of 2026-08-29T19:24+07:00 to
`CORE-REQUEST-GM-037`, item 1: "loud to whom?".

WHAT WAS MEASURED THERE (by pf-adversary, round `nbulzb`, and re-read from
the source in this round before writing a line of this file):

* `runtime.py` reads `override_result.cause` outside the `try: print(...)
  except Exception: pass` guard -- this lane demanded that, and it stands;
* that read sits INSIDE `except (ValueError, OSError, TypeError)`;
* a bare `AttributeError` is in neither net, so it unwinds the game
  listener thread (`pf_login_game_server_v141.py:7440` has no `except`).
  The process keeps the login port and loses the game port.  A supervisor
  sees a live process; a tester sees a client that connects and then never
  enters; the console says nothing.

So "loud" had a consumer nobody had named, and the honest answer is that a
dead game port is not loudness -- it is the quietest failure this lane can
produce, because the one artifact an operator watches (the console) stays
empty while the server looks healthy.

THE ANSWER THIS LANE SHIPS: the consumer of the loudness is the events row
`gm_login_scene_override_lookup_failed_ConsumeResultMisuse` and a red CI.
`ConsumeResultMisuse` inherits BOTH `AttributeError` (so nothing that
catches one changes behaviour, `copy.deepcopy`'s instance-level
`getattr(x, "__deepcopy__", None)` included) and `TypeError` (so the net
`runtime.py` ALREADY has catches it, with no change to chief's file).

WHAT IS NOT CLAIMED.  Nothing here is client-observable: no byte of any of
this reaches a client, and the paths driven below are in-repo regression
drills -- at HEAD a real `ConsumeResult` cannot exist without a cause.
This file is wire/console-side only.  The end-to-end half of the same
property (the events row, through the real dispatcher) is in
`test_gm_login_scene_consume_cause_wiring_in_runtime.py`; this file pins
the object.
"""
from __future__ import annotations

import contextlib
import copy
import io
import pathlib
import pickle
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pirateforce_foundation.gm import login_scene_consume  # noqa: E402

C = login_scene_consume

# The exact tuple `runtime.py` catches around the consume call.  Copied by
# hand ON PURPOSE and not imported: the point of these tests is that this
# lane's error lands inside chief's net, and a net this file computed from
# chief's source could change under it without a single test going red --
# it would just start proving a different, weaker sentence.  The end-to-end
# file drives the real dispatcher, which is what pins the real tuple.
THE_RUNTIME_NET = (ValueError, OSError, TypeError)


def a_result_that_lost_its_cause() -> C.ConsumeResult:
    """A real `ConsumeResult` with the `cause` slot never filled.

    Not a stub class: the point is the object chief's call site actually
    receives.  `__new__` skips `__init__`, which is the only shape in which
    `__slots__` leaves a slot unset -- the in-repo regression a future
    return path could write (a subclass filling two slots, a fast-path
    constructor) without any test noticing today.
    """
    result = C.ConsumeResult.__new__(C.ConsumeResult)
    object.__setattr__(result, "scene_id", None)
    object.__setattr__(result, "outcome", C.CONSUME_FAILED)
    return result


class TheErrorIsBothKindsOfWrongTests(unittest.TestCase):
    """Two bases, two different mutation kills."""

    def test_it_is_still_an_attribute_error(self):
        # Drop this base and `hasattr`, `getattr(x, n, default)` and
        # `copy.deepcopy`'s instance lookup all start raising instead of
        # falling back -- the regression D8-R closed, re-opened.
        self.assertTrue(
            issubclass(C.ConsumeResultMisuse, AttributeError)
        )

    def test_it_is_also_a_type_error(self):
        # THE mutation kill for this round: make it a plain
        # `AttributeError` and this test is the only thing that goes red.
        self.assertTrue(issubclass(C.ConsumeResultMisuse, TypeError))

    def test_the_runtime_net_catches_it(self):
        # The sentence in one line: chief's existing handler sees it.
        try:
            raise C.ConsumeResultMisuse("measured")
        except THE_RUNTIME_NET as error:
            self.assertIsInstance(error, C.ConsumeResultMisuse)
        else:  # pragma: no cover - only reachable if the bases change
            self.fail("the runtime's net did not catch ConsumeResultMisuse")

    def test_the_events_row_would_name_it(self):
        # `runtime.py` appends `..._lookup_failed_{type(error).__name__}`,
        # so the class NAME is an operator-facing string, not an internal
        # detail: it is what a GT harness greps for.  Renaming the class is
        # allowed; renaming it without noticing this is not.
        self.assertEqual(
            "ConsumeResultMisuse", C.ConsumeResultMisuse.__name__
        )


class AResultThatLostAFieldTests(unittest.TestCase):
    def test_reading_the_lost_field_raises_the_survivable_error(self):
        result = a_result_that_lost_its_cause()
        with self.assertRaises(C.ConsumeResultMisuse):
            result.cause

    def test_that_raise_is_caught_by_the_runtime_net(self):
        # The whole point, stated where it can fail: this is the read
        # `runtime.py` performs, and it no longer leaves the try block.
        result = a_result_that_lost_its_cause()
        try:
            result.cause
        except THE_RUNTIME_NET:
            pass
        else:  # pragma: no cover - only reachable if __getattr__ goes
            self.fail("the lost-field read escaped the runtime's net")

    def test_the_message_names_the_field_and_carries_no_value(self):
        result = a_result_that_lost_its_cause()
        with self.assertRaises(C.ConsumeResultMisuse) as caught:
            result.cause
        message = str(caught.exception)
        self.assertIn("cause", message)
        # No VALUE from the result may ride along: `outcome` is set on this
        # object and a message built with `!r` of the instance would print
        # it (and, on a real failure, a scene id).  Round `9wy444` D1.
        self.assertNotIn(C.CONSUME_FAILED, message)

    def test_hasattr_and_getattr_default_still_behave(self):
        # Proof of the `AttributeError` half, on the object rather than on
        # the class: the standard library's swallow still swallows.
        result = a_result_that_lost_its_cause()
        self.assertFalse(hasattr(result, "cause"))
        self.assertEqual(
            "sentinel", getattr(result, "cause", "sentinel")
        )

    def test_a_well_formed_result_is_not_intercepted(self):
        # `__getattr__` runs only after normal lookup fails, so nothing on
        # the ordinary path changed.  Kill: a `__getattribute__` written by
        # mistake instead would make this red.
        result = C.ConsumeResult(
            None, C.CONSUME_FAILED, C.CAUSE_CLAIM_RAISED
        )
        self.assertEqual(C.CAUSE_CLAIM_RAISED, result.cause)
        self.assertEqual(C.CONSUME_FAILED, result.outcome)
        self.assertIsNone(result.scene_id)


class TheOperatorGetsALineAndNotOnlyAnEventsRowTests(unittest.TestCase):
    """Otherwise this round would have made the failure QUIETER.

    The escape it replaces at least reached stderr through the thread
    excepthook on its way to killing the listener.  An events row is read
    by a GT harness and by nobody watching a console at 3am, so the console
    keeps a line -- a named one, not the placeholder cause the letter
    forbids.
    """

    LINE = (
        "GM_CONSUME_RESULT_LOST_FIELD field=cause "
        "effect=override_refused_login_at_own_row"
    )

    def read_the_console(self, action):
        console = io.StringIO()
        with contextlib.redirect_stdout(console):
            with self.assertRaises(C.ConsumeResultMisuse):
                action()
        return console.getvalue()

    def test_the_lost_field_prints_its_own_token(self):
        result = a_result_that_lost_its_cause()
        self.assertIn(
            self.LINE, self.read_the_console(lambda: result.cause)
        )

    def test_the_line_carries_no_value_from_the_result(self):
        result = a_result_that_lost_its_cause()
        printed = self.read_the_console(lambda: result.cause)
        # `outcome` is set on this object and a scene id would be set on a
        # real one; neither may ride out on a console line.  Round `9wy444`
        # D1, same rule as the cause vocabulary itself.
        self.assertNotIn(C.CONSUME_FAILED, printed)
        self.assertEqual(1, len(printed.splitlines()))

    def test_an_ordinary_dunder_probe_prints_nothing(self):
        # THE mutation kill for the `in __slots__` guard: drop it and every
        # `copy.deepcopy` in the tree prints a lane token, which is how a
        # console token stops meaning anything.
        console = io.StringIO()
        with contextlib.redirect_stdout(console):
            copy.deepcopy(C.ConsumeResult(1, C.CONSUMED))
            self.assertIsNone(
                getattr(C.ConsumeResult(1, C.CONSUMED), "__deepcopy__", None)
            )
        self.assertEqual("", console.getvalue())

    def test_a_dead_stdout_does_not_change_the_error(self):
        # A diagnostic must never cost more than the diagnostic.  Kill:
        # unguard the print and this raises ValueError (closed file), which
        # `runtime.py` would log under the WRONG name.
        result = a_result_that_lost_its_cause()
        broken = io.StringIO()
        broken.close()
        with contextlib.redirect_stdout(broken):
            with self.assertRaises(C.ConsumeResultMisuse):
                result.cause


class WritingAFieldIsTheSameKindOfWrongTests(unittest.TestCase):
    """The half that already existed, moved inside the net.

    pf-adversary's original finding was that `result.cause = f"...{exc}"`
    was a legal one-line change.  It raises today and it raised before this
    round -- but as a bare `AttributeError`, so the one-line change that
    got as far as PRODUCTION would have taken the listener thread with it.
    """

    def test_assignment_raises_and_the_runtime_net_catches_it(self):
        result = C.ConsumeResult(1, C.CONSUMED)
        with self.assertRaises(C.ConsumeResultMisuse):
            result.cause = "anything"
        try:
            result.cause = "anything"
        except THE_RUNTIME_NET:
            pass
        else:  # pragma: no cover
            self.fail("an assignment escaped the runtime's net")

    def test_deletion_raises_and_the_runtime_net_catches_it(self):
        result = C.ConsumeResult(1, C.CONSUMED)
        with self.assertRaises(C.ConsumeResultMisuse):
            del result.cause
        try:
            del result.cause
        except THE_RUNTIME_NET:
            pass
        else:  # pragma: no cover
            self.fail("a deletion escaped the runtime's net")

    def test_the_old_catchers_still_catch(self):
        # Anything in this tree written as `except AttributeError` around a
        # ConsumeResult keeps working; that is the back-compat half.
        result = C.ConsumeResult(1, C.CONSUMED)
        with self.assertRaises(AttributeError):
            result.cause = "anything"
        with self.assertRaises(AttributeError):
            a_result_that_lost_its_cause().cause


class CopyAndPickleAreUntouchedTests(unittest.TestCase):
    """`__getattr__` is exactly the hook `copy`/`pickle` probe with getattr.

    `copy.deepcopy` looks up `__deepcopy__` ON THE INSTANCE with a default;
    `pickle` probes `__reduce_ex__` and friends.  Every one of those probes
    now reaches this lane's `__getattr__` -- and survives only because the
    error is still an `AttributeError`.  D8-R pins the round trip; this
    pins the reason, so a future "tidy the bases" change fails HERE with a
    name that explains itself rather than in a deepcopy three files away.
    """

    def results(self):
        return [
            C.ConsumeResult(1, C.CONSUMED),
            C.ConsumeResult(
                None, C.CONSUME_FAILED, C.CAUSE_ENTRY_SURVIVED_CLAIM
            ),
        ]

    def test_the_dunder_probe_falls_back_instead_of_raising(self):
        for original in self.results():
            with self.subTest(outcome=original.outcome):
                self.assertIsNone(
                    getattr(original, "__deepcopy__", None)
                )

    def test_copy_deepcopy_and_pickle_still_round_trip(self):
        for original in self.results():
            with self.subTest(outcome=original.outcome):
                self.assertEqual(original, copy.copy(original))
                self.assertEqual(original, copy.deepcopy(original))
                self.assertEqual(
                    original, pickle.loads(pickle.dumps(original))
                )


if __name__ == "__main__":
    unittest.main()
