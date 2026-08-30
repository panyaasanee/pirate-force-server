"""GM-003 v1: server-side GM command grammar -- PARSE AND LOG ONLY.

Scope of this file, stated plainly so it cannot be over-claimed later:

* It parses the six command strings the owner asked for (``warp`` ``npc``
  ``item`` ``lv`` ``spawn`` ``say``) into a structured ``GmCommand``.
* It logs an issued command server-side (``log_gm_command``).
* It does **not** execute any of them.  RE-090 (PASS/DONE) has since pinned
  ``ForcePos``'s byte layout in full with zero unproven fields
  (``gm/teleport_wire.py``), and ``gm/warp_executor.py`` (CORE-REQUEST-011)
  bridges the same-scene case of a parsed ``warp`` command into a real
  outbound ``ForcePos`` frame -- but that is still not execution: it
  returns frame bytes, it does not send them, and it does not cover the
  scene-crossing case (that needs ``TeleportVital``, whose ``target``/
  ``aux`` sub-objects still carry several positional-only fields RE-090
  leaves unproven -- see ``gm/warp_executor.py``'s own docstring for which
  ones and why guessing them is refused rather than attempted).  ``spawn``
  still needs mob-spawn wiring that is not proven yet (notes_to_chief
  20260826_1630 lists this as RE-open); executing ``npc``/``item``/``lv``
  needs write access to player/world state that lives in runtime.py,
  outside this lane's write zone.  Wiring any of that in is a
  CORE-REQUEST to chief, filed per command once its dependency is ready --
  see docs/GM_LANE.md.
* ``GM_RunGMCommandVital`` (0x51E9, client->server) is how a real client
  would deliver this text.  A structural candidate byte layout for it is now
  proven (see ``gm/command_capture.py`` for the pin), but the two
  wide-string fields it carries are not yet confirmed to be "command name"
  and "raw text" -- that mapping is RE-request territory, not something
  this module assumes.  This module therefore takes a plain ``str`` and
  does not depend on 0x51E9 at all, so command parsing/logging can be
  exercised and tested independently of how that mapping resolves.

``warp``'s scene_id is checked against ``gm.scene_catalog`` (GM-004, this
lane's own committed catalog) only to flag a scene_id that has no known GM
name -- it is a hint for the log, not a hard rule, because a scene_id
missing from the catalog is not proof that warping there is invalid.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
import time
import uuid
from pathlib import Path

from . import npc_switch_catalog
from . import scene_catalog

# The grammar, spelled ONCE.  Every usage sentence this lane shows a human
# is a value here, and `parse_gm_command` raises those same values rather
# than re-typing them -- so a grammar change cannot leave the parser saying
# one thing and the way-out line saying another.
#
# ORDER IS OPERATOR-VISIBLE, and pinned by a test that says so.  It reaches
# a human twice: `unknown GM command 'x'; expected one of (...)` and the
# joined vocabulary `usage_hint_for` returns for an unknown verb.
# pf-adversary (round `9wy444`, D9) reversed this dict and the WHOLE SUITE
# stayed green -- `test_gm_standalone_map_is_not_chat_writable.py` compares
# SETS, so it never saw the order at all.  An earlier version of this
# comment claimed that file pinned the tuple; it does not.  The pin is
# `test_gm_chat_command_parse_way_out.py::TheDescriberItselfTests::
# test_the_vocabulary_order_is_pinned_because_a_human_reads_it`.
COMMAND_USAGE = {
    "warp": "warp <scene_id> [x y]",
    "npc": "npc on|off <mob_id>",
    "item": "item <id> <n>",
    "lv": "lv <n>",
    "spawn": "spawn <mob_id>",
    "say": "say <message>",
}

COMMAND_NAMES = tuple(COMMAND_USAGE)

DEFAULT_LOG_PATH = "capture/gm_command_log.ndjson"

# Channel_GMGlobalMessageVital (0x9F2C) is a global broadcast, not a private
# chat line -- capping this keeps a fat-fingered or hostile "say" from
# growing without bound once execution is wired in, and keeps each logged
# record to roughly one write() call worth of bytes.
MAX_SAY_MESSAGE_LENGTH = 480


# ---------------------------------------------------------------------------
# AUDIT VOCABULARY (CORE-REQUEST-GM-032 items 1-2)
#
# ~~One GM command writes up to two rows~~ -- up to THREE since
# CORE-REQUEST-GM-040 (2026-08-30) -- in `DEFAULT_LOG_PATH`, distinguished
# by the `record` field and tied together by `record_id`:
#
#   issued  -- a GM account typed a line, it parses, here it is.  Written by
#              `log_gm_command` BEFORE any gate is read.
#   outcome -- what this lane then did with it.  Written by
#              `log_gm_command_outcome` AFTER the gates and the composer had
#              their say.
#   outcome -- (SECOND one, `outcome: "queued"`, only when the action really
#              reached runtime.py's action list) written by
#              `log_gm_command_queued` from the append-site confirmation
#              callback chief wired for CORE-REQUEST-GM-040.
#
# !! A READER OF THIS FILE MUST TAKE THE **LAST** OUTCOME ROW FOR A
# `record_id`, NOT "THE" OUTCOME ROW.  `GT-127`/`GT-141` grade on this file
# and their old greps assume one outcome row per issued row; a composed-then-
# appended command now writes `composed` and then `queued`, in that order,
# and reading the first one back would report a command as less far along
# than it got.  Append-only, never an amend: the second line does not
# replace the first, it extends the sequence.
#
# Why the second row is not optional: COO-DECISION 20260829_0041 measured
# that the issued row alone cannot answer the question GT-127 asks it.  With
# both version gates shut, `/warp 2 100 200` produced exactly the row it
# would produce on the day the gate opens and a real frame goes out.
AUDIT_RECORD_ISSUED = "issued"
AUDIT_RECORD_OUTCOME = "outcome"

# !! THERE IS A THIRD FILE STATE AND A READER HAS TO BE TOLD ABOUT IT.
# pf-adversary's closing question, and it is the right one: an `issued` row
# with NO `outcome` row after it. Four ways to reach it, and they are not the
# same event -- the outcome write failed (`gm_chat_action_outcome_log_failed_
# <Type>`), the module raised before the write point
# (`gm_chat_action_unexpected_<Type>`), the issued row handed back no id
# (`gm_chat_action_outcome_no_record_id`), or the process died between the two
# appends (no console line at all, because nothing was alive to print one).
#
# What a reader may conclude from a half-pair: NOTHING WAS SENT. Every path
# above ends with the action withheld -- `_make_action` returns the action
# only after the outcome row is on disk. What a reader may NOT conclude is
# which of the four happened; that is on stderr, not in the file.
#
# !! ONE THING A HALF-PAIR NO LONGER RULES OUT, as of the cross-scene `/warp`
# (round `gejldf`): that nothing at all HAPPENED. "Nothing was sent" is still
# exact -- no byte leaves this lane either way -- but a `/warp` to another
# scene writes `config/gm_login_scene.json` BEFORE the outcome row, and only
# three of the four half-pair paths take it back off (`_make_action` runs the
# undo when the write fails; a process that dies between the two appends runs
# nothing at all, and an undo can itself fail, which is what
# `gm_chat_action_outcome_stage_not_reverted` on stderr says).  A reader who
# finds an `issued` row for a `warp` with no `outcome` row has to CHECK THAT
# CONFIG FILE before concluding the command left no trace. Said here
# because "two rows so the file stops having one meaning for two states" is
# only honest if the third state is named too. The "nothing was sent" half is
# pinned as behaviour, not as a constant nothing reads:
# `tests/test_gm_command_audit_outcome.py::HalfPairTests`.

AUDIT_OUTCOME_NOTE = (
    "CORE-REQUEST-GM-032: what this lane did with the command named by "
    "record_id; not a claim about what the runtime or the client did"
)

# A frame was composed and handed back to the caller.  This is the STRONGEST
# thing this lane can honestly write, and it is deliberately not "sent" and
# not "queued": `make_gm_chat_command_action` returns an action tuple to
# `runtime.py`, and whether that tuple is appended to the action list --
# `actions = actions + [gm_action]`, runtime.py:5763 -- happens in a zone
# this lane cannot read back.
OUTCOME_COMPOSED = "composed"

# ~~RESERVED, AND UNREACHABLE ON PURPOSE.~~  SUPERSEDED 2026-08-30 by
# CORE-REQUEST-GM-040 (LANE-GM round `dm8o4l`); the paragraph below is kept
# because it is the reason the door is shaped the way it now is.
#
# ~~`queued` is the word CORE-REQUEST-
# GM-032 item 3 asks chief for: it may only be written once the append site
# reports back (a callback handed out with the action, or anything else this
# lane can read).  No code path passes it today, and
# `tests/test_gm_command_audit_outcome.py` fails if one starts to without
# that confirmation arriving -- i.e. the day someone makes this reachable,
# they have to delete a test that says why they may not.~~  A token that
# claims more than it measured is the failure COO-DECISION 20260829_0141
# item 3 made a standing pf-adversary check.
#
# WHAT IS TRUE NOW: the append site DOES report back.  Chief wired it at
# `runtime.py`'s `actions = actions + [gm_action]` (CORE-REQUEST-GM-040,
# merged 2026-08-30T10:47Z) as a `(action, callback)` pair matched by `is`,
# and `chat_command_action.py` arms that pair with the exact object it is
# about to return.  So the word is now writable -- BY ONE FUNCTION ONLY,
# `log_gm_command_queued` below, which takes no `outcome` parameter and
# hard-codes this constant.
#
# THE THREE OLD PINS DID NOT MOVE, and that is the point: `queued` is still
# NOT in `AUDIT_OUTCOMES`, `is_known_outcome('queued')` is still False, and
# `log_gm_command_outcome` still raises for it by every spelling including
# the tuple-index route pf-adversary used.  Nothing was relaxed; a second,
# narrower door was cut, and no test that guarded the first one was deleted
# to do it.
OUTCOME_QUEUED = "queued"

# `withheld_` = the command was valid and authorized, and this lane chose to
# put nothing on the wire; the suffix names the shut gate.
# `refused_` = the command could not be turned into a frame; the suffix names
# the reason (an exception TYPE name, never a message -- messages embed the
# GM's typed text).
OUTCOME_WITHHELD_PREFIX = "withheld_"
OUTCOME_REFUSED_PREFIX = "refused_"

# !! `OUTCOME_QUEUED` IS NOT IN THIS TUPLE, AND THAT IS THE ENFORCEMENT.
# pf-adversary (this round) wrote a function into `lane_hooks/lane_gm_chat_
# command.py` that passed `AUDIT_OUTCOMES[-1]` straight through to
# `log_gm_command_outcome`, and the word `queued` landed in the ndjson file
# with all 519 GM tests green: the source scan in
# `tests/test_gm_command_audit_outcome.py` matches names and literals, so a
# tuple index walks past it untouched. A source-shaped scan cannot make an
# output-shaped guarantee. The writer itself now refuses the word -- the scan
# stays as the early warning, this is the door.
# A cross-scene `/warp` (and the bare `warp <scene_id>` form, which carries no
# position for ForcePos either) writes the account's next-login scene into
# `config/gm_login_scene.json` -- `gm/login_scene_stage.py`.  It is the only
# outcome in this vocabulary that names a REAL, DURABLE effect, and it is
# still not a claim that anything moved: no frame was composed, no byte was
# put on the wire, and nothing at all happens until that GM logs out and back
# in.  The word says exactly that and no more.  `executed` stays False in the
# row for the same reason -- the gameplay command did not execute, a config
# entry was written.
#
# The `_coords_ignored` variant exists because `/warp 126 100 200` cannot do
# what it says: the login path spawns at the scene's own registry entry point
# (lane A's `world_scene_travel`), so the two numbers the GM typed are
# dropped.  One word that covered both cases would let a tester read the file
# and believe their coordinates were honoured somewhere.
OUTCOME_STAGED_LOGIN_SCENE = "staged_login_scene"
OUTCOME_STAGED_LOGIN_SCENE_COORDS_IGNORED = "staged_login_scene_coords_ignored"

AUDIT_OUTCOMES = (
    OUTCOME_COMPOSED,
    OUTCOME_STAGED_LOGIN_SCENE,
    OUTCOME_STAGED_LOGIN_SCENE_COORDS_IGNORED,
)
AUDIT_OUTCOME_PREFIXES = (OUTCOME_WITHHELD_PREFIX, OUTCOME_REFUSED_PREFIX)


@dataclass(frozen=True)
class GmCommand:
    name: str
    args: tuple[str, ...]
    raw: str


class GmCommandParseError(ValueError):
    pass


class GmCommandArgsError(ValueError):
    """A `GmCommand.args` value does not have the shape this module requires.

    `GmCommand` is a plain frozen dataclass (see above) -- nothing stops a
    caller from hand-building one with an `args` value that is not a real
    `tuple[str, ...]`, the same "regardless of source" threat model
    `gm/warp_executor.py` and `gm/say_wire.py` already defend against for
    their own `GmCommand` inputs (see their own `type(args) is not tuple`
    checks and docstrings for the pf-adversary history: a blacklist of
    individually-discovered wrong shapes was defeated by an integer-keyed
    dict, then an `isinstance(args, tuple)` allowlist was defeated by a
    tuple *subclass* lying through `__len__`/`__getitem__`). This module's
    own `describe_warp_target`/`describe_npc_target`/`log_gm_command` used
    to skip that check entirely -- an integer-keyed dict silently logged its
    *keys* as `args` instead of raising, and `None` raised a bare
    `TypeError` instead of a module-specific error a caller could catch.
    """


def parse_gm_command(text: str) -> GmCommand:
    """Parse one line of GM chat/command text into a GmCommand.

    Grammar (owner's spec, notes_to_chief 20260826_1630 section GM-003):
      warp <scene_id> [x y]
      npc on|off <mob_id>
      item <id> <n>
      lv <n>
      spawn <mob_id>
      say <message...>
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    stripped = text.strip()
    if not stripped:
        raise GmCommandParseError("empty command")
    parts = stripped.split(maxsplit=1)
    name = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""

    if name == "warp":
        args = rest.split()
        if len(args) not in (1, 3):
            raise GmCommandParseError(COMMAND_USAGE["warp"])
        _require_int(args[0], "scene_id")
        if len(args) == 3:
            _require_number(args[1], "x")
            _require_number(args[2], "y")
        return GmCommand(name, tuple(args), stripped)

    if name == "npc":
        args = rest.split()
        if len(args) != 2 or args[0] not in ("on", "off"):
            raise GmCommandParseError(COMMAND_USAGE["npc"])
        _require_int(args[1], "mob_id")
        return GmCommand(name, tuple(args), stripped)

    if name == "item":
        args = rest.split()
        if len(args) != 2:
            raise GmCommandParseError(COMMAND_USAGE["item"])
        _require_int(args[0], "id")
        _require_int(args[1], "n")
        return GmCommand(name, tuple(args), stripped)

    if name == "lv":
        args = rest.split()
        if len(args) != 1:
            raise GmCommandParseError(COMMAND_USAGE["lv"])
        _require_int(args[0], "n")
        return GmCommand(name, tuple(args), stripped)

    if name == "spawn":
        args = rest.split()
        if len(args) != 1:
            raise GmCommandParseError(COMMAND_USAGE["spawn"])
        _require_int(args[0], "mob_id")
        return GmCommand(name, tuple(args), stripped)

    if name == "say":
        if not rest:
            raise GmCommandParseError(COMMAND_USAGE["say"])
        if len(rest) > MAX_SAY_MESSAGE_LENGTH:
            raise GmCommandParseError(
                f"say message exceeds {MAX_SAY_MESSAGE_LENGTH} characters"
            )
        return GmCommand(name, (rest,), stripped)

    raise GmCommandParseError(
        f"unknown GM command {name!r}; expected one of {COMMAND_NAMES}"
    )


def usage_hint_for(body: str) -> str:
    """Name the grammar of the command that was typed, and NOTHING ELSE.

    D8, ruled on by COO-DECISION 20260829_1344: a refused `/warp 9999` named
    the scenes it would have accepted, but `/warp island` and a bare
    `/warp` printed nothing at all, because the refusal happens at the parse
    layer, upstream of every printer this lane owns.  This is the sentence
    that silence was missing.

    !! IT CONTAINS NO CLIENT BYTES, AND THAT IS THE WHOLE DESIGN.
    The first version of this function returned `str(error)`, which quotes
    what was typed (`scene_id must be an integer, got 'island'`).
    pf-adversary (round `9wy444`, D1) measured what that means on the WIRED
    server rather than in a test: `runtime.py:5140-5150` says it outright --
    `session.token` is the process-wide `--token` CLI value, not a
    per-connection authenticated login, so EVERY connection this listener
    accepts shares one identity.  On the only configuration where this
    feature ever fires (that one token listed in `gm_accounts.json`), any
    player typing `/warp <anything>` in local chat would have had their
    sentence printed to the operator's console, attributed to the operator's
    own GM account -- and `decode_local_talk_payload` throws the wire's
    `speaker` field away, so the line could not even have told the truth
    about who typed it.  This lane's founding rule is that a non-GM's chat
    is never decoded, pattern-matched, or written anywhere by it; until
    identity is per-connection (chief's zone: `runtime.py`,
    `pf_login_game_server_v141.py`), the only safe thing to print is text
    this lane wrote itself.

    So the return value is always one of exactly seven strings: one of the
    six `COMMAND_USAGE` sentences, or all six joined.  Which of the seven is
    the ONLY thing a typed line can influence here, and every one of them is
    this lane's own words.  That also bounds the line's width by
    construction rather than by a cap, and makes it encodable on any console
    that can carry ASCII -- the two other ways pf-adversary broke the
    echoing version (D2, D7).

    WHAT THE OPERATOR LOSES, said plainly rather than glossed: they no
    longer read the offending token back. What they keep is the half D8 was
    filed about -- that a command was refused at all, and what its grammar
    is. `got 'island'` was the nice-to-have; it was also the entire attack
    surface.

    `body` is the command WITHOUT the chat sigil -- the same string
    `parse_gm_command` was handed, so the verb read here is the verb that
    failed.  A caller holding a sigil-prefixed line uses
    `chat_command.command_body` rather than slicing it itself.
    """
    stripped = body.strip() if isinstance(body, str) else ""
    name = stripped.split(maxsplit=1)[0].lower() if stripped else ""
    usage = COMMAND_USAGE.get(name)
    if usage is None:
        # An unknown verb (and an empty line) asks "what CAN I type", not
        # "how do I spell what I just typed" -- so the answer is the whole
        # vocabulary.  It is also the answer that reveals nothing at all
        # about the line that prompted it.
        return " | ".join(COMMAND_USAGE.values())
    return usage


def _require_int(value: str, label: str) -> None:
    try:
        int(value)
    except ValueError as exc:
        raise GmCommandParseError(f"{label} must be an integer, got {value!r}") from exc


def _require_number(value: str, label: str) -> None:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise GmCommandParseError(f"{label} must be a number, got {value!r}") from exc
    if not math.isfinite(parsed):
        # A position field that silently accepts nan/inf is a landmine for
        # whoever wires real warp execution against this parser later --
        # reject it here so that check never has to be re-added downstream.
        raise GmCommandParseError(f"{label} must be finite, got {value!r}")


def _require_args_tuple(args: object, *, min_length: int) -> tuple[str, ...]:
    """Reject any `args` that is not a real `tuple` of at least `min_length`.

    `type(args) is not tuple`, not `isinstance` -- see `GmCommandArgsError`'s
    docstring for why an isinstance allowlist is not enough (a tuple
    subclass can lie through `__len__`/`__getitem__`).
    """
    if type(args) is not tuple:
        raise GmCommandArgsError(f"command args must be a tuple, got {args!r}")
    if len(args) < min_length:
        raise GmCommandArgsError(
            f"command args must have at least {min_length} element(s), got {args!r}"
        )
    return args


def _require_arg_int(value: str, label: str) -> int:
    """Parse one `GmCommand.args` element as int, or raise `GmCommandArgsError`.

    `describe_warp_target`/`describe_npc_target` accept a `GmCommand`
    "regardless of source" (see `GmCommandArgsError`'s docstring) -- a
    hand-built command whose `args` tuple has the right shape but a
    non-numeric element (e.g. `("abc",)`) must not raise a bare `ValueError`
    out of `int()`; that would break the same threat model `_require_args_tuple`
    exists to close, just one field deeper. `parse_gm_command`'s own
    `_require_int` already guarantees this for its own input path, so this is
    a separate check for callers that skip `parse_gm_command` entirely.
    """
    # Catches Exception broadly, not just TypeError/ValueError: a hand-built
    # element whose __int__ raises something else (AttributeError, KeyError,
    # a custom exception) would otherwise leak past this function's own
    # promised error type -- the same class of gap warp_executor.py's
    # identical helper closed.
    try:
        return int(value)
    except Exception as exc:
        raise GmCommandArgsError(f"{label} must be an integer, got {value!r}") from exc


def describe_warp_target(command: GmCommand) -> str | None:
    """The GM scene name for a parsed warp command's scene_id, or None if
    the id has no row in the GM-004 catalog -- a hint, not a validity gate.
    """
    if command.name != "warp":
        raise ValueError("describe_warp_target only applies to warp commands")
    args = _require_args_tuple(command.args, min_length=1)
    scene_id = _require_arg_int(args[0], "scene_id")
    if not scene_catalog.is_known_scene_id(scene_id):
        return None
    return scene_catalog.gm_scene_name(scene_id)


def describe_npc_target(command: GmCommand) -> str | None:
    """The client's own name for a parsed npc command's mob_id, or None if
    mob_id is not one of the 7 client-flagged (n_GM_SWITCH=1) NPCs -- a hint
    for the log, not a validity gate: a mob_id missing from this table is not
    proof that toggling it is invalid, only that the client did not flag it
    as a GM-switch NPC.
    """
    if command.name != "npc":
        raise ValueError("describe_npc_target only applies to npc commands")
    args = _require_args_tuple(command.args, min_length=2)
    mob_id = _require_arg_int(args[1], "mob_id")
    if not npc_switch_catalog.is_gm_switchable_npc(mob_id):
        return None
    return npc_switch_catalog.npc_gm_name(mob_id)


def new_audit_record_id() -> str:
    """One id tying an `issued` row to the `outcome` row that closes it.

    Random, not a counter: two processes appending to the same ndjson file
    (the runtime and a replay tool, or two runtimes sharing a capture root)
    would hand out the same counter value and silently merge two commands
    into one story.  16 hex characters, because the whole population is one
    audit file, and short enough that a human reading the file can match a
    pair by eye.
    """
    return uuid.uuid4().hex[:16]


def log_gm_command(
    command: GmCommand,
    account_name: str,
    *,
    log_path: str | Path = DEFAULT_LOG_PATH,
    now_ts: float | None = None,
    record_id: str | None = None,
) -> Path:
    """Append one ndjson line recording that account_name issued command.

    This is the "log ฝั่งเซิร์ฟเวอร์" step GM-003 calls for before any
    command has real execution wired in.  It performs no gameplay effect.

    The row this writes says only that a GM typed a parseable command.  It
    cannot say what became of it -- at the moment it is written, no gate has
    been read and no frame has been composed (see `log_gm_command_outcome`,
    which writes the second row that can).  `record_id` correlates the two;
    a caller that passes None gets a fresh one, so every row in the file has
    the field whether or not anyone closes it.
    """
    if not isinstance(account_name, str) or not account_name:
        raise ValueError("account_name must be a non-empty str")
    if record_id is not None and (
        not isinstance(record_id, str) or not record_id
    ):
        raise ValueError("record_id must be a non-empty str or None")
    args = _require_args_tuple(command.args, min_length=0)
    ts = now_ts if now_ts is not None else time.time()
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
        "account": account_name,
        "command": command.name,
        "args": list(args),
        "raw": command.raw,
        "executed": False,
        # ~~"parsed and logged only, no gameplay effect applied"~~ -- that
        # note was true of every command this lane had until the cross-scene
        # `/warp` (round `gejldf`), which writes a login-scene config entry
        # before its own outcome row.  pf-adversary caught the row still
        # saying it, in the file GT-127 and GT-141 are graded on.  The note
        # now says what this row can honestly say at the moment it is
        # written: the line parsed, and nothing has been decided yet.
        "note": (
            "GM-003 v1: parsed and logged; what became of it is the outcome "
            "row with the same record_id"
        ),
        "record": AUDIT_RECORD_ISSUED,
        "record_id": record_id if record_id is not None else new_audit_record_id(),
    }
    return _append_audit_record(record, log_path)


def log_gm_command_outcome(
    command: GmCommand,
    account_name: str,
    outcome: str,
    *,
    record_id: str,
    log_path: str | Path = DEFAULT_LOG_PATH,
    now_ts: float | None = None,
) -> Path:
    """Append the second ndjson row: what became of an already-logged command.

    CORE-REQUEST-GM-032 items 1-2, from `COO-DECISION 20260829_0041`'s
    finding that "the audit has to record whether the queueing really
    happened".  Until this row existed, `/warp 2 100 200` with the version
    gate SHUT and the same line with the gate OPEN wrote byte-identical
    rows, because `log_gm_command` runs before either gate is read -- so
    the audit file, which `GT-127` decides on, could not tell a withheld
    command from a sent one.

    Appended, never an amend of the issued row: this house does not rewrite
    history, and an audit log whose earlier lines can change is not an audit
    log.  Two rows sharing one `record_id` say more than one mutated row
    anyway -- the pair carries the order of events.

    NOT SUBJECT TO `MAX_COMMAND_LOG_BYTES`, deliberately and boundedly: the
    quota is read once, before the `issued` row, in `handle_local_talk_chat`.
    A command that got an issued row therefore always gets its outcome row,
    even if the cap fell between them -- because the alternative is an
    `issued` row nothing ever closes, which is the one file state this round
    exists to eliminate.  The overshoot is one line per command that already
    passed the gate, not unbounded growth.

    `outcome` must be one of `AUDIT_OUTCOMES`, or carry one of
    `AUDIT_OUTCOME_PREFIXES` with something after it.  What each value claims is
    documented on those constants; the one thing NO value here claims today
    is that the frame reached a socket, which is not knowable from inside
    this lane (see `OUTCOME_QUEUED`).
    """
    if not isinstance(account_name, str) or not account_name:
        raise ValueError("account_name must be a non-empty str")
    if not isinstance(record_id, str) or not record_id:
        raise ValueError("record_id must be a non-empty str")
    if not isinstance(outcome, str) or not outcome:
        raise ValueError("outcome must be a non-empty str")
    # Prefixed values (`refused_<ExcType>`, `withheld_<gate>`) are open sets
    # by construction -- the suffix is a type name or a gate name -- so the
    # check is "starts with a known prefix, or is a known exact value", not
    # membership in a closed list.  An unrecognised outcome is a programming
    # error in this lane, not a client input, so it raises rather than
    # writing a row nobody can interpret.
    if outcome == OUTCOME_QUEUED:
        # Named separately from "unknown", because it is not unknown -- it is
        # forbidden HERE, and the caller who reaches this line is trying to
        # write through the general-purpose door a word that only the
        # append-site confirmation may write (see OUTCOME_QUEUED's own
        # comment).  Still a hard refusal after CORE-REQUEST-GM-040: the
        # word became writable, this function did not become its writer.
        raise ValueError(
            "outcome 'queued' may not be written through this writer; only "
            "log_gm_command_queued, called from the append-site "
            "confirmation callback (CORE-REQUEST-GM-040), may write it"
        )
    if not is_known_outcome(outcome):
        raise ValueError(f"unknown outcome: {outcome!r}")
    args = _require_args_tuple(command.args, min_length=0)
    ts = now_ts if now_ts is not None else time.time()
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
        "account": account_name,
        "command": command.name,
        "args": list(args),
        "raw": command.raw,
        "executed": False,
        "note": AUDIT_OUTCOME_NOTE,
        "record": AUDIT_RECORD_OUTCOME,
        "record_id": record_id,
        "outcome": outcome,
    }
    return _append_audit_record(record, log_path)


def log_gm_command_queued(
    command: GmCommand,
    account_name: str,
    *,
    record_id: str,
    log_path: str | Path = DEFAULT_LOG_PATH,
    now_ts: float | None = None,
) -> Path:
    """Append the `queued` row -- the word CORE-REQUEST-GM-032 item 3 reserved.

    CORE-REQUEST-GM-040, LANE-GM's half.  Chief's half landed first
    (`runtime.py`, the append site: `pirate-force-server#299`, merged
    2026-08-30T10:47Z): right after `actions = actions + [gm_action]` it
    reads `session._gm_action_queued_confirm`, a `(action, callback)` pair
    matched by `is`, and fires the callback.  THAT CALLBACK IS THE ONLY
    THING THIS FUNCTION EXISTS FOR.  Calling it from anywhere else writes a
    claim nothing measured, which is exactly the failure
    `OUTCOME_QUEUED`'s own comment was reserved against.

    WHY A SEPARATE FUNCTION AND NOT A FLAG ON `log_gm_command_outcome`:
    pf-adversary's standing finding (round `xk4wmz`, pinned by
    `tests/test_gm_command_audit_outcome.py::QueuedIsReservedTests::
    test_the_word_is_named_for_the_day_it_lands_and_refused_until_then`) is
    that the WRITER is the door and a source scan cannot make an
    output-shaped guarantee -- an `AUDIT_OUTCOMES[-1]` read past the scan
    once already.  A keyword flag on the general writer would be reachable
    by exactly that kind of accidental pass-through (`**kwargs` forwarded by
    a hook, a caller that copies a call site).  A function with no `outcome`
    parameter at all cannot be reached by a value; it can only be reached by
    a name a reader can see and a test can scan for.  So:

    - `log_gm_command_outcome` still REFUSES `queued` by every spelling,
      unchanged, and `is_known_outcome('queued')` is still False.  Those
      three pins stay exactly as they were; nothing was relaxed to land
      this.
    - the word is hard-coded HERE and never taken from a parameter, so no
      caller has to name it -- which keeps the AST scan over the lane's
      source (`QueuedIsReservedTests`) both green and meaningful: it still
      says "no lane file outside this one names the reserved word", and
      that is still true after this round.

    THIS IS A THIRD ROW, NOT AN AMEND OF THE SECOND.  One appended command
    now writes `issued` -> `outcome:composed` -> `outcome:queued`, three
    lines sharing one `record_id`, in that order.  Append-only is this
    house's rule (see `log_gm_command_outcome`'s own docstring) and the
    order of the pair already carried meaning; the third line extends the
    sequence rather than rewriting the second.  A reader of the file that
    assumed "exactly one outcome row per issued row" must now read "the
    LAST outcome row for a record_id is the furthest that command got" --
    `GT-127`/`GT-141` grade on this file, so that sentence is the one that
    changed for them.

    `executed` stays False, and that is deliberate even here.  `queued`
    means the action tuple really reached `runtime.py`'s action list -- one
    step further than `composed`, which only ever meant "the frame exists
    and was handed back".  It is still NOT a claim that bytes reached a
    socket, that the client parsed them, or that anything moved in the
    world; nothing inside this process can see any of those.  The three
    words are a ladder with a top rung this lane cannot reach.
    """
    if not isinstance(account_name, str) or not account_name:
        raise ValueError("account_name must be a non-empty str")
    if not isinstance(record_id, str) or not record_id:
        # Same reasoning as the outcome row: an id that matches no issued row
        # reads like a complete record and is worse than a missing line.
        raise ValueError("record_id must be a non-empty str")
    args = _require_args_tuple(command.args, min_length=0)
    ts = now_ts if now_ts is not None else time.time()
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
        "account": account_name,
        "command": command.name,
        "args": list(args),
        "raw": command.raw,
        "executed": False,
        "note": AUDIT_OUTCOME_NOTE,
        "record": AUDIT_RECORD_OUTCOME,
        "record_id": record_id,
        "outcome": OUTCOME_QUEUED,
    }
    return _append_audit_record(record, log_path)


def is_known_outcome(outcome: str) -> bool:
    """True for a value `log_gm_command_outcome` will write.

    `queued` is False here, and by any spelling: a prefixed value cannot end
    up equal to it either, since neither prefix is a prefix of the word.
    ~~The day CORE-REQUEST-GM-032 item 3 lands, the change is one line HERE,
    next to the reason, rather than in whichever caller happens to want
    it.~~ -- that day came (CORE-REQUEST-GM-040, 2026-08-30) AND THIS LINE
    DID NOT CHANGE, deliberately.  Flipping it here would have made `queued`
    writable through `log_gm_command_outcome` by any caller holding the
    string, which is the exact hole `QueuedIsReservedTests` measured.  The
    word got its own writer (`log_gm_command_queued`) instead, and this
    predicate keeps meaning what it always meant: "a value the GENERAL
    outcome writer will accept".
    """
    if outcome == OUTCOME_QUEUED:
        return False
    if outcome in AUDIT_OUTCOMES:
        return True
    return any(
        outcome.startswith(prefix) and len(outcome) > len(prefix)
        for prefix in AUDIT_OUTCOME_PREFIXES
    )


def _append_audit_record(record: dict, log_path: str | Path) -> Path:
    """Serialize one record and append it as one ndjson line.

    Shared by both audit rows so the fail-closed properties below (short
    write detection, 0o600/0o700 modes, serialize-before-touching-disk) are
    one implementation rather than two that drift.
    """
    # Serialize before touching the filesystem: a non-serializable args
    # element (shape-valid tuple, e.g. a custom object with no JSON mapping)
    # must not create the log directory/file and then raise -- that would
    # violate this function's own fail-closed "writes nothing on rejection"
    # contract for a failure mode one step past the shape check.
    line = json.dumps(record, ensure_ascii=False) + "\n"
    path = Path(log_path)
    # mode=0o700 on the leaf directory only (Path.mkdir(parents=True) creates
    # any missing *parents* at the platform default mode, ignoring `mode` --
    # see gm/command_capture.py's identical caveat for capture_raw_gm_command's
    # own directory). 0o700 has no group/other bits, so no umask can add any
    # back regardless of this project's own default (0o022) or a permissive
    # one (0o000).
    #
    # pf-adversary (verification pass, same round): `mkdir(..., exist_ok=True)`
    # never chmods a directory that already exists. This function's own
    # `DEFAULT_LOG_PATH` and command_capture.py's `DEFAULT_CAPTURE_ROOT`
    # share the literal parent directory `capture/`, which `.gitignore`
    # documents as never cleaned up -- whichever of the two functions runs
    # first on a real host creates that shared parent at whatever mode the
    # umask in effect at that one moment left it, and it would otherwise
    # stay there forever. `os.chmod` re-asserts 0o700 on every call.
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    # Explicit mode=0o600, same fix and same rationale as
    # capture_raw_gm_command's os.open() call in gm/command_capture.py: the
    # builtin open("a") this line used to call creates a new file at the
    # platform default (0o666 masked by umask, no execute bit but still
    # world-readable, and world-writable under a permissive umask) with no
    # way to pass an explicit mode. This file is an ndjson audit log of every
    # GM command issued -- including full `say <message>` bodies and other
    # free-text a GM typed -- the same class of sensitive, client/GM-typed
    # content the capture-file fix (round vb3ktn) was written to protect, in
    # a sibling file that fix did not touch. Regardless-of-umask reasoning is
    # identical: 0o600 has no group/other bits to be added back by any umask.
    # Same Windows caveat as command_capture.py applies (NTFS ignores this
    # bit split; this write zone has no ACL API to close that gap from here).
    fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    try:
        # pf-adversary (round hs9m2r): this used to be a bare
        # `os.write(fd, ...)` whose return value was discarded. write(2) is
        # not required to write every requested byte in one call, and a
        # filesystem that fills up mid-write is the classic case where it
        # writes fewer WITHOUT raising. The old code therefore reported
        # success for a short write: `log_gm_command` returned normally,
        # `chat_command.handle_local_talk_chat`'s `except OSError` never
        # fired, and the caller handed the GM command onward believing it
        # was audited -- while the ndjson file held a truncated fragment
        # with no trailing newline, which the next successful append then
        # glued itself onto, corrupting two records instead of one. That is
        # exactly the "a full disk silently turns audited GM actions into
        # unaudited ones" failure this function's callers claim to be
        # closed against.
        #
        # ~~O_APPEND makes the loop safe: every write lands at the current
        # end of file atomically, so a resumed write cannot interleave with
        # another process's record.~~ MEASURED FALSE by pf-adversary in the
        # round that moved this comment into shared code (CORE-REQUEST-GM-032):
        # O_APPEND makes each individual write(2) atomic against the append
        # offset, NOT a SEQUENCE of them. With a short write, another writer's
        # whole record can land in the gap, and the probe produced exactly
        # that -- two unparseable lines, one of them a real GM command's
        # `issued` row. What the loop actually buys is DETECTION: a short
        # write is no longer reported as success (which is the failure it was
        # written for). Recorded rather than papered over, and it is this
        # lane's to own now precisely because this round DOUBLED the number of
        # write(2) calls per command and therefore the window.
        # Zero bytes written with no exception means no forward progress is
        # possible -- raise rather than spin.
        payload = line.encode("utf-8")
        written = 0
        while written < len(payload):
            count = os.write(fd, payload[written:])
            if count <= 0:
                raise OSError(
                    f"short write to {path}: {written}/{len(payload)} bytes"
                )
            written += count
    finally:
        os.close(fd)
    return path
