from .actor_wire import bind_actor_and_avatar_identity, read_name
from .model import Position
from .world_scene_travel import is_position_persist_allowed, load_scene_registry
import hashlib
import sys
import unicodedata


def _say(line: str) -> None:
    """One ASCII console line, and never this login's or create's exception.

    Same wrapper discipline every other print on a request path in this
    package uses (`session.py`): a closed or broken stderr must not become
    the caller's error.  ASCII only, because the bridge console is cp874.
    """
    try:
        print(line, file=sys.stderr)
    except Exception:
        pass


def persist_class_id_from_starting_gear(store, character) -> int | None:
    """Write the class the player picked onto the row she just created.

    CORE-REQUEST of `pf_bridge/notes_to_chief/20260904_0423_LANE-DB-CORE-
    REQUEST-class-id-resolver-built-needs-two-hookups.md` point 2.2, granted
    to this file by `COO-DECISION 20260904_0446` points 1-2.  This is THE ONE
    caller Rule 14.13(d) is lifted for (`tests/test_world_avatar_attr.py::
    ...::test_no_module_outside_this_file_mentions_this_module` names this
    file and only this file); a second caller is still red there.

    WHAT IT DOES.  Decode the AvatarAttr body the store just stored, read the
    three starting-gear slots, and ask `persistence_class_id.resolve_class_id`
    which of the five committed `CHARCREATE_CLASS` presets they are.  A class
    id comes back only on an exact, unambiguous match; `None` -- no match, a
    body missing one of the three slots, a body that will not decode -- writes
    NOTHING and leaves the column NULL, which is the fail-closed answer
    `COO-DECISION 20260901_1059` requires: "unknown" is a named gap, never a
    guess.  Nothing here can write a class id that was not read verbatim off a
    sourced table row.

    WHY IT NEVER RAISES.  It runs AFTER `store.create_character` returned, so
    the character row and its position and backpack rows are committed and
    visible.  Raising from here would report "character creation failed" to a
    client whose character exists -- the client would then be looking at a
    list containing the character it was just told it could not have.  So the
    only outcomes are: the column is written, or it stays NULL and the console
    says which reason.  The exception's TYPE is printed, never its text: a
    message can carry a character name, and a non-ASCII byte on the bridge's
    cp874 console kills the tool that is reading it.

    WHY THE WRITE IS NULL-ONLY (pf-adversary D2 on `#705`, `COO-DECISION
    20260904_0549` item 1).  A re-sent `CreateActorDataEx` replays this
    call on the SAME row through `create_character`'s create-fingerprint
    retry path, and an unconditional write here would silently revert a
    class id another writer (LANE-DB's NULL-only backfill, `COO-DECISION
    20260904_0445`) already set on that row between the two attempts.
    `store.write_typed_attribute_if_unset` closes that inside one
    transaction; a caller-side read-then-write would reopen the same race.

    Returns the class id written, or `None` on any of the four reasons
    nothing was written: unresolvable body, no single preset match, the
    write refused (soft-deleted row), or the column already held a value
    from another writer -- that last one is not a failure, it is the guard
    doing its job.
    """
    from . import persistence_class_id
    from . import world_avatar_attr

    character_id = getattr(character, "id", None)
    try:
        body = world_avatar_attr.decode_avatar_attr(
            getattr(character, "avatar_wire", None)
        )
        resolved = persistence_class_id.resolve_class_id(
            body.named("n_DRESS_CHEST"),
            body.named("n_DRESS_LEGGINGS"),
            body.named("n_SLOT_RHAND"),
        )
    except Exception as error:
        _say(
            f"CHARACTER_CLASS_ID cid={character_id} not_written "
            f"reason=avatar_body_unreadable ({type(error).__name__})"
        )
        return None
    if resolved is None:
        _say(
            f"CHARACTER_CLASS_ID cid={character_id} not_written "
            "reason=starting_gear_matches_no_single_preset"
        )
        return None
    try:
        wrote = store.write_typed_attribute_if_unset(
            character_id, "class_id", resolved
        )
    except Exception as error:
        _say(
            f"CHARACTER_CLASS_ID cid={character_id} not_written "
            f"reason=write_refused ({type(error).__name__})"
        )
        return None
    if wrote is None:
        _say(
            f"CHARACTER_CLASS_ID cid={character_id} not_written "
            "reason=already_set"
        )
        return None
    _say(f"CHARACTER_CLASS_ID cid={character_id} written class_id={wrote}")
    return wrote


def _class_id_for_a_retried_skill_grant(store, character_id) -> "int | None":
    """The row's OWN `class_id`, but only when nothing has been granted yet.

    Exists for exactly one caller, `CharacterLifecycle.create`, for the
    retry gap `pf-adversary` measured in this round's first cut of the
    starting-skill hookup: gating the grant on
    `persist_class_id_from_starting_gear`'s return made a transient failure
    inside `store.grant_starting_skills` (a locked database, or any of the
    exceptions `grant_starting_skills_for_class`'s own `try` is written to
    catch) PERMANENT. That return is `None` on every later create-
    fingerprint retry of a character whose `class_id` already landed --
    by design, it is the NULL-only guard doing its job -- so once the
    winning attempt's grant call failed, the column would never again
    report as freshly-resolved and nothing would ever ask for the grant a
    second time. No backfill closes that gap the way LANE-DB's own
    `persistence_class_id_backfill` closes the equivalent gap for
    `class_id` itself.

    So a resend that finds the column already set falls back to reading it
    here -- but ONLY when `store.list_character_skills` for this character
    is still empty. That is what tells "the winning attempt wrote class_id
    but its own grant call then failed" (retry, correctly) apart from "a
    prior attempt already wrote both class_id AND its skills, and a
    DIFFERENT writer has since corrected class_id to something else"
    (`pf-adversary` D2 on `#705`, the scenario `tests/test_class_id_login_
    wiring.py::StartingSkillHookupTests::
    test_a_retry_after_another_writer_corrects_the_class_grants_nothing_new`
    pins) -- there, skills are not empty, and this function must not fire
    a second, now-mismatched grant. Re-granting through the corrected
    class_id's own kit in that second case is not attempted:
    `grant_starting_skills` has no matching "revoke" half, so it could
    only ever add a second kit on top, and this module does not guess
    whether that is wanted.

    Swallows every exception (a soft-deleted row, a store without either
    method) into `None`, matching the fail-closed discipline every caller
    in this module keeps.
    """
    try:
        if store.list_character_skills(character_id):
            return None
        return store.read_typed_attributes(character_id).get("class_id")
    except Exception:
        return None


def grant_starting_skills_for_class(store, character, class_id: int) -> "tuple[int, ...] | None":
    """Give the character her class's starting-kit skills, once class_id
    is known.

    CORE-REQUEST of `pf_bridge/notes_to_chief/20260904_0542_LANE-DB-
    CORE-REQUEST-starting-skill-door-built-needs-one-hookup.md`, called at
    the same site as `persist_class_id_from_starting_gear` because both
    need the same resolved `class_id` -- this function does not resolve a
    class id itself, only what to do once one exists.

    `class_id` is whatever the call site decided is the right one to grant
    a kit for THIS call -- see `CharacterLifecycle.create` and
    `_class_id_for_a_retried_skill_grant`'s own docstring for how a retry
    picks it apart from a merely-already-set column that should stay
    untouched.

    Never raises, for the same reason `persist_class_id_from_starting_gear`
    never does: the character row already exists.
    """
    character_id = getattr(character, "id", None)
    from . import persistence_starting_skills

    try:
        skill_ids = persistence_starting_skills.resolve_starting_skill_ids(class_id)
    except Exception as error:
        _say(
            f"CHARACTER_STARTING_SKILLS cid={character_id} not_written "
            f"reason=resolve_failed ({type(error).__name__})"
        )
        return None
    if skill_ids is None:
        _say(
            f"CHARACTER_STARTING_SKILLS cid={character_id} not_written "
            f"reason=no_kit_for_class_id class_id={class_id}"
        )
        return None
    try:
        granted = store.grant_starting_skills(character_id, skill_ids)
    except Exception as error:
        _say(
            f"CHARACTER_STARTING_SKILLS cid={character_id} not_written "
            f"reason=grant_refused ({type(error).__name__})"
        )
        return None
    _say(f"CHARACTER_STARTING_SKILLS cid={character_id} written skill_ids={granted}")
    return granted


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

        character = self.store.create_character(
            account_id, normalized, name_key, fingerprint, build,
            self.default_position,
        )
        # The class she picked is resolved and stored HERE, after the row
        # exists, and not inside `store.create_character`: that method is
        # LANE-DB's and runs one `BEGIN IMMEDIATE` transaction from its first
        # statement to its last, so a second writer inside it would be a
        # nested write on a locked row.  By the time this line runs, on EVERY
        # return path of that method (the fresh INSERT and the
        # create-fingerprint retry alike), the transaction is closed and the
        # row is readable.  The retry path re-resolving the same body is not
        # what makes this safe on its own (pf-adversary D2 on `#705`: an
        # unconditional write here would revert a class id another writer
        # set on this row between the first attempt and the retry) --
        # `write_typed_attribute_if_unset` is what makes it safe, by only
        # ever writing a NULL column.
        resolved_class_id = persist_class_id_from_starting_gear(self.store, character)
        # Same call site, same reason: piece 5's starting-skill kit
        # (`pf_bridge/notes_to_chief/20260904_0542_LANE-DB-CORE-REQUEST-
        # starting-skill-door-built-needs-one-hookup.md`). A resend whose
        # class_id was already set falls back to
        # `_class_id_for_a_retried_skill_grant`, which re-reads the row --
        # but only retries the grant when nothing was granted yet, so a
        # transient `store.grant_starting_skills` failure on the winning
        # attempt gets another chance instead of stranding the character
        # with a class and no skills forever (`pf-adversary`, this round).
        class_id_for_skills = resolved_class_id
        if class_id_for_skills is None:
            class_id_for_skills = _class_id_for_a_retried_skill_grant(
                self.store, character.id,
            )
        if class_id_for_skills is not None:
            grant_starting_skills_for_class(self.store, character, class_id_for_skills)
        return character

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
