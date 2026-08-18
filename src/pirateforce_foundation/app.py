"""Run the preserved V141 listeners with persistent character lifecycle enabled."""
import argparse
import os
import sys
from pathlib import Path
from .connection import GameConnectionBindings, adapt_game_listener
from .legacy_bridge import LegacyProjector, load_legacy
from .lifecycle import CharacterLifecycle
from .channel_message_hypothesis import load_channel_message_hypothesis_scenario
from .chat_input_hypothesis import load_chat_input_hypothesis_scenario
from .delete_actor_hypothesis import load_delete_actor_hypothesis_scenario
from .delete_refresh_hypothesis import load_delete_refresh_hypothesis_scenario
from .item_move_capture import load_item_move_capture_scenario
from .item_move_hypothesis import load_item_move_hypothesis_scenario
from .logout_hypothesis import load_logout_hypothesis_scenario
from .model import Position
from .population_scenario import load_population_scenario
from .runtime import make_state_class
from .runtime_console import install_runtime_console
from .scenario import load_scenario
from .scene_load import load_scene_load_scenario
from .second_password_bypass import SECOND_PASSWORD_MODES
from .stats_progression_hypothesis import (
    load_hp_death_hypothesis_scenario,
    load_stats_progression_hypothesis_scenario,
)
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
    pre.add_argument('--logout-hypothesis-scenario')
    pre.add_argument('--chat-input-hypothesis-scenario')
    pre.add_argument('--channel-message-hypothesis-scenario')
    pre.add_argument('--delete-actor-hypothesis-scenario')
    pre.add_argument('--delete-refresh-hypothesis-scenario')
    pre.add_argument('--stats-progression-hypothesis-scenario')
    pre.add_argument('--hp-death-hypothesis-scenario')
    pre.add_argument(
        '--second-password-mode', choices=SECOND_PASSWORD_MODES,
        default='required',
    )
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
    # PF-HYPOTHESIS-LEDGER: HYP-PF-012 active
    logout_hypothesis = (
        load_logout_hypothesis_scenario(known.logout_hypothesis_scenario)
        if known.logout_hypothesis_scenario else None
    )
    # PF-HYPOTHESIS-LEDGER: HYP-PF-014 active
    chat_input_hypothesis = (
        load_chat_input_hypothesis_scenario(known.chat_input_hypothesis_scenario)
        if known.chat_input_hypothesis_scenario else None
    )
    # PF-HYPOTHESIS-LEDGER: HYP-PF-019 active
    channel_message_hypothesis = (
        load_channel_message_hypothesis_scenario(
            known.channel_message_hypothesis_scenario
        )
        if known.channel_message_hypothesis_scenario else None
    )
    # PF-HYPOTHESIS-LEDGER: HYP-PF-015 active
    delete_actor_hypothesis = (
        load_delete_actor_hypothesis_scenario(known.delete_actor_hypothesis_scenario)
        if known.delete_actor_hypothesis_scenario else None
    )
    # PF-HYPOTHESIS-LEDGER: HYP-PF-021 active
    delete_refresh_hypothesis = (
        load_delete_refresh_hypothesis_scenario(
            known.delete_refresh_hypothesis_scenario
        )
        if known.delete_refresh_hypothesis_scenario else None
    )
    # PF-HYPOTHESIS-LEDGER: HYP-PF-020 active
    stats_progression_hypothesis = (
        load_stats_progression_hypothesis_scenario(
            known.stats_progression_hypothesis_scenario
        )
        if known.stats_progression_hypothesis_scenario else None
    )
    # PF-HYPOTHESIS-LEDGER: HYP-PF-022 active
    # HP-DEATH-002.  This is the one lane in this file that can make a
    # character appear to die on a real client, so it is the one lane a reader
    # should double-check: it is refused alongside every other mode, it demands
    # an explicit existing --db like the other hypothesis lanes, and with the
    # flag absent nothing in the process can even name the death-timer field.
    hp_death_hypothesis = (
        load_hp_death_hypothesis_scenario(known.hp_death_hypothesis_scenario)
        if known.hp_death_hypothesis_scenario else None
    )
    if sum(value is not None for value in (
        scenario, scene_load, population, item_move_capture,
        item_move_hypothesis, logout_hypothesis, chat_input_hypothesis,
        channel_message_hypothesis, delete_actor_hypothesis,
        delete_refresh_hypothesis, stats_progression_hypothesis,
        hp_death_hypothesis,
    )) > 1:
        pre.error(
            '--scenario, --scene-load-scenario, --population-scenario, and '
            '--item-move-capture-scenario/--item-move-hypothesis-scenario/'
            '--logout-hypothesis-scenario/--chat-input-hypothesis-scenario/'
            '--channel-message-hypothesis-scenario/'
            '--delete-actor-hypothesis-scenario/'
            '--delete-refresh-hypothesis-scenario/'
            '--stats-progression-hypothesis-scenario/'
            '--hp-death-hypothesis-scenario are mutually exclusive'
        )
    if item_move_capture is not None and not known.db:
        pre.error('--item-move-capture-scenario requires an explicit existing --db')
    if item_move_hypothesis is not None and not known.db:
        pre.error('--item-move-hypothesis-scenario requires an explicit existing --db')
    if logout_hypothesis is not None and not known.db:
        pre.error('--logout-hypothesis-scenario requires an explicit existing --db')
    if chat_input_hypothesis is not None and not known.db:
        pre.error('--chat-input-hypothesis-scenario requires an explicit existing --db')
    if channel_message_hypothesis is not None and not known.db:
        pre.error(
            '--channel-message-hypothesis-scenario requires an explicit existing --db'
        )
    if delete_actor_hypothesis is not None and not known.db:
        pre.error('--delete-actor-hypothesis-scenario requires an explicit existing --db')
    if delete_refresh_hypothesis is not None and not known.db:
        pre.error(
            '--delete-refresh-hypothesis-scenario requires an explicit existing --db'
        )
    if stats_progression_hypothesis is not None and not known.db:
        pre.error(
            '--stats-progression-hypothesis-scenario requires an explicit existing --db'
        )
    if hp_death_hypothesis is not None and not known.db:
        pre.error(
            '--hp-death-hypothesis-scenario requires an explicit existing --db'
        )
    db_path = known.db or str(
        root / (
            'state/object_population_v94.sqlite3' if population is not None
            else ('state/test_arena_v1.sqlite3' if (scenario or scene_load)
                  else 'state/pirateforce.sqlite3')
        )
    )
    if item_move_capture is not None or item_move_hypothesis is not None:
        db_path = resolve_item_move_capture_db(db_path)
    self_test_only = '--self-test-only' in remaining
    if not self_test_only:
        mode = (
            'arena' if scenario is not None else
            'scene-load' if scene_load is not None else
            'population' if population is not None else
            'item-move-capture' if item_move_capture is not None else
            'item-move-hypothesis' if item_move_hypothesis is not None else
            'logout-hypothesis' if logout_hypothesis is not None else
            'chat-input-hypothesis' if chat_input_hypothesis is not None else
            'channel-message-hypothesis'
            if channel_message_hypothesis is not None else
            'delete-actor-hypothesis' if delete_actor_hypothesis is not None else
            'delete-refresh-hypothesis'
            if delete_refresh_hypothesis is not None else
            'stats-progression-hypothesis'
            if stats_progression_hypothesis is not None else
            'hp-death-hypothesis' if hp_death_hypothesis is not None else
            'foundation'
        )
        install_runtime_console(
            root, known.capture_root, db_path, mode,
        )
    legacy = load_legacy(root/'current/pf_login_game_server_v141.py')
    store = SQLiteStore(db_path, root/'migrations')
    if (
        scene_load is not None
        or item_move_capture is not None
        or item_move_hypothesis is not None
        or logout_hypothesis is not None
        or chat_input_hypothesis is not None
        or channel_message_hypothesis is not None
        or delete_actor_hypothesis is not None
        or delete_refresh_hypothesis is not None
        or stats_progression_hypothesis is not None
        or hp_death_hypothesis is not None
    ):
        if not Path(db_path).is_file():
            raise FileNotFoundError(db_path)
        if (
            item_move_capture is not None
            or item_move_hypothesis is not None
            or logout_hypothesis is not None
            or chat_input_hypothesis is not None
            or channel_message_hypothesis is not None
            or delete_actor_hypothesis is not None
            or delete_refresh_hypothesis is not None
            or stats_progression_hypothesis is not None
            or hp_death_hypothesis is not None
        ):
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
        logout_hypothesis_scenario=logout_hypothesis,
        chat_input_hypothesis_scenario=chat_input_hypothesis,
        channel_message_hypothesis_scenario=channel_message_hypothesis,
        delete_actor_hypothesis_scenario=delete_actor_hypothesis,
        delete_refresh_hypothesis_scenario=delete_refresh_hypothesis,
        stats_progression_hypothesis_scenario=stats_progression_hypothesis,
        hp_death_hypothesis_scenario=hp_death_hypothesis,
        # PF-HYPOTHESIS-LEDGER: HYP-PF-009 active
        second_password_mode=known.second_password_mode,
    )
    legacy.game_listener = adapt_game_listener(
        legacy.game_listener, connection_bindings, managed_sockets,
    )
    server_main = adapt_server_main(
        legacy.main, shutdown, managed_sockets, legacy.threading,
    )
    legacy.run_self_test = lambda verbose=True: None
    if self_test_only:
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
