from .actor_wire import bind_identity_and_selector
from .model import Position

class CharacterLifecycle:
    def __init__(self, store, default_position: Position, avatar_extractor=None):
        self.store, self.default_position = store, default_position
        self.avatar_extractor = avatar_extractor

    def login(self, login_name: str):
        aid = self.store.ensure_account(login_name)
        sid = self.store.open_session(aid)
        return aid, sid, self.store.list_characters(aid)

    def create(self, account_id: int, name: str, submitted_wire: bytes):
        used = {c.selector for c in self.store.list_characters(account_id)}
        selector = next((n for n in range(256) if n not in used), None)
        if selector is None: raise ValueError("no selector available")
        lo, hi = 0x10000000 + account_id * 0x10000 + selector + 1, 0
        wire = bind_identity_and_selector(submitted_wire, lo, hi, selector)
        if self.avatar_extractor is None:
            raise ValueError("opaque AvatarAttr extractor is required")
        avatar_wire = self.avatar_extractor(wire)
        return self.store.create_character(account_id, selector, name, wire, avatar_wire, lo, hi, self.default_position)

    def select(self, session_id: str, selector: int):
        return self.store.select_character(session_id, selector)

    def exit(self, session_id, character, position):
        self.store.save_position(character.id, position)
        self.store.close_session(session_id)
