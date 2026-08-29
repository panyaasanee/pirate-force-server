"""A `ConsumeResult` that lost a field must cost the OVERRIDE, not the port.

Round `npo898`, consuming chief's reply of 2026-08-29T19:24+07:00 to
`CORE-REQUEST-GM-037`, item 1: "loud to whom?".

WHAT WAS MEASURED THERE (by pf-adversary, round `nbulzb`, and re-read from
the source in this round before writing a line of this file):

* `runtime.py` reads `override_result.cause` outside the `try: print(...)
  except Exception: pass` guard -- this lane demanded that, and it stands;
* that read sits INSIDE `except (ValueError, OSError, TypeError)`;
* a bare `AttributeError` is in neither net, so it unwinds the game
  listener thread: `game_listener` in
  `current/pf_login_game_server_v141.py` wraps `state.dispatch` in no
  `except` but the socket ones, its accept loop catches only
  `socket.timeout`, and it is a daemon thread while the login accept loop
  is the main one.  The process keeps the login port and loses the game
  port -- a supervisor sees a live process, a tester sees a client that
  connects and never enters.

WHAT THIS FILE'S FIRST VERSION GOT WRONG, kept rather than quietly fixed
(pf-adversary D5, this round, measured): it said the old failure left "the
console saying nothing".  It does not.  An uncaught error in a daemon
thread reaches Python's default `threading.excepthook`, which prints a
full traceback -- file, line, field name -- to stderr.  The old failure was
LOUDER IN CONTENT than what replaces it.  The defect was the DEAD PORT, and
a supervisor blind to it.  That is enough of a reason on its own; the
exaggeration was not needed and is struck here rather than argued.

THE ANSWER THIS LANE SHIPS: the operator's artifact is a named console
line, and a red CI.  `ConsumeResultMisuse` inherits BOTH `AttributeError`
(so nothing that catches one changes behaviour, `copy.deepcopy`'s
instance-level `getattr(x, "__deepcopy__", None)` included) and `TypeError`
(so the net `runtime.py` ALREADY has catches it, with no change to chief's
file).  The events row `..._lookup_failed_ConsumeResultMisuse` is a third
artifact and NOT a greppable one on a default boot (D6): `app.py` builds an
event exporter only under `--export-events`.

WHAT IS NOT CLAIMED.  Nothing here is client-observable: no byte of any of
this reaches a client, and the paths driven below are in-repo regression
drills -- at HEAD a real `ConsumeResult` cannot exist without a cause.
This file is console-side only.  It also does not claim the game listener
is now safe from `AttributeError` in general (D7): only THIS class's
raises moved inside chief's net.  `CORE-REQUEST-GM-039` is the ticket for
the net itself.  The end-to-end half of the property (the console line and
the events row, through the real dispatcher) is in
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
# (pf-adversary attacked this hand-copy from both sides this round --
# narrowing chief's net, widening it to `except Exception`, and swapping
# the bases underneath it -- and every attack turned the wiring file red.)
THE_RUNTIME_NET = (ValueError, OSError, TypeError)

# Values chosen to be unmistakable in a haystack: if either ever reaches a
# console line, `assertNotIn` finds it.  A real failure's `scene_id` is an
# integer read out of `gm_login_scene.json`, which is why `None` -- what the
# first version of these tests used -- could not prove anything (D3).
LOUD_SCENE_ID = 90210
LOUD_OUTCOME = C.CONSUME_FAILED


def a_result_missing(
    field: str,
    scene_id: int | None = LOUD_SCENE_ID,
    outcome: str = LOUD_OUTCOME,
    cause: str = C.CAUSE_CLAIM_RAISED,
) -> C.ConsumeResult:
    """A real `ConsumeResult` with exactly one slot never filled.

    Not a stub class: the point is the object chief's call site actually
    receives.  `__new__` skips `__init__`, which is the only shape in which
    `__slots__` leaves a slot unset -- the in-repo regression a future
    return path could write (a subclass filling two slots, a fast-path
    constructor) without any test noticing today.
    """
    values = {"scene_id": scene_id, "outcome": outcome, "cause": cause}
    del values[field]
    result = C.ConsumeResult.__new__(C.ConsumeResult)
    for name, value in values.items():
        object.__setattr__(result, name, value)
    return result


def a_result_that_lost_its_cause() -> C.ConsumeResult:
    return a_result_missing("cause")


@contextlib.contextmanager
def console():
    """Capture stdout, so the suite does not print the lane's own token.

    pf-adversary D4 counted six emissions of
    `GM_CONSUME_RESULT_LOST_FIELD` on a plain `pytest -s` run of this
    round's files -- from a suite whose own source argues that a token
    printed where nothing was refused is what teaches an operator to
    ignore it.  Every test here now reads the console rather than leaking
    to it, including the ones that do not assert on it.
    """
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        yield captured


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
        # detail.  (It is only greppable under `--export-events`; see the
        # module docstring.)  Renaming the class is allowed; renaming it
        # without noticing this is not.
        self.assertEqual(
            "ConsumeResultMisuse", C.ConsumeResultMisuse.__name__
        )


class AResultThatLostAFieldTests(unittest.TestCase):
    def test_reading_the_lost_field_raises_the_survivable_error(self):
        result = a_result_that_lost_its_cause()
        with console():
            with self.assertRaises(C.ConsumeResultMisuse):
                result.cause

    def test_that_raise_is_caught_by_the_runtime_net(self):
        # The whole point, stated where it can fail: this is the read
        # `runtime.py` performs, and it no longer leaves the try block.
        result = a_result_that_lost_its_cause()
        with console():
            try:
                result.cause
            except THE_RUNTIME_NET:
                pass
            else:  # pragma: no cover - only reachable if __getattr__ goes
                self.fail("the lost-field read escaped the runtime's net")

    def test_every_slot_raises_when_it_is_the_one_that_is_missing(self):
        # `runtime.py` reads `scene_id` and `outcome` BEFORE it reads
        # `cause`, so those two are the fields a real regression loses
        # first.  The first version of this file only ever lost `cause`.
        for field in ("scene_id", "outcome", "cause"):
            with self.subTest(field=field):
                result = a_result_missing(field)
                with console():
                    with self.assertRaises(C.ConsumeResultMisuse):
                        getattr(result, field)

    def test_a_name_outside_the_slots_still_raises(self):
        # THE D1 KILL, and it was the disqualifying gap: an `else: return
        # None` in `__getattr__` -- four characters -- turned the hook into
        # the silent default this whole round forbids, and survived 4951
        # tests.  A name that is not a slot must still RAISE, and must
        # print nothing.
        result = C.ConsumeResult(1, C.CONSUMED)
        with console() as printed:
            with self.assertRaises(C.ConsumeResultMisuse):
                result.consume_cause  # a plausible typo, not a slot
        self.assertEqual("", printed.getvalue())

    def test_the_message_names_the_field_and_carries_no_value(self):
        for field in ("scene_id", "outcome", "cause"):
            with self.subTest(field=field):
                result = a_result_missing(field)
                with console():
                    with self.assertRaises(C.ConsumeResultMisuse) as caught:
                        getattr(result, field)
                message = str(caught.exception)
                self.assertIn(field, message)
                self.assertNotIn(str(LOUD_SCENE_ID), message)
                self.assertNotIn(C.CAUSE_CLAIM_RAISED, message)

    def test_hasattr_and_getattr_default_still_behave(self):
        # Proof of the `AttributeError` half, on the object rather than on
        # the class: the standard library's swallow still swallows.
        result = a_result_that_lost_its_cause()
        with console():
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
        with console() as printed:
            self.assertEqual(C.CAUSE_CLAIM_RAISED, result.cause)
            self.assertEqual(C.CONSUME_FAILED, result.outcome)
            self.assertIsNone(result.scene_id)
        self.assertEqual("", printed.getvalue())


class TheOperatorGetsALineTests(unittest.TestCase):
    """With the raise now CAUGHT, the console would otherwise get nothing.

    Not "a message where there was none" -- see the module docstring: the
    escape this replaces printed a traceback on its way to killing the
    port.  This is a message that does not cost the port.
    """

    def line_for(self, field):
        return (
            f"GM_CONSUME_RESULT_LOST_FIELD field={field} read=refused"
        )

    def read_the_console(self, result, field):
        with console() as printed:
            with self.assertRaises(C.ConsumeResultMisuse):
                getattr(result, field)
        return printed.getvalue()

    def test_the_line_names_the_field_that_was_actually_lost(self):
        # THE D2 KILL: three mutants survived the whole suite before this
        # -- hardcoding `field=cause`, hardcoding the message's field, and
        # narrowing the slot guard to `name == "cause"`.  An operator was
        # being told to grep `cause` while `cause` was present and intact.
        for field in ("scene_id", "outcome", "cause"):
            with self.subTest(field=field):
                printed = self.read_the_console(
                    a_result_missing(field), field
                )
                self.assertIn(self.line_for(field), printed)

    def test_the_line_claims_no_effect_it_cannot_know(self):
        # D4: the first version printed
        # `effect=override_refused_login_at_own_row` -- word for word the
        # same line a `hasattr` probe produced, having refused nothing.
        # What the effect WAS belongs to the events row `runtime.py`
        # appends, which is the only place that knows.
        printed = self.read_the_console(
            a_result_that_lost_its_cause(), "cause"
        )
        self.assertNotIn("effect=", printed)
        self.assertIn("read=refused", printed)

    def test_the_line_carries_no_value_from_the_result(self):
        # D3: the first version drove a result whose `scene_id` was None,
        # so appending `scene_id={...}` to the printed line survived the
        # whole suite.  A real failure's scene id comes out of
        # `gm_login_scene.json` -- round `9wy444` D1 forbids it reaching a
        # console under this lane's token.
        printed = self.read_the_console(
            a_result_missing("cause"), "cause"
        )
        self.assertNotIn(str(LOUD_SCENE_ID), printed)
        self.assertNotIn(C.CONSUME_FAILED, printed)
        self.assertEqual(1, len(printed.splitlines()))

    def test_a_subclass_that_loses_its_own_slot_prints_too(self):
        # D12: the guard read `ConsumeResult.__slots__`, so the shape the
        # hook's own docstring names -- a subclass filling some of its
        # slots -- raised with no console line at all.
        class Sub(C.ConsumeResult):
            __slots__ = ("extra",)

        instance = Sub(1, C.CONSUMED)
        printed = self.read_the_console(instance, "extra")
        self.assertIn(self.line_for("extra"), printed)

    def test_an_ordinary_dunder_probe_prints_nothing(self):
        # The other half of the `in slots` guard: drop it and every
        # `copy.deepcopy` in the tree prints a lane token, which is how a
        # console token stops meaning anything.
        with console() as printed:
            copy.deepcopy(C.ConsumeResult(1, C.CONSUMED))
            self.assertIsNone(
                getattr(C.ConsumeResult(1, C.CONSUMED), "__deepcopy__", None)
            )
        self.assertEqual("", printed.getvalue())

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


class ADiagnosticThatRaisesIsNotADiagnosticTests(unittest.TestCase):
    """D10: `repr()` of a lost result used to raise -- inside an `except`.

    The likeliest place anyone writes `repr(override_result)` is chief's
    own handler, where a second raise is caught by nothing and takes the
    listener thread after all -- the exact failure this round exists to
    remove, re-entered through the diagnostic.
    """

    def test_repr_of_a_lost_result_neither_raises_nor_prints(self):
        for field in ("scene_id", "outcome", "cause"):
            with self.subTest(field=field):
                result = a_result_missing(field)
                with console() as printed:
                    rendered = repr(result)
                self.assertIn("<lost>", rendered)
                self.assertEqual("", printed.getvalue())

    def test_repr_of_a_well_formed_result_is_unchanged(self):
        result = C.ConsumeResult(
            7, C.CONSUME_FAILED, C.CAUSE_GM_MAP_UNREADABLE
        )
        self.assertEqual(
            "ConsumeResult(scene_id=7, outcome='consume_failed', "
            "cause='gm_map_unreadable')",
            repr(result),
        )


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
        with console():
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
