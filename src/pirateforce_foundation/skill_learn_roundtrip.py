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

#: The trailing u8 at object+0x2C.  Imported as a value the same way
#: `skill_list_at_login` imports its own: nobody knows what the byte means,
#: so this lane sends the one the only rendering capture carried rather
#: than inventing a second unknown.
LEARN_RESULT_TRAILING_BYTE = 0

#: WHICH MEMBER CARRIES WHAT IS THIS PROJECT'S DESIGN, NOT A MEASUREMENT.
#: Named as a constant so that a reader who greps for a claim finds the
#: disclaimer instead of a comment somebody deleted.
RECORD_MEMBERS_ARE_THIS_PROJECTS_DESIGN = (
    "record_u32_0=skill_id, record_u16_4=0, record_u32_8=points_remaining"
)

#: Outcomes.  Exactly three, and the third one exists because the window
#: between the spend and the grant is real.
OUTCOME_LEARNED = "learned"
OUTCOME_REFUSED = "refused"
OUTCOME_SPENT_BUT_NOT_GRANTED = "spent_but_not_granted"

#: Refusal reasons.  Every one names the row or the rule, never the caller.
REFUSE_CHARACTER_ID_NOT_AN_INT = "character_id_is_not_an_int"
REFUSE_SKILL_ID_NOT_AN_INT = "skill_id_is_not_an_int"
REFUSE_STORE_CANNOT_GRANT = "store_does_not_answer_grant_learned_skill"
REFUSE_BALANCE_UNMEASURED = "skill_point_balance_has_never_been_written"


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
    try:
        points_remaining, skills_after = skill_grant_wiring.learn_and_grant_skill(
            store, character_id, skill_id,
        )
    except Exception as error:              # noqa: BLE001 - every refusal
        # this lane's two steps raise is a game answer, not a crash; which
        # one it was is decided by RE-READING the balance, never by reading
        # the exception's type.
        points_after = _balance_or_none(store, character_id)
        spent = (
            points_before is not None
            and points_after is not None
            and points_after < points_before
        )
        return LearnSkillRoundTrip(
            OUTCOME_SPENT_BUT_NOT_GRANTED if spent else OUTCOME_REFUSED,
            getattr(error, "reason", None) or type(error).__name__,
            character_id, skill_id, points_before,
            points_after if spent else points_before,
            None, None, None,
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

    EVERY NUMBER COMES OFF THE ARTIFACT, not off the arguments that were
    handed in -- the rule pf-adversary's D3 established one module to the
    left this same day.  `frame_bytes` is the length of the composed frame;
    `records` is decoded back out of the composed pc rather than counted in
    the list that was encoded; `RESULT` is derived from the outcome, never
    typed into the format string.  A mutant that stops composing cannot
    print a healthy line here.
    """
    from .learn_skill_result_frame import (
        LEARN_SKILL_RESULT_PAYLOAD_BASE_SIZE,
        LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET,
        LEARN_SKILL_RESULT_RECORD_WIRE_SIZE,
        decode_learn_skill_result_payload,
    )

    records_on_wire, trailing_on_wire, frame_bytes = 0, -1, 0
    if result.pc is not None and result.frame is not None:
        start = LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET
        # The count field is read off the wire and then handed straight back
        # through the decoder, so a pc that merely starts with the right tag
        # cannot answer -- `skill_list_at_login.measured_record_count` was
        # written the same way, on the same finding, the same day.
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
    return (
        "LEARN_SKILL_ROUND_TRIP cid=%d skill=%d outcome=%s reason=%s "
        "points=%s records=%d trailing_u8=%d frame_bytes=%d RESULT=%s"
        % (
            result.character_id,
            result.skill_id,
            result.outcome,
            result.reason if result.reason is not None else "-",
            result.points_remaining if result.points_remaining is not None
            else "-",
            records_on_wire,
            trailing_on_wire,
            frame_bytes,
            "TOLD" if records_on_wire else "NOT_TOLD",
        )
    )
