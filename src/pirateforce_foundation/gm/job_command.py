"""GM `/job <class_id>`: set the selected character's stored class.  DB ONLY.

PANYA-ORDER 2026-09-08 ~14:5x (`pf_bridge/notes_to_chief/20260908_1455_KA1A-
PANYA-ORDER-COO-gm-sandbox-skill-all-job-no-level-gate-class-weapons.md`,
section 2.2), routed by `COO-DECISION 20260908_1541`: the owner wants ONE GM
character she can move between the five classes, so she can watch every
class's skills come out on a training dummy without rolling five characters.

WHAT THIS MODULE DOES, AND THE HALF IT REFUSES TO DO.

  * IT WRITES `characters.class_id` through LANE-DB's own existing door,
    `store.write_typed_attributes(character_id, {"class_id": n})` -- the
    same door `/lv` writes `level` through (`gm/level_command.py`), the same
    column `migrations/006_character_typed_attribute_columns.sql` created,
    and the same validator (`persistence_typed_attrs.validate`).  No new
    store method is asked for and none is added.
  * THE SCREEN HALF IT DELIVERS IS THE RELOG ONE.  `session.py`'s login
    reads this exact column back (`_class_id_on_the_row`, which calls
    `store.read_typed_attributes(character_id).get("class_id")`) and
    `legacy_bridge.start_game` puts it on the wire as `u32tag(0x19,
    class_id)` inside the login actor.  So the next login after this write
    draws the new class -- and NOT before, which is why every success line
    this module writes says `relog_required=yes` in the owner's own words
    rather than leaving her to grade the command broken.
  * IT SENDS NO ATTRIBUTE FRAME.  The frame that would change a class
    mid-session is `UpdateAttrVital` (0x309A) with the class field, and
    `gm/attr_wire.py`'s (b'') rule forbids every partial block through its
    named-field door: the client's apply is a full-object copy (`RE-222`
    Q0), so a sparse 0x309A zeroes every field this lane leaves unset, HP
    included -- that is what killed a live client in one frame during
    `GT-193`/`GT-218`.  This module does not import `attr_wire`, does not
    reach for it, and must never be edited into a second sparse sender.

WHY THE LOGIN GATE IS A DIFFERENT QUESTION HERE THAN IT IS FOR `/lv`.
`/lv` has to ask `store.read_character_vitals_or_none` before it will stand
behind its write, because the login's VITALS are all-three-or-none
(`PANYA-DECISION 20260901_1059`) and a row with a broken HP pair sends the
composer's constant instead of the row's level.  The class does not ride
that gate: `legacy_bridge.start_game`'s own comment says so in as many
words -- "THIS IS NOT AN ALL-OR-NONE PAIR with the vitals above" -- and
`session.py` reads the class from `read_typed_attributes`, which answers
about the COLUMN.  So the read-back check below IS the login question for
this command, asked at the same door the login asks, and there is no second
gate to consult.  Saying otherwise (copying `/lv`'s `login_would_send`
verbatim) would refuse writes the login would have honoured.

WHY IT ALSO REFUSES THE CANONICAL DATABASE.  `AGENTS.md` section 7: this
command WRITES a row, so the shared canonical-DB gate in
`gm/chat_command_action.py` stands above it exactly as it does for `/lv`
and `/speed`, and it fails CLOSED -- a store path this lane cannot read
counts as canonical and the write is refused.  An attended boot runs a
timestamped run-copy DB, and a relog inside that boot reads back the row.

THE ALLOWLIST IS NOT RE-IMPLEMENTED HERE.  `/job` is a sibling of `/lv` and
`/warp` in `gm/commands.py`'s one grammar, so it comes through
`gm/chat_command.handle_local_talk_chat`'s identity check like they do
(`REFUSAL_NOT_GM`); a non-GM's line is never decoded, never parsed, and
never reaches this module at all.  PANYA-ORDER section 3 item 1 is answered
by using that door, not by adding a second one.

MULTIPLAYER.  This command names its row by the `characters.id` of the
character selected ON THE CONNECTION WHOSE FRAME IS BEING ANSWERED.  Two GMs
on two sessions typing `/job` write two different rows; nothing here is
process-global or per-scene, so `TWO_SESSIONS_SAME_SCENE` is answered by
construction.

NOT AN M-ANYTHING.  A class set by a GM is a way to REACH a testable state,
never evidence that class selection works (`prompts/LANE-GM.md`, sentence
3).  Any ticket that uses `/job` to arrive somewhere says so in its
nonclaims.
"""
from __future__ import annotations

from dataclasses import dataclass

from .. import class_catalog
from .. import persistence_typed_attrs as _typed_attrs


#: The wire field this command writes: the class field, x=13, u32
#: (`persistence_typed_attrs.TYPED_COLUMNS`).  Spelled as the FIELD NUMBER
#: and resolved to a column name through LANE-DB's own map, so a column
#: rename in their zone cannot leave this module writing a stale string --
#: the same discipline `gm/level_command.LEVEL_FIELD_X` keeps.
CLASS_FIELD_X = 13

#: Refusal reasons.  Strings, because they are written into the audit row
#: and read by a human on a console line; each one names WHAT was wrong,
#: never "failed".  None of them repeats the command name: the dispatch
#: prefixes them with `refused_job_` / `gm_chat_action_job_refused_`.
REFUSED_ARGS_SHAPE = "args_not_a_one_string_tuple"
REFUSED_NOT_AN_INTEGER = "argument_not_an_integer"
REFUSED_NOT_A_CLASS_ID = "not_one_of_the_five_class_ids"
REFUSED_NO_CHARACTER = "no_selected_character"
REFUSED_NO_STORE = "no_store_on_this_session"
REFUSED_ROW_MISSING = "row_not_found"
REFUSED_WRITE_FAILED = "write_failed"
REFUSED_READBACK_MISMATCH = "readback_did_not_hold_the_value"
#: The repair after a refusal that put a value on disk this command will not
#: stand behind.  A SEPARATE word from the refusal it follows, because "the
#: row was put back" and "the row is still carrying it" are different states
#: for the tester and only one of them is safe to walk away from.  Same two
#: suffixes `gm/level_command.py` uses, for the same reason.
REPAIRED_SUFFIX = "_row_put_back"
REPAIR_FAILED_SUFFIX = "_row_still_carries_it"


class JobArgumentError(ValueError):
    """`/job`'s argument is not a class this module will write."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def class_column() -> str:
    """The `characters` column this command writes (`class_id`)."""
    return _typed_attrs.column_for(CLASS_FIELD_X)


def class_ids() -> tuple[int, ...]:
    """The five class ids this command accepts: (1, 2, 4, 16, 32) today.

    READ FROM `class_catalog`, never retyped.  They are a BITMASK, not
    1..5 (`class_catalog` builds them from the client's own
    `CHARCREATE_CLASS` table), and a literal tuple here would be a second
    place for that table to drift away from.
    """
    return tuple(class_catalog.CLASS_IDS)


def usage() -> str:
    """The one sentence a human gets back for a bad argument.

    It NAMES THE FIVE VALUES rather than saying "a valid class", because
    the owner's own order says a refusal must tell her what it would have
    accepted ("`COMMAND_REFUSED`... bad values are refused WITH the values
    that are accepted -- never silent, never guessed").
    """
    return "job <" + "|".join(str(i) for i in class_ids()) + ">"


def parse_class_id(args: object) -> int:
    """`args` (a `GmCommand.args`) -> the class id to write, or raise.

    `commands.parse_gm_command` has already checked that `job` carries
    exactly one integer-looking token, so this is the SECOND check,
    deliberately -- `gm/level_command.parse_level`'s docstring carries the
    pf-adversary history of hand-built `args` values (an integer-keyed dict,
    a tuple subclass lying through `__len__`/`__getitem__`) defeating a
    shape check one layer up.  A module that writes a database row does not
    inherit another module's validation; it repeats it.

    `type(args) is not tuple` rather than `isinstance`, for that same
    tuple-subclass reason.  `bool` cannot come out of `int(str)`.
    """
    if type(args) is not tuple or len(args) != 1 or type(args[0]) is not str:
        raise JobArgumentError(
            REFUSED_ARGS_SHAPE,
            f"job takes exactly one string argument; got {args!r}",
        )
    text = args[0].strip()
    try:
        class_id = int(text, 10)
    except ValueError:
        raise JobArgumentError(
            REFUSED_NOT_AN_INTEGER, f"{text!r} is not a whole number; {usage()}"
        ) from None
    if class_id not in class_ids():
        raise JobArgumentError(
            REFUSED_NOT_A_CLASS_ID,
            f"class {class_id} is not one of the five class ids; {usage()}",
        )
    return class_id


@dataclass(frozen=True)
class JobWrite:
    """What one `/job` did, in the shape the console line and the audit read.

    `written` is the value the STORE READ BACK, never the number the GM
    typed -- the two differ exactly when something between them changed the
    value, which is the case a `/job` that "looked fine" must not hide.
    `previous` is `None` when the row's class could not be read beforehand
    (an unseeded row -- `migrations/006` adds `class_id` with no default and
    no backfill, so NULL is the ordinary state of an old row); that is not a
    refusal, it only means there is nothing to undo TO.
    """

    written: int | None
    previous: int | None
    refusal: str | None
    detail: str

    @property
    def ok(self) -> bool:
        return self.refusal is None


def _previous_class_id(store: object, character_id: int) -> int | None:
    """The row's current class, or `None` for "could not be read".

    THE COLUMN, through the door the LOGIN itself reads
    (`session.py::_class_id_on_the_row`), so "what the login would have
    drawn a moment ago" and "what this function returns" cannot disagree.

    Never raises: a failure to read the OLD value must not stop the new one
    being written -- the owner asked for the class to change, not for a
    perfect audit of what it was.
    """
    reader = getattr(store, "read_typed_attributes", None)
    if reader is None:
        return None
    try:
        stored = reader(character_id)
        class_id = stored[class_column()]
    except Exception:  # noqa: BLE001 -- KeyError included: the column is
        # OMITTED when NULL, which is "never written", not an error
        return None
    if type(class_id) is not int or isinstance(class_id, bool):
        return None
    return class_id


def login_would_send(store: object, character_id: int, class_id: int) -> bool:
    """Would the NEXT LOGIN really put `class_id` on the wire for this row?

    ASKED OF THE LOGIN'S OWN DOOR -- `read_typed_attributes`, which is what
    `session.py::_class_id_on_the_row` calls, and whose answer decides
    between the row's class and `player_wire.PLAYER_LOGIN_CLASS_ID`.  See
    the module docstring for why this is a DIFFERENT door from the one
    `/lv` has to ask (the vitals gate does not govern the class).

    Unanswerable -> `False`, never `True`: this gates a CLAIM about a
    screen, and "cannot tell" may not be reported as "yes".
    """
    return _previous_class_id(store, character_id) == class_id


def _repair(store: object, character_id: int, previous: int | None) -> str:
    """Put `previous` back after a write this command will not stand behind.

    Returns the suffix the caller appends to its refusal reason, so the
    audit row and the console line say WHICH of the two durable states the
    tester is walking away from.  `""` when there was nothing to put back.
    """
    if previous is None:
        return ""
    writer = getattr(store, "write_typed_attributes", None)
    if writer is None:
        return REPAIR_FAILED_SUFFIX
    try:
        writer(character_id, {class_column(): previous})
    except Exception:  # noqa: BLE001 -- the repair may not raise either
        return REPAIR_FAILED_SUFFIX
    return REPAIRED_SUFFIX


def write_class_id(store: object, character_id: object, class_id: int) -> JobWrite:
    """Write `class_id` onto `character_id`'s row.  Never raises.

    THE ORDER IS: read the old value (best effort) -> write -> check the
    read-back.  The read-back check is not ceremony: `write_typed_attributes`
    returns the row's typed columns AFTER the write, so a value that came
    back different from the one asked for means something between this
    module and the disk changed it, and reporting success on that would be
    the exact shape of lie this house's evidence rules exist to stop.

    EVERY failure comes back as a refusal object with a NAMED reason,
    because this is called from a chat dispatch whose own module docstring
    records what an escaping exception costs there: `runtime.py`'s handler
    catches only four types and `v141` wraps the connection loop with no
    `except` at all, so an escaping `TypeError` unwinds the listener thread
    and parks the client on "connecting".
    """
    if type(character_id) is not int or isinstance(character_id, bool) or character_id <= 0:
        return JobWrite(
            None, None, REFUSED_NO_CHARACTER,
            f"no usable selected character id on this connection ({character_id!r})",
        )
    writer = getattr(store, "write_typed_attributes", None)
    if writer is None:
        return JobWrite(
            None, None, REFUSED_NO_STORE,
            "this session's store has no write_typed_attributes door",
        )
    column = class_column()
    previous = _previous_class_id(store, character_id)
    try:
        after = writer(character_id, {column: class_id})
    except KeyError:
        return JobWrite(
            None, previous, REFUSED_ROW_MISSING,
            f"character {character_id} has no live row to write",
        )
    except Exception as error:  # noqa: BLE001 -- named, never escaping
        return JobWrite(
            None, previous, REFUSED_WRITE_FAILED,
            f"{type(error).__name__}: {error}",
        )
    try:
        read_back = after[column]
    except Exception:  # noqa: BLE001 -- a store that returned another shape
        read_back = None
    if type(read_back) is not int or isinstance(read_back, bool) or read_back != class_id:
        # REPAIRED HERE, NOW, not handed up as an `undo` for the dispatch to
        # run.  pf-adversary (round `l86bt4`, D6) measured why on `/lv`: the
        # dispatch runs a verdict's undo ONLY when the audit row could not
        # be written, so an undo attached to this branch never ran on the
        # ordinary path.
        repair = _repair(store, character_id, previous)
        return JobWrite(
            class_id, previous, f"{REFUSED_READBACK_MISMATCH}{repair}",
            f"asked for class {class_id}, the row read back {read_back!r}",
        )
    return JobWrite(
        read_back, previous, None,
        f"class {previous if previous is not None else '?'} -> {read_back}",
    )


def undo(store: object, character_id: int, previous: int | None):
    """A zero-argument callable that puts the class back, or `None`.

    `None` when there is nothing to undo TO (`previous is None`), which the
    caller must not confuse with "the undo ran and failed" -- the dispatch's
    own audit distinguishes those two and this returns the FIRST of them by
    being absent rather than by returning a callable that lies about
    succeeding.

    WHY `/job` NEEDS ONE: `_make_action`'s rule is that no durable effect
    survives a failure to record it in the audit, and this command has
    durable state (`/speed` grew one for the same reason, pf-adversary round
    `hw6dix`).
    """
    if previous is None:
        return None

    def _restore() -> bool:
        return write_class_id(store, character_id, previous).ok

    return _restore


def _ascii_only(line: str) -> str:
    """Printable ASCII, with everything else replaced by `?`.

    ENFORCED, not asserted -- the bridge console is cp874 and a byte outside
    it kills the tool reading the line, not just the line.  `{args!r}` and a
    store exception's message are both reachable carriers of foreign text on
    this module's refusal paths (pf-adversary round `l86bt4`, D11, on the
    identical `/lv` line).
    """
    return "".join(c if 32 <= ord(c) < 127 else "?" for c in line)


#: The console token PANYA-ORDER section 2.2 asks for by name.  A COUNTABLE
#: line: the owner's `HEADLESS_PROOF:` block greps for it, so its shape is
#: an interface, not a log message, and `tests/test_gm_job_command.py` pins
#: every field name below.
CONSOLE_TOKEN = "GM_JOB"


def console_line(result: JobWrite, character_id: object) -> str:
    """One ASCII line for the SERVER HOST's console.  Never the player's screen.

    `GM_JOB cid=<n> class_id_from=<a> class_id_to=<b> relog_required=<yes|no>`,
    the shape PANYA-ORDER 2026-09-08 section 2.2 spells.

    `relog_required` IS ALWAYS `yes` ON THE SUCCESS PATH, and it is measured
    rather than assumed: this command sends no frame at all, and the only
    place `class_id` reaches a client is the login actor
    (`legacy_bridge.start_game`, `u32tag(0x19, class_id)`).  The owner's own
    order says to write that plainly in the result so the tester relogs
    instead of grading the command broken.  `class_id_from=none` is a row
    whose column was NULL (the ordinary state of a row created before the
    class seam) -- not an error, and not `0`, which is a class id nobody has.
    """
    if result.ok:
        previous = "none" if result.previous is None else str(result.previous)
        return _ascii_only(
            f"{CONSOLE_TOKEN} cid={character_id} class_id_from={previous} "
            f"class_id_to={result.written} relog_required=yes "
            "(row written; the next login for this character sends it; "
            "no attribute frame was sent to the live client)"
        )
    return _ascii_only(
        f"{CONSOLE_TOKEN} REFUSED [{result.refusal}]: {result.detail}"
    )
