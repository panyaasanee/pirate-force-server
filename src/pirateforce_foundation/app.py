"""Run the preserved V141 listeners with persistent character lifecycle enabled."""
import argparse
import os
import sys
from pathlib import Path
from .legacy_bridge import LegacyProjector, load_legacy
from .lifecycle import CharacterLifecycle
from .model import Position
from .runtime import make_state_class
from .scenario import load_scenario
from .store import SQLiteStore

def main():
    root = Path(__file__).resolve().parents[2]
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument('--db')
    pre.add_argument('--scenario')
    pre.add_argument('--capture-root')
    known, remaining = pre.parse_known_args(); sys.argv = [sys.argv[0], *remaining]
    scenario = load_scenario(known.scenario) if known.scenario else None
    db_path = known.db or str(
        root / ('state/test_arena_v1.sqlite3' if scenario else 'state/pirateforce.sqlite3')
    )
    legacy = load_legacy(root/'current/pf_login_game_server_v141.py')
    store = SQLiteStore(db_path, root/'migrations'); Path(db_path).parent.mkdir(parents=True, exist_ok=True); store.migrate()
    # A previous process cannot own a live lease after this process starts.
    store.expire_open_sessions()
    default = Position(1,0,legacy.V135_PLAYER_X,legacy.V135_PLAYER_Y,legacy.V135_PLAYER_Z)
    lifecycle = CharacterLifecycle(store, default, legacy.extract_avatar_attr_wire_from_actor)
    legacy.run_self_test(verbose=True)
    legacy.GameSessionState = make_state_class(
        legacy, lifecycle, LegacyProjector(legacy), scenario=scenario,
    )
    legacy.run_self_test = lambda verbose=True: None
    if known.capture_root:
        capture_root = Path(known.capture_root).resolve()
        capture_root.mkdir(parents=True, exist_ok=True)
        # The frozen V141 listener writes to relative capture_v141/. Isolate
        # that immutable behavior under this run's timestamped capture root.
        os.chdir(capture_root)
    legacy.main()

if __name__ == '__main__': main()
