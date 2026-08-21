"""Runtime hookup for the HYP-PF-031 chat-triggered return-select push.

LOGOUT-CHAT-PUSH-001 is GT-033 variant C.  The attended GT-033 A/B is blocked
at the TRIGGER: the tester cannot click the client's HOME menu item, so the
client never sends LogoutVital 0x1B40 and the request-paired logout shapes
(PF-013 close, PF-028 return-select-first) can never fire.  The tester CAN
type into chat, and the chat-input trigger path is proven end to end by
HYP-PF-027.  This lane answers ONE accepted 34-byte ascii12 chat-input frame
by pushing the byte-identical hash-pinned HYP-PF-028 ReturnSelectServerVital
(0x709E) response UNSOLICITED -- no LogoutVital request, no ack, no close, no
write -- exactly once per session, so an attended run can observe whether the
response ALONE causes the client screen transition.  Nothing in the chat
request is read; a LogoutVital under this scenario is deliberately NOT
answered (named no-reply event) so the session asks exactly one question.
Wrong shapes, wrong sequences, repeat triggers, and every frame without the
opt-in scenario fail closed with no reply and no write, and
``production_allowed`` stays false everywhere.  No client has ever been shown
an unsolicited 0x709E push.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PAYLOAD_SIZE,
    CHAT_INPUT_PROBE_REQUEST_PCS,
    CHAT_INPUT_VITAL_ID,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.logout_hypothesis import (  # noqa: E402
    CHAT_PUSH_TRIGGER_CLASSIFICATION,
    CHAT_PUSH_TRIGGER_PAYLOAD_SIZE,
    CHAT_PUSH_TRIGGER_VITAL_ID,
    LOGOUT_POST_ACK_ACTION_NONE,
    LOGOUT_REQUEST_PCS,
    LOGOUT_RESPONSE_POLICY_CHAT_PUSH_RETURN_SELECT,
    RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256,
    RETURN_SELECT_SERVER_RESPONSE_FRAME_SIZE,
    RETURN_SELECT_SERVER_RESPONSE_PC_SHA256,
    RETURN_SELECT_SERVER_RESPONSE_PC_SIZE,
    load_logout_hypothesis_scenario,
    make_return_select_server_response,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    load_chat_input_hypothesis_scenario,
)


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
CHAT_PUSH_SCENARIO_PATH = (
    ROOT / "scenarios" / "logout_hypothesis_chat_push_return_select.json"
)
RETURN_SELECT_SCENARIO_PATH = (
    ROOT / "scenarios" / "logout_hypothesis_return_select_server.json"
)
CHAT_ECHO_SCENARIO_PATH = ROOT / "scenarios" / "chat_input_hypothesis_echo.json"

PUSH_EVENT = "logout_chat_push_hypothesis_return_select_pushed"
REPEAT_EVENT = "logout_chat_push_hypothesis_already_sent_no_reply"
NO_SELECTED_EVENT = "logout_chat_push_hypothesis_no_selected_no_reply"
WRONG_SEQUENCE_EVENT = "logout_chat_push_hypothesis_wrong_sequence_no_reply"
LOGOUT_NO_REPLY_EVENT = "logout_chat_push_hypothesis_logout_vital_no_reply"
EVENT_PREFIX = "logout_chat_push_hypothesis_"
ACTION_LABEL = "HYP_PF_031_LOGOUT_CHAT_PUSH_RETURN_SELECT_SERVER_UNSOLICITED"


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest().upper()


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class _RecordingTimerFactory:
    def __init__(self) -> None:
        self.scheduled: list[tuple[float, object]] = []

    def __call__(self, delay_seconds, callback):
        self.scheduled.append((delay_seconds, callback))
        return self


class LogoutChatPushRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.scenario = load_logout_hypothesis_scenario(CHAT_PUSH_SCENARIO_PATH)
        self.timer_factory = _RecordingTimerFactory()

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ----------------------------------------------------------

    def _state(self, login, *, scenario="chat_push", ready=True, select=True):
        if scenario == "chat_push":
            scenario = self.scenario
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            logout_hypothesis_scenario=scenario,
            close_timer_factory=self.timer_factory,
        )
        state = state_type(login)
        # A transport close lever is always attached so the request-paired
        # profiles used as controls can run their own full shape; the chat
        # push itself must never pull it (asserted via timer_factory).
        state.attach_transport_socket_closer(lambda: None)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(login)
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        if select:
            characters = self.store.list_characters(state.foundation.account_id)
            actions = state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(characters[-1].selector)
            ))
            self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = ready
        return state

    def _trigger(self):
        return self.legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])

    def _session_closed_at(self, session_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
            ).fetchone()
        self.assertIsNotNone(row)
        return row["closed_at"]

    def _table_counts(self):
        db = sqlite3.connect(str(self.db_path))
        try:
            names = [row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            return {
                name: db.execute(
                    'SELECT COUNT(*) FROM "%s"' % name).fetchone()[0]
                for name in names
            }
        finally:
            db.close()

    def _refused(self, state, parsed, event):
        before = state.logout_chat_push_count
        out = state.dispatch(parsed)
        self.assertEqual(out, [])
        self.assertEqual(state.logout_chat_push_count, before)
        self.assertTrue(
            any(e.startswith(event) for e in state.events),
            state.events[-3:],
        )

    # ----- scenario / profile ----------------------------------------------

    def test_scenario_profile_fields(self):
        self.assertEqual(
            self.scenario.response_policy,
            LOGOUT_RESPONSE_POLICY_CHAT_PUSH_RETURN_SELECT,
        )
        self.assertEqual(
            self.scenario.post_ack_action, LOGOUT_POST_ACK_ACTION_NONE,
        )
        self.assertEqual(self.scenario.close_delay_ms, 0)
        self.assertEqual(self.scenario.hypothesis_id, "HYP-PF-031")
        self.assertEqual(
            self.scenario.scenario_id,
            "logout_hypothesis_chat_push_return_select",
        )

    def test_trigger_constants_are_pinned_against_the_chat_module(self):
        # The logout module copies the trigger id rather than importing the
        # neighbouring lane (the HYP-PF-027 rule); this binding is what keeps
        # the copy from drifting silently.
        self.assertEqual(CHAT_PUSH_TRIGGER_VITAL_ID, CHAT_INPUT_VITAL_ID)
        self.assertEqual(
            CHAT_PUSH_TRIGGER_PAYLOAD_SIZE, CHAT_INPUT_PAYLOAD_SIZE,
        )
        self.assertEqual(CHAT_PUSH_TRIGGER_CLASSIFICATION, "ascii12")

    # ----- the accepted trigger --------------------------------------------

    def test_one_trigger_pushes_exactly_the_pinned_frame_once(self):
        state = self._state("cp01")
        expected = make_return_select_server_response(self.legacy)
        actions = state.dispatch(self._trigger())
        self.assertEqual(actions, [
            (ACTION_LABEL, expected[0], expected[1], 0.0),
        ])
        self.assertEqual(len(actions[0][1]), RETURN_SELECT_SERVER_RESPONSE_PC_SIZE)
        self.assertEqual(
            len(actions[0][2]), RETURN_SELECT_SERVER_RESPONSE_FRAME_SIZE,
        )
        self.assertEqual(
            _sha(actions[0][1]), RETURN_SELECT_SERVER_RESPONSE_PC_SHA256,
        )
        self.assertEqual(
            _sha(actions[0][2]), RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256,
        )
        self.assertEqual(
            actions[0][2], self.legacy.frame_pc(bytes(actions[0][1])),
        )
        self.assertEqual(state.events.count(PUSH_EVENT), 1)
        self.assertEqual(state.logout_chat_push_count, 1)

    def test_the_push_is_one_shot(self):
        state = self._state("cp02")
        first = state.dispatch(self._trigger())
        self.assertEqual(len(first), 1)
        again = state.dispatch(self._trigger())
        self.assertEqual(again, [])
        self.assertEqual(state.events.count(REPEAT_EVENT), 1)
        self.assertEqual(state.events.count(PUSH_EVENT), 1)
        self.assertEqual(state.logout_chat_push_count, 1)

    def test_the_push_touches_no_database_row_and_no_socket(self):
        state = self._state("cp03")
        session_id = state.foundation.session_id
        before = self._table_counts()
        actions = state.dispatch(self._trigger())
        self.assertEqual(self._table_counts(), before)
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertFalse(state.logout_acknowledged)
        self.assertTrue(all(len(action) == 4 for action in actions))
        self.assertEqual(self.timer_factory.scheduled, [])

    # ----- the refusal ladder ----------------------------------------------

    def test_wrong_text_bytes_fail_closed(self):
        state = self._state("cp04")
        pc = bytearray(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        pc[-1] ^= 0xFF
        self._refused(
            state, self.legacy.parse_outer(bytes(pc)), EVENT_PREFIX,
        )

    def test_no_selected_character_fails_closed(self):
        state = self._state("cp05", select=False)
        self._refused(state, self._trigger(), NO_SELECTED_EVENT)

    def test_not_yet_runtime_ready_fails_closed(self):
        state = self._state("cp06", ready=False)
        self._refused(state, self._trigger(), WRONG_SEQUENCE_EVENT)

    # ----- LogoutVital under this scenario is deliberately unanswered -------

    def test_logout_vital_is_no_reply_by_name_with_no_write(self):
        state = self._state("cp07")
        session_id = state.foundation.session_id
        for subcode in (1, 3):
            self.assertEqual(
                state.dispatch(
                    self.legacy.parse_outer(LOGOUT_REQUEST_PCS[subcode])
                ),
                [],
            )
        self.assertEqual(state.events.count(LOGOUT_NO_REPLY_EVENT), 2)
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertFalse(state.logout_acknowledged)
        self.assertEqual(state.logout_ack_count, 0)
        self.assertEqual(self.timer_factory.scheduled, [])

    def test_logout_vital_stays_no_reply_even_after_the_push(self):
        state = self._state("cp08")
        self.assertEqual(len(state.dispatch(self._trigger())), 1)
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(LOGOUT_REQUEST_PCS[1])),
            [],
        )
        self.assertEqual(state.events.count(LOGOUT_NO_REPLY_EVENT), 1)
        self.assertFalse(state.logout_acknowledged)

    # ----- containment ------------------------------------------------------

    def test_with_the_scenario_absent_nothing_composes(self):
        state = self._state("cp09", scenario=None)
        expected = make_return_select_server_response(self.legacy)
        actions = state.dispatch(self._trigger())
        labels = [row[0] for row in actions]
        self.assertFalse(
            any(label.startswith("HYP_PF_031") for label in labels), labels,
        )
        self.assertFalse(
            {bytes(row[1]) for row in actions} & {expected[0]},
        )
        self.assertFalse(
            any(event.startswith(EVENT_PREFIX) for event in state.events),
        )

    def test_other_logout_scenarios_never_push_on_chat(self):
        scenario = load_logout_hypothesis_scenario(RETURN_SELECT_SCENARIO_PATH)
        state = self._state("cp10", scenario=scenario)
        actions = state.dispatch(self._trigger())
        labels = [row[0] for row in actions]
        self.assertFalse(
            any(label.startswith("HYP_PF_031") for label in labels), labels,
        )
        self.assertFalse(
            any(event.startswith(EVENT_PREFIX) for event in state.events),
        )
        # And that scenario's own request-paired behavior is untouched.
        logout_actions = state.dispatch(
            self.legacy.parse_outer(LOGOUT_REQUEST_PCS[1])
        )
        self.assertEqual(
            [label for label, *_ in logout_actions],
            [
                "HYP_PF_028_LOGOUT_SUBCODE01_RETURN_SELECT_SERVER_"
                "RESPONSE_FIRST",
                "HYP_PF_028_LOGOUT_SUBCODE01_ACK_THEN_SERVER_SOCKET_CLOSE",
            ],
        )

    def test_the_chat_keyed_lanes_stay_mutually_exclusive(self):
        chat_scenario = load_chat_input_hypothesis_scenario(
            CHAT_ECHO_SCENARIO_PATH,
        )
        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                logout_hypothesis_scenario=self.scenario,
                chat_input_hypothesis_scenario=chat_scenario,
            )

    def test_the_other_lane_counters_never_move(self):
        state = self._state("cp11")
        state.dispatch(self._trigger())
        self.assertEqual(state.chat_input_echo_count, 0)
        self.assertEqual(state.channel_message_sweep_count, 0)
        self.assertEqual(state.stats_progression_sweep_count, 0)
        self.assertEqual(state.npc_hostile_sweep_count, 0)
        self.assertEqual(state.logout_ack_count, 0)

    # ----- the exact scenario allowlist -------------------------------------

    def test_scenario_allowlist_is_exact(self):
        data = json.loads(
            CHAT_PUSH_SCENARIO_PATH.read_text(encoding="utf-8")
        )
        loaded = load_logout_hypothesis_scenario(CHAT_PUSH_SCENARIO_PATH)
        self.assertEqual(loaded.hypothesis_id, "HYP-PF-031")
        for mutate in (
            lambda d: d.__setitem__("production_allowed", True),
            lambda d: d.__setitem__("test_only", False),
            lambda d: d["entry"].__setitem__("response_policy", "ack_only"),
            lambda d: d["entry"].__setitem__("one_shot", False),
            lambda d: d["entry"].__setitem__("post_ack_action", "close_socket"),
            lambda d: d["entry"].__setitem__(
                "logout_vital_policy", "answer_with_the_pf012_ack",
            ),
            lambda d: d["entry"].pop("trigger"),
            lambda d: d["requests"]["chat_trigger"].__setitem__(
                "vital_id", 0x1B40,
            ),
            lambda d: d["composed_responses"]["chat_push_return_select"]
            .__setitem__("pc_sha256", "00" * 32),
            lambda d: d["composed_responses"]["chat_push_return_select"]
            .__setitem__("frame_size", 46),
            lambda d: d["persisted_post_state"].__setitem__(
                "database_write", "sessions_closed_at",
            ),
        ):
            tampered_data = json.loads(json.dumps(data))
            mutate(tampered_data)
            tampered = Path(self.tmp.name) / "tampered.json"
            tampered.write_text(json.dumps(tampered_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_logout_hypothesis_scenario(tampered)


if __name__ == "__main__":
    unittest.main()
