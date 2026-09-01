"""Runtime hookup for HYP-PF-041 (LOGOUT-TEARDOWN-TIMER-VARIANT-001).

RE-189 branch 2 of Job 2 (pf_bridge/notes_to_chief/20260901_1635_LANE-A-
STATUS-chiefreply-consumed-adversary-reverify-corerequest-re189-branches23.md
section 3, approved by chief in
notes_to_chief/20260901_1658_CHIEF-REPLY-core-request-re189-branches-2-3-
lane-a-may-edit-again-under-same-spec.md) asks whether the post-ack close
DELAY itself matters to the real client -- GT-008 (2026-08-18) measured only
the one pinned value (250 ms) and found the client never notices the close
at all.  This file drives four new scenario profiles
(logout_hypothesis._PROFILE_TEARDOWN_TIMER_VARIANT_{0MS,2000MS,10000MS,
NEVER}) through the real dispatcher exactly like
tests/test_logout_ack_close.py already does for the pinned 250 ms shape --
no new response byte exists under any of the four: every ack pin reused here
is the unchanged HYP-PF-012 composition, and the only lever that changes is
the existing, already-wired close_delay_ms field (runtime.py:1952) or, for
the "never" variant, post_ack_action staying LOGOUT_POST_ACK_ACTION_NONE
(the unmodified echo shape).  No runtime.py edit was needed or made: both
fields were already generic before this round.  production_allowed stays
False everywhere; no default-boot behavior changes.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy  # noqa: E402
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.logout_hypothesis import (  # noqa: E402
    LOGOUT_ACK_FRAME_SHA256,
    LOGOUT_ACK_PC_SHA256,
    LOGOUT_CLOSE_DELAY_MS_VARIANT_0MS,
    LOGOUT_CLOSE_DELAY_MS_VARIANT_2000MS,
    LOGOUT_CLOSE_DELAY_MS_VARIANT_10000MS,
    LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
    LOGOUT_POST_ACK_ACTION_NONE,
    LOGOUT_REQUEST_PCS,
    load_logout_hypothesis_scenario,
    make_logout_ack_response,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
VARIANT_0MS_PATH = (
    ROOT / "scenarios" / "logout_hypothesis_teardown_timer_variant_0ms.json"
)
VARIANT_2000MS_PATH = (
    ROOT / "scenarios" / "logout_hypothesis_teardown_timer_variant_2000ms.json"
)
VARIANT_10000MS_PATH = (
    ROOT / "scenarios" / "logout_hypothesis_teardown_timer_variant_10000ms.json"
)
VARIANT_NEVER_PATH = (
    ROOT / "scenarios" / "logout_hypothesis_teardown_timer_variant_never.json"
)


class _RecordingTimerFactory:
    """Deterministic stand-in for the threading.Timer close schedule."""

    def __init__(self) -> None:
        self.scheduled: list[tuple[float, object]] = []

    def __call__(self, delay_seconds, callback):
        self.scheduled.append((delay_seconds, callback))
        return self

    def fire_all(self) -> None:
        for _delay, callback in self.scheduled:
            callback()


class _RecordingCloser:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


class _LogoutTeardownTimerVariantTestBase(unittest.TestCase):
    SCENARIO_PATH: Path
    EXPECTED_DELAY_MS: int

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.scenario = load_logout_hypothesis_scenario(self.SCENARIO_PATH)
        self.timer_factory = _RecordingTimerFactory()
        self.closer = _RecordingCloser()

    def tearDown(self):
        self.tmp.cleanup()

    def _state(self, login, *, attach_closer=True, ready=True):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            logout_hypothesis_scenario=self.scenario,
            close_timer_factory=self.timer_factory,
        )
        state = state_type(login)
        if attach_closer:
            state.attach_transport_socket_closer(self.closer)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        characters = self.store.list_characters(state.foundation.account_id)
        self.assertEqual(len(characters), 1)
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[0].selector)
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = ready
        return state

    def _session_closed_at(self, session_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
            ).fetchone()
        self.assertIsNotNone(row)
        return row["closed_at"]

    def _logout_parsed(self, subcode):
        return self.legacy.parse_outer(LOGOUT_REQUEST_PCS[subcode])


class LogoutTeardownTimerVariant0MsTests(_LogoutTeardownTimerVariantTestBase):
    SCENARIO_PATH = VARIANT_0MS_PATH
    EXPECTED_DELAY_MS = LOGOUT_CLOSE_DELAY_MS_VARIANT_0MS

    def test_scenario_loads_with_the_swept_delay(self):
        self.assertEqual(
            self.scenario.post_ack_action, LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
        )
        self.assertEqual(self.scenario.close_delay_ms, self.EXPECTED_DELAY_MS)
        self.assertEqual(self.scenario.hypothesis_id, "HYP-PF-041")

    def test_ack_then_close_scheduled_at_the_swept_delay(self):
        state = self._state("teardown-0ms")
        session_id = state.foundation.session_id
        expected_pc, expected_frame = make_logout_ack_response(self.legacy, 1)
        actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual(actions, [(
            "HYP_PF_013_LOGOUT_SUBCODE01_ACK_THEN_SERVER_SOCKET_CLOSE",
            expected_pc, expected_frame, 0.0,
        )])
        self.assertIsNotNone(self._session_closed_at(session_id))
        self.assertTrue(state.logout_close_scheduled)
        self.assertEqual(
            [delay for delay, _cb in self.timer_factory.scheduled],
            [self.EXPECTED_DELAY_MS / 1000.0],
        )
        self.assertEqual(self.closer.calls, 0)
        self.timer_factory.fire_all()
        self.assertEqual(self.closer.calls, 1)


class LogoutTeardownTimerVariant2000MsTests(_LogoutTeardownTimerVariantTestBase):
    SCENARIO_PATH = VARIANT_2000MS_PATH
    EXPECTED_DELAY_MS = LOGOUT_CLOSE_DELAY_MS_VARIANT_2000MS

    def test_scenario_loads_with_the_swept_delay(self):
        self.assertEqual(self.scenario.close_delay_ms, self.EXPECTED_DELAY_MS)

    def test_ack_then_close_scheduled_at_the_swept_delay(self):
        state = self._state("teardown-2000ms")
        actions = state.dispatch(self._logout_parsed(3))
        self.assertEqual(len(actions), 1)
        self.assertEqual(
            [delay for delay, _cb in self.timer_factory.scheduled],
            [self.EXPECTED_DELAY_MS / 1000.0],
        )
        self.timer_factory.fire_all()
        self.assertEqual(self.closer.calls, 1)


class LogoutTeardownTimerVariant10000MsTests(_LogoutTeardownTimerVariantTestBase):
    SCENARIO_PATH = VARIANT_10000MS_PATH
    EXPECTED_DELAY_MS = LOGOUT_CLOSE_DELAY_MS_VARIANT_10000MS

    def test_scenario_loads_with_the_swept_delay(self):
        self.assertEqual(self.scenario.close_delay_ms, self.EXPECTED_DELAY_MS)

    def test_ack_then_close_scheduled_at_the_swept_delay(self):
        state = self._state("teardown-10000ms")
        actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual(len(actions), 1)
        self.assertEqual(
            [delay for delay, _cb in self.timer_factory.scheduled],
            [self.EXPECTED_DELAY_MS / 1000.0],
        )
        self.timer_factory.fire_all()
        self.assertEqual(self.closer.calls, 1)


class LogoutTeardownTimerVariantNeverTests(_LogoutTeardownTimerVariantTestBase):
    SCENARIO_PATH = VARIANT_NEVER_PATH

    def test_scenario_loads_with_close_disabled(self):
        self.assertEqual(
            self.scenario.post_ack_action, LOGOUT_POST_ACK_ACTION_NONE,
        )
        self.assertEqual(self.scenario.hypothesis_id, "HYP-PF-041")

    def test_ack_only_no_close_ever_scheduled(self):
        state = self._state("teardown-never")
        expected_pc, expected_frame = make_logout_ack_response(self.legacy, 1)
        actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual(actions, [(
            "HYP_PF_012_LOGOUT_SUBCODE01_ACK_AFTER_CLEAN_CLOSE",
            expected_pc, expected_frame, 0.0,
        )])
        self.assertFalse(state.logout_close_scheduled)
        self.assertEqual(self.timer_factory.scheduled, [])
        self.assertEqual(self.closer.calls, 0)

    def test_missing_closer_does_not_matter_for_this_variant(self):
        # Unlike the three close_socket variants, this profile never needs
        # the transport lever at all -- attaching it is irrelevant to the
        # outcome, which the ack-close variants above are not (see
        # test_logout_ack_close.py's own
        # test_missing_transport_closer_fails_closed_with_no_write).
        state = self._state("teardown-never-nolever", attach_closer=False)
        actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual(len(actions), 1)
        self.assertEqual(self.timer_factory.scheduled, [])


class LogoutTeardownTimerVariantAllowlistTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _assert_every_mutation_rejected(self, path, mutations):
        data = json.loads(path.read_text(encoding="utf-8"))
        for mutate in mutations:
            tampered_data = json.loads(json.dumps(data))
            mutate(tampered_data)
            tampered = Path(self.tmp.name) / "tampered.json"
            tampered.write_text(json.dumps(tampered_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_logout_hypothesis_scenario(tampered)

    def test_0ms_variant_allowlist_is_exact(self):
        self._assert_every_mutation_rejected(
            VARIANT_0MS_PATH,
            (
                lambda d: d.__setitem__("production_allowed", True),
                lambda d: d["entry"].__setitem__("close_delay_ms", 250),
                lambda d: d["entry"].__setitem__("post_ack_action", "none"),
            ),
        )

    def test_2000ms_variant_allowlist_is_exact(self):
        self._assert_every_mutation_rejected(
            VARIANT_2000MS_PATH,
            (
                lambda d: d.__setitem__("production_allowed", True),
                lambda d: d["entry"].__setitem__("close_delay_ms", 250),
                lambda d: d["entry"].__setitem__("post_ack_action", "none"),
            ),
        )

    def test_10000ms_variant_allowlist_is_exact(self):
        self._assert_every_mutation_rejected(
            VARIANT_10000MS_PATH,
            (
                lambda d: d["entry"].__setitem__("close_delay_ms", 250),
                lambda d: d.__setitem__("hypothesis_id", "HYP-PF-013"),
            ),
        )

    def test_never_variant_allowlist_is_exact(self):
        self._assert_every_mutation_rejected(
            VARIANT_NEVER_PATH,
            (
                lambda d: d["entry"].__setitem__("post_ack_action", "close_socket"),
                lambda d: d["entry"].__setitem__("close_delay_ms", 0),
            ),
        )


if __name__ == "__main__":
    unittest.main()
