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
from .scene_load import load_scene_load_scenario
from .session import ReadOnlyFoundationSession
from .store import SQLiteStore

def main():
    root = Path(__file__).resolve().parents[2]
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument('--db')
    pre.add_argument('--scenario')
    pre.add_argument('--scene-load-scenario')
    pre.add_argument('--capture-root')
    known, remaining = pre.parse_known_args(); sys.argv = [sys.argv[0], *remaining]
    scenario = load_scenario(known.scenario) if known.scenario else None
    # PF-HYPOTHESIS-LEDGER: HYP-PF-007 frozen
    # PF-HYPOTHESIS-LEDGER: GEO-PF-002 frozen
    # PF-HYPOTHESIS-LEDGER: GEO-PF-003 frozen
    scene_load = (
        load_scene_load_scenario(known.scene_load_scenario)
        if known.scene_load_scenario else None
    )
    if scenario is not None and scene_load is not None:
        pre.error('--scenario and --scene-load-scenario are mutually exclusive')
    db_path = known.db or str(
        root / ('state/test_arena_v1.sqlite3' if (scenario or scene_load)
                else 'state/pirateforce.sqlite3')
    )
    legacy = load_legacy(root/'current/pf_login_game_server_v141.py')
    store = SQLiteStore(db_path, root/'migrations')
    if scene_load is not None:
        if not Path(db_path).is_file():
            raise FileNotFoundError(db_path)
    else:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True); store.migrate()
        # A previous process cannot own a live lease after this process starts.
        store.expire_open_sessions()
    default = Position(1,0,legacy.V135_PLAYER_X,legacy.V135_PLAYER_Y,legacy.V135_PLAYER_Z)
    lifecycle = CharacterLifecycle(store, default, legacy.extract_avatar_attr_wire_from_actor)
    legacy.run_self_test(verbose=True)
    projector = LegacyProjector(legacy)
    session_factory = None
    if scene_load is not None:
        session_factory = lambda token: ReadOnlyFoundationSession(
            store, projector, token, scene_load,
        )
    legacy.GameSessionState = make_state_class(
        legacy, lifecycle, projector, scenario=scenario,
        scene_load_scenario=scene_load, session_factory=session_factory,
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
