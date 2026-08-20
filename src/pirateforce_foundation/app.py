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
from .move_authority_hypothesis import (
    load_move_authority_hypothesis_scenario,
)
from .logout_hypothesis import load_logout_hypothesis_scenario
from .model import Position
from .population_scenario import load_population_scenario
from .npc_hostile_hypothesis import (
    load_npc_hostile_hypothesis_scenario,
)
from .npc_hp_link_hypothesis import (
    load_npc_hp_link_hypothesis_scenario,
)
from .runtime import make_state_class
from .runtime_console import install_runtime_console
from .damage_hp_link_hypothesis import (
    load_damage_hp_link_hypothesis_scenario,
)
from .damage_model_hypothesis import (
    load_damage_model_hypothesis_scenario,
)
from .remote_player_hypothesis import (
    load_remote_player_hypothesis_scenario,
)
from .runtimeres_death_hypothesis import (
    load_runtimeres_death_hypothesis_scenario,
)
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
    pre.add_argument('--runtimeres-death-hypothesis-scenario')
    pre.add_argument('--damage-model-hypothesis-scenario')
    pre.add_argument('--damage-hp-link-hypothesis-scenario')
    pre.add_argument('--remote-player-hypothesis-scenario')
    pre.add_argument('--npc-hostile-hypothesis-scenario')
    pre.add_argument('--npc-hp-link-hypothesis-scenario')
    pre.add_argument('--move-authority-hypothesis-scenario')
    pre.add_argument(
        '--second-password-mode', choices=SECOND_PASSWORD_MODES,
        default='required',
    )
    pre.add_argument('--capture-root')
    known, remaining = pre.parse_known_args(); sys.argv = [sys.argv[0], *remaining]
    # PF-HYPOTHESIS-LEDGER: HYP-PF-030 active
    # MOVE-AUTHORITY-002.  The only lane in this file that can REFUSE a
    # durable write instead of composing bytes: behind this flag the server
    # stops persisting a reported position that exceeds our own movement
    # budget, and emits nothing either way (no corrective-reposition frame has
    # ever been captured, so none is invented).  With the flag absent the
    # checkpoint path is exactly the one MOVE-AUTHORITY-001 characterized.
    # Refused alongside every other mode and demands an explicit existing --db.
    move_authority_hypothesis = (
        load_move_authority_hypothesis_scenario(
            known.move_authority_hypothesis_scenario
        )
        if known.move_authority_hypothesis_scenario else None
    )
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
    # PF-HYPOTHESIS-LEDGER: HYP-PF-023 active
    # RUNTIMERES-ENCODER-001 + RUNTIMERES-DISPATCH-001.  The lane that can drive
    # a KNOWN actor through the real engine death chain (GSCN_RunTimeProtocolRes
    # 0x6E9D, derived mask bit 0x02, object +0x1C) rather than HP-DEATH-002's
    # local-player death window.  Registered by the round-86 ledger append; it is
    # refused alongside every other mode and demands an explicit existing --db.
    runtimeres_death_hypothesis = (
        load_runtimeres_death_hypothesis_scenario(
            known.runtimeres_death_hypothesis_scenario
        )
        if known.runtimeres_death_hypothesis_scenario else None
    )
    # PF-HYPOTHESIS-LEDGER: HYP-PF-024 active
    # DAMAGE-ENCODER-001 + DAMAGE-DISPATCH-001.  The lane that puts a damage
    # NUMBER on the wire: CHitResult 0x16F7 version 0 inside the VitalData
    # collection (BASE mask 0x02, object +0x18) -- a different collection from
    # the actor-entry one above, despite the matching bit number.  The formula
    # behind that number is this project's own; the original server's is gone.
    # Refused alongside every other mode and demands an explicit existing --db.
    damage_model_hypothesis = (
        load_damage_model_hypothesis_scenario(
            known.damage_model_hypothesis_scenario
        )
        if known.damage_model_hypothesis_scenario else None
    )
    # PF-HYPOTHESIS-LEDGER: HYP-PF-026 active
    # DAMAGE-HP-LINK-001.  The middle piece of the hit -> bleed -> die loop:
    # the server runs OUR damage arithmetic against a server-held HP balance
    # and tells the one client both halves -- the floating number (CHitResult
    # 0x16F7, proven rendering at GT-024) and the shrinking HP bar
    # (UpdateAttrVital/ActorAttr hp_current, proven rendering at GT-019) --
    # ending in the proven dying window.  OUR design, not the original
    # server's, which is unrecoverable.  Refused alongside every other mode
    # and demands an explicit existing --db.
    damage_hp_link_hypothesis = (
        load_damage_hp_link_hypothesis_scenario(
            known.damage_hp_link_hypothesis_scenario
        )
        if known.damage_hp_link_hypothesis_scenario else None
    )
    # PF-HYPOTHESIS-LEDGER: HYP-PF-025 active
    # REMOTE-PLAYER-ENCODER-001 + REMOTE-PLAYER-DISPATCH-001.  The lane that
    # puts actor_type 2 (CNetActor, the remote-player branch) on the actor-
    # entry wire for the first time -- OUR design, not the original server's,
    # which is closed, unpublished and unrecoverable.  Registered by the
    # round-96 ledger append; it is refused alongside every other mode and
    # demands an explicit existing --db.
    remote_player_hypothesis = (
        load_remote_player_hypothesis_scenario(
            known.remote_player_hypothesis_scenario
        )
        if known.remote_player_hypothesis_scenario else None
    )
    # PF-HYPOTHESIS-LEDGER: HYP-PF-027 active
    # NPC-HOSTILE-001 + NPC-HOSTILE-DISPATCH.  Door A of the mob-aggro design:
    # the lane that makes the first Port Royal placement PRESENT as hostile,
    # pairing the SCENE-005 player faction 1 on the StartGame entry with a
    # five-byte faction splice (BasicAttr bit 0x0400, value 6) on the proven
    # HYP-PF-023 spawn.  Both values are OUR composition; the original
    # server's faction assignment is unrecoverable.  Registered by the
    # round-99 ledger append; it is refused alongside every other mode and
    # demands an explicit existing --db.
    npc_hostile_hypothesis = (
        load_npc_hostile_hypothesis_scenario(
            known.npc_hostile_hypothesis_scenario
        )
        if known.npc_hostile_hypothesis_scenario else None
    )
    # PF-HYPOTHESIS-LEDGER: HYP-PF-029 active
    # NPC-HP-LINK-001.  The first lane in this tree that moves a TARGET's hit
    # points: eight GSCN_RunTimeProtocolRes 0x6E9D v4 frames alternating the
    # VitalData hit carrier (CHitResult 0x16F7, BASE mask 0x02 at +0x18) with
    # the actor-entry target carrier (DERIVED mask 0x02 at +0x1C, actor_type 4)
    # against the one frozen Port Royal placement identity 0x2001, over a
    # server-held balance ladder 100/100/37/37/37/37/0/0.  THE ARITHMETIC AND
    # THE LINK ARE OURS, NOT THE ORIGINAL SERVER'S, WHICH IS UNRECOVERABLE: no
    # capture shows a target's hit points moving in response to damage in
    # either direction, and round 83 proved the client never subtracts -- which
    # is exactly why the server must say both halves itself.  Whether the
    # client renders the intermediate value 37 on the target's bar is
    # UNDECIDABLE from static analysis and is the queued attended test; the
    # only thing proven so far is the negative (505 damage, bar did not move),
    # recorded with its provenance caveat in
    # reports/PF_NPC_HP_LINK029_GT027_RERUN_ATTENDED_RESULT_20260820.md --
    # testimony plus screenshots, client-observable layer only, never to be
    # cited as wire-layer evidence.
    # This checkpoint wires the FLAG only: the flag is refused alongside every
    # other mode and demands an explicit existing --db, and the runtime.py
    # dispatch branch is deliberately a separate checkpoint, so the loaded
    # scenario is not handed to make_state_class below.
    npc_hp_link_hypothesis = (
        load_npc_hp_link_hypothesis_scenario(
            known.npc_hp_link_hypothesis_scenario
        )
        if known.npc_hp_link_hypothesis_scenario else None
    )
    if sum(value is not None for value in (
        scenario, scene_load, population, item_move_capture,
        item_move_hypothesis, logout_hypothesis, chat_input_hypothesis,
        channel_message_hypothesis, delete_actor_hypothesis,
        delete_refresh_hypothesis, stats_progression_hypothesis,
        hp_death_hypothesis, runtimeres_death_hypothesis,
        damage_model_hypothesis, damage_hp_link_hypothesis,
        remote_player_hypothesis, npc_hostile_hypothesis,
        npc_hp_link_hypothesis, move_authority_hypothesis,
    )) > 1:
        pre.error(
            '--scenario, --scene-load-scenario, --population-scenario, and '
            '--item-move-capture-scenario/--item-move-hypothesis-scenario/'
            '--logout-hypothesis-scenario/--chat-input-hypothesis-scenario/'
            '--channel-message-hypothesis-scenario/'
            '--delete-actor-hypothesis-scenario/'
            '--delete-refresh-hypothesis-scenario/'
            '--stats-progression-hypothesis-scenario/'
            '--hp-death-hypothesis-scenario/'
            '--runtimeres-death-hypothesis-scenario/'
            '--damage-model-hypothesis-scenario/'
            '--damage-hp-link-hypothesis-scenario/'
            '--remote-player-hypothesis-scenario/'
            '--npc-hostile-hypothesis-scenario/'
            '--npc-hp-link-hypothesis-scenario/'
            '--move-authority-hypothesis-scenario are mutually exclusive'
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
    if runtimeres_death_hypothesis is not None and not known.db:
        pre.error(
            '--runtimeres-death-hypothesis-scenario requires an explicit '
            'existing --db'
        )
    if damage_model_hypothesis is not None and not known.db:
        pre.error(
            '--damage-model-hypothesis-scenario requires an explicit '
            'existing --db'
        )
    if damage_hp_link_hypothesis is not None and not known.db:
        pre.error(
            '--damage-hp-link-hypothesis-scenario requires an explicit '
            'existing --db'
        )
    if remote_player_hypothesis is not None and not known.db:
        pre.error(
            '--remote-player-hypothesis-scenario requires an explicit '
            'existing --db'
        )
    if npc_hostile_hypothesis is not None and not known.db:
        pre.error(
            '--npc-hostile-hypothesis-scenario requires an explicit '
            'existing --db'
        )
    if npc_hp_link_hypothesis is not None and not known.db:
        pre.error(
            '--npc-hp-link-hypothesis-scenario requires an explicit '
            'existing --db'
        )
    if move_authority_hypothesis is not None and not known.db:
        pre.error(
            '--move-authority-hypothesis-scenario requires an explicit '
            'existing --db'
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
            'runtimeres-death-hypothesis'
            if runtimeres_death_hypothesis is not None else
            'damage-model-hypothesis'
            if damage_model_hypothesis is not None else
            'damage-hp-link-hypothesis'
            if damage_hp_link_hypothesis is not None else
            'remote-player-hypothesis'
            if remote_player_hypothesis is not None else
            'npc-hostile-hypothesis'
            if npc_hostile_hypothesis is not None else
            'npc-hp-link-hypothesis'
            if npc_hp_link_hypothesis is not None else
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
        or runtimeres_death_hypothesis is not None
        or damage_model_hypothesis is not None
        or damage_hp_link_hypothesis is not None
        or remote_player_hypothesis is not None
        or npc_hostile_hypothesis is not None
        or npc_hp_link_hypothesis is not None
        or move_authority_hypothesis is not None
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
            or runtimeres_death_hypothesis is not None
            or damage_model_hypothesis is not None
            or damage_hp_link_hypothesis is not None
            or remote_player_hypothesis is not None
            or npc_hostile_hypothesis is not None
            or npc_hp_link_hypothesis is not None
            or move_authority_hypothesis is not None
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
        # RUNTIMERES-DISPATCH-001.  None unless the flag was handed in, and
        # make_state_class refuses it alongside every other mode a second time.
        runtimeres_death_hypothesis_scenario=runtimeres_death_hypothesis,
        # DAMAGE-DISPATCH-001.  None unless the flag was handed in, and
        # make_state_class refuses it alongside every other mode a second time.
        damage_model_hypothesis_scenario=damage_model_hypothesis,
        # DAMAGE-HP-LINK-001.  None unless the flag was handed in, and
        # make_state_class refuses it alongside every other mode a second time.
        damage_hp_link_hypothesis_scenario=damage_hp_link_hypothesis,
        # REMOTE-PLAYER-DISPATCH-001.  None unless the flag was handed in, and
        # make_state_class refuses it alongside every other mode a second time.
        remote_player_hypothesis_scenario=remote_player_hypothesis,
        # NPC-HOSTILE-DISPATCH.  None unless the flag was handed in, and
        # make_state_class refuses it alongside every other mode a second time.
        npc_hostile_hypothesis_scenario=npc_hostile_hypothesis,
        # NPC-HP-LINK-003 joins the flag to the branch.  The runtime.py branch
        # _dispatch_npc_hp_link_hypothesis exists (NPC-HP-LINK-002), so the
        # loaded scenario is handed through here exactly as every sibling lane
        # hands its own: None unless the flag was given, and make_state_class
        # refuses it alongside every other mode a second time.  Until this line
        # landed the CLI flag loaded a scenario the runtime never received and
        # an attended tester could not reach the lane at all.
        npc_hp_link_hypothesis_scenario=npc_hp_link_hypothesis,
        # MOVE-AUTHORITY-002.  None unless the flag was handed in, and
        # make_state_class refuses it alongside every other mode a second time.
        move_authority_hypothesis_scenario=move_authority_hypothesis,
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
