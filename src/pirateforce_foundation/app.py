"""Run the preserved V141 listeners with persistent character lifecycle enabled."""
import argparse
import os
import sys
from pathlib import Path
from .connection import GameConnectionBindings, adapt_game_listener
from .legacy_bridge import LegacyProjector, load_legacy
from .lifecycle import CharacterLifecycle
from .item_move_capture import load_item_move_capture_scenario
from .item_move_hypothesis import load_item_move_hypothesis_scenario
from .model import Position
from .population_scenario import load_population_scenario
from .runtime import make_state_class
from .scenario import load_scenario
from .scene_load import load_scene_load_scenario
from .session import ReadOnlyFoundationSession
from .store import SQLiteStore
from .shutdown import (
    ManagedSocketModule,
    ServerShutdownController,
    adapt_server_main,
    run_server,
)


def resolve_item_move_capture_db(path: str) -> str:
    """Pin capture mode to one existing DB across the later capture-root chdir."""
    resolved = Path(path).resolve(strict=True)
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    return str(resolved)

def main() -> int:
    root = Path(__file__).resolve().parents[2]
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument('--db')
    pre.add_argument('--scenario')
    pre.add_argument('--scene-load-scenario')
    pre.add_argument('--population-scenario')
    pre.add_argument('--item-move-capture-scenario')
    pre.add_argument('--item-move-hypothesis-scenario')
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
    population = (
        load_population_scenario(known.population_scenario)
        if known.population_scenario else None
    )
    item_move_capture = (
        load_item_move_capture_scenario(known.item_move_capture_scenario)
        if known.item_move_capture_scenario else None
    )
    # PF-HYPOTHESIS-LEDGER: HYP-PF-008 active
    item_move_hypothesis = (
        load_item_move_hypothesis_scenario(known.item_move_hypothesis_scenario)
        if known.item_move_hypothesis_scenario else None
    )
    if sum(value is not None for value in (
        scenario, scene_load, population, item_move_capture,
        item_move_hypothesis,
    )) > 1:
        pre.error(
            '--scenario, --scene-load-scenario, --population-scenario, and '
            '--item-move-capture-scenario/--item-move-hypothesis-scenario '
            'are mutually exclusive'
        )
    if item_move_capture is not None and not known.db:
        pre.error('--item-move-capture-scenario requires an explicit existing --db')
    if item_move_hypothesis is not None and not known.db:
        pre.error('--item-move-hypothesis-scenario requires an explicit existing --db')
    db_path = known.db or str(
        root / (
            'state/object_population_v94.sqlite3' if population is not None
            else ('state/test_arena_v1.sqlite3' if (scenario or scene_load)
                  else 'state/pirateforce.sqlite3')
        )
    )
    if item_move_capture is not None or item_move_hypothesis is not None:
        db_path = resolve_item_move_capture_db(db_path)
    legacy = load_legacy(root/'current/pf_login_game_server_v141.py')
    store = SQLiteStore(db_path, root/'migrations')
    if (
        scene_load is not None
        or item_move_capture is not None
        or item_move_hypothesis is not None
    ):
        if not Path(db_path).is_file():
            raise FileNotFoundError(db_path)
        if item_move_capture is not None or item_move_hypothesis is not None:
            store.migrate()
            store.expire_open_sessions()
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
    shutdown = ServerShutdownController()
    connection_bindings = GameConnectionBindings(
        shutdown.record_connection_failure,
    )
    managed_sockets = ManagedSocketModule(legacy.socket, shutdown)
    legacy.GameSessionState = make_state_class(
        legacy, lifecycle, projector, scenario=scenario,
        scene_load_scenario=scene_load, session_factory=session_factory,
        connection_bindings=connection_bindings,
        population_scenario=population,
        item_move_capture_scenario=item_move_capture,
        item_move_hypothesis_scenario=item_move_hypothesis,
    )
    legacy.game_listener = adapt_game_listener(
        legacy.game_listener, connection_bindings, managed_sockets,
    )
    server_main = adapt_server_main(
        legacy.main, shutdown, managed_sockets, legacy.threading,
    )
    legacy.run_self_test = lambda verbose=True: None
    if '--self-test-only' in remaining:
        # Keep the frozen argument-validation/self-test-only return outside the
        # production shutdown runner. An unrequested run_server return is always
        # an early-startup failure, including before either listener binds.
        server_main()
        return 0
    if known.capture_root:
        capture_root = Path(known.capture_root).resolve()
        capture_root.mkdir(parents=True, exist_ok=True)
        # The frozen V141 listener writes to relative capture_v141/. Isolate
        # that immutable behavior under this run's timestamped capture root.
        os.chdir(capture_root)
    return run_server(server_main, shutdown)

if __name__ == '__main__':
    raise SystemExit(main())
