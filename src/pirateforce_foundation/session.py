"""Transport-independent lifecycle session used by real adapters and loopback tests."""
from dataclasses import replace
import sys
import threading

from . import bag_admission
from . import login_speed
from . import persistence_login_vitals as login_vitals
from . import player_wire
from .inventory import (
    HYPOTHESIZED_V111_SLOT2_BACKPACK,
)


def _class_id_on_the_row(store, character_id):
    """The row's stored `class_id`, or None -- and it never raises.

    `COO-DECISION 20260904_0446` point 3 and `COO-DECISION 20260903_1943`
    point 3: a login must not fail because this column could not be read.
    Every reason it cannot be read -- no store, no character id, a character
    soft-deleted between select and here (`KeyError`), a database whose typed
    columns are missing (`SchemaDriftError`), a stub store in another lane's
    test that has no such method (`AttributeError`) -- lands on the same
    answer as a NULL column: None, meaning "the composer's own constant".
    That matters beyond tidiness: `runtime.py`'s START_GAME_REQ handler
    catches KeyError, PermissionError, ValueError and RuntimeError only, and
    v141 wraps the per-connection loop in try/finally with no except at all,
    so anything else escaping here parks the client on "connecting" forever.

    `read_typed_attributes` is LANE-DB's own read method and returns only the
    columns that are NOT NULL, so a `.get` is the whole contract: a character
    created before this seam existed has no key and stays on the constant.
    """
    if store is None or character_id is None:
        return None
    try:
        return store.read_typed_attributes(character_id).get("class_id")
    except Exception:
        return None


def _class_id_console_line(character) -> str:
    """One ASCII line, read off the character the frame will be built from.

    It asks the CHARACTER, not the resolution, for the same reason
    `login_vitals.console_line_after_apply` does (`COO-DECISION 20260903_0647`
    point 2): printing the read instead of the applied value puts
    `from_row class_id=4` on the console of a login whose frame then carries
    the composer's literal, and it is loudest exactly when the seam is
    broken.  Never raises, always returns a str.
    """
    try:
        value = getattr(character, "class_id", None)
    except Exception:
        value = None
    if value is None:
        return (
            "LOGIN_CLASS_ID fallback class_id="
            f"{player_wire.PLAYER_LOGIN_CLASS_ID} reason=row_has_no_class_id"
        )
    return f"LOGIN_CLASS_ID from_row class_id={value}"

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
        # COO-DECISION 20260829_0848 (route 1): gate 2's acquired-row
        # criterion is the identity counter, and bag_admission must not
        # import store -- so the counter is read HERE (through lifecycle,
        # the same indirection backpack() uses) and threaded in.
        # backpack_issued_through is INCLUSIVE (column minus one; see
        # store.py's own EXCLUSIVE/INCLUSIVE trap note).
        issued_through = self.lifecycle.backpack_issued_through(
            self.session_id, selected,
        )
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
            issued_through=issued_through,
        ):
            # Unconditional, not attended-only.  The PermissionError below
            # names HYP-PF-008, which is the wrong sentence for THREE of the
            # refusals this predicate returns (a malformed bag -- a real bug,
            # gate 1 should have raised first -- a drifted header, and since
            # round hsz32u a counter refusal: acquired_identity_not_issued,
            # e.g. a store whose next_item_identity fell behind the bag
            # after a partial restore).  Without this line a structural
            # fault reaches the operator misattributed to a hypothesis that
            # had nothing to do with it -- the stderr token below is the
            # line that names the true reason.
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
                # Same issued_through as the gate above, so the console line
                # names the SAME refusal the gate returned -- a bare
                # classify() here could report golden_plus_acquired for a
                # bag the gate just refused on the counter.
                print(
                    bag_admission.console_line(
                        bag_admission.classify(
                            backpack, issued_through=issued_through,
                        )
                    ),
                    file=sys.stderr,
                )
            except Exception:
                pass
            raise PermissionError(
                "HYP-PF-008 post-state requires its explicit opt-in scenario"
            )
        # CORE-REQUEST `pf_bridge/notes_to_chief/20260902_2010` (COO-DECISION
        # 20260902_1846 point 3): the ONE place the row is read for a login's
        # movement speed.  It happens here, and not in the projector or in
        # player_wire, because this is the last layer that still holds both a
        # store and a character id; below this the composers are pure.
        #
        # The value is attached to the selected character rather than passed
        # as an argument.  `start_game` is called up to three MORE times per
        # production login by runtime.py -- the faction recompose runs on
        # EVERY flagless login and replaces pc/frame outright -- and each of
        # those passes `self.foundation.selected`.  Threading the speed only
        # into the call below would therefore have been a change the very
        # next recompose puts straight back to 400.0: visible in a unit test,
        # invisible on the wire.  (R309's lesson, written into that round
        # file: a call site that seizes the frame has to be asked who it is
        # taking that frame away from.)
        #
        # Nothing here can fail a login.  `resolve_for_character` answers with
        # the constant -- exactly what main sends today -- for a read that
        # raises, a column with no value, or a value the wire validator
        # refuses, and it names which of those happened on the console.
        #
        # !! BOTH LOOKUPS GO THROUGH `getattr`, AND THAT IS NOT DEFENSIVE
        # HABIT -- pf-adversary measured the direct form killing three
        # existing tests and, in production, the listener thread.  Before
        # this change `select_and_start` asked `lifecycle` for `select`
        # and `backpack` only, and asked `selected` for nothing at all;
        # `self.lifecycle.store.…` and `selected.id` silently widened both
        # contracts ONE LINE ABOVE the try that is supposed to make this
        # non-fatal.  `AttributeError` is exactly the class runtime.py's
        # START_GAME_REQ handler does not catch (it catches KeyError,
        # PermissionError, ValueError, RuntimeError), and v141 wraps the
        # per-connection loop in try/finally with no except at all -- so
        # the thread unwinds with the client parked on "connecting".
        # `None` here reaches `resolve_for_character`'s own try and comes
        # back as ROW_COULD_NOT_BE_READ carrying the constant, which is
        # the behaviour this whole seam promises for a read it cannot do.
        resolved = login_speed.resolve_for_character(
            getattr(self.lifecycle, "store", None),
            getattr(selected, "id", None),
            fallback=player_wire.PLAYER_LOGIN_MOVEMENT_SPEED,
        )
        # SAY IT ON THE WAY THROUGH, NOT ONLY ON THE WAY OUT.  The first
        # draft printed refusals only, which put a token on the console for
        # the non-goal and none on the goal -- and the goal is precisely
        # what `gm/speed_wire.py`'s SPEED_LOGIN_READ_LANDED gate wants
        # somebody to be able to point at on `main`.  A refusal that says
        # nothing is equally useless (R309 defect D3), so BOTH are printed:
        # one ASCII line per login, wrapped for the same reason every other
        # print in this file is -- a closed or broken stderr must not
        # become this login's exception (R309 defect D4).
        try:
            print(resolved.console_line(), file=sys.stderr)
        except Exception:
            pass
        # `replace` needs a dataclass, which is the third contract this
        # seam must not silently widen: a stub `selected` in somebody
        # else's test raises TypeError here just as surely as the two
        # lookups above did.  Falling back to the unmodified object gives
        # that caller main's behaviour instead of a crash.
        if resolved.came_from_the_row:
            try:
                selected = replace(selected, movement_speed=resolved.value)
            except TypeError:
                pass
        # THE LOGIN-VITALS SEAM, AND IT IS ONE CALL POINT (COO-DECISION
        # 20260903_0447 and 0647).  A second `resolve_for_character` in this
        # method would not just cost a read: that function WRITES on the
        # dead-row branch, so two resolves of one login are two revives.
        # `tests/test_persistence_login_vitals.py::TheOneLoginSeamTests`
        # grades this shape from the other side -- both doors called, the
        # return value kept, the resolver called at most once.
        #
        # THE FALLBACKS ARE CONSOLE-ONLY, AND THE FIRST DRAFT OF THIS COMMENT
        # CLAIMED A MECHANISM THAT DOES NOT EXIST (`pf-adversary` defect D2).
        # It said the constants here are why an unreadable row composes the
        # frame `main` composes -- they are not.  A fallback value can never
        # reach the wire: every reason that carries one is outside
        # `WIRE_TAKES_THE_ROWS_NUMBERS`, so `wire_kwargs()` is `{}`, the apply
        # returns the character untouched, and `start_game` sees three `None`s
        # and uses the COMPOSER'S OWN SIGNATURE DEFAULTS.  What these three
        # constants actually decide is the numbers printed on the console when
        # the row could not be used -- which is worth getting right (a login
        # that prints numbers it did not send is a lie an operator acts on)
        # but is not why the frame is unchanged.  Measured: drifting all three
        # to 99/1/7 left 140 tests green and put `level=99 hp=1/7` on the
        # console of a login that sent 1/100/100.
        #
        # The two lookups are `getattr` for the reason the speed seam above
        # spells out at length: a missing `store` or `id` must arrive as
        # ROW_COULD_NOT_BE_READ, not as an `AttributeError` runtime.py's
        # START_GAME_REQ handler does not catch.
        vitals = login_vitals.resolve_for_character(
            getattr(self.lifecycle, "store", None),
            getattr(selected, "id", None),
            fallback_level=player_wire.PLAYER_LOGIN_LEVEL,
            fallback_hp_current=player_wire.PLAYER_LOGIN_HP_CURRENT,
            fallback_hp_max=player_wire.PLAYER_LOGIN_HP_MAX,
        )
        # PRINTED AFTER THE APPLY, AND THE LINE ASKS THE CHARACTER WHETHER IT
        # CARRIES THE ROW (COO-DECISION 20260903_0647 point 2).  Printing the
        # resolution alone BEFORE the apply -- which is what the speed seam
        # above does -- puts `from_row level=7 hp=37/250` on the console of a
        # login whose frame then carries the composer's literals, and it is
        # loudest exactly when the seam is most broken.
        #
        # ONE NAME, NOT TWO, AND THAT IS THE REPAIR OF `pf-adversary` DEFECT
        # D1.  The first draft kept the pre-apply object beside the post-apply
        # one and had the console compare them; hoisting the rebinding above
        # the print then made both arguments the same object and printed the
        # loud REFUSED token on every CORRECT login, with 140 tests green.
        # `console_line_after_apply` now reads the three fields off the
        # character it is given -- the same three `legacy_bridge.start_game`
        # reads to build the frame -- so there is no earlier object to get
        # wrong.  It never raises and always returns a str; the wrapper is for
        # a closed or broken stderr, same as the print above it.
        selected = login_vitals.apply_to_character(selected, vitals)
        try:
            print(
                login_vitals.console_line_after_apply(vitals, selected),
                file=sys.stderr,
            )
        except Exception:
            pass
        # THE CLASS SHE PICKED, from the row, once per login (CORE-REQUEST of
        # `pf_bridge/notes_to_chief/20260904_0423` point 2.2, granted by
        # `COO-DECISION 20260904_0446` point 3).  Same three moves as the two
        # seams above: read without ever raising, rebind onto the character so
        # every `start_game` recompose composes it too, then say on the
        # console what the character now carries.
        #
        # THE PRINT IS HERE AND NOT IN `legacy_bridge.start_game` on purpose:
        # that function runs up to four times per production login, so a line
        # printed there would repeat a per-login fact four times and make a
        # fallback look like four failures.  This is the one place a login
        # passes through exactly once.
        class_id = _class_id_on_the_row(
            getattr(self.lifecycle, "store", None), getattr(selected, "id", None),
        )
        if class_id is not None:
            # `replace` needs a dataclass; a stub `selected` in another lane's
            # test raises TypeError, and falling back to the unmodified object
            # gives that caller main's behaviour instead of a crash -- the
            # same guard the speed seam above uses.
            try:
                selected = replace(selected, class_id=class_id)
            except TypeError:
                pass
        try:
            print(_class_id_console_line(selected), file=sys.stderr)
        except Exception:
            pass
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
        # !! THIS SESSION DOES **NOT** READ THE ROW'S SPEED, AND THAT IS A
        # MEASURED DECISION RATHER THAN AN OVERSIGHT.  A pf-adversary pass
        # raised the inconsistency correctly -- this class holds `self.store`
        # and the character's id, so the same character could compose two
        # different ActorAttrs depending on whether the server was booted
        # with `--scene-load`, and that is a real cost.  It was implemented,
        # and then `tests/test_action_ack.py::test_port_royal_faction1_start_
        # game_projection_is_allowed_end_to_end` went red and named the
        # bigger cost: that test guards this milestone by snapshotting the
        # database file AND ITS SIDECARS around a StartGame and requiring
        # them byte-identical.  `store.read_typed_attributes` opens its own
        # connection, so merely READING creates `-wal` and `-shm` where
        # there were none.  "Read-only" here means the process leaves no
        # trace on disk, not just that it issues no UPDATE.
        #
        # So the divergence stays, and it is a NONCLAIM rather than a
        # silence: a `--scene-load` boot composes the constant even when the
        # row holds another number.  Closing it needs a read that does not
        # open a connection (the caller handing the value in, or a
        # store-level cache), which is a different change with a different
        # owner -- not something to sneak in behind a scenario flag.
        selected = matches[0]
        self.selected = selected
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
