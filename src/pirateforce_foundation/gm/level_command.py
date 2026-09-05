"""GM `/lv <n>`: set the selected character's stored level.  DB ONLY.

PANYA-ORDER 2026-09-06 01:55 (`pf_bridge/notes_to_chief/20260906_0155_PANYA-
ORDER-LANE-GM-slash-lv-set-character-level-first-job-deadline-1400.md`): a GM
types `/lv <n>` and the character's level really changes -- on screen, and
surviving a relog -- because LANE-CS cannot test a level-gated attack skill
without it.

WHAT THIS MODULE DOES, AND THE HALF IT REFUSES TO DO.

  * IT WRITES `characters.level` through LANE-DB's own existing door,
    `store.write_typed_attributes(character_id, {"level": n})`
    (`store.py`, LANE-DB charter `COO-DECISION 20260901_1100`).  No new store
    method is asked for and none is added -- the column already exists
    (`migrations/006_character_typed_attribute_columns.sql:130`) and the
    writer already validates it (`persistence_typed_attrs.validate`).
  * THE SCREEN HALF IT DELIVERS IS THE RELOG ONE, and it is a real one, not a
    consolation prize: the login path reads this exact column back
    (`store.read_character_vitals` -> `persistence_login_vitals.
    resolve_for_character` -> `apply_to_character`) and `legacy_bridge.
    start_game` puts it on the wire as the login vital `u16tag(0x12, level)`.
    So the next login after this write draws the new number.
  * IT SENDS NO ATTRIBUTE FRAME AND NO LEVEL FRAME -- it does send ONE chat
    notice back down the same socket (`say_wire.make_local_talk_notice_frame`,
    the 0xAC52 codec CHAT-ECHO-001/002 pinned), and the distinction is the
    whole safety argument rather than a quibble.  ~~"IT SENDS NO FRAME TO A
    LIVE CLIENT"~~ -- struck: pf-adversary (round `l86bt4`, D3) measured that
    sentence false against this module's own dispatch, and it is the sentence
    a reviewer would have trusted when deciding the command is safe.  The
    frame that would change a level
    mid-session is `UpdateAttrVital` (0x309A) with BasicAttr bit 0x0002
    (`gm/attr_wire.py:424`, x=2, tag 0x12, u16, `GetLv`; RE-117).  A SPARSE
    0x309A killed a real client in one frame during `GT-193`/`GT-218` -- the
    client's apply is a full-object copy (`RE-222` Q0, `ActorAttr::full copy
    [0x00464F30,0x004652AC)`), so every mask bit this lane leaves unset
    becomes a ZERO on the client, HP included.  `gm/attr_wire.py`'s (b'')
    rule therefore forbids every partial block through its named-field door,
    and this module does not reach for it, does not import it, and must
    never be edited into a second sparse sender.  The live-update half is an
    RE question (this round's `RE` letter), not a guess this module makes.

WHY IT ALSO REFUSES THE CANONICAL DATABASE.  `AGENTS.md` section 7: `ห้ามแตะ
canonical DB ตัวจริง` -- `state/pirateforce.sqlite3`.  This command WRITES a
row, so that rule is load-bearing for it exactly as it is for `/speed`
(`gm/chat_command_action.py`'s `CANONICAL_DB_FILENAME` gate).  The gate is
shared rather than re-implemented here, and it fails CLOSED: a store path
this lane cannot read counts as canonical and the write is refused.  The
owner's own requirement survives the gate untouched -- an attended boot runs
a timestamped run-copy DB, and a relog INSIDE that boot reads back the row
this command wrote.

MULTIPLAYER (`AGENTS.md` section 7 first line).  This command names its row by the
`characters.id` of the character selected ON THE CONNECTION WHOSE FRAME IS
BEING ANSWERED, never by an id handed in from anywhere.  Two GMs on two
sessions typing `/lv` in the same scene write two different rows; nothing
here is process-global and nothing here is per-scene, so `TWO_SESSIONS_SAME_
SCENE` is answered by construction rather than by a test double.

NOT AN M-ANYTHING.  A level set by a GM is a way to REACH a testable state,
never evidence that levelling works (`prompts/LANE-GM.md`, sentence 3).  Any
ticket that uses `/lv` to arrive somewhere has to say so in its nonclaims.
"""
from __future__ import annotations

from dataclasses import dataclass

from .. import persistence_standard_status as _standard_status
from .. import persistence_typed_attrs as _typed_attrs


#: The wire field this command writes: BasicAttr bit 0x0002, tag 0x12, u16
#: (`gm/attr_wire.py:424`, RE-117).  Spelled as the FIELD NUMBER and resolved
#: to a column name through LANE-DB's own map, so a column rename in their
#: zone cannot leave this module writing a stale string.
LEVEL_FIELD_X = 2

#: `level = 0` is storable (migration 006's CHECK is `BETWEEN 0 AND 65535`)
#: but it is NOT an adjudicated level: `store.read_character_vitals` returns a
#: `level_zero_is_not_an_adjudicated_level` gap for such a row, which makes
#: the LOGIN fall back to the composer's constant instead of the row -- i.e.
#: `/lv 0` would look like it did nothing after a relog, and would leave a row
#: the vitals gate refuses.  So the floor is the committed table's own first
#: row, which is 1, and never the schema's 0.
MIN_LEVEL = _standard_status.STANDARD_STATUS_MIN_LEVEL

#: THE CEILING IS THE CLIENT'S TABLE, NOT THE COLUMN'S WIDTH, and the first
#: draft of this module had it wrong in the dangerous direction (65535, the
#: u16 storage maximum).  pf-adversary (round `l86bt4`, D5) measured what
#: that would have handed an attended tester:
#:
#:   * `data/standard_status.tsv` is the client's own sha-pinned
#:     `CONSTDATA_TH__STANDARD_STATUS`, and it holds rows 1..255 and nothing
#:     above -- three other modules in this repository already refuse a level
#:     outside 1..255 by that table (`persistence_standard_status.py`,
#:     `field_mobs.py`, `scene2_prison_exile_tables.py`);
#:   * the client's XP bar (`0x519299`) DIVIDES displayed experience by
#:     `STANDARD_STATUS[level + 1].n_EXP_CURRENTLV` -- so the row the client
#:     reaches for is the one ABOVE the level it is drawing.
#:
#: Hence `- 1`: at the table's last row the `level + 1` lookup has no row at
#: all, and this lane has no business finding out what the client does then
#: on the owner's own machine -- `/warp <x> <y>` (`1744`) and a sparse
#: `0x309A` (`GT-193`) are what "find out on a live client" has cost here
#: twice already.  A `/lv 255` refused is a tester typing `/lv 254`; a
#: `/lv 255` accepted is a client nobody promised would survive it.
#: [สมมติของสาย GM - รอ COO ยืนยัน]: nothing in this repository MEASURES the
#: 255 case; the `- 1` is this lane's own reading of a divisor it can see.
LEVEL_CEILING_MARGIN = 1

#: Refusal reasons.  Strings, because they are written into the audit row and
#: read by a human on a console line; each one names WHAT was wrong, never
#: "failed".  NONE of them repeats the command name: the dispatch prefixes
#: them with `refused_lv_` / `gm_chat_action_lv_refused_`, and a value that
#: also said `lv_` would stutter in every audit row a tester greps.
REFUSED_ARGS_SHAPE = "args_not_a_one_string_tuple"
REFUSED_NOT_AN_INTEGER = "argument_not_an_integer"
REFUSED_OUT_OF_RANGE = "out_of_range"
REFUSED_NO_CHARACTER = "no_selected_character"
REFUSED_NO_STORE = "no_store_on_this_session"
REFUSED_CANONICAL_DB = "canonical_db"
REFUSED_ROW_MISSING = "row_not_found"
REFUSED_WRITE_FAILED = "write_failed"
REFUSED_READBACK_MISMATCH = "readback_did_not_hold_the_value"
#: THE ROW MOVED AND THE LOGIN STILL WILL NOT SEND IT.  pf-adversary (round
#: `l86bt4`, D1) measured the state that makes this reachable: the login's
#: vitals gate is ALL THREE OR NONE (`PANYA-DECISION 20260901_1059`), so a
#: row whose `hp_current`/`hp_max` do not resolve (`hp_max IS NULL`,
#: `hp_current > hp_max`, `hp_max = 0`) comes back
#: `row_refused_by_vitals_gate` with EMPTY wire kwargs -- and
#: `legacy_bridge.start_game` then sends `player_wire.PLAYER_LOGIN_LEVEL`,
#: which is 1.  The row said 50 and the screen said 1, and the only trace was
#: a `LOGIN_VITALS` line on the server console one login later.  This command
#: holds the store, so it asks instead of claiming.
REFUSED_LOGIN_WOULD_NOT_SEND = "login_would_not_send_it"
#: The repair after one of the two refusals above put a value on disk that
#: this command will not stand behind.  A SEPARATE word from the refusal it
#: follows, because "the row was put back" and "the row is still carrying it"
#: are different states for the tester and only one of them is safe to walk
#: away from.
REPAIRED_SUFFIX = "_row_put_back"
REPAIR_FAILED_SUFFIX = "_row_still_carries_it"


class LevelArgumentError(ValueError):
    """`/lv`'s argument is not a level this module will write."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def level_column() -> str:
    """The `characters` column this command writes (`level`)."""
    return _typed_attrs.column_for(LEVEL_FIELD_X)


def storage_ceiling() -> int:
    """What the COLUMN could hold: 65535 today (u16).

    Read from LANE-DB's own typed-column table rather than retyped, so a
    storage-rule change in their zone moves with it.  NOT the command's
    ceiling -- see `max_level`, and see `LEVEL_CEILING_MARGIN` for the
    measurement that separates the two.
    """
    return int(_typed_attrs.TYPED_COLUMNS[level_column()].maximum)


def max_level() -> int:
    """The highest level this command will write: 254 today.

    The client's own committed table stops at 255 and its XP bar reads the
    `level + 1` row, so the last row is left alone (`LEVEL_CEILING_MARGIN`).
    `min` with the column's own width is not belt-and-braces: if LANE-DB ever
    narrows the storage rule below the table, the column wins, because a
    value the column refuses is a write that fails in front of a tester.
    """
    return min(
        _standard_status.STANDARD_STATUS_MAX_LEVEL - LEVEL_CEILING_MARGIN,
        storage_ceiling(),
    )


def usage() -> str:
    """The one sentence a human gets back for a bad argument."""
    return f"lv <n>, {MIN_LEVEL}..{max_level()}"


def parse_level(args: object) -> int:
    """`args` (a `GmCommand.args`) -> the level to write, or raise.

    `commands.parse_gm_command` has already checked that `lv` carries exactly
    one integer-looking token, so this is the SECOND check, deliberately:
    `GmCommand` is a plain dataclass and `gm/commands.py`'s own
    `GmCommandArgsError` docstring records the pf-adversary history of
    hand-built `args` values (an integer-keyed dict, a tuple subclass lying
    through `__len__`/`__getitem__`) defeating a shape check one layer up.
    A module that writes a database row does not inherit another module's
    validation; it repeats it.

    `type(args) is not tuple` rather than `isinstance`, for the tuple-subclass
    reason above.  `bool` is excluded from the parsed value for free: this
    parses from TEXT, and `bool` never comes out of `int(str)`.
    """
    if type(args) is not tuple or len(args) != 1 or type(args[0]) is not str:
        raise LevelArgumentError(
            REFUSED_ARGS_SHAPE,
            f"lv takes exactly one string argument; got {args!r}",
        )
    text = args[0].strip()
    try:
        level = int(text, 10)
    except ValueError:
        raise LevelArgumentError(
            REFUSED_NOT_AN_INTEGER, f"{text!r} is not a whole number; {usage()}"
        ) from None
    ceiling = max_level()
    if level < MIN_LEVEL or level > ceiling:
        raise LevelArgumentError(
            REFUSED_OUT_OF_RANGE,
            f"level {level} is outside {MIN_LEVEL}..{ceiling}; {usage()}",
        )
    return level


@dataclass(frozen=True)
class LevelWrite:
    """What one `/lv` did, in the shape the console line and the audit read.

    `written` is the value the STORE READ BACK, never the number the GM
    typed -- the two differ exactly when something between them changed the
    value, which is the case a `/lv` that "looked fine" must not hide.
    `previous` is `None` when the row's level could not be read beforehand
    (an unseeded row, a vitals gap); that is not a refusal, it only means
    there is nothing to undo TO.
    """

    written: int | None
    previous: int | None
    refusal: str | None
    detail: str

    @property
    def ok(self) -> bool:
        return self.refusal is None


def _previous_level(store: object, character_id: int) -> int | None:
    """The row's current level, or `None` for "could not be read".

    THE COLUMN, NOT THE VITALS GATE, and the difference is the whole point.
    An earlier draft read `store.read_character_vitals_or_none`, and
    pf-adversary (round `l86bt4`, D7) measured what that cost: that door
    returns `None` for ANY incomplete resolution -- a bad HP pair, not a
    missing level -- so on exactly the rows this command is most likely to
    have to put back, the previous level read as "unreadable" and the undo
    came out `None`.  `read_typed_attributes` answers about the COLUMN, which
    is the thing being restored.

    Never raises: a failure to read the OLD value must not stop the new one
    being written -- the owner asked for the level to change, not for a
    perfect audit of what it was.
    """
    reader = getattr(store, "read_typed_attributes", None)
    if reader is None:
        return None
    try:
        stored = reader(character_id)
        level = stored[level_column()]
    except Exception:  # noqa: BLE001 -- see the docstring (KeyError included:
        # the column is OMITTED when NULL, which is "never written", not an
        # error)
        return None
    if type(level) is not int or isinstance(level, bool):
        return None
    return level


def login_would_send(store: object, character_id: int, level: int) -> bool:
    """Would the NEXT LOGIN really put `level` on the wire for this row?

    ASKED OF THE LOGIN'S OWN DOOR, `store.read_character_vitals_or_none` --
    the read `persistence_login_vitals.resolve_for_character` makes and the
    one whose gaps decide whether `legacy_bridge.start_game` sends the row's
    numbers or `player_wire`'s constants.  This is deliberately the door
    `_previous_level` above stopped using: there it was the wrong question,
    here it is exactly the right one.

    WHY THIS FUNCTION EXISTS (pf-adversary, round `l86bt4`, D1, MEASURED):
    the gate is ALL THREE OR NONE (`PANYA-DECISION 20260901_1059`).  A row
    with `hp_max IS NULL`, `hp_current > hp_max` or `hp_max = 0` resolves
    `row_refused_by_vitals_gate` with EMPTY wire kwargs, and the login then
    sends `PLAYER_LOGIN_LEVEL`, which is 1.  So a `/lv 50` on such a row
    wrote 50, said `LV SET RELOG`, and the relog drew 1.  The command holds
    the store; it can ask rather than promise.

    Unanswerable -> `False`, never `True`: this gates a CLAIM about a screen,
    and "cannot tell" may not be reported as "yes".
    """
    reader = getattr(store, "read_character_vitals_or_none", None)
    if reader is None:
        return False
    try:
        vitals = reader(character_id)
    except Exception:  # noqa: BLE001 -- cannot ask => cannot claim
        return False
    return getattr(vitals, "level", None) == level


def _repair(store: object, character_id: int, previous: int | None) -> str:
    """Put `previous` back after a write this command will not stand behind.

    Returns the suffix the caller appends to its refusal reason, so the audit
    row and the console line say WHICH of the two durable states the tester
    is walking away from.  `""` when there was nothing to put back -- the row
    held no level before, so leaving it is not the same defect as leaving a
    number that overwrote a real one.
    """
    if previous is None:
        return ""
    writer = getattr(store, "write_typed_attributes", None)
    if writer is None:
        return REPAIR_FAILED_SUFFIX
    try:
        writer(character_id, {level_column(): previous})
    except Exception:  # noqa: BLE001 -- the repair may not raise either
        return REPAIR_FAILED_SUFFIX
    return REPAIRED_SUFFIX


def write_level(store: object, character_id: object, level: int) -> LevelWrite:
    """Write `level` onto `character_id`'s row.  Never raises.

    THE ORDER IS: read the old value (best effort) -> write -> check the
    read-back.  The read-back check is not ceremony: `write_typed_attributes`
    returns the row's typed columns AFTER the write, so a value that came
    back different from the one asked for means something between this module
    and the disk changed it, and reporting success on that would be the exact
    shape of lie this house's evidence rules exist to stop.

    EVERY failure comes back as a refusal object with a NAMED reason, because
    this is called from a chat dispatch whose own module docstring records
    what an escaping exception costs there: `runtime.py`'s handler catches
    only four types and `v141` wraps the connection loop with no `except` at
    all, so an escaping `TypeError` unwinds the listener thread and parks the
    client on "connecting".
    """
    if type(character_id) is not int or isinstance(character_id, bool) or character_id <= 0:
        return LevelWrite(
            None, None, REFUSED_NO_CHARACTER,
            f"no usable selected character id on this connection ({character_id!r})",
        )
    writer = getattr(store, "write_typed_attributes", None)
    if writer is None:
        return LevelWrite(
            None, None, REFUSED_NO_STORE,
            "this session's store has no write_typed_attributes door",
        )
    column = level_column()
    previous = _previous_level(store, character_id)
    try:
        after = writer(character_id, {column: level})
    except KeyError:
        return LevelWrite(
            None, previous, REFUSED_ROW_MISSING,
            f"character {character_id} has no live row to write",
        )
    except Exception as error:  # noqa: BLE001 -- named, never escaping
        return LevelWrite(
            None, previous, REFUSED_WRITE_FAILED,
            f"{type(error).__name__}: {error}",
        )
    read_back = None
    try:
        read_back = after[column]
    except Exception:  # noqa: BLE001 -- a store that returned another shape
        read_back = None
    if type(read_back) is not int or isinstance(read_back, bool) or read_back != level:
        # REPAIRED HERE, NOW, not handed up as an `undo` for the dispatch to
        # run.  pf-adversary (round `l86bt4`, D6) measured why: the dispatch
        # runs a verdict's undo ONLY when the audit row could not be written
        # (`chat_command_action._make_action`), so an undo attached to this
        # branch never ran on the ordinary path -- three of this lane's own
        # artifacts said three different things about a row nobody put back.
        repair = _repair(store, character_id, previous)
        return LevelWrite(
            level, previous, f"{REFUSED_READBACK_MISMATCH}{repair}",
            f"asked for level {level}, the row read back {read_back!r}",
        )
    if not login_would_send(store, character_id, level):
        # THE ROW MOVED AND THE SCREEN WILL NOT.  Put it back and say so:
        # this command's whole product is a level the next login draws, and a
        # row that survives while the claim does not is worse than a refusal
        # -- the tester would relog, read 1, and grade the command broken
        # while the database quietly disagreed with the screen.
        repair = _repair(store, character_id, previous)
        return LevelWrite(
            level, previous, f"{REFUSED_LOGIN_WOULD_NOT_SEND}{repair}",
            f"the row took level {level}, but this character's login vitals "
            "do not resolve (all three or none), so the next login would "
            "send the composer's constant instead -- fix hp_current/hp_max "
            "for this row first",
        )
    return LevelWrite(
        read_back, previous, None,
        f"level {previous if previous is not None else '?'} -> {read_back}",
    )


def undo(store: object, character_id: int, previous: int | None):
    """A zero-argument callable that puts the level back, or `None`.

    `None` when there is nothing to undo TO (`previous is None`), which the
    caller must not confuse with "the undo ran and failed" -- the dispatch's
    own audit distinguishes those two and this returns the FIRST of them by
    being absent rather than by returning a callable that lies about
    succeeding.

    WHY `/lv` NEEDS ONE AT ALL: the same reason `/speed` grew one
    (`gm/chat_command_action.py::_speed_undo`, pf-adversary round `hw6dix`).
    This command has durable state, and `_make_action`'s rule is that no
    effect survives a failure to record it in the audit.
    """
    if previous is None:
        return None

    def _restore() -> bool:
        result = write_level(store, character_id, previous)
        return result.ok

    return _restore


def _ascii_only(line: str) -> str:
    """Printable ASCII, with everything else replaced by `?`.

    ENFORCED, not asserted.  pf-adversary (round `l86bt4`, D11) found the
    first draft of `console_line` claiming this in its docstring and not
    doing it, with two reachable carriers of foreign text (`{args!r}` and a
    store exception's message).  This is the same filter
    `persistence_login_vitals.console_line` ends with, for the same reason:
    the bridge console is cp874 and a byte outside it kills the tool reading
    the line, not just the line.
    """
    return "".join(c if 32 <= ord(c) < 127 else "?" for c in line)


def console_line(result: LevelWrite, character_id: object) -> str:
    """One ASCII line for the SERVER HOST's console.  Never the player's screen.

    The success wording says RELOG and says no level frame was sent, because
    both halves are what the tester has to know: the row is the effect, and
    the screen does not move until the next login.
    """
    if result.ok:
        return _ascii_only(
            f"GM LV: character {character_id} level -> {result.written} "
            "(row written; the next login for this character sends it; "
            "no attribute frame was sent to the live client)"
        )
    return _ascii_only(f"GM LV REFUSED [{result.refusal}]: {result.detail}")
