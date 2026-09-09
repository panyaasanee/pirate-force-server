"""LANE-CS: the learn-skill round trip -- adjudicate, spend, grant, and
COMPOSE THE CONFIRMATION FRAME the client is owed.

Where the project stops without this module
-------------------------------------------
Three halves of the learn-skill lane were on `main` and none of them was
joined to the next one:

  * `skill_learn_wiring.learn_skill_spend` reads a balance and spends it;
  * `skill_grant_wiring.learn_and_grant_skill` spends and then writes the
    row;
  * `learn_skill_result_frame.make_learn_skill_result_response` composes the
    proven 0x673C result body.

So a character could be charged a skill point and given a row, and the
client was told NOTHING -- the encoder that exists to tell her sat one
import away with no caller on any path a player reaches.  This module is
that path: one call, one named outcome, and on success the bytes.

WHAT IT REFUSES TO PRETEND
--------------------------
`learn_and_grant_skill` is TWO store calls and its own docstring says the
points are not refunded when the second one raises.  That window cannot be
closed from this lane: the single transaction that would close it has to
`BEGIN IMMEDIATE` around `character_skills` and `characters.skill_points`,
which are LANE-DB's tables and LANE-DB's write zone (a CORE-REQUEST for it
went out with this round).  What this lane CAN do, and does, is refuse to
let the window be silent:

  * every refusal that can be named BEFORE any point is spent is named
    before any point is spent (`preflight_refusal`);
  * when the grant raises anyway, the balance is RE-READ and compared with
    the balance from before the attempt, and the outcome is
    `spent_but_not_granted` -- a measurement, not an assumption, and a
    named outcome rather than a bare exception travelling up a stack that
    has no idea a point is now missing.

NONCLAIMS -- read these before using one symbol from this file
--------------------------------------------------------------
  * The SEMANTICS of the three 0x673C record members are NOT known and are
    not claimed here.  `RECORD_MEMBERS_ARE_THIS_PROJECTS_DESIGN` says in
    one constant what the encoder's own nonclaims say in prose: putting the
    skill id in `record_u32_0` is THIS PROJECT'S DESIGN, the same posture
    the result-frame lane already took for the record values it sweeps.
    Nobody has measured what the original server put there, and nobody can.
  * Nothing here claims a client renders anything for this frame.  No
    client has seen one composed by this path; that is an attended ticket
    (proposed to LANE-K this round -- ticket NUMBERS are K's to assign, so
    none is spelled here), not a flag flip -- `NOW.md` `0945`.
  * Nothing here claims which class may learn which skill.  No committed
    table answers that, so this module does not ask.
  * This module has NO frame dispatch and NO handler.  Nothing in
    `runtime.py` calls it; the seam is a CORE-REQUEST, and it is not
    smuggled in here.
"""

from dataclasses import dataclass
from typing import Any

from . import skill_grant_wiring
from .learn_skill_result_frame import (
    LearnSkillResultRecord,
    make_learn_skill_result_response,
)

#: No scenario flag.  This module reads and writes through gates that are
#: themselves on the normal boot; there is nothing here for a flag to hide.
production_allowed = True

#: The trailing u8 at object+0x2C.  Taken as a value the same way the
#: login-list lane takes its own: nobody knows what the byte means, so this
#: lane sends the one the only rendering capture carried rather than
#: inventing a second unknown.
#: THE SIBLING LANE IS NOT SPELLED HERE, ON PURPOSE.  Its own console
#: token counts "callers in src" by scanning every file in this package for
#: its module name, so prose about it is treated as a use of it -- LANE-CS
#: turned that pin red once already (round `jty60h`, pf-adversary D1) by
#: writing the name in a comment.  This note is what replaces the name.
LEARN_RESULT_TRAILING_BYTE = 0

#: WHICH MEMBER CARRIES WHAT IS THIS PROJECT'S DESIGN, NOT A MEASUREMENT.
#: Named as a constant so that a reader who greps for a claim finds the
#: disclaimer instead of a comment somebody deleted.
RECORD_MEMBERS_ARE_THIS_PROJECTS_DESIGN = (
    "record_u32_0=skill_id, record_u16_4=0, record_u32_8=points_remaining"
)

#: Outcomes.  Four named here, plus `OUTCOME_SPENT_ON_NOTHING` below (kept
#: apart because it is discovered after the grant call returns, not while
#: unwinding one that raised) -- five in total.  pf-adversary round
#: `mfgv4m`, D7: this comment used to say "exactly three" while a fourth
#: constant sat twelve lines below it; a fifth is added the same round this
#: sentence is corrected, so the count is written as a fact to keep current
#: rather than a number to trust.
OUTCOME_LEARNED = "learned"
OUTCOME_REFUSED = "refused"
OUTCOME_SPENT_BUT_NOT_GRANTED = "spent_but_not_granted"
#: pf-adversary round `mfgv4m`, D4 -- the exception branch used to fold this
#: into `OUTCOME_REFUSED` whenever the balance could not be RE-READ after a
#: raise (`points_after is None`), regardless of `points_before`.  A
#: refusal says nothing was spent; here nobody can say that, because the
#: one measurement that would say so is the measurement that just failed.
#: Reporting it as `refused` told a maintainer the point was safe when the
#: honest answer is "unknown" -- this outcome exists so "unknown" is a
#: word the caller can see instead of a guess baked into `spent`.
OUTCOME_SPEND_STATUS_UNKNOWN = "spend_status_unknown"

#: Refusal reasons.  Every one names the row or the rule, never the caller.
REFUSE_CHARACTER_ID_NOT_AN_INT = "character_id_is_not_an_int"
REFUSE_SKILL_ID_NOT_AN_INT = "skill_id_is_not_an_int"
REFUSE_STORE_CANNOT_GRANT = "store_does_not_answer_grant_learned_skill"
REFUSE_BALANCE_UNMEASURED = "skill_point_balance_has_never_been_written"
#: pf-adversary round `8wzpyw`, D1 -- the worst defect this module shipped
#: with in its first hour.  `grant_learned_skill` is `INSERT OR IGNORE`, so
#: learning a skill she ALREADY HOLDS wrote nothing and charged her anyway:
#: three clicks measured as three points gone, one row, and
#: `outcome=learned RESULT=TOLD` every time.  The evidence was already in
#: this module's hand -- the granted set came back the same size -- and
#: nothing looked at it.  Asked BEFORE the spend, because that is the only
#: place where refusing costs her nothing; the size check after the grant
#: is the belt behind it, for the row that appears between the two reads.
REFUSE_ALREADY_HOLDS_SKILL = "character_already_holds_this_skill"
#: The same defect seen from the other side: the grant returned, and the
#: set of skills did not grow.  Nothing was written, so nothing may be
#: reported as learned -- and the point that was already spent is named,
#: exactly like `spent_but_not_granted`, rather than swallowed.
OUTCOME_SPENT_ON_NOTHING = "spent_but_nothing_was_written"


class SkillLearnRoundTripError(RuntimeError):
    """One exception class, with a named `reason`, like this lane's others."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason


@dataclass(frozen=True)
class LearnSkillRoundTrip:
    """What happened, in the words a caller may act on.

    `pc` and `frame` are `None` for every outcome but `learned`: a refusal
    that still handed back bytes would be a frame nobody may send, and the
    caller would have to know which field to distrust.
    """

    outcome: str
    reason: "str | None"
    character_id: int
    skill_id: int
    points_before: "int | None"
    points_remaining: "int | None"
    skills_after_grant: "tuple[int, ...] | None"
    pc: "bytes | None"
    frame: "bytes | None"

    @property
    def learned(self) -> bool:
        return self.outcome == OUTCOME_LEARNED


def _balance_or_none(store: Any, character_id: int) -> "int | None":
    """The measured balance, or `None` when the store cannot answer at all.

    A store that raises while being asked for a balance is not evidence
    that nothing was spent, so the caller below treats `None` as "unknown"
    and never as "unchanged" -- the whole point of re-reading.
    """
    try:
        return store.get_skill_points(character_id)
    except Exception:                       # noqa: BLE001 - see docstring
        return None


def _skills_or_none(store: Any, character_id: int) -> "tuple[int, ...] | None":
    """The skill ids the character holds, or `None` when nobody can say.

    `None` means "not answered" and is never read as "she holds nothing":
    a store that cannot list, or raises while listing, is not evidence that
    a second charge is safe -- it is only evidence that this check cannot
    decide.  The size comparison after the grant is what still catches the
    duplicate in that case.
    """
    lister = getattr(store, "list_character_skills", None)
    if not callable(lister):
        return None
    try:
        return tuple(lister(character_id))
    except Exception:                       # noqa: BLE001 - see docstring
        return None


def preflight_refusal(store: Any, character_id: int, skill_id: int) -> "str | None":
    """The refusal to give BEFORE a single point is spent, or `None`.

    Only conditions that can be decided without writing are checked here.
    This is deliberately not a copy of `learn_skill_spend`'s own rules: the
    affordability rule lives there and stays there (one rule, one owner),
    and duplicating it would create the second answer this lane keeps
    writing tests to prevent.  What it adds is the checks that decide
    whether STEP TWO can possibly succeed, because those are the ones whose
    failure costs the player a point she can never get back.
    """
    if isinstance(character_id, bool) or not isinstance(character_id, int):
        return REFUSE_CHARACTER_ID_NOT_AN_INT
    if isinstance(skill_id, bool) or not isinstance(skill_id, int):
        return REFUSE_SKILL_ID_NOT_AN_INT
    if not callable(getattr(store, "grant_learned_skill", None)):
        return REFUSE_STORE_CANNOT_GRANT
    held = _skills_or_none(store, character_id)
    if held is not None and skill_id in held:
        return REFUSE_ALREADY_HOLDS_SKILL
    if _balance_or_none(store, character_id) is None:
        return REFUSE_BALANCE_UNMEASURED
    return None


def learn_skill_round_trip(
    legacy: Any, store: Any, character_id: int, skill_id: int,
) -> LearnSkillRoundTrip:
    """Adjudicate, spend, grant, and compose the client's confirmation.

    Returns a `LearnSkillRoundTrip` for every path this lane can name, and
    raises `SkillLearnRoundTripError` for none of them: a caller on the
    login/skill path must be able to answer a click without a `try`.  The
    one thing that still propagates is an exception from composing the
    frame, because a payload this lane cannot read back is not a refusal --
    it is a bug in this lane, and `make_learn_skill_result_response`
    already refuses it by name.
    """
    reason = preflight_refusal(store, character_id, skill_id)
    if reason is not None:
        return LearnSkillRoundTrip(
            OUTCOME_REFUSED, reason, character_id, skill_id,
            None, None, None, None, None,
        )

    points_before = _balance_or_none(store, character_id)
    held = _skills_or_none(store, character_id)
    try:
        points_remaining, skills_after = skill_grant_wiring.learn_and_grant_skill(
            store, character_id, skill_id,
        )
    except Exception as error:              # noqa: BLE001 - every refusal
        # this lane's two steps raise is a game answer, not a crash; which
        # one it was is decided by RE-READING the balance, never by reading
        # the exception's type.
        points_after = _balance_or_none(store, character_id)
        # pf-adversary round `mfgv4m`, D4: `points_after is None` (the
        # re-read itself failed, e.g. "database is locked") used to fall
        # through to the `else` below and be reported as `refused` with
        # `points_before` -- a point may well be gone and this outcome said
        # nothing was ever spent.  That comparison needs BOTH reads to mean
        # anything, so the case where either is missing is its own named
        # outcome instead of a silent guess.
        if points_before is None or points_after is None:
            outcome = OUTCOME_SPEND_STATUS_UNKNOWN
            reported_points = points_after if points_after is not None else points_before
        elif points_after < points_before:
            outcome = OUTCOME_SPENT_BUT_NOT_GRANTED
            reported_points = points_after
        else:
            outcome = OUTCOME_REFUSED
            reported_points = points_before
        return LearnSkillRoundTrip(
            outcome,
            getattr(error, "reason", None) or type(error).__name__,
            character_id, skill_id, points_before, reported_points,
            None, None, None,
        )

    # THE BELT BEHIND THE PREFLIGHT (same finding).  `grant_learned_skill`
    # is `INSERT OR IGNORE`: it returns the character's whole skill set
    # whether or not this call wrote a row.  If the set did not grow, the
    # point is already spent and nothing was written -- so no frame is
    # composed and the outcome says exactly that, instead of a cheerful
    # `learned` for a row that was already there.  `held` may be None
    # (the store could not list), and then this check cannot decide and
    # does not pretend to.
    if held is not None and len(tuple(skills_after)) <= len(held):
        return LearnSkillRoundTrip(
            OUTCOME_SPENT_ON_NOTHING, REFUSE_ALREADY_HOLDS_SKILL,
            character_id, skill_id, points_before, points_remaining,
            tuple(skills_after), None, None,
        )
    records = (
        LearnSkillResultRecord(
            record_u32_0=skill_id,
            record_u16_4=0,
            record_u32_8=max(int(points_remaining), 0),
        ),
    )
    pc, frame = make_learn_skill_result_response(
        legacy, records, LEARN_RESULT_TRAILING_BYTE,
    )
    return LearnSkillRoundTrip(
        OUTCOME_LEARNED, None, character_id, skill_id, points_before,
        points_remaining, tuple(skills_after), pc, frame,
    )


def headless_token(result: LearnSkillRoundTrip) -> str:
    """The one ASCII line an attended boot prints for `GT-321`.

    EVERY NUMBER THIS VITAL'S OWN BYTES CARRY comes off the decoded
    artifact, not off the arguments that were handed in -- the rule
    pf-adversary's D3 established one module to the left this same day.
    `skill=` and `points=` are read back out of the decoded record
    (`record_u32_0`/`record_u32_8`) when a record decoded, exactly the
    fields `RECORD_MEMBERS_ARE_THIS_PROJECTS_DESIGN` names for them --
    pf-adversary round `mfgv4m`, D6 found both still typed straight from
    `result.skill_id`/`result.points_remaining`, so a composer that
    silently swapped or dropped a field would still print a token that
    read TOLD with the caller's own numbers.  `frame_bytes` is the length
    of the composed frame; `records` is decoded back out of the composed
    pc rather than counted in the list that was encoded; `RESULT` is
    derived from the outcome, never typed into the format string.  A
    mutant that stops composing, or composes the wrong record, cannot
    print a healthy line here.

    `cid=` is the one field this vital's bytes never carry at all (see the
    module NONCLAIMS and `learn_skill_result_frame`'s: no character id is
    part of this record), so it is unavoidably `result.character_id` --
    echoed from the call, not read off any artifact, and named as such
    here rather than folded into the sentence above.
    """
    from .learn_skill_result_frame import (
        LEARN_SKILL_RESULT_PAYLOAD_BASE_SIZE,
        LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET,
        LEARN_SKILL_RESULT_RECORD_WIRE_SIZE,
        decode_learn_skill_result_payload,
    )

    records_on_wire, trailing_on_wire, frame_bytes = 0, -1, 0
    skill_on_wire, points_on_wire = result.skill_id, result.points_remaining
    if result.pc is not None and result.frame is not None:
        start = LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET
        # The count field is read off the wire and then handed straight back
        # through the decoder, so a pc that merely starts with the right tag
        # cannot answer.  The login-list lane's own row-count measurement was
        # written the same way, on the same finding, the same day (its module
        # name is deliberately not spelled here -- see the note beside
        # LEARN_RESULT_TRAILING_BYTE).
        declared = int.from_bytes(result.pc[start + 1:start + 3], "little")
        size = (
            LEARN_SKILL_RESULT_PAYLOAD_BASE_SIZE
            + LEARN_SKILL_RESULT_RECORD_WIRE_SIZE * declared
        )
        try:
            decoded, trailing_on_wire = decode_learn_skill_result_payload(
                result.pc[start:start + size]
            )
        except Exception:               # noqa: BLE001 - a pc this lane
            # cannot read back is not evidence the client was told
            # anything, so the token says so instead of dying inside the
            # line an operator is reading to find out what happened.
            decoded, trailing_on_wire = (), -1
        records_on_wire = len(decoded)
        frame_bytes = len(result.frame)
        if decoded:
            # pf-adversary round `mfgv4m`, D6: read the fields this vital's
            # own design (`RECORD_MEMBERS_ARE_THIS_PROJECTS_DESIGN`) names
            # for them off the decoded record, not off the arguments this
            # function was handed -- a token that merely echoed its inputs
            # could not tell a correctly composed frame from one that put
            # the wrong skill id or the wrong balance on the wire.
            skill_on_wire = decoded[0].record_u32_0
            points_on_wire = decoded[0].record_u32_8
    return (
        "LEARN_SKILL_ROUND_TRIP cid=%d skill=%d outcome=%s reason=%s "
        "points=%s records=%d trailing_u8=%d frame_bytes=%d RESULT=%s"
        % (
            result.character_id,
            skill_on_wire,
            result.outcome,
            result.reason if result.reason is not None else "-",
            points_on_wire if points_on_wire is not None else "-",
            records_on_wire,
            trailing_on_wire,
            frame_bytes,
            "TOLD" if records_on_wire else "NOT_TOLD",
        )
    )


#: The database a flagless boot opens, spelled once.
DEFAULT_DB_RELATIVE_PATH = "state/pirateforce.sqlite3"


def _print_console_line(line: str) -> None:
    """Print one line the cp874 bridge console can carry, always.

    The token is built out of integers and names and cannot carry a
    surprise, but the refusal line interpolates the operator's own `--db`
    path.  Escaping is lossy on purpose: an operator reading `sch\\xf6n`
    still recognises the path, and a dead console recognises nothing.
    """
    print(line.encode("ascii", "backslashreplace").decode("ascii"))


def main(argv: "list[str] | None" = None) -> int:
    """``python -m pirateforce_foundation.skill_learn_roundtrip``.

    WHY THIS ENTRY POINT EXISTS AT ALL, in one sentence: an attended ticket
    whose pass criterion is a console line that NOTHING IN THE TREE CAN
    PRINT burns a slot on the owner's machine and comes back FAIL blaming
    the server.  This lane escalated exactly that defect against `GT-307`
    three hours before writing this file, and pf-adversary caught the same
    lane about to file it again.  So the token this lane's new ticket names
    is produced by a command that ships with the tree, against a real
    database, the same way the login lane produces its own.

    Prints one `LEARN_SKILL_ROUND_TRIP` line and exits 0 when the learn
    succeeded, or the same line with the named refusal and exits 1.  A
    refusal is not a crash: the operator reads one line either way.
    """
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(
        prog="python -m pirateforce_foundation.skill_learn_roundtrip",
        description=(
            "Adjudicate one learn-skill request against a real database and "
            "compose the client's confirmation frame."
        ),
    )
    parser.add_argument(
        "--character", type=int, required=True, metavar="CID",
        help="character id (the cid the console prints at creation)",
    )
    parser.add_argument(
        "--skill", type=int, required=True, metavar="ID",
        help="skill id from the client's own SKILL_CONTEXT table",
    )
    parser.add_argument(
        "--db", default=None, metavar="PATH",
        help="database file; default is the one a flagless boot opens (%s)"
             % DEFAULT_DB_RELATIVE_PATH,
    )
    args = parser.parse_args(argv)

    from .legacy_bridge import load_legacy
    from .store import SQLiteStore

    # The checkout this module runs out of.  Computed here rather than
    # imported from the sibling that already has the same three lines: that
    # module's own console token counts "callers in src" by scanning every
    # file in this package for its name, so importing it would make its
    # token report a caller that does not call it.  Three lines duplicated
    # beats a token that lies (see the note beside
    # LEARN_RESULT_TRAILING_BYTE).
    root = Path(__file__).resolve().parents[2]
    database = args.db
    if database is None:
        database = Path(root) / DEFAULT_DB_RELATIVE_PATH
    store = SQLiteStore(database, Path(root) / "migrations")
    # pf-adversary round `mfgv4m`, D1: without this call, a `--db` path that
    # does not exist yet is silently handed to sqlite3 (which creates an
    # empty FILE, no tables) and every read below then raises, is swallowed
    # by `_balance_or_none`/`_skills_or_none`, and comes out the far end as
    # the named refusal `REFUSE_BALANCE_UNMEASURED` -- a real, specific-
    # sounding reason for what is actually "this database was never
    # migrated".  `migrate()` is the same call the test fixture in `tests/
    # test_skill_learn_roundtrip.py` makes before touching a store, and it
    # is a no-op against an already-migrated database (nothing left to
    # apply), so this does not change behaviour against the live server's
    # own database (`app.py` migrates it at boot) -- it only stops this
    # entry point from lying about a database nobody has migrated yet.
    store.migrate()
    legacy = load_legacy(Path(root) / "current" / "pf_login_game_server_v141.py")
    result = learn_skill_round_trip(legacy, store, args.character, args.skill)
    _print_console_line(headless_token(result))
    return 0 if result.learned else 1


if __name__ == "__main__":  # pragma: no cover - console entry point
    raise SystemExit(main())
