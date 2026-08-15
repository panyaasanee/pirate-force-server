import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "wait_for_pf_stage", ROOT / "tools" / "wait_for_pf_stage.py"
)
WAITER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(WAITER)


class WaitForStageTests(unittest.TestCase):
    def test_launcher_capture_root_resolves_nested_live_logs(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            nested = root / "capture_v141"
            nested.mkdir()
            game = nested / "GAME_LIVE.txt"
            events = nested / "GAME_EVENTS_LIVE.txt"
            game.write_text(
                "SENT label=FOUNDATION_CREATE_COMMITTED frame_bytes=244\n"
                "SENT label=ARENA_V1_P30_INITIAL frame_bytes=212\n",
                encoding="utf-8",
            )
            events.write_text(
                "EVENT name=TargetVital actor_id=0x000000000000201F "
                "placement=P30 kind=2\n",
                encoding="utf-8",
            )
            logs = WAITER.resolve_logs(root)
            self.assertEqual({item.name for item in logs}, {
                "GAME_LIVE.txt", "GAME_EVENTS_LIVE.txt",
            })
            self.assertIn("CREATE_COMMITTED", WAITER.find_stage_line(logs, "create-committed"))
            self.assertIn("ARENA_V1_P30_INITIAL", WAITER.find_stage_line(logs, "population"))
            self.assertIn("placement=P30", WAITER.find_stage_line(logs, "arena-target"))

    def test_partial_target_event_does_not_pass(self):
        with tempfile.TemporaryDirectory() as raw:
            event = Path(raw) / "GAME_EVENTS_LIVE.txt"
            event.write_text(
                "EVENT name=TargetVital actor_id=0x000000000000201F kind=2\n",
                encoding="utf-8",
            )
            self.assertIsNone(WAITER.find_stage_line([event], "arena-target"))


if __name__ == "__main__":
    unittest.main()
