"""Transport-independent lifecycle session used by real adapters and loopback tests."""
from dataclasses import replace
import sys
import threading

from . import bag_admission
from .inventory import (
    HYPOTHESIZED_V111_SLOT2_BACKPACK,
)

class FoundationSession:
    def __init__(
        self, lifecycle, projector, login_name: str, *,
        allow_hypothesized_item_move: bool = False,
        allow_hypothesized_item_swap: bool = False,
        allow_hypothesized_item_merge: bool = False,
        allow_soft_delete: bool = False,
    ):
        if type(allow_hypothesized_item_move) is not bool:
            raise TypeError("hypothesized item-move gate must be bool")
        if type(allow_hypothesized_item_swap) is not bool:
            raise TypeError("hypothesized item-swap gate must be bool")
        if allow_hypothesized_item_swap and not allow_hypothesized_item_move:
            raise ValueError(
                "HYP-PF-017 swap requires the item-move opt-in lane"
            )
        if type(allow_hypothesized_item_merge) is not bool:
            raise TypeError("hypothesized item-merge gate must be bool")
        if allow_hypothesized_item_merge and not allow_hypothesized_item_move:
            raise ValueError(
                "HYP-PF-018 merge requires the item-move opt-in lane"
            )
        if type(allow_soft_delete) is not bool:
            raise TypeError("soft-delete gate must be bool")
        self.lifecycle, self.projector = lifecycle, projector
        self.allow_hypothesized_item_move = allow_hypothesized_item_move
        self.allow_hypothesized_item_swap = allow_hypothesized_item_swap
        self.allow_hypothesized_item_merge = allow_hypothesized_item_merge
        self.allow_soft_delete = allow_soft_delete
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

    # PF-HYPOTHESIS-LEDGER: HYP-PF-015 active
    def soft_delete_character(self, selector: int) -> int:
        if not self.allow_soft_delete:
            raise PermissionError(
                "HYP-PF-015 soft delete requires its explicit opt-in scenario"
            )
        if self.selected is not None:
            raise PermissionError(
                "soft delete is a character-select-stage operation"
            )
        cid = self.lifecycle.soft_delete(self.session_id, selector)
        self.characters = self.lifecycle.store.list_characters(self.account_id)
        return cid

    def select_and_start(self, selector: int):
        selected = self.lifecycle.select(self.session_id, selector)
        backpack = self.lifecycle.backpack(self.session_id, selected)
        # Gate 2, per COO-DECISION 20260829_0441 (BAG_ADMISSION_WIRING).  The
        # first two terms of may_enter_world ARE the condition this line
        # carried before, in the same order.  TWO differences, both measured
        # by pf-adversary over 120,000 mutated bags -- there is no third:
        #   1. a golden bag that ACQUIRED rows is now ADMITTED (this is what
        #      M5 needs to survive a relog);
        #   2. with the opt-in ON, a value that fails require_backpack_shape
        #      is now REFUSED where the old bare `or allow_...` admitted it.
        #      Unreachable in production (gate 1 raises on such a value
        #      first), but it IS a state that used to pass here.
        # inventory.is_unmoved_baseline is NOT narrowed: it is may_enter_world's
        # first term unchanged, and the move/swap/merge family keeps the guard
        # it has.
        #
        # LEDGER PIN, DO NOT REFLOW AWAY: docs/HYPOTHESIS_LEDGER.json requires
        # the literal string "is_unmoved_baseline" to appear in this file
        # (HYP-PF-010, source_refs), and after this rewiring NO CODE carries
        # it -- only this comment block does (twice: the sentence above and
        # this note), which means the ledger check now passes on prose.  If
        # that pin should now name may_enter_world instead, amend the ledger
        # entry -- never delete the marker to make
        # tools/verify_hypothesis_ledger.py go green.
        if not bag_admission.may_enter_world(
            backpack,
            allow_hypothesized_item_move=self.allow_hypothesized_item_move,
        ):
            # Unconditional, not attended-only.  The PermissionError below
            # names HYP-PF-008, which is the wrong sentence for two of the
            # refusals this predicate returns (a malformed bag -- a real bug,
            # gate 1 should have raised first -- and a drifted header).
            # Without this line a structural fault reaches the operator
            # misattributed to a hypothesis that had nothing to do with it.
            #
            # A DIAGNOSTIC MAY NEVER ALTER DISPATCH (runtime.make_stdout_event
            # _exporter's rule, applied here).  pf-adversary measured TWO
            # stream states where the bare print changed what the caller
            # sees: a closed stderr turned this refusal into a ValueError
            # that runtime.py reports as BACKPACK_LOAD_REFUSED -- the exact
            # misattribution this line exists to prevent -- and a
            # BrokenPipeError escaped both of runtime.py's handlers and
            # unwound the listener thread in silence.  Both are swallowed
            # here, so the PermissionError below is what leaves this method,
            # always.  A THIRD state is NOT fixed and is not a dispatch bug:
            # with sys.stderr None (pythonw, no console) print() writes to
            # stdout, so the token lands in the run's .out.txt.  The durable
            # cure for that one is an event beside the print, which this
            # round did not add -- see the round letter.
            try:
                print(
                    bag_admission.console_line(
                        bag_admission.classify(backpack)
                    ),
                    file=sys.stderr,
                )
            except Exception:
                pass
            raise PermissionError(
                "HYP-PF-008 post-state requires its explicit opt-in scenario"
            )
        self.selected = selected
        self.backpack = backpack
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

    # PF-HYPOTHESIS-LEDGER: HYP-PF-008 active
    def move_hypothesized_v111_slot2(self) -> bool:
        if not self.allow_hypothesized_item_move:
            raise PermissionError(
                "HYP-PF-008 mutation requires its explicit opt-in scenario"
            )
        if self.selected is None or self.backpack is None:
            raise RuntimeError("no selected character Backpack")
        updated = self.lifecycle.move_hypothesized_v111_slot2(
            self.session_id, self.selected,
        )
        if updated is None:
            return False
        self.backpack = updated
        return True

    # PF-HYPOTHESIS-LEDGER: HYP-PF-010 active
    def move_backpack_item_to_free_slot(
        self, item_identity: int, destination_slot: int,
    ) -> bool:
        if not self.allow_hypothesized_item_move:
            raise PermissionError(
                "HYP-PF-010 mutation requires its explicit opt-in scenario"
            )
        if self.selected is None or self.backpack is None:
            raise RuntimeError("no selected character Backpack")
        updated = self.lifecycle.move_backpack_item_to_free_slot(
            self.session_id, self.selected, item_identity, destination_slot,
        )
        if updated is None:
            return False
        self.backpack = updated
        return True

    # PF-HYPOTHESIS-LEDGER: HYP-PF-017 active
    def swap_backpack_item_with_occupied_slot(
        self, item_identity: int, destination_slot: int,
    ) -> bool:
        if not self.allow_hypothesized_item_swap:
            raise PermissionError(
                "HYP-PF-017 mutation requires its explicit opt-in scenario"
            )
        if self.selected is None or self.backpack is None:
            raise RuntimeError("no selected character Backpack")
        updated = self.lifecycle.swap_backpack_item_with_occupied_slot(
            self.session_id, self.selected, item_identity, destination_slot,
        )
        if updated is None:
            return False
        self.backpack = updated
        return True

    # PF-HYPOTHESIS-LEDGER: HYP-PF-018 active
    def merge_backpack_item_into_occupied_slot(
        self, item_identity: int, destination_slot: int,
    ) -> bool:
        if not self.allow_hypothesized_item_merge:
            raise PermissionError(
                "HYP-PF-018 mutation requires its explicit opt-in scenario"
            )
        if self.selected is None or self.backpack is None:
            raise RuntimeError("no selected character Backpack")
        updated = self.lifecycle.merge_backpack_item_into_occupied_slot(
            self.session_id, self.selected, item_identity, destination_slot,
        )
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

    def soft_delete_character(self, _selector: int) -> int:
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

    def move_hypothesized_v111_slot2(self):
        raise PermissionError("scene-load milestone cannot mutate Backpack state")

    def move_backpack_item_to_free_slot(self, _item_identity, _destination_slot):
        raise PermissionError("scene-load milestone cannot mutate Backpack state")

    def swap_backpack_item_with_occupied_slot(self, _item_identity, _destination_slot):
        raise PermissionError("scene-load milestone cannot mutate Backpack state")

    def merge_backpack_item_into_occupied_slot(self, _item_identity, _destination_slot):
        raise PermissionError("scene-load milestone cannot mutate Backpack state")

    def close(self, _position=None):
        return False

    def close_connection(self) -> bool:
        return False
