"""Transport-independent lifecycle session used by real adapters and loopback tests."""
from dataclasses import replace
import threading

class FoundationSession:
    def __init__(self, lifecycle, projector, login_name: str):
        self.lifecycle, self.projector = lifecycle, projector
        self.selected = None
        self.backpack = None
        self._closed = False
        self._close_lock = threading.RLock()
        # Everything that can fail locally is initialized before login opens a
        # lease.  Once login returns, only plain attribute assignment remains.
        self.account_id, self.session_id, self.characters = lifecycle.login(login_name)

    def character_list(self):
        self.characters = self.lifecycle.store.list_characters(self.account_id)
        return self.projector.character_list(self.characters)

    def create(self, name: str, actor_wire: bytes):
        character = self.lifecycle.create(self.account_id, name, actor_wire)
        self.characters = self.lifecycle.store.list_characters(self.account_id)
        return character, self.projector.create_success(character)

    def select_and_start(self, selector: int):
        self.selected = self.lifecycle.select(self.session_id, selector)
        self.backpack = self.lifecycle.backpack(self.session_id, self.selected)
        return self.selected, self.projector.start_game(
            self.selected, backpack=self.backpack,
        )

    def merge_v111_stack(self) -> bool:
        if self.selected is None or self.backpack is None:
            raise RuntimeError("no selected character Backpack")
        updated = self.lifecycle.merge_v111_stack(self.session_id, self.selected)
        if updated is None:
            return False
        self.backpack = updated
        return True

    def checkpoint(self, position):
        if self.selected is None:
            raise RuntimeError("no selected character")
        self.lifecycle.checkpoint(self.session_id, self.selected, position)
        self.selected = replace(self.selected, position=position)

    def close(self, position=None):
        with self._close_lock:
            if self._closed:
                return False
            if self.selected and position:
                self.lifecycle.exit(self.session_id, self.selected, position)
                self.selected = replace(self.selected, position=position)
            else:
                self.lifecycle.store.close_session(self.session_id)
            self._closed = True
            return True

    def close_connection(self) -> bool:
        """Close this exact lease without rewriting its last position."""
        with self._close_lock:
            if self._closed:
                return False
            self.lifecycle.store.close_session(self.session_id)
            self._closed = True
            return True


class ReadOnlyFoundationSession:
    """Existing-character projection with no database write path."""
    def __init__(self, store, projector, login_name: str, scenario):
        self.store, self.projector, self.scenario = store, projector, scenario
        self.account_id, characters = store.list_characters_for_login_read_only(login_name)
        self.characters = [
            character for character in characters
            if character.name == scenario.required_character_name
        ]
        if len(self.characters) != 1:
            raise KeyError(scenario.required_character_name)
        self.selected = None
        self.backpack = None

    def character_list(self):
        return self.projector.character_list(self.characters)

    def create(self, _name: str, _actor_wire: bytes):
        raise PermissionError("scene-load milestone is read-only")

    def select_and_start(self, selector: int):
        matches = [character for character in self.characters if character.selector == selector]
        if len(matches) != 1:
            raise KeyError(selector)
        self.selected = matches[0]
        # PF-HYPOTHESIS-LEDGER: HYP-PF-001 frozen
        # PF-HYPOTHESIS-LEDGER: HYP-PF-007 frozen
        # PF-HYPOTHESIS-LEDGER: GEO-PF-002 frozen
        # PF-HYPOTHESIS-LEDGER: GEO-PF-003 frozen
        return self.selected, self.projector.start_game(
            self.selected, self.scenario.position,
            self.scenario.player_basic_faction,
        )

    def checkpoint(self, _position):
        raise PermissionError("scene-load milestone cannot checkpoint")

    def merge_v111_stack(self):
        raise PermissionError("scene-load milestone cannot mutate Backpack state")

    def close(self, _position=None):
        return False

    def close_connection(self) -> bool:
        return False
