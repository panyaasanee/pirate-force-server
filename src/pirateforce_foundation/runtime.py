"""Lifecycle-aware V141 state factory for the real legacy TCP listeners."""
from .model import Position
from .session import FoundationSession

def make_state_class(legacy, lifecycle, projector):
    class PersistentGameSessionState(legacy.GameSessionState):
        def __init__(self, token: str):
            super().__init__(token)
            self.foundation = FoundationSession(lifecycle, projector, token)

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
                actions = [("FOUNDATION_SELECTED_START_GAME", pc, frame, 0.10)]
                if not self.teleport_sent:
                    tp_pc, tp_frame = legacy.make_login_teleport(1, 0)
                    actions.append((
                        "V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE",
                        tp_pc, tp_frame, 0.70,
                    ))
                    self.teleport_sent = True
                    self.events.append(
                        "v135_startgame_movement_p0_minus100x_minus50y_teleport_zero_sent"
                    )
                return actions

            actions = super().dispatch(parsed)
            durable_target = legacy.parse_v141_refresh_target_pos(parsed)
            if (
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
            return actions
    return PersistentGameSessionState
