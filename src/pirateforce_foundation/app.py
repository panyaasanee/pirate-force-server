"""Run the preserved V141 listeners with persistent character lifecycle enabled."""
import argparse
import sys
from pathlib import Path
from .legacy_bridge import LegacyProjector, load_legacy
from .lifecycle import CharacterLifecycle
from .model import Position
from .runtime import make_state_class
from .store import SQLiteStore

def main():
    root = Path(__file__).resolve().parents[2]
    pre = argparse.ArgumentParser(add_help=False); pre.add_argument('--db', default=str(root/'state/pirateforce.sqlite3'))
    known, remaining = pre.parse_known_args(); sys.argv = [sys.argv[0], *remaining]
    legacy = load_legacy(root/'current/pf_login_game_server_v141.py')
    store = SQLiteStore(known.db, root/'migrations'); Path(known.db).parent.mkdir(parents=True, exist_ok=True); store.migrate()
    # A previous process cannot own a live lease after this process starts.
    store.expire_open_sessions()
    default = Position(1,0,legacy.V135_PLAYER_X,legacy.V135_PLAYER_Y,legacy.V135_PLAYER_Z)
    lifecycle = CharacterLifecycle(store, default, legacy.extract_avatar_attr_wire_from_actor)
    legacy.run_self_test(verbose=True)
    legacy.GameSessionState = make_state_class(legacy, lifecycle, LegacyProjector(legacy))
    legacy.run_self_test = lambda verbose=True: None
    legacy.main()

if __name__ == '__main__': main()
