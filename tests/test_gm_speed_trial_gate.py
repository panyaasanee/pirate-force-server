"""COO `0646` item 2: the runtime trial gate that opens `/speed` for ONE value.

WHY THIS FILE EXISTS
--------------------
`/speed` is held by two locks that this lane may not open on `main`
(`speed_wire.SPEED_LOGIN_READ_LANDED` is `False`,
`speed_wire.SHAPES_CLEARED_BY_A_REAL_CLIENT` is empty), and `COO 2147` point 3
forbids opening either until the attended round that deliberately tries a safe
value has happened and has a result.  That round -- `GT-218` -- cannot boot
until both locks are already open.  Neither side can move first.

COO-DECISION 2026-09-03T06:46+07:00 (`pf_bridge/notes_to_chief/20260903_0646_
COO-DECISION-lane-gm-the-row-keeps-being-written-and-the-trial-opens-at-
runtime-not-on-main.md`, item 2) cut the loop without opening either lock:
"ไม่มีล็อกไหนถูกเปิดบน `main` ทั้งสองคงค่าเดิม -- ทางเปิดคือ **เกต runtime** รูปเดียวกับ
`PFGM_FORCE=1`".  `PF_SPEED_TRIAL=<one value>` in the process environment
admits `/speed <that one value>` and nothing else; the owner is the one who
opens it, in her own session, and it closes when the process dies.

WHAT IS PINNED HERE, AND IN WHICH ORDER
---------------------------------------
1. `TheShippedDefaultOpensNothingTests` runs FIRST on purpose: it is the half
   `COO 2147` point 3 is actually about.  With the variable unset -- which is
   every `main` checkout, every gate run, and every machine nobody has armed
   -- the route behaves EXACTLY as it did before this gate existed, and both
   module constants are untouched.
2. The unit half: what "one value" means when the value arrives as text.
3. The end-to-end half: an armed gate really does put the frame on the route,
   with BOTH locks still measured shut while it does.

WHAT IS NOT PINNED, BECAUSE NOBODY MEASURED IT.  That any `/speed` value is
safe on a real client.  `GT-193` [FAIL] is the only client-observable
measurement this door has and it ends in a dead character and a locked client.
This gate is a way for the owner to try ONE value while watching; it is not
evidence about the value, and no test here claims otherwise.
"""
from __future__ import annotations

import ast
import io
import json
import os
import struct
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import attr_wire  # noqa: E402
from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import speed_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import login_speed  # noqa: E402
from pirateforce_foundation import persistence_typed_attrs  # noqa: E402
from pirateforce_foundation import player_wire  # noqa: E402

RUN_COPY_DB_FILENAME = "pirateforce_lane_gm_20260903_0713.sqlite3"

#: The value every end-to-end test below arms.  Deliberately NOT `400.0`:
#: `migrations/009` gives the column that DEFAULT and it equals the hardcoded
#: login constant, so a test written on `400.0` passes even when the door it
#: means to exercise has been deleted (`COO 0054`, and LANE-DB's letter
#: `20260903_0635` section 4 states the same rule for its own file).
ARMED = "450"
ARMED_F32 = 450.0

#: The number `main` sends at login today, read from the module that owns it
#: rather than typed here -- this file must never become a second place
#: `400.0` is written down (`login_speed.py` states the same rule).
CONSTANT = player_wire.PLAYER_LOGIN_MOVEMENT_SPEED


def make_chat_payload(message: str, speaker: str = "") -> bytes:
    """One inbound 0xAC52 chat payload, in the GT-006/GT-009 measured shape."""
    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


@contextmanager
def environment(value):
    """`PF_SPEED_TRIAL` set to `value`, or REMOVED when `value` is `None`.

    Removal is why this is not `mock.patch.dict(os.environ, {...})`: that
    helper can add and overwrite, but the state this file has to be able to
    produce -- and to RESTORE to -- is the key being absent.  `clear=True`
    would produce it by emptying the whole environment, which is a different
    experiment (`load_legacy` and `tempfile` both read it).
    """
    saved = os.environ.get(speed_wire.SPEED_TRIAL_ENV)
    if value is None:
        os.environ.pop(speed_wire.SPEED_TRIAL_ENV, None)
    else:
        os.environ[speed_wire.SPEED_TRIAL_ENV] = value
    try:
        yield
    finally:
        if saved is None:
            os.environ.pop(speed_wire.SPEED_TRIAL_ENV, None)
        else:
            os.environ[speed_wire.SPEED_TRIAL_ENV] = saved


class FakeSelected:
    def __init__(self, identity_lo=1, identity_hi=0, character_id=1):
        self.identity_lo = identity_lo
        self.identity_hi = identity_hi
        self.id = character_id


class FakeStore:
    """The read-back goes through the REAL validator, and it has to.

    Same reason `tests/test_gm_speed_deferred.py`'s double states: the
    validator rounds to f32 on the way in, and that divergence is the only
    thing that can tell "the number the row holds" apart from "the number the
    GM typed".  This file leans on it directly -- the gate compares against
    the READ-BACK, so a double that echoed the typed value would leave the
    `400.1` -> `400.1000061035156` case unproven.
    """

    def __init__(self, path):
        self.path = path
        self.calls = []
        self.undo_writes = []
        self.stored = {}

    def read_typed_attributes(self, character_id):
        return dict(self.stored)

    def write_typed_attributes(self, character_id, values):
        self.undo_writes.append((character_id, dict(values)))
        self.stored.update(values)

    #: When set, the number this store reports the row HOLDS, whatever was
    #: typed.  A real store can diverge from the typed value for reasons this
    #: lane does not control -- the f32 round trip does it today, a CHECK
    #: constraint or a future clamp could do more -- and the gate's contract
    #: is that it admits THE NUMBER THAT GOES ON THE WIRE, which is this one.
    readback = None

    def write_speed_by_identity(self, identity_lo, identity_hi, speed):
        self.calls.append((identity_lo, identity_hi, speed))
        column = chat_command_action.SPEED_TYPED_COLUMN
        self.stored[column] = speed
        if self.readback is not None:
            return {speed_wire.SPEED_FIELD_X: float(self.readback)}
        return {
            speed_wire.SPEED_FIELD_X: persistence_typed_attrs.validate(
                column, speed
            )
        }


class FakeLifecycle:
    def __init__(self, store):
        self.store = store


class FakeFoundation:
    def __init__(self, selected, store):
        self.selected = selected
        self.lifecycle = None if store is None else FakeLifecycle(store)


class FakeSession:
    def __init__(self, store, token="GM_ONE", selected=None):
        self.token = token
        self.events = []
        self.foundation = FakeFoundation(
            FakeSelected() if selected is None else selected, store
        )


class _Case(unittest.TestCase):
    """No `setUp` here patches either lock -- that is the point of the file.

    Every other `/speed` test file opens one gate or another to reach the code
    below it.  These run against the SHIPPED constants, so the only thing that
    can put a frame on the route is the runtime gate itself.

    THE ENVIRONMENT IS SCRUBBED FOR EVERY TEST, and that is not tidiness: a
    developer (or a bridge console) that armed `PF_SPEED_TRIAL` in the shell
    it then ran `pytest` from would otherwise flip the meaning of every
    "nothing is armed" assertion in this file, silently.  Each test that wants
    an armed gate says so with `environment(...)`.
    """

    GM_ACCOUNT = "GM_ONE"

    def setUp(self):
        gm_dispatch.reset_rate_limit_state_for_tests()
        scrubbed = environment(None)
        scrubbed.__enter__()
        self.addCleanup(scrubbed.__exit__, None, None, None)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.config_path = self.tmp / "gm_accounts.json"
        self.config_path.write_text(
            json.dumps({"gm_accounts": [self.GM_ACCOUNT]}), encoding="utf-8"
        )
        self.log_path = self.tmp / "capture" / "gm_command_log.ndjson"
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.state_dir = self.tmp / "state"
        self.state_dir.mkdir()
        self.run_copy_db = str(self.state_dir / RUN_COPY_DB_FILENAME)

    def store(self):
        return FakeStore(self.run_copy_db)

    def session(self, store=None):
        return FakeSession(self.store() if store is None else store)

    def act(self, session, text=f"/speed {ARMED}"):
        return chat_command_action.make_gm_chat_command_action(
            session,
            make_chat_payload(text),
            self.legacy,
            config_path=str(self.config_path),
            log_path=str(self.log_path),
        )

    def act_capturing_console(self, session, text=f"/speed {ARMED}"):
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            action = self.act(session, text)
        return action, buffer.getvalue()

    def one_line_starting(self, console, token):
        lines = [
            line for line in console.splitlines() if line.startswith(token)
        ]
        self.assertEqual(len(lines), 1, console)
        return lines[0]

    def assertNoTrialLine(self, console):
        self.assertNotIn(
            chat_command_action.SPEED_TRIAL_CONSOLE_TOKEN,
            console,
            "a route that sent nothing still announced an open trial gate",
        )


class TheShippedDefaultOpensNothingTests(_Case):
    """`COO 2147` point 3, restated as assertions: nothing is armed by default."""

    def test_neither_lock_is_edited_by_this_section(self):
        self.assertFalse(speed_wire.SPEED_LOGIN_READ_LANDED)
        self.assertEqual(speed_wire.SHAPES_CLEARED_BY_A_REAL_CLIENT, frozenset())

    def test_an_unset_variable_reads_as_unset_not_as_a_value(self):
        self.assertEqual(
            speed_wire.trial_opening(), (speed_wire.TRIAL_UNSET, None)
        )
        self.assertEqual(speed_wire.trial_console_field(), speed_wire.TRIAL_UNSET)

    def test_an_unset_variable_admits_no_value_a_gm_could_type(self):
        for value in (0.0, -0.0, 1.0, 400.0, ARMED_F32, 1e30, -5.5):
            with self.subTest(value=value):
                self.assertFalse(speed_wire.trial_admits(value))

    def test_the_route_still_defers_and_sends_nothing(self):
        session = self.session()
        action, console = self.act_capturing_console(session)
        self.assertIsNone(
            action,
            "an unarmed process put something on the wire for /speed",
        )
        self.assertIn(chat_command_action.EVENT_SPEED_DEFERRED, session.events)
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_TRIAL_ADMITTED, session.events
        )
        self.assertNoTrialLine(console)
        self.one_line_starting(
            console, chat_command_action.SPEED_DEFERRED_CONSOLE_TOKEN
        )

    def test_the_deferral_line_says_the_gate_is_unset(self):
        session = self.session()
        _action, console = self.act_capturing_console(session)
        line = self.one_line_starting(
            console, chat_command_action.SPEED_DEFERRED_CONSOLE_TOKEN
        )
        self.assertIn(f"trial_opens_for={speed_wire.TRIAL_UNSET}", line)


class OneValueMeansOneF32Tests(_Case):
    """What "ค่าเดียว" has to mean when the value arrives as shell text."""

    def test_three_spellings_of_the_same_number_arm_the_same_gate(self):
        for spelling in ("450", "450.0", "4.5e2", " 450 ", "+450"):
            with self.subTest(spelling=spelling):
                self.assertEqual(
                    speed_wire.trial_opening({"PF_SPEED_TRIAL": spelling}),
                    (speed_wire.TRIAL_ARMED, ARMED_F32),
                )

    def test_the_armed_value_is_rounded_the_way_the_row_is(self):
        # `400.1` is stored and read back as `400.1000061035156`; a gate that
        # compared against the un-rounded double would arm a value the route
        # can never offer it, and the door would look armed and never open.
        rounded = persistence_typed_attrs.validate(
            chat_command_action.SPEED_TYPED_COLUMN, 400.1
        )
        self.assertNotEqual(rounded, 400.1)
        self.assertEqual(
            speed_wire.trial_opening({"PF_SPEED_TRIAL": "400.1"}),
            (speed_wire.TRIAL_ARMED, rounded),
        )
        self.assertTrue(
            speed_wire.trial_admits(rounded, {"PF_SPEED_TRIAL": "400.1"})
        )

    def test_only_that_one_value_is_admitted(self):
        armed = {"PF_SPEED_TRIAL": ARMED}
        self.assertTrue(speed_wire.trial_admits(ARMED_F32, armed))
        for other in (449.0, 451.0, 450.0001, -450.0, 0.0, 400.0):
            with self.subTest(other=other):
                self.assertFalse(speed_wire.trial_admits(other, armed))

    def test_negative_zero_is_not_the_same_value_as_zero(self):
        # `-0.0 == 0.0` is True in Python, so an `==` comparison here would
        # let `PF_SPEED_TRIAL=0` admit `/speed -0`.  LANE-DB's round `vitdca`
        # met the same value from the persistence side.
        self.assertTrue(speed_wire.trial_admits(0.0, {"PF_SPEED_TRIAL": "0"}))
        self.assertFalse(speed_wire.trial_admits(-0.0, {"PF_SPEED_TRIAL": "0"}))
        self.assertTrue(speed_wire.trial_admits(-0.0, {"PF_SPEED_TRIAL": "-0"}))
        self.assertFalse(speed_wire.trial_admits(0.0, {"PF_SPEED_TRIAL": "-0"}))

    def test_a_bool_is_never_a_speed_on_either_side_of_the_gate(self):
        self.assertFalse(speed_wire.trial_admits(True, {"PF_SPEED_TRIAL": "1"}))
        self.assertFalse(speed_wire.trial_admits(False, {"PF_SPEED_TRIAL": "0"}))
        self.assertEqual(
            speed_wire.trial_opening({"PF_SPEED_TRIAL": "True"}),
            (speed_wire.TRIAL_MALFORMED, None),
        )

    def test_an_integer_offered_value_is_admitted_by_its_f32(self):
        # The route offers a float today, but `trial_admits` is called
        # "regardless of source" like every other entry point in this lane.
        self.assertTrue(speed_wire.trial_admits(450, {"PF_SPEED_TRIAL": ARMED}))


class EverythingMalformedFailsClosedTests(_Case):
    MALFORMED = (
        "fast",
        "450abc",
        "nan",
        "NaN",
        "inf",
        "-inf",
        "infinity",
        "1e400",
        "450,0",
        "0x1p3",
        "450 451",
    )

    def test_none_of_these_arm_the_gate(self):
        for raw in self.MALFORMED:
            with self.subTest(raw=raw):
                self.assertEqual(
                    speed_wire.trial_opening({"PF_SPEED_TRIAL": raw}),
                    (speed_wire.TRIAL_MALFORMED, None),
                )

    def test_none_of_these_admit_any_value(self):
        for raw in self.MALFORMED:
            for value in (0.0, 1.0, 450.0, float("1e30")):
                with self.subTest(raw=raw, value=value):
                    self.assertFalse(
                        speed_wire.trial_admits(value, {"PF_SPEED_TRIAL": raw})
                    )

    def test_a_value_beyond_f32_is_malformed_not_clamped(self):
        # A clamp would arm a value the owner did not choose, which is the one
        # thing a fail-closed gate may never do.
        beyond = repr(persistence_typed_attrs.F32_MAX * 2)
        self.assertEqual(
            speed_wire.trial_opening({"PF_SPEED_TRIAL": beyond}),
            (speed_wire.TRIAL_MALFORMED, None),
        )

    def test_an_empty_or_blank_variable_reads_as_unset(self):
        # `set PF_SPEED_TRIAL=` on the bridge's cmd.exe leaves an empty
        # string.  The operator who cleared it did the right thing and must
        # not be told she made a mistake.
        for raw in ("", " ", "\t", "  \n "):
            with self.subTest(raw=repr(raw)):
                self.assertEqual(
                    speed_wire.trial_opening({"PF_SPEED_TRIAL": raw}),
                    (speed_wire.TRIAL_UNSET, None),
                )

    def test_a_non_string_value_is_malformed(self):
        self.assertEqual(
            speed_wire.trial_opening({"PF_SPEED_TRIAL": 450.0}),
            (speed_wire.TRIAL_MALFORMED, None),
        )

    def test_a_mapping_that_raises_is_malformed_not_an_exception(self):
        class Hostile:
            def get(self, _key):
                raise RuntimeError("no environment here")

        self.assertEqual(
            speed_wire.trial_opening(Hostile()),
            (speed_wire.TRIAL_MALFORMED, None),
        )
        self.assertFalse(speed_wire.trial_admits(450.0, Hostile()))
        self.assertEqual(
            speed_wire.trial_console_field(Hostile()), speed_wire.TRIAL_MALFORMED
        )


class TheArmedValueGetsThroughBothLocksTests(_Case):
    """~~The end-to-end half: an armed gate really does reach the composer.~~

    STRUCK BY `COO-DECISION 20260904_0345` ITEM 2, which WITHDREW COO's own
    2026-09-03 06:46 approval of this gate: that approval predates `RE-222`
    (21:49), and `RE-222` Q0 says the client's apply is a full-object copy
    whose constructor zeroes every field first.  So the harm never depended
    on the number the gate admits -- it is the 54 rows the sparse shape
    omits, which is what `GT-218` measured (HP `0/1`, cash `0`, one frame).
    There is no safe value to admit, so the composer below this gate is
    shut.

    WHAT THIS CLASS PINS NOW: the gate still does its own job exactly as
    before -- it still parses one value, still admits only that value, still
    bypasses rather than opens the two locks -- and the route now ends in a
    REFUSAL WITH ONE CONSOLE LINE AND ZERO BYTES, which is the outcome COO
    ordered in as many words.  The gate's parsing half is unchanged and its
    own classes above still pin it; only the ending moved.
    """

    def test_the_armed_value_no_longer_produces_this_doors_own_action(self):
        session = self.session()
        with environment(ARMED):
            action = self.act(session)
        self.assertIsNotNone(
            action, "the armed value must still produce a REFUSAL, not silence"
        )
        self.assertNotEqual(action[0], chat_command_action.SPEED_ACTION_LABEL)
        self.assertEqual(
            action[0], chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL
        )

    def test_both_locks_are_still_shut_and_so_is_the_composer(self):
        # THE CLAIM COO `0646` MADE AND THIS TEST KEEPS: the gate BYPASSES the
        # locks for one value, it does not OPEN them.  A future round that
        # implemented the gate by flipping a constant instead turns this red.
        # The third clause is new (`0345` item 2): the composer it bypasses
        # into is shut too, so bypassing buys nothing.
        session = self.session()
        with environment(ARMED):
            action = self.act(session)
            self.assertTrue(speed_wire.send_deferred())
            self.assertEqual(
                speed_wire.SHAPES_CLEARED_BY_A_REAL_CLIENT, frozenset()
            )
            with self.assertRaises(speed_wire.SpeedWireError):
                speed_wire.compose_sparse_speed_update(
                    self.legacy, 1, 0, ARMED_F32
                )
        self.assertEqual(
            action[0], chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL
        )
        self.assertTrue(speed_wire.send_deferred())

    def test_the_event_trail_names_the_shut_composer_not_the_gate(self):
        # ~~names the gate that let it out~~ -- nothing gets let out now.
        # `EVENT_SPEED_TRIAL_ADMITTED` is noted BELOW the compose on purpose
        # (see `_speed_action`'s own comment: a line saying `sending=` above a
        # composer that then refused would be the console lying about bytes),
        # so a refused compose never reaches it.  What the trail carries
        # instead names the compose refusal by exception type, which is the
        # word an operator greps.
        session = self.session()
        with environment(ARMED):
            self.act(session)
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_TRIAL_ADMITTED, session.events
        )
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_DEFERRED, session.events
        )
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_WITHHELD_SHAPE_UNCLEARED,
            session.events,
        )
        self.assertTrue(
            [
                event
                for event in session.events
                if event.startswith(
                    chat_command_action
                    .EVENT_SPEED_PERSIST_COMPOSE_REFUSED_PREFIX
                )
            ],
            f"no compose-refused event in {session.events!r}",
        )

    def test_the_row_is_still_written_first(self):
        store = self.store()
        session = self.session(store)
        with environment(ARMED):
            self.act(session)
        self.assertEqual(len(store.calls), 1)
        # `(identity_lo, identity_hi, speed)` since the door swap; the value
        # is still the f32 the environment armed, and the row still moves
        # before either lock is consulted.
        self.assertEqual(store.calls[0][2], ARMED_F32)
        self.assertEqual(
            store.stored[chat_command_action.SPEED_TYPED_COLUMN], ARMED_F32
        )

    def test_the_console_says_the_door_shut_not_which_value_it_opened_for(self):
        # ~~says which value the door opened for~~ -- struck.  COO `0345`
        # item 2 asks for exactly "a refusal with ONE console line and no
        # bytes out", and this is that line.  The `sending=` line is
        # deliberately NOT printed as well: it lives below the compose, so a
        # refused compose can never produce a console line that claims bytes
        # went out.
        session = self.session()
        with environment(ARMED):
            _action, console = self.act_capturing_console(session)
        self.assertNotIn(chat_command_action.SPEED_TRIAL_CONSOLE_TOKEN, console)
        line = self.one_line_starting(console, "GM_CHAT_NO_BYTES_SENT")
        self.assertIn("SpeedWireError", line)

    def test_that_line_is_pure_ascii(self):
        # The bridge console is cp874; one non-ASCII byte costs the whole line
        # and therefore the grep an attended round is run on.
        session = self.session()
        with environment(ARMED):
            _action, console = self.act_capturing_console(session)
        line = self.one_line_starting(console, "GM_CHAT_NO_BYTES_SENT")
        line.encode("ascii")

    def test_the_typed_spelling_never_reaches_the_console(self):
        # `/speed 4.5e2` is the same f32 as `450`, so the gate admits it -- and
        # the console must never echo the GM's own text, refusal or not.  The
        # reason survives the door closing: the typed string is the one thing
        # on this path this lane did not write.
        session = self.session()
        with environment(ARMED):
            _action, console = self.act_capturing_console(session, "/speed 4.5e2")
        self.assertNotIn("4.5e2", console)
        self.assertIn("GM_CHAT_NO_BYTES_SENT", console)

    def test_the_environments_raw_text_never_reaches_the_console(self):
        # An armed-but-malformed variable is the case where echoing would be
        # easiest and worst: the raw string is the one thing on this path that
        # this lane did not write.
        session = self.session()
        with environment("fast; rm -rf /"):
            _action, console = self.act_capturing_console(session)
        self.assertNotIn("rm -rf", console)
        self.assertNotIn("fast", console)


class EveryOtherValueStaysHeldTests(_Case):
    """"ค่าอื่นทุกค่ายังถูกกัก" -- the other half of the same sentence."""

    def test_a_different_value_is_still_deferred_while_the_gate_is_armed(self):
        session = self.session()
        with environment(ARMED):
            action, console = self.act_capturing_console(session, "/speed 451")
        self.assertIsNone(action)
        self.assertIn(chat_command_action.EVENT_SPEED_DEFERRED, session.events)
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_TRIAL_ADMITTED, session.events
        )
        self.assertNoTrialLine(console)

    def test_and_its_deferral_line_names_the_value_that_would_pass(self):
        # The operator who typed the wrong number learns the right one from
        # the console rather than from the shell she set the variable in.
        session = self.session()
        with environment(ARMED):
            _action, console = self.act_capturing_console(session, "/speed 451")
        line = self.one_line_starting(
            console, chat_command_action.SPEED_DEFERRED_CONSOLE_TOKEN
        )
        self.assertIn(f"trial_opens_for={ARMED_F32!r}", line)

    def test_a_malformed_gate_holds_every_value_and_says_so(self):
        session = self.session()
        with environment("fast"):
            action, console = self.act_capturing_console(session)
        self.assertIsNone(action)
        line = self.one_line_starting(
            console, chat_command_action.SPEED_DEFERRED_CONSOLE_TOKEN
        )
        self.assertIn(f"trial_opens_for={speed_wire.TRIAL_MALFORMED}", line)

    def test_the_gate_is_re_read_every_command_not_cached_at_import(self):
        # The two outcomes still DIFFER, which is what makes this a re-read
        # test: armed reaches the composer and is refused there (an action
        # carrying a refusal notice), unarmed never gets past the deferral
        # (no action at all).  Only the first one's ending changed
        # (`COO-DECISION 20260904_0345` item 2).
        session = self.session()
        with environment(ARMED):
            first = self.act(session)
        self.assertEqual(
            first[0], chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL
        )
        second = self.act(self.session())
        self.assertIsNone(
            second,
            "the gate stayed open after the variable was removed -- a door "
            "that outlives the owner's session is the one COO 2147 forbids",
        )


class TheGateNeverRaisesIntoDispatchTests(_Case):
    """An unanswerable gate is a CLOSED gate, and a printer never vetoes."""

    def test_a_raising_admit_check_holds_the_frame(self):
        session = self.session()
        with mock.patch.object(
            speed_wire, "trial_admits", side_effect=RuntimeError("boom")
        ):
            with environment(ARMED):
                action, console = self.act_capturing_console(session)
        self.assertIsNone(action)
        self.assertIn(chat_command_action.EVENT_SPEED_DEFERRED, session.events)
        self.assertNoTrialLine(console)

    def test_a_raising_console_field_costs_the_word_not_the_frame(self):
        session = self.session()
        with mock.patch.object(
            speed_wire, "trial_console_field", side_effect=RuntimeError("boom")
        ):
            with environment(ARMED):
                action, console = self.act_capturing_console(session)
        # ~~the word, not the frame~~ -- there is no frame on this route any
        # more (`COO-DECISION 20260904_0345` item 2), so what this pins now is
        # the half that still matters and is still the point: a raising
        # DIAGNOSTIC never alters dispatch.  The route reaches the same
        # refusal it reaches with a healthy console, and the refusal line is
        # still printed.
        self.assertIsNotNone(action)
        self.assertEqual(
            action[0], chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL
        )
        self.assertIn("GM_CHAT_NO_BYTES_SENT", console)

    def test_unavailable_is_its_own_word_not_one_of_the_gates_two(self):
        self.assertNotIn(
            chat_command_action.SPEED_TRIAL_UNAVAILABLE,
            (speed_wire.TRIAL_UNSET, speed_wire.TRIAL_MALFORMED),
        )

    def test_a_console_that_cannot_be_written_does_not_change_the_verdict(self):
        # ~~still lets the frame out~~ -- no frame leaves this route now.  The
        # property is unchanged and still worth pinning in the other
        # direction: a printer that could veto would be a second, invisible
        # gate, and a printer that could RESCUE would be one too.  With
        # stderr unusable the route reaches the same refusal verdict.
        session = self.session()
        with mock.patch.object(chat_command_action.sys, "stderr", None):
            with environment(ARMED):
                action = self.act(session)
        self.assertIsNotNone(action)
        self.assertEqual(
            action[0], chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL
        )


class TheWordsAGraderGrepsAreLiteralsTests(_Case):
    """The console token and the env name are read by humans and by greps."""

    def test_the_env_variable_is_named_exactly_as_the_decision_wrote_it(self):
        self.assertEqual(speed_wire.SPEED_TRIAL_ENV, "PF_SPEED_TRIAL")

    def test_the_console_token_is_two_ascii_words_and_a_third(self):
        token = chat_command_action.SPEED_TRIAL_CONSOLE_TOKEN
        self.assertEqual(token, "SPEED TRIAL OPEN")
        token.encode("ascii")

    def test_the_three_state_words_are_ascii_and_space_free(self):
        for word in (
            speed_wire.TRIAL_UNSET,
            speed_wire.TRIAL_MALFORMED,
            speed_wire.TRIAL_ARMED,
            chat_command_action.SPEED_TRIAL_UNAVAILABLE,
        ):
            with self.subTest(word=word):
                word.encode("ascii")
                self.assertNotIn(" ", word)

    def test_the_two_tokens_cannot_be_confused_by_a_prefix_grep(self):
        # `SPEED DEFERRED` and `SPEED TRIAL OPEN` report opposite outcomes, so
        # neither may be a prefix of the other.
        deferred = chat_command_action.SPEED_DEFERRED_CONSOLE_TOKEN
        trial = chat_command_action.SPEED_TRIAL_CONSOLE_TOKEN
        self.assertFalse(deferred.startswith(trial))
        self.assertFalse(trial.startswith(deferred))


class TheKeyDoesNOTReopenTheLOGINDoorTests(_Case):
    """chief named this failure before it could happen; this is its pin.

    `login_speed.py`'s module docstring, point 3 (`wire_trial_only`, written
    after pf-adversary caught chief's own first draft in round `4lf2hl`, D1),
    states the trap in as many words: if this lane implemented COO `0646`'s
    trial by making `send_deferred()` answer `False`, then a login gated on
    `send_deferred()` alone would send WHATEVER THE ROW HOLDS -- and `/speed`
    writes its row even when the frame is withheld.  His worked example is the
    exact `GT-193` disaster: the trial opens for `400`, the tester types
    `/speed 300` (frame withheld, ROW WRITTEN), the ticket's own recovery step
    is a re-login, and `00 00 96 43` goes out.

    THIS LANE DID NOT IMPLEMENT IT THAT WAY -- `send_deferred()` is untouched
    and the key wraps the holds instead -- and that is a property, not a
    coincidence, so it is measured here rather than left to the two modules'
    comments agreeing with each other.  `login_speed.py` is chief's file and
    nothing here edits it; these tests only read it.
    """

    def test_send_deferred_is_still_true_with_the_key_armed(self):
        with environment(ARMED):
            self.assertTrue(
                speed_wire.send_deferred(),
                "the trial was implemented by flipping the deferral, which "
                "opens the login door login_speed.py point 3 holds shut",
            )

    def test_the_login_frame_still_carries_the_constant_after_a_trial_speed(self):
        # End to end: arm the key, send a `/speed`, then ask the resolver what
        # the NEXT login would put on the wire for that character.
        store = self.store()
        session = self.session(store)
        with environment(ARMED):
            action = self.act(session)
            # The wire door is shut (`0345` item 2) -- but the ROW still
            # moves, which is exactly the trap chief named: this test's whole
            # point is that a written row must not reach the login frame.
            # Closing the wire door makes that MORE important, not less.
            self.assertEqual(
                action[0],
                chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL,
            )
            resolved = login_speed.resolve_for_character(
                store, 1, fallback=CONSTANT
            )
        self.assertEqual(
            resolved.value,
            CONSTANT,
            "the row a trial /speed left behind reached the login frame",
        )
        # `WIRE_DEFERRED`, not `WIRE_TRIAL_ONLY`, and the difference IS the
        # result: `wire_trial_only` is the belt chief added for the OTHER
        # implementation shape -- the one that flips `send_deferred()` for the
        # session -- and it is never reached from here, because this lane did
        # not take that shape.  The plain deferral is what answers, exactly as
        # it did before this round existed.
        self.assertEqual(resolved.reason, login_speed.WIRE_DEFERRED)
        self.assertNotEqual(resolved.reason, login_speed.WIRE_TRIAL_ONLY)

    def test_the_row_really_did_move_so_the_test_above_is_not_vacuous(self):
        # Without this, the assertion above would pass on a route that never
        # wrote anything at all.
        store = self.store()
        session = self.session(store)
        with environment(ARMED):
            self.act(session)
        self.assertEqual(
            store.stored.get(chat_command_action.SPEED_TYPED_COLUMN), ARMED_F32
        )
        self.assertNotEqual(ARMED_F32, CONSTANT)


class TheKeyOpensNOTHINGABOVEItselfTests(_Case):
    """Every refusal that stands ABOVE the two holds still stands.

    COO `0646` opened ONE door: the two `/speed` holds, for one value.  It said
    nothing about the run-copy-DB gate, the version gate, or the identity read,
    and every one of those exists for a reason that has nothing to do with
    `GT-193`.  The key is read BELOW all of them on purpose; these tests are
    what stops a later round from "simplifying" it upward.

    The canonical-DB one is the expensive one to get wrong: it is the guard
    that stops `/speed` writing to the project's canonical database, and no
    environment variable an owner sets in a hurry may ever be a way around it.
    """

    def test_an_armed_key_does_not_reach_the_canonical_database(self):
        store = self.store()
        store.path = chat_command_action.CANONICAL_DB_FILENAME
        session = self.session(store)
        with environment(ARMED):
            action = self.act(session)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_CANONICAL_DB,
            session.events,
        )
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_TRIAL_ADMITTED, session.events
        )
        self.assertEqual(
            store.calls, [], "the canonical database was written to"
        )
        self.assertNotEqual(action[0], chat_command_action.SPEED_ACTION_LABEL)

    def test_an_armed_key_does_not_open_a_shut_version_gate(self):
        session = self.session()
        with mock.patch.object(
            attr_wire, "UPDATE_ATTR_VITAL_VERSION_CONFIRMED", None
        ):
            with environment(ARMED):
                action = self.act(session)
        self.assertIn(
            chat_command_action.EVENT_SPEED_WITHHELD_NO_VERSION, session.events
        )
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_TRIAL_ADMITTED, session.events
        )
        self.assertNotEqual(action[0], chat_command_action.SPEED_ACTION_LABEL)

    def test_an_armed_key_does_not_invent_a_selected_character(self):
        session = FakeSession(self.store())
        session.foundation.selected = None
        with environment(ARMED):
            action = self.act(session)
        self.assertIn(
            chat_command_action.EVENT_SPEED_NO_SELECTED_CHARACTER,
            session.events,
        )
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_TRIAL_ADMITTED, session.events
        )
        self.assertNotEqual(action[0], chat_command_action.SPEED_ACTION_LABEL)


class TheGateAdmitsTheROWNotTheTYPINGTests(_Case):
    """Which number the key is compared against, when the two can differ.

    WHY THIS CLASS EXISTS: mutating the production call site from
    `_trial_admits(stored)` to `_trial_admits(value)` left every other test in
    this file green.  It could not fail them, because in all of them the store
    echoes the typed number back and the two are the same float.  The
    divergence has to be MANUFACTURED to be measured, and it has to be
    measured, because the safety property is not "the owner typed the armed
    number" -- it is "the frame that leaves this process carries the armed
    number".  Those are the same sentence only while nothing between the two
    changes the value, and the f32 round trip already does.
    """

    def diverging_store(self, readback):
        store = self.store()
        store.readback = readback
        return store

    def test_a_row_that_holds_the_armed_value_is_admitted(self):
        # Typed 451, row holds 450.0, gate armed at 450: the frame will carry
        # 450.0, which is what the owner armed, so it goes.
        # ~~so it goes~~ -- it reaches the composer and is refused there
        # (`0345` item 2).  The property this class exists for is UNCHANGED
        # and still measured: which number the gate is compared against.  The
        # armed row is admitted PAST the gate (it gets to the composer at
        # all), where the row that holds something else is held BEFORE it --
        # the two outcomes are still distinguishable, and the next test is
        # the other half.
        store = self.diverging_store(ARMED_F32)
        session = self.session(store)
        with environment(ARMED):
            action = self.act(session, "/speed 451")
        self.assertIsNotNone(action)
        self.assertEqual(
            action[0], chat_command_action.SPEED_DENIED_NOTICE_ACTION_LABEL
        )
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_DEFERRED, session.events
        )
        self.assertTrue(
            [
                event
                for event in session.events
                if event.startswith(
                    chat_command_action
                    .EVENT_SPEED_PERSIST_COMPOSE_REFUSED_PREFIX
                )
            ],
            f"the armed row was held before the composer: {session.events!r}",
        )

    def test_a_row_that_holds_something_else_is_HELD_even_when_the_typing_matches(self):
        # THE DIRECTION THAT MATTERS.  Typed 450, gate armed at 450 -- but the
        # row holds 451.0, so the frame would carry a number nobody armed.  A
        # gate that read the TYPING would let that out.
        store = self.diverging_store(451.0)
        session = self.session(store)
        with environment(ARMED):
            action, console = self.act_capturing_console(session)
        self.assertIsNone(
            action,
            "a frame carrying a value the owner never armed left this process",
        )
        self.assertIn(chat_command_action.EVENT_SPEED_DEFERRED, session.events)
        self.assertNotIn(
            chat_command_action.EVENT_SPEED_TRIAL_ADMITTED, session.events
        )
        self.assertNoTrialLine(console)

    def test_the_console_reports_the_row_not_the_typing(self):
        # The `SPEED TRIAL OPEN` line is gone with the door (`0345` item 2 --
        # it sat below the compose so it could never claim bytes that did not
        # go out).  The half of this test that still has something to measure
        # is the half that was always the risk: the GM's own typing must not
        # reach the console on ANY outcome.
        store = self.diverging_store(ARMED_F32)
        session = self.session(store)
        with environment(ARMED):
            _action, console = self.act_capturing_console(session, "/speed 451")
        self.assertNotIn(chat_command_action.SPEED_TRIAL_CONSOLE_TOKEN, console)
        line = self.one_line_starting(console, "GM_CHAT_NO_BYTES_SENT")
        self.assertNotIn("451", line)


class TheGuardAroundTheTwoHoldsIsOneNotOverOneNameTests(_Case):
    """The AST shape of the wrapper, pinned for pf-adversary D6's own reason.

    The first draft of this round wrote `if speed_wire.send_deferred() and not
    trial_admitted:`, and `tests/test_gm_speed_denied_nine_paths.py::
    _assert_the_deferral_branch_holds_one_reason` went red -- correctly.  That
    pin exists because a second term in a hold's condition is invisible to
    every other guard in this module, and the AST cannot tell a term that
    WIDENS a hold from one that narrows it.

    Moving the key OUT of those conditions and into a wrapper keeps that pin
    intact, so this class owes the wrapper the same discipline: exactly one
    `not` over exactly one name.  A second reason folded in here could not
    hide a silent SEND (this branch is the withholding side), but it could
    hide a silent REFUSAL that reaches neither hold's audit word -- which is
    the same family of defect, one door along.
    """

    @staticmethod
    def _speed_action_tree():
        source = Path(chat_command_action.__file__).read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef) and node.name == "_speed_action":
                return node
        raise AssertionError("_speed_action is not in this module any more")

    def _the_wrapper(self):
        """The one `if` whose body holds BOTH `/speed` holds, or a failure."""
        function = self._speed_action_tree()
        found = []
        for node in ast.walk(function):
            if not isinstance(node, ast.If):
                continue
            calls = {
                getattr(child.func, "attr", None)
                for child in ast.walk(node.test)
                if isinstance(child, ast.Call)
            }
            body_calls = {
                getattr(child.func, "attr", None)
                for stmt in node.body
                if isinstance(stmt, ast.If)
                for child in ast.walk(stmt.test)
                if isinstance(child, ast.Call)
            }
            if calls:
                continue
            if {"send_deferred", "shape_cleared"} <= body_calls:
                found.append(node)
        self.assertEqual(
            len(found),
            1,
            "exactly one call-free `if` must enclose both /speed holds; "
            "found %d" % len(found),
        )
        return found[0]

    def test_the_wrapper_is_a_single_not_over_a_single_name(self):
        test = self._the_wrapper().test
        self.assertIsInstance(
            test,
            ast.UnaryOp,
            "the guard around both /speed holds is not a bare `not` -- a "
            "second reason folded in here reaches neither hold's audit word",
        )
        self.assertIsInstance(test.op, ast.Not)
        self.assertIsInstance(
            test.operand,
            ast.Name,
            "the guard's operand is not a plain local; the key must be read "
            "ONCE, above both holds, into a name both of them then share",
        )
        self.assertEqual(test.operand.id, "trial_admitted")

    def test_the_key_is_read_exactly_once_on_this_route(self):
        # Two reads could see two environments and produce the combination
        # neither hold was designed for.
        function = self._speed_action_tree()
        reads = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and getattr(node.func, "id", None) == "_trial_admits"
        ]
        self.assertEqual(len(reads), 1, "the runtime key is read %d times" % len(reads))

    def test_neither_hold_kept_a_second_term_in_its_own_condition(self):
        # The other half of pf-adversary D6, asserted from this side too, so
        # a future round cannot satisfy his pin by deleting his file.
        function = self._speed_action_tree()
        for node in ast.walk(function):
            if not isinstance(node, ast.If):
                continue
            names = {
                getattr(child.func, "attr", None)
                for child in ast.walk(node.test)
                if isinstance(child, ast.Call)
            }
            if "send_deferred" in names or "shape_cleared" in names:
                with self.subTest(line=node.lineno):
                    self.assertNotIsInstance(
                        node.test,
                        ast.BoolOp,
                        "a hold's condition at line %d grew a second term"
                        % node.lineno,
                    )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
