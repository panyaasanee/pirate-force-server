"""Transport-independent lifecycle session used by real adapters and loopback tests."""
from dataclasses import replace

class FoundationSession:
    def __init__(self, lifecycle, projector, login_name: str):
        self.lifecycle, self.projector = lifecycle, projector
        self.account_id, self.session_id, self.characters = lifecycle.login(login_name)
        self.selected = None

    def character_list(self):
        self.characters = self.lifecycle.store.list_characters(self.account_id)
        return self.projector.character_list(self.characters)

    def create(self, name: str, actor_wire: bytes):
        character = self.lifecycle.create(self.account_id, name, actor_wire)
        self.characters = self.lifecycle.store.list_characters(self.account_id)
        return character, self.projector.create_success(character)

    def select_and_start(self, selector: int):
        self.selected = self.lifecycle.select(self.session_id, selector)
        return self.selected, self.projector.start_game(self.selected)

    def checkpoint(self, position):
        if self.selected is None:
            raise RuntimeError("no selected character")
        self.lifecycle.checkpoint(self.session_id, self.selected, position)
        self.selected = replace(self.selected, position=position)

    def close(self, position=None):
        if self.selected and position:
            self.lifecycle.exit(self.session_id, self.selected, position)
        else:
            self.lifecycle.store.close_session(self.session_id)
