"""Runtime hookup for HYP-PF-042 (LOGOUT-ACK-FIRST-REORDER-001).

RE-189 Job 2, branch 3.  ``runtime.py``'s routing branch already composes
``make_logout_ack_response`` before ``make_return_select_server_response``
(the reverse of ``LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST`` -- chief's
round, CORE-REQUEST option (a), see the ``LOGOUT_RESPONSE_POLICY_
ACK_FIRST_REORDER`` constant comment and the ``RE_189_BRANCH3_...`` action
labels in ``runtime.py``).  Before this file's scenario existed, that branch
was provably unreachable: ``tests/test_logout_ack_first_reorder_routing_
wired.py`` (chief's own file) proves the wiring is correct with an in-memory
probe scenario AND proves the real ``require_logout_hypothesis_scenario``
allowlist refused any scenario carrying this ``response_policy``.  This file
is the other half: it drives the SAME dispatch path through the REAL,
on-disk, allowlisted scenario file
(``scenarios/logout_hypothesis_ack_first_reorder.json``) exactly the way
``tests/test_logout_teardown_timer_variant_scenario_wired.py`` does for
HYP-PF-041, with no mock and no patch anywhere in this file.

HYP-PF-042 IS NOT HYP-PF-041.  HYP-PF-041 (LOGOUT-TEARDOWN-TIMER-VARIANT-001)
is a sibling opened by the same CORE-REQUEST letter but is a different
hypothesis (the post-ack close-delay VALUE, not frame order) -- see the
``_PROFILE_ACK_FIRST_REORDER`` comment block in ``logout_hypothesis.py`` for
the full id-collision analysis.  HYP-PF-042 is NOT YET a registered entry in
``docs/HYPOTHESIS_LEDGER.json`` as of this round (a CORE-REQUEST accompanies
this round asking chief to register it, the same two-step pattern
HYP-PF-040/HYP-PF-041 both used); ``tools/verify_hypothesis_ledger.py`` still
passes unchanged (entries=49, same count as before this file's diff) because
no ``# PF-HYPOTHESIS-LEDGER: HYP-PF-042 active`` annotation line was added
anywhere -- that line is deliberately withheld until the ledger entry exists.

No byte is invented anywhere in this file: every ack pin and every
ReturnSelectServerVital pin reused here is the unchanged HYP-PF-012/
HYP-PF-028 composition, hash-checked against the same constants
``test_logout_ack_first_reorder_routing_wired.py`` and
``test_logout_return_select_hypothesis.py`` already check against.
``production_allowed`` stays ``False``; no default-boot behavior changes.
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
    LOGOUT_CLOSE_DELAY_MS,
    LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
    LOGOUT_RESPONSE_POLICY_ACK_FIRST_REORDER,
    LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST,
    LOGOUT_REQUEST_PCS,
    RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256,
    RETURN_SELECT_SERVER_RESPONSE_PC_SHA256,
    load_logout_hypothesis_scenario,
    make_logout_ack_response,
    make_return_select_server_response,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "logout_hypothesis_ack_first_reorder.json"
RETURN_SELECT_SCENARIO_PATH = (
    ROOT / "scenarios" / "logout_hypothesis_return_select_server.json"
)


class _RecordingTimerFactory:
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


def _sha(blob: bytes) -> str:
    import hashlib
    return hashlib.sha256(blob).hexdigest().upper()


class LogoutAckFirstReorderScenarioWiredTests(unittest.TestCase):
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
        self.scenario = load_logout_hypothesis_scenario(SCENARIO_PATH)
        self.timer_factory = _RecordingTimerFactory()
        self.closer = _RecordingCloser()

    def tearDown(self):
        self.tmp.cleanup()

    def _state(self, login, *, scenario=None, attach_closer=True, ready=True):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            logout_hypothesis_scenario=(
                scenario if scenario is not None else self.scenario
            ),
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

    def _default_state(self, login, **kwargs):
        """A state built exactly like ``_state`` but with NO logout
        hypothesis scenario at all -- the flagless default boot shape
        (``app.py`` passes ``None`` here whenever ``--logout-hypothesis-
        scenario`` is not given, which is every default boot)."""
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            logout_hypothesis_scenario=None,
            close_timer_factory=self.timer_factory,
        )
        state = state_type(login)
        state.attach_transport_socket_closer(self.closer)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        characters = self.store.list_characters(state.foundation.account_id)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[0].selector)
        ))
        state.runtime_ack_sent = True
        return state

    def _session_closed_at(self, session_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
            ).fetchone()
        return None if row is None else row["closed_at"]

    def _logout_parsed(self, subcode):
        return self.legacy.parse_outer(LOGOUT_REQUEST_PCS[subcode])

    # --- the scenario loads with the reordered policy -------------------

    def test_scenario_loads_with_the_reordered_policy(self):
        self.assertEqual(
            self.scenario.response_policy, LOGOUT_RESPONSE_POLICY_ACK_FIRST_REORDER,
        )
        self.assertEqual(
            self.scenario.post_ack_action, LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
        )
        self.assertEqual(self.scenario.close_delay_ms, LOGOUT_CLOSE_DELAY_MS)
        self.assertEqual(self.scenario.hypothesis_id, "HYP-PF-042")

    # --- real dispatch, no mock, ack goes out first ----------------------

    def test_subcode01_ack_first_then_return_select_through_real_dispatch(self):
        state = self._state("arfw01")
        session_id = state.foundation.session_id
        self.assertIsNone(self._session_closed_at(session_id))
        expected_ack = make_logout_ack_response(self.legacy, 1)
        expected_rss = make_return_select_server_response(self.legacy)
        actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual(actions, [
            (
                "RE_189_BRANCH3_LOGOUT_SUBCODE01_ACK_FIRST",
                expected_ack[0], expected_ack[1], 0.0,
            ),
            (
                "RE_189_BRANCH3_LOGOUT_SUBCODE01_RETURN_SELECT_SERVER_"
                "RESPONSE_THEN_SERVER_SOCKET_CLOSE",
                expected_rss[0], expected_rss[1], 0.0,
            ),
        ])
        self.assertEqual(_sha(actions[0][1]), LOGOUT_ACK_PC_SHA256[1])
        self.assertEqual(_sha(actions[0][2]), LOGOUT_ACK_FRAME_SHA256[1])
        self.assertEqual(
            _sha(actions[1][1]), RETURN_SELECT_SERVER_RESPONSE_PC_SHA256,
        )
        self.assertEqual(
            _sha(actions[1][2]), RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256,
        )
        self.assertIsNotNone(self._session_closed_at(session_id))
        self.assertTrue(state.logout_acknowledged)
        self.assertTrue(state.logout_close_scheduled)
        self.assertIn(
            "logout_hypothesis_subcode01_ack_before_return_select_response",
            state.events,
        )
        self.assertEqual(
            [delay for delay, _cb in self.timer_factory.scheduled],
            [LOGOUT_CLOSE_DELAY_MS / 1000.0],
        )
        self.assertEqual(self.closer.calls, 0)
        self.timer_factory.fire_all()
        self.assertEqual(self.closer.calls, 1)

    def test_subcode03_ack_first_then_return_select_through_real_dispatch(self):
        state = self._state("arfw03")
        expected_ack = make_logout_ack_response(self.legacy, 3)
        expected_rss = make_return_select_server_response(self.legacy)
        actions = state.dispatch(self._logout_parsed(3))
        self.assertEqual([label for label, *_ in actions], [
            "RE_189_BRANCH3_LOGOUT_SUBCODE03_ACK_FIRST",
            "RE_189_BRANCH3_LOGOUT_SUBCODE03_RETURN_SELECT_SERVER_"
            "RESPONSE_THEN_SERVER_SOCKET_CLOSE",
        ])
        self.assertEqual(actions[0][1:], (expected_ack[0], expected_ack[1], 0.0))
        self.assertEqual(actions[1][1:], (expected_rss[0], expected_rss[1], 0.0))

    def test_order_is_the_exact_reverse_of_return_select_first(self):
        """Same two pinned frames, opposite send order, side by side --
        driven through two REAL on-disk scenario files, no mock."""
        return_select_scenario = load_logout_hypothesis_scenario(
            RETURN_SELECT_SCENARIO_PATH
        )
        baseline_state = self._state(
            "arfw-baseline", scenario=return_select_scenario,
        )
        baseline_actions = baseline_state.dispatch(self._logout_parsed(1))
        reordered_state = self._state("arfw-reordered")
        reordered_actions = reordered_state.dispatch(self._logout_parsed(1))
        # return_select_first: [0x709E frame, ack frame]
        # ack_first_reorder:   [ack frame, 0x709E frame]
        self.assertEqual(baseline_actions[0][1], reordered_actions[1][1])
        self.assertEqual(baseline_actions[0][2], reordered_actions[1][2])
        self.assertEqual(baseline_actions[1][1], reordered_actions[0][1])
        self.assertEqual(baseline_actions[1][2], reordered_actions[0][2])

    def test_missing_transport_closer_still_fails_closed(self):
        state = self._state("arfw-nolever", attach_closer=False)
        session_id = state.foundation.session_id
        self.assertEqual(state.dispatch(self._logout_parsed(1)), [])
        self.assertIn(
            "logout_hypothesis_close_unavailable_no_reply", state.events,
        )
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertFalse(state.logout_acknowledged)
        self.assertEqual(self.timer_factory.scheduled, [])

    def test_wrong_sequence_fails_closed(self):
        state = self._state("arfw-seq", ready=False)
        session_id = state.foundation.session_id
        self.assertEqual(state.dispatch(self._logout_parsed(1)), [])
        self.assertIn("logout_hypothesis_wrong_sequence_no_reply", state.events)
        self.assertIsNone(self._session_closed_at(session_id))

    # --- unreachable from any default (flagless) boot --------------------

    def test_unreachable_from_a_default_boot_with_no_scenario_at_all(self):
        # app.py passes logout_hypothesis_scenario=None whenever
        # --logout-hypothesis-scenario is not given -- every default boot.
        # No RE_189_BRANCH3 action, no HYP_PF ack action, nothing at all:
        # the dispatcher's own gate (`if logout_hypothesis_scenario is not
        # None and nested_id == LOGOUT_VITAL_ID`) never even calls into the
        # logout hypothesis dispatch for this request.
        state = self._default_state("arfw-default")
        session_id = state.foundation.session_id
        actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual(
            [a for a in actions if a[0].startswith(("HYP_PF", "RE_189"))], [],
        )
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertFalse(state.logout_acknowledged)

    def test_default_boot_scenario_files_never_carry_this_policy(self):
        # Static proof over the whole scenarios/ directory, matching the
        # project's own "grep-based proof" convention for unreachable-by-
        # default branches: every OTHER shipped logout_hypothesis_*.json
        # file must not carry response_policy=ack_first_reorder -- only
        # this one, brand-new, explicitly-selected file does, and nobody is
        # selected by default.
        other_files = sorted(
            p for p in (ROOT / "scenarios").glob("logout_hypothesis_*.json")
            if p != SCENARIO_PATH
        )
        self.assertGreaterEqual(len(other_files), 9)
        for path in other_files:
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertNotEqual(
                    data.get("entry", {}).get("response_policy"),
                    LOGOUT_RESPONSE_POLICY_ACK_FIRST_REORDER,
                )

    def test_hypothesis_id_is_not_the_teardown_timer_variants_id(self):
        # Regression pin for the id-collision this module's own comment
        # block documents at length: HYP-PF-042 must never be HYP-PF-041.
        self.assertNotEqual(self.scenario.hypothesis_id, "HYP-PF-041")
        self.assertEqual(self.scenario.hypothesis_id, "HYP-PF-042")

    # --- isolation: unrelated, already-allowlisted scenarios untouched --

    def test_return_select_first_branch_labels_are_unaffected(self):
        return_select_scenario = load_logout_hypothesis_scenario(
            RETURN_SELECT_SCENARIO_PATH
        )
        state = self._state("arfw-untouched", scenario=return_select_scenario)
        actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual([label for label, *_ in actions], [
            "HYP_PF_028_LOGOUT_SUBCODE01_RETURN_SELECT_SERVER_RESPONSE_FIRST",
            "HYP_PF_028_LOGOUT_SUBCODE01_ACK_THEN_SERVER_SOCKET_CLOSE",
        ])


class LogoutAckFirstReorderAllowlistTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _assert_every_mutation_rejected(self, mutations):
        data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        for mutate in mutations:
            tampered_data = json.loads(json.dumps(data))
            mutate(tampered_data)
            tampered = Path(self.tmp.name) / "tampered.json"
            tampered.write_text(json.dumps(tampered_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_logout_hypothesis_scenario(tampered)

    def test_the_allowlist_is_exact(self):
        self._assert_every_mutation_rejected((
            lambda d: d.__setitem__("production_allowed", True),
            lambda d: d["entry"].__setitem__("close_delay_ms", 0),
            lambda d: d["entry"].__setitem__("post_ack_action", "none"),
            lambda d: d["entry"].__setitem__(
                "response_policy", LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST,
            ),
            lambda d: d.__setitem__("hypothesis_id", "HYP-PF-041"),
            lambda d: d.__setitem__("hypothesis_id", "HYP-PF-028"),
        ))

    def test_loading_it_returns_the_real_profile_object(self):
        scenario = load_logout_hypothesis_scenario(SCENARIO_PATH)
        self.assertEqual(
            scenario.response_policy, LOGOUT_RESPONSE_POLICY_ACK_FIRST_REORDER,
        )
        self.assertEqual(scenario.hypothesis_id, "HYP-PF-042")


if __name__ == "__main__":
    unittest.main()
