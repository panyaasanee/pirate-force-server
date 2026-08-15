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

    def test_arena_v2_population_label_passes(self):
        with tempfile.TemporaryDirectory() as raw:
            game = Path(raw) / "GAME_LIVE.txt"
            game.write_text(
                "SENT label=ARENA_V2_P30_INITIAL frame_bytes=217\n",
                encoding="utf-8",
            )
            self.assertIn(
                "ARENA_V2_P30_INITIAL",
                WAITER.find_stage_line([game], "population"),
            )

    def test_scene2_labels_are_distinct(self):
        with tempfile.TemporaryDirectory() as raw:
            game = Path(raw) / "GAME_LIVE.txt"
            game.write_text(
                "SENT label=SCENE2_LOAD_ONLY_SELECTED_START_GAME frame_bytes=1\n"
                "SENT label=SCENE2_LOAD_ONLY_TELEPORT_MARKER2_ONCE frame_bytes=2\n",
                encoding="utf-8",
            )
            self.assertIn("SELECTED_START_GAME", WAITER.find_stage_line([game], "scene2-start-game"))
            self.assertIn("TELEPORT_MARKER2", WAITER.find_stage_line([game], "scene2-teleport"))


if __name__ == "__main__":
    unittest.main()
