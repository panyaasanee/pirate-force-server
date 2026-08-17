from .actor_wire import bind_actor_and_avatar_identity, read_name
from .model import Position
import hashlib
import unicodedata

class CharacterLifecycle:
    def __init__(self, store, default_position: Position, avatar_extractor=None):
        self.store, self.default_position = store, default_position
        self.avatar_extractor = avatar_extractor

    def login(self, login_name: str):
        aid = self.store.ensure_account(login_name)
        sid = self.store.open_session(aid)
        try:
            characters = self.store.list_characters(aid)
        except BaseException as error:
            try:
                self.store.close_session(sid)
            except BaseException as close_error:
                error.add_note(
                    f"Foundation session cleanup also failed: {close_error!r}"
                )
            raise
        return aid, sid, characters

    def create(self, account_id: int, name: str, submitted_wire: bytes):
        if self.avatar_extractor is None:
            raise ValueError("opaque AvatarAttr extractor is required")
        normalized = unicodedata.normalize("NFKC", name).strip()
        if not normalized:
            raise ValueError("empty character name")
        if name != normalized:
            raise ValueError(
                "character name must already be NFKC-normalized without surrounding whitespace"
            )
        if read_name(submitted_wire) != name:
            raise ValueError("character name does not match CreateActorDataEx")
        name_key = normalized.casefold()
        fingerprint = hashlib.sha256(submitted_wire).hexdigest()

        def build(selector):
            lo = 0x10000000 + account_id * 0x10000 + selector + 1
            if lo > 0xFFFFFFFF:
                raise OverflowError("server character identity exhausted")
            hi = 0
            wire, avatar_wire = bind_actor_and_avatar_identity(
                submitted_wire, lo, hi, selector, self.avatar_extractor
            )
            return wire, avatar_wire, lo, hi

        return self.store.create_character(
            account_id, normalized, name_key, fingerprint, build,
            self.default_position,
        )

    def select(self, session_id: str, selector: int):
        return self.store.select_character(session_id, selector)

    # PF-HYPOTHESIS-LEDGER: HYP-PF-015 active
    def soft_delete(self, session_id: str, selector: int) -> int:
        return self.store.soft_delete_character(session_id, selector)

    def checkpoint(self, session_id, character, position):
        self.store.save_position(session_id, character.id, position)

    def backpack(self, session_id, character):
        return self.store.get_backpack(session_id, character.id)

    def merge_v111_stack(self, session_id, character):
        return self.store.apply_v111_stack_merge(session_id, character.id)

    # PF-HYPOTHESIS-LEDGER: HYP-PF-008 active
    def move_hypothesized_v111_slot2(self, session_id, character):
        return self.store.apply_hypothesized_v111_slot2_move(
            session_id, character.id,
        )

    # PF-HYPOTHESIS-LEDGER: HYP-PF-010 active
    def move_backpack_item_to_free_slot(
        self, session_id, character, item_identity, destination_slot,
    ):
        return self.store.move_backpack_item_to_free_slot(
            session_id, character.id, item_identity, destination_slot,
        )

    def exit(self, session_id, character, position):
        self.store.save_position(session_id, character.id, position)
        self.store.close_session(session_id)
