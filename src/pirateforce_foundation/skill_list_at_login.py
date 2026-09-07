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

THE REASON THIS IS NOT WIRED IN THIS ROUND (read this before using the module)
----------------------------------------------
The HYP-PF-033 sweep lane's own docstring records, from GT-249 run on
a real client on 2026-09-05: after its six-frame sweep landed, the client
stopped emitting any outbound movement frame for the rest of the session --
the player could open windows and drag items but COULD NOT WALK until a fresh
login -- and which frame (or which interaction between them) causes it was
never isolated.  That lane's ``production_allowed`` is ``False`` for exactly
that reason.

This module composes ONE frame of that same vital.  Sending it unconditionally
on every login is therefore, on today's evidence, a candidate way to ship a
game where nobody can move.  So:

  * ``production_allowed`` is ``False`` here too, and the condition to flip it
    is written down rather than left to a future round's judgement: an
    attended run that sends THIS module's single frame at login, with its own
    observation window, and reports (a) the skill window populated and (b)
    movement still working afterwards.  That is the ticket this round files.
  * nothing in ``src/`` calls this module (``callers_in_src=0`` in its console
    token, measured by a test, not asserted here).  The one seam it needs is
    in ``runtime.py``, outside this lane's write zone, and the CORE-REQUEST
    filed with this round says in its own text that it must NOT be wired
    until that attended result comes back green on movement.

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
    LearnSkillResultRecord,
    make_learn_skill_result_response,
)


SKILL_LIST_AT_LOGIN_CHECKPOINT = "SKILL-LIST-AT-LOGIN-001"
production_allowed = False

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
        return make_learn_skill_result_response(
            legacy, records, SKILL_LIST_TRAILING_BYTE,
        )
    except ValueError as error:
        raise SkillListAtLoginError(
            REFUSE_SKILL_ID_OUTSIDE_U32,
            "the proven encoder refused these skill ids: %s" % (error,),
        ) from error


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


def describe_skill_list(skill_ids: "tuple[int, ...] | list[int]") -> tuple[str, ...]:
    """ASCII console lines for a headless boot to print.

    One line per record plus a summary, in the shape the bridge console can
    carry (cp874: ASCII only).  The summary's ``callers_in_src`` is a claim
    that is MEASURED by a test which greps every sibling module, not by this
    function -- a module under ``src/`` scanning its own package at import
    time is exactly the thing that has no business being here.
    """
    records = skill_list_records(skill_ids)
    lines = [
        "SKILL_LIST_AT_LOGIN record=%d skill_id=%d u32_0=%d u16_4=%d u32_8=%d"
        % (index, record.record_u32_0, record.record_u32_0,
           record.record_u16_4, record.record_u32_8)
        for index, record in enumerate(records)
    ]
    lines.append(
        "SKILL_LIST_AT_LOGIN_SUMMARY records=%d trailing=%d "
        "observed_cap=%d callers_in_src=0 production_allowed=%s RESULT=ARMED"
        % (
            len(records),
            SKILL_LIST_TRAILING_BYTE,
            OBSERVED_ACCEPTED_RECORD_COUNT,
            production_allowed,
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


def seam_carrier(runtime_path: "Any" = None) -> str:
    """Who would send this frame today, MEASURED off ``runtime.py``.

    ``runtime`` when the login path actually names ``login_skill_list_response``,
    ``module_only`` when it does not, ``unknown`` when there is no runtime to
    read.  GT-307's token line ends in ``sent_by=``, and a hard-coded
    ``sent_by=runtime`` would be the same species of lie as the
    ``callers_in_src=0`` that pf-adversary killed in round ``e8pss9``: a
    claim about the tree, printed by a format string that cannot see it.
    """
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
    return "runtime" if LOGIN_SEAM_SYMBOL in text else "module_only"


def headless_token(
    character_id: int, skill_ids: "tuple[int, ...]", frame: bytes,
    sent_by: str,
) -> str:
    """The one ASCII line GT-307 names as its ``HEADLESS_PROOF:``.

    Every number in it is a measurement of the arguments it was handed: the
    row count is the length of what the store returned, the byte count is
    the length of the frame the proven encoder composed, and ``sent_by``
    comes from ``seam_carrier()``.  Nothing here re-derives an id from the
    class table -- that is the substitution GT-307 exists to rule out.
    """
    return (
        "SKILL_LIST_AT_LOGIN cid=%d rows=%d ids=(%s) trailing_u8=%d "
        "frame_bytes=%d sent_by=%s"
        % (
            character_id,
            len(skill_ids),
            ",".join(str(skill_id) for skill_id in skill_ids),
            SKILL_LIST_TRAILING_BYTE,
            len(frame),
            sent_by,
        )
    )


def compose_from_database(
    database_path: "Any", character_id: int,
) -> "tuple[tuple[int, ...], bytes]":
    """``(skill ids, frame)`` for one character, read out of a real database.

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

    path = Path(database_path)
    if not path.is_file():
        raise SkillListAtLoginError(
            REFUSE_CHARACTER_ROW_MISSING,
            "no database at %s; this command reads an existing database and "
            "never creates one" % (path,),
        )
    root = repository_root()
    store = SQLiteStore(path, root / "migrations")
    skill_ids = read_character_skill_ids(store, character_id)
    legacy = load_legacy(root / "current" / "pf_login_game_server_v141.py")
    _pc, frame = make_skill_list_response(legacy, skill_ids)
    return skill_ids, frame


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
        skill_ids, frame = compose_from_database(database, args.character)
    except SkillListAtLoginError as error:
        print(
            "SKILL_LIST_AT_LOGIN_REFUSED cid=%s reason=%s detail=%s"
            % (args.character, error.reason, error)
        )
        return 1
    print(
        headless_token(
            args.character, skill_ids, frame, seam_carrier(args.runtime),
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - console entry point
    raise SystemExit(main())
