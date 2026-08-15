"""Lifecycle-aware V141 state factory for the real legacy TCP listeners."""
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
                    out.append(("LOGIN_VERIFY_ACK_ONCE", pc, frame, 0.0)); self.login_ack_sent = True
                if not self.select_actor_sent:
                    pc, frame = self.foundation.character_list()
                    out.append(("FOUNDATION_CHARACTER_LIST_ONCE", pc, frame, 0.35)); self.select_actor_sent = True
                return out
            if nested_id == legacy.CREATE_ACTOR_VITAL:
                self.rx_frames += 1
                parsed_create = legacy.parse_create_actor(parsed)
                if not parsed_create: return []
                op, has_actor, wire = parsed_create
                if op != 1 or has_actor != 1 or not wire or self.create_actor_reply_sent: return []
                summary = legacy.decode_create_actor_data_ex(wire)
                character, (pc, frame) = self.foundation.create(summary["name"], wire)
                self.last_actor_summary = summary; self.create_actor_reply_sent = True
                return [("FOUNDATION_CREATE_COMMITTED", pc, frame, 0.10)]
            if nested_id == legacy.START_GAME_REQ:
                self.rx_frames += 1
                selector = legacy.parse_start_game_req(parsed)
                if selector is None or self.start_game_reply_sent: return []
                try:
                    _, (pc, frame) = self.foundation.select_and_start(selector)
                except KeyError:
                    return []
                self.start_game_seen = True; self.start_game_reply_sent = True
                return [("FOUNDATION_SELECTED_START_GAME", pc, frame, 0.10)]
            return super().dispatch(parsed)
    return PersistentGameSessionState
