"""Lifecycle-aware V141 state factory for the real legacy TCP listeners."""
from .model import Position
from .scenario import is_p30_target_observation, make_p30_target
from .session import FoundationSession
from .scene_object import is_scene_remote_target, make_scene_remote_actor


def _active_arena_version(scenario) -> str:
    """Derive a label only while an opt-in Arena branch is active."""
    return "V2" if scenario.basic_faction is not None else "V1"


def make_state_class(legacy, lifecycle, projector, scenario=None,
                     scene_load_scenario=None, session_factory=None):
    if scenario is not None and scene_load_scenario is not None:
        raise ValueError("Arena and scene-load scenarios are mutually exclusive")
    class PersistentGameSessionState(legacy.GameSessionState):
        def __init__(self, token: str):
            super().__init__(token)
            self.foundation = (
                session_factory(token) if session_factory is not None
                else FoundationSession(lifecycle, projector, token)
            )
            self.arena_scenario = scenario
            self.arena_spawned = False
            self.arena_target_captured = False
            if scene_load_scenario is not None:
                # The load-only branch must never inherit V141 population.
                self.npc_spawn_sent = True
                self.population_indices = ()
                if scene_load_scenario.remote_actor is not None:
                    self.scene_remote_spawned = False
                    self.scene_remote_target_captured = False

        def dispatch(self, parsed):
            nested_id = parsed.nested_id
            if nested_id == legacy.LOGIN_VERIFY_VITAL:
                self.rx_frames += 1
                out = []
                if not self.login_ack_sent:
                    pc, frame = legacy.make_game_login_ack(self.token)
                    out.append(("LOGIN_VERIFY_ACK_ONCE", pc, frame, 0.0))
                    self.login_ack_sent = True
                    self.events.append("login_verify_seen")
                else:
                    self.events.append("duplicate_login_verify_suppressed")
                if not self.select_actor_sent:
                    pc, frame = self.foundation.character_list()
                    out.append(("FOUNDATION_CHARACTER_LIST_ONCE", pc, frame, 0.35))
                    self.select_actor_sent = True
                    self.events.append("select_actor_sent")
                return out
            if nested_id == legacy.CREATE_ACTOR_VITAL:
                self.rx_frames += 1
                self.create_actor_seen = True
                try:
                    parsed_create = legacy.parse_create_actor(parsed)
                except Exception as exc:
                    self.last_actor_summary = {"decode_error": repr(exc)}
                    self.events.append("create_actor_unparsed")
                    return []
                if not parsed_create:
                    self.events.append("create_actor_unparsed")
                    return []
                op, has_actor, wire = parsed_create
                self.events.append(f"create_actor_op{op}_has{has_actor}")
                if op != 1 or has_actor != 1 or not wire:
                    return []
                if self.create_actor_reply_sent:
                    self.events.append("duplicate_create_actor_suppressed")
                    return []
                try:
                    summary = legacy.decode_create_actor_data_ex(wire)
                    character, (pc, frame) = self.foundation.create(summary["name"], wire)
                except Exception as exc:
                    self.last_actor_summary = {
                        "decode_error": repr(exc), "wire_len": len(wire)
                    }
                    self.events.append("foundation_create_rejected_no_reply")
                    return []
                self.last_actor_summary = summary
                self.create_actor_reply_sent = True
                self.events.append("create_actor_success_echo_sent")
                return [("FOUNDATION_CREATE_COMMITTED", pc, frame, 0.10)]
            if nested_id == legacy.START_GAME_REQ:
                self.rx_frames += 1
                self.start_game_seen = True
                selector = legacy.parse_start_game_req(parsed)
                self.events.append(f"start_game_req_selector_{selector!r}")
                if selector is None or self.start_game_reply_sent:
                    return []
                try:
                    _, (pc, frame) = self.foundation.select_and_start(selector)
                except KeyError:
                    return []
                self.start_game_reply_sent = True
                self.events.append("start_game_res_scene_identity_sent")
                load_only = scene_load_scenario is not None
                actions = [(
                    "SCENE2_LOAD_ONLY_SELECTED_START_GAME" if load_only
                    else "FOUNDATION_SELECTED_START_GAME",
                    pc, frame, 0.10,
                )]
                if not self.teleport_sent:
                    if load_only:
                        p = scene_load_scenario.position
                        tp_pc, tp_frame = legacy.make_login_teleport(
                            p.scene_id, p.scene_seq, p.x, p.y, p.z,
                        )
                    else:
                        tp_pc, tp_frame = legacy.make_login_teleport(1, 0)
                    actions.append((
                        "SCENE2_LOAD_ONLY_TELEPORT_MARKER2_ONCE" if load_only
                        else "V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE",
                        tp_pc, tp_frame, 0.70,
                    ))
                    self.teleport_sent = True
                    self.events.append(
                        "scene2_load_only_marker2_teleport_sent" if load_only else
                        "v135_startgame_movement_p0_minus100x_minus50y_teleport_zero_sent"
                    )
                return actions

            durable_target = legacy.parse_v141_refresh_target_pos(parsed)
            remote = scene_load_scenario.remote_actor if scene_load_scenario is not None else None
            if (
                remote is not None and not self.scene_remote_spawned
                and self.runtime_ack_sent and self.teleport_sent
                and self.foundation.selected is not None
                and nested_id == legacy.TARGET_POS_VITAL
            ):
                if durable_target is None:
                    return []
                pc, frame = make_scene_remote_actor(legacy, remote)
                self.scene_remote_spawned = True
                self.events.append("scene2_p60_mobs34_single_committed")
                return [("SCENE2_P60_MOBS34_SINGLE_INITIAL", pc, frame, 0.0)]
            if remote is not None and self.scene_remote_spawned and is_scene_remote_target(
                legacy, parsed, remote.actor_identity,
            ):
                if not self.scene_remote_target_captured:
                    self.scene_remote_target_captured = True
                    self.events.append("scene2_p60_target_kind2_captured_no_reply")
                return []
            arena_actions = []
            suppress_inherited_population = (
                self.arena_scenario is not None
                and not self.arena_spawned
                and self.runtime_ack_sent
                and self.teleport_sent
                and self.foundation.selected is not None
                and nested_id == legacy.TARGET_POS_VITAL
            )
            if suppress_inherited_population and (
                durable_target is None
                or self.foundation.selected.position.scene_id
                != self.arena_scenario.scene_id
            ):
                # Before Arena population exists, TargetPos is either the exact
                # trigger or a complete no-op.  Never let the broader frozen
                # dispatcher retain malformed coordinates for a later frame.
                return []
            if (
                self.arena_scenario is not None
                and not self.arena_spawned
                and self.runtime_ack_sent
                and self.teleport_sent
                and self.foundation.selected is not None
                and self.foundation.selected.position.scene_id == self.arena_scenario.scene_id
                and durable_target is not None
            ):
                pc, frame, target = make_p30_target(
                    legacy, self.arena_scenario, durable_target,
                )
                # Commit scenario state before queueing and suppress the inherited
                # P0/P30/P91 population branch for this opt-in session only.
                self.arena_spawned = True
                self.npc_spawn_sent = True
                self.population_indices = (legacy.V112_MONSTER_INDEX,)
                self.population_refresh_anchor = tuple(durable_target[:3])
                arena_version = _active_arena_version(self.arena_scenario)
                version = arena_version.lower()
                self.events.append(f"arena_{version}_p30_test_only_population_committed")
                arena_actions = [
                    (f"ARENA_{arena_version}_P30_INITIAL", pc, frame, 0.0),
                    (f"ARENA_{arena_version}_P30_MODEL_READY_REAPPLY", pc, frame,
                     self.arena_scenario.reapply_ms / 1000.0),
                ]

            actions = super().dispatch(parsed)
            if (
                scene_load_scenario is None
                and
                durable_target is not None
                and self.foundation.selected is not None
            ):
                x, y, z, heading, _flags, _moving = durable_target
                selected = self.foundation.selected
                candidate = Position(
                    selected.position.scene_id,
                    selected.position.scene_seq,
                    x, y, z, heading,
                )
                if candidate != selected.position:
                    self.foundation.checkpoint(candidate)

            if self.arena_scenario is not None and self.arena_spawned:
                if (
                    is_p30_target_observation(legacy, parsed)
                    and not self.arena_target_captured
                ):
                    self.arena_target_captured = True
                    version = _active_arena_version(self.arena_scenario).lower()
                    self.events.append(
                        f"arena_{version}_p30_target_kind2_captured_no_reply"
                    )
            return actions + arena_actions
    return PersistentGameSessionState
