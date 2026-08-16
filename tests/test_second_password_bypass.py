from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.item_move_capture import (
    load_item_move_capture_scenario,
)
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.second_password_bypass import (
    SECOND_PASSWORD_MODES,
    SECOND_PASSWORD_OK_FRAME_SHA256,
    SECOND_PASSWORD_OK_PC_SHA256,
    make_proactive_second_password_ok,
    require_second_password_mode,
)
from pirateforce_foundation.store import SQLiteStore


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
CAPTURE_PATH = ROOT / "scenarios" / "item_move_capture_v111_slot2.json"

RUNTIME_READY_PC = bytes.fromhex(
    "12 6F 6E 14 00 00 00 00 08 00 0B 02 12 02 00 "
    "12 A2 25 0B 04 0B 02 0B 00 0B 00 0B 00 0F 00 00 "
    "12 90 2A 0B 00 2A 00 00 00 00 2A 00 00 00 00 "
    "2A 00 00 C0 68 44 2A 00 00 00 00 0B 00 0B 00"
)
EMPTY_RUNTIME_PC = bytes.fromhex(
    "12 6F 6E 14 00 00 00 00 08 00 0B 00"
)


class SecondPasswordBypassTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        default = Position(
            1, 0, self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
        )
        self.lifecycle = CharacterLifecycle(
            self.store, default, self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.capture = load_item_move_capture_scenario(CAPTURE_PATH)

    def tearDown(self):
        self.tmp.cleanup()

    def _state(self, login="bypass", *, mode="bypass", capture=True):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            item_move_capture_scenario=self.capture if capture else None,
            second_password_mode=mode,
        )
        state = state_type(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        created = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        self.assertEqual(created[0][0], "FOUNDATION_CREATE_COMMITTED")
        character = self.store.list_characters(state.foundation.account_id)[0]
        started = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        self.assertEqual(
            [action[0] for action in started],
            [
                "FOUNDATION_SELECTED_START_GAME",
                "V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE",
            ],
        )
        return state

    def test_server_parameter_is_exact_default_off_and_contains_no_credential(self):
        self.assertEqual(SECOND_PASSWORD_MODES, ("required", "bypass"))
        self.assertEqual(require_second_password_mode("required"), "required")
        self.assertEqual(require_second_password_mode("bypass"), "bypass")
        for invalid in (True, 1, None, "", "disabled", "BYPASS"):
            with self.assertRaisesRegex(ValueError, "exactly required or bypass"):
                require_second_password_mode(invalid)

        source = (ROOT / "src" / "pirateforce_foundation" /
                  "second_password_bypass.py").read_text(encoding="utf-8").lower()
        for forbidden in ("1234", "digest =", "credential_value", "password_value"):
            self.assertNotIn(forbidden, source)

    def test_exact_ok_packet_is_hash_pinned_and_contains_no_request_digest(self):
        pc, frame = make_proactive_second_password_ok(self.legacy, "bypass")
        self.assertEqual(len(pc), 34)
        self.assertEqual(len(frame), 44)
        self.assertEqual(
            hashlib.sha256(pc).hexdigest().upper(),
            SECOND_PASSWORD_OK_PC_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(frame).hexdigest().upper(),
            SECOND_PASSWORD_OK_FRAME_SHA256,
        )
        self.assertEqual((pc[21], pc[23:27], pc[28:32]), (1, b"\0" * 4, b"\0" * 4))
        self.assertNotIn(b"7D014E541AFAA43267CA80BCCBC3FD6B", pc)

        with mock.patch.object(
            self.legacy, "make_check_second_password_success",
            return_value=(pc + b"\0", frame),
        ):
            with self.assertRaisesRegex(RuntimeError, "PC drift"):
                make_proactive_second_password_ok(self.legacy, "bypass")
        with self.assertRaisesRegex(ValueError, "requires bypass mode"):
            make_proactive_second_password_ok(self.legacy, "required")

    def test_proactive_ok_is_once_after_runtime_ready_and_after_baseline_actions(self):
        state = self._state()
        self.assertFalse(state.second_password_bypass_sent)
        parsed = self.legacy.parse_outer(RUNTIME_READY_PC)
        actions = state.dispatch(parsed)
        labels = [action[0] for action in actions]
        self.assertEqual(labels[:3], [
            "RUNTIME_RES_ACK_FIRST_REQ",
            "V99_SHOW_MESSAGE_LOCAL_SERVER_ONLINE",
            "V100_MUSIC_CONTROL_CURRENT_SCENE",
        ])
        self.assertEqual(
            labels[3], "HYP_PF_009_PROACTIVE_SECOND_PASSWORD_OK_ONCE",
        )
        expected = self.legacy.make_check_second_password_success()
        self.assertEqual(actions[3][1:3], expected)
        self.assertEqual(actions[3][3], 0.0)
        self.assertTrue(state.second_password_bypass_sent)
        self.assertIn(
            "hyp_pf_009_proactive_second_password_ok_committed", state.events,
        )

        duplicate = state.dispatch(self.legacy.parse_outer(RUNTIME_READY_PC))
        self.assertNotIn(
            "HYP_PF_009_PROACTIVE_SECOND_PASSWORD_OK_ONCE",
            [action[0] for action in duplicate],
        )
        self.assertEqual(
            state.events.count("hyp_pf_009_proactive_second_password_ok_committed"),
            1,
        )

    def test_bypass_repeats_exact_ok_on_empty_runtime_polls_without_credentials(self):
        state = self._state()
        state.dispatch(self.legacy.parse_outer(RUNTIME_READY_PC))
        empty = self.legacy.parse_outer(EMPTY_RUNTIME_PC)
        self.assertEqual(empty.vital_count, 0)

        first = state.dispatch(empty)
        second = state.dispatch(empty)
        for actions in (first, second):
            matching = [action for action in actions if action[0] ==
                        "HYP_PF_009_SECOND_PASSWORD_OK_KEEPALIVE"]
            self.assertEqual(len(matching), 1)
            self.assertEqual(
                matching[0][1:3],
                self.legacy.make_check_second_password_success(),
            )
        self.assertTrue(state.second_password_bypass_keepalive_started)
        self.assertEqual(
            state.events.count(
                "hyp_pf_009_second_password_ok_keepalive_started"
            ),
            1,
        )

        baseline = self._state("pulse-baseline", mode="required")
        baseline.dispatch(self.legacy.parse_outer(RUNTIME_READY_PC))
        self.assertNotIn(
            "HYP_PF_009_SECOND_PASSWORD_OK_KEEPALIVE",
            [action[0] for action in baseline.dispatch(empty)],
        )

    def test_baseline_has_no_proactive_packet_or_state_effect(self):
        state = self._state("baseline", mode="required")
        actions = state.dispatch(self.legacy.parse_outer(RUNTIME_READY_PC))
        self.assertEqual([action[0] for action in actions], [
            "RUNTIME_RES_ACK_FIRST_REQ",
            "V99_SHOW_MESSAGE_LOCAL_SERVER_ONLINE",
            "V100_MUSIC_CONTROL_CURRENT_SCENE",
        ])
        self.assertFalse(state.second_password_bypass_sent)
        self.assertNotIn(
            "hyp_pf_009_proactive_second_password_ok_committed", state.events,
        )

    def test_bypass_is_available_without_capture_and_cli_default_is_required(self):
        state = self._state("global-bypass", mode="bypass", capture=False)
        actions = state.dispatch(self.legacy.parse_outer(RUNTIME_READY_PC))
        self.assertIn(
            "HYP_PF_009_PROACTIVE_SECOND_PASSWORD_OK_ONCE",
            [action[0] for action in actions],
        )

        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        required = subprocess.run(
            [
                sys.executable, "-m", "pirateforce_foundation.app",
                "--db", str(self.db_path), "--self-test-only",
            ],
            cwd=ROOT, env=env, text=True, capture_output=True, check=False,
        )
        self.assertEqual(required.returncode, 0, required.stderr)

        bypass = subprocess.run(
            [
                sys.executable, "-m", "pirateforce_foundation.app",
                "--second-password-mode", "bypass",
                "--db", str(self.db_path), "--self-test-only",
            ],
            cwd=ROOT, env=env, text=True, capture_output=True, check=False,
        )
        self.assertEqual(bypass.returncode, 0, bypass.stderr)

        invalid = subprocess.run(
            [
                sys.executable, "-m", "pirateforce_foundation.app",
                "--second-password-mode", "sometimes", "--self-test-only",
            ],
            cwd=ROOT, env=env, text=True, capture_output=True, check=False,
        )
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("invalid choice", invalid.stderr)

    def test_v141_is_immutable(self):
        self.assertEqual(
            hashlib.sha256(LEGACY_PATH.read_bytes()).hexdigest().upper(),
            "2EB05ED2FDBDD5EE3D91F7FBB8C1D16A4C7A02A843BC97169B16A389E4EA4C22",
        )


if __name__ == "__main__":
    unittest.main()
