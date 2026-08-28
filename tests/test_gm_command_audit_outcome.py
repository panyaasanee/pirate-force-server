"""CORE-REQUEST-GM-032 items 1-2: the audit row that says what BECAME of a
GM command, and the test that makes it impossible to ship the two states
looking the same.

WHY THIS FILE EXISTS, IN ONE MEASUREMENT.  `COO-DECISION 20260829_0041`
found that `capture/gm_command_log.ndjson` -- the file `GT-127` decides on --
answered "did the queueing really happen?" with a row written BEFORE any gate
was read.  Measured on main before this round: `/warp 2 100 200` typed with
`FORCE_POS_VITAL_VERSION_CONFIRMED = None` (nothing on the wire, RE-129 open)
and the same line typed with the gate open (a real ForcePos frame handed to
the runtime) produced byte-identical rows apart from the timestamp.  An audit
that cannot tell those apart is not an audit of anything an attended tester
cares about.

WHAT IS ASSERTED HERE AND WHAT IS DELIBERATELY NOT.  These tests pin that the
two states write DIFFERENT values, that a pair of rows is tied by one
`record_id`, and that the strongest word this lane may write today is
`composed` -- the frame exists and was handed back.  `queued` is reserved for
the day CORE-REQUEST-GM-032 item 3 lands (chief reporting back from
`actions = actions + [gm_action]`), and `test_queued_is_unreachable_until_the
_append_site_reports_back` fails the moment any lane file tries to write it
first.  Nothing here claims a byte reached a client; both gates are shut.
"""
from __future__ import annotations

import ast
import json
import pathlib
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import commands  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import login_scene_stage  # noqa: E402
from pirateforce_foundation.gm import say_wire  # noqa: E402
from pirateforce_foundation.gm import teleport_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

# Same disclaimer as every other file in this lane that opens a gate: NOT the
# real byte.  RE-129 has not answered, and a test constant must never be
# readable later as if it had.
UNPROVEN_TEST_VERSION = 7

# THE LANE'S WRITE ZONE, AS A ZONE AND NOT AS ONE DIRECTORY.  Round `xk4wmz`
# learned this the expensive way: pf-adversary put a gate-free composer in
# `lane_hooks/lane_gm_chat_command.py`, the whole suite stayed green, and the
# scan that was supposed to catch it only walked `gm/`.  Both halves, by glob,
# so a third hook module is covered on the day it is created.
LANE_SOURCE_FILES = sorted(
    (ROOT / "src/pirateforce_foundation/gm").rglob("*.py")
) + sorted(
    (ROOT / "src/pirateforce_foundation/lane_hooks").glob("lane_gm_*.py")
)

# The one file allowed to say the reserved word: it is where the word is
# defined and documented.
OUTCOME_QUEUED_DEFINITION_SITE = (
    ROOT / "src/pirateforce_foundation/gm/commands.py"
)


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
        self.id = 4242


class FakeFoundation:
    def __init__(self, selected=None):
        self.selected = selected


class FakeSession:
    def __init__(self, token="GM_ONE", position=None):
        self.token = token
        self.events = []
        self.foundation = FakeFoundation(FakeSelected(position))


class _Case(unittest.TestCase):
    GM_ACCOUNT = "GM_ONE"
    PLAYER_ACCOUNT = "DECKHAND"

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
        # The cross-scene half of `/warp` writes this file (round `gejldf`).
        # Named into the temp dir in every case, so no test can stage into
        # the checkout it is testing.
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

    def staged_login_scenes(self):
        if not self.login_scene_config_path.exists():
            return {}
        return json.loads(
            self.login_scene_config_path.read_text(encoding="utf-8")
        ).get("gm_login_scene", {})

    def log_records(self):
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def outcome_rows(self):
        return [
            row
            for row in self.log_records()
            if row.get("record") == commands.AUDIT_RECORD_OUTCOME
        ]

    def open_the_warp_gate(self):
        return mock.patch.object(
            teleport_wire,
            "FORCE_POS_VITAL_VERSION_CONFIRMED",
            UNPROVEN_TEST_VERSION,
        )


class TheTwoStatesAreDistinguishableTests(_Case):
    """Item 2, stated as the thing that was missing: same typed line, two
    different files."""

    LINE = "/warp 2 100 200"

    def _outcome_for_one_warp(self, gate_open):
        session = FakeSession(position=FakePosition(scene_id=2))
        if gate_open:
            with self.open_the_warp_gate():
                action = self.act(session, self.LINE)
        else:
            action = self.act(session, self.LINE)
        rows = self.outcome_rows()
        self.assertEqual(len(rows), 1, f"audit log: {self.log_records()}")
        return action, rows[0]["outcome"]

    def test_the_same_command_writes_a_different_value_on_each_side_of_the_gate(
        self,
    ):
        withheld_action, withheld_outcome = self._outcome_for_one_warp(False)
        self.assertIsNone(withheld_action)

        self.setUp()  # a clean log, so the second run is read on its own
        sent_action, sent_outcome = self._outcome_for_one_warp(True)
        self.assertIsNotNone(sent_action)

        # The whole point of the round, in one assertion.
        self.assertNotEqual(withheld_outcome, sent_outcome)
        self.assertEqual(
            withheld_outcome,
            chat_command_action.OUTCOME_WARP_WITHHELD_NO_VERSION,
        )
        self.assertEqual(sent_outcome, commands.OUTCOME_COMPOSED)
        # LITERALS, NOT JUST THE CONSTANTS.  pf-adversary mutated
        # `OUTCOME_COMPOSED` to "queued" and then to "sent" and the whole
        # 519-test GM suite stayed green, because every assertion compared the
        # row against the constant that had just been changed.  The file is
        # what GT-127 grades, so the file's own bytes are what gets pinned.
        self.assertEqual(sent_outcome, "composed")
        self.assertEqual(withheld_outcome, "withheld_force_pos_vital_version")

    def test_the_withheld_value_names_the_gate_that_is_shut(self):
        # An attended tester reading this file has to be able to go straight
        # to the open question, so the value carries the gate's name -- not
        # a bare "withheld", which would make RE-129 and RE-132 read alike.
        _, outcome = self._outcome_for_one_warp(False)
        self.assertTrue(outcome.startswith(commands.OUTCOME_WITHHELD_PREFIX))
        self.assertIn("force_pos_vital_version", outcome)

    def test_the_say_gate_and_the_warp_gate_do_not_write_the_same_word(self):
        session = FakeSession(position=FakePosition(scene_id=2))
        self.act(session, "/say all hands on deck")
        say_outcome = self.outcome_rows()[0]["outcome"]
        self.assertEqual(
            say_outcome, chat_command_action.OUTCOME_SAY_WITHHELD_NO_VERSION
        )
        self.assertNotEqual(
            say_outcome, chat_command_action.OUTCOME_WARP_WITHHELD_NO_VERSION
        )

    def test_a_command_with_no_wire_path_says_so_rather_than_nothing(self):
        session = FakeSession(position=FakePosition(scene_id=2))
        action = self.act(session, "/lv 40")
        self.assertIsNone(action)
        self.assertEqual(
            self.outcome_rows()[0]["outcome"],
            chat_command_action.OUTCOME_NO_WIRE_PATH,
        )


class PairingTests(_Case):
    def test_one_command_writes_one_issued_row_and_one_outcome_row(self):
        session = FakeSession(position=FakePosition(scene_id=2))
        self.act(session, "/warp 2 100 200")
        rows = self.log_records()
        self.assertEqual([row["record"] for row in rows], ["issued", "outcome"])
        self.assertEqual(rows[0]["record_id"], rows[1]["record_id"])
        # Same command, same account, on both halves: a reader must not have
        # to join through anything but `record_id`.
        for field in ("account", "command", "args", "raw"):
            self.assertEqual(rows[0][field], rows[1][field], field)

    def test_two_commands_make_two_pairs_that_do_not_cross(self):
        session = FakeSession(position=FakePosition(scene_id=2))
        self.act(session, "/warp 2 100 200")
        self.act(session, "/say all hands")
        rows = self.log_records()
        self.assertEqual(len(rows), 4)
        first, second = rows[0]["record_id"], rows[2]["record_id"]
        self.assertNotEqual(first, second)
        self.assertEqual(rows[1]["record_id"], first)
        self.assertEqual(rows[3]["record_id"], second)

    def test_a_refusal_before_the_audit_writes_neither_row(self):
        # A non-GM never reaches the log at all, so there is no half-pair to
        # interpret.  The invariant a reader depends on: every outcome row
        # has an issued row above it.
        session = FakeSession(
            token=self.PLAYER_ACCOUNT, position=FakePosition(scene_id=2)
        )
        self.assertIsNone(self.act(session, "/warp 2 100 200"))
        self.assertEqual(self.log_records(), [])

    def test_neither_row_ever_says_it_executed_anything(self):
        # `executed` was pinned on the issued row only, so a mutant setting
        # the OUTCOME row's `executed` to True survived the whole suite --
        # and GT-127 grades on `"executed": false`.  A reader would have
        # found one false and one true per command with nothing red.
        session = FakeSession(position=FakePosition(scene_id=2))
        self.act(session, "/warp 2 100 200")
        for row in self.log_records():
            with self.subTest(record=row["record"]):
                self.assertIs(row["executed"], False)

    def test_the_issued_row_keeps_every_field_it_already_had(self):
        # Additive, not a reshape: `GT-133`'s wire criterion and
        # `test_gm_commands.py` both read these names, and a round that
        # renamed one while adding the outcome row would break a queue entry
        # nobody would think to re-read.
        session = FakeSession(position=FakePosition(scene_id=2))
        self.act(session, "/warp 2 100 200")
        issued = self.log_records()[0]
        for field in ("ts", "account", "command", "args", "raw", "executed",
                      "note"):
            self.assertIn(field, issued)
        self.assertFalse(issued["executed"])


class AuditFailureIsFailClosedTests(_Case):
    def test_a_composed_frame_is_withheld_when_its_outcome_cannot_be_written(
        self,
    ):
        # `handle_local_talk_chat` already refuses to hand onward a command it
        # could not record AT ALL.  The same reasoning one row later: bytes
        # whose only trace says "a GM typed something" are bytes with no
        # audit trail, and this lane's whole permission story is the trail.
        session = FakeSession(position=FakePosition(scene_id=2))
        boom = OSError("disk full")
        with self.open_the_warp_gate(), mock.patch.object(
            chat_command_action, "log_gm_command_outcome", side_effect=boom
        ):
            action = self.act(session, "/warp 2 100 200")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_NOT_AUDITED_ACTION_WITHHELD,
            session.events,
        )
        self.assertIn(
            f"{chat_command_action.EVENT_OUTCOME_LOG_FAILED_PREFIX}OSError",
            session.events,
        )

    def test_the_withheld_warp_leaves_no_parked_target_behind(self):
        # The defect this closes: `_warp_action` parks the destination only
        # AFTER the frame exists, so that "no bytes went out" and "a target is
        # parked" can never disagree.  Withholding the composed action for an
        # audit failure is a NEW way to reach exactly that disagreement, and a
        # target left parked would let chief's confirmation token
        # (CORE-REQUEST-GM-031) match the player's next ordinary step against
        # a warp nobody sent.
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_warp_gate(), mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            side_effect=OSError("disk full"),
        ):
            self.assertIsNone(self.act(session, "/warp 2 100 200"))
        self.assertIsNone(getattr(session, "gm_last_warp_target", None))

    def test_a_withheld_say_does_not_clear_an_earlier_warps_target(self):
        # The clearing above must be tied to the command that PARKED the
        # target, not to "any withheld action".  A `/say` whose audit row
        # fails would otherwise delete the comparison a real, sent `/warp`
        # set up moments earlier -- a second bug wearing the first one's
        # clothes.
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_warp_gate():
            self.assertIsNotNone(self.act(session, "/warp 2 100 200"))
        parked = getattr(session, "gm_last_warp_target", None)
        self.assertIsNotNone(parked)
        with mock.patch.object(
            say_wire, "GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED",
            say_wire.CHANNEL_CODEC_VITAL_VERSION,
        ), mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            side_effect=OSError("disk full"),
        ):
            self.assertIsNone(self.act(session, "/say all hands"))
        # Not vacuous: the say really did compose and really was withheld for
        # the audit failure, which is the only path that could have cleared
        # the target.
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_NOT_AUDITED_ACTION_WITHHELD,
            session.events,
        )
        self.assertIs(getattr(session, "gm_last_warp_target", None), parked)

    def test_a_warp_that_is_audited_keeps_its_parked_target(self):
        # The control for the test above: the clearing must be tied to the
        # withholding, not to every warp.
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_warp_gate():
            self.assertIsNotNone(self.act(session, "/warp 2 100 200"))
        self.assertIsNotNone(getattr(session, "gm_last_warp_target", None))

    def test_the_failure_event_carries_a_type_name_and_not_the_message(self):
        # Exception messages embed the GM's typed text -- a cp874 console
        # hazard and a needless echo of client-supplied bytes, the same rule
        # every other refusal in this module follows.
        session = FakeSession(position=FakePosition(scene_id=2))
        secret = "disk full while writing /say ATTACK AT DAWN"
        with self.open_the_warp_gate(), mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            side_effect=OSError(secret),
        ):
            self.act(session, "/warp 2 100 200")
        self.assertFalse(
            [event for event in session.events if "ATTACK AT DAWN" in event]
        )

    def test_a_withheld_command_still_reports_the_audit_failure(self):
        # Nothing left to withhold (the gate already withheld it), but the
        # trail must not go quiet: "no outcome row" and "no command" look
        # identical in the file otherwise.
        session = FakeSession(position=FakePosition(scene_id=2))
        with mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            side_effect=OSError("disk full"),
        ):
            action = self.act(session, "/warp 2 100 200")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_OUTCOME_LOG_FAILED_PREFIX}OSError",
            session.events,
        )
        self.assertNotIn(
            chat_command_action.EVENT_OUTCOME_NOT_AUDITED_ACTION_WITHHELD,
            session.events,
        )

    def test_an_outcome_row_with_no_issued_id_is_refused_not_invented(self):
        # A fresh id here would produce an orphan pair that READS complete.
        # Worse than a missing row, so it is a named refusal instead.
        session = FakeSession(position=FakePosition(scene_id=2))
        real = chat_command.handle_local_talk_chat

        def strip_the_id(*args, **kwargs):
            outcome = real(*args, **kwargs)
            return chat_command.ChatCommandOutcome(
                authorized=outcome.authorized,
                command=outcome.command,
                text=outcome.text,
                refusal_reason=outcome.refusal_reason,
                record_id=None,
            )

        with self.open_the_warp_gate(), mock.patch.object(
            chat_command_action, "handle_local_talk_chat", strip_the_id
        ):
            action = self.act(session, "/warp 2 100 200")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_NO_RECORD_ID, session.events
        )
        self.assertEqual(self.outcome_rows(), [])


class HalfPairTests(_Case):
    """The third file state, named because a file with two documented
    meanings and three states is the hole this round set out to close.

    An `issued` row with no `outcome` row after it is reachable four ways
    (the outcome write failed, the module raised before the write point, no
    `record_id` came back, the process died between the appends).  A reader
    cannot tell which from the file -- but the one thing they must be able to
    conclude is pinned here: NOTHING WAS SENT.
    """

    def test_every_half_pair_path_withholds_the_action(self):
        cases = {
            "outcome write failed": mock.patch.object(
                chat_command_action,
                "log_gm_command_outcome",
                side_effect=OSError("disk full"),
            ),
            "raised before the write point": mock.patch.object(
                chat_command_action,
                "make_warp_force_pos_frame_with_target",
                side_effect=BaseException("not even an Exception"),
            ),
        }
        for name, patcher in cases.items():
            with self.subTest(path=name):
                self.setUp()
                session = FakeSession(position=FakePosition(scene_id=2))
                with self.open_the_warp_gate(), patcher:
                    try:
                        action = self.act(session, "/warp 2 100 200")
                    except BaseException:  # noqa: BLE001 - see below
                        # A BaseException escaping is itself "nothing was
                        # sent": no action was returned to the caller.
                        action = None
                self.assertIsNone(action)
                records = self.log_records()
                self.assertTrue(records, "the issued row should still be there")
                outcomes = [
                    row for row in records
                    if row["record"] == commands.AUDIT_RECORD_OUTCOME
                ]
                self.assertEqual(
                    outcomes, [], "this path is supposed to be a half-pair"
                )
                self.assertIsNone(
                    getattr(session, "gm_last_warp_target", None),
                    "a half-pair must not leave a target parked either",
                )


class StagedLoginSceneRowTests(_Case):
    """The cross-scene half of `/warp` (round `gejldf`) in the audit file.

    Two properties, and the second is the one that cost the design work:
    the row says `staged_login_scene` and NOT `composed` (nothing was put on
    the wire), and a command whose outcome row cannot be written takes its
    staged config entry back off disk -- because unlike every other outcome
    in this vocabulary, this one has already changed durable state by the
    time the write point is reached.
    """

    def test_a_cross_scene_warp_writes_the_staged_word_not_composed(self):
        session = FakeSession(position=FakePosition(scene_id=1))
        # Gate patched OPEN, to show the word does not come from a shut gate:
        # this command never reads the version gate at all.
        with self.open_the_warp_gate():
            self.assertIsNone(self.act(session, "/warp 3"))
        rows = self.outcome_rows()
        self.assertEqual(1, len(rows))
        # The literal, not the constant: round `nz0qt2` measured that every
        # assertion comparing a row to `commands.OUTCOME_*` survived mutating
        # the constant to "sent" with the whole suite green.
        self.assertEqual("staged_login_scene", rows[0]["outcome"])
        self.assertEqual(False, rows[0]["executed"])
        self.assertEqual({"GM_ONE": 3}, self.staged_login_scenes())

    def test_coordinates_that_cannot_be_honoured_get_their_own_word(self):
        session = FakeSession(position=FakePosition(scene_id=1))
        self.assertIsNone(self.act(session, "/warp 3 100 200"))
        rows = self.outcome_rows()
        self.assertEqual(1, len(rows))
        self.assertEqual("staged_login_scene_coords_ignored", rows[0]["outcome"])

    def test_a_stage_refused_by_the_allowlist_says_so(self):
        # Reachable only through a config edit between the authorization and
        # the stage; the word still has to be readable rather than a crash.
        session = FakeSession(position=FakePosition(scene_id=1))
        self.config_path.write_text(
            json.dumps({"gm_accounts": [self.GM_ACCOUNT]}), encoding="utf-8"
        )
        with mock.patch.object(
            login_scene_stage,
            "stage_login_scene",
            return_value=login_scene_stage.StageResult(
                False, login_scene_stage.REASON_CONFIG_UNREADABLE, 3, None
            ),
        ):
            self.assertIsNone(self.act(session, "/warp 3"))
        rows = self.outcome_rows()
        self.assertEqual("refused_stage_config_unreadable", rows[0]["outcome"])

    def test_an_unwritable_outcome_row_takes_the_staged_entry_back(self):
        session = FakeSession(position=FakePosition(scene_id=1))
        with mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            side_effect=OSError("disk full"),
        ):
            self.assertIsNone(self.act(session, "/warp 3"))
        # The issued row is on disk, the outcome row is not -- and the config
        # entry the command had already written is gone again.
        self.assertEqual([], self.outcome_rows())
        self.assertEqual({}, self.staged_login_scenes())
        self.assertIn(
            f"{chat_command_action.EVENT_OUTCOME_LOG_FAILED_PREFIX}OSError",
            session.events,
        )

    def test_an_undo_that_fails_is_named_rather_than_silent(self):
        session = FakeSession(position=FakePosition(scene_id=1))
        with mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            side_effect=OSError("disk full"),
        ), mock.patch.object(
            login_scene_stage, "restore_login_scene", return_value=False
        ):
            self.assertIsNone(self.act(session, "/warp 3"))
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_STAGE_NOT_REVERTED, session.events
        )
        # The entry really is still there -- the event is not decoration.
        self.assertEqual({"GM_ONE": 3}, self.staged_login_scenes())

    def test_an_undo_that_raises_is_reported_as_a_failed_undo(self):
        session = FakeSession(position=FakePosition(scene_id=1))
        with mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            side_effect=OSError("disk full"),
        ), mock.patch.object(
            login_scene_stage,
            "restore_login_scene",
            side_effect=RuntimeError("no"),
        ):
            self.assertIsNone(self.act(session, "/warp 3"))
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_STAGE_NOT_REVERTED, session.events
        )


class VocabularyTests(unittest.TestCase):
    def test_an_unknown_outcome_is_refused_at_the_writer(self):
        command = commands.parse_gm_command("warp 2")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log.ndjson"
            with self.assertRaises(ValueError):
                commands.log_gm_command_outcome(
                    command,
                    "GM_ONE",
                    "everything_went_fine",
                    record_id="a" * 16,
                    log_path=str(path),
                )
            self.assertFalse(path.exists())

    def test_every_outcome_this_route_can_write_is_a_known_value(self):
        # The route spells its outcomes as its own constants; if one drifts
        # out of the vocabulary the writer would raise at runtime, on the
        # listener thread, on a real GM's command.  Caught here instead.
        for name in dir(chat_command_action):
            if not name.startswith("OUTCOME_"):
                continue
            value = getattr(chat_command_action, name)
            if not isinstance(value, str) or name.endswith("_PREFIX"):
                continue
            with self.subTest(name=name):
                self.assertTrue(
                    commands.is_known_outcome(value), f"{name}={value!r}"
                )

    def test_a_bare_prefix_with_no_reason_after_it_is_not_a_value(self):
        self.assertFalse(commands.is_known_outcome(commands.OUTCOME_REFUSED_PREFIX))
        self.assertFalse(
            commands.is_known_outcome(commands.OUTCOME_WITHHELD_PREFIX)
        )
        self.assertTrue(commands.is_known_outcome("refused_warp_ValueError"))


class QueuedIsReservedTests(unittest.TestCase):
    """The honest-token standard (COO-DECISION 20260829_0141 item 3), applied
    to the one word in this vocabulary that would over-claim."""

    def _referencing_files(self):
        found = []
        for path in LANE_SOURCE_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == "OUTCOME_QUEUED":
                    found.append((path, node.lineno))
                elif (
                    isinstance(node, ast.Attribute)
                    and node.attr == "OUTCOME_QUEUED"
                ):
                    found.append((path, node.lineno))
                elif (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and node.value == commands.OUTCOME_QUEUED
                ):
                    found.append((path, node.lineno))
        return found

    def test_queued_is_unreachable_until_the_append_site_reports_back(self):
        # `queued` may be written only when something OUTSIDE this lane has
        # confirmed the action was appended (CORE-REQUEST-GM-032 item 3,
        # runtime.py:5763).  Until that exists, no lane file may name it
        # except the definition site.  Deleting this test is the deliberate
        # act that day; drifting into it is not possible.
        offenders = [
            (path, line)
            for path, line in self._referencing_files()
            if path != OUTCOME_QUEUED_DEFINITION_SITE
        ]
        self.assertEqual(
            offenders,
            [],
            "a lane file names the reserved outcome `queued`; nothing in "
            "this lane can observe the append site, so nothing here may "
            "claim it",
        )

    def test_the_scan_actually_sees_the_word_it_claims_to_look_for(self):
        # A scanner that reads nothing passes the test above forever.  The
        # definition site really does contain the name, so it must appear.
        seen = {path for path, _ in self._referencing_files()}
        self.assertIn(OUTCOME_QUEUED_DEFINITION_SITE, seen)

    def test_the_scan_covers_both_halves_of_the_lanes_zone(self):
        # Round `xk4wmz`, probe G: a scan that walks only `gm/` misses the
        # lane's own hook modules, and the suite stays green while the lane
        # does the forbidden thing in the half nobody looks at.
        scanned = {path.name for path in LANE_SOURCE_FILES}
        self.assertIn("commands.py", scanned)
        self.assertIn("chat_command_action.py", scanned)
        self.assertTrue(
            [name for name in scanned if name.startswith("lane_gm_")],
            "the lane_hooks half of the zone fell out of the scan",
        )

    def test_the_word_is_named_for_the_day_it_lands_and_refused_until_then(
        self,
    ):
        # Reserved, not deleted: chief's item 3 has a name to write, and this
        # is the pin that says which one.
        self.assertEqual(commands.OUTCOME_QUEUED, "queued")
        # ...AND THE WRITER IS THE DOOR, NOT THE SOURCE SCAN.  pf-adversary
        # passed `AUDIT_OUTCOMES[-1]` from a lane hook file straight into the
        # writer and put `queued` in the ndjson with every test green: an AST
        # scan matches names and literals, and a tuple index is neither.  A
        # source-shaped scan cannot make an output-shaped guarantee.
        self.assertFalse(commands.is_known_outcome(commands.OUTCOME_QUEUED))
        self.assertNotIn(commands.OUTCOME_QUEUED, commands.AUDIT_OUTCOMES)

    def test_the_writer_refuses_the_reserved_word_by_every_route_in(self):
        command = commands.parse_gm_command("warp 2")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log.ndjson"
            # The constant, the bare literal, and the route the adversary
            # actually used (a value read out of the exported tuple rather
            # than spelled anywhere).  The last one is the reason the writer
            # has to be the door: no source scan sees it.
            for spelling in (
                commands.OUTCOME_QUEUED,
                "queued",
                "".join(["que", "ued"]),
            ):
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


class NoBytesWentOutTests(unittest.TestCase):
    def test_both_gates_are_still_shut_on_the_shipped_constants(self):
        # Every "composed" row in these tests came from a PATCHED gate.  If
        # this fails without an RE result and a COO-DECISION behind it,
        # someone opened a door while adding an audit field.
        self.assertIsNone(teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED)
        self.assertIsNone(say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED)


if __name__ == "__main__":
    unittest.main()
