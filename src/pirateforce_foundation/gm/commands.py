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
from pathlib import Path

from . import npc_switch_catalog
from . import scene_catalog

COMMAND_NAMES = ("warp", "npc", "item", "lv", "spawn", "say")

DEFAULT_LOG_PATH = "capture/gm_command_log.ndjson"

# Channel_GMGlobalMessageVital (0x9F2C) is a global broadcast, not a private
# chat line -- capping this keeps a fat-fingered or hostile "say" from
# growing without bound once execution is wired in, and keeps each logged
# record to roughly one write() call worth of bytes.
MAX_SAY_MESSAGE_LENGTH = 480


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
            raise GmCommandParseError("warp <scene_id> [x y]")
        _require_int(args[0], "scene_id")
        if len(args) == 3:
            _require_number(args[1], "x")
            _require_number(args[2], "y")
        return GmCommand(name, tuple(args), stripped)

    if name == "npc":
        args = rest.split()
        if len(args) != 2 or args[0] not in ("on", "off"):
            raise GmCommandParseError("npc on|off <mob_id>")
        _require_int(args[1], "mob_id")
        return GmCommand(name, tuple(args), stripped)

    if name == "item":
        args = rest.split()
        if len(args) != 2:
            raise GmCommandParseError("item <id> <n>")
        _require_int(args[0], "id")
        _require_int(args[1], "n")
        return GmCommand(name, tuple(args), stripped)

    if name == "lv":
        args = rest.split()
        if len(args) != 1:
            raise GmCommandParseError("lv <n>")
        _require_int(args[0], "n")
        return GmCommand(name, tuple(args), stripped)

    if name == "spawn":
        args = rest.split()
        if len(args) != 1:
            raise GmCommandParseError("spawn <mob_id>")
        _require_int(args[0], "mob_id")
        return GmCommand(name, tuple(args), stripped)

    if name == "say":
        if not rest:
            raise GmCommandParseError("say <message>")
        if len(rest) > MAX_SAY_MESSAGE_LENGTH:
            raise GmCommandParseError(
                f"say message exceeds {MAX_SAY_MESSAGE_LENGTH} characters"
            )
        return GmCommand(name, (rest,), stripped)

    raise GmCommandParseError(
        f"unknown GM command {name!r}; expected one of {COMMAND_NAMES}"
    )


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


def log_gm_command(
    command: GmCommand,
    account_name: str,
    *,
    log_path: str | Path = DEFAULT_LOG_PATH,
    now_ts: float | None = None,
) -> Path:
    """Append one ndjson line recording that account_name issued command.

    This is the "log ฝั่งเซิร์ฟเวอร์" step GM-003 calls for before any
    command has real execution wired in.  It performs no gameplay effect.
    """
    if not isinstance(account_name, str) or not account_name:
        raise ValueError("account_name must be a non-empty str")
    args = _require_args_tuple(command.args, min_length=0)
    ts = now_ts if now_ts is not None else time.time()
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
        "account": account_name,
        "command": command.name,
        "args": list(args),
        "raw": command.raw,
        "executed": False,
        "note": "GM-003 v1: parsed and logged only, no gameplay effect applied",
    }
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
        # O_APPEND makes the loop safe: every write lands at the current
        # end of file atomically, so a resumed write cannot interleave with
        # another process's record. Zero bytes written with no exception
        # means no forward progress is possible -- raise rather than spin.
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
