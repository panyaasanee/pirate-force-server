from .actor_wire import bind_actor_and_avatar_identity, read_name
from .model import Position
from .world_scene_travel import is_position_persist_allowed, load_scene_registry
import hashlib
import unicodedata

class CharacterLifecycle:
    def __init__(self, store, default_position: Position, avatar_extractor=None):
        self.store, self.default_position = store, default_position
        self.avatar_extractor = avatar_extractor
        # Loaded once at boot (this object is a single long-lived instance,
        # see app.py) rather than per checkpoint -- the registry is static
        # committed content for the life of a run, and checkpoint() fires on
        # every movement tick (measured ~19 times in one short walk), not
        # just at login like most of this file's other registry readers.
        self._scene_registry = load_scene_registry()

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
        # CORE-REQUEST-018 / GT-106 (4).3: a character whose current scene is
        # pinned persist_position_allowed=False (today: scene 17, no return
        # path measured yet) must not have this checkpoint overwrite its
        # stored character_positions row at all -- writing scene_id=1 with
        # scene 17's XYZ (or scene 17 itself, which would then refuse the
        # character at next login per login_entry_allowed) is worse than
        # leaving the last-known-good row untouched. store.save_position
        # still verifies session/character ownership either way (pf-adversary
        # finding 1) -- a stale or hijacked session still raises here, only
        # the column write itself is skipped.
        allowed = is_position_persist_allowed(position.scene_id, self._scene_registry)
        self.store.save_position(session_id, character.id, position, write_position=allowed)

    def backpack(self, session_id, character):
        return self.store.get_backpack(session_id, character.id)

    def backpack_issued_through(self, session_id, character):
        # Route 1 (COO-DECISION 20260829_0848): gate 2 needs the identity
        # counter, and the admission predicate must not import store --
        # session reads it through here, the same indirection backpack()
        # above uses.
        return self.store.backpack_issued_through(session_id, character.id)

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

    # PF-HYPOTHESIS-LEDGER: HYP-PF-017 active
    def swap_backpack_item_with_occupied_slot(
        self, session_id, character, item_identity, destination_slot,
    ):
        return self.store.swap_backpack_item_with_occupied_slot(
            session_id, character.id, item_identity, destination_slot,
        )

    # PF-HYPOTHESIS-LEDGER: HYP-PF-018 active
    def merge_backpack_item_into_occupied_slot(
        self, session_id, character, item_identity, destination_slot,
    ):
        return self.store.merge_backpack_item_into_occupied_slot(
            session_id, character.id, item_identity, destination_slot,
        )

    def exit(self, session_id, character, position):
        # Same gate as checkpoint() above -- the session still closes either
        # way, only the position write is skipped. A stale/non-owning
        # session still raises PermissionError here and close_session below
        # never runs, exactly as before this gate existed.
        allowed = is_position_persist_allowed(position.scene_id, self._scene_registry)
        self.store.save_position(session_id, character.id, position, write_position=allowed)
        self.store.close_session(session_id)
