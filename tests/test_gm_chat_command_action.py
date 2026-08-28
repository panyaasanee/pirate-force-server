"""LANE-GM: the chat line -> outbound ACTION half (`gm/chat_command_action.py`).

`tests/test_gm_chat_command.py` proves the READ half: a GM's chat line is
authorized, decoded and audited, and a non-GM's is not.  This file proves the
SEND half, which is the one that decides whether anything happens on screen:

1. THE SAFETY GATE IS REAL, NOT DECORATIVE.  With
   `FORCE_POS_VITAL_VERSION_CONFIRMED = None` (today, RE-129 open) a valid
   `/warp` from a real GM must produce NO action and a named event.  GT-101
   measured what an unproven vital version does to a real client -- modal
   error, connection halted, socket closed -- so "we composed the frame
   anyway and someone will notice later" is the failure this file exists to
   make impossible.
2. THE PATH ACTUALLY WORKS once that one byte is known.  With the constant
   patched to a value, the same chat line must yield a real
   `(label, pc, frame, delay)` action whose bytes are the ForcePos frame the
   pinned composer builds -- so the day RE-129 answers, the change is that
   constant and nothing else.
3. NOTHING ESCAPES.  The call site is chief's dispatch on the game-listener
   thread, shared by every player.  Every hostile session shape below must
   come back as None plus an event, never as an exception.
4. THE PERMISSION STORY SURVIVES THE NEW PATH.  A non-GM typing the exact
   command that works for a GM gets no action, no audit row, and nothing
   decoded -- the allowlist is checked before the payload is read, on this
   path too.
"""
from __future__ import annotations

import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import accounts as gm_accounts  # noqa: E402
from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import teleport_wire  # noqa: E402
from pirateforce_foundation.gm.commands import GmCommand  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

# A value that is NOT the real one -- RE-129 has not answered.  Tests that
# need the gate open patch this in explicitly so no test can accidentally
# read as evidence about the real client's accepted version.
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


class FakeFoundation:
    def __init__(self, selected=None):
        self.selected = selected


class FakeSession:
    """The three attributes the module is allowed to read, and nothing else.

    Deliberately not a runtime session: if this module ever starts reaching
    for a fourth attribute, these tests must fail rather than quietly work
    because a real session happened to have it.
    """

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
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def act(self, session, text, **kwargs):
        return chat_command_action.make_gm_chat_command_action(
            session,
            make_chat_payload(text),
            self.legacy,
            config_path=str(self.config_path),
            log_path=str(self.log_path),
            **kwargs,
        )

    def log_records(self):
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def open_the_version_gate(self):
        return mock.patch.object(
            teleport_wire,
            "FORCE_POS_VITAL_VERSION_CONFIRMED",
            UNPROVEN_TEST_VERSION,
        )


class VersionGateTests(_Case):
    def test_the_shipped_constant_is_still_none_so_no_bytes_can_go_out(self):
        # If this ever fails without RE-129 being answered and cited in
        # teleport_wire.py's own comment, someone guessed the byte GT-101
        # measured as session-killing.
        self.assertIsNone(teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED)

    def test_a_valid_gm_warp_yields_no_action_while_the_version_is_unknown(self):
        session = FakeSession(position=FakePosition(scene_id=2))
        action = self.act(session, "/warp 2 100 200")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_WARP_WITHHELD_NO_VERSION, session.events
        )

    def test_the_line_is_still_authorized_and_audited_while_withheld(self):
        # The audit half must not regress just because the send half is
        # gated: GT-127 is decided on this log.
        session = FakeSession(position=FakePosition(scene_id=2))
        self.act(session, "/warp 2 100 200")
        records = self.log_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["command"], "warp")
        self.assertFalse(records[0]["executed"])
        self.assertIn(
            f"{chat_command_action.EVENT_ACCEPTED_PREFIX}warp", session.events
        )


class WarpActionTests(_Case):
    def test_a_same_scene_warp_becomes_a_real_force_pos_action(self):
        session = FakeSession(position=FakePosition(scene_id=2, z=30.0))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 100 200")
        self.assertIsNotNone(action)
        label, pc, frame, delay = action
        self.assertEqual(label, chat_command_action.WARP_ACTION_LABEL)
        self.assertEqual(delay, 0.0)
        self.assertIsInstance(pc, (bytes, bytearray))
        self.assertIsInstance(frame, (bytes, bytearray))

    def test_the_bytes_are_the_pinned_composers_bytes_not_new_ones(self):
        # This module must never become a second place that knows how to
        # build ForcePos: it composes through warp_executor/teleport_wire or
        # not at all.
        session = FakeSession(position=FakePosition(scene_id=2, z=30.0))
        with self.open_the_version_gate():
            _label, pc, frame, _delay = self.act(session, "/warp 2 100 200")
        expected_pc, expected_frame = teleport_wire.make_force_pos_frame(
            self.legacy, UNPROVEN_TEST_VERSION, 100.0, 200.0, 30.0
        )
        self.assertEqual(bytes(pc), bytes(expected_pc))
        self.assertEqual(bytes(frame), bytes(expected_frame))

    def test_the_z_comes_from_the_connection_not_from_a_default(self):
        # The `warp` grammar carries no elevation; inventing one (0.0, say)
        # would drop the character through the floor or into the sky.
        session = FakeSession(position=FakePosition(scene_id=2, z=-12.5))
        with self.open_the_version_gate():
            _label, _pc, frame, _delay = self.act(session, "/warp 2 1 2")
        _pc2, expected = teleport_wire.make_force_pos_frame(
            self.legacy, UNPROVEN_TEST_VERSION, 1.0, 2.0, -12.5
        )
        self.assertEqual(bytes(frame), bytes(expected))

    def test_a_cross_scene_warp_is_refused_not_silently_hopped_in_place(self):
        # ForcePos carries no scene id (RE-090).  Sending an in-scene hop for
        # "go to scene 3" would look like a working warp that went nowhere.
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 3 100 200")
        self.assertIsNone(action)
        self.assertTrue(
            any(
                event.startswith(chat_command_action.EVENT_WARP_REFUSED_PREFIX)
                for event in session.events
            ),
            session.events,
        )

    def test_scene_only_warp_with_no_coordinates_is_refused(self):
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2")
        self.assertIsNone(action)
        self.assertTrue(
            any(
                event.startswith(chat_command_action.EVENT_WARP_REFUSED_PREFIX)
                for event in session.events
            ),
            session.events,
        )

    def test_a_gm_with_no_selected_character_gets_no_action(self):
        session = FakeSession(position=None)
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 100 200")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_WARP_NO_POSITION, session.events
        )

    def test_the_other_commands_parse_and_audit_but_send_nothing_yet(self):
        for text, name in (
            ("/say hello", "say"),
            ("/lv 5", "lv"),
            ("/item 1001 2", "item"),
            ("/npc on 7", "npc"),
            ("/spawn 42", "spawn"),
        ):
            with self.subTest(text=text):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(position=FakePosition(scene_id=2))
                with self.open_the_version_gate():
                    action = self.act(session, text)
                self.assertIsNone(action)
                self.assertIn(
                    f"{chat_command_action.EVENT_NO_WIRE_PATH_PREFIX}{name}",
                    session.events,
                )


class PermissionTests(_Case):
    def test_a_non_gm_typing_the_working_command_gets_no_action(self):
        session = FakeSession(token=self.PLAYER_ACCOUNT,
                              position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 100 200")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_REFUSED_PREFIX}{gm_dispatch.REFUSAL_NOT_GM}",
            session.events,
        )

    def test_a_non_gm_line_is_never_decoded_or_audited(self):
        session = FakeSession(token=self.PLAYER_ACCOUNT,
                              position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            self.act(session, "/warp 2 100 200")
        self.assertEqual(self.log_records(), [])
        # Nothing in the event trail may carry the sentence a player typed.
        for event in session.events:
            self.assertNotIn("warp 2 100 200", event)

    def test_ordinary_chat_from_a_gm_is_not_a_command(self):
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "just talking to the crew")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_REFUSED_PREFIX}{chat_command.REFUSAL_NOT_A_COMMAND}",
            session.events,
        )

    def test_the_payload_can_never_name_the_account_that_is_checked(self):
        # The identity is the session's authenticated token.  A payload that
        # spells out a GM name must not promote the player who sent it.
        session = FakeSession(token=self.PLAYER_ACCOUNT,
                              position=FakePosition(scene_id=2))
        payload = make_chat_payload("/warp 2 1 2", speaker=self.GM_ACCOUNT)
        with self.open_the_version_gate():
            action = chat_command_action.make_gm_chat_command_action(
                session,
                payload,
                self.legacy,
                config_path=str(self.config_path),
                log_path=str(self.log_path),
            )
        self.assertIsNone(action)
        self.assertEqual(self.log_records(), [])


class FailClosedTests(_Case):
    """Every one of these runs on the shared game-listener thread."""

    def test_a_session_with_no_token_is_a_named_refusal_not_a_crash(self):
        class NoToken:
            def __init__(self):
                self.events = []
                self.foundation = FakeFoundation(FakeSelected(FakePosition()))

        session = NoToken()
        action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)
        self.assertTrue(
            any(
                event.startswith(chat_command_action.EVENT_BAD_SESSION_PREFIX)
                for event in session.events
            ),
            session.events,
        )

    def test_a_str_subclass_token_is_rejected_before_the_allowlist(self):
        # accounts.is_gm_account closes the __eq__/__hash__ bypass; this path
        # must not be the one place a subclass gets in.
        class Sneaky(str):
            def __eq__(self, other):  # pragma: no cover - must never be called
                return True

            def __hash__(self):
                return hash(str(self))

        session = FakeSession(token=Sneaky(self.PLAYER_ACCOUNT),
                              position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)
        self.assertEqual(self.log_records(), [])
        # Asserting the SPECIFIC event, not merely "no action": relaxing this
        # module's own `type(token) is not str` to `isinstance` still ends in
        # None (handle_local_talk_chat repeats the check and raises, which the
        # outer catch turns into an `unexpected_ValueError` event), so a test
        # that only checked for None would pass against that mutation and
        # prove nothing about the check it claims to cover.
        self.assertTrue(
            any(
                event.startswith(chat_command_action.EVENT_BAD_SESSION_PREFIX)
                for event in session.events
            ),
            session.events,
        )

    def test_a_session_whose_events_list_raises_still_returns_none(self):
        class HostileEvents(list):
            def append(self, item):
                raise RuntimeError("console is on fire")

        session = FakeSession(position=FakePosition(scene_id=2))
        session.events = HostileEvents()
        with self.open_the_version_gate():
            action = self.act(session, "not a command")
        self.assertIsNone(action)

    def test_a_session_with_no_events_attribute_at_all_still_returns_none(self):
        class Bare:
            token = "GM_ONE"
            foundation = None

        action = self.act(Bare(), "/warp 2 1 2")
        self.assertIsNone(action)

    def test_a_composer_that_explodes_is_caught_and_named(self):
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate(), mock.patch.object(
            chat_command_action,
            "make_warp_force_pos_frame",
            side_effect=OverflowError("nope"),
        ):
            action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_WARP_REFUSED_PREFIX}OverflowError",
            session.events,
        )

    def test_an_exception_message_never_reaches_the_event_trail(self):
        # Exception text can embed client bytes and is a cp874 hazard on the
        # bridge console: type names only.
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate(), mock.patch.object(
            chat_command_action,
            "make_warp_force_pos_frame",
            side_effect=ValueError("ทดสอบ secret"),
        ):
            self.act(session, "/warp 2 1 2")
        for event in session.events:
            self.assertNotIn("secret", event)
            self.assertEqual(event, event.encode("ascii", "replace").decode())

    def test_an_authorization_helper_that_explodes_is_caught(self):
        session = FakeSession(position=FakePosition(scene_id=2))
        with mock.patch.object(
            chat_command_action,
            "handle_local_talk_chat",
            side_effect=MemoryError("boom"),
        ):
            action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_UNEXPECTED_PREFIX}MemoryError",
            session.events,
        )

    def test_a_hand_built_command_with_a_hostile_args_shape_is_refused(self):
        # `GmCommand` is a plain frozen dataclass -- "regardless of source"
        # is the threat model warp_executor already defends; this path must
        # not be the hole.
        class Liar(tuple):
            def __len__(self):
                raise AttributeError("gotcha")

        session = FakeSession(position=FakePosition(scene_id=2))
        outcome = chat_command.ChatCommandOutcome(
            authorized=True,
            command=GmCommand(name="warp", args=Liar(), raw="/warp"),
            text="/warp",
            refusal_reason=None,
        )
        with self.open_the_version_gate(), mock.patch.object(
            chat_command_action, "handle_local_talk_chat", return_value=outcome
        ):
            action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)


class EventNameContractTests(_Case):
    """The event strings themselves, pinned as literals.

    pf-adversary (round `gr2q9j`) measured that every other event assertion in
    this file compares the module's output against the module's own constant,
    so renaming any constant to anything at all left the suite green -- a
    tautology, not a test.  These names are read by graders (GT entries),
    by console greps and by whoever debugs an attended boot, so they are an
    interface.  Pin them here, once, as text.
    """

    EXPECTED = {
        "EVENT_ACCEPTED_PREFIX": "gm_chat_command_accepted_",
        "EVENT_REFUSED_PREFIX": "gm_chat_command_refused_",
        "EVENT_NO_WIRE_PATH_PREFIX": "gm_chat_command_no_wire_path_",
        "EVENT_BAD_SESSION_PREFIX": "gm_chat_command_bad_session_",
        "EVENT_BAD_PAYLOAD_PREFIX": "gm_chat_command_bad_payload_",
        "EVENT_WARP_NO_POSITION": "gm_chat_warp_no_current_position",
        "EVENT_WARP_REFUSED_PREFIX": "gm_chat_warp_refused_",
        "EVENT_UNEXPECTED_PREFIX": "gm_chat_command_unexpected_",
        "EVENT_WARP_WITHHELD_NO_VERSION": (
            "gm_chat_warp_withheld_no_confirmed_force_pos_vital_version_re129_open"
        ),
    }

    def test_every_event_name_is_the_literal_string_it_has_always_been(self):
        for name, literal in self.EXPECTED.items():
            with self.subTest(name=name):
                self.assertEqual(getattr(chat_command_action, name), literal)

    def test_every_event_name_is_ascii_for_the_cp874_bridge_console(self):
        # The label had this test; the event strings -- which are what
        # actually reach session.events and the console exporter -- did not.
        for name in self.EXPECTED:
            value = getattr(chat_command_action, name)
            with self.subTest(name=name):
                self.assertEqual(value, value.encode("ascii").decode())

    def test_this_route_and_the_hook_route_never_share_an_event_name(self):
        # Exactly one of the two may be wired at the 0xAC52 branch. If both
        # were, identical event names would make the double-wire look like
        # normal operation -- one typed command producing two audit rows and
        # two rate-limit charges, indistinguishable from a GM typing twice.
        from pirateforce_foundation.lane_hooks import lane_gm_chat_command

        for ours, theirs in (
            (chat_command_action.EVENT_ACCEPTED_PREFIX,
             lane_gm_chat_command.HOOK_EVENT_ACCEPTED_PREFIX),
            (chat_command_action.EVENT_REFUSED_PREFIX,
             lane_gm_chat_command.HOOK_EVENT_REFUSED_PREFIX),
        ):
            with self.subTest(ours=ours):
                self.assertNotEqual(ours, theirs)
                self.assertFalse(theirs.startswith(ours))
                self.assertFalse(ours.startswith(theirs))


class DeadGuardTests(_Case):
    """The `_current_position` guards, which no other test reaches.

    pf-adversary showed all three could be deleted with the suite still
    green.  Two are redundant with downstream validation; the `z is None`
    one is not -- it decides which event name the round emits.
    """

    def test_a_position_with_no_z_is_treated_as_absent_not_half_read(self):
        session = FakeSession(position=FakePosition(scene_id=2, z=None))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_WARP_NO_POSITION, session.events
        )

    def test_a_position_with_no_scene_id_is_treated_as_absent(self):
        session = FakeSession(position=FakePosition(scene_id=None))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_WARP_NO_POSITION, session.events
        )

    def test_a_session_with_no_foundation_is_treated_as_absent(self):
        class NoFoundation:
            token = "GM_ONE"

            def __init__(self):
                self.events = []

        session = NoFoundation()
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 1 2")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_WARP_NO_POSITION, session.events
        )


class ProductionCallShapeTests(_Case):
    """The three-argument call chief will actually write.

    Every other test in this file passes explicit `config_path=`/`log_path=`,
    so the shape that resolves both from CWD -- the one that decides where
    GT-127's verdict file lands -- ran zero times (pf-adversary defect 12).
    """

    def setUp(self):
        super().setUp()
        self.enterContext(
            mock.patch.dict(
                os.environ,
                {gm_accounts.ENV_OVERRIDE: str(self.config_path)},
            )
        )
        previous_cwd = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, previous_cwd)

    def test_the_default_argument_call_authorizes_and_audits(self):
        session = FakeSession(position=FakePosition(scene_id=2))
        action = chat_command_action.make_gm_chat_command_action(
            session, make_chat_payload("/warp 2 100 200"), self.legacy
        )
        # Version gate still shut, so no action -- but the audit half must
        # work through the production path, because that is GT-127's verdict.
        self.assertIsNone(action)
        landed = self.tmp / "capture" / "gm_command_log.ndjson"
        self.assertTrue(
            landed.is_file(),
            "the default log path resolves relative to CWD; GT-127 reads "
            "this file, so where it lands is part of the contract",
        )
        rows = [
            json.loads(line)
            for line in landed.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["command"], "warp")

    def test_the_default_argument_call_refuses_a_non_gm(self):
        session = FakeSession(token=self.PLAYER_ACCOUNT,
                              position=FakePosition(scene_id=2))
        action = chat_command_action.make_gm_chat_command_action(
            session, make_chat_payload("/warp 2 100 200"), self.legacy
        )
        self.assertIsNone(action)
        self.assertFalse((self.tmp / "capture").exists())


class ContractTests(_Case):
    def test_the_label_carries_TELEPORT_because_runtime_greps_for_it(self):
        # runtime.py:3653-3660 `_move_authority_note_server_moves` reopens the
        # move-authority grace window for exactly one reason: "the action it
        # queued carries TELEPORT in its label".  Without the substring, a GM
        # warp looks to that gate like an impossible client jump; it refuses
        # the reading, and -- since the baseline only advances on admitted
        # readings -- refuses every later one too, freezing the durable row
        # for the rest of the session and persisting the pre-warp point at
        # logout.  This is a cross-module contract expressed as a substring,
        # which is exactly the kind that rots silently; pin it.
        self.assertIn("TELEPORT", chat_command_action.WARP_ACTION_LABEL)

    def test_the_move_authority_gate_still_keys_on_that_substring(self):
        # The other half of the contract: if runtime.py ever stops keying on
        # "TELEPORT", this file should fail rather than keep asserting a rule
        # nobody enforces any more.
        source = (ROOT / "src/pirateforce_foundation/runtime.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('if action and "TELEPORT" in action[0]:', source)

    def test_the_action_shape_matches_what_runtime_appends(self):
        # runtime.py appends (label, pc, frame, delay_before) tuples; a
        # different arity would fail at the serve loop, not here.
        session = FakeSession(position=FakePosition(scene_id=2))
        with self.open_the_version_gate():
            action = self.act(session, "/warp 2 1 2")
        self.assertIsInstance(action, tuple)
        self.assertEqual(len(action), 4)
        self.assertIsInstance(action[0], str)
        self.assertIsInstance(action[3], float)

    def test_the_action_label_is_ascii_for_the_cp874_bridge_console(self):
        self.assertEqual(
            chat_command_action.WARP_ACTION_LABEL,
            chat_command_action.WARP_ACTION_LABEL.encode("ascii").decode(),
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
