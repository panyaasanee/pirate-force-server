"""SKILL-LIST-AT-LOGIN-001 -- the character's OWN persisted skill rows,
composed into the one frame a client has been observed to render.

Why this module exists (COO-ORDER `20260907_2050`, LANE-CS)
-----------------------------------------------------------
The owner sat in front of the game on 2026-09-07 and watched a production
boot print

    CHARACTER_STARTING_SKILLS cid=1 written skill_ids=(111, 40000, 99, 110)

while BOTH skill tabs on screen stayed empty, "show all" included.  The rows
are in the database.  Nothing reads them back out onto the wire.  Every skill
a client has ever displayed in this project's history came out of
the HYP-PF-033 sweep lane's pinned steps, under an opt-in flag, with
values that lane calls opaque on purpose -- so on a normal login the window is
empty and there is no code path that could fill it.  This module is the read
half: character row in, ``(pc, frame)`` out, no flag, no fixed table.

WHERE THE IDS COME FROM, AND WHY THAT MATTERS LESS THAN IT SOUNDS
-----------------------------------------------------------------
``store.list_character_skills`` -- the ``character_skills`` rows -- and NOT
``class_catalog.starting_skill_ids``.  That distinction is the point of the
order, and this module honours it in the only way that is honest about today:

  * it is a REAL difference in what the code depends on.  The class table
    answers "what does a class start with"; the rows answer "what does THIS
    character have".  Only the second can ever grow -- a learned skill, a GM
    grant, a class change -- and only the second is per-character.
  * it is NOT yet a difference a player could see.  For every character
    alive today the rows were written from the class table by
    ``lifecycle.py``'s ``CHARACTER_STARTING_SKILLS`` call, so the two answers
    are identical, character for character.  ``migrations/014`` widened
    ``source`` to admit a ``learned`` grant, but nothing writes one yet.
    Anybody reading this module as "now the skills are real" is reading it
    wrong: what is real is the ROUTE.  The day a second writer exists, this
    route already carries it and the class-table route never could.

WHY IT IS WIRED NOW, AND WHAT PAID FOR THE FLAG (2026-09-08, round `ixbs2f`)
----------------------------------------------
It stayed unwired for three rounds, and the reason was specific rather than
cautious.  The HYP-PF-033 sweep lane's own docstring records, from GT-249 run
on a real client on 2026-09-05: after its six-frame sweep landed, the client
stopped emitting any outbound movement frame for the rest of the session --
the player could open windows and drag items but COULD NOT WALK until a fresh
login.  Which frame caused it was not isolated, so this module composing ONE
frame of that same vital was a candidate way to ship a game nobody can walk
in, and ``production_allowed`` stayed ``False`` with the condition to flip it
written down instead of left to a future round's judgement.

**GT-276 answered it.**  PASS, R323C, attended, ``OBSERVER_CONFIRMED``
2026-09-07T21:33+07:00: the walk-lock is ONE BYTE.  Steps carrying trailing
u8 == 1 lock walking; steps carrying trailing u8 == 0 walk.  The record count
made no difference across those three.  The tester's own proposed reading of
why R312 locked is that the six-frame sweep it rode in contained trailing-1
steps; that is in the letter's `proposed status` section and not in its
`RESULT:` line, so it is recorded here as the tester's reading and not as a
measured fact (pf-adversary D5 caught the earlier wording, which stated it
flat and went further than five dummy-record frames can carry).

So the flag is flipped, and these are the things that carry it:

  * The refusal is on the BYTES, not on a constant.  ``make_skill_list_response``
    decodes back the payload it just composed and raises
    ``REFUSE_TRAILING_BYTE_LOCKS_WALKING`` unless what it measures is 0, so a
    frame that leaves this module CARRIES A TRAILING BYTE MATCHING the ones
    R323C measured as walkable.  Say it that way and not "a frame R323C
    measured as walkable" (which this section did say, until pf-adversary D5):
    R323C booted five frames of DUMMY records at counts 0, 1 and 3.  It never
    booted this frame.  The claim is about one byte.
  * The owner ordered the seam by hand (PANYA `20260908_1455` item 2.3, "this
    is the piece that is really missing"), and COO-DECISION `20260908_1541`
    moved the seam into this lane's write zone and named the byte: trailing 0,
    not optional.
  * ``runtime.py``'s login path now CALLS ``login_skill_list_response``, so
    ``seam_carrier()`` reports ``runtime`` off a call node in that file and
    the console token's ``callers_in_src`` is counted off the tree.

WHAT IS STILL NOT MEASURED, written here rather than left for somebody to
find: R323C did not re-boot count 4 at trailing 0.  Count 4 at trailing 0 is
GT-249's own step 6 -- the step that rendered 3 of 4 ids -- and every
character alive today has exactly 4 rows, so the first production login under
this seam is the one count R323C skipped.  ``GT-307`` is the attended ticket
for precisely that, this seam is its build precondition, and nothing in this
section says the attended run became unnecessary.

NONCLAIMS -- inherited and new
-------------------------------
  * Every nonclaim in the HYP-PF-033 sweep lane still stands and is
    not repeated here.  In particular the three record members' SEMANTICS are
    unknown; this module puts the skill id in all three wire positions for the
    same reason GT-249's step 6 did -- the position that means "skill id", if
    any, is unproven -- and the composer it uses is the SAME frame module the
    sweep lane composes with, so the two cannot drift apart.
  * GT-249 measured that 3 of 4 sent ids appeared and id ``40000`` did not,
    and that the class-named tab stayed empty throughout.  Reading the ids
    from the database instead of the class table changes NONE of that: the
    ids are the same four ids.  This module does not claim it fixes ``40000``
    and does not claim to know why it did not render.
  * Nothing here persists anything, learns anything, or spends a skill point.
    It is a read and a compose.
  * No claim is made that a login is the right MOMENT to send this frame.
    GT-249's positive result came from a trigger, not from login, and whether
    the client's window is even constructed yet at ``StartGame`` time is
    exactly what the attended ticket asks.
"""
from __future__ import annotations

from typing import Any

from .learn_skill_result_frame import (
    LEARN_SKILL_RESULT_COUNT_TAG,
    LEARN_SKILL_RESULT_PAYLOAD_BASE_SIZE,
    LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET,
    LEARN_SKILL_RESULT_RECORD_WIRE_SIZE,
    LearnSkillResultRecord,
    decode_learn_skill_result_payload,
    make_learn_skill_result_response,
)


SKILL_LIST_AT_LOGIN_CHECKPOINT = "SKILL-LIST-AT-LOGIN-001"

#: True since 2026-09-08 (round `ixbs2f`).  Flipped on GT-276's PASS (R323C),
#: which measured the walk-lock as the trailing u8 rather than this vital, and
#: on the owner's order in `20260908_1455` item 2.3 carried by COO-DECISION
#: `20260908_1541`.  The module docstring's "WHY IT IS WIRED NOW" holds what
#: this rests on -- and the one thing R323C did not boot, which is `GT-307`.
production_allowed = True

#: The trailing u8 GT-249's positive step carried.  Imported as a value, not
#: as a decision: this lane has no idea what the byte means (that module's
#: nonclaims say so) and picks the one that was on the wire the one time a
#: client rendered anything, rather than inventing a second unknown.
SKILL_LIST_TRAILING_BYTE = 0

#: The record count field is a u16 on the proven wire.  A fact about the
#: serializer, not a policy.
WIRE_MAX_RECORDS = 0xFFFF

#: The largest record count any real client has been OBSERVED to accept:
#: GT-249's ``COUNT4_REAL_SKILL_IDS_CLASS1_TRAIL0``, four records.  Above this
#: nothing has ever been measured, so the login path refuses by name instead
#: of guessing that a bigger frame is fine.  Raising this is an attended
#: result's job, not a future round's convenience -- a character who has
#: learned a fifth skill must produce a NAMED refusal in the log, which is a
#: bug report, and never a silently truncated skill window.
OBSERVED_ACCEPTED_RECORD_COUNT = 4

#: Refusal reasons.  Every one names the row or the wire, never the caller.
REFUSE_CHARACTER_ID_NOT_AN_INT = "character_id_is_not_an_int"
REFUSE_CHARACTER_ROW_MISSING = "character_row_does_not_exist"
REFUSE_NO_SKILL_ROWS = "character_has_no_skill_rows"
REFUSE_SKILL_ID_NOT_AN_INT = "skill_id_is_not_an_int"
REFUSE_SKILL_ID_OUTSIDE_U32 = "skill_id_is_outside_the_u32_wire_field"
REFUSE_DUPLICATE_SKILL_ID = "skill_ids_are_not_distinct"
REFUSE_TOO_MANY_FOR_THE_WIRE = "record_count_is_outside_the_u16_wire_field"
REFUSE_TOO_MANY_UNMEASURED = "record_count_is_above_any_observed_acceptance"
#: pf-adversary D5 (round `jqeid1`): `path.is_file()` waves a zero-byte file
#: through, and `sqlite3.connect` then CREATES a database in it -- while the
#: refusal string beside it says this command never creates one.  A separate
#: reason, so an operator whose --db is a stub reads which of the two it was.
REFUSE_NOT_A_DATABASE = "path_is_not_an_sqlite_database"
#: WHAT R323C MEASURED, kept apart from what follows from it (pf-adversary
#: D4 caught the first draft of this comment stating the second as the
#: first).  MEASURED, on a real client, 2026-09-07
#: (`KA1A-R323C-RESULTS-GT276-PASS-trailing-u8-1-locks-walking-not-record-
#: count`): two frames of this vital differing in one byte, trailing u8 = 1
#: stops the client emitting movement frames and trailing u8 = 0 does not;
#: record count and contents make no difference.  That letter's OWN
#: nonclaims say it did not measure whether the lock ever releases (the
#: owner closed the game), and did not boot its step 6 -- real ids with
#: trailing 0 -- which is the frame this module composes.
#: NOT MEASURED, inferred here and labelled as inference: GT-249 recorded
#: that its own lock lasted until a fresh login, so a frame sent AT login
#: would be re-sent by the one escape anybody has written down.  Nobody has
#: run that, and this module is not the place to find out.
REFUSE_TRAILING_BYTE_LOCKS_WALKING = "composed_frame_does_not_end_in_the_walkable_zero"
#: pf-adversary D5: the first draft of the guard below reported an
#: undecodable payload under the reason above, so an operator grepping
#: "walk lock" would read "the locking byte is set" when the byte was 0 and
#: only the slice arithmetic had drifted.  This module already refused that
#: pattern once by name (see REFUSE_NOT_A_DATABASE): two facts, two reasons.
REFUSE_PAYLOAD_UNREADABLE = "composed_payload_could_not_be_decoded_back"
#: pf-adversary D2/M5: `make_learn_skill_result_response` self-checks that it
#: is decoder-inverse and raises a BARE RuntimeError when it is not.  That
#: escaped this module's "one exception class" promise and would have unwound
#: the listener thread at v141:7440, which has no except.  Translated here.
REFUSE_ENCODER_NOT_INVERSE = "the_proven_encoder_did_not_round_trip"


class SkillListAtLoginError(RuntimeError):
    """This character's skill list cannot be put on the wire, by name.

    Carries the machine-readable ``reason`` (one of the ``REFUSE_*``
    constants) beside the human sentence -- the shape this lane's other
    fail-closed modules already use -- so a caller branches on a constant and
    never on a message.

    (The sibling module is not named here on purpose: its own
    ``callers_in_src`` token is measured by a test that greps this package for
    its name, so a mention in a docstring would read as a caller and make that
    token false.  Same reason the progression-table module is not named in it.)
    """

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


def read_character_skill_ids(store: Any, character_id: int) -> tuple[int, ...]:
    """The skill ids persisted for ``character_id``, oldest grant first.

    A thin, named-refusal wrapper over ``SQLiteStore.list_character_skills``
    and deliberately nothing more: this lane does not own ``store.py`` and
    does not open a second query against LANE-DB's table.

    The store's own ``TypeError`` (a bool or non-int id) and ``KeyError`` (no
    such character, or soft-deleted) become this module's named refusals, so
    a login-path caller has ONE exception class to catch and a reason string
    to print.  An empty result is refused too, and that is a decision worth
    stating: ``encode_learn_skill_result_payload`` would happily compose a
    count-0 frame, and a count-0 frame is a claim ("this character knows
    nothing") that this project cannot currently tell apart from "the grant
    at creation was refused" -- ``lifecycle.py`` prints ``not_written`` on
    several paths and characters created before ``migrations/011`` have no
    rows at all.  Sending nothing and logging a reason is recoverable;
    telling the client the window is empty on purpose is not.
    """
    if isinstance(character_id, bool) or not isinstance(character_id, int):
        raise SkillListAtLoginError(
            REFUSE_CHARACTER_ID_NOT_AN_INT,
            "character id %r is not a plain int" % (character_id,),
        )
    try:
        skill_ids = store.list_character_skills(character_id)
    except KeyError as error:
        raise SkillListAtLoginError(
            REFUSE_CHARACTER_ROW_MISSING,
            "character %d has no live row to read skills from" % character_id,
        ) from error
    except TypeError as error:  # pragma: no cover - guarded above, kept honest
        raise SkillListAtLoginError(
            REFUSE_CHARACTER_ID_NOT_AN_INT,
            "the store refused character id %r" % (character_id,),
        ) from error
    if not skill_ids:
        raise SkillListAtLoginError(
            REFUSE_NO_SKILL_ROWS,
            "character %d has no rows in character_skills; sending a "
            "count-0 frame would assert an empty skill list this project "
            "cannot currently distinguish from a grant that never ran"
            % character_id,
        )
    return tuple(skill_ids)


def skill_list_records(
    skill_ids: "tuple[int, ...] | list[int]",
) -> tuple[LearnSkillResultRecord, ...]:
    """One record per skill id, the id in all three wire positions.

    The three-position repeat is GT-249's step-6 convention and the reason is
    that lane's, not this one's: the member that means "skill id", if any, is
    unproven, so an attended tester should not have to guess which field the
    client read before judging what is on screen.

    Refuses, by name and with no records: a non-int/bool id, an id outside the
    u32 field, a repeated id (``character_skills`` carries
    ``UNIQUE(character_id, skill_id)``, so a duplicate reaching here means the
    caller assembled the list itself and this module is being used as a
    general composer it is not), a count above the u16 wire field, and a count
    above anything a client has been observed to accept.
    """
    if isinstance(skill_ids, (str, bytes)) or not isinstance(
        skill_ids, (list, tuple)
    ):
        raise SkillListAtLoginError(
            REFUSE_SKILL_ID_NOT_AN_INT,
            "skill ids must arrive as a list or tuple, got %r"
            % (type(skill_ids).__name__,),
        )
    checked: list[int] = []
    for skill_id in skill_ids:
        if isinstance(skill_id, bool) or not isinstance(skill_id, int):
            raise SkillListAtLoginError(
                REFUSE_SKILL_ID_NOT_AN_INT,
                "skill id %r is not a plain int" % (skill_id,),
            )
        if not 0 <= skill_id <= 0xFFFFFFFF:
            raise SkillListAtLoginError(
                REFUSE_SKILL_ID_OUTSIDE_U32,
                "skill id %d does not fit the u32 wire field" % skill_id,
            )
        if skill_id in checked:
            raise SkillListAtLoginError(
                REFUSE_DUPLICATE_SKILL_ID,
                "skill id %d appears more than once" % skill_id,
            )
        checked.append(skill_id)
    if len(checked) > WIRE_MAX_RECORDS:
        raise SkillListAtLoginError(
            REFUSE_TOO_MANY_FOR_THE_WIRE,
            "%d records do not fit the u16 count field (max %d)"
            % (len(checked), WIRE_MAX_RECORDS),
        )
    if len(checked) > OBSERVED_ACCEPTED_RECORD_COUNT:
        raise SkillListAtLoginError(
            REFUSE_TOO_MANY_UNMEASURED,
            "%d records is above the largest count any client has been "
            "observed to accept (%d, GT-249); raising this needs an attended "
            "result, not a bigger constant"
            % (len(checked), OBSERVED_ACCEPTED_RECORD_COUNT),
        )
    return tuple(
        LearnSkillResultRecord(
            record_u32_0=skill_id,
            record_u16_4=skill_id,
            record_u32_8=skill_id,
        )
        for skill_id in checked
    )


def measured_trailing_byte(pc: bytes, record_count: int) -> int:
    """The trailing u8 CARRIED BY ``pc``, decoded, never the constant.

    pf-adversary (round `3f12wv`, D3) named the reason this is a function
    and not an expression inside one caller: ``headless_token`` printed
    ``trailing_u8=`` straight out of ``SKILL_LIST_TRAILING_BYTE``, so the
    line an operator pastes as ``HEADLESS_PROOF:`` said ``trailing_u8=0``
    about a frame whose trailing byte was ``0x01`` -- the walk-locking one.
    A token that reports a constant instead of the bytes is the exact defect
    ``seam_carrier`` was written to kill one field to its left.  Both the
    refusal in ``make_skill_list_response`` and the token now come through
    here, so they cannot disagree about the same frame.

    ``record_count`` is needed because the decoder refuses a payload with a
    byte left over after the trailing u8, so it has to be handed exactly the
    slice; the three geometry names come from ``learn_skill_result_frame``,
    the plain frame module COO-DECISION `20260907_2241` created so that this
    lane never imports the HYP-PF-033 sweep lane's own module.  That lane's
    containment test pins its importer list exactly, and it pins it by
    SUBSTRING over every file in this package -- the first draft of this
    guard imported from there and turned it red, the second turned it red
    again just by naming that module in this sentence, and the third by
    naming the test class.  Neither name is written here; this note is what
    replaces them, and the shape is worth remembering: in this package,
    prose about a gated name is treated as a use of it.

    Raises ``SkillListAtLoginError`` and never a bare decoder exception --
    the same one-exception-class promise the rest of this module makes.
    """
    payload_start = LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET
    payload_size = (
        LEARN_SKILL_RESULT_PAYLOAD_BASE_SIZE
        + LEARN_SKILL_RESULT_RECORD_WIRE_SIZE * record_count
    )
    try:
        _records, trailing = decode_learn_skill_result_payload(
            pc[payload_start:payload_start + payload_size]
        )
    except Exception as error:      # noqa: BLE001 - a payload this module
        # just composed and cannot read back is not a frame to send, and it
        # is not a walk-lock either: separate reason, see its constant.
        raise SkillListAtLoginError(
            REFUSE_PAYLOAD_UNREADABLE,
            "the composed payload could not be decoded back, so the "
            "trailing byte could not be checked at all: %s" % (error,),
        ) from error
    return trailing


def measured_record_count(pc: bytes) -> int:
    """The record count CARRIED BY ``pc``, decoded, never ``len(skill_ids)``.

    pf-adversary (round `jty60h`, D3) named the defect this closes: every
    number in the token except the trailing byte was measured off something
    the caller had in hand BEFORE the frame existed, so a mutant that stops
    composing -- or stops appending the composed action to the login list --
    leaves ``rows=4`` printing about a wire that carries nothing.  The count
    is read out of the payload's own u16 field and then handed back through
    the same decoder that ``measured_trailing_byte`` uses, so a byte string
    that merely starts with the right tag cannot answer.

    Raises ``SkillListAtLoginError`` and never a bare decoder exception, the
    same one-exception-class promise the rest of this module makes.
    """
    start = LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET
    header = bytes(pc[start:start + 3])
    if len(header) != 3 or header[0] != LEARN_SKILL_RESULT_COUNT_TAG:
        raise SkillListAtLoginError(
            REFUSE_PAYLOAD_UNREADABLE,
            "the composed pc carries no readable record-count field at "
            "offset %d, so the row count could not be measured at all"
            % (start,),
        )
    declared = int.from_bytes(header[1:3], "little")
    payload_size = (
        LEARN_SKILL_RESULT_PAYLOAD_BASE_SIZE
        + LEARN_SKILL_RESULT_RECORD_WIRE_SIZE * declared
    )
    try:
        records, _trailing = decode_learn_skill_result_payload(
            pc[start:start + payload_size]
        )
    except Exception as error:      # noqa: BLE001 - same reasoning as
        # `measured_trailing_byte`: a payload this module just composed and
        # cannot read back is not a frame to report a row count about.
        raise SkillListAtLoginError(
            REFUSE_PAYLOAD_UNREADABLE,
            "the composed payload could not be decoded back, so the record "
            "count could not be measured at all: %s" % (error,),
        ) from error
    return len(records)


def make_skill_list_response(
    legacy: Any, skill_ids: "tuple[int, ...] | list[int]",
) -> tuple[bytes, bytes]:
    """``(pc, frame)`` carrying this character's skill ids, or a named refusal.

    The bytes are composed by ``make_learn_skill_result_response`` and not by
    anything here: that function re-decodes its own payload, re-checks the
    composed PC size, the vital id and the embedded body before returning, and
    this module adds no fifth copy of a wire layout it does not own.

    ``record_u16_4`` is a u16 field, so a skill id above 65535 fits the two
    u32 positions but not the middle one -- that refusal comes back from the
    encoder as ``ValueError`` rather than from the loop above, and is
    translated here so a caller still sees one exception class.
    """
    records = skill_list_records(skill_ids)
    try:
        pc, frame = make_learn_skill_result_response(
            legacy, records, SKILL_LIST_TRAILING_BYTE,
        )
    except ValueError as error:
        raise SkillListAtLoginError(
            REFUSE_SKILL_ID_OUTSIDE_U32,
            "the proven encoder refused these skill ids: %s" % (error,),
        ) from error
    except RuntimeError as error:
        # pf-adversary D2/M5: the composer's own inverse check raises a bare
        # RuntimeError, which this module's docstring promises callers will
        # never see -- and a seam written to that promise ("one except with
        # one named reason") would have let it through into a listener
        # thread with no except of its own.
        raise SkillListAtLoginError(
            REFUSE_ENCODER_NOT_INVERSE,
            "the proven encoder did not round-trip its own payload: %s"
            % (error,),
        ) from error
    # MEASURED BY DECODING THE COMPOSED PAYLOAD, not by reading
    # SKILL_LIST_TRAILING_BYTE back, and that difference is the whole point.
    # Every pin this module had on the walk-lock byte compared the constant
    # with a value decoded out of a frame composed FROM that same constant:
    # both sides move together, so editing the constant to 1 left all of them
    # green while this route composed the frame R323C measured as locking the
    # player's movement for the rest of the session.  Sent at LOGIN that lock
    # would plausibly be re-sent by the one escape GT-249 wrote down (a fresh
    # login), which nobody has run -- see SKILL_LIST_TRAILING_BYTE's comment
    # for which half of that is measured.  Either way the check belongs in
    # the route, where a caller cannot get past it by editing one integer,
    # and not only in a test.
    #
    # It decodes rather than indexing a byte position: the trailing u8 is NOT
    # the last byte of the frame (the composed frame ends in an outer
    # `0B 00` after it), and a hard-coded negative index would be a fifth
    # copy of a wire layout this module does not own.  The three names below
    # are the OWNER module's published sizes, imported as values the same way
    # SKILL_LIST_TRAILING_BYTE is -- the decoder refuses a payload with a byte
    # left over after the trailing u8, so it has to be handed exactly the
    # slice, and these are the only numbers that say where it ends.
    trailing = measured_trailing_byte(pc, len(records))
    if trailing != 0:
        raise SkillListAtLoginError(
            REFUSE_TRAILING_BYTE_LOCKS_WALKING,
            "the composed payload carries trailing 0x%02X, and R323C "
            "measured that a non-zero trailing byte stops the client "
            "emitting movement frames" % (trailing,),
        )
    return pc, frame


def login_skill_list_response(
    legacy: Any, store: Any, character_id: int,
) -> tuple[bytes, bytes]:
    """The whole route: character row -> persisted skill ids -> ``(pc, frame)``.

    This is the single entry point a login-path caller needs, and the only one
    the CORE-REQUEST filed with this round asks anybody to call.  It raises
    ``SkillListAtLoginError`` -- never a bare ``KeyError``, ``TypeError`` or
    ``ValueError`` -- so the seam in ``runtime.py`` is one ``except`` with one
    named reason to append to ``self.events``, and a character whose row
    cannot answer gets a login with no skill frame rather than a login that
    dies inside a listener thread with no ``except`` around it.
    """
    return make_skill_list_response(
        legacy, read_character_skill_ids(store, character_id)
    )


def callers_in_src() -> int:
    """How many sibling modules under ``src/`` name this one, COUNTED.

    It used to be the literal ``0`` inside the summary format string, with a
    test doing the counting; that was honest for exactly as long as the answer
    stayed 0, and round `ixbs2f` wired the seam, so the constant would now
    print ``callers_in_src=0`` on a server that sends this frame on every
    login.  A number about the tree, printed by a format string that cannot
    see the tree, is the same species of defect ``seam_carrier`` exists to
    kill one field to its right; the fix is the same one -- go and look.

    NOT AT IMPORT TIME, which is the objection the old docstring raised and
    which still stands.  It runs only when somebody asks for the console
    summary, by the same rule ``seam_carrier()`` follows: a package walk on a
    boot path would be the thing with no business here.  (An earlier draft of
    this paragraph said "the console entry point calls it".  It does not --
    ``main()`` calls ``seam_carrier()`` and ``headless_token()``, and
    ``describe_skill_list`` has no caller outside ``tests/``.  pf-adversary
    D6: a sentence about a call site that does not exist, doing the work of
    answering "is this on a boot path?".)

    SUBSTRING, NOT AST, on purpose and unlike ``seam_carrier``.  The question
    here is "does any sibling module mention this module at all", which is the
    widest form of the question and the one that cannot miss an alias, a
    ``getattr`` or an import this module did not predict.  It counts prose
    too, and that is a deliberate over-count: a mention that turns out to be a
    comment costs somebody a look at a diff, while a call this scan cannot see
    costs a token that says nothing sends the frame while something does.
    Returns 0 rather than raising when the package cannot be walked.  THE
    CAVEAT, WRITTEN HERE RATHER THAN POINTED AT: a 0 because the directory
    could not be read and a 0 because nothing names this module print the
    same digit.  An earlier draft said the caveat was "named in ``main``'s
    docstring"; it was not written anywhere (pf-adversary D6).  The
    ``sent_by`` field beside it in the summary is the one that cannot be
    faked, so read that one first.
    """
    from pathlib import Path

    here = Path(__file__).resolve()
    try:
        siblings = sorted(here.parent.rglob("*.py"))
    except OSError:
        return 0
    total = 0
    for path in siblings:
        if path.resolve() == here:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if here.stem in text:
            total += 1
    return total


def describe_skill_list(skill_ids: "tuple[int, ...] | list[int]") -> tuple[str, ...]:
    """ASCII console lines for a headless boot to print.

    One line per record plus a summary, in the shape the bridge console can
    carry (cp874: ASCII only).  The summary's ``callers_in_src`` comes from
    ``callers_in_src()`` -- see that function for why it stopped being a
    literal the day the seam landed.
    """
    records = skill_list_records(skill_ids)
    lines = [
        "SKILL_LIST_AT_LOGIN record=%d skill_id=%d u32_0=%d u16_4=%d u32_8=%d"
        % (index, record.record_u32_0, record.record_u32_0,
           record.record_u16_4, record.record_u32_8)
        for index, record in enumerate(records)
    ]
    # `sent_by` and a COMPUTED result, not `RESULT=ARMED` as a literal:
    # pf-adversary D7 deleted the seam's try/except out of `runtime.py`,
    # left the import and the comments, and this line still read
    # `callers_in_src=1 ... RESULT=ARMED` on a server that sends nothing --
    # because a mention in a comment is a "caller" to a substring scan, and
    # `ARMED` was typed into the format string.  `sent_by` comes from the AST
    # walk that only a real call node satisfies, and `RESULT` is derived from
    # it, so the two halves of this line cannot disagree.
    carrier = seam_carrier()
    lines.append(
        "SKILL_LIST_AT_LOGIN_SUMMARY records=%d trailing=%d "
        "observed_cap=%d callers_in_src=%d sent_by=%s production_allowed=%s "
        "RESULT=%s"
        % (
            len(records),
            SKILL_LIST_TRAILING_BYTE,
            OBSERVED_ACCEPTED_RECORD_COUNT,
            callers_in_src(),
            carrier,
            production_allowed,
            "ARMED" if (carrier != "module_only" and production_allowed)
            else "NOT_ARMED",
        )
    )
    return tuple(lines)


#: The name a login-path caller has to spell in ``runtime.py`` for this
#: module to reach a player.  ``seam_carrier()`` looks for exactly this and
#: reports what it finds, so the console token below turns on the day the
#: seam lands and not one round earlier.
LOGIN_SEAM_SYMBOL = "login_skill_list_response"

#: The database ``app.py`` boots on when nobody passes ``--db``.  Spelled
#: once here so the headless token GT-307 asks for reads what a normal boot
#: reads, rather than a copy somebody remembered to point at.
DEFAULT_DB_RELATIVE_PATH = "state/pirateforce.sqlite3"


def repository_root() -> "Any":
    """The checkout this module is running out of."""
    from pathlib import Path

    return Path(__file__).resolve().parents[2]


def _seam_call_scopes(tree: "Any") -> "Any":
    """Every call to ``LOGIN_SEAM_SYMBOL``, with the def chain around it.

    Returns one tuple per call node: the enclosing ``FunctionDef`` chain,
    OUTERMOST FIRST, empty when the call sits at module level (which runs at
    import).  ``ClassDef`` is deliberately not part of the chain -- a method
    is reached through an instance, and the name a caller spells is the
    method's, which is what the reachability rule below looks for.
    """
    import ast

    sites = []

    def walk(node: "Any", stack: "Any") -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Call):
                func = child.func
                name = getattr(func, "attr", getattr(func, "id", ""))
                if name == LOGIN_SEAM_SYMBOL:
                    sites.append(tuple(stack))
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(child, stack + [child])
            else:
                walk(child, stack)

    walk(tree, [])
    return tuple(sites)


def _named_outside_its_own_body(tree: "Any", func_node: "Any") -> bool:
    """True when this module spells ``func_node``'s name somewhere else.

    "Somewhere else" excludes the def's ENTIRE own subtree, so a function
    that only calls itself does not vouch for itself.  Both spellings count:
    a bare ``Name`` (``helper()``) and an ``Attribute`` (``self.helper()``),
    because the seam's carrier in ``runtime.py`` is reached the second way.
    """
    import ast

    own = {id(node) for node in ast.walk(func_node)}
    target = func_node.name
    for node in ast.walk(tree):
        if id(node) in own:
            continue
        if isinstance(node, ast.Name) and node.id == target:
            return True
        if isinstance(node, ast.Attribute) and node.attr == target:
            return True
    return False


def _calls_the_seam(tree: "Any") -> bool:
    """True when this module calls ``LOGIN_SEAM_SYMBOL`` FROM REACHABLE CODE.

    Split out of ``seam_carrier`` when the search widened from one file to
    the auto-imported hook package: two copies of an AST walk is how the two
    halves of one answer drift apart.

    REACHABILITY IS THE POINT, AND IT IS WHY THIS IS NOT A PLAIN WALK
    (pf-adversary D7, round ``ixbs2f``, paid here).  The first version asked
    only "is there a call node anywhere in this file".  A mutant that deletes
    the ONE line on the login path -- ``skill_list_action =
    self._skill_list_login_action(legacy)`` -- while leaving the method it
    called in place still answered ``runtime``: the call node inside the now
    dead method is still a call node.  A server that sends nothing at login
    would print ``sent_by=runtime ... RESULT=ARMED`` in the very token an
    operator pastes as ``HEADLESS_PROOF:`` for GT-307.  The suite caught that
    mutant on eight tests, but the token line -- the one artifact that
    travels alone, into a ticket, away from the suite -- did not.

    THE RULE, stated so a reader can check it against the code.  A call
    counts when every enclosing def, except the OUTERMOST one, has its name
    spelled somewhere else in the same module.  The exception for the
    outermost def is not a loophole being papered over: a module-level def is
    exactly what another file imports and calls (``runtime.py``'s own
    ``make_state_class`` is called from ``app.py`` and appears nowhere in
    ``runtime.py`` outside its own body), so demanding an in-file caller for
    it would answer ``module_only`` on the tree that ships today.

    WHAT THIS STILL CANNOT SEE, said rather than implied.  A name spelled in
    dead code of another function vouches for the carrier just as well as a
    live call does -- this is an in-file NAME check, not an execution proof,
    and no static check in this file claims to be one.  Nothing here reads
    ``app.py`` to confirm the outermost def is really imported.  What it does
    buy is the property the token needs: deleting the login-path call, and
    nothing else, flips the token to ``module_only``.
    """
    for chain in _seam_call_scopes(tree):
        if not chain:
            # Module level: it runs at import, so there is nobody to name it.
            return True
        # chain[0] is the outermost def -- see the docstring for why it is
        # exempt.  Everything nested inside it has to be named to count.
        if all(
            _named_outside_its_own_body(tree, node) for node in chain[1:]
        ):
            return True
    return False


def seam_carrier(runtime_path: "Any" = None, hooks_dir: "Any" = None) -> str:
    """Who would send this frame today, MEASURED off ``runtime.py``.

    ``runtime`` when the login path actually CALLS
    ``login_skill_list_response``, ``module_only`` when it does not,
    ``unknown`` when there is no runtime to read or it does not parse.
    GT-307's token line ends in ``sent_by=``, and a hard-coded
    ``sent_by=runtime`` would be the same species of lie as the
    ``callers_in_src=0`` that pf-adversary killed in round ``e8pss9``: a
    claim about the tree, printed by a format string that cannot see it.

    THIS IS AN AST CHECK BECAUSE A SUBSTRING CHECK WAS ALREADY WRONG.  The
    first version of this function asked ``LOGIN_SEAM_SYMBOL in text``, and
    pf-adversary (round ``jqeid1``, D4) turned it on with a single line:

        # TODO(next round): call login_skill_list_response from the login path

    One comment and the token an operator pastes as ``HEADLESS_PROOF:``
    reads ``sent_by=runtime`` on a server that sends nothing.  A call node is
    the smallest thing that cannot be written by accident or by a plan.

    IT NO LONGER READS ONE FILE (pf-adversary D2, paid).  ``runtime.py`` does
    ``from . import lane_hooks``, and that package's ``_discover()`` imports
    EVERY ``lane_*.py`` module beside it at process start, so a lane can put
    this frame on a live boot path without ``runtime.py`` changing by a byte.
    The old answer for that tree was ``module_only``: the token would have
    told an operator nothing sends this frame while a hook was sending it.
    Every auto-imported hook module is now read too, in the same
    filename-sort order the package documents, and a call in one of them
    answers ``hook:<module>``.

    ``runtime`` beats a hook when both call it, because a direct call on the
    login path is the seam GT-307 is about and a hook is the way around it.

    WHAT IT STILL CANNOT SEE, said rather than implied.  ``hook:<module>`` is
    an UPPER bound on "this frame is live", not a proof of it: ``_discover()``
    additionally refuses a hook module whose own ``production_allowed`` is
    false (``LANE_HOOK_DISCOVERY ... SKIPPED_NOT_PRODUCTION_ALLOWED``), and
    that flag is not read here.  And neither half sees a call made through a
    variable, a ``getattr`` or an alias -- an AST call node is still the
    smallest thing that cannot be written by accident, which is the property
    this function trades reach for.
    """
    import ast
    from pathlib import Path

    path = (
        Path(runtime_path)
        if runtime_path is not None
        else Path(__file__).resolve().parent / "runtime.py"
    )
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return "unknown"
    if _calls_the_seam(tree):
        return "runtime"

    folder = (
        Path(hooks_dir)
        if hooks_dir is not None
        else path.resolve().parent / "lane_hooks"
    )
    try:
        # sorted(): lane_hooks/__init__.py documents filename-sort order as
        # the ONLY ordering guarantee `_discover()` gives, and this answer
        # names one module, so it has to break ties the same way.
        candidates = sorted(folder.glob("lane_*.py"))
    except OSError:
        candidates = []
    for candidate in candidates:
        try:
            hook_tree = ast.parse(candidate.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            # A hook file this function cannot read is one `_discover()`
            # cannot import either -- it prints IMPORT_FAILED and moves on,
            # and so does this.
            continue
        if _calls_the_seam(hook_tree):
            return "hook:%s" % (candidate.stem,)
    return "module_only"


def headless_token(
    character_id: int, skill_ids: "tuple[int, ...]", frame: bytes,
    sent_by: str, trailing: int, *, pc: bytes,
) -> str:
    """The one ASCII line GT-307 names as its ``HEADLESS_PROOF:``.

    Every number in it is a measurement of the arguments it was handed: the
    row count is the length of what the store returned, the byte count is
    the length of the frame the proven encoder composed, ``sent_by`` comes
    from ``seam_carrier()``, and ``trailing`` comes from
    ``measured_trailing_byte`` -- it used to be ``SKILL_LIST_TRAILING_BYTE``
    interpolated straight into the format string, which pf-adversary (D3)
    turned into a token reading ``trailing_u8=0`` about a frame carrying
    ``0x01``.  Nothing here re-derives an id from the class table -- that is
    the substitution GT-307 exists to rule out.

    ``rows`` COMES OFF THE WIRE (round `jty60h`, pf-adversary D3 again, one
    field to the left).  It used to be ``len(skill_ids)`` -- the list the
    store returned, which exists whether or not anything was ever composed
    or appended -- so the single line an operator pastes into ``GT-307``'s
    ``HEADLESS_PROOF:`` travelled alone saying ``rows=4`` about a login that
    sent no frame at all.  ``pc`` is keyword-only and has no default on
    purpose: a caller that has no composed pc cannot produce a token by
    forgetting an argument, and the two counts are compared here rather than
    trusted, so the store's answer and the wire's answer cannot disagree
    inside one line.  ``ids`` still comes from the store, because the
    substitution GT-307 rules out is exactly "the ids on the wire are not
    the ids on the row".
    """
    on_the_wire = measured_record_count(pc)
    if on_the_wire != len(skill_ids):
        raise SkillListAtLoginError(
            REFUSE_PAYLOAD_UNREADABLE,
            "the composed pc carries %d records but the store returned %d "
            "skill ids; a token that reported either number alone would be "
            "a measurement of nothing"
            % (on_the_wire, len(skill_ids)),
        )
    return (
        "SKILL_LIST_AT_LOGIN cid=%d rows=%d ids=(%s) trailing_u8=%d "
        "frame_bytes=%d sent_by=%s"
        % (
            character_id,
            on_the_wire,
            ",".join(str(skill_id) for skill_id in skill_ids),
            trailing,
            len(frame),
            sent_by,
        )
    )


def compose_from_database(
    database_path: "Any", character_id: int,
) -> "tuple[tuple[int, ...], bytes]":
    """``(skill ids, frame)`` for one character, read out of a real database.

    A thin drop of the ``pc`` from ``compose_from_database_with_pc``; every
    word below describes that function too.  The console entry point takes
    the three-value form because the token has to MEASURE the trailing byte
    off the composed payload rather than print a constant (pf-adversary D3),
    and ``pc`` is what carries it.
    """
    skill_ids, _pc, frame = compose_from_database_with_pc(
        database_path, character_id,
    )
    return skill_ids, frame


def compose_from_database_with_pc(
    database_path: "Any", character_id: int,
) -> "tuple[tuple[int, ...], bytes, bytes]":
    """``(skill ids, pc, frame)`` for one character, read out of a real database.

    Opens the file that is already there and refuses a missing one by name.
    It does NOT call ``store.migrate()``, writes no row and commits no
    change of its own.  The rows come back through
    ``read_character_skill_ids``, which is the same call the seam makes, so
    the token measures the production route rather than a second one built
    for the console.

    THE ONE SIDE EFFECT, STATED RATHER THAN DENIED.  ``list_character_skills``
    reads through ``SQLiteStore.connect()``, and that context manager runs
    ``PRAGMA journal_mode=WAL`` on every open.  Against a database the
    server has already booted -- every canonical one -- the mode is already
    WAL and the file does not change by a byte (a test sha256s it).  Against
    a database still in ``delete`` journal mode, opening it FLIPS it to WAL,
    which rewrites the header: that is a real write and this docstring is
    not going to call it "read-only" (another test measures the flip, so the
    claim cannot rot).  ``store.py`` has a ``connect_read_only()`` that would
    avoid it, but no skills reader goes through it, and adding a second
    query against LANE-DB's table is the thing this module refuses to do.
    Filed for the seam's owner rather than worked around here.
    """
    from pathlib import Path

    from .legacy_bridge import load_legacy
    from .store import SQLiteStore

    import sqlite3

    path = Path(database_path)
    if not path.is_file():
        raise SkillListAtLoginError(
            REFUSE_CHARACTER_ROW_MISSING,
            "no database at %s; this command reads an existing database and "
            "never creates one" % (path,),
        )
    # pf-adversary D5: is_file() is True of a zero-byte file, and
    # sqlite3.connect turns one into a fresh database on disk -- the exact
    # thing the refusal above promises not to do.  The header is the only
    # answer that is not a guess: every sqlite file starts with these 16
    # bytes, and no truncated copy or text stub does.
    with path.open("rb") as handle:
        header = handle.read(16)
    if header != b"SQLite format 3\x00":
        raise SkillListAtLoginError(
            REFUSE_NOT_A_DATABASE,
            "%s is not an sqlite database (header %r); refusing rather than "
            "creating one in it" % (path, header),
        )
    root = repository_root()
    store = SQLiteStore(path, root / "migrations")
    try:
        skill_ids = read_character_skill_ids(store, character_id)
    except OverflowError as error:
        raise SkillListAtLoginError(
            REFUSE_CHARACTER_ID_NOT_AN_INT,
            "character id %r does not fit an sqlite INTEGER" % (character_id,),
        ) from error
    except sqlite3.DatabaseError as error:
        raise SkillListAtLoginError(
            REFUSE_NOT_A_DATABASE,
            "%s did not answer as this project's database: %s" % (path, error),
        ) from error
    legacy = load_legacy(root / "current" / "pf_login_game_server_v141.py")
    pc, frame = make_skill_list_response(legacy, skill_ids)
    return skill_ids, pc, frame


def _print_console_line(line: str) -> None:
    """Print one line the cp874 bridge console can carry, always.

    ``headless_token`` builds its line out of integers and cannot carry a
    surprise, but the refusal line interpolates the operator's own ``--db``
    path.  pf-adversary (D6) pointed one at a directory with an "o-umlaut" in
    it and ``print`` raised ``UnicodeEncodeError`` INSIDE the error report --
    the tool dying while explaining why it could not run, which is the
    round-142 failure the ASCII house rule exists to prevent.  Escaping is
    lossy on purpose: an operator reading ``sch\\xf6n`` still recognises the
    path, and a dead console recognises nothing.
    """
    print(line.encode("ascii", "backslashreplace").decode("ascii"))


def main(argv: "list[str] | None" = None) -> int:
    """``python -m pirateforce_foundation.skill_list_at_login --character N``.

    Prints GT-307's token on success, or a single ``SKILL_LIST_AT_LOGIN_REFUSED``
    line with the named reason and exits 1.  A refusal is not a crash: the
    attended operator reads one line either way, and the reason string is the
    same one the seam would append to ``self.events``.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m pirateforce_foundation.skill_list_at_login",
        description=(
            "Read one character's persisted skill rows and compose the login "
            "skill-list frame from them."
        ),
    )
    parser.add_argument(
        "--character", type=int, required=True, metavar="CID",
        help="character id (the cid the console prints at creation)",
    )
    parser.add_argument(
        "--db", default=None, metavar="PATH",
        help="database file; default is the one a flagless boot opens (%s)"
             % DEFAULT_DB_RELATIVE_PATH,
    )
    parser.add_argument(
        "--runtime", default=None, metavar="PATH",
        help="runtime module to measure sent_by against (default: the "
             "runtime.py next to this module)",
    )
    args = parser.parse_args(argv)

    database = args.db
    if database is None:
        database = repository_root() / DEFAULT_DB_RELATIVE_PATH
    try:
        skill_ids, pc, frame = compose_from_database_with_pc(
            database, args.character,
        )
    except SkillListAtLoginError as error:
        _print_console_line(
            "SKILL_LIST_AT_LOGIN_REFUSED cid=%s reason=%s detail=%s"
            % (args.character, error.reason, error)
        )
        return 1
    _print_console_line(
        headless_token(
            args.character, skill_ids, frame, seam_carrier(args.runtime),
            measured_trailing_byte(pc, len(skill_ids)), pc=pc,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - console entry point
    raise SystemExit(main())
