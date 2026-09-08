"""Read back WHAT THE SANDBOX ROW HOLDS, in 12 ASCII characters.

WHY THIS MODULE EXISTS, said as the attended tester experiences it.  The GM
skill sandbox (`PANYA-ORDER 2026-09-08 14:5x`, sections 2.1-2.2) is two
commands that write rows and move no pixel: `/job <class_id>` writes
`characters.class_id`, `/skill all` writes 137 rows into `character_skills`.
Both answer ON SCREEN at the moment they are typed -- `JOB SET RELOG`,
`SKILL ALL OK` -- and then the tester relogs, which is the whole point of
those two sentences.  AFTER the relog there was no way to ask whether the
rows survived it.  The `class_id` half the client draws for itself; the 137
skill rows it does not, because nothing sends them yet (LANE-CS owns the
login skill list, `#1159`), so "the sandbox is ready" was a question only the
server console could answer -- and at an attended boot the person typing is
looking at the game, not at the console.

`sandbox` is that readback as a command.  It WRITES NOTHING -- no row, no
file, no frame but its own sentence -- and it answers for the character the
typing session has selected, on the same local-talk notice channel `staged`,
`/lv` and the typo notice use.  It is the sibling of `gm/staged_readback.py`
one question over: that one answers "where will my next login put me", this
one answers "what will my next login find on my row".

IT ASKS THE DOORS THE LOGIN ITSELF ASKS, and that is the whole design.  The
class comes from `session._class_id_on_the_row` -- not a copy of it, the
function `legacy_bridge.start_game` calls to decide between the row's class
and `player_wire.PLAYER_LOGIN_CLASS_ID` -- so "what this says" and "what the
next login will send" cannot disagree by construction.  The skills come from
`store.list_character_skills`, the same door `gm/skill_all_command.py` counts
with.  A readback that re-implements either lookup would answer for a world
that does not exist; this is the mistake `gm/staged_readback.py` made in its
first version and paid for three ways (pf-adversary round `qpauwp`).

THE FIVE ANSWERS, and why each is the length it is.  A notice body is exactly
12 printable ASCII characters (`gm/say_wire.py::NOTICE_TEXT_EXACT_LENGTH` --
a MEASURED length, GT-006/GT-009, not a style rule), so these sentences were
found inside that length rather than written freely:

    JOB016 SK137   the row holds class 16 and 137 of the curriculum skills
    NO JOB SK137   the row holds NO class; the next login sends the constant
    JOB016 SK???   the class read; the skill rows could not be counted
    NO JOB SK???   neither could be read (or neither has ever been written)
    COUNT TOOBIG   a number on the row does not fit the width it is given

`NO JOB` FOLDS TWO CAUSES ON PURPOSE -- a NULL column and a read that failed
-- and that is not sloppiness: `session._class_id_on_the_row` folds them too,
deliberately (`COO-DECISION 20260904_0446` point 3), because the login sends
its own constant in both cases.  A readback whose screen distinguished two
states the login does not would be answering a question nobody at the client
can act on.  The SERVER console line below keeps them apart for whoever is
reading it, since there the width is not pinned.

`SK<n>` COUNTS CURRICULUM IDS, NEVER ROWS.  A character can hold skills this
lane never granted (`grant_starting_skills` writes some at birth), so "how
many rows are on the table" and "is the sandbox stocked" are different
questions and only the second one is this command's.  The row total goes to
the console line as `rows=`, where it cannot be mistaken for the first.

EVERY CHARACTER COMES OUT OF THIS MODULE OR OUT OF AN INTEGER, never out of
anything a client typed: `sandbox` takes no arguments at all, so there is no
query to echo and the whole class of hazards the `warp <scene name>` form had
to close (pf-adversary round `osxc85`, D1/D2) cannot exist here.

NONCLAIMS, the ones that matter before anybody quotes this on a ticket:

* `JOB016 SK137` says WHAT THE ROWS HOLD.  It is not evidence that the client
  draws class 16, that any skill is castable, or that a skill window opens --
  nothing sends the skill list yet.  This is a tool for reaching a testable
  state, never proof that the state is right (`prompts/LANE-GM.md`, sentence
  three).
* it says nothing about SKILL POINTS.  `/skill all` spends none, so a stocked
  sandbox row is not a row that earned what it holds.
* the count is of the CURRICULUM under its sha256 pin.  If that table grows,
  `SK137` becomes `SK<new total>` on the same rows -- the denominator is the
  committed file, not a memory of it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import class_skill_curriculum as _curriculum
from ..session import _class_id_on_the_row

#: The console token this lane greps for at an attended boot.
CONSOLE_TOKEN = "GM_SANDBOX"

# The one place these bodies are spelled.  Their length is asserted against
# `say_wire.NOTICE_TEXT_EXACT_LENGTH` itself rather than against the literal
# 12, so a round that moves the pinned length moves these with it instead of
# shipping a body the wire will refuse.
NOTICE_TOO_BIG = "COUNT TOOBIG"

# `JOB` + three digits, and three rather than "as many as the id needs": a
# fixed width keeps the body at the pinned length for class 1 and class 32
# alike, and a variable one would ship an 11-character body for class 1 --
# refused by `say_wire.make_local_talk_notice_frame`, which is a crash where
# an answer was asked for.  The same reasoning `staged`'s `%06d` records.
_CLASS_WIDTH = 3
_SKILL_WIDTH = 3
_NO_CLASS = "NO JOB"
_UNKNOWN_SKILLS = "?" * _SKILL_WIDTH


@dataclass(frozen=True)
class SandboxState:
    """What the row holds, as the login's own doors answer it.

    `class_id` is `None` for BOTH "the column is NULL" and "the column could
    not be read", because the login cannot tell those apart either -- see the
    module docstring.  `curriculum_held` is `None` only for "could not be
    counted"; zero rows counted is `0`, which is a different fact and reads
    differently on screen.
    """

    class_id: int | None
    curriculum_held: int | None
    rows_held: int | None
    curriculum_total: int


def read_sandbox_state(store: object, character_id: object) -> SandboxState:
    """Ask the row what it holds.  NEVER RAISES.

    Never raising is not tidiness: this runs on the listener thread, and
    `gm/level_command.write_level`'s docstring records what an escaping
    exception does there -- it unwinds the thread and parks the client on
    "connecting" forever.  A readback that can crash the session it is
    reporting on is worse than no readback.
    """
    total = _curriculum.SKILL_COUNT
    if type(character_id) is not int or isinstance(character_id, bool) or character_id <= 0:
        # No selected character on this connection: there is no row to read,
        # which is not the same fact as a row that reads back empty.
        return SandboxState(None, None, None, total)
    class_id = _class_id_on_the_row(store, character_id)
    if type(class_id) is not int or isinstance(class_id, bool):
        # `_class_id_on_the_row` promises `None` or the stored value, and the
        # stored value is whatever LANE-DB's typed map holds -- a `str` in a
        # hand-edited row included.  A non-int is "no class this lane will
        # render", never something to format into the body.
        class_id = None
    held, rows = _count_skills(store, character_id)
    return SandboxState(class_id, held, rows, total)


def _count_skills(store: object, character_id: int) -> tuple[int | None, int | None]:
    """(curriculum ids held, rows held), or `(None, None)` for "unreadable".

    NEVER SUBSTITUTES ZERO FOR AN ANSWER IT DID NOT GET, which is the defect
    pf-adversary measured in `gm/skill_all_command._read_skills`'s first
    version (round `wv0fpe`, D3): an empty set standing in for "unknown"
    turned an unreadable store into a confident number on screen.
    """
    reader = getattr(store, "list_character_skills", None)
    if reader is None:
        return (None, None)
    try:
        ids = frozenset(int(i) for i in reader(character_id))
    except Exception:  # noqa: BLE001 -- see the docstring
        return (None, None)
    curriculum = frozenset(_curriculum.CURRICULUM_SKILL_IDS)
    return (len(ids & curriculum), len(ids))


def notice_body(state: SandboxState) -> str:
    """The 12-character sentence for `state`.

    The length is not asserted here -- `say_wire.make_local_talk_notice_frame`
    refuses anything else, and a second check in this module would be a copy
    of the rule rather than the rule.  `tests/test_gm_sandbox_readback.py`
    pins every branch of this function against that constant.
    """
    class_part = _NO_CLASS
    if state.class_id is not None:
        if not _fits(state.class_id, _CLASS_WIDTH):
            return NOTICE_TOO_BIG
        class_part = "JOB%0*d" % (_CLASS_WIDTH, state.class_id)
    skill_part = "SK" + _UNKNOWN_SKILLS
    if state.curriculum_held is not None:
        if not _fits(state.curriculum_held, _SKILL_WIDTH):
            return NOTICE_TOO_BIG
        skill_part = "SK%0*d" % (_SKILL_WIDTH, state.curriculum_held)
    return f"{class_part} {skill_part}"


def _fits(value: int, width: int) -> bool:
    """Would `value` render inside `width` digits without a sign?

    A negative class id is as unrenderable as a five-digit one -- `%03d` of
    -1 is `"-01"`, which reads as a class this game does not have.
    """
    return 0 <= value < 10 ** width


def console_line(character_id: object, state: SandboxState) -> str:
    """The server-console line, where the width is not pinned.

    Carries what the screen cannot: the row total next to the curriculum
    count, and `class_id=none` in the one place a reader can act on the
    difference between a NULL column and a read that failed -- by looking at
    whether `rows=` answered on the same line.
    """
    class_id = "none" if state.class_id is None else str(state.class_id)
    held = "unknown" if state.curriculum_held is None else str(state.curriculum_held)
    rows = "unknown" if state.rows_held is None else str(state.rows_held)
    return (
        f"{CONSOLE_TOKEN} cid={character_id} class_id={class_id} "
        f"skills={held}/{state.curriculum_total} rows={rows}"
    )
