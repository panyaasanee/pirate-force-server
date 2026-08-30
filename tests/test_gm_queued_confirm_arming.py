"""CORE-REQUEST-GM-040 -- this lane's half of the append-site confirmation.

Chief's half landed first (`runtime.py`, `pirate-force-server#299`, merged
2026-08-30T10:47Z): right after `actions = actions + [gm_action]` it reads
`session._gm_action_queued_confirm`, a `(action, callback)` pair matched by
`is`, clears it, and calls the callback.  It is proven, on the real
dispatcher, by `test_gm_chat_command_dispatch_wiring.py::
ActionQueuedConfirmHookTests`, and nothing set the attribute until this
round -- chief's own letter called it "inert scaffolding".

This file proves the OTHER half: that `make_gm_chat_command_action` arms
that pair with the exact object it returns, and that the callback it hands
out writes the `queued` row `OUTCOME_QUEUED` has had reserved since
CORE-REQUEST-GM-032 item 3.

The two halves are proven to COMPOSE -- real lane, real runtime, a real row
on disk -- in `test_gm_chat_command_dispatch_wiring.py::
QueuedRowLandsEndToEndTests`.  This file is deliberately the offline half:
it can reach failure shapes (a session that refuses the attribute, a writer
that raises, a callback called twice) that the end-to-end cannot stage.
"""
from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import commands  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import teleport_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

# The fixtures below are the same shapes `test_gm_chat_command_action.py`
# uses, restated rather than imported: no test file in this suite imports
# another (checked), and a cross-import would make one file's collection
# depend on `tests/` being on `sys.path`, which differs between `unittest
# discover` and `unittest tests.<name>`.  Kept deliberately minimal -- these
# are the whole session surface `SessionSurfaceTests` allows, so a module
# that starts reaching past it fails here too instead of quietly working.
UNPROVEN_TEST_VERSION = 7


def make_chat_payload(message: str, speaker: str = "") -> bytes:
    """0xAC52 payload in the GT-006/GT-009 measured shape."""
    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


class FakePosition:
    def __init__(self, scene_id=2, x=10.0, y=20.0, z=30.0):
        self.scene_id = scene_id
        self.scene_seq = 0
        self.x = x
        self.y = y
        self.z = z


class FakeSelected:
    def __init__(self, position=None):
        self.position = position
        self.id = 41


class FakeFoundation:
    def __init__(self, selected=None):
        self.selected = selected


class FakeSession:
    def __init__(self, token="GM_ONE", position=None):
        self.token = token
        self.events = []
        self.foundation = FakeFoundation(FakeSelected(position))


class _ArmCase(unittest.TestCase):
    GM_ACCOUNT = "GM_ONE"

    def setUp(self):
        gm_dispatch.reset_rate_limit_state_for_tests()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.config_path = self.tmp / "gm_accounts.json"
        self.config_path.write_text(
            json.dumps({"gm_accounts": [self.GM_ACCOUNT]}), encoding="utf-8"
        )
        self.log_path = self.tmp / "capture" / "gm_command_log.ndjson"
        self.login_scene_config_path = self.tmp / "config" / "gm_login_scene.json"
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def act(self, session, text):
        return chat_command_action.make_gm_chat_command_action(
            session,
            make_chat_payload(text),
            self.legacy,
            config_path=str(self.config_path),
            log_path=str(self.log_path),
            login_scene_config_path=str(self.login_scene_config_path),
        )

    def rows(self):
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def outcomes(self):
        return [
            row["outcome"]
            for row in self.rows()
            if row["record"] == commands.AUDIT_RECORD_OUTCOME
        ]

    def open_the_version_gate(self):
        return mock.patch.object(
            teleport_wire,
            "FORCE_POS_VITAL_VERSION_CONFIRMED",
            UNPROVEN_TEST_VERSION,
        )

    def a_composed_warp(self, session=None):
        """One `/warp` that really composes a frame, with the gate patched."""
        session = session if session is not None else FakeSession(
            position=FakePosition(scene_id=2)
        )
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 100 200")
        self.assertIsNotNone(action, "fixture must compose, or it proves nothing")
        return session, action


class ArmingTests(_ArmCase):
    def test_the_pairing_names_the_exact_object_that_was_returned(self):
        # `is`, not `==`.  Chief's append site matches on identity, so an
        # equal-but-distinct copy parked here would never fire and would
        # fail SILENTLY -- no row, no event, nothing to grep.  This is the
        # single assertion the whole feature rests on.
        session, action = self.a_composed_warp()
        pending = session._gm_action_queued_confirm
        self.assertIs(pending[0], action)
        self.assertTrue(callable(pending[1]))

    def test_the_callback_writes_the_queued_row_the_lane_could_not_write(self):
        session, _ = self.a_composed_warp()
        self.assertEqual(self.outcomes(), [commands.OUTCOME_COMPOSED])
        session._gm_action_queued_confirm[1]()
        self.assertEqual(
            self.outcomes(),
            [commands.OUTCOME_COMPOSED, commands.OUTCOME_QUEUED],
        )

    def test_all_three_rows_share_one_record_id_and_keep_their_order(self):
        # The reason the pair carried meaning is the reason the triple does:
        # `issued` -> `composed` -> `queued` is the command's whole story,
        # and a reader takes the LAST outcome row, not "the" outcome row.
        session, _ = self.a_composed_warp()
        session._gm_action_queued_confirm[1]()
        rows = self.rows()
        self.assertEqual(
            [row["record"] for row in rows],
            [
                commands.AUDIT_RECORD_ISSUED,
                commands.AUDIT_RECORD_OUTCOME,
                commands.AUDIT_RECORD_OUTCOME,
            ],
        )
        self.assertEqual(len({row["record_id"] for row in rows}), 1)

    def test_the_queued_row_still_does_not_claim_execution(self):
        # `queued` is one rung above `composed` and still nowhere near
        # "the client saw it".  Nothing in this lane can observe a socket.
        session, _ = self.a_composed_warp()
        session._gm_action_queued_confirm[1]()
        queued = self.rows()[-1]
        self.assertEqual(queued["outcome"], commands.OUTCOME_QUEUED)
        self.assertFalse(queued["executed"])
        self.assertEqual(queued["account"], self.GM_ACCOUNT)
        self.assertEqual(queued["command"], "warp")

    def test_a_withheld_command_arms_nothing(self):
        # The version gate is SHUT here (shipped state), so `/warp` composes
        # nothing.  Arming anyway would leave a pairing on the session that
        # can never fire, and the next real command would have to report
        # overwriting it -- an anomaly event for a non-anomaly.
        session = FakeSession(position=FakePosition(scene_id=2))
        self.assertIsNone(self.act(session, "/warp 2 100 200"))
        self.assertFalse(hasattr(session, "_gm_action_queued_confirm"))

    def test_a_command_from_a_non_gm_arms_nothing(self):
        session = FakeSession(token="DECKHAND", position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            self.assertIsNone(self.act(session, "/warp 2 100 200"))
        self.assertFalse(hasattr(session, "_gm_action_queued_confirm"))

    def test_an_unaudited_command_arms_nothing_because_it_sends_nothing(self):
        # `_log_outcome` failing withholds the action (GM-032's fail-closed
        # rule).  The arming has to follow the action, not the composer:
        # a pairing for bytes that were deliberately dropped is a promise
        # to write `queued` for a command that will never be appended.
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            with mock.patch.object(
                chat_command_action,
                "log_gm_command_outcome",
                side_effect=OSError("disk gone"),
            ):
                self.assertIsNone(self.act(session, "/warp 2 100 200"))
        self.assertFalse(hasattr(session, "_gm_action_queued_confirm"))


class ArmingFailsSafeTests(_ArmCase):
    def test_a_session_that_refuses_the_attribute_still_gets_its_command(self):
        # A slotted session, a read-only proxy: the command is authorized,
        # composed and audited by the time we arm.  Losing the `queued` row
        # must not cost the GM the command itself.
        class Slotted:
            __slots__ = ("token", "events", "foundation")

            def __init__(self, inner):
                self.token = inner.token
                self.events = inner.events
                self.foundation = inner.foundation

        session = Slotted(FakeSession(position=FakePosition(scene_id=2)))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 100 200")
        self.assertIsNotNone(action)
        self.assertTrue(
            [
                event for event in session.events
                if event.startswith(
                    chat_command_action.EVENT_QUEUED_CONFIRM_NOT_ARMED_PREFIX
                )
            ],
            session.events,
        )

    def test_the_write_failed_event_carries_a_type_name_and_not_a_message(self):
        # Same rule as every other refusal in this module: an exception
        # message can embed the GM's typed text.
        session = FakeSession(position=FakePosition(scene_id=2))
        self.assertNotIn("disk gone", "".join(session.events))
        with self.open_the_version_gate():
            with mock.patch.object(
                chat_command_action,
                "log_gm_command_queued",
                side_effect=OSError("secret path /home/panya/x"),
            ):
                self.a_composed_warp(session)
                session._gm_action_queued_confirm[1]()
        joined = "".join(session.events)
        self.assertIn(
            f"{chat_command_action.EVENT_QUEUED_CONFIRM_WRITE_FAILED_PREFIX}OSError",
            joined,
        )
        self.assertNotIn("secret path", joined)

    def test_a_write_failure_after_the_append_withholds_nothing(self):
        # The asymmetry with `_log_outcome` is the point.  By the time this
        # callback runs the action is already in runtime.py's action list;
        # there is nothing left to take back, so the honest report is "it
        # went out and we could not record that", as an event.
        session, action = self.a_composed_warp()
        before = list(self.rows())
        with mock.patch.object(
            chat_command_action,
            "log_gm_command_queued",
            side_effect=OSError("full"),
        ):
            session._gm_action_queued_confirm[1]()
        self.assertEqual(self.rows(), before)
        self.assertIsNotNone(action)

    def test_a_second_call_is_refused_rather_than_writing_a_second_row(self):
        # Chief's hook clears the pairing before calling, so a second call
        # cannot come from him.  If one arrives, two `queued` rows for one
        # record_id would read like the command was appended twice.
        session, _ = self.a_composed_warp()
        confirm = session._gm_action_queued_confirm[1]
        confirm()
        confirm()
        self.assertEqual(
            self.outcomes(),
            [commands.OUTCOME_COMPOSED, commands.OUTCOME_QUEUED],
        )
        self.assertIn(
            chat_command_action.EVENT_QUEUED_CONFIRM_FIRED_TWICE, session.events
        )

    def test_overwriting_a_pending_pairing_is_named_not_silent(self):
        # By construction this should not happen: every action we arm for is
        # returned, and runtime.py appends what it is given.  A pairing still
        # sitting there when the next command arrives means one did not, and
        # that command's missing `queued` row needs a reason a reader can
        # find.
        session = FakeSession(position=FakePosition(scene_id=2))
        session._gm_action_queued_confirm = (("STALE",), lambda: None)
        self.a_composed_warp(session)
        self.assertIn(
            chat_command_action.EVENT_QUEUED_CONFIRM_OVERWROTE_PENDING,
            session.events,
        )
        # ...and the stale pairing is really gone, replaced by ours.
        self.assertNotEqual(session._gm_action_queued_confirm[0], ("STALE",))


class TheOldDoorIsStillShutTests(unittest.TestCase):
    """Nothing that guarded `queued` before this round was relaxed to land it.

    `QueuedIsReservedTests` in `test_gm_command_audit_outcome.py` owns these
    three pins.  They are restated here on purpose: this is the file that
    would be edited by someone widening the door, and a reader who arrives
    from the feature should meet the pins in the same place as the feature.
    """

    def test_the_general_writer_still_refuses_the_word(self):
        command = commands.parse_gm_command("warp 2")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log.ndjson"
            for spelling in (commands.OUTCOME_QUEUED, "queued", "que" + "ued"):
                with self.subTest(spelling=spelling):
                    with self.assertRaises(ValueError):
                        commands.log_gm_command_outcome(
                            command,
                            "GM_ONE",
                            spelling,
                            record_id="a" * 16,
                            log_path=str(path),
                        )
            self.assertFalse(path.exists())

    def test_the_vocabulary_predicate_still_says_no(self):
        self.assertFalse(commands.is_known_outcome(commands.OUTCOME_QUEUED))
        self.assertNotIn(commands.OUTCOME_QUEUED, commands.AUDIT_OUTCOMES)

    def test_the_new_writer_takes_no_outcome_parameter_at_all(self):
        # THE SHAPE IS THE GUARANTEE.  A keyword flag on the general writer
        # would be reachable by an accidental pass-through -- pf-adversary
        # got `queued` into the ndjson once through `AUDIT_OUTCOMES[-1]`,
        # and a source scan cannot see a tuple index.  A function with no
        # outcome parameter cannot be reached by a VALUE; only by a NAME,
        # which a reader sees and a scan can find.
        import inspect

        parameters = inspect.signature(commands.log_gm_command_queued).parameters
        self.assertNotIn("outcome", parameters)

    def test_only_the_confirmation_path_may_even_NAME_the_new_writer(self):
        # THE HOLE THIS CLOSES, found by running this round's own adversary
        # pass against itself.  `QueuedIsReservedTests`' AST scan forbids a
        # lane file from naming `OUTCOME_QUEUED` or the literal `queued`.
        # That scan is why the new writer hard-codes the word -- but it also
        # means the scan can no longer SEE a lane file that writes `queued`,
        # because such a file now only has to name a FUNCTION.  Before this
        # round no lane file could write the word at all; without this test
        # any of them could, and the guard that used to catch it would stay
        # green.  Same lesson as the `AUDIT_OUTCOMES[-1]` incident, one
        # level up: when the door moves, the scan has to move with it.
        offenders = []
        for path in sorted(
            (ROOT / "src/pirateforce_foundation/gm").rglob("*.py")
        ) + sorted(
            (ROOT / "src/pirateforce_foundation/lane_hooks").glob("lane_gm_*.py")
        ):
            if path.name in ("commands.py", "chat_command_action.py"):
                continue
            if "log_gm_command_queued" in path.read_text(encoding="utf-8"):
                offenders.append(path.name)
        self.assertEqual(
            offenders,
            [],
            "a lane file outside the append-site confirmation path names the "
            "`queued` writer; only the callback armed for a returned action "
            "has measured what that word claims",
        )

    def test_the_scan_above_actually_sees_the_name_it_looks_for(self):
        # A scanner that reads nothing passes the test above forever.
        source = (
            ROOT / "src/pirateforce_foundation/gm/chat_command_action.py"
        ).read_text(encoding="utf-8")
        self.assertIn("log_gm_command_queued", source)

    def test_the_new_writer_refuses_a_record_id_that_closes_nothing(self):
        command = commands.parse_gm_command("warp 2")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log.ndjson"
            for bad in ("", None):
                with self.subTest(record_id=bad):
                    with self.assertRaises(ValueError):
                        commands.log_gm_command_queued(
                            command, "GM_ONE", record_id=bad, log_path=str(path)
                        )
            with self.assertRaises(ValueError):
                commands.log_gm_command_queued(
                    command, "", record_id="a" * 16, log_path=str(path)
                )
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
